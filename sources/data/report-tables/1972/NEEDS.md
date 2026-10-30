# 1972 edition: what the shared code needs (for the integration pass)

Edition: calendar 1972 annual town report, `4494-1972-annual-town-report.pdf`, 132 pages. Tables were read on
the 51 pages `find_financial_pages.py --list 1972` picked; 69 tables (map.csv), 38 landed pages (pages.csv).
Every financial statement in this report is for the CALENDAR year ended December 31, 1972 (p46, p47, p51) and
is landed in the standard datasets with the period quoted in each map row; the town moves to a July-June year
after this report (p8: `the new eighteen month fiscal year cycle`; p125: `18-Month Budget Request (1/1/73-6/30/74)`).
Decide at the merge whether calendar-year statements stay in `treasurers-cash`, `report-treasurers-cash-reconciliation`
and the like with `fy` = 1972, or move to `-calendar-year` datasets as 1986 and 1981 did for their SECOND calendar-year
statements. 1972 has no fiscal-year statement beside them.

Hand checks below were computed from `build/textract/out/4494-1972-annual-town-report.cells.tsv`.
Opt-ins in edition.json: `unlabeled_subtotals`, `unlabeled_subtotals_in` (appropriations, payments, balance sheets,
trust funds, school budget summary, school special accounts), `rounding_tolerance_usd`, `accountant_marks`,
`stop_for_comma_without_dollar`, `id_column_words`, `recon_net_on_transfer_line`, `stacked_pairs`, `receipts_span`.

## FINDER MISSES: 1

p71 (the voted Classification and Salary Schedule of March 4, 1972, under Article 3, with the town meeting's
exceptions): a table of whole-dollar and hourly pay by step (`Police Sergeant 7475 7675 7925 ...`, `Patrolman
6775 7025 ...`). It prints no dollar sign and no thousands comma, so the page read as holding under three money
figures and was not sent; it has no cells. It is the schedule the Town actually voted (p15-16 are PROPOSALS for
1973 and 1974). Listed as gap 2 in gaps.csv.
Checked and NOT misses: p82 (election returns), p103-115 (school personnel years), p119-121 (enrollment, census):
counts, no money.

## ROSTER PAGES

p31 roster of firemen; p95-98 school retirements and resignations; p103-117 School Personnel Listing 1972-73
(name, school, degree, year of hire; no pay); written to `rosters.csv`. Not sent for tables. p99-102 (graduates
and scholarship recipients) are name lists with no amounts in the lines read.

## PRIVACY

Nothing withheld (TJ, 30 October 2026: everything in the annual reports is public). Named in landed rows: the
Library and Cemetery Perpetual Care donors (p45/7, p69), the school prize fund donors (p45/7). The two named
grant recipients on the Mabel L. Allen and Joseph A. Harwood prize funds (p70, `Grant - Michael Mulligan`,
`Grant - Judith Buswell`) are in lines only (see TABLES THE CELLS MISSED).

## TABLES THE CELLS MISSED ON SENT PAGES (not finder misses: the page was sent)

Textract returned no cell for these regions, so no row can be written; the text is in lines.tsv:
- p68: `Investment of Funds` under the summary (savings banks and book numbers for Worthy Poor and Library, by
  donor: `American Legion: Worcester No. Sav. Inst. Bk. 125,567 1,317.38`, `Nathaniel C. Day ...`, `Susan T.
  Howard ...` totalling `$8,380.68`). Only the 5-row summary (68/1) is a table.
- p70: the whole top half, REPORT OF TRUST FUNDS IN CUSTODY OF SCHOOL COMMITTEE (Mabel L. Allen School Prize
  Fund 589.86 and Joseph A. Harwood School Prize Fund 537.51, total 1,127.37, with their investments, income
  and grants). Only the Stabilization Fund section (70/1) is a table. The two prize fund balances are in
  p45/7.
- p44: the printed sum of the appropriation balances, `83,432.54` (right of `Purchase Equip-Truck and Plow 225.00`),
  reached no cell.

## SHARED-CODE CHANGES THE EDITION NEEDS (none made here)

Items 1 and 2 were tested on a COPY of `scripts/` in the scratchpad (never the shared script): both worked and
moved nothing else in this folder.

1. **`CASH_INVESTED` does not match this edition's account list.** p46/2 prints the roll-forward and the accounts
   in one table, opened by `Cash in Banks:` (no `Current Cash Invested` line). Add `|^CASH IN BANKS` to
   `CASH_INVESTED`. Tested: `treasurers-cash` publishes 10 accounts summing to 102,786.16, `the unlabelled figure
   printed as the last row`; today it is refused (`accounts sum 18,203,587.65, printed 102,786.16`, because the
   roll-forward lines are summed with the accounts).
2. **The accountant-schedule identity does not name this edition's carry-forward column.** The schedule heads it
   `Balance to 1973` beside `Balance to Revenue` (p56-67). Widen `BALANCE (?:TO )?(?:FY|FISCAL)` to
   `(?:FY|FISCAL|19\d\d)` in both `accountant-schedule` identities (the 1988 and the 1991 entries, which are the
   ones this header matches: `Total Funds Available`, `Total Expended`, no `ENCUMBERED`). Tested:
   `report-appropriations` moves from 100 `checked` (the omnibus lists) to 240 `checked`, one `check failed` (p64
   School Zones, `294.00 2,700.00` printed in one cell), and 19 pages `proven` instead of 7. Today the identity cannot be applied and those rows are `no check`.
3. **The Treasurer's roll-forward has no transfer lines, so the chain cannot be followed.** p46/2 prints
   `Balance December 31, 1971 $90,506.42` + `Receipts January 1, through December 31, 1972 5,977,356.13` =
   (unlabelled) `6,067,862.55`; `Disbursements ... 5,965,076.39`; `Cash Balance December 31, 1972 102,786.16`;
   (unlabelled) `6,067,862.55`; `Balance December 31, 1972 per cash book 102,786.16`. Recomputed by hand: 90,506.42
   + 5,977,356.13 = 6,067,862.55 and 6,067,862.55 - 5,965,076.39 = 102,786.16, both to the cent. With item 1 applied
   the 7 rows are written and the status is `no check` (`the chain could not be followed: disbursed, net_disbursed,
   net_receipt`). Wanted: when the page prints no `LESS INVESTMENTS` or `LESS REVENUE CASH` line, take net =
   gross, and take the ledger from `^CASH BALANCE`.
4. **A cell holding a section subtotal AND the next line's item.** p49 row 16: `Trailer Park Assessments |  |
   17,416.75 5,022.00`. 17,416.75 is the Licenses and Permits subtotal (8,487.50 + 6,330.00 + 2,255.00 + 157.00 +
   121.75 + 5.50 + 60.00); 5,022.00 is the Trailer Park Assessments item itself. The receipts reader takes the first
   figure of a cell, so the statement sums to 5,972,334.13 against the printed 5,977,356.13, short by exactly 5,022.00.
   Every one of the 152 receipts rows therefore reads `check failed`. Recomputed by hand, with the 5,022.00 added,
   the 30 right-hand-column figures (section subtotals and lone items, p47-50) sum to 5,977,356.13 to the cent, and each section's items sum to its
   subtotal (diff 0.00). The grand total prints as `$5,977.356.13` (full stop for a comma; the map's
   `stated_total` carries 5977356.13).
5. **A two-figure-column ledger (items in the left column, section subtotals in the right one, on the next
   unlabelled row).** Pages 44, 45, 47-54 print every statement this way. The validator and `unlabeled_subtotals`
   look for a subtotal in the SAME column as its items, so the balance sheet, the receipts and the payments read
   `no check` (payments p54 would read `check failed` against `Total Payments` summing only the right-hand column,
   so p54/1 is mapped `checks=none`). Recomputed by hand: the 17 payment section subtotals (104,585.74;
   166,758.68; 86,693.00; 298,469.45; 41,472.45; 2,439,668.72; 34,827.88; 11,562.55; 26,945.32; 76,562.98;
   1,479,793.01; 721,030.39; 1,120.00; 14,140.30; 24,944.89; 136,501.03; 300,000.00) sum to the printed
   `Total Payments: $5,965,076.39`, and each section's items sum to its subtotal (diff 0.00); the assets side of
   the balance sheet (302,786.16 + 108,702.45 + 41,110.94 + 37,724.02 + 47,229.03 + 16,435.15 + 44,898.40 +
   4,720.31 + 29.78) sums to `$603,636.24`; liabilities and reserves sum to the same 603,636.24 (agency 16.25 +
   guarantee deposits 16,085.92 + overestimates 2,334.90 + federal grants 18,703.51 + revolving funds 6,214.74 +
   appropriation balances 83,432.54 + overlay 27,112.79 + burial rights 7,440.00 + reserve fund 20,000.00 +
   revenue reserved 187,397.54 + surplus revenue 217,152.48 + receipts reserved 11,621.70 + other receipts
   reserved 6,123.87). Wanted: a mode where the figure in column B on an unlabelled row closes the items in column
   A since the previous such row.
6. **Row-level misreads, NOT repaired.** (a) p126/2 row 4: `TUITION & TRANSPORTATION of STATE WARDS, Chapter |
   76 8,183.45`: the `76` of `Chapter 76` is in the figure cell, so the row reads 768,183.45; the check catches it
   (`rows sum 1,420,186.01 vs printed 660,186.01`, off 760,000.00) and the true figure is 8,183.45 (it is the p48
   `Public Welfare - Tuition & Transportation 8,183.45`). (b) p123/3 row 3: `All Lunchroom Sales, including
   Sept. Balance | - 85,383.64`: the dash is a separator in the label and the figure is positive (85,383.64 ties to
   `$129,111.41` and to p123/2's column total); it reads -85383.64. (c) p15 row 5 `6 6900` reads 66900 (the 7 yr
   rate of the Principal Clerk; the row's 6 yr rate is 6675). (d) p46/1 prints the 1971 and 1972 rows one line off:
   the 1971 Real Estate balance `11,876.23` sits on the Motor Vehicle line (it closes the 1971 Real Estate row:
   86,502.60 + 508.52 = 66,759.17 + 754.17 + 7,621.55 + 11,876.23 = 87,011.12). (e) p68 row 1: the cell `$ $
   8,380.68 $` (stray dollar signs) is unparsed, so Worthy Poor has no value (8,380.68 + 5,387.56 + 11,120.00 +
   62,449.68 = 87,337.92 as printed). (f) p55 table 3 (Highway Garage issue): a one-row table, so no figure column
   is found and the row is a label with no figures (`11-1-70 100,000 1971-75 4.75 20,000 4,750 20,000 3,800
   40,000 8,550 60,000`; 100,000 - 40,000 = 60,000 and p55/4 starts at a balance of 40,000 after the 1973
   payment). (g) p125: `275.` (Improvement of Sites appropriation) is unparsed so the row's v1 is the spent
   column (each row carries its own column_meaning, which says so). (h) p128 `(Est.) 8,000.00` and `.04*` unparsed.
   All are candidates for the cell witness (`locate_cell_misreads.py 1972`), none is pinned by two printed
   identities.
7. **p69 prints four trust fund blocks side by side with interleaved rows** (Worthy Poor and Sidewalks above,
   Cemetery Perpetual Care and Library below). Mapped `layout=spans:1-4,5-8` in page order; every label and figure
   is as printed but the reader's `group` (the last label ending in a colon) leaks across blocks, so some rows carry
   a wrong group (`U.S. Treasury Bonds:` on a `Balance December 31, 1972` row). Use label and page order; do not
   trust `group` for p69.
8. **New datasets and families to register** (generic `report-*` columns): `report-proposed-salary-schedule`
   (family `proposed-classification-salary-schedule`: a PROPOSED schedule, rule 1, hourly/weekly/annual units
   in the cell), `report-school-lunch` (families `lunch-meals-by-month`, `lunch-finances-by-month`,
   `lunch-receipts-summary`, `lunch-bills-summary`), families `debt-schedule-by-year` (`report-debt`),
   `school-categorical-aid` (`report-school-state-aid`). `table-semantics.csv` should call the school lunch
   `Valuation of Commodities` column the value of donated commodities, not cash.
   The omnibus total (`Total Budget Voted: $3,177,396.64`) is summed across p72/1, p72/2 and p73/2 by the map's
   `stated_total` (72/1 + 72/2 + 73/2 = 3,177,396.64 to the cent); the three tables are `checked`.

## What this report prints that earlier ones in the batch do not

The Personnel Committee's PROPOSED pay scales for two future Marches (p15-16); the Treasurer's statements for a
CALENDAR year with a Tax Collector's report that nets 1968-1972 commitments (p46); federal revenue sharing funds
invested ($40,141.00, p45; the first appearance of the fund); the school lunch program with its meals and money by
month (p123); an 18-month school budget request for the move to a July-June year (p125-129); and a historical
note quoting the 1922-23 school budget ($27,912) inside a retirement tribute (p96, NOT LANDED).

## Integration pass, 31 October 2026: what was done with each item

Opt-ins and names are in `sources/data/report-tables/README.md` (1971-1980). By item number above:
1, 3 APPLIED (`cash_book_list` with `Cash in Banks:`; `recon_no_transfers`): treasurers-cash 10 accounts, reconciliation `checked`. 2 APPLIED (always on). 4 NOT APPLIED: a cell holding a subtotal and the next item is a reading of two figures, so the receipts stay 5,022.00 short and `check failed`. 5 APPLIED for the payments only (`statement_span`: the outer column and each section close); the balance sheet's two-column ledger is not. 6 NOT APPLIED: misreads; the cell witness found no candidate pinned by two identities. 7 left as mapped. 8 APPLIED: names registered (README, 1971-1980). Calendar-year statements stay in the ordinary datasets (README). Finder miss p71: re-read list.
