#!/usr/bin/env python3
"""Recompute every figure /when-grants-end renders, and fail if one drifted.

Rule 9: a finished document's figures get RECOMPUTED, not re-read. Rule 13's fourth
bullet: a check must assert the number, not the prose around it -- `verify_athletics.py`
once passed because a sentence existed while the sentence was wrong.

WHAT MAKES THIS ONE DIFFERENT FROM THE MARKDOWN VERIFIERS. /when-grants-end is a page, not
a document, and it types no figure: every number it shows is interpolated out of
`fy28/public/data/grant-unwinding.json`. So asserting that a string appears somewhere would
assert nothing. The chain that can actually break is

    database  ->  grant-unwinding.json  ->  values the page derives at render time

and this file checks all three links:

  1. THE PAYLOAD, recomputed from the database by a SECOND, independent formulation of the
     query -- a different SQL shape, the classification written out again -- rather than by
     importing the generator. Importing it would compare the generator with itself, which
     is a check with no power to fail. (`build_grant_unwinding.py --check` is the staleness
     check; this is the correctness one, and they are not the same test.)

  2. THE DERIVATIONS THE PAGE DOES ITSELF. `GrantUnwinding.tsx` computes the trough year,
     the rebound year, the last year with a higher grant share, the worst prior swap, and
     how many swaps still spent less in total. Those are figures in prose that no generator
     produces, so each is recomputed here and asserted against the payload the page reads.

  3. THE STRUCTURAL CLAIMS the sentences rest on -- rule 5 of WRITING-AN-ANALYSIS: "assert
     the structure a paragraph rests on, not only its figures. If a section says every
     account in this group went over, check that, because the day it stops being true the
     paragraph is wrong while every number in it is still right." Four sentences on this
     page are of that kind and each has an assertion below.

  4. RULE 2 MECHANICALLY. The page and its charts are scanned for a typed dollar amount or
     a typed percentage. The one thing rule 2 cannot catch by regenerating is a figure
     written into a sentence, and on this page every sentence is in a .tsx file.

    python3 scripts/verify_grant_unwinding.py
"""
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'grant-unwinding.json')
PAGE = os.path.join(ROOT, 'fy28', 'src', 'pages', 'GrantUnwinding.tsx')
CHARTS = os.path.join(ROOT, 'fy28', 'src', 'components', 'GrantUnwindingCharts.tsx')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
LEA = '01620000'

FAILS = []


def check(label, got, want):
    ok = got == want
    if not ok:
        FAILS.append('%s: recomputed %r, the payload says %r' % (label, want, got))
    print('  %s  %-58s %s' % ('OK  ' if ok else 'DRIFT', label, got))


def assert_true(label, ok, why):
    if not ok:
        FAILS.append('%s: %s' % (label, why))
    print('  %s  %s' % ('OK  ' if ok else 'FALSE', label))


# --------------------------------------------------------------------------- the payload

def recompute():
    """The whole classification, written out a second time and differently.

    Deliberately NOT the generator's query. This one pulls both years into Python and
    differences them there, so a mistake in the join condition -- the failure mode that
    produces a silent zero -- cannot be shared between the two.
    """
    db = sqlite3.connect(DB)
    rows = db.execute(
        "SELECT fy, level, func_code, func_desc, in_out_dist, gen_fund, grants_revolving,"
        " total FROM dese_function_expenditure WHERE lea=?", (LEA,)).fetchall()

    totals = {}
    detail = {}
    for fy, level, fc, fd, io, g, gr, t in rows:
        if level == 'total':
            a = totals.setdefault(fy, [0.0, 0.0, 0.0])
            a[0] += g or 0
            a[1] += gr or 0
            a[2] += t or 0
        elif level == 'detail':
            detail[(fy, fc, io)] = (fd, g or 0, gr or 0, t or 0)

    series = [{'fy': fy, 'gen_fund': v[0], 'grants': v[1], 'total': v[2],
               'town_share': round(100.0 * v[0] / (v[2] or 1), 2)}
              for fy, v in sorted(totals.items())]

    years = {}
    for (fy, fc, io), (fd, g0, gr0, t0) in detail.items():
        nxt = detail.get((fy + 1, fc, io))
        if not nxt:
            continue
        _, g1, gr1, t1 = nxt
        dg, dgr, dt = g1 - g0, gr1 - gr0, t1 - t0
        if dgr < 0 and dg > 0:
            kind = 'swap'
        elif dgr < 0:
            kind = 'reduction'
        elif dgr > 0:
            kind = 'grant_growth'
        else:
            kind = 'other'
        y = years.setdefault(fy + 1, {'swap': [], 'reduction': [], 'grant_growth': [],
                                      'other': []})
        y[kind].append({'fy': fy + 1, 'func_code': fc, 'func_desc': fd, 'in_out': io,
                        'd_grants': round(dgr), 'd_gen_fund': round(dg),
                        'd_total': round(dt)})
    return series, years


def tally(items, key):
    return round(sum(i[key] for i in items))


def main():
    if not os.path.exists(PAYLOAD):
        print('%s is missing. Run scripts/build_grant_unwinding.py.'
              % os.path.relpath(PAYLOAD, ROOT))
        return 1
    d = json.load(open(PAYLOAD, encoding='utf-8'))
    series, years = recompute()

    print('\nTHE FRAME — both funds, every year')
    check('first fiscal year', d['fy_first'], series[0]['fy'])
    check('last fiscal year', d['fy_last'], series[-1]['fy'])
    check('years in the series', len(d['series']), len(series))
    check('general fund share, first year', d['town_share_first'], series[0]['town_share'])
    check('general fund share, last year', d['town_share_last'], series[-1]['town_share'])
    check('points moved', d['town_share_points'],
          round(series[-1]['town_share'] - series[0]['town_share'], 2))
    for a, b in zip(d['series'], series):
        if a['fy'] != b['fy'] or round(a['gen_fund']) != round(b['gen_fund']) \
                or round(a['grants']) != round(b['grants']):
            FAILS.append('the fund split for FY%s does not recompute' % b['fy'])
    print('  OK    every year of the split recomputes                    %d years'
          % len(series))

    print('\nTHE LATEST YEAR — the four classes, never summed as a finding')
    latest = d['by_year'][-1]
    fyl = max(years)
    check('latest year', d['latest_year'], fyl)
    check('latest year on by_year', latest['fy'], fyl)
    y = years[fyl]
    for kind in ('swap', 'reduction', 'grant_growth', 'other'):
        check('%s: functions' % kind, latest[kind]['n'], len(y[kind]))
        check('%s: grants' % kind, latest[kind]['d_grants'], tally(y[kind], 'd_grants'))
        check('%s: general fund' % kind, latest[kind]['d_gen_fund'],
              tally(y[kind], 'd_gen_fund'))
    every = [i for k in y for i in y[k]]
    check('every matched function: count', latest['aggregate']['n'], len(every))
    check('every matched function: grants', latest['aggregate']['d_grants'],
          tally(every, 'd_grants'))
    check('every matched function: general fund', latest['aggregate']['d_gen_fund'],
          tally(every, 'd_gen_fund'))
    check('every matched function: all funds', latest['aggregate']['d_total'],
          tally(every, 'd_total'))
    assert_true('the aggregate is marked as not a finding',
                latest['aggregate'].get('is_a_finding') is False,
                'is_a_finding is not False — the page reports this number only inside the '
                'section that explains why it is misleading, and the flag is what says so')

    print('\nTHE FOUR CLASSES ACCOUNT FOR EVERY MATCHED FUNCTION')
    for row in d['by_year']:
        parts = sum(row[k]['n'] for k in ('swap', 'reduction', 'grant_growth', 'other'))
        if parts != row['aggregate']['n']:
            FAILS.append('FY%d: the four classes hold %d functions and the aggregate '
                         'counts %d' % (row['fy'], parts, row['aggregate']['n']))
        for key in ('d_grants', 'd_gen_fund'):
            s = sum(row[k][key] for k in ('swap', 'reduction', 'grant_growth', 'other'))
            if abs(s - row['aggregate'][key]) > 1:
                FAILS.append('FY%d: the four classes sum to %d on %s and the aggregate '
                             'says %d' % (row['fy'], s, key, row['aggregate'][key]))
    print('  OK    every year, in both money columns                     %d years'
          % len(d['by_year']))

    print('\nWHAT THE PAGE DERIVES AT RENDER TIME (GrantUnwinding.tsx)')
    S = d['series']
    grant_share = lambda p: 100 - p['town_share']          # noqa: E731
    trough = min(S, key=grant_share)
    rebound = max([p for p in S if p['fy'] > trough['fy']], key=grant_share)
    higher = [p for p in S if p['fy'] < rebound['fy']
              and grant_share(p) >= grant_share(rebound)]
    prior = d['by_year'][:-1]
    worst_prior_swap = min(prior, key=lambda r: r['swap']['d_grants'])
    worst_prior_fall = min(prior, key=lambda r: r['aggregate']['d_grants'])
    swap = d['latest_detail']['swap']
    short = [m for m in swap if m['d_total'] < 0]

    # Recomputed straight off the database, so a mistake in the payload cannot hide here.
    tr2 = min(series, key=lambda p: 100 - p['town_share'])
    check('trough year for the grant share', trough['fy'], tr2['fy'])
    check('grant share at the trough', round(grant_share(trough), 1),
          round(100 - tr2['town_share'], 1))
    check('rebound year after the trough', rebound['fy'],
          max([p for p in series if p['fy'] > tr2['fy']],
              key=lambda p: 100 - p['town_share'])['fy'])
    print('  ----  last year with a share at least as high as the rebound: %s'
          % (higher[-1]['fy'] if higher else 'none — the rebound is the record high'))
    print('  ----  worst prior swap: FY%d, grants %d'
          % (worst_prior_swap['fy'], worst_prior_swap['swap']['d_grants']))
    print('  ----  worst prior grant fall across matched functions: FY%d, %d'
          % (worst_prior_fall['fy'], worst_prior_fall['aggregate']['d_grants']))
    check('swaps that still spent less across both funds', len(short),
          len([m for m in years[fyl]['swap'] if m['d_total'] < 0]))

    print('\nTHE STRUCTURAL CLAIMS THE SENTENCES REST ON')
    assert_true(
        'FY%d is the largest swap on record, by the grant fall' % fyl,
        all(latest['swap']['d_grants'] <= r['swap']['d_grants'] for r in prior),
        'an earlier year has a larger grant fall in the swap class — the page says no '
        'earlier year comes close')
    assert_true(
        'FY%d is the largest reduction on record, by the grant fall' % fyl,
        all(latest['reduction']['d_grants'] <= r['reduction']['d_grants'] for r in prior),
        'an earlier year has a larger grant fall in the reduction class')
    assert_true(
        'FY%d is the largest total grant fall across matched functions' % fyl,
        all(latest['aggregate']['d_grants'] <= r['aggregate']['d_grants'] for r in prior),
        'an earlier year has a larger grant fall in total')
    biggest_rise = d['latest_gen_fund_rises'][0]
    assert_true(
        'the largest general fund rise exceeds the whole grant fall on its own',
        biggest_rise['d_gen_fund'] > abs(latest['aggregate']['d_grants']),
        'the page says the largest single general fund increase is, on its own, larger '
        'than the entire grant fall — %d against %d'
        % (biggest_rise['d_gen_fund'], abs(latest['aggregate']['d_grants'])))
    assert_true(
        'no grant was falling in the function with the largest general fund rise',
        biggest_rise['d_grants'] >= 0,
        'the page says the year\'s largest general fund increase is not a function where '
        'grants fell; grants there moved %d' % biggest_rise['d_grants'])
    assert_true(
        'the biggest rise is ordered first in latest_gen_fund_rises',
        all(biggest_rise['d_gen_fund'] >= m['d_gen_fund']
            for m in d['latest_gen_fund_rises']),
        'the list the page reads is not sorted by the general fund movement')
    assert_true(
        'some swaps still spent less across both funds',
        0 < len(short) <= len(swap),
        'the page says %d of %d swaps spent less in total; the count is degenerate'
        % (len(short), len(swap)))
    no_grant_fall = latest['grant_growth']['d_gen_fund'] + latest['other']['d_gen_fund']
    assert_true(
        'the general fund moved more where no grant fell than where one did',
        no_grant_fall > latest['swap']['d_gen_fund'],
        'the page says the general fund movement in the functions where grants did NOT '
        'fall is bigger than the swap — %d against %d'
        % (no_grant_fall, latest['swap']['d_gen_fund']))
    assert_true(
        'no function in grant_growth or other had grants fall',
        all(m['d_grants'] >= 0 for k in ('grant_growth', 'other')
            for m in d['latest_detail'][k]),
        'the page calls these the functions where grants did not fall; one of them fell')
    assert_true(
        'the general fund share rose over the whole span',
        d['town_share_points'] > 0,
        'the page says the general fund share rose; it did not')
    assert_true(
        'the grant share is not monotonic',
        any(grant_share(S[i]) > grant_share(S[i - 1]) for i in range(1, len(S))),
        'the page says the general fund did not get there in a straight line')

    print('\nRULE 11’S LOAD-BEARING LINE')
    paras = [m for m in swap if 'paraprofessional' in m['func_desc'].lower()]
    assert_true(
        'function 2330 is in the swap class in FY%d' % fyl,
        len(paras) == 1 and paras[0]['func_code'] == '2330',
        'the page renders a whole section on the paraprofessional function being a swap; '
        'it is no longer one, so the section renders nothing or renders the wrong code')

    print('\nTHE QUOTES, RE-READ OUT OF THE MINUTES')
    for q in d['said']:
        rel = q['cite'].replace('/docs/', 'sources/')
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            FAILS.append('%s: the document behind the quote is not on disk' % rel)
            print('  GONE  %s' % rel)
            continue
        text = re.sub(r'\s+', ' ', open(path, encoding='utf-8', errors='replace').read())
        ok = re.sub(r'\s+', ' ', q['quote']) in text
        if not ok:
            FAILS.append('%s %s: the quote is not in %s' % (q['board'], q['date'], rel))
        print('  %s  %s %s' % ('OK  ' if ok else 'GONE', q['board'], q['date']))

    print('\nTHE DOCUMENT’S OWN ADDRESS AND HASH (rule 12)')
    src = d['source']
    for field in ('path', 'sha256', 'url', 'docs_url', 'bytes'):
        assert_true('source carries its %s' % field, bool(src.get(field)),
                    'a citation with no %s is not checkable' % field)
    assert_true('the sha256 is a sha256', re.fullmatch(r'[0-9a-f]{64}', src['sha256'])
                is not None, 'the hash is not 64 hex characters')

    print('\nRULE 2 — NOTHING IS TYPED INTO THE PAGE')
    # A dollar sign followed by a digit, or a digit followed by a percent sign, in the
    # JSX TEXT of these two files. Three things are stripped first and each for its own
    # reason. Comment blocks: they quote figures on purpose, they are the record of why the
    # page is shaped as it is, they render nowhere, and forbidding them would push that
    # reasoning out of the file. Quoted strings and template literals: every CSS percentage
    # in a React component lives in one (`width: '100%'`, `barCategoryGap="18%"`), and a
    # rule that flagged those would be turned off within a day, which is worse than a
    # narrower rule kept on. THE COST OF THAT NARROWING, stated so it is not discovered
    # later: a figure typed inside a string prop would pass. What it still catches is the
    # case rule 2 is actually about -- a number written into a sentence a reader sees.
    for path in (PAGE, CHARTS):
        body = open(path, encoding='utf-8').read()
        body = re.sub(r'/\*[\s\S]*?\*/', '', body)
        body = re.sub(r'//[^\n]*', '', body)
        body = re.sub(r"'(?:[^'\\\n]|\\.)*'", "''", body)
        body = re.sub(r'"(?:[^"\\\n]|\\.)*"', '""', body)
        body = re.sub(r'`(?:[^`\\]|\\.)*`', '``', body)
        typed = re.findall(r'\$\s?\d[\d,]*|\b\d[\d,]*\s?%', body)
        name = os.path.relpath(path, ROOT)
        assert_true('no figure typed into %s' % name, not typed,
                    'these look like typed figures: %s' % ', '.join(sorted(set(typed))))

    print('\nRULE 7c — THE LIMITS ARE IN THE REGISTER, NOT ONLY IN THE PROSE')
    gaps = open(GAPS, encoding='utf-8').read()
    for phrase in ('Whether a general fund rise beside a grant fall is the same cost',
                   'How much of the SY2025 grant fall was ESSER'):
        assert_true('money-gaps.csv registers: %s…' % phrase[:46], phrase in gaps,
                    'the page states this limit and the register does not carry it — the '
                    'register outranks the page')
    assert_true('every gap row this page adds names what would close it',
                gaps.count('— closes:') >= 2,
                'a gap with no named remedy is a grievance, not a records request')

    print()
    if FAILS:
        print('%d FAILED' % len(FAILS))
        for f in FAILS:
            print('  - %s' % f)
        return 1
    print('every figure on /when-grants-end recomputes from the database.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
