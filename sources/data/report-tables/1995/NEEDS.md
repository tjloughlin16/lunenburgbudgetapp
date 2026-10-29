# 1995 edition: what the integration pass needs to change

Written by the 1995 worker, 28-29 October 2026. Nothing here was changed in a shared file. PDF
pages throughout (printed folio = PDF page - 6: SPECIAL REVENUE FUNDS p57 prints `51`).

Tables were read on the 39 pages `find_financial_pages.py --list 1995` picked; 42 tables came
back, all mapped. Eight picked pages returned NO table (p11, 17, 18, 60, 75, 78, 79, 82): each is
prose with dollar amounts in sentences (selectmen's report, Council on Aging grants, town clerk /
treasurer report, warrant articles) -- picked correctly, nothing tabular lost.

## 1. Dataset registrations (three NEW datasets, GENERIC columns via emit_generic)

| dataset | family | pages | rows | what it is |
|---|---|---|---:|---|
| `report-tax-bill-breakdown` | `tax-bill-breakdown` | 47-48 | 67 | The Board of Assessors' **Breakdown of the Average Residential Tax Bill, Fiscal Year 1996**: budgeted amount, percent of tax levy and cost to the average taxpayer for each town service, under eight category rows. A BUDGET (FY1996), never an actual; the percent and per-taxpayer columns are the Assessors' arithmetic. No 2001-2010 or FY-era dataset holds it. |
| `report-highway-accounts` | `highway-accounts` | 21 | 18 | The Highway Superintendent's own **Appropriated / Expenditures / Balance** for six highway accounts, rounded to the dollar. Fiscal 1995 by the schedule (not printed on the page). Not a copy of the accountant schedule: TRAFFIC SIGNS & DEVICES expended 8,735 here, 9,000.00 on p55. |
| `report-vehicle-inventory` | `highway-vehicles` | 22 | 32 | **Highway Department vehicles/equipment as of March 1996**: year, make and model, mileage. No money. |

`map_annual_report_pages.PROOF` entries are not needed for the first two to be honest: neither
has a check the reader can run today (see 3 and 5).

## 2. Row identities that close by hand and the reader does not apply

| family | pages | identity as printed | closes by hand |
|---|---|---|---|
| `special-revenue` | 57-59 | `BALANCE FY 96` = `FORWARD` + `TOTAL REVENUE` - `TOTAL EXPENDED` (this edition prints TOTAL REVENUE / TOTAL EXPENDED where 2001-2010 print RECEIPTS / DISBURSEMENTS) | 76 of 76 rows (75 funds + GRAND TOTAL) |
| `collection-of-taxes` | 66 | `BALANCES` = FORWARD + COMMITMENTS + REFUNDS + PAYMENTS + ABATEMENTS + TAX TITLE -- there is NO `ADJUSTMENTS` column, so the existing identity (which names it) is skipped. Needs a variant with `{'absent': ['ADJUSTMENTS']}` | 28 of 28; every column also sums to the GRAND TOTAL row |
| `omnibus-amendment` | 74 | `New Appropriation` = `Additional` + `May 14 Vote` | 7 of 7; Additional sums to the $111,359 the vote states |
| `debt-by-issue` | 65 | existing `^BALANCE = ^AMOUNT - TOTAL PAYMENTS PRINCIPAL`, but the AMOUNT cell holds the PAYABLE years too (`$330,000 1986-95`), so the term does not parse -> `check failed` on all 7 issues | 7 of 7 (see 4) |

## 3. Totals the reader cannot reach, which tie by hand

- **p76-77 omnibus**: `TOTAL BUDGET VOTED $ 11,369,011` (p77, right-hand group) covers BOTH
  side-by-side groups on BOTH pages. The 81 voted lines sum to exactly 11,369,011. Reader:
  `col 6 at p77r7 reaches rows on a page not held`. The map's `stated_total` (11369011) is
  there for an emitter that wants it.
- **p65 t2 bonds authorized and unissued**: `TOTAL UNISSUED: $2,507,975` closes on both lists
  (31 amounts). Same message.
- **p47-48 tax bill breakdown**: each CATEGORY row prints ABOVE its lines and equals their sum
  (Town Administrative 533,602 ... Debt Retirement 309,788); the eight categories sum to
  `TOTAL COST OF TOWN SERVICES 11,369,011` (= the TOTAL BUDGET VOTED, p77). validate_totals
  reads the categories as items, so every row was `check failed` on figures that tie; the map
  says `checks=none` to stop that. Needs: a labelled row immediately under a blank row, whose
  value equals the sum of the rows that follow it up to the next blank row, is a subtotal of
  them. Then drop `checks=none`.
- **p64 debt repayment schedule**: TOTAL STREET BETTERMENT, GRAND TOTAL PRINCIPAL and GRAND
  TOTAL INTEREST are `check failed` because validate_totals reports the sparse `2001` column
  open (`GRAND TOTAL PRINCIPAL 2001 45,000.00 of_totals OFF -3,263.00`; `GRAND TOTAL INTEREST
  2001 3,263.00 empty OFF 3,263.00`). The page is right: the only 2001 entries are STREET
  BETTERMENT 91's principal 45,000 and interest 3,263, which ARE the grand totals; it is the
  total-of-totals stack popping the wrong run in a column with one block. Every other column
  closes.
- **p51-56 accountant schedule**: department subtotals and the GRAND TOTAL (p56 r76,
  `$11778244.60 | $11778244.60 | $11450889.14 | $265951.42 | $61404.04`) print with NO label --
  the 2001 NEEDS item 5, unchanged. 57 rows are `checked` by the row identity; the other 177
  are `no check`.

## 4. Parser marks (validate_totals.REPAIRS candidates)

| mark | where | effect today |
|---|---|---|
| a trailing footnote asterisk, `($147,587.00) *` | p63 t2 r6 (footnote `* INVESTED MONIES NOT TRANSFERRED UNTIL CHECKS ARE ACTUALLY DISBURSED`) | the cell does not parse, the accounts sum 1,334,749.00 instead of 1,187,162.00, and **treasurers-cash refuses the table (0 rows)**. With the mark read, the 15 accounts sum to the GENERAL LEDGER BALANCE exactly |
| angle brackets for a negative, `<$ 1,343>`, `$ 26,520>` | p21 t1 r9; p22 (prose, no cells) | lands blank, text in unparsed_cells |
| an amount and a year range in one cell, `$330,000 1986-95` | p65 t1 r3-r10, the AMOUNT and PAYABLE columns merged by Textract | AMOUNT does not parse, debt-by-issue identity fails (2 above) |

## 5. Identifier columns with dotted line numbers (p77)

The right-hand group's line numbers are `913`, `914.1`, `914.2`, `914.3`, `941`. `ID_TEXT`
(`^\d[\d\s\-/&]*$`) rejects `914.1`, so the column is read as figures and five rows carry the
line number in v1 and the amount in v2 (UNEMPLOYMENT COMP, HEALTH INSURANCE, LIFE INSURANCE,
MEDICARE CONTRIB, LIABILITY INSURANCE). Change: accept `^\d+\.\d$` (one decimal digit, no `$`,
no comma) as an identifier when the column also holds plain integers. p76 has `411-5800`, which
already passes.

## 6. Tables Textract did not return on pages that WERE sent (not finder misses)

- **p86, right-hand column**: 57 school wages (SPED TUTOR ... SPEECH PATHOLOGIST ... SUBSTITUTE)
  are in lines.tsv only; the cells hold only the left column (56 wages). The coverage check
  fails all 56 captured rows for it. Needs a lines-based read of the right column (x > 0.59).
- **p61, trust funds**: the table came back, but its BOOK BALANCE and MARKET BALANCE columns are
  misaligned (two figures in one cell, values shifted a row, rows empty). The page is printed
  rotated; in lines.tsv the BOOK BALANCE column is the set of lines at `top` ~0.22 and MARKET
  BALANCE at `top` ~0.13, each in row order by `left` (120,036.70 at 0.169, 100.00 at 0.185,
  500.00 at 0.201 ...). The first six columns look aligned. NOT LANDED rather than published
  wrong; p62 (aligned) is landed with `header_from=61/1`.
- **p62, SUMMARY OF FUNDS**: 13 purposes (CEMETERY 185,128.21, WORTHY POOR FUNDS 24,100.26 ... SECURITY STREET 4,311.65; each figure prints just above its label on the rotated page, `left` 0.6158 vs 0.6176) and
  `GRAND TOTAL TRUST FUNDS: 512,307.70`, in lines only. It would be `trust-funds-summary`
  (2001's family name).
- **p22, highway accounts**: SNOW REMOVAL (65,000 / 91,520 / `$ 26,520>`), LANDFILL (4,000 /
  3,997 / 3), VEHICLE MAINTENANCE (131,660 / 131,346 / 314) -- the rest of p21's
  `report-highway-accounts`, as prose lines with no table.
- **p21 grouping**: the first account's description runs over two rows, so its three lines
  carry group `and clerical.` instead of `LABOR` (a description continuation row overwrites
  the group).

## 7. A finding, not a reader defect: special revenue GRAND TOTAL (p59)

The GRAND TOTAL does not close on the 75 funds printed in any of its four columns: FORWARD off
-15,167.43, TOTAL REVENUE off 63,415.61, TOTAL EXPENDED off 47,405.88, BALANCE FY 96 off 842.30.
The four differences themselves satisfy the row identity (-15,167.43 + 63,415.61 - 47,405.88 =
842.30), and every listed fund closes it. What the data shows: the printed total includes one or
more funds, netting to that quadruple, that pp57-59 do not list (the lines file holds no such
row). It does not show which, or whether the list or the total is in error. BALANCE FY 96
222,906.47 is also the special revenue UNDESIGNATED balance on the balance sheet (p49), so the
total, not the list, agrees with the balance sheet. A candidate gap row for the integration pass
to weigh. -- closes: the Town Accountant's fiscal 1995 special revenue fund ledger.

## FINDER MISSES

**None found.** Every page with no cells was searched in lines.tsv for `$` figures, cents and
comma-grouped numbers, and for fee / receipt / revenue / collected / budget / appropriat. Hits
were all prose: p23-24 (Monty Tech fundraisers, $7,000, $1,400, $191,000), p25 ($55,064 COPS
grant, $15,495 vests), p26 (`Larceny over $250`), p29 (ambulance ~$80,000), p33 ($6,000 grant),
p34 ($7 memberships), p39 ($50,000 capital request), p80-81 (a $10.00 dog fee in by-law text).
Two non-money tables sit on unsent pages and are out of scope: p26-28 police incidents by type,
p29 FIRE DEPARTMENT VEHICLES & MILEAGE AS OF MARCH 1996.

## ROSTER PAGES

| page | what | notes |
|---|---|---|
| 40 | `SCHOOL STAFF` -- Lunenburg High School staff by department (principal, assistant principal, mathematics, English, science, ... director of athletics), about 60 names | the only per-school staff roster in the edition; no cells (page not sent) |
| 41 | `LHS SCHOOL COUNCIL` -- 11 members with role (`Gail Wolejko - Parent/Co-chair`) | |
| 35 | `LUNENBURG SCHOOL COMMITTEE` -- five members with office and term expiry | |
| 37 | School Building Committee -- co-chairs, members, advisors | |
| 29 | `ROSTER OF FIREFIGHTERS FOR 1995` -- 45 names, ranks, `*` = rescue squad | a town roster, not a school one (2010 put its fire roster in report-officials) |

The school WAGE pages (p86-88) list positions only (`TEACHER B+15 MAX`), no names, so they are
not rosters and cannot be joined to one by name.

## Page integrity (report_review.py --dry-run): 2 issues, one cause

`out_of_place` and `duplicate_folio` on PDF 66: its folio line reads `09` (lines.tsv p66,
left 0.5073, top 0.9657) and printed 9 is also on PDF 15. Its neighbours put it at 60, and
`09` is `60` read upside down -- COLLECTION OF TAXES is a landscape page, as are the trust fund
pages. Hypothesis, not verified against the pixels; nothing here suggests a page is missing or
out of order. If confirmed, page_integrity could accept a folio that reads as its expected
number rotated 180 degrees.

## What the integration pass did with each item (29 October 2026)

Applied ONCE in the shared code (see `sources/data/report-tables/README.md`, "Added by the 1991-2000 integration pass"); counts are this folder's rows after the re-run.

- **1 three new datasets**: REGISTERED (`build_db.py`, PROOF). The tax bill breakdown is ONE name with 1996's: `report-tax-bill-breakdown`, family `tax-bill-breakdown`.
- **2 identities** (special revenue, taxes, omnibus-amendment, debt-by-issue via the amount+years reading): APPLIED. special revenue 76 of 76, omnibus-amendment 7 of 7.
- **3 totals**: omnibus p76-77 and bonds p65 APPLIED (list totals, `checked`); the tax bill's category blocks APPLIED (`category_blocks`: all 67 rows `checked`, eight categories = 11,369,011); debt repayment 2001 column and accountant unlabelled totals NOT APPLIED (validator block walk).
- **4 parser marks**: APPLIED (`($147,587.00) *` -> treasurer's cash published, 15 accounts; `<$ 1,343>`; `$330,000 1986-95`).
- **5 dotted line numbers**: APPLIED.
- **6 tables Textract did not return** (p86 right column, p61-62 trust, p22 highway prose, p21 grouping): NOT APPLIED -- no lines reader; p86's 56 rows stay `check failed` on coverage, honestly.
- **7 special revenue GRAND TOTAL finding**: recorded in the rows' reconciliation; not registered as a money gap (no page asks it).
- **wages**: families `gross-wages-town` (pp84-85) and `gross-wages-school` (pp86-88). No total is printed for either.
- **page integrity, folio `09`**: NOT APPLIED.
- **ROSTER PAGES**: p40 read into `sources/data/rosters/1995-p040-high.json`.
