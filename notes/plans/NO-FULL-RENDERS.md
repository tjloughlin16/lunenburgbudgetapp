# No more full-site renders: the plan

TJ, 26 November 2026: *"we need to fix it so we don't go full builds. so create a plan that would
do that. include changes to unblock today's full site build that wouldn't lead to a site
rebuild. we're not doing a rebuild for this next deploy."*

**Status: plan only. Nothing here is built.** The merge gate (`scripts/check_full_render.py`)
stays off until step 5. Background and measurements: `notes/process/AVOIDING-FULL-RENDERS.md`.

## Why every page re-renders today

The prerender reuses a cached page only while one key shared by all ~3,900 routes is unchanged
(`fy28/scripts/prerender.mjs`, `global`, line ~564): the built `index.html` from `<html` on,
plus the probe, plus the prerender script's own text. The built `index.html` names the hashed
bundle (`/assets/index-<hash>.js`) and stylesheet, so **any byte of change in the bundle changes
every page's key**. That covers code, and also the two data files compiled into the bundle
(`fy28/src/data/sources.json` and `agent-manifest.json`), which the refresh rewrites most days.
Over 16-26 November, 66 of 149 commits would have caused a full render, 38 of them data-only.

What is already right, and the plan builds on it: **each cached page records the data files it
fetched while rendering, with their hashes** (`entry.deps`, checked in `whyNot()`). A page whose
data changed is already re-rendered on its own. The only all-or-nothing input is the shell key.

## Step 1: relink mode. Ships the waiting deploy with no full render

**Change, in `fy28/scripts/prerender.mjs`:** when a cached page's only failing check is the shell
key, do not re-render it. Reuse it and **relink** it: rewrite its `/assets/*.js` and
`/assets/*.css` references to the new bundle's names, splice today's preamble (as reuse already
does), and run the same `check()` every reused page goes through. The page then gets the new key.

Pages still rendered, as today:
- **never rendered before** (the 49 new closeout, tuition and town-office routes);
- **input changed** (any fetched data file differs from what the page was rendered with; this is
  how a page whose payload now uses a new block type gets re-rendered);
- reads the clock or another host; cached file missing or altered;
- **a named list** (`ONLY`-style, extended to add to the reuse set rather than replace it) of
  the pages whose own component changed in this deploy. For the waiting deploy that is the
  closeout hubs and tuition page (most already new routes) and `/sources`, the one page that
  renders the bundled `sources.json` (`components/SourceIndex.tsx`).

**What a relinked page can get wrong, stated plainly.** Its prerendered HTML was made by the
previous code. Anyone running JavaScript (nearly every reader) sees the new code the moment the
bundle loads, because React replaces `#root`. A reader **without** JavaScript (crawlers, some
agents) sees the previous layout of that page until it is re-rendered. The **data** is not stale:
any page whose data changed is re-rendered by the `input changed` rule. The exposure is layout
only, for no-JS readers only, on pages whose component changed (in this deploy, mainly topic
pages through `Topic.tsx` and `Blocks.tsx`). Step 3 bounds how long that lasts.

**The gate:** relinked pages are not renders, so the 100-page build gate does not trip. Expected
render count for the waiting deploy: the 49 new routes plus data-changed pages plus the named
list, roughly 100-200. If it exceeds the gate, the cause is a list of `input changed` paths,
which is a real finding, not a reason for a full render.

**Upload:** every relinked page's HTML changes (its asset names), so wrangler uploads ~3,900
small HTML files. That is upload, not rendering: minutes. If memory or upload trouble appears,
use the chunked upload in the existing deploy-upload memory.

**How it ships:** `RELINK=1` in the environment of the build `refresh.py --ship-only` runs (the
ship passes its environment through), then the normal deploy and the production sha256 check.
No `prerender_gate.py approve` is involved, and `FULL=1` is never set.

**Test, before use:** a fixture with three cached routes and a changed bundle name: an unchanged
page is relinked (not rendered) with the new asset names; a page whose dep changed is rendered;
a new route is rendered; a relinked page whose cached file was altered is rendered.

**Size:** a contained change to `whyNot()` and the reuse loop, plus the test. One session.

## Step 2: take the data out of the bundle (same deploy as step 1)

Move `sources.json` (read by `SourceIndex.tsx`) and `agent-manifest.json` (9 imports) from
`import` to a run-time `fetch` of `/data/<name>.json`, the way every report payload already
loads. `sources.json` already has a copy in `fy28/public/data/`; `agent-manifest.json` needs its
generator to write one there. The other eight files in `fy28/src/data/` are not rewritten by the
refresh (0-3 changes since 16 November) and can stay.

After this, a refresh that only changes data never changes the bundle, and the pages that read
those files track them through `entry.deps` like any other fetched file. **This removes 38 of the
66.** It is a code change, so it goes out in the step 1 relink deploy, not as a full render.

## Step 3: a rolling refresh instead of a full render

Relinked pages are marked (`relinked: <date>` on the cache entry). Each build re-renders the
oldest-marked pages up to a fixed budget (say 150 a day, under the gate) in addition to its own
work. ~3,900 pages turn over in under a month with no build ever rendering more than a few
hundred. This is the bound on step 1's no-JS staleness, and it replaces "approve one full render".

Optionally, a scheduled weekly pass with a larger budget, run at night through the refresh.
Still not a full render: the budget is the rule.

## Step 4: take the prerender script's own text out of the key

Every edit to `prerender.mjs` (comments included) currently invalidates every page. Replace the
script's text in the key with an explicit `RENDER_FORMAT` version, bumped only when the shape of
the output HTML changes. A bump is then a decision someone makes deliberately, and even a bump is
served by relink plus the rolling refresh rather than all at once.

## Step 5: arm the merge gate, redefined

Once steps 1-4 exist, a code change no longer means a full render. Narrow
`scripts/check_full_render.py` to what still would: `RENDER_FORMAT` bumps and the build config.
Then arm it (`ops/FULL-RENDER-GATE-ARMED`), so a full render can never land again without TJ's
`FULL_RENDER_APPROVED`.

## Not chosen, and why

- **Approve one more full render.** TJ: not for this deploy.
- **Code splitting per route** (lazy routes, a key per page's chunks). More precise for code, but
  a change across the app, and a shared chunk still invalidates everything. Revisit only if
  step 3's staleness ever matters.
- **A stable-named entry script** (`/assets/app.js` that loads the hashed bundle) so the shell
  never changes. It would end the HTML upload churn, but it needs no-cache headers for that file
  and still needs step 3 to refresh stale pages. Worth considering after steps 1-3.

## Order and ownership

Steps 1 and 2 together unblock the waiting deploy (the 43+ commits on main since the 23 November
build). Steps 3-5 end the problem. The task *incremental render* (T-HY3QY) covers this plan, and
TJ schedules it (26 November 2026).

## 27 November 2026: what "only the pages that changed" has to mean

TJ, 27 November 2026, declining a one-off deploy that rendered a fixed tier of pages: *"What I
was asking was not a one-time fix. I don't know why we have a full site deploy, we shouldn't. I
didn't change everything on every site recently, so I only want to deploy the pages that
actually changed, with clear content changes."*

**Measured against main at `d27591bba`** (a bundle build in a scratch export, the cache from
the 23 November full render, the reuse check patched to ignore the bundle): of 3,918 routes,
1,361 still re-render on whole-file data hashes, and most of those for a file every page of a
family reads: `boards.json` (288 board pages), `topics.json` (277 topic pages),
`boards-nav.json` (368), each person's JSON (440, where only a document count changed),
`searchable-pdfs.json` (117), plus 340 board pages that read the clock. Only 46 routes are new.
So step 1 alone is not enough. Detection has to be per page at two grains it does not have yet:

1. **Code: which source files did THIS page execute.** Record them while rendering, using Chrome's
   precise coverage over CDP (`Profiler.startPreciseCoverage`) mapped back through a hidden
   sourcemap to `fy28/src/**`, with each file's hash. After a bundle change a page re-renders
   only if a file it executed changed; otherwise it is relinked. The map is never deployed.
2. **Data: which part of a shared file did THIS page read.** The probe wraps `Response.json()` so
   the parsed value records the paths the page touched, and the entry stores a hash of those
   values instead of the file's. A board page that reads one board's entry is untouched by an edit
   to another board.
3. **The script's own text leaves the key** (step 4 above, `RENDER_FORMAT`), and the shell is
   keyed without its asset names, so relinking is the default on a bundle change.

**Seeding.** The 3,887 cached pages carry no coverage or read-paths. They were rendered before
any of this existed. The first build after this lands has to learn them, and learning a page
means rendering it once. That pass runs at low priority in daily batches while every other
page is relinked; until a page has been seeded, a change to any file in its route's static import
closure re-renders it. Nothing renders the whole site in one build.

## 27 November 2026: what was built

In `fy28/scripts/prerender-incremental.mjs`, wired into `prerender.mjs`, tested by
`fy28/scripts/test_prerender_incremental.mjs`:

- **The shell is keyed without its asset names**, and `RENDER_FORMAT` replaces the script's own
  text. A new bundle relinks every reused page (asset names rewritten one to one, or the page is
  rendered instead). Steps 1 and 4 above.
- **Live figures.** The footer's meeting-document count and each person's documents-searched
  count are `<span data-live>`, spliced with today's value into every shipped page; a rendered
  page must already carry today's value or the build fails, which proves the two formats agree.
  Pages cached before the spans existed are marked by their own sentences (`legacyLiveSpans`).
- **Read paths.** Each render records which values of each JSON file it read (a Proxy on
  `Response.json`), proved by recomputing every value from the file; the page re-renders only when
  one of those values changes. A write through the data, or over 20,000 reads, keys it on the
  whole file. Measured: a board page reads 2,554 values of `boards.json`, not the file.
- **Blobs.** The bytes of every JSON input, by sha256, so a page with no read record still counts a
  file whose only change is a live path as unchanged.
- **Legacy adoption**, once: `PRERENDER_ADOPT_LEGACY=<commit> PRERENDER_ADOPT_REPO=<repo>` adopts
  entries made before the new key, only if `fy28/index.html` from `<html` on is identical at that
  commit and now, and seeds blobs from that commit where each sha256 matches.
- **`searchable-pdfs.json` gains `has`**, so `SearchableLinks` looks up the PDFs a page links
  instead of reading the whole list.
- **The gate does not count up to 400 clock-reading pages** (they say "in 3 days" and change
  daily), and counts them again past that.

**Not built yet: code coverage per page** (requirement 4 of *incremental render*). Until it is, a
component change relinks the pages that use it, and a reader without JavaScript sees the previous
layout of those pages until they next render; `RENDER_ALSO=/a,/b` renders named pages as well.

Measured on main (`19a328f7f`, ship-shaped export, the 23 November cache): 2,587 of 3,963 pages
relinked with no render; 1,376 render once, because they were cached before pages recorded their
reads and a file each reads really changed in four days of refreshes.
