# handoff.md

Snapshot of current state. Overwritten each session — for full history see memory.md.

---

## Last session: 2026-09-19, 14:53 IST (2026)

### What was done
- Completed Phase 4 (visualization & output): final composite image
  (before/after RGB + U-Net severity map + honest stat block), cropped to
  remove the known nodata edge artifact, sized to eliminate layout dead
  space. U-Net chosen as the primary model shown; baseline appears only as a
  one-line validation callout (60.7% vs 44.9%). Confirmed done by the user.
- Completed Phase 5 (polish & packaging): `environment.yml` (corrected
  channels), `.gitignore` (excludes `.env` and regeneratable raw/processed
  GeoTIFFs, keeps PNGs + model weights tracked), README.md (drafted,
  reviewed in full, approved with no changes), final end-to-end recruiter
  Q&A block appended to `1.md`. Write-up confirmed as the Phase 5 output
  format (not notebook, not live demo). Confirmed done by the user.
- Started Phase 6 (web app): built a FastAPI backend (SQLite database via
  plain `sqlite3`, `GET /fires` + `GET /fires/{id}` endpoints, static image
  serving, CORS enabled for localhost:3000) and a Next.js + Leaflet
  frontend (landing/list page, fire detail page with an interactive map --
  real OpenStreetMap base layer plus toggleable before/after/severity
  overlay layers via Leaflet's LayersControl, positioned at the raster's
  real geographic bounds). User manually tested it in-browser (after I
  couldn't -- no browser tooling available this session, user declined the
  Claude in Chrome extension) and confirmed the layer toggle and image
  positioning both work correctly.
- **Phase 6 explicitly NOT done.** Section 10.3 requires deployment to
  free-tier hosting with a confirmed public link before the phase counts as
  complete -- only local dev servers have been run so far.
- Retroactively logged 4 decisions to `decisions.md` that were made in the
  moment during this session but not recorded until session close (U-Net as
  Phase 4 primary, write-up as Phase 5 format, and the bundle of Phase 6
  architecture choices).

### Current state
- **Backend:** `webapp/backend/` -- `app.py` (FastAPI), `seed.py` (one-time
  script: generates `static/fires/camp-fire/{before,after,severity}.png`
  plus geographic bounds, populates `fires.db`), `fires.db` (SQLite, 1 row).
  Run with `conda run -n burnscan uvicorn app:app --port 8000` from
  `webapp/backend`.
- **Frontend:** `webapp/frontend/` -- Next.js (JS, Tailwind, App Router).
  `app/page.js` (fire list), `app/fires/[id]/page.js` (detail page),
  `app/fires/[id]/FireMap.js` + `MapLoader.js` (Leaflet map, dynamically
  imported client-side only since Leaflet needs browser APIs). Run with
  `npm run dev` from `webapp/frontend`. Node v24.13.1/npm 11.8.0 already
  present on this machine.
- **Both servers currently stopped** -- user is running them manually in
  their own VS Code terminal per their preference, using the two commands
  above.
- **Not yet done:** any deployment. No Vercel/Render/Railway accounts or
  config have been touched this session.
- **Environment:** `burnscan` conda env now also has `fastapi` and
  `uvicorn` alongside everything from before.
- **Git:** still unresolved/deliberately deferred, unchanged from prior
  sessions.
- **skills/ and hooks:** still not set up (Section 6 first-week hold --
  project started 2026-09-17, now 2026-09-19, so still within the window;
  worth checking again next session).

### Next steps
1. **Deploy the backend** (Render or Railway free tier) and **the frontend**
   (Vercel free tier), per Section 10.2/10.3. Confirm it's actually reachable
   via a public link -- that's the explicit bar Section 10.3 sets before
   Phase 6 can be called done.
2. Before deploying, the frontend's hardcoded `API_BASE = "http://localhost:8000"`
   (in `app/page.js`, `app/fires/[id]/page.js`, and passed into `FireMap.js`)
   will need to become the deployed backend's real URL -- likely via a Next.js
   environment variable, not a hardcoded string. Flag this to the user before
   just hardcoding a production URL in its place.
3. Once deployed and confirmed reachable, close out Phase 6 with the user's
   explicit confirmation, then move to whatever's next (Section 5/10 don't
   define anything past Phase 6).
4. Re-check the Section 6 skills/hooks hold next session.
