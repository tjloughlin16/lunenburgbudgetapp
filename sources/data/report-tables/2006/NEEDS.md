# 2006 edition: what the integration pass needs to change

Written by the 2006 worker, 28 October 2026. Nothing here was changed in a shared file. Each item names the
exact change, why, and the pages. Page numbers are PDF pages; printed folios run three behind (Assessors,
printed 43, is PDF 46).

## 1. Receipts, p48: a column-pair layout (`annual-report-receipts`) -- NOT LANDED until then

Textract returned the receipts page as 8 columns: `(empty) | label | figure | label | figure | (empty) | label | figure`.
`layout=groups:N` splits `ncols // N` columns per group, so no N pairs each label with its own figure (groups:4
puts `$205,146.36` beside `WETLANDS ADVERTISING FEE`).

- **Change:** in `read_report_tables.records()`, accept an explicit span list, e.g. `layout=spans:2-3,4-5,7-8`.
- **Then map** p48/1 to `annual-report-receipts` with `layout=spans:2-3,4-5,7-8`.
- **What it should prove:** the SUMMARY OF RECEIPTS categories, as read, sum to 25,125,404.05, which is the printed
  GRAND TOTAL (computed here from the nine category cells). The account rows have not been summed.

## 2. Treasurer's cash, p64 t2: the printed balance sits outside the table (`treasurers-cash`) -- refused

`emit_treasurers_cash` publishes only when a total row is in the same table. On p64 the 29 accounts are table 2
and their total, $6,651,744.00, is printed below the list (outside Textract's table) and as `GENERAL LEDGER BALANCE`
in table 1. The accounts as read sum to 6,651,744.00 (notes.csv), so the page ties.

- **Change:** let `emit_treasurers_cash` take `stated_total` from map.csv when no total row is in the table
  (map.csv already carries `stated_total=6651744.00` on p64/2).

## 3. NEW dataset `report-treasurers-reconciliation`, p64 t1: register it, and give it an identity

The FY2011-FY2025 reports print only the account list under *Reconciliation of Treasurer's cash*. This edition
also prints the year's roll-forward: balance June 30 2005, receipts 7/1/05-6/30/06 less investments transferred,
disbursements less revenue cash invested, general ledger balance. 4 rows, generic schema.

- **Register** the dataset for merge / build_db / `map_annual_report_pages.PROOF` (label `treasurers-reconciliation`).
- **Identity:** `opening + (receipts - investments transferred) - (disbursed - revenue cash invested) = general ledger balance`.
  Two cells hold two figures each (`$71,193,967.00 ($48,093,859.00)`), which the generic emitter leaves in
  `unparsed_cells`; an emitter for this table needs to split them.
- **Textract misread two digits here.** On the PDF image (rendered at 3x) the opening balance is **$4,561,756.00**
  (Textract: `$4,581,756.00`, line confidence 77.8) and investments transferred are **($46,093,859.00)**
  (Textract: `($48,093,859.00)`). With the image's digits the page ties twice: 71,193,967 - 46,093,859 =
  25,100,108 (printed) and 4,561,756 + 25,100,108 = 29,661,864 (printed) = 23,010,120 + 6,651,744. As read, it does
  not. The rows keep Textract's figures (rule 13); a triage that proposes these two corrections would be right.

## 4. Trust funds, pp65-66: the 2006 column set needs its own ENDING CASH identity

2006 prints `BEGIN BAL PRINCIPAL | BEGIN BAL EARNINGS | CONTRIB TO PRINCIPAL | REALIZED GAIN/LOSS | NET EARNINGS |
DISBURSEMENTS | ENDING CASH VALUE | UNREALIZED GAIN/LOSS | ENDING MARKET VALUE` -- no TRANSFERS column, and
`BEGIN BAL` where the regex wants `BEGIN+ING BALANCE`. So `IDENTITIES['trust-funds']`' ENDING CASH identity never
applies (ENDING MARKET = ENDING CASH + UNREALIZED does).

- **Change:** add a second identity to `trust-funds`:
  `ENDING CASH = BEGIN BAL PRINC + BEGIN BAL EARN + CONTRIB + NET EARNINGS - DISBURSE` (REALIZED GAIN/LOSS is
  NOT a term: it is already inside NET EARNINGS).
- **Tested here, outside the script:** on the 38 rows that print all of those columns, 36 tie. PERPETUAL CARE
  BEQUEST: 152,502.91 + 791.67 + 0.00 + 1,778.29 - 0.00 = 155,072.87, printed; adding the realized 383.89 would
  give 155,456.76. The two that do not tie are p66's `TOTALS` and `GRAND TOTAL`, whose CONTRIB column is already
  flagged open by the column check (printed 95,640.22, rows sum 102,708.72).

## 5. Side-by-side columns read as separate tables, right column first: p90, p91 (omnibus)

Textract numbered p90's and p91's tables RIGHT column first (p91 t1 starts `Subtotal Police`, 46 Fire Department;
t2 starts 7 Group Life Insurance). `validate_totals` walks tables in Textract's order, so the omnibus blocks are
summed out of order: `Subtotal Police` is summed against lines 1-2 (printed 1,176,126.00, rows sum 2,416,862.00)
and `Total Omnibus` against nothing. The failures on pp90-92 are this ordering, not the page.

- **Change:** order a page's tables by reading order (left edge, then top) before the block walk, or let map.csv
  give an explicit `order`.
- **Expected after it, and not tested:** `Total Gen Gov Unclass` (2,062,089.00) still misses by 851.00 if line 16,
  MacGregor Pension, is the blank `$ *` Textract read; that cell needs the image.

## 6. Tables whose first row is DATA: a `header` field in map.csv

`records()` takes row 1 as the header when no row holds a money figure. Where the page prints no header row, that
loses the first data row and names the columns after it. NOT LANDED here for that reason:

| page/table | would be | what row 1 is |
|---|---|---|
| 15/1 | report-dept-activity | `Environmental Information Responses | 99` |
| 16/1 | report-dept-activity | `Nursing Visits | 1211` |
| 24/1 | report-dept-activity | `Fires | 74` |
| 26/1 | report-dept-activity | `Abandoned 911 calls | 141` (fiscal 2006 police counts) |
| 36/1 | report-enrollment-mcas | the title row; the real header is row 2, `School/Grade | 10-01-03 | 10-01-04 | | 10/01/05 | 10/02/06` (groups:2) |

- **Change:** a map.csv column `header` = `none` | `row:N`. Then land the five above.
- **The same defect is in the officials tables, and in 2010's.** p7-p9 (and 2010 p8-p9) print no header, so each
  table's first office holder is dropped and `column_meaning` reads `v1=2005` / `v1=2010` -- a year, not a column
  name. Landed here anyway to match 2010; both editions should be re-run once `header` exists.

## 7. capital-plans: `copy` from the map, and panels -- pp88, 89, 111 NOT LANDED

`emit_capital_plan` writes `copy='committee report'` for every row. The shared file already uses
`town meeting article` (63 rows). In 2006 the Capital Planning Committee report (p17) lists its six items in prose;
the tables are town meeting article copies:

- **p111/1**, Article 21, Special Town Meeting December 5, 2006, FY07 capital plan: six items, which sum (by hand
  here) to $250,000.00, the sum the vote states (`stated_total=250000` is on the row). Needs `copy` from map.
- **p88/1 + p89/1**, Article 3, Annual Town Meeting May 6, 2006: the FY07 capital outlay list, two side-by-side
  panels with `Sub Total` rows and a `TOTAL $346,798.00` (voted contingent on a capital outlay exclusion), and on
  p89 the Capital Program list beside it, `TOTAL $1,450,000.00`. Needs `copy`, panels, and a sub-total-aware check.
- **Change:** take `copy` from a map.csv column (default `committee report`).

## 8. p69 is printed rotated: the debt repayment schedule's page 2 is unread

Textract returned p69's figures reversed (`000'592'E$`, `$17768'926`, `036151$`): the page is printed upside down.
Nothing on it is usable as read. Remedy: re-read the page from a rotated image (a Textract call -- not made by
this worker), or read it by eye. Until then p69 is `unread` and `report-debt` holds p68 only.

## 9. A decision, not a mapping: births, marriages and deaths, pp71-76

Every row names a private person: births name the infant and both parents (with maiden names); marriages name
both parties with residence and, on p74-75, dates of birth (`January 9, 1978`); deaths give name and age. No
dataset holds these in any year (`report-vital-records` holds the cemetery's burial list). A searchable index of
named births with parents and of dates of birth is TJ's call, so nothing was landed. The text is already in the
extracted text file.

## 10. For placement-counts (prose, not a table): p43

The Special Services report prints, in prose: *"ten students received services outside the district during the
2006/2007 school year. Of the ten students, eight are In day placements and two are In residential placements."*
Parts tie (8 + 2 = 10). It names the 2006/2007 SCHOOL YEAR, not a 1 March SIMS date, and cites no SIMS report --
unlike the FY2013-FY2025 sentences `placement-counts` reads. Also printed: 274 students with disabilities, 14.8%
of enrollment; 51 students on 504 plans.

## 11. p85: Textract folded data into the header

The state election's first table carries data rows in its header (`PREC A 644 485 20 1149 ...`), so its column
names hold figures and its TOTAL row fails as read. `header_from=77/1` would not help (it applies only when no
header was read). The `header` field in item 6 would.

## Integration pass, 28 October 2026

What the one integration agent did with each item above. Counts are this folder's rows after
`read_report_tables.py`; the reasons for anything not applied are here so nobody re-asks.

- **1 receipts column spans (p48).** APPLIED: `layout=spans:2-3,4-5,7-8`. LANDED: 99 accounts, `checked`.
- **2 treasurer's cash total outside the table (p64 t2).** APPLIED: `stated_total` is used when the table prints no total. 29 accounts publish.
- **3 register the reconciliation; identity; two-figure cells.** APPLIED, RENAMED to `report-treasurers-cash-reconciliation` (one name across 2001-2008). Cells printing two figures are split. The chain is `check failed`: net receipts off 2,000,000.00 and opening + net receipts off -20,000.00 -- exactly the two Textract misreads the worker found on the image. Kept as read (rule 13).
- **4 trust-funds identity without TRANSFERS.** APPLIED (absent TRANSFERS, disbursements subtracted). 73 of 80 rows `checked`.
- **5 table order on the omnibus pages.** NOT APPLIED -- a change to validate_totals' block walk (table order, cross-page grand totals, unlabelled department subtotals). validate_totals is shared with the FY2011/FY2020 reviews, and the parser changes that WERE made there were proved not to alter one check of those reports; a block-walk change could not be proved the same way in this pass.
- **6 first row is data (p15, 16, 24, 26, 36) and officials.** APPLIED: p15/16/24/26 LANDED in report-dept-activity, p36 in report-enrollment-mcas with `header=row:2`; officials keep their first holder.
- **7 capital-plans `copy` (p111, p88-89).** APPLIED for p111 (map `copy=town meeting article`; 6 rows `checked` against $250,000). p88-89 NOT LANDED: two panels with sub-totals and two different lists need a sub-total-aware emitter.
- **8 p69 printed rotated.** NOT APPLIED: needs a re-read of a rotated image (a Textract call was not allowed in this pass). Page stays `refused` with its reason.
- **9 births, marriages, deaths.** NOT APPLIED -- a decision for TJ, not a mapping: named births (infants, parents) and marriages (dates of birth) stay NOT LANDED.
- **10 placement count in prose.** NOT APPLIED -- prose figures (placement counts, vital-record counts, fire incidents, capital plan prose, pie-chart percentages) need a prose reader; no table reader can land them. `placement-counts` is SIMS-sourced and dated 1 March; these sentences name a school year and no source, so adding them is a decision about mixing two measurements, not a mapping. Recorded here with their pages; nothing was inferred.
- **11 p85 data in the header.** APPLIED by the header-stops-at-counts rule in validate_totals.split_header.
