"""
Checks which Sentinel-2 tile actually covers the Camp Fire's real extent,
using the FIRMS detection points already pulled (rather than guessing from
the coarse search bounding box).
"""

import os

import ee
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
ee.Initialize(project=os.environ["GEE_PROJECT_ID"])

firms = pd.read_csv("data/raw/firms/camp_fire_detections.csv")
min_lon, max_lon = firms["longitude"].min(), firms["longitude"].max()
min_lat, max_lat = firms["latitude"].min(), firms["latitude"].max()
fire_extent = ee.Geometry.BBox(min_lon, min_lat, max_lon, max_lat)

print("FIRMS detection extent (the fire's actual footprint):")
print(f"  longitude: {min_lon:.4f} to {max_lon:.4f}")
print(f"  latitude:  {min_lat:.4f} to {max_lat:.4f}\n")

for tile in ["10SEJ", "10SFJ", "10TEK", "10TFK"]:
    scene = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterDate("2018-10-01", "2018-10-31")
        .filter(ee.Filter.eq("MGRS_TILE", tile))
        .first()
    )
    geom = scene.geometry()
    # A 1km error margin is needed for polygon-vs-polygon contains() checks on
    # Earth Engine geometries; too tight a margin (e.g. 30m) gives false negatives
    # at tile edges due to geodesic-vs-projected coordinate rounding.
    fully_contains = geom.contains(fire_extent, ee.ErrorMargin(1000)).getInfo()
    print(f"Tile {tile}: fully contains FIRMS fire extent = {fully_contains}")
