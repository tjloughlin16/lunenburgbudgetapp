# School Committee minutes delivered 27 October 2026

One set of School Committee minutes, the special meeting of **15 July 2026**, sent to this
project by email and not posted on the Agenda Center. Filed under
`sources/meetings/school-committee/` like every other set, with the file_id `rr2026-10-27`
in place of an Agenda Center document number. There is no Agenda Center number, and the
id is where a reader can see how the document arrived. The same convention as
`PROVENANCE-select-board-2026-09-18.md`.

## Minutes sent to us are the meeting's minutes. They are not posted

TJ, 28 October 2026: *"we need to assume if they send us minutes directly, then they are
'posted' to me. They have made it clear they may not use the Agenda site."* And, the same
day: *"we should not change the posting percent if they send to me. the point is for them to
post to the public."*

So a delivered set is filed and read as the meeting's minutes: held, searchable, linked from
the meeting's page. But it is not **posted**, and no posting figure counts it. Posted means
the town put it on its Agenda Center, for everyone. A delivered set has no Agenda Center
address, and that absence is the test (`meeting_records.status()`, `build_boards.py`,
`build_board_posting.py`). The meeting's minutes keep the status the approval window gives
them, `not available` or `MISSING`, with this copy beside that status.

The Committee's counsel says so in writing. In its response of 26 October 2026 to TJ's Open
Meeting Law complaint of 5 October (Matthew P. Milward, VDH Boston, for the Committee), it
argues that *"the Open Meeting Law does not require that meeting minutes be posted to a
website"* and that M.G.L. c. 30A §22(c) requires minutes to be *"made available upon request
by any person within 10 days."* It concedes that the Committee did not answer TJ's request of
8 September 2026 within ten days, and commits to provide the minutes requested *"as
expeditiously as possible"*. The response and the complaint are summarised in
`notes/HANDOFF-FILINGS.md`.

Counsel's position is about §22(c), availability on request. This archive's posting measure
asks a different question: what a resident who has asked nobody can read.

## This delivery

**15 July 2026 is meeting 6 of the 35** in TJ's request of 8 September 2026
(`notes/outbound/REQUEST-school-committee-minutes.md`). It is the first of the 35 to arrive
by email.

**Emailed by Liz Petersen, Executive Assistant to the Superintendent, at 4:54 PM on
27 October 2026**, copied to the Superintendent, the Chair and a fourth recipient (Renee, address `remkey`). Subject
`07/15/26 Minutes`, body *"Attached are the minutes from the 07/15/26 School Committee
meeting."*

| | |
|---|---|
| file, as received | `07.15.26 - minutes Lunenburg School Committee.pdf` |
| our copy | `meetings/school-committee/2026-07-15-minutes-rr2026-10-27.pdf` |
| bytes | 150,618 |
| sha256 | `6465af1919aaafa8d4451ecb60a3ed266a9988e7b754551451a89a97282a8d24` |
| pages | 5, all digital (`pdf_kind`: text layer on every page) |
| PDF metadata | Author `Liz Petersen`, Creator `Microsoft® Word 2016`, created 2026-10-27 16:39:40 -04:00 |
| state | public. It passed the screen on arrival (`redact.gate()`: nothing found) |

The PDF was made the afternoon it was sent, 104 days after the meeting. **The document does
not say whether the Committee has approved these minutes**, and nothing marks it a draft, so
it is filed without `-draft`. §22(c) covers minutes *"whether approved or in draft form"*, so
the delivery does not settle that either.

It was first filed as `correspondence/2026-10-27-school-committee-minutes-2026-07-15.pdf`
and refiled here the next day. The bucket keeps that first object. It is registered in
`sources/data/archive-orphans.csv`, `superseded_by` this key: the same bytes.

## What is in it

`SPECIAL MEETING MINUTES / SCHOOL COMMITTEE / Wednesday, July 15, 2026`, recorded by Gina
Gonsalves. Present: Brzozoski (Chair), Sculimbrene, Gilman, Russell. Young absent.

| item | motion | result as printed |
|---|---|---|
| 4a | accept the 06.24.2026 minutes | 4-0 |
| 6a | table the warrant article until after the spending plan | 4-0 |
| 6b | approve the proposed spending plan | 4-0 |
| 6c | approve the warrant article, $350,000 for the FY2027 school operating budget | 3-1, Gilman NO |

**Item 5b lists `Warrants: 6/18/26 to 6/30/26 - $362,767.40` with no motion and no vote.**

## The follow-up: no vote was taken on the warrant

TJ replied at 5:31 PM that the minutes did not say whether the warrant was voted and
approved. **Laura Brzozoski, Chair of the School Committee, 8:50 PM, 27 October 2026:**

> *"It is not recorded as a vote in the minutes because no vote was taken."*

TJ acknowledged the reply at 9:37 PM.

Twelve minutes before the minutes, at 4:42 PM, the same office had shared a Drive folder of
the warrant's bills, and its message reads: *"The warrants are always on the agenda for each
period with a total, and they are approved by the committee in public session."* Access was
revoked by 4:51 PM over personal information in the bills. That thread is
`correspondence/2026-10-27-warrants-folder-superintendent.txt`. Two statements from one
evening: the first about the practice, the second about this occasion. What this establishes is the Chair's statement that the
Committee took no vote on the 6/18/26-6/30/26 bills warrant at this meeting. It does not
establish whether that warrant was approved by another route or at another meeting.

## Against our minutes of the recording

`sources/data/recording-minutes/school-committee/2026-07-15-Dvp2YlTJOXo.json`, written from
machine captions, recorded the outcome of the warrant-article vote (6c) as **not audible**.
These minutes print 3-1, Gilman voting no, and they are the record. Our recording minutes
show no vote on the bills warrant either, which agrees with the Chair.
