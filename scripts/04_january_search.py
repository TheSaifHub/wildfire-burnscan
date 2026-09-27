"""
Widens the "after" scene search into January 2019, restricted to tile 10TFK
(confirmed in 03_check_tile_coverage.py to cover ~99.7% of the Camp Fire extent).
"""

import os

import ee
from dotenv import load_dotenv

load_dotenv()
ee.Initialize(project=os.environ["GEE_PROJECT_ID"])

collection = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterDate("2019-01-01", "2019-01-31")
    .filter(ee.Filter.eq("MGRS_TILE", "10TFK"))
    .sort("CLOUDY_PIXEL_PERCENTAGE")
)

info = collection.getInfo()
print(f"January 2019, tile 10TFK: {len(info['features'])} scene(s) found\n")
for feature in info["features"]:
    props = feature["properties"]
    print(f"  {props['PRODUCT_ID']}  |  cloud cover: {props['CLOUDY_PIXEL_PERCENTAGE']:.1f}%")
