# 1983 edition: what the shared code needs (for the integration pass)

Edition: calendar 1983 annual town report, `4483-1983-annual-town-report.pdf`, 132 pages. Tables were read on
the 59 pages `find_financial_pages.py --list 1983` picked; 44 of those landed rows or were mapped (map.csv covers
all 83 tables in cells.tsv). Every hand check below was computed from the cells
(`build/textract/out/4483-1983-annual-town-report.cells.tsv`) and lines, not typed from the page.

## FINDER MISSES: 0

Every page NOT in the picked list was scanned for money-shaped figures in lines.tsv; none has more than 4
(p15 and p121 have 4 each, both prose: a library trustees caption and the school custodial staff listing).
(Method bounds the misses, it does not prove zero.)

## ROSTER PAGES

Not sent for tables, no money on the page, written to `rosters.csv`: p18 `Roster of Firefighters for 1983`;
p116 `RESIGNATIONS DURING 1983` (School Department); p117-p122 `School Personnel Listing 1983-84`
(superintendent, guidance, teaching staff by school, aides, custodial staff, cafeteria substitutes).
Also NOT staff rosters and not landed: p35-p36 `Jury List` (private residents, name/address/occupation; never
to be landed). p124 prints staff as FTE by role (landed as `report-school-staff-fte`), which is not a roster.

## NEW DATASETS / FAMILIES this edition introduces (names for README.md)

- `report-office-budget-cuts` (NEW, p37): the Town Clerk / Tax Collector / Treasurer table `FY 83 | FY 84 | DECREASE`,
  a budget comparison of three administration lines. One office per row.
- `report-expenditure-shares` (NEW, p40/2): the FY 1983 expenditure pie as percentages, no dollars; only nine of fourteen
  slices reached a table cell, the other five (SCHOOLS 59.4%, HIGHWAYS 8.7%, PROTECTION 7.8%, STATE & COUNTY ASSESS.
  5%, GEN'L GOVT. 4.7%) are in the page lines only, and no row is written from them.
- family `debt-history-selected-years` in `report-debt` (p38): outstanding debt and payment at 1950, 1955 ... 1985.
- family `general-fund-long-term-debt` in `report-fund-balance-sheets` (p51/3): the debt account group.
- family `school-general-appropriation` in `report-school-special-accounts` (p126): the school general appropriation by
  series, FY-83 appropriation and spent, FY-84 request.
- Everything else reuses the settled names (README): `report-auditors-cash-schedule` (families `cash-composition`,
  `investments-composition`), `report-statement-of-payments`, `report-fund-balance-sheets`, `report-revenue-sharing`,
  `report-treasurers-cash-calendar-year`, `report-treasurers-cash-reconciliation`, `report-trust-funds`.

## SHARED-CODE CHANGES NEEDED (each: what, why, which pages, hand check)

1. **Cash reconciliation, p40/1: net disbursed printed beside the ledger balance.** The page prints
   `General Ledger Balance | 9,217,865.88 1,154,794.21` as ONE line (net disbursed, then the ledger balance), and the
   unlabelled 10,372,660.09 under it is the `after receipts` TOTAL (= disbursed + ledger balance), not the net
   disbursed. `emit_cash_reconciliation` takes figs[0] of the ledger line as the ledger balance and the unlabelled line
   as `net_disbursed`, so 23 rows read `check failed (net disbursed 10,372,660.09 != 9,217,865.88)`. Needed: an opt-in
   (e.g. `recon_net_beside_ledger`) that reads a two-figure `General Ledger Balance` line as (net disbursed, ledger)
   and the line under it as the total to tie to `opening + net receipts`. HAND CHECK, all four steps tie to the cent:
   17,945,256.93 - 8,876,924.14 = 9,068,332.79; 1,304,327.30 + 9,068,332.79 = 10,372,660.09;
   17,927,069.17 - 8,709,203.29 = 9,217,865.88; 10,372,660.09 - 9,217,865.88 = 1,154,794.21. The 11 bank lines under it
   sum to 1,154,794.21 as well. The p54 revenue-sharing reconciliation (printed on separate lines) does check.
2. **Detailed statement of receipts, p41-p45/1** (`stated_total` 17,945,256.93 = `Receipts` on p40): 174 rows read
   `check failed` because of four reader limits, and with all four mended the accounts tie to the cent:
   (a) `RECEIPTS_GRAND = ...|^TOTAL RECEIPTS$` does not match the printed `TOTAL RECEIPTS:` (trailing colon), so the
   total row is summed as an account (accounts 18,069,214.48 + total 17,945,256.93 = the 36,014,471.41 the note shows);
   (b) p41 r32 `Commonwealth of Massachusetts: | | 135,184.00` is the unlabelled SUBTOTAL of the federal aid-to-schools group
   (12,123+2,700+65,785+15,074+19,000+9,602+10,900 = 135,184) sharing a line with the next heading, so it is read as an account;
   (c) p42 r53-r54 are two license items with NO label cell (`45.00`, `11,131.45`), dropped as subtotals; licenses
   19,847.80 + 681.75 + 50.00 + 630.00 + 870.00 + 45.00 + 11,131.45 = 33,256.00, the printed subtotal;
   (d) p43 r20 `Residency Certificates | 50:00` (a colon for the full stop) is unparsed; a `CALENDAR_REPAIRS` entry
   for `d:dd` in a cents column. Arithmetic: 18,069,214.48 (accounts as read, without the total row) - 135,184.00
   + 11,176.45 + 50.00 = 17,945,256.93.
3. **Detailed statement of payments, p45/2-p48 (20 rows `check failed`, off 316,046.16 against TOTAL PAYMENTS 17,927,069.17).**
   Four reader limits; hand tie below. (a) The General Government subtotal 316,046.16 is printed in the page lines
   (p45 line 89) and in NO cell; (b) p45 r15 `Montachusett Regional Planning District | Assessment 1,664.19`: the amount is
   inside the label cell, so the 21 cells sum 314,381.97 and the subtotal is 1,664.19 higher; (c) p46 r62 reads
   `Driver Education Program 10,333.0°` (the final `9` as a degree sign), 10,333.09 by the schools subtotal 4,235,684.26
   = 3,814,950.38 (p46) + 410,400.79 (p47 r1-r20) + 10,333.09; a glyph witness should decide; (d) a section of ONE
   line prints its amount in the subtotal column (p47 r32 Conservation 399.22, r34 Park 34,670.67; p48 r24 Petty Cash
   Advances 2,820.00), so it reads as a subtotal. HAND TIE: the printed subtotals and one-line sections (GG 316,046.16; protection
   526,484.64; health 106,700.19; highways 599,273.18; veterans 26,340.42; schools 4,235,684.26; library 73,777.37;
   cemeteries 19,405.39; conservation 399.22; park 34,670.67; special detail wages 47,964.24; unclassified 351,175.87;
   debt 888,760.48; agency/payroll deductions 1,434,504.93; petty cash 2,820.00; refunds 30,473.01; 2,048.22; 348,734.86;
   investments 8,709,203.29; payments deferred 172,602.77) sum to 17,927,069.17.
4. **Stacked pairs, p55/2 (`MIDDLE SCHOOL: PRINCIPAL INTEREST`).** `PAIR` does not accept a leading `$` (`$ 65,000. 9,555.`),
   so the first issue's row is NOT split, its TOTAL (74,555 ...) and the GRAND TOTAL rows `check failed` for want of it.
   The same row has bare `$` in two cells. SANITARY LANDFILL and STREET BETTERMENTS split and check. Hand check:
   65,000+9,555 = 74,555; 260,000 + 21,840 = 281,840 (the printed total); 95,000 principal + 19,665 interest = 114,665.
5. **Omnibus budget, p76-77.** Items sum to the printed `TOTAL BUDGET VOTED: $6,133,681.00` (82 item rows, LIST TOTAL
   `checked`), and the section totals sum too (252,840 + 508,505 + 107,919 + 8,591 + 38,378 + 486,278 + 106,605 + 481,550
   + 28,300 + 4,039,559 + 75,156 = 6,133,681). The column validator, left on, tied the p77 TOTAL rows to the election
   table of p75 (`1282 822 225 at p77r4 ...`, a header carried across pages) and wrote nine false failures; the map
   sets `checks=none` for p76-77 instead. The validator should not take a header from a table 2 pages earlier.
6. **Tax collection, p67/1.** The map sets `header=row:1`: with the default the second header row (`1981 | $ | $ ...`)
   hid the columns and all 15 rows wrote blank amounts. `6,124.53fwd` (no space) reads as 6,124.53 in COMMITMENTS and the
   1981 motor vehicle row's second commitment `2.10` lands on its own row; the row's COMMITMENTS is 6,124.53 + 2.10 only
   if the page means both; NOT ESTABLISHED. Row labels (section/item) come out empty in the output, as in 1986.
7. **Calendar-year reconciliation, p70/3** (`report-treasurers-cash-calendar-year`): `no check`. The printed chain does
   NOT close on the page itself: 1,741,911.80 + 8,822,224.76 = 10,564,136.56, the page prints 10,542,136.56*, and
   10,564,136.56 - 9,039,140.59 = 1,524,995.97 where 1,502,995.97 is printed (a difference of exactly 22,000.00 in both).
   The 31 December accounts below sum to the printed 1,502,995.97, and the auditor's p8 schedule (same date) prints a
   Massachusetts Municipal Depository Trust Account of (22,000.00). A hypothesis only: nothing here tests that these are
   the same 22,000.
8. **Elections, p75/1.** Candidates and their votes are public (elected officials, ward of the annual election); landed as
   `report-elections` with the office as a heading row, no totals to check against.

## NOT LANDED / PRIVACY

- Named births: there are none in the sent pages (the 1986 births pages were not sent here either). No named births landed.
- Burials: no named burial list is in the sent pages (p44 prints cemetery receipts only).
- Vendor list: none printed (gap row).
- p35-p36 jury list (private residents): not sent for tables, not landed.
- p89/2: only the 1984 tuition rates have cells; the 1983 rates ($984 / $1,968 / $2,258 / $2,167) are in the lines only and no row is written from them.
- p3 tables, p89/1 school calendar: no money, mapped NOT LANDED.

## Integration pass, 30 October 2026: what was done with each item

- **Privacy:** TJ, 30 October 2026: *"Yes publish. Everything in the annual reports is public."* `withheld_rows` is removed from this folder's `edition.json`; the rows it held are published. (The reader's mechanism stays, unused, for a takedown.)
- 1 (net disbursed beside the ledger balance): APPLIED as the opt-in `recon_net_beside_ledger` (set here). p40/1 is now mapped to `treasurers-cash` (`stated_total` 1,154,794.21) under the widened `CASH_INVESTED`: 11 accounts published, the roll-forward 8 rows `checked`.
- 2a (`TOTAL RECEIPTS:`): APPLIED. 2d (`50:00`): APPLIED as the opt-in `colon_for_point` (set here). 2b, 2c: NOT APPLIED -- a rule that takes a labelled row as a subtotal, or an unlabelled one as an account, chosen because the statement then closes, is fitting the reader to the total. Receipts stay `check failed`.
- 3 (payments): NOT APPLIED. 3c `10,333.0°` was not a candidate for the cell witness: `locate_cell_misreads.py 1983` finds 0 cells pinned by two identities (the payments carry no row identity).
- 4 (`$` before a stacked pair): APPLIED. p55: 12 checked / 4 failed -> 15 / 3.
- 5 (validator header carried two pages): NOT APPLIED (shared validator); `checks=none` stays.
- 6 (`fwd` glued): nothing to apply -- `validate_totals.FWD` already reads `6,124.53fwd` (the row lands 6124.53).
- Found here: the accountant schedule pp57-66 prints no header and p56's header has no balance columns, so no identity applies (11 checked). Not changed.
- Names: p126 -> `report-school-budget-summary`, family `school-budget-summary` (was `school-general-appropriation` in special accounts). p125 family -> `school-receipts-returned-to-town` (it borrowed 1986's `school-state-aid-vs-appropriation`, a different layout). `report-office-budget-cuts` and `report-expenditure-shares` kept as new.
