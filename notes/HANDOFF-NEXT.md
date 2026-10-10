# Handoff: everything not yet done, as of Saturday 10 October 2026, 08:30

One list for the next session. Read this first; the linked handoffs carry their own detail.
Earlier versions are in git history (`git log -p notes/HANDOFF-NEXT.md`).

## RIGHT NOW (Sat 10 Oct 08:30)

- **The new always-additive refresh is RUNNING** (started 07:00, its FIRST real run, in this
  tree; log `build/refresh-logs/2026-10-10.log`). DO NOT commit in the main tree until it
  finishes (`pgrep -fl "[d]aily_refresh"`). Then read its log end to end: did it commit only
  its own files, replay/push cleanly, report "not yet refreshable" files, and deploy (or say
  why not)? Its search step (`build_search_index.py`) will be SLOW -- see below.
- **The paced minutes run is STOPPED on purpose** (`build/minutes-pacing.STOPPED`). Overnight,
  its usage readings went STALE and the stale branch ran BEFORE the weekly-line rule, so it
  wrote meetings with the week at 28% vs a line near 18%. Fixed in `usage_governor.py`
  (stale + weekly line -> wait; 24 of 24 rules). Before removing the marker: find WHY the
  readings went stale overnight (429 back-off? the OAuth token in the keychain expiring
  while no interactive session refreshed it?) -- `~/.claude/usage-api-log.csv`,
  `~/.claude/usage-api-backoff`. Then `rm build/minutes-pacing.STOPPED`; launchd restarts it
  within 30 min. Its overnight output (recording-minutes/, official-votes/) is uncommitted
  in this tree -- the refresh will treat it as somebody else's work; commit it after.
- **The overnight job (02:30) was STOPPED and unscheduled** at 08:20. It spent 5.5 hours in
  `build_search_index.py` -- every file read (4,535), then a long FTS5 query loop
  (fts5NextMethod) that scales badly now the index holds ~2,900 OML letters and the new
  split rows. Never reached the D1 steps. So STILL TO DO, after the refresh:
  1. `python3 scripts/sync_d1.py --full` (fits on Workers Paid; recreates parents+children,
     so it sidesteps the foreign-key wall; `--check` after).
  2. Find the slow FTS5 step in `build_search_index.py` (likely a per-document MATCH or the
     affinity pass) and fix it; then `sync_search_d1.py` -- site search has been frozen
     since 8 Oct (SQLITE_TOOBIG, fixed by `890111ac`, but never pushed).
- **Uncommitted in the main tree** (from last night's deploy builds + the paced run): fy28 API
  payloads, views/ (2,896 OML text view links removed), recording-minutes, official-votes,
  watcher logs. Commit them once the refresh finishes (the refresh will not stage them).

## Open work, in rough priority order

1. **Cloudflare: the account is on WORKERS PAID since 9 Oct.** D1 bills instead of stopping
   (CLAUDE.md updated); databases may reach 10 GB. The PAGES 20,000-file limit is NOT lifted
   (needs Pro): the build is 18,238 after the OML texts were moved to GitHub links
   (`be4f1142`). Plan the next cut before the next refusal.
2. **D1 bug 3** (rebuilding a parent table under its children) remains in the incremental
   path; `--full` sidesteps it. Decide later whether to fix the incremental path (UPSERT).
3. **Para salary correction -- DONE** (`notes/findings/PARA-SALARY-CORRECTION.md`): 107 of 120
   hourly rates rose ~4%; the model's 3.0/2.0/2.0 para rates are now understated -- queue a
   model update. **Dee Bus -- DONE** (`notes/findings/DEE-BUS-CONTRACT.md`). Request only
   partly answered: a follow-up for the FY23-FY25 contract would settle the 7.6% question.
4. **Transportation report -- LIVE** at /analysis/transportation (schools section). TJ is
   reviewing; changes go in `scripts/build_transportation.py`, never by hand.
5. **Journal export** -- full 1,744-page report requested from the Town Manager; samples in
   `build/inbox/2026-10-09-town-manager-journal-samples/`. 13e gate when it lands.
6. **Decisions still with TJ:** the internal para-wages email (raw withheld, transcription
   published -- OK?); retire `~/lunenburgbudgets-refresh`; the morning report
   (notification/file/both).
7. The OML index (model-free parts), the OML filename-decoding bug (OML 2023-243),
   MUNIS Part 2, an off-machine backup, the 9 MUNIS PDFs to publish, and having the paced
   run commit its own output daily.

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
