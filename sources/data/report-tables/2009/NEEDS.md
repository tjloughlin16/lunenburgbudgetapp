# 2009 edition: what the integration pass has to change

This worker writes only inside `report-tables/2009/`. These are the shared-code changes the
2009 edition needs. Each one blocks rows that are refused in `map.csv` today (dataset empty,
reason in `note`) or rows that are landed but thinner than they should be.

## 1. `header_from` must override a header that is only the running title (special revenue, pp56-59)

- **Where:** `scripts/read_report_tables.py`, `records()`: `if not names and m.get('header_from')`.
- **Change:** apply `header_from` whenever the map names one, not only when no header was read
  (or: when every header cell on the page is one of the page's top lines, i.e. the running title).
- **Why:** pp56-59 repeat `TOWN OF LUNENBURG / SPECIAL REVENUE FUNDS / FISCAL YEAR ENDING 6/30/09`
  as Textract header rows and print no column headings. The reader named the columns from those
  title words (`TOWN OF SPECIAL REVENUE FISCAL YEAR ENDING`), read the fund-number column
  (`1518`, `2660`) as a value, and could not apply the `special-revenue` identity. 125 rows refused.
  `map.csv` already carries `header_from=55/1` for all four pages.
- **Watch:** p55's columns are FORWARD 7/1/2008 | TOTAL RECEIPTS | TOTAL DISBURSEMENTS |
  BALANCE FWD TO FY'10 in cols 3-6, the same positions pp56-59 use (col 1 fund number, col 2 name).
  The fund-number column should be a label, not a figure: it has no `$`, `.` or `,`.

## 2. Wages: the dollar sign read as a leading `8` or `3` (pp84-89)

- **Measured:** of the 574 wage cells in columns 4 and 8 on pp84-89, 484 print `$` and 90 do not.
  Of those 90, 74 begin with `8` and 16 with `3` (`855,054.97`, `891,898.47`, `8100.00`,
  `369,512.93`). The 2010 edition's wage pages have 549 of 549 with `$`. On pp46-73 every money cell prints `$` except on p61 (Treasurer's cash), which prints none and ties to its own total.
- **Why it is refused rather than landed:** `coverage()` grades a wage page by comparing the
  cells to the page's LINE output, and the lines share the misreading. It passed every row as
  `checked` (574 checked on the first run). The fix cannot be a rule that drops the leading digit:
  `87,342.00` may be `$7,342.00` or `$87,342.00` with the sign lost.
- **Change wanted (one of):** a parser mark in `validate_totals` that records a figure with no `$`
  in a column where the page otherwise prints `$` as ambiguous (`unparsed_cells`, status
  `check failed`), so the 484 clean rows land and the 90 do not; or an independent second reader
  for these pages (Vision OCR text, `sources/town-annual-reports/text/` is Textract too) as the
  coverage witness.
- **Also on p89 t2:** its first row `VAILLANCOURT | JAMES | SCHOOL | S38,212.37` is taken as the
  header because `S38,212.37` does not parse, so header_from is not applied and the row is lost.
  Item 1 fixes the header; `S` for `$` is the same family of misread.
- **And the period is not printed** (gaps.csv row 1). Land under `report-gross-wages` with
  `period` = not printed; never sum with calendar 2010 or the fiscal FY2011+ rows.

## 3. A header row below an empty first row (enrollment, p28)

- `records()` / `V.split_header`: p28 t1 row 1 is empty and row 2 is the printed header
  `School/Grade | 10/01/07 | 10/01/08 | 10/01/09`. With no money figure in the table the reader
  takes `rows[:1]` (the empty row) as the header, so v1-v3 say `not established` and the header
  lands as a data row labelled `School/Grade`. Change: skip leading empty rows before taking the
  first row as header. Landed as is; 32 rows.

## 4. Count tables with no money cell lose rows above the first decimal (special services, p31)

- p31 t1: rows `# of Students Referred by Part C ... | 9` and `# of Students who have IEP
  Proposed or Implemented by 3rd Birthday | 9` sit above `District Rate | 100.0`, the first cell
  `is_figure` accepts, so they become header. Refused. Change: for family `special-services`
  (or any table whose header candidate rows each carry a label AND a number), the header is the
  first row only.
- p30 t1 percentages (`5.90%`, `.97%`) are not figures to `is_figure`, so they ride in the label.
  A percent-aware figure rule (`\d*\.?\d+\s*%`) would put them in v1/v2 with
  `column_meaning` `State Data 08/09 | LUNENBURG 08/09`. Same for p35 (THMS MCAS) and p41 (Monty
  Tech competency), which already do this in 2010.

## 5. Trust-funds identity does not match this year's header

- `IDENTITIES['trust-funds']` wants `BEGIN+ING BALANCE PRINC` / `BEGIN+ING BALANCE EARN`; 2009
  prints `BEGIN BAL PRINCIPAL` / `BEGIN BAL EARNINGS`, `CONTRIB TO PRINC FY 09`, `NET EARNS FY 09`,
  `DISBURS FR PRINC FY 09`, `TRANS EARNS FY 09`, `ENDING CASH VALUE FY 09`, `UNREALIZED GAIN/LOSS`,
  `6/30/2009 MARKET VALUE` (p62 t1). Suggested: `BEGIN\w*\s+BAL\w*\s+PRINC`, `BEGIN\w*\s+BAL\w*\s+EARN`,
  `NET EARN`, `DISBURS`, `TRANS\w* EARN|TRANSFERS`, and `MARKET VALUE` for the second identity's
  target. Today the 73 rows are graded by their SUBTOTAL columns only (71 checked, 2 failed: the
  `Bartholomew Trust Funds Subtotal`, p63 t2, which totals rows across both pages).

## 6. Accountant schedule: a blank BALANCE is not checked

- 2009 prints BALANCE TO REVENUE only where something is left; for a fully spent line the cell
  is blank and `row_identity` skips a blank target, so those rows fall to the grand-total check
  (which Textract's subtotal rows make fail: `grouping`). 74 of the 76 `check failed` on pp49-53 are of this
  kind (no row identity applied). Change, if wanted: treat a blank target as zero when every term is printed. Same in 2010.

## 7. Omnibus p73 t1 has no header

- Textract split p73 into a right half (t1, 2 columns, no header) and a left half (t2,
  `Line No. | Account | VOTED FY 2010`). t1's v1 says `not established`. A `header_from` with a
  column offset (`73/2+1`) would let t1 name its figure column `VOTED FY 2010`.

## 8. Prose figures no table holds (no emitter; for an integration pass to decide)

- **placement-counts:** pp29-30 `nine students received services outside the district during the
  2009/2010 school year. Of the nine students, eight are in day placements and one is in
  residential placement. Of the day placements, three are serviced in a Collaborative and five are
  in private day placements.` Parts tie (8+1=9; 3+5=8). Unlike FY2013+, no SIMS date (`1 March`) is
  printed. Also `two hundred and fifty-three students with disabilities ... 14.83%` (p29).
- **Fire incidents (dept-activity):** p18 `Emergency Medical Calls - 639, Fire Rescue Calls - 239,
  Inspections/Service Calls - 751 for a Total of 1629` (calendar year; parts tie). 2010 printed
  this as a table.
- **Vital records counts:** p69 `DURING 2009 THE TOWN CLERK RECORDED ... BIRTHS 81 DEATHS 64
  MARRIAGES- 44`.
- **Capital plan:** p15 prose: `$234,030 was approved for capital requests`, of which `$122,030`
  contingent on a grant and three items approved outright (cruisers `$69,000`, pagers/portables
  `$33,000`, vault `$10,000`, `a total of $112,000`); p74 article `$233,950.00 for the FY10 Yearly
  Capital Plan`. The two totals differ by $80 and the page does not reconcile them. 2010 printed a
  table (`capital-plans`).

## 9. Dataset registration

- `report-special-services` is NEW (`rows/report-special-services.csv`, 18 rows, GENERIC
  columns): needs a `PROOF` entry in `map_annual_report_pages.py` (style: nothing, it prints no
  total) and a table in `build_db.py`, as `report-weights-measures` got for 2010.

## 10. pages.csv says `unread` for refused pages

- `page_states()` marks a page `refused` only if some map row for it has a dataset. pp56-59 and
  pp84-89 were read and refused by eye (reasons in `map.csv`), and come out `unread`. A map
  `note` beginning `NOT LANDED (refused` could count as mapped.

## Findings on the page (measurements, not explanations)

- p14 t2 (Abstract of Assessments): the class rows sum to 5,055 accounts and $1,297,176,664 --
  identical to the FY2009 row of the Valuation and Tax History table on the same page (t1). The
  printed `TOTALS` row says 5,003 and 1,322,671,840 -- identical to that table's FY2008 row. Every
  cell read at 95%+ confidence (triage `printed_error`). Not tested: why.
- p60 (capital projects), `REPLACE WALK-IN FREEZERS AND COOLER`: 49,960.00 - 36,147.69 = 13,812.31,
  printed balance 11,812.31; the EXPENDED column's GRAND TOTAL is off by exactly 2,000.00. Triage:
  one-digit misread. Recorded, not applied.
- p68 Moderator: precincts 12+19+16+23 = 70, printed TOTAL 72; the candidate and Blanks rows above
  sum to 14 in precinct A. Recorded, not applied.
- p73 prints `FY 2009 Omnibus Budget` as its title and `VOTED FY 2010` as its figure column.

## Integration pass, 28 October 2026

What the one integration agent did with each item above. Counts are this folder's rows after
`read_report_tables.py`; the reasons for anything not applied are here so nobody re-asks.

- **1 header_from over a running title (pp56-59).** APPLIED. `header_from` now always wins when the map names it, and identifier columns (a fund number or range: `1518`, `2830-2838`, no `$`, `.` or `,`, left of the first text column) are part of the label, not a figure. pp56-59 LANDED: special-revenue-funds 2009 is 153 rows, all `checked` (was 28).
- **2 wages: `$` read as a leading 8 or 3 (pp84-89).** APPLIED, with an INDEPENDENT witness: scripts/witness_dollar_glyphs.py compares each suspect cell's first glyph with this page's own `$` (484 templates) and digits, at the face's own advance width, and must pass a negative control (97 known digits: 0 read as `$`). Of the 90: 85 read as `$` (`87,342.00` -> $7,342.00), 5 undecided -> no value, `check failed`, `AMBIGUOUS` in `reconciliation`. pp84-89 LANDED: 575 rows, 570 `checked`, 5 `check failed`. glyph-witness.csv holds every decision with its scores.
- **2 (p89 t2 `S38,212.37`).** APPLIED: validate_totals.REPAIRS reads `S` before a money figure as `$`.
- **3 header under an empty row (p28).** APPLIED: a row of dates is the header wherever Textract put it in the first five rows.
- **4 count rows above the first decimal (p31) and percents.** APPLIED: p31 t1 LANDED with `header=row:1`; percents are figures marked `[percent]`.
- **5 trust-funds identity for this year's header.** APPLIED: a `BEGIN BAL ... NET EARN ... DISBURS ... TRANS EARN` identity (disbursements printed negative, so added) and `MARKET VALUE = ENDING CASH + UNREALIZED`. 73 of 73 rows `checked` (was 71).
- **6 blank BALANCE read as zero.** NOT APPLIED, measured: on 2010 the blank-balance lines fail in offsetting pairs inside one department (Payroll +439.48 / Other Expenses -439.48) -- the balance is struck per department, so the identity fails on correct figures.
- **7 header_from with a column offset (p73 t1).** NOT APPLIED: p73 t1 still reads `not established`. One table; the offset syntax was not worth a new map grammar in this pass.
- **8 prose figures.** NOT APPLIED -- prose figures (placement counts, vital-record counts, fire incidents, capital plan prose, pie-chart percentages) need a prose reader; no table reader can land them. `placement-counts` is SIMS-sourced and dated 1 March; these sentences name a school year and no source, so adding them is a decision about mixing two measurements, not a mapping. Recorded here with their pages; nothing was inferred.
- **9 dataset registration.** APPLIED, RENAMED: `report-special-services` is now `report-special-education` (the same quantity 2008 landed), families `disability-types`, `dropout-rate`, `early-childhood-transition`. Registered in PROOF, build_db and table-semantics.
- **10 refused pages showing `unread`.** APPLIED: a financial page whose map rows say `NOT LANDED` is `refused`, not `unread`.
