# 1998 edition: what the integration pass needs to change

Written by the 1998 worker, 28-29 October 2026. Nothing here was changed in a shared file. PDF pages
throughout. No NEW dataset and no new family: everything 1998 prints mapped to a name that already
exists (`omnibus-amendment` is 2002's family; `trust-funds-book` and
`report-treasurers-cash-reconciliation` are the README's settled names).

## 1. School wage list: the GRADE column is read as a figure (p87-93) -- 375 rows `check failed`

`SCHOOL EMPLOYEES / REPORT OF WAGES PAID` prints `NAME | POSITION | GRADE | GROSS WAGES`. GRADE is
a pay lane or step (`M+75 MAX`, `B+15 MAX`, `6`, `3`, `M 2(.60)`). Where it is a bare integer it
parses, `figure_cols` (n >= 2) makes column 3 a figure column, and v1 becomes the GRADE (`6`) on
those rows; the wage moves to v2. The coverage check then compares v1 against the page's money
lines and fails EVERY row on the page (p87: 10 money figures not captured, 10 captured not in the
text -- the grades).

The figures themselves are right. Checked by me from cells.tsv, column 4 only, total rows excluded:

| run | rows | sum of GROSS WAGES | printed |
|---|---:|---:|---|
| school, p87-93 | 374 | 7,760,579.99 | p93: `TOTAL SCHOOL EMPLOYEES 374` / `TOTAL SCHOOL GROSS WAGES $ 7,760,579.99` |
| town, p94-96 | 153 | 2,171,450.71 | p96: `TOTAL TOWN EMPLOYEES 153` / `TOTAL TOWN GROSS WAGES $2,171,450.71` |

Both tie to the cent AND to the printed headcount.

Change (either): (a) the wage emitter and its coverage take the figure under the column whose
printed name matches `GROSS WAGES` (`by_name`), not v1; or (b) a map column `text` (`text:3`)
naming columns that are never figure columns, applied before `figure_cols`. (a) is the smaller
change and fixes it for every edition with a grade/step column.

## 2. Wage GRAND TOTAL: one per edition, and this edition prints two runs

`stated_total` for `report-gross-wages` is tied as `stated[-1]` against ALL wage rows of the
edition. 1998 prints a school run and a town run, each with its own total (table above), so I left
`stated_total` empty rather than give a total that is not printed (9,932,030.70 is our sum, not the
page's). Change: tie each `stated_total` to the rows from the previous stated-total page (exclusive)
through its own page, so p93 = 7,760,579.99 and p96 = 2,171,450.71. Then set those two in map.csv.

## 3. Treasurer's cash (p60 table 2): the unlabelled total is counted as an account -- refused

`emit_treasurers_cash` refused: `accounts sum 3,544,628.00, printed 1,772,314.00`. Row 18 has no
label and one figure, `$1,772,314.00`, in the SAME column as the 17 accounts (in 2001 it sat in a
column of its own). So it goes into `accts` and the lone-figure branch never fires (it requires the
lone row to be below every account). The 17 accounts sum to **1,772,314.00** (checked by me), which
the page prints twice: row 18 and `GENERAL LEDGER BALANCE $1,772,314.00` (table 1, row 4).

Change: in `emit_treasurers_cash`, an unlabelled LAST row with one figure is the total, not an
account, wherever its column. The map already carries `stated_total=1772314`.

## 4. Collection of taxes (p63): no ADJUSTMENTS column, so the row identity never applies

1998 prints `TAX | FORWARD | COMMITMENTS | REFUNDS | PAYMENTS | ABATEMENTS | TAX TITLE | BALANCES`.
The `collection-of-taxes` identity names ADJUSTMENTS, so it is skipped and `proof` is empty on all
30 rows. Add to IDENTITIES:

    ('BALANCES', [(1, 'FORWARD'), (1, 'COMMIT'), (1, 'REFUNDS'), (1, 'PAYMENTS'),
                  (1, 'ABATEMENTS'), (1, 'TAX TITLE')], {'absent': ['ADJUSTMENTS']}),

Tested by me on the emitted rows: **30 of 30 foot**, GRAND TOTAL included.

## 5. Budget amendment (p72): a printed row identity, not registered

STM May 9, 1998, Article 3: `Item # | Description | Additional | Current Appropriation | New
Appropriation`. NEW = ADDITIONAL + CURRENT closes on 4 of 4 lines (41,544 + 118,800 = 160,344;
-44,906 + 339,250 = 294,344; -2,321 + 108,000 = 105,679; 5,683 + 20,500 = 26,183). Add
`'omnibus-amendment': [('NEW APPROP', [(1, 'ADDITIONAL'), (1, 'CURRENT APPROP')])]`. 2002's p85
header (`Additional | Additional | May 4 Vote | NEW`) would not match it, so it is safe there.
map.csv has `checks=none` on 72/1 (no column totals are printed); rows are `no check` until then.

## 6. Valuation abstract (p41 table 3): an AVERAGE column is summed

The validator summed `Average Value` against the TOTALS row (printed 118,900; rows sum 1,866,200)
and failed all 14 rows, though Valuation (509,178,000) and Accounts (4,282) close at TOTALS. I set
`checks=none` on 41/3, so those rows are `no check`, which is honest but loses two real ties.
Change: leave a column whose printed name matches `AVERAGE|AVG` out of the column checks; then
drop `checks=none` from 41/3.

## 7. Page map subjects

- **p79** (Article 33, the FY1999 budget as voted, `TOTAL BUDGET VOTED $14,062,526`) is classed
  `regional-school` and given the Monty Tech `answers` text, presumably because line 310 reads
  `MONTY TECH $130,910`. It is the town's omnibus budget. The classifier in
  `map_annual_report_pages` needs to prefer `appropriations` here.
- **p44** (FY1998 receipts) is classed `tax-collection`; it is receipts.

## 8. Debt (p61, p62): what the failures are

- p61's printed heading is `DEBT REPAYMENT SCHEDULE AS OF JUNE 30, 1996`, but its columns start at
  FISCAL YEAR 1999 and it holds the 03/13/98 Municipal Purpose issue: the date as printed
  contradicts the contents. map.csv keeps period_fy 1998 and says it is our reading.
- p61 two cells Textract read at low confidence close their totals under a one-digit change:
  `$6,450` (62.3%, Street Betterment 91 interest FY2000; `6,480` closes both its issue total
  51,480 and GRAND TOTAL INTEREST 110,144) and `$415,880` (49.7%, TOTAL DEBT FY2000; principal
  306,736 + interest 110,144 = 416,880). Worth the glyph witness or a look at the pixels.
- p62 `TOTAL` AMOUNT is printed 2,875,830 but the six issues sum to 3,535,830: the 660,000
  issue of 03/13/98 is left out of the AMOUNT total while every other column's total includes it
  (PAID PREVIOUS PRINCIPAL 988,329 closes). A printed error on the page; triage calls it
  `grouping`.

## 9. Trust funds (p58): one cell

`RYAN BUSQUE` DIVIDENDS reads `$ 1` where its INT line prints `$ -`; TOTAL COLONIAL DIVIDENDS is off
by exactly 1.00 (17,961.05 printed, 17,962.05 summed). Probably a dash read as `1`.
BOOK BALANCE is off 0.01 at the same total.

## FINDER MISSES

**None found.** Every page with money figures in a table layout was sent. Checked: every page
with no cells and two or more money-like figures in lines.tsv -- p11, 12, 18, 19, 20, 70, 71, 74,
75, 76, 77, 78. p11, 12, 19, 70, 75-78 were in the finder's list (sent; Textract returned no table:
they are prose). p18 (septic and nursing COUNTS, two money figures in highway prose), p20 (library
prose), p71 and p74 (zoning by-law section numbers read as decimals) were not sent and hold no money
table. The pie charts on p45 (`GENERAL FUND REVENUES FY 98`) and p53 (`GENERAL FUND EXPENDITURES FY
98`) print percents only.

## ROSTER PAGES

- **p32** `SCHOOL STAFF` -- high school staff by department (principal, mathematics, physical
  education, ... nurse, alternative education), names only
- **p39** `TURKEY HILL MIDDLE SCHOOL STAFF 1998-1999` -- grades, resource center
- **p40** `TURKEY HILL MIDDLE SCHOOL STAFF 1998-1999` (cont.) -- special areas, reading tutor,
  cafeteria, custodians
- (p38: the Passios Elementary School Council members for 1998-1999, in prose)

None was sent for tables. Also note for the roster pass: the school WAGE list p87-93 names 374
school employees with POSITION and GRADE, and the town list p94-96 names 153 with POSITION and
DEPARTMENT; both are landed in `report-gross-wages`.

## What the integration pass did with each item (29 October 2026)

Applied ONCE in the shared code (see `sources/data/report-tables/README.md`, "Added by the 1991-2000 integration pass"); counts are this folder's rows after the re-run.

- **1 GRADE as a figure**: APPLIED. 529 of 529 wage rows `checked`.
- **2 one total per list**: APPLIED; `stated_total` set on p93 (7,760,579.99) and p96 (2,171,450.71); both tie.
- **3 treasurer's cash, unlabelled last row**: APPLIED. 17 accounts = 1,772,314.00, published.
- **4 taxes without ADJUSTMENTS**: APPLIED.
- **5 omnibus-amendment identity**: APPLIED; p72 4 of 4 `checked`.
- **6 AVERAGE column**: APPLIED; `checks=none` dropped from 41/3; report-valuation 9 -> 23 checked.
- **7 subjects**: p79 APPLIED (`appropriations`); p44 (receipts) NOT -- no receipts subject.
- **8, 9 debt and trust cells**: NOT APPLIED (no witness on these tables; they stay `check failed`).
- **ROSTER PAGES**: p32, p39, p40 read into `sources/data/rosters/1998-p*.json`.
