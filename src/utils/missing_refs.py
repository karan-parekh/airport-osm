import warnings
import geopandas as gpd


"""
The dictionary below was generated manually by checking all the holding points at YMML on OpenStreetMaps website
They key is the node and value is the ref in format "{taxiway},{runway}"
"""
ymml_holding_pts = {
    8379717541: "M,09/27",
    8379717540: "N,09/27",
    8379717542: "34,09/27",  # Hold short position on runway 34 going towards 09/27
    9308483340: "V,09/27",
    9308483341: "V,09/27",
    2462020037: "A,09/27",
    2462020046: "A,09/27",
    8379717543: "P,09/27",
    8379717544: "Q,09/27",
    4954531608: "B,16/34",
    2462020035: "C,16/34",
    2462020067: "C,16/34",
    8379717539: "E,16/34",
    5032705167: "E,16/34",
    8379717545: "F,16/34",
    8379717546: "G,16/34",
    8379717547: "J,16/34",
    9045537824: "K,16/34",
    8379717548: "K,16/34",
    5032704010: "K,16/34",
}

airport_holding_pts: dict = {"YMML": ymml_holding_pts}


def add_missing_refs(gdf: gpd.GeoDataFrame, icao_code: str) -> gpd.GeoDataFrame:

    gdf = gdf.reset_index().copy()
    holding_points = airport_holding_pts.get(icao_code, None)
    if not holding_points:
        warnings.warn(
            f"No holding points found for {icao_code}. Returning dataframe as is"
        )
        return gdf

    for node, ref in holding_points.items():
        row = gdf[gdf.id == node]
        index = row.index.values[0]
        gdf.loc[index, "ref"] = ref

    return gdf
