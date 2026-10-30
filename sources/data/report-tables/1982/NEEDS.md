# 1982 edition: what the shared code needs (for the integration pass)

Edition: calendar 1982 annual town report, `4504-1982-annual-town-report.pdf`, 168 pages. Tables were read
on the 61 pages `find_financial_pages.py --list 1982` picked; 46 of those carry a mapped table (pages.csv),
the rest are prose pages with dollar figures where the picked table is a text list or is not money (map.csv,
NOT LANDED). The folder reproduces under the shared script AS IT STANDS (`--check` ok). Items 1-3 below are
patches that would improve it; they were tried in a scratch copy of `read_report_tables.py` (not in the repo)
and the measured effect is quoted. Every hand check was computed from the cells
(`build/textract/out/4504-1982-annual-town-report.cells.tsv`) and lines, not typed from the page.

## FINDER MISSES: 0

Every page of the 168 NOT in the picked list was scanned in `lines.tsv` for money-shaped figures; the highest
count was 4 (p91, a school personnel listing with hire dates and hours, no money). A bound, not a proof.

## ROSTER PAGES

Not sent for tables, in `rosters.csv`: p20 `Roster of Firefighters for 1982`; p71-73 School Department
retirements; p74 resignations (name, position, period of service, replacement); p75-92 `School Personnel
Listing 1982-83` (name, education, hire date, position, FTE); p94-95 `School Enrollment` by classroom and teacher.
No FTE-by-role table exists apart from p101 (landed as `report-school-staff-fte`).

## 1. Shared-code patches, tried in a scratch copy (not applied)

**1a. `RECEIPTS_GRAND` must accept a colon.** `RECEIPTS_GRAND = re.compile(r'GRAND TOTAL|^TOTAL RECEIPTS$', re.I)`
-> `r'GRAND TOTAL|^TOTAL RECEIPTS:?$'`. The 1982 statement closes on `TOTAL RECEIPTS: $ 18,155,786.05` (p118 r41).
Unpatched, that row is summed as an account, so `annual-report-receipts` reads 173 rows `check failed`
(note: accounts sum 36,323,879.87 vs GRAND TOTAL not read). Patched: accounts sum 18,168,093.82 vs 18,155,786.05,
still `check failed` for the two reasons in item 4, which together account for the whole difference.

**1b. `CASH_INVESTED` must also match this page's marker.** `CASH_INVESTED = re.compile(r'CURRENT CASH INVESTED', re.I)`
-> `r'CURRENT CASH INVESTED|REVENUE CASH AND REVENUE CASH INVESTED'`. p113/1 holds the roll-forward AND the account
list in one table, split by the line `Revenue Cash and Revenue Cash Invested:` (row 13). Patched, with the map
sending p113/1 to `treasurers-cash` (as 2007 p73): 13 accounts sum to 1,304,327.30 = the unlabelled last figure =
the general ledger balance, and the roll-forward goes to `report-treasurers-cash-reconciliation` with all four
steps closing (net receipts 8,189,973.72; opening + net 9,797,291.92; net disbursed 8,492,964.62; ledger balance
1,304,327.30). Unpatched (the map as it stands sends p113/1 to `report-treasurers-cash-reconciliation`, family
`cash-reconciliation`): all 29 lines of the table land there, each `checked` by the same chain, and the account
lines are lines of the reconciliation rather than `treasurers-cash` rows. After applying 1b, change the map row
back to `treasurers-cash`.

**1c. A new IDENTITY for the 1982 accountant schedule (pp132-139).** Columns are `Approp. Forward | Total Funds
Available | Program Name | Amount Expended | Total Expended | Balance to Revenue | Balance to Fiscal 1983`. Add to
`IDENTITIES['accountant-schedule']`:

    ('BALANCE TO REVENUE', [(1, 'AVAILABLE'), (-1, 'TOTAL EXPENDED'), (-1, 'BALANCE TO FISCAL')],
     {'absent': ['ENCUMBERED'], 'blank_target': 'zero', 'needs': ['AVAILABLE']})

Unpatched: 0 of 270 schedule rows `checked` (all `no check`). Patched: 168 `checked`, 5 `check failed`, the rest
`no check`; the identity is the 1991 one with the 1982 column names. The 5 failures are rows to look at with the
image (cell witness), not typed: p134 `Purchase Police Cruiser` (a `5,366.00TF` transfer mark in the row), p135
`Plan Sewerage`, p136 `Private Ways 1982`, p136 `Veterans' Benefits` (Amount Expended 14,903.36 against Total
Expended 14,930.36 -- a transposition by the printer or by Textract, not established), p136 `School Department`.

Also needed for 1982 and already in the shared code: `accountant_marks` (`721.35RF`, `1,307.05TR`) -- set in
edition.json.

## 2. Reader behaviour that leaves rows `check failed`/`no check` (not patched)

**2a. A heading row that carries the previous section's subtotal.** p116 r11 prints `Licenses and Permits:` with
12,632.42 in the subtotal column: Textract put the subtotal of the trust-fund receipts (r3-r10: 420.48 + 2,175.00 +
2,591.86 + 7,250.00 + 130.00 + 15.08 + 50.00 = 12,632.42) on the heading line. `emit_receipts_span` lands it as an
account called `Licenses and Permits`, so the row is a DOUBLE COUNT of eight rows above it. It is landed (not
withheld: `withheld_rows` carries a privacy reason) and is `check failed` with the rest of the statement.

**2b. Three figures the page prints that Textract returned in no cell** (rule 13c: found by diffing money
figures in `lines.tsv` against `cells.tsv` per page; none typed into a row):
- p114: `143,932.60`, the subtotal of the federal aid-to-schools items (Public Law 874 ... Facilities Study Plan);
  the eight items sum to it.
- p115: `Meals Tax - School Lunch` **324.65**, a labelled account printed after the payroll deductions subtotal
  (1,372,870.67). This is an ACCOUNT with no cell, and it is exactly the shortfall: with 2a removed the accounts
  sum to 18,155,461.40, which is 324.65 under the printed 18,155,786.05.
- p116: `10,776.15`, the subtotal of the offsets to departmental expenditures (Advertising ... Cable T.V. Fees).
- p123: `172,602.77`, the footnote `*See also $172,602.77 departmental expenditures actually paid FY 1983`: prose.
Receipts therefore stay `check failed` until the missing account is read (a cell witness, or a re-read of p115).

**2c. The revenue sharing reconciliation (p129/1) fails its chain on wrapped labels.** The page prints `Less
Investments Transferred to Revenue / Sharing Cash Account` over two table rows, the figure on the second, and the
disbursement block likewise; the reader takes the unlabelled running subtotal (308,139.72) as the net receipts.
Every identity HOLDS ON THE PAGE, checked from the cells: 122,164.51 + (382,182.18 - 196,206.97 = 185,975.21) =
308,139.72; 382,182.18 - 185,975.21 = 196,206.97; 308,139.72 - 196,206.97 = 111,932.75 = the ledger balance. The
13 rows are `check failed` for reading, not for arithmetic. A wrapped-label rule in `emit_cash_reconciliation`
(a row with no kind, a label and one figure takes the next unfilled net slot) would settle it; not tried.

**2d. The voted budget (pp156-158) prints items in column 2 and `Total X:` in column 3.** The validator ties a total
only to a column of the same number, so every `Total Library:` / `Total Schools:` row is `check failed`
(`rows sum 0.00`, triage `grouping`) although each section ties in the cells: Total Highways 484,300.00,
Total Schools 3,894,306.00, Total Health 108,797.00, Total Veterans' Benefits 28,200.00 each equal the items
above them, and the 14 `check failed` rows of the dataset are all of this kind. The TOTAL BUDGET VOTED printed is
5,999,348.00 (p157 r32) and a map `stated_total` was NOT used: the list sums section totals as well as items
(12,468,072.20, a double count by construction). The page is two panels interleaved (157/1 and 157/2), so the
section `Total Library:` also sums items from the other panel. Proof by section needs the validator to tie a
labelled `Total` in the subtotal column to the item column, as `unlabeled_subtotals` does for unlabelled rows.

**2e. `unlabeled_subtotals_in`** is set in edition.json for `report-statement-of-payments`,
`report-fund-balance-sheets`, `report-trust-funds`, `report-revenue-sharing`, `report-school-appropriations`
(default is the accountant schedule only). Measured: trust funds 0 -> 8 checked, fund balance sheets 23 -> 25,
payments unchanged at 20 of 176 (a section's subtotal is checked only where it closes on the same table; the
sections run across pages). Hand check of p119-123 from the cells: every section subtotal equals the items above it.

**2f. Debt (p131/2): 4 `check failed`** on the `TOTAL:` / `GRAND TOTAL: PRINCIPAL` / `GRAND TOTAL: INTEREST` rows,
the stacked principal-and-interest layout of 1986 p47 (3 failures there too). p131/1 closes: Amount and Balance
tie to `TOTAL:` (1,542,000 and 465,000).

**2g. School staff (p101/1) is `checks=none`** in the map: its rows are different units (pupils, FTE by role,
dollars), and the column check read `NET TOTAL EXPENDITURES` as a total of the FTE rows (17 false failures).

## 3. CELLS MISSING / one-of-two printed sets (rule 13c)

- **p44 tuition rates: Textract returned one of the two printed sets.** The lines hold both `EFFECTIVE for period
  September 1, 1982 - December 31, 1982 ... KINDERGARTEN (1/2 X $2110.) $1,055 / ELEMENTARY 2,110. / MIDDLE 2,301. /
  HIGH 2,462.` and a second set; the cells are only the second (984 / 1,968 / 2,258 / 2,167 -- the 1981-82
  net cost per pupil of p101 item 5). The first set is in no cell and is not landed; no row is written from lines.
- p102: `In addition, the Town received during FY...` state aid to construction (32,600.00) and food services
  (39,371.79) print below the total and land as rows after it.

## 4. Privacy (TJ, 29 Oct 2026)

- Births: the book prints a Births, Marriages and Deaths record (text line 11659 of the extracted text), on pages not sent for tables (no money). No table was read there and nothing is landed; named births are not landed.
- **Withheld** (`edition.json` `withheld_rows`, as 1986): report-trust-funds p146/1 rows 9 and 11 (the two School
  Prize Fund grants of 75.00 to NAMED PUPILS -- minors receiving an award) and report-warrant-article-amounts
  p158/1 row 7 (a pension allowance voted to one named former employee, 2,439.20). Nothing else on those pages
  is touched, and the names are not repeated in this folder (grepped).
- **Landed, flagged for TJ's eye:** p143/2 `Bequests Received` -- 18 named donors to the cemetery perpetual care fund
  (75.00-250.00 each), the cemetery lot payments of the 1986 p51 kind; the library trust funds' donors (old
  charitable bequests, historic names) and the fund names Mabel L. Allen and Joseph A. Harwood (the School Prize
  funds, i.e. the DONORS, not recipients). No burials list is printed in the pages read.
- Elections (p156/1-2) land candidates' vote totals; candidates are public office-holders. The first half of the
  ballot (moderator, selectman, assessor, auditor) is on p155, not sent for tables.

## 5. What this edition prints that 2010 and 1986 did not

- A SCHOOL SUMMARY OF ACCOUNTS (p103, `report-school-appropriations`, NEW): FY-82 appropriation, FY-82 spent and the
  FY-83 request side by side by account series -- three stages in one table, never differenced (rule 1). Its
  FY-82 total prints `$ 3,531,167.*`; 13 rows `checked`.
- School receipts returned to the town (p102, `report-school-state-aid` family `school-state-aid-receipts`): FY-82
  ACTUAL and FY-83 ESTIMATED receipts in one table. The 1986 table of this dataset is a different family.
- Calendar-year reconciliation (p146/2) as in 1986 p53.
- The prose on p46 says the School Department budget fell from $4,138,975 to $3,506,167 (-15.3%) under Proposition
  2 1/2 and was then voted $3,793,599 (+8.4%); stated by the Superintendent, in prose, not landed.

## New dataset names used

None new beyond those settled by the 1986-1990 pass, EXCEPT `report-school-appropriations` (NEW, above). Reused:
`report-school-state-aid`, `report-school-staff-fte`, `report-school-special-accounts`, `report-statement-of-payments`,
`report-fund-balance-sheets`, `report-revenue-sharing`, `report-treasurers-cash-calendar-year`,
`report-treasurers-cash-reconciliation` (family `cash-reconciliation-revenue-sharing`), `annual-report-receipts`,
`report-warrant-article-amounts` (new family `special-articles-voted`), `report-trust-funds` (families
`trust-fund-bank-accounts`, `trust-fund-rollforward`), `report-fee-schedule` (`school-tuition-rates`).

## Integration pass, 30 October 2026: what was done with each item

- **Privacy:** TJ, 30 October 2026: *"Yes publish. Everything in the annual reports is public."* `withheld_rows` is removed from this folder's `edition.json`; the rows it held are published. (The reader's mechanism stays, unused, for a takedown.)
- 1a (`TOTAL RECEIPTS:`): APPLIED. Receipts stay `check failed` for 2a/2b, as measured here.
- 1b (`CASH_INVESTED`): APPLIED, and p113/1 is mapped to `treasurers-cash` (`stated_total` 1,304,327.30): 13 accounts published, the roll-forward 11 rows `checked`.
- 1c (accountant identity): APPLIED as the widened 1991 identity: 150 checked / 5 failed / 115 no check -- the same as the worker's own scratch copy (`w1982/p`) gives. The 168 written above was a miscount.
- 2a, 2b, 2d, 2f, 3: NOT APPLIED. 2a/2d are reclassifications of rows that would be chosen BECAUSE they make a total close; 2b and 3 are figures in no cell (a re-read, not a reader rule); 2f is the block walk's grouping.
- 2c (wrapped labels in the revenue sharing reconciliation): APPLIED, always on, with a second rule (a labelled line whose figure is printed on the row below). p129/1: 13 rows `checked`.
- Names: `report-school-appropriations` -> `report-school-budget-summary` (p103/1 `school-budget-summary`, p103/2 `net-budget-request`, p103/3 `budget-by-cost-kind`); `unlabeled_subtotals_in` follows the rename. p102 family -> `school-receipts-returned-to-town`.
