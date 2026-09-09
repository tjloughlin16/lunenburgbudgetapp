# Where we left off — 9 September 2026

Written at the end of a long session. Everything below is committed, pushed and
deployed unless it says otherwise.

## Running when this was written

- **The D1 push was attempted and FAILED ON AUTHORISATION, not on quota.**
  `code: 7403 — the given account is not valid or is not authorized to access this
  service`. It failed BEFORE writing anything, so nothing is in a half-state and the live
  `/api/query` still answers normally (checked: 276ms, correct row count).

  **This changes the problem.** We have spent a day managing a quota worry —
  117,775 rows against a 100,000/day free-tier allowance — and have never got far enough
  to discover whether it binds. The API token wrangler is using has either expired, lost
  its D1 permission, or points at the wrong account. **Fix the credentials first, then
  find out whether the quota is real.** Do not buy a plan on the strength of an error
  that turned out to be an auth failure.
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
