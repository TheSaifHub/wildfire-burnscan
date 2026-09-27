"""Check actual footprint overlap with our AOI for every January candidate,
not just their MGRS_TILE label -- a different relative orbit (R013 vs R113)
can cover a different slice of the same nominal tile."""

import os

import ee
from dotenv import load_dotenv

load_dotenv()
ee.Initialize(project=os.environ["GEE_PROJECT_ID"])

AOI = ee.Geometry.BBox(-121.75, 39.60, -121.35, 39.95)
aoi_area_km2 = AOI.area(ee.ErrorMargin(1000)).getInfo() / 1e6

collection = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterDate("2018-12-01", "2019-01-31")
    .filter(ee.Filter.eq("MGRS_TILE", "10TFK"))
    .sort("CLOUDY_PIXEL_PERCENTAGE")
)

info = collection.getInfo()
print(f"{'Product ID':<55} {'Cloud%':>7} {'AOI overlap':>12}")
for feature in info["features"]:
    props = feature["properties"]
    scene = ee.Image(feature["id"])
    footprint = scene.geometry()
    overlap_km2 = footprint.intersection(AOI, ee.ErrorMargin(1000)).area(ee.ErrorMargin(1000)).getInfo() / 1e6
    pct_overlap = 100 * overlap_km2 / aoi_area_km2
    print(f"{props['PRODUCT_ID']:<55} {props['CLOUDY_PIXEL_PERCENTAGE']:>6.1f}% {pct_overlap:>11.1f}%")
