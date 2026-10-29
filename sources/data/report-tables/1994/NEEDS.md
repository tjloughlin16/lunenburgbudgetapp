# 1994 edition: what the integration pass needs to change

Written by the 1994 worker, 28-29 October 2026. Nothing here was changed in a shared file. PDF pages
throughout (printed folio = PDF page - 3: Bonded Indebtedness prints `62` on PDF p65). No NEW dataset
was needed: every financial table in this edition is a quantity an existing dataset already holds.

## 1. Special revenue: this edition's headers need their own row identity (p37-39)

The `special-revenue` identity looks for `FORWARD 7`, `RECEIPTS`, `DISBURSEMENTS`. 1994 heads the
columns `FORWARD | TOTAL REVENUE | TOTAL EXPENDED | BALANCE FY 95`, so no identity applies and all
69 rows are `no check`.

Change: add to `IDENTITIES['special-revenue']`
`('BALANCE FY', [(1, '^FORWARD'), (1, 'TOTAL REVENUE'), (-1, 'TOTAL EXPENDED')])`.
Tested on the raw cells before writing this: **69 of 69 rows close**, the unlabelled total row
included (p39 r46: 128,474.03 + 1,595,488.94 - 1,760,370.02 = -36,407.05, which is also the
balance sheet's special revenue `DESIGNATED ($36,407)`, p31).

Also: Textract carries the running title into the header (`JUNE 30, FORWARD`); the reader's
running-title rule did not strip it here.

## 2. Collection of taxes: identity without an ADJUSTMENTS column (p68)

`collection-of-taxes` requires `ADJUSTMENTS`; 1994 prints `TAX | FORWARD | COMMITMENTS | REFUNDS |
PAYMENTS | ABATEMENTS | TAX TITLE | BALANCES`, no adjustments. So `proof` is empty on all 26 rows.

Change: a second layout, `('BALANCES', [(1,'FORWARD'),(1,'COMMIT'),(1,'REFUNDS'),(1,'PAYMENTS'),
(1,'ABATEMENTS'),(1,'TAX TITLE')], {'absent': ['ADJUSTMENTS']})`. Tested: **26 of 26 rows foot**,
GRAND TOTAL included (payments, abatements and tax title are printed negative).

## 3. Treasurer's cash refused, though the accounts tie (p64 table 2)

`accounts sum 915,487.00, printed 389,750.00: not published (refused)`. Two causes:

- `SHAWMUT MONEY MARKET ($135,987.00) *` -- the trailing ` *` (a footnote mark; the note is not in
  the table) stops the parse, so the account drops out. Needs a parser mark in
  `validate_totals.REPAIRS`: strip a trailing ` *` after a figure.
- the last row is `| $389,750.00` (no label, one figure). `emit_treasurers_cash` counts it as an
  ACCOUNT (it has figures and is not `is_total`), and the lone-figure branch never runs because that
  row is not below the last account -- it IS the last account.

With both fixed: 13 positive accounts 525,737.00 less 135,987.00 = **389,750.00**, which is the
printed `GENERAL LEDGER BALANCE` (64/1 r5) and the lone figure (64/2 r15). The map already carries
`stated_total=389750`.

## 4. Omnibus budget: `incomplete` where it should be `open` (p42-43)

Rows read `col 3 at p43r48 reaches rows on a page not held`. The run does begin on p42 row 1 --
the line right above it is `THE BUDGET LINE ITEMS WERE DISCUSSED AND VOTED AS FOLLOWS:` -- so
`may_begin_earlier` is wrong here (header=none tables are presumably treated as continuations).

It would NOT close if it were checked, and that is the page's doing, not Textract's: the page image
(checked) PRINTS `136 INDEPENDENT AUDIT $9.50`, `146 TAX COLLECTOR'S ADMINISTRATION $49.73` and
`151 TAX COLLECTOR'S SALARY $9.54`. Lines sum 10,492,165.77 against `TOTAL BUDGET VOTED
$10,560,871.00`, off 68,705.23. Read as $9,500 / $49,73x / $9,54x the gap shrinks to a few dollars,
but that is a reading we would be supplying, not one the page prints: keep the printed figures and
let the rows be `check failed`. A way to say "the run starts at this table" in the map (e.g.
`header=none` plus a new `starts_run=yes`) would do it.

## 5. Bonds authorized and unissued tie, but are `no check` (p65 table 2, `groups:2`)

29 authorisations in two side-by-side lists sum to **2,352,975 exactly**, the printed `TOTAL
UNISSUED:` (and the map's `stated_total`). The validator checks per column of the group layout and
reports `no total printed` / `reaches rows on a page not held`. Change: for a `groups:N` table with
a `stated_total`, check the sum of every group's figures against it (as `emit_capital_plan` does).

## 6. Debt by issue: Textract mis-registered a rotated page (p65 table 1)

The page is printed landscape (rotated 90 degrees). Textract's cells merge two issues into one cell
(`$297,000 $152,000`, `$45,000 $10,000`) and shift later columns by a row, so 11 of 12 rows fail
`BALANCE = AMOUNT - TOTAL PAYMENTS PRINCIPAL`. The page image is clean and its own rows close
(e.g. ELEMENTARY SCHOOL REMODEL. 07/22/85: $330,000 - $297,000 = $33,000). The failures are the
reading. Only TOTAL closes (1,749,072 - 1,152,072 = 597,000). A re-read of this one page (rotated
before Textract) would fix it; not done here (no AWS calls).

## 7. Accountant schedule: the column totals are unlabelled (p36 r80)

The four pages' totals are printed on p36 row 80 with NO label: `$10719069.86 | $10719069.86 |
$10839922.60 | $164722.24 | ($285574.98)`. So rows without a printed BALANCE TO REVENUE are
`no check` (`no total printed`); 61 rows with one close their row identity. If an unlabelled last
row of a continued run were treated as a GRAND total, the column checks could run across p33-36.
The forward amounts print on their OWN row above the line they belong to, labelled `fwd` or `RFT`
(legend p36 r81-82: `fwd forward from FY 1993`, `Transfer`); they land as separate rows with one
figure, and they are inside the next line's TOTAL FUNDS AVAILABLE -- never sum them with it.

## 8. Trust funds: a 0.02 column miss fails 55 rows (p66-67)

`DIVIDENDS at p67r9 TOTAL COLONIAL: printed 8,166.58, rows sum 8,166.56 (off 0.02)`, and every row
in that block is `check failed` because of it. Not established whether Textract misread one digit
or the page's own total is off by two cents (triage: 45 one-digit corrections would close it); not
checked against the image. The other columns of the same block close. Below the COLONIAL block,
MMDT, STOCK and CENTURY close (9 rows checked, STABILIZATION 90,366.94 -> 91,193.23 among them).

## 9. Page subjects in pages.csv are the classifier's, and three are wrong

`map_annual_report_pages` assigned p32 (the receipts) `tax-collection`, p42 (the FY95 omnibus
budget) `trust-and-stabilization` (from Article 5's stabilization vote above the table) and p43
(the omnibus continued) `regional-school` (from the `MONTY TECH` budget line). Worth a look when the
subject vocabulary is next touched; nothing in this folder can set it.

## FINDER MISSES

**None.** Every page whose Textract lines hold 3+ money figures was picked
(`find_financial_pages.py --list 1994`: 27 pages, 0 unread). Checked per page from lines.tsv: no
unpicked page holds a money table (the most is p7, p14, p58 with two figures each, all in prose or
an election tally). PDF p69 has no text at all; the image is blank.

Picked pages that are NOT money tables: p4 (About the Town: a valuation and tax-rate total in
prose), p13 (Highway narrative, one paragraph per account), p18 (library narrative); and eight
picked pages returned no table at all because they are prose -- p10 (Council on Aging), p41 and
p44-p47, p49, p52 (town meeting warrant articles, each stating a sum).

## ROSTER PAGES

- **p21** `ROSTER OF FIREFIGHTERS FOR 1994` (Chief, Asst. Chief, officers, members; `*Denotes
  service on the Rescue Squad`). 2001 and 2010 put the fire roster in `report-officials`.
- **p30** `LHS SCHOOL COUNCIL` (members with role: Chair, Parent, Faculty, Community).

No school STAFF roster is printed in this edition: the school reports (p26-p30) are narrative;
searched for roster, staff, faculty, teacher and principal. The elected and appointed officials
lists (p5-p6) are officials, not staff rosters.

## What the integration pass did with each item (29 October 2026)

Applied ONCE in the shared code (see `sources/data/report-tables/README.md`, "Added by the 1991-2000 integration pass"); counts are this folder's rows after the re-run.

- **1 special revenue identity**: APPLIED. 69 of 69 checked.
- **2 collection of taxes without ADJUSTMENTS**: APPLIED.
- **3 treasurer's cash**: APPLIED (trailing ` *`; unlabelled last row is the total). 14 accounts = 389,750.00, published.
- **4 omnibus p42-43**: APPLIED (list totals, from the map's stated_total). 80 lines sum 10,492,165.77 against 10,560,871.00: all `check failed`, honestly -- the page prints `$9.50`, `$49.73`, `$9.54`.
- **5 bonds unissued, groups:2**: APPLIED (list totals). `checked`.
- **6 rotated debt page**: NOT APPLIED (needs a re-read; no AWS in this pass).
- **7 unlabelled accountant totals**: NOT APPLIED (validator block walk).
- **8 trust 0.02**: nothing to apply; stays `check failed`.
- **9 page subjects**: APPLIED (a page's subject follows the dataset it was landed in): p42, p43 `appropriations`. p32 (receipts) NOT -- no receipts subject exists.
- **ROSTER PAGES**: none -- no school staff roster is printed (the fire roster and the LHS council are not staff).
