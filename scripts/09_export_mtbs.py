"""
Downloads the MTBS 2018 CONUS burn severity mosaic, clipped to the Camp Fire
AOI, as the ground-truth reference for Phase 3.
"""

import os

import ee
import requests
from dotenv import load_dotenv

load_dotenv()
ee.Initialize(project=os.environ["GEE_PROJECT_ID"])

AOI = ee.Geometry.BBox(-121.75, 39.60, -121.35, 39.95)

image = (
    ee.ImageCollection("USFS/GTAC/MTBS/annual_burn_severity_mosaics/v1")
    .filterDate("2018-01-01", "2018-12-31")
    .filter(ee.Filter.eq("system:index", "mtbs_CONUS_2018"))
    .first()
    .clip(AOI)
)

url = image.getDownloadURL({
    "region": AOI,
    "scale": 30,
    "format": "GEO_TIFF",
})

response = requests.get(url, timeout=120)
response.raise_for_status()

out_path = "data/raw/mtbs/camp_fire_mtbs_severity_2018.tif"
with open(out_path, "wb") as f:
    f.write(response.content)

size_mb = len(response.content) / (1024 * 1024)
print(f"Saved -> {out_path} ({size_mb:.1f} MB)")
