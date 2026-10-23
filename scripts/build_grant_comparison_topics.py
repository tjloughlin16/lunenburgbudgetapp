#!/usr/bin/env python3
"""Lunenburg's federal grant allocations against the districts it is compared with.

    python3 scripts/build_grant_comparison_topics.py           # write the two topic payloads
    python3 scripts/build_grant_comparison_topics.py --check   # fail if either would change

TJ, 22 October 2026 (notes/MASTER-PLAN.md item 10): *"create a report comparing our GRANT
setup to other districts to see what gaps we have or where we are better."*

TWO PAGES on the school-all-funds shelf, registered there through TOPIC_GENERATORS:

    grant-allocations-compared   the five grants every comparison district holds, per pupil
    grants-others-receive        the grants comparison districts are allocated and Lunenburg is not

THE DATA
  sources/data/dese-entitlement-allocations.csv   DESE's allocation pages, every district,
                                                  FY2017-FY2027 (extract_dese_entitlements.py)
  sources/data/dese-grant-opportunities.csv       DESE's open-grants list: each code's type and
                                                  eligibility text, quoted, never paraphrased
  sources/state-dese/er3w-dyti.json               DESE's district profile: the 1 October
                                                  headcount and the low-income, English-learner
                                                  and disability shares, by school year

THE COMPARISON SETS ARE NOT TYPED HERE. They are imported from build_town_comparison.py,
which defines them for /analysis/towns-like-us: the bordering towns and the peers this project
chose (NEIGHBOURS, PEERS, each mapped to the DISTRICT that schools it by DISTRICT_OF), and the
two cohorts the math picks (cohort() over IS_KEYS and DOES_KEYS). A town is not its district:
Ashby and Townsend are both North Middlesex, and the page compares districts.

THE JOIN IS BY DESE DISTRICT CODE, never by name: the profile's dist_code (`01620000`) and the
allocation page's district code (`0162`) are the same number. FITCHBURG CANNOT BE JOINED:
DESE's own select lists two districts labelled `Fitchburg` (0097 and 5884) and its code pages
name districts only by label, so extract_dese_entitlements.py leaves the code blank rather than
guess. Fitchburg is therefore left out and the page says so; it is not counted as a district
with no grants.

PER PUPIL = allocation / DESE's 1 October headcount for the same fiscal year (the profile's
`sy` is the fiscal year: Lunenburg's 2025 headcount of 1,563 is DESE's FY2025 enrolment).
FY2025 is the last year with a headcount, so it is the year compared; FY2026 and FY2027 are
shown in dollars only. The division is ours; both inputs are DESE's.

WHAT IS COMPARABLE. A (fund code, year) is compared only when its rows came off DESE's
by-fund-code page (`view=code`). For IDEA FY2018 DESE's code page answers with an error and the
four rows held came off by-district pages for the extractor's reconciliation districts, so that
year is a gap for every median, never a small sample. A blank amount is blank, never zero; a
district not on a code's page is NOT ON THE LIST -- which is what DESE printed -- and the page
says "not listed", not "received nothing".

WHAT THIS DOES NOT SHOW (rule 7). An allocation is formula output. A lower Title I or IDEA
figure is the formula's answer to the district's counts, not money Lunenburg failed to claim,
and the page says so; why IDEA per pupil is lower is not established, and is registered in
money-gaps.csv with the one document that would settle it. Competitive grants are not on these
pages at all.
"""
import argparse
import csv
import json
import os
import statistics as st
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
from brief import step  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
import build_town_comparison as TC  # noqa: E402

ME = os.path.basename(__file__)
T_PP, T_GAP = 'grant-allocations-compared', 'grants-others-receive'
ALLOC = os.path.join(ROOT, 'sources', 'data', 'dese-entitlement-allocations.csv')
OPPS = os.path.join(ROOT, 'sources', 'data', 'dese-grant-opportunities.csv')
PROFILE = TC.DESE
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json')
CSV_NAME = 'grant-allocations-compared.csv'
CSV_OUT = os.path.join(ROOT, 'fy28', 'public', 'docs', 'data', CSV_NAME)

LUN = 'Lunenburg'
YEAR = 2025                    # the last fiscal year DESE has a headcount for
FIRST, LAST = 2017, 2027       # the allocation pages held
# The five grants every comparison district is allocated. Order is the page's order.
FIVE = [('0305', 'Title I'), ('0140', 'Title II-A'), ('0309', 'Title IV-A'),
        ('0240', 'IDEA'), ('0262', 'Early childhood IDEA')]
IDEA = '0240'
TITLE_I = '0305'
TITLE_III = '0180'
# What a reader calls the other codes. Names only; every figure is read off the CSV.
SHORT = {'0180': 'Title III', '0186': 'Title III immigrant', '0184': 'Title III summer',
         '0400': 'Perkins secondary', '0401': 'Perkins postsecondary',
         '0274': 'Special education improvement', '0113': 'ESSER I', '0115': 'ESSER II',
         '0119': 'ESSER III', '0252': 'ARP IDEA', '0264': 'ARP early childhood IDEA',
         '0302': 'ARP homeless youth'}
SHORT.update(dict(FIVE))
SETS = [('border', "Bordering towns' districts"), ('peer', 'Peers we chose'),
        ('makeup', 'Alike in make-up'), ('behaviour', 'Alike in behaviour')]
SET_SHORT = {'border': 'border', 'peer': 'peer', 'makeup': 'make-up', 'behaviour': 'behaviour'}


def fail(msg):
    raise SystemExit('build_grant_comparison_topics: ' + msg)


def rows(path):
    with open(path, encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


def load():
    # ---- the comparison sets, from the comparison report itself
    frame, _ = TC.build_frame()
    makeup = [x['town'] for x in TC.cohort(frame, TC.IS_KEYS, 10)[0]]
    behaviour = [x['town'] for x in TC.cohort(frame, TC.DOES_KEYS, 10)[0]]
    named = dict(border=[TC.DISTRICT_OF[t] for t in TC.NEIGHBOURS],
                 peer=[TC.DISTRICT_OF[t] for t in TC.PEERS],
                 makeup=makeup, behaviour=behaviour)

    # ---- DESE's district profile: codes, headcount, shares
    with open(PROFILE, encoding='utf-8') as fh:
        raw = json.load(fh)
    code, prof = {}, {}
    want = {'Student Headcount': 'n', 'Low-Income % Headcount': 'li',
            'English learner % Headcount': 'el', 'Students with disabilities % Headcount': 'swd'}
    for r in raw:
        c = r['dist_code'][:4]
        if code.setdefault(r['dist_name'], c) != c:
            fail('profile name %r carries two codes' % r['dist_name'])
        k = want.get(r['ind_subcat'])
        v = TC.num(r.get('ind_value'))
        if k and v is not None:
            prof.setdefault(c, {}).setdefault(int(r['sy']), {})[k] = v

    # ---- the allocations
    alloc, names, view = {}, {}, {}
    nocode = set()
    for r in rows(ALLOC):
        k = (r['fund_code'], int(r['fy']))
        view.setdefault(k, set()).add('code' if 'view=code' in r['source_url'] else 'district')
        if not r['district_code']:
            nocode.add(r['district'])
            continue
        names[r['district_code']] = r['district']
        if r['amount'] != '':
            alloc[(r['district_code'],) + k] = int(r['amount'])
    comparable = {k for k, v in view.items() if v == {'code'}}

    lun = code[LUN]
    if (lun, IDEA, YEAR) not in alloc:
        fail('Lunenburg has no IDEA row for FY%d -- the join broke' % YEAR)
    if prof[lun][YEAR]['n'] < 1000:
        fail('Lunenburg headcount for FY%d looks wrong' % YEAR)

    # ---- resolve every named district to a code, refuse rather than drop silently
    members, excluded = {}, []
    for s, ds in named.items():
        for d in ds:
            c = code.get(d)
            if d in nocode:
                excluded.append(d)
                continue
            if c is None or not any(k[0] == c for k in alloc):
                fail('%s (%s set) does not resolve to a district on the allocation pages' % (d, s))
            members.setdefault(c, dict(name=d, sets=[]))
            if s not in members[c]['sets']:
                members[c]['sets'].append(s)
    excluded = sorted(set(excluded))
    if excluded != ['Fitchburg']:
        fail('expected only Fitchburg to be unattributable, got %s' % excluded)
    if lun in members:
        fail('Lunenburg is in its own comparison set')
    # every comparison district has a headcount in the comparison year
    for c, m in members.items():
        if not prof.get(c, {}).get(YEAR, {}).get('n'):
            fail('%s has no FY%d headcount' % (m['name'], YEAR))
    return dict(alloc=alloc, prof=prof, code=code, lun=lun, members=members, named=named,
                excluded=excluded, comparable=comparable, names=names)


def snapshot():
    """The archive key of the newest snapshot of DESE's allocation pages -- the one the
    extractor reads -- so a citation follows the data rather than a typed date."""
    base = os.path.join(ROOT, 'sources', 'state-dese', 'entitlements')
    newest = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))[-1]
    return 'state-dese/entitlements/' + newest


def opportunities():
    """DESE's open-grants list, by single fund code: (type, eligibility, detail url)."""
    out = {}
    for r in rows(OPPS):
        for fc in r['fund_code'].split():
            out[fc] = r
    return out


def per_pupil(D, c, fc, y):
    a = D['alloc'].get((c, fc, y))
    n = D['prof'].get(c, {}).get(y, {}).get('n')
    if a is None or not n or (fc, y) not in D['comparable']:
        return None
    return a / n


def median(vals):
    vals = [v for v in vals if v is not None]
    return st.median(vals) if vals else None


def usd0(v):
    return C.usd(v) if v is not None else ''


def build():
    D = load()
    lun, members, prof, alloc = D['lun'], D['members'], D['prof'], D['alloc']
    comp = sorted(members, key=lambda c: members[c]['name'])
    N = len(comp)
    in_set = lambda s: [c for c in comp if s in members[c]['sets']]

    def five_total(c, y):
        vs = [per_pupil(D, c, fc, y) for fc, _ in FIVE]
        return sum(vs) if all(v is not None for v in vs) else None

    # ------------------------------------------------------------ page one: per pupil
    lp = {fc: per_pupil(D, lun, fc, YEAR) for fc, _ in FIVE}
    if any(v is None for v in lp.values()):
        fail('Lunenburg is missing one of the five grants in FY%d' % YEAR)
    for c in comp:
        for fc, nm in FIVE:
            if per_pupil(D, c, fc, YEAR) is None:
                fail('%s has no %s row in FY%d; the page says all five are held by all' % (
                    members[c]['name'], nm, YEAR))
    idea_l = lp[IDEA]
    idea_all = [per_pupil(D, c, IDEA, YEAR) for c in comp]
    idea_med = median(idea_all)
    idea_below = sum(1 for v in idea_all if v < idea_l)
    ti_l = lp[TITLE_I]
    mk = in_set('makeup')
    ti_mk = median([per_pupil(D, c, TITLE_I, YEAR) for c in mk])
    li_l = prof[lun][YEAR]['li']
    li_mk = median([prof[c][YEAR]['li'] for c in mk])
    five_l = five_total(lun, YEAR)
    five_med = median([five_total(c, YEAR) for c in comp])
    # Every year since FY2017 that can be compared, Lunenburg's IDEA per pupil against the median
    years = list(range(FIRST, YEAR + 1))
    idea_years = [y for y in years if (IDEA, y) in D['comparable']]
    below_every = all(per_pupil(D, lun, IDEA, y) < median([per_pupil(D, c, IDEA, y) for c in comp])
                      for y in idea_years)
    if not below_every:
        fail('Lunenburg is no longer below the comparison median on IDEA in every comparable year')
    not_cmp = [y for y in years if y not in idea_years]
    if not_cmp != [2018]:
        fail('the years IDEA cannot be compared changed: %s' % not_cmp)
    # what each formula follows, across every district with a headcount (not only the sets)
    def corr(fc, share):
        xs, ys = [], []
        for c in prof:
            v = per_pupil(D, c, fc, YEAR)
            s = prof[c].get(YEAR, {}).get(share)
            if v is not None and s is not None:
                xs.append(s)
                ys.append(v)
        return TC.pearson(xs, ys), len(xs)
    r_ti, n_ti = corr(TITLE_I, 'li')
    r_idea, n_idea = corr(IDEA, 'swd')
    if not (r_ti > 0.6 and r_idea < 0.4):
        fail('the formula correlations moved: Title I %.2f, IDEA %.2f' % (r_ti, r_idea))

    U = lambda v: figure(round(v), C.usd(v))
    F = lambda y: figure(y, C.fy(y), 'fiscal year')
    Y = F(YEAR)
    f, con = LD.fact, TP.conclusion
    nfig = figure(N, C.num(N), 'districts')
    facts1 = [
        f('idea-l', U(idea_l), 'IDEA allocation per pupil, Lunenburg, %s' % C.fy(YEAR), 'published',
          {'y': Y}),
        f('idea-med', U(idea_med), 'IDEA, median of the %s comparison districts' % C.num(N),
          'published', {'n': nfig}),
        f('idea-below', figure(idea_below, '%s of %s' % (C.num(idea_below), C.num(N)), 'districts'),
          'comparison districts with less IDEA per pupil', 'published'),
        f('ti-l', U(ti_l), 'Title I per pupil, Lunenburg', 'published'),
        f('ti-mk', U(ti_mk), 'Title I, median of the districts alike in make-up', 'published'),
        f('li-l', figure(li_l, C.pct(li_l), '%'), 'Lunenburg pupils counted low-income', 'published'),
        f('li-mk', figure(li_mk, C.pct(li_mk), '%'), 'low-income, median of those alike in make-up',
          'published'),
        f('five-l', U(five_l), 'the five grants together, per pupil, Lunenburg', 'published'),
        f('five-med', U(five_med), 'the five together, comparison median', 'published'),
        f('r-ti', figure(round(r_ti, 2), '%.2f' % r_ti, 'correlation'),
          'Title I per pupil against low-income share, %s districts' % C.num(n_ti), 'published',
          {'n': figure(n_ti, C.num(n_ti), 'districts')}),
        f('r-idea', figure(round(r_idea, 2), '%.2f' % r_idea, 'correlation'),
          'IDEA per pupil against disability share, same districts', 'published'),
    ]
    q240 = opportunities().get(IDEA)
    conc1 = [
        con('IDEA, the largest grant, came to %s a pupil in %s; the comparison median was %s.'
            % (C.usd(idea_l), C.fy(YEAR), C.usd(idea_med)),
            ['idea-l', 'idea-med', 'idea-below'],
            {'a': U(idea_l), 'b': U(idea_med), 'y': Y},
            notes=[step('DESE names the inputs as enrolment in public and private schools and '
                        'children in poverty. Our divisor counts only pupils enrolled in the '
                        'district, so the two can differ.', 'hypothesis'),
                   step('Which input puts Lunenburg lower is not on these pages.', 'gap',
                        closes="DESE's IDEA allocation calculation for Lunenburg: its base amount, "
                               'enrolment and poverty counts')]),
        con('Lunenburg has been below that median on IDEA in every comparable year since %s.'
            % C.fy(FIRST), ['idea-l', 'idea-med'], {'y': F(FIRST)},
            notes=[step('%s is not compared: DESE’s page for it returns an error.' % C.fy(2018),
                        'gap', {'y': F(2018)},
                        closes="DESE's IDEA allocation page for that year, by fund code")]),
        con('Title I follows the low-income share closely; IDEA barely follows the disability share.',
            ['r-ti', 'r-idea', 'ti-l', 'ti-mk', 'li-l', 'li-mk'],
            notes=[step('So a lower Title I is the formula’s answer to fewer low-income pupils, '
                        'not money left unclaimed.', 'hypothesis'),
                   step('The low-income share is DESE’s count of enrolled pupils; Title I is set '
                        'from Census poverty counts, which this page does not hold.', 'gap',
                        closes="The Census poverty estimates DESE used for each district's Title I")]),
        con('Across all five, Lunenburg got %s a pupil against a median of %s.'
            % (C.usd(five_l), C.usd(five_med)), ['five-l', 'five-med'],
            {'a': U(five_l), 'b': U(five_med)}),
    ]

    x = [nm for _, nm in FIVE]
    tracks = [TP.track(LUN, [lp[fc] for fc, _ in FIVE])]
    for s, label in SETS:
        cs = in_set(s)
        tracks.append(TP.track('%s, median' % label,
                               [median([per_pupil(D, c, fc, YEAR) for c in cs]) for fc, _ in FIVE]))
    chart1 = TP.series(
        'Allocations per pupil by grant', x, tracks, '$', kind='bar',
        note='%s. Each allocation divided by DESE’s October headcount; each set’s median. '
             'Fitchburg cannot be matched and is left out.' % C.fy(YEAR),
        note_figures={'y': Y})
    also1 = [TP.series(
        'IDEA per pupil over time', [C.fy(y) for y in years], [
            TP.track(LUN, [per_pupil(D, lun, IDEA, y) for y in years]),
            TP.track('Comparison districts, median',
                     [median([per_pupil(D, c, IDEA, y) for c in comp]) if y in idea_years else None
                      for y in years]),
            TP.track('Alike in make-up, median',
                     [median([per_pupil(D, c, IDEA, y) for c in mk]) if y in idea_years else None
                      for y in years])],
        '$', note='%s is a gap: DESE’s page for it returns an error.' % C.fy(2018),
        note_figures={'y': F(2018)})]

    def setnames(c):
        return ', '.join(SET_SHORT[s] for s, _ in SETS if s in members[c]['sets'])
    cols = ['Set', 'Pupils', 'Low-income'] + [nm for _, nm in FIVE] + ['All five']
    order = [lun] + sorted(comp, key=lambda c: -five_total(c, YEAR))
    view_year = dict(
        key='fy%d' % YEAR, label='%s, per pupil' % C.fy(YEAR), total_col=None,
        kinds=['published'] * len(cols), columns=cols,
        rows=[dict(label=LUN if c == lun else members[c]['name'],
                   cells=['Lunenburg' if c == lun else setnames(c),
                          C.num(prof[c][YEAR]['n']), C.pct(prof[c][YEAR]['li'])]
                   + [usd0(per_pupil(D, c, fc, YEAR)) for fc, _ in FIVE]
                   + [usd0(five_total(c, YEAR))])
              for c in order],
        note='Allocation divided by DESE’s October headcount, %s, highest first after Lunenburg. '
             'Pupils and low-income share are DESE’s district profile. Fitchburg is left out: '
             'DESE lists two districts by that name and its pages cannot tell them apart.' % C.fy(YEAR))
    lun_codes = sorted({k[1] for k in alloc if k[0] == lun}, key=lambda fc: (fc not in dict(FIVE), fc))
    other = [fc for fc in lun_codes if fc not in dict(FIVE)]
    lcols = [nm for _, nm in FIVE] + ['One-time and other']
    view_lun = dict(
        key='lunenburg', label='Lunenburg by year, dollars', total_col=None,
        kinds=['published'] * len(lcols), columns=lcols,
        rows=[dict(label=C.fy(y),
                   cells=[usd0(alloc.get((lun, fc, y))) for fc, _ in FIVE]
                   + ['; '.join('%s %s' % (SHORT[fc], C.usd(alloc[(lun, fc, y)]))
                                for fc in other if (lun, fc, y) in alloc)])
              for y in range(FIRST, LAST + 1)],
        note='DESE’s allocation to Lunenburg, as printed. A blank is a year DESE’s page does not '
             'list Lunenburg for that grant. One-time grants are the pandemic relief funds.')
    table1 = dict(caption='Allocations, district by district', views=[view_year, view_lun])

    src_alloc = dict(label='Massachusetts DESE — Grant allocations and awards, by fund code, '
                           '%s to %s' % (C.fy(FIRST), C.fy(LAST)),
                     href='https://www.doe.mass.edu/grants/entitlement-allocation.aspx')
    src_ours = dict(label='Lunenburg Budget Project — %s (every figure on these pages: '
                          'allocation, headcount, per pupil, by district and year)' % CSV_NAME,
                    href='/docs/data/%s' % CSV_NAME)
    src_prof = dict(label='Massachusetts DESE — district profiles: headcount, low-income, '
                          'English-learner and disability shares (er3w-dyti)',
                    href='/docs/state-dese/er3w-dyti.json')
    src_cmp = dict(label='Lunenburg Budget Project — Towns like us (where the comparison '
                         'sets are defined)', href='/analysis/towns-like-us')
    sources1 = [src_alloc,
                dict(label='Massachusetts DESE — IDEA allocation page, %s (our copy)' % C.fy(YEAR),
                     href='/docs/%s/code-0240-fy%d.html' % (snapshot(), YEAR)),
                dict(label='Massachusetts DESE — %s (eligibility, quoted)' % q240['program'],
                     href=q240['detail_url']),
                src_prof, src_ours, src_cmp]
    page1 = TP.page(
        T_PP,
        'Lunenburg gets less IDEA per pupil than most comparable districts; Title I tracks its '
        'low-income share.',
        facts1, conc1, chart=chart1, also=also1, table=table1, sources=sources1)

    # ------------------------------------------------------------ page two: what others get
    opps = opportunities()
    lun_has = {k[1] for k in alloc if k[0] == lun}
    all_years = range(FIRST, LAST + 1)
    lacks = []
    for fc in sorted({k[1] for k in alloc}):
        if fc in lun_has:
            continue
        got = [c for c in comp if any(alloc.get((c, fc, y), 0) > 0 for y in all_years)]
        if got:
            now = [c for c in comp if alloc.get((c, fc, YEAR), 0) > 0]
            lacks.append(dict(fc=fc, got=got, now=now))
    lacks.sort(key=lambda r: -len(r['got']))
    by = {r['fc']: r for r in lacks}
    if TITLE_III not in by or lacks[0]['fc'] != TITLE_III:
        fail('Title III is no longer the grant most comparison districts get and Lunenburg does not')
    # Lunenburg is on NO Title III page, any year -- checked against the names too, in case a
    # row lost its code
    for r in rows(ALLOC):
        if r['fund_code'] == TITLE_III and 'lunenburg' in r['district'].lower():
            fail('a Title III row names Lunenburg: %r' % r['district'])
    t3 = by[TITLE_III]
    t3_now = len(t3['now'])
    el_l = prof[lun][YEAR]['el']
    el_0 = prof[lun][FIRST]['el']
    n_l = prof[lun][YEAR]['n']
    learners = n_l * el_l / 100
    rates = []
    for c in prof:
        a = alloc.get((c, TITLE_III, YEAR))
        p = prof[c].get(YEAR, {})
        if a and p.get('n') and p.get('el'):
            rates.append(a / (p['n'] * p['el'] / 100))
    rate = st.median(rates)
    est = learners * rate
    floor = 10000
    q3 = opps[TITLE_III]
    if '$10,000' not in q3['eligibility'] or q3['grant_type'] != 'Entitlement':
        fail("DESE's Title III eligibility text no longer states the $10,000 floor")
    if est >= floor:
        fail('the Title III estimate passed the floor; the page says it falls short')

    nY = figure(t3_now, '%s of %s' % (C.num(t3_now), C.num(N)), 'districts')
    facts2 = [
        f('t3-now', nY, 'comparison districts allocated Title III, %s' % C.fy(YEAR), 'published',
          {'y': Y}),
        f('t3-ever', figure(len(t3['got']), C.num(len(t3['got'])), 'districts'),
          'allocated it in some year, %s to %s' % (C.fy(FIRST), C.fy(LAST)), 'published',
          {'a': F(FIRST), 'b': F(LAST)}),
        f('t3-l', figure(0, 'Not listed', 'allocations'), 'Lunenburg, on every Title III page held',
          'published'),
        f('el-l', figure(el_l, C.pct(el_l), '%'), 'Lunenburg pupils learning English, %s' % C.fy(YEAR),
          'published', {'y': Y}),
        f('el-0', figure(el_0, C.pct(el_0), '%'), 'the same share in %s' % C.fy(FIRST), 'published',
          {'y': F(FIRST)}),
        f('floor', figure(floor, C.usd(floor)), 'the least DESE will allocate a district, by statute',
          'statute'),
        f('rate', U(rate), 'Title III per learner, median district, our estimate', 'estimate'),
        f('est', U(est), 'Lunenburg at that rate, our estimate', 'estimate'),
    ]
    for fc in [r['fc'] for r in lacks if r['fc'] != TITLE_III]:
        r = by[fc]
        facts2.append(f('c%s' % fc, figure(len(r['got']), C.num(len(r['got'])), 'districts'),
                        '%s: comparison districts in some year' % SHORT[fc], 'published'))
    typed = [r['fc'] for r in lacks if r['fc'] in opps]
    untyped = [r['fc'] for r in lacks if r['fc'] not in opps]
    if any(opps[fc]['grant_type'] != 'Entitlement' for fc in typed):
        fail('a grant Lunenburg lacks is no longer listed as an entitlement')
    conc2 = [
        con('Title III, for English learners, went to %s comparison districts in %s; '
            'Lunenburg is on no list.' % (nY['text'], C.fy(YEAR)),
            ['t3-now', 't3-ever', 't3-l'], {'n': nY, 'y': Y}),
        con('DESE allocates it only where it reaches %s; at the median rate Lunenburg would get '
            'about %s.' % (C.usd(floor), C.usd(est)), ['floor', 'rate', 'est', 'el-l', 'el-0'],
            {'f': figure(floor, C.usd(floor)), 'e': U(est)},
            notes=[step('Our learner count is the October headcount times DESE’s share; DESE '
                        'counts learners in March. Both figures are ours.', 'hypothesis'),
                   step('Whether Lunenburg draws Title III through a consortium is not on these '
                        'pages: they do not list a consortium’s members.', 'gap',
                        closes="DESE's Title III consortium membership, or the district's "
                               'Title III application')]),
        con('DESE lists %s as %s: by formula, not competed for.'
            % (' and '.join(SHORT[fc] for fc in typed),
               'an entitlement' if len(typed) == 1 else 'entitlements'), ['t3-now'] +
            ['c%s' % fc for fc in typed if fc != TITLE_III],
            notes=[step('DESE requires Perkins districts to offer career technical programmes; '
                        'that may be why Lunenburg is not listed. Nothing here tests it.',
                        'hypothesis')]
            if '0400' in typed else ()),
        con('Competitive grants are not on these pages, so what the district applied for and won '
            'is not compared.', ['t3-l'],
            notes=[step('The open-grants list shows what is open now, not who won.', 'gap',
                        closes="The district's grants list by year, with each competitive "
                               'award notice')]),
    ]
    if untyped:
        conc2[2]['notes'] = list(conc2[2].get('notes', [])) + [
            step('%s %s not on that list, so %s type is not stated here.'
                 % (' and '.join(SHORT[fc] for fc in untyped), 'is' if len(untyped) == 1 else 'are',
                    'its' if len(untyped) == 1 else 'their'), 'gap',
                 closes="DESE's grant pages for %s" % ', '.join('fund code %s' % fc for fc in untyped),
                 allow=tuple(untyped))]
    chart2 = TP.ranking(
        'Grants Lunenburg is not allocated',
        [(SHORT[r['fc']], len(r['got'])) for r in lacks], 'districts', basis='published',
        note='How many of the %s comparison districts DESE allocated each in some year, %s to %s.'
             % (C.num(N), C.fy(FIRST), C.fy(LAST)),
        note_figures={'n': nfig, 'a': F(FIRST), 'b': F(LAST)})
    gcols = ['Districts, any year', 'Districts, %s' % C.fy(YEAR), 'DESE’s type', 'Who']
    view_g = dict(
        key='lacks', label='Grants Lunenburg is not allocated', total_col=None,
        kinds=['published'] * len(gcols), columns=gcols,
        rows=[dict(label='%s (fund code %s)' % (SHORT[r['fc']], r['fc']),
                   cells=[C.num(len(r['got'])), C.num(len(r['now'])),
                          opps[r['fc']]['grant_type'] if r['fc'] in opps else 'not on the open list',
                          ', '.join(members[c]['name'] for c in r['got'])])
              for r in lacks],
        note='Of %s comparison districts, %s to %s. Not listed means DESE’s page for that grant '
             'and year does not name Lunenburg.' % (C.num(N), C.fy(FIRST), C.fy(LAST)))
    t3cols = ['Set', 'Pupils', 'Learning English', 'Title III', 'Per learner']
    t3rows = []
    for c in [lun] + sorted(comp, key=lambda c: -(prof[c][YEAR]['el'])):
        p = prof[c][YEAR]
        a = alloc.get((c, TITLE_III, YEAR))
        t3rows.append(dict(label=LUN if c == lun else members[c]['name'],
                           cells=['Lunenburg' if c == lun else setnames(c), C.num(p['n']),
                                  C.pct(p['el']), usd0(a) or 'not listed',
                                  usd0(a / (p['n'] * p['el'] / 100)) if a and p['el'] else '']))
    view_t3 = dict(
        key='title-iii', label='Title III, %s' % C.fy(YEAR), total_col=None,
        kinds=['published', 'published', 'published', 'published', 'estimate'], columns=t3cols,
        rows=t3rows,
        note='Ordered by the share learning English. Per learner divides by the October headcount '
             'times that share, our estimate of the count.')
    table2 = dict(caption='What comparison districts get that Lunenburg does not',
                  views=[view_g, view_t3])
    sources2 = [src_alloc,
                dict(label='Massachusetts DESE — Title III allocation page, %s (our copy)' % C.fy(YEAR),
                     href='/docs/%s/code-0180-fy%d.html' % (snapshot(), YEAR)),
                dict(label='Massachusetts DESE — %s (eligibility, quoted)' % q3['program'],
                     href=q3['detail_url'])]
    if '0400' in opps:
        sources2.append(dict(label='Massachusetts DESE — %s (eligibility)' % opps['0400']['program'],
                             href=opps['0400']['detail_url']))
    sources2 += [dict(label="Lunenburg Budget Project — dese-grant-opportunities.csv (DESE's "
                            'open-grants list, each grant’s type and eligibility)',
                      href='/docs/data/dese-grant-opportunities.csv'),
                 src_prof, src_ours, src_cmp]
    page2 = TP.page(
        T_GAP,
        'Most comparison districts get Title III for English learners; we estimate Lunenburg is '
        'just under its floor.',
        facts2, conc2, chart=chart2, table=table2, sources=sources2)

    # ------------------------------------------------------------ the figures, as a CSV
    out = []
    every = [lun] + comp
    for c in every:
        for y in range(FIRST, LAST + 1):
            p = prof.get(c, {}).get(y, {})
            for fc in sorted({k[1] for k in alloc if k[0] == c and k[2] == y}):
                a = alloc[(c, fc, y)]
                pp = per_pupil(D, c, fc, y)
                out.append(dict(
                    fy=y, district=LUN if c == lun else members[c]['name'], district_code=c,
                    sets='lunenburg' if c == lun else ' '.join(members[c]['sets']),
                    fund_code=fc, grant=SHORT.get(fc, fc), amount=a,
                    headcount=('%d' % p['n']) if p.get('n') else '',
                    low_income_pct=p.get('li', ''), english_learner_pct=p.get('el', ''),
                    disability_pct=p.get('swd', ''),
                    per_pupil=('%.2f' % pp) if pp is not None else '',
                    comparable='yes' if (fc, y) in D['comparable'] else
                    'no: DESE’s page by fund code for this year was not served'))
    return {T_PP: page1, T_GAP: page2}, out, dict(
        idea_l=idea_l, idea_med=idea_med, idea_below=idea_below, n=N, ti_l=ti_l, ti_mk=ti_mk,
        five_l=five_l, five_med=five_med, t3_now=t3_now, t3_ever=len(t3['got']), est=est,
        rate=rate, el_l=el_l, r_ti=r_ti, r_idea=r_idea)


FIELDS = ['fy', 'district', 'district_code', 'sets', 'fund_code', 'grant', 'amount', 'headcount',
          'low_income_pct', 'english_learner_pct', 'disability_pct', 'per_pupil', 'comparable']


def outputs():
    pages, table, _ = build()
    texts = {OUT % k: json.dumps(v, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
             for k, v in pages.items()}
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, FIELDS, lineterminator='\n')
    w.writeheader()
    w.writerows(table)
    texts[CSV_OUT] = buf.getvalue()
    return texts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    for tid in (T_PP, T_GAP):
        if REG.TOPICS.get(tid, (None, None, None))[2] != ME:
            fail('%s is not registered to %s in scripts/topic_registry/' % (tid, ME))
    texts = outputs()
    if a.check:
        stale = [p for p, t in texts.items()
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != t]
        for p in stale:
            print('STALE %s' % os.path.relpath(p, ROOT), file=sys.stderr)
        if stale:
            return 1
        print('grant comparison topics: current')
        return 0
    for p, t in texts.items():
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(t)
        os.replace(tmp, p)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
