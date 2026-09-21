"""The plan: which of the annual-report backlog gets done, in what batches, and when.

    python3 scripts/build_ingest_plan.py
    python3 scripts/build_ingest_plan.py --check

Writes `sources/data/ingest-plan.csv`, in the order the work is to be done.

TJ: *"We need to create a plan (a separate 'thing' on the ingestion page backlog) of which
of these backlog items will be done, and when, as 'batches'. In order to optimize token
spend and delivery time."*

THE ECONOMICS, BECAUSE THEY DECIDE THE BATCHES.

The expensive thing here is not running an extractor, it is WRITING one. Running is local
Python over files already on disk and costs nothing; writing one costs a working session,
and that cost is per TABLE FAMILY rather than per page. Forty-eight pages of special
revenue funds are one job, not forty-eight — they are the same table printed twelve times.

So a batch is a table family, and the sequence is value per extractor written. That is why
`special-revenue` outranks `receivables` despite both being large, and why the tail is one
batch rather than six: six small families sharing one pass is cheaper than six passes.

TWO KINDS OF WORK THAT ARE NOT AUTHORING, and they are scheduled differently:

  re-OCR   compute, not thought. It costs ~25 minutes a report and no allowance at all,
           and it needs nobody watching. It belongs in the background BESIDE an authoring
           batch, never in front of one — the whole point is the overlap.
  triage   looking at pages nobody has classified. Cheap, and it is scheduled EARLY
           despite delivering nothing itself, because 73 unclassified pages may contain
           the next `special-revenue` and no plan built without opening them is honest.

WHAT `delivers` IS FOR. Every batch names what a reader gets when it lands -- a registered
gap closed, a series completed, a page that becomes possible. A batch that cannot name one
is a batch that should be argued with before it is scheduled.

The page counts are DERIVED from `annual-report-pages.csv` on every run, so a plan cannot
quietly disagree with the queue it is a plan for. The batching, the order and the estimates
are judgements, written here to be argued with.
"""
import argparse
import collections
import csv
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(ROOT, 'sources', 'data', 'annual-report-pages.csv')
OUT = os.path.join(ROOT, 'sources', 'data', 'ingest-plan.csv')

FIELDS = ['seq', 'batch', 'channel', 'kind', 'subjects', 'items', 'years',
          'runs_beside', 'effort', 'cost', 'status', 'delivers']

# THE THREE CHANNELS, because they are limited by completely different things and a plan
# that mixes them cannot be scheduled.
#
#   session     I write an extractor. Limited by MY time; costs nothing to run afterwards.
#   refresh     a claude -p run per item, dripped by the daily refresh at its own caps
#               (MAX_MINUTES_PER_RUN = 3, MAX_OFFICIAL_VOTES_PER_RUN = 40). Limited by
#               the PLAN ALLOWANCE, and the only thing here that spends it.
#   background  local compute -- OCR, fetching. Limited by wall clock and by nothing else,
#               so it always runs beside something rather than in front of it.
#
# The allowance figures are the measured ones in CLAUDE.md: a minutes run is about 0.09%
# of a week and a votes run about 0.03%, on a plan that buys roughly 100% a week.
RATE = {'recording-minutes': (3, 0.09), 'official-votes': (40, 0.03)}


def drip(n, per_day, pct_each):
    """How long a dripped stream takes, and what it costs, at the refresh's own cap."""
    days = -(-n // per_day)
    return ('%s runs at %d a day' % ('{:,}'.format(n), per_day),
            '%.0f%% of a week in total, ~%.1f%% a day' % (n * pct_each, per_day * pct_each),
            days)

# seq, batch, channel, kind, subjects, effort, cost, what lands when it does.
#
# `effort` is in SESSIONS for the authoring work, measured against the two extractors
# written on 21 September: Treasurer's Cash and the Trust Fund Balance listing were about
# one session each, including the arguing with the page that is most of the work.
PLAN = [
    (1, 'Finish trust and stabilization', 'session', 'extractor',
     ['trust-and-stabilization'], '1 session', 'free',
     'The general Stabilization Fund in every year it is still missing from '
     '/analysis/stabilization-funds. The thread is already open and the readers exist; '
     'this closes it rather than leaving it at nine years of twelve.'),
    (2, 'Re-OCR the pages that came out upside down', 'background', 're-OCR',
     ['__reversed__'], '2 hours of compute', 'free, unattended',
     'Pages on which no extractor can currently see a figure at all. Detect the reversal, '
     'force the opposite rotation, verify. Runs BESIDE batches 1 and 3, because it needs '
     'a machine rather than a person.'),
    (3, 'Triage the unclassified pages', 'session', 'triage', ['unknown'],
     '1 session', 'free',
     'Nothing directly. It turns pages whose heading the scanner lost into ranked work, '
     'and it is scheduled here rather than last because one of them may be the next '
     'special-revenue and a plan that never opens them is guessing.'),
    (4, 'Special revenue funds', 'session', 'extractor', ['special-revenue'],
     '1-2 sessions', 'free',
     'THE BIG ONE. Closes the registered gaps "What any special revenue fund bought" and '
     '"Grants received in earlier years" outright. Rule 11\u2019s load-bearing uncertainty: '
     'grants and revolving funds pay for real staff and appear nowhere in the budget, so '
     'a line rising because a grant ended is today indistinguishable from one rising '
     'because the district grew.'),
    (5, 'Combined balance sheet', 'session', 'extractor', ['balance-sheet'],
     '1 session', 'free',
     'The whole town in one statement, which this project does not have at all. Closes '
     '"What the town held town-wide at 30 June 2024 and 30 June 2025" and bears on the '
     'free-cash discrepancy /free-cash records and cannot explain.'),
    (6, 'Receivables and tax collection', 'session', 'extractor',
     ['receivables', 'tax-collection'], '1-2 sessions', 'free',
     'What is owed and what was collected, over twelve years. One batch because they are '
     'the two halves of the same question and sit on adjacent pages in the same reports.'),
    (7, 'The tail: payroll, valuation, capital, appropriations, enrolment, elections',
     'session', 'extractor',
     ['payroll', 'valuation', 'capital', 'appropriations', 'enrollment', 'elections',
      'vital-records', 'officials', 'debt'],
     '1 session', 'free',
     'Six small families in one pass. Individually none justifies a session; together '
     'they finish the run and every one of them already has a dataset this tops up.'),
    # ---- THE OTHER STREAMS. TJ: "make sure the 'plan' pages include ALL open backlog
    # items, across all categories." They are not annual-report work and they are not
    # limited by the same thing, which is exactly why they have to be on the same page:
    # the two below are the ONLY items here that spend the plan allowance, and between
    # them they are months of it.
    (8, 'Captions for the recordings still missing them', 'background', 'fetch',
     ['__captions__'], '', 'free, throttled by YouTube',
     'Meetings whose only surviving record is a video become searchable. No allowance at '
     'all -- it is fetching, not thinking -- so it runs beside anything.'),
    (9, 'Votes out of the town\u2019s own minutes', 'refresh', 'claude -p',
     ['__votes__'], '', '',
     'Every vote the town published, each with its quote checked verbatim. Dripped by the '
     'daily refresh at 40 a day; the cap exists because the alternative is spending a '
     'week of allowance in an afternoon.'),
    (10, 'Our minutes, written from the recordings', 'refresh', 'claude -p',
     ['__minutes__'], '', '',
     'The full record of meetings the town never minuted -- decisions, transfers, budget '
     'items, public comment. The most expensive thing this project does per item, and at '
     'three a day the slowest; that pacing is deliberate.'),
]


def stream_counts():
    """How many items are left in the streams that are not annual-report pages."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import build_ingest_status as S
    except Exception:
        return {}
    out = {}
    try:
        out['__captions__'] = sum(p['n'] for p in S.caption_pending())
    except Exception:
        pass
    try:
        out['__votes__'] = sum(p['n'] for p in S.register_pending(
            lambda r: r.get('minutes') == '1', 'official-votes'))
    except Exception:
        pass
    try:
        out['__minutes__'] = sum(p['n'] for p in S.register_pending(
            lambda r: bool(r.get('transcript_paths')), 'recording-minutes'))
    except Exception:
        pass
    return out


def counts():
    """Pages and years still to do, per subject, derived from the queue itself."""
    by = collections.defaultdict(list)
    rev = []
    if not os.path.exists(PAGES):
        return by, rev
    for r in csv.DictReader(open(PAGES, encoding='utf-8')):
        if r['state'] == 'read':
            continue
        if r['state'] == 'reversed':
            rev.append(int(r['fy']))
            continue
        by[r['subject']].append(int(r['fy']))
    return by, rev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    by, rev = counts()
    streams = stream_counts()
    rows = []
    for seq, batch, channel, kind, subjects, effort, cost, delivers in PLAN:
        years, n = [], None
        if subjects == ['__reversed__']:
            years = rev
            n = len(years)
        elif subjects and subjects[0].startswith('__'):
            n = streams.get(subjects[0], 0)
            if subjects[0] in ('__votes__', '__minutes__'):
                key = 'official-votes' if subjects[0] == '__votes__' else 'recording-minutes'
                per_day, pct = RATE[key]
                effort, cost, days = drip(n, per_day, pct)
                effort = '%s \u2014 about %d days' % (effort, days)
        else:
            years = [y for s in subjects for y in by.get(s, [])]
            n = len(years)
        status = 'done' if not n else ('next' if seq == 1 else 'planned')
        rows.append(dict(
            seq=seq, batch=batch, channel=channel, kind=kind,
            subjects=' + '.join(s for s in subjects if not s.startswith('__')) or '\u2014',
            items=n or 0,
            years=('FY%d\u2013FY%d' % (min(years), max(years))) if years else '',
            runs_beside='yes' if channel == 'background' else '',
            effort=effort, cost=cost, status=status, delivers=delivers))

    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    wr.writeheader()
    wr.writerows(rows)
    text = buf.getvalue()

    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if cur != text:
            print('STALE %s -- run: python3 scripts/build_ingest_plan.py'
                  % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('ok -- %d batches, %s items planned'
              % (len(rows), '{:,}'.format(sum(r['items'] for r in rows))))
        return 0

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(text)
    print('wrote %s -- %d batches covering %s items'
          % (os.path.relpath(OUT, ROOT), len(rows),
             '{:,}'.format(sum(r['items'] for r in rows))))
    for r in rows:
        print('  %2d. %-46s %-11s %6s  %s'
              % (r['seq'], r['batch'][:46], r['channel'],
                 '{:,}'.format(r['items']), r['effort'][:44]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
