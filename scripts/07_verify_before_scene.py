"""Explicitly verify the before-scene (2018-10-22) is an R113 orbit pass with
real AOI overlap, rather than assuming it from a non-empty file size."""

import os

import ee
from dotenv import load_dotenv

load_dotenv()
ee.Initialize(project=os.environ["GEE_PROJECT_ID"])

AOI = ee.Geometry.BBox(-121.75, 39.60, -121.35, 39.95)
aoi_area_km2 = AOI.area(ee.ErrorMargin(1000)).getInfo() / 1e6

scene = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterDate("2018-10-22", "2018-10-23")
    .filter(ee.Filter.eq("MGRS_TILE", "10TFK"))
    .first()
)

product_id = scene.get("PRODUCT_ID").getInfo()
footprint = scene.geometry()
overlap_km2 = footprint.intersection(AOI, ee.ErrorMargin(1000)).area(ee.ErrorMargin(1000)).getInfo() / 1e6
pct_overlap = 100 * overlap_km2 / aoi_area_km2

print(f"Product ID: {product_id}")
print(f"Relative orbit: {'R113' if '_R113_' in product_id else ('R013' if '_R013_' in product_id else 'UNKNOWN')}")
print(f"AOI overlap: {pct_overlap:.1f}%")
