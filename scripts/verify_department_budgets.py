#!/usr/bin/env python3
"""Recompute every figure in /analysis/department-budgets from the ledger, independently.

    python3 scripts/verify_department_budgets.py

Nothing here imports the generator. Each headline figure is derived again from
`sources/data/gl-history.csv` and the DLS files by a second route, then asserted against
the VALUE the payload registered for it and against the TEXT the markdown prints -- on a
word boundary, because a bare substring check once passed on digits inside a bigger number.

It also asserts the STRUCTURE the conclusions rest on, not only their figures:
  * the county retirement assessment really is the fastest-growing group;
  * no school or town department other than the one named ended a year over budget;
  * the snow removal count is over the complete years only;
  * every gap this report cites is a row in money-gaps.csv;
  * the report is listed in UNLISTED (it is a draft and must have no door);
  * the conclusions pass scripts/conclusions.py's rule-2 check as published.
Fails rather than warns.
"""
import csv
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import conclusions as C  # noqa: E402

ID = 'department-budgets'
PAY = os.path.join(ROOT, 'fy28', 'public', 'data', ID + '.json')
MD = os.path.join(ROOT, 'sources', 'analyses', ID + '.md')
GL = os.path.join(ROOT, 'sources', 'data', 'gl-history.csv')
NG = os.path.join(ROOT, 'sources', 'data', 'dls-new-growth.csv')
OV = os.path.join(ROOT, 'sources', 'data', 'dls-override-votes.csv')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
UNLISTED = os.path.join(ROOT, 'sources', 'analyses', 'UNLISTED')

bad = []


def fail(msg):
    bad.append(msg)


def num(x):
    return float(x) if x not in ('', None) else 0.0


def in_text(text, s):
    """`s` present in `text`, not as part of a longer number."""
    return re.search(r'(?<![\d.,])' + re.escape(s) + r'(?![\d])', text) is not None


def main():
    pay = json.load(open(PAY, encoding='utf-8'))
    md = ' '.join(open(MD, encoding='utf-8').read().split())
    rows = [r for r in csv.DictReader(open(GL, encoding='utf-8')) if r['sheet'] == 'general_fund']
    years = sorted({int(r['fiscal_year']) for r in rows})
    y0, y1 = years[0], years[-1]
    complete = [y for y in years
                if not any(r['actual_is_partial'] == 'true' for r in rows
                           if int(r['fiscal_year']) == y)]

    # ---- the two operating groups, by a second route: explicit department sets
    benefit = lambda r: r['object'].startswith('5700') or r['object'] == '570010'
    def is_school(r):
        return r['department_code'] in ('300', '301') and not benefit(r)
    def is_town(r):
        fn = r['account'].split('-')[1]
        return fn in '12456' and len(fn) == 1 and r['department_code'] not in ('132', '133')

    def total(pred, y, col='original'):
        return sum(num(r[col]) for r in rows if int(r['fiscal_year']) == y and pred(r))

    def rate(pred, a, b):
        return ((total(pred, b) / total(pred, a)) ** (1 / (b - a)) - 1) * 100

    lim = {int(r['fy']) - 1: float(r['prior_levy_limit'])
           for r in csv.DictReader(open(NG, encoding='utf-8'))
           if r['municipality'] == 'Lunenburg' and r['prior_levy_limit']}
    ovr = [(int(r['fy']), float(r['amount'])) for r in csv.DictReader(open(OV, encoding='utf-8'))
           if r['municipality'] == 'Lunenburg' and r['result'] == 'WIN'
           and r['vote_type'] == 'Override' and y0 < int(r['fy']) <= y1]
    lev_last = lim[y1] - sum(a * 1.025 ** (y1 - y) for y, a in ovr)
    levy_ex = ((lev_last / lim[y0]) ** (1 / (y1 - y0)) - 1) * 100
    fund0 = sum(num(r['original']) for r in rows if int(r['fiscal_year']) == y0)

    def pull(pred):
        return total(pred, y0) / fund0 * (rate(pred, y0, y1) - levy_ex)

    # every group, for the "fastest" assertion -- by function and department code
    def grp(key):
        def p(r):
            d, fn = r['department_code'], r['account'].split('-')[1]
            if key == 'retirement':
                return d == '820'
            if key == 'debt':
                return fn == '7'
            if key == 'reserves':
                return d in ('132', '133')
            if key == 'assessments':
                return d in ('310', '825', '841')
            if key == 'benefits':
                return (d in ('300', '301') and benefit(r)) or fn == '9'
            return {'schools': is_school, 'town': is_town}[key](r)
        return p
    rates = {k: rate(grp(k), y0, y1) for k in
             ('schools', 'town', 'benefits', 'retirement', 'debt', 'assessments', 'reserves')}

    # ---- execution
    def spent(pred):
        rv = sum(total(pred, y, 'revised') for y in complete)
        ac = sum(total(pred, y, 'actual') for y in complete)
        return ac / rv * 100, rv - ac

    s_sp, s_tb = spent(is_school)
    t_sp, t_tb = spent(is_town)

    dept_years_over = set()
    for d in {r['department_code'] for r in rows}:
        for y in complete:
            sel = [r for r in rows if r['department_code'] == d and int(r['fiscal_year']) == y]
            if sum(num(r['actual']) for r in sel) > sum(num(r['revised']) for r in sel) + 1:
                dept_years_over.add((d, y))
    operating = {r['department_code'] for r in rows if is_school(r) or is_town(r)}
    op_over = sorted(x for x in dept_years_over if x[0] in operating)

    snow = [r for r in rows if r['department_code'] == '423']
    snow_over = sum(1 for y in complete
                    if sum(num(r['actual']) for r in snow if int(r['fiscal_year']) == y)
                    > sum(num(r['original']) for r in snow if int(r['fiscal_year']) == y) + 1)
    snow_tx = sum(num(r['transfers_1']) + num(r['transfers_2']) for r in snow
                  if int(r['fiscal_year']) in complete)

    # ---- residual
    by = {(r['account'], int(r['fiscal_year'])): r for r in rows}
    res_amt = fit_amt = 0.0
    res_n = 0
    for (a, y), r in by.items():
        x = num(r['revised']) - num(r['original']) - num(r['transfers_1']) - num(r['transfers_2'])
        if x >= 0.5:
            res_n += 1
            res_amt += x
            p = by.get((a, y - 1))
            if p and num(p['revised']) - num(p['actual']) >= x - 0.5:
                fit_amt += x

    ret = grp('retirement')
    expect = {
        'town-departments-grew-faster-than-the-schools': {
            't': rate(is_town, y0, y1), 's': rate(is_school, y0, y1),
            'tp': rate(is_town, y0, y1 - 1), 'sp': rate(is_school, y0, y1 - 1),
            'b': rate(lambda r: r['department_code'] in ('300', '301'), y0, y1)},
        'ranked-by-pull-town-departments-lead': {
            'pt': pull(is_town), 'ps': pull(is_school), 'lx': levy_ex},
        'the-county-retirement-assessment-grew-fastest': {
            'r': rates['retirement'], 'a': total(ret, y0), 'b': total(ret, y1)},
        'the-schools-leave-less-unspent': {'ss': s_sp, 'ts': t_sp, 'tb': t_tb, 'sb': s_tb},
        'snow-and-ice-is-the-budget-that-runs-over': {'n': snow_over, 'x': snow_tx},
        'money-reached-budgets-outside-any-recorded-transfer': {
            'a': res_amt, 'f': fit_amt / res_amt * 100, 'r': res_n},
    }

    both = sorted((float(r['amount']) for r in csv.DictReader(open(OV, encoding='utf-8'))
                   if r['municipality'] == 'Lunenburg' and r['vote_type'] == 'Override'
                   and 'town and school' in r['description'].lower()), reverse=True)
    if both:
        expect['priced-at-level-service-the-town-showed-a-gap-too'] = {'o': both[0]}

    cons = {c['id']: c for c in pay['conclusions']}
    checked = 0
    for cid, figs in expect.items():
        c = cons.get(cid)
        if not c:
            fail('%s: conclusion missing from the payload' % cid)
            continue
        for k, v in figs.items():
            f = c['figures'].get(k)
            if f is None:
                fail('%s/%s: figure not registered' % (cid, k))
                continue
            tol = max(1e-6, abs(v) * 1e-9) if isinstance(f['value'], (int, float)) else 0
            if abs(float(f['value']) - v) > max(tol, 0.005):
                fail('%s/%s: payload says %r, recomputed %r' % (cid, k, f['value'], v))
            if not in_text(md, f['text']):
                fail('%s/%s: %r is not in the markdown' % (cid, k, f['text']))
            checked += 1

    # ---- structure
    if max(rates, key=rates.get) != 'retirement':
        fail('county retirement is no longer the fastest group: %r' % rates)
    if not (rates['town'] > rates['schools']):
        fail('town departments no longer grew faster than the schools')
    if not (pull(is_town) == max(pull(grp(k)) for k in rates)):
        fail('town departments no longer lead the pull ranking')
    if not (pull(is_school) < 0):
        fail('the schools\u2019 pull is no longer negative')
    if len({d for d, _ in op_over}) != 1 or op_over[0][0] != '423':
        fail('operating departments over their final budget are now %r' % op_over)
    else:
        so = cons['the-schools-leave-less-unspent']['so_what']
        times = {1: 'once', 2: 'twice'}.get(len(op_over))
        if times and times not in so:
            fail('the so_what says %r but %d department-years ran over' % (so, len(op_over)))
    if y1 in complete:
        fail('FY%d is complete in the ledger now; the part-year exclusion is stale' % y1)

    gaps = {r['what'] for r in csv.DictReader(open(GAPS, encoding='utf-8'))}
    cited = re.findall(r'## Gaps registered by this report\s*(.*?)\s*Already registered', md)
    for line in (cited[0].split(' - ')[1:] if cited else []):
        if line.strip() not in gaps:
            fail('gap cited but not registered: %r' % line.strip())
    if not cited:
        fail('the gaps section is missing from the markdown')

    unl = [l.strip() for l in open(UNLISTED, encoding='utf-8') if l.strip()
           and not l.startswith('#')]
    if ID not in unl:
        fail('%s is not in sources/analyses/UNLISTED, so it would join the site' % ID)

    bad.extend(C.check(ID, pay['conclusions']))

    gen = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts',
                                                       'build_department_budgets.py'), '--check'],
                         capture_output=True, text=True)
    if gen.returncode:
        fail('generator --check: ' + gen.stderr.strip())

    if bad:
        print('FAIL %d:\n  %s' % (len(bad), '\n  '.join(bad)), file=sys.stderr)
        return 1
    print('department-budgets: %d figures recomputed and found in the document; structure '
          'holds; %d conclusions pass the rule-2 check' % (checked, len(pay['conclusions'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
