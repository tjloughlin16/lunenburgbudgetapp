# 1966 edition: what the shared code needs (for the integration pass)

Edition: calendar 1966 annual town report, `4509-1966-annual-town-report.pdf`, 126 pages. Tables were read on the 51
pages `find_financial_pages.py --list 1966` picked; 86 tables (map.csv), 36 landed pages (pages.csv; 5 `proven`).
Opt-ins in edition.json: the 1981 set plus `unlabeled_subtotals` and `rounding_tolerance_usd: 1`. Hand checks below are
computed from `build/textract/out/4509-1966-annual-town-report.cells.tsv`. `--check` reproduces. The reader limits that
1971 already named are cited, not re-described ("1971 item N"); 1966 prints the same layouts.

## FINDER MISSES

1. **p36, the School Committee's prize funds (Mabel L. Allen, Joseph A. Harwood).** Sent by the finder; Textract returned
   cells only for the Stabilization Fund section at the foot of the page (36/1). The top two thirds, `REPORT OF TRUST FUNDS
   IN CUSTODY OF SCHOOL COMMITTEE`, are in lines only: summary (567.09, 523.59, 1,090.68), investment of funds (Fitchburg
   Gas and Electric stock 498.00 and 480.48; Fidelity Cooperative Bank books 69.09 and 43.11), and the two balances and
   income panels (balance 12/31/65 565.19 and 522.75; dividends 30.00 each; interest 1.90 and .84; 12/31/66 balances
   567.09 and 523.59; two grants of 30.00 to named pupils). Money page with no cells: a re-read of the page is needed.
   The two 12/31/66 balances ARE landed, from the balance sheet (p20/3) and not from this page.
2. **p111, the `Net Total Expenditure for Day School Support` row.** Its three figures ($538,872. elementary, $301,754.
   high school, $840,626. total) sit on the lines of a 10-line label and are in no cell (page lines 44-46); the row
   lands with the two cells that were read, shifted (301754, 840626, no elementary figure).
3. **p17, the pie chart of the Treasurer's receipts and payments.** Only three legend fragments reached a cell (landed
   as `receipts-payments-pie-legend`); the large slices (support of schools 47.3% $1,079,455.60; taxes real and
   personal $1,034,157.71; excise $170,896.45; charities and veterans $135,630.70; the agency and trust slice
   $272,639.46) are in the graphic and in page lines only (lines 8, 14, 17, 20, 24). Nothing else on the page.
4. Pages sent and read as prose only (no table cells; money in sentences or warrant text, nothing missed by eye): p7, p54,
   p57, p62, p67-69 (warrant articles), p87, p89, p95. p63-65 table cells are the voted budget; the articles' text
   with the amounts voted is p66-70 prose.

## ROSTER PAGES

p100-107 School personnel for 1966-67 (name, education, subject or grade, years, year appointed; no pay printed). p108
(school bus contractors, with route numbers) and p109-110 (enrollment by grade and teacher) are name or count lists with
no money and were not sent. Written to `rosters.csv`. Births p71, marriages p73 and the jury list p76 were not sent
either (no money); "Everything in the annual reports is public" (TJ, 30 Oct), a later pass reads them from text.
No `withheld_rows` is used anywhere in this folder.

## SHARED-CODE CHANGES THE EDITION NEEDS

1. **Accountant's schedule (p29-32): the GRAND TOTALS row (p32) totals all four pages, the validator sums one page.**
   p32 rows would read `check failed` (33 rows, "rows sum 673,850.00" against 2,117,474.81), a limit of the instrument and
   not of the figures. map.csv sets `checks=none` on p32/1 for that reason. By hand over p29-32 (cells 2-6, leading
   marks `a`, `b`, `C`, `di` and trailing marks stripped): Appropriated 2,117,474.81, Balance Forward and Transferred In
   371,982.46, Total Funds Available 2,489,457.27, Total Expended 2,315,998.88, Balance to 1967 173,458.39. **All five tie
   to the printed GRAND TOTALS to the cent.** Change: pool an accountant schedule's pages against a GRAND TOTALS that
   prints on the last (as `receipts_span` does for receipts). The row identity does not apply either: the carry-forward
   is headed `Balance to -1967` (the 1971 item 2 widening `(?:FY|FISCAL|19\d\d)` would not match the hyphen: `-?19\d\d`).
   Leading marks (`C 1,500.00`, `C 344.95`, `a 15,778.00`: 4 cells on p29, `a` and `C` between figures on p29-32)
   are before the figure, as in 1971 item 2. p29 r53-58 and p29 r24-30 are multi-line accounts (two or three lines
   for one account, the second carrying the transfers): they read as rows of their own.
2. **Receipts (p21-24): section subtotals printed one row low, as 1971 item 3 and 1975 item 2.** `accounts sum
   3,184,216.92 vs the printed GRAND TOTAL 2,934,351.10` and all 154 rows are `check failed`. By hand the third-column
   figures of p21-24 (every section subtotal and every direct line, `Total Receipts` excluded) sum to **2,934,351.10 to
   the cent**; the five labels that sit on a subtotal's row (`Motor Vehicle and Trailer Excise:`, `Street Betterments:`,
   `Interest:`, `Treasurer:`, ... ) read as accounts. Also a heading and its figure in one cell (`Aid to Families with
   Dependent Children,  $` r2 of p31 is the schedule; p23 r24 `Licenses and Permits: | | 11,695.81` is the TRUST funds
   subtotal under the next heading).
3. **Payments (p25-28): ties by hand, `checks=none` in the map as 1971.** Third-column figures of p25-28 (`Total
   Payments` excluded) sum to **2,840,633.91** = printed `Total Payments`.
4. **Treasurer's cash (p21/1): `report-treasurers-cash` and the reconciliation emit nothing**, the same refusal as 1971
   item 1: `accounts sum 8,882,466.00, printed 120,188.09`. Chain by hand: 26,470.90 + 2,934,351.10 = 2,960,822.00;
   2,960,822.00 - 2,840,633.91 = 120,188.09; the cash-in-banks lines (106,321.45 + 200.00 + 10,000.00 + cash on hand
   3,666.64) sum to 120,188.09. Both printed. Needs the 1971 fix.
5. **Balance sheet (p18-19): ties by hand.** p18/1's section subtotals (219,328.65, 38,368.79, 8,874.16, 9,983.11,
   4,773.02, 63,002.21, 1,201.88) sum to the 345,531.82 that closes the liabilities side on p19/1. The p18/2 sections
   (2,312.95 + 55.81 + 39,127.42 + 1,583.50 + 900.00 + ...) and p19/1 detail are one liabilities list across two pages.
6. **Debt (p33/1): `check failed` on a one-row group.** `Grand Totals` (1,682,000 paid principal) = 810,000 (Elementary)
   + 740,000 (Junior-Senior) + 132,000 (the 1961 issue, one row followed by its own subtotal row of 132,000). The reader
   counts that subtotal as a second account (rows sum 1,814,000). Interest 327,534.00 = 128,538.00 + 192,600.00 + 6,396.00,
   total payments 143,000 = 50,000 + 75,000 + 18,000. All tie by hand. Change: an unlabelled row equal to the single
   detail line above it, in a group, is its subtotal.
7. **Debt schedule (p33/2) has 13 columns, `MAX_V` is 8.** Every year row spills into a second `no check` row (1967:
   20000 ... 105000 | 7795 112795 215000), and `-----` for `NONE`/nil is read as a label in place of a value. By hand
   each year row closes: 20,000 + 10,000 + 65,000 + 10,000 = 105,000 principal, 575 + 7,220 = 7,795 interest,
   105,000 + 7,795 = 112,795; the printed Totals row (320,000 | 18,040 | 338,040) ties. Library bond (p33/3): the 1964
   principal cell is `$` alone, so the 1964 row lands shifted left by one (490.00 where interest is); the balance column
   is correct by `columns_as_printed`.
8. **Revenue analysis (p38/1): `-0-` and `(47,947.90)CR` do not parse.** `$ -0-` is a zero and `(...)CR` is a credit
   (negative); both cells are dropped, so rows 1, 2, 4, 6, 8, 10 land with fewer values and their ordinal `v` shifts
   (row 3 `Taxes and Recap.` lands 77.49, 376.47, 301.84 for 1964, 1965, 1966). `columns_as_printed` shows the shift. Row
   `Revenue transfer` and `Current Year Revenue`/`Tax Titles` equal across the table by the page's own arithmetic; no
   identity is applied. `FREE CASH`-line 16 is the figure TJ's free-cash work reads (40,675.21 in 1966).
9. **Welfare (p55/1): `11*` (families) is not a figure,** so General Relief lands with 1,463.25 in `v1` (persons aided
   missing) while every other row has the count first. Last row: label `* Families`, the totals 125,548.84 | 105,321.09 |
   20,227.75 (the table's total row). Net cost = expended - reimbursements by the page's own arithmetic on all rows.
10. **School budget summary (p112/1): `- 17,000.` and `- 35,081.` (federal funds committed) are not read,** and
    `NET BUDGET REQUEST TO TOWN: $` lands 941,114 | 1,019,676 with the 1966 column's `$` figure first. Repeated labels
    `Salaries` / `Expenses` lose their series banner (1000 Series - Administration ...); the banner is in `group`. By
    hand the columns close: 958,114 - 17,000 = 941,114 (1966 appropriation net of federal funds), 1,054,757 - 35,081 =
    1,019,676 (1967 request). The $936,994.89 spent + $4,119.11 returned = 941,114.00 is printed.
11. **p114/2: `+ 35,081.00` and `$ 214,351.22` (the grand total receipts) lose their values.** Grand total 214,351.22: the nine receipts 117,795.75 + 53,087.00 + 937.06 + 5,378.81 + 1,381.00 + 135.00 + 255.00 + 50.60 + 250.00 =
    sum to 179,270.22, and + 35,081.00 (the P.L. 874 and 864 funds allotted toward 1967) = 214,351.22 by hand, as printed. p111/2 prints `RECEIPTS ACCREDITED TO SCHOOLS $197,629.73`, a
    different total (excludes vocational and evening classes per its definition): not summed with it.
12. **School special accounts (p113, p115-118): small tables with a `.$ $ 83.00`, `$ 1750.` and `+ 17,300.00`** style cell
    drop their figure: p115/6 balance on hand 12/31/66 (83.00), p116/3 salaries 1,750., expenses 100., tuition 360.
    (2,210.00 total read), p116/6 `+ 17,300.00` estimated receipts 1967 and p117/2, p117/4 anticipated 1967 receipts
    1,980.00 and 3,842.85, p118/1 receipts. Estimates and anticipated receipts are FORECASTS (rule 1): never differenced
    with the actual columns. A balance-on-hand roll-forward closes by hand on every fund: 51.00 + 332.00 - 300.00 =
    83.00; 4,637.48 + 17,695.00 - 13,750.00 = 8,582.48; 4,423.46 + 664.51 - 3,545.78 = 1,542.19; 1,876.61 - 1,876.61 = 0;
    0 + 14,750.00 - 6,804.50 = 7,945.50 (Title I, the amount is not printed); 0 + 7,556.00 - 6,533.26 = 1,022.74;
    0 + 13,417.50 - 8,428.05 = 4,989.45; 0 + 1,017.00 - 1,017.00 = 0. The unnamed families `athletic-account`,
    `vocational-account`, `adult-education-self-supporting` and `adult-education-and-federal-funds` are new in
    `report-school-special-accounts` (the datasets' own statements per fund, not the accounts-by-year table of p113).
13. **Trust funds (p35/1): two funds per panel, one above the other.** `spans:1-4,5-8` reads each panel top to bottom,
    so Sidewalks and Grounds then Cemetery Perpetual Care fall in panel 1 and Worthy Poor then Library in panel 2. The
    `group` text lags (a bequest donor lands under `December 31, 1965`). Every figure is read; the funds close by
    hand: Cemetery 51,435.49 + 1,150.00 + 1,248.09 + 1,019.70 = 54,853.28, less 2,143.71 transferred = 52,709.57;
    Worthy Poor 7,522.92 + 310.55 = 7,833.47, less 260.00 grant = 7,573.47; Library 11,120.00 + 196.71 + 317.51 =
    11,634.22, less 514.22 = 11,120.00; Sidewalks 5,624.77 + 226.15 = 5,850.92. Stabilization (p36/1) 104,778.88 +
    4,760.65 = 109,539.53, matching `Treasurer's` in the summary. All also tie to the balance sheet (p20/3).
14. **Tax collection (p28/2): item labels and the balance column are lost, as 1971 item 4.** `NONE` in the balance column is
    nil. Totals row: commitments 1,345,548.71, collected 1,211,947.81, abated 92,161.72, refunds 10,832.16, tax titles
    5,028.39, balance 47,242.95. Printed below: interest paid into the Treasury 2,187.44, fees received by the Tax
    Collector 1,459.00.
15. **Voted budget and special articles: `special-articles-voted` and `omnibus-funding-sources` stay `no check`, as 1971 item
    5.** By hand: 55,000.00 (surplus revenue) + 26,236.11 (other available funds, p64/4 and p65/2) + 66,536.81 (raise by
    taxation, p65/1 and p65/2) = 147,772.92, the printed `TOTAL SPECIAL ARTICLES VOTED`; the Overlay and article
    balance transfers sum to the printed 6,704.83. The voted budget (`omnibus-budget`, 63/6-64/2) closes to `TOTAL BUDGET
    VOTED` 1,539,858.00 (82 rows `checked`).
16. **Classification plan (p60/1) lands as `report-classification-plan` family `salary-schedule-proposed`.** It is the
    schedule to be voted March 4, 1967 (a PROPOSAL). Positions with a second title on the next line (Senior Clerk/Typist,
    Principal Clerk, Library Technician) land as two rows (the 6th and 7th step in the second); cells such as `1300yr`,
    `35wk` and `1:75` (a mis-read `1.75`) do not parse as pure figures. Check the family name against the other
    editions' (1975 and 1981 print adopted schedules).

## NAMES FOR THE INTEGRATION PASS

- `report-welfare-aid` (family `welfare-aid-by-category`): as 1964 p54, which prints the same table. 1959 p49 calls
  its table `report-welfare-cost`. Same quantity (a Welfare Department table of aided persons, expended, reimbursed,
  net cost): one name should be chosen.
- `report-monty-tech` (family `vocational-district-budget`): the Regional Vocational School District Committee's
  approved budget ($28,440.00, p122). The shared dataset exists; this is a VOTED budget, never an actual. The year is
  not printed in the table.
- `report-fund-balance-sheets`, family `revenue-analysis` (new): the Accountant's six-year analysis of revenue accounts
  (p38). 
- `report-expenditure-shares`, family `receipts-payments-pie-legend` (new): see FINDER MISSES 3.
- `report-school-special-accounts` families `athletic-account`, `vocational-account`, `adult-education-self-supporting`,
  `adult-education-and-federal-funds`.
- `report-trust-funds`, `trust-funds-custody` and the rest are reused as named in README.md.

## WHAT THIS REPORT PRINTS THAT 2010 DID NOT

The Treasurer's receipts and payments as a pie chart with percentages (p16-17); the Welfare Department's table of persons
aided with reimbursements (p55); the six-year analysis of revenue accounts and free cash (p38); a proposed Classification
and Salary Schedule with the weekly and hourly rates of 1967 (p60); the School Department's federal programs each as a
small statement (P.L. 874, NDEA Titles III and V, ESEA Titles I and III, Operation Headstart); an Adult Education
account; and the Regional Vocational District's first budget of $28,440 (p122).
