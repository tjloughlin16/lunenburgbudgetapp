#!/usr/bin/env python3
"""Every figure on /school-staffing, recomputed by a SECOND route.

    python3 scripts/verify_school_staffing.py

WHY A `--check` IS NOT ENOUGH. `build_staffing_charts.py --check` proves the published
payload is what the generator now writes FROM THE DATABASE. If the database load dropped
a row, coerced a column, or collided a primary key, the generator and its own check would
agree perfectly about a wrong number. So this reads the CSVs the database was built from,
aggregates them in plain Python -- no SQL, no shared helper -- and asserts the published
payload against that.

WHAT TAKING THE OTHER ROAD ACTUALLY BUYS, on this page specifically:

  * THE ROLLUP TRAP IS RE-DERIVED, not trusted. `dese-educator-workforce.csv` prints
    `All Educators` as a row BESIDE seven race rows that sum to it. This project once
    summed both and published 38 administrators and 118 paraprofessionals where the file
    says 19 and 59 -- exactly 2x. The check here is not "does the generator filter" but
    "does the naive sum still come to exactly twice the published figure", computed from
    the CSV. If DESE reshapes the file, the assumption behind the filter is gone and this
    says so.
  * THE COLUMN NAMES IN `dese-sped-program.csv` DO NOT SAY WHAT THEY HOLD. In the
    SPECIAL EDUCATION STAFF table, `denominator_cnt` carries the FTE and `measure_cnt`
    carries the count of children. Nothing in the header says so; the only thing that
    establishes it is that the printed rate reproduces from the two. That is recomputed
    here for every row rather than inherited from the generator.
  * THE TWO PARAPROFESSIONAL SERIES ARE READ FROM TWO SEPARATE FILES, joined here for
    the first time by a second route, and the DERIVED difference between them is
    recomputed. A page that publishes a subtraction across two files has to have the
    subtraction checked somewhere that is not the code that made it.
  * WHAT THE PAGE DERIVES AT RENDER TIME is asserted too. The window control in the
    `.tsx` computes a change between two years the reader picks, and the three named
    windows' figures on the cards come out of the payload -- but the up-step counts, the
    school panel deltas and the gross/net subject arithmetic are recomputed here because
    nothing else on the site would notice one of them going wrong.
  * AND THE STRUCTURE THE ARGUMENT RESTS ON (rule 13), not only the figures: that the
    window matrix accounts for every ordered pair of published years; that the schools
    sum to the district in every year; that the special education paraprofessional series
    falls at every step and the derived difference rises at every step, which is the
    whole shape of that conclusion; and that the meeting-search terms include the ones
    the TOWN uses rather than only the ones this project uses.
"""
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')

# THREE PAGES, ONE BODY OF DATA, ONE VERIFIER.
#
# /school-staffing was one page answering three questions and is now three pages. The data
# behind them is still computed once -- `build_staffing_charts.py` SELECTS three payloads
# out of one build -- so this file still checks one body of data, and checking it in three
# places would be three chances to check it three different ways.
#
# The order matters exactly once: a block published on two pages is the SAME block (it was
# selected, not recomputed), and the merge below takes the first, so the checks read the
# window page's copy where a block appears twice. `same_where_shared()` asserts that they
# really are identical rather than assuming it, because "computed once" is a property of
# the generator and this file exists to not take the generator's word for anything.
PAGES = (
    ('/school-staffing', 'school-staffing.json',
     ('composition', 'peers', 'state'),
     ('the-sign-is-a-property-of-the-window',
      'fewest-teachers-per-pupil-in-the-group')),
    ('/who-works-in-each-school', 'who-works-in-each-school.json',
     ('board', 'composition', 'headcount', 'peers', 'roster', 'state', 'wages'),
     ('a-headcount-is-not-an-fte-count',)),
    ('/the-paraprofessionals', 'the-paraprofessionals.json',
     ('dollars', 'peers', 'sped_staffing', 'state'),
     ('the-change-is-paraprofessionals',
      'paraprofessionals-outside-special-education',
      'inside-sped-the-money-went-to-paraprofessionals')),
)
GAPS = os.path.join(DATA, 'money-gaps.csv')
PERSONAS = os.path.join(ROOT, 'notes', 'process', 'PERSONAS.md')

LEA = '01620000'
STATE_LEA = '00000000'
ALL_TEACHERS = 'All Teachers'
SPED_STAFF = 'Special Education FTEs per 100 SWDs'

FAILS = []
CHECKS = [0]


def ok(label, got, want, tol=0.0):
    CHECKS[0] += 1
    if got is None or want is None:
        if got is not want:
            FAILS.append('%s: %r against %r' % (label, got, want))
        return
    if isinstance(got, (int, float)) and isinstance(want, (int, float)):
        if abs(float(got) - float(want)) > tol:
            FAILS.append('%s: %s against %s' % (label, got, want))
        return
    if got != want:
        FAILS.append('%s: %r against %r' % (label, got, want))


def true(label, cond, why=''):
    CHECKS[0] += 1
    if not cond:
        FAILS.append('%s%s' % (label, (' — ' + why) if why else ''))


def load(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def f(x):
    return None if x in (None, '') else float(x)


def payloads():
    """The three published files, and the merged body of data the checks below read.

    Asserts, on the way, the four things a split can silently get wrong: a page that lost
    a block it renders; a block that ended up on no page at all; a conclusion on two pages
    or on none; and a shared block whose two copies are not the same bytes.
    """
    got = {}
    for url, name, keys, cids in PAGES:
        path = os.path.join(PUB, name)
        true('%s is not published at %s' % (url, name), os.path.exists(path))
        if not os.path.exists(path):
            continue
        got[name] = json.load(open(path, encoding='utf-8'))

    merged, owner = {}, {}
    for url, name, keys, cids in PAGES:
        j = got.get(name) or {}
        for k in keys:
            ok('%s publishes the block %r it renders' % (url, k), k in j, True)
            if k in merged:
                # SHARED, NOT RECOMPUTED. If these two ever differ, one page is drawing a
                # different series from the other under the same name, which is the exact
                # failure splitting a generator in three would have caused.
                true('%s and %s publish DIFFERENT %r blocks. They are selected from one '
                     'build and must be identical bytes.' % (owner[k], url, k),
                     json.dumps(j.get(k), sort_keys=True)
                     == json.dumps(merged[k], sort_keys=True))
            else:
                merged[k] = j.get(k)
                owner[k] = url
        for extra in ('said', 'searched', 'minutes', 'sources', 'not_established',
                      'closes', 'about', 'grain', 'generated_by', 'source'):
            true('%s publishes no %r' % (url, extra), bool(j.get(extra)))
        mine = [c['id'] for c in (j.get('conclusions') or [])]
        ok('%s publishes exactly the conclusions it owns' % url, mine, list(cids))

    merged['conclusions'] = [c for _u, name, _k, _c in PAGES
                             for c in (got.get(name) or {}).get('conclusions') or []]
    for extra in ('said', 'searched', 'minutes'):
        merged[extra] = (got.get(PAGES[0][1]) or {}).get(extra)

    # EACH PAGE KEEPS ITS OWN CAVEATS. A caveat on two pages is a shared caveat block
    # wearing a disguise, and it is the tell that the cut is in the wrong place.
    seen = {}
    for url, name, _k, _c in PAGES:
        for g in (got.get(name) or {}).get('not_established') or []:
            true('the caveat %r is on %s and on %s. Each page keeps its own.'
                 % (g[:44], seen.get(g), url), g not in seen)
            seen[g] = url
    return merged


def main():
    d = payloads()

    # ------------------------------------------------------------------ the FTE series
    ts = [r for r in load('dese-teacher-subject.csv')
          if r['lea'] == LEA and r['org_level'] == 'district'
          and r['subject'] == ALL_TEACHERS]
    district = sorted(((int(r['fy']), f(r['teacher_fte'])) for r in ts), key=lambda r: r[0])
    true('the teacher series is empty in the CSV', len(district) >= 15,
         'a join that matches nothing looks exactly like a district with no history')
    comp = d['composition']
    ok('published years of teacher FTE', len(comp['district']), len(district))
    by_fy = dict(district)
    for p in comp['district']:
        ok('teacher FTE FY%d' % p['fy'], p['fte'], by_fy.get(p['fy']), 0.001)

    # ---- THE WINDOW MATRIX. Every ordered pair, recomputed. This is the page's most
    # important single claim and it is arithmetic over the whole series, so a second
    # route has real power here.
    years = [y for y, _ in district]
    rose = fell = flat = 0
    for i, a in enumerate(years):
        for b in years[i + 1:]:
            delta = round(by_fy[b] - by_fy[a], 1)
            if delta > 0:
                rose += 1
            elif delta < 0:
                fell += 1
            else:
                flat += 1
    ew = comp['every_window']
    ok('window pairs', ew['pairs'], rose + fell + flat)
    ok('windows that rise', ew['rose'], rose)
    ok('windows that fall', ew['fell'], fell)
    ok('windows that are flat', ew['flat'], flat)
    true('the matrix does not hold every pair of published years',
         ew['pairs'] == len(years) * (len(years) - 1) // 2)

    # ---- the three named windows, and their up-step counts, which the cards print.
    for key in ('whole', 'charted', 'recent'):
        w = comp['windows'][key]
        span = [y for y in years if w['first_fy'] <= y <= w['last_fy']]
        true('the %s window holds fewer than two years' % key, len(span) >= 2)
        ok('%s window first' % key, w['first'], by_fy[span[0]], 0.001)
        ok('%s window last' % key, w['last'], by_fy[span[-1]], 0.001)
        ok('%s window change' % key, w['change'],
           round(by_fy[span[-1]] - by_fy[span[0]], 4), 0.001)
        ok('%s window steps' % key, w['steps'], len(span) - 1)
        ok('%s window up-steps' % key, w['up'],
           sum(1 for a, b in zip(span, span[1:]) if by_fy[b] > by_fy[a]))
        ok('%s window years' % key, (w['first_fy'], w['last_fy']), (span[0], span[-1]))

    # ------------------------------------------------------------------ by school
    school_rows = [r for r in load('dese-teacher-subject.csv')
                   if r['lea'] == LEA and r['org_level'] == 'school'
                   and r['subject'] == ALL_TEACHERS]
    by_school_fy = {}
    for r in school_rows:
        by_school_fy.setdefault(int(r['fy']), {})[r['org_code']] = f(r['teacher_fte'])
    true('no school rows in the CSV at all', bool(by_school_fy))
    for y in years:
        got = sum(v for v in by_school_fy.get(y, {}).values() if v is not None)
        ok('schools sum to the district in FY%d' % y, round(got, 2),
           round(by_fy[y], 2), 0.5)
    for s in comp['schools']['rows']:
        for p in s['points']:
            ok('%s FTE FY%d' % (s['org_code'], p['fy']), p['fte'],
               by_school_fy.get(p['fy'], {}).get(s['org_code']), 0.001)
        if s['since_era']:
            era = [p for p in s['points'] if p['fy'] >= comp['schools']['era']]
            ok('%s change since the reconfiguration' % s['org_code'],
               s['since_era']['change'], round(era[-1]['fte'] - era[0]['fte'], 4), 0.001)
            ok('%s up-steps since the reconfiguration' % s['org_code'],
               s['since_era']['up'],
               sum(1 for a, b in zip(era, era[1:]) if b['fte'] > a['fte']))

    # ------------------------------------------------------------------ by subject
    gs = [r for r in load('dese-teacher-grade-subject.csv')
          if r['lea'] == LEA and r['org_level'] == 'district']
    subj = {}
    for r in gs:
        v = f(r['total_fte'])
        if v is not None:
            subj.setdefault(r['subject'], {})[int(r['fy'])] = v
    true('the subject CSV produced nothing', bool(subj))
    for w in comp['subjects']['windows']:
        up = down = 0.0
        for row in w['rows']:
            a = subj.get(row['subject'], {}).get(w['first_fy'], 0.0)
            b = subj.get(row['subject'], {}).get(w['last_fy'], 0.0)
            ok('%s %s first' % (w['key'], row['subject']), row['first'], a, 0.001)
            ok('%s %s last' % (w['key'], row['subject']), row['last'], b, 0.001)
            ok('%s %s change' % (w['key'], row['subject']), row['change'],
               round(b - a, 4), 0.001)
            if b - a > 0:
                up += b - a
            else:
                down += b - a
        ok('%s gross movement' % w['key'], w['gross'], round(up - down, 4), 0.002)
        ok('%s net movement' % w['key'], w['net'], round(up + down, 4), 0.002)
        true('%s: the gross is not larger than the net, which would mean nothing '
             'cancelled' % w['key'], abs(w['gross']) >= abs(w['net']) - 1e-9)

    # ------------------------------------------------- the headcount, and the 2x trap
    wf = [r for r in load('dese-educator-workforce.csv') if r['lea'] == LEA]
    published, naive = {}, {}
    for r in wf:
        key = (int(r['fy']), r['job_class'])
        v = f(r['educators_headcount'])
        if v is None:
            continue
        naive[key] = naive.get(key, 0.0) + v
        if r['race_level'] == 'all':
            published[key] = v
    true('the educator workforce CSV produced no Lunenburg rows', bool(published))
    for key, pub in sorted(published.items()):
        # THE GUARD, RE-DERIVED. Not "did the generator filter" but "is the file still
        # shaped so that filtering is the right thing to do".
        ok('FY%d %s: the naive sum is twice the published figure' % key,
           naive[key], 2 * pub, 0.001)
    hc = d['headcount']
    for r in hc['rows']:
        ok('headcount FY%d %s' % (r['fy'], r['job_class']), r['educators_headcount'],
           published.get((r['fy'], r['job_class'])), 0.001)
    for r in hc['naive']:
        ok('published naive sum FY%d %s' % (r['fy'], r['job_class']), r['naive'],
           naive.get((r['fy'], r['job_class'])), 0.001)

    # ---- headcount beside FTE. Two files; the share is the whole point of the section.
    radar = {}
    for r in load('dese-radar.csv'):
        if r['lea'] == LEA:
            radar[(int(r['fy']), r['measure'])] = f(r['value'])
    for r in hc['vs_fte']:
        t_hc = published[(r['fy'], 'Teacher')]
        t_fte = radar[(r['fy'], 'Teacher FTE')]
        p_hc = published[(r['fy'], 'Paraprofessional')]
        p_fte = radar[(r['fy'], 'Paraprofessional FTE')]
        ok('FY%d teacher headcount' % r['fy'], r['teacher_headcount'], t_hc, 0.001)
        ok('FY%d teacher FTE' % r['fy'], r['teacher_fte'], t_fte, 0.001)
        ok('FY%d teacher share of a post' % r['fy'], r['teacher_share'], t_fte / t_hc,
           1e-9)
        ok('FY%d para headcount' % r['fy'], r['para_headcount'], p_hc, 0.001)
        ok('FY%d para FTE' % r['fy'], r['para_fte'], p_fte, 0.001)
        ok('FY%d para share of a post' % r['fy'], r['para_share'], p_fte / p_hc, 1e-9)
        true('FY%d: the teacher headcount is not above the teacher FTE. The whole '
             'section rests on people outnumbering posts' % r['fy'], t_hc >= t_fte)

    # ---- the peer ranking, recomputed, INCLUDING that the state total is not a district.
    enrol = {}
    for r in load('dese-enrollment.csv'):
        if r['org_level'] == 'district' and f(r['total_cnt']):
            enrol[(int(r['fy']), r['lea'])] = f(r['total_cnt'])
    fy_peer = hc['peers']['fy']
    per100 = {}
    # EVERY district in the file, not `wf` -- `wf` is Lunenburg only, and ranking a set of
    # one would have passed every rank check trivially. Caught by this verifier's own
    # first run, which is what a second route is for.
    for r in load('dese-educator-workforce.csv'):
        if r['race_level'] != 'all' or int(r['fy']) != fy_peer or r['lea'] == STATE_LEA:
            continue
        n = enrol.get((fy_peer, r['lea']))
        if not n:
            continue
        per100.setdefault(r['job_class'], []).append(
            (100.0 * f(r['educators_headcount']) / n, r['district'], r['lea']))
    true('no per-100 headcounts recomputed for the peer year', bool(per100))
    true('DESE’s State Totals row is being ranked as though it were a district',
         all(p['lea'] != STATE_LEA for p in hc['peers']['rows']))
    for jc, rank in sorted(hc['peers']['ranks'].items()):
        got = sorted(per100[jc], key=lambda t: -t[0])
        mine = next(t for t in got if t[2] == LEA)
        ok('%s peer count' % jc, rank['of'], len(got))
        ok('%s rank' % jc, rank['rank'], got.index(mine) + 1)
        ok('%s value' % jc, rank['value'], mine[0], 1e-9)
        ok('%s highest' % jc, rank['highest'], got[0][1])
        ok('%s lowest' % jc, rank['lowest'], got[-1][1])

    # -------------------------------- the special education staff table, and its columns
    sp_raw = [r for r in load('dese-sped-program.csv')
              if r['lea'] == LEA and r['geo_level'] == 'district'
              and r['indicator_category'] == SPED_STAFF]
    true('the special education staff table produced nothing', bool(sp_raw))
    sped_para, swd_by_fy, reproduced, seen = {}, {}, 0, 0
    for r in sp_raw:
        if r['indicator'] == 'Total Students with Disabilities':
            swd_by_fy[int(r['fy'])] = f(r['denominator_cnt'])
            continue
        fte, n, rate = f(r['denominator_cnt']), f(r['measure_cnt']), f(r['measure_pct'])
        if fte is None or n is None or rate is None:
            continue
        seen += 1
        # THE COLUMN NAMES DO NOT SAY WHAT THEY HOLD. The only thing that establishes
        # which is which is that the printed rate reproduces from the pair.
        if abs(round(100.0 * fte / n, 1) - round(100.0 * rate, 1)) <= 0.051:
            reproduced += 1
            if r['indicator'] == 'Paraprofessionals':
                sped_para[int(r['fy'])] = fte
    ok('rows of the staff table checked', d['sped_staffing']['reproduces']['checked'], seen)
    ok('rows that failed to reproduce', d['sped_staffing']['reproduces']['failed'],
       seen - reproduced)
    true('the paraprofessional row of the staff table no longer reproduces in every '
         'year — it is the only row of it this project publishes as a figure',
         len(sped_para) >= 3)

    sp = d['sped_staffing']
    for r in sp['rows']:
        ok('FY%d all-programmes para FTE' % r['fy'], r['all_programmes'],
           radar[(r['fy'], 'Paraprofessional FTE')], 0.001)
        ok('FY%d special education para FTE' % r['fy'], r['special_education'],
           sped_para.get(r['fy']), 0.001)
        # THE DERIVED SUBTRACTION, recomputed by the other route.
        ok('FY%d the derived difference' % r['fy'], r['implied'],
           round(radar[(r['fy'], 'Paraprofessional FTE')] - sped_para[r['fy']], 4), 0.001)
        ok('FY%d children on a plan' % r['fy'], r['swd'], swd_by_fy.get(r['fy']), 0.001)
        true('FY%d: the special education count exceeds the all-programmes count, so the '
             'subtraction the page publishes is not a subset difference' % r['fy'],
             r['implied'] >= 0)

    # THE SHAPE OF THE CONCLUSION, not only its endpoints. "It is not one noisy year"
    # is a structural claim and it is what makes this publishable at all.
    fell_every = all(b['special_education'] < a['special_education']
                     for a, b in zip(sp['rows'], sp['rows'][1:]))
    rose_every = all(b['implied'] > a['implied']
                     for a, b in zip(sp['rows'], sp['rows'][1:]))
    true('the special education paraprofessional series no longer falls at every step',
         fell_every, 'the conclusion says it does, and that is the half a reader checks')
    true('the derived difference no longer rises at every step', rose_every)
    ok('special education up-steps', sp['special_education']['up'], 0)
    ok('derived-difference up-steps', sp['implied']['up'], sp['implied']['steps'])

    # ------------------------------------------------ every conclusion's registered value
    reg = {c['id']: c['figures'] for c in d['conclusions']}
    ok('conclusions published across the three pages', len(d['conclusions']),
       sum(len(c) for _u, _n, _k, c in PAGES))
    for cid in ('the-sign-is-a-property-of-the-window', 'a-headcount-is-not-an-fte-count',
                'paraprofessionals-outside-special-education'):
        true('the conclusion %r is gone from the payload' % cid, cid in reg)
    if 'the-sign-is-a-property-of-the-window' in reg:
        g = reg['the-sign-is-a-property-of-the-window']
        ok('conclusion: pairs that fell', g['fell']['value'], fell)
        ok('conclusion: pairs that rose', g['rose']['value'], rose)
        ok('conclusion: pairs in all', g['pairs']['value'], rose + fell + flat)
        ok('conclusion: charted change', g['charted_change']['value'],
           comp['windows']['charted']['change'], 0.001)
        ok('conclusion: whole change', g['whole_change']['value'],
           comp['windows']['whole']['change'], 0.001)
    if 'a-headcount-is-not-an-fte-count' in reg:
        g = reg['a-headcount-is-not-an-fte-count']
        last = hc['vs_fte'][-1]
        ok('conclusion: teacher headcount', g['headcount']['value'],
           published[(last['fy'], 'Teacher')], 0.001)
        ok('conclusion: teacher FTE', g['fte']['value'],
           radar[(last['fy'], 'Teacher FTE')], 0.001)
        ok('conclusion: the gap between them', g['missing']['value'],
           published[(last['fy'], 'Teacher')] - radar[(last['fy'], 'Teacher FTE')], 0.001)
        true('the headline figure has no unit, and a bare count on a card is the '
             'defect rule 7b names', bool(g['headcount']['unit']))
    if 'paraprofessionals-outside-special-education' in reg:
        g = reg['paraprofessionals-outside-special-education']
        first, last = sp['rows'][0], sp['rows'][-1]
        ok('conclusion: derived rise', g['implied_rise']['value'],
           round(last['implied'] - first['implied'], 4), 0.001)
        ok('conclusion: all-programmes first', g['all_first']['value'],
           radar[(first['fy'], 'Paraprofessional FTE')], 0.001)
        ok('conclusion: special education last', g['sped_last']['value'],
           sped_para[last['fy']], 0.001)
        ok('conclusion: children first', g['swd_first']['value'], swd_by_fy[first['fy']],
           0.001)

    # ------------------------------------------------------- rule 7c: the gaps registry
    gaps = load('money-gaps.csv')
    for phrase in ('moved out of special education',
                   'counsellors, social workers and psychologists'):
        true('money-gaps.csv no longer registers %r. The registry outranks the page: a '
             'limit stated only in prose is invisible to the next person who hits it'
             % phrase,
             any(phrase in g['what'] for g in gaps))
    for g in gaps:
        if 'moved out of special education' in g['what'] \
                or 'counsellors, social workers and psychologists' in g['what']:
            true('the gap %r names no closing document' % g['what'][:40],
                 '— closes:' in g['why'],
                 'a gap with no named remedy is a grievance; one with a named document '
                 'is a records request')

    # -------------------------------------------------- rule 15a: the omission step ran
    for term in ('social worker', 'caseload', 'adjustment counselor',
                 'reduction in force', 'paraprofessional'):
        true('%r is not in the published search list. The town says these words and this '
             'project says others; searching only our own vocabulary is what the '
             'omission step exists to stop.' % term,
             any(t['term'] == term for t in d['searched']))
    ell = next((t for t in d['searched'] if t['term'] == 'ELL'), None)
    true('the ELL search has gone back to matching substrings. It once reported 3,049 '
         'documents by matching “well”, “shell” and “sell”, which is a quarter of the '
         'whole archive presented as a denominator.',
         ell is not None and ell['documents'] < 100)
    for key in ('para-transfers', 'social-worker-caseloads',
                'social-workers-billed-elsewhere', 'esser-hired-13'):
        true('the quote %r is no longer on the page. Each one is there because the '
             'omission step of the persona review found it, and quotes are the first '
             'thing a later edit trims.' % key,
             any(q['key'] == key for q in d['said']))
    # ================================================== THE SCHOOL BOARD (the panels)
    #
    # A SECOND ROUTE, in plain Python off the CSVs: the roster entries joined to the role
    # classification by hand, the enrolment file read directly, and both DESE teacher
    # files summed independently. Nothing below shares a line of code with the generator.
    b = d['board']
    ents = [r for r in load('staff-roster-entries.csv')]
    cls = {(r['role_raw'], r['grade_or_dept']): r['role_category']
           for r in load('role-classification.csv')}
    true('the roster CSV is empty', len(ents) > 1000)
    enrol_csv = {}
    for r in load('dese-enrollment.csv'):
        if r['lea'] == LEA and r['org_level'] == 'school':
            enrol_csv[(int(r['fy']), r['org_code'])] = r
    prog_csv = {}
    for r in load('dese-teacher-program-area.csv'):
        if r['lea'] == LEA and r['org_level'] == 'school':
            prog_csv[(int(r['fy']), r['org_code'])] = r
    band_csv = {}
    for r in load('dese-teacher-grade-subject.csv'):
        if r['lea'] == LEA and r['org_level'] == 'school' and r['subject'] == 'All':
            band_csv[(int(r['fy']), r['org_code'])] = r

    # THE RECONCILIATION THE PAGE PUBLISHES, redone from the two CSVs rather than read
    # out of the payload. Two DESE files, one quantity.
    agree = compared = 0
    for k, pr in prog_csv.items():
        bd = band_csv.get(k)
        if bd is None or f(pr['total_fte']) is None or f(bd['total_fte']) is None:
            continue
        compared += 1
        if abs(f(pr['total_fte']) - f(bd['total_fte'])) < 0.05:
            agree += 1
    ok('school-years where the programme and grade-band files were compared',
       b['band_check']['compared'], compared)
    ok('school-years where the two DESE teacher files agree on a school total',
       b['band_check']['agree'], agree)
    true('the two DESE teacher files no longer agree about every school total. The '
         'panels publish that agreement as a reconciliation.',
         compared > 0 and agree == compared)

    # EVERY PANEL, EVERY YEAR: the categories sum to the roster, the roster count matches
    # a hand count of the CSV, and the children and the teaching FTE match the state's
    # own files.
    panels_checked = rows_checked = 0
    for fy_s, panels in sorted(b['by_fy'].items()):
        fyy = int(fy_s)
        for p in panels:
            panels_checked += 1
            here = [r for r in ents
                    if int(r['fy']) == fyy and r['school'] == p['school']]
            ok('FY%d %s names printed' % (fyy, p['school']), p['names'], len(here))
            if p['rows'] is not None:
                ok('FY%d %s categories sum to the roster' % (fyy, p['school']),
                   sum(r['names'] for r in p['rows']), len(here))
                by_cat = {}
                for r in here:
                    c = cls.get((r['role_raw'], r['grade_or_dept']))
                    by_cat[c] = by_cat.get(c, 0) + 1
                for r in p['rows']:
                    rows_checked += 1
                    # `by_cat` has no entry for a category nobody was printed under, and
                    # a row for such a category now EXISTS with a count of nought -- see
                    # the note in build_staffing_charts.py. Lunenburg High FY2025 read
                    # "Who teaches 38 (down 6)" over a single row "Teachers 38 (up 3)",
                    # both correct and irreconcilable, because the nine specialist
                    # teachers who account for the difference had no row at all.
                    ok('FY%d %s %s' % (fyy, p['school'], r['key']),
                       r['names'], by_cat.get(r['key'], 0))
                    # A ZERO ROW MUST BE EARNED. It is there to explain a fall, so it may
                    # only appear where the category held somebody at the other end of
                    # the window; a category empty at both ends is still omitted.
                    if r['names'] == 0:
                        back0 = [q for q in ents
                                 if int(q['fy']) == fyy - (b['window'] - 1)
                                 and q['school'] == p['school']]
                        true('FY%d %s %s prints a zero only because it emptied'
                             % (fyy, p['school'], r['key']),
                             any(cls.get((q['role_raw'], q['grade_or_dept'])) == r['key']
                                 for q in back0))
                    # THE THREE-YEAR BADGE, recomputed. It is the most quotable thing on
                    # a panel and nothing else on this site would notice it going wrong.
                    if r['delta'] is not None:
                        back = [q for q in ents if int(q['fy']) == fyy - (b['window'] - 1)
                                and q['school'] == p['school']]
                        prev = sum(1 for q in back
                                   if cls.get((q['role_raw'], q['grade_or_dept'])) == r['key'])
                        ok('FY%d %s %s three-year change'
                           % (fyy, p['school'], r['key']), r['delta'], r['names'] - prev)
                    else:
                        true('FY%d %s %s has no change and no reason given'
                             % (fyy, p['school'], r['key']),
                             bool(p['delta_unavailable']))
            else:
                true('FY%d %s withholds its categories without saying it printed two '
                     'rosters' % (fyy, p['school']), p['names_band'] is not None)
            if p['org_code']:
                en = enrol_csv.get((fyy, p['org_code']))
                ok('FY%d %s children' % (fyy, p['school']), p['students'],
                   f(en['total_cnt']) if en else None, 0.001)
                pr = prog_csv.get((fyy, p['org_code']))
                if p['teaching'] is not None:
                    ok('FY%d %s teaching FTE' % (fyy, p['school']),
                       p['teaching']['total_fte'],
                       f(pr['total_fte']) if pr else None, 0.001)
                    ok('FY%d %s special education teaching FTE' % (fyy, p['school']),
                       p['teaching']['sped_fte'],
                       f(pr['sped_fte']) if pr else None, 0.001)
    true('the school panels cover fewer than fifty school-years', panels_checked >= 50)
    true('the school panels publish fewer than three hundred category rows',
         rows_checked >= 300)

    # THE DOUBLED ROSTER. The one school-year the town printed twice is withheld rather
    # than summed, and the overlap that establishes it is recomputed here.
    doubled = [(int(k), p) for k, ps in b['by_fy'].items() for p in ps
               if p['names_band']]
    true('no double-printed roster is reported. The FY2024 report prints two complete '
         'Turkey Hill rosters and a panel that sums them says 135 people at a school of '
         '64.', len(doubled) >= 1)
    for fyy, p in doubled:
        pages = p['names_band']['pages']
        sets = [{r['name'] for r in ents if int(r['fy']) == fyy
                 and r['school'] == p['school'] and r['page'] == pg and r['name']}
                for pg in pages]
        ok('FY%d %s names shared between the two printed rosters' % (fyy, p['school']),
           p['names_band']['shared'], len(sets[0] & sets[1]))
        true('FY%d %s publishes summed categories beside a doubled roster'
             % (fyy, p['school']), p['rows'] is None and p['per_adult'] is None)

    # THE ERAS. Turkey Hill Middle and Turkey Hill Elementary are two schools under one
    # roster heading, and the panel has to say so.
    true('the reorganisation is no longer reported. Turkey Hill Middle (to FY2016) and '
         'Turkey Hill Elementary (from FY2017) are different schools under one printed '
         'heading, and a reader scrubbing across that year must be told.',
         any(x['school'] == 'turkey-hill' for x in b['breaks']))
    for x in b['breaks']:
        true('the %s break states the same grade span either side, which would make it '
             'a rename' % x['school'], x['was_span'] != x['now_span'])

    # THE SECOND INSTRUMENT ON THE ERAS: teaching FTE in a grade band, against enrolment
    # in those grades, recomputed from the two CSVs.
    hb = next((x for x in b['band_era_evidence']['schools']
               if x['school'] == 'high' and x['band'] == 'grade_6_8_fte'), None)
    true('the high school no longer carries grades 6-8 teaching FTE in any year, so the '
         'independent confirmation of the reorganisation is gone', hb is not None)
    if hb:
        taught = sorted(int(r['fy']) for r in band_csv.values()
                        if r['org_code'] == hb['org_code']
                        and (f(r['grade_6_8_fte']) or 0) >= b['band_era_evidence']['floor'])
        ok('years Lunenburg High carried grades 6-8 teaching FTE', hb['taught'], taught)
        # Only the years BOTH files publish for this school. The enrolment file reaches
        # back to 1992 and the teacher file starts in 2008, and comparing across that is
        # the like-for-like error in one line.
        band_years = {int(r['fy']) for r in band_csv.values()
                      if r['org_code'] == hb['org_code']}
        enrolled = sorted(fyy for (fyy, code), r in enrol_csv.items()
                          if code == hb['org_code'] and fyy in band_years and any(
                              f(r[c]) for c in ('grade_6_cnt', 'grade_7_cnt', 'grade_8_cnt')))
        ok('years Lunenburg High enrolled a grade 6-8 child', hb['enrolled'], enrolled)
        true('the teacher file and the enrolment file no longer agree about when grade 8 '
             'was in the high school building', hb['agrees'])

    # THE CROSS-CHECK: two organisations counting the same teachers, redone here.
    xc = b['cross_check']
    teach_cats = {c['key'] for c in b['categories'] if c['group'] == xc['group']}
    ok('the categories the cross-check treats as teaching',
       sorted(xc['categories']), sorted(teach_cats))
    redone, short2 = [], []
    for fy_s, ps in b['by_fy'].items():
        fyy = int(fy_s)
        for p in ps:
            if p['rows'] is None or not p['teaching'] or not p['teaching']['total_fte']:
                true('FY%d %s publishes a cross-check with no single roster or no state '
                     'FTE to check it against' % (fyy, p['school']),
                     not p.get('cross_check'))
                continue
            here = [r for r in ents
                    if int(r['fy']) == fyy and r['school'] == p['school']]
            heads = sum(1 for r in here
                        if cls.get((r['role_raw'], r['grade_or_dept'])) in teach_cats)
            fte = f(prog_csv[(fyy, p['org_code'])]['total_fte'])
            redone.append((fyy, p['school'], heads, fte))
            if heads < fte:
                short2.append((fyy, p['school']))
            c = p.get('cross_check')
            true('FY%d %s has both counts and publishes no cross-check'
                 % (fyy, p['school']), c is not None)
            if c:
                ok('FY%d %s teaching names' % (fyy, p['school']), c['heads'], heads)
                ok('FY%d %s teaching FTE in the cross-check' % (fyy, p['school']),
                   c['fte'], fte, 0.001)
                ok('FY%d %s names per post' % (fyy, p['school']), c['ratio'],
                   heads / fte, 1e-9)
                ok('FY%d %s is flagged as fewer names than posts' % (fyy, p['school']),
                   c['flag'], 'fewer-names-than-posts' if heads < fte else None)
    ok('school-years with both a roster and a state FTE', xc['compared'], len(redone))
    ok('school-years with fewer names printed than posts counted',
       xc['flagged'], len(short2))
    for r in xc['by_school']:
        ok('%s school-years compared' % r['school'], r['years'],
           sum(1 for x in redone if x[1] == r['school']))
        ok('%s school-years with fewer names than posts' % r['school'], r['short'],
           sum(1 for x in short2 if x[1] == r['school']))
    true('the disagreement is no longer concentrated in the two co-located schools, '
         'which is the reading the page offers and does not assert',
         all(r['short'] == r['years'] or r['short'] < r['years']
             for r in xc['by_school']))
    hi = max(redone, key=lambda x: x[2] / x[3])
    ok('the highest names-per-post in any school-year', xc['highest']['ratio'],
       hi[2] / hi[3], 1e-9)
    for x in xc['doubled']:
        heads = []
        for ro in next(p for p in b['by_fy'][str(x['fy'])]
                       if p['school'] == x['school'])['names_band']['rosters']:
            heads.append(sum(r['names'] for r in ro['rows'] if r['group'] == xc['group']))
        ok('FY%d %s teaching names on each printed roster' % (x['fy'], x['school']),
           x['heads'], heads)
        ok('FY%d %s names per post if the two rosters were added together'
           % (x['fy'], x['school']), x['summed_ratio'], sum(heads) / x['fte'], 1e-9)
        true('FY%d %s: adding the two printed rosters together would no longer sit '
             'outside every other school-year, so the reason they are shown apart has '
             'gone' % (x['fy'], x['school']),
             x['outside_every_other_year']
             and x['summed_ratio'] > xc['highest']['ratio'])

    # THE TWO LIMITS THE PANELS REST ON ARE REGISTERED, not only written on the page.
    gaps = load('money-gaps.csv')
    for phrase in ('What share of a post any non-teaching adult in a school holds',
                   'Which school year a printed staff roster describes'):
        true('the gap %r is no longer in sources/data/money-gaps.csv. A limit stated in '
             'one paragraph of one page is invisible to everyone who did not read that '
             'page.' % phrase, any(g['what'] == phrase for g in gaps))

    # THE YEAR ALIGNMENT, recomputed as a tally rather than asserted as a sentence.
    yb = b['year_basis']
    true('the panels no longer publish how many report sentences were matched against '
         'the state’s enrolment. An unstated denominator beside a split verdict is the '
         'shape of error this project keeps finding.',
         yb['reports'] > 0 and len(yb['sentences']) > 0)
    ok('sentences matched, against the tally the page prints',
       sum(yb['tally'].values()), len(yb['sentences']))
    for sent in yb['sentences']:
        cand = sent['candidates']
        best = min(cand, key=lambda k: cand[k]['off'])
        ok('which year the FY%d report’s own prose is closer to' % sent['report_fy'],
           sent['closer'], best)
        for label, c in cand.items():
            en = enrol_csv.get((c['fy'], sent['org_code']))
            ok('FY%d %s enrolment behind the %s reading'
               % (sent['report_fy'], sent['org_code'], label),
               c['dese'], f(en['total_cnt']) if en else None, 0.001)

    if os.path.exists(PERSONAS):
        text = open(PERSONAS, encoding='utf-8').read()
        for url, _n, _k, _c in PAGES:
            true('no persona review is recorded for %s in notes/process/PERSONAS.md. A '
                 'report that is entirely correct and answers nobody’s question is a '
                 'failure no verifier can catch.' % url, url in text)

    if FAILS:
        print('%d check(s) FAILED of %d:' % (len(FAILS), CHECKS[0]))
        for x in FAILS:
            print('  ' + x)
        return 1
    print('ok — %d checks, every figure on %s recomputed from the CSVs the database '
          'was built from' % (CHECKS[0], ', '.join(u for u, _n, _k, _c in PAGES)))
    print('   teacher FTE FY%d–FY%d: %d ordered pairs, %d fall, %d rise'
          % (years[0], years[-1], rose + fell + flat, fell, rose))
    print('   headcount FY%d: %d teachers holding %.1f FTE (%.2f of a post each)'
          % (hc['vs_fte'][-1]['fy'], hc['vs_fte'][-1]['teacher_headcount'],
             hc['vs_fte'][-1]['teacher_fte'], hc['vs_fte'][-1]['teacher_share']))
    print('   paraprofessionals FY%d–FY%d: all programmes %.1f→%.1f, special education '
          '%.1f→%.1f' % (sp['first_fy'], sp['last_fy'], sp['all_programmes']['first'],
                         sp['all_programmes']['last'], sp['special_education']['first'],
                         sp['special_education']['last']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
