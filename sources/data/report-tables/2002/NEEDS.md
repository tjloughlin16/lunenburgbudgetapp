# 2002 edition: what the integration pass needs to change

Written by the 2002 worker, 28 October 2026. Nothing below was changed: each item is a shared
script, registry or decision outside `report-tables/2002/`. Figures are from this folder's rows
or the Textract cells/lines for `4528-2002-annual-town-report`, by page.

## 1. treasurers-cash: 0 rows published, and the accounts DO tie (p62 table 2)

`emit_treasurers_cash` looks for a total row with a TOTAL / "ledger balance" label. On p62 the
total row prints no label (cells r21: empty, empty, `$3,851,439.00`), and the `GENERAL LEDGER
BALANCE $3,851,439.00` it ties to is in table 1. The 20 accounts sum to 3,851,439.00 (the
emitter's own note says so). So the refusal is the emitter not finding a total, not a failed tie.

Change: let `emit_treasurers_cash` use `m['stated_total']` when no labelled total is read
(map.csv now carries `stated_total=3851439` on 62/2), the way `emit_capital_plan` does. Expected
result: 20 rows, `accounts sum to the stated total`.

## 2. NEW dataset `report-treasurers-cash-reconciliation` (p62 table 1): register it

The year's cash FLOW, which no FY2011-FY2025 table or 2010 prints: balance June 30, 2001;
receipts 7/1/01-6/30/02 less investments transferred; disbursed less revenue cash invested;
general ledger balance. Emitted in GENERIC columns, family `cash-reconciliation`, 8 rows.

- Register it with `merge_report_tables.py` / `build_db.py` like any new `report-*` file, and give
  `map_annual_report_pages.PROOF` a label for it (p62 is `unproven` only because PROOF has none).
- The page states its own identity, down the column, not across a row:
  `2,958,339 + (54,887,434 - 24,832,996 = 30,054,438) = 33,012,777`;
  `33,012,777 - (55,395,096 - 26,233,758 = 29,161,338) = 3,851,439` = GENERAL LEDGER BALANCE.
  All four steps close by our arithmetic. `IDENTITIES` is row-wise, so this needs a vertical
  identity (or a bespoke emitter) to make the rows `checked`; today they are `no check`.

## 3. validate_totals: 2002's department subtotals print WITHOUT A LABEL (p49-54)

In the 2002 accountant schedule a department's line items print APPROPRIATED and EXPENDED only;
its subtotal prints on an unlabelled row carrying AVAILABLE and BALANCE TO REVENUE too. The
validator sums those subtotal rows together with the lines under `GRAND TOTAL`, e.g. TOTAL
EXPENDED printed 18,361,468.36, rows sum 31,911,676.01 (triage: grouping). That is why 157
accountant-schedule rows read `check failed`: the triage says whole rows, not a digit.

A naive test (lines since the last heading or subtotal, summed against the next unlabelled row
that carries AVAILABLE) closes 76 of 94 subtotal column-blocks on APPROPRIATED and EXPENDED. The
18 that do not are probably my block boundaries, not misreads -- unchecked. Change: treat an
unlabelled row with an AVAILABLE figure as a subtotal of the rows above it since the last
heading/subtotal, as a labelled `Total` would be.

## 4. NEW table families (no identity proposed for two of them)

| family | dataset | pages | identity |
|---|---|---|---|
| `trust-funds-book` | report-trust-funds | 67-69 | **none proposed.** Columns are ALLOCATION, BEG BAL 6/30/01, DIVIDENDS, CONTRIBUTIONS, REDEMPTIONS, BOOK BALANCE -- not 2010's ENDING CASH / ENDING MARKET. Book balance includes dividends on some rows and not others (SALE OF CEMETERY LOT: 28,249.21 + 1,251.09 - 850.00 = 28,650.30; GEORGE WAKEFIELD SCHOL: 18,088.07 - 1,500.00 = 16,588.07, dividends 758.11 not added), so no single row identity holds. Keep it apart from `trust-funds` in any sum |
| `omnibus-amendment` | report-appropriations | 85 | `NEW = Additional + May 4 Vote` is what the figures read as (lines 5, 6 close; line 4: 19,126 + 100,000 != 199,126). Needs item 5 first |
| `cash-reconciliation` | report-treasurers-cash-reconciliation | 62 | item 2 |

## 5. Parser mark: an amount with a TRAILING FULL STOP does not parse (p85)

`$19,126.`, `1,418.`, `$100,000.`, `$2,397,142.` (the STM Article 1 table). They land in `label`
and v1 is the line number. A money pattern accepting `\d[\d,]*\.$` (no cents) as whole dollars
would fix it. Check first that it does not turn sentence-final numbers in prose cells into figures.

## 6. gross-wages: a PRINTED GRAND TOTAL exists and ties to the cent (p107)

p107 prints `GRAND TOTAL GROSS WAGES FOR 2002 $12,853,426.68`. The 582 employee rows (p99-107)
sum to exactly 12,853,426.68. The coverage grade (`coverage()`) does not use it; a total-tie is a
stronger proof than coverage and could be recorded in `reconciliation`. The total row is IN
report-gross-wages as `kind=total` -- anything summing the dataset must exclude it.

Also: unlike 2010, this payroll lists SCHOOL employees (teachers, paraprofessionals, substitutes)
with the town, by POSITION, not by department. `gross-wages.csv`'s `department` column has no
honest value for these rows; the label carries `NAME POSITION`.

## 7. Enrollment header (p38): the dates are row 3, the reader takes row 1

p38's table has no money figure, so `records()` takes row 1 (`ENROLLMENT--OCTOBER 1, 2002`) as
the header and column_meaning reads `not established` for the three counts. The printed header
is row 3: `School/Grade | 10-01-00 | 10-01-01 | 10-01-02`. A `header_row` column in map.csv (or
taking the first row whose other cells are all non-empty) would name them. The school totals
(`Total Primary School 185 179 187` ...) and `TOTAL ALL SCHOOLS* 1888 1877 1883` are printed
identities nobody checks today (also true of 2010's enrollment rows).

## 8. A DECISION, not a code change: births and marriages (p70-73) are held

They name private persons with identifiers: births give the child, date, birthplace and parents;
marriages give date of birth and residence. FY2012-FY2025 print counts only, `AT THE
RECOMMENDATION OF THE REGISTRY OF VITAL RECORDS AND US DEPARTMENT OF STATE` (FY2012 catalogue
row). I did not land them; deaths (p74) and burials (p10) are landed, as 2010 lands burials.
TJ to decide. If counts are wanted, they should be counted from the rows and labelled as ours --
the page prints no count.

## 9. Facts found that a reader may ask about (not changes; nothing here explains them)

- Omnibus FY2003 (p76-77): Article 3's six funding sources on p76 sum to $18,624,017.00; the
  page prints `Total Omnibus Budget $18,624,217.00`. $200 apart.
- State primary (p93), Republican auditor: write-ins print `5 6 4 4` by precinct and TOTAL `5`;
  the precincts sum to 19, and the race's TOTAL row (`216 146 145 157 664`) equals blanks
  (645) plus 19. Textract's line pass reads the same `5`.
- Bonded indebtedness (p63): BALANCE is after the FY2003 payment (`TOTAL PAYMENTS THRU 2003`),
  total $4,536,018; the balance sheet (p46) and repayment schedule (p64-65) print $5,037,933 at
  June 30, 2002. 5,037,933 - 501,915 (FY2003 principal) = 4,536,018. Do not treat the by-issue
  balance as the 30 June 2002 stock.
- Bonds authorized and unissued (p63): total printed in whole dollars ($20,991,379) against
  lines summing to $20,991,378.67.
- Special revenue funds GRAND TOTAL balance (p59) $564,302.99 equals the balance sheet's
  special revenue fund equity (p46). The water, sewer and solid waste ENTERPRISE funds are rows
  of the special revenue schedule (p59); the balance sheet has no enterprise column.
- Pages 48 and 55 are pie charts (`GENERAL FUND REVENUES FY 02`, `GENERAL FUND EXPENDITURES FY
  02`) with percentages only and no Textract table, so they are not in pages.csv. If the page map
  should list every financial page, they need rows from outside map.csv.

## Integration pass, 28 October 2026

What the one integration agent did with each item above. Counts are this folder's rows after
`read_report_tables.py`; the reasons for anything not applied are here so nobody re-asks.

- **1 treasurer's cash: unlabelled total row.** APPLIED: an unlabelled last row holding one figure is the total; 20 accounts publish.
- **2 register the reconciliation.** APPLIED: 9 rows `checked` down the page.
- **3 unlabelled department subtotals.** NOT APPLIED -- a change to validate_totals' block walk (table order, cross-page grand totals, unlabelled department subtotals). validate_totals is shared with the FY2011/FY2020 reviews, and the parser changes that WERE made there were proved not to alter one check of those reports; a block-walk change could not be proved the same way in this pass.
- **4 new families.** `trust-funds-book` is now the family for every 2001-2005 book layout; the omnibus amendment reads (see 5).
- **5 trailing full stop.** APPLIED: `$19,126.` reads as 19126 (validate_totals.REPAIRS, only with `$` or a thousands comma, so `12.` stays a line number). p85: `NEW = Additional + May 4 Vote` now has values in v1-v3.
- **6 gross-wages grand total.** APPLIED: `stated_total=12853426.68` on p107; the employee rows sum to it (recorded in `reconciliation`).
- **7 enrollment header (p38).** APPLIED: a row of dates is the header.
- **8 births and marriages.** NOT APPLIED -- a decision for TJ, not a mapping: named births (infants, parents) and marriages (dates of birth) stay NOT LANDED.
- **9 facts found.** No change asked.
