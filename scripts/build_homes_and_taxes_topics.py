#!/usr/bin/env python3
"""Homes and taxes, split into topic pages: fourteen pages and the Homes, taxes, growth hub.

    python3 scripts/build_homes_and_taxes_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_homes_and_taxes_topics.py --check   # fail if any output would change

WHY THIS EXISTS. scripts/topics.py has the model: one question per page, under five minutes,
facts first, one to four conclusions resting on them. This shelf absorbs four reports --
/lunenburg-by-the-numbers, /homes-and-taxes, /homes-and-students and /growth -- and lists two
pages other categories own (enrolment-by-year, per-pupil-spending) without touching them.

IT COMPUTES NOTHING NEW THAT IT CAN READ INSTEAD. Every figure comes from a payload or a
dataset already in the repository, and the script refuses to write if two of them stop
agreeing where they are supposed to:

  fy28/public/data/lunenburg-by-the-numbers.json  build_lunenburg_by_the_numbers.py: the
                                    Census Bureau's ACS five-year estimates, 2014-2018 and
                                    2019-2023, EVERY ONE A SAMPLE ESTIMATE WITH A MARGIN.
  fy28/public/data/property-owners.json   build_property_owners.py: DLS's average single-family
                                    bill FY1988-FY2026 and the assessor's FY2026 parcel file.
  fy28/public/data/homes-and-students.json  build_homes_and_students.py: DLS parcels beside
                                    DESE's enrolment.
  fy28/public/data/commercial-base.json   build_commercial_base.py: DLS assessed value by
                                    class and certified new growth.
  sources/data/dls-new-growth.csv   fetch_dls_property.py: the new-growth file's own columns,
                                    for the levy added and its share of the prior levy limit.
  fy28/public/data/enrollment.json  only to tie the enrolment figure to DESE's own series.

RULE 3. A Census figure is PUBLISHED by the Census Bureau and is a SAMPLE ESTIMATE: every
tile that carries one says so and carries its margin. A median bill computed from the
assessor's values at the tax rate, with no exemption applied, is OUR estimate, kind
`estimate`. Arithmetic on published figures (a share, a ratio, a change) says so in its label.

RULE 7. Every cause attached to a measurement here is a `hypothesis` note, and every limit is
a `gap` naming the record that would settle it. No page identifies a property owner: every
parcel figure is a count or a median across hundreds of homes.

NOT REBUILT. /growth's projection -- the new commercial value a year it would take to hold
the budget gap, in buildings -- is computed by the model in TypeScript (model/answers.ts) and
no payload carries it. Reproducing it here would be a second copy of the model, so it stays
where it is and the shelf links to its dials.
"""
import argparse
import csv
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
from brief import step  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT_DIR = os.path.join(PUB, 'topics')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
NG_CSV = os.path.join(ROOT, 'sources', 'data', 'dls-new-growth.csv')
HUB = 'homes-and-taxes'
GEN = 'build_homes_and_taxes_topics.py'

MINE = [t for t, (_, home, gen) in REG.TOPICS.items() if home == HUB and gen == GEN]


def fail(msg):
    raise SystemExit('build_homes_and_taxes_topics: ' + msg)


def load(name):
    return json.load(open(os.path.join(PUB, name), encoding='utf-8'))


def said(payload, key, kind='minutes'):
    """One quotation a payload already verified against our copy of the minutes."""
    s = next((x for x in payload.get('said', []) if x['key'] == key), None)
    if s is None:
        fail('quotation %r is no longer in its payload' % key)
    if not s['cite'].startswith('/docs/'):
        fail('quotation %r does not cite our copy' % key)
    return dict(quote=s['quote'], board=s['board'], date=s['date'], href=s['cite'],
                label='%s %s, %s' % (s['board'], kind, s['date']))


def sources(*payloads):
    """Every document the four payloads cite, keyed by filename. Each /docs/ address must be
    in the archive manifest, because rule 12 needs our copy to exist."""
    man = {r['key'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    out = {}
    for p in payloads:
        for s in p['sources']:
            href = s['docs_url']
            if href.startswith('/docs/'):
                key = href[len('/docs/'):]
                if key not in man and not os.path.exists(os.path.join(ROOT, 'fy28', 'public', 'docs', key)):
                    fail('%s is neither in archive-manifest.csv nor published' % key)
            name = href.split('/')[-1]
            out[name] = dict(label='%s — %s' % (s['publisher'], name), href=href)
    return out


# --------------------------------------------------------------------- the pages

def build():
    BN = load('lunenburg-by-the-numbers.json')
    PO = load('property-owners.json')
    HS = load('homes-and-students.json')
    CB = load('commercial-base.json')
    EN = load('enrollment.json')
    src = sources(BN, PO, HS, CB)
    S = lambda *names: [src[n] for n in names]
    U = lambda v: figure(v, C.usd(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    PM = lambda e, m, unit=None: figure(e, '%s ± %s' % (C.num(e), C.num(m)), unit)
    PTS = lambda v: figure(v, C.points(v))
    # The Census's age bands are definitions, not figures: declared once, as literals, on
    # every tile and conclusion, longest first so '45 to 64' is stripped before '45'.
    AGES = ('45-to-64', '45 to 64', '25 to 44', '18 to 24', '65', '18', '45', '64')
    f = lambda *a, allow=(), **k: LD.fact(*a, allow=tuple(allow) + AGES, **k)
    con = lambda *a, allow=(), **k: TP.conclusion(*a, allow=tuple(allow) + AGES, **k)
    out = {}

    W, W0 = BN['window'], BN['previous_window']          # '2019–2023', '2014–2018'
    if (BN['vintage'], BN['previous_vintage']) != (2023, 2018):
        fail('the Census vintages are not 2018 and 2023; re-read every label here')
    CEN = ('2019–2023', '2014–2018')

    # ------------------------------------------------ the cross-checks
    last_fy = EN['last_fy']
    enrol = next(r['total'] for r in EN['district'] if r['fy'] == last_fy)
    hs_last = HS['series'][-1]
    if (hs_last['fy'], hs_last['students']) != (last_fy, enrol) or BN['children']['students'] != enrol:
        fail('DESE’s enrolment, homes-and-students and the Census page disagree on %s' % C.fy(last_fy))
    t = BN['tenure']
    if (t['owner']['estimate'], t['occupied']['estimate']) != (PO['tenure']['owners'], PO['tenure']['households']):
        fail('the Census page and the homes page disagree on owner-occupied households')
    bills = {r['fy']: r for r in PO['bills']['rows']}
    for r in HS['series']:
        if r['fy'] in bills and bills[r['fy']]['parcels'] != r['homes']:
            fail('DLS single-family parcels disagree between payloads for %s' % C.fy(r['fy']))
    ng_csv = {int(r['fy']): r for r in csv.DictReader(open(NG_CSV, encoding='utf-8'))
              if r['municipality'] == 'Lunenburg' and r['total_levy']}
    for r in CB['new_growth']:
        c = ng_csv.get(r['fy'])
        if c is None or (int(c['total_levy']), int(c['total_value']), int(c['res_value'])) != (
                r['total_levy'], r['total_value'], r['residential_value']):
            fail('commercial-base.json and dls-new-growth.csv disagree on %s' % C.fy(r['fy']))
        # the printed share of the prior levy limit, recomputed
        if abs(100 * int(c['total_levy']) / int(c['prior_levy_limit']) - float(c['levy_pct_of_prior_limit'])) > 0.006:
            fail('the new-growth file’s share of the prior limit does not recompute for %s' % C.fy(r['fy']))
    # The four classes sum to DLS's printed total from FY2008 on. Before that DLS's total runs
    # up to a few hundred thousand dollars above them (a class the export does not carry), so
    # for those years only the printed share is checked, and no page sums the classes there.
    for r in CB['values']:
        if r['commercial'] + r['industrial'] != r['commercial_industrial']:
            fail('commercial-base.json: commercial plus industrial no longer sums for %s' % C.fy(r['fy']))
        if r['fy'] >= 2008 and r['residential'] + r['commercial_industrial'] + r['personal'] != r['total']:
            fail('commercial-base.json: the classes no longer sum for %s' % C.fy(r['fy']))
        if abs(100 * (r['commercial_industrial'] + r['personal']) / r['total'] - r['cip_share']) > 0.006:
            fail('commercial-base.json: the business share does not recompute for %s' % C.fy(r['fy']))
    pb = PO['bills']
    lun_nb = next(r for r in pb['neighbours'] if r['town'] == 'Lunenburg')
    if lun_nb['bill'] != bills[pb['last_fy']]['bill']:
        fail('the neighbour table’s Lunenburg bill is not the series’ last bill')

    # ------------------------------------------------ population and households
    pop, pop0 = BN['ages']['population'], BN['previous']['ages']['population']
    hh, hh0 = BN['households']['households'], BN['previous']['households']['households']
    tests = BN['change']['tests']
    tp = next(x for x in tests if x['label'] == 'Population')
    th = next(x for x in tests if x['label'] == 'Households')
    if not (tp['distinguishable'] and th['distinguishable']):
        fail('population or households no longer clears its margin; rewrite the population page')
    if (tp['new'], tp['old'], th['new'], th['old']) != (pop['estimate'], pop0['estimate'],
                                                         hh['estimate'], hh0['estimate']):
        fail('the change tests are not the published estimates')
    ch = BN['change']
    survived = sum(1 for x in tests if x['distinguishable'])
    if (survived, len(tests)) != (ch['survived'], ch['compared']):
        fail('the count of changes beyond the margin no longer recomputes')
    SURV = figure(survived, '%d of %d' % (survived, len(tests)), 'Census measures')
    out['town-population'] = TP.page(
        'town-population',
        'About %s residents in %s households, on a sample; both grew by more than the survey’s margin.'
        % (C.num(pop['estimate']), C.num(hh['estimate'])),
        [f('pop', PM(pop['estimate'], pop['moe'], 'residents'), 'residents, %s sample estimate' % W,
           'published', allow=CEN),
         f('pop0', PM(pop0['estimate'], pop0['moe'], 'residents'), 'residents, %s sample estimate' % W0,
           'published', allow=CEN),
         f('hh', PM(hh['estimate'], hh['moe'], 'households'), 'households, %s sample estimate' % W,
           'published', allow=CEN),
         f('hh0', PM(hh0['estimate'], hh0['moe'], 'households'), 'households, %s sample estimate' % W0,
           'published', allow=CEN),
         f('surv', SURV, 'measures that moved beyond the margin (our test)', 'published')],
        [con('Residents rose by %s and households by %s between the two samples, beyond the margin.'
             % (C.num(tp['difference']), C.num(th['difference'])), ['pop', 'pop0', 'hh', 'hh0'],
             {'a': N(tp['difference']), 'b': N(th['difference'])},
             notes=[step('New homes, people moving in and smaller households all fit these '
                         'counts; the survey carries no reason for the change.', 'hypothesis')]),
         con('Only %s things the Census measures here changed by more than its own noise.'
             % SURV['text'], ['surv'], {'s': SURV},
             notes=[step('A change inside the margin is one this survey cannot see, which is not '
                         'the same as one that did not happen.', 'gap',
                         closes='the town census, compiled each year by the Town Clerk, which '
                                'counts every resident rather than sampling')])],
        table=dict(caption='Fifteen Census measures, two five-year samples', views=[dict(
            key='tests', label='%s against %s' % (W0, W), total_col=-1,
            kinds=['ledger', 'ledger', 'stated', 'stated'],
            columns=[W0, W, 'Change', 'Beyond the margin'],
            rows=[dict(label=x['label'], cells=[x['old_text'], x['new_text'], x['difference_text'],
                                                'yes' if x['distinguishable'] else 'no'])
                  for x in tests],
            note='Census Bureau ACS five-year estimates, each with its margin of error. The two '
                 'windows share no year. The last two columns are our arithmetic: a change is '
                 'beyond the margin when it exceeds the combined margin of its two estimates.')]),
        sources=S('acs5-2023-B01001-lunenburg.json', 'acs5-2018-B01001-lunenburg.json',
                  'acs5-2023-B11005-lunenburg.json', 'acs5-2018-B11005-lunenburg.json',
                  'census-acs.csv'),
        finding_figures={'a': N(pop['estimate']), 'b': N(hh['estimate'])})

    # ------------------------------------------------ residents by age
    ages = {g['key']: g for g in BN['ages']['groups']}
    ages0 = {g['key']: g for g in BN['previous']['ages']['groups']}
    sen, kid, mid, early, young = (ages[k] for k in ('senior', 'children', 'middle', 'early', 'young'))
    if round(sum(g['estimate'] for g in ages.values())) != round(pop['estimate']):
        fail('the age groups no longer sum to the population')
    ts = next(x for x in tests if x['label'] == 'Share of the town 65 and over')
    if ts['distinguishable']:
        fail('the 65-and-over share now clears its margin; rewrite the age page')
    out['residents-by-age'] = TP.page(
        'residents-by-age',
        '%s residents are 65 or over, %s of the town; %s are under 18. Both are sample estimates.'
        % (PM(sen['estimate'], sen['moe'])['text'], C.pct(sen['share']),
           PM(kid['estimate'], kid['moe'])['text']),
        [f('sen', PM(sen['estimate'], sen['moe'], 'residents'), 'residents 65 or over, %s sample' % W,
           'published', allow=CEN),
         f('sensh', P(sen['share']), 'of residents are 65 or over, ± %s' % C.points(sen['share_moe']),
           'published', {'m': PTS(sen['share_moe'])}),
         f('sensh0', P(ages0['senior']['share']), 'of residents were 65 or over, %s' % W0,
           'published', allow=CEN),
         f('kid', PM(kid['estimate'], kid['moe'], 'residents'), 'residents under 18, %s sample' % W,
           'published', allow=CEN),
         f('mid', PM(mid['estimate'], mid['moe'], 'residents'), 'residents 45 to 64, the largest band',
           'published', allow=('45 to 64',)),
         f('early', PM(early['estimate'], early['moe'], 'residents'), 'residents 25 to 44',
           'published', allow=('25 to 44',)),
         f('young', PM(young['estimate'], young['moe'], 'residents'), 'residents 18 to 24',
           'published', allow=('18 to 24',)),
         f('enrol', N(enrol, 'children'), 'enrolled in the district, %s, a DESE count' % C.fy(last_fy),
           'published', {'y': F(last_fy)})],
        [con('About %s residents are 65 or over, near the %s children the district enrols.'
             % (C.num(sen['estimate']), C.num(enrol)), ['sen', 'enrol', 'kid'],
             {'a': N(sen['estimate']), 'b': N(enrol)},
             notes=[step('The enrolment is a count; the age figure is a sample estimate with a '
                         'margin of %s either way, so the two are not measured alike.'
                         % C.num(sen['moe']), 'gap', {'m': N(sen['moe'])},
                         closes='the town census by age, held by the Town Clerk')]),
         con('The 65-and-over share went from %s to %s, a move inside the survey’s margin.'
             % (C.pct(ages0['senior']['share']), C.pct(sen['share'])), ['sensh0', 'sensh'],
             {'a': P(ages0['senior']['share']), 'b': P(sen['share'])})],
        table=dict(caption='Residents by age, two five-year samples', views=[dict(
            key='ages', label='%s and %s' % (W0, W), total_col=-1,
            kinds=['ledger', 'ledger', 'ledger'],
            columns=[W0, W, 'Share, %s' % W],
            rows=[dict(label=ages[k]['label'], cells=[ages0[k]['text'], ages[k]['text'],
                                                      '%s ± %s' % (ages[k]['share_text'], ages[k]['share_moe_text'])])
                  for k in ('children', 'young', 'early', 'middle', 'senior')],
            note='Census Bureau ACS table B01001, each band a sum of age cells with its margin of '
                 'error. Two estimates whose intervals overlap are not different.')]),
        sources=S('acs5-2023-B01001-lunenburg.json', 'acs5-2018-B01001-lunenburg.json',
                  'dese-enrollment-by-grade.xlsx'),
        finding_figures={'a': PM(sen['estimate'], sen['moe']), 'p': P(sen['share']),
                         'b': PM(kid['estimate'], kid['moe'])},
        finding_allow=('65', '18'))

    # ------------------------------------------------ households with children
    H = BN['households']
    wc, wo = H['with_child'], H['without_child']
    sh0 = BN['previous']['households']['share']
    out['households-with-children'] = TP.page(
        'households-with-children',
        '%s of %s households have a child under 18, about a third; how many use the schools is unpublished.'
        % (PM(wc['estimate'], wc['moe'])['text'], C.num(hh['estimate'])),
        [f('wc', PM(wc['estimate'], wc['moe'], 'households'), 'households with a child under 18, %s' % W,
           'published', allow=CEN + ('18',)),
         f('wcsh', P(H['share']), 'of households, ± %s' % C.points(H['share_moe']), 'published',
           {'m': PTS(H['share_moe'])}),
         f('wo', PM(wo['estimate'], wo['moe'], 'households'), 'households with no child under 18',
           'published', allow=('18',)),
         f('wcsh0', P(sh0), 'of households had a child under 18, %s' % W0, 'published',
           allow=CEN + ('18',)),
         f('enrol', N(enrol, 'children'), 'enrolled in the district, %s' % C.fy(last_fy),
           'published', {'y': F(last_fy)}),
         f('lps', None, 'households with a child in the Lunenburg schools', 'gap',
           closes='a count of distinct households with a child enrolled, from the district’s '
                  'student information system')],
        [con('About a third of households have a child under 18: %s, with a margin of %s.'
             % (C.pct(H['share']), C.points(H['share_moe'])), ['wc', 'wcsh', 'wo'],
             {'p': P(H['share']), 'm': PTS(H['share_moe'])}, allow=('18',),
             notes=[step('That is a ceiling on homes using the town’s schools: it counts children '
                         'at Monty Tech, private and charter schools, and children too young for '
                         'school.', 'gap',
                         closes='a count of distinct households with a child enrolled, from the '
                                'district’s student information system')]),
         con('The share was %s in %s; the difference is inside the margin.' % (C.pct(sh0), W0),
             ['wcsh0', 'wcsh'], {'p': P(sh0)}, allow=CEN),
         con('No published record joins a child to a household to a school.', ['lps', 'enrol'])],
        sources=S('acs5-2023-B11005-lunenburg.json', 'acs5-2018-B11005-lunenburg.json',
                  'dese-enrollment-by-grade.xlsx'),
        finding_figures={'a': PM(wc['estimate'], wc['moe']), 'b': N(hh['estimate'])},
        finding_allow=('18',))

    # ------------------------------------------------ household income
    I, I0, R = BN['income'], BN['previous']['income'], BN['rank']
    inc, inc0 = I['all_households'], I0['all_households']
    pp = BN['per_pupil']['last']
    tinc = next(x for x in tests if x['label'] == 'Median household income')
    if tinc['distinguishable']:
        fail('median income now clears its margin; rewrite the income page')
    RANK = figure(R['rank'], R['rank_text'], 'municipalities')
    OVER = figure(R['overlap'], R['overlap_text'], 'municipalities')
    PPR = figure(pp['rank'], pp['rank_text'], 'districts')
    out['household-income'] = TP.page(
        'household-income',
        'Median household income is %s ± %s on a sample, ranking %s Massachusetts municipalities.'
        % (C.usd(inc['estimate']), C.usd(inc['moe']), R['rank_text']),
        [f('inc', U(inc['estimate']), 'median household income, ± %s, %s' % (C.usd(inc['moe']), W),
           'published', {'m': U(inc['moe'])}, allow=CEN),
         f('rank', RANK, 'Massachusetts municipalities, ranked on that median', 'published'),
         f('over', OVER, 'municipalities whose interval overlaps (our test)', 'published'),
         f('inc0', U(inc0['estimate']), 'median household income, ± %s, %s'
           % (C.usd(inc0['moe']), W0), 'published', {'m': U(inc0['moe'])}, allow=CEN),
         f('pp', PPR, 'school districts on spending per pupil, %s' % C.fy(pp['fy']), 'published',
           {'y': F(pp['fy'])})],
        [con('Lunenburg ranks %s on income, but %s have intervals overlapping its own.'
             % (R['rank_text'], R['overlap_text']), ['rank', 'over', 'inc'],
             {'r': RANK, 'o': OVER}),
         con('Median income was %s in %s; the rise to %s is inside the margin.'
             % (C.usd(inc0['estimate']), W0, C.usd(inc['estimate'])), ['inc0', 'inc'],
             {'a': U(inc0['estimate']), 'b': U(inc['estimate'])}, allow=CEN),
         con('On spending per pupil the district ranked %s in %s, a different set and measure.'
             % (pp['rank_text'], C.fy(pp['fy'])), ['pp', 'rank'], {'r': PPR, 'y': F(pp['fy'])},
             notes=[step('Nothing here establishes what a town of this income spends per pupil; '
                         'the two ranks are drawn over different sets.', 'gap',
                         closes='nothing published sets income beside spending per pupil for '
                                'one set of places')])],
        sources=S('acs5-2023-B19013-massachusetts-lunenburg.json',
                  'acs5-2018-B19013-massachusetts-lunenburg.json'),
        finding_figures={'a': U(inc['estimate']), 'm': U(inc['moe']), 'r': RANK})

    # ------------------------------------------------ income by age
    bands = {b['label']: b for b in I['bands']}
    bands0 = {b['label']: b for b in I0['bands']}
    sn, md, yg = bands['65 and over'], bands['45 to 64'], bands['25 to 44']
    gap = BN['senior_gap']
    ratio = 100.0 * sn['estimate'] / md['estimate']
    if abs(ratio - gap['share']) > 1e-9:
        fail('the senior income share no longer recomputes')
    tsn = next(x for x in tests if x['label'] == 'Median income, householder 65 and over')
    if not tsn['distinguishable'] or tsn['old'] != bands0['65 and over']['estimate']:
        fail('the 65-and-over income change no longer clears its margin as the page says')
    out['income-by-age'] = TP.page(
        'income-by-age',
        'A household headed by someone 65 or over has a median income of %s, %s of a 45-to-64 household’s.'
        % (C.usd(sn['estimate']), C.pct(ratio)),
        [f('sn', U(sn['estimate']), 'householder 65 or over, ± %s, %s' % (C.usd(sn['moe']), W),
           'published', {'m': U(sn['moe'])}, allow=CEN + ('65',)),
         f('md', U(md['estimate']), 'householder 45 to 64, ± %s' % C.usd(md['moe']), 'published',
           {'m': U(md['moe'])}, allow=('45 to 64',)),
         f('yg', U(yg['estimate']), 'householder 25 to 44, ± %s' % C.usd(yg['moe']), 'published',
           {'m': U(yg['moe'])}, allow=('25 to 44',)),
         f('ratio', P(ratio), 'the 65-and-over median against 45 to 64 (ours)', 'published',
           allow=('65', '45 to 64')),
         f('sn0', U(tsn['old']), 'householder 65 or over, ± %s, %s' % (C.usd(tsn['old_moe']), W0),
           'published', {'m': U(tsn['old_moe'])}, allow=CEN + ('65',)),
         f('levy', None, 'property tax paid by households 65 and over', 'gap', allow=('65',),
           closes='the Assessors’ commitment list with exemptions granted, joined to the town '
                  'census by age of owner')],
        [con('A 65-and-over household’s median income is %s of a 45-to-64 household’s.'
             % C.pct(ratio), ['sn', 'md', 'ratio'], {'p': P(ratio)}, allow=('65', '45'),
             notes=[step('These are two medians of two sets of households, not one household’s '
                         'income falling with age. Income is not savings, equity or a tax bill.',
                         'gap', closes='the Assessors’ exemption list joined to the town census '
                                       'by age of owner')]),
         con('The 65-and-over median rose from %s to %s, one of the few changes beyond the margin.'
             % (C.usd(tsn['old']), C.usd(sn['estimate'])), ['sn0', 'sn'],
             {'a': U(tsn['old']), 'b': U(sn['estimate'])}, allow=('65',),
             notes=[step('Better-off retirees moving in, or people working longer, would fit; the '
                         'survey does not say which.', 'hypothesis')]),
         con('How much of the levy households headed by someone 65 or over pay is not published.',
             ['levy'], allow=('65',))],
        said=[said(BN, 'fixed-incomes')],
        sources=S('acs5-2023-B19049-lunenburg.json', 'acs5-2018-B19049-lunenburg.json'),
        finding_figures={'a': U(sn['estimate']), 'p': P(ratio)}, finding_allow=('65', '45', '64'))

    # ------------------------------------------------ owners and renters
    TN, TN0 = BN['tenure'], BN['previous']['tenure']
    pc = PO['parcels']
    dls_sf = bills[pb['last_fy']]['parcels']
    out['owners-and-renters'] = TP.page(
        'owners-and-renters',
        '%s of occupied homes are owner-occupied, %s households, on a sample estimate.'
        % (C.pct(TN['owner_share']), PM(TN['owner']['estimate'], TN['owner']['moe'])['text']),
        [f('own', PM(TN['owner']['estimate'], TN['owner']['moe'], 'households'),
           'owner-occupied homes, %s sample' % W, 'published', allow=CEN),
         f('ownsh', P(TN['owner_share']), 'of occupied homes, ± %s' % C.points(TN['owner_share_moe']),
           'published', {'m': PTS(TN['owner_share_moe'])}),
         f('rent', PM(TN['renter']['estimate'], TN['renter']['moe'], 'households'),
           'renter-occupied homes, %s sample' % W, 'published', allow=CEN),
         f('ownsh0', P(TN0['owner_share']), 'of occupied homes were owned, %s' % W0, 'published',
           allow=CEN),
         f('sf', N(dls_sf, 'homes'), 'single-family homes, %s, the state’s count' % C.fy(pb['last_fy']),
           'published', {'y': F(pb['last_fy'])}),
         f('sfa', N(pc['single_family'], 'homes'), 'single-family homes in the assessor’s %s file'
           % C.fy(pc['fy']), 'published', {'y': F(pc['fy'])}),
         f('parcels', N(pc['parcels'], 'parcels'), 'parcels of every kind in that file', 'published')],
        [con('%s of occupied homes are owned, so a levy change reaches most households as a bill.'
             % C.pct(TN['owner_share']), ['own', 'ownsh', 'rent'], {'p': P(TN['owner_share'])},
             notes=[step('A renting household pays through its rent. How much of a levy increase '
                         'reaches a rent, and how fast, is not measured.', 'gap',
                         closes='a survey of Lunenburg rents over several years, which nobody '
                                'publishes')]),
         con('The owned share was %s in %s; the difference is inside the margin.'
             % (C.pct(TN0['owner_share']), W0), ['ownsh0', 'ownsh'], {'p': P(TN0['owner_share'])},
             allow=CEN),
         con('Two published counts of single-family homes read %s and %s.'
             % (C.num(dls_sf), C.num(pc['single_family'])), ['sf', 'sfa', 'parcels'],
             {'a': N(dls_sf), 'b': N(pc['single_family'])},
             notes=[step('Neither counts condominiums, two- and three-family homes or apartments, '
                         'and neither is a count of households.', 'gap',
                         closes='the assessors’ parcel counts by use code, every class')])],
        sources=S('acs5-2023-B25003-lunenburg.json', 'acs5-2018-B25003-lunenburg.json',
                  'AvgSingleFamTaxBill.xlsx', 'L3_SHP_M162_LUNENBURG.zip'),
        finding_figures={'p': P(TN['owner_share']),
                         'a': PM(TN['owner']['estimate'], TN['owner']['moe'])})

    # ------------------------------------------------ average tax bill
    ten, sf0 = pb['ten'], pb['since_first']
    y0, y1 = pb['span_from_fy'], pb['last_fy']
    b0, b1 = bills[y0], bills[y1]
    if (b0['bill'], b1['bill'], b0['value'], b1['value']) != (ten['bill_from'], ten['bill_to'],
                                                             ten['value_from'], ten['value_to']):
        fail('property-owners.json: the ten-year change is not the series’ own rows')
    bch, vch, rch = (100 * (b1[k] / b0[k] - 1) for k in ('bill', 'value', 'rate'))
    first = bills[pb['first_fy']]
    bch_all = 100 * (b1['bill'] / first['bill'] - 1)
    RATE = lambda v: figure(v, '$%.2f' % v, 'per $1,000 of value')
    YA, YB = F(y0), F(y1)
    out['average-tax-bill'] = TP.page(
        'average-tax-bill',
        'The average single-family bill was %s in %s, up %s in ten years while the tax rate fell %s.'
        % (C.usd(b1['bill']), C.fy(y1), C.pct(bch), C.pct(-rch)),
        [f('b1', U(b1['bill']), 'average single-family bill, %s' % C.fy(y1), 'published', {'y': YB}),
         f('v1', U(b1['value']), 'average single-family value, %s' % C.fy(y1), 'published', {'y': YB}),
         f('r1', RATE(b1['rate']), 'tax rate per $1,000, %s (derived)' % C.fy(y1), 'published',
           {'y': YB}, allow=('$1,000',)),
         f('b0', U(b0['bill']), 'average single-family bill, %s' % C.fy(y0), 'published', {'y': YA}),
         f('v0', U(b0['value']), 'average single-family value, %s' % C.fy(y0), 'published', {'y': YA}),
         f('r0', RATE(b0['rate']), 'tax rate per $1,000, %s (derived)' % C.fy(y0), 'published',
           {'y': YA}, allow=('$1,000',)),
         f('bch', P(bch), 'rise in the bill, ten years (our arithmetic)', 'published'),
         f('vch', P(vch), 'rise in the value, ten years (our arithmetic)', 'published'),
         f('bfirst', U(first['bill']), 'average bill, %s, the first year DLS publishes'
           % C.fy(pb['first_fy']), 'published', {'y': F(pb['first_fy'])})],
        [con('In ten years the average home’s value rose %s and its bill %s; the rate fell %s.'
             % (C.pct(vch), C.pct(bch), C.pct(-rch)), ['v0', 'v1', 'b0', 'b1', 'vch', 'bch', 'r0', 'r1'],
             {'v': P(vch), 'b': P(bch), 'r': P(-rch)}),
         con('Proposition 2½ caps the levy, not values: the rate is the levy spread over total value.',
             ['r0', 'r1'], allow=('2½',)),
         con('Since %s the average bill has risen %s, from %s to %s.'
             % (C.fy(pb['first_fy']), C.pct(bch_all, 0), C.usd(first['bill']), C.usd(b1['bill'])),
             ['bfirst', 'b1'], {'y': F(pb['first_fy']), 'p': P(bch_all, 0), 'a': U(first['bill']),
                                'b': U(b1['bill'])},
             notes=[step('This is the town-wide average home. Any one household’s bill depends on '
                         'its own value and any exemption or abatement it holds.', 'gap',
                         closes='the Assessors’ commitment list, by parcel, with exemptions')])],
        table=dict(caption='The average single-family home and its bill, by year', views=[dict(
            key='bills', label='Last twenty years', total_col=2, kinds=['ledger', 'stated', 'ledger'],
            columns=['Average value', 'Tax rate', 'Average bill'],
            rows=[dict(label=C.fy(y), cells=[C.usd(bills[y]['value']), '$%.2f' % bills[y]['rate'],
                                             C.usd(bills[y]['bill'])])
                  for y in sorted(bills, reverse=True)[:20]],
            note='DLS Average Single-Family Tax Bill. The rate is derived, the bill divided by the '
                 'average value, per thousand dollars.')]),
        sources=S('AvgSingleFamTaxBill.xlsx'),
        finding_figures={'a': U(b1['bill']), 'y': YB, 'b': P(bch), 'r': P(-rch)})

    # ------------------------------------------------ against the neighbours
    nb = pb['neighbours']
    if [r['town'] for r in nb] != [r['town'] for r in sorted(nb, key=lambda r: -r['bill'])]:
        fail('the neighbour table is not in bill order')
    pos = 1 + [r['town'] for r in nb].index('Lunenburg')
    if pos != pb['position'] or len(nb) != pb['of']:
        fail('Lunenburg’s position among the neighbours no longer recomputes')
    med = statistics.median(r['bill'] for r in nb if r['town'] != 'Lunenburg')
    if med != pb['neighbour_median_bill']:
        fail('the neighbour median no longer recomputes')
    hi, lo = nb[0], nb[-1]
    POS = figure(pos, '%s of %d' % ({1: '1st', 2: '2nd', 3: '3rd'}.get(pos, '%dth' % pos), len(nb)),
                 'towns')
    SW = figure(pb['statewide_rank'], '%d of %d' % (pb['statewide_rank'], pb['statewide_of']),
                'municipalities')
    out['tax-bill-neighbours'] = TP.page(
        'tax-bill-neighbours',
        'At %s, the average bill is %s nearby towns and %s statewide.'
        % (C.usd(lun_nb['bill']), POS['text'], SW['text']),
        [f('bill', U(lun_nb['bill']), 'Lunenburg’s average bill, %s' % C.fy(y1), 'published', {'y': YB}),
         f('pos', POS, 'among this project’s nearby towns, by bill', 'published'),
         f('sw', SW, 'rank statewide, highest bill first', 'published'),
         f('med', U(med), 'median of the ten neighbours’ bills (ours)', 'published'),
         f('hi', U(hi['bill']), '%s, the highest of them' % hi['town'], 'published'),
         f('lo', U(lo['bill']), '%s, the lowest' % lo['town'], 'published'),
         f('pct', P(100 * lun_nb['bill_pct_income']), 'Lunenburg’s bill as a share of income per capita',
           'published'),
         f('ipc', U(lun_nb['income_per_capita']), 'income per capita, as DLS prints it', 'published')],
        [con('The average bill sits in the middle: below the neighbours’ median of %s.' % C.usd(med),
             ['bill', 'pos', 'med', 'hi', 'lo'], {'m': U(med)}),
         con('The bill is %s of income per capita here, a ratio DLS prints for every town.'
             % C.pct(100 * lun_nb['bill_pct_income']), ['pct', 'ipc', 'sw'],
             {'p': P(100 * lun_nb['bill_pct_income'])},
             notes=[step('What each town buys with its bill, in services, schools and debt, is not '
                         'in this file, so a lower bill is not a cheaper town.', 'gap',
                         closes='each town’s spending by function as filed with DLS, set beside '
                                'its bill')])],
        table=dict(caption='The average single-family bill, %s, nearby towns' % C.fy(y1), views=[dict(
            key='towns', label='Highest bill first', total_col=0, kinds=['ledger', 'ledger', 'ledger'],
            columns=['Average bill', 'Average value', 'Bill / income per capita'],
            rows=[dict(label=r['town'], cells=[C.usd(r['bill']), C.usd(r['value']),
                                               C.pct(100 * r['bill_pct_income'])]) for r in nb],
            note='DLS Average Single-Family Tax Bill. The ten towns are the set this project '
                 'compares Lunenburg with on this measure.')]),
        sources=S('AvgSingleFamTaxBill.xlsx'),
        finding_figures={'a': U(lun_nb['bill']), 'p': POS, 's': SW})

    # ------------------------------------------------ years in the home
    c23, c18 = PO['census']['2023'], PO['census']['2018']
    b10, b80 = c23['before_2010'], c23['since_1980s']
    if (c23['owners'], c23['vintage']) != (TN['owner']['estimate'], 2023):
        fail('the moved-in table is not the owners on the tenure page')
    MY = lambda v: figure(v, str(v), 'year')
    out['years-in-the-home'] = TP.page(
        'years-in-the-home',
        '%s owner households moved in before 2010, about half; the median owner moved in in %d.'
        % (PM(b10['households'], b10['moe'])['text'], c23['median_moved_in']),
        [f('b10', PM(b10['households'], b10['moe'], 'households'), 'owners in the home since before 2010',
           'published', allow=('2010',)),
         f('b10sh', P(100 * b10['share']), 'of %s owner households, %s' % (C.num(c23['owners']), W),
           'published', {'o': N(c23['owners'])}, allow=CEN),
         f('b80', PM(b80['households'], b80['moe'], 'households'), 'owners in the home since 1989 or earlier',
           'published', allow=('1989',)),
         f('b80sh', P(100 * b80['share']), 'of owner households, since 1989 or earlier', 'published',
           allow=('1989',)),
         f('med', MY(c23['median_moved_in']), 'median year the owner moved in, %s sample' % W,
           'published', allow=CEN),
         f('med0', MY(c18['median_moved_in']), 'the same median, %s sample' % W0, 'published',
           allow=CEN)],
        [con('About half of owner households, %s, have been in the house since before 2010.'
             % C.pct(100 * b10['share']), ['b10', 'b10sh'], {'p': P(100 * b10['share'])},
             allow=('2010',)),
         con('%s owner households have been in the house since 1989 or earlier.'
             % PM(b80['households'], b80['moe'])['text'], ['b80', 'b80sh'],
             {'a': PM(b80['households'], b80['moe'])}, allow=('1989',),
             notes=[step('Whether long-tenured owners can carry the bill is not shown: the Census '
                         'does not publish tenure against income for a town this size.', 'gap',
                         closes='the Assessors’ exemption list joined to the town census')]),
         con('The median owner’s move-in year was %d on the %s sample and %d on the %s one.'
             % (c18['median_moved_in'], W0, c23['median_moved_in'], W), ['med0', 'med'],
             {'a': MY(c18['median_moved_in']), 'b': MY(c23['median_moved_in'])}, allow=CEN,
             notes=[step('The Census publishes the median without a margin, so whether the move '
                         'is larger than the survey’s noise is not known.', 'gap',
                         closes='the town census, which records when each household arrived')])],
        table=dict(caption='Owner households by the year they moved in, %s' % W, views=[dict(
            key='moved', label='Census table B25038, owners', total_col=-1,
            kinds=['ledger', 'ledger', 'stated'], columns=['Households', 'Margin', 'Share'],
            rows=[dict(label=r['label'], cells=[C.num(r['households']), '± %s' % C.num(r['moe']),
                                                C.pct(100 * r['share'])]) for r in c23['bands']],
            note='Census Bureau ACS five-year sample. The share is our arithmetic on the owners '
                 'total, and carries the margin of both estimates.')]),
        sources=S('acs5-2023-B25038-lunenburg.json', 'acs5-2023-B25039-lunenburg.json',
                  'acs5-2018-B25039-lunenburg.json'),
        finding_figures={'a': PM(b10['households'], b10['moe']), 'm': MY(c23['median_moved_in'])},
        finding_allow=('2010',))

    # ------------------------------------------------ bill by deed year
    db = pc['bands']
    new, old = db[0], db[-1]
    if (new['label'], old['label']) != ('2021 or later', 'before 1986'):
        fail('the deed bands are not the ones this page names')
    dratio = 100.0 * old['median_bill'] / new['median_bill']
    if abs(dratio / 100 - pc['earliest_band_bill_ratio']) > 1e-9:
        fail('the long-held against newest bill ratio no longer recomputes')
    if sum(b['homes'] for b in db) != pc['single_family']:
        fail('the deed bands no longer sum to the single-family count')
    RT = figure(pc['rate'], '$%.2f' % pc['rate'], 'per $1,000 of value')
    out['bill-by-deed-year'] = TP.page(
        'bill-by-deed-year',
        'A home last deeded before 1986 would pay a median %s before exemptions; one deeded since 2021, %s.'
        % (C.usd(old['median_bill']), C.usd(new['median_bill'])),
        [f('old', U(old['median_bill']), 'median bill, homes last deeded before 1986 (ours)',
           'estimate', allow=('1986',)),
         f('new', U(new['median_bill']), 'median bill, homes deeded since 2021 (ours)', 'estimate',
           allow=('2021',)),
         f('ratio', P(dratio), 'the first against the second (ours)', 'estimate'),
         f('vold', U(old['median_value']), 'median assessed value, deeded before 1986', 'published',
           allow=('1986',)),
         f('vnew', U(new['median_value']), 'median assessed value, deeded since 2021', 'published',
           allow=('2021',)),
         f('rate', RT, 'tax rate per $1,000, %s' % C.fy(pc['fy']), 'published', {'y': F(pc['fy'])},
           allow=('$1,000',)),
         f('nom', N(pc['nominal']['deeds'], 'deeds'), 'last deeds that were nominal transfers',
           'published'),
         f('nomsh', P(100 * pc['nominal']['share']), 'of %s single-family homes (our arithmetic)'
           % C.num(pc['single_family']), 'published', {'n': N(pc['single_family'])})],
        [con('Long-held homes pay %s of what recently bought ones do: the bill follows today’s value.'
             % C.pct(dratio), ['old', 'new', 'ratio', 'vold', 'vnew', 'rate'], {'p': P(dratio)},
             notes=[step('These bills are value times the rate with no exemption or abatement '
                         'applied, so they are our estimate, not anybody’s bill.', 'gap',
                         closes='the Assessors’ commitment list, by parcel, with exemptions')]),
         con('A third of last deeds, %s, are nominal transfers, so a deed year is not an arrival year.'
             % C.num(pc['nominal']['deeds']), ['nom', 'nomsh'], {'n': N(pc['nominal']['deeds'])},
             notes=[step('A transfer into a trust or within a family resets the date without '
                         'anybody moving.', 'gap',
                         closes='the town census, which records when each household arrived')])],
        table=dict(caption='Single-family homes by the year of their last deed, %s' % C.fy(pc['fy']),
                   views=[dict(
            key='deeds', label='The assessor’s parcel file', total_col=-1,
            kinds=['ledger', 'ledger', 'stated', 'ledger'],
            columns=['Homes', 'Median value', 'Median bill', 'Median last sale'],
            rows=[dict(label=b['label'], cells=[C.num(b['homes']), C.usd(b['median_value']),
                                                C.usd(b['median_bill']),
                                                C.usd(b['median_sale_price']) if b['median_sale_price'] else None])
                  for b in db],
            note='MassGIS Level 3 parcels, single-family use codes. The bill is our estimate: value '
                 'times the year’s rate, no exemption applied. The sale price leaves out nominal '
                 'transfers.')]),
        sources=S('L3_SHP_M162_LUNENBURG.zip'),
        finding_figures={'a': U(old['median_bill']), 'b': U(new['median_bill'])},
        finding_allow=('1986', '2021'))

    # ------------------------------------------------ homes and enrolment
    ser = HS['series']
    s0, s1 = ser[0], ser[-1]
    peak = max(ser, key=lambda r: r['students'])
    steps_ = list(zip(ser, ser[1:]))
    fell = sum(1 for a, b in steps_ if b['homes'] < a['homes'])
    if fell != 0:
        fail('single-family homes fell in %d steps; rewrite the homes page' % fell)
    w5 = HS['window5']
    r5a = next(r for r in ser if r['fy'] == w5['first_fy'])
    if (s1['homes'] - r5a['homes'], s1['students'] - r5a['students']) != (w5['homes'], w5['students']):
        fail('the five-year window no longer recomputes')
    for r in ser:
        if abs(round(100.0 * r['students'] / r['homes'], 1) - r['students_per_100_homes']) > 1e-9:
            fail('students per hundred homes no longer recomputes for %s' % C.fy(r['fy']))
    D = lambda v: figure(v, '%.1f' % v, 'students per 100 homes')
    out['homes-and-enrolment'] = TP.page(
        'homes-and-enrolment',
        '%s more single-family homes since %s; enrolment is %s below its %s peak.'
        % (C.num(s1['homes'] - s0['homes']), C.fy(s0['fy']), C.num(peak['students'] - s1['students']),
           C.fy(peak['fy'])),
        [f('h0', N(s0['homes'], 'homes'), 'single-family homes, %s' % C.fy(s0['fy']), 'published',
           {'y': F(s0['fy'])}),
         f('h1', N(s1['homes'], 'homes'), 'single-family homes, %s' % C.fy(s1['fy']), 'published',
           {'y': F(s1['fy'])}),
         f('pk', N(peak['students'], 'children'), 'enrolled, %s, the peak' % C.fy(peak['fy']),
           'published', {'y': F(peak['fy'])}),
         f('st1', N(s1['students'], 'children'), 'enrolled, %s' % C.fy(s1['fy']), 'published',
           {'y': F(s1['fy'])}),
         f('d0', D(s0['students_per_100_homes']), 'students per hundred homes, %s (ours)' % C.fy(s0['fy']),
           'published', {'y': F(s0['fy'])}),
         f('d1', D(s1['students_per_100_homes']), 'students per hundred homes, %s (ours)' % C.fy(s1['fy']),
           'published', {'y': F(s1['fy'])}),
         f('h5', figure(w5['homes'], '+%s' % C.num(w5['homes']), 'homes'),
           'single-family homes, %s to %s' % (C.fy(w5['first_fy']), C.fy(w5['last_fy'])),
           'published', {'a': F(w5['first_fy']), 'b': F(w5['last_fy'])}),
         f('s5', figure(w5['students'], '−%s' % C.num(-w5['students']), 'children'),
           'enrolled children, same years', 'published')],
        [con('Single-family homes never fell between two years the record holds; enrolment peaked in %s.'
             % C.fy(peak['fy']), ['h0', 'h1', 'pk', 'st1'], {'y': F(peak['fy'])}),
         con('Students per hundred homes fell from %.1f to %.1f.'
             % (s0['students_per_100_homes'], s1['students_per_100_homes']), ['d0', 'd1'],
             {'a': D(s0['students_per_100_homes']), 'b': D(s1['students_per_100_homes'])},
             notes=[step('Fewer children per home, older households, children schooled elsewhere and '
                         'new homes bought by households without children all fit; these two counts '
                         'separate none of them.', 'hypothesis')]),
         con('In the last five years: %s more homes and %s fewer enrolled children.'
             % (C.num(w5['homes']), C.num(-w5['students'])), ['h5', 's5'],
             {'a': N(w5['homes']), 'b': N(-w5['students'])},
             notes=[step('The homes series is single-family parcels only; condominiums and '
                         'apartments added in the same years are not in it.', 'gap',
                         closes='the assessors’ parcel counts by use code for every year, '
                                'including condominiums and multi-family')])],
        table=dict(caption='Single-family homes and enrolled children, by year', views=[dict(
            key='series', label='%s to %s' % (C.fy(s0['fy']), C.fy(s1['fy'])), total_col=-1,
            kinds=['ledger', 'ledger', 'stated'],
            columns=['Single-family homes', 'Enrolled children', 'Students per 100 homes'],
            rows=[dict(label=C.fy(r['fy']), cells=[C.num(r['homes']), C.num(r['students']),
                                                   '%.1f' % r['students_per_100_homes']])
                  for r in reversed(ser)],
            note='DLS single-family parcels and DESE’s 1 October enrolment. A year missing from the '
                 'table is missing from one of the two files. The ratio is our arithmetic.')]),
        said=[said(BN, 'both-halves')],
        sources=S('AvgSingleFamTaxBill.xlsx', 'dese-enrollment-by-grade.xlsx'),
        finding_figures={'a': N(s1['homes'] - s0['homes']), 'y': F(s0['fy']),
                         'b': N(peak['students'] - s1['students']), 'z': F(peak['fy'])})

    # ------------------------------------------------ new growth
    ng = CB['new_growth']
    n1 = ng[-1]
    c1 = ng_csv[n1['fy']]
    big = max(ng, key=lambda r: r['total_levy'])
    low = min(ng, key=lambda r: r['total_levy'])
    lim_pct = float(c1['levy_pct_of_prior_limit'])
    res_pct = float(c1['res_pct_of_total'])
    if abs(100 * n1['residential_value'] / n1['total_value'] - res_pct) > 0.006:
        fail('the residential share of new value does not recompute for %s' % C.fy(n1['fy']))
    Y1 = F(n1['fy'])
    out['new-growth'] = TP.page(
        'new-growth',
        'New growth added %s to the %s levy limit, %s of the prior limit, on top of Proposition 2½.'
        % (C.usd(n1['total_levy']), C.fy(n1['fy']), C.pct(lim_pct, 2)),
        [f('ng', U(n1['total_levy']), 'added to the levy limit by new growth, %s' % C.fy(n1['fy']),
           'published', {'y': Y1}),
         f('pct', P(lim_pct, 2), 'of the prior year’s levy limit', 'published'),
         f('cap', figure(2.5, '2.5%', 'a year'), 'growth in the levy limit the statute allows',
           'statute'),
         f('val', U(n1['total_value']), 'new value certified, every class, %s' % C.fy(n1['fy']),
           'published', {'y': Y1}),
         f('res', U(n1['residential_value']), 'of it residential', 'published'),
         f('respct', P(res_pct), 'residential share of the new value', 'published'),
         f('big', U(big['total_levy']), 'added in %s, the largest year' % C.fy(big['fy']), 'published',
           {'y': F(big['fy'])}),
         f('low', U(low['total_levy']), 'added in %s, the smallest year' % C.fy(low['fy']), 'published',
           {'y': F(low['fy'])})],
        [con('New growth added %s to the limit in %s, beside the 2.5%% the statute allows.'
             % (C.pct(lim_pct, 2), C.fy(n1['fy'])), ['ng', 'pct', 'cap'],
             {'p': P(lim_pct, 2), 'y': Y1, 'c': figure(2.5, '2.5%')}),
         con('About half of %s’s new value was housing: %s of %s.'
             % (C.fy(n1['fy']), C.usd(n1['residential_value']), C.usd(n1['total_value'])),
             ['val', 'res', 'respct'], {'y': Y1, 'a': U(n1['residential_value']), 'b': U(n1['total_value'])}),
         con('Since %s the levy added by new growth ran from %s in %s to %s in %s.'
             % (C.fy(ng[0]['fy']), C.usd(low['total_levy']), C.fy(low['fy']), C.usd(big['total_levy']),
                C.fy(big['fy'])), ['low', 'big'],
             {'f': F(ng[0]['fy']), 'a': U(low['total_levy']), 'x': F(low['fy']),
              'b': U(big['total_levy']), 'z': F(big['fy'])},
             notes=[step('New growth is added once, then grows with the limit. What was built in '
                         'any year is not in the state’s file.', 'gap',
                         closes='the assessors’ new-growth worksheets, which list the parcels '
                                'behind each year’s figure')])],
        table=dict(caption='Certified new growth, by year', views=[dict(
            key='ng', label='%s to %s' % (C.fy(ng[0]['fy']), C.fy(n1['fy'])), total_col=0,
            kinds=['ledger', 'ledger', 'ledger', 'ledger'],
            columns=['Added to levy', 'New value', 'Residential value', 'Share of prior limit'],
            rows=[dict(label=C.fy(r['fy']), cells=[C.usd(r['total_levy']), C.usd(r['total_value']),
                                                   C.usd(r['residential_value']),
                                                   C.pct(float(ng_csv[r['fy']]['levy_pct_of_prior_limit']), 2)])
                  for r in reversed(ng)],
            note='DLS new growth file, Lunenburg rows, every column as the state prints it.')]),
        sources=S('new_growth.xlsx'),
        finding_figures={'a': U(n1['total_levy']), 'y': Y1, 'p': P(lim_pct, 2)},
        finding_allow=('2½',))

    # ------------------------------------------------ business building pace
    st = CB['step']
    rec = [r for r in ng if st['from_fy'] <= r['fy'] <= st['to_fy']]
    bef = [r for r in ng if st['before_from_fy'] <= r['fy'] <= st['before_to_fy']]
    if round(sum(r['non_residential_value'] for r in rec) / len(rec)) != st['avg_non_residential'] or \
            round(sum(r['non_residential_value'] for r in bef) / len(bef)) != st['avg_non_residential_before']:
        fail('commercial-base.json: the step averages no longer recompute')
    for r in ng:
        if r['total_value'] - r['residential_value'] != r['non_residential_value']:
            fail('non-residential new value is no longer total minus residential for %s' % C.fy(r['fy']))
    mult = st['avg_non_residential'] / st['avg_non_residential_before']
    nbest = max(ng, key=lambda r: r['non_residential_value'])
    top3 = sorted(ng, key=lambda r: -r['non_residential_value'])[:3]
    if sorted(r['fy'] for r in top3) != list(range(st['from_fy'], st['to_fy'] + 1)):
        fail('the three largest non-residential years are no longer the recent three')
    n23 = next(r for r in ng if r['fy'] == st['before_to_fy'])
    M = figure(mult, '%.1f times' % mult, 'the earlier pace')
    SPAN_R = '%s–%s' % (C.fy(st['from_fy']), C.fy(st['to_fy']))
    SPAN_B = '%s–%s' % (C.fy(st['before_from_fy']), C.fy(st['before_to_fy']))
    RF = {'a': F(st['from_fy']), 'b': F(st['to_fy'])}
    BF = {'c': F(st['before_from_fy']), 'd': F(st['before_to_fy'])}
    out['business-building-pace'] = TP.page(
        'business-building-pace',
        'Non-residential new growth averaged %s a year in %s, %s the pace before it.'
        % (C.usd(st['avg_non_residential']), SPAN_R, M['text']),
        [f('rec', U(st['avg_non_residential']), 'non-residential new value a year, %s' % SPAN_R,
           'published', RF),
         f('bef', U(st['avg_non_residential_before']), 'a year, %s' % SPAN_B, 'published', BF),
         f('mult', M, 'the recent pace against the earlier (our arithmetic)', 'published'),
         f('best', U(nbest['non_residential_value']), 'added in %s, the largest year' % C.fy(nbest['fy']),
           'published', {'y': F(nbest['fy'])}),
         f('y23', U(n23['non_residential_value']), 'added in %s, the year before the step'
           % C.fy(n23['fy']), 'published', {'y': F(n23['fy'])}),
         f('what', None, 'what was built, and where', 'gap',
           closes='the assessors’ new-growth worksheets for the step years, which list the parcels')],
        [con('Non-residential new growth ran %s its %s pace in %s.' % (M['text'], SPAN_B, SPAN_R),
             ['rec', 'bef', 'mult', 'best', 'y23'], dict({'m': M}, **RF, **BF),
             notes=[step('Equipment and utility plant, taxed as personal property, are inside this '
                         'figure with buildings; the file does not split them.', 'gap',
                         closes='the assessors’ new-growth worksheets, by class and parcel'),
                    step('Three years is the whole of the step; whether the pace holds is not known.',
                         'gap', closes='the certified new growth for the years after, as DLS '
                                       'publishes it')]),
         con('What was built, and where, is not in the state’s file: it certifies dollars, not buildings.',
             ['what'])],
        sources=S('new_growth.xlsx'),
        finding_figures=dict({'avg': U(st['avg_non_residential']), 'm': M}, **RF))

    # ------------------------------------------------ commercial share
    vals = {r['fy']: r for r in CB['values']}
    v1 = vals[CB['last_fy']]
    vpk = max(CB['values'], key=lambda r: r['cip_share'])
    vlo = min(CB['values'], key=lambda r: r['cip_share'])
    cip = v1['commercial_industrial'] + v1['personal']
    if abs(100 * cip / v1['total'] - v1['cip_share']) > 0.006:
        fail('the business share does not recompute for %s' % C.fy(v1['fy']))
    pre = vals[vlo['fy'] - 1]
    reval = 100 * (vlo['residential'] / pre['residential'] - 1)
    v22 = vals[CB['last_fy'] - 4]
    v02 = vals[CB['first_fy']]
    ci_step = 100 * (v1['commercial_industrial'] / v22['commercial_industrial'] - 1)
    ci_long = 100 * (v22['commercial_industrial'] / v02['commercial_industrial'] - 1)
    peers = CB['peers']
    if {p['fy'] for p in peers} != {v1['fy']} or \
            next(p['cip_share'] for p in peers if p['town'] == 'Lunenburg') != v1['cip_share']:
        fail('the peer shares are not the same year as Lunenburg’s')
    others = [p for p in peers if p['town'] != 'Lunenburg']
    higher = sum(1 for p in others if p['cip_share'] > v1['cip_share'])
    HI = figure(higher, '%d of %d' % (higher, len(others)), 'towns')
    SP = lambda v: figure(v, C.pct(v), '% of assessed value')
    out['commercial-share'] = TP.page(
        'commercial-share',
        'Business property is %s of the %s tax base, against %s in %s and %s in %s.'
        % (C.pct(v1['cip_share']), C.fy(v1['fy']), C.pct(vpk['cip_share']), C.fy(vpk['fy']),
           C.pct(vlo['cip_share']), C.fy(vlo['fy'])),
        [f('sh', SP(v1['cip_share']), 'business share of assessed value, %s' % C.fy(v1['fy']),
           'published', {'y': F(v1['fy'])}),
         f('pk', SP(vpk['cip_share']), 'the share in %s, the highest' % C.fy(vpk['fy']), 'published',
           {'y': F(vpk['fy'])}),
         f('lo', SP(vlo['cip_share']), 'the share in %s, the lowest' % C.fy(vlo['fy']), 'published',
           {'y': F(vlo['fy'])}),
         f('cip', U(cip), 'commercial, industrial and personal property', 'published'),
         f('tot', U(v1['total']), 'assessed value of every class, %s' % C.fy(v1['fy']), 'published',
           {'y': F(v1['fy'])}),
         f('reval', P(reval), 'rise in residential value in %s (our arithmetic)' % C.fy(vlo['fy']),
           'published', {'y': F(vlo['fy'])}),
         f('cistep', P(ci_step), 'rise in commercial and industrial value, %s–%s'
           % (C.fy(v22['fy']), C.fy(v1['fy'])), 'published', {'a': F(v22['fy']), 'b': F(v1['fy'])}),
         f('cilong', P(ci_long), 'the same, %s–%s' % (C.fy(v02['fy']), C.fy(v22['fy'])), 'published',
           {'a': F(v02['fy']), 'b': F(v22['fy'])}),
         f('hi', HI, 'compared towns with a larger business share', 'published')],
        [con('In %s residential value rose %s and the business share fell to %s.'
             % (C.fy(vlo['fy']), C.pct(reval), C.pct(vlo['cip_share'])), ['reval', 'lo', 'sh'],
             {'y': F(vlo['fy']), 'r': P(reval), 's': SP(vlo['cip_share'])},
             notes=[step('Rising home values alone would lower the share, since the base is mostly '
                         'homes; the file does not separate revaluation from building.',
                         'hypothesis')]),
         con('Commercial and industrial value rose %s in four years, after %s over the twenty before.'
             % (C.pct(ci_step), C.pct(ci_long)), ['cistep', 'cilong', 'cip', 'tot'],
             {'a': P(ci_step), 'b': P(ci_long)},
             notes=[step('How much of the rise is construction and how much is revaluation of what '
                         'stood is not split in this series.', 'gap',
                         closes='the assessors’ new-growth worksheets set against their revaluation '
                                'reports')]),
         con('%s compared towns have a larger business share than Lunenburg.'
             % HI['text'], ['hi', 'sh'], {'h': HI},
             notes=[step('A share compares towns of different size; it says nothing about what any '
                         'of them collects.', 'gap',
                         closes='each town’s levy by class, which DLS publishes separately')])],
        table=dict(caption='Business share of assessed value', views=[
            dict(key='towns', label='Compared towns, %s' % C.fy(v1['fy']), total_col=-1,
                 kinds=['ledger'], columns=['Business share'],
                 rows=[dict(label=p['town'], cells=[C.pct(p['cip_share'], 2)]) for p in peers],
                 note='DLS assessed values by class. The towns are the set this project compares '
                      'Lunenburg with.'),
            dict(key='years', label='Lunenburg, by year', total_col=-1,
                 kinds=['ledger', 'ledger', 'ledger', 'ledger'],
                 columns=['Residential', 'Commercial and industrial', 'Personal property', 'Business share'],
                 rows=[dict(label=C.fy(r['fy']), cells=[C.usd(r['residential']),
                                                        C.usd(r['commercial_industrial']),
                                                        C.usd(r['personal']), C.pct(r['cip_share'], 2)])
                       for r in sorted(CB['values'], key=lambda r: -r['fy'])],
                 note='DLS assessed values by class, as certified each year.')]),
        sources=S('assessedvalues.xlsx'),
        finding_figures={'a': P(v1['cip_share']), 'y': F(v1['fy']), 'b': P(vpk['cip_share']),
                         'x': F(vpk['fy']), 'c': P(vlo['cip_share']), 'z': F(vlo['fy'])})

    # ------------------------------------------------ the hub
    h = {}
    h['h-pop'] = f('h-pop', PM(pop['estimate'], pop['moe'], 'residents'), 'residents, %s sample' % W,
                   'published', allow=CEN)
    h['h-sen'] = f('h-sen', P(sen['share']), 'of residents 65 or over, ± %s' % C.points(sen['share_moe']),
                   'published', {'m': PTS(sen['share_moe'])})
    h['h-kid'] = f('h-kid', P(H['share']), 'of households with a child under 18', 'published',
                   allow=('18',))
    h['h-inc'] = f('h-inc', U(sn['estimate']), 'median income, householder 65 or over', 'published',
                   allow=('65',))
    h['h-surv'] = f('h-surv', SURV, 'Census measures that changed beyond the margin', 'published')
    h['h-levy'] = f('h-levy', None, 'property tax paid by households 65 and over', 'gap', allow=('65',),
                    closes='the Assessors’ commitment list with exemptions, joined to the town census')
    h['h-own'] = f('h-own', P(TN['owner_share']), 'of occupied homes owner-occupied', 'published')
    h['h-bill'] = f('h-bill', U(b1['bill']), 'average single-family bill, %s' % C.fy(y1), 'published',
                    {'y': YB})
    h['h-bch'] = f('h-bch', P(bch), 'rise in that bill in ten years', 'published')
    h['h-rch'] = f('h-rch', P(-rch), 'fall in the tax rate in the same years', 'published')
    h['h-pos'] = f('h-pos', POS, 'nearby towns, by average bill', 'published')
    h['h-homes'] = f('h-homes', N(s1['homes'] - s0['homes'], 'homes'), 'more single-family homes since %s'
                     % C.fy(s0['fy']), 'published', {'y': F(s0['fy'])})
    h['h-st'] = f('h-st', N(peak['students'] - s1['students'], 'children'), 'fewer enrolled than at the %s peak'
                  % C.fy(peak['fy']), 'published', {'y': F(peak['fy'])})
    h['h-ng'] = f('h-ng', P(lim_pct, 2), 'added to the levy limit by new growth, %s' % C.fy(n1['fy']),
                  'published', {'y': Y1})
    h['h-cip'] = f('h-cip', SP(v1['cip_share']), 'business share of the tax base, %s' % C.fy(v1['fy']),
                   'published', {'y': F(v1['fy'])})
    tiers = [
        LD.tier('Who lives here', [h['h-pop'], h['h-sen'], h['h-kid'], h['h-inc'], h['h-surv'],
                                   h['h-levy']]),
        LD.tier('Homes and the bill', [h['h-own'], h['h-bill'], h['h-bch'], h['h-rch'], h['h-pos']]),
        LD.tier('Growth', [h['h-homes'], h['h-st'], h['h-ng'], h['h-cip']]),
    ]
    hub_ladder = LD.ladder(tiers, [
        LD.conclusion('Every Census figure here is a sample; only %s changed beyond its margin.'
                      % SURV['text'], ['h-pop', 'h-surv'], {'s': SURV}),
        LD.conclusion('About a third of households have a child under 18; %s of residents are 65 or over.'
                      % C.pct(sen['share']), ['h-kid', 'h-sen'], {'p': P(sen['share'])}, allow=('18', '65')),
        LD.conclusion('The average bill rose %s in ten years while the tax rate fell %s.'
                      % (C.pct(bch), C.pct(-rch)), ['h-bill', 'h-bch', 'h-rch', 'h-pos'],
                      {'b': P(bch), 'r': P(-rch)}),
        LD.conclusion('Single-family homes never fell in the record; enrolment is %s below its %s peak.'
                      % (C.num(peak['students'] - s1['students']), C.fy(peak['fy'])),
                      ['h-homes', 'h-st'], {'a': N(peak['students'] - s1['students']), 'y': F(peak['fy'])}),
        LD.conclusion('New growth added %s to the %s levy limit; business is %s of the base.'
                      % (C.pct(lim_pct, 2), C.fy(n1['fy']), C.pct(v1['cip_share'])), ['h-ng', 'h-cip'],
                      {'p': P(lim_pct, 2), 'y': Y1, 'c': SP(v1['cip_share'])}),
        LD.conclusion('What households headed by someone 65 or over pay in property tax is not published.',
                      ['h-levy', 'h-inc', 'h-own'], allow=('65',)),
    ])
    out[HUB] = TP.hub(
        HUB,
        'About %s residents live in %s households, %s owner-occupied, on a Census sample. '
        'The average single-family bill was %s in %s, and the town has %s more single-family homes '
        'than in %s while enrolment fell.'
        % (C.num(pop['estimate']), C.num(hh['estimate']), C.pct(TN['owner_share']), C.usd(b1['bill']), C.fy(y1),
           C.num(s1['homes'] - s0['homes']), C.fy(s0['fy'])),
        hub_ladder,
        answer_figures={'a': N(pop['estimate']), 'b': N(hh['estimate']), 'o': P(TN['owner_share']),
                        'c': U(b1['bill']), 'y': YB,
                        'h': N(s1['homes'] - s0['homes']), 'z': F(s0['fy'])})

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
        stale = []
        for p, text in outs.items():
            cur = open(p, encoding='utf-8').read() if os.path.exists(p) else None
            if cur != text:
                stale.append(os.path.relpath(p, ROOT))
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('homes and taxes topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
