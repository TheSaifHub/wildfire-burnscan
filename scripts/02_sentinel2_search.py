"""
Searches Google Earth Engine's Sentinel-2 collection for candidate "before"
and "after" scenes covering the Camp Fire area, and prints each candidate's
cloud-cover percentage so a scene can be picked by hand.

Doesn't download or export any imagery yet -- that's a separate, later step
once a specific before/after pair is chosen.

Requires GEE_PROJECT_ID environment variable (see .env) and a one-time
`earthengine authenticate` login already completed in this environment.
"""

import os

import ee
from dotenv import load_dotenv

load_dotenv()

ee.Initialize(project=os.environ["GEE_PROJECT_ID"])

# Same Butte County / Paradise bounding box used for the FIRMS pull
AOI = ee.Geometry.BBox(-121.75, 39.60, -121.35, 39.95)

BEFORE_START, BEFORE_END = "2018-10-01", "2018-10-31"
AFTER_START, AFTER_END = "2018-12-10", "2018-12-31"


def list_candidates(start, end, label):
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(AOI)
        .filterDate(start, end)
        .sort("CLOUDY_PIXEL_PERCENTAGE")
    )

    info = collection.getInfo()
    print(f"\n--- {label} window: {start} to {end} ---")
    print(f"{len(info['features'])} scene(s) found\n")

    for feature in info["features"]:
        props = feature["properties"]
        scene_id = props["PRODUCT_ID"]
        date = props["GENERATION_TIME"]
        cloud_pct = props["CLOUDY_PIXEL_PERCENTAGE"]
        print(f"  {scene_id}  |  cloud cover: {cloud_pct:.1f}%")


list_candidates(BEFORE_START, BEFORE_END, "BEFORE")
list_candidates(AFTER_START, AFTER_END, "AFTER")
