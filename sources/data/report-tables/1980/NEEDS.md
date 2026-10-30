# 1980 edition: what the shared code needs (for the integration pass)

Edition: calendar 1980 annual town report, `4502-1980-annual-town-report.pdf`, 140 pages. Tables were read on the 68 pages
`find_financial_pages.py --list 1980` picked; 89 tables (map.csv), 47 landed pages (pages.csv), 15 of them `proven`.
Opt-ins in edition.json: those of 1981 plus `unlabeled_subtotals` / `rounding_tolerance_usd` as briefed, and
`unlabeled_subtotals_in` (accountant schedule, payments, revenue sharing, fund balance sheets, trust funds).
Hand checks below are from `build/textract/out/4502-1980-annual-town-report.cells.tsv`.

## FINDER MISSES: 0

Every page the finder did not send was scanned for lines with money figures: p8, 12, 16, 18, 19, 20, 23, 30, 36, 78, 82-85,
89, 97-99, 104, 107. All are prose (highway and library narratives, the 1980 Proposition 2 1/2 text, warrant-article
wording with sums in sentences). None is a table of money. Bound, not proof.

## ROSTER PAGES

p17 roster of firemen; p112-114 School Department resignations and leaves (names, positions, replacements, no pay);
p115-121 School Personnel Listing 1980-81 (name, position, start date `(B.9/72)`, no pay). Written to `rosters.csv`.
None sent for tables. p73-76 (births, marriages, deaths) were NOT sent (no money): out of scope.

## PRIVACY

Nothing held out (TJ, 30 Oct 2026). `withheld_rows` is not used. Named people landed: pupil prize recipients and the
perpetual-care donors on p68-70 (trust fund pages, as 1981-1986).

## SHARED-CODE CHANGES THE EDITION NEEDS (none made here)

1. **Receipts (p39-43) read `check failed` on all 176 rows, and the cause is the instrument.** `emit_receipts_span`
   counts as accounts (a) two labelled section SUBTOTALS: p39 row 19 `Special Assessments: 553.50` (the Farm Animal
   excise subtotal, 101.50 + 452.00, printed one row low beside the next heading) and p41 row 23 `Licenses and
   Permits: 9,524.04` (a subtotal printed beside its heading), and (b) the two rows AFTER the grand total, `Less Payroll
   Deductions Receivable (9,783.95)` and `Total Receipts in FY 1980: 15,473,258.08` (which doubles the sum). By hand the
   accounts sum to the printed `Total Receipts: $15,483,042.03` to the cent: the 176 accounts summed
   as 30,956,593.70 less 15,473,258.08 plus 9,783.95 less 553.50 less 9,524.04 = 15,483,042.03 (checked). Change: stop
   reading accounts at the grand-total row, and treat a row whose label is a `:` heading and whose only figure is the
   running sum of the amounts above it since the last subtotal as a subtotal. 15,473,258.08 is the receipts line
   of the p38 reconciliation (`15,483,042.03 - 9,783.95`).
2. **Accountant schedule (p56-66), 9 rows `check failed`, all accountant marks the reader does not take:** a mark
   printed after a figure in the Approp. Forward column (`4.76R`, `600.00 28,000.00R`, `35,000.00R`, `6,500.00R`), and
   two figures in one cell where the second carries `TR` (`27,371.00 1,229.00TR`, `16.25TR 21,400.00 186.00TR`,
   `1,236.22 4,500.00TR`, `3,672,283.38 115,207.92TR`). p62 rows 14, 15, 17, 18, 20; p58 row 46; p63 row 22; p64 row 48
   (`675.00Fwd`); p66 row 23 (the balance cell is in the next column to the right). `R` and `TR` are the accountant's
   `returned` and `transfer` marks as 1981-1985 used `rct`, `ret`, `TR`.
3. **Debt (p55), 7 rows `check failed`:** `TOTAL MIDDLE SCHOOL` sums two issues printed in one cell
   (`1,340,000 40,000`), so its row identity has nothing to close on; and in the repayment schedule the FY1990 column
   (panel 2) closes on `GRAND TOTAL: PRINCIPAL 20,000` while the validator sums the landfill `Total: 21,260`. By
   hand every column ties: 1982 principal 65,000 + 20,000 + 20,000 = 105,000, interest 17,745 + 1,020 + 11,340 =
   30,105; FY1990 20,000 + 1,260 = 21,260.
4. **Payments (p44-47) and revenue sharing payments (p53/3, p54/1) are `checks=none`** because the validator counts the
   section subtotals as payments (the subtotal sits in the right-hand column with the group label above, so
   `unlabeled_subtotals_in` does not catch it). By hand: the 19 figures in the right-hand column of p44-47 above
   `Total Payments:` sum to $15,692,410.24, the printed Total Payments (less Payments Deferred until FY 1981
   (217,221.16) = $15,475,189.08, the Disbursements line of the p38 reconciliation); revenue sharing: opening line
   116,165.72 + the subtotals on p53-54 = 240,419.41, the printed Total Payments. Same as 1981 p101-104.
5. **Stacked-line cells.** p37 table 1 prints seven lines in one cell per fiscal year (`$669,901.94 32,750.34 96,641.17
   159,832.05 (297,378.25) -0- (42,348.66)`) beside one cell of seven labels, and a `Free Cash` row with
   `$533,393.38 For FY 1978`. They land as ONE row each with no figures and the text in `unparsed_cells`. Change: split a cell
   of N lines against a label cell of N lines (the label cell must have the same number of lines). By hand the FY1976
   column sums: 669,901.94 + 32,750.34 + 96,641.17 + 159,832.05 - 297,378.25 - 0 - 42,348.66 = 619,398.59 = the printed
   `Balance Surplus Revenue June 30`, so the idea is sound. The same shape closes p71/1 (item 6).
6. **p71 table 1 (revenue cash invested by half-year and bank) is NOT LANDED.** Each half-year's five bank lines are stacked
   in one cell per column; a first run produced a row whose first figure was `20221` (the digits `20 2 2 1` of a stacked
   count column), which is a number that does not exist on the page (rule 13). The totals are landed from 71/2 and 71/3
   (FY1980 7,792,190.78 invested, 196,074.90 earned; calendar 1980 9,318,675.07 / 208,596.80; first six months FY1981
   5,700,628.01 / 98,060.74). Two subtotals exist ONLY in 71/1: 7/1/79-12/31/79 `SUBTOTAL 4,174,143.72 / 85,538.84` and
   1/1/80-6/30/80 `SUBTOTAL 3,618,047.06 / 110,536.06`; they sum to the FY1980 total (7,792,190.78 and 196,074.90). The
   bank detail (Mass. Municipal Trust, State Street, First Safety, Worcester County National, Capitol, Worcester North,
   rates 5.25%-20.00%) needs the stacked-line splitter of item 5.
7. **A figure Textract put in NO cell.** p50 (general fund balance sheet, assets side, bottom): `Revenue Fiscal 1981
   6,086,900.72` is in the page lines (lines 67-68) and in no cell. Without it the assets read by cell sum to 1,925,859.70 against
   liabilities 8,012,760.42; with it they tie (1,925,859.70 + 6,086,900.72 = 8,012,760.42, hand-checked). A re-read of
   p50, not a reader rule.
8. **Trust fund roll-forward panels (p69-70) were printed side by side and Textract put most of them in no cell.** Cells
   hold: the summary (68/1), holdings by bank account (68/2-4, 69/1-2), the library interest and balance lines (70/1) and
   the school prize roll-forward (70/2). The cemetery, worthy poor and sidewalks-and-grounds roll-forwards (opening balance,
   bequests received with donor names, interest, grants, closing balance: cemetery `Balance July 1, 1979 78,623.72` ... `Balance
   June 30, 1980 82,699.67`; worthy poor `8,197.32` ... `8,647.74`) and the stabilization fund roll-forward (`21,693.56`
   ... `24,538.42`) are in the page LINES only. 70/2's first row `Balance June 30, 1980 24,538.42` belongs to the
   stabilization panel (map note). Needs a re-read by panel; the closing balances are already landed from the p68 summary.
9. **Row identity for the p38/1 recapitulation** (`gross amount to be raised - total offsets = net raised by taxation`):
   FY1981: 7,104,185.90 - 2,730,389.48 = 4,373,796.42 (checked by hand; the other five years tie too). The reader
   checks only items 6-11 against the total offsets.
