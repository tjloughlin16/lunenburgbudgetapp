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

---

# UPDATE — 5 September 2026, after `town-annual-reports/` was populated

Written after observing the move, not before it. **Everything below is tested, not
predicted.** I stopped as soon as I understood what had happened and changed nothing.

## What moved

| | before | now |
|---|---|---|
| the 16 annual report PDFs | `sources/town-budget/docs/` | `sources/town-annual-reports/docs/` ✅ |
| their extracted text | `sources/town-budget/text/` | `sources/town-annual-reports/text/` ✅ |
| their 16 index rows | `sources/town-budget/index.csv` | `sources/town-annual-reports/index.csv` ✅ |
| **their OCR geometry** | `sources/town-budget/ocr/` | **still there — 17 files** ❌ |
| **their page cache** | `sources/town-budget/pages/` | **still there — 32 files** ❌ |

The move is half done. `ocr/` and `pages/` are derived *from the annual reports* and belong
with them; they are sitting in the folder the reports left.

## What broke, and why you will not see it break

**Eight scripts hardcode `sources/town-budget/docs` and now see zero annual reports.**

    report_pages.py            survey_annual_reports.py   extract_annual_receipts.py
    extract_special_revenue.py verify_against_page.py     dump_report_pages.py
    dump_roster_pages.py       build_archive_guide.py

**None of them errors.** `report_pages.py` walks an empty glob and rebuilds a cache of
nothing. `verify_against_page.py` cannot render the page it is meant to check against.

**And the extractors keep working, which is the trap.** `extract_tables.py` reads the *page
cache*, not the PDFs — so it still produces byte-identical output:

    $ python3 scripts/extract_tables.py vital_records
    all 14 planned edition(s) produced rows
    vital_records: 96 rows, 15 editions

That is the failure mode §3 of this file warned about, now real: **rows that look correct
and are no longer traceable to a document.**

## The one that actually matters: rule 12's spine is severed

`scripts/build_dataset_provenance.py` hardcodes `sources/town-budget/index.csv` and filters
for `annual-town-report` in the `local` column. It now finds **0 of 16**.

    0 of 225 provenance rows resolve to a document

Every annual-report dataset has lost its address, its publisher label, both of the town's
URLs and its sha256. `sources/data/dataset-provenance.csv` still has 225 rows; the
`document`, `publisher_label`, `upstream`, `sha256` and `bytes` columns are now **all
empty**.

**It exits 0 and prints a reassuring line.** It still says
`16 source documents, all with an address and a sha256` — because that counts what it found
in the index it was pointed at, before the join. Then it writes 225 rows with empty
provenance and succeeds. Nothing in the check suite catches this.

## Fixes, in the order they matter

1. **`build_dataset_provenance.py` must read every `sources/*/index.csv`, not one.**
   There are six: `district-budget`, `meetings`, `state-dese`, `town-annual-reports`,
   `town-budget`, `town-supplementary`. Keying on the filename rather than the folder makes
   it survive the next move too.
2. **Make it fail when the join does.** A run that resolves 0 of 225 rows must exit non-zero.
   That single guard would have caught this at the moment it happened. Suggested: fail if
   any dataset resolves none of its editions.
3. **Move `ocr/` and `pages/` to `sources/town-annual-reports/`** and update the four path
   constants in `report_pages.py` (`DOCS`, `OCR`, `PAGES`) and the seven other scripts above.
   Note `sources/town-budget/ocr/` and `pages/` may also hold non-annual-report material —
   check before moving wholesale.
4. **Rebuild in this order afterwards**, because each reads the last:

       python3 scripts/report_pages.py --rebuild        # ~5 min, needs the PDFs findable
       python3 scripts/extract_tables.py <each>         # or scripts/process_report.py
       python3 scripts/build_dataset_provenance.py      # the join — check it is not 0
       python3 scripts/build_report_tables_provenance.py
       python3 scripts/build_archive_guide.py
       python3 scripts/build_db.py --check
       python3 scripts/verify_report_tables.py
       python3 scripts/build_source_index.py

5. **`check_archive_layout.py` needs to know `town-annual-reports/` is legitimate** — it is
   a fourteenth top-level folder, which that check is written to refuse.

## What I did NOT do

Nothing. No file was edited, moved or deleted after the move was noticed. The datasets in
`sources/data/` are the ones produced before it, and they are unchanged and still correct as
readings — it is only their link back to the documents that is gone.

## The backup predates all of this

`/Users/tj/lunenburgbudgets-backup-2026-09-05/lunenburgbudgets-2026-09-05.zip` was taken at
11:19, before the move, and holds `sources/town-budget/index.csv` **with** its 16
annual-report rows. If the index rows need recovering rather than regenerating:

    unzip -p .../lunenburgbudgets-2026-09-05.zip \
      lunenburgbudgets/sources/town-budget/index.csv | grep annual-town-report

A remote copy of that zip also exists.
