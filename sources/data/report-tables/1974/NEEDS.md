# 1974 edition: what the shared code needs (for the integration pass)

Edition: calendar 1974 annual town report, `4496-1974-annual-town-report.pdf`, 150 pages. Its financial
statements cover the 18-MONTH TRANSITIONAL YEAR January 1, 1973 - June 30, 1974 (p51 `Transitional Year January 1,
1973 through June 30, 1974`; p70 `18 MONTH TRANSITIONAL YEAR ENDING JUNE 30, 1974`), printed as three period columns
`Jan-Dec 1973 | Jan-Jun 1974 | 18 Month | Totals`. Tables were read on the 61 pages `find_financial_pages.py --list
1974` picked; 82 tables (map.csv), 44 landed pages (pages.csv: 17 proven, 27 unproven). Hand checks below were
computed from `build/textract/out/4496-1974-annual-town-report.cells.tsv`.

`edition.json` opt-ins: `unlabeled_subtotals`, `rounding_tolerance_usd`, `accountant_marks`,
`stop_for_comma_without_dollar`, `id_column_words`, `recon_net_on_transfer_line`, `stacked_pairs`, `receipts_span`
(the last four are inert here), and `unlabeled_subtotals_in` widened to the receipts, payments, revenue sharing,
balance sheet and trust datasets (without it the section subtotals of the receipts and payments closed nothing:
receipts 197 `no check` -> 101 `checked`; payments 167 `no check` (6 `check failed`) -> 103 `checked`).

## FINDER MISSES: 1

- **p94, `1974-75 TUITION RATES`** (a money table, no cells): elementary and middle (K-7) $894. and high school
  (8-12) $1177. for September-December 1974, $1002. and $1323. for January-December 1975, each tied to State Report
  figures for the prior school year. The finder needs 3+ money figures a page; p94 has four, printed without cents
  (`$ 894.`), so they were not counted. Family `school-tuition-rates` in `report-fee-schedule` (1981 p43, 1985 p104).
  Registered as a gap in gaps.csv (it is in lines.tsv only).

The other non-picked pages with any money text are prose (p7, p10, p26, p27, p30, p95, p98), 2-5 figures each.

## ROSTER PAGES

p32 firemen (a list of names, `*` marks), p117-119 School Department resignations and leaves during 1974 (prose with
dates), p127-144 `School Personnel Listing 1974-75` (name, college, degree, assignment; no pay). Written to
`rosters.csv`. None sent for tables.

## PRIVACY

No `withheld_rows`. TJ, 30 Oct 2026: everything in the annual reports is public. Names landed: election candidates
(p75-76), committee members (p90), trust fund donors and bequests (p44-45, p71-73), prize fund recipients (funds, not
persons, are named), Highway/School payees do not appear (no vendor list is printed in 1974).

## SHARED-CODE CHANGES THE EDITION NEEDS (none made here)

1. **`V.figure_cols` counts a bare four-digit YEAR in the label column as a figure, so the whole label column becomes
   a figure column and every label on that table is lost.** `figure_cols` marks a column as figures when 2+ cells
   parse; `1973`, `1971`, `(1973)` parse as numbers. Seen on p46/2 (receipts: rows `1971 Real Estate` ... plus the
   bare `1973`/`1970` rows under `Certified Forest Land:` and `Motor Vehicle and Trailer Excise:`), p70/1 (tax
   collector: the `1970`/`1971`/... sub-headings), p126/1 and p126/2 (school lunch: `(1973)`, `(1974)`, and
   `September`... lost) and p57/2 (the fiscal year column). Result: `label` empty and `label_missing = yes` for 16
   receipts rows on p46, 32 lunch rows on p126, every `tax-collection` row (`item` and `section` empty), and the
   year read as `v1` on p57/2. The figures are right; what they are for is not. Change: in `figure_cols` (or in
   `records()`), do not count as a figure a cell with no `$`, comma or decimal point whose value is 1900-2099 when
   the column also holds at least as many text cells as figures. Re-run 1974 after it: p46/2, p70/1, p126 and p57/2
   gain their labels, and p46/2 should close the way p47-p50 do.

2. **`-0-` is not read as a figure** (`validator DASH` has `-`, `$-`, em and en dashes only). The receipts and payments
   print `-0-` for an empty period, so a row with `-0-` in Jan-Dec 1973 lands with its Jan-Jun 1974 figure as `v1`;
   `columns_as_printed` says which column each value is, but the ordinal shifts from row to row. Change: read `-0-` as
   zero in `is_figure`/`parse` for the calendar editions (opt-in, as `colon_for_point`). Not needed to close any total
   (zero adds nothing).

3. **A trailing footnote mark of two or three asterisks is not stripped.** `CALENDAR_REPAIRS` `trailing footnote mark`
   is `[*#]`, one character, and the pattern is matched whole, so `23,000.00**` (p77 `General Highway Maintenance &
   Construction`, `** From Special Highway Grant`) and `40,000.00***` (p77 `Reserve Fund`, `*** From Overlay Surplus`)
   lose their value. Those two rows are the whole difference between the omnibus rows (`3,712,799.00`) and the printed
   `TOTAL BUDGET VOTED: $3,775,799.00` (off 63,000.00 = 23,000.00 + 40,000.00): 83 omnibus rows read `check failed`
   for that one reason. Change: `[*#]+` in both repairs. By hand 3,712,799.00 + 23,000.00 + 40,000.00 = 3,775,799.00.

4. **A row identity for the three-period layout (new family `detailed-receipts-three-periods` and
   `detailed-payments-three-periods`):** `Jan-Dec 1973 + Jan-Jun 1974 = 18 Month` on every row that prints all three,
   and `Jan-Dec 1973 + Jan-Jun 1974 = Totals` on every section subtotal. The page states it by its column heads. By
   hand it closes on 164 of 164 receipts rows and 153 of 154 payments rows; the one that does not is p51 row 29
   (`Purchase Radio & Communications Equipment Fire/Police Departments`, `- 1,658.14 | -0- | 1,658.14`), where a stray
   hyphen before the first figure was read as a minus. Today 96 receipts rows and 69 payments rows are
   `no check` only because their section's subtotal is on another page or the rows are alone in the section.

5. **Statements spanning pages are checked per page.** The receipts run p46-p50 and the payments run p51-p54 are each
   ONE statement with one grand total (p50 row 56 `$11,809,231.97`; p54 row 46 `Total Payments: $11,790,311.02`), and
   a section (e.g. `Health`, which starts at p51 row 45 and ends at the p52 row 12 subtotal) may start on one page and its subtotal land on the next. The
   validator reads each table alone, so `Total Payments` reads `check failed` (rows sum 0.00) and the Health rows on
   p51 read `no check`. Change: pool the receipts and payments tables of an edition like `receipts_span` does, against
   the map's `stated_total` (set on p50/1 and p54/1; the reader ignores it for these families). By hand: the Totals
   column (every section subtotal plus every lone Totals-only row) sums to 11,809,231.97 on p46-50 and 11,790,311.02
   on p51-54, to the cent, and so does each section's Jan-Dec and Jan-Jun column.

6. **New datasets need registering** in `NEW_GENERIC` (read_report_tables.py) and `PROOF` (map_annual_report_pages.py):
   `report-transitional-receipts`, `report-treasurers-interest`, `report-voted-pay-rates`, `report-school-lunch`.
   Names and what they are, for the README table:

   | name | what it is | grain |
   |---|---|---|
   | `report-transitional-receipts` | the Treasurer's DETAILED STATEMENT OF RECEIPTS for the 18-month transitional year, three period columns per account. NOT `annual-report-receipts`: that holds one fiscal-year amount per source, and the 18-month total is a different period | one revenue account |
   | `report-statement-of-payments` family `detailed-payments-three-periods` (existing dataset, new family) | the same statement of PAYMENTS in the same three columns. Never summed with the one-column `detailed-payments` | one printed line |
   | `report-treasurers-interest` (NEW) | the Treasurer's table of revenue cash invested and money borrowed, by half-year: amount, rate, interest earned or paid | one half-year |
   | `report-voted-pay-rates` (NEW) | pay RATES voted at a special town meeting, by position and year of service (police Chief, Sergeant, Patrolman; the hourly special-detail rate). A rate, not a payroll; a VOTED stage | one position |
   | `report-school-lunch` (NEW) | the school lunch program report: meals by type and month (counts), food, labor, other costs, USDA reimbursements and sales by month (dollars), year-on-year changes, balance on hand. Four families: `lunch-meals-monthly`, `lunch-finances-monthly`, `lunch-year-change-money`, `lunch-year-change-meals`, `lunch-year-summary` | one month or one measure |

   `report-statement-of-payments` and `report-transitional-receipts` could instead be one new `report-statement-of-receipts`
   family set; kept apart here because the 1986 receipts were folded into `annual-report-receipts` and the shapes differ.

7. **`emit_treasurers_cash` cannot split p46/1.** The roll-forward (`Balance December 31, 1972` ... `Balance June 30,
   1974 per cash book`) and the cash-in-banks list (7 accounts + `Cash on Hand`, total 121,707.11) are ONE table, with no
   `Revenue Cash Invested:` line for `CASH_INVESTED` to start the account list at. Mapped to
   `report-treasurers-cash-reconciliation` (so all 16 lines landed, `no check`); a map to `treasurers-cash` was refused
   (`accounts sum 23,945,743.37, printed 121,707.11`) because the roll-forward lines were summed as accounts. Change: treat
   `Balance .. per cash book` as the start of the account list when the table prints no `Revenue Cash Invested` line
   (opt-in). By hand: 102,786.16 + 11,809,231.97 = 11,912,018.13; - 11,790,311.02 = 121,707.11; the 8 lines of the list
   sum to 121,707.11. The revenue sharing fund's own reconciliation (p55/3) has the same shape with the opening balance
   `-0-` (item 2) and reads `the chain could not be followed`; by hand 0 + 294,675.87 - 294,283.93 = 391.94.

8. **Cross-column nested subtotals are not checked** (balance sheets p42-45, p55, trust funds p71-73): a detail column's
   lines sum to a subtotal printed in the NEXT column, which the column-by-column validator cannot see (`no check`,
   `no total printed`). By hand: the assets side of the general fund balance sheet (13 top-level lines, p42 t1 + p43 t2)
   and the liabilities side (20 top-level lines, p42 t2 + p43 t1 + p44 t1) each sum to the printed 5,263,344.57; the trust
   funds summary (p71) sums to the printed 109,725.08 only with the worthy poor funds (8,834.85) in it:
   100,890.23 + 8,834.85.

9. **Accountant schedule p67: `TR 990.00` (the transfer mark BEFORE the figure).** `Purchase of Lawn Mower | 990.00 R |
   990.00 | ... | 215.00 | TR 990.00` is the one `check failed` on the accountant schedule (all of p58-p66 and p68 are
   proven). `accountant_marks` reads the mark AFTER the figure only. Change: allow `(?:TR|TF|R|RF|AR)\s` before the figure
   in the same repair. p69 is `unproven` for another reason: it ends with no GRAND TOTAL printed.

10. **p11 stacks two half-year figures in one cell** (`$ 250,000 600,000`, `$ 1,113.37 5,258.69`, `5% to 5½ 8½ to 9%`), so
    the Dates / Invested / Interest Earned rows land as text with no values (3 rows, `no check`). `stacked_pairs`
    splits PRINCIPAL and INTEREST only. Change: split a cell of N whitespace-separated figures into N rows when the
    `Dates` cell beside it holds N periods (opt-in). By hand: invested 250,000 + 600,000 = 850,000 (Total 1973); interest
    earned 1,113.37 + 5,258.69 = 6,372.06; 2,075,000 + 3,700,000 = 5,775,000 (Total 1974); 19,727.78 + 35,940.74 =
    55,668.52. Those interest totals are the same figures as receipts `Proceeds of Revenue Cash Invested` (p49: 6,372.06
    and 19,727.78) and the 18,804.41 interest paid is the payments line `Interest on Temporary Loans` (p53).

11. **`report-debt` `debt-repayment-schedule` p57/2** has 13 figure columns (Highway, Middle School, Conservation Land,
    Grand Total, each Principal | Interest | Total, with a spacer): it is read with `layout=spans:1-4,5-7,8-10,12-14` so
    each fiscal year is four panel rows (the `panel` column says which; the fiscal year sits on panel 1 only, and as
    `v1`, item 1). Today `no check`. By hand: the principal column sums to 918,500 and the interest column to 239,815 =
    the printed totals.

12. **Town facts table (p3/1), NOT LANDED**, prints the assessed valuation (`$52,009,970.00 (Real Estate)`,
    `$ 2,908,970.00 (Personal Property)`), tax rate (`$44.00`), land area, road miles and the 1971 State Census population
    (7,825). Every edition prints one (1981, 1985 not landed either). A `report-town-facts` dataset (one fact per row,
    value as printed) would hold all of them; suggested, not done.

## What the page prints that no earlier edition mapped

- The 18-month transitional year itself: the town changed its financial year from calendar to July-June. Statements
  carry 1973, six months of 1974 and the 18-month total; the accountant's schedule carries forward to `Fiscal 1975`; the
  School Department prints an `18-month Budget` (p146) and `Actual Receipts 18-Month period` (p147).
- The Treasurer's own invested and borrowed cash table with rates (p11), and a cross-tie: `Proceeds of Revenue Cash
  Invested` and `Interest on Temporary Loans` in the statements equal the interest in that table.
- School lunch program report (p125-126): meals by type and month, costs, USDA reimbursements and commodity valuation.
- Pay rates for police voted at the November 25, 1974 Special Town Meeting, including the scale substituted for July 1,
  1975 and hourly special-detail rates (p83).
- `Net Funded or Fixed Debt` split INSIDE and OUTSIDE the debt limit (p44: $40,000.00 inside, $920,000.00 outside), which
  is what the modern `debt limit` gap asks for; so there is no such gap for 1974.

## A discrepancy in the printed record (a fact, then a hypothesis)

p147 `Monies Returned to the Town`, actual 18-month column: the eight printed lines (890,837.30; 113,758.16; 7,801.75;
36,469.00; 10,769.98; 60.00; 8,712.00; 172.34) sum to 1,068,580.53 and the printed total is 1,059,955.65: a difference of
8,624.88. The estimated FY-75 column ties to its total (799,840 exactly). The printed total is exactly the sum of the lines
with the `Driver Education Fees` line at 87.12 instead of 8,712.00 (1,059,868.53 + 87.12). The 8,712.00 itself is
confirmed by the Treasurer's statement (p50: 6,192.00 + 2,520.00 = 8,712.00 for `Driver Education Receipts`) and its
18-month Chapter 70 line by p47-48. HYPOTHESIS, not tested: the total was keyed with a decimal-place slip on that line.
Nothing here tests it; the School Department's worksheet would. Those 14 rows are `no check`.

## Other honest limits

- p145 (school statistics): Textract garbled the staff counts (cells `2/5`, `I`, `5 5 1`, counts in the GRAND TOTAL
  column); rows are as read and `checks=none`.
- p126/1 meals-by-month (counts, not dollars) and p125 (signed year-on-year changes) are landed as printed.
- Elections (p75-76): 40 rows, the tables carry no date of their own; dated by their position beside the April 6, 1974
  Annual Town Meeting excerpt only.

## Integration pass, 31 October 2026: what was done with each item

Opt-ins and names are in `sources/data/report-tables/README.md` (1971-1980). By item number above:
1 APPLIED (`year_labels`). 2 NOT SET for 1974: `dash_zero` moved the revenue sharing payments' column walk, and the three-period identity reads a blank as zero anyway. 3 APPLIED (`marks_wide`): the omnibus budget closes. 4 APPLIED (always on, families `detailed-receipts-three-periods`, `detailed-payments-three-periods`, and the revenue sharing families renamed `receipts-three-periods` / `payments-three-periods`): p51 row 29 now FAILS its identity -- `- 1,658.14`, the stray hyphen, is a misread and is shown as one (p51 proven -> unproven). 5 APPLIED for payments (`statement_span`); receipts are closed by the identity. 6 APPLIED: names unified (`report-treasurers-interest` -> `report-revenue-cash-invested`). 7 APPLIED by `recon_no_transfers` on the reconciliation mapping (`checked`); the list is not remapped. 9 NOT SET (`accountant_marks_before` breaks p66's department total). 10, 11, 12 NOT APPLIED. p147's $8,624.88: a discrepancy, not adjusted. Finder miss p94: re-read list.
