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

THE SIGNAL is the endpoint /usage itself reads -- api.anthropic.com/api/oauth/usage, with
the token Claude Code keeps in the macOS keychain -- polled at most once a minute by fetch()
and appended to ~/.claude/usage-api-log.csv. It is the SERVER's figure, so it moves whether
or not any interactive session is active.

IT REPLACED THE STATUS LINE AFTER THE STATUS LINE FROZE. 7 October 2026: the status line's
rate_limits change only when the interactive session itself calls the model; idle, they sat
at "8%" for 48 minutes while a 6-worker run spent $51, and the session hit 100% at 17:50
against a 65%-by-20:30 plan. The status line refreshed every minute, so the frozen number
LOOKED fresh. A signal that can be stale while looking current is worse than none: the
governor now trusts only a reading it fetched itself, and the status line is display only. The bars are WHOLE PERCENTS, so
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

LOG = os.path.expanduser('~/.claude/usage-api-log.csv')   # written by fetch(), and only by it
URL = 'https://api.anthropic.com/api/oauth/usage'
FETCH_EVERY_S = 150      # the endpoint answers 429 when polled every minute (7 October, 22:40)
BACKOFF_S = 600          # after a refusal, ask nothing for this long
_BACKOFF = os.path.expanduser('~/.claude/usage-api-backoff')
STALE_S = 420            # a reading older than this is unknown, never current (> FETCH_EVERY_S x 2)
BAND = 2.0               # points either side of the line that count as "on it"
RAMP_S = 300             # at most one added worker per five minutes
SLOPE_S = 900            # the window the emergency slope is measured over
EMERGENCY_X = 2.0        # filling at more than this multiple of the planned slope
PER_MEETING_PCT = 0.2    # what one in-flight meeting adds to the five-hour bar -- the
                         # STARTING guess only; the run measures its own (Plan.per_meeting)
MARGIN_MAX_S = 600       # stop aiming this long before the deadline...
MARGIN_FRAC = 0.10       # ...or this fraction of a short horizon, whichever is smaller


def _token():
    """Claude Code's own OAuth access token, from the keychain. Never printed, never stored."""
    import json
    import subprocess
    raw = subprocess.run(['security', 'find-generic-password', '-s', 'Claude Code-credentials', '-w'],
                         capture_output=True, text=True, timeout=10).stdout.strip()
    return json.loads(raw)['claudeAiOauth']['accessToken']


def fetch(force=False):
    """Ask the server for the bars and append a row to LOG. At most once per FETCH_EVERY_S
    (the last row's age decides). Returns True on a fresh reading. Any failure -- an expired
    token, no network -- returns False and writes nothing, so the reading goes STALE and the
    governor drops to one worker: a reading it could not get is never guessed."""
    import json
    import urllib.request
    hist = readings()
    now = dt.datetime.now().timestamp()
    if hist and now - hist[-1]['t'] < (FETCH_EVERY_S if not force else 60):
        return True                      # even a forced fetch is at most once a minute
    if os.path.exists(_BACKOFF) and now - os.path.getmtime(_BACKOFF) < BACKOFF_S:
        return False                     # refused recently: ask nothing until the back-off ends
    try:
        req = urllib.request.Request(URL, headers={
            'Authorization': 'Bearer ' + _token(), 'anthropic-beta': 'oauth-2025-04-20',
            'Content-Type': 'application/json', 'User-Agent': 'claude-cli'})
        d = json.loads(urllib.request.urlopen(req, timeout=15).read())
        f5, f7 = d['five_hour'], d['seven_day']
        reset = dt.datetime.fromisoformat(f5['resets_at']).timestamp()
        new = not os.path.exists(LOG)
        with open(LOG, 'a', encoding='utf-8') as fh:
            if new:
                fh.write('at,five_hour,seven_day,five_hour_resets_at\n')
            fh.write('%s,%s,%s,%d\n' % (dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                                         f5['utilization'], f7['utilization'], reset))
        return True
    except Exception as e:                              # noqa: BLE001 -- any failure is "unknown"
        if getattr(e, 'code', None) == 429:
            open(_BACKOFF, 'w').write(str(now))
        return False


def readings(path=LOG):
    """Every reading fetch() recorded, oldest first: dicts with t (epoch), u5, u7, reset (epoch).
    The resets_at the server returns carries microseconds that drift between calls, so it is
    rounded to the minute -- otherwise every reading would look like a new window."""
    out = []
    if not os.path.exists(path):
        return out
    for r in csv.DictReader(open(path, encoding='utf-8')):
        try:
            rs = float(r.get('five_hour_resets_at') or 0)
            out.append(dict(t=dt.datetime.fromisoformat(r['at'].replace('Z', '+00:00')).timestamp(),
                            u5=float(r['five_hour']), u7=float(r['seven_day']),
                            reset=(round(rs / 60) * 60) if rs else None))
        except (ValueError, KeyError, TypeError):
            continue
    return sorted(out, key=lambda x: x['t'])


class Plan:
    """What the run is aiming at, and what it has decided so far."""

    def __init__(self, session_cap=95.0, week_cap=90.0, by=None, max_jobs=3, ramp=RAMP_S, caps=None):
        # ONE CAP PER WINDOW. TJ, 7 October 2026: "Run the session to 100% for the first
        # session, then up to 80% for the second." `caps` is that list; the last one repeats.
        self.caps = list(caps) if caps else [session_cap]
        self.windows_seen = 0
        session_cap = self.caps[0]
        self.session_cap, self.week_cap, self.by, self.max_jobs = session_cap, week_cap, by, max_jobs
        self.ramp = ramp                         # seconds between added workers
        self.t0 = self.u0 = self.window = None   # the line's start, re-anchored each window
        self.jobs = 1
        self.last_change = 0.0
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
    if plan.window and now > plan.window and (reset is None or reset == plan.window):
        # THE OLD WINDOW IS OVER and the next opens on first use. The latest reading still
        # carries the OLD window's figure until something calls the model -- 8 October 03:11 it
        # said 100% and the run stopped "at the 80% cap" of a window that was really at 0.
        reset, u5 = None, 0.0

    if u7 >= plan.week_cap:
        return dict(jobs=0, start=False, stop='weekly cap %g%% reached (%g%%)' % (plan.week_cap, u7),
                    wait_reset=False, target=None, note='')

    # A NEW WINDOW re-anchors the line where it starts.
    if plan.window != reset and not (reset is None and plan.window and now <= plan.window):
        if plan.window is not None:
            plan.windows_seen += 1
            plan.session_cap = plan.caps[min(plan.windows_seen, len(plan.caps) - 1)]
        plan.window, plan.t0, plan.u0 = reset, now, u5

    dl = plan.deadline(reset)
    if u5 + in_flight * plan.per_meeting >= plan.session_cap:
        past_by = plan.by and reset and plan.by <= reset
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
    # NOT TWITCHY. 7 October 22:28: one worker on $0.37 meetings, with the interactive session
    # busy too, moved the bar 6 -> 10 in five minutes, and a half-window slope on whole-percent
    # readings called that 2x the plan and stopped the run. At one worker, running ahead is the
    # PAUSE's job; the brake is for a runaway -- a sustained slope AND well over the line.
    if len(recent) >= 2 and recent[-1]['t'] - recent[0]['t'] >= SLOPE_S * 0.8 and planned_slope > 0:
        slope = (recent[-1]['u5'] - recent[0]['u5']) / (recent[-1]['t'] - recent[0]['t'])
        if slope > EMERGENCY_X * planned_slope and u5 > target + 3 * BAND:
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
    p3b = Plan(session_cap=100, max_jobs=6)
    decide(p3b, [R(now - 10, 6)], now)
    blip = [R(now + 60, 6), R(now + 300, 10)]
    d = decide(p3b, blip, now + 320)
    case('6 -> 10 in five minutes at one worker: pause, NOT an emergency', not d['stop'])
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
    d = decide(p6, [R(now - STALE_S - 60, 40)], now)
    case('a reading older than STALE_S: STALE, one worker', d['jobs'] == 1 and 'STALE' in d['note'])
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
    p10 = Plan(caps=[100, 80])
    decide(p10, [R(now - 10, 3)], now)
    first = p10.session_cap
    decide(p10, [dict(t=now + 5 * 3600, u5=0, u7=50, reset=reset + 5 * 3600)], now + 5 * 3600 + 5)
    case('caps 100,80: the second window aims at 80', first == 100 and p10.session_cap == 80)
    p11 = Plan(caps=[100, 80], by=now + 8 * 3600)
    decide(p11, [R(now - 10, 99)], now)
    after = now + 3 * 3600 + 60                       # past the first window's reset
    d = decide(p11, [dict(t=after - 30, u5=100, u7=49, reset=reset)], after)
    case('after the reset, a reading still at the OLD 100%: start the new window at 0', d['start'] and not d['stop'])
    print('%d of %d rules hold' % (15 - len(fails), 15))
    return 1 if fails else 0


if __name__ == '__main__':
    if '--test' in sys.argv:
        sys.exit(_test())
    ok = fetch(force=True)
    print(('' if ok else 'COULD NOT FETCH -- ') + describe(Plan(), readings(), dt.datetime.now().timestamp()))
