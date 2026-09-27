# decisions.md — Project & Technical Decisions Log

Append-only log for Wildfire BurnScan (Wildfire Burn Scar Tracker).

Rules (per CLAUDE.md Section 7a):
- Updated the moment a real decision is made — data source, architecture, library, phase approach — not only at "end."
- Each entry covers: what was decided, why, and what alternatives were considered.
- Entries are never overwritten or removed; this is a running history of how the project's direction was shaped.

---

## 2026-09-17 — Wildfire selection: Camp Fire (2018)

**Decision:** Camp Fire, Butte County, California (ignited 2018-11-08) is the
anchor wildfire for this project.

**Why:** Confirmed present in the MTBS database via direct query against MTBS's
official ArcGIS data service (apps.fs.usda.gov, EDW_MTBS_01 layer — the same
backend mtbs.gov itself serves from). Large, well-documented, high-severity
fire (destroyed the town of Paradise almost entirely), giving a strong, easy-to-see
dNBR signal for the baseline model in Phase 3. Falls well within Sentinel-2's
coverage window (launched 2015).

**MTBS record details:**
- MTBS fire_name: `CAMP`
- MTBS Fire ID: `CA3982012144020181108`
- MTBS-mapped acreage: 153,619 acres (CAL FIRE's official figure is 153,336 —
  small discrepancy is normal; MTBS maps burn extent independently from Landsat
  imagery rather than using the incident agency's perimeter)
- Ignition date: 2018-11-08
- MTBS's own reference scenes: pre-fire 2018-07-19, post-fire 2019-07-22

**Alternatives considered:** Dixie Fire (2021, CA — largest single fire in CA
history, ~1M+ acres), Bootleg Fire (2021, OR — ~414,000 acres, different
ecosystem), CZU Lightning Complex (2020, CA — smaller at ~86,500 acres, flagged
for likely coastal fog/cloud cover risk in Sentinel-2 scenes). Camp Fire chosen
for its severity/documentation combination and lower expected cloud-cover risk
around the fire dates (inland Sierra foothills, dry November) versus CZU's
coastal fog risk.

---

## 2026-09-17 — Before/after Sentinel-2 scene pair selected

**Decision:** Before scene = 2018-10-22, after scene = 2019-01-13, both on
Sentinel-2 tile `10TFK`.

**Why:** FIRMS detection points (2,261 total, pulled as an independent
cross-check on the fire's location/date) confirmed tile `10TFK` covers 99.7%
of the fire's actual extent (2,254/2,261 points; the remaining 7, all from
Nov 9, sit just south of the tile edge and fall into neighboring tile
`10SFJ` — the fire's southwest growth edge, not sensor noise). Both dates are
fully cloud-free (0.0%) on `10TFK`. The after-date search was widened from
an initial December window (best option: Dec 11, 11.2% cloud, only 16 days
post-containment) into January 2019 because 16 days was tighter than the
5-7 week smoke-clearing guideline set during planning. Jan 13, 2019 lands at
49 days (~7 weeks) post-containment (Nov 25, 2018) with 0.0% cloud cover —
satisfies both the smoke-clearing window and image quality.

**Alternatives considered:** Dec 26 initially looked best (4.5% cloud) but
that scene was on tile `10SFJ`, which was later confirmed to barely touch the
fire extent — ruled out once the correct tile was identified. Dec 11 (11.2%
cloud, correct tile `10TFK`) was the next-best pre-January candidate but
rejected for being too soon after containment. January candidates Jan 23
(0.7%) and Jan 25 (1.6%) were also nearly cloud-free but Jan 13 was chosen for
being both cleaner (0.0%) and closer to the 5-7 week target window.

**CORRECTION (same session):** Jan 13, 2019 turned out to be invalid and was
never actually usable. It's a different relative orbit pass (`R013`) than the
other 10TFK candidates (`R113`) — despite sharing the same MGRS tile label,
its real image footprint sits entirely north of the fire area (lat
40.05-40.64°N vs. our AOI's 39.60-39.95°N), giving 0% actual overlap with the
fire. This wasn't caught during scene selection because cloud-cover filtering
was based on whole-scene metadata, not footprint-vs-AOI overlap. Every other
`R013` candidate in the Dec-Jan search window has the same 0% overlap problem;
every `R113` candidate has a consistent 85% overlap.

**Revised after-date: Jan 25, 2019** (`R113`, confirmed 85% AOI overlap,
matching the before-scene's coverage exactly) — 1.6% cloud cover, 61 days
(~8.7 weeks) post-containment. This is about 1.7 weeks past the original 5-7
week smoke-clearing guideline, but the cloud-cover improvement over the
in-window alternative (Jan 10, 18.0% cloud, 46 days) was judged worth the
small extra delay. Before-scene (Oct 22, 2018) was explicitly re-verified as
`R113` with 85% AOI overlap to confirm it wasn't just assumed to match.

---

## 2026-09-18 — Skipped formal cloud masking for Phase 2

**Decision:** Skip cloud masking (via Sentinel-2's SCL band) for the Camp
Fire before/after pair.

**Why:** Both locked-in scenes already have very low cloud cover (0.0% before,
1.6% after) — confirmed via Earth Engine's `CLOUDY_PIXEL_PERCENTAGE` metadata
during scene selection. The SCL cloud-flag band was never downloaded (only
B2, B3, B4, B8, B11, B12 were pulled), so doing this properly now would mean
going back to Earth Engine for an additional band. Given how clean these two
scenes already are, the added complexity wasn't judged worth it for this
fire/date pair.

**Alternatives considered:** Pull the SCL band and mask flagged pixels
properly. Rejected for now as unnecessary given the low cloud cover, but
flagged to revisit if this project ever works with a cloudier scene where
cloud contamination could actually affect the NBR/dNBR results.

---

## 2026-09-18 — U-Net segmentation model confirmed better than baseline, including on the specific diagnosed weakness

**Decision:** The trained U-Net (3-level, 12-channel input = 6 before-bands +
6 after-bands, trained on 64x64 patches, west 60%/east 40% region-based
train/test split) is confirmed as a real improvement over the dNBR-threshold
baseline, and supersedes it as the project's working model going forward.

**Aggregate numbers (test region only, held-out):**
| Metric | Baseline | U-Net |
|---|---|---|
| Overall agreement | 44.9% | 60.7% |
| Unburned precision | 70.3% | 48.9% |
| Low precision | 59.6% | 70.2% |
| Moderate precision | 32.8% | 60.9% |
| High precision | 25.6% | 51.2% |

**Spatial pattern (test region only, same pixels for both):** Agreement rose
from 44.0% to 60.7% of valid test pixels; overestimation (calling something
more severe than MTBS) dropped from 39.2% to 23.9%; underestimation stayed
roughly flat (16.9% to 15.3%). Visually, the baseline's solid, contiguous
red overestimation blob at the fire's core broke up into a mixed green/red
pattern under the U-Net — the reduction is concentrated in the same area the
blob originally occupied, not just relocated elsewhere. This confirms the
U-Net addressed the specific weakness diagnosed earlier (a per-pixel threshold
rule cannot treat a pixel differently based on spatial context; a model that
sees neighborhoods can).

**Honest trade-off:** Unburned precision dropped (70.3% to 48.9%) — the model
became more willing to call areas "burned" at some severity, which helped the
burned classes substantially but cost some accuracy on genuinely unburned
ground. Net effect is clearly positive (+15.8 points overall agreement), but
not a uniform win across every class.

**Alternatives considered:** A per-pixel Random Forest classifier was
considered and rejected before building anything (see prior chat, not a
separate decisions.md entry) specifically because it doesn't use spatial
context, which is exactly what the diagnosed core-blob weakness needed.

---

## 2026-09-19 — Phase 4 output: U-Net as primary model, baseline as brief callout

**Decision:** The final Phase 4 map/stat output features the U-Net as the
primary severity map. The baseline appears only as a one-line validation
comparison (60.7% vs. 44.9%), not as an equal-billing second map.

**Why:** Phase 4's stated audience is a non-technical viewer who needs one
clear, correct answer, not two competing severity maps to parse. The
baseline's role at this stage is supporting evidence of rigor (it shows the
U-Net was validated against something, and beat it) rather than a co-equal
deliverable.

**Alternatives considered:** Showing both maps side by side as equal outputs
— rejected as adding visual clutter without adding clarity for the target
audience.

---

## 2026-09-19 — Phase 5 output format: write-up (README-centered), not notebook or live demo

**Decision:** Phase 5's polish/packaging output is a README-centered
write-up. No Jupyter notebook was built; the Phase 6 web app was treated as
a separate, later, explicitly-gated decision rather than folded into Phase 5.

**Why:** The stated audience (recruiter/PM) wants the story and result fast,
not to run code or interact with a live tool — a strong README with the
final image front-and-center plus `1.md`'s Q&A block is a complete portfolio
piece on its own. A notebook would be redundant given 22 already
well-organized standalone scripts, and notebooks render poorly/inconsistently
on GitHub compared to a README.

**Alternatives considered:** Notebook (rejected: redundant with existing
scripts, worse portfolio rendering). Live demo/web app as the Phase 5
deliverable itself (rejected: Section 10 frames the web app as its own later
phase with its own scope, not something Phase 5 needs to resolve).

---

## 2026-09-19 — Phase 6 backend/frontend architecture choices

**Decisions, bundled (all made during Phase 6 planning/build):**
- **SQLite via plain `sqlite3` stdlib module**, not an ORM (SQLAlchemy) —
  one table, unnecessary complexity for the current scale.
- **`scripts/` stays flat** (01-22, no pipeline/diagnostics subfolder split)
  — the README's script index provides the same navigational clarity without
  the risk/busywork of moving 22 files.
- **"Preset list" built as a genuine list-driven architecture** (API returns
  an array, frontend maps over an array), seeded with exactly one real entry
  (Camp Fire) rather than hardcoded for a single fire — no rearchitecting
  needed when more fires are added later.
- **Leaflet base-map + toggleable-overlay pattern** (real OpenStreetMap tile
  layer as base, before/after/severity as `ImageOverlay` layers via
  `LayersControl`) rather than three flat, non-interactive images — matches
  Section 10.2's "interactive map" requirement more genuinely.
- **Next.js: JavaScript (not TypeScript), Tailwind, App Router** — kept
  simple per Section 3's "correct and simple for a first-time learner"
  standard, avoiding TypeScript's extra layer for this project's scale.

**Why bundled into one entry:** these were all made together during a single
planning-then-build pass, not as separable standalone decisions each
requiring its own alternatives analysis.

## 2026-09-27 — Project renamed from "BurnScan" to "Wildfire BurnScan"

**Decision:** The project's display name is now "Wildfire BurnScan"
everywhere it appears as user-facing text or documentation (README, CLAUDE.md,
1.md, log file headings, web app home-page heading, browser tab title,
FastAPI title).

**Why:** User's choice of name. "Wildfire" spelled as one word to match the
existing "Wildfire Burn Scar Tracker" wording used throughout the project.

**Scope rules:** Internal names were deliberately left unchanged -- the
`burnscan` conda environment name (and every command that references it),
folder paths, script filenames, and database table names. Past entries in the
append-only logs (memory.md, decisions.md, learning.md) were not edited; only
each file's heading line was updated. The web app's browser tab title
(`layout.js`) was also replaced at the same time -- it still held Next.js's
default placeholder ("Create Next App").

**Alternatives considered:** "Wild Fire BurnScan" (two words) -- rejected as
inconsistent with the project's existing one-word "Wildfire" spelling.
