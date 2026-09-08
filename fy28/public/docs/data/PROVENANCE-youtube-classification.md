# What board each PEG video was for — and what that claim is

**Written by us. It is not a document the town published.**

`sources/data/youtube-videos.csv` holds what the channel published: the video id, the
**title exactly as posted**, the URL. Everything in the four files described here sits
BESIDE that title and is recomputable from it. Improving the classification never means
re-fetching anything, and the title is never replaced by a cleaned version.

## The claim, stated plainly

**A language model read 1,594 distinct title stems and decided, for each, what the video
IS.** That is the most derived thing in this archive: rule 13 with a language model. What
the channel published is the title; what body it was for is our reading of it.

`classified_by` and `classified_at` carry the model and the date on every row.

## Three outcomes, and two of them are not the same thing

| `kind` | means |
|---|---|
| `meeting` | a meeting of one or more identifiable public bodies. The bodies are rows in `youtube-video-boards.csv` |
| `not_a_meeting` | **we know it is not a public body meeting.** A Mass at St. Boniface, a basketball game, a library book club, a Town Manager's report segment |
| `undetermined` | **we could not tell.** Not the nearest match, not the most common board |

`not_a_meeting` is not a small residue on this channel. St. Boniface Mass is one of the
six commonest title stems. Filing a Catholic mass as town business would be a real error in
a published dataset, and so would filing `Committee Confidential - Open Space Committee`
— a talk show ABOUT a committee — as that committee meeting.

**Publish the undetermined count as a denominator wherever this index is used.** A
classifier that silently drops what it cannot read produces a clean-looking index quietly
missing whole boards.

### The line drawn between a body convening and a body presenting

A title that names a body and an event where that body **convenes in public** — meeting,
hearing, workshop, forum, information session, site visit — is a `meeting`. A title that
names a body only as the **presenter of a topical programme** — `Board of Assessors Tax
Exemption Presentation`, `Select Board - 40B Presentation` — is `not_a_meeting`, category
`presentation`. That line is ours and it is arguable; it is written down so it can be
argued with, and an override moves any single video across it.

## There is no `board` column on a video

A tri-board meeting is filed under all three boards. So the boards live in a separate
table, one row per (video, board) pair: a tri-board meeting is three rows and is not a
special case, and a single-board meeting is one row and is not a different shape.

The eight `TriBoard` / `Tri-Board` videos are filed under Select Board, Finance Committee
and School Committee. That is not read off the word "tri" — it is what the town's own
minutes say. School Committee minutes, 4 June 2025: *"the plan at this time is to schedule
a tri-board meeting once a month and that is the full membership of the school committee,
the select board, and the finance committee."* The eight videos run July 2025 to March
2026, which is the schedule the Select Board minutes of 3 June 2025 describe.

## A renamed board is ONE board

`Selectmen Meeting` and `Select Board` are the same body. The evidence is in the data
rather than in the name: titles using **Selectmen** or **Board of Selectmen** run
2012-07-23 to 2020-10-13, titles using **Select Board** or **Selectboard** begin
2020-10-20 and run to 2026-09-01. No overlap, one week apart, one AgendaCenter folder
across both periods. Every such assertion is written in the `basis` column of
`youtube-boards.csv`, and the name the title actually used survives in
`board_name_in_title` on the (video, board) row.

Where a name looks similar and nothing establishes that it is the same body, the two are
**not** merged. `Green Community Task Force` is its own board rather than being folded into
the AgendaCenter's `Green Communities Committee`.

## Boards outside the AgendaCenter's 51 folders

Allowed, and every one is flagged. `meetings_folder` is empty for them and `basis` says so
in capitals. Town Meeting, the Water District, the Green Community Task Force and the TCP
Building Design Committee are real bodies the channel records and the AgendaCenter does
not carry; MA DPU, the MA Energy Facilities Siting Board and FERC are not Lunenburg bodies
at all. The generator prints all of them on every run.

## The meeting date

Derived from the title where the title states one, and `date_source` records which route
each row used. It is never guessed from position in the channel, and there is no upload
date to fall back on — a flat channel extraction returns none, which is registered as a gap
in `money-gaps.csv`.

**The order and century were established from the data, not assumed.** Of the 3,685
`NN.NN.NN` runs in these titles, **2,163 have a second field greater than 12 and none has
a first field greater than 12** — so the form is MM.DD.YY, unambiguously. Two-digit years run
07 to 27 and are read as 20xx; `date_flag` marks any date later than the day the index was
fetched, which catches the two titles that say 27 where the channel's own ordering puts
them in 2024 and 2025.

Four written forms are read: `MM.DD.YY` (and `/`, `-`, or `,` used consistently),
`MM DD YY`, `MMDDYY`/`MMDDYYYY` run together, and `Month Dth, YYYY`. A month name followed
by a bare year is deliberately NOT read as a date — `Oct 2014` would otherwise parse as
20 October 2014.

## Human corrections survive re-classification

`youtube-classification-overrides.csv` is keyed on `video_id`, and the generator **reads it
and never writes it**. Without that, every improvement to the classification would silently
discard every correction, and nothing would report that it happened. The generator prints
how many overrides it applied on every run, including when the answer is zero.

To correct one video, add a row with the fields you want to change and leave the rest
blank; `corrected_by` and `why` are for the person, not the model.

## What this is not

- It is not a claim that a meeting happened. It is a claim about what a title says.
- It is not a claim that the recording is complete. Several titles say the opposite
  (`Board of Assessors PARTIAL MEETING (power outage)`), and those are still `meeting`.
- The **title stem** — the title with its date removed — is OURS, a grouping device for
  classifying 4,671 titles as 1,594 decisions. It is never a quotable form of the title.
