# 1977 NEEDS (for the integration pass)

All figures below were computed by hand from `rows/` and the cells; nothing here changed a shared script.

## 1. Subtotal printed on the NEXT section's heading row (receipts p40, p44; payments p45-47) -- a reader rule
The statements print a section's subtotal on the line of the heading that FOLLOWS it (`Special Assessments: | | 658.00` is the subtotal of the farm animal excise above it, 102.50 + 555.50). The reader treats these as accounts.
- Receipts p40-44: six rows end in `:` and are such subtotals (`Special Assessments:` 658.00, `Interest:` 1,023.50, `Added Costs:` 8,638.56, `Commonwealth of Massachusetts: Loss of Taxes:` 145,046.40 on p40; `Current Year Refunds:` 4,854.32 and `Previous Year Refunds:` 6,294.30 on p44). Accounts sum 9,808,615.32; removing those six gives exactly the printed Total Receipts 9,642,100.24. Today all 172 receipts rows read `check failed`.
- Payments p45-47: fourteen rows with no label or a label ending in `:` carry the shifted subtotals (p45 t1 r21, r33, r52, r56; p46 r20, r24, r29, r35, r46, r52; p47 r15, r33, r39, r47). The remaining rows sum to exactly the printed Total Payments 9,664,867.94; with them, 15 rows read `check failed`.
- Change: an `edition.json` opt-in (suggest `subtotal_on_next_heading`) that treats a figure on a heading-only row (label ends `:`, or no label, with a figure in the total column) as the subtotal of the group above it.

## 2. Treasurer's cash roll-forward, p39 (and 52 t1)
39/1 holds the roll-forward and the account list in one table; the disbursed line shares a cell with the cash book balance (`9,664,867.94 16,694.95`). Landed in `report-treasurers-cash-reconciliation` (24 rows, `no check`: `the chain could not be followed`). `recon_net_beside_ledger` is set and did not help. By hand: 39,462.65 + 9,642,100.24 = 9,681,562.89; - 9,664,867.94 = 16,694.95 = the sum of the bank accounts and cash on hand (559.11 + 2,000 x 4 + 2,572.73 + 4,502.26 + 1,060.85 = 16,694.95 checked by hand). Wanted: a reading of `Cash in Banks:` as the `treasurers-cash` account list with `stated_total` 16694.95.

## 3. Accountant's schedule marks (report-appropriations accountant-schedule, 7 `check failed`)
- `19,982.83Cr` (p61, Snow Removal Expense): a deficit printed with `Cr`; unparsed, so the row reads a balance of 0. Wanted: `Cr` suffix = negative balance.
- `3,370.00 R` (p57 Purchase Police Cruiser) and `1,819.00 R` (p58 Purchase of Fire Hose): an `R` after an appropriated-forward figure; unparsed, so the row fails its identity. 
- `119.16 TR` (p57 Replace Furnace, Jones House): the balance is in the PDF lines (0.6960, 0.4299) but in no table cell. A re-read, not a rule.
- p62 `Land, or Interest in Land...` and p65 `Celebration of our Nation`: `fwd mark` repaired cells; still fail.
- p59 `Hiring Conservation Assistant (Maps)`: balance to revenue blank; not examined further.

## 4. Debt, p54 (report-debt, 7 `check failed`)
The totals tie by hand (65,000 + 25,935 = 90,935 and so on for every column; the schedule's GRAND TOTAL rows tie to 778,500 / 150,075 / 928,575). The failures are the validator's block walk: `TOTAL MIDDLE SCHOOL` follows a first row whose cells hold TWO bonds each (`1,340,000 40,000`), so rows sum 0; and the `Total:` rows in the schedule are walked against the GRAND TOTAL rows.

## 5. FINDER MISSES
- p37 (Cash Flow and Investment Income Estimate, week of February 1978): this IS a money table and it was sent, but Textract returned it as 44 columns with figures split across cells (`1 | 661 | 00` for 1,661.00) on a rotated page. Mapped NOT LANDED. Needs a re-read of the PDF page by another instrument.
- p38 (Treasurer's office cost table, calendar 1970-73 and fiscal 1975-79): readable but NOT LANDED on purpose. Read as a table, the two interest columns drift across blank cells, a bar-chart axis ($80,000 ... $10,000) leaks into v4/v5, and the star that marks FY1978-79 as ESTIMATED is stripped as a footnote mark (repaired_cells), so an estimate would read as an actual (rule 1). The printed rows: Cal. 1970 36,816 / 13,633 / -0- / 50,449; Cal. 1971 37,251 / 12,356 / (1,710) / 47,897; Cal. 1972 44,232 / 14,974 / (1,883) / 57,323; Cal. 1973 61,477 / 18,804 / (10,408) / 69,873; FY 1975 78,271 / -0- / (68,860) / 9,411; FY 1976 91,127 / -0- / (70,630) / 20,497; FY 1977 100,175 / -0- / (65,515) / 34,660; FY 1978 104,350 / -0- / (65,000)* / 39,350*; FY 1979 129,355* / -0- / (75,000)* / 54,355*; `*Estimated`. A proposed dataset `report-treasurers-office-cost` needs the star kept as a stage.
- FINDER MISSES in the sense of money tables on pages with NO cells: none found. Pages 14, 16, 28, 29, 30 were sent (3+ money figures in the text) and Textract found no table on them; p29 prose gives the snow removal cost ($75,614.83, equal to the accountant's schedule on p61) and p30 the new police facility.

## 6. ROSTER PAGES (staff rosters, named, no money)
p120 (resignations), p121 (aides/tutors), p122 (leaves of absence), p123-124 (retirements), p125-143 (School Personnel Listing 1977-78: administration, clerical, teachers, aides, health services, cafeteria substitutes; p142 is the only one with a table, 142/1, mapped NOT LANDED), p153-154 (school lunch staff). None carries FTE or a funding source.

## 7. New datasets (generic `report-*` columns; register in the integration pass)
- `report-school-lunch` (families `lunch-receipts`, `lunch-expenditures`, `lunch-meal-counts`): the School Department's lunch program by month, p155-156. Receipts and expenditures are actuals; meal counts are counts and never summed with money. Totals are printed inside the total row's LABEL (`TOTAL INCOME: ($184,729.65)`, `TOTAL EXPENDITURES: ($172,629.17)`). 49 rows, `no check`; by hand the four expenditure columns sum to 172,629.17 (96,503.54 + 62,938.81 + 4,110.46 + 9,076.36). The income columns (97,008.41 + 5,515.08 + 579.39 + 81,626.77 = 184,729.65) tie by hand too.
- `report-school-staff-changes` (families `staff-reductions`, `staff-additions`): the School Committee's proposed cuts and additions in the FY-78 request with their dollar effect, p95. A proposal. 36,757 - 15,424 = 21,333 printed.
- Register note: `report-school-lunch` and `report-school-staff-changes` need registration wherever the shared datasets are registered (the generic `report-*` columns).

## 8. Hand-checks that the reader does not make
- Omnibus budget (p75-76): the budget lines sum to exactly the printed TOTAL BUDGET VOTED $4,823,506.00 (rows `no check` because the map says `checks=none`, as 1981).
- Special articles voted (p76/3, 77/1, 77/2, 77/4): revenue sharing 115,590.00 + transfers from other available funds 14,115.01 + borrowing 30,000.00 + raised by taxation 86,654.53 = 246,359.54 (printed); + 4,823,506 = 5,069,865.54 (printed GRAND TOTAL). 77/3 (footnote **) sums to the printed 14,115.01.
- Revenue sharing (p52-53): 5,605.72 + 237,657.23 - 239,985.30 = 3,277.65; balance sheet sides both 186,570.88.
- Trust funds (p83-85): summary 146,163.99 = p51 total; per-fund balances June 30, 1977 agree between p51, p83 and the roll-forwards (71,719.98; 8,648.48; 15,936.79 is on p83 only, no roll-forward printed for the library fund; 6,665.62; 23,065.88; 19,024.65; 1,102.59).
- General account balance sheet liabilities total $6,097,314.27 (p50 t1 last row); the page prints no total for the assets side, and the deficits line (Snow Removal 19,982.83) is the last asset line.

## 9. Not landed, with reason (in map.csv)
p3 (town facts, office hours, meeting dates), p37, p38, p82 (empty table), p89 (school calendar), p142 (roster). p3 prints the assessed valuation ($66,890,790.00 real, $3,203,280.00 personal) and tax rate ($48.00): no dataset holds a one-line valuation; see the valuation gap in gaps.csv.

## 10. Inventory notes
tax-collection (p67) lands through the legacy emitter exactly as 1981 p121 does: most `item` cells are blank and `proof` is empty (26 rows). The levy labels are in the cells; the legacy schema does not carry them.

## Integration pass, 31 October 2026: what was done with each item

Opt-ins and names are in `sources/data/report-tables/README.md` (1971-1980). By item number above:
1 APPLIED (`colon_heading_subtotals`: 6 receipts rows; receipts close to 9,642,100.24; payments via `statement_span`). 2 APPLIED for the chain (`checked`); the account list is not remapped. 3 APPLIED (`Cr` negative, `R` marks); `accountant_marks_before` NOT set (it cost a page). 4 NOT APPLIED (block walk). 5 p37/p38 re-read list. 6 APPLIED: `rosters.csv` written by the integration pass (it was missing) and p125-143 read. 7 APPLIED (names registered).
