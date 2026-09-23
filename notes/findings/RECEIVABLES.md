# The Collector's RECEIVABLES SUMMARY, and what is surprising about it

`scripts/extract_receivables.py` -> `sources/data/receivables.csv` and
`sources/data/receivables-reconciliation.csv`. Everything below was checked on the page,
by rendering it, not inferred from a reading:

    swift scripts/render_pdf_page.swift sources/town-annual-reports/docs/<report>.pdf <page> /tmp/p.png

---

## 1. Two of the 29 pages are not this table at all

`sources/data/annual-report-pages.csv` marks 29 pages `subject=receivables`, and that
column is a guess off a heading. Twenty-seven are the Collector's `COLLECTION OF TAXES /
RECEIVABLES SUMMARY`. The other two are different tables in the FY2024 report:

| page | what it actually is |
|---|---|
| FY2024 p21 | `Combining Balance Sheet - Enterprise Funds`, on which `Receivables:` is a stub heading over six blank lines |
| FY2024 p22 | `General Fund Accounts Receivable Detail` — a different table, different columns |

Neither is read by this extractor. FY2024 p21 is also the page
`money_gaps` already records as the year the town-wide balance sheet stopped being
printed.

## 2. The table runs onto a page that does not repeat its heading

FY2015 page 45 and FY2025 page 41 open straight into `OTHER EXCISE TAXES` and end in the
GRAND TOTAL. Looking for the heading finds neither, and losing the last page loses the
control total and with it the whole year. The page run is extended over any following
page that prints a GRAND TOTAL and no title line of its own.

## 3. The COLUMN ORDER changes between years, and nothing says so

Same eight headings, two different orders:

| years | order as printed |
|---|---|
| FY2016, FY2017, FY2018 | FORWARD COMMITTMENTS **ADJUSTMENTS REFUNDS PAYMENTS ABATEMENTS** TRANSFER BALANCES |
| FY2019 onward | FORWARD COMMITTMENTS **ABATEMENTS PAYMENTS REFUNDS TRANSFER ADJUSTMENTS** BALANCES |

A reader who assumes one layout and carries it to the other year gets four columns
transposed and a table that still looks plausible. Every page's header is read, per page,
and `column_order` is written into the reconciliation file for each year.

## 4. FY2023 and FY2024 are both headed `FY2021 COLLECTION OF TAXES`

Verified on the rendered page in both reports. FY2023 page 54 reads

    TOWN OF LUNENBURG
    FY2021 COLLECTION OF TAXES
    RECEIVABLES SUMMARY
    JUNE 30, 2023

and FY2024 page 38 the same, over `JUNE 30, 2024`. The date line and every figure belong
to the year on the cover — FY2023's opening balance is FY2022's closing balance to the
cent — so this is a stale heading in the town's own template and not a misfiled table.
**It means the fiscal year cannot be taken from the heading**, which is the obvious place
to take it from.

## 5. FY2018 opens $13,300.00 above where FY2017 closed

Both figures are printed, each on its own GRAND TOTAL line, in two different annual
reports:

| | printed GRAND TOTAL |
|---|---:|
| FY2017 BALANCES | $9,008,228.35 |
| FY2018 BALANCE FORWARD | $9,021,528.35 |

Every other consecutive pair that can be checked agrees exactly (FY2020->FY2021 and
FY2021->FY2022 to the cent, FY2022->FY2023 two cents apart, FY2023->FY2024 to the cent).

**What this does not show.** Nothing here says which figure is wrong, or whether either
is: a receivable balance can legitimately be restated between one year's report and the
next, and the two reports were produced a year apart. The column is published as
`opens_where_prior_closed` rather than described.
**— closes:** the Collector's own year-end receivable control for FY2017 and FY2018, or
the reconciliation of receivables that accompanies the free cash submission to DLS.

## 6. Five boxes of 2,795 were corrected, each one looked at

Each was found the same way: the year missed its own GRAND TOTAL by exactly one figure.
Each was then settled by rendering the page. They are listed in `CORRECTIONS` in the
extractor, addressed to a page and a coordinate.

| report | page | the page prints | the scanner returned |
|---|---|---|---|
| FY2017 | 45 | `($15,951.34)` | `$15,951.34` |
| FY2018 | 52 | `($1,106.89)` | `(51,106.89)` |
| FY2022 | 49 | `($14,434,655.16)` | `$14,434,655.16` |
| FY2023 | 55 | `(2,092.75)` | `2.092.75` |
| FY2023 | 55 | `47,179.26` | `7.179.2` |

Four of the five are the same defect: **these pages print negative figures in red
parentheses, and the scanner keeps the red and loses the brackets.** A dropped bracket
costs twice the figure, which is why it shows up so cleanly against a control total.

Two more losses were general enough to fix in the reader rather than by correction, and
both were invisible rather than wrong — a token that is not recognised as a figure is
never placed in a column at all:

- a trailing full stop (`$3,362.61.`, FY2021 p47), and
- a closing square bracket for a round one (`($170,480.35]`, FY2021 p48).

Each cost a whole year on its own.

## 7. Six of the twelve readings tie; six are refused, and none for the town's reasons

(Twelve readings of eleven years: FY2016 is held twice, in the report and in its addendum, and neither copy is readable.)

`receivables-reconciliation.csv` carries every year, published or not, with the reason.

| year | why it is not published |
|---|---|
| FY2015 | the header came back as ONE box (`COMMITTMENTS DJUSTMENT REFUNDS PAYMENTS ABATEMENTS TRANSFER BALANCES`); only one column position is measurable, so the pitch cannot be fitted |
| FY2016 | **both copies are clipped.** The main report's pages 47-49 stop before TRANSFER and BALANCES and print no GRAND TOTAL; the addendum's pages 9-12 print the total but their header names only six columns |
| FY2019 | the scan ends before the BALANCES column — the GRAND TOTAL line's last figure is returned as `(S91,94` |
| FY2024 | the scanner dropped most of the BALANCE FORWARD column on page 38: the detail sums $468,188.31 short of the printed forward total, while five of the eight columns tie exactly and a sixth is 8 cents out |
| FY2025 | the scan of pages 40-41 returns a fraction of the figures (`205072)`, `1938970`, `31,00.00`), and no GRAND TOTAL row survives it |

**Every one of those is a statement about the instrument, not about the town.** All five
years print the table and all five print a GRAND TOTAL somewhere in it — FY2025's is on
page 41 and was seen on the rendered page. What is missing is a reading good enough to
prove itself.
**— closes:** re-reading those eleven pages at higher fidelity
(`swift scripts/ocr_words.swift`), or the Collector's own receivable control report for
those years, which the accounting system can print directly.

## What is published, and what it is not

`receivables.csv` carries the years that tie: one row per printed line, the eight columns
as the town prints them, and `row_check`. Ten rows are marked
`two printed lines read as one` — two lines of the table whose label the scanner returned
once, published because they are part of a reading that ties and labelled because nobody
should quote one as a single line of the document.

A receivable is what is OWED to the town and not yet collected. It is not revenue, it is
not an appropriation, and a balance falling does not mean money arrived — an abatement, a
transfer to tax title and a payment all reduce it, and the table prints them in separate
columns for exactly that reason.
