#!/usr/bin/env python3
"""HOW DEEP THE BACKLOG IS, BY THE MEETING'S OWN DATE -- not by when we found it.

    python3 scripts/build_backlog_depth.py            # write the note and the payload
    python3 scripts/build_backlog_depth.py --check    # fail if either is stale

TJ, 28 September 2026: *"i want a visualization in the backlog that shows all the documents
in the backlog and their MEETING DATE (NOT discover date) as a count. so i can see how deep
the backlog is based on month+year, or a rollup per year, and the type. For instance, I
could see that we have official minutes piling up for FY23 as an example. But I could also
see if we haven't processed a lot of recent materials."*

WHY THE MEETING DATE AND NOT THE DISCOVERY DATE. They answer different questions and both
are real. `first_seen` in `meeting-watch-state.csv` is when OUR crawler found a document,
and it is the right key for deciding what is NEW -- a 2024 meeting whose minutes the town
published last week is new work however old the meeting. But it is the wrong key for
asking how deep the hole is: discovery dates cluster on the days we happened to crawl, so
a chart of them shows our crawling schedule rather than the town's record. The meeting date
is the town's own, it does not move, and a pile at FY2023 means something about FY2023.

WHAT COUNTS AS BACKLOG. Not a second definition: `sweep_backlog.py` already decides what
work is outstanding across all three streams, and this reads `jobs()` rather than restating
the test. If the sweeper would run it, it is in the backlog here. A number that disagreed
with the queue that drains it would be worse than no number.

THE THREE STREAMS ARE NOT INTERCHANGEABLE and the chart must not add them:

  votes      ONE SET of the town's minutes, read for the votes in it        ~$0.09
  reconcile  ONE MEETING where we hold both records, compared               ~$0.32
  minutes    ONE RECORDING, minutes written from its captions               ~$0.37

EVERY COUNT HERE IS DOCUMENTS TO PROCESS, NEVER THE THINGS INSIDE THEM. A set of minutes
may hold eight votes or none, so `votes 3,041` is three thousand SETS OF MINUTES still to
read and not three thousand votes. Labelled `the votes in the town's minutes` beside that
figure it read as a count of votes, which is the units failure rule 7b exists to stop --
ten children, ten documents and ten budget lines must not look alike.

`reconcile` can only ever exist where a RECORDING exists, so it is empty before 2025 by
construction rather than by neglect -- the channel does not go back further. Reading its
zero for 2019 as a gap would be reading our instrument again.
"""
import argparse
import collections
import csv
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

OUT = os.path.join(ROOT, 'notes', 'generated', 'BACKLOG-DEPTH.md')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'backlog-depth.json')
STREAMS = ('votes', 'reconcile', 'minutes')
# What one job of each stream costs, measured from sources/data/agentic-spend.csv rather
# than assumed, so a quote in weeks of allowance is derived like everything else.
SPEND = os.path.join(ROOT, 'sources', 'data', 'agentic-spend.csv')


def unit_costs():
    """Mean cost per job per stream, from what was actually spent."""
    by = collections.defaultdict(list)
    if os.path.exists(SPEND):
        for r in csv.DictReader(open(SPEND, encoding='utf-8')):
            try:
                c = float(r.get('cost_usd') or '')
            except ValueError:
                continue
            if c > 0:
                by[r.get('stream', '')].append(c)
    return {s: (sum(v) / len(v) if v else None) for s, v in by.items()}


def gather():
    import sweep_backlog as S
    jobs = S.jobs()
    by_year = collections.defaultdict(lambda: collections.Counter())
    by_month = collections.defaultdict(lambda: collections.Counter())
    by_board = collections.defaultdict(lambda: collections.Counter())
    for j in jobs:
        d, s = j['date'], j['stream']
        if len(d) < 7:
            continue
        by_year[d[:4]][s] += 1
        by_month[d[:7]][s] += 1
        by_board[j['board']][s] += 1
    return jobs, by_year, by_month, by_board


def fiscal_year(ym):
    """Massachusetts FY: July starts the next one. FY2023 is Jul 2022 - Jun 2023."""
    y, m = int(ym[:4]), int(ym[5:7])
    return y + 1 if m >= 7 else y


def payload(jobs, by_year, by_month, by_board, costs):
    tot = collections.Counter(j['stream'] for j in jobs)
    by_fy = collections.defaultdict(lambda: collections.Counter())
    for ym, c in by_month.items():
        for s, n in c.items():
            by_fy['FY%d' % fiscal_year(ym)][s] += n
    est = {s: (costs.get(s) or 0) * tot[s] for s in STREAMS}
    return {
        'id': 'backlog-depth',
        'title': 'How deep the backlog is',
        'grain': 'One row per DOCUMENT still to process, placed by the MEETING’s own '
                 'date — never the things inside it: one set of minutes may hold eight '
                 'votes or none, so this counts sets of minutes and not votes. Streams are '
                 'counted separately and must not be added, being three different pieces '
                 'of work at three different prices.',
        'streams': [{'name': s, 'jobs': tot[s],
                     'unit_cost': round(costs[s], 3) if costs.get(s) else None,
                     'estimated_usd': round(est[s], 2) if costs.get(s) else None}
                    for s in STREAMS],
        'total_jobs': len(jobs),
        'estimated_usd': round(sum(est.values()), 2),
        'estimated_weeks': round(sum(est.values()) / 500.0, 2),
        'by_year': [dict(year=y, **{s: by_year[y][s] for s in STREAMS},
                         total=sum(by_year[y].values()))
                    for y in sorted(by_year)],
        'by_fiscal_year': [dict(fy=f, **{s: by_fy[f][s] for s in STREAMS},
                                total=sum(by_fy[f].values()))
                           for f in sorted(by_fy)],
        'by_month': [dict(month=m, **{s: by_month[m][s] for s in STREAMS},
                          total=sum(by_month[m].values()))
                     for m in sorted(by_month)],
        'by_board': [dict(board=b, **{s: by_board[b][s] for s in STREAMS},
                          total=sum(by_board[b].values()))
                     for b in sorted(by_board, key=lambda k: -sum(by_board[k].values()))],
        'not_established': [
            'When any of this will be done. The sweep runs in whatever allowance is left '
            'before the weekly reset, which varies.',
            'That a zero is an absence. `reconcile` cannot exist before the recordings do, '
            'so its zero before 2025 is the channel’s start date and not a gap.',
        ],
    }


def bar(n, hi, width=40):
    return '█' * max(1, round(width * n / hi)) if n else ''


def render(pay):
    L = []
    w = L.append
    w('# How deep the backlog is')
    w('')
    w('**Generated by `scripts/build_backlog_depth.py`. Do not edit.**')
    w('')
    w('Every outstanding machine-reading job, placed by the **meeting’s own date** — '
      'not by when we discovered it. %s jobs, about $%s, roughly %s of a week’s '
      'allowance.' % (f"{pay['total_jobs']:,}", f"{pay['estimated_usd']:,.0f}",
                      f"{pay['estimated_weeks']:.1f}"))
    w('')
    w('| stream | one job is | documents | $ each | $ total |')
    w('|---|---|---:|---:|---:|')
    # WHAT A JOB IS, NOT WHAT IT IS ABOUT. `votes` reads ONE FILE PER SET OF MINUTES, so
    # its count is sets of minutes and not votes -- a set may hold eight or none. Labelled
    # `the votes in the town's minutes` beside 3,041 it read as a count of votes, which is
    # the units failure rule 7b exists to stop.
    what = {'votes': 'one set of the town\u2019s minutes, read for the votes in it',
            'reconcile': 'one meeting where we hold both records, compared',
            'minutes': 'one recording, minutes written from its captions'}
    for s in pay['streams']:
        w('| `%s` | %s | %s | %s | %s |'
          % (s['name'], what.get(s['name'], ''), f"{s['jobs']:,}",
             ('$%.2f' % s['unit_cost']) if s['unit_cost'] else '—',
             ('$%s' % f"{s['estimated_usd']:,.0f}") if s['estimated_usd'] else '—'))
    w('')
    w('**The streams are not interchangeable and must not be added into one bar.** '
      '`reconcile` can only exist where a recording exists, so its zero before 2025 is '
      'the channel’s start date, not neglect.')
    unpriced = [x for x in pay['streams'] if not x['unit_cost']]
    if unpriced:
        w('')
        w('**THE MONEY ABOVE IS SHORT BY %s JOB(S).** %s carries no measured cost, '
          'because `agentic-spend.csv` is written by `sweep_backlog.py` and that stream '
          'has only just been added \u2014 until today the daily refresh was the only '
          'thing that ran it, and the refresh does not price into that ledger. A dash is '
          'what an unmeasured cost looks like; the total is of the streams that have one, '
          'and it stops understating the first time the sweeper runs.'
          % (f"{sum(x['jobs'] for x in unpriced):,}",
             ' and '.join('`%s`' % x['name'] for x in unpriced)))
    w('')
    w('## By calendar year of the meeting')
    w('')
    hi = max((r['total'] for r in pay['by_year']), default=1)
    w('| year | votes | reconcile | minutes | total | |')
    w('|---|---:|---:|---:|---:|---|')
    for r in pay['by_year']:
        w('| %s | %d | %d | %d | **%d** | `%s` |'
          % (r['year'], r['votes'], r['reconcile'], r['minutes'], r['total'],
             bar(r['total'], hi)))
    w('')
    w('## By fiscal year (July–June, as the town budgets)')
    w('')
    hi = max((r['total'] for r in pay['by_fiscal_year']), default=1)
    w('| fiscal year | votes | reconcile | minutes | total | |')
    w('|---|---:|---:|---:|---:|---|')
    for r in pay['by_fiscal_year']:
        w('| %s | %d | %d | %d | **%d** | `%s` |'
          % (r['fy'], r['votes'], r['reconcile'], r['minutes'], r['total'],
             bar(r['total'], hi)))
    w('')
    w('## The last two years, month by month')
    w('')
    recent = [r for r in pay['by_month'] if r['month'] >= pay['by_month'][-1]['month'][:4]
              and True][-24:] if pay['by_month'] else []
    hi = max((r['total'] for r in recent), default=1)
    w('| month | votes | reconcile | minutes | total | |')
    w('|---|---:|---:|---:|---:|---|')
    for r in recent:
        w('| %s | %d | %d | %d | **%d** | `%s` |'
          % (r['month'], r['votes'], r['reconcile'], r['minutes'], r['total'],
             bar(r['total'], hi, 30)))
    w('')
    w('## By board')
    w('')
    w('| board | votes | reconcile | minutes | total |')
    w('|---|---:|---:|---:|---:|')
    for r in pay['by_board'][:20]:
        w('| %s | %d | %d | %d | **%d** |'
          % (r['board'], r['votes'], r['reconcile'], r['minutes'], r['total']))
    w('')
    w('## What this does not say')
    w('')
    for n in pay['not_established']:
        w('- %s' % n)
    w('')
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    jobs, by_year, by_month, by_board = gather()
    pay = payload(jobs, by_year, by_month, by_board, unit_costs())
    doc = render(pay)
    js = json.dumps(pay, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
    if a.check:
        rc = 0
        for path, want in ((OUT, doc), (PAYLOAD, js)):
            cur = open(path, encoding='utf-8').read() if os.path.exists(path) else ''
            if cur != want:
                print('STALE %s' % os.path.relpath(path, ROOT))
                rc = 1
        return rc
    os.makedirs(os.path.dirname(PAYLOAD), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(doc)
    open(PAYLOAD, 'w', encoding='utf-8').write(js)
    print('wrote %s and %s' % (os.path.relpath(OUT, ROOT), os.path.relpath(PAYLOAD, ROOT)))
    print('  %s job(s): %s' % (f"{pay['total_jobs']:,}",
                               ', '.join('%s %s' % (f"{s['jobs']:,}", s['name'])
                                         for s in pay['streams'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
