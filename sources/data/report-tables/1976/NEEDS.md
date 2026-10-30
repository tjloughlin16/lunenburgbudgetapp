# 1976 edition: what the shared code needs (for the integration pass)

Edition: calendar 1976 annual town report, `4498-1976-annual-town-report.pdf`, 160 pages. Tables were read on the 60 pages
`find_financial_pages.py --list 1976` picked; 80 tables (map.csv), 42 landed pages (pages.csv: 13 proven, 29 unproven).
edition.json opt-ins: `unlabeled_subtotals`, `rounding_tolerance_usd`, `accountant_marks`, `stop_for_comma_without_dollar`,
`id_column_words`, `recon_net_on_transfer_line`, `stacked_pairs`, `receipts_span`. Hand checks were computed from
`build/textract/out/4498-1976-annual-town-report.cells.tsv`.

## FINDER MISSES: 0

Every unsent page that prints a `$` figure was read in `lines.tsv` (p16, 17, 19, 24, 27, 33, 35, 40, 44): all prose or
one-line figures. Bound, not proof.

## ROSTER PAGES

p29 roster of firemen; p127-128 School Department personnel changes (names, dates, positions, no pay). In `rosters.csv`.
p129-130 are enrollment counts by classroom with the teacher's surname: counts, out of scope.

## PRIVACY

None withheld (TJ, 30 Oct 2026: everything in the annual reports is public). Deaths (p61) and the cemetery bequests by donor
(p92/6) are landed with names.

## NEW DATASETS (names chosen here; unify with the other workers)

- `report-pay-schedule`, family `police-pay-scale` (55/1): a voted RATE schedule (annual dollars and $/hour on one page).
- `report-energy-use`, family `school-fuel-oil` (106/1): gallons, barrels, degree days; no money.
- `report-school-lunch`, families `lunches-served`, `lunch-income-expenditures`, `lunch-income-summary`, `lunch-expenditure-summary`
  (153/1-4): the School Lunch Program Report 1975-76, counts and money.
- family `cemetery-burial-fees` in `report-fee-schedule` (12/1-2): fee RATES, as 2003-2004.
- family `deaths` in `report-vital-records` (61/1-2): death records with age; 1981 landed burials as `vital-records`.

## SHARED-CODE CHANGES THE EDITION NEEDS (none made here)

1. **Receipts span (p64-68/1): label-with-subtotal rows are read as accounts.** Textract puts a block's SUBTOTAL on the row of the
   NEXT block's heading: a row whose label ends in a colon and whose only figure is in the last column (`Farm Animal, Machinery,
   Equipment Excise: | | 324,711.54`, `Special Assessments: 1,110.50`, `Commonwealth of Massachusetts: 72,793.86`,
   `Current Year Refunds: 633.38`, `Previous Year Refunds: 12,658.35`, `Treasurer: 4,213.71`) is the previous block's subtotal.
   Hand check: accounts as read sum 11,568,958.02; those six rows sum 416,121.34; the cell `Reimbursement by CETA - Workmen's
   Compensation | Premium 507.30` (p67) is dropped because the word `Premium` shares the cell with the figure. 11,568,958.02 -
   416,121.34 + 507.30 = 11,153,343.98, the printed `Total Receipts:` (p68/1) to the cent. Today all 180 rows are `check failed`.
   Wanted: treat such a row as a subtotal in the receipts span, and read `Premium 507.30` as label + figure.
2. **Same colon-subtotal rows in the Detailed Statement of Payments (p68/2-71/1).** `Debt and Interest: 147,016.48` (the
   Unclassified subtotal), `Agency and Trust: 137,615.00` (the Debt subtotal) and the unlabelled subtotals (3,227,841.85,
   50,139.54, 35,178.19, 954,618.66, 9,074.44, 25,962.08, 231,625.17, 5,392,227.76) are summed with the accounts, so `Total
   Payments: 11,150,213.73` (p71) reports `check failed` (rows sum 10,242,417.59) on 14 rows. The statement does tie by hand
   once subtotals are left out. The `unlabeled_subtotals` rule did not recognise the Schools (p70) block, whose first rows are
   `Montachusett Regional Vocational Technical | School District Assessment` over two rows.
3. **Treasurer's cash roll-forward, p63 and p76 (revenue sharing): the ledger line is `Cash Book Balance June 30, 1976` /
   `Cash Balance June 30, 1976`**, which `RECON` does not take as `ledger`, so "the chain could not be followed" on both
   (no investments line exists on these pages). The chain closes by hand: 36,332.40 + 11,153,343.98 = 11,189,676.38;
   - 11,150,213.73 = 39,462.65 (p63); 1,356.11 + 273,875.23 = 275,231.34; - 269,625.62 = 5,605.72 (p76).
4. **p63 is one table holding both the roll-forward AND the cash by bank** (6,587.49 + 10,000 + 3 x 2,000 + 15,000 + 1,323.35 +
   551.81 = 39,462.65 by hand). Mapped to `report-treasurers-cash-reconciliation`, so all 17 rows land there with no bank-list
   identity; as `treasurers-cash` it was refused (the roll-forward rows were summed as accounts). Wanted: split a table at a map
   row, or hand the roll-forward block to the reconciliation emitter as for 2007-2008, leaving the bank list to `treasurers-cash`.
5. **Revenue sharing payments span two tables (p76/3, p77/1)** closing on one `Total Payments: 269,625.62` (p77/1). Sum by hand:
   135,046.00 + 1,005.00 + 1,200.00 + 42,243.24 + 3,369.98 + 23,238.54 + 62,786.66 + 71.09 + 665.11 = 269,625.62. Today the
   6 rows of 77/1 are `check failed` (summed alone, 90,131.38). Wanted: pool the payments across the two tables.
6. **p78/2 debt repayment schedule (stacked principal/interest pairs)**: 9 rows `check failed` and p78/1 `TOTAL MIDDLE SCHOOL` (a stacked
   `1,340,000 40,000` pair of issues in one cell). The page's own arithmetic holds: Middle School principal 65,000 x 11 = 715,000 and
   interest 165,165.00; Grand Total FY1978 = 124,000.00 + 36,447.20 = 160,447.20. The failures come from the `Total:` rows being
   compared with the principal/interest halves of the stacked row. Left as `check failed`.
7. **School budget summary (p155/1): 16 `check failed`.** The page prints the FY-76 spent column down to `TOTAL SPENT FROM TOWN
   2,871,632.88`, which is the NET spent 2,760,092.76 + the escrow 111,540.12, not a column total; the series DO sum: FY-76
   appropriation 2,928,767, spent 2,810,092.76, request 3,114,303 (hand sums). The check is comparing the wrong rows to the wrong total.
8. **Accountant's schedule, 8 `check failed`** (p81 police cruisers 10,000.00 / 2,630.00; p88 library carpeting; p89 cemetery truck, oil roads,
   tractor lines with `TR`/`RF` marks, and a `768.77` carried into a label). Not investigated beyond the row list; the page is an older layout
   (account lines with indented object-of-expense sub-lines, no total per sub-line).
9. **Voted budget (p45-47)**: the page prints the FY1977 budget in two panels per page, returned as separate tables; 45/1, 45/2 and the first
   part of 46 are `proven`. p47/1 returns only the tail of the special articles list (articles 20, 37, 42 and the borrowing article 16) and the
   two totals: the earlier special articles are on p48-50 as text, which Textract did not return as a table (p48-50 have no cells).
10. **Not landed**: 3/1-3 (town facts, office hours, meeting schedule), 14/1 (library music categories, empty cells), 98/2 (school start times).

## What this report prints that 2010 did not

An older single-fund statement set (detailed statement of receipts and payments, general-fund balance sheet, revenue sharing fund, trust fund
rollforwards), the school lunch program report, the Tax Collector's report by levy year, a police pay scale, school fuel-oil consumption, and the
School Department budget request beside the spent figure (all as in 1981/1985 except the lunch, fuel and pay-scale tables).

## Integration pass, 31 October 2026: what was done with each item

Opt-ins and names are in `sources/data/report-tables/README.md` (1971-1980). By item number above:
1 APPLIED (`colon_heading_subtotals`: 6 rows); the receipts stay 507.30 short because `Premium 507.30` shares the label cell (a re-read, not applied). 2 APPLIED via `statement_span` where detail runs close; the 14 column-check failures stay. 3 APPLIED (`Cash Book Balance` ledger, `checked`). 4 NOT APPLIED (no table split). 5 NOT APPLIED. 6, 7, 8 NOT APPLIED (stacked pairs, the escrow line, two-figure cells); `accountant_marks_before` makes p87's total line fail its identity honestly (a term does not parse). Names: `report-pay-schedule` -> `report-voted-pay-rates`.
