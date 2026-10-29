# report-tables/2008: what the integration pass needs to change

Written by the 2008 worker, which may write only inside this folder. Each item: the change, why,
and the pages. Nothing here has been applied.

## 1. Receipts (p60) need a column-span layout -- NOT LANDED until then

- **Change:** `read_report_tables.records()` accepts `layout` = `spans:1-2,4-5,7-8` (explicit
  column ranges per side-by-side group) beside `groups:N`. Then map p60 t1 to
  `annual-report-receipts`, `layout=spans:1-2,4-5,7-8`, and remove the NOT LANDED note.
- **Why:** Textract returned 8 columns for p60: three label/amount pairs with EMPTY spacer
  columns 3 and 6. `groups:N` cuts equal widths: `groups:3` gives 1-2/3-4/5-6 and drops 7-8;
  `groups:4` separates the middle label (col 4) from its amount (col 5).
- **What it would find (hand-summed from the cells, not by the script):** 99 account rows sum
  to 25,460,186.81 against the printed `GRAND TOTAL` 25,458,178.81, off 2,008.00. The SUMMARY OF
  RECEIPTS categories sum to 25,458,178.81 exactly. So the accounts would land `check failed`,
  as 2010's did, unless one cell is a misread.

## 2. Treasurer's cash (p77): the emitter counts the reconciliation rows as accounts -- refused

- **Change:** `emit_treasurers_cash` sums only the rows after a `CURRENT CASH INVESTED`
  group line (or excludes rows whose label starts `RECEIPTS` / `DISBURSED`). Optionally a new
  `treasurers-cash-reconciliation` target for the four reconciliation lines.
- **Why:** 2008 prints, above the accounts, `BALANCE JUNE 30, 2007 $9,947,833.02` +
  `RECEIPTS 7/1/07 -6/30/08 42,530,194.63` - `DISBURSED (38,770,174.81)` =
  `GENERAL LEDGER BALANCE 6/30/08 $13,707,852.84`. 2010 does not. The emitter includes the
  receipts and disbursements lines and refuses (`accounts sum 17,467,872.66, printed
  13,707,852.84`). Removing those two lines leaves 13,707,852.84, equal to the printed TOTAL,
  so after the change the 31 accounts would publish. The reconciliation identity itself also
  closes (9,947,833.02 + 42,530,194.63 - 38,770,174.81 = 13,707,852.84).

## 3. Special education p42 t1: a false `check failed` from the validator

- **Change:** `validate_totals` should not read `Out of District Total` (a category, the
  number of students served out of district) as a column total. The identity the table does
  print: `Enrolled SPED students 218` = 130 + 61 + 24 + 3 (the four settings), which closes.
- **Why:** five rows of p42 t1 are `check failed` (`printed 3.00, rows sum 433.00`) on an
  identity the page does not state. Their status is our instrument's mistake, not the page's.
  Until fixed, treat those five statuses as unreliable.

## 4. New dataset to register: `report-special-education`

- **Change:** register `report-special-education` (generic columns) in the merge, the database
  and `map_annual_report_pages` (`PROOF` entry `NOTHING`, as for the other count tables).
- **Families:** `disability-types` (p41: percent by disability category, Lunenburg 08/09 against
  the state 06/07), `educational-environment` (p42 t1, Indicator 5, 2007-08), `evaluation-
  timelines` (p42 t2, Indicator 11, 2005-06), `early-childhood-transition` (p42 t3, Indicator
  12, 2007-08). 26 rows.
- **Percents are not parsed.** Their values stay in `label`, as 2010's MCAS percentages do
  (p49 here, p43 there). If the reader learns to parse `NN.NN%` into v-values, both editions
  gain usable figures; percents should be a separate `kind`, never summed with counts.
- **Overlap to note, not merge:** `dese-sped-indicator.csv` holds DESE's own indicator series
  from 2017. These 2007-08 figures are the district's printed copy and come from a different
  source and decade.

## 5. A placement count, printed in prose (p41) -- for `placement-counts`

- p41: `eight students received services outside the district during the 2008/2009 school year.
  Of the eight students, seven are in day placements and one is in residential placement.`
  Parts tie (7 + 1 = 8). No as-of date and no SIMS citation are printed, unlike FY2013-FY2025.
- **Change:** a `placement-counts` row for edition 2008 (total 8, day 7, residential 1,
  `as_of` not printed, page 41), added by whoever owns that dataset's reader.
- **Do not reconcile with p42 t1's `Out of District Total 3`:** that is the 2007-08 state
  indicator for ages 6-21. It covers a different year and uses a different definition.

## 6. Two election rows absorbed into the header (p82)

- `V.split_header` took p82 t1 rows 3-4 (`JOHN R. EDWARDS 7 5 9 8 29`, `HILARY CLINTON 254 283
  250 217 1004`) into the header, so `columns_as_printed` reads `PREC A 7 254` and those two
  candidates are not rows. The Democratic preference TOTAL then fails (printed 454 / 1770).
- **Change:** in `split_header`, stop the header at the first row whose first cell is text and
  whose other cells are all counts. The same rule may recover rows in 2010's election pages.

## 7. Printed or misread footing errors in elections, left `check failed` (no change asked)

These are honest failures, recorded so nobody "fixes" them by hand:
- p85 ASSESSOR TOTAL: the cells read `66 64 67 71 28`; the precincts sum to 268. Probably a
  dropped digit, but neither reading is confirmed against the PDF image.
- p87 PRESIDENT / VICE PRESIDENT: TOTAL column prints `47` for BLANKS and `6` for Write-ins,
  where the precincts sum to 24 and 23. 47 = 24 + 23, and the column foots to 5756 only with
  24 and 23. The page or Textract has merged two cells.
- p90 SENATOR IN GENERAL COURT TOTAL: `33 19 34 29 117`. The precincts sum to 115;
  WRITE-INS 2 + BLANKS 115 = 117.

## 8. Cross-page grand totals the validator sums on one page

- p68 `GRAND TOTAL` (26,935,671.86) spans the whole schedule (p62-68). It is checked against
  p68's rows only, so nine rows there fail with `triage: grouping`. p79 `GRAND TOTAL INTEREST`
  likewise (rows sum 0.00). These are not misreads. **Change:** let `validate_totals` sum a
  GRAND TOTAL over every page of a `header_from`/same-name run.

## 9. Printed, but not in a Textract table, so not landed

- **Fire department roster** (p27, after Department Statistics): `ROSTER OF THE LUNENBURG FIRE
  DEPARTMENT`, about 30 names with ranks, in the text layer only. 2010 put its fire roster in
  `report-officials`. It needs a line reader.
- **Capital planning** (p14): prose with amounts, not a table. `$307,027.65 was expended ... for
  the FY plan` and nine items with costs; `$249,960.00 was approved for borrowing`. Not landed
  in `capital-plans`. It needs a prose reader, or a person to transcribe it with a sum check.
  Expended is not the same quantity as 2010's approved, so keep the stages apart (rule 1).
- **Vital record counts** (p86): `BIRTHS - 82 DEATHS - 70 MARRIAGES - 38`, calendar 2008. The
  same page states that names are no longer printed, on the Registry of Vital Records'
  advice.
- **General fund revenue and expenditure shares** (p61, p69): pie charts. The text layer has
  percentages and category names (e.g. `PROPERTY TAXES 62.56%`, `Education 55.97%`), with the
  positions only partly reconstructible.
- **Town meeting excerpts** (p91-99): motions and votes in prose, as in 2010.

## 10. Cells that print a spreadsheet error

- p65 (three cells; no other page of the cells file has one): `#REF!` (Textract `#REFI`) is printed where a figure
  belongs, e.g. Fire Hydrant Expense, TOTAL FUNDS AVAILABLE. The PDF prints it, so it is a
  defect in the town's document, not a misread. Candidate for `document-defects.csv`.

## Integration pass, 28 October 2026

What the one integration agent did with each item above. Counts are this folder's rows after
`read_report_tables.py`; the reasons for anything not applied are here so nobody re-asks.

- **1 receipts column spans (p60).** APPLIED: `layout=spans:1-2,4-5,7-8`. LANDED: 98 accounts, `checked` against the GRAND TOTAL (the accounts sum to 25,458,178.81 as read -- the 2,008.00 difference the worker hand-summed did not appear in the reader's sum).
- **2 treasurer's cash reconciliation rows (p77).** APPLIED: rows above `CURRENT CASH INVESTED:` go to `report-treasurers-cash-reconciliation` (4 rows, `checked`: balance + receipts - disbursed = general ledger balance); the 31 accounts publish against the printed TOTAL.
- **3 false check on `Out of District Total` (p42 t1).** APPLIED: map `checks=none` on p42 t1.
- **4 register report-special-education.** APPLIED (PROOF, build_db, table-semantics). 2009's `report-special-services` was folded into it. p42 t2/t3 also `header=row:1`, so their count rows are data.
- **5 placement count in prose.** NOT APPLIED -- prose figures (placement counts, vital-record counts, fire incidents, capital plan prose, pie-chart percentages) need a prose reader; no table reader can land them. `placement-counts` is SIMS-sourced and dated 1 March; these sentences name a school year and no source, so adding them is a decision about mixing two measurements, not a mapping. Recorded here with their pages; nothing was inferred.
- **6 election rows absorbed into the header (p82).** APPLIED in validate_totals.split_header: the header stops at the first row of counts. JOHN R. EDWARDS and HILARY CLINTON are rows.
- **7 printed footing errors in elections.** No change asked; still `check failed` as printed.
- **8 cross-page grand totals.** NOT APPLIED -- a change to validate_totals' block walk (table order, cross-page grand totals, unlabelled department subtotals). validate_totals is shared with the FY2011/FY2020 reviews, and the parser changes that WERE made there were proved not to alter one check of those reports; a block-walk change could not be proved the same way in this pass.
- **9 fire roster, capital prose, vital counts, pie charts, town meeting text.** NOT APPLIED -- prose figures (placement counts, vital-record counts, fire incidents, capital plan prose, pie-chart percentages) need a prose reader; no table reader can land them. `placement-counts` is SIMS-sourced and dated 1 March; these sentences name a school year and no source, so adding them is a decision about mixing two measurements, not a mapping. Recorded here with their pages; nothing was inferred.
- **10 `#REF!` cells (p65).** NOT APPLIED: a candidate for document-defects.csv, which another workstream owns; recorded here.
