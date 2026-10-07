#!/usr/bin/env python3
"""Verify every figure in `sources/analyses/fy25-school-surplus.md` and
`fy28/public/data/fy25-school-surplus.json`, recomputed by a DIFFERENT route than the
generator: `decimal.Decimal` arithmetic straight off the CSV, rather than the generator's
own `float` accumulation and helper functions. Rule 9 and `notes/process/WRITING-AN-ANALYSIS.md` §5:
assert the number, never the prose around it.

    python3 scripts/verify_fy25_school_surplus.py
"""
import csv
import json
import os
import re
import sys
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, 'sources', 'data', 'munis-school-ytd.csv')
REVDIST = os.path.join(ROOT, 'sources', 'data', 'revenue-distribution-fy26.csv')
MINUTES_TXT = os.path.join(ROOT, 'sources', 'meetings', 'text', 'school-committee',
                           '2025-09-17-minutes-7408.txt')
MD = os.path.join(ROOT, 'sources', 'analyses', 'fy25-school-surplus.md')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'fy25-school-surplus.json')
DISTRICT_FIGURE = Decimal('603885.97')

FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)


def D(s):
    return Decimal(s)


def main():
    md = open(MD, encoding='utf-8').read()
    pay = json.load(open(PAYLOAD, encoding='utf-8'))

    rows = []
    with open(LEDGER, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['fiscal_year'] == '2025' and r['period'] == '13' \
                    and r['report'] == 'gf-school' and r['type'] == 'E':
                rows.append(r)
    check(len(rows) == 415, 'expected 415 FY2025 period-13 gf-school expense rows, got %d'
          % len(rows))

    orig = sum(D(r['original_approp']) for r in rows)
    transfers = sum(D(r['transfers_adjustments']) for r in rows)
    revised = sum(D(r['revised_budget']) for r in rows)
    expended = sum(D(r['ytd_expended']) for r in rows)
    encumbered = sum(D(r['encumbrances']) for r in rows)
    available = sum(D(r['available_budget']) for r in rows)

    check(orig == D('25304074.00'), 'original appropriation recomputed as %s, expected '
          '25304074.00' % orig)
    check(transfers == D('-122502.44'), 'transfers recomputed as %s, expected -122502.44'
          % transfers)
    check(revised == D('25181571.56'), 'revised budget recomputed as %s, expected '
          '25181571.56' % revised)
    check(expended == D('24554454.70'), 'expended recomputed as %s, expected 24554454.70'
          % expended)
    check(encumbered == D('0.00'), 'encumbered recomputed as %s, expected 0.00' % encumbered)
    check(available == D('627116.86'), 'available recomputed as %s, expected 627116.86'
          % available)
    check(orig + transfers == revised, 'revised budget does not equal original + transfers: '
          '%s != %s' % (orig + transfers, revised))
    check(revised - expended - encumbered == available, 'available does not equal revised - '
          'expended - encumbered: %s != %s' % (revised - expended - encumbered, available))

    diff = available - DISTRICT_FIGURE
    check(diff == D('23230.89'), 'diff vs district recomputed as %s, expected 23230.89' % diff)
    moved_out = -transfers
    check(moved_out == D('122502.44'), 'moved out recomputed as %s, expected 122502.44'
          % moved_out)
    not_spent = available + moved_out
    check(not_spent == D('749619.30'), 'not spent against original recomputed as %s, '
          'expected 749619.30' % not_spent)

    # ---- the scope check, against the revenue-distribution workbook -------------------
    want = None
    with open(REVDIST, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['line'] == 'ALL NEW FY26 REVENUES distributed by FY25 share / School Dept %':
                want = D(r['fy25'])
    check(want is not None, 'revenue-distribution-fy26.csv has no School Dept FY25 row')
    check(want == orig, 'scope check failed: revenue-distribution-fy26.csv says %s, the '
          'ledger says %s' % (want, orig))

    # ---- the district's quote, verbatim in the minutes --------------------------------
    check(os.path.exists(MINUTES_TXT), 'missing %s' % os.path.relpath(MINUTES_TXT, ROOT))
    minutes = open(MINUTES_TXT, encoding='utf-8').read()
    check('$603,885.97' in minutes, 'the minutes no longer quote $603,885.97')
    check('the surplus number has gone up to $603,885.97' in ' '.join(minutes.split()),
          'the exact sentence around the district’s figure has changed')

    # ---- by-function, salary vs non-salary, by a independent grouping -----------------
    fam = {}
    for r in rows:
        func = r['account'].split('-')[3]
        family = (int(func) // 1000) * 1000
        sal, non = fam.setdefault(family, [D('0'), D('0')])
        v = D(r['available_budget'])
        if r['obj'].startswith('51'):
            fam[family][0] += v
        else:
            fam[family][1] += v

    EXPECT_FAMILY = {
        2000: (D('136171.16'), D('112326.42')),
        4000: (D('113828.89'), D('113745.59')),
        7000: (D('0'), D('64747.51')),
        3000: (D('5192.12'), D('24915.45')),
        9000: (D('0'), D('29945.74')),
        1000: (D('8850.07'), D('11764.71')),
        5000: (D('0'), D('5629.20')),
    }
    for family, (esal, enon) in EXPECT_FAMILY.items():
        sal, non = fam.get(family, (D('0'), D('0')))
        check(sal == esal, 'family %d salary recomputed as %s, expected %s'
              % (family, sal, esal))
        check(non == enon, 'family %d non-salary recomputed as %s, expected %s'
              % (family, non, enon))

    total_fam = sum((sal + non) for sal, non in fam.values())
    check(total_fam == available, 'the function families do not sum to the available total: '
          '%s != %s' % (total_fam, available))

    concentration = (fam[2000][0] + fam[2000][1]) + (fam[4000][0] + fam[4000][1])
    check(concentration == D('476072.06'), 'instruction + operations concentration '
          'recomputed as %s' % concentration)

    # ---- the paraprofessional accounts, function 2330, by org -------------------------
    para = {}
    for r in rows:
        if r['account'].split('-')[3] != '2330':
            continue
        para[r['org']] = dict(
            original=D(r['original_approp']), transfers=D(r['transfers_adjustments']),
            revised=D(r['revised_budget']), expended=D(r['ytd_expended']),
            available=D(r['available_budget']))

    EXPECT_PARA = {
        'S2512131': dict(available=D('48824.80')),            # Primary SPED
        'S2516131': dict(available=D('21767.92')),            # HS SPED
        'S2515131': dict(available=D('5873.68'), transfers=D('53674.00')),  # MS SPED
        'S2514131': dict(available=D('3154.40'), transfers=D('-65000.00')),  # ES SPED
        'S2066131': dict(available=D('30174.26'), expended=D('4785.74'),
                          revised=D('34960.00')),              # HS non-SPED
    }
    for org, want in EXPECT_PARA.items():
        got = para.get(org)
        check(got is not None, 'no function-2330 account %s in the recomputation' % org)
        if got:
            for k, v in want.items():
                check(got[k] == v, 'para account %s %s recomputed as %s, expected %s'
                      % (org, k, got[k], v))

    # ---- cross-check the markdown and the payload against these same figures ----------
    def need(text, label):
        check(text in md, '%s not found verbatim in the markdown' % label)

    need('$627,117', 'the available total')
    need('$23,231', 'the diff vs the district')
    need('$122,502', 'the moved-out total')
    need('$749,619', 'the not-spent-against-original total')
    need('$603,885.97', 'the district’s exact figure')
    need('$136,171', 'instruction salary')
    need('$113,829', 'operations salary')
    need('$48,825', 'primary SPED para available')  # rounds from 48824.80

    pt = pay['totals']
    check(Decimal(str(pt['original'])) == orig, 'payload original does not match')
    check(Decimal(str(pt['transfers'])) == transfers, 'payload transfers does not match')
    check(Decimal(str(pt['revised'])) == revised, 'payload revised does not match')
    check(Decimal(str(pt['expended'])) == expended, 'payload expended does not match')
    check(Decimal(str(pt['encumbered'])) == encumbered, 'payload encumbered does not match')
    check(Decimal(str(pt['available'])) == available, 'payload available does not match')
    check(Decimal(str(pay['diff'])) == diff, 'payload diff does not match')
    check(Decimal(str(pay['moved_out'])) == moved_out, 'payload moved_out does not match')
    check(Decimal(str(pay['not_spent_against_original'])) == not_spent,
          'payload not_spent_against_original does not match')
    check(Decimal(str(pay['district_figure'])) == DISTRICT_FIGURE,
          'payload district_figure does not match the quoted $603,885.97')

    by_func = {r['family']: r for r in pay['by_function']}
    for family, (esal, enon) in EXPECT_FAMILY.items():
        r = by_func.get(family)
        check(r is not None, 'payload by_function is missing family %d' % family)
        if r:
            check(Decimal(str(r['salary'])) == esal, 'payload family %d salary mismatch'
                  % family)
            check(Decimal(str(r['non_salary'])) == enon, 'payload family %d non-salary '
                  'mismatch' % family)

    pa_by_org = {r['org']: r for r in pay['para_accounts']}
    for org, want in EXPECT_PARA.items():
        r = pa_by_org.get(org)
        check(r is not None, 'payload para_accounts is missing %s' % org)
        if r:
            for k, v in want.items():
                check(Decimal(str(r[k])) == v, 'payload para %s %s mismatch' % (org, k))

    # ---- the conclusions: every registered figure matches what we just recomputed ----
    want_figures = {
        'diff': diff, 'ledger': available, 'district': DISTRICT_FIGURE,
        'total': not_spent, 'orig': orig, 'turned_back': available, 'moved': moved_out,
        'ops': fam[4000][0] + fam[4000][1], 'sal': fam[4000][0], 'non': fam[4000][1],
    }
    for c in pay['conclusions']:
        for name, f in c['figures'].items():
            if name in want_figures:
                got = Decimal(str(f['value']))
                check(got == want_figures[name], 'conclusion %s figure %s = %s, '
                      'recomputed as %s' % (c['id'], name, got, want_figures[name]))
            if f['text'] not in (' '.join([c['claim'], c.get('so_what', ''), c['detail']])):
                check(False, 'conclusion %s: figure %s renders as %r but that string is '
                      'not in its own prose' % (c['id'], name, f['text']))

    if FAILS:
        sys.stderr.write('verify_fy25_school_surplus: %d failure(s)\n' % len(FAILS))
        for m in FAILS:
            sys.stderr.write('  - %s\n' % m)
        return 1
    print('verify_fy25_school_surplus: all figures recomputed and matched (415 accounts, '
          '%d function families, %d para accounts, %d conclusions)'
          % (len(fam), len(para), len(pay['conclusions'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
