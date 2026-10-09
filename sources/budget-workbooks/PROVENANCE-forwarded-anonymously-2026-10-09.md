# Nine documents forwarded anonymously — received 9 October 2026

Covers everything under `budget-workbooks/forwarded-anonymously-2026-10-09/`. The decision on
each file, and why, is in `sources/data/redactions.csv`, keyed by its sha256.

## How it reached us

**Sent to TJ Loughlin anonymously, on 9 October 2026.** The sender described the files as the
response to a public records (FOIA) request made by somebody else. That is the whole of the
route as far as anything here records:

- **who made the request is not known;**
- **to whom it was made is not known;**
- **on what date it was made, or answered, is not known;**
- **whether this is the complete response is not known.**

None of that is inferred or filled in below. There is no URL and no requester to cite. The
address, in rule 12's sense, is this note: a third party's records-request response,
forwarded to us anonymously. What would settle it is the request and the response letter
themselves, from whoever made it, or the district's own record of the request.

| | |
|---|---|
| file | `documents.zip`, as received |
| bytes | 5,516,322 |
| sha256 | `2ce1028d4db5965a853d66ea6686412ea02f498a3db50ed64e753d6eefe5c82e` |
| members | 9 files |

The zip is kept unchanged, outside the archive, at
`build/inbox/2026-10-09-anonymous-records-request/_original-documents.zip`.

**Why this folder.** `budget-workbooks/` is the archive's home for documents *sent to us*
rather than mirrored from a publisher, and it already holds one records-request response
passed on by somebody other than the requester (the Finance Committee's files include a
School Department FOIA response the committee held). This delivery is filed beside it, in a
folder named for how it arrived, not for what it is about.

**Filenames.** `delivered_as` in the catalogue and the register is each file's name exactly
as delivered. Four carry a trailing ` (1)`, ` (2)` or ` (4)`, which reads like a browser's
duplicate-download suffix; the archive key drops it. That reading is ours, and the delivered
name is kept so nothing rests on it.

## What the documents say they are

Read from the documents themselves, not from the sender's description. Most are addressed
to the Lunenburg School Committee, and their subjects match items on the Committee's
**revised agenda for 7 October 2026**
(`sources/meetings/text/school-committee/2026-10-07-agenda-8058.txt`): line item transfers
(item 7), removal of surplus material (9b), the Brooks House redevelopment proposal (9e), the
special education reserve fund (9h) and the revised paraprofessional salary schedule (10a).
The two Fair Share earmark memos are dated 7 October 2026 and addressed to the Committee,
but no item on that agenda names them. **That these were the packet for that meeting is
consistent with the documents and is not established by them.**

The salary scale's own file metadata records a last save on 8 October 2026, the day after
the meeting -- which fits the word `Corrected` in its name and is not otherwise checked.

## What happened to each file

Every file went through `ingest.stage()`, which runs `redact.gate()`, and then was read in
full by eye: every page rendered, every cell, every embedded image, the Word file's
metadata, tracked changes and hidden text. Decided by Claude on 9 October 2026, for TJ's
review.

| delivered as | pdf_kind | the gate | decision |
|---|---|---|---|
| Advisory on Special Education Stabilization Fund - Circuit Breaker - School Finance.pdf | digital: 1 text | passed the screen | publish |
| Brooks House Memo 10-7-26.docx | (Word) | passed the screen | publish |
| Brooks House redevelopment summary.pdf | digital: 3 text+image | passed the screen | publish |
| Corrected Lunenburg_Paraprofessional_Salary_Scale FY27-FY28 (1).xlsx | (Excel) | passed the screen | publish |
| Enrollment Summary.pdf | digital: 1 text, 1 text+image | passed the screen | **withhold** |
| ExcessMaterialsOctober7 (2).pdf | digital: 2 text | passed the screen | publish |
| FC1192_Fair_Share_Special_Support_Memo (1).pdf | digital: 2 text | passed the screen | publish |
| Fair_Share_Earmarks_Memo (4).pdf | digital: 1 text | passed the screen | publish |
| Line Item Transfers 10-7-26.pdf | scan: 3 image | **held**: unscreenable (a scan) | publish, after reading every page by eye |

**Withheld: the enrollment summary.** A student information system printout of students by
grade, race and sex. Nobody is named, but some cells count a single student, and a small-cell
disclosure cannot be recalled from a bucket that keeps everything for ten years. Its raw is in
the private bucket only, and it is not in `sources/`. It waits for TJ's decision: publish as
it is, publish a copy with the small cells suppressed, or keep it withheld.

**Passed by the screen is not cleared by the screen.** Eight of the nine passed
`pii_screen.py`, which finds per-person tables and identifier patterns and cannot recognise a
name in prose. The clearance is the reading, recorded in `decided_by`.

## What kind of evidence this is (rule 13a)

- **The line item transfers are district forms, signed** by the Superintendent and the
  temporary business administrator: account numbers, original budgets, transfers and revised
  budgets. They are the district's own requests, not a ledger printout; the ledger behind
  them is MUNIS.
- **The salary scale is a workbook somebody built.** Its own last line says the figures are
  transcribed from a source schedule, a PDF that is not in this delivery. A figure from it is
  `stated` until checked against that schedule or the contract.
- **The memos and the Brooks House summary are people's arguments**, useful for what was
  proposed and asked, and carrying the authority of their authors.
- **The advisory is a printout of a state guidance web page**, last updated by the state in
  November 2020. The state's own copy is the one to cite where it can be found.
