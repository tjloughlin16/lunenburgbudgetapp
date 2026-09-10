#!/usr/bin/env python3
"""Every figure on /which-grades-students-leave, recomputed by a SECOND ROUTE.

    python3 scripts/verify_attrition.py

WHY A SECOND ROUTE AND NOT A SECOND OPINION. `build_attrition.py` reads
`dese_attrition` and `dese_enrollment` out of the database, so a load that dropped a row
or collided a key would have the generator and its own `--check` agreeing perfectly about
a wrong number. This reads the CSVs the database was built from -- which are the source
of truth; the database is a derived read model -- pivots them in Python rather than
filtering in SQL, and asserts the VALUES the payload publishes.

AND IT ASSERTS THE STRUCTURE, NOT ONLY THE FIGURES. Three sentences on that page are
claims about shape rather than about amounts, and each is checked as a shape:

  * that ONE grade is the highest in every measured year -- recomputed, not read;
  * that a school never publishes its own top grade, which is why the finding exists
    only at district level -- re-derived from the enrolment CSV by DESE's own rule;
  * that the year on a row is the year the children were GONE -- re-established here by
    the same three independent routes the generator uses, because if that is wrong every
    grade on the page is off by one and every figure is still internally consistent.

Rule 2 is re-run against the PUBLISHED payload rather than the generator's own working
copy: `conclusions.check` strips each registered rendering out of the prose and fails on
any digit left standing.
"""
import collections
import csv
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conclusions as C

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'attrition.json')
ATTR = os.path.join(ROOT, 'sources', 'data', 'dese-attrition.csv')
ENROL = os.path.join(ROOT, 'sources', 'data', 'dese-enrollment.csv')
TOWN = os.path.join(ROOT, 'sources', 'data', 'dese-town-enrollment.csv')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
PERSONAS = os.path.join(ROOT, 'notes', 'process', 'PERSONAS.md')
PAGE = os.path.join(ROOT, 'fy28', 'src', 'pages', 'WhichGradesStudentsLeave.tsx')

LEA = '01620000'
ALL = 'All Students'
HIGH = 'Lunenburg High'
SEQ = ['PK', 'K'] + [str(i) for i in range(1, 13)]
NEXT = {a: b for a, b in zip(SEQ, SEQ[1:])}
GRADES = [('gk_pct', 'K', 'k_cnt')] + [('g%02d_pct' % i, str(i), 'grade_%d_cnt' % i)
                                       for i in range(1, 12)]
ENROL_GRADES = [('pk_cnt', 'PK')] + [('k_cnt', 'K')] + [
    ('grade_%d_cnt' % i, str(i)) for i in range(1, 13)]

fails = []


def check(ok, msg):
    if not ok:
        fails.append(msg)
    return ok


def near(got, want, tol, msg):
    return check(abs(float(got) - float(want)) <= tol,
                 '%s: payload %s, recomputed %s' % (msg, want, got))


def f(x):
    return None if x in (None, '') else float(x)


def load_attrition():
    rows = []
    with open(ATTR, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            r['sy'] = int(r['sy'])
            for c, _l, _e in GRADES:
                r[c] = f(r[c])
            r['grd_all'] = f(r['grd_all'])
            rows.append(r)
    check(rows, 'dese-attrition.csv is empty')
    return rows


def load_enrolment():
    out, schools = {}, collections.defaultdict(dict)
    with open(ENROL, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['lea'] != LEA:
                continue
            fy = int(r['fy'])
            if r['org_level'] == 'district':
                out[fy] = r
            elif r['org_level'] == 'school':
                schools[r['org_code']][fy] = r
    check(out, 'no Lunenburg district enrolment rows in dese-enrollment.csv')
    return out, schools


def span_of(row):
    return [lab for col, lab in ENROL_GRADES if f(row.get(col)) and f(row[col]) > 0]


def weighted(a, e):
    num = den = 0.0
    for c, _l, ecol in GRADES:
        if a[c] is None or not f(e.get(ecol)):
            return None
        num += a[c] * f(e[ecol])
        den += f(e[ecol])
    return num / den if den else None


def main():
    if not os.path.exists(PAYLOAD):
        raise SystemExit('%s is not here. Run scripts/build_attrition.py first.'
                         % os.path.relpath(PAYLOAD, ROOT))
    d = json.load(open(PAYLOAD, encoding='utf-8'))
    rows = load_attrition()
    en, schools = load_enrolment()

    dist_raw = [r for r in rows if r['org_type'] == 'District' and r['stu_grp'] == ALL]
    dist_raw.sort(key=lambda r: r['sy'])

    # ---- the two levels, and the overlap ---------------------------------------
    lv = d['levels']
    check(len(rows) == lv['rows'], 'row count: payload %d, CSV %d' % (lv['rows'], len(rows)))
    by_level = collections.Counter(r['org_type'] for r in rows)
    check(by_level['District'] == lv['district_rows'] and
          by_level['School'] == lv['school_rows'],
          'the district/school split does not reproduce: %s' % dict(by_level))
    check(sorted({r['stu_grp'] for r in rows}) == lv['groups'],
          'the student group list does not reproduce')

    # ---- ROUTE 1 to the offset: which year's enrolment is the denominator -------
    err = {0: [], -1: []}
    for a in dist_raw:
        for off in err:
            e = en.get(a['sy'] + off)
            if not e or a['grd_all'] is None:
                continue
            w = weighted(a, e)
            if w is not None:
                err[off].append(abs(w - a['grd_all']))
    near(max(err[-1]), d['offset']['prior_year_max_error'], 1e-5,
         'the prior-year weighted reconciliation')
    near(max(err[0]), d['offset']['same_year_max_error'], 1e-5,
         'the same-year weighted reconciliation')
    check(max(err[0]) > max(err[-1]) * 2,
          'the two candidate denominators are no longer distinguishable, so the grade '
          'join the whole page rests on is not established')

    # ---- ROUTE 2 to the offset: grade 8 at the high school ----------------------
    hs_code = None
    for code, yrs in schools.items():
        if any(r['org_name'] == HIGH for r in yrs.values()):
            hs_code = code
    check(hs_code, 'no org_code in the enrolment CSV carries the name %r' % HIGH)
    held = sorted(fy for fy, r in schools[hs_code].items() if '8' in span_of(r))
    reported = sorted(r['sy'] for r in rows if r['org_name'] == HIGH
                      and r['stu_grp'] == ALL and r['g08_pct'] is not None)
    check(held == d['grade8_lag']['enrolment_years'],
          'the years %s held grade 8 do not reproduce: %s' % (HIGH, held))
    check(reported == d['grade8_lag']['attrition_years'],
          'the years %s reports a grade-8 rate do not reproduce: %s' % (HIGH, reported))
    check([y + 1 for y in held] == reported,
          'the one-year lag between the two files no longer holds')

    # ---- ROUTE 3 to the offset: DESE's own group definition years ---------------
    for grp, want in (('Economically Disadvantaged', 'economically_disadvantaged'),
                      ('Low Income', 'low_income')):
        yrs = sorted(r['sy'] for r in rows if r['org_type'] == 'District'
                     and r['stu_grp'] == grp and r['grd_all'] is not None)
        check(yrs == d['group_definition_lag'][want],
              'the published years for %r do not reproduce: %s' % (grp, yrs))
    ed = d['group_definition_lag']['economically_disadvantaged']
    check((ed[0], ed[-1]) == (2016, 2022),
          'DESE says Economically Disadvantaged covered enrolment years 2015-2021; on '
          'the one-year offset that is rows SY2016-SY2022 and the file says SY%d-SY%d'
          % (ed[0], ed[-1]))

    # ---- the terminal-grade rule, re-derived by DESE's own wording --------------
    checked = 0
    bad = []
    labels = {lab for _c, lab, _e in GRADES}
    for r in rows:
        if r['org_type'] != 'School' or r['stu_grp'] != ALL:
            continue
        code = r['org_code']
        prev, now = schools.get(code, {}).get(r['sy'] - 1), schools.get(code, {}).get(r['sy'])
        if not prev or not now:
            continue
        nxt = set(span_of(now))
        expect = {g for g in span_of(prev) if g in labels and NEXT.get(g) in nxt}
        if not expect:
            continue
        checked += 1
        got = {lab for c, lab, _e in GRADES if r[c] is not None}
        if got != expect:
            bad.append((r['sy'], r['org_name'], sorted(expect), sorted(got)))
    check(not bad, 'the terminal-grade rule fails on %d school-year(s): %s'
          % (len(bad), bad[:2]))
    check(checked == d['terminal_grade']['school_years_checked'],
          'the terminal-grade rule covered %d school-years, payload says %d'
          % (checked, d['terminal_grade']['school_years_checked']))
    # THE CONSEQUENCE, ASSERTED RATHER THAN DESCRIBED: the grade this page is about is
    # published for the district and for NO school in the current configuration.
    g = d['outlier']['grade']
    col = [c for c, lab, _e in GRADES if lab == g][0]
    now_schools = {r['org_name'] for r in rows
                   if r['org_type'] == 'School' and r['stu_grp'] == ALL
                   and r['sy'] == d['last_sy'] and r[col] is not None}
    check(not now_schools,
          'grade %s attrition is now published for %s, and the page says no school '
          'publishes it' % (g, sorted(now_schools)))

    # ---- the district series, grade by grade ------------------------------------
    by_sy = {r['sy']: r for r in dist_raw}
    for row in d['district']:
        src = by_sy.get(row['sy'])
        if not check(src, 'SY%d is in the payload and not in the CSV' % row['sy']):
            continue
        near(src['grd_all'], row['all'], 1e-9, 'SY%d all-grades rate' % row['sy'])
        for gr in row['grades']:
            c = [c for c, lab, _e in GRADES if lab == gr['grade']][0]
            check(src[c] == gr['rate'],
                  'SY%d grade %s: payload %s, CSV %s' % (row['sy'], gr['grade'],
                                                         gr['rate'], src[c]))
        if 'cohort' in row:
            e = en[row['cohort_fy']]
            coh = sum(f(e[ecol]) for _c, _l, ecol in GRADES)
            near(coh, row['cohort'], 0.5, 'SY%d K-11 cohort' % row['sy'])
            near(src['grd_all'] * coh, row['implied'], 0.05,
                 'SY%d implied departures' % row['sy'])

    # ---- the grade profile, and the one grade that stands off -------------------
    highest = collections.Counter()
    for r in dist_raw:
        best = max(GRADES, key=lambda t: (r[t[0]] is not None, r[t[0]] or -1))
        highest[best[1]] += 1
    for p in d['grade_profile']:
        v = [r[[c for c, lab, _e in GRADES if lab == p['grade']][0]] for r in dist_raw]
        v = [x for x in v if x is not None]
        near(statistics.mean(v), p['mean'], 5e-5, 'grade %s mean' % p['grade'])
        near(statistics.median(v), p['median'], 5e-5, 'grade %s median' % p['grade'])
        check(min(v) == p['min'] and max(v) == p['max'],
              'grade %s range does not reproduce' % p['grade'])
        check(highest[p['grade']] == p['times_highest'],
              'grade %s is highest in %d years, payload says %d'
              % (p['grade'], highest[p['grade']], p['times_highest']))
    o = d['outlier']
    check(highest[o['grade']] == len(dist_raw),
          'grade %s is the highest in %d of %d years and the page claims every one'
          % (o['grade'], highest[o['grade']], len(dist_raw)))
    means = {p['grade']: p['mean'] for p in d['grade_profile']}
    runner = max((m for gg, m in means.items() if gg != o['grade']))
    near(means[o['grade']] / runner, o['multiple'], 0.05,
         'how many times the next grade')

    # A RISING RUN IS A SHAPE, so it is recounted rather than read.
    ser = [s['rate'] for s in o['series']]
    runs, cur = [], 1
    for a, b in zip(ser, ser[1:]):
        cur = cur + 1 if b > a else 1
        runs.append(cur)
    check(runs[-1] == o['rising_run'],
          'the current run of rises is %d, payload says %d' % (runs[-1], o['rising_run']))
    check(max(runs[:-1]) == o['longest_prior_rising_run'],
          'the longest earlier run of rises is %d, payload says %d'
          % (max(runs[:-1]), o['longest_prior_rising_run']))
    check(sorted(ser, reverse=True).index(o['latest']['rate']) + 1 == o['rank_of_latest'],
          'the latest year no longer ranks where the payload says it does')

    # ---- the churn against the enrolment change ---------------------------------
    ch = d['churn']
    total = sum(r['implied'] for r in d['district'] if r.get('implied') is not None)
    near(total, ch['implied_total'], 1.0, 'the implied total departures')
    near(f(en[ch['first_fy']]['total_cnt']), ch['enrol_first'], 0.5, 'enrolment at the start')
    near(f(en[ch['last_fy']]['total_cnt']), ch['enrol_last'], 0.5, 'enrolment at the end')
    near(total / abs(ch['enrol_change']), ch['ratio'], 0.05, 'the churn ratio')

    # ---- the eras ---------------------------------------------------------------
    for b in d['eras']['bands']:
        yrs = [r for r in dist_raw if b['first_sy'] <= r['sy'] <= b['last_sy']]
        col = [c for c, lab, _e in GRADES if lab == o['grade']][0]
        near(statistics.mean(r[col] for r in yrs), b['outlier_mean'], 5e-5,
             'SY%d-SY%d grade %s mean' % (b['first_sy'], b['last_sy'], o['grade']))
        near(statistics.mean(r['grd_all'] for r in yrs), b['all_mean'], 5e-5,
             'SY%d-SY%d all-grades mean' % (b['first_sy'], b['last_sy']))
    check(len({b['span'] for b in d['eras']['bands'] if b['covid']}) <= 1,
          'the pandemic era now straddles two grade configurations')

    # ---- the school-level artefact ----------------------------------------------
    art = d['school_artefact']
    col = [c for c, lab, _e in GRADES if lab == art['grade']][0]
    hs = [r for r in rows if r['org_name'] == HIGH and r['stu_grp'] == ALL
          and r['grd_all'] is not None]
    a = [r['grd_all'] for r in hs if r[col] is not None]
    b = [r['grd_all'] for r in hs if r[col] is None]
    near(statistics.mean(a), art['with_mean'], 5e-5, 'the high school with grade 8')
    near(statistics.mean(b), art['without_mean'], 5e-5, 'the high school without it')
    check(len(a) == art['with_years'] and len(b) == art['without_years'],
          'the split of high school years does not reproduce')
    near((statistics.mean(a) - statistics.mean(b)) * 100, art['points'], 0.05,
         'the artefact, in points')

    # ---- the selected populations -----------------------------------------------
    for grp in d['groups']:
        got = [r for r in rows if r['org_type'] == 'District'
               and r['stu_grp'] == grp['grp']]
        pub = [r[col] for r in got if r[col] is not None]
        check(len(pub) == grp['published_years'],
              '%s has %d published grade-%s years, payload says %d'
              % (grp['grp'], len(pub), art['grade'], grp['published_years']))
        if pub:
            near(statistics.mean(pub), grp['mean'], 5e-5, '%s mean' % grp['grp'])
    ref = [g for g in d['groups'] if g['grp'] == ALL][0]
    gg = d['group_gap']
    swd = [r for r in rows if r['org_type'] == 'District' and r['stu_grp'] == gg['grp']]
    for row in gg['grades']:
        c = [c for c, lab, _e in GRADES if lab == row['grade']][0]
        theirs = [r[c] for r in swd if r[c] is not None]
        ours = [r[c] for r in dist_raw if r[c] is not None]
        near((statistics.mean(theirs) - statistics.mean(ours)) * 100, row['gap_points'],
             0.05, 'the %s gap at grade %s' % (gg['grp'], row['grade']))
    check(gg['widest']['grade'] == o['grade'],
          'the widest group gap is now at grade %s and the page says grade %s'
          % (gg['widest']['grade'], o['grade']))
    check(gg['widest']['gap_points'] > gg['next_widest']['gap_points'] * 2,
          'the gap at grade %s is no longer more than double every other grade, and '
          'the conclusion is written as "at one step, not everywhere"' % o['grade'])
    check(ref['mean'] == [p for p in d['grade_profile']
                          if p['grade'] == o['grade']][0]['mean'],
          'the All Students reference rate disagrees with the grade profile')

    # ---- where they went, and the column that is not there ----------------------
    dest = d['destinations']
    with open(TOWN, encoding='utf-8') as fh:
        rdr = csv.DictReader(fh)
        check(not any('grade' in c for c in rdr.fieldnames),
              'dese-town-enrollment.csv now has a grade column, which is the document '
              'that would close the largest gap on this page')
        town = [r for r in rdr if r['town'] == 'Lunenburg' and int(r['fy']) == dest['fy']]
    check(town, 'no Lunenburg rows for FY%d in the town enrolment CSV' % dest['fy'])
    away = sum(int(float(r['students'])) for r in town
               if not (r['enrollment_reason'] == 'Resident/Member'
                       and r['district'] == 'Lunenburg'))
    check(away == dest['elsewhere'],
          'children educated elsewhere in FY%d: CSV %d, payload %d'
          % (dest['fy'], away, dest['elsewhere']))
    monty = sum(int(float(r['students'])) for r in town if 'Montachusett' in r['district'])
    check(monty == dest['monty_tech'],
          'Monty Tech: CSV %d, payload %d' % (monty, dest['monty_tech']))

    # ---- the grade 8 to grade 9 step --------------------------------------------
    g9 = d['grade9']
    for row in g9['years']:
        e, nxt = en[row['cohort_fy']], en[row['sy']]
        near(f(e['grade_8_cnt']), row['grade8'], 0.5,
             'the grade 8 cohort of FY%d' % row['cohort_fy'])
        near(f(nxt['grade_9_cnt']), row['grade9'], 0.5,
             'grade 9 in SY%d' % row['sy'])
        near(f(e['grade_8_cnt']) * (1 - row['rate']), row['stayed'], 0.05,
             'those who stayed, FY%d' % row['cohort_fy'])
    check(sum(1 for r in g9['years'] if r['residual'] > 0) == g9['larger'],
          'the count of years grade 9 was larger than the eighth graders who stayed '
          'does not reproduce')

    # ---- DESE's own words, still in the payload ---------------------------------
    for phrase in ('from the end of one school year to the beginning of the next',
                   'as of October 1 of the given school year'):
        check(phrase in d['dese']['definition'],
              'the published DESE definition no longer contains %r, and trap 1 on this '
              'page rests on it' % phrase)
    check('no grade in the given year for students from the previous year to advance'
          in d['dese']['blanks'],
          'the published DESE blank rule no longer states the terminal-grade case')

    # ---- rule 2, re-run against the published payload ---------------------------
    problems = C.check('attrition', d['conclusions'])
    for p in problems:
        check(False, p)
    for c in d['conclusions']:
        check(c['kind'] in ('measured', 'hypothesis'), '%s: bad kind' % c['id'])
        check(c.get('bearing') in ('sizes', 'lever'),
              '%s: no bearing, so nothing says whether a reader can act on it' % c['id'])
    heads = {c['id']: c['figures'][c['figure']]['value']
             for c in d['conclusions'] if c.get('figure')}
    near(means[o['grade']], heads['one-grade-does-all-the-leaving'], 1e-9,
         'the headline grade rate')
    near(o['latest']['rate'], heads['a-high-year-not-a-new-level'], 1e-9,
         'the latest year')
    near(total, heads['the-leaving-is-nine-times-the-fall'], 1.0,
         'the headline implied total')
    near(statistics.mean([r[[c for c, lab, _e in GRADES
                             if lab == o['grade']][0]]
                          for r in rows
                          if r['org_type'] == 'District'
                          and r['stu_grp'] == 'Students with Disabilities'
                          and r[[c for c, lab, _e in GRADES
                                 if lab == o['grade']][0]] is not None]),
         heads['the-gap-is-at-one-step-not-everywhere'], 5e-5,
         'the headline IEP rate')

    # ---- the quotes, verbatim, at the address the page cites --------------------
    for s in d['said']:
        rel = s['cite'].replace('/docs/', 'sources/')
        path = os.path.join(ROOT, rel)
        if not check(os.path.exists(path), '%s is cited and is not here' % rel):
            continue
        text = re.sub(r'\s+', ' ', open(path, encoding='utf-8', errors='replace').read())
        check(re.sub(r'\s+', ' ', s['quote']) in text,
              'the quote from %s %s is not in %s' % (s['board'], s['date'], rel))

    # ---- the gap register outranks the page -------------------------------------
    have = {r['what'] for r in csv.DictReader(open(GAPS, encoding='utf-8'))}
    for g_ in d['gaps']:
        check(g_['what'] in have,
              'the page cites a gap that is not in money-gaps.csv: %r' % g_['what'])
        check(g_['closes'],
              'the gap %r has no "— closes:" document. A gap with no named remedy '
              'is a grievance.' % g_['what'])

    # ---- the persona review was actually run ------------------------------------
    personas = open(PERSONAS, encoding='utf-8').read()
    check('/which-grades-students-leave' in personas,
          'notes/process/PERSONAS.md records no review of this page. Rule 15a: a '
          'verifier checks the figures and cannot check that anybody’s question '
          'was answered.')

    # ---- rule 2 on the page itself ----------------------------------------------
    if os.path.exists(PAGE):
        src = open(PAGE, encoding='utf-8').read()
        body = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
        body = re.sub(r'className="[^"]*"', '', body)
        body = re.sub(r"'[^']*'", '', body)
        stray = sorted(set(re.findall(r'>\s*[^<>{}]*?(\d[\d,.]*)%?[^<>{}]*?<', body)))
        check(not stray,
              'literal figures are typed into the page: %s. Rule 2: every figure comes '
              'out of the payload.' % stray[:6])

    if fails:
        print('verify_attrition: %d problem(s)' % len(fails))
        for m in fails:
            print('  ' + m)
        return 1
    print('verify_attrition: ok — %d conclusions, %d district years, %d school-years '
          'checked against DESE’s own blank rule, the denominator established '
          'three independent ways'
          % (len(d['conclusions']), len(d['district']),
             d['terminal_grade']['school_years_checked']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
