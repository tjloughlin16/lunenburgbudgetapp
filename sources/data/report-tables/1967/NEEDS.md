# 1967 edition: what the shared code needs (for the integration pass)

Edition: calendar 1967 annual town report, `4510-1967-annual-town-report.pdf`, 140 pages. Tables were read on the 63 pages
`find_financial_pages.py --list 1967` picked; 89 tables (map.csv), 46 landed pages (pages.csv: 11 `proven`, 33 `unproven`, 2 `refused`).
Opt-ins in edition.json: the 1981 set plus `unlabeled_subtotals` and `rounding_tolerance_usd: 1`. `--check` reproduces.
Hand checks are computed from `build/textract/out/4510-1967-annual-town-report.cells.tsv`.

## FINDER MISSES: 0 pages, but three CELL gaps on sent pages

1. **p15 pie chart (`We Received` / `We Spent`).** The large slices (labels and dollars such as `$1,493,069.54`, `$1,119,658.16`, `$210,684.90`, `$189,864.51`, with their percents; which slice carries which is not established from the lines) are drawn with labels in the picture and are in page LINES only, not in a cell. 15/1 lands six small slices; 15/2 is NOT LANDED because each cell packs one slice's dollars with the next slice's label. A re-read by slice is needed. By eye from the lines: i. All Other $5,019.92 (0.2%).
2. **p18, the `Deferred Revenue Accounts` block** (apportioned street assessments not due 342.34; uncommitted apportioned streets assessments, revenue due 1968 through 1980, 342.34) is in lines (p18 lines 6, 8) with no cell.
3. Pages sent with no table and read as prose only: p74-78 (warrant articles; amounts in running text). Nothing missed there by eye.

## ROSTER PAGES

p47 Fire Department company roster; p113-121 Personnel for 1967-68, Teaching Staff (subject, education, degree, years of experience, year appointed; no pay printed). Written to `rosters.csv`. Not sent for tables. Out of scope (not sent, no money): births, marriages, deaths, jury list, enrollment by grade (p123-124).

## PRIVACY

No `withheld_rows`. Candidate names (p71), bequest donors (p40) and trust fund holders are public (TJ, 30 Oct 2026). p40 is NOT LANDED for a layout reason (item 5), not for privacy.

## SHARED-CODE CHANGES THE EDITION NEEDS (none made here)

1. **Treasurer's cash, p19/1: same as 1971 NEEDS item 1** (`CASH_INVESTED` does not match `Cash in Banks:`; `treasurers-cash` and the reconciliation get 0 rows, `accounts sum 14,100,242.10, printed 329,818.24: not published (refused)`). Chain by hand: 120,188.09 + 4,579,892.61 = 4,700,080.70; less 4,370,262.46 = 329,818.24 (printed, twice); bank list 123,507.95 + 177,748.67 + 20,968.67 + 7,592.95 = 329,818.24. Here the two disbursement/balance labels are on separate rows (no merged cell).
2. **Detailed receipts p19-22: same as 1971 NEEDS item 3.** 155 rows `check failed`. By hand from the cells: the 29 third-column figures of the four tables sum to 8,852,776.06; less the printed Total Receipts 4,579,892.61 is 4,272,883.45; adding the `Trust and Investment Funds:` section subtotal 307,009.16 (printed in the SECOND column, one row below its heading, p21) gives 4,579,892.61 to the cent. Section subtotals sit one row low (`Taxes Previous Year: 1,081,983.58`, `Grants and Gifts: 3,256.01`, `Licenses and Permits: 117,232.02`, `Treasurer: 1,232.50`, `Health and Sanitation: 1,046.80` ...).
3. **Detailed payments p23-26: ties by hand.** The 18 third-column figures sum to 8,740,524.92 including Total Payments 4,370,262.46, i.e. the other 17 sum to exactly 4,370,262.46. Map has `checks=none`: rows read `no check`. Change: honour the map `stated_total` in the payments emitter (as 1975 NEEDS item 7).
4. **Accountant's schedule p27-38: same as 1971 NEEDS item 2 (identity now matches `Balance to 1968`; 160 rows `checked`).** Seven rows `check failed`, none a misread: `TR`/`Fwd` marks BEFORE a figure (p29 r4 `TR 17.14`, p32 r4, r24); a sub-appropriation whose figures sit on another row (p29 r8: `699.00 | 699.00` with the expenditure on the lines above); `710 00` (no decimal point) read as 71000 (p34 r26; 710.00 - 702.85 = 7.15 printed); `83.00 Fwd.` with `534 00 Fees` split on the line above (p34 r46; 83.00 + 534.00 = 617.00 - 500.00 = 117.00); and **p38 r4 (`Premiums on Loans`), a PRINTED discrepancy seen on the page image**: Amounts Expended 3,807.85, Total Expended 3,807.95, Balance to 1968 2,959.15; 6,767.00 - 3,807.85 = 2,959.15, so the Total Expended column prints ten cents high. Whether the typo is the Town's or the scan's is not established.
5. **p40/1 NOT LANDED (trust funds, four stacked panels): same as 1975 NEEDS item 4.** Sidewalks and Grounds over Cemetery Perpetual Care in cols 1-4, Worthy Poor over Library in cols 5-8, and `Balance December 31, | 1967` puts the year in a figure cell (read as 1967.0). Closing balances tie to p39 and p18. Needs a re-read by panel; the bequest donors (1,625.00) and interest by bank are in the cells.
6. **p16/1 and p16/2 NOT LANDED: a label column that contains years.** `Overlay Deficits: 1963 1964 1965` (p16/1) and `Chapter 90 Construction: 1964 1965 1967` (p16/2) put four-digit years in column 1; `validate_totals.figure_cols` calls any column with 2+ parsed values a figure column, so the WHOLE first column stops being a label and 55 rows publish with `label_missing`. Tested with `layout=spans:1-3` and `header=skip:1`: same. Change: a column whose only parsed values are 1800-2100 integers stays a label column. The same defect makes the year in `debt-repayment-schedule` (p42/2, 16 rows) the figure and leaves the label empty.
7. **p18/3 tax collector NOT LANDED.** The `tax-collection` emitter published 19 rows with empty items and the figures in the wrong columns (1967 as a commitment). By-hand 1967 levy figures are in the map note. Needs a layout the emitter takes: a levy-year sub-heading with `Real Estate`, `Personal Property`, `Motor Vehicle Excise` beneath, and no printed title.
8. **p42/1 debt by issue: Grand Totals check fails for a reader reason.** The Middle School issue is one row followed by a subtotal that repeats it (1,340,000 twice) and the Elementary block prints `$ ---`. Every Grand Totals column ties by hand (map note). Change: a one-row group whose subtotal equals the row is a subtotal.
9. **p71-72 voted budget: the printed total does not close the printed lines.** 81 lines sum to 1,621,336.00, the printed `TOTAL BUDGET VOTED` is 1,612,336.00 (-9,000.00). Computed again by hand from the page image of p72 by department; rows stay `check failed`. A printed-document discrepancy, not a reader one; nothing here says which line or the total is off.
10. **p73 special articles.** The 24 amounts of 73/1 sum to 84,045.13; the printed subtotal 136,536.33 = 84,045.13 + 52,491.20 (the `Raise by Taxation and Appropriate` block of 73/2, Articles 6-30), to the cent; the two transfer blocks of 73/2 (30,000.00 and 22,973.73) sum to 52,973.73, which is the p72/3 funding total. `TOTAL SPECIAL ARTICLES VOTED 1,746,112.33` is 2,760.00 below budget 1,612,336.00 + 136,536.33 = 1,748,872.33, a printed difference unexplained here. The three blocks and the list are in `special-articles-voted` with no stated total (none of the printed figures belongs to one table).
11. **p131 school receipts: cells holding a figure and a parenthetical** (`233,409.41 (65% of Entitlement, $359,091.40)`, `80,080.00 ($16,080 due from 1967) ($64,000 due for 1968)`, `1,700.00 (We now have a year-round Program)`) do not parse, so the 1968 column has 3 of 8 values and 6 rows read `check failed`. By hand 233,409.41 + 80,080.00 + 800 + 7,595 + 800 + 195 + 1,700 + 40 = 324,619.41, the printed total; the actual column sums to 273,817.47, printed.
12. **p43 `(47,947.90)CR` credits and stray header words.** Parenthesised values with a trailing `CR` and cells such as `CURRENT YEAR $ -0-` do not parse (rows lose 5 values). Map has `checks=none`. Column identity by hand for 1967 in the map note.
13. **PROOF / generic registrations for NEW names** (`map_annual_report_pages.PROOF`, `NEW_GENERIC`): `report-welfare-services` (families `welfare-case-load-months`, `welfare-by-category`), `report-revenue-accounts-analysis` (`revenue-accounts-analysis`), `report-school-census-minors` (`registration-of-minors`). New families in existing datasets: `report-expenditure-shares` `treasurer-payments-pie-legend`; `report-fund-balance-sheets` `debt-accounts`, `trust-funds-custody`; `report-school-budget-summary` `school-net-cost-summary`; `report-dept-activity` `nashoba-mental-health-cases`.

## Integration pass, 31 October 2026: what was done

Names and opt-ins are in `sources/data/report-tables/README.md` (1959-1970). Pages proven/unproven/refused:
11/33/2 as the worker left the folder -> 19/25/2. Renamed: `report-welfare-services` -> `report-welfare-aid`; `report-revenue-accounts-analysis` -> `report-surplus-free-cash`; p15 -> `treasurers-payments-pie`.
Opt-ins set: `colon_heading_subtotals`, `cash_book_list`, `recon_no_transfers`, `dash_zero`, `accountant_marks_wide`, `accountant_marks_before`, `marks_wide`, `year_labels`, `statement_span`, `receipts_stop_at_grand`, `collector_columns`, `credit_marks`, `unit_rates`.
By kind of item above: the treasurer's-cash roll-forward (`Cash in Banks:` / `per cash book`) -> `cash_book_list` +
`recon_no_transfers`; the accountant's `Balance to 19xx` identity -> always on since 1971-1980, `TR` before a figure ->
`accountant_marks_before`; section subtotals printed on the next heading -> `colon_heading_subtotals` (dropped only
when equal to their own section to the cent, listed in notes.csv); payments over several pages -> `statement_span`;
the Tax Collector's past-participle columns -> `collector_columns` where it moved a row; `cr`/`CR` credits ->
`credit_marks`; leading `+`/`*` -> `signed_figures`; unit-suffixed rates -> `unit_rates`; `-0-` -> `dash_zero`.
NOT APPLIED (reasons in the README): the `rows` map column (one table feeding two datasets), debt schedules wider
than `MAX_V` 8, a one-issue debt group's repeated subtotal, a figure at the end of a label cell, two figures or a
figure and words in one cell, `II`/`I`/`O` read as digits (built behind `roman_counts`, measured, not set), a leading
or trailing `-`, digit groups split one per cell (1963 p9), text-valued town-facts rows, side-by-side trust panels,
and every figure Textract put in no cell (re-read list). `locate_cell_misreads.py`: 0 candidates.

## Close-out, 30 October 2026: every financial page proven or blocked

Pages proven / unproven / refused: 19 / 25 / 2 before, 40 / 6 / 0 after; the 6 not proven are registered as blocked (scratchpad file for `page-blocked.csv`, appended by the parent).

Readings and identities opted into in `edition.json` (each documented where it is defined in `scripts/read_report_tables.py`, or `scripts/declared_identities.py`): `expended_from_amounts`, `ed_mark`, `stepped_subtotals_in` (5), `receipts_two_columns`, `school_statistics_totals`, `dollar_sign_labels`, `welfare_net_cost`, `row_identity_skip` (1), `cell_readings` (5), `declared_identities` (48), `unlabeled_subtotals_in` (2).

Blocked: p15 (chart, not a table); p38 (the page's own arithmetic does not close); p45 (not a financial table: a schedule of pay rates with no printed identity); p59 (not a financial table: a fee schedule with no printed identity); p71 (the page's own arithmetic does not close); p72 (the page's own arithmetic does not close).
