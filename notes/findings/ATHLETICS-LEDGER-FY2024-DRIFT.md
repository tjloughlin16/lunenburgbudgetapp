# `athletics-ledger.md` §7 no longer recomputes, and it moves a published headline

Found 5 September 2026 while running every verifier in the repo. **Not fixed, deliberately** —
the fix moves a number the site publishes, and which of two sources is authoritative for FY2024
is a decision, not an extraction detail.

## What fails

`python3 scripts/verify_records_request_2026_06.py` — 5 of 166 checks:

| the analysis says | the data now produces |
|---|---:|
| FY2024 Coaches, general fund | `65,073.00` → **`46,733.00`** |
| FY2024 Coaches, outside the general fund | `62,015.40` → **`80,355.40`** |
| FY2024 comparable general fund total | `153,339.00` → **`124,301.00`** |
| FY2024 outside the general fund | `198,303.89` → **`227,341.89`** |
| **the town's appropriation covered 44% of what the workbook says the sports cost** | **35%** |

The 44% figure is the headline of §7 and appears three times, including in the document's own
"what this does not say" table.

## Why

`scripts/verify_records_request_2026_06.py` maps the workbook's `Coaches` onto three general
fund lines: `Athletic Coaches`, `Freshman & MS Coaches`, `Unified Sports Coach`.
`sources/data/athletics-history.csv` holds all three for FY2020–FY2022 and FY2026, and **only
`Athletic Coaches` for FY2023–FY2025**.

That is not an extraction failure. The source those years are read from —
`district-budget/text/fy27-budget-projections-as-of-2-24-26-with-restorations.txt`, page 8 —
prints, verbatim:

    Athletic Coaches                        $100,351  $46,733  $155,614  $159,444  $159,444
    Unified Sports,Track/Basketball Coach     $1,200        -    $1,832    $3,812    $3,812
    Freshman & MS Coaches                          -        -         -   $14,415   $14,415

In the FY2024 column both of the other lines print a dash. The current reading is faithful to
that document. `65,073.00` is not derivable from it, and 65,073 − 46,733 = 18,340 matches no
line on the page.

## What has to be decided

**Which document is authoritative for FY2024 athletics actuals.** The FY2020–FY2022 rows in
`athletics-history.csv` come from `fy24-approved-budget.txt`; FY2023–FY2025 come from the FY27
projection files. The analysis was written when FY2024 was read from something else. Rule 1
applies: a figure taken from a forward budget document's actuals column and a figure taken from
an approved budget are not the same measurement, and rule 13 applies to the choice — whichever
is used, the document must quote the line and the column it rests on.

Until that is settled, **do not simply rewrite 44% to 35%.** The verifier recomputes from
`athletics-history.csv`, so making the prose match the script would publish whichever source the
extractor happens to prefer, which is the thing rule 13 exists to prevent.

## What is already fixed

Three failures in the same verifier were mechanical and are repaired:

- it looked for `account-details-fy2024.xlsx`; the archive reorg renamed these to
  `account-details-fy2024-fund1301.xlsx`
- it required `PROVENANCE-fund1301.md` to contain its own sha256, because the skip still
  named the file `PROVENANCE.md`
- `athletics-ledger.md` said the classifier scans 220 documents and finds 18 on a ledger
  basis; it scans 349 and finds 10. `athletics.md`'s basis table had drifted the same way and
  is corrected.
