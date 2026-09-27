"""
Confirms class balance specifically within the patches that will actually be
used for training/testing (i.e. after dropping <50%-valid patches), not just
the whole train/test region -- this is what the model will actually see.
"""

import numpy as np
import rasterio

PATCH_SIZE = 64
SPLIT_COLUMN = 2094

CLASS_LABELS = {1: "Unburned/very low", 2: "Low", 3: "Moderate", 4: "High"}

with rasterio.open("data/processed/mtbs_aligned.tif") as src:
    mtbs = src.read(1)
with rasterio.open("data/processed/baseline_severity.tif") as src:
    baseline = src.read(1)

height, width = mtbs.shape
valid = np.isin(baseline, [1, 2, 3, 4]) & np.isin(mtbs, [1, 2, 3, 4])

n_rows = height // PATCH_SIZE
n_cols = width // PATCH_SIZE

train_counts = {c: 0 for c in CLASS_LABELS}
test_counts = {c: 0 for c in CLASS_LABELS}
train_patches, test_patches = 0, 0

for r in range(n_rows):
    for c in range(n_cols):
        y0, y1 = r * PATCH_SIZE, (r + 1) * PATCH_SIZE
        x0, x1 = c * PATCH_SIZE, (c + 1) * PATCH_SIZE
        patch_valid = valid[y0:y1, x0:x1]
        if patch_valid.mean() < 0.5:
            continue

        patch_mtbs = mtbs[y0:y1, x0:x1]
        patch_center_x = (x0 + x1) // 2
        target = train_counts if patch_center_x < SPLIT_COLUMN else test_counts
        for cls in CLASS_LABELS:
            target[cls] += int(((patch_mtbs == cls) & patch_valid).sum())

        if patch_center_x < SPLIT_COLUMN:
            train_patches += 1
        else:
            test_patches += 1

print(f"Kept patches: {train_patches} train, {test_patches} test\n")
print(f"{'Class':<20}{'Train pixels':>15}{'Train %':>10}{'Test pixels':>15}{'Test %':>10}")
train_total = sum(train_counts.values())
test_total = sum(test_counts.values())
for cls, label in CLASS_LABELS.items():
    tr = train_counts[cls]
    te = test_counts[cls]
    print(f"{label:<20}{tr:>15}{100*tr/train_total:>9.1f}%{te:>15}{100*te/test_total:>9.1f}%")
