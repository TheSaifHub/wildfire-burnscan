"""
Inspects the MTBS annual burn severity mosaic dataset on Earth Engine for
2018, to confirm it actually covers the Camp Fire before downloading anything.
"""

import os

import ee
from dotenv import load_dotenv

load_dotenv()
ee.Initialize(project=os.environ["GEE_PROJECT_ID"])

AOI = ee.Geometry.BBox(-121.75, 39.60, -121.35, 39.95)

collection = ee.ImageCollection("USFS/GTAC/MTBS/annual_burn_severity_mosaics/v1")

info_2018 = collection.filterDate("2018-01-01", "2018-12-31").getInfo()
print(f"2018 images in collection: {len(info_2018['features'])}")
for feature in info_2018["features"]:
    props = feature["properties"]
    print(f"  id={feature['id']}  properties keys sample: "
          f"{ {k: props[k] for k in list(props)[:8]} }")

image = collection.filterDate("2018-01-01", "2018-12-31").mosaic().clip(AOI)

hist = image.reduceRegion(
    reducer=ee.Reducer.frequencyHistogram(),
    geometry=AOI,
    scale=30,
    maxPixels=1e9,
).getInfo()
print("\nPixel value histogram over our AOI (severity class -> pixel count):")
print(hist)
