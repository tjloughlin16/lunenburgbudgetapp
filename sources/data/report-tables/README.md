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

**29 October 2026, TJ: a $1 rounding tolerance on the calendar editions' total checks.** Every 1991-2010 `edition.json` carries `"rounding_tolerance_usd": 1`: a printed total within $1.00 of the sum of its rows counts as closing (status `checked`), and the row's `reconciliation` says `within $1 rounding tolerance (printed differs by $N)` so it stays countable. It is a DOLLAR tolerance, off for percent and rate columns and for election pages. Rounding is the likely cause of the Unit 2 debt schedules ($1 off GRAND TOTAL INTEREST) but nothing here tests it; the Treasurer's bond schedule or the Accountant's debt ledger would. The annual-reports page carries this as a generated caveat.

## One name per quantity -- the 1986-1990 batch, decided 29 October 2026 by the integration pass

| one name | was | what it is | grain | editions |
|---|---|---|---|---|
| `report-auditors-cash-schedule` (NEW) | `report-auditors-cash-schedule` (1986), `report-auditor-cash-schedule` (1987, 1988) | the AUDITOR's own schedule of the Treasurer's cash and investments at the close: balances by fund, opening and closing, and their composition by bank account. A second printing, by another officer, of the stock `treasurers-cash` holds; never summed with it. Families by LAYOUT: `cash-by-fund` (1987 p9/1, 1988 p10/1: General and Revenue Sharing Fund cash at the two dates, then the cash composition), `investments-by-fund` (1987 p9/2, 1988 p10/2 -- 1988's was mislabelled `cash-by-fund`), `investments-composition` (1986 p11/3, 1988 p10/3, was `investment-accounts`), and 1986's own `cash-reconciliation-schedule` (a roll-forward: opening + receipts - disbursements), `cash-composition`, `investments-schedule` (opening + purchases - maturities), `trust-custody-composition` | one fund or one account | 1986-1988 |
| `annual-report-receipts` (EXISTING) | `report-statement-of-receipts` (1986) | the Treasurer's DETAILED STATEMENT OF RECEIPTS, by source: the same quantity, stage and grain every edition 1987-2010 lands here. Read by the span emitter (`receipts_span`, below); 1986's unlabelled section subtotals are not accounts | one revenue account | 1986-2010 |
| family `tax-levy-history` in `report-valuation` (EXISTING dataset) | `report-tax-levy-history` (1987), `tax-levy-history` in `report-valuation` (1988) | the property tax LEVY by fiscal year with its percent increase, as the Town Clerk (1987 p27) and the Treasurer (1988 p30) print it. 2000-2010 print the same quantity, with more columns, as `Valuation and tax history` in `report-valuation`, family `valuation`; the levy-only chart keeps its own family. 1988's FY1990 line prints `(est)`: an estimate in a column of actuals, labelled as printed | one fiscal year | 1987, 1988 |
| family `cash-reconciliation-revenue-sharing` in `report-treasurers-cash-reconciliation` | 1986 p46/1 (`reconciliation` in `report-revenue-sharing`), 1987 p30/2 | the federal General Revenue Sharing fund's own cash roll-forward, read down the page by the same chain as the General Fund's. A SEPARATE family so its ledger balance is never summed with the General Fund's (the emitter used to write every table as `cash-reconciliation`; it now keeps the map's family) | one printed line | 1986, 1987 |
| `report-revenue-sharing` (NEW) | (1986 only) | the revenue sharing fund's RECEIPTS by source and PAYMENTS by purpose (p46/2-3), each closing on its printed total | one source or purpose | 1986 |
| `report-statement-of-payments` (NEW) | (1986 only) | the Treasurer's DETAILED STATEMENT OF PAYMENTS by department and object. An actual (rule 1); no other edition prints it | one printed line | 1986 |
| `report-fund-balance-sheets` (NEW) | (1986 only) | one balance sheet PER FUND with a single amount column (general fund liabilities, assets, fund balance and long-term debt; trust funds in custody; revenue sharing). `balance-sheet` publishes per fund COLUMN of a combined sheet and cannot hold these | one printed line | 1986 |
| `report-treasurers-cash-calendar-year` (NEW) | (1986 only) | a SECOND Treasurer's reconciliation for the CALENDAR year ended 31 December 1986, with its account list. The same kind of quantity as `report-treasurers-cash-reconciliation` but a different PERIOD in a file whose `fy` would read 1986 for both: kept apart so the two are never summed or compared as one year | one printed line | 1986 |
| `report-vendor-payments` (NEW) | (1986 only) | payments over $4,000 to one payee in fiscal 1986 (MGL c.40 s.4G), name and address in one cell. Businesses are named (the redaction principle identifies providers); SIX payees printed `Surname, Given` with a street address are private individuals paid as persons and were held out (`edition.json` `withheld_rows`) until TJ decided; RELEASED 30 October 2026, see *Publishing names* below | one payee | 1986 |
| `report-school-staff-fte` (NEW) | (1986 only) | School Department staff in FTE by role and school -- a headcount-equivalent, not a roster and not a payroll | one role | 1986 |
| `report-school-state-aid` (NEW) | (1986 only) | the School Committee's table of state aid by chapter against the school appropriation, FY-85 to FY-87: RECEIPTS for the past years, an estimate for the coming one, labelled per column | one chapter | 1986 |
| `report-school-special-accounts` (NEW) | (1986 only) | the School Department's revolving, grant and article accounts (`Summary of Special Accounts FY 86`) | one account | 1986 |
| `report-agency-funds` (NEW) | (1987 only) | money the Town held for others at the close (payroll withholdings, union dues, deposits) | one account | 1987 |

Families added inside existing datasets, each a layout of its own and never summed with another:
`report-trust-funds` `trust-fund-bank-accounts` and `trust-fund-rollforward` (1986), `trust-fund-accounts`
and `trust-fund-rollforward` (1987), `trust-accounts-by-bank` (1988); `report-debt`
`debt-by-issue-principal-interest` (1988), `debt-temporary-borrowing` (1988, was `temporary-borrowing`;
1989) -- notes in anticipation of revenue, borrowed and not bonded; `report-fee-schedule`
`school-tuition-rates` (1986: a per-pupil RATE set from the State's cost, not a fee collected).

## What the reader does for the 1986-1990 batch (29 October 2026)

Every new reading is a per-edition OPT-IN in `edition.json` wherever it would change what an
earlier edition publishes -- proved by re-running all 25 folders with `--check` (1991-2010 reproduce
byte for byte) and by splitting every shared dataset on `fy`: FY2011-FY2025 rows are byte-identical
to HEAD and every shared file is a pure append. The opt-ins (`OPTS` in `read_report_tables.py`):

- `accountant_marks`: `$2523.60 rct`, `RF`, `ret`, `TR`, `Ewd` (Textract's `fwd`) after an
  APPROPRIATED FORWARD figure, as `fwd` already was. 1991 prints `RF` too, which is why it is an opt-in.
- `stop_for_comma_without_dollar`: `54.587` in a column of whole dollars with commas elsewhere (1990).
- `id_column_words`: a line-number column that also holds the first words of a series label
  (`TOTAL GENERAL | GOVERNMENT - 100 SERIES`, 1987 p51).
- `recon_net_on_transfer_line`: the net printed on the `LESS INVESTMENTS` line is the net, so the
  unlabelled line under it is the running subtotal (1988 p32). 1991 prints its net there too.
- `stacked_pairs`: PRINCIPAL and INTEREST printed in one cell (`20,000 3,780`), split where the PAGE
  names both -- a column headed `... PRINCIPAL INTEREST` becomes two columns (1986 p48), a row labelled
  `... : PRINCIPAL INTEREST` two rows (1986 p47; rows renumbered 2N / 2N+1, each split cell says so).
- `receipts_span`: one statement of receipts over several tables and pages, pooled against ONE grand
  total (the map's `stated_total`, else the last `GRAND TOTAL` / `TOTAL RECEIPTS` row); the SUMMARY is
  the rows under a SUMMARY heading, or the run directly above the grand total that sums to it while the
  accounts do too; an unlabelled row is a section subtotal; an account's amount is its first figure.
- `withheld_rows`: rows held out of a dataset by page/table/row, with the reason (1986's six
  individuals). Not a redaction: nothing is altered, the rows are simply not published yet.

And, always on, proved not to move any 1991-2010 output: `CALENDAR_REPAIRS` for a whole-dollar
negative with a footnote mark (`($280,016)*`), cents with no leading zero (`.12`), full stops for
the thousands separator in whole dollars (`12.600.`, `7.939.779.`), `17,75$`; the treasurer's cash
total labelled `TREASURER'S CASH JUNE 30, 19..`; a second `BALANCE ... PER CASH BOOK` line is not the
opening balance; the revenue sharing fund's own ledger and `LESS REVENUE SHARING CASH` lines; the
`ADJUSTMENT` = new - prior identity for `omnibus-amendment` (1990 p52, by column position, the
headings being dates); the 1988 accountant identity BALANCE REVENUE = AVAILABLE - AMOUNT EXPENDED -
BALANCE FY (no TOTAL EXPENDED column); and a cell printing a list item and the list's total together
(`$22833.74 $281551.33`), read as the item where the second figure IS the map's `stated_total`.

The cell witness ran over the batch (`locate_cell_misreads.py`, which now also names an unheaded
debt schedule's columns by position -- the last is the row's TOTAL -- for its own row identity):
three candidates, all 1987 p40, all accepted by the blind scripted reader ($0.009); see
`1987/witnessed-cells.csv`.

## One name per quantity -- the 1981-1985 batch, decided 30 October 2026 by the integration pass

| one name | was | what it is | grain | editions |
|---|---|---|---|---|
| `report-school-budget-summary` (NEW) | `report-school-budget-summary` (1981, 1985), `report-school-appropriations` (1982), family `school-general-appropriation` in `report-school-special-accounts` (1983) | the School Committee's own SUMMARY OF ACCOUNTS for the general appropriation, by account series (`1000 ADMINISTRATION`, `2000 INSTRUCTION` ...), salaries and expenses: the year's appropriation (and amendment), what was spent, and the coming year's request or appropriation SIDE BY SIDE. The columns MIX STAGES: one dataset with the stage in `column_meaning`, never differenced across columns (rule 1). Families: `school-budget-summary`, `budget-by-cost-kind` (the salaries / expenses / capital split, 1981 p88/2, 1982 p103/3), `net-budget-request` (1982 p103/2, a lone figure). 1984 p138 prints the same table and is NOT landed (see 1984 NEEDS 3) | one series or cost kind | 1981, 1982, 1983, 1985 |
| family `school-receipts-returned-to-town` in `report-school-state-aid` (EXISTING dataset) | `school-receipts-returned-to-town` (1981), `school-state-aid-receipts` (1982), `school-state-aid-vs-appropriation` (1983, 1984 -- 1986's family name, a different layout) | `Monies returned to the Town` by the School Department, by source (Chapter 70, transportation, tuition ...): the past year's ACTUAL receipts beside the coming year's ESTIMATED receipts, each labelled per column. Never summed with 1986's state-aid-against-appropriation layout | one source | 1981-1984 |
| family `school-receipts-returned-half-years` in `report-school-state-aid` | `report-school-monies-returned` (1985) | the same receipts by source in two half-years and a fiscal-year TOTAL -- actuals only. Its own family because its columns are periods, not stages | one source | 1985 |
| `report-cash-management` (NEW) | (1981 only) | the State-required monthly cash management chart: month-end cash on hand, in non-interest and interest-bearing accounts. A stock at each month end, never summed across months | one month | 1981 |
| `report-treasurers-outlook` (NEW) | (1981 only) | the Treasurer's own projection for FY83 and his illustration of a hidden payroll cost. **ESTIMATES**, the Treasurer's -- never an actual and never a budget, and labelled so in `table-semantics.csv` | one printed line | 1981 |
| `report-office-budget-cuts` (NEW) | (1983 only) | the Town Clerk / Tax Collector / Treasurer table `FY 83 | FY 84 | DECREASE`: two budgets and the difference as printed | one office | 1983 |
| `report-expenditure-shares` (NEW) | (1983 only) | the FY1983 expenditure pie as PERCENTS, no dollars; nine of fourteen slices reached a cell, the other five are in the page text only and no row is written from them | one category | 1983 |

Families added inside existing datasets by the workers (each its own layout): `report-valuation`
`raised-by-taxation-five-year` (1981); `report-appropriations` `omnibus-funding-sources`,
`special-articles-voted`, `special-article-funding-sources` (1981); `report-warrant-article-amounts`
`special-articles-voted` (1982); `report-fee-schedule` `proposed-license-permit-fees` (1981, a
PROPOSED stage); `report-debt` `debt-history-selected-years` (1983); `report-fund-balance-sheets`
`general-fund-long-term-debt` (1983). And `report-vital-records` family `births` (1986 p62, below).

## What the reader does for the 1981-1985 batch (30 October 2026)

Proved the same way as before: all 25 folders 1986-2010 re-run and compared byte for byte with a
snapshot taken before the first change -- 1987-2010 identical, 1986 changed only by TJ's release
and the births below. Always on, because no 1986-2010 output moves:

- `RECEIPTS_GRAND` takes `TOTAL RECEIPTS:` with a colon (1981-1983) and the misprint `TOTAL RECIPTS`
  (1984).
- `CASH_INVESTED` also finds `Revenue Cash and Revenue Cash Invested:`, the line that opens the
  account list under the roll-forward in ONE table (1982 p113, 1983 p40, 1984 p41 -- now mapped to
  `treasurers-cash`, the roll-forward going to the reconciliation).
- the accountant-schedule identities of 1988 and 1991 are WIDENED, not added to: `BALANCE (?:TO
  )?REVENUE` = AVAILABLE - EXPENDED - `BALANCE (?:TO )?(?:FY|FISCAL)` (`Balance to Fiscal 1982`,
  `BALANCE TO FY 85`).
- a stacked principal/interest pair may follow the column's `$ ` (`$ 65,000 15,015`).
- the cash reconciliation reads each cell through `recon_figures`: where the raw text yields no
  figure, every token through CALENDAR_REPAIRS (`20,096,425,52 (11,420,305,18)`, 1981 p95, which
  raised an IndexError); a `LESS ...` label wrapped over two rows takes its net from the second
  (1981 p109, 1982 p129); a labelled line whose figure is printed on the row below takes that
  figure (1982 p129 `Disbursements ...`).
- CALENDAR_REPAIRS: a footnote letter in brackets (`$ 978.48(A)`), the `$` printed twice
  (`$ $ 111,474.00`).

Per-edition opt-ins (`edition.json`): `recon_net_beside_ledger` (1983: `General Ledger Balance |
9,217,865.88 1,154,794.21`, the net disbursed printed beside the ledger balance) and
`colon_for_point` (1983 `50:00`, 1984 `5,033:74*`; a cell `10:30` elsewhere may be a time).

Not applied, with the reason in each folder's NEEDS.md: every rule that would reclassify a row
as a subtotal or an account BECAUSE the statement then closes (1982 2a/2d, 1983 2b/2c); the
validator's block walk (shared with the FY reviews); figures Textract put in no cell (a re-read,
not a reader rule). The cell witness: `locate_cell_misreads.py 1981 1982 1983 1984 1985` finds
0 candidates (no misread there is pinned by two printed identities), so nothing was read and
nothing spent; the misreads the workers named stay in the discrepancy register.

## Publishing names: TJ's decision, 30 October 2026

**30 October 2026, TJ: *"Yes publish. Everything in the annual reports is public."*** Every
`withheld_rows` entry in 1981-1986 is removed and those rows are published: 1986's six private
payees and the page heading naming one, the 1981-1985 pupils' prizes and scholarships, and the
named pension allowances. Named births and burials are publishable too. The reader's
`withheld_rows` / `heading_pages` mechanism stays in `read_report_tables.py`, unused, for a
takedown.

Births landed so far: 1986 p62 tables 2-4 (22 rows, `report-vital-records`, family `births`; name,
birthplace and parents in the label, the day as v1, as the burials land). **Births 2001-2007 landed 30 October 2026** (`report-vital-records`, family `births`: 80, 77, 80, 84,
82, 82, 68 rows, each equal to the name cells on the printed pages; the month is the `group`, or the
header cell on a page that opens mid-month, e.g. 2006 p72 `MAY`), and the 2005 and 2006 Town Clerk
deaths (78 rows each, family `deaths`). **Marriages 2001-2007 are NOT landed, and the reason is a
reader limit, not a decision:** a marriage is two rows (groom, bride) with the date on the first only,
and `read_report_tables.py` takes a dateless row for a heading, so it lands about half the people
(2001: 43 of 83 name cells). Landing the half would publish a partial list as the list; it needs a
reader opt-in that carries the date down. 1981-1985 sent no births page for tables.

Named perpetual-care bequest donors are landed as in 1986: 1982 p143/2 (`Bequests Received`, 18
donors).

## One name per quantity -- the 1971-1980 batch, decided 31 October 2026 by the integration pass

The 1959-1970 folders exist beside these while their own workers finish; `HELD` (one edition per
line) keeps them out of every shared file until their integration pass removes the lines.
`merge_report_tables.editions()` reads it, so the merge, `--check` and every hooked generator agree.

| one name | was | what it is | grain | editions |
|---|---|---|---|---|
| `report-school-lunch` (NEW) | `report-school-lunch` (1971-1977, 1979), `report-school-lunch-program` (1978) | the School Lunch Program report: meals served by month (COUNTS) and the program's income, USDA reimbursements and expenditures by month (DOLLARS), with year summaries. One family per edition's layout (`lunches-served-monthly`, `lunch-finances-monthly`, `lunch-income-monthly` ...); counts and dollars are never summed together. `Valuation of Commodities` is donated food, not cash. Period: the SCHOOL year as printed | one month or one measure | 1971-1979 |
| `report-revenue-cash-invested` (NEW) | `report-revenue-cash-invested` (1978-1980), `report-treasurers-interest` (1974) | the Treasurer's revenue cash invested and the interest it earned: by half-year with rates and the money BORROWED and its interest (1974, family `invested-borrowed-interest`), or as totals for the fiscal year, the calendar year and the next fiscal year's first six months with the interest reconciliation (1978-1980). Actuals; the periods overlap, so never summed across rows. The half-year detail by bank (1978 p70/1, 1979 p77/1, 1980 p71/1) is NOT LANDED: stacked-line cells | one period or line | 1974, 1978-1980 |
| `report-voted-pay-rates` (NEW) | `report-voted-pay-rates` (1974), `report-pay-schedule` (1976) | police pay RATES by step, and hourly special-detail rates, VOTED at a special town meeting (1974 p83, 1976 p55). A rate, not a payroll | one position | 1974, 1976 |
| `report-proposed-salary-schedule` (NEW) | (1972, 1973) | the Personnel Committee's PROPOSED classification and salary schedule. A different STAGE from the voted rates (rule 1), so a different dataset, never merged with `report-voted-pay-rates`. 1972's VOTED schedule (p71) printed no `$` or comma and was not sent for tables: a finder miss, gap 2 in 1972/gaps.csv | one position | 1972, 1973 |
| `report-transitional-receipts` (NEW) | (1974 only) | the Treasurer's detailed statement of receipts for the 18-MONTH TRANSITIONAL YEAR, January 1, 1973 - June 30, 1974, in `Jan-Dec 1973 | Jan-Jun 1974 | 18 Month | Totals`. NOT `annual-report-receipts`: that file holds one fiscal-year `amount` per source, and an 18-month figure in that column beside 12-month ones would be read as a year. The payments in the same layout are `report-statement-of-payments` family `detailed-payments-three-periods`, and the revenue sharing fund's are `report-revenue-sharing` families `receipts-three-periods` / `payments-three-periods` (renamed from `receipts` / `payments` so they are never summed with a one-column layout) | one revenue account | 1974 |

One-edition datasets, each its own quantity: `report-expenditure-history` (1971 p8: population,
enrollment and town expenditures at five-year intervals 1950-1971), `report-veterans-services`
(1971 p33), `report-school-spending-shares` (1971 p98: the SCHOOL dollar by category, dollars and
percents -- NOT `report-expenditure-shares`, 1983's TOWN pie in percents only: a different
quantity), `report-energy-use` (1976 p106: fuel oil and degree days, no money),
`report-school-staff-changes` (1977 p95: PROPOSED staff cuts and additions in the FY-78 request),
`report-town-facts` (1978 p3: one fact per row, mixed units), `report-per-capita-comparison` (1978
p36: Census Bureau per capita figures for FY1976, Lunenburg against state and national averages)
and `report-financial-performance` (1979 p40: the Treasurer's nineteen measures FY1975-FY1979, the
town's own figures) -- NOT merged: different publisher, quantity and grain --
`report-committee-income-expenses` (1978 p89, the 250th anniversary committee) and
`report-surplus-free-cash` (1980 p37: surplus revenue and free cash FY1976-FY1980 actual and FY1981
ESTIMATED, the estimate labelled in `column_meaning`).

**Calendar-year statements (1971-1973).** Until the 18-month transition the town's financial year
WAS the calendar year: 1971, 1972 and 1973 print one set of statements, for the year ended
December 31, and no fiscal-year set beside it. So they stay in the ordinary datasets
(`treasurers-cash`, `report-treasurers-cash-reconciliation`, `annual-report-receipts` ...) with
`fy` = the edition's year and the period quoted in `edition.json` `periods` and in each map row.
The `-calendar-year` dataset exists for a SECOND statement printed beside a fiscal one (1986), and
that is where the 1978-1980 half-year and calendar-year reconciliations went (families
`cash-reconciliation-calendar-year` and `cash-reconciliation-and-accounts-half-year`, the period in
the family name), because 1978-1980 also print the fiscal-year one. **The 18-month year (1973-74)**
is never put in a column beside 12-month figures: its statements are the three-period layout
above; 1973's accountant schedule and voted budget are 18-month budgets in their own columns, and
`Expended through 12/31/73` is 12 of them (1973 NEEDS).

## What the reader does for the 1971-1980 batch (31 October 2026)

Every new reading is an `edition.json` opt-in, set on 1971-1980 only; all 30 folders 1981-2010 were
re-run and compared byte for byte with a snapshot taken before the first change (identical), and
FY2011-FY2025 rows of every shared file are identical to HEAD. New opt-ins:

- `colon_heading_subtotals` (receipts span): a section subtotal Textract printed on the NEXT
  section's heading row (`Special Assessments: | | 658.00`). The row is dropped as an account ONLY
  when its one figure equals, to the cent, the sum of two or more accounts directly above it that
  start at a heading (a change of `group`, or an account printed in the subtotal column) and cross no
  subtotal. The grand total plays no part in the decision. It found exactly the rows the workers
  tied by hand (1973 8, 1975 4, 1976 6, 1977 6, 1971 5, 1979's `453.00`, 1980 2), and each is
  listed in `notes.csv`.
- `receipts_stop_at_grand`: rows printed after the grand total (1980's `Less Payroll Deductions
  Receivable`, `Total Receipts in FY 1980`) are not accounts.
- `statement_span` (`["report-statement-of-payments"]`): one statement of payments over several pages
  in two figure columns. Two printed identities, each upgrading only a `no check` row: the OUTER
  column above `Total Payments` sums to it (the map's `stated_total`, else that row); a run of
  detail lines sums exactly to the outer figure after it (or the one beside its heading). Nothing is
  reclassified.
- `recon_no_transfers`: the roll-forward prints no `LESS INVESTMENTS` line, so the unlabelled line
  under the receipts is opening + receipts, and the one under the closing cash is a footing. Always
  on beside it (1981-2010 unmoved): the ledger line `Cash Balance ...` / `Cash Book Balance ...`, and
  `Disbursements ... Cash Book Balance | 13,499,119.17 36,332.40` read as two lines.
- `cash_book_list`: the bank list under a roll-forward opens at `Cash in Banks:` or `Balance ... per
  cash book`, whichever is first, and the cash book balance is the list's total where nothing else
  prints one.
- `dash_zero`: `-0-` is zero (not 1974: there the zero cells moved the column walk of the revenue
  sharing payments and the three-period identities already read a blank as zero).
- `accountant_marks_wide`: `R`, `A`, `F`, `SR` after a figure and `19,982.83Cr` as a negative (not
  1973, whose `Funds Available` prints several marked components in one column and fails the column
  checks once they are read); `accountant_marks_before`: `TR 610.00` (not 1974 or 1977, where it sits
  on a department's total line and is not its balance).
- `marks_wide`: two or three footnote stars (`120,000.00**`), `$ 3,560,880.*`, and a `$` printed
  after the figure (`$ 942.58 $`). Turning it on for 1981-1985 and 2003 would read cells those
  editions publish unread today (1981 p132 `$ 9,158.05**`, 1983 p125 -- which would become proven --
  2003 p74 `$ 243.68 $`): left for their next pass, not changed silently in this one.
- `year_labels`: a column whose every figure is a bare year (`1973`, `(1974)`) and which holds as
  many text cells is a label column (1974 p46/p70/p126); with it, `tax-collection` takes `Balance`
  as well as `BALANCES`.

Always on (no 1981-2010 output moved): the accountant identity's carried column may be headed by
the bare year (`Balance to 1972`), and the 1974 three-period row identities (`18 Month` and
`Totals` = the two halves, applied where a half prints a figure).

Not applied, each recorded at the end of its NEEDS.md: two figures in one cell (1972 p49
`17,416.75 5,022.00`, 1979 `4,250.00 750.00TR`, 1978 p66), `amount/CODE` cells (1978-1979 school
lunch), stacked-line cells (1977 p37, 1978 p70/1, 1979 p77/1, 1980 p37 and p71/1), side-by-side
trust panels, `Premium 507.30` sharing a label cell (1976), the 1972 two-column balance sheet, and
every figure Textract put in no cell (a re-read). The cell witness: `locate_cell_misreads.py
1971 ... 1980` finds 0 candidates, so nothing was read and nothing spent.

## One name per quantity -- the 1959-1970 batch, decided 31 October 2026 by the integration pass

`HELD` is gone: its last twelve lines were this batch, and every edition folder 1959-2010 is now
merged. Rule 1 decided each merge -- same quantity, stage and grain -- and every rename is in the
editions' `map.csv`.

| one name | was | what it is | grain | editions |
|---|---|---|---|---|
| `report-welfare-aid` (NEW) | `report-welfare-cost` (1959), `report-welfare-assistance` (1962), `report-welfare-aid` (1963, 1964, 1966), `report-welfare-programs` (1965), `report-welfare-services` (1967) | the Welfare Department's table: expended, reimbursements (State, Federal, cities and towns, recoveries) and net cost to the Town, by program, calendar-year actuals. Family `welfare-aid-by-category` where the count column is PERSONS AIDED (1962-1967); `welfare-case-loads` for 1959, whose count is an AVERAGE CASE LOAD (a different count, never summed with persons aided); `welfare-case-load-months` for 1967 p58/1 (persons aided and expended in four months) | one program (or month) | 1959, 1962-1967 |
| `report-tax-collection-by-levy-year` (NEW) | `report-tax-collection-levy-years` (1961), `report-tax-collection-by-levy-year` (1962) | the Tax Collector's report by levy year. NOT folded into `tax-collection`: these two print `Abatement Rescinded` (1962: $232.22) and betterments `Apportioned`, which `tax-collection` has no column for, so folding them would drop printed figures. The other 1959-1970 editions print the same table and stay in `tax-collection`, where the `collector_columns` opt-in (below) now reads their Collected / Abated / Refunded columns | one tax type in one levy year | 1961, 1962 |
| `report-surplus-free-cash`, family `revenue-accounts-analysis` | `report-surplus-free-cash` family `surplus-revenue-free-cash` (1965), `report-fund-balance-sheets` family `revenue-analysis` (1966), `report-revenue-accounts-analysis` (1967) | the Accountant's six-year ANALYSIS OF REVENUE ACCOUNTS (taxes and recap, estimated receipts, unexpended balances, revenue transfer to E & D, balance forward, adjustments, free cash): actuals by year. 1980's comparison keeps its own family `surplus-revenue-free-cash` (another layout, with an ESTIMATED year). Not a balance sheet, so out of `report-fund-balance-sheets` | one line across six years | 1965-1967 |
| `report-expenditure-shares`, families `treasurers-payments-pie` / `treasurers-receipts-pie` | `report-receipts-payments-chart` (1963) and, inside `report-expenditure-shares`, `treasurers-spending-pie-percent-and-dollars`, `receipts-share-analysis`, `payments-share-analysis`, `receipts-share-pie`, `payments-share-pie`, `tax-dollar-pie-legend`, `receipts-payments-pie-legend`, `treasurer-payments-pie-legend` | the legend of the Treasurer's two pies, `We Received` and `We Spent`: one slice's percent and dollars. Assigned to receipts or payments PER TABLE by the slices it lists (state tax, licenses and permits, departmental offsets = receipts); a percent of receipts is never summed with a percent of payments. 1961 p18 `tax-dollar-distribution` (cents of the TAX dollar) stays its own family, and 1983's percents-only town pie keeps its own | one slice | 1960-1967 |
| `report-proposed-salary-schedule` | `report-classification-plan` family `salary-schedule-proposed` (1966 p60) | 1966 printed the schedule `to be voted on at Annual Meeting March 4, 1967`: PROPOSED pay by step, the 1968-1970 and 1972-1973 quantity. `report-classification-plan` (2010) is a point-value and grade plan with no pay | one position | 1966, 1968-1970 |

Kept apart, each its own quantity: `report-school-building-approved-costs` (1959 p37: the costs the
School Building Assistance Commission APPROVED, the State's reimbursement base -- an approval, never
a payment) and `report-capital-project-costs` (1961 p68: a building committee's cost of the new wing
TO COMPLETION -- an actual). Different stage (rule 1), so not merged. `report-school-census-minors`
(1967 p136: children registered by age band, a COUNT) and `report-treasurers-then-and-now` (1961 p15,
the same quantity as 1991's, family `office-then-and-now-1951-1961`) as named.

## What the reader does for the 1959-1970 batch (31 October 2026)

Every opt-in of 1971-1980 was measured on each edition alone and with the rest (on, then each one
off). All are set on all twelve except `marks_wide` on 1969 (it turns one `no check` row to `check
failed` and proves no page). New opt-ins, each set only where it moved a row, and none read by any
edition before 1959-1970:

- `collector_columns`: the Tax Collector's `Collected` / `Abated` / `Refunded` columns read as
  payments, abatements and refunds (1959, 1960, 1963-1967; 1968-1970 head them PAYMENTS etc. and
  are unmoved). Checked by hand on 1966 p28: committed + refunds = collected + abated + tax title +
  balance on each levy row.
- `credit_marks`: `cr 180.29*` and `(47,947.90)CR` are credits, read as negatives (1959 p49: the
  welfare net-cost column then ties, 5,068.67 - 180.29 + 1,141.30 + 547.20 = 6,576.88; 1966 p38,
  1967 p43).
- `signed_figures`: a printed `+` or a footnote `*` before a figure (`+ 3,113.54`, `+$1,223.`,
  `*20,000.00`). A leading or trailing `-` is NOT read (1962 p110 `$ 510.91 -`): nothing on the
  page says whether the dash is a sign or a rule.
- `unit_rates`: `1.50hr`, `1300yr`, `40wk` read as the rate; the unit stays in the printed text
  `reconciliation` quotes. A `1 yr` header (a space) is a step heading and is not read.
- `list_total_tolerance`: the edition's `rounding_tolerance_usd` also applies to a map
  `stated_total` list, worded with the same phrase (1964 p62-63: 75 voted lines $0.50 from TOTAL
  BUDGET VOTED -> 76 rows `checked`).

Built and measured, NOT set: a `roman_counts` reading (`II` -> 11 in a column of counts) proved no
page and turned one 1959 row to `check failed`; the code is in the reader behind its opt-in, set on
no edition.

Not applied, each listed at the end of the editions' NEEDS.md: the `rows` map column (one Textract
table feeding two datasets: 1959 p58-59, 1962 p18, 1963 p20, 1968 p26); debt schedules wider than
`MAX_V` 8 (adding v9..v13 changes the header of every shared generic file, FY2011+ included); a
one-issue debt group whose subtotal repeats the issue (a validator grouping change shared with the
FY reviews); joining digit groups split one per cell (1963 p9: one page, `report-valuation`); a
figure at the end of a label cell; figures Textract put in no cell (re-reads). The cell witness:
`locate_cell_misreads.py 1959 ... 1970` finds 0 candidates, so nothing was read and nothing spent.
