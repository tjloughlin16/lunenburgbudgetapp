# 1960 edition: what the shared code needs (for the integration pass)

Edition: calendar 1960 annual town report, `4551-1960-annual-town-report.pdf`, 120 pages. Tables were read on the 49
financial pages `find_financial_pages.py --list 1960` picked (58 tables in map.csv, 31 landed pages in pages.csv, all
`unproven` by the reader's own identities). Opt-ins in edition.json: the 1971 set (`accountant_marks`,
`stop_for_comma_without_dollar`, `id_column_words`, `recon_net_on_transfer_line`, `stacked_pairs`, `receipts_span`,
`unlabeled_subtotals`, `rounding_tolerance_usd: 1`). Hand checks are computed from
`build/textract/out/4551-1960-annual-town-report.cells.tsv`. `--check` reproduces. No `withheld_rows`.

## FINDER MISSES

1. **p19, the County block of the receipts (7,167.78).** Textract's table 2 stops at `Hawkers' and Peddlers' Licenses`
   (36.00); below it the lines print the State subtotal 294,998.58 and a `County:` block (Aid to Highways Chapter 90
   Construction 3,348.85, Maintenance 2,699.89, Dog Refund 961.84, Dutch Elm Disease Control 157.20 = 7,167.78) that is
   in NO cell. Money, no cells; a re-read of the page (not a reader rule) would land it.
2. Pages sent and read as prose (money in sentences or warrant text, no table): p41, p42, p48-p50, p60-p62 (warrant
   articles), p81, p89, p63 (returns only). Nothing missed by eye there.

## ROSTER PAGES

p82-83 School Department resignations and appointments (name, date, present location); p108-112 Lunenburg School
Personnel for 1960-61 (name, education, degree, years of experience, year appointed, subject or grade; no pay). Written to
`rosters.csv`. Not sent for tables, so out of scope: births (p67-68) and other vital-record lists, school enrollment by
grade (p113), prize and scholarship names (p89), the auxiliary police roster (p39, a name list).

## SHARED-CODE CHANGES THE EDITION NEEDS (none made here)

1. **Treasurer's cash, p18/1: `CASH_INVESTED` does not match `Cash In Banks:`.** Same as 1971 NEEDS item 1: roll-forward
   and bank accounts are ONE table, so `treasurers-cash.csv` and the reconciliation get 0 rows
   (`accounts sum 5,650,165.11, printed 138,829.27: not published (refused)`). Here the chain IS labelled and complete:
   `Balance December 31, 1959` 307,850.57; `Receipts January 1 thru December 31, 1960` 1,575,537.80; unlabelled subtotal
   1,883,388.37 (there is no LESS INVESTMENTS line); `Disbursements ...` 1,744,559.10; `Cash Balance December 31, 1960`
   138,829.27; the subtotal 1,883,388.37 repeated; `Balance December 31, 1960 per cash book` 138,829.27. By hand:
   307,850.57 + 1,575,537.80 = 1,883,388.37; less 1,744,559.10 = 138,829.27. The three banks (125,090.88 + 3,000.00 +
   10,738.39) sum to 138,829.27 as printed. Not run with a patched pattern here.
2. **Accountant's schedule (p26-37): the identity does not apply, 465 rows `no check`.** Same as 1971 NEEDS item 2: the
   carry-forward column is headed `Balance to 1961`, which `BALANCE (?:TO )?(?:FY|FISCAL)` does not match; widen it to
   `(?:FY|FISCAL|19\d\d)`. By hand from the cells: **127 of 127 rows that print a Total Funds Available figure close**
   (total funds available - total expended - balance to revenue - balance to 1961, blank as zero), none fail. Marks
   `RF`, `ED`, `Fwd`, `TR` follow a figure here and read; the first column is `Approp. Forward`, before the account.
3. **Receipts (p18-21): `check failed` 117 of 117, because three section subtotals are printed beside the NEXT heading.**
   Same as 1971 NEEDS item 3 and 1975 NEEDS item 2: `Motor Vehicle and Trailer Excise:` 39,714.61 (the previous-year taxes
   subtotal), `Farm Animal Excise:` 94,506.22 (the motor vehicle excise subtotal) and `Interest:` 416.27 (the farm animal
   excise subtotal) are read as accounts (134,637.10). By hand: accounts read 1,703,007.12 - 134,637.10 + the County block of
   FINDER MISS 1 (7,167.78) = **1,575,537.80, the printed Total Receipts, to the cent**.
4. **Voted budget (p58/4, 58/5, 59/1): `* 23,000.00` for the Reserve Fund is in no row** (a printed asterisk before the
   figure with a space; 1975 NEEDS item 1). `check failed` 71 of 71, off by exactly 23,000.00: 974,805.80 read + 23,000.00 =
   **997,805.80, the printed Total Budget Voted**. The Assessors' heading is not in any cell at the head of 58/5.
5. **Payments (p22-25): `no check` 138 rows (`checks=none`).** By hand: the 36 unlabelled section subtotals in the third
   column (p22-25, including `Invested, United States Treasury Bills` 247,035.00) plus the Assessments subtotal 23,329.76
   that Textract put in the SECOND figure column of the `Invested, ...` line (p25 row 5) = **1,744,559.10, Total Payments,
   to the cent**. The reader does not take the shifted subtotal.
6. **School lunch (p117): two cells print a label or a second figure with the amount.** `14*` (September, adult milk; a
   footnote mark, row 2 col 9) and `2,000.00 Finance 5,684.47` (October sales) and `Comm. (Oct.1959) 816.50` (October
   commodity value) are not read, so ten of eleven `lunches-served-monthly` rows are `check failed` on the last column only:
   by hand columns 1-7 of the counts tie to TOTALS to the unit (132,924; 3,408; 7,473; 2,661; 146,891; 56; 4,239), and the
   finances columns 1-4 tie to the cent; column 5 (sales) ties with 2,000.00 + 5,684.47 (38,274.77 + 7,684.47 =
   45,959.24 printed) and column 6 with 816.50 (9,446.50 + 816.50 = 10,263.00 printed).
7. **Balance sheet (p16-17): no identity is taken (1975 NEEDS item 7).** By hand: the asset subtotals (p16/2) sum to
   636,829.26; the liability and reserve subtotals (p16/1 and p17/1) sum to 636,829.26, the printed total. Debt: 132,000.00 +
   963,000.00 = 1,095,000.00 (p17/2, p17/3). Trust funds in custody: 67,335.55 + 1,048.51 = 68,384.06 (p17/4, p17/5).
8. **p104/1 holds the budget summary AND the School Committee's special accounts in ONE table.** Landed whole in
   `report-school-budget-summary` (as printed); `report-school-special-accounts` in 1971 splits them by table. Splitting by
   row (from `SPECIAL ACCOUNTS:` down) is a reader change if wanted. LESS: P. L. 874 lines print two figures in a cell.
9. **p15, the Treasurer's pie chart ("We Received / We Spent 1960").** Only twelve small slices reached a cell (three tables
   of four); the large slices (support of schools, school construction, school lunch, agency and trusts, highways) are in
   the page lines. Landed as `report-expenditure-shares`, family `treasurers-spending-pie-percent-and-dollars`: percent
   AND dollars (the 1983 family holds percents only). The percent is part of the label; the dollar amount is v1. The 12
   dollar amounts equal the p23-24 payment totals (e.g. Library 10,362.91).
10. **Registrations.** No new dataset names: every table landed in an existing name (settled-name rule). New FAMILIES in
    existing datasets: `report-valuation` `assessors-1910-1960-comparison`; `report-fund-balance-sheets`
    `trust-funds-in-custody`; `report-school-staff-fte` `school-cost-per-pupil-town-statistics`;
    `report-school-special-accounts` `athletic-account`; `report-expenditure-shares` family above.

## What this report prints that 2010 did not

An all-cash, calendar-year Treasurer's receipts-and-payments statement with the Treasurer's pie chart; a general fund
balance sheet with unexpended appropriation balances, federal grants, and the Stabilization Fund established at the 1960
Town Meeting ($100,000 voted from surplus revenue, $2,059.00 on the sheet at year end); the Assessors' 1910-1960
comparison; the School Committee's athletic (Chapter 658) and lunch-program statements.

## Integration pass, 31 October 2026: what was done

Names and opt-ins are in `sources/data/report-tables/README.md` (1959-1970). Pages proven/unproven/refused:
0/31/0 as the worker left the folder -> 18/13/0. Renamed: pie families -> `treasurers-payments-pie` (p15/1-2) and `treasurers-receipts-pie` (p15/3).
Opt-ins set: `colon_heading_subtotals`, `cash_book_list`, `recon_no_transfers`, `dash_zero`, `accountant_marks_wide`, `accountant_marks_before`, `marks_wide`, `year_labels`, `statement_span`, `receipts_stop_at_grand`, `collector_columns`, `signed_figures`.
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

Pages proven / unproven / refused: 18 / 13 / 0 before, 29 / 2 / 0 after; the 2 not proven are registered as blocked (scratchpad file for `page-blocked.csv`, appended by the parent).

Readings and identities opted into in `edition.json` (each documented where it is defined in `scripts/read_report_tables.py`, or `scripts/declared_identities.py`): `expended_from_amounts`, `ed_mark`, `stepped_subtotals_in` (2), `school_statistics_totals`, `dollar_sign_labels`, `cell_readings` (1), `declared_identities` (1), `line_rows` (1), `signed_figures`.

Blocked: p9 (not a financial table: a two-year comparison with no printed identity); p15 (chart, not a table).
