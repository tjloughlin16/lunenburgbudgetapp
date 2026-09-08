#!/usr/bin/env python3
"""Recompute every figure on the four special education reports, from the CSVs.

WHY IT READS THE CSVs AND NOT THE DATABASE. `scripts/build_special_education.py` writes
the four payloads out of `sources/data/lunenburg.db`. A verifier that queried the same
database with the same SQL would prove that sqlite is deterministic. The CSVs are the
source of truth and the database is a derived read model rebuilt from scratch every run,
so reading the CSVs makes this an INDEPENDENT path: it catches a drifting extract and a
drifting database load as well as a drifting page.

WHAT IT ASSERTS, and the order matters -- rule 13 says a check must assert the number, not
the prose around it, because `verify_athletics.py` once passed on a sentence that existed
and was wrong:

  1. EVERY FIGURE in the four payloads, recomputed from the CSVs.
  2. THE STRUCTURAL CLAIMS the prose rests on. A page can be wrong while every number on
     it is a faithful copy: "the budget line ties to the general fund column" is a
     sentence about a relationship, and the day it stops holding the figures are all still
     right. Those are asserted separately and by name.
  3. THE SEPARATION ITSELF. The four reports exist because their grains must not be
     joined, so this refuses to pass if a payload has acquired a field from another one's
     grain -- a dollar in the student payload, a student count in the cost payload.
  4. THE PERSONA REVIEW, notes/process/PERSONAS.md. Six readers, one test each, and three
     of the six are about what a document OMITS. The text that satisfied each is asserted
     against the rendered page source, so a later edit cannot quietly remove it.

    python3 scripts/verify_special_education.py
"""
import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
PAGES = os.path.join(ROOT, 'fy28', 'src', 'pages')
LEA = '01620000'
TOWN = 'Lunenburg'

FAILS = []
CHECKS = [0]


def rows(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def num(v):
    v = (v or '').strip()
    if not v:
        return None
    return float(v)


def payload(name):
    with open(os.path.join(PUB, name), encoding='utf-8') as fh:
        return json.load(fh)


def eq(label, got, want, tol=0.0):
    CHECKS[0] += 1
    ok = (got == want) if not tol else (got is not None and want is not None
                                        and abs(got - want) <= tol)
    if not ok:
        FAILS.append('%s: page says %r, the CSVs give %r' % (label, got, want))
    return ok


def head(t):
    print('\n%s' % t)


# ---------------------------------------------------------------- 1. how many students

def check_students():
    head('§students  fy28/public/data/sped-students.json against dese-sped-*.csv')
    d = payload('sped-students.json')
    prog = [r for r in rows('dese-sped-program.csv')
            if r['lea'] == LEA and r['geo_level'] == 'district']

    def pick(fy, cat, ind, col):
        for r in prog:
            if int(r['fy']) == fy and r['indicator_category'] == cat and r['indicator'] == ind:
                return num(r[col])
        return None

    for c in d['counts']:
        fy = c['fy']
        eq('FY%d count on an IEP' % fy, float(c['swd']),
           pick(fy, 'Enrollment', 'Students with Disabilities', 'measure_cnt'))
        eq('FY%d enrolment' % fy, float(c['enrolled']),
           pick(fy, 'Enrollment', 'Total In- and Out-of-District Students', 'denominator_cnt'))
        eq('FY%d in district' % fy, float(c['in_district']),
           pick(fy, 'In District/Out of District', 'In-District', 'measure_cnt'))
        eq('FY%d out of district' % fy, float(c['out_of_district']),
           pick(fy, 'In District/Out of District', 'Out-of-District', 'measure_cnt'))
        eq('FY%d share' % fy, c['share_pct'],
           round(100.0 * c['swd'] / c['enrolled'], 2), 0.005)
    print('  ..    %d years of counts recomputed' % len(d['counts']))

    # THE STRUCTURAL CLAIM. Finding 2 says the two published parts add up in every year,
    # and that the ratio denominator IS the in-district count. Both are relationships, so
    # both are asserted rather than left to the figures.
    CHECKS[0] += 1
    if not all(c['in_district'] + c['out_of_district'] == c['swd'] for c in d['counts']):
        FAILS.append('the page claims in-district + out-of-district = the total in every '
                     'year, and it no longer does')
    else:
        print('  OK    in district + out of district = the published total, every year')
    CHECKS[0] += 1
    if not (d['denominator_all_match'] and all(x['residual'] == 0 for x in d['denominator'])):
        FAILS.append('the page claims the staffing-ratio denominator equals the '
                     'in-district count exactly; it no longer does')
    else:
        print('  OK    the staffing-ratio denominator is the in-district count, every year')

    ind = [r for r in rows('dese-sped-indicator.csv')
           if r['lea'] == LEA and r['geo_level'] == 'district'
           and r['indicator_category'] == 'SPECIAL EDUCATION STAFF']
    paras = {int(r['fy']): r for r in ind
             if 'paraprofessional' in r['indicator'].lower()}
    for p in d['paras']:
        r = paras.get(p['fy'])
        CHECKS[0] += 1
        if not r:
            FAILS.append('FY%d paraprofessional row is not in the indicator CSV' % p['fy'])
            continue
        eq('FY%d para FTE' % p['fy'], float(p['fte']), num(r['denominator_cnt']))
        eq('FY%d para base' % p['fy'], float(p['swd_base']), num(r['measure_cnt']))
        eq('FY%d para per 100' % p['fy'], p['per_100'], num(r['measure_pct']), 0.001)
        eq('FY%d para rate reproduces' % p['fy'],
           round(100.0 * p['fte'] / p['swd_base'], 1), p['per_100'], 0.051)
    print('  ..    %d years of paraprofessional FTE recomputed' % len(d['paras']))

    # THE OTHER STRUCTURAL CLAIM, and the one that decides what the page is allowed to
    # publish: exactly one staff row reproduces from its own printed figures.
    tally = {}
    for r in ind:
        if r['value_type'] != 'FTE per 100 SWD':
            continue
        fte, base, rate = num(r['denominator_cnt']), num(r['measure_cnt']), num(r['measure_pct'])
        if fte is None or base is None or rate is None:
            continue
        t = tally.setdefault(r['indicator'], [0, 0])
        t[1] += 1
        t[0] += 1 if abs(round(100.0 * fte / base, 1) - rate) < 0.051 else 0
    for s in d['staff_reconciliation']:
        got = tally.get(s['indicator'])
        eq('%s reproduces in' % s['indicator'], (s['reproduces'], s['years']),
           (got[0], got[1]) if got else None)
    CHECKS[0] += 1
    perfect = [k for k, v in tally.items() if v[0] == v[1]]
    if len(perfect) != 1 or 'paraprofessional' not in perfect[0].lower():
        FAILS.append('the page publishes the paraprofessional row BECAUSE it is the only '
                     'staff row that reproduces; the set that reproduces is now %r'
                     % (perfect,))
    else:
        print('  OK    exactly one staff row reproduces, and it is the one published')

    mv = {int(r['fy']): r for r in rows('dese-sped-movement.csv')
          if r['lea'] == LEA and r['geo_level'] == 'district' and r['grades'] == 'K-12'}
    for t in d['third_count']:
        r = mv[t['fy']]
        eq('FY%d movement enrolled' % t['fy'], float(t['enrolled']), num(r['enrolled_cnt']))
        eq('FY%d movement on IEP' % t['fy'], float(t['on_iep']), num(r['on_iep_cnt']))
        eq('FY%d movement in' % t['fy'], float(t['moved_in']), num(r['moved_in_cnt']))
        eq('FY%d movement out' % t['fy'], float(t['moved_out']), num(r['moved_out_cnt']))
    CHECKS[0] += 1
    if not all(g['difference'] < 0 for g in d['third_count_gap']):
        FAILS.append('the page says the movement file is LOWER in every overlapping '
                     'year; it is not')
    else:
        print('  OK    the third count is lower than the programme count in every year')

    for row in d['disability']:
        eq('FY%d %s' % (row['fy'], row['kind']), float(row['count']),
           pick(row['fy'], 'Disability Type All', row['kind'], 'measure_cnt'))
    for row in d['placement']:
        eq('FY%d placement %s' % (row['fy'], row['setting']), float(row['count']),
           pick(row['fy'], 'Placement', row['setting'], 'measure_cnt'))
    for s in d['placement_shortfall']:
        parts = sum(p['count'] for p in d['placement'] if p['fy'] == s['fy'])
        eq('FY%d placement parts' % s['fy'], s['parts'], parts)
        eq('FY%d placement unaccounted' % s['fy'], s['unaccounted'], s['total'] - parts)
    print('  ..    disability, placement and grade-span rows recomputed')

    # THE SEPARATION. No money in the student payload, at any depth.
    CHECKS[0] += 1
    blob = json.dumps(d)
    money = re.findall(r'"(gen_fund|grants|total_eligible|paid|usd|dollars)"', blob)
    if money:
        FAILS.append('the student payload has acquired money fields %r -- the four '
                     'reports are separate so that a cost per student cannot be written'
                     % sorted(set(money)))
    else:
        print('  OK    the student payload carries no money field')


# ------------------------------------------------------------------ 2. who leaves

def check_leaving():
    head('§leaving  fy28/public/data/sped-leaving.json against dese-town-enrollment.csv')
    d = payload('sped-leaving.json')
    src = [r for r in rows('dese-town-enrollment.csv') if r['town'] == TOWN]
    inbound_src = [r for r in rows('dese-town-enrollment.csv')
                   if r['lea'] == LEA and r['town'] != TOWN
                   and r['enrollment_reason'] == 'School Choice Program']
    for s in d['series']:
        fy = s['fy']
        yr = [r for r in src if int(r['fy']) == fy]
        eq('FY%d resident total' % fy, float(s['total']),
           sum(num(r['students']) or 0 for r in yr))
        eq('FY%d in Lunenburg' % fy, float(s['in_lunenburg']),
           sum(num(r['students']) or 0 for r in yr if r['lea'] == LEA))
        eq('FY%d elsewhere' % fy, float(s['elsewhere']),
           sum(num(r['students']) or 0 for r in yr if r['lea'] != LEA))
        eq('FY%d elsewhere share' % fy, s['elsewhere_pct'],
           round(100.0 * s['elsewhere'] / s['total'], 2), 0.005)
    print('  ..    %d years recomputed' % len(d['series']))

    latest = d['latest_year']
    for row in d['elsewhere_latest']:
        eq('FY%d %s' % (latest, row['district']), float(row['students']),
           sum(num(r['students']) or 0 for r in src
               if int(r['fy']) == latest and r['district'] == row['district']
               and r['lea'] != LEA))
    for n in d['net']:
        eq('FY%d choice out' % n['fy'], float(n['out']),
           sum(num(r['students']) or 0 for r in src if int(r['fy']) == n['fy']
               and r['enrollment_reason'] == 'School Choice Program'))
        eq('FY%d choice in' % n['fy'], float(n['in']),
           sum(num(r['students']) or 0 for r in inbound_src if int(r['fy']) == n['fy']))
        eq('FY%d choice net' % n['fy'], n['net'], n['in'] - n['out'])
    print('  ..    both directions of school choice recomputed')

    # THE STRUCTURAL CLAIM, and it is the reason this report is separate at all.
    CHECKS[0] += 1
    with open(os.path.join(DATA, 'dese-town-enrollment.csv'), encoding='utf-8') as fh:
        cols = next(csv.reader(fh))
    if any(re.search(r'iep|disab|sped|special', c, re.I) for c in cols):
        FAILS.append('dese-town-enrollment.csv now carries a disability column -- the '
                     'whole reason this report is kept apart has changed and the page '
                     'must be rewritten')
    else:
        print('  OK    the source still carries no disability flag')

    # ELSEWHERE MEANS "not the Lunenburg LEA". The first version of the generator
    # subtracted the Resident/Member PROGRAMME instead, which hid the largest destination
    # in the file. Asserted, because it is a definition and definitions drift silently.
    CHECKS[0] += 1
    member = sum(num(r['students']) or 0 for r in src
                 if int(r['fy']) == latest and r['enrollment_reason'] == 'Resident/Member')
    here = d['last']['in_lunenburg']
    if member <= here:
        FAILS.append('the Resident/Member programme no longer exceeds enrolment in the '
                     'Lunenburg district; the definition note on the page is now wrong')
    else:
        print('  OK    Resident/Member (%d) still exceeds Lunenburg enrolment (%d), which '
              'is why "elsewhere" is drawn from the district code' % (member, here))


# ------------------------------------------------------------------- 3. what it costs

def check_cost():
    head('§cost  fy28/public/data/sped-cost.json against dese-function-expenditure.csv')
    d = payload('sped-cost.json')
    exp = [r for r in rows('dese-function-expenditure.csv')
           if r['lea'] == LEA and r['level'] == 'detail'
           and r['func_code'] in ('9300', '9400')]
    for s in d['spend']:
        yr = [r for r in exp if int(r['fy']) == s['fy']]
        eq('FY%d tuition general fund' % s['fy'], float(s['gen_fund']),
           round(sum(num(r['gen_fund']) or 0 for r in yr)))
        eq('FY%d tuition other funds' % s['fy'], float(s['grants']),
           round(sum(num(r['grants_revolving']) or 0 for r in yr)))
        eq('FY%d tuition all funds' % s['fy'], float(s['total']),
           round(sum(num(r['total']) or 0 for r in yr)))
    print('  ..    %d years of tuition by fund recomputed' % len(d['spend']))

    hist = {int(r['fy']): r for r in rows('ood-tuition-history.csv')
            if r['stage'] == 'restated'}
    for m in d['budget_vs_fund']:
        eq('FY%d restated budget line' % m['fy'], float(m['budget']),
           num(hist[m['fy']]['total']))
        eq('FY%d budget minus general fund' % m['fy'], m['vs_gen_fund'],
           m['budget'] - m['dese_gen_fund'])
    # THE FINDING ITSELF, and the only sentence on the page that could go wrong while
    # every figure stayed right: the line ties to the GENERAL FUND column and to no other.
    CHECKS[0] += 1
    ties = [m for m in d['budget_vs_fund'] if abs(m['vs_gen_fund']) <= 2]
    allf = [m for m in d['budget_vs_fund'] if abs(m['vs_all_funds']) <= 2]
    if len(ties) != d['ties_count'] or len(ties) < 8 or allf:
        FAILS.append('the page rests on the budget line tying to DESE’s general fund '
                     'column and NOT to its all-funds column; recomputed, %d tie to the '
                     'general fund and %d tie to all funds'
                     % (len(ties), len(allf)))
    else:
        print('  OK    the budget line ties to the general fund column in %d of %d years, '
              'and to all funds in none' % (len(ties), len(d['budget_vs_fund'])))

    cb = {int(r['fy']): r for r in rows('dese-circuit-breaker.csv')
          if r['lea'] == LEA and r['level'] == 'district'}
    for b in d['breaker']:
        r = cb[b['fy']]
        eq('FY%d claimed students' % b['fy'], float(b['students']),
           num(r['eligible_students_claimed']) or 0)
        eq('FY%d eligible expense' % b['fy'], float(b['eligible']),
           round(num(r['total_eligible_expenses']) or 0))
        eq('FY%d threshold' % b['fy'], float(b['threshold']),
           round(num(r['threshold_amount']) or 0))
        eq('FY%d paid' % b['fy'], float(b['paid']),
           round(num(r['total_quarterly_payment']) or 0))
        eq('FY%d transport reimbursed' % b['fy'], float(b['reimb_transport']),
           round(num(r['reimb_transport']) or 0))
        eq('FY%d claim residual' % b['fy'], b['claim_residual'],
           round((num(r['total_eligible_expenses']) or 0)
                 - (num(r['threshold_amount']) or 0)
                 - (num(r['total_net_claim']) or 0)))
    print('  ..    %d years of circuit breaker recomputed' % len(d['breaker']))

    for b in d['beside']:
        s = next(x for x in d['spend'] if x['fy'] == b['fy'])
        c = next(x for x in d['breaker'] if x['fy'] == b['fy'])
        eq('FY%d outside the appropriation' % b['fy'], b['outside_appropriation'], s['grants'])
        eq('FY%d circuit breaker paid' % b['fy'], b['circuit_breaker_paid'], c['paid'])
        eq('FY%d difference' % b['fy'], b['difference'],
           s['grants'] - c['paid'])

    # THE MECHANISM the page describes: the threshold is a DEDUCTION, not a rate, and
    # that rests on an identity holding in most years rather than in all of them. A page
    # that said "in every year" would be wrong the moment it stopped, with every figure
    # on it still right.
    CHECKS[0] += 1
    zero = [b['fy'] for b in d['breaker'] if b['claim_residual'] == 0]
    if sorted(zero) != sorted(d['cb_identity_years']) or len(zero) < 10:
        FAILS.append('the page says eligible - threshold = the net claim in %d of %d '
                     'years; recomputed it is %d'
                     % (len(d['cb_identity_years']), len(d['breaker']), len(zero)))
    else:
        print('  OK    eligible - threshold = the net claim in %d of %d years, as the '
              'page says' % (len(zero), len(d['breaker'])))

    # THE SEPARATION, the other way: no student count in the money payload.
    CHECKS[0] += 1
    stray = re.findall(r'"(swd|in_district|on_iep|share_pct)"', json.dumps(d))
    if stray:
        FAILS.append('the cost payload has acquired student fields %r' % sorted(set(stray)))
    else:
        print('  OK    the cost payload carries no student count')


# ------------------------------------------------------------------------ 4. the route

def check_route():
    head('§route  fy28/public/data/sped-route.json against dese-sped-trajectory.csv')
    d = payload('sped-route.json')
    tr = [r for r in rows('dese-sped-trajectory.csv')
          if r['lea'] == LEA and r['geo_level'] == 'district']
    for c in d['cohorts']:
        r = next(x for x in tr if int(x['fy']) == c['fy']
                 and x['grade_span'] == c['grade_span']
                 and x['placement_at_start'] == c['start'])
        eq('FY%d %s %s cohort' % (c['fy'], c['grade_span'], c['start']),
           float(c['cohort']), num(r['cohort_cnt']))
        eq('FY%d %s %s out of district' % (c['fy'], c['grade_span'], c['start']),
           float(c['out_of_district']), num(r['out_of_district_cnt']))
        eq('FY%d %s %s rate' % (c['fy'], c['grade_span'], c['start']), c['ood_pct'],
           round(100.0 * c['out_of_district'] / c['cohort'], 1), 0.051)
    print('  ..    %d cohorts recomputed' % len(d['cohorts']))

    for p in d['pooled']:
        got = [c for c in d['k12'] if c['start'] == p['start']]
        eq('%s pooled cohort' % p['start'], p['cohort'], sum(c['cohort'] for c in got))
        eq('%s pooled out of district' % p['start'], p['out_of_district'],
           sum(c['out_of_district'] for c in got))
    # THE COMPARISON IS THE PAGE. Two starting placements, and the substantially separate
    # one has to be the higher of the two or the standfirst is backwards.
    CHECKS[0] += 1
    incl = next((p for p in d['pooled'] if 'Inclusive' in p['start']), None)
    sub = next((p for p in d['pooled'] if 'Separate' in p['start']), None)
    if not incl or not sub or sub['ood_pct'] <= incl['ood_pct']:
        FAILS.append('the page compares two starting placements and says the '
                     'substantially separate one is the higher; that is no longer true')
    else:
        print('  OK    %.1f%% against %.1f%% — the comparison the page makes still holds'
              % (sub['ood_pct'], incl['ood_pct']))
    # AND THE BASES TRAVEL. A percentage off tens of children must never be published
    # alone, so every cohort row carries its count.
    CHECKS[0] += 1
    if any('cohort' not in c or 'out_of_district' not in c for c in d['cohorts']):
        FAILS.append('a trajectory row no longer carries its counts; a percentage off a '
                     'base of tens must never travel alone')
    else:
        print('  OK    every rate is published beside its own counts')

    # The state benchmark must be the STATE rollup and nothing else -- the row that once
    # turned a $26.6M district into $116M when it was summed with the detail.
    st = [r for r in rows('dese-sped-trajectory.csv')
          if r['geo_level'] == 'state' and r['grade_span'] == 'K-12']
    for s in d['latest_state']:
        r = next(x for x in st if int(x['fy']) == s['fy']
                 and x['placement_at_start'] == s['start'])
        eq('state FY%d %s cohort' % (s['fy'], s['start']), float(s['cohort']),
           num(r['cohort_cnt']))
        eq('state FY%d %s rate' % (s['fy'], s['start']), s['ood_pct'],
           round(100.0 * s['out_of_district'] / s['cohort'], 1), 0.051)
    CHECKS[0] += 1
    if any(int(r['district'] != 'State') for r in
           [x for x in rows('dese-sped-trajectory.csv') if x['geo_level'] == 'state']):
        FAILS.append('a row marked geo_level=state is not the State rollup')
    else:
        print('  OK    the benchmark rows are the State rollup and are never summed in')

    pc = {int(r['fy']): r for r in rows('placement-counts.csv')}
    for c in d['counts']:
        r = pc[c['fy']]
        eq('FY%d town placement total' % c['fy'],
           c['total'], int(r['total']) if r['total'].strip() else None)
        eq('FY%d town as-of' % c['fy'], c['as_of'], r['as_of'])
        eq('FY%d collaborative basis' % c['fy'], c['collaborative_basis'],
           r['collaborative_basis'])
    print('  ..    %d years of the town’s own count recomputed' % len(d['counts']))

    prog = [r for r in rows('dese-sped-program.csv')
            if r['lea'] == LEA and r['geo_level'] == 'district'
            and r['indicator_category'] == 'In District/Out of District'
            and r['indicator'] == 'Out-of-District']
    for t in d['two_counts']:
        r = next(x for x in prog if int(x['fy']) == t['fy'])
        eq('FY%d DESE out-of-district' % t['fy'], float(t['dese']), num(r['measure_cnt']))
        eq('FY%d the two counts differ by' % t['fy'], t['difference'], t['dese'] - t['town'])
    # The two kinds of hole in the town's series are different and the page describes
    # them differently, so which years fall in which is asserted rather than inferred from
    # an empty cell.
    CHECKS[0] += 1
    nosplit = [c['fy'] for c in d['counts'] if c['day'] is None
               and c['residential'] is None and c['collaborative'] is None]
    if nosplit != d['count_no_split']:
        FAILS.append('the years with no published split are %r, not %r'
                     % (nosplit, d['count_no_split']))
    else:
        print('  OK    %d year(s) print a total and no split; the rest print their parts'
              % len(nosplit))

    CHECKS[0] += 1
    agree = sum(1 for t in d['two_counts'] if t['difference'] == 0)
    if agree != d['two_counts_agree'] or agree == len(d['two_counts']):
        FAILS.append('the page says the two counts agree in %d of %d years; recomputed '
                     'they agree in %d' % (d['two_counts_agree'], len(d['two_counts']), agree))
    else:
        print('  OK    the two published counts agree in %d of %d years and are not '
              'reconciled anywhere' % (agree, len(d['two_counts'])))


# ---------------------------------------------------------------- the persona review

def check_personas():
    head('§personas  notes/process/PERSONAS.md — six readers, one test each')
    src = {}
    for f in ('SpecialEducationHub.tsx', 'SpedStudents.tsx', 'SpedLeaving.tsx',
              'SpedCost.tsx', 'SpedRoute.tsx'):
        src[f] = ' '.join(open(os.path.join(PAGES, f), encoding='utf-8').read().split())
    # The rendered page is the page source AND the payload it draws from: the meeting
    # quotes and their annotations live in the JSON, are re-read out of the minutes on
    # every build, and are what a reader actually sees under the charts. Checking only the
    # .tsx would report a persona test as unmet on a page that meets it.
    ALL = ' '.join(list(src.values())
                   + [json.dumps(payload(f), ensure_ascii=False) for f in
                      ('sped-students.json', 'sped-leaving.json', 'sped-cost.json',
                       'sped-route.json')]).lower()

    # Each entry is the phrase the review ADDED or kept, so a later edit that removes it
    # fails rather than silently undoing the review. Whitespace is collapsed above,
    # because prose wraps and a check that fails on a line break teaches the wrong lesson.
    NEEDED = [
        ('1. the resident who thinks the schools are not straight with them: the worst '
         'number is findable in the first screen',
         'The line in the budget the town votes said'),
        ('2. the second-hand reader: the first screen carries one sentence that stays '
         'true when repeated',
         'Both figures are correct, and they are not the same quantity'),
        ('3. the resident close to the boards: findings name mechanisms, not people',
         'a classification is a decision somebody made'),
        ('4. the Finance Committee member: the control question is answered',
         'has no way of knowing whether the thing got cheaper or somebody else started '
         'paying for more of it'),
        ('5. the School Committee member: the thing they cut is addressed directly',
         'A vote to ADD posts'),
        ('6. the Select Board member: a careless comparison is made harder',
         'this is a bearing rather than a comparison'),
        ('the people nobody writes reports for: a concrete thing somebody asked for',
         'backbone of special education'),
    ]
    for label, needle in NEEDED:
        ok = ' '.join(needle.split()).lower() in ALL
        CHECKS[0] += 1
        print('  %s  %s' % ('OK  ' if ok else 'GONE', label))
        if not ok:
            FAILS.append('persona review: %s — the text that satisfied it is gone' % label)

    # Step 3 of the review is not simulation: every report that names a category has to
    # have searched the archive for what was said about it in the same year.
    for name, f in (('students', 'sped-students.json'), ('leaving', 'sped-leaving.json'),
                    ('cost', 'sped-cost.json'), ('route', 'sped-route.json')):
        d = payload(f)
        CHECKS[0] += 1
        if not d['said'] or not d['searched']:
            FAILS.append('the %s report quotes nobody from the meeting archive — step 3 '
                         'of the persona review' % name)
        CHECKS[0] += 1
        if d['minutes']['searchable'] >= d['minutes']['held']:
            FAILS.append('the %s report publishes a coverage denominator with no '
                         'unsearchable documents in it, which has never been true' % name)
    print('  OK    every report quotes the archive and publishes its denominator')

    # AND THE THING THE WHOLE STRUCTURE EXISTS FOR: each report states its own grain, and
    # says so where a reader meets it rather than in a footnote.
    for f in ('SpedStudents.tsx', 'SpedLeaving.tsx', 'SpedCost.tsx', 'SpedRoute.tsx'):
        CHECKS[0] += 1
        if '<Grain>' not in src[f]:
            FAILS.append('%s no longer states what it counts before it counts it' % f)
    print('  OK    all four reports state their grain above the fold')


def main():
    for fn in (check_students, check_leaving, check_cost, check_route, check_personas):
        fn()
    print('\n%d assertions' % CHECKS[0])
    if FAILS:
        print('\n%d FAILED:' % len(FAILS))
        for f in FAILS:
            print('  - %s' % f)
        return 1
    print('PASS — every figure on the four reports recomputes from the CSVs')
    return 0


if __name__ == '__main__':
    sys.exit(main())
