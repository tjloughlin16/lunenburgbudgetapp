# Where we left off — 9 September 2026

Written at the end of a long session. Everything below is committed, pushed and
deployed unless it says otherwise.

## Running when this was written

- **D1 IS PUSHED AND CURRENT.** 99 tables, 117,775 rows, verified by `sync_d1.py --check`
  and by querying the new tables live. Every DESE table and `stated_cuts` are now
  answerable through `/api/query`.

  **Two things this settled, after a day of guessing at both:**

  The failure was never the quota. It was a stale wrangler OAuth token that had lost its
  `d1 (write)` scope and come back with `account (read)` alone — `code 7403`, which reads
  like an account problem and is a credential refresh. `npx wrangler login` fixed it.
  **When D1 refuses, check `npx wrangler whoami` for the scope list before assuming
  anything about limits.**

  And the quota does not bind the way this script's own warning says. It prints
  "~235,550 writes with indexes — the free tier allows 100,000 a day" and then the import
  succeeded in one pass at 117,902 statements. An import is not billed as rows x 2, so
  that warning is pessimistic. Nobody should buy a plan on the strength of it. The
  earlier exhaustion on 5 September was FOUR full re-imports in one day, which is a
  different thing from one.

- 18 tables are in the local database and not in the published one — every DESE table and
  `stated_cuts`. Until the push lands, querying them through the API returns
  `no such table`, including from the schema page's own modal.

## Blocked, with a date

- **YouTube transcripts. Test ONCE on Thursday 10 September**, not before. The caption
  endpoint IP-blocked us after ten fetches and had not lifted after six hours; retrying is
  what makes it last. The one-shot test is written in `notes/QUEUE.md` under the YouTube
  section. If still blocked, the options are a residential proxy or accepting that
  captions are not obtainable at scale. **Do not use `yt-dlp --cookies-from-browser`** — it
  authenticates as TJ and attaches scraping to his own Google account.
- The **video index is done and committed** regardless: 4,671 recordings, classified into
  2,857 meetings across 40 boards, and it already answers the thing that mattered — which
  231 meetings have no other surviving record, 162 of them School Committee.

## Half-finished, both agents killed by a rate limit mid-edit

Neither left the tree broken; both were recovered enough to build and commit.

- **`/what-sports-cost`** — still needs its conclusions rewritten to the enforced contract,
  and needs to say plainly WHAT IS COUNTED. The athletic director, the trainer and
  insurance ARE in the town's appropriation and are NOT in the district's per-sport
  workbook, which is a large part of why three published totals disagree by 1.88x. And
  facility costs cannot be attributed at all — grounds, custodians and utilities are
  whole-school lines with nothing splitting out athletics. Register that gap.
- **`/school-staffing`** — the district-wide and per-subject work landed. Still owed: the
  per-school breakdown, general education against special education
  (`dese_teacher_program_area`), and the counsellor / social worker question
  (`dese_educator_workforce`, minding the rollup trap that once turned 14 administrators
  into 28).

## The document to read next

**`notes/process/WHAT-DECIDERS-NEED.md`** — 979 lines, written today, demand-first: what
the Town Manager, Select Board, Finance Committee and School Committee actually decide,
when, and what would change the answer. TJ was part-way through reading it.

It names four things nobody has analysed. **The cut register was the first and is now
built.** The other three are not:

1. **Enrolment as its own report.** `dese_enrollment`, 1,194 rows, 1992–2026, per school,
   with disability, English-learner and low-income counts. Read by NOTHING. It is the other
   half of the staffing argument: enrolment 1,824 → 1,568 while English learners went
   3 → 70 and the low-income share 10.0% → 25.2%.
2. **Ballot questions.** `ballot_questions`, 7 questions 2012–2025 with precinct tallies,
   read by nothing — while `/overrides` models override arithmetic without ever consulting
   how this town actually votes. Cheapest item on the list.
3. **No forward enrolment projection exists anywhere in the archive.** Zero hits across
   3,877 documents. Enrolment drives Chapter 70, per-pupil spending, staffing and the MSBA
   case, and nobody projects it.

Also unread: `balance_sheet` (774 rows — the only STOCK table in an archive of flows),
`report_debt`, `report_capital_projects`, `dese_circuit_breaker` as a 21-year series.

## Dated and close

**A Special Town Meeting is called for 17 November and its warrant closes 17 September at
5 p.m.** Anything meant to reach that meeting has to exist before then.

And from the FY27 calendar reconstructed out of the minutes: **anything that will change a
number in the budget must land before mid-February.** After that the argument is about a
document rather than about the figure.

## Still TJ's

- **D7, the records request.** Top item is now EPIMS' federal salary source per individual
  — the thing that would settle which fund pays which post. Then the fee schedules the
  family-costs page is missing: the adopted transportation fee schedule and the adopted
  student activity fee schedule, both real charges TJ has paid, neither published.
- **D3**, the tax-rate and town-meeting extraction.
- The nine unpriced charges on `/what-families-pay`. Values drop into the `HOUSEHOLD` list
  in `scripts/build_rate_register.py` around line 93 — a row with an empty value already
  renders as a named unpriced charge, so filling them in is data entry rather than a
  rebuild.

## Two things about how to work here that cost time today

- **Do not run several agents that each build.** `npm run build:site` spawns Chrome on a
  fixed port and shares `dist/`; briefing agents to "check before building" does not work
  because check-then-build races. One agent builds, at the end. Written up in CLAUDE.md
  under "Several agents in one working tree", along with the `git checkout` incident that
  destroyed five uncommitted rows of another agent's work.
- **`tsc -b` is not a syntax check.** It reads an incremental cache and passed a file Vite
  could not parse. For anything hand-edited, parse it with `@babel/parser` (jsx +
  typescript plugins), which is what Vite actually uses.

## Next session, first thing: classify the remaining 48 conclusions

`bearing` is now in the conclusion contract (`scripts/conclusions.py`), validated,
published and counted on the synthesis page. Two values:

- **`sizes`** — establishes how big something is, or how it got this way. Context. MOST
  conclusions are this and that is correct; you cannot act on a problem nobody has sized.
- **`lever`** — points at something a body in this town can actually decide. A fee, a
  vote, a schedule, a request.

**1 lever, 1 sizes, 48 unclassified** as of this commit. The count is published, so the
gap is visible rather than quiet, and nothing defaults — an unjudged conclusion is not the
same as one judged to be context.

**Rule 8 holds:** name what can be pulled and what it costs somebody. Never say which to
pull. `lever` is not a recommendation.

Candidate levers on a first read, to be argued rather than accepted: the fee schedules
(`families`, `sportsmoney` — set by School Committee vote); health insurance plan design
(`insurance` — `/bend-the-curve` already models 75/25 → 70/30); and the cut register
(`cuts`), because FY2020 proved a published cut list is negotiable, three of eight
withdrawn in four weeks.

Likely `sizes`, not levers: Chapter 70 minimum aid and the rising state minimum — nobody
in Lunenburg controls the Legislature's floor; the peer and outflow comparisons; the
special education trio; staffing.

Also owed on this page, from the same conversation: **render the eight-step "how Chapter 70
actually works" walkthrough**, which is in `minimum-aid.json` as `how_it_works` and not yet
on the page.

## And a real defect a reader found

**`/where-students-go-instead` does not count private schools and does not say so.** A
reader asked why Cushing Academy is absent. It is absent because DESE's town-enrolment file
covers PUBLIC districts only — every reason in it (school choice, charter, foster care,
foreign exchange, tuitioned-in) is a public mechanism, and Massachusetts keeps no statewide
register of private-school enrolment by town of residence.

So 177 is a floor, not a total, and the page reads as though it were a total. Owed: a title
and standfirst that say PUBLIC, and a gap row naming what would close it — the district's
own October 1 resident census, or the town census, either of which counts resident children
regardless of where they enrol.

**It matters in the opposite direction from the rest of that page.** A student at a private
school costs the town no tuition and no assessment, and barely moves Chapter 70. Private
departures are close to free for the budget — the one group whose leaving does not cost
money — and the page cannot count them.

## STILL OPEN: `dese_sped_movement` is unread. (Grade span was already published — my error)

Found 9 September, verified, not built.

`dese_sped_program`, `indicator_category='Grade Span'`, `geo_level='district'`,
`lea='01620000'` — six years, five bands, reconciling to the published total
(`reconciles='yes'`, parts sum to `Total Students with Disabilities`):

        fy    PK-2   3-5   6-8   9-12   >12   total
      2021      87    59    51     56     8    261
      2022      64    61    44     49     9    227
      2023      66    54    63     45     6    234
      2024      61    57    60     47     8    233
      2025      70    47    68     51    12    248
      2026      68    55    70     55    10    258

**TJ caught this: `grade_span` is already in `sped-students.json` and already on the page.**
The note below was written as though it were missing. What follows about the numbers still
holds; what was wrong was the claim that nothing publishes them.

**The total is flat and the distribution is not.** 261 → 258 overall, while PK–2 fell 19
and Grades 6–8 rose 19 — a stable headline concealing a complete shift underneath.

**THE REAL GAP IS `dese_sped_movement`, WHICH NOTHING READS.** It has two things grade span
does not:

- **Individual grades**, not five bands. FY2024: Grade 5 is 29 of 147 on an IEP (19.7%)
  against Grade 10 at 7 of 120 (5.8%) — a threefold spread the bands hide.
- **`moved_in_cnt` and `moved_out_cnt`** — children moving ONTO and OFF an IEP during the
  year. That is a FLOW, and it is exactly what separates "a cohort moving through" from
  "fewer young children identified", which the grade-span chart raises and cannot answer.

Moved off, by year, district total: 40, 19, 28, 28, 21, 17. Moved on: 28, 24, 19, 33, 23,
38. **FY2024 is the crossover — 38 on against 17 off**, more than two joining for every one
leaving, and moving-off has fallen every year since FY2021.

**THE TRAP, and it nearly caught me:** FY2025's row is byte-identical to FY2024's and is
flagged `repeats_prior_year='yes'`. DESE republished the year unchanged. **Never sum
FY2024 and FY2025 as two years of movement.** The registry warned about this exact pair at
ingest and the extractor set the column so nobody could miss it.

**TWO READINGS FIT AND THIS DATA CANNOT SEPARATE THEM** — write it that way or not at all:

- a cohort moving through. The 87 identified in PK–2 in FY2021 would reach Grades 3–5 by
  FY2024 and middle school by FY2026, and 6–8 does rise 51 → 70 across exactly that window.
- fewer young children being identified, which is a different fact with different
  consequences for what the district should staff for.

These are annual snapshots, not children followed through time. `dese_sped_trajectory` is
cohort-shaped and may settle it; check before writing either sentence.

**Why it is worth doing:** out-of-district placement clusters at the older end and costs
most there. If the bulge is real and moving, the expensive years are ahead rather than
behind — which is a forecastable thing on the one line the town most wants to forecast,
and nobody has it.

Also note `Special Education Beyond Grade 12` — 10 students in FY2026, post-secondary
placements a district funds to age 22. Small count, typically the costliest placements,
and never mentioned anywhere on the site.

Grade SPAN, not individual grade. DESE publishes the five bands and no finer.

## DONE 10 Sept: 603 CMR 28 is ingested. Kept for the reasoning, and for what it still cannot settle

Asked 9 September: is there a legally defined ratio of paraprofessionals to students on an
IEP, by classroom setting? **Nothing in this archive answers it, and the archive should
hold the answer.**

**What exists here now, separately and never crossed:**

- `dese_sped_program`, `indicator_category='Special Education FTEs per 100 SWDs'` —
  paraprofessional FTE per 100 students with disabilities, DISTRICT-WIDE only.
- `dese_sped_program`, `indicator_category='Placement'` — FY2026: Full Inclusion 183
  (70.9%), Substantially Separate 41 (15.9%), Partial Inclusion 16, Separate School in
  District 2, of 258.

Nothing joins them. Nothing in the archive says how many paraprofessionals a substantially
separate classroom has against an inclusion classroom.

**The regulation is 603 CMR 28.06(6)** and it is public. Its SHAPE — stated here as shape
only, because the specific maximums were recalled rather than read, and a recalled figure
quoted at a Finance Committee meeting is the exact failure rule 13 exists to prevent —
is a maximum number of students per certified special education teacher, **with a higher
maximum permitted when an aide is present.**

**DONE.** `sources/state-dese/603cmr28-special-education-regulations.html`, sha256
`33943cfe…`, from `https://www.doe.mass.edu/lawsregs/603cmr28.html?section=all`, text
extracted, catalogued, pushed to R2. The rule is 28.06(6)(d): eight students to one
certified special educator, or twelve to an educator AND AN AIDE. A page is being built.

**Then the analysis that matters.** If an aide is what PERMITS a larger class rather than
being a ratio in its own right, then paraprofessional counts track PROGRAM STRUCTURE and
not student headcount. That would be a real explanation for the thing `/school-staffing`
measures and cannot explain: paraprofessionals rising while enrolment fell.

And it speaks straight to the argument the Finance Committee and the School Committee are
having. If the regulation requires roughly the staffing Lunenburg has for the 41
substantially separate students it reports, then "did we add too much staff" is not a
question about judgement at all — it is a question about how many children have plans
requiring that setting. **That reframing is worth more than either side's current number.**

**What it cannot settle**, and say so on any page that uses it: the regulation sets
MAXIMUMS, not requirements. A district may staff above them. And an IEP can specify
one-to-one support for an individual child regardless of class size, which no ratio
predicts and no published count reveals.
