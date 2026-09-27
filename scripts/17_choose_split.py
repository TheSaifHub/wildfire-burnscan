"""
Evaluates candidate vertical/horizontal train/test split lines and picks the
one that gives both regions a reasonably balanced mix of MTBS severity
classes -- a lopsided split (e.g. all the severe burn on one side) would make
for an unfair, misleading test.
"""

import numpy as np
import rasterio

with rasterio.open("data/processed/mtbs_aligned.tif") as src:
    mtbs = src.read(1)

with rasterio.open("data/processed/baseline_severity.tif") as src:
    baseline = src.read(1)

# Same "valid" definition used for the baseline-vs-MTBS comparison: excludes
# our nodata edge strip AND MTBS's background/outside-perimeter pixels
valid = np.isin(baseline, [1, 2, 3, 4]) & np.isin(mtbs, [1, 2, 3, 4])

height, width = mtbs.shape
classes = [1, 2, 3, 4]


def region_class_counts(mask):
    return {c: int(((mtbs == c) & mask).sum()) for c in classes}


def balance_score(train_mask, test_mask):
    train_counts = region_class_counts(train_mask & valid)
    test_counts = region_class_counts(test_mask & valid)
    # worst-case (smallest) class count across both regions -- want this maximized
    return min(list(train_counts.values()) + list(test_counts.values())), train_counts, test_counts


print("Evaluating candidate splits (fraction = train portion):\n")
best = None
for axis, axis_name in [(1, "vertical (west=train/east=test)"), (0, "horizontal (north=train/south=test)")]:
    for frac in [0.4, 0.45, 0.5, 0.55, 0.6]:
        if axis == 1:
            split_at = int(width * frac)
            train_mask = np.zeros_like(mtbs, dtype=bool)
            train_mask[:, :split_at] = True
        else:
            split_at = int(height * frac)
            train_mask = np.zeros_like(mtbs, dtype=bool)
            train_mask[:split_at, :] = True
        test_mask = ~train_mask

        score, train_counts, test_counts = balance_score(train_mask, test_mask)
        print(f"  {axis_name}, frac={frac}: worst-case class count={score}")
        print(f"    train: {train_counts}")
        print(f"    test:  {test_counts}")

        if best is None or score > best[0]:
            best = (score, axis, axis_name, frac, split_at)

print(f"\nBest split: {best[2]}, frac={best[3]}, split_at_pixel={best[4]}, worst-case class count={best[0]}")
