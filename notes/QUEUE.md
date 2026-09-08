# What is queued, in order

## THE ORDER, set by TJ on 8 September 2026

**Phase two, then phase four, then phase three.** Phase three (the town hub, the digests,
the refresh mechanisms) waits until **every drill-in report is built** — TJ was explicit
that the reports come first, even though the hub is the thing residents would notice
soonest. D1 is tomorrow's; D7 and D3 are TJ's own.

Phase one is closed. All three partial pages are routed and rendering, the harvest ran to
2009 rather than 2023, and `/what-stopped-being-funded` finished on 8 September. What
survives from it is listed under *Still open from phase one* below rather than left in a
section marked done.

## Still open from phase one

- ~~**The SEARCHABLE-TEXT denominator, item 3's other half.**~~ **DONE, 8 September 2026.**
  `search_minutes.py` counted a document as searched when a `.txt` file existed for it, and
  a `.txt` exists for every scan the extractor opened holding nothing but the
  `===PAGE n===` markers the extractor itself wrote. Measured properly:
  **8,899 of the 12,015 documents held are searchable
  (74%)**, so 3,116 were being reported as
  covered while contributing nothing a grep could match, and a further 50
  the town lists are not held at all.
  **The threshold is zero, and that is measured rather than chosen.** Calibrated against a
  signal independent of the extractor — whether the PDF carries a `/Font` resource — and
  the two agree at zero and nowhere else. Do not take that from this note; recompute it:

      python3 scripts/build_minutes_searchable.py --calibrate

  It prints the cross-tabulation band by band and the two percentages the cut rests on,
  both of which are currently above 99.8. The documents in the 1-40 character band are NOT
  scans; they are one-line AgendaCenter stubs that do carry a text layer
  (`Planning Board Meeting1.`), and folding them in would have misattributed several
  hundred documents to OCR.
  Each unsearchable document is diagnosed from its own structure rather than assumed:
  **3,096 image scans, 3 whose text is drawn as vector
  outlines** (no font and no raster image — OCR cannot see those either until somebody
  rasterises them), **14 blank**, 2 with a text layer our
  extractor could not read, 1 that will not parse.
  Worst affected, as a share of what that board holds:
  board-of-assessors 255/488 (52%), select-board 629/1,347 (47%), lunenburg-housing-authority 110/255 (43%), school-building-committee-meeting 67/160 (42%), finance-committee 305/780 (39%).
  `scripts/build_minutes_searchable.py` writes `sources/data/minutes-searchable.csv` per
  board and year, `check_generated.py` fails if it goes stale, `search_minutes.py` reports
  the denominator **for the filter you ran** rather than the archive average, and the limit
  is registered as a `record` gap in `sources/data/money-gaps.csv`.
  **Still open from it:** one orphan — `select-board/2026-02-24-agenda-7671.txt` is in the
  text tree and not in `sources/meetings/index.csv`, so the tree and the index disagree by
  one document. Nothing established about why.
- **Item 4, the rule 15a re-runs.** Only `/what-stopped-being-funded` re-ran its searches
  against the grown archive. **Athletics, PEG and free cash have not**, and neither has
  *why $1,500?* — the vote is in the minutes of 26 February 2025 with no derivation, and
  the reasoning may sit in a 2023 or 2024 meeting nobody has read.
- **Item 5, YouTube transcripts.** Not started; needs one install. The design caveat
  stands and is the reason it stays cheap: a caption is a machine's rendering of audio,
  *fifteen hundred* / *$1,500* / *$50* are one sound to it, so a transcript locates a
  moment and never cites a figure.

## OCR the image-only meeting documents — NOT urgent, recorded so it is not lost

TJ, 8 September 2026: *"lets add to the roadmap to OCR those meeting minutes that aren't
text. Not imoprtant right now."*

**3,116 documents, 26% of what the
meeting archive holds, carry no text a search can match.** Measured across all of them
rather than sampled, and they are not one thing: **3,096 are image PDFs**, so
the words are there and unreadable rather than absent and OCR would recover them;
**3 draw their text as vector outlines**, which OCR cannot see either
until the page is rasterised first; **14 are blank** and hold nothing to
recover, here or ever; 2 have a text layer our own extractor could not
read, which is ours to fix and not OCR's job; 1 will not parse at all.
So the OCR run's real target is 3,099 documents, not
all 3,116. They are in R2, so the originals survive whatever happens to this
disk, which is what made this safe to defer. Per board and year:
`sources/data/minutes-searchable.csv`.

Two things to carry into it when it happens:

- **OCR output is a rendering, not the record.** Rule 13 exactly, and the Monty Tech
  lottery PDF is the worked example already in this archive: its per-applicant pages OCR'd
  to `L.unenburg`, `Lunchburg` and `Accepte`. Whatever this produces must be marked as
  ours and must never be quoted as the document's own words.
- ~~**Fix the denominator first, or this hides itself.**~~ **Done, 8 September 2026.**
  `sources/data/minutes-searchable.csv` is the signal, per board and per year, and
  `check_generated.py` fails when it stops reproducing — so an OCR run that works shows up
  as the image-scan count falling, and one that silently does not shows up as it not.


Written 8 September 2026. Ordered deliberately: **finishing beats starting**, and each
item below is either half-built or blocked on the one above it.

---

## 1. Finish the three partial pages — ONE AGENT AT A TIME

Four agents were launched at once and the machine saturated: load average 15, and each
agent runs `npm run build:site`, which spawns Chrome and prerenders every route. **That
build is not parallel-safe** — they contend for `dist/` and prerender port 8794, which
produces phantom "rendered 0 chars" failures that look like real defects. Three were
stopped mid-work.

All three are routed and rendering. Resume them rather than restarting — their context is
preserved and each was close.

| page | where it stopped |
|---|---|
| `/what-families-pay` | building the charts component; had the most new findings queued |
| `/if-students-leave` | wiring the route and App |
| `/stopped-being-funded` | making the search counts derived rather than typed |

**One at a time.** This is the lesson, not an aside: four agents was right for the work and
wrong for the machine.

## 2. Harvest the meetings, 2023-2024

**~1,734 documents we do not hold.** Confirmed against the town's own AgendaCenter,
one year at a time to be sure the range flags behave:

    2023: 841      2024: 893      2025: 904 (we hold 901 — essentially complete)

`fetch_agendas.py --from 2025` was a CHOICE somebody made, and it was then read — by me —
as a fact about what the town publishes. It is not.

## 3. Fix the denominator that made step 2 invisible

`search_minutes.py` prints on every run:

    Searched 1,422 of 1,422 documents the town has published.

(Fixed twice since. The count above was a snapshot of a 2025-onward archive; the second
defect, counting a text FILE as searched text, is closed under *Still open from phase one*.)

**That denominator is ours.** It compares what we hold against what we hold, and calls the
result what the town published. The line exists precisely so that a grep finding nothing
cannot read as *nobody said it* — and it has been doing the opposite, reassuring us with
our own number.

Fix it to compare against what the AgendaCenter reports exists, and to say plainly when the
two differ. **Do this AFTER the harvest**, or it just prints a more precise wrong number.

## 4. Re-run every rule 15a search that came back empty

Athletics, PEG, free cash and the rest were searched against a corpus missing more than
half the record. In particular: **why $1,500?** The School Committee minutes of 26 February
2025 record the vote and no derivation. A slideshow was presented and is not in the
archive. The reasoning may sit in a 2023 or 2024 meeting nobody has read.

## 5. YouTube transcripts — a finding aid, never a source

### TJ's specification, 8 September 2026

> *"I want you to be able to find all the videos posted for every committee, list them and
> store them, then fetch their transcripts in reverse order (newest first). And this
> mechanism will be used to create the refresh mechanism too to find new ones, and fetch
> their link and their transcript."*

**Four parts, and the fourth is the reason the first three are worth building.**

1. **ENUMERATE.** Every video the PEG channel has posted, for every committee — not just
   School Committee and Select Board. `youtube.com/user/LunenburgAccess/videos`. The
   committee has to be derived from the video title, and titles are written by a person, so
   **the mapping from title to board is OURS and gets marked as ours.** It will not be
   clean: expect abbreviations, misspellings, renamed boards and joint meetings belonging
   to two. A video whose board cannot be determined is recorded as undetermined rather than
   guessed into the nearest match.
2. **STORE THE INDEX.** One row per video: id, title as posted, URL, published date, board
   as we classified it, duration, and whether a transcript has been fetched. This index is
   the durable artefact — it is worth having even for videos whose transcripts never
   arrive, because it establishes THAT a meeting was recorded, which is itself a fact the
   written record does not always carry.
3. **FETCH NEWEST FIRST.** Reverse chronological, resumable, rate-limited. Newest first
   because the refresh case and the backfill case are then the same loop, and because an
   interrupted backfill has still delivered the most useful half.
4. **THE SAME MECHANISM IS THE REFRESH DETECTOR.** Re-running the enumeration and diffing
   against the stored index IS "what is new since last time". Do not build a second
   watcher for phase three's refresh mechanisms — this is it. That is the design
   constraint that should shape parts 1-3: the enumeration must be cheap enough to run
   often and must produce a stable id per video so a diff means something.

### The caveat, built in from the start rather than added after

Auto-generated captions are a machine's rendering of audio, not a record. They mangle names
and — fatally here — numbers: *fifteen hundred*, *$1,500* and *$50* are the same sound to a
caption model. **A figure quoted from a caption as though it were the record is rule 13
with a microphone.**

So: a transcript locates the MOMENT. The citation is the video at that timestamp, or the
document the transcript tells you to go and ask for. Store transcripts somewhere that makes
this structural rather than advisory — they are ours, derived, and must never be mistaken
for minutes. They do not belong in `sources/meetings/text/`, which holds documents the town
published.

**And it changes the coverage story.** The town posts minutes for 40% of School Committee
meetings and none at all for 2021 or 2022. A recording of a meeting whose minutes were
never posted is the only account of it that exists. That is the strongest argument for
building this, and also the strongest reason to be careful about how it is quoted.

### THE TITLES ARE NOT CONSISTENT, AND THAT IS THE HARD PART

TJ, 8 September 2026: *"Be careful indexing the videos. Their titles are not consistently
labeled. No standard formatting."*

**So the board and the date are DERIVED, and everything derived here is ours.** Rule 13 is
the whole of this section: the title is the observed thing, our reading of it is not, and
the two must never be stored in a way that lets the second be mistaken for the first.

- **Store the title exactly as posted, always, in its own column.** Never a cleaned or
  normalised version in its place. Every classification we make sits BESIDE it and is
  recomputable from it, so improving the classifier does not require re-fetching anything.
- **A video whose board cannot be determined is `undetermined`.** Not the nearest match,
  not the most common board, not a guess with a confidence score that later gets read as a
  fact. This project has a worked example of the failure — fuzzy label matching proposed
  `M.S. Special Ed Speech Pathologists` -> `E.S. …` at 0.97 similarity, and they are two
  different schools.
- **Publish the undetermined count as a denominator.** Exactly the lesson the minutes
  coverage line taught twice: a classifier that silently drops what it cannot read produces
  a clean-looking index that is quietly missing whole boards. If 300 videos cannot be
  assigned, the number 300 has to be visible everywhere the index is used.
- **The published DATE is not necessarily the meeting date.** A recording uploaded days
  later carries the upload date, and joint or re-posted meetings break it further. Derive
  the meeting date from the title where the title states one, fall back to the publish
  date, and **record which of the two each row used** — a column, not a convention. A
  transcript matched to the wrong meeting is worse than one matched to none.
- **A VIDEO BELONGS TO N BOARDS, AND THAT IS A DATA MODEL DECISION, NOT A PARSING ONE.**
  TJ's example, 8 September 2026: *"a tri-board meeting was created. That would have broken
  any parsing up to that point.... so that should be filed under the 3 boards it
  represents. So we need to be flexible in processing titles and understanding what they
  represent."*

  So **there is no `board` column.** One table of videos keyed on video id, and a separate
  `video_board` table with one row per (video, board) pair. A tri-board meeting is three
  rows and is not a special case; a single-board meeting is one row and is not a different
  shape. Anything that puts a board in the video row forces the tri-board meeting to pick a
  winner or invent a `board_2` column, and both are how the next unforeseen format breaks
  it again.

  The wider point in his correction is the one to build for: **the titles will keep
  producing arrangements nobody anticipated.** A tri-board meeting is not a malformed
  title, it is a real meeting the town held, and the index has to be able to represent
  things the town does rather than only things the town has done so far. That is why the
  classifier is an agent reading intent and not a parser matching a shape — and it is why
  `undetermined` has to be cheap, because the alternative to representing something
  correctly must be recording that we could not, never squeezing it into the nearest slot.
**THE CLASSIFIER IS AN AGENT READING THE TITLES, NOT A PATTERN TABLE.** TJ, correcting an
earlier draft of this section that proposed regexes: *"i just mean, an agent will have to
review the titles to classify which committee they are for. Storing them verbatim is super
required of course."*

That is the right call — no set of patterns survives titles with no standard formatting —
and it makes the stored shape matter more, not less:

- **The classification is a MODEL'S JUDGMENT about a string.** It is the most derived thing
  in this archive and it gets marked as ours everywhere it appears. Rule 13 with a
  language model: what the channel published is the title; what board it was for is our
  reading of it.
- **Store the judgment beside the title, never in place of it**, with the model that made
  it and when. A reclassification then rewrites one column and touches nothing else.
- **HUMAN CORRECTIONS MUST SURVIVE RE-CLASSIFICATION.** This is the part that is easy to
  get wrong and expensive to discover: a separate overrides file, keyed on video id, that
  the classifier reads and never writes. Without it, every improvement to the prompt
  silently discards every correction TJ has made, and nothing reports that it happened.
- **Give the agent the board list and let it decline.** It should be choosing from the
  boards the town actually has — the meeting archive already holds them — and returning
  `undetermined` must be an allowed answer rather than a failure it tries to avoid.
- **Batch it and keep it cheap.** Titles are short; thousands fit in few calls. The whole
  index can be reclassified for very little, which is what makes the overrides file and
  the verbatim titles worth having.

**Do not tune the classifier against a sample and then report the sample's accuracy.**
The honest figure is *how many it refused to classify*, which needs no ground truth — and
if accuracy is wanted, it has to be measured against titles that were not used to write
the prompt.

### WE DO NOT DOWNLOAD THE VIDEOS

TJ, 8 September 2026: *"we dont need to download the videos."*

**The index and the transcript. Never the media file.** This is an explicit exception to
the instinct the rest of this archive runs on — rule 12 says keep our own copy because
links die, and that instinct is right for a 2 MB PDF and wrong here:

- **Size.** The archive is 4.26 GB after taking in 21,000 documents. A single two-hour
  meeting recording is comparable to a fair slice of that. Mirroring years of them across
  every board is a different kind of project.
- **The bucket is write-once for ten years.** A mistake in a document ingest is an
  annoyance; the same mistake across video files is permanent and large.
- **We are not the archive of record for the recordings.** The PEG channel is, and this
  project already extracted its finances. What we need from a video is *what was said and
  when* — the transcript gives that, and the timestamped URL gives the citation.

So the stored artefacts are: the video index (one row per meeting recording) and the
transcripts. **The citation is a URL into the channel at a timestamp**, which means the
link dying is a real exposure we are accepting knowingly rather than one we overlooked —
and the index is what makes it recoverable, because it records the title, the date and the
board even if the video goes.

### What it needs

One install (`yt-dlp` or `youtube-transcript-api`); neither is on the machine. **Neither is
needed to download media** — both can list a channel and pull captions alone, and the
fetcher should be written so it cannot pull a media stream even by accident.


The minutes carry a standing notice that each meeting is recorded and uploaded, and the
archive already holds the address: `youtube.com/user/LunenburgAccess/videos`. That is the
PEG access channel whose finances this project extracted the same week.

Needs one install (`yt-dlp` or `youtube-transcript-api`); neither is on the machine.

**Design it with the caveat built in from the start.** Auto-generated captions are a
machine's rendering of audio, not a record. They mangle names and — fatally here — numbers:
*fifteen hundred*, *$1,500* and *$50* are the same sound to a caption model. So a
transcript locates the moment; the citation is the video at that timestamp, or the document
it tells you to ask for. **A figure quoted from a caption as though it were the record is
rule 13 with a microphone.**

---

## Blocked, not queued

- **D1 is not synced.** Today's write budget is spent — the free tier stopping, not
  billing. ~70,000 rows per full push against 100,000 a day, and several went today.
  Resets tomorrow; `sync_d1 --check` is the only red until then.
- **D7, the records request.** Still the highest-value thing on the whole list and still
  TJ's to send. It has grown teeth this week: the MUNIS year-end expense report for prior
  years (we already hold FY2026's, so it is a small ask against a named document), the
  athletics accounts-payable detail, the district's fee schedule as published to families,
  and the 26 February 2025 athletic user fee presentation.
- **D3**, the tax-rate and town-meeting extraction, still parked.

---

# Phase two: what the DESE data becomes

Set 8 September 2026, after ingesting 18 DESE files. **Sequenced deliberately — the
database work gates everything below it.**

## 6. Build the database out

15 of 18 staged files are catalogued and unread. Nothing below can start until they load,
and each carries a trap already recorded in `notes/DATA-TO-INGEST.md`: rollup rows beside
detail, `FY` against `SY` keys, a repeated SY2024 row, VLOOKUP front sheets.

**Do not load them all into one wide table.** They are different grains — district, school,
person-class, placement-cohort — and joining across grains is how this project produced
$116M for a $26.6M district.

## 7. Grant money unwinding — the visual TJ asked for first

The finding is already established for one line. Paraprofessionals, function 2330:

    FY2013 -> FY2014   total +1.3%   general fund -40%   grants +190%
    FY2019 -> FY2022   total +22%    town's share +44%

**Half of what looks like growth is a grant ending.** The page should run that across every
function code, not just paras — a stacked area of general fund against grants per function,
where the eye sees the swap even when the total is flat.

**The honest frame:** this is DESE's attribution of a dollar to a fund. It does not say
which post, which grant, or that the same people moved between funds.

## 8. Staffing over time — counts, costs, and CUTS

TJ, restating it: *"school staffing over time. Costs, counts, cuts, etc."*

**"Cuts" is the framing that makes this a page rather than a table**, and it is the one
thing here nobody can currently answer. The town has argued about staffing cuts through
two override cycles and no published series shows what actually happened to the workforce.

What we now hold that makes it possible:

    dese_teacher_grade_subject   FTE by grade band AND subject AND school
    dese_teacher_program_area    GEN_ED / SPED / CAREER_TECH / EL FTE
    dese_educator_workforce      HEADCOUNT by job class, plus hires and retention
    dese_function_expenditure    the same years, split general fund vs grants
    budget_figure                what was budgeted and later restated, per line

**Four series, four different units, and that is the whole difficulty.** FTE, headcount,
dollars and budget lines do not convert into one another, and a page that quietly treats
them as the same thing will be wrong in a way nobody can see. State the unit on every
figure.

**The cuts question specifically.** A post disappearing from a budget line is not a cut: it
can be a vacancy unfilled, a role recoded, a grant ending, or a retirement not replaced.
`dese_educator_workforce` carries HIRES and RETENTION alongside headcount, which is the
only thing here that distinguishes *people leaving* from *posts disappearing*. Use it.

**Two traps already paid for, both recorded above.** The educator table's naive sum is
exactly 2x the truth — `All Educators` sits beside the seven race rows, and I published
double figures before catching it. And any cost-per-FTE reproduces the $69,161 error unless
it names its denominator, because EPIMS FTE is per ASSIGNMENT while a budget line pays
whole salaries.

Carry unresolved rather than solving: sped teacher FTE 18.5 (2008) to 2.0 (2026) against
flat total FTE.

## 8a. The original framing, kept: FTE against funding and cost

Now possible and previously not: FTE by grade band, subject and school; headcount by job
class including administrators; special education staffing ratios; retention and new hires.

**Cost per FTE is the prize and the trap.** EPIMS FTE is per ASSIGNMENT; a budget line pays
whole salaries. Any cost-per-FTE figure must state which denominator it used, or it will
reproduce the $69,161 error in a new costume.

Carry forward as unresolved: sped teacher FTE 18.5 (2008) to 2.0 (2026) against flat total
FTE, and administrators 28 to 38 on a base of ten people over three years.

## 9. Chapter 70, modelled exactly

34 years of every formula term, FY1993-FY2026, and FY2026 aid reconciles to the figure
derived independently for `/state-aid`. Foundation enrolment, foundation budget, required
local contribution, aid, required and actual NSS — plus `keyfactors.xlsx` holding the
INPUTS (English learner, vocational and low-income shares).

**Whether it can be modelled *exactly* is an open question, not a promise.** The formula has
hold-harmless and minimum-aid provisions; Lunenburg's aid already sits $395,366 above
foundation-minus-required, which is those provisions operating. Test the reproduction
against known years before claiming a model.

## 10. Special education: four reports, not one

The data now answers, separately: how many students (a published count, 217-265); how many
leave and where (58 via choice in SY2026, back to 2014); what it costs and what circuit
breaker reimburses; and the route into out-of-district placement.

**Keep them apart.** Merging them into one narrative is how a proxy becomes a fact.

## 11. What else — candidates worth testing

- **Lunenburg is 310th of 318 districts on per-pupil spending**, $18,027 against a $23,520
  median. Verify, then publish; it is the plainest fact in the whole batch.
- **Spending mix against peers** — do we spend more on administration and less on teaching,
  per pupil, than comparable districts?
- **Foundation budget against actual spending, by category.** The foundation formula assumes
  a per-pupil amount per category. Comparing actual function spending to what the formula
  assumes shows where the town spends above or below the state's own model of adequacy.
  Nobody in town has this.
- **Circuit breaker against the out-of-district line** — how much of that cost comes back,
  and whether the budget line is stated net or gross of it.
- **The net school choice position** — we hold both directions. Children out, children in,
  and the tuition each way.
- **Retirement exposure** — educators by age group drives future salary-step cost.
- **Student-teacher ratio against spending**, over time and against peers.

---

# Phase three: the site as a town hub

Set 8 September 2026. **A different KIND of content from everything above, and that
distinction is the first design decision.**

Every page on this site so far is a *measurement* — a figure somebody can check against a
document. What follows is *announcements*: what happened, what is coming, what is open for
registration. Both are useful and they are not the same epistemic category. **Keep them
structurally and visually distinct**, or the credibility built by the first gets spent by
the second. A wrong meeting date is a small error; a wrong meeting date sitting beside a
budget figure teaches a reader that the budget figures are that kind of number.

## 12. Refresh mechanisms — soon, TJ wants these in days

**"Deterministic" is TJ's word and it is the right requirement.** Every checker answers
*what changed since the last run*, stores that state, and is idempotent — running twice
produces one result, not two. No feed should ever be able to say "new" about something it
already said was new.

**YouTube — the Lunenburg Access channel.** `youtube.com/user/LunenburgAccess/videos`, found
in the minutes' own standing notice, and it is the PEG channel whose finances this project
already extracted. **Use the channel RSS feed** (`/feeds/videos.xml?channel_id=…`) rather
than the API: no key, no quota, no billing, and it is a published interface. Surface as
"3 new videos this week" / "New School Committee video".

**Meetings — we already have the fetcher.** `scripts/fetch_agendas.py` walks board × year.
Extend it to report NEW rather than re-download everything, and drive two surfaces:
*"Upcoming meetings this week"* with the agenda downloadable, and *"minutes posted"* when a
meeting that had none gets some. **The second is quietly valuable**: it is the same signal
as `minutes-coverage.csv`, live — a town where minutes appear promptly looks different from
one where they do not, and now that is measurable rather than felt.

**Cost.** These are cheap (RSS and HTML, no paid API), but anything writing to D1 shares the
100,000/day budget the data push needs — see the question inbox, which was given its own
database for exactly this reason. Do the same here, or keep state in a committed file.

## 12a. MEETING DIGESTS — this is the actual point, and I had it filed wrong

TJ: *"i personally was watching every meeting in town (Select board, finance committee and
school committee). and taking notes, and posting them online. People loved it because i
focused only on the details that mattered to them. That is missing."*

**So the feed is not notifications with digests attached. The digests ARE the product**, and
the notifications exist to bring people to them. Filed above as though "new video posted"
were the feature; it is the delivery mechanism.

**And this dissolves the line I drew in the section above.** I warned that announcements
must stay apart from measurements. A meeting digest is neither: it is derived from a PRIMARY
SOURCE this archive already holds, it can quote, and every quote can be asserted against the
minutes file on build — exactly what `/what-sports-cost` and `/state-aid` already do. That
makes it far closer to the analysis pages than to a news feed, and it should be built to
their standard rather than a lower one.

**What is checkable and what is editorial, kept apart (rule 7).**

- *What the minutes say* — quotable, citable, asserted at build time. A vote, a figure, a
  motion, who moved it.
- *Why it matters to you* — TJ's actual contribution, and the reason people read it. That is
  judgement and must read as judgement.

The failure mode is the familiar one: an editorial line hardening into a stated fact by the
next paragraph. A digest saying *"the Committee cut middle school athletics"* when the
minutes record a budget reduction of $14,415 has already crossed it.

**We can go backwards as well as forwards.** The archive now holds **4,660 sets of minutes
back to 2009**, extracted to text. Digests need not start with the next meeting — the
back catalogue is there, and the years nobody has read are exactly where the answers to
current arguments sit.

**On drafting them.** If a model drafts, three rules and none is optional: every claim
carries a quote from the minutes; the quote is asserted against the file at build time so a
fabricated one fails the build rather than publishing; and a person approves before it goes
out. A hallucinated decision on a town budget site would cost more credibility than the
whole feed is worth. Note also that per-meeting drafting costs money per meeting, unlike
everything else here — cap it and say so.

**Start with the three boards TJ already watched** — Select Board, Finance Committee, School
Committee. We hold 1,022 sets of their minutes, 2010-2026.

## 13. Community news

Aggregate and LINK. Do not republish. Reproducing somebody else's announcement wholesale is
both a copyright problem and a quality one — the value is the pointer plus a sentence of
context, not a copy. Attribute the source on every item.

## 14. Athletics and youth sports — a section of its own

Registration openings harvested and posted as they appear. Same rule as community news:
link, summarise, attribute; never wholesale copy.

**Note the tension with `/what-sports-cost`.** That page says the district's own athletics
cost figures are disputed. A sports section that reads as promotional next to an analysis
that reads as sceptical needs a clear line between them, or each undermines the other.

## 15. The sports directory — TJ says MUCH later, recorded now so it is not lost

What sports are available at what ages, how to register, who to contact, what it costs.

**This is the most useful thing on the whole list for an ordinary resident, and the hardest
to keep true.** It is not derived from any document we hold: it must be gathered from
leagues, the district and youth organisations, and it goes stale the moment a season turns
or a volunteer changes. Anything built here needs a stated review cadence and a visible
"last checked" date per entry, or it becomes a page of wrong phone numbers.

If it is ever built: the same rules apply. Every entry names where it came from and when it
was verified.

## 16. Facebook — later still

Push the above to drive people back to the site. Nothing to build until the feeds exist.


---

# Phase four: Monty Tech, the outflow nobody has modelled

Set 8 September 2026. Recorded for later — the data is in hand.

## 17. A Monty Tech drill-in

**It is bigger than school choice and growing faster, and nothing on this site mentions it.**

    FY      in Lunenburg   Monty Tech   all resident   MT share
    2014           1,513           70          1,699       4.1%
    2019           1,616           72          1,792       4.0%
    2026           1,553           97          1,730       5.6%

Flat around 4% through FY2019, then up every single year since. 70 -> 97 in headcount,
+39%, while Lunenburg's own enrolment fell. And the Class of 2030 lottery admitted **24
Lunenburg students against 365 places, 6.6% of the incoming class** — larger than the
current four-year average, so the climb looks set to continue.

**THE REASON IT MATTERS IS NOT THE ONE PEOPLE ASSUME.** Monty Tech is an ASSESSMENT, not a
tuition. Lunenburg is a member town of the regional vocational district and pays a share of
its operating cost. So 27 more students since 2014 is not 27 x $5,000 walking out — it is a
growing slice of a bill the town has almost no control over, set by a district it does not
run. That is a different mechanism from school choice and a different argument.

It also complicates `/if-students-leave`, which treats leaving as school choice. **Monty
Tech is the larger outflow — 97 against 58 — and has grown for seven straight years.**

## What we hold

- `dese_town_enrollment`, FY2014-FY2026, Lunenburg residents at Montachusett Regional
- `report_monty_tech` (70 rows) from the annual town reports
- `sources/inbox/montytech-class-of-2030-lottery.pdf`, sha `0a28526cac39` — OCR'd

**On the lottery PDF: the summary page is trustworthy, the applicant pages are not.** The
18 town figures sum to exactly the printed total of 365, which is the parts-tie-to-total
check. The per-applicant pages are OCR of an image PDF and produced `L.unenburg`,
`Lunchburg`, `Accepte`, `Waitlis`. **Do not count accepted-versus-waitlisted from that OCR**
— that is a derived thing quoted as observed. If the split is wanted, request it.

No personal data in the document: town, an anonymous applicant number, and a status. Checked
before archiving.

## What we do NOT hold, and would need

- **The assessment itself.** What Lunenburg pays Monty Tech each year, and how the share is
  calculated. That is the money question and it is not in anything here yet.
- Prior years' lottery results, for an applications trend rather than a single cohort.
- Whether Lunenburg applicants are accepted at a different rate than other member towns.

## The questions a resident would actually ask

- Is the assessment rising faster than the student count, or slower?
- Does a student at Monty Tech cost the town more or less than one in Lunenburg?
- Is the rise demand from families, or capacity decisions at Monty Tech?

**The third cannot be answered from counts alone** — an admission is a place offered as well
as a place wanted, and the lottery exists precisely because demand exceeds supply. Counts
show the outcome of both and separate neither.
