# 1965 edition: what the shared code needs (for the integration pass)

Edition: calendar 1965 annual town report, `4508-1965-annual-town-report.pdf`, 138 pages (a scan: Textract text on 137 of
138 pages). Tables were read on the 60 pages `find_financial_pages.py --list 1965` picked; 73 tables (map.csv), 41 landed
pages (pages.csv; 2 `proven`: p76 and p77, the voted budget, which closes on its printed total). Opt-ins in edition.json are
the 1981 set plus `unlabeled_subtotals` and `rounding_tolerance_usd: 1`. Hand checks below were computed from
`build/textract/out/4508-1965-annual-town-report.cells.tsv`. `--check` reproduces. The reader limits that repeat the 1971
and 1975 folders are referenced, not re-described.

## FINDER MISSES

1. **p22, `Deferred Revenue Accounts`.** The top of the page prints `Apportioned Street Assessments Not Due`, `Uncommitted
   Apportioned Street Assessment $ 795.97`, `Revenue Due 1966 through 1980 $ 795.97` (lines 1-6 of the page): money, no cell.
   Page 22 was sent and has four tables, none of them this block. A re-read is needed to land it.
2. **p20-21, the asset total.** No cell of the asset table (20/1) holds the total; the liabilities side closes on `$368,057.93`
   (21/1 last row). By hand the asset side's unlabelled subtotal column sums to the same 368,057.93.
3. **p4, `Assessed Valuation: $11,810,645 (Real Estate - $10,983,935; Personal Property - $826,710)`.** Textract split the value
   over two rows (`Assessed Valuation:` / `Property - $826,710)`), and the reader keeps only rows with one figure, so the row
   is NOT in `report-town-facts` (4 of 19 rows landed: Settled, Population, Tax Rate, a representative; the others are
   text-valued with no figure). The valuation also lands as `report-valuation` p8 (1965 row: 11,810,645). Change: let
   `report-town-facts` keep text-valued rows (as 1978 p3 does) and join a wrapped value.
4. **p18**, the pie `Where Did Your 1965 Tax Dollar Go?` (cents per dollar: `83.0c SCHOOLS`, `7.3c`, `75.7q`): sent, no cells,
   percent-like figures only, no dollar amounts. Not a money table by the brief's rule. The dollar legend of the same two
   pies is p19 (landed).
5. Pages sent and read as prose (no cells, nothing missed by eye): p56 (Sealer: `158 weighing devices inspected in 1965`),
   p69, p71, p72, p74, p78-p84 (warrant articles; the amounts are in running text), p132 (School Lunch Program prose; its
   table is p134).

## ROSTER PAGES

p107-109 school Resignations and Appointments (name, date, location, replacement); p118-128 School Personnel listing (name,
education, degree, years of experience, year appointed, subject or grade; no pay printed); p129-130 enrollment by grade and
teacher. Written to `rosters.csv`. Not sent for tables. Not sent either, so out of scope: officials (p5-6), births (p85-86),
marriages (p87-88), jury list (p89-90), arrests list (p52), population and school enrollment table (p64). Births, marriages and
the jury list name people: "Everything in the annual reports is public" (TJ, 30 Oct); a later pass reads them from the text.
No `withheld_rows` is used.

## SHARED-CODE CHANGES THE EDITION NEEDS (none made here)

1. **Detailed statement of receipts (p23-26): four section subtotals printed on the next heading's row.** Same as 1975 NEEDS
   item 2 and 1971 item 3. Here: `Commonwealth of Massachusetts: | | 83,142.92` (the Federal grants subtotal, p24 row 15),
   `County: | | 397,894.14` (the Commonwealth's, row 52), `Trust Funds: | | 238,167.96` (Agency, p25 row 11) and `Licenses and
   Permits: | | 6,315.79` (Trust Funds, p25 row 20). Their sum is 725,520.81 and the reader's `accounts sum 3,438,474.85 vs the
   printed GRAND TOTAL 2,712,954.04` is off by exactly that, so all 138 rows read `check failed`. By hand, the 28 third-column
   figures of p23 (rows 15-41) to p26 sum to Total Receipts 2,712,954.04, to the cent (computed from the cells; the grand total
   is the 29th).
2. **Treasurer's cash reconciliation split across two tables (p23/1 rows 1-14, p23/2).** Textract put the roll-forward in two
   tables and the statement of receipts in the first of them from row 15. 23/1 rows 1-14 hold `Balance December 31, 1964
   $127,120.62`, the subtotal `2,840,074.67` (twice), `Disbursements ... 2,813,603.77`, `Cash in Banks:`, `State Street Bank
   and Trust Company`, `Cash on Hand 3,244.69` and the closing `$ 26,470.90`; 23/2 holds `Receipts ... 2,712,954.04`, `Cash Balance
   December 31, 1965 26,470.90`, `Balance December 31, 1965 per cash book $26,470.90` and `Worcester County National Bank regular
   Account 13,226.21 / per bank statement 10,000.00`. Mapped as `treasurers-cash` with `header: skip:14` on 23/1 so the receipts
   are not polluted; the emitter refuses: `accounts sum 23,226.21, printed 26,470.90` (the 3,244.69 cash on hand is in the
   other table), so `treasurers-cash` and the reconciliation get 0 rows. By hand: 127,120.62 + 2,712,954.04 = 2,840,074.66
   (printed .67, one cent); 2,840,074.67 - 2,813,603.77 = 26,470.90; 13,226.21 + 10,000.00 + 3,244.69 = 26,470.90. Change: an
   emitter that pools a reconciliation across the tables of one page, or a re-read of the page.
3. **Accountant's schedule (p31-43): a row with only `Amounts Expended` read as a failure.** The identity now applies (the
   reader was widened to `Balance to 1966` while this folder was being written: 155 rows `checked`, 15 `check failed`, 326
   `no check`, the last being rows with no Total Funds Available figure), as 1971 NEEDS item 2 asked. The 15 failures are
   rows whose only expended figure is printed in `Amounts Expended` with `Total Expended` blank (a one-line account does not
   repeat it); the reader reads Total Expended as 0 and the row as off by that amount. By hand, with Amounts Expended taken as
   the total expended, 12 of the 15 close (p32 Purchase Office Equip. 1,698.00 - 1,645.60 - 52.40; Revaluation Study
   Committee 200.00 - 5.10 - 194.90; Development & Industrial Commission 185.00 - 37.50 - 147.50; p33 Radio Equipment 800.00 -
   762.26 - 37.74; p36 Chapter 90 Construction 1965 and 1963; p37 Dump Truck and Plow 567.00 and the 4,000.00 line, whose
   balance prints `07` for .07; p39 Adult Education Self-Supporting 749.00 - 698.00 - 51.00; p41 Resurface Courts, Fence and
   Gates, Playground Equipment). Three do not: p34 `Transfer` (5,125.00 available, 500.00 expended, no balance), p40
   `Construct, Equip and Furnish ...` (451.72, nothing else in the cells) and p43 `Interest on Temporary Loans` (available
   2,218.34, Total Expended 2,218.35: one cent, a digit in the scan or a printed discrepancy; not corrected). Change: when
   `Total Expended` is blank and `Amounts Expended` has the line's only figure, use it. Other limits: the first two figure
   columns come BEFORE the account name; marks print after the first figure (`300,000.00 B`) and sometimes before another
   (`7,504.22 TR`); `p38/1` has a header that swallowed a data row (`Accounts Aid to Families with Dependent Children ...
   A.F.D.C. Cash Grants 9,557.49` in the header cell), so its named columns are not trustworthy; p39/28 reads `870.598.00`
   (a full stop for the comma) and is not taken as a figure.
4. **Bonded indebtedness p44/1: unlabelled group subtotals counted as bonds.** 13 rows read `check failed`: `Paid Principal
   ELEMENTARY ... printed 1,539,000.00, rows sum 2,413,000.00`. The three group subtotals (900,000 / 1,095,000 / 150,000 and
   their paid columns) are rows without a label, and the reader sums them as issues. By hand, the issues sum to the printed
   `Grand Totals:` in every column except Total Principal: Paid Principal 760,000 + 665,000 + 114,000 = 1,539,000; Paid 1965
   50,000 + 75,000 + 18,000 = 143,000; interest 128,538 + 192,600 + 6,396 = 327,534; balance 90,000 + 355,000 + 18,000 =
   463,000. The Grand Totals cell for Total Principal reads `$ 168,200`, which cannot be right (1,539,000 + 143,000 =
   1,682,000 and the three groups' Total Principal are 810,000 + 740,000 + 132,000 = 1,682,000): a dropped digit in the scan or
   in Textract, NOT corrected here. One row prints `13,079:28` (a colon for the full stop). Change: a row with no label and
   figures under a bond group is a group subtotal.
5. **School summary p111, one false `check failed`.** `TOTAL 1965 EXPENDITURES: $887,597.92` sits below the table's total in
   the `SPENT 1965` column and is tested as that column's total (`rows sum 0.00`). It is the Committee's own line: 870,597.92
   spent + 17,000.00 Public Law 874 = 887,597.92, by hand. The other 14 rows of the table are `checked`.
6. **Special articles (p77/3 and p77/1): block subtotals counted as articles.** The three funding blocks end on unlabelled
   subtotals (123,035.04; 27,432.46; 7,475.00), so the LIST TOTAL against `$157,942.50` is not attempted and 49 rows read
   `no check` (as 1971 p70-71). By hand: block one 123,035.04 = the 31 articles of 77/3 and 77/1; block two 27,432.46 = 12
   lines; block three 7,475.00 = 6,500.00 + 975.00; 123,035.04 + 27,432.46 + 7,475.00 = 157,942.50, the printed total. The
   omnibus (76/1, 76/2, 77/2) is `checked` on all 78 rows against `TOTAL BUDGET VOTED: $1,427,565.00` (proven pages 76, 77).
7. **p46/2 trust funds, two panels interleaved.** Cemetery Perpetual Care (left) and the Library fund (right) share one
   eight-column table; the right panel's interest lines print the account holder and the amount in ONE cell
   (`Francis Caldwell 22.52`, `Emma M. Dimond 13.52`, `Stephen Stickney 85.00`, ...), so these amounts are in labels, not in
   value columns, and the right panel's rows read under the left panel's group. Read by hand: Library balance December 31,
   1964 11,120.00 + interest and dividends 599.72... see the printed `Balance December 31, 1965 11,120.00` after the transfer to
   the Library Trustees 479.72. `spans:1-4,5-8` was the best available layout; it does not separate them. Cemetery by hand:
   50,305.47 + 1,050.00 + 1,154.95 + 988.76 = 53,499.18; less 2,063.69 transferred = 51,435.49, the printed balance (and the
   22/3 and 45/1 figure).
8. **Fee in the p19 pie legend (a cell versus the page).** Table 19/2 reads `C. 2.3% Health | 28,789.45`; the p27 Health
   subtotal in the cells is 48,789.45 and 2.3% of the 2.1 million paid is about 48,000 (the percent is unaffected). Left as
   Textract read it; the pie legend's side (We Received or We Spent) is not established by the cells (map note on 19/1-3).
9. **Welfare p67/1: the totals row has no label.** The last row's label cell reads `* Families` (the footnote text), and its
   three figures 122,461.02 / 102,466.20 / 19,994.82 are the table's column totals (the six program rows sum to them). The
   rows are `no check`; a total printed on a row with a footnote label is not recognised.
10. **Valuation chart p135 (NOT LANDED).** A bar chart `GROWTH IN TERMS OF POPULATION, VALUATION AND TAX RATE` (1930 ... 1965)
    came out as five rows of axis labels and data points in no readable order; it carries 1930-1945 values (tax rate $30.00,
    $28.50, $33.80, $32.00 ...; valuation $2,187,815 ...) that the p8 table (1950-1965) does not. A re-read of the page or the
    PDF's chart is needed.

## What this report prints that 2010 did not

A town in the middle of the 1960s: the Treasurer's whole cash statement (receipts, payments, accountant's schedule) for a
calendar year; a revenue analysis 1960-1965 (`ANALYSIS OF REVENUE ACCOUNTS`); the Welfare Department's table of five
assistance programs with persons aided and the State and federal reimbursements; the tax dollar pie legend; the valuation
and tax rate for 1950-1965 (tax rate $89.00 on $11,810,645); federal NDEA and Public Law 874 school accounts with their
year's roll-forwards; and a Stabilization Fund transfer of $4,000 (Article 11, 1965 Annual Meeting).

## Integration pass, 31 October 2026: what was done

Names and opt-ins are in `sources/data/report-tables/README.md` (1959-1970). Pages proven/unproven/refused:
6/35/0 as the worker left the folder -> 15/26/0. Renamed: `report-welfare-programs` -> `report-welfare-aid`; p50 family -> `revenue-accounts-analysis`; p19 legend split payments (19/1-2) and receipts (19/3).
Opt-ins set: `colon_heading_subtotals`, `cash_book_list`, `recon_no_transfers`, `dash_zero`, `accountant_marks_wide`, `accountant_marks_before`, `marks_wide`, `year_labels`, `statement_span`, `receipts_stop_at_grand`, `collector_columns`, `signed_figures`.
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
