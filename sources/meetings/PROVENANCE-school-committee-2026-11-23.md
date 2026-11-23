# School Committee and Policy Sub-Committee minutes, in a Drive folder downloaded 23 November 2026

Eighteen files in a Google Drive folder shared with TJ by the Superintendent's office. TJ
downloaded them as one archive, `drive-download-20261123T201924Z-1-001.zip` (the name carries
the download time, 23 November 2026 20:19 UTC). The folder has three subfolders: `2024 Minutes`,
`2025 Minutes` (with `POLICY` inside it) and `2026 Minutes`.

This is a partial answer to TJ's request of 8 September 2026 for School Committee minutes
(`notes/outbound/REQUEST-school-committee-minutes.md`). The Superintendent's reply of
19 November 2026 says: *"Please find a portion of additional minutes from 2024, 2025, and 2026
in Liz's latest email to you."* The same reply says the district *"is unable to provide a
date by which the remaining minutes will be provided"*
(`correspondence/2026-11-19-records-requests-superintendent.txt`). **When the covering email
was sent is not recorded here.** The date in the file id, `rr2026-11-23`, is the date of the
download.

Minutes are filed and read as their meetings' minutes, and **not counted as posted**: posted
means on the town's Agenda Center. This follows `PROVENANCE-school-committee-2026-10-27.md`.
Every PDF was made in Microsoft Word, author `Liz Petersen`, with a text layer on every page.

`scripts/ingest_sc_minutes_2026_11_23.py` did the filing, and
`sources/data/sc-minutes-2026-11-23-delivery.csv` records what became of each of the 18
files, with its sha256. `--check` re-proves that register against the archive.

## Filed: seven sets of minutes not held before

| meeting, as printed | delivered as | our copy | pages |
|---|---|---|---:|
| School Committee, Wednesday, March 5, 2025 (Budget Hearing) | `03.05.25 Minutes (Autosaved).pdf` | `school-committee/2025-03-05-minutes-rr2026-11-23.pdf`, held by the screen then published, see below | 19 |
| School Committee, Wednesday, April 2, 2025 | `Minutes 04.02.25.pdf` | `school-committee/2025-04-02-minutes-rr2026-11-23.pdf` | 6 |
| School Committee, Wednesday, June 18, 2025 | `6.18.25 Minutes (002).pdf` | `school-committee/2025-06-18-minutes-rr2026-11-23.pdf` | 5 |
| Policy Sub-Committee, Friday, February 21, 2025 | `Copy of MINUTES 7  Policy Meeting  Minutes 2-21-25 (1).pdf` | `school-committee/2025-02-21-minutes-rr2026-11-23.pdf` | 1 |
| Policy Sub-Committee, Friday, March 21, 2025 | `Copy of MINUTES 8  Policy Meeting  Minutes 3-21-25.pdf` | `school-committee/2025-03-21-minutes-rr2026-11-23.pdf` | 1 |
| Policy Sub-Committee, Friday, October 24, 2025 | `Policy Meeting  Minutes 10-24-25.pdf` | `school-committee/2025-10-24-minutes-rr2026-11-23.pdf` | 1 |
| Policy Sub-Committee, Friday, October 31, 2025 | `Policy Meeting  Minutes 10-31-25.pdf` | `school-committee/2025-10-31-minutes-rr2026-11-23.pdf` | 1 |

Each is filed under the date printed in its heading, and every printed date matches the
district's filename. None is marked draft. None says whether it has been approved.

**The Policy Sub-Committee minutes are filed under `school-committee/`**, because that is the
Agenda Center board where the town posted those meetings' agendas (for example
`school-committee/2025-02-21-agenda-7066.pdf`, titled *School Committee Policy
Sub-Committee*). Filed there, each set of minutes joins the register row of its own meeting.
The 2024 Policy minutes from the 18 November packet first went under
`school-advisory-councils-committees/`, while their agendas are under `school-committee/`, so
the register showed each 2024 meeting as two half-rows. **They were refiled on 23 November
2026** to `school-committee/<date>-minutes-rr2026-11-18.pdf`, the same bytes under a new key.
The bucket keeps the old objects, so the six old keys are registered in
`sources/data/archive-orphans.csv` with `superseded_by` naming each new one. The town's Agenda
Center has no Policy Sub-Committee board of its own, so School Committee is where they belong.
`PROVENANCE-school-advisory-councils-committees-2026-11-18.md` still describes where they were
first filed; it is a record of that delivery and is not rewritten.

The PDF creation dates are worth noting, and they are not evidence of when the minutes were
written: a PDF is made whenever somebody exports it. The 5 March 2025 PDF was created on
2025-09-23. The February and March 2025 Policy PDFs were created on 2025-02-18 and
2025-03-18, three days before each meeting, which looks like a notice template filled in
afterwards. The April and June 2025 PDFs were created on 2026-10-19, and the October 2025
Policy PDFs on 2026-10-20 and 2026-10-21.

## Published as delivered: the 5 March 2025 budget hearing

In the public comment, two speakers, each named with a home address, describe a disability:
one their own diagnosis, the other a sibling's special education support. The ingest screen
held the file (`redact.gate()`: a medical term), and it was first marked to be published as
our redacted copy with those two speakers masked.

**TJ overruled that the same day, 23 November 2026**: *"it's required by our boards for public
speakers to say their name and address, so meeting minutes can't be redacted ever for that
reason."* The minutes are published as delivered, unredacted, and
`sources/data/redactions.csv` says `publish`. `notes/process/DATA-PRIVACY.md` now lists
public-comment speakers in minutes as shown, never masked.

## Not re-filed: ten files already held

| delivered as | what we already hold |
|---|---|
| `Minutes 3 Policy Meeting  9-6-24.pdf`, `MINUTES 4 Policy Meeting  9-20-24 (1).pdf`, `Policy Meeting  Minutes 10-4-24.pdf`, `MINUTES -6  Policy Meeting  11-1-24 (1).pdf` | the same bytes, from the 21 October 2026 packet (`PROVENANCE-school-advisory-councils-committees-2026-11-18.md`), now under `school-committee/` |
| `07.15.26 - minutes Lunenburg School Committee.pdf`, `07.29.2026 - minutes.pdf`, `08.26.2026 Minutes.pdf`, `09.09.2026 -minutes.pdf` | the same bytes the town has posted on its Agenda Center (`school-committee/2026-07-15-minutes-7901.pdf`, `-7930`, `-7980`, `-8002`) |
| `7  Policy Meeting  6-21-24 Minutes (1).pdf` | different bytes but the same text as `2024-06-21-minutes-rr2026-11-18.pdf`, one stray word shorter |
| `MINUTES 1 Policy Meeting  7-12-24.docx` | the Word file behind `2024-07-12-minutes-rr2026-11-18.pdf`, with the same text |

## Filed as correspondence: the district's own posting list

`Minutes Overview.xlsx` is filed at
`correspondence/2026-11-23-school-committee-minutes-overview.xlsx`. It is a one-sheet list with
columns `Date | Meeting | Minutes posted? | STATUS | needs attention`. It runs from 3 January
2024 to 21 October 2026, one row per meeting of the School Committee and its sub-committees.
The workbook properties carry the time of Drive's export, not the date the sheet was written,
so **who kept it and when are not established**.

As printed: 120 rows. `Minutes posted?` says `Yes` on 74, `No` on 45 and `No (upcoming)` on 1.
`STATUS` says `Completed, waiting for vote` on the six 2024 Policy Sub-Committee meetings, and
`cancelled` on 2 September 2026. One date, 19 March 2025, has two `School Committee` rows, one
`No` and one `Yes`.

It is the district's own account of which minutes it had posted, and it is not checked here
against the Agenda Center. Comparing the two is a question for the School Committee minutes
goal.
