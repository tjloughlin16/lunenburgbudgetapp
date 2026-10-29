# Handoff: the 52 older annual town reports (1959-2010), from the town's archive into the app

Written 28 October 2026, to survive a context reset. **Read this first, then
`notes/PLAN-ANNUAL-REPORT-PIPELINE.md` (sections 4, 4a), then CLAUDE.md.** A summary in a
conversation is not a source (rule 13): every state below names the command that re-checks it.

## NOW (29 October 2026): finishing 1991-2010 to the FY standard, BEFORE any new batch

TJ, 29 Oct: *"i want the 1991 - 2010 'fully done' before you move onto the other pages"* -- and
*"run it safely in case you hit the limit"* (5% of the week left, resets 29 Oct 22:59 ET).

**Done means** what FY2011-FY2025 reached: every financial page `proven` or `blocked`, a blocked
page registered in `sources/data/page-blocked.csv` with its reason and the ONE document that
would settle it. At the start: **412 proven, 189 unproven, 4 refused** across the 20 editions.

    python3 - <<'X'   # the count, re-derive it, never quote this file
    import csv,collections; c=collections.Counter(r['state'] for r in csv.DictReader(open('sources/data/annual-report-pages.csv')) if int(r['fy'])<=2010); print(c)
    X

**Open pages by what fails them** (29 Oct): appropriations 93 + 9, debt 31 + 1, trust funds 25 + 3,
payroll 10, valuation 6, capital 5, special revenue 4, receipts 2, vital records 2, other 2.

**THE UNITS, in order, ONE AT A TIME** -- each ends with every `read_report_tables.py <ed> --check`,
`merge_report_tables.py --check`, `build_db.py --check`, and a commit by explicit path. A unit cut
off by the usage limit is simply re-run; nothing is committed until it passes.

1. **Appropriations, unlabelled department subtotals** (the 93). The accountant schedule prints a
   department's subtotal with no label; the validator sums it with its own detail lines. Fix as a
   PER-EDITION OPT-IN in `edition.json` (as `validator_drop_titles` was), never a change to the
   shared block walk -- so FY2011-FY2025 cannot move. Verify FY byte-identical anyway.
2. **Debt** (repayment-schedule grouping, `$` read as `8`): grouping by opt-in; misreads witnessed
   from the page's own glyphs or recorded in the discrepancy register, never silently corrected.
3. **Trust funds** (books printed across pages and out of order, comma decimals).
4. **The rest** (payroll, valuation, capital, special revenue, receipts).
5. **Residue: what cannot be proven.** A page whose own arithmetic does not close (e.g. 1998 p62
   leaves a $660,000 bond out of one column's total; 1994 p42 prints `$9.50`) is BLOCKED with the
   reason and the document that would settle it -- never forced to close, never averaged.

Each unit runs in a FRESH agent (CLAUDE.md 7g: not in a long session), with this section as its
brief; the parent verifies and commits. Progress is recorded here after each unit.

| unit | state | proven / unproven / refused after |
|---|---|---|
| 1 appropriations | not started | |
| 2 debt | not started | |
| 3 trust funds | not started | |
| 4 the rest | not started | |
| 5 residue to blocked | not started | |

## Where it stands

| | reports | re-check |
|---|---|---|
| fetched from the town, backed up in R2 | 52 of 52 (1959-2010) | `sources/town-annual-reports/index.csv` (68 rows = 16 FY + 52) |
| Textract **text**, every page | 52 of 52, 6,246 pages | `python3 scripts/read_annual_reports.py --status` |
| searchable on the live site | 52 of 52 (8,358 report pages incl. FY) | `/search?type=annual-reports&q=cemetery` |
| Textract **tables** | **10 of 52** (2001-2010), every page; finder built for the rest (step 3) | `python3 scripts/read_annual_reports.py --status --feature tables` |
| mapped by a worker (edition folder) | **10 of 52** (2001-2010) | `python3 scripts/read_report_tables.py <ed> --check` |
| integrated: shared datasets, rosters, `lunenburg.db` | 2001-2010: **see "Integration pass" below** | `python3 scripts/merge_report_tables.py --check`; `annual_report_progress.py` |
| pushed to D1, on the site | not yet for 2001-2010 | `sync_d1.py --check` |

**The remaining 42 (1959-2000)** have text and are searchable, and nothing more. Finishing them
is steps 4-7 below, in batches.

## TJ's decisions -- binding, do not re-ask

- **Order of work** (plan section 4): AWS reading runs in parallel with everything, newest year
  first, hard stop at the monthly cap. Where reports and meetings both want the Claude plan,
  **annual reports first**. 28 Oct: *"The annual reports right now are the top priority."*
- **What to extract** (plan section 4a): work from the PAGE outward. Map a table to an existing
  dataset only when it is the same quantity, stage and grain; what does not map becomes a NEW
  dataset in the database and searchable; what a modern dataset has and an old report lacks is
  a GAP in `money-gaps.csv`. *"these go back to the 50s ... capture information from tables and
  finances that may no longer exist."*
- **Tables scope:** text on every page (done), then Tables **only on financial pages** for the
  rest. The ten pilot reports got Tables on every page on purpose -- they are the ANSWER KEY for
  a financial-page finder (see step 3).
- **Spend:** batches, confirming cost as you go -- *"batches of 10, then if costs map out, double
  to 20"*; *"dont blow out budgets accidentally"*; parallelise for speed at the same cost.
- **Done means** what FY2011-FY2025 reached: pages proven or blocked, the same datasets, in
  `lunenburg.db`, on the site. *"fully integrated into the app ... to full completion."*
- **Cache backup:** yes, to the PRIVATE bucket (not yet done -- step 0).
- **Unattended map + review in the refresh:** approved, not yet wired (P2 in the plan).
- **Quarterly fetch:** annual reports are their own source `annual-reports`, every 90 days; next
  run 26 January 2027 (`python3 scripts/source_cadence.py`).

## The process, step by step

### 0. Before anything: holds and switches

- `build/STOP-METERED` was written 28 Oct to pause the meeting backlog (`process_meeting.py`) so
  reports get the plan allowance. **It also blocks Textract.** Read it, and delete it before a
  Textract run (and tell TJ the meeting run resumes) -- or rewrite it after.
- `build/STOP-TEXTRACT` is the meter's latch. If present, read why before deleting.
- Monthly AWS cap $50 (UTC month). October ended the session at **$28.00** (ledger). November
  starts fresh on 1 Nov UTC.
- Back up the Textract cache (`build/textract/cache/`, paid responses, one machine only) to the
  PRIVATE R2 bucket -- TJ said yes; not done.

### 1. Fetch (done; quarterly from now)

`python3 scripts/watch_documents.py --annual-reports` -> `fetch_town_docs.py --scope
annual-reports`. Walks the town's Annual Town Reports page, DocumentCenter and ArchiveCenter;
lands new PDFs through `ingest.py` (backed up before they reach `sources/`). **No local OCR**:
`pdf_kind.extract_text(ocr=False)` for annual reports -- Textract reads them.

### 2. Text read (done for all 52)

`python3 scripts/read_annual_reports.py --batch N --feature text --workers 16` -- newest first,
pages in flight on threads under ONE meter (`textract_spend.Meter`, one process only; every
reservation on the main thread). `--dry-run` first; it prints the estimate and the ceiling, and
the run prints `COST: estimate | ledger | pages x price` at the end. The text then went into
`sources/town-annual-reports/text/<stem>.txt` and the index's `read` column (one-off script in
commit 40240528f; fold it into read_annual_reports.py when P2 is built), then
`build_search_index.py` and `sync_search_d1.py`.

### 3. Tables read (10 done; 42 to go) -- financial pages only

**The finder is built (28 Oct, second session): `scripts/find_financial_pages.py`.** A page is
financial when its Textract TEXT read holds 3+ money figures; no headings, no keywords.
`--score` runs it against the ten answer-key reports (each worker's `map.csv` `financial` column)
and exits 1 on any miss -- it found 334 of 334 and picked 466 of 1,076 pages. `--list` prices the
rest: 2,122 pages across the 42, ~$32. Read only those:

    python3 scripts/find_financial_pages.py --score
    python3 scripts/read_annual_reports.py --batch 10 --feature tables --financial-only --dry-run

The first batch (1991-2000) dry-runs at 402 pages, $6.03, ceiling $6.64. **Not yet sent.**

**What financial-only does NOT read for 1959-2000, by design:** count tables with no money --
elections, enrollment/MCAS, vital records, officials, department activity. Workers built datasets
from those in 2001-2010; for the older years their text is searchable and their tables are not.
TJ was told on 28 Oct; reverse it by reading those pages too, not by changing the threshold.

**A trap fixed with it:** `textract_pages.write_out` built `lines.tsv` from the run's feature
only, so a financial-only tables run would have cut each report's `lines.tsv` down to the
financial pages and dropped every roster page `dump_roster_pages.py` reads. Lines now come from
the tables read where a page has one and the text read otherwise, whatever the run's feature;
all 108 existing TSVs regenerate byte-identical.

### 4. Per-report workers (10 done; 42 to go)

The brief, verbatim and reusable: **`notes/process/ANNUAL-REPORT-WORKER-BRIEF.md`**. One worker
per report, in parallel, each writing only `sources/data/report-tables/<ed>/` (edition.json,
map.csv, gaps.csv by eye; the rest generated by `scripts/read_report_tables.py`), listing
shared-script changes in `NEEDS.md`. Batches of ~10 (TJ's doubling rule applies).

### 5. Rosters

`scripts/dump_roster_pages.py` reads Textract lines for calendar editions (rows rebuilt from
line positions). It needs the edition's catalogue rows, so it runs AFTER the merge. Write to a
scratch `--out` and copy ONLY `<year>-p*.txt` into `sources/data/rosters/` -- **never overwrite
`FY*.txt`**: today's rendering differs from the committed FY files by whitespace on all 99
pages (pre-existing drift; HEAD's script produces the same), and the FY readings are proven
against the committed ones. Then each page is read into its `.json` (the judgment step), and
`build_staff_rosters.py` accounts for every line.

### 6. One integration agent, after every batch of workers

Its brief was (28 Oct): unify new-dataset names across folders (same quantity, stage, grain ->
one name; record in `sources/data/report-tables/README.md`); apply every NEEDS.md item ONCE in
the shared scripts; re-run every edition folder and `--check`; `merge_report_tables.py` and
`--check` (FY2011-FY2025 byte-identical); `report_review.py <stems>`; rosters (step 5);
`build_db.py` (only when no site build runs) and `--check`; the downstream generators
(build_extraction_gaps, build_ingest_plan, build_archive_guide, build_schema_page,
build_annual_reports, build_dataset_provenance, build_ingest_status, map_annual_report_pages).
No commit, no D1 push, no deploy -- the parent checks, then does those.

### 7. Verify, commit, push, deploy (the parent session)

`merge_report_tables.py --check`; `annual_report_progress.py`; SQL counts per edition in
`lunenburg.db`; `check_generated.py` once; commit by explicit path (other sessions have
uncommitted work); `sync_d1.py`; `npm run build:site`; `bash scripts/deploy_site.sh`. Rule 10:
deploy only when TJ asks (he asked on 28 Oct for this work).

## Measured, 28 October 2026

| what | measured |
|---|---|
| Textract text | 6,246 pages, $9.369 ledger; 8 workers 2.2 pages/s, 16 -> 4.2, 32 -> 5.6 (AWS throttling near) |
| Textract tables | 1,076 pages (2001-2010), $16.14 ledger, 512 s at 16 workers |
| estimate vs ledger | equal to the cent on every batch |
| ledger vs AWS's own bill | Tables price CONFIRMED (166 pages: $2.49 vs AWS $2.56). **Text price NOT yet confirmed** -- AWS Budgets lags; check `textract_spend.py --status` until AWS reads ~$28 |
| pilot worker (2010, built the tooling) | 377,821 tokens, 146 tool calls, 39 min |
| per-report worker (2001-2009) | 2,109,670 tokens for nine = ~234k each; 13 min in parallel |
| plan usage at the time | week 82% (resets Oct 29 22:59 ET), 5-hour window 12% -- TJ: "don't worry about the session percentage right now" |

For a fresh batch, ask TJ for `/usage` before and after: % of the week per report is the number
he wants, and tokens are only a proxy for it.

## Traps hit on 28 October, so they are not hit again

- **A sandbox test tripped the REAL Textract latch.** Fixed: a sandboxed `TEXTRACT_STATE` now
  gets a sandboxed latch. Test with `TEXTRACT_FAKE=1 TEXTRACT_STATE=<scratch>
  TEXTRACT_TEST_CAP=<$>`.
- **The meter refuses a second process** by design; parallelism is threads inside one run.
- **The crawler OCR'd scans locally** before `ocr=False` (40 minutes on one report).
- **A killed crawl leaves the index without its new rows** -- re-run it; files on disk are not
  re-downloaded.
- **The 52 PDFs broke FY-era scripts** (`report_pages.py --rebuild` crashed). Fixed with
  `report_year.report_edition` / `fiscal_editions`; the Vision-era extractors skip calendar
  editions explicitly.
- **`$` read as a leading 8 or 3** in the 2009 wage tables (90 of 574 cells), and the coverage
  check's witness shared the misread -- a check with no power to fail. Integration was told to
  mark or independently witness those cells.
- **Workers name the same new dataset differently.** Give the next batch the settled names.
- **The calendar label is not the financial year.** 2010's balance sheet says "FOR THE YEAR
  ENDED JUNE 30, 2010" (p55); wages say "CALENDAR 2010". Quote the page, every time.
- **The IAM user cannot read Cost Explorer or CloudWatch.** TJ was given the read-only policy
  (`cloudwatch:GetMetricStatistics`, `ce:GetCostAndUsage`); if granted, wire CloudWatch's
  per-minute request count into the meter as a live check against the ledger.
- **`check_generated.py` already failed on other sessions' stale outputs** before this work
  (spending-vs-required, question bank, source index, D1 drift, debt-repayment). Do not
  attribute those to this work, and do not "fix" them by regenerating other sessions' files.

## Integration pass, 28 October -- RESULT

**Done and re-checked by the parent session, 28 October.** `merge_report_tables.py --check`: 28
shared files reproduce from 10 edition folders; every edition's `read_report_tables.py --check`
passes; `build_db.py --check` exit 0; `build_staff_rosters.py`: 6,237 of 6,237 roster lines
accounted for. Every shared dataset is a pure append against HEAD (0 rows removed) except the
three regenerated wholesale (`money-gaps`, `staff-position-map`, `dataset-provenance`).
Integration agent: 479,963 tokens, 164 tool calls, 51 min.

| edition | rows checked / failed / no check | pages proven / unproven / refused | roster entries |
|---|---|---|---:|
| 2001 | 572 / 226 / 412 | 14 / 10 / 0 | 223 |
| 2002 | 1,441 / 207 / 389 | 22 / 13 / 0 | 162 |
| 2003 | 1,080 / 269 / 570 | 20 / 16 / 0 | 199 |
| 2004 | 1,237 / 336 / 529 | 20 / 18 / 0 | 238 |
| 2005 | 1,199 / 242 / 321 | 19 / 13 / 0 | 270 |
| 2006 | 1,394 / 184 / 433 | 23 / 13 / 3 | 156 |
| 2007 | 1,169 / 292 / 464 | 23 / 15 / 0 | 281 |
| 2008 | 1,384 / 20 / 376 | 29 / 4 / 0 | 234 |
| 2009 | 1,375 / 136 / 386 | 16 / 13 / 0 | 221 |
| 2010 | 1,261 / 334 / 443 | 14 / 16 / 0 | 215 |

Settled new-dataset names, the NEEDS items applied and not applied (with reasons), and the
`$`-glyph witness for the wage tables (`scripts/witness_dollar_glyphs.py`): see
`sources/data/report-tables/README.md` and each edition's `NEEDS.md`.

**NOT the FY finish line yet: 131 pages unproven across the ten.** Mostly grouping in the
validator (block walk, cross-page grand totals, unlabelled subtotals -- deliberately NOT changed,
because the FY reviews share that validator and nothing proved the change harmless there), plus
Textract misreads the review register lists (`notes/generated/annual-report-discrepancies.csv`).

**DECIDED, 28 October: the analyses use the older history** (TJ: "if thats your suggestion lets
do it"). Commit a875eb8ab regenerated the 19 generators that read these datasets. State aid's
measured Chapter 70 series now runs over 21 checked years, FY2001-FY2022, not 8 -- only rows
checked against their page, same quantity every year; the flag beside the model's rate moved from
1.75 to 1.68 points, and the model's rate itself is unchanged. **Do the same after every future
batch**: merge, then run those generators and read each diff before it ships. Still stale and NOT
this work's (other sessions' inputs): build_budget_feed, build_ch70_formula, build_decisions_doc,
build_master_report, build_notices, build_reading_time, build_recording_minutes,
build_short_versions, build_athletics_charts, sync_d1 (after their work).

**DEPLOY STILL OWED for a875eb8ab and de02ffa27's pages** (the data is already live in D1). On 28
October the deploy script refused because the FY-breakdown session was writing
`fy28/public/data/fy-breakdown/*` mid-build; a build now would ship that session's work in
progress. Deploy when that session says its work is ready, or with TJ's word to ship both.

**Other unfinished items:** `money-classification` rows for the calendar receipts (they are kept
out of `revenue_history` until classified -- a judgement, not a join); a reader for figures printed
in prose (placement counts, vital-record counts); the validator block walk; the 2006 p69 re-read
(printed upside down); the decision on publishing named births and marriages; splitting 2004 p46
(Passios and Primary on one page) per building.
