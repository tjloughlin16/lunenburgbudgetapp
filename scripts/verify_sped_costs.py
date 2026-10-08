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
    # TWO BASES. After: the gross need already computed. Before: the account's tuition put
    # back on the tuition line, overruns added the same way.
    before = {y: max(0, led[y]['ood'][1] + cb.get(y, 0) - led[y]['ood'][0])
              + max(0, var[y]['indist']) + max(0, var[y]['trans']) for y in munis_years}
    rq = pay['request']
    T3, T5 = 300000, 500000
    if rq['thresholds'] != [T3, T5]:
        bad.append('thresholds changed: %s' % rq['thresholds'])
    for b in rq['bases']:
        check('before basis FY%d' % b['fy'], before[b['fy']], b['before'])
        check('after basis FY%d' % b['fy'], gross[b['fy']], b['after'])
        check('account tuition FY%d' % b['fy'], cb[b['fy']], b['cb_tuition'])
    if any(cb.get(y, 0) <= 0 for y in munis_years):
        bad.append('the account did not pay tuition in every closed year; a card says it does')
    q = 'the-300000-question'
    check('years in 17 over 300k, after', sum(1 for y in years if gross[y] > T3), 0)
    check('years over 300k, before', sum(1 for y in munis_years if before[y] > T3), f(q, 'over'))
    check('years within 500k, before', sum(1 for y in munis_years if before[y] <= T5), f(q, 'within'))
    wb = max(munis_years, key=lambda y: before[y])
    check('worst before-basis year', wb, f(q, 'wfy'))
    check('worst before-basis amount', before[wb], f(q, 'wbefore'))
    q4 = 'the-account-pays-tuition-every-year'
    check('account tuition, low', min(cb[y] for y in munis_years), f(q4, 'lo'))
    check('account tuition, high', max(cb[y] for y in munis_years), f(q4, 'hi'))

    # THE ACCOUNT'S BALANCE, by a second route: the annual report rows read with Decimal,
    # then the DATABASE's fund 2640 rows carried forward, then checked against the March
    # report's implied opening.
    bal = {}
    with open(os.path.join(DATA, 'special-revenue-read.csv'), encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['fund'] == '50/50 Grant Sped Tuitions':
                bal[int(r['fy'])] = D(r['carried'])
    db = sqlite3.connect(os.path.join(DATA, 'lunenburg.db'))
    flow = {}
    for fy, typ, e, enc in db.execute("SELECT fiscal_year, type, ytd_expended, encumbrances FROM "
                                      "munis_school_ytd WHERE period=13 AND fund='2640'"):
        a = flow.setdefault(int(fy), [D(0), D(0)])
        if typ == 'R':
            a[0] -= D(str(e or 0))
        else:
            a[1] += D(str(e or 0)) + D(str(enc or 0))
    for fy in sorted(y for y in flow if y > max(bal)):
        bal[fy] = bal[fy - 1] + flow[fy][0] - flow[fy][1]
    with open(os.path.join(DATA, 'school-special-revenue-fy26-q3.csv'), encoding='utf-8') as fh:
        q3 = next(r for r in csv.DictReader(fh) if r['fund'].lstrip("'") == '2640')
    implied = D(q3['balance']) - D(q3['revenue']) + D(q3['expenditure'])
    if abs(implied - bal[max(bal) - 1]) > D('0.01'):
        bad.append('carried 30 June balance %s is not the March report implied %s'
                   % (bal[max(bal) - 1], implied))
    yrs = pay['cb_account']['years']
    for row in yrs:
        if abs(D(str(row['closing'])) - bal[row['fy']]) > D('0.01'):
            bad.append('account balance FY%d: payload %s, recomputed %s'
                       % (row['fy'], row['closing'], bal[row['fy']]))
    pk = max(bal, key=bal.get)
    check('account balance peak year', pk, f(q4, 'pfy'))
    check('account balance peak', float(bal[pk]), f(q4, 'peak'))
    check('account balance at the last close', float(r0(bal[max(bal)] * 100)) / 100,
          f(q4, 'bal'))
    ys = sorted(bal)[-7:]
    check('years falling, last six', sum(1 for a, b in zip(ys, ys[1:]) if bal[b] < bal[a]),
          f(q4, 'fell'))

    pct = max(round(100.0 * var[y]['indist'] / led[y]['indist'][0], 1) for y in years)
    check('in-district largest overrun share', pct, f('tuition-misses-both-ways', 'band'))
    tr = [var[y]['trans'] for y in years]
    check('transport years over', sum(1 for v in tr if v > 0), f('tuition-misses-both-ways', 't_over'))
    check('transport worst overrun', max(tr), f('tuition-misses-both-ways', 't_worst'))

    # THE CIRCUIT BREAKER CHART, every row, by a second route: DESE's CSV extracts rather
    # than the database, the payment file's CSV, Decimal sums.
    pays = {}
    with open(os.path.join(DATA, 'dese-circuit-breaker.csv'), encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['lea'] == LEA and r['level'] == 'district':
                pays[int(r['fy'])] = r0(D(r['total_quarterly_payment'] or '0'))
    split = {}
    with open(os.path.join(DATA, 'dese-function-expenditure.csv'), encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['lea'] == LEA and r['level'] == 'detail' and r['func_code'] in ('9300', '9400'):
                a = split.setdefault(int(r['fy']), [D(0), D(0)])
                a[0] += D(r['gen_fund'] or '0')
                a[1] += D(r['grants_revolving'] or '0')
    want = []
    for y in years:
        row = dict(fy=y, received=pays.get(y), earned=pays.get(y + 1), gf=None, cb_account=None,
                   other=None, other_unsplit=None, total=None)
        if y in split:
            g, o = r0(split[y][0]), r0(split[y][1])
            row.update(gf=g, total=g + o)
            if y in cb:
                row.update(cb_account=cb[y], other=o - cb[y], basis='dese+munis')
            else:
                row.update(other_unsplit=o, basis='dese')
        else:
            row.update(gf=led[y]['ood'][1], cb_account=cb[y], basis='munis')
        want.append(row)
    got = pay['circuit_breaker']['rows']
    if len(got) != len(want):
        bad.append('circuit breaker chart: %d rows, recomputed %d' % (len(got), len(want)))
    for g, w in zip(got, want):
        if g != w:
            bad.append('circuit breaker chart FY%s: payload %r, recomputed %r' % (w['fy'], g, w))
    last = max(pays)
    check('latest circuit breaker payment', pays[last], f('the-refund-arrives-a-year-later', 'paid'))
    check('latest payment year', last, f('the-refund-arrives-a-year-later', 'fy'))
    check('the year it pays for', last - 1, f('the-refund-arrives-a-year-later', 'for'))
    # The paragraph that calls one figure unexplained rests on an equality; assert it.
    u = pay['circuit_breaker']['unexplained']
    if u['other'] != pays.get(u['fy']):
        bad.append('the unexplained remainder no longer equals the FY%d payment' % u['fy'])
    # The stat row, recomputed.
    stats = [x['value'] for x in pay['stats']]
    for v in (gross[worst_fy], r0(bal[max(bal)]), pays[last]):
        if '${:,}'.format(v) not in stats:
            bad.append('stat %s is not in the stat row' % v)

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
          f('the-300000-question', 'cap'))
    if '${:,}'.format(r0(n[cy] * D('0.02'))) not in [x['value'] for x in pay['stats']]:
        bad.append('the reserve cap is not in the stat row')

    # PER CHILD BY TYPE, from the CSV extracts.
    ft = {}
    with open(os.path.join(DATA, 'dese-function-expenditure.csv'), encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['lea'] == LEA and r['level'] == 'detail' and r['func_code'] in ('9300', '9400'):
                ft[(int(r['fy']), r['func_code'])] = D(r['total'] or '0')
    with open(os.path.join(DATA, 'placement-counts.csv'), encoding='utf-8') as fh:
        pc = {int(r['fy']): r for r in csv.DictReader(fh)}
    nps = []
    for row in rq['by_type']:
        r = pc[row['fy']]
        col, npub = int(r['collaborative']), int(r['day']) + int(r['residential'])
        check('per collaborative FY%d' % row['fy'], r0(ft[(row['fy'], '9400')] / col),
              row['per_collaborative'])
        check('per non-public FY%d' % row['fy'], r0(ft[(row['fy'], '9300')] / npub),
              row['per_nonpublic'])
        nps.append(r0(ft[(row['fy'], '9300')] / npub))
    check('non-public median', r0(D(str(median(nps)))), rq['nonpublic_median'])

    # THE CAPTIONS: every quote re-found in its caption file, by a plain substring search
    # over the raw segments joined with single spaces, and the per-child figure re-parsed.
    for c in rq['said']:
        fn = os.path.join(ROOT, 'sources', 'data', 'youtube-transcripts', 'school-committee')
        hit = False
        for name in os.listdir(fn):
            if name.startswith(c['date']):
                segs = json.load(open(os.path.join(fn, name), encoding='utf-8'))['segments']
                if ' '.join(' '.join(x['text'].split()) for x in segs).find(c['quote']) >= 0:
                    hit = True
        if not hit:
            bad.append('caption not found: %r' % c['quote'][:50])
    m_ = re.search(r'average price of ([\d,]+) per child',
                   next(c['quote'] for c in rq['said'] if c['key'] == 'average'))
    check('per child as the captions render it', int(m_.group(1).replace(',', '')),
          rq['said_per_child'])

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
