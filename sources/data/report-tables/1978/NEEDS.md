# 1978 edition: what the shared code needs (for the integration pass)

Edition: calendar 1978 annual town report, `4500-1978-annual-town-report.pdf`, 184 pages. Tables were read on the 58
pages `find_financial_pages.py --list 1978` picked; 85 tables (map.csv), 47 landed pages (pages.csv). Hand checks
below were computed from `build/textract/out/4500-1978-annual-town-report.cells.tsv` and `.lines.tsv`.
edition.json opt-ins: `unlabeled_subtotals`, `rounding_tolerance_usd`, `accountant_marks`, `stop_for_comma_without_dollar`,
`id_column_words`, `recon_net_on_transfer_line`, `stacked_pairs`, `receipts_span`.

## FINDER MISSES

1. **p180** (printed 178): the last School Department special account, `18. PUBLIC LAW 94-482, VOCATIONAL EDUCATION ACT
   (Project #78-162-505-033-3)`: 1st payment `$ 4,139.00`, `$ 4,139.00`, balance on hand. Money, continues the table of
   p179 (`report-school-special-accounts`). Not sent, so no cells. Its receipt side is on p40 (`Public Law 94-482 4,139.00`).
Every other page not sent has no money table (a scan for 3+ figures in lines.tsv on unsent pages found only p24, a prose
recommendation, and p180).

## ROSTER PAGES

In `rosters.csv`: p4-5 officials, p21 police roster, p32-33 jury list (name, address, occupation), p128-136 school
resignations, retirements and service recognition, p137-158 the school personnel listing for 1978-79 (name, college, degree,
start date, no pay), p171 food services personnel. Not sent for tables.

## FIGURES TEXTRACT PUT IN NO CELL (a re-read, not a reader rule) -- hand checks tie WITH them

1. **p42 foot, the first three payment lines.** `Detailed Statement of Payments` begins at the foot of p42, under the receipts
   table, and `Moderator's Salary 100.00`, `Auditor's Salary 100.00`, `Selectmen's Administration 24,483.17` are in
   lines.tsv (top 0.8322-0.8612) but in no cell. Hand check, cells p43-46: every section subtotal equals the sum of its
   lines except the first (`196,798.55` printed vs `172,115.38` summed; the difference 24,683.17 is exactly those three
   lines), and the subtotals plus the standalone lines sum to `Total Payments 15,272,040.25`. So the statement closes; the
   rows in `report-statement-of-payments` are short by those three lines. The 13 `check failed` rows there are the validator
   grouping a statement of subtotals against the total (rows sum 10,401,436.76), not a misread.
2. **p41 foot, `Library: Fines 1,252.64`** (lines.tsv top 0.8627; label `Library:` and `Fines` are lines, no cell). Hand check
   of the receipts statement, p38-42: all section subtotals tie to their lines (0.00 off in each of 35 sections); lines +
   standalone amounts = 15,299,860.87; plus 1,252.64 = `Total Receipts 15,301,113.51`. And see 3.
3. **p38/1 rows 12-17, motor vehicle excise, labels one row above their amounts.** Labels `1974`..`1978` sit on rows 12-16 and
   the five amounts on rows 13-17 (`1,678.06`, `8,305.04`, `26,650.73`, `175,538.97`, and `198,244.46` on a row with NO
   label). The tax collector (p66) fixes the pairing: 1,678.06 is the 1974 levy, 198,244.46 the 1978 levy. The reader
   landed `... 1975 = 1678.06` (a year off) and dropped the label-less 198,244.46, so `annual-report-receipts` is short by
   198,244.46 + 1,252.64 = 199,497.10 and all 166 rows say `check failed`. Change: none to the reader (a skewed scan); a
   re-read of that one table, or a `copy` row in the map.
4. **p180 `Public Law 94-482` (account 18)**, see FINDER MISSES.
5. **p78 right-hand strip: Articles 12, 13, 14, 15, 19, 21, 23, 24 ...** (`7,500.00`, `1,500.00`, `445.00`, `5,000.00`,
   `17,500.00`, `15,000.00`, `9,000.00`, `2,000.00`) are in lines.tsv beside the unclassified lines but in no cell, so the
   special articles are landed from p79 only (Articles 25-39); `TOTAL SPECIAL ARTICLES VOTED 194,225.00` and `GRAND TOTAL
   5,575,647.00` are printed. 5,381,422 + 194,225 = 5,575,647 ties. The budget lines sum to the printed `TOTAL BUDGET
   VOTED 5,381,422.00` (checked: 215,646 + 315,916 + 142,442 + 376,374 + 62,256 + 3,677,003 + 57,551 + 10,634 + 38,965 +
   341,340 + 143,295).
6. **Appropriation rows with a missing balance cell**: p59 t1 r35, p60 r37, p61 r32 (`Purchase Chipper` 7,463.00 + 37
   = 7,500.00 available, 6,541.00 expended, balance 959.00 appears in the narrative), p62 r17 and r29, p64 r14 and r22:
   7 `check failed` rows in `report-appropriations`, all a balance figure absent from its row.

## SHARED-CODE CHANGES THE EDITION NEEDS (none made here)

1. **Stacked multi-line cells in a table of figures** (p53/1, p70/1). p53/1 first data row prints two bond issues in one row
   (`1,340,000 40,000`, `9-15-67 6-20-69`, `4.2% 4.9%`); the reader lands no row for `MIDDLE SCHOOL CONSTRUCTION` and the
   subtotal row `TOTAL MIDDLE SCHOOL` then fails (rows sum 0). Change: split a cell of N stacked figures into N rows when the
   whole row does so (the same N across the row). p70/1 is worse: the reader MERGES the stacked digits of the count column
   (`3 1 7 3` -> 3173, `611111715`), so 70/1 is mapped NOT LANDED. Its period subtotals (7/1/77-12/31/77 invested
   2,035,000.00, interest 43,206.31; 1/1/78-6/30/78 6,434,088.03 / 33,937.90) are therefore in no dataset.
2. **Cells printing `amount/CODE`** (p173/1, `Receipts from Comm. of Mass.`: `55.50/MW`, `8,735.04/USDA`, and up to three to a
   cell, `1,676.96/NFA 6,410.78/USDA 53.70/MW`). The reader skips them without a note (`unparsed_cells` is empty) and
   the row's total then lands in the position of the Commonwealth column. Hand check, the column sums to its printed
   `61,451.24` (including `5,063,23` as 5,063.23, a comma for the point); the two `check failed` rows (November and
   TOTAL INCOME) are this. Change: read `amount/CODE` as the amount with the code in the label or a note; sum several.
3. **A trailing `$` after the figure**: p67/1 row 1 is `Cemetery | $ $75,245.06 $`, the CALENDAR_REPAIRS rule for `$`
   printed twice does not cover a trailing `$`, so the cemetery row (75,245.06) is missing and the summary
   (`stated_total` 152,458.74) fails: 7 `check failed` rows in `report-trust-funds`. By hand 75,245.06 + 8,865.22 + 15,475.01 +
   7,165.62 + 24,450.55 + 20,160.76 + 1,096.52 = 152,458.74.
4. **`30,843.64 Fwd 4,825.27` in one cell (p66/1 r4), `1,384.67 $24,450.55` (p69/3 r2), `28,800.00 1,200.00` (p57)**: two
   figures in one cell; the first is dropped or the cell is not read, so the 1976 and 1977 committed figures of the tax
   collector's report are missing from `tax-collection`.
5. **p3/1 `$67,926,470.00 (Real Estate)` / `$ 3,313,000.00 (Personal Property)`** are figures with a trailing word, not read; the
   dataset `report-town-facts` holds the rate, the population and one row that is a district label (`1st Middlesex`).
6. **`report-debt` repayment schedule**: 6 `check failed` rows of the same kind 1981 p111 and 1985 p65 carry (the stacked
   PRINCIPAL/INTEREST pair split against the `Total:` and `GRAND TOTAL` rows). Not a misread.

## NEW DATASETS (names for the integration pass to settle)

`report-town-facts` (1981 left the same table NOT LANDED), `report-per-capita-comparison` (p36), `report-committee-income-expenses`
(p89, the 250th Anniversary / Old Home Week committee), `report-school-lunch-program` (p173-174), `report-revenue-cash-invested`
(p70/2-3 only). Reused: `report-statement-of-payments`, `report-revenue-sharing`, `report-fund-balance-sheets`, `report-school-staff-fte`,
`report-school-state-aid`, `report-school-budget-summary`, `report-school-special-accounts`, `report-fee-schedule` (school tuition rates),
`report-property-tax-exemptions`, `report-treasurers-cash-calendar-year` (here a SIX-MONTH reconciliation, July 1 - December 31,
1978, p69/5; the period is quoted in map.csv and its family keeps it apart).

## PRIVACY

`withheld_rows` NOT used (TJ, 30 Oct 2026). Named pupils paid grants from the school prize funds (p69/1) and named
perpetual-care bequest donors (p68/4) are landed as printed. p67 shows trust funds by named bequest.
