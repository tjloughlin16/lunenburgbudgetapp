#!/usr/bin/env python3
"""Recompute every figure /how-chapter-70-works renders, and fail if one drifted.

    python3 scripts/verify_ch70_formula.py

Rule 9: a finished document's figures get RECOMPUTED, not re-read. Rule 13's fourth
bullet: a check must assert the NUMBER, not the prose around it.

WHY THIS IS NOT `build_ch70_formula.py --check`.

    database  ->  ch70-formula.json  ->  what Ch70Formula.tsx derives at render time

`--check` establishes that the middle link reproduces. It cannot establish that the middle
link is RIGHT, because it compares the generator with itself -- and this generator has a
second self-comparison problem the others do not: it CALLS `build_minimum_aid.build()`, so
a mistake in that module's SQL would be inherited silently. Everything below goes back to
the database by an independent route: every row of the two DESE tables read unfiltered and
partitioned in Python, and the arithmetic written out again.

WHAT IT CHECKS BEYOND THE FIGURES.

  1. THE EIGHT STEPS ARE UNCHANGED, IN ORDER AND IN WORDING. This is the check this page
     exists to have. The steps were not computed from anything -- they are an explanation
     that took an hour of questions to reach, and the comment above them in
     scripts/build_minimum_aid.py says the ORDER is why it lands, because each step answers
     the question the previous one raises. So the published list is asserted identical to
     the module's, step by step, field by field. Nothing here would notice a good rewrite;
     that is the point. A rewrite is a decision somebody makes deliberately, and it should
     have to break a check.

  2. EVERY QUOTED DEFINITION IS THE PAYLOAD'S, AND THE PAYLOAD'S IS DESE'S. The page quotes
     eight definitions at their cells. Each is re-read out of the published payload and
     matched against the module that carries the extract, so a definition cannot be
     paraphrased on its way to a reader.

  3. THE STRUCTURAL CLAIMS, not just the numbers. Three sentences on this page are claims
     about shape rather than figures, and each is wrong the day it stops holding while
     every number in it is still a faithful copy of the workbook:

       * the year's per-pupil increase and the marginal effect of one pupil COINCIDE, and
         they coincide BECAUSE the foundation aid increment is zero;
       * the foundation budget has never fallen below the required contribution in any
         published year, which is what makes the threshold section a limit rather than a
         description;
       * DESE's glossary names exactly two provisions that reduce aid, and the reduction
         column is populated in the years the page prints and in no others.

  4. RULE 2 MECHANICALLY. The page is scanned for a typed dollar amount or a typed
     percentage. Every sentence on it lives in a .tsx file, and the one thing regenerating
     cannot catch is a figure written into one.

  5. RULE 7c. Every money_gaps row the page cites is still in the registry and still
     carries the `— closes:` half that turns a limit into a records request.

  6. RULE 12. The workbook's sha256, bytes and publisher address, against the manifest.
"""
import csv
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

import build_minimum_aid as MA          # noqa: E402  -- the module the steps live in

DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'ch70-formula.json')
PAGE = os.path.join(ROOT, 'fy28', 'src', 'pages', 'Ch70Formula.tsx')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
LEA = '01620000'
DOC_KEY = 'state-dese/dese-ch70-key-factors.xlsx'

FAILS = []


def check(label, got, want, tol=0.0):
    ok = (abs(got - want) <= tol) if isinstance(want, float) and isinstance(got, (int, float)) \
        else got == want
    if not ok:
        FAILS.append('%s: recomputed %r, the payload says %r' % (label, want, got))
    shown = ('%0.2f' % got) if isinstance(got, float) else got
    print('  %s  %-62s %s' % ('OK  ' if ok else 'DRIFT', label, shown))


def assert_true(label, ok, why):
    if not ok:
        FAILS.append('%s: %s' % (label, why))
    print('  %s  %s' % ('OK  ' if ok else 'FALSE', label))


def rows(db, sql, *args):
    cur = db.execute(sql, args)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def recompute():
    """The database again, by a different route.

    Every row of both tables, unfiltered, partitioned in Python -- so a WHERE clause that
    has quietly stopped matching cannot be shared between the two formulations. That is the
    silent-zero failure this repository has had four of.
    """
    db = sqlite3.connect(DB)
    aid_all = rows(db, 'SELECT * FROM dese_ch70_aid_factor')
    aid = {r['fy']: r for r in aid_all if r['lea'] == LEA and r['level'] == 'district'}
    assert aid, 'no Lunenburg district rows -- the partition matched nothing'

    years = sorted(aid)
    last = years[-1]
    a, p = aid[last], aid[last - 1]
    enrol = a['foundation_enrollment']
    rate = round((a['ch70_aid'] - p['ch70_aid']) / enrol, 2)
    share = a['required_local_contribution'] / a['foundation_budget']
    shares = [(fy, aid[fy]['required_local_contribution'] / aid[fy]['foundation_budget'])
              for fy in years]
    top = max(shares, key=lambda x: x[1])
    return {
        'fy': last, 'fy_first': years[0], 'fy_last': last, 'years': len(years),
        'aid': a['ch70_aid'], 'prior_aid': p['ch70_aid'],
        'increase': a['ch70_aid'] - p['ch70_aid'],
        'enrollment': enrol,
        'aid_per_pupil': a['ch70_aid'] / enrol,
        'rate': rate,
        'ratio': (a['ch70_aid'] / enrol) / rate,
        'foundation_aid_increment': a['foundation_aid_increment'] or 0,
        'foundation_budget': a['foundation_budget'],
        'foundation_per_pupil': a['foundation_budget'] / enrol,
        'required_local_contribution': a['required_local_contribution'],
        'need': a['foundation_budget'] - a['required_local_contribution'],
        'headroom': p['ch70_aid'] - (a['foundation_budget']
                                     - a['required_local_contribution']),
        'required_share': share,
        'pupils_at_zero': enrol * share,
        'fall_pct': 1 - share,
        'highest_share': top[1], 'highest_share_fy': top[0],
        'ever_negative': [fy for fy in years
                          if aid[fy]['foundation_budget']
                          < aid[fy]['required_local_contribution']],
        'cut_years': [(fy, aid[fy]['ch70_aid_reduction']) for fy in years
                      if aid[fy]['ch70_aid_reduction']],
    }


def main():
    if not os.path.exists(PAYLOAD):
        raise SystemExit('%s is missing. Run scripts/build_ch70_formula.py.'
                         % os.path.relpath(PAYLOAD, ROOT))
    d = json.load(open(PAYLOAD, encoding='utf-8'))
    r = recompute()

    # ---------------------------------------------------------------- the eight steps
    print('THE EIGHT STEPS -- the artefact, unchanged in order and in wording')
    want = MA.HOW_IT_WORKS
    got = d['how_it_works']
    check('how many steps the page publishes', len(got), len(want))
    for i, (g, w) in enumerate(zip(got, want), 1):
        assert_true('step %d: %s' % (i, w['step'][:52]),
                    g == w,
                    'the published step differs from the one in build_minimum_aid.py. '
                    'The sequence is the artefact — every step answers the question the '
                    'previous one raises — and a rewrite has to be deliberate.')
    assert_true('the unlock is still step 4',
                d['unlock'] == want[3]['step'],
                'the page names one step as the thing everything else follows from, and '
                'it is no longer the fourth')
    assert_true('every step still carries its `watch` line',
                all(s.get('watch') for s in got),
                'the warning is where every misreading in the original conversation '
                'happened; a step without one publishes the misreading')

    # ---------------------------------------------------------------- the definitions
    print('\nDESE’S OWN WORDS -- quoted, never rendered')
    src = {x['cell']: x for x in MA.DEFINITIONS}
    for x in d['definitions']:
        assert_true('%s %s' % (x['cell'], x['term'][:40]),
                    x['cell'] in src and src[x['cell']] == x,
                    'the payload’s definition is not the workbook extract’s — rule 13, '
                    'quote the source and never your rendering of it')
    assert_true('the two reduction provisions are among them',
                all(x in d['definitions'] for x in d['reductions'])
                and len(d['reductions']) == 2,
                'the page states that DESE’s glossary names exactly two provisions that '
                'reduce aid, and it no longer does')

    # ---------------------------------------------------------------- every figure
    print('\nEVERY FIGURE, RECOMPUTED FROM THE DATABASE')
    check('fiscal year', d['fy'], r['fy'])
    check('years published', d['years'], r['years'])
    check('Chapter 70 aid', d['aid'], r['aid'], 0.005)
    check('foundation enrollment', d['enrollment'], r['enrollment'])
    check('the increase', d['increase'], r['increase'], 0.005)
    check('foundation aid increment', d['foundation_aid_increment'],
          r['foundation_aid_increment'], 0.005)
    check('foundation budget', d['foundation_budget'], r['foundation_budget'], 0.005)
    check('required local contribution', d['required_local_contribution'],
          r['required_local_contribution'], 0.005)
    check('what the formula says is needed', d['need'], r['need'], 0.005)
    check('headroom above the line', d['headroom'], r['headroom'], 0.005)
    check('foundation budget per pupil', d['foundation_per_pupil'],
          r['foundation_per_pupil'], 0.005)
    check('aid per pupil', d['three_numbers'][0]['value'], r['aid_per_pupil'], 0.005)
    check('this year’s increase per pupil', d['three_numbers'][1]['value'], r['rate'], 0.005)
    check('what one more pupil moves the aid by', d['three_numbers'][2]['value'],
          r['rate'], 0.005)
    check('the ratio between the first two', d['ratio'], r['ratio'], 0.0005)

    T = d['threshold']
    check('required contribution as a share of the foundation budget',
          T['required_share'], r['required_share'], 1e-9)
    check('pupils at which the subtraction turns negative', T['pupils_at_zero'],
          r['pupils_at_zero'], 0.005)
    check('the fall that implies', T['fall_pct'], r['fall_pct'], 1e-9)
    check('highest required share published', T['highest_share'], r['highest_share'], 1e-9)
    check('...and the year it was', T['highest_share_fy'], r['highest_share_fy'])
    check('years checked', T['years_checked'], r['years'])

    check('years the reduction column is populated',
          [c['fy'] for c in d['cut_years']], [fy for fy, _ in r['cut_years']])
    for c in d['cut_years']:
        check('  reduction in FY%d' % c['fy'], c['amount'],
              dict(r['cut_years'])[c['fy']], 0.005)

    # -------------------------------------------------- the structural claims
    print('\nTHE CLAIMS THAT ARE ABOUT SHAPE RATHER THAN AMOUNT')
    assert_true('the per-pupil increase and the marginal effect are one number',
                d['three_numbers'][1]['value'] == d['three_numbers'][2]['value'],
                'the page says the second and third figures coincide')
    assert_true('...and they coincide BECAUSE the formula paid nothing',
                r['foundation_aid_increment'] == 0,
                'the page gives that as the reason. With a foundation aid increment the '
                'two are different quantities and the sentence is wrong')
    assert_true('the foundation budget has never fallen below the requirement',
                not r['ever_negative'],
                'the threshold section states that it has not happened in any published '
                'year, and it now has: %s' % r['ever_negative'])
    assert_true('the threshold is published as a calculation, not a measurement',
                T['is_measurement'] is False,
                'a scenario labelled as a measurement is rule 7 broken at the point a '
                'reader is most likely to quote it')

    # -------------------------------------------------- the quotes, re-read
    print('\nWHAT THE TOWN SAID -- re-read out of the extracted minutes')
    for q in d['said']:
        rel = q['cite'].replace('/docs/', 'sources/')
        path = os.path.join(ROOT, rel)
        present = os.path.exists(path)
        if present:
            text = re.sub(r'\s+', ' ',
                          open(path, encoding='utf-8', errors='replace').read())
            present = re.sub(r'\s+', ' ', q['quote']) in text
        assert_true('%s %s' % (q['board'], q['date']), present,
                    'the quote is no longer in %s' % rel)

    # -------------------------------------------------- rule 2, mechanically
    print('\nRULE 2 -- no figure typed into a sentence')
    money_re = re.compile(r'(?<![\w$])\$\s?\d[\d,]*(\.\d+)?')
    pct_re = re.compile(r'(?<![\w.])\d+(\.\d+)?\s?(%|percent\b)')
    body = open(PAGE, encoding='utf-8').read()
    body = re.sub(r'/\*[\s\S]*?\*/', '', body)
    body = re.sub(r'^\s*//.*$', '', body, flags=re.M)
    # `100%` is a CSS length on a grid template, not a figure about the town.
    allowed = ('100%',)
    for m in list(money_re.finditer(body)) + list(pct_re.finditer(body)):
        s = m.group(0).strip()
        if s in allowed:
            continue
        FAILS.append('%s carries a typed figure %r -- rule 2 says derive it'
                     % (os.path.relpath(PAGE, ROOT), s))
    print('  OK    %s' % os.path.relpath(PAGE, ROOT))

    # -------------------------------------------------- rule 7c, the registry
    print('\nRULE 7c -- the limits are rows in the registry, not prose here')
    registry = {row['what']: row for row in csv.DictReader(open(GAPS, encoding='utf-8'))}
    for g in d['gaps']:
        present = g['what'] in registry
        assert_true('registered: %s' % g['what'][:56], present,
                    'the page cites a gap that is not in money-gaps.csv')
        if present:
            assert_true('  ...and it names the document that would close it',
                        '— closes:' in registry[g['what']]['why'],
                        'a gap with no named remedy is a grievance, not a records request')

    # -------------------------------------------------- rule 12, the document
    print('\nRULE 12 -- the document travels with the figures')
    man = {row['key']: row for row in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    assert_true('the workbook is in the archive manifest', DOC_KEY in man,
                'the page cites a document the manifest does not describe')
    if DOC_KEY in man:
        check('sha256', d['source']['sha256'], man[DOC_KEY]['sha256'])
        check('bytes', d['source']['bytes'], int(man[DOC_KEY]['bytes']))
        check('the publisher’s address', d['source']['url'], man[DOC_KEY]['upstream'])

    # -------------------------------------------------- rule 15a, the persona review
    # A verifier checks the figures. It cannot check that anybody's question was answered,
    # and a report that is entirely correct and answers nobody's question is a failure no
    # verifier can catch -- so what CAN be asserted is that the review was run and that
    # the three sentences it added are still on the page.
    print('\nRULE 15a -- the persona review was run, and its changes are still here')
    personas = open(os.path.join(ROOT, 'notes', 'process', 'PERSONAS.md'),
                    encoding='utf-8').read()
    assert_true('a review of this page is recorded in PERSONAS.md',
                '/how-chapter-70-works' in personas,
                'notes/process/PERSONAS.md has no entry for this page')
    page = open(PAGE, encoding='utf-8').read()
    for who, phrase in (
            ('readers 1 and 6: whose decisions these are',
             'is a decision anybody in Lunenburg makes'),
            ('reader 6: the aid is town revenue, not a payment to the district',
             'it arrives as\n          town revenue'),
            ('reader 4: the control question',
             'If you are building a budget')):
        assert_true(who, phrase in page,
                    'the persona review added this and an edit has removed it')

    # -------------------------------------------------- the conclusions contract
    print('\nTHE CONCLUSIONS -- re-run against the published payload')
    import conclusions as C
    problems = C.check('how-chapter-70-works', d['conclusions'])
    for p in problems:
        FAILS.append(p)
    assert_true('every conclusion states its bearing',
                all(c.get('bearing') for c in d['conclusions']),
                'a conclusion with no bearing tells a reader nothing about whether '
                'anybody can act on it')
    assert_true('no figure in a conclusion is unregistered', not problems,
                '; '.join(problems))

    print()
    if FAILS:
        print('%d PROBLEM(S):' % len(FAILS))
        for f in FAILS:
            print('  - %s' % f)
        return 1
    print('every figure /how-chapter-70-works renders recomputes from the database, and '
          'the eight steps are unchanged.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
