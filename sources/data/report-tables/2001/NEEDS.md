# 2001 edition: what the integration pass needs to change

Written by the 2001 worker, 28 October 2026. Nothing here was changed in a shared file; every item
is a change to `scripts/read_report_tables.py`, `validate_totals.py`, a shared dataset, or a
decision. PDF pages throughout (printed folio = PDF page - 3).

## 1. Dataset registrations (two NEW datasets)

| dataset | family | pages | rows | what it is |
|---|---|---|---:|---|
| `report-cash-reconciliation` | `cash-reconciliation` | 68 (table 1) | 8 | The Treasurer's cash FLOW for FY2001: balance 6/30/00, receipts less investments transferred, disbursed less revenue cash invested, general ledger balance. `treasurers-cash` holds only closing balances by account. |
| `report-warrant-article-amounts` | `master-capital-facilities-plan` | 82 (table 3) | 9 | Per-project amounts printed inside a warrant article: Article 8, 5/12/2001 ATM, a $41,190,000 Master Capital Facilities Plan (eight buildings), **PASSED OVER**. A proposal, never an appropriation. |

Both go through `emit_generic` (GENERIC columns). They need `build_db.py` / `merge_report_tables.py`
registration and a `map_annual_report_pages.PROOF` entry if they are to prove a page
(`warrant-article-amounts`: column total, `TOTAL` closes 41,190,000 -- all 9 rows `checked`).

A new FAMILY in an existing dataset: `trust-funds-summary` (p74 table 2, report-trust-funds) -- the
fund balances grouped by purpose. A different grain from `trust-funds`; never sum the two.

## 2. Treasurer's cash: the accounts tie, the emitter cannot see the total (p68)

`emit_treasurers_cash` refused p68 table 2 (`printed none read`). The 18 accounts sum to
**2,958,339.00**, which the page prints twice: `GENERAL LEDGER BALANCE $2,958,339.00` (table 1, row 9)
and a lone figure in column 3 under the list (table 2, row 19). Neither reaches the emitter: the
lone figure is in a column holding ONE value, so `figure_cols` (n >= 2) does not count it, and the
row becomes a group label `$2,958,339.00`.

Change: let `emit_treasurers_cash` take its total from (a) a row whose only content is one parsed
figure outside the figure columns, or (b) a `stated_total` in map.csv (`2958339`, cited to p68 t1 r9).
Same one-figure-column loss on p68 table 1: `$30,518,885.00` (column 4) lands as a group label.

## 3. Tables with no money figure lose their FIRST ROW to the header

`records()`: when no row holds a money-formatted figure, `head, body = rows[:1], rows[1:]`. On these
pages row 1 is DATA, and it survives only as `columns_as_printed` / `column_meaning` text:

- p20 tables 1-9 (fire incidents): each table's first row is its category total -- `FIRES 58`,
  `ALARMS 74`, `MUTUAL AID 26`, `EMERGENCY MEDICAL CALLS 636`, `RESCUE CALLS 7`, ...
- p22 (police crimes): `ASSAULT AND BATTERY 44`
- p30, p31 (Nashoba): `Housing & Nuisance Investigations 12`, `Students Eligible 388`

2010's p20 has the same loss. Change: treat row 1 as header only when it parses to no figure in
the columns that hold figures below it; otherwise `head = []`.

And the opposite on p37 (enrollment): the printed header `School/Grade | 10-01-99 | 10-01-00 |
10-01-01` is ROW 3; rows 1-2 are the title and a blank. So `column_meaning` says `not established`
and the date row lands as a row with three unparsed cells. Change: a `header_row` column in
map.csv (here `37/1: 3`).

## 4. Non-numeric cells in a figure column are dropped (p79 deaths)

`DEATHS - 2001` prints the month (`JUNE`, `JULY`, ...) as a row in the DATE column. That column is a
figure column (day numbers), so the month row has no label, no figure, and is skipped: the 65
death rows carry the DAY and the AGE but not the MONTH. (p13's burials list prints its months in
the NAME column and keeps them as `group`.) Change: a text-only row whose only cell sits in a
figure column should set `group`.

## 5. Accountant's schedule: subtotals print with NO label (p55-60)

Each department block ends in an unlabelled row (`| $82,652.00 | | $82,652.00 | $79,637.12 |
$1,392.00 | $1,622.88`). `validate_totals` sees it as an item, so the GRAND TOTAL check sums items
AND subtotals: TOTAL EXPENDED printed 16,382,445.79, rows sum 29,013,805.47. That one open total is
why 164 of 237 accountant-schedule rows are `check failed` -- a reader failure, not 164 bad
figures. The subtotal rows themselves are `checked` by the row identity
(BALANCE TO REVENUE = AVAILABLE - EXPENDED - ENCUMBERED).

Not solved here: summing only the rows that print TOTAL FUNDS AVAILABLE gives 18,084,494.65, still
not 16,382,445.79, because labelled section totals (`Total Insurance` 1,657,672.00, p60) sit in
the same column. The block structure needs: unlabelled row after a block = subtotal of the block;
`Total <section>` = sum of its subtotals.

## 6. Omnibus budget: two columns per page, read as four tables out of order (p81-82)

Textract split the FY2002 omnibus into 81/1 (lines 1-33), 81/2 (51-...), 82/2 (34-50), 82/1
(81-88). Subtotals span tables (`Subtotal Fire Dept.` 494,316.00 is on 81/2, its lines partly
elsewhere), so 17 rows fail on grouping. The article states the total in prose:
`VOTED UNANIMOUSLY to raise and appropriate $17,240,722.00` (p81), and the page prints
`Total Omnibus Budget $17,240,722.00`. My own sum of the numbered lines that parsed is
16,966,172.00 + line 14A 35,000.00; lines 12 (`$-0-`), 44, 56 (UMAS `242-3`), 58 (`$-0-`) and 75
did not parse cleanly. Change: order the four tables by line number before validating, and check
the omnibus against `stated_total` (now in map.csv for all four tables, unused by `emit_generic`).

## 7. Trust funds: a 2001 layout the identity table does not know (p72-74)

Columns are `ACCOUNT | ALLOCATION | BEG BAL 6/30/00 | DIVIDENDS | CONTRIBUTIONS | REDEMPTIONS |
BOOK BALANCE`. No `ENDING CASH`, so `IDENTITIES['trust-funds']` does not apply. The book balance
is NOT a row identity: a principal fund's DIVIDENDS are credited to its `... INT` account
(PERP CARE BEQ INT: 3,359.49 + 226.70 own + 6,510.28 from PERPETUAL CARE BEQUEST - 3,323.28 =
6,773.19). Rows with no `INT` partner do foot (`STABILIZATION PEOPLES BANK` 408,764.58 + 24,309.41
= 433,073.99). An identity would have to pair rows; leave `no check` until someone writes that.
The 31 `check failed` rows are the DIVIDENDS column at `TOTAL COLONIAL` (p72): printed 11,625.50,
rows sum 11,614.39, triaged `printed_error`.

## 8. A placement count printed in PROSE (p49) -- for `placement-counts`, not a gap

p49 (Office of Instruction): *"Eight students from our community are educated outside our schools:
three are served in collaborative placements, three in a day programs, and one in a residential
program."* The parts sum to **7**, not 8 -- the same parts-sum-to-total check `placement-counts`
already runs would FAIL. No measurement date is printed ("Currently"). Also on p49: 13.5% of the
student population identified with a disability, and 2.5% more under Section 504 plans. Not in any
table, so not in map.csv. Change: a `placement-counts` row for edition 2001, page 49,
`check failed` (3 + 3 + 1 = 7 vs 8).

## 9. Decision for TJ: per-person births and marriages (p75-78)

The Town Clerk printed every 2001 birth (date, infant's name, birthplace, both parents' names) and
marriage (date, both parties, dates of birth, residences). FY2011-FY2025 land only the COUNTS.
Mapped NOT LANDED pending a decision on whether named infants and parents go into a searchable
database. Deaths (p79, name and age) ARE landed, as 2010 landed its burials list.

## 10. Smaller

- Percent cells (`78%`) do not parse, so the MCAS performance-level tables (p45-48) carry their
  percentages in the row label, as 2010 p43 did. `239,5` (p45 t2, Grade 4 2001 Overall) is unparsed.
- p54 and p61 are pie charts (`GENERAL FUND REVENUES FY 01`, `GENERAL FUND EXPENDITURES FY 01`)
  with percentages only; Textract found no table, so they are not in map.csv or pages.csv.
- Election misreads recorded as `check failed`, figures left as read: p90 `Frederick J. Liatsis`
  PREC D `36` (TOTAL 2030 needs 136), and two `Blanks` rows off by 1 and 3.
- Debt repayment p70: `2018` column at the Mass Water Pollution Trust 04/29/98 issue is off 10.00
  (triage: one digit, `$10,858` -> `$10,868`); `GRAND TOTAL INTEREST` is summed against the wrong
  block (grouping), because the issue names print on the TOTAL row of the issue above.

## Integration pass, 28 October 2026

What the one integration agent did with each item above. Counts are this folder's rows after
`read_report_tables.py`; the reasons for anything not applied are here so nobody re-asks.

- **1 two new datasets.** APPLIED: `report-cash-reconciliation` RENAMED to `report-treasurers-cash-reconciliation` (one name across 2001-2008); `report-warrant-article-amounts` kept. `trust-funds-summary` kept as a family; the book layout is now family `trust-funds-book`.
- **2 treasurer's cash total (p68).** APPLIED: the unlabelled lone figure under the list is the total; 18 accounts publish. (`stated_total=2958339` also set.)
- **3 first rows lost; enrollment header row 3.** APPLIED (see 2007 item 4; a row of dates is the header).
- **4 months in a figure column (p79).** APPLIED: a month printed in a figure column becomes the `group` of the rows under it.
- **5 unlabelled accountant subtotals.** NOT APPLIED -- a change to validate_totals' block walk (table order, cross-page grand totals, unlabelled department subtotals). validate_totals is shared with the FY2011/FY2020 reviews, and the parser changes that WERE made there were proved not to alter one check of those reports; a block-walk change could not be proved the same way in this pass.
- **6 omnibus table order.** NOT APPLIED -- a change to validate_totals' block walk (table order, cross-page grand totals, unlabelled department subtotals). validate_totals is shared with the FY2011/FY2020 reviews, and the parser changes that WERE made there were proved not to alter one check of those reports; a block-walk change could not be proved the same way in this pass.
- **7 trust funds 2001 layout.** As asked: no identity.
- **8 placement count in prose.** NOT APPLIED -- prose figures (placement counts, vital-record counts, fire incidents, capital plan prose, pie-chart percentages) need a prose reader; no table reader can land them. `placement-counts` is SIMS-sourced and dated 1 March; these sentences name a school year and no source, so adding them is a decision about mixing two measurements, not a mapping. Recorded here with their pages; nothing was inferred.
- **9 births and marriages.** NOT APPLIED -- a decision for TJ, not a mapping: named births (infants, parents) and marriages (dates of birth) stay NOT LANDED.
- **10 smaller.** Percents APPLIED (`[percent]`); the pie charts and election misreads unchanged.
