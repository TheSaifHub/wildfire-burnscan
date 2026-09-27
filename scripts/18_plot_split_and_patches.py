"""
Visualizes the chosen train/test split (west 60% = train, east 40% = test)
and the 64x64 patch grid, before any training happens.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import rasterio

PATCH_SIZE = 64
SPLIT_COLUMN = 2094  # from 17_choose_split.py

with rasterio.open("data/processed/mtbs_aligned.tif") as src:
    mtbs = src.read(1)
with rasterio.open("data/processed/baseline_severity.tif") as src:
    baseline = src.read(1)

height, width = mtbs.shape
valid = np.isin(baseline, [1, 2, 3, 4]) & np.isin(mtbs, [1, 2, 3, 4])

# after-fire RGB, for context
RGB_INDICES = [2, 1, 0]
with rasterio.open("data/processed/after_stack.tif") as src:
    after_stack = src.read()
rgb = after_stack[RGB_INDICES].astype(np.float32)
stretched = np.zeros_like(rgb)
for i in range(3):
    band = rgb[i]
    lo, hi = np.percentile(band, [2, 98])
    stretched[i] = np.clip((band - lo) / (hi - lo), 0, 1)
after_rgb = np.moveaxis(stretched, 0, -1)

# --- Build train/test tint overlay ---
overlay = after_rgb.copy()
train_tint = np.array([0.1, 0.2, 0.9])  # blue
test_tint = np.array([0.9, 0.5, 0.1])   # orange
alpha = 0.35

overlay[:, :SPLIT_COLUMN] = (1 - alpha) * overlay[:, :SPLIT_COLUMN] + alpha * train_tint
overlay[:, SPLIT_COLUMN:] = (1 - alpha) * overlay[:, SPLIT_COLUMN:] + alpha * test_tint

# --- Figure out which 64x64 patches are usable (>=50% valid pixels) ---
n_rows = height // PATCH_SIZE
n_cols = width // PATCH_SIZE
train_patches, test_patches = 0, 0
for r in range(n_rows):
    for c in range(n_cols):
        y0, y1 = r * PATCH_SIZE, (r + 1) * PATCH_SIZE
        x0, x1 = c * PATCH_SIZE, (c + 1) * PATCH_SIZE
        patch_valid = valid[y0:y1, x0:x1]
        if patch_valid.mean() < 0.5:
            continue
        patch_center_x = (x0 + x1) // 2
        if patch_center_x < SPLIT_COLUMN:
            train_patches += 1
        else:
            test_patches += 1

print(f"Usable patches (>=50% valid pixels): {train_patches} train, {test_patches} test "
      f"({train_patches + test_patches} total, {PATCH_SIZE}x{PATCH_SIZE} each)")

# --- Plot: full split overview + zoomed patch-grid inset near the boundary ---
fig, axes = plt.subplots(1, 2, figsize=(18, 9))

axes[0].imshow(overlay)
axes[0].axvline(SPLIT_COLUMN, color="white", linewidth=2, linestyle="--")
axes[0].set_title("Train (blue, west) / Test (orange, east) split")
axes[0].axis("off")
patches = [
    mpatches.Patch(color=train_tint, label="Train region"),
    mpatches.Patch(color=test_tint, label="Test region"),
]
axes[0].legend(handles=patches, loc="lower left", fontsize=9, framealpha=0.9)

# Zoomed inset centered on the split boundary, showing actual patch grid lines
zoom_half = 320
cy = height // 2
y0, y1 = cy - zoom_half, cy + zoom_half
x0, x1 = SPLIT_COLUMN - zoom_half, SPLIT_COLUMN + zoom_half
axes[1].imshow(overlay[y0:y1, x0:x1])
# draw patch grid lines within this crop
first_grid_x = (x0 // PATCH_SIZE) * PATCH_SIZE
for gx in range(first_grid_x, x1, PATCH_SIZE):
    axes[1].axvline(gx - x0, color="white", linewidth=0.6, alpha=0.7)
first_grid_y = (y0 // PATCH_SIZE) * PATCH_SIZE
for gy in range(first_grid_y, y1, PATCH_SIZE):
    axes[1].axhline(gy - y0, color="white", linewidth=0.6, alpha=0.7)
axes[1].axvline(SPLIT_COLUMN - x0, color="white", linewidth=2, linestyle="--")
axes[1].set_title(f"Zoomed: {PATCH_SIZE}x{PATCH_SIZE} patch grid near the split boundary")
axes[1].axis("off")

plt.tight_layout()
plt.savefig("data/processed/split_and_patches.png", dpi=150, bbox_inches="tight")
print("Saved data/processed/split_and_patches.png")
