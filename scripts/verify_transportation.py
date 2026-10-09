#!/usr/bin/env python3
"""Recompute every headline figure in /analysis/transportation by a DIFFERENT ROUTE.

    python3 scripts/verify_transportation.py

The generator reads the ledgers from their CSV extracts, classifies accounts by function and
object code, sums in float, and reads the bid form's rates as a declared table that it tests
against the scan. This takes each figure another way:

  * the MUNIS years from the DATABASE (`munis_school_ytd`), selected by SQL on the account
    string, summed with Decimal;
  * the Finance Committee years from `gl-history.csv` selected by ORG AND OBJECT rather than
    by function code;
  * the contract's regular-route prices from the SUBTOTALS the bid form prints, read out of
    the scan's text layer with a regular expression, rather than from rate x buses x days;
  * the athletics totals from the database table, not the CSV;
  * the budget book from `lps_budget_lines` by row number;
  * every quotation re-read from the document its citation points at.

It asserts the NUMBER, never the prose around it: every figure a conclusion registers is
recomputed and compared to the value the payload carries, and every claim and supporting
line is looked for in the published markdown.
"""
import csv
import json
import os
import re
import sqlite3
import sys
from decimal import Decimal as D, ROUND_HALF_EVEN

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
PAY = os.path.join(ROOT, 'fy28', 'public', 'data', 'transportation.json')
MD = os.path.join(ROOT, 'sources', 'analyses', 'transportation.md')
BID = os.path.join(ROOT, 'sources', 'contracts', 'txt', 'dee-bus-bid-proposal-rates-fy26-fy30.txt')
OVERVIEW = os.path.join(ROOT, 'sources', 'district-budget', 'text',
                        'school-department-fy26-budget-overview.txt')
LEA = '01620000'

# By ORG and OBJECT -- the generator keys on function and object. Two keys to one account.
ORG_OBJ = {
    'regular': [('S3991692', '535025')],
    'sped': [('S3991692', '535026')],
    'athletic': [('S3066672', '535016')],
    'band': [('S0055632', '535016'), ('S0066632', '535016')],
}
BOOK_ROWS = {'regular': [167], 'sped': [168], 'athletic': [170], 'band': [143, 144]}

bad = []


def check(name, got, want):
    if got != want:
        bad.append('%s: recomputed %r, payload says %r' % (name, got, want))


def r0(x):
    return int(D(str(x)).quantize(D('1'), rounding=ROUND_HALF_EVEN))


def r2(x):
    return D(str(x)).quantize(D('0.01'), rounding=ROUND_HALF_EVEN)


def p1(a, b):
    return float((D(a) * 100 / D(b)).quantize(D('0.1'), rounding=ROUND_HALF_EVEN))


def money(s):
    return D(re.sub(r'[^\d.]', '', s))


def main():
    pay = json.load(open(PAY, encoding='utf-8'))
    md = open(MD, encoding='utf-8').read()
    flat = re.sub(r'\s+', ' ', md)
    db = sqlite3.connect(os.path.join(DATA, 'lunenburg.db'))
    cards = {c['id']: c for c in pay['conclusions']}
    fig = lambda cid, k: cards[cid]['figures'][k]['value']

    # ---- the ledger, two routes ------------------------------------------------------
    led = {}
    for cat, pairs in ORG_OBJ.items():
        for org, obj in pairs:
            for fy, o, ex, en, rv in db.execute(
                    'SELECT fiscal_year, original_approp, ytd_expended, encumbrances, '
                    'revised_budget FROM munis_school_ytd WHERE period=13 AND fund=? AND '
                    'org=? AND obj=? AND type=?', ('0100', org, obj, 'E')):
                a = led.setdefault((int(fy), cat), [D(0), D(0), D(0)])
                a[0] += D(str(o))
                a[1] += D(str(ex)) + D(str(en))
                a[2] += D(str(rv))
    for r in csv.DictReader(open(os.path.join(DATA, 'gl-history.csv'), encoding='utf-8')):
        if r['sheet'] != 'general_fund' or r['actual_is_partial'] == 'true':
            continue
        fy = int(r['fiscal_year'])
        if fy >= 2023:
            continue
        for cat, pairs in ORG_OBJ.items():
            if (r['org'], r['object']) in pairs:
                a = led.setdefault((fy, cat), [D(0), D(0), D(0)])
                a[0] += D(r['original'])
                a[1] += D(r['actual'])
                a[2] += D(r['revised'])
    spent = lambda fy, c: r0(led[(fy, c)][1])
    budget = lambda fy, c: r0(led[(fy, c)][0])
    cats = list(ORG_OBJ)

    # every year of the payload's table
    for row in pay['by_year']:
        if row['fy'] > 2026:
            continue
        for c in cats:
            check('FY%d %s budget' % (row['fy'], c), budget(row['fy'], c), row[c + '_budget'])
            check('FY%d %s spent' % (row['fy'], c), spent(row['fy'], c), row[c + '_spent'])

    all26 = sum(spent(2026, c) for c in cats)
    allb26 = sum(budget(2026, c) for c in cats)
    c1 = 'school-day-is-the-bill'
    check(c1 + ' share', p1(spent(2026, 'athletic'), all26), fig(c1, 'share'))
    check(c1 + ' budget share', p1(budget(2026, 'athletic'), allb26), fig(c1, 'bshare'))
    check(c1 + ' all', all26, fig(c1, 'all'))
    for k, c in (('reg', 'regular'), ('sped', 'sped'), ('ath', 'athletic'), ('band', 'band')):
        check(c1 + ' ' + k, spent(2026, c), fig(c1, k))
    shares = {fy: p1(spent(fy, 'athletic'), sum(spent(fy, c) for c in cats))
              for fy in range(2010, 2027)}
    check(c1 + ' highest share', max(shares.values()), fig(c1, 'hi'))
    check(c1 + ' lowest share', min(shares.values()), fig(c1, 'lo'))

    # ---- athletics: the sheet, from the database ---------------------------------------
    sheet = {fy: r2(t) for fy, t in db.execute(
        "SELECT fy, SUM(value) FROM athletics_by_sport WHERE metric='Transportation' "
        "AND is_numeric=1 GROUP BY fy")}
    c2 = 'athletic-cost-was-already-there'
    check(c2 + ' sheet FY2024', float(sheet[2024]), fig(c2, 'sheet24'))
    check(c2 + ' sheet FY2025', float(sheet[2025]), fig(c2, 'sheet25'))
    check(c2 + ' line FY2024', budget(2024, 'athletic'), fig(c2, 'line'))
    check(c2 + ' spent FY2024', spent(2024, 'athletic'), fig(c2, 'spent24'))
    check(c2 + ' spent FY2025', spent(2025, 'athletic'), fig(c2, 'spent25'))
    check(c2 + ' FY2026 line', budget(2026, 'athletic'), fig(c2, 'new'))

    # ---- the contract, from the subtotals the form prints ---------------------------
    lines = open(BID, encoding='utf-8').read().split('\n')
    at = lambda n: lines[n - 1]
    printed = {
        2026: (money(re.search(r'\$(\d+)\.0000', at(26)).group(1)),
               money(re.search(r'([\d,]+) 00', at(29)).group(1))),
        2028: (money(re.search(r'\$([\d,]+)', at(193)).group(1)),
               money(re.search(r'\$([\d,]+)', at(195)).group(1))),
        2029: (money(re.search(r'\$ ([\d,]+)\.', at(306)).group(1)),
               money(re.search(r's ([\d,]+)\.', at(310)).group(1))),
        2030: (money(re.search(r'\$([\d,]+)\.00', at(392)).group(1)),
               money(re.search(r'\$([\d,]+)\.00', at(395)).group(1))),
    }
    reg = {fy: a + b for fy, (a, b) in printed.items()}
    # FY2027's 83-passenger subtotal is illegible in the text layer (`530240`); its
    # 77-passenger subtotal and the 83-passenger rate are legible, so it is rebuilt from them.
    reg[2027] = money(re.search(r'\$ ([\d,]+)\.00', at(113)).group(1)) + \
        3 * money(re.search(r'(\d+)\*', at(110)).group(1)) * 180
    c4 = 'contract-fixes-the-price'
    check(c4 + ' FY2028 price', r0(reg[2028]), fig(c4, 'p28'))
    check(c4 + ' FY2029 price', r0(reg[2029]), fig(c4, 'o29'))
    check(c4 + ' FY2030 price', r0(reg[2030]), fig(c4, 'o30'))
    check(c4 + ' FY2028 rise', p1(reg[2028] - reg[2027], reg[2027]), fig(c4, 'rise'))
    b27 = [r0(v) for v, in db.execute('SELECT fy27_balanced FROM lps_budget_lines WHERE row=167')]
    check(c4 + ' FY2027 budget', b27[0], fig(c4, 'b27'))
    if b27[0] != r0(reg[2027]):
        bad.append('the FY2027 budget no longer equals the contract’s second-year price')
    gt = money(re.search(r'([\d,]+\.\d\d)', at(268)).group(1))
    if gt != D('6086125.00'):
        bad.append('the Grand Total no longer reads 6,086,125.00 in the text layer')

    c5 = 'the-seven-point-six'
    b25 = [r0(v) for v, in db.execute('SELECT fy25_budget FROM lps_budget_lines WHERE row=167')][0]
    check(c5 + ' FY2025 budget', b25, fig(c5, 'b25'))
    check(c5 + ' FY2026 price', r0(reg[2026]), fig(c5, 'p26'))
    check(c5 + ' step', r0(reg[2026] - b25), fig(c5, 'step'))
    ov = re.search(r'7\.6% line increase = \$([\d,]+)', open(OVERVIEW, encoding='utf-8').read())
    if not ov or money(ov.group(1)) != reg[2026] - b25:
        bad.append('the overview’s 7.6% dollar figure no longer equals the contract price less '
                   'the FY2025 budget')
    check(c5 + ' 11 buses', float(r2(D(b25) / 180 / 11)), fig(c5, 'fa'))
    check(c5 + ' 10 buses', float(r2(D(b25) / 180 / 10)), fig(c5, 'fb'))
    check(c5 + ' FY2026 average', float(r2(reg[2026] / 180 / 11)), fig(c5, 'f26'))

    # ---- trips, OUR estimate, from the form's own words and rates --------------------
    est = re.search(r'(\d+) fild trips.*?([\d,]+) miles', at(32))
    trips_n, miles = int(est.group(1)), int(est.group(2).replace(',', ''))
    hours = 4 if 'four (4) hours' in at(33) else None
    mrate = money(re.search(r'\$ ([\d.]+)', at(35)).group(1))
    wrate = money(re.search(r's (\d+)', at(73)).group(1))
    full = D(miles) / trips_n * mrate + hours * wrate
    nowait = D(miles) / trips_n * mrate
    c3 = 'trips-per-sport'
    check(c3 + ' trip price', float(r2(full)), fig(c3, 'full'))
    check(c3 + ' no-wait price', float(r2(nowait)), fig(c3, 'nowait'))
    check(c3 + ' trips', float((sheet[2025] / full).quantize(D('0.1'))), fig(c3, 'trips'))
    check(c3 + ' trips no wait', float((sheet[2025] / nowait).quantize(D('0.1'))), fig(c3, 'tnw'))
    top = db.execute("SELECT season, level, sport, value FROM athletics_by_sport WHERE "
                     "metric='Transportation' AND fy=2025 AND is_numeric=1 "
                     "ORDER BY CAST(value AS REAL) DESC LIMIT 1").fetchone()
    check(c3 + ' top sport dollars', float(r2(top[3])), fig(c3, 'top'))

    # ---- special education ------------------------------------------------------------
    c6 = 'sped-transport-is-the-variable'
    check(c6 + ' FY2019', spent(2019, 'sped'), fig(c6, 'low'))
    check(c6 + ' FY2026', spent(2026, 'sped'), fig(c6, 'now'))
    for fy in (2024, 2026):
        check(c6 + ' over FY%d' % fy, spent(fy, 'sped') - budget(fy, 'sped'), fig(c6, 'o%d' % fy))
    cbt = {int(fy): r0(v) for fy, v in db.execute(
        "SELECT fy, reimb_transport FROM dese_circuit_breaker WHERE lea=? AND level='district' "
        "AND reimb_transport IS NOT NULL AND reimb_transport != ''", (LEA,))}
    check(c6 + ' circuit breaker FY2025', cbt[2025], fig(c6, 'cb1'))
    check(c6 + ' circuit breaker FY2026', cbt[2026], fig(c6, 'cb2'))

    # ---- the fee ------------------------------------------------------------------------
    c7 = 'fee-netted-from-the-line'
    o26, t26 = db.execute("SELECT original_approp, transfers_adjustments FROM munis_school_ytd "
                          "WHERE period=13 AND fiscal_year=2026 AND fund='0100' AND "
                          "obj='535025'").fetchone()
    check(c7 + ' voted', r0(o26), fig(c7, 'voted'))
    check(c7 + ' netted', r0(reg[2026] - D(str(o26))), fig(c7, 'net'))
    if r0(t26) != r0(reg[2026] - D(str(o26))):
        bad.append('the FY2026 transfer no longer equals the amount the line was netted by')
    fee = {int(fy): -D(str(v)) for fy, v in db.execute(
        "SELECT fiscal_year, ytd_expended FROM munis_school_ytd WHERE period=13 AND "
        "fund='1308' AND obj='437601'")}
    check(c7 + ' FY2025 receipts', float(r2(fee[2025])), fig(c7, 'f25'))
    check(c7 + ' FY2026 receipts', float(r2(fee[2026])), fig(c7, 'f26'))
    if fee[2023] or fee[2024]:
        bad.append('the bus fee account took in money before FY2025, which the page denies')

    # ---- FY2027 -------------------------------------------------------------------------
    c8 = 'fy27-athletic-buses'
    z, ls = db.execute('SELECT fy27_balanced, fy27_level_service FROM lps_budget_lines '
                       'WHERE row=170').fetchone()
    check(c8 + ' balanced', r0(z), fig(c8, 'zero'))
    check(c8 + ' level service', r0(ls), fig(c8, 'ls'))
    said = {q['key']: q for q in pay['said']}
    nums = [money(x) for x in re.findall(r'\$[\d,]+', said['restore']['quote'])]
    check(c8 + ' restore', r0(nums[0]), fig(c8, 'restore'))
    check(c8 + ' town', r0(nums[2]), fig(c8, 'town'))
    check(c8 + ' fund', r0(nums[3]), fig(c8, 'fund'))

    # ---- DESE: a third route to the school-day total, where it ties ------------------
    dese = {}
    for fy, code, gf in db.execute(
            "SELECT fy, func_code, gen_fund FROM dese_function_expenditure WHERE lea=? AND "
            "((func_code='3300' AND level='detail') OR func_code='ODTR')", (LEA,)):
        dese[int(fy)] = dese.get(int(fy), 0) + r0(gf)
    for fy in (2022, 2023, 2024):
        want = spent(fy, 'regular') + spent(fy, 'sped')
        if dese.get(fy) != want:
            bad.append('FY%d: DESE %s against the ledger %s' % (fy, dese.get(fy), want))

    # ---- quotations, verbatim, at the address cited ---------------------------------
    for q in pay['said']:
        path = os.path.join(ROOT, 'sources', q['cite'][len('/docs/'):].replace(
            'minutes/text/', 'meetings/text/', 1))
        text = re.sub(r'\s+', ' ', open(path, encoding='utf-8').read())
        if re.sub(r'\s+', ' ', q['quote']) not in text:
            bad.append('quote %r is not verbatim in %s' % (q['key'], q['cite']))
        if q['quote'] not in md and re.sub(r'\s+', ' ', q['quote']) not in flat:
            bad.append('quote %r is not in the published markdown' % q['key'])

    # ---- the prose: every card in the markdown; rule 2 against the payload ----------
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import conclusions
    for p in conclusions.check('transportation', pay['conclusions']):
        bad.append(p)
    for c in pay['conclusions']:
        for k in ('claim', 'so_what'):
            if c[k] not in flat:
                bad.append('%s %s is not in the markdown' % (c['id'], k))
        if c['kind'] == 'hypothesis' and 'our estimate' not in (c['claim'] + c['basis']).lower():
            bad.append('%s is an estimate and does not say so' % c['id'])
    for s in pay['stats']:
        if not re.search(r'\d', s['value']):
            bad.append('stat %r has no figure' % s['label'])

    if bad:
        print('verify_transportation: %d problem(s)' % len(bad))
        for b in bad:
            print('  ' + b)
        return 1
    print('verify_transportation: every headline figure recomputed by a second route; %d '
          'conclusions, %d quotations checked' % (len(pay['conclusions']), len(pay['said'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
