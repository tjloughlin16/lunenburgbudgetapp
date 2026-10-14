#!/usr/bin/env python3
"""Enrolment, split into topic pages: thirteen pages and the Students and schools hub.

    python3 scripts/build_enrolment_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_enrolment_topics.py --check   # fail if any output would change

WHY THIS EXISTS. scripts/topics.py has the model: one question per page, under five minutes,
facts first, one to four conclusions resting on them. The enrolment shelf lists the twelve
pages this script owns, and two special education pages (students-with-an-iep,
out-of-district-placements) that build_special_education_topics.py writes and which are
listed here without being touched.

IT COMPUTES NOTHING NEW THAT IT CAN READ INSTEAD. Every figure comes from a payload already
in the repository, and the script refuses to write if two of them stop agreeing where they
are supposed to:

  fy28/public/data/enrollment.json        build_enrollment.py: DESE's 1 October headcount,
                                          FY1994-FY2026, by grade band, school and group.
  fy28/public/data/attrition.json         build_attrition.py: DESE's attrition RATE by grade.
                                          Every count of children on those pages is the rate
                                          times the enrolment -- IMPLIED, so kind `estimate`.
  fy28/public/data/sped-leaving.json      /where-students-go-instead: DESE's enrolment of
                                          town residents by district, FY2014-FY2026.
  fy28/public/data/if-students-leave.json the two DESE flow files, the FY2025 annual town
                                          report's enrolment table, and the scenario at its
                                          own defaults (ASSUMED rates -- kind `estimate`).
  fy28/public/data/monty-tech.json        DESE's Chapter 70 workbook, the district's budget
                                          books and the town's ledger line.
  fy28/public/data/sped-students.json     only for the third FY2026 enrolment count.
  fy28/public/data/peer-spending.json     only for DESE's all-funds spending a pupil at
                                          Monty Tech, set beside the operating budget on
                                          /enrolment/monty-tech-funding as NOT the same measure.

RULE 7. A count of children is a fact. Why any of them left, or arrived, is a hypothesis and
every page says so in a `hypothesis` note, or names the record that would settle it.
DOLLARS ARE NOT STUDENTS: nothing here divides a cost by a headcount. The scenario page's
appropriation per pupil, and the "appropriation carried with them" built on it, are left out
for exactly that reason.

RULE 13a. Where two published counts of the same children disagree -- three FY2026
enrolments, DESE's two counts of Monty Tech pupils, three low-income definitions -- they are
shown side by side as separate facts, each saying what it counts, and never averaged.
"""
import argparse
import csv
import json
import os
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
HUB = 'enrolment'

MINE = [t for t, (_, home, gen) in REG.TOPICS.items()
        if home == HUB and gen == 'build_enrolment_topics.py']


def fail(msg):
    raise SystemExit('build_enrolment_topics: ' + msg)


def load(name):
    return json.load(open(os.path.join(PUB, name), encoding='utf-8'))


def said(payload, key, kind='minutes'):
    """One quotation a payload already verified against our copy of the minutes."""
    s = next((x for x in payload['said'] if x['key'] == key), None)
    if s is None:
        fail('quotation %r is no longer in its payload' % key)
    if not s['cite'].startswith('/docs/'):
        fail('quotation %r does not cite our copy' % key)
    return dict(quote=s['quote'], board=s['board'], date=s['date'], href=s['cite'],
                label='%s %s, %s' % (s['board'], kind, s['date']))


def sources():
    """Every document a page here cites, by its publisher's filename. Each must be in the
    archive manifest, because rule 12 needs our copy to exist."""
    man = {r['key'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    out = {}
    for key, pub in (
            ('state-dese/dese-enrollment-by-grade.xlsx', 'Massachusetts DESE'),
            ('state-dese/dese-student-attrition.xlsx', 'Massachusetts DESE'),
            ('state-dese/dese-residents-sending.xlsx', 'Massachusetts DESE'),
            ('state-dese/dese-enrollment-receiving.xlsx', 'Massachusetts DESE'),
            ('state-dese/dese-sped-program-characteristics.xlsx', 'Massachusetts DESE'),
            ('state-dese/dese-ch70-key-factors.xlsx', 'Massachusetts DESE'),
            ('state-dese/dese-ch70-district-profile.xlsx', 'Massachusetts DESE'),
            ('budget-workbooks/ch70-fy27-summary.xlsx', 'Massachusetts DESE'),
            ('town-annual-reports/docs/4130-fy-2025-annual-town-report.pdf', 'Town of Lunenburg'),
            ('town-annual-reports/docs/4124-fy-2017-annual-town-report.pdf', 'Town of Lunenburg'),
            ('town-budget/docs/3583-fy27-monty-tech-budget-presentation-pdf.pdf',
             'Montachusett Regional Vocational Technical School District'),
            ('town-budget/docs/a103-fy24-monty-tech-budget-for-public-hearing-march-08-2023-pdf.pdf',
             'Montachusett Regional Vocational Technical School District'),
            ('town-budget/docs/3769-fy-2027-operating-budgets-balanced-tier-1-tier2.pdf',
             'Town of Lunenburg'),
            ('state-dese/district-expenditures-by-function.xlsx',
             'Massachusetts DESE, expenditures by function, all funds'),
            ('town-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.xlsx',
             'Town of Lunenburg, MUNIS (records request)'),
            ('meetings/text/select-board/2021-01-19-minutes-5244.txt',
             'Select Board minutes, 19 January 2021'),
    ):
        if key not in man and not os.path.exists(os.path.join(ROOT, 'fy28', 'public', 'docs', key)):
            fail('%s is neither in archive-manifest.csv nor published' % key)
        name = key.split('/')[-1]
        out[name] = dict(label='%s — %s' % (pub, name), href='/docs/' + key)
    return out


def p100(x):
    return 100.0 * x


def span(*maps):
    """Every year from the first any map holds to the last, so a year nobody printed is a
    gap in the chart and never a zero."""
    ys = sorted(set().union(*[set(m) for m in maps]))
    return list(range(ys[0], ys[-1] + 1))


# --------------------------------------------------------------------- the pages

def build():
    EN = load('enrollment.json')
    AT = load('attrition.json')
    OF = load('sped-leaving.json')
    LV = load('if-students-leave.json')
    MT = load('monty-tech.json')
    SS = load('sped-students.json')
    PS = load('peer-spending.json')
    src = sources()
    S = lambda *names: [src[n] for n in names]
    U = lambda v: figure(v, C.usd(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    SY = lambda v: figure(v, 'SY%d' % v, 'school year')
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    f, con = LD.fact, TP.conclusion
    out = {}

    # ------------------------------------------------ the cross-checks
    dist = {r['fy']: r for r in EN['district']}
    last_fy = EN['last_fy']
    d26 = dist[last_fy]
    if d26['k5'] + d26['g68'] + d26['g912'] + d26['sp'] != d26['total']:
        fail('enrollment.json: the FY2026 grade bands no longer sum to the total')
    ch = AT['churn']
    if ch['enrol_last'] != d26['total'] or ch['last_fy'] != last_fy:
        fail('attrition.json and enrollment.json disagree on the FY2026 enrolment')
    fl = LV['flows']
    fl1 = fl['both_ways']['last']
    if fl1['sy'] != last_fy or fl1['at_lunenburg'] + fl1['in_all'] != d26['total']:
        fail('residents at Lunenburg plus children arriving no longer equals DESE’s enrolment')
    ol = OF['last']
    if (ol['fy'], ol['in_lunenburg'], ol['elsewhere'], ol['School Choice Program'],
            ol['Charter School']) != (fl1['sy'], fl1['at_lunenburg'], fl1['out_all'],
                                      fl1['out_choice'], fl1['out_charter']):
        fail('sped-leaving.json and if-students-leave.json disagree on the latest year')
    rlast = OF['routes'][-1]
    hl = MT['headline']
    if not (rlast['monty_tech'] == hl['students'] == AT['destinations']['monty_tech']):
        fail('three payloads disagree on the number of residents at Monty Tech')
    if hl['school_choice'] != rlast['school_choice'] or LV['scenario']['baseline_out'] != rlast['school_choice']:
        fail('the payloads disagree on residents leaving under school choice')
    # The town's printed table: each school's "resident" column is DESE's own FY2026 total.
    tr = LV['enrollment']
    sch26 = {r['school']: r['total'] for r in EN['schools'] if r['fy'] == last_fy}
    town_res = sorted(r['resident'] for r in tr['schools'])
    if town_res != sorted(sch26.values()) or tr['district_resident'] != d26['total']:
        fail('the annual town report’s resident column no longer equals DESE’s FY2026 counts')
    sc = LV['scenario']
    if abs(sc['tuition_out'] + sc['aid_loss'] - sc['net_cost']) > 0.5:
        fail('the scenario’s year-one figure no longer equals tuition plus aid')
    if abs(sc['leavers'] * sc['defaults']['tuition'] - sc['tuition_out']) > 0.5:
        fail('the scenario’s tuition is no longer leavers times the base rate')
    if abs(sc['leavers'] * sc['aid_per_pupil'] - sc['aid_loss']) > 0.5:
        fail('the scenario’s aid loss is no longer leavers times the marginal aid')
    asm = {r['fy']: r for r in MT['assessment']}
    a26 = asm[2026]
    if a26['required'] + a26['transport'] + a26['capital'] != a26['total']:
        fail('monty-tech.json: the FY2026 assessment no longer foots')
    if MT['ledger']['expended'] != a26['total']:
        fail('the town ledger’s Monty Tech line no longer equals the district’s FY2026 bill')
    req = {r['fy']: r for r in MT['required']}
    r26 = req[2026]
    if round(r26['lps_rlc'] + r26['mt_rlc']) != round(r26['town_rlc']):
        fail('the two districts’ required contributions no longer sum to the town’s')
    if r26['mt_rlc'] != a26['required']:
        fail('DESE’s required contribution and the district’s book disagree for FY2026')

    # ------------------------------------------------ enrolment by year
    pk, tr0, pl = EN['peak'], EN['trough'], EN['plateau']
    fall = p100((pk['total'] - tr0['total']) / pk['total'])
    since = [dist[y]['total'] for y in dist if y >= tr0['fy']]
    if min(since) != pl['low'] or max(since) != pl['high']:
        fail('enrollment.json: the plateau no longer bounds every year since the trough')
    sp_enr = next((r for r in SS['counts'] if r['fy'] == last_fy), None)
    if sp_enr is None:
        fail('sped-students.json: the program file has no FY2026 enrolment')
    YL0 = F(last_fy)
    year_table = dict(caption='DESE enrolment by year, 1 October headcount', views=[dict(
        key='bands', label='District total and grade bands', total_col=0,
        kinds=['ledger'] * 4, columns=['All', 'Pre-K to 5', 'Grades 6–8', 'Grades 9–12'],
        rows=[dict(label=C.fy(r['fy']), cells=[C.num(r['total']), C.num(r['k5']),
                                               C.num(r['g68']), C.num(r['g912'])])
              for r in sorted(EN['district'], key=lambda r: -r['fy'])],
        note='DESE’s enrolment by grade file, Lunenburg district rows. The bands do not add to '
             'the total by the few students DESE counts beyond grade 12.')])
    # THE SIGNATURE of the page and of the hub: the headcount every year DESE prints it, so
    # the peak, the fall and the plateau the finding names are one picture.
    tot = {y: r['total'] for y, r in dist.items()}
    year_chart = TP.series('Children enrolled, every year', [C.fy(y) for y in span(tot)],
                           [TP.track('Enrolled, DESE headcount', [tot.get(y) for y in span(tot)],
                                     'published')], 'children', kind='bar',
                           note='DESE’s 1 October headcount. A gap is a year the file does not '
                                'print.', note_allow=('1 October',))
    out['enrolment-by-year'] = TP.page(
        'enrolment-by-year',
        '%s children in %s: %s fewer than the %s peak, and close to where the count has sat since %s.'
        % (C.num(d26['total']), C.fy(last_fy), C.num(pk['total'] - d26['total']), C.fy(pk['fy']),
           C.fy(tr0['fy'])),
        [f('now', N(d26['total'], 'children'), 'enrolled, 1 October, %s' % C.fy(last_fy),
           'published', {'y': F(last_fy)}, allow=('1 October',)),
         f('peak', N(pk['total'], 'children'), 'enrolled, %s, the peak' % C.fy(pk['fy']),
           'published', {'y': F(pk['fy'])}),
         f('trough', N(tr0['total'], 'children'), 'enrolled, %s, the low' % C.fy(tr0['fy']),
           'published', {'y': F(tr0['fy'])}),
         f('high', N(pl['high'], 'children'), 'the highest year since %s' % C.fy(tr0['fy']),
           'published', {'y': F(tr0['fy'])}),
         f('fall', P(fall), 'fall from %s to %s (our arithmetic)' % (C.fy(pk['fy']), C.fy(tr0['fy'])),
           'published', {'a': F(pk['fy']), 'b': F(tr0['fy'])}),
         f('town', N(tr['district_total'], 'children'),
           'in the %s annual town report’s table' % C.fy(tr['fy']), 'published',
           {'y': F(tr['fy'])}),
         f('town-choice', N(tr['district_choice_in'], 'children'),
           'of them listed as school choice students', 'published'),
         f('dese-in', N(fl1['in_all'], 'children'),
           'of DESE’s %s count, resident in another town' % C.fy(last_fy), 'published',
           {'y': F(last_fy)}),
         f('spfile', N(sp_enr['enrolled'], 'children'),
           'in and out of district, %s, DESE special education file' % C.fy(last_fy),
           'published', {'y': F(last_fy)})],
        [con('Enrolment fell %s from %s to %s, then stopped falling.'
             % (C.pct(fall), C.fy(pk['fy']), C.fy(tr0['fy'])), ['peak', 'trough', 'fall'],
             {'p': P(fall), 'a': F(pk['fy']), 'b': F(tr0['fy'])},
             notes=[step('Births, families moving, school choice and Monty Tech all move this '
                         'count. The file carries no reason, so nothing here says which did.',
                         'hypothesis')]),
         con('Every year since %s has been between %s and %s children.'
             % (C.fy(tr0['fy']), C.num(pl['low']), C.num(pl['high'])), ['trough', 'high', 'now'],
             {'y': F(tr0['fy']), 'a': N(pl['low']), 'b': N(pl['high'])}),
         con('Three published counts of the same year’s children read %s, %s and %s.'
             % (C.num(d26['total']), C.num(sp_enr['enrolled']), C.num(tr['district_total'])),
             ['now', 'spfile', 'town', 'town-choice'],
             {'a': N(d26['total']), 'b': N(sp_enr['enrolled']), 'c': N(tr['district_total'])},
             notes=[step('DESE’s special education file heads its count “Total In- and '
                         'Out-of-District Students”; nothing published reconciles it to the '
                         'headcount.',
                         'gap', closes='DESE’s definition of the enrolment column in its '
                                       'special education program file, for the same year')]),
         # MEASURED, not a hypothesis: DESE's receiving file splits the headcount into
         # residents and children from other towns, and the assert above ties the two
         # halves to the headcount. So the town's "Resident" column, which IS the headcount,
         # already holds those children, and its total adds school choice again on top.
         con('DESE’s %s includes %s children from other towns; the town’s table adds %s more.'
             % (C.num(d26['total']), C.num(fl1['in_all']), C.num(tr['district_choice_in'])),
             ['now', 'dese-in', 'town', 'town-choice'],
             {'a': N(d26['total']), 'b': N(fl1['in_all']), 'c': N(tr['district_choice_in'])},
             notes=[step('DESE counts %s of those children under school choice and the town '
                         'counts %s; nothing here matches the two lists child by child.'
                         % (C.num(fl1['in_choice']), C.num(tr['district_choice_in'])), 'gap',
                         {'a': N(fl1['in_choice']), 'b': N(tr['district_choice_in'])},
                         closes='the district’s 1 October school choice roster for the same year',
                         allow=('1 October',))])],
        chart=year_chart,
        table=year_table,
        sources=S('dese-enrollment-by-grade.xlsx', '4130-fy-2025-annual-town-report.pdf',
                  'dese-sped-program-characteristics.xlsx'),
        finding_figures={'a': N(d26['total']), 'y': F(last_fy),
                         'b': N(pk['total'] - d26['total']), 'z': F(pk['fy']),
                         'x': F(tr0['fy'])})

    # ------------------------------------------------ enrolment by grade band
    bands = {b['band']: b for b in EN['bands']}
    k5, g68, hs = bands['pre-K to grade 5'], bands['grades 6-8'], bands['grades 9-12']
    if (k5['last'], g68['last'], hs['last']) != (d26['k5'], d26['g68'], d26['g912']):
        fail('enrollment.json: the bands’ last year is not the FY2026 district row')
    b0 = EN['base_fy']
    if (k5['first'], g68['first'], hs['first']) != (dist[b0]['k5'], dist[b0]['g68'], dist[b0]['g912']):
        fail('enrollment.json: the bands’ first year is not the base-year district row')
    hsP, k5P, mdP = -p100(hs['pct']), -p100(k5['pct']), -p100(g68['pct'])
    YB, YL = F(b0), F(last_fy)
    order = ['Lunenburg Primary School', 'Turkey Hill Elementary School',
             'Lunenburg Middle School', 'Lunenburg High', 'Advanced Community Experience Program']
    if sorted(order) != sorted(sch26):
        fail('enrollment.json: the FY2026 schools are not the five this page names')
    out['enrolment-by-grade-band'] = TP.page(
        'enrolment-by-grade-band',
        'Grades 9–12 lost %s of their children from %s to %s; pre-K to grade 5 lost %s.'
        % (C.pct(hsP), C.fy(b0), C.fy(last_fy), C.pct(k5P)),
        [f('hs0', N(hs['first'], 'children'), 'in grades 9–12, %s' % C.fy(b0), 'published',
           {'y': YB}, allow=('9–12',)),
         f('hs1', N(hs['last'], 'children'), 'in grades 9–12, %s' % C.fy(last_fy), 'published',
           {'y': YL}, allow=('9–12',)),
         f('hsp', P(hsP), 'fall in grades 9–12 (our arithmetic)', 'published', allow=('9–12',)),
         f('k50', N(k5['first'], 'children'), 'pre-K to grade 5, %s' % C.fy(b0), 'published',
           {'y': YB}, allow=('grade 5',)),
         f('k51', N(k5['last'], 'children'), 'pre-K to grade 5, %s' % C.fy(last_fy), 'published',
           {'y': YL}, allow=('grade 5',)),
         f('md0', N(g68['first'], 'children'), 'in grades 6–8, %s' % C.fy(b0), 'published',
           {'y': YB}, allow=('6–8',)),
         f('md1', N(g68['last'], 'children'), 'in grades 6–8, %s' % C.fy(last_fy), 'published',
           {'y': YL}, allow=('6–8',))],
        [con('Grades 9–12 went from %s to %s children, down %s.'
             % (C.num(hs['first']), C.num(hs['last']), C.pct(hsP)), ['hs0', 'hs1', 'hsp'],
             {'a': N(hs['first']), 'b': N(hs['last']), 'p': P(hsP)}, allow=('9–12',),
             notes=[step('Where the missing ninth graders went is not in this file: a vocational '
                         'admission, a private school, school choice and a move are one absence.',
                         'gap', closes='DESE’s residents-by-district file with a grade on each '
                                       'row')]),
         con('The younger bands fell far less: %s for pre-K to grade 5, %s for grades 6–8.'
             % (C.pct(k5P), C.pct(mdP)), ['k50', 'k51', 'md0', 'md1'],
             {'a': P(k5P), 'b': P(mdP)}, allow=('grade 5', '6–8'))],
        # The three bands over the same years: the finding is that one fell much further.
        chart=(lambda ys: TP.series('Enrolment by grade band', [C.fy(y) for y in ys], [
            TP.track('Pre-K to grade 5', [dist[y]['k5'] if y in dist else None for y in ys]),
            TP.track('Grades 6–8', [dist[y]['g68'] if y in dist else None for y in ys]),
            TP.track('Grades 9–12', [dist[y]['g912'] if y in dist else None for y in ys])],
            'children', note='DESE’s 1 October headcount, Lunenburg district rows.',
            note_allow=('1 October',)))([y for y in span(dist) if y >= b0]),
        table=dict(caption='Enrolment by grade band and by school', views=[
            dict(key='bands', label='Grade bands, %s and %s' % (C.fy(b0), C.fy(last_fy)),
                 total_col=-1, kinds=['ledger', 'ledger', 'stated'],
                 columns=[C.fy(b0), C.fy(last_fy), 'Change'],
                 rows=[dict(label=lab, cells=[C.num(b['first']), C.num(b['last']),
                                              C.pct(p100(b['pct']))])
                       for lab, b in (('Pre-K to grade 5', k5), ('Grades 6–8', g68),
                                      ('Grades 9–12', hs))],
                 note='DESE’s 1 October headcount. The change column is our arithmetic.'),
            dict(key='schools', label='Schools, %s' % C.fy(last_fy), total_col=-1,
                 kinds=['ledger'], columns=['Children'],
                 rows=[dict(label=s, cells=[C.num(sch26[s])]) for s in order],
                 note='DESE’s school rows for the same count.')]),
        sources=S('dese-enrollment-by-grade.xlsx'),
        finding_figures={'a': P(hsP), 'y': YB, 'z': YL, 'b': P(k5P)},
        finding_allow=('9–12', 'grade 5'))

    # ------------------------------------------------ high-needs students
    li = EN['low_income']
    old14 = li['old'][-1]
    ec0, ec1 = li['econ'][0], li['econ'][-1]
    nw0, nw1 = li['new'][0], li['new'][-1]
    if (old14['fy'], ec0['fy'], ec1['fy'], nw0['fy'], nw1['fy']) != (2014, 2015, 2021, 2022, last_fy):
        fail('enrollment.json: the three low-income series no longer break where this page says')
    hn_first = min(y for y, r in dist.items() if r['high_needs'] is not None)
    hn_share = p100(d26['high_needs'] / d26['total'])
    el0 = dist[b0]['el']
    if d26['swd'] != sp_enr['swd']:
        fail('enrollment.json and sped-students.json disagree on students with disabilities')
    pop_rows = [dict(label=C.fy(y), cells=[
        C.num(dist[y]['el']), C.num(dist[y]['swd']),
        C.num(dist[y]['high_needs']) if dist[y]['high_needs'] is not None else None])
        for y in sorted(dist, reverse=True) if y >= b0]
    li_rows = []
    for y in sorted(dist, reverse=True):
        if y < b0:
            continue
        o = next((r['n'] for r in li['old'] if r['fy'] == y), None)
        e = next((r['n'] for r in li['econ'] if r['fy'] == y), None)
        n = next((r['n'] for r in li['new'] if r['fy'] == y), None)
        li_rows.append(dict(label=C.fy(y), cells=[None if v is None else C.num(v) for v in (o, e, n)]))
    out['high-needs-students'] = TP.page(
        'high-needs-students',
        'English learners went from %s to %s; low income was measured three ways and is not one series.'
        % (C.num(el0), C.num(d26['el'])),
        [f('el0', N(el0, 'children'), 'English learners, %s' % C.fy(b0), 'published', {'y': YB}),
         f('el1', N(d26['el'], 'children'), 'English learners, %s' % C.fy(last_fy), 'published',
           {'y': YL}),
         f('li14', P(p100(old14['pct'])), 'low income, free or reduced lunch, %s' % C.fy(2014),
           'published', {'y': F(2014)}),
         f('ec15', N(ec0['n'], 'children'), 'economically disadvantaged, %s' % C.fy(2015),
           'published', {'y': F(2015)}),
         f('ec21', N(ec1['n'], 'children'), 'economically disadvantaged, %s' % C.fy(2021),
           'published', {'y': F(2021)}),
         f('li22', P(p100(nw0['pct'])), 'low income, broader definition, %s' % C.fy(nw0['fy']),
           'published', {'y': F(nw0['fy'])}),
         f('li26', P(p100(nw1['pct'])), 'low income, broader definition, %s' % C.fy(last_fy),
           'published', {'y': YL}),
         f('hn26', N(d26['high_needs'], 'children'), 'high needs, %s' % C.fy(last_fy),
           'published', {'y': YL}),
         f('hnshare', P(hn_share), 'of enrolment, %s (our arithmetic)' % C.fy(last_fy),
           'published', {'y': YL}),
         f('swd26', N(d26['swd'], 'children'), 'students with disabilities, %s' % C.fy(last_fy),
           'published', {'y': YL})],
        [con('English learners rose from %s children in %s to %s in %s.'
             % (C.num(el0), C.fy(b0), C.num(d26['el']), C.fy(last_fy)), ['el0', 'el1'],
             {'a': N(el0), 'y': YB, 'b': N(d26['el']), 'z': YL},
             notes=[step('Which languages, which schools and what it costs to teach them are '
                         'not in DESE’s file.', 'gap',
                         closes='the district’s English learner roster by school and its EL '
                                'staffing budget')]),
         con('Low income is three series, not one: %s in %s, %s in %s, under three definitions.'
             % (C.pct(p100(old14['pct'])), C.fy(2014), C.pct(p100(nw1['pct'])), C.fy(last_fy)),
             ['li14', 'ec15', 'ec21', 'li22', 'li26'],
             {'a': P(p100(old14['pct'])), 'y': F(2014), 'b': P(p100(nw1['pct'])), 'z': YL},
             notes=[step('Each definition is a proxy for household income and the proxies '
                         'differ, so the rise across a definition change is not a measurement '
                         'of poverty.', 'gap',
                         closes='one low-income definition applied to every year, which DESE '
                                'does not publish')]),
         con('%s children were high needs in %s, %s of enrolment.'
             % (C.num(d26['high_needs']), C.fy(last_fy), C.pct(hn_share)),
             ['hn26', 'hnshare', 'swd26'],
             {'a': N(d26['high_needs']), 'y': YL, 'p': P(hn_share)},
             notes=[step('High needs is DESE’s union of the groups: a child can be an English '
                         'learner, low income and on a plan at once, so the groups are never '
                         'added.', 'gap', closes='nothing; it is the definition. DESE '
                                                 'publishes the union, not the overlaps')])],
        # Low income as three tracks because it IS three definitions (rule 13a): the steps
        # where one hands over to the next are definition changes, not measurements.
        chart=(lambda ys, o, e, n, el: TP.series(
            'English learners and low income', [C.fy(y) for y in ys], [
                TP.track('Low income, free or reduced lunch', [o.get(y) for y in ys]),
                TP.track('Economically disadvantaged', [e.get(y) for y in ys]),
                TP.track('Low income, broader definition', [n.get(y) for y in ys]),
                TP.track('English learners', [el.get(y) for y in ys])],
            'children', note='DESE’s counts. The three low-income lines are three definitions '
                             'and never one series.'))(
            [y for y in span(dist) if y >= b0], {r['fy']: r['n'] for r in li['old']},
            {r['fy']: r['n'] for r in li['econ']}, {r['fy']: r['n'] for r in li['new']},
            {y: r['el'] for y, r in dist.items() if r['el'] is not None}),
        table=dict(caption='Groups within enrolment, by year', views=[
            dict(key='groups', label='English learners, disabilities, high needs', total_col=-1,
                 kinds=['ledger'] * 3,
                 columns=['English learners', 'With disabilities', 'High needs'], rows=pop_rows,
                 note='DESE’s counts. High needs is published from %s; a blank is a year DESE '
                      'did not publish it.' % C.fy(hn_first)),
            dict(key='income', label='Low income, three definitions', total_col=-1,
                 kinds=['ledger'] * 3,
                 columns=['Free or reduced lunch', 'Economically disadvantaged',
                          'Low income, broader'], rows=li_rows,
                 note='Three definitions, never one series. A blank is a year the definition '
                      'was not in use.')]),
        sources=S('dese-enrollment-by-grade.xlsx'),
        finding_figures={'a': N(el0), 'b': N(d26['el'])})

    # ------------------------------------------------ nearby districts
    peers = {p['district']: p for p in EN['peers']}
    me = peers['Lunenburg']
    others = sorted((p for p in EN['peers'] if p['district'] != 'Lunenburg'),
                    key=lambda p: p['pct'])
    most, least = others[0], others[-1]
    fell_more = sum(1 for p in others if p['pct'] < me['pct'])
    if me['first'] != dist[b0]['total'] or me['last'] != d26['total']:
        fail('enrollment.json: the Lunenburg peer row is not the district series')
    pf = {p['district']: f('p-' + p['district'].lower().replace(' ', '-').replace('–', '-'),
                           P(-p100(p['pct'])), '%s fall, %s to %s' % (p['district'], C.fy(b0),
                                                                       C.fy(last_fy)),
                           'published', {'a': YB, 'b': YL})
          for p in EN['peers']}
    out['nearby-district-enrolment'] = TP.page(
        'nearby-district-enrolment',
        'Lunenburg’s enrolment fell %s from %s to %s; %s of %s nearby districts fell further.'
        % (C.pct(-p100(me['pct'])), C.fy(b0), C.fy(last_fy), C.num(fell_more), C.num(len(others))),
        [pf[p['district']] for p in EN['peers']],
        [con('%s fell most, %s; %s fell least, %s.'
             % (most['district'], C.pct(-p100(most['pct'])), least['district'],
                C.pct(-p100(least['pct']))),
             [pf[most['district']]['id'], pf[least['district']]['id'], pf['Lunenburg']['id']],
             {'a': P(-p100(most['pct'])), 'b': P(-p100(least['pct']))},
             notes=[step('Ayer Shirley regionalised in %s and has no %s row, so it is left out.'
                         % (C.fy(2012), C.fy(b0)), 'gap', {'a': F(2012), 'b': YB},
                         closes='a combined Ayer and Shirley count for the years before the '
                                'region formed'),
                    step('Births and housing are outside this file, so why the region fell is '
                         'not tested here.', 'hypothesis')])],
        # Drawn as the FALL, the same positive figure the facts print, so a bar and its tile
        # cannot round one number two ways.
        chart=TP.ranking('Enrolment fall, nearby districts',
                         [(p['district'], -p100(p['pct'])) for p in EN['peers']], '%',
                         highlight='Lunenburg',
                         basis='estimate',
                         note='%s to %s, DESE’s 1 October headcount for each district (the fall '
                              'is our arithmetic).' % (C.fy(b0), C.fy(last_fy)),
                         note_figures={'a': YB, 'b': YL}, note_allow=('1 October',)),
        table=dict(caption='Enrolment in nearby districts and Lunenburg', views=[dict(
            key='peers', label='%s and %s' % (C.fy(b0), C.fy(last_fy)), total_col=-1,
            kinds=['ledger', 'ledger', 'stated'], columns=[C.fy(b0), C.fy(last_fy), 'Change'],
            rows=[dict(label=p['district'], cells=[C.num(p['first']), C.num(p['last']),
                                                    C.pct(p100(p['pct']))])
                  for p in EN['peers']],
            note='DESE’s 1 October headcount for each district. The change is our arithmetic.')]),
        sources=S('dese-enrollment-by-grade.xlsx'),
        finding_figures={'p': P(-p100(me['pct'])), 'a': YB, 'b': YL, 'n': N(fell_more),
                         'm': N(len(others))})

    # ------------------------------------------------ grade-to-grade loss
    ot = AT['outlier']
    gp = {g['grade']: g for g in AT['grade_profile']}
    if gp['8']['times_highest'] != ot['years'] or round(gp['8']['mean'], 4) != round(ot['mean'], 4):
        fail('attrition.json: grade 8 is no longer the highest grade every year')
    swd = next(g for g in AT['groups'] if g['grp'] == 'Students with Disabilities')
    gg = AT['group_gap']['widest']
    if gg['grade'] != '8' or round(gg['group_mean'], 4) != round(swd['mean'], 4):
        fail('attrition.json: the widest disability gap is no longer at grade 8')
    g8, lo, hi = p100(ot['mean']), p100(ot['others_low']), p100(ot['others_high'])
    sw = p100(swd['mean'])
    lo_g = next(g['grade'] for g in AT['grade_profile'] if round(g['mean'], 4) == round(ot['others_low'], 4))
    G8 = ('grade 8', 'Grade 8', 'grade 9', 'eighth')
    grade_rows = [dict(label='Grade %s' % g['grade'] if g['grade'] != 'K' else 'Kindergarten',
                       cells=[C.pct(p100(g['mean'])), C.pct(p100(g['min'])), C.pct(p100(g['max']))])
                  for g in AT['grade_profile']]
    out['grade-to-grade-loss'] = TP.page(
        'grade-to-grade-loss',
        'On average %s of eighth graders do not return for grade 9; other grades lose %s to %s.'
        % (C.pct(g8), C.pct(lo), C.pct(hi)),
        [f('g8', P(g8), 'grade 8 leaving rate, mean of %s years' % C.num(ot['years']),
           'published', {'n': N(ot['years'])}, allow=('grade 8',)),
         f('lo', P(lo), 'lowest other grade, mean (grade %s)' % lo_g, 'published',
           allow=('grade %s' % lo_g,)),
         f('hi', P(hi), 'highest other grade, mean (grade %s)' % ot['runner_up'], 'published',
           allow=('grade %s' % ot['runner_up'],)),
         f('top', N(gp['8']['times_highest'], 'years'),
           'of %s in which grade 8 lost the most' % C.num(ot['years']), 'published',
           {'n': N(ot['years'])}, allow=('grade 8',)),
         f('implied', N(ot['implied_per_year'], 'children'),
           'eighth graders a year, rate times enrolment (ours)', 'estimate'),
         f('swd', P(sw), 'grade 8 rate, students with disabilities', 'published',
           allow=('grade 8',)),
         f('swdlo', P(p100(swd['min'])), 'that group’s lowest year', 'published'),
         f('swdhi', P(p100(swd['max'])), 'that group’s highest year', 'published'),
         f('where', None, 'which school each eighth grader went to', 'gap',
           closes='DESE’s residents-by-district file with a grade on each row, or the '
                  'district’s October return broken out by exit grade and reason')],
        [con('Grade 8 was the highest-leaving grade in all %s years DESE publishes.'
             % C.num(ot['years']), ['g8', 'top', 'lo', 'hi'], {'n': N(ot['years'])}, allow=G8,
             notes=[step('A vocational admission, a private or charter school, school choice, '
                         'a placement and a move all fit the rate. Nothing published separates '
                         'them.', 'hypothesis')]),
         con('That is about %s children a year, an implied count rather than one anybody '
             'published.' % C.num(ot['implied_per_year']), ['implied'],
             {'n': N(ot['implied_per_year'])}),
         con('Eighth graders with disabilities leave at %s against %s for all students.'
             % (C.pct(sw), C.pct(g8)), ['swd', 'g8', 'swdlo', 'swdhi'],
             {'a': P(sw), 'b': P(g8)},
             notes=[step('The group is on the order of twenty children a grade, so it swings '
                         'from %s to %s between years. A placement made at the transition fits '
                         'it as well as a move does.' % (C.pct(p100(swd['min'])),
                                                         C.pct(p100(swd['max']))),
                         'hypothesis', {'a': P(p100(swd['min'])), 'b': P(p100(swd['max']))})]),
         con('No published record says where a departing eighth grader went.', ['where'],
             allow=G8)],
        # The latest year's own rates, read off DESE's file -- no mean taken -- with grade 8,
        # the grade the finding is about, marked. It was the highest in every year.
        chart=TP.ranking('Leaving rate by grade, the latest year',
                         [('Kindergarten' if g['grade'] == 'K' else 'Grade %s' % g['grade'],
                           p100(g['rate'])) for g in AT['district'][-1]['grades']], '%',
                         highlight='Grade 8',
                         note='SY%d, DESE’s attrition rate. Grade 8 was the highest grade in all '
                              '%s years the file covers.' % (AT['district'][-1]['sy'],
                                                            C.num(ot['years'])),
                         note_figures={'y': SY(AT['district'][-1]['sy']), 'n': N(ot['years'])},
                         note_allow=('Grade 8',)),
        table=dict(caption='Leaving rate by grade', views=[dict(
            key='grades', label='Every grade, %s years' % C.num(ot['years']), total_col=-1,
            kinds=['ledger', 'ledger', 'ledger'], columns=['Mean', 'Lowest year', 'Highest year'],
            rows=grade_rows,
            note='DESE’s attrition rate: the share of a grade enrolled one year and not enrolled '
                 'the next autumn. The mean of the yearly rates is our arithmetic.')]),
        said=[said(AT, 'band-transition')],
        sources=S('dese-student-attrition.xlsx', 'dese-enrollment-by-grade.xlsx',
                  'dese-residents-sending.xlsx'),
        finding_figures={'a': P(g8), 'b': P(lo), 'c': P(hi)}, finding_allow=('grade 9',))

    # ------------------------------------------------ grade 8 trend
    lt = ot['latest']
    er = AT['eras']
    rank_word = {1: 'highest', 2: 'second-highest', 3: 'third-highest'}[ot['rank_of_latest']]
    g8_rows = [dict(label='SY%d' % r['sy'], cells=[C.pct(p100(r['rate'])), C.num(r['cohort']),
                                                    '%.1f' % r['implied']])
               for r in sorted(ot['series'], key=lambda r: -r['sy'])]
    out['grade-8-loss-trend'] = TP.page(
        'grade-8-loss-trend',
        'The latest grade 8 rate, %s, is the %s of %s years, inside a range the town has always been in.'
        % (C.pct(p100(lt['rate'])), rank_word, C.num(ot['years'])),
        [f('latest', P(p100(lt['rate'])), 'grade 8 leaving rate, SY%d' % lt['sy'], 'published',
           {'y': SY(lt['sy'])}, allow=('grade 8',)),
         f('max', P(p100(ot['max'])), 'the highest year, SY%d' % ot['max_sy'], 'published',
           {'y': SY(ot['max_sy'])}),
         f('min', P(p100(ot['min'])), 'the lowest year, SY%d' % ot['min_sy'], 'published',
           {'y': SY(ot['min_sy'])}),
         f('cohort', N(lt['cohort'], 'children'), 'in that grade 8, %s' % C.fy(lt['cohort_fy']),
           'published', {'y': F(lt['cohort_fy'])}, allow=('grade 8',)),
         f('run', N(ot['rising_run'], 'years'), 'the current run of rises', 'published'),
         f('prior', N(ot['longest_prior_rising_run'], 'years'), 'the longest earlier run',
           'published'),
         f('spread', figure(p100(er['spread']), C.points(p100(er['spread']))),
           'between the five eras’ averages', 'published')],
        [con('%s in SY%d sits between the %s low and the %s high of the series.'
             % (C.pct(p100(lt['rate'])), lt['sy'], C.pct(p100(ot['min'])), C.pct(p100(ot['max']))),
             ['latest', 'min', 'max'],
             {'a': P(p100(lt['rate'])), 'y': SY(lt['sy']), 'b': P(p100(ot['min'])),
              'c': P(p100(ot['max']))}),
         con('The rise has run %s years; an earlier run was also %s.'
             % (C.num(ot['rising_run']), C.num(ot['longest_prior_rising_run'])), ['run', 'prior'],
             {'a': N(ot['rising_run']), 'b': N(ot['longest_prior_rising_run'])},
             notes=[step('Whether it continues is not something three points can say.',
                         'hypothesis')]),
         con('Split at each school reorganisation, the eras’ averages sit within %s of each other.'
             % C.points(p100(er['spread'])), ['spread'],
             {'s': figure(p100(er['spread']), C.points(p100(er['spread'])))}),
         con('In a grade of %s children, each child who leaves moves the rate almost a point.'
             % C.num(lt['cohort']), ['cohort'], {'n': N(lt['cohort'])})],
        chart=TP.series('Eighth-grade leaving rate by year', ['SY%d' % r['sy'] for r in ot['series']],
                        [TP.track('Grade 8, share not back the next autumn',
                                  [p100(r['rate']) for r in ot['series']])], '%',
                        note='DESE’s attrition rate for grade 8, every school year it publishes.',
                        note_allow=('grade 8',)),
        table=dict(caption='Grade 8 leaving rate by year', views=[dict(
            key='g8', label='Seventeen years', total_col=-1, kinds=['ledger', 'ledger', 'stated'],
            columns=['Rate', 'Grade 8 the year before', 'Implied children'], rows=g8_rows,
            note='DESE’s rate and DESE’s enrolment. The implied column multiplies them and is '
                 'ours, not a headcount anybody published.')]),
        sources=S('dese-student-attrition.xlsx', 'dese-enrollment-by-grade.xlsx'),
        finding_figures={'a': P(p100(lt['rate'])), 'n': N(ot['years'])},
        finding_allow=('grade 8',))

    # ------------------------------------------------ leaving and arriving
    all_last = AT['district'][-1]
    out['leaving-and-arriving'] = TP.page(
        'leaving-and-arriving',
        'DESE’s rates imply about %s children leave each year; enrolment fell %s in %s years.'
        % (C.num(ch['per_year_whole']), C.num(-ch['enrol_change']), C.num(ch['transitions'])),
        [f('per', N(ch['per_year_whole'], 'children'), 'leaving a year, implied (ours)',
           'estimate'),
         f('total', N(ch['implied_total'], 'departures'),
           'implied over %s years (ours)' % C.num(ch['transitions']), 'estimate',
           {'n': N(ch['transitions'])}),
         f('e0', N(ch['enrol_first'], 'children'), 'enrolled, %s' % C.fy(ch['first_fy']),
           'published', {'y': F(ch['first_fy'])}),
         f('e1', N(ch['enrol_last'], 'children'), 'enrolled, %s' % C.fy(ch['last_fy']),
           'published', {'y': F(ch['last_fy'])}),
         f('rate', P(p100(all_last['all'])), 'of all grades leaving, SY%d' % all_last['sy'],
           'published', {'y': SY(all_last['sy'])}),
         f('who', None, 'who arrives in place of those who leave', 'gap',
           closes='the district’s enrolment records coded by entry reason: moved in, returned '
                  'from private school, choice, repeat')],
        [con('Implied departures over %s years total %s; enrolment fell %s.'
             % (C.num(ch['transitions']), C.num(ch['implied_total']), C.num(-ch['enrol_change'])),
             ['total', 'e0', 'e1'],
             {'n': N(ch['transitions']), 'a': N(ch['implied_total']), 'b': N(-ch['enrol_change'])},
             notes=[step('Each implied figure is DESE’s rate times DESE’s enrolment. A child who '
                         'leaves and returns is two events, so it is not a count of children.',
                         'gap', closes='the district’s withdrawal records, counted by child')]),
         con('So arrivals offset most departures; who arrives is a residual nothing here '
             'measures.', ['per', 'rate', 'who'],
             notes=[step('Births, families moving in and children returning from private '
                         'schools all fit the residual equally.', 'hypothesis')])],
        # Two flows a year: the departures DESE's rate implies (ours, so an estimate) and the
        # headcount's own change. The distance between them is the arrivals nobody counts.
        chart=TP.series('Implied departures and the net change', ['SY%d' % r['sy'] for r in ch['years']], [
            TP.track('Departures, rate times enrolment', [r['implied'] for r in ch['years']],
                     'estimate', 'bar'),
            TP.track('Net change in enrolment',
                     [dist[r['sy']]['total'] - dist[r['sy'] - 1]['total'] for r in ch['years']],
                     'published', 'bar')], 'children',
            note='Departures are DESE’s rate times its enrolment (ours). The net change is each '
                 'headcount less the year before.'),
        sources=S('dese-student-attrition.xlsx', 'dese-enrollment-by-grade.xlsx'),
        finding_figures={'a': N(ch['per_year_whole']), 'b': N(-ch['enrol_change']),
                         'n': N(ch['transitions'])})

    # ------------------------------------------------ children schooled elsewhere
    of0, rc = OF['first'], OF['route_change']
    r0 = OF['routes'][0]
    out['children-schooled-elsewhere'] = TP.page(
        'children-schooled-elsewhere',
        '%s resident children were in other public districts in %s, against %s in %s; the mix changed.'
        % (C.num(ol['elsewhere']), C.fy(ol['fy']), C.num(of0['elsewhere']), C.fy(of0['fy'])),
        [f('el0', N(of0['elsewhere'], 'children'), 'schooled in other districts, %s'
           % C.fy(of0['fy']), 'published', {'y': F(of0['fy'])}),
         f('el1', N(ol['elsewhere'], 'children'), 'schooled in other districts, %s'
           % C.fy(ol['fy']), 'published', {'y': F(ol['fy'])}),
         f('share', P(ol['elsewhere_pct']), 'of resident children, %s' % C.fy(ol['fy']),
           'published', {'y': F(ol['fy'])}),
         f('mt0', N(r0['monty_tech'], 'children'), 'at Monty Tech, %s' % C.fy(r0['fy']),
           'published', {'y': F(r0['fy'])}),
         f('mt1', N(rlast['monty_tech'], 'children'), 'at Monty Tech, %s' % C.fy(rlast['fy']),
           'published', {'y': F(rlast['fy'])}),
         f('ch0', N(r0['school_choice'], 'children'), 'school choice out, %s' % C.fy(r0['fy']),
           'published', {'y': F(r0['fy'])}),
         f('ch1', N(rlast['school_choice'], 'children'), 'school choice out, %s'
           % C.fy(rlast['fy']), 'published', {'y': F(rlast['fy'])}),
         f('cs0', N(r0['charter'], 'children'), 'at charter schools, %s' % C.fy(r0['fy']),
           'published', {'y': F(r0['fy'])}),
         f('cs1', N(rlast['charter'], 'children'), 'at charter schools, %s' % C.fy(rlast['fy']),
           'published', {'y': F(rlast['fy'])}),
         f('private', None, 'children at private or parochial schools', 'gap',
           closes='nothing the state publishes; private schools do not report enrolment by '
                  'town of residence')],
        [con('The total moved from %s to %s while Monty Tech rose from %s to %s.'
             % (C.num(of0['elsewhere']), C.num(ol['elsewhere']), C.num(r0['monty_tech']),
                C.num(rlast['monty_tech'])), ['el0', 'el1', 'mt0', 'mt1'],
             {'a': N(of0['elsewhere']), 'b': N(ol['elsewhere']), 'c': N(r0['monty_tech']),
              'd': N(rlast['monty_tech'])}),
         con('School choice went from %s to %s and charter schools from %s to %s.'
             % (C.num(r0['school_choice']), C.num(rlast['school_choice']), C.num(r0['charter']),
                C.num(rlast['charter'])), ['ch0', 'ch1', 'cs0', 'cs1'],
             {'a': N(r0['school_choice']), 'b': N(rlast['school_choice']), 'c': N(r0['charter']),
              'd': N(rlast['charter'])},
             notes=[step('A count of departures is not a reason for them; nothing here or in '
                         'the meeting record surveys the households.', 'hypothesis')]),
         con('These are public districts only, so the total is a floor.', ['private', 'share'],
             notes=[step('The file carries no disability flag either, so none of these is a '
                         'special education count.', 'gap',
                         closes='DESE’s residents-by-district file with disability status')])],
        chart=TP.series('Resident children in other districts', [C.fy(r['fy']) for r in OF['routes']], [
            TP.track('All public districts elsewhere', [r['elsewhere'] for r in OF['routes']]),
            TP.track('Monty Tech', [r['monty_tech'] for r in OF['routes']]),
            TP.track('School choice', [r['school_choice'] for r in OF['routes']]),
            TP.track('Charter schools', [r['charter'] for r in OF['routes']])], 'children',
            note='DESE’s enrolment of town residents by district. Private schools are not in it, '
                 'so the total is a floor.'),
        table=dict(caption='Resident children schooled outside Lunenburg, by route', views=[dict(
            key='routes', label='Thirteen years', total_col=3, kinds=['ledger'] * 4,
            columns=['Monty Tech', 'School choice', 'Charter', 'All elsewhere'],
            rows=[dict(label=C.fy(r['fy']), cells=[C.num(r['monty_tech']),
                                                    C.num(r['school_choice']), C.num(r['charter']),
                                                    C.num(r['elsewhere'])])
                  for r in sorted(OF['routes'], key=lambda r: -r['fy'])],
            note='DESE’s enrolment of town residents by district. All elsewhere includes a few '
                 'children under other programmes, such as another vocational district.')]),
        sources=S('dese-residents-sending.xlsx', 'dese-enrollment-receiving.xlsx'),
        finding_figures={'a': N(ol['elsewhere']), 'y': F(ol['fy']), 'b': N(of0['elsewhere']),
                         'z': F(of0['fy'])})

    # ------------------------------------------------ school choice flows
    net = OF['net']
    n0, n1 = net[0], net[-1]
    outs = [r['out'] for r in net]
    pk_out = max(net, key=lambda r: r['out'])
    lo_out = min(net, key=lambda r: r['out'])
    if pk_out['out'] != OF['peak_choice'] or pk_out['fy'] != OF['peak_choice_year']:
        fail('sped-leaving.json: the school choice peak disagrees with its own series')
    out['school-choice-flows'] = TP.page(
        'school-choice-flows',
        '%s residents left under school choice in %s and %s arrived; arrivals were %s in %s.'
        % (C.num(n1['out']), C.fy(n1['fy']), C.num(n1['in']), C.num(n0['in']), C.fy(n0['fy'])),
        [f('out1', N(n1['out'], 'children'), 'residents out by school choice, %s' % C.fy(n1['fy']),
           'published', {'y': F(n1['fy'])}),
         f('in1', N(n1['in'], 'children'), 'arriving by school choice, %s' % C.fy(n1['fy']),
           'published', {'y': F(n1['fy'])}),
         f('in0', N(n0['in'], 'children'), 'arriving by school choice, %s' % C.fy(n0['fy']),
           'published', {'y': F(n0['fy'])}),
         f('outpk', N(pk_out['out'], 'children'), 'out by school choice, %s, the most'
           % C.fy(pk_out['fy']), 'published', {'y': F(pk_out['fy'])}),
         f('outlo', N(lo_out['out'], 'children'), 'out by school choice, %s, the fewest'
           % C.fy(lo_out['fy']), 'published', {'y': F(lo_out['fy'])}),
         f('net1', N(-n1['net'], 'children'), 'net loss by school choice, %s' % C.fy(n1['fy']),
           'published', {'y': F(n1['fy'])}),
         f('tuition', None, 'what the town pays for each child who chooses out', 'gap',
           closes='the DLS Cherry Sheet for Lunenburg, which prints the school choice sending '
                  'assessment on its own line')],
        [con('Children leaving by school choice ranged from %s to %s a year.'
             % (C.num(lo_out['out']), C.num(pk_out['out'])), ['outpk', 'outlo', 'out1'],
             {'a': N(lo_out['out']), 'b': N(pk_out['out'])}),
         con('Children arriving by school choice fell from %s in %s to %s in %s.'
             % (C.num(n0['in']), C.fy(n0['fy']), C.num(n1['in']), C.fy(n1['fy'])), ['in0', 'in1'],
             {'a': N(n0['in']), 'y': F(n0['fy']), 'b': N(n1['in']), 'z': F(n1['fy'])},
             notes=[step('The district decides how many seats to open, so fewer seats offered '
                         'and fewer families applying both fit this. Nothing published '
                         'separates them.', 'hypothesis')]),
         con('No document in the archive states the tuition that follows a child either way.',
             ['tuition', 'net1'])],
        chart=TP.series('School choice, both directions', [C.fy(r['fy']) for r in net], [
            TP.track('Residents leaving', [r['out'] for r in net]),
            TP.track('Children arriving', [r['in'] for r in net])], 'children', kind='bar',
            note='DESE’s two enrolment files, school choice rows only.'),
        table=dict(caption='School choice, both directions', views=[dict(
            key='net', label='Thirteen years', total_col=-1, kinds=['ledger'] * 3,
            columns=['Out', 'In', 'Net'],
            rows=[dict(label=C.fy(r['fy']), cells=[C.num(r['out']), C.num(r['in']),
                                                    C.num(r['net'])])
                  for r in sorted(net, key=lambda r: -r['fy'])],
            note='DESE’s two enrolment files, school choice rows only. Net is in minus out.')]),
        said=[said(LV, 'seats'), said(LV, 'uneven')],
        sources=S('dese-residents-sending.xlsx', 'dese-enrollment-receiving.xlsx'),
        finding_figures={'a': N(n1['out']), 'y': F(n1['fy']), 'b': N(n1['in']),
                         'c': N(n0['in']), 'z': F(n0['fy'])})
    if len(outs) != len(OF['routes']):
        fail('sped-leaving.json: the school choice series and the routes differ in length')

    # ------------------------------------------------ the departure scenario (ASSUMED)
    df = sc['defaults']
    lc = LV['formula_history']['latest_components']
    if lc['foundaidinc'] != 0 or abs(lc['minaidinc'] / lc['enrollment'] - sc['aid_per_pupil']) > 0.005:
        fail('the marginal aid is no longer the minimum aid increment over foundation pupils')
    out['departure-scenario'] = TP.page(
        'departure-scenario',
        'A scenario on assumed rates: %s students choosing out would take %s from the town in year one.'
        % (C.num(sc['leavers']), C.usd(sc['net_cost'])),
        [f('leavers', N(sc['leavers'], 'students'), 'high school students leaving, assumed',
           'estimate'),
         f('rate', U(df['tuition']), 'school choice base tuition a child, c.76 §12B', 'statute',
           allow=('c.76 §12B',)),
         f('tuit', U(sc['tuition_out']), 'sending tuition, year one (ours)', 'estimate'),
         f('aidpp', U(sc['aid_per_pupil']), 'aid a foundation pupil at the margin, %s (ours)'
           % C.fy(2026), 'published', {'y': F(2026)}),
         f('aid', U(sc['aid_loss']), 'Chapter 70 aid lost, year one (ours)', 'estimate',
           allow=('70',)),
         f('total', U(sc['net_cost']), 'leaving the town, year one (ours)', 'estimate'),
         f('fpp', U(sc['foundation_per_pupil']), 'foundation budget a pupil, the formula’s rate',
           'published'),
         f('upper', U(sc['aid_loss_upper']), 'aid lost if priced at that rate (ours)',
           'estimate'),
         f('base', N(sc['baseline_out'], 'children'), 'out by school choice, %s'
           % C.fy(sc['baseline_sy']), 'published', {'y': F(sc['baseline_sy'])}),
         f('after', N(sc['after_out'], 'children'), 'out by school choice, with the scenario',
           'estimate'),
         f('rate-gap', None, 'the tuition Lunenburg actually pays a child', 'gap',
           closes='the DLS Cherry Sheet for Lunenburg, school choice sending line')],
        [con('Of the %s, %s is sending tuition and %s is Chapter 70 aid at the margin.'
             % (C.usd(sc['net_cost']), C.usd(sc['tuition_out']), C.usd(sc['aid_loss'])),
             ['total', 'tuit', 'aid', 'rate', 'aidpp'],
             {'a': U(sc['net_cost']), 'b': U(sc['tuition_out']), 'c': U(sc['aid_loss'])},
             allow=('70',),
             notes=[step('The tuition is the statutory base rate, which is higher for special '
                         'education; no document here states what Lunenburg pays.', 'gap',
                         closes='the DLS Cherry Sheet for Lunenburg, school choice sending line')]),
         con('Priced at the formula’s %s a pupil, the aid alone would be %s.'
             % (C.usd(sc['foundation_per_pupil']), C.usd(sc['aid_loss_upper'])), ['fpp', 'upper'],
             {'a': U(sc['foundation_per_pupil']), 'b': U(sc['aid_loss_upper'])},
             notes=[step('The %s margin is %s’s minimum aid increment, %s, over %s foundation '
                         'pupils. The Legislature resets it every year.'
                         % (C.usd(sc['aid_per_pupil']), C.fy(lc['fy']), C.usd(lc['minaidinc']),
                            C.num(lc['enrollment'])), 'gap',
                         {'a': U(sc['aid_per_pupil']), 'y': F(lc['fy']), 'b': U(lc['minaidinc']),
                          'n': N(lc['enrollment'])}, allow=('Chapter 70',),
                         closes='DESE’s preliminary Chapter 70 calculation for the year in '
                                'question')]),
         con('It would take school choice out from %s to %s, %s times what DESE counts.'
             % (C.num(sc['baseline_out']), C.num(sc['after_out']), '%.2f' % sc['after_multiple']),
             ['base', 'after', 'leavers'],
             {'a': N(sc['baseline_out']), 'b': N(sc['after_out']),
              'm': figure(sc['after_multiple'], '%.2f' % sc['after_multiple'])}),
         con('The scenario assumes no saving: the students come from four grades, so no '
             'classroom closes.', ['leavers', 'total'],
             notes=[step('Nothing published says at what enrolment a section is removed.', 'gap',
                         closes='the district’s staffing rule for when a section is added or '
                                'removed')])],
        # The scenario's year-one figure IS these two parts (asserted above); every part is
        # on assumed rates, so the whole is an estimate.
        chart=TP.parts('Year one of the scenario', [('Sending tuition', sc['tuition_out']),
                                                    ('Chapter 70 aid lost', sc['aid_loss'])],
                       '$', basis='estimate',
                       note='Assumed rates, not a forecast: the statutory base tuition and the '
                            'minimum aid increment.'),
        said=[said(OF, 'fivethousand')],
        sources=S('dese-residents-sending.xlsx', 'dese-ch70-district-profile.xlsx',
                  'ch70-fy27-summary.xlsx'),
        finding_figures={'n': N(sc['leavers']), 'a': U(sc['net_cost'])})

    # ------------------------------------------------ Monty Tech enrolment
    cnt = {r['fy']: r for r in MT['counts']}
    c26 = cnt[2026]
    if c26['headcount'] != hl['students'] or c26['foundation'] != hl['foundation']:
        fail('monty-tech.json: the counts table and the headline disagree for FY2026')
    gaps_c = [r['difference'] for r in MT['counts']]
    if any(g == 0 for g in gaps_c) or min(gaps_c) != hl['count_gap_min'] or max(gaps_c) != hl['count_gap_max']:
        fail('monty-tech.json: the two Monty Tech counts no longer differ in every year as stated')
    st26 = next(s for s in MT['students'] if s['fy'] == 2026)
    if st26['all_resident'] != ol['total']:
        fail('monty-tech.json and sped-leaving.json disagree on resident schoolchildren')
    mshare = p100(st26['monty_tech'] / st26['all_resident'])
    if not all(c26['headcount'] > d['students'] for d in OF['destinations']):
        fail('Monty Tech is no longer the largest outside district residents attend')
    fe, fb = p100(hl['fe_share']), p100(hl['fb_share'])
    out['monty-tech-enrolment'] = TP.page(
        'monty-tech-enrolment',
        '%s residents attended Monty Tech in %s, up from %s in %s: more than any other outside district.'
        % (C.num(c26['headcount']), C.fy(2026), C.num(hl['students_from']), C.fy(hl['from_fy'])),
        [f('hc', N(c26['headcount'], 'children'), 'at Monty Tech, DESE headcount, %s' % C.fy(2026),
           'published', {'y': F(2026)}),
         f('fe', N(c26['foundation'], 'pupils'), 'at Monty Tech, DESE foundation enrolment, %s'
           % C.fy(2026), 'published', {'y': F(2026)}),
         f('hc0', N(hl['students_from'], 'children'), 'at Monty Tech, headcount, %s'
           % C.fy(hl['from_fy']), 'published', {'y': F(hl['from_fy'])}),
         f('res', P(mshare), 'of %s resident schoolchildren (ours)' % C.num(st26['all_resident']),
           'published', {'n': N(st26['all_resident'])}),
         f('feshare', P(fe), 'of the town’s foundation enrolment, %s' % C.fy(2026), 'published',
           {'y': F(2026)}),
         f('fbshare', P(fb), 'of the town’s foundation budget, %s' % C.fy(2026), 'published',
           {'y': F(2026)}),
         f('turned', None, 'Lunenburg applicants Monty Tech turned away', 'gap',
           closes='Monty Tech’s admissions report by member town: applicants, admitted, '
                  'waitlisted')],
        [con('Monty Tech enrolment went from %s in %s to %s in %s.'
             % (C.num(hl['students_from']), C.fy(hl['from_fy']), C.num(c26['headcount']),
                C.fy(2026)), ['hc0', 'hc', 'res'],
             {'a': N(hl['students_from']), 'y': F(hl['from_fy']), 'b': N(c26['headcount']),
              'z': F(2026)},
             notes=[step('A count is families applying and Monty Tech admitting; nothing '
                         'published separates demand from capacity.', 'hypothesis')]),
         con('DESE counts %s by headcount and %s by foundation enrolment for the same year.'
             % (C.num(c26['headcount']), C.num(c26['foundation'])), ['hc', 'fe'],
             {'a': N(c26['headcount']), 'b': N(c26['foundation'])},
             notes=[step('Foundation enrolment differs from the headcount in all %s years, from '
                         '%s below it to %s above. Nothing published reconciles them.'
                         % (C.num(len(gaps_c)), C.num(-hl['count_gap_min']),
                            C.num(hl['count_gap_max'])), 'gap',
                         {'n': N(len(gaps_c)), 'b': N(-hl['count_gap_min']),
                          'c': N(hl['count_gap_max'])},
                         closes='DESE’s definition of foundation enrolment for a regional '
                                'vocational member, beside its October headcount')]),
         con('Monty Tech is %s of the town’s foundation enrolment and %s of its foundation '
             'budget.' % (C.pct(fe), C.pct(fb)), ['feshare', 'fbshare'],
             {'a': P(fe), 'b': P(fb)},
             notes=[step('The state’s formula sets a larger foundation budget for a vocational '
                         'pupil. That is the formula’s assumption, not a measured cost.',
                         'gap', closes='Monty Tech’s spending attributed to member towns, which '
                                       'no published document gives')])],
        chart=TP.series('Monty Tech pupils, two DESE counts', [C.fy(r['fy']) for r in MT['counts']], [
            TP.track('Headcount, 1 October', [r['headcount'] for r in MT['counts']]),
            TP.track('Foundation enrolment, Chapter 70', [r['foundation'] for r in MT['counts']])],
            'children', note='Two counts of the same residents that differ every year. Neither is '
                             'chosen or averaged.'),
        table=dict(caption='Lunenburg residents at Monty Tech, two DESE counts', views=[dict(
            key='counts', label='Thirteen years', total_col=-1, kinds=['ledger'] * 3,
            columns=['Headcount', 'Foundation enrolment', 'Difference'],
            rows=[dict(label=C.fy(r['fy']), cells=[C.num(r['headcount']),
                                                    ('%.2f' % r['foundation']).rstrip('0').rstrip('.'),
                                                    ('%.2f' % r['difference']).rstrip('0').rstrip('.')])
                  for r in sorted(MT['counts'], key=lambda r: -r['fy'])],
            note='The headcount is DESE’s 1 October enrolment of residents by district; '
                 'foundation enrolment is the Chapter 70 formula’s count. Neither is averaged.')]),
        said=[said(MT, 'disentangle')],
        sources=S('dese-residents-sending.xlsx', 'dese-ch70-key-factors.xlsx'),
        finding_figures={'a': N(c26['headcount']), 'y': F(2026), 'b': N(hl['students_from']),
                         'z': F(hl['from_fy'])})

    # ------------------------------------------------ Monty Tech assessment
    fc = MT['forecast']
    rqp = p100(a26['required_share'])
    share_from = p100(req[fc['base_fy']]['fb_share'])
    a_rows = []
    for y in sorted(asm, reverse=True):
        r = asm[y]
        cell = lambda v: None if v is None else C.usd(v)
        a_rows.append(dict(label=C.fy(y), cells=[C.usd(r['total']), cell(r['required']),
                                                 cell(r['transport']), cell(r['capital'])]))
    out['monty-tech-assessment'] = TP.page(
        'monty-tech-assessment',
        'Lunenburg’s %s Monty Tech bill was %s; %s of it is a minimum the state sets.'
        % (C.fy(2026), C.usd(a26['total']), C.pct(rqp)),
        [f('bill', U(a26['total']), 'Monty Tech assessment, %s' % C.fy(2026), 'published',
           {'y': F(2026)}),
         f('req', U(a26['required']), 'state-required minimum within it', 'published'),
         f('trans', U(a26['transport']), 'transportation and other operating', 'published'),
         f('cap', U(a26['capital']), 'capital', 'published'),
         f('share', P(rqp), 'of the bill set by the state formula', 'published'),
         f('town', U(r26['town_rlc']), 'one town-wide requirement, %s' % C.fy(2026), 'published',
           {'y': F(2026)}),
         f('lps', U(r26['lps_rlc']), 'of it to Lunenburg Public Schools', 'published'),
         f('proj', U(fc['projected']), '%s projection for %s, at %s a year'
           % (fc['date'][:4], C.fy(fc['actual_fy']), C.pct(p100(fc['rate']))), 'published',
           {'y': F(fc['actual_fy']), 'r': P(p100(fc['rate']))}, allow=(fc['date'][:4],)),
         f('cagr', P(p100(fc['required_cagr'])), 'a year, the required minimum (our arithmetic)',
           'published'),
         f('next', U(asm[2027]['total']), 'Monty Tech assessment, %s' % C.fy(2027), 'published',
           {'y': F(2027)})],
        [con('Transportation, %s, and capital, %s, are the only parts outside the formula.'
             % (C.usd(a26['transport']), C.usd(a26['capital'])),
             ['trans', 'cap', 'req', 'share', 'bill'],
             {'a': U(a26['transport']), 'b': U(a26['capital'])}),
         con('The state requires %s from the town; %s of it is for Lunenburg Public Schools.'
             % (C.usd(r26['town_rlc']), C.usd(r26['lps_rlc'])), ['town', 'lps', 'req'],
             {'a': U(r26['town_rlc']), 'b': U(r26['lps_rlc'])},
             notes=[step('The rest is Monty Tech’s share, split by each district’s share of '
                         'the town’s foundation budget. Whether the agreement lets that change is '
                         'not established.', 'gap',
                         closes='the regional agreement itself, which is not in this archive')]),
         con('A %s projection at %s a year put %s at %s; the bill was %s.'
             % (fc['date'][:4], C.pct(p100(fc['rate'])), C.fy(fc['actual_fy']),
                C.usd(fc['projected']), C.usd(fc['actual'])), ['proj', 'bill', 'cagr'],
             {'r': P(p100(fc['rate'])), 'y': F(fc['actual_fy']), 'a': U(fc['projected']),
              'b': U(fc['actual'])}, allow=(fc['date'][:4],),
             notes=[step('The required minimum compounded at %s a year and Monty Tech’s share of '
                         'the foundation budget went from %s to %s. Why the projection used its '
                         'rate is not stated.' % (C.pct(p100(fc['required_cagr'])),
                                                  C.pct(share_from), C.pct(fb)), 'gap',
                         {'a': P(p100(fc['required_cagr'])), 'b': P(share_from), 'c': P(fb)},
                         closes='the method behind the projection in the Select Board packet')])],
        chart=(lambda ys: TP.series('Monty Tech assessment and its minimum', [C.fy(y) for y in ys], [
            TP.track('The assessment', [asm[y]['total'] for y in ys], 'stated', 'bar'),
            TP.track('State-required minimum', [asm[y]['required'] for y in ys], 'published',
                     'line')], '$',
            note='The district’s budget books, and for one year the Town’s appropriation; the '
                 'minimum is DESE’s. A gap is a year it was not published.'))(sorted(asm)),
        table=dict(caption='The Monty Tech assessment, by year and part', views=[dict(
            key='parts', label='Five years', total_col=0,
            kinds=['stated', 'ledger', 'stated', 'stated'],
            columns=['Total', 'Required minimum', 'Transportation', 'Capital'], rows=a_rows,
            note='The district’s budget books, except one year that is the Town’s appropriation '
                 'and one stated by the district as the prior year’s figure. The required '
                 'minimum is DESE’s. A blank is a part not published for that year.')]),
        said=[said(MT, 'governed'), said(MT, 'reduce')],
        sources=S('3583-fy27-monty-tech-budget-presentation-pdf.pdf',
                  'a103-fy24-monty-tech-budget-for-public-hearing-march-08-2023-pdf.pdf',
                  'dese-ch70-key-factors.xlsx', 'glytdbud-expense-fy2026-p12-gf-all.xlsx',
                  '3769-fy-2027-operating-budgets-balanced-tier-1-tier2.pdf',
                  '2021-01-19-minutes-5244.txt'),
        finding_figures={'y': F(2026), 'a': U(a26['total']), 'p': P(rqp)})

    # ------------------------------------------------ Monty Tech funding
    # WHERE THE DISTRICT'S OPERATING BUDGET COMES FROM, off the Budget Summary (PDF page 25)
    # as build_monty_tech.py read it: every figure anchored in the document text, every
    # identity the page prints checked there, and the five sources footing to the printed
    # Total Budget. Re-checked here, because this page is the one that publishes the split.
    dv = {r['fy']: r for r in MT['district']}
    if sorted(dv) != [2026, 2027]:
        fail('monty-tech.json: the district budget is no longer FY2026 and FY2027')
    NAMES = dict(ch70='State Chapter 70 aid', assessments='Member towns’ assessments',
                 transport_aid='State transportation aid',
                 excess_deficiency='Excess & Deficiency (reserves)',
                 regional_transport_fund='Regional Transportation Fund')
    for y, r in dv.items():
        ps = r['revenue']['parts']
        if [p['key'] for p in ps] != list(NAMES):
            fail('monty-tech.json: FY%d revenue sources are not the five this page names' % y)
        if sum(p['amount'] for p in ps) != r['budget'] or not r['revenue']['ties']:
            fail('FY%d: the five revenue sources no longer sum to the printed Total Budget' % y)
        if ps[0]['amount'] != r['ch70'] or ps[1]['amount'] != r['all_assessments']:
            fail('FY%d: Chapter 70 or the assessments disagree with the district summary' % y)
    d6, d7 = dv[2026], dv[2027]
    rv6 = {p['key']: p for p in d6['revenue']['parts']}
    rv7 = {p['key']: p for p in d7['revenue']['parts']}
    if d6['lunenburg'] != a26['total']:
        fail('Lunenburg’s FY2026 assessment differs between the summary and the parts table')
    sh = lambda p: p100(p['share'])
    rest6 = sum(sh(rv6[k]) for k in ('transport_aid', 'excess_deficiency',
                                     'regional_transport_fund'))
    rest6_amt = sum(rv6[k]['amount'] for k in ('transport_aid', 'excess_deficiency',
                                               'regional_transport_fund'))
    lun6 = p100(d6['lunenburg_of_assessments'])
    mtpp = PS['destinations']['widest']
    if mtpp['lea'] != '08320000':
        fail('peer-spending.json: the widest destination is no longer Monty Tech (LEA 08320000)')
    pp_fy = PS['destinations']['fin_fy']
    ga = MT['figures']['grant-awards']
    gr = ga['values']['fy25_grant_awards']
    PG = MT['figures']['district-budget']
    if PG['docs_url'] != src['3583-fy27-monty-tech-budget-presentation-pdf.pdf']['href']:
        fail('the Budget Summary is no longer read off the presentation this page cites')
    summary_src = dict(label='Montachusett Regional Vocational Technical School District — '
                             'FY27 Monty Tech Budget Presentation, FY 2027 Budget Summary, PDF '
                             'page 25', href=PG['docs_url'] + '#page=25')
    grants_src = dict(label='The same presentation — Update of Annual Grant Awards, PDF page 5',
                      href=ga['docs_url'] + '#page=5')
    yrs = [2026, 2027]
    CH70 = ('Chapter 70',)
    out['monty-tech-funding'] = TP.page(
        'monty-tech-funding',
        'State Chapter 70 aid paid %s of Monty Tech’s %s operating budget; the member towns paid %s.'
        % (C.pct(sh(rv6['ch70'])), C.fy(2026), C.pct(sh(rv6['assessments']))),
        [f('budget', U(d6['budget']), 'Monty Tech operating budget, %s' % C.fy(2026),
           'published', {'y': F(2026)}),
         f('ch70', U(rv6['ch70']['amount']), 'state Chapter 70 aid, paid by the state', 'published',
           allow=CH70),
         f('towns', U(rv6['assessments']['amount']), 'assessed on the member towns',
           'published'),
         f('aid', U(rv6['transport_aid']['amount']), 'state transportation aid', 'published'),
         f('ed', U(rv6['excess_deficiency']['amount']),
           'from Excess & Deficiency, the district’s reserve', 'published'),
         f('rtf', U(rv6['regional_transport_fund']['amount']), 'from its Regional Transportation Fund',
           'published'),
         f('lun', U(d6['lunenburg']), 'of it assessed on Lunenburg, %s' % C.fy(2026), 'published',
           {'y': F(2026)}),
         f('next', U(d7['budget']), 'operating budget proposed, %s' % C.fy(2027), 'published',
           {'y': F(2027)}),
         f('pp', U(mtpp['per_pupil']), 'a pupil, all funds (DESE), %s: another measure'
           % C.fy(pp_fy), 'published',
           {'y': F(pp_fy)}),
         f('grants', U(gr), 'grant awards the district charts for %s' % C.fy(2025), 'published',
           {'y': F(2025)}),
         f('funds', None, 'Monty Tech’s spending by fund, in dollars', 'gap',
           closes='DESE’s End of Year Financial Report for LEA 08320000, which splits '
                  'spending by fund')],
        [con('The state’s Chapter 70 aid paid %s of the %s budget; the towns’ assessments %s.'
             % (C.pct(sh(rv6['ch70'])), C.fy(2026), C.pct(sh(rv6['assessments']))),
             ['ch70', 'towns', 'budget'],
             {'a': P(sh(rv6['ch70'])), 'y': F(2026), 'b': P(sh(rv6['assessments']))}, allow=CH70),
         con('Lunenburg’s %s was %s of the towns’ assessments; it pays none of the Chapter 70.'
             % (C.usd(d6['lunenburg']), C.pct(lun6)), ['lun', 'towns', 'ch70'],
             {'a': U(d6['lunenburg']), 'p': P(lun6)}, allow=CH70),
         con('The other %s, %s, is state transportation aid and the district’s own funds.'
             % (C.pct(rest6), C.usd(rest6_amt)), ['aid', 'ed', 'rtf'],
             {'p': P(rest6), 'a': U(rest6_amt)}),
         con('This is the operating budget only; DESE’s %s a pupil for %s counts every fund.'
             % (C.usd(mtpp['per_pupil']), C.fy(pp_fy)), ['pp', 'grants', 'funds', 'budget'],
             {'a': U(mtpp['per_pupil']), 'y': F(pp_fy)},
             notes=[step('That the difference between them is grants and other funds is a '
                         'hypothesis. The %s of %s awards is an award total, not a year’s '
                         'spending.' % (C.usd(gr), C.fy(2025)), 'hypothesis',
                         {'a': U(gr), 'y': F(2025)}),
                    step('Monty Tech’s spending split by fund is not in this archive.', 'gap',
                         allow=('08320000',),
                         closes='DESE’s End of Year Financial Report for LEA 08320000, which '
                                'splits spending by fund')])],
        chart=TP.series('Monty Tech operating budget by source', [C.fy(y) for y in yrs], [
            TP.track(NAMES[k], [{p['key']: p for p in dv[y]['revenue']['parts']}[k]['amount']
                                for y in yrs], 'stated', 'bar') for k in NAMES],
            '$', kind='bar', stacked=True,
            note='The district’s own Budget Summary, a sheet it assembled: %s approved, %s '
                 'proposed. Operating budget only; grants and revolving funds are outside it.'
                 % (C.fy(2026), C.fy(2027)),
            note_figures={'y': F(2026), 'z': F(2027)}),
        table=dict(caption='Monty Tech’s operating budget, by source', views=[dict(
            key='sources', label='Two years', total_col=-1,
            kinds=['stated'] * 4,
            columns=['%s approved' % C.fy(2026), 'Share', '%s proposed' % C.fy(2027), 'Share'],
            rows=[dict(label=NAMES[k], cells=[C.usd(rv6[k]['amount']), C.pct(sh(rv6[k])),
                                              C.usd(rv7[k]['amount']), C.pct(sh(rv7[k]))])
                  for k in NAMES]
                 + [dict(label='Total Budget', cells=[C.usd(d6['budget']), C.pct(100.0),
                                                      C.usd(d7['budget']), C.pct(100.0)])],
            note='The FY 2027 Budget Summary, PDF page 25. Excess & Deficiency is the sum of '
                 'what it applies to operating and to capital. The five sum to the printed '
                 'Total Budget in both years, checked by the generator.')]),
        sources=[summary_src, grants_src, src['district-expenditures-by-function.xlsx']],
        finding_figures={'a': P(sh(rv6['ch70'])), 'y': F(2026), 'b': P(sh(rv6['assessments']))},
        finding_allow=CH70)

    # ------------------------------------------------ the hub
    h = {}
    h['h-now'] = f('h-now', N(d26['total'], 'children'), 'enrolled, %s' % C.fy(last_fy),
                   'published', {'y': YL})
    h['h-peak'] = f('h-peak', N(pk['total'], 'children'), 'enrolled, %s, the peak' % C.fy(pk['fy']),
                    'published', {'y': F(pk['fy'])})
    h['h-hs'] = f('h-hs', P(hsP), 'fall in grades 9–12 since %s' % C.fy(b0), 'published',
                  {'y': YB}, allow=('9–12',))
    h['h-el'] = f('h-el', N(d26['el'], 'children'), 'English learners, %s' % C.fy(last_fy),
                  'published', {'y': YL})
    h['h-g8'] = f('h-g8', P(g8), 'of eighth graders not back for grade 9', 'published',
                  allow=('grade 9',))
    h['h-per'] = f('h-per', N(ch['per_year_whole'], 'children'), 'leaving a year, implied (ours)',
                   'estimate')
    h['h-where'] = f('h-where', None, 'where a departing eighth grader went', 'gap',
                     closes='DESE’s residents-by-district file with a grade on each row')
    h['h-else'] = f('h-else', N(ol['elsewhere'], 'children'), 'schooled in other districts, %s'
                    % C.fy(ol['fy']), 'published', {'y': F(ol['fy'])})
    h['h-mt'] = f('h-mt', N(rlast['monty_tech'], 'children'), 'of them at Monty Tech', 'published')
    h['h-ch'] = f('h-ch', N(rlast['school_choice'], 'children'), 'of them by school choice',
                  'published')
    h['h-in'] = f('h-in', N(n1['in'], 'children'), 'arriving by school choice, %s'
                  % C.fy(n1['fy']), 'published', {'y': F(n1['fy'])})
    h['h-bill'] = f('h-bill', U(a26['total']), 'Monty Tech assessment, %s' % C.fy(2026),
                    'published', {'y': F(2026)})
    tiers = [
        LD.tier('How many', [h['h-now'], h['h-peak'], h['h-hs'], h['h-el']]),
        LD.tier('Who leaves', [h['h-g8'], h['h-per'], h['h-where']]),
        LD.tier('Where they go', [h['h-else'], h['h-mt'], h['h-ch'], h['h-in'], h['h-bill']]),
    ]
    hub_ladder = LD.ladder(tiers, [
        LD.conclusion('Enrolment peaked at %s in %s and has held near %s since %s.'
                      % (C.num(pk['total']), C.fy(pk['fy']), C.num(d26['total']), C.fy(tr0['fy'])),
                      ['h-peak', 'h-now'],
                      {'a': N(pk['total']), 'y': F(pk['fy']), 'b': N(d26['total']),
                       'z': F(tr0['fy'])}),
        LD.conclusion('The high school did most of the shrinking: grades 9–12 fell %s.'
                      % C.pct(hsP), ['h-hs'], {'p': P(hsP)}, allow=('9–12',)),
        LD.conclusion('One step loses children: %s of eighth graders are not back for grade 9.'
                      % C.pct(g8), ['h-g8', 'h-per'], {'p': P(g8)}, allow=('grade 9',)),
        LD.conclusion('Of %s residents schooled elsewhere, %s are at Monty Tech, a district the '
                      'town belongs to.' % (C.num(ol['elsewhere']), C.num(rlast['monty_tech'])),
                      ['h-else', 'h-mt', 'h-ch', 'h-bill'],
                      {'a': N(ol['elsewhere']), 'b': N(rlast['monty_tech'])}),
        LD.conclusion('No published record says why any child left, or where an eighth grader '
                      'went.', ['h-where', 'h-in']),
    ])
    out[HUB] = TP.hub(
        HUB,
        '%s children were in Lunenburg’s schools in %s, near where the count has sat since %s. '
        'Another %s residents were schooled in other public districts, %s of them at Monty Tech.'
        % (C.num(d26['total']), C.fy(last_fy), C.fy(tr0['fy']), C.num(ol['elsewhere']),
           C.num(rlast['monty_tech'])),
        hub_ladder, chart=year_chart, table=year_table,
        answer_figures={'a': N(d26['total']), 'y': YL, 'z': F(tr0['fy']),
                        'b': N(ol['elsewhere']), 'c': N(rlast['monty_tech'])})

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
        print('enrolment topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
