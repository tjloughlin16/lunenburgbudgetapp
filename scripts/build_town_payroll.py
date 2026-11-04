#!/usr/bin/env python3
"""TOWN AND SCHOOL PAYROLL: what the Town paid its people each year, as its own wage lists
print it, name by name, 2011-2025. One topic page on the Town departments shelf.

    python3 scripts/build_town_payroll.py           # write the topic payload
    python3 scripts/build_town_payroll.py --check   # fail if it would change

TJ, 4 November 2026, once the wage list read every year: B, a payroll page. Until that day the
list read only some years, and TJ had held it back -- *"if we dont have the data, we shouldn't
show partial data"* -- because a total built on a half-read year ranks the scan, not the payroll.

EVERY FIGURE IS sources/data/gross-wages.csv (scripts/extract_gross_wages.py). What it is:
GROSS pay in the year each list prints -- ten of the fifteen headings say calendar, five print
only the year -- every fund, overtime, details and stipends included. What it is not: salary,
FTE, the cost of a post with benefits, or what taxes alone paid (rule 11). Dollars are each
year's own, not adjusted for inflation.

THE 2.5% LINE IS OURS: the 2011 payroll grown at the levy limit's 2.5% a year. It is a pace to
measure against, not a claim that payroll is subject to the levy limit.
"""
import argparse
import collections
import csv
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
import topic_blocks as TB  # noqa: E402

ID = 'town-payroll'
DATA = os.path.join(ROOT, 'sources', 'data')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % ID)
CAP = 0.025
BANDS = [(0, 50000, 'Paid under $50,000'), (50000, 100000, 'Paid $50,000 to $99,999'),
         (100000, None, 'Paid $100,000 or more')]


def fail(msg):
    raise SystemExit('build_town_payroll: ' + msg)


def load():
    by = collections.defaultdict(list)
    for r in csv.DictReader(open(os.path.join(DATA, 'gross-wages.csv'), encoding='utf-8')):
        by[int(r['fy'])].append(r)
    years = sorted(by)
    if years != list(range(years[0], years[-1] + 1)):
        fail('the wage list has a missing year: %s' % years)
    return by, years


def page():
    by, years = load()
    first, last = years[0], years[-1]
    amt = {y: [float(r['amount']) for r in by[y]] for y in years}
    tot = {y: sum(amt[y]) for y in years}
    n = {y: len(amt[y]) for y in years}
    med = {y: statistics.median(amt[y]) for y in years}
    band = {y: [sum(a for a in amt[y] if a >= lo and (hi is None or a < hi)) for lo, hi, _ in BANDS]
            for y in years}
    hundred = {y: sum(1 for a in amt[y] if a >= 100000) for y in years}
    pace = {y: tot[first] * (1 + CAP) ** (y - first) for y in years}
    grew = tot[last] / tot[first] - 1
    pace_grew = pace[last] / tot[first] - 1
    yearly = (tot[last] / tot[first]) ** (1.0 / (last - first)) - 1
    dept_years = [y for y in years if sum(1 for r in by[y] if r['department']) > 0.9 * n[y]]
    if dept_years != list(range(first, 2018)):
        fail('the years that print a department moved: %s -- rewrite the department chart' % dept_years)
    school = {y: sum(float(r['amount']) for r in by[y] if r['department'] == 'School') for y in dept_years}
    share = {y: school[y] / tot[y] for y in dept_years}
    lo_s, hi_s = min(share.values()), max(share.values())
    checked = sum(1 for y in years for r in by[y] if r['status'] == 'checked')
    rows_all = sum(n.values())

    yr = lambda y: figure(y, str(y), 'year')
    U = lambda v: figure(v, C.usd(v))
    P = lambda x: figure(x * 100, C.pct(x * 100, 0), 'percent')
    N = lambda v, unit: figure(v, C.num(v), unit)
    xs = [str(y) for y in years]

    # ---- the signature: payroll beside the pace the levy limit allows a levy
    chart = TP.series(
        'Payroll beside the levy limit’s pace', xs,
        [TP.track('Payroll, as the wage lists print it', [round(tot[y], 2) for y in years], 'published',
                  labels={len(years) - 1: ('up %s since %d' % (C.pct(grew * 100, 0), first),
                                           (C.pct(grew * 100, 0), str(first)))}),
         TP.track('The %d payroll at %s a year (ours)' % (first, C.pct(CAP * 100)),
                  [round(pace[y], 2) for y in years], 'estimate')],
        '$', kind='line', from_zero=False,
        note='Gross pay, every fund, each year’s dollars. The levy limit applies to the tax levy, not to '
             'payroll; it is drawn as a pace.', note_allow=())

    bands = TP.series(
        'Payroll by what each person was paid', xs,
        [TP.track(label, [round(band[y][i], 2) for y in years], 'published')
         for i, (_, _, label) in enumerate(BANDS)],
        '$', kind='bar', stacked=True,
        note='Each person’s gross pay for the year, in that year’s dollars.', note_allow=())

    dx = [str(y) for y in dept_years]
    depts = TP.series(
        'Schools and the rest of the Town', dx,
        [TP.track('School', [round(school[y], 2) for y in dept_years], 'published'),
         TP.track('Every other department', [round(tot[y] - school[y], 2) for y in dept_years], 'published')],
        '$', kind='bar', stacked=True, totals=True,
        note='Only %d to %d print a department beside each name.' % (dept_years[0], dept_years[-1]),
        note_figures={'a': yr(dept_years[0]), 'b': yr(dept_years[-1])})

    big = [band[y][2] / tot[y] for y in (first, last)]
    bands_block = TB.chart(bands, so=(
        'Pay of $100,000 or more was %s of payroll in %d and %s in %d.'
        % (C.pct(big[0] * 100, 0), first, C.pct(big[1] * 100, 0), last),
        {'a': P(big[0]), 'y': yr(first), 'b': P(big[1]), 'z': yr(last)}, ('100,000',)))
    depts_block = TB.chart(depts, so=(
        'The schools are most of payroll: %s to %s in each of these years.'
        % (C.pct(lo_s * 100, 0), C.pct(hi_s * 100, 0)), {'l': P(lo_s), 'h': P(hi_s)}, ()))

    f = LD.fact
    facts = [
        f('tot', U(tot[last]), 'paid to everyone on the %d wage list' % last, 'published',
          label_figures={'y': yr(last)}),
        f('tot0', U(tot[first]), 'paid to everyone on the %d wage list' % first, 'published',
          label_figures={'y': yr(first)}),
        f('grew', P(grew), 'payroll growth, %d to %d' % (first, last), 'published',
          label_figures={'a': yr(first), 'b': yr(last)}),
        f('pace', P(pace_grew), 'the same years at the levy limit’s %s a year (ours)' % C.pct(CAP * 100),
          'estimate', label_figures={'c': figure(CAP * 100, C.pct(CAP * 100), 'percent')}),
        f('h1', N(hundred[last], 'people'), 'people paid $100,000 or more, %d' % last, 'published',
          label_figures={'y': yr(last)}, allow=('100,000',)),
        f('h0', N(hundred[first], 'people'), 'people paid $100,000 or more, %d' % first, 'published',
          label_figures={'y': yr(first)}, allow=('100,000',)),
        f('n', N(n[last], 'people'), 'people paid anything, %d' % last, 'published',
          label_figures={'y': yr(last)}),
        f('med', U(med[last]), 'the middle person’s pay, %d' % last, 'published', label_figures={'y': yr(last)}),
        f('dept', None, 'payroll by department after %d' % dept_years[-1], 'gap',
          label_figures={'y': yr(dept_years[-1])},
          closes='The Town’s wage list with each name’s department, as it printed through %d'
                 % dept_years[-1]),
    ]
    con = TP.conclusion
    conclusions = [
        con('Payroll rose %s from %d to %d; at the levy limit’s %s a year it would have risen %s.'
            % (C.pct(grew * 100, 0), first, last, C.pct(CAP * 100), C.pct(pace_grew * 100, 0)),
            ['tot', 'tot0', 'grew', 'pace'],
            {'g': P(grew), 'a': yr(first), 'b': yr(last), 'c': figure(CAP * 100, C.pct(CAP * 100), 'percent'),
             'p': P(pace_grew)},
            so='That is %s a year. Wages are every fund, so grants and fees pay part, not taxes alone.'
               % C.pct(yearly * 100),
            so_figures={'y': figure(yearly * 100, C.pct(yearly * 100), 'percent')}),
        con('%d people were paid $100,000 or more in %d; in %d, %d were.'
            % (hundred[last], last, first, hundred[first]), ['h1', 'h0'],
            {'h': N(hundred[last], 'people'), 'a': yr(last), 'b': yr(first), 'z': N(hundred[first], 'people')},
            allow=('100,000',),
            so='Each year in its own dollars, so a fixed line counts more people as pay rises.'),
        con('The number of people paid rose from %d to %d; the middle person’s pay, from %s to %s.'
            % (n[first], n[last], C.usd(med[first]), C.usd(med[last])), ['n', 'med'],
            {'a': N(n[first], 'people'), 'b': N(n[last], 'people'), 'c': U(med[first]), 'd': U(med[last])},
            so='Most of the growth is in pay per person, not people; a name is not a job or an FTE.'),
        con('Schools were %s to %s of payroll in every year a department is printed, %d to %d.'
            % (C.pct(lo_s * 100, 0), C.pct(hi_s * 100, 0), dept_years[0], dept_years[-1]), ['dept'],
            {'l': P(lo_s), 'h': P(hi_s), 'a': yr(dept_years[0]), 'b': yr(dept_years[-1])},
            so='After %d the list prints no department, so the split cannot be followed.' % dept_years[-1],
            so_figures={'y': yr(dept_years[-1])}),
    ]

    rows_t = [dict(label=str(y), cells=[C.num(n[y]), '$' + format(tot[y], ',.2f'), C.usd(med[y]),
                                         C.num(hundred[y])]) for y in reversed(years)]
    table = dict(caption='Every year of the wage list', views=[dict(
        key='years', label='By year', kinds=['ledger'] * 4,
        columns=['People paid', 'Payroll', 'Middle pay', 'Paid $100,000 or more'], rows=rows_t,
        note='%s of %s names sit on a page where every printed amount was captured.'
             % (C.num(checked), C.num(rows_all)))])

    sources = [
        dict(key='wages', label='Lunenburg Budget Project — gross-wages.csv (every name and amount the Town’s '
                                'wage lists print, 2011–2025)', href='/docs/data/gross-wages.csv'),
        dict(key='refused', label='Lunenburg Budget Project — gross-wages-refused.csv (rows not read, and '
                                  'records the Town printed twice)', href='/docs/data/gross-wages-refused.csv'),
        dict(key='add16', label='Town of Lunenburg — FY2016 annual town report addendum (the 2016 list)',
             href='/docs/town-annual-reports/docs/4122-fy-2016-annual-town-report-addendum.pdf'),
    ]
    cite = TP.cite
    return TP.page(
        ID,
        'The Town paid %s in %d, %s more than in %d. The levy limit’s pace would be %s.'
        % (C.usd(tot[last]), last, C.pct(grew * 100, 0), first, C.pct(pace_grew * 100, 0)),
        facts, conclusions, chart=chart, table=table, sources=sources,
        finding_figures={'a': U(tot[last]), 'y': yr(last), 'g': P(grew), 'b': yr(first), 'p': P(pace_grew)},
        flow=['finding', cite(('chart', 0), 'wages', 'add16'), cite('ladder', 'wages'),
              cite(bands_block, 'wages'), cite(depts_block, 'wages'), 'related',
              cite(('table', 0), 'wages', 'refused'), 'sources'],
        draft=None if ID in REG.TOPICS else dict(title='Town and school payroll', home='department-budgets'))


def render():
    return json.dumps(page(), ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text = render()
    if a.check:
        if not os.path.exists(OUT) or open(OUT, encoding='utf-8').read() != text:
            print('STALE %s' % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('town payroll: current')
        return 0
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, OUT)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
