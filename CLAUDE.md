# CLAUDE.md — Wildfire Burn Scar Tracker (Wildfire BurnScan)

This file governs how Claude Code behaves in this repo. Read it fully before doing any work.

---

## 0. Project overview (plain words)

NASA gives you the exact location and date of a wildfire. You grab a satellite photo from just before the fire and one from just after, and your model highlights exactly which areas burned and how severely. It's "spot the difference" for fire damage, done automatically, using data real fire-monitoring agencies actually use.

**Why it matters:** governments, insurance companies, forestry/land management agencies, and researchers use this to map burn severity, plan recovery efforts, and assess damage — directly tied to real jobs in climate tech, geospatial analytics, disaster response, and insurance risk modeling.

**Data sources:**
- **NASA FIRMS** (Fire Information for Resource Management System) — exact fire detection points: lat/long, date, time, confidence, brightness. Free, web download or API (needs a free API key). This is what removes the guesswork — it tells you exactly where and when to look.
- **Copernicus Sentinel-2 (ESA)** — before/after imagery for the fire's location, pulled via Google Earth Engine.
- **MTBS (Monitoring Trends in Burn Severity)** — US government dataset with pre-labeled, expert-verified burn severity maps for major US wildfires. Free download. Used as ground truth to check your own results against.
- **CAL FIRE** (optional, if focusing on California) — official fire perimeter shapefiles, free.

**Difficulty:** moderate. Data collection is genuinely the easy part here since FIRMS hands you exact coordinates/dates. The harder, new concepts are: spectral bands beyond RGB (NIR, SWIR), NBR (Normalized Burn Ratio) and dNBR (the before/after difference used for burn severity), coordinate reference systems, and image segmentation vs. plain classification.

---

## 1. Who this is for

The user is learning ML/geospatial concepts for the first time on this project. Explain everything in plain words — someone with only a basic understanding of the project should be able to follow any explanation or summary and get the gist. No unexplained jargon.

---

## 2. Session control (hard rule)

- Do NOT start any work, read files, or make plans until the user types exactly **"start"**.
- Do NOT close out a session (write handoff.md, update 1.md, show the summary table) until the user types exactly **"end"**.
- If the user talks before "start," you can acknowledge or clarify, but don't act on the task yet.

## 3. Approval discipline (hard rule)

- No code, config, file, dependency, or architecture change without the user's explicit go-ahead first.
- Before any nontrivial step: state the recommended approach, briefly say why it beats the alternatives, then stop and wait for approval. Never just proceed.
- "Best approach" means correct and simple for someone learning this stack for the first time — not the cleverest option, not over-engineered.

## 4. Teaching style — hand-holding

- Tell the user exactly what to do, step by step. Don't assume prior knowledge.
- Before using a new concept (spectral bands, NBR/dNBR, coordinate reference systems, segmentation vs. classification, etc.), explain it in plain words first.
- Work through the phases below in order. Don't skip ahead. Confirm the current phase is genuinely done — with the user, not by self-declaring — before starting the next.

---

## 5. Project phases

Work in order. A phase is not "done" until the user says it's done.

**Phase 0 — Setup & concept grounding**
- Get Google Earth Engine access sorted, and a free NASA FIRMS API key if going the API route
- Pick ONE specific, well-documented wildfire to start — ideally one that's in the MTBS database so ground truth exists
- Plain-language primer before touching code: what a "band" is, what NBR/dNBR is, what a coordinate reference system is, why satellite images aren't just RGB
- Set up the environment (Python env, libraries) — confirm with the user before installing anything

**Phase 1 — Get the data**
- Pull the fire's exact location + date from FIRMS
- Pull two Sentinel-2 scenes for that location: one shortly before the fire, one shortly after (once smoke has cleared)
- Confirm cloud cover is low enough to be usable
- Download the matching MTBS burn severity map for the same fire, if available
- Export/save everything locally in a usable format

**Phase 2 — Preprocessing**
- Align all images (same resolution, projection, crop) to the same coordinate box
- Compute NBR for the before and after scenes
- Basic cleanup: cloud masking, normalization

**Phase 3 — Change detection (the core model)**
- Start simple: compute dNBR (before-NBR minus after-NBR) and threshold it into severity bands (unburned, low, moderate, high) — builds intuition and gives a baseline
- Compare this baseline against the MTBS ground-truth map — how close is it?
- Move to a real segmentation model only once the baseline works and is understood
- Compare the model against the baseline — is it actually better?

**Phase 4 — Visualization & output**
- Produce a clear before/after/burn-severity map
- Package it so a non-technical viewer (recruiter, PM) gets it immediately

**Phase 5 — Polish & packaging**
- Clean repo structure, README written for a general audience
- Write the final recruiter-level Q&A block into `1.md`
- Decide with the user whether this becomes a live demo, notebook, or write-up

---

## 6. skills/ and hooks — not yet

- No `skills/` folder for the first week of sessions. The workflow isn't settled yet; writing skills early just means rewriting them later.
- No hooks at all until explicitly asked about and confirmed by the user.
- After one week: stop and ask the user whether to lock in skills now. Only create `skills/` on a yes.
- Ask about hooks as its own separate question: "do we need hooks here, or is it overhead?" Add only what genuinely reduces the user's effort — never add either just because it's common practice elsewhere.

---

## 7. handoff.md (write only at "end")

Update `handoff.md` at the end of every session with:
- Date, time, and year
- What was done this session — factual, no padding
- Current state — what exists, what works, what's broken/half-done
- Next steps — specific, ordered, actionable

Purpose: a future session with zero memory reads this file and resumes work without re-asking where things stand.

---

## 7a. memory.md, decisions.md, learning.md (write at "end," decisions.md also mid-session)

Maintain three additional files alongside handoff.md:

- **memory.md** — append-only running log. At every "end," add a dated entry:
  what was completed this session, what's currently in progress (unfinished,
  mid-task). Never overwrite past entries — this is a full history, not a snapshot.

- **decisions.md** — append-only log of project structure and technical decisions.
  Update this the moment a real decision is made (data source, architecture,
  library, phase approach) — not only at "end." Each entry: what was decided,
  why, what alternatives were considered.

- **learning.md** — append-only. At every "end," log any blockers hit this
  session and how they were resolved (or that they're still open). Include
  root cause if known, not just symptoms.

If none of these files exist yet, create them on the next "start" with a brief
header explaining their purpose, then begin logging from that session onward.

**How this differs from handoff.md:** handoff.md is a snapshot — it gets
overwritten each session with only the latest state, so a fresh session can
resume fast. memory.md is a diary — every session gets appended, nothing is
ever overwritten. Both exist; they do different jobs.

---

## 8. 1.md — interview prep (write only at "end", if real work happened)

Rules:
- No yap. No restated context, no filler, no intro paragraphs. Straight to the point.
- Each entry: what was built/learned that session + the interview questions that map to it.
- Skip the entry entirely if nothing interview-worthy happened.
- At the very end of the whole project, add one final recruiter-level Q&A block covering the project end to end ("walk me through this project," "why this architecture," "what would you change," etc.).

---

## 9. End-of-session summary (shown in chat, only at "end")

Before writing handoff.md, post this table in the chat:

| Done this session | Next steps |
|---|---|
| ... | ... |

Keep it short — a recap, not a report.

---

## 10. Product / Web App track (added after core pipeline works)

This project isn't just a notebook + model — the end goal is a small, real, demo-able web app the user can show an interviewer or put on a resume/portfolio. Do not start this track until Phase 4 (Visualization & output) is genuinely working and confirmed by the user. Building the app on top of a shaky pipeline just means redoing it later.

### 10.1 What the app actually does (MVP scope)

- User picks or searches a fire event (or picks from a small preset list of 3-5 well-documented fires — don't try to cover every wildfire ever for v1)
- App shows before/after satellite imagery for that fire's location
- App shows the burn-severity overlay (dNBR-based, color-coded by severity)
- A short summary stat block (e.g., "X km² burned, severity breakdown: Y% high, Z% moderate")

Do not add more features than this for v1. A narrow, polished MVP beats a broad, half-working one — confirm this scope with the user before building past it.

### 10.2 Tech stack (confirm with user before installing anything, per Section 3)

- **Backend:** FastAPI — serves precomputed results (don't run live Earth Engine/segmentation calls on every request; precompute and cache instead)
- **Frontend:** Next.js or React, with Leaflet or Mapbox for the interactive map
- **Data storage:** SQLite or Postgres to cache processed results per fire event (fire name, coordinates, date, before/after image URLs, computed severity stats)
- **Hosting:** frontend on Vercel (free tier), backend on Render/Railway (free tier)

### 10.3 Phases (insert as Phase 6 in the existing sequence — Phase 5 "Polish & packaging" still comes first)

**Phase 6 — Web app build**
- Build backend endpoints first (serve cached results for each preset fire event) — confirm API shape with user before frontend work starts
- Build frontend: map/list view → fire event selection → before/after display → severity overlay
- Add the summary stat block
- Deploy to free-tier hosting, confirm it's actually reachable via a public link before calling this phase done

Same hard rules apply here as the rest of the doc: no scope creep past the MVP list in 10.1 without the user explicitly approving it, and this phase isn't "done" until the user says so — not on self-declaration.

### 10.4 handoff.md / 1.md

Sections 7 and 8's rules apply unchanged to this phase — web app work gets logged in handoff.md and interview-prep entries in 1.md exactly like any other phase, written only at "end."
