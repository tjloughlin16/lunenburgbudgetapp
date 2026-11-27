---
name: building-a-page
description: How to build or review a topic page or hub on this site -- the "what it means" rule, choosing the page's shape (matrix, timeline, panels, checks, custom diagrams) instead of the default template, the limits the build enforces, and the review checklist. Load before writing or changing any generator under scripts/build_*topics*.py, any topic registry, or any page TJ asks to review, consolidate or make more interesting.
---

# Building a page

CLAUDE.md rule 7h is the short version. This is the working detail, kept out of the
always-loaded file to save context. The two ideas that matter most, in TJ's words:

1. **Every figure arrives with what it means.** *"put the conclusions as insights, following
   the 'what it means' pattern so we dont put important metrics without an insight to
   understand them"* (25 October 2026). A reader should be able to draw a conclusion, not
   just see a fact.
2. **A page takes the shape of its subject.** *"since we simplified the pages, they are losing
   some of their power ... 1 paragraph, a chart, metrics, a few conclusions, and sources.
   Thats relatively boring"* and *"you can build diagrams, charts, or whatever on the fly even
   if we dont have templates for them"*. The pages had started to look identical while their
   subjects were very different.

## THE TEMPLATE IS GONE (31 October 2026). Compose the page

TJ: *"this page is so boring now!"* ... *"we need to just outright remove the topic building
template"* ... *"we need to hold the big CONCEPTS in there, but not the designs."* A topic page is
now `flow=[...]` in `TP.page()`: the parts in the order a reader meets them, and `Topic.tsx` draws
exactly that. Nothing but sources is mandatory. Worked example:
`scripts/build_school_receipts_to_town.py`.

**The concepts (TJ's list), not a layout:** a signature image at the top that IS the page;
conclusions; metrics with units; short; hub and spoke for every detail. If your page looks like
the last page you built, it is not showing its data the best way.

**THE LADDER IS CLOSED TOO (20 November 2026).** TJ, on capital pages that were composed and
still ended in a grid of facts and a list of conclusions: *"you followed the base template agai
:("* ... *"cut the usage of templates anyhere"*. Every composed page that day drew `'ladder'`,
because it was the only part that held conclusions, so composing still ended in the template's
back half. Now:

- **A conclusion sits under the visual it explains.** On a topic page, `('conclusion', i)` in the
  flow, directly after its chart, table or block (or another conclusion about the same visual).
  It draws the claim, what it means, and the facts it rests on as its figures. The build refuses a
  conclusion placed anywhere else, and one left out.
- **On a hub, or on any block**, `TB.claims(block, conclusions, facts)` attaches them to that
  block. A hub may then pass `ladder=None` and no `chart`, if a block placed `lead`/`top` is its
  signature.
- **A fact is drawn only under a conclusion that rests on it.** A fact nothing rests on is refused
  (it would be drawn nowhere). There is no free-standing grid of tiles any more.
- `'ladder'` in a composed flow is refused except on the pages in `topic.LADDER_FROZEN`, which used
  it that day; the list only shrinks. Worked example: `scripts/build_capital_rankings.py` (a path
  diagram, the ranked list with its funding line, a slope chart of two orders, share bands, and on
  the hub a grid of projects across years), each with its conclusions under it.

**Citations are strict.** In a composed flow every part with figures (chart, table, block,
ladder) is wrapped in `TP.cite(part, *sources)`, by index or by a source's `key`. Sources are
numbered at the foot and each section prints [n] linked to them. The build refuses a section with
no citation, and a source no section cites. TJ: *"this is a good model to keep strict."*

**A page with no `flow` is refused, unless it is one of the pages frozen in
`scripts/topic_legacy_flow.json` (18 November 2026) AND its shape is unchanged.** TJ, that day,
after six parks pages were rebuilt from new ledgers into the old slots: *"are the pages still
being constrained by the template?!"* So: a new page must be composed; adding a fact, chart, block
or table to an old page means composing it; a composed page leaves the list
(`python3 scripts/freeze_legacy_flow.py --prune`). The list only shrinks. A data refresh moves
values, not shape, so it never trips this.

## Every fund and every account has its own page

TJ, 19 November 2026, finding the Parks funds had nowhere to drop into: *"i thought we have a rule
that every fund/account gets its detailed page for navigation?"* ... *"this needs to be a pattern
for ALL funds"*. The school side already works this way (`/school-funds/<slug>`,
`/school-lines/<slug>`, one renderer `pages/FyItem.tsx`, payloads from `build_fy_breakdown.py`).

- **Any fund or account a page names gets a detail page**, town or school: what it is, its money
  in and out by year, and its postings where a journal is held. A page that mentions fund 1500
  links to fund 1500's page.
- **One renderer, many payloads** (rule 7d). A new fund is a new payload, never a new component.
- **Where no journal is held, the page says so** and registers the gap (rule 7c), rather than
  the fund having no page at all.

## The split: what binds and what is yours

| integrity: fixed, every page, every block, enforced | shape: the author's call |
|---|---|
| every digit a registered figure (rule 2) | which parts, in what order, how many |
| every claim says what it rests on (rule 3) | chart or diagram type, including ones never used before |
| our reading drawn as our reading (rule 7) | how much a diagram says |
| nothing tells the reader what to do (rule 8) | |
| a chart is a component from the payload (rule 7f) | |

## Choose the shape from the subject

Ask first: *what KIND of answer is this?*

| the answer is | draw it as | block |
|---|---|---|
| a rule (who pays, which case applies) | a decision matrix | `TB.matrix` |
| a sequence over time (a placement, a season) | a timeline | `TB.timeline` |
| a comparison of two or three things | cards side by side | `TB.panels` |
| causes and effects, or which source does what | a table of marks | `TB.checks` |
| something a reader will misread | a definition first | `TB.explain`, tone `define` |
| steps that add up (a bridge, a waterfall) | a bridge or stack | `TP.bridge`, or `custom` |
| a quantity over years (a TREND) | lines | `TP.series(kind='line')` |
| what a whole is made of (COMPOSITION) | stacked bars | `TP.series(kind='bar', stacked=True)` |
| things ranked by size | a ranking | `TP.ranking` |
| anything else | a component written for this page | `TB.custom` + `fy28/src/components/blocks/custom/` |

**Lines show trends, bars show composition** (TJ, 26 October 2026). A grant's history over the
years is a line; how a year's total splits between grants is a stacked bar. Next year, when shown,
is its own track continuing the line, in its own basis (a published figure, or `estimate`).

Any chart can also be placed mid-page with `TB.chart(spec, place=...)`. Places: `lead`,
`chart`, `also1`, `also2`, `body`, `end`. Block words do not count toward the 320-word page
limit; the site-wide reading-time ratchet still measures them.

Worked examples: `/special-education-reserve/surprise-costs` (matrix and timeline),
`/special-education-reserve` (custom money stack, three answer panels),
`/special-education/circuit-breaker` (five steps, a checks table, a worked year),
`/special-education-reserve/reserve-options` (four rule cards beside seven sizes).

A conclusion may be **categorical** ("a private move-in is not a surprise") when the finding is a
rule; name its basis -- the statute, a regulation, or our reading.

## "What it means": the state of enforcement

- **Enforced:** `panels`, `chart` and `custom` blocks refuse to build without `so=`.
- **Not yet enforced:** a CONCLUSION's meaning. Pass `so=` to `TP.conclusion` / `LD.conclusion`,
  or attach them in bulk the way `build_serf_topics.py`'s `meanings()` does. 26 October 2026:
  30 of 941 conclusions carry one. Every page you touch gets one on every conclusion.
- A meaning is what follows for a resident or a board: what to expect, what it changes, what
  question it raises. Not a cause (rule 7: if it is our reading, say so), not an instruction
  (rule 8: no "should", no charge).

## Limits the build enforces

finding 110 characters · hub answer 260 · fact label 60 · page prose 320 words · topic 2-12
facts and 1-4 conclusions · hub 2-6 conclusions · start pages 3 · related pages 4 · titles are
2-4 word nouns, never a sentence or question · no digits in a chart or block title (years go
in the note) · a digit in block prose needs `allow=` if it is not a registered figure.

## Conventions settled 26 October 2026 (not enforced; follow them)

- **A label is a noun the value completes.** "Years the lines spent under budget · 11 of 17",
  not "...spent under budget, of → 17". A count names its unit in the label ("years of 17 a
  line spent past its vote"): the tile prints the value and the label, never the unit.
- **One name per thing, across pages.** Grants through `journal.grant_program()`. A rule every
  figure depends on (which overspending counts) is stated once, where the figures are.
- **Consolidate before adding.** If a page opens on another page's figure, it is a section of
  that page. Retire it: remove it from its registry, delete its payload, map it in
  `TOPIC_MERGED` (`fy28/src/routes.ts`) so the old address opens the replacement.
- **A page appears where a reader looks for it.** A shelf group may list another hub
  (`TopicLink.shelfEntry`). A comparison district's pages appear only on its own hub.
- **Same denominator everywhere.** One figure must not read "16 of 17 years" on one page and
  "12 of 13 bad years" on another.

## Conventions settled 27 November 2026 (on /school-all-funds/fy2026-closeout/why-it-was-left)

- **Print the difference; never leave the reader to subtract.** A table across years carries a
  change column, and where offsets exist, what is left after them. TJ: *"i want to see the DIFFs
  too. i am mentally doing the math constantly to find the problem lines."* The column that found
  the real rows was "Still short": MIIA fell $836k on the vendor line and was $0 short once its
  June reclasses were counted. Sort or flag by the figure that identifies a problem row, not by
  raw size -- sorted by size, the false lead was the first row.
- **A ranked set includes every category that qualifies, even one with its own page.**
  Out-of-district tuition was excluded by name ("it has its own page") while ranking fifth by
  what it left. TJ: *"where are the out of district lines too?!"* A reader takes a comparison set
  as complete. Widen the set rather than displace another category, and if one truly must be left
  out, say so beside the chart.
- **A vendor or month view of the journal can mistake a reclass for spending that stopped.**
  Account and category totals include every reclass; views by vendor, by month, or across the
  town/school line do not. Check the account total before calling a vendor's fall a cut. See
  `notes/findings/JOURNAL-RECLASSES.md`.
- **Long category names on a bar chart wrap to their column** (`TopicCharts.tsx`, `WrapTick`);
  nothing to do per page. Past twelve categories the axis still thins its ticks.

## Review checklist, for every page

1. What is the one thing this page is for? Is it the first thing on it (rule 7a)?
2. Does another page open on the same figure? Then consolidate.
3. What kind of answer is it? Does the shape match (the table above)?
4. Does every conclusion and every block say what it means?
5. Is the lead a comparison someone on the deciding board would dispute or have to answer for
   (`notes/process/AUDIT-PASS.md`), or is it inventory?
6. Does each figure carry its unit, and the same denominator as elsewhere on the site?
7. Phone width: `bash scripts/check_phone_width.sh <route>`.

## The review queue (TJ, 26 October 2026)

1. **The surplus pages**, /fy2026-closeout: `notes/handoffs-done/HANDOFF-SURPLUS-PAGES.md`.
2. **Athletics**, /athletics.
3. **The whole school budget**, /school-all-funds.

Each in a fresh session, not a long one (CLAUDE.md 7g).
