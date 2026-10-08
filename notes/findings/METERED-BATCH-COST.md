# What a metered batch actually costs, and which bar stops it

**Measured 3 October 2026**, running `scripts/extract_official_votes.py` over the town's
official minutes: one `claude -p` call per set of minutes, haiku, output a list of votes
each carrying a verbatim quote.

Every figure here is recoverable rather than remembered. Each vote file carries its own
`cost_usd`, and `scripts/votes_run_timing.py` reports per-chunk and total elapsed, writes,
mean per meeting and spend from the files and the run log.

---

## 1. THERE ARE TWO BARS AND THE WEEKLY ONE IS NOT THE BINDING ONE

`/usage` reports a **weekly** allowance and a **rolling 5-hour session** window. Everything
written down in `~/.claude/CLAUDE.md` before today was about the weekly bar, and during a
batch the weekly bar is not what stops you.

    13:00   weekly 37%   session  1%
    17:30   weekly 42%   session 69%

The batch moved the weekly bar **5 points** and the session bar **68** in the same interval.
A 5-hour window is roughly a fourteenth of a week, so a batch that is comfortable against
the weekly cap can exhaust the session window and take the interactive session down with
it -- which is the cost that actually hurts, because it blocks a person rather than a script.

**So quote a batch in SESSION terms, not only weekly.** The old rule, *1% of the week ~ $5*,
is still right and still insufficient.

## 2. THE PER-MEETING SHARE, AND HOW TO BOUND IT HONESTLY

    mean cost per set of minutes   $0.1113   (256 priced writes)
    1% of the week                 >= $5.70
    per meeting                    <= 0.0195% of the week
    sets of minutes per 1%         >= 51

The bound is one-sided for a reason worth repeating: the interactive session also consumed
part of those 5 points, so the batch caused **at most** 5, which makes 1% worth **at least**
$5.70 and the per-meeting share **at most** 0.0195%.

And the bar reports whole percents, so `37 -> 42` is anywhere from 4.01 to 5.99 real points.
That is +/-20%: the honest range is **0.016% to 0.023% a meeting**, 43 to 64 meetings per
point. The reading sharpens as the batch's share of the move grows.

**THE PUBLISHED FIGURE WAS WRONG BY HALF.** `notes/generated/AGENTIC-BACKLOG.md` and the
ingest dashboard both state `~0.03% of the week each` for this stream. Measured, it is
<=0.0195%, so the published cost overstates by 35-55% -- and it is the number anybody sizes
a batch against. It was typed in, beside figures that are computed. Rule 2.

## 3. SERIAL vs SHARDED: the throughput lever is real and was the wrong one

The work is generation-bound, not input-bound, which kills the obvious optimisations:

    corr(duration, votes found)  = 0.61
    corr(duration, cost)         = 0.89
    corr(duration, input chars)  = 0.49

    duration   median 36s   mean 50s   p90 110s   max 141s
    input      median 6,870 chars      max 73,502

Truncating the input would not help much and risks dropping votes, which breaks the stream's
only guarantee. There is no cheaper model; it is already haiku.

The one real lever is that the run is **serial**, and `--board` makes sharding trivial: three
or four processes over disjoint board sets, same calls, same cost, 3-4x the throughput.

**It was still the wrong move, and TJ called it before the measurement did.** *"i think we'll
just burn session limits too quickly TBH"* -- then, an hour later, the session bar at 69%.
Sharding multiplies the RATE, and the rate is what the 5-hour window meters. Serial spreads
$111 across three windows; 3x concentrates it into one.

> **The rule: parallelise against a budget that refills, never against a window that meters
> rate.** A weekly cap cares how much. A rolling window cares how fast.

## 4. A REDIRECTED LOG IS NOT A PROGRESS METER

The first timing reporter counted `wrote` lines in the run log and said **0 writes after 20
minutes** while 23 vote files were already on disk. The log is Python's stdout redirected to
a file, so it is **block-buffered** in ~8KB blocks: it held 1,690 lines, every one a skip,
and the writes were in the unflushed tail.

Twenty minutes of real progress invisible, and had anybody asked *is it stuck* there was
evidence saying yes. Same shape as every instrument failure in rule 13c: the tool was
silent and the silence got reported as a fact about the work.

**Count the artefacts, not the log.** `votes_run_timing.py` takes the files' mtimes as the
authority for how many and how fast, uses the log for COST alone -- the one thing it
uniquely carries -- and prints the lag rather than averaging it away.

## 5. THE RECIPE, for the next metered batch

1. **Two bar readings bracket the batch**, and record BOTH bars each time. One reading
   calibrates nothing.
2. **Run 50 first.** It is under the threshold that needs a `/usage` check and it produces a
   real mean cost and a real seconds-per-item.
3. **Quote the batch in both bars** before starting: % of the week, and % of a 5-hour window
   at the chosen concurrency.
4. **Commit in chunks**, path-scoped. `git add -A` while a background job is writing sweeps
   its output into an unrelated commit -- it put 28 vote files into a commit about a wrong
   figure on 3 October.
5. **One writer per queue.** The extractor's `current` check protects a meeting already
   written, not one in flight, so two processes over one queue pay twice for the same item.
6. **Cap concurrency by the window, not by the machine.** See 3.

## 6. THE TARGET PACE: ONE STREAM, SERIAL, ~80% OF A WINDOW -- TJ, 7 October 2026

TJ, shown the table below: *"ok 80% in 5 hours is a perfect pace."* So that is the pace,
and it is a DECISION about how full to run a window, not only a measurement.

**Measured** (`agentic-spend.csv`, timestamped, `process_meeting.py --next 300`, haiku,
official-v1 reads, 7 October 2026 10:22-11:52): **$5.98 an hour, 42 meetings an hour,
$0.144 a meeting**, one at a time.

**Estimated, not measured: the window is ~$37.** From section 1's ratio -- 5 weekly points
against 68 session points is ~1/14 of a week, and a week is ~$500. The one direct reading
agrees: $1.15 of batch spend in the first 8 minutes after the 11:39 reset, and `/usage`
read 3% (= $1.15 / $37). But this session was also working in those 8 minutes, so the
agreement is partly luck.

| pace | window per hour | 100% after |
|---|---:|---:|
| 1 at a time | ~16% | ~6 h -- never, inside a 5-hour window |
| 2 at a time | ~32% | ~3 h |
| 3 at a time | ~48% | ~2 h |

**The rule that follows:** a meeting batch runs ONE stream, serially, and that leaves ~20%
of the window for interactive work. Two streams are only for an account with nothing else
on it, and are checked against `/usage` at the three-hour mark. This is section 3's
conclusion (serial, not sharded) with a number on it.

**What would change it:** a reading of the session bar about an hour after a reset with no
interactive session running. ~17-19% confirms the table; much lower means the window is
bigger than $37 and two streams fit.

## What this does NOT establish

- **The session window's dollar size.** 68 points for ~$28 of scripted spend implies roughly
  $0.41 a point, but the interactive session was the larger consumer of that window and its
  share is unmeasured. A batch run with no interactive session beside it would settle it --
  closes: `/usage` before and after an unattended batch on an idle account.
- **Whether the session bar is linear.** Two readings cannot show a shape.
- **That sharding would in fact have failed.** It was not tried. The 69% reading made the
  test not worth paying for, which is a decision and not a measurement.

## 7. MEASURED PER MEETING, 7-8 October 2026 -- and the $37 estimate retired

The usage governor now reads the server's own bars (`usage_governor.fetch`), so the window's
size is observed rather than estimated. Overnight 7-8 October, with the interactive session
nearly idle: **96 meetings moved the session bar from 6% to 100% for $39.80** (~$0.42 a point,
a window of pure batch ~$42), and **74 meetings moved it 3% -> 66% for $34.71**.

| a meeting that needs | API-equivalent | of a 5-hour window | of the week |
|---|---:|---:|---:|
| all three steps (our minutes on sonnet, town minutes read, reconcile) | ~$0.60 | **~1%** | **~0.1%** |
| only the town's minutes read | ~$0.02 | ~0.05% | ~0.005% |

TJ, reading it: *"So 1% per meeting."* For the backlog as it stands (early 2024, mostly
three-step meetings), yes: a full window is ~90-100 meetings, 100 meetings ~10% of a week.
Section 6's $37 window was inflated by the interactive Opus session sharing it; the batch-only
measurement above supersedes it.
