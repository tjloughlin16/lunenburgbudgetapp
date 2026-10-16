#!/usr/bin/env python3
"""The Bromfield shelf: its hub, Harvard per pupil, Harvard line by line, and Lunenburg at
Harvard's rate. Harvard Public Schools (DESE LEA 01250000) is the district The Bromfield School
(01250505) belongs to.

    python3 scripts/build_bromfield_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_bromfield_topics.py --check   # fail if any output would change

WHY THIS EXISTS. TJ, 15 October 2026: "Can you build a hub and similar pages for Bromfield as we
have for Monty Tech" -- a BENCHMARK comparison, then narrowed: "I just mean a comparison, per
pupil spend comparison, how that breaks down, you know, that kind of thing." Harvard is a
neighbouring K-12 district that spends well above the state median; Lunenburg pays it nothing
beyond a few school choice tuitions. So this is what a neighbour spends, set beside Lunenburg,
like for like: both are K-12 districts, on DESE's one all-funds measure.

IT COMPUTES NOTHING NEW THAT IT CAN READ INSTEAD.

  scripts/per_pupil_measures.py      DESE's per-pupil figure for every district (measures()) and
                                     each district split into DESE's categories and footed to
                                     DESE's own total (breakdown()) -- the same code the Monty
                                     Tech and School spending shelves draw.
  fy28/public/data/high-schools.json build_high_schools.py: DESE's SCHOOL-level figure for The
                                     Bromfield School's high school and Lunenburg High, only in
                                     years each enrolled grades 9-12 and nothing below.
  fy28/public/data/peer-spending.json build_peer_spending.py: who each district serves (low
                                     income, from RADAR), and its not_established limit, quoted.
  fy28/public/data/topics/cost-of-the-median.json
                                     build_school_spending_topics.py: Lunenburg at the state
                                     median. READ, so the site carries one figure for it.

Rule 7: Harvard serves a smaller low-income share than Lunenburg, and nothing here separates
spending from population, size or anything else. Rule 8: this is what a benchmark spends, for
planning, never what Lunenburg got wrong.
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
HUB = 'bromfield'
BROMFIELD_HS, LUNENBURG_HS = '01250505', '01620505'

MINE = [t for t, (_, home, gen) in REG.TOPICS.items()
        if home == HUB and gen == 'build_bromfield_topics.py']


def fail(msg):
    raise SystemExit('build_bromfield_topics: ' + msg)


def load(name):
    p = os.path.join(PUB, name)
    if not os.path.exists(p):
        fail('%s is not built' % os.path.relpath(p, ROOT))
    return json.load(open(p, encoding='utf-8'))


def sources():
    return {
        'dese': dict(label='Massachusetts DESE, expenditures by function, all funds — '
                           'district-expenditures-by-function.xlsx',
                     href='/docs/' + PPM.KEY),
        'statewide': dict(label='Lunenburg Budget Project — dese-function-statewide.csv '
                                '(DESE’s statewide distribution, by function)',
                          href='/docs/data/dese-function-statewide.csv'),
        'radar': dict(label='Lunenburg Budget Project — dese-radar.csv (DESE’s FTE pupil counts '
                            'and student demographics, from RADAR)',
                      href='/docs/data/dese-radar.csv'),
        'school': dict(label='Massachusetts DESE, school expenditures by spending category — '
                             'school-expenditures-by-spending-category.xlsx',
                       href='/docs/state-dese/school-expenditures-by-spending-category.xlsx'),
    }


def build():
    M = PPM.measures()
    by = {r['fy']: r for r in M['by_year']}
    years = [r['fy'] for r in M['by_year']]
    y, y0 = M['last_fy'], M['first_fy']
    last, first = by[y], by[y0]
    # The words "above the state median every year" and "below it every year" are only true
    # while these hold.
    if not all(by[v]['harvard'] > by[v]['state_median'] for v in years):
        fail('Harvard was not above the state median in every year; the page says it was')
    if not all(by[v]['lunenburg'] < by[v]['state_median'] for v in years):
        fail('Lunenburg was not below the state median in every year; the page says it was')
    gap = {v: by[v]['harvard'] - by[v]['lunenburg'] for v in years}
    if not gap[y] > gap[y0] > 0:
        fail('the gap no longer widened from %s to %s, which the hub says' % (y0, y))

    src = sources()
    S = lambda *k: [src[x] for x in k]
    U = lambda v: figure(v, C.usd(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    P = lambda v: figure(v, C.pct(v, 1))
    OF = lambda a, b: figure(a, '%d of %d' % (a, b), 'rank')
    PU = lambda v: figure(v, '{:,.1f}'.format(v), 'FTE pupils')
    f, con = LD.fact, TP.conclusion
    yl = {'y': F(y)}
    out = {}

    # ---- who each district serves: peer-spending.json, the same FY as the spending
    peer = load('peer-spending.json')
    if peer['fin_fy'] != y:
        fail('peer-spending.json demographics are FY%s, the spending FY%s' % (peer['fin_fy'], y))
    demo = {d['district']: d for d in peer['demographics']}
    li_h, li_l = 100 * demo['Harvard']['low_income'], 100 * demo['Lunenburg']['low_income']
    if not li_h < li_l:
        fail('Harvard no longer serves a smaller low-income share than Lunenburg')
    limit = next((s for s in peer['not_established'] if 'cannot separate' in s), None)
    QUOTE = 'a six-district cross-section cannot separate that from anything else'
    if not limit or QUOTE not in limit:
        fail('peer-spending.json no longer states the limit this shelf quotes')

    # ---- the school-level figure, Bromfield's high school and Lunenburg High
    hs = {s['code']: s for s in load('high-schools.json')['spending']['schools']}
    bh, lh = hs[BROMFIELD_HS]['years'], hs[LUNENBURG_HS]['years']
    if not (bh[str(y)]['grades_9_12_only'] and lh[str(y)]['grades_9_12_only']):
        fail('FY%d: one of the two high schools did not enrol grades 9-12 only' % y)
    like = sorted(int(v) for v in bh if bh[v]['grades_9_12_only'] and lh.get(v, {}).get('grades_9_12_only'))
    bs, ls = bh[str(y)]['total'], lh[str(y)]['total']

    # ------------------------------------------------ Harvard per pupil
    out['harvard-per-pupil'] = TP.page(
        'harvard-per-pupil',
        'Harvard spent %s a pupil in %s, %s more than Lunenburg, on DESE’s all-funds measure.'
        % (C.usd(last['harvard']), C.fy(y), C.usd(gap[y])),
        [f('har', U(last['harvard']), 'a pupil at Harvard, all funds, %s' % C.fy(y), 'published', yl),
         f('lun', U(last['lunenburg']), 'a pupil at Lunenburg, the same measure', 'published'),
         f('gap', U(gap[y]), 'more a pupil at Harvard', 'published'),
         f('smed', U(last['state_median']), 'median of all %s districts' % C.num(last['districts']),
           'published', {'n': N(last['districts'])}),
         f('gap0', U(gap[y0]), 'the same gap in %s' % C.fy(y0), 'published', {'y': F(y0)}),
         f('hrank', OF(last['harvard_rank'], last['districts']), 'Harvard among districts, '
           'highest first', 'published'),
         f('lrank', OF(last['lunenburg_rank'], last['districts']), 'Lunenburg, the same ranking',
           'published'),
         f('brom', U(bs), 'a pupil at Bromfield’s high school, %s' % C.fy(y), 'published', yl),
         f('lhs', U(ls), 'at Lunenburg High, the same school-level measure', 'published'),
         f('li', P(li_h), 'of Harvard’s students low-income; Lunenburg %s' % C.pct(li_l, 1),
           'published', {'l': P(li_l)})],
        [con('Harvard spent %s a pupil in %s, %s more than Lunenburg’s %s.'
             % (C.usd(last['harvard']), C.fy(y), C.usd(gap[y]), C.usd(last['lunenburg'])),
             ['har', 'lun', 'gap'],
             {'a': U(last['harvard']), 'y': F(y), 'g': U(gap[y]), 'b': U(last['lunenburg'])}),
         con('The gap was %s in %s. Harvard ran above the state median every year, Lunenburg '
             'below.' % (C.usd(gap[y0]), C.fy(y0)), ['gap0', 'smed', 'hrank', 'lrank'],
             {'g': U(gap[y0]), 'y': F(y0)}),
         con('School by school, Bromfield’s high school spent %s a pupil, Lunenburg High %s.'
             % (C.usd(bs), C.usd(ls)), ['brom', 'lhs'], {'a': U(bs), 'b': U(ls)},
             notes=[step('A school-level figure is a different measure from the district one: '
                         'the school’s own spending plus a share of the district’s.', 'measured'),
                    step('Compared only in %s and %s; before that Bromfield’s code also '
                         'enrolled grades below 9.' % (C.fy(like[0]), C.fy(like[-1])), 'measured',
                         {'a': F(like[0]), 'b': F(like[-1])}, allow=('grades below 9',))]),
         con('Harvard’s students were %s low-income, Lunenburg’s %s: the two serve different '
             'populations.' % (C.pct(li_h, 1), C.pct(li_l, 1)), ['li'],
             {'a': P(li_h), 'b': P(li_l)},
             notes=[step('“%s%s.” Spending is not shown here to cause any result.'
                         % (QUOTE[0].upper(), QUOTE[1:]), 'quote',
                         cite=('/data/peer-spending.json', 'Spending compared, what it does not '
                                                          'establish'))])],
        chart=TP.series('Spending a pupil, Harvard and Lunenburg', [C.fy(v) for v in years], [
            TP.track('Harvard', [by[v]['harvard'] for v in years]),
            TP.track('Median of all districts', [by[v]['state_median'] for v in years]),
            TP.track('Lunenburg', [by[v]['lunenburg'] for v in years]),
        ], '$', note='DESE, all funds, over total pupils, reported after each year closed. Both '
                     'are K-12 districts. No capital or debt service in any of them.',
            note_allow=('K-12',)),
        table=dict(caption='Spending a pupil, by year', views=[
            dict(key='by-year', label='District, DESE, all funds',
                 note='Ranked among every district DESE prints a figure for, highest first.',
                 columns=['Harvard', 'Rank', 'Lunenburg', 'Rank', 'State median', 'Gap'],
                 kinds=['ledger'] * 6,
                 rows=[dict(label=C.fy(v), cells=[
                     C.usd(by[v]['harvard']), '%d of %d' % (by[v]['harvard_rank'], by[v]['districts']),
                     C.usd(by[v]['lunenburg']), '%d of %d' % (by[v]['lunenburg_rank'], by[v]['districts']),
                     C.usd(by[v]['state_median']), C.usd(gap[v])]) for v in reversed(years)]),
            dict(key='school', label='High school, school level',
                 note='DESE’s school-level figure, Total A+B+C, only in years both schools '
                      'enrolled grades 9-12 and nothing below.',
                 columns=['Bromfield high school', 'Lunenburg High', 'Gap'],
                 kinds=['ledger'] * 3,
                 rows=[dict(label=C.fy(v), cells=[
                     C.usd(bh[str(v)]['total']), C.usd(lh[str(v)]['total']),
                     C.usd(bh[str(v)]['total'] - lh[str(v)]['total'])]) for v in reversed(like)])]),
        sources=S('dese', 'statewide', 'school', 'radar'),
        finding_figures={'a': U(last['harvard']), 'y': F(y), 'g': U(gap[y])})

    # ------------------------------------------------ Harvard, line by line
    # The twin of /monty-tech/monty-tech-line-by-line: the same split, footed the same way.
    hb = PPM.breakdown(PPM.HARVARD, y)
    lb = PPM.breakdown(PPM.LUNENBURG, y)
    if hb['pp'] != last['harvard'] or lb['pp'] != last['lunenburg']:
        fail('the line-by-line totals are not the per-pupil figures this shelf prints')
    hcat = {c['code']: c for c in hb['cats']}
    lcat = {c['code']: c for c in lb['cats']}
    if [c['code'] for c in sorted(hb['cats'], key=lambda c: -c['pp'])[:2]] != ['TCHR', 'BENE']:
        fail('teachers then insurance are no longer Harvard’s two largest categories')
    diffs = {k: hcat[k]['pp'] - (lcat[k]['pp'] if k in lcat else 0) for k in hcat}
    if max(diffs, key=diffs.get) != 'TCHR':
        fail('teachers are no longer the widest category gap between Harvard and Lunenburg')
    if abs(sum(diffs.values()) + sum(lcat[k]['pp'] for k in lcat if k not in hcat)
           - (hb['total'] / hb['fte_total'] - lb['total'] / lb['fte_total'])) > 0.01:
        fail('the category gaps no longer add to the gap between the totals a pupil')
    t2305 = next(r for r in hb['lines'] if r['code'] == '2305' and r['where'] == 'In-District')
    if max(hb['lines'], key=lambda r: r['grants']) is not t2305:
        fail('classroom teachers are no longer the largest line Harvard’s grants and revolving '
             'funds paid')
    gsh, lgsh = 100.0 * hb['grants'] / hb['total'], 100.0 * lb['grants'] / lb['total']
    tc, be = hcat['TCHR'], hcat['BENE']
    out['harvard-line-by-line'] = TP.page(
        'harvard-line-by-line',
        'Harvard’s %s a pupil in %s by what it bought: teachers first, %s paid by grants and '
        'revolving.' % (C.usd(hb['pp']), C.fy(y), C.pct(gsh, 1)),
        [f('pp', U(hb['pp']), 'a pupil, all funds, %s, DESE' % C.fy(y), 'published', yl),
         f('total', U(hb['total']), 'spent, all funds, %s' % C.fy(y), 'published', yl),
         f('fte', PU(hb['fte_total']), 'FTE pupils DESE divides by', 'published'),
         f('tchr', U(tc['pp']), 'teachers, a pupil (our division)', 'published'),
         f('bene', U(be['pp']), 'insurance, retirement and other, a pupil', 'published'),
         f('tgap', U(diffs['TCHR']), 'more a pupil on teachers than Lunenburg', 'published'),
         f('gap', U(hb['pp'] - lb['pp']), 'more a pupil in all', 'published'),
         f('grants', U(hb['grants']), 'paid by grants and revolving funds', 'published'),
         f('gsh', P(gsh), 'of Harvard’s total from them', 'published'),
         f('lgsh', P(lgsh), 'of Lunenburg’s total from them', 'published'),
         f('t2305', U(t2305['grants']), 'classroom teachers, paid from them', 'published'),
         f('cap', N(hb['capital_rows']), 'rows coded capital (7000) or debt (8000) in DESE’s file',
           'published', allow=('7000', '8000'))],
        [con('Teachers were %s of the %s a pupil; insurance, retirement and other, %s, came next.'
             % (C.usd(tc['pp']), C.usd(hb['pp']), C.usd(be['pp'])), ['tchr', 'pp', 'bene', 'fte'],
             {'a': U(tc['pp']), 'b': U(hb['pp']), 'c': U(be['pp'])}),
         con('Teachers are the widest gap with Lunenburg: %s a pupil of the %s in all.'
             % (C.usd(diffs['TCHR']), C.usd(hb['pp'] - lb['pp'])), ['tgap', 'gap'],
             {'a': U(diffs['TCHR']), 'b': U(hb['pp'] - lb['pp'])}),
         con('Grants and revolving funds paid %s of Harvard’s total, %s of Lunenburg’s.'
             % (C.pct(gsh, 1), C.pct(lgsh, 1)), ['grants', 'gsh', 'lgsh', 'total'],
             {'a': P(gsh), 'b': P(lgsh)}),
         con('Classroom teachers were their largest line, %s; none of the total is capital or debt.'
             % C.usd(t2305['grants']), ['t2305', 'cap'], {'a': U(t2305['grants'])},
             notes=[step('Which grant or revolving fund pays those salaries is not in DESE’s '
                         'file.', 'gap', closes='DESE’s End of Year Pupil and Financial Report '
                                                'for Harvard, which reports spending by fund')])],
        chart=PPM.breakdown_chart(hb),
        table=PPM.breakdown_table(hb),
        sources=S('dese', 'radar'),
        finding_figures={'a': U(hb['pp']), 'y': F(y), 'p': P(gsh)})

    # ------------------------------------------------ Lunenburg at Harvard's rate
    # OUR ARITHMETIC, labelled so. The state median's version is READ off cost-of-the-median.json.
    cm = {x['id']: x['value'] for x in load('topics/cost-of-the-median.json')['facts']}
    pl, ph = lb['fte_total'], hb['fte_total']
    if cm['pupils']['value'] != pl or cm['med']['value'] != last['state_median'] \
            or cm['spent']['value'] != lb['total']:
        fail('cost-of-the-median.json no longer reads the pupils, median and total used here')
    if abs(cm['med']['value'] * pl - cm['need']['value']) > 0.5:
        fail('the state median times Lunenburg’s pupils no longer recomputes to its page')
    need = hb['pp'] * pl
    more = need - lb['total']
    mores = cm['more']['value']
    if abs(cm['need']['value'] - lb['total'] - mores) > 0.5:
        fail('the state median’s distance no longer recomputes to cost-of-the-median')
    if not more > mores > 0:
        fail('Harvard’s rate no longer lies above the state median’s for Lunenburg, as the page says')
    # THE TWO TOTALS, decomposed exactly: Lunenburg spent MORE in all than Harvard, with more
    # pupils at a lower rate. Its extra pupils at its own rate, less Harvard's pupils times the
    # gap a pupil, IS the difference between the totals -- asserted to the cent.
    rh, rl = hb['total'] / ph, lb['total'] / pl
    lgap = lb['total'] - hb['total']
    vol, rate = (pl - ph) * rl, ph * (rh - rl)
    if abs(vol - rate - lgap) > 0.01:
        fail('the pupil and rate parts no longer add to the difference between the totals')
    if not (lgap > 0 and rate > 0 and pl > ph):
        fail('the decomposition’s words assume Lunenburg spent more in all, with more pupils')
    # IN TAX TERMS. TJ, 16 October 2026: "the equivalent increase to Lunenburg taxes if we had
    # that same spend per pupil". OUR ESTIMATE, on stated assumptions: the whole difference
    # raised from the property tax, spread in proportion over the levy (so every bill rises by
    # the same share), FY2025 spending against the FY2026 levy -- the latest of each. Read from
    # the property-tax pages (build_homes_and_taxes_topics.py runs first), never recomputed.
    def _facts(name):
        return {x['id']: x for x in json.load(open(os.path.join(OUT_DIR, name + '.json'),
                                                    encoding='utf-8'))['facts']}
    rs, hv = _facts('regional-school-share'), _facts('home-value-and-bill')
    levy, avg_bill, std_bill = (rs['levy']['value']['value'], rs['bill']['value']['value'],
                                hv['std']['value']['value'])
    tax_rows = [(lab, [fmt(more), fmt(mores)]) for lab, fmt in (
        ('More than spent, a year (ours)', C.usd),
        ('More than Lunenburg’s schools spent, all funds (ours)', lambda v: C.pct(100 * v / lb['total'], 0)),
        ('As a share of the FY2026 tax levy (ours)', lambda v: C.pct(100 * v / levy, 1)),
        ('Added to the tax on the same $500,000 home (ours)', lambda v: C.usd(std_bill * v / levy)),
        ('Added to the average single-family bill (ours)', lambda v: C.usd(avg_bill * v / levy)))]
    if not 0 < more / levy < 1:
        fail('the Harvard-rate difference is no longer a share of the levy between 0 and 1')
    out['lunenburg-at-harvard-rate'] = TP.page(
        'lunenburg-at-harvard-rate',
        'At Harvard’s %s rate a pupil, Lunenburg would have spent %s more, by our arithmetic.'
        % (C.fy(y), C.usd(more)),
        [f('lun', U(lb['pp']), 'Lunenburg a pupil, all funds, %s' % C.fy(y), 'published', yl),
         f('har', U(hb['pp']), 'Harvard a pupil, the same measure', 'published'),
         f('pupils', PU(pl), 'Lunenburg’s FTE pupils, DESE', 'published'),
         f('hpupils', PU(ph), 'Harvard’s FTE pupils, DESE', 'published'),
         f('need', U(need), 'at Harvard’s rate (ours)', 'estimate'),
         f('more', U(more), 'more than Lunenburg spent (ours)', 'estimate'),
         f('smed', U(last['state_median']), 'median of all districts a pupil', 'published'),
         f('mores', U(mores), 'more, at the state median (ours)', 'estimate'),
         f('lgap', U(lgap), 'Lunenburg’s total less Harvard’s', 'published'),
         f('vol', U(vol), 'Lunenburg’s extra pupils at its own rate (ours)', 'estimate'),
         f('rate', U(rate), 'Harvard’s pupils times the gap a pupil (ours)', 'estimate'),
         f('li', P(li_h), 'of Harvard’s students low-income; Lunenburg %s' % C.pct(li_l, 1),
           'published', {'l': P(li_l)})],
        [con('Harvard’s %s for each of Lunenburg’s %s pupils comes to %s, %s more than spent.'
             % (C.usd(hb['pp']), PU(pl)['text'], C.usd(need), C.usd(more)),
             ['har', 'pupils', 'need', 'more', 'lun'],
             {'a': U(hb['pp']), 'n': PU(pl), 'b': U(need), 'c': U(more)}),
         con('At the median of all districts, which Harvard spends above, it is %s more.'
             % C.usd(mores), ['smed', 'mores'], {'a': U(mores)}),
         con('Lunenburg spent %s more: %s for more pupils, less %s for Harvard’s higher rate.' % (C.usd(lgap), C.usd(vol), C.usd(rate)), ['lgap', 'vol', 'rate', 'hpupils'],
             {'a': U(lgap), 'b': U(vol), 'c': U(rate)},
             notes=[step('Possibly fixed costs spread over fewer pupils in a smaller district. '
                         'Nothing here tests it.', 'hypothesis')]),
         con('Harvard’s students were %s low-income, Lunenburg’s %s; a rate is not a like-for-like '
             'cost.' % (C.pct(li_h, 1), C.pct(li_l, 1)), ['har', 'lun', 'li'],
             {'a': P(li_h), 'b': P(li_l)})],
        chart=TP.series('Lunenburg’s spending at other rates',
                        ['Spent', 'At the all-district median', 'At Harvard’s rate'], [
            TP.track('Spent, all funds, DESE', [lb['total'], None, None], 'published', 'bar'),
            TP.track('Ours, a rate times Lunenburg’s pupils', [None, cm['need']['value'], need],
                     'estimate', 'bar')],
            '$', stacked=True,
            note='%s, all funds. The two right-hand bars are our multiplication, not a target '
                 'or a cost anybody proposed.' % C.fy(y), note_figures=yl),
        table=dict(caption='A pupil, side by side, %s' % C.fy(y), views=[
            dict(key='side', label='Category by category', columns=['Lunenburg', 'Harvard',
                                                                    'Difference'],
                 kinds=['ledger'] * 3, total_col=2, rows=[
                     dict(label=c['short'], cells=[
                         C.usd(lcat[c['code']]['pp']) if c['code'] in lcat else None,
                         C.usd(c['pp']), C.usd(diffs[c['code']])]) for c in hb['cats']]
                 + [dict(label=c['short'], cells=[C.usd(c['pp']), None, C.usd(-c['pp'])])
                    for c in lb['cats'] if c['code'] not in hcat]
                 + [dict(label='Total, as DESE prints it', cells=[
                     C.usd(lb['pp']), C.usd(hb['pp']), C.usd(hb['pp'] - lb['pp'])])],
                 note='DESE, all funds. Each category over the district’s total FTE pupils, our '
                      'division, so the rows add to DESE’s totals. A dash: no spending there.'),
            dict(key='rates', label='The arithmetic', columns=['A pupil', 'Times pupils',
                                                               'More than spent'],
                 kinds=['ledger'] * 3, total_col=1, rows=[
                     dict(label=k, cells=[C.usd(r), C.usd(n), C.usd(n - lb['total'])])
                     for k, r, n in (('Lunenburg, as spent', lb['pp'], lb['total']),
                                     ('All-district median', last['state_median'],
                                      cm['need']['value']),
                                     ('Harvard', hb['pp'], need))],
                 note='Ours: DESE’s rate a pupil times Lunenburg’s %s FTE pupils. The '
                      'all-district line is the one on Reaching the state median.'
                      % PU(pl)['text']),
            dict(key='tax', label='In budget and tax terms', columns=['At Harvard’s rate', 'At the state median'],
                 kinds=['ledger'] * 2, rows=[dict(label=l, cells=c) for l, c in tax_rows],
                 note='Ours, and a scenario, not a proposal: as if the whole difference were raised '
                      'from the property tax, spread in proportion over the FY2026 levy, so every '
                      'bill rises by the same share. FY2025 spending against the FY2026 levy, the '
                      'latest of each. A rise this size is far beyond what Proposition 2½ allows '
                      'in a year without an override vote.')]),
        sources=S('dese', 'statewide', 'radar'),
        finding_figures={'y': F(y), 'a': U(more)})

    # ------------------------------------------------ the hub
    h = {}
    h['h-har'] = f('h-har', U(last['harvard']), 'a pupil at Harvard, all funds, %s' % C.fy(y),
                   'published', yl)
    h['h-lun'] = f('h-lun', U(last['lunenburg']), 'a pupil at Lunenburg, the same measure',
                   'published')
    h['h-smed'] = f('h-smed', U(last['state_median']), 'median of all districts', 'published')
    h['h-gap0'] = f('h-gap0', U(gap[y0]), 'the gap in %s' % C.fy(y0), 'published', {'y': F(y0)})
    h['h-tgap'] = f('h-tgap', U(diffs['TCHR']), 'of the gap a pupil on teachers', 'published')
    h['h-gsh'] = f('h-gsh', P(gsh), 'of Harvard’s spending from grants and revolving funds',
                   'published')
    h['h-more'] = f('h-more', U(more), 'more for Lunenburg at Harvard’s rate (ours)', 'estimate')
    h['h-li'] = f('h-li', P(li_h), 'of Harvard’s students low-income; Lunenburg %s'
                  % C.pct(li_l, 1), 'published', {'l': P(li_l)})
    tiers = [
        LD.tier('A pupil, %s' % C.fy(y), [h['h-har'], h['h-lun'], h['h-smed'], h['h-gap0']]),
        LD.tier('Where the money goes', [h['h-tgap'], h['h-gsh']]),
        LD.tier('Scale and population', [h['h-more'], h['h-li']]),
    ]
    hub_ladder = LD.ladder(tiers, [
        LD.conclusion('Harvard spent %s a pupil, %s more than Lunenburg; in %s the gap was %s.'
                      % (C.usd(last['harvard']), C.usd(gap[y]), C.fy(y0), C.usd(gap[y0])),
                      ['h-har', 'h-lun', 'h-gap0'],
                      {'a': U(last['harvard']), 'g': U(gap[y]), 'y': F(y0), 'h': U(gap[y0])}),
        LD.conclusion('Teachers are the widest part of the gap; grants paid %s of Harvard’s '
                      'spending.' % C.pct(gsh, 1), ['h-tgap', 'h-gsh'], {'a': P(gsh)}),
        LD.conclusion('At Harvard’s rate, Lunenburg would have spent %s more, by our arithmetic.'
                      % C.usd(more), ['h-more', 'h-smed'], {'a': U(more)}),
        LD.conclusion('Harvard serves a smaller low-income share; spending is not shown to cause '
                      'results.', ['h-li']),
    ])
    out[HUB] = TP.hub(
        HUB,
        'Harvard, the district The Bromfield School belongs to, spent %s a pupil in %s, %s more '
        'than Lunenburg, on the same state measure. It serves a smaller low-income share, and '
        'nothing here shows the spending causes results.'
        % (C.usd(last['harvard']), C.fy(y), C.usd(gap[y])),
        hub_ladder,
        chart=TP.series('Spending a pupil, Harvard and Lunenburg', [C.fy(v) for v in years], [
            TP.track('Harvard', [by[v]['harvard'] for v in years]),
            TP.track('Median of all districts', [by[v]['state_median'] for v in years]),
            TP.track('Lunenburg', [by[v]['lunenburg'] for v in years]),
        ], '$', note='DESE, all funds, over total pupils, reported after each year closed.'),
        answer_figures={'a': U(last['harvard']), 'y': F(y), 'g': U(gap[y])})

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
        print('bromfield topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
