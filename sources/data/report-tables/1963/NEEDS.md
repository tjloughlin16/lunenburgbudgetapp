# 1963 edition: what the shared code needs (for the integration pass)

Edition: calendar 1963 annual town report, `4506-1963-annual-town-report.pdf`, 124 pages. Tables were read on the 60 pages
`find_financial_pages.py --list 1963` picked; 87 tables (map.csv); `--check` reproduces. Opt-ins in edition.json: those of
1971 (`accountant_marks`, `stop_for_comma_without_dollar`, `id_column_words`, `recon_net_on_transfer_line`, `stacked_pairs`,
`receipts_span`) plus `unlabeled_subtotals` and `rounding_tolerance_usd: 1`. Hand checks are computed from
`build/textract/out/4506-1963-annual-town-report.cells.tsv`. The 1963 layout is the 1971 layout (same Treasurer's statements, same
accountant's schedule) with a smaller report: nearest example is 1971; "same as 1971 NEEDS item N" below means the same reader limit.

## FINDER MISSES

None by eye. Pages sent with no table and read as prose: p6-8 (Selectmen's and Assessors' reports), p48, p57, p58, p60, p67-70
(warrant articles), p118 (lunch narrative); the money in them is in sentences. Two things to know, neither a miss:
p17's pie chart is text (the big slices, `9.9% and $176,369.36` and the like, are chart labels, not a table; only the
small-slice legend is a table and is landed); and p16 `Where Did Your 1963 Tax Dollar Go?` (cents of the tax dollar, no dollar
figures) was not sent, correctly.

## ROSTER PAGES

p84 school administration; p99-102 School Department resignations, transfers and appointments; p109-116 school personnel
listing (name, education, degree, years of experience, year appointed in Lunenburg, subject or position; no pay); p78-79 jury
list (name, residence, occupation, last employer). Written to `rosters.csv`. Not sent for tables, so out of scope: births p71-73,
marriages p74-76, deaths p77, enrollment by teacher p117, the voters count p121. "Everything in the annual reports is public"
(TJ, 30 Oct): a later pass can read them from the text. No `withheld_rows` is used. The p45 firemen's names and p50 committee
members ARE tables and are landed (`report-officials`).

## SHARED-CODE CHANGES THE EDITION NEEDS (none made here)

1. **p9, the Assessors' recapitulation (3 tables): every amount is split into digit groups, one per cell.** `1 | 309 | 686 | 88`
   is $1,309,686.88 (item A.1), `191 | 010 | 00` is 191,010.00, `2 | 515 | 38` is 2,515.38. No cell holds a figure, so the map marks
   all three NOT LANDED and the page is `refused`. Reading rule that would land them: in a row whose figure cells are
   `d{1,3} | d{3} | ... | d{2}` (trailing group exactly two digits), join the groups into one amount. By eye the page is the
   tax-rate worksheet (A raised by taxation 1,309,686.88; available funds 191,010.00; B state 4,026.77; C county 30,241.33; D overlay
   29,000.00; E gross amount 1,572,964.98; F estimated receipts, of which Motor Vehicle excise 142,661.61 and total
   459,887.39 per the Assessors' text on p8). `report-valuation` is the nearest dataset (it holds the 1987-2010 recapitulation).

2. **p20/1 is ONE table holding the Treasurer's cash reconciliation (rows 1-14) AND the start of the detailed statement of
   receipts (rows 15-43).** The map lands it as `annual-report-receipts` with `header: skip:14` so the roll-forward rows are not
   summed as receipts; the reconciliation itself is therefore NOT in any dataset. The reader accepts the same (page, table) in two
   map rows (tried, the folder restored), but with no way to say which rows, the reconciliation dataset then also took the 29
   receipts rows. Needed: a map column `rows` (`1-14`, `15-43`) so one table feeds two datasets. Then map a second row,
   `report-treasurers-cash-reconciliation` / `cash-reconciliation`, rows 1-14, period 1963. By hand from the cells:
   Balance December 31, 1962 10,182.20 + Receipts January 1 thru December 31, 1963 2,336,257.05 = 2,346,439.25 (printed, twice);
   Disbursements 2,211,531.14; Cash Balance December 31, 1963 134,908.11 (= 2,346,439.25 - 2,211,531.14); cash in banks
   111,975.74 + 10,000.00 + 12,932.37 (cash on hand) = 134,908.11 = `Balance December 31, 1963 per cash book`. The Disbursements
   line (2,211,531.14) is $164.00 below Total Payments on p27 (2,211,695.14): both printed so, and not reconciled here.

3. **Detailed statement of receipts (p20-23): the Treasurer subtotal is printed one row low.** `Treasurer:` has Revenue Loan
   250,000.00, Treasury Bills Maturing 297,915.58, Interest on Treasury Bills 1,318.92; its subtotal 549,234.50 sits on the NEXT
   heading's row, `Protection of Persons and Property:` (p22 row 47). The reader counts it as an account, so `accounts sum
   2,885,491.55 vs the printed GRAND TOTAL 2,336,257.05` (off exactly 549,234.50) and all 129 rows are `check failed`. By hand,
   the third-column figures of p20 rows 17-43 and p21-23 (the section subtotals and the total) sum to 2 x 2,336,257.05, i.e. the
   subtotals sum to Total Receipts to the cent. Same limit as 1971 NEEDS item 3 (there five rows, here one). The rule: a heading
   label ending `:` with a figure only in the subtotal column, directly under a section whose sum it equals, is that section's
   subtotal.

4. **Accountant's schedule (p28-39, `accountant-schedule`): the identity does not apply, 485 rows `no check`.** The carry-forward column
   is `Balance to 1964`; `BALANCE (?:TO )?(?:FY|FISCAL)` does not match it. Widen it to `(?:FY|FISCAL|19\d\d)` as 1971 NEEDS item 2
   asks. Computed by hand from the cells: **139 of 139 rows that print a Total Funds Available figure close** (AVAILABLE - TOTAL
   EXPENDED - BALANCE TO REVENUE - BALANCE TO 1964 = 0, blank read as zero; a figure such as `.05` has no leading digit). The first
   column is `Approp. Forward`, BEFORE the account name. Marks after a figure are handled (`11.80 Fwd`, `7,100.00 ED`, `14,900.00 OS`,
   `250,000.00 B`, `23.56 RF`); `TR OS` stands alone in Balance to Revenue (p39).
   **Two blocks make 24 rows `check failed` today for a reason of grouping, not arithmetic:** p34 rows 28-42 (welfare: Aid to Families with
   Dependent Children, Old Age Assistance, Disability Assistance and Medical Aid for the Aged Town Relief) print sub-subtotals
   (`Total A.F.D.C.` 9,812.22, `Total D.A.` 4,329.74, `Total O.A.A.` 10,207.72, `Total M.A.A.` 9,425.88 = 33,775.56, the line's printed
   total expended), with the cash-grant figure INSIDE the label cell (`A.F.D.C. Cash Grants 9,065.17`); and p38 rows 4-12 (Park
   Department: `Total Salaries and Wages` 5,294.15 over seven figures inside the label cell, `Director $ 685.17`). The validator
   reads the printed sub-total as a section total over rows it cannot see. A figure printed at the END of a label cell is not read.

5. **School lunch p120/3 NOT LANDED.** A summary box in three columns, each a stack of text cells with figures inside the text
   (`4,956.14 Other 21,775.85 Labor 57,045.97`, `$74,054.38 TOTAL | $78,100.69 TOTAL | HAND, June 1963`): no cell is one figure. The
   figures repeat the TOTALS row of p120/2 and add expenditures 74,054.38, receipts 78,100.69 (= 21,054.72 + 57,045.97, which includes the
   4,051.16 opening balance) and the balance on hand 4,046.31 (also in the p118 prose). Needed: split a cell on figure boundaries
   when it holds a label between figures.

6. **Tax Collector's report (p27/2, p27/3, `tax-collection`): the emitter drops most columns.** It looks columns up as `FORWARD`,
   `COMMIT`, `ADJUSTMENTS`, `REFUNDS?\b`, `PAYMENTS`, `ABATEMENTS`, `TAX TITLE`, `BALANCES`; this page prints `Year | Committed |
   Collected | Abated | Abatement Rescinded | Refunded | Added to Tax Title | Balance`. Only `committed` and (for two rows) the tax-title
   column land; `collected`, `abated`, `refunded` and `balance` come out blank. Add the synonyms `COLLECTED`->payments,
   `ABATED`->abatements, `REFUNDED`->refunds, `ADDED TO TAX TITLE`->transfer, `^BALANCE$`->balance. `Abatement Rescinded` has no column
   in the dataset (nine cells blank, one `83.70`). The `Year` column and the tax-type sub-headings read as the label (the page
   prints `Poll Taxes:` / `Personal` `Property:` as a split heading), so `item` is wrong on most rows; same as 1971 NEEDS item 4.
   The page prints its own foot: committed 1,179,557.41, collected 1,060,419.19, abated 51,013.88, abatement rescinded 106.18,
   refunded 7,418.11, added to tax title 1,209.79, balance 74,438.84; and `Total Costs received by Tax Collector $1,495.18` inside the
   Totals label. p27/3 (betterments) is a new family `betterments`: Apportioned 22.27 + Interest 16.92 (1962, `Fwd.`) and
   Apportioned 179.89 + Interest 59.96 (1963), totals 279.04, all collected, `NONE` balance.

7. **School Department request tables (p87-89, `budget-request-by-series`): the figure shares the cell with the label and the signs
   are not read.** The first column is `Salaries - $19,455.` (label and REQUEST 1964 in one cell), the third `+$1,223.` / `-$ 25.` /
   `*$671.` / `+$870.*`. The reader takes AVAILABLE 1963 as v1 and leaves the request and the difference in the label text. Needed:
   a figure at the end of a label cell, and a whole-dollar figure with a leading `+`, `-` or `*` and a trailing full stop.
   The values are not lost (they are in `label`), they are unparsed. p89/3 prints no label (food or the series heading is outside the table).

8. **Bonded indebtedness (p40/1): `Grand Totals` check fails by $78,000.00.** The third group (the 1961 Jr.-Sr. High Addition loan, 4-1-61)
   has ONE issue and prints its own subtotal row under it (78,000 / 2,886.00 / 18,000 ...) equal to that issue, so the column sums
   count it twice: rows sum 1,326,000 against the printed 1,248,000 (655,000 + 515,000 + 78,000). By hand every column of the three
   group subtotals sums to the printed Grand Totals. The 11-column header is three stacked rows (`Paid / Previous Years / Principal`),
   assembled as `Paid Principal ELEMENTARY | Previous Years Interest SCHOOL | Paid Principal | 1963 Interest | Total Principal |
   Payments Interest`: the words are the printed ones, in a stitched order; the group heading `ELEMENTARY SCHOOL` leaks into two names.
   `column_meaning` should read v3 Paid Previous Years Principal, v4 Paid Previous Years Interest, v5 Paid 1963 Principal, v6 Paid 1963
   Interest, v7 Total Payments Principal, v8 Total Payments Interest, v9 Bal. Prin. 12-31-63 (v1 Amount, v2 Rate).

9. **Welfare (p55/1, `report-welfare-aid`): the persons-aided count `51*` and the split label.** The `Aid to Families with |
   Dependent Children` row is two table rows (label split), and its persons cell `51*` (footnote mark: families) does not parse, so v1 is
   Expended on that row. The `*Families` footnote text shares the TOTAL row's label cell ($109,151.07 | $83,139.27 | $26,011.80). By hand:
   expended 2,173.26 + 2,778.83 + 43,820.36 + 25,494.92 + 18,213.42 + 8,206.11 + 8,464.17 = 109,151.07;
   reimbursements 1,666.99 + 32,853.84 + 21,184.99 + 13,564.51 + 6,321.22 + 7,547.72 = 83,139.27; net 26,011.80.

10. **p18/2 last row: `Old Age Assistance Recovery 262.90` is outside the table.** Textract's cells end at `Old Assistance` with no
    figure; the line `Old Age Assistance Recovery | 262.90` is in lines.tsv (page 18, line 168; text page 18 end). With it the liabilities
    side adds up: 94,450.73 (p18/2 subtotals 91.75 + 55.81 + 17,843.62 + 76,459.55) + 262.90 + 368,442.91 (p19/1 subtotals) =
    463,156.54, the printed total, which also equals the sum of the nine asset subtotals on p18/1 (463,156.54).

11. **`special-articles-voted` and `omnibus-funding-sources` are not in `LIST_FAMILIES`** (same as 1971 NEEDS item 5): 39 rows stay
    `no check`. By hand: surplus-revenue transfers 90,600.00 (p65/3: 2,500 + 200 + 5,300 + 25,000 + 1,600 + 2,000 + 3,375 + 48,575 +
    1,450 + 600); other available funds 78,410.00 (37,000 + 9,110 + 7,000 + 8,000 + 2,000 + 14,500 + 600 + 200); raised by taxation
    61,396.00 (p66/1 48,125.00 + p66/2 13,271.00); together 230,406.00, the printed TOTAL SPECIAL ARTICLES VOTED. The voted budget
    (`omnibus-budget`, p64/3-4 + p65/2 + p65/1) closes to TOTAL BUDGET VOTED 1,270,290.88 with its stated_total: 75 rows `checked`.

12. **`report-town-facts` (p4/1) keeps only rows with a figure** (3 of 16: population 1960 6,334; tax rate 82.00; and the last row).
    County, elevation, area, roads, valuation (`$11,184,625 (Real Estate - $10,502,460; Personal Property - $682,165)`) and the
    representatives are text-valued and are dropped. Needed: keep a text-valued row (the 1975 edition's p3 needs the same).
    `report-officials` (p45) lands each row of four names as one label (`Wayne A. Balcom Frederick L. Cuddy, Jr. Roger G. Gilchrest
    John G. Proctor`): one person per cell would be better.

## NEW dataset names (for the one-name-per-quantity table)

`report-receipts-payments-chart` (p17: families `spent-small-slices-a-d`, `spent-small-slices-e-h`, `received-small-slices`: the
small slices of the Treasurer's receipts-and-payments pie, percent and dollars), `report-welfare-aid` (p55: family
`welfare-aid-by-category`: persons aided, expended, reimbursed, net cost to the town). New families in existing datasets:
`report-debt` `debt-limit-computation` (p11; the 1985 edition printed the same computation, NOT LANDED there);
`tax-collection` `betterments` (p27/3); `report-trust-funds` `stabilization-fund-rollforward` (p43/3); `report-officials`
`fire-department-roster` (p45); `report-school-budget-summary` `budget-request-by-series` (p87-89: request 1964 against available 1963,
STAGES MIXED in their own columns) and `gross-budget-and-pupil-growth` (p90); `report-school-staff-fte` `school-cost-per-pupil`
(p108/2). Used as they stand: `report-town-facts`, `report-dept-activity`, `report-elections`, `report-school-lunch`,
`report-school-special-accounts`, `report-school-state-aid`.

## Integration pass, 31 October 2026: what was done

Names and opt-ins are in `sources/data/report-tables/README.md` (1959-1970). Pages proven/unproven/refused:
12/30/1 as the worker left the folder -> 20/22/1. Renamed: `report-receipts-payments-chart` -> `report-expenditure-shares` (`treasurers-payments-pie`, `treasurers-receipts-pie`).
Opt-ins set: `colon_heading_subtotals`, `cash_book_list`, `recon_no_transfers`, `dash_zero`, `accountant_marks_wide`, `accountant_marks_before`, `marks_wide`, `year_labels`, `statement_span`, `receipts_stop_at_grand`, `collector_columns`.
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

Pages proven / unproven / refused: 20 / 22 / 1 before, 42 / 1 / 0 after; the 1 not proven are registered as blocked (scratchpad file for `page-blocked.csv`, appended by the parent).

Readings and identities opted into in `edition.json` (each documented where it is defined in `scripts/read_report_tables.py`, or `scripts/declared_identities.py`): `expended_from_amounts`, `ed_mark`, `stepped_subtotals_in` (3), `school_statistics_totals`, `dollar_sign_labels`, `welfare_net_cost`, `not_totals` (5), `cell_readings` (6), `declared_identities` (33), `unlabeled_subtotals_in` (2), `digit_group_tables` (3).

Blocked: p17 (chart, not a table).
