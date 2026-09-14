# The budget season, as a thing with parts — a proposal to agree on

TJ, 14 September 2026: *"we need standard conventions for every one of these 'seasons' to
work, and be tracked. As very specific things. That info can be captured retroactively or
built from meetings that are happening and documents being produced, discovered in our
refresh, which should auto-feed the budget feed. But we have to agree on what to look for,
how to categorize it, how to bucket it, and how to present it."*

**Status: PROPOSAL. Nothing below is built. Edit this, then we build to it.**

---

## 0. How it actually goes — TJ, 14 September 2026, in full

*"The school announces a deficit in January. Sometimes they present an initial impact set,
with some potential cuts that are on the table. The school committee agrees to nothing.
They argue. The town citizens get involved. Over the next 3 or 4 meetings, citizens
advocate to not cut the things they want, and the schools adjust their cut proposals. At
the same time, they find money and lose money, so the deficit number changes by hundreds
of thousands. They even make mistakes — 2 years in a row they had duplicated $500k or
something like that, so the deficit changed by quite a lot after a single meeting. The
meetings focus on different things. Sometimes sports. Sometimes special education. Then
they put out an official proposal for the budget, which includes degrees of budgets —
level service, core services, balanced budget, restore, etc. Not the same every year. But
each one comes with pros/cons, cuts and saves. Then they negotiate what to save and what
not to save from the budget. So citizens find it hard to track what cuts are still on the
table, and if they should advocate for their family. Like, when band was being discussed,
it rallied the band families to come speak, which pulled it off the list. While all this
is happening, the town manager works with the select board to discuss budget options.
People talk about whether an override should be filed. Sometimes a citizen files a
citizen petition for an override, gets it approved, then presents information to various
committees. The petition has dollar amounts, cuts and saves. The committees agree or
disagree, vote to recommend or deny. Warrants close. Last-minute changes — new money is
found. Additional proposals are made, like using free cash this year, or shifting money
around to reduce the deficit. Then the final deficit and budget numbers land. The
committees have hearings, vote, and finalize the things that will be brought to town
meeting. Then town meeting decides. So keeping citizens aligned on all those happenings —
to know what the current state of all that is along the way — is critical."*

**What that says the page is: a STATUS BOARD, not a feed.** At any moment a resident
needs, in this order:

1. **The deficit now** — the number, when it last changed, by how much, and *why* (money
   found, money lost, a mistake corrected, a state figure landed). And its path.
2. **The cuts now** — three columns: **still on the table** · **came off** (and what pulled
   it off: "band families spoke, 4 Mar") · **decided**. Grouped the way families think:
   sports, band and music, transportation, special education, teachers by school, etc.
   *This is the column a family reads to decide whether to show up.*
3. **The proposals** — once the official tiers exist (level service / core / balanced /
   restore — different names every year), each with its $, its cuts and its saves, side
   by side. Before they exist: "not yet — usually late February."
4. **The override track** — is one being discussed, filed (by the town or by petition),
   for how much, with what cuts and saves attached; each committee's position on it
   (recommend / deny / not yet), with dates.
5. **Late moves** — free cash, transfers, new revenue, anything that changed the number
   after the warrant closed.
6. **What goes to Town Meeting** — the articles as they will be voted; then the result;
   then what took effect.

Each block has a **now**, a **changed since last meeting**, and a **history** (the thread).
The nine milestones in §1 are the moments those blocks flip from "not yet" to a fixed
value; the extraction feeds the "now" and the history between milestones.

**What makes a past season useful under the same board:** FY26 with every block at its
final value and its history is exactly the story of FY26 — no override filed, the gap
closed by X, the cuts that stood. Same board, no "live" column.

## 1. The unit: a season is a fixed sequence of milestones — the ALARMING ones only

TJ: *"we only need the alarming info. We don't need total revenues or the total budget.
We just need the amounts that cause issues, like a deficit."* So no revenue forecast, no
budget total. A milestone is *a moment where a number or a list that hurts gets fixed by
somebody with the standing to fix it.* Each has: who fixes it, what it fixes, the proof,
and how we find it — live and retro. If it hasn't happened, the page says "not yet".

| # | milestone, in plain words | who | fixes | proof | how we find it (live) | retro |
|---|---|---|---|---|---|---|
| 1 | **The gap** | Superintendent / Town Manager | the shortfall ($), school and town, as first stated — and as it moves | said at a meeting; the preliminary budget presentation | budget-state `deficit`, staff-ranked; documents watch on the presentation | the presentation + our minutes |
| 2 | **The choices** | Superintendent | the scenarios / tiers, each with its $ and its cut list (FTE, programs, expense) | scenarios document; meeting | budget-state cuts by scenario name; documents watch | the scenarios document |
| 3 | **The School Committee picks** | School Committee vote | which scenario; the override ask ($) | vote in our minutes | vote motion `scenario` / `override` | our minutes / town's minutes |
| 4 | **The town's cuts** | Town Manager → Select Board | what the no-override budget removes on the town side | balanced budget document; vote | documents watch; vote `balanced` / `omnibus` | the balanced budget document |
| 5 | **Override on the ballot, or not** | Select Board vote | the question(s), amount(s), tiers | vote; warrant | vote `ballot` / `override question` | warrant |
| 6 | **Finance Committee says** | FinCom votes | recommend / not, per money article | votes | vote `recommend` + article | FinCom report in the warrant |
| 7 | **Town Meeting appropriates** | Town Meeting | the appropriation ($), contingent or not | warrant results | results CSV; town's minutes | annual report |
| 8 | **The vote at the polls** | the election | passed / failed, tallies | printed results | `ballot-questions.csv` | same |
| 9 | **What actually took effect** | School Committee / Select Board | the cuts that stand (FTE, programs, expense); anything restored later | adoption vote; a later STM | aftermath cuts; special episode outcome | our minutes; the adopted budget |

Nine. FY26 had no override: 5 = "none placed", 8 = "no question" — still rows.

## 1a. The calendar is the town's official one, not our agenda windows

TJ: *"the calendar should match the town's calendar from the clerk. This is the town's
official dates."* We hold it, in pieces:

- **The Charter and bylaws** fix the shape: the Town Manager presents the preliminary
  budget *by mid-February* ("as required by the Town Charter" — the FY23 presentation,
  page 2); the Finance Committee holds its hearing; the warrant opens and closes on dates
  the Select Board votes ("Warrant Open, 1/10/23 – 3/20/23" on FY23 agendas). The bylaw
  text in our archive says the Annual Town Meeting "shall be held on the first Saturday in
  April" — but the last two were 3 May 2025 and 2 May 2026, so the ACTUAL date is read
  from the Select Board's vote and the warrant each year, never assumed from the bylaw.
- **The Town Manager's preliminary budget presentation** carries a *"Budget Calendar"*
  page every year (FY23: page 45 — department presentations from 24 Feb, House Ways &
  Means end of April, Senate end of May, Town Meeting 7 May, state budget by 30 June,
  state aid final by July) and the **FinCom budget meeting schedule** (page 46, every
  department by date). `a74-fy23-preliminary-budget-presentation`, and its siblings for
  FY21, FY24.
- **The Select Board** votes the warrant open and close dates; **the Town Clerk** posts
  the election. Both are in our minutes and in `budget-cycles.csv`.
- The district's own **"FY22 Budget Schedule"** (district-budget index) is the school
  side's version.

So per season the calendar is a short list of OFFICIAL dates — preliminary budget due,
FinCom hearing, warrant closes, Town Meeting, election, state budget — each from one of
those documents, with the milestone it belongs to. Retro: read off that year's
presentation and warrant. Live: the new presentation arrives through the documents watch
and the dates are proposed from it. The agenda-window calendar is retired.

## 2. The buckets: three, by who has the last word

Unchanged from what we agreed today:

- **FINAL** — milestones 7, 8, 9. Town Meeting and the ballot. Never a board vote.
- **THE STORY** — milestones 1–6, each a fixed point, and the threads between them.
- **SAID** — everything else on the record: figures stated, cuts floated, warnings.

A thread is a story *about one milestone's number*: "how did the gap go from $2.4M to
$566k" is the story of milestone 1; "how did the tiers get sized" is milestone 5's. So
threads are named by the milestone they feed, not invented from data.

## 3. Where the data comes from — one table, one CSV per season

`sources/data/budget-seasons/fy27.csv` (one row per milestone, plus one per thread event):

    milestone, date, who, figure, list, source, how, status

- **Retroactive** (FY26, FY27): written by hand from the documents we hold, checked against
  them, each row citing its proof. This is a day's work per season and it is what makes
  FY26 useful — no extraction needed for nine rows.
- **Live** (FY28): the refresh proposes rows — "milestone 2 may have happened: budget
  presentation on the School Committee agenda, 12 Feb; figure as heard $28.5M" — and a
  person confirms by keeping the row. The detectors already exist (agenda markers, vote
  motions, budget-state figures, documents watch, ballot CSV); what changes is that they
  write *to the milestone table* instead of to the page.

The extraction (statements, cuts, warnings) stays what it is: the raw record that threads
and SAID are built from. It stops being the thing the page is organised around.

## 4. How it is presented — the status board, top to bottom

1. **One line.** "FY27: the gap is $566k (was $2.4M in January), 41 cuts still on the
   table, two override tiers on the ballot 16 May." Generated; blanks skipped.
2. **The deficit now** (block 1) — the number big; under it "last changed 18 Mar, down
   $302k: four classroom teachers cut from the count"; then the path as a small chart or
   list.
3. **The cuts now** (block 2) — three columns, grouped by family, each item with FTE or $
   as heard, who named it, and for "came off": what pulled it off. A family filter is the
   most useful control on the site.
4. **The proposals** (block 3) — the tiers side by side, or "not yet".
5. **The override track** (block 4) and **late moves** (block 5) — short.
6. **What goes to Town Meeting / FINAL** (block 6) — as now.
7. **Changed since** — the change log for the last meeting or week, in one place.
8. **Meeting by meeting** — as now, below everything.

The calendar is not a section: each block carries its official date ("preliminary budget
due mid-Feb", "warrant closes 20 Mar", "Town Meeting 2 May") beside its status. **It
must read the same for FY26 (retro) and FY28 (live)** — same blocks, same words.

## 5. What we have to agree on

- [ ] the nine milestones, and their names in citizens' words (edit the table)
- [ ] the official-date list per season, and which document each date is read from
- [ ] that a milestone is *fixed by standing*, so a resident's figure never fixes one
- [ ] the CSV shape, and that a person confirms live rows before they show
- [ ] that FY26 and FY27 get written retroactively by hand first, before any detector work
- [ ] retire: the agenda-window calendar; the kind/scope metric cards; auto-detected threads
      as the primary structure (keep the detector as a proposer only)

Once agreed: FY27 by hand (so we can see the shape on real data), then FY26, then the
detectors pointed at the table, then FY28 live.
