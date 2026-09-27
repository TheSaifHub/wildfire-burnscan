"""
Phase 3, step 2: compare our baseline severity map against MTBS's ground
truth, restricted to pixels valid in both datasets.

Excluded from comparison:
- Our nodata (255) -- the edge-clipping artifact
- MTBS class 0 (Background) -- outside the area MTBS actually mapped for this fire
- MTBS class 5 (Increased Greenness) and 6 (Non-Mapping Area) -- our 4-class
  scheme has no equivalent categories, so including them would compare
  different concepts, not just disagree on severity
"""

import numpy as np
import rasterio

CLASS_LABELS = {1: "Unburned/very low", 2: "Low", 3: "Moderate", 4: "High"}

with rasterio.open("data/processed/baseline_severity.tif") as src:
    baseline = src.read(1)

with rasterio.open("data/processed/mtbs_aligned.tif") as src:
    mtbs = src.read(1)

valid = np.isin(baseline, [1, 2, 3, 4]) & np.isin(mtbs, [1, 2, 3, 4])
total_valid = valid.sum()
print(f"Pixels valid in both datasets: {total_valid} ({100 * total_valid / baseline.size:.1f}% of AOI)\n")

classes = [1, 2, 3, 4]
confusion = np.zeros((4, 4), dtype=np.int64)
for i, our_class in enumerate(classes):
    for j, mtbs_class in enumerate(classes):
        confusion[i, j] = ((baseline == our_class) & (mtbs == mtbs_class) & valid).sum()

# --- Print confusion matrix ---
col_width = 12
header = " " * 22 + "".join(f"{CLASS_LABELS[c]:>{col_width}}" for c in classes)
print("Rows = our baseline, Columns = MTBS ground truth")
print(header)
for i, our_class in enumerate(classes):
    row = f"{CLASS_LABELS[our_class]:<22}" + "".join(f"{confusion[i, j]:>{col_width}}" for j in range(4))
    print(row)

# --- Overall agreement ---
agreement = np.trace(confusion) / total_valid
print(f"\nOverall agreement (exact class match): {100 * agreement:.1f}%")

# --- Per-class breakdown: of the pixels OUR model called each class, what did MTBS say? ---
print("\nPer-class breakdown (of pixels we called each class, what MTBS actually says):")
for i, our_class in enumerate(classes):
    row_total = confusion[i].sum()
    if row_total == 0:
        continue
    match_pct = 100 * confusion[i, i] / row_total
    print(f"  We said '{CLASS_LABELS[our_class]}' ({row_total} px) -> MTBS agrees on {match_pct:.1f}%")
