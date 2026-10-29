# 1997 edition: what the shared code needs (for the integration pass)

Written by the 1997 worker, 29 October 2026. Nothing here was changed in shared code; each item
says the exact change, why, and the pages. Figures marked "by hand" were recomputed from
`build/textract/out/4523-1997-annual-town-report.cells.tsv` by column position, not read off a
rendered table.

## 1. School wage list: the GRADE column is read as an amount (pp90-96) -- 343 rows `check failed`

`SCHOOL EMPLOYEES / REPORT OF WAGES PAID` prints `NAME | POSITION | GRADE | GROSS WAGES`. GRADE is
the salary lane and step (`M+75 MAX`, `B9`, `0`, `2`, `M 1 (.60)`). Where it is a bare integer the
reader takes it as a figure, so `v1` is the step and the wage goes to `v2`; `coverage()` reads `v1`
only, so every school page fails (7-13 figures per page "not captured", the same number "not in
the text": the steps). 1998 (same layout) has the same defect.

- **Change:** in `records()`, a column whose PRINTED header matches `GRADE|STEP|DEGREE` is never a
  figure column (text, part of the label) -- or, more generally, `id_columns()` should also take an
  integer-only column to the RIGHT of the text when the table's money column carries `$`.
- **Proof it is the reader, not the page (by hand):** taking column 4 alone, the 342 school rows
  sum to exactly **$7,169,207.04**, the printed `TOTAL SCHOOL GROSS WAGES` (p96), and 342 is the
  printed `TOTAL SCHOOL EMPLOYEES`.

## 2. Wage stated_total is summed against EVERY wage row of the edition

`coverage()` sums all `report-gross-wages` rows against the last `stated_total`. 1997 prints two
lists: the school list WITH a total (p96, `7169207.04`, in map.csv) and the town list (p97) with
none. So the school total is compared with school + town rows (7,443,861.96 incl. the 52 town rows
at 783,775.86) and can never tie, even after item 1.

- **Change:** scope a `stated_total` to the run of map rows it closes -- the contiguous pages of
  the same `name` ending at the page that carries it (here pp90-96) -- not to the whole dataset.

## 3. Collection of taxes: 1997 prints no ADJUSTMENTS column, so no row identity applies (p66)

`IDENTITIES['collection-of-taxes']` needs `ADJUSTMENTS`; 1997's header is
`TAX | FORWARD | COMMITMENTS | REFUNDS | PAYMENTS | ABATEMENTS | TAX TITLE | BALANCES`, so the
identity is not applied and `proof` is blank on all 28 rows.

- **Change:** add a variant
  `('BALANCES', [(1,'FORWARD'),(1,'COMMIT'),(1,'REFUNDS'),(1,'PAYMENTS'),(1,'ABATEMENTS'),(1,'TAX TITLE')], {'absent': ['ADJUSTMENTS']})`.
- **Tested by hand on this page's rows:** 28 of 28 foot, GRAND TOTAL included.

## 4. Omnibus line numbers with a sub-line (`122.1`, `914.1`) and `NEW BGT` are read as amounts (pp81-82)

`ID_TEXT` accepts `1518`, `2830-2838`, not `122.1`. On p81 table 2 column 1 and p82 column 4 the
line numbers include `122.1`, `141.1`, `914.1`-`914.3` and `NEW BGT`, so the columns are figure
columns and every line number became `v1`. The map works around it with `layout=spans:2-3` (p81/2)
and `spans:1-3,5-6` (p82): amounts are right, but those rows carry NO line number.

- **Change:** `ID_TEXT = r'^\d[\d\s\-/&]*(\.\d)?$'` (one decimal digit, only in a table whose
  amounts carry `$`), and accept an all-caps non-numeric code (`NEW BGT`) in a column that is
  otherwise identifiers. Then drop the two `spans` from map.csv.
- **Second defect, same pages:** p81 table 2 column 4 holds the line numbers (`299`, `300` ...) of
  the RIGHT-hand column, whose names and amounts Textract returned as table 1. Pairing them needs
  a row-wise join of 81/2 col 4 to 81/1 (same row index); not attempted.
- **By hand:** the 85 amounts read on pp81-82 sum to $13,533,289, $200 under the printed
  `TOTAL BUDGET $ 13,533,489.00`; `COUNCIL ON AGING` (p81, last line of the right column) prints
  no amount. Not resolved; not inferred.

## 5. `header_from` cannot point FORWARD (p61 continues p62)

The trust fund book is printed with its continuation first: p61 (library accounts, `TOTAL CENTURY:`,
`GRAND TOTAL TRUST FUNDS: $ 726,988.53`) continues p62, which carries the header. `prev_header` is
filled in reading order, so `header_from=62/1` on p61 resolves to nothing and p61's columns are
`not established`.

- **Change:** resolve `header_from` in a first pass over all mapped tables before building records.

## 6. Parser mark: `0,13452` (comma for the decimal point in a fraction), p62 row 7

The ALLOCATION share of `SALE OF CEMETERY LOT` reads `0,13452`; unparsed, so `TOTAL COLONIAL: 1`
fails by exactly 0.13452 (triage calls it grouping) and that row's values shift one v-column.

- **Change:** in `validate_totals.REPAIRS`, `^0,(\d{4,})$` -> `0.\1` (a leading zero then a comma
  and four or more digits cannot be a thousands separator). The allocations then sum to 1.00000
  (by hand: 0.86548 + 0.13452).

## 7. Debt repayment schedule p65: a merged label breaks the validator's blocks

Row 21 is read `TOTAL MUNICIPAL PURPO MASS WATER POLLUTION`: the 1995 issue's total line and the
next issue's heading in one cell. The validator then sums the wrong blocks for `GRAND TOTAL
INTEREST` (`rows sum 0.00`) and 12 rows fail. **By hand:** for every fiscal year 1998-2017 and
TOTAL, the PRINCIPAL rows sum to `GRAND TOTAL PRINCIPAL` exactly ($2,183,000 in all); the INTEREST
rows sum to `GRAND TOTAL INTEREST` except 1998 (+1), 1999 (-1), 2000 (-1) and TOTAL (-1), and
`GRAND TOTAL PRINCIPAL + INTEREST = TOTAL DEBT` except 2000 (292,781 vs printed 292,782) --
whole-dollar rounding as printed. No change requested beyond a note: the rows are `check failed`
partly for the reader's grouping, partly for the page's own $1 roundings.

## 8. Page subject: p82 is classed `trust-and-stabilization`

`pages.csv` gives p82 the subject `trust-and-stabilization` (Article 38's prose mentions the
Stabilization Fund). The page's table is the FY1998 omnibus budget (`report-appropriations`,
family `omnibus-budget`), as p81 is. Subject should follow the map's dataset where one is landed.

## 9. A placement count printed in prose (p41) -- for `placement-counts`

Special Education Department report, p41: *"Approximately two hundred students in the district are
currently identified with a disability ... This figure represents 11% of the total school
population ... Eleven students receive services in out-of-district placements."* No date or SIMS
source is printed with it (FY2013-FY2025 cite SIMS Report 7, 1 March). Not landed here (prose, not
a table); the integration pass decides whether `placement-counts` takes a prose figure with no
stated date.

## 10. Wage family name across 1996-1999

1997 uses family `gross-wages` (as 1998) for both lists, period NOT PRINTED. 1999 uses
`gross-wages-school` for its school list. One name per layout should be settled once.

## FINDER MISSES

**None found.** Every page with no cells was read in lines.tsv for money figures: pp10, 31 (one `$`
amount each, in prose), 75, 77, 78, 87 (article prose and by-law section numbers) are prose, not
tables. Two pages are financial but print SHARES only, no amounts, and were rightly not sent:
p47 `GENERAL FUND REVENUES FY 97` and p56 `GENERAL FUND EXPENDITURES FY 97` (pie charts:
`PROPERTY TAXES 68%`, `Education 64%` ...). Fourteen picked pages returned no table at all
(pp11, 12, 16, 17, 18, 21, 22, 23, 73, 80, 83, 84, 85, 86): department and town-meeting prose with
amounts in sentences.

## ROSTER PAGES

Three school staff rosters, none sent for tables (no money), for `dump_roster_pages`:

- p35 `SCHOOL STAFF` (High School, by department)
- p38 `THOMAS C. PASSIOS ELEMENTARY SCHOOL FACULTY`
- p40 `TURKEY HILL MIDDLE SCHOOL STAFF 1997 - 1998` (lower half of the page)

Also, already landed: p27 `ROSTER OF FIREFIGHTERS` (report-officials) and the school wage list
pp90-96, which names every school employee with POSITION and GRADE (report-gross-wages).

## Document defects (our copy)

- Town wage list p97 stops at `GENDRON` (read `ENDRON`) with the bottom clipped; pp98-99 are blank
  scans; no town total anywhere. Registered in gaps.csv.
- Some p97 surnames are clipped at the left edge (`ROST, NORMA B`, `ENDRON, JAMES A`); left as read.

## What the integration pass did with each item (29 October 2026)

Applied ONCE in the shared code (see `sources/data/report-tables/README.md`, "Added by the 1991-2000 integration pass"); counts are this folder's rows after the re-run.

- **1 GRADE as an amount**: APPLIED. 395 of 395 wage rows `checked` (were 343 failed).
- **2 one total per list**: APPLIED; school 342 rows = 7,169,207.04 = printed.
- **3 taxes without ADJUSTMENTS**: APPLIED.
- **4 `122.1` line numbers**: APPLIED; `NEW BGT` NOT; the `spans` workarounds stay (they also drop 81/2 col 4, the right column's line numbers). The omnibus list total APPLIED: 85 amounts 13,533,289 against 13,533,489, off 200 -- `check failed`, honestly.
- **5 `header_from` forward**: APPLIED (p61 takes p62's header).
- **6 `0,13452`**: APPLIED; ALLOCATION now closes, DIVIDENDS is off 0.02, honestly.
- **7 debt p65 merged label**: NOT APPLIED (validator grouping).
- **8 p82 subject**: APPLIED (`appropriations`).
- **9 placement count in prose (p41)**: NOT LANDED -- `placement-counts.csv` is generated (`extract_placement_counts.py`) and every row carries a stated `as_of` date and its SIMS source; this sentence states neither. Recorded as unfinished in the README.
- **10 wage family**: settled -- `gross-wages-school` (pp90-96), `gross-wages-town` (p97).
- **Document defect**: the town list's truncation (p97 clipped, pp98-99 blank) is registered in `sources/data/document-defects.csv`.
- **ROSTER PAGES**: p35, p38, p40 read into `sources/data/rosters/1997-p*.json`.
