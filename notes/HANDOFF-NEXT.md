# Handoff: everything not yet done, as of 7 October 2026

One list for the next session. Read this first; the two linked handoffs carry their own
detail. Everything below the line "Done" is context, not work.

## Open work, in rough priority order

1. **Deploy the per-board "Missing records" pages** -- built and committed (`ab15603a`), NOT
   live: they are new routes, so they need a FULL site build (`cd fy28 && npm run build:site`,
   ~36 min today, never a bare `vite build`), then `npx wrangler pages deploy` from `fy28/`
   (Node 22), then check `/boards/parks-commission/records` on production. The same build
   relabels the email-notice agenda link (item 8). See the section at the bottom.
2. **Make the site build incremental** -- `notes/HANDOFF-FASTER-SITE-BUILD.md`. A full build
   took 36.5 minutes on 7 October (781 routes, serial, one Chrome per page). Re-render only
   pages whose code or data files changed; render 3-4 at once; print per-page progress.
3. **A way to delete from the archive** -- `notes/HANDOFF-TAKEDOWN.md`. Register + 410 Gone
   + a delete that lifts and re-locks the bucket, refusing anything not in a verified
   backup snapshot (`scripts/backup_snapshot.py --covers`). First case: 16 already-public
   MUNIS documents that print staff MUNIS logins (grep `User: +[a-z]` in
   `sources/town-ledgers` and `sources/budget-workbooks`). Take a FRESH snapshot first.
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
7. **The 9 PDFs of the 6 October MUNIS delivery** stay `pending` in `redactions.csv`
   (every page prints the report user's login). Publish as login-masked copies once the
   takedown work gives us redaction-by-mask for PDFs, or leave them; the spreadsheets carry
   every figure.
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

(to be filled in when the build job reports)
