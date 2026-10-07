# Handoff: a site build that only re-renders what changed

Written 7 October 2026 for a fresh session. Nothing here is built yet.

## Why

TJ, 7 October 2026, while the School Committee's emailed agenda waited on a full build to
reach the site the morning of its meeting: *"i think we need to figure out how to improve
the site build. it takes too long"* -- and *"we should only be regenerating the pages that
have changed."*

## What is true today (read from the code, 7 October 2026)

- `npm run build:site` = `tsc -b && vite build` then `node scripts/prerender.mjs`.
- `prerender.mjs` renders EVERY route (781 that day), ONE AT A TIME, each in a FRESH Chrome
  launched with `--dump-dom` and `--virtual-time-budget=10000`. Launch cost is paid 781
  times, serially.
- It already has `ONLY=route,route` (render just those) -- but nothing decides which routes
  changed, so nothing uses it automatically.
- It serves `dist/` from its own local server on port 8794 while rendering.
- Read the script's comments before touching it: the Chrome profile sweep (128 GB of
  leaked profiles once filled the disk), why `--user-data-dir` must NOT be passed (it made
  every route hit the 300 s timeout), the retry-once rule, and the shell-read hazard on a
  second run.

## The design

1. **Measure each page's inputs, don't guess them.** The local server already sees every
   request. Log which `/data/*.json` (and any other non-bundle asset) each route fetches
   while it renders, and write `dist/.prerender-deps.json`: route -> [file, sha256], plus
   the sha256 of the JS/CSS bundle (`dist/assets/*`). Route-to-data is then an observed map,
   never a hand-kept one.
2. **Skip what is provably unchanged.** On the next build: if the bundle hash is unchanged
   AND every dep of a route has the same sha256 AND the route's previous HTML exists ->
   reuse it. Otherwise render it. A code change re-renders everything (every page shares the
   bundle) -- correct, and the common case for data-only refreshes is the win.
   - A route never seen before renders. A route with no recorded deps renders (fail open).
   - Print the split: `rendered N, reused M (deps unchanged), forced K`.
   - `FULL=1` forces a whole re-render, for when the map itself is in doubt.
3. **Render several at once.** 3-4 concurrent Chrome processes instead of one. Keep the
   per-process timeout, the retry-once, and the profile sweep (sweep after ALL workers end).
4. **Do not break what reads `dist/`.** `check_prerender.py` (a MIXTURE of prerendered and
   not is a killed build -- a reused page IS prerendered, make sure the check agrees),
   `build_sitemap.py`, the search index, affinity, and `build_reading_time.py` all read
   `dist/`. Run each after a reuse build and compare with a full build's output.

## How to prove it

- Full build once (`FULL=1`), record the time. Change one data file (e.g. re-run
  `build_meeting_feed.py`), build again: only the routes that fetch `meeting-feed.json`
  re-render, and their HTML matches what a full build would produce (diff a reused build's
  `dist/` against a full build's, ignoring timestamps).
- Change one `.tsx` file: everything re-renders.
- `check_prerender.py` passes on both.

## Constraints from CLAUDE.md that apply

- The build is NOT parallel-safe across agents: port 8794 and a shared `dist/`. One build at a
  time; check with a pattern that cannot match itself (`pgrep -f "[v]ite build"`).
- Never a bare `vite build` into dist (it clobbers the prerendered dist).
- Deploying is rule 10: only when TJ asks. `npx wrangler pages deploy` from `fy28/`, Node 22.
