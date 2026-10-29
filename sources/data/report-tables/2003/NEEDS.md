# report-tables/2003: what the integration pass needs to change

Written by the 2003 worker, which may write only inside this folder. Each item: the change, why,
and the pages. Nothing here has been applied. Figures marked "by hand" were summed from the
Textract cells in `build/textract/out/4529-2003-annual-town-report.cells.tsv`, not by the script.

## 1. Receipts (p52) need a column-span layout -- NOT LANDED until then

- **Change:** the same as 2008's NEEDS item 1: `read_report_tables.records()` accepts
  `layout` = `spans:1-2,4-5,7-8` beside `groups:N`. Then set p52 t1 in `map.csv` to
  `dataset=annual-report-receipts`, `layout=spans:1-2,4-5,7-8`, and drop the NOT LANDED note.
- **Why:** Textract returned 8 columns: three label/amount pairs with EMPTY spacer columns 3
  and 6. `groups:3` cuts 1-2/3-4/5-6 and drops 7-8; `groups:4` puts the middle label (col 4)
  and its amount (col 5) in different groups.
- **What it would find (by hand):** the 100 account rows sum to **$19,060,763.56, the printed
  `GRAND TOTAL` exactly**, so they would land `checked`. The eleven SUMMARY OF RECEIPTS
  categories sum to $19,510,024.04, which is the GRAND TOTAL plus $449,260.48 -- the printed
  `NON RECURRING REVENUE` category. Measured only; why the categories exceed the total by that
  line is not tested here.

## 2. Treasurer's cash (p68): the total is in the OTHER table on the page -- refused

- **Change:** `emit_treasurers_cash` takes the printed total from `map.csv`'s `stated_total`
  when the table itself prints none (cite it as `GENERAL LEDGER BALANCE, p68 table 1`). Then
  set `stated_total=17970305` on p68 t2.
- **Why:** Textract split the page in two: table 1 is the reconciliation ending
  `GENERAL LEDGER BALANCE $17,970,305.00`; table 2 is the 22 bank accounts, with no total row.
  The emitter looks for the total inside table 2, finds none, and refuses
  (`notes.csv`: `accounts sum 17,970,305.00, printed none read`).
- **What it would find (by hand):** the 22 accounts sum to $17,970,305, equal to the printed
  general ledger balance, so all 22 would publish.

## 3. A table with no money figure loses its FIRST ROW -- 27 tables

- **Change:** in `records()`, the fallback `head, body = rows[:1], rows[1:]` (taken when no
  row holds a money figure) should apply only when row 1 looks like a header -- e.g. no cell
  in it is a four-digit year, a person's name or an integer count -- or `map.csv` gets a
  `header_rows` column (`0` = no header row) that overrides it.
- **Why:** officials lists, rosters and activity counts print integers and years, which are
  not money, so row 1 is always taken as the header. On 2003 that drops real rows:
  p6 t1-5, p7 t2-4, p8 t1-6/8-11/13, p9 t1 (an office holder each; p8 t3 and t13 two), p7 t1 (the position heading `ANIMAL CONTROL OFFICER-1 YR`), p25 t1 (two firefighters),
  p37 t1 (the School Committee chair), p19 t1 (`Septic System Consultations 57`), p20 t1
  (`Students Eligible 373`), p26 t1 (`Alarm responses 643`, the first police category), p47 t1
  (`Passed Both ... 138 students 85%`). Each is named in its `map.csv` note. Not checked whether
  2010's headerless officials tables (p8, p9) lost rows the same way; worth a look in the same
  pass.

## 4. A header row under a title row is not read (p39 enrollment)

- **Change:** let `header_from` name a row of the same table (e.g. `39/1/r3`), or let
  `split_header` skip a one-cell title row.
- **Why:** p39's row 1 is `ENROLLMENT--OCTOBER 1, 2003` and the column header
  `School/Grade | 10-01-01 | 10-01-02 | 10-01-03` is row 3, so the 20 enrollment rows land with
  an empty `column_meaning`. The figures are right; their dates are not attached.

## 5. A row identity for the treasurer's cash reconciliation (new family)

- **Change:** register for family `treasurers-cash-reconciliation` the printed identity
  `BALANCE JUNE 30, 2002 + RECEIPTS + LESS INVESTMENTS TRANSFERRED = subtotal` and
  `subtotal - (DISBURSED + LESS REVENUE CASH INVESTED) = GENERAL LEDGER BALANCE`. It is not
  a column identity, so `IDENTITIES` (by column) cannot hold it; it needs a small emitter or a
  row-sequence check. 2008 (its NEEDS item 2) has the same reconciliation.
- **By hand:** 3,851,439 + 69,885,335 - 25,194,490 = 48,542,284; 72,761,749 - 42,189,770 =
  30,571,979; 48,542,284 - 30,571,979 = 17,970,305 = GENERAL LEDGER BALANCE. Closes. The 8 rows
  are `no check` until then.

## 6. Register two NEW datasets (merge, build_db, PROOF)

- `report-treasurers-cash-reconciliation` (p68 t1, 8 rows): the treasurer's cash FLOW for the
  year. No FY2011-FY2025 dataset holds it; they print only the closing balances by account.
  2008 proposed `treasurers-cash-reconciliation` for the same thing -- pick one name.
- `report-weights-measures-fee-schedule` (p89-p90, 41 rows): the sealing fee per device class
  adopted by the Annual Town Meeting of May 3, 2003, Article 24 (By-Law Article II Section 12).
  A rate set by vote, not the Sealer's activity in `report-weights-measures`. `$20.00/Cost` and
  `Cost` are not parsed as figures.
- `map_annual_report_pages.PROOF` has no entry for either, so p89-p90 read `unproven`.

## 7. Prose figures that belong in existing datasets (not tables, so not read here)

- **placement-counts:** p46 (Special Services Report) prints `two hundred and forty-five. (245)
  students ... received some form of special education or related service. This represents 13 %`
  and `only eight students receive services outside the district during the 2003/2004 school
  year`. No split, no count date, no source named. Whether it goes into `placement-counts`
  beside the SIMS-sourced counts is the integration pass's call; the gap is in `gaps.csv`.
- **Monty Tech:** p31 prints Monty Tech enrollment by member town in prose (`... Westminster
  (52), and Winchendon (100). In addition, there are 33 out of district students`). FY2011
  catalogues the same table; not read here.

## 8. A decision for TJ, not a mapping: named births and marriages (p76-p79)

The 2003 report prints every BIRTH by name with birthplace and both parents' names (p76-p77),
and every MARRIAGE by both names WITH DATE OF BIRTH and residence (p78-p79). FY2011-FY2025
print only counts. They are left NOT LANDED. Deaths (p80, name and age) were landed in
`report-vital-records` family `deaths`, at the same grain as the burial lists already there;
undo that too if the decision is that named vital records stay out of the database.

## Integration pass, 28 October 2026

What the one integration agent did with each item above. Counts are this folder's rows after
`read_report_tables.py`; the reasons for anything not applied are here so nobody re-asks.

- **1 receipts column spans (p52).** APPLIED: `layout=spans:1-2,4-5,7-8`. LANDED: 100 accounts, `checked` against the GRAND TOTAL $19,060,763.56.
- **2 treasurer's cash total in the other table (p68).** APPLIED: `stated_total=17970305`; 22 accounts publish.
- **3 tables with no money figure lose their first row.** APPLIED generally (see 2007 item 4).
- **4 header row under a title row (p39).** APPLIED: a row of dates is the header.
- **5 reconciliation identity.** APPLIED: 9 rows `checked`.
- **6 register two datasets.** APPLIED, RENAMED: `report-treasurers-cash-reconciliation` (family `cash-reconciliation`), and `report-weights-measures-fee-schedule` is now `report-fee-schedule` (family `sealing-fee-schedule`), beside 2004's Town Clerk fees.
- **7 prose figures.** NOT APPLIED -- prose figures (placement counts, vital-record counts, fire incidents, capital plan prose, pie-chart percentages) need a prose reader; no table reader can land them. `placement-counts` is SIMS-sourced and dated 1 March; these sentences name a school year and no source, so adding them is a decision about mixing two measurements, not a mapping. Recorded here with their pages; nothing was inferred.
- **8 births and marriages.** NOT APPLIED -- a decision for TJ, not a mapping: named births (infants, parents) and marriages (dates of birth) stay NOT LANDED.
