# How to work in this repo

This is a public budget tool for one town. Residents and town officials read it and quote
it. The rules below exist because each one was learned by getting it wrong here.

---

## 1. Never mix budgets with actuals in one calculation

A **budget** is what somebody voted or proposed. An **actual** is what got spent. For some
lines they differ by 7%, and for out-of-district tuition by 59%.

A growth rate measured from an actual to a budget is partly growth and partly the step
between the two. That error put a special education escalator 1.5 points too high and was
invisible until somebody asked how the number was derived.

- The projection uses **budget columns only**. `finance.py` reads `fy27_balanced`.
- Actual spending answers a different question and lives in
  `sources/analyses/budget-vs-actual.md`.
- An actual may **explain** something in an analysis. It may never feed a projection.
- `scripts/audit_provenance.py` fails the build if a projection module reads an actuals
  column. Run it.

## 2. Interpolate every figure. Never type one into prose

A number typed into a sentence is the only thing here that can be silently wrong. The type
checker cannot see it, and it keeps rendering confidently long after the model has moved.

Three figures were found stating amounts the model no longer produced — one off by
$313,000. All were in prose beside figures that were computed.

- Derive it from the model, always, even when it feels stable.
- After any change to a rate or a bucket, grep the prose for literal figures.
- The same rule applies to `conclusions.py` and `headlines.py`, which are prose that ships.

## 3. Say which numbers are ours

Every figure is one of: published by somebody, set by contract, fixed by statute, or our
estimate. A reader cannot judge the argument without knowing which.

- `model/citations.py` carries the document and the basis for each headline figure.
- Anything we estimated says so, in the app, in the citation, in that color.
- The source archive is split: published by others above the line, written by us below it,
  in those words.

## 4. Weight times excess rate, not rate alone

A line matters to the gap in proportion to its **share of the budget times how far its
growth exceeds the levy cap**. Neither number means anything alone.

Utilities grow at 15% and are 2.3% of spending: 0.28 points. Teaching salaries are 35.7%
of spending and grew at 2.50%: 0.01 points. The biggest line in the budget is not a driver.

Rank by pull. Never by size, and never by rate.

## 5. Follow magnitude, not actionability

Athletics is 1.7% of spending and had three sections in this app. Special education is
about 22% and had none — because "the district must place a child where the plan requires"
reads like *nothing to model here*.

That reasoning is wrong. A line nobody controls still sets the size of the problem. Measure
everything; decide what is actionable afterwards.

## 6. Check assumptions against history, and check like for like

Every rate in the model was inherited from the district's forward budget narrative and
never once tested against its own later budgets. Four years of data sat in the same file.

- `scripts/backtest_rates.py` compares each assumption to what the line actually did,
  budget to budget. Run it after any change to rates or buckets.
- A three-year rate off a small base is not a trend. Read the year-by-year before
  concluding — three of six flagged lines turned out to be one-time step changes.
- Lines that go to zero and reappear renamed produce −100% rates that look like findings.

## 7. Only facts are stated as facts. A proxy is never a fact

**A number computed from the data is a fact. An explanation for why that number moved is
not.** The second is a hypothesis, however obvious it feels, and it must be labeled as one
every single time.

This rule has been broken here repeatedly and always the same way: a real measurement gets
one plausible cause attached, and a sentence later the cause is being restated as though it
were the measurement.

Three that shipped before being caught:

| written as fact | actually established |
|---|---|
| "The district brought children back in district" | Two budget lines moved in opposite directions by similar amounts |
| "The difference is not a pay rise — it is more staff" | The increase exceeds what the contract percentages alone produce |
| "The mix shifted toward intensity" | Two sources report different student counts and cannot be reconciled |

Each of those has other explanations that fit the same data equally well: the tuition line
may simply have been over-budgeted for years; the staffing residual could be
classifications, steps, hours, or recoding; the counts differ because they count different
things.

**How to write it instead.** Separate the two, explicitly, in the text:

- *What the data shows* — the measurement, and only the measurement.
- *What it does not show* — the alternatives that fit equally well.
- *A possible explanation, offered as a hypothesis* — if it is worth recording, say plainly
  that nothing here tests it, and name what would.

**Do not use a proxy as if it were the thing.** Dollars are not students. A budget line is
not a filled position. A count of documents is not a count of decisions. If the actual
quantity is not published, the honest sentence is that we cannot say — not a number
inferred from something adjacent to it.

Specifics that follow from this:

- If the data cannot distinguish two explanations, give both, and say it cannot.
- `MANDATE_FLOOR` is an assumption we invented because a cascade needs somewhere to stop.
  The town has cut a school psychologist to zero. There is no established floor.
- A document stating intent is evidence of intent, not of outcome. The district writing
  that in-district staff are cheaper than placements shows what it meant to do. It does
  not show what happened.
- Name what would settle it. Usually one number nobody publishes.

## 7a. Do not open a page with the context. Open it with the thing

**A page leads with what it is for. Everything explaining how to read it comes after.**

TJ, after the same correction on four different pages: *"we need to keep the top sections
from being big blocks of text that are just context, across the whole app. its a pattern
you do when you build, but people hate that."*

It is a pattern, and it comes from writing the page in the order it was built rather than
the order it is read. Everything above the fold got there because it seemed necessary
BEFORE the reader could understand what follows — which is true for the author, who has
just spent an hour on the caveats, and false for the reader, who came for a table.

The count is the test. Four real cases here, all mine:

| page | prose before the thing | after |
|---|---:|---:|
| the front page | ~700 words, then eighteen links | four doors |
| the schema page | 156 words and a caveat | 32 words and a metric row |
| the money page | five documents as equals | two, then the rest |
| the school flow | a section answering the question the cards raise | answered on the card |

**How to write it instead.**

- **The thing first.** The inventory, the four doors, the two documents, the figure. If
  the page is called *the database, table by table*, the tables are the page.
- **A caveat goes beside what it qualifies**, not above everything. The note about which
  database the query button reads belongs next to the query button. A footnote that opens
  the page is a preface.
- **The key comes after the thing it is a key to.** Explaining the badges before a reader
  has seen a badge is explaining a legend to somebody who has not seen the map.
- **One line under the title, not a paragraph.** If the standfirst needs three sentences,
  the page is doing two jobs.
- **Guidance does not get worse by moving down. It gets findable**, because a reader
  meets it after they have seen the thing it is about.

The exception is a genuine warning that changes whether the reader should trust what
follows — rule 3's territory, and the caveat block on `/reports`. Those lead. "Here is how
this page is organised" is not one of them.

## 7b. A drill-in page: conclusions, then categories, then the raw

**Every analysis page opens with what it MEANS, not with what it holds.** TJ's pattern,
and it is the shape a resident reads rather than the shape the data arrives in:

1. **Insights / conclusions.** What this page establishes, in sentences. Three or four,
   each one a claim a reader could repeat at a meeting.
2. **Organised categorical data.** The breakdown that supports them — by year, by category,
   by school. Charts belong here.
3. **Raw data and context.** The table, the caveats, the method, what it does not show.

Rule 7 governs all three: a figure is a fact, an explanation for it is a hypothesis, and
the top of the page is exactly where that line gets crossed. An insight may say *this line
grew 40% while enrolment fell*. It may not say *because the district hired* unless a
document says so.

Rule 7a still applies within section 1 — lead with the conclusion, not with a paragraph
explaining that conclusions follow.

### A conclusion is a metric and two lines. Everything else expands

TJ, 9 September 2026, reading the synthesis page: *"we cannot have BOLD context lines that
are 3-5 lines. the metric + the description need to be short. context description should
be 1 or 2 lines max. Additional context must go into the expansion. which means we have to
be HYPER clear about what the metric represents, and what conclusion to draw from it
without needing a full paragraph of context for each."*

    the METRIC, with its unit          93 of 132 budget items
    one line: what it is               when the school budget stops funding something
    one line: what follows             it usually comes back
    ---- everything else expands ----

**The hard part is not the trimming. Cutting the context forces the METRIC to carry its
own meaning**, and that usually means picking a different metric rather than writing
shorter prose around the same one. `93` needs a paragraph. `93 of 132 budget items` needs
one line. Where a figure cannot be made self-explanatory in a few words it is the wrong
figure for the card.

Two failures this rule exists to stop, both real:

- **A bare number.** `93`, `10`, `18`. This project's whole discipline is that dollars are
  not students and a count is not a rate -- rule 7, and the reason every report states its
  grain. A unitless figure in a stat box abandons that at the moment a reader is most
  likely to quote it. Ten children, ten documents and ten budget lines must not look alike.
- **Insider vocabulary.** *A line printed at zero in the district's book* is precise and is
  not English anybody speaks. Every noun in it is ours. TJ, who reads this project daily,
  said of that card: *"i have NO idea what this is talking about."* Precision and jargon
  are not the same thing, and the second is often an unfinished sentence.

**Enforce the length in the generator, not by eye** -- a character budget derived from the
card's real width, and a build that fails past it. A rule checked by reading lasts until
the next report.

**And trimming must never cost the epistemic label.** The one scenario among sixteen
measured conclusions has to stay visibly a scenario however short it gets: a reader who
takes a modelled figure as something that happened has been misled, which is worse than
any sentence cut to make room.

### A conclusion is a COMPARISON, or it is inventory

TJ, 10 October 2026: *"the summary at the top feels like a nothing-burger... we need to find
the contentious points and surface them, not just show blank metrics."* The transportation
page led with *athletic buses were 6.4% of spending* while its own ledger showed the special
education bus line closing FY2026 $67,556 past its budget, uncovered. **Before drafting any
card, run `notes/process/AUDIT-PASS.md`** -- eight comparisons, and a card leads only if a
member of the deciding board would dispute it or have to answer for it. Rule 8 still governs
how it is WRITTEN: two measured things side by side, a question for the budget, never a
charge.

### Three years is a trend HERE, and that is not a general claim

The default instinct — "three years is too short to plot" — is wrong in this town, and
it was corrected after being applied to athletics participation. TJ:

> *"our boards in town are hesitant to look forward even 2 years because they dont trust
> the stability. So 3 years to them is magical."*

The audience is a board that will not project two years out. A three-year series is not a
weak trend to them; it is more forward visibility than they currently use. So plot it —
and **state the span on the chart** so nobody mistakes three years for fifteen.

The rule this replaces is not "short series are fine". It is: **judge a series against
what the reader currently has, not against what a statistician would want.** Five checked
years of state revenue is thin for a regression and substantial for a town that budgets
one year at a time.

## 7c. A conclusion you cannot draw is a GAP, and it gets registered

**When an analysis stops short because the data will not carry it, that stopping point is
a finding and it belongs in `sources/data/money-gaps.csv`.** Not only in the prose of the
page that hit it.

TJ: *"While we generate insights, if we can't draw conclusions because data is missing,
that's a GAP (and a VISUAL one I hope) we have to fill."*

The reason it must be registered rather than merely written: a limit stated in one
paragraph of one page is invisible to everyone who did not read that page — including the
next person building the next page, who will hit the same wall and describe it again in
different words. `money_gaps` is the single registry, it loads into the database, it is
published at `/api/money_gaps.json`, and `/what-we-cannot-answer` renders it. Add a row
there and it appears everywhere that matters.

**The rule in practice.** While building an analysis page, whenever you write a sentence
of the form *we cannot say whether…* or *this does not establish…*, ask whether the same
limit is already a row in `money-gaps.csv`. If it is, cite it. If it is not, add it, with:

- `side` — which kind of gap. The values are read off the data rather than mapped in code,
  so a new kind appears on the page the day it appears in the CSV. `people` was added this
  way, for the roster limits: **no FTE, no funding source, undated within the year.**
- `what` — the question that cannot be answered, phrased as a question and not as a
  complaint about a document.
- `why` — the reason, and then **`— closes:` and the single document that would settle
  it.** That last half is the most useful thing on the page: a gap with no named remedy is
  a grievance, and a gap with one is a records request.

**And the registry outranks the page.** If an analysis and `money_gaps` disagree about
whether something is knowable, the analysis is wrong until the registry is updated —
because the registry is what the request letter, the API and the gaps page all read.

## 7d. Every report is MODEL-DRIVEN. There is one kind of report, not two

**A report's figures come from a generated payload, and its furniture comes from
`fy28/src/components/report.tsx`. Nothing else is a report.**

TJ, 20 September 2026, asking why the metrics on the stabilization report did not look
like the metrics on every other report: *"this neeeds to be model driven... is this
written and built the same way the other pages are?"* It was not, and the honest answer
was no.

This site had grown **two** kinds of report:

| | how it was built | what it got |
|---|---|---|
| 29 pages | generated JSON payload → React page → `report.tsx` | `Stat` rows, `Insight`/`Conclusions` cards, `Section`, `Grain`, `Provenance` |
| 20 markdown analyses | a `.md` rendered generically by `Analysis.tsx` | prose |

`report.tsx` says in its own header why that is a defect: *"a reader takes a difference in
PRESENTATION for a difference in CONFIDENCE. Four readings of one archive must look like
four readings of one archive."* Two pipelines guarantee that difference.

**The fix was one renderer and many payloads, not twenty hand-written pages.**
`Analysis.tsx` now fetches `/data/<id>.json` for the report it is showing. If that payload
exists it renders the stat row, the grain and the conclusion cards through the same
components every other report uses, above the document. If it does not, the page is
unchanged. So the conversion proceeds one report at a time and no report is a special
case.

**What a generator must emit to be a report.** Alongside its markdown:

- `stats` — the row of headline figures. Each is a `value` already formatted by the
  generator and a `label` that carries its UNIT. A bare number in a stat box is the thing
  a reader is most likely to quote, and rule 7b forbids it.
- `grain` — what the figures COUNT, in the report's own words.
- `conclusions` — built with `scripts/conclusions.py`: `conclusion()`, `figure()`,
  `emit()`. The validator is the point of it. It enforces the 95-character claim, the
  110-character supporting line, that every digit in the prose is a registered figure and
  that every registered figure actually appears. It refuses to emit otherwise, which is
  rule 7b's *enforce the length in the generator, not by eye* made mechanical.
- `sources` and `not_established` — rule 12 and rule 7c, in the payload rather than only
  in the prose.

**The markdown does not go away.** It is what `/docs` serves, what the PDF is rendered
from, and what an agent that cannot run JavaScript reads. Generate both from ONE pass over
one set of figures — `build_stabilization.py` is the worked example — because generating
them separately is exactly how the page and the document come to disagree.

**A new report starts here.** Not from a blank page and not by copying prose: from a
generator that emits a payload, and the shared components that render it. If a page needs
furniture `report.tsx` does not have, add it there, where every report gets it.


## 7e. Label what KIND of statement you are making, when it is not obvious

TJ, 21 September 2026, after a day in which findings, status changes and finished work
all arrived in the same register and had to be read closely to tell apart:

> *"can you LABEL your statements when your commentary is changing? Can you mark
> [TASK-COMPLETE] when you think something is done? and [STATUS-UPDATE] when something
> has drastically changed status? BUT, also [TECH-REPORT] When you are just commenting on
> issues. But you dont need to label literally everything you say. Just when it seems
> necessary."*

Three labels, used in replies to him — not in commits, documents or anything published.

**These three are now GLOBAL** — `~/.claude/CLAUDE.md` carries them for every repo, along
with `[GRILLED]` and `[ASSUMING]`, which grill a claim before it reaches him. This section
stays because the worked examples below are this project's own. If the two ever disagree,
the global file is the one every other repo reads.

| label | answers | for |
|---|---|---|
| `[TASK-COMPLETE]` | *is it done?* | a thing he asked for is finished and VERIFIED — the check passed, the count moved, the page renders. Not "I have finished typing" |
| `[STATUS-UPDATE]` | *what moved?* | the work itself advanced or failed, by an amount. Ten pages ingested. Two years still refusing. A claim withdrawn. Progress **or** regress, and both carry a number |
| `[TECH-REPORT]` | *why?* | a defect, a cause, a limitation. An explanation of something, however interesting, is not a change in what is done |

**The line between the last two is where this goes wrong, and it did.** TJ, 21 September
2026: *"[STATUS-UPDATE] should only be used if you are saying something was iteratively
accomplished… You are blurring status-update with tech-report."*

He was right. "The town changed the table format after FY2023" was labelled a status
update and is nothing of the kind — it explains why a count did not move. The count
moving is the status.

**The test: can you put a number and a direction in it?**

    [STATUS-UPDATE]  422 financial pages -> 474. FY2025's budget pages now classify.
    [TECH-REPORT]    they did not before because the money pattern required cents,
                     and the warrant prints round dollars.

Same work, two sentences, two different labels. If the sentence has no count in it and
nothing finished, it is a `[TECH-REPORT]` — or it needs no label at all.

**The discipline is in NOT labelling everything.** A label on every paragraph is a label
on nothing, and the point is that the eye can skip to the ones that matter. Ordinary
answers, questions and working notes carry no label.

**`[TASK-COMPLETE]` is the one with a bar.** It means measured, not felt — rule: a thing
is done when a script says so. "Nine of nine funds have a balance for every year they
existed" is a completion; "I have written the extractor" is not, and while the difference
is invisible in prose it is the whole difference in practice.

And a withdrawal gets `[STATUS-UPDATE]` as loudly as an advance. A claim quietly dropped
is worse than one never made.

---

## 7f. A chart is a COMPONENT, never an image

TJ, 22 September 2026, looking at the budget and personnel pages: *"Are you building
these charts as images? why not build them as interactive charts?"* and then, plainly:
*"we shouldnt ever just embed charts as images. thats a bad model. we need to update them
all to actual charts."*

He is right, and the defect is the same one rule 7d names. This site had grown **two**
ways of drawing a chart:

| | how it was drawn | what a reader gets |
|---|---|---|
| the bespoke report pages | `recharts`, in a React component | hover, values, a legend that filters |
| the markdown analyses | an SVG generated by a script, embedded with `![]()` | a picture |

`report.tsx` says why that is a defect in its own header: *a reader takes a difference in
PRESENTATION for a difference in CONFIDENCE.* Nothing about the evidence behind
`/analysis/town-budgets` is weaker than the evidence behind `/athletics-money`, and one of
them was a flat image.

**An image of a chart cannot be read.** No value under the cursor, so every number a
reader wants has to already be printed on it; no series to isolate, so twelve lines on one
axis stay a smear; nothing for a screen reader but the alt text; and it does not reflow, so
the phone gets a shrunken copy of a desktop layout. Every one of those is a thing the data
could answer and the picture cannot.

**The rule.** A chart on a web page is a component rendered from the report's PAYLOAD -- 
the same `/data/<id>.json` that already feeds the stat row and the conclusions. Never a
`.svg` written by a build script and embedded as an image. One payload, one set of figures,
rendered for whoever is reading.

**The exception is not the web page.** The markdown is what `/docs` serves, what the PDF is
rendered from, and what an agent that cannot run JavaScript reads, and none of those can
run a component -- so the generated SVG stays in the markdown for them. What must not
happen is the WEB page falling back to the picture when it could draw the thing.

**How it is wired, and why that shape.** `renderMarkdown` meets `![alt](charts/foo.svg)`
and asks a registry whether a component is registered for `foo`. If one is, it renders it
in the figure's place, keeping the caption; if not, it renders the image exactly as before.
So conversion is one chart at a time, no analysis is a special case, and a new chart that
nobody has converted yet still appears. That is rule 7d's own answer -- one renderer, many
payloads -- applied to the pictures instead of the prose.

**When adding a chart to a report: write the component first.** Generating an SVG and
promising to convert it later is how twenty-five of them accumulated.

### The opening chart is the page's SIGNATURE, and it goes first

TJ, 22 September 2026: *"the point is, people remember pages based on visuals. each page's
signature is a visual basically... so the charts that are defining per page show up
first."*

**A reader remembers one image per page and almost never a sentence.** Ask what that image
is for a report before writing anything else, and put it at the top: after the summary,
ABOVE the stat row and the conclusion cards. The pie on `town-budgets` is that page --
one slice at 57% is the whole argument -- and the pie on `town-personnel` is that page:
69% schools.

**That is not where the model-driven conversion left them.** Everything the markdown
carries renders below the generated furniture, so a chart written at the top of a document
came out underneath three metrics and six cards. `Analysis.tsx` now hoists the figures
from a document's LEAD and from its short-version block and renders them directly under
the summary. Only FIGURES move; prose stays where it was, because a paragraph above the
metrics is the block of context rule 7a spent four pages removing.

**Watch for this when adding it to a page: `split` is null on a report with no
`## The short version` heading**, and the first attempt read the lead off `split` alone --
so it moved nothing on the two pages the request was about. The lead is everything before
the document's first `H2`, with or without a short version.

**And the signature does not have to be a pie.** TJ: *"OR, like the commercial development
page, a visual representation that is more interesting like buildings in proportions."*
`/commercial-development` translates an abstract quantity into a countable one -- a
projection in dollars becomes a number of BUILDINGS, at the town's own archetype values --
and that is what makes it stick. A generic chart of a specific finding is a missed
opportunity; the best signature is drawn in the units the subject is actually made of.

## 7g. IF A PROCESS ALREADY DOES IT, LET THE PROCESS DO IT

TJ, 27 September 2026, after a morning in which the backlog counters moved by about 790
items for **$49.56 of scripted spend** while an interactive session ran all day beside
them:

> *"If we have processes in place, there's no need to do your own token usage unless we
> agree. If you're telling me we have tooling to limit token usage and you just burned 25%
> of my weekly spend for no good reason, that's awful."*

He is right, and the shape of the mistake is worth stating exactly, because it does not
feel like a mistake while it is happening.

**The scripted streams are cheap and the session is not.** A votes run is ~$0.15, a
minutes run ~$0.45, and `sweep_backlog.py` is scheduled, supervised every 30 minutes and
restarts itself. A long interactive session at high context is the dominant consumer on
this account -- the measured case in this file is one session at **$329 API-equivalent,
about 65% of a week**. So the agent watching the work costs more than the work.

**And the counters do not care.** Reading OCR dumps, surveying pages and writing an
extractor with a person in the loop moves an ingestion count by two, at session prices,
while the batch beside it moves it by 790 at batch prices.

**The rule.** When a scheduled process already covers a job, DO NOT DO THAT JOB BY HAND,
and do not sit watching it. Start it, confirm it is producing -- `sweep_health.py` answers
that in one line -- and stop. Interactive work on something a process covers needs TJ to
agree to it first, in that turn, not inferred from an earlier `keep going`.

**What still belongs in a session**, so this does not become a reason to do nothing: work
no process exists for, a decision that needs judgement, and a defect a check cannot see.
Writing the extractor was legitimate. Narrating nine pages of box dumps while doing it was
not, and neither was staying in the loop once the sweeps were confirmed healthy.

**AND NEVER DO INGEST WORK IN A CONTEXT-HEAVY SESSION.** TJ, 27 September 2026:
*"You should NEVER invest with a context heavy session. All the ingest data can be done in
isolation."*

The mechanism is the part worth holding on to: **every turn re-sends the whole
conversation**, so the same work costs several times more late in a long session than it
does in a fresh one. Reading a page of OCR at turn 200 is not the same purchase as reading
it at turn 3. That is why today's attended work cost roughly four times what a thousand
unattended jobs did -- not because extraction is expensive, but because of WHERE it was
done.

Ingest and extraction have no dependency on a conversation's history. They take a page and
a rule and produce rows. So they run in ISOLATION -- a fresh session, a subagent, or a
`claude -p` script -- and the long session does the thing only it can do: decide what to
build and judge whether the answer is honest.

The test before starting any ingest work: *could this run with none of this conversation
in front of it?* If yes, it must not run here.

**When in doubt, say what it will cost before starting.** `1% of the week ~ $5
API-equivalent`; a batch is quoted in % of the week and a session is worth quoting the
same way.

## 7h. Convey it the best possible way. The template is not the answer

TJ, 25 October 2026, after a page explaining which family moves make a special education
surprise cost was built outside the framework -- a decision matrix and a month-by-month
timeline -- and read better than anything inside it:

> *"i didnt mean to constrain outcomes. you clearly have been constrained."* ... *"you can
> build diagrams, charts, or whatever on the fly even if we dont have templates for them or
> havent used them before ... for ANY page, hub we build."* ... *"since we simplified the
> pages, they are losing some of their power ... 1 paragraph, a chart, metrics, a few
> conclusions, and sources. Thats relatively boring."*

He was right, and the cause was specific. Every chart type drew a QUANTITY, every conclusion
was a metric and two lines, and every word was counted as if read top to bottom. A page whose
answer is a MECHANISM -- who pays, under which rule, from when -- had nowhere to go, so the
answer got cut to fit the slots or was never attempted.

**The rules split in two, and only one half binds.**

| integrity: fixed, every page, every block | shape: the author's call |
|---|---|
| every digit a registered figure (rule 2) | which parts, in what order, how many |
| every claim says what it rests on (rule 3) | chart or diagram type, including ones never used before |
| our reading drawn as our reading, never as the law or the record (rule 7) | how much a diagram says |
| nothing tells the reader what to do (rule 8) | |
| a chart is a component from the payload, never an image (rule 7f) | |

**The question every page gets, before it ships and when it is reviewed:** *is this information
conveyed in the best possible way? Did the template constrain it, and can we do better?* A rule
is a matrix. A sequence over time is a timeline. A comparison is two panels side by side. A
cause-and-effect list is a table of marks. A thing the reader may misread opens with its
definition. The default layout (finding, chart, facts, conclusions) is a floor, not a ceiling.

**And every figure arrives with what it means.** TJ, 25 October 2026: *"put the conclusions as
insights, following the 'what it means' pattern so we dont put important metrics without an
insight to understand them."* A reader should be able to draw a conclusion, not just see a
fact. Blocks enforce it; conclusions do not yet, and 30 of 941 carry one (26 October 2026).

**How, mechanically -- load the `building-a-page` skill** (`.claude/skills/building-a-page/`)
before writing or reviewing any page. It holds the shape-by-subject table, the blocks and where
they go, the limits the build enforces, the conventions settled on 26 October, the review
checklist and TJ's review queue. Kept there, not here, so a session that is not building pages
does not carry it.

## 8. This app explains how to fix the problem. It is not an audit

The job is helping a resident understand what would work, and what each option costs
somebody. It is not cataloguing what the town got wrong.

- A discrepancy goes in an analysis document. It reaches the app only when it changes an
  assumption.
- Findings arrive as *what this means for planning*, never as *what they got wrong*.
- Give the district credit where the budget shows them doing the right thing.

## 9. Verify against the source after writing, not before

Every figure in a finished document gets re-checked against the data by script. Not
re-read — recomputed. Prose drifts during editing, and the version that ships is the one
nobody checked.

## Push holds -- read before ANY `git push`

**None at present.** (The hold of 19 October 2026, unmasked journal names in history, ended
26 October 2026 with the rewrite: `notes/HANDOFF-HISTORY-REWRITE.md`.)

A hold recorded only in one session's memory is invisible to every other session, which is how
those names reached GitHub on 19 October. So a hold is written HERE, with its reason and what
lifts it, and removed here when it lifts. Local branches still on the pre-rewrite history --
`wip-snapshot-2026-10-19`, `gen/town-office-space` -- are never pushed.

## 10. Nothing deploys without being asked

Tag what is live. `v1` is the build before the source archive; `v2` is the current public
build. Branch for anything substantial and never reuse a branch whose history got tangled.
Verify a deploy by hashing a document from production against the archive.

---

## 11. A budget line is NET, and it is dollars — it is not what the thing costs

**A budget line is what the town has to raise, after everything else that pays for the
thing has been subtracted.** If paras cost $1.5M and the state gives $500,000, the line
says $1M. Nothing in the document says $1.5M anywhere, and nothing marks the line as net.

The district does this deliberately and says so in its own workbook. Beside general
education transportation, in the comments column: *"Does this reflect a reduction of $50K
to accound for the money planned to come from the busing fees?"* That is a budget line
being netted down by expected fee revenue, asked about by the people writing it.

So a line can rise because the thing got more expensive, or because a grant stopped
covering part of it, or because a fee stopped being collected — and all three look
identical. **A rate measured off a net line is a rate of change in the town's share, not
in the cost.** Say which one you mean, every time.

The same trap runs the other way for anything fee-funded: modelling "what fee would make
this self-funding" against a line that is already net of fees counts the fees twice.

**And above all of it sits state aid.** Chapter 70 is about **35%** of the school
appropriation -- $9,229,410 of $26,287,474 in the FY2026 revenue ledger -- and it is set in
the Governor's budget rather than by anything Lunenburg does. So even the appropriation is
not the town's bill: the town's bill is what is left after Chapter 70, and that can move
without a single cost changing. A year where aid rises and the appropriation rises with it
is not the same year as one where aid is flat and the town covers the difference, and the
expense side of the budget cannot tell them apart.

**Chapter 70 is not the same thing as state aid, and this paragraph got that wrong for
months.** It said Chapter 70 was "roughly $11.4M of a $26.6M school budget", which put the
share near 43%. $11,404,917 is the Governor's FY27 figure for **all** state aid to
Lunenburg -- the line the Town Manager's press release calls *State aid* -- and Chapter 70
is 78.7% of it. The rest is Unrestricted General Government Aid and the other cherry sheet
receipts, none of which is school money. Two real figures, folded together, and the
resulting share was eight points too high in the document that tells everyone else never to
type a figure into prose. See `/state-aid`, where both are computed.

The model handles this on the revenue side, which is right -- but note what it grows:
**total state aid, not Chapter 70 alone.** `model/finance.py` carries the aid as one
`state_aid` field, so the rate applies to the whole cherry sheet.

**That rate was 2% with nothing behind it, and it is now derived.** The obstacle was rule 1
in its purest form: the only measured series anybody had was Chapter 70 RECEIPTS, actual to
actual, and it may not be differenced against a forward rate on a budgeted TOTAL. Different
quantity, different stage. So a like-for-like series had to be built -- and it existed
unread, in the town's own `Subtotal State Aid` line, **twenty-three consecutive budget
years, FY2005-FY2027**, mostly in a single worksheet.

The rate is the MEDIAN annual step of that series, not its compound rate: the compound rate
is carried by four policy step-years of +10% or more, and projecting it forward assumes a
legislature. See `notes/findings/STATE-AID-RATE.md` and the generated, `--check`ed series
beside it. Confidence is moderate rather than high, because Chapter 70 is most of the base
and it is a FORMULA whose inputs move independently, not a trend.

**The lesson generalises past this rate.** A rate can go unexamined for years not because
nobody looked but because the obvious comparison is forbidden -- and when rule 1 blocks the
easy series, the answer is to go and build the hard one, not to leave the rate BARE. Two
other rates in this repo are in that position right now.

What must not happen is an expense line being described as "what the town pays" when three
layers sit between the two.

And you cannot see all the inputs or all the outputs, which is the general form of it.

**On the way in**, the district's budget documents show the general fund appropriation and
nothing else. Grants, circuit breaker reimbursement, school choice, revolving funds and
gifts pay for real staff and real programs and appear nowhere in them. So a line that rises
may mean the district employs more people, or may mean a grant that was paying for those
people ended and the cost landed on the town. Those are different facts about the world and
identical facts on the page.

**On the way out**, a budget shows dollars against a line and never people, children or
services. That is rule 7's territory and it is the same problem pointed the other way.

Both are why this project measures **appropriations** and says so. That is a real quantity,
it is what residents vote on, and it is what the model projects. It is not a measure of
staffing, of caseload, or of what the schools cost all in.

- Never let "the line went up" become "the district hired people". Write the first.
- Never call a budget line a cost. It is a net appropriation. If you need the cost, you
  need the grants, the fees and the revolving funds too, and they are in different
  documents.
- When a rate rests on a line, ask what else could be paying for that line, and say so
  next to the rate if you cannot rule it out.
- Name what would settle it. For funding sources that is usually DESE's End of Year
  Financial Report, which separates spending by fund. For people, the town **does** publish
  a headcount -- per-school staff rosters in every annual report, FY2011 to FY2025 -- but it
  is a list of names with no FTE and no funding source, so it bounds the question rather
  than settling it. The thing nobody publishes is which fund pays which post.
- The archive holding 245 documents does not fix this. Lunenburg publishes a great deal
  and still does not publish the mapping between the two.

---

## 12. Every source carries its address, its filename, and our copy

A figure is only checkable if somebody can get back to the document it came from. Three
things make that possible, and the first two are never optional.

**1. Where it came from, as deeply as it goes.** The direct link to the file itself, not
the page that lists it. `.../school-budget-information` is an index; it will be
reorganised, and the document a figure rests on will not be findable from it in two years.
Link the file.

Where there is no link because the document did not come off a website, say what did
produce it: a records request and its date, an email and who sent it, a meeting packet.
"Obtained from the Town by records request" is an address. "Public" is not.

**2. The publisher's own filename.** Links die — 57 of ours did in a single day, and every
one was a Google Drive link the district still holds. When that happens the only way a
resident gets the document is to ask the town for it by name, so record the name the
publisher used, not just the one we saved it under.

**3. Our processed copy, downloadable.** Whatever we actually read: the PDF, and the
extracted CSV or text if a figure was computed from one. If a number came out of a
spreadsheet we built, that spreadsheet is a source too and it gets published like any
other.

And a sha256 on all of it, because a Drive file can be replaced in place without its URL
changing.

**A link is not checked until something has been downloaded from it.** A URL whose title
matches, whose folder is right and whose date lines up is a *candidate*. The check is to
fetch it and match the sha256 against our copy — which is rule 13 applied to addresses,
because a plausible link is a derived thing being quoted as an observed one. Six district
documents once looked like they had changed when the only thing wrong was that our fetcher
did not understand Drive's `open?id=` form and was comparing a sign-in page to a PDF.

**When adding a source, add all of this at the same time.** Retrofitting provenance is how
43 of our primary documents ended up with no address at all: they were gathered before the
mirror existed and nobody wrote down where they came from. The count is on the sources
page and it is meant to be uncomfortable.

**Cite the sources.** In the analyses, beside the figure, not in a footer.

---

## 13. Quote the source, never your rendering of it

Every serious error in this project's analysis has the same shape: **something derived got
quoted as though it were observed.** Not invented — derived. There was always a real thing
underneath, which is exactly why it survives review.

Four that happened in a single day:

| quoted as | actually was |
|---|---|
| "the sheet's columns are headed `FY23 ACTUALS`" | `C4='FY23'` and `C5='ACTUALS'` — two cells, stitched together by our own script |
| "the actuals sheet" | a forward budget workbook with a column headed ACTUALS |
| "`main` is 15 commits ahead" | a number read off a summary, never off the repo |
| a verifier passing on "four of eight usable years" | the string was present; there are nine |
| `v1` summed across a run and called APPROPRIATED | the first column of each PAGE that held figures — three different printed columns |

**The rules.**

- **Cite a coordinate and the raw value.** `A20 = 'Purchase of Service (officials,
  uniforms, transportation, ice time, dues)'`. A rendered table is for reading, never for
  quoting. If you cannot give the cell or the line number, you have not checked it.
- **Check what a reader sees, not only what the file holds.** `fy27-proposals.xlsx` hides
  nine columns including FY23 actuals; our second copy of the same data hides a different
  set. Both statements "the workbook contains FY23 actuals" and "there is no FY23 column"
  were true at once. `data/document-basis.csv` records the hidden set for every workbook.
- **A check must assert the number, not the prose around it.** `verify_athletics.py` first
  checked that a sentence existed and passed while the sentence was wrong. Derive the value
  from the data and compare.
- **A positional name is not a column name.** `v1` in the annual-report extracts means
  *the first column of this page that held figures*, and the column ruler is built per
  page. Summing it across a run adds one page's APPROPRIATED to another's TOTAL EXPENDED,
  and FY2011 came out within 1% of its own printed total that way — compensating errors
  producing a check that passed because it had no power to fail. Read `column_meaning`,
  which names the columns where the table states an identity that fixes them and says
  `not established` where it does not.
- **A summary in this conversation is not a source.** After a context reset the handoff
  reads exactly like something already verified. It is a claim about the repo, not the
  repo.
- **When an extract has a total the source itself prints, reconcile to it.**
  `extract_town_ledger.py` silently dropped 16 of 67 departments — MUNIS prints zero as
  `.00` and the regex wanted a digit before the point. Nothing noticed for weeks because
  nothing compared the extract to the report's own GRAND TOTAL. It does now, and refuses
  to write if it does not tie.

The general form: **an instrument that reformats before you see it is part of the finding,
and it has to be checked like one.**

### 13a. A sheet the accounting system printed is proof. A sheet somebody assembled is not

TJ, 8 September 2026, on the athletics costs: *"this is why we need ACTUALS where possible.
hand crafted decks and sheets are not trustworthy to this degree of confidence."* And
immediately, correcting the first draft of this rule: *"well. not all sheets of course. hand
crafted sheets not backed by a financial printout. munis sheets are proof for instance."*

**That correction is the rule.** The first draft condemned spreadsheets as a class, and this
archive disproves it in one query: **seven of the ten `ledger` documents here are `.xlsx`** —
every MUNIS export, the fund cashbooks, the year-end expense report. The strongest evidence
we hold is spreadsheets.

**So the axis is not the file format. It is whether the accounting system produced the
figure or a person did.** A MUNIS export is a printout of what the books say, and it
arrives with the marks of that: account numbers, periods, warrant references, and totals
the system foots itself. A workbook someone built to answer a question is an argument —
useful, often the only thing available, and carrying exactly as much authority as the
person who typed it.

`document-basis.csv` already encodes this and does not look at extensions.

**The worked example, because it is the sharpest this archive has.** Three published figures
for one quantity — what Lunenburg athletics cost in a year:

| figure | document | how it reached us |
|---:|---|---|
| $185,355.62 | *"Cost of Running Each Sport"*, attributed to a PowerPoint to School Committee, 1 May 2024, slide 12 | transcribed by the district into the PDF below; **the deck itself is not in the archive** |
| $275,947.63 | `FY24 Programmatic Cost`, in *Athletic Program Costs by Sport*, with the FY26 budget materials | published, held, `sha256 218d17e1…` |
| $349,145.39 | `Total Expenses`, the district's own by-sport workbook | **records request; no publisher address exists** |

**Highest against lowest is 1.88x.** Per sport it is far worse: Outdoor Track is $15,221.50
in one column and $1,146.00 in the other, a factor of thirteen.

**And the first two are printed side by side, in one table, on one page.** This is not two
documents that happen to disagree and nobody noticed. Whoever built that page was looking
straight at $19,805.28 next to $25,774.45 for football and left both there.

**What follows for the work.**

- **A figure a person assembled is `stated`, however official the document looks.** Slide
  numbers, letterheads and budget-packet covers are not provenance. The question is always
  what produced the number, not what it was printed on — and not what it was saved as.
- **A figure the accounting system printed is evidence, in whatever format it arrives.**
  A MUNIS `.xlsx` is not a spreadsheet in the sense this rule warns about. Check for the
  system's own marks: account codes, a period, a warrant or journal reference, and a total
  the report foots itself.
- **Where a ledger exists, prefer it, and say when one does not.** Athletics is the only
  programme here where any transaction-level record exists at all, and even that one — the
  revolving fund's cashbook — cannot attribute a payment to a sport: 173 disbursements,
  zero mentions of any sport.
- **Never average or reconcile disagreeing hand-built figures into one number.** Publish
  the spread. A reader deciding which sport to cut is better served by *"between $1,146 and
  $15,221, and the town has not reconciled them"* than by any single figure we could
  choose, and choosing one would be us adding a claim the documents do not make.
- **Ask for the ledger.** The remedy is almost always a report the accounting system can
  already produce: the accounts-payable detail behind the warrants, the year-end expense
  report by department. Both are named on the records request for this reason.

The general form: **a hand-built sheet is an argument someone assembled; a printout from
the books is a record of what happened.** They arrive in the same file format, open in the
same program, and are not the same kind of thing. Ask which one produced it, never what it
was saved as.


### 13b. Reading a table off a photograph: measure the page, never guess at it

Half the tables in the annual reports are scans. Four rules got FY2020's stabilization
funds out of one, after every tolerance-based attempt failed, and each replaces a constant
somebody would otherwise tune by hand.

**1. MEASURE THE ROTATION, DO NOT FIGHT IT.** A scan is slightly turned, so a row's own
observations do not share a `y` and two adjacent rows do. There is no tolerance that
works: at 0.004 two funds merge, at 0.003 one fund splits from its own account number.
The rotation is recoverable from the page itself — take each figure's nearest neighbour
to the right, take the MEDIAN slope between them. FY2020 page 41: **−0.01033 from 158
pairs.** Then `Y = y − slope·x`, and in that coordinate a row shares a value and ordinary
clustering works.

**2. THE BAND IS HALF THE PAGE'S OWN ROW PITCH.** Not a constant. A guessed 0.004 held
some rows together and split others — and what it lost from the long rows was `ending
cash` and `ending market`, the two columns everything is checked against. Measure the
median gap between consecutive rows and halve it; a page set in a larger face then needs
no new number.

**3. PLACE FIGURES BY COLUMN POSITION, NEVER BY ORDER.** A fund with no activity prints
nothing in those columns. Take the figures in order and every one lands under the wrong
heading from the first gap onward. Assign each to the column whose centre it is nearest,
and let an absent column stay absent.

**4. NAME COLUMNS FROM A HEADER YOU READ AND WROTE DOWN.** Never inferred. Two attempts to
name them from the heading words automatically produced confident nonsense — three columns
all claiming to be `begin_principal`, and a proportional word-split turning `TRANSFERS OF
TRANSFERS OF ENDING CASH` (one OCR observation spanning three columns) into `TRANSFERS
PRINCIPAL / OF EARNINGS / TRANSFERS VALUE`. This is rule 13's own trap wearing a new coat:
**a position is not a name**, which is why `column_meaning` exists. Read the printed
header, write the layout down per year, and let a year whose column count disagrees be
refused rather than aligned.

**And the layout is a HYPOTHESIS that the document tests.** Nine columns read off FY2014
were proposed for four other years. FY2015 and FY2016 accepted them — ten to twelve rows a
page closing. FY2017 and FY2022 refused them, one row and none, so those headers differ
and wait to be read. **A wrong layout cannot make real arithmetic close**, and that is the
whole reason any of this is safe to do with OCR: the cache visibly contains
`S2,041,061.72`, `$1,968,108,91` and `$9,587,16`, and a misread digit does not survive an
identity the table states about itself.

So the order is: measure, band, place, name, then **prove every row and write only what
proves**. `scripts/read_trust_table.py` is the worked example.


### 13c. A PATTERN THAT DOES NOT MATCH IS NOT AN ABSENCE. Go and look at the page

**Every year of these documents is laid out differently, and a reader who assumes
otherwise reports missing data that is sitting on the page.**

TJ, 21 September 2026, after I told him four separate times that a figure did not exist:

> *"i think this is a recurring problem. yo uare thinking there is standardization when
> there isn't. every year they produce a different format. or something like that. so we
> cant lose data because you tried to fit it to a format and couldn't. you have to look
> just like i do. you have to do your own search when things dont fit the pattern. dont
> make me do it"*

He was right every time, and the failures were not subtle once anybody opened the page.
In one afternoon, on one fund:

| what I reported | what was actually true |
|---|---|
| "FY2019 has no general Stabilization row" | it is on a different page, labelled just `STABILIZATION` with no bank in front of it |
| "FY2022–FY2025 are missing" | FY2022 and FY2025 were in the data; I had read the poorer of two code paths |
| "fourteen pages came out upside down" | none of them had; the test matched round thousands |
| "the extractor publishes nothing for FY2023" | that report prints TWO trust tables with different headers, and `LAYOUTS` was keyed by year, so one was always wrong. **The general Stabilization Fund is on the WIDER one** -- the fourteen-column `TRUST FUNDS / FISCAL YEAR 2023 SUMMARY / Page 4 of 9` at pdf page 51, not the eight-column `HELD BY OTHER BANKS` at page 49. This line said "the narrower one" until 1 October 2026, when FY2023 was read and closed: five funds, both printed identities, footing to the page's own SUBTOTALS, and corroborated by the `Treasurer's Cash as of 6/30/2023` listing on page 48 printing `Bartholomew Stabilization Fund 2,730,600.73`, identical. A rule written to stop a wrong claim about a document carried one |
| "the column does not foot, so the year is unreadable" | a comma was scanned as a full stop, so a million dollars never matched the money pattern |

**The common shape: a matcher failed, and I reported the failure as a fact about the
town.** A regex that finds nothing, a heading that is absent, a layout that refuses —
each of those is a statement about OUR INSTRUMENT. Rule 13 already says an instrument
that reformats before you see it is part of the finding; this is the same rule for an
instrument that finds nothing.

**What to do instead, in order.**

1. **Open the page.** Dump every box on it, labels and figures, top to bottom. Not the
   filtered view the extractor uses — the whole page. Most of these were visible in the
   first ten lines of that dump.
2. **Search for the thing, not for the pattern.** `grep -i stabiliz` across every page of
   the report, then look at what came back. The bare `STABILIZATION` row was two pages
   from where the extractor was looking and unreachable by any refinement of it.
3. **Assume the format changed.** Layouts here vary year to year and sometimes WITHIN one
   report: FY2023 prints a fourteen-column trust summary and an eight-column "held by
   other banks" table, and `LAYOUTS` was keyed by year, so one of them was always wrong.
4. **Then, and only then, say a thing is not published** — and say which pages were
   looked at.

**And never report "missing" from a count.** A dataset with no rows for a year, a queue
saying `unread`, a payload with a short series: all three are things we built, and each
was wrong about the archive today. Check the document before describing what the town
did or did not print.

The cost of getting this wrong is not a slow afternoon. It is telling a resident the town
does not publish something it publishes every year.

### 13d. A PDF IS A SCAN ONLY IF ITS PAGES SAY SO. Never because an extractor got nothing

TJ, 4 October 2026: *"just make sure they aren't digital-first. you made that mistake
before"* -- and then: *"put this as a rule somewhere in the extraction/ingestion flow, to
validate digital text vs assuming."*

Four scripts decided "scan" because an extractor returned fewer than about 200 characters.
That measures the EXTRACTOR. A digital PDF with unmapped fonts returns nothing; so does text
drawn as outlines; so does a reader that failed to open the file. All three were called
scans, OCR'd, and labelled `ocr` as if a camera had been involved. It is 13c pointed at a
document.

**`scripts/pdf_kind.py` is the only answer to "is this a scan".** It reads each page's
STRUCTURE -- fonts, raster images, vector paths -- and reads its text with TWO extractors
before calling any page unreadable. A document is `digital`, `scan`, `mixed`,
`digital, text unreadable`, `outlines` or `blank`, and the label on any OCR says which.

**`mixed` is the case the old rule could not see at all.** Twenty-eight of the Finance
Committee's PDFs are digital documents with some pages that are only pictures -- the FY27
school budget presentation to the committee has 19 of 51. A whole-document character count
passed every one of them as digital and never read those pages. `pdf_kind.extract_text()`
keeps the text layer where it reads and takes OCR only for the pages that need it.

**The ingest screen fails closed on it.** `pii_screen.py` holds any PDF with even one page it
cannot read, because a picture page is exactly where a screenshot of a staff list would be.

Do not write a new character-count test. Call `pdf_kind`.

### 13e. The raw is private. The public copy is ours. The decision is written down

TJ, 4 October 2026, after a records-request delivery put one employee's number, start date,
grade and salary into the public bucket -- whose lock refuses deletion unless it is
deliberately lifted (see *Removing a document* below): *"we
probably need a REDACTION mechanism, so that we can have a private storage of the raw, and a
public version with all redacted PII removed. This will come up in MUNIS data too."*

- **The gate.** `ingest.stage()` calls `redact.gate()` on every document with no public
  upstream -- a records request, an email, a MUNIS run. Anything `pii_screen.py` flags or
  cannot read goes to the PRIVATE bucket (`lunenburg-budget-private`, no public URL) and
  waits as `pending`. Nothing reaches the public bucket until `sources/data/redactions.csv`
  says `publish`, or as our redacted copy.
- **The redacted copy** is built by `redact.py` from the raw and a declared rule,
  deterministically, and `--check` rebuilds it byte for byte. It opens -- first sheet, first
  page, first slide -- with **UNOFFICIAL DOCUMENT, REDACTION DONE BY
  LUNENBURGBUDGETPROJECT.ORG** and *Official document available upon request*, TJ's words.
- **Redact quasi-identifiers, not only names.** Job title and hire date name everybody in a
  department of four. A document whose rows cannot be made anonymous is WITHHELD.
- **A redacted PDF is rebuilt as images.** Black boxes over a live text layer -- overlay
  redaction -- hide nothing from anybody who selects the text.
- **Every redacted output is screened again**, and every mask pattern must be gone from it,
  or nothing is written.

A screen is not a clearance: it finds per-person TABLES and identifier PATTERNS, and cannot
recognise a name in running prose. The register's `decided_by` says who looked.

**MUNIS: PROCESS, VERIFY IT IS SAFE, PUBLISH -- AND ONLY THEN BUILD AGAINST IT.** TJ,
6 October 2026: *"once we process the data, and verify its safe, it can all be made public.
dont build against the private data. confirm the data is safe, make it public, then build
against it. the town manager doesnt need to confirm. we are responsible for checking
ourselves."* `redact.gate()` holds every key under `town-ledgers/` as `pending` whatever the
screen finds, because a clean screen is not the check: it cannot see a person's name in an
account description or a journal reference. The check is ours -- every distinct text field
read for a person -- and it ends in `publish` in `redactions.csv`. Until then nothing is
analysed, extracted into `sources/`, loaded into `lunenburg.db` or put on a page. The fact of
a delivery (the register row, the filenames) is public from the start.


---

## 14. After correcting a large error, re-examine everything it was explaining

**A residual is a slush fund. It silently pays for every input you got wrong, and shrinking
it presents the bill.**

On 30 August the FY26 athletic fee was corrected from $250 to $325 — a right number from the
wrong year. The calibration factor fell from 1.4520 to 1.1316 and the surcharge gap from
$58,815 to $21,974. No published revenue figure needed to change, because the fee model is
anchored to a measurement and the calibration absorbs the difference either way.

What the correction actually did was make a *second*, older error visible. `SIBLING_MIX`
assumes 30% of participations take a sibling discount; the district's own fee-category
counts show about 7%. At a 45% unexplained residual an error that size is invisible. At 13%
it is the obvious next question. The term for this is **error masking**: a dominant error
conceals subordinate ones, so fixing the big one does not only improve the number — it
changes what is *findable*.

Two things follow, and both have already gone wrong here:

- **Anchoring makes outputs robust and inputs untestable.** An input wrong by a factor of
  four moved the published revenue figure 1.4%, because the calibration moved the other way.
  Compensating errors. Nothing on the site would ever have flagged it, which is why the
  inputs have to be checked directly rather than by whether the answer looks right.
- **The prose that justified a choice outlives the number it rested on.** That commit moved
  four figures and zero sentences, so the site went on publishing "45%" and an arithmetic
  impossibility that no longer existed.

So: after any correction, run `python3 scripts/build_show_your_work.py` and read the diff.
It is computed from the model, so it states what the model now believes rather than what
somebody wrote when it believed something else. `audit_provenance.py` fails if it is stale.

---

## 15. There is a written process for producing an analysis. Follow it in order

`notes/process/WRITING-AN-ANALYSIS.md` — eight steps, and the order is the point. Data in before
a sentence is written; decompose by what the money buys before looking for a headline;
both halves of every section including what it does not show; the document that would
settle each open question; the verifier written before publishing rather than after; the
persona review; charts only where the finding is visual; then publish.

The table at the end says why each step cannot move. The short version: a sentence written
before the query gets defended instead of tested, and a verifier written after the prose
asserts what you wrote rather than what is true.

## 15a. A verifier checks the figures. It cannot check that anybody's question was answered

Every figure in a finished analysis is recomputed by a script. Nothing checks whether the
document answers what the reader came with -- and a report that is entirely correct and
answers nobody's question is a failure no verifier can catch.

`notes/process/PERSONAS.md` carries six readers and one test each, and every concern in them is
quoted from a real public meeting rather than invented. Run it before publishing an
analysis and again after any substantial change.

The step that matters most is the one a writer cannot do for themselves: **for every
category a report says underspent or overspent, search the meeting archive for what people
said about that thing in the same year.** The first run of this found a booster president
telling the School Committee *"we currently have more heads than we have helmets"* in the
same year the report described an athletics equipment line spending 44% of its budget. The
report held both halves and had not put them together.

Three of the six tests are about what a document OMITS. Omissions are exactly what does not
show up on re-reading your own work.

---

## The annual town reports

**AND 52 OLDER ONES, 1959-2010, ARRIVED 28 OCTOBER 2026 -- FINISHED 30 OCTOBER 2026: every
financial page `proven` or `blocked` (`page-blocked.csv`). Start at
`notes/HANDOFF-ANNUAL-REPORTS-1959-2010.md`.** Read by Textract, not Vision; extracted by
per-report workers into `sources/data/report-tables/<year>/` and merged. What follows about
"finished" is about the FY2011-FY2025 set only.

Sixteen of them, FY2011-FY2025, read page by page into 25 datasets.

**THEY ARE FINISHED. 15 of 15 years, 2 October 2026.** Every financial page of every annual
town report, FY2011-FY2025, is `proven` or `blocked`.

    python3 scripts/annual_report_progress.py   # prints: Every year is done. Nothing to pick.

**DONE MEANS EVERY PAGE IS `proven` OR `blocked`. IT DOES NOT MEAN EVERY FIGURE IS IN A
DATASET.** Three pages across fifteen years are closed WITHOUT being read, each registered in
`sources/data/page-blocked.csv` with its reason and the ONE document that would settle it:
FY2023 p25, a 93 dpi scan whose digits are below the resolution of the file; and FY2016 p23
and p49, which the TOWN printed short -- p49 prints four of the eight columns its own run
uses, and p23 is page one of a receipts list that needs two with no continuation anywhere in
its 204 pages. For those three a better scan is not a remedy that exists; the remedy is
another document.

**AND DO NOT READ THE ROW COUNTS AS A BACKLOG.** `status` on a `report_*` row says whether a
GENERIC extract was exhausted, and a page read by eye SUPERSEDES that extract without
emptying it -- so `notes/generated/AGENTIC-BACKLOG.md` still shows thousands of unreconciled
rows on years that are finished, and now says so at the top. ROW GRAIN IS NOT PAGE GRAIN,
and reporting the first as the answer to the second cost an hour on 1 October 2026.

**WHICH YEARS ARE DONE, AND WHICH IS NEXT -- one command, and it is the only answer:**

    python3 scripts/annual_report_progress.py

**A year is DONE when EVERY financial page the map holds for it is `proven`**, meaning the
page closed on an identity the page itself prints. ALL FIFTEEN are done. Row-level `status` across
the `report-*` CSVs answers a DIFFERENT question -- whether a table was exhausted -- and a
year can be done with most of its rows still `check failed`. Reporting the second as the
answer to the first cost an hour on 1 October 2026, and then led to the ingestion dashboard
being called coarse when it was right. Never derive which years are done from commit
messages; `git log | grep` is an instrument, and rule 13c applies to it. The story is
`notes/PLAN-ANNUAL-REPORTS-TO-ZERO.md`, learning loop entry 9 -- and that PLAN is what to
read before working a year, in front of everything else.

**The other entry point is
`notes/reference/ANNUAL-REPORTS.md`** -- what exists, where each thing lives, what state it is
in, and what is still uncaptured. It is generated, so its counts cannot drift.

Do not go looking for this in the CSVs. Three things there are easy to get wrong and all
three are written down:

- **`v1` is an ordinal, not a column.** Read `column_meaning`.
- **`status` splits the rows into three.** `checked`, `check failed`, `no check` -- and
  nothing may be aggregated without splitting on it.
- **How many copies of each thing exist is in `notes/reference/BACKUP.md`, and it is
  GENERATED.** Do not restate the count here. This line used to read *six of the sixteen
  source PDFs exist only in this working tree*, which was true until the archive moved to
  R2 on 5 September 2026 and false every day after — and on 23 September it made somebody
  raise a false alarm about the annual reports being unbacked. They are all in the bucket,
  byte-verified. Rule 2 is not only about the model: a figure typed into prose is the one
  thing here that can be silently wrong, and this file is prose that ships.

## Nothing is downloaded without being saved: `ingest.land`

TJ, 25 September 2026: *"i want to make sure any file we downoad is ALWAYS saved before we
can even think of deleting it or cleaning a repo..."*

**THE INVARIANT: a document is in `sources/` if and only if it is in the bucket.** One
sentence, and it is an invariant rather than a procedure -- which is the difference between
a guarantee and a habit. `check_archive_backed_up.py` answers it offline in under a second.

`scripts/ingest.py` is the one door. `stage()` validates and writes atomically into
gitignored `build/ingest/`, and registers the document as IN FLIGHT in the TRACKED
`sources/data/ingest-pending.csv`. `secure()` pushes it, reads it back, compares, and only
then moves it into `sources/` and writes the manifest row. A failed push leaves it staged
and pending, and the gate refuses every destructive operation while that is true -- so the
next run retries rather than the next run destroying.

**What it replaced, and why every part of it mattered.** Fifteen fetchers wrote straight
into `sources/` -- a git working directory -- and the durable copy was step 10 of 10 of the
daily run, with its failure ignored. So the archive made its promise when bytes hit the
disk and only kept it an hour later. In that window: six agendas sat unbacked for days, 39
documents were orphaned in the bucket, `git clean -fd` would have deleted a fetched `.csv`
(untracked AND not ignored), and the write was not atomic, so a crash left a truncated file
at the real archival name.

**And the catalogue only ever names what is held.** A document still in flight keeps an
EMPTY `path` in `sources/meetings/index.csv`, which is exactly what `fetch_agendas.py
--backfill` looks for -- so tomorrow retries it. That is what stops *catalogued but not on
disk*, which cost an afternoon on 25 September.

**A PARTIAL TREE MAY NOT PUBLISH A COUNT.** `build_minutes_searchable.py` defines `held` as
*index rows whose file exists on disk*, so the figure is about THIS CHECKOUT and reads as a
figure about the archive: the same published sentence had three defensible values in one day
-- 12,055, 12,072 and 12,088 -- across three trees. It now calls `archive_storage.incomplete()`
and REFUSES, naming the file and `sync_archive.py --pull`. Any other generator publishing a
corpus count should do the same.

**A RENAME ORPHANS AN OBJECT.** The bucket's lock refuses deletion in ordinary use, so
changing a document's filename leaves the old object there, unfindable
because the bucket cannot be listed. Eleven went that way when a slug changed how it renders
an apostrophe (`town-manager-s` to `town-manager-39-s`). `sources/data/archive-orphans.csv`
is the register, matched by **sha256** rather than by name, and it says `superseded_by` where
the same bytes are held under another key -- the only possible remedy, and the same move
`document-defects.csv` makes for a document that cannot be corrected.

**The refresh is VERIFIED, not forced.** `daily_refresh.sh` used to open with `git reset
--hard` and `git clean -fd`, and the reason was stated 120 lines below at the commit: `-A` is
safe because the top of the run destroyed anything else. So the destruction was not
protecting anything -- it was buying an assumption. Both scripts now STOP if the refresh tree
is not pristine and change nothing at all, which buys the same assumption for free. There is
no `git clean` in either any more. A dirty tree is abnormal and gets a person, because
self-healing is exactly what let two weeks of manifest drops go unnoticed.

## Where the bytes are: git holds what changes, R2 holds what must not

**The documents are not in this repository.** Every PDF, spreadsheet, Word file and
PowerPoint the town, the district and the state published -- 1,762 files, 1.38 GB -- lives
in a public R2 bucket. A fresh clone gets `sources/` with its manifests and its extracted
text and holes where the originals should be:

    python3 scripts/sync_archive.py --pull   # fetches what is missing, verifies each sha256

**Nothing about the published addresses changed.** `/docs/<path>` still serves every
document; `fy28/functions/docs/_bucket.js` streams it out of the bucket under the same URL,
and sets `x-archive-source: r2` so a test can tell which copy answered. A URL is an
interface and where the bytes are kept is an implementation detail -- which is also why
`llms.txt` can keep telling agents to cite those addresses.

**The line between the two is the line rule 12 already drew.** A document somebody else
published does not change: if our copy ever differed from what we uploaded that is a
defect, not a revision, and the bucket freezes it -- a lock blocks deletion *and*
overwriting for ten years across every prefix. An OVERWRITE is refused loudly (`HTTP 409, the
object is locked by the bucket policy`). **A DELETE is not: R2 answers it with success and
keeps the object** -- found on 5 October 2026, when a delete meant to prove the lock was
working reported success and the object was still listed and still served. So whether an
object is gone is answered by LISTING it afterwards, never by the response.

**Removing a document: the lock is a setting, not a law of nature.** Ten years is the
lock rule's age, and the account owner can lift it. TJ, 6 October 2026: *"we HAVE to have a
way to delete things. it can't truly be permanent."* There is ONE way, and it is
`scripts/takedown.py`, documented in `notes/process/REMOVING-FROM-THE-ARCHIVE.md`. In
outline:
- a private copy first;
- a row in `sources/data/takedowns.csv`;
- the site answers **410 Gone, with the reason** (deploy);
- a FRESH verified `backup_snapshot.py`;
- `--delete`, which lifts the lock, deletes, confirms by listing, and restores the lock in a
  `finally`.

Use it when a public document holds private information. Never delete by hand, and never
write "cannot be deleted" here again -- that sentence sent two agents the wrong way on 19
October 2026, when three workbooks naming families were treated as permanent. Not reached by
any deletion: git history, search engines, the Wayback Machine.

Everything we
derive from
those documents does change -- the extracted text when an extractor improves, the analyses
when a rate does -- and git versions that properly: atomic across files, with a message,
reviewable before it merges. `archive_storage.frozen()` is where that line is drawn, in one
place, so the manifest, the push, the reconciler and the site build cannot disagree about
it.

**Two consequences worth knowing before they surprise you.**

- **An object in the bucket cannot be corrected, only superseded under a new key.** A push
  that finds different bytes already stored under a key stops and says so rather than
  trying to fix it.
- **The bucket also holds a frozen snapshot of our derived files**, taken 5 September 2026,
  because the archive was pushed whole. Nobody reads it -- the site serves the git version,
  which is checked first -- and `check_archive_storage.py` reports it as *an older
  rendering*, separately from real failures, so it cannot be mistaken for one.

**A branch switch across the untracking commit deletes the documents from this disk.**
`git rm --cached` keeps a file; moving between a commit that tracks it and one that does
not does not. Nine contract PDFs went that way the day it was done. After any checkout or
merge that crosses it, run `sync_archive.py --pull` and then `build_source_index.py`, which
is the check that catches it -- *catalogued but not on disk*.

`sources/data/archive-manifest.csv` is the index into all of it, tracked in git because a
clone held only in R2 would have to ask the network what exists before it could ask for any
of it. It is published at `/data/archive-manifest.csv` and deliberately **not** stored in
the bucket: an object there cannot be updated once written, so a manifest inside it would
be permanently out of date about its own contents.

## A report can be published and linked from nowhere

`sources/analyses/UNLISTED` names the analyses that exist, are served at their ordinary
address, and have no door on the site. TJ has twice asked for one: *"feel free to publish
it when you're ready, but not linked to any reports page. Just give me the link to read
it."*

The first time that was done by not adding it to the index, which is not a decision anybody
can find -- and FOUR generators enumerate `sources/analyses/*.md` independently, so the next
run of any of them would have relisted it. `build_reports_index.py`, `build_sitemap.py`,
`fy28/scripts/prerender.mjs` and `build_master_report.py` all read that one file now.

**Unlisted means three doors shut, not one.** Not in `/reports` and linked from nowhere; not
in `sitemap.xml`, so it is never pushed to IndexNow -- unlinked and indexed is not unlisted;
and no static twin in `dist/`, the same trade the site already makes for unlisted routes and
draft posts. It IS still served, hashed and citable, because rule 12 does not bend for a
draft. Deleting its line is how a report joins the site.

**Four doors were open at first, and each was found only by looking for it.** The page was
out of the sitemap while its `/data/<id>.json` payload and its `/docs/analyses/<id>.md` copy
were still in it; the control file itself was catalogued and published at
`/docs/analyses/UNLISTED`, naming the slug; and `/what-it-all-adds-up-to` -- a public page --
listed the report with a link, because the master report enumerates the directory too.

A PDF and the `/docs` copy are NOT doors. They are serving formats for a document meant to be
readable and citable; what makes a report listed is something LINKING to it.

## The budget feed has its own guideline

`notes/process/BUDGET-FEED-GUIDELINES.md` is how a budget season page is read before it
ships -- three passes as the parent whose child's programme is on the list -- and
`notes/process/BUDGET-SEASON-MODEL.md` is what the page is built to. Both are scoped to
the feed and its season files; nothing in them is a rule for the rest of the site.

## Picking up mid-stream

`notes/HANDOFF-AGENT-ACCESS.md` covers one workstream on its own: making this archive
usable by an assistant. What exists, what is not solved, what to do next, and the four
separate agent failures in one day that prompted it — none of which was the agent's fault.



`notes/HANDOFF-WAYFINDING.md` is the running doc for the site's reading experience: real
links, the ranked front page, per-page reading time, the **short version** every page
declares (five-minute budget, ratcheted) and the **fold** behind it. `notes/process/READING-FLOW.md`
is the design it follows -- three readers, their paths, what each page owes them.

`notes/HANDOFF-MONEY-IN.md` is the running doc for the current workstream: modelling every
route money takes into the school budget, what has been established, and what is explicitly
not. It is where to start if the work in progress is the money-flow page.

`notes/HANDOFF.md` is written to survive a context reset: which branch is live, what is on
the working branch and not yet deployed, the open decision, and — most importantly — the
list of claims that are NOT established, so they do not get restated as fact by somebody
arriving fresh.

---

## The shape almost every defect here has taken

Thirteen were found in a single day, 5 September 2026, and they are one bug wearing
different clothes: **something derived was written down, the thing it derived from moved,
and nothing connected the two.**

Three sub-causes. Each has a rule, and the rule is the preventable part:

**1. A LOCATION WAS HARDCODED where location is not identity.** This archive is keyed on
provenance and re-files documents on purpose -- that is what `views/` is for. So a literal
`sources/<folder>/` in a script is a latent break with a date on it. It broke
`build_dataset_provenance.py` (0 of 225 rows resolved, silently), eight annual-report
pipeline scripts, `document-basis.csv`, and the crawler index list in `build_db.py`.

> Read the manifest, or glob every `sources/*/index.csv`. Never name one folder.

**2. A FIGURE OR A NAME WAS TYPED into prose.** Rule 2 says never type a figure, and it
was applied to the projection and to nothing else. So llms.txt carried a document number
that renumbering had moved, the /minutes 404 named a bundle that splitting had deleted, and
a caveat quoted a series -- `0, 5, 4, 4, 0` -- typed from a field the same commit had
already fixed, repeating the undercount it existed to explain.

> Rule 2 covers every generated surface, not just the model: llms.txt, the READMEs, the
> caveats, the worked examples, the fixtures a check asserts against.

**3. A JOIN THAT MATCHES NOTHING LOOKS EXACTLY LIKE DATA THAT IS ABSENT.** Four of the
thirteen were silent zeros: the provenance join, `link_state`/`copy_state` on 613 of 616
documents, the roster classification, the crawled-document branch that never consulted the
status files at all.

> A join whose result is used must assert that it matched. `build_dataset_provenance.py`
> and `build_db.py` now refuse to write rather than write nothing.

**And the meta-cause: every one was found by a person or an agent, never by a check.**

    python3 scripts/check_generated.py

runs the `--check` of every generator and fails if any output no longer reproduces. It is
the mechanical half of the answer -- if an input moved, the output stops reproducing and
this says so. It cannot catch a figure typed into a sentence that nothing regenerates,
which is why the caveats and the worked examples are now derived rather than written.

It earned itself on its first run: a recursion that was splitting split files into
further parts, and a staleness check comparing a `\r\n` file against a newline-translated
read, so it had been reporting a clean file as stale every time.

## Reachability: some agents cannot fetch this site at all

Not because anything is wrong with it. It answers in under 300ms, to any user agent, with
no bot protection — checked. Their sandbox has an egress allowlist and this domain is not
on it: `x-deny-reason: host_not_allowed`. Nothing published here changes that.

Three things do, and all three are now true:

**1. The GitHub mirror is complete, and said out loud.** Every static API file, the
extracted text, the manifests and the analysis database are committed, so
`raw.githubusercontent.com/tjloughlin16/lunenburgbudgetapp/main/<path>` serves them.
1,366 files. `check_github_mirror.py` fails if one stops being committed, because a
fallback that has quietly gone incomplete is worse than one never promised. The only thing
that cannot be mirrored is `/api/query`, which needs a database at request time — an agent
on GitHub queries the committed database instead.

**2. The sitemap carries the endpoints, not just the pages.** An agent reported that its
fetcher accepts only URLs that came from a prior SEARCH RESULT — not links extracted from a
page it had already fetched. It had the homepage open, with `/agents` and `/api/index` as
real anchors, and was still refused. So being a link is not sufficient; being INDEXED is
what reaches that tool, and the sitemap is where that starts. It now lists 67 URLs: 24
pages and 43 addresses a program needs.

**3. Being indexed is pushed, not waited for.** `check_sitemap.py --submit` sends the
sitemap's URLs to IndexNow, which Bing, Yandex, Seznam and Naver honour — Bing matters
because several agent search tools are built on it. Google does not participate; for
Google, **Search Console is the only honest answer** to "has this been indexed", and it
needs the domain verified. Nothing here scrapes a `site:` query and calls the count a
measurement.

**4. A URL the user pastes is always fetchable.** That is the immediate unblock when an
agent is refused, and it is worth telling people: paste `/api/tables` or a query URL into
the prompt and the tool will take it.

## What /api/query can cost -- and since 9 October 2026, it CAN cost money

**THE ACCOUNT IS ON WORKERS PAID SINCE 9 OCTOBER 2026** (TJ upgraded after the search
database passed the free plan's 500 MB cap). D1 no longer STOPS at a daily limit: reads and
writes are a monthly allowance, and usage past it is BILLED per million rows. A database may
now reach 10 GB. So the failure mode below has flipped -- a runaway query no longer takes the
site dark until midnight, it runs up a bill nobody capped -- and the four protections listed
below (the read estimate, the edge cache, the LIMIT, `rowsRead`) are now the spending guard.
A full `sync_d1.py --full` (~320,000 writes) now fits comfortably; it no longer has to be
rationed across days. The Pages 20,000-file limit is NOT lifted by this plan (that needs Pro).
What follows is the free-plan history, kept because it explains why those guards exist.

**On the Workers Free plan D1 does not bill. It stops.** 5 million rows read a day, 100,000
written; past either, queries fail until tomorrow. That is what happened on 5 September --
four full database re-imports, about 95,000 writes each, and the day's budget was gone. It
cost availability, not money.

**The billable unit is ROWS READ, and it is not the number of rows you get back.**
`SELECT fy, COUNT(*) FROM report_appropriations GROUP BY fy` returns 14 rows and reads
9,330. A caller cannot tell the difference and should not have to, so every `/api/query`
response now states `rowsRead`.

**The READ limit is the exposure, and it is tight.** 5 million rows a day sounds large and
is not: one join across two tables here reads 19,006, so **263 of them takes the endpoint
dark until tomorrow.** One enthusiastic agent could do that in minutes. Cloudflare publishes
no usage or spending cap for D1, so the cap has to be ours.

Four things keep it bounded, in order of how much they do:

0. **A query estimated to read more than 250,000 rows is refused before it reads
   anything.** `build_api.py` writes the row count of every table into
   `functions/api/_tablesizes.js`, and `query.js` reads the tables a statement names and
   bounds the worst case -- a scan of each, multiplied per join. It is an ESTIMATE and
   says so; the true cost is only knowable afterwards, which is what `rowsRead` reports.
   A three-way join across the big tables estimates a billion rows and is refused with the
   reason and a suggested narrower route.

1. **Identical queries are served from the edge.** The data changes only when the database
   is redeployed, so two identical queries an hour apart must return the same rows.
   `caches.default`, keyed on the statement and its parameters, ten minutes. A public
   endpoint answering the same question repeatedly is the whole shape of the load, and
   this removes nearly all of it. `x-query-cache: hit` says when it fired.
2. **One statement, SELECT only, LIMIT capped at 1,000.** That bounds the response, not
   the read -- see above -- but it stops the obvious abuses.
3. **`rowsRead` is published**, so an expensive query is visible as expensive rather than
   discovered on a bill.

**If this ever moves to Workers Paid the exposure changes**, and it is worth knowing the
shape before it does: 25 billion rows read a month are included, then $0.001 per million.
Sustaining an overage needs roughly 9,600 rows read every second for a month. Cloudflare
publishes no hard spending cap, so the protection is the cache and the query limits rather
than a budget setting.

## Several agents in one working tree

Four agents worked this repo at once on 9 September 2026 and every problem that caused was
a SHARED RESOURCE nobody had declared. None was a coding mistake; each was two correct
processes wanting the same thing.

**`check_generated.py` runs 8 checks at once, so run it ONCE, at the end.** It was a serial
loop taking 28 minutes -- long enough that nobody ran it before committing, which is the
only moment it earns anything -- and it is now 3.5 minutes. But four agents each running it
mid-work put 32 Python processes on the machine and took the load average past 11. The old
version was slow enough that concurrent runs queued politely; the fast one does not. So:
verify at the end of a task, not as you go, and if several agents are working, one of them
runs it for everybody. `--serial` exists for debugging a single check.

**The site build is not parallel-safe and cannot be made safe by asking.** `npm run
build:site` spawns Chrome on a fixed port 8794 and writes a shared `dist/`. Briefing each
agent to "check before building" does not work, because check-then-build races: three
agents check at the same moment, all see the port free, and two die with `EADDRINUSE` or a
half-written `dist/`. One of those failures arrived as exit 137 and was reported as an
out-of-memory kill, which sent me looking in the wrong place entirely. **Have one agent
build, at the end, or take a real lock.**

**And the wait-loop that check is written into LIES, because `pgrep -f` matches itself.**
`pgrep -f "build:site|vite build|prerender"` matches the `zsh -c` command line of the loop
running it, so the loop sees a builder that is itself, never exits, and every later "is the
slot free?" check inherits a false BUSY. Three of those were the entire contention signal in
one session, and the agent reported another agent's builds as the cause. The bug is a
**self-matching pattern**, and it costs a whole session's coordination rather than failing
loudly.

> Write the pattern so it cannot match its own literal text: `pgrep -f "[v]ite build"`.
> Or exclude the caller: `pgrep -f ... | grep -v $$`. Never grep for a string that is
> sitting in your own argv.

This has now happened twice here. The guidance above -- check the slot before building --
is what puts the pattern in an agent's hands, so it does not get to be stated without the
trap beside it.

**`git checkout <file>` destroys another agent's uncommitted work.** It cost five
`money-gaps.csv` rows written by two other agents, and only three were recoverable from a
grep somebody happened to have taken. The owning agents rewrote theirs from their own
findings, which is the right repair -- reconstructing another agent's row from its title
would be inventing content and calling it recovery. The same family as the standing rule
against `git stash`: **never discard working-tree state you did not create.**

**A generated file with several authors gets clobbered, not merged.** `money-gaps.csv` was
rewritten whole twice in one day, once with the line endings changed. Append, re-read
immediately before writing, and preserve the file's existing newline convention.

## Running the checks

**The full catalogue -- every check and generator, one line each -- is
`notes/reference/CHECKS.md`.** Look a command up there before inventing one. The ones every
session needs:

    python3 scripts/check_generated.py           # EVERY generator still reproduces its output -- once, at the end
    python3 scripts/audit_provenance.py          # no projection reads actuals; model.json is fresh
    python3 scripts/check_archive_backed_up.py   # THE GATE: nothing destructive runs while a document is unbacked
    python3 scripts/annual_report_progress.py    # which annual-report years are done
    python3 scripts/process_meeting.py --status  # the meeting backlog; --next N only when TJ asks, with his N
    python3 scripts/search_minutes.py "term"     # what the town said, with both denominators
    bash scripts/deploy_site.sh                  # THE way to deploy (rule 10: only when asked)

## For a reader who arrives at the repository, not the site

**Some agents cannot fetch this site at all.** One asked what the archive holds about
paraprofessionals, could reach only package registries and GitHub, cloned the repository
and landed on the Vite starter template -- untouched since the initial commit, while the
repo grew into 3,877 documents and 57 datasets. It reverse-engineered its way in with
`git ls-tree | grep roster`.

For that reader **GitHub is the site**, and `fy28/public/llms.txt` is at an address nobody
would guess. `README.md` is now generated by `scripts/build_readme.py`: the same map, at
the address they actually arrive at, with `raw.githubusercontent.com` links that work
without a clone. Its counts are derived, and `--check` fails if it names a file that is not
in the repository -- because a path is the whole of what that reader gets.

## Searching what the town said

Rule 15a says to search the meeting archive for what people said about a thing in the same
year, and for a long time said it without naming anything to search. Use this:

    python3 scripts/search_minutes.py "jersey" --board school-committee --since 2025-07-01

It greps `sources/meetings/text/` -- 1,422 documents, every board, 2025 onward -- and prints
the board, the date and the citable URL for each hit. **It also prints, on every run, how
many documents were searched out of how many the town has published, and lists any that
cannot be searched at all.**

That last part is not decoration. A grep that finds nothing prints nothing, and nothing
reads as *nobody said it*. It is not: it means nobody said it *in the documents that can be
read*, and those were different numbers for months. 39 documents the town published as Word
files were absent from the archive -- the fetcher tested `blob.startswith(b'%PDF')` and
recorded everything else as missing, and the extractor walked `*.pdf` only, so each half of
the assumption hid the other. One was School Committee minutes from the middle of FY26.
`fetch_agendas.py` now identifies the format from its magic bytes and `extract_minutes.py`
reads Word and Excel too, so coverage is currently 1,422 of 1,422 -- but the reason to print
the denominator is that nobody will notice the next gap either.

The archive is also published: `/minutes/<board>.txt` per board, `/data/minutes-index.csv`
with a `has_text` column, and `/minutes/find/` for callers that can only fetch URLs.

**It searches TWO corpora and reports TWO denominators.** `sources/meetings/text/` is what
the town published. `sources/data/youtube-transcripts/` is machine captions of the
recordings -- ours, derived, and a FINDING AID rather than a source: a caption model hears
*fifteen hundred*, *$1,500* and *$50* alike. They are searched together by default,
because the register counts meetings whose only surviving record is a recording -- most of
them School Committee -- and a search that skipped those reported *nobody said it* about
meetings it had no way to read. Every caption hit is labelled a transcript and cited as
**the video at its timestamp**, never as a document, and caption coverage is printed as its
own line. Do not add the two together.

Both corpora are indexed by `scripts/build_minutes_fts.py` into `sources/data/minutes-fts.db`
-- SQLite FTS5, `porter` stemmed, derived and gitignored exactly like `lunenburg.db`, and
deliberately NOT in it (everything in `lunenburg.db` is pushed to D1, which is at its write
budget). Real tokenisation is not only speed: `ELL` used to match thousands of documents
through *well*, *shell* and *sell*. Stemming means a hit may be a variant of your word, so
every result prints the surface forms that matched and says whether yours was among them.
The index re-reads its manifest on every search and greps anything it has not caught up
with, so a stale index makes a search slower and never quieter.

`notes/reference/SCHEMA.md` documents the database. The one rule: the CSVs are the source of truth
and the database is a derived read model, rebuilt from scratch every run. Nothing is ever
edited in it -- a row in a database has no address, no publisher filename and no sha256.

## Ingesting new documents

`sources/` is organised by **how a document reached us** — the one attribute that is
single-valued and never changes. Everything else (fiscal year, subject, what we use it
for) is multi-valued, and lives in the catalogue and in `views/`, not in a path.

**Run this before you commit an ingest. It fails on the mistakes that actually happen:**

    python3 scripts/check_archive_layout.py

Four rules it enforces, and why each one is there:

1. **No new top-level folder.** Thirteen exist and each is a way a document arrived. A
   fourteenth is a decision about the archive, not a place to put a delivery — and
   `records-request-2026-06/` is the folder name that taught us this, because it could
   have held literally anything.
2. **Every MUNIS report goes in the subfolder for what it IS** — `expenses`, `revenue`,
   `account-details`, `transfers`, `purchase-orders`, `fund-balances` — never in one named
   for when it was asked for.
3. **The filename carries the fiscal year and the period**:
   `<report>-fy<YYYY>-p<PP>-<scope>.<ext>`. Two reports print the identical title
   `YEAR-TO-DATE BUDGET REPORT` and differ only by period; `p09`, `p12` and `p13` are three
   different answers and the filename is the only place that survives.
4. **A delivery carries a PROVENANCE file.** Nothing in `munis-ledgers/` came off a
   website, so the request or the email IS the address. Where we do not know how something
   arrived, write that down — see `munis-ledgers/expenses/PROVENANCE-fy2026-p09.md`, which
   records the gap rather than inventing a route.

Then the usual: `build_source_index.py` fails if a new file is not described,
`extract_munis_report.py --check` ties every report to its own GRAND TOTAL, and
`build_views.py` re-indexes it by year and subject.

**Mirrors are the exception to rule 3.** A document under `town-budget/`,
`town-supplementary/`, `district-budget/`, `meetings/`, `dese/` or `dls/` keeps the
publisher's own filename, because that is the name a resident asks the town for when the
link dies.

## The standing questions

Some numbers would settle more than any further analysis.

**Two of them turned out to be published, in documents this project already held.** They sat
unread for a different reason each time, and both reasons are worth keeping: one was prose
rather than a table, and the other was found by searching for a heading the town does not
consistently use. Neither was hard to get once anybody looked.

- ~~Out-of-district **placement counts** by year.~~ **PUBLISHED, FY2013–FY2025.** In the
  Special Services report inside each annual town report, sourced to SIMS Report 7 and
  measured on 1 March, split into collaborative, day and residential placements.
  `sources/data/placement-counts.csv`. It is two sentences of prose with no heading naming
  it, which is why fifteen years of it went unread. Two checks come with it: the parts sum
  to the total, and each year states the previous year's figure.
  **This does not settle the money.** A placement count is children placed; it says nothing
  about which fund paid or what any placement cost, and rule 11 still applies to the tuition
  line.
- ~~Whether budgeted positions were **filled**.~~ **BOUNDED, not settled.** The town
  publishes per-school staff rosters, by name and position, in every annual report from
  FY2011 to FY2025 — 51 blocks across fifteen years. But a roster carries **no FTE**, so a
  0.4 music teacher and a full-timer are one row each; **no funding source**, which is the
  question that actually matters; and it is a point in time, undated within the year. A
  count of names the town printed is a real quantity and it is not a staffing level.
- ~~The FY26 **year-end** figures.~~ **HELD FOR THE SCHOOLS, at the close; not yet for the
  town.** The school department's General Fund and special funds at **period 13** -- the
  closed year, FY2023 to FY2026 -- arrived 6 October 2026 in the Town's answer to the
  4 September records request (`town-ledgers/expenses/*-p13-*-school.xlsx`, extracted to
  `sources/data/munis-school-ytd.csv`). The town General Fund is held only to **period 12**
  (June, before the close; `PROVENANCE-fy2026-p12.md`), so its closing adjustments are not.
  This line said everything stopped at 31 March for a month after period 12 arrived --
  a standing question is prose, and rule 2 applies to it too.
- **How grants and state funding map onto the budget lines.** The budget shows the general
  fund and nothing else, so a line rising because a grant ended looks exactly like a line
  rising because the district grew. This one is load-bearing: the in-district special
  education escalator is built on a paraprofessional line, and it cannot currently be
  distinguished from grant money unwinding.
