# Handoff: teacher pay, comparison districts, and the 19 October session

Written 19 October 2026, when TJ paused the work. Read CLAUDE.md first; rules 2, 3, 7, 7c, 8, 12,
13, 13d and 13e all bit during this work. Nothing below is deployed. About 58 commits sit on `main`
since the last deploy (`a8fc3d9d8`).

## Stop first: frozen processes

Three OCR jobs were **paused, not killed** (`kill -STOP`), to let the battery charge:

- `ext1.py ayer-shirley-teachers-2025-2028 dese-teacher-contract-wachusett` (pid 24468)
- `ext1.py dese-teacher-contract-uxbridge dese-teacher-contract-tyngsborough` (pid 24472)
- `ext1.py shrewsbury-teachers-2025-2028` (pid 24474)
- plus their `swift-frontend ... scripts/ocr_pdf.swift` children (24502, 24503, 36706)

The agent that started them **has died** (it hit the session limit, mid-ingest). Nothing will
collect their output, so **kill them** rather than resuming:

    kill -CONT 24468 24472 24474 24502 24503 36706; kill 24468 24472 24474 24502 24503 36706

(After a reboot they are simply gone.) All six PDFs are real scans, checked with `pdf_kind.py`.
But **those jobs were OCR'ing whole contracts**, 55–124 pages each, when only the salary-schedule
appendix is needed. Next time: find the schedule pages first, OCR only those, one document at a
time. Four parallel whole-document jobs kept the laptop at full load for over 30 minutes and drained
the battery while plugged in.

## What the work established (all committed unless marked)

| Question | Answer | Page |
|---|---|---|
| Did teacher spending rise from more teachers or more per teacher? | More per teacher. FY2009→FY2025: 15.2 fewer teachers saved $926,988; a pay increase for the 105.0 remaining added $3,814,737; the line rose $2,887,749 | `/school-spending-history/pay-or-headcount` |
| Average salary vs comparison districts | DESE average $97,233 in FY2025, 2nd of the project's six | `/school-spending-history/teacher-pay-compared` |
| Is Lunenburg's pay SCALE the lowest? | Of the five districts with current contracts held (Lunenburg, Harvard, North Middlesex, Fitchburg, Monty Tech), lowest in the bachelor's and master's lanes. With longevity at 25 years, master's top is 3rd of 5 (Lunenburg's longevity, $5,700, is the largest) | same |
| Where do Lunenburg's teachers sit on the scale? | Calendar 2025: 56 of 90 matched full-year teachers paid at least the master's top step, gross | `/school-spending-history/teachers-on-the-scale` |
| Is that unusual? | Against Harvard (the only district measurable so far): 61 of 104 at or above Harvard's own master's top. About the same share; Lunenburg has fewer teachers low on its scale (lower quartile 95.8% vs 86.1% of own top) | same |

Rule 7, which the pages keep: none of this shows raises vs steps vs who is on staff, and nothing
links fewer teachers to higher pay. Gross pay includes stipends, coaching and longevity.

## The comparison sets (the reason this matters)

The district has named its own comparison districts:

- **FY2026 Superintendent's proposed budget, p57:** "The districts listed above are the districts
  the Budget Task Force identified as comparable districts/communities": Nashoba, Groton-Dunstable,
  Ashburnham-Westminster, Shrewsbury, Uxbridge, Maynard, Wachusett, Ayer-Shirley, Hudson.
- **FY2020 budget (Dec 2018):** RADAR comparison districts Uxbridge, Tyngsborough, Ayer Shirley;
  DART summary used Harvard, Ayer Shirley, Uxbridge. (Documents ingested, commit 1cd7ed8e8.)

TJ's decision: merge every set the district chose into ONE **official** set (11 districts:
the nine + Tyngsborough + Harvard), keep **the project's six** as a separate set, and show both
side by side on the teacher pay pages. The 28-district "Comparable Districts" page in the FY26
draft budget book is NOT in the official set (no stated criterion).

TJ on disputes: if people object to the comparables, he will ask them which districts they think
are comparable. The pages already say who chose each set.

## In flight: the dead agent's uncommitted work

The "official comparison set" agent died before committing. On disk, uncommitted:

- `sources/data/comparison-sets.csv` (untracked, 21 rows) + `scripts/check_comparison_sets.py`
  (untracked). Looks complete for the official set; check the `project-six` rows exist.
- `scripts/extract_dese_teacher_salaries.py` (untracked): DESE average salary for every district.
  Unknown whether its source file was ingested or its output written; verify it reproduces
  Lunenburg's DESE averages (FY2018–FY2025: 74,236 / 77,908 / 83,054 / 85,067 / 85,426 / 88,019 /
  98,894 / 97,233).
- `scripts/extract_teacher_salary_schedules.py`, `sources/data/teacher-salary-schedules.csv`,
  `teacher-salary-schedule-docs.csv` and their `fy28/public/docs/data/` copies (modified): new
  districts' schedules. **Known defect:** a step value `'11/13'` (Tyngsborough) that the page
  generator's `schedules()` cannot parse; normalise it (integer step plus a `step_as_printed`
  column) before anything rebuilds.
- `sources/contracts/index.csv` (modified) and many `fy28/public/docs/contracts/txt/*.txt`
  (untracked), plus `fy28/public/api/teacher_salary_schedule*` (untracked; someone ran build_api).
- `scripts/build_spending_staff_students_topics.py` shows as modified: **check the diff before
  committing**. It may be the dead agent's compatibility change, or nothing intended.
- `notes/reference/records-requests.csv` and `money-gaps.csv`: hunks from several agents; stage
  by hunk.
- Its last words were "Now ingest all fifteen documents through ingest.land". `ingest.py --status`
  shows 0 in flight and `check_archive_backed_up.py` passes, so either the fifteen were never moved
  into `sources/`, or they were already secured. Find them before assuming either.

Contracts held now (`sources/contracts/pdf/`, 47 files) include current or new ones for Shrewsbury
2025–28, Groton-Dunstable 2024–27, Ayer Shirley 2022–25 and 2025–28, Ashburnham-Westminster
2025–28, Hudson 2025–28, plus DESE filings for Maynard, Uxbridge, Tyngsborough, Wachusett and
others. Several are scans whose schedule pages are not yet read.

**To finish:** kill the frozen jobs; review and commit the comparison-sets file and the DESE salary
extractor; read only the schedule pages of the new contracts; fix the `'11/13'` step; rerun
`extract_peer_teacher_pay.py` (it picks up new master's-lane cells automatically, so A-W FY2025 or
Tyngsborough FY2022 would become measurable); then update `teacher-pay-compared` and
`teachers-on-the-scale` to show both sets: average salary ranked within each, the scale comparison
for each, and own-scale composition where measurable.

## The own-scale comparison: why it is thin

Few districts publish a wage list that marks teachers. Survey results are in
`notes/findings/WAGE-LISTS-COMPARISON-TOWNS.md` (every place searched).

- Measured on own scale: **Harvard** only.
- List read, schedule for that year not held: **Ashburnham-Westminster** (FY2025),
  **Tyngsborough** (2022).
- List found but no job titles, so teachers cannot be separated (left alone): Hudson, Maynard,
  Uxbridge.
- No list found: Shrewsbury, Nashoba, Wachusett, Groton-Dunstable, Ayer Shirley, North Middlesex,
  Monty Tech, Fitchburg, Leominster.

For most districts the only route is a records request for teachers by step and lane.

## Records requests drafted, NOT sent (`notes/reference/records-requests.csv`)

- `2026-10-19-teacher-step-lane-counts`: to Lunenburg: teachers (FTE) by step and lane, 1 October
  FY2018–FY2026, counts only; plus the teacher agreements FY2015–FY2024.
- `2026-10-19-teacher-contract-{groton-dunstable,ayer-shirley,leominster,ashburnham-westminster}`:
  current Unit A agreements. Some may now be moot: newer contracts were found for G-D, Ayer Shirley
  and A-W. Re-check before sending.

## Decisions still waiting on TJ

1. **Deploy.** Run the full `check_generated.py` and `check_phone_width.sh` once first: many agents
   touched shared outputs.
2. **Journal API files.** `fy28/public/api/munis_school_journal*.json` exist, so the next deploy
   publishes the journal tables. Another session recorded the redaction decision; confirm it is
   intended.
3. **`sources/data/gross-wages.csv`**: the town's full name-and-pay list, already published at
   `/docs/data/gross-wages.csv` from earlier work (commit 97a955f76). Keep, or make private and
   publish aggregates only? The teacher-pay work publishes no names.
4. **DESE FY2025 relabel.** DESE's FY2025 compliance summary (`comply-fy2025.xlsx`, posted 13 Oct
   2026, not yet ingested) labels Lunenburg's FY2025 $25,420,399.65 as ACTUAL net school spending;
   our profile copy marks it budgeted. FY2024's compliance file ties to the profile exactly, and
   FY2025's budgeted figure in last year's file was $24,234,658.71, so the profile's label is
   wrong. An agent to ingest the compliance files and relabel was offered, not started.
5. Smaller: school-year vs summer rhythm for the meeting estimator (would let School Committee
   qualify); fix the four wrong statements on `/walkthrough`; tell the Town about the child's name
   missed on p643 of Report 1; show an estimate when a posted meeting is far off.

## Other work from this session (committed, for orientation)

- `/crisis` is the Budget crisis hub: units on rates; "What would prevent cuts" lists all 14
  priced options in fiscal years covered.
- School spending history: Growth by spending type (ranked), Spending by type over time (stack plus
  15 small multiples), Pay or headcount, Teacher pay compared, Teachers on the scale.
- Hubs: a "Start here" group on all 21 (`start=[...]` in each registry file).
- 404 page; small multiples and `page(also=...)` in `scripts/topic.py`.
- Grouping audit: 12 invented or misleading groupings fixed site-wide (Monty Tech, walkthrough,
  stopped funding, state aid, buses, athletics, gap by function, school surplus).
- Boards: likely next meeting (backtested, `scripts/meeting_cadence.py`); schedule check of each
  board's stated schedule against the record (Select Board says "every Tuesday except the last",
  met on 8 last Tuesdays).
- Journal handoff: `notes/HANDOFF-MUNIS-JOURNAL.md` (another session is working it).
