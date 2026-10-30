# 1986 edition: what the shared code needs (for the integration pass)

Edition: calendar 1986 annual town report, `4549-1986-annual-town-report.pdf`, 122 pages. Tables were
read on the 56 pages `find_financial_pages.py --list 1986` picked; 39 of those landed rows (pages.csv),
the rest are prose pages with dollar figures (departments, warrant articles) where the picked table is
not money, or are mapped NOT LANDED (map.csv). Every hand check below was computed from the cells
(`build/textract/out/4549-1986-annual-town-report.cells.tsv`), not typed from the page.

## FINDER MISSES: 0

Every page of the 122 NOT in the picked list was scanned for 6+ money figures in the lines; none had
them. (Method: a regex for `1,234` / `$12.34` over `lines.tsv`; a page with a money table and fewer
than six figures would not show, so this bounds the misses, it does not prove zero.)

## ROSTER PAGES

No school staff roster is printed. Name lists with no money, not sent, written to `rosters.csv`:
p23 `Roster of Firefighters of 1986`; p108-p109 the School Department's personnel changes
(`Resignations During 1986`, `RESIGNATIONS DURING 1986 (Continued)`, `On Leave of Absence During 1986`).
p112 prints staff as FTE by role (landed as `report-school-staff-fte`), which is not a roster.

## CELLS MISSING ON PICKED PAGES (rule 13c: the table was returned, rows of it were not)

1. **p71 (omnibus budget, Article 8): eight printed rows have no cell.** Items 62 `Veterans' Services
   Admin.` 3,645, 63 `Veterans' Benefits` 12,500, 64 `School Department` 5,040,000, 66 `Mont. Reg. Voc.
   Tech.` 53,800, and the totals around them are in `lines.tsv` (p71 lines 137-166) but in no table.
   None is typed into the rows. THE PAGE TIES TO THE DOLLAR WITH THEM: the 70 item rows landed sum to
   2,700,134; the four unread items are 5,109,945; four lines whose thousands separator Textract read as
   a full stop (`12.600.`, `4.100.`, `13.000.`, `100.000.`) are unparsed and are 129,700; together
   7,939,779, the printed `TOTAL BUDGET VOTED` (p72 line 70, `7.939.779.`; map `stated_total`). So the
   shortfall the 66 `check failed` rows report (5,239,645) is exactly those twelve lines and nothing else.
   What would settle it: a re-read of p71's veterans/schools block, or a calendar repair (item 3).
2. **p92 table 3, `Effective January 1, 1987:`** returned with its caption only. The 1987 tuition
   rates are in the page lines (kindergarten $1,502 and the three grade bands that follow) and no row
   is written from them.
3. **p38/p39 boundary.** The right-hand panel of p38 ends mid-way through `Unclassified` (last cell row:
   `Worcester County Extension Service 25.00`); the lines at the top of p39 hold `Unemployment
   Compensation 1,472.00`, `Pension Allowance J. McGregor 616.00`, `Registrar Veterans' Graves 184.83`
   and the section's subtotal, but Textract put Unemployment Compensation into 39/1 as a header-like row
   (`Refunds: $ | $`'s neighbour) and the rest in no cell. The statement's section subtotals, the debt lines and the agency lines sum to 21,180,730.27 against the printed TOTAL PAYMENTS 21,656,011.94 (short
   475,281.67). The p38 Unclassified items alone sum to 472,968.85; that is HYPOTHESIS ONLY about where
   the rest sits, and nothing here tests it.

## 1. Calendar-only readings (CALENDAR_REPAIRS), all measured on this edition

- **`.12`, `.15`, `.84`, `.01`, `.85`** (cents with no leading `0`): 15 unparsed cells on the p54-59
  accountant schedule (`Selectmen's Salaries ... .12`), 3 on p74 (`.01 .85 .15`), 1 on p37 (`Telephones .84`).
- **`12.600.`, `$328.800.`, `100.000.`** (a full stop for the thousands separator AND a trailing full
  stop, whole dollars): p71-72, 8 cells: four items and four section totals (`TOTAL GENERAL GOVERNMENT`, `TOTAL PROTECTION ...`, `TOTAL HEALTH`, `TOTAL UNCLASSIFIED`).
- **`17,75$`** (`$` at the end, a comma for the decimal point): p37 r1, `Postage Reimbursement` 17.75.
- **`10:00`** (a colon for the decimal point): p39 `Registry-Parking Ticket Surcharge` 10.00.
- **`2,2`** (comma for decimal in an FTE): p112 `Principals/Adm. Assistants`, Textract `2,2`.
Each is a reading of an instrument's output, not a fact about the town; all are currently left as
`unparsed_cells` (preserved, not guessed).

## 2. Two figures in ONE cell (a stacked pair) -- the largest unlanded block

- **p47 debt repayment schedule**: every issue row prints PRINCIPAL and INTEREST stacked in one cell
  (`20,000 3,780`), under `FISCAL YEAR | 1988 ... 1997 | TOTAL`, with a TOTAL row beneath that parses.
  All 9 issue rows are `no check` with `n_values 0`, so the TOTAL rows `check failed` (rows sum 0). By
  hand from the cells: each issue's TOTAL row equals the sum of its two stacked figures in every year it
  prints (e.g. Sanitary Landfill 23,780 = 20,000 + 3,780), and the row `GRAND TOTAL` 1,028,708 =
  802,420 + 226,288 (its stacked pair). Wanted: a splitter that turns `a b` into two columns
  (PRINCIPAL, INTEREST) per fiscal year when the header names both (p47 header cell 2 reads
  `MIDDLE SCHOOL : PRINCIPAL INTEREST` in the label column).
- **p54-59 accountant schedule**: Textract merged a department's several lines into one cell
  (`7,602.57 2,243.04`; `12,200.00 50,964.00`; p55 r4 five labels, five amounts). 61 unparsed cells.
  The reader cannot split a label cell that spans several lines.

## 3. Row identities and checks the machinery lacks (all hand-verified on the cells)

- **Detailed statement of receipts (p36-37, `report-statement-of-receipts`).** Items in column 2,
  an UNLABELLED section subtotal in column 3. The column-3 amounts of the four tables sum to
  21,618,494.85 to the cent, the printed `TOTAL RECEIPTS`, which also equals the `Receipts` line of the
  Treasurer's reconciliation (p35) and of the auditor's schedule (p10). 22 of 23 subtotals equal the
  detail lines above them; the exception is p37 r6, whose detail begins on p36 (a section crossing a
  page). `mark_unlabeled_subtotals` runs only for `report-appropriations`; I tried it on a COPY of the
  script (not applied) for these datasets and it moved no row (checked 3 -> 5 on balance sheets), so
  the miss is the cross-page/cross-table sections, not the opt-in.
- **Detailed statement of payments (p38-39)**: 12 of 12 column subtotals on p38 (both panels) and p39
  equal the lines above them; the page total does not tie (CELLS MISSING item 3).
- **General fund balance sheet (p40-42)**: 7 of 8 subtotals (p40-41) equal the lines above them; the exception
  (p41 r17, 126,916.48) continues a section from p40. The statement balances: total assets 9,700,665.44
  = total liabilities and fund balances 9,700,665.44 (p42 r8, both sides), and the long term debt
  766,862.95 = 130,000.00 outside the debt limit + 636,862.95 inside (p42 r19-r20).
- **Treasurer's cash**: the p35 chain closes (landed `checked`, 6 of 6); the p53 calendar-year chain
  closes by hand: 970,444.19 + 11,903,196.79 - 10,724,275.08 = 2,149,365.90, and the 11 accounts of 53/2
  sum to the same figure, to the cent.
- **Cross-statement ties** (no check can reach them; each by hand): the auditor's General Fund overdraft
  (1,057.65) + General Fund invested 1,884,820.87 = 1,883,763.22, the Treasurer's general ledger balance
  (p35); trust funds 384,822.83 on p11, p44, p50 and p43-44's sum.
- **Revenue sharing (p46)**: receipts 248,710.55 = payments 248,710.55; ledger balance 77,047.52 = the
  p45 liabilities and assets (77,047.52 each).
- **School staff FTE (p112)**: see map.csv 112/1 note. The `Aides` GRAND TOTAL cell reads 5.5 where its
  four school columns print 1.8, 1.7, 2.0, 1.0 (= 6.5); that is a printed or Textract defect to be
  settled from the image. The reader's own check (`NET TOTAL EXPENDITURES` read as the column's GRAND
  TOTAL) is a false failure, so 112/1 carries `checks=none`.
- **Accountant schedule (p54-59)**: 5 rows `check failed` on the BALANCE REVENUE identity (p54 Accept
  Canterbury Road, p57 Stone Bridge, p58 Utilities & Building Maintenance and Holding Tank Town Beach,
  p59 Interest Middle School Loan); in three the blank BALANCE REVENUE cell is read as 0 where the
  columns imply 200 / 500 / 100, which may be a cell Textract dropped. Candidates for the cell-witness
  pass; not settled here.

## 4. New dataset names (reuse across the 1986-1990 batch where it is the same quantity)

| name | what it is |
|---|---|
| `report-statement-of-receipts` (family `detailed-receipts`) | the Treasurer's DETAILED STATEMENT OF RECEIPTS, nested, by source; not folded into `annual-report-receipts` because that emitter pools by page and would write the unlabelled subtotals as sources |
| `report-statement-of-payments` (family `detailed-payments`) | the Treasurer's DETAILED STATEMENT OF PAYMENTS, by department and object; an actual |
| `report-fund-balance-sheets` (families `general-fund-liabilities`, `general-fund-assets`, `general-fund-fund-balance-and-debt`, `trust-funds-custody`, `revenue-sharing`) | single-fund balance sheets with one amount column; `balance-sheet` publishes per FUND COLUMN and cannot hold these |
| `report-auditors-cash-schedule` (families `cash-reconciliation-schedule`, `cash-composition`, `investments-schedule`, `investments-composition`, `trust-custody-composition`) | the Auditor's schedule on p10-11 |
| `report-revenue-sharing` (families `reconciliation`, `receipts`, `payments`) | the federal General Revenue Sharing fund |
| `report-treasurers-cash-calendar-year` | the SECOND Treasurer's reconciliation (calendar 1986) and its account list; kept apart from the fiscal one because `treasurers-cash` has no date column |
| `report-vendor-payments` (family `vendor-payments-over-4000`) | payments to vendors over $4,000 in fiscal 1986 (MGL c.40 s.4G), name and address in one cell |
| `report-school-staff-fte` | School Department staff in FTE by role and school |
| `report-school-state-aid` | State aid by chapter against the school appropriation, FY-85 to FY-87 |
| `report-school-special-accounts` | the School Department's revolving, grant and article accounts |
| families in existing datasets | `report-trust-funds`: `trust-fund-rollforward`, `trust-fund-bank-accounts`; `report-fee-schedule`: `school-tuition-rates`; `report-warrant-article-amounts`: `unexpended-articles-reappropriated` (existing, 1989); `report-appropriations`: `supplementary-budget` (existing, 1992) |

If the integration pass decides `report-statement-of-receipts` should be `annual-report-receipts`,
the emitter needs: an unlabelled column-3 figure is a section subtotal; `TOTAL RECEIPTS` is the
grand total; pool across pages 36-37, not per page.

## 5. Not landed, by decision (map.csv says why)

- p62 tables 2-4: the births of 1986 by month, named children with birthplace and parents. As 2001
  p75-77: no dataset holds per-person births and landing names is TJ's decision.
- p3 (office hours, meeting schedule), p77 (a zoning by-law's permitted-use list), p92 table 1 (the
  no-school horn signals): no money, no dataset.
- p87 is landed in `report-elections` with `financial=no` and `checks=none`: two ballot-question
  tables of Yes/No/Blanks whose column headings and question numbers are not in the cells.

## 6. What this report prints that 2010 did not

An Auditor's schedule of cash and investments (p10-11); a nested DETAILED STATEMENT of receipts and of
payments (p36-39); single-fund balance sheets including a long term debt statement with the debt-limit
split (p40-42); trust fund roll-forwards by fund and by bank account (p50-52); a second, calendar-year
Treasurer's reconciliation (p53); the federal Revenue Sharing fund (p45-46); vendors over $4,000 (p60-62);
the School Committee's state-aid-against-appropriation table and special accounts (p112-115).

## What was done with each item above

(Integration pass, 29 October 2026.)

- **Names.** `report-statement-of-receipts` -> `annual-report-receipts` (same quantity as 1987-2010), read
  by the span emitter (`receipts_span`): the accounts now sum to TOTAL RECEIPTS 21,618,494.85 to the cent,
  `checked`. `report-auditors-cash-schedule` kept (1987 and 1988 renamed to it). p46/1 (revenue sharing
  roll-forward) -> `report-treasurers-cash-reconciliation`, family `cash-reconciliation-revenue-sharing`, as
  1987 p30/2: the chain closes (`checked`). The other new datasets kept; see the README.
- **1 calendar readings.** `.12` etc. (cents with no leading zero) and `12.600.` / `7.939.779.` (full stops
  for the thousands separator) APPLIED, always on, 1991-2010 unchanged. `17,75$` APPLIED (it is the one
  cell that left the receipts 17.75 short). `10:00` and `2,2` SKIPPED: a colon reads as a time and `2,2`
  as 2.2 or 22; one cell each, nothing decides it from the cell alone.
- **2 stacked pairs.** APPLIED as opt-in `stacked_pairs`: p48's PRINCIPAL INTEREST columns split in two,
  p47's PRINCIPAL INTEREST rows split in two. p48 now `checked`; p47 closes every issue and every year but
  1997, where only ONE issue pays, so the validator's by-kind rule (it needs two rows of a kind) cannot
  reach `GRAND TOTAL : PRINCIPAL` -- our grouping, not the town's arithmetic. Not changed: the validator
  is shared with the FY reviews. The p54-59 merged label cells: SKIPPED, a label spanning several lines
  cannot be split without guessing which amount is whose.
- **3 identities.** Receipts: done (above). Payments p38-39: SKIPPED, the page total does not tie because
  cells are missing (CELLS MISSING 3), not for want of an identity. Balance sheets, trust books: the
  `unlabeled_subtotals` walk was tried on them (a new `unlabeled_subtotals_in` list; code kept, off by
  default) and moved 2 balance-sheet rows and no page, so it is not switched on. Accountant schedule
  p54-59: the five BALANCE REVENUE failures stay; `locate_cell_misreads.py` pins none of them.
- **CELLS MISSING 1 (p71).** Unchanged and correct: the 74 item rows sum to 2,829,834 and the omnibus list
  is short of TOTAL BUDGET VOTED by exactly 5,109,945, the four items Textract returned in no cell. The
  four full-stop totals now read. Settles: a re-read of p71.
- **Privacy.** p62 births NOT landed (as 2001). `report-vendor-payments`: six payees printed as
  `Surname, Given` with a street address are private individuals paid as persons; HELD OUT by
  `edition.json` `withheld_rows` (60/2/6, 60/2/19, 61/1/1, 61/1/11, 61/1/15, 61/2/12), pending TJ. The
  page itself is public in the archive and its text in search; p61's heading in `pages.csv` and
  `tables.csv` is one of those names, because the page begins with it.
- **Rosters.** p23 (firefighters) and p108-109 (resignations, leave of absence) are not school staff
  rosters; not dumped into `sources/data/rosters/`.

