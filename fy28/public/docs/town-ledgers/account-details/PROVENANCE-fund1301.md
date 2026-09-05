# Records request, 17 June 2026 — athletics financial detail

Rule 12 asks for three things at the same time as the document itself: where it came from,
the publisher's own filename, and our processed copy, with a sha256 on all of it. This file
carries all three for the five documents in this directory, written when they arrived rather
than retrofitted.

## Where it came from

**Obtained from the Town of Lunenburg** in response to a public records request under
M.G.L. c. 66 § 10, made on **17 June 2026** by a resident. The Town's response was forwarded
to this project by email. There is no URL: these documents were not published, and asking for
them is the only route to them.

**The requester is deliberately not named here.** Rule 12 asks for an address a reader can
use to get back to the document, and for a records request that is the request and its date —
both of which are above. The name of a private resident who asked the town a question is not
part of that address, and it is not ours to publish. Anyone wanting these files can ask the
Town for them by the filenames in the table below.

The request form is reproduced from the town's fillable PDF. The field `Materials Sought`
reads, verbatim:

> FY 24, FY25 and FY 26 Financial data records and number of participants for Lunenburg
> athletics. All sports, all levels. Records to include expenses including but not limited
> to, coaching stipends, insurance, Athletic director salaries, transportation costs,
> uniforms, officials. Revenue including but not limited to- user fees, gate sales.
>
> I am looking for a series of spreadsheets and general ledger entries.

**The request form itself is neither published nor kept.** It carries the requester's home
address, telephone number and personal email in form fields. None of that is needed to check
any figure, and holding it is not something a public-interest archive should do to a private
resident who asked the town a question. Our copy has been deleted. Its sha256 was
`449d5cdb450a69570fad394f4cddb72901dbae1fa24b5c9c7b98af4a9bd00be5`, recorded so that a copy
obtained from the Town can still be checked against the one this analysis was written from.
The wording of the request survives in the quotation above, which is the part that bears on
what the Town was asked for. This is a decision, not an oversight.

## What arrived, under which name

| our copy | the town's filename | sha256 |
|---|---|---|
| `fund-1301-journal-detail-fy24.xlsx` | `FY24 Account_Detail_.xlsx` | `9bbf76db320bf83148870005e7208b990dddaeb5e04433e9196d62c38d8230bd` |
| `fund-1301-journal-detail-fy25.xlsx` | `FY25 Account_Detail.xlsx` | `3ebf3472134182f2f52953323f47330a59f130ad24842b677a9db4666a53691f` |
| `fund-1301-journal-detail-fy26.xlsx` | `FY26 Account_Detail.xlsx` | `fc76a981f0857c6670ad19b3199a0ad1f5d5d724d58a1817adb0f6ba04b7a69a` |
| `athletics-by-sport-fy24-fy26.xlsx` | `Copy of Athletics 24.25 (1).xlsx` | `9c669e9f34a4c5c0807b018a51292b1b2248c2c388652012f8b673487415069b` |
| `athletic-fee-counts-2025-2026.docx` | `ATHLETIC FEES 2025.docx` | `82042df3785b4c0406649a54bee77cb9aaa7514c2cbad58aaf4fd57e40bbf1eb` |

Files are byte-identical to what the town sent; only the names differ, and the town's names
are above so a resident can ask for them by the name the town uses.

## What each one actually is

Rule 13: what the file is called is not what the file contains, and both were checked by
opening it.

**The three `Account_Detail` workbooks are not what their names suggest.** Each holds one
sheet, `Journal Detail Export`, and every row in all three is the same single account:

    D2 = '1301-0-000-0000-00-0-00-0-104000'    ORG 1301 · OBJECT 104000 · DESCRIPTION 'CASH'

So this is **the cashbook of fund 1301** — the Chapter 658 athletics revolving fund — and not
the expense-object detail the request asked for. There is no object `535016`, no transportation
object, no vendor name on any disbursement row: column `X` (`VDR NAME/ITEM DESC`) is populated
on receipts and empty on every payment. What the files do carry, and nothing else in the
archive does, is a **date on every movement of money** and an opening balance the town itself
prints (`SRC='SOY'`, `REFERENCE='SOY BAL'`).

Each year's file is a full twelve periods. Effective dates run 2023-07-06 to 2024-06-30,
2024-07-03 to 2025-06-30, and 2025-07-07 to **2026-06-12** — so FY26 is complete to within
eighteen days of year-end and the FY26 figures here are not a full year.

No rows are hidden and no columns are hidden in any of the three.

**`athletics-by-sport-fy24-fy26.xlsx`** — despite the `24.25` in the town's filename, every
sheet carries **three** school years, 23/24, 24/25 and 25/26, side by side. Sheets `Fall`,
`Winter`, `Spring` hold one row per sport with participation counts by fee category and cost
lines (officials, assignor, police/EMS, coaches, transportation, equipment reconditioning,
dues and fees, uniforms, equipment, misc). `Summary` is a partial roll-up whose blocks are
labelled with mixed years (`A3='Fall - 24/25'`, `A17='Winter  - 23/24'`, `G3='Spring 23/24'`)
and should not be read as a single year. `Sheet3` is empty.

The three season sheets **do not share a column layout** — `Official` begins at `AF` on Fall
and at `AG` on Winter and Spring, and everything to the right of it is shifted by one column.
`scripts/extract_athletics_by_sport.py` therefore builds its column map from rows 1 and 2 of
each sheet rather than assuming positions.

**`athletic-fee-counts-2025-2026.docx`** is one page, titled `ATHLETIC FEES 2025-2026`, giving
participation counts by fee category for each season. It is the only document we hold that
gives fee-category counts for 2025-26 — those columns are present but empty in the workbook.

## Our processed copies

Everything computed from these is re-derivable by script:

| file | produced by |
|---|---|
| `sources/data/fund-1301-cash-journal.csv` | `scripts/extract_fund1301_ledger.py` |
| `sources/data/athletics-by-sport.csv` | `scripts/extract_athletics_by_sport.py` |
| `sources/data/athletics-by-sport-reconciliation.csv` | `scripts/extract_athletics_by_sport.py` |

Both extractors reconcile to a total the source itself prints, and both say plainly which
columns in them are ours rather than the town's — the running balance in the first, the
row-level sums in the second. `scripts/verify_records_request_2026_06.py` recomputes every
figure quoted in `sources/analyses/athletics-ledger.md` from these files.
