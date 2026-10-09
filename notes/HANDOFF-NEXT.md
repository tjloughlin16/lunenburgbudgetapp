# Handoff: everything not yet done, as of 9 October 2026, 13:50

One list for the next session. Read this first; the linked handoffs carry their own detail.
The 07:30 version of this file is in git history (`git log -p notes/HANDOFF-NEXT.md`).

## Nothing is running (TJ restarted the laptop, 9 October ~13:50)

- The minutes run stopped at its 80% session cap at ~08:45: 61 meetings, $28.25 (~5.7% of
  the week). Its output was committed (`a9bca989` and the 9 Oct refresh `55ed43ed`).
- **The AG determinations download FINISHED:** 2,808 fetched + 82 held, 0 failed, against a
  portal census of 2,889 numbers (`fetch_oml_determinations.py --census`). Letters to
  early 2014 are committed (`708f2d49`); **the rest of `sources/state-law/` is uncommitted
  in the MAIN tree** (see "two trees" below). Next: commit it, then `pdf_kind` over every
  letter (the letters are DIGITAL; never OCR wholesale -- `HANDOFF-OML-INDEX.md`).
- Today's refresh ran (09:54, exit 0) after the 07:00 one died on the `state-law` folder;
  the site was deployed to PRODUCTION at 13:09 (`wrangler pages deploy --branch main`;
  a bare deploy from the refresh tree goes to a PREVIEW alias -- refresh.py now names the
  branch). Production verified by sha256 of `/data/app-metrics.json`.

## TWO TREES, AND THE MAIN ONE IS BEHIND

`../lunenburgbudgets-refresh` is clean at `origin/main` (`1bce4f0d`). **This tree is several
commits behind origin and dirty**: the OML letters' text and index, today's job-postings
snapshot, `notes/reference/records-requests.csv` (one row added), and copies of script
changes that are already on origin. Bring it up to date carefully: commit the OML/state-law
data first, then `git pull --no-rebase`; expect conflicts only in the append-only CSVs
(archive-manifest, archive-push-state, ingest-pending, agentic-spend) -- resolve as a
union, then `sync_archive.py --manifest`. Never `git checkout`/`stash` another session's
work.

## Open work, in rough priority order

1. **The weekly pacing line -- APPROVED, NOT BUILT** (TJ, 9 Oct: "Yes ok let's build
   that!"). `process_meeting.py --week-line`: start a meeting only while the server's
   seven_day utilization is under `goal x hours-since-reset/168` (goal 90%, rising to 100%
   in the last 24 h before the reset) AND the 5-hour window is under 80%. Interactive use
   counts against the same bars, so the batch throttles itself -- TJ: "I just use capacity
   and the minutes fills in the rest." Week resets Thu 23:00 (seven_day.resets_at; the
   governor does not record it yet). Always running, one serial stream, newest first; a
   dashboard line actual-vs-target. At 12:30 Fri: 19% used vs a line of 8%, so nothing
   should start before ~Sat 07:00.
2. **D1 sync, bug 3 of 3 -- a decision.** Fixed today: the journal's malformed foreign key
   (`build_db.py`, now `(source, key)`), and parents sent after their children
   (`d1_incremental.py`). Still failing: rebuilding `document` (2,595 local rows vs 1,420 in
   D1) while `crosswalk` and `ledger_snapshot` reference it. `batch_sql`'s docstring lists
   three fixes; the recommendation given TJ was UPSERT for parent tables. Until then
   `sync_d1.py --check` fails and check_generated reports it; TJ said deploy past it.
3. **The anonymous records-request files -- in the inbox, NOT INGESTED.**
   `build/inbox/2026-10-09-anonymous-records-request/` (nine files + PROVENANCE.md +
   the original zip; also still in ~/Downloads). TJ: "these are from a FOIA request and
   someone sent it to me anonymously. Dont ingest." Includes
   `Corrected Lunenburg_Paraprofessional_Salary_Scale FY27-FY28 (1).xlsx` -- apparently the
   corrected schedule approved 7 Oct. When TJ says ingest: through the 13e gate, provenance
   "a third party's records request, forwarded anonymously". `build/` is gitignored and on
   this disk only.
4. **Paraprofessional salary schedule: compare original and corrected.** We hold the
   pre-correction FY26-FY28 agreement and schedule (committed 20 Aug; the district's HR page
   still serves those exact bytes, checked 9 Oct). The correction (Superintendent, 16 Sep,
   per our captions): hourly rates "did not calculate accurately into the annual salaries".
   Records request sent 9 Oct (`records-requests.csv`). When TJ clears the inbox file or
   the district answers: diff every classification, step and figure.
5. **Dee Bus.** We hold no transportation contract. 11 regular-education buses (TJ,
   confirmed; also our captions, SC 22 Jan 2025 1:34:54). Sports transport is in dollars
   only (by-sport workbook; budget line $40,000 FY24 -> $87,822 FY25 -> $127,550 FY26
   budget, with the fee-fund share falling the same year -- a hypothesis, not established).
   TJ will request the contract later; drafts were given in the session (contract + rate
   schedule; athletic-trip invoices). Not yet a money-gaps row.
6. **The refresh, rebuilt as always-additive** -- design approved, NOT BUILT:
   `notes/HANDOFF-REFRESH-ADDITIVE.md`.
7. **Two working-copy fetchers are untested in a real run**: `fetch_board_pages.py` now
   lands every changed page through `ingest.land_version()`. Tomorrow's refresh is its first
   live use; check its log and `working-copies.csv`.
8. The journal export (13e gate), the OML index (model-free parts), MUNIS Part 2, an
   off-machine backup, the 9 MUNIS PDFs to publish -- unchanged from the 07:30 list.

## Done on 9 October (all on origin/main)

- Refresh: counts only what it writes; "found on external sites" vs "found in our local
  files", each with where it was found; snapshots counted once; a failed run no longer
  counts as the day's run; `--branch main` on deploy. (`2906aa17`, `86b6191a`, `a8defc14`,
  `a5e37e13`)
- Dashboard: OML card + burndown + by-year; live "Found so far today"; "What it picked up"
  itemised; Questions tab with "(N)" and last-checked; Held section removed.
- The 2027 resurrection SOLVED: two recordings with misdated minutes and captions whose
  manifest rows kept restoring them; rows removed, objects in `archive-orphans.csv`; the two
  correct transcripts (held on one disk only) now in the bucket. (`056b2abb`)
- Backups: the check compares CONTENTS now; three versions held on one disk are landed;
  `working-copies.csv` + `ingest.land_version()`. (`a5e37e13`)
- Job postings: a pii_screen match on a public posting is noted, not refused.
- `state-law/` approved as a top-level folder; OML reviews stay unlisted (TJ).

## Built 7-9 October -- where to find it

**Reports, all live and UNLISTED** (`sources/analyses/UNLISTED`), each a generator + payload
+ verifier (rule 7d):

| page | generator | verifier |
|---|---|---|
| `/analysis/special-education-costs` | `build_sped_costs.py` | `verify_sped_costs.py` |
| `/analysis/fy26-school-surplus` (and fy25) | `build_school_surplus.py --fy/--all` | `verify_school_surplus.py` |
| `/analysis/sitting-on-money` (FinCom #9) | `build_sitting_on_money.py` | `verify_sitting_on_money.py` |
| `/analysis/spending-what-comes-in` (#7) | `build_spending_what_comes_in.py` | `verify_spending_what_comes_in.py` |
| `/analysis/spent-with-no-budget` (#12) | `build_spent_no_budget.py` | `verify_spent_no_budget.py` |

FY26 surplus is period 13 AS RUN 6 Oct with encumbrances still open: rerun when the Town's
post-close report arrives.

**Open Meeting Law, EXPERIMENTAL and hidden** (no links, not in the sitemap, not
prerendered, noindex): `/meeting-minutes/<board>/<date>-<video>/oml`, written by
`scripts/oml_review.py <board> <date> [--without-minutes]`, rendered by
`fy28/src/pages/OmlReview.tsx`, numbered points (`#point-N`). Never says "violation".
Reviews exist for Parks 2026-06-24 and 2026-07-22, School Committee 2026-07-29, 2026-08-26
and 2026-10-07. The law: `scripts/oml_law.py`, `sources/state-law/`.

**The usage governor**: `process_meeting.py --until-usage` (`--session-caps`, `--week-cap`,
`--by`, `--max-jobs`, `--ramp`, `--oldest`), `scripts/usage_governor.py` (reads the
server's own usage bars, polls every 150 s), output guard in `scripts/backlog_pace.py`.
`notes/HANDOFF-USAGE-GOVERNOR.md`. Measured: a three-step meeting ~1% of a 5-hour window,
~0.1% of the week (`notes/findings/METERED-BATCH-COST.md` sections 6-7). Two things that
cost hours: a new window opens only on FIRST USE after a reset, so do not wait for a
reading to change before starting; and always arm a watcher on an overnight run.

**Faster site build**: one Chrome over a DevTools pipe plus a reuse cache --
`notes/HANDOFF-FASTER-SITE-BUILD.md`. Full build ~10-14 min, nothing changed: seconds.

**Board records**: "not available" until the OML approval window closes (later of 30 days
and the third subsequent meeting), MISSING only after; reasons in
`sources/data/meeting-record-explanations.csv`. Live.

## Held, by TJ's decision (not work)

- 5 meetings in `sources/data/review-queue.csv` are held for review; TJ: "we can skip
  those. none are important." They stay out of `process_meeting.py` runs. Two of them
  (council-on-aging 2026-07-14, cemetery-commission 2026-07-30) would recover their
  attendance on a re-read now that the attendee quote rule is fixed.

## Done on 6-7 October (for orientation; all committed and pushed)

- Runaway protection: limit stop, no-progress stop, backlog-must-shrink, kill switch
  (`build/STOP-METERED`); `sweep_backlog.py` retired; the refresh does NEW items only.
- `process_meeting.py --next N`: newest first, transcripts first (`read_order.py`), serial,
  locked, ceiling; structured reads (v2) of the town's minutes; review queue.
- School MUNIS period 13 FY23-FY26 published and in the database
  (`munis-school-ytd.csv`); FY25 surplus findings + unlisted report; asked-vs-delivered note.
- Backlog dashboard: board filter, % open, missing records (by hue), held-for-review, each
  toggleable.
- Meetings announced only by email reach the upcoming list
  (`sources/data/meeting-notices-email.csv`; feed, board pages and agenda previews read it).
- Agenda previews: executive sessions always listed; items ranked executive session ->
  senior hires -> contracts/pay -> money votes; split URLs (`h ttps://`) repaired.
- Verified full backup: `scripts/backup_snapshot.py`.
- Parks Commission missing-recordings report (2025-2026), email draft in
  `notes/outbound/drafts/`.

## Per-board "Missing records" pages -- status

Built 7 October 2026, committed `ab15603a`; deployed and live since.

- `/boards/<slug>/records` (`fy28/src/pages/BoardRecords.tsx`): every meeting a board has
  held; gaps only by default, "show every meeting" toggle; YouTube / official minutes /
  transcript; MISSING in `--status-critical`, n/a with a reason where a record is not
  expected. Linked from each board page ("Missing records ->").
- Board pages' Recent meetings: MISSING instead of a dash; Our minutes shows `pending`
  (in our queue) or `needs video` (written from the recording).
- ONE definition: `scripts/meeting_records.py`, imported by `build_backlog_depth.py`,
  `build_boards.py` and `build_board_records.py`.
- Email reports for any board: `python3 scripts/build_board_records.py --md --board SLUG
  --since YYYY-MM-DD --out notes/outbound/drafts/<NAME>.md` (TJ's approved format: gaps
  only, YouTube + official minutes, newest year first).
- Known: the page counts a missing transcript and the email format does not, so a year's
  "N of M" can differ by design. Parks 9 Apr 2025's recording was only joined to its meeting
  on 7 October (an override), so its captions are not fetched yet -- the next transcript
  fetch picks it up.
