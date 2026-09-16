# Handoff — wayfinding, the short version, and the fold

Written 16 September 2026 to survive a context reset. **Nothing here is a source**: after
a reset it reads like something verified, and it is a claim about the repo. Check anything
load-bearing against the branch.

**Merged to `main` on 16 September (fast-forward, pushed), deployed by the 9:00 daily
refresh that day** — nobody ran a deploy by hand. `54f82336 Daily refresh, 2026-09-15` is
in the sequence because the cron committed that day's refresh onto the branch while it was
checked out; Cloudflare Pages put that day's deploy on a preview alias, not production, so
production skipped a day's refresh and caught up on the 16th.

`notes/process/READING-FLOW.md` is the design document this branch built to. Read it
first; this file is what a person needs to *continue*, not the argument.

---

## What the branch did, in one paragraph

A walk through the live site as three residents (a parent, a taxpayer, a board member) on
15 September found the pages good and the paths between them assuming the reader already
knew the map. So: every navigation is a real `<a href>`; the front page ranks its doors
and carries the projected gap; `/solutions` is listed and sits beside the crisis; caveats
moved to the foot of the pages they used to open; every page names itself in the browser
tab; meeting pages show posted roster names where the caption's hearing can be matched.
Then the length problem: every page shows an estimated reading time, counted from itself;
every page can declare a **short version** sized to one sitting, held to a five-minute
budget by a ratchet; and everything after the short version sits behind one control —
**the fold** — that says what it is and how long it is, and opens itself for any link into
it.

## The mechanisms, and where each lives

| thing | where | what to know |
|---|---|---|
| Real links | `fy28/src/lib/nav.tsx` | `<Go to="tab">` renders `<a href>`, routes in-app on a plain left click only. The router is a React context (`NavProvider` in `App.tsx`); no `onJump` props remain. **Every new navigation must be a `Go` or an `<a>`, never a `<button onClick={go}>`.** |
| Per-page `<title>` | `fy28/src/lib/title.ts` | App sets it in a layout effect from `LABEL`; `ReportShell` overrides from a passive effect for the routes that serve many pages. All 157 pages carried the site title before this. |
| Reading time on the page | `fy28/src/components/ReadingTime.tsx` | Counts text nodes under `#root` minus header/breadcrumb/footer/`[data-no-count]`, re-counts on a MutationObserver, 230 wpm. Renders on the breadcrumb row (App's `Breadcrumb`). Says **Reference** (with row count) for `REFERENCE` tabs and **Interactive** for `TOOLS` tabs — both sets in `routes.ts`. |
| The short version | `data-short` attribute | Set by `<Section kind="conclusions">`, every `<Conclusions>` block, `<ShortVersion>` (all in `components/report.tsx`), the crisis page's Upshot section, and raw `<section data-section="conclusions" data-short="">` on five pages. Counted once however the marks nest. |
| The fold | `fy28/src/components/FullVersion.tsx` | A native `<details>`; summary reads *Read the full analysis ↓ · 10 min* (its own word count). **Opens itself** on a `#hash` inside it, on a click of an in-page anchor whose target is inside (capture-phase listener — citation markers, "how this was worked out"), and on `beforeprint`. Carries an "On this page" contents list (numbered, two columns, `.toc-*` in `index.css`). |
| The table | `scripts/build_reading_time.py` → `notes/generated/reading-time.csv` | One row per prerendered route: words, minutes, `kind` (page/reference/tool, read off the build), `short_words`, `short_over_budget`, sections, `words_before_first_section`, `table_rows`. **Reads `fy28/dist`, so build first.** Registered in `check_generated.py`. |
| The budget | same script, `SHORT_BUDGET = 1150` | Five minutes — TJ: "each short page should be 5 minutes or less", a ceiling not a target. Enforced as a **ratchet**: a short version over budget may only shrink; one under may not go over; the writer **refuses to write** if a baseline would move upward (`--allow-growth` to do it on purpose, e.g. when a mark widens rather than the text). `--strict` also fails pages with none — not yet in `check_generated`; turn it on when the list below is empty. |
| Posted names | `scripts/build_recording_minutes.py` | Matches heard attendees to `sources/data/board-pages.csv` rosters — seat-like roles only, unambiguous only, and **only within the member's current term** (term expiry − 3 years). `posted_name`, `posted_role`, `matched_by` on each attendee; the heard form is always kept. Rendered in `pages/WhatWasSaid.tsx`. Under-matching is the safe direction. |
| Search titles | `scripts/build_search_index.py` | Page name from `<title>` minus the site suffix; H1 as fallback. **The index has not been rebuilt or synced** — do it at deploy (`build_search_index.py`, then `sync_search_d1.py`, inside the D1 write budget). |
| `/paras` | `routes.ts` | Slug for the paraprofessionals page; `/the-paraprofessionals` is an alias. `paras` had been an alias for `/school-staffing` — the routes comment records why that was overridden. `notes/process/PERSONAS.md` records the review under the new address. |

## The numbers as of `608b2f02`

From `notes/generated/reading-time.csv`, 81 prerendered routes:

- **45 pages declare a short version; 0 are over the five-minute budget; 13 declare none.**
  (16 September: the nine that were over were brought under -- see below.)
- The fold is on all 29 React report pages, `/crisis`, the six crisis-area pages, the
  three money reports, and any markdown analysis whose first `##` matches
  `SHORT_HEADING` in `pages/Analysis.tsx` (*The short version*, *What this establishes*,
  *In plain terms*, *What we now hold*, *Where things stand*).

**How the nine over budget were brought under (16 September).** TJ: "I thought we
agreed to make them all 5 or less." No prose was cut and no figure typed:
- Six report pages (`courses`, `class-size`, `which-grades`, `if-students-leave`,
  `other-districts`, `ch70`) show their **first three** findings on the card and the rest
  under *The other findings* at the top of the full version — `Conclusions` takes
  `short={false}`, and the payload's order decides which three. A generator that wants a
  different three reorders its conclusions.
- `/crisis`: the two objection cards, the three-panel picture and the closing card moved
  into the full version (`UpshotMore` in `components/Upshot.tsx`).
- `/the-situation`: its own `Conclusions` takes `from`/`to`; three on the card, fourteen
  in the fold.
- `/one-big-report`: a new short version — *The story in N figures*, one row per section
  with that section's headline figures — and the nine sections behind the fold.
  `Section` and `Conclusions` take `short={false}` there so the index does not count as
  the short version, which is how it measured 15,479 words.

**Which three are on the card (16 September).** TJ: "make sure whats remaining on all 5m
short cards are truly the most important things ... Things we want them to repeat in
public ... if they are supportive metrics that won't resonate ... it doesnt deserve to be
in the 5m short form." So every page with more than three findings now shows THREE, and
six pages name theirs by id in a `SHORT` constant at the top of the page component
(`splitConclusions` in `components/report.tsx`); the others take the payload's first
three. The choices, for pruning:
- `/cut-register`: the override took 13 positions off the list · 48 adopted cuts nobody
  can check · a cut list is a draft (3 gone in four weeks).
- `/lunenburg-by-the-numbers`: a third of homes have a child · a sixth of the town is
  65+ · ordinary on income, near the bottom on spending.
- `/homes-and-taxes`: value +101%, rate −27%, bill +48% · $7,444, 6th of 11 · the bill by
  when you bought.
- `/special-education-class-size`: eight to one · the rule is a minimum, IEPs add · 41 of
  258 substantially separate.
- `/which-grades-students-leave`: one grade does all the leaving · the leaving is nine
  times the fall · the gap is at one step. (The IEP rate, 34.7% vs 20.5%, is the fourth
  and arguably belongs on the card instead of "one step" — TJ's call.)
- `/what-other-districts-spend`: bottom quarter, 17 of 17 years · near the top on pay,
  fewest teachers · the districts our children leave for spend more.
- Left as the payload's first three: circuit breaker, enrolment, courses, if-students-
  leave, Chapter 70, and every page with three or fewer.

**No short version (13):** eleven markdown analyses that open with context rather than a
conclusion — `show-your-work`, `fy26-closeout`, `fy26-closeout-town`, `athletics`,
`athletics-ledger`, `questions`, `budget-vs-actual`, `sped-and-funds`, `what-you-can-ask`,
`peer-districts`, `fy27-and-the-override` — plus `/why-it-repeats` and `/athletics`. For a
markdown document the fix is in the document: a first section headed *The short version*,
and the page folds itself. Several of those openers (*What this rests on, and what it is
not*; *Why this is a separate document*) are rule 7a violations in their own right.

## Analytics (16 September)

Two layers, neither with a cookie or an identifier -- `fy28/src/lib/track.ts`:

1. **Cloudflare Web Analytics**, loaded by the app as a script tag (never zone-injected
   again -- that once altered archived HTML bytes). **Needs the site token** in
   `fy28/src/data/analytics.json` (`cfBeaconToken`); empty means nothing loads. Create
   the site in the dashboard: Analytics & Logs > Web Analytics > Add a site >
   lunenburgbudgetproject.org, and paste the token from the snippet. It is public by
   nature, so it lives in git.
2. **First-party events** -- `view` (with landing flag and referrer host), `door`,
   `fold_open`, `exit`, `search_zero`, `question` -- POSTed with `sendBeacon` to
   `functions/api/event.js`, written to the Analytics Engine dataset
   `lunenburg_site_events` (binding `EVENTS` in `wrangler.jsonc`; Analytics Engine, not
   D1, so the search sync and question inbox keep their write budget). Live the moment
   the next deploy carries the binding. `scripts/report_site_events.py` prints the funnel;
   **it needs an API token with Account Analytics: Read** in `CF_ANALYTICS_TOKEN` --
   wrangler's OAuth login does not have that scope (checked).

The prerenderer and headless checks are excluded (`navigator.webdriver`), and dev builds
send nothing.

## What is NOT done, in order

1. **Verify the 16 September deploy** (the daily refresh does build, sitemap, search
   index, D1 sync, deploy): `/paras`, `/the-paraprofessionals` (alias), `/solutions`, and
   that `/crisis#where-the-town-is` opens the fold; `version.json` should say built
   2026-09-16.
2. **The editing pass** on the 13 with no short version (above). Then flip
   `--strict` on in `check_generated.py`.
3. **The blog has zero published posts.** It is the site's built "faster read" format and
   `HomeLatest` renders nothing until one is published. See `notes/HANDOFF-BLOG.md`.
4. **Names on meeting pages**: only ~170 of ~1,028 attendees match, by design. Older
   meetings stay as heard because the roster is evidence only for the current term. If TJ
   wants more, the honest route is historical rosters from the annual reports, not a looser
   matcher.
5. `oxlint` is broken in `node_modules` (missing native binding) — pre-existing; `tsc` is
   the check that runs.
6. `check_generated.py` reports ~30 stale generators **from the 15 September refresh**,
   unrelated to this branch; everything this branch touches passes.

## Things that will bite

- **Never wrap a `Section`'s close inside a `FullVersion` opened outside it.** The
  rollout script got five pages wrong that way; `tsc` catches it (JSX nesting), so run it.
- **A `<details>` hides its content from `scrollIntoView`.** Anything that links into a
  page must go through an anchor or a hash so `FullVersion` sees it; a programmatic
  `scrollIntoView` from elsewhere needs to open the fold first.
- **`build_reading_time.py` measures `dist`.** A stale build gives a stale table and the
  `--check` will say STALE against the committed CSV. Build, then write, then check.
- **The Python and DOM word counts differ by a few percent** (different tag stripping).
  The on-page figure is the one a reader sees; the CSV is for triage. Do not "fix" one to
  match the other by typing.
- **The ratchet baseline is the committed CSV.** Running the writer with `--allow-growth`
  moves it; do that only when the *mark* changed, and say so in the commit.
- **The reading-time `<span>` is `data-no-count`** and so is the fold's contents list;
  anything else added to the chrome should be too, or it counts itself.
- The three "walk as a resident" screenshots and the `page.py` text-dumper live only in
  the session scratchpad; the method (headless Chrome `--screenshot` against a local
  static server over `dist`, `--dump-dom` to check `<details open>`) is cheap to redo.
