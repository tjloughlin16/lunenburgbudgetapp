#!/usr/bin/env python3
"""THE DAYS NOBODY LOOKED. A gap in the crawl becomes a gap in what can be said.

    python3 scripts/check_watch_gaps.py [--days 30] [--max-gap 1]

Exit 1 when the watcher has missed more consecutive days than `--max-gap` allows inside the
window, or when the most recent run is older than that.

WHY THIS EXISTS. TJ, 25 September 2026, on being told an agenda was `first seen` on the
morning of its meeting: *"Can you be sure we processed the agenda and would know if it was
posted wed or Thurs?"*

No. The watcher ran on the 23rd and the 25th and NOT on the 24th, so `first_seen` for that
document could mean Wednesday evening, Thursday, or Friday morning. It had also missed the
18th and the 22nd. The figure was quoted as though it were a posting time; it is a statement
about when this project last looked.

    A matcher that found nothing is a fact about the instrument.
    A day nobody crawled is a fact about us.

Neither is a fact about the town, and both read exactly like one. This is the same shape as
`search_minutes.py` printing its denominator on every run: a silence means nothing until you
know how hard somebody listened.

WHAT IT CANNOT DO. It cannot recover a missed day -- the AgendaCenter shows what is posted
now, not what was posted on a Thursday. A gap, once it has happened, is permanent, and the
only remedy is to notice it while the documents are still fresh enough to reason about. So
this reports rather than repairs, and it is the honest half of the pair with
`money-gaps.csv`, where the question it cannot answer is registered.
"""
import argparse
import csv
import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, 'sources', 'data', 'meeting-watch-runs.csv')


def days_run(window_start):
    if not os.path.exists(RUNS):
        return set()
    out = set()
    with open(RUNS, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            d = (r.get('ran') or '')[:10]
            try:
                day = dt.date.fromisoformat(d)
            except ValueError:
                continue
            if day >= window_start:
                out.add(day)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=30, help='how far back to look')
    ap.add_argument('--max-gap', type=int, default=1,
                    help='the most consecutive days the watcher may skip')
    ap.add_argument('--as-of', default=dt.date.today().isoformat())
    a = ap.parse_args()

    today = dt.date.fromisoformat(a.as_of)
    start = today - dt.timedelta(days=a.days - 1)
    ran = days_run(start)
    if not ran:
        print('no watcher run recorded in the last %d days. The crawl is not running at '
              'all, and every `first seen` is meaningless until it is.' % a.days)
        return 1

    missed = [start + dt.timedelta(days=i) for i in range(a.days)
              if (start + dt.timedelta(days=i)) not in ran
              and (start + dt.timedelta(days=i)) <= today]

    # THE LONGEST RUN OF MISSED DAYS IS THE MEASURE, not the total. Ten scattered single
    # days leave every document datable to within a day; one four-day gap makes four days of
    # postings indistinguishable. The second is what makes a `first seen` unusable.
    longest, run, worst_end = 0, 0, None
    prev = None
    for d in missed:
        run = run + 1 if prev and (d - prev).days == 1 else 1
        if run > longest:
            longest, worst_end = run, d
        prev = d
    last = max(ran)
    behind = (today - last).days

    print('watcher: %d of the last %d days crawled; last run %s (%d day%s ago)'
          % (len(ran), a.days, last, behind, '' if behind == 1 else 's'))
    if missed:
        print('  %d day(s) not crawled: %s%s'
              % (len(missed), ', '.join(str(d) for d in missed[:12]),
                 ' ...' if len(missed) > 12 else ''))
        print('  longest unbroken gap: %d day(s)%s'
              % (longest, ', ending %s' % worst_end if worst_end else ''))
        print('  Any document first seen after a gap could have been posted on any day in '
              'it. That is the width of the doubt on every `first_seen` in the window.')

    bad = longest > a.max_gap or behind > a.max_gap
    if bad:
        print('  !! more than %d consecutive day(s) missed. Run scripts/refresh.py, and '
              'treat `first_seen` in this window as no better than the gap.' % a.max_gap)
    else:
        print('ok: no gap longer than %d day(s); `first_seen` is good to within that.'
              % a.max_gap)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
