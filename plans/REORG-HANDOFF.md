# Handoff to the agent doing the archive reorg

Written 5 September 2026, at the end of the annual-report work. Read
`plans/ARCHIVE-REORG.md` for the plan and the decisions; **this file is what changed
underneath it while you were away, and what will break if you move the wrong thing.**

---

## 0. There is a full backup. Use it rather than being careful

    /Users/tj/lunenburgbudgets-backup-2026-09-05/lunenburgbudgets-2026-09-05.zip

3.1 GB, 19,765 entries, whole repo including `.git`. CRC-verified with `unzip -t` and
checked back against the live tree with `shasum -c`. A sha256 manifest of all 16,503
working-tree files and a README sit beside it. **A remote copy also exists.**

So the expensive failure mode here is not losing bytes. It is a *silent* wrong move — an
index row pointing at a file that is no longer there, a script reading an empty directory
and writing an empty CSV. Every check below exists to catch one of those.

---

## 1. The tree is not what `ARCHIVE-REORG.md` assumed

That file opens by telling you to run `git status -sb` and stop if it returns anything. **It
will return about 1,113 files.** That is expected and it is not a reason to stop — it is a
reason to branch off the current work rather than off `main`, or to get it committed first.
Ask before you assume which.

`sources/BACKUP.md` **no longer exists.** It moved to `notes/reference/BACKUP.md` and is now
generated. That was one of the two things `check_archive_layout.py` was failing on.

---

## 2. What is new, by directory

### New directories

| path | what | size | regenerable? |
|---|---|---:|---|
| `sources/town-budget/ocr/` | OCR geometry, 17 TSVs, Apple Vision at raster scale 6.0 | 14 MB | yes, **~2 hours** |
| `sources/town-budget/pages/` | each page as text, two renderings per report | 22 MB | yes, ~5 min — but only from `ocr/` |
| `sources/data/inventory/` | 16 per-report table catalogues, read page by page by an agent | 1 MB | **no, practically** — many hours of agent reading |
| `sources/data/rosters/` | 200 roster page dumps + parsed JSON | 1 MB | **no, practically** |
| `sources/data/verify/` | scratch. `verify_against_page.py` writes page images here on demand | — | yes, delete freely |

`sources/town-budget/docs/` gained the 16 annual town report PDFs (that folder is now
758 MB, 194 files).

### New files in `sources/data/` — 25 datasets, 5 provenance notes

23 CSVs (`report-*.csv` ×12, `annual-report-*.csv` ×4, `placement-counts`,
`ballot-questions`, `special-revenue-funds`, `staff-roster-entries`, `staff-roster-counts`,
`staff-position-map`, `extraction-plan`, `dataset-provenance`), plus
`PROVENANCE-report-tables.md`, `PROVENANCE-placement-counts.md`,
`PROVENANCE-staff-rosters.md`, `PROVENANCE-annual-report-receipts.md`,
`PROVENANCE-special-revenue-funds.md`.

### New documentation

| file | what |
|---|---|
| `notes/reference/ANNUAL-REPORTS.md` | **the entry point.** Generated. Every dataset, where it lives, what state it is in, what is uncaptured |
| `notes/reference/BACKUP.md` | Generated. Every path with size and **how many copies exist** |
| `sources/town-budget/PIPELINE.md` | how a PDF becomes a database row |
| `notes/HANDOFF-ANNUAL-REPORTS.md` | state and open risks of the extraction |
| `notes/findings/TOWN-ARCHIVE.md` | how the reader was built and what broke it |
| `notes/findings/ATHLETICS-LEDGER-FY2024-DRIFT.md` | an unrelated open decision — do not action, do not delete |
| `plans/ANNUAL-REPORTS.md` | the plan for the extraction |
| `notes/generated/` | 4 generated catalogues |

### New scripts — 21

`extract_tables.py`, `pdf_tables.py`, `report_pages.py`, `process_report.py`,
`survey_annual_reports.py`, `build_report_catalogue.py`, `build_extraction_plan.py`,
`build_dataset_provenance.py`, `build_report_anomalies.py`,
`build_report_tables_provenance.py`, `build_staff_rosters.py`, `build_archive_guide.py`,
`extract_annual_receipts.py`, `extract_placement_counts.py`, `verify_against_page.py`,
`verify_report_tables.py`, `check_ocr_orientation.py`, `dump_report_pages.py`,
`dump_roster_pages.py`, `report_annual_report_contents.py`, `render_page.swift`.

---

## 3. What breaks if you move it — the dependency map

**This is the part to read twice.** These are hardcoded paths, not configuration.

### `sources/town-budget/{docs,ocr,pages,text}/` — 11 scripts

    build_archive_guide.py      check_archive_layout.py     dump_report_pages.py
    dump_roster_pages.py        extract_annual_receipts.py  extract_special_revenue.py
    process_report.py           report_pages.py             survey_annual_reports.py
    verify_against_page.py      verify_free_cash.py

Move `docs/` and **every annual-report extractor stops finding its PDFs**. It will not error
loudly in all cases: `extract_tables.py` reads the *page cache*, so it would keep producing
the same rows off stale text while the PDFs sat somewhere else — silently correct-looking
and no longer traceable to a document.

### `sources/data/{inventory,rosters}/` — 5 scripts

    build_report_anomalies.py   build_report_catalogue.py   build_staff_rosters.py
    dump_roster_pages.py        verify_against_page.py

### `sources/town-budget/index.csv` — `build_dataset_provenance.py`

This is the join from every dataset row to its source document, its sha256 and both of the
town's URLs. **It is rule 12's spine.** If a document moves, its `local` column has to move
with it in the same commit.

### `scripts/build_source_index.py` — 30 hardcoded `data/…` item paths

There is a new `annual-reports` group of 30 catalogued items, each naming a file under
`sources/data/`. It fails loudly (`catalogued but not on disk`), which is the intended
behaviour — but it means **moving anything in `sources/data/` breaks the site build**, not
just a check.

### `scripts/build_db.py` — 25 dataset names

The loader names each CSV. A renamed CSV is a missing table, and the 19 reconciliations do
not cover the annual-report data, so **the DB would build clean and be short a table.**

---

## 4. Two reorg items I found but did not action

Both are written up in full at the end of `plans/ARCHIVE-REORG.md`.

**a. The 27 duplicated mirror files.** All byte-identical (verified by sha256, not assumed).
`check_archive_layout.py` says *"delete the `town-budget/` copy"* — but
`sources/town-budget/index.csv` records all 27 under `town-budget/docs/`. Delete alone and
27 index rows point at nothing. It is **two operations that must land together**: delete,
and repoint those rows to `town-supplementary/`. The sha256 in each row does not change.

The cause is `fetch_town_docs.py` testing *"have I got this?"* against one folder only, so a
re-fetch of an already-supplementary document lands a second copy under town-budget. Fixing
that is part of the job, not a follow-up.

**b. `sources/town-annual-reports/` is half-populated.** One PDF (FY2011, byte-identical to
the copy in `town-budget/docs/`) and an `index.csv` with a header and no rows. So FY2011 is a
17th duplicate that `check_archive_layout.py` does not report, because that check compares
`town-budget/` against `town-supplementary/` only. Three files already reference the folder.
Finish the move or delete the folder — one file in it is the state most likely to be
mistaken for done.

---

## 5. Run these before you commit

    python3 scripts/check_archive_layout.py       # is every document where the layout says
    python3 scripts/build_source_index.py         # fails if a file is catalogued and absent
    python3 scripts/verify_source_copies.py       # every copy still the same bytes (slow, ~5 min)
    python3 scripts/check_moved_docs.py           # every address published before a reorg still resolves
    python3 scripts/build_views.py --check        # every symlink in views/ still resolves
    python3 scripts/build_db.py --check           # 19 reconciliations must tie
    python3 scripts/verify_report_tables.py       # 121 stated reconciliations, recomputed
    python3 scripts/build_archive_guide.py --check   # the two generated guides not stale
    python3 scripts/build_dataset_provenance.py   # rebuild the row→document join AFTER moving anything

Current state: **all of these pass except `check_archive_layout.py`**, which fails only on
the 27 duplicates in §4a. That is the one thing you are here to fix.

`check_source_links.py` also passes but takes several minutes and hits the town's site — it
is not affected by a local move, so skip it unless you change a URL.

---

## 6. Things that are NOT yours

- `notes/findings/ATHLETICS-LEDGER-FY2024-DRIFT.md` and the 5 failures in
  `verify_records_request_2026_06.py`. A published headline (44% → 35%) turns on which
  document is authoritative for FY2024 athletics actuals. Flagged at the top of
  `notes/HANDOFF.md`. Leave it.
- The extraction residuals in `notes/HANDOFF-ANNUAL-REPORTS.md`. Nothing there is a layout
  problem.
- `sources/data/verify/` is scratch and can be emptied, but it is not part of the reorg.

---

## 7. The one rule that matters most here

`sources/` is organised by **how a document reached us** — the one attribute that is
single-valued and never changes. Fiscal year, subject and what we use it for are
multi-valued and live in the catalogue and in `views/`, not in a path. Thirteen top-level
folders exist and each is a way a document arrived; a fourteenth is a decision about the
archive, not a place to put a delivery.

And: **a link is not checked until something has been downloaded from it.** After the reorg,
`verify_source_copies.py` is what proves a moved file is still the file.
