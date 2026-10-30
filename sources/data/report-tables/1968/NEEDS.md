# 1968 edition: what the shared code needs (for the integration pass)

Edition: calendar 1968 annual town report, `4511-1968-annual-town-report.pdf`, 148 pages. Tables were read on the 57
pages `find_financial_pages.py --list 1968` picked; 78 tables (map.csv), 43 landed pages (pages.csv). Opt-ins in
edition.json are those of 1971 plus `unlabeled_subtotals` and `rounding_tolerance_usd: 1`. `--check` reproduces. Hand
checks below are computed from `build/textract/out/4511-1968-annual-town-report.cells.tsv`.

## FINDER MISSES: 0

Every money table sits on a page that was sent. Pages sent with no table or only a one-cell prose table and read as prose
(money in sentences): p25 (the auditor's text; its tax-collection table was read), p55-56, p73-77 (warrant articles),
p91-92, p94. Nothing missed by eye. FIGURES IN NO CELL on pages that were sent (a re-read, not a rule):
1. **p71, funding of the voted budget and special articles (right panel, page lines 92-196).** `Transfers from: Overlay
   Surplus 2,348.00 ... Chapter 616 4,818.99` ($112,229.49), the SPECIAL ARTICLES block (`Transfer from Surplus Revenue`:
   Article 10 7,107.00, Article 20 34,293.00, Article 54 48,600.00, total $90,000.00; `Transfer from Other Available
   Funds` $19,881.49) are in no table cell. By hand they tie: 7,107 + 34,293 + 48,600 = 90,000.00; 407 + 765 + 4,818.99 +
   335 + 300 + 960 + 400.50 + 11,895 = 19,881.49; 90,000.00 + 19,881.49 = 109,881.49; and 96,419.01 (the raised-by-taxation
   articles of p72, read) + 109,881.49 = 206,300.50, the printed TOTAL SPECIAL ARTICLES VOTED. So `special-articles-voted`
   holds only the taxation half, and the funding sources family (`omnibus-funding-sources`, 1971 p70/2) has no 1968 rows.
2. **p26, Old Age Assistance Relief 5,113.85** (page line 83) is in no cell. It is the missing item of the federal grants
   section: 22,839.14 (p26 items) + 104,670.95 (p27 items) = 127,510.09 only with it.

## ROSTER PAGES

p106-109 (resignations, retirements, appointments of school staff) and p120-131 (School Personnel for 1968-69, by
school: name, subject or grade, education, years of experience, year appointed): no pay printed. Written to `rosters.csv`.
Not sent for tables. Births p81-82, marriages p83-85, deaths p86, the jury list p87-89 and enrollment by grade p133-134
were not sent either (no money); named lists, public (TJ, 30 Oct 2026). No `withheld_rows` anywhere in this folder.

## SHARED-CODE CHANGES THE EDITION NEEDS (none made here)

1. **Receipts p26-29: section subtotals read as accounts, and the roll-forward in the same table (annual-report-receipts).**
   Same defect as 1975 NEEDS item 2: a row whose label ends in a colon and whose only figure is in the last column
   (`Trust and Investment Funds: | | 30,794.17`, `Protection of Persons and Property: | | 3,470,183.54`, `Treasurer: |
   | 1,154.40`) is the PREVIOUS section's subtotal printed beside the next heading. The span emitter counts 172 rows as
   accounts (sum 17,488,916.71 against the printed 6,283,781.45) and every row is `check failed`. Walked by hand, every
   section closes on its printed subtotal to the cent (every printed subtotal on p26-29 but the federal grants one), except the federal grants section, which
   lacks the cell in item 2 of the misses above. The real accounts whose only figure sits in the last column
   (Farm Animal Excise 515.23, Interest 2,443.37, Trailer Park Assessments 4,746.00, Commission on Telephone Booth 158.76,
   Highway - Machinery Fund 9,074.58, Tree Warden - Machinery Fund 215.50, Previous Year Refunds 114.11) are 17,267.55. By
   hand: 6,261,400.05 (accounts in column 2) + 17,267.55 + 5,113.85 (missing cell) = 6,283,781.45, the printed Total
   Receipts. A second cause: p26/1 holds the END of the roll-forward (`Disbursements 6,405,374.17`, `Cash Balance
   208,225.52`), the bank list (2,089.34 + 154,997.01 + 25,000.00 + 26,139.17 = 208,225.52) and the start of receipts in ONE
   table, so those lines land as receipts. Change: (a) the section-subtotal rule of 1975 item 2; (b) a way to split one table
   by row range between two datasets (a `rows` column in map.csv), or an emitter that reads `Detailed Statement of
   Receipts` as the start of the receipts. Same as 1971 NEEDS (receipts check failed on p43-46).
2. **Payments p30-33 tie by hand but the reader prints `no check` (checks none, as 1971).** The section subtotals close on
   their rows: 103,130.48; 128,960.00; 62,492.74; 238,116.29; 164,057.44; 2,246,099.00; 33,431.27; 9,322.70; 26,929.86;
   21,499.20; 575,756.76 (of which the payroll deductions subtotal 397,368.28 is printed beside `Payroll Attachments
   105.81`); 22,600.83; 3,930.82; 75,886.50; 2,295,000.00 sum to 6,405,374.17, the printed Total Payments (p33), which is
   also the Disbursements of the p26 roll-forward. No change asked; the evidence is here.
3. **Treasurer's cash: no `treasurers-cash` or reconciliation rows.** The roll-forward (Balance Dec 31, 1967 329,818.24 +
   Receipts 6,283,781.45 = 6,613,599.69; less Disbursements 6,405,374.17 = Cash Balance 208,225.52) is printed ABOVE the
   table on p26, in page lines 2-15 with no cell for its first rows; the cells begin at `Disbursements`. Both identities
   hold by hand. Landing it needs the same change as item 1(b).
4. **p48/1 (Sidewalks and Grounds) header cell reads `Sidewalks December 31, 1967`**; the table is one fund and landed with
   header none. No change asked.
5. **p21 pie charts NOT LANDED.** Two pies (`We Received`, `We Spent`) with a lettered legend; ten of about twenty slice
   labels reached a cell (two 5-row tables), the big slices' amounts and percents are in page lines outside any cell
   (e.g. `$1,390,600.47`, `49.5%`, `$402,983.90`) and the letter-to-slice key is graphical. A re-read of the page is needed.
   The statements the pies summarise are p26-33, which are landed in full.
6. **Proposed salary schedule p13**: three tables, one header row (13/1 row 2); 13/2 has 8 columns and 13/3 three
   unnamed steps. Landed with `header_from` / header none; mixed units in the cells (annual `3500`, hourly `2.10`, weekly
   `35wk`, yearly `1700yr`) as printed. The step names of 13/3 are `not established`.

## What this report prints that 2010 did not

A voted budget for the calendar year with a footnoted Reserve Fund; the Treasurer's statement of receipts and payments
for the calendar year; a general-accounts balance sheet with deferred revenue, debt and trust accounts; a School
Department summary with special federal-fund accounts (Public Law 874, Title I, Title III, NDEA, Headstart); the proposed
classification and salary schedule; the school lunch program month by month; no wage list, no stabilization fund
statement other than the one in the School Committee's trust report (p49, 11,828.77).

## Integration pass, 31 October 2026: what was done

Names and opt-ins are in `sources/data/report-tables/README.md` (1959-1970). Pages proven/unproven/refused:
16/26/1 as the worker left the folder -> 21/21/1. Renamed: none.
Opt-ins set: `colon_heading_subtotals`, `cash_book_list`, `recon_no_transfers`, `dash_zero`, `accountant_marks_wide`, `accountant_marks_before`, `marks_wide`, `year_labels`, `statement_span`, `receipts_stop_at_grand`, `unit_rates`.
By kind of item above: the treasurer's-cash roll-forward (`Cash in Banks:` / `per cash book`) -> `cash_book_list` +
`recon_no_transfers`; the accountant's `Balance to 19xx` identity -> always on since 1971-1980, `TR` before a figure ->
`accountant_marks_before`; section subtotals printed on the next heading -> `colon_heading_subtotals` (dropped only
when equal to their own section to the cent, listed in notes.csv); payments over several pages -> `statement_span`;
the Tax Collector's past-participle columns -> `collector_columns` where it moved a row; `cr`/`CR` credits ->
`credit_marks`; leading `+`/`*` -> `signed_figures`; unit-suffixed rates -> `unit_rates`; `-0-` -> `dash_zero`.
NOT APPLIED (reasons in the README): the `rows` map column (one table feeding two datasets), debt schedules wider
than `MAX_V` 8, a one-issue debt group's repeated subtotal, a figure at the end of a label cell, two figures or a
figure and words in one cell, `II`/`I`/`O` read as digits (built behind `roman_counts`, measured, not set), a leading
or trailing `-`, digit groups split one per cell (1963 p9), text-valued town-facts rows, side-by-side trust panels,
and every figure Textract put in no cell (re-read list). `locate_cell_misreads.py`: 0 candidates.

## Close-out, 30 October 2026: every financial page proven or blocked

Pages proven / unproven / refused: 21 / 21 / 1 before, 39 / 3 / 1 after; the 4 not proven are registered as blocked (scratchpad file for `page-blocked.csv`, appended by the parent).

Readings and identities opted into in `edition.json` (each documented where it is defined in `scripts/read_report_tables.py`, or `scripts/declared_identities.py`): `expended_from_amounts`, `ed_mark`, `stepped_subtotals_in` (5), `receipts_two_columns`, `school_statistics_totals`, `dollar_sign_labels`, `cell_readings` (1), `declared_identities` (2), `collector_balance_identity`.

Blocked: p11 (not a financial table: a short history with no printed identity); p13 (not a financial table: a schedule of pay rates with no printed identity); p21 (chart, not a table); p139 (not a table with a printed identity: appropriation beside expenditure, no total).
