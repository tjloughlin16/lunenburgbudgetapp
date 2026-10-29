# report-tables: one folder per annual-report edition read from Textract

The 1959-2010 annual town reports are read one edition at a time, possibly by several agents at
once. A worker writes ONLY inside its own edition's folder here; `scripts/merge_report_tables.py`
is the one thing that writes the shared datasets. Rule and reasons:
`notes/PLAN-ANNUAL-REPORT-PIPELINE.md` section 4a.

## Layout of `report-tables/<edition>/`

| file | written by | what it is |
|---|---|---|
| `edition.json` | a person / agent, by eye | edition key (`2010`), `fy`, `basis` (`calendar`), the PDF, its stem, and `periods`: the financial period of each statement, **quoted from the page that prints it** |
| `map.csv` | by eye | EVERY Textract table on every page (page, table): the `dataset` it lands in (empty = not landed, with the reason in `note`), `family`, a plain `name`, `grain`, `financial` (yes = the page belongs in the page map), `layout` (`groups:N` when N tables are printed side by side), `header_from` (`page/table` whose printed header a headerless continuation uses), `stated_total` (a total the page prints in prose), `period_fy`, `period` |
| `gaps.csv` | by eye | rule 7c gap candidates (`side,what,why`, `why` ending `— closes: <document>`): what a modern dataset holds that this edition does not print, with what was searched |
| `tables.csv` | `read_report_tables.py` | the inventory: every table, its printed header cells, the page's top lines |
| `rows/<dataset>.csv` | `read_report_tables.py` | the rows for each target, **in that shared file's own columns** |
| `pages.csv` | `read_report_tables.py` | page-map rows in `annual-report-pages.csv`'s schema; `state` by `map_annual_report_pages.PROOF` |
| `catalogue.csv` | `read_report_tables.py` | `annual-report-catalogue.csv` rows: what each table is, and where it landed |
| `notes.csv` | `read_report_tables.py` | what each bespoke emitter decided (a column refused, a total that did not tie) |
| `glyph-witness.csv` | `witness_dollar_glyphs.py` | wage cells whose `$` Textract may have read as a digit, decided from the page's own glyphs (only where such cells exist) |
| `NEEDS.md` | the worker, then the integration pass | shared-code changes the edition needed, and what was done with each |

## Running one edition

    python3 scripts/read_report_tables.py 2009 --inventory   # tables.csv, to write map.csv against
    # write edition.json, map.csv, gaps.csv BY EYE
    python3 scripts/read_report_tables.py 2009               # rows, pages, catalogue
    python3 scripts/read_report_tables.py 2009 --check

Then, ONCE, after every worker has finished (never by a worker running in parallel):

    python3 scripts/merge_report_tables.py && python3 scripts/merge_report_tables.py --check
    python3 scripts/build_db.py

## How a row is told apart from the FY2011-FY2025 rows

By its `edition` column (`2010`, never `FY2010`), or for files with no `edition` column, by its
`document` naming this edition's PDF. The merge keeps every other row as the raw bytes it was.

## One name per quantity -- decided 28 October 2026, by the integration pass

The ten 2001-2010 workers each named a NEW quantity the first time they met it, so the same thing
arrived under several names. Rule 1 decides a merge: same quantity, same stage, same grain. A
similar heading is not a match. Every new dataset has the GENERIC `report-*` columns.

| one name | was | what it is | grain | editions |
|---|---|---|---|---|
| `report-treasurers-cash-reconciliation` | `report-cash-reconciliation` (2001, 2005), `report-treasurers-cash-reconciliation` (2002-2004), `report-treasurers-reconciliation` (2006), and the block above the accounts inside `treasurers-cash` (2007, 2008) | the Treasurer's cash ROLL-FORWARD for the fiscal year: opening balance, receipts less investments transferred, disbursed less revenue cash invested, general ledger balance. An actual, a flow; `treasurers-cash` is the closing STOCK by account and stays separate | one printed line; family `cash-reconciliation` | 2001-2008 |
| `report-fee-schedule` | `report-weights-measures-fee-schedule` (2003), `report-fee-schedule` (2004) | a fee RATE set by town meeting vote -- the Sealer's fee per device (2003, family `sealing-fee-schedule`), the Town Clerk's fees (2004, family `town-clerk-fees`). Not money collected: `report-weights-measures` is the Sealer's activity and stays separate | one fee | 2003, 2004 |
| `report-special-education` | `report-special-services` (2009), `report-special-education` (2008) | the Special Services report's statistics tables: shares by disability type, state indicators. Family names the table (`disability-types`, `dropout-rate`, `educational-environment`, `evaluation-timelines`, `early-childhood-transition`) | one printed line | 2008, 2009 |
| `report-library-service-values` | (2004 only) | the library's own ESTIMATE of its services' value to residents | one service | 2004 |
| `report-warrant-article-amounts` | (2001 only) | per-project amounts inside a warrant article (Article 8, 2001, PASSED OVER): a proposal | one project | 2001 |

And within an existing dataset, one FAMILY name per layout: the 2001-2005 trust fund book
(`ALLOCATION | BEG BAL | DIVIDENDS | CONTRIBUTIONS | REDEMPTIONS | BOOK BALANCE`) is
`trust-funds-book` in every edition (it was `trust-funds` in four and `trust-funds-book` in one),
so it is never summed with the 2006-2010 `trust-funds` layout, whose ending cash it does not print.

## What the reader does that the workers asked for (NEEDS.md, applied once)

Each folder's NEEDS.md ends with what was done with each of its items, and why where it was not.
In the shared code:

- **map columns** `header` (`none` | `row:N` | `skip:N`), `layout=spans:...`, `copy`, `checks=none`
  -- documented at the top of `scripts/read_report_tables.py`.
- **headers**: a first row that reads as data is data; Textract's empty first row is the
  missing header; a row of dates is the header wherever it sits; the page's running title is
  not part of any column name; `header_from` always wins when the map names it; the header of a
  money table stops at the first row of counts (validate_totals.split_header).
- **identifiers** (a fund number or range, a line number, left of the first text column of a
  table of amounts) are part of the label, not a figure; a numbered line with no amount is a row.
- **parser marks** (validate_totals.REPAIRS): `S` for `$`, a trailing `+`, `;` for `,`, whole
  dollars ending in a full stop. Proved not to change one check of the FY2011, FY2020 or 2000
  reviews.
- **percents** are figures, `[percent]` in `column_meaning`, outside every column check.
- **row identities** for the 2006, 2007 and 2009 trust fund layouts, 2007's debt header, and
  2004's `PRE A` precincts. NOT the blank-balance-as-zero identity: on 2010 it fails in offsetting
  pairs within a department, on correct figures.
- **emitters**: treasurer's cash takes its total from a labelled row, an unlabelled lone figure,
  or the map's `stated_total`, and hands a roll-forward block to the reconciliation emitter,
  which checks its chain DOWN the page; capital plans take `copy` from the map; wage pages carry
  a printed GRAND TOTAL tie where the map gives one.
- **pages**: a financial page the map says is `NOT LANDED` is `refused`, not `unread`.
- **stale rows**: a dataset a folder no longer produces is removed from its `rows/`.

## The glyph witness: `glyph-witness.csv`

`scripts/witness_dollar_glyphs.py <edition>` (`--check`). On a wage page where most figures print
`$`, a figure with no `$` that begins with a glyph Textract confuses with one (`8`, `3`, `5`) is
decided from the PDF's pixels: its first glyph is compared with the page's own `$` signs and its
own digits, the cell's width must agree with the reading, and a negative control on the known
digits must call none of them `$`. Decided `$` -> the reading replaces Textract's; undecided ->
the cell has NO value and its row is `check failed`, `AMBIGUOUS`. Only 2009 has such cells today.
Why it exists: the coverage check's witness is Textract's own line output, which shares the
misread, so it passed all 90 inflated wages as `checked`.
