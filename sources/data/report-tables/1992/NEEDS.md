# 1992 edition: what the shared code needs (for the integration pass)

Written by the 1992 worker, 28-29 October 2026. Nothing below was changed in shared code; every
item is a proposal with the pages it affects and the evidence that it is right. Counts were
computed by hand from `rows/*.csv` and the Textract cells, not by the reader.

## 1. Receipts printed as three tables: pool the accounts across a page's tables

`emit_receipts` sums the accounts of ONE map row against the GRAND TOTAL. Textract read p24's
three printed columns as three tables (t3 left, t1 middle, t2 right); only t2 holds the SUMMARY
OF RECEIPTS and `GRAND TOTAL $9,518,881.45`.

- The accounts of all three tables sum to 9,518,881.45 exactly (t3 6,824,372.99 + t1
  2,510,420.40 + t2 184,088.06, from notes.csv).
- As emitted: t2's 25 accounts are `check failed` (184,088.06 against 9,518,881.45) and t1/t3's
  92 are `no check`. The failure is FALSE: it is a total that covers the other two tables too.

Change: when several map rows on one page land in `annual-report-receipts`, sum their accounts
together against the one GRAND TOTAL (or accept `layout=tables:24/3,24/1,24/2`). With it, all
117 rows would be `checked` and p24 would be proven.

## 2. A third trust-fund layout: a row IDENTITY for `trust-funds-interest-ledger`

p37-40 print `TRUST ACCOUNT | ACCOUNT AND NUMBER | PRIOR YEAR BALANCE | PRIOR MONTH INTEREST |
CURRENT INTEREST | TRANSFERS TO & FROM | BEQUESTS RECEIPTS | GRANTS & GIFTS | BALANCE`. Neither the
2001-2005 book layout nor the 2006-2010 one. Proposed:

    'trust-funds-interest-ledger': [('^BALANCE$', [(1, 'PRIOR YEAR'), (1, 'PRIOR MONTH'),
        (1, 'CURRENT INTEREST'), (1, 'TRANSFERS'), (1, 'BEQUESTS'), (1, 'GRANTS')])],

Tested on the 1992 rows (blank = 0): **74 of 77 rows with a printed balance close.** The three
that do not:
- p38 SIDEWALKS & GROUNDS `INCOME #79900039` and its TOTALS row: both off by exactly $1.00
  (16,695.22 + 789.22 + 271.65 + 308.34 - 60.00 = 18,004.43; printed 18,005.43). The same $1 in
  the row and its subtotal: printed that way or misread identically twice; not settled here.
- p40 `TOTAL CONSERVATION`: the TRANSFERS figure `$1,048.87` landed in the LABEL
  (`TOTAL CONSERVATION $1,048.87`), so the row is short by exactly that. A label-building defect.
Two balances are unparsed (`$105.636.70` p37, `$29.340.54` p38: full stops for both separators).
The validator's column checks already mark 87 of 90 trust rows `checked` without this identity.

## 3. Special revenue headed TOTAL REVENUE / TOTAL EXPENDED

p29-30 head `FORWARD | TOTAL REVENUE | TOTAL EXPENDED | BALANCE FY 93`. The `special-revenue`
identity names `FORWARD 7`, `RECEIPTS`, `DISBURSEMENTS`, so it is not applied: 41 rows `no check`.
Proposed second entry:

    ('BALANCE', [(1, '^FORWARD$'), (1, 'TOTAL REVENUE'), (-1, 'TOTAL EXPENDED')]),

Tested: **41 of 41 rows close** (e.g. School Lunch -228.39 + 268,957.54 - 255,273.00 = 13,456.15).

## 4. Treasurer's reconciliation: `DISBURSE`, not `DISBURSED`

p32 prints `DISBURSE 7/1/91 - 6/30/92`. `RECON`'s `^DISBURSED` misses it, so the chain checks the
ledger balance through the printed net-disbursed subtotal and never uses the gross disbursement
(28,705,823). Change `('disbursed', r'^DISBURSED')` to `r'^DISBURSE'`. By hand every step closes:
28,705,823 - 12,043,649 = 16,662,174. Rows are `checked` today; this makes the check complete.

## 5. A printed total that covers several tables (stated_total for generic emitters)

Two places print one total over rows Textract split across tables or pages:
- p33 t2-t4, BONDS AUTHORIZED AND UNISSUED: 13 items sum to 649,830 = `TOTAL UNISSUED: $649.830`
  (t4). Rows are `no check` ("reaches rows on a page not held").
- p46-47, FY1993 omnibus budget: 80 lines (31 on p46, 49 on p47) sum to 9,453,667 = `OTAL | BUDGET VOTED | $9,453,667`
  (p47; the T lost at the margin, so the row is `kind=row`, not total).
Both totals are in map `stated_total`. Proposed: `emit_generic` checks the non-total rows of all
map rows sharing a `name` and `stated_total` against it (as `emit_capital_plan` does for one).

## 6. Collection of taxes: REFUND (singular), no ADJUSTMENTS column

p34 heads `TAX | FORWARD | COMMITTMENTS | REFUND | PAYMENTS | ABATEMENTS | TAX TITLE | BALANCES`.
- **Data loss, fix first:** `emit_tax_collection` matches `REFUNDS`, so the REFUND column is
  dropped; the nine rows with a refund land with `refunds` empty. Change the regex to `REFUNDS?`.
- The `collection-of-taxes` identity names ADJUSTMENTS, absent here, so it is not applied.
  Proposed second entry without it, refund singular:
  `('BALANCES', [(1,'FORWARD'),(1,'COMMIT'),(1,'REFUND'),(1,'PAYMENTS'),(1,'ABATEMENTS'),(1,'TAX TITLE')], {'absent': ['ADJUSTMENTS']})`.
  Tested from the cells: **25 of 25 rows close**.

## 7. Parser mark: a full stop for the thousands comma in a whole-dollar table

p33, p35, p36 (debt) print many whole-dollar figures with a full stop for the comma:
`$330.000`, `$132.000`, `$13.390`, `$6.153`, `$209.500`, `$649.830`. They parse as 330.000 etc.;
triage already says `misread settled -- a full stop read for a thousands comma` but the value
stays. Proposed REPAIR: in a column whose other figures are whole dollars, `$D{1,3}.DDD` (exactly
three digits after the stop, no cents anywhere in the column) reads as `D,DDD`. Also `S390`,
`S802` (p35) are unparsed: the `S`-for-`$` repair seems to require a comma.

## 8. `$8327.` is not read as a figure

p52 t2 (Special Town Meeting Nov 10, 1992, Article 5): `310 | Monty Tech Assessment | $8327.` --
no comma and a trailing full stop. The row lands with NO value (the whole text in the label).
REPAIRS lists "whole dollars ending in a full stop" (`$19,126.`), apparently only with a comma.

## 9. Headerless omnibus budget: the UMAS column becomes v1 on some rows only

p46-47 print no column headings: UMAS account number (printed on every p46 line, on only five of
p47's), line item, amount. The account number parses as a figure, so the AMOUNT is `v2` on p46
and `v1` on most of p47 -- the same quantity in two positions, both `not established`. Also
p47 r47-48 carry `14.2`, `14.3` in that column (misreads of account numbers). Proposed: a map
column `columns=UMAS No.|Line item|Voted FY 1993` naming a headerless table's columns, or treat a
numeric first column left of a text column as an identifier (README "identifiers") also when
it is not on every row.

## 10. Debt by issue: Textract shifted the last three columns one row down

p33 t1: `TOTAL PAYMENTS PRINCIPAL | ... INTEREST | BALANCE` for issue N are on row N+1, and
several cells hold two figures (`$27,693 $17,307`). p36: the TOTAL column (and 2000-2001 from
STREET BETTERMENTS 89 on) shifted one row down likewise. Rows are honestly `check failed` on
the figures as read. No code change proposed; a re-read of those two pages (by layout, rule 13b)
would recover them. Recorded so the failures are not mistaken for misprints.

## FINDER MISSES

**None found.** Every page whose text prints money in a table was sent for tables
(`find_financial_pages.py --list 1992`: 34 picked, 0 unread). Pages with money in the text but
no cells were checked by eye: p7, p14, p15, p17, p19 (department prose with one or two
figures), p45 (special town meeting articles), p57 (election), and p48-p51 (town meeting
articles: amounts in prose, `VOTED UNANIMOUSLY TO RAISE $13,330 BY BORROWING`) -- p48-p51
were in fact sent and returned no tables, correctly. No financial table was missed.

## ROSTER PAGES

2 pages, for `dump_roster_pages`:
- **p21** -- `SCHOOL STAFF` (lower part of the page): principals, assistant principals,
  administrative secretaries by school.
- **p22** -- the roster continued: teachers by grade (`GRADE 1` ... `GRADE 8`, `(1/2 time)`
  marks), guidance, special education, nurses, then the Principal's and Parent Advisory
  Councils.

Neither page was sent for tables. Not roster pages, noted to save a search: p4-p5 (town
officials, elected and appointed), p9 (fire department roster, which Textract DID read as a
table and which lands in `report-officials` as 2001's does), p18 (School Committee members).

## What the integration pass did with each item (29 October 2026)

Applied ONCE in the shared code (see `sources/data/report-tables/README.md`, "Added by the 1991-2000 integration pass"); counts are this folder's rows after the re-run.

- **1 receipts pooled across three tables**: APPLIED. 117 of 117 `checked` (were 25 failed / 92 no check).
- **2 trust ledger identity**: APPLIED under the ONE name `trust-investment-accounts` (this folder's `trust-funds-interest-ledger` renamed in map.csv; same layout as 1991 and 1993). 88 checked, 2 failed (the $1.00 SIDEWALKS & GROUNDS rows, as found). `$105.636.70`, `$29.340.54` now read.
- **3 special revenue TOTAL REVENUE / TOTAL EXPENDED**: APPLIED. 41 of 41 checked.
- **4 `DISBURSE`**: APPLIED (`^DISBURSE`); the reconciliation rows stay `checked`.
- **5 one total over several tables/pages**: APPLIED (list totals). Bonds unissued and the FY1993 omnibus (incl. the `OTAL | BUDGET VOTED` row) now `checked`.
- **6 REFUND (singular)**: APPLIED -- the data loss first: `emit_tax_collection` takes `REFUNDS?`, so the nine refunds are no longer dropped; the identity without ADJUSTMENTS applies.
- **7 full stop for a thousands comma; `S390`**: APPLIED per column (whole-dollar columns only).
- **8 `$8327.`**: APPLIED (a one-row table's `$` column is a figure column); p52 lands $8,327.
- **9 headerless omnibus, UMAS column**: PARTLY. Where the amounts print with a `$`, comma or cents the UMAS column is now an identifier (label); `14.2`, `14.3` read as sub-line numbers. Where both columns print bare integers nothing can tell them apart, and `column_meaning` still says `not established`.
- **10 debt rows shifted a row (p33, p36)**: NOT APPLIED -- needs a re-read by layout (no AWS in this pass).
- **ROSTER PAGES**: p21, p22 read into `sources/data/rosters/1992-p*.json`.
