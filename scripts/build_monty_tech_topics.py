#!/usr/bin/env python3
"""The Monty Tech shelf: its hub, the per-pupil page, Monty Tech line by line, and Lunenburg at
Monty Tech's rate (TJ, 15 October 2026: "how much would our budget be if we had the same per
pupil rate as Monty Tech?").

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
  fy28/public/data/topics/cost-of-the-median.json
                                             build_school_spending_topics.py: Lunenburg at the
                                             state median. The rate scenario READS it, so the site
                                             carries one figure for it. Run that generator first.
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
import census_revenue as CR  # noqa: E402
import build_transportation as BT  # noqa: E402  (levy_share: the one place 'mostly taxes' is measured)

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
        'radar': dict(label='Lunenburg Budget Project — dese-radar.csv (DESE’s FTE pupil counts, '
                            'from RADAR)', href='/docs/data/dese-radar.csv'),
        'census': dict(label='U.S. Census Bureau, Annual Survey of School System Finances, FY2024 '
                             '— census-elsec24.xlsx', href='/docs/' + CR.KEY),
        'census-doc': dict(label='U.S. Census Bureau, the same survey’s documentation and data '
                                 'dictionary — census-school24doc.docx', href='/docs/' + CR.DOC_KEY),
        'census-f33': dict(label='U.S. Census Bureau, Form F-33 and its instructions, survey year '
                                 '2024, page 8, Part I Section A — census-f33_2024_508.pdf',
                           href='/docs/' + CR.F33_KEY),
        'mt-book': dict(label='Monty Tech, FY24 budget for public hearing, 8 March 2023, staffing '
                              'profile — a103-fy24-monty-tech-budget-for-public-hearing-march-08-2023-pdf.pdf',
                        href='/docs/town-budget/docs/a103-fy24-monty-tech-budget-for-public-hearing-'
                             'march-08-2023-pdf.pdf'),
        'mt-deck': dict(label='Monty Tech, FY27 Budget Presentation, page 5, “Update of Annual '
                              'Grant Awards” — 3583-fy27-monty-tech-budget-presentation-pdf.pdf',
                        href='/docs/town-budget/docs/3583-fy27-monty-tech-budget-presentation-pdf.pdf'),
        'eoyr': dict(label='Massachusetts DESE, End of Year Financial Report FY2025, printing '
                           'version — printing-version.xlsx, sheet eoy25, lines 3524-3529',
                     href=EOYR),
    }


# "OTHER LOCAL", ITEMISED. TJ, 23 October 2026, on the single row this replaced ("Other local:
# tuition, fees, interest, other"): *"that's a huge number and not to know what it represents is
# hard... like what is A07 Tuition?! U97?!"* Each item now has its own row, named in plain words
# with the Census code beside it in small type. The names and the meanings are census_revenue's,
# read from the Census Bureau's own data dictionary and F-33 instructions -- not typed here.
REVENUE_HEAD = (('Federal and state grants, less meals', 'grants'),
                ('Private gifts', 'donations'),
                ('School-meal money, federal and state', 'meals'),
                ('State Chapter 70 aid', 'ch70'),
                ('State transportation aid', 'transport'),
                ('Pensions the state pays on its behalf', 'on_behalf'),
                ('State capital and debt aid', 'capital_aid'),
                ('Town budgets, mostly property tax', 'towns'))

# One line under the table per item a reader cannot read off its name, each the Census form's own
# instruction for that line. The quoted words are asserted verbatim against the form here, as
# census_revenue asserts the instruction it holds; the rest of each line is ours.
ITEM_LINES = {
    'D11': ('Paid by other school systems (D11): the form asks for “payments received from other '
            'school systems, both within and outside the state, for tuition, transportation, and '
            'other services”, and tells a regional district to report here any assessments paid by '
            'independent school districts.', 'payments received from other school systems, both within and '
            'outside the state, for tuition, transportation, and other services'),
    'A07': ('Tuition (A07): the Census item is “Tuition fees from pupils, parents, and other private '
            'sources”, one of the form’s student-fee lines. Tuition another school system pays is '
            'D11, not this.', None),
    'A09': ('School meal sales (A09): what students, teachers and adults paid for breakfasts, '
            'lunches and milk, “not from state or federal funds”; those are the school-meal row '
            'above.', 'not from state or federal funds'),
    'A13': ('Student activity receipts (A13): gross receipts of district activity funds “under '
            'control of the custodian of district funds”.',
            'under control of the custodian of district funds'),
    'U22': ('Interest earned (U22): “interest earnings from all funds held by the school system”, '
            'every fund, not the general fund alone.',
            'interest earnings from all funds held by the school system'),
    'U97': ('Refunds and other local revenue (U97): “receipts from refunds of prior year expenditures and other '
            'revenue from local sources not provided for elsewhere”. The survey does not split the '
            'two.', 'receipts from refunds of prior year expenditures and other revenue from local '
            'sources not provided for elsewhere'),
    'A40': ('Rent (A40): the Census item is “Rents and royalties”; the form asks for revenue “from '
            'allowing temporary possession or granting rights to the use of school district '
            'buildings, land, or other properties”.', 'from allowing temporary possession or '
            'granting rights to the use of school district buildings, land, or other properties'),
}

# WHAT MONTY TECH'S ITEMS WERE FOR is not in any document held here (searched 23 October 2026:
# both Monty Tech budget books, the meeting archive). The FY2024 hearing book's staffing profile
# lists Practical Nursing and Continuing and Post Graduate Studies under "Salaries from
# Revolving/Special Revenue Funds" (town-budget/text/a103-...-march-08-2023-pdf.txt, lines
# 459-463), so the programmes exist; it prints no revenue for them. Registered in money-gaps.csv.
ITEM_GAP = ('What Monty Tech’s tuition (A07), payments from other school systems (D11) and refunds '
            'and other revenue (U97) were for is not in any document held here. Its FY2024 budget '
            'book lists Practical Nursing and Continuing and Post Graduate Studies staff among those '
            'paid from revolving or special-revenue funds, so those programmes exist; it prints no '
            'revenue for them. Closes: Monty Tech’s audited financial statements, revenue by fund.')
ITEM_GAP_QUOTE = (os.path.join(ROOT, 'sources', 'town-budget', 'text',
                               'a103-fy24-monty-tech-budget-for-public-hearing-march-08-2023-pdf.txt'),
                  ('Salaries from Revolving/Special Revenue Funds', 'Practical Nursing',
                   'Continuing and Post Graduate Studies'))


def item_codes(mt, lu):
    """The other-local items either district reported, in the survey's own order."""
    return [c for c in CR.OTHER_LOCAL if mt['other_local_items'][c] or lu['other_local_items'][c]]


def revenue_rows(mt, lu, sh, SP):
    items = CR.local_items()
    codes = item_codes(mt, lu)
    for d in (mt, lu):
        if sum(d['other_local_items'][c] for c in codes) != d['other_local']:
            fail('%s: the itemised rows do not add to the other local revenue they replace'
                 % d['name'])
        if sum(d[k] for _, k in REVENUE_HEAD) + d['other_local'] != d['total']:
            fail('%s: the table\'s rows do not add to total revenue' % d['name'])
    pct = lambda d, v: SP(100.0 * v / d['total'])
    rows = [dict(label=lab, cells=[C.usd(mt[k]), SP(sh(mt, k)), C.usd(lu[k]), SP(sh(lu, k))])
            for lab, k in REVENUE_HEAD]
    for c in codes:
        a, b = mt['other_local_items'][c], lu['other_local_items'][c]
        rows.append(dict(label=items[c]['name'], code='Census %s' % c,
                         cells=[C.usd(a), pct(mt, a), C.usd(b), pct(lu, b)]))
    rows.append(dict(label='Total revenue', cells=[C.usd(mt['total']), SP(sh(mt, 'total')),
                                                   C.usd(lu['total']), SP(sh(lu, 'total'))]))
    return rows


def revenue_lines(mt, lu):
    form = ' '.join(open(CR.F33_TEXT, encoding='utf-8').read().replace('\u2013', '-').split())
    out = []
    for c in item_codes(mt, lu):
        if c not in ITEM_LINES:
            fail('Census item %s has money in it and no line saying what it is' % c)
        line, quote = ITEM_LINES[c]
        if quote and quote not in form:
            fail('the words quoted for %s are not in the F-33, verbatim' % c)
        out.append(line)
    held = open(ITEM_GAP_QUOTE[0], encoding='utf-8').read()
    if not all(q in held for q in ITEM_GAP_QUOTE[1]):
        fail('the Monty Tech FY2024 budget book no longer reads as the gap line says')
    return out + [ITEM_GAP]


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


    # ------------------------------------------------ Monty Tech, line by line
    # The twin of /school-spending/per-pupil-line-by-line: the same split, footed the same way
    # by per_pupil_measures.breakdown(), drawn by the same two helpers.
    mb = PPM.breakdown(PPM.MONTY, y)
    lb = PPM.breakdown(PPM.LUNENBURG, y)
    if mb['pp'] != last['monty'] or lb['pp'] != last['lunenburg']:
        fail('the line-by-line totals are not the per-pupil figures this shelf prints')
    mcat = {c['code']: c for c in mb['cats']}
    if [c['code'] for c in sorted(mb['cats'], key=lambda c: -c['pp'])[:2]] != ['TCHR', 'BENE']:
        fail('teachers then insurance are no longer Monty Tech’s two largest categories')
    mtop = max(mb['lines'], key=lambda r: r['grants'])
    if mtop['code'] != '3400':
        fail('food services is no longer the largest line grants and revolving funds paid')
    meq = next(r for r in mb['lines'] if r['code'] == '2420' and r['where'] == 'In-District')
    PU = lambda v: figure(v, '{:,.1f}'.format(v), 'FTE pupils')
    yl = {'y': F(y)}
    tc, be = mcat['TCHR'], mcat['BENE']
    out['monty-tech-line-by-line'] = TP.page(
        'monty-tech-line-by-line',
        'Monty Tech’s %s a pupil in %s, by what it paid for: insurance and grants are in it, '
        'capital is not.' % (C.usd(mb['pp']), C.fy(y)),
        [f('pp', U(mb['pp']), 'a pupil, all funds, %s, DESE' % C.fy(y), 'published', yl),
         f('total', U(mb['total']), 'spent, all funds, %s' % C.fy(y), 'published', yl),
         f('fte', PU(mb['fte_total']), 'FTE pupils DESE divides by', 'published'),
         f('tchr', U(tc['pp']), 'teachers, a pupil (our division)', 'published'),
         f('bene', U(be['pp']), 'insurance, retirement and other, a pupil', 'published'),
         f('grants', U(mb['grants']), 'paid by grants and revolving funds', 'published'),
         f('food', U(mtop['grants']), 'food services, paid by them', 'published'),
         f('foodall', U(mtop['total']), 'food services, all funds', 'published'),
         f('eq', U(meq['total']), 'instructional equipment, all funds', 'published'),
         f('eqgr', U(meq['grants']), 'of it from grants and revolving funds', 'published'),
         f('cap', N(mb['capital_rows']), 'rows coded capital (7000) or debt (8000) in DESE’s file',
           'published', allow=('7000', '8000'))],
        [con('Teachers were %s of the %s a pupil; insurance, retirement and other, %s, came next.'
             % (C.usd(tc['pp']), C.usd(mb['pp']), C.usd(be['pp'])), ['tchr', 'pp', 'bene', 'fte'],
             {'a': U(tc['pp']), 'b': U(mb['pp']), 'c': U(be['pp'])}),
         con('Grants and revolving funds paid %s; their largest line was food services, %s of %s.'
             % (C.usd(mb['grants']), C.usd(mtop['grants']), C.usd(mtop['total'])),
             ['grants', 'food', 'foodall', 'total'],
             {'a': U(mb['grants']), 'b': U(mtop['grants']), 'c': U(mtop['total'])}),
         con('None of it is capital or debt service: %s rows in DESE’s file carry those codes.'
             % C.num(mb['capital_rows']), ['cap'], {'n': N(mb['capital_rows'])}),
         con('Instructional equipment, %s, IS counted; %s of it came from grants and revolving '
             'funds.' % (C.usd(meq['total']), C.usd(meq['grants'])), ['eq', 'eqgr'],
             {'a': U(meq['total']), 'b': U(meq['grants'])},
             notes=[step('Whether every district codes the same purchase as equipment rather than '
                         'capital is not visible in DESE’s data.', 'gap',
                         closes='each district’s End of Year Financial Report workbook, with its '
                                '7000 and lease schedules', allow=('7000',))])],
        chart=PPM.breakdown_chart(mb),
        table=PPM.breakdown_table(mb),
        sources=S('dese', 'radar'),
        finding_figures={'a': U(mb['pp']), 'y': F(y)})

    # ------------------------------------------------ Lunenburg at Monty Tech's rate
    # OUR ARITHMETIC, labelled so: a rate DESE printed times the pupils DESE counted. The state
    # median's version is READ off cost-of-the-median.json (build_school_spending_topics.py), so
    # the site carries one figure for it, and recomputed here only to prove it ties.
    cm = {x['id']: x['value'] for x in
          json.load(open(os.path.join(OUT_DIR, 'cost-of-the-median.json'), encoding='utf-8'))['facts']}
    pl, pm = lb['fte_total'], mb['fte_total']
    if cm['pupils']['value'] != pl or cm['med']['value'] != last['state_median'] \
            or cm['spent']['value'] != lb['total']:
        fail('cost-of-the-median.json no longer reads the pupils, median and total used here')
    if abs(cm['med']['value'] * pl - cm['need']['value']) > 0.5:
        fail('the state median times Lunenburg’s pupils no longer recomputes to its page')
    vmed = last['vocational_median']
    if not mb['pp'] < vmed:
        fail('Monty Tech is no longer below the vocational median, which the page says')
    need = {'mt': mb['pp'] * pl, 'v': vmed * pl, 's': cm['need']['value']}
    more = {k: v - lb['total'] for k, v in need.items()}
    if abs(more['s'] - cm['more']['value']) > 0.5:
        fail('the state median’s distance no longer recomputes to cost-of-the-median')
    # THE TWO TOTALS, decomposed exactly: rates are DESE's totals over DESE's pupils, unrounded,
    # so Monty Tech's pupils times the gap less the pupil difference times Lunenburg's rate IS
    # the difference between the totals -- asserted to the cent.
    rm, rl = mb['total'] / pm, lb['total'] / pl
    tgap = mb['total'] - lb['total']
    rate, vol = pm * (rm - rl), (pl - pm) * rl
    if abs(rate - vol - tgap) > 0.01:
        fail('the rate and pupil parts no longer add to the difference between the totals')
    if not (tgap > 0 and vol > 0):
        fail('the decomposition’s words assume Monty Tech spent more in all and has fewer pupils')
    nyears = len(M['by_year'])
    lc = {c['code']: c for c in lb['cats']}
    side = [(c, lc.get(c['code'])) for c in mb['cats']] + \
           [(None, c) for c in lb['cats'] if c['code'] not in mcat]
    out['lunenburg-at-monty-tech-rate'] = TP.page(
        'lunenburg-at-monty-tech-rate',
        'At Monty Tech’s %s rate a pupil, Lunenburg would have spent %s more, by our arithmetic.'
        % (C.fy(y), C.usd(more['mt'])),
        [f('lun', U(lb['pp']), 'Lunenburg a pupil, all funds, %s' % C.fy(y), 'published', yl),
         f('mt', U(mb['pp']), 'Monty Tech a pupil, the same measure', 'published'),
         f('pupils', PU(pl), 'Lunenburg’s FTE pupils, DESE', 'published'),
         f('need', U(need['mt']), 'at Monty Tech’s rate (ours)', 'estimate'),
         f('more', U(more['mt']), 'more than Lunenburg spent (ours)', 'estimate'),
         f('vmed', U(vmed), 'median vocational district a pupil', 'published'),
         f('morev', U(more['v']), 'more, at the vocational median (ours)', 'estimate'),
         f('smed', U(last['state_median']), 'median of all districts a pupil', 'published'),
         f('mores', U(more['s']), 'more, at the all-district median (ours)', 'estimate'),
         f('tgap', U(tgap), 'Monty Tech’s total less Lunenburg’s', 'published'),
         f('rate', U(rate), 'Monty Tech’s pupils times the gap a pupil (ours)', 'estimate'),
         f('vol', U(vol), 'its fewer pupils times Lunenburg’s rate (ours)', 'estimate')],
        [con('Monty Tech’s %s for each of Lunenburg’s %s pupils comes to %s, %s more than spent.'
             % (C.usd(mb['pp']), PU(pl)['text'], C.usd(need['mt']), C.usd(more['mt'])),
             ['mt', 'pupils', 'need', 'more', 'lun'],
             {'a': U(mb['pp']), 'n': PU(pl), 'b': U(need['mt']), 'c': U(more['mt'])}),
         con('At the vocational median, which Monty Tech spends below, it is %s more; all '
             'districts’, %s.' % (C.usd(more['v']), C.usd(more['s'])), ['vmed', 'morev', 'smed', 'mores'],
             {'a': U(more['v']), 'b': U(more['s'])}),
         con('Monty Tech is a vocational high school, Lunenburg K-12; the vocational median '
             'beat the state’s all %s years.' % C.num(nyears), ['vmed', 'smed', 'mt'],
             {'n': N(nyears)}, allow=('K-12',),
             notes=[step('Possibly shop equipment, smaller shop classes and buses across many '
                         'towns. Nothing here tests it.', 'hypothesis')]),
         con('The totals differ by %s: %s from Monty Tech’s higher rate, less %s for fewer '
             'pupils.' % (C.usd(tgap), C.usd(rate), C.usd(vol)), ['tgap', 'rate', 'vol'],
             {'a': U(tgap), 'b': U(rate), 'c': U(vol)})],
        chart=TP.series('Lunenburg’s spending at other rates',
                        ['Spent', 'At the all-district median', 'At Monty Tech’s rate',
                         'At the vocational median'], [
            TP.track('Spent, all funds, DESE', [lb['total'], None, None, None], 'published', 'bar'),
            TP.track('Ours, a rate times Lunenburg’s pupils', [None, need['s'], need['mt'],
                                                                need['v']], 'estimate', 'bar')],
            '$', stacked=True,
            note='%s, all funds. The three right-hand bars are our multiplication, not a target '
                 'or a cost anybody proposed.' % C.fy(y), note_figures=yl),
        table=dict(caption='A pupil, side by side, %s' % C.fy(y), views=[
            dict(key='side', label='Category by category', columns=['Lunenburg', 'Monty Tech',
                                                                    'Difference'],
                 kinds=['ledger'] * 3, total_col=2, rows=[
                     dict(label=(m or l)['short'], cells=[
                         C.usd(l['pp']) if l else None, C.usd(m['pp']) if m else None,
                         C.usd((m['pp'] if m else 0) - (l['pp'] if l else 0))])
                     for m, l in side] + [dict(label='Total, as DESE prints it', cells=[
                         C.usd(lb['pp']), C.usd(mb['pp']), C.usd(mb['pp'] - lb['pp'])])],
                 note='DESE, all funds. Each category over the district’s total FTE pupils, our '
                      'division, so the rows add to DESE’s totals. A dash: no spending there.'),
            dict(key='rates', label='The arithmetic', columns=['A pupil', 'Times pupils',
                                                               'More than spent'],
                 kinds=['ledger'] * 3, total_col=1, rows=[
                     dict(label=k, cells=[C.usd(r), C.usd(n), C.usd(n - lb['total'])])
                     for k, r, n in (('Lunenburg, as spent', lb['pp'], lb['total']),
                                     ('All-district median', last['state_median'], need['s']),
                                     ('Monty Tech', mb['pp'], need['mt']),
                                     ('Vocational median', vmed, need['v']))],
                 note='Ours: DESE’s rate a pupil times Lunenburg’s %s FTE pupils. The '
                      'all-district line is the one on Reaching the state median.'
                      % PU(pl)['text'])]),
        sources=S('dese', 'statewide', 'radar'),
        finding_figures={'y': F(y), 'a': U(more['mt'])})

    # ------------------------------------------------ Monty Tech revenue, against Lunenburg's
    # TJ, 16 October 2026: people say *"monty tech makes most of its money by grants and
    # fundraising"* -- *"we need to show that, and compare lunenburg's grants."* Every figure is
    # the Census Bureau's, read and footed by census_revenue.py; the grouping is OURS and says so.
    fund = page_facts('monty-tech-funding')
    R = CR.revenue()
    mt, lu = R['monty'], R['lunenburg']
    sh = lambda d, k: 100.0 * d[k] / d['total']
    P = lambda v: figure(round(v, 1), C.pct(v))
    # A share that rounds to 0.0% is not nothing: Monty Tech's gifts are $6,000, not zero.
    SP = lambda v: 'under 0.1%' if 0 < v < 0.05 else C.pct(v)
    ry = {'y': F(CR.FY)}
    mgd, lgd = sh(mt, 'grants_and_donations'), sh(lu, 'grants_and_donations')
    mst, lst = sh(mt, 'state_and_towns'), sh(lu, 'state_and_towns')
    times = mt['state_and_towns'] / mt['grants_and_donations']
    # "More than N times": N is the whole part of the measured ratio, interpolated.
    tn = int(times)
    # The words below say "most", "a small share at both" and that Lunenburg's gifts were
    # larger. They are only true while these hold.
    if not (mgd < 20 and lgd < 20 and mst > 50 and tn >= 2):
        fail('the revenue page\'s words no longer fit the Census figures: grants and donations '
             '%.1f%% / %.1f%%, Chapter 70 and towns %.1f%%, ratio %.2f' % (mgd, lgd, mst, times))
    if not lu['donations'] > mt['donations']:
        fail('Monty Tech now reports more in private gifts than Lunenburg; the page says fewer')
    awards = fund['grants']['value']['value']
    # TJ, 16 October 2026, reading the first chart: *"it SEEMS like you are saying lunenburg gets
    # its biggest percent of revenue from the member towns"*. For Lunenburg it is the Town of
    # Lunenburg's own budget, so the label says what that money IS -- mostly property tax, by the
    # town's own revenue distribution -- not who passes it on.
    lv = BT.levy_share(2026)
    TOWN_LABEL = 'Town budgets, mostly property tax'
    # FIVE BANDS, because the site has five validated hues, and NINE sources. So two bands
    # are groups, and each is named for exactly what it holds (TJ, 19 October 2026, on an
    # invented grouping elsewhere: "that was bad!"). Grants exclude school-meal money, which
    # is paid per meal by formula -- it once made up a quarter of Monty Tech's "grants". The
    # state's transport aid and the pensions it pays on a district's behalf are both state
    # payments outside Chapter 70 that nobody applies for. Every source is its own table row.
    order = [('Grants and donations', 'grants_and_donations'), ('State Chapter 70 aid', 'ch70'),
             (TOWN_LABEL, 'towns'),
             ('State transport aid and state-paid pensions', 'transport_and_pensions'),
             ('The rest: school meals, tuition, fees', 'meals_and_local')]
    if mt['capital_aid'] or lu['capital_aid']:
        fail('state capital aid is no longer zero for both; give it a band of its own')
    for d in (mt, lu):
        if sum(d[k] for _, k in order) != d['total']:
            fail('the chart\'s five parts do not add to %s\'s total revenue' % d['name'])
    out['monty-tech-revenue'] = TP.page(
        'monty-tech-revenue',
        # THE COMPARISON LEADS (TJ, 23 Oct 2026, could not find this page as a comparison).
        'Towns paid %s of Lunenburg schools’ %s revenue, %s of Monty Tech’s; Chapter 70, '
        '%s and %s.' % (C.pct(sh(lu, 'towns')), C.fy(CR.FY), C.pct(sh(mt, 'towns')),
                        C.pct(sh(lu, 'ch70')), C.pct(sh(mt, 'ch70'))),
        [f('mt-total', U(mt['total']), 'Monty Tech revenue, every source, %s' % C.fy(CR.FY),
           'published', ry),
         f('mt-gd', U(mt['grants_and_donations']), 'of it grants and donations (our grouping)',
           'published'),
         f('mt-gdp', P(mgd), 'share from grants and donations', 'published'),
         f('mt-st', U(mt['state_and_towns']), 'Chapter 70 aid plus member town budgets',
           'published', allow=('Chapter 70',)),
         f('mt-stp', P(mst), 'share from Chapter 70 and town budgets', 'published',
           allow=('Chapter 70',)),
         f('mt-don', U(mt['donations']), 'private gifts to Monty Tech', 'published'),
         f('lu-total', U(lu['total']), 'Lunenburg schools revenue, %s' % C.fy(CR.FY), 'published',
           ry),
         f('lu-gd', U(lu['grants_and_donations']), 'of it grants and donations', 'published'),
         f('lu-gdp', P(lgd), 'share from grants and donations', 'published'),
         f('lu-stp', P(lst), 'share from Chapter 70 and the town budget', 'published',
           allow=('Chapter 70',)),
         f('lu-don', U(lu['donations']), 'private gifts to Lunenburg’s schools', 'published'),
         f('awards', U(awards), 'grant awards Monty Tech charts, a later year', 'published')],
        [con('Grants and donations brought Monty Tech %s of %s in %s, %s.'
             % (C.usd(mt['grants_and_donations']), C.usd(mt['total']), C.fy(CR.FY), C.pct(mgd)),
             ['mt-gd', 'mt-total', 'mt-gdp'],
             {'a': U(mt['grants_and_donations']), 'b': U(mt['total']), 'y': F(CR.FY), 'p': P(mgd)},
             notes=[step('“Grants” is our grouping: federal money and the state’s program '
                         'grants, less school-meal money, which is paid per meal by formula. '
                         'Chapter 70, transport aid and pensions the state pays are left out.',
                         'measured', allow=('Chapter 70',)),
                    step('Monty Tech’s school-meal money was %s, federal and state; counted as a '
                         'grant, it would raise the share to %s.'
                         % (C.usd(mt['meals']), C.pct(sh(mt, 'meals') + mgd)), 'measured',
                         {'a': U(mt['meals']), 'p': P(sh(mt, 'meals') + mgd)}),
                    step('Monty Tech’s own chart shows %s in grant awards for %s: awards in a '
                         'later year, not revenue received.' % (C.usd(awards), C.fy(2025)),
                         'measured', {'a': U(awards), 'y': F(2025)})]),
         con('State Chapter 70 aid and member town budgets brought %s, over %s times as much.'
             % (C.pct(mst), C.num(tn)), ['mt-st', 'mt-stp'],
             {'p': P(mst), 'n': figure(tn, C.num(tn), 'times')}, allow=('Chapter 70',)),
         con('Lunenburg’s schools took %s from grants and donations; Chapter 70 and the town budget, %s.'
             % (C.pct(lgd), C.pct(lst)), ['lu-gd', 'lu-gdp', 'lu-stp', 'lu-total'],
             {'a': P(lgd), 'b': P(lst)}, allow=('Chapter 70',),
             notes=[step('Lunenburg reported no school-meal revenue to the survey, where Monty '
                         'Tech reported %s of federal meal money. If Lunenburg’s sits in another '
                         'federal line, its grant share is overstated.' % C.usd(mt['meals_federal']), 'gap',
                         {'a': U(mt['meals_federal'])},
                         closes='Lunenburg’s DESE End of Year Financial Report, its revenue '
                                'and food service schedules')]),
         con('Private gifts: %s to Monty Tech in %s, %s to Lunenburg’s schools.'
             % (C.usd(mt['donations']), C.fy(CR.FY), C.usd(lu['donations'])),
             ['mt-don', 'lu-don'],
             {'a': U(mt['donations']), 'y': F(CR.FY), 'b': U(lu['donations'])},
             notes=[step('Money a separate foundation or booster club raises and spends itself '
                         'is not on a district’s books, so it is not in either figure.', 'gap',
                         closes='the IRS Form 990 of any foundation raising money for Monty Tech', allow=('990',))])],
        chart=TP.series('Where the money comes from', ['Monty Tech', 'Lunenburg schools'], [
            TP.track(name, [sh(mt, k), sh(lu, k)]) for name, k in order],
            '%', kind='bar', stacked=True, decimals=1,
            note='Census Bureau, %s, shares of each district’s revenue; grouping ours. Lunenburg’s '
                 'town budget is %s property tax (%s).' % (C.fy(CR.FY), C.pct(lv['share']), C.fy(2026)),
            note_figures=dict(ry, s=figure(lv['share'], C.pct(lv['share'])), t=F(2026))),
        table=dict(caption='Revenue by source, %s' % C.fy(CR.FY), views=[dict(
            key='sources', label='Census Bureau, in dollars',
            columns=['Monty Tech', 'Share', 'Lunenburg schools', 'Share'],
            kinds=['ledger'] * 4,
            rows=revenue_rows(mt, lu, sh, SP),
            note='Town budgets: for Lunenburg, the Town of Lunenburg’s appropriation; for Monty '
                 'Tech, what its member towns are assessed. The file reports thousands of dollars, '
                 'shown here times 1,000; each total is checked against its items. The rows after '
                 'town budgets are the rest of local revenue, one row per Census item; an item '
                 'neither district reported is left out.',
            lines=revenue_lines(mt, lu))]),
        sources=S('census', 'census-doc', 'census-f33', 'mt-deck', 'mt-book'),
        finding_figures={'a': P(sh(lu, 'towns')), 'y': F(CR.FY), 'b': P(sh(mt, 'towns')),
                         'c': P(sh(lu, 'ch70')), 'd': P(sh(mt, 'ch70'))},
        finding_allow=('Chapter 70',))

    # ------------------------------------------------ the hub
    en, asmt, fund = (page_facts('monty-tech-%s' % t) for t in ('enrolment', 'assessment', 'funding'))
    V = lambda facts, k: facts[k]['value']
    # THE DISTRICT'S OWN FIVE SOURCES, as monty-tech-funding draws them. This chart once
    # folded the Regional Transportation Fund into "its own reserves" beside Excess &
    # Deficiency; the district's Budget Summary counts that fund as one of the three revenues
    # that pay for transportation (build_monty_tech.py checks that identity), not a reserve.
    parts = [('State Chapter 70 aid', V(fund, 'ch70')['value']),
             ('Member towns’ assessments', V(fund, 'towns')['value']),
             ('State transportation aid', V(fund, 'aid')['value']),
             ('Excess & Deficiency (reserves)', V(fund, 'ed')['value']),
             ('Regional Transportation Fund', V(fund, 'rtf')['value'])]
    if round(sum(v for _, v in parts), 2) != V(fund, 'budget')['value']:
        fail('the five sources no longer add up to the operating budget on monty-tech-funding')
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
