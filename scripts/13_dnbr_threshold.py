"""
Phase 3, step 1: compute dNBR and threshold it into severity classes, using
MTBS's own calibrated thresholds for the Camp Fire specifically (pulled from
MTBS's data service, fire_id CA3982012144020181108) rather than generic
textbook cutoffs.

dNBR = (before_NBR - after_NBR) * 1000   (the standard published scale)

Classes: 1=Unburned/very low, 2=Low, 3=Moderate, 4=High. Nodata pixels
(carried over from before_nbr.tif / after_nbr.tif) are written as 255.
"""

import numpy as np
import rasterio

LOW_THRESHOLD = 60
MODERATE_THRESHOLD = 301
HIGH_THRESHOLD = 570
NODATA_VALUE = 255

with rasterio.open("data/processed/before_nbr.tif") as src:
    before_nbr = src.read(1)
    profile = src.profile

with rasterio.open("data/processed/after_nbr.tif") as src:
    after_nbr = src.read(1)

nodata_mask = np.isnan(before_nbr) | np.isnan(after_nbr)

dnbr = (before_nbr - after_nbr) * 1000

severity = np.full(dnbr.shape, NODATA_VALUE, dtype=np.uint8)
severity[~nodata_mask & (dnbr < LOW_THRESHOLD)] = 1
severity[~nodata_mask & (dnbr >= LOW_THRESHOLD) & (dnbr < MODERATE_THRESHOLD)] = 2
severity[~nodata_mask & (dnbr >= MODERATE_THRESHOLD) & (dnbr < HIGH_THRESHOLD)] = 3
severity[~nodata_mask & (dnbr >= HIGH_THRESHOLD)] = 4

out_profile = profile.copy()
out_profile.update(count=1, dtype="uint8", nodata=NODATA_VALUE)
with rasterio.open("data/processed/baseline_severity.tif", "w", **out_profile) as dst:
    dst.write(severity, 1)

# Also save the raw continuous dNBR, useful for Phase 4 visualization
dnbr_profile = profile.copy()
dnbr_profile.update(count=1, dtype="float32", nodata=np.nan)
dnbr_out = np.where(nodata_mask, np.nan, dnbr).astype(np.float32)
with rasterio.open("data/processed/dnbr.tif", "w", **dnbr_profile) as dst:
    dst.write(dnbr_out, 1)

labels = {1: "Unburned/very low", 2: "Low", 3: "Moderate", 4: "High", NODATA_VALUE: "Nodata"}
total = severity.size
print("Baseline severity class distribution:")
for value in [1, 2, 3, 4, NODATA_VALUE]:
    count = (severity == value).sum()
    print(f"  {labels[value]:<20} {count:>10} pixels ({100 * count / total:.1f}%)")
