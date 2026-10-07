# Design: a backlog run steered by the real usage bars

Written 7 October 2026. Approved by TJ the same day; **build after 4:40 pm** so the build does
not spend the window the run is filling. Nothing here is built yet.

TJ: *"add meetings as fast as possible until we hit a certain percent of either a session
window or weekly window, and also rate limit it when the rates are going faster or slower
than desired. or even stop it if the window is filling faster than expected (meaning, the
same as our guards, but now directly against usage limits)"* -- and, on every guard:
*"checking that we're not burning tokens ONLY and we're producing expected output."*

## The interface -- ONE command, the way minutes are already started

TJ, 7 October 2026: *"my assumption was this tool is kicked off the same way i kick off
minutes. except now, i say, 'run minutes until we hit 80% weekly usage or 90% session
usage'."* So:

    python3 scripts/process_meeting.py --until-usage --week-cap 80 --session-cap 90

It runs the backlog newest-first until EITHER cap is reached. On the session cap it waits
for the window to reset and carries on; on the weekly cap it stops. It needs no `--next N`
and no wrapper: **this replaces `run_backlog_until.py`** (the chainer that kept one run going
until 9 pm), which is retired once this is proven. `--next N` and `--max-usd` still work and
bound it further. The caps default to 95 session / 90 weekly (TJ: "your decisions are fine").
An emergency stop writes `build/STOP-METERED`, which ends the whole run.

## The RATE -- derived from the caps and the clock, never typed

TJ, 7 October 2026: *"how can we set the RATE that we reach those"* -- and *"what if i want
to hit the session limit in the next 1 hour"*.

    session rate = (session-cap - u5) / (time to the 5h reset - 10 min)     %/hour of the window
    weekly rate  = (week-cap  - u7) / (time to the weekly reset)            %/hour of the week

The run follows the SLOWER of the two, so neither cap is overshot, and re-derives both every
minute from the live bars (closed loop: behind -> add a worker, ahead -> wait).

**`--by TIME`** moves the deadline: `--by +1h`, `--by 16:30`, `--by "thu 23:00"`. It replaces
the reset as the end of the target line, for whichever cap it is given with:

    process_meeting.py --until-usage --session-cap 90 --by +1h     # fill the window in an hour

**`--rate N`** holds the session bar at a fixed N %/hour instead (room kept for interactive
work). **`--max-jobs`** (default 3) is the speed limit: one worker is ~16 %/h of a window, so
3 is ~48 %/h at most, ramped one worker per 5 minutes.

**It says up front when a target cannot be met**, rather than quietly missing it:

    [gov] session 90% by 15:40 needs 60%/h; 3 workers reach ~48%/h -> ETA 16:05
    [gov] at the session cap every window, the week reaches only ~70% by Thu 23:00

The 5-hour window bounds how fast the WEEK can fill (one window at ~$32-37, ~7 windows in
the last 35 hours of a week), so a weekly cap can be unreachable however the session is run.

**The emergency stop is relative to the plan** -- more than 2x the PLANNED slope -- so a
deliberately fast hour does not trip it and a runaway beyond it does. Stopping is
anticipated by ~1 point per worker in flight, so a 90% cap lands just under 90.

## What exists today, and what this replaces

| piece | today | after |
|---|---|---|
| speed | one meeting at a time, ~$6/h, ~16% of a window an hour | 1-3 workers, chosen every minute |
| aim | ~80% of a window, from a $37 ESTIMATE | a % the operator picks, measured |
| stop | usage-limit text in a step's output (i.e. after the window is already full) | before the cap, from the bar itself |
| spend vs output | `backlog_pace.py` -- every paid call matched to its file | unchanged, and it can now stop the run |

## The signal

`~/.claude/statusline-usage.sh` (the status line, refresh 60 s) appends every changed reading
to `~/.claude/usage-log.csv`:

    at,five_hour,seven_day,five_hour_resets_at,session

- `five_hour`, `seven_day` -- the same percentages `/usage` prints.
- `five_hour_resets_at` -- epoch seconds; the window's end, so the target line has an end.
- Only COMPLETE readings are logged (both bars), deduplicated per session. On the first run
  other open sessions reported a weekly figure with no five-hour one (20/69/72% beside this
  account's 29%); those are not readings of this window and are dropped.

**It only refreshes while a Claude Code session is open.** A reading older than
`STALE = 5 min` is UNKNOWN, never current -- see Fallback.

## The controller -- one loop, once a minute, inside `process_meeting.py`

Inputs: the latest reading `u5` (five-hour %), `u7` (weekly %), its age, the reset time `R`,
and two caps the operator gives: `--session-cap` (default 95) and `--week-cap` (default 90).

1. **CAP.** If `u5 >= session-cap` or `u7 >= week-cap`: start nothing new. Let in-flight
   meetings finish (a step killed half-way is paid for and produces nothing). If the window
   resets before `--until`, wait for `R` and resume; otherwise end the run.

2. **TARGET LINE.** At the start of each window, take `(t0, u0)` and draw a straight line to
   `(R - 10 min, session-cap)`. The 10 minutes are margin: in-flight meetings land after the
   decision to stop. Target now = `u0 + (cap - u0) * (now - t0) / (R - 10min - t0)`.

3. **PACE.** `gap = u5 - target` in points.
   - `gap > +3` (ahead): drop to 1 worker and sleep between meetings until back on the line.
   - `-3 <= gap <= +3`: hold the current worker count.
   - `gap < -3` (behind): add a worker, at most one per 5 minutes, up to `--max-jobs`
     (default 3). The 5-minute step is the brake on the 3 October failure: concurrency rises
     only after the bar has shown what the last step cost.

4. **EMERGENCY STOP -- filling faster than planned.** Over the last 15 minutes of readings,
   `slope = Δu5 / Δt`. If `slope > 2 × the target line's slope` AND `u5` is above the line:
   stop ALL workers after their current meeting, write `build/STOP-METERED`, notify. A person
   restarts it. This is "crushing it in the first five minutes", caught in minutes rather than
   at the limit. (Interactive work counts toward the same bar -- if TJ starts a heavy session,
   the governor slows or stops the batch, which is the point.)

5. **OUTPUT GUARD -- unchanged and binding.** Before each new meeting, `backlog_pace.audit()`
   over the last hour. Any paid call with no output, any output with no paid call, REPEATING,
   or `$/file > $0.50` once `$1` is spent: stop, exactly like today. Usage going up with
   output not going up is the failure TJ named, and it is checked in dollars AND in files,
   never in the bar alone.

## Workers -- parallel without paying twice

- **One process, one lock, one dispatcher.** The dispatcher pops the next meeting off ONE
  newest-first queue and hands it to a worker thread; a meeting is never handed out twice.
  `--oldest` remains for a separate slow run and is not needed once this exists.
- Every worker obeys the same kill switch, limit-text stop, ceiling and failure counters. A
  limit or STOP seen by any worker stops the dispatcher.
- The `--max-usd` ceiling and the no-progress (`stuck`) check keep working as now, summed
  across workers.

## Fallback when the reading is stale

No session open (TJ away 5-9 pm with the computer idle): the reading ages past 5 minutes.
Then: **one worker, no parallelism**, paced by dollars against the window estimate
(`$/h <= cap% × window$ / 5h`, window$ = the measured $32-37). Same as today's run. Parallel
work is only ever chosen on a fresh measurement.

## Output to the log TJ tails

One line per decision change, starting `[gov HH:MM]`, so `tail_backlog.sh` shows it:

    [gov 15:02] 5h 58% (target 55%, +3) 7d 31%  workers 2->1  ahead of the line
    [gov 15:40] 5h 71% (target 71%)  workers 1->2  behind
    [gov 16:28] 5h 94% -> cap 95 reached; finishing 2 in flight, then waiting for 16:40

## How it is proven before it runs unattended

1. **Unit:** the controller as a pure function `decide(readings, now, caps, jobs) -> (jobs,
   sleep, stop)`, tested on synthetic series: on the line, ahead, behind, a 3x spike, a stale
   reading, cap reached.
2. **Dry run:** `--dry-run --governor` prints the decision for the current real reading.
3. **Capped live run:** `--next 10 --max-jobs 2 --session-cap <now+5>` -- it must stop at
   the cap, and `backlog_pace.py --audit` must show every paid call matched.

## Decided

- Defaults 95 session / 90 weekly; the emergency stop ends the run (TJ, 7 October 2026).
