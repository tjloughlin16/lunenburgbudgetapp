# Tolerances: when a check may close without tying to the cent

**The policy in one line:** a printed total, or a row's own printed identity, closes if it is
within **$1.00** of what its parts sum to, and when it closes that way it SAYS SO, in the words
`within $1 rounding tolerance`, and is counted. Anything else either ties exactly, or has an
allowance listed below with its reason, or it does not close.

TJ approved the $1 allowance on 29 October 2026 for printed totals and extended it on
30 October 2026 to a row's own identity. On 31 October 2026 he asked for it to be findable in
one place: *"we should have an approved $1 allowance. if thats not easily discoverable lets make
a POLICY doc that pulls all this info into 1 place."* This is that place. A script that applies
a tolerance should point here, and a new tolerance is written here before it is coded.

## Why an allowance exists at all

The town's printed reports round. A column of whole dollars rarely adds to a total printed
from the unrounded figures; a schedule may carry cents in its rows and print its total to the
dollar. Refusing those pages calls the town's arithmetic wrong when it is only rounding, and it
blocks pages whose every row ties.

**Rounding is the likely cause, and it is a HYPOTHESIS** (rule 7). Nothing here tests it. A $1
miss could also be a misread digit in the last place. That is why the allowance is capped at a
dollar and labelled every time: a reader can count how much of the archive rests on it, and a
later witness (a ledger, a better scan) can re-open any one of them.

## The $1 allowance: where it applies

| check | applies? | where it is coded |
|---|---|---|
| a printed column total against its rows (annual reports, all editions 1959-2010) | yes | `validate_totals.close(tol=)`, from each `edition.json` `rounding_tolerance_usd: 1` |
| a row's own printed identity, e.g. appropriated + forward = available | yes, 1984 and 1991-2010 | `row_identity_tolerance` in `edition.json`; `read_report_tables.py` |
| a debt schedule row's TOTAL against its year columns | yes, 1991-2010 | `debt_row_totals` in `edition.json` |
| a list of voted lines against TOTAL BUDGET VOTED | yes, 1964 | `list_total_tolerance` in `edition.json` |
| the combined balance sheet: column footing, assets = liabilities + equity, the reprinted total, the debt mirror | yes | `verify_balance_sheet.py` (`mark()`) |
| percent, rate, count, ratio or vote columns | **never**: $1 is meaningless there | `validate_totals.PERCENT_COL` |
| election pages | **never** | `tol_off_pages` |
| a cross-document check, where one schedule is checked against another | **never**: two documents are not rounding against each other | `verify_balance_sheet.py` check 3 |
| a case where an exact tie also exists | **never displaces it**: the exact run wins | `validate_totals.close()` |
| a projection, or any model figure | **never** | rules 1 and 2 |
| FY2011-FY2025 annual-report editions | not opted in | their own extractors |

**How it is labelled.** A row that closed inside the allowance carries
`within $1 rounding tolerance (printed differs by $N)` in its `reconciliation`, and its status
is `checked`. The phrase is one constant, `validate_totals.TOLERANCE_PHRASE`;
`build_annual_reports.py` counts rows by it, and the caveat on `/analysis/annual-reports` is
computed from that count. `verify_balance_sheet.py` prints `ok~` and the same phrase, and its
summary counts them. **Do not reword the phrase.** The count depends on it.

## Other standing allowances, each with its reason

These predate the policy. Each is confined to the column or check that needs it.

| allowance | where | why |
|---|---|---|
| **exact to the cent** (the default) | everywhere not listed | |
| half a unit per item | `validate_totals.close()` | the items are printed to finer places than their total (shares to 4 places summing to `1`); the page itself shows the rounding |
| **$1 per row** on rounded columns | `extract_town_ledger.py`; `notes/reference/SCHEMA.md` *Sign conventions and rounding* | MUNIS prints `original`, `transfers`, `revised` to whole dollars, so N rounded rows can miss the GRAND TOTAL by up to N dollars. `expended` carries cents and must tie exactly. That column would move if a row were dropped |
| $1 per row or 0.25%, whichever is larger | `extract_line_history.py` (`total_check`) | **wider than the policy, deliberately.** It decides whether a page of text is a budget at all, not whether a figure is right; the FY19 approved budget's printed total omits one of its own rows. The difference is reported, not hidden |
| under $5 | `audit_provenance.py` base check | the expense base rebuilt from `fy27_balanced` against the published appropriation. Whole-dollar lines summed |
| one cent | `extract_gl_history.py` `TOLERANCE` | binary floating-point summation noise only |
| none, to the cent | `verify_enterprise_balance_sheet.py` | nothing on that page is printed to the dollar |
| **no printed total counts as reconciled, footnoted** | `build_monty_tech_history.py` (`NO_TOTAL`) | TJ, 2 November 2026: *"if there are no totals, we need to consider them reconciled ... we can caveat it of course... with a footnote"*. A page that prints no total has nothing to fail against, so a reading of it is grouped with the reconciled ones rather than flagged. Its own status still says `No total to check against`, and every chart that groups it says in its note how many such years it counts. A `check failed` reading is NOT covered: that is a page whose total exists and was missed |

## What is NOT an allowance

- **A printed defect, pinned exactly.** `verify_balance_sheet.PRINTED_DEFECTS` records a page
  that disagrees with itself, to the cent, with what is not established. If the difference
  moves by a penny the check fails again. That is an exception list, not a tolerance.
- **A $10, $100 or $1,000 miss, or a transposed digit.** Those are the signature of hand-keyed
  figures (`notes/findings/ANNUAL-REPORTS-1959-2010-FINDINGS.md`) or a misread. They stay
  open, go to the cell witness, or are `blocked` in `page-blocked.csv`. They are never
  absorbed.
- **Disagreeing hand-built figures.** Never averaged or reconciled into one number (rule 13a).
  Publish the spread.

## Adding or changing a tolerance

1. TJ approves it. Record the date and his words here.
2. Add a row above: the check, the amount, the reason, and the file.
3. Code it as a named constant or an `edition.json` opt-in with a `_why`, never an inline number.
4. Label every closure it makes, and count them. A tolerance nobody can count is a place
   errors hide.

## Checking it

    python3 scripts/verify_balance_sheet.py        # summary line counts the checks closed within $1
    python3 scripts/build_annual_reports.py --check
    grep -c "within \$1 rounding tolerance" sources/data/report-*.csv
