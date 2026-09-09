#!/usr/bin/env python3
"""Recompute every figure /what-the-state-requires-us-to-spend renders, and fail if one
drifted.

Rule 9: a finished document's figures get RECOMPUTED, not re-read. Rule 13's fourth
bullet: a check must assert the NUMBER, not the prose around it -- `verify_athletics.py`
once passed because a sentence existed while the sentence was wrong.

WRITTEN AFTER THE PROSE, which is the only order in which this step works (step 5 of
`notes/process/WRITING-AN-ANALYSIS.md`). A verifier written first asserts what the author
intended; written after, it asserts what is true and finds where the two parted.

WHAT THIS CHECKS, AND WHY IT IS NOT `build_spending_vs_required.py --check`.

    database  ->  spending-vs-required.json  ->  the values SpendingVsRequired.tsx derives

`--check` establishes that the middle link reproduces. It cannot establish that the middle
link is RIGHT, because it compares the generator with itself. Everything below recomputes
the payload from the database by a SECOND, independent formulation -- every row of both
tables read unfiltered and partitioned in Python, the rank string parsed again, the
arithmetic written out again -- so a WHERE clause that quietly stopped matching, which is
the silent-zero failure this repository has had four of, cannot be shared between the two
routes.

  1. THE PAYLOAD, recomputed. Required, spent, ratio, median, quartiles, rank, the
     counterfactual, and the two summary counts.

  2. THE DERIVATIONS THE PAGE DOES ITSELF, in TSX, that no generator produces. Six
     sentences on the page are computed at render time and exist nowhere in the payload:

       * the count of years below the enforced floor, and the narrowest year
       * the years below the state's first quartile
       * the most recent earlier year at or worse than the latest rank
       * the years whose ratio EQUALS the state median, and the last of them
       * spending growth against requirement growth between those two years
       * the count of years in which the town spent more than a median district would

     -- each recomputed here from the database rather than read off the payload.

  3. THE STRUCTURAL CLAIMS THE SENTENCES REST ON. Rule 5 of WRITING-AN-ANALYSIS: "assert
     the structure a paragraph rests on, not only its figures." Four sentences here are
     structural rather than numeric --

       * the town is above the required minimum in EVERY measured year
       * the ratio in the best-ranked year is LOWER than the ratio in the latest year,
         which is the whole reason the page leads with rank
       * the requirement grew faster than the spending between those two years, and the
         spending did not fall
       * the latest ratio sits INSIDE the state's middle half

     -- and each is asserted. The day one stops holding, a paragraph is wrong while every
     number in it is still a faithful copy of the source.

  4. RULE 1 MECHANICALLY. The two stages must be two collections and must never meet. It
     asserts that the payload carries no combined field, that the fiscal years of the two
     arrays are disjoint and ordered, that every row of each carries the stage the
     generator claims, and that the page's chart file names no dataKey that could hold
     both.

  5. RULE 2 MECHANICALLY. The page and its charts are scanned for a typed dollar amount or
     a typed percentage. Every sentence on this page lives in a .tsx file, and the one
     thing regenerating cannot catch is a figure written into one.

  6. RULE 7c. Every money_gaps row the page cites is in the registry and carries a
     `— closes:` half, and the two rows this page ADDED are still there.

  7. RULE 12. The workbook, its address, its bytes and its sha256, against the manifest.

  8. RULE 15a AND THE PERSONA REVIEW. Every quote is re-read out of the meeting archive,
     and the things `notes/process/PERSONAS.md` added to the page are asserted here rather
     than trusted to stay.

    python3 scripts/verify_spending_vs_required.py
"""
import csv
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'spending-vs-required.json')
PAGE = os.path.join(ROOT, 'fy28', 'src', 'pages', 'SpendingVsRequired.tsx')
CHARTS = os.path.join(ROOT, 'fy28', 'src', 'components', 'SpendingVsRequiredCharts.tsx')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
MINUTES = os.path.join(ROOT, 'sources', 'meetings', 'text')
LEA = '01620000'
DOC_KEY = 'state-dese/dese-ch70-district-profile.xlsx'

FAILS = []


def check(label, got, want, tol=0.0):
    ok = (abs(got - want) <= tol) if isinstance(want, float) and isinstance(got, (int, float)) \
        else got == want
    if not ok:
        FAILS.append('%s: recomputed %r, the payload says %r' % (label, want, got))
    shown = ('%0.4f' % got) if isinstance(got, float) else got
    print('  %s  %-64s %s' % ('OK  ' if ok else 'DRIFT', label, shown))


def assert_true(label, ok, why):
    if not ok:
        FAILS.append('%s: %s' % (label, why))
    print('  %s  %s' % ('OK  ' if ok else 'FALSE', label))


def rows(db, sql, *args):
    cur = db.execute(sql, args)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def recompute():
    """Everything again, read unfiltered and partitioned in Python.

    The generator selects Lunenburg's district rows in SQL and joins the statewide table
    by fiscal year. This reads BOTH tables whole and does the selection and the join in
    Python, so a WHERE clause or a LIKE pattern that stopped matching cannot be shared
    between the two routes."""
    db = sqlite3.connect(DB)
    fml_all = rows(db, 'SELECT * FROM dese_ch70_formula')
    st_all = rows(db, 'SELECT * FROM dese_ch70_statewide')

    mine = [r for r in fml_all
            if r['lea'] == LEA and r['level'] == 'district'
            and r['net_school_spending'] is not None]
    assert mine, 'no Lunenburg district rows -- the partition matched nothing'
    mine.sort(key=lambda r: r['fy'])

    # The statewide row, matched on the WORDS of the measure rather than on a LIKE.
    state = {}
    for r in st_all:
        if 'net school spending' in (r['measure'] or ''):
            state[r['fy']] = r
    assert state, 'the statewide comparison matched nothing'

    def rank_of(fy):
        s = state.get(fy)
        if not s:
            return None, None
        m = re.match(r'\s*(\d+)\s+of\s+(\d+)', str(s['lunenburg_rank_of_districts'] or ''))
        return (int(m.group(1)), int(m.group(2))) if m else (None, None)

    out = {'actual': [], 'budgeted': [], 'reconciles_all': True}
    for r in mine:
        s = state.get(r['fy'])
        rk, of = rank_of(r['fy'])
        if r['reconciles'] != 'yes':
            out['reconciles_all'] = False
        row = {
            'fy': r['fy'],
            'required': round(r['required_nss']),
            'spent': round(r['net_school_spending']),
            'ratio': round(r['nss_pct_of_required'], 4),
            'above_required': round(r['net_school_spending'] - r['required_nss']),
            'state_median': round(s['median'], 4) if s else None,
            'p25': round(s['p25'], 4) if s and s['p25'] is not None else None,
            'p75': round(s['p75'], 4) if s and s['p75'] is not None else None,
            'rank': rk, 'districts': of,
            'at_state_median': round(r['required_nss'] * s['median']) if s else None,
            'short_of_median':
                round(r['required_nss'] * s['median'] - r['net_school_spending'])
                if s else None,
        }
        out[r['nss_stage']].append(row)

    A = out['actual']
    B = out['budgeted']
    ranked = [a for a in A if a['rank']]
    out['best'] = min(ranked, key=lambda a: a['rank'])
    out['latest'] = A[-1]
    out['at_or_above'] = sum(1 for a in ranked
                             if a['state_median'] and a['ratio'] >= a['state_median'])
    out['measured'] = len(ranked)

    # ---- what the PAGE derives at render time, and the payload does not carry
    L = out['latest']
    out['below_floor'] = [a['fy'] for a in A if a['ratio'] < 1]
    out['lowest'] = min(A, key=lambda a: a['ratio'])
    out['below_p25'] = [a['fy'] for a in A
                        if a['p25'] is not None and a['ratio'] < a['p25']]
    prior = [a for a in A
             if a['fy'] < L['fy'] and a['rank'] is not None and a['rank'] >= L['rank']]
    out['worst_since'] = prior[-1] if prior else None
    exact = [a for a in A if a['state_median'] is not None
             and a['ratio'] == a['state_median']]
    out['exact_median_years'] = [a['fy'] for a in exact]
    out['last_exact'] = exact[-1] if exact else None
    if out['last_exact']:
        E = out['last_exact']
        out['spent_growth'] = L['spent'] / E['spent'] - 1
        out['req_growth'] = L['required'] / E['required'] - 1
    out['spent_more_than_median_years'] = sum(1 for a in A
                                              if (a['short_of_median'] or 0) < 0)
    out['stage_disjoint'] = (not B) or (max(a['fy'] for a in A) < min(b['fy'] for b in B))
    return out


def main():
    for path in (DB, PAYLOAD, PAGE, CHARTS, GAPS, MANIFEST):
        if not os.path.exists(path):
            print('missing: %s' % os.path.relpath(path, ROOT))
            return 1
    d = json.load(open(PAYLOAD, encoding='utf-8'))
    r = recompute()
    A, B = d['actual'], d['budgeted']
    L, BEST = d['latest_actual'], d['best_rank']

    print('\nTHE SERIES, ROW BY ROW')
    check('measured (actual) years', len(A), len(r['actual']))
    check('budgeted years', len(B), len(r['budgeted']))
    for stage in ('actual', 'budgeted'):
        for got, want in zip(d[stage], r[stage]):
            if got != want:
                FAILS.append('%s FY%s: recomputed %r, the payload says %r'
                             % (stage, want['fy'], want, got))
    print('  %s  every row of both stages recomputes field for field'
          % ('OK  ' if not FAILS else 'DRIFT'))
    assert_true('every year reconciles required NSS to aid plus contribution',
                r['reconciles_all'],
                'a year does not reconcile, and the generator is meant to refuse to write')

    print('\nTHE HEADLINE POSITIONS')
    check('latest measured fiscal year', L['fy'], r['latest']['fy'])
    check('latest rank', L['rank'], r['latest']['rank'])
    check('districts in the latest year', L['districts'], r['latest']['districts'])
    check('latest ratio', L['ratio'], r['latest']['ratio'], 1e-9)
    check('latest state median', L['state_median'], r['latest']['state_median'], 1e-9)
    check('best-ranked fiscal year', BEST['fy'], r['best']['fy'])
    check('best rank', BEST['rank'], r['best']['rank'])
    check('best-year ratio', BEST['ratio'], r['best']['ratio'], 1e-9)
    check('years at or above the state median', d['years_at_or_above_median'],
          r['at_or_above'])
    check('measured years with a rank', d['years_measured'], r['measured'])
    check('the gap to the median ratio, latest year', L['short_of_median'],
          r['latest']['short_of_median'])
    check('spending at the median ratio, latest year', L['at_state_median'],
          r['latest']['at_state_median'])

    print('\nWHAT THE PAGE DERIVES AT RENDER TIME (in TSX, from nothing else)')
    page_below = [a['fy'] for a in A if a['ratio'] < 1]
    check('years below the enforced floor', page_below, r['below_floor'])
    page_lowest = min(A, key=lambda a: a['ratio'])
    check('the narrowest year', page_lowest['fy'], r['lowest']['fy'])
    check('  ...spent that year', page_lowest['spent'], r['lowest']['spent'])
    check('  ...required that year', page_lowest['required'], r['lowest']['required'])
    check('  ...clear of the floor by', page_lowest['above_required'],
          r['lowest']['above_required'])
    page_p25 = [a['fy'] for a in A if a['p25'] is not None and a['ratio'] < a['p25']]
    check('years below the state first quartile', page_p25, r['below_p25'])
    prior = [a for a in A if a['fy'] < L['fy'] and a['rank'] is not None
             and a['rank'] >= L['rank']]
    check('the most recent earlier year at or worse than the latest rank',
          prior[-1]['fy'] if prior else None,
          r['worst_since']['fy'] if r['worst_since'] else None)
    check('  ...its rank', prior[-1]['rank'] if prior else None,
          r['worst_since']['rank'] if r['worst_since'] else None)
    exact = [a for a in A if a['state_median'] is not None
             and a['ratio'] == a['state_median']]
    check('years whose ratio EQUALS the state median',
          [a['fy'] for a in exact], r['exact_median_years'])
    check('the last of them', exact[-1]['fy'] if exact else None,
          r['last_exact']['fy'] if r['last_exact'] else None)
    if exact:
        E = exact[-1]
        check('  ...how far it was from the median, in dollars', E['short_of_median'],
              r['last_exact']['short_of_median'])
        check('spending growth since that year', L['spent'] / E['spent'] - 1,
              r['spent_growth'], 1e-12)
        check('requirement growth since that year', L['required'] / E['required'] - 1,
              r['req_growth'], 1e-12)
    check('years the town spent MORE than a median district would',
          sum(1 for a in A if (a['short_of_median'] or 0) < 0),
          r['spent_more_than_median_years'])

    print('\nTHE STRUCTURAL CLAIMS THE PARAGRAPHS REST ON')
    assert_true('the town is above the required minimum in every measured year',
                not r['below_floor'],
                'a measured year is below the enforced floor, and finding 1 says none is')
    assert_true('the best-ranked year has a LOWER ratio than the latest year',
                r['best']['ratio'] < r['latest']['ratio'],
                'it does not, and finding 4 -- the whole reason this page leads with rank '
                'rather than ratio -- rests on it')
    if r.get('last_exact'):
        assert_true('the requirement grew faster than the spending since the median year',
                    r['req_growth'] > r['spent_growth'],
                    'it did not, and the dollars section says the position fell because '
                    'the requirement outran the spending')
        assert_true('spending did not fall over that span', r['spent_growth'] > 0,
                    'spending fell, and the same sentence says it did not')
    assert_true('the latest ratio sits inside the state’s middle half',
                r['latest']['p25'] <= r['latest']['ratio'] <= r['latest']['p75'],
                'it does not, and finding 5 says Lunenburg is inside the middle half')
    assert_true('the latest rank is worse than the best rank on record',
                r['latest']['rank'] > r['best']['rank'],
                'it is not, and finding 3 describes a fall')

    # -------------------------------------------------------------- rule 1, mechanically
    print('\nRULE 1 -- two stages, two collections, and they never meet')
    assert_true('the payload carries no combined series',
                not any(k in d for k in ('series', 'all', 'combined', 'years')),
                'a caller could read a single field and difference across the stage')
    assert_true('the two arrays are disjoint in fiscal year and ordered',
                r['stage_disjoint']
                and not (set(a['fy'] for a in A) & set(b['fy'] for b in B)),
                'the actual and budgeted years overlap, so a chart drawn on fy would put '
                'two stages at one x position')
    assert_true('the stage warning names both spans',
                all(('FY%d' % y) in d['stage_warning']
                    for y in (A[0]['fy'], A[-1]['fy'], B[0]['fy'], B[-1]['fy'])),
                'the warning does not name the years it is about')
    charts = open(CHARTS, encoding='utf-8').read()
    for key in ('ours_actual', 'ours_budgeted', 'rank_actual', 'rank_budgeted',
                'median_actual', 'median_budgeted'):
        assert_true('the charts split the stage into %s' % key, ('%s:' % key) in charts,
                    'the split dataKey is gone, and a single key can draw one path '
                    'through both stages')
    assert_true('no chart draws a bare `ratio` or `rank` line',
                'dataKey="ratio"' not in charts and 'dataKey="rank"' not in charts,
                'a dataKey holding both stages is on a chart')
    assert_true('the budgeted marks are drawn differently, not only labelled',
                charts.count('strokeDasharray="5 4"') >= 3,
                'the dashed treatment that separates the stages by FORM is gone, so the '
                'split survives only in a caption')

    # -------------------------------------------------------------- rule 2, mechanically
    print('\nRULE 2 -- no figure typed into a sentence')
    money_re = re.compile(r'(?<![\w$])\$\s?\d[\d,]*(\.\d+)?')
    pct_re = re.compile(r'(?<![\w.])\d+(\.\d+)?\s?(%|percent\b)')
    allowed = ('100%',)   # ResponsiveContainer dimensions, not figures about the town
    for path in (PAGE, CHARTS):
        src = open(path, encoding='utf-8').read()
        body = re.sub(r'/\*[\s\S]*?\*/', '', src)
        body = re.sub(r'^\s*//.*$', '', body, flags=re.M)
        for m in list(money_re.finditer(body)) + list(pct_re.finditer(body)):
            s = m.group(0).strip()
            if s in allowed:
                continue
            FAILS.append('%s carries a typed figure %r -- rule 2 says derive it'
                         % (os.path.relpath(path, ROOT), s))
        print('  OK    %s' % os.path.relpath(path, ROOT))

    # ------------------------------------------------------------- rule 15a, the archive
    print('\nRULE 15a -- every quote, re-read out of the meeting archive')
    for q in d['said']:
        rel = q['cite'].replace('/docs/', '')
        path = os.path.join(ROOT, 'sources', rel)
        present = os.path.exists(path)
        assert_true('%s %s is in the archive' % (q['board'], q['date']), present,
                    'a quote is attributed to a document that is not here')
        if present:
            text = re.sub(r'\s+', ' ', open(path, encoding='utf-8',
                                            errors='replace').read())
            assert_true('  ...and still carries the sentence quoted',
                        re.sub(r'\s+', ' ', q['quote']) in text,
                        'quote the source, never your rendering of it')
    assert_true('the searched terms carry their denominator',
                all(t['documents'] >= 0 for t in d['searched'])
                and d['minutes']['held'] == d['minutes']['searchable']
                                          + d['minutes']['unsearchable'],
                'a term count without a denominator reads as "nobody said it"')
    assert_true('the coverage share is under one, and the page says so',
                d['minutes']['searchable_share'] < 1,
                'the archive is fully searchable, so the caveat should be rewritten '
                'rather than left claiming a gap that closed')

    # ------------------------------------------------------------------ rule 7c
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
    for added in ('What Lunenburg’s net school spending actually was in the two most '
                  'recent years',
                  'How the district’s own accounts add up to the net school spending '
                  'DESE reports'):
        assert_true('this page ADDED: %s' % added[:48], added in registry,
                    'the limit this page hit is no longer registered')

    # ------------------------------------------------------------------ rule 12
    print('\nRULE 12 -- the document travels with the figures')
    man = {row['key']: row for row in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    assert_true('the workbook is in the archive manifest', DOC_KEY in man,
                'the page cites a document the manifest does not describe')
    if DOC_KEY in man:
        check('sha256', d['source']['sha256'], man[DOC_KEY]['sha256'])
        check('bytes', d['source']['bytes'], int(man[DOC_KEY]['bytes']))
        check('the publisher’s address', d['source']['url'], man[DOC_KEY]['upstream'])

    # ------------------------------------------------------------------ the persona review
    print('\nTHE PERSONA REVIEW -- what notes/process/PERSONAS.md added, asserted')
    page = ' '.join(open(PAGE, encoding='utf-8').read().split())
    for label, needle, why in [
        ('reader 1 — the gap is in the STAT ROW, not six findings down',
         'requirement. Arithmetic on a published median &mdash; not a proposal '
         'anybody made </Stat>',
         'the reader who believes something is hidden must meet the worst-looking figure '
         'on the first screen or conclude it was buried'),
        ('reader 1 — the worst fact is on the first screen',
         'measured years at or above the state median',
         'the reader who thinks something is hidden must meet the position, good and '
         'bad, in the stat row rather than after six findings'),
        ('reader 2 — the repeatable sentence is the true one',
         'is not what this series says',
         'the sentence a neighbour repeats has to be the corrected one, in the first '
         'screen'),
        ('reader 3 — mechanisms, never people',
         'It does not establish why',
         'the page must refuse the causal step in the finding itself, not only in the '
         'caveats, or somebody named at a meeting is the implied cause'),
        ('reader 4 — the gap is a named document, not a lament',
         'Closes:',
         'the Finance Committee member needs the document that would settle it'),
        ('reader 5 — the most recent MEASURED year is stated as such',
         'the most recent MEASURED year',
         'the School Committee member must not read a budgeted figure as a result'),
        ('reader 6 — the town-versus-school frame is made harder, not easier',
         'a budget somebody chose',
         'the Select Board member must see that this measure is not an appropriation '
         'argument'),
        ('the corroborating pages are named as INDEPENDENT',
         'never as one figure confirming',
         'two pages of similar magnitude must not read as one confirming the other'),
        ('the counterfactual is labelled beside itself',
         'not a proposal anybody made',
         'the dollar gap must carry its own warning where it is drawn'),
        ('reader 5 — "does this measure the cuts?" is answered before it is asked',
         'Does any of this measure the reductions?',
         'the School Committee member arrives with exactly this question, and a page that '
         'lets them read a pre-reduction year as a verdict on the reductions has failed '
         'them however correct its arithmetic'),
        ('reader 4 — one thing that could be done differently next year',
         'One thing that could be done differently next year',
         'the Finance Committee test is whether the report names an action, and this one '
         'can, because the figure they asked for is in a workbook they already receive'),
        ('reader 6 — the town-versus-school frame is refused where it does not hold',
         'only one side has a floor',
         'the Select Board member will reach for the comparison, and the honest answer is '
         'that the statute puts a floor under one side and not the other'),
        ('reader 6 — and neither reading of that is endorsed',
         'both readings fit this page equally well',
         'naming the asymmetry without refusing both flattering readings of it is how '
         'rule 7 gets broken'),
    ]:
        assert_true(label, needle in page, why)

    print()
    if FAILS:
        print('%d PROBLEM(S):' % len(FAILS))
        for f in FAILS:
            print('  - %s' % f)
        return 1
    print('every figure /what-the-state-requires-us-to-spend renders recomputes from the '
          'database.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
