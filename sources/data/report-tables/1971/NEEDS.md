# 1971 edition: what the shared code needs (for the integration pass)

Edition: calendar 1971 annual town report, `4493-1971-annual-town-report.pdf`, 136 pages. Tables were read on the
53 pages `find_financial_pages.py --list 1971` picked; 68 tables (map.csv), 39 landed pages (pages.csv; 6 `proven`).
Opt-ins in edition.json: those of 1981 (`accountant_marks`, `stop_for_comma_without_dollar`, `id_column_words`,
`recon_net_on_transfer_line`, `stacked_pairs`, `receipts_span`) plus `unlabeled_subtotals` and `rounding_tolerance_usd: 1`.
Hand checks below are computed from `build/textract/out/4493-1971-annual-town-report.cells.tsv`. `--check` reproduces.

## FINDER MISSES

1. **p41, the second half of the General Accounts balance sheet.** Sent by the finder, but Textract returned NO table
   cells for it (lines only). It prints the rest of the appropriation balances (Eliminate Corners 3,478.60 ...
   Winter Recreation Site 193.30), `Overlay Reserved for Abatements` (levy of 1970 4,945.72, levy of 1971 12,040.85,
   total 16,986.57), `Revenue Reserved Until Collected` (86,098.87), `Receipts Reserved for Appropriation` (departmental
   17,549.12, aid to highways 58,266.30 ...), `Surplus Revenue 190,730.40`, the total `$520,694.41` (the same figure
   p40 prints under the assets), the DEBT ACCOUNTS ($1,175,000 serial loans, inside/outside the debt limit) and the
   TRUST AND INVESTMENT ACCOUNTS ($88,163.87 in custody of the commissioners, $1,117.95 school committee). Money
   page, no cells: a re-read of the page (not a reader rule) is needed to land it. p40/3 stops mid-list for this reason.
2. Pages sent with no table and read as prose only (the money is in sentences or warrant text, not a table): p7, p11, p13,
   p28, p74-78 (warrant articles), p86 (Montachusett Regional Vocational School District prose). Nothing missed there
   by eye; p86's assessment figures are in running text.

## ROSTER PAGES

p32 roster of firemen; p101-114 School Personnel Listing 1971-72 (administration, clerical, teaching staff with
education, degree, years of experience and year appointed; custodians and cafeteria staff; no pay printed); p119-120
resignations during 1971 (professional and custodial staff). Written to `rosters.csv`. Not sent for tables.
Not sent either, so out of scope: burials (p20), deaths p79, births p80-81, marriages p82, school enrollment by grade
(p115-116), prize and scholarship recipients (p122-124), staff retirements (p117). The births, deaths, marriages and
burials are named lists in the text; "Everything in the annual reports is public" (TJ, 30 Oct): a later pass reads
them from the text if wanted. No `withheld_rows` is used anywhere in this folder.

## SHARED-CODE CHANGES THE EDITION NEEDS (none made here)

1. **Treasurer's cash, p42/2: `CASH_INVESTED` does not match `Cash in Banks:`.** The roll-forward and the account list
   are ONE table here, and the line that opens the accounts is `Cash in Banks:`. Unmatched, the roll-forward lines
   (127,998.78 ...) are summed as accounts, `accounts sum 11,423,790.26, printed 90,506.42: not published (refused)`, and
   `treasurers-cash.csv` and the reconciliation get 0 rows. TESTED by running the reader once with
   `CASH_INVESTED = re.compile(... + r'|^CASH IN BANKS', re.I)` patched in (folder restored afterwards, `--check`
   reproduces): `7 accounts sum to 90,506.42, the unlabelled figure printed as the last row` (67,361.12 + 2,000 + 3,600 +
   2,000 + 500 + 15,000 + 45.30 = 90,506.42, the figure the page prints as `Balance December 31, 1971 per cash book`).
   The reconciliation then lands 6 rows but `the chain could not be followed`: three more things are needed in
   `emit_cash_reconciliation` for this page: (a) `Balance December 31, 1970` as `opening` (it matches) and
   `Receipts January 1, thru December 31, 1971` as `receipts` (it matches) but there is no `LESS INVESTMENTS` line, the
   page's running subtotal 5,666,641.92 is printed as an unlabelled line after Receipts; (b) one cell holds two labels and
   two figures: `Disbursements January 1, thru December 31, 1971 Cash Balance December 31, 1971 | 5,576,135.50 90,506.42`;
   (c) the closing line is `Balance December 31, 1971 per cash book | $ | $ 90,506.42`, which the `opening` pattern
   excludes (`PER CASH BOOK`) and `ledger` does not match. Chain by hand: 127,998.78 + 5,538,643.14 = 5,666,641.92;
   5,666,641.92 - 5,576,135.50 = 90,506.42. Both printed.

2. **Accountant's schedule (p51-62, `accountant-schedule`): the identity does not apply, 474 rows `no check`.** The column
   headed `Balance to 1972` is not matched by `BALANCE (?:TO )?(?:FY|FISCAL)`. Widen it to `(?:FY|FISCAL|19\d\d)`
   (the 1991 form, absent `ENCUMBERED`: BALANCE TO REVENUE = TOTAL FUNDS AVAILABLE - TOTAL EXPENDED - BALANCE TO 1972,
   blank read as zero on a row printing an available figure). Computed by hand from the cells: **163 of 163 rows that
   print a Total Funds Available figure close**, none fail. Leading marks are also printed BEFORE the figure in two
   columns (`TR 610.00` in Total Expended, `TR` alone in Balance to Revenue; 23 cells in p51-62 begin with a mark): the mark list in
   `accountant_marks` handles marks AFTER a figure only (`1,200,000.00 B`, `2,355.90 RF`, `118.75 Fwd`, `324.15 RC`,
   `21,175.00 ED` are after, and read). The first column is `Approp. Forward` and comes BEFORE the account name (cols
   1-2 are the figures, col 3 the account), unlike 1981.

3. **Detailed statement of receipts (p43-46): five subtotals Textract printed one row low.** The subtotal in the third
   column sits on the NEXT heading's row: `Grants and Gifts:` 469.04 (= interest 3,804.63's section 407.80 + 61.24),
   `Library:` 91,873.11 (= the Schools section above, 30.00 + 153.03 + 74,398.15 + 5,540.88 + 4,464.00 + 6,078.30 +
   333.00 + 217.50 + 556.00 + 102.25), `Cemetery:` 1,410.69 (= the Library fines 1,094.89 + 271.00 + 44.80), `Park:`
   1,950.00 (= Cemetery 1,130.00 + 820.00), `Current Year Refunds:` 4,449.77 (= insurance and damage claims 975.46 +
   896.31 + 62.75 + 460.00 + 397.60 + 1,508.20 + 76.80 + 72.65). Each equals the section ABOVE it, proved row by row
   from the cells, independently of the grand total. The reader counts them as accounts, so
   `accounts sum 5,638,795.75 vs the printed GRAND TOTAL 5,538,643.14` (off exactly 100,152.61 = their sum) and all 147
   rows are `check failed`. By hand, the 32 third-column figures of p43-46 sum to Total Receipts 5,538,643.14 to the
   cent. The rule: a heading label ending `:` with a figure only in the subtotal column, directly under a section whose
   sum it equals, is that section's subtotal. NOT applied here because the README records the same
   reclassify-because-it-closes rule as declined for 1982/1983; here each reclassification is proved by its own
   section sum, not by the grand total.

4. **`tax-collection` (p42/1): labels and the balance column are lost.** `item` is empty on every row and `balance` is
   blank although the page prints it (`5,642.18`, `18,832.84`, `151,379.91` ...). Two causes seen in the emitter:
   the balance column is looked up as `BALANCES`, this page prints `Balance`; and the first column holds the levy
   years as sub-headings (`1968`, `1969`, `1970`, `1971`), which read as figures, making column 1 a figure column so the
   label (`Real Estate`, `Motor Vehicle Excise`) goes nowhere. 1981 and 1986 show the same empty `item`; 1995 and
   2014 do not. The figures themselves (committed with its `Fwd` mark, refunds, payments, abatements, tax titles) are
   read. Page foot totals: commitments $2,608,922.68, refunds $18,797.07, payments $2,346,826.62, abatements
   $98,529.91, tax titles $30,983.31, balance $151,379.91, grand total received $2,352,125.75.

5. **Special articles and funding sources (p70/2-3, p71): `special-articles-voted` and `omnibus-funding-sources` are not
   in `LIST_FAMILIES`**, so they stay `no check`. By hand: transfers from surplus revenue 93,002.20 + other available
   funds 18,163.60 + raise by taxation 67,344.20 (p71/2's 58,541.54 + p71/1's 8,802.66) + borrowing 15,000.00 =
   193,510.00, the printed `Total Special Articles Voted`; the Overlay and article-balance transfers (p70/2) sum to the
   printed 21,355.28. The voted budget (`omnibus-budget`, p69/1-2 + p70/1) closes to `Total Budget Voted` 2,828,113.04:
   82 rows `checked`.

6. **A figure inside a cell with trailing text is lost (p131/1).** `SCHOOL LUNCH (USDA Reimbursements) (*Includes $2281.32
   received for Non-Food | $ 40,433.33* Assistance)`: the figure and the label's tail share a cell, so 40,433.33 (USDA
   school lunch reimbursement, the same figure p43 prints under the Commonwealth) is carried only in the row's `group`
   text. The 32,600.00 and 2,404.51 rows read.

7. **p8 population row**: `7700 E.` (the 1970 population, an estimate) does not parse, so the row prints five values
   for six years; `column_meaning` says which column is which, but a reader taking `v5` as 1970 gets 7,825 (1971).
   Capital Outlay and Loans & Investments have a blank 1965 and the same shift (ordinal `v`, read `columns_as_printed`).

8. **p127/2 lunch finances**: September's food and other bills print `$` with no figure (two cells empty), and April's
   food and other bills are blank; the row `1970: Balance on Hand, September 1, 1970 $7,847.52` is a balance, not a
   month, landed as a row labelled `1970:`.

## NEW dataset names (for the one-name-per-quantity table)

`report-expenditure-history` (p8: population, enrollment and town expenditures at five-year intervals 1950-1971),
`report-veterans-services` (p33: case loads, expended, 50% returned by the State, 1969-1971), `report-school-lunch`
(p127: families `lunches-served-monthly`, `lunch-finances-monthly`, `lunch-receipts-total`, `lunch-bills-total`),
`report-school-spending-shares` (p98: the school dollar by category and by kind, with percents). New families in
existing datasets: `report-school-state-aid` `school-federal-funds-offset` (p130/3) and `school-categorical-aid-received`
(p131/1); `report-school-staff-fte` `school-cost-per-pupil-calendar-year` (p128/3, struck on the calendar year, not the
school year of p128/1). If a sibling worker names the same quantity differently (a school lunch dataset in 1972-1980,
a five-year expenditure table), reuse one name.
