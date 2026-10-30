# 1984 edition: what the shared code needs (for the integration pass)

Edition: calendar 1984 annual town report, `4484-1984-annual-town-report.pdf`, 146 pages. Tables were
read on the 56 pages `find_financial_pages.py --list 1984` picked; 79 tables mapped, 71 with a dataset (landed, or
refused with a reason in notes.csv), the rest NOT LANDED (map.csv). Every hand check below was computed from the cells
(`build/textract/out/4484-1984-annual-town-report.cells.tsv`), not typed from the page.
`edition.json` carries the opt-ins the 1986-1990 pass settled (`unlabeled_subtotals`,
`rounding_tolerance_usd` 1, `accountant_marks`, `id_column_words`, `recon_net_on_transfer_line`,
`stacked_pairs`, `receipts_span`) and `withheld_rows` (below).

## FINDER MISSES: 0

Every page of the 90 NOT in the picked list was scanned in `lines.tsv` for money figures
(`$1,234`, `1,234.56`); one page had 4 (p95, School Committee prose: `$20,000.`, `$6,000.`, `$70,000.`,
`$31,000.`, no table) and none had more. This bounds the misses, it does not prove zero.

## ROSTER PAGES

Written to `rosters.csv`: p22 `Roster of Firefighters of 1984` (names and ranks); p122-p133 the School
Department's staff pages (name, position, college, degree, year of hire; no pay, no FTE, no funding source;
the text of these pages is not in cells). p136 prints staff as FTE by role (landed in
`report-school-staff-fte`), which is not a roster.

## 1. Changes proved on this edition, needed in `scripts/read_report_tables.py`

Each was tried by importing the module and patching the object in memory, then running
`read_report_tables.py 1984` (the file on disk is untouched; the outputs here are the UNPATCHED run).

**1a. `IDENTITIES['accountant-schedule']`: the carry-forward column is headed `BALANCE TO FY 85`, not
`BALANCE FY ..`.** The two 1988/1991 identities match the term `'BALANCE FY'`. Change that term to
`'BALANCE (?:TO )?FY'` in both. Proved: accountant-schedule rows (p53-p59) go from 0 checked / 233
no check to 137 checked / 3 check failed / 93 no check, and the 3 failures are real:
p54 `Hospital, Medical and other Related Expenses` (a label with a figure fused into it,
`Police/Firemen14,653.63TF`) whose four figures `14793.60 14793.60 140.00 14793.63` do not close and p59 `Sanitary Landfill Loan` /
`Interest Sanitary Landfill` print their expended column as two figures in one cell
(`20,000.00 20,000.00`). The map already takes the header from p56 (`header_from`), where Textract kept
`AMOUNT EXPENDED` in one cell; p53-55 and p57-58 split it into `PROGRAM NAME AMOUNT | EXPENDED`, which
shifts every column name by one.

**1b. `RECEIPTS_GRAND` must read `TOTAL RECIPTS`.** p43 prints `TOTAL RECIPTS` (sic). The regex
`^TOTAL RECEIPTS$` misses it, so the grand total (18,403,002.25) is summed as an account. Change the
pattern to `GRAND TOTAL|^TOTAL REC[EI]*PTS$`. Proved (patched run): the accounts then sum to 18,665,668.62
against the printed 18,403,002.25, and the whole excess is explained to the cent by three things in
p42-43, none of them a transcription error:
- 256,550.98 is the printed subtotal of the motor vehicle excise section (170,399.26 + 83,546.99 +
  2,587.04 + 17.69), printed on the row of the NEXT label `Farm Animal, Machinery, Equipment` (p42 t1
  r12): a LABELLED subtotal, so the emitter takes it as an account;
- 6,615.39 is the printed subtotal of the three interest lines (6,070.86 + 539.65 + 4.88), printed on
  the row labelled `Added Costs:` (p42 t1 r28), the same pattern;
- 500.00 is MISSING: p42 t1 r28 right strip is one cell holding two accounts and two figures
  (`Sidewalks and Grounds - Transfer Wakefield Scholarship - Transfer | 300.00 200.00`), so the
  Trust & Investment section's printed subtotal (19,767.02) is 500.00 more than its parsed lines.
256,550.98 + 6,615.39 - 500.00 = 262,666.37, the excess. So the receipts rows are `check failed`
honestly, and a reader who adds the three corrections gets 18,403,002.25 to the cent. Every other section
subtotal of p42-43 that I paired with its lines (computed from the cells, the left strips of p42 and p43 t2
and the right strips of p42 and p43 t1) ties to the cent.

**1c. `CASH_INVESTED` must also find `Revenue Cash and Revenue Cash Invested:` (p41, p65).** p41 prints
the roll-forward and the eleven bank accounts as ONE table, with the account list introduced by that
label. `emit_treasurers_cash` only splits a chain block off on `CURRENT CASH INVESTED`, so mapped as
`treasurers-cash` it sums the chain's figures with the accounts (9,973,446.42 against 1,749,971.20)
and REFUSES, publishing no accounts. The map therefore lands p41 whole in
`report-treasurers-cash-reconciliation` (24 rows, all `checked`: the chain closes, 18,403,002.25 less
9,584,350.04 and so on to 1,749,971.20), which carries the accounts as chain rows. With the pattern
widened p41 could be mapped as `treasurers-cash` again and the eleven accounts (which sum to
1,749,971.20, computed here) would land there too. p65 (calendar year) is the same shape and is
landed whole in `report-treasurers-cash-calendar-year` (generic, no check).

## 2. Cells the reader does not read (rule 13c: the table was returned, figures were not)

1. **p76 omnibus budget: `Dutch Elm Nuisance Control | Tree Warden Administration | 8,000.00 5,000.00`**
   is one cell pair (t3 r14), two figures in a cell and not parsed. The 76 listed items sum to
   6,628,717.00; the printed TOTAL BUDGET VOTED is 6,642,332.00; the difference, 13,615.00, is these two
   lines (13,000.00) plus the pension allowance line (615.00) held out below. So the 55 `check failed`
   rows are exactly those lines and nothing else.
2. **p52 t2 debt repayment schedule, first issue (`MIDDLE SCHOOL`)**: the row prints `1.365.` (full stop
   for the comma) in the 1988 column and empty `$` cells for 1989-1990, so `stacked_pairs` does not
   split it and the issue's principal and interest rows are not written. Its TOTAL row (71,825 / 69,095 /
   66,365 / 207,285) then `check failed` because its rows are missing, and `GRAND TOTAL INTEREST` fails
   for the same reason. The other four issues and the GRAND TOTAL PRINCIPAL check.
3. **p44 detailed statement of payments.** An extra leftmost column holds four lone running sums beside
   section rows (271,812.33 at `Tri-Community Summer School`; 538,559.25 at the special detail wages
   subtotal; 95,540.65 at `Contributory Retirement System`; the page's own cumulative check marks). They
   land as a first figure on those rows. Row `Regional School Dist. Study Comm. | 551.67` and
   `Recovery from Pupils School Books | 237.41` have their amount inside the label cell (a label split
   over two cells), so those two payments are not parsed. p45: the section `Payments Deferred from
   Fiscal 1983 133,661.37` is read as label `... 1983` with the amount lost, and `TOTAL PAYMENTS:
   $18,404,952.22*` (asterisk) has no value; the map's `stated_total` is 18,404,952.22. Statuses are
   `no check` for all 95 rows; the page does not tie.
4. **p45 t1 right strip, r21** `Central Mass. Mosquito Control 17,627.00` shares a row with the printed
   `1,367,241.29` subtotal of the left strip, which lands in that row's label.
5. **p46-p47 general fund balance sheet:** the assets side prints no total in the cells or the lines of
   p46-47; the only large totals are 8,286,387.89 (p48, the right-hand side) and the long term debt
   410,000.00 (p48 t2). Nothing ties; 127 of 145 balance sheet rows are `no check`.
6. **p48 t2** the long term debt statement has `$ 410.000.00` (a full stop for the comma) on the left
   side; the right side and the total print `410,000.00`.
7. **p62 t1 is MIXED** (holdings by bank, rows 1-27, and the opening of the cemetery roll-forward, rows
   28+); one table cannot be split. The trust rows are all `no check` (`checks=none`).
8. **p63-p64 trust roll-forwards** do not tie row by row through the reader (labels are in the page lines,
   the cemetery bequest block prints the donors' names). 170 trust rows, all `no check`.
9. **p137 school state aid:** `TRANSPORTATION (Chapter 71)` prints two figures in one cell
   (`99,990. 4,840.`), so its FY-84 value is not parsed and the FY-85 `103,239.` lands as v1. Whole-dollar
   cells end in a full stop.
10. **p139-p142 school special accounts:** the account's balance on hand and receipts are in the LABEL
    cell, only appropriation or balance, expenditures and the FY-85 balance are columns. Row 4
    (athletic) prints `5,033:74*` (a colon for the point) and its FY-85 value is not parsed; rows 15, 16,
    18, 21, 24 print a `#Returned to Comm. of Mass.` note inside the figure cells.
11. **p136 school statistics:** a mixed-unit table (pupils, FTE, dollars). Row 1 (`NUMBER OF PUPILS`) and
    rows 4-5's dollar figures print `$ 180,050./Kdg. $1,338,311./Elem.` as two figures in one cell and
    are not parsed. Positional only; `checks=none`.

## 3. NOT LANDED because a landed row would be wrong (not because the data is absent)

- **p138 School Department summary of accounts (FY-84 appropriation, budget amendment, expended,
  FY-85 request).** Tried as a new dataset (`report-school-budget-summary`) and withdrawn: the series code
  (1000, 2000, 3000, 7000, 7100 ...) is read as a figure (`-7100` on `Site Improvement`), the series total
  is printed in parentheses (`($266,430.97)`) and parentheses read as NEGATIVE, so an appropriation lands
  as -266,430.97; salaries and expenses share one cell (`91,046. 17,300.`); and the administration and
  instruction rows are lost. What a landed version needs: a parentheses-as-series-total reading, the
  series code as part of the label, stacked salary/expense cells split as `stacked_pairs` does for debt,
  and the columns kept separate (an appropriation and an ACTUAL side by side: rule 1). The page also
  prints the FY-84 overdraft (+12,146.63) and the amount placed in escrow for summer salaries
  (+79,818.04); the accountant's schedule p57 prints the same school department overdraft.
- **p86 t5 Trades and Services pay rates** (an amended excerpt, Special Town Meeting November 1, 1984).
  The cells carry their unit (`1,770/yr.`, `214.55wk.`, `4.30`), which no figure parser reads. A new
  dataset (provisionally `report-pay-rates-voted`, one position and year of service, with the unit as
  a column) needs a unit-aware reader. Not the full schedule: see gaps.csv.

## 4. New datasets, and settled names reused

Reused (same quantity, stage and grain): `report-auditors-cash-schedule` (p8-9, families
`cash-reconciliation-schedule`, `cash-composition`, `investments-schedule`, `investments-composition`,
`trust-custody-composition`); `annual-report-receipts` (p42-43, `receipts_span`);
`report-statement-of-payments` (p44-45); `report-fund-balance-sheets` (p46-50, families
`general-fund-assets`, `general-fund-liabilities`, `general-fund-fund-balance-and-debt`,
`trust-funds-custody`, `revenue-sharing`); `report-revenue-sharing`; the family
`cash-reconciliation-revenue-sharing` in `report-treasurers-cash-reconciliation`;
`report-treasurers-cash-calendar-year` (p65); `report-trust-funds` families `trust-funds-summary`,
`trust-fund-bank-accounts`, `trust-fund-rollforward`; `report-debt` families `debt-by-issue`,
`debt-repayment-schedule`; `report-school-staff-fte`, `report-school-state-aid`,
`report-school-special-accounts`, `report-fee-schedule` family `school-tuition-rates` (TWO tables this
year, effective January 1, 1984 and January 1, 1985, `period_fy` 1984 and 1985);
`report-property-tax-exemptions`; `report-dept-activity` (police, p23-24); `report-elections`;
`report-warrant-article-amounts` and `report-appropriations` families `budget-amendment-proposed`,
`supplementary-budget`, `omnibus-budget`, `accountant-schedule`; `tax-collection`.

NEW datasets: none are landed. Two are described above as not landed (p138, p86 t5).

Stage notes, so none is read as the other (rule 1):
- p71 t2 is Article 9 AS WARRANTED for the Special Town Meeting of February 6, 1984 (seven items, no total
  printed); p71 t4 is Article 9 AS VOTED from the Reserve Fund (five items, 17,725 printed). The
  supplement alone, not a new total.
- p86 t8 + p87 t1 are Article 2 of the Special Town Meeting of November 1, 1984. The 17 amounts sum to
  11,600, the figure the page says is taken from free cash (`2/3 VOTE DECLARED TO TAKE $11,600. FROM FREE
  CASH`). They are landed as `supplementary-budget` (VOTED); the stage rests on that declared vote, the
  word `VOTED` is not legible in the cell text for this article. p87 t2 is Article 3 AS WARRANTED
  (six items, 20,174); the vote took five of them for 19,074 (item 29, 1,100, disapproved), so it is never
  the appropriation.
- p76 is the FY1985 budget as voted at the May 12, 1984 Annual Town Meeting (Textract numbered the three
  strips 2, 3, 1; the map reads them in page order). A budget, not an actual.

## 5. Privacy: rows held out (`edition.json` `withheld_rows`), names not repeated here

- A pension allowance paid to one named person: p44 t1 r64 (payments), p58 t1 r42 (accountant's
  schedule) and p76 t1 r40 (the voted budget line, which names her).
- p64 t1 r27 and r36: the named recipient of a school prize grant and of a scholarship grant, paid as
  persons (a student's name beside an amount). The funds' own names, and the donors, are kept.
- No `heading_pages`: none of the pages' top lines (`tables.csv` `page_top_lines`) names them.
- Births: none landed. Burials: none landed; the cemetery department's `1984 BURIALS` list (text line
  964 of the extracted text) is on a page not sent for tables, so no named burial row exists here.
- Trust fund donor and bequest names (cemetery bequests, library funds, p49, p62-63) are landed as the
  fund's printed labels, as 1986 does: they are gifts TO the Town, not payments to persons.

## 6. Observations about the page, for the integration pass

- Pages 8-9 (the Auditor's schedules) print a SECOND roll-forward of cash for the General Fund and the
  Revenue Sharing Fund with gross receipts and disbursements; they tie by the page's own columns (the
  General Fund closes at 22,404.70), and 30 of 41 rows are `checked`.
- The Treasurer's disbursements on p41 (18,407,372.22) include 2,420.00 of petty cash advances that p44
  prints on their own line below the payments subtotal; p45 TOTAL PAYMENTS is 18,404,952.22. 18,407,372.22
  less 18,404,952.22 is 2,420.00.
- p52 `BONDED INDEBTEDNESS` is a year later than the rest of the book (`Due Fiscal 1985`), as 1986 p48 is.
- The reader's `pages` count: 6 proven (p8, p9, p41, p50, p51, p71), 32 unproven, 1 refused (p138).
  `unproven` here means rows with `no check` or `check failed`, not unread.

## Integration pass, 30 October 2026: what was done with each item

- **Privacy:** TJ, 30 October 2026: *"Yes publish. Everything in the annual reports is public."* `withheld_rows` is removed from this folder's `edition.json`; the rows it held are published. (The reader's mechanism stays, unused, for a takedown.)
- 1a (`BALANCE TO FY`): APPLIED as the widened identities. 138 checked / 3 failed / 93 no check (the three named here).
- 1b (`TOTAL RECIPTS`): APPLIED. Receipts stay `check failed` for the three reasons measured here.
- 1c (`CASH_INVESTED`): APPLIED; p41/1 mapped to `treasurers-cash`: 11 accounts published (sum 1,749,971.20), the chain 5 rows `checked`.
- 2.x cells, 3 (p138, p86 t5): NOT APPLIED (figures in no cell, two figures in one cell, a unit-aware reader). `5,033:74*` reads through the opt-in `colon_for_point` (set here).
- Names: p137 family -> `school-receipts-returned-to-town`.
