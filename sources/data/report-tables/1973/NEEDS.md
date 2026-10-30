# 1973 edition: what the shared code needs (for the integration pass)

Edition: calendar 1973 annual town report, `4495-1973-annual-town-report.pdf`, 128 pages. Tables were read on the
47 pages `find_financial_pages.py --list 1973` picked; 61 tables (map.csv). The year is the CALENDAR year 1973,
the transition to an 18-month fiscal year ending June 30, 1974: the accountant's schedule and the voted budget
are 18 months (a budget), `Expended through 12/31/73` is 12 of them (an actual), kept in their own columns.
Hand checks below come from `build/textract/out/4495-1973-annual-town-report.cells.tsv`.

## FINDER MISSES: 0

Pages not picked were scanned for figures in `lines.tsv` (any page with a dollar or comma-thousands figure): 6, 18,
19, 23, 24, 27, 69, 78, 81, 86, 125 each hold one or two figures in prose, none a money table. Picked pages that
returned no table (7, 13, 15, 26, 28, 29, 68, 70-73, 83, 84, 124) are prose, including the warrant articles' text with
amounts (68, 70-73); no rows were written from lines.

## ROSTER PAGES

p99-114 School Personnel Listing 1973-74 (name, position, education, start date), the custodial and lunchroom lists
(p111-112), resignations (p113) and leaves (p114): no pay, no table read. Written to `rosters.csv`.

## PRIVACY

No `withheld_rows` (TJ, 30 Oct: everything in the annual reports is public). Named trust fund donors, bequests and
two named students receiving $30 grants (p63, page text) are public record; the p61/2 and p62/2 tables are NOT LANDED
for a different reason (item 6).

## SHARED-CODE CHANGES THE EDITION NEEDS (none made here)

1. **Receipts and payments: a subtotal merged into the next section's heading row is counted as an account.**
   Textract prints a section subtotal on the row of the NEXT heading, so a label ending in a colon carries a figure:
   `Interest:` 707.89 (subtotal of Special Assessments), `Commonwealth of Massachusetts:` 94,107.92, `Licenses and
   Permits:` 11,171.62, `Treasurer:` 3,061.78, `Health and Sanitation:` 7,373.40, `Park:` 2,100.00, `Claims:` 2,429.25,
   `Previous Year Refunds:` 684.04 (p48-52, receipts); `Recreation:` 9,846.60, `Unclassified:` 29,833.12, `Debt and
   Interest:` 80,803.96, `Agency and Trust:` 1,213,731.22 (p54, payments). Change: in `receipts_span` (and for payments)
   a row whose label ends in `:` and whose figure sits in the subtotal column is a section subtotal, not an account.
   By hand: the receipts accounts without those 8 rows sum to 6,843,586.96 = the printed total (p52) to the cent
   (161 rows); the payments accounts without the 4 colon rows sum to 6,602,333.52 = the printed `Total Payments:` (p55)
   to the cent (145 rows). Today receipts read `check failed` (accounts sum 6,965,222.86, 121,635.90 over, exactly the 8
   subtotals) and payments' p55 total fails because `receipts_span` pooling is not applied to
   `report-statement-of-payments`, so the sum covers only the last page's block (118,640.47 short = the first
   section's subtotal). Change: pool payments the same way (the map gives `stated_total` 6602333.52).
2. **Treasurer's cash reconciliation: `Cash Balance December 31, 1973` is not recognised as the ledger line.**
   `RECON` has no pattern for `^Cash Balance`, so p46/2 and p47/1 read `the chain could not be followed: disbursed,
   net_disbursed, opening, receipts`. The edition prints no investment transfer lines. By hand: 102,786.16 +
   6,843,586.96 = 6,946,373.12 (printed as the unlabelled subtotal); less 6,602,333.52 = 344,039.60 (printed). Revenue
   sharing (p47/1): 0 + 219,123.55 - 219,123.55 = 0. Also `Balance December 31, 1972 $ -0- $` (p47) and `Cash Balance
   ... -0-` come out as labels with no figure because `-0-` is not a figure. And p46/2 holds the roll-forward AND the
   bank list in one table: the list opens at `Balance December 31, 1973 per cash book` / `Cash in Banks:`, which
   `CASH_INVESTED` does not know, so the table is mapped to the reconciliation and the bank rows land in family
   `cash-reconciliation`. Change: add `^Cash Balance` to `RECON` as the ledger, `-0-` as zero, and
   `Balance .* per cash book|Cash in Banks:` to `CASH_INVESTED`, then map 46/2 to `treasurers-cash` (the 8 banks sum to
   344,039.60 by hand: 85,911.35 + 10,000 + 2,000 + 2,000 + 226,660.29 + 15,000 + 1,155.50 + 1,312.46). The row `Capitol
   Bank ... (Includes 12/31 State Distribution of $223,663.97)` has a dollar figure inside the LABEL, read as a value.
3. **Accountant's schedule (p57-60): marks and a separator.** (a) `5,000.00 SR` (p59 Road Machinery Maintenance, the page's
   KEY prints `RS`) is not an accountant mark; (b) `19.013.26` (p58 Road Oil and Tar, expended) has a full stop for the
   thousands comma in a column of cents. With both read, by hand the columns tie to the cent: budgets (p57-58) 5,301,875.42
   funds available, 3,231,968.24 expended (3,212,954.98 + 19,013.26), 2,069,907.18 balance; special articles (p58-60)
   578,704.75 (573,704.75 + 5,000.00), 325,890.74, 252,814.01. Today 13 + 11 + 1 special-article rows read `check failed`
   (`the block summed is the wrong one`): "Funds Available" is printed as SEVERAL figures with marks when a line was funded
   from more than one place (`1,163.60 TR | 36.40 | 1,200.00 | -0-`), so the column check sees extra cells. Change: a row
   identity for this layout (all figures but the last two, summed = expended + balance), or reading the marked figures as
   components of Funds Available. One suspect: p58 Conservation Fund, `9,000.01 F | 2,000.00 TR | 16,000.00 TR | 8,250.00
   | 135.00 | 3,115.01`: components sum to 35,250.01, less 135.00 would leave 35,115.01, but 3,115.01 is printed/read; the column of
   balances still ties to its total with 3,115.01, so I cannot tell whether the page prints 3,115.01 or Textract dropped a digit
   (witness: `locate_cell_misreads.py` on p58). The row is left as read.
4. **Omnibus budget total is $70.00 short of its items.** `Reserve Fund 120,000.00**` (p67) has a DOUBLE footnote mark that
   no repair reads (CALENDAR_REPAIRS has the single `*`), so the amount is unparsed. Reading it, the 82 item rows of p66-67
   sum to 5,322,885.00, and the printed `TOTAL BUDGET VOTED: $5,322,815.00` is $70.00 LESS. Today the list reads `check failed`
   (off 119,930.00 = 120,000.00 - 70.00). I did not establish whether the page, the printing or a misread digit
   in one of 82 items causes the $70; not resolved here. Change: read `**`.
5. **Tax collection (p46/1): labels lost and no identity.** The emitted rows have empty `section` and `item` (as 1981's did), so a row
   cannot be tied to its levy year and tax; 25 rows, status blank. The page states an identity: commitments + refunds -
   payments - abatements - tax titles = balance, e.g. 1973 real estate 2,653,678.56 + 9,316.16 - 2,471,142.41 - 66,436.41 -
   15,047.24 = 110,368.66 and the column totals 3,325,402.22 / 21,845.35 / 3,008,700.23 / 138,140.55 / 15,047.24 /
   185,359.55 (the balances 19,521.14 + 12,580.97 + 1,272.44 + 110,368.66 + 41,534.86 + 75.00 + 6.48 sum to 185,359.55 by hand);
   `Grand Total Received` 3,016,652.20 = 3,008,700.23 + 6,278.97 + 1,673.00. Textract merged 1972 motor vehicle excise
   into two rows (`34,515.22 Fwd` then `119,663.06 ...`): commitments are forward + additional.
6. **Trust fund pages p61/2 and p62/2 are NOT LANDED.** Several funds printed side by side (worthy poor, library, sidewalks,
   cemetery; and their ledgers on p62) were read as 7 columns with the cell contents of different funds merged (a row pairs
   `Worcester No. Sav. Inst. Bk. 125,567 Francis Caldw...` with 1,407.43). The rows would attach figures to the wrong
   names. Needs a layout-aware re-read (the four panels separately). The page text carries the printed ledgers, and the
   balances are landed from p61/1 (8,561.31 + 5,671.94 + 13,120.00 + 64,336.23 = 91,689.48), p63/1 and p63/2.
7. **Balance sheet (p42, p44) side by side.** Read with `spans:1-3,4-6`; `panel` 1 is ASSETS, `panel` 2 is LIABILITIES AND
   RESERVES. The `Agency: County Dog Licenses` row (p42r23) is a cell holding two figures, `6,677.29 26.85` (the payroll deductions
   subtotal and the item), and lands with no value. No identity is printed per side except the totals (2,941,446.54 each, p44;
   the right side prints `2,941.446.54`), so these rows are `no check`. Not hand-tied here.
8. **School statistics (p120/1)** are not a column of totals, so `checks=none`. The calendar-year statement (p120/3) is five
   statistics in different units, not summed.
9. **The p10 charts (births 1963-1973, population mix by age) and p3 facts** are NOT LANDED (counts, interleaved with chart labels).

## NEW datasets this edition names

`report-proposed-salary-schedule` (p17: a proposal in annual dollars; 2010's `salary-schedule` is adopted and hourly), and
`report-school-lunch` (p115: monthly meals and finances of the school lunch program). Families inside existing datasets:
`report-appropriations` `accountant-schedule-revenue-sharing`; `report-fund-balance-sheets` `general-fund-balance-sheet`,
`general-fund-liabilities-continued`; `report-trust-funds` `trust-funds-school-prizes`.
