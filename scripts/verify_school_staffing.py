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
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'school-staffing.json')
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


def main():
    d = json.load(open(PAYLOAD, encoding='utf-8'))

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
    ok('conclusions published', len(d['conclusions']), 6)
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
    if os.path.exists(PERSONAS):
        text = open(PERSONAS, encoding='utf-8').read()
        true('no persona review is recorded for /school-staffing in '
             'notes/process/PERSONAS.md. A report that is entirely correct and answers '
             'nobody’s question is a failure no verifier can catch.',
             '/school-staffing' in text)

    if FAILS:
        print('%d check(s) FAILED of %d:' % (len(FAILS), CHECKS[0]))
        for x in FAILS:
            print('  ' + x)
        return 1
    print('ok — %d checks, every figure on /school-staffing recomputed from the CSVs '
          'the database was built from' % CHECKS[0])
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
