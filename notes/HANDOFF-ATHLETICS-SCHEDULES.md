# Handoff: athletics schedules, the bus model, and the site menu

Written 12 October 2026, before a context reset. Everything below is a claim about the repo
as of commit `496d9e06`. **Check it against the repo before restating it** (rule 13).

## State

| commit | what | deployed? |
|---|---|---|
| `b7c1baba` | Boards: hub and spokes, tab bar replaces sidebar | yes |
| `75bf48ff` | Site menu (`SiteMenu.tsx`), same map in every footer | yes |
| `5ce56a3e` | Menu change counts, New reports, Reports search category, threads link their reports | yes |
| `323608c2` | Transportation: contract year totals split into routes / trip lines / waiting | **NO** |
| `496d9e06` | Athletics schedules FY2022-FY2027, schedule-based bus model | **NO** |

**`fy28/dist` holds a finished, verified build of `496d9e06`** (1,627/1,627 prerendered,
`check_prerender.py` passes). The deploy was blocked by the auto-mode permission classifier,
not by anything wrong. TJ approved deploying it. To ship it:

    cd fy28 && PATH="$HOME/.nvm/versions/node/v22.22.2/bin:$PATH" npx wrangler pages deploy

Then check `/transportation` live: the new sections "the sheet and the posted schedules" and
"The FY2027 estimate against the posted schedules" should render.

The rest of the working tree's dirty files (`fy28/public/api/*`, `app-metrics`, `schema.html`,
`d1-pushed*`, `views/...`) are the daily refresh's, not this work's. Do not commit them as
ours. `notes/findings/OML-TRAINING-2026-09-23.md` is untracked from an earlier session.

## Hard constraints (TJ's)

- **No student names, no rosters.** Roster COUNTS only. Names are stripped at fetch time.
- Published text describes the robots behaviour neutrally ("The pages are not archived or
  republished").
- `scripts/fetch_arbiter_schedules.py` **refuses on robots.txt (exit 3)**. The data needed for
  analysis is held; ask before overriding it. Spring 2027 is one manual fetch next June, nothing
  recurring.
- Rule 10: deploy only when asked. NextLevel tags: `#appdev #lunenburgbudgetapp` + feature tag,
  never `#goalsetters`.

## What the data holds

- `sources/data/athletics-schedules.csv`: 2,752 games, FY2022-FY2027 (ArbiterLive, entity
  13354). Scheduled, not played.
- `athletics-schedules-coverage.csv`: which teams' schedules exist, by year.
- `athletics-venue-distances.csv`: 165 venues, 153 with OSRM round-trip miles from
  1079 Massachusetts Ave; 12 blank.
- `athletics-roster-counts.csv`: FY2022 only, 10 teams, 202 players, no names. Matches the
  district's FY2022 participation counts where both exist (Golf 16, Girls Soccer 43).

## Findings published in the transportation report (all scheduled games; dollars are OUR estimate)

- FY2025 at **FY2026 contract prices** (FY2025 rates are not held, which is a weakness): $140,719
  (shared bus per date+venue) to $189,118 (one bus per team-game). Miles alone are $46,599 to
  $61,198. The rest is the bid form's 4-hour waiting assumption, labelled as ours. The sheet says
  $91,066.
- Sports where the sheet is below even the cost of the miles: FY2025 Unified Track $355 (3 away),
  FY2025 MS Softball $677.50 (6), FY2024 MS Softball $985.50 (5), FY2025 HS Baseball $3,260 (19),
  FY2025 Boys Lacrosse $1,462.50 (14). Indoor track is the reverse: 14 amounts, 5 meets.
- FY2027 autumn, high school, like for like: home share **45.8% vs 53.9%** in FY2026. The district's
  "more home competitions" is not supported in autumn as scheduled. Winter as posted leans
  their way (54.1% vs 43.5%) but has not been played, so it is not counted.
- FY2027 full-year assembly: $120,296 to $165,633 against the district's $58,880. Miles alone are
  ~$36k-$49k, so their figure leaves ~1.1 waiting hours per shared bus.
- `money-gaps.csv`: the `trips` row was rewritten; two new rows (games in uncovered seasons; how
  the district built its FY2027 estimate). Closes: Dee Bus invoices FY2024-FY2026, per trip.

## Found AFTER the commit, not yet in the report. Next work, awaiting TJ's yes

1. **Rename "charges".** `sheet_charges()` in `scripts/build_transportation.py` (~line 842) counts
   each addend in a sheet cell's formula, e.g.
   `=(2310+577+...+485)/2` = 14. "Charge" presumes each addend is a bus bill. The sheet does not
   say that. Rename to "amounts in the formula" in the prose and the table.
2. **Amount count vs trip count, by year.** FY2024: addend counts track distinct away trips
   closely (Baseball 12/12, MS Boys Basketball 7/7, MS Field Hockey 5/5, Football 13/15,
   Golf 8/9, Girls Soccer 15/16). FY2025: 2-5 addends against 8-21 trips, and larger amounts.
   **Hypothesis:** FY2025 was billed in batches, not per trip. So "one charge" never meant one
   trip, and Unified Track's FY2025 $355 is likely a partial total.
3. **Same amounts in two rows.** FY2025 MS Track `=250+670+175+535+375+162.5+402.5` is the
   identical list behind HS boys and girls track (halved). FY2024 MS Track reuses HS track's 925
   and 1064. Shared buses, copying or double counting: the sheet cannot tell them apart. Rule 7.
4. **Proposed test, at no cost:** within each FY2024 sport, rank the addends and rank the
   scheduled away trips by distance, then see whether the orders agree (a rank correlation).
   It needs no FY2024 contract rates. If they agree, the per-trip reading gains support. If
   they do not, drop it.
5. Track: 7 addends against 1-3 scheduled away meets. Either invitationals are listed as neutral
   or home, or other trips were booked to track. Not checked.

Any of these needs a rebuild (~13 min) and a separate deploy approval.

## Other pending items

- **`athletics-fincom.csv` year mislabel:** rows from `participation-23-24-1.xlsx` store the
  fall-season calendar year as `fiscal_year` (2021 = fall 2021 = FY2022). A fix was offered;
  awaiting TJ. After fixing, re-run everything downstream.
- **Separate future reports TJ asked for, not started:** officials/umpires per home game;
  per-sport season cost with fees and programme value. Both build on `athletics-schedules.csv`.
- **Offer NextLevel filing** (one line, after the deploy): the site menu, change counts and New
  reports (`75bf48ff`, `5ce56a3e`); the boards redesign (`b7c1baba`); the athletics schedules and
  bus model (`323608c2`, `496d9e06`).
- Older offers still open: the week digest (last week / pick a week, not built).
- `check_generated.py` shows many STALE outputs from the refresh's uncommitted work (README,
  decisions doc, reading-time, short-versions, app metrics, money flow, town flow, schema, question
  bank, D1 sync and others). They are not this work's. Leave them to the refresh unless TJ says.

## Commands

    python3 scripts/build_transportation.py && python3 scripts/verify_transportation.py
    python3 scripts/build_reports_index.py --check
    cd fy28 && npm run build:site     # Node 22 on PATH; ~13 min; check `pgrep -f "[v]ite build"` first
    python3 scripts/check_prerender.py
