# memory.md — Session Diary

Append-only running log for Wildfire BurnScan (Wildfire Burn Scar Tracker).

Rules (per CLAUDE.md Section 7a):
- One dated entry is added at every "end" — never overwritten, never edited after the fact.
- Each entry covers: what was completed this session, and what's currently in progress / left mid-task.
- This is a full history, not a snapshot. For "where do things stand right now," see handoff.md instead.

---

## 2026-09-17

**Completed:** Phase 0 in full (concept primer, Camp Fire selected and
confirmed in MTBS, GEE + FIRMS access, `burnscan` conda environment built).
Phase 1 in full (FIRMS cross-check pulled, before/after Sentinel-2 scenes
pulled and footprint-verified, MTBS ground-truth severity map pulled and
verified). Set up this file plus decisions.md and learning.md (new this
session, per Section 7a).

**In progress / unfinished:** Nothing left mid-task — both Phase 0 and Phase
1 were closed out cleanly this session. Phase 2 (preprocessing: aligning all
rasters to one grid/CRS, computing NBR) has not been started. One open
question for Phase 2 that wasn't resolved: how to reconcile Sentinel-2's 10m
native resolution with MTBS's 30m native resolution when aligning them to a
shared grid — needs a decision with the user before implementation.

---

## 2026-09-18

**Completed:** Phase 2 in full (raster alignment, NBR computation, cloud
masking explicitly skipped and logged). Phase 3 in full (dNBR baseline built
using MTBS's own fire-specific thresholds, compared against MTBS ground
truth, core-concentrated overestimation bias diagnosed via spatial
visualization, one hypothesis tested and ruled out, small U-Net built and
trained, confirmed via spatial comparison to have fixed the specific
diagnosed weakness). Both phases confirmed done by the user.

**In progress / unfinished:** Nothing left mid-task. Phase 4 (visualization
& output) has not been started. One open question not yet resolved: whether
Phase 4's final output should feature the U-Net, the baseline, or both side
by side — needs a decision with the user before starting Phase 4. Also
still open: whether the Section 6 "first week, no skills/hooks" hold has
elapsed and should be revisited.

---

## 2026-09-19

**Completed:** Phase 4 in full (final composite output, confirmed done).
Phase 5 in full (environment.yml, .gitignore, README drafted/reviewed/
approved, final recruiter Q&A block in 1.md, write-up confirmed as output
format). Both confirmed done by the user.

**In progress / unfinished:** Phase 6 (web app) started but explicitly NOT
done — backend (FastAPI/SQLite) and frontend (Next.js/Leaflet) are both
built and manually confirmed working locally by the user, but no deployment
has happened. Section 10.3 requires a confirmed public link before this
phase counts as complete. Next session's first task is deployment (Vercel
for frontend, Render/Railway for backend), including updating the frontend's
currently-hardcoded `http://localhost:8000` API base URL to point at the
deployed backend. Also still open: the Section 6 skills/hooks hold check
(project is now 2 days old as of this session, still likely within the
first-week window).
