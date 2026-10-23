#!/usr/bin/env python3
"""School staffing, split into topic pages: twelve pages and the School staff hub.

    python3 scripts/build_school_staffing_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_school_staffing_topics.py --check   # fail if any output would change

WHY THIS EXISTS. scripts/topics.py has the model: one question per page, under five minutes,
facts first, one to four conclusions resting on them. This shelf absorbs /school-staffing,
/who-works-in-each-school and /paras, which scripts/build_staffing_charts.py selects out of one
build. The two pages about paraprofessional MONEY are home on other shelves (special education,
FY2026 closeout) and are listed here without being touched.

THESE PAGES ARE ABOUT PEOPLE, AND FOUR INSTRUMENTS COUNT THEM. Each figure says which:

  DESE FTE                 full-time equivalents per ASSIGNMENT -- teachers by school, subject
                           and programme; paraprofessionals district-wide. Not people, not
                           filled posts, not who pays.
  DESE headcount           people, once each, by job class, FY2021-FY2023 only, with the
                           state's retention rate.
  the town's rosters       NAMES printed in each annual town report, FY2011-FY2025. No FTE, no
                           fund, no date within the year. Which role a printed title is, is
                           OUR classification (classify_roster_roles.py) and marked estimate.
  the district directory   the district's own contact list, fetched by date. No FTE, no fund.

RULE 13a. Where two of them count the same thing differently -- the state's two teacher files,
the state's two paraprofessional files, a roster against an FTE -- they are separate facts set
side by side, never averaged and never reconciled into one.

RULE 11, AND THE STANDING QUESTION ON ROSTERS. A count of names is not FTE and not a staffing
level; an FTE is not a filled post; neither says which fund pays. Every page that could be read
that way carries the gap and the document that would close it.

NO INDIVIDUAL IS NAMED OR IDENTIFIED. Counts only. Quotations that describe one employee's own
post are left out even where a payload carries them.

IT COMPUTES NOTHING NEW THAT IT CAN READ INSTEAD, and refuses to write where two payloads stop
agreeing where they must:

  fy28/public/data/school-staffing.json          DESE teacher FTE by year, school, subject and
                                                 programme; the comparison-sheet ratios.
  fy28/public/data/who-works-in-each-school.json the rosters, DESE's headcount and retention.
  fy28/public/data/the-paraprofessionals.json    the two DESE paraprofessional files.
  fy28/public/data/sped-students.json            the special education paraprofessional count,
                                                 asserted equal to the file above.
  sources/data/school-staff-directory.csv        the district's staff directory, by fetch.
"""
import argparse
import collections
import csv
import datetime
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
# Lunenburg's two districts. DESE's comparison sheet, not this project, chose the districts
# the teacher rank is taken over, and Monty Tech is one of them: the rank is left as DESE's
# and a note beside it says so (lunenburg_districts, the one place the LEA is typed).
import lunenburg_districts as DIST  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
DOCS_DATA = os.path.join(ROOT, 'fy28', 'public', 'docs', 'data')
OUT_DIR = os.path.join(PUB, 'topics')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
DIRECTORY = os.path.join(ROOT, 'sources', 'data', 'school-staff-directory.csv')
DIR_KEY = 'district-budget/docs/personnel/staff-directory/%s/%s.csv'

MINE = [t for t, (_, home, gen) in REG.TOPICS.items()
        if home == 'school-staffing' and gen == 'build_school_staffing_topics.py']

# The documents a gap would be closed by. Prose, no figures; said once here so two pages
# naming the same remedy cannot drift apart.
EPIMS = ('Lunenburg’s EPIMS work assignment detail by school, job classification and '
         'program area, year by year')
POSITIONS = ('the district’s position control report: each post with its FTE, school, '
             'funding source and whether it was filled')
DATED_ROSTER = 'a dated staff roster, or the district’s October EPIMS submission'
MEMBERSHIP = 'DESE’s statement of how it chooses each year’s comparison districts'


def fail(msg):
    raise SystemExit('build_school_staffing_topics: ' + msg)


def load(name):
    return json.load(open(os.path.join(PUB, name), encoding='utf-8'))


def said(payload, key):
    """One quotation a payload already verified against our copy of the minutes."""
    s = next((x for x in payload['said'] if x['key'] == key), None)
    if s is None:
        fail('quotation %r is no longer in its payload' % key)
    if not s['cite'].startswith('/docs/'):
        fail('quotation %r does not cite our copy' % key)
    return dict(quote=s['quote'], board=s['board'], date=s['date'], href=s['cite'],
                label='%s minutes, %s' % (s['board'], s['date']))


def day(iso):
    d = datetime.date.fromisoformat(iso)
    return '%d %s %d' % (d.day, d.strftime('%B'), d.year)


def sources(fetches):
    man = {r['key'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    out = {}
    dese = 'Massachusetts DESE'
    for k, (key, pub) in {
            'teacher-data': ('state-dese/dese-teacher-data.xlsx', dese),
            'grade-subject': ('state-dese/dese-teachers-by-grade-subject.xlsx', dese),
            'program-area': ('state-dese/dese-teachers-by-program-area.xlsx', dese),
            'enrolment': ('state-dese/dese-enrollment-by-grade.xlsx', dese),
            'retention': ('state-dese/dese-educators-retention.xlsx', dese),
            'sped-program': ('state-dese/dese-sped-program-characteristics.xlsx', dese),
            'radar': ('state-dese/radar-district-comparison.xlsx', dese + ', district comparison'),
            'directory': (DIR_KEY % (fetches[-1], 'directory-of-staff-all-lunenburg-public-'
                                     'schools-staff'),
                          'Lunenburg Public Schools, staff directory, %s' % day(fetches[-1])),
    }.items():
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        out[k] = dict(label='%s — %s' % (pub, key.split('/')[-1]), href='/docs/' + key)
    for k, (f, what) in {
            'roster-counts': ('staff-roster-counts.csv',
                              'names printed on each school roster, by title and year'),
            'roster-provenance': ('PROVENANCE-staff-rosters.md',
                                  'where each annual-report roster was read from'),
            'directory-rows': ('school-staff-directory.csv',
                               'the district directory as each listing prints it'),
    }.items():
        if not os.path.exists(os.path.join(DOCS_DATA, f)):
            fail('/docs/data/%s is not published' % f)
        out[k] = dict(label='Lunenburg Budget Project — %s (%s)' % (f, what),
                      href='/docs/data/' + f)
    return out


def span(*maps):
    """Every year from the first any map holds to the last, so a year nobody printed is a
    gap in a chart and never a zero."""
    ys = sorted(set().union(*[set(m) for m in maps]))
    return list(range(ys[0], ys[-1] + 1))


FTE_UNIT = 'full-time equivalents'


def build():
    SS = load('school-staffing.json')
    WW = load('who-works-in-each-school.json')
    PA = load('the-paraprofessionals.json')
    ST = load('sped-students.json')
    rows_dir = list(csv.DictReader(open(DIRECTORY, encoding='utf-8')))
    fetches = sorted({r['fetched'] for r in rows_dir})
    src = sources(fetches)
    S = lambda *names: [src[n] for n in names]

    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    FTE = lambda v: figure(v, '%.1f' % v, 'full-time equivalents')
    CHG = lambda v: figure(v, '%+.1f' % v if round(v, 1) else '0.0', 'full-time equivalents')
    R2 = lambda v: figure(v, '%.2f' % v, 'per hundred pupils')
    f, con = LD.fact, TP.conclusion
    out = {}

    # ---------------------------------------------------------------- the inputs, checked
    comp = SS['composition']
    dist = {r['fy']: r for r in comp['district']}
    radar = {r['fy']: r for r in SS['state']['points']}
    if WW['composition'] != comp or PA['state'] != SS['state'] or WW['state'] != SS['state']:
        fail('the three staffing payloads no longer carry the same DESE series')
    yrs = sorted(dist)
    pairs = [(a, b) for i, a in enumerate(yrs) for b in yrs[i + 1:]]
    fell = sum(1 for a, b in pairs if dist[b]['fte'] < dist[a]['fte'])
    ew = comp['every_window']
    if (len(pairs), fell) != (ew['pairs'], ew['fell']):
        fail('every_window no longer counts the pairs of years in the district series')

    # ================================================================ teachers over time
    era = comp['eras']['total']
    first, last = yrs[0], yrs[-1]
    win = comp['windows']
    wc, wr, ww = win['charted'], win['recent'], win['whole']
    if (ww['first_fy'], ww['last_fy']) != (first, last) or wr['last_fy'] != last:
        fail('the windows no longer run to the last published year')
    hi = max((dist[y] for y in yrs if y >= era), key=lambda r: r['fte'])
    lo = min((dist[y] for y in yrs if y >= era), key=lambda r: r['fte'])
    gap11a = round(dist[2010]['fte'] - dist[2011]['fte'], 1)
    gap11b = round(dist[2012]['fte'] - dist[2011]['fte'], 1)
    both = sorted(set(radar) & set(dist))
    differ = [y for y in both if abs(radar[y]['teacher_fte'] - dist[y]['fte']) > 0.05]
    ylast_both = both[-1]
    if ylast_both not in differ:
        fail('the two teacher files now agree for %s; the side-by-side fact needs rewriting'
             % ylast_both)
    filled_gap = f('filled-gap', None, 'which teaching posts were filled, and who pays for each',
                   'gap', closes=POSITIONS)
    out['teacher-fte-over-time'] = TP.page(
        'teacher-fte-over-time',
        'The state counted %s teacher FTE in %s, %s fewer than in %s; %s of %s year pairs end lower.'
        % (FTE(dist[last]['fte'])['text'], C.fy(last), '%.1f' % -wr['change'], C.fy(wr['first_fy']),
           C.num(fell), C.num(len(pairs))),
        [f('t-last', FTE(dist[last]['fte']), 'teacher FTE, the state’s count, %s' % C.fy(last),
           'published', {'y': F(last)}),
         f('t-first', FTE(dist[first]['fte']), 'teacher FTE, %s, its first year' % C.fy(first),
           'published', {'y': F(first)}),
         f('t-hi', FTE(hi['fte']), 'teacher FTE, %s, the highest from %s' % (C.fy(hi['fy']), C.fy(era)),
           'published', {'y': F(hi['fy']), 'e': F(era)}),
         f('t-lo', FTE(lo['fte']), 'teacher FTE, %s, the lowest from %s' % (C.fy(lo['fy']), C.fy(era)),
           'published', {'y': F(lo['fy']), 'e': F(era)}),
         f('pairs', N(fell, 'pairs of years'), 'of %s year pairs end lower than they start'
           % C.num(len(pairs)), 'published', {'n': N(len(pairs))}),
         f('w-charted', CHG(wc['change']), 'FTE change, %s to %s' % (C.fy(wc['first_fy']), C.fy(wc['last_fy'])),
           'published', {'a': F(wc['first_fy']), 'b': F(wc['last_fy'])}),
         f('w-recent', CHG(wr['change']), 'FTE change, %s to %s' % (C.fy(wr['first_fy']), C.fy(wr['last_fy'])),
           'published', {'a': F(wr['first_fy']), 'b': F(wr['last_fy'])}),
         f('w-whole', CHG(ww['change']), 'FTE change, %s to %s' % (C.fy(first), C.fy(last)),
           'published', {'a': F(first), 'b': F(last)}),
         f('radar-last', FTE(radar[ylast_both]['teacher_fte']), 'teacher FTE, %s, the state’s '
           'comparison sheet' % C.fy(ylast_both), 'published', {'y': F(ylast_both)}),
         f('file-last', FTE(dist[ylast_both]['fte']), 'teacher FTE, %s, the state’s teacher file'
           % C.fy(ylast_both), 'published', {'y': F(ylast_both)}),
         filled_gap],
        [con('In %s of %s pairs of published years the state counts fewer teachers at the end.'
             % (C.num(fell), C.num(len(pairs))), ['pairs', 't-hi', 't-lo'],
             {'a': N(fell), 'n': N(len(pairs))}),
         con('%s to %s reads %s FTE; %s to %s reads %s; %s to %s, %s.'
             % (C.fy(wc['first_fy']), C.fy(wc['last_fy']), '%+.1f' % wc['change'],
                C.fy(wr['first_fy']), C.fy(wr['last_fy']), '%+.1f' % wr['change'],
                C.fy(first), C.fy(last), '%+.1f' % ww['change']),
             ['w-charted', 'w-recent', 'w-whole', 't-first', 't-last'],
             {'a': F(wc['first_fy']), 'b': F(wc['last_fy']), 'c': CHG(wc['change']),
              'd': F(wr['first_fy']), 'e': F(wr['last_fy']), 'g': CHG(wr['change']),
              'h': F(first), 'i': F(last), 'j': CHG(ww['change'])},
             notes=[step('%s reads %s below %s and %s below %s. No published staffing decision '
                         'explains it, so a window opening there measures the file.'
                         % (C.fy(2011), '%.1f' % gap11a, C.fy(2010), '%.1f' % gap11b, C.fy(2012)),
                         'gap', {'y': F(2011), 'a': FTE(gap11a), 'p': F(2010), 'b': FTE(gap11b),
                                 'q': F(2012)}, closes=EPIMS)]),
         con('The state’s two files print %s and %s teacher FTE for %s; neither is chosen here.'
             % ('%.1f' % radar[ylast_both]['teacher_fte'], '%.1f' % dist[ylast_both]['fte'],
                C.fy(ylast_both)), ['radar-last', 'file-last'],
             {'a': FTE(radar[ylast_both]['teacher_fte']), 'b': FTE(dist[ylast_both]['fte']),
              'y': F(ylast_both)}),
         con('An FTE counts assignments: not people, not filled posts, not who pays.',
             ['t-last', 'filled-gap'])],
        chart=(lambda ys: TP.series('Teacher FTE, two state files', [C.fy(y) for y in ys], [
            TP.track('DESE teacher file', [dist[y]['fte'] if y in dist else None for y in ys],
                     'published', 'bar'),
            TP.track('DESE comparison sheet', [radar[y]['teacher_fte'] if y in radar else None
                                               for y in ys], 'published', 'line')], FTE_UNIT,
            note='Two counts from the same state, set side by side and not reconciled. An FTE '
                 'counts assignments, not people.'))(span(dist, radar)),
        table=dict(caption='Teacher FTE by year, two state files', views=[dict(
            key='years', label='Teacher FTE', total_col=-1, kinds=['ledger'] * 3,
            columns=['Teacher file', 'Comparison sheet', 'Pupils enrolled'],
            rows=[dict(label=C.fy(y), cells=[
                '%.1f' % dist[y]['fte'],
                ('%.1f' % radar[y]['teacher_fte']) if y in radar else None,
                C.num(dist[y]['students'])]) for y in sorted(yrs, reverse=True)],
            note='Both are DESE’s. A blank is a year the comparison sheet does not print. They '
                 'are set side by side and not reconciled.')]),
        said=[said(SS, 'chair-staffing-up'), said(SS, 'composition-not-headcount')],
        sources=S('teacher-data', 'radar', 'enrolment'),
        finding_figures={'a': FTE(dist[last]['fte']), 'y': F(last), 'c': FTE(-wr['change']),
                         'z': F(wr['first_fy']), 'p': N(fell), 'n': N(len(pairs))})

    # ================================================================ teachers per pupil
    ranks_t = {r['fy']: r for r in SS['state']['ranks']['teachers']}
    ranks_p = {r['fy']: r for r in SS['state']['ranks']['paras']}
    rl = SS['state']['last_fy']
    rf = SS['state']['first_fy']
    rt = ranks_t[rl]
    if abs(rt['value'] - radar[rl]['teachers_per_100']) > 1e-9:
        fail('the teacher rank no longer carries Lunenburg’s own ratio')
    chg_all = SS['state']['change']
    chg_ros = SS['state']['change_over_roster_years']
    t09, p09 = 100 * chg_all['teacher_fte']['pct'], 100 * chg_all['pupils_in_district']['pct']
    t11, p11 = 100 * chg_ros['teacher_fte']['pct'], 100 * chg_ros['pupils_in_district']['pct']
    y11 = chg_ros['teacher_fte']['first_fy']
    virtual = sorted({p['district'] for p in PA['peers'] if 'Virtual' in p['district']})
    v_from = min(p['first_fy'] for p in PA['peers'] if p['district'] in virtual)
    of_first = ranks_t[rf]['of']
    # The places within the districts the sheet carries in EVERY year -- the one list on
    # which two years' ranks can be compared. Read off the payload, never chosen here.
    stab = SS['state']['stable_ranks']
    st_t = {r['fy']: r for r in stab['teachers']}
    st_p = {r['fy']: r for r in stab['paras']}
    n_stable = len(stab['members'])
    hn = ww['per_100_high_needs']
    ORD = lambda n: '%d%s' % (n, 'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th'))
    SP_ = lambda v: figure(v, '%+.1f%%' % v)
    peer_rl = {p['district']: next((q['teachers_per_100'] for q in p['points'] if q['fy'] == rl), None)
               for p in PA['peers'] if p['district'] in stab['members']}
    peer_rl['Lunenburg'] = radar[rl]['teachers_per_100']
    if sorted(peer_rl) != sorted(stab['members']) or None in peer_rl.values():
        fail('a stable-list district has no %s ratio' % rl)
    if sorted(peer_rl, key=lambda d: -peer_rl[d]).index('Lunenburg') + 1 != st_t[rl]['rank']:
        fail('the stable-list order no longer puts Lunenburg at the payload’s rank')
    tpp_chart = TP.ranking('Teachers per hundred pupils, the same districts',
                           sorted(peer_rl.items()), 'per hundred pupils', highlight='Lunenburg',
                           basis='estimate',
                           note='%s: DESE’s FTE over its pupils (our division), for only the %s '
                                'districts its sheet carries in every year.' % (C.fy(rl), C.num(n_stable)),
                           note_figures={'y': F(rl), 'n': N(n_stable)})
    # Who is on DESE's sheet in the rank's year, read off the payload -- and whether Monty Tech
    # is one of them. The note under the rank says so only while the sheet says so.
    monty = DIST.dese_name(DIST.MONTY_LEA)
    sheet_rl = {p['district'] for p in PA['peers'] if any(q['fy'] == rl for q in p['points'])}
    if len(sheet_rl) != rt['of']:
        fail('the districts on the %s sheet no longer number the rank’s %d' % (rl, rt['of']))
    mt_note = ([step('One of the %s on DESE’s sheet is %s, Lunenburg’s vocational district, which '
                     'teaches grades %s only. The rank is over DESE’s set, not ours.'
                     % (C.num(rt['of']), DIST.MONTY_SHORT, DIST.grade_span(DIST.MONTY_LEA)),
                     'measured', {'n': N(rt['of'])}, allow=(DIST.grade_span(DIST.MONTY_LEA),),
                     cite=(DIST.MONTY_HREF, DIST.MONTY_SHORT))]
               if monty in sheet_rl else [])
    out['teachers-per-pupil'] = TP.page(
        'teachers-per-pupil',
        'Lunenburg had %s teacher FTE per hundred pupils in %s, %s of %s on the state’s sheet.'
        % ('%.2f' % rt['value'], C.fy(rl), ORD(rt['rank']), C.num(rt['of'])),
        [f('r-last', R2(rt['value']), 'teacher FTE per hundred pupils, %s' % C.fy(rl), 'published',
           {'y': F(rl)}),
         f('r-first', R2(radar[rf]['teachers_per_100']), 'the same ratio, %s' % C.fy(rf), 'published',
           {'y': F(rf)}),
         f('rank', figure(rt['rank'], ORD(rt['rank']), 'place'), 'of %s on the state’s sheet, highest first, %s'
           % (C.num(rt['of']), C.fy(rl)), 'published', {'n': N(rt['of']), 'y': F(rl)}),
         f('of-first', N(of_first, 'districts'), 'districts on the same sheet in %s' % C.fy(rf),
           'published', {'y': F(rf)}),
         f('st-rank', figure(st_t[rl]['rank'], ORD(st_t[rl]['rank']), 'place'),
           'of the %s on the sheet every year, %s' % (C.num(n_stable), C.fy(rl)), 'published',
           {'n': N(n_stable), 'y': F(rl)}),
         f('t09', SP_(t09), 'teacher FTE change, %s to %s' % (C.fy(rf), C.fy(rl)), 'published',
           {'a': F(rf), 'b': F(rl)}),
         f('p09', SP_(p09), 'pupils in district, the same years', 'published'),
         f('t11', SP_(t11), 'teacher FTE change, %s to %s' % (C.fy(y11), C.fy(rl)), 'published',
           {'a': F(y11), 'b': F(rl)}),
         f('p11', SP_(p11), 'pupils in district, the same years', 'published'),
         f('hn-first', R2(hn['first']), 'teacher FTE per hundred high-needs pupils, %s'
           % C.fy(hn['first_fy']), 'published', {'y': F(hn['first_fy'])}),
         f('hn-last', R2(hn['last']), 'the same ratio, %s' % C.fy(hn['last_fy']), 'published',
           {'y': F(hn['last_fy'])})],
        [con('In %s the state counts %s teacher FTE per hundred pupils, %s of %s districts.'
             % (C.fy(rl), '%.2f' % rt['value'], ORD(rt['rank']), C.num(rt['of'])),
             ['r-last', 'r-first', 'rank', 'of-first'],
             {'y': F(rl), 'a': R2(rt['value']), 'r': figure(rt['rank'], ORD(rt['rank'])),
              'n': N(rt['of'])},
             notes=[step('The sheet held %s districts in %s and %s in %s, %s of them virtual '
                         'schools from %s, so a rank in one year is not a rank in another.'
                         % (C.num(of_first), C.fy(rf), C.num(rt['of']), C.fy(rl),
                            C.num(len(virtual)), C.fy(v_from)), 'gap',
                         {'a': N(of_first), 'y': F(rf), 'b': N(rt['of']), 'z': F(rl),
                          'v': N(len(virtual)), 'w': F(v_from)}, closes=MEMBERSHIP)] + mt_note),
         con('Among the %s districts on the sheet in every year, Lunenburg is %s in %s.'
             % (C.num(n_stable), ORD(st_t[rl]['rank']), C.fy(rl)), ['st-rank'],
             {'n': N(n_stable), 'r': figure(st_t[rl]['rank'], ORD(st_t[rl]['rank'])),
              'y': F(rl)}),
         con('From %s teachers fell %s and pupils %s; from %s teachers rose %s as pupils fell %s.'
             % (C.fy(rf), C.pct(-t09), C.pct(-p09), C.fy(y11), C.pct(t11), C.pct(-p11)),
             ['t09', 'p09', 't11', 'p11'],
             {'y': F(rf), 'a': P(-t09), 'b': P(-p09), 'z': F(y11), 'c': P(t11), 'd': P(-p11)}),
         con('Per hundred high-needs pupils the state counts %s teachers in %s, against %s in %s.'
             % ('%.2f' % hn['last'], C.fy(hn['last_fy']), '%.2f' % hn['first'], C.fy(hn['first_fy'])),
             ['hn-first', 'hn-last'],
             {'a': R2(hn['last']), 'y': F(hn['last_fy']), 'b': R2(hn['first']), 'z': F(hn['first_fy'])},
             notes=[step('One part of “high needs”, low income, was replaced and redefined between '
                         '%s and %s, so the series is not one measure throughout.'
                         % (C.fy(2014), C.fy(2022)), 'gap', {'a': F(2014), 'b': F(2022)},
                         closes='DESE’s definition of high needs for each year it is published')])],
        # A RANK AMONG THE SAME DISTRICTS. The sheet's membership changes year to year, so the
        # chart draws only the districts it carries in every year (stable_ranks), and asserts
        # that its order puts Lunenburg where the payload's own rank does.
        chart=tpp_chart,
        table=dict(caption='Teacher FTE per hundred pupils, the state’s comparison sheet',
                   views=[dict(
                       key='ranks', label='Lunenburg by year', total_col=-1, kinds=['ledger'] * 3,
                       columns=['Per hundred pupils', 'Place', 'Districts on the sheet'],
                       rows=[dict(label=C.fy(y), cells=['%.2f' % ranks_t[y]['value'],
                                                        C.num(ranks_t[y]['rank']),
                                                        C.num(ranks_t[y]['of'])])
                             for y in sorted(ranks_t, reverse=True)],
                       note='Place counts from the highest ratio. DESE chooses who is on the sheet, '
                            'and it changed underneath this series.')]),
        said=[said(SS, 'need-has-risen')],
        sources=S('radar', 'teacher-data', 'enrolment'),
        finding_figures={'a': R2(rt['value']), 'y': F(rl), 'r': figure(rt['rank'], ORD(rt['rank'])),
                         'n': N(rt['of'])})

    # ================================================================ teachers by school
    sc = comp['schools']
    s_era = comp['eras']['school']
    open_rows = [r for r in sc['rows'] if r['open_now'] and r['first_fy'] <= s_era]
    pts = {r['name']: {p['fy']: p for p in r['points']} for r in open_rows}
    if len(open_rows) != 4:
        fail('expected four schools open across the comparable era, found %d' % len(open_rows))
    move = {n: round(p[last]['fte'] - p[s_era]['fte'], 1) for n, p in pts.items()}
    bf = sc['biggest_fall']
    th = pts[bf['name']]
    if min(move, key=move.get) != bf['name']:
        fail('the biggest fall is no longer the school the payload names')
    others = max(abs(v) for n, v in move.items() if n != bf['name'])
    dmove = round(dist[last]['fte'] - dist[s_era]['fte'], 1)
    worst = sc['worst']
    if abs(worst['difference']) != max(abs(r['difference']) for r in sc['reconciliation']):
        fail('the worst reconciliation year is no longer the largest difference')
    short = {'Lunenburg Primary School': 'Primary', 'Turkey Hill Elementary School': 'Turkey Hill',
             'Lunenburg Middle School': 'Middle', 'Lunenburg High': 'High'}
    order = ['Lunenburg Primary School', 'Turkey Hill Elementary School', 'Lunenburg Middle School',
             'Lunenburg High']
    if set(order) != set(pts):
        fail('the four schools are no longer the four this page names')
    per = lambda y: 100.0 * th[y]['fte'] / th[y]['students']
    if abs(per(s_era) - th[s_era]['per_100']) > 1e-9:
        fail('per_100 is no longer FTE per hundred pupils')
    out['teachers-by-school'] = TP.page(
        'teachers-by-school',
        'Turkey Hill Elementary went from %s to %s teacher FTE, %s to %s; the district fell %s.'
        % ('%.1f' % th[s_era]['fte'], '%.1f' % th[last]['fte'], C.fy(s_era), C.fy(last),
           '%.1f' % -dmove),
        [f('th-first', FTE(th[s_era]['fte']), 'teacher FTE, Turkey Hill Elementary, %s' % C.fy(s_era),
           'published', {'y': F(s_era)}),
         f('th-last', FTE(th[last]['fte']), 'the same school, %s' % C.fy(last), 'published',
           {'y': F(last)}),
         f('d-move', CHG(dmove), 'district teacher FTE change, %s to %s' % (C.fy(s_era), C.fy(last)),
           'published', {'a': F(s_era), 'b': F(last)}),
         f('others', FTE(others), 'FTE, the largest move at any other school, same years', 'published'),
         f('thp-first', N(th[s_era]['students'], 'pupils'), 'pupils at Turkey Hill, %s' % C.fy(s_era),
           'published', {'y': F(s_era)}),
         f('thp-last', N(th[last]['students'], 'pupils'), 'pupils at Turkey Hill, %s' % C.fy(last),
           'published', {'y': F(last)}),
         f('thr-first', R2(per(s_era)), 'its teacher FTE per hundred pupils, %s' % C.fy(s_era),
           'published', {'y': F(s_era)}),
         f('thr-last', R2(per(last)), 'the same ratio, %s' % C.fy(last), 'published', {'y': F(last)}),
         f('recon', FTE(abs(worst['difference'])), 'FTE, the most the schools and district differ',
           'published')],
        [con('Turkey Hill Elementary fell from %s to %s teacher FTE; the district fell %s.'
             % ('%.1f' % th[s_era]['fte'], '%.1f' % th[last]['fte'], '%.1f' % -dmove),
             ['th-first', 'th-last', 'd-move'],
             {'a': FTE(th[s_era]['fte']), 'b': FTE(th[last]['fte']), 'c': FTE(-dmove)},
             notes=[step('A fall in FTE fits a post cut, a post split between schools or an '
                         'assignment recoded. Nothing here tests which.', 'hypothesis')]),
         con('No other school moved by more than %s FTE over the same years.' % ('%.1f' % others),
             ['others'], {'a': FTE(others)}),
         con('Per hundred pupils Turkey Hill had %s teacher FTE in %s and %s in %s.'
             % ('%.2f' % per(s_era), C.fy(s_era), '%.2f' % per(last), C.fy(last)),
             ['thr-first', 'thr-last', 'thp-first', 'thp-last'],
             {'a': R2(per(s_era)), 'y': F(s_era), 'b': R2(per(last)), 'z': F(last)}),
         con('The schools sum to the district’s count within %s FTE in every year.'
             % ('%.1f' % abs(worst['difference'])), ['recon'], {'a': FTE(abs(worst['difference']))})],
        chart=TP.series('Teacher FTE by school', [C.fy(y) for y in range(s_era, last + 1)],
                        [TP.track(short[n], [pts[n][y]['fte'] for y in range(s_era, last + 1)])
                         for n in order], FTE_UNIT,
                        note='DESE’s teacher file, from %s, when the schools took their present '
                             'grades.' % C.fy(s_era), note_figures={'y': F(s_era)}),
        table=dict(caption='Teacher FTE by school, %s to %s' % (C.fy(s_era), C.fy(last)), views=[dict(
            key='schools', label='DESE teacher FTE', total_col=-1, kinds=['ledger'] * 4,
            columns=[short[n] for n in order],
            rows=[dict(label=C.fy(y), cells=['%.1f' % pts[n][y]['fte'] for n in order])
                  for y in range(last, s_era - 1, -1)],
            note='From %s, when the schools took their present grades. Earlier years count '
                 'buildings that held different grades, so a series across that line would '
                 'measure the reconfiguration.' % C.fy(s_era))]),
        said=[said(SS, 'turkey-hill-class-sizes')],
        sources=S('teacher-data', 'enrolment'),
        finding_figures={'a': FTE(th[s_era]['fte']), 'b': FTE(th[last]['fte']), 'y': F(s_era),
                         'z': F(last), 'c': FTE(-dmove)})

    # ================================================================ teachers by subject
    subj = comp['subjects']
    wins = {w['key']: w for w in subj['windows']}
    wrun, wpk = wins['the-comparable-run'], wins['since-the-latest-peak']
    for w in (wrun, wpk):
        if abs(w['up'] + w['down'] - w['net']) > 0.05:
            fail('subject window %s no longer nets' % w['key'])
    fall_pk = min(wpk['rows'], key=lambda r: r['change'])
    rise_run = max(wrun['rows'], key=lambda r: r['change'])
    arts = next(r for r in subj['rows'] if r['subject'] == 'Arts')
    ag = subj['agreement']
    out['teachers-by-subject'] = TP.page(
        'teachers-by-subject',
        'From %s to %s subjects lost %s teacher FTE and gained %s; %s alone fell %s.'
        % (C.fy(wpk['first_fy']), C.fy(wpk['last_fy']), '%.1f' % -wpk['down'], '%.1f' % wpk['up'],
           fall_pk['subject'].lower(), '%.1f' % -fall_pk['change']),
        [f('pk-down', FTE(-wpk['down']), 'teacher FTE lost by subjects, %s to %s'
           % (C.fy(wpk['first_fy']), C.fy(wpk['last_fy'])), 'published',
           {'a': F(wpk['first_fy']), 'b': F(wpk['last_fy'])}),
         f('pk-up', FTE(wpk['up']), 'teacher FTE gained by subjects, the same years', 'published'),
         f('pk-fall', FTE(-fall_pk['change']), '%s FTE lost, the same years' % fall_pk['subject'].lower(),
           'published'),
         f('run-up', FTE(wrun['up']), 'FTE gained by subjects, %s to %s'
           % (C.fy(wrun['first_fy']), C.fy(wrun['last_fy'])), 'published',
           {'a': F(wrun['first_fy']), 'b': F(wrun['last_fy'])}),
         f('run-down', FTE(-wrun['down']), 'FTE lost by subjects, the same years', 'published'),
         f('run-rise', FTE(rise_run['change']), '%s FTE gained, the same years'
           % rise_run['subject'].lower(), 'published'),
         f('arts', FTE(arts['latest']), 'Arts FTE, %s: music and art together' % C.fy(arts['last_fy']),
           'published', {'y': F(arts['last_fy'])}),
         f('agree', N(ag['agree'], 'subject-years'), 'of %s where the state’s two subject files agree'
           % C.num(ag['compared']), 'published', {'n': N(ag['compared'])}),
         f('music-gap', None, 'music teacher FTE, apart from art', 'gap',
           closes='the district’s master schedule by year, or EPIMS assignments by course code')],
        [con('From %s to %s subjects lost %s FTE and gained %s; %s fell %s.'
             % (C.fy(wpk['first_fy']), C.fy(wpk['last_fy']), '%.1f' % -wpk['down'], '%.1f' % wpk['up'],
                fall_pk['subject'].lower(), '%.1f' % -fall_pk['change']),
             ['pk-down', 'pk-up', 'pk-fall'],
             {'a': F(wpk['first_fy']), 'b': F(wpk['last_fy']), 'c': FTE(-wpk['down']),
              'd': FTE(wpk['up']), 'e': FTE(-fall_pk['change'])},
             notes=[step('A subject losing FTE may have lost a section, a course, or one '
                         'teacher’s timetable moved across subjects; nothing published says which.',
                         'gap', closes='the district’s master schedule by year')]),
         con('From %s to %s subjects gained %s and lost %s; %s rose %s.'
             % (C.fy(wrun['first_fy']), C.fy(wrun['last_fy']), '%.1f' % wrun['up'],
                '%.1f' % -wrun['down'], rise_run['subject'].lower(), '%.1f' % rise_run['change']),
             ['run-up', 'run-down', 'run-rise'],
             {'a': F(wrun['first_fy']), 'b': F(wrun['last_fy']), 'c': FTE(wrun['up']),
              'd': FTE(-wrun['down']), 'e': FTE(rise_run['change'])}),
         con('The state counts music and art as one subject, so what happened to music is not '
             'shown.', ['arts', 'music-gap']),
         con('The state’s two subject files agree in %s of %s subject-years.'
             % (C.num(ag['agree']), C.num(ag['compared'])), ['agree'],
             {'a': N(ag['agree']), 'n': N(ag['compared'])})],
        chart=(lambda moved: TP.ranking(
            'Teacher FTE change by subject', [(r['subject'], r['change']) for r in moved],
            FTE_UNIT, highlight=fall_pk['subject'],
            note=('%s to %s, DESE’s teachers by grade and subject: every subject that moved.'
                  % (C.fy(wpk['first_fy']), C.fy(wpk['last_fy'])))
            if len(moved) == sum(1 for r in wpk['rows'] if r['change']) else
            ('%s to %s, DESE’s teachers by grade and subject: the %s subjects that moved most, '
             'of %s.' % (C.fy(wpk['first_fy']), C.fy(wpk['last_fy']), C.num(len(moved)),
                         C.num(sum(1 for r in wpk['rows'] if r['change'])))),
            note_figures={'a': F(wpk['first_fy']), 'b': F(wpk['last_fy'])}
            if len(moved) == sum(1 for r in wpk['rows'] if r['change']) else
            {'a': F(wpk['first_fy']), 'b': F(wpk['last_fy']), 'n': N(len(moved)),
             'm': N(sum(1 for r in wpk['rows'] if r['change']))}))(
            sorted((r for r in wpk['rows'] if r['change']), key=lambda r: -abs(r['change']))
            [:TP.ROWS_MAX]),
        table=dict(caption='Teacher FTE by subject', views=[
            dict(key=w['key'], label='%s to %s' % (C.fy(w['first_fy']), C.fy(w['last_fy'])),
                 total_col=-1, kinds=['ledger'] * 3,
                 columns=[C.fy(w['first_fy']), C.fy(w['last_fy']), 'Change'],
                 rows=[dict(label=r['subject'], cells=['%.1f' % r['first'], '%.1f' % r['last'],
                                                       '%+.1f' % r['change']])
                       for r in sorted(w['rows'], key=lambda r: r['change']) if r['first'] or r['last']],
                 note='DESE’s teachers by grade and subject. A subject the file does not print for '
                      'a year is read as none. Teachers counted against every core subject are '
                      'outside these rows.')
            for w in (wpk, wrun)]),
        said=[said(SS, 'cuts-by-subject'), said(SS, 'fy27-cut-list')],
        sources=S('grade-subject', 'teacher-data'),
        finding_figures={'a': F(wpk['first_fy']), 'b': F(wpk['last_fy']), 'c': FTE(-wpk['down']),
                         'd': FTE(wpk['up']), 'e': FTE(-fall_pk['change'])})

    # ================================================================ paraprofessionals, FTE
    pf, pl = radar[rf], radar[rl]
    trough = min(SS['state']['points'], key=lambda r: r['para_fte'])
    if trough['fy'] != SS['state']['trough']['fy']:
        fail('the paraprofessional low is no longer the payload’s trough year')
    rpt, rpl = ranks_p[trough['fy']], ranks_p[rl]
    if rpl['rank'] != 1 or rpt['rank'] != rpt['of']:
        fail('the paraprofessional ranks are no longer first and last; rewrite the conclusion')
    rise_t = round(pl['para_fte'] - trough['para_fte'], 1)
    rise_f = round(pl['para_fte'] - pf['para_fte'], 1)
    out['paraprofessional-fte'] = TP.page(
        'paraprofessional-fte',
        'The state counted %s paraprofessional FTE in %s, against %s in %s and %s in %s.'
        % ('%.1f' % pl['para_fte'], C.fy(rl), '%.1f' % trough['para_fte'], C.fy(trough['fy']),
           '%.1f' % pf['para_fte'], C.fy(rf)),
        [f('p-last', FTE(pl['para_fte']), 'paraprofessional FTE, all programmes, %s' % C.fy(rl),
           'published', {'y': F(rl)}),
         f('p-low', FTE(trough['para_fte']), 'the same count, %s, the lowest' % C.fy(trough['fy']),
           'published', {'y': F(trough['fy'])}),
         f('p-first', FTE(pf['para_fte']), 'the same count, %s, its first year' % C.fy(rf),
           'published', {'y': F(rf)}),
         f('pr-last', R2(pl['paras_per_100']), 'paraprofessional FTE per hundred pupils, %s'
           % C.fy(rl), 'published', {'y': F(rl)}),
         f('pr-low', R2(trough['paras_per_100']), 'the same ratio, %s' % C.fy(trough['fy']),
           'published', {'y': F(trough['fy'])}),
         f('rank-last', N(rpl['of'], 'districts'), 'on the sheet in %s; Lunenburg highest' % C.fy(rl),
           'published', {'y': F(rl)}),
         f('rank-low', N(rpt['of'], 'districts'), 'on the sheet in %s; Lunenburg lowest'
           % C.fy(trough['fy']), 'published', {'y': F(trough['fy'])}),
         f('st-low', figure(st_p[trough['fy']]['rank'], ORD(st_p[trough['fy']]['rank']), 'place'),
           'of the %s on the sheet every year, %s' % (C.num(n_stable), C.fy(trough['fy'])),
           'published', {'n': N(n_stable), 'y': F(trough['fy'])}),
         f('st-last', figure(st_p[rl]['rank'], ORD(st_p[rl]['rank']), 'place'),
           'of the %s on the sheet every year, %s' % (C.num(n_stable), C.fy(rl)),
           'published', {'n': N(n_stable), 'y': F(rl)}),
         f('rise-low', CHG(rise_t), 'FTE change, %s to %s' % (C.fy(trough['fy']), C.fy(rl)),
           'published', {'a': F(trough['fy']), 'b': F(rl)}),
         f('rise-first', CHG(rise_f), 'FTE change, %s to %s' % (C.fy(rf), C.fy(rl)), 'published',
           {'a': F(rf), 'b': F(rl)})],
        [con('The state counted %s paraprofessional FTE in %s, %s in %s and %s in %s.'
             % ('%.1f' % pf['para_fte'], C.fy(rf), '%.1f' % trough['para_fte'], C.fy(trough['fy']),
                '%.1f' % pl['para_fte'], C.fy(rl)), ['p-first', 'p-low', 'p-last'],
             {'a': FTE(pf['para_fte']), 'y': F(rf), 'b': FTE(trough['para_fte']),
              'z': F(trough['fy']), 'c': FTE(pl['para_fte']), 'x': F(rl)},
             notes=[step('Whether the fall to %s was people leaving or the file counting '
                         'differently is not published.' % C.fy(trough['fy']), 'gap',
                         {'y': F(trough['fy'])}, closes=EPIMS)]),
         con('Measured from %s the rise is %s FTE; measured from %s it is %s.'
             % (C.fy(trough['fy']), '%+.1f' % rise_t, C.fy(rf), '%+.1f' % rise_f),
             ['rise-low', 'rise-first'],
             {'y': F(trough['fy']), 'a': CHG(rise_t), 'z': F(rf), 'b': CHG(rise_f)}),
         con('Per hundred pupils that is %s in %s, highest of %s, from %s in %s, lowest of %s.'
             % ('%.2f' % pl['paras_per_100'], C.fy(rl), C.num(rpl['of']),
                '%.2f' % trough['paras_per_100'], C.fy(trough['fy']), C.num(rpt['of'])),
             ['pr-last', 'pr-low', 'rank-last', 'rank-low'],
             {'a': R2(pl['paras_per_100']), 'y': F(rl), 'n': N(rpl['of']),
              'b': R2(trough['paras_per_100']), 'z': F(trough['fy']), 'm': N(rpt['of'])},
             notes=[step('The sheet’s membership changed between those years, so the two places '
                         'are not ranks among the same districts.', 'gap', closes=MEMBERSHIP)]),
         con('Among the %s districts on the sheet in every year, it was %s in %s and %s in %s.'
             % (C.num(n_stable), ORD(st_p[trough['fy']]['rank']), C.fy(trough['fy']),
                ORD(st_p[rl]['rank']), C.fy(rl)), ['st-low', 'st-last'],
             {'n': N(n_stable), 'r': figure(st_p[trough['fy']]['rank'], ORD(st_p[trough['fy']]['rank'])),
              'y': F(trough['fy']), 's': figure(st_p[rl]['rank'], ORD(st_p[rl]['rank'])),
              'z': F(rl)})],
        chart=TP.series('Paraprofessional FTE by year', [C.fy(y) for y in sorted(radar)],
                        [TP.track('All programmes, DESE comparison sheet',
                                  [radar[y]['para_fte'] for y in sorted(radar)])], FTE_UNIT,
                        kind='bar',
                        note='Staff paid from grants and revolving funds are counted alongside '
                             'those the town appropriates for.'),
        table=dict(caption='Paraprofessional FTE by year, the state’s comparison sheet', views=[dict(
            key='years', label='All programmes', total_col=-1, kinds=['ledger'] * 3,
            columns=['FTE', 'Per hundred pupils', 'Place on the sheet'],
            rows=[dict(label=C.fy(y), cells=['%.1f' % radar[y]['para_fte'],
                                             '%.2f' % radar[y]['paras_per_100'],
                                             '%s of %s' % (C.num(ranks_p[y]['rank']),
                                                           C.num(ranks_p[y]['of']))])
                  for y in sorted(radar, reverse=True)],
            note='DESE counts staff paid from grants and revolving funds alongside those the town '
                 'appropriates for, so a grant arriving or ending does not show.')]),
        said=[said(SS, 'esser-hired-13')],
        sources=S('radar'),
        finding_figures={'a': FTE(pl['para_fte']), 'y': F(rl), 'b': FTE(trough['para_fte']),
                         'z': F(trough['fy']), 'c': FTE(pf['para_fte']), 'x': F(rf)})

    # ================================================================ paraprofessional counts
    hc = WW['headcount']
    vs = {r['fy']: r for r in hc['vs_fte']}
    for y, r in vs.items():
        if abs(r['para_fte'] - radar[y]['para_fte']) > 0.05 or \
                abs(r['teacher_fte'] - radar[y]['teacher_fte']) > 0.05:
            fail('the headcount file’s FTE beside it no longer matches the comparison sheet, %s' % y)
    roles = {r['role']: {p['fy']: p['names'] for p in r['points']}
             for r in WW['roster']['roles']}
    rpara = roles['paraprofessional']
    hy = hc['last_fy']
    rup = [r for r in rows_dir if r['fetched'] == fetches[-1] and r['listing_kind'] == 'roll-up']
    titled_para = sum(1 for r in rup if 'paraprofessional' in r['title'].lower())
    title_counts = collections.Counter(r['title'].strip() for r in rup)
    ss_only = title_counts['Special Services']
    dlast = day(fetches[-1])
    out['paraprofessional-counts'] = TP.page(
        'paraprofessional-counts',
        'For %s the state counts %s paraprofessional FTE; the town printed %s paraprofessional '
        'names.' % (C.fy(rl), '%.1f' % radar[rl]['para_fte'], C.num(rpara[rl])),
        [f('c-fte-h', FTE(vs[hy]['para_fte']), 'paraprofessional FTE, the state, %s' % C.fy(hy),
           'published', {'y': F(hy)}),
         f('c-hc-h', N(vs[hy]['para_headcount'], 'people'), 'paraprofessionals as people, the state, %s'
           % C.fy(hy), 'published', {'y': F(hy)}),
         f('c-ro-h', N(rpara[hy], 'names'), 'paraprofessional names the town printed, %s (ours)'
           % C.fy(hy), 'estimate', {'y': F(hy)}),
         f('c-fte-l', FTE(radar[rl]['para_fte']), 'paraprofessional FTE, the state, %s' % C.fy(rl),
           'published', {'y': F(rl)}),
         f('c-ro-l', N(rpara[rl], 'names'), 'paraprofessional names printed, %s (ours)' % C.fy(rl),
           'estimate', {'y': F(rl)}),
         f('c-dir', N(titled_para, 'people'), 'titled paraprofessional, district directory, %s'
           % dlast, 'published', allow=(dlast,)),
         f('c-ss', N(ss_only, 'people'), 'titled only “Special Services”, the same directory',
           'published'),
         f('year-gap', None, 'which school year a printed roster describes', 'gap',
           closes=DATED_ROSTER)],
        [con('For %s the state counts %s paraprofessionals as people and %s as FTE; the town '
             'printed %s.' % (C.fy(hy), C.num(vs[hy]['para_headcount']), '%.1f' % vs[hy]['para_fte'],
                              C.num(rpara[hy])),
             ['c-fte-h', 'c-hc-h', 'c-ro-h'],
             {'y': F(hy), 'a': N(vs[hy]['para_headcount']), 'b': FTE(vs[hy]['para_fte']),
              'c': N(rpara[hy])}),
         con('For %s the state counts %s FTE and the town printed %s names.'
             % (C.fy(rl), '%.1f' % radar[rl]['para_fte'], C.num(rpara[rl])),
             ['c-fte-l', 'c-ro-l', 'year-gap'],
             {'y': F(rl), 'a': FTE(radar[rl]['para_fte']), 'b': N(rpara[rl])},
             notes=[step('Which printed titles are paraprofessionals is our reading, and a roster '
                         'carries no date, so the two may not describe the same year.', 'gap',
                         closes=DATED_ROSTER)]),
         con('The district’s directory titles %s people paraprofessional and %s only “Special '
             'Services”.' % (C.num(titled_para), C.num(ss_only)), ['c-dir', 'c-ss'],
             {'a': N(titled_para), 'b': N(ss_only)},
             notes=[step('Some of those listed as Special Services may be paraprofessionals; the '
                         'titles do not say.', 'hypothesis')])],
        chart=(lambda ys: TP.series('Paraprofessionals, three counts', [C.fy(y) for y in ys], [
            TP.track('Names the town printed (our reading)', [rpara.get(y) for y in ys],
                     'estimate'),
            TP.track('FTE, DESE comparison sheet', [radar[y]['para_fte'] if y in radar else None
                                                    for y in ys]),
            TP.track('People, DESE workforce file', [vs[y]['para_headcount'] if y in vs else None
                                                     for y in ys])], 'count',
            note='Names, FTE and people are three different things, set side by side and never '
                 'reconciled.'))(span(rpara, {y: 1 for y in radar if y >= min(rpara)})),
        table=dict(caption='Paraprofessionals, three counts by year', views=[dict(
            key='three', label='Side by side, not reconciled', total_col=-1,
            kinds=['stated', 'ledger', 'ledger'],
            columns=['Names printed (ours)', 'State FTE', 'State headcount'],
            rows=[dict(label=C.fy(y), cells=[
                C.num(rpara[y]) if y in rpara else None,
                ('%.1f' % radar[y]['para_fte']) if y in radar else None,
                C.num(vs[y]['para_headcount']) if y in vs else None])
                for y in sorted(set(rpara) | {y for y in radar if y >= min(rpara)}, reverse=True)],
            note='Names from the annual town reports, classified by printed title (our reading). '
                 'FTE from DESE’s comparison sheet; headcount from DESE’s workforce file, which '
                 'covers three years.')]),
        sources=S('radar', 'retention', 'roster-counts', 'roster-provenance', 'directory'),
        finding_figures={'y': F(rl), 'a': FTE(radar[rl]['para_fte']), 'b': N(rpara[rl])})

    # ================================================================ staff by programme
    prog = {r['fy']: r for r in comp['programme']['rows']}
    for y, r in prog.items():
        if abs(r['gen_ed_fte'] + r['sped_fte'] + r['career_tech_fte'] + r['el_fte']
               - r['total_fte']) > 0.15 or abs(r['total_fte'] - dist[y]['fte']) > 0.05:
            fail('the programme split no longer sums to the teacher total, %s' % y)
    sp = PA['sped_staffing']
    sprow = {r['fy']: r for r in sp['rows']}
    stp = {r['fy']: r['fte'] for r in ST['paras']}
    for y, r in sprow.items():
        if stp.get(y) != r['special_education']:
            fail('the two payloads disagree on special education paraprofessional FTE, %s' % y)
        if abs(r['all_programmes'] - radar[y]['para_fte']) > 0.05:
            fail('the all-programmes count is no longer the comparison sheet’s, %s' % y)
    a0, a1 = sp['all_programmes'], sp['special_education']
    im = sp['implied']
    sy0, sy1 = sp['first_fy'], sp['last_fy']
    out['staff-by-programme'] = TP.page(
        'staff-by-programme',
        'Paraprofessional FTE coded to special education fell from %s to %s while the all-programmes '
        'count rose.' % ('%.1f' % a1['first'], '%.1f' % a1['last']),
        [f('tsp-first', FTE(prog[first]['sped_fte']), 'teacher FTE coded special education, %s'
           % C.fy(first), 'published', {'y': F(first)}),
         f('tsp-last', FTE(prog[last]['sped_fte']), 'the same, %s' % C.fy(last), 'published',
           {'y': F(last)}),
         f('tge-first', FTE(prog[first]['gen_ed_fte']), 'teacher FTE coded general education, %s'
           % C.fy(first), 'published', {'y': F(first)}),
         f('tge-last', FTE(prog[last]['gen_ed_fte']), 'the same, %s' % C.fy(last), 'published',
           {'y': F(last)}),
         f('psp-first', FTE(a1['first']), 'paraprofessional FTE, special education, %s' % C.fy(sy0),
           'published', {'y': F(sy0)}),
         f('psp-last', FTE(a1['last']), 'the same file, %s' % C.fy(sy1), 'published', {'y': F(sy1)}),
         f('pall-first', FTE(a0['first']), 'paraprofessional FTE, all programmes, %s' % C.fy(sy0),
           'published', {'y': F(sy0)}),
         f('pall-last', FTE(a0['last']), 'the other file, %s' % C.fy(sy1), 'published', {'y': F(sy1)}),
         f('imp-first', FTE(im['first']), 'difference between the two files, %s (ours)' % C.fy(sy0),
           'estimate', {'y': F(sy0)}),
         f('imp-last', FTE(im['last']), 'the same difference, %s (ours)' % C.fy(sy1), 'estimate',
           {'y': F(sy1)})],
        [con('Teacher FTE coded to special education fell from %s in %s to %s in %s.'
             % ('%.1f' % prog[first]['sped_fte'], C.fy(first), '%.1f' % prog[last]['sped_fte'],
                C.fy(last)), ['tsp-first', 'tsp-last', 'tge-first', 'tge-last'],
             {'a': FTE(prog[first]['sped_fte']), 'y': F(first), 'b': FTE(prog[last]['sped_fte']),
              'z': F(last)},
             notes=[step('Whether the same teachers were reported under another code is not '
                         'published.', 'gap', closes=EPIMS)]),
         con('Paraprofessional FTE coded to special education fell from %s in %s to %s in %s.'
             % ('%.1f' % a1['first'], C.fy(sy0), '%.1f' % a1['last'], C.fy(sy1)),
             ['psp-first', 'psp-last'],
             {'a': FTE(a1['first']), 'y': F(sy0), 'b': FTE(a1['last']), 'z': F(sy1)}),
         con('Over the same years the all-programmes count rose from %s to %s.'
             % ('%.1f' % a0['first'], '%.1f' % a0['last']), ['pall-first', 'pall-last'],
             {'a': FTE(a0['first']), 'b': FTE(a0['last'])},
             notes=[step('A reassignment, a recoding and a change in what one file counts all fit. '
                         'The two files have different definitions.', 'hypothesis')]),
         con('The difference between the files went from %s to %s; nothing says it is general '
             'education.' % ('%.1f' % im['first'], '%.1f' % im['last']), ['imp-first', 'imp-last'],
             {'a': FTE(im['first']), 'b': FTE(im['last'])},
             notes=[step('Nothing published says the special education file’s staff sit inside '
                         'the all-programmes count.', 'gap', closes=EPIMS)])],
        chart=TP.series('Paraprofessional FTE, two state files', [C.fy(y) for y in sorted(sprow)], [
            TP.track('All programmes, comparison sheet',
                     [sprow[y]['all_programmes'] for y in sorted(sprow)]),
            TP.track('Special education, program file',
                     [sprow[y]['special_education'] for y in sorted(sprow)])], FTE_UNIT,
            note='Two DESE files with two definitions. Nothing published says one sits inside '
                 'the other.'),
        table=dict(caption='Staff by programme, as the state codes them', views=[
            dict(key='paras', label='Paraprofessionals', total_col=-1, kinds=['ledger', 'ledger', 'stated'],
                 columns=['All programmes', 'Special education', 'Difference (ours)'],
                 rows=[dict(label=C.fy(y), cells=['%.1f' % sprow[y]['all_programmes'],
                                                  '%.1f' % sprow[y]['special_education'],
                                                  '%.1f' % sprow[y]['implied']])
                       for y in sorted(sprow, reverse=True)],
                 note='Two DESE files with two definitions: the comparison sheet, and special '
                      'education program characteristics.'),
            dict(key='teachers', label='Teachers', total_col=2, kinds=['ledger'] * 3,
                 columns=['General education', 'Special education', 'All teachers'],
                 rows=[dict(label=C.fy(y), cells=['%.1f' % prog[y]['gen_ed_fte'],
                                                  '%.1f' % prog[y]['sped_fte'],
                                                  '%.1f' % prog[y]['total_fte']])
                       for y in sorted(prog, reverse=True)],
                 note='DESE’s teachers by program area. Career and technical and English learner '
                      'FTE, small in every year, are in the total.')]),
        sources=S('program-area', 'radar', 'sped-program'),
        finding_figures={'a': FTE(a1['first']), 'b': FTE(a1['last'])})

    # ================================================================ people and posts
    wf = {(r['fy'], r['job_class']): r for r in hc['rows']}
    classes = hc['job_classes']
    people = sum(wf[(hy, c)]['educators_headcount'] for c in classes)
    other = [c for c in classes if c not in ('Teacher', 'Paraprofessional')]
    hy0 = hc['first_fy']
    out['headcount-and-fte'] = TP.page(
        'headcount-and-fte',
        'The state counted %s teachers in %s, holding %s full-time equivalent posts between them.'
        % (C.num(vs[hy]['teacher_headcount']), C.fy(hy), '%.1f' % vs[hy]['teacher_fte']),
        [f('h-t', N(vs[hy]['teacher_headcount'], 'people'), 'teachers as people, %s' % C.fy(hy),
           'published', {'y': F(hy)}),
         f('h-tf', FTE(vs[hy]['teacher_fte']), 'teacher FTE, %s' % C.fy(hy), 'published', {'y': F(hy)}),
         f('h-t0', N(vs[hy0]['teacher_headcount'], 'people'), 'teachers as people, %s' % C.fy(hy0),
           'published', {'y': F(hy0)}),
         f('h-tf0', FTE(vs[hy0]['teacher_fte']), 'teacher FTE, %s' % C.fy(hy0), 'published',
           {'y': F(hy0)}),
         f('h-p', N(vs[hy]['para_headcount'], 'people'), 'paraprofessionals as people, %s' % C.fy(hy),
           'published', {'y': F(hy)}),
         f('h-pf', FTE(vs[hy]['para_fte']), 'paraprofessional FTE, %s' % C.fy(hy), 'published',
           {'y': F(hy)})]
        + [f('h-%d' % i, N(wf[(hy, c)]['educators_headcount'], 'people'), '%s, people, %s'
             % ({'Administrator': 'administrators', 'Other - Licensed': '“other, licensed” staff',
                 'Other - Non-Licensed': '“other, non-licensed” staff'}[c], C.fy(hy)),
             'published', {'y': F(hy)})
           for i, c in enumerate(other)]
        + [f('h-all', N(people, 'people'), 'people in all %s job classes, %s'
             % (C.num(len(classes)), C.fy(hy)), 'published', {'n': N(len(classes)), 'y': F(hy)}),
           f('fte-gap', None, 'FTE for anyone but teachers and paraprofessionals', 'gap',
             closes=EPIMS)],
        [con('The state counted %s teachers in %s holding %s FTE; in %s, %s holding %s.'
             % (C.num(vs[hy]['teacher_headcount']), C.fy(hy), '%.1f' % vs[hy]['teacher_fte'],
                C.fy(hy0), C.num(vs[hy0]['teacher_headcount']), '%.1f' % vs[hy0]['teacher_fte']),
             ['h-t', 'h-tf', 'h-t0', 'h-tf0'],
             {'a': N(vs[hy]['teacher_headcount']), 'y': F(hy), 'b': FTE(vs[hy]['teacher_fte']),
              'z': F(hy0), 'c': N(vs[hy0]['teacher_headcount']), 'd': FTE(vs[hy0]['teacher_fte'])},
             notes=[step('Together they give an average share of a post for the whole class and '
                         'nothing about any one person’s hours.', 'gap', closes=EPIMS)]),
         con('Paraprofessionals were %s people and %s FTE that year.'
             % (C.num(vs[hy]['para_headcount']), '%.1f' % vs[hy]['para_fte']), ['h-p', 'h-pf'],
             {'a': N(vs[hy]['para_headcount']), 'b': FTE(vs[hy]['para_fte'])}),
         con('The file counts %s people in %s job classes and publishes no FTE for three of them.'
             % (C.num(people), C.num(len(classes))),
             ['h-all', 'fte-gap'] + ['h-%d' % i for i in range(len(other))],
             {'a': N(people), 'n': N(len(classes))},
             notes=[step('The file does not list which jobs its two “Other” classes hold.', 'gap',
                         closes='DESE’s data dictionary for its educator workforce file')])],
        chart=TP.series('People and FTE, the state’s files', ['Teachers', 'Paraprofessionals'], [
            TP.track('People', [vs[hy]['teacher_headcount'], vs[hy]['para_headcount']]),
            TP.track('FTE', [vs[hy]['teacher_fte'], vs[hy]['para_fte']])], 'count', kind='bar',
            note='%s: people from DESE’s workforce file, FTE from its comparison sheet.' % C.fy(hy),
            note_figures={'y': F(hy)}),
        table=dict(caption='People by job class, the state’s workforce file', views=[dict(
            key='classes', label='Headcount', total_col=-1, kinds=['ledger'] * 3,
            columns=[C.fy(y) for y in range(hy0, hy + 1)],
            rows=[dict(label=c, cells=[C.num(wf[(y, c)]['educators_headcount'])
                                       for y in range(hy0, hy + 1)]) for c in classes],
            note='People, counted once each. The file prints every class beside a total row; '
                 'reading both doubles every figure.')]),
        sources=S('retention', 'radar'),
        finding_figures={'a': N(vs[hy]['teacher_headcount']), 'y': F(hy),
                         'b': FTE(vs[hy]['teacher_fte'])})

    # ================================================================ staff retention
    # THE RATE IS THE STATE'S, NOT OURS. Retained people over last year's headcount reproduces
    # it for teachers and paraprofessionals but NOT for every class (administrators, FY2022:
    # 13 of 14 against a printed 81.3%), so no definition is asserted or stated here.
    for c in ('Paraprofessional', 'Teacher'):
        for y in range(hc['first_fy'] + 1, hc['last_fy'] + 1):
            r, prev = wf[(y, c)], wf[(y - 1, c)]
            if abs(r['retained_headcount'] / prev['educators_headcount'] - r['retained_pct']) > 0.0015:
                fail('the %s retention rate has moved, %s; re-read the file' % (c, y))
    ret = lambda c, y: 100 * wf[(y, c)]['retained_pct']
    ys = list(range(hy0, hy + 1))
    para_hires = [wf[(y, 'Paraprofessional')]['hires_headcount'] for y in ys]
    hired = [(y, h) for y, h in zip(ys, para_hires) if h is not None]
    out['staff-retention'] = TP.page(
        'staff-retention',
        'The state reports %s of paraprofessionals retained in %s and %s in %s, against %s in %s.'
        % (C.pct(ret('Paraprofessional', ys[1])), C.fy(ys[1]), C.pct(ret('Paraprofessional', ys[2])),
           C.fy(ys[2]), C.pct(ret('Paraprofessional', ys[0])), C.fy(ys[0])),
        [f('rp-%d' % y, P(ret('Paraprofessional', y)), 'paraprofessionals retained, %s' % C.fy(y),
           'published', {'y': F(y)}) for y in ys]
        + [f('rt-%d' % y, P(ret('Teacher', y)), 'teachers retained, %s' % C.fy(y), 'published',
             {'y': F(y)}) for y in ys]
        + [f('hp-%d' % y, N(h, 'people'), 'paraprofessionals hired, %s' % C.fy(y), 'published',
             {'y': F(y)}) for y, h in hired]
        + [f('why-gap', None, 'why people left: resigned, moved, or a post ended', 'gap',
             closes='the district’s separation records by job class and reason, names removed')],
        [con('The state reports %s of paraprofessionals retained in %s and %s in %s.'
             % (C.pct(ret('Paraprofessional', ys[1])), C.fy(ys[1]),
                C.pct(ret('Paraprofessional', ys[2])), C.fy(ys[2])),
             ['rp-%d' % y for y in ys] + ['hp-%d' % y for y, _ in hired],
             {'a': P(ret('Paraprofessional', ys[1])), 'y': F(ys[1]),
              'b': P(ret('Paraprofessional', ys[2])), 'z': F(ys[2])}),
         con('Teachers were retained at %s, %s and %s over the same three years.'
             % tuple(C.pct(ret('Teacher', y)) for y in ys), ['rt-%d' % y for y in ys],
             {'a%d' % i: P(ret('Teacher', y)) for i, y in enumerate(ys)}),
         con('The state’s file covers only %s to %s, and says nothing about why anybody left.'
             % (C.fy(ys[0]), C.fy(ys[-1])), ['why-gap'], {'a': F(ys[0]), 'b': F(ys[-1])})],
        chart=TP.series('Share retained from the year before', [C.fy(y) for y in ys], [
            TP.track('Paraprofessionals', [ret('Paraprofessional', y) for y in ys]),
            TP.track('Teachers', [ret('Teacher', y) for y in ys])], '%', kind='bar',
            note='DESE’s own rate, the only years its file covers.'),
        table=dict(caption='Share retained from the year before, by job class', views=[dict(
            key='retained', label='The state’s rate', total_col=-1, kinds=['ledger'] * len(ys),
            columns=[C.fy(y) for y in ys],
            rows=[dict(label=c, cells=[C.pct(ret(c, y)) for y in ys]) for c in classes],
            note='The share DESE publishes for each class. Its file does not state the '
                 'denominator, and for one class it does not follow from the headcounts.')]),
        said=[said(WW, 'para-transfers')],
        sources=S('retention'),
        finding_figures={'a': P(ret('Paraprofessional', ys[1])), 'y': F(ys[1]),
                         'b': P(ret('Paraprofessional', ys[2])), 'z': F(ys[2]),
                         'c': P(ret('Paraprofessional', ys[0])), 'x': F(ys[0])})

    # ================================================================ support staff
    ro = WW['roster']
    r0, r1 = ro['first_fy'], ro['last_fy']
    sup = [('counselor', 'counsellors'), ('psychologist', 'psychologists'),
           ('social_worker', 'social workers'), ('nurse', 'nurses'),
           ('speech_therapist', 'speech therapists')]
    for k, _ in sup:
        if k not in roles:
            fail('the roster no longer classifies %s' % k)
    get = lambda k, y: roles[k].get(y, 0)
    sw_first = min(y for y, n in roles['social_worker'].items() if n)
    olic = wf[(hy, 'Other - Licensed')]['educators_headcount']
    out['school-support-staff'] = TP.page(
        'school-support-staff',
        'The town printed %s counsellors, %s psychologists and %s social workers on its %s school '
        'rosters.' % (C.num(get('counselor', r1)), C.num(get('psychologist', r1)),
                      C.num(get('social_worker', r1)), C.fy(r1)),
        [f('s-%s' % k.replace('_', '-'), N(get(k, r1), 'names'), '%s printed, %s (ours)'
           % (lab, C.fy(r1)), 'estimate', {'y': F(r1)}) for k, lab in sup]
        + [f('s0-%s' % k.replace('_', '-'), N(get(k, r0), 'names'), '%s printed, %s (ours)'
             % (lab, C.fy(r0)), 'estimate', {'y': F(r0)}) for k, lab in sup[:3]]
        + [f('s-olic', N(olic, 'people'), 'state headcount, “other licensed” staff, %s' % C.fy(hy),
             'published', {'y': F(hy)}),
           f('case-gap', None, 'caseloads, and FTE, for any of these posts', 'gap',
             closes='the district’s per-building social worker and counsellor caseloads, with FTE '
                    'and funding source')],
        [con('The town printed %s counsellors, %s psychologists and %s social workers in %s.'
             % (C.num(get('counselor', r1)), C.num(get('psychologist', r1)),
                C.num(get('social_worker', r1)), C.fy(r1)),
             ['s-counselor', 's-psychologist', 's-social-worker', 's-nurse', 's-speech-therapist'],
             {'a': N(get('counselor', r1)), 'b': N(get('psychologist', r1)),
              'c': N(get('social_worker', r1)), 'y': F(r1)}),
         con('In %s it printed %s counsellors and %s psychologist; social workers first appear in %s.'
             % (C.fy(r0), C.num(get('counselor', r0)), C.num(get('psychologist', r0)),
                C.fy(sw_first)), ['s0-counselor', 's0-psychologist', 's0-social-worker'],
             {'y': F(r0), 'a': N(get('counselor', r0)), 'b': N(get('psychologist', r0)),
              'z': F(sw_first)},
             notes=[step('Which titles are which role is our reading of the printed page, and '
                         'what each school chose to print changed year to year.', 'gap',
                         closes=DATED_ROSTER)]),
         con('The state publishes no FTE for any of these posts, and names no job class for them.',
             ['s-olic', 'case-gap'],
             notes=[step('The district holds per-building social worker caseloads; they are not '
                         'published.', 'gap',
                         closes='the caseload breakdown the district gave the School Committee')])],
        chart=TP.series('Support staff names printed', [C.fy(y) for y in range(r0, r1 + 1)],
                        [TP.track(lab.capitalize(), [get(k, y) for y in range(r0, r1 + 1)], 'estimate')
                         for k, lab in sup[:4]], 'names',
                        note='Names on the annual town report rosters, classified by printed title '
                             '(our reading). A name is not a post.'),
        table=dict(caption='Support staff names printed, by year (our classification)', views=[dict(
            key='roles', label='Annual town report rosters', total_col=-1, kinds=['stated'] * 4,
            columns=['Counsellors', 'Psychologists', 'Social workers', 'Nurses'],
            rows=[dict(label=C.fy(y), cells=[C.num(get(k, y)) for k, _ in sup[:4]])
                  for y in range(r1, r0 - 1, -1)],
            note='Names, not posts: a part-time post and a full-time one are one name each.')]),
        said=[said(WW, 'social-worker-caseloads'), said(WW, 'esser-unwound')],
        sources=S('roster-counts', 'roster-provenance', 'retention'),
        finding_figures={'a': N(get('counselor', r1)), 'b': N(get('psychologist', r1)),
                         'c': N(get('social_worker', r1)), 'y': F(r1)})

    # ================================================================ printed school rosters
    years = {r['fy']: r for r in ro['years']}
    if sum(r['names'] for r in ro['years']) != ro['entries_in_panel']:
        fail('the roster years no longer sum to the panel')
    peak = max(years.values(), key=lambda r: r['names'])
    co = sum(1 for r in ro['years'] if r['central_office_printed'])
    bys = {r['school']: r['names'] for r in ro['by_school']['rows']}
    if ro['by_school']['fy'] != r1 or sum(bys.values()) != years[r1]['names']:
        fail('the latest roster no longer sums by school')
    cc = WW['board']['cross_check']
    uns = 100 * ro['unclassified_share']
    out['printed-school-rosters'] = TP.page(
        'printed-school-rosters',
        'The town printed %s names on its school rosters in %s, against %s in %s.'
        % (C.num(years[r1]['names']), C.fy(r1), C.num(years[r0]['names']), C.fy(r0)),
        [f('n-last', N(years[r1]['names'], 'names'), 'names on the school rosters, %s' % C.fy(r1),
           'published', {'y': F(r1)}),
         f('n-first', N(years[r0]['names'], 'names'), 'names on the school rosters, %s' % C.fy(r0),
           'published', {'y': F(r0)}),
         f('n-peak', N(peak['names'], 'names'), 'names, %s, the most printed' % C.fy(peak['fy']),
           'published', {'y': F(peak['fy'])})]
        + [f('n-%s' % k, N(bys[k], 'names'), 'names, %s, %s' % (lab, C.fy(r1)), 'published', {'y': F(r1)})
           for k, lab in (('primary', 'Primary'), ('turkey-hill', 'Turkey Hill'),
                          ('middle', 'Middle'), ('high', 'High'))]
        + [f('co', N(co, 'years'), 'of %s with a central office roster (left out here)'
             % C.num(len(years)), 'published', {'n': N(len(years))}),
           f('short', N(cc['flagged'], 'school-years'), 'of %s with fewer teaching names than '
             'teaching FTE' % C.num(cc['compared']), 'published', {'n': N(cc['compared'])}),
           f('uns', P(uns), 'of printed titles we could not classify', 'estimate'),
           f('level-gap', None, 'how many posts a roster’s names fill', 'gap', closes=POSITIONS)],
        [con('The town printed %s names in %s and %s in %s, most in %s.'
             % (C.num(years[r1]['names']), C.fy(r1), C.num(years[r0]['names']), C.fy(r0),
                C.fy(peak['fy'])),
             ['n-last', 'n-first', 'n-peak', 'n-primary', 'n-turkey-hill', 'n-middle', 'n-high', 'co'],
             {'a': N(years[r1]['names']), 'y': F(r1), 'b': N(years[r0]['names']), 'z': F(r0),
              'p': F(peak['fy'])},
             notes=[step('A roster carries no date, so which school year it describes is not '
                         'established.', 'gap', closes=DATED_ROSTER)]),
         con('In %s of %s school-years a school printed fewer teaching names than the state counts '
             'FTE.' % (C.num(cc['flagged']), C.num(cc['compared'])), ['short', 'uns'],
             {'a': N(cc['flagged']), 'n': N(cc['compared'])},
             notes=[step('Our reading of a scanned page, what the town chose to print, and staff '
                         'shared between two schools all fit. Nothing here separates them.',
                         'hypothesis')]),
         con('A printed name has no FTE and no fund, so a count of names is not a staffing level.',
             ['n-last', 'level-gap'])],
        chart=TP.series('Names printed on the school rosters', [C.fy(y) for y in range(r0, r1 + 1)],
                        [TP.track('Names, every school roster', [years[y]['names']
                                                                 for y in range(r0, r1 + 1)])],
                        'names', kind='bar',
                        note='The annual town reports, central office left out. A name has no FTE '
                             'and no fund.'),
        table=dict(caption='Names printed on the school rosters, by year', views=[dict(
            key='years', label='Annual town reports', total_col=0, kinds=['stated'] * 2,
            columns=['Names', 'Schools printed'],
            rows=[dict(label=C.fy(y), cells=[C.num(years[y]['names']),
                                             C.num(len(years[y]['schools']))])
                  for y in range(r1, r0 - 1, -1)],
            note='One row per printed name, per school. A central office roster, printed in some '
                 'years and not others, is left out so its comings and goings are not read as '
                 'staffing.')]),
        sources=S('roster-counts', 'roster-provenance', 'teacher-data'),
        finding_figures={'a': N(years[r1]['names']), 'y': F(r1), 'b': N(years[r0]['names']),
                         'z': F(r0)})

    # ================================================================ district staff directory
    def per_fetch(d):
        rows = [r for r in rows_dir if r['fetched'] == d]
        ru = [r for r in rows if r['listing_kind'] == 'roll-up']
        sl = [r for r in rows if r['listing_kind'] == 'school']
        seen = collections.defaultdict(set)
        for r in sl:
            seen[r['person_key']].add(r['listing'])
        return dict(rollup=len(ru), people=len({r['person_key'] for r in ru}),
                    listings=collections.Counter(r['listing'] for r in sl),
                    rows=len(sl), multi=sum(1 for v in seen.values() if len(v) > 1))
    pf_ = {d: per_fetch(d) for d in fetches}
    L, E = pf_[fetches[-1]], pf_[fetches[0]]
    if L['people'] != L['rollup']:
        fail('the roll-up no longer has one row per person')
    dfirst = day(fetches[0])
    lnames = sorted(L['listings'])
    out['district-staff-directory'] = TP.page(
        'district-staff-directory',
        'The district’s staff directory listed %s people on %s; it carries no FTE and no fund.'
        % (C.num(L['rollup']), dlast),
        [f('d-last', N(L['rollup'], 'people'), 'on the district-wide list, %s' % dlast, 'published',
           allow=(dlast,)),
         f('d-first', N(E['rollup'], 'people'), 'on the same list, %s' % dfirst, 'published',
           allow=(dfirst,)),
         f('d-rows', N(L['rows'], 'rows'), 'on the %s separate listings, %s'
           % (C.num(len(lnames)), dlast), 'published', {'n': N(len(lnames))}, allow=(dlast,)),
         f('d-multi', N(L['multi'], 'people'), 'on two or more of those listings', 'published'),
         f('d-ss', N(ss_only, 'people'), 'titled only “Special Services”', 'published'),
         f('d-gap', None, 'FTE, fund and start date for anyone listed', 'gap', closes=POSITIONS)],
        [con('The district-wide list named %s people on %s and %s on %s.'
             % (C.num(L['rollup']), dlast, C.num(E['rollup']), dfirst), ['d-last', 'd-first'],
             {'a': N(L['rollup']), 'b': N(E['rollup'])}, allow=(dlast, dfirst)),
         con('Its %s separate listings print %s rows; %s people appear on two or more.'
             % (C.num(len(lnames)), C.num(L['rows']), C.num(L['multi'])), ['d-rows', 'd-multi'],
             {'n': N(len(lnames)), 'a': N(L['rows']), 'b': N(L['multi'])},
             notes=[step('A person on two schools’ lists fits a post shared between buildings; the '
                         'directory does not say how the week is split.', 'hypothesis')]),
         con('It is a contact list: %s people are titled only “Special Services”, and none has an '
             'FTE.' % C.num(ss_only), ['d-ss', 'd-gap'], {'a': N(ss_only)})],
        chart=TP.ranking('Directory rows by listing', [(n, L['listings'][n]) for n in lnames],
                         'rows', note='The district’s own sheets, fetched %s. A person on two '
                                      'listings has two rows.' % dlast, note_allow=(dlast,)),
        table=dict(caption='Rows on each listing of the district directory', views=[dict(
            key='listings', label='By date fetched', total_col=-1, kinds=['ledger'] * len(fetches),
            columns=[day(d) for d in fetches],
            rows=[dict(label=n, cells=[C.num(pf_[d]['listings'][n]) for d in fetches])
                  for n in lnames]
            + [dict(label='District-wide list', cells=[C.num(pf_[d]['rollup']) for d in fetches])],
            note='The district’s own sheets, read as printed. A person on two school listings has '
                 'two rows. Names are not published here.')]),
        sources=S('directory', 'directory-rows'),
        finding_figures={'a': N(L['rollup'])}, finding_allow=(dlast,))

    # ================================================================ the hub
    ros_hy = years[hy]['names']
    h = {}
    h['h-t-last'] = f('h-t-last', FTE(dist[last]['fte']), 'teacher FTE, %s' % C.fy(last), 'published',
                      {'y': F(last)})
    h['h-w-charted'] = f('h-w-charted', CHG(wc['change']), 'teacher FTE change, %s to %s'
                         % (C.fy(wc['first_fy']), C.fy(wc['last_fy'])), 'published',
                         {'a': F(wc['first_fy']), 'b': F(wc['last_fy'])})
    h['h-w-recent'] = f('h-w-recent', CHG(wr['change']), 'teacher FTE change, %s to %s'
                        % (C.fy(wr['first_fy']), C.fy(wr['last_fy'])), 'published',
                        {'a': F(wr['first_fy']), 'b': F(wr['last_fy'])})
    h['h-ratio'] = f('h-ratio', R2(rt['value']), 'teacher FTE per hundred pupils, %s' % C.fy(rl),
                     'published', {'y': F(rl)})
    h['h-pairs'] = f('h-pairs', N(fell, 'pairs of years'), 'of %s year pairs end lower'
                     % C.num(len(pairs)), 'published', {'n': N(len(pairs))})
    h['h-p-last'] = f('h-p-last', FTE(pl['para_fte']), 'paraprofessional FTE, %s' % C.fy(rl),
                      'published', {'y': F(rl)})
    h['h-p-low'] = f('h-p-low', FTE(trough['para_fte']), 'paraprofessional FTE, %s'
                     % C.fy(trough['fy']), 'published', {'y': F(trough['fy'])})
    h['h-p-sped'] = f('h-p-sped', FTE(a1['last']), 'special education paraprofessional FTE, %s'
                      % C.fy(sy1), 'published', {'y': F(sy1)})
    h['h-ret'] = f('h-ret', P(ret('Paraprofessional', ys[1])), 'paraprofessionals retained, %s'
                   % C.fy(ys[1]), 'published', {'y': F(ys[1])})
    h['h-dese'] = f('h-dese', N(people, 'people'), 'people in the state’s headcount, %s'
                    % C.fy(hy), 'published', {'y': F(hy)})
    h['h-roster'] = f('h-roster', N(ros_hy, 'names'), 'names on the town’s school rosters, %s'
                      % C.fy(hy), 'published', {'y': F(hy)})
    h['h-dir'] = f('h-dir', N(L['rollup'], 'people'), 'on the district’s directory, %s' % dlast,
                   'published', allow=(dlast,))
    h['h-filled'] = f('h-filled', None, 'which posts are filled, and which fund pays each', 'gap',
                      closes=POSITIONS)
    hub_ladder = LD.ladder([
        LD.tier('Teachers', [h['h-t-last'], h['h-w-charted'], h['h-w-recent'], h['h-pairs'],
                             h['h-ratio']]),
        LD.tier('Paraprofessionals', [h['h-p-last'], h['h-p-low'], h['h-p-sped'], h['h-ret']]),
        LD.tier('People, counted three ways', [h['h-dese'], h['h-roster'], h['h-dir'], h['h-filled']]),
    ], [
        LD.conclusion('Teacher FTE reads %s from %s to %s and %s from %s to %s.'
                      % ('%+.1f' % wc['change'], C.fy(wc['first_fy']), C.fy(wc['last_fy']),
                         '%+.1f' % wr['change'], C.fy(wr['first_fy']), C.fy(wr['last_fy'])),
                      ['h-w-charted', 'h-w-recent', 'h-t-last'],
                      {'a': CHG(wc['change']), 'b': F(wc['first_fy']), 'c': F(wc['last_fy']),
                       'd': CHG(wr['change']), 'e': F(wr['first_fy']), 'g': F(wr['last_fy'])}),
        LD.conclusion('In %s of %s pairs of published years the count ends lower than it starts.'
                      % (C.num(fell), C.num(len(pairs))), ['h-pairs', 'h-ratio'],
                      {'p': N(fell), 'n': N(len(pairs))}),
        LD.conclusion('Paraprofessional FTE rose from %s in %s to %s in %s; another file codes %s '
                      'to special education.' % ('%.1f' % trough['para_fte'], C.fy(trough['fy']),
                                                 '%.1f' % pl['para_fte'], C.fy(rl), '%.1f' % a1['last']),
                      ['h-p-low', 'h-p-last', 'h-p-sped'],
                      {'a': FTE(trough['para_fte']), 'y': F(trough['fy']), 'b': FTE(pl['para_fte']),
                       'z': F(rl), 'c': FTE(a1['last'])}),
        LD.conclusion('The state reports %s of paraprofessionals retained in %s.'
                      % (C.pct(ret('Paraprofessional', ys[1])), C.fy(ys[1])), ['h-ret'],
                      {'a': P(ret('Paraprofessional', ys[1])), 'y': F(ys[1])}),
        LD.conclusion('For %s the state counts %s people; the town printed %s names. They count '
                      'different things.' % (C.fy(hy), C.num(people), C.num(ros_hy)),
                      ['h-dese', 'h-roster', 'h-dir'],
                      {'y': F(hy), 'a': N(people), 'b': N(ros_hy)}),
        LD.conclusion('Which posts are filled, and which fund pays for each, is not published.',
                      ['h-filled']),
    ])
    out['school-staffing'] = TP.hub(
        'school-staffing',
        'The state counted %s teacher FTE in %s; whether that is a rise or a fall depends on the '
        'year it is measured from. Paraprofessional FTE was %s in %s, the most per pupil on '
        'the state’s sheet. Nothing published says which posts were filled.'
        % ('%.1f' % dist[last]['fte'], C.fy(last), '%.1f' % pl['para_fte'], C.fy(rl)),
        hub_ladder,
        chart=(lambda ys: TP.series('Teachers and paraprofessionals, state FTE', [C.fy(y) for y in ys], [
            TP.track('Teachers, DESE teacher file', [dist[y]['fte'] if y in dist else None
                                                     for y in ys]),
            TP.track('Paraprofessionals, comparison sheet',
                     [radar[y]['para_fte'] if y in radar else None for y in ys])], FTE_UNIT,
            note='Assignments, not people or filled posts; neither file says which fund pays.'))(
            span(dist, radar)),
        answer_figures={'a': FTE(dist[last]['fte']), 'y': F(last), 'c': FTE(pl['para_fte']),
                        'x': F(rl)})

    if sorted(k for k in out if k != 'school-staffing') != sorted(MINE):
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
        print('school staffing topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
