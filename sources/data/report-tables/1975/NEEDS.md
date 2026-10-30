# 1975 edition: what the shared code needs (for the integration pass)

Edition: calendar 1975 annual town report, `4497-1975-annual-town-report.pdf`, 152 pages. Tables were read on the 56
pages `find_financial_pages.py --list 1975` picked; 66 tables (map.csv), 41 landed pages (pages.csv). Hand checks below
were computed from `build/textract/out/4497-1975-annual-town-report.cells.tsv`. Opt-ins in edition.json are the
1981 set (`accountant_marks`, `stop_for_comma_without_dollar`, `id_column_words`, `recon_net_on_transfer_line`,
`stacked_pairs`, `receipts_span`) plus `unlabeled_subtotals` and `rounding_tolerance_usd`: 1.

## FINDER MISSES: 0

Of the 56 picked pages, 12 returned no table (p11, p28, p29, p33, p44-p50, p84): all prose (the Town Clerk's letter,
Highway, Veterans, Tree Warden, warrant articles whose amounts are in running text, Monty Tech). No right-hand column of
bare figures on any of them. Bound, not proof.

## ROSTER PAGES

p126-142 School personnel listing 1975-76 (administration, clerical, guidance, teaching staff by school with degree and
years of experience, playground aides, custodial staff with start dates, cafeteria substitutes): no pay printed.
Written to `rosters.csv`. Not sent for tables. Births, deaths and the jury list (p34-40) were not sent either (no money).

## PRIVACY

No `withheld_rows`. Trust fund holdings name the funds' donors (Mabel L. Allen, Joseph A. Harwood) and p82/3 lists
perpetual-care bequest donors; both landed (TJ, 30 Oct 2026: everything in the annual reports is public). p83 prize
grant recipients are NOT LANDED for the layout reason in item 4, not for privacy.

## SHARED-CODE CHANGES THE EDITION NEEDS (none made here)

1. **Footnote asterisks with no space, and three budget lines in no cell (p42-43).** The voted budget prints
   `124,524.00**` (Police Department), `24,554.00**` (Municipal Refuse Disposal Area) and `25,782.00***` (General
   Highway Maintenance). CALENDAR_REPAIRS accepts a footnote mark after a SPACE (`($135,987.00) *`) but not glued to the
   figure, so the three rows publish no value (`unparsed_cells`) and sit 174,860.00 short. A fourth gap is a re-read,
   not a rule: the left panel of p43 opens with `Library by Taxation 43,341.00`, `Cemeteries 9,593.00` and `Park
   Department 33,038.00` (page lines 4, 5, 20, 21, 28, 29), which Textract put in no cell. By hand the budget ties
   exactly: the 26 general government items (166,880.00) + 37 protection to schools items (3,636,149.00) + 18
   unclassified and debt items (303,789.00) + 85,972.00 = 4,192,790.00, the printed TOTAL BUDGET VOTED. Change: allow
   `\*+` directly after a figure in CALENDAR_REPAIRS; the three left-panel lines need a re-read (nothing is called
   absent). Until then the omnibus rows read `check failed` (LIST TOTAL off 260,832.00 = 174,860.00 + 85,972.00).
2. **Section subtotals printed beside the NEXT section heading (p56-60 receipts).** Textract returned four section
   subtotals on the row of the following heading: `Motor Vehicle and Trailer Excise: | | 9.04` (the Certified Forest
   Land subtotal), `Commonwealth of Massachusetts: | | 56,090.92` (the Federal grants subtotal), `Interest: | | 743.58`
   (Special Assessments) and `Licenses and Permits: | | 16,100.95` (Trust and Investment Funds). The span emitter counts
   them as accounts, so the 172 receipts read `check failed`: 13,486,688.95 - 72,944.49 (their sum) = 13,413,744.46,
   the printed Total Receipts, to the cent. Change: a row whose label ends in a colon and whose only figure is in the
   last column, with a heading-only row above it that has no figure, is a section subtotal. (Hypothesis, not tested:
   a one-row vertical shift in Textract's table reading.)
3. **Reconciliation of Treasurer's cash: a layout with no chain the emitter follows (p56/1, p65/3).** The roll-forward
   prints the receipts total in a third column, wraps `Disbursements ... Cash Book Balance` into one cell holding two
   figures (`13,499,119.17 36,332.40`), and has no `Revenue Cash and Revenue Cash Invested:` line (the cash is a CASH
   BOOK balance, `Balance June 30, 1975 per cash book`). Mapped as `treasurers-cash` the emitter refused (accounts sum
   27,107,235.54, printed 36,332.40: it read the roll-forward as accounts), so p56/1 is mapped to
   `report-treasurers-cash-reconciliation` and the 21 rows land raw with `no check` (`the chain could not be followed`);
   the bank-account list below the chain lands in the same rows. Change: CASH_INVESTED also finds
   `Balance June 30, 19xx per cash book` as the line that opens the account list, and a cell holding two figures after a
   `Disbursements` label is (disbursed, balance). By hand: 121,707.11 + 13,413,744.46 = 13,535,451.57; less 13,499,119.17
   = 36,332.40 = the eight bank lines of p56 (3,547.53 + 10,000 + 2,000 + 2,000 + 2,000 + 15,000 + 1,251.54 + 533.33).
   Revenue sharing (p65/3): 391.94 + 228,711.88 = 229,103.82; less 227,747.71 = 1,356.11, one bank account.
4. **p83/1 NOT LANDED.** Four fund panels in one eight-column table: library (left), and sidewalks and grounds, school
   prize and stabilization STACKED in the right three columns, so a row's label and amount are from different funds. Same
   defect as 1981 p123/3. The closing balances tie in the page text (library 13,753.39; sidewalks and grounds 6,254.97;
   school prize 1,115.73; stabilization 16,934.80), each equal to p55 and p81. A re-read by panel is needed.
5. **p98/1 NOT LANDED.** A six-row table of a personnel proposal (eliminate, add, savings, net) set beside a tribute to
   Howard Brock; Textract returned fragments (`PERSONNEL ELIMINTE: (a) (f) w THEE`) and no dollar figure reached a cell.
   Re-read from the page image if the savings are wanted.
6. **Accountant's schedule (p68-79): `TR` / `R` marks beside a SECOND figure.** Ten rows read `check failed` and are
   not misreads of a digit: a cell prints two figures and a transfer mark (`18,136.00 64.00`, `TR 18,200.00`; `88,707.90TR`)
   or the label wraps over two rows, so the row identity takes the wrong cell: p69 r11, p70 r23 and r50, p72 r19, p75 r40
   and r41, p76 r30 and r45, p77 r15, p78 r40. p74 (six columns, `Chapter 90 Improvement FY1975-$`) has no identity
   registered and reads `no check` throughout. Change: IDENTITIES for the 1975 header
   `Approp. Forward | Total Funds Available | Accounts | Amounts Expended | Total Expended | Balance to Revenue | Balance to
   Fiscal 1976` already match (148 `checked` across the dataset); the two-figure cell is the open item.
7. **Statements that print an identity the emitters do not take.** Balance sheet (p52-54): by hand the eleven asset
   subtotals sum to 5,743,004.83 and the twenty liability subtotals to 5,743,004.83, the printed total, to the cent;
   the rows read `no check`. Payments (p61-64): the right-hand column (section subtotals and single lines, excluding
   the Total Payments row) sums to the printed 13,499,119.17 to the cent; rows read `no check`. Trust funds in custody
   (p55) 114,079.04 and the revenue sharing balance sheet (p65) 182,072.05 likewise tie by hand. Change: honour the map's
   `stated_total` in the payments and balance sheet emitters, as the receipts span does.
8. **PROOF / generic registrations for NEW names.** `report-school-lunch` (NEW: families `lunch-meals-served`,
   `lunch-finances-monthly`, `lunch-expenditure-summary`, `lunch-receipts-summary`) needs `map_annual_report_pages.PROOF`
   and `NEW_GENERIC`. New families in existing datasets: `report-fee-schedule` `cemetery-fees` (a rate, no date printed);
   `report-appropriations` `omnibus-transfers-from` (printed under `Transfers from:`; the page does not say what they are
   transferred to); `report-school-state-aid` `school-categorical-aid-received`.

## What 1975 prints that 1981 did not

- A year of 18-month transition: `1974 (6 months)` Real Estate and Personal Property taxes (p56, p80) and `Teachers'
  Salary Escrow, Fiscal 1975` / `Prior Year Teachers' Salaries Paid from Escrow` 121,695.92 and 88,707.90 (p54, p62, p76).
  The page calls it `18 Month Transitional Year` (p76). What caused the change is not stated in the tables.
- School lunch program report (p144): meals served by month, and costs against USDA reimbursements and sales by month,
  with commodity valuation.
- Cemetery fee schedule (p13).
- A Treasurer's cash that is a CASH BOOK balance ($36,332.40) with revenue cash invested held on the balance sheet
  (`Invested 1,245,987.53`, p52), not the revenue-cash account list of 1981.
- Bonded indebtedness by issue with principal and interest in SEPARATE columns (p67), not stacked pairs.
- Revenue sharing with a `Grants` line inside payments (p66/2), counted in the 227,747.71 total as printed.

## Integration pass, 31 October 2026: what was done with each item

Opt-ins and names are in `sources/data/report-tables/README.md` (1971-1980). By item number above:
1 APPLIED (`marks_wide`); the three left-panel budget lines in no cell remain a re-read. 2 APPLIED (`colon_heading_subtotals`: 4 rows; receipts close to 13,413,744.46). 3 APPLIED for the general fund (`Disbursements ... Cash Book Balance` two lines; `checked`); p65/3 revenue sharing still cannot be followed (its receipts line prints two figures). 4, 5 NOT APPLIED (panels, fragments). 6 PARTLY (`accountant_marks_wide`, `accountant_marks_before`); two-figure cells remain. 7 APPLIED for payments (`statement_span`); balance sheet not. 8 APPLIED.
