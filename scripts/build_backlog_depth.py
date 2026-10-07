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

  votes      ONE SET of the town's OFFICIAL minutes, processed              ~$0.09
  reconcile  ONE MEETING's two records, compared                            ~$0.32
  minutes    ONE RECORDING, OUR minutes written from it                     ~$0.37

THE STREAM CALLED `votes` IS THE TOWN'S OFFICIAL MINUTES. TJ, 28 September 2026: *"why are
you so focused on votes? We process OFFICIAL minutes and we create our own minutes. votes
is ONE PIECE of what the minutes have in them."* The stream is named after the extractor
that reads it today, which framed a document-processing backlog as a vote-counting one.
The key stays `votes` because that is the script; what a reader is shown is the document.

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
import glob
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

OUT = os.path.join(ROOT, 'notes', 'generated', 'BACKLOG-DEPTH.md')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'backlog-depth.json')
STREAMS = ('official', 'official-v1', 'reconcile', 'minutes')
# THE TWO OFFICIAL STREAMS ARE ONE READ IN TWO STATES (TJ, 6 October 2026): `official` is a
# set of the town's minutes never read; `official-v1` was read for votes only and waits to
# be re-read STRUCTURED (schema 2). Same command, same price, so they share a unit cost --
# measured from the structured reads, never from the old votes-only rows (`votes` in the
# ledger), which bought a smaller thing.
SHARED_COST = {'official-v1': 'official'}
LABEL = {'official': 'official, unread', 'official-v1': 'official, votes only',
         'reconcile': 'reconcile', 'minutes': 'our minutes'}
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
    for s, into in SHARED_COST.items():
        by[into] = by[into] + by.pop(s, [])
    out = {s: (sum(v) / len(v) if v else None) for s, v in by.items()}
    for s, into in SHARED_COST.items():
        out[s] = out.get(into)
    return out


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


# THE BOARDS A READER FILTERS THE CHART TO (TJ, 6 October 2026): the three budget boards,
# so the fiscal-year chart can show, per board, how much of each year is still open.
FILTER_BOARDS = [('select-board', 'Select Board'), ('school-committee', 'School Committee'),
                 ('finance-committee', 'Finance Committee')]


def processable_meetings():
    """Every (board, date) with a record there is work to do on: the town's minutes with
    readable text, or a recording on our-minutes' own list (open or already written). The
    denominator of `% still open` -- a meeting with only an agenda has nothing to process
    and would dilute it."""
    import extract_official_votes as E
    import refresh
    out = {(e['board_slug'], e['date']) for e in E.minutes_files()
           if len(E.norm(open(e['path'], encoding='utf-8', errors='replace').read())) >= E.MIN_CHARS}
    out |= {(t['board_slug'], t['meeting_date']) for t in refresh.minutes_targets(refresh.policy())}
    out |= {(p.split(os.sep)[-2], os.path.basename(p)[:10])
            for p in glob.glob(os.path.join(ROOT, 'sources', 'data', 'recording-minutes', '*', '*.json'))}
    return out


def by_board_fy(jobs):
    """Per fiscal year, for every board together and for each FILTER_BOARD: open jobs by
    stream, and MEETINGS -- how many have anything to process, how many are still open.
    `% open` is meetings over meetings, one unit; the streams are never added for it."""
    meetings = processable_meetings()
    open_m = {(j['board'], j['date']) for j in jobs}
    out = {}
    for key, keep in [('all', None)] + [(slug, slug) for slug, _ in FILTER_BOARDS]:
        rows = collections.defaultdict(lambda: collections.Counter())
        for j in jobs:
            if (keep is None or j['board'] == keep) and len(j['date']) >= 7:
                rows['FY%d' % fiscal_year(j['date'][:7])][j['stream']] += 1
        held = collections.Counter()
        still = collections.Counter()
        for b, d in meetings | open_m:
            if (keep is None or b == keep) and len(d) >= 7:
                fy = 'FY%d' % fiscal_year(d[:7])
                held[fy] += 1
                still[fy] += (b, d) in open_m
        out[key] = [dict(fy=fy, **{s: rows[fy][s] for s in STREAMS}, total=sum(rows[fy].values()),
                         meetings=held[fy], meetings_open=still[fy],
                         pct_open=round(100.0 * still[fy] / held[fy], 1) if held[fy] else 0.0)
                    for fy in sorted(held)]
    return out


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
        'grain': 'One row per MEETING still to process (a board on a date), placed by the '
                 'meeting’s own date — never the things inside it: one set of minutes may '
                 'hold eight votes or none. Streams are counted separately and must not be '
                 'added, being different pieces of work at different prices; the two '
                 'official streams are one structured read of the town’s minutes, split by '
                 'whether the minutes were ever read before (votes only) or never.',
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
        'by_board_fiscal_year': by_board_fy(jobs),
        'filter_boards': [dict(slug=s_, name=n_) for s_, n_ in FILTER_BOARDS],
        'not_established': [
            'When any of this will be done. The sweep runs in whatever allowance is left '
            'before the weekly reset, which varies.',
            'That a zero is an absence. `reconcile` cannot exist before the recordings do, '
            'so its zero before 2025 is the channel’s start date and not a gap.',
        ],
    }


def bar(n, hi, width=40):
    return '█' * max(1, round(width * n / hi)) if n else ''


def table(w, head, key, rows, hi, width=40):
    w('| %s | %s | total |%s' % (head, ' | '.join(LABEL[s] for s in STREAMS), ' |' if hi else ''))
    w('|---|%s---:|%s' % ('---:|' * len(STREAMS), '---|' if hi else ''))
    for r in rows:
        w('| %s | %s | **%d** |%s' % (r[key], ' | '.join('%d' % r[s] for s in STREAMS), r['total'],
                                       ' `%s` |' % bar(r['total'], hi, width) if hi else ''))


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
    w('| stream | one job is | meetings | $ each | $ total |')
    w('|---|---|---:|---:|---:|')
    # WHAT A JOB IS, NOT WHAT IT IS ABOUT. `votes` reads ONE FILE PER SET OF MINUTES, so
    # its count is sets of minutes and not votes -- a set may hold eight or none. Labelled
    # `the votes in the town's minutes` beside 3,041 it read as a count of votes, which is
    # the units failure rule 7b exists to stop.
    what = {'official': 'one meeting\u2019s OFFICIAL minutes, never read: read, structured',
            'official-v1': 'one meeting\u2019s OFFICIAL minutes, read for votes only: re-read, structured',
            'reconcile': 'one meeting\u2019s two records, compared',
            'minutes': 'one recording, OUR minutes written from it'}
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
        w('**THE MONEY ABOVE IS SHORT BY %s JOB(S).** %s carries no measured cost yet: '
          'nothing of that kind has been logged in `agentic-spend.csv`, the ledger the sweep '
          'writes. A dash is what an unmeasured cost looks like; the total is of the streams '
          'that have one, and it stops understating the first time one of these runs is logged.'
          % (f"{sum(x['jobs'] for x in unpriced):,}",
             ' and '.join('`%s`' % x['name'] for x in unpriced)))
    w('')
    w('## By calendar year of the meeting')
    w('')
    hi = max((r['total'] for r in pay['by_year']), default=1)
    table(w, 'year', 'year', pay['by_year'], hi)
    w('')
    w('## By fiscal year (July–June, as the town budgets)')
    w('')
    hi = max((r['total'] for r in pay['by_fiscal_year']), default=1)
    table(w, 'fiscal year', 'fy', pay['by_fiscal_year'], hi)
    w('')
    for slug, name in FILTER_BOARDS:
        rows = pay['by_board_fiscal_year'].get(slug, [])
        if not rows:
            continue
        w('## %s, by fiscal year' % name)
        w('')
        w('Open = meetings with anything still to process, of the meetings with a record to process.')
        w('')
        w('| fiscal year | meetings | still open | %% open | %s |' % ' | '.join(LABEL[s] for s in STREAMS))
        w('|---|---:|---:|---:|%s' % ('---:|' * len(STREAMS)))
        for r in rows:
            w('| %s | %d | %d | %.0f%% | %s |' % (r['fy'], r['meetings'], r['meetings_open'], r['pct_open'],
                                                ' | '.join('%d' % r[s] for s in STREAMS)))
        w('')
    w('## The last two years, month by month')
    w('')
    recent = [r for r in pay['by_month'] if r['month'] >= pay['by_month'][-1]['month'][:4]
              and True][-24:] if pay['by_month'] else []
    hi = max((r['total'] for r in recent), default=1)
    table(w, 'month', 'month', recent, hi, 30)
    w('')
    w('## By board')
    w('')
    table(w, 'board', 'board', pay['by_board'][:20], None)
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
