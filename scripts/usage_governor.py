#!/usr/bin/env python3
"""THE USAGE GOVERNOR -- how many workers a backlog run may have, decided from the real
usage bars. Pure: no model calls, no files written. The design is
notes/HANDOFF-USAGE-GOVERNOR.md; process_meeting.py --until-usage is what drives it.

    python3 scripts/usage_governor.py            # the latest reading, and what it means
    python3 scripts/usage_governor.py --test     # the decision rules on synthetic series

TJ, 7 October 2026: *"add meetings as fast as possible until we hit a certain percent of
either a session window or weekly window, and also rate limit it when the rates are going
faster or slower than desired. or even stop it if the window is filling faster than
expected."*

THE SIGNAL is ~/.claude/usage-log.csv, written by the status line (~/.claude/
statusline-usage.sh) every time a reading changes while a Claude Code session is open:
`at, five_hour, seven_day, five_hour_resets_at, session`. The bars are WHOLE PERCENTS, so
every threshold below is a few points wide on purpose -- a rule finer than the instrument
is a rule that fires on rounding.

THE RULES, each one a line in decide():

  cap        u5 + what is in flight >= session cap, or u7 >= week cap -> start nothing new
  line       a straight line from where the plan started to (deadline - margin, cap);
             the deadline is --by, else the window's reset
  pace       more than BAND points ahead of the line -> one fewer worker, or a pause at one;
             more than BAND behind -> one more worker, at most one per RAMP_S, up to max_jobs
  emergency  over the last SLOPE_S of readings, filling at more than 2x the planned slope
             AND above the line -> stop everything (a person restarts it)
  stale      no reading for STALE_S -> one worker, no line, no parallelism; the caps cannot
             be seen, so the limit-text stop in process_meeting is all that protects them
"""
import csv
import datetime as dt
import os
import sys

LOG = os.path.expanduser('~/.claude/usage-log.csv')
LATEST = os.path.expanduser('~/.claude/usage-latest.json')   # rewritten on EVERY refresh
STALE_S = 300            # a reading older than this is unknown, never current
BAND = 2.0               # points either side of the line that count as "on it"
RAMP_S = 300             # at most one added worker per five minutes
SLOPE_S = 900            # the window the emergency slope is measured over
EMERGENCY_X = 2.0        # filling at more than this multiple of the planned slope
PER_MEETING_PCT = 0.5    # what one in-flight meeting adds to the five-hour bar -- the
                         # STARTING guess only; the run measures its own (Plan.per_meeting)
MARGIN_MAX_S = 600       # stop aiming this long before the deadline...
MARGIN_FRAC = 0.10       # ...or this fraction of a short horizon, whichever is smaller


def readings(path=LOG):
    """Every complete reading, oldest first: dicts with t (epoch), u5, u7, reset (epoch)."""
    out = []
    if not os.path.exists(path):
        return out
    for r in csv.DictReader(open(path, encoding='utf-8')):
        try:
            out.append(dict(t=dt.datetime.fromisoformat(r['at'].replace('Z', '+00:00')).timestamp(),
                            u5=float(r['five_hour']), u7=float(r['seven_day']),
                            reset=float(r.get('five_hour_resets_at') or 0) or None))
        except (ValueError, KeyError, TypeError):
            continue
    out = sorted(out, key=lambda x: x['t'])
    # THE LAST READING IS AS FRESH AS THE LAST REFRESH, not the last change: the csv only
    # gets a row when a figure moves. usage-latest.json is rewritten every refresh; if it
    # agrees with the last row, that row is current as of the file's mtime.
    if out and path == LOG and os.path.exists(LATEST):
        try:
            import json
            j = json.load(open(LATEST, encoding='utf-8'))
            if float(j['five_hour']) == out[-1]['u5'] and float(j['seven_day']) == out[-1]['u7']:
                out.append(dict(out[-1], t=os.path.getmtime(LATEST)))
        except (ValueError, KeyError, TypeError, OSError):
            pass
    return out


class Plan:
    """What the run is aiming at, and what it has decided so far."""

    def __init__(self, session_cap=95.0, week_cap=90.0, by=None, max_jobs=3, ramp=RAMP_S):
        self.session_cap, self.week_cap, self.by, self.max_jobs = session_cap, week_cap, by, max_jobs
        self.ramp = ramp                         # seconds between added workers
        # MEASURED, not assumed. A fixed 0.5 points a meeting stopped the 7 October retest at
        # 60% of a 63% cap: six $0.016 meetings in flight were reserved as 3 points. The run
        # calls measured() as meetings finish and the bar moves.
        self.per_meeting = PER_MEETING_PCT
        self.m0 = self.mu0 = None

    def measured(self, done, u5):
        """Points per finished meeting since the first call: the bar's rise over the
        meetings done. Only once the bar has moved 2 points (it reports whole percents),
        and bounded, so one odd reading cannot make the reserve 0 or 10."""
        if self.m0 is None:
            self.m0, self.mu0 = done, u5
            return
        dn, du = done - self.m0, u5 - self.mu0
        if dn >= 10 and du >= 2:
            self.per_meeting = min(1.0, max(0.02, du / dn))
        self.t0 = self.u0 = self.window = None   # the line's start, re-anchored each window
        self.jobs = 1
        self.last_change = 0.0

    def deadline(self, reset):
        if self.by and reset:
            return min(self.by, reset)
        return self.by or reset


def decide(plan, hist, now, in_flight=0):
    """-> dict(jobs, start: bool, stop: str|None, wait_reset: bool, target, note).

    `hist` is readings() (oldest first). `in_flight` is how many meetings are running now.
    Mutates `plan` (anchors the line, records worker changes)."""
    last = hist[-1] if hist else None
    if not last or now - last['t'] > STALE_S:
        plan.jobs = 1
        return dict(jobs=1, start=True, stop=None, wait_reset=False, target=None,
                    note='STALE reading -- one worker, caps unseen')
    u5, u7, reset = last['u5'], last['u7'], last['reset']

    if u7 >= plan.week_cap:
        return dict(jobs=0, start=False, stop='weekly cap %g%% reached (%g%%)' % (plan.week_cap, u7),
                    wait_reset=False, target=None, note='')

    # A NEW WINDOW re-anchors the line where it starts.
    if plan.window != reset:
        plan.window, plan.t0, plan.u0 = reset, now, u5

    dl = plan.deadline(reset)
    if u5 + in_flight * plan.per_meeting >= plan.session_cap:
        past_by = plan.by and (not reset or plan.by <= reset)
        return dict(jobs=0, start=False, stop=('session cap %g%% reached by the --by time' % plan.session_cap)
                    if past_by else None, wait_reset=not past_by, target=plan.session_cap,
                    note='session cap %g%% reached (%g%% + %d in flight)' % (plan.session_cap, u5, in_flight))
    if plan.by and now >= plan.by:
        return dict(jobs=0, start=False, stop='the --by time passed at %g%% (cap %g%%)' % (u5, plan.session_cap),
                    wait_reset=False, target=plan.session_cap, note='')

    span = (dl or now + 3600) - plan.t0
    margin = min(MARGIN_MAX_S, MARGIN_FRAC * span)
    end = (dl or now + 3600) - margin
    frac = 1.0 if end <= plan.t0 else min(1.0, max(0.0, (now - plan.t0) / (end - plan.t0)))
    target = plan.u0 + (plan.session_cap - plan.u0) * frac
    planned_slope = (plan.session_cap - plan.u0) / max(end - plan.t0, 60)   # points per second

    # EMERGENCY: the window filling far faster than the plan, and above it.
    recent = [h for h in hist if now - h['t'] <= SLOPE_S and h['reset'] == reset]
    if len(recent) >= 2 and recent[-1]['t'] - recent[0]['t'] >= SLOPE_S / 2 and planned_slope > 0:
        slope = (recent[-1]['u5'] - recent[0]['u5']) / (recent[-1]['t'] - recent[0]['t'])
        if slope > EMERGENCY_X * planned_slope and u5 > target + BAND:
            return dict(jobs=0, start=False, wait_reset=False, target=target,
                        stop='EMERGENCY: filling at %.1f%%/h, %.1fx the plan (%.1f%%/h), %g%% against a line at %.0f%%'
                        % (slope * 3600, slope / planned_slope, planned_slope * 3600, u5, target), note='')

    gap = u5 - target
    note = 'on the line'
    if gap > BAND:
        if plan.jobs > 1:
            plan.jobs -= 1
            plan.last_change = now
            note = 'ahead by %.0f -- one fewer worker' % gap
        else:
            return dict(jobs=1, start=False, stop=None, wait_reset=False, target=target,
                        note='ahead by %.0f -- pausing' % gap)
    elif gap < -BAND and plan.jobs < plan.max_jobs and now - plan.last_change >= plan.ramp:
        plan.jobs += 1
        plan.last_change = now
        note = 'behind by %.0f -- one more worker' % -gap
    elif gap < -BAND:
        note = 'behind by %.0f' % -gap
    return dict(jobs=plan.jobs, start=True, stop=None, wait_reset=False, target=target, note=note)


def describe(plan, hist, now):
    """One line for a person: where the bars are, the line, and what a deadline needs."""
    if not hist:
        return 'no usage reading yet -- is the status line configured, and a session open?'
    last = hist[-1]
    age = now - last['t']
    dl = plan.deadline(last['reset'])
    s = '5h %g%%  7d %g%%  (reading %ds old%s)' % (last['u5'], last['u7'], age, ', STALE' if age > STALE_S else '')
    if dl and dl > now:
        need = (plan.session_cap - last['u5']) / ((dl - now) / 3600)
        s += '  -> %g%% by %s needs %.0f%%/h' % (plan.session_cap,
                                                dt.datetime.fromtimestamp(dl).strftime('%H:%M'), need)
        if need > plan.max_jobs * 16:
            s += ' (more than %d workers reach, ~%d%%/h)' % (plan.max_jobs, plan.max_jobs * 16)
    return s


def _test():
    """The rules on synthetic series. Each case states what must happen."""
    now = 1_000_000.0
    reset = now + 3 * 3600
    R = lambda t, u5, u7=30: dict(t=t, u5=u5, u7=u7, reset=reset)
    fails = []

    def case(name, cond):
        print('  %-55s %s' % (name, 'ok' if cond else 'FAIL'))
        if not cond:
            fails.append(name)

    p = Plan(session_cap=90, max_jobs=3)
    d = decide(p, [R(now - 10, 40)], now)
    case('first reading anchors the line; starts with one worker', d['jobs'] == 1 and d['start'])
    d = decide(p, [R(now - 10, 40), R(now + 3590, 40)], now + 3600)
    case('an hour in and still at 40%: behind -> adds a worker', d['jobs'] == 2)
    d = decide(p, [R(now + 3700, 40)], now + 3720)
    case('...but not a second one inside five minutes', d['jobs'] == 2)
    p2 = Plan(session_cap=90, max_jobs=3)
    decide(p2, [R(now - 10, 40)], now)
    d = decide(p2, [R(now + 590, 55)], now + 600)
    case('ahead of the line at one worker: pause', not d['start'] and not d['stop'])
    p3 = Plan(session_cap=90, max_jobs=3)
    decide(p3, [R(now - 10, 40)], now)
    spike = [R(now + 60, 40), R(now + 600, 48), R(now + 960, 60)]
    d = decide(p3, spike, now + 960)
    case('20 points in 15 minutes on a 3-hour plan: EMERGENCY stop', bool(d['stop']) and 'EMERGENCY' in d['stop'])
    p4 = Plan(session_cap=90)
    d = decide(p4, [R(now - 10, 89.6)], now, in_flight=2)
    case('at the cap counting in-flight: start nothing, wait for reset', not d['start'] and d['wait_reset'])
    p4b = Plan(session_cap=63)
    p4b.measured(0, 58); p4b.measured(79, 60)
    d = decide(p4b, [R(now - 10, 60)], now, in_flight=6)
    case('six cheap meetings in flight at 60%: MEASURED reserve, keep going', d['start'] and abs(p4b.per_meeting - 0.0253) < 0.001)
    p5 = Plan(session_cap=90, week_cap=80)
    d = decide(p5, [R(now - 10, 40, 80)], now)
    case('weekly cap reached: stop', bool(d['stop']) and 'weekly' in d['stop'])
    p6 = Plan()
    d = decide(p6, [R(now - 400, 40)], now)
    case('a reading over five minutes old: STALE, one worker', d['jobs'] == 1 and 'STALE' in d['note'])
    p7 = Plan(session_cap=60, by=now + 1800)
    decide(p7, [R(now - 10, 50)], now)
    d = decide(p7, [R(now + 1795, 55)], now + 1800)
    case('--by passed short of the cap: stop and say so', bool(d['stop']) and '--by' in d['stop'])
    p8 = Plan(session_cap=60, by=now + 1800)
    decide(p8, [R(now - 10, 50)], now)
    d = decide(p8, [R(now + 1000, 60)], now + 1000)
    case('cap reached before --by: stop, do not wait for a reset', bool(d['stop']) and not d['wait_reset'])
    p9 = Plan(session_cap=90)
    decide(p9, [R(now - 10, 40)], now)
    new = dict(t=now + 4 * 3600, u5=2, u7=35, reset=reset + 5 * 3600)
    d = decide(p9, [new], now + 4 * 3600 + 5)
    case('a new window re-anchors the line at its own start', p9.u0 == 2 and d['start'])
    print('%d of %d rules hold' % (12 - len(fails), 12))
    return 1 if fails else 0


if __name__ == '__main__':
    if '--test' in sys.argv:
        sys.exit(_test())
    print(describe(Plan(), readings(), dt.datetime.now().timestamp()))
