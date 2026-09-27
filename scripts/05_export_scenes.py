"""
Downloads the locked-in before/after Sentinel-2 scenes for the Camp Fire
(tile 10TFK) as local GeoTIFFs, cropped to the fire area.

Bands: B2, B3, B4 (RGB), B8 (NIR), B11, B12 (SWIR) -- covers true-color
visualization plus everything needed for NBR/dNBR math in Phase 2.
"""

import os

import ee
import requests
from dotenv import load_dotenv

load_dotenv()
ee.Initialize(project=os.environ["GEE_PROJECT_ID"])

TILE = "10TFK"
BANDS = ["B2", "B3", "B4", "B8", "B11", "B12"]

# Same fire-area bounding box used for the FIRMS pull and tile search
AOI = ee.Geometry.BBox(-121.75, 39.60, -121.35, 39.95)

SCENES = {
    "before_2018-10-22": ("2018-10-22", "2018-10-23"),
    "after_2019-01-25": ("2019-01-25", "2019-01-26"),
}

OUT_DIR = "data/raw/sentinel2"

for label, (start, end) in SCENES.items():
    scene = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterDate(start, end)
        .filter(ee.Filter.eq("MGRS_TILE", TILE))
        .first()
        .clip(AOI)
    )

    # Earth Engine's direct-download endpoint caps requests at 48MB. A full
    # 6-band crop at 10m resolution exceeds that, so each band is downloaded
    # as its own single-band GeoTIFF and stacked back together in Phase 2.
    for band in BANDS:
        url = scene.select(band).getDownloadURL({
            "region": AOI,
            "scale": 10,
            "format": "GEO_TIFF",
        })

        response = requests.get(url, timeout=120)
        response.raise_for_status()

        out_path = os.path.join(OUT_DIR, f"{label}_{TILE}_{band}.tif")
        with open(out_path, "wb") as f:
            f.write(response.content)

        size_mb = len(response.content) / (1024 * 1024)
        print(f"Saved {label} {band} -> {out_path} ({size_mb:.1f} MB)")
