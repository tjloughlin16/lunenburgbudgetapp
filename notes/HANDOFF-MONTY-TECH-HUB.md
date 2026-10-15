# Handoff: Monty Tech hub and per-pupil pages

Written 15 October 2026, at the end of a long session, so the build can start fresh.
Read this first, then `scripts/topics.py` (the model) and `scripts/topic_registry/enrolment.py`.

## What TJ asked for

TJ, 14-15 October 2026, after people in town suggested that *"some districts include their
capital projects and some districts do not"* in per-pupil spending: *"we might need to add
this information to a page about the finances of Monty Tech and per pupil spending"*, and
*"Monty Tech might need to become a hub?"* He agreed to the plan below.

## The plan

1. **A `monty-tech` category in `scripts/topic_registry/`** -- shelf "Monty Tech", hub title
   a 2-4 word noun (never a sentence or question; see the hub-and-spoke memory). Area
   `school`. Groups list:
   - the three topics that exist now, HOME on Enrolment and staying there, so their
     addresses do not change: `monty-tech-enrolment`, `monty-tech-assessment`,
     `monty-tech-funding` (also listed on Department budgets). One page, many shelves --
     never a copy.
   - two new topics below.
2. **New topic `monty-tech-per-pupil` ("Monty Tech per pupil")**, home `monty-tech`.
   DESE's per-pupil figure for Monty Tech (LEA `08320000`), Lunenburg (`01620000`) and the
   state median, by year, FY2009-FY2025. Says what the figure counts and does not (below).
   `build_monty_tech.py` already reads the FY TTPP row in `dese_total()`; extend rather
   than duplicate.
3. **New topic `what-per-pupil-counts` ("What per pupil counts"** -- or a better 2-4 word
   noun), HOME on `school-spending`, listed on the Monty Tech hub. Three measures side by
   side, each with what it counts, what it leaves out, and who set the rule: DESE per-pupil
   expenditure, Chapter 70 net school spending, the federal (NCES) tables. This is the page
   that answers the capital claim.
4. **`money-gaps.csv` row (rule 7c)**: whether districts code borderline purchases
   (equipment, technology, repairs) to the counted 2400s/4000s or the uncounted 7000s
   consistently cannot be answered from DESE's data. `-- closes:` DESE's Chart of Accounts
   and the EOYR instructions.
5. **Ingest the two primary documents (rule 12, through `ingest.py`)**: M.G.L. c.70 §2 and
   DESE's Chart of Accounts. Neither is in the archive (searched 14 Oct: only noise hits).

## OPEN DECISION -- ask TJ before building the hub route

`/monty-tech` is the long report today (Tab `montytech`, UNLISTED, aliases in
`fy28/src/routes.ts` ~700). Recommended: the HUB takes `/monty-tech` and the long report
moves to `/analysis/monty-tech`, still served because sources cite it. Alternative: hub at a
new address, `/monty-tech` untouched. TJ said "good idea" to the plan without picking one.

## What was established (14 October), and how

**Observed -- the data.** `sources/state-dese/district-expenditures-by-function.xlsx` (DESE,
every district, FY2009-FY2025): **363,514 rows, 337 districts, and not one row with a
function code starting 6, 7 or 8.** Codes present: 1xxx-5xxx and 9xxx only. So DESE's
per-pupil figure cannot contain capital (7000, fixed assets) or debt service (8000) for any
district, by construction. Recompute it in the generator and ASSERT it -- `dese_total()`
already does this for the two districts in one year; widen it to every district and year.

**Observed -- what the figure DOES include.** Lunenburg FY2025 rows in the same file:
transportation (3300) $1,234,726, $787 per pupil; food services (3400) $753,028, $480 per
pupil, all from grants/revolving; `TTPP` "Expenditure (Admin, Instruction, Operations)"
$30,031,242 total = $26,986,344 general fund + $3,044,898 grants/revolving, $18,027 per
pupil. These are spot values to orient by -- derive every figure on the page from the file
(rule 2).

**Observed -- the statute** (fetched 14 Oct from
https://malegislature.gov/Laws/GeneralLaws/PartI/TitleXII/Chapter70/Section2). "Net school
spending" is *"the total amount spent for the support of public education, including tuition
payments..."*, *"determined without regard to whether such amounts are regularly charged to
school or nonschool accounts"*, and *"shall not include any spending for school
construction, long-term debt service, school meals, transportation of students..."* nor
*"expenditures from grants..."*. Re-quote from our ingested copy, not from this note.

**Observed -- DESE's description** (https://profiles.doe.mass.edu/statereport/ppx.aspx):
*"Per pupil expenditures are calculated by dividing a district's operating costs by its
average pupil membership (FTEs)"*, in-district and total. It does not itself list the
exclusions.

**NOT observed -- the explicit exclusion sentence.** A search engine quotes DESE as saying
community services (6000), fixed assets (7000) and debt service (8000) are *"not included in
the per pupil expenditure calculations"*, from doe.mass.edu/finance/statistics/per-pupil-exp.html.
That page returns **404** (DESE reorganised its finance pages); the Wayback Machine answered
429. Do not quote the sentence until it is read on a page we hold. The data above stands
without it.

## The distinctions the "what counts" page must make

These are where the "some include capital" claim has substance. Keep facts and hypotheses
apart (rule 7).

- **Two state measures disagree on purpose.** Per-pupil expenditure INCLUDES transportation,
  food service and grants; net school spending EXCLUDES all three. A comparison mixing them
  shows a gap that is definitional. Fact.
- **The federal tables are a third measure**, with capital outlay and interest on debt as
  separate columns (e.g. https://nces.ed.gov/programs/digest/d22/tables/dt22_236.75.asp). Fact.
- **Coding judgement at the edges** (2400s/4000s counted vs 7000s not): a HYPOTHESIS about
  variation. Nothing in DESE's file shows how consistently districts code. -> the gap row.
- **Town-side spending for schools** (health insurance, building upkeep) must be counted per
  the statute's *"school or nonschool accounts"* clause; whether every town reports all of it
  is not visible in this data. Hypothesis about variation, not a finding.
- **A local presentation is not DESE's figure.** Ask which number a claim used.

## Process, and the traps this session hit

- Follow `notes/process/WRITING-AN-ANALYSIS.md`; payload-driven per rule 7d; conclusions via
  `scripts/conclusions.py`; `notes/process/AUDIT-PASS.md` before drafting any card.
- Type-check with `npx tsc -b` from `fy28/`. `tsc --noEmit -p .` checks an empty root config
  and PASSES while the build fails -- it did again on 14 October.
- **A code change re-renders all ~1,939 pages: ~25 minutes.** A data-only change reuses most
  (~5 min). Batch the code changes into one build.
- A failed `npm run build:site` leaves `dist/` partly emptied. Never deploy after one;
  `bash scripts/deploy_site.sh` refuses a half-built dist anyway.
- Deploy only when TJ asks (rule 10); verify on production, not on dist.

## Done in the same session, for context

Committed and deployed 14 October: the meeting-index title guard (`42fd7d913`), meetings
filed under a board shown as "Board — the body printed" (`dd32d0f0c`), dial-in numbers only
from joining verbs (`8ad325d89`). Unrelated to this work except that the Monty Tech board
pages share the same deploy.
