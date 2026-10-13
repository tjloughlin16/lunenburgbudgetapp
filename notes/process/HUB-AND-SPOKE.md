# Hub and spoke: every report, broken into pages

TJ, 12 October 2026: *"we aren't going to use the small/large formats anymore. i dont think it
works. we need people to jump into the data they need right away, vs scrolling pages."* And:
*"we dont need FULL reports.... we need all the smaller reports broken out."*

This is the plan for moving every report on `/reports` to that model, and the brief every
agent building a category works from. Transportation and Athletics were built first, on 12
October, and are the worked examples.

## The model

```
/reports
 └─ AREA            The schools · The town · Budget options       (a heading on /reports)
     └─ CATEGORY    a shelf, and a hub page at /<category>          ("Special education")
         └─ TOPIC   one question, one page at /<category>/<topic>   ("Out-of-district tuition")
```

- **Hub:** a one-line-to-three answer, the signature chart, the matrix of facts, three to six
  conclusions (each opening to what it rests on), and a card per topic. About 3 minutes.
- **Topic:** a one-line finding, one chart, 2–12 facts, 1–4 conclusions, the figures table,
  what was said about THIS topic only, sources. Under 5 minutes.
- **One question, one page, one address.** A topic that belongs on two shelves is listed on
  both and lives at one address. Never two copies.
- **No full reports.** Nothing promotes the long documents. They stay served at their
  addresses, because sources and agents cite them, and come off the shelves as their
  subject's category is built (`UNCATEGORISED` in `scripts/build_reports_index.py`).
- **No fold, no short version.** The page IS short.
- **A page that is too long is two pages.** TJ: *"it's an indicator that we didn't hub and
  spoke it enough if the final reports are still too long."* `scripts/topic.py` refuses a
  topic past 320 words of prose or a 30-row table, and a hub past 400 words. The remedy is
  to split the topic in the registry -- never to trim the prose until it fits.

## Titles

**Page titles, hub titles and category names are never sentences and never questions.** A
title names the subject in two to four words: *Bus fee*, *School bus costs*, *Transportation*.
The claim goes on the line under it -- the payload's `finding`. `scripts/topics.py` refuses a
title that ends in `?` or `.`, runs past five words, or repeats another topic's title.

## The machinery (read these before building)

| file | what it is |
|---|---|
| `scripts/topics.py` | the registry: loads every `scripts/topic_registry/<category>.py`, checks titles |
| `scripts/topic_registry/<category>.py` | ONE FILE PER CATEGORY: `CATEGORY`, `GENERATOR`, `TOPICS` |
| `scripts/topic.py` | `page()`, `conclusion()`, `hub()` -- the validated payloads |
| `scripts/ladder.py` | `fact()`, `tier()`, `matrix()`, `ladder()`, `conclusion()` |
| `scripts/brief.py`, `scripts/conclusions.py` | `figure()`, `step()`, the rule-2 check |
| `scripts/build_topics_index.py` | assembles `fy28/public/data/topics.json` -- the shelves |
| `fy28/src/pages/Topic.tsx` | renders every hub and topic; nothing per-category |
| worked examples | `build_topics()` at the end of `scripts/build_transportation.py`; `scripts/build_athletics_topics.py` |

A category is: one registry file, one generator writing `fy28/public/data/topics/<id>.json`
for its hub and each topic, with `--check`. No React. No hand-written pages.

## The categories

Built 12 October 2026: **Transportation**, **Athletics**.

| area | category id | shelf / hub title | absorbs (current shelf entries) |
|---|---|---|---|
| school | `special-education` | Special education / Special education costs | sped (4 reports: special-education-costs, sped-and-funds, sped-and-the-curve, hiring-here-or-placing-there), circuitbreaker, classsize |
| school | `school-staffing` | School staffing / School staff | staffing, schoolstaff, parastaff |
| school | `enrolment` | Enrolment / Students and schools | enrollment, attrition, outflow, leaving, montytech |
| school | `state-aid` | State aid / Chapter 70 aid | minaid, formula, required |
| school | `school-spending` | School spending / Spending compared | peers, spending-compared, per-pupil-spending, peer-districts, variance (budget-vs-actual) |
| school | `school-programs` | School programs / Programs and cuts | courses, ap, cuts, stopped, unwind |
| town | `town-reserves` | Town reserves / Free cash and stabilization | free-cash, stabilization-funds, stabilization-option, freecashlever |
| town | `fy2026-closeout` | FY2026 closeout / FY2026 year end | fy26-closeout, fy26-closeout-town, fy26-school-surplus, fy25-school-surplus |
| town | `department-budgets` | Department budgets / Town departments | town-budgets, town-personnel, the 12 town-budget-* documents |
| town | `homes-and-taxes` | Homes and taxes / Homes, taxes, growth | bythenumbers, owners, homestudents, growth |
| town | `health-insurance` | Health insurance / Health insurance costs | insurance, healthlever |
| town | `boards` | Boards / Boards and committees | boardcompare, board-composition, open-seats |
| town | `parks` | Parks and recreation / Parks department | parks (youth sports cross-listed from Athletics' elsewhere) |
| options | `budget-options` | Budget options / Closing the gap | override, fees (feelever), extras, classrooms, salaries, fy27-and-the-override, fy27-cut-reconciliation |

Not migrated: the live pages (blog, budget feed, this week, boards, minutes) and the method
shelf (annual reports, connecting the budget, what you can ask, questions) -- those are not
reports with findings; they stay as they are.

**Order of work**, in waves of three so the five-hour usage window is not exhausted:
1. special-education, town-reserves, fy2026-closeout
2. enrolment, school-staffing, state-aid
3. school-spending, school-programs, department-budgets
4. homes-and-taxes, health-insurance, boards, parks, budget-options

## What an agent building a category must do

1. Read `CLAUDE.md` (rules 1, 2, 3, 7, 7b, 11, 12, 13, 13a are binding) and the machinery above.
2. **Inventory first.** Read every source report the category absorbs, list the questions
   they answer, and find the duplicates -- one question gets one page.
3. Write `scripts/topic_registry/<category>.py` (titles: 2–4 word nouns) and
   `scripts/build_<category>_topics.py` with `--check`. Read figures from the repo's data and
   payloads; never type one.
4. Run the generator, `--check`, and `python3 scripts/topics.py` until all pass.
5. **Do not edit any other file.** Not `topics.py`, not `topic.py`, not React, not another
   category. Report a framework limit instead of working around it.
6. Report: every finding and conclusion verbatim, the source of each figure, every judgement
   call on disagreeing sources, what was left as a gap.

## After each category lands (the coordinating session)

- Recompute a sample of its headline figures from the raw data, independently.
- `python3 scripts/build_topics_index.py`, `build_reports_index.py` (move the absorbed
  entries to `UNCATEGORISED`), `npx tsc -b` from `fy28/`.
- Look at the hub and two topics rendered, desktop and 400px.
- Only then build and deploy.

## Status

| category | built | verified | deployed |
|---|---|---|---|
| transportation | 12 Oct | 12 Oct | 12 Oct (pending) |
| athletics | 12 Oct | 12 Oct (3 figures recomputed; $400 fee and "paid" fixed) | 12 Oct (pending) |
