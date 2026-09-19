# Threads: a matter tracked across meetings, across boards, to a decision

TJ, 19 September 2026: *"auto-identify threads of important things being discussed. The
point is to be able to track it across meetings, over time, and across boards... The hard
part is identifying what should be considered a 'thread'. Not to treat EVERYTHING as a
thread, and not to miss the important things."*

**Status: PROPOSAL. Edit this, then we build to it.** Written in the same shape as
`notes/process/BUDGET-SEASON-MODEL.md`, because the budget feed is where every mechanism
below already exists.

---

## 0. The budget feed is the first thread, and it is the only one guaranteed forever

The budget season is a thread with a fixed shape: nine milestones, one season per fiscal
year, always exists, always itemised. Everything in this document is the *general* case —
a matter that arises, recurs, and resolves, on no schedule and belonging to no season.

**Nothing here changes the budget feed.** `sources/data/budget-threads.csv` keeps telling
the budget's own stories under the budget's own page. This model governs what happens when
a matter is not about the budget being built, or outlives the season it started in.

## 1. What already exists, and what does not

| the mechanism | where it lives | ports? |
|---|---|---|
| a thread as `id, order, label, question, match, kinds, seasons, note` | `sources/data/budget-threads.csv` | yes, minus `seasons` |
| first thread by order claims a row; unclaimed → `other` | `thread_of()`, `build_budget_feed.py:657` | yes |
| a candidate proposed, never created: ≥5 lines across ≥3 meetings | `propose_threads()`, `build_budget_feed.py:684` | yes — this is the core |
| a stop list of things every meeting has | `THREAD_STOP`, `:668` | yes, and it must grow |
| the now / changed-since / history block | `BUDGET-SEASON-MODEL.md` §4 | yes |
| **the record the threads filter** | `write_budget_state.py` → `sources/data/budget-state/` | **no** |

The last row is the whole of the new work. Budget threads filter rows an extractor pulled
out because they were *figures about the budget being built* — a hard boundary that a
general thread does not have and does not need one, because **the record already exists**:
`sources/data/recording-minutes/` holds 159 meetings across 17 boards, each carrying
`topics`, `decisions`, `votes`, `budget_items` and `tags`, every one with a second in the
video. Threads filter minutes instead of budget-state. No new model pass to start.

## 2. What makes something a thread: TWO gates, both required

"Important to families" is the right test for whether a matter is worth **surfacing**. It
is the wrong test for whether it is a **thread**, and conflating them is what makes this
fire on everything. A unanimous vote to accept a $4,170 line has family impact and is not
a thread; it is an event.

**The signature of a thread is an open decision that recurs.** Two gates:

**Gate A — PERSISTENCE.** Machine-detectable, and it is what `propose_threads` already
measures. One of:

- the matter appears in **≥3 distinct meetings** (any boards) with **≥5 mentions**; or
- it has a **scheduled next step** on the record — a warrant article, a posted hearing, a
  study due back, a contract up for renewal, a deadline in a grant — even at one mention.

The second half matters more than the first. A matter with a date attached is a thread from
the moment it acquires the date, and waiting for a third meeting is waiting until after the
point where a resident could have acted. The manual pass (§12) found the extended day
programme fee increase on exactly one line — *"agreed to place a fee increase on a future
meeting agenda rather than let the programme run unsustainably"* — a direct cost to
families that a three-meeting floor does not see until it is decided.

### Gate A as written is RETROSPECTIVE. Three leading signals fix that

TJ, 19 September 2026: *"we don't hyperfocus on being able to identify historical threads.
We have to be able to identify threads that are STARTING."*

**Recurrence is a lagging indicator by construction.** A floor of three meetings cannot fire
until a matter has been running for months -- by which time a resident who wanted to act on
it has missed it. The paraprofessional contract is the proof: `paraprofessional` appears in
7 meetings across 2 boards and clears the floor easily, but those are *different matters*
(new positions, restorations, an undercount, a departure). The **contract** appears in
exactly one meeting, 16 September 2026, three times:

    superintendent's report: "...paraprofessional contract delay"
    VOTE: "pass over paraprofessional contract reratification"
    "Topics for future discussion: capital plan, paraprofessional contract"

One meeting, and unmistakably a thread. So Gate A gains three leading signals:

**1. A NON-DECISION, at n=1.** *Passed over, tabled, deferred, continued, referred, laid on
the table, "will come back", "bring back", "topics for future discussion".* **A board
declining to decide is a board stating that the question is open** -- which is the
definition of a thread, arriving the first time it happens rather than the third. Measured
over the 108 recent meetings: **83 such signals** (51 in decisions, 32 in votes). A workable
volume, and it is the single change that makes the detector prospective.

**2. ACCELERATION, not count.** Two meetings three weeks apart is a live matter; three
meetings across eighteen months is a recurring agenda item. Rank on the rate, not the total.

**3. THE SECOND BOARD BEATS THE THIRD MENTION.** Every confirmed thread in §12 reached a
second board early. Every false positive stayed on one board, or spread only incidentally.
Cross-board spread is the strongest single predictor in this data, and it is cheap to
compute -- so weight a new board far above another mention at the same one.

**And a fourth, which is not a detector at all: KNOWN FUTURE OBLIGATIONS seed threads before
anybody says a word.** A contract's expiry, a study's due date, a grant's end, a statutory
deadline. The paraprofessional contract was going to come up whether or not it was ever
mentioned. That is a calendar, and this project does not currently hold one -- see §13.

### A NON-DECISION is a TRIGGER, never a bar. Gate B still has to fire

TJ, 19 September 2026: *"I don't think we should just identify anything unresolved. It has
to also raise to the level of IMPORTANCE somehow too. But yes one meeting that opens a can
of worms or an important thing should immediately create the thread. That's how things
happen."*

**The non-decision changes WHEN Gate A may fire. It changes nothing about Gate B.** Both
gates are still required, and the trigger is the weaker claim of the two: it says the
question is open, not that the question matters.

A sample of the 83 deferrals says why, and the spread is enormous:

| deferred | thread? |
|---|---|
| *"Decision on pursuing a comprehensive/forensic audit of FY25 books was deferred"* | **yes** |
| *"all extracurricular activities and athletics are considered 'on the table' for further reductions"* | **yes** |
| *"The custodial union MOU was not voted on because the custodial union had not yet seen it"* | **yes** |
| *"Table approval of the May 27th minutes because the SharePoint folder was not accessible"* | no |
| *"The scheduling of a select board tour of Town Hall was passed over"* | no |
| *"Commission will try to staff a table at the vendor fair with flyers"* | no |

Roughly a third of deferrals are real, a third are housekeeping, a third are in between.

**The seven kinds already kill most of the housekeeping** -- a vendor-fair table, approving
minutes, scheduling a tour and circulating edits are none of rule, money, service, contract,
project or asset. **The kind that leaks is `office`**: *"appointment of a payroll and
benefits coordinator was passed over"* is an office and is not a thread. So `office`
narrows to **a post that DECIDES things becoming vacant or contested** -- a superintendent
search, a town manager search -- and never a routine appointment. §11's checklist doubted
that kind and the data settles it.

### The bar: REACH x CHANGE, ranked -- the same shape as rule 4

CLAUDE.md rule 4 ranks a budget line by *pull*: its share of the budget times how far its
growth exceeds the cap, because neither number means anything alone. A thread is the same
shape. **Importance is REACH times CHANGE**, and four inputs are readable from the record:

1. **Reach -- who it touches.** Everyone in town (a fee, a tax, a bylaw) > every school
   family > one programme's families > one neighbourhood > one person, which is excluded
   outright by the individual-matters rule above.
2. **Stake.** A figure or an FTE attached; and whether the thing is *eliminated*, merely
   *reduced*, or only *studied*.
3. **Irreversibility.** Sell, dispose, demolish, borrow, sign a multi-year contract. A
   building cannot be un-sold, and that asymmetry is worth weight on its own.
4. **DID RESIDENTS SHOW UP.** **582 public-comment speakers across 95 of 165 meetings**,
   each carrying a topic and a second in the recording. This is the only one of the four
   that is **not our judgement** -- it is the town telling us what matters, and the season
   model already leans on it: the band families spoke and band came off the cut list.
   Weight it highest.

**The bar RANKS the proposals. It does not silently cut them** -- §4's recall rule still
governs, and a candidate held back by a low score is still written to the declined registry
with its score, never dropped. A bar that deletes is a bar nobody can audit.

### Two rows that are never a matter, both already marked in the data

Running the gates forward over the 40 meetings since 21 June 2026 produced two false-positive
families, and the record already carries the flag to kill each:

- **A PROCEDURAL VOTE.** *"Close the public hearing"*, *"Open/continue the hearing"*,
  *"Move the question"*. Our minutes already set `procedural: true` -- **85 of 224 votes
  since 21 June** -- and the detector was not reading it. A procedural motion is the meeting
  operating itself, never a matter.
- **A REPORT BUNDLE.** *"Chair's report: business administrator search, financial practices
  review, special ed stabilization fund, paraprofessional contract delay"*, *"Committee
  reports (open space, library, master plan, stormwater, ...)"*. **40 such topics** in the
  same window. One row, ten unrelated subjects -- the Adult Activity Center failure at row
  level, and it scores high precisely because it is dense. A bundle may SEED a candidate
  (the paraprofessional contract was found in one) but may never itself be the evidence.

Weight `decision` and substantive `vote` rows above `topic` rows generally: a decision is
something the board did, a topic is what the agenda called it.

### The can of worms gets its own trigger

TJ's phrase, and the forensic-audit deferral is the case. What marks one is that it points
at a **systemic** problem rather than a single decision: *audit, forensic, investigation,
review of practices, town counsel opinion, complaint, conflict of interest, how did this
happen, unaccounted, discrepancy.*

One of those beside a non-decision is a thread **immediately**, whatever it scores on reach
-- because the reach is exactly what is not yet known, and that is the reason to open it.

### A match must fix the SENSE, not the token

The school surplus clears the gates on its own (Nov 2025, Feb 2026, and the Town Meeting
floor in May 2026, across two boards). But **half the hits for `surplus` are a different
word**: declare the electric range surplus, two fabric love seats, a 1998 Ford E-350
ambulance. That is not entity-versus-matter -- it is **polysemy**, one token carrying
unrelated meanings, and it needs the match to carry an exclusion:
`surplus` NOT `(declare\w*\s+\w*\s*surplus|surplus (property|equipment|furniture|vehicle))`.

Entity-versus-matter and polysemy are different failures and both have to be handled at the
`match` column. Neither is fixed by a threshold.

### A thread that no vote can close

The surplus thread has a shape §3 did not anticipate: **no decision will ever resolve it.**
It is an accountability question -- *how did a surplus that size arise, and does the
explanation hold* -- not a pending choice. It still has a closure on the record (the
financial practices review with UMass Boston, named 16 September 2026), but the closing act
is *an explanation being accepted or not*, never a motion carrying.

So `status` gains a fourth value: **`answered`** -- distinct from `resolved` (a decision was
made), `lapsed` (it went quiet) and `open`. And the `closes` column for such a thread names
the document or review that would answer it, which is `money_gaps`' `-- closes:` convention
pointed at a thread instead of a gap.

**And a CEILING, which the floor alone does not give.** A term appearing in more than about
**40% of meetings** is a *facet* — a way of slicing the record — not a matter. `#budget`
is in 87 of 108 recent meetings, `#personnel` in 86, `#facilities` in 79. Every one clears
a recurrence floor by an order of magnitude and none is a thread. Without the ceiling the
detector's top twenty results are all facets and the real candidates are buried below
them, which is what the first run did.

**Gate B — CONSEQUENCE.** Editorial, proposed by the detector and confirmed by a person.
The matter changes one of:

| kind | what it looks like | example here |
|---|---|---|
| `rule` | a bylaw, regulation, policy, zoning change | the stormwater bylaw article |
| `money` | a fee, a rate, a cost residents pay | trash fees, athletic user fees |
| `service` | a service level: hours, staffing, a programme | library hours, a cut sport |
| `contract` | a union agreement, a vendor, a lease | a collective bargaining settlement |
| `project` | a new study, design, build, or purchase | a building design committee |
| `asset` | town land or buildings changing use or hands | Turkey Hill |
| `office` | who holds a post that decides things | a superintendent search |

**Both gates, or it is not a thread.** A matter that recurs endlessly and changes nothing
is a standing agenda item. A matter with real consequence that resolves in one meeting is
an event, and belongs in the board's own record where it already is.

### The one-question test — the discriminator, and it needs no new schema

**If you cannot write the thread's `question` column as ONE sentence, it is not a thread.**
That column already exists in `budget-threads.csv` and was being used as a caption. It is
the gate.

The Adult Activity Center fails it in a way no threshold catches: 9 mentions across 2
boards, every item a real decision with a real vote — a surplus electric range, a pavilion
dedication, an IT capital request, two love seats, the parking. They share a **location**,
not a question. A thread is one open question the same people keep coming back to.

### An ENTITY is not a MATTER, and this is what the detector gets wrong

The detector finds named things. A named thing is a *place*, a *body* or a *person*, and a
matter is a *question about one*. Three of the strongest Gate A signals in §12 are entities
hosting a different number of matters:

| the entity | meetings | matters inside it |
|---|---:|---|
| Turkey Hill | 40 | **two** — rebuild-or-renovate (MSBA), and the ADA bathrooms — plus incidental mention: paraprofessionals, DIBELS scores, solar offsets, intercom upgrades |
| Monty Tech | 13 | **one** — why Lunenburg's assessment rose far faster than Monty Tech's own budget |
| Adult Activity Center | 9 | **none** — it is the room the meetings are in |

So the detector proposes an **entity**, and the confirming step is not a yes or no: it is
*name the matter, and write the qualifier that separates it from the rest of the entity's
traffic.* `match` becomes entity **and** qualifier —
`Turkey Hill` + `(MSBA|rebuild|renovat|statement of interest)` — never the entity alone.
A thread keyed on the bare entity collects everything that happens in a building.

### Tags CONFIRM. They cannot DISCOVER

The 55-tag vocabulary on the minutes looked like the obvious detector input and must not be
one. **There is no `stormwater` tag in any of the 159 meetings** — and the stormwater
utility is the largest live matter in town: a new fee, billed to every property owner
separately from the tax bill, on its way to a Special Town Meeting. The vocabulary is
school-budget-shaped (`turkey-hill`, `msba`, `chapter-70`, `monty-tech`, `school-choice`)
because that is what this project was built around, and a detector that trusts it inherits
that blind spot exactly. Tags are a good *second* signal on a thread already named, and a
closed list can only find what somebody already thought of.

### Two hard exclusions

**Never propose a person's name.** The citizens' petition surfaced through the petitioner's
name across 4 boards. The matter is the petition; the petitioner is not the thread, and
rule 8 already says so. Person names are suppressed at the proposer, not corrected later.

**Never open a thread on an individual's business.** A dangerous-dog hearing and a
no-trespass order against an unhoused person at the Pleasant Street Conservation Area both
have a scheduled step and real consequence, and neither may ever be a thread. A thread is a
matter of **general application**. This is an exclusion by rule, not a threshold.

## 3. A thread MUST declare how it dies

The budget season gets this free: milestone 9 ends it. A general thread has no milestone,
so **the closure criterion is written when the thread is created**, in its own column, in
citizens' words:

    closes: Town Meeting votes the article
    closes: the Select Board signs the contract
    closes: the study comes back and the board accepts or rejects it

Without one, threads never resolve and the page becomes a graveyard, which is the opposite
of the archive TJ asked for. A thread whose closure has happened moves to **resolved**, with
the date and the citation of the thing that closed it, and stays readable forever.

A thread can also **lapse**: no mention in 12 months and no scheduled step. That is not
resolved and must never be shown as resolved — it is *went quiet*, and it is frequently the
most interesting state on the page.

## 4. Tune for recall. Filter by hand

**The detector proposes. A person creates.** This is already how the budget feed works and
it is the answer to "the hard part is identifying what counts" — the criteria do not have to
*decide*, only to *rank*. So they are tuned to over-propose.

The two failures are not symmetric:

- **Over-proposal** costs one line in a list nobody has to act on.
- **A miss is invisible.** It has the exact shape of the silent zeros in CLAUDE.md: a
  detector that finds nothing prints nothing, and nothing reads as *nothing was happening*.

So, borrowed from `search_minutes.py`, **the proposer prints its denominator**: how many
meetings were read, out of how many the town held, and which could not be read at all.

And a rejected candidate is **recorded, not forgotten** —
`sources/data/threads-declined.csv`: the candidate, the date declined, and one line of
reason. Without it, *we looked and said no* is indistinguishable from *nobody looked*, and
the same candidate is re-proposed and re-argued every run.

## 5. A fiscal year is a VIEW, not the container

TJ's instinct was to capture threads per FY. The budget season is genuinely FY-scoped —
that is what a season is. A general thread is not: a bylaw, a building project or a land
question spans fiscal years, and cutting it at 1 July breaks the exact thing threads exist
to do.

So a thread carries `started` and `resolved` dates and the FY view is derived from them. A
thread open across three fiscal years appears in all three.

## 6. Cross-board is the point

The budget feed is already cross-board across three boards. Extending that to all 17 is
where this earns its keep: a stormwater article moves Task Force → Select Board → Town
Meeting, and no page currently shows that as one story.

The term for the unit is a **docket** — a matter that carries an identity across sittings
and moves between bodies. Steal the part where every matter has a stable id that can be
cited, so a resident, an agenda and a vote can all point at the same thing.

## 7. Coverage is bounded by the record, and the bound is published

A thread can only be tracked through meetings that can be read.
`scripts/build_board_posting.py` already measures which meetings got minutes, by board and
fiscal year, and some of the 17 boards are thin.

**Every thread prints *tracked through N of M meetings*.** When a thread goes quiet because
the record went quiet rather than because the matter did, that is a **rule 7c gap** and it
gets a row in `sources/data/money-gaps.csv` with `— closes:` the minutes nobody posted.

## 8. What a thread page says — rule 7 applies at every line

Per thread, in this order (rule 7a: the thing first, the explanation after):

1. **Where it stands now** — one line, and the date it last moved.
2. **What changed since the last meeting.**
3. **What happens next** — the scheduled step and its date, or *nothing scheduled*.
4. **The history** — every meeting that touched it: board, date, what was said or decided,
   the vote if there was one, each citing the video at its second or the minutes document.
5. **What this does not establish** — the caveats. Captions mishear; an agenda item is not
   a decision; a board discussing a thing is not the board that decides it.

**The epistemic line is where this will break.** A vote is a fact. *Why* the matter moved is
a hypothesis unless somebody said so on the record — rule 7, and threads are a narrative
format, which is precisely the format that crosses it. Every row cites a timestamp; nothing
is written that a citation does not carry.

And rule 7b's length discipline: a thread's standing is a **status and two lines**, not a
paragraph. Everything else expands.

## 9. The index page

`/threads` — open threads first, ranked by when they last moved; resolved below, with the
date and what closed them; lapsed in their own group, labelled *went quiet*, never mixed in
with resolved.

Filterable by the consequence kinds in §2 and by board. The kinds are read off the data, not
mapped in code, so a new kind appears the day it appears in the CSV — the same rule
`money_gaps` uses for `side`.

## 10. The shape of the file

`sources/data/threads.csv` — one row per thread, the budget's columns plus what §3 and §5
require:

    id, order, label, question, kind, match, tags, boards, started, closes,
    resolved_on, resolved_by, status, note

- `kind` — one of §2's seven.
- `match` — the regex, as in budget-threads. `tags` — the minutes tags it owns
  (`turkey-hill`, `override`), which is a stronger signal than a regex and is already
  written on every meeting.
- `boards` — blank means any; a value narrows it.
- `closes` — the closure criterion, in citizens' words. Required.
- `status` — `open` · `resolved` · `lapsed`. Derived where it can be, overridable by hand.

A thread TJ starts by hand is the same row with no detector behind it. That is the whole of
"I can form a thread myself."

## 11. What we have to agree on

- [ ] the two gates, and that BOTH are required
- [ ] the seven consequence kinds — and whether `office` earns its place
- [ ] that a scheduled next step makes a thread at one mention
- [ ] that closure is declared at creation, and `lapsed` is never shown as `resolved`
- [ ] the declined registry, and that it is part of the build rather than a note
- [ ] FY as a derived view rather than the container
- [ ] that the detector only ever proposes

Once agreed: a manual pass over the 159 meetings to see what the criteria actually catch
(and what they wrongly catch), tune, then the detector, then the page.

---

## 12. The manual pass, 19 September 2026 — running the gates by hand

TJ: *"analyze recent data as the mechanisms would... a manual pass at thread identification
and proposal to test to make sure we have it right."*

**What was read:** `sources/data/recording-minutes/`, **108 meetings across 17 boards**,
19 September 2025 – 19 September 2026, 8,715 lines of topics, decisions, votes, budget
items and tags. Gate A was run as `propose_threads` would run it; Gate B by reading the
candidates. Everything below cites the meetings it came from.

### 12a. What the gates proposed — 11 threads

**Open:**

| thread | kind | boards | span | closes |
|---|---|---|---|---|
| **The stormwater utility: a new fee on every property** | money | 5 | Jan 2026 – live | the Special Town Meeting votes the article |
| **Turkey Hill: rebuild or renovate** | project | 4 | Oct 2025 – live | the MSBA statement of interest is submitted or dropped (window opens January, closes April 2027) |
| **Turkey Hill: the ADA bathrooms** | project | 3 | Jan 2026 – live | the bathroom project is funded or abandoned |
| **Brooks House: what becomes of it** | asset | 2 | Jul 2026 – live | the Select Board adopts a disposition; the town-meeting-directed report was **overdue** in July |
| **TC Passios: the site's future** | project | 3 | Feb 2026 – live | the feasibility study comes back and a board acts on it |
| **925 Mass Ave: the RFP** | asset | 3 | May 2026 – live | a proposal is accepted or the RFP lapses |
| **The Monty Tech assessment** | money | 3 | Sep 2025 – live | the assessment is set each year — a recurring thread, never resolved |
| **The extended day programme fee** | money | 1 | Apr 2026 – live | the School Committee votes the new fee |

**Resolved — and these are the archive TJ asked for:**

| thread | closed by | when |
|---|---|---|
| **Kids Kingdom: custody to the town** | joint warrant article, Annual Town Meeting | May 2026 |
| **The fourth fire shift** | moved off the override into the omnibus budget, retained | Article L, Apr 2026 |
| **The citizens' petition to restore middle school sports** | **Article 3 passed** — transfer from the WRAP fund | Special Town Meeting, 3 Sep 2026 |
| **Trash and recycling: the enterprise fund** | Article Y recommended 5–0, then Town Meeting | Mar–May 2026 |

That last one is the model case for why threads matter: pay-as-you-throw was floated in
January, the programme was cut in the DPW budget in February, an enterprise fund conversion
was explored in March, and it reached the warrant in April — across three boards, and no
page in this project shows it as one story.

### 12b. What the gates correctly REJECTED

| candidate | Gate A | why it is not a thread |
|---|---|---|
| `#budget` | 87 of 108 meetings | a facet. So are `#personnel` (86), `#facilities` (79), `#staffing` (73), `#policy` (67) |
| Adult Activity Center | 9 mentions, 2 boards | a venue. Fails the one-question test outright |
| Green Communities | 4 mentions, 4 boards | routine appointments. The real matter is Wallace Park lighting, which is its own candidate |
| the petitioner's name | 5 mentions, 4 boards | a person. The thread is the petition |
| the Pleasant Street no-trespass order | scheduled step, real consequence | an individual's business. Excluded by rule |

Each of these goes in `sources/data/threads-declined.csv` with the reason, so none is
re-argued on the next run.

### 12c. What the pass found that is NOT about threads

Two defects in the underlying record, both of which break cross-board counting:

1. **The board name is free text and the slug is not.** 108 meetings produced **24 distinct
   board names** from 17 directories: `Finance Comittee` beside `Finance Committee`,
   `Select Board` beside `Select Board Workshop` and `Select Board Meeting -`, `TriBoard`
   beside `TriBoard Meeting`, `School Committee Forum` beside `School Committee`. Any
   count of *how many boards touched this* is wrong unless it keys on `board_slug`.
2. **Three minutes files carry impossible dates** — `2027-11-06` (Board of Assessors),
   `2027-01-16` (Architectural Preservation District Commission), `2021-11-22` (Parks
   Commission). A date in the future puts a meeting outside every window that should hold
   it.

### 12d. What the pass changed in this document

- Gate A gained a **ceiling** (§2) — without it the top twenty candidates are all facets.
- Gate B gained the **one-question test**, using the `question` column that already existed.
- **Entity ≠ matter** was added, with the Turkey Hill / Monty Tech / Adult Activity Center
  table: the detector proposes an entity and a person names the matter inside it.
- **Tags confirm, they do not discover** — the missing `stormwater` tag.
- Two hard exclusions: **person names** and **individual matters**.

Nothing in §3–§11 needed changing. The closure column, the declined registry, FY-as-a-view
and propose-never-create all survived contact with the data.

---

## 14. The pages: a door, a landing page, a thread

TJ, 19 September 2026, describing it before reading §8: *"we'll get a threads landing page
that will list all open and historical threads. The home page will have a link to the
threads, and maybe even list what we consider the most 'important' three open threads or
maybe even 2 open and a recently closed thread. Then clicking a thread will bring me to the
page that shows me how it's forming or formed, meeting chrono and votes, etc, and what's
left open."*

That is §8 and §9. What it adds is the **front page**, and `READING-FLOW.md` already rules
out the obvious way to do it.

### 14a. The door cannot say "Threads"

**"Threads" is our word.** No resident has heard it, and READING-FLOW's *"a door without
scent"* is exactly this mistake, already made once: *"The budget feed" was our name for a
thing no resident has heard of. A door says what is behind it in words the reader already
has.*

So the door is the question, not the feature:

    What the town is deciding now          ← the door
    9 things still open. 4 settled this year.

`Threads` stays as the route and the internal name. It never appears on the door.

And the doors are **ranked, not equal** -- the crisis first and heavier, the plumbing
quiet. A threads door is not a fifth equal box; it earns a position on the same argument
every other door did.

### 14b. Two open and one closed, and the closed one is the load-bearing card

TJ's instinct, and the reason it is right is worth writing down: **the closed thread is the
only card that shows a payoff instead of promising one.** Two open threads say *here is
something unresolved*; a closed one says *and this is what it looks like when it ends* --
with a vote, a tally and a date. It teaches what a thread is by showing a finished one,
which no amount of explanation above the cards would do (rule 7a).

Each card carries, and nothing more:

    the thread's name, in the reader's words
    who it touches            ← reach, from the bar in §2. This is what makes someone click.
    where it stands now, and the date it last moved
    what happens next, and when        (or, on the closed card: how it ended, and the vote)

Rule 7b's discipline applies: a metric and two lines. If the standing needs a paragraph,
the thread is badly named.

### 14c. The landing page: RANK first, then GROUPS

TJ: *"The threads page likely needs categorization so it's not just a huge linear list."*

**But a group and a rank answer different readers, and the page needs both in that order.**
A rank serves the reader who does not know what they are looking for -- *what should I know
about?* A group serves the reader who does -- *what is happening with the schools?* Group
first and the most important matter in town can sit third inside a collapsed section, which
is the failure this whole page exists to prevent.

So:

    WHAT IS MOVING NOW          ranked by the §2 bar, 3-5 threads, ungrouped
    ---------------------------------------------------------------
    then everything, in groups

**The groups are NOT the seven kinds.** `rule / money / service / contract / project /
asset / office` is *our* classification -- it is how we decided something was a thread, and
it is the same category of mistake as putting "Threads" on the door. A resident does not
think *this is a contract matter*; they think *is this about my kid's school or my tax
bill?*

The precedent is already here: `BUDGET-SEASON-MODEL.md` §4 groups the cut list *"the way
families think: sports, band and music, transportation, special education, teachers by
school"*. Same rule, one level up:

| group | what a resident is asking | threads today |
|---|---|---|
| **Schools and my kids** | programmes, staffing, buildings, athletics | Turkey Hill x2, athletics on the table, extended day fee |
| **What I pay** | fees, rates, the tax bill, overrides | stormwater fee, veterans exemption, trash enterprise fund |
| **Town land and buildings** | what is being sold, built, closed, given away | Brooks House, TC Passios, 925 Mass Ave, Kids Kingdom, the turf field |
| **Water, sewer, roads, trash** | the services that arrive at the house | sewer pump procurement, recycling |
| **How the town runs** | bylaws, contracts, who decides | the SAP rewrite, DPW union, trust fund vacancy |

Five. With a dozen or two live threads, six groups or more produces groups of two, which
reads worse than the list it replaced.

**A thread belongs to more than one group, and that is fine.** Turkey Hill's ADA bathrooms
are *schools* and *buildings*. This archive already settled the general case: the one
single-valued attribute gets the path, and everything multi-valued lives in `views/`. So a
thread carries tags and **the groups are views over tags**, read off the data rather than
mapped in code -- the `money_gaps` `side` rule, so a new group appears the day it appears
in the CSV.

**And the RESOLVED section is the one that actually needs this.** Open threads are
self-limiting -- there are only ever so many live at once. Resolved threads accumulate
forever, and by year three the archive is the bulk of the page. Group resolved threads **by
fiscal year first**, then by the same five, because *what did Town Meeting settle in FY26*
is the question people bring to an archive.

Then **lapsed**, in its own group, labelled *went quiet* -- never mixed in with resolved,
because a matter nobody decided is not a matter that was settled, and that is the single
most misleading thing this page could do.

### 14d. The thread page: forming, or formed

TJ said *"how it's forming or formed"*, and the tense is a real design distinction rather
than a turn of phrase. **The same page reads as two different documents depending on
status**, and the order flips:

| open -- *forming* | resolved -- *formed* |
|---|---|
| where it stands now | how it ended, with the vote and the tally |
| what changed since the last meeting | what it cost, or changed, for whom |
| **what happens next, and when** | the chronology, start to finish |
| the chronology so far | what is still unanswered, if anything |
| what is still unanswered | |

An open thread's most valuable line is **what happens next** -- it is the only thing a
resident can act on. A closed thread's is **how it ended**. Putting the chronology first on
either is writing the page in the order it was built (rule 7a).

Every row in the chronology carries its board, its date, and a citation: the video at its
second, or the minutes document, or -- once §12c's extraction lands -- **the Town Clerk's
own printed sentence from the annual report**, which outranks both.

### 14d-i. The unit of a chronology is the MEETING, never the recording

A thread's history is a list of meetings, and a meeting is not a file. Three ways one
meeting produces several records, all real in this archive:

- **A meeting recorded in parts.** The 2 May 2026 Annual Town Meeting is two videos and two
  minutes files -- 6h56m and 4h55m, **3 overlapping motions out of 45**, so they are two
  sessions of one meeting with a seam, not duplicates. Summing them double-counts the
  overlap; picking one drops half the votes.
- **A joint body.** A Tri-Board meeting is one meeting that belongs to the Tri-Board and
  counts for three boards (§ the registry's `constituent_boards`).
- **Two records of the same vote.** Our minutes of the recording, and the Town Clerk's
  printed record in the annual report a year later. The second supersedes; it does not add.

`scripts/build_meeting_register.py` is already **one row per board and date** -- it is the
thing that has this right. **A thread reads the register, never a glob of the minutes
directory.** Globbing files is the location-as-identity mistake CLAUDE.md names as the
commonest defect here, and a chronology is exactly where it would show up as a
double-counted vote a resident could read.

### 14e. Two things TJ's sketch does not have, and both are cheap

- **A feed per thread.** `build_feeds.py` already publishes Atom per board and for the
  budget. A thread is the single most subscribe-able object this project has -- a resident
  who cares about the stormwater fee wants to be told when it moves, and does not want the
  Select Board's whole agenda. `/feeds/threads/<id>.xml`.
- **The coverage line, on every thread** (§7): *tracked through N of M meetings*. Without
  it a thread that went quiet because the record went quiet is indistinguishable from one
  where nothing happened -- and the boards with the thinnest minutes are not the boards
  with the least happening.

---

## 15. STATE OF PLAY, 19 September 2026 — what was built, what is half-built

Written so this survives a context reset. **Nothing in this section is a claim about the
design; it is a claim about the repository**, and every path in it is real.

### 15a. Built and checked

| what | where | state |
|---|---|---|
| this model | `notes/process/THREADS-MODEL.md` | proposal; §11 is the checklist still to argue |
| canonical board names | `scripts/write_recording_minutes.py` (`board_name_for`) | **done** — reads `sources/data/youtube-boards.csv`; the video's own title is kept as `video_title` |
| board names backfilled | all `sources/data/recording-minutes/*/*.json` | **done** — 36 distinct names to 17, 31 files rewritten |
| Tri-Board as its own body | `sources/data/youtube-boards.csv` (+ new `constituent_boards` column) | **done** — 8 recordings |
| Tri-Board fan-out | `scripts/build_youtube_classification.py` | **done** — 4 rows per meeting, new `role` column: `owner` + 3 `member`. `--check` passes |
| Town Meeting as a primary body | `sources/data/recording-minutes-policy.csv` | **done** — priority **0**, ahead of the three budget boards |
| Town Meeting minutes | `sources/data/recording-minutes/town-meeting/` | **done — 11 of 11**, 2022-05-07 to 2026-09-03, **219 substantive votes** |
| the annual-report vote extractor | `scripts/extract_town_meeting_votes.py` | **done**, with `--check` |
| extracted Town Meeting votes | `sources/data/town-meeting-votes.csv` | **PARTIAL — FY2022-FY2025 only, 143 articles** |

### 15b. NOT built

- **`sources/data/threads.csv` does not exist.** No thread has been created. The twelve in
  §12 and the seven in §16 are *proposals in this document*, nothing more.
- **No detector script exists.** The manual pass was run with throwaway scripts in a
  scratchpad, now gone. §2's gates are written down and have never been implemented.
- **`sources/data/threads-declined.csv` does not exist.**
- **No page exists.** No `/threads`, no thread page, no front-page door.
- **The backfill is unfinished: FY2011-FY2021 are NOT extracted.** Eleven years. It was
  stopped mid-FY2021 on 19 September when the plan hit its rate limit. To resume:

      for fy in 2021 2020 2019 2018 2017 2016 2015 2014 2013 2012 2011; do
        python3 scripts/extract_town_meeting_votes.py --fy $fy
      done
      python3 scripts/extract_town_meeting_votes.py --check

  Roughly **$0.65-$0.90 each**, so the eleven are about **1.5-2% of a week**. Run it when
  the plan is idle, not beside interactive work.

### 15c. Fixed on the way, and why each was a real defect

- **`scripts/fetch_youtube_transcripts.py`** now filters to `role == 'owner'`. Without it
  the Tri-Board fan-out would have fetched each of those recordings **four times into four
  folders**. Introduced and fixed in the same session.
- **`scripts/build_agentic_backlog.py`** now dedupes on `video_id`. It was counting every
  (video, board) row, so a Tri-Board recording counted three times in a backlog *of
  recordings*. **Pre-existing.**
- **`sources/data/annual-report-contents.csv` under-names the FY2025 Town Meeting pages by
  three** — 138, 140 and 143 print articles the catalogue does not list. `slice_for()` takes
  the union of the catalogue and the pages that actually carry an `ARTICLE n:` heading, and
  prints the difference. A catalogue silently dropping three pages of votes reads exactly
  like three pages of votes that were never held.

### 15d. The quote check, and the four rounds it took

`--check` asserts every `quote` is the Clerk's own sentence. It went from 26/49 to 138/143,
and **every round was our instrument, not the model**:

1. **Curly quotes.** The report prints `“ ” ’`; a model transcribing writes `" '`.
2. **Page breaks inside sentences.** The Clerk's sentences run across pages, so the text
   interrupts them with the PDF's printed page footer and our own `===PAGE n===` marker.
3. **Hyphenation, four renderings of one tally** — `Yes -243`, `Yes-320`, `re - authorize`,
   and `cur-`/`rent` wrapped across a line. Resolved by comparing the character sequence
   with whitespace and hyphens removed from both sides.
4. **THE ONE THAT MATTERED.** A negative test showed the check could not catch a quote that
   is perfectly verbatim but **filed against the wrong article** — forty articles in a row
   each opening `VOTED (Yes-n, No-n...)`, so a document-wide search passes on all of them.
   Two FY2024 rows had genuinely anchored on a neighbouring article's vote line.
   `article_spans()` now requires the quote between that article's heading and the next.

**Building that check introduced its own trap, and it is the lesson to keep.** The heading
regex required `ARTICLE 6:`; FY2024 prints `ARTICLE 6.`. It found 6 headings in a report
with 26 articles and reported nearly every row as failing. **A pattern that silently matches
almost nothing reads exactly like the data being wrong** — so the result now splits three
ways, the `checked` / `check failed` / `no check` split the annual-report datasets already
use: verbatim under its own heading · verbatim under another · heading not locatable.

**The negative test is the part to re-run after any change to `norm()`.** Control passes;
a changed digit, a dropped word, swapped clauses, a paraphrase and another article's quote
all fail. A relaxation that makes any of those pass has gone too far.

### 15e. Open, and honestly unresolved

- **4 of 143 rows are verbatim but not under their own heading** (FY2023 special 10, FY2025
  annual 15, FY2025 special 5, FY2025 special 13). Two involve a **consent calendar**, which
  disposes of several articles in one printed sentence outside any article's span, and that
  is a plausible explanation for those two. **It is not tested.** The other two are
  unexplained. They are reported in their own category and not counted as passes.
- **Our minutes of 2024-05-04 say "the FY26 school and town budget".** A May 2024 Annual
  Town Meeting sets **FY2025**. A model error in a derived layer, and exactly the drift the
  annual-report extraction exists to catch.
- **Three minutes files carry impossible dates** — `2027-11-06` (Board of Assessors),
  `2027-01-16` (Architectural Preservation District Commission), `2021-11-22` (Parks).
- **39 Town Meeting recordings exist on the channel; we hold 11 transcripts.** The other 28
  have no transcript, so the 219 votes above are five years, not fifteen.
- **`office` was narrowed but not removed.** §11's checklist item stands.
- **Whether athletics-on-the-table belongs to Threads or to the budget feed is undecided**
  — the first real boundary case between the two systems.

## 16. The seven threads the new rules propose TODAY

From 40 meetings, 21 June to 19 September 2026, after excluding procedural votes and report
bundles. **None of these has been created.**

| thread | kind | trigger | closes |
|---|---|---|---|
| **The DPW union contract (Teamsters Local 170)** | contract | non-decision + **can of worms** (*"until labor counsel resolves discrepancies"*, 7 Jul, n=1) | the Select Board ratifies, or it returns to negotiation |
| **The Salary Administration Plan rewrite and comp study** | rule + money | three deferrals across two meetings, accelerating | November STM and spring ATM vote the bylaw changes |
| **The turf field and track feasibility study** | project + asset | placeholder warrant article to **borrow**, 16 Sep, passed 5-0 | Town Meeting votes the study; the study returns |
| **The sewer pump station procurement** | contract + project | a single **multi-year** contract, to Special Town Meeting | the STM article, then the award |
| **The veterans property tax exemption increase** | money + rule | scheduled step at one mention (November STM deadline) | November STM |
| **Trust fund administration during a vacancy** | rule + office | warrant article + a *"breach notice"* + a standing vacancy | the warrant article passes |
| **Athletics and extracurriculars "on the table" for FY28** | service | *"all extracurricular activities and athletics are considered 'on the table'"*, 24 Jun | **UNDECIDED** — this may belong to the budget feed, not here |

**Flagged, not opened:** football helmets and the fundraising policy review. Low reach, but
`PERSONAS.md` records a booster president telling the School Committee *"we currently have
more heads than we have helmets"*. It belongs in the declined registry **with that note**,
so it re-surfaces rather than being re-argued from nothing.

**Correctly rejected:** the Eagle Scout loafing shed; the Town Hall tour passed over; 49
excise abatements moved to the next agenda; the rec department's library-space MOU.

**And the ranking is worse than the curation.** The two highest-scored rows were report
bundles, and the DPW contract -- the clearest new thread here -- scored below them. The
§2 bar orders a list a person reads; it is **not yet good enough to cut on**, which is why
§4 says it ranks rather than deletes.


---

## 17. What running the proposer for real turned up, 19 September 2026

`scripts/propose_threads.py` exists and `--check` passes (20 threads, 11 declined, every
one still matching the record and every one carrying a closure criterion). Over the 39
meetings since 21 June it reads **36 triggered items, 19 of them already claimed** by a
registered thread, and the noise the earlier throwaway version produced -- procedural
motions and report bundles -- is gone.

Three findings from the first real run, none of them anticipated above:

### 17a. A thread must be claimable by BOARD, not only by its words

The Stormwater Task Force, 31 August: *"Agreed the warrant article should include enough
financial/rate substance for voters to understand the choice, but should not include a
draft bylaw."* That is the stormwater thread, and it was proposed as NEW -- because the
sentence never says "stormwater". **A board talking about its own subject does not repeat
the subject's name.**

So `threads.csv`'s `boards` column has to do real work: an item at the Stormwater Task
Force with no other thread claiming it belongs to that board's thread by default. This is
the mirror of the entity-versus-matter problem in §2 -- there, the entity was too broad
without a qualifier; here the qualifier is present and the entity is merely assumed.

### 17b. The bar cannot see a reach it has no words for

Lunenburg Water District, 8 September: *"MassDEP conversation on PFAS regulations,
blending, and the 2029 compliance deadline."* **Scored 2 -- near the bottom.** It is a
statutory deadline with a date, on a contaminant, affecting every water customer, and the
compliance cost lands on rates.

The `REACH` table simply has no word for *water district customers*, so a matter that
should score at the top scored at the bottom. This is the general failure of a keyword
bar and the reason §4 insists it **ranks rather than cuts**: had it cut, this would have
vanished, and nobody would have known to look. It is also a thread, and it was missed by
the manual pass in §12 entirely -- by a person, not by the detector.

### 17c. The ranking is still the weakest part, and that is now measured

In §16 the two highest-scored rows were report bundles; those are gone. But the DPW union
contract -- the clearest new thread in the window -- is claimed and so no longer ranked,
and PFAS scores 2. **The bar is good enough to order a list a person reads and is not good
enough to cut on.** Do not let a future change quietly turn it into a filter.


## 18. A closure is a REFERENCE, not a sentence — and the first four were wrong

Within an hour of seeding `threads.csv` by hand, two of its four resolved threads had
closures that do not survive contact with the record. Both were prose typed into a cell,
which is rule 2's territory exactly: *a number typed into a sentence is the only thing here
that can be silently wrong.*

| filed as | what the record holds |
|---|---|
| `solid-waste-enterprise`: *"Article Y recommended 5-0, then carried at Town Meeting"* | **The 2 May 2026 ATM record contains no solid-waste or enterprise-fund vote or topic at all** besides Article 14 (PEG access). The FinCom's 5-0 recommendation on 31 Mar 2026 is real; what Town Meeting did is unknown to us. **Returned to `open`**, with the missing document named. |
| `fourth-fire-shift`: *"moved off the override into the omnibus and retained"* | Article 10, the FY27 balanced budget, passed 340-68 -- and **the budget does not itemise the shift**. That it was retained rests on the Select Board record of 16 Mar 2026, not on this vote. Kept resolved, with that distinction written into the note (rule 7). |

So the registry stopped carrying sentences about votes. It carries `closed_board`,
`closed_date`, `closed_article` and `closed_match`, and `scripts/build_threads.py`
**resolves the motion, the outcome and the tally from the record**. Nothing about a vote is
typed by a person, and a page renders what the record says rather than what somebody
believed when they wrote the row.

### 18a. The merge happens by itself

`resolve_closure()` prefers the **official** record -- the Town Clerk's printed proceedings
in the annual report -- and falls back to **ours** (our minutes of the recording, from
machine captions) only while the first does not exist. Every closure states which it used
in `basis`, and a caption-derived one carries the as-heard caveat.

The annual report runs about a year behind, so all three resolved threads today are `ours`
and each upgrades to `official` the day that year's report is extracted -- **with no edit to
the registry.** That is TJ's *"accept the transcript version, then merge"* built in rather
than remembered.

### 18b. Precedence between motions is not cosmetic

Several motions can name one article. At the 3 September 2026 Special Town Meeting the
School Committee moved to **support** article 3 before Town Meeting moved the transfer
itself, and matching on the article number alone picked the supporting motion and called it
the closure. The order is: the number **and** the subject, then the subject, then the
number.

### 18c. The build refuses rather than writes

`build_threads.py` will not write if a thread says `resolved` and its closure does not
resolve to a vote, or if any thread has no closure criterion. Verified by breaking both
deliberately. A registry that quietly accepts an unresolvable closure is how the typed
prose survived in the first place.

---

## 19. The QA pass, 19 September 2026 — five defects, and what each one teaches

The registry, the resolver and the pages were built in one sitting and then read
adversarially. Every finding below was in shipped code.

### 19a. The rule in §2, broken by the person who wrote it

§2 says a thread matches an **entity AND a qualifier**, and gives Turkey Hill as the worked
example. Both Turkey Hill threads were then seeded matching the bare entity, `turkey hill`,
because **the schema had no column to put a qualifier in**. The result: the ADA thread's
items were **46 of 46 shared** with the rebuild thread — one thread rendered twice, on a
page whose whole purpose is to separate matters.

`qualify` is now a column. Shared items fell to 1.

**The lesson is about schemas, not attention.** A rule written in prose and given no field
to live in will be broken by whoever fills the file in, including its author on the same
day. If a rule constrains the data, the data shape has to be able to express it.

### 19b. `started` and `match` were compensating for each other

Every thread's pattern was checked against the whole record rather than its own window, and
almost all of them claimed items from years before the matter existed:

    sap-rewrite             matched a DIFFERENT YEAR'S salary schedule article, 2022
    middle-school-sports    matched a citizen petition about the SEWER SERVICE AREA MAP
    solid-waste-enterprise  matched solid waste removal at Woodruff, 2022

None of those is the matter. None was excluded by a pattern — all were hidden by a date.
**Two mechanisms, each covering the other's weakness, which is the shape every compensating
error in this repository has had.**

A pattern general enough to be useful — `surplus`, `salary schedule` — cannot be made
precise, so the answer is not to fix the patterns. It is to **count what each one would
claim outside its own window and print it**, so a thread leaning on its start date is
legible as one. Writing qualifiers took the worst from 56 to 8.

And the check found one genuine error the compensation was hiding: **`kids-kingdom` began
eight months before the date it was given** — the School Committee was *"split on the Kids
Kingdom move"* in February 2025.

### 19c. Our vocabulary was rendering to residents

`note` is the registry's own margin — *ENTITY vs MATTER*, *CAN OF WORMS trigger, at n=1*,
*POLYSEMY*, *IRREVERSIBLE* — and the thread page was drawing it under the heading **"What
this does not show"**. Rule 7b's second named failure, on the exact page most likely to be
quoted.

`note` is no longer published at all. `caveat` carries the reader's half, in English, and
each one says what the record does NOT establish rather than what we found clever about it.

### 19d. The style pass: invented colours, and a second copy of a scale

The page used `--border`, `--ok`, `--warn` and `--bg`. **None exists in this stylesheet**,
so every hardcoded fallback was what actually rendered — three off-palette values that
ignore the theme. It also carried its own two-state provenance badge, when
`components/Basis.tsx` already holds the scale and says why there may only be one: *"two
copies of a scale is two scales."*

Our captions are `stated` — *a document says so and nothing independent checks it*. The
Clerk's printed record is `cross-checked` **only where a recording of the same meeting
exists to set against it**; where the report is the only record it is authoritative and
still unchecked, so it stays `stated`. Overstating the Clerk is the same failure as
overstating the captions, pointed the other way.

Three structural fixes came with it: each landing section now means one thing (the groups
browse OPEN threads; Settled owns the archive) instead of showing one row three times; the
chronology runs newest-first while open and start-to-finish once settled, which is what
§14d said and the first cut did not do; and `/threads/<unknown>` says so rather than
silently rendering the index.

### 19e. A regex that hung for three hours, and left correct data behind

`PAGE_BREAK` was `\s*\d{0,4}\s*===PAGE \d+===\s*` — **two unbounded `\s*` either side of an
optional number, leading the pattern.** At every position inside a whitespace run the engine
tries every way of splitting that run before failing to find the literal, and an OCR'd
annual report is mostly whitespace. On the 648 KB FY2018 report it did not finish in three
hours.

**The dangerous part is not the hang. It is where the hang was.** It came *after* that
year's rows were written, so the backfill had correct data on disk, a live process, and no
output — and was reported as running for three hours. A failure that leaves the data right
and simply stops is the hardest kind to see.

Two literal-anchored passes replace it: remove `===PAGE \d+===`, then remove lines holding
nothing but one to four digits. Both start with something fixed, so the engine has one
place to try per position instead of hundreds. `--check` went from not finishing to **0.38
seconds**, and it now covers all 263 articles rather than the 143 it had managed before.

> **Never lead a pattern with `\s*` before a literal**, and never let a long-running job's
> progress travel through a pipe that buffers — the last run went through `grep`, whose 4 KB
> buffer held a year's output invisibly. `python3 -u`, and the shell writes its own markers.

### 19f. What the check now says, in three numbers

    251 of 263 verbatim UNDER THEIR OWN ARTICLE HEADING
     10 verbatim, but under another heading
      2 whose heading could not be located, verified against the document only

The 10 are now a pattern rather than a mystery: *"VOTED TO POSTPONE INDEFINITELY Article
20."*, *"Article 4 was PASSED OVER."*, *"ARTICLE 10 W AS P ASSED OVER"*. **A consent
calendar disposes of several articles in one printed sentence, outside any article's span.**
Four of the ten are that shape. It is a real feature of the document and not an extraction
error — and it is still reported separately rather than forgiven, because the remaining six
are not yet explained.
