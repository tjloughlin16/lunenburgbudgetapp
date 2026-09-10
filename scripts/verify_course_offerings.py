#!/usr/bin/env python3
"""Every figure on /what-courses-actually-ran, recomputed by a SECOND route.

    python3 scripts/verify_course_offerings.py

THE GENERATOR AGREES WITH ITSELF BY CONSTRUCTION. That is what a `--check` proves and it
is not enough: `build_course_offerings.py` reads `dese_class_size` out of the database,
and if the LOAD dropped a row, coerced a column or collided a primary key, the generator
and its own check would agree perfectly about a wrong number.

So this reads the CSV the database was built from, aggregates it in Python with pivots
rather than SQL, and asserts the published payload against that. Three independent things
follow from taking the other road:

  * the DB LOAD is checked -- 3,160 rows in, 3,160 rows out, every figure equal;
  * the ROLLUPS are recomputed rather than trusted, both of them, on all 79 cells;
  * the CURRICULUM workbook is re-read BY COLUMN POSITION rather than by header name,
    so a header rename that the generator's `need` check would catch and a header
    REORDER that it would not are both covered.

AND IT ASSERTS WHAT THE PAGE DERIVES AT RENDER TIME. Several figures a reader sees are
computed in the `.tsx` from the payload and exist in no generator output: the net section
change, the count of subjects that gained and lost, the share of the high school's
sections in each subject, the seats-per-student series. Nothing else on this site would
notice one of those going wrong, because nothing else computes them.

AND IT ASSERTS THE STRUCTURE THE ARGUMENT RESTS ON, not only its figures (rule 13):

  * that the grades-9-12 years and the analysis window are the same span throughout,
    read off DESE's enrolment file rather than off the school's name;
  * that no CH74 row is ever summed into a subject total;
  * that the two school-years the page refuses to trend are the only ones above the
    implausibility bound, so the exclusion is a rule and not a taste;
  * that every conclusion's registered value is the value this second route computes.
"""
import collections
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

CSV = os.path.join(ROOT, 'sources', 'data', 'dese-class-size.csv')
TEACHER = os.path.join(ROOT, 'sources', 'data', 'dese-teacher-subject.csv')
GRADE_SUBJ = os.path.join(ROOT, 'sources', 'data', 'dese-teacher-grade-subject.csv')
ENROL = os.path.join(ROOT, 'sources', 'data', 'dese-enrollment.csv')
CURRICULUM = os.path.join(ROOT, 'sources', 'state-dese', 'dese-curriculum-lunenburg.xlsx')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'course-offerings.json')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')

HIGH = 'Lunenburg High'
MIDDLE = 'Lunenburg Middle School'
DISTRICT = 'Lunenburg'
ROLLUP = 'All'
CH74 = 'CH74 - '
LEA = '01620000'

FAILS = []
CHECKS = [0]


def ok(label, got, want, tol=0.0):
    CHECKS[0] += 1
    if isinstance(got, float) or isinstance(want, float):
        good = abs(float(got) - float(want)) <= tol
    else:
        good = got == want
    if not good:
        FAILS.append('%s: payload says %r, the CSV gives %r' % (label, want, got))


def load():
    rows = list(csv.DictReader(open(CSV, encoding='utf-8')))
    if not rows:
        FAILS.append('%s is empty' % CSV)
        return []
    for r in rows:
        r['sy'] = int(r['sy'])
        for k in ('tot_clss_cnt', 'avg_clss_cnt', 'tot_stu_cnt'):
            r[k] = float(r[k] or 0)
    return rows


def pivot(rows):
    """(sy, org_name, subj) -> row. A pivot rather than a filter, so a duplicated key --
    which is what a primary-key collision in the load would look like from this side --
    is caught here rather than silently winning."""
    out = {}
    for r in rows:
        key = (r['sy'], r['org_name'], r['subj'])
        if key in out:
            FAILS.append('the CSV carries %r twice' % (key,))
        out[key] = r
    return out


def main():
    if not os.path.exists(PAYLOAD):
        print('MISSING %s — run scripts/build_course_offerings.py'
              % os.path.relpath(PAYLOAD, ROOT))
        return 1
    d = json.load(open(PAYLOAD, encoding='utf-8'))
    rows = load()
    if not rows:
        print('\n'.join(FAILS))
        return 1
    P = pivot(rows)

    # ---- the load itself -------------------------------------------------------
    ok('rows in the CSV', len(rows), 3160)
    ok('org-year cells', len({(r['sy'], r['org_code']) for r in rows}),
       d['rollups']['cells'])
    ok('CH74 rows', sum(1 for r in rows if r['subj'].startswith(CH74)),
       d['rollups']['ch74_rows'])
    hot = [r for r in rows if r['subj'].startswith(CH74)
           and (r['tot_clss_cnt'] or r['tot_stu_cnt'])]
    CHECKS[0] += 1
    if hot:
        FAILS.append('%d Chapter 74 rows are not zero; every subject total on the page '
                     'excludes them on the strength of their being zero' % len(hot))

    # ---- both rollups, recomputed ----------------------------------------------
    cells = collections.defaultdict(dict)
    for r in rows:
        cells[(r['sy'], r['org_name'])][r['subj']] = r
    for key, by_subj in cells.items():
        CHECKS[0] += 1
        total = by_subj.get(ROLLUP)
        if total is None:
            FAILS.append('%r has no All row' % (key,))
            continue
        parts = sum(v['tot_clss_cnt'] for s, v in by_subj.items()
                    if s != ROLLUP and not s.startswith(CH74))
        if abs(parts - total['tot_clss_cnt']) > 0.001:
            FAILS.append('%r: All=%g but the subjects sum to %g'
                         % (key, total['tot_clss_cnt'], parts))
    resid = []
    for sy in sorted({r['sy'] for r in rows}):
        dist = [r for r in rows if r['sy'] == sy and r['org_type'] == 'District'
                and r['subj'] == ROLLUP][0]
        sch = [r for r in rows if r['sy'] == sy and r['org_type'] == 'School'
               and r['subj'] == ROLLUP]
        gap = dist['tot_clss_cnt'] - sum(x['tot_clss_cnt'] for x in sch)
        if gap:
            resid.append(dict(sy=sy, sections=round(gap),
                              students=round(dist['tot_stu_cnt']
                                             - sum(x['tot_stu_cnt'] for x in sch)),
                              schools=len(sch)))
    ok('the years the district total exceeds its schools',
       resid, d['rollups']['district_residual'])

    # ---- the implausible school-years, as a RULE not a list ---------------------
    bad = sorted(((r['sy'], r['org_name'], r['avg_clss_cnt']) for r in rows
                  if r['subj'] == ROLLUP and r['avg_clss_cnt'] > 30.0),
                 key=lambda t: -t[2])
    ok('school-years above the implausibility bound',
       [(sy, org) for sy, org, _a in bad],
       [(r['sy'], r['org']) for r in d['implausible']])
    nxt = max((r['avg_clss_cnt'] for r in rows
               if r['subj'] == ROLLUP and r['avg_clss_cnt'] <= 30.0), default=0)
    CHECKS[0] += 1
    if not bad or nxt >= min(t[2] for t in bad):
        FAILS.append('the excluded years are not separated from the rest by the bound, '
                     'so the exclusion is a taste rather than a rule')

    # ---- the high school series -------------------------------------------------
    first, last = d['window']['first_sy'], d['window']['last_sy']
    ok('the window spans one grade era', d['window']['years'], last - first + 1)
    era = [e for e in d['eras'] if e['first_sy'] <= first and e['last_sy'] >= last]
    CHECKS[0] += 1
    if len(era) != 1 or era[0]['span'] != '9–12':
        FAILS.append('the analysis window is not inside a single grades-9-12 era: %r'
                     % (d['eras'],))
    nine = [e for e in d['eras'] if e['span'] == '9–12']
    years912 = sorted(y for e in nine for y in range(e['first_sy'], e['last_sy'] + 1))
    ok('the grades-9-12 years', years912, d['computer_science']['nine_to_twelve_years'])

    for pt in d['high_school']:
        r = P[(pt['sy'], HIGH, ROLLUP)]
        ok('LHS SY%d sections' % pt['sy'], round(r['tot_clss_cnt']), pt['sections'])
        ok('LHS SY%d average' % pt['sy'], round(r['avg_clss_cnt'], 1), pt['avg'])
        ok('LHS SY%d students' % pt['sy'], round(r['tot_stu_cnt']), pt['students'])
        ok('LHS SY%d seats' % pt['sy'],
           round(r['tot_clss_cnt'] * r['avg_clss_cnt']), pt['seats'])
        # THE PAGE DERIVES THIS AND NO GENERATOR PUBLISHES IT ANYWHERE ELSE.
        ok('LHS SY%d seats per student' % pt['sy'],
           round(r['tot_clss_cnt'] * r['avg_clss_cnt'] / r['tot_stu_cnt'], 2),
           pt['seats_per_student'], tol=0.011)

    for pt in d['district']:
        r = P[(pt['sy'], DISTRICT, ROLLUP)]
        ok('district SY%d sections' % pt['sy'], round(r['tot_clss_cnt']), pt['sections'])
        ok('district SY%d students' % pt['sy'], round(r['tot_stu_cnt']), pt['students'])

    # ---- every subject at the high school, and what the PAGE computes from it ----
    hs_total_last = P[(last, HIGH, ROLLUP)]['tot_clss_cnt']
    net = 0
    gained = lost = 0
    for s in d['high_school_subjects']:
        a = P[(first, HIGH, s['subj'])]
        b = P[(last, HIGH, s['subj'])]
        ok('LHS %s first' % s['subj'], round(a['tot_clss_cnt']), s['first'])
        ok('LHS %s last' % s['subj'], round(b['tot_clss_cnt']), s['last'])
        ok('LHS %s change' % s['subj'],
           round(b['tot_clss_cnt']) - round(a['tot_clss_cnt']), s['change'])
        ok('LHS %s last average' % s['subj'], round(b['avg_clss_cnt'], 1), s['last_avg'])
        ok('LHS %s last students' % s['subj'], round(b['tot_stu_cnt']),
           s['last_students'])
        for pt in s['points']:
            r = P[(pt['sy'], HIGH, s['subj'])]
            ok('LHS %s SY%d' % (s['subj'], pt['sy']), round(r['tot_clss_cnt']),
               pt['sections'])
        net += s['change']
        gained += 1 if s['change'] > 0 else 0
        lost += 1 if s['change'] < 0 else 0

    h = d['headline']
    ok('the net section change', net, h['sections_change'])
    ok('subjects that gained', gained, h['gainers'])
    ok('subjects that lost', lost, h['losers'])
    ok('the net change against the two All rows', net,
       round(hs_total_last) - round(P[(first, HIGH, ROLLUP)]['tot_clss_cnt']))
    ok('the students change', h['students_change'],
       round(P[(last, HIGH, ROLLUP)]['tot_stu_cnt'])
       - round(P[(first, HIGH, ROLLUP)]['tot_stu_cnt']))

    # ---- computer science, both schools -----------------------------------------
    cs = d['computer_science']
    subj = 'Computer and Information Sciences'
    ok('CS sections at the high school across its grades-9-12 years',
       sum(round(P[(y, HIGH, subj)]['tot_clss_cnt']) for y in years912),
       cs['hs_sections'])
    ok('the year the high school ran one',
       [y for y in years912 if P[(y, HIGH, subj)]['tot_clss_cnt']], [cs['hs_year']])
    ok('the students in it', round(P[(cs['hs_year'], HIGH, subj)]['tot_stu_cnt']),
       cs['hs_students'])
    for p_ in cs['high_all']:
        r = P[(p_['sy'], HIGH, subj)]
        ok('CS at the high school SY%d' % p_['sy'], round(r['tot_clss_cnt']),
           p_['sections'])
        ok('CS students at the high school SY%d' % p_['sy'], round(r['tot_stu_cnt']),
           p_['students'])
    ok('the years the high school did run it',
       [p_['sy'] for p_ in cs['high_all'] if p_['sections']],
       sorted(set(cs['ran_years']) | {cs['hs_year']}))
    mid_years = sorted({r['sy'] for r in rows if r['org_name'] == MIDDLE})
    ok('the middle school years', len(mid_years), cs['middle_years'])
    CHECKS[0] += 1
    if any(not P[(y, MIDDLE, subj)]['tot_clss_cnt'] for y in mid_years):
        FAILS.append('the middle school did not run computer science in every year, and '
                     'the page says it did')

    # ---- what stopped altogether, recomputed from the whole file ----------------
    first_sy_all = min(r['sy'] for r in rows)
    last_sy_all = max(r['sy'] for r in rows)
    want_ret = []
    for name in sorted({r['subj'] for r in rows
                        if not r['subj'].startswith(CH74) and r['subj'] != ROLLUP}):
        pts = sorted((r for r in rows if r['org_type'] == 'District'
                      and r['subj'] == name), key=lambda r: r['sy'])
        ran = [x for x in pts if x['tot_clss_cnt']]
        if ran and ran[-1]['sy'] != last_sy_all:
            want_ret.append((name, ran[-1]['sy'], round(ran[-1]['tot_clss_cnt'])))
    ok('the subjects that ran and have not since',
       sorted(want_ret), sorted((r['subj'], r['last_sy'], r['last_sections'])
                                for r in d['retired']))
    for r in d['retired']:
        ok('%s years since it ran' % r['subj'], last_sy_all - r['last_sy'],
           r['years_since'])
        ok('%s is in a reliable year' % r['subj'], r['last_sy'] >= first_sy_all + 1,
           r['in_reliable_years'])

    # ---- the second instrument --------------------------------------------------
    fj = d['fte']
    for s in fj['subjects']:
        ok('district %s sections at the start' % s['subj'],
           round(P[(fj['first_sy'], DISTRICT, s['subj'])]['tot_clss_cnt']),
           s['sections_first'])
        ok('district %s sections at the end' % s['subj'],
           round(P[(fj['last_sy'], DISTRICT, s['subj'])]['tot_clss_cnt']),
           s['sections_last'])
        sign = lambda x: 0 if abs(x) < 1e-9 else (1 if x > 0 else -1)   # noqa: E731
        ok('whether %s agrees' % s['subj'],
           sign(s['fte_change']) == sign(s['sections_change']), s['agrees'])
    ok('subjects where the two instruments agree',
       sum(1 for s in fj['subjects'] if s['agrees']), fj['agree'])
    ok('subjects compared', len(fj['subjects']), fj['compared'])
    ok('subjects where they disagree', fj['compared'] - fj['agree'], fj['disagree'])
    off = [x for x in fj['subjects'] if not x['agrees']]
    ok('the subjects that disagree', sorted(x['subj'] for x in off),
       sorted(fj['disagreeing']))
    ok('the largest line in the comparison',
       max(fj['subjects'], key=lambda x: x['fte_first'])['subj'], fj['biggest_line'])
    BD = fj['biggest_disagreement']
    ok('the disagreement the page names',
       max(off, key=lambda x: x['fte_first'])['subj'], BD['subj'])
    ok('whether it is the largest line', BD['subj'] == fj['biggest_line'],
       BD['is_largest_line'])
    ok('its sections at the start',
       round(P[(fj['first_sy'], DISTRICT, BD['subj'])]['tot_clss_cnt']),
       BD['sections_first'])
    ok('its sections at the end',
       round(P[(fj['last_sy'], DISTRICT, BD['subj'])]['tot_clss_cnt']),
       BD['sections_last'])
    ok('its average class at the start',
       round(P[(fj['first_sy'], DISTRICT, BD['subj'])]['avg_clss_cnt'], 1),
       BD['first_avg'], tol=0.05)
    ok('its average class at the end',
       round(P[(fj['last_sy'], DISTRICT, BD['subj'])]['avg_clss_cnt'], 1),
       BD['last_avg'], tol=0.05)
    # THE SENTENCE, NOT ONLY THE FIGURES. The first draft of this page called the
    # disagreeing subjects "the smallest lines in the comparison"; that was true of an
    # earlier window and false of this one, and every figure around it was still right.
    # So the STRUCTURE the paragraph rests on is asserted too.
    CHECKS[0] += 1
    if BD['fte_change'] >= 0 or BD['sections_change'] <= 0:
        FAILS.append('%s no longer has FTE falling while sections rise, and the page '
                     'says it does' % BD['subj'])

    # ---- the one subject the persona review promoted ----------------------------
    #
    # RECOMPUTED, INCLUDING THE CHOICE OF BASELINE. The middle school's largest single
    # fall is a year it recovered from, so the conclusion compares the current RUN against
    # the year before it -- and a check that only re-added the arithmetic would not notice
    # if that choice quietly reverted to the dramatic one. So the run and its baseline are
    # derived here from the CSV independently.
    L = d['language']
    for school, key in ((HIGH, 'high'), (MIDDLE, 'middle')):
        for pt in L[key]:
            r = P[(pt['sy'], school, 'Foreign Language')]
            tot = P[(pt['sy'], school, ROLLUP)]
            ok('%s language SY%d sections' % (school, pt['sy']),
               round(r['tot_clss_cnt']), pt['sections'])
            ok('%s language SY%d students' % (school, pt['sy']),
               round(r['tot_stu_cnt']), pt['students'])
            ok('%s language SY%d share' % (school, pt['sy']),
               round(r['tot_stu_cnt'] / tot['tot_stu_cnt'], 4), pt['share'], tol=0.0001)
    mp = L['middle']
    lastn = mp[-1]['sections']
    run = []
    for p in reversed(mp):
        if p['sections'] != lastn:
            break
        run.append(p['sy'])
    ok('the middle school run at its current level', sorted(run), L['middle_run'])
    prior = [p for p in mp if p['sy'] not in set(run)]
    ok('the baseline year the conclusion compares to', prior[-1]['sy'],
       L['middle_step']['from_sy'])
    ok('the years at this level', len(run), L['middle_step']['years_at_this_level'])
    ok('the lowest share in the middle school series',
       min(p['share'] for p in mp), L['middle_low']['share'], tol=0.0001)
    CHECKS[0] += 1
    if L['middle_low']['sy'] != mp[-1]['sy']:
        FAILS.append('the lowest share is no longer the most recent year, and the '
                     'conclusion calls the current year the lowest')
    earlier = [p['sy'] for p in mp[:-1] if p['sections'] == lastn]
    ok('the earlier years at this level', earlier, L['middle_prior_at_this_level'])

    # ---- the curriculum workbook, re-read by POSITION ----------------------------
    import openpyxl
    wb = openpyxl.load_workbook(CURRICULUM, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    it = ws.iter_rows(values_only=True)
    next(it)
    next(it)
    crows = [r for r in it if r and (r[0] or '').strip()]
    ok('curriculum rows', len(crows), d['curriculum']['rows'])
    ok('curriculum rows naming a product',
       sum(1 for r in crows if (r[4] or '').strip()), d['curriculum']['with_product'])
    ok('curriculum rows naming none',
       sum(1 for r in crows if not (r[4] or '').strip()), d['curriculum']['blank'])
    ok('the subjects that named one',
       sorted({(r[0] or '').strip() for r in crows if (r[4] or '').strip()}),
       d['curriculum']['reported_subjects'])

    # ---- the conclusions, against this second route ------------------------------
    import conclusions as C
    bad2 = C.check('courses', d['conclusions'])
    CHECKS[0] += 1
    if bad2:
        FAILS.extend(bad2)
    want = {
        'the-high-school-runs-more-sections-not-fewer': {
            'last': round(P[(last, HIGH, ROLLUP)]['tot_clss_cnt']),
            'first': round(P[(first, HIGH, ROLLUP)]['tot_clss_cnt']),
            'avg_last': round(P[(last, HIGH, ROLLUP)]['avg_clss_cnt'], 1),
            'stu_last': round(P[(last, HIGH, ROLLUP)]['tot_stu_cnt']),
        },
        'foreign-language-narrowed-on-every-instrument': {
            'sec_last': round(P[(last, HIGH, 'Foreign Language')]['tot_clss_cnt']),
            'stu_last': round(P[(last, HIGH, 'Foreign Language')]['tot_stu_cnt']),
            'share_last': (P[(last, HIGH, 'Foreign Language')]['tot_stu_cnt']
                           / P[(last, HIGH, ROLLUP)]['tot_stu_cnt']),
            'share_first': (P[(first, HIGH, 'Foreign Language')]['tot_stu_cnt']
                            / P[(first, HIGH, ROLLUP)]['tot_stu_cnt']),
        },
        'computer-science-at-the-high-school': {
            'sections': sum(round(P[(y, HIGH, subj)]['tot_clss_cnt']) for y in years912),
            'years': len(years912),
            'students': round(P[(cs['hs_year'], HIGH, subj)]['tot_stu_cnt']),
        },
        'a-fifth-of-high-school-sections-have-no-named-subject': {
            'sections': round(P[(last, HIGH, 'Miscellaneous')]['tot_clss_cnt']),
            'avg': round(P[(last, HIGH, 'Miscellaneous')]['avg_clss_cnt'], 1),
            'share': (P[(last, HIGH, 'Miscellaneous')]['tot_clss_cnt']
                      / P[(last, HIGH, ROLLUP)]['tot_clss_cnt']),
        },
        'the-middle-school-world-language': {
            'share_last': (P[(d['language']['middle_last']['sy'], MIDDLE,
                              'Foreign Language')]['tot_stu_cnt']
                           / P[(d['language']['middle_last']['sy'], MIDDLE,
                                ROLLUP)]['tot_stu_cnt']),
            'sec_last': round(P[(d['language']['middle_last']['sy'], MIDDLE,
                                 'Foreign Language')]['tot_clss_cnt']),
            'stu_last': round(P[(d['language']['middle_last']['sy'], MIDDLE,
                                 'Foreign Language')]['tot_stu_cnt']),
            'sec_first': round(P[(d['language']['middle_step']['from_sy'], MIDDLE,
                                  'Foreign Language')]['tot_clss_cnt']),
        },
        'sections-and-teacher-fte-agree': {
            'agree': sum(1 for s in fj['subjects'] if s['agrees']),
            'compared': len(fj['subjects']),
        },
    }
    by_id = {c['id']: c for c in d['conclusions']}
    for cid, figs in want.items():
        CHECKS[0] += 1
        if cid not in by_id:
            FAILS.append('conclusion %s is no longer on the page' % cid)
            continue
        for name, value in figs.items():
            ok('%s/%s' % (cid, name), value, by_id[cid]['figures'][name]['value'],
               tol=0.0005)

    # ---- rule 7c: the registry outranks the page ---------------------------------
    have = {r['what'] for r in csv.DictReader(open(GAPS, encoding='utf-8'))}
    for g in d['gaps']:
        CHECKS[0] += 1
        if g['what'] not in have:
            FAILS.append('the page cites a gap that is not in money-gaps.csv: %s'
                         % g['what'])
        CHECKS[0] += 1
        if not g['closes']:
            FAILS.append('the gap %r names no document that would close it. A gap with '
                         'no named remedy is a grievance.' % g['what'])


    # ==================================================================================
    # THE PER-SCHOOL, PARTICIPATION AND ERA WORK, RECOMPUTED FROM THE CSVs
    #
    # Everything below arrives from the DATABASE in the generator and from the CSVs here,
    # so a load that dropped a row, coerced a column or collided a key is caught. The
    # teacher file is read here for the first time -- the sections half of this page has
    # always been re-derived from `dese-class-size.csv` and the FTE half never was, which
    # meant half of every comparison on the page rested on one route.
    #
    # THE ROLLUPS ARE RECOMPUTED AND NOT TRUSTED, on both files: `subject='All'` is a
    # rollup row in the teacher file exactly as `subj='All'` is in the class-size file,
    # and the district is a rollup beside its schools in both.
    # ==================================================================================
    teach = list(csv.DictReader(open(TEACHER, encoding='utf-8')))
    CHECKS[0] += 1
    if not teach:
        FAILS.append('%s is empty' % TEACHER)
    for r in teach:
        r['fy'] = int(r['fy'])
        r['teacher_fte'] = float(r['teacher_fte'] or 0)
    FTE = {}
    for r in teach:
        if r['subject_level'] != 'subject':
            continue
        key = (r['fy'], r['org_name'], r['subject'])
        if key in FTE:
            FAILS.append('the teacher CSV carries %r twice' % (key,))
        FTE[key] = r['teacher_fte']

    # -- the FTE rollup this page decomposes a district figure across ----------------
    dist_fte, sch_fte = collections.defaultdict(float), collections.defaultdict(float)
    for r in teach:
        if r['subject_level'] != 'subject' or r['lea'] != LEA:
            continue
        if r['org_name'] == DISTRICT:
            dist_fte[(r['fy'], r['subject'])] += r['teacher_fte']
        elif r['org_level'] == 'school':
            sch_fte[(r['fy'], r['subject'])] += r['teacher_fte']
    worst = max((abs(dist_fte.get(k, 0) - sch_fte.get(k, 0))
                 for k in set(dist_fte) | set(sch_fte)), default=0)
    ok('the worst district-against-schools FTE gap', round(worst, 3),
       d['fte_rollup']['worst'], tol=0.001)
    ok('the subject-years in that check', len(set(dist_fte) | set(sch_fte)),
       d['fte_rollup']['subject_years'])
    CHECKS[0] += 1
    if worst > d['fte_rollup']['tolerance']:
        FAILS.append('district FTE and the sum of its schools differ by %.2f, past the '
                     'tolerance this page publishes a decomposition against' % worst)

    # -- the schools, their windows, and the swing the exclusion rests on ------------
    for sc in d['schools']:
        st = sc['stability']
        if st is None:
            continue
        pts = sorted((r for r in rows if r['org_name'] == sc['name']
                      and r['subj'] == ROLLUP
                      and sc['window']['first_sy'] <= r['sy'] <= sc['window']['last_sy']),
                     key=lambda r: r['sy'])
        ok('%s: comparable years' % sc['name'], len(pts), sc['window']['years'])
        swing = max((abs(b['tot_clss_cnt'] - a['tot_clss_cnt']) / a['tot_clss_cnt']
                     for a, b in zip(pts, pts[1:]) if a['tot_clss_cnt']), default=0)
        ok('%s: worst one-year section swing' % sc['name'], round(swing, 4), st['swing'],
           tol=0.0001)
        ok('%s: is it trendable' % sc['name'], swing <= st['bound'], st['trendable'])
        for y in st['sections']:
            m = [r for r in pts if r['sy'] == y['sy']][0]
            ok('%s SY%d sections' % (sc['name'], y['sy']), round(m['tot_clss_cnt']),
               y['sections'])
            ok('%s SY%d students' % (sc['name'], y['sy']), round(m['tot_stu_cnt']),
               y['students'])

    # -- both quadrants, district and per school ------------------------------------
    def check_instruments(inst, org):
        for r in inst['subjects']:
            a = P.get((inst['first_sy'], org, r['subj']))
            b = P.get((inst['last_sy'], org, r['subj']))
            CHECKS[0] += 1
            if not a or not b:
                FAILS.append('%s has no %r class-size row at one end of its window'
                             % (org, r['subj']))
                continue
            ok('%s %s FTE at the start' % (org, r['subj']),
               FTE.get((inst['first_sy'], org, r['subj'])), r['fte_first'], tol=0.001)
            ok('%s %s FTE at the end' % (org, r['subj']),
               FTE.get((inst['last_sy'], org, r['subj'])), r['fte_last'], tol=0.001)
            ok('%s %s FTE change' % (org, r['subj']),
               round(FTE[(inst['last_sy'], org, r['subj'])]
                     - FTE[(inst['first_sy'], org, r['subj'])], 1),
               r['fte_change'], tol=0.001)
            ok('%s %s sections change' % (org, r['subj']),
               round(b['tot_clss_cnt']) - round(a['tot_clss_cnt']),
               r['sections_change'])
            ok('%s %s class size change' % (org, r['subj']),
               round(round(b['avg_clss_cnt'], 1) - round(a['avg_clss_cnt'], 1), 1),
               r['avg_change'], tol=0.001)
            ok('%s %s got fuller' % (org, r['subj']),
               round(b['avg_clss_cnt'], 1) - round(a['avg_clss_cnt'], 1) > 0, r['fuller'])
            # THE QUADRANT LABEL IS A CLAIM AND IT IS RECOMPUTED, because a dot in the
            # wrong corner is the one error on this chart a reader cannot see.
            dx = r['fte_change']
            dy = r['sections_change']
            want = (None if abs(dx) <= 0.05 or dy == 0 else
                    ('fewer teachers, more classes' if dx < 0 and dy > 0 else
                     'fewer teachers, fewer classes' if dx < 0 else
                     'more teachers, more classes' if dy > 0 else
                     'more teachers, fewer classes'))
            ok('%s %s quadrant' % (org, r['subj']), want, r['quadrant'])
    check_instruments(d['instruments'], DISTRICT)
    for sc in d['schools']:
        if sc['instruments']:
            check_instruments(sc['instruments'], sc['name'])

    # -- the decomposition's two identities ------------------------------------------
    DEC = d['decomposition']
    ok('the schools’ FTE change sums to the district’s',
       round(sum(p_['fte_change'] for p_ in DEC['parts']), 1),
       DEC['district']['fte_change'], tol=0.25)
    ok('the schools’ section change sums to the district’s',
       sum(p_['sections_change'] for p_ in DEC['parts']),
       DEC['district']['sections_change'])

    # -- participation: the denominator, and every share on the page -----------------
    enr = {}
    for r in csv.DictReader(open(ENROL, encoding='utf-8')):
        if r['org_level'] == 'school':
            enr[(int(r['fy']), r['org_code'])] = float(r['total_cnt'] or 0)
    for sc in d['schools']:
        pa = sc['participation']
        if not pa:
            continue
        for y in pa['denominator']['years']:
            allrow = P[(y['sy'], sc['name'], ROLLUP)]
            ok('%s SY%d denominator' % (sc['name'], y['sy']),
               round(allrow['tot_stu_cnt']), y['all_students'])
            ok('%s SY%d enrolled' % (sc['name'], y['sy']),
               round(enr[(y['sy'], sc['org_code'])]), y['enrolled'])
        for r in pa['subjects']:
            for pt in r['points']:
                m = P[(pt['sy'], sc['name'], r['subj'])]
                den = P[(pt['sy'], sc['name'], ROLLUP)]['tot_stu_cnt']
                ok('%s %s SY%d share' % (sc['name'], r['subj'], pt['sy']),
                   round(m['tot_stu_cnt'] / den, 4), pt['share'], tol=0.0001)
                ok('%s %s SY%d sections' % (sc['name'], r['subj'], pt['sy']),
                   round(m['tot_clss_cnt']), pt['sections'])

    # -- the worked Miscellaneous case ------------------------------------------------
    MC = d['miscellaneous']
    a = P[(MC['first_sy'], HIGH, MC['subj'])]
    b = P[(MC['last_sy'], HIGH, MC['subj'])]
    ok('Miscellaneous sections at the start', round(a['tot_clss_cnt']),
       MC['sections_first'])
    ok('Miscellaneous sections at the end', round(b['tot_clss_cnt']), MC['sections_last'])
    ok('the Miscellaneous share at the start',
       round(a['tot_stu_cnt'] / P[(MC['first_sy'], HIGH, ROLLUP)]['tot_stu_cnt'], 4),
       MC['share_first'], tol=0.0001)
    ok('the Miscellaneous share at the end',
       round(b['tot_stu_cnt'] / P[(MC['last_sy'], HIGH, ROLLUP)]['tot_stu_cnt'], 4),
       MC['share_last'], tol=0.0001)
    ok('Miscellaneous student places at the end',
       round(b['tot_clss_cnt'] * b['avg_clss_cnt']), MC['seats_last'])
    # SEATS ARE NOT CHILDREN, asserted rather than trusted: if the two ever coincide the
    # sentence this page builds on the difference has stopped being true.
    CHECKS[0] += 1
    if MC['seats_last'] == MC['students_last']:
        FAILS.append('Miscellaneous student places and distinct students are now the '
                     'same number, and this page explains that they are different '
                     'quantities')

    # -- the eras, and the second instrument that confirms their boundary -------------
    BANDS = d['bands']
    ok('the eras cover the file with no gap',
       [(BANDS[i]['last_sy'] + 1) for i in range(len(BANDS) - 1)],
       [b['first_sy'] for b in BANDS[1:]])
    ok('the eras start at the file', BANDS[0]['first_sy'], min(r['sy'] for r in rows))
    ok('the eras end at the file', BANDS[-1]['last_sy'], max(r['sy'] for r in rows))
    G8 = d['grade8_shift']
    grade8 = set(range(G8['grade8_first_sy'], G8['grade8_last_sy'] + 1))
    # ...from the enrolment CSV, by grade, exactly as the generator does but read here
    # off the file rather than off the database.
    held8 = {int(r['fy']) for r in csv.DictReader(open(ENROL, encoding='utf-8'))
             if r['org_level'] == 'school' and r['org_name'].lower().startswith('lunenburg high')
             and float(r['grade_8_cnt'] or 0) > 0
             and min(x['sy'] for x in rows) <= int(r['fy']) <= max(x['sy'] for x in rows)}
    ok('the years grade 8 was in the high school, by enrolment', held8, grade8)
    # ...and from the teacher-by-grade-band CSV, which knows nothing about either.
    staffed = {int(r['fy']) for r in csv.DictReader(open(GRADE_SUBJ, encoding='utf-8'))
               if r['org_name'] == HIGH and r['subject'] == ROLLUP
               and float(r['grade_6_8_fte'] or 0) >= d['grade8_staffing']['noise_bound']
               and min(x['sy'] for x in rows) <= int(r['fy']) <= max(x['sy'] for x in rows)}
    ok('the same years, by teacher assignment', staffed, grade8)
    for g in d['grade8_shift']['subjects']:
        band = [e['participation'] for e in
                [x for x in d['era_series']['subjects'] if x['subj'] == g['subj']][0]['eras']]
        ok('%s into the grade-8 era' % g['subj'],
           round(band[G8['grade8_era']] - band[G8['grade8_era'] - 1], 4), g['into'],
           tol=0.0001)
        ok('%s back out of it' % g['subj'],
           round(band[G8['grade8_era'] + 1] - band[G8['grade8_era']], 4), g['out_of'],
           tol=0.0001)

    # -- every era mean, recomputed from the yearly rows ------------------------------
    for r in d['era_series']['subjects']:
        for e in r['eras']:
            yrs = [y for y in range(e['first_sy'], e['last_sy'] + 1)
                   if (y, HIGH, r['subj']) in P]
            ok('%s %d-%d participation' % (r['subj'], e['first_sy'], e['last_sy']),
               round(sum(P[(y, HIGH, r['subj'])]['tot_stu_cnt']
                         / P[(y, HIGH, ROLLUP)]['tot_stu_cnt'] for y in yrs) / len(yrs), 4),
               e['participation'], tol=0.0001)
            ok('%s %d-%d student places' % (r['subj'], e['first_sy'], e['last_sy']),
               round(sum(P[(y, HIGH, r['subj'])]['tot_clss_cnt']
                         * P[(y, HIGH, r['subj'])]['avg_clss_cnt'] for y in yrs) / len(yrs)),
               e['seats'])
            got = [FTE[(y, HIGH, r['subj'])] for y in yrs if (y, HIGH, r['subj']) in FTE]
            ok('%s %d-%d teacher FTE' % (r['subj'], e['first_sy'], e['last_sy']),
               round(sum(got) / len(got), 2) if got else None, e['fte'], tol=0.005)

    # ---- rule 13: every quote still in the document it is attributed to -----------
    import re
    for s in d['said']:
        CHECKS[0] += 1
        path = os.path.join(ROOT, 'sources', s['cite'].replace('/docs/', '', 1))
        if not os.path.exists(path):
            FAILS.append('%s is not in the archive' % s['cite'])
            continue
        text = re.sub(r'\s+', ' ', open(path, encoding='utf-8', errors='replace').read())
        if re.sub(r'\s+', ' ', s['quote']) not in text:
            FAILS.append('the quote attributed to %s %s is not in %s'
                         % (s['board'], s['date'], s['cite']))

    # ---- rule 2 on the CAVEATS, which is where it was never applied -------------
    #
    # `not_established`, `closes` and `differently` are prose that ships and they carry
    # five figures and two dates. Nothing in `conclusions.check()` reaches them -- it
    # only scans conclusions -- so this asserts each one appears, recomputed here.
    caveats = ' '.join(d['not_established']) + ' ' + d['closes'] + ' ' + d['differently']
    others = [r['avg_clss_cnt'] for r in rows
              if r['subj'] == ROLLUP and r['org_type'] == 'School'
              and r['avg_clss_cnt'] <= 30.0]
    before = [p_ for p_ in d['high_school'] if p_['sy'] == 2012]
    after = [p_ for p_ in d['high_school'] if p_['sy'] == 2013]
    expect = [
        ('the highest plausible average class size', '%.1f' % max(others)),
        ('the highest impossible school average',
         '%.1f' % max(r['avg_clss_cnt'] for r in rows
                      if r['subj'] == ROLLUP and r['avg_clss_cnt'] > 30.0)),
        ('the students the break added',
         '{:,}'.format(after[0]['students'] - before[0]['students'])),
        ('the seats the break added',
         '{:,}'.format(after[0]['seats'] - before[0]['seats'])),
        ('the curriculum rows naming a product', str(d['curriculum']['with_product'])),
        ('the curriculum rows', str(d['curriculum']['rows'])),
        ('the span of the file',
         str(max(r['sy'] for r in rows) - min(r['sy'] for r in rows) + 1)),
    ]
    for label, text in expect:
        CHECKS[0] += 1
        if text not in caveats:
            FAILS.append('%s (%s) does not appear in the caveats, which state it'
                         % (label, text))
    for key in ('whittle', 'schedule'):
        q = [x for x in d['said'] if x['key'] == key]
        CHECKS[0] += 1
        if not q:
            FAILS.append('the caveats are built from the date of the %r quote and it is '
                         'gone' % key)
            continue
        y, mo, day = q[0]['date'].split('-')
        months = ('January February March April May June July August September October '
                  'November December').split()
        want = '%d %s %s' % (int(day), months[int(mo) - 1], y)
        CHECKS[0] += 1
        if want not in caveats:
            FAILS.append('the caveats do not carry %s, the date of the %r quote'
                         % (want, key))

    # The worked cell, recomputed. It is the most extreme SUBJECT row in the file and
    # the page prints it verbatim, so a change in what is most extreme has to fail here
    # rather than leave the page quoting a cell that is no longer the example.
    cells = [r for r in rows
             if r['subj'] not in (ROLLUP,) and not r['subj'].startswith(CH74)
             and r['tot_clss_cnt'] and r['avg_clss_cnt'] > 30.0]
    w = max(cells, key=lambda r: r['avg_clss_cnt'])
    IC = d['implausible_cell']
    ok('the worked cell year', w['sy'], IC['sy'])
    ok('the worked cell school', w['org_name'], IC['org'])
    ok('the worked cell subject', w['subj'], IC['subj'])
    ok('the worked cell sections', round(w['tot_clss_cnt']), IC['sections'])
    ok('the worked cell average', round(w['avg_clss_cnt'], 1), IC['avg'], tol=0.05)
    ok('the worked cell against the school',
       round(P[(w['sy'], w['org_name'], ROLLUP)]['tot_stu_cnt']), IC['school_students'])

    # ---- rule 15a: the persona review was RUN, and recorded ----------------------
    #
    # A verifier checks the figures and cannot check that anybody's question was
    # answered. What it CAN check is that the review which does happened at all and left
    # its record -- and that the four things the omission step produced are still on the
    # page, because those are exactly the material a later edit trims first.
    personas = os.path.join(ROOT, 'notes', 'process', 'PERSONAS.md')
    CHECKS[0] += 1
    if not os.path.exists(personas):
        FAILS.append('notes/process/PERSONAS.md is not here')
    else:
        text = open(personas, encoding='utf-8').read()
        CHECKS[0] += 1
        if '/what-courses-actually-ran' not in text:
            FAILS.append('no persona review is recorded for this page. Run it -- a report '
                         'that is entirely correct and answers nobody\'s question is a '
                         'failure no verifier can catch.')
    for key in ('whittle', 'apstats', 'largest31', 'french', 'restoration'):
        CHECKS[0] += 1
        if not any(q['key'] == key for q in d['said']):
            FAILS.append('the quote %r is no longer on the page. It is there because the '
                         'omission step of the persona review found it, and it is the '
                         'first thing a later edit trims.' % key)
    CHECKS[0] += 1
    if not d.get('differently'):
        FAILS.append('the Finance Committee test: the page names nothing that could be '
                     'done differently next year')
    for term in ('French', 'Latin'):
        CHECKS[0] += 1
        if not any(t['term'] == term for t in d['searched']):
            FAILS.append('%r is not in the published search list. Residents used the '
                         'names of the languages and this project used the name of the '
                         'subject, and searching only our own vocabulary is what the '
                         'omission step exists to stop.' % term)

    if FAILS:
        print('%d check(s) FAILED of %d:' % (len(FAILS), CHECKS[0]))
        for f in FAILS:
            print('  ' + f)
        return 1
    print('ok — %d checks, every figure on /what-courses-actually-ran recomputed '
          'from %s' % (CHECKS[0], os.path.relpath(CSV, ROOT)))
    print('   the high school SY%d→SY%d: %d→%d sections, %d→%d students'
          % (first, last, h['first']['sections'], h['last']['sections'],
             h['first']['students'], h['last']['students']))
    print('   sections against teacher FTE: %d of %d subjects agree'
          % (fj['agree'], fj['compared']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
