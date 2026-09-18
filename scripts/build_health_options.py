#!/usr/bin/env python3
"""What the town may lawfully do about health insurance, and what every other town spends.

    python3 scripts/build_health_options.py           # write fy28/public/data/health-options.json
    python3 scripts/build_health_options.py --check

TJ, 18 September 2026: "I'm not following the options in terms of which insurance is
available, at what %, etc etc" -- and, on the law: "we cannot break the law or let people
and need to tell them why it can't go below that."

TWO DATASETS, ONE PAYLOAD.

`sources/data/health-insurance-law.csv` is the menu: one row per thing a Massachusetts
town can or cannot do, each with the section that permits or forbids it, who decides, the
threshold, and who the change lands on. Every row links to the statute on
malegislature.gov, so a reader can check the sentence rather than take ours. The research
behind it is notes/findings/MA-MUNICIPAL-HEALTH-INSURANCE.md.

`sources/data/dls-health-insurance.csv` is what every municipality in the Commonwealth
actually spent, FY2002 onward, from Schedule A via the DLS Gateway.

AND THE COMPARISON IS NOT AS SIMPLE AS THE FILE LOOKS. DLS prints its own warning: for a
SELF-INSURED town the figure includes the EMPLOYEE share, and a town accounting through a
trust may have workers' compensation and OPEB inside it -- and nothing in the export says
which town is which. So this payload ranks towns on GROWTH, where a level difference in
what the figure contains cancels, and says so on the page. Lunenburg is fully insured
through the MIIA joint purchase group, so its own figure is the town's premium share.
"""
import argparse
import csv
import io
import json
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
LAW = os.path.join(ROOT, 'sources', 'data', 'health-insurance-law.csv')
SPEND = os.path.join(ROOT, 'sources', 'data', 'dls-health-insurance.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'health-options.json')
TOWN = 'Lunenburg'
SPAN = 10          # years over which growth is compared
BANDS = [(-100, 0), (0, 2), (2, 4), (4, 6), (6, 8), (8, 10), (10, 100)]
NEIGHBOURS = ['Lunenburg', 'Ayer', 'Groton', 'Littleton', 'Shirley', 'Townsend',
              'Westford', 'Leominster', 'Fitchburg', 'Lancaster', 'Harvard']


def rows(p):
    with io.open(p, encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def series():
    by = {}
    for r in rows(SPEND):
        if r['expenditure'] == '':
            continue
        by.setdefault(r['municipality'], {})[int(r['fy'])] = float(r['expenditure'])
    if TOWN not in by:
        raise SystemExit('no %s in %s' % (TOWN, os.path.relpath(SPEND, ROOT)))
    return by


def cagr(a, b, years):
    return (b / a) ** (1.0 / years) - 1 if a > 0 and b > 0 and years else None


def build():
    by = series()
    latest = max(by[TOWN])
    first = latest - SPAN
    peers = []
    for town, s in by.items():
        if first in s and latest in s and s[first] > 0:
            g = cagr(s[first], s[latest], SPAN)
            if g is not None:
                peers.append(dict(municipality=town, first=s[first], last=s[latest], growth=round(100 * g, 2)))
    peers.sort(key=lambda p: p['growth'])
    if len(peers) < 300:
        raise SystemExit('only %d municipalities have both FY%d and FY%d' % (len(peers), first, latest))
    me = next(p for p in peers if p['municipality'] == TOWN)
    rank = peers.index(me) + 1
    growths = [p['growth'] for p in peers]
    law = rows(LAW)
    if not any(r['available_to_lunenburg'] == 'no' for r in law):
        raise SystemExit('the law file lists nothing the town cannot do; that is not this statute')
    return dict(
        generated_by='scripts/build_health_options.py',
        about='What Massachusetts law lets a town do about health insurance, what each option costs somebody, and what every municipality in the Commonwealth has spent since FY2002.',
        grain='LAW as the statute states it, linked section by section; DOLLARS as each town filed them on Schedule A. The spending figure is a net appropriation and is not the same quantity in every town — see `comparison_caveat`.',
        research='notes/findings/MA-MUNICIPAL-HEALTH-INSURANCE.md',
        options=law,
        can=[r['id'] for r in law if r['available_to_lunenburg'] != 'no'],
        cannot=[r['id'] for r in law if r['available_to_lunenburg'] == 'no'],
        town=dict(
            municipality=TOWN, fy=latest, spent=by[TOWN][latest],
            series=[dict(fy=fy, spent=by[TOWN][fy]) for fy in sorted(by[TOWN])],
            growth=me['growth'], rank=rank, of=len(peers),
            median_growth=round(statistics.median(growths), 2),
            faster_than_median=round(me['growth'] - statistics.median(growths), 2),
        ),
        peers=dict(
            span_years=SPAN, from_fy=first, to_fy=latest, count=len(peers),
            fastest=peers[-8:][::-1], slowest=peers[:8], all=peers,
            # THE DISTRIBUTION, for the chart: how many towns fall in each band of annual
            # growth, and which band holds Lunenburg. A rank alone ("301 of 343") tells a
            # reader where the town sits and not whether the pack is tight or spread.
            histogram=[dict(band=b, low=lo, high=hi,
                            towns=sum(1 for p in peers if lo <= p['growth'] < hi),
                            has_town=lo <= me['growth'] < hi)
                       for b, (lo, hi) in enumerate(BANDS)],
        ),
        # THE NEIGHBOURS, year by year, for the lines on the chart. The eleven the rest of
        # this project compares against (scripts/fetch_dls_tax_bills.TOWNS), each as its own
        # series so a reader can see whose curve bends and whose does not.
        neighbours=[dict(municipality=t, series=[dict(fy=fy, spent=by[t][fy]) for fy in sorted(by[t])])
                    for t in NEIGHBOURS if t in by],
        comparison_caveat=(
            'DLS prints two warnings on this report and both bite. For a SELF-INSURED town the figure '
            'includes the employee share, and a town accounting through a trust may have workers’ '
            'compensation and OPEB inside it — and nothing in the file says which town is which. So the '
            'LEVEL is not comparable across towns; the GROWTH is, because whatever a town’s figure '
            'contains it contains in both years. Lunenburg is fully insured through the MIIA joint '
            'purchase group, so its figure is the town’s premium share alone.'),
        sources=[
            dict(title='Health Insurance Expenditures, every municipality, FY2002 onward',
                 publisher='Massachusetts Division of Local Services',
                 url='https://dls-gw.dor.state.ma.us/reports/rdPage.aspx?rdReport=ScheduleA.HealthInsurance.HealthInsExpenditures',
                 local='sources/data/dls-health-insurance.csv'),
            dict(title='M.G.L. Chapter 32B — municipal group insurance', publisher='The General Court',
                 url='https://malegislature.gov/Laws/GeneralLaws/PartI/TitleIV/Chapter32B',
                 local='sources/data/health-insurance-law.csv'),
        ],
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    d = build()
    text = json.dumps(d, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
    if a.check:
        if not os.path.exists(OUT) or open(OUT, encoding='utf-8').read() != text:
            raise SystemExit('STALE %s — run: python3 scripts/build_health_options.py' % os.path.relpath(OUT, ROOT))
        print('ok — %d options, %d municipalities compared' % (len(d['options']), d['peers']['count']))
        return
    open(OUT, 'w', encoding='utf-8').write(text)
    t = d['town']
    print('wrote %s: %d options (%d the town cannot do); %s FY%d $%s, growth %.2f%%/yr over %d years — %d of %d, median %.2f%%'
          % (os.path.relpath(OUT, ROOT), len(d['options']), len(d['cannot']), t['municipality'], t['fy'],
             format(int(t['spent']), ','), t['growth'], SPAN, t['rank'], t['of'], t['median_growth']))


if __name__ == '__main__':
    main()
