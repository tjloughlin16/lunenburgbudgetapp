#!/usr/bin/env python3
"""Recompute every figure /monty-tech renders, and fail if one drifted.

    python3 scripts/verify_monty_tech.py

Rule 9: a finished document's figures get RECOMPUTED, not re-read. Rule 13's fourth
bullet: a check must assert the NUMBER, not the prose around it.

WRITTEN AFTER THE PROSE (step 5 of `notes/process/WRITING-AN-ANALYSIS.md`). A verifier
written first asserts what the author intended.

WHY THIS IS NOT `build_monty_tech.py --check`.

    database + printed documents  ->  monty-tech.json  ->  the analysis and the page

`--check` establishes that the middle link reproduces. It cannot establish that the middle
link is RIGHT, because it compares the generator with itself. Everything below recomputes
from the database by a second, independent formulation, and re-reads every figure taken
off a printed page out of that page's own extracted text -- so a mistake cannot be shared
between the two.

WHAT IS CHECKED

 1. THE DERIVED SERIES, recomputed with different SQL: the town's required local
    contribution minus the Lunenburg district's, year by year.
 2. THE STRUCTURAL CLAIMS. Rule 5 of WRITING-AN-ANALYSIS -- assert the structure a
    paragraph rests on, not only its figures. Five sentences here are structural:
      * the town's total contribution is bound by WEALTH in every published year, which
        is what makes "a child changing school does not change the town's obligation" true
      * the required contribution splits by FOUNDATION BUDGET share, exactly, in 19 of 20
      * every annual-report candidate sits ABOVE the derived state minimum
      * every annual-report row carries `check failed` or `no check`
      * `report_monty_tech` still has no column meaning
 3. THE PRINTED FIGURES, re-read. Every value the page takes off a budget book is found
    again in that book's extracted text, at the line the payload names.
 4. THE FOUR-PART IDENTITY, recomputed for each year the district prints it.
 5. THE THREE-WAY FY2026 TIE: the district's book, the Town's budget book, the ledger.
 6. THE ANALYSIS DOCUMENT. Every figure typed into `sources/analyses/monty-tech.md` is
    derived here and asserted to appear, on a word boundary.
 7. RULE 2 MECHANICALLY. The page and its charts are scanned for a typed dollar amount.
 8. RULE 7c. Every money_gaps row the page cites is in the registry with a `— closes:`.
 9. RULE 12. Every document travels with its hash and its address.
10. THE PERSONA REVIEW -- `notes/process/PERSONAS.md`, six readers, three of whose tests
    are about what a document OMITS.
"""
import csv
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'monty-tech.json')
PAGE = os.path.join(ROOT, 'fy28', 'src', 'pages', 'MontyTech.tsx')
CHARTS = os.path.join(ROOT, 'fy28', 'src', 'components', 'MontyTechCharts.tsx')
DOCUMENT = os.path.join(ROOT, 'sources', 'analyses', 'monty-tech.md')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')

LPS_LEA = '01620000'
MT_LEA = '08320000'
TOWN = 'Lunenburg'
LEDGER_FY = 2026

FAILS = []


def check(label, got, want, tol=0.0):
    if isinstance(want, (int, float)) and isinstance(got, (int, float)):
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


def flat_document():
    return ' '.join(open(DOCUMENT, encoding='utf-8').read().split())


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


def pct1(x):
    return '%.1f%%' % (x * 100)


def main():
    if not os.path.exists(PAYLOAD):
        print('MISSING %s — run scripts/build_monty_tech.py' % PAYLOAD)
        return 1
    d = json.load(open(PAYLOAD, encoding='utf-8'))
    db = sqlite3.connect('file:%s?mode=ro' % DB, uri=True)
    flat = flat_document()
    h = d['headline']

    # ------------------------------------------------- 1. the derived series, again
    print('\n§1  The required contribution, derived again with different SQL')
    town = {r['fy']: r for r in q(
        db, "SELECT fy, town_foundation_enrollment fe, town_foundation_budget fb, "
            "required_local_contribution rlc, combined_effort_yield cey, "
            "target_local_contribution tgt FROM dese_ch70_contribution "
            "WHERE municipality=?", TOWN)}
    lps = {r['fy']: r for r in q(
        db, "SELECT fy, foundation_enrollment fe, foundation_budget fb, "
            "required_local_contribution rlc FROM dese_ch70_aid_factor WHERE lea=?",
        LPS_LEA)}
    years = sorted(set(town) & set(lps))
    mine = {fy: dict(fe=town[fy]['fe'] - lps[fy]['fe'],
                     fb=town[fy]['fb'] - lps[fy]['fb'],
                     rlc=town[fy]['rlc'] - lps[fy]['rlc']) for fy in years}
    check('years published', len(d['required']), len(years))
    payload = {r['fy']: r for r in d['required']}
    worst = max(years, key=lambda fy: abs(payload[fy]['mt_rlc'] - mine[fy]['rlc']))
    check('largest disagreement across %d years, in dollars' % len(years),
          max(abs(payload[fy]['mt_rlc'] - mine[fy]['rlc']) for fy in years), 0.0, 0.01)
    check('FY%d required contribution' % LEDGER_FY,
          payload[LEDGER_FY]['mt_rlc'], mine[LEDGER_FY]['rlc'], 0.01)
    check('FY%d foundation enrollment' % LEDGER_FY,
          payload[LEDGER_FY]['mt_fe'], mine[LEDGER_FY]['fe'], 0.01)
    print('  (worst year FY%d)' % worst)

    # ------------------------------------------------- 2. the structural claims
    print('\n§2  The five sentences that are structure rather than arithmetic')
    assert_true('the town’s total is bound by WEALTH in every published year',
                all(abs(town[fy]['tgt'] - town[fy]['cey']) < 1.0 for fy in years),
                'the 82.5%-of-foundation cap now binds somewhere, so enrollment DOES '
                'enter the town-wide total and the page’s central sentence is wrong')
    # And the guard must be capable of failing: the cap has to be a real, different number.
    assert_true('...and the cap is a genuinely different number, so that is not vacuous',
                all(0.825 * town[fy]['fb'] > town[fy]['cey'] for fy in years),
                'the two are the same quantity and the check above proves nothing')
    exact = [fy for fy in years
             if abs(mine[fy]['rlc'] / town[fy]['rlc'] - mine[fy]['fb'] / town[fy]['fb'])
             < 1e-5]
    check('years where the share identity holds exactly', d['apportionment']['exact'],
          len(exact))
    assert_true('the split is by FOUNDATION BUDGET share, not by enrollment share',
                all(abs(mine[fy]['rlc'] / town[fy]['rlc']
                        - mine[fy]['fe'] / town[fy]['fe']) > 1e-3 for fy in exact),
                'the foundation-budget share and the enrollment share are the same '
                'number, so the page distinguishes two things that do not differ')

    cand = q(db, "SELECT fy, v1, status, column_meaning FROM report_appropriations "
                 "WHERE label='Monty Tech Assessment' "
                 "AND table_family='accountant-schedule' ORDER BY fy")
    usable = [c for c in cand if (c['column_meaning'] or '').startswith('v1=appropriated')]
    check('annual-report candidates with an established column meaning',
          d['candidates_meta']['n'], len(usable))
    assert_true('every annual-report row is `check failed` or `no check`',
                all(c['status'] in ('check failed', 'no check') for c in cand),
                'one of them now passes its own reconciliation — good news, and the page '
                'says otherwise')
    assert_true('every candidate sits ABOVE the derived state minimum for its year',
                all(float(c['v1']) > mine[c['fy']]['rlc'] for c in usable
                    if c['fy'] in mine),
                'the cross-check the long series rests on has stopped holding')
    rmt = q(db, "SELECT DISTINCT column_meaning, status FROM report_monty_tech")
    assert_true('`report_monty_tech` still has no column meaning and is still unusable',
                bool(rmt) and not any(r['column_meaning'] for r in rmt)
                and {r['status'] for r in rmt} == {'no check'},
                'the table the page says cannot be read has changed state')

    # ------------------------------------------------- 3. the printed figures, re-read
    print('\n§3  Every figure taken off a printed page, found again in that page')
    for key, fig in sorted(d['figures'].items()):
        path = os.path.join(ROOT, fig['text'])
        if not os.path.exists(path):
            FAILS.append('%s: %s is not here' % (key, fig['text']))
            print('  GONE  %s' % key)
            continue
        lines = open(path, encoding='utf-8', errors='replace').read().splitlines()
        blob = ' '.join(' '.join(lines[fig['line'] - 1:
                                       fig['line'] - 1 + fig['lines']]).split())
        bad = [n for n, v in fig['values'].items()
               if not any(f in blob for f in ([format(v, ',.2f'), format(v, '.2f')]
                                              if isinstance(v, float)
                                              else [format(v, ','), str(v)]))]
        assert_true('%s — %d value(s) on line %d of %s'
                    % (key, len(fig['values']), fig['line'],
                       os.path.basename(fig['text'])),
                    not bad, 'not on that line: %s' % bad)

    # ------------------------------------------------- 4. the four-part identity
    print('\n§4  The four parts sum to the total the district prints')
    for row in d['assessment']:
        if row['transport'] is None:
            continue
        parts = row['required'] + row['transport'] + (row['capital'] or 0)
        check('FY%d  minimum + transport + capital' % row['fy'], parts,
              float(row['total']), 0.01)

    # ------------------------------------------------- 5. the FY2026 three-way tie
    print('\n§5  FY%d: the district’s book, the Town’s book and the ledger' % LEDGER_FY)
    led = q(db, "SELECT original, expended, account, name FROM munis_ledger "
                "WHERE dept='310' AND fy=? AND period='12'", LEDGER_FY)
    check('ledger rows for department 310', len(led), 1)
    if led:
        check('ledger appropriation', d['ledger']['original'], float(led[0]['original']))
        check('ledger expended', d['ledger']['expended'], float(led[0]['expended']))
        check('the district’s own FY%d assessment' % LEDGER_FY,
              d['figures']['parts-fy26-fy27']['values']['fy26_total'],
              float(led[0]['original']), 0.01)
        check('the Town’s FY2027 budget book, FY%d column' % LEDGER_FY,
              d['figures']['town-book']['values']['fy26_budgeted'],
              float(led[0]['original']), 0.01)
        check('account number', d['ledger']['account'], led[0]['account'])

    # ------------------------------------------------- 6. the analysis document
    print('\n§6  Every figure in sources/analyses/monty-tech.md, derived here')
    a = {r['fy']: r for r in d['assessment']}
    dist = {r['fy']: r for r in d['district']}
    states(flat, 'the FY2026 assessment', usd(mine[LEDGER_FY]['rlc']
                                              + a[2026]['transport']
                                              + a[2026]['capital']))
    states(flat, 'the account number', led[0]['account'] if led else '')
    states(flat, 'the required minimum', usd(mine[LEDGER_FY]['rlc']))
    states(flat, 'the transport assessment', usd(a[2026]['transport']))
    states(flat, 'the capital assessment', usd(a[2026]['capital']))
    states(flat, 'what sits above the minimum',
           usd(a[2026]['total'] - a[2026]['required']))
    states(flat, 'the state-set share',
           pct1(mine[LEDGER_FY]['rlc'] / a[2026]['total']))
    states(flat, 'the negotiated share',
           pct1(1 - mine[LEDGER_FY]['rlc'] / a[2026]['total']))
    states(flat, 'the printed foundation share',
           '%.2f%%' % (100 * mine[LEDGER_FY]['fb'] / town[LEDGER_FY]['fb']))
    states(flat, 'the Lunenburg district’s share',
           '%.2f%%' % (100 * lps[LEDGER_FY]['fb'] / town[LEDGER_FY]['fb']))
    states(flat, 'the Lunenburg district foundation budget', usd(lps[LEDGER_FY]['fb']))
    states(flat, 'the Monty Tech foundation budget', usd(mine[LEDGER_FY]['fb']))
    states(flat, 'the Lunenburg district contribution', usd(lps[LEDGER_FY]['rlc']))
    states(flat, 'the town-wide contribution', usd(town[LEDGER_FY]['rlc']))
    states(flat, 'the Lunenburg district foundation enrollment',
           format(int(lps[LEDGER_FY]['fe']), ','))
    states(flat, 'growth in the required contribution since FY%d' % h['from_fy'],
           pct1(mine[LEDGER_FY]['rlc'] / mine[h['from_fy']]['rlc'] - 1))
    states(flat, 'the FY%d required contribution' % h['from_fy'],
           usd(mine[h['from_fy']]['rlc']))
    states(flat, 'town-wide growth over the same span',
           pct1(town[LEDGER_FY]['rlc'] / town[h['from_fy']]['rlc'] - 1))
    states(flat, 'Lunenburg district growth over the same span',
           pct1(lps[LEDGER_FY]['rlc'] / lps[h['from_fy']]['rlc'] - 1))
    states(flat, 'the FY%d share' % h['from_fy'],
           '%.2f%%' % (100 * mine[h['from_fy']]['rlc'] / town[h['from_fy']]['rlc']))
    states(flat, 'the Monty Tech foundation rate per pupil',
           usd(mine[LEDGER_FY]['fb'] / mine[LEDGER_FY]['fe']))
    states(flat, 'the Lunenburg foundation rate per pupil',
           usd(lps[LEDGER_FY]['fb'] / lps[LEDGER_FY]['fe']))
    states(flat, 'the ratio between them',
           '%.2f' % ((mine[LEDGER_FY]['fb'] / mine[LEDGER_FY]['fe'])
                     / (lps[LEDGER_FY]['fb'] / lps[LEDGER_FY]['fe'])))
    states(flat, 'the enrollment share of the town’s foundation',
           '%.2f%%' % (100 * mine[LEDGER_FY]['fe'] / town[LEDGER_FY]['fe']))

    states(flat, 'the statutory cap on the local share',
           '%s%%' % ('%g' % (d['wealth']['cap_pct'] * 100)))

    F = d['forecast']
    states(flat, 'the town’s FY2026 projection', '$%s' % format(F['projected'], ',.2f'))
    states(flat, 'the projection miss', usd(F['actual'] - F['projected']))
    states(flat, 'the projection miss, as a percentage',
           pct1(F['actual'] / F['projected'] - 1))
    states(flat, 'what the required contribution actually compounded at',
           pct1((mine[LEDGER_FY]['rlc'] / mine[F['base_fy']]['rlc'])
                ** (1 / (LEDGER_FY - F['base_fy'])) - 1))

    D = dist[LEDGER_FY]
    states(flat, 'the district’s FY2026 budget', usd(D['budget']))
    states(flat, 'Chapter 70’s share of it', pct1(D['ch70'] / D['budget']))
    states(flat, 'all eighteen assessments as a share of it',
           pct1(D['all_assessments'] / D['budget']))
    states(flat, 'Lunenburg’s share of the district budget',
           '%.2f%%' % (100 * D['lunenburg'] / D['budget']))
    states(flat, 'Lunenburg’s share of the district’s foundation enrollment',
           '%.2f%%' % (100 * D['lunenburg_fe'] / D['members_fe']))

    stu = {r['fy']: r for r in d['students']}
    latest = max(stu)
    states(flat, 'Monty Tech students', format(int(stu[latest]['monty_tech']), ','))
    states(flat, 'school choice students', format(int(stu[latest]['school_choice']), ','))
    states(flat, 'charter students', format(int(stu[latest]['charter']), ','))
    states(flat, 'the first-year count', format(int(stu[min(stu)]['monty_tech']), ','))
    states(flat, 'the district’s own per-pupil figure', usd(a[2026]['total']
                                                            / a[2026]['foundation_enrollment']))
    states(flat, 'the per-pupil figure on the October headcount',
           usd(a[2026]['total'] / stu[latest]['monty_tech']))

    M = d['assessment_meta']
    states(flat, 'the FY2027 district figure', usd(M['fy27_district']))
    states(flat, 'the FY2027 town figure', usd(M['fy27_town']))
    states(flat, 'the FY2027 disagreement', '$%d' % round(M['fy27_gap']))
    states(flat, 'the FY2025 appropriation', usd(M['fy25_budgeted']))
    states(flat, 'the FY2025 actual', usd(M['fy25_actual']))
    states(flat, 'the FY2025 underspend', '$%s' % format(round(-M['fy25_gap']), ','))
    states(flat, 'the FY2024 assessment', usd(M['fy24_district']))
    states(flat, 'the FY2024 expended', '$%s' % format(M['fy24_town'], ',.2f'))
    states(flat, 'the FY2023 assessment', usd(a[2023]['total']))

    # Rule 11's own figure, which is quoted from another page of this site and must not
    # be allowed to go stale here.
    pp = q(db, "SELECT per_pupil FROM dese_function_expenditure "
               "WHERE lea=? AND fy=2025 AND level='total' AND func_code='TTPP'", LPS_LEA)
    if pp:
        states(flat, 'DESE’s all-funds per-pupil figure, not to be subtracted',
               usd(pp[0]['per_pupil']))

    mn = d['minutes']
    states(flat, 'meeting documents searchable', format(mn['searchable'], ','))
    states(flat, 'meeting documents held', format(mn['held'], ','))
    states(flat, 'the searchable share', '%d%%' % round(100 * mn['searchable'] / mn['held']))

    for c in d['candidates']:
        if c['usable']:
            states(flat, 'FY%d annual-report candidate' % c['fy'], usd(c['value']))
            states(flat, 'FY%d derived minimum' % c['fy'], usd(c['required']))

    # ------------------------------------------------- 7. rule 2 on the page source
    print('\n§7  Rule 2 — no figure typed into the page or its charts')
    for src in (PAGE, CHARTS):
        if not os.path.exists(src):
            FAILS.append('%s is not here' % os.path.relpath(src, ROOT))
            print('  GONE  %s' % os.path.relpath(src, ROOT))
            continue
        body = re.sub(r'/\*[\s\S]*?\*/', '', open(src, encoding='utf-8').read())
        body = re.sub(r'^\s*//.*$', '', body, flags=re.M)
        typed = set(re.findall(r'\$[\d][\d,]{2,}(?:\.\d+)?', body))
        typed |= set(re.findall(r'(?<![\w.])\d{1,3}\.\d%', body))
        assert_true('%s carries no typed money or percentage'
                    % os.path.basename(src), not typed,
                    'typed into the source: %s' % sorted(typed))

    # ------------------------------------------------- 8. rule 7c
    print('\n§8  Rule 7c — every gap this page cites is in the registry, with a remedy')
    reg = {r['what']: r for r in csv.DictReader(open(GAPS, encoding='utf-8'))}
    for gap in d['gaps']:
        present = gap['what'] in reg
        assert_true('registered: %s' % gap['what'][:58], present,
                    'the page cites a gap the registry does not carry')
        if present:
            assert_true('  ...and names the document that would close it',
                        bool(gap['closes']),
                        'a gap with no named remedy is a grievance')

    # ------------------------------------------------- 9. rule 12
    print('\n§9  Rule 12 — every document travels with its hash and its address')
    man = {row['key']: row for row in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    cited = [(doc['path'][len('sources/'):], doc['sha256'], doc['filename'])
             for doc in d['documents']]
    cited += [(fig['path'][len('sources/'):], fig['sha256'], fig['filename'])
              for fig in d['figures'].values()]
    for key, sha, name in cited:
        present = key in man
        assert_true('in the manifest: %s' % name, present,
                    'the page cites a document the manifest does not describe')
        if present:
            check('  sha256 %s' % name, sha, man[key]['sha256'])

    # ------------------------------------------------ 10. the persona review
    print('\n§10  The persona review must have been run — notes/process/PERSONAS.md')
    page_src = open(PAGE, encoding='utf-8').read() if os.path.exists(PAGE) else ''
    body = ' '.join(re.sub(r'/\*[\s\S]*?\*/', '', page_src).split())
    said = json.dumps(d['said'], ensure_ascii=False)
    NEEDED = [
        ('1 — the worst fact is above the fold, not buried',
         'Lunenburg vote sets it', body),
        ('2 — the repeatable sentence is the true one',
         'is not a departure', body),
        ('3 — nobody on a board is ambushed; the mechanism is named, not a person',
         'computed by the state', body),
        ('4 — the Finance Committee control question is answered',
         'What would you have had to see, and when', body),
        ('5 — the School Committee is told what it can and cannot reach',
         'aligned with the Lunenberg Public Schools', said),
        ('6 — the town-versus-school frame is refused rather than fed',
         'does not raise the town', body),
        ('the district is given credit where it does the right thing',
         'also publishes the split, in full', body),
        ('the concrete thing somebody raised is addressed',
         'disentangle ourselves from Monty Tech', said),
    ]
    for label, needle, hay in NEEDED:
        ok = ' '.join(needle.split()) in ' '.join(hay.split())
        print('  %s  %s' % ('OK  ' if ok else 'GONE', label))
        if not ok:
            FAILS.append('persona review: "%s" — the text that satisfied it is gone'
                         % label)
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
    print('every figure /monty-tech and sources/analyses/monty-tech.md carry recomputes '
          'from the database and from the documents they name.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
