#!/usr/bin/env python3
"""The Monty Tech shelf: its hub and the per-pupil page.

    python3 scripts/build_monty_tech_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_monty_tech_topics.py --check   # fail if any output would change

WHY THIS EXISTS. TJ, 14-15 October 2026, after people in town said *"some districts include
their capital projects and some districts do not"* in per-pupil spending: *"we might need to
add this information to a page about the finances of Monty Tech and per pupil spending"* and
*"Monty Tech might need to become a hub?"* The hub takes /monty-tech; the long report moved to
/analysis/monty-tech.

IT COMPUTES NOTHING NEW THAT IT CAN READ INSTEAD.

  fy28/public/data/topics/monty-tech-*.json  the three Monty Tech pages build_enrolment_topics.py
                                             writes. The hub's pupils, bill and budget figures are
                                             THEIR facts, read by id, so the hub and the pages
                                             cannot round one figure two ways. Run that generator
                                             first; check_generated.py runs both.
  scripts/per_pupil_measures.py              DESE's per-pupil figure for every district, read once
                                             off DESE's workbook, with the census of function codes
                                             that shows it holds no capital or debt for anybody.

LIKE FOR LIKE. Monty Tech is a vocational high school; Lunenburg is a K-12 district. The page
leads with Monty Tech against the other regional vocational districts (DESE codes 08...), and
shows the all-district median and Lunenburg only as context. Who chose the comparison: DESE's
own district codes, not this project.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
from brief import step  # noqa: E402
import per_pupil_measures as PPM  # noqa: E402

PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT_DIR = os.path.join(PUB, 'topics')
HUB = 'monty-tech'
EOYR = '/docs/state-dese/dese-eoyr-fy2025-printing-version.xlsx'

MINE = [t for t, (_, home, gen) in REG.TOPICS.items()
        if home == HUB and gen == 'build_monty_tech_topics.py']


def fail(msg):
    raise SystemExit('build_monty_tech_topics: ' + msg)


def page_facts(tid):
    p = os.path.join(OUT_DIR, '%s.json' % tid)
    if not os.path.exists(p):
        fail('%s is not built; run build_enrolment_topics.py first' % os.path.relpath(p, ROOT))
    return {f['id']: f for f in json.load(open(p, encoding='utf-8'))['facts']}


def sources():
    return {
        'dese': dict(label='Massachusetts DESE, expenditures by function, all funds — '
                           'district-expenditures-by-function.xlsx',
                     href='/docs/' + PPM.KEY),
        'statewide': dict(label='Lunenburg Budget Project — dese-function-statewide.csv '
                                '(DESE’s statewide distribution, by function)',
                          href='/docs/data/dese-function-statewide.csv'),
        'eoyr': dict(label='Massachusetts DESE, End of Year Financial Report FY2025, printing '
                           'version — printing-version.xlsx, sheet eoy25, lines 3524-3529',
                     href=EOYR),
    }


def build():
    M = PPM.measures()
    by = {r['fy']: r for r in M['by_year']}
    y = M['last_fy']
    last = by[y]
    eq = M['equipment']
    if eq['fy'] != y:
        fail('the equipment year %s is not the per-pupil year %s' % (eq['fy'], y))
    above = [r['fy'] for r in M['by_year'] if r['vocational_median'] > r['state_median']]
    if len(above) != len(M['by_year']):
        fail('the vocational median was not above the all-district median in every year: '
             'the page says it was')
    # The finding, the hub and a conclusion say "above the all-district median, below the
    # vocational one" in words; the words are only true while these hold.
    if not last['state_median'] < last['monty'] < last['vocational_median']:
        fail('FY%d: Monty Tech is no longer between the all-district and vocational medians' % y)
    if not 2 * last['monty_rank'] > last['vocational']:
        fail('FY%d: Monty Tech is no longer in the lower half of vocational districts, which '
             'the hub says ("less than most")' % y)
    src = sources()
    S = lambda *k: [src[x] for x in k]
    U = lambda v: figure(v, C.usd(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    OF = lambda a, b: figure(a, '%d of %d' % (a, b), 'rank')
    f, con = LD.fact, TP.conclusion
    out = {}

    # ------------------------------------------------ Monty Tech per pupil
    capital_rows = sum(v for k, v in M['census'].items() if k in '678')
    years = [r['fy'] for r in M['by_year']]
    out['monty-tech-per-pupil'] = TP.page(
        'monty-tech-per-pupil',
        'Monty Tech spent %s a pupil in %s: above the all-district median, below the vocational one.'
        % (C.usd(last['monty']), C.fy(y)),
        [f('mt', U(last['monty']), 'a pupil at Monty Tech, all funds, %s' % C.fy(y), 'published',
           {'y': F(y)}),
         f('rank', OF(last['monty_rank'], last['vocational']),
           'among regional vocational districts, highest first', 'published'),
         f('vmed', U(last['vocational_median']), 'median vocational district, %s' % C.fy(y),
           'published', {'y': F(y)}),
         f('smed', U(last['state_median']), 'median of all %s districts' % C.num(last['districts']),
           'published', {'n': N(last['districts'])}),
         f('lun', U(last['lunenburg']), 'a pupil at Lunenburg, a K-12 district', 'published',
           allow=('K-12',)),
         f('eq', U(eq['monty']), 'instructional equipment a pupil at Monty Tech, counted',
           'published'),
         f('eqmed', U(eq['median']), 'the same, median vocational district', 'published'),
         f('rows', N(M['rows']), 'rows in DESE’s file, every district, %s to %s'
           % (C.fy(M['first_fy']), C.fy(y)), 'published', {'a': F(M['first_fy']), 'b': F(y)}),
         f('cap', N(capital_rows), 'of them coded capital (7000) or debt service (8000)',
           'published', allow=('7000', '8000'))],
        [con('Monty Tech spent %s a pupil in %s, ranked %s vocational districts; median %s.'
             % (C.usd(last['monty']), C.fy(y), '%d of %d' % (last['monty_rank'], last['vocational']),
                C.usd(last['vocational_median'])),
             ['mt', 'rank', 'vmed'],
             {'a': U(last['monty']), 'y': F(y), 'r': OF(last['monty_rank'], last['vocational']),
              'b': U(last['vocational_median'])}),
         con('In every year since %s the vocational median ran above the median of all districts.'
             % C.fy(M['first_fy']), ['vmed', 'smed', 'lun'], {'y': F(M['first_fy'])},
             notes=[step('So Monty Tech against Lunenburg compares a vocational high school with '
                         'a K-12 district; the like-for-like line is the vocational median.',
                         'measured', allow=('K-12',))]),
         con('None of these figures holds capital or debt: %s of %s rows carry those codes.'
             % (C.num(capital_rows), C.num(M['rows'])), ['rows', 'cap'],
             {'c': N(capital_rows), 'n': N(M['rows'])}),
         con('Instructional equipment IS counted: %s a pupil at Monty Tech, %s at the median.'
             % (C.usd(eq['monty']), C.usd(eq['median'])), ['eq', 'eqmed'],
             {'a': U(eq['monty']), 'b': U(eq['median'])},
             notes=[step('DESE’s form puts vocational equipment in 2420 “irrespective of unit '
                         'cost”, inside the per-pupil figure.', 'quote', allow=('2420',),
                         cite=(EOYR, 'DESE End of Year Report form, lines 3524-3529')),
                    step('Whether every district codes the same purchase the same way is not '
                         'visible in DESE’s data.', 'gap', allow=('7000',),
                         closes='each district’s End of Year Financial Report workbook, with its '
                                '7000 and lease schedules')])],
        chart=TP.series('Spending a pupil, Monty Tech and the medians', [C.fy(v) for v in years], [
            TP.track('Monty Tech', [by[v]['monty'] for v in years]),
            TP.track('Median vocational district', [by[v]['vocational_median'] for v in years]),
            TP.track('Median of all districts', [by[v]['state_median'] for v in years]),
            TP.track('Lunenburg', [by[v]['lunenburg'] for v in years]),
        ], '$', note='DESE, all funds, over total pupils, reported after each year closed. No '
                     'capital or debt service in any of them.'),
        table=dict(caption='Spending a pupil, by year', views=[dict(
            key='by-year', label='DESE, all funds',
            note='Monty Tech ranked among the regional vocational districts DESE codes 08, '
                 'highest first.',
            columns=['Monty Tech', 'Rank', 'Vocational median', 'All-district median',
                     'Lunenburg'],
            kinds=['ledger'] * 5,
            rows=[dict(label=C.fy(v), cells=[
                C.usd(by[v]['monty']), '%d of %d' % (by[v]['monty_rank'], by[v]['vocational']),
                C.usd(by[v]['vocational_median']), C.usd(by[v]['state_median']),
                C.usd(by[v]['lunenburg'])]) for v in reversed(years)])]),
        sources=S('dese', 'statewide', 'eoyr'),
        finding_figures={'a': U(last['monty']), 'y': F(y)})

    # ------------------------------------------------ the hub
    en, asmt, fund = (page_facts('monty-tech-%s' % t) for t in ('enrolment', 'assessment', 'funding'))
    V = lambda facts, k: facts[k]['value']
    parts = [('State Chapter 70 aid', V(fund, 'ch70')['value']),
             ('The member towns', V(fund, 'towns')['value']),
             ('State transportation aid', V(fund, 'aid')['value']),
             ('Its own reserves', V(fund, 'ed')['value'] + V(fund, 'rtf')['value'])]
    if round(sum(v for _, v in parts), 2) != V(fund, 'budget')['value']:
        fail('the four payers no longer add up to the operating budget on monty-tech-funding')
    h = {}
    h['h-hc'] = f('h-hc', V(en, 'hc'), en['hc']['label']['text'], 'published',
                  en['hc']['label']['figures'], en['hc']['label']['literals'])
    h['h-all'] = f('h-all', V(en, 'w1'), en['w1']['label']['text'], 'published',
                   en['w1']['label']['figures'], en['w1']['label']['literals'])
    h['h-towns'] = f('h-towns', V(en, 'towns'), en['towns']['label']['text'], 'published')
    h['h-bill'] = f('h-bill', V(asmt, 'bill'), asmt['bill']['label']['text'], 'published',
                    asmt['bill']['label']['figures'], asmt['bill']['label']['literals'])
    h['h-share'] = f('h-share', V(asmt, 'share'), asmt['share']['label']['text'], 'published')
    h['h-next'] = f('h-next', V(asmt, 'next'), asmt['next']['label']['text'], 'published',
                    asmt['next']['label']['figures'], asmt['next']['label']['literals'])
    h['h-budget'] = f('h-budget', V(fund, 'budget'), fund['budget']['label']['text'], 'published',
                      fund['budget']['label']['figures'], fund['budget']['label']['literals'])
    h['h-ch70'] = f('h-ch70', V(fund, 'ch70'), fund['ch70']['label']['text'], 'published',
                    allow=('Chapter 70',))
    h['h-pp'] = f('h-pp', U(last['monty']), 'a pupil, all funds, %s' % C.fy(y), 'published',
                  {'y': F(y)})
    h['h-vmed'] = f('h-vmed', U(last['vocational_median']), 'median vocational district',
                    'published')
    h['h-cap'] = f('h-cap', N(capital_rows), 'capital or debt rows in DESE’s per-pupil data',
                   'published')
    tiers = [
        LD.tier('Lunenburg’s pupils and its bill', [h['h-hc'], h['h-all'], h['h-towns'],
                                                    h['h-bill'], h['h-share'], h['h-next']]),
        LD.tier('Who pays for the school', [h['h-budget'], h['h-ch70']]),
        LD.tier('A pupil', [h['h-pp'], h['h-vmed'], h['h-cap']]),
    ]
    hc, w1, bill, share = V(en, 'hc'), V(en, 'w1'), V(asmt, 'bill'), V(asmt, 'share')
    ch70, budget = V(fund, 'ch70'), V(fund, 'budget')
    hub_ladder = LD.ladder(tiers, [
        LD.conclusion('%s of Monty Tech’s %s pupils lived in Lunenburg.'
                      % (hc['text'], w1['text']), ['h-hc', 'h-all'], {'a': hc, 'b': w1}),
        LD.conclusion('Lunenburg’s bill was %s; %s of it is a minimum the state formula sets.'
                      % (bill['text'], share['text']), ['h-bill', 'h-share', 'h-next'],
                      {'a': bill, 'b': share}),
        LD.conclusion('State Chapter 70 aid paid %s of the %s operating budget.'
                      % (ch70['text'], budget['text']), ['h-ch70', 'h-budget'],
                      {'a': ch70, 'b': budget}, allow=('Chapter 70',)),
        LD.conclusion('It spent %s a pupil, below the vocational median of %s, and none of it '
                      'capital.' % (C.usd(last['monty']), C.usd(last['vocational_median'])),
                      ['h-pp', 'h-vmed', 'h-cap'],
                      {'a': U(last['monty']), 'b': U(last['vocational_median'])}),
    ])
    out[HUB] = TP.hub(
        HUB,
        'Monty Tech is the regional vocational high school Lunenburg belongs to. Lunenburg’s bill '
        'was %s, most of it a minimum the state sets; the school spent %s a pupil in %s, less '
        'than most vocational districts.' % (bill['text'], C.usd(last['monty']), C.fy(y)),
        hub_ladder,
        chart=TP.parts('Who pays for Monty Tech’s operating budget', parts, '$',
                       note='The district’s own budget summary for the year. Capital and grants '
                            'are outside it.'),
        answer_figures={'a': bill, 'b': U(last['monty']), 'y': F(y)})

    if sorted(k for k in out if k != HUB) != sorted(MINE):
        fail('the pages built are not the pages the registry gives this script: %s'
             % sorted(set(MINE) ^ set(out)))
    return out


def outputs():
    return {os.path.join(OUT_DIR, '%s.json' % t):
            json.dumps(p, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
            for t, p in build().items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    outs = outputs()
    if a.check:
        stale = [os.path.relpath(p, ROOT) for p, text in outs.items()
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != text]
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('monty tech topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
