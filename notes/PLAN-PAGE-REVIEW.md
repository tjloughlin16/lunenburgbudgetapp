# Plan: review every page, now that the template is gone

**Status, 31 October 2026:** written; not started. TJ wants it kicked off *after* the review of
the most recent pages (the general fund split, the school receipts page, salaries from grants and
fees) is finished.

## Why

TJ, 31 October 2026, on a page rebuilt into the topic template the same day:

> *"this page is so boring now! ... what happened?!"* ... *"we need to just outright remove the
> topic building template"* ... *"all of our pages have sucked since we added it unfortunately. i
> think we have the hub and spoke model, so leveraging that when it makes sense is the way to keep
> things short."*

> *"we need to hold the big CONCEPTS in there, but not the designs or anything. what worked the
> best is: there's a header image that is representative of the page. there are conclusions.
> metrics. and keep it short (and use hub/spoke everywhere possible to add details). but showing
> the literal same type of info each page gets old and boring and doesnt represent the data in the
> best way possible."*

> *"we need to basically review EVERY page on the site to see if there are better pages to be
> built now."*

## What already changed (the mechanism, done 31 October)

- **The template is removed from the framework.** A topic page is now `flow`: an ordered list of
  parts the generator composes (`scripts/topic.py`, the `FLOW` comment). The renderer
  (`fy28/src/pages/Topic.tsx`, `FlowItem`) draws exactly that list and nothing else.
- **Nothing is mandatory except sources.** Tiles 0-12, conclusions 0-4, chart optional, and every
  part a page builds must appear in its flow (a built figure nobody can see is refused).
- **Every existing page still renders as it did**, because a generator that passes no `flow` gets
  `default_flow()`: the old slot order written out. **That is a migration aid, not a format.** A
  page on `default_flow` is a page this review has not reached yet.
- **Integrity is unchanged** (rule 7h's left column): every digit a registered figure, every claim
  says what it rests on, our reading drawn as ours, nothing prescriptive, charts as components,
  `so=` (what it means) on every block with figures.

## Citations: strict, on every composed page

TJ, 31 October 2026: *"make sure in the new 'template' it requires putting sources, citations for
sections that point to the sources at the bottom of the page. this is a good model to keep
strict."* Built: `TP.cite(part, *sources)`. In a composed flow every chart, table, block and the
ladder must cite at least one source, and every source must be cited by some section, or the build
refuses. The renderer numbers the sources and prints [n] under each section. **So converting a
page to its own flow means citing each section**, and the review cannot skip it.

## The concepts that stay (TJ's list, not a layout)

1. **A signature image at the top that IS the page**, drawn in the units the subject is made of
   (rule 7f). One image a reader remembers.
2. **Conclusions**, each with what it means, each a comparison someone on the deciding board would
   dispute or have to answer for (`notes/process/AUDIT-PASS.md`). Not inventory.
3. **Metrics**, each carrying its unit.
4. **Short.** Detail goes to a spoke page, not further down this one.
5. **Hub and spoke wherever it makes sense.** A hub answers the shelf's question and points to its
   spokes. A spoke answers one question.

What does *not* stay: the same five parts in the same order on every page. If two pages look the
same, one of them is not showing its data the best way.

## The inventory

| kind | count | where |
|---|---:|---|
| topic pages | 257 | `scripts/topics.py`, 24 shelves (`scripts/topic_registry/`) |
| hubs | 24 | same |
| bespoke pages | ~89 components | `fy28/src/pages/` (front page, org charts, boards, feed, FY items...) |
| markdown analyses | 50 | `sources/analyses/*.md`, rendered by `Analysis.tsx` |

Hubs are not on `flow` yet: `Topic.tsx` still draws them in the old fixed order. **Converting the
hub renderer is step 0 of this review**, before the first shelf. Same change as the topics: a hub
`flow`, and `default_flow` for hubs not yet reworked.

## How each page is reviewed

For every page, in one sitting, answer these in order and record the verdict:

1. **What is the one thing this page is for?** One sentence. If it takes two, it is two pages.
2. **Is there a better page to build now?** The data has grown since most of these were written
   (the FY breakdown, the school journal, 1959-2010 annual reports, MUNIS period 13). Look for
   the comparison the page could now make that it could not when it was built.
3. **What kind of answer is it?** A rule, a sequence, a comparison, a composition, a trend, a
   ranking, a mechanism. Draw it as that (the shape table in `.claude/skills/building-a-page`),
   including a component written for this page alone.
4. **What is its signature image?** And is it first?
5. **Hub, spoke, merge or retire?** Does another page open on the same figure (consolidate)? Is it
   long because it is really a hub with three spokes (split)?
6. **Is it short?** Everything a reader could skip moves to a spoke or the end.
7. **Same denominators as the rest of the site?**

**Verdicts:** `keep` (fine as it is; give it an explicit flow anyway), `recompose` (same content,
better shape), `rebuild` (a better page exists now), `split` (hub + spokes), `merge into <id>`,
`retire`.

## The register

`notes/process/PAGE-REVIEW-REGISTER.csv`, one row per page: `page, shelf, kind, verdict, one_thing,
signature, reason, session_date, done`. A page is done when its generator passes an explicit
`flow` and the register says so. A script (`scripts/page_review_progress.py`, to write in step 0)
counts the pages still on `default_flow` (recompute it and compare with the payload's flow), so
progress is measured, not remembered.

## Order

**Step 0, one session:** the hub renderer on `flow`; the register and progress script; the
`building-a-page` skill rewritten around the five concepts in place of the template; CLAUDE.md
rule 7h pointed at it.

**Then one shelf per fresh session** (CLAUDE.md 7g: never in a long, context-heavy one). Most
recently built first, because that is where TJ's review is now and where the template did the most
damage:

1. School budget, all funds (17): the FY breakdown, school receipts, salaries from grants and fees, preschool
2. FY2026 closeout (17), already half-reviewed in `notes/HANDOFF-SURPLUS-PAGES.md`
3. Department budgets (19), including the new Town general fund
4. Special education (22) and the SERF reserve (9): the pages built outside the template, which
   read best. They are the worked examples for everything after
5. Athletics (14), transportation (9)
6. School spending (25), spending history (20), staffing (14), programs (15)
7. State aid (14), enrolment (14), buildings (6)
8. Town: free cash (5), reserves (6), homes and taxes (19), health insurance (12), boards (8), parks (11)
9. Options: crisis (26), budget options (19)
10. Comparisons: Monty Tech (9), Bromfield (4)
11. The bespoke pages and the markdown analyses, last. Most are older and many may retire into
    hubs.

TJ reviews each shelf's result before the next starts. That is the gate, not a formality: the
first shelves set the pattern the rest copy.

## Cost

- **Sessions dominate.** CLAUDE.md's measured case is one long session at about 65% of a week. So:
  one shelf per fresh session, closed when the shelf is done.
- **A shelf of ~15-25 pages is likely one session.** This is an ESTIMATE; nothing has measured it.
  Read `/usage` before and after the first shelf and write the number here, then quote the rest
  from it.
- Regenerating payloads is local Python and costs nothing against the plan.

## Known issues found while building the mechanism

Three generators refuse to write on 31 October 2026, each on a data assertion unrelated to the
flow change. Their 17 payloads had the default flow stamped in place (the same flow the generator
will write once fixed), so they render.
- `build_athletic_director_topic.py`: "the directors named are ...".
- `build_special_education_topics.py`: `kpeak = max(CB['series'], ...)`, a circuit breaker year
  with `children` = None.
- `build_journal_surplus_topics.py`: "a School Committee warrant covering 18 June to 5 July now
  appears in the minutes".
