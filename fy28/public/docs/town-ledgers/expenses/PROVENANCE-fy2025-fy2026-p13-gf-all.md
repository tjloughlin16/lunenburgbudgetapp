# Town General Fund at period 13, FY2025 and FY2026, and the parks funds' journal -- the Town's answer to the 5 November request

Covers three PDFs, all held in the PRIVATE bucket as `pending` (CLAUDE.md 13e). None is in
`sources/` yet, and nothing is extracted from them until our review writes `publish` in
`sources/data/redactions.csv`.

| our key | delivered as | sha256 |
|---|---|---|
| `town-ledgers/expenses/glytdbud-expense-fy2026-p13-gf-all.pdf` | `GF2026.pdf` | `f4bb0303980bba712282a3d3fe71e7330cc7f7ef75db10f2053a7e050634c340` |
| `town-ledgers/expenses/glytdbud-expense-fy2025-p13-gf-all.pdf` | `Print_ GF 2025.pdf` | `313b0e2e43d3d5cb89561a54ecc3c89f6b346bb5209ac3473ea18cee3e5b32f6` |
| `town-ledgers/account-details/account-details-fy2023-fy2026-p13-funds-1500-1523-journal.pdf` | `1500_1523.pdf` | `08c9d29bc48e4661d0398520ed09b5d4f6e9131fa4db560343df2a837c0dc204` |

## How it reached us

**The Town's answer to items 1 and 2 of this project's records request of 5 November 2026**
to the Town Manager, *Records request: Parks funds and the year-end reports*
(`notes/reference/records-requests.csv`, id `2026-11-05-town-one-list`; text as drafted:
`notes/outbound/drafts/RECORDS-REQUEST-ONE-LIST-2026-11-05.txt`). Item 3, the Account Trial
Balance for funds 1300-2999, is not among these files.

TJ forwarded the three files from his phone on 17 November 2026. **The message that carried
them from the Town, and the date it arrived, are not recorded here** -- that is a gap, written
down rather than guessed. The reports' own footers date the run (below).

There is no URL: the reports were not published, they were asked for. The request is the
address.

## What each one says about itself

Read off the printed pages (rendered; see the next section for why not the text layer):

- **`GF2026.pdf`** -- MUNIS `glytdbud`, `FOR 2026 13`, fund `0100 GENERAL FUND`, every
  department, columns ORIGINAL APPROP / TRANFRS/ADJSTMTS / REVISED BUDGET / YTD EXPENDED /
  ENC/REQ / AVAILABLE BUDGET / PCT USED. 278 pages. `Report generated: 11/05/2026 14:07`, run
  by the Town Manager. **Its printed title reads `YTD 1500 1523`** -- the name of the parks run
  saved earlier that afternoon, reused; the period line and fund show what it actually is.
  PDF metadata title `Print_ YTD 1500 1523`, author `JenniferWarren`.
- **`Print_ GF 2025.pdf`** -- the same report, `FOR 2025 13`, title `GF 2025`, 278 pages,
  `Report generated: 11/05/2026 14:10`, same user.
- **`1500_1523.pdf`** -- MUNIS `glytdbud` with journal detail, `FOR 2026 13`,
  `JOURNAL DETAIL 2023 0 TO 2026 13`, funds 1500 (Park Revolving, expense and revenue) and
  1523 (Park Gift, expense and revenue). 17 pages. `Report generated: 11/05/2026 13:37`,
  same user. Options page: `Year/Period: 2026/13`, `Suppress zero bal accts: N`.
  It foots to its own `GRAND TOTAL`: revised budget 50,000.00; YTD actual 17,241.41 expense
  less 26,307.45 and 516.00 revenue = -9,582.04, as printed.

The MUNIS login printed on every page is one reason MUNIS PDFs have stayed private here
(see the 6 October rows in `redactions.csv`).

## What did not parse

- **`GF2026.pdf` and `Print_ GF 2025.pdf`: no usable text layer on any page, 278 of 278 in
  each.** They were printed to PDF through a PostScript driver (`PScript5.dll`, Acrobat
  Distiller 17.0) with fonts that carry no character map: pypdf returns glyph ids
  (`/0/1/2 /3/i255...`), pdfplumber returns `(cid:5)`. The pages render cleanly, so they
  need OCR (Textract) before any figure can be read. `scripts/pdf_kind.py` labels both
  `digital: 222 text, 56 text+image` and `digital: 190 text, 88 text+image` -- it counts
  glyph ids as text, which is a defect in the instrument, not a fact about the documents;
  and `pii_screen.py` therefore screened unreadable text and reported nothing.
- **`1500_1523.pdf`** has a clean text layer on all 17 pages and ties to its grand total.
- The Town has sent spreadsheets alongside PDFs before (6 October). None arrived with these;
  an `.xlsx` of the two GF runs would remove the OCR step entirely.
