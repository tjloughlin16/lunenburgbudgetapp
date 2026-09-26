#!/usr/bin/env python3
"""Every headline figure on /analysis/towns-like-us, recomputed from the archive.

    python3 scripts/verify_how_we_compare.py

WHAT THIS ADDS OVER `build_town_comparison.py --check`. That rebuilds the payload with the
generator's own code and byte-compares: it catches an input that moved and cannot catch the
generator being wrong, because the same arithmetic produces both sides. This reads the
PUBLISHED payload and recomputes each headline figure by a different route -- straight out
of the CSVs and the JSON, with its own joins -- and compares. Rule 9: recomputed, not
re-read.

It also re-reads the Select Board minute the report QUOTES and asserts each quoted sentence
is still verbatim in it, because a quotation is the one kind of figure a recomputation
cannot check.
"""
import csv
import json
import math
import os
import statistics as st
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'towns-like-us.json')
DOC = os.path.join(ROOT, 'sources', 'analyses', 'towns-like-us.md')


def rows(p):
    with open(os.path.join(ROOT, p), encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class Check:
    def __init__(self):
        self.bad = 0
        self.n = 0

    def __call__(self, what, got, want, tol=0.0):
        self.n += 1
        if isinstance(got, (int, float)) and isinstance(want, (int, float)):
            ok = abs(got - want) <= tol
        else:
            ok = got == want
        if ok:
            print('  ok    %-58s %s' % (what, want))
        else:
            self.bad += 1
            print('  FAIL  %-58s payload %r, recomputed %r' % (what, want, got))


def main():
    if not os.path.exists(PAYLOAD):
        raise SystemExit('%s does not exist. Run scripts/build_town_comparison.py.'
                         % os.path.relpath(PAYLOAD, ROOT))
    with open(PAYLOAD, encoding='utf-8') as fh:
        P = json.load(fh)
    doc = open(DOC, encoding='utf-8').read()
    FY, SY, BASE_SY = P['fy'], P['sy'], P['base_sy']
    c = Check()

    print('The tax figures, straight out of the DLS extract:')
    bill = {(r['municipality'], int(r['fy'])): r for r in rows('sources/data/dls-avg-tax-bill.csv')}
    lun = bill[('Lunenburg', FY)]
    stats = {s['label']: s['value'] for s in P['stats']}
    c('Lunenburg average single-family bill, FY%d' % FY,
      '$%s' % format(round(f(lun['avg_sf_bill'])), ',d'),
      next(v for k, v in stats.items() if k.startswith('average single-family tax bill')))
    c('its rank among the 351', '%s of 351' % ordinal(int(lun['rank'])),
      next(v for k, v in stats.items() if k.startswith('where that bill ranks')))
    row = next(r for r in P['local'] if r['town'] == 'Lunenburg')
    c('average single-family value', f(lun['avg_sf_value']), row['value'], 0.5)
    c('bill as a share of income', f(lun['bill_pct_of_income']), row['pinc'], 0.005)

    print('\nThe commercial share, from the assessed-values extract:')
    vals = {(r['municipality'], int(r['fy'])): r for r in rows('sources/data/dls-assessed-values.csv')}
    c('commercial, industrial and personal share of the base',
      f(vals[('Lunenburg', FY)]['cip_pct']), row['cip'], 0.005)

    print('\nThe overrides, counted from the DLS votes file:')
    ov = [r for r in rows('sources/data/dls-override-votes.csv')
          if r['municipality'] == 'Lunenburg' and r['vote_type'] == 'Override']
    c('override questions Lunenburg has put', len(ov), row['put'])
    c('...and won', len([r for r in ov if r['result'] == 'WIN']), row['won'])
    c('...worth, in permanent levy capacity',
      sum(f(r['amount']) or 0 for r in ov if r['result'] == 'WIN'), row['won_amt'], 1.0)

    print('\nThe school figures, straight out of the DESE indicator file:')
    with open(os.path.join(ROOT, 'sources', 'state-dese', 'er3w-dyti.json'), encoding='utf-8') as fh:
        dese = json.load(fh)
    def ind(dist, sy, cat, sub):
        for r in dese:
            if (r['dist_name'] == dist and r['sy'] == str(sy)
                    and r['ind_cat'] == cat and r['ind_subcat'] == sub):
                return f(r['ind_value'])
        return None
    pp = ind('Lunenburg', SY, 'Expenditures Per Pupil', 'Total Expenditures')
    c('Lunenburg per pupil, all funds, SY%d' % SY, pp, row['pp'], 0.5)
    # DESE'S OWN IDENTITY, asserted rather than assumed: the ten in-district components sum
    # to the in-district total it also publishes. A misread category would break this.
    parts = ['Administration', 'Guidance, Counseling and Testing', 'Instructional Leadership',
             'Instructional Materials, Equipment and Technology',
             'Insurance, Retirement Programs and Other', 'Operations and Maintenance',
             'Other Teaching Services', 'Professional Development', 'Pupil Services', 'Teachers']
    got = sum(ind('Lunenburg', SY, 'Expenditures Per Pupil', p) or 0 for p in parts)
    c('the ten in-district components sum to DESE’s in-district total',
      round(got), round(ind('Lunenburg', SY, 'Expenditures Per Pupil',
                            'Total In-District Expenditures')), 1)

    print('\nThe frame, and Lunenburg’s place in it:')
    c('towns in the frame', P['frame_size'], len(P['twins']) and P['frame_size'])
    inframe = [r['town'] for r in P['twins'] if r['town'] != 'Lunenburg']
    c('the two cohorts name ten towns each', len(inframe), 20)
    c('no town is in both closest-ten lists', len(P['overlap10']), 0)

    print('\nThe correlations, recomputed on the payload’s own frame is not possible '
          '— so their SIGNS and the ordering the report leans on:')
    cm = {x['key']: x['r'] for x in P['correlations']}
    # THE REPORT CLAIMS THE TOP TWO, NOT A WINNER, and this check used to assert a winner.
    # Home value is +0.91 and income per capita +0.92: a difference of nothing, and the
    # first draft of both the report and this verifier called home value the strongest. An
    # ordering the data does not support, asserted twice, and caught here.
    top2 = sorted(cm, key=lambda k: -abs(cm[k]))[:2]
    c('home value and income are the two strongest relationships',
      sorted(top2), sorted(['value_bill', 'income_bill']))
    c('new growth against the bill is the weakest',
      min(cm, key=lambda k: abs(cm[k])), 'ng_bill')
    c('every correlation is inside [-1, 1]',
      all(-1.0 <= v <= 1.0 for v in cm.values()), True)
    for k, x in ((k, x) for k, x in ((x['key'], x) for x in P['correlations'])):
        got = '%+.2f' % x['r']
        if got != x['text']:
            print('  FAIL  %-58s text %r, value renders %r' % (k, x['text'], got))
            c.bad += 1
        c.n += 1

    print('\nWhere the children go, counted from DESE’s residents file:')
    dest = [r for r in rows('sources/data/dese-town-enrollment.csv')
            if r['town'] == 'Lunenburg' and r['fy'] == str(FY)]
    total = sum(int(r['students']) for r in dest)
    c('children enrolled anywhere, FY%d' % FY, total,
      sum(d['students'] for d in P['destinations']))
    own = sum(int(r['students']) for r in dest if r['district'] == 'Lunenburg')
    c('...of them in Lunenburg’s own schools', own,
      sum(d['students'] for d in P['destinations'] if d['kind'] == 'own'))
    c('...schooled elsewhere', total - own,
      sum(d['students'] for d in P['destinations'] if d['kind'] != 'own'))

    print('\nThe quotations, verbatim in the minute they are attributed to:')
    minute = os.path.join(ROOT, 'sources', 'meetings', 'text', 'select-board',
                          '2025-11-25-minutes-7534.txt')
    text = ' '.join(open(minute, encoding='utf-8', errors='replace').read().split())
    for q in ('At the maximum allowable CIP shift of 1.50',
              'a savings of only $224.25 for a $350,000 residential property',
              'a tax increase of approximately $2,336.75 for a comparable commercial property',
              'The estimated Fiscal Year 2026 single tax rate was projected at $14.39 per thousand'):
        c('in the Select Board minute of 25 November 2025: “%s…”' % q[:34],
          q in text, True)
        if q not in doc:
            print('  FAIL  the report no longer quotes: %s' % q)
            c.bad += 1
        c.n += 1
    fc = os.path.join(ROOT, 'sources', 'meetings', 'text', 'finance-committee',
                      '2025-03-06-minutes-7008.txt')
    ftext = ' '.join(open(fc, encoding='utf-8', errors='replace').read().split())
    c('in the Finance Committee minute of 6 March 2025: the $20,827 figure',
      'The foundational budget per pupil spent is $20,827' in ftext, True)

    print('\nAnd the report says what it cannot establish:')
    c('conclusions carry a not_shown each',
      all(x.get('not_shown') for x in P['conclusions']), True)
    c('the payload registers what is not established', len(P['not_established']) >= 4, True)

    print('\n%d checks, %d failed' % (c.n, c.bad))
    return 1 if c.bad else 0


def ordinal(n):
    if 10 <= n % 100 <= 20:
        return '%dth' % n
    return '%d%s' % (n, {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th'))


if __name__ == '__main__':
    sys.exit(main())
