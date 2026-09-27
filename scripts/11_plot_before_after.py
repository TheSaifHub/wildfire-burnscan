"""
Phase 2 sanity check: plot before/after scenes as true-color RGB (B4, B3, B2)
side by side, to visually confirm alignment before moving on to NBR math.
"""

import matplotlib.pyplot as plt
import numpy as np
import rasterio

# Band order in the stacked files is [B2, B3, B4, B8, B11, B12] (see
# 10_align_rasters.py) -- RGB display wants [B4, B3, B2], i.e. indices [2, 1, 0]
RGB_INDICES = [2, 1, 0]


def load_rgb(path):
    with rasterio.open(path) as src:
        stack = src.read()
    rgb = stack[RGB_INDICES].astype(np.float32)

    # Sentinel-2 surface reflectance is scaled 0-10000ish; raw values are too
    # dark/flat to see detail directly, so stretch each channel to its own
    # 2nd-98th percentile range and clip to 0-1 for a viewable image.
    stretched = np.zeros_like(rgb)
    for i in range(3):
        band = rgb[i]
        lo, hi = np.percentile(band, [2, 98])
        stretched[i] = np.clip((band - lo) / (hi - lo), 0, 1)

    return np.moveaxis(stretched, 0, -1)  # (height, width, 3) for matplotlib


before_rgb = load_rgb("data/processed/before_stack.tif")
after_rgb = load_rgb("data/processed/after_stack.tif")

fig, axes = plt.subplots(1, 2, figsize=(16, 8))
axes[0].imshow(before_rgb)
axes[0].set_title("Before: Oct 22, 2018")
axes[0].axis("off")

axes[1].imshow(after_rgb)
axes[1].set_title("After: Jan 25, 2019")
axes[1].axis("off")

plt.tight_layout()
plt.savefig("data/processed/before_after_rgb.png", dpi=150, bbox_inches="tight")
print("Saved data/processed/before_after_rgb.png")
