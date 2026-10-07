# Handoff: a site build that only re-renders what changed

Written 7 October 2026 for a fresh session. **BUILT the same day** -- see "Done" at the end.

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

## Done, 7 October 2026 -- measured

`fy28/scripts/prerender.mjs` now reuses a page when every input it was SEEN to read is
byte-identical, renders the rest four at a time (`PRERENDER_JOBS`), prints one line per
page, and keeps its cache in `fy28/.prerender-cache/` (gitignored; `vite build` empties
`dist/`, so the cache cannot live there). `FULL=1` renders everything.

| build | rendered | reused | prerender step |
|---|---:|---:|---:|
| full, old serial script | 830 | -- | 36.5 min (781 routes) |
| full, 4 at a time | 830 | 0 | 20 min |
| nothing changed | 0 | 830 | 2 s (whole `build:site` 49 s) |
| `board-records.json` changed | 49 | 781 | 76 s |

The nothing-changed build was compared byte for byte with the full one: 841 of 841 HTML
files identical.

**What the design above missed: THE CLOCK.** A page's HTML also depends on today's date
("upcoming", "in 3 days", and now "not available" turning MISSING), which no file records.
The served shell carries a probe that wraps `Date` and `fetch`: a page that READS the clock
is reused only on the day it was rendered, one that fetches another origin never. The
first probe counted creating a Date as reading it -- d3-time makes two scratch Dates on
load, Cloudflare's beacon times itself -- and flagged all 830 pages; the second counts a
Date only when its value is used before a setter overwrites it, and ignores other origins'
scripts. 65 pages read the clock today, all of them the ones that show meetings.

**Checked for false negatives, not assumed:** every one of the 765 unflagged pages was
rendered again with the clock three days ahead and compared with the build: 0 changed.
The one difference was not the clock -- see below. The checker is not in the repo; it is
cheap to rewrite (render with `Date` shifted, compare visible text) and worth re-running
if a page starts showing a date.

**Found on the way: every prerendered page shipped `og:url=http://localhost:61348/...`**,
the build server's own address, because `setShareMeta` read `window.location.origin`;
`Subscribe` printed feed URLs the same way. Both now use `SITE` from `src/lib/abs.ts`, and
the prerender fails any page containing a `localhost:<port>` address.

Still open: 4 workers made a full render only ~1.8x faster than serial -- the next gain
there is not launching a fresh Chrome per page (one browser, many tabs via CDP), which is
a bigger change than this one and not needed while most builds are reuse builds.
