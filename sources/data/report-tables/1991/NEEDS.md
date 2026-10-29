# 1991 edition: what the shared code needs (for the integration pass)

Edition: calendar 1991 annual town report, `4490-1991-annual-town-report.pdf`, 68 pages. Tables
were read on the 33 pages `find_financial_pages.py --list 1991` picked; 26 of those returned at
least one table (35 tables). The seven picked pages that returned NO table -- p10, p11, p13,
p18, p20, p45, p48 -- are department prose and warrant-article prose with dollar figures in the
sentences; they were sent and Textract found no table on them.

Every hand check below was computed from the rows this folder writes (or the cells), not typed
from the page.

## 1. New row IDENTITIES (validate on the rows before adding, as for 2006/2007/2009)

### 1a. `trust-investment-accounts` (NEW family in report-trust-funds), p36-p39

Printed header: `TRUST ACCOUNT | ACCOUNT AND NUMBER | PRIOR YEAR BALANCE | PRIOR MONTH INTEREST |
CURRENT INTEREST | TRANSFERS TO & FROM | BEQUESTS RECEIPTS | GRANTS & GIFTS | BALANCE`.
Negatives are printed in parentheses, so every term is ADDED:

    ('BALANCE', [(1, 'PRIOR YEAR BALANCE'), (1, 'PRIOR MONTH INTEREST'), (1, 'CURRENT INTEREST'),
                 (1, 'TRANSFERS'), (1, 'BEQUESTS'), (1, 'GRANTS')])

Closes on **78 of 79** rows that print a BALANCE (TOTALS rows included). The one miss is
IRVING KIMBALL (p39 r9), whose transfer cell reads `($1.76).` and does not parse -- see 3b.
It is a THIRD trust layout, neither 2001-2005 `trust-funds-book` nor 2006-2010 `trust-funds`;
the target regex `^BALANCE$` must not catch `PRIOR YEAR BALANCE`. On p37 Textract merged the
first two header cells (`TRUST ACCOUNT ACCOUNT AND NUMBER`), so the table has 8 columns there.

### 1b. `collection-of-taxes` without an ADJUSTMENTS column, p35

1991 prints `TAX | FORWARD | COMMITMENTS | REFUNDS | PAYMENTS | ABATEMENTS | TAX TITLE | BALANCES`
-- no ADJUSTMENTS. The existing identity names ADJUSTMENTS, so it is not applied and every
`tax-collection` row has an empty `proof`. A variant with `{'absent': ['ADJUSTMENTS']}` and the
same other terms closes on **21 of 21** rows (payments, abatements and tax title printed negative).

### 1c. `accountant-schedule`, 1991 layout, p26-p29

1991 prints `APPROPRIATED FORWARD | TOTAL FUNDS AVAILABLE | PROGRAM NAME | AMOUNT EXPENDED |
TOTAL EXPENDED | BALANCE REVENUE | BALANCE FY 92` -- no ENCUMBERED, and the balance split
between revenue (closed out) and forward. The 2001-2010 identity names ENCUMBERED, so it is not
applied. By hand, TOTAL FUNDS AVAILABLE - TOTAL EXPENDED - BALANCE REVENUE - BALANCE FY 92 = 0
closes on **78 of 78** rows that print an AVAILABLE figure, with blanks as zero. A proposal:

    ('BALANCE REVENUE', [(1, 'AVAILABLE'), (-1, 'TOTAL EXPENDED'), (-1, 'BALANCE FY')],
     {'absent': ['ENCUMBERED']})

with the target and BALANCE FY read as zero when blank. The README records that blank-as-zero
was REFUSED on 2010 because it failed in offsetting pairs; here it holds line by line, but it
should be enabled only for this layout (`absent: ENCUMBERED`). p25 cannot take it: Textract
merged TOTAL FUNDS AVAILABLE into the program-name cell (`$73887.00 Selectmen's
Administration`), so the available figure is in `label`.

### 1d. `omnibus-amendment`, p51

`Item # | Description | Additional | May 11 Vote | New Approp`: Additional + May 11 Vote = New
Approp closes on 3 of 3 lines (50,500 + 282,942 = 333,442; 27,358 + 78,188 = 105,546;
7,500 + 116,000 = 123,500). Header words differ from 2002's (`May 4 Vote`, `NEW`):
`('NEW', [(1, 'ADDITIONAL'), (1, 'MAY \\d+ VOTE')])` would cover both, but 2002's line 4 does
not close (its own NEEDS).

## 2. Validator / emitters

### 2a. A subtotal that covers a SECTION, across two columns -- p27 `Total Highway`

`Total Highway` (p27 r23) subtotals only the HIGHWAYS block (r18-r22), and the block's figures sit
in DIFFERENT columns from the subtotal: APPROPRIATED FORWARD 218,377 + 6,000 RF + 137,400 +
11,000 + 119,191 = 491,968, printed under TOTAL FUNDS AVAILABLE; AMOUNT EXPENDED 212,671.33 +
145,233.04 + 9,868.40 + 118,870.62 = 486,643.39, printed under TOTAL EXPENDED. Both tie by hand.
The validator summed every row back to the top of p26 and failed 42 correct rows ("grouping, the
block summed is the wrong one"). **map.csv sets `checks=none` on p26 and p27** so those rows are
`no check`, not a false `check failed`. What would let the check run: start a subtotal's block
at the nearest section heading above it (`HIGHWAYS`, a row with a label and no figures), and
allow a subtotal to foot a sibling column when its own column is blank in the block.

### 2b. Receipts split into two tables on one page -- p24

Textract returned p24's three label|amount columns as 24/2 (left) and 24/1 (centre and right,
`groups:2`). `emit_receipts` checks each TABLE against the GRAND TOTAL, so 24/1's 79 accounts
are `check failed` against 9,532,917.83 and 24/2's 44 are `no check` (no total in that table).
It should pool the tables of one page. **Pooling would not make it pass**: 24/1 + 24/2 accounts
sum to 9,650,522.83, 117,605.00 more than GRAND TOTAL. The page prints SCHOOL TRANSPORTATION
$121,543.00 twice (24/1 rows 1 and 3; the page lines carry it twice too). That is a candidate
explanation, not a finding: dropping one copy leaves the accounts 3,938.00 SHORT. What does tie:
the TAXES & EXCISES category, 6,533,682.04, equals 24/2 rows 2-33, and the SUMMARY OF RECEIPTS
categories sum to the GRAND TOTAL.

### 2c. Treasurer's cash refused for a parser reason -- p31/2

`treasurers-cash` wrote 0 rows: "accounts sum 6,149,144.00, printed 3,012,213.00: refused".
Two causes: (1) SHAWMUT MONEY MARKET prints `($124,718.00 )*` -- a space before the closing
parenthesis and a trailing asterisk -- and does not parse (3a); (2) the unlabelled lone figure
under the list (r15, 3,012,213.00) was summed as an account. Read as -124,718.00, the 14
accounts sum to exactly **3,012,213.00**, which is both the lone figure and the reconciliation's
GENERAL LEDGER BALANCE (31/1 r7). Fix 3a and check that the lone-figure branch fires.

### 2d. Debt repayment schedule, 2001 column -- p34 (3 rows `check failed` on correct figures)

Only STREET BETTERMENT 91 pays in fiscal 2001, and its principal row is labelled
`STREET BETTERMENT 91 PRINCIPAL`. The validator summed 48,263 into GRAND TOTAL PRINCIPAL 2001
(printed 45,000) and 0 into GRAND TOTAL INTEREST (printed 3,263). By hand 45,000 + 3,263 =
48,263 = TOTAL STREET BETTERMENT 2001 and both grand totals tie. Same shape as 2001's note that
an issue name prints on a PRINCIPAL row. Left as `check failed` (not hidden by `checks=none`,
which would discard the 91 rows that check).

### 2e. Omnibus `stated_total` has no emitter -- p46-p47

As in 2001: TOTAL BUDGET VOTED 9,594,034 is in `stated_total`, nothing checks it. The lines as
read sum to 9,594,459, **425 more**. `DUTCH ELM 097` (46/1 r41) is printed so; nothing here
says which line is off.

## 3. Parser marks (validate_totals.REPAIRS)

- 3a. `($124,718.00 )*` (p31/2 r6): space before `)` and a trailing `*` (the asterisk's meaning
  is not printed on the page).
- 3b. `($1.76).` (p39/1 r9): a parenthesised negative followed by a full stop.

## 4. New datasets (register in the merge with the generic `report-*` columns)

| dataset | family | pages | what it is |
|---|---|---|---|
| `report-property-tax-exemptions` | `exemption-clauses` | p8/2, p9/1 | the Assessors' summary of exemptions available by statutory clause (17D, 22, 22E, 37A, 41A, 41C, 42, 43; c.61, 61A, 61B) with the exemption amount in prose. A rule, not money granted. No figure parses: the amounts are in `label` |
| `report-treasurers-then-and-now` | `then-and-now` | p30/1 | the Treasurer's comparison of the office's workload thirty years earlier against now: population, persons assessed, MVE bills, persons on payroll, total receipts, total disbursements, building permits. Mixed units, one statistic per row; NOW receipts/disbursements equal p31's 30,824,827 / 30,861,853 |

Reused, with a new family: `report-trust-funds` / `trust-investment-accounts` (1a);
`report-warrant-article-amounts` / `budget-supplement-passed-over` (p47/2, Article 7 PASSED OVER,
$81,949). Reused families: `omnibus-amendment` (p51/1, p52/1), `trust-funds-summary` (p39/2).

## FINDER MISSES

**None found.** Every page NOT sent for tables was searched in `lines.tsv` for `$` figures and
comma-grouped amounts. Only six such pages carry any (p15, p16, p21, p49, p54, p57), one or two
figures each, all inside sentences: a $30,000 drug task force grant (p15), `Larceny over $250`
(p16), wiring fees $648.00 and arts grants $3,131 (p21), a fee raised from $3.00 to $12.00 per
day (p49), two ballot questions' tax amounts $81,949.00 and $236,447.00 (p54, an election page),
and $440,000 raised by the schools (p57). No money table.

## ROSTER PAGES

Staff rosters, none sent for tables (non-money pages), for `dump_roster_pages`:

- p60 -- `Thomas C. Passios Elementary School Staff` (principal, assistant principal, secretary;
  Primary pre-school and kindergarten; specialists; grades 1-4)
- p61 -- Passios `Principal's Advisory Council` (teachers and parents)
- p62-p63 -- `TURKEY HILL MIDDLE SCHOOL FACULTY` (grades 5-8, guidance, special education,
  specialists, tutors, custodians), then its Principal's Advisory Council on p63
- p65-p66 -- `LUNENBURG HIGH SCHOOL FACULTY` by department, with custodial staff on p66

Not school rosters, also unread and noted only so they are not mistaken for absent:
p14 `ROSTER OF FIREFIGHTERS OF 1991` (2001 landed its fire roster in `report-officials`);
p4-p5 `TOWN OFFICIALS` elected and appointed. p56/1 (School Committee) WAS sent and is mapped to
`report-officials`.

## What the integration pass did with each item (29 October 2026)

Applied ONCE in the shared code (see `sources/data/report-tables/README.md`, "Added by the 1991-2000 integration pass"); counts are this folder's rows after the re-run.

- **1a trust-investment-accounts identity**: APPLIED. report-trust-funds 83 checked / 4 failed / 3 no check -> 90 checked. `($1.76).` is read (3b).
- **1b collection of taxes without ADJUSTMENTS**: APPLIED (a second identity, `absent: ADJUSTMENTS`).
- **1c accountant schedule, 1991 layout**: APPLIED (`BALANCE REVENUE = AVAILABLE - TOTAL EXPENDED - BALANCE FY`, blank as zero, only on a row printing an AVAILABLE figure -- so p25, whose AVAILABLE figure Textract merged into the label, is not checked).
- **1d omnibus-amendment identity**: APPLIED (`^NEW = ADDITIONAL + VOTE|CURRENT APPROP`); p51 3 of 3 checked.
- **2a section subtotal across two columns (p26-27)**: NOT APPLIED -- it is the validator's block walk, shared with the FY reviews; `checks=none` stays.
- **2b receipts split across tables (p24)**: APPLIED (pooled per page). All 123 accounts are now `check failed` against the one GRAND TOTAL (pooled accounts 117,605.00 over it, as measured) -- honest: nothing settles which figure.
- **2c treasurer's cash**: APPLIED (3a mark read; the unlabelled last row is the total). 14 accounts published, summing to 3,012,213.00.
- **2d debt repayment 2001 column**: NOT APPLIED (validator grouping); 3 rows stay `check failed`.
- **2e omnibus stated_total**: APPLIED (list totals). The 80 lines sum to 9,594,459 against 9,594,034 printed, off 425: the 81 rows are `check failed`, honestly.
- **3a, 3b parser marks**: APPLIED as calendar-only readings.
- **4 new datasets**: REGISTERED (`build_db.py`, `map_annual_report_pages.PROOF`). Article 7's 20 supplements now check against `Total Additional Distribution: $81,949`.
- **ROSTER PAGES**: p60, p62, p63, p65, p66 listed in `rosters.csv`, dumped and read into `sources/data/rosters/1991-p*.json`. p61 (an advisory council) was not taken.
