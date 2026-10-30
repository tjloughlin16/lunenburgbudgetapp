# 1961 edition: what the shared code needs (for the integration pass)

Edition: calendar 1961 annual town report, `4548-1961-annual-town-report.pdf`, 128 pages. Tables were read on the 51 pages
`find_financial_pages.py --list 1961` picked; 65 tables (map.csv), 37 landed pages (pages.csv; 17 `proven`). Opt-ins in
edition.json are the 1971 set (`accountant_marks`, `stop_for_comma_without_dollar`, `id_column_words`,
`recon_net_on_transfer_line`, `stacked_pairs`, `receipts_span`) plus `unlabeled_subtotals` and `rounding_tolerance_usd: 1`.
Hand checks below are computed from `build/textract/out/4548-1961-annual-town-report.cells.tsv`. `--check` reproduces.

## FINDER MISSES: 0

Ten picked pages have no cells (p14, p50, p52, p60-63, p75, p76, p122): all prose, with the money in sentences (Town Clerk
and Tax Collector letter, Tree Warden, Conservation, Highway, Library, warrant articles with amounts in the text, school
lunch letter). No right-hand column of bare figures on any of them (lines read for p14, 50, 52, 60-63, 75, 76, 122). Bound,
not proof.

## ROSTER PAGES

p46 police, p47 auxiliary police, p49 fire (continued), p97-99 school resignations and appointments, p115-119 school
personnel 1961-62 (name, years, year appointed; no pay printed). Written to `rosters.csv`. p48 (fire department, three
columns of names) WAS sent and is landed in `report-officials` family `fire-department-roster`. Not sent either, so out of
scope: births p78-80, marriages p81-84, deaths p85-86, jury list p87-88, enrollment by grade p120, election check list p126.

## PRIVACY

No `withheld_rows`. Trust fund depositor and bequest names, school prize donors and grant recipients, the 1961 election
candidates and the fire department names all landed (TJ, 30 Oct 2026: everything in the annual reports is public).

## NEW NAMES in this folder (not in the README's settled list)

- `report-capital-project-costs` (p68): the School Building Addition Committee's cost of the new wing ($282,411.90, which is
  the `Total Costs` of the p42 issue), the existing building ($14,755.11), committee expense, project total $297,257.59. A
  project cost to completion, not a year and not the 2001-2010 `report-capital-projects` fund schedule.
- `report-tax-collection-levy-years` (p29/2, p29/3): the Tax Collector's table by levy year, landed OUTSIDE `tax-collection`
  on purpose; see item 3. Fold it into `tax-collection` once item 3 is fixed.
- families inside existing datasets: `report-valuation` `budgets-valuation-tax-rate-six-year` (p11),
  `report-treasurers-then-and-now` `office-then-and-now-1951-1961` (p15), `report-expenditure-shares`
  `tax-dollar-distribution` and `receipts-share-analysis` (p18, p19), `report-fund-balance-sheets` `debt-accounts` and
  `trust-accounts-in-custody` (p21), `report-school-special-accounts` `school-athletic-account` (p114),
  `report-school-staff-fte` `school-cost-per-pupil` (p113/2), `report-officials` `fire-department-roster` (p48).

## SHARED-CODE CHANGES THE EDITION NEEDS (none made here)

1. **Receipts: two section subtotals printed one row low (p24).** `Licenses and Permits: | | 4,319.32` is the Trust and
   Investment Funds subtotal (325.00 + 1,678.54 + 32.66 + 1,419.54 + 428.58 + 187.50 + 187.50 + 60.00 = 4,319.32) and
   `Treasurer: | $ | 1,137.94 $` is the previous block's subtotal (69.30 + 71.50 + 7.26 + 150.00 + 650.00 + 189.88 = 1,137.94).
   The span emitter counts them as accounts: 138 receipts rows `check failed`, `accounts sum 2,114,314.43 vs the printed
   GRAND TOTAL 2,108,857.17`, off 5,457.26 = 4,319.32 + 1,137.94. By hand the 25 right-hand-column figures of p22-25 sum to
   2,108,857.17 to the cent. Same as 1975 NEEDS item 2 (a row whose label ends in a colon with only a last-column figure,
   under a heading row, is a subtotal shifted from above).
2. **Treasurer's cash, p22/1: the roll-forward and the accounts are one table.** Mapped as `treasurers-cash` the emitter
   refused (`accounts sum 6,743,059.32, printed 207,301.27`), so it is mapped to `report-treasurers-cash-reconciliation`
   and lands 12 rows `no check`. Same as 1971 NEEDS item 1 and 1975 NEEDS item 3 (`Cash in Banks:` should open the account
   list; `Balance December 31, 1961 per cash book` is the closing line; the 207,301.27 is printed three times). By hand:
   138,829.27 + 2,108,857.17 = 2,247,686.44; less 2,040,385.17 = 207,301.27 = 203,576.31 + 3,000.00 + 724.96.
3. **Tax Collector's column names (p29/2, p29/3).** `emit_tax_collection` names columns from FORWARD, COMMIT,
   ADJUSTMENTS, REFUNDS, PAYMENTS, ABATEMENTS, TAX TITLE, BALANCES. This report heads them Committed, Collected, Abated,
   Abatement Rescinded, Refunded, Added to Tax Title, Balance, so `collected`, `abated` and `balance` come out empty (it is
   why 1971 p42 and 1966 p28 land mostly blank). Change: also accept `COLLECTED` (payments), `ABATED`, `REFUNDED`, `BALANCE\b`
   and `ADDED TO TAX TITLE`; then p29 can move into `tax-collection`. Until then the table is in the generic dataset, so no
   figure is lost. `NONE` in the balance column is a printed zero and is dropped, so a row's later figures sit under earlier
   column names in `v1..v8`; `columns_as_printed` records which columns held figures.
4. **Omnibus budget and special articles share a table (p73/1).** `TOTAL BUDGET VOTED 1,093,589.22` is followed in the same
   table by the SPECIAL ARTICLES blocks, so a `stated_total` over the omnibus list would sum the special articles in
   (89 item rows summed 1,254,972.97). The map gives the omnibus rows NO stated_total (they read `no check`). By hand the 87
   budget lines above the total row sum to 1,093,589.22 to the cent, and the special articles tie to the printed TOTAL
   SPECIAL ARTICLES VOTED $110,993.75 (55,000.00 + 11,424.00 + 9,181.00 + 35,388.75, the taxation block being 26,404.75 on
   p73 + 8,984.00 on p74). Change: let a `stated_total` list stop at the row that carries it (the printed total row closes
   the list).
5. **Letters read as digits (`I` for 1, `II` for 11, `O` for 0).** Textract returned `I`, `II`, `O` in figure cells (p114/2
   `April 2 | II`, `October I | 6`; p124/1 `Special Milk @n/c` June `I`; p112/1 `$ O`). The reader drops them without recording
   an `unparsed_cells` entry, which in p114/2 shifts October and November miles into the calls column; that table is
   therefore NOT LANDED. Change: a lone `I`/`l` as a count in a column of counts reads as 1 (a CALENDAR_REPAIRS entry) or is
   at least recorded as unparsed. The lunch counts then tie: Special Milk @n/c 18 + 1 = 19 as printed.
6. **Footnote asterisks glued to a figure (p111/1).** `$ 1,789.86**` (Vocational Education, 1961 spent) is unparsed (the
   `**` has no space before it); the row keeps its column names correctly (`columns_as_printed` = `1961 Budget | 1962 Budget`)
   and `unparsed_cells` records it. Same as 1975 NEEDS item 1.
7. **Wide schedules wrap (p42/2).** The 13-column debt schedule has more than eight value columns, so each printed row lands
   as two rows (the first carrying the year and the leading columns, the second the rest). No figure is lost; the row
   identity checks close (`checked`). `Fwd1,095,000` and `1967 1968` (two years in one cell) are read as printed. Change: more
   `v` columns, or one row per printed line.
8. **Accountant's schedule: figures on a row below their label (p35, p40).** Eight rows (p35 table rows 3, 8, 13, 18, 30; p40
   rows 25, 33, 36) carry the figures while the account name sits on the row above or in a neighbouring cell, so the rows
   land `label_missing` and the two pages stay `unproven` (refused_by appropriations). E.g. p35 row 3 `7,500.00 | 3,000.00 | |
   | 2.25 | | 29,997.75` follows `Chapter 90 Construction 1961 White Street and Shirley Road Labor`. Not fixed; the account
   schedule has no row-identity check in this layout, so every schedule row reads `no check`.
9. **Unlabelled-total check on mixed-unit tables.** The validator reads labels like `Total receipts, exclusive of bond
   issues` (p15) and `Vocational Education ... ($617.10 total)` (p112/2) as totals; those two tables have `checks=none`. By
   hand p112/2's 1961 Receipts column sums to the printed 154,212.84 over its 12 lines.
10. **Lunch tables (p124).** Both tables read `check failed` and the reasons are in the page, not the reader: `Number of Days
   Served` prints `16 (Jr.-Sr. H.S.) 14 (Elementary)` for September and the column of 156 other days + 16 = 172 or + 14 =
   170 is not the printed 171 (not reconciled here); the Lunchroom Sales column sums to 44,425.22 and prints 46,035.78, the
   difference 1,610.56 being the `BALANCE-$1,610.56*` named in that column's header; the USDA commodities column sums to
   9,695.60 and prints 9,698.61 (off 3.01, cause not established).
11. **p15/1 `None`.** `Building applications and permits processed | None | 369`: the reader drops `None`, so 369 sits in the
   1951 column (noted in map.csv).
12. **p43/2 NOT LANDED.** Four fund panels (Library and Sidewalks and Grounds stacked on the left; Worthy Poor and Cemetery
   Perpetual Care stacked on the right) in one eight-column table. Same defect as 1975 NEEDS item 4. The funds' printed totals
   are in `trust-funds-summary` (p43/1), and the roll-forward (p44-45) lands.

## Integration pass, 31 October 2026: what was done

Names and opt-ins are in `sources/data/report-tables/README.md` (1959-1970). Pages proven/unproven/refused:
17/20/0 as the worker left the folder -> 25/12/0. Renamed: `report-tax-collection-levy-years` -> `report-tax-collection-by-levy-year` (family `tax-types-by-levy-year`); p19 -> `treasurers-receipts-pie`.
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
