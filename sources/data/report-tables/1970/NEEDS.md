# 1970 edition: what the shared code needs (for the integration pass)

Edition: calendar 1970 annual town report, `4492-1970-annual-town-report.pdf`, 136 pages. Tables were read on the 54 pages
`find_financial_pages.py --list 1970` picked; 67 tables (map.csv), 38 landed pages (pages.csv). Opt-ins in edition.json: those
of 1971 (`accountant_marks`, `stop_for_comma_without_dollar`, `id_column_words`, `recon_net_on_transfer_line`, `stacked_pairs`,
`receipts_span`) plus `unlabeled_subtotals` and `rounding_tolerance_usd: 1`. The layout is the 1971 layout page for page
minus 12 (p28 = 1971 p40, p30 = p42, p31-34 = p43-46, p35-38 = p47-50, p39-50 = p51-62, p51 = p63, p52-54 = p64-66,
p69-70 = p69-70, p124-132 = p127-133). Hand checks below are computed from
`build/textract/out/4492-1970-annual-town-report.cells.tsv`. `--check` reproduces.

## FINDER MISSES

1. **p98, THE SCHOOL DOLLAR (School Committee report).** A money table: eight categories with Lunenburg and national-median
   percents and the dollars spent in 1970 (Capital Outlay $16,901.17 1.0% / 2.2%; Maintenance $32,374.23; Utilities, Fuel
   $46,382.11; Administration $56,365.22; Books & Supplies $87,928.91; Custodial Salaries $92,213.48; Transportation
   $121,802.50; Instruction $1,229,644.52), against `$1,683,612.1 for schools was spent in 1970`. The finder did NOT send
   it (the dollar figures sit in the text as a chart legend), so there are no cells. It is the same quantity as 1971
   `report-school-spending-shares` (p98 of 1971). A re-read of the page is needed to land it.
2. Pages sent with no table cells at all and read as prose: p9, p12, p71-74 (warrant articles), p123 (school lunch prose),
   p133 (Montachusett Regional Vocational School prose with the $5,037,000 contract). Nothing missed by eye there.
3. **p70: the borrowing line of the special articles is in no table.** `By Borrowing / Article 6. Town Garage 100,000.00 /
   $100,000.00` is printed between the 70/4 and 70/6 columns and Textract returned it as text only.
   `Total Special Articles Voted: $307,190.00` = 24,079.00 (70/2) + 38,869.62 (70/4) + 144,241.38 (70/6) + 100,000.00 =
   307,190.00 exactly (computed). The three landed tables foot to 207,190.00, so `special-articles-voted` is left with no
   stated_total and its rows are `no check`.

## ROSTER PAGES

p55 roster of firemen; p104 resignations during 1970 (professional and custodial staff); p105-116 School Personnel Listing
1970-71 (administration, clerical, teaching staff with education, degree, years of experience and year appointed;
custodians and cafeteria staff; no pay printed). Written to `rosters.csv`. Not sent for tables, so out of scope: officials
(p5-6), deaths, births, marriages, school enrollment by grade (p101-102), graduates and scholarship recipients
(p118-121), school bus contractors (p117), retirements (p103). "Everything in the annual reports is public" (TJ, 30 Oct): a
later pass reads the named lists from the text if wanted. No `withheld_rows` is used.

## SHARED-CODE CHANGES THE EDITION NEEDS (none made here). Same items as 1971; computed again on 1970

1. **Treasurer's cash, p30/2: same as 1971 NEEDS item 1.** `CASH_INVESTED` does not match `Cash in Banks:`, so the
   roll-forward lines are summed as accounts: `accounts sum 9,872,595.80, printed 127,998.78: not published (refused)` and
   `treasurers-cash.csv` and the reconciliation get 0 rows. By hand from the cells: the seven accounts (36,923.58 + 23,594.09
   + 35,265.48 + 2,000.00 + 10,000.00 + 15,500.00 + 4,715.63 `Cash on Hand`) sum to 127,998.78, the unlabelled figure
   printed as the last row. Roll-forward by hand: 448,187.60 + 4,488,110.30 = 4,936,297.90; less disbursements 4,808,299.12 =
   127,998.78, all printed. Differences from 1971: the page prints `Cash on Hand: 4,715.63` among the accounts, and the
   `Disbursements ... | 4,808,299.12 | 4,936,297.90` line carries the roll-forward subtotal in the next column (the 1971 page
   fused the labels in one cell).
2. **Accountant's schedule (p39-50, `accountant-schedule`): resolved by the shared pattern since the first run, one residue.**
   The first run of this folder left all 557 rows `no check` because the carry-forward column is `Balance to 1971`; with the
   shared `BALANCE (?:TO )?REVENUE` identity as it stands now, **169 rows are `checked`** and 320 are `no check` (`no total
   printed`: detail sub-lines under a department with no Total Funds Available of their own, and the department-header rows).
   By hand from the cells, 177 of 178 rows that print a Total Funds Available figure close (Total Funds Available = Total
   Expended + Balance to Revenue + Balance to 1971, blank read as zero); the 8 not reached by the reader include p49 row 46
   (Park Department 21,610.00), which prints `21,297.40 312.60` in ONE cell (total expended and balance to revenue fused;
   21,297.40 + 312.60 = 21,610.00), and rows carrying a leading mark. None fail.

3. **Payments (p35-38) are one statement over four pages and are not pooled.** Landed with `checks=none` as 1971 p47-50 (no
   `payments_span` exists for them; `receipts_span` does). By hand the section subtotals foot to Total Payments
   $4,808,299.12 to the cent: General Government 128,280.87 + Protection 133,336.91 + Health 74,083.11 + Highways
   389,587.86 + Charities and Soldiers' Benefits 35,773.15 + Schools 1,954,807.09 + Library 31,596.62 + Cemeteries
   9,008.57 + Recreation 27,845.29 + Unclassified 31,288.80 + Debt and Interest 1,112,656.45 + Agency and Trust 550,949.39 +
   Petty Cash Advances 760.00 + Refunds 20,241.01 + Trust Fund Deposits 5,317.57 + Assessments 102,766.43 + Investments
   200,000.00 = 4,808,299.12. It equals the disbursements line of the p30 reconciliation.
4. **`tax-collection` (p30/1): labels lost, as 1971 NEEDS item 4.** `item` is empty on every row and `balance` is blank
   where the page prints it (7,155.23, 23,366.96, 159,695.31 ...): the levy years in the first column read as figures and the
   header is `Balance`, not `BALANCES`. Page foot totals as printed: commitments $2,054,920.32, refunds $20,240.51, payments
   $1,828,796.62, abatements $86,548.71, tax titles $(120.19), balance $159,695.31, grand total received $1,832,598.32
   (payments + interest 2,564.70 + fees 1,237.00 = 1,828,796.62 + 3,801.70 = 1,832,598.32, computed).
5. **Special articles and funding (p70/2, 70/4, 70/5, 70/6): `special-articles-voted` and `omnibus-funding-sources` are
   not in `LIST_FAMILIES`**, as 1971 item 5. By hand: 70/2 = 24,079.00, 70/4 = 38,869.62, 70/6 = 144,241.38 match their
   printed subtotals. 70/5 sums to 43,759.00 against the printed $44,079.00: the row `Tree Warden Machinery | Acct. 320.00` has
   its label and figure in one cell and the figure 320.00 is not read (43,759.00 + 320.00 = 44,079.00).
6. **Unit-suffixed rates are not read (p21 salary schedule).** `1.50hr`, `1900yr`, `40wk`, `110wk` (48 cells in 20 rows,
   e.g. Substitute Nurse 3.40hr, Fire Chief 1900yr, Recreation Director 900yr, Life Guard 1.75hr/1.85hr/1.95hr) are not
   figures, so those 20 rows land with blank values (Life Guard) or not at all (29 of about 50 positions landed). Same
   limitation as 1972 and 1973 salary schedules if they carry units. Wanted: keep the cell text (`1.75hr`) and unit.
7. **Balance sheet p28/1 mixes assets and liabilities in one table** (rows 1-38 assets, rows 39-54 liabilities and the
   first appropriation balances), where 1971 split them. Landed as `general-fund-assets` with the layout noted; both sides
   foot to $592,461.57 by hand: assets 508,923.93 (cash, receivables, tax titles, departmental) + aid to highways 77,470.88 +
   unprovided-for 4,475.27 + overlay deficits/overdrawn 388.91 + snow removal 1,202.58; liabilities 53,044.81 + appropriation
   balances 135,082.26 (the p28 right panel rows 50-54 5,768.82 + p29 126,994.05 + 2,319.39, computed) + sale of burial
   rights 5,760.00 + reserves and surplus revenue 398,574.50. Trust and investment accounts: 86,351.85 + 1,109.56 +
   13,148.84 = 100,610.25, printed.
8. **School lunch p124/3 is one table where 1971 had two** (receipts and bills share cells with their labels). Landed as
   family `lunch-totals`; the cell text `Total Food Bills - $67,721.09 | USDA Reimbursement - | $31,670.12` is read as
   label and one figure, so only some of the six totals reach a value column. The totals are on p124/2's last row as well
   and tie there (food 67,721.09; other 7,902.68 with 470.00 equipment; labor 35,244.66; USDA 31,670.12; sales 87,045.83
   with the September 1 balance 6,318.33).
9. **Debt p51/1: the first table also holds the appropriated funds** (`Stabilization Fund 100,000 / Accelerated Taxation
   100,000 / State Matching Grant 1,500 = $1,581,500 Total Appropriated`), whose labels sit in a cell with the figures.
   Landed `checks=none`; the issue rows foot by hand (985,000 paid off; 1,340,000 + 40,000 = 1,380,000; balance 1,130,000 +
   30,000 = 1,160,000 = the Middle School schedule total on p51/2).

## NEW dataset names

None. Every table maps to a dataset or family 1971-1981 already named: `report-proposed-salary-schedule`
(family `proposed-classification-salary-schedule`, p21), `report-school-lunch` (adds family `lunch-totals`, p124/3),
`report-school-staff-fte` `school-cost-per-pupil-calendar-year` (p126/2, which here also carries three census
populations), `report-elections` (p75).
