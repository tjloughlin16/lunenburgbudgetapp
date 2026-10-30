# 1981 edition: what the shared code needs (for the integration pass)

Edition: calendar 1981 annual town report, `4503-1981-annual-town-report.pdf`, 140 pages. Tables were read
on the 58 pages `find_financial_pages.py --list 1981` picked; 82 tables (map.csv), 42 landed pages
(pages.csv). Hand checks below were computed from `build/textract/out/4503-1981-annual-town-report.cells.tsv`.
The opt-ins in edition.json: `unlabeled_subtotals`, `rounding_tolerance_usd`, `accountant_marks`,
`stop_for_comma_without_dollar`, `id_column_words`, `recon_net_on_transfer_line`, `stacked_pairs`, `receipts_span`
(the last four are the ones 1981 actually exercises; the others are inert here and set per the brief).

## FINDER MISSES: 0

Every page not in the picked list has `lines.tsv` text but no money table (the 140 pages were not scanned figure by
figure; the picked list has 58 pages and the picked pages with no table returned (p20, p21, p22, p30, p45, p53, p134, p136, p137, p138) are prose pages with dollar figures). Bound, not proof.

## ROSTER PAGES

p20 roster of firemen; p69-78 School Department staff (administration, guidance, teaching staff by school,
custodial, cafeteria) with a start date per name and no pay; written to `rosters.csv`. Not sent for tables.
p61-65 name staff in personnel-change prose. NO named births were landed (none on a sent page); burials
(p15) follow the 1988/2010 precedent.

## PRIVACY

`withheld_rows`: 124/1/17, 124/1/18, 124/1/20 -- three pupils named as prize grant recipients on the school
prize fund (children). The `Grants` subtotal on that page (150.00) is the figure in the rows. Names not repeated.
No vendor list is printed in 1981 (no payee names with addresses).

## SHARED-CODE CHANGES THE EDITION NEEDS (none made here)

1. **`emit_cash_reconciliation` crashes on a line whose figures print commas for decimal points**
   (p95 table 2: `20,096,425,52 (11,420,305,18)`). `raw_figures` reads the raw cell text, so the `Disbursements
   ... Less Revenue Cash Invested` line has a matching label and no figures, and `figs[0]` raises IndexError and
   stops the whole edition. The comma-for-decimal repair in CALENDAR_REPAIRS exists
   (`(\$?\d{1,3}(?:,\d{3})*),(\d{2})`) but is not applied to the cells this emitter reads. Change: apply
   CALENDAR_REPAIRS to the cell text in `raw_figures`, or guard `figs[0]`. Until then 95/2 is mapped NOT LANDED
   (no dataset). By hand the chain closes: 1,623,718.31 + (20,125,619.66 - 11,465,899.43 = 8,659,720.23) =
   10,283,438.54; less (20,096,425.52 - 11,420,305.18 = 8,676,120.34) = 1,607,318.20 = the p95 list of accounts
   (12 accounts, checked in notes.csv) and the p93 June total.
2. **`RECEIPTS_GRAND = r'GRAND TOTAL|^TOTAL RECEIPTS$'` misses `Total Receipts:`** (trailing colon, p100). The
   row is counted as an account, the 177 accounts "sum" to twice the total, and every receipts row reads
   `check failed`. The map also states `stated_total=20125619.66`. Change: `^TOTAL RECEIPTS:?$`. By hand the 177
   accounts sum to the printed 20,125,619.66 to the cent (the doubled figure 40,251,239.32 is that plus the row
   itself), so all 177 should read `checked`.
3. **`_pair` (stacked principal/interest) does not accept a leading `$`**: p111 table 2, `MIDDLE SCHOOL: PRINCIPAL
   INTEREST | $ 65,000 15,015 | ...` is not split, the row publishes no figures and the TOTAL / GRAND TOTAL rows
   fail by exactly its amounts. Change: let `_pair` strip a leading `$ `. (Rows for the landfill split and close.)
4. **A transfer label split over two rows** (p109 table 1: `Less Investments Transferred to Revenue` / `Sharing
   Cash Account | 131,931.13`): the net sits on the second label row, which the emitter ignores, so the next
   unlabelled figure (238,700.18) is taken as the net. Change: a label row with a figure that continues a
   `LESS ...` label is the net. By hand it ties (see map note).
5. **Accountant schedule identity** (p112-120, 532 rows, 84 `checked` only on the omnibus rows). 1981 heads
   `Balance to Revenue | Balance to Fiscal 1982` and `Total Expended`, which none of the IDENTITIES patterns
   match. Proved offline (scratchpad probe, nothing written): adding
   `('BALANCE\\s+TO\\s+REVENUE', [(1, 'AVAILABLE'), (-1, 'TOTAL EXPENDED'), (-1, 'BALANCE\\s+TO\\s+FISCAL')],
   {'blank_target': 'zero', 'needs': ['AVAILABLE']})` to `IDENTITIES['accountant-schedule']` gives checked 119,
   check failed 7 (p113 x2, p115, p117 x2, p118, p120), no check 241, from 2 checked. The seven should be read.
   Printed headers for the report's pages: `Approp. Forward | Total Funds Available | Accounts Amounts | Expended |
   Total Expended | Balance to Revenue | Balance to Fiscal 1982`.
6. **PROOF registrations** for the NEW datasets (`map_annual_report_pages.PROOF`; they also need adding to
   `NEW_GENERIC` in `read_report_tables.py` if that list is used to grade pages): `report-cash-management`,
   `report-school-budget-summary`, `report-treasurers-outlook`. Page state is `unproven` on 30 of 42 pages until then.
7. **A subtotal-aware check for the Treasurer's payments (p101-104) and the balance sheet (p105-108)**. Both
   close by hand and the instrument calls them `no check`: the 20 right-hand-column figures of p101-104 sum to
   the printed Total Payments 20,096,425.52; the asset side (1,807,887.86 + 5,337,361.26) and the liability side
   (sixteen subtotals) each sum to the printed 7,145,249.12; the trust funds in custody sum to the printed
   193,335.35. `report-cash-management` columns also tie by hand (map note) but the validator groups the
   deduction row wrongly, so `checks=none`.
8. **p123 table 3 needs a re-read by panel**: four funds' roll-forwards (cemetery, sidewalks and grounds, library,
   worthy poor) merged by Textract into one table; mapped NOT LANDED rather than put a figure under the wrong
   fund. The year-end balances are landed elsewhere (122/1, 107/3 and 108/1). Perpetual-care bequests (named
   donors, gifts to the Town) are on this page.

## NEW DATASETS / FAMILIES (reuse where the same quantity)

NEW datasets: `report-cash-management` (the State-required monthly cash management chart),
`report-school-budget-summary` (the School Committee's summary of accounts: appropriation, spent, request),
`report-treasurers-outlook` (the Treasurer's own FY83 projection and an illustration: an ESTIMATE). Existing
settled names reused: `report-school-staff-fte`, `report-school-state-aid` (new family
`school-receipts-returned-to-town`), `report-school-special-accounts`, `report-statement-of-payments`,
`report-fund-balance-sheets`, `report-revenue-sharing`, `report-treasurers-cash-calendar-year`,
`report-treasurers-cash-reconciliation` (`cash-reconciliation-revenue-sharing`), `report-fee-schedule`
(`school-tuition-rates`, new family `proposed-license-permit-fees`: PROPOSED stage), `annual-report-receipts`,
`report-property-tax-exemptions`. New families in existing datasets: `report-valuation`
`raised-by-taxation-five-year`; `report-appropriations` `omnibus-funding-sources`, `special-articles-voted`
(a voted stage, deliberately NOT in the proposed-stage warrant-article dataset) and
`special-article-funding-sources`.

## WHAT THIS REPORT PRINTS THAT 2010 DID NOT

The State cash management chart (p93); the Treasurer's FY83 outlook and the hidden-payroll-cost example (p94);
the School Committee's own summary of accounts and special accounts (p86-91); a revenue sharing fund with its
own reconciliation, receipts, payments and balance sheet (p109-110); two Treasurer's reconciliations (fiscal and
calendar year, p95 and p124); a Treasurer's detailed statement of payments (p101-104); and per-fund balance sheets.

## Integration pass, 30 October 2026: what was done with each item

- **Privacy:** TJ, 30 October 2026: *"Yes publish. Everything in the annual reports is public."* `withheld_rows` is removed from this folder's `edition.json`; the rows it held are published. (The reader's mechanism stays, unused, for a takedown.)
- 1 (IndexError on p95/2): APPLIED, always on. `emit_cash_reconciliation` reads each cell through `recon_figures` (CALENDAR_REPAIRS per token when the raw text yields no figure) and no longer indexes an empty list. p95/2 is now landed (`report-treasurers-cash-reconciliation`, `cash-reconciliation`): 7 rows `checked`, every step of the chain closing.
- 2 (`Total Receipts:`): APPLIED, always on (`RECEIPTS_GRAND` takes the colon and `TOTAL RECIPTS`). 176 accounts `checked`.
- 3 (`$` before a stacked pair): APPLIED, always on (`PAIR`). p111: 10 checked / 7 failed -> 16 / 3; the three left are the block walk's grouping.
- 4 (wrapped transfer label, p109): APPLIED, always on. 11 rows `checked`.
- 5 (accountant identity): APPLIED, always on, as a widening of the 1988 and 1991 identities (`BALANCE (?:TO )?REVENUE`, `BALANCE (?:TO )?(?:FY|FISCAL)`). Accountant schedule 136 checked / 7 failed (the seven named here).
- 6 (PROOF): APPLIED for `report-cash-management`, `report-treasurers-outlook`, `report-school-budget-summary` (and NEW_GENERIC, build_db, table-semantics).
- 7 (subtotal-aware payments / balance sheet): NOT APPLIED. It is the validator's block walk, shared with the FY2011-FY2025 reviews; no prior pass has changed it either.
- 8 (p123/3 re-read by panel): NOT APPLIED -- needs a new Textract read, outside this pass.
- Names: `report-school-budget-summary` kept (the unified name); p88/2 family renamed `budget-by-cost-kind`. `school-receipts-returned-to-town` kept in `report-school-state-aid` (now the family for the same table 1982-1984).
