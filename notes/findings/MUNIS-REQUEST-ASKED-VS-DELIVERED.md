# MUNIS request: asked vs delivered

6 October 2026. A snapshot: the figures below were read off the delivered spreadsheets that
day and are not regenerated -- the datasets in `sources/data/` are the source of truth.

The Town's 6 October answer delivered the two items we called most important -- school
special funds and period 13 -- and none of the transaction-level detail.

## Asked vs delivered

| # | What we asked for (4 Sept) | Delivered 6 Oct | Note |
| --- | --- | --- | --- |
| 1 | The same report for funds other than 0100 -- school grants, revolving, school choice; 12 funds named | **Yes** | All 12 named funds, every year, among 61 school special funds, account by account, FY2023-FY2026 |
| 2 | Period 13, the year-end close | **Yes, schools only** | FY2024, FY2025, FY2026 (and FY2023, not asked). Town-wide period 13 not delivered |
| 2 | Purchase orders closed after the initial close | No | |
| 3a | FY26 year-end transfer schedule, with counterparty and authority | No | Each account's net transfer only, as before |
| 3b | Journal export for kindergarten paraprofessional accounts S2032121 and S2032131 | No | A trial balance came for fund 1300 (lost books / tech) instead, which we did not ask for |
| 3c | Finance Committee minutes from 14 July 2026 | No | Not the Town Accountant's to send |
| 4 | Back years: account details, quarterly reports (periods 3, 6, 9), revenue ledger, transfers with authority, appropriation as voted | Mostly no | Period 13 only. The special-funds reports carry those funds' revenue lines |

Source files: `sources/town-ledgers/expenses/*-p13-*-school.xlsx` and
`sources/town-ledgers/account-details/account-details-fy2026-trial-balance-fund1300.xlsx`;
provenance in `sources/town-ledgers/expenses/PROVENANCE-fy2023-fy2026-p13-school.md`. The
request: `notes/generated/DATA-REQUEST.md`, sent as `2026-09-04-town-accountant-package` in
`notes/reference/records-requests.csv`.

## What it settles, and what to ask next

- **FY2026 school year-end is now known from the closed ledger.** The school General Fund
  spent $25,613,679.23 of a $26,332,564 revised budget, with $482,118.07 available, at
  period 13 (the report's own GRAND TOTAL line).
- **Money outside the general fund is visible for the first time** -- the 61 special funds'
  spending, by account, for four years. Whether their account codes let us attach each fund
  to a budget line is still a hypothesis.
- **The kindergarten paraprofessional accounts did not move at the close:** $93,691.03 +
  $5,373.12 = $99,064.15 spent against a $0 budget, the same total the request cited from
  June. What the spending was still needs the journal export.

Ask for next, narrowly:

1. The journal export for S2032121 and S2032131, FY2026.
2. Town-wide period 13 for FY2026.
3. The FY2026 transfer schedule with counterparties and authority.

A live copy of this note is a Claude Doc (private to TJ): MUNIS request: asked vs delivered.
