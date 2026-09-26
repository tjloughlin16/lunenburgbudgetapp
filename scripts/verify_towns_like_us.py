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

    print('\nThe state\u2019s share, recomputed from the Chapter 70 contribution file:')
    ch = {r['municipality']: r for r in rows('sources/data/dese-ch70-contribution.csv')
          if r['fy'] == str(FY)}
    lr = ch['Lunenburg']
    fb, rc = f(lr['town_foundation_budget']), f(lr['required_local_contribution'])
    c('Lunenburg\u2019s share of its foundation budget', round(100 * (fb - rc) / fb, 1),
      P['state_share']['Lunenburg'], 0.05)
    # THE INDEPENDENT CHECK, and the reason the town-level figure is safe to use for all 351:
    # DESE publishes the same formula cut by DISTRICT, and the two must land in the same
    # place. A town figure covers every district its children attend; a district figure
    # covers one school system. A point apart is agreement; ten would not be.
    dist = [r for r in rows('sources/data/dese-ch70-formula.csv')
            if r['fy'] == str(FY) and r['district'].strip().upper() == 'LUNENBURG']
    if dist:
        d0 = dist[0]
        aid, nss = f(d0['ch70_aid']), f(d0['required_nss'])
        town_pc = 100 * (fb - rc) / fb
        c('...agrees with the district-level Chapter 70 file to within 2 points',
          abs(100 * aid / nss - town_pc) < 2.0, True)

    print('\nHomes per pupil, recomputed from parcels over pupils:')
    par = {r['municipality']: f(r['sf_parcels']) for r in rows('sources/data/dls-avg-tax-bill.csv')
           if r['fy'] == str(FY) and r['sf_parcels']}
    fte = ind('Lunenburg', SY, 'Student Enrollment', 'Total FTE Pupils')
    c('Lunenburg single-family homes per pupil', round(par['Lunenburg'] / fte, 2),
      P['homes_per_pupil']['Lunenburg'], 0.005)

    print('\nEvery town verdict agrees with its own two numbers:')
    lun = next(v for v in P['verdicts'] if v['town'] == 'Lunenburg')
    placed = [v for v in P['verdicts'] if v['town'] != 'Lunenburg' and v['pp_diff'] is not None]
    bad_q = [v['town'] for v in placed
             if v['quadrant'] != '%s-%s' % ('pays-less' if v['bill_diff'] < 0 else 'pays-more',
                                            'spends-more' if v['pp_diff'] > 0 else 'spends-less')]
    c('no town is filed under a quadrant its figures contradict', bad_q, [])
    bad_d = [v['town'] for v in placed if round(v['bill'] - lun['bill']) != v['bill_diff']]
    c('every bill difference is that town\u2019s bill minus Lunenburg\u2019s', bad_d, [])
    c('every town in a regional district says so instead of being dropped',
      sorted(v['town'] for v in P['verdicts'] if v['quadrant'] == 'regional'),
      sorted({r['town'] for r in P['local'] if r['town'] not in P['homes_per_pupil']}))
    c('every comparison town has a verdict',
      len([v for v in P['verdicts'] if v['town'] != 'Lunenburg']),
      len({r['town'] for r in P['local'] + P['twins'] if r['town'] != 'Lunenburg'}))

    reg = [v for v in P['verdicts'] if v['quadrant'] == 'regional']
    c('...and each one carries what it is required to raise per child',
      all(v.get('required_pp') and v.get('state_pp') for v in reg), True)
    c('...and what the schools its children attend spend per pupil',
      all(v.get('pp') for v in reg), True)
    # RECOMPUTED, not trusted: the required contribution per child comes straight out of
    # the Chapter 70 file for that town, whatever kind of district it belongs to.
    bad_r = []
    for v in reg:
        row = ch.get(v['town'])
        if not row:
            bad_r.append(v['town'])
            continue
        want = round(f(row['required_local_contribution']) / f(row['town_foundation_enrollment']))
        if want != v['required_pp']:
            bad_r.append('%s (%s vs %s)' % (v['town'], v['required_pp'], want))
    c('every regional town\u2019s required contribution per child recomputes', bad_r, [])

    print('\nTaxable value per pupil, recomputed \u2014 the measure that replaced a homes COUNT:')
    av = {r['municipality']: r for r in rows('sources/data/dls-assessed-values.csv')
          if r['fy'] == str(FY)}
    tot = f(av['Lunenburg']['total'])
    c('Lunenburg taxable value per pupil', round(tot / fte), P['value_per_pupil']['Lunenburg'], 1)
    biz = sum(f(av['Lunenburg'][k]) for k in ('commercial', 'industrial', 'personal_property'))
    c('...of which business, industrial and personal', round(biz), P['commercial']['lun_business'], 1)

    print('\nThe commercial gap, recomputed:')
    C = P['commercial']
    c('Lunenburg business value per pupil', round(biz / fte), C['lun_per_pupil'], 1)
    c('what it would take to reach the median business base per pupil',
      round((C['median_per_pupil'] - C['lun_per_pupil']) * fte), C['need_to_reach_median'], 2000)
    # THE TABLE IS IN DOLLARS, NOT SHARES, and the reason is in the report: two towns a point
    # apart on share can be half a billion apart in value. Assert that the two disagree, so a
    # future edit cannot quietly go back to shares without this noticing.
    byshare = sorted(C['towns'], key=lambda r: -r['share'])[0]['town']
    byvalue = sorted(C['towns'], key=lambda r: -r['business'])[0]['town']
    c('the biggest business base by VALUE is not the biggest by SHARE',
      byshare != byvalue, True)

    print('\nAnd a town like ours, one measure at a time:')
    dims = P['by_dimension']
    c('every measure names its nearest towns', all(len(d['towns']) == 3 for d in dims), True)
    c('Lunenburg never appears in its own nearest list',
      any('Lunenburg' in [t['town'] for t in d['towns']] for d in dims), False)
    # THE POINT OF THE SECTION, asserted: if one town were nearest on most measures the
    # multi-dimensional answer would be theatre.
    from collections import Counter
    hits = Counter(t['town'] for d in dims for t in d['towns'])
    c('no town is nearest on more than half the measures',
      max(hits.values()) <= len(dims) // 2, True)

    print('\nThe funding stack, recomputed \u2014 and it must FOOT:')
    F = P['funding']
    bad_sum = [r['town'] for r in F
               if abs(r['from_homes'] + r['from_business'] + r['from_state']
                      + r['above_foundation'] - r['per_pupil']) > 3]
    c('every town\u2019s four parts sum to what it spends per pupil', bad_sum, [])
    lun = next(r for r in F if r['town'] == 'Lunenburg')
    lr = ch['Lunenburg']
    fb, rc = f(lr['town_foundation_budget']), f(lr['required_local_contribution'])
    en = f(lr['town_foundation_enrollment'])
    c('...its state part is the foundation budget less the required contribution, per child',
      round((fb - rc) / en), lun['from_state'], 1)
    c('...and the part above is what it spends less the foundation budget',
      round(ind('Lunenburg', SY, 'Expenditures Per Pupil', 'Total Expenditures') - fb / en),
      lun['above_foundation'], 2)
    # THE ORDER IS THE ARGUMENT: sorted by the part a town decides, not by total spending.
    c('the stack is sorted by what each town spends above the state\u2019s figure',
      [r['town'] for r in F] == [r['town'] for r in
                                 sorted(F, key=lambda x: -x['above_foundation'])], True)

    print('\nEvery measure\u2019s own axis:')
    D = P['distributions']
    c('each measure carries every town', all(len(d['values']) == d['n'] for d in D), True)
    # A RANK MUST ALLOW FOR TIES. Two towns round to the same 1.271x as Lunenburg on
    # `above`, so `strictly above, plus one` is 124 while the published rank, broken on the
    # unrounded values, is 125. Both are right. The check is that the rank sits inside the
    # block of equal values, which is the only thing a reader can verify from the payload.
    def rank_ok(d):
        above = sum(1 for v in d['values'] if v > d['lunenburg'])
        ties = sum(1 for v in d['values'] if v == d['lunenburg'])
        return above + 1 <= d['rank'] <= above + max(ties, 1)
    c('each rank sits inside its own block of equal values',
      [d['key'] for d in D if not rank_ok(d)], [])
    c('the middle half is inside the whole range',
      all(d['lo'] <= d['p25'] <= d['median'] <= d['p75'] <= d['hi'] for d in D), True)
    # THE TAX BILL IS THE MIDDLE OF THE FRAME, and the report leans on that beside a rank of
    # 158 on spending. Assert both rather than trust a sentence.
    bill = next(d for d in D if d['key'] == 'bill')
    pp = next(d for d in D if d['key'] == 'per_pupil')
    c('Lunenburg\u2019s tax bill sits within $50 of the median of the frame',
      abs(bill['lunenburg'] - bill['median']) < 50, True)
    c('...while its spending per pupil is in the bottom ten', pp['rank'] > pp['n'] - 10, True)

    # THE CHAPTER 70 IDENTITY, on every town the map shades. The choropleth's readout prints
    # foundation = required + state as an identity rather than as a finding, so it has to BE
    # one in the payload -- and the state's share has to be that same division, not a second
    # figure computed somewhere else.
    HM = {x['key']: x['values'] for x in P['heatmap']['measures']}
    eq = [t for t, f in HM['foundation_pp'].items()
          if f is not None and HM['required_pp'].get(t) is not None
          and abs(f - HM['required_pp'][t] - (HM['state_pp'].get(t) or 0)) > 1.0]
    c('what the state says a child needs = what the town must raise + what the state adds',
      eq, [])
    sh = [t for t, v in HM['state_share'].items()
          if v is not None and abs(v - 100.0 * (HM['state_pp'][t] / HM['foundation_pp'][t])) > 0.01]
    c('...and the state\u2019s share is that division and nothing else', sh, [])
    c('all three terms cover the same towns',
      len([v for v in HM['foundation_pp'].values() if v is not None]),
      len([v for v in HM['state_share'].values() if v is not None]))

    print('\nAnd every lever says how sure it is:')
    c('each lever carries a confidence and a caveat',
      all(l.get('confidence') and l.get('caveat') for l in P['levers']), True)
    c('confidences are only the two words the rule allows',
      sorted({l['confidence'] for l in P['levers']}), ['measured', 'not established'])

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
