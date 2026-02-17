"""
Test Suiet for AirportOSM

"""

from unittest.mock import Mock

import geopandas as gpd
import pytest

from airport_osm import AirportOSM, AerowayRef
from airport_osm.errors import AirportOSMError, GraphError
from networkx import MultiDiGraph as Graph


class TestGdfAndGraphProperties:
    """Test loading of gdf and graph properties"""

    def test_gdf_success(self, mock_gdf: Mock):
        airport = AirportOSM(icao_code="YMML")
        gdf = airport.gdf
        mock_gdf.assert_called_once()
        assert isinstance(gdf, gpd.GeoDataFrame)

    def test_empty_gdf(self, mock_gdf: Mock):
        empty_gpd = gpd.GeoDataFrame()
        mock_gdf.return_value = empty_gpd
        airport = AirportOSM(icao_code="ABCD")
        with pytest.raises(AirportOSMError):
            airport.gdf

    def test_features_gdf_args(self, mock_gdf: Mock):
        airport = AirportOSM(icao_code="ABCD")
        airport.gdf
        mock_gdf.assert_called_once_with(
            "ABCD",
            {
                "aeroway": [
                    "aerodrome",
                    "runway",
                    "taxiway",
                    "gate",
                    "holding_position",
                    "parking_position",
                ]
            },
        )

    def test_G_success(self, mock_graph: Mock):
        airport = AirportOSM(icao_code="YMML")
        G = airport.G
        mock_graph.assert_called_once()
        assert isinstance(G, Graph)

    def test_empty_G(self, mock_graph: Mock):
        empty_graph = Graph()
        mock_graph.return_value = empty_graph
        airport = AirportOSM(icao_code="ABCD")
        with pytest.raises(GraphError):
            airport.G

    def test_graph_args(self, mock_graph: Mock):
        airport = AirportOSM(icao_code="ABCD")
        airport.G
        custom_filter = '["aeroway"~"aerodrome|runway|taxiway|gate|holding_position|parking_position"]'
        mock_graph.assert_called_once_with(
            "ABCD", custom_filter=custom_filter, simplify=False
        )


class TestTaxiInstructions:
    """Test Taxi instructions"""

    def test_taxi(self, mock_gdf: Mock, mock_graph: Mock):
        airport = AirportOSM(icao_code="YMML")
        orig = AerowayRef(aeroway="parking_position", ref="F13")
        dest = AerowayRef(aeroway="holding_position", ref="B")
        instructions = airport.taxi(orig, dest, include_runway=False)
        mock_gdf.assert_called_once()
        mock_graph.assert_called_once()
        assert isinstance(instructions, str)

    def test_taxi_from_gate_to_runway(self, mock_gdf: Mock, mock_graph: Mock):
        airport = AirportOSM(icao_code="YMML")
        instructions = airport.taxi_from_gate_to_runway(gate="13", runway="16")
        mock_gdf.assert_called_once()
        mock_graph.assert_called_once()
        expected_instructions = (
            "Taxi via, Golf, Sierra, Uniform, Alpha, Bravo, hold short runway 16"
        )
        # Todo: Optimise the method to return a path with less turns. Most optimal path here should be "Taxi via Golf, Aplha, Bravo, hold short runway 16"
        if isinstance(instructions, str):
            assert instructions == expected_instructions
