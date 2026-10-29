# 2000 edition: what the shared code needs (for the integration pass)

Written by the 2000 worker, 28-29 October 2026. Nothing below was applied: every item is a
change to a shared script or a decision for the integration pass. Tables were read on the
financial pages only (`find_financial_pages.py --list 2000`: 51 picked, cells on 39; the other
12 -- p13, 14, 15, 18, 19, 20, 104, 107, 108, 109, 112, 113 -- were SENT and Textract returned
no table; they are prose).

## 1. Wage pages: coverage must read the GROSS column, not v1 (p127-p134)

The school half of the payroll report prints `Employee | Position | Degree | Step | Gross`. A
STEP is a pay-grade label (`MAX`, `H`, `Student`, or an integer `1`-`12`); where it is an
integer the reader parses it as a figure, so the row has `v1=Step, v2=Gross` (column_meaning
says so on the six-column pages). `coverage()` compares only `v1` with the page's money lines,
so all 368 school rows are `check failed` although every gross figure is captured.

Tested in a scratch script (not in the shared code): taking the LAST figure of each row instead
of `v1`, all eight school pages close coverage exactly (p127 44 of 44 ... p134 49 of 49), and the
four town pages still close.

Change, either: (a) in `coverage()`, grade the figure in the column whose printed header is
`GROSS` (else the row's last figure); or (b) treat a column headed `Degree` or `Step` as text
(part of the label), like `id_columns` does for identifiers. (b) also stops a step being
summed as money by anyone who reads `v1`.

Related: p128, p130 and p133 have SEVEN columns (first | initial | last | ...) against p127's
six, so they are mapped `header=none` (column_meaning `not established`); borrowing p127's
header named the step `Gross`. A per-page header from the column count would recover them.

## 2. Wage pages: a printed SUBTOTAL for one block (p126)

p126 prints `Total Town $2,582,740.85` for the four town pages (p123-p126). The 172 town
employee rows sum to exactly 2,582,740.85 (scratch check). It is not set as `stated_total`
because `coverage()` sums EVERY wage row of the edition against the last stated total, and the
school pages (no printed total) would be added in. Change: let `stated_total` apply to the
pages that carry it (or to a page range named in the map).

## 3. Accountant's schedule: unlabelled department subtotals (p70-p76)

Same layout and the same failure as 2001 NEEDS #5 and 2002 NEEDS #3: each department's
subtotal prints on an unlabelled row (`| $80,573.00 | | $81,851.94 | $79,098.37 | | $2,753.57`),
so the validator sums lines AND subtotals under `GRAND TOTAL`: TOTAL EXPENDED printed
15,355,508.38, rows sum 27,534,317.07. That one open total is why 139 of the 281
accountant-schedule rows are `check failed` -- a reader failure, not bad figures.

## 4. Omnibus budget: table order across two pages (p105-p106)

Same as 2001 NEEDS #6. Four tables, two columns over two pages: 105/1 lines 1-3, 106/2 lines
4-49, 105/2 lines 50-54, 106/1 lines 55-86. `Subtotal Fire Dept. $444,686.00` (105/2) includes
lines 48-49 printed on 106/2 (290,000 + 13,800 = the 303,800 it is short), and `Total
Protection` / `Total Omnibus $15,801,974.00` (106/1) sum blocks in other tables. The three
amounts Article 4 voted (15,673,333.24 + 5,000 + 123,640.76) equal the printed Total Omnibus;
the map carries it as `stated_total`, which no emitter checks.

## 5. Trust funds SUMMARY OF FUNDS on p88: printed, not returned as a table

p88 prints `TOTAL TRUST ACCTS JUNE 30, 2000 / SUMMARY OF FUNDS`: sixteen purposes (CEMETERY
$244,559.73 ... STOCKS $978.48) to `GRAND TOTAL TRUST FUNDS: $882,808.73`. It is in the page's
lines (lines.tsv) but not in cells.tsv. 2001 landed its copy as `report-trust-funds`, family
`trust-funds-summary` (74/2). Not read from lines here (the brief says tables only). Needs a
lines reader or a decision.

## 6. FY2002 capital plan, item by item, in PROSE on p14

The Capital Planning Committee report (p14, a page sent for tables; Textract returned none)
prints twelve items with amounts in a sentence: `$85,000 for town-wide technology updates,
$19,000 for Lancaster Avenue guard rail replacement, ... $2,000 for file cabinets in the
Assessor's office`. They sum to 392,210, the printed `FY2002's bottom line figure is
$392,210.00`. That is `capital-plans` (per-item, proposed) and would close; no emitter reads
prose. Integration's call whether to land it.

## 7. Police offences list split across p26 and p27

p27/1 holds only the second half of the list; p26 (12 categories, sum 157 in the text) was not
sent for tables (no money on it). The printed `Total 616` covers both pages (157 + 459), so the
map sets `checks=none` on p27. Out of scope for this batch (non-money); noted so nobody reads
the p27 rows as the whole list.

## 8. Debt repayment schedule: `$` read as `8` (p89)

All 48 rows are `check failed`; triage settles many as `$` read as `8` (`83,263` -> `3,263`,
`8195,676`, `87,502`). The glyph witness runs on wage pages only; p89 is the same misreading
on a page with printed row and column totals. Change: run `witness_dollar_glyphs.py` on
repayment schedules too.

## FINDER MISSES

**None found.** Every page with three or more money figures in its text was picked. Pages
considered and rejected as misses:

- p69 `GENERAL FUND REVENUES FY 00` and p77 `GENERAL FUND EXPENDITURES FY 00`: pie charts that
  print PERCENT shares only (`PROPERTY TAXES 63.78%`, `Education 62.43%`), no money figure.
  Financial in subject, but there is no money table to read; the shares are derivable from
  p68 and p70-76.
- p24 (fire incidents), p31-32 (Nashoba health counts), p44 (enrollment): count tables, out of
  scope for this batch.

## ROSTER PAGES

Four school/staff roster pages, none sent for tables (no money), for `dump_roster_pages`:

- p43 `LUNENBURG PUBLIC SCHOOLS / SCHOOL COMMITTEE` and `Central Office Personnel` (central
  office, business office, facilities & grounds)
- p48 `FACULTY / ADMINISTRATION / ... CUSTODIAL STAFF` (Lunenburg High School: follows the
  high school report ending p47)
- p51 `FACULTY` (Turkey Hill Middle School: follows its report, p49-50)
- p53 `FACULTY` (Thomas C. Passios Elementary School, bottom of the page)

Not school: p25 `ROSTER OF FIREFIGHTERS` (2001 and 2010 put the fire roster in
`report-officials`); p7-p10 elected and appointed officials. Note also that the payroll report
(p127-p134) names every school employee with position, degree and step -- a roster with pay,
landed in `report-gross-wages`.

## What the integration pass did with each item (29 October 2026)

Applied ONCE in the shared code (see `sources/data/report-tables/README.md`, "Added by the 1991-2000 integration pass"); counts are this folder's rows after the re-run.

- **1 wages, GROSS not v1**: APPLIED (a column with no figure-shaped cell is label). 541 of 541 rows `checked`. The seven-column pages (p128, p130, p133) keep `header=none`.
- **2 the town subtotal on p126**: APPLIED (`stated_total` 2,582,740.85; one total per list). Families `gross-wages-town`, `gross-wages-school`.
- **3 unlabelled accountant subtotals**: NOT APPLIED (validator block walk).
- **4 omnibus table order**: APPLIED as a list total -- 86 lines = 15,801,974 = printed; 5 rows stay `check failed` on the validator's `Subtotal Fire Dept.` grouping.
- **5 summary of funds (p88), 6 capital plan in prose (p14)**: NOT APPLIED (no lines or prose reader).
- **7 police offences**: out of scope (non-money).
- **8 `$` read as `8` on p89**: NOT APPLIED -- the 48 rows are `check failed` against the page's own totals, a check with the power to fail; the glyph witness stays on wage lists.
- **ROSTER PAGES**: p43, p48, p51, p53 read into `sources/data/rosters/2000-p0*.json`. The catalogue also offered pp127-134 (the payroll report's name triggers the roster pattern): not rosters, not copied.
