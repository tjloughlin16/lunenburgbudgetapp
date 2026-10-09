# Handoff: everything not yet done, as of 9 October 2026, 07:30

One list for the next session. Read this first; the linked handoffs carry their own detail.
The 7 October version of this file is in git history (`git log -p notes/HANDOFF-NEXT.md`).

## Running right now (background, started 9 October)

- **The minutes backlog, governed.** Started 06:45:58:
  `python3 scripts/process_meeting.py --until-usage --session-caps 80 --by 09:00 --max-jobs 6 --week-cap 85 --max-usd 45`,
  log `build/process-meeting-2026-10-09.log` (marker `=== MORNING`). At 07:22 the window
  was at 28% against a line of 26%, at ~1.0 point a meeting. **The `--by 09:00` is wrong for
  this window:** it opened ~06:40 and resets ~11:40, so the run will stop at 80% around
  09:00 and leave ~2.5 h of window unused. To retarget: stop it (`touch build/STOP-METERED`
  or kill the process; finished meetings are kept), remove the stop file, restart with
  `--by 11:30` and a cap TJ chooses (95% was suggested). Its output -- files under
  `sources/data/official-votes/`, `recording-minutes/` and friends -- is UNCOMMITTED;
  commit it when the run ends (the 8-9 Oct overnight output was committed as `cf19f3c3`).
- **The AG determinations download.** `python3 scripts/fetch_oml_determinations.py --all`,
  appending to `build/oml-determinations-all.log`; at 07:22 it was walking OML 2013-170.
  Download only: TJ, 8 Oct, *"Let's just ingest them. Don't process them for now."*
  Lands through `ingest`, so every letter is in the bucket. Restarted 9 Oct ~06:46 after the
  OML 2012-5 crash (one number listed twice; fixed in `7f5005a8`). When it finishes: commit
  `sources/state-law/`, then re-run `pdf_kind` over every letter (see
  `HANDOFF-OML-INDEX.md` -- the letters are DIGITAL; never OCR them wholesale).
- Nothing watches either job once this session ends. `tail -f` the logs, or
  `bash scripts/tail_backlog.sh`.

## Open work, in rough priority order

1. **Retarget the minutes run** (above), and commit its output when it ends.
2. **The refresh, rebuilt as always-additive** -- design approved in principle,
   NOT BUILT: `notes/HANDOFF-REFRESH-ADDITIVE.md`. Runs in whatever branch it is in, never
   destructive, a page that fails to build is marked blocked and the run moves on. Today's
   refresh tree was unstuck by hand on 9 Oct (reset to main; the stranded 22 Sep commit is
   kept on branch `stranded-refresh-2026-09-22`). Also: the refresh does not log spend for
   `write_recording_minutes` -- fix inside the redesign.
3. **D1 sync fails with a FOREIGN KEY constraint** (seen 9 Oct). Not investigated. The
   live `/api/query` still serves the older database. Start with `python3 scripts/sync_d1.py`
   and read which table it stops on.
4. **The journal export** (TJ, 9 Oct: *"I'm told the journal export is on its way"*). When
   it arrives it is held at the gate (13e): verify every text field for a person, publish,
   THEN build. It answers: report #12's "spent with no budget" lines, the surplus
   "Was it thrift?" question, and what the special-education overrun was spent on. Roll up
   the journal lines to the period-13 totals before using any of it.
5. **The OML index** (model-free parts only): rule units, issue taxonomy, FTS over the
   letters, citation graph -- `HANDOFF-OML-INDEX.md` sections 1, 3, 4. The model DIGEST of
   the letters waits, and when built runs as a pipeline identical to `process_meeting.py`
   (newest first, resumable, governed). TJ, 8 Oct.
6. **Decisions waiting on TJ:**
   - the new top-level folder `sources/state-law/` (CLAUDE.md "no new top-level folder";
     it holds the statute, 940 CMR 29, AG guidance and the determinations);
   - whether to LIST any of the unlisted reports (below) -- persona review (rule 15a) first;
   - the next FinCom report: #3, "The school budget beyond the vote"
     (`notes/REPORTS-TO-GENERATE.md`);
   - the 9 PDFs of the 6 Oct MUNIS delivery, pending only for staff logins in the
     headers, which TJ said on 7 Oct are not an issue -- confirm publish (13e).
7. **After the next refresh**: check that no 2027-dated minutes reappeared (a resurrection
   seen once, cause not established).
8. **MUNIS Part 2** -- still with the Town Manager (vendor names that are people). Same gate.
9. **An off-machine backup copy** -- `~/lunenburg-backups/` is on the same disk.
10. **`notes/reference/records-requests.csv`** -- edits lost 6 Oct; if TJ remembers changing
    a request around 5 Oct, redo it.

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
