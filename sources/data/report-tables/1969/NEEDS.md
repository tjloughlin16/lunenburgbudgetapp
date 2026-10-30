# 1969 edition: what the shared code needs (for the integration pass)

Edition: calendar 1969 annual town report, `4512-1969-annual-town-report.pdf`, 132 pages. Tables were read on the
53 pages `find_financial_pages.py --list 1969` picked; 79 tables (map.csv), 40 landed pages (pages.csv; 12 `proven`).
Opt-ins in edition.json: those of 1971 (`accountant_marks`, `stop_for_comma_without_dollar`, `id_column_words`,
`recon_net_on_transfer_line`, `stacked_pairs`, `receipts_span`, `unlabeled_subtotals`, `rounding_tolerance_usd: 1`).
Hand checks below are computed from `build/textract/out/4512-1969-annual-town-report.cells.tsv`. `--check` reproduces.
No `withheld_rows`. Page numbers are PDF pages (the printed folio is two lower).

## FINDER MISSES

0. **None.** Sent by the finder and returned with no cells: p10, p15, p49, p52, p53, p61, p68-71, p84 (and p85's three
   tables are courses and committee names, mapped `financial=no`). Read by eye from the lines: p10, p15, p61 and p84 carry
   no money table; p49 (Tree Warden), p52-53 (Highway; road oil and tar `20,202 gallons ... at a cost of $4,000`) and p68-71
   (warrant Articles 9 onward) hold their figures in sentences. A pie chart or percentage table without dollar figures
   was not seen. Textract returned tables on every other picked page.

## ROSTER PAGES

p95-99 resignations, appointments and transfers during 1969 (custodial, clerical, teaching, cafeteria; no pay);
p107-116 School Personnel Listing for 1969-70 (education, degree, years of experience, year appointed; no pay). In
`rosters.csv`. Not sent for tables and out of scope: births, deaths, marriages (p73-81, p130), burials (p26), senior
awards (p105), school enrollment. "Everything in the annual reports is public" (TJ, 30 Oct): a later pass may read the named lists.

## SHARED-CODE CHANGES THE EDITION NEEDS (none made here)

1. **Treasurer's cash, p22/2: same as 1971 NEEDS item 1.** `CASH_INVESTED` does not match `Cash in Banks:`;
   `accounts sum 14,416,875.90, printed 448,187.60: not published (refused)`; `treasurers-cash` and
   `report-treasurers-cash-reconciliation` get 0 rows. Differences from 1971 for the same fix: the roll-forward has NO
   `LESS INVESTMENTS` line and prints its running subtotal 4,805,625.30 twice (unlabelled, after Receipts and again after
   Cash Balance); the closing line is both `Cash Balance December 31, 1969` (448,187.60) and `Balance December 31, 1969
   per cash book | $ | $ 448,187.60`. Chain by hand: 208,225.52 + 4,597,399.78 = 4,805,625.30; less 4,357,437.70 =
   448,187.60. Accounts: 146,546.90 + 15,000.00 + 261,853.22 + 5,000.00 + 15,500.00 + 4,287.48 = 448,187.60 (the figure the
   page prints, unlabelled, as the last row). Receipts and Disbursements tie to the p26 and p30 totals (items 3, 4).

2. **Accountant's schedule (p31-42): 158 rows `checked`, so the 1971 item 2 widening is already in; 2 `check failed` are the instrument.**
   p34 `Manning Rescue Unit`: one cell holds two amounts (`53.70 530.50`), so Total Expended is unreadable; by hand
   584.20 - 584.20 (53.70 + 530.50) = 0, the TR mark. p35 `t1r10`: the account label sits on the row above and Total
   Expended is blank with the single expended figure in the Amounts column (297.54); by hand 300.00 - 297.54 = 2.46 =
   Balance to Revenue, which closes. By hand 154 of 154 rows printing a Total Funds Available figure and a Total Expended
   close within $1 once a leading `TR` is read as zero balance and a single Amounts figure is read as Total Expended.

3. **Detailed statement of receipts (p23-26): five-plus subtotals Textract printed one row low, same as 1971 item 3.**
   `Commonwealth of Massachusetts:` 61,273.87 (equals the Grants and Gifts lines above it), `Interest:` 47.61,
   `Taxes, Motor Vehicle Excise and Betterments` 3,093.21, `Cemetery:` 1,702.12, `Park:`, `Current Year Refunds:`
   3,107.12 and the like: the subtotal sits on the NEXT heading's row. The reader counts them as accounts:
   `accounts sum 5,878,429.92 vs the printed GRAND TOTAL 4,597,399.78`, all 152 rows `check failed`. By hand the 32 figures
   in the third (subtotal) column of p23-26, excluding the total row, sum to Total Receipts 4,597,399.78 to the cent.
   One further cell: `Farm Animal Excise: Current Year` prints 476.24 directly in the third column.

4. **Detailed statement of payments (p27-30): `checks=none`, 169 rows `no check`.** The validator sums each page's rows
   against the one printed total (`rows sum 1,679,101.27 (off 2,678,336.43) [triage: grouping]`) when `checks` is left on,
   a false failure on correct figures, as 1971 p48-50. By hand the 16 subtotal-column figures of p27-30 (113,892.08;
   138,738.80; 60,544.27; 272,857.91; 1,975,162.77; 25,713.52; 7,129.52; 24,278.56; 31,480.90; 859,143.10; 503,907.89;
   750.00; 16,165.51; 4,743.38; 95,466.39; 198,925.00) = 4,328,899.60, plus the four soldiers' benefits lines of p28/3 in
   the second column (29.42 + 1,518.85 + 1,152.38 + 25,837.45 = 28,538.10, whose subtotal Textract left unprinted) =
   4,357,437.70, the printed Total Payments, to the cent. `Trust Fund Deposits:` 16,165.51 and `Assessments:` 4,743.38
   are subtotals printed one row low, as item 3.

5. **Voted budget (p65-66): trailing footnote marks with no space are unparsed.** `15,097.00**` (General Health Expense)
   and `35,000.00(1)` (Reserve Fund) land in `unparsed_cells`, so the omnibus list total reads 2,218,283.31 against the
   printed 2,268,380.31 (off exactly 50,097.00 = 15,097.00 + 35,000.00) and all 83 rows are `check failed`, `checks=none`
   notwithstanding (the list-total check runs from `stated_total`). By hand the 81 amounts of p65/1-2 and p66/1-2 sum to
   2,268,380.31 to the cent. Wanted in `CALENDAR_REPAIRS`: `**` and a parenthesised single digit directly after a figure
   (also `820.00(2)`, `271.00(3)` on p67/2, which read). The `special-articles-voted` blocks (66/4 55,000.00; 67/1
   81,444.59; 67/2 24,937.21) sum to 161,381.80 by hand, and the `omnibus-funding-sources` lines (p66/3, 20 lines) to
   82,521.72; neither family is in `LIST_FAMILIES` (same as 1971 item 5).

6. **Debt (p43): `no check`, three reading limits.** (a) The rate column holds the years and the rate in one cell
   (`1956-70 2.5`, `1958-68 3.6`, `1968-87 4.2`, `1970-73 4.9`), which is unparsed, so `v1..v8` are Amount, Paid Principal
   (previous years), Previous Years Interest, Paid Principal (1969), 1969 Interest, Total Principal, Payments Interest,
   Bal.Prin. in order and the rate is in `unparsed_cells`. (b) The footnote marks `(1)`, `(2)` beside the block subtotals
   are read as the figures -1 and -2 (v2 of the two subtotal rows). (c) The header spans two rows (`Paid Principal` /
   `Previous Years Interest` / `Paid Principal` / `1969 Interest`, with `Paid Previous Years` and `Paid 1969` in the
   lines): `column_meaning` repeats `Paid Principal` for two columns. By hand: Jr.-Sr. block 985,000 + 110,000 =
   1,095,000; 855,000 + 110,000 = 965,000; 190,500 + 23,760 = 214,260; 65,000; 3,250; 920,000 + 110,000 = 1,030,000;
   193,750 + 23,760 = 217,510; balance 65,000. Middle School 1,340,000 + 40,000 = 1,380,000; 70,000; 56,280; 70,000;
   53,340; 140,000; 109,620; balance 1,200,000 + 40,000 = 1,240,000. Appropriated 1,380,000 + 100,000 + 100,000 + 1,500 =
   1,581,500. Balances 65,000 + 1,240,000 = 1,305,000, the figure the balance sheet prints as serial loans (p21). In
   the schedule (43/2), `1,000.000` for 1972's balance (a full stop in place of a comma) is a printed typo read as
   1000.000; the sum of the 1970 row 65,000 + 80,000 + 1,625 + 52,398.12 = 199,023.12 ties.

7. **`tax-collection` (p22/1): labels lost, same as 1971 item 4.** The page foot totals are printed in the figures.

8. **Lunch (p118): the days column fails its own total, and the finances table has one two-figure cell.**
   `lunches-served-monthly`: the seven count columns tie to their printed TOTALS to the unit (133,093; 5,542; 5,109; 2,716;
   131,348; 5,897; 6,644). The days column does not: April prints `17/E; 18/HS` and June `16/E; 12/HS`, the other eight
   months sum to 142, and the printed total is 173 (142 + 17 + 16 = 175 on the elementary reading, 142 + 18 + 12 = 172
   on the high school reading). Nothing here says which is meant, so the 9 `check failed` rows stand; the cause of the 173
   is not established. `lunch-finances-monthly`: see the map note (the first row holds two figures in the sales cell;
   the column closes by hand, 51,852.79 + 4,804.97 + 2,000.00 = 58,657.76).

9. **School special accounts (p124-128) land as a NEW family `school-account-rollforward` in
   `report-school-special-accounts`.** The School Department prints each special account as a short roll-forward of
   dollar lines; Textract returned each as a fragment of 1-6 rows with no header and the labels often carrying the
   dates and project numbers. Rows carry the label as printed and one amount (`header: none`). Misreads kept as printed:
   `-Gs- 4,606.00`, `02 155.98`, `$0 421.78` (p122), `1,000.000`. The `school-federal-funds-offset` and
   `school-categorical-aid-received` families of `report-school-state-aid` are the 1971 families (123/2, 123/3).

10. **p122 school budget summary: first data row packs two lines.** `1000 Series - ADMINISTRATION: Salaries Expenses | $
    42,063.00 3,615.00 | $ 39,660.58 4,522.25 | $ 6,175.00` is one cell per column with two amounts each (Salaries,
    Expenses); the figures are in `unparsed_cells`. Also `+ 4,258.69` and `+ 14,040.54` read as unparsed (a leading `+`).

11. **p45/1 first cell** holds three labels and two figures (`December 31, 1968 Balance Interest Received: | $ $ 6,340.11
    65.52`), unparsed; the 200.00 and 265.52 lines and the 6,605.63 balance read. By hand 6,340.11 + 265.52 = 6,605.63.
    p45/2 (Library) and p45/3 (Cemetery) open with empty rows. By hand from the page: Library 11,120.00 + 595.26
    received = 11,715.62, less the 595.26 transferred to the Library Trustees = 11,120.00; Cemetery 55,661.89 + bequests
    1,625.00 + interest and dividends 2,786.42 = 60,073.31, less the 2,670.11 transferred to the Cemetery Commission =
    57,403.20, the figure p44 and p21 print.

## What this report prints that 2010 did not (and 1971 did)

The Treasurer's detailed statements of receipts and payments, the accountant's schedule, the General Accounts balance
sheet, bond schedules, the voted budget with its special articles, the School Department's own summary and special
accounts (including federal funds roll-forwards and the Headstart program), and the Personnel Board's proposed salary
schedule. Not in 1971: the school lunch counts are for the school year 1968-69 on p118 (1971 has them on p127); no
veterans' services table (1971 p33), no five-year expenditure table (1971 p8), no school-dollar-by-category table (1971
p98): each was searched for by page in the cells (`grep` of table headers, not of a pattern), none is among the 79 tables.

## NEW dataset names

None new. Reused: `report-proposed-salary-schedule` (family `proposed-classification-salary-schedule`, as 1972 p15),
`report-school-lunch`, `report-school-staff-fte`, `report-school-budget-summary`, `report-school-state-aid`,
`report-school-special-accounts` (NEW FAMILY `school-account-rollforward`), `report-fund-balance-sheets` (families
`general-fund-balance-sheet` NEW for the single table p20/1 carrying both sides, `general-fund-liabilities`, `debt-accounts`
and `trust-and-investment-accounts` NEW as separate families of p21), `report-debt`, `report-trust-funds`.

## Integration pass, 31 October 2026: what was done

Names and opt-ins are in `sources/data/report-tables/README.md` (1959-1970). Pages proven/unproven/refused:
12/28/0 as the worker left the folder -> 22/18/0. Renamed: none.
Opt-ins set: `colon_heading_subtotals`, `cash_book_list`, `recon_no_transfers`, `dash_zero`, `accountant_marks_wide`, `accountant_marks_before`, `year_labels`, `statement_span`, `receipts_stop_at_grand`, `signed_figures`, `unit_rates` (`marks_wide` NOT set: it turns one row to `check failed` and proves no page).
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

Pages proven / unproven / refused: 22 / 18 / 0 before, 37 / 3 / 0 after; the 3 not proven are registered as blocked (scratchpad file for `page-blocked.csv`, appended by the parent).

Readings and identities opted into in `edition.json` (each documented where it is defined in `scripts/read_report_tables.py`, or `scripts/declared_identities.py`): `expended_from_amounts`, `ed_mark`, `stepped_subtotals_in` (4), `school_statistics_totals`, `dollar_sign_labels`, `cell_readings` (4), `declared_identities` (4), `unlabeled_subtotals_in` (2), `signed_figures`.

Blocked: p17 (not a financial table: a schedule of pay rates with no printed identity); p45 (the page's own arithmetic does not close); p118 (the page's own arithmetic does not close).
