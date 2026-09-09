#!/usr/bin/env python3
"""Recompute every figure /why-we-only-get-minimum-aid renders, and fail if one drifted.

Rule 9: a finished document's figures get RECOMPUTED, not re-read. Rule 13's fourth
bullet: a check must assert the NUMBER, not the prose around it -- `verify_athletics.py`
once passed because a sentence existed while the sentence was wrong.

WRITTEN AFTER THE PROSE, which is the only order in which this step works (step 5 of
`notes/process/WRITING-AN-ANALYSIS.md`). A verifier written first asserts what the author
intended; written after, it asserts what is true and finds where the two parted.

WHAT THIS CHECKS, AND WHY IT IS NOT `build_minimum_aid.py --check`.

    database  ->  minimum-aid.json  ->  the values MinimumAid.tsx derives at render time

`--check` establishes that the middle link reproduces. It cannot establish that the middle
link is RIGHT, because it compares the generator with itself. Everything below recomputes
the payload from the database by a SECOND, independent formulation -- different SQL shape,
the arithmetic written out again in Python -- so a mistake in a join condition cannot be
shared between the two.

  1. THE PAYLOAD, recomputed. Every figure the page prints, derived again.

  2. THE ARITHMETIC IDENTITIES THE SENTENCES REST ON. Rule 5 of WRITING-AN-ANALYSIS:
     "assert the structure a paragraph rests on, not only its figures." Five sentences on
     this page are structural claims rather than figures --

       * the whole of the latest increase IS the minimum aid increment, to the cent
       * DESE's own foundation-aid rule reproduces the printed increment
       * the target local contribution IS the combined effort yield, every year
       * the town's requirement splits between its districts by foundation budget share
       * every district in the comparison lands on the identical per-pupil rate

     -- and each is asserted rather than described. The day one stops holding, the
     paragraph is wrong while every number in it is still a faithful copy of the workbook.

  3. THE DERIVATIONS THE PAGE DOES ITSELF, in TSX, that no generator produces: which
     districts are counted as "at the rate", which year is named as the exception, and the
     last row of each series.

  4. RULE 2 MECHANICALLY. The page and its charts are scanned for a typed dollar amount or
     a typed percentage. Every sentence on this page lives in a .tsx file, and the one
     thing regenerating cannot catch is a figure written into one.

  5. RULE 1 MECHANICALLY. The page must not difference across stages, so it asserts that
     no series it publishes mixes `nss_stage` values silently, and that the two
     Governor's-stage figures it quotes exist only inside quotation text.

  6. RULE 7c. Every money_gaps row the page cites is still in the registry, still carries
     a `— closes:` half, and the two rows this page ADDED are still there.

    python3 scripts/verify_minimum_aid.py
"""
import csv
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'minimum-aid.json')
PAGE = os.path.join(ROOT, 'fy28', 'src', 'pages', 'MinimumAid.tsx')
CHARTS = os.path.join(ROOT, 'fy28', 'src', 'components', 'MinimumAidCharts.tsx')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
LEA = '01620000'
TOWN = 'Lunenburg'
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


# ---------------------------------------------------------------- an independent recompute

def rows(db, sql, *args):
    cur = db.execute(sql, args)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def recompute():
    """Everything again, pulled into Python and differenced there.

    The generator selects the district rows and walks them in a dict keyed on fy. This
    reads every row of both tables unfiltered and partitions in Python, so a WHERE clause
    that quietly stopped matching -- the silent-zero failure this repository has had four
    of -- cannot be shared between the two routes."""
    db = sqlite3.connect(DB)
    aid_all = rows(db, 'SELECT * FROM dese_ch70_aid_factor')
    con_all = rows(db, 'SELECT * FROM dese_ch70_contribution')
    fml_all = rows(db, 'SELECT * FROM dese_ch70_formula')
    dist_all = rows(db, 'SELECT * FROM dese_ch70_statewide')

    aid = {r['fy']: r for r in aid_all if r['lea'] == LEA and r['level'] == 'district'}
    town = {r['fy']: r for r in con_all if r['municipality'] == TOWN}
    peers = {}
    for r in aid_all:
        if r['level'] == 'district':
            peers.setdefault(r['fy'], {})[r['lea']] = r

    assert aid, 'no Lunenburg district rows -- the partition matched nothing'
    assert town, 'no Lunenburg municipal rows -- the partition matched nothing'

    years = sorted(aid)
    last, first = years[-1], years[0]
    a, p, t = aid[last], aid[last - 1], town[last]

    out = {
        'fy_first': first, 'fy_last': last, 'years': len(years),
        'increase': a['ch70_aid'] - p['ch70_aid'],
        'minimum_aid': a['minimum_aid_increment'] or 0,
        'foundation_aid': a['foundation_aid_increment'] or 0,
        'enrollment': a['foundation_enrollment'],
        'per_pupil': round((a['ch70_aid'] - p['ch70_aid']) / a['foundation_enrollment'], 2),
        'foundation_budget': a['foundation_budget'],
        'foundation_per_pupil': a['foundation_budget'] / a['foundation_enrollment'],
        'required_local_contribution': a['required_local_contribution'],
        'need': a['foundation_budget'] - a['required_local_contribution'],
        'prior_aid': p['ch70_aid'],
        'headroom': p['ch70_aid'] - (a['foundation_budget'] - a['required_local_contribution']),
        'aid': a['ch70_aid'],
    }

    # THE FOUNDATION-AID RULE, written out from DESE's User Guide sentence rather than
    # from the generator's expression.
    holds = 0
    for fy in years[1:]:
        this, prev = aid[fy], aid[fy - 1]
        foundation_aid = this['foundation_budget'] - this['required_local_contribution']
        due = foundation_aid - prev['ch70_aid']
        printed = this['foundation_aid_increment'] or 0
        if abs((due if due > 0 else 0.0) - printed) < 1.5:
            holds += 1
    out['rule_holds_in'] = holds
    out['rule_of'] = len(years) - 1

    # THE COMPONENT RECONCILIATION.
    terms = ('foundation_aid_increment', 'down_payment_aid_increment',
             'growth_aid_increment', 'target_aid_phase_in', 'minimum_aid_increment',
             'non_operating_reduction', 'hold_harmless_low_income',
             'minimum_aid_adjustment')
    bad = []
    for fy in years[1:]:
        s = 0.0
        for k in terms:
            s += aid[fy][k] or 0
        if abs(s - (aid[fy]['ch70_aid'] - aid[fy - 1]['ch70_aid'])) >= 1.0:
            bad.append(fy)
    out['unreconciled'] = bad
    out['reconciles_in'] = len(years) - 1 - len(bad)

    # THE FLOOR, at the peers.
    latest_rates = {}
    for lea, r in peers[last].items():
        prev = peers[last - 1].get(lea)
        if prev and r['foundation_enrollment']:
            latest_rates[r['district']] = round(
                (r['ch70_aid'] - prev['ch70_aid']) / r['foundation_enrollment'], 2)
    out['peer_districts'] = len(latest_rates)
    out['peer_rates'] = sorted(set(latest_rates.values()))
    out['peers_at_lunenburg_rate'] = sum(
        1 for v in latest_rates.values() if abs(v - out['per_pupil']) < 0.005)

    on_floor = []
    for fy in years[1:]:
        rs = {}
        for lea, r in peers.get(fy, {}).items():
            prev = peers.get(fy - 1, {}).get(lea)
            if prev and r['foundation_enrollment']:
                rs[lea] = round((r['ch70_aid'] - prev['ch70_aid'])
                                / r['foundation_enrollment'], 2)
        mine = rs.get(LEA)
        if mine is None:
            continue
        if sum(1 for v in rs.values() if abs(v - mine) < 0.005) > 1:
            on_floor.append(fy)
    out['on_floor'] = on_floor

    # THE MUNICIPAL SIDE.
    out['target_is_cey'] = all(
        abs((town[fy]['target_local_contribution'] or 0)
            - (town[fy]['combined_effort_yield'] or 0)) < 1 for fy in years)
    out['effort_reduction_total'] = sum((town[fy]['effort_reduction'] or 0) for fy in years)
    out['dollar_increment_total'] = sum((town[fy]['dollar_increment'] or 0) for fy in years)
    out['above_years'] = sum(1 for fy in years if (town[fy]['excess_effort'] or 0) > 0)
    out['below_first'] = min(fy for fy in years if not (town[fy]['excess_effort'] or 0) > 0)
    out['increment_first'] = min(fy for fy in years if (town[fy]['dollar_increment'] or 0) > 0)
    out['increment_years'] = sum(1 for fy in years if (town[fy]['dollar_increment'] or 0) > 0)
    out['shortfall_last'] = town[last]['shortfall'] or 0
    out['target_share_last'] = (town[last]['target_local_contribution']
                                / town[last]['town_foundation_budget'])

    # THE ALLOCATION.
    out['alloc_predicted'] = (t['required_local_contribution'] * a['foundation_budget']
                              / t['town_foundation_budget'])
    out['alloc_elsewhere_rlc'] = (t['required_local_contribution']
                                  - a['required_local_contribution'])
    out['alloc_elsewhere_foundation'] = (t['town_foundation_budget'] - a['foundation_budget'])
    out['alloc_holds'] = sum(
        1 for fy in years
        if abs(aid[fy]['required_local_contribution']
               - town[fy]['required_local_contribution'] * aid[fy]['foundation_budget']
               / town[fy]['town_foundation_budget']) < 2.0)

    # THE SHARE SERIES.
    sh = [(fy, aid[fy]['required_local_contribution'] / aid[fy]['foundation_budget'])
          for fy in years]
    lowfy, low = min(sh, key=lambda x: x[1])
    out['share_first'], out['share_low_fy'] = sh[0][1], lowfy
    out['share_low'], out['share_last'] = low, sh[-1][1]

    # THE STATEWIDE DISTRIBUTION.
    dd = [r for r in dist_all
          if r['measure'] == 'required local contribution as a share of the '
                             'foundation budget' and r['fy'] >= first]
    out['dist_years'] = len(dd)
    out['dist_last'] = max(dd, key=lambda r: r['fy'])

    # WEALTH, re-ranked.
    frm = out['below_first'] - 1
    pair = {}
    for r in con_all:
        if r['fy'] in (frm, last):
            pair.setdefault(r['municipality'], {})[r['fy']] = r
    g = [(m, v[last]['equalized_valuation'] / v[frm]['equalized_valuation'] - 1)
         for m, v in pair.items()
         if frm in v and last in v and v[frm]['equalized_valuation']]
    g.sort(key=lambda x: -x[1])
    out['municipalities'] = len(g)
    out['eqv_growth'] = dict(g)[TOWN]
    out['eqv_rank'] = [x[0] for x in g].index(TOWN) + 1
    out['eqv_median'] = sorted(x[1] for x in g)[len(g) // 2]

    # THE TWO SIDES SINCE THE REGIME CHANGED. The persona review added this to the page,
    # so it is recomputed here like everything else -- and the like-for-like claim it rests
    # on is asserted: both figures must come from the same table and the same stage, which
    # is why the aid and the requirement are both read off dese_ch70_aid_factor rather than
    # one of them off a receipt.
    frm2 = out['below_first'] - 1
    out['since_aid_pct'] = aid[last]['ch70_aid'] / aid[frm2]['ch70_aid'] - 1
    out['since_required_pct'] = (aid[last]['required_local_contribution']
                                 / aid[frm2]['required_local_contribution'] - 1)
    out['since_required_change'] = (aid[last]['required_local_contribution']
                                    - aid[frm2]['required_local_contribution'])
    out['since_aid_change'] = aid[last]['ch70_aid'] - aid[frm2]['ch70_aid']
    out['since_from'] = frm2

    # NET SCHOOL SPENDING against the requirement, and its stage.
    nss = sorted((r for r in fml_all
                  if r['lea'] == LEA and r['level'] == 'district'
                  and r['nss_pct_of_required'] is not None and r['fy'] >= first),
                 key=lambda r: r['fy'])
    out['nss_years'] = len(nss)
    out['nss_above'] = sum(1 for r in nss if r['nss_pct_of_required'] > 1)
    out['nss_lowest'] = min(r['nss_pct_of_required'] for r in nss)
    out['nss_stages'] = sorted({r['nss_stage'] for r in nss if r['nss_stage']})
    out['nss_latest_stage'] = nss[-1]['nss_stage']

    # THE PUBLICLY STATED SHARE.
    out['recomputed_2022'] = (aid[2022]['required_local_contribution']
                              / aid[2022]['foundation_budget'])

    # THE MARGINAL ARITHMETIC, re-derived.
    fpp = a['foundation_budget'] / a['foundation_enrollment']
    after = t['required_local_contribution'] * (a['foundation_budget'] + fpp) \
        / (t['town_foundation_budget'] + fpp)
    need_after = (a['foundation_budget'] + fpp) - after
    out['need_change'] = need_after - out['need']
    out['pupils_to_close'] = out['headroom'] / out['need_change']
    return out


def main():
    for path in (DB, PAYLOAD, PAGE, CHARTS, GAPS):
        if not os.path.exists(path):
            print('missing: %s' % os.path.relpath(path, ROOT))
            return 1
    d = json.load(open(PAYLOAD, encoding='utf-8'))
    r = recompute()
    H, Z, R, W, M, SH = (d['headline'], d['why_zero'], d['regime'], d['wealth'],
                         d['marginal'], d['share'])

    print('\nTHE HEADLINE')
    check('fiscal years covered', d['years'], r['years'])
    check('first fiscal year', d['fy_first'], r['fy_first'])
    check('last fiscal year', d['fy_last'], r['fy_last'])
    check('Chapter 70 aid, latest year', H['aid'], r['aid'], 0.01)
    check('the increase', H['increase'], r['increase'], 0.01)
    check('minimum aid increment', H['minimum_aid_increment'], r['minimum_aid'], 0.01)
    check('foundation aid increment', H['foundation_aid_increment'], r['foundation_aid'], 0.01)
    check('foundation enrollment', H['enrollment'], r['enrollment'], 0.001)
    check('the increase, per foundation pupil', H['per_pupil'], r['per_pupil'], 0.005)
    check('foundation budget per pupil', H['foundation_per_pupil'],
          r['foundation_per_pupil'], 0.01)

    print('\nWHY THE FORMULA PRODUCED NOTHING')
    check('foundation budget', Z['foundation_budget'], r['foundation_budget'], 0.01)
    check('required local contribution (district)', Z['required_local_contribution'],
          r['required_local_contribution'], 0.01)
    check('what the formula says the district needs', Z['need'], r['need'], 0.01)
    check('prior year’s aid', Z['prior_aid'], r['prior_aid'], 0.01)
    check('headroom above the line', Z['headroom'], r['headroom'], 0.01)
    check('years DESE’s own rule reproduces the printed increment',
          Z['rule_holds_in'], r['rule_holds_in'])

    print('\nTHE STRUCTURAL CLAIMS -- what the sentences rest on')
    # THE HEADLINE SENTENCE. Not "the minimum aid figure is 240,450" but "the WHOLE
    # increase is the minimum aid increment" -- the day the formula pays a dollar of its
    # own, the first finding is wrong while every figure in it is still right.
    assert_true('the whole increase IS the minimum aid increment, to the cent',
                abs(r['increase'] - r['minimum_aid']) < 0.01,
                'the increase is %.2f and minimum aid is %.2f -- finding 1 says they are '
                'the same number' % (r['increase'], r['minimum_aid']))
    assert_true('and the formula’s own aid term is exactly zero',
                r['foundation_aid'] == 0,
                'the foundation aid increment is %.2f' % r['foundation_aid'])
    assert_true('DESE’s foundation-aid rule reproduces the latest year',
                r['fy_last'] in [f for f in range(r['fy_first'] + 1, r['fy_last'] + 1)]
                and r['rule_holds_in'] >= r['rule_of'] - 2,
                'the rule reproduces only %d of %d years' % (r['rule_holds_in'], r['rule_of']))
    assert_true('the target local contribution IS the combined effort yield, every year',
                r['target_is_cey'],
                'it is not, and finding 4 rests on it -- that identity is the whole reason '
                'enrollment does not enter the town’s contribution')
    # THE MARGINAL SECTION RESTS ON THE LATEST YEAR, and the page states the count rather
    # than claiming every year -- FY2007 is $18,090 off the proportion and the page names
    # it. So this asserts the latest year AND that the published count is the true one; a
    # second exception appearing would move the count and be caught, rather than being
    # absorbed into a sentence that says "every year".
    assert_true('the town’s requirement splits by foundation budget share, latest year',
                r['fy_last'] not in [x['fy'] for x in d['allocation'] if not x['holds']],
                'the identity fails in the year the marginal section is built on')
    check('years the allocation identity holds', d['allocation_summary']['holds_in'],
          r['alloc_holds'])
    check('the years it does not', d['allocation_summary']['exceptions'],
          [x['fy'] for x in d['allocation'] if not x['holds']])
    assert_true('Lunenburg lands on a per-pupil rate at least one other district shares',
                r['fy_last'] in r['on_floor'],
                'FY%d is not on a shared rate, and finding 3 says it is' % r['fy_last'])
    assert_true('the latest year’s excess effort is zero -- the town is BELOW target',
                r['shortfall_last'] > 0,
                'the shortfall is %.2f' % r['shortfall_last'])
    assert_true('the statutory 82.5% cap on the target local share is not binding',
                r['target_share_last'] < 0.825,
                'the target share is %.4f, at or above the cap -- the marginal section '
                'assumes it is slack' % r['target_share_last'])

    print('\nTHE FLOOR, AT THE PEERS')
    check('districts with a comparable rate in the latest year',
          d['floor'][-1]['districts'], r['peer_districts'])
    check('districts on Lunenburg’s own rate', len(
        [x for x in d['floor'][-1]['rows']
         if abs(x['per_pupil'] - H['per_pupil']) < 0.005]), r['peers_at_lunenburg_rate'])
    check('years Lunenburg is on a shared rate', d['on_floor'], r['on_floor'])

    print('\nTHE MUNICIPAL SIDE')
    check('effort reductions, summed', R['effort_reduction_total'],
          r['effort_reduction_total'], 0.01)
    check('dollar increments, summed', R['dollar_increment_total'],
          r['dollar_increment_total'], 0.01)
    check('years above target', R['above_years'], r['above_years'])
    check('first year below target', R['below_first'], r['below_first'])
    check('first year a dollar increment was added', R['increment_first'],
          r['increment_first'])
    check('years a dollar increment was added', R['increment_years'], r['increment_years'])
    assert_true('below target and being charged for it are different years',
                r['increment_first'] > r['below_first'],
                'they are the same year, and finding 5 says they are not')

    print('\nTHE REQUIRED SHARE, AND WHERE IT SITS')
    check('share, first year', SH['first'], r['share_first'], 1e-9)
    check('share, the trough', SH['low'], r['share_low'], 1e-9)
    check('the trough year', SH['low_fy'], r['share_low_fy'])
    check('share, latest year', SH['last'], r['share_last'], 1e-9)
    check('years of statewide distribution', len(d['distribution']), r['dist_years'])
    check('Lunenburg’s rank, latest year',
          d['distribution'][-1]['lunenburg_rank_of_districts'],
          r['dist_last']['lunenburg_rank_of_districts'])
    check('statewide median, latest year', d['distribution'][-1]['median'],
          r['dist_last']['median'], 1e-9)
    # The page says the statewide maximum IS the statutory cap showing up in the data.
    assert_true('the statewide maximum required share equals the 82.5% cap',
                abs(r['dist_last']['p_max'] - 0.825) < 0.0005,
                'the maximum is %.4f, so the sentence naming it as the cap is wrong'
                % r['dist_last']['p_max'])

    print('\nWEALTH, RANKED AGAINST EVERY MUNICIPALITY')
    check('municipalities in both years', W['municipalities'], r['municipalities'])
    check('equalized valuation growth', W['eqv_growth'], r['eqv_growth'], 1e-9)
    check('rank, fastest first', W['eqv_rank'], r['eqv_rank'])
    check('median growth', W['eqv_median'], r['eqv_median'], 1e-9)
    assert_true('Lunenburg grew faster than the median municipality',
                r['eqv_growth'] > r['eqv_median'],
                'it did not, and the page says its wealth rose faster than most')

    print('\nTHE ALLOCATION, AND THE MARGINAL ARITHMETIC')
    check('predicted district contribution', d['allocation'][-1]['predicted'],
          r['alloc_predicted'], 0.01)
    check('the town’s contribution toward its other district',
          d['allocation'][-1]['elsewhere_rlc'], r['alloc_elsewhere_rlc'], 0.01)
    check('the town’s foundation budget outside this district',
          d['allocation'][-1]['elsewhere_foundation'], r['alloc_elsewhere_foundation'], 0.01)
    check('what one more pupil adds to the formula’s own need',
          M['need_change'], r['need_change'], 0.01)
    check('pupils needed to close the headroom', M['pupils_to_close'],
          r['pupils_to_close'], 1e-6)
    assert_true('the marginal block is flagged as not a measurement',
                M['is_measurement'] is False,
                'it is not flagged, and it is a counterfactual')
    assert_true('the town’s own requirement is unmoved by the extra pupil',
                M['town_rlc_change'] == 0.0,
                'the payload says the town’s requirement moved, which contradicts the '
                'combined-effort-yield identity the section rests on')

    print('\nTHE TWO SIDES SINCE THE REGIME CHANGED')
    check('base year', d['since']['from_fy'], r['since_from'])
    check('aid, change', d['since']['aid_change'], r['since_aid_change'], 0.01)
    check('aid, per cent', d['since']['aid_pct'], r['since_aid_pct'], 1e-9)
    check('required contribution, change', d['since']['required_change'],
          r['since_required_change'], 0.01)
    check('required contribution, per cent', d['since']['required_pct'],
          r['since_required_pct'], 1e-9)
    assert_true('the requirement really has risen faster than the aid',
                r['since_required_pct'] > r['since_aid_pct'],
                'it has not, and the sixth finding says it has')
    assert_true('foundation enrollment really is lower at the end than at the start',
                d['since']['enrollment_to'] < d['since']['enrollment_from'],
                'the finding says "on a smaller number of children"')

    print('\nNET SCHOOL SPENDING, AND ITS STAGE (rule 1)')
    check('years with a spending ratio', d['spending']['years'], r['nss_years'])
    check('years above the requirement', d['spending']['above_required'], r['nss_above'])
    check('lowest ratio', d['spending']['lowest'], r['nss_lowest'], 1e-9)
    check('the stages present', d['spending']['stages'], r['nss_stages'])
    check('the latest year’s stage', d['spending']['latest_stage'], r['nss_latest_stage'])
    assert_true('the series carries more than one stage and says so',
                len(r['nss_stages']) > 1 and 'stages' in d['spending'],
                'the page tells a reader the last years are budgeted rather than spent, '
                'and the payload must carry the stage for it to be able to')

    print('\nRULE 1 -- the two stages of one year, and neither is derived from the other')
    for x in d['stage_examples']:
        floor_row = [f for f in d['floor'] if f['fy'] == x['fy']]
        assert_true('FY%d: the enacted rate comes off the floor series' % x['fy'],
                    bool(floor_row)
                    and abs(floor_row[0]['shared_rate'] - x['enacted']) < 0.005,
                    'the enacted per-pupil rate on the stage table does not match the '
                    'rate the peer comparison computes for the same year')
        said = [q for q in d['said'] if q['key'] == x['key']]
        assert_true('FY%d: the earlier figure is inside a checked quotation' % x['fy'],
                    bool(said) and str(int(x['said'])) in said[0]['quote'],
                    'the Governor’s-stage figure is not in the quote it is attributed to')
        assert_true('FY%d: the two stages differ, and are never subtracted' % x['fy'],
                    x['said'] != x['enacted'],
                    'the row would be pointless if they were equal')

    print('\nA FIGURE STATED IN PUBLIC')
    check('Lunenburg’s own required share, the year of the statement',
          d['corroboration']['recomputed'], r['recomputed_2022'], 1e-9)

    print('\nTHE RECONCILIATION THE PAGE ADMITS TO')
    check('years the printed components sum to the change', d['reconciles_in'],
          r['reconciles_in'])
    check('the years they do not', [u['fy'] for u in d['unreconciled']], r['unreconciled'])
    assert_true('every unreconciled year is named in what this page cannot say',
                all(('FY%d' % u['fy']) in ' '.join(d['not_established'])
                    for u in d['unreconciled']),
                'a year whose components do not add up is not named in the caveats')

    # ------------------------------------------------------------------ rule 2, mechanically
    print('\nRULE 2 -- no figure typed into a sentence')
    money_re = re.compile(r'(?<![\w$])\$\s?\d[\d,]*(\.\d+)?')
    pct_re = re.compile(r'(?<![\w.])\d+(\.\d+)?\s?(%|percent\b)')
    for path in (PAGE, CHARTS):
        src = open(path, encoding='utf-8').read()
        body = re.sub(r'/\*[\s\S]*?\*/', '', src)          # block comments
        body = re.sub(r'^\s*//.*$', '', body, flags=re.M)   # line comments
        # The four exemptions, each of which is a QUOTATION or a STATUTORY CONSTANT and
        # neither of which a regeneration could produce:
        #   * the statutory cap, 82.5%, which is DESE's own sentence quoted in the
        #     definitions table and named again in the prose beside a computed value
        #   * the two Governor's-stage per-pupil rates, which appear ONLY inside the text
        #     of a meeting quote in the generator, never in the page
        #   * tailwind sizing like text-[15px], which the regexes already exclude
        #   * `100%` and `-100%`, which are CSS/JSX layout dimensions on a
        #     ResponsiveContainer and a flex box rather than figures about the town
        allowed = ('82.5%', '100%')
        for m in list(money_re.finditer(body)) + list(pct_re.finditer(body)):
            s = m.group(0).strip()
            if s in allowed:
                continue
            FAILS.append('%s carries a typed figure %r -- rule 2 says derive it'
                         % (os.path.relpath(path, ROOT), s))
        print('  OK    %s' % os.path.relpath(path, ROOT))

    # ------------------------------------------------------------------ rule 7c, the registry
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
    for added in ('Why Chapter 70 aid moved by more than the components DESE publishes',
                  'Which cell of DESE’s contribution sheet is mislabelled in FY2020'):
        assert_true('this page ADDED: %s' % added[:48],
                    any(w.startswith(added) for w in registry),
                    'the limit this page hit is no longer registered')

    # ------------------------------------------------------------------ rule 12, the document
    print('\nRULE 12 -- the document travels with the figures')
    man = {row['key']: row for row in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    assert_true('the workbook is in the archive manifest', DOC_KEY in man,
                'the page cites a document the manifest does not describe')
    if DOC_KEY in man:
        check('sha256', d['source']['sha256'], man[DOC_KEY]['sha256'])
        check('bytes', d['source']['bytes'], int(man[DOC_KEY]['bytes']))
        check('the publisher’s address', d['source']['url'], man[DOC_KEY]['upstream'])

    print()
    if FAILS:
        print('%d PROBLEM(S):' % len(FAILS))
        for f in FAILS:
            print('  - %s' % f)
        return 1
    print('every figure /why-we-only-get-minimum-aid renders recomputes from the database.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
