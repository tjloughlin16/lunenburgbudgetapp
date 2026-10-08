#!/usr/bin/env python3
"""Recompute every figure in /analysis/special-education-costs by a DIFFERENT ROUTE.

    python3 scripts/verify_sped_costs.py

The generator reads the MUNIS year-end reports from `munis-school-ytd.csv` and the state's
files from the database. This reads the MUNIS reports from the DATABASE (`munis_school_ytd`)
and the state's files from their CSV extracts, sums with Decimal rather than float, and
classifies accounts by a written-out list of function codes rather than the generator's
regular expressions. Two routes landing on the same figure is the check; one route checked
against itself is not.

It asserts the NUMBER (rule: assert the number, not the prose around it): every figure a
conclusion registers is recomputed here and compared, and every rendering is looked for in
the published markdown on a word boundary.
"""
import csv
import json
import os
import re
import sqlite3
import sys
from decimal import Decimal as D, ROUND_HALF_EVEN
from statistics import median

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
PAY = os.path.join(ROOT, 'fy28', 'public', 'data', 'special-education-costs.json')
MD = os.path.join(ROOT, 'sources', 'analyses', 'special-education-costs.md')
LEA = '01620000'
ELL = ('0100-3-300-2310-51-0-06-1-511001', '0100-3-300-2110-51-0-04-2-545001')
TUITION_FUNCS = {'9100', '9300', '9400'}

bad = []


def check(name, got, want):
    if got != want:
        bad.append('%s: recomputed %r, payload says %r' % (name, got, want))


def r0(x):
    return int(D(x).quantize(D('1'), rounding=ROUND_HALF_EVEN))


def kind(account, desc):
    parts = account.split('-')
    fund, func, prog = parts[0], parts[3], parts[4]
    if fund != '0100':
        return None
    if desc.strip().upper() in ('SPECIAL ED TRANSPORTATION', 'SPECIAL EDUCATION TRANSPORTATION'):
        return 'trans'
    if prog != '51' or account in ELL:
        return None
    return 'ood' if func in TUITION_FUNCS else 'indist'


def ledger():
    sums = {}
    db = sqlite3.connect(os.path.join(DATA, 'lunenburg.db'))
    for fy, acct, desc, typ, o, s, e in db.execute(
            "SELECT fiscal_year, account, description, type, original_approp, ytd_expended, "
            "encumbrances FROM munis_school_ytd WHERE period=13"):
        if typ != 'E':
            continue
        k = kind(acct, desc)
        if k:
            a = sums.setdefault((int(fy), k), [D(0), D(0)])
            a[0] += D(str(o or 0))
            a[1] += D(str(s or 0)) + D(str(e or 0))
    munis_years = {fy for fy, _ in sums}
    with open(os.path.join(DATA, 'gl-history.csv'), encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['sheet'] != 'general_fund' or r['department_code'] != '300':
                continue
            fy = int(r['fiscal_year'])
            if fy in munis_years:
                continue
            k = kind(r['account'], r['org_desc'])
            if k:
                a = sums.setdefault((fy, k), [D(0), D(0)])
                a[0] += D(r['original'] or '0')
                a[1] += D(r['actual'] or '0')
    years = sorted({fy for fy, _ in sums})
    out = {}
    for fy in years:
        out[fy] = {k: (r0(sums[(fy, k)][0]), r0(sums[(fy, k)][1])) for k in ('ood', 'indist', 'trans')}
    return out, sorted(munis_years)


def fund2640():
    db = sqlite3.connect(os.path.join(DATA, 'lunenburg.db'))
    out = {}
    for fy, acct, typ, s, e in db.execute(
            "SELECT fiscal_year, account, type, ytd_expended, encumbrances FROM "
            "munis_school_ytd WHERE period=13 AND fund='2640'"):
        func = acct.split('-')[3]
        if typ == 'E' and func in TUITION_FUNCS:
            out[int(fy)] = out.get(int(fy), D(0)) + D(str(s or 0)) + D(str(e or 0))
    return {k: r0(v) for k, v in out.items()}


def dese_all_funds():
    t = {}
    with open(os.path.join(DATA, 'dese-function-expenditure.csv'), encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['lea'] == LEA and r['level'] == 'detail' and r['func_code'] in ('9300', '9400'):
                t[int(r['fy'])] = t.get(int(r['fy']), D(0)) + D(r['total'] or '0')
    return t


def placed():
    with open(os.path.join(DATA, 'placement-counts.csv'), encoding='utf-8') as fh:
        return {int(r['fy']): int(r['total']) for r in csv.DictReader(fh)}


def dese_counts():
    out = {}
    with open(os.path.join(DATA, 'dese-sped-program.csv'), encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['lea'] == LEA and r['indicator_category'] == 'In District/Out of District':
                out.setdefault(int(r['fy']), {})[r['indicator']] = int(float(r['measure_cnt']))
    return out


def nss():
    with open(os.path.join(DATA, 'dese-ch70-formula.csv'), encoding='utf-8') as fh:
        return {int(r['fy']): D(r['net_school_spending']) for r in csv.DictReader(fh)
                if r['lea'] == LEA and r['net_school_spending']}


def main():
    pay = json.load(open(PAY, encoding='utf-8'))
    md = re.sub(r'\s+', ' ', open(MD, encoding='utf-8').read())
    led, munis_years = ledger()
    years = sorted(led)
    var = {fy: {k: led[fy][k][1] - led[fy][k][0] for k in led[fy]} for fy in years}
    gross = {fy: sum(max(0, v) for v in var[fy].values()) for fy in years}
    worst_fy = max(years, key=lambda y: gross[y])

    C = {c['id']: c['figures'] for c in pay['conclusions']}
    f = lambda cid, k: C[cid][k]['value']

    check('years in the ledger', len(years), f('the-worst-year-in-seventeen', 'n'))
    check('worst year, overruns added', gross[worst_fy], f('the-worst-year-in-seventeen', 'worst'))
    check('worst year', worst_fy, f('the-worst-year-in-seventeen', 'fy'))
    check('years needing a reserve', sum(1 for y in years if gross[y] > 0),
          f('the-worst-year-in-seventeen', 'needing'))
    check('median year', r0(D(str(median(gross[y] for y in years)))),
          f('the-worst-year-in-seventeen', 'median'))

    ood = [var[y]['ood'] for y in years]
    check('tuition years over', sum(1 for v in ood if v > 0), f('tuition-misses-both-ways', 'over'))
    check('tuition worst overrun', max(ood), f('tuition-misses-both-ways', 'worst'))
    check('tuition worst year', years[ood.index(max(ood))], f('tuition-misses-both-ways', 'fy'))
    check('tuition largest underspend', -min(ood), f('tuition-misses-both-ways', 'best'))

    cb = fund2640()
    above = {y: led[y]['ood'][1] + cb.get(y, 0) - led[y]['ood'][0] for y in munis_years}
    wy = max(above, key=above.get)
    check('every fund, worst above voted', above[wy],
          f('counting-the-reimbursement-account', 'above'))
    check('every fund, worst year', wy, f('counting-the-reimbursement-account', 'fy'))
    check('circuit breaker account that year', cb[wy], f('counting-the-reimbursement-account', 'cb'))
    if not all(v > 0 for v in above.values()):
        bad.append('the claim that every fund ran above the voted line in all four years no '
                   'longer holds: %s' % above)

    pct = max(round(100.0 * var[y]['indist'] / led[y]['indist'][0], 1) for y in years)
    check('in-district largest overrun share', pct, f('in-district-lands-close', 'band'))

    af, pl = dese_all_funds(), placed()
    per = {y: r0(af[y] / pl[y]) for y in sorted(pl) if y in af}
    last4 = sorted(per)[-4:]
    pm = r0(D(str(median(per[y] for y in last4))))
    check('per child placed, recent median (our estimate)', pm,
          f('a-placement-is-a-six-figure-step', 'pp'))
    dc = dese_counts()
    mid = {y: pl[y] - dc[y]['Out-of-District'] for y in dc if y in pl}
    my = max(mid, key=mid.get)
    check('largest October-to-March rise', mid[my], f('a-placement-is-a-six-figure-step', 'rise'))
    check('three placements at the estimate', mid[my] * pm,
          f('a-placement-is-a-six-figure-step', 'total'))

    n = nss()
    cy = max(y for y in n if y <= years[-1])
    check('reserve cap, 2% of net school spending', r0(n[cy] * D('0.02')),
          f('the-reserve-town-meeting-created', 'cap'))

    # Every registered rendering is in the published document, on a word boundary.
    for c in pay['conclusions']:
        for k, fig in c['figures'].items():
            # A word boundary on digits: `65` must not match inside `$65,000` or `1,650`,
            # and a following comma is fine only when no digit comes after it.
            pat = r'(?<![\d,.$])' + re.escape(fig['text']) + r'(?!\d|[,.]\d)'
            if not re.search(pat, md):
                bad.append('%s/%s: %r is not in the markdown' % (c['id'], k, fig['text']))
    # The averages a reader asked for, recomputed.
    avg = lambda k: r0(sum(D(led[y][k][1]) for y in years) / len(years))
    for k, key in (('indist', 'indist'), ('ood', 'ood_gf')):
        check('average %s' % k, avg(k), pay['averages'][key])
    check('combined average', r0(sum(D(led[y]['ood'][1] + led[y]['indist'][1]) for y in years)
                                 / len(years)), pay['averages']['combined_gf'])
    for v in (pay['averages']['indist'], pay['averages']['ood_gf'], pay['averages']['combined_gf']):
        if '${:,}'.format(v) not in md:
            bad.append('average %s is not in the markdown' % v)

    if bad:
        print('verify_sped_costs: %d problem(s)' % len(bad))
        for b in bad:
            print('  ' + b)
        return 1
    print('verify_sped_costs: every conclusion figure and every average recomputed by a second '
          'route and found in the document (%d conclusions, %s to %s)'
          % (len(pay['conclusions']), 'FY%d' % years[0], 'FY%d' % years[-1]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
