# 1988 edition: what the shared code needs (for the integration pass)

Edition: calendar 1988 annual town report, `4487-1988-annual-town-report.pdf`, 84 pages. Tables were read on the 34 pages
`find_financial_pages.py --list 1988` picked; 25 of those returned at least one table (35 tables). The picked pages with NO
table are p14, p28, p49, p52-p55, p60 and p63: department prose and warrant-article prose with dollar figures in sentences.
Every hand check below was computed from the cells or the page image, not typed from the page.

## FINDER MISSES

None. Pages not sent that still print a `$` or a thousands figure (p8, p18, p19, p21, p24, p31, p48, p69, p75, p79) were read
in the page lines: one-line prose figures, the police offence counts (p18-p19, no money), the school enrollment table (p69, a
count table, out of scope) and the Town Clerk's narrative. No money table is on any of them.

## ROSTER PAGES

p76 (T. C. Passios Elementary School staff), p78 (Middle School staff), p80 and p81 (High School staff, continued). p77's
`STAFF` is a prose heading about retirements, not a roster. Listed in `rosters.csv`. p69 also prints the School Committee.

## 1. Emitters that refused or failed on a layout they have not met

### 1a. `annual-report-receipts` (p33): the emitter sums the wrong column. 104 rows `check failed`, all for a structural reason

The page prints two label|SUB TOTAL|TOTAL|GRAND TOTAL blocks side by side, plus a SUMMARY OF RECEIPTS and a GRAND TOTAL
$9,136,391.80. `emit_receipts` sums the first figure of every row (the SUB TOTAL) and takes the row whose LABEL contains
`GRAND TOTAL` -- here `OTHER FINANCING SOURCES GRAND TOTAL`, $340,125.00, a summary line -- so it reports `accounts sum
17,932,720.60 vs the printed GRAND TOTAL 340,125.00`. By hand from the cells (both blocks, summary rows excluded): the TOTAL
columns sum to **5,482,361.06 (left) + 3,654,030.74 (right) = 9,136,391.80**, the printed GRAND TOTAL, to the cent; the
GRAND TOTAL column sums to 5,460,751.06 + 3,675,640.74 = 9,136,391.80 as well, and the seven SUMMARY categories (5,377,603.52 +
83,147.54 + 128,498.33 + 3,048,975.86 + 57,844.81 + 100,196.74 + 340,125.00) sum to it. Change: take the GRAND TOTAL from a
cell under a `GRAND TOTAL` HEADER (the last row's last column), check the TOTAL column across both groups, and do not treat
the SUMMARY block as accounts. Rows with a SUB TOTAL and no TOTAL (e.g. `1985 MOTOR VEHICLE EXCISE`) take the SUB TOTAL as
their amount; an account whose TOTAL differs from its SUB TOTAL (`1987 REAL ESTATE TAXES ($2582.25)` into `1988 REAL ESTATE
TAXES $4717566.41 | $4714984.16`) is a group.
Cell misreads in the block, found only because the totals tie: `INTEREST 1985 M V E | 12.23` (no `$`) and `DEMANDS 1988 M V E
| 2040 | 6493` (whole dollars, no `$`).

### 1b. `report-treasurers-cash-reconciliation` (p32/1): 7 rows `check failed`, the layout prints a running subtotal

The page: balance June 30, 1987 $1,489,570.51; receipts $21,976,863.78 less investments transferred ($9,950,911.85) =
$12,025,951.93; then an unlabeled **$13,515,522.44 = opening + net receipts**; disbursed $21,915,962.24 less revenue cash
invested ($9,945,556.34) = $11,970,405.90; GENERAL LEDGER BALANCE $1,545,116.54, and the same $13,515,522.44 again beside it.
The emitter compares the unlabeled figure with net receipts alone and reports `off 1,489,570.51`. By hand: 1,489,570.51 +
12,025,951.93 = 13,515,522.44; 13,515,522.44 - 11,970,405.90 = 1,545,116.54, all tie. Change: a figure on a line with no label
that follows `LESS INVESTMENTS` is the running subtotal (opening + net receipts) and the second copy of it is its echo.

### 1c. `treasurers-cash` (p32/2): refused, 0 rows

Eleven accounts sum to 1,545,116.54 and the last row is `TREASURER'S CASH JUNE 30, 19` $1,545,116.54, the total (the cell
cuts the year off). `emit_treasurers_cash` does not recognise that label as a total, so it sums it as a twelfth account
(3,090,233.08 = 2 x 1,545,116.54) and refuses. The map's `stated_total` is set to 1545116.54 and the same refusal remains.
Change: treat a final row labelled `TREASURER'S CASH` as the total. The total ties to p32/1's GENERAL LEDGER BALANCE and to p10's
General Fund 95,840.56 + invested 1,449,275.98.

### 1d. `tax-collection` (p42): no row identity, `FORWARD` sits in the COMMITMENTS cell

The page prints no FORWARD column: a carried-forward amount is `$13,386.09` or `fwd` in the COMMITMENTS cell
(`$18,103.71 fwd $13,386.09`, rows 3-4: forward and commitment in one cell, one figure each). The reader takes the first as
the commitment. By hand, row identity FORWARD + COMMITMENTS + REFUNDS - PAYMENTS - ABATEMENTS - TAX TITLE = BALANCES closes on
the one row with no forward (`1988 REAL ESTATE`: 4,834,271.13 + 16,869.18 - 4,731,606.35 - 81,435.21 - 38,098.75 = 0.00).
GRAND TOTAL $5,756,212.86 / $21,588.06 / $5,386,786.01 / $130,104.36 / $38,189.50 / $222,721.05 are printed; the page prints
`$72,435.80 FORWARD / $5,683,777.06 COMMITTED` under them (72,435.80 + 5,683,777.06 = 5,756,212.86, the GRAND TOTAL
commitments). The rows are `no status` (the dataset has no status column) and the page is `unproven`.

## 2. New row identities and families

### 2a. `report-debt` family `debt-by-issue-principal-interest` (p40/1), a NEW layout, 74 report-debt rows `checked`

PAID PREVIOUS YEARS, DUE IN FISCAL 1989 and TOTAL PAYMENTS THRU 1989 each print PRINCIPAL and INTEREST. Identities, closed
by hand on all 11 issues and the TOTAL row ($1,228,543 amount; $410,423 + $174,460 = $584,883 principal; $643,660 balance):
BALANCE = AMOUNT - TOTAL PAYMENTS PRINCIPAL, and TOTAL PAYMENTS PRINCIPAL = PAID PREVIOUS + DUE principal; the same for interest
($176,222 + $60,958 = $237,180). The rows are `checked` by the column totals only.

### 2b. `trust-funds-summary` (p43/1): a cell holding two figures

Row 10 prints `WAKEFIELD SCHOLARSHIP | $22833.74 $281551.33`: the fund's balance and the page total in ONE cell. The reader reads
no figure for the row, so nine items sum to 258,717.59 against the printed 281,551.33 and all nine rows are `check failed`,
off by exactly 22,833.74 = the Wakefield balance. By hand: 258,717.59 + 22,833.74 = 281,551.33. Change: split a two-figure cell
whose second figure is the page's printed total (`raw_figures()` already does this for money cells; the trust-summary emitter
does not use it).

### 2c. `trust-accounts-by-bank` (p43/2, p43/3), a NEW family, 45 rows `no check`

Unlabeled subtotals after each group of bank accounts; none closes in the reader. By hand, all tie to the cent: Cemetery
perpetual care bequest 20,000.00 + 69,736.70 = 89,736.70; perpetual care income 6,017.79 + 8,021.72 = 14,039.51; headstone
account 100.00 + 198.13 = 298.13; 89,736.70 + 14,039.51 + 298.13 = 104,074.34 (the printed Cemetery total); Library books
bequests 8,900.00, books income 9,083.32, all-purpose bequests 6,200.00, all-purpose income 3,412.61: sum 27,595.93 (the
summary's LIBRARY); Worthy Poor 10,952.35 + 4,435.30 = 15,387.65; School Prize 582.28 + 564.76 = 1,147.04. The sidewalks and
grounds, stabilization and conservation blocks in the page's left column are in the page lines but Textract returned no cell
for them (only three tables on the page); queued as a line-level read.

### 2d. `report-auditor-cash-schedule` (NEW dataset, p10/1-3), 14 rows `checked`, 5 `no check`

The Auditor's schedule: General Fund and Revenue Sharing Fund cash at 7/1/87 and 6/30/88, and the composition of the
General Fund balance by bank. By hand: 500 + 500 + 101,044.56 + 3,010.00 - 9,214.00 = 95,840.56 (General Fund, 6/30/88);
the seven investment accounts sum to 1,449,275.98; 95,840.56 + 1,449,275.98 = 1,545,116.54 = p32's Treasurer's cash. The
opening 7/1/87 total (34,939.02 + 1,530,744.38 = 1,565,683.40) is NOT printed anywhere in the book.
Needs registering as a dataset with the generic `report-*` columns.

### 2e. Accountant schedule, p34-p38: no identity in the reader (as 1991 p25-29)

181 of 265 rows `no check`, 75 checked. By hand over the cells, TOTAL FUNDS AVAILABLE = AMOUNT EXPENDED + BALANCE REVENUE +
BALANCE FY 1989 closes on **154 of 164** single-line rows. The ten that do not are Textract misreads of the grid or the page,
not source errors: 34/6-7 (a wrapped label put `$20.00` and `$210.00` on the wrong rows), 35/40, 35/43-46 (a balance read into
two columns), 35/5, 36/28 (`P.L. 874`: 7,903.42 against 6,323.95 + 15,799.47) and 34/38 `Town Counsel Legal Expense`
(15,000.00 against 7,979.50 + 7,020.05 = 14,999.55, 45 cents; not checked against the image).

## 3. A discrepancy the town printed: the omnibus 400 series (p51)

**Observed on the page image** (p51 rendered from the PDF, not from the cells): `TOTAL 400 SERIES 699,200` printed under lines
that sum to **699,290** (442,750 + 20,000 + 75,000 + 37,400 + 8,800 + 88,470 + 4,900 + 21,970). The printed 100-900 series totals
sum to 9,072,176, but the printed TOTAL BUDGET VOTED is **9,072,266**, which is the sum of the LINES (9,072,176 + 90).
So the town's own grand total agrees with the lines and the 400-series subtotal is $90 short. Nine rows `check failed`.
That is a printed-page fact; the cause (a typo in the subtotal, or a line changed after it was typed) is not shown.

## 4. Textract cell merges that stopped a read

- **p44/1** NOT LANDED. A two-panel fund roll-forward in which Textract joined label, sub-label and amounts in shared cells
  (`Balance July 1, 1987 Income Perpetual Care: Fitchburg Savings | $2077.86 | $105340.90`). Page `refused`. The closing balances
  equal the p43/1 summary. A line-level read would land it as a roll-forward family in `report-trust-funds`.
- **p5/1** town facts: labels and values offset by a row (SETTLED / `1718`). Not landed in any year.

## 5. Page subjects

`pages.csv` classes p33 (the receipts) as `vital-records` by keyword (`MARRIAGE LICENSES`); the dataset landed there is
`annual-report-receipts`. Receipts have no subject in the vocabulary; left to the integration pass.

## 6. Out of scope and not landed

p5 (town facts, hours, meeting schedule), p12 (exemption clauses: landed, `report-property-tax-exemptions`), p56 (zoning
by-law text), p61-p62 (the Town Clerk fee schedule, landed as `report-fee-schedule` family `town-clerk-fees`; the CURRENT
fees the article replaces are not printed). p16 lists burials from March (names, age, cemetery), landed as
`report-vital-records` as 2010 and 2001 did; January and February are on p15, not sent for tables. Names of the deceased:
the redaction gate's call.

## 7. What this report prints that 2010 did not

A temporary-borrowing schedule (nine notes, $374,000, p40/2); the Treasurer's tax levy chart FY1982-FY1990 with percent
increases (p30); the Auditor's own cash schedule (p10); a trust fund schedule by custodian (p11); balances by bank account for
every trust fund (p43); bonded indebtedness with principal and interest paid and due (p40); a repayment schedule `AS OF
DECEMBER 31, 1988`.

## What was done with each item (integration pass, 29 October 2026)

- **Names.** `report-auditor-cash-schedule` -> `report-auditors-cash-schedule`; 10/2 was `cash-by-fund` but
  prints INVESTMENTS by fund, so `investments-by-fund`; 10/3 `investment-accounts` -> `investments-composition`
  (as 1986). `tax-levy-history` stays in `report-valuation` (1987 joined it). `temporary-borrowing` ->
  `debt-temporary-borrowing` (1989's name, same quantity).
- **1a receipts.** APPLIED as opt-in `receipts_span` with the SUMMARY under `SUMMARY:` and the GRAND TOTAL from
  the map's `stated_total`. The SUB TOTAL accounts sum to 9,136,453.80 against 9,136,391.80: off 62.00, which
  is `TOWN BY LAWS $62.00` (p33 r56), a SUB TOTAL that no TOTAL beside it carries -- every other group of SUB
  TOTALs equals its TOTAL. `check failed`; not adjusted.
- **1b running subtotal.** APPLIED as opt-in `recon_net_on_transfer_line`: 7 of 7 rows `checked`.
- **1c treasurer's cash.** APPLIED, always on: `TREASURER'S CASH JUNE 30, 19` is the list's total. 11 accounts
  published.
- **1d tax collection.** SKIPPED: splitting `$18,103.71 fwd $13,386.09` into a FORWARD the page prints no column
  for would be our layout, not the page's; `tax-collection` writes `proof` only from its own identity.
- **2b two figures in one cell.** APPLIED, always on, only where the second figure IS the map's
  `stated_total`: the nine trust summary rows `checked`.
- **2c trust accounts by bank.** Tried `unlabeled_subtotals` on report-trust-funds: no row moved. Left.
- **2e accountant schedule.** APPLIED: the identity BALANCE REVENUE = AVAILABLE - AMOUNT EXPENDED - BALANCE FY
  (no TOTAL EXPENDED column), always on (no earlier edition has the header). The rows the worker named as
  misreads fail it; the cell witness located none of them.
- **5 page subject.** SKIPPED: receipts have no subject in the vocabulary.
- **Privacy.** p16 named burials landed in `report-vital-records`, the 2010 / 2001 precedent, unchanged.
- **Rosters.** pp76, 78, 80, 81 dumped and read into `sources/data/rosters/1988-*.json`.
