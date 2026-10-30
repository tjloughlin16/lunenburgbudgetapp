# 1979 edition: what the shared code needs (for the integration pass)

Edition: calendar 1979 annual town report, `4501-1979-annual-town-report.pdf`, 164 pages. Tables were read on the
65 pages `find_financial_pages.py --list 1979` picked (89 tables in map.csv; 16 pages `proven`, 33 `unproven` in
pages.csv). edition.json opt-ins: `unlabeled_subtotals`, `rounding_tolerance_usd: 1`, `accountant_marks`,
`stop_for_comma_without_dollar`, `id_column_words`, `recon_net_on_transfer_line`, `stacked_pairs`, `receipts_span`
(the receipts, accountant's schedule and reconciliation ones are exercised; the others inert, set per the brief).

## FINDER MISSES

One, and it is a part of a table on a sent page, not a whole page: **p85, `Raise by Taxation and Appropriate:`** (the third
group of the special articles, after `Transfer from E. & D.`, `Transfer from Revenue Sharing` and `Transfer from Other
Available Funds`). Ten articles (13 Sewerage-Study Plan 18,000.00; 18 Repairs - Jones House 8,250.00; 24 Dump Truck w/Plow
600.00; 25 Front End Loader/Backhoe 964.00; 28 Drainage Various Streets 25,000.00; 30 Reconstruct/Widen Highland Street
15,000.00; 31 Plow Private Roads 6,500.00; 32 Police Cruisers 6,050.94; 33 Radio Equipment-Police 1,880.24; 37 Line & Fill
Tennis Courts 5,145.90) and the group total `$ 87,391.08` are in `lines.tsv` (lines at top 0.7335-0.8864, left ~0.60-0.85) and
in NO Textract table. It is financial: the items sum to 87,391.08 to the cent, and the page's four groups close the
printed TOTAL SPECIAL ARTICLES VOTED: 63,966.00 + 80,160.00 + 14,607.92 + 87,391.08 + 202,000.00 (86/1, borrowing) =
448,125.00. Not landed (the reader reads cells only), so the special-articles family sums to 360,733.92, not 448,125.00.

Every other page not picked is prose (checked the money lines of pp12, 13, 17, 24, 28, 33, 41, 87-91: sentences, no
tabular figures). Bound, not proof.

## ROSTER PAGES

p30 roster of firemen; pp117-142 School Department personnel (resignations, retirements, teachers/supervisors/specialists
with college, degree and step, custodians, aides, library aides, school lunch personnel with start date). No pay is
printed. Written to `rosters.csv`. Births, marriages and deaths (pp78 and 162), burials and the scholarship recipients
(p150) are on pages that were NOT sent for tables and are out of scope.

## PRIVACY

`withheld_rows` not used (TJ, 30 October: everything in the annual reports is public). Named in the landed rows: donors of
perpetual-care bequests (75/2) and the donors and prize recipients of the school prize fund (75/1, 76/3).

## SHARED-CODE CHANGES THE EDITION NEEDS (none made here)

1. **A printed `-0-` is dropped, and the figures after it shift LEFT into the wrong columns.** 40/1 (14 cells), 59/1 (11),
   73/1 (11), 60/1 (1). Effects, all visible in the rows: `report-financial-performance` lines 4 (`Prior Years Taxes
   Uncollected`: 12,489 then four `-0-`), 18 and 19 (all `-0-`; line 18 has no row at all); `report-debt` `debt-by-issue`
   SANITARY LANDFILL 10-5-79 has v3 = 202,000 although that figure is the BALANCE (v8) -- and the row reads `checked`;
   `tax-collection` blanks where a balance is `-0-`. Change: read `-0-` / `$-0-` as the figure 0.00, per column (a
   calendar-only repair in `CALENDAR_REPAIRS`, opt-in, because earlier FY reviews must stay byte-identical). The map
   notes on 40/1, 59/1 and 73/1 carry a WARNING until this is done. 2001 NEEDS.md also met `$-0-`.
2. **Receipts: a subtotal that Textract put on the wrong row.** p43 table 1 row 21 reads `Special Assessments: | | 453.00`.
   By coordinates (`lines.tsv`, page 43): `453.00` is at top 0.4975, directly under `360.00` (0.4829), the last Farm Animal
   excise line, and the label `Special Assessments:` is at top 0.5260; 93.00 + 360.00 = 453.00. So 453.00 is the unlabelled
   subtotal of `Farm Animal, Machinery, Equipment Excise`, not an account, and the accounts sum to 16,812,368.27 against the
   printed total 16,811,915.27, off by exactly 453.00. All 171 receipts rows therefore read `check failed`; with the one row
   treated as a subtotal they tie to the cent. Change: when a figure sits directly under the last item of a group and a row
   label sits lower, move it (or an edition-level `figure_moves`/`subtotal_rows` list naming page/table/row 43/1/21).
3. **Accountant's schedule: two figures in one cell** (`4,250.00 750.00TR`, p63, p68, p69, p70: total expended and
   balance to revenue, with the `TR` mark, in the Total Expended cell). The reader takes one figure and `Balance to
   Revenue` reads as blank, so the row identity fails: 12 rows `check failed`, all of this shape (p63 x6, p68 x1, p69 x2,
   p70 x3), and the printed cells are in the lines. `accountant_marks` handles `TR` only after an APPROPRIATED FORWARD
   figure. Change: split a cell holding an amount and a `TR`/`R`-marked amount into two columns when the page's
   header has both. Also unparsed there: a trailing ` R` / ` A` mark (`26,800.00 R`, pp64-71).
4. **Two figures in one cell on other tables**: p72/2 `Disbursements ... 7,653,941.57 (4,119,424.16)` (the disbursement and
   the revenue cash invested; the row has no value in `report-treasurers-cash-calendar-year`), and p59/1 MIDDLE SCHOOL
   (`1,340,000 40,000`: two issues of one project in each cell, so TOTAL MIDDLE SCHOOL `check failed`, 1 of 29 rows).
   `stacked_pairs` is for principal and interest only.
5. **Footnote marks and signs on amounts, unparsed (value dropped)**: `$ 14,607.92**` (85/5, 86/2), `$ 20,765.00**`
   (156/1), `$ 3,560,880.*` and `$ 1,718.*` (154/1, 152/1; trailing full stop AND star), `- 35,000.` and `+ 128,799.40`
   (154/1; a spaced sign), `$1,261.00$` (p61). The unparsed cells are listed per row in `unparsed_cells`. Change: strip
   a trailing `*`/`**`, and read `- N`/`+ N` as signed, in CALENDAR_REPAIRS.
6. **Revenue cash invested, p77 table 1 is NOT LANDED.** Textract merged each half-year's banks, vehicles and amounts
   into multi-line cells and the reader glues the merged counts into a number (v1 = `611111715`; `123`; `12351`). The
   SUBTOTAL and TOTAL rows are corroborated by 77/2 and 77/3, which are landed. Change: a table emitter for multi-line
   cells (split a cell on its line breaks, which `cells.tsv` does not keep) or a read from `lines.tsv`.
7. **School lunch income (143/1): the `Receipts from Commonwealth of Massachusetts` column does not parse** (several coded
   amounts in one cell: `36.60/MW 5,037.95/CC 1,299,36/NFA`; the code is printed on the page), so in most rows the
   columns after it shift left and `TOTAL INCOME` lands in the Commonwealth column. `checks=none` on 143/1. By hand
   from the cells (comma-for-point repaired in `1,299,36`, `10,590,44`): every month's four receipt columns plus its
   coded Commonwealth amounts equal TOTAL INCOME RECEIVED (11 of 11), and the 11 totals sum to 181,237.45, the printed
   TOTALS INCOME. Change: a cell of coded amounts (`N/CODE`) is a list; keep it as a text cell.
8. **Single-column statements across tables.** The statement of payments (47/2, 48/1-51/1) mixes detail lines (middle
   column) with unlabelled department subtotals and single-line items (last column) under one `$` header, and the revenue
   sharing payments run across 57/3 and 58/1. The column checks fail on figures that tie, so the map sets `checks=none`.
   By hand: on pp47-51 every unlabelled subtotal equals the detail lines above it (except where my parse dropped the
   `.99` Teachers' Association Dues, a figure printed with no leading digit), and the last-column figures sum to Total
   Payments 16,839,999.27; revenue sharing payments 183,818.38 + 50.00 + 25,263.00 + 52,992.05 + 430.00 + 2,033.32 +
   2,351.04 = 266,937.79. Change: the receipts-span pooling (`receipts_span`) applied to a statement of payments, with
   subtotal detection, would turn these `no check` rows into `checked`.
9. **Register in `NEW_GENERIC` (and `map_annual_report_pages.PROOF`)**: `report-financial-performance.csv`,
   `report-school-lunch.csv`, `report-revenue-cash-invested.csv`. Three new datasets, GENERIC columns. Names to reconcile
   with the sibling 1971-1980 folders: `report-school-lunch` is the name 1971-1977 use (1978 uses
   `report-school-lunch-program`, same quantity -- one name is needed); `report-revenue-cash-invested` is also 1978's and
   1980's name (same quantity); `report-financial-performance` is the Treasurer's 19-line comparison FY1975-FY1979 and
   may be the same quantity as 1978's `report-per-capita-comparison` and 1980's equivalent -- not checked; the integration
   pass decides. A new family in `report-fund-balance-sheets`: `debt-accounts-serial-loans` and
   `debt-accounts-net-funded-debt` (55/1, 55/2: the debt accounts of the balance sheet; the page does not say in the
   cells which side each is). The half-year reconciliation (72/2) is in `report-treasurers-cash-calendar-year` in its own
   family `cash-reconciliation-and-accounts-half-year` (six months, 1 July - 31 December 1979); it is neither a fiscal nor
   a calendar year and must never be summed with one.
10. **`header: row:N` on `report-valuation` p42/1 and the five-year columns**: the `Total Increase` column is a difference
    printed on the page (FY1980 less FY1976), not a year; the map notes it. If the column checks should skip a column named
    `Total Increase`, that is a change; here the table has `checks=none`.

## What this report prints that 2010 did not (or that no earlier folder lands)

The Treasurer's 19-line comparison of financial performance FY1975-FY1979 (p40); a half-year (July-December 1979)
Treasurer's reconciliation with the accounts (p72); the recapitulation of revenue cash invested including interest
earned by half-year (p77); the school lunch program's own monthly income, expenditure and statistics report (pp143-144);
the debt accounts of the balance sheet and the General Revenue Sharing fund's receipts, payments and balance sheet
(pp55, 57-58); FY1980 special articles by funding source (pp85-86), voted April 7, 1979.

## Integration pass, 31 October 2026: what was done with each item

Opt-ins and names are in `sources/data/report-tables/README.md` (1971-1980). By item number above:
1 APPLIED (`dash_zero`). 2 APPLIED: the `453.00` row is caught by `colon_heading_subtotals` on its own section (93.00 + 360.00), not because the total then closes; the receipts close. 3 NOT APPLIED (two figures in one cell). 4 NOT APPLIED. 5 APPLIED (`marks_wide`), spaced signs not. 6, 7 NOT APPLIED. 8 APPLIED for the general fund payments (`statement_span`); revenue sharing not. 9 APPLIED (registered; `report-financial-performance` kept apart from 1978's per capita table). 10 not changed. Finder miss p85: re-read list.
