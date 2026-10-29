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
| `rosters.csv` | by eye | staff roster pages no table was read on (1991-2000 read tables on financial pages only), `page,printed_heading,source`, for `dump_roster_pages.py` |
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

## One name per quantity -- the 1991-2000 batch, decided 29 October 2026 by the integration pass

| one name | was | what it is | grain | editions |
|---|---|---|---|---|
| family `trust-investment-accounts` (in `report-trust-funds`) | `trust-investment-accounts` (1991, 1993), `trust-funds-interest-ledger` (1992) | the `TRUST and INVESTMENT ACCOUNTS` ledger: PRIOR YEAR BALANCE, PRIOR MONTH INTEREST, CURRENT INTEREST, TRANSFERS, BEQUESTS/DEPOSITS RECEIPTS, GRANTS & GIFTS/WITHDRAWALS, BALANCE. A THIRD trust layout: never summed with `trust-funds-book` or `trust-funds` | one account | 1991-1993 |
| `report-tax-bill-breakdown`, family `tax-bill-breakdown` | `tax-bill-breakdown` (1995), `average-tax-bill` (1996) | the Board of Assessors' BREAKDOWN OF THE AVERAGE RESIDENTIAL TAX BILL for the coming fiscal year: budgeted amount by town service, under eight category rows, with the Assessors' own percent-of-levy and cost-to-the-average-taxpayer arithmetic. A BUDGET (rule 1), never an actual | one service (or one category row) | 1995, 1996 |
| families `gross-wages-school` and `gross-wages-town` (in `report-gross-wages`) | `gross-wages` (1995-1998, 2000; 1999's town list), `gross-wages-school` (1999's school list) | the two wage lists 1995-2000 print, each with its own layout (the school list prints a GRADE / DEGREE / STEP column) and its own printed total, never a combined one. 2001-2010 print one combined list and stay `gross-wages`. Period: as printed (`REPORT OF WAGES PAID`, `GROSS WAGES 1995`) -- never calendar or fiscal unless the page says so | one employee | 1995-2000 |
| `report-property-tax-exemptions` (NEW) | (1991 only) | the Assessors' summary of exemptions by statutory clause (17D, 22, 41A, c.61 ...): a RULE, with the amount in prose; no money granted | one clause | 1991 |
| `report-treasurers-then-and-now` (NEW) | (1991 only) | the Treasurer's comparison of the office's workload thirty years apart; mixed units, one statistic per row | one statistic | 1991 |
| `report-highway-accounts` (NEW) | (1995 only) | the Highway Superintendent's own APPROPRIATED / EXPENDITURES / BALANCE by account, to the dollar. Not the accountant's schedule, which differs line by line | one account | 1995 |
| `report-vehicle-inventory` (NEW) | (1995 only) | highway vehicles and equipment as of March 1996: year, make, mileage. No money | one vehicle | 1995 |

**Mid-year changes to voted budget lines: the same quantity and stage, three layouts.** A VOTED
change to the current year's omnibus lines at a special town meeting is one quantity (a budget,
amended), printed three ways, so each layout keeps its own family and none is ever summed with
`omnibus-budget`: `omnibus-amendment` (`Additional | <prior vote> | New Approp`: 1991, 1995, 1998,
2002; 1991 p52 prints only the new amount), `stm-budget-adjustments` (`AMOUNT | NEW TOTAL` 1993;
`prior | adjustment | amended` 2004), `supplementary-budget` (the supplement alone, 1992). A
PROPOSED change is a different stage (rule 1) and lands in `report-warrant-article-amounts`:
`budget-amendment-proposed` (1996 Article 2, whose vote changed two of the five lines, printed in
prose under the table) and `budget-supplement-passed-over` (1991 Article 7). `exemptions-abatements`
(1997, in `report-valuation`) is a count and dollar total of exemptions and abatements granted
per fiscal year, never summed with the overlay lines.

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

Added by the 1991-2000 integration pass (29 October 2026); each 1991-2000 NEEDS.md ends with
what was done with each of its items:

- **calendar-only readings** (`CALENDAR_REPAIRS` in `read_report_tables.py`, kept OUT of
  validate_totals.REPAIRS so nothing the FY reviews parse can move): a trailing footnote mark
  (`($135,987.00) *`, `#`), a full stop after a negative, angle brackets for a negative
  (`<$ 1,343>`), a comma for the decimal point (`0,13452`, `$ 19,548,51`), full stops for both
  separators (`$105.636.70`), the amount and the years payable in one cell (`$330,000 1986-95`);
  and per COLUMN: `$330.000` and `S390` in a column of whole dollars, `150.` in a column of
  whole dollars ending in full stops. One figure per cell only (`10.00 2.00` is two fees).
- **identifiers**: a sub-line `914.1` is a line number; a table of amounts may print them with a
  comma and no `$` (`64,935`).
- **one-row tables**: a column holding a `$` figure is a figure column (`$8327.`, 1992 p52).
- **wage lists**: a GRADE / DEGREE / STEP column, or any column with no figure-shaped cell, is
  part of the label, so the wage is v1; a printed total closes its OWN list (the map rows from
  the one after the previous total through the one that carries it); a figure sharing a line
  with its label, and the list's own total printed outside the table, are read as such.
- **row identities**: collection of taxes without ADJUSTMENTS (and `REFUND`, singular -- the
  emitter now takes it, which it dropped); special revenue headed TOTAL REVENUE / TOTAL
  EXPENDED, with and without TRANSFERRED; the 1991 accountant schedule (BALANCE REVENUE, blank
  read as zero only on a row printing an AVAILABLE figure); `trust-investment-accounts`;
  `omnibus-amendment` and `budget-amendment-proposed` (Additional + prior vote = New).
- **list totals**: an item list whose total sits outside its table, spans tables, groups or
  pages (`stated_total` on omnibus budgets, bonds authorized and unissued, trust summaries,
  warrant-article lists) is summed against it -- `no check` rows become `checked` or `check
  failed`; a whole-dollar total over items with cents ties within its rounding.
- **category blocks**: the tax bill breakdown's category rows close on the lines below them.
- **receipts** split into several tables on one page are pooled against the one GRAND TOTAL.
- **treasurer's cash**: an unlabelled last row with one figure is the total, wherever its
  column; the reconciliation takes `DISBURSE` as well as `DISBURSED`.
- **column checks** (validate_totals gained an optional `names_of`, which no FY review
  passes: their outputs are byte-identical, `--json` compared on FY2011, FY2020 and the 2000
  review): a continuation table takes the names of the table its `header_from` names, which may
  be FORWARD (1997 p61 continues p62); an AVERAGE column is left out of the column checks; and
  where `edition.json` says `"validator_drop_titles": true` (1993 only), the running title is
  dropped from the names -- NOT by default, because joining an accountant schedule's pages
  exposes the block walk's grouping instead (2003 +68 false failures, 1999 +51, 2000 +70).
- **page subjects** follow the dataset a page was landed in where the keyword classifier
  disagreed (the omnibus budget is not `regional-school` for one MONTY TECH line). Receipts have
  no subject in that vocabulary and are left to the classifier.

## The glyph witness: `glyph-witness.csv`

`scripts/witness_dollar_glyphs.py <edition>` (`--check`). On a wage page where most figures print
`$`, a figure with no `$` that begins with a glyph Textract confuses with one (`8`, `3`, `5`) is
decided from the PDF's pixels: its first glyph is compared with the page's own `$` signs and its
own digits, the cell's width must agree with the reading, and a negative control on the known
digits must call none of them `$`. Decided `$` -> the reading replaces Textract's; undecided ->
the cell has NO value and its row is `check failed`, `AMBIGUOUS`. Only 2009 has such cells today.
It reads every wage family (`gross-wages*`). On 1996 it finds suspect cells and REFUSES (its
negative control calls 7 known digits `$`), so it cannot decide them; there the printed totals
do part of the work instead. The school list (pp96-102; suspects on pp97-100) sums to its
printed $6,709,600.54 to the cent over its printed 318 employees, which an inflated leading
digit could not survive. The town list (suspects on p94) is NOT settled: it is one employee and
$5,171.00 SHORT of its printed total and count, and an inflated cell inside it would only be
hidden by a larger missing one -- so its p94 rows are `checked` by coverage alone, the check
the witness exists to back up. Open.
Why it exists: the coverage check's witness is Textract's own line output, which shares the
misread, so it passed all 90 inflated wages as `checked`.
