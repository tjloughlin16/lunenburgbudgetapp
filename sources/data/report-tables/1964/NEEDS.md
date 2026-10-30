# 1964 edition: what the shared code needs (for the integration pass)

Edition: calendar 1964 annual town report, `4507-1964-annual-town-report.pdf`, 124 pages. Tables were read on the 56 pages
`find_financial_pages.py --list 1964` picked; 84 tables (map.csv), 39 landed pages (pages.csv). Opt-ins in edition.json are
the 1971-1980 set (`accountant_marks`, `stop_for_comma_without_dollar`, `id_column_words`, `recon_net_on_transfer_line`,
`stacked_pairs`, `receipts_span`, `unlabeled_subtotals`, `rounding_tolerance_usd: 1`) copied from 1971. Hand checks were
computed from `build/textract/out/4507-1964-annual-town-report.cells.tsv`.

## FINDER MISSES: 0

p14 (`Where Did Your 1964 Tax Dollar Go?`, the tax dollar as cents per service) has no cells and no dollar figures, so it is
the percent-chart case, not a miss. Its large slices and p15's large slices exist as page lines only (see gaps.csv, last row).

## ROSTER PAGES

p5-7, 10-12 (town officials and committees), p42-44, 48, 50, 56, 58, 60 (department heads and staff), p100-103 (school
resignations and appointments; p103/1 is mapped NOT LANDED), p109-110 (class officers, scholarship recipients), p111-117
(school personnel with subject, years, year appointed in Lunenburg; no pay printed). Written to `rosters.csv`. Not sent for
tables. p4/2-4 (committees) and p62/1-2 (election returns) were sent and landed as `report-officials` and `report-elections`.

## PRIVACY

No `withheld_rows`. Burials (p47/3-4, `report-vital-records` family `cemetery-burials`), election candidates, trust fund donors
and prize grant recipients all landed (TJ, 30 Oct 2026: everything in the annual reports is public).

## SHARED-CODE CHANGES THE EDITION NEEDS (none made here)

1. **Receipts read `check failed` (p18/2-p21/1).** Same as 1971 NEEDS item 3 / 1975 NEEDS item 2: section subtotals sit on the
   row of the NEXT heading (`Motor Vehicle and Trailer Excise: | | 53,295.78`, `Commonwealth of Massachusetts: | | 70,560.19`,
   `County: | | 387,523.01`), so the span emitter counts them as accounts (2,916,137.38 vs the printed 2,407,958.34). By hand the
   figures in the third (subtotal) column of p18/2-p21/1, excluding the Total Receipts row, sum to 2,407,958.34 to the cent.
2. **Payments `no check` (p22-p25).** `checks=none` per 1971. By hand the third-column figures of p22/1-p25/1, excluding the
   Total Payments row, sum to 2,415,745.82, the printed Total Payments, to the cent. Both totals equal the Receipts and
   Disbursements lines of the p18/1 reconciliation.
3. **Reconciliation of Treasurer's cash (p18/1): the chain check fails on the instrument, not the figures.** Mapped to
   `report-treasurers-cash-reconciliation` as 1973 does (as `treasurers-cash` the emitter refused: accounts 7,628,599.35 vs 127,120.63,
   it read the roll-forward as accounts). The 13 rows read `check failed` (`general ledger balance 127,120.63 != 134,908.11 (off
   -7,787.48)`): the emitter took the opening balance as the ledger balance because it did not take the page's `Receipts` and
   `Disbursements` lines (each label carries the date range) and does not know `Cash Balance December 31, 1964` as the closing line;
   -7,787.48 is exactly receipts less disbursed. By hand: 134,908.11 + 2,407,958.34 = 2,542,866.45 (printed in the third column,
   twice); less 2,415,745.82 = 127,120.63 = `Balance December 31, 1964 per cash book` = 115,986.01 + 10,000.00 + 1,134.62. Change:
   RECON `ledger` also matches `^CASH BALANCE`, and `receipts`/`disbursed` bind the figure in the SECOND cell of the row.
4. **Accountant's schedule (p26-37): 136 rows `checked` (11 pages proven), 384 `no check`, 1 `check failed`.** The failure is p28 `Purchase
   of Fire Hose` (`8.64 Fwd | 8.64 | ... | 8.64 | ED 8.64`): the `ED` mark before Total Expended is not an accepted accountant mark, so
   Total Expended is read blank and Balance to Revenue (blank) != 8.64. Change: add `ED` to the `accountant_marks` set. The `no check`
   rows are the lines that print an amount in one column only (itemised sub-lines of an account, as 1971). Hand check on col 2 and col 5
   (Total Funds Available, Total Expended): 108 of 126 rows satisfy Total Funds = Total Expended + Balance to Revenue + Balance to 1965;
   the other 18 are off by cents to dollars (5,792.50 vs 5,792.45; 12,304.00 vs 12,303.22; 26,950.00 vs 26,949.82), which is a balance
   printed on a neighbouring row or in a cell not read; no cause is tested.
5. **Voted budget `check failed` by $0.50 (p62/3-p63/2).** 75 item rows sum to 1,327,407.96, the printed TOTAL BUDGET VOTED is
   1,327,408.46. Not located: one cell is probably misread by a fraction, and the stated-list-total check has no rounding
   tolerance (`stated_list_totals` ignores `rounding_tolerance_usd`; $0.50 is within it). The right-hand panel of p63 (`Transfers
   from:` overlay, article balances, `$31,439.63`, page lines 63/80-185) reached NO cell; it is a money list on a sent page and is
   not landed (compare 1971's `omnibus-funding-sources`). Needs a re-read of that panel.
6. **Debt p38/1: a one-issue group repeats its issue as the unlabelled subtotal.** The 1961 addition (`4-1-61 $150,000 ...`) is one
   issue, and the line under it (`$96,000 $4,524.00 ...`) repeats it; the subtotal rule does not drop it because the AMOUNT
   column of that row is blank, so Paid Previous Principal reads 1,492,000 vs the printed Grand Totals 1,396,000 (off the 96,000)
   and Balance 642,000 vs 606,000 (off 36,000). By hand: 710,000 + 590,000 + 96,000 = 1,396,000 and 140,000 + 430,000 + 36,000 =
   606,000. Change: a subtotal row equal to the single detail line above it is a subtotal even when the first column is blank.
7. **School lunch counts p121/1: Adult Lunches total off by 50.** The 10 months sum to 8,914 and the TOTALS row prints 8,864. The
   other columns of the row tie (182,711; 3,831; 157,904; 4,878). Not established whether the printed total or a monthly cell is
   wrong (misread of a cell vs a printed addition error): a better look at the p121 image is the check.
8. **Same-as-1975 limits that apply here:** p16/1-2 and p17/1 are single-statement balance sheets, read per section with `checks=none`
   (the 447,013.19 total is printed on both sides); p40/1 (eight Textract columns, two side-by-side trust groups) lands with no check.
9. **Finding aid, not a reader change:** the p16 balance sheet title prints `December 31, 1965` while every line is 1964. Quoted as
   printed in the period.
