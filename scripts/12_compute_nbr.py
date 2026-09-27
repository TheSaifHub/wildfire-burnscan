"""
Phase 2, step 2: compute NBR for the before and after scenes.

NBR = (NIR - SWIR) / (NIR + SWIR) = (B8 - B12) / (B8 + B12)

Nodata pixels (B8 == 0 and B12 == 0, matching the file's own nodata=0 tag)
are excluded and written out as NaN, rather than a fake 0, since 0 is itself
a legitimate NBR value.
"""

import numpy as np
import rasterio

# Band order in the stacked files: [B2, B3, B4, B8, B11, B12]
B8_INDEX = 3
B12_INDEX = 5


def compute_nbr(stack_path, out_path):
    with rasterio.open(stack_path) as src:
        profile = src.profile
        b8 = src.read(B8_INDEX + 1).astype(np.float32)
        b12 = src.read(B12_INDEX + 1).astype(np.float32)

    nodata_mask = (b8 == 0) & (b12 == 0)

    # Suppress the runtime warning numpy would otherwise print for the
    # divide-by-zero at nodata pixels -- we're handling those explicitly below.
    with np.errstate(divide="ignore", invalid="ignore"):
        nbr = (b8 - b12) / (b8 + b12)

    nbr[nodata_mask] = np.nan

    out_profile = profile.copy()
    out_profile.update(count=1, dtype="float32", nodata=np.nan)
    with rasterio.open(out_path, "w", **out_profile) as dst:
        dst.write(nbr, 1)

    valid_pixels = ~np.isnan(nbr)
    print(f"{out_path}")
    print(f"  nodata pixels: {nodata_mask.sum()} ({100 * nodata_mask.sum() / nodata_mask.size:.1f}%)")
    print(f"  NBR range (valid pixels): {nbr[valid_pixels].min():.3f} to {nbr[valid_pixels].max():.3f}")
    print(f"  NBR mean (valid pixels): {nbr[valid_pixels].mean():.3f}")


compute_nbr("data/processed/before_stack.tif", "data/processed/before_nbr.tif")
compute_nbr("data/processed/after_stack.tif", "data/processed/after_nbr.tif")
