#!/usr/bin/env python3
"""Lunenburg's federal grant allocations against the districts it is compared with.

    python3 scripts/build_grant_comparison_topics.py           # write the two topic payloads
    python3 scripts/build_grant_comparison_topics.py --check   # fail if either would change

TJ, 22 October 2026 (notes/MASTER-PLAN.md item 10): *"create a report comparing our GRANT
setup to other districts to see what gaps we have or where we are better."*

TWO PAGES on the school-all-funds shelf, registered there through TOPIC_GENERATORS:

    grant-allocations-compared   the five grants every comparison district holds, per pupil
    grants-others-receive        which grants comparison districts get and Lunenburg does not:
                                 a presence matrix, competitive awards and formula grants apart

THE DATA
  sources/data/dese-entitlement-allocations.csv   DESE's allocation pages, every district,
                                                  FY2017-FY2027 (extract_dese_entitlements.py)
  sources/data/dese-competitive-awards.csv        DESE's competitive award documents, FY2026-
                                                  FY2027, one row per recipient, matched to a
                                                  district by name (extract_dese_awards.py)
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
money-gaps.csv with the one document that would settle it.

FORMULA AND COMPETITIVE ARE NEVER MIXED (TJ, 23 October 2026: "almost a PUSH to the school
committee to look into other grants"). The push is only honest for grants a district applies
for. So the second page keeps two groups by DESE's OWN label: every code on the "Entitlement And
Allocation Grants" pages is formula money, and every document under "Competitive Awards" is a
competitive award. A competitive award list shows who WON; nothing DESE publishes says who
applied and lost, and the page says so rather than reading absence as not trying. DESE posts
award lists for FY2026 and the current year only; earlier ones redirect to its 404 page.
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
MT_NAME = 'Montachusett Regional Vocational Technical'   # DESE's label on the allocation pages
MT_LABEL = 'Monty Tech'
MT_SET = 'Lunenburg’s vocational district, not counted'
FWIN = (2023, 2027)            # the formula window the presence matrix reads, "any year"
EBP, MYCAP = '0117', '0424'    # the two competitive awards Lunenburg won (refused if that moves)
AWARDS = os.path.join(ROOT, 'sources', 'data', 'dese-competitive-awards.csv')
# What a reader calls each competitive grant a comparison district or Lunenburg won. NAMES
# ONLY, shortened from DESE's own program title on the award document; a code that appears
# without one here refuses the build rather than printing a 70-character title in a row.
AWARD_SHORT = {
    '0117': 'Evidence-based practice', '0122': 'Rethinking discipline',
    '0181': 'English learner education support', '0199': 'Interpreters in schools',
    '0213': 'Time-out regulations support', '0215': 'Genocide education',
    '0335': 'Safe and supportive schools', '0413': 'Work-based learning planning',
    '0419': 'Career pathways, implementation', '0424': 'Middle school exploration (MyCAP)',
    '0426': 'Career technical frameworks', '0436': 'Career pathways, planning',
    '0589': 'Civics teaching and learning', '0593': 'Reading success (PRISM II)',
    '0594': 'Reading success (PRISM III)', '0598': 'MyCAP planning and implementation',
    '0612': 'Early childhood partnerships', '0710': 'Farm to school (MA FRESH)',
    '0718': 'Arts and cultural vitality', '0794': 'Hate crimes prevention',
    '221P': 'Teacher apprenticeship planning',
}
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
    W, docs = awards(code)
    mts = [c for c, n in names.items() if n == MT_NAME]
    if len(mts) != 1:
        fail('%r is not one district on the allocation pages: %s' % (MT_NAME, mts))
    mt = mts[0]
    if mt in members:
        fail('Monty Tech is in a comparison set; the pages keep it beside Lunenburg, uncounted')
    if not prof.get(mt, {}).get(YEAR, {}).get('n'):
        fail('Monty Tech has no FY%d headcount' % YEAR)
    return dict(alloc=alloc, prof=prof, code=code, lun=lun, members=members, named=named,
                excluded=excluded, comparable=comparable, names=names, awards=W, award_docs=docs,
                mt=mt, mt_towns=mt_towns())


def awards(code_of):
    """The competitive award rows attributed to a district (extract_dese_awards.py), and one
    row per award document with its printed proposal counts and our copy's address."""
    got, docs = [], {}
    for r in rows(AWARDS):
        fc = r['fund_code'].upper()
        docs[(int(r['fy']), fc)] = dict(fy=int(r['fy']), fund=fc, copy=r['our_copy'],
                                        received=int(r['proposals_received'] or 0),
                                        recommended=int(r['proposals_recommended'] or 0))
        if r['district_code']:
            got.append(dict(fy=int(r['fy']), fund=fc, code=r['district_code'],
                            amount=float(r['amount']), joint=int(r['joint']),
                            copy=r['our_copy']))
    if not got:
        fail('no competitive award is attributed to any district -- run extract_dese_awards.py')
    for w in got:
        d = docs[(w['fy'], w['fund'])]
        w['received'], w['recommended'] = d['received'], d['recommended']
    return got, sorted(docs.values(), key=lambda d: (d['fy'], d['fund']))


def mt_towns():
    """Monty Tech's member towns, off the one parser build_monty_tech.py uses (DESE's
    apportionment sheet as the district reprints it). Lunenburg must be one of them."""
    import build_monty_tech as MTB
    t = MTB.member_towns()
    if LUN not in {x['town'] for x in t['towns']}:
        fail('Lunenburg is not a Monty Tech member town on the apportionment sheet')
    return t


def first_set(m):
    return next(s for s, _ in SETS if s in m['sets'])


def column_order(members):
    """Bordering districts first, then the peers, then each cohort, alphabetical within."""
    order = [s for s, _ in SETS]
    return sorted(members, key=lambda c: (order.index(first_set(members[c])), members[c]['name']))


def short_district(name):
    return name.replace(' School District', '')


def snapshot():
    """The archive key of the newest snapshot of DESE's allocation pages -- the one the
    extractor reads -- so a citation follows the data rather than a typed date."""
    base = os.path.join(ROOT, 'sources', 'state-dese', 'entitlements')
    newest = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))[-1]
    return 'state-dese/entitlements/' + newest


def opportunities():
    """DESE's open-grants list, by single fund code: (type, eligibility, detail url). A row
    may carry several codes -- `0419/0436`, `0285-0563`, `0005 0006 7061 9611` -- and each is
    a key; codes are upper-cased, as the award documents print some of them lower."""
    import re
    out = {}
    for r in rows(OPPS):
        for fc in re.split(r'[\s/\-]+', r['fund_code'].strip()):
            if fc:
                out[fc.upper()] = r
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
    mt = D['mt']
    order = [lun, mt] + sorted(comp, key=lambda c: -five_total(c, YEAR))
    view_year = dict(
        key='fy%d' % YEAR, label='%s, per pupil' % C.fy(YEAR), total_col=None,
        kinds=['published'] * len(cols), columns=cols,
        rows=[dict(label=LUN if c == lun else MT_LABEL if c == mt else members[c]['name'],
                   cells=['Lunenburg' if c == lun else MT_SET if c == mt else setnames(c),
                          C.num(prof[c][YEAR]['n']), C.pct(prof[c][YEAR]['li'])]
                   + [usd0(per_pupil(D, c, fc, YEAR)) for fc, _ in FIVE]
                   + [usd0(five_total(c, YEAR))])
              for c in order],
        note='Allocation divided by DESE’s October headcount, %s, highest first after Lunenburg. '
             'Pupils and low-income share are DESE’s district profile. Fitchburg is left out: '
             'DESE lists two districts by that name and its pages cannot tell them apart. Monty Tech, '
             'Lunenburg’s vocational district, is shown and is in no median.' % C.fy(YEAR))
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
    # TWO KINDS OF GRANT, KEPT APART, each by DESE's own label (rule 3, rule 8):
    #   FORMULA     every code on DESE's "State and Federal Entitlement And Allocation Grants"
    #               pages. A district does not compete for these; not getting one is the
    #               formula's answer to its counts, and what decides it is quoted where held.
    #   COMPETITIVE every award document DESE lists under "Competitive Awards". These are the
    #               grants a district applies for, and the only ones a "push" can be about.
    opps = opportunities()
    W = D['awards']
    lun_has = {k[1] for k in alloc if k[0] == lun}
    # MONTY TECH IS COLUMN 1, drawn beside Lunenburg and counted nowhere: it is the regional
    # vocational district Lunenburg belongs to, not a comparison district, and its grants
    # serve students from every member town. Columns 2 on are the comparison districts.
    mt, mt_towns = D['mt'], D['mt_towns']
    cols = [lun, mt] + column_order(members)
    col_label = [LUN, MT_LABEL] + [short_district(members[c]['name']) for c in cols[2:]]
    SPAN = {'border': 'Bordering', 'peer': 'Peers', 'makeup': 'Make-up', 'behaviour': 'Behaviour'}
    spans = [(LUN, 1), (MT_LABEL, 1)] + [(SPAN[s], sum(1 for c in cols[2:] if first_set(members[c]) == s))
                                         for s, _ in SETS]
    spans = [s for s in spans if s[1]]

    # ---- formula: any year in the window
    fw = range(FWIN[0], FWIN[1] + 1)
    def f_cell(c, fc):
        ys = [y for y in fw if alloc.get((c, fc, y), 0) > 0]
        if not ys:
            return None
        return '%s in %s; %s of %s years' % (C.usd(alloc[(c, fc, ys[-1])]), C.fy(ys[-1]),
                                             C.num(len(ys)), C.num(len(fw)))
    f_codes = sorted({k[1] for k in alloc if k[2] in fw and k[0] in set(comp) | {lun}
                      and alloc[k] > 0})
    f_rows = [(fc, [f_cell(c, fc) for c in cols]) for fc in f_codes]
    f_rows = [(fc, cs) for fc, cs in f_rows if any(cs)]
    f_rows.sort(key=lambda r: (-sum(1 for v in r[1][2:] if v), SHORT[r[0]]))
    f_lacks = [fc for fc, cs in f_rows if cs[0] is None]
    f_lacks_n = {fc: sum(1 for v in cs[2:] if v) for fc, cs in f_rows}
    if TITLE_III not in f_lacks or max(f_lacks, key=lambda fc: f_lacks_n[fc]) != TITLE_III:
        fail('Title III is no longer the formula grant most comparison districts get and Lunenburg does not')
    for r in rows(ALLOC):
        if r['fund_code'] == TITLE_III and 'lunenburg' in r['district'].lower():
            fail('a Title III row names Lunenburg: %r' % r['district'])

    # ---- competitive: every award document held
    a_years = sorted({w['fy'] for w in W})
    def c_cell(c, fc):
        hits = [w for w in W if w['code'] == c and w['fund'] == fc]
        if not hits:
            return None
        return '; '.join('%s%s, %s' % (C.usd(w['amount']), ' joint' if w['joint'] > 1 else '',
                                       C.fy(w['fy'])) for w in sorted(hits, key=lambda w: w['fy']))
    c_codes = sorted({w['fund'] for w in W if w['code'] in set(comp) | {lun}})
    for fc in c_codes:
        if fc not in AWARD_SHORT:
            fail('competitive fund code %s has no short name in AWARD_SHORT' % fc)
    c_rows = [(fc, [c_cell(c, fc) for c in cols]) for fc in c_codes]
    c_rows.sort(key=lambda r: (-sum(1 for v in r[1][2:] if v), AWARD_SHORT[r[0]]))
    c_n = {fc: sum(1 for v in cs[2:] if v) for fc, cs in c_rows}
    mt_awards = [w for w in W if w['code'] == mt]
    c_gap = [fc for fc, cs in c_rows if cs[0] is None and c_n[fc]]
    c_lun = [fc for fc, cs in c_rows if cs[0] is not None]
    winners = sorted({w['code'] for w in W if w['code'] in members})
    per = {c: len({w['fund'] for w in W if w['code'] == c}) for c in comp}
    top = max(per.values())
    top_c = [c for c in comp if per[c] == top]
    if len(top_c) != 1:
        fail('two comparison districts tie for the most competitive grants: %s' % top_c)
    top_c = top_c[0]
    second = sorted(per.values())[-2]
    # the open list: DESE's current-grants list names its own Grant Type for each code
    def opp(fc):
        return opps.get(fc.upper())
    c_open = [fc for fc in c_gap if opp(fc) and opp(fc)['grant_type'] == 'Competitive'
              and opp(fc)['district_reading'] == 'districts eligible']
    c_still = [fc for fc in c_open if opp(fc)['open_on_list_date'] == 'yes']
    c_closed_type = [fc for fc in c_gap if opp(fc) and opp(fc)['grant_type'] in ('Continuation', 'Targeted')]
    ebp = [w for w in W if w['code'] == lun and w['fund'] == EBP]
    if len(ebp) != 1 or c_n.get(EBP):
        fail('the evidence-based practice award to Lunenburg changed shape')
    ebp = ebp[0]
    myc = [w for w in W if w['code'] == lun and w['fund'] == MYCAP]
    if len(myc) != 1 or set(c_lun) != {EBP, MYCAP}:
        fail('Lunenburg won something other than the two awards the page names: %s' % c_lun)
    myc = myc[0]

    # ---- Title III's floor, our estimate (kept from the first version of this page)
    t3_ever = f_lacks_n[TITLE_III]
    el_l = prof[lun][YEAR]['el']
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
    perk = opps.get('0400')
    mt_perk = [y for y in fw if alloc.get((mt, '0400', y), 0) > 0]
    if (mt, '0400', YEAR) not in alloc:
        fail('Monty Tech has no Perkins allocation in FY%d' % YEAR)
    if mt_awards:
        fail('Monty Tech now appears on an award document; the page says it does not')
    if '0400' in f_lacks and (not perk or 'Career Technical Education programs' not in perk['eligibility']):
        fail("DESE's Perkins eligibility text no longer names career technical programmes")

    A0, A1 = F(a_years[0]), F(a_years[-1])
    FW0, FW1 = F(FWIN[0]), F(FWIN[1])
    ofN = lambda n: figure(n, '%s of %s' % (C.num(n), C.num(N)), 'districts')
    g_fig = figure(len(c_gap), C.num(len(c_gap)), 'grants')
    top_name = short_district(members[top_c]['name'])
    facts2 = [
        f('c-gap', g_fig, 'competitive grants others won that Lunenburg did not', 'published'),
        f('c-who', ofN(len(winners)), 'comparison districts that won at least one', 'published'),
        f('c-top', figure(top, C.num(top), 'grants'), 'won by %s, the most of any' % top_name,
          'published'),
        f('c-lun', figure(len(c_lun), C.num(len(c_lun)), 'grants'),
          'competitive grants Lunenburg won', 'published'),
        f('c-open', figure(len(c_open), C.num(len(c_open)), 'grants'),
          'of those, offered for %s and open to districts' % C.fy(LAST),
          'published', {'y': F(LAST)}),
        f('c-still', figure(len(c_still), C.num(len(c_still)), 'grants'),
          'of those, still open on DESE’s current list', 'published'),
        f('ebp', U(ebp['amount']), 'Lunenburg, evidence-based practice grant, %s' % C.fy(ebp['fy']),
          'published', {'y': F(ebp['fy'])}),
        f('ebp-n', figure(ebp['recommended'], '%s of %s' % (C.num(ebp['recommended']),
                                                           C.num(ebp['received'])), 'proposals'),
          'proposals DESE funded for that grant', 'published'),
        f('t3-ever', ofN(t3_ever), 'comparison districts allocated Title III, %s–%s'
          % (C.fy(FWIN[0]), C.fy(FWIN[1])), 'published', {'a': FW0, 'b': FW1}),
        f('t3-l', figure(0, 'Not listed', 'allocations'), 'Lunenburg, on every Title III page held',
          'published'),
        f('floor', figure(floor, C.usd(floor)), 'the least DESE will allocate a district, by statute',
          'statute'),
        f('est', U(est), 'Lunenburg at the median rate per learner, our estimate', 'estimate'),
    ]
    conc2 = [
        con('Comparison districts won %s competitive DESE grants Lunenburg did not, %s–%s.'
            % (C.num(len(c_gap)), C.fy(a_years[0]), C.fy(a_years[-1])),
            ['c-gap', 'c-who', 'c-top'], {'n': g_fig, 'a': A0, 'b': A1},
            notes=[step('%s, one of the districts alike in make-up, won %s; the next most was %s.'
                        % (top_name, C.num(top), C.num(second)), 'measured',
                        {'t': figure(top, C.num(top)), 's': figure(second, C.num(second))}),
                   step('Whether Lunenburg applied for them is not published: DESE lists only '
                        'who won.', 'gap',
                        closes="The district's list of the DESE grants it applied for in those "
                               'years'),
                   step('DESE no longer posts its award lists before %s.' % C.fy(a_years[0]),
                        'gap', {'a': A0},
                        closes="DESE's competitive award lists for the years before, "
                               'by records request')]),
        con('%s of them were offered again for %s, open to school districts; %s.'
            % (C.num(len(c_open)), C.fy(LAST),
               'none is still open' if not c_still else '%s still open' % C.num(len(c_still))),
            ['c-open', 'c-still', 'c-gap'],
            dict({'n': figure(len(c_open), C.num(len(c_open))), 'y': F(LAST)},
                 **({'s': figure(len(c_still), C.num(len(c_still)))} if c_still else {})),
            notes=[step('DESE lists %s more as continuation or targeted grants, for past '
                        'grantees or invited districts.' % C.num(len(c_closed_type)),
                        'measured', {'k': figure(len(c_closed_type), C.num(len(c_closed_type)))}),
                   step('Who may enter is our reading of DESE’s eligibility text, quoted beside '
                        'each grant on the open-grants page.', 'hypothesis',
                        cite=('/grants-open-to-lunenburg', 'Grants open to Lunenburg now'))]),
        con('Lunenburg won %s for evidence-based practice, a grant no comparison district won.'
            % C.usd(ebp['amount']), ['ebp', 'ebp-n', 'c-lun'], {'a': U(ebp['amount'])},
            notes=[step('It also won %s for middle school exploration (MyCAP) in %s, as did %s '
                        'comparison districts.' % (C.usd(myc['amount']), C.fy(myc['fy']),
                                                   C.num(c_n[MYCAP])), 'measured',
                        {'a': U(myc['amount']), 'y': F(myc['fy']),
                         'n': figure(c_n[MYCAP], C.num(c_n[MYCAP]))})]),
        con('Title III, formula money for English learners, reached %s comparison districts; '
            'never Lunenburg.' % ofN(t3_ever)['text'], ['t3-ever', 't3-l', 'floor', 'est'],
            {'n': ofN(t3_ever)},
            notes=[step('DESE allocates it only where it reaches %s; at the median rate per '
                        'learner Lunenburg would get about %s.' % (C.usd(floor), C.usd(est)),
                        'estimate', {'f': figure(floor, C.usd(floor)), 'e': U(est)}),
                   step('Whether Lunenburg draws it through a consortium is not on these pages.',
                        'gap', closes="DESE's Title III consortium membership, or the "
                                      "district's Title III application")]
            + ([step('Perkins, the other formula grant some get, requires career technical '
                     'programmes, DESE’s eligibility text says.', 'measured'),
                step('Monty Tech, Lunenburg’s vocational district, was allocated Perkins in %s of '
                     '%s years, %s in %s, for students from all %s member towns.'
                     % (C.num(len(mt_perk)), C.num(len(fw)), C.usd(alloc[(mt, '0400', YEAR)]),
                        C.fy(YEAR), C.num(mt_towns['count'])), 'measured',
                     {'k': figure(len(mt_perk), C.num(len(mt_perk))),
                      'n': figure(len(fw), C.num(len(fw))),
                      'a': U(alloc[(mt, '0400', YEAR)]), 'y': Y,
                      'm': figure(mt_towns['count'], C.num(mt_towns['count']))}),
                step('How much of it serves Lunenburg’s students is not published.', 'gap',
                     closes="Monty Tech's Perkins application and budget, by member town or "
                            'by programme')]
               if '0400' in f_lacks else [])),
    ]
    finding2 = ('Comparison districts won %s competitive grants Lunenburg did not in %s–%s; it '
                'won %s.' % (C.num(len(c_gap)), C.fy(a_years[0]), C.fy(a_years[-1]),
                             C.num(len(c_lun))))
    chart2 = TP.presence(
        'Who gets which grant',
        col_label,
        [('Competitive, %s–%s' % (C.fy(a_years[0]), C.fy(a_years[-1])),
          [(AWARD_SHORT[fc], cs) for fc, cs in c_rows]),
         ('Formula, any year %s–%s' % (C.fy(FWIN[0]), C.fy(FWIN[1])),
          [(SHORT[fc], cs) for fc, cs in f_rows])],
        'districts', spans=spans, related=[1],
        note='Grey: Monty Tech, Lunenburg’s vocational district, shared by %s member towns; '
             'in no count. Fitchburg cannot be matched.' % C.num(mt_towns['count']),
        note_figures={'m': figure(mt_towns['count'], C.num(mt_towns['count']))})

    # ---- tables
    def who(fc, cell):
        return '; '.join('%s %s' % (col_label[i], cs) for i, cs in enumerate(cell) if cs and i >= 2)
    gcols = ['Fiscal years', 'Comparison districts', 'Lunenburg', MT_LABEL, 'DESE’s %s list' % C.fy(LAST),
             'Proposals funded', 'Who, and how much']
    def listed(fc):
        o = opp(fc)
        if not o:
            return 'not listed'
        return '%s%s' % (o['grant_type'], ', due %s' % o['due'] if o.get('due') else '')
    def funded(fc):
        ds = {w['fy']: w for w in D['award_docs'] if w['fund'] == fc}
        return '; '.join('%s of %s, %s' % (d['recommended'], d['received'], C.fy(y))
                         for y, d in sorted(ds.items()) if d['received'])
    view_c = dict(
        key='competitive', label='Competitive grants', total_col=None,
        kinds=['published'] * len(gcols), columns=gcols,
        rows=[dict(label='%s · %s' % (AWARD_SHORT[fc], fc),
                   cells=[', '.join(C.fy(y) for y in sorted({w['fy'] for w in D['award_docs']
                                                              if w['fund'] == fc})),
                          C.num(c_n[fc]), cs[0] or 'not awarded', cs[1] or 'not awarded',
                          listed(fc), funded(fc),
                          who(fc, cs)])
              for fc, cs in c_rows],
        note='DESE’s competitive award lists, %s and %s; the number after each name is DESE’s fund code. A joint award names several districts '
             'and prints one amount. The list is DESE’s current-grants list, with its type. Monty Tech, '
             'Lunenburg’s vocational district, is on no award list held.'
             % (C.fy(a_years[0]), C.fy(a_years[-1])))
    table2 = dict(caption='Competitive grants comparison districts won', views=[view_c])
    fcols = ['Comparison districts', 'Lunenburg', MT_LABEL, 'DESE’s type', 'Who']
    view_f = dict(
        key='formula', label='Formula grants', total_col=None,
        kinds=['published'] * len(fcols), columns=fcols,
        rows=[dict(label='%s · %s' % (SHORT[fc], fc),
                   cells=[C.num(f_lacks_n[fc]), cs[0] or 'not listed', cs[1] or 'not listed',
                          opps[fc]['grant_type'] if fc in opps else 'on DESE’s entitlement pages',
                          ', '.join(col_label[i] for i, v in enumerate(cs) if v and i >= 2)])
              for fc, cs in f_rows],
        note='Any year %s to %s. Every code is on DESE’s entitlement and allocation pages; the type '
             'is DESE’s current-grants list where it names one. Monty Tech serves students from '
             'every member town and is in no count.' % (C.fy(FWIN[0]), C.fy(FWIN[1])))
    t3cols = ['Set', 'Pupils', 'Learning English', 'Title III', 'Per learner']
    t3rows = []
    for c in [lun, mt] + sorted(comp, key=lambda c: -(prof[c][YEAR]['el'])):
        p = prof[c][YEAR]
        a = alloc.get((c, TITLE_III, YEAR))
        t3rows.append(dict(label=LUN if c == lun else MT_LABEL if c == mt else members[c]['name'],
                           cells=['Lunenburg' if c == lun else MT_SET if c == mt else setnames(c), C.num(p['n']),
                                  C.pct(p['el']), usd0(a) or 'not listed',
                                  usd0(a / (p['n'] * p['el'] / 100)) if a and p['el'] else '']))
    view_t3 = dict(
        key='title-iii', label='Title III, %s' % C.fy(YEAR), total_col=None,
        kinds=['published', 'published', 'published', 'published', 'estimate'], columns=t3cols,
        rows=t3rows,
        note='Ordered by the share learning English. Per learner divides by the October headcount '
             'times that share, our estimate of the count.')
    dcols = ['Set', 'Competitive grants won', 'Won alone, dollars', 'Joint awards']
    def drow(c):
        ws = [w for w in W if w['code'] == c]
        alone = sum(w['amount'] for w in ws if w['joint'] == 1)
        return dict(label=LUN if c == lun else MT_LABEL if c == mt else members[c]['name'],
                    cells=['Lunenburg' if c == lun else MT_SET if c == mt else setnames(c),
                           C.num(len({w['fund'] for w in ws})), C.usd(alone) if alone else '',
                           C.num(sum(1 for w in ws if w['joint'] > 1)) if any(w['joint'] > 1 for w in ws) else ''])
    view_d = dict(
        key='by-district', label='By district', total_col=None, kinds=['published'] * len(dcols),
        columns=dcols,
        rows=[drow(c) for c in [lun, mt] + sorted(comp, key=lambda c: (-per[c], members[c]['name']))],
        note='Competitive grants counted once however many years. A joint award is not split: '
             'DESE prints one amount for the group.')
    tables2 = [dict(caption='Formula grants others get', views=[view_f]),
               dict(caption='Title III and the learners it follows', views=[view_t3]),
               dict(caption='Competitive grants won, district by district', views=[view_d])]
    sources2 = [dict(label='Massachusetts DESE — Competitive awards, %s and current, by fund code'
                           % C.fy(a_years[0]), href='https://www.doe.mass.edu/grants/awards.html'),
                dict(label='Lunenburg Budget Project — dese-competitive-awards.csv (every '
                           'recipient on every award document, with our district match)',
                     href='/docs/data/dese-competitive-awards.csv'),
                dict(label='Massachusetts DESE — Evidence-based practice award, %s (our copy)'
                           % C.fy(ebp['fy']), href=ebp['copy']),
                src_alloc,
                dict(label='Massachusetts DESE — %s (eligibility, quoted)' % q3['program'],
                     href=q3['detail_url'])]
    if perk:
        sources2.append(dict(label='Massachusetts DESE — %s (eligibility)' % perk['program'],
                             href=perk['detail_url']))
    sources2 += [dict(label="Lunenburg Budget Project — dese-grant-opportunities.csv (DESE's "
                            'current-grants list, each grant’s type and eligibility)',
                      href='/docs/data/dese-grant-opportunities.csv'),
                 src_prof, src_ours, src_cmp]
    page2 = TP.page(
        T_GAP, finding2, facts2, conc2, chart=chart2, table=table2, tables=tables2,
        sources=sources2,
        finding_figures={'n': g_fig, 'a': A0, 'b': A1, 'k': figure(len(c_lun), C.num(len(c_lun)))})
    stats2 = dict(c_gap=len(c_gap), c_who=len(winners), c_top=top, c_lun=len(c_lun),
                  c_open=len(c_open), t3_ever=t3_ever, est=est, rate=rate)

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
        stats2, idea_l=idea_l, idea_med=idea_med, idea_below=idea_below, n=N, ti_l=ti_l,
        ti_mk=ti_mk, five_l=five_l, five_med=five_med, r_ti=r_ti, r_idea=r_idea)


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
