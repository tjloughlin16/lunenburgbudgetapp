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

## In flight

- The town officials and staff lists: an agent began 1 November with a three-edition pilot
  (`sources/data/town-rosters/`). It is step 5 for one family, started early because TJ asked for a
  town-side ranking of who served longest.
- Searchable copies of the 16 FY2011-FY2025 report PDFs: an agent began 1 November.

## Cost

Steps 1, 2 and 4 are code and small reads. Steps 3 and 5 are reading, done in isolated workers.
Quote each batch in % of the week before it starts, and measure the first one.
