from unittest.mock import patch, Mock

from networkx import MultiDiGraph as Graph
import geopandas as gpd
import osmnx as ox
import pytest

from typing import Generator


@pytest.fixture
def sample_gdf() -> gpd.GeoDataFrame:
    """Loads locally stored Melbourne Aiport data as GeoDataFrame"""
    path = "./tests/data/ymml.gpkg"
    gdf = gpd.read_file(path)
    return gdf


@pytest.fixture
def sample_graph() -> Graph:
    """Loads locally stored Melbourne Aiport data as NetworkX MultiDiGraph"""
    path = "./tests/data/ymml.graphml"
    graph = ox.load_graphml(path)
    return graph


@pytest.fixture
def mock_gdf(sample_gdf) -> Generator[Mock, None, None]:
    with patch(
        "airport_osm.main.ox.features_from_place", return_value=sample_gdf
    ) as mock:
        yield mock


@pytest.fixture
def mock_graph(sample_graph) -> Generator[Mock, None, None]:
    with patch(
        "airport_osm.main.ox.graph_from_place", return_value=sample_graph
    ) as mock:
        yield mock
