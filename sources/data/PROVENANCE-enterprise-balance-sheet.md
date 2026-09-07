# The enterprise-funds balance sheet, read from the page

**What this is.** The COMBINING BALANCE SHEET — ENTERPRISE FUNDS from the FY2024 and FY2025
annual town reports: what the town's four enterprise funds **hold** at 30 June — Sewer,
Water, Solid Waste and PEG Access — transcribed by **reading the rendered page directly**
rather than by OCR.

    sources/data/enterprise-balance-sheet.csv                 the figures
    sources/data/enterprise-balance-sheet-printed-totals.csv  the totals and the Proof row
                                                              the sheet itself prints
    scripts/render_report_page.swift                          renders a page to PNG
    scripts/append_enterprise_balance_sheet_year.py           adds a year, and REFUSES one
                                                              that does not tie
    scripts/verify_enterprise_balance_sheet.py                checks one against the other

## This is RATEPAYER money, and that is the first thing to say about it

Rule 11. An enterprise fund is funded by the people who use it: sewer and water user
charges and betterments, trash fees, and PEG Access's cable franchise money. **None of
these balances is a tax dollar and none of it is available to the town's general
operations.** A sentence that puts $6.84M of FY2025 enterprise assets next to a school
budget gap is comparing two things that cannot be spent on each other.

The one place they touch is the `Due to/from other funds` line, which is a claim between
funds and not a transfer of ownership. In FY2024 the Sewer fund carries **(303,552.33)** on
it and the four funds together carry **(211,876.24)**; in FY2025 Sewer carries
**323,705.05** and the four together **448,414.78**. What the counterparty fund is, and why
the sign reverses between the two years, is **not established** by this sheet — it prints
one net figure per fund and names nothing.

## Why it is a dataset of its own, and not more rows in `balance-sheet.csv`

`PROVENANCE-balance-sheet.md` already records the reason and this document is its other
half. The town-wide COMBINED BALANCE SHEET — ALL FUND TYPES AND ACCOUNT GROUPS runs
FY2011–FY2023 and has **six fund-type columns**, one of which is a single `enterprise`
column. This is a **different table**: four *named funds* plus a memorandum-only total, a
different line list, and its own printed `Proof` row. The two share a shape and not a
meaning, so unioning them would put rows into a schema whose column meanings they do not
share.

**And FY2024 and FY2025 print no town-wide balance sheet at all.** That is the finding that
makes this dataset necessary rather than optional: for those two years the enterprise sheet
is the only balance sheet the town published.

## The table of contents and the page disagree, in both editions

Read off the rendered contents pages, verbatim:

| edition | contents page | the entry | what the page actually holds |
|---|---|---|---|
| FY2024 | printed 2 (pdf 2) | `Balance Sheet for FY Ending June 30, 2024    Page 21` | the enterprise sheet |
| FY2024 | printed 2 (pdf 2) | `Combining Balance Sheet– Enterprise Funds    Page 28` | the enterprise sheet, again |
| FY2025 | printed 2 (pdf 2) | `Balance Sheet for FY Ending June 30, 2025    Page 21` | the enterprise sheet |

FY2025's contents lists **no** enterprise-funds entry at all; its only balance-sheet entry
is the one naming a town-wide sheet that is not in the book. So in both editions a reader
following the contents to the town-wide balance sheet arrives at the enterprise sheet
instead.

*What this does NOT establish:* whether the town-wide sheet was produced and dropped in
layout, or never produced. Nothing on either page says. The document that would settle it
is the Town Accountant's FY2024 and FY2025 year-end submissions to the Division of Local
Services, which the annual report does not contain.

## FY2024 prints the same sheet twice, and that is used as a check

Printed pages **21** and **28** of the FY2024 report carry the identical table. Both were
transcribed independently and `verify_enterprise_balance_sheet.py` asserts that every one
of the 38 figures and 25 printed totals agrees between them. **They do, exactly.**

`printing` (1 or 2) is therefore a column in the CSV, and **nothing may be aggregated
across it without collapsing on it first** — summing FY2024 over both printings doubles the
town's money. `enterprise_balance_sheet`'s row in `table-semantics.csv` says so and its
default query filters `printing = 1`.

One correction to the catalogue while we are here: `annual_report_catalogue` records that
*"Page 21's copy also lost the fund-name column headers, which page 28 has."* **The rendered
page 21 carries the full header row** — `Sewer Enterprise Fund | Water Enterprise Fund |
Solid Waste Enterprise Fund | PEG Access Enterprise Fund | (Insert Name) Enterprise Fund ×4
| Totals (Memorandum Only)`. That note describes the OCR's output, not the page. Rule 13:
an instrument that reformats before you see it is part of the finding.

## What makes a reading trustworthy here: five checks

1. **Column footing.** Each fund column's detail rows must sum to the total the sheet
   prints for that column, in each of the three sections. Independent because the town
   printed the total; we did not derive it.
2. **The identity the sheet states.** `Total Liabilities + Total Fund Equity = Total
   Assets`, per column — and the sheet reprints Total Assets at its foot as
   `Total Liabilities and Fund Equity`, so the town's own two rows must agree as well.
3. **The sheet's own printed `Proof` row.** Rule 13: reconcile to a total the source itself
   prints. The Proof is recomputed as `Total Assets − Total Liabilities and Fund Equity`
   and must equal the zero the town printed, in every column.
4. **The memorandum cross-foot.** The `Totals (Memorandum Only)` column must equal the four
   fund columns added across — on every total row **and on every detail line**. This is the
   check that found the FY2024 defect below; the four total rows all tie, so nothing weaker
   than a line-by-line cross-foot would have seen it.
5. **FY2024's two printings**, above.

Every cell is checked to the **cent**. There is no rounding allowance: unlike the town-wide
sheet's long-term debt column, nothing on this page is printed to the dollar.

Each check was shown to have power to fail before the dataset was believed, by staging a
corrupted copy through the append gate:

| what was broken | what caught it | what was written |
|---|---|---|
| FY2025 Sewer cash `2,180,979.26` → `2,180,997.26` | column footing (+18.00) and the memorandum cross-foot | nothing |
| FY2024 printing 2's Sewer cash moved by 1¢ | the two-printings check, naming the cell | nothing |
| FY2025's printed Sewer `Proof` set to 1.00 | the Proof check (−1.00) | nothing |

**A year that does not tie is not written down here.**
`append_enterprise_balance_sheet_year.py` merges into a copy, runs the verifier against the
copy, and replaces the real files only if every check passes — because "append, then
verify" leaves an unreconciled row in a file somebody can query while the complaint scrolls
past.

## Coverage

| edition | figures | printings | printed page | pdf index | checks |
|---|---:|---:|---:|---:|---|
| FY2024 | 76 | 2 | 21 and 28 | 21 and 28 | all five, to the cent; one printed defect below |
| FY2025 | 38 | 1 | 21 | 25 | all four applicable, to the cent |

Both editions tie to their own printed `Proof`. Nothing was refused.

## Page numbers: the catalogue holds the PDF index, not the printed page

`annual_report_catalogue.pages` gives FY2025's sheet as **25**, which is the PDF index; the
page prints **21** at its foot. `render_report_page.swift` inferred the offset as **+1** for
FY2025 where the true offset is **+4**, and **0** for FY2024 where it happens to be right.
Both numbers are recorded in the CSVs, `page_printed` and `page_pdf`, so neither has to be
re-derived.

| edition | PDF index | printed page | confirmed from the page foot |
|---|---:|---:|---|
| FY2024 | 21, 28 | 21, 28 | yes — both pages print their own number |
| FY2025 | 25 | 21 | yes |

**Never trust the inference; read the foot.**

## What is recorded and what is not

Only cells that print a **figure** are rows here. The sheet prints `0.00` (FY2024) or `-`
(FY2025) on roughly half its lines and in four (FY2024) or two (FY2025) unlabelled template
fund columns — FY2024 heads them `(Insert Name) Enterprise Fund` — and those are the
spreadsheet's output for an empty cell, not data about a fund. They are not recorded and
they are not funds. Every total in `enterprise-balance-sheet-printed-totals.csv` carries the
**raw cell text** in its `quote`, including FY2025's Proof row, which prints `(0.00)` in the
Sewer and Totals columns and `-` in Water and PEG Access. The recorded amount is `0.00`; the
glyph is in the quote.

**Parenthesised negatives** are the sign convention on both pages and have been checked
explicitly, because a missed one has already cost this repository $315,772 elsewhere. Four
cells carry them: FY2024 `User Fees` Water `(3.14)`, `Due to/from other funds` Sewer
`(303,552.33)` and Totals `(211,876.24)`, and FY2025 `Due to/Due From` Water `(33,942.00)`.
All four are stored negative, and each one is load-bearing in a footing that would fail by
twice its size if the sign were dropped.

## FY2024's memorandum column is $102,000.00 out, on two offsetting lines

**What the data shows.** On printed pages 21 and 28 alike:

    Reserved for expenditures       Sewer  400,000.00    Totals (Memorandum Only)   502,000.00
    Unreserved retained earnings    Sewer 1,813,817.53
                                    Water    51,333.93
                              Solid Waste   181,853.82
                               PEG Access 1,028,836.87   Totals (Memorandum Only) 2,973,842.15

The four fund columns add to `400,000.00` on the first line and `3,075,842.15` on the
second. The memorandum column is **$102,000.00 too high** on the first and **$102,000.00
too low** on the second. The errors cancel exactly, which is why `Total Fund Equity`
(3,483,633.65), `Total Assets`, the identity and the printed `PROOF` row all still tie in
every column — a textbook pair of **compensating errors**, invisible to every check that
looks only at totals.

**What it does not show.** Which of the two presentations is right, or what the $102,000.00
is. A reservation of $102,000.00 sitting in a fund column that prints blank, a memorandum
column keyed to a different worksheet row, and a reclassification made only in the total
column all fit this signature equally well, and nothing on the page distinguishes them.
Both printings carry it identically, so it is not a page-specific misprint — but that only
rules out the layout, not the source.

**What would settle it:** the Town Accountant's FY2024 trial balance for the enterprise
funds. The annual report does not contain one.

It is pinned to the exact amount in `PRINTED_DEFECTS` in
`verify_enterprise_balance_sheet.py`. If it changes by a penny the check fails again — a new
discrepancy hiding inside an old allowance is exactly what an exception list exists to
prevent. Nothing is adjusted to make it tie.

## The line list changes between the two years, and the sheet does not say why

FY2025 is not FY2024's form with different numbers. Three differences:

- FY2024's liability section leads with `Warrants payable` (`123,306.83` memorandum) and
  prints `Accounts payable` as `0.00`. FY2025 reverses it: `Accounts Payable` carries
  `232,738.60` and `Warrants Payable` prints `-`.
- FY2025 adds `Other Receivables` (`60,513.74`, Sewer) on both the asset and the deferred
  revenue side; FY2024 prints that line as `0.00`.
- FY2024's `Reserved for expenditures` (`400,000.00`, Sewer) has no FY2025 counterpart;
  FY2025 prints `-`.

*What is not established:* whether any of these is a real change in the funds' position or
a change in how the accountant filled the same form. A line moving from one row to an
adjacent row of the same worksheet and a balance genuinely arriving or leaving look
identical here, and rule 7 applies: two budget lines moving in opposite directions is a
measurement, not a story about what happened.

## Provenance

| | FY2024 | FY2025 |
|---|---|---|
| publisher's document | FY 2024 Annual Town Report | FY 2025 Annual Town Report |
| publisher's address | https://www.lunenburgma.gov/DocumentCenter/View/4132 (also ArchiveCenter/ViewFile/Item/211) | https://www.lunenburgma.gov/DocumentCenter/View/4130 (also ArchiveCenter/ViewFile/Item/213) |
| our copy | `sources/town-annual-reports/docs/4132-fy-2024-annual-town-report.pdf` | `sources/town-annual-reports/docs/4130-fy-2025-annual-town-report.pdf` |
| sha256 | `46f14ff8459ec81fb3f21dcda473709c1d03af423abbf7c7633f7d5005f2907a` | `a9ee7b51154d94fd5551f934ce629a2929cc4e5efd8c48cd4bdb8224b8907158` |
| bytes | 52,210,075 | 7,237,129 |
| printed heading | `TOWN OF LUNENBURG / Combining Balance Sheet - Enterprise Funds / as of  June 30, 2024 / (Unaudited)` | `TOWN OF LUNENBURG / Combining Balance Sheet - Enterprise Funds / as of June 30, 2025 / (unaudited)` |
| pages | printed 21 and 28 = pdf 21 and 28 | printed 21 = pdf 25 |

The publisher's own filenames are the DocumentCenter item numbers `4132` and `4130`; those
are the names to ask the Town for if the links die.

## How a year is added

    # render it; CHECK THE NUMBER PRINTED AT THE FOOT against what you asked for
    swift scripts/render_report_page.swift <report.pdf> /private/tmp/<scratch> <page> --scale 6

    # transcribe into two staged CSVs of the same shape as the real ones, then
    python3 scripts/append_enterprise_balance_sheet_year.py --rows staged-rows.csv \
                                                            --totals staged-totals.csv

Scratch directories go under `/private/tmp`, never in the repository.

## What this dataset is not

- It is **unaudited** — both sheets say so on their own face — and the annual report
  contains no notes.
- A fund balance is not a measure of what anything cost, of what any service consumed, or
  of what a rate should be. Rule 11 in its general form: this is a stock, and every rate
  question is about a flow.
- `Unreserved retained earnings` is **not** an enterprise equivalent of free cash. Free cash
  is certified by the Division of Local Services from a different submission; nothing here
  is certified by anybody.
- It says nothing about the schools. It is here because it is the only balance sheet FY2024
  and FY2025 publish, not because it bears on the school budget.
