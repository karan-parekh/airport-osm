import re

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point


def nearest_holding_position(
    gdf: gpd.GeoDataFrame, runway_designator: str
) -> pd.Series:
    # Project to metric system
    crs = gdf.estimate_utm_crs()
    gdf = gdf.to_crs(crs)

    match = re.match(r"(\d{1,2})([LRC]?)", runway_designator.upper())
    if not match:
        raise ValueError("Invalid runway designator")

    runway_number = match.group(1).zfill(2)  # ensure 03 not 3
    side = match.group(2)  # L, R, C or ""

    runway = gdf[
        (gdf["aeroway"] == "runway") & (gdf["ref"].str.contains(str(runway_number)))
    ]

    if side:
        runway = runway[runway["ref"].str.contains(side)]

    runway_geom = runway.iloc[0].geometry
    coordinates = list(runway_geom.coords)
    start_point = Point(coordinates[0])
    end_point = Point(coordinates[-1])
    bearing = calculate_bearing(start_point, end_point)

    # Runway number to heading
    runway_heading = int(runway_number) * 10  # 09 -> 90 deg

    # Determine which end matches runway heading
    if abs(bearing - runway_heading) < 90:
        threshold = start_point
    else:
        threshold = end_point

    holding_positions = gdf[
        (gdf["aeroway"] == "holding_position")
        & (gdf.ref.str.contains(str(runway_designator)))
    ].copy()

    holding_positions["distance"] = holding_positions.geometry.distance(threshold)
    nearest = holding_positions.sort_values("distance").iloc[0]
    return nearest


def nearest_parking_position(gdf: gpd.GeoDataFrame, gate_ref: str) -> pd.Series:
    """
    Find the nearest parking_position to a given gate.

    Parameters:
        gdf (GeoDataFrame): Must contain columns ['aeroway', 'ref', 'geometry']
        gate_ref (str): Gate reference (e.g. "13")

    Returns:
        Pandas Series with one element.
    """
    # Project to metric system
    crs = gdf.estimate_utm_crs()
    gdf = gdf.to_crs(crs)

    # Filter for parking positions
    ppdf = (
        gdf[(gdf.aeroway == "parking_position") & (gdf.ref.str.contains(gate_ref))]
        .dropna(axis=1, how="all")
        .copy()
    )

    # Filter for gates
    gate = gdf[(gdf.aeroway == "gate") & (gdf.ref == "13")].dropna(axis=1, how="all")

    # Compute distances
    gate_geometry = gate.iloc[0].geometry
    ppdf["distance"] = ppdf.geometry.distance(gate_geometry)
    nearest = ppdf.sort_values("distance").iloc[0]

    return nearest


def calculate_bearing(p1: Point, p2: Point) -> int:
    """
    Calculates the bearing between two points.
    Returns: angle in degrees clockwise from North.
    """
    delta_x = p2.x - p1.x
    delta_y = p2.y - p1.y

    # atan2(x, y) gives the angle from the positive Y-axis (North)
    angle = np.atan2(delta_x, delta_y)

    # Convert radians to degrees and normalize to 0-360
    bearing = np.degrees(angle)
    return (bearing + 360) % 360
