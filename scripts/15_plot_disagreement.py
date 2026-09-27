"""
Phase 3 sanity check: map where our baseline agrees/disagrees with MTBS,
split into "we overestimated severity" vs "we underestimated severity",
next to the after-fire RGB image for geographic context.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap
import numpy as np
import rasterio

with rasterio.open("data/processed/baseline_severity.tif") as src:
    baseline = src.read(1)

with rasterio.open("data/processed/mtbs_aligned.tif") as src:
    mtbs = src.read(1)

valid = np.isin(baseline, [1, 2, 3, 4]) & np.isin(mtbs, [1, 2, 3, 4])

# 0 = excluded, 1 = agree, 2 = we overestimated severity, 3 = we underestimated severity
category = np.zeros(baseline.shape, dtype=np.uint8)
category[valid & (baseline == mtbs)] = 1
category[valid & (baseline > mtbs)] = 2
category[valid & (baseline < mtbs)] = 3

colors = ["#e0e0e0", "#2ca02c", "#d62728", "#1f77b4"]
labels = ["Excluded (nodata/background)", "Agree", "We overestimated severity", "We underestimated severity"]
cmap = ListedColormap(colors)

# after-fire RGB, for geographic reference (same approach as script 11)
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

fig, axes = plt.subplots(1, 2, figsize=(18, 9))

axes[0].imshow(after_rgb)
axes[0].set_title("After: Jan 25, 2019 (for reference)")
axes[0].axis("off")

axes[1].imshow(category, cmap=cmap, vmin=0, vmax=3)
axes[1].set_title("Baseline vs. MTBS agreement")
axes[1].axis("off")
patches = [mpatches.Patch(color=colors[i], label=labels[i]) for i in range(4)]
axes[1].legend(handles=patches, loc="lower left", fontsize=9, framealpha=0.9)

plt.tight_layout()
plt.savefig("data/processed/disagreement_map.png", dpi=150, bbox_inches="tight")
print("Saved data/processed/disagreement_map.png")

for i, label in enumerate(labels):
    count = (category == i).sum()
    print(f"  {label:<32} {count:>10} pixels ({100 * count / category.size:.1f}%)")
