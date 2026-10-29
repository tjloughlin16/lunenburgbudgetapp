# 2005: what the integration pass needs to change

Nothing below was changed by the 2005 worker. Each item is a change to a shared script or file.

## 1. treasurers-cash: take the printed total from the sibling table (p67)

`emit_treasurers_cash` looks for the total row INSIDE the table it is given. On p67 Textract split
the page into two tables: table 1 is the reconciliation and ends `GENERAL LEDGER BALANCE |
$4,561,756.00` (r9); table 2 is the 28 accounts (`ENTERPRISE` ... `CASH ON HAND`), with no total
row. The 28 accounts sum to **4,561,756.00**, which is that printed balance exactly, so the table
ties, but it is refused (`notes.csv`: `printed none read: not published`).

Change: let a map row name a total in another table, e.g. a `total_from` column (`67/1`, matched
by the label `ledger balance`), or reuse `stated_total` for treasurers-cash. With either, p67 t2
publishes 28 rows `checked`.

## 2. A row identity for the cash reconciliation (new family `cash-reconciliation`, p67 t1)

New dataset `report-cash-reconciliation` (8 rows, all `no check`). The page's arithmetic closes:

    11,448,796 + 89,794,153 - 46,055,549 = 55,187,400
    91,967,814 - 41,342,170              = 50,625,644
    55,187,400 - 50,625,644              =  4,561,756 = GENERAL LEDGER BALANCE

It is a chain down ONE column of running figures, not a row identity across columns, so
`IDENTITIES` cannot express it. It needs a small emitter (or an identity type that runs down a
column). Also: Textract put `$55,187,400.00` (r5 c4, a row with no label) into `group` for the
rows below it, because a row with figures in a non-figure column and no label became a heading.
That subtotal should be a row.

Register `report-cash-reconciliation` as a dataset (build_db, schema docs) so the merge can land
it.

## 3. Trust funds 2005 layout: NO row identity holds -- do not add one

p68-70 print `ACCOUNT | ALLOCATION | BEG BAL 6/30/04 | DIVIDENDS | CONTRIBUTIONS | REDEMPTIONS |
BOOK BALANCE`, not 2010's ten columns, so the `trust-funds` identities do not apply. I tested the
obvious candidate, BOOK BALANCE = BEG BAL + DIVIDENDS + CONTRIBUTIONS - REDEMPTIONS: it held on
12 of 86 rows. Dividends are printed against a principal account (e.g. `PERPETUAL CARE BEQUEST`,
BEG 120,036.70, DIVIDENDS 2,411.11, BOOK 120,036.70) while the book balance of the matching `...
INT` account grows. So the only checks are the printed column subtotals (`TOTAL COLUMBIA FUNDS`
and the others), which is what the rows' statuses already rest on. If a pair identity
(principal + INT account) is wanted, it is a new emitter, not an `IDENTITIES` entry.

## 4. Header rows that include the page title (p55-p60, accountant-schedule)

`V.split_header` took 9 header rows on p55-60, the first four being the title (`TOWN OF
LUNENBURG / GENERAL FUND APPROPRIATIONS / SUMMARY & CLASSIFICATION OF ACCOUNTS / FISCAL YEAR
2005`, read as cells r1-r4 in columns 2-4). `header_names` concatenates them, so `column_meaning`
for v1 reads `TOWN GENERAL SUMMARY & FISCAL APPROPRIATED FORWARD`. The figures are right; the
column NAME carries the title. Change: a map column (e.g. `header_rows_skip:4`) or a rule in
`header_names` that drops header rows whose cells hold no column word.

Also on these pages: APPROPRIATED and FORWARD are one printed column with a two-line header
(lines p55 `APPROPRIATED` left 0.3815, `FORWARD` left 0.3911). A department heading row carries
its forward, the lines under it their appropriation (`Selectmen's Administration $1,131.00`;
`Payroll-Administration $81,270.00 | $82,401.00` = 81,270 + 1,131). Row identities only fire
where BALANCE TO REVENUE is printed. Most of the 189 `check failed` are validator GROUPING misses
(the GRAND TOTAL on p60 summed against every row including subtotals: `rows sum 37,055,421.39`
vs printed `22,439,642.34`), the same kind 2010 shows (72 failed). That is P6 layer 1's block
detection, not a misread.

## 5. capital-plans: the `copy` field

`emit_capital_plan` writes `copy: committee report` on every row. The 2005 rows (p85 t3, t4)
are the copy in the TOWN MEETING MINUTES, Article 5 as voted, not the Capital Planning
Committee's report (which is prose on p12). Change: take `copy` from the map row. The two
tables tie to their own printed SUB TOTALs (529,681.20 and 10,761.36); the page's TOTAL is
540,442.56 and the article votes $540,443.00. `DPW 6 Wheel Dump Truck w/Plow & Sander $96,000.00`
is printed twice and both rows are needed to reach the SUB TOTAL.

## 6. Placement counts are printed, in prose (p48) -- for `placement-counts`

The Special Services report (PDF page 48, `SPECIAL SERVICES DEPARTMENT - SPED`) states:
`two hundred and sixty-four (264) students with disabilities ... 14% of our total student
population`; `eight students received services outside the district during the 2005/2006 school
year. Of the eight, students, seven are in day placements and one is in a residential
placement`. Parts 7 + 1 = 8 tie. No `as_of` date is printed (the FY-era rows use SIMS, 1 March);
the school year named is 2005/2006, a year ahead of the book. This is prose, not a Textract
table, so the table reader cannot land it. Needs a row in `placement-counts.csv` (or that
reader extended to this edition), with `as_of` left unestablished.

## 7. Per-person vital records: a decision for TJ (p75-p80)

Births (p75-77: date, child's name, parents, birthplace), marriages (p77-79: names, residence,
DATE OF BIRTH) and Town Clerk deaths (p80: date, name, age) are NOT LANDED. No dataset holds
per-person births or marriages in any year, and the FY2012 report onward prints counts only,
citing the Registry of Vital Records' recommendation (extraction-plan, FY2012 p105). Landing
names, parents and dates of birth into a searchable database is a privacy call, not an
extraction one. If counts are wanted instead (as `vital_records` holds for FY2011-FY2025), they
are countable from these tables; the 2005 report prints no count of its own. The cemetery burial
list on p11 IS landed (`report-vital-records`, as 2010 p15).

## Integration pass, 28 October 2026

What the one integration agent did with each item above. Counts are this folder's rows after
`read_report_tables.py`; the reasons for anything not applied are here so nobody re-asks.

- **1 treasurer's cash total in the sibling table (p67).** APPLIED: `stated_total=4561756` on p67 t2; 28 accounts publish.
- **2 cash reconciliation identity (p67 t1).** APPLIED, RENAMED to `report-treasurers-cash-reconciliation`: a down-the-page emitter; 9 rows `checked` (the $55,187,400 subtotal is now a row, not a group).
- **3 trust funds 2005 layout.** As asked, no identity added; family renamed `trust-funds-book` (the 2001-2005 layout), so it is never summed with the 2006+ `trust-funds` rows.
- **4 header rows that include the page title (pp55-60).** APPLIED: map `header=skip:4`, and generally the page's running title is dropped from column names everywhere.
- **5 capital-plans `copy`.** APPLIED: map `copy=town meeting article` on p85 t3/t4.
- **6 placement counts in prose.** NOT APPLIED -- prose figures (placement counts, vital-record counts, fire incidents, capital plan prose, pie-chart percentages) need a prose reader; no table reader can land them. `placement-counts` is SIMS-sourced and dated 1 March; these sentences name a school year and no source, so adding them is a decision about mixing two measurements, not a mapping. Recorded here with their pages; nothing was inferred.
- **7 per-person vital records.** NOT APPLIED -- a decision for TJ, not a mapping: named births (infants, parents) and marriages (dates of birth) stay NOT LANDED.
