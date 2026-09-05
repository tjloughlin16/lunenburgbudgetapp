# Handoff: fifteen years of annual town reports

Written 5 September 2026, at the end of a long session. **Nothing is committed.**

**The index is `notes/reference/ANNUAL-REPORTS.md`** — what exists, where it lives, what
state it is in, what is uncaptured. Generated, so its counts cannot drift. This file is only
the state and the open risks.

Read `plans/ANNUAL-REPORTS.md` for the plan and `notes/findings/TOWN-ARCHIVE.md` for how
the reader was built and what broke it. This file is the state and the open risks.

---

## The one thing to understand first

These reports are the **official record** — Town Manager and Finance Committee approved,
carrying tables exported from MUNIS. There is nothing more authoritative to check them
against. So the question is never whether the town's figure is right. It is only ever
**whether we transcribed it faithfully**, and a table that prints no total is not less
authoritative — it simply cannot be checked by arithmetic and must be checked by reading
the page.

The `status` vocabulary says which:

| value | meaning |
|---|---|
| `checked` | a check existed and it passed |
| `check failed` | a check existed and it did not pass — **look at this** |
| `no check` | no total, no identity; verify by reading the page |

`row_check` and `derived_cell` carry the per-row version.

---

## What is on disk (back this up: `sources/`, 1.5 GB)

| path | what | cost to lose |
|---|---|---|
| `town-budget/docs/` | the town's PDFs, the primary source | **irreplaceable if links die** |
| `town-budget/ocr/` | OCR geometry, 16 TSVs | ~2 hours compute |
| `town-budget/pages/` | page text, two renderings each | ~5 min |
| `data/inventory/` | 863 catalogued tables, read page by page | many hours of agent reading |
| `data/rosters/` | 100 roster pages + parsed JSON | many hours of agent reading |
| `data/*.csv` | 55 files: the datasets, provenance, plan | seconds |
| `data/lunenburg.db` | derived read model | seconds |

`notes/reference/BACKUP.md` and `sources/town-budget/PIPELINE.md` explain each stage.
**No page images are stored** — they are regenerated on demand by `render_page.swift`.

---

## Where the data stands

**13,926 rows in the twelve generic extracts**, plus the six hand-built datasets.
19 of 19 pre-existing project reconciliations still tie. `verify_report_tables.py`
recomputes all 121 reconciliations these files state about themselves, and they match.

Every one of them is now **catalogued on the public sources page** with a title, a blurb
and the caveat that governs it — `scripts/build_source_index.py`, group
`annual-reports` — and `sources/data/PROVENANCE-report-tables.md` is the generated
document a reader should meet before quoting any figure out of them.

**Trustworthy now**

- `placement-counts` — 15 years, FY2011–FY2025. Answers a standing question `CLAUDE.md`
  recorded as unpublished. Parts sum to the total in every year; each year's stated prior
  figure matches its predecessor.
- `staff-roster-entries` — 3,815 entries, 15 years, 7 schools, 100 pages. Every line
  accounted for; one known defect (a hyphen-wrapped surname).
- `ballot-questions` — 7 records, every tally verified against its own precinct figures.
- `annual-report-receipts` — 504 rows tie to the report's printed GRAND TOTAL, twice over.
- `report-elections` — 1,573 rows prove themselves (parts sum to printed total), 56 more
  have a lost cell derivable from the row.
- `special-revenue-funds` — 693 rows prove themselves via the fund identity
  (forward + receipts − disbursements = carried forward), 351 cells recovered from it.

**Not trustworthy yet**

- `report-appropriations` — 4,665 rows, two table families. **The "within 1–4%" this file
  once reported was cancellation, not agreement**; see the section below. Now reconciled on
  the NAMED column wherever the columns could be established. Closest: the FY2016 omnibus
  at **+$45 on $33.8M** and FY2015's at **−$1,020 on $32.0M**; the accountant's schedule
  is closest in FY2020 at **+$33,741 on $43.1M**. Nothing ties to the cent yet.
- `report-gross-wages` (3,545), `report-officials`, `report-dept-activity`,
  `report-enrollment-mcas`, `report-monty-tech`, `report-vital-records`,
  `report-valuation` — **no check available**. Spot-verified only.

---

## What was wrong, and what is now known

The open risk this file carried through the last session (`mark_arithmetic_subtotals()`
eating real rows) was real and second-order. What was actually wrong was worse and had the
opposite sign of what it looked like.

**`v1` is an ORDINAL, not a column.** It means *the first column on this page that held
figures*. The ruler is built per page, so v1 is not the same printed column twice: FY2011
page 62 put TOTAL AVAILABLE there, page 64 put APPROPRIATED there, page 61 has only three
of the six columns at all. The run reconciliation summed all of those together and compared
the result to a printed appropriation. **FY2011 came out within 1% of its own printed total
by cancellation** — compensating errors producing a check that passed because it had no
power to fail. Reconciled on the named column it is −$1,514,660.

That is fixed, and so are eight other things. All of it is in `scripts/extract_tables.py`,
each with the case that forced it written beside it.

| what | how it is settled |
|---|---|
| columns named | `name_columns()` scores every ordered assignment of the six printed names against the table's own identities — `available = appropriated + forward`, `balance = available − expended − encumbered`. **4,353 of 4,665 appropriations rows** carry a `column_meaning`; the rest say `not established` and their runs say the v-numbers are ordinals, in those words, on every column they quote |
| two tables in one dataset | `table_family` discriminates the Town Accountant's schedule (2,760 rows) from the town meeting omnibus budget (1,905). They share nothing but a subject and must never be averaged together |
| the omnibus read by ruler | it has one money column and no identity, so it is read by walking the line. That also handles the **side-by-side panels** — FY2015 p140 prints two votes per printed line, and reading across paired `Town Accountant` with the police, fire and buildings total |
| page furniture appropriated | the footer legend (`fwd - forward from FY 2015  $265,386.55`) and 69 page numbers were budget lines. $207k–$838k a year |
| subtotals missed | the identity is tested in **every** column, not the first. FY2022 went +$28.7M → −$4.8M. A labelled row must tie in two columns; an unlabelled one in one |
| `Subtotal Police` | `is_total()` matched only TOTAL. $2.8M double-counted in FY2016 alone |
| grand total lost to the ruler | row kind is read off the page line, not off our cut of it |
| the grand row compacted | the check paired our v4 sum against the report's v5 whenever the grand row had a blank column — the shift this extractor exists to prevent, inside the check |
| line numbers appropriated | money in the omnibus always prints its cents or its separator; a bare `37` is a line number |

**A new check that the table supplies itself:** the omnibus numbers its own lines, so a gap
in the numbering is a missing row. FY2021 runs 78, 79B, 80 — line 79 is the school
department, $21.6M of a $39.9M budget, and it is absent from both renderings of both pages
it could be on. Nothing else in the extraction could have told us that.

### What is still wrong, in order

1. **Rows the chosen rendering does not contain.** The extractor picks OCR or the text layer
   per page for its columns and never notices the other holds more rows. `County Retirement
   Assessment $967,652.00` is printed on FY2016 page 30, is absent from Vision's OCR of that
   page, and is absent from the dataset. **22 money pages** fail this audit — 11
   appropriations, 8 gross wages, 2 debt, 1 valuation. It is why FY2016/FY2017/FY2018 are
   $4–8M short. The omnibus reader already fixes it for its family by taking whichever
   rendering holds more lines; the accountant's schedule cannot, because it needs the
   geometry.
2. **The 312 rows with no column names.** Mostly FY2012 p60–64, FY2013 p67–68, FY2014 p24
   and FY2023 p31, where the OCR is degraded enough that no assignment beats chance. Those
   pages need reading, not more inference.
3. **FY2012** compares against a "printed total" of $1,032,000.00, which is not one.
4. **Trust funds FY2017 and FY2020** read their own grand totals as −$19.00 and $7.00.
   `verify_report_tables.py` names them and says plainly that it is our reading of the
   TOTAL that is not credible, not the rows.

## Claims that are NOT established

- That `v1` is APPROPRIATED. It is an ordinal. Read `column_meaning`, which says what the
  columns are on that row's page or says they are not established.
- That a run reconciling closely has been checked, unless its reconciliation names the
  column. A positional reconciliation adds one page's column to another page's different
  column.
- That any `check failed` row is wrong. It means our total and the printed total disagree;
  the row may be right and a neighbour wrong.
- That `no check` means unreliable. It means unverified by arithmetic.
- That the catalogue's cross-year grouping is fact. It clusters on plain-English names and
  is a hypothesis about which tables are the same table.
- That `valuation` covers FY2020–FY2025. It does not; those years have no valuation pages
  in the plan.
- That a staff roster count is a staffing level. No FTE, no funding source, a point in time.
- That `report-gross-wages` is complete. Two-panel pages were mishandled until late and
  only FY2025 p177 was verified after the fix.

---

## Next steps, in order

1. **Recover rows the chosen rendering does not hold** — the largest remaining defect.
   The diagnostic is cheap: for each page, count figure rows in both renderings and flag
   where the unused one has more. What is NOT cheap is recovering them faithfully — a line
   read by trailing figures has no column positions, and a line ending `fwd` puts its
   amount in a different column from one that does not. Do not write a recovered value into
   a named column without establishing which column it is.
2. **Read the pages where columns cannot be established** — FY2012 p60–64, FY2013 p67–68,
   FY2014 p24, FY2023 p31. Inference has done what it can there.
3. **FY2012 appropriations** — the row taken as GRAND TOTAL is not one.
4. **Verify the six unchecked datasets by page**, using
   `python3 scripts/verify_against_page.py <dataset> <edition> [--pages N]`, which renders
   the page beside the rows extracted from it. Two such passes found nine defects that no
   arithmetic could have surfaced.
5. **Provenance docs** for the 11 datasets without one.
6. **Verifier scripts** that recompute, in the style of `verify_athletics.py`.
7. `CLAUDE.md` rule 11 and the standing questions are already corrected; re-read them
   against the current data before publishing anything.

---

## Tools worth knowing

    python3 scripts/report_pages.py --rebuild          # page cache (5 min) — REQUIRED after any OCR change
    python3 scripts/extract_tables.py <dataset>        # generic extractor, 15 datasets
    python3 scripts/extract_tables.py --list
    python3 scripts/verify_against_page.py <ds> <ed>   # page image beside the extracted rows
    python3 scripts/check_ocr_orientation.py <dir>     # are any pages sideways
    python3 scripts/process_report.py FY2019           # one report end to end, gated
    python3 scripts/build_db.py                        # reload; 19 reconciliations must tie
    python3 scripts/verify_report_tables.py            # every stated reconciliation, recomputed
    python3 scripts/build_report_tables_provenance.py  # the provenance doc, from the data
    python3 scripts/build_source_index.py              # every dataset described, or it fails

**The instrument is part of the finding — check it before you believe it.** Twice in one
session a measurement was wrong because the thing doing the measuring was. `MONEY_TOKEN`
is `[\d,]+\.\d\d`, so on the FY2019 and FY2023 scans — where OCR renders thousands
separators as full stops — it counts `$89.617.70` as two tokens, and a capture rate
computed against it said those years were losing a third of their figures. `amount()`
parses them correctly and the real capture is 99%. And `column_ruler`'s `blank_frac` is a
constant that decides how much of a page is readable at all: at 0.92 it merged two columns
on FY2011 page 64 and 55 of that page's 98 figures parsed as nothing.

**A fix upstream of the page cache does nothing until the cache is rebuilt.** That cost an
hour once: the flip correction was verified working on raw geometry, the extractors were
re-run, and the output was unchanged — because they read the cache.
