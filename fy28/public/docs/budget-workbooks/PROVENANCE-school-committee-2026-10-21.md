# The School Committee packet for 21 October 2026 — downloaded 18 November 2026

Covers everything under `budget-workbooks/school-committee-2026-10-21/`, and six Policy
Sub-Committee minutes filed under `meetings/school-advisory-councils-committees/` as
`rr2026-11-18`. What became of every file is in
`sources/data/sc-packet-2026-10-21-delivery.csv`, written by `scripts/ingest_sc_packet.py`;
`--check` re-proves it. The decision on each held file is in `sources/data/redactions.csv`,
keyed by its sha256.

## How it reached us

**A Google Drive folder named `10-21-26 SC Meeting`, shared with TJ Loughlin and downloaded by
him as one archive.** Who shared it is not recorded here (`notes/process/DATA-PRIVACY.md`:
say how a document arrived, not who passed it on).

| | |
|---|---|
| file | `10-21-26 SC Meeting-20261118T195513Z-1-001.zip` |
| bytes | 186,136,919 |
| sha256 | `5e12590bbe3b4035dfc235316dada9de725fc055fcf00201d04025d8c1b42c52` |
| members | 57 files, all in one folder |
| downloaded | 18 November 2026, 19:55 UTC — the timestamp Drive wrote into the archive's name |

The zip is kept unchanged, outside the archive, at
`build/inbox/2026-11-18-sc-packet-2026-10-21/_original.zip`. TJ also had the folder unpacked
in Downloads; its 57 files were compared to the zip's by sha256 and are identical.

Most members are named `Copy of …`, which is what Drive writes when a file is copied into
another folder. The archive key drops it; `delivered_as` keeps the name exactly as delivered,
so nothing rests on that reading.

**Is any of it publicly posted?** Checked on 20 November 2026, by sha256 against the whole
archive manifest:

- **The agenda and the four sets of regular-session minutes are**, on the town's Agenda Center
  (documents 8086, 8002, 8016, 8046, 8058), byte for byte. Nothing new was written for them.
- **Nothing else is.** The district's School Committee documents page, as mirrored here
  (`sources/district-budget/index.csv`, crawled through 19 November 2026), holds no file with
  the same bytes and none with a matching title. Its `Line Item Transfer` is a different form,
  dated 11/18/2026. The page lists only current materials, so an earlier posting that was
  later removed would not show here. The agenda itself links no attachments.

So the address, in rule 12's sense, is this note: a packet share, downloaded by TJ.

## What the packet is

The materials for the meeting of **Wednesday 21 October 2026**
(`sources/meetings/text/school-committee/2026-10-21-agenda-8086.txt`), matching its items:
minutes for approval (6a, 6b), warrants of `10/6/26 to 10/19/26 $455,603.72` (7a), the line
item transfer (7), the homecoming participation question (9b), and the FY28 capital plan
(10b): the school department's capital request forms, the technology list, vendor quotes and
the Superintendent's capital narrative.

## What happened to each file

Every file went through `ingest.stage()`, which runs `redact.gate()`.

**Filed and public.** The capital request forms, the narrative, the technology list, the vendor
quotes, the line item transfer and the homecoming memo. The screen found nothing in them;
two were held by the screen only because a page is a picture, and each was looked at:

- the line item transfer is one scanned page: account lines and staff signatures;
- the clocks-and-bells quote's picture page is a floor plan of speaker coverage.

The homecoming document is the Superintendent's memo recommending that float building be
limited to students enrolled at the high school. **It names no student.**

**The six Policy Sub-Committee minutes** are filed as that board's minutes, under
`meetings/school-advisory-councils-committees/`, by the date each prints. Two print a date the
agenda does not list: item 6b names 9/29/24 and 10/2/24, and the documents print Friday
20 September 2024 and Friday 4 October 2024. They are held and searchable and **not counted as
posted**: posted means on the town's Agenda Center, and these are not
(`PROVENANCE-school-committee-2026-10-27.md` in `sources/meetings/` sets the convention).

**Held private: the twelve warrant batches.** Each is a MUNIS `INVOICE ENTRY PROOF LIST`
followed by the scanned invoices it pays: 307 pages, every one a picture. Batch 6210 is one
payment coded `SPED TUITIONS-PRIVATE`, out-of-district special education tuition, and a
tuition invoice is billed for a named child. That is the case `DATA-PRIVACY.md` masks. The
raw is in the private bucket, `pending` in `redactions.csv`, until every page is read; the
proof-list pages can then be published and any invoice naming a child or family withheld.

**One duplicate.** The playground form arrived twice (`Copy of …` and `Copy of Copy of …`),
same bytes; one copy is kept.

## Where the forms are read

`scripts/extract_capital_submissions.py` reads the forms and the narrative into
`sources/data/capital-submissions-fy28.csv` and `sources/data/capital-narrative-fy28.csv`, and
its `--check` ties the narrative's schedule to the year totals the narrative prints.
