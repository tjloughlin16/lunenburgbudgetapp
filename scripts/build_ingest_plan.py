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
    # ---- AT THE END, AND WITH A CLAIM TO TEST. TJ, 21 September 2026: "debt repayment
    # schedule. This is one of the most misquoted things about our budgets. One year
    # (youll see in the minutes) people said we were drawing down so much debt that we
    # could add hundreds to the tax burden and residents would see no change. Which I
    # dont think is true."
    #
    # That is a claim a schedule settles, and it is the reason this batch is worth doing
    # rather than a nice-to-have: a debt schedule states, year by year, how much service
    # falls off. Either the fall is large enough to absorb new borrowing invisibly or it
    # is not, and the document says which.
    #
    # THE ARITHMETIC IT HAS TO SUPPORT, so the extract is built for the question: debt
    # service retiring in a year, against what a given amount of new borrowing would add
    # in that same year. Both are annual figures and they are comparable; a total
    # outstanding is neither and is the figure most likely to be quoted instead.
    #
    # WE HOLD 354 ROWS AND THE SPLIT IS THE POINT: 74 checked, 98 check failed, 182 no
    # check -- and eight years of the fifteen have no rows at all (FY2012-FY2016, FY2018,
    # FY2022). A series with holes cannot answer "how much falls off each year", which is
    # the whole question.
    #
    # AND THE QUOTE IS NOT YET FOUND. Searching the minutes for it turned up budget talk
    # and not the sentence; rule 15a says find what was actually said before writing about
    # what a category does, so locating it is part of this batch rather than a footnote.
    (11, 'Debt repayment schedule', 'session', 'extractor', ['debt'],
     '1 session', 'free',
     'Answers a claim this town argues over: that retiring debt leaves room to borrow '
     'again at no cost to a tax bill. A schedule states how much service falls off each '
     'year, so the claim is checkable rather than a matter of belief. 23 pages unread '
     'across FY2011-FY2024, and eight years currently hold no rows at all.'),
    # ---- NOT AN INGESTION, BUT IT DECIDES WHETHER ANY SEARCH MEANS ANYTHING.
    #
    # `search_minutes.py` is meant to print, on every run, how many documents it searched
    # out of how many the town has published. That line is the whole reason a search can
    # be cited: a grep that finds nothing prints nothing, and nothing READS AS "nobody
    # said it" -- which is a claim about the town rather than about our coverage.
    #
    # It currently refuses to print it: "the three states do not account for every
    # document in scope. Refusing to print a coverage line that does not foot." The
    # refusal is correct -- a wrong denominator is worse than none -- but while it stands,
    # every rule 15a search in this project is unquantified, including the one that just
    # failed to find any discussion of the town dropping its appropriations schedule.
    #
    # Found 21 September 2026 looking for exactly that. Written down here because it is
    # the kind of thing that gets rediscovered rather than remembered.
    (12, 'Fix the minutes-search coverage line', 'session', 'repair', [],
     'part of a session', 'free',
     'Nothing is ingested. It restores the denominator on every minutes search \u2014 '
     '"searched N of M published documents" \u2014 without which a search that finds '
     'nothing cannot be cited as evidence that nothing was said, which is what rule 15a '
     'asks every analysis to do.'),
    # TWO STAFF DIRECTORIES THE TOWN PUBLISHES AS ONE SPREADSHEET, given by TJ on 24
    # September 2026: one sheet of TOWN staff and one of SCHOOL staff, at a Google
    # `pubhtml` address.
    #
    # WHY IT IS `permanent` AND NOT A ONE-OFF READ. A published Google Sheet is
    # overwritten in place. It carries TODAY and no history, exactly like the town's own
    # `/m/directory` -- and that source taught this project the rule: if we do not keep a
    # dated snapshot per fetch, nobody can ever say who worked here in a given year,
    # because the publisher will have overwritten the only copy. `fetch_staff_directory.py`
    # already holds the pattern: one folder per fetch date, and the fiscal year derived
    # from it rather than typed.
    #
    # AND THE EXISTING DIRECTORY IS NOT ON A SCHEDULE EITHER, which is the larger half of
    # this job. `fetch_staff_directory.py` is named in no scheduled script -- not
    # `refresh.py`, not `daily_refresh.sh`, not `weekly_sweep.sh`; only its own extractor
    # and this plan mention it. There is exactly ONE snapshot on disk, 2026-09-22. So the
    # town's people are a single photograph with nothing arranged to take the next one,
    # and the failure mode is silent: the file keeps answering, correctly, about a day
    # that recedes. Both directories belong on the same recurring fetch, and that is what
    # makes this entry `permanent` rather than another extractor to write.
    #
    # WHAT IT IS WORTH. The org charts are built from annual-report rosters, the officials
    # listing and the town directory -- and every one of those is a list of NAMES with no
    # FTE and no funding source. A school-staff directory is the first source here that
    # covers the district's people outside the annual report, which is where /org-charts
    # is thinnest: the Library shows one person and employs ten, and four departments
    # appear in no annual report at all.
    #
    # It does not settle rule 11's standing question. A directory is who the town lists,
    # not who is funded by what, and a name is not an FTE.
    (13, 'The town and school staff directories', 'session', 'fetch + extractor', [],
     'part of a session', 'free',
     'Who works for the town and for the district TODAY, from two sheets the town '
     'publishes itself — the first source here covering school staff outside an '
     'annual report. Snapshotted per fetch, because the publisher overwrites it and the '
     'only history of it will be the one we keep. '
     'https://docs.google.com/spreadsheets/d/e/2PACX-1vR9MlZ81EtnImzmf_Z2GNEl9iAIlHjOykE'
     'XoE_u4odon7HQ_-4ZA6McyzfKr3tI066sI8dYTKuIqwvs/pubhtml'),
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
