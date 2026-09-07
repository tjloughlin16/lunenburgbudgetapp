# PEG Access, read from the page

**What this is.** The PEG Access / Public Access Cable **revenue-versus-expenses statement**
and the **line-item expense table** beside it, from every annual town report that prints
them — FY2015 through FY2025, eleven editions — transcribed by **reading the rendered page
directly** rather than by OCR.

    sources/data/peg-access.csv                 every printed expense line
    sources/data/peg-access-printed-totals.csv  every row the statement prints, quoted
    sources/data/peg-access-identities.csv      the arithmetic each statement states
                                                about itself
    scripts/verify_peg_access.py                recomputes all of it
    scripts/append_peg_access_year.py           adds a year, and REFUSES one that
                                                does not tie

## This is CABLE FRANCHISE money, and that is the first thing to say about it

Rule 11. Comcast pays the Town a franchise fee under its cable licence; that fee, plus the
interest it earns, is the whole of this money. **It is paid by cable subscribers, not by
taxpayers, and it is not available to the town's general operations.** From FY2020 it sits
in a statutory enterprise fund and is appropriated by its own Town Meeting article,
separately from the omnibus budget. A sentence putting a PEG balance next to a school
budget gap compares two things that cannot be spent on each other.

The one place it touches the general fund is the expense line the reports call **`Indirect
Costs`** from FY2021 on — money moving *out* of PEG *to* the town, and Town Meeting votes
the amount by name. The FY2023 report's warrant carries `$47,503.00 from PEG Access and
Cable Related Enterprise Fund` and that is exactly the `Indirect Costs` line in the FY2024
expense table; the FY2024 report's carries `transfer $27,929.97 from the PEG Access and
Cable Related Enterprise` and that is exactly FY2025's. Two documents, two years, to the
cent.

## The series is renamed four times. That is not what happened

| edition | how the report heads it |
|---|---|
| FY2015–FY2020 | Public Access Cable |
| FY2021–FY2022 | PEG Access Enterprise Fund |
| FY2023 | PEG access (Public Access Cable) |
| FY2025 | Public Access Cable |

Rule 6 warns that lines which vanish and reappear renamed produce findings that are
artefacts. Here the renaming is real and it is **not the event**. The event is in the
FY2019 annual report's Annual Town Meeting warrant, quoted verbatim:

> **ARTICLE 16.** To see if the Town will vote to establish, under Chapter 44, §53F ½, a
> Public Educational Government (PEG) Access Enterprise Fund, and transfer in to such fund
> all funds remaining in the Public Educational Government (PEG) Access and Cable Related
> Receipts Reserved For Appropriation Fund and the Comcast Tech Capital Grant Fund as of
> June 30, 2019; or take any other action relative thereto. (Submitted by Public Access
> Committee) (Board of Selectmen and Finance Committee recommend approval) **VOTED
> UNANIMOUSLY**

`sources/town-annual-reports/text/4126-fy-2019-annual-town-report.txt`, lines 8591–8595.

So: **one continuous body of money, two different funds, and the headings track neither.**
Through FY2019 it was a receipts-reserved-for-appropriation fund *plus* a separate Comcast
Tech Capital Grant Fund — which is why FY2019's statement is the only one with a
`Comcast Tech Fund (Undesignated Fund)` row, added in the year the two were merged. From
FY2020 it is one enterprise fund. The report went on calling it *Public Access Cable* for
another year and reverted to that heading in FY2025, six years after the fund it names
ceased to exist.

*What this does NOT establish:* the amounts transferred under Article 16. The warrant names
no figure and no later report reconciles the old fund's closing balance to the new fund's
opening one. That is registered as a gap.

## `Starting Balance` does not mean the same thing twice, and nothing on the page says so

This is the trap in the dataset and it is worth more than any figure in it.

| edition | what the opening row is |
|---|---|
| FY2015–FY2017, FY2019 | the previous edition's own `Ending Balance`, matching it **to the cent** |
| FY2018 | $303,551.54 against FY2017's $303,909.77 — $358.23 apart, with no fund change to explain it |
| FY2020 | $447,813.36 — not FY2019's $573,837.37, and unexplained |
| FY2021 | **$272,000.00, which the same page's prose calls "the budget starting balance"** |
| FY2022 | there is none; `TOTAL` is that year's revenue less that year's expenses |
| FY2023, FY2024 | there is none; `Balance` is that year's revenue less expenses |
| FY2025 | **$208,772 — again the budget**, and `Ending Balance` is that less expenses |

Rule 1 in its purest form: FY2021 and FY2025 put an **appropriation** where four earlier
editions put an **actual balance**, in a row with the same label, and the arithmetic below
it is unchanged. A chart of "PEG fund balance, FY2015–FY2025" drawn from this column would
show a collapse from $582,941.93 to $272,000.00 in FY2021 that is a change of definition
and not a change of money.

`verify_peg_access.py` therefore **reports** year-to-year continuity and does not fail on
it — a failure there would be a failure to read the page rather than a failure of the page.
What it fails on is arithmetic each page states about itself.

## What makes a reading trustworthy here: seven checks

1. **Line-item footing.** The expense lines must sum to the TOTAL the report prints for
   them, to the cent. Independent because the town printed the total.
2. **Percent footing.** From FY2020 the table prints a `% of Expense` column and a printed
   `100.00%`; the column must add to it, within the rounding of ten or eleven two-decimal
   figures.
3. **Every printed percent, recomputed** from its own amount over the printed total.
4. **The identities the statement states about itself** — recorded in
   `peg-access-identities.csv` over the printed row **ordinals**, not the labels, because
   the arithmetic differs every few years and two rows of FY2019's statement carry the
   identical printed label `Subtotal`.
5. **Every printed row is reached by an identity.** A row no arithmetic on the page touches
   is a finding; FY2020 has one and it is pinned below.
6. **The two pages of the same report agree on total expenses.** The line-item TOTAL and
   the statement's `Expenses` row are printed on different pages in eight of the eleven
   editions, from the same workbook — a genuinely independent cross-check.
7. **What the prose says the figure was.** Four editions restate a revenue figure in a
   sentence, and it must equal what the table prints.

**Sign convention.** Nothing in any of these eleven statements is printed in parentheses or
with a minus sign; every figure is positive, FY2022's `TOTAL` included, which is a surplus.
Check 8 asserts that the parenthesisation of each raw `quote` matches the sign of the
amount stored beside it, **in both directions**, so the first negative to appear cannot be
stored positive — a missed parenthesis has already cost this repository $315,772 elsewhere.

Each check was shown to have power to fail before the dataset was believed, by staging a
corrupted FY2025 through the append gate:

| what was broken | what caught it | what was written |
|---|---|---|
| `Equip/Maint` 7,156.03 → 7,174.03 | line-item footing (+18.00) | nothing |
| `Ending Balance` 30,632 → 30,633 | the identity `6 − 5 = 7` (−1.00) | nothing |
| the identity `6 − 5 = 7` deleted | three printed rows reached by no arithmetic | nothing |
| `Videographers` percent 21.06 → 22.06 | percent footing (+1.01) and the per-line recomputation | nothing |
| `Lease` 6,000.00 stored as −6,000.00 | footing, the percent, **and the sign check naming the cell** | nothing |

**A year that does not tie is not written down here.** `append_peg_access_year.py` merges
into copies, runs the verifier against the copies, and replaces the real files only if every
check passes — because "append, then verify" leaves an unreconciled row in a file somebody
can query while the complaint scrolls past.

## Five printed defects, pinned and not adjusted away

Every one is the town's own report disagreeing with itself. Each is recorded in
`PRINTED_DEFECTS` in the verifier with the amount pinned exactly, so a discrepancy that
changes by a penny fails again.

**FY2017 — the expense lines add to $450.01 more than the printed TOTAL.** The ten lines on
printed page 68 add to `74,665.74`; the printed `TOTAL` is `$74,215.73`. $450.00 of the
difference is the last line, `Vendor Expenses $450.00`: the pie on printed page 69 labels
the other **nine** lines and not that one, and those nine percentages add to exactly 100.00
— so the total and the chart exclude the same line. The remaining **one cent** is not
explained by that; the nine included lines add to `74,215.74`.
*What is not established:* whether Vendor Expenses was paid and left out of the total or
never paid and left in the table, and where the cent went. Both the statement on page 69 and
the FY2018 report use `74,215.73`, so the printed total is what the rest of the record rests
on. *Closes it:* the Town Accountant's FY2017 year-end detail for the fund.

**FY2017 — the two pages disagree about the revenue by $40.00.** Printed page 68:
*"The overall payments received for FY17 were $107,849.80."* Printed page 69, and the table
on it: `$107,889.80`. The table's figure is the one the statement foots to
(270,235.70 + 107,889.80 = 378,125.50, as printed), so the prose is the odd one out — and
nothing on either page says so.

**FY2020 — the two tables on one page disagree by 32 cents.** `FY20 Line Item Expenses by
Percentage` foots to `Total $116,933.22`; `FY20 REVENUE vs EXPENSES` prints
`Expenses $116,933.54`. Each foots to its own printed total exactly, so each is internally
right and they disagree with each other.
*What is not established:* which figure is the year's expenses.

**FY2020 — a printed row no arithmetic reaches.** The statement prints a row labelled
`Subtotal` at `449,041.36` between Expenses and Total, and the page's own arithmetic runs
past it: 699,875.47 − 116,933.54 = 582,941.93, which is the `Total` printed below.
`449,041.36` is the figure FY2019's statement prints **in the same position**, one edition
earlier.
*What is not established:* whether the row survived from the prior year's workbook or means
something the page does not say. It is recorded and not removed.

**FY2024 — the two pages disagree by $1.16.** The statement on printed page 63 prints
`Expenses $174,150`; the line-item table on printed page 64 foots to `Total $174,151.16`.
That statement is printed in whole dollars throughout, and rounding or truncating
174,151.16 gives 174,151 — so this is not a display rounding. FY2025, printed the same way,
is 97 cents apart and *is* consistent with truncation, which is why the whole-dollar
tolerance is $1.00 and FY2024 exceeds it.

## FY2024 was UNCATALOGUED, not absent

`annual_report_catalogue` holds no PEG entry of any kind for FY2024, which reads exactly
like a report that does not print the statement. It does print it. **FY24 REVENUE vs
EXPENSES is on printed page 63** (pdf 63) and **FY24 LINE ITEMS AS A PERCENTAGE on printed
page 64** (pdf 64), and both reconcile on every check. The FY2024 report's own contents page
even says so: *"Lunenburg Public Access Pages 60-65"*.

Two smaller catalogue gaps were found the same way and are also now read:

- **FY2023's revenue-versus-expenses statement**, printed page 79 (pdf 79). The catalogue
  records only the line-item table on page 80 and the task that produced this dataset was
  told there was no statement for FY2023. There is.
- **FY2019's pages.** The catalogue gives 82 and 83, which are the PDF indices; the pages
  print **80** and **81** at their feet.

The reason all three hid is the same: the tables are **images with no text layer**, so the
extracted text for those pages is blank and a search of the text finds the Financials
paragraph and then nothing. Rule 13 — an instrument that reformats before you see it is part
of the finding.

## Page numbers: the catalogue holds the PDF index, not the printed page

Read off the foot of each rendered page, never from an inferred offset.

| edition | statement (printed / pdf) | line items (printed / pdf) |
|---|---|---|
| FY2015 | 66 / 66 | 65 / 65 |
| FY2016 | 74 / 74 | 73 / 73 |
| FY2017 | 69 / 69 | 68 / 68 |
| FY2018 | 83 / 83 | 82 / 82 |
| FY2019 | **81 / 83** | **80 / 82** |
| FY2020 | 75 / 75 | 75 / 75 |
| FY2021 | **72 / 73** | **72 / 73** |
| FY2022 | 72 / 72 | 72 / 72 |
| FY2023 | 79 / 79 | 80 / 80 |
| FY2024 | **63 / 63** | **64 / 64** |
| FY2025 | **60 / 64** | **60–61 / 64–65** |

Both numbers are in the CSVs, `page_printed` and `page_pdf`, so neither has to be
re-derived.

**Two instrument cautions, both hit while reading these pages.**
`scripts/render_report_page.swift` infers the printed-to-PDF offset from the document and is
wrong on some reports — for FY2025 the true offset is +4. And **a rotated page is silently
cropped by a renderer that sizes its canvas from the unrotated box**:
`scripts/render_page.swift` did exactly that to FY2019, whose pages carry `/Rotate 270`, and
the result looked like a valid page of the report with its first line sliced off. Nothing
about it said *cropped*. The FY2019 figures here were re-read from a render sized off the
**rotated** box.

## The FY2025 comparison against the enterprise balance sheet does not reconcile

`enterprise_balance_sheet` now holds a `peg_access` column for FY2024 and FY2025, so there
is one year where a flow statement and a stock statement in the same book can be compared.
They do not agree, and this is reported rather than smoothed.

| | |
|---|---:|
| PEG Access Total Fund Equity, 30 June 2024 | 1,028,836.87 |
| PEG Access Total Fund Equity, 30 June 2025 | 1,072,661.74 |
| **the change** | **+43,824.87** |
| FY25 statement: revenue subtotal | 262,565 |
| FY25 statement: expenses | 178,140 |
| **revenue less expenses** | **+84,425** |
| difference | 40,600.13 |

And the FY2025 report prints a **third** figure for the same fund on the same date: the
Treasurer's Cash schedule carries `Bartholomew- PEG Access Enterprise Fund 782,591.31$`. A
fourth, if the statement's own `Ending Balance $30,632` is counted — but that one is
explicitly the budget less expenses, so it is spending authority rather than money.

*What the data shows:* four figures, one fund, one date, no line drawn between any pair.
*What it does not show:* which quantity each is. A budget balance, a bank balance, a fund
equity and a year's surplus are four different things and the report labels none of them as
such. Note also that the balance sheet is dated 30 June and the statement covers the year to
30 June, so a timing difference cannot be ruled out either — but a timing difference does
not explain $40,600.
*Closes it:* the Town Accountant's FY2025 statement of revenues, expenditures and changes in
fund balance for the PEG Access and Cable Related Enterprise Fund. Registered in
`money-gaps.csv`.

One thing worth flagging without a conclusion attached: **`Investment Interest` is $35,430
in FY2024 and $35,430 in FY2025** — the identical figure in consecutive years, in a line
that appears in no earlier edition. It could be right. Nothing here tests it, and the
document that would is the same one.

## What the town said about it

Rule 15a. `scripts/search_minutes.py "PEG Access"` over the whole meeting archive returns
**one** document, and it bears directly on the FY2025 ending balance:

> Finance Committee, 23 October 2025 — *"…own vote to transfer the sum of $35,271 from
> retained grants of the PEB Access and Cable related Enterprise Fund to fund the FY26 PEG
> Access and Cable related Enterprise operation and capital budget. Ana Lockwood asks about
> their total budget."*
> `/docs/minutes/text/finance-committee/2025-10-23-minutes-7467.txt`

That is FY26 operations being funded out of retained earnings, in the year after a statement
whose ending balance is $30,632. The minutes do not say the two are related and nothing here
establishes that they are.

`search_minutes.py "PEG" --board select-board` returns nothing across 155 Select Board
documents, and `"Public Access"` returns 535 documents almost all of which are the standard
open-meeting notice saying the meeting is being broadcast on the Public Access channel. The
meeting archive begins in 2025, so it cannot speak to FY2015–FY2024 at all.

## Provenance

Every figure comes from an annual town report published by the Town of Lunenburg. Our copies
are named by the publisher's own DocumentCenter item number, which is the name to ask the
Town for if a link dies.

Every one of the eleven is in `sources/town-annual-reports/index.csv`, one row per
edition, carrying the publisher's own DocumentCenter and ArchiveCenter addresses, the local
path, the byte length and the sha256 — checked by `scripts/check_source_links.py` (does the
publisher's copy still open) and `scripts/verify_source_copies.py` (and if it opens, is it
still the same bytes). The publisher's own filename is the DocumentCenter item number, which
is the prefix of our filename and the name to ask the Town for if a link dies: FY2015 is
`4121`, FY2025 is `4130`, and the numbering is not in fiscal-year order.

`sources/data/archive-manifest.csv` carries the sha256 and byte length of each, and
`sources/town-annual-reports/index.csv` its catalogue entry. Every row of both CSVs names
the document it came from in a `document` column.

## How a year is added

    # render it BY PDF INDEX, sized from the ROTATED box, and CHECK THE NUMBER PRINTED AT
    # THE FOOT against what you asked for
    swift scripts/render_report_page.swift <report.pdf> /private/tmp/<scratch> <page> --scale 6

    # transcribe into three staged CSVs of the same shape as the real ones, then
    python3 scripts/append_peg_access_year.py --rows staged-rows.csv \
                                              --totals staged-totals.csv \
                                              --identities staged-identities.csv

Scratch directories go under `/private/tmp`, never in the repository.

## What this dataset is not

- It is **not audited** and the annual report contains no notes to it. It is a department's
  own report of its own year, laid out in Word.
- **The line list is not stable.** `Insurance` is an expense line through FY2020 and
  disappears after it; `Indirect Costs` appears in FY2021 and never existed before;
  `Videographers` splits out of `Salaries` in FY2021 after one year as `Payroll
  Videographers`; `Legal Fees` exists only in FY2018. A line-by-line series across those
  boundaries compares different things. Rule 6.
- **An expense line is dollars, not people or programmes.** `Videographers $37,512.50` is a
  budget line; it is not a count of videographers, of hours or of shows. Rule 7.
- **It says nothing about the schools.** It is here because it is a whole fund the town
  publishes an eleven-year statement for and nobody had read, not because it bears on the
  school budget. It bears on the school budget only in the sense that rule 11 does: it is
  another route money takes that the general-fund budget does not show.
