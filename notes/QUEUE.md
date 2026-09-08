# What is queued, in order

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

## 8. Staffing, in FTE, against funding and cost

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
