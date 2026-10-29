# 1996 edition: what the integration pass needs to change

Written by the 1996 worker, 28-29 October 2026. Nothing here was changed in a shared file; each item
is a change to `scripts/read_report_tables.py`, `validate_totals.py`, `map_annual_report_pages.py`, a
shared dataset, or a decision. Page numbers are PDF pages (the printed folio runs 6 behind: Balance
Sheet folio 41 = PDF p47).

**What was sent for tables.** `build/textract/ledger.csv` (sha256 `77d133e7...`) records tables `ok`
for 43 pages, the 43 `find_financial_pages.py --list 1996` picks. 36 returned cells. Seven were SENT
and returned no table: p13, p18, p22, p24 (department prose with figures in sentences) and p84, p85,
p86 (warrant articles in prose). Those seven are not "pages with no table" in the sense of unread:
Textract read them and found none. Every other page with no cells was not sent.

## 1. Dataset registrations

| dataset | family | pages | rows | what it is |
|---|---|---|---:|---|
| `report-tax-bill-breakdown` (NEW) | `average-tax-bill` | 45, 46 | 68 | The Board of Assessors' *Breakdown of the Average Residential Tax Bill, Fiscal Year 1997*: per town service, the BUDGETED amount, its percent of the tax levy and its cost to the average taxpayer. A budget (FY1997), not an actual. The `Percent of Tax Levy` and `Cost to Average Taxpayer` columns are the Assessors' derivation, not measurements. No dataset holds this in any year; other 1991-2000 workers may meet the same table under another name -- harmonise by rule 1 (same quantity, stage, grain). |
| `report-warrant-article-amounts` (existing name, 2001) | `budget-amendment-proposed` (new family) | 81 | 5 | Special Town Meeting, May 11, 1996, Article 2: the WARRANT's proposed amendments to five FY1996 budget lines voted May 13, 1995 (`Additional | May 13 Vote | New Appropriation`). The meeting voted two of the five at different amounts, printed in prose under the table (132 Reserve Fund $104,333 / $224,333; 300 School Dept. $107,549 / $6,819,486), so these rows are the proposal, never the appropriation. |

Both go through `emit_generic`. `map_annual_report_pages.PROOF` has no entry for either, so p45, p46
and p81 are `unproven` whatever their arithmetic does.

## 2. Identities the shared code does not have (each tested here, by our own sum, on 1996's cells)

- **collection-of-taxes WITHOUT an ADJUSTMENTS column** (p67). 1996 prints `TAX | FORWARD |
  COMMITMENTS | REFUNDS | PAYMENTS | ABATEMENTS | TAX TITLE | BALANCES`. The existing identity names
  ADJUSTMENTS, so it is not applied and every `proof` is blank. Proposed: `('BALANCES', [(1,'FORWARD'),
  (1,'COMMIT'), (1,'REFUNDS'), (1,'PAYMENTS'), (1,'ABATEMENTS'), (1,'TAX TITLE')], {'absent':
  ['ADJUSTMENTS']})` (payments, abatements and tax title print negative). Tested: **26 of 26 rows
  close**, and all seven columns sum exactly to the printed GRAND TOTAL (1,606,405.23; 9,020,880.20;
  32,059.52; -9,148,640.36; -114,269.92; -145,337.19; 1,251,097.48).
- **special-revenue with a TRANSFERRED column** (p58-60). Headers `FORWARD | TOTAL REVENUE | TOTAL
  EXPENDED | TRANSFERRED TO GENERAL FUND | BALANCE FY 97`. Proposed: `BALANCE = FORWARD + REVENUE -
  EXPENDED - TRANSFERRED`. Tested: **79 of 79 fund rows close**.
- **category-above-block** (p45-46, tax bill). Each category prints ABOVE its lines, then a blank
  row (`Town Administrative 561,672` then 19 lines). The validator sums every row against
  `TOTAL COST OF TOWN SERVICES` and fails on the grouping (it summed 20,731,206), so the map sets
  `checks=none` and all 68 rows are `no check`. Tested: each of the eight categories equals the sum of
  its lines, and the eight categories sum to 12,742,557 exactly. NOTE the page break: Public Works
  ends p45 and Education starts p46 with no blank row between, so a block reader must break at the page.
- **warrant amendment rows** (p81): `Additional + May 13 Vote = New Appropriation`. Tested: 5 of 5.
- **omnibus across two side-by-side panels** (p83, `groups:2`): the 84 lines in both panels sum to
  the in-table `TOTAL BUDGET $ 12,742,557` exactly, but the column check reads each panel alone
  (`col 4 ... reaches rows on a page not held`), so all 85 rows are `no check`. The map's
  `stated_total` (12742557) is not read by `emit_generic`.
- **debt repayment schedule by row label** (p66). `GRAND TOTAL PRINCIPAL` is the sum of the
  `PRINCIPAL` rows and `GRAND TOTAL INTEREST` of the `INTEREST` rows -- not of the issue `TOTAL ...`
  rows, which `TOTAL DEBT` sums. Tested: principal closes in all 16 columns; interest in 14 (1997 and
  1999 are each $1 under the printed figure); `TOTAL DEBT` = principal + interest in all 16. The
  validator instead summed issue totals for 2004-2010 (only one issue pays there) and fails those
  columns as `grouping`. Separately, the issue total `TOTAL STREET BETTERMENTS` prints $33,688 over
  rows $25,000 + $8,888 = $33,888; $8,888 is corroborated by p65 (`DUE IN FISCAL 1997` interest for
  STREET BETTERMENTS 1989) and by the column's grand total, so the printed issue total is the odd one.

## 3. Column checks ignore `header_from` (p59-60)

`cell_checks` names columns from each Textract table's OWN header rows. On p59-60 the running
title bleeds into the header (`FUNDS (CONT.) TOTAL EXPENDED`), so the EXPENDED column is a different
name from p58's and the GRAND TOTAL on p60 is checked against p59+p60 only: `printed 2,060,205.39,
rows sum 1,528,025.11 (off 532,180.28)`. 532,180.28 is p58's expended. The map gives `header_from=58/1`
on p59 and p60 (which fixed column_meaning), but the checks do not read it. Tested by our sum: all
five columns of the named fund rows on p58-60 sum exactly to the GRAND TOTAL row. Change: let
`cell_checks` take a continuation table's column names from its `header_from`. This leaves 42 rows
`check failed` and p59, p60 `unproven` on correct figures.

## 4. Trust funds (p62-63)

- **A comma for the decimal point**: p62 row 17, `J& M SDWLK/GRDS INT`, BOOK BALANCE `$ 19,548,51`.
  It does not parse, so TOTAL COLONIAL's book column fails by 19,548.52. Add to
  `validate_totals.REPAIRS`: a figure ending `,DD` after a full thousands group is `.DD`. Even then the
  page's own DIVIDENDS and BOOK BALANCE totals each differ from their rows by 0.01 (triage proposes a
  one-digit misread; it may equally be the printer's rounding).
- **A column offset for `header_from`**: p63 has NINE columns where p62's header has eight
  (REDEMPTIONS prints its `$` in a column of its own). Borrowing p62's header named BOOK BALANCE
  `MARKET BALANCE`, so the map uses `header=none` instead and p63's column_meaning is `not
  established`. Wanted: `header_from=62/1` plus a column mapping (e.g. `cols:1,2,3,4,5,-,6,7,8`).
- The layout is the 2001-2005 `trust-funds-book` plus a MARKET BALANCE column on p62 only.
  `GRAND TOTAL TRUST FUNDS: 704,001.84` is the BOOK BALANCE column (the five subtotals sum to it).

## 5. Wage list (p93-102): two reader defects and one finding

- **A numeric DEGREE/STEP lands in v1** (p96-102). Where the school list prints a bare step (`0`,
  `6`, `MAX` is text), the step is parsed as a figure and the wage moves to v2; `column_meaning` says
  so, but `coverage()` reads v1 and fails every school page. Change: on a wage list, a column whose
  printed header is `DEGREE/STEP` is part of the label. Tested by taking the LAST figure of each row:
  coverage is exact on all seven school pages, and the **318 school rows sum to 6,709,600.54, the
  printed `TOTAL SCHOOL EMPLOYEES 318 TOTAL SCHOOL GROSS WAGES $ 6,709,600.54`** (in-table, p102 r9).
- **The coverage witness misses a figure that shares a line with the department** (p95): Textract's
  line output prints `BUILDING INSPE $ 40,996.26` as one line, so 13 correctly-read cells count as
  `captured, not in the text`. Change: accept a money figure at the END of a line as a printed figure.
- **Two runs, two totals, one `stated_total`**: `coverage()` sums ALL wage rows against the last
  `stated_total`. 1996 prints a town total and a school total and no combined one, so neither was
  given. Change: allow a stated_total per run (per map row group).
- **FINDING, not a reader defect: the town run does not tie.** p95 prints (below the table, page text)
  `TOTAL TOWN EMPLOYEES 156 / TOTAL TOWN GROSS WAGES $ 1,925,089.92`. The cells hold 155 employee rows
  summing to 1,919,918.92: one employee and $5,171.00 short. The page TEXT agrees with the cells (155
  figures on p93-95 besides the total, same sum), and a row-spacing scan of p93-95 found no gap that is
  not a two-line name. So either a row neither Textract pass read, or the printed total/count is off;
  not settled. The one check that would settle it is looking at p93-95 in the PDF for a 156th name.
- The year of the wages is NOT PRINTED (`REPORT OF WAGES PAID`, no calendar or fiscal year): as 2003.

## 6. Smaller

- p83 omnibus: `215 OUT OF STATE EXPENSE $ I` -- the amount is unreadable (`I`), so the line became a
  GROUP heading and that group name is carried onto the 13 left-panel rows below it (297 TOWN FOREST
  ...). The rows still sum to TOTAL BUDGET exactly, so the line is $0 or `-`. Change: in a budget list,
  a numbered line with an unparsed amount is a row with no value, never a group.
- p64 reconciliation: Textract put each pair (`$37,517,924.00 ($17,199,793.00)`) in ONE cell; the
  reconciliation emitter read it correctly (4 rows checked).
- `pages.csv` gives p45, p46 and p81 the subject `regional-school` -- a keyword guess by the mapper, not
  anything on those pages (tax-bill breakdown; town meeting budget amendment).

## FINDER MISSES

Pages NOT sent for tables that hold financial content. Neither was read any other way.

| page | heading | why it is financial | why the finder skipped it |
|---|---|---|---|
| 49 | `GENERAL FUND REVENUES FY 96` | a pie chart of FY1996 general fund revenue by source: property taxes 65%, state-local aid 26%, motor vehicle excise 5%, all other 4% | percentages only, no `$` figure; a chart, so a table read would return little -- borderline |
| 57 | `GENERAL FUND EXPENDITURES FY 96` | a pie chart of FY1996 general fund spending by function: education 63%, public safety 11%, insurance/workers' comp/unemployment 9%, all other 8%, public works 6%, debt service 3% | the same: shares, no `$` figure -- borderline |

No money TABLE was found on an unsent page. Pages with `$` figures that were not sent (p12, 16, 19, 23,
29, 30, 31, 39, 61, 76, 82, 87) carry them in sentences (p76 and p82: the $862,043 / $654,408 override
questions), not tables.

## ROSTER PAGES

For `dump_roster_pages`. None of these was sent for tables.

| page | what | period |
|---|---|---|
| 36 | Lunenburg High School staff by department (administration, English, science, art, reading, social studies, business, guidance, special education, health, athletics, nurse) and the LHS School Council | 1996 report; year not printed beside the list |
| 40 | T.C. Passios Elementary School `FACULTY / 1996 - 1997` (principal through grade 3, cafeteria, custodians) and the Elementary School Advisory Council | 1996-1997 |
| 41 | Passios faculty continued (`Grade 4:` seven names) | 1996-1997 |

Also person-level but not rosters: p93-102 (wages, landed above); p38 School Committee members (officials).

## What the integration pass did with each item (29 October 2026)

Applied ONCE in the shared code (see `sources/data/report-tables/README.md`, "Added by the 1991-2000 integration pass"); counts are this folder's rows after the re-run.

- **1 datasets**: `report-tax-bill-breakdown` REGISTERED, family renamed `average-tax-bill` -> `tax-bill-breakdown` (one name with 1995). `budget-amendment-proposed` kept in report-warrant-article-amounts (a proposal, rule 1); its identity APPLIED, 5 of 5.
- **2 identities**: taxes without ADJUSTMENTS, special revenue with TRANSFERRED (79 of 79), category blocks (68 of 68 `checked`, eight categories = 12,742,557), warrant amendment: APPLIED. Omnibus p83 groups:2: APPLIED (list totals, `checked`). Debt repayment by row label: NOT APPLIED (validator).
- **3 `header_from` in the column checks**: APPLIED (`names_of`).
- **4 trust**: `$ 19,548,51` and `$ 500,00` APPLIED; p63's nine-column `header_from` mapping NOT APPLIED. The 0.01 differences remain, honestly.
- **5 wages**: APPLIED -- the step is label; one total per list (`stated_total` set on p95 1,925,089.92 and p102 6,709,600.54); a figure at the end of a line counts. All 474 rows `checked` on coverage. School: 318 rows = 6,709,600.54 = printed. Town: 155 rows = 1,919,918.92, printed 1,925,089.92 -- one employee and 5,171.00 short, in the reconciliation. OPEN: the glyph witness refuses this edition (negative control), and p94 has suspect cells only coverage covers (README).
- **6 `$ I`**: NOT APPLIED. Page subjects p45, p46, p81: APPLIED (`appropriations`).
- **ROSTER PAGES**: p36, p40, p41 read into `sources/data/rosters/1996-p*.json`.
