"""
Tests whether applying MTBS's dnbr_offst correction (-3, meaning
corrected_dNBR = raw_dNBR - (-3) = raw_dNBR + 3) meaningfully improves
agreement with MTBS's ground truth, particularly for the High severity class
where our baseline showed the most overestimation.
"""

import numpy as np
import rasterio

DNBR_OFFSET = -3
LOW_THRESHOLD = 60
MODERATE_THRESHOLD = 301
HIGH_THRESHOLD = 570

CLASS_LABELS = {1: "Unburned/very low", 2: "Low", 3: "Moderate", 4: "High"}

with rasterio.open("data/processed/dnbr.tif") as src:
    dnbr = src.read(1)

corrected_dnbr = dnbr - DNBR_OFFSET  # raw_dNBR - (-3) = raw_dNBR + 3

nodata_mask = np.isnan(dnbr)

severity = np.full(dnbr.shape, 255, dtype=np.uint8)
severity[~nodata_mask & (corrected_dnbr < LOW_THRESHOLD)] = 1
severity[~nodata_mask & (corrected_dnbr >= LOW_THRESHOLD) & (corrected_dnbr < MODERATE_THRESHOLD)] = 2
severity[~nodata_mask & (corrected_dnbr >= MODERATE_THRESHOLD) & (corrected_dnbr < HIGH_THRESHOLD)] = 3
severity[~nodata_mask & (corrected_dnbr >= HIGH_THRESHOLD)] = 4

with rasterio.open("data/processed/mtbs_aligned.tif") as src:
    mtbs = src.read(1)

valid = np.isin(severity, [1, 2, 3, 4]) & np.isin(mtbs, [1, 2, 3, 4])
total_valid = valid.sum()

classes = [1, 2, 3, 4]
confusion = np.zeros((4, 4), dtype=np.int64)
for i, our_class in enumerate(classes):
    for j, mtbs_class in enumerate(classes):
        confusion[i, j] = ((severity == our_class) & (mtbs == mtbs_class) & valid).sum()

agreement = np.trace(confusion) / total_valid
print(f"Offset-corrected overall agreement: {100 * agreement:.1f}%  (uncorrected baseline was 44.9%)\n")

print("Per-class breakdown (offset-corrected):")
for i, our_class in enumerate(classes):
    row_total = confusion[i].sum()
    if row_total == 0:
        continue
    match_pct = 100 * confusion[i, i] / row_total
    print(f"  We said '{CLASS_LABELS[our_class]}' ({row_total} px) -> MTBS agrees on {match_pct:.1f}%")

# How many pixels actually changed class because of the +3 shift?
with rasterio.open("data/processed/baseline_severity.tif") as src:
    original_severity = src.read(1)
changed = (severity != original_severity) & ~nodata_mask
print(f"\nPixels that changed class due to the offset correction: {changed.sum()} "
      f"({100 * changed.sum() / (~nodata_mask).sum():.2f}% of valid pixels)")
