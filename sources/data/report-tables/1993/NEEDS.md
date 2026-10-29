# 1993 edition: what the integration pass needs to change

Written by the 1993 worker, 29 October 2026. Nothing here was changed in a shared file. PDF pages
throughout (the index on p2 prints folios one behind the PDF: `Balance Sheet 25` = PDF p26).

Tables were read on the 28 pages `find_financial_pages.py --list 1993` picked; 19 of them hold
cells (pp3, 17, 26-34, 36-37, 52-58). The other 9 picked pages (9, 13, 14, 38-43) were sent and
Textract returned no table: department prose and warrant articles with amounts in sentences.

Every closure count below was measured by monkeypatching the change into an in-memory run
(scratch script, nothing written), not estimated.

## 1. THE VALIDATOR NAMES COLUMNS WITH THE RUNNING TITLE, SO ITS RUNS BREAK ACROSS PAGES (biggest item)

`validate_totals.streams()` builds `names` from every header row, and on pp28-34 Textract returns
the running title (`TOWN OF LUNENBURG / GENERAL FUND APPROPRIATIONS / SUMMARY & CLASSIFICATION OF
ACCOUNTS / FISCAL YEAR 1993 (CONT.)`) as header rows. The title differs page to page (`TOWN ... OF`,
`... (CONT.)`, `OF LUNENBURG` in a different cell), so the APPROPRIATED column is named three
different ways and the carry-by-shared-name across pages drops pages:

- **Accountant schedule, pp28-32.** APPROPRIATED FORWARD at `GRAND TOTAL` (p32 r30): printed
  10,164,676.42, rows sum 8,864,977.60, off **1,299,698.82 = exactly the APPROPRIATED cells of pp28
  and 29**. 29 rows `check failed` that are not wrong.
- **Special revenue, pp32-34.** TOTAL REVENUE at `GRAND TOTAL` (p34 r54): off 385,915.74 = the
  p32-table-2 REVENUE cells (387,908.74 less the title's own `1993`, read as a figure).

`read_report_tables.drop_title()` already solves this for the map's own names. Change: apply the
same rule inside `streams()` (and `split_header` callers in V) before `names` is built. With it:
`report-appropriations` 71 checked / 67 failed / 100 no check -> **112 / 38 / 88**. The 38 that
still fail are real: see 4.

## 2. Row identities (`IDENTITIES`), three layouts 1993 prints

| family | identity (printed headers) | closes |
|---|---|---|
| `trust-investment-accounts` (NEW family, pp56-58) | `^BALANCE$` = `PRIOR YEAR` BALANCE + `PRIOR MONTH` INTEREST + `^CURRENT INTEREST` + `TRANSFERS` TO & FROM + `DEPOSITS` RECEIPTS + `WITHDRAWALS` GRANTS & GIFTS (withdrawals printed negative, so added) | **80 of 80** account/TOTALS rows (the 10 others are the summary, 58/2) |
| `special-revenue`, 1993 headers | `^BALANCE FY` = `^FORWARD` + `TOTAL REVENUE` - `TOTAL EXPENDED` (2001's names were `FORWARD 7` / `RECEIPTS` / `DISBURSEMENTS`) | **59 of 59** -> special-revenue-funds goes 20 checked / 39 failed -> 59 checked |
| `collection-of-taxes`, no ADJUSTMENTS column | `BALANCES` = FORWARD + COMMIT + REFUNDS + PAYMENTS + ABATEMENTS + TAX TITLE, `absent: ['ADJUSTMENTS']` | **27 of 27** rows `footed to its own printed balance`, incl. GRAND TOTAL 1,340,817.36 |

Also `emit_special_revenue` fills `receipts` from a header matching `RECEIPTS`; 1993 heads it
`TOTAL REVENUE`, so `receipts` is blank on all 59 rows. Change: `RECEIPTS|REVENUE`.

## 3. Parser marks and cells

- **Trailing `#` footnote mark** (p55 t2 r6): `($203,501.00) #` (SHAWMUT MONEY MARKET, keyed to the
  page's footnote `INVESTED MONIES NOT TRANSFERRED UNTIL CHECKS ARE ACTUALLY DISBURSED`) does not
  parse, so `emit_treasurers_cash` sums 337,141.00 against the printed 133,640.00 and REFUSES the
  table. With the mark read through: 337,141.00 - 203,501.00 = **133,640.00**, the lone figure under
  the list and the GENERAL LEDGER BALANCE (55/1). Add ` #` (and `*`) to `validate_totals.REPAIRS`.
- **Amount and years payable in one cell** (p53 t1, all 11 issues): `$330,000 1986-95`. AMOUNT does
  not parse, so `debt-by-issue`'s BALANCE = AMOUNT - TOTAL PAYMENTS PRINCIPAL reports `a term did not
  parse` and all 11 rows are `check failed`. By hand it closes on every issue (330,000 - 264,000 =
  66,000; ... 114,330 - 19,330 = 95,000). Change: split a cell `$N YYYY-YY` into the amount and a
  text `payable` before parsing.

## 4. Misreads found and NOT applied (the figures stay as Textract read them)

Each was looked at in the PDF image (pypdfium2 render), and each is the same glyph trouble the 2009
witness handles on wage pages: a `$` printed hard against the next digit.

| where | Textract | page image | what it closes |
|---|---|---|---|
| p30 `Sanders-Highway Dept. 22/92`, TOTAL ENCUMBERED | `$622.98` (line conf 71.1) | `$822.98` | 20,000.00 - 19,177.02; GRAND TOTAL ENCUMBERED 195,957.86 (rows 195,757.86, off 200.00) |
| p54 first ELEMENTARY SCHOOL REMODELING, INTEREST (EXEMPTED) 1995 | `$6,280` (81.9) | `$5,280` | TOTAL REMODELING 38,280; row TOTAL 15,840 |
| p54 GRAND TOTAL INTEREST 1995 | `$66,063` (46.6) | `$56,063` | TOTAL DEBT 277,063 = 221,000 + 56,063 |

The integration pass could extend `witness_dollar_glyphs.py` beyond wage pages; until then these
rows are `check failed`, which is honest.

## 5. Totals the reader cannot see

- **Omnibus budget across two tables** (p37 t1 + t2): `TOTAL BUDGET VOTED 10,208,686.` sits under
  table 1 (UMAS 300-941, 38 lines, 8,847,056) and is the total of both (table 2, UMAS 122-299, 41
  lines, 1,361,630). Mapped `checks=none`, rows `no check`. A map column naming the tables a total
  covers would make all 79 lines `checked`.
- **Bonds authorized and unissued** (p53 t2 + t3): `TOTAL UNISSUED: $1,619,775` at the foot of t3 =
  1,525,775 (t2) + 94,000 (t3). Same remedy; 17 items + total, now `no check`.
- **Trust summary** (p58 t2): the ten purposes sum to `GRAND TOTAL TRUST $455,981.64`, which Textract
  left out of the table (row 11 empty; the figure is in the lines). Let `emit_generic` check a
  table's rows against the map's `stated_total` (given: 455981.64) -> 10 rows `checked`.

## 6. Dataset decisions (no new dataset)

- **No NEW dataset.** Every table is the same quantity as an existing one.
- **NEW FAMILY `trust-investment-accounts`** in `report-trust-funds` (pp56-58), named for the
  printed heading `TRUST and INVESTMENT ACCOUNTS`. A third layout: neither 2001's book nor 2010's
  ending cash. Never sum with either. The integration pass may want one name for it across the
  1991-2000 editions (others in this batch likely print the same layout).
- p36 t1 (FY93 budget-line changes, April 10 1993 STM Article 1) went into `report-appropriations`
  family `stm-budget-adjustments`, as 2004 p94. Its UMAS `914.1` is not matched by `ID_TEXT`
  (`^\d[\d\s\-/&]*$` has no `.`), so the WHOLE UMAS column fails `id_columns` and lands as a figure: rows 1-6 carry `v1=UMAS` (132, 210, 650, 449, 913, 914.1), `v2=AMOUNT`, `v3=NEW TOTAL`, labelled so in `column_meaning`; row 7's `1300-5300` matches ID_TEXT and joins its label, so its v1 is AMOUNT. Change: allow `\d+\.\d` (a UMAS sub-line, no `$`, not two decimals) in ID_TEXT.
- p52 `tax-collection` shows subject `tax-collection` on p27 in pages.csv (the receipts page) --
  `M.subject_of` keys on `TAXES & EXCISES`. Cosmetic; the page is proven by `annual-report-receipts`.

## FINDER MISSES

**None found.** Every page whose lines print a `$` figure was checked: the 5 pages with a `$` figure
outside the picked set print one or two figures in prose (p6, p12 `$5000 contribution`, p15
`Larceny over $250`, p16, p46 a ballot question) -- none is a table. No page with no cells holds an
appropriation, receipt, balance, wage, debt, trust or valuation table.

## ROSTER PAGES

**1 page.** p24, `SCHOOL STAFF` under the Lunenburg High School report (principal, assistant
principal, department lists by subject, secretaries). Not sent for tables. Not a roster: p18 (School
Committee members and terms -- officials), p25 (LHS School Council -- a committee). No
elementary/middle school staff lists were found (searched the lines for staff, faculty, teacher,
principal, custodian, secretary).

## Out of scope by the batch rule, printed and not read

Elected/appointed officials (pp4-5), enrollment (p18 `OCTOBER 1, 1993 ENROLLMENT SUMMARY`),
elections (pp44-46), vital records (pp47-51): not sent for tables, not rows, not gaps.

## What the integration pass did with each item (29 October 2026)

Applied ONCE in the shared code (see `sources/data/report-tables/README.md`, "Added by the 1991-2000 integration pass"); counts are this folder's rows after the re-run.

- **1 running title in the validator's names**: APPLIED FOR THIS EDITION ONLY (`edition.json` `validator_drop_titles: true`; the validator takes the names through a new optional `names_of`). Not the default: on 1999, 2000 and 2003 the same change joined accountant-schedule pages whose unlabelled department subtotals then failed the GRAND TOTAL on correct figures. report-appropriations here: 71/67/100 -> 192 checked / 38 failed / 8 no check; the 38 failures are the TOTAL ENCUMBERED block off 200.00 (the `$622.98`/`$822.98` misread, item 4).
- **2 identities** (trust-investment-accounts, special revenue 1993 headers, collection of taxes without ADJUSTMENTS): APPLIED. trust 90 of 90, special revenue 59 of 59 checked. `emit_special_revenue` fills `receipts` from TOTAL REVENUE.
- **3 trailing `#`, amount + years in one cell**: APPLIED. Treasurer's cash published (14 accounts = 133,640.00); debt-by-issue closes.
- **4 the three `$`-glyph misreads**: NOT APPLIED -- the figures stay as read and their rows `check failed`, which these tables can do because they print totals; the glyph witness was not extended past wage lists (its own reason: a table with a total already has a check that can fail).
- **5 totals over two tables; trust summary GRAND TOTAL**: APPLIED (list totals). The omnibus (79 lines, incl. `150.`, `0.` now read) and the bonds and the summary are `checked`.
- **6 `914.1`**: APPLIED (identifier). Receipts page subject: NOT APPLIED -- the subject vocabulary has no receipts subject.
- **ROSTER PAGES**: p24 read into `sources/data/rosters/1993-p024-high.json`.
