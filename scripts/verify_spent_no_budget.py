#!/usr/bin/env python3
"""Every figure in /analysis/spent-with-no-budget, recomputed by a SECOND ROUTE.

    python3 scripts/verify_spent_no_budget.py

The generator reads `munis-school-ytd.csv` in floats, imports helpers from
build_sitting_on_money.py and classifies each row with one function. This script imports
nothing from either: it reads the CSV itself in Decimal, keys every row by the ACCOUNT STRING
(fund and department taken from the string, not from the columns), writes the three
definitions out again as three separate set comprehensions, and then checks the PUBLISHED
payload -- the by-year table, the four-year totals, every line's total, the recurring set,
the worked case, the special-fund measure, the stat row, every registered conclusion figure,
the rule-2 check on the conclusions as shipped, and that every cited gap is registered.
"""
import csv
import json
import os
import sys
from collections import defaultdict
from decimal import Decimal as D

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conclusions import check  # noqa: E402  -- the rule-2 check, re-run on the shipped payload

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(ROOT, 'sources', 'data', 'munis-school-ytd.csv')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'spent-with-no-budget.json')
SURPLUS = os.path.join(ROOT, 'fy28', 'public', 'data', 'fy26-school-surplus.json')
YEARS = (2023, 2024, 2025, 2026)
KG = ('0100-3-300-2330-03-2-12-1-511103', '0100-3-300-2330-03-2-13-1-511203')
HALF = D('0.005')

bad = []
CHECKED = set()


def d(s):
    s = (s or '').strip()
    return D(s) if s not in ('', '-') else D(0)


def same(name, got, want, tol=D('0.5')):
    if abs(D(str(got)) - D(str(want))) > tol:
        bad.append('%s: payload %s, recomputed %s' % (name, got, want))


def usd(x):
    n = int(D(x).quantize(D(1), rounding='ROUND_HALF_EVEN'))
    return ('-$%s' if n < 0 else '$%s') % format(abs(n), ',d')


# ---- the ledger, by the account string ------------------------------------------------
gf, sp = {}, defaultdict(list)
for r in csv.DictReader(open(CSV, encoding='utf-8')):
    if r['period'] != '13':
        continue
    y = int(r['fiscal_year'])
    seg = r['account'].split('-')
    if r['report'] == 'special-school' and r['type'] == 'E':
        sp[y].append((d(r['revised_budget']), d(r['ytd_expended'])))
    elif r['report'] == 'gf-school':
        if seg[0] != '0100' or seg[2] != '300':
            bad.append('gf-school row outside fund 0100 / department 300: %s' % r['account'])
        gf[(y, r['account'])] = dict(o=d(r['original_approp']), r=d(r['revised_budget']),
                                     s=d(r['ytd_expended']), e=d(r['encumbrances']),
                                     av=d(r['available_budget']))

zero = lambda v: abs(v) < HALF  # noqa: E731
A = {y: {a for (yy, a), v in gf.items() if yy == y and zero(v['o']) and v['s'] > HALF} for y in YEARS}
B = {y: {a for (yy, a), v in gf.items() if yy == y and zero(v['r']) and v['s'] > HALF} for y in YEARS}
C = {y: {a for (yy, a), v in gf.items() if yy == y and zero(v['o']) and v['r'] > HALF} for y in YEARS}

pay = json.load(open(PAYLOAD, encoding='utf-8'))
conc = {c['id']: c for c in pay['conclusions']}


def fig(cid, key, want, tol=D('0.5')):
    CHECKED.add((cid, key))
    if key not in conc[cid]['figures']:
        bad.append('%s/%s: not registered' % (cid, key))
        return
    f = conc[cid]['figures'][key]
    same('%s/%s' % (cid, key), f['value'], want, tol)


# ---- by year ------------------------------------------------------------------------
py = {y['fy']: y for y in pay['by_year']}
tot = dict(a=D(0), b=D(0), c=D(0))
shares = []
for y in YEARS:
    a_sp = sum(gf[(y, a)]['s'] for a in A[y])
    b_sp = sum(gf[(y, a)]['s'] for a in B[y])
    c_mv = sum(gf[(y, a)]['r'] for a in C[y])
    dept_s = sum(v['s'] for (yy, _a), v in gf.items() if yy == y)
    dept_av = sum(v['av'] for (yy, _a), v in gf.items() if yy == y)
    tot['a'] += a_sp
    tot['b'] += b_sp
    tot['c'] += c_mv
    shares.append(a_sp / dept_s * 100)
    p = py[y]
    for k, want in (('a_n', len(A[y])), ('b_n', len(B[y])), ('c_n', len(C[y])),
                    ('c_also_a', len(C[y] & A[y]))):
        if p[k] != want:
            bad.append('FY%d %s: payload %s, recomputed %s' % (y, k, p[k], want))
    same('FY%d a_spent' % y, p['a_spent'], a_sp, D('0.01'))
    same('FY%d b_spent' % y, p['b_spent'], b_sp, D('0.01'))
    same('FY%d c_moved' % y, p['c_moved'], c_mv, D('0.01'))
    same('FY%d dept_spent' % y, p['dept_spent'], dept_s, D('0.01'))
    same('FY%d dept_available' % y, p['dept_available'], dept_av, D('0.01'))
    if dept_av <= 0:
        bad.append('FY%d closed over its total -- "covered elsewhere in the total" is false' % y)
    if not B[y] <= A[y]:
        bad.append('FY%d: a (b) line is not an (a) line, and the text says every one is' % y)
    fig('spent-on-lines-voted-at-zero', 'a%d' % y, a_sp)
    fig('spent-on-lines-voted-at-zero', 'an%d' % y, len(A[y]), D(0))
    if B[y]:
        fig('still-zero-after-transfers', 'b%d' % y, b_sp)
        fig('still-zero-after-transfers', 'bn%d' % y, len(B[y]), D(0))
    if C[y]:
        fig('money-found-by-transfer', 'c%d' % y, c_mv)
        fig('money-found-by-transfer', 'cn%d' % y, len(C[y]), D(0))
fig('spent-on-lines-voted-at-zero', 'a_tot', tot['a'])
fig('spent-on-lines-voted-at-zero', 'share', max(shares), D('0.05'))
fig('still-zero-after-transfers', 'b_tot', tot['b'])
fig('money-found-by-transfer', 'c_tot', tot['c'])

# ---- line by line, and persistence ------------------------------------------------------
a_years = defaultdict(list)
for y in YEARS:
    for a in A[y]:
        a_years[a].append(y)
pl = {ln['account']: ln for ln in pay['lines']}
every = set().union(*A.values(), *B.values(), *C.values())
if set(pl) != every:
    bad.append('lines: payload carries %s, recomputed %s' % (sorted(set(pl) ^ every), ''))
for a, ys in a_years.items():
    same('line %s a_total' % a, pl[a]['a_total'], sum(gf[(y, a)]['s'] for y in ys), D('0.01'))
voted_other = sum(1 for a, ys in a_years.items()
                  if any(gf[(y, a)]['o'] > HALF for y in YEARS if y not in ys))
recurring = {a for a, ys in a_years.items() if len(ys) >= 2}
inst = [(a, y) for a, ys in a_years.items() for y in ys if y > YEARS[0]]
prior = sum(1 for a, y in inst if gf[(y - 1, a)]['s'] > HALF)
if set(pay['recurring']) != recurring:
    bad.append('recurring: payload %s, recomputed %s' % (sorted(pay['recurring']), sorted(recurring)))
fig('mostly-a-missing-year', 'n_other', voted_other, D(0))
fig('mostly-a-missing-year', 'n_a', len(a_years), D(0))
fig('mostly-a-missing-year', 'n_rec', len(recurring), D(0))
fig('mostly-a-missing-year', 'n_prior', prior, D(0))
fig('mostly-a-missing-year', 'n_inst', len(inst), D(0))
for k in conc['mostly-a-missing-year']['figures']:
    if k.startswith('r'):
        CHECKED.add(('mostly-a-missing-year', k))
rec_counts = sorted((len(a_years[a]) for a in recurring), reverse=True)
got_counts = sorted((conc['mostly-a-missing-year']['figures']['r%d' % i]['value']
                     for i in range(len(recurring))), reverse=True)
if rec_counts != got_counts:
    bad.append('recurring year counts: payload %s, recomputed %s' % (got_counts, rec_counts))

# ---- the worked case ----------------------------------------------------------------------
k26 = sum(gf[(2026, a)]['s'] for a in KG)
k25v = sum(gf[(2025, a)]['o'] for a in KG)
if any(not zero(gf[(2026, a)]['o']) for a in KG):
    bad.append('a kindergarten line is not voted at $0 in FY2026')
if any(gf[(y, KG[0])]['s'] > HALF for y in YEARS[:-1]):
    bad.append('the kindergarten aides line spent before FY2026, and the text says it did not')
fig('kindergarten-aides-fy2026', 'k26', k26)
fig('kindergarten-aides-fy2026', 'k25v', k25v)
fig('kindergarten-aides-fy2026', 'kaid', gf[(2026, KG[0])]['s'])
fig('kindergarten-aides-fy2026', 'kpar', gf[(2026, KG[1])]['s'])
sur = {c['id']: c for c in json.load(open(SURPLUS, encoding='utf-8'))['conclusions']}
fig('kindergarten-aides-fy2026', 'pover',
    D(str(sur['salary-lines-left-money-though-aides-ran-over']['figures']['s_paras']['value'])))

# ---- special funds ------------------------------------------------------------------------
psf = {s['fy']: s for s in pay['special_funds']}
for y in YEARS:
    spending = [(r, s) for r, s in sp[y] if s > HALF]
    at0 = [(r, s) for r, s in spending if zero(r)]
    if psf[y]['lines_spending'] != len(spending) or psf[y]['at_zero'] != len(at0):
        bad.append('FY%d special-fund counts differ' % y)
    same('FY%d special spent at zero' % y, psf[y]['spent_at_zero'], sum(s for _r, s in at0), D('0.01'))

# ---- the stat row ---------------------------------------------------------------------------
want_stats = [usd(tot['a']), usd(tot['b']), usd(k26)]
got_stats = [s['value'] for s in pay['stats']]
if got_stats != want_stats:
    bad.append('stats: payload %s, recomputed %s' % (got_stats, want_stats))
for s in pay['stats']:
    if not s.get('label'):
        bad.append('a stat has no label, so no unit')

# ---- every registered figure was checked; the conclusions as shipped pass rule 2 -----------
for cid, c in conc.items():
    for k in c['figures']:
        if (cid, k) not in CHECKED:
            bad.append('%s/%s is registered and this script never recomputed it' % (cid, k))
bad.extend(check('spent-with-no-budget', pay['conclusions']))

# ---- the gaps it cites are registered -------------------------------------------------------
have = {r['what'].strip() for r in csv.DictReader(open(GAPS, encoding='utf-8'))}
for g in pay['gaps']:
    if g not in have:
        bad.append('gap cited and not registered: %s' % g[:70])

if bad:
    print('verify_spent_no_budget: %d PROBLEM(S)' % len(bad))
    for b in bad:
        print('  - ' + b)
    sys.exit(1)
print('verify_spent_no_budget: every figure recomputed in Decimal from the CSV and matched -- '
      '%d conclusion figures, %d lines, %d years' % (len(CHECKED), len(pl), len(YEARS)))
