"""
Phase 2, step 1: alignment.

Stacks the 6 separate before-bands into one multi-band raster, same for the
6 after-bands, then resamples the MTBS severity map (30m) onto that exact
same pixel grid (10m) using nearest-neighbor, so all three rasters can be
compared pixel-for-pixel.
"""

import os

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject

BANDS = ["B2", "B3", "B4", "B8", "B11", "B12"]
SENTINEL_DIR = "data/raw/sentinel2"
OUT_DIR = "data/processed"

os.makedirs(OUT_DIR, exist_ok=True)


def stack_bands(label, tile="10TFK"):
    """Reads 6 single-band GeoTIFFs and stacks them into one array."""
    band_arrays = []
    reference_profile = None

    for band in BANDS:
        path = f"{SENTINEL_DIR}/{label}_{tile}_{band}.tif"
        with rasterio.open(path) as src:
            band_arrays.append(src.read(1))
            if reference_profile is None:
                reference_profile = src.profile

    stack = np.stack(band_arrays, axis=0)  # shape: (6, height, width)
    return stack, reference_profile


def save_stack(stack, profile, out_path):
    profile = profile.copy()
    profile.update(count=stack.shape[0])
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(stack)


# --- Step 1: stack before and after bands ---
before_stack, before_profile = stack_bands("before_2018-10-22")
after_stack, after_profile = stack_bands("after_2019-01-25")

# --- Step 2: confirm before/after already share the same grid ---
# (both were pulled from Earth Engine with the same AOI/scale/CRS, so this
# should already be true -- checking rather than assuming it)
assert before_profile["transform"] == after_profile["transform"], "before/after transform mismatch"
assert before_profile["crs"] == after_profile["crs"], "before/after CRS mismatch"
assert before_stack.shape == after_stack.shape, "before/after shape mismatch"
print(f"Before/after grids match: shape={before_stack.shape}, crs={before_profile['crs']}")

save_stack(before_stack, before_profile, f"{OUT_DIR}/before_stack.tif")
save_stack(after_stack, after_profile, f"{OUT_DIR}/after_stack.tif")
print("Saved before_stack.tif and after_stack.tif")

# --- Step 3: resample MTBS (30m) onto the Sentinel-2 grid (10m) ---
with rasterio.open("data/raw/mtbs/camp_fire_mtbs_severity_2018.tif") as mtbs_src:
    mtbs_data = mtbs_src.read(1)
    mtbs_transform = mtbs_src.transform
    mtbs_crs = mtbs_src.crs

aligned_mtbs = np.zeros((before_stack.shape[1], before_stack.shape[2]), dtype=mtbs_data.dtype)

reproject(
    source=mtbs_data,
    destination=aligned_mtbs,
    src_transform=mtbs_transform,
    src_crs=mtbs_crs,
    dst_transform=before_profile["transform"],
    dst_crs=before_profile["crs"],
    resampling=Resampling.nearest,
)

mtbs_out_profile = before_profile.copy()
mtbs_out_profile.update(count=1, dtype=aligned_mtbs.dtype)
with rasterio.open(f"{OUT_DIR}/mtbs_aligned.tif", "w", **mtbs_out_profile) as dst:
    dst.write(aligned_mtbs, 1)

print(f"Saved mtbs_aligned.tif -> shape={aligned_mtbs.shape}, matches Sentinel-2 grid: "
      f"{aligned_mtbs.shape == before_stack.shape[1:]}")
