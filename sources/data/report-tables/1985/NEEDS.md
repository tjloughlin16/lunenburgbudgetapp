# 1985 edition: what the shared code needs (for the integration pass)

Edition: calendar 1985 annual town report, `4485-1985-annual-town-report.pdf`, 172 pages. Tables were read on the 59 pages
`find_financial_pages.py --list 1985` picked; Textract returned tables on 45 of them (tables.csv). The other 14 picked pages
are prose with dollar figures (departments, warrant articles, the Moderator's minutes). Folder opted in to everything
1986 uses: `unlabeled_subtotals`, `rounding_tolerance_usd: 1`, `stacked_pairs`, `accountant_marks`, `id_column_words`,
`recon_net_on_transfer_line`, `receipts_span`. Every hand check below was computed from the cells
(`build/textract/out/4485-1985-annual-town-report.cells.tsv`) or the lines, not typed from the page.

## FINDER MISSES: 0

Pages with 6+ money figures in `lines.tsv` that are NOT in the finder's list: none (the nine pages with 6+ figures and no
table, 22, 30, 83, 86-89, 91, 92, are all in the list and are prose). Bounds the misses; does not prove zero.

## ROSTER PAGES

p34 `ROSTER OF FIREFIGHTERS OF 1985`; p145-146 the School Department's `RESIGNATIONS DURING 1985` and `ON LEAVE OF ABSENCE
DURING 1985`; p147-159 `School Personnel Listing 1985-86` (clerical, teaching, nursing, custodial and cafeteria staff).
All written to `rosters.csv`. p162 prints staff in FTE by role (landed as `report-school-staff-fte`), which is not a roster.

## CELLS MISSING ON PICKED PAGES (rule 13c: the table was returned, the lines of it were not)

1. **p56 left column (the statement of receipts, second half).** Textract returned only the right-hand column as 56/1 and a
   four-row fragment as 56/2. The left column (Town Clerk's fees, the Treasurer's investment lines, protection permits,
   health, street betterments, the four articles) is in `lines.tsv` (p56 lines 1-206) and in no table, as is the start of
   the Town Clerk's block that p55/2 breaks off (`Cert. Copy Birth, Death, Marriage 676.00`). THE STATEMENT TIES WITH THEM:
   the 19 unlabelled section subtotals of p55 (8,664,100.64) plus the 9 of the right column of p56 (384,394.35) plus the left
   column's printed subtotals read from the lines -- Town Clerk 26,887.55, Treasurer 12,727,793.50 (= 12,578,430.32 +
   118,267.45 + 1,500.00 + 25,508.59 + 4,087.14), protection 109,151.31, health 12,833.07, street betterments 35,500.00,
   Art. Fire Truck 140,000.00, Art. Wheel Chair Lift 31,000.00, Art. School Roof Repair 70,000.00 -- sum to 22,201,660.42,
   the printed TOTAL RECEIPTS, to the cent. So the 132 `annual-report-receipts` rows are `check failed` (accounts 8,801,969.57
   vs 22,201,660.42) for ONE reason, lines that are in no cell, and nothing else. Nothing is typed into the rows.
   What would settle it: a re-read of p56 that returns the left column as a table.
2. **p57 table 1, the payments statement's two panels.** Not landed (map says so). The left panel puts label AND amount in one
   cell (`Selectmen's Administ. 39,052.64`), the right is label | amount | subtotal. The reader drops the left panel's
   embedded amount and hangs the right panel's section names on the wrong lines, so landing it would publish about half the
   lines under wrong headings. Needs a reader that splits a panel's embedded amount (the wage-list reading of a figure sharing
   a cell with its label, applied to a payments panel). 58/1-2 land; 58/3 returned seven blank rows after one line
   (`Audit of Municipal Accounts 14,860.00`) and the subtotal 397,330.71, also NOT LANDED. TOTAL PAYMENTS 22,187,605.68 is
   printed on 58/2 and is the Treasurer's reconciliation `Disbursements` line (54/1), so the statement is complete on the page.

## 1. Readings that would help (CALENDAR_REPAIRS), each measured on this edition

- **A footnote letter in brackets after a figure**, `$ 978.48(A)` (p14 table 4 row 1). The cell is unparsed, so the trust
  custody list sums to 538,375.74 against its printed TOTAL $539,354.22: short by exactly 978.48 (5 rows `check failed`).
- **Two `$` before a figure**, `$ $ 111,474.00` (p64 table 2 row 1, Federal Grants): the figure is lost; the total 250,720.79
  = 111,474.00 + 8,229.50 + 131,017.29 would close with it.
- **A `$` in front of a stacked principal-and-interest pair**, `$ 65,000. 4,095.` (p65 table 1 row 2, Middle School): the pair
  is not split, so the MIDDLE SCHOOL principal and interest rows hold no values and the TOTAL and GRAND TOTAL columns fail
  with `rows sum 0.00` (7 `check failed` rows, all fed by that one row; the other issues close). Also `$` alone in the empty
  year cells of that row.
- **A thousands separator printed as a full stop, in cents**: `226.811.97` (p63 table 2 row 7, revenue sharing total) and a
  stray extra digit `130,0000.00` (p63 table 3 row 3). Not repaired here.
- **Misread digits on p64 table 1** (the revenue sharing reconciliation): `250,720.70` for the Disbursements line, whose total
  on the same page is 250,720.79, and `(179.703.50)`, where 250,720.79 less 131,017.29 is 119,703.50. HYPOTHESIS only (a
  digit and a separator misread); the 10 rows are `check failed` as read. The glyph witness could decide.
- **A label running into its figure**: `Local Aid Add. Assistance256,524.00` (p55 table 1 row 43), `Insurance25,951.38`
  (p55 table 2 row 18), `Elections, Registration, Census6, 761.95` (p56, lines).

## 2. Row identity for the accountant's schedule (p72-77): `BALANCE TO FY`

The 1985 carry-forward column is headed `BALANCE TO FY 85`; the identity in `IDENTITIES['accountant-schedule']` matches
`BALANCE FY`, so all 216 schedule rows read `no check`. The same identity as 1991's -- BALANCE REVENUE = TOTAL FUNDS AVAILABLE
- TOTAL EXPENDED - BALANCE TO FY, blank read as zero on a row printing an AVAILABLE figure, `absent: ['ENCUMBERED']` --
measured here by hand on the rows: 148 of 156 rows printing a TOTAL FUNDS AVAILABLE close. The eight that do not are wrapped
labels (`Accept Pine Acres & | Hickory Lane`, `Accept Sandycove, Cove Road & | Cove Terrace`, `of Refuse`), one line printed
across two cells, and rows whose expended figure sits in a neighbouring row. Change: let the 1991 entry's `BALANCE FY` match
`BALANCE (?:TO )?FY`. Headers: pages 74, 75, 77 start with a data row inside the header, so the map gives them `header=none`
and `header_from=73/1`; page 72 has `header=row:1`.

## 3. Other defects found, not repaired

- **p164 (school budget summary): parenthesised series totals read as negative.** `($121,879.)` is the POSITIVE sum of the
  series' lines (99,379 + 22,500); the reader reads parentheses as negative, so the six series rows carry the wrong sign
  (v2-v3 negative) and the FY-85 appropriation cell of each is unparsed. `checks=none` in the map. Needs: a parenthesised
  amount on a series-header row is a positive subtotal.
- **p165-168 (special accounts):** the account title cell carries the opening balance and receipts as prose, as in 1986's
  p113-115; the figures sit in the label, not in columns.
- **Group labels on p58:** the reader's section heading carries past the section it names (`Debt and Interest:` over the
  `Petty Cash Advances` line; `Investments:` over the `1984 Warrants Payable` line and TOTAL PAYMENTS). A property of the
  emitter's grouping, as in 1986 p38-39; the figures are right.
- **p104 table 2 (tuition rates):** two rate sets are printed one under the other (effective 1 January 1985 and the rate
  beneath it); the second set's heading is not a cell. Landed as printed, `report-fee-schedule`, family `school-tuition-rates`.

## 4. Privacy

- No named births. The 1985 report's vital-records pages were not sent for tables.
- `report-vendor-payments`: this report prints NO payments-over-$4,000 list (searched for `4,000`, `contracts`, `40, s. 4G`
  in the text); 1986 is the first edition with it.
- `edition.json` `withheld_rows`: ONE line, p70 table 2 row 16, a scholarship grant printed against a named individual.
  Named bequest and prize funds (`Worthy Poor`, library bequests, the prize funds) are fund names and follow 1986's precedent.
  No name repeated here.

## 5. New datasets in this edition (names for the integration pass to settle)

- `report-school-monies-returned` (p163): money the School Department collected and returned to the Town, by source, in two
  half-years and a FY-85 total. An actual, a flow. Cell `(CYR) 54.00` carries a footnote tag.
- `report-school-budget-summary` (p164): the School Committee's own summary of the general appropriation by account series
  (FY-85 appropriation, amendment, expenditures; FY-86 request). MIXES STAGES across columns (rule 1); never differenced.
  Possibly the same quantity 1986 p112/2 (`report-school-state-aid`) starts from, but that table is state aid, a different
  quantity.

Not new, but reused from 1986: `report-fund-balance-sheets`, `report-statement-of-payments`, `report-revenue-sharing`,
`report-auditors-cash-schedule`, `report-school-staff-fte`, `report-school-special-accounts`,
`report-treasurers-cash-calendar-year`, `report-property-tax-exemptions`.

## Integration pass, 30 October 2026: what was done with each item

- **Privacy:** TJ, 30 October 2026: *"Yes publish. Everything in the annual reports is public."* `withheld_rows` is removed from this folder's `edition.json`; the rows it held are published. (The reader's mechanism stays, unused, for a takedown.)
- Cells missing (p56, p57): NOT APPLIED -- a re-read, not a reader rule.
- 1: `(A)` and `$ $` APPLIED, always on (CALENDAR_REPAIRS). `$` before a stacked pair APPLIED: p65 21 checked / 7 failed -> 24 / 6. `226.811.97` was already read (`full stop for a thousands comma`). `130,0000.00` and the p64 misreads: `locate_cell_misreads.py 1985` finds 0 candidates, so nothing was sent to the witness. Label run into its figure: NOT APPLIED.
- 2 (`BALANCE TO FY`): APPLIED. 148 checked / 8 failed / 60 no check -- the worker's 148 by hand.
- 3 (parenthesised series totals, special accounts, group labels): NOT APPLIED.
- Names: `report-school-monies-returned` -> `report-school-state-aid`, family `school-receipts-returned-half-years`; `report-school-budget-summary` kept.
