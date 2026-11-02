# Plan: everything the annual reports print, in the database

**Started 1 November 2026.** TJ: *"i want all the datasets found in the annual reports to get into
the database, very easily searchable and analyzable. i think we only did the ones we previously
identified, but i want to cover anything that is in the reports."*

## Why this is needed: what was found on 1 November

- **The town officials and staff lists were never read.** Most years print them as a LIST, not a
  table, and every survey so far found tables. `report-officials.csv` holds scraps from 33 editions.
  The historical report ranks school staff by years served because the school rosters were the only
  staff list ever read end to end.
- **The 1959-2010 tables are covered**: Textract found 3,696 tables and every one is mapped to a
  dataset. **FY2011-FY2025 are not**: their catalogue lists 866 tables and 199 read, and the
  difference was never sorted into repeats, prose and real gaps.
- **`notes/reference/EXTRACTION-GAPS.md` is an orphan.** It says "generated" and nothing generates
  it. It was last written 7 September 2026, so it still says the balance sheet and the tax rate were
  never extracted, both of which are now datasets, and it counts sixteen reports, not 67.
- **The database loads report datasets from a hand-kept list** in `scripts/build_db.py`, so four
  never arrived: `report-index`, `report-signatures`, `report-filing`,
  `report-appropriations-supplement`.

## The steps, in order

1. **Coverage register (generated, `--check`ed).** One generator over all 67 reports that writes
   `notes/reference/EXTRACTION-GAPS.md` again, plus a CSV beside it. For each edition: the pages, the
   tables found, the tables mapped to a dataset, the lists found (from step 3), and which of those are
   in the database. The headline is what is not yet in a dataset. It is added to `check_generated.py`,
   so it cannot go stale again.
2. **The database takes every report dataset or says why not.** `build_db.py` globs every
   `report-*.csv` and refuses to build if one is neither loaded nor named in an exclusion list with a
   reason (a refusal log is not data). Load the four that are missing.
3. **A list survey, beside the table survey.** Read every report for named LISTS printed as text:
   officers, committees, department staff, licences, dogs, births and so on. Record each in a
   catalogue with its edition, pages and what it lists. This is ingest work, so it runs in isolated
   agents (CLAUDE.md 7g), never in a long session.
4. **Sort the FY2011-FY2025 catalogue.** For each of the 866 entries: a repeat of a table already
   read, prose, or a real gap.
5. **Extract every real gap into a dataset**, family by family
   (`notes/process/INGESTING-A-TABLE-FAMILY.md`), each with its own check: a printed total where one
   exists, line accounting where none does.
6. **Searchable and analyzable.** Every dataset in `lunenburg.db`, in D1 and `/api/tables`, with a
   row in `notes/reference/SCHEMA.md`; names searchable through the people index where a dataset
   holds people.

## Where it stands (handoff, 2 November 2026, afternoon)

Next 1 and 2 of the morning handoff are done locally: the database guard widened, ten datasets
loaded, both generators reproducing. **Not yet pushed to D1 or deployed** -- `sync_d1.py --check`
will disagree by those ten tables until it is. Pick up at **Next**.

**Done**

- **Step 1, the coverage register.** `scripts/build_annual_report_coverage.py` writes
  `notes/reference/EXTRACTION-GAPS.md` and two CSVs, and is in `check_generated.py`. Read its
  numbers from it, not from here.
- **Step 2, the database guard.** `build_db.py` `check_report_datasets` refuses to build if a
  `report-*.csv` is neither loaded nor in `REPORT_NOT_LOADED` with a reason.
- **One family of step 5: the town officials and staff lists.** `scripts/build_town_rosters.py`
  makes `sources/data/town-roster-entries.csv` (every officers directory and department roster
  in 67 editions), and the file is in the database. `/analysis/historical-report` ranks town and
  school staff on ONE board, by span (first year to last year printed). That ranking was TJ's
  call, 1 November: *"we do not need a school rank and town rank separately. Combine them."*
  Names with forms that disagree (LeBlanc's middle initial; Deming, Jr. and Sr.) are held out,
  not joined.
- **Searchable copies of the 16 FY2011-FY2025 report PDFs** (`searchable-pdfs.csv`).

- **Every report-fed dataset is in the database: 92 of 92.** The ten that escaped by name
  (`treasurers-cash`, `pages-read`, ...) are in `REFERENCE`, and `check_report_datasets` now
  also demands every CSV `build_annual_report_coverage.scan_datasets` classes as report `data`,
  not only `report-*` -- one definition shared with `EXTRACTION-GAPS.md`. Shown to fail when one
  is removed. Costs ~6s of an ~12s `build_db.py`.
- **Both stale generators reproduce.** `extract_appropriations_supplement.py` refused FY2011 p60
  because the generic extract had gained rows for it -- all `check failed` -- so it now defers
  only to `checked` rows. `extract_report_signatures.py` was stale against the 28 Sep / 2 Oct
  re-OCR; regenerated, with `(Submitted by` and `take any other action` added to `WARRANT`, which
  removed eight warrant sponsor lines that were being read as signatures.
- **Every database object has a `table-semantics.csv` row: 206 of 206**, including
  `town_roster_entries`, which had none.

**Next, in order**

1. **Push D1 and deploy** -- only when TJ asks (rule 10).
2. **Two junk rows in `report-signatures`:** FY2012 pages 9 and 18 (In Memoriam) give an
   obituary sentence as the `department`.
3. **Step 4: sort the 866 FY2011-FY2025 catalogue entries.** Start with the 287 on pages no
   dataset reads.
4. **Step 3: the list survey** (licences, dogs, births, committees). The officials and staff
   lists are already done. This is ingest work, so isolated agents; quote it first.
5. **Small fixes:**
   - `mirror_group()` in `build_source_index.py` never sets `searchableUrl`.
   - The town rosters' positions still carry tenure text such as "5 year terms".
   - `check_generated.py` runs `build_db.py --check` beside readers of the same database, and
     on 2 November that raced: `database is locked`, and a `lunenburg.db-journal` that
     `build_source_index.py` then failed on as an uncatalogued file.

**Failing in `check_generated.py` on 2 November and NOT from this work** (left for their own
processes): `write_recording_minutes`, `build_suggested_reports`, `build_vote_lists` /
`verify_vote_lists`, `build_notices`, `build_one_big_report` (`variance` claimed by no page),
`verify_balance_sheet` (12 failures), and `sync_d1 --check` (API error 7500).

**Open questions for TJ, not decided**

- **Search dates.** Annual-report hits in search carry no date (`build_search_index.py` sets
  `'date': ''` on archive documents). Dating them was offered and not yet asked for.
- **Ranking measure.** The board ranks by span, which counts gap years; `held` counts only the
  years printed. Switching to `held` would reorder some rows. Not raised as a change, only noted.

## Cost

Steps 1, 2 and 4 are code and small reads. Steps 3 and 5 are reading, done in isolated workers.
Quote each batch in % of the week before it starts, and measure the first one.
