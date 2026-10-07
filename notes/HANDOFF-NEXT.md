# Handoff: everything not yet done, as of 7 October 2026

One list for the next session. Read this first; the two linked handoffs carry their own
detail. Everything below the line "Done" is context, not work.

## Open work, in rough priority order

1. **Deploy the per-board "Missing records" pages** -- built and committed (`ab15603a`), NOT
   live: they are new routes, so they need a FULL site build (`cd fy28 && npm run build:site`,
   ~36 min today, never a bare `vite build`), then `npx wrangler pages deploy` from `fy28/`
   (Node 22), then check `/boards/parks-commission/records` on production. The same build
   relabels the email-notice agenda link (item 8). See the section at the bottom.
2. **The site build is incremental** (7 October, `HANDOFF-FASTER-SITE-BUILD.md`): a build
   with nothing changed takes ~1 minute, one data file ~2. NOT YET DEPLOYED with it: the
   og:url fix (every live page says `localhost:61348`), the "not available" approval
   window on board records, and `meeting-record-explanations.csv`.
3. **A way to delete from the archive** -- `notes/HANDOFF-TAKEDOWN.md`. Still wanted, but
   it has NO current case: the MUNIS logins it was for look like staff email names, and TJ
   decided on 7 October they are not an issue (see the top of that handoff). Not urgent.
4. **The meeting backlog** -- TJ runs it, ideally outside a long session:
   `python3 scripts/process_meeting.py --next N --dry-run`, then without `--dry-run`,
   redirecting to `build/process-meeting-<date>.log`. Watch for free with
   `tail -f build/process-meeting-*.log | grep --line-buffered -E "^\[|wrote|FAILED|STOPPED|done|completed"`.
   ~$0.14 a meeting measured. If a session watches it, by EXCEPTION only (memory:
   monitor-by-exception).
5. **FY25 school surplus report** (`/analysis/fy25-school-surplus`, UNLISTED) -- before it is
   linked: the waterfall chart is an SVG, the web COMPONENT is owed (rule 7f); run the
   persona review (rule 15a); then delete its line from `sources/analyses/UNLISTED`.
6. **MUNIS Part 2** -- the Town Manager is still preparing it; she is removing citizen names
   that appear as vendors in a special-education fund. The request PDF she has
   (`notes/outbound/drafts/MUNIS-REQUEST-RUNS.pdf`) gives her the steps, keeping the vendor
   number. When it arrives: it is held at the gate automatically (`redact.gate`, any key
   under `town-ledgers/`); verify every text field ourselves (a vendor name that is a
   person; logins in PDF headers), publish what is safe, THEN build (CLAUDE.md 13e). Re-run
   `scripts/build_munis_request_xlsx.py` and `build_munis_request_runs_pdf.py` -- they fill
   in what arrived from the data.
7. **The 9 PDFs of the 6 October MUNIS delivery** are `pending` in `redactions.csv` only
   because every page prints the report user's login. With the 7 October decision that
   logins are not an issue, they can be screened and published as-is -- TJ to confirm,
   since it is a publish (13e). The spreadsheets already carry every figure.
8. **Next full site build** will also: relabel an email-notice agenda link (the board page
   says "the posted agenda" -- wrong for one that was emailed; the label is in the page
   code), and refresh the prerendered HTML behind today's data-only deploys.
9. **`notes/reference/records-requests.csv`** -- another session's uncommitted edits to it
   were lost on 6 October (overwritten; unrecoverable). If TJ recalls updating a request's
   status or dates around 5 October, that needs redoing.
10. **Reports to build** -- `notes/REPORTS-TO-GENERATE.md`, ordered; 1 = "Is anyone sitting on
    money?", now with four closed school years from `munis-school-ytd.csv`.
11. **An off-machine backup copy** -- the verified snapshot
    (`~/lunenburg-backups/2026-10-06-214608/`) is on the same disk as the repo.

12. **The usage governor -- TJ approved 7 October, BUILD AFTER 4:40 PM that day.** Live
    usage now arrives without /usage: `~/.claude/statusline-usage.sh` (statusLine,
    refresh 60 s) logs `five_hour`, `seven_day` and the reset epoch to
    `~/.claude/usage-log.csv` while a session is open. Build into process_meeting: stop at
    X% of session OR weekly; pace along a straight line to the cap at the reset (wait when
    ahead, add a worker -- 2-3, one dispatcher, one queue -- when behind); emergency stop if
    the window fills >2x the planned slope over 15 min; keep backlog_pace's spend-to-output
    guard; stale reading -> dollar estimate and ONE worker.

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

Built 7 October 2026, committed `ab15603a`, not deployed.

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
