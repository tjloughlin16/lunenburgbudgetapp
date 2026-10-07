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

MISSING RECORDS ARE NOT BACKLOG -- a fourth thing on the same chart, never summed into it.
TJ, 7 October 2026: *"update the backlog dash to have a different category on the FY bars
for MISSING information... if we clear all work, i want to still visualize on this chart
the ones that are missing and not yet available."* A job is work our pipeline can still do;
a missing record is the town never having published the minutes, never having recorded the
meeting, or the recording having no transcript -- there is no command to run that produces
one. Conflating the two would make a fully-worked year that the town simply never recorded
look identical to a year nobody has touched, so they are counted, coloured and labelled
separately everywhere this payload is read. Read straight from `meeting-register.csv`
(rows with `part_of` set skipped -- that meeting's record lives under another board's row):

  missing_minutes      minutes != '1'                        the town published none
  missing_video        the board records, this date is on/   no recording exists for a
                        after its first dated recording,      board that otherwise has one
                        and video != '1'
  missing_transcript   video == '1' and transcript != '1'     captions disabled, or not
                                                               yet fetched (`captions_disabled`
                                                               carried as a sub-count)

Verified against the file before trusting them (rule 13c): `minutes`, `video`, `transcript`
and `captions_disabled` are each only ever `'0'` or `'1'` across all 7,057 rows, checked
6 October 2026.
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
MISSING_STREAMS = ('missing_minutes', 'missing_video', 'missing_transcript')
MISSING_LABEL = {'missing_minutes': 'no town minutes', 'missing_video': 'no recording',
                 'missing_transcript': 'no transcript'}
REGISTER = os.path.join(ROOT, 'sources', 'data', 'meeting-register.csv')
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
    `% open` is meetings over meetings, one unit; the streams are never added for it.

    NEEDS-REVIEW MEETINGS ARE PULLED OUT ENTIRELY, not added as a fourth stream. TJ, 7
    October 2026: a meeting with an OPEN row in `review-queue.csv` is "pulled out of the
    normal flow of processing so they can't back anything up" -- so it is work for a
    person, never in the machine job totals, the cost, or `% open`, the same way a
    missing record is never counted as backlog. `review_queue.open_keys()` is the one
    function that decides this, imported by process_meeting.py too, so the two can never
    disagree about which meetings are held."""
    import review_queue as Q
    review_keys = {k for k in Q.open_keys() if len(k[1]) >= 7}
    meetings = processable_meetings()
    jobs = [j for j in jobs if (j['board'], j['date']) not in review_keys]
    open_m = {(j['board'], j['date']) for j in jobs}
    out = {}
    for key, keep in [('all', None)] + [(slug, slug) for slug, _ in FILTER_BOARDS]:
        rows = collections.defaultdict(lambda: collections.Counter())
        for j in jobs:
            if (keep is None or j['board'] == keep) and len(j['date']) >= 7:
                rows['FY%d' % fiscal_year(j['date'][:7])][j['stream']] += 1
        held = collections.Counter()
        still = collections.Counter()
        review = collections.Counter()
        for b, d in meetings | open_m:
            if (b, d) in review_keys:
                continue
            if (keep is None or b == keep) and len(d) >= 7:
                fy = 'FY%d' % fiscal_year(d[:7])
                held[fy] += 1
                still[fy] += (b, d) in open_m
        for b, d in review_keys:
            if keep is None or b == keep:
                review['FY%d' % fiscal_year(d[:7])] += 1
        out[key] = [dict(fy=fy, **{s: rows[fy][s] for s in STREAMS}, total=sum(rows[fy].values()),
                         meetings=held[fy], meetings_open=still[fy],
                         pct_open=round(100.0 * still[fy] / held[fy], 1) if held[fy] else 0.0,
                         needs_review=review[fy])
                    for fy in sorted(set(held) | set(review))]
    return out


def missing_records():
    """Every (board, date) meeting still missing a record the town or our own pipeline is
    expected to produce -- not work, an absence. Read straight off `meeting-register.csv`,
    never off `jobs()`: a job is something a command can still do, and there is no command
    that produces a transcript the town never recorded."""
    rows = [r for r in csv.DictReader(open(REGISTER, encoding='utf-8')) if not r.get('part_of')]
    first_video = {}
    for r in rows:
        d = r.get('date', '')
        if r.get('video') == '1' and len(d) >= 7:
            b = r['board_slug']
            if b not in first_video or d < first_video[b]:
                first_video[b] = d
    out = []
    for r in rows:
        d = r.get('date', '')
        if len(d) < 7:
            continue
        b = r['board_slug']
        mm = r.get('minutes') != '1'
        mv = b in first_video and d >= first_video[b] and r.get('video') != '1'
        mt = r.get('video') == '1' and r.get('transcript') != '1'
        if mm or mv or mt:
            out.append(dict(board=b, date=d, missing_minutes=mm, missing_video=mv,
                             missing_transcript=mt,
                             captions_disabled=mt and r.get('captions_disabled') == '1'))
    return out


def missing_by_fy(missing):
    """`missing_records()` rolled up by fiscal year, for 'all' and each FILTER_BOARD --
    the same key shape `by_board_fy` uses, so the two merge row for row."""
    out = {}
    for key, keep in [('all', None)] + [(slug, slug) for slug, _ in FILTER_BOARDS]:
        rows = collections.defaultdict(collections.Counter)
        for m in missing:
            if keep is None or m['board'] == keep:
                fy = 'FY%d' % fiscal_year(m['date'][:7])
                for s in MISSING_STREAMS:
                    if m[s]:
                        rows[fy][s] += 1
                if m['captions_disabled']:
                    rows[fy]['captions_disabled'] += 1
        out[key] = rows
    return out


def _with_missing(rows, counts_by_fy, zero):
    """`rows` (a list of per-fiscal-year dicts, each already holding `fy`) with the three
    missing-record columns merged in. A fiscal year present only in `counts_by_fy` -- every
    job cleared, something still missing -- gets a new row rather than being dropped,
    which is the whole point TJ asked for: the bar must still show."""
    idx = {r['fy']: dict(r) for r in rows}
    for fy in counts_by_fy:
        if fy not in idx:
            idx[fy] = dict(fy=fy, **zero)
    for fy, base in idx.items():
        c = counts_by_fy.get(fy, collections.Counter())
        for s in MISSING_STREAMS:
            base[s] = c.get(s, 0)
        base['captions_disabled'] = c.get('captions_disabled', 0)
    return [idx[fy] for fy in sorted(idx)]


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
    missing = missing_records()
    missing_fy = missing_by_fy(missing)
    missing_tot = collections.Counter()
    for m in missing:
        for s in MISSING_STREAMS:
            if m[s]:
                missing_tot[s] += 1
        if m['captions_disabled']:
            missing_tot['captions_disabled'] += 1
    fy_zero = dict(**{s: 0 for s in STREAMS}, total=0)
    board_fy_zero = dict(**{s: 0 for s in STREAMS}, total=0, meetings=0, meetings_open=0, pct_open=0.0,
                         needs_review=0)
    byfy_all = _with_missing(
        [dict(fy=f, **{s: by_fy[f][s] for s in STREAMS}, total=sum(by_fy[f].values())) for f in sorted(by_fy)],
        missing_fy['all'], fy_zero)
    byfy_board = by_board_fy(jobs)
    byfy_board = {k: _with_missing(rows, missing_fy.get(k, {}), board_fy_zero) for k, rows in byfy_board.items()}
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
        # MISSING RECORDS ARE NOT JOBS. Counted and totalled here the same way the job
        # streams are, but never folded into `total_jobs`, `estimated_usd` or `pct_open` --
        # there is no command that fixes an absence, so it is not backlog.
        'missing_streams': [{'name': s, 'label': MISSING_LABEL[s], 'meetings': missing_tot[s]}
                            for s in MISSING_STREAMS],
        'missing_meetings': len(missing),
        'missing_captions_disabled': missing_tot['captions_disabled'],
        'total_jobs': len(jobs),
        'estimated_usd': round(sum(est.values()), 2),
        'estimated_weeks': round(sum(est.values()) / 500.0, 2),
        'by_year': [dict(year=y, **{s: by_year[y][s] for s in STREAMS},
                         total=sum(by_year[y].values()))
                    for y in sorted(by_year)],
        'by_fiscal_year': byfy_all,
        'by_month': [dict(month=m, **{s: by_month[m][s] for s in STREAMS},
                          total=sum(by_month[m].values()))
                     for m in sorted(by_month)],
        'by_board': [dict(board=b, **{s: by_board[b][s] for s in STREAMS},
                          total=sum(by_board[b].values()))
                     for b in sorted(by_board, key=lambda k: -sum(by_board[k].values()))],
        'by_board_fiscal_year': byfy_board,
        'filter_boards': [dict(slug=s_, name=n_) for s_, n_ in FILTER_BOARDS],
        'not_established': [
            'When any of this will be done. The sweep runs in whatever allowance is left '
            'before the weekly reset, which varies.',
            'That a zero is an absence. `reconcile` cannot exist before the recordings do, '
            'so its zero before 2025 is the channel’s start date and not a gap.',
            'Whether a missing recording is a technical failure or a board that stopped '
            'recording for good. `missing_video` only asks whether the date is on or after '
            'the board’s own first dated recording, never whether the board still records '
            'today, so a board that recorded once years ago and never again shows every '
            'later meeting as missing rather than as a policy change.',
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


def missing_table(w, rows):
    """Fiscal years with at least one missing record -- a separate table from the job
    counts above it, never a shared total, because a missing record is not backlog."""
    show = [r for r in rows if any(r.get(s) for s in MISSING_STREAMS)]
    if not show:
        w('Nothing missing.')
        return
    w('| fiscal year | %s | missing total |' % ' | '.join(MISSING_LABEL[s] for s in MISSING_STREAMS))
    w('|---|%s---:|' % ('---:|' * len(MISSING_STREAMS)))
    for r in show:
        tot = sum(r.get(s, 0) for s in MISSING_STREAMS)
        w('| %s | %s | **%d** |' % (r['fy'], ' | '.join('%d' % r.get(s, 0) for s in MISSING_STREAMS), tot))


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
    w('**%s meeting(s) are missing a record outright and are not counted above: %s.** Not '
      'backlog -- there is no command that produces a transcript the town never recorded.'
      % (f"{pay['missing_meetings']:,}",
         ', '.join('%s %s' % (f"{m['meetings']:,}", m['label']) for m in pay['missing_streams']))
      + (' Of the missing transcripts, %s have captions disabled rather than unfetched.'
         % f"{pay['missing_captions_disabled']:,}" if pay['missing_captions_disabled'] else ''))
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
    w('### Missing records, by fiscal year -- not backlog')
    w('')
    w('The town never published minutes, never recorded the meeting, or the recording has '
      'no transcript. A fiscal year can appear here with every job above cleared.')
    w('')
    missing_table(w, pay['by_fiscal_year'])
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
        w('**Missing records (not backlog):**')
        w('')
        missing_table(w, rows)
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
