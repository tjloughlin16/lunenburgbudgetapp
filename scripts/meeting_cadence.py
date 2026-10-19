#!/usr/bin/env python3
"""WHEN A BOARD IS LIKELY TO MEET NEXT, inferred from when it has met -- and tested.

    python3 scripts/meeting_cadence.py --test          # the unit checks, synthetic histories
    python3 scripts/meeting_cadence.py --report        # every board: rule, backtest, estimate

TJ, 19 October 2026: *"we need to project/estimate the next meeting for the boards when
there's nothing officially posted. they are pretty structured/consistent in when they are
run, so we could show a LIKELY NEXT MEETING flag and guess when the next meeting will be."*

WHAT THIS IS (rule 7). A rhythm read off past dates is a HYPOTHESIS ABOUT THE FUTURE. Nobody
published it; the town posts a meeting 48 hours ahead and nothing before that. So every
output here is OUR ESTIMATE, and the page that shows it says so in the estimate colour
(rule 3). A board that has posted a future meeting shows that posting and never this.

HOW THE RULE IS READ. Three families of rule, each scored on the board's last year of
meetings before the moment of prediction:

  * nth weekday of the month -- any set of {1st, 2nd, 3rd, 4th, last} on one weekday
    ("1st and 3rd Tuesday", "last Thursday");
  * every N weeks on a weekday, N = 1..4, phase fitted to the recent meetings;
  * and both skip the months the board HABITUALLY does not meet -- read from history
    (a month met in at most a third of the board's active years, seen at least twice).

A meeting within two days of a rule date counts as that date (a holiday shift). The score is
the overlap between the dates the rule generates and the dates the board met (2*hits over
the sum of both), ties to the rule that generates fewer dates.

THE BACKTEST IS THE HONESTY MECHANISM, and nothing is shown without it. For every meeting the
board held in the year before the build date, the inference is run on the history up to and
including the meeting BEFORE it -- what we would have known the day after that one -- and its
next date is predicted. A prediction is EXACT when the board met on that date, and WITHIN A
WEEK when it met within seven days of it.

THE THRESHOLD IS OURS (rule 3 -- an assumption we chose, not a fact about the board):
an estimate is shown only when the backtest made at least MIN_PREDICTIONS predictions, at
least MIN_EXACT_SHARE of them were exact AND as many came within a week of the board's actual
next meeting, AND the board met recently -- its last meeting
within three of its rule's intervals, plus any habitual-gap months in between. Seventy per
cent is chosen because below it the estimate is wrong about as often as one time in three,
which is the point at which "likely" stops being an honest word for it.
"""
import argparse
import collections
import datetime as dt
import sys

D = dt.date
WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
          'September', 'October', 'November', 'December']
ORD = {1: '1st', 2: '2nd', 3: '3rd', 4: '4th', 5: 'last'}   # 5 means "last of the month"

TRAIN_DAYS = 365        # the history a rule is scored on
SHIFT_DAYS = 2          # a meeting this close to a rule date counts as it (holiday shift)
BACKTEST_DAYS = 365     # the replay covers meetings in the year before the build date
# OUR ASSUMPTIONS, stated: see the module docstring.
MIN_PREDICTIONS = 6
MIN_EXACT_SHARE = 0.70
RECENT_INTERVALS = 3
MIN_TRAIN_MEETINGS = 5  # fewer than this in the year and no rule is attempted


def _d(x):
    return x if isinstance(x, D) else D.fromisoformat(x)


def nth_of(day):
    """(n, is_last): which occurrence of its weekday this date is in its month."""
    n = (day.day - 1) // 7 + 1
    return n, (day + dt.timedelta(days=7)).month != day.month


# ------------------------------------------------------------------ habitual gap months

def gap_months(dates, cutoff):
    """Calendar months this board habitually does NOT meet, read off the up-to-three years
    before `cutoff`. A year-window counts as ACTIVE when the board met in at least six
    distinct months of it; a month is a gap when it was observed in two or more active
    windows, met in at most a third of them, and not met in the latest one. Fewer than two windows, no gaps: one
    quiet August is not a habit."""
    windows = []
    for k in range(3):
        hi = cutoff - dt.timedelta(days=365 * k)
        lo = hi - dt.timedelta(days=365)
        ds = [d for d in dates if lo < d <= hi]
        months = collections.Counter(d.month for d in ds)
        if len(months) >= 6:
            windows.append(months)
    if len(windows) < 2:
        return frozenset()
    gaps = set()
    for m in range(1, 13):
        met = sum(1 for w in windows if w.get(m))
        # ...and never a month the board met in during the latest year: a habit it has
        # just broken is not one to project.
        if met <= len(windows) / 3 and not windows[0].get(m):
            gaps.add(m)
    return frozenset(gaps)


# ------------------------------------------------------------------ rules

class Rule:
    """A candidate rhythm. `kind` is 'nth' (weekday + set of nths) or 'every' (N weeks)."""

    def __init__(self, kind, weekday, nths=None, weeks=None, phase=None, gaps=frozenset()):
        self.kind, self.weekday, self.nths, self.weeks, self.phase = kind, weekday, nths, weeks, phase
        self.gaps = gaps

    def matches(self, day):
        if day.weekday() != self.weekday or day.month in self.gaps:
            return False
        if self.kind == 'nth':
            n, last = nth_of(day)
            return n in self.nths or (5 in self.nths and last)
        return (day.toordinal() // 7) % self.weeks == self.phase

    def dates(self, lo, hi):
        """Every rule date with lo < date <= hi."""
        out, day = [], lo + dt.timedelta(days=1)
        while day <= hi:
            if self.matches(day):
                out.append(day)
            day += dt.timedelta(days=1)
        return out

    def next_after(self, day, count=1):
        out, d = [], day + dt.timedelta(days=1)
        for _ in range(800):
            if self.matches(d):
                out.append(d)
                if len(out) == count:
                    break
            d += dt.timedelta(days=1)
        return out

    def interval_days(self):
        if self.kind == 'every':
            return 7 * self.weeks
        return 30.0 / len(self.nths)

    def words(self):
        wd = WEEKDAYS[self.weekday]
        if self.kind == 'every':
            base = {1: 'every %s' % wd, 2: 'every other %s' % wd}.get(self.weeks, 'every %d weeks on a %s' % (self.weeks, wd))
        else:
            ns = [ORD[n] for n in sorted(self.nths)]
            if len(ns) == 4 and 5 not in self.nths:
                base = 'every %s but the 5th' % wd
            else:
                base = '%s %s of the month' % (' and '.join([', '.join(ns[:-1]), ns[-1]] if len(ns) > 1 else ns), wd)
        if self.gaps:
            base += ', not in %s' % _month_list(sorted(self.gaps))
        return base

    def key(self):
        return (self.kind, self.weekday, tuple(sorted(self.nths or ())), self.weeks, self.phase)


def _month_list(ms):
    names = [MONTHS[m - 1] for m in ms]
    return names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' or ' + names[-1]


def score(rule, actual, lo, hi):
    """(F, hits, expected): overlap of rule dates with actual meeting dates in (lo, hi],
    a meeting within SHIFT_DAYS of a rule date standing for it, each used once."""
    exp = rule.dates(lo, hi)
    if not exp:
        return 0.0, 0, 0
    left = sorted(actual)
    hits = 0.0
    for e in exp:
        best = None
        for a in left:
            if abs((a - e).days) <= SHIFT_DAYS and (best is None or abs((a - e).days) < abs((best - e).days)):
                best = a
        if best is not None:
            # A shifted meeting counts half: it is evidence of the rule, and also of an
            # extra meeting on a nearby day, which is common here and must not pull a
            # rule toward dates the board does not keep.
            hits += 1.0 if best == e else 0.5
            left.remove(best)
    return 2.0 * hits / (len(actual) + len(exp)), hits, len(exp)


def _subsets(items):
    items = list(items)
    for mask in range(1, 1 << len(items)):
        yield frozenset(items[i] for i in range(len(items)) if mask >> i & 1)


def infer(dates, cutoff):
    """The best rule for meetings up to and including `cutoff`, or None.

    Returns dict(rule, explained, of) -- `explained` meetings of the `of` in the training
    year that fell on a date the rule names."""
    dates = sorted({_d(x) for x in dates if _d(x) <= cutoff})
    lo = cutoff - dt.timedelta(days=TRAIN_DAYS)
    train = [d for d in dates if d > lo]
    if len(train) < MIN_TRAIN_MEETINGS:
        return None
    gaps = gap_months(dates, cutoff)
    wd_count = collections.Counter(d.weekday() for d in train)
    best = None
    for wd, n in wd_count.items():
        if n < 0.4 * len(train) and n < 3:
            continue
        cands = []
        # nth-weekday sets: only nths that actually occur, to keep the search small.
        seen = set()
        for d in train:
            if d.weekday() == wd:
                k, last = nth_of(d)
                seen.add(min(k, 4) if k < 5 else 5)
                if last:
                    seen.add(5)
        for s in _subsets(sorted(seen)):
            if 5 in s and 4 in s:
                continue   # "4th and last" is ambiguous in four-week months
            cands.append(Rule('nth', wd, nths=s, gaps=gaps))
        # every N weeks: phase from the board's most recent meetings on that weekday.
        recent = [d for d in train if d.weekday() == wd][-6:]
        for weeks in (1, 2, 3, 4):
            phases = collections.Counter((d.toordinal() // 7) % weeks for d in recent)
            if phases:
                cands.append(Rule('every', wd, weeks=weeks, phase=phases.most_common(1)[0][0], gaps=gaps))
        for r in cands:
            f, hits, exp = score(r, train, lo, cutoff)
            k = (f, -exp, r.kind == 'nth')
            if best is None or k > best[0]:
                best = (k, r, hits)
    if best is None or best[2] == 0:
        return None
    # `explained`: meetings that fell ON a rule date, not merely near one.
    return dict(rule=best[1], explained=sum(1 for d in train if best[1].matches(d)), of=len(train))


def backtest(dates, as_of):
    """Replay the inference over the year before `as_of`.

    After each meeting the board held in that year, the rule is inferred from the history
    up to and including that meeting and its next date is named -- what this page would
    have shown the day after. Two meetings in a row that would have named the same date
    (a Saturday site walk between two regular Wednesdays) are ONE forecast, counted once.

      made   distinct dates we would have named
      exact  of those, dates the board DID meet on
      week   of those, forecasts where the board's actual next meeting came within seven
             days of the named date -- the check that a rule is not skipping meetings
             (a "3rd Wednesday" rule for a board that meets on the 1st and 3rd would name
             real meeting dates and still miss every other meeting)

    `exact` is "met on that date", not "that was the very next meeting", on purpose: the
    page shows an estimate only while nothing is posted, and an extra meeting is posted
    48 hours ahead and replaces the estimate. What a reader relies on is whether the date
    named will be a meeting."""
    dates = sorted({_d(x) for x in dates if _d(x) <= as_of})
    held = set(dates)
    named = {}
    lo = as_of - dt.timedelta(days=BACKTEST_DAYS)
    for i in range(1, len(dates)):
        if dates[i] <= lo:
            continue
        prev = dates[i - 1]
        inf = infer(dates[:i], prev)
        if not inf:
            continue
        p = inf['rule'].next_after(prev)
        if p and p[0] <= as_of and p[0] not in named:
            named[p[0]] = dates[i]
    return dict(made=len(named), exact=sum(1 for p in named if p in held),
                week=sum(1 for p, nxt in named.items() if abs((nxt - p).days) <= 7))


def not_a_rhythm(slug):
    """A body whose meetings are called per matter, not kept on a calendar. A public
    hearing is noticed because an application or an article needs one; that it usually
    lands on the parent board's regular night says when the BOARD meets, not that a hearing
    is coming. Our judgement, stated here so it is findable."""
    return slug.endswith('-public-hearing') or slug.endswith('-appointing-committee')


def likely_next(dates, as_of, count=6):
    """Everything the page needs, or None when there is no history to read.

    `show` says whether the estimate clears OUR threshold. `dates` are the next `count`
    rule dates after `as_of`, so the page -- which judges past and future on the reader's
    clock -- can roll forward past a date that has gone by without a rebuild."""
    as_of = _d(as_of)
    hist = sorted({_d(x) for x in dates if _d(x) <= as_of})
    inf = infer(hist, as_of)
    bt = backtest(hist, as_of)
    out = dict(backtest=bt, as_of=as_of.isoformat(),
               threshold=dict(min_predictions=MIN_PREDICTIONS, min_exact_share=MIN_EXACT_SHARE))
    if not inf:
        quiet = not hist or (as_of - hist[-1]).days > TRAIN_DAYS / 2
        return dict(out, show=False, reason='has not met recently' if quiet else 'no regular pattern',
                    rule=None, dates=[], last_met=hist[-1].isoformat() if hist else None)
    r = inf['rule']
    nxt = [d.isoformat() for d in r.next_after(as_of, count)]
    last = hist[-1]
    # Recency: three intervals, plus every habitual-gap day between the last meeting and now.
    gap_days = sum(1 for k in range((as_of - last).days) if (last + dt.timedelta(days=k + 1)).month in r.gaps)
    recent = (as_of - last).days <= RECENT_INTERVALS * r.interval_days() + gap_days
    passes = (bt['made'] >= MIN_PREDICTIONS and bt['exact'] >= MIN_EXACT_SHARE * bt['made']
              and bt['week'] >= MIN_EXACT_SHARE * bt['made'])
    reason = None if (passes and recent) else (
        'has not met recently' if passes else
        'too few predictions to test' if bt['made'] < MIN_PREDICTIONS else
        'the pattern did not hold often enough')
    # `on_rule`: the board's most recent meetings that fell ON the rule -- for a caller that
    # wants the usual TIME of the rhythm's meetings rather than of whatever met last (a
    # Saturday site walk is not when the commission's Wednesday meeting starts).
    return dict(out, show=bool(passes and recent), reason=reason, rule=r.words(),
                weekday=WEEKDAYS[r.weekday], explained=inf['explained'], of=inf['of'],
                last_met=last.isoformat(), dates=nxt,
                on_rule=[d.isoformat() for d in hist if r.matches(d)][-10:])


# ------------------------------------------------------------------ tests

def _gen(rule, lo, hi, drop=(), extra=()):
    ds = [d for d in rule.dates(D.fromisoformat(lo), D.fromisoformat(hi)) if d.isoformat() not in drop]
    return sorted(ds + [D.fromisoformat(x) for x in extra])


def test():
    fails = 0

    def ok(cond, msg):
        nonlocal fails
        print(('ok    ' if cond else 'FAIL  ') + msg)
        fails += 0 if cond else 1

    # 1st and 3rd Tuesday, two years, a holiday shift and a cancelled one.
    r = Rule('nth', 1, nths=frozenset({1, 3}))
    h = _gen(r, '2024-09-30', '2026-10-10', drop={'2025-11-04'}, extra={'2025-12-17'})
    res = likely_next(h, '2026-10-10')
    ok(res['rule'] == '1st and 3rd Tuesday of the month', '1st & 3rd Tuesday read: %s' % res['rule'])
    ok(res['dates'][0] == '2026-10-20', 'next 1st/3rd Tuesday after 10 Oct 2026 is 20 Oct: %s' % res['dates'][0])
    ok(res['show'], 'shown, backtest %s' % res['backtest'])

    # Every other Monday.
    r = Rule('every', 0, weeks=2, phase=(D(2026, 10, 5).toordinal() // 7) % 2)
    h = _gen(r, '2024-10-01', '2026-10-06')
    res = likely_next(h, '2026-10-08')
    ok(res['rule'] == 'every other Monday', 'biweekly read: %s' % res['rule'])
    ok(res['dates'][0] == '2026-10-19', 'next is 19 Oct: %s' % res['dates'][0])
    ok(res['show'], 'shown, backtest %s' % res['backtest'])

    # 2nd Wednesday, July and August off -- must skip the summer.
    r = Rule('nth', 2, nths=frozenset({2}), gaps=frozenset({7, 8}))
    h = _gen(r, '2023-06-01', '2026-06-30')
    res = likely_next(h, '2026-06-20')
    ok('not in July or August' in (res['rule'] or ''), 'summer gap read: %s' % res['rule'])
    ok(res['dates'][0] == '2026-09-09', 'next after June skips to 9 Sep: %s' % res['dates'][0])
    res = likely_next(h, '2026-08-20')
    ok(res['show'], 'still shown in late August, the gap excused: %s' % res['reason'])

    # An irregular board: dates scattered with no rhythm. Must not be shown.
    import random
    rnd = random.Random(7)
    day, h = D(2024, 9, 1), []
    while day < D(2026, 10, 1):
        day += dt.timedelta(days=rnd.randint(5, 40))
        h.append(day)
    res = likely_next(h, '2026-10-10')
    ok(not res['show'], 'irregular board not shown: %s (backtest %s)' % (res['reason'], res['backtest']))

    # A regular board that has gone quiet: not shown.
    r = Rule('nth', 3, nths=frozenset({1}))
    h = _gen(r, '2024-01-01', '2025-12-31')
    res = likely_next(h, '2026-10-10')
    ok(not res['show'] and res['reason'] == 'has not met recently', 'dormant board not shown: %s' % res['reason'])

    print('%d failure(s)' % fails)
    return 1 if fails else 0


def report(as_of=None):
    import csv
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    as_of = as_of or D.today().isoformat()
    by = board_dates(csv.DictReader(open(os.path.join(root, 'sources', 'data', 'meeting-register.csv'), encoding='utf-8')))
    shown = 0
    for slug in sorted(by):
        if not_a_rhythm(slug):
            continue
        res = likely_next(by[slug], as_of)
        if res['backtest']['made'] == 0 and not res['rule']:
            continue
        bt = res['backtest']
        shown += res['show']
        print('%-48s %-46s %2d/%2d exact %2d wk  %s' % (slug[:48], (res['rule'] or '-')[:46], bt['exact'], bt['made'], bt['week'],
                                                     ('SHOW ' + res['dates'][0]) if res['show'] else res['reason'] or ''))
    print('%d shown' % shown)


def board_dates(rows):
    """{slug: [dates]} from meeting-register rows. A row whose agenda names a different
    body -- a sub-committee filed under its parent -- is not the board's own rhythm and is
    left out."""
    by = collections.defaultdict(set)
    for r in rows:
        if r.get('board_slug') and r.get('date') and not (r.get('body_as_printed') or '').strip():
            by[r['board_slug']].add(r['date'])
    return {k: sorted(v) for k, v in by.items()}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--test', action='store_true')
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--as-of')
    a = ap.parse_args()
    if a.test:
        sys.exit(test())
    report(a.as_of)
