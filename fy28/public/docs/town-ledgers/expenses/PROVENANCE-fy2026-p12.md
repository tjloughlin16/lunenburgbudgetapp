# FY26 year-to-date budget report, period 12 — obtained 2 September 2026

Rule 12 asks for three things at the same time as the document: where it came from, the
publisher's own filename, and our processed copy, with a sha256 on all of it. All three
are here, written when the files arrived rather than retrofitted.

## Where it came from

**Sent by email on 2 September 2026 by Jennifer Warren, Town Manager**, forwarding a
message she had sent the same morning to the Finance Committee, copied to the Town
Accountant, the Assistant Town Accountant, the Chair of the School Committee and the
Superintendent. The report itself was produced the previous evening by **Karen Barrett,
Town Accountant**, whose name appears on the report's own footer.

There is no URL. These documents were not published; they were asked for and sent. The
email is the address.

The Town Manager's covering words, quoted because they bear on how the figures should be
read:

> "This is the current FY26 report- figures likely to continue to adjust as we continue
> the year-end reconciliation process."

And in the message to the Finance Committee:

> "Attached are the current YTD FY26 balances. These figures are likely to continue to
> adjust as we continue the year-end reconciliation process."

**Both officials are named because both were acting in a town role.** That is the same
test applied to the Finance Committee member who supplied the FY27 workbook, and the same
reason the resident who filed the June 2026 records request is not named.

## What arrived, under which name

| our copy | the sender's filename | sha256 |
|---|---|---|
| `town-general-fund-expenditures-fy26-p12.pdf` | `Print_ YEAR-TO-DATE BUDGET REPORT.pdf` | `22de705da725f5005ccd65b20a5023d9043ac02f99e3bad2d55d4a31c41b1c9c` |
| `town-general-fund-expenditures-fy26-p12.xlsx` | `FY26 BUDGET YEAR TO DATE REPORT (9-1-2026).xlsx` | `215dd64f597f1f2d8a373080756a188c0fecfd7caff9158824ec7d293e287cd1` |
| `town-general-fund-expenditures-fy26-p12.txt` | *(ours — text extracted from the PDF)* | `3996d309e22de235188cac1dc11cf2570d37eb68c0df493d73902e37795750a6` |

Files are byte-identical to what was sent; only the names differ, and the sender's names
are above so the same documents can be asked for by the name the town uses.

## What each one is, checked by opening it

**The PDF** is the MUNIS `glytdbud` report as it prints, 28 pages, and it is the only one
of the two that states its own parameters. From its options page, verbatim:

    Print totals only: N                          Year/Period: 2026/12
    Suppress zero bal accts: Y
    Account type       Expense
    Report generated: 09/01/2026 18:56   User: kbarrett   Program ID: glytdbud

**The Excel** is the same report as data: one sheet, `ACCOUNT DETAIL`, 709 rows, columns
`FUND / DEPARTMENT / ORG / OBJ / ACCOUNT / ACCOUNT DESCRIPTION / TYPE / ROLLUP /
SUB-ROLLUP / ORIGINAL APPROP / TRANFRS/ADJSMTS / REVISED BUDGET / YTD EXPENDED /
ENCUMBRANCES`.

**The Excel does not state its own period, and this matters.** Nothing inside it says
`2026/12`; that is only on the PDF. The two are asserted to be the same report by
reconciling the Excel's 635 account rows against the PDF's own printed GRAND TOTAL:

| | Excel, summed | PDF GRAND TOTAL |
|---|---:|---:|
| Original appropriation | 51,189,965.10 | 51,189,965 |
| Transfers / adjustments | 2,826,046.42 | 2,826,046 |
| Revised budget | 54,016,011.52 | 54,016,012 |
| YTD expended | **52,163,984.85** | **52,163,984.85** |
| Encumbrances | **529,325.69** | **529,325.69** |

The two cent-bearing columns agree exactly. The three appropriation columns differ by
under a dollar because **the PDF rounds them and the Excel does not** — which also settles
something this project had only been able to back-solve: the rounding is in the printing,
not in the ledger.

## Three things to hold onto before quoting any figure from this

**1. It is period 12, not period 13.** Period 12 is June. Period 13 is the year-end close,
after purchase orders are closed in the lapse period. The Town Manager says as much in
her covering note. **So this is not the final close and the unspent figure will move** —
in FY25, closing purchase orders moved the school figure by $21,770.53 between two School
Committee meetings a fortnight apart.

**2. `Suppress zero bal accts: Y`.** Accounts with a zero balance are omitted. An account
absent from this report is not necessarily absent from the ledger, and nothing should
reason from what is *not* here.

**3. It is expenditures only.** `Account type Expense`. The revenue side of FY26 at this
period is a separate run and is not held.

## What it makes possible that was not possible before

This is the **first account-level general fund expenditure report in the archive**. Every
prior one was run with `Print totals only: Y`, which renders the entire school district as
a single row, `300 SCHOOL DEPARTMENT`.

Here the school department is **258 accounts**, each with an org code, an object code and
a description — `SUPT SALAR`, `SPED PRIVA`, `CLASS ADS`, `TRANSPORTA`. That is the first
material this project has ever held for building the crosswalk between the district's
named budget lines and the town's coded ledger accounts, which `notes/SCHEMA.md` describes
as the single biggest limit on what can be answered.

**It does not build that crosswalk by itself.** Matching `CLASS ADS` to "Classified Ads"
is a judgement, and a plausible name match is exactly the derived-quoted-as-observed error
rule 13 exists to prevent. Every mapping has to be established and recorded with its
evidence, one at a time.
