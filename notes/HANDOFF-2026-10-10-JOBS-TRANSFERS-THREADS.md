# Handoff: jobs, transfers, threads, search, org-chart sources

Written Saturday night, 10 October 2026, by the session that did all of it, for TJ to pick up
after a reset. The earlier workstream from the same session (the transportation brief, the
FY26 surplus audit) is `notes/HANDOFF-CITIZEN-FIRST-REPORTS.md`; its open decisions still stand
and are repeated at the bottom.

**State:** everything is committed and pushed (`main` = `origin/main`). The last deploy was
started at the end of the session (build + `wrangler pages deploy`, with retries). **First thing
tomorrow, check it landed:** `curl -s https://lunenburgbudgetproject.org/data/threads.json | grep -c '"hot"'`
should be non-zero. If not, run `npm run build:site` then `npx wrangler pages deploy` from `fy28/`
(Node 22 via nvm). Uploads failed repeatedly tonight with `write EPIPE` while the machine was
under load (load average 40+); the same files deployed fine once the machine was idle. **Never
build while process_meeting / the refresh is running if you can help it.**

## What shipped (by feature)

| feature | where | built by | notes |
|---|---|---|---|
| Transportation brief answers TJ's 4 questions | `/analysis/transportation` | `build_transportation.py` | trend since FY2019, circuit breaker offset, athletic fund shift, trips per sport (ours) |
| Search: Jobs and People kinds | `/search` | `build_search_index.py` (`job`, `person` corpora) | person = one row per name on the org charts; same name ≠ proven same person |
| Search: partial words + words-together ranking | `functions/api/search.js` `ftsExpression` | — | every word ≥3 letters is a prefix; exact phrase and NEAR(…,3) OR'd in so words together rank first; all kinds queried in PARALLEL |
| Search: spinner, slow notice, no empty search on load | `pages/Search.tsx` | — | |
| Search: `per=` (≤60) and `match=together` API params | `search.js` | — | used by search-built threads |
| Job postings page, town + schools | `/jobs` | `build_job_postings.py` (+ `fetch_town_job_postings.py`, new) | town job board fetched daily; snapshot only when parsed postings change; parse must tie to the page's own category counts or it refuses |
| Job notifications tray | header "Jobs" button | `components/JobPostings.tsx` `JobsTray` | badge = new since this browser last opened it; "taken down", never "filled" |
| Jobs block on board/department pages | `/boards/<slug>`, `/departments/<slug>` | `job-posting-owners.csv` (ours, with basis) | |
| Transfers for every board | `/boards/<slug>/transfers` | `build_board_transfers.py` (was build_school_transfers) | 13 boards; evidence graded per row: district FORM (gold) / town minutes / recording; FY = stated in minutes else meeting's FY (marked †) |
| School transfers: tentative + accounts | `/boards/school-committee/transfers` | `school-transfer-sheet-lines.csv` (transcribed by eye from the district's forms, every side ties to the printed total) | 7 Oct 2026 FY27: $41,560.06 tentative (two transfers) + $1,784.90 reclassification; accounts looked up in the MUNIS ledger for building (segment 6, 99/99 consistent) and DESE function; "crosses schools/programs" flag |
| Org chart sources | `/org-charts` | `build_org_charts.py` `source_docs()` | every name has a source number → our copy (with `#page=N`) and the publisher's |
| Org chart: LIKELY INCORRECT band | `/org-charts?unit=Lunenburg Public Schools` | `build_org_charts.py` | 36 people only on the district's master list at a school whose own sheet omits them (Melanie Roy among them); muted, own band, out of headcounts. 11 district-wide master-list-only people kept with † |
| Org chart links on board pages | board sidebar | `lib/orgChartLink.ts` reads `/docs/data/body-crosswalk.csv` | 31 of 60 boards |
| Threads: pin + Top threads | `/threads` | `threads.csv` new `pin` column | turf = pin 1 |
| Threads: FY26 school surplus | `/threads/fy26-school-surplus` | `threads.csv` | 3 meetings so far |
| Threads: 🔥 HOT | thread cards | `build_threads.py` `temperature()` | open + ≥3 meetings + ≥2 boards in 30 days + latest ≤14 days; 6 of 18 qualify today (Town Meeting run-up) |
| Threads: search-built | `/threads/<slug>?q=<words>`, "Create a thread" on search | `components/DynamicThread.tsx` | every dated mention, words together, oldest first; each mention and meeting heading links to the raw record |
| Threads link in header | header | `App.tsx` | |
| Contention detection (forward only) | `write_recording_minutes.py` SCHEMA `contention` | same minutes call, no extra runs | missing key on older files = NOT READ, never calm; threads show "Contested" |

## Root causes found and fixed (worth remembering)

- **`build_threads.py` was in neither the daily refresh nor `check_generated`** → threads.json frozen
  at 19 Sep for three weeks. Now in both. Same check for any new generator: is it in `refresh.py`
  and `check_generated.py`?
- **Threads read only votes/decisions/topics** → budget discussion and public comment never reached
  a thread. Now read too.
- **The district's master staff list is not authoritative** for a building with its own sheet (TJ).
  Registered in `money-gaps.csv`; closes with a dated HR roster.
- **Town minutes never print account codes** — only the district's transfer forms do.
- **A sheet reader that took the first total** dropped the second 7 Oct transfer. Read all.
- **Rebuilding the search index during a site build** reads a half-written `dist/` and drops pages
  from live search. Never run `build_search_index.py` while `build:site` is running.

## Not done / open (TJ's calls)

1. **Search-built threads may miss mentions** (TJ, last message: "may not be correctly identifying
   all mentions… maybe it is"). Known limits, all by design, worth reviewing with an example:
   - only DATED kinds (minutes/agendas, our notes, captions, jobs) — documents carry no date;
   - `match=together` requires the words within 5 words of each other (stops "Turkey Hill … roof"
     four pages apart) — a meeting that says it differently is missed;
   - the newest 60 per kind (the page says when the cap hit);
   - our notes exist only for meetings we processed; the town posts SC minutes late (none after
     26 Aug 2026 as of tonight — checked, 404).
2. **Contention backfill** for the turf meetings (24 Sep FinCom, 29 Sep/6 Oct SB, 7 Oct SC, 8 Oct
   FinCom): ~1% of a 5-hour window each via `process_meeting.py`. TJ said forward-only; ask before.
3. **A "ledger says" view on transfers** — the MUNIS reports carry net transfers per account per
   year (305 town accounts in FY26 p12). Offered, not built.
4. **Sources convention on every page** — TJ's main to-do (memory `sources-on-every-page`); the org
   chart is the worked example. Not started on purpose.
5. **Search speed**: production "budget" ~3.5s after the parallel fix (was 6.2s). If still slow,
   stop prefixing very common or short words. Local dev search is slower (~8s; sync sqlite).
6. From the earlier handoff, still open: REPORT-FORMAT.md + CLAUDE.md 7b/7d; model transport rate
   (6% vs contract 7.4%); derivations.py spread; FY27 $1 gap; fy26-closeout §8; list/unlist the FY26
   surplus page; NextLevel filing (not yet offered for tonight's features).
7. A React duplicate-key warning on `/boards/school-committee` in dev — not traced, may predate this.

## Commands

    python3 scripts/build_board_transfers.py --check   # transfers, all boards
    python3 scripts/build_job_postings.py --check      # /jobs + town postings
    python3 scripts/fetch_town_job_postings.py --check # town job board snapshots
    python3 scripts/build_threads.py --check           # threads (now in refresh + check_generated)
    python3 scripts/build_org_charts.py --check        # org charts (+ downstream: body_crosswalk, tenure, roster_completeness, report_filing)
    python3 scripts/build_search_index.py --check && python3 scripts/sync_search_d1.py --plan
