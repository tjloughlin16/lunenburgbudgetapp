# 2007 edition: what the integration pass needs to change

Written by the 2007 worker. Nothing here has been applied: every item is a change to a SHARED
script or file, which a worker may not touch. Each says the exact change, why, and which pages.

## 1. Trust funds: an identity for the 2007 headers (`scripts/read_report_tables.py`, IDENTITIES)

**Change.** Add a second entry to `IDENTITIES['trust-funds']`:

    ('ENDING CASH', [(1, 'BEGIN BAL PRINC'), (1, 'BEGIN BAL EARN'), (1, 'CONTRIB'),
                     (1, 'NET EARNINGS'), (1, 'DISBURSE'), (1, 'TRANS\\. OF EARN')]),

**Why.** p74-75 print `BEGIN BAL PRINCIPAL | BEGIN BAL EARNINGS | CONTRIB TO PRINCIPAL FY 07 |
REALIZED G/L FY 07 | FY 07 NET EARNINGS | DISBURSEMENTS FROM PRINC. FY 07 | FY 07 TRANS. OF
EARNINGS | FY 07 ENDING CASH VALUE`. The existing regexes (`BEGIN+ING BALANCE PRINC`,
`TRANSFERS`) find nothing, so no row identity runs and the rows are graded by column totals only.
Two differences from 2010, both measured on this edition's rows:
- DISBURSEMENTS are printed NEGATIVE here, so the term is `+1`, not 2010's `-1`.
- `REALIZED G/L` is NOT a term. With it, 0 of 41 eight-value rows close; without it, 37 of 41.
The four that do not close (PERPETUAL CARE BEQUEST off 3,100.00, SALE OF CEMETERY LOTS off
5,100.00, the cemetery SUBTOTAL and the p75 SUBTOTALS off 8,200.00) differ by round hundreds that
carry into both subtotals, which reads as a printed difference rather than a misread. The new
regexes cannot match 2010's `BEGINNING BALANCE PRINC.` headers, so 2010 is unaffected.

## 2. Bonded indebtedness: a term for the 2007 header (`IDENTITIES['debt-by-issue']`)

**Change.** Add `('^BALANCE', [(1, '^AMOUNT'), (-1, '^TOTAL PRINCIPAL')])`.

**Why.** p76 prints `TOTAL PAYMENTS THRU 2007` over two sub-columns; Textract put `TOTAL` on
the principal column and `PAYMENTS THRU 2007` on the interest column, so the names read
`TOTAL PRINCIPAL` and `PAYMENTS THRU 2007 INTEREST` and `PAYMENTS PRINCIPAL` matches nothing.
AMOUNT - TOTAL PRINCIPAL = BALANCE closes on all 10 issues; the TOTAL row is off $1
(35,610,615 - 7,206,877 = 28,403,738, printed 28,403,737).

## 3. Treasurer's cash: skip the reconciliation block (`emit_treasurers_cash`)

**Change.** Take accounts only from rows AFTER the row labelled `CURRENT CASH INVESTED:`, when
the table has one; record the block above it (balance 6/30/06, receipts, disbursed, general
ledger balance 6/30/07) as a reconciliation identity in the note.

**Why.** p73 prints, above the account list, `BALANCE JUNE 30,2006 $6,651,744.00 / RECEIPTS
7/1/06-6/30/07 34,618,168.48 / DISBURSED (31,322,079.46) / GENERAL LEDGER BALANCE 6/30/07
$9,947,833.02`. The emitter counts RECEIPTS and DISBURSED as accounts, so it sums 13,243,922.04
against 9,947,833.02 and refuses the page (0 rows; page state `refused`). Both identities close
by hand: the 31 accounts sum to 9,947,833.02 = the printed `TOTAL`; and 6,651,744.00 +
34,618,168.48 - 31,322,079.46 = 9,947,833.02 = the printed general ledger balance. 2010's p68
prints no such block, which is why the emitter never met it.

## 4. Tables with no money figure lose their first row (`records()`)

**Change.** A map column `header_rows` (0 = the table prints no header row) that `records()`
honours instead of `head, body = rows[:1], rows[1:]`.

**Why.** For a table with no money figure, `records()` takes row 1 as the header. On these
tables row 1 is DATA, and it is lost (each map row's note names the lost row):
p8 t1-5, p9 t1-10, p10 t1-5 (appointees), p14 t2 (`Nursing Visits | 795`), p15 t1-4 (`560`,
`20` -- a stated total --, `357`, `17`), p18 t1 (the whole Conservation Commission: a one-row
table), p20 t1 (Planning Board), p25 t1 (`Fires | 61` -- the Total row 1766 lands without it),
p27 t1 (`Abandoned 911 calls | 140`), p37 t1 (School Committee chair). Set `header_rows=0` on
those rows of map.csv once the column exists.

## 5. Two tables NOT LANDED that need a by-eye header or a text emitter

- **p55 t4, Assessor's Account for Exemptions and Abatements (overlay).** The PRINTED heads are
  misaligned on the page itself (checked on the scan): `FY2005 FY2004` run together over the
  second figure column, `FY2003` over the third, nothing over the fourth. Naming columns from
  the header would put FY2003 on the FY2004 figures. Needs a header override per (page, table):
  cols 2-5 = FY2006, FY2005, FY2004, FY2003 -- the order the heads are printed in, which is
  itself an inference about a misprinted page and should say so in `column_meaning`.
- **p43 t2, Turkey Hill MCAS placement among Massachusetts schools** (`136 of 565`, `top 24%`
  by grade and subject). A RANK, so it needs its own `table_family` (`mcas-rank`) in
  report-enrollment-mcas. No cell parses as a figure except the grade, so the four rows whose
  grade cell is blank are read as group headings: landing it would land 3 of 7 rows.

## 6. Out-of-district placements, printed in prose (`placement-counts.csv`)

The 2007 report prints the quantity `placement-counts` holds, in prose on PDF page 50 (Special
Services, Elaine E. Blaisdell): *"Of the total number of students receiving services, eight
students received services outside the district during the 2007/2008 school year. Of the eight
students, seven are in day placements and one is in residential placement."* Also on the page:
263 students with disabilities (14.5%), and 78 students on 504 plans. Proposed row:

    fy=2008, as_of=(not printed -- "during the 2007/2008 school year"), total=8, day=7,
    residential=1, collaborative=(not printed), parts_tie=yes (7+1=8), page=50,
    document=4515-2007-annual-town-report.pdf, checks="parts 7+1=8 ties to stated 8"

Caution: the FY2013-FY2025 rows are SIMS Report 7 counts as of 1 March. This one names no
source and no date, so it is the same quantity at an unknown date and must say so.

## 7. Births and marriages: a decision for TJ, not a mapping

p80-81 print every 2007 birth with the child's name, birthplace and both parents' names; p82-83
every marriage with names, full dates of birth and residences. The FY2012+ reports print only
counts, on the Registry of Vital Records' advice. They are NOT LANDED. Landing names of children
and dates of birth in a searchable database is a publication decision (rule 13e's quasi-identifier
reasoning applies even though the report itself is public). Counts could be landed instead.

## 8. Not captured anywhere, no table to read

- PDF p58 `GENERAL FUND REVENUES FY 07` and p65 `GENERAL FUND EXPENDITURES FY 07`: pie charts
  printed as percentages (property taxes 61.38%, state-local aid 26.36%, ...; education 55.56%,
  debt service 9.73%, ...). Textract found no table; the labels and percents are in the lines.
- The omnibus vote (p89) itemises its sources: raise and appropriate $23,925,685.00 + free cash
  $106,941.00 + Article 22 transfer $22,358.00 + septic receipts $10,872.00 + sewer betterment
  fund $680,080.00 = 24,745,936.00. The p91 table prints `Total Omnibus $24,673,945.00`. Both
  are recorded as printed; nothing here says which is right.

## Integration pass, 28 October 2026

What the one integration agent did with each item above. Counts are this folder's rows after
`read_report_tables.py`; the reasons for anything not applied are here so nobody re-asks.

- **1 trust-funds identity.** APPLIED as written (disbursements added, REALIZED G/L not a term). 41 of 51 rows `checked` (was 28); the 10 failures are the round-hundred differences the worker named, the subtotals carrying them, and a few the identity does not close.
- **2 debt-by-issue `TOTAL PRINCIPAL`.** APPLIED. report-debt 2007: 100 checked, 6 failed (was 82 / 16).
- **3 treasurer's cash: skip the reconciliation block.** APPLIED: the block lands in `report-treasurers-cash-reconciliation` (4 rows, `checked`); the 31 accounts publish against the printed TOTAL 9,947,833.02. p73 was `refused`; it is now read.
- **4 tables with no money figure lose their first row.** APPLIED generally: a first row that reads as data (a text cell and a number, in either order) is data; Textract's empty first row is taken as the missing header. The officials tables, p14/p15/p18/p20/p25/p27/p37 rows are recovered.
- **5 p55 t4 misaligned heads; p43 t2 MCAS rank.** NOT APPLIED: both need column names by eye per table, which is an inference about a misprinted page; left NOT LANDED.
- **6 placement count in prose.** NOT APPLIED -- prose figures (placement counts, vital-record counts, fire incidents, capital plan prose, pie-chart percentages) need a prose reader; no table reader can land them. `placement-counts` is SIMS-sourced and dated 1 March; these sentences name a school year and no source, so adding them is a decision about mixing two measurements, not a mapping. Recorded here with their pages; nothing was inferred.
- **7 births and marriages.** NOT APPLIED -- a decision for TJ, not a mapping: named births (infants, parents) and marriages (dates of birth) stay NOT LANDED.
- **8 pie charts, omnibus sources.** NOT APPLIED -- prose figures (placement counts, vital-record counts, fire incidents, capital plan prose, pie-chart percentages) need a prose reader; no table reader can land them. `placement-counts` is SIMS-sourced and dated 1 March; these sentences name a school year and no source, so adding them is a decision about mixing two measurements, not a mapping. Recorded here with their pages; nothing was inferred.
