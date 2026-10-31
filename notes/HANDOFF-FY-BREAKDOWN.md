# Handoff: one fiscal year, broken down -- why a surplus happened

## NOW -- 30 October 2026, late. READ THIS FIRST; everything below is history

**State.** Committed, pushed and deployed (see Deploy below). Nothing from this session is
pending.

**Shipped this session:**
- `1e2bd2d82`: the preschool card says "2 teachers, 4 paras", counted from the roster's
  position titles. The build fails if a post is neither.
- `86daaf39e`: TJ decided to keep the March 2026 MUNIS reports public. The login they print is
  `kbarrett` (Karen Barrett, Town Accountant), in her official role. No takedown.
- `821d5f6fe`: **School lines against budget**, `/school-all-funds/budget-against-actual`
  (`scripts/build_budget_against_actual.py`, `bva-grid.tsx`, `bva-across.tsx`):
  - The grid has a **Usual year** column, the median of a line's years, and a filter chip.
  - **The rule (ours):** a line usually misses one way when its median is >=10% off its vote
    and >=$5,000 off, or >=$50,000 off either way, over >=3 years. Constants are `TREND_*`.
  - **"Lines that usually miss the same way"** is the same list: 24 of 288 lines, 15 over
    budget and 9 under. It replaced the August every-year test, which `book_years()` still
    checks.
  - The dot chart's **FY2021** is read from the Finance Committee workbook, starred, with the
    reason: the budget documents print the budget in the actual column (116 of 117 lines).
  - Every percentage says "over budget" or "under budget".
  - "What the school fund left unspent" is now the second chart.
  - `report.tsx`: a stated column gets an asterisk and one footnote, not "not from the books"
    under every heading. This applies to every table on the site.

**Open, for TJ:**
1. The $5,000 floor on the 10% route was added by this session. Without it, 135 lines
   qualify, mostly $300 supply lines. Keep it?
2. The axis says "over budget" where TJ wrote "overbudgeted". On this page, *Overbudgeted* is
   the O flag and means the reverse (voted more than spent). Confirm the wording.
3. Free cash: TJ wants it, but later. It is designed in `notes/PLAN-FREE-CASH-SECTION.md`, ON HOLD.
4. The records request (`notes/outbound/drafts/RECORDS-REQUEST-FY2026-CLOSE.md`) is unsent.
   The Town Manager's email address is not in the repo, and her Town directory page lists none.
   `jwarren@lunenburgma.gov` is unconfirmed; the "To" line on the 4 Sep request will settle it.

**Small queued fix:** `annual-report-receipts.csv` FY2021 PRE-SCHOOL TUITION reads 11.64; the
page prints $11,648.82. This is an extractor defect.

**Deploy:**
DEPLOYED 30 Oct 2026, `69b72501` (lunenburg-fy28), from `deb071a14`, pushed to origin/main.
Verified: the live `/data/topics/budget-against-actual.json` is byte-identical to the repo's.
Afterwards, every leftover file was committed at TJ's request (229 `views/` symlinks and the
audit-report text extracts). The working tree was clean.

## Earlier NOW -- 30 October 2026, end of day

**State.** Everything is committed on `main`, local, not pushed by this session. The site build and
deploy belong to the annual-reports session (`lunenburgbudgets-e4`). It has the list of commits and
will message before it builds. Do not run `npm run build:site`. A Vite dev server is running on
:8811 (TJ uses it). Leave it running. Commit by explicit path; other sessions have uncommitted work
in the tree.

**Live already** (e4's deploy 7a7d0950): the FY breakdown and its item pages, School lines against
budget (`/budget-vs-actual` points there), per-year flags, the preschool report, Town general fund.

**Committed 30 Oct, waiting for e4's next deploy:**
- `54eef74a4` and `85b879b78` -- **year signatures** at the top of the FY breakdown
  (`fy-signatures.tsx`, `signatures_data()`, `sources/data/fy-signatures.csv`). For each year:
  - **How it began:** the gap, the cuts and the override. FY2026 adds a free cash row: Article 12,
    $500,000, on a condition. The books' original budget equals the omnibus plus the $500,000; the
    generator computes that match and states it only when it holds.
  - **How it ended:** the figure as announced, beside our Left.
  - **Weak spots:**
    - The FY2023 and FY2024 endings come from machine captions only (SC 3 Sep 2025, 1:35:42 and
      1:36:18). Check them against the video.
    - The FY2023 and FY2024 beginnings: nothing found (registered gaps).
    - Override window: "the 12 months before 1 July" is our rule.
- `84d8b6531` and `67ee6e57b` -- **preschool**:
  - a "What kind of account this is" box. It says the tuition is a revenue line, not a revolving
    fund; it closes to the general fund each year; and the amount above plan is part of free cash.
    That last point is our reading of how free cash works; we have not seen the closing entry.
  - wording: "planned on", not "budgeted"; the lead reads "4.2 times what the Town planned".
- `c220bd8e4` -- **DESE chart of accounts and EOYR instructions** ingested
  (`sources/state-dese/`).
  - No preschool function or program code.
  - p103: a municipality's tuition receipts reduce net school spending.
  - Our working-copy EOYR FY2023 shows $43,058 on Schedule 1 line 30. Whether that is preschool
    is not established.
- `32db35ca5` -- `keystone-tuition-rates` added to `NOT_READINGS` in the annual-report map.
- `cc57a39bd`, `cea97f22b` -- **records request drafted, NOT SENT**:
  `notes/outbound/drafts/RECORDS-REQUEST-FY2026-CLOSE.md`. Ten items, one email:
  - A (outstanding from 4 Sep): revenue Account Detail incl. preschool 0100-01001-431900, revenue
    p13, transfer report, POs closed late, the journal's redaction log and spreadsheet.
  - B (new): Town GF p13, special revenue balances at the FY2026 close and at 30 June 2025, trust
    and agency, circuit breaker receipts Apr-Aug 2026, tax recap sheets FY2023-26.
  - Register row `2026-10-30-town-fy2026-close-and-outstanding` ("to send") in
    `notes/reference/records-requests.csv`. A Gmail-ready HTML copy was in the old session's
    scratchpad; rebuild it from the .md if needed. When TJ sends it, set `sent` and `status`.

**Withdrawn 30 Oct:** "no Town Meeting vote for the FY2026 $500,000". The vote is held
(`town-meeting-votes.csv`, 2025 article 12).

**TJ's decisions still open** (`notes/findings/FY-BREAKDOWN-AND-PRESCHOOL-2026-10-30.md` §7):
1. ~~MUNIS March 2026 reports print a Town user's login and first name.~~ **Decided: keep.** It is
   `kbarrett` / Karen Barrett, Town Accountant, in her official role. No takedown.
2. A free cash section on the Town general fund page?
3. ~~The preschool card: "2 teachers, 4 paras" instead of "6 posts"?~~ **Done, `1e2bd2d82`.**

**Small queued fix:** `annual-report-receipts.csv` FY2021 PRE-SCHOOL TUITION reads 11.64; the
page prints $11,648.82. This is an extractor defect.

**TJ is sending review feedback next.** Take each item as it comes. Small edits go to the
generator plus `--check`. Hand anything large to a subagent.

## START HERE -- 28 October 2026. For a NEW SESSION. Deployed (c9c3750fa), still hidden

This section stands on its own. Everything below it is history; where they disagree, this wins.

### NEXT SESSION STARTS HERE -- 29 October 2026, early. Uncommitted, undeployed

**Coordination, still binding until TJ lifts it:** another session (`lunenburgbudgets-e4`) owns the
site build and deploy -- do NOT run `npm run build:site`; tell it when changes are ready and its
deploy carries them. Do NOT run `build_db.py` until TJ gives the all-clear (that session is rebuilding
`lunenburg.db` with 2001-2010 rows). Commit by explicit path only; three sessions' work is in the tree.

**DONE 29 Oct (later session), uncommitted: the ego-web toggle and both line-page cleanups below.**
Toggle: `fy-ego-web.tsx`, chips Chart/Table, `localStorage['fy-ego-view']`, In/Out lists removed.
Memo chart stacked over its table. `PayerTraces` redrawn as stacked bars per payer; `trace_of`
emits `lines` (the payer's 3 largest other lines across ALL years, `TRACE_LINES`, ours) and per
year `by` / `others`, and fails if here + lines + others does not equal the year's total.
`build_fy_breakdown.py --check` current, verifier ties, tsc clean, rendered on a dev server.
**The third cleanup is DONE too (TJ approved, 29 Oct) -- and it was about the LEVEL-1 chart, not
the bridge.** TJ's "circuit breaker in various flavors" was the labels under "The plan and what
happened" (`fy-plan.tsx`): now ONE label per fund (name + total; parts only in the hover -- TJ
rejected sub-labels: "i dont want the subbullets"), set on a 35-degree slant, circuit breaker one
part (`cb.lines`, wherever spent). The figures table under it has a title and is centred. The bridge
kept its four steps; its labels are constant with the year's qualifier as `sub`, `means` the hover.
A three-step bridge (all CB vs offset) was built on a misread and reverted -- do not redo it.
**ITEM 0 BUILT, 29 Oct (committed with this note; not deployed).**
- Data: `scripts/build_fund_flows.py --check` -> `sources/data/school-fund-flows.csv` (written by a
  subagent, spot-checked: CB receipts are `posts_to=='actual'` CRP rows; IDEA 2814 FY26 has only a
  BUA budget posting, so $0 received is real; CB opening $426,893.23 equals the FY2022 annual
  report's CARRIED 6/30/2022 in `special-revenue-read.csv`, an independent third source).
- Page: block `fy-fund-flows` "Money in, money out" (`flows_data`), after the bridge: by payer,
  expandable to funds linked to their pages; received / moved / spent (paid) / received less spent
  / balance at 30 June / against the year before. Capital and other appropriations LEFT OUT (a
  capital article's vote is not a receipt in the journal: $0 received every year), said under it.
- Fund pages: `FundFlows` chart + table (`flows` in each fund file), balance a gap where unknown.
- OPEN: (a) `special-revenue-read.csv` holds the CB and other balances back to FY2019 -- the fund
  chart could reach back before FY2023; (b) the FY2025 annual report's balance column disagrees
  with ours in 17 funds (CB printed $333,494.89 = exactly the FY26 reclass entry 2026/12/000692);
  not established why; (c) `finance.json` stale from another session's inputs and D1 `money_gaps`
  one row behind (`sync_d1.py`, when the deploying session runs); (d) money-gaps row 312 (CB
  balance) can now be partly answered from this data.
**ITEM 1 BUILT, 29 Oct:** block `fy-big-changes` "The biggest changes from last year" (`big_changes`):
three lists (cost every fund / final budget / left), top 8 by dollars, % only off a prior year of
$10,000+ and never on Left (thresholds ours); line table gains a sortable "Change in what it cost"
column (`chg`/`t_chg` on each row). Lines matched by account, so a RENAMED line reads as new + gone
(rule 6) -- e.g. FY2026 "Kindergarten Aides/Regular" is "new this year"; not checked whether it is a rename.
**ITEM 2 BUILT, 29 Oct:** block `fy-sources` "Where each source's money went" (`sources_data`):
one horizontal bar per payer (capital left out), split by the 6 largest lines across all bars and
years (`SOURCE_LINES`, ours; fixed colours), every other line, same kind of work, on no line
(hatched); a tick at what it received (item 0's receipts) and the gap outlined; Dollars / Shares.
DEFINITION SPLIT, stated on the block: its SPENT is the page's (payments + owed at 30 June, in the
year ordered); Money in, money out is CASH. They differ by orders owed across a 30 June -- e.g.
ARPA 2595, $75,000 ordered Jan 2025, paid Sep 2025 (other grants FY2025 +$75,000 here).
**RELEASED, 29 Oct (TJ: "They don't need to be hidden anymore"):** fy-breakdown is on the
school-all-funds shelf (registry, first group + start page); /school-lines, /school-funds,
/school-groups lose noindex and are in the sitemap (`build_sitemap.fy_item_pages`), client-rendered,
not prerendered. topics.json and sitemap.xml are regenerated at build -- not committed here, because
the working tree's topics.json also carries another session's uncommitted athletics registry change.
**ITEM 3 BUILT, 29 Oct (a subagent; reviewed):** /school-all-funds/budget-against-actual, "School
lines against budget" (`build_budget_against_actual.py --check`; `bva-across.tsx`, `bva-year.tsx`).
Across the years FY2018-FY2026 first (budget documents vs journal, never added), then the year
picker; FY2023+ carries the three flags ($5,000 and 10%, ours); earlier years a banner. It asserts
its document-years figures equal the August `budget-vs-actual.json`. NOT YET DONE, TJ's go needed:
point /budget-vs-actual (`variance`) at it and put `budget-vs-actual` in UNLISTED; whether the
older `school-budget-against-actual` and `line-level-misses` topics merge into it.
**WITHDRAWN, 30 Oct:** an earlier note here said the workbook's TRANSFERS differ from the journal on 12
and 15 lines. Wrong -- our join took the `school_facilities` sheet's row, whose transfer columns are
blank. On the general-fund sheet transfers equal the journal on every line; the workbook's ACTUAL is
payments only (journal spent less orders carried into the next year). build_budget_against_actual
now asserts the tie.
**DEPLOYED, 29 Oct evening** (deployment 54f87d0c; verified by hash: budget-against-actual.json,
fy-breakdown.json and a fund file on production equal fy28/dist). Three `deploy_site.sh` runs had
failed at upload (~10,500 of 12,328, wrangler EPIPE/ECONNRESET): a failed attempt keeps nothing, so
every retry restarted at 9,015. Fix that worked: split build/deploy-stage into 3 hard-linked chunks,
`npx wrangler pages deploy <chunk> --branch upload-staging` each (all succeeded first try; a
preview branch never touches production), then `deploy_site.sh` uploaded 0 files and succeeded.

**PRESCHOOL BUILT, 30 Oct (a subagent; reviewed, committed, NOT deployed):** /school-all-funds/preschool,
/town-funds/general-fund (`build_town_funds.py`, `TownFund.tsx`), FY breakdown section "School money
that goes to the Town" (`fy-town-receipts`); shared reader `scripts/school_receipts.py`. No general-fund
preschool cost identifiable (build asserts no account or line names preschool; gap row added); IDEA
preschool 262/264/298; staff pay = annual-report roster x wage list, OUR match, totals only.
OPEN: (a) `annual-report-receipts.csv` FY2021 PRE-SCHOOL TUITION reads 11.64; the page prints
$11,648.82 (p25, by eye) -- fix the extractor; (b) FY2023 receipts page is a blocked 93 dpi scan;
FY2024 only a combined $150,100 from a slide; (c) TJ TO DECIDE: the FY2026 p09 MUNIS revenue report
(and the p09 expense reports) print a Town user's login and first name; they are ALREADY in the
public bucket; not registered in redactions.csv, not used by the page. Takedown or accept.

**TOP OF THE QUEUE (TJ, 29 Oct, late): PRESCHOOL TUITION -- a report, an FY breakdown section, and a
Town general fund page.** TJ: *"let's do a preschool report and put it in the school page. But I also
want the preschool money to go into the FY breakdown page ... it might have to be its own section to
show the additional funds. And I think we probably need a fund page slug for the town general fund
... it should work the same as the schools."*
- ESTABLISHED: families' preschool tuition is a TOWN receipt, never a school one. Town general fund
  0100, dept 01001, account 431900 "PRE-SCHOOL TUITION" (named so in `fincom-ledgers.csv`, FY2025
  local receipts; printed "PS TUITION" in the MUNIS revenue report). The school journal has NO
  preschool receipt in any fund, FY2023-FY2026, and none credited to an expense line (searched).
  So the school budget carries the preschool at FULL cost; the tuition offsets nothing on the
  school side (rule 11's trap inverted).
- DATA: `annual-report-receipts.csv` source 'PRE-SCHOOL TUITION', FY1987-FY2022 (public; several
  rows 'no check' -- read them by eye before quoting); `fincom-ledgers.csv` FY2025 (public FinCom
  doc); FY2026 to 31 Mar: `sources/town-ledgers/revenue/glytdbud-revenue-fy2026-p09-gf-all.txt`
  line 66 -- est $10,000, received $75,279.04 (752.8%). THAT FILE HAS NO ROW IN redactions.csv:
  MUNIS, so verify it safe (read every text field for a person) and register `publish` BEFORE
  building on it (rule 13e). FY2023-FY2024 receipts: look in the annual reports' receipts tables
  (the dataset stops at FY2022 -- check whether the FY2023-FY2025 editions print the line).
- The tuition RATE: School Committee votes it each year (e.g. FY2025: 2-day $1,897.11, 4-day
  $3,548.58, minutes 2024-02-07; FY2027 increase on the 2026-01-21 agenda). search_minutes.py.
- The COST side: the preschool's school lines (P.S./preschool sped, paras, the IDEA preschool
  grants 262/'IDEA (preschool)') -- from the FY breakdown model. Never net tuition against them as
  if the district did; show both, labelled (rule 11).
- ESTIMATE vs RECEIVED: the Town budgets this receipt low (FY2026 $10,000 vs $75,279 by March);
  the excess falls to free cash. Why it is estimated low is NOT established.
- DONE 30 Oct (subagent): DESE's Chart of Accounts and End of Year Report instructions FETCHED,
  through `ingest` (stage/secure, read back), described in `sources/state-dese/index.csv`:
  `dese-chart-of-accounts-2022-07.docx` (published `eoy/chartofaccounts.docx`, "Chart of Accounts
  — Criteria for Financial Reporting", last updated July 2022, sha 20f0f483), and
  `dese-eoyr-fy2023-printing-version.pdf` (`eoy/fy2023/printing-version.pdf`, pdf_kind digital,
  sha 44759524) beside the FY2025 printing version already held; crosswalks for FY2023, FY2024 and
  FY2026 too. DESE published no FY2024 or FY2026 printing version (both 404). WHAT THEY SAY:
  * NO preschool function code and NO preschool program column. The chart's 89 function codes
    (1110-9500) name none; Schedule 1's program columns are Regular Day, Special Education, Ch 74
    Vocational, Adult Ed and Other, Undistributed (FY2023 p9; FY2025 eoy25!A213-B225).
  * Preschool appears in exactly three places: Schedule 4 column 1, "3-5 Yr. Olds all placements
    (doe032-- 30 - 48)" -- SPECIAL EDUCATION only, by function (FY2023 p79; eoy25!E2182-E2186);
    Schedule 7 line 4020 "To and from Regular Pre-School" (p82-83; eoy25!D2255, D2277), and the
    Schedule 1 instruction that preschool transportation goes in Column 1, Regular Day (p28;
    eoy25!D683). So regular-education preschool spending is NOT reported separately: it sits in
    Regular Day by function. Only special education preschool (Schedule 4) and transport are split.
  * Tuition revenue: general fund lines 30-50 (30 "Tuition From Individuals") are "revenue earned
    as tuition payments for pupils tuitioned in" (p10; eoy25!D241, D284); revolving line 640 names
    adult ed, community school, summer school, out-of-district -- not preschool (p12; eoy25!D330).
    Preschool tuition is NOT named anywhere: registered in money-gaps (last row, 30 Oct).
  * Town-side receipt: a municipality's general fund tuition receipts REDUCE net school spending
    (p103, 603 CMR 10.06: "the school district's or municipality's general fund receipts for
    tuition received for students attending the district's schools"). Read, not inferred.
- CORRECTION to the line this replaced, which said Lunenburg's own End of Year Report is NOT held:
  the FY2023 and FY2024 WORKING COPIES are held and extracted (`scripts/extract_eoyr.py`,
  `sources/data/eoyr-schedule1/4/7.csv`) -- not the filed reports. In them: Schedule 1 line 30 is
  $43,058 in FY2023 and $0 in FY2024 (J17); Schedule 4 column 1 is $344,170 in FY2023 and
  $95,276 (grants only) in FY2024 (E1024); Schedule 7 line 4020 is $0 both years. Whether the
  FY2023 $43,058 is preschool tuition is NOT established.
- Wording updated to cite the held chart: check_function_crosswalk.py, build_coding_questions.py
  (REQUEST-CODING.md regenerated), build_ledger_structure.py (LEDGER-STRUCTURE.md regenerated).
  The chart does not settle the crosswalk -- it defines what a district REPORTS to the state, not
  how the Town codes its ledger -- but: 0300, 2310 and 2900 are not chart codes; social workers
  are 2800 (Psychological Services; EOYR-EPIMS crosswalk maps EPIMS 3370/3371 there) and
  adjustment counselors 2710, so the $369k at MUNIS 2710 / book 2900 is neither, by name.
- NOT ESTABLISHED, and do not write it: that the preschool has "no budget". No line is NAMED
  preschool; its staff are most likely budgeted inside Primary School lines ("P.S." = Primary
  School). The finding is that the budget does not SHOW what the preschool costs.
- BUILD: (1) report on the schools shelf; (2) FY breakdown section "school money that goes to the
  town" (preschool tuition first; look for others the same way); (3) a fund-page mechanism for the
  Town general fund, same shape as /school-funds/<slug> (a slug, history, received/estimate by year).
  Cost note: a full build ~1-2% of the week -- do it in a FRESH session.

**TJ DECIDED, 29 Oct (late) -- NOT YET DONE, do these next:**
1. SWITCH: /budget-vs-actual (tab `variance`, `BudgetVsActual.tsx`, aliases routes.ts ~l.592) opens
   /school-all-funds/budget-against-actual; `budget-vs-actual` into sources/analyses/UNLISTED.
   `_redirects` is ignored by Cloudflare -- do it in the app routing.
2. FY2018-FY2022 from gl-history.csv (FinCom workbook): YES, for transfers and the flags. (An
   earlier "transfers miss 12/269 and 15/265 lines" was our own join error -- withdrawn.)
3. MERGE the older topics `school-budget-against-actual` and `line-level-misses` into the new
   report if similar (TOPIC_MERGED in routes.ts).
4. RESTRUCTURE -- DECIDED (TJ, 29 Oct: "use your best judgment"; ours: yes): per-year flags move to
   the FY breakdown (block + every-line table filter); the report drops its year picker for a line x
   year grid FY2018-FY2026 linking each FY2023+ column to that year's breakdown. One question per
   page: the year's story there, the pattern across years here.
Then item 4 below (the year's signatures).

**QUICK CLEANUP FIRST (TJ, 29 Oct) -- small, do before item 0:** on every fund and line page,
"What it connects to" (`fy28/src/components/blocks/custom/fy-ego-web.tsx`) draws the chart and then
In / Out lists that repeat it block for block. TJ: *"i dont think we need the 'in' and 'out'
areas"*, then *"or put it as a toggle: chart vs table view"*. Build the toggle: two chips (`Chip`
from fy-shared, as the year picker), Chart default; Table = one table, groups In / Out (and the
between-awards arcs as a third group), each row the other end (linked to its page), the kind of
connection, the generator's amount text, in the chart's fixed order (kind, then name). Remember
the choice in localStorage inside try/catch. The table is also the chart's only text version --
the SVG is `role="img"` -- so the toggle is what keeps it reachable for screen readers. Strings in
`scripts/fy_items.py` (the index text), never typed in the component.

**QUICK CLEANUP, also first (TJ, 29 Oct) -- two more on the line pages (`fy-item-history.tsx`):**
- **"What the bills were for" (`LineMemoCats`): stack, do not split.** The chart and "Largest
  changes, by payee and kind of bill" sit side by side (`md:grid-cols-2`); the table is a long list
  and the pair looks odd. Chart full width, the table under it.
- **"Where its other payers went" (`PayerTraces`) is unreadable -- replace the bars.** TJ: *"VERY
  hard to understand. i cant figure out what the bars are saying."* The current card draws each
  year as one thin bar of the fund's school-line total, scaled per fund, darker where spent here.
  Replace with, per payer fund, a stacked bar chart by year (recharts, as `GroupSplit` already does
  on the group page -- reuse it): each bar is everything that fund spent on school lines that year,
  split into THIS line, its top other lines, and the rest. THIS line called out in a big way: the
  bottom segment, a strong colour, its amount labelled on the bar; the other lines muted shades,
  the rest grey; the same line keeps the same colour every year. Keep the arrived/left sentences
  above each chart and the top-other-lines links below. `trace_of` already emits `here`, `top`
  and `total` per year; add per-line amounts for the top lines across all years (a fixed set, so
  colours and order hold year to year -- object constancy, as the ego web).

**QUICK CLEANUP, also first (TJ, 29 Oct) -- the bridge ("From the plan to what happened"):**
TJ: *"'circuit breaker' shows up in various flavors. i dont know why. i think we should have 1
circuit brekaer line"*, then *"putting them at a slant i think will be possible and better to
visualize those sub labels"*. Cause: the bridge already has ONE circuit breaker step a year
(`build_fy_breakdown.py` ~line 1311, `cb_step`), but its LABEL is chosen by that year's sign --
"counted on and not charged" / "charged beyond what was counted on" / "which the book did not
count on" / "against a book not read yet" -- so the same bar is renamed as the year changes. Fix:
every step gets a constant short label ("Circuit breaker", "General fund", "Other funds, toward
school lines", ...) plus a `sub` field carrying the year's qualifier ("counted on, not charged");
`means` stays the tooltip. In the bridge component (fy28/src, `fy-bridge`), draw the label and the
sub-label as angled axis ticks (about -30 degrees, sub smaller and muted) so the long ones fit.
Same rule for the general fund step ("left unspent" / "spent past its budget" -> label constant,
qualifier in `sub`).

**QUEUED BY TJ -- build these next, in this order:**

0. **TOP PRIORITY (TJ, 29 Oct: "thats the top priority TBH more than the others"): revenue that
   went unspent, per fund and overall, and each fund's revenue against its spending over time.**
   TJ: *"if the school received circuit breaker money, or idea grant money, or fee money, or
   whatever, and didnt spend it, we need to show total revenue and total unspent revenue, overall
   and on a per-fund basis. this will flag if the school isnt spending what they are earning. And
   the year over year change of that will be importantt o call out too. and on the fund page ...
   revenue and expense chanrts per fund, to show if the accounts are being consistently drained
   and filed or if changes happen."*
   - **The data exists:** the school journal (`journal.py`; `J.is_revenue(account)`) carries each
     fund's receipts as credits to its revenue accounts, FY2023-FY2026. A first look (29 Oct, NOT
     verified -- revenue rows were not filtered to `posts_to == 'actual'`, so estimated-revenue
     budget postings may be mixed in) put the circuit breaker (2640) at receipts $415,750 /
     $301,589 / $608,818 / $325,970 against spending $494,968 / $466,296 / $498,451 / $337,499.
     Re-derive with the filter before any figure is used; reconcile to the MUNIS revenue reports
     where held (`sources/town-ledgers/revenue/`, `school-special-revenue-fy26-q3.csv`).
   - **Opening balances:** "unspent" across years needs each fund's balance at 1 July 2022.
     Candidates: `sources/town-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx` (one point,
     FY26 p09 -- back-cast with the journal and check it ties), `fund-balances-fincom.csv`,
     `PROVENANCE-special-revenue-funds.md`. MUNIS is held at the gate until verified safe (rule
     13e / memory munis-stays-private) -- check `redactions.csv` before building against any of it.
     If no opening balance exists, register the gap in `money-gaps.csv` (rule 7c).
   - **A BALANCE AT 30 JUNE IS A FACT. The award period is context, not a correction.** An
     earlier draft of this note called grant balances "falsely unspent" because an award (IDEA
     2813: $846,872 received FY2025, spent into FY2026) runs past the fiscal year. TJ, 29 Oct:
     *"'falsely unspent' is subjective. if the school is clamining the state isnt giving us enough
     money, but not spending funds in CB or idea grant, it changes the interpretation."* So:
     show received / spent / balance at 30 June BY FISCAL YEAR for every fund, grants included --
     that is the measurement. Beside it, as context only, the award's spend-by date (how long the
     money may still be spent) -- it explains time left; it never shrinks the balance. Rule 7: a
     carry-forward being planned is the district's possible explanation, a hypothesis unless a
     document says so. Rule 8: where the district says aid falls short, the unspent balance goes
     beside that statement as two facts and a question for the budget -- never as a charge.
   - **Shape:** on the FY breakdown page, a block "Money in, money out" -- per payer kind and per
     fund: received, spent, the difference, the balance where known, and the change from last
     year, ranked by dollars. On each fund page, a revenue-and-spending chart across the years with
     the running balance, so filling and draining show. Rule 1: receipts and spending are both
     actuals, so this is like for like -- but a budgeted revenue is never mixed in.

1. **A "biggest changes" table on the FY breakdown page.** TJ, 29 Oct: *"the hockeystick spending
   curve in collaborative tuition fund year over year needs to be called out in some way on the FY
   breakdown chart as its a big change. Im thinking either a specific table for 'big changes' (both
   biggest spend changes, biggest budget changes, or biggest unspent changes), or putting another
   column into the 'every line' table."* Recommendation: a block of its own -- three short ranked
   lists (all-funds cost, final budget, left), each line with its prior-year figure, this year's and
   the change, linking to `/school-lines/<slug>` -- plus a change column in the every-line table so
   it sorts. Rank by DOLLAR change with the % beside it (a % off a small base is noise: rule 6). The
   inputs already exist per line in `fy_items` (`line_hist`: voted, budget, spent, all_in, left).
   Emit from `build_fy_breakdown.py` as a block; strings in the generator; a prior year must exist.
2. **"Where the non-general-fund money went" -- NOW ONE CHART WITH ITEM 0's REVENUE (TJ, 29 Oct).**
   TJ: *"a viz that shows every non general fund source of funding, and show what it paid for in
   that year (the lines, funds, etc) as proportions, to show how each one of those sources was
   distributed that year ... a non-timeline related bar chart with x axis just being the source of
   spend and the y axis being stacked bars for each place it was spent, or a horizontal thing ...
   it would be ideal if we could also show the revenue and amount unspent on the same chart."*
   Recommended (agreed in principle, not yet seen by TJ): ONE HORIZONTAL STACKED BAR PER SOURCE,
   for the selected year (it follows the page's year picker). Bar length = revenue received that
   year (item 0's receipts). Segments = where it was spent: its largest school lines by name, then
   the rest, then "on no school line"; then a HATCHED segment for received-and-not-spent. Where a
   source spent MORE than it received (drawing down its balance), the bar runs past a tick at the
   revenue mark -- never cropped. A toggle: dollars / proportions (proportions make every bar the
   same length so distributions compare). A line keeps one colour across bars and years. Horizontal
   because source names are long. Data: `fund_on` in `fy_items.files` for the spending side;
   item 0's journal receipts for the revenue side; group by payer (`FB.payer`), with a way into
   each programme's fund page. Grants: the bar is the fiscal year's receipts and spending, per
   TJ's ruling under item 0 (a balance at 30 June is a fact; the award period is context).
   Rule 7: a source's distribution shifting is a measurement; why is not.

   The earlier text of this item, kept for its detail:
   **"Where the non-general-fund money went" section.** TJ, 29 Oct: *"analyzes the non-general-fund
   money we know relate to school lines, and give an analsyis of where that money went (which school
   lines were funded the most) and is that different than the year(s) before it ... calls out if
   grant money or state money or fees had a diffference in how they were spent from the previous
   year or even the average (if there is a clear trend)."* The data is `fund_on` in `fy_items.files`
   (fy -> payer label -> account -> amount, from the same expense rows every line page ties to).
   Group by payer kind (`build_fy_breakdown.PAYERS`: IDEA, other grants, circuit breaker, fees...),
   per year: top lines and their share; the change from last year; against the average where the
   series supports it. The worked example is the circuit breaker: private tuitions $484k (FY23) ->
   $0 (FY26) while collaborative went $11k -> $333k, and IDEA arrived on private in FY26 ($287k).
   Rule 7 on every sentence: a payer moving between lines is a measurement; WHY is a hypothesis.

4. **LAST IN THE QUEUE (TJ, 29 Oct): each year's SIGNATURES, as an executive summary at the top of
   the FY breakdown page.** TJ: *"There are some sort of signatures to every fiscal year that need to
   be included ... the surplus for the year. So it gets announced. If there's a giant surplus, then
   it becomes dramatic and everybody gets upset. And that, so we got to put that right at the top of
   the page as sort of like executive summary call out ... but there's also a beginning ... whether
   or not that year had a successful override, was funded by an override, how many cuts were
   announced if there was a deficit, the deficit amount announced ... It's mostly needed to make
   sure this page has all the context it needs for what a school's fiscal year did at the high
   level."* The END: the surplus as ANNOUNCED (who said it, when, the figure, beside our measured
   Left). The BEGINNING: the deficit announced, cuts announced (how many), override attempted /
   passed / funding the year. Sources: School Committee and Finance Committee presentations and
   minutes (`search_minutes.py`), the budget books, Town Meeting / election results. Rule 7: an
   announced figure is what someone SAID -- cite it as theirs, beside ours, never merged.

   **BUILT 30 Oct (subagent), not deployed:** `fy-signatures` custom block ("Beginning and end"),
   directly under the year picker; follows `useFyYear`. Generator `signatures_data()` in
   `build_fy_breakdown.py`; component `fy28/src/components/blocks/custom/fy-signatures.tsx`. It
   READS existing records rather than copying them: `stated-figures.csv` (FY2025 surplus),
   `stated-cuts.csv` (cut lists, counted by row), `budget-seasons/fy26.csv` (FY2026 gap and
   override), `dls-override-votes.csv` (a vote dated in the 12 months before 1 July -- OUR window).
   What only this block needed is in the new `sources/data/fy-signatures.csv`, including
   `searched` rows saying where we looked. Per year:
   - FY2023: no gap, no cut list found (spring 2022 SC minutes not held, only agendas; captions,
     FinCom minutes, the FY23 presentation searched); no override vote on the DLS register. END:
     nothing announced at the close (SC/FinCom/SB minutes + captions, mid-June 2023 to Jan 2024).
     The only figure is RETROSPECTIVE and CAPTIONS-ONLY: SC 3 Sep 2025, 1:35:42, "FY23 was
     1068.2675", read by us as $106,826.75 (matches the period-13 unspent). Check the video.
   - FY2024: same searches, nothing found at either end; captions SC 3 Sep 2025, 1:36:18, "FY24 was
     21577628", read as $215,776.28. Check the video.
   - FY2025: gap $1.5 million "made public at the November 15, 2023 School Committee meeting" (FY25
     budget update p40 -- the minutes of that day do not print it); cuts 9 with the override / 23
     without (override statement, April 2024); override PASSED 18 May 2024, $948,136, 753-664 (DLS).
     END: $582,115.44 (3 Sep 2025, memo read by the SC chair), then $603,885.97 (17 Sep 2025).
   - FY2026: gap $3,492,995 (Town Manager's target, 5 Feb 2025), restated $1,913,460 (12 Mar 2025);
     39 cuts (approved list, 12 Mar 2025); override $2,099,337 voted by Town Meeting 3 May 2025,
     never on the ballot. END: "approximately $470,000 to $600,000" unexpended, PRELIMINARY, the
     Town Manager to the Select Board, 1 Sep 2026 (minutes pp6-7; the update itself not held);
     and 29 Jul 2026 "well below" ~$600,000 (Business Manager). Update when the books close.
   - Two gaps registered in money-gaps.csv (FY2023/24 turnback at the close; FY2023/24 season).
   - NOT done: the $500,000 free cash for FY2026 (Article 12). WITHDRAWN 30 Oct: "the season file
     records only the SC's contingent acceptance" was a search that stopped early. The vote IS held:
     `town-meeting-votes.csv`, 2025 annual, article 12, 3 May 2025, Yes 123 No 45 -- $500,000 from
     Free Cash to the FY2026 school operating budget "only if voters fail to approve a Proposition
     2 1/2 override ... on or before November 15, 2025" (FY2025 town report p140). No Lunenburg
     override vote in the DLS register between 18 May 2024 and 16 May 2026. The school journal's
     FY2026 original budget is $26,287,474 = the $25,787,474 omnibus + $500,000 exactly -- so it
     appears to have been transferred (an arithmetic match, not a posting that says so). ADDED 30 Oct:
     a `free_cash` row in fy-signatures.csv; the generator states the books' match only when it holds. A real phone-width check
     (`check_phone_width.sh` builds, so it was not run here).

3. **A WHOLE DIFFERENT REPORT, BOTTOM OF THE QUEUE: school budget vs actuals, line by line over
   time (TJ, 29 Oct).** TJ: *"map over time the same info thats in the fy breakdowns, but focus
   entirely on the school lines that are over or under budget. identify the things where the
   lines had LEFTOVER. and we have to identify if adjustments were made midyear to reconcile, like
   money pulled in to fix a GAP (flag this as 'underfunded') or the money moved elsewhere
   ('overbudgeted'). we should also flag if a line had transfers and the budget was adjusted mid
   year, but the next years budget started from the higher line again (or higher than previous
   year spending). IOW, if a budget starts significantly higher than the previous year spending,
   that should be flagged."*
   - **READ FIRST: it partly exists.** `sources/analyses/budget-vs-actual.md` (Aug 2026, 735 lines,
     payload `fy28/public/data/budget-vs-actual.json`; generators `build_variance_charts.py`,
     `build_school_spending_topics.py`) is the older, document-level version. Decide with TJ
     whether the new report replaces it or becomes its line-level companion -- never a third
     version beside both (rule 7d: one renderer, many payloads).
   - **The data is the FY breakdown's own line rows**, FY2023-FY2026: `voted`, `transfers`,
     `carried`, `budget`, `before`, `off`/`on`, `spent` (payments plus owed), `left`, and
     `budget_walk` (`bw`: walk text, adj, flag) -- per line per year, already tied to the journal.
   - **Three flags, each a measured rule with its threshold printed (thresholds are OURS):**
     - **Underfunded:** transfers IN during the year to cover spending past the vote (voted <
       spent, transfers > 0). Report the gap and how much the transfers covered.
     - **Overbudgeted:** budget moved OUT mid-year, or left at year end (voted > spent; transfers
       < 0 or left > 0). Report what left the line and where it went where the journal says.
     - **Restarted high:** next year's VOTE starts above last year's spending by more than the
       threshold -- especially after a mid-year cut moved money off the line (the cut was not
       carried into the next budget). Compare the vote to the prior year's spending AND to its
       prior final budget; say which.
   - **Rule 1 is not broken here** -- this is a budget-vs-actual ANALYSIS, which rule 1 allows; it
     must never feed a projection. **Rule 7:** a flag is a measurement; why a line was over- or
     under-budgeted is a hypothesis, and the report says so on every flag. **Rule 8:** findings as
     what they mean for planning, never as what the district got wrong; credit lines that track.
   - **Rule 6 caution:** a line that goes to zero and reappears renamed produces false "restarted
     high" flags; check the year-by-year before flagging.

**Done in this session (29 Oct, early) -- all uncommitted; `build_fy_breakdown.py --check` current, tsc clean:**
- Popups: one header row (Open its page + Close); copy-link button and "its page" row links gone;
  pointer cursor on every button site-wide (`fy28/src/index.css`, Tailwind 4 resets it).
- "What it connects to" (`fy-ego-web.tsx`) ordered by kind then name, never by size.
- History charts moved to `fy-item-history.tsx` (one component, page + fund popup tab "Across the
  years"). Line history: per-payer spending lines + all-in; a budget-against-spending chart with a
  "Left in the budget" row under it (left = budget less the SCHOOL BUDGET's own spending, so it can
  exceed the gap to the all-funds bar -- private FY2026: $522,629 left vs $753,108 all-in).
- **Collaborative tuition FY2025/26 votes are NET of the circuit breaker** (books print gross then
  `Circuit Breaker ... -452,580`); `printed_plan` is passed into `fy_items` and the line draws the
  book's gross beside the vote. FY2023/24 books print no offset anywhere (searched whole books).
- Line pages: "Where its other payers went" cards (`trace_of`), "Who it paid / What kind of bill /
  How many bills" (`payees_out`, `KIND_BUCKET`), "What the bills were for" (`MEMO_CATS`, a keyword
  list, OURS, shown where it sorts >=50% of the money: 9 of 294 lines), "The published price"
  (`PAYEE_RATES`, FLLAC -> Keystone Key Program).
- **Group pages** `/school-groups/<slug>` (`GROUPS` in `fy_items.py`, route in `routes.ts`,
  `fy-items.ts`, `GroupPage` in `FyItem.tsx`): out-of-district tuition = the district's own category
  (private + collaborative). Small multiples per line (placements / budget+all-in / cost by payer),
  placement counts (`placement-counts.csv`, FY2026 not held), which line each fund paid, other moves,
  each-line table, both-added-together, payer cards. Member line pages and paying fund pages link to it.
- **Keystone (formerly FLLAC) rate sheets FY24-FY27 INGESTED** by a subagent: `sources/peer-districts/
  keystone-tuition-rate-sheet-*.pdf` (5, incl. an earlier FY24 upload), dataset
  `sources/data/keystone-tuition-rates.csv` from `scripts/extract_keystone_tuition.py`. Every
  Lunenburg FLLAC invoice FY25-27 is exactly 1/4 of the Key Program member school-year rate.
  `build_source_index.py` exits 1 on 507 PRE-EXISTING uncatalogued files (1991-2000 report CSVs and
  `search.db`), none from this ingest -- so `sources.json` was not regenerated. Fix separately.

**What the collaborative spike is, as established (rule 7 -- measurements only):** all-in $487,249
(FY25) -> $1,070,265 (FY26). Of the +$583,016: ~$160k more of NEXT year's tuition paid early
($189,277 of FY2027 Q1 invoices `27L2KEY1x` dated 30 Jun 2026), $58,708 owed at year end, ~$365k
FY26's own bills (+80%). Published price +4.2%; own-year tuition bills = ~9.6 years at the annual
rate vs 5.6 (FY25) and 4.2 (FY24). NOT established: that ~9.6 tuition-years is ~9-10 children --
the FY2026 annual town report (1 March 2026 count) settles it, and it is not yet held. FLLAC billed
one bundled invoice a quarter through FY2024 and per-student from FY2025, so invoice COUNTS are not
comparable across that boundary (an open idea: detect and mark "billed differently from here").

### Earlier: 28 October 2026, evening. Uncommitted, undeployed (another agent commits)

**Done this session (verify_fy_breakdown ties; build --check current; tsc clean):**
- **Rule a fixed** (`fy_breakdown.entries`, and its own route in the verifier): a journal that does
  not net is read one memo at a time; a memo is a move when its school and other sides go opposite
  ways (an accrual moves neither). Eight re-charges added, $111,000 FY2023/25/26 (Turkey Hill,
  fringe, stipends). Line files key a re-charge by (journal, memo). Audit groups 21 and 589 were NOT
  misses (21: Curriculum Adoption is outside the school scope; 589: grant-to-grant).
- **The web's between-funds arrows now point the true way** (`fy_web.py`): cost a fund gave away
  points out of it. Its assertion is now strict.
- **Payee and web files checked by a second route** (`verify_fy_breakdown.side_file_checks`).
- **RULE D WAS BUILT AND REMOVED. DO NOT RE-ADD IT.** TJ, 28 Oct: a correction is explicit and is
  followed (rule a), but *"we can't assume if it was done once, it is done always"* -- "we cannot
  assume the 344k from the 2k". It placed a grant account's other pay on the line one correction
  paired it with ($2,668 of evidence placed $343,772). Also double-counted pay later moved back.
  The 'no school line' pile stays unmatched, explained by the appendix.
- **Per-item pages**: `/school-lines/<slug>`, `/school-funds/<slug>` (`scripts/fy_items.py`, run by
  build_fy_breakdown; `fy28/src/pages/FyItem.tsx`; popups and pages share `LineBody`/`FundBody`;
  `fy-ego-web.tsx`). 294 lines, 45 funds; hidden like the parent (noindex, not prerendered, not in
  sitemap). Open: no page for the school budget as a fund; line names keep `.title()`'s
  "Superintendent'S"; Expenses/Analysis tabs on the page not clicked through.
- **Athletics**: /athletics/athletic-director fixed (TJ read the fee-fund row as "the fee fund paid
  the AD"; it now draws "looked for: none found" as an empty box) and leads with a salary line
  chart; fee-fund-ledger merged into /athletics/fee-fund-history (TOPIC_MERGED); money-gaps row on
  fee-fund balances rewritten; transportation.md's "balance is not known" corrected.
- **Cost moved between funds, award to award** (`fund_moves_between`, block `fy-fund-moves`, web
  kind `fund` drawn giver -> taker, a "Moved between funds" column and popup tab, programme pages
  show awards side by side). Entries with no school line are now moves, not spending. 32 entries
  FY2023-26; reversals marked.
- **Rule a reads one MEMO at a time** (TJ: the whole-journal split "seems to create accounting
  bugs"). Exception: in a journal that nets, memos that do NOT net alone are read together
  (2025/10/000604: substitutes' pay off four lines under one memo, onto the school health grant
  under another). A memo that nets alone is never pooled; nothing is shared by proportion across
  memos. Moved FY2023 payer splits only (~$27k over 15 lines); line totals unchanged.
- `check_generated.py`, 28 Oct evening: 36 stale, almost all from the database the 2021 backlog
  and other sessions rebuilt (D1, recording minutes, README, money flow...). Not regenerated here.

### Earlier: 28 October 2026, end of day

**Do first, not optional (TJ): fix the re-charge rule.** `fy_breakdown.py` rule a only counts a
`GEN`/`GRV` entry as a re-charge if its expense lines net to zero within a dollar. An audit found
**11 entries naming a school line on one side that the rule skips** because the amounts do not tie
one-to-one -- e.g. "genetic syst turkey hill": a security system charged to Computers-Purchase &
Lease, $40,867 moved against $40,000 onto grant #1192. Groups 125, 102, 300, 271, 363, 61, 164, 428,
209, 95, 589 (and part of 21) in `build/audits-2026-10-28/noline/verdicts.csv`. Fix in the model AND
in `verify_fy_breakdown.py` (its own route), then re-run every generator that reads the model
(`build_fy_breakdown.py`, `check_generated.py` once at the end). Expect Left by line to shift; the
period-13 tie must still hold.

**Then ask TJ (explained to him in plain terms, not yet decided): a fourth match rule.** Grants and
fee funds book payroll to accounts named for a KIND of work, often on function 0000/2000/2300, so
it lands on "no school line" even when it pays the same staff. The Town's own year-end corrections
keep moving that pay to and from specific school lines (e.g. "RECLASS SCHOOL MEMO 10/11/24-6"
took $219,367 off IDEA #240 support salaries: $108,181 onto E.S. Sped Paraprofessionals, $111,186
onto another IDEA year). Proposed rule d, OURS and labelled: place a grant/fee payroll account on
the school line(s) the Town's entries moved pay between it and. The audit's reading of all 770
no-school-line groups ($9,536,079, FY2023-26): same as a line ~$2.39M, possibly ~$2.36M (mostly
ESSER), own programme ~$4.53M (lunch, extended day, trips), not a line cost ~$0.26M. Figures are
the agent's, from `verdicts.csv` -- RE-DERIVE before any reaches a page (rule 2). The page already
carries a figure-free appendix, "Why grant money is hard to match" (TJ asked for it).

**`build/audits-2026-10-28/` is gitignored ON PURPOSE**: `noline/verdicts.csv` quotes memos, some
naming students (scholarships). Never commit it; redact before anything from it ships.
`fund1301/readings.csv`: the row-by-row read of every athletic fee fund posting FY2023-26.

**Built today, uncommitted (TJ has not yet said commit):**
- FY breakdown blocks: `fy-payees` (Who the schools paid: general fund paid / % / % kept after
  re-charges, our allocation), `fy-salaries` (three tabs: school salary lines, by fund, **Paid every
  pay period** -- steady pay outside the general fund, 8+ runs within 25% of the typical run, ours),
  `fy-web` (last block; badges for sources and other-fund share, every line shown, find box),
  `fy-plan` vertical labels, `fy-budget-changes` sortable, the appendix above. Files:
  `scripts/fy_payees.py`, `fy_salaries.py`, `fy_web.py`, `build_fy_breakdown.py`,
  `fy28/src/components/blocks/custom/fy-{payees,salaries,web,plan,budget-changes,shared,source-table}.tsx`, `index.ts`.
- `/school-all-funds/activities-fund` (`scripts/build_activities_fund_topics.py`, registry
  `school_all_funds.py`, in check_generated).
- By an agent: `/athletics/fee-fund-history` (`scripts/build_fee_fund_history_topic.py`) and
  `/athletics/athletic-director` (`scripts/build_athletic_director_topic.py`), registry
  `athletics.py`, in check_generated; 5 money-gaps rows. `fee-fund-ledger` overlaps the new
  fee fund page on FY2025 -- merging is TJ's call. money-gaps row 236 is partly stale (annual
  reports print FY2021-23 balances; a district file prints 30 June 2026).
- money-gaps: rows appended today (activities fund, AD gaps); `topics.json` regenerated.

**The athletic director, settled as far as the records go** (for anyone who meets the question):
the AD's own account was general fund only FY2023-26; no fee-fund row names or pays the AD. What
TJ remembered is real: the FY2026 budget built the AD line NET of a planned $20,407 fee-fund
offset (Town Manager target budget, `Athletic Director 92,455 94,813 94,813 74,406`; SC 16 Apr 2025
video 9608s), which the books never carried out. The fee fund's regular per-run slice is HOURLY
($23.77, then $24.72), most likely the part-time athletic secretary (hypothesis). FY2025's $13,692
onto H.S. Principal/Asst Principal is that year's non-stipend fee-fund pay. Open: which line paid
the AD FY2011-17 (budget printed $0; wages ~$97-112k). TJ: the AP/AD split was "a 1 year thing
for 1 of the athletic directors. the paid from athletic fee fund goes beyond that" -- so the
pre-FY2023 years are where to keep looking.

### Added 28 October 2026 (later session). Not committed, not deployed

- **`fy-web`, "How the funds and lines connect"** (TJ's BAG: "every school line is a block. every
  fund / source of money is a block ... directional lines"). Hand-written SVG canvas, no library:
  funds left, lines right by category, sinks (no line / capital / between funds) under them.
  Arrows are `m['src']` placements, nothing new (`scripts/fy_web.py`, asserts each fund's arrows
  carry its placements). Budget transfers dashed, only where one side is one line. The school
  budget's own spending per line is OFF by default (it buries the rest). Drag, +/−/Fit,
  ctrl+scroll; a block focuses its arrows and lists them. Data: `fy-breakdown/web-<year>.json`.
  First pass: works, readable. Untested by TJ. Ideas not built: search a block, open the line
  popup from the web, a force layout.
- **`fy-payees`, "Who the schools paid"** (`scripts/fy_payees.py`): every payee paid by INVOICE
  in the year, every school fund, against the year before, change, New / Not paid this year, a
  popup (what was bought, lines and funds, every payment). `payees-<year>.json`, ~850 KB each.
  Grain stated on the block: invoices only, so health premiums the Town charges by journal entry
  are not in it (MIIA shows -$875,596 FY2026, which is NOT a cut). Payee identity is
  `journal.vendor_key`; masked names are one row and never "new".
- **`fy-payees` general fund columns**: General fund $ and % (fund 0100 paid the invoice), and
  **% kept** after re-charges -- OUR ALLOCATION: each school line's re-charged share applied to every
  payment on it (re-charges post to lines, not invoices). Budget transfers do not enter; moves back
  are a summary total, not spread. FLLAC FY2026: 100% paid, 72% kept.
- **`fy-salaries`, "Salaries paid outside the general fund"** (`scripts/fy_salaries.py`): by school
  salary line (pay moved off/back by journal entry, both ends named; share moved) and by fund
  (moved / same kind of work / no school line / other). Pay = `build_pay_by_fund_topics.is_pay`;
  each year TIES to that page's model and FY2026 gives its published 6.4%. Grant payroll cannot be
  pinned to a line (accounts name a kind of work). Links to the two pay pages. Every column has an
  ⓘ definition. BY FUND is split by HOW pay got there (TJ: "unclear if these payments paid back the
  general fund, or the salaries were not originally put onto the general fund"): own pay run /
  moved by journal entry, net / other entries. Moves are ONE NET per fund on purpose: the model
  shares a multi-fund entry over funds by all they received, so "came off the school budget" per
  fund would be our sharing. The exact school-side totals (re-charged off / moved back onto school
  salary lines) are in the summary. A re-charge is not a payment back: it moves the expense.
- `fy-web` lines carry two marks (TJ: "draw attention to lines that have a lot of connections or BIG
  connections"): a badge counting funds other than the general fund (filled at 3+) and a bar + % of
  the line's cost other funds paid (strong at 25%+). Thresholds OURS, said in the key. "Order lines
  by" size / sources / share. EVERY line shows by default, the general-fund-only ones tagged so
  (TJ: "thats good info"); a find box shows and focuses any block; the panel lists ALL of a
  block's arrows, drawn or not.
- Vocabulary, one set across payees and salaries: General fund paid / General fund kept / % kept.
- `fy-web` is now the LAST block and sized to the whole web (TJ: it was cut off; too detailed for
  the middle of the page).
- `fy-plan`: the legend became vertical labels under each segment (TJ asked), a fund's on/off-line
  parts share one label, and it falls back to a wrapped list when they do not fit (phones).
- `fy-budget-changes`: sortable headers (Show all applies after the sort).
- `Chip` and `Bars` moved into `fy-shared.tsx`.
- **Fund 1305 became its own page, not a callout here** (TJ): /school-all-funds/activities-fund,
  "After-school activities fund", `scripts/build_activities_fund_topics.py`, in check_generated.
  Named by the Town's name ON PURPOSE: the $70 student activity fee may not be deposited in 1305
  at all (the district keeps student activity accounts off the Town's books). Ties both sides to
  the period-13 report (interest is the only income difference). New money-gaps row.
- Not verified by a second route: the payee and web files (the generator asserts their sums;
  `verify_fy_breakdown.py` does not read them yet).
- `check_generated.py` full pass, 28 Oct morning: the FY-breakdown family all passes; 24 other
  checks stale, from other sessions' work (2021 meeting backlog, README, D1, money/town flow).

**First, in order:** load the `building-a-page` skill; read this section; run
`python3 scripts/check_generated.py` ONCE (the category split -- nurses/reserve/details -- was never
followed by a full pass, so other generators such as `build_db`, `build_show_your_work` may be
stale); re-run the model before quoting any figure (rule 2). On 28 Oct `build_fy_breakdown.py
--check` printed "current" and `verify_fy_breakdown.py` "1066 lines in 4 years, every part
recomputed and tied to the period-13 report".

**What the page is.** /school-all-funds/fy-breakdown, `?fy=FY2025` picks a year (FY2023-FY2026).
A hidden draft: the address works, on no shelf, not in topics.json or the sitemap. TJ's framing:
*"watching the money cross boundaries is really what we're trying to represent here. This is a
money relationship page more than anything."* Boundaries = fiscal years and funds. It is a
TEMPLATE: a year unlocks itself from the data, never by hand.

**Blocks, top to bottom** (`page()` in `scripts/build_fy_breakdown.py`, ~line 959; components in
`fy28/src/components/blocks/custom/fy-*.tsx`, registered in `index.ts`):

| block | what it shows |
|---|---|
| `fy-year-picker` | the year (in-flow only; the pinned floating copy was removed -- TJ: "awkward to see at all times") |
| `fy-plan` | plan bar vs What happened bar, in dollars, FROM ZERO; unspent OUTLINED at the end of What happened (TJ chose that spot) |
| `fy-bridge` | plan -> what happened as a bridge, its own section, same width as fy-plan, from zero |
| `fy-year-line` | money across 1 July and 30 June; each crossing ties to the other year to the cent. FY2026 prepaid $189,276.75 of FY2027 collaborative tuition |
| `fy-year-weeks` | every week, bars by fund/kind |
| `fy-budget-changes` | lines whose final budget differs from the vote: voted, transfers, carried, final, change; top N + Show all; popup lists the transfers and the other side of each |
| `fy-line-table` | THE big table TJ likes; popup per line (Summary / Transfers / Expenses / Analysis), flag and walk inside |
| `fy-line-funds` | School lines other funds paid: one row per line, largest first, popup; against the vote, against the final budget, changed after the vote |
| `fy-source-table` | What other funds paid for, by fund ("Kind of fund"); popup "What it bought" shows memo, paid to, and "No school line · function 2000" where it applies; every posting table sorts and filters (`SortTable` in `fy-shared.tsx`) |
| `fy-overlap`, `fy-year-facts` | overlap with the school budget; the year in figures |
| `fy-readiness` | which years are ready; the next year's missing inputs worded as a records request |

**Rules and names settled with TJ -- keep them:**
- "re-charged", never "moved". "Journal entries" and "payments", never "sources".
- "Same vendor as the line", not "same payee": a bus company is not proof of the same purchase
  (the after-school field-trip buses matched Regular Transportation via one vendor). Option 1,
  matching by object code, was tried and rejected -- it dropped 82%, including real IDEA/CB tuition.
- Budget walk: voted + transfers + carried in = final (ties to p13 on all 262 FY2026 lines).
  Flag: |change| >= $5,000 AND >= 50% of the vote (`ADJ_MIN`, `ADJ_SHARE` -- OUR thresholds).
  Flag counts 17/13/23/12, lines changed 109/73/202/82 (FY2023-26; re-run before quoting).
- Fund names readable via `journal.grant_program()` ("Athletic fee fund (Chapter 658) · 1301"),
  printed name underneath.
- Categories by DESE function code (`build_school_surplus.py` CATEGORIES): Nurses 3200, Salary
  reserve 0300 (a local code, not in DESE's list), Special details 3600, 5150 to benefits. No
  salary catch-all.
- Spent = payments + owed (memory `spent-means-payments-plus-owed`). Bars start at zero, always.

**How a new year unlocks:** `readiness()` -- the journal plus the gf-school and special-school
period-13 reports held. `journal.YEARS`/`OPEN_FY` are read lazily off the journal CSV.
`refresh.py` rebuilds and verifies the page daily. By hand still: one `PLAN_BOOKS` line per year (an
unmapped year builds with its offset "not read").

**Open, none promised -- ask TJ which:**
1. `check_generated.py` full pass (above). Do this one regardless.
2. A separate "Vendor matches to check" section -- offered; TJ said the "What it bought" fix
   "should resolve it". Ask before building.
3. ~~Sortable columns on Budget changes after the vote~~ DONE 28 Oct.
4. DONE 28 Oct as its own page (/school-all-funds/activities-fund), not a callout here (TJ).
   Was: fund 1305 (after-school activities) put $178,540 under function 2000 with no school line --
   payroll $66,554, Nature's Classroom $32,120, College Board AP $29,826, Chocksett Inn $14,780 and
   more. TJ: *"WOAH"*. Shown, not yet called out as a finding; rule 7 (a fact, not a charge) and
   rule 8 apply if it becomes one.
5. Other funds' unspent money: a registered gap (money-gaps; needs period-13 fund balances).
6. Release: where it lives and what its finding is (currently year-neutral). Level 2 categories.
   The $303,499 Town-side Unemployment -> Health Insurance entry is TJ's.
7. Offer to file the FY breakdown and search logging to NextLevel (#appdev #lunenburgbudgetapp).

**Checks and gotchas:** `build_fy_breakdown.py --check`, `verify_fy_breakdown.py`,
`cd fy28 && npx tsc -b` (stricter than `--noEmit`; it broke a build once),
`bash scripts/check_phone_width.sh school-all-funds/fy-breakdown`. A digit in a block label needs
`T.lit`. Dev server: one only, port 8811 (several at once confused which tab was current). Deploy
only when asked: `bash scripts/deploy_site.sh` after a full site build (never a bare `vite build`).
Do not commit other sessions' files (CLAUDE.md, money-gaps, document-defects, official-votes,
budget-state, recording-minutes, agentic-spend, page_integrity/totals scripts).

### What changed overnight, 27-28 October

Unspent sits at the end of What happened (TJ chose it); the budget walk
(voted -> transfers -> carried -> final) on every line, a Budget changes after the vote table
with the transfers behind each change, a flag for lines moved by half or more and $5,000
(thresholds ours); School lines other funds paid sorts by amount, opens a popup, measures
against the vote and the final budget, and shows what each fund booked the money as plus its
memos; "Same payee" is now "Same vendor" (a bus company is not proof of the same purchase);
fund popups say "No school line · function 2000" in place of "booked to a heading" and have
sortable, filterable tables. Categories: "Nurses & other staff" split into Nurses (3200),
Salary reserve (0300), Special details (3600); no salary catch-all remains. Search logging is
LIVE (a test row landed). Offered, not built: a separate "Vendor matches to check" section.
check_generated.py was not rerun after the category split -- run it first next session.

## 27 October 2026, night. Pushed (7e2c8b8cc), not deployed then

The page grew from one table into a year's money relationships. Blocks, in order, every one a
single FY switched by the picker, every figure from `build_fy_breakdown.py`:

1. **The plan and what happened** (`fy-plan`): in dollars, plan bar (budget used, circuit breaker
   charged, then UNSPENT outlined at the end -- TJ: "always") against what happened by payer.
2. **From the plan to what happened** (`fy-bridge`): a bridge, FROM ZERO (a truncated axis made
   $3M look longer than $26M). Its sentence is asserted every year.
3. **Across the year line** (`fy-year-line`): in across 1 July / out across 30 June; each
   crossing tied to the other year (owed 30 June = next year's carried in, to the cent). FY2026
   paid $189,276.75 of FY2027 collaborative tuition early. TJ: "watching the money cross
   boundaries ... this is a money relationship page".
4. weeks, the big line table, then **School lines other funds paid** (`fy-line-funds`: one row per
   line, largest first, popup per line) above **What other funds paid for** (by fund; column is
   "Kind of fund", not "who paid"), overlap, the year in figures.
5. **Years and what they need** (`fy-readiness`): a year UNLOCKS ITSELF when the journal and both
   period-13 reports are held (`readiness()`); `journal.YEARS`/`OPEN_FY` are read off the journal.
   The next year's missing inputs are worded as the records request. `refresh.py` rebuilds and
   verifies the page daily, so a new MUNIS year needs no step once extracted. PLAN_BOOKS is still
   one line per year by hand; an unmapped year builds with its offset "not read".

**Open:** deploy (`bash scripts/deploy_site.sh`; the site build must be rerun first -- the last one
predates the popup). Search logging is live in D1 (`search_log` created 27 Oct) but records only
after that deploy. Other funds' unspent money is a registered gap (money-gaps: needs period-13
fund balances). The weekly chart's per-year June line replaced a hardcoded FY2026 claim.
The $303,499 Town-side entry is still TJ's. Next level (TJ, earlier): level 2, categories.

## Earlier state, 27 October 2026 (afternoon)

TJ wants to keep thinking about this page in a fresh session. Nothing is half-done; everything below
is committed (latest page commits 69294bb2e, 5ddc37962) and DEPLOYED, but still a DRAFT: the address
works, it is on no shelf, not in topics.json, not in the sitemap. Load the `building-a-page` skill,
then read this section. The older sections below are history -- several of their sentences are
superseded (the alluvial, pool, timeline and four-part table are gone; facts DO switch with the year).

**Address:** /school-all-funds/fy-breakdown (`?fy=FY2025` picks the year; old /fy2026-closeout/
fy2026-breakdown maps here via `TOPIC_MERGED`). Title "FY breakdown". Companion, registered and
public: /fy2026-closeout/fy2026-circuit-breaker ("Circuit breaker and surplus").

**The page, top to bottom (blocks, in `build_fy_breakdown.py` `page()`):**
1. `fy-year-picker` -- one global year for the page (`fy-year.ts`: `?fy=` + window event
   `fy-breakdown-year`). Big year + "1 July X to 30 June Y", pops on change, a compact copy pins
   under the header once scrolled past (IntersectionObserver; CSS sticky could not work in a block).
2. `fy-year-weeks` -- every week of the year across every line, bars by fund/kind, re-charges off
   and back split, top entries per week on hover. Click to pin; clear by background click, Clear, Esc.
3. `fy-line-table` -- THE table TJ likes. Wide breakout, Category column, head and tail (15 + 15)
   with a gap row, chips per cell with counts ("3 journal entries", "2 funds"). Two sums per line:
   - Budget - Spent before re-charges + Re-charged to other funds - Re-charged from other funds = Left
   - Spent by school budget + Paid by other funds, re-charged later + Paid by other funds, from the start = Total
   Column headers carry plain-English hover definitions saying which side of the sum they sit on.
   Clicking a row opens a POPUP (`LineView`), tabs: Summary / Transfers and re-charges / Expenses
   (every journal row, who paid, filters by fund, payee, memo) / Analysis (weekly bars, payee bars
   showing their memos, memo bars showing their payees; clicking a bar filters Expenses).
   Line rows load lazily from /data/fy-breakdown/lines-<year>.json (~1 MB each).
4. `fy-year-facts` -- facts and conclusions per year, switching with the picker.

**Vocabulary settled with TJ -- keep it:** "re-charged", never "moved" (a re-charge sends the BILL
to another fund after the school budget paid; no money goes INTO that fund). "Journal entries" and
"payments", never "sources". "Paid by other funds, re-charged later" = general fund paid first, the
other fund then put the same amount back.

**The model (`scripts/fy_breakdown.py`), the parts that took the longest to get right:**
- Scope 0100 / dept 300; owed footing (spent = payments + owed, memory `spent-means-payments-plus-owed`).
- Rule a (re-charges) is measured on the SCHOOL side, each account NETTED WITHIN EACH JOURNAL ENTRY
  before classifying off/on -- one entry debiting and crediting Health Insurance had produced a fake
  "moved back".
- A move back nets against the fund's direct (payee-rule) placement on the same line (`backs`), or
  Total double-counts (8 FY2025 lines did).
- Whatever other-fund money cannot be placed goes to unmatched, why "moved between funds by journal entry".
- `verify_fy_breakdown.py` recomputes it by its own route; both are in `check_generated.py`.
  27 Oct: "1066 lines in 4 years, every part recomputed and tied to the period-13 report".

**Findings TJ reacted to (re-run before quoting -- rule 2):**
- Private tuition and collaborative tuition are large counter-acting numbers in the same category.
- Collaborative tuition: the vote counted on circuit breaker reimbursement it did not receive until a
  single 29 June 2026 charge -- the whole circuit breaker page grew out of this.
- A Town-side journal entry of $303,499 landed on Unemployment on 12 June 2026 ("move to correct
  acct") and was reclassed to Health Insurance on 30 June; health premiums arrive by monthly journal
  entries from the Town's books, outside the school's journal. Not chased further.

**Open threads, none promised -- TJ's call which to pick up:**
- What the page is FOR when it is released: it is a general analysis of any year, so where does it
  live, and what is its finding? The current finding is year-neutral ("left $32,022 in FY2023 and
  $482,118 in FY2026; pick a year").
- DONE 27 Oct (afternoon): payload weight. Each line's transfers and journal entries (`moves`,
  `jes`) now live in the line files under `mv`, read when the Transfers tab opens; the unused
  `payers` field is gone. fy-breakdown.json 2.04 MB -> 0.93 MB (gzip 202 KB -> 135 KB).
- DONE 27 Oct (afternoon): the wide table shows a "More columns: scroll the table sideways" line
  and an edge shadow on whichever side hides columns, only while it overflows.
- The $303,499 Town-side entry (above).
- The hover-chip and modal code is all in `fy-line-table.tsx` (large); split it if it grows again.

**Checks before shipping anything here:** `python3 scripts/build_fy_breakdown.py --check`,
`python3 scripts/verify_fy_breakdown.py`, `bash scripts/check_phone_width.sh school-all-funds/fy-breakdown`.
Deploy only when TJ asks (`bash scripts/deploy_site.sh`; the upload can drop with EPIPE -- retry).

## RENAMED: FY breakdown, /school-all-funds/fy-breakdown (27 October 2026). Still hidden

TJ: "lets call this FY breakdown, unrelated to 2026 ... it shouldnt go in fy2026 closeout. this
is a general analysis of the FY". Draft home is school-all-funds; the old id maps there
(routes.ts TOPIC_MERGED). One year picker for the page (`fy-year-picker`, `fy-year.ts`,
`?fy=FY2025`), pinned under the header once scrolled past; no chart has its own. The finding,
facts and conclusions are still written about FY2026 -- the next thing to make year-neutral.

## REBUILT AROUND THE LINE TABLE, 27 October 2026. Still hidden (draft), not deployed

TJ cut everything below the table ("those charts dont help"): the alluvial, the pool, the moves
timeline and the category table are gone, components and generator code with them. The page is
now: the line table (two sums; re-charges apart from money other funds paid from the start;
each line opens a popup -- Summary, Expenses with every row and who paid, Analysis by week,
payee and memo, from /data/fy-breakdown/lines-<year>.json), then `fy-year-weeks`, every week of
the year across every line. Companion page: /fy2026-closeout/fy2026-circuit-breaker (registered,
on the shelf). Vocabulary settled with TJ: "re-charged", never "moved" (a re-charge sends the
BILL to another fund; no money goes into it).

## SHELVED, 26 October 2026 (late). HIDDEN, NOT RELEASED. TJ is taking a different approach

TJ, after reading it: *"im struggling to undersand this ... and how it helps undersand the
moves"*, then: *"lets put this page into a hidden section where we wont release it."* The page is
built as a DRAFT (`draft=` in `build_fy_breakdown.py`), so it is on no shelf, not in topics.json,
not in the sitemap and not prerendered; the address /fy2026-closeout/fy2026-breakdown still opens.
Model, verifier and components are kept; `check_generated.py` still runs both.

**Why it did not land, in one line:** it opened on the all-funds identity (other funds paid
$1.6M toward the lines, voted $1.0M below cost), which is mostly STRUCTURAL -- fee funds paying
their own staff's insurance every year -- and it buried the part that changed between years: the
moves. What finally made sense in conversation was one table, measured from the journal:

| | FY2025 | FY2026 |
|---|---:|---:|
| left, as reported (owed counted) | $554,945 | $482,118 |
| bills moved between the school budget and other funds | $253,382 onto it | $366,899 off it |
| next year's tuition paid early | none | $189,277 |
| last year's orders never paid | $38,354 | $41,377 |
| left before those moves (our arithmetic) | $769,973 | $263,119 |

Run the model before quoting any of it (rule 2). TJ declined rebuilding the page around it.

## BUILT, 26 October 2026 (night): the data, the identity, the verifier, the alluvial. Not committed, not deployed

- `scripts/fy_breakdown.py`: the model. The identity closes to the cent on every line, every year;
  owed footing (FY2023 $32,022 / FY2024 $31,705 / FY2025 $554,945 / FY2026 $482,118 -- run it, do
  not quote this line). Both worked cases reproduce. Match rules a/b/c are declared in its docstring,
  with two decisions made here: CAPITAL ARTICLES are matched only by journal entry (by payee they
  pulled ~$818k of HVAC work onto operating lines); a cost moved BACK onto the general fund is left
  with its own account (IDEA's aide payroll on fund 2813 is function 0000, unmatched -- placing the
  move-back on the aide lines made a phantom negative).
- `scripts/verify_fy_breakdown.py`: own CSV reader, shares only `category_of`; ties every line to
  the period-13 `available_budget` less next July's SOY, and the alluvial's columns to every school
  expense dollar. Power-tested three ways (shifted term, one cent, broken prepay rule): all fail it.
  Found one real defect while being written: placed money on a line with no postings that year was
  silently dropped ($48,910 in FY2026). Fixed in both routes; the model now asserts it.
- `scripts/build_fy_breakdown.py` -> `/fy2026-closeout/fy2026-breakdown`, "Surplus in four parts":
  alluvial (`fy-alluvial.tsx`, `?block=tuition` opens on one block), waterfall of the four parts,
  4 conclusions with meanings, 12 facts, the four-way table by category with a tab per year. In
  `check_generated.py`. Phone width checked (400px, clean). Registry: lead group of the shelf.
- money-gaps: new last row (which line a grant dollar pays toward; closes: DESE-approved grant
  budgets, End of Year Financial Report). Public copies not regenerated (refresh does it).
- ALSO BUILT (same night, TJ: "build everything you planned"): `fy-pool` (under lines -> one pool
  -> over lines + left; no line-to-line edges), `fy-moves-timeline` (transfers / fund moves /
  money crossing years, July-June, the Town's memo on each), `fy-line-table` (every line, sortable,
  each opening on its own waterfall and its payers with the matching rule; unmatched money listed).
  All three carry FY2023-FY2026 tabs. The payload is ~950 KB, mostly the line table. Waiting on
  TJ's comparison against what he thinks will reveal the most.

Written 26 October 2026 (late), for a FRESH session. Load the `building-a-page` skill first,
then read this file, then `notes/HANDOFF-SURPLUS-PAGES.md` (the surplus work this grows out of).

## What TJ asked, in his words

> *"a lot of money moves in and out of the school budget. and from a lot of sources. generally
> speaking, how can someone actually say why a surplus happened? moving costs into general fund
> and out of grants muddies the water and makes it hard to find the true causes here. there HAS
> to be a way to see why they had leftover money."*

> *"im struggling to truly understand the surplus ... the only answer i have right now is 'its
> too complicated to understand why we have a surplus', but it feels like the shell game"*

He pictured: a single page per fiscal year, from the ledger, journal and budget, showing what
was spent, from which source, onto which function code, and where money was NOT spent; a
timeline of transfers; and "a node graph where money is moved from one bucket to another".

**The job of the page is to replace "it's too complicated" with four numbers.** Not to say
anybody played a shell game (rule 8: the effect on the figure, never intent). The concept that
makes it feel like one is FUNGIBILITY: inside one appropriation a dollar left on one line pays
for another, and a cost moved between funds changes what a line shows without changing what
anything cost. The page has to make that movement visible, which is what dissolves the feeling.

## The method: an identity, not an estimate

For every general fund line (and so for the year, by summing):

    left on the line  =  (voted - all-funds cost)        budgeted above or below what it cost
                      +  transfers in, less out          budget moved between lines (BUA)
                      +  paid by other funds             grants, circuit breaker, revolving, reclasses
                      -  paid this year for another year prepayments; carried orders (SOY/YEC/POE)

It is accounting arithmetic: GF spend = all-funds cost - other funds' share, and left = voted +
transfers - GF spend. Every term is measured off the journal, so the four totals sum to the
surplus to the cent or the build fails.

**Worked test case the page MUST reproduce (FY2026 private tuition, 535019):** voted $988,630;
all-funds cost $753,109 ($466,001 GF + $287,108 IDEA grant fund 2814 to May Institute);
transfers $0. So (988,630 - 753,109) + 0 + 287,108 = **$522,629**, the line's printed
available. 45% budgeted above cost, 55% a change of payer.

Second test case (collaborative tuition, 535023): the 29 June reclass of $333,494.89 to fund
2640 is "paid by other funds"; the 30 June $189,276.75 on `27L2KEY` invoices is "paid this year
for another year". Both are on /fy2026-closeout/fy2026-tuition-paid-early; tie to it.

## The hard part: "the same thing" across funds

**Function codes alone do not join the funds.** The IDEA grant booked May Institute's tuition as
CONTRACTED SERVICES, not tuition (/school-all-funds/grant-coding documents that FY2025 grants
moved off the teaching headings). A function-code view would have shown "grant spent on
services, tuition came in under" and never connected them. So "all-funds cost of a line" needs:

1. **Payee match first, for invoices** (`API`/`APM`, vendor present): a payee paid from the GF
   line in any year, paid from another fund in this year, counts toward that line. Payee names
   through `journal.payee()` / `vendor_key()`.
2. **Function code for the rest**, where both funds book the same heading.
3. **Payroll has no payee** (3,176 of 6,583 FY2026 actual lines carry a vendor; payroll does not,
   by design: names masked). Payroll moved between funds is already measured on
   /school-all-funds/pay-moved-between-funds (journal entries moving GF pay to other funds and
   back); reuse that logic, do not re-derive it.
4. **Anything unmatched stays visibly unmatched**, its own row, never folded into "budgeted
   above cost". Rule 13 3/sub-cause 3: a join that matches nothing looks like absence.

Every match rule is OUR reading and says so (rule 7); the identity's arithmetic is not.

## The page: one FY at a time, four pictures (settled with TJ, 26 Oct 2026, late)

TJ: *"there has to be a way to visualize fungibility then. this has to be a solved problem?"*
It is two problems, and only one is drawable.

**Across funds (who paid) -- solved.** An ALLUVIAL diagram (a Sankey across years). **This is
the page's opening picture.** Columns FY2023 to FY2026; in each, stacked blocks by function group
(`build_school_surplus.CATEGORIES`), each block split by payer (GF, each grant via
`journal.grant_program()`, circuit breaker, revolving). Bands flow year to year. A payer shift
reads as a band keeping its height and changing colour: May Institute, GF blue in FY2025, grant
orange in FY2026. Cost held, payer changed. The state publishes the all-funds-by-function half
(DESE End of Year Financial Report; `fetch_dese_radar.py`): use it as the outside check on our
journal sums. The literature's name for the question is the flypaper effect / supplanting.

**Inside one appropriation (which leftover covered which overrun) -- NOT drawable.** The books
record no pairing between a line's leftover and another line's overrun; the money is a pool.
Any line-to-line arrow is invented (the private-covered-collaborative story in the surplus
handoff is exactly such an invention -- say so where it appears). So draw a HUB-AND-SPOKE: under
lines pour into a central pool, over lines draw from it, the net is what was left. The only
direct edges are those the books record with both ends named: `BUA` transfers and `GEN`
reclasses, solid and dated. **Second picture.**

**Unmatched money is its own grey band/spoke, labelled unmatched** -- payroll moved between funds
has no payee, and a grant may book tuition as services. Never fold it into "voted above cost".

| question | picture | block |
|---|---|---|
| Who paid for what, and did it change? | alluvial, FY2023-FY2026 | `TB.custom`, new component |
| What did the pool absorb? | hub-and-spoke, one FY | `TB.custom`, new component |
| Why is each line under? | waterfall per line + sortable four-way table | `TP.bridge` / table |
| When did money move? | timeline of transfers, reclasses, prepayments | `TB.timeline` or custom |

Opening line: the year's four totals as a comparison (AUDIT-PASS), e.g. "Of $482,118 left: $X
voted above cost, $Y paid by other funds, $Z moved by transfer, -$W paid for next year."
Plus conclusions with `so=` on every one (`topic.MEANINGS_REQUIRED`), a not-established block,
sources, money-gaps citations. Build order: data + identity + verifier, then the alluvial, then
the pool, then the rest. TJ's aim, verbatim: *"i want to find a way to analyze these FYs to
figure this out."* The page is an instrument for that first, a publication second.

## Data, and what to check before writing a sentence

- `sources/data/munis-school-journal.csv` via `scripts/journal.py` (`lines()`, `accounts()`,
  `COLUMN_OF` maps source codes to actual / encumbrance / original_budget / transfer,
  `fund_group()`, `in_surplus_scope()`, `left()`). FY2023-FY2026, 93 funds.
- FY2026 actuals by fund group (journal, expense accounts): General fund $25,657,318; Revolving
  and lunch $1,856,768; Grants $1,021,253; Capital and other $788,956; Circuit breaker $337,499.
  Recompute, do not quote.
- **FIRST STEP: tie every year and every fund to the period-13 reports** (GF:
  `munis-school-ytd.csv`; special funds: the period-13 special funds report). money-gaps row 225
  says that report leaves some special revenue funds out against the annual town report -- so
  state which funds the page covers, and that the rest is not held.
- Budgets exist for the GF only (BUC/BUA). Other funds have no "voted" column in the same
  sense; they enter the identity only as "paid by other funds".
- FY2025 closes on a different footing from FY2026 (`HANDOFF-SURPLUS-PAGES.md`, item 1): use
  the owed footing throughout and say so.

## The verifier, written before the prose (rule 15)

A `verify_fy_breakdown.py` that recomputes the four terms from the raw CSV with Decimal,
sharing only the category definition, and asserts: the four sum to each line's printed
available; the year's four sum to the surplus; the two test cases above reproduce exactly.

## Cost

A generator, a Sankey component, a verifier: a few hours. Fresh session (rule 7g). The
interactive session is the expensive part, so keep OCR-style reading out of it.

## Not this page's job

Whether any shift was proper. Lawfulness of the prepayment is on its own page (c.71 s.71D).
Supplement-not-supplant / IDEA maintenance of effort was raised in conversation on 26 October
as a QUESTION, unchecked: MOE is tested in aggregate with allowable exceptions, so one payer
shift establishes nothing. Do not put it on a page without the regulation and the district's
MOE figures in hand.
