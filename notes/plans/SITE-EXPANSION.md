# Two doors, not one: a plan for opening the finances up

**Written 7 September 2026, from TJ's brief.** Not started — this is the plan to argue with
before anything moves.

---

## The problem, stated exactly

The site today is **one curated path**. It answers a specific question — *why does this
budget break, and what would fix it* — and every page is a step in that argument. That is
why it works.

Meanwhile the archive has grown far past what the argument uses: 72 tables, 66,831 rows,
3,877 documents, a money-flow model for the schools and for the whole town, a queryable
API, and a growing set of structural findings about how the town's money actually moves.

**Adding that to the existing pages would wreck them.** TJ: *"if we put everything we have
and more on the pages we have, it gets overwhelming."* The argument pages are load-bearing
precisely because they are narrow. The reference material is valuable precisely because it
is broad. They are different products for different visits, and one page cannot be both.

There is also a third thing with nowhere to live at all: **what we have learned about how
the town's financial structure works.** Rule 11's whole subject — net vs gross, four money
systems, every special revenue fund being a school fund, the tier below 3 that no report
reaches. None of that is an argument about FY28 and none of it is a document. It is
currently scattered across handoffs and commit messages.

---

## The shape: a landing page with doors

`/` becomes a **chooser**, not a chapter. Small, fast, and honest about what each door is
for — a reader picks their depth rather than being walked down one corridor.

| door | for | what it holds |
|---|---|---|
| **Understanding the budget** | a resident with a question about the override, the schools, their tax bill | everything the site is today: the walkthrough, the situation, bend the curve, build your own budget, what solved requires |
| **The money, explained** | anyone asking "how does this actually work" | the structural findings. Where money comes from, where it goes, who decides. The money-flow diagrams, follow the money, who decides, the ledger structure |
| **The data** | a reporter, a committee member, a resident checking a number | the schema page, charts over time, the query tool, the archive of documents |
| **For AI assistants** | agents | `/agents`, `/ask`, the API. Already built, currently hard to find |

**Three doors would be better than four if two of the middle ones merge.** That is the
first thing to decide — see *Open decisions*.

### On the name

TJ asked for a better word than "Finances". The problem with it is that it is the name of a
department, so it reads as *the Finance Committee's page* rather than *the town's money*.

| candidate | for | against |
|---|---|---|
| **The money** | plain, short, reads aloud, matches how people actually ask | slightly informal |
| **How the money works** | says it is explanatory, not a data dump | long for a nav item |
| **Town finances** | unambiguous | reads institutional; sounds like a department page |
| **Follow the money** | already a page name here | would have to be renamed or absorbed |

**Recommendation: "The money"** as the door, with the standfirst carrying the precision.
It is the phrase a resident already uses, and it sits beside "Understanding the budget"
without either sounding like the other.

---

## What already exists and would move in

Nothing here needs building. It needs a home and a route.

| built, and currently unreachable from the site | would live under |
|---|---|
| `notes/reference/data-model/schema.html` — 72 tables, semantics, live query modal | The data |
| `notes/reference/data-model/school-money-flow.html` | The money |
| `notes/reference/data-model/town-money-flow.html` | The money |
| `notes/reference/data-model/who-decides.html` | The money |
| `notes/reference/data-model/follow-the-money.html` | The money |
| `notes/reference/data-model/money-in.html` | The money |
| `notes/reference/LEDGER-STRUCTURE.md` | The money |
| `notes/reference/MONEY-NODES.md` | The data |
| `/api/query`, `/api/index` | For assistants + The data |

**Every one of these is generated and `--check`ed already.** That is the good news and it
sets the pattern: a page that ships here is a page a script reproduces.

## What would be new

1. **Charts over time, for the questions people actually ask.** Athletics by year. An
   account or a category's spend by year. Revenue by class by year. Enrollment against
   spending. The point is that a resident should not have to write SQL to see a line go up.
   - *Constraint:* most series are shorter than they look. `revenue_history` is five
     checked years; `special_revenue_funds` is fifteen years and **zero** checked. A chart
     drawn over unchecked data is the most confident-looking wrong thing this project could
     ship. Every chart states its coverage and its `status`, or it does not ship.
2. **The structural findings, written down.** The thing with nowhere to go. Each one as a
   short piece with its evidence and, per rule 7, what it does *not* establish.
3. **A query page** — the schema page's modal, as a first-class page.

---

## The constraints that actually decide this

**1. A URL is an interface, and `/` is currently the walkthrough.** Making `/` a chooser
changes what the single most-linked address on the site shows. That is legitimate and it is
not free: the walkthrough needs its own slug, `/` needs to keep serving something sensible
to everyone who has bookmarked it, and `check_moved_docs.py` needs to cover the move. No
existing address may 404.

**2. The sitemap, `llms.txt` and the GitHub mirror are generated from the route table.**
Adding routes is cheap; forgetting to regenerate is the failure. `check_sitemap.py`,
`check_github_mirror.py` and `build_agent_endpoints.py` all have to pass before it ships.

**3. Anything that queries D1 at page load spends the read budget.** The free tier stops at
5 million rows read a day, and one join reads 19,006. A charts page that fires several
queries per visit is a different cost profile from today's entirely static site.
**Pre-render the series into JSON at build time; keep live querying to the explicit query
tool**, where the reader chose to run it.

**4. Rule 3 travels with the data.** Anything we estimated says so, in that colour,
wherever it appears. Moving a figure to a new page does not shed its provenance.

**5. Nothing deploys without being asked** (rule 10), and this is big enough to want a
branch and a preview URL before it touches the live site.

---

## Phasing

Each phase ends somewhere shippable, so none of it is a long dark tunnel.

- **Phase 1 — the doors.** New landing page; walkthrough moves to its own slug with `/`
  preserved; nav reworked to two levels. Nothing else moves. *Ships on its own.*
- **Phase 2 — move what exists.** The generated reference pages get real routes, real
  styling and a place in the sitemap. Big visible gain, almost no new writing.
- **Phase 3 — the findings.** The structural conclusions written up, each with its evidence
  and its limits.
- **Phase 4 — charts.** Pre-rendered series, each stating its coverage. Start with
  athletics and revenue-by-class, which are the two with checked data behind them.
- **Phase 5 — the query tool** as a page, with the schema page as its reference.

## Open decisions — for TJ

1. **Three doors or four?** "The money" and "The data" could be one door with two sections.
   Four doors risks the chooser needing a chooser.
2. **Does `/` become the chooser, or does the chooser live at `/start` with `/` staying the
   walkthrough?** The second is safer and weaker.
3. **Is "The money" the right name**, or does it need to say "town" in it?
4. **Do the reference pages get restyled into the app**, or are they linked out as the
   standalone generated pages they already are? Restyling costs real effort; linking out is
   honest and slightly jarring.
5. **How much of the crisis argument moves under its door** versus staying at top level —
   `/sources` and `/reports` in particular are cited externally.
