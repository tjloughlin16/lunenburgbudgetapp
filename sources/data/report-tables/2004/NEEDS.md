# 2004 edition: what the integration pass needs to change

Written by the 2004 worker. Nothing here was changed in a shared file; each item names the
exact change, why, and the pages. Figures quoted are as Textract read them.

## 1. Dataset registrations (three NEW datasets, emitted with the GENERIC columns)

| dataset | family | pages | what the page prints |
|---|---|---|---|
| `report-library-service-values` | `library-service-values` | p25 | `SERVICE VALUES 2004`: per library service, the count used and the library's own ESTIMATE of its value to residents (count x a unit price the page names), TOTAL $1,292,620.00. An estimate by the library, not a town expenditure. 10 rows, all `checked` (they foot to the printed TOTAL) |
| `report-treasurers-cash-reconciliation` | `cash-reconciliation` | p74 t1 | the year's cash roll-forward: `BALANCE JUNE 30, 2003` $17,970,305.00 + receipts net of investments transferred $35,688,091.00 = $53,658,396.00; less disbursements net of revenue cash invested $42,209,600.00 = `GENERAL LEDGER BALANCE` $11,448,796.00. 8 rows, `no check` |
| `report-fee-schedule` | `town-clerk-fees` | p100-101 | Town Clerk fees under MGL c.262 s.34, clauses 1-79, old and new, as voted at ATM May 1, 2004, Article 28. 30 rows, `no check` (no total exists) |

Each needs whatever `merge_report_tables.py` / `build_db.py` / the catalogue need to know a new
`report-*` file exists (the same step 2010's `report-weights-measures` and
`report-classification-plan` took).

## 2. `emit_treasurers_cash`: accept a total printed OUTSIDE the table (p74 t2)

The 24 accounts in p74 t2 sum to **$11,448,796.00** exactly, which is the `GENERAL LEDGER
BALANCE` the page prints in t1 and again below the listing (a line Textract read, outside any
table). The emitter looks for a total ROW in the same table, finds none, and refuses
(`notes.csv`: `printed none read: not published (refused)`), so `treasurers-cash` gets 0 rows
for 2004.

Change: when no total row is found, use `Decimal(m['stated_total'])` if the map row carries one.
`map.csv` already sets `stated_total = 11448796.00` on p74 t2 (cited in its note). With that
change the 24 accounts publish and p74 becomes `proven`.

## 3. Row identities

- **`elections`: precinct columns printed `PRE A`..`PRE D`** (State Primary, p90-92). The
  identity's terms are `PREC A`, `PREC B`, `PREC C` (and `PRE\w* D`), so p90-92 rows get no
  row identity. Change the first three to `PRE\w* A`, `PRE\w* B`, `PRE\w* C` (same form the
  D term already uses). 2010 is unaffected (its headers print `PREC`).
- **`trust-funds`: this edition's layout is different** (p70-72): `ACCOUNT | ALLOCATION |
  BEG BAL 6/30/03 | DIVIDENDS | CONTRIBUTIONS | REDEMPTIONS | BOOK BALANCE`, no
  principal/earnings split and no market value. The existing identities name columns this page
  does not print, so they do not apply (correctly). I am NOT proposing a new identity: the
  rows do not follow one convention. `SALE OF CEMETERY LOT` closes as BEG + DIVIDENDS -
  REDEMPTIONS (29,211.38 + 998.80 - 1,200.00 = 29,010.18), but `PERPETUAL CARE BEQUEST` prints
  DIVIDENDS 4,647.13 and BOOK BALANCE equal to BEG (120,036.70), and REDEMPTIONS are printed
  positive on some rows and in parentheses on others (`STABILIZATION FIRSTFED BANK`
  `$ (678,273.77)`). Someone should read p70-72 against the PDF before writing one.
- **`cash-reconciliation`** (new, p74 t1): the identity is a running sum, not a row identity:
  r1 + r4 = r5 and r5 - r8 = r9 (`53,658,396 - 42,209,600 = 11,448,796`), with r4 = r2 + r3 and
  r8 = r6 + r7. It needs a vertical (column) identity, which the emitter cannot express today.
- **`accountant-schedule`: a blank `BALANCE TO REVENUE` is never checked.** By the docstring
  this is deliberate (`a blank target is not checked`). Evidence for revisiting it: of the 57
  2004 rows with an AVAILABLE figure and no BALANCE cell, 35 satisfy available = expended +
  encumbered, so they would close if a blank target counted as zero when every term column is
  present. The other 22 would fail, which is information too.

## 4. Parser marks (`validate_totals.parse` / `is_figure`)

- **Trailing `+`** on a money cell (p14 capital plan: `$ 2,500.00+`, `$ 3,678.36+`,
  `$ 4,583.00+`). Unparsed now, so the 17 parsed items sum to $629,681.20 against the printed
  TOTAL $640,442.56 and every row is `check failed`. The three unparsed amounts are exactly
  the $10,761.36 difference: with `+` stripped the plan foots to its TOTAL. The `+` itself is
  not explained on the page; record it, do not drop it.
- **Percent cells** (`67%`) are not figures, so the MCAS tables (p47-48) land with their values
  inside `label` and no v-values; and their three-row printed header (`Performance Level` /
  `Advanced | Proficient | ...` / `Lunenburg | State`) is emitted as two label-only rows
  because the header split falls back to the first row only.
- **`$6,920;527`** (p75 t2, `TOTAL UNISSUED:`): a semicolon for a comma. Unparsed; the
  authorisations above it are not checked against it.
- **Two printed lines in one cell** (p76-77 repayment schedule from FY2011 on, p86 elections):
  `$3,257 $12,437`. Unparsed, kept as printed; these are the bulk of the `check failed` rows
  on p76-77 and p86.

## 5. Payroll: every page is `proven` by coverage, and the printed grand total does not tie

`report-gross-wages` p103-110 (calendar 2004). Seven of eight pages are `proven` by the
coverage rule (every money figure in the page's LINE output is captured with a name). p108 is
`unproven`: `O'MALLEY MARK` reads `643 71,681.66` in one cell.

But p110 prints `GRAND TOTAL GROSS WAGES FOR CALENDAR YEAR 2004 $ 13,383,038.25`, and the 554
parsed employee figures plus O'Malley's $71,681.66 sum to **$13,376,576.45 -- $6,461.80
short**. The coverage witness is the same engine reading the same page twice, so it cannot see
a figure Textract missed in both passes. Suggest: a sum-to-printed-grand-total check for the
wage run, from `stated_total` on p110 (set in `map.csv`); until then the per-page `proven` is
weaker than it looks. The grand-total row itself is emitted as a `kind=total` row in
`report-gross-wages`; make sure the merge does not count it as an employee.

## 6. Prose figures that a dataset holds elsewhere (not tables, so not landed here)

- **Out-of-district placements, school year 2004/2005** -- `placement-counts` territory, and the
  2010 edition registers it as a GAP. The 2004 report PRINTS it, in prose, PDF p49 (Special
  Services Department): `nine students received services outside the district during the
  2004/2005 school years. Of the nine students, one is in a collaborative placement, seven are
  in day placements and one is in a residential placement.` Also: `an additional forty-seven
  students identified with disabilities receive accommodations under a 504 plan.` No
  measurement date is stated (FY2013+ rows are SIMS, 1 March). Parts sum to the total (1+7+1=9).
- Inspector of Weights & Measures (p22): `The fiscal budget was $2,310` and `were charged
  $3,885 in fees` -- the only W&M figures this edition prints (the device table is a gap).
- Monty Tech October 1, 2004 enrollment by member town (p32): Lunenburg 59 of 1,229.

## 7. Held for a decision: births and marriages (p78-80, p82-83)

Mapped NOT LANDED, deliberately, not refused. The births list names each infant with
birthplace and both parents; the marriages list prints each party's full date of birth and
residence. The FY2011-FY2025 reports print counts only. Deaths (p81) and burials (p13) ARE
landed in `report-vital-records`, following 2010's burial list. Whether infants' names with
parents, and adults' dates of birth, go into a searchable public database is a call for TJ /
the integration pass, not for a worker. If yes: map p78-80 to `report-vital-records` family
`births` and p82-83 family `marriages`; nothing else changes.

## 8. Readings worth a look against the PDF (not changed; figures stay as read)

- p52 balance sheet, ENTERPRISE column refused: `USER CHARGES RECEIVABLE` read $4,455.65 and
  `DEFERRED REVENUE` $4,456.55; with $4,455.55 in both, assets and liabilities both foot
  (330,901.57 + 4,455.55 = 335,357.12; 2,629.63 + 4,455.55 = 7,085.18). Either a misread
  twice or the town printed it so.
- p51 t1 `Open Space` levy percent read `0.140`; 139,600 / 996,295,300 is 0.0140%, and with
  0.0140 the column foots to the printed 100.0000.
- p75 t1 the printed TOTAL row's AMOUNT ($24,119,410) does not foot (the nine issues sum to
  $30,975,812, off by exactly MASS WATER POOL 9's $6,856,402); its BALANCE does.

## Integration pass, 28 October 2026

What the one integration agent did with each item above. Counts are this folder's rows after
`read_report_tables.py`; the reasons for anything not applied are here so nobody re-asks.

- **1 three new datasets.** APPLIED: `report-library-service-values` (kept), `report-treasurers-cash-reconciliation` (kept; now the one name for 2001-2008), `report-fee-schedule` (kept; 2003's sealing fees folded into it). Registered in PROOF, build_db, table-semantics.
- **2 treasurer's cash total outside the table.** APPLIED via `stated_total`; 24 accounts publish.
- **3 identities.** APPLIED: elections `PRE\w* A..D` (report-elections 2004: 228 checked, was 172); cash reconciliation down the page (9 rows `checked`). NOT APPLIED: trust-funds (none proposed) and the blank-balance identity (see 2009 item 6 for the measurement).
- **4 parser marks.** APPLIED: trailing `+` and `;` for `,` (validate_totals.REPAIRS). The p14 capital plan now foots to its TOTAL: 20 rows `checked` (was 17 `check failed`). Two figures in one cell stay unparsed, as printed. Percents are figures, `[percent]`.
- **5 payroll grand total.** APPLIED: `stated_total=13383038.25` on p110; every wage row's `reconciliation` carries the tie. It does not tie: 554 parsed rows sum to 13,304,894.79, short 78,143.46 with O'MALLEY's `643 71,681.66` unread -- the worker's 6,461.80 once that cell is counted. Per-page coverage grades are unchanged.
- **6 prose figures.** NOT APPLIED -- prose figures (placement counts, vital-record counts, fire incidents, capital plan prose, pie-chart percentages) need a prose reader; no table reader can land them. `placement-counts` is SIMS-sourced and dated 1 March; these sentences name a school year and no source, so adding them is a decision about mixing two measurements, not a mapping. Recorded here with their pages; nothing was inferred.
- **7 births and marriages.** NOT APPLIED -- a decision for TJ, not a mapping: named births (infants, parents) and marriages (dates of birth) stay NOT LANDED.
- **8 readings worth a look.** No change asked; figures stay as read.
