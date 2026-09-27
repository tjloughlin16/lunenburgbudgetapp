# Handoff: what ingest costs, and where it must run

Written 27 September 2026, at the end of a session that cost about four times what the
work inside it did. Read this before doing any ingest or extraction work.

---

## 1. THE RULE THAT MATTERS MOST

**Never do ingest work in a context-heavy session.** Every turn re-sends the whole
conversation, so identical work costs several times more at turn 200 than at turn 3.

The test before starting anything: *could this run with none of this conversation in front
of it?* If yes, it must not run here. Ingest and extraction take a page and a rule and
produce rows -- they depend on no history -- so they go to a fresh session, a subagent, or
a `claude -p` script.

This is rule 7g in `CLAUDE.md`, and it exists because it was got wrong on the day it was
written.

## 2. THE NUMBERS, MEASURED RATHER THAN ESTIMATED

The calibration in `CLAUDE.md` holds: **1% of the weekly allowance is about $5 of the
API-equivalent cost the CLI reports.**

| work | measured cost | where |
|---|---|---|
| one votes extraction | $0.15 | `extract_official_votes.py` |
| one recording-minutes write | $0.42-$0.57 | `write_recording_minutes.py` |
| one annual-report page, read in isolation | **$0.32 average** (0.064% of a week) | `benchmark_ingest.py` |
| ten annual-report pages | **$3.19, 0.64% of a week, 2,004 values, 21 minutes** | same |

The ten-page run moved `/usage` from 58% to 58%. It is, against the weekly cap,
effectively free.

**What is NOT measured, and cannot be from inside a session:** what the session itself
costs. `total_cost_usd` comes back from every `claude -p` call, so scripted work prices
itself; nothing equivalent reaches an interactive session. Every session figure in this
file is arithmetic off TJ's own `/usage` readings, which only he can run.

On the day this was written: roughly 10% of the week went to about a thousand unattended
jobs, and roughly 40% to the conversation beside them.

## 3. WHAT IS RUNNING, UNATTENDED

| what | when | notes |
|---|---|---|
| `sweep_supervisor.sh` | every 30 min (launchd) | runs a 25-minute sweep IN THE FOREGROUND |
| `away_sweep.sh` | 02:00 Sunday, Monday | no ceiling; stops when the plan refuses |
| `weekly_sweep.sh` | 02:00 Thursday | before the Thursday 11:00 reset |
| `refresh.sh` | daily | the ordinary watch-and-fetch run |

**The reset is THURSDAY 11:00 America/New_York.** Not Wednesday. `weekly_sweep.sh`
records why that matters.

Health in one line, and it measures OUTPUT rather than liveness:

    python3 scripts/sweep_health.py      # exits non-zero if nothing has been written

## 4. TWO DEFECTS FOUND THE HARD WAY, BOTH FIXED, BOTH WORTH REMEMBERING

**A process being up is not a process working.** On the night of 26 September both streams
stopped producing at about 23:00 -- the sweep hit the rolling FIVE-HOUR session limit and
went into exponential backoff, the votes backfill died -- and both processes stayed alive
and idle for eight hours. `pgrep` reported them running, because they were.

**And launchd reaps a job's entire process group when the script exits.** The first
supervisor used `nohup ... &` and returned, so both children died instantly, every time.
It logged `restarted` on the half hour for hours while both logs stayed at zero bytes. A
restart that cannot outlive its own supervisor is worse than none, because it reports
success. The work now runs in the foreground inside a window shorter than the launchd
interval.

**The limiter is the rolling five-hour window, not the weekly cap.** You cannot spend a
week's allowance in a day by running harder. It has to be spread across days.

**And the spend ledger had no costs in it at all** until 27 September: `cost_of()` scraped
stdout for a `$` and neither sub-script printed one, though both already held
`total_cost_usd`. Every row back to 18 September has an empty cost column.

## 5. THE ANNUAL REPORT PAGES

One unit is one PAGE. `benchmark_ingest.py` reads a page in isolation, and the run KEEPS
its work -- the benchmark IS the ingest:

    python3 scripts/benchmark_ingest.py --fy 2017 --page 148
    python3 scripts/build_annual_report_reads.py    # the JSON reads -> a CSV the map sees
    python3 scripts/map_annual_report_pages.py      # ...which is what moves the counter

**A page counts as read only when a CSV carrying `fy` and `page` cites it.** JSON moves
nothing. And `ingest-benchmark.csv` is excluded from that scan on purpose: it carries
`fy` and `page` and would have counted an ATTEMPT as a reading, including a page that
refused. A number that moves without the archive moving is the one thing this count must
never do.

**A refusal is a correct answer and is not written.** Several pages return no rows because
OCR merged header cells -- FY2019 p53-55 merge `COMMITTMENTS ABATEMENTS` into one box, so
seven header words sit over eight columns. Naming that last column from its position is
rule 13b's own trap. Those pages wait for the header to be read properly rather than
being filled in.

## 6. WHAT ELSE SHIPPED THAT DAY

`/analysis/towns-like-us` is deployed and UNLISTED (`sources/analyses/UNLISTED`). Its
headline finding changed late: a tax bill is a dollar amount and moves with house prices,
so every comparison that ranked towns by it was ranking the housing market. Lunenburg is
145th of 351 on the dollar bill and **78th of 351 on the bill as a share of what a home is
worth**. That reversed `Only 8 of 161 can` to `Only 20 of 161`, added a fourth route
(houses that are WORTH a lot, not many houses), and left six towns explained by nothing --
registered in `money-gaps.csv`.

`scripts/verify_towns_like_us.py` -- 83 checks, all passing.

## 7. WHAT IS NOT ESTABLISHED

- **What a session costs.** No number reaches the agent. Only TJ's `/usage` says.
- **Whether the ÷5 convention still holds** after any plan or promo change. Re-measure
  with `benchmark_ingest.py` and a `/usage` reading either side.
- **FY2024 p38/p39** are titled `FY2021 COLLECTION OF TAXES` while dated June 30 2024.
  Nothing has settled whether those are prior-year comparatives or a reprinted heading,
  and nothing should be published from them until it has.
- **The six low-effort towns** that fit none of the four routes -- Ipswich, Woburn, Lenox,
  Medford, Canton, Norwood. Three carry business shares near twice the median and fail
  only the exact 2x test, which is said on the page rather than tuned away.

## 8. IF YOU DO ONE THING

Confirm the streams are producing, and then leave them alone:

    python3 scripts/sweep_health.py
    bash scripts/status.sh --once
