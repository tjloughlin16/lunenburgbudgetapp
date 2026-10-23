# The Superintendent's special education funding deck for the Finance Committee, 22 October 2026

This did not come off a website, and it was not a records request. The share is the
address (rule 12), set out below.

## How it reached us

**Shared informally by a member of the Finance Committee, after the slides became public
record.** TJ, 23 October 2026: *"came from someone on the finance committee directly after
they became public record. but not as a FOIA request. so just a friendly share."* TJ did not
name the member, so this note does not either.

The copy on TJ's computer was saved from a Gmail attachment at **08:00 on 22 October 2026**
(file-system timestamp and download origin). The Finance Committee met at 7:00 PM that
evening. So our copy is from before the presentation, and we do not know whether the version
shown that night differs from it.

| our copy | publisher's filename, as shared | bytes | sha256 | state |
|---|---|---:|---|---|
| `2026-10-22-special-education-funding-superintendent-finance-committee.pptx` | `Lunenburg_Special_Education_Funding_10_Slides.pptx` | 63,570 | `1b7f6f9fe4b4ffa445ab975ac5c8125318227c0ecc45518435b47418d506a4fa` | public |

It passed the screen on arrival (`redact.gate()`: nothing found), so it went straight to the
public bucket. The only person it names is the Superintendent, in her role. The extracted
text, with the speaker notes, is in `text/`.

## Who made it

**The school district: the Superintendent's office.** The evidence, from the file itself:

- **Slide 1** reads *"LUNENBURG PUBLIC SCHOOLS / How special education funding flows / A guide
  for the Lunenburg Finance Committee / Dr. Jodi Fortuna / Superintendent of Schools / October
  2026"*.
- **`docProps/core.xml`**: `lastModifiedBy` = `Jodi Fortuna`, revision 5, created
  2026-10-21T13:36:16Z, modified 2026-10-21T19:51:11Z.
- **The same file also says** `creator` = `Walnut Exporter`, and `docProps/app.xml` names its
  one theme `ChatGPT`. *A hypothesis, which nothing here tests:* the deck was first generated
  by a tool and then edited in PowerPoint under the Superintendent's name. The speaker notes
  say *"Sources retained from the supplied presentation"* and slide 10 says *"Published
  figures are from the supplied deck"*. So it was rebuilt from an earlier deck that we do not
  hold.

It is **not** a Finance Committee member's own summary. A member only passed it on.

## Where it was presented

**Finance Committee, 22 October 2026**, agenda item 6b, *Special Town Meeting Warrant
Articles* (`meetings/finance-committee/2026-10-22-agenda-8087.pdf`). The committee took it up
under the article *Transfer of funds to the Special Education Reserve Fund*. Found with
`scripts/search_minutes.py "circuit breaker" --board finance-committee`. The town's minutes of
that meeting are not yet held, so all of this comes from our machine captions, which are a
finding aid and not a record:

- [1:38:11](https://www.youtube.com/watch?v=wQWhIwYOc9o&t=5891s): the Chair introduces the
  article and says he asked *"Jodi and her team"* to explain how the operating budget,
  Circuit Breaker and IDEA money interact.
- [1:41:53](https://www.youtube.com/watch?v=wQWhIwYOc9o&t=6113s): *"I'm going to go through
  this presentation"*. Slides 2 and 3 are then read aloud nearly word for word, up to the
  FY27 IDEA allocations of $423,413 and $13,967.

## What kind of evidence it is (rule 13a)

**`stated`: an explanation somebody wrote, not a record printed by an accounting system.**
Most of it describes how the funding mechanisms work. Its figures fall into three kinds:

- **Transcribed from DESE's published listings.** The FY26 final Circuit Breaker row on slide
  6 (9 students, $484,149 instruction, $94,993 transportation, $579,142 total) matches DESE's
  own workbook in this archive: `sources/data/dese-circuit-breaker.csv`, the FY2026 row,
  from `state-dese/dese-circuit-breaker.xlsx`. The FY27 initial listing and the FY27 IDEA
  allocations were **not** checked against a DESE file.
- **Worked examples.** Slide 4's $100,000 placement is an example.
- **Illustration only.** Slide 8's $5,000,000 spending plan says so on the slide itself.

The deck says what it does not establish. Speaker note 1: *"It does not certify current
Lunenburg fund balances or total special education expenditures."* Slide 9: *"This
presentation does not establish that Lunenburg has funded this reserve."*
