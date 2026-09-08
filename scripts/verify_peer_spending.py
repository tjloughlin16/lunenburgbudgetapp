#!/usr/bin/env python3
"""Recompute every figure /what-other-districts-spend renders, and fail if one drifted.

    python3 scripts/verify_peer_spending.py

Rule 9: a finished document's figures get RECOMPUTED, not re-read. Rule 13's fourth
bullet: a check must assert the NUMBER, not the prose around it -- `verify_athletics.py`
once passed because a sentence existed while the sentence was wrong.

WRITTEN AFTER THE PROSE, which is the only order in which this step works (step 5 of
`notes/process/WRITING-AN-ANALYSIS.md`). A verifier written first asserts what the author
intended; written after, it asserts what is true and finds where the two parted.

WHAT THIS CHECKS, AND WHY IT IS NOT `build_peer_spending.py --check`.

    database  ->  peer-spending.json  ->  the analysis and the page

`--check` establishes that the middle link reproduces. It cannot establish that the middle
link is RIGHT, because it compares the generator with itself. Everything below recomputes
the payload from the database by a SECOND, independent formulation -- different SQL shape,
the arithmetic written out again -- so a mistake in a join condition cannot be shared
between the two.

  1. THE PAYLOAD, recomputed. Every headline figure derived again.

  2. THE STRUCTURAL CLAIMS THE SENTENCES REST ON. Rule 5 of WRITING-AN-ANALYSIS: "assert
     the structure a paragraph rests on, not only its figures." Six sentences here are
     structural rather than numeric --

       * Lunenburg is below the statewide first quartile in EVERY published year
       * its rank among the six is never higher than fifth
       * (1+spending) / (1+pupils) = (1+per pupil), for every district
       * the eleven category gaps SUM to the in-district gap
       * DESE's total per-pupil is over TOTAL FTE and every other row over IN-DISTRICT FTE
       * DESE's average teacher salary IS the Teachers function's spend per teacher FTE

     -- and each is asserted. The day one stops holding, a paragraph is wrong while every
     number in it is still a faithful copy of the source.

  3. THE ROLLUP TRAP AND THE STATE ROW, checked from the other side: that a query written
     WITHOUT a level filter would in fact produce a different answer. A guard nobody can
     trip is not a guard.

  4. THE ANALYSIS DOCUMENT. Every figure typed into `sources/analyses/per-pupil-spending.md`
     is derived here and asserted to appear, on a word boundary, with whitespace collapsed.

  5. RULE 2 MECHANICALLY. The page and its charts are scanned for a typed dollar amount or
     a typed percentage. Every sentence on the page lives in a .tsx file, and the one thing
     regenerating cannot catch is a figure written into one.

  6. RULE 1 MECHANICALLY. Nothing on this page may be differenced across a stage, so the
     stage split is asserted to be real and the two collections asserted to be at different
     fiscal years and never subtracted.

  7. RULE 7c. Every money_gaps row the page cites is in the registry and carries a
     `— closes:` half.

  8. THE PERSONA REVIEW. `notes/process/PERSONAS.md` -- six readers, and three of the six
     tests are about what a document OMITS, which is what a writer cannot see in their own
     work. The things the review added are asserted here rather than trusted to stay.
"""
import collections
import csv
import json
import os
import re
import sqlite3
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'peer-spending.json')
PAGE = os.path.join(ROOT, 'fy28', 'src', 'pages', 'PeerSpending.tsx')
CHARTS = os.path.join(ROOT, 'fy28', 'src', 'components', 'PeerSpendingCharts.tsx')
DOCUMENT = os.path.join(ROOT, 'sources', 'analyses', 'per-pupil-spending.md')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')

LEA = '01620000'
TOWN = 'Lunenburg'
FIN_FY = 2025
CH70_FY = 2026
BASE_FY = 2012

FAILS = []


def check(label, got, want, tol=0.0):
    if isinstance(want, float) and isinstance(got, (int, float)):
        ok = abs(got - want) <= tol
    else:
        ok = got == want
    if not ok:
        FAILS.append('%s: recomputed %r, the payload says %r' % (label, want, got))
    shown = ('%0.4f' % got) if isinstance(got, float) else got
    print('  %s  %-62s %s' % ('OK  ' if ok else 'DRIFT', label, shown))


def assert_true(label, ok, why):
    if not ok:
        FAILS.append('%s: %s' % (label, why))
    print('  %s  %s' % ('OK  ' if ok else 'FALSE', label))


def q(db, sql, *args):
    cur = db.execute(sql, args)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


# ------------------------------------------------------ the document, for the figure scan

def flat_document():
    text = open(DOCUMENT, encoding='utf-8').read()
    return ' '.join(text.split())


def in_document(flat, needle):
    """A figure has to appear on a word boundary. A bare substring check on `61` once
    passed on the digits inside `$25,613,679.23`."""
    n = ' '.join(str(needle).split())
    return re.search(r'(?<![\w.,])%s(?![\w]|,\d|\.\d)' % re.escape(n), flat) is not None


def states(flat, label, needle):
    ok = in_document(flat, needle)
    if not ok:
        FAILS.append('the analysis does not state %s (%r)' % (label, needle))
    print('  %s  %-56s %s' % ('OK  ' if ok else 'GONE', label, needle))


def usd(n):
    return '$%s' % format(int(round(n)), ',')


def main():
    if not os.path.exists(PAYLOAD):
        print('MISSING %s — run scripts/build_peer_spending.py' % PAYLOAD)
        return 1
    d = json.load(open(PAYLOAD, encoding='utf-8'))
    db = sqlite3.connect('file:%s?mode=ro' % DB, uri=True)
    flat = flat_document()

    # ------------------------------------------------------------------ 1. the headline
    print('\n§1  The headline, recomputed from the database')
    lun = q(db, "SELECT gen_fund, grants_revolving, total, per_pupil "
                "FROM dese_function_expenditure "
                "WHERE lea=? AND fy=? AND level='total' AND func_code='TTPP'",
            LEA, FIN_FY)
    assert_true('exactly one district-total row for Lunenburg in FY%d' % FIN_FY,
                len(lun) == 1, 'the level/func_code scoping no longer isolates one row')
    lun = lun[0]
    H = d['headline']
    check('FY%d total per pupil' % FIN_FY, H['per_pupil'], lun['per_pupil'], 0.5)
    check('FY%d all-funds total' % FIN_FY, H['total'], lun['total'], 1.0)
    check('FY%d general fund' % FIN_FY, H['gen_fund'], lun['gen_fund'], 1.0)
    check('FY%d grants and revolving' % FIN_FY, H['grants_revolving'],
          lun['grants_revolving'], 1.0)
    check('FY%d grant share' % FIN_FY, H['grant_share'],
          round(lun['grants_revolving'] / lun['total'], 4), 0.0001)

    sw = q(db, "SELECT districts, per_pupil_p25 p25, per_pupil_median med, "
               "per_pupil_p75 p75, lunenburg_per_pupil lun, "
               "lunenburg_rank_of_districts rank FROM dese_function_statewide "
               "WHERE level='total' AND fy=?", FIN_FY)
    assert_true('one statewide total row for FY%d' % FIN_FY, len(sw) == 1,
                'the statewide distribution no longer has exactly one total row')
    sw = sw[0]
    rank, of = (int(x) for x in sw['rank'].split(' of '))
    check('statewide median', H['statewide_median'], sw['med'], 0.5)
    check('statewide rank', H['statewide_rank'], rank)
    check('districts ranked', H['statewide_of'], of)
    check('districts that spend less', H['statewide_spend_less'], of - rank)
    check('below the statewide median by', H['statewide_below_median'],
          sw['med'] - sw['lun'], 0.5)
    check('statewide lower quartile', H['statewide_p25'], sw['p25'], 0.5)

    # ---------------------------------------------- 2. the structural claims, asserted
    print('\n§2  The structural claims the sentences rest on')

    below = q(db, "SELECT fy, lunenburg_per_pupil lun, per_pupil_p25 p25 "
                  "FROM dese_function_statewide WHERE level='total' ORDER BY fy")
    assert_true('every published year has a Lunenburg figure and a quartile',
                all(r['lun'] is not None and r['p25'] is not None for r in below),
                'a year is missing one of the two, so "every year" cannot be asserted')
    under = [r['fy'] for r in below if r['lun'] < r['p25']]
    check('years below the statewide first quartile', H['bottom_quarter_years'], len(under))
    check('years published', H['bottom_quarter_of'], len(below))
    assert_true('below the first quartile in EVERY published year',
                len(under) == len(below),
                'the document says every year and the data now says %d of %d'
                % (len(under), len(below)))

    # Rank among the six, recomputed year by year with a plain sort rather than the
    # generator's ranked() helper.
    by_year = collections.defaultdict(list)
    for r in q(db, "SELECT fy, lea, per_pupil FROM dese_function_expenditure "
                   "WHERE level='total' AND func_code='TTPP'"):
        by_year[r['fy']].append(r)
    ranks = []
    for fy_, rows in by_year.items():
        order = sorted(rows, key=lambda r: -r['per_pupil'])
        ranks.append(next(i + 1 for i, r in enumerate(order) if r['lea'] == LEA))
    check('best rank in the six-district set', H['best_rank'], min(ranks))
    check('worst rank in the six-district set', H['worst_rank'], max(ranks))
    assert_true('never higher than %dth of six in any year' % min(ranks),
                min(ranks) >= 5, 'the document says fifth or sixth and nothing else')

    # The identity, written out again.
    fte = {}
    for r in q(db, "SELECT lea, fy, measure, value FROM dese_measure "
                   "WHERE measure IN ('In-District FTE Pupils','Total FTE Pupils')"):
        fte.setdefault((r['lea'], r['fy']), {})[r['measure']] = r['value']
    tot = {}
    for r in q(db, "SELECT lea, district, fy, total, per_pupil "
                   "FROM dese_function_expenditure WHERE level='total'"):
        tot[(r['lea'], r['fy'])] = r
    worst = 0.0
    for row in d['decomposition']:
        lea = next(x['lea'] for x in d['districts'] if x['district'] == row['district'])
        a, b = tot[(lea, BASE_FY)], tot[(lea, FIN_FY)]
        pa, pb = fte[(lea, BASE_FY)], fte[(lea, FIN_FY)]
        spend = b['total'] / a['total'] - 1
        pupils = pb['Total FTE Pupils'] / pa['Total FTE Pupils'] - 1
        pp = b['per_pupil'] / a['per_pupil'] - 1
        worst = max(worst, abs((1 + spend) / (1 + pupils) - 1 - pp))
        check('  %-30s spending' % row['district'], row['spend_pct'],
              round(spend, 4), 0.0001)
        check('  %-30s pupils' % row['district'], row['pupils_pct'],
              round(pupils, 4), 0.0001)
        check('  %-30s per pupil' % row['district'], row['per_pupil_pct'],
              round(pp, 4), 0.0001)
        check('  %-30s at FY%d pupils' % (row['district'], BASE_FY),
              row['at_old_enrolment'], round(b['total'] / pa['Total FTE Pupils']), 1)
    assert_true('(1+spending) / (1+pupils) = (1+per pupil), every district', worst < 0.005,
                'the identity the page rests on drifts by %.4f' % worst)

    # The category gaps SUM to the in-district gap.
    cats = q(db, "SELECT func_cat_code code, district, per_pupil "
                 "FROM dese_function_expenditure WHERE level='category' AND fy=?", FIN_FY)
    peer = d['category_headline']['median_peer']
    gapsum = sum(r['per_pupil'] for r in cats if r['district'] == TOWN) \
        - sum(r['per_pupil'] for r in cats if r['district'] == peer)
    ind = {r['district']: r['per_pupil'] for r in q(
        db, "SELECT district, per_pupil FROM dese_function_expenditure "
            "WHERE level='rollup' AND func_code='IIII' AND fy=?", FIN_FY)}
    check('the in-district gap to %s' % peer, d['category_headline']['gap'],
          ind[TOWN] - ind[peer], 0.5)
    assert_true('the eleven category gaps SUM to the in-district gap',
                abs(gapsum - (ind[TOWN] - ind[peer])) <= 1.0,
                'they sum to %.0f against a headline gap of %.0f'
                % (gapsum, ind[TOWN] - ind[peer]))
    assert_true('%s is the MEDIAN of the five comparison districts' % peer,
                abs(ind[peer] - statistics.median(
                    v for k, v in ind.items() if k != TOWN)) < 0.5,
                'the comparator is no longer the median district and the page says it is')
    check('the gap in dollars', d['category_headline']['gap_in_dollars'],
          round((ind[TOWN] - ind[peer]) * fte[(LEA, FIN_FY)]['In-District FTE Pupils']), 1)

    # The two denominators.
    print('\n§3  DESE prints one per-pupil column over two denominators')
    mism = []
    for r in q(db, "SELECT lea, district, fy, func_code, total, per_pupil "
                   "FROM dese_function_expenditure WHERE per_pupil > 0"):
        f = fte[(r['lea'], r['fy'])]
        want = f['Total FTE Pupils'] if r['func_code'] == 'TTPP' \
            else f['In-District FTE Pupils']
        if abs(r['total'] / want - r['per_pupil']) > 1.0:
            mism.append('%s FY%d %s' % (r['district'], r['fy'], r['func_code']))
    assert_true('the total is over TOTAL FTE and every other row over IN-DISTRICT FTE',
                not mism, 'it fails on %d row(s): %s' % (len(mism), mism[:5]))
    check('rows tested', d['denominators']['rows_tested'],
          len(q(db, "SELECT 1 FROM dese_function_expenditure WHERE per_pupil > 0")))
    # And the label in our own derived table is still the wrong one, so the paragraph
    # that says so is still true. If somebody fixes the extractor, this fires and the
    # paragraph gets rewritten rather than quietly becoming false.
    basis = {r['per_pupil_basis'] for r in q(
        db, "SELECT per_pupil_basis FROM dese_function_statewide "
            "WHERE level='total' AND fy=?", FIN_FY)}
    assert_true('our own basis label still reads in-district on the total row',
                basis == {d['denominators']['label_in_our_table']},
                'the label is now %s — the paragraph about it needs rewriting, not '
                'deleting' % sorted(basis))

    # The teacher identity.
    print('\n§4  DESE’s average teacher salary IS the Teachers spend per teacher FTE')
    tspend = {r['district']: r['total'] for r in q(
        db, "SELECT district, total FROM dese_function_expenditure "
            "WHERE level='category' AND func_cat_code='TCHR' AND fy=?", FIN_FY)}
    tm = collections.defaultdict(dict)
    for r in q(db, "SELECT district, measure, value FROM dese_measure WHERE fy=? AND "
                   "measure IN ('Average Teacher Salary','Teacher FTE',"
                   "'Teachers per 100 FTE students')", FIN_FY):
        tm[r['district']][r['measure']] = r['value']
    worst_t = 0.0
    for dist, v in tm.items():
        worst_t = max(worst_t, abs(1 - (tspend[dist] / v['Teacher FTE'])
                                   / v['Average Teacher Salary']))
    check('worst gap between the two', d['teachers_meta']['worst_gap'],
          round(worst_t, 4), 0.0005)
    assert_true('within 2% in every district', worst_t < 0.02,
                'the page calls the multiplication DESE’s own construction')
    # And the ratio's denominator, which the page names.
    ratio_bad = [dist for dist, v in tm.items()
                 if abs(100 * v['Teacher FTE']
                        / fte[(next(x['lea'] for x in d['districts']
                                    if x['district'] == dist), FIN_FY)]['In-District FTE Pupils']
                        - v['Teachers per 100 FTE students']) > 0.05]
    assert_true('teachers per 100 is over IN-DISTRICT FTE pupils', not ratio_bad,
                'it fails for %s and the page names that denominator' % ratio_bad)

    # ----------------------------------------------- 5. the rollup trap, from both sides
    print('\n§5  The rollup trap — a guard nobody can trip is not a guard')
    scoped = q(db, "SELECT SUM(total) t FROM dese_function_expenditure "
                   "WHERE lea=? AND fy=? AND level='total'", LEA, FIN_FY)[0]['t']
    unscoped = q(db, "SELECT SUM(total) t FROM dese_function_expenditure "
                     "WHERE lea=? AND fy=?", LEA, FIN_FY)[0]['t']
    assert_true('summing without a level filter really does give a different answer',
                unscoped > scoped * 2,
                'the levels no longer overlap, so the guard proves nothing (%.0f vs %.0f)'
                % (unscoped, scoped))
    check('the scoped total is the headline', scoped, lun['total'], 1.0)
    state = q(db, "SELECT COUNT(*) n FROM dese_ch70_formula WHERE level='state'")[0]['n']
    assert_true('the Chapter 70 table still carries a separable STATE row', state > 0,
                'every district query on the page excludes it by `level`')
    assert_true('and it is not in the finance table',
                not q(db, "SELECT 1 FROM dese_function_expenditure WHERE lea='00000000'"),
                'a state row there would be included by every district query')

    # ------------------------------------------------------------- 6. rule 1, the stages
    print('\n§6  Rule 1 — the stages are real and are never differenced')
    stage_rows = q(db, "SELECT fy, basis FROM dese_ch70_statewide "
                       "WHERE measure='net school spending as a share of required'")
    seen = collections.Counter(
        r['basis'][len('stage: '):] for r in stage_rows
        if r['basis'] and r['basis'].startswith('stage: '))
    assert_true('the net school spending measure carries more than one stage',
                len(seen) >= 2,
                'the page splits on it and rule 1 forbids differencing across it')
    check('stages counted', d['standing']['stages'], dict(seen))
    assert_true('the two collections are at DIFFERENT fiscal years',
                d['fin_fy'] != d['ch70_fy'],
                'the page says so explicitly and never subtracts one from the other')
    peer_stages = {r['stage'] for r in d['standing']['peers']}
    assert_true('every FY%d peer figure is at one stage' % CH70_FY, len(peer_stages) == 1,
                'the peer table compares across stages: %s' % sorted(peer_stages))

    # The standing figures themselves.
    print('\n§7  The two standings')
    for key, measure in (('nss', 'net school spending as a share of required'),
                         ('rlc', 'required local contribution as a share of the '
                                 'foundation budget')):
        row = q(db, "SELECT median, lunenburg, lunenburg_rank_of_districts rank "
                    "FROM dese_ch70_statewide WHERE fy=? AND measure=?",
                CH70_FY, measure)[0]
        r_, of_ = (int(x) for x in row['rank'].split(' of '))
        check('%s — Lunenburg' % key, d['standing'][key]['lunenburg'],
              row['lunenburg'], 0.00005)
        check('%s — statewide median' % key, d['standing'][key]['median'],
              row['median'], 0.00005)
        check('%s — rank' % key, d['standing'][key]['rank'], r_)
        check('%s — districts' % key, d['standing'][key]['districts'], of_)
        check('%s — districts above' % key, d['standing'][key]['above'], r_ - 1)

    T = d['standing']['target']
    con = q(db, "SELECT town_foundation_budget fb, target_local_contribution tlc, "
                "shortfall, dollar_increment, required_local_contribution rlc "
                "FROM dese_ch70_contribution WHERE fy=? AND municipality=?",
            CH70_FY, TOWN)[0]
    check('target local share', T['target_local_share'], round(con['tlc'] / con['fb'], 4),
          0.0001)
    check('actual required share', T['actual_local_share'],
          round(con['rlc'] / con['fb'], 4), 0.0001)
    check('points below target', T['points_below_target'],
          round((con['tlc'] - con['rlc']) / con['fb'] * 100, 2), 0.02)
    check('the shortfall', T['shortfall'], con['shortfall'], 1.0)
    check('this year’s increment', T['dollar_increment'], con['dollar_increment'], 1.0)
    assert_true('the requirement is BELOW the formula’s own target',
                con['rlc'] < con['tlc'],
                'the page calls the low required share a phase-in position')
    aid = q(db, "SELECT target_aid_pct FROM dese_ch70_aid_factor "
                "WHERE fy=? AND lea=? AND level='district'", CH70_FY, LEA)[0]
    assert_true('the formula treats Lunenburg as ABOVE-average wealth',
                aid['target_aid_pct'] < T['statewide_target_aid_pct'],
                'target aid %.1f%% against %.1f%% statewide — the paragraph says the '
                'formula treats the town as comparatively wealthy'
                % (aid['target_aid_pct'], T['statewide_target_aid_pct']))

    db.close()

    # ---------------------------------------------------- 8. the analysis document itself
    print('\n§8  Every figure typed into the analysis, derived and found')
    C = d['category_headline']
    L = d['lunenburg_denominator']
    lastyear = d['last_year']
    lun_row = next(r for r in lastyear if r['lea'] == LEA)
    next_lowest = lastyear[-2]
    states(flat, 'the headline per-pupil figure', usd(H['per_pupil']))
    states(flat, 'the statewide median', usd(H['statewide_median']))
    states(flat, 'the distance below it', usd(H['statewide_below_median']))
    states(flat, 'the statewide rank', H['statewide_rank'])
    states(flat, 'districts that spend less', H['statewide_spend_less'])
    states(flat, 'the next-lowest district', usd(next_lowest['per_pupil']))
    states(flat, 'the margin between them',
           usd(next_lowest['per_pupil'] - lun_row['per_pupil']))
    states(flat, 'the margin as a share',
           '%.1f%%' % (100 * (next_lowest['per_pupil'] / lun_row['per_pupil'] - 1)))
    states(flat, 'the all-funds total', usd(H['total']))
    states(flat, 'the grants and revolving total', usd(H['grants_revolving']))
    states(flat, 'the grant share', '%.1f%%' % (H['grant_share'] * 100))
    states(flat, 'the in-district figure', usd(C['lunenburg']))
    states(flat, 'the median district’s in-district figure', usd(C['peer']))
    states(flat, 'the gap per pupil', usd(abs(C['gap'])))
    states(flat, 'the gap in dollars', usd(abs(C['gap_in_dollars'])))
    states(flat, 'in-district FTE pupils', format(C['fte_in_district'], ','))
    for row in d['decomposition']:
        states(flat, '%s spending growth' % row['district'],
               '%.1f%%' % (row['spend_pct'] * 100))
        states(flat, '%s money at FY%d pupils' % (row['district'], BASE_FY),
               usd(row['at_old_enrolment']))
    for code in ('TCHR', 'SERV', 'LDRS', 'OPMN', 'MATL', 'PDEV', 'TSER'):
        row = next(c for c in d['categories'] if c['code'] == code)
        states(flat, '%s gap' % code, usd(abs(row['gap'])))
    for code in ('PDEV', 'MATL', 'TSER'):
        row = next(c for c in d['statewide_categories'] if c['code'] == code)
        states(flat, '%s statewide median' % code, usd(row['median']))
        states(flat, '%s Lunenburg' % code, usd(row['lunenburg']))
    lt = next(r for r in d['teachers'] if r['is_lunenburg'])
    states(flat, 'Lunenburg’s average teacher salary', usd(lt['average_salary']))
    states(flat, 'teachers per 100 in-district pupils', '%.2f' % lt['per_hundred'])
    states(flat, 'the worst gap in the teacher identity',
           '%.2f%%' % (d['teachers_meta']['worst_gap'] * 100))
    S = d['standing']
    states(flat, 'the required share', '%.1f%%' % (S['rlc']['lunenburg'] * 100))
    states(flat, 'the median required share', '%.1f%%' % (S['rlc']['median'] * 100))
    states(flat, 'net school spending of required', '%.4f' % S['nss']['lunenburg'])
    states(flat, 'the median multiple', '%.4f' % S['nss']['median'])
    states(flat, 'the target local share', '%.1f%%' % (T['target_local_share'] * 100))
    states(flat, 'points below target', '%.2f' % T['points_below_target'])
    states(flat, 'the shortfall', usd(T['shortfall']))
    states(flat, 'searchable meeting documents', format(d['minutes']['searchable'], ','))
    states(flat, 'meeting documents held', format(d['minutes']['held'], ','))
    states(flat, 'the denominator rows tested',
           format(d['denominators']['rows_tested'], ','))
    states(flat, 'the share of the ratio that is the denominator',
           '%.1f%%' % (L['denominator_share'] * 100))
    bene = next(c for c in d['categories'] if c['code'] == 'BENE')
    states(flat, 'the insurance and retirement line', usd(bene['lunenburg']))

    # And the structure a paragraph rests on, not only its figures.
    print('\n§9  The claims the document makes about itself')
    assert_true('the document says the measure is NOT the appropriation',
                'not the school appropriation' in flat,
                'rule 11’s caveat is the first thing this document owes a reader')
    assert_true('the document says it is not a scorecard',
                'It is not a scorecard' in flat,
                'rule 8 — a comparison left as a ranking is the failure mode here')
    assert_true('the document says the peer set is ours',
                'The set is ours' in flat or 'the set is ours' in flat,
                'rule 3 — a reader cannot judge the argument without knowing whose set '
                'this is')
    assert_true('the document says nothing tests spending against results',
                'no relation between spending and results' in flat
                or 'any relation between spending and results' in flat.lower(),
                'rule 7 — the page prints MCAS and must refuse the inference in words')

    # -------------------------------------------------------------- 10. rule 2, the page
    print('\n§10  Rule 2 — no figure typed into a sentence')
    money_re = re.compile(r'(?<![\w$])\$\s?\d[\d,]*(\.\d+)?')
    pct_re = re.compile(r'(?<![\w.])\d+(\.\d+)?\s?(%|percent\b)')
    # The one exemption is `100%`, which is a ResponsiveContainer dimension and a flex
    # width rather than a figure about the town.
    allowed = ('100%',)
    for path in (PAGE, CHARTS):
        src = open(path, encoding='utf-8').read()
        body = re.sub(r'/\*[\s\S]*?\*/', '', src)
        body = re.sub(r'^\s*//.*$', '', body, flags=re.M)
        for m in list(money_re.finditer(body)) + list(pct_re.finditer(body)):
            s = m.group(0).strip()
            if s in allowed:
                continue
            FAILS.append('%s carries a typed figure %r — rule 2 says derive it'
                         % (os.path.relpath(path, ROOT), s))
        print('  OK    %s' % os.path.relpath(path, ROOT))

    # ----------------------------------------------------------------- 11. rule 7c
    print('\n§11  Rule 7c — the limits are rows in the registry, not prose here')
    registry = {row['what']: row for row in csv.DictReader(open(GAPS, encoding='utf-8'))}
    for g in d['gaps']:
        present = g['what'] in registry
        assert_true('registered: %s' % g['what'][:56], present,
                    'the page cites a gap that is not in money-gaps.csv')
        if present:
            assert_true('  ...and it names the document that would close it',
                        '— closes:' in registry[g['what']]['why'],
                        'a gap with no named remedy is a grievance, not a records request')

    # ----------------------------------------------------------------- 12. rule 12
    print('\n§12  Rule 12 — every document travels with its hash and its address')
    man = {row['key']: row for row in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    for doc in d['documents']:
        present = doc['key'] in man
        assert_true('in the manifest: %s' % doc['filename'], present,
                    'the page cites a document the manifest does not describe')
        if present:
            check('  sha256 %s' % doc['filename'], doc['sha256'], man[doc['key']]['sha256'])
            check('  bytes  %s' % doc['filename'], doc['bytes'],
                  int(man[doc['key']]['bytes']))
            check('  address %s' % doc['filename'], doc['url'], man[doc['key']]['upstream'])

    # ----------------------------------------------------------------- 13. the personas
    print('\n§13  The persona review must have been run — notes/process/PERSONAS.md')
    page_src = open(PAGE, encoding='utf-8').read()
    page_body = ' '.join(re.sub(r'/\*[\s\S]*?\*/', '', page_src).split())
    NEEDED = [
        ('the worst fact is above the fold, not buried',
         'years below the statewide first quartile', page_body),
        ('the repeatable sentence is the true one, not “we are last”',
         'is a margin of', page_body),
        ('the reader close to the boards is not ambushed',
         'High in a small set and low in a large one is not a contradiction', page_body),
        ('the Finance Committee control question is answered',
         'What would you have had to see, and when', page_body),
        ('the page tells a board one thing it could do differently',
         'What this changes for planning', page_body),
        ('the town-versus-school frame is refused rather than fed',
         'Both are &ldquo;less&rdquo;, from different starting points', page_body),
        ('the district is given credit where it is doing the right thing',
         'is not in this data', page_body),
        ('a concrete thing somebody asked for, in a line called low',
         'Teachers and parents donate supplies', json.dumps(d['said'])),
    ]
    for label, needle, hay in NEEDED:
        ok = ' '.join(needle.split()) in ' '.join(hay.split())
        print('  %s  %s' % ('OK  ' if ok else 'GONE', label))
        if not ok:
            FAILS.append('persona review: "%s" — the text that satisfied it is gone'
                         % label)
    # Step 3, which has to be re-run rather than remembered: the page calls categories low,
    # so the meeting archive must have been searched about those categories.
    said_keys = {q_['key'] for q_ in d['said']}
    assert_true('the archive was searched about the lines called lowest',
                {'materials', 'sharing-pd', 'grant-pd'} <= said_keys,
                'the page names professional development and materials as the two lines '
                'furthest below the state and quotes nobody about either')
    assert_true('the searchable DENOMINATOR is published beside the searches',
                d['minutes']['searchable'] < d['minutes']['held'],
                'a grep that finds nothing prints nothing, and nothing reads as nobody '
                'said it')

    print()
    if FAILS:
        print('%d PROBLEM(S):' % len(FAILS))
        for f in FAILS:
            print('  - %s' % f)
        return 1
    print('every figure /what-other-districts-spend and '
          'sources/analyses/per-pupil-spending.md carry recomputes from the database.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
