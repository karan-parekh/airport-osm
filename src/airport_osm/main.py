"""
AirportOSM is a thin OSMnx wrapper that designed for getting ground movement instructions for airports.
This is designed with LLMs in mind and is intended to be used as a tool for agents to call.

Citation:
    OSMnx: Boeing, G. (2025). Modeling and Analyzing Urban Networks and Amenities With OSMnx. Geographical Analysis, 57(4), 567-577. https://doi.org/10.1111/gean.70009
"""

import logging
import re
from typing import Literal, Optional, get_args

import networkx as nx
import osmnx as ox
from geopandas import GeoDataFrame
from networkx import MultiDiGraph as Graph
from pydantic import BaseModel

from .utils.missing_refs import add_missing_refs
from .utils.turn_instructions import generate_turn_instructions
from .utils.nearest_point import nearest_parking_position, nearest_holding_position

from .errors import AirportOSMError, GraphError

AEROWAY_TYPE = Literal[
    "aerodrome", "runway", "taxiway", "gate", "holding_position", "parking_position"
]


class AerowayRef(BaseModel):
    """
    A point on the movement area of an airport can be defined by the type of aeroway and a reference name of the point.
    Eg: Runway 09, Taxiway C, Holding point A1, Gate 34.

    Args:
        aeroway: defines the type of area: 'runway', 'taxiway', 'holding_position', etc.
        ref: ref is the name of the aeroway: '09/27' for a runway or 'C' for a taxiway, etc.

    Usage:
        >>> ar = AerowayRef(aeroway="runway", ref="09")
        >>> ar = AerowayRef(aeroway="gate", ref="D16")
        >>> ar = AerowayRef(aeroway="parking_position", ref="B3")
    """

    aeroway: AEROWAY_TYPE
    ref: str


class AirportOSM:
    """
    AirportOSM is a thin OSMnx wrapper that designed for getting ground movement instructions for airports.

    Args:
        icao_code: ICAO code of the airport.

    Usage:
        >>> melb = AirportOSM(icao_code='YMML') # Melbourne airport
        >>> orig = AerowayRef(aeroway='gate', ref='D16')
        >>> dest = AerowayRef(aeroway='runway', ref='09')
        >>> print(melb.taxi(orig, dest))
        Taxi via B, continue on C, turn left on D, turn right on E, hold short runway 09

    To handle cache, use OSMnx cache setting options. https://osmnx.readthedocs.io/en/stable/user-reference.html#module-osmnx.settings
    """

    def __init__(self, icao_code: str) -> None:
        if not self._is_icao_code(icao_code.upper()):
            raise AirportOSMError(f"Invalid ICAO code: {icao_code}")
        self.icao_code = icao_code.upper()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._gdf: Optional[GeoDataFrame] = None
        self._G = None
        self._G_no_rw: Optional[Graph] = None

    @property
    def gdf(self) -> GeoDataFrame:
        """Lazy loading GeoDataFrame"""
        if self._gdf is None:
            self._gdf = self._load_gdf()
        return self._gdf

    @property
    def G(self) -> Graph:
        """Lazy loading Graph"""
        if self._G is None:
            self._G = self._load_graph()
        return self._G

    @property
    def G_no_runways(self):
        """Lazy loading Graph with no runways for taxi instructions"""
        if self._G_no_rw is None:
            self._G_no_rw = self._remove_runways()
        return self._G_no_rw

    def taxi_from_gate_to_runway(
        self, gate: str, runway: str, turn_instructions: bool = True
    ) -> GeoDataFrame | str:
        """
        Taxi instructions fom gate/stand to the hold short point before the runway

        Args:
            gate: Gate/Stand name eg: "13"
            runway: Runway number eg: "03L"
        """
        parking_position = nearest_parking_position(self.gdf, gate)
        holding_position = nearest_holding_position(self.gdf, runway)
        orig = AerowayRef(aeroway="parking_position", ref=parking_position.ref)
        dest = AerowayRef(aeroway="holding_position", ref=holding_position.ref)

        instructions = self.taxi(orig, dest, turn_instructions=turn_instructions)
        if not isinstance(instructions, str):
            return instructions
        instructions = f"{instructions}, hold short runway {runway}"
        return instructions

    def taxi_from_runway_to_gate(
        self, runway: str, gate: str, turn_instructions: bool = True
    ) -> GeoDataFrame | str:
        raise NotImplementedError(
            "Method under construction. Please use `.taxi` API instead"
        )  # Todo: Implement this method
        # orig = AerowayRef(aeroway="runway", ref=runway)
        # dest = AerowayRef(aeroway="gate", ref=gate)
        # return self.taxi(orig, dest, turn_instructions=turn_instructions)

    def taxi(
        self,
        orig: AerowayRef,
        dest: AerowayRef,
        include_runway: bool = False,
        turn_instructions: bool = True,
    ) -> GeoDataFrame | str:
        """
        Generate taxi instructions from `orig` to `dest`.
        """
        orig_node = self._find_node(orig)
        dest_node = self._find_node(dest)
        route = self._get_shortest_path(orig_node, dest_node, include_runway)

        if route is None:
            raise GraphError(f"Empty Route between {orig} and {dest}")
        G = self.G if include_runway else self.G_no_runways
        route_gdf = ox.routing.route_to_gdf(G, route, weight="length")
        if turn_instructions:
            return generate_turn_instructions(route_gdf)
        return route_gdf

    def _get_shortest_path(
        self, orig_node: int, dest_node: int, include_runway: bool
    ) -> list[int] | None:
        try:
            G = self.G if include_runway else self.G_no_runways
            return ox.shortest_path(G, orig_node, dest_node, weight="length")
        except nx.NodeNotFound as e:
            raise e

    def _find_node(self, loc: AerowayRef) -> int:
        row = self.gdf[
            (self.gdf.aeroway == loc.aeroway) & (self.gdf.ref.str.contains(loc.ref))
        ]
        if row.empty:
            raise AirportOSMError(f"Node not found for location {loc}")
        node = row.id.values[0]
        return node

    def _load_gdf(self) -> GeoDataFrame:
        tags = {
            "aeroway": list(get_args(AEROWAY_TYPE)),
            "proposed:aeroway": ["taxiway"],
        }
        gdf = ox.features_from_place(self.icao_code, tags)
        if gdf.empty:
            raise AirportOSMError(f"No features found for '{self.icao_code}'")

        gdf = gdf.dropna(axis=1, how="all")  # Drop columns where all the values are NA
        gdf.reset_index(inplace=True)  # Flatten multi index
        gdf = add_missing_refs(gdf, self.icao_code)
        return gdf

    def _load_graph(self) -> Graph:
        current_aeroways = f'["aeroway"~"{"|".join(get_args(AEROWAY_TYPE))}"]'
        proposed_aeroways = '["proposed:aeroway"~"taxiway"]'
        custom_filter = [current_aeroways, proposed_aeroways]
        G_complex = ox.graph_from_place(
            self.icao_code, custom_filter=custom_filter, simplify=False
        )
        if G_complex.number_of_nodes() == 0:
            raise GraphError(f"Graph not found for place {self.icao_code}")
        return ox.add_edge_bearings(G_complex)

    def _remove_runways(self):
        runways = list(self.gdf[self.gdf.aeroway == "runway"].ref.values)
        nodes, edges = ox.graph_to_gdfs(self.G)
        if edges.empty:
            raise GraphError("Graph edges are empty")

        edges_no_rw = edges[~edges.ref.isin(runways)]
        nodes_no_rw = nodes[nodes.index.isin(edges_no_rw.index.get_level_values("v"))]
        G_no_rw = ox.convert.graph_from_gdfs(nodes_no_rw, edges_no_rw)
        return G_no_rw

    @staticmethod
    def _is_icao_code(code: str) -> bool:
        pattern = r"^[A-Z]{4}$"
        return bool(re.match(pattern, code))
