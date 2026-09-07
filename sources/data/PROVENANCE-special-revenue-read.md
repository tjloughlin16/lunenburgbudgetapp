# Special revenue funds, read from the page

**What this is.** The Special Revenue Funds schedule from the annual town reports —
balance brought forward, total receipts, total disbursements, balance carried forward, per
fund — transcribed by **reading the rendered page directly** rather than by OCR.

    sources/data/special-revenue-read.csv             the figures
    sources/data/special-revenue-printed-totals.csv   the totals the report itself prints
    scripts/render_report_page.swift                  renders a printed page to PNG
    scripts/verify_special_revenue_read.py            checks one against the other

## Why a second dataset for a table we already extract

`special-revenue-funds.csv` is made by `extract_special_revenue.py` from OCR geometry, and
**not one of its sixteen years ties to its own printed grand total.**

That is not the extractor's fault, and it was checked rather than assumed: for FY2022 the
OCR produced 483 amounts totalling $31,220,415.35 and the dataset holds 483 amounts
totalling $31,220,415.35. Identical. Every amount the instrument produced was captured.

The instrument is the problem, and it is a *good* instrument — it is simply not good
enough for a table that has to tie exactly:

| what it did | on FY2022 |
|---|---|
| dropped a cell | page 33, `Adult Education` receipts, **$3,330.00**, one value out of ~70 |
| misread a digit | page 34, `Insurance Recoveries - Police` disbursements read as **$19,726.17**; the page says **$19,725.17** |
| mangled names | `FY22 ESSER III #119` → `FY22 ESSER Ill #119`; `Title IV` → `Tille IV` |
| **misread the target** | the printed GRAND TOTAL for receipts is **$9,235,154.01**; OCR recorded **$9,236,164.01** |

That last row is why the two datasets are kept apart rather than one correcting the other.
The reconciliation was being measured against a number that was itself wrong by $1,010.

## What makes a reading trustworthy — which is not that a model produced it

**A figure read off an image is a READING.** It has exactly the same status as the OCR's
output: an instrument's product, not a published number. Rule 13 applies to it in full.

It becomes trustworthy because two *independent* things check it:

1. **The report's own printed GRAND TOTAL**, four columns, all four must tie. Independent
   because the town printed it; we did not derive it.
2. **The identity the table states** — forward + receipts − disbursements = carried —
   on every row.

Passing one could be luck. Passing both is not: a wrong digit that survives the row
identity must be compensated by another wrong digit in the same row, and must still leave
the column total unchanged.

**A year that does not tie is not written down here.** It stays out until it does.

## Coverage

| edition | funds | rows tie | columns tie |
|---|---:|---|---|
| FY2022 | 167 | 167 of 167 | 4 of 4, to the penny |

Fifteen editions remain. The schedule runs pages 33–37 in FY2022; the pages differ by year
and are named in `annual_report_catalogue`.

## How a year is added

    swift scripts/render_report_page.swift <report.pdf> <dir> 33 34 35 36 37
    # read each page, append rows to special-revenue-read.csv
    # record the GRAND TOTAL row in special-revenue-printed-totals.csv
    python3 scripts/verify_special_revenue_read.py

The renderer takes the **printed** page number and works out the offset to the PDF index
from the document itself, because that offset is not constant across the sixteen reports.
