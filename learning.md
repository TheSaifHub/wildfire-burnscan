# learning.md — Blockers & Resolutions Log

Append-only log for Wildfire BurnScan (Wildfire Burn Scar Tracker).

Rules (per CLAUDE.md Section 7a):
- Updated at every "end."
- Logs any blockers hit that session and how they were resolved — or notes that they're still open.
- Include root cause when known, not just the symptom.
- Entries are never overwritten; this is a full history of what went wrong and what was learned.

---

## 2026-09-17 — FIRMS API rejected a 10-day query range

**Blocker:** `01_firms_pull.py` returned `400 Bad Request` when requesting
FIRMS detections over a 10-day window.

**Root cause:** FIRMS's area/csv API caps `DAY_RANGE` at 5 days per request —
undocumented in the parameter name itself, only found by checking FIRMS's own
API reference page.

**Fix:** Reduced `DAY_RANGE` to 5, starting 2018-11-06 (covers Nov 6-11,
comfortably spans the Nov 8 ignition date). Re-ran successfully, 2,261
detection points returned.

**Lesson:** check the actual API reference for hard limits before assuming a
parameter accepts any value — the API's own docs, not just the request shape,
should be checked first when a request looks reasonable but still fails.

---

## 2026-09-17 — Earth Engine direct-download 48MB request cap

**Blocker:** `getDownloadURL()` for a 6-band, full-resolution Sentinel-2 crop
failed with `Total request size (247636440 bytes) must be less than or equal
to 50331648 bytes`.

**Root cause:** Earth Engine's synchronous direct-download endpoint has a
hard 48MB response-size limit. A 6-band, 10m-resolution crop of our AOI was
roughly 5x over that limit.

**Fix:** Split the download into one request per band (6 single-band
GeoTIFFs per scene instead of 1 six-band GeoTIFF), each comfortably under the
limit. Bands get stacked back into one multi-band array in Phase 2 code.

**Lesson:** Earth Engine's direct download path is meant for small
crops/previews, not full-resolution multi-band exports of an area this size —
for anything larger than this, `Export.image.toDrive()` (async batch export)
would be the more scalable approach; direct per-band download was a
reasonable choice here given the AOI size but won't be if we work with bigger
areas later.

---

## 2026-09-18 — Ruled out: MTBS's dnbr_offst does NOT explain our High-severity overestimation

**Observation:** Our Phase 3 baseline (dNBR thresholded with MTBS's own
Camp-Fire-specific cutoffs) showed only 25.6% per-class agreement with MTBS on
"High" severity, and a disagreement map showed the overestimation wasn't
scattered randomly — it was heavily concentrated in one solid area right at
the core of the burn scar (the most totally destroyed ground, likely the town
of Paradise and its immediate surroundings).

**Hypothesis tested:** We built our baseline without applying MTBS's own
`dnbr_offst` calibration correction (-3 for this fire — the mean dNBR MTBS
measured over a known-unburned reference area, meant to correct for
scene-to-scene noise). Hypothesis: adding this correction back in
(`corrected_dNBR = raw_dNBR - (-3) = raw_dNBR + 3`) might close some of the
gap, especially near class boundaries.

**Result: hypothesis ruled out.** Applying the correction moved overall
agreement from 44.9% to 44.8%, and High-severity per-class agreement from
25.6% to 25.5% — statistically negligible. Only 0.78% of valid pixels changed
class at all. The offset (3 units on a scale where thresholds are spaced
60-570 apart) is simply too small to matter.

**What's still unexplained:** the core-concentrated overestimation pattern
itself is real and confirmed (via the disagreement map), but its actual cause
remains open. Leading candidates not yet tested: (1) the sensor/date-pair
mismatch between our Sentinel-2 pair (~3 months apart) and MTBS's own
Landsat-based pre/post pair (~1 year apart) noted earlier, and (2) dNBR's
known tendency to behave non-linearly in areas of near-total vegetation/
structure loss, where the index can saturate or respond differently to bare
soil/ash/urban char than to partially-scorched vegetation. Neither has been
tested yet — noted here as an open question, not a confirmed explanation.

---

## 2026-09-17 — Sentinel-2 "same tile" doesn't guarantee "same ground coverage"

**Blocker:** Picked Jan 13, 2019 as the after-scene based on it having 0%
cloud cover on tile `10TFK`. Export downloaded six suspiciously tiny
(~35KB) near-empty GeoTIFFs instead of the expected ~15MB files per band.

**Root cause:** Sentinel-2's MGRS tile grid cell (`10TFK`) is larger than a
single satellite pass's imaging swath. Different orbit passes tagged with the
same tile name can cover different slices of that tile. Jan 13's scene was
relative orbit `R013`, whose actual footprint sat entirely north of our fire
area (0% real overlap) — while the `R113` orbit passes (used for the before
scene and most other candidates) consistently covered 85% of our AOI.
Whole-scene `CLOUDY_PIXEL_PERCENTAGE` metadata reflects the whole scene
footprint, not overlap with our specific area of interest, so a scene can look
perfect on that metric while covering none of the area that actually matters.

**Fix:** Added an explicit AOI-vs-footprint overlap check (geometry
intersection area) before trusting any candidate scene, not just filtering by
MGRS tile name and cloud percentage. Re-ran the check across every Dec/Jan
candidate at once — cleanly separated into "all R013 = 0% overlap" vs. "all
R113 = 85% overlap," and picked Jan 25, 2019 (R113, 1.6% cloud, 85% overlap)
as the corrected after-date.

**Lesson for future scene selection:** verify footprint/orbit overlap with the
actual AOI *before* picking a candidate scene based on cloud cover or tile
name alone — not after a failed download. Cloud-cover metadata and tile
labels are necessary but not sufficient; a scene needs to actually cover the
target area to be usable regardless of how clean its metadata looks.

---

## 2026-09-18 — NumPy silently wrapped a negative sentinel value in a uint8 array

**Blocker:** U-Net training crashed on the first batch with
`IndexError: Target 156 is out of bounds` — a value with no obvious
connection to anything in the code (classes were only ever 0-3, or -100 for
"ignore this pixel").

**Root cause:** The label array was built as
`np.where(valid, mtbs - 1, IGNORE_INDEX).astype(np.int64)`, where `mtbs` is a
`uint8` array. `mtbs - 1` was computed as `uint8` arithmetic before being
passed into `np.where`, and NumPy's scalar-promotion rules then combined that
`uint8` array with the Python int `-100` by casting `-100` *down* into
`uint8` instead of promoting the array *up* to a signed type. `-100 mod 256 =
156` — an invalid class index that only surfaced once it hit PyTorch's loss
function, several steps removed from where the actual bug was.

**Fix:** Explicitly cast to a signed type before doing arithmetic that could
go negative: `mtbs.astype(np.int64) - 1` instead of `mtbs - 1`.

**Lesson:** when mixing an unsigned-integer array (common for raster/label
data straight from GeoTIFFs) with any negative sentinel value, cast the array
to a signed type *first*, explicitly, rather than trusting automatic type
promotion to do the sensible thing — the failure mode is silent (no
error, no warning) until the corrupted value happens to hit something that
validates its range, which can be arbitrarily far downstream of the actual
bug. Worth specifically checking dtype any time a raster/label array is going
to be combined with a negative number.

---

## 2026-09-19 — Nodata crop: assumed a uniform threshold, actual shape was a band

**Blocker:** A first attempt at cropping the black nodata edge out of the
Phase 4 output used a single threshold (>99% valid) applied independently to
both rows and columns. It crashed with `zero-size array to reduction
operation minimum which has no identity` -- no column ever cleared that bar.

**Root cause:** Assumed the nodata region was spread out geometrically (a
diagonal/rotated wedge) without actually checking. Measuring it directly
showed it was a contiguous horizontal band at the bottom of the image (rows
3332-3941) -- every column dips below any reasonable per-column threshold
because the band drags every column's average down uniformly, even though
almost the entire image (rows 54-3331) is otherwise ~100% valid.

**Fix:** Two-stage crop instead of one uniform check: find the valid row
range first (using the row-wise average, which cleanly separates the good
region from the bad band), then compute column validity *only within that
already-cropped row range* -- at that point columns cleanly separate too.

**Lesson:** don't guess the geometry of a data problem and pick a threshold
to match the guess -- measure the actual distribution (row_frac.min/max/
median, col_frac.min/max/median) first. The fix here was fast once the real
shape was visible, but the first attempt wasted a run assuming a shape that
wasn't there.

---

## 2026-09-19 — SQL INSERT placeholder count didn't match table column count

**Blocker:** `webapp/backend/seed.py` crashed with
`sqlite3.OperationalError: table fires has 20 columns but 19 values were
supplied` -- after already spending ~1-2 minutes re-running U-Net inference
over the full map (no checkpointing in that script, so the failure cost a
full re-run).

**Root cause:** Plain off-by-one -- the `CREATE TABLE` statement had 20
columns, the `INSERT` placeholder string (`?,?,?,...`) had only 19 `?`
marks, written by hand and miscounted.

**Fix:** Recounted both the column list and the placeholder string
explicitly and added the missing `?`.

**Lesson:** hand-counting placeholders against a column list is exactly the
kind of thing that's easy to get wrong silently -- worth deliberately
recounting both sides rather than eyeballing it, especially in a script with
an expensive, non-cached step earlier in the same run.

---
