# 1962 edition: what the shared code needs (for the integration pass)

Edition: calendar 1962 annual town report, `4505-1962-annual-town-report.pdf`, 128 pages. Tables were read on the 56 pages
`find_financial_pages.py --list 1962` picked (36 have table cells); 73 tables (map.csv), 36 landed pages. Opt-ins in edition.json:
those of 1971. Same layout family as 1961 and 1971; settled names reused (1961's `receipts-share-analysis`, `school-cost-per-pupil`,
`school-athletic-account`, 1979's `debt-accounts-*`, 1975's `trust-funds-custody`). `--check` reproduces.

## FINDER MISSES (money printed in the page's lines, in no Textract cell; a re-read is needed, not a reader rule)

1. p40 top of the right-hand column: Cemetery Perpetual Care continued -- dividends from seven cooperative banks (Hyannis 160.00, Shirley 80.00, Wellesley 305.00, Mattapan 80.00, Wakefield 120.00, Marlborough 80.00, Falmouth 80.00 = 905.00), total $49,303.94, transfer to Cemetery Commission $1,750.00, balance December 31, 1962 $47,553.94. 40/3 stops at interest 862.16.
2. p39: the Worthy Poor and Cemetery Perpetual Care investment panels (bank books, Treasury bonds, seven cooperative banks = 23,000.00; funds 6,718.59 and 47,553.94). Only Sidewalks and Library reached 39/2.
3. p38 foot of 38/1: `Grand Totals:` row (1,040,000 | 250,548.00 | 208,000 | 25,558.50 | 1,248,000 | 276,106.50); 38/1's last row is empty.
4. p17 below the total: `Deferred Revenue Accounts` ($1,498.66 twice).
5. p65 bottom of the budget: Treasurer `Salary 1,600.00` and `Administration 4,900.00` (=6,500.00). They are why the voted budget lists sum to 1,248,028.58 against the printed total 1,254,528.58 (off exactly 6,500.00); with them it ties.
6. p110: the day-school `Monies Returned to the Town 1962` block (Chapter 70 74,113.68; Chapter 71 73,431.00; tuition, rentals, fees, ungraded classes ...; total earnings $155,790.33; net cost $611,722.67) and the adult education block (request 1,889.00; earnings 848.03; net 1,040.97). Only the vocational block (110/1) and P.L. 874 (110/2) reached cells.
7. p111: athletic fund expenditures $5,865.99 and balance on hand $3,066.69.
8. p122: the lunch summary under the tables (receipts $70,831.19, expenditures $66,780.03, balance June 15, 1962 $4,051.16) and `1960-61 COMPARISON TOTALS`.
9. p15: the large pie slices (see map); p14: the tax-dollar pie in cents (no cells at all, percentages only).
10. p92: school budget request by series in prose lines, the same figures as 109/2 (no cells). p93-97 continue it.
11. Footnotes in lines only: p25 (`$27,669.60 assessed to Tri-Town Lanes, Inc., and $41,537.04 all other` = the 69,206.64 real estate balance; tax collector's costs received $1,413.80), p27 (Town Clerk fees received $1,358.80), p66 (`$67,588.10 Transfer from Accellerated Grant`).
Pages sent with prose only, nothing missed by eye: p4 (facts, landed), p9, p45, p47, p50, p51, p56-58, p60, p68-70, p55 (veterans' prose; word list not landed).

## ROSTER PAGES
p43 fire roster (landed as `report-officials`), p104-105 School resignations and appointments, p112-117 School Department Personnel (name, years, year appointed; no pay). Written to rosters.csv.

## SHARED-CODE CHANGES THE EDITION NEEDS (none made here)

1. **p18/1 holds the Treasurer's cash reconciliation (rows 1-13) AND the opening of the receipts statement (rows 14-41) in ONE table.** The map can give one dataset per table, so it is mapped as `annual-report-receipts` with `header: skip:13` and the cash block is NOT landed: closing cash $10,182.20 (printed as Cash Balance, per cash book, and the sum of banks 7,012.57 + 3,000.00 + 169.63); by hand 207,301.27 + 2,152,547.72 = 2,359,848.99, less 2,349,666.79 = 10,182.20, all printed. Needs: split a table at a row for two emitters (or `treasurers-cash` taking `Cash in Banks:` as CASH_INVESTED, same as 1971 NEEDS item 1).
2. **Receipts: `check failed` on all 134 rows is the reader, not the page.** The section heading is printed beside the PREVIOUS section's subtotal (`Treasurer: | | 1,146.45` is the General Government subtotal; `Protection of Persons and Property: | | 500,000.00` is the Treasurer's). So labelled rows holding a lone figure in the subtotal column are subtotals. By hand ALL 28 sections tie (items to their subtotal) and the subtotals sum to Total Receipts $2,152,547.72 (981,630.43 + 393,736.08 + 694,411.84 + 82,769.37). Payments (`no check`, checks none): all 18 sections tie, the highways and trust deposits ones across a page break, and the subtotals sum to 2,349,666.79.
3. **`tax-collection` emitter reads only headings COMMIT/PAYMENTS/ABATEMENTS/REFUNDS/BALANCES** and takes the levy year from sub-heading rows. 1962 prints Committed, Collected, Abated, Abatement Rescinded, Refunded, Added to Tax Title, Balance with the YEAR as a column (and, for betterments, Apportioned). Landed meanwhile as `report-tax-collection-by-levy-year` (20 rows, all `checked` by the column totals). Hand check: every column total ties (committed 1,099,086.76; collected 978,948.81; abated 43,246.75; rescinded 232.22; refunded 8,515.09; to tax title 681.88; balance 84,956.63; betterments 1,354.75 / 1,119.91 / 195.65 / 39.19). Motor vehicle 1961 prints 19,906.85 Fwd and an additional 8,284.70 on one row (19,906.85 + 8,284.70 + 916.71 = 29,108.26 = 23,502.73 + 5,605.53).
4. **Accountant's schedule (p26-37): 386 rows `no check`** because `BALANCE (?:TO )?(?:FY|FISCAL)` does not match `Balance to 1963` (same as 1971 NEEDS item 2). By hand 136 of 136 rows printing Total Funds Available close (= total expended + balance to revenue + balance to 1963). Leading marks `ED`, `TR OS` before a figure in Total Expended (`ED 22.47`) make 8 rows `check failed` (same as 1971 item 2). p37 prints the carry-forward column as `Balance to 1962` where p26-36 print `Balance to 1963`.
5. **Debt schedule 38/3 has 13 columns** (> MAX_V=8), so each year splits into two records and `no check`. By hand principal 1,105,000 and interest 107,940.00 tie to the printed Totals row. 38/1's own checks pass.
6. **Voted budget (65-66): `check failed`** only because of finder miss 5; ties by hand with it.
7. **Cells the reader does not read** (rows land without them): a count followed by a word (`13 (families)`, `8 (families)`, 54/1); a figure and words in one cell (`$ 277,444.60 or 45.7% increase`, 7/2, so 7/2 is NOT LANDED); a leading `+` (`+ 3,113.54`, 108/1 balance on hand); a trailing `-` (`$ 510.91 -`, 110/1 total earnings); two figures with marks in one cell (`425.00 3,119.00 | (Bldgs.) 3,544.00 (New Equip.)`, 109/2 capital outlay and totals rows); a lone figure in a column the rows above do not use (39/1 `$ 72,283.51`, same as 1971 p64/1); town-facts rows with no figure (4/1: only 3 of 16 rows land).
8. Trust fund roll-forwards, balance sheet asset side, school budget by object and lunch finances are `no check` in the reader; by hand: Worthy Poor 6,379.53 + 100.00 + 239.06 = 6,718.59; Sidewalks 6,539.82 + 100.00 + 251.16 = 6,890.98; Library 11,120.00 + 168.23 + 280.00 = 11,568.23 less 448.23 = 11,120.00; Stabilization 50,000.00 + 141.69; assets and liabilities both 410,975.20; school p108 appropriation 716,055.00 and spent 702,941.46; 109/2 request 775,513.00 less 8,000.00 = 767,513.00; lunch counts and bills tie to their totals, sales total includes the $1,728.29 opening balance.

## What this report prints that 1971 did not
The Treasurer's pie analysis with dollars (p15), the Welfare table by category (p54), the first year of the Stabilization Fund (p41), state reimbursement toward bond payments (38/2), and the school budget by object rather than by series (p108).

## Integration pass, 31 October 2026: what was done

Names and opt-ins are in `sources/data/report-tables/README.md` (1959-1970). Pages proven/unproven/refused:
16/20/0 as the worker left the folder -> 26/10/0. Renamed: `report-welfare-assistance` -> `report-welfare-aid`; pie families -> `treasurers-payments-pie` / `treasurers-receipts-pie`.
Opt-ins set: `colon_heading_subtotals`, `cash_book_list`, `recon_no_transfers`, `dash_zero`, `accountant_marks_wide`, `accountant_marks_before`, `marks_wide`, `year_labels`, `statement_span`, `receipts_stop_at_grand`, `signed_figures`.
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

Pages proven / unproven / refused: 26 / 10 / 0 before, 36 / 0 / 0 after; the 0 not proven are registered as blocked (scratchpad file for `page-blocked.csv`, appended by the parent).

Readings and identities opted into in `edition.json` (each documented where it is defined in `scripts/read_report_tables.py`, or `scripts/declared_identities.py`): `expended_from_amounts`, `ed_mark`, `stepped_subtotals_in` (4), `school_statistics_totals`, `dollar_sign_labels`, `welfare_net_cost`, `cell_readings` (1), `declared_identities` (5), `line_rows` (1), `signed_figures`.
