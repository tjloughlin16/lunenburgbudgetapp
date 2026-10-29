# 1999 edition: what the integration pass needs to change

Written by the 1999 worker, 29 October 2026. Nothing here was changed in a shared file; every item
is a change to `scripts/read_report_tables.py`, `validate_totals.py`, a shared dataset, or a
decision. PDF pages throughout (printed folio = PDF page - 3 through p107; see item 1).

No NEW dataset was needed: every table in cells.tsv maps to an existing dataset and family, or is
NOT LANDED with its reason (p5 town facts and office hours). One new FAMILY in an existing
dataset: `gross-wages-school` (item 2).

## 1. The PDF is missing printed folios 105 and 106 (school wages)

PDF p107 carries folio `104` and ends at `Gloria A O'Brien`; PDF p108 carries folio `107` and opens
at `Tamara L Yourk`. Every other folio from p55 to p107 runs PDF - 3 without a break (checked on
the bottom line of each page in lines.tsv). The 278 school rows sum to **6,018,558.34**, exactly the
sum of every `$` figure in the lines of p103-108 less the total, against the printed
`TOTAL SCHOOL GROSS WAGES $8,198,325.62` -- short **2,179,767.28**, the two missing pages.

Not a reader defect: a document defect. It wants a row in whatever register records an incomplete
source (`document-defects.csv`?), and the remedy is another copy of the 1999 report (Town Clerk,
Ritter Memorial Library). It also means any school-wage figure for 1999 covers surnames A-O'Brien
and Yourk-Z only.

## 2. Wage emitter: two lists, two totals; STEP is a label

- **Two printed totals.** 1999 prints a TOWN list (p100-102, `NAME | POSITION | DEPT | GROSS`,
  `TOTAL TOWN GROSS WAGES $2,309,939.34`) and a SCHOOL list (p103-108,
  `NAME | POSITION | DEGREE | STEP | GROSS`, `TOTAL SCHOOL GROSS WAGES $8,198,325.62`).
  `emit_wages` sums every wage row of the edition against `stated[-1]`, so giving either total as
  `stated_total` produced a false note (429 rows vs one list's total). The map carries NO
  stated_total; both totals are in the map notes. Change: sum per `family` (or per map
  `stated_total` run) against that run's own total. Tested by hand: town rows sum to
  **2,309,939.34 = printed** (152 rows); school as item 1.
- **STEP read as a figure.** On 86 school rows a numeric STEP (`11`, `3`, `2`) lands in v1 and the
  GROSS in v2 (column_meaning says `v1=STEP | v2=GROSS` per row, so nothing is mislabelled, but a
  consumer reading v1 as gross is wrong). `MAX` steps are text and go to the label, as does DEGREE.
  Change: a column headed `STEP` (and `DEGREE`) in a wage table is part of the label, never a
  figure. With that fixed, coverage on p103-108 should pass (all 6 pages fail coverage now only on
  these step cells: e.g. p103 `12 not captured, 12 captured not in the text` = its 12 step rows).
- New family `gross-wages-school` in `report-gross-wages`: same quantity (gross pay per employee),
  different printed layout, separate total. Rename if the integration pass prefers one family.
- Period: NEITHER list names a year (`REPORT OF WAGES PAID`). Calendar vs fiscal is not printed.

## 3. Treasurer's cash refused on a footnote mark (p85 table 2)

`FLEET MONEY MARKET ($96,703.00) *` -- the trailing `*` (footnote: `INVESTED MONIES NOT TRANSFERRED
UNTIL CHECKS ARE ACTUALLY DISBURSED`) leaves the cell unparsed, so the accounts sum 2,062,230.00
against the printed 1,965,527.00 and the emitter refuses. With -96,703.00 read, the 18 accounts sum
to **1,965,527.00** exactly, the `GENERAL LEDGER BALANCE` of table 1 and the lone figure under the
list. Change: add a trailing ` *` / `*` footnote mark to `validate_totals.REPAIRS` (alongside the
trailing `+`). `stated_total=1965527` is already in the map.

## 4. A decimal comma in a share (p83 table 1)

`G HUBBARD CONS | 0,00060` (ALLOCATION column) is unparsed, so the allocations sum 0.99940 against
`TOTAL COLONIAL: 1` and all 21 Colonial rows are `check failed`. The triage's suggestions
(`0.46220 -> 0.46280` ...) are wrong about the cause. Change: in a column of fractions below 1,
read `0,ddddd` as `0.ddddd` (REPAIRS). The same rows also fail DIVIDENDS by one cent
(16,140.25 vs printed 16,140.26), which would still fail, honestly.

## 5. Row identity: collection of taxes WITHOUT an ADJUSTMENTS column (p84)

1999 prints `TAX | FORWARD | COMMITMENTS | REFUNDS | PAYMENTS | ABATEMENTS | TAX TITLE | BALANCES`
-- no ADJUSTMENTS. The `collection-of-taxes` identity names ADJUSTMENTS, so it is not applied and all
32 rows carry an empty `proof`. Tested on the emitted rows: FORWARD + COMMITMENTS + REFUNDS +
PAYMENTS + ABATEMENTS + TAX TITLE = BALANCES closes on **32 of 32**. Change: a second identity with
`{'absent': ['ADJUSTMENTS']}`. The page also prints a GRAND TOTAL row (r43) no emitter checks.

## 6. Cross-page block in a trust book printed out of order (p82, p83)

Folio 79 (PDF p82) CONTINUES folio 80 (PDF p83): the Century accounts start at the foot of p83 and
end on p82 with `TOTAL CENTURY:` and `GRAND TOTAL TRUST FUNDS: 839,978.68`. The validator cannot
reach the p83 rows from p82, so both totals failed as `grouping`; p82 is `checks=none` in the map.
By hand: Century BEG BALANCE 17,278.40 (p83 r45-62) + 85,702.59 (p82) = **102,980.99** = printed;
GRAND TOTAL = Colonial 276,526.00 + PBHG 5,207.61 + MMDT 6,701.36 + Stock 978.48 + Stabilization
428,860.64 + Century 121,704.59 = **839,978.68** = printed. Change (if wanted): let a map row name a
`continues` page so a run can be summed across pages in a stated order.

Also on p82: the `SUMMARY OF FUNDS` (CEMETERY 235,770.80 ... STABILIZATION 428,860.64 ... STOCKS
978.48, `GRAND TOTAL TRUST FUNDS: 839,978.68`) is in lines.tsv but Textract returned NO table for
it. It is 2001's `trust-funds-summary` family. Not read any other way, per the brief. If the
integration pass reads a table from lines, this is the one.

## 7. Average columns are not sums (p55 table 3)

`Property Class Code and Description | Valuation | Accounts | Average Value`: the validator sums
AVERAGE VALUE down to TOTALS (123,900) and fails all 14 rows. Valuation and Accounts closed at
TOTALS on that run. The map sets `checks=none`, so the table is `no check`. Change: exclude a column
headed `Average` / `Avg` from column checks; 2001's `Avg. Value` was not summed.

## 8. Overlay identities (p56 table 1), offered, not needed

`Total Potential Charges` = `Charges to 6/30/99` + `Potential Liability` (`-`), and `Assessors
Overlay` - `Total Potential Charges` = `Overlay Excess/Shortfall`. Tested on the cells: the second
closes in 4 of 5 years; FY1997 prints 44,704 against 122,992 - 78,287 = 44,705 (the page's own
rounding or a misread). Rows are `no check` now.

## 9. Omnibus budget account numbers (p97)

Headerless (`header=none`); the account number lands in v1 where it is a plain integer (`122`,
`4115800`) and in the label where it is not (`122.1`, `242/243`, `429-210`), so v1 means two things
across rows (`column_meaning` says `not established`). The column check to `TOTAL BUDGET VOTED
$14,726,852` closes and all 89 rows are `checked`. Change: let `id_columns` accept dotted, slashed
and hyphenated line numbers (`ID_TEXT`). The vote's three sources tie: 149,812 + 100,000 +
14,477,040 = 14,726,852.

## 10. Accountant schedule GRAND TOTAL (p60-66): grouping, as in 2001

Department subtotal rows print no label, so the validator sums detail AND subtotal rows to the
GRAND TOTAL (TOTAL EXPENDED rows 26,212,423.47 vs printed 14,484,116.19). 136 rows are `check
failed` for this; the per-row BALANCE identity closes on 152 rows. Same shape as 2001's p55-60.

## 11. Placement counts are printed (p52), in prose

`placement-counts` holds FY2013-FY2025, and 2010 registered a gap for it. 1999 PRINTS it, p52:
*"Nine students from our community are educated outside our schools: four are served in
collaborative placements, three in day programs, and two in residential programs."* Not a
financial table, so not read here; for whoever extends `placement-counts` backwards. Parts sum to
the total (4 + 3 + 2 = 9). The date is not stated in the sentence; the section is the 1999-2000
school year report.

## FINDER MISSES

**None.** All 50 pages `find_financial_pages.py --list 1999` picked were sent for tables (0
unread). 36 returned tables; 14 returned none (p11, 12, 15, 19, 20, 23, 88, 89, 93-96, 98, 99:
department prose and warrant articles with dollar amounts in sentences). Every unpicked page with a
`$` in its lines (p14, 16, 18, 24, 53, 90, 92: one or two figures each) holds them in prose. p59
(`GENERAL FUND REVENUES FY 99`) and p67 (`GENERAL FUND EXPENDITURES FY 99`) are pie charts with
percentages and no money figures -- not tables.

## ROSTER PAGES

For `dump_roster_pages` (none has cells; none was read):

| PDF page | what |
|---:|---|
| 40 | Lunenburg High School staff by department (`UNIFIED ARTS`, `LIBRARY MEDIA SPECIALIST`, `SCIENCE`, `MATHEMATICS`, ...) |
| 43 | Thomas C. Passios Elementary School: school council (1998-1999) and `FACULTY` |

Also, not school rosters: p27 `ROSTER OF FIREFIGHTERS` (officials, as 2001), p37 School Committee
membership, p7-9 elected and appointed officials. The wage lists (p100-108) name every town and
school employee with a position; they are landed in `report-gross-wages`.

## What the integration pass did with each item (29 October 2026)

Applied ONCE in the shared code (see `sources/data/report-tables/README.md`, "Added by the 1991-2000 integration pass"); counts are this folder's rows after the re-run.

- **1 printed pages 105-106 absent from the PDF**: REGISTERED in `sources/data/document-defects.csv` (folios re-checked: PDF p105-108 print 102, 103, 104, 107). The school rows carry the shortfall: 278 rows = 6,018,558.34 against 8,198,325.62 printed, short 2,179,767.28.
- **2 wages**: APPLIED (STEP is label; one total per list, `stated_total` set on p102 and p108; families `gross-wages-town`, `gross-wages-school`). Town 151 rows = 2,309,939.34 = printed. 431 of 431 rows `checked` on coverage.
- **3 trailing ` *`**: APPLIED. Treasurer's cash published, 18 accounts = 1,965,527.00.
- **4 `0,00060`**: APPLIED; the 0.01 DIVIDENDS miss remains, honestly.
- **5 taxes without ADJUSTMENTS**: APPLIED.
- **6 trust book printed out of order; summary of funds from lines**: NOT APPLIED (validator; no lines reader).
- **7 AVERAGE column**: APPLIED; `checks=none` dropped from 55/3.
- **8 overlay identities**: NOT APPLIED (offered, not needed).
- **9 dotted/slashed account numbers**: APPLIED.
- **10 accountant GRAND TOTAL grouping**: NOT APPLIED (validator block walk).
- **11 placement count in prose (p52)**: NOT LANDED, for the reason in 1997 item 9 (no `as_of` date, no SIMS source printed).
- **ROSTER PAGES**: p40, p43 read into `sources/data/rosters/1999-p*.json`.
