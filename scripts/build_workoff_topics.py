#!/usr/bin/env python3
"""The senior property tax work-off program, season by season: /homes-and-taxes/senior-tax-work-off.

    python3 scripts/build_workoff_topics.py           # write the topic payload
    python3 scripts/build_workoff_topics.py --check   # fail if it would change

A resident asked, 26 October 2026, for the program over the years: how many took part, which
departments they worked in, the hours (total and by department), and the tax reduction in
dollars. The research is notes/findings/SENIOR-TAX-WORKOFF.md; the figures it settled are in

  sources/data/senior-tax-workoff.csv              one row per program season (CY2010-CY2025),
                     plus two annual-report counts whose season is not stated. Every figure has
                     a cite (a path into sources/ and a line) and the raw text found there.
  sources/data/senior-tax-workoff-departments.csv  every department each annual report lists,
                     as printed, with OUR grouping of the names (Treasurer, Tax Collector and
                     Treasurer/Tax Collector are one row).

THIS SCRIPT RE-CHECKS EVERY CITE before it writes anything: the file exists under sources/, the
quote is in the text within a few lines of the cited line (whitespace-insensitive), a PRINTED
figure appears in its own quote, and a figure marked `ours` recomputes (a sum of the amounts in
its quotes, or hours times the printed rate). It refuses otherwise. scripts/verify_workoff.py
recomputes every figure on the page by a second route, from the cited lines rather than the CSV.

PRIVACY. Participants are private individuals. No name, address or individual amount is in the
data or on the page -- counts and totals only. Two annual reports print a wage list by name;
it is not used (the findings say why).

RULE 7. The page states what the records count. Why fewer people take part is not in any
record held; the page says so where it matters and offers no cause. RULE 8: the program is
credited, nothing is a charge.
"""
import argparse
import csv
import glob
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topic_blocks as TB  # noqa: E402
import topics as REG  # noqa: E402

TID = 'senior-tax-work-off'
ME = os.path.basename(__file__)
DATA = os.path.join(ROOT, 'sources', 'data', 'senior-tax-workoff.csv')
DEPTS = os.path.join(ROOT, 'sources', 'data', 'senior-tax-workoff-departments.csv')
PUB = os.path.join(ROOT, 'fy28', 'public', 'docs', 'data')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % TID)
WINDOW = (1, 3)   # a quote may start a line before its cite and run three lines past it

# Statements the page uses that are not a season's figure: the votes that changed the rules,
# when withholding began, the money the Assessors had in 2019, the two adoption dates. Each is
# checked against its cited line exactly like a CSV row.
M = 'sources/meetings/text/'
EVENTS = {
    'vote1000': (M + 'senior-citizens-tax-work-off-committee/2014-01-27-minutes-5338.txt:17',
                 'a motion to increase the tax work-off deduction from $750.00 to $1000.00'),
    'vote1500': (M + 'select-board/2019-04-16-minutes-5155.txt:111',
                 'To approve the proposed changes to the Senior Property Taxation Work-Off Program'),
    'funded': (M + 'select-board/2019-04-16-minutes-5155.txt:109',
               'enough money to cover 12 applicants. Right now there are only six people working for the town.'),
    'w2': (M + 'board-of-assessors/2013-12-10-minutes-644.txt:64',
           'It would then be the net pay that is credited to the tax bill.'),
    'est1998': ('sources/town-annual-reports/text/4121-fy-2015-annual-town-report.txt:2640', 'Est. 1998'),
    'may2000': (M + 'select-board/2019-03-05-minutes-5150.txt:209',
                'the town initially approved this law in May of 2000'),
    'minwage': (M + 'council-on-aging/2020-03-10-minutes-1907.txt:95',
                'decided to raise the hourly wage of property tax work-off participants to minimum wage'),
}
WORDS = {'a': 1, 'an': 1, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
         'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12,
         'thirteen': 13, 'fourteen': 14, 'fifteen': 15, 'sixteen': 16}


def fail(msg):
    raise SystemExit('build_workoff_topics: ' + msg)


def squash(s):
    return re.sub(r'\s+', '', (s or '').replace('’', "'")).lower()


_TEXT = {}


def lines_of(path):
    if path not in _TEXT:
        full = os.path.join(ROOT, path)
        if not path.startswith('sources/') or not os.path.exists(full):
            fail('cite %r is not a file under sources/' % path)
        _TEXT[path] = open(full, encoding='utf-8', errors='replace').read().split('\n')
    return _TEXT[path]


def check_cite(cite, quote, where):
    """The quote is in the cited file, starting near the cited line."""
    m = re.fullmatch(r'(sources/[^:]+):(\d+)', cite.strip())
    if not m:
        fail('%s: cite %r is not path:line' % (where, cite))
    path, n = m.group(1), int(m.group(2))
    ls = lines_of(path)
    if not 1 <= n <= len(ls):
        fail('%s: %s has no line %d' % (where, path, n))
    win = squash(' '.join(ls[max(0, n - 1 - WINDOW[0]): n + WINDOW[1]]))
    if not quote.strip() or squash(quote) not in win:
        fail('%s: quote not at %s: %r' % (where, cite, quote[:70]))
    return path, n


def cites(row, m):
    cs = [c.strip() for c in row[m + '_cite'].split('|')]
    qs = [q.strip() for q in row[m + '_quote'].split('|')]
    if len(cs) != len(qs):
        fail('%s %s: %d cites for %d quotes' % (row['season'], m, len(cs), len(qs)))
    return [check_cite(c, q, '%s %s' % (row['season'], m)) + (q,) for c, q in zip(cs, qs)]


def present(f, q):
    """`f` written in `q` as a whole figure: not part of a longer number."""
    return re.search(r'(?<![\d,.])%s(?!\d|[,.]\d)' % re.escape(f), q, re.I) is not None


def forms(v, kind):
    """Every way a printed figure is written in these documents."""
    x = float(v)
    out = {v}
    if kind == 'dollars':
        out |= {'$' + format(x, ',.2f'), '$' + format(x, ',.0f') if x.is_integer() else '$' + format(x, ',.2f')}
    elif kind == 'participants':
        out |= {str(int(x))} | {w for w, k in WORDS.items() if k == int(x) and len(w) > 2}
    else:
        out |= {format(x, ',.2f').rstrip('0').rstrip('.'), format(x, ',.2f'), format(x, ',g')}
    return out


def numbers_in(q, kind):
    """Amounts or counts in a quote: '$7,970.00' -> 7970.0; for a count, a bare integer not
    after '$', or a number word ('A Tax Work Off applicant' -> 1)."""
    if kind == 'dollars':
        return [float(x.replace(',', '')) for x in re.findall(r'\$([\d,]+(?:\.\d+)?)', q)]
    ns = re.findall(r'(?<![$\w,.])(\d+)(?![\w,.])', q)
    if ns:
        return [float(ns[0])]
    w = q.split()[0].lower()
    return [float(WORDS[w])] if w in WORDS else []


def verified(row, m):
    """The figure in column `m` of a row, checked against its cite. None when blank."""
    v = row[m]
    if not v:
        return None
    base = m.replace('_alt', '')
    kind = row.get(m + '_kind', 'printed') or 'printed'
    cs = cites(row, m)
    if kind == 'printed':
        q = cs[0][2]
        if not any(present(f, q) for f in forms(v, base)):
            fail('%s %s: %s is not in its own quote %r' % (row['season'], m, v, q))
    elif kind == 'ours':
        how = row[m + '_how']
        if how == 'sum':
            got = sum(numbers_in(q, base)[0] for _, _, q in cs)
        elif how == 'hours x rate':
            rate = numbers_in(cs[0][2], 'dollars')[0]
            got = float(row['hours']) * rate
            if rate != float(row['rate']):
                fail('%s: the rate in the quote is not the row\'s rate' % row['season'])
        else:
            fail('%s %s: an `ours` figure must say how: %r' % (row['season'], m, how))
        if abs(got - float(v)) > 0.005:
            fail('%s %s: ours is %s, recomputed %s' % (row['season'], m, v, got))
    else:
        fail('%s %s: kind %r' % (row['season'], m, kind))
    return float(v)


def load():
    rows = list(csv.DictReader(open(DATA, encoding='utf-8')))
    seasons, unpinned = [], []
    for r in rows:
        x = dict(season=r['season'], note=r['note'])
        for m in ('participants', 'participants_alt', 'hours', 'dollars', 'dollars_alt'):
            x[m] = verified(r, m)
        for k in ('participants_kind', 'participants_alt_qualifier', 'hours_qualifier', 'dollars_kind',
                  'dollars_qualifier', 'dollars_basis', 'dollars_alt_kind', 'dollars_alt_basis', 'cap', 'rate',
                  'rate_kind'):
            x[k] = r[k]
        if x['dollars'] is not None and x['dollars_basis'] not in ('before withholding', 'after withholding', 'not stated'):
            fail('%s: dollars basis %r' % (r['season'], x['dollars_basis']))
        x['srcs'] = sorted({p for m in ('participants', 'hours', 'dollars', 'dollars_alt', 'cap', 'rate')
                            if r[m + '_cite'] for p, _, _ in cites(r, m)})
        # cap and rate: '750', '1000>1500' (changed mid-season), '?' (unclear), 'minimum wage'
        for m in ('cap', 'rate'):
            v = r[m]
            if not v:
                continue
            q = ' | '.join(x[2] for x in cites(r, m))
            if v != '?' and not (m == 'rate' and r['rate_kind'] == 'ours'):
                for part in v.split('>'):
                    if part.isdigit() and not ('$' + format(int(part), ',d') in q or '$%s' % part in q):
                        fail('%s %s: %s is not in %r' % (r['season'], m, part, q))
                    if not part.isdigit() and squash(part) not in squash(q):
                        fail('%s %s: %r is not in %r' % (r['season'], m, part, q))
        if r['rate_kind'] == 'ours':   # $750 / 93.75 hours
            q = cites(r, 'rate')[0][2]
            h = float(re.search(r'([\d.]+) hours', q).group(1))
            if abs(numbers_in(q, 'dollars')[0] / h - float(r['rate'])) > 0.005:
                fail('%s: our rate does not recompute' % r['season'])
        (seasons if r['season'].startswith('CY') else unpinned).append(x)
    ys = [int(s['season'][2:]) for s in seasons]
    if ys != list(range(ys[0], ys[-1] + 1)):
        fail('seasons are not consecutive: %s' % ys)
    events = {k: check_cite(c, q, k) + (q,) for k, (c, q) in EVENTS.items()}
    depts = list(csv.DictReader(open(DEPTS, encoding='utf-8')))
    for d in depts:
        check_cite(d['cite'], d['printed'], 'department %s %s' % (d['season'], d['printed']))
    return seasons, unpinned, events, depts


# ------------------------------------------------------------------ formatting

def usd2(v):
    return '$' + format(v, ',.2f')


def hrs(v):
    """Hours as the charts print them (two places), so a bar and a sentence agree."""
    return format(v, ',.2f')


def hrs_t(v):
    """Hours as the documents print them, for the table."""
    return format(v, ',.2f').rstrip('0').rstrip('.')


def L(s):
    """A label carrying a date or a year: its digits are declared literals."""
    return (s, None, tuple(re.findall(r'\d(?:[\d,.]*\d)?', s)))


def doc_of(path):
    """The original document behind an extracted text, for the sources list."""
    if path.startswith('sources/town-annual-reports/text/'):
        p = path.replace('/text/', '/docs/').replace('.txt', '.pdf')
    else:
        board, name = path.split('/')[-2], os.path.basename(path)[:-4]
        hit = sorted(glob.glob(os.path.join(ROOT, 'sources', 'meetings', board, name + '.*')))
        p = os.path.relpath(hit[0], ROOT) if hit else path
    return p[len('sources/'):]


BOARD = {'board-of-assessors': 'Board of Assessors', 'council-on-aging': 'Council on Aging',
         'senior-citizens-tax-work-off-committee': 'Senior Tax Work-Off Committee',
         'select-board': 'Select Board'}


def source_label(path):
    m = re.search(r'/(\d{4})-fy-(\d{4})-annual-town-report', path)
    if m:
        return 'Town of Lunenburg — Annual Town Report, FY%s (the program\'s own section)' % m.group(2)
    board, name = path.split('/')[-2], os.path.basename(path)
    return 'Town of Lunenburg — %s minutes, %s' % (BOARD[board], name[:10])


# ------------------------------------------------------------------ the page

def build():
    S, U, E, D = load()
    by = {int(s['season'][2:]): s for s in S}
    years = sorted(by)
    first, last = years[0], years[-1]
    allow_years = tuple(str(y) for y in years)
    N = lambda v, u='seniors': figure(v, C.num(v), u)
    D2 = lambda v: figure(v, usd2(v), 'dollars')
    H = lambda v: figure(v, hrs(v), 'hours')

    p0, p1 = by[first]['participants'], by[last]['participants']
    d0, d1 = by[first]['dollars'], by[last]['dollars']
    if by[first]['dollars_basis'] != 'not stated' or by[last]['dollars_basis'] != 'before withholding':
        fail('the first and last totals are no longer on the bases the page describes')
    cap0, cap1 = int(by[first]['cap']), int(by[last]['cap'])
    hours = {y: by[y]['hours'] for y in years if by[y]['hours'] is not None}
    h0y = min(hours)
    h0, h1 = hours[h0y], hours[last]
    hmax_y = max(hours, key=hours.get)
    if hmax_y != h0y:
        fail('the first season with hours is no longer the most hours; the hours sentence is wrong')
    possible = p1 * cap1
    funded = int(re.search(r'cover (\d+) applicants', E['funded'][2]).group(1))
    working = WORDS[re.search(r'only (\w+) people', E['funded'][2]).group(1)]
    no_count = [y for y in years if by[y]['participants'] is None]
    no_hours = [y for y in years if y >= h0y and by[y]['hours'] is None]
    alt = {y: by[y] for y in years if by[y]['dollars_alt'] is not None}

    # ------------------------------------------------------------ facts
    f = LD.fact
    facts = [
        f('first', N(p0), 'seniors who finished the %d season' % first, 'published', allow=(str(first),)),
        f('last', N(p1), 'seniors who took part in the %d season' % last, 'published', allow=(str(last),)),
        f('cap', figure(cap1, C.usd(cap1), 'dollars'), 'most one senior can earn in a season, since July 2019',
          'published', allow=('2019',)),
        f('d-first', D2(d0), 'taken off tax bills for the %d season' % first, 'published', allow=(str(first),)),
        f('d-last', D2(d1), 'earned in %d, before withholding' % last, 'published', allow=(str(last),)),
        f('possible', D2(possible), 'the most %s seniors could earn in %d: ours' % (C.num(p1), last), 'estimate',
          {'n': N(p1)}, allow=(str(last),)),
        f('h-first', H(h0), 'hours worked in %d, all departments' % h0y, 'published', allow=(str(h0y),)),
        f('h-last', H(h1), 'hours worked in %d, all departments' % last, 'published', allow=(str(last),)),
        f('funded', N(funded, 'applicants'), 'applicants the Assessors had money for, April 2019', 'published',
          allow=('2019',)),
        f('working', N(working), 'seniors working for the town that month', 'published'),
        f('gap-dept', None, 'hours worked in each department, any season', 'gap',
          closes='the HR director’s timesheets returned to the Assessors each November, tallied by department'),
        f('gap-2013', None, 'seniors, hours and dollars for the 2013 season', 'gap', allow=('2013', 'FY2014'),
          closes='the Assessors’ FY2014 list of work-off credits'),
    ]

    # ------------------------------------------------------------ conclusions, each with what it means
    con = TP.conclusion
    yrs = {'a': figure(first, str(first)), 'b': figure(last, str(last))}
    conclusions = [
        con('%s seniors finished the %d season; %s took part in %d.' % (C.num(p0), first, C.num(p1), last),
            ['first', 'last'], dict(yrs, p=N(p0), q=N(p1)),
            so='The program reaches fewer households than in its first recorded year. No record held '
               'says why, and nothing here tests a reason.'),
        con('The cap doubled, from %s to %s; a season’s total fell from %s to %s.'
            % (C.usd(cap0), C.usd(cap1), usd2(d0), usd2(d1)),
            ['cap', 'd-first', 'd-last'],
            {'c0': figure(cap0, C.usd(cap0)), 'c1': figure(cap1, C.usd(cap1)), 'd0': D2(d0), 'd1': D2(d1)},
            so='A larger cap has not raised what comes off tax bills in total: the total follows the '
               'number of people taking part.'),
        con('In %d, %s seniors earned %s of the %s their caps allowed.'
            % (last, C.num(p1), usd2(d1), usd2(possible)),
            ['d-last', 'possible'], {'y': yrs['b'], 'n': N(p1), 'd': D2(d1), 'm': D2(possible)},
            so='Together they earned about half of it. Whether for lack of hours or by choice, no '
               'record held says.'),
        con('In April 2019 the Assessors had money for %s applicants; %s seniors were working.'
            % (C.num(funded), C.num(working)),
            ['funded', 'working'], {'f': N(funded, 'applicants'), 'w': N(working)}, allow=('2019',),
            so='That year money was not what limited the program. What did, the minutes do not show.'),
    ]

    # ------------------------------------------------------------ the signature chart: who took part
    xs = [str(y) for y in years]
    printed = [by[y]['participants'] if by[y]['participants_kind'] == 'printed' else None for y in years]
    ours = [by[y]['participants'] if by[y]['participants_kind'] == 'ours' else None for y in years]
    ours_y = [y for y in years if by[y]['participants_kind'] == 'ours']
    chart = TP.series(
        'Seniors taking part, by season', xs,
        [TP.track('Count a record prints', printed, basis='stated'),
         TP.track('Our sum of two approvals', ours, basis='estimate')],
        'count', kind='bar', stacked=True,
        note='No count is published for %s. %s is our sum of the Assessors’ two approvals.'
             % (' or '.join(map(str, no_count)), ', '.join(map(str, ours_y))),
        note_allow=tuple(map(str, no_count + ours_y)))

    # ------------------------------------------------------------ the money, coloured by what it is
    BASES = [('Before withholding', 'before withholding', 'stated', 'printed'),
             ('After withholding', 'after withholding', 'stated', 'printed'),
             ('Basis not stated', 'not stated', 'stated', 'printed'),
             ('Ours: hours times the rate', 'before withholding', 'estimate', 'ours')]
    money = TP.series(
        'Tax reduction, by season', xs,
        [TP.track(name, [by[y]['dollars'] if by[y]['dollars'] is not None and by[y]['dollars_basis'] == b
                         and by[y]['dollars_kind'] == k else None for y in years], basis=basis)
         for name, b, basis, k in BASES],
        '$', kind='bar', stacked=True, decimals=2,
        note='One total a season. The %s figure is printed as “under” it. Two seasons have a second, '
             'different total: see below.' % ', '.join(str(y) for y in years if by[y]['dollars_qualifier'] == 'under'),
        note_allow=tuple(str(y) for y in years if by[y]['dollars_qualifier'] == 'under'))
    money_block = TB.chart(money, place='chart', so=(
        'The totals are not one series. Since 2014 the credit is pay net of withholding, and the reports '
        'print some years before it, one after it and most without saying, so a change between two '
        'colours is not a measured change.', None, ('2014',)))

    hseries = [hours.get(y) for y in years if y >= h0y]
    hchart = TP.series('Hours worked, all departments together', [str(y) for y in years if y >= h0y],
                       [TP.track('Hours a report prints', hseries, basis='stated')], 'hours', kind='bar',
                       decimals=2,
                       note='No hours are published before %d, or for %s.' % (h0y, ', '.join(map(str, no_hours))),
                       note_allow=tuple(map(str, [h0y] + no_hours)))
    hours_block = TB.chart(hchart, place='chart', so=(
        'Total hours fell from %s in %d to %s in %d. No report says how they split between departments.'
        % (hrs(h0), h0y, hrs(h1), last), {'a': H(h0), 'b': H(h1)}, (str(h0y), str(last))))

    # ------------------------------------------------------------ the rules, as a timeline
    def states(test):
        """printed where a season's own record states it, carried (ours) between two that do,
        unclear where the record is ambiguous."""
        out = []
        for y in years:
            r = by[y]
            out.append('unclear' if test(r) == '?' else 'printed' if test(r) else None)
        idx = [i for i, s in enumerate(out) if s == 'printed']
        for a, b in zip(idx, idx[1:]):
            for i in range(a + 1, b):
                if out[i] is None:
                    out[i] = 'carried'
        return out

    def capis(v):
        return lambda r: '?' if r['cap'] == '?' and v in (750, 1000) else str(v) in r['cap'].split('>')

    def rateis(*vs):
        return lambda r: '?' if r['rate'] == '?' and '15' in vs else any(v in r['rate'].split('>') for v in vs)

    ix = {y: i for i, y in enumerate(years)}
    legend = [('printed', 'A record states it for that season', 'neutral'),
              ('carried', 'Between two seasons that state it: our reading', 'neutral', 'outline'),
              ('unclear', 'The record is unclear', 'other')]
    t = TB.track
    cap_tracks = [
        t(('Up to $750', None, ('$750',)), states(capis(750)),
          note='Council on Aging and committee minutes; the 2014 season paid “anywhere between” the two caps.',
          basis=('record', 'Council on Aging minutes')),
        t(('Up to $1,000', None, ('$1,000',)), states(capis(1000)), event=ix[2014],
          note='The committee voted in January 2014 to take it to Town Meeting; no Town Meeting vote is held.',
          basis=('record', 'Committee minutes, January 2014')),
        t(('Up to $1,500', None, ('$1,500',)), states(capis(1500)), event=ix[2019],
          note='Select Board vote, April 2019; in force from July 2019, mid-season.',
          basis=('record', 'Select Board minutes, April 2019')),
    ]
    rate_tracks = [
        t(('$8 an hour, ours', None, ('$8',)), states(lambda r: r['rate'] == '8'),
          note='Ours: $750 for 93.75 hours, from the committee’s 2011 minutes.', basis=('reading', 'Our reading')),
        t(('$10 an hour', None, ('$10',)), states(rateis('10'))),
        t(('$12, then minimum wage', None, ('$12',)), states(rateis('12', 'minimum wage')), event=ix[2019],
          note='The committee moved the rate to minimum wage in March 2020; the cap stayed.',
          basis=('record', 'Council on Aging minutes, March 2020')),
        t(('$15 an hour', None, ('$15',)), states(rateis('15'))),
    ]
    for tr in cap_tracks + rate_tracks:   # the notes carry years: declared literals
        if tr['note']:
            tr['note'] = (tr['note'], None, tuple(re.findall(r'\d[\d,.]*', tr['note'])))
    rules = TB.timeline(
        'The cap and the hourly rate, season by season', xs,
        [('Most one senior could earn', cap_tracks), ('Hourly rate', rate_tracks)],
        legend, place='body', marker=(ix[2013], L('Paid as wages from 2014: the net is credited')),
        event_label='a vote that changed it',
        note=('No rate is printed for %s. The FY2022 report prints $15 as the rate when it was written, '
              'not the rate paid in 2022.' % ', '.join(str(y) for y in years if not by[y]['rate'] and y > 2011),
              None, tuple(str(y) for y in years if not by[y]['rate'] and y > 2011) + ('FY2022', '$15', '2022')))

    # ------------------------------------------------------------ departments, as a timeline
    dyears = sorted({int(d['season'][2:]) for d in D})
    dper = list(range(dyears[0], dyears[-1] + 1))
    missing = [y for y in dper if y not in dyears]
    groups = {}
    for d in D:
        groups.setdefault(d['grouped_as_ours'], set()).add(int(d['season'][2:]))
    order = sorted(groups, key=lambda g: (-len(groups[g]), g))
    dtracks = []
    for g in order:
        n = len(groups[g])
        tag = '%d of %d reports' % (n, len(dyears))
        dtracks.append(t(g, ['listed' if y in groups[g] else 'noreport' if y in missing else None for y in dper],
                         tags=[(tag, None, (str(n), str(len(dyears))))]))
    for y in dyears:   # the count per season on the page is the count the report lists
        printed_n = sum(1 for d in D if int(d['season'][2:]) == y)
        if printed_n != sum(1 for g in groups if y in groups[g]):
            fail('season %d: two printed names were grouped into one row; the counts would differ' % y)
    depts = TB.timeline(
        'Departments that took part, as each report lists them', [str(y) for y in dper],
        [('Department or board', dtracks)],
        [('listed', 'Listed in that season’s report', 'neutral'),
         ('noreport', 'No program section that year', 'other')], place='body',
        note=('The grouping of names is ours: Treasurer, Tax Collector and Treasurer/Tax Collector are one row. '
              'No report says how many hours each department received, and none before %d names them.' % dyears[0],
              None, (str(dyears[0]),)))

    # ------------------------------------------------------------ where two records disagree
    y12, y24 = sorted(alt)
    first_alt = by[first]['participants_alt']
    disagree = TB.panels('Where two town records disagree', [
        TB.panel(('The %d season, seniors' % first, None, (str(first),)),
                 [('Completed, Council on Aging, December', C.num(p0), None),
                  ('To receive a credit, a month earlier', 'about ' + C.num(first_alt), None)]),
        TB.panel(('The %d season, dollars' % y12, None, (str(y12),)),
                 [(L('Assessors, May 2013'), usd2(by[y12]['dollars']), None),
                  ('Ours: two approvals added', usd2(by[y12]['dollars_alt']), None)]),
        TB.panel(('The %d season, dollars' % y24, None, (str(y24),)),
                 [('Annual report, before withholding', usd2(by[y24]['dollars']), None),
                  (L('Assessors, February 2026'), usd2(by[y24]['dollars_alt']), None)]),
        TB.panel('The year the town adopted it',
                 [(L('Annual reports, FY2015 to FY2018'), '1998', None),
                  (L('Town Manager, March 2019'), 'May 2000', None)]),
    ], place='end', so='Each pair is shown as printed. Nothing held says which is right, and we do not average them.')

    # ------------------------------------------------------------ what a season is (it is misread)
    lead = TB.explain('How a season is counted', [
        ('A season runs from 1 January to 1 November. What a senior earns comes off the third-quarter '
         'tax bill of the next fiscal year, so the 2016 season is charged to FY2017.', None,
         ('1', '2016', 'FY2017')),
        ('Since 2014 a senior in the program is paid as a town employee, and federal tax, Medicare and '
         'retirement are withheld. It is the **net** pay that is credited, so the cap is the most a senior '
         'can earn, not the reduction on the bill.', None, ('2014',)),
        'Every figure here is a total for all participants. No participant is named and no one’s amount is shown.',
    ], place='lead', tone='define')

    gaps = TB.explain('What no record held answers', [
        'Hours in each department, for any season: every report prints one total.',
        ('The 2013 season, and the 2023 season’s hours and departments: neither annual report has the '
         'program’s section.', None, ('2013', '2023')),
        ('Whether the totals for 2018 to 2021 are before or after withholding, and what 2022 was before it.',
         None, ('2018', '2021', '2022')),
        'Which account pays the credits. The Assessors’ minutes say “likely” the overlay, and ask.',
        ('When Town Meeting accepted the program, and whether it voted the 2014 move to $1,000.', None,
         ('2014', '$1,000')),
        ('Two annual reports, FY2011 and FY2014, count %s and %s seniors with no season stated; they are '
         'in the table, not the charts.' % (C.num(U[0]['participants']), C.num(U[1]['participants'])),
         {'a': N(U[0]['participants']), 'b': N(U[1]['participants'])}, ('FY2011', 'FY2014')),
    ], place='end', tone='plain')

    # ------------------------------------------------------------ the table
    dcount = {y: sum(1 for d in D if int(d['season'][2:]) == y) for y in dyears}

    def money_cell(r):
        if r['dollars'] is None:
            return ''
        s = ('under ' if r['dollars_qualifier'] == 'under' else '') + usd2(r['dollars'])
        if r['dollars_kind'] == 'ours':
            s += ' (ours)'
        if r['dollars_alt'] is not None:
            s += ' or ' + usd2(r['dollars_alt']) + (' (ours)' if r['dollars_alt_kind'] == 'ours' else '')
        return s

    def who(r):
        if r['participants'] is None:
            return ''
        s = C.num(r['participants'])
        if r['participants_kind'] == 'ours':
            s += ' (our sum)'
        if r['participants_alt'] is not None:
            s += ' (about %s credited)' % C.num(r['participants_alt'])
        return s

    def src(r):
        kinds = sorted({('Annual report' if 'annual-town-report' in p else BOARD[p.split('/')[-2]])
                        for p in r['srcs']})
        return '; '.join(kinds)

    rows = []
    for y in years:
        r = by[y]
        rows.append(dict(label=str(y), cells=[
            who(r), (('over ' if r['hours_qualifier'] == 'over' else '') + hrs_t(r['hours'])) if r['hours'] is not None else '',
            C.num(dcount[y]) if y in dcount else '', money_cell(r),
            (r['dollars_basis'] + (' or ' + r['dollars_alt_basis'] if r['dollars_alt'] is not None
                                   and r['dollars_alt_basis'] != r['dollars_basis'] else ''))
            if r['dollars'] is not None else '', src(r)]))
    for r in U:
        rows.append(dict(label='%s report, season not stated' % r['season'].split('-')[1], cells=[
            who(r), 'over ' + hrs_t(r['hours']), '', '', '', src(r)]))
    table = dict(caption='The program, season by season', views=[dict(
        key='all', label='Every season', total_col=None, kinds=['stated'] * 6,
        columns=['Seniors', 'Hours', 'Departments listed', 'Tax reduction', 'Before or after withholding', 'Source'],
        rows=rows,
        note='As printed. “Ours” marks a figure we computed: hours times the printed rate, or two approvals '
             'added. A blank is not published in any record held.')])

    # ------------------------------------------------------------ sources
    paths = sorted({p for s in S + U for p in s['srcs']} | {p for p, _, _ in E.values()}
                   | {d['cite'].split(':')[0] for d in D})
    sources = [dict(label=source_label(p), href='/docs/' + doc_of(p)) for p in paths]
    sources += [
        dict(label='Lunenburg Budget Project — senior-tax-workoff.csv (every figure, its cite and the text '
                   'found there)', href='/docs/data/senior-tax-workoff.csv'),
        dict(label='Lunenburg Budget Project — senior-tax-workoff-departments.csv (each department as '
                   'printed, and our grouping)', href='/docs/data/senior-tax-workoff-departments.csv'),
    ]

    return TP.page(
        TID,
        'Seniors in the work-off fell from %s in %d to %s in %d, while the cap rose from %s to %s.'
        % (C.num(p0), first, C.num(p1), last, C.usd(cap0), C.usd(cap1)),
        facts, conclusions, chart=chart, table=table, sources=sources,
        finding_figures={'p': N(p0), 'q': N(p1), 'a': figure(cap0, C.usd(cap0)), 'b': figure(cap1, C.usd(cap1))},
        finding_allow=(str(first), str(last)),
        blocks=[lead, money_block, hours_block, rules, depts, disagree, gaps])


def output():
    return json.dumps(build(), indent=1, ensure_ascii=False, sort_keys=True) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if REG.TOPICS.get(TID, (None, None, None))[2] != ME:
        fail('%s is not registered to %s in scripts/topic_registry/' % (TID, ME))
    text = output()
    pubs = [(src, os.path.join(PUB, os.path.basename(src))) for src in (DATA, DEPTS)]
    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else None
        stale = cur != text or any(not os.path.exists(p) or open(p, 'rb').read() != open(s, 'rb').read()
                                   for s, p in pubs)
        if stale:
            print('STALE %s' % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('senior tax work-off topic: current')
        return 0
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, OUT)
    for s, p in pubs:
        shutil.copyfile(s, p)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
