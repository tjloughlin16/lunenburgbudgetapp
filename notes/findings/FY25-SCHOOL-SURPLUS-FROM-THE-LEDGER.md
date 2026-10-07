# The FY25 school surplus, from the closed ledger

6 October 2026. Working notes, kept so the analysis is not lost; the report generated from
them recomputes every figure (`scripts/build_fy25_school_surplus.py`, when built). Figures
here were read off `sources/data/munis-school-ytd.csv` (FY2025, `gf-school`, `type` E, 415
accounts) that day -- a snapshot, not a source.

## What the data shows

| FY2025 school General Fund, period 13 | |
|---|---:|
| original appropriation | $25,304,074.00 |
| transfers and adjustments, net | -$122,502.44 |
| revised budget | $25,181,571.56 |
| spent | $24,554,454.70 |
| encumbered | $0.00 |
| available at the close | $627,116.86 |
| the district's figure, School Committee 17 Sept 2025 | $603,885.97 |

- The closed ledger shows **$23,230.89 more** unspent than the figure the School Committee
  was told. No single account and no pair of accounts equals that difference.
- Against the ORIGINAL appropriation, **$749,619.30** was not spent by the department:
  $627,116.86 turned back at the close plus $122,502.44 moved out during the year.
- **Scope checked:** the original appropriation equals the FY25 school figure in the Town's
  own revenue-distribution workbook (`revenue-distribution-fy26.csv`, `fy25` = 25,304,074).
  This run is department 300 only. (The FY2024 period-13 report run in August 2024 covered
  departments 300 and 301, so runs of this report are not automatically comparable.)
- **Nothing is still open:** encumbrances are $0.00, so the figure is final as the system holds it.

## Where it sat (net unspent by DESE function, from the account string's fourth segment)

| function | salary (obj 51xxxx) | non-salary |
|---|---:|---:|
| 2000 instruction | 136,171 | 112,326 |
| 4000 operations & maintenance | 113,829 | 113,746 |
| 7000 assets | -- | 64,748 |
| 9000 out-of-district tuition | -- | 29,946 |
| 3000 other student services | 5,192 | 24,915 |
| 1000 leadership / admin | 8,850 | 11,765 |
| 5000 fixed charges | -- | 5,629 |

Almost no account ended overspent (the largest over-lines are in operations and maintenance,
-18,750, and assets, -3,262). That pattern is observed; that year-end transfers absorbed the
overages is a hypothesis.

## Para accounts (function 2330)

Special-education paraprofessional lines ended under budget: primary 48,824.80, high school
21,767.92, middle 5,873.68, elementary 3,154.40. High-school paraprofessionals spent 4,785.74
of 34,960.00. Para budgets were moved between lines mid-year in both directions (e.g. middle
school SPED paras +53,674; elementary SPED paras -65,000). The "double booking of the para
salaries" named in the 17 September 2025 minutes is not visible at this grain.

## What it does not show

- What any dollar was spent on, or when -- no journal.
- Where the $122,502.44 moved out of the department went -- net per account, no counterparty.
- Why the ledger is $23,230.89 above the district's September figure. Entries posted after
  17 September 2025 are a hypothesis; nothing here tests it.
- Whether facilities' unspent salary was unfilled posts -- dollars are not posts (rule 7, 11).

## Closes with

The FY2025 transfer schedule for department 300 with counterparties and authority, and the
journal entries posted to department 300 after 17 September 2025.

## Consistent with, not proof of

The Town's explanation for FY25 -- *"significant turnover and unfilled positions in the
facilities department resulted in unspent salaries and stalled maintenance projects"* (quoted
in `sources/analyses/fy26-closeout.md`) -- is consistent with operations and maintenance
holding about $228k of the unspent total, split almost evenly between salary and non-salary.
