# 1990 edition: what the shared code needs (for the integration pass)

Edition: calendar 1990 annual town report, `4489-1990-annual-town-report.pdf`, 76 pages. Tables were
read on the 30 pages `find_financial_pages.py --list 1990` picked; 32 tables on 29 of them are mapped
(p27 is Treasurer's prose and was not a table page). Every figure below was computed from the rows or
cells in this folder.

## FINDER MISSES: 0

No money table on a page with no cells. (p27 is picked? no: it is prose, not listed, no table.)

## ROSTER PAGES

p65 `T.C. Passios Elementary School Staff` (foot of the Elementary School Principal's report) and
p68 `MIDDLE SCHOOL STAFF`. No high school staff list is printed (p69-70 are the principal's prose).
In `rosters.csv`.

## 1. `treasurers-cash` publishes 0 rows: a footnote mark after a WHOLE-dollar negative (p28 table 2)

`SHAWMUT MONEY MARKET | ($280,016)*`. CALENDAR_REPAIRS 'trailing footnote mark' requires `\.\d{2}`
(cents), so the whole-dollar figure is not read as negative: the accounts sum to 281,505 against the
printed $1,489 and notes.csv refuses the table. With ($280,016) as a negative the twelve accounts
sum to exactly 1,489 (500 + 500 + 64,334 + 42,986 + 157 - 280,016 + 15,817 + 22,905 + 3,168 + 62,443 +
55,185 + 13,510). Change: let the pattern take `(?:\.\d{2})?`. Same family as 1991's repair.

## 2. omnibus budget p44-46: a full stop for the thousands comma, with no `$` (73 rows, all `check failed`)

Printed `54.587`, `41.672`, `15.890`, `8.572`, `30.000`, `683.845` in a column of whole dollars with
commas elsewhere (`107,870`). STOP_THOUSANDS wants a `$`. Read as 54,587 / 41,672 / 15,890 / 8,572 /
30,000 / 683,845 the 73 lines sum to the printed `TOTAL BUDGET VOTED` $9,609,362: the shortfall today
is $833,731.434 and the six corrections add $833,731.434 exactly. Change: apply the stop-for-comma
repair to a `\d{1,3}\.\d{3}` cell in a column whose other cells are whole dollars, `$` or not.

## 3. p52 omnibus-amendment layout (5 rows, `no check`)

Columns `FY1991 5/12/90 | FY1991 9/25/90 | ADJUSTMENT` (prior vote, new amount, difference). The
identity `ADJUSTMENT = new - prior` closes by hand on all five lines (e.g. Monty Tech 121,728 -
113,854 = 7,874; Solid Waste Committee prints no prior and 160 new, 160). The existing
`omnibus-amendment` identity is `Additional + vote = New` and does not match these headers. Add a
row identity for the prior/new/adjustment layout (a family of its own, as `stm-budget-adjustments`).

## 4. accountant schedule p24-p26: TOTAL FUNDS AVAILABLE read into the label cell

On most rows of pp24-26 Textract returns `$20000.00 Town Counsel Salary` as one label cell, so the
TOTAL FUNDS AVAILABLE figure is in the label and the v-columns shift left of p23's. 85 rows are
`no check` (no total is printed on pp24-26, as in 1991) and the p24-26 figures cannot be compared by
column with p23's. Change: split a leading `$figure` off a label in an accountant-schedule table into
the TOTAL FUNDS AVAILABLE column. Not done here (shared emitter).

## 5. receipts p22 are short of their own printed total: $980,467.00 (125 rows `check failed`)

The 125 lines sum to $7,193,802.84; the printed GRAND TOTAL is $8,174,269.84; the SUMMARY OF RECEIPTS
categories on the same page sum to $8,174,269.84 (notes.csv). The page ends at `STATE REVENUE:
ABATEMENTS ELDERLY $34,710.00` while the summary prints STATE REVENUE $1,555,317.75: the receipt lines
under STATE REVENUE are not in the scan (the page number at the foot is 20; the next PDF page is
printed 21). Not a reader defect: registered as a gap in gaps.csv. The nine summary categories are
rows of the same dataset (groups:3), so they tie to the printed total on their own.

## 6. debt repayment schedule p30-p31: a displaced column, and two arithmetic misses

`layout=spans:1-11` leaves out the right-hand TOTAL column on both pages: Textract returns each issue
total one row off (`$14280` beside INTEREST, `$1000` beside TOTAL 1985 BETTERMENTS). With it dropped
84 of 93 rows are `checked`. The 9 left:
- p30 VOTING MACHINES 1991: PRINCIPAL $4500 + INTEREST $266 = $4,766, printed `TOTAL VOTING MACHINES:
  $6766`. Both Textract outputs read `$6766`; p29 gives the same $4,500 and $266 for that issue; the
  displaced TOTAL column on the right reads `$4766`. A misread or a printed error: not established
  without the page image.
- p31 STREET BETTERMENTS 89, 1999-2000 and the GRAND TOTAL rows under them: the 2000 column is
  displaced one row as well (principal $25000 on the heading row, $988 interest on the PRINCIPAL row).
  The GRAND TOTAL PRINCIPAL / INTEREST / TOTAL DEBT rows (p31 r31-r33) fail for 1991-1993 and 1999-2000:
  the reader sums the issues of this page only, the first 1993 TOTAL DEBT misses by exactly $20,000, and
  the cause (a single digit, a displaced cell, or the totals spanning p30 and p31) was not established.
An integration option: a `drop displaced column` support in the reader instead of `spans`.

## 7. What 1990 prints that 2010 did not (new, or changed layout)

Nothing new at dataset level; the same layouts as 1991 (accountant schedule with `BALANCE FY 91`,
trust-investment-accounts ledger, debt by issue and repayment schedule, collection of taxes without
ADJUSTMENTS, omnibus budget and a special town meeting adjustment). 1990 prints no Treasurer's
then-and-now table (p27 is prose) and no tax-bill-breakdown.

## What was done with each item (integration pass, 29 October 2026)

- **1 footnote on a whole-dollar negative.** APPLIED, always on: `($280,016)*` reads; the twelve accounts
  sum to the stated $1,489 and are published.
- **2 `54.587`.** APPLIED as opt-in `stop_for_comma_without_dollar`: the omnibus budget closes on TOTAL
  BUDGET VOTED $9,609,362.
- **3 ADJUSTMENT = new - prior.** APPLIED, always on: an `omnibus-amendment` identity by column position
  (the headings are dates). 5 of 5 rows `checked`.
- **4 split a leading `$figure` off the label.** SKIPPED, as 1989 item 4.
- **5 receipts.** Read by `receipts_span`; still 980,467.00 short of the GRAND TOTAL because the STATE REVENUE
  lines are not in the scan (registered in gaps.csv). `check failed`, correctly.
- **6 debt.** SKIPPED: `spans:1-11` already drops the displaced column; the misses left need the image.
- **Rosters.** pp65, 68 dumped and read into `sources/data/rosters/1990-*.json`.
