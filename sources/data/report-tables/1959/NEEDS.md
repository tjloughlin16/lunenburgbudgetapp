# 1959 edition: what the shared code needs (for the integration pass)

Edition: calendar 1959 annual town report, `4550-1959-annual-town-report.pdf`, 116 pages. Tables were read on the 44
pages `find_financial_pages.py --list 1959` picked; 53 tables (map.csv). Opt-ins in edition.json: those of 1971 plus
`unlabeled_subtotals` and `rounding_tolerance_usd: 1`. `--check` reproduces. Hand checks below are computed from
`build/textract/out/4550-1959-annual-town-report.cells.tsv`. The report is a single volume with no names withheld
(`withheld_rows` is not used).

## FINDER MISSES

0. Every page with 3+ money figures in the text has cells or is prose: p41 (Tree Warden's saw, State liability
$1,802.51), p43 (Sealer's prose), p51-52 (Highway prose), p54, p79 (school building history), p60-63 (warrant article
text) hold money only in sentences. No money TABLE was found on a page with no cells.

## ROSTER PAGES

p5 Town Government (officers by name); p72 Jury List (name, residence); p80-81 School Department resignations and
appointments; p103-106 School Personnel 1959-60 (education, degree, years of experience, year appointed; no pay).
Written to `rosters.csv`. Not sent for tables: p108 school enrollment by grade and teacher (counts), p91 award recipients,
births/deaths/marriages (p68), burials.

## SHARED-CODE CHANGES THE EDITION NEEDS (none made here)

1. **Treasurer's cash, p18/1: the roll-forward and the account list are ONE table** (same as 1971 NEEDS item 1,
   `CASH_INVESTED` must match `Cash In Banks:`). Landed meanwhile as `report-treasurers-cash-reconciliation` (12 rows,
   `no check: the chain could not be followed`), because mapped to `treasurers-cash` the reader writes 0 rows
   (`accounts sum 4,940,980.35, printed 307,850.57: not published (refused)`, notes.csv). Same three chain limits as
   1971: an unlabelled running subtotal after Receipts ($1,646,993.45, printed twice, before and after the
   disbursements), no `LESS INVESTMENTS` line, and a closing line `Balance December 31, 1959 per cash book`. By hand,
   both printed identities close: 286,650.70 + 1,360,342.75 = 1,646,993.45; 1,646,993.45 - 1,339,142.88 = 307,850.57;
   and the three bank lines 287,684.38 + 10,000.00 + 10,166.19 = 307,850.57.

2. **Accountant's schedule (p26-36, `accountant-schedule`): the identity does not apply, 536 rows `no check`.** Same as
   1971 NEEDS item 2: the carry-forward column is `Balance to 1960`, not matched by `BALANCE (?:TO )?(?:FY|FISCAL)`;
   widen to `(?:FY|FISCAL|19\d\d)` (BALANCE TO REVENUE = TOTAL FUNDS AVAILABLE - TOTAL EXPENDED - BALANCE TO 1960).
   Computed by hand on the rows: **58 of 59 rows that print a Total Funds Available figure close** (within $1). The one
   that does not is `Painting Brooks' House 115.00` (p27): the balance 115.00 is merged into the label. The first
   figure column is headed `Approp. Forward` (one column; the words are stacked `Approp.` over `Forward`) and, as in
   1971, comes BEFORE the account name. 378 further rows are sub-lines with no Total Funds Available figure.

3. **Detailed statement of receipts (p18/2-p21): one subtotal printed one row low.** Same as 1971 NEEDS item 3. On p20
   the cell row `Treasurer: | | 93.50` (t1 row 41) carries the subtotal of the section ABOVE it, `General Government:`
   (Advertising 63.50 + Sale of Street Lists 10.00 + Sub-Division Notifications 20.00 = 93.50). The reader counts it as
   an account: `accounts sum 1,360,436.25 vs the printed GRAND TOTAL 1,360,342.75` (off exactly 93.50), so all 114 rows
   are `check failed`. Without that row the accounts sum to Total Receipts 1,360,342.75 to the cent. Total Receipts
   includes the `Temporary Loan` 50,000.00 (the revenue anticipation loan, a borrowing, not revenue).

4. **`tax-collection` (p25/2): labels and the balance column are lost.** Same as 1971 NEEDS item 4: `item` empty,
   the levy-year column read as figures; the committed and collected figures are read. Footnote marks `*` and `**`
   follow balances (1,234.20*, 13,032.97**); the 1958 motor vehicle excise row prints two lines (18,586.88 Fwd. and
   4,170.15).

5. **Detailed statement of payments (p22-25): a figure inside the label cell.** `Constructing, Improving, and Repairing
   Eastern | Ave. 8,756.72` (p23/1 row 11) has the figure in the label's tail (same as 1971 NEEDS item 6), so it is
   not read. By hand the Highways section is short by exactly that 8,756.72 (128,360.10 + 8,756.72 = 137,116.82, the
   printed subtotal); the other 14 unlabelled subtotals each equal their section's rows to the cent, and the 15
   subtotals sum to Total Payments 1,339,142.88 (the Disbursements line of the p18 reconciliation). All 136 rows are
   `no check` (`checks=none`: a list total outside the table).

6. **Voted budget (p58 t3-t4, p59 t1-t2): special articles share the tables with the budget, and `*20,000.00` is lost.**
   There is no way in map.csv to give rows 1-19 of p59/1 and p59/2 one family and rows 21+ another (the special articles
   by funding source, subtotals 100,000.00, 20,448.46 and 69,283.03, begin at `SPECIAL ARTICLES`). A row-range column
   in map.csv would do it (so would a break on a heading row). So all 99 p58-59 rows are `omnibus-budget`,
   `no stated_total`, `no check`. By hand: budget lines 958,966.64 + the Reserve Fund 20,000.00 (a cell `*20,000.00`
   whose leading `*` stops the figure; it is the overlay-surplus footnote mark) = 978,966.64, the printed `TOTAL BUDGET
   VOTED`, to the cent. The special-article lines are NOT budget (rule 1: a vote of money from other sources); one
   total for them is not printed in the cells.

7. **Welfare (p49/1): `cr 180.29*` is a CREDIT.** The Aid to Dependent Children net cost to the Town is a credit
   (reimbursements exceeded expenditure). The cell does not parse as negative, so the column total fails: printed
   6,576.88, rows sum 6,757.17 (off 180.29). With the credit negative it ties: 5,068.67 - 180.29 + 1,141.30 +
   547.20 = 6,576.88. A `cr` prefix = negative would close it (a CALENDAR_REPAIRS entry).

8. **School lunch (p111/1): `II` for 11.** The `No. Days` column prints `II` for June (Textract read the Roman numeral
   shape) and `18*` for September; the column foots to the printed 172 only with 11 (18+22+15+17+19+15+19+16+20+11).
   The column check fails and so, in the reader's reading, do the other columns of nine monthly rows (they close by
   hand: 126,016 = 14,404 + 16,747 + 11,588 + 13,376 + 14,158 + 10,869 + 13,030 + 11,057 + 13,889 + 6,898). The money
   table (p111/2) has a misplaced first row (September: `$ 2,000.00` and `Finance Com.` in the valuation column; the
   month's own figures on the next row, labelled blank) and no printed totals row for most columns it checks.

9. **General fund balance sheet (p16-17): no list-total mechanism for `report-fund-balance-sheets`.** 84 of 90 rows
   `no check`. By hand it ties on both sides: liabilities and reserves (4,867.64 + 20,320.18 + 59,989.06 + 12,356.09 +
   24,925.12 + 11,136.44 + 43,948.49 + 1,453.25 + 214,077.01) and assets (307,850.57 + 41,203.37 + 13,032.97 + 40.71 +
   1,609.63 + 1,068.32 + 28,196.86 + 70.85) are each 393,073.28, the printed total; the unexpended balances sum to
   their subtotal 59,989.06, receipts reserved to 12,356.09, revenue reserved to 43,948.49. Trust funds in custody
   (p17/4-5): 5,908.88 + 11,100.00 + 6,071.97 + 43,393.68 = 66,474.53; + 1,047.39 = 67,521.92.

10. **p15 (Analysis of Treasurer's receipts and payments): two pie charts, NOT LANDED.** The slices and percents are
    lines, not cells (and garbled: `10.3% SCHOOL & FEDERAL ... 45.9%`); three figures reached a cell and all three are
    printed again on p18 and p25. The page state is `refused`. A re-read of the page image would land the shares as a
    `report-expenditure-shares`-type dataset (percents of receipts and of payments by category).

## NEW dataset names (for the one-name-per-quantity table)

`report-welfare-cost` (p49: family `welfare-case-loads`, the Welfare Board's average case load, expended,
reimbursements and net cost to the Town by assistance program; a sibling of `report-veterans-services`);
`report-school-building-approved-costs` (p37/3: family `approved-costs-breakdown`, the costs the School Building
Assistance Commission approved for the Jr.-Sr. High School, on which the State reimbursed 50%; a cost base, not a
payment, never summed with `report-debt`). Reused: `report-town-facts` (as 1978), `report-dept-activity` (Town Clerk
counts, Dog Officer, Attendance Officer), `report-elections` (Annual Town Meeting 7 March 1959, one column, no
precincts), `report-vital-records` (totals only), `report-school-lunch`, `report-school-budget-summary`,
`report-school-state-aid`, `report-school-staff-fte`, `report-school-special-accounts` (the Chapter 658 athletic
account), `report-debt` (families `debt-by-issue`), `report-trust-funds`, `report-fund-balance-sheets`.

## What 1959 prints that 1971 did not

A balance sheet whose debt accounts are printed on both sides (`Net Funded or Fixed Debt` and `Serial Loans`, same
$1,235,000); the State's share of school building costs spelled out (p37 note: $40,648.16 a year for 15 years); the
Welfare Board's own cost table (p49); an Attendance Officer's table (p102); a printed Annual Town Meeting count of
ballots including a recount (p58, `Original Count Before Recount`, Howard A. Hamel 853, Eino O. Toko 853).

## Integration pass, 31 October 2026: what was done

Names and opt-ins are in `sources/data/report-tables/README.md` (1959-1970). Pages proven/unproven/refused:
15/15/1 as the worker left the folder -> 24/6/1. Renamed: `report-welfare-cost` -> `report-welfare-aid` (family `welfare-case-loads` kept).
Opt-ins set: `colon_heading_subtotals`, `cash_book_list`, `recon_no_transfers`, `dash_zero`, `accountant_marks_wide`, `accountant_marks_before`, `marks_wide`, `year_labels`, `statement_span`, `receipts_stop_at_grand`, `collector_columns`, `credit_marks`.
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
