# Handoff: everything not yet done, as of Saturday 10 October 2026, 09:10

One list for the next session. Read this first; the linked handoffs carry their own detail.
Earlier versions are in git history (`git log -p notes/HANDOFF-NEXT.md`).

## RIGHT NOW (Sat 10 Oct 09:10) -- everything from the 08:30 list is DONE

- **The paced minutes run is RUNNING again, and WAITING** (week 30% vs line 18.3%; the line
  reaches 30% around Sun 07:00). Restarted 09:06 on the fixed governor. Why it overspent
  overnight, all fixed and pushed:
  - stale + weekly line -> wait (`9c560673`);
  - after a 5-hour reset the server sends `resets_at: null`; fetch() threw and discarded the
    reading -> went STALE at 22:05 (`47a2ea70`, a null reset is now a reading);
  - a failed fetch waited a full 30 min to retry (now retried at FETCH_EVERY_S) and left no
    trace -- failures now go to `~/.claude/usage-api-errors.csv` (`47a2ea70`);
  - the OAuth token lapses ~8 h after last use when nothing calls the model; fetch() now
    renews it first (`claude auth status`, else one haiku call, $0.0054, at most 1/30 min,
    logged as kind `renew`) (`954bc940`). HYPOTHESIS for 06:20-08:15 Sat, not proven: the
    first `renew` or `401` row in the errors CSV will settle it.
- **The "5.5-hour search build" was SLEEP, not compute.** The 02:36 job slept at 02:37:11
  and ran ~45 s an hour. Awake, the build is 15 s. `daily_refresh.sh` now holds
  `caffeinate -i` for its lifetime (`c505bcff`); it still cannot WAKE the machine at 07:00
  (that needs `sudo pmset repeat wakeorpoweron`, TJ's call).
- **Site search is current** -- frozen since 8 Oct, now pushed (3,288 files) and
  `sync_search_d1.py --check` ok. Fixed: FTS5 UNINDEXED lookups scanned the table
  (`b784473b`, a `search_key` table); rows indexed before the 40,000-char split were never
  re-split (`235a4806`); two files could share a doc_key and hide each other (`235a4806`).
- **D1 analysis database current**: `sync_d1.py --full`, 122 tables / 161,301 rows match.
  D1 bug 3 FIXED in the incremental path (`6445f815`: parents upserted, never emptied;
  tested against strict FKs, not yet against D1 itself -- watch the next push that changes
  `document`).
- `build_source_index.py` no longer fails on a SQLite `-journal` beside a skipped DB (`b9a83593`).
- **The 10 Oct refresh did NOT deploy** -- six outputs were stale because the overnight run's
  output was uncommitted; that is committed (`cced8d52`) and they reproduce (`9028f145`).
  The site deploys on the next refresh, or by hand when TJ asks (rule 10).
- `check_watch_gaps.py` exits 1 on six days the watcher missed (18 Sep - 6 Oct). History;
  nothing to fix.
- **Not mine, left alone:** uncommitted `build_transportation.py` / `transportation.md` /
  `transportation.json` (another session, 08:53) and fy28/public/api/* payloads.

## Open work, in rough priority order

1. **Cloudflare: the account is on WORKERS PAID since 9 Oct.** D1 bills instead of stopping
   (CLAUDE.md updated); databases may reach 10 GB. The PAGES 20,000-file limit is NOT lifted
   (needs Pro): the build is 18,238 after the OML texts were moved to GitHub links
   (`be4f1142`). Plan the next cut before the next refusal.
2. ~~D1 bug 3~~ FIXED 10 Oct (`6445f815`).
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
