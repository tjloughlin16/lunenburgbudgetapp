# The combined balance sheet, read from the page

**What this is.** The COMBINED BALANCE SHEET — ALL FUND TYPES AND ACCOUNT GROUPS from the
annual town reports: what the town HOLDS at 30 June, by fund type, transcribed by **reading
the rendered page directly** rather than by OCR.

    sources/data/balance-sheet.csv                 the figures
    sources/data/balance-sheet-printed-totals.csv  the totals the report itself prints
    scripts/render_report_page.swift               renders a page to PNG
    scripts/append_balance_sheet_year.py           adds a year, and REFUSES one that does not tie
    scripts/verify_balance_sheet.py                checks one against the other

## Why this table

Every other dataset in this archive measures money **moving** — appropriated, received,
disbursed. This is the only table in the annual reports that measures what the town
**holds**: cash, receivables, warrants payable, reserves and undesignated fund balance. It
is where free cash comes from and where the enterprise funds' accumulated position sits.

`notes/reference/EXTRACTION-GAPS.md` counted it as surveyed in fourteen editions, 488 figure
rows, and **no dataset held any of them**.

## Why it is READ rather than extracted

`pdf_tables.py` names this page as one where layout extraction recovers **zero** of its 61
money tokens. The OCR is worse than that on the older editions — FY2023's page comes out as
`TOTAL LIABILITIES/FLIND EQUITY` with `$` read as `5` or `8` throughout, and the FY2011 and
FY2012 pages lose the entire heading and the cash section above the receivables.

The pages themselves are clean. Every one examined so far renders legibly at the default 2x
— including FY2023, the worst OCR of the sixteen. So this uses the method
`PROVENANCE-special-revenue-read.md` established: render, read, and write nothing down that
independent checks do not confirm.

**A figure read off an image is a READING.** It has the same status as the OCR's output —
an instrument's product, not a published number — and rule 13 applies to it in full.

## What makes a reading trustworthy here: four checks, and one of them is a second document

1. **Column footing.** Each fund column's detail rows must sum to the total the report
   prints for that column, in each of the three sections. Independent because the town
   printed the total; we did not derive it.
2. **The identity the table states.** `TOTAL LIABILITIES + TOTAL FUND EQUITY = TOTAL
   ASSETS`, per column — and the sheet reprints TOTAL ASSETS at its foot as a
   `TOTAL LIABILITIES/FUND EQUITY` row, so the town's own two totals must agree as well.
3. **A CROSS-DOCUMENT check, which is the strongest thing available.** The Special Revenue
   Funds schedule elsewhere in the *same report* prints a GRAND TOTAL balance carried
   forward, and that schedule carries the enterprise funds inside it. So

       SPECIAL REVENUE fund equity + ENTERPRISE fund equity == special revenue carried

   This ties the balance sheet to `special-revenue-read.csv` — thirteen editions already
   verified to the penny, read from **different pages** by a **different pass**. It was
   confirmed to the cent on FY2011, FY2013, FY2019 and FY2022 *before a single row was
   written down*.
4. **The long-term debt mirror.** The account group prints the same figure as an asset
   (`AMOUNT TO BE PROVIDED FOR RETIREMENT OF GENERAL LONG TERM DEBT`) and as a liability
   (`GENERAL OBLIGATION LONG TERM DEBT`). They must match.

Passing one could be luck. Passing four, where the third involves a separate document, is
not.

**A year that does not tie is not written down here.** `append_balance_sheet_year.py`
merges into a copy, runs the verifier against the copy, and replaces the real files only if
every check passes — because "append, then verify" leaves an unreconciled row in a file
somebody can query while the complaint scrolls past.

Each check was shown to have power to fail before the dataset was believed: a single
transposed digit in `TAX LIENS` is caught by the footing, a dropped `RESERVED FOR
ENDOWMENTS` row by the fund equity total, and a $1 change in the special revenue carried
total by the cross-check.

## Rounding is a property of the page, not a tolerance we grant

The GENERAL LONG-TERM DEBT column is printed **to the dollar** in its total rows while its
detail rows sometimes carry cents — FY2022 prints detail `$38,749,084.72` and total
`$38,749,085`. That column alone is checked to within $1; every other column is checked to
the cent. The allowance is named and confined rather than applied everywhere.

## Coverage

| edition | figures | printed page | checks |
|---|---:|---:|---|
| FY2011 | 61 | 53 | all four, to the penny |

FY2012–FY2023 are surveyed and legible but **not yet transcribed**. The table above is the
honest count, not the ambition.

## The town-wide balance sheet does NOT exist for FY2024 or FY2025

Both reports print a **Combining Balance Sheet — Enterprise Funds** instead, and only that.
FY2024 prints it twice, on pages 21 and 28, with identical figures; its own table of
contents says page 21 should be "Balance Sheet for FY Ending June 30, 2024" and the
town-wide sheet is simply absent. These are a different table with a different population —
four enterprise funds, not six fund types — and they belong in an enterprise-fund dataset
of their own, checked against their own printed `Proof` row. Appending them here would put
rows into a schema whose column meanings they do not share.

So the ceiling on this dataset is **FY2011–FY2023, thirteen editions**, which is the same
span the special revenue read covers and not a coincidence: they are checked against each
other.

## One printed sheet does not balance itself, and it is recorded rather than fixed

**FY2019, FIDUCIARY TRUST and AGENCY column.** The page prints `TOTAL ASSETS
$3,841,163.85` and `TOTAL LIABILITIES/FUND EQUITY $3,183,866.50`. The page disagrees with
itself by **$657,297.35**. Both sides foot to their own printed totals — assets are
$3,845,771.57 cash less $4,607.72 `DUE FROM/TO GENERAL FUND`; equity is the single
`UNDESIGNATED` figure with `TOTAL LIABILITIES $0.00` — so this is not a transcription
error, it is what the town printed.

*What is not established:* why. FY2020 and FY2021 both carry a `RESERVED FOR ENDOWMENTS`
line in that column ($661,563.75 and $668,915.17) which FY2019 does not print, and that is
close to the gap. **That is a hypothesis and nothing here tests it.** The document that
would settle it is the audited financial statements for FY2019, which the annual report
does not contain.

It is pinned to the exact amount in `PRINTED_DEFECTS` in the verifier. If it changes by a
penny the check fails again — a new discrepancy hiding inside an old allowance is exactly
what an exception list exists to prevent. Nothing is adjusted to make it tie.

## The cross-check does not hold on FY2023, and that is known before anyone transcribes it

Reading FY2023's page (printed page 24) gives `TOTAL FUND EQUITY` of $6,131,303.68 for
SPECIAL REVENUE and $3,812,502.24 for ENTERPRISE — $9,943,805.92 together. The FY2023
special revenue schedule prints a GRAND TOTAL carried forward of **$10,031,099.78**. They
differ by **$87,293.86**, where FY2011, FY2013, FY2019 and FY2022 agree to the cent.

FY2023 is also the year `verify_special_revenue_read.py` already records a restatement
break in: the town re-cut its grant funds by year between the FY2022 and FY2023 reports and
restated $17,861.24. **These are two different amounts and nothing here connects them.**
The gap may be a fund moved between statements, a restatement, or a reading error in
figures nothing has yet checked — those two equity figures are a reading off one page and
have not been through the four checks. Whoever transcribes FY2023 finds out which; until
then it is an open question, not a defect, and it is not in `PRINTED_DEFECTS`.

## Page numbers: the catalogue holds the PDF index, not the printed page

`annual_report_catalogue.pages` for this table is the **PDF page index**, and the two
differ by an offset that is not constant across the sixteen reports. Reading the catalogue
figure as a printed page lands you on the wrong page — FY2019's catalogue entry says 28,
and printed page 28 is the FY2019 receipts table; the balance sheet prints **26**.

`render_report_page.swift` takes a *printed* page number and infers the offset from the
document, and its inference is also wrong on some of these: it reported +1 for FY2011 where
the true offset is +3, and +1 for FY2019 where it is +2. **Confirm from the number printed
at the foot of the rendered image, every time.** Both numbers are recorded in the CSVs,
`page_printed` and `page_pdf`, so neither has to be re-derived.

| edition | PDF index | printed page | confirmed from the page foot |
|---|---:|---:|---|
| FY2011 | 56 | 53 | yes |
| FY2013 | 61 | 57 | yes |
| FY2019 | 28 | 26 | yes |
| FY2022 | 24 | 24 | yes |
| FY2023 | 24 | 24 | yes |

The PDF indices for the remaining editions — FY2012 p56, FY2014 p20, FY2015 p20, FY2016
p20–21, FY2017 p20, FY2018 p26, FY2020 p22, FY2021 p23 — come from the OCR (`grep` for
`TOTAL LIABILITIES` in `sources/town-budget/ocr/`). Their printed page numbers are **not
yet confirmed** and must be read off the foot of the image when each year is transcribed.

## How a year is added

    # find the PDF page
    grep -i 'total liabilities' sources/town-budget/ocr/<doc>.tsv | cut -f1 | sort -un

    # render it; check the number printed at the FOOT against what you asked for
    swift scripts/render_report_page.swift <report.pdf> <scratch-dir> <page>

    # transcribe into two staged CSVs of the same shape as the real ones, then
    python3 scripts/append_balance_sheet_year.py --rows staged-rows.csv \
                                                 --totals staged-totals.csv

Scratch directories go under `/private/tmp`, never in the repository.

## What this dataset is not

Rule 11 applies here as everywhere: these are the town's **general-purpose financial
statement** figures as printed in the annual report. They are unaudited as published, the
report contains no notes, and a fund balance is not a measure of what anything cost or of
what any service consumed. `FUND BALANCES: UNRESERVED: UNDESIGNATED` for the general fund
is *not* free cash — free cash is certified by the Division of Local Services from a
different submission, and the two are related but not the same number.
