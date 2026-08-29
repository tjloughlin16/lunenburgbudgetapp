"""Recompute every figure in the budget-versus-actual analysis, and fail if one drifted.

Rule 9: figures in a finished document get re-checked by script, not re-read. This file's
companion, verify_sped_analysis.py, caught stale prose four times in one day.

Everything here is recomputed from the extracted series and the FY27 workbook. Where the
two disagree that is the finding, not an error, so both are checked against the document
rather than against each other.

    python3 scripts/verify_budget_vs_actual.py
"""
import os, sys, csv, collections, statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, 'sources/analyses/budget-vs-actual.md')
DATA = os.path.join(ROOT, 'sources/data')

TEXT = open(DOC, encoding='utf-8').read()
PLAIN = TEXT.replace('**', '')
FAILS = []

# FY21's actual column is its budget in 98% of lines, so the year is excluded everywhere.
# Documented in the analysis; enforced here so a future pass cannot quietly reinstate it.
EXCLUDED_YEARS = {2021}


def present(label, needle):
    ok = needle in TEXT or needle in PLAIN
    if not ok:
        FAILS.append(f'{label}: "{needle}" not in the document')
    print(f"  {'OK  ' if ok else 'GONE'}  {label:<44} {needle}")


def money(v):
    return f'${v:,.0f}'


rows = list(csv.DictReader(open(os.path.join(DATA, 'line-history.csv'))))
cell = collections.defaultdict(dict)
for r in rows:
    cell[(r['key'], int(r['fy']))][r['stage']] = (float(r['value']),
                                                  r['documents_disagree'] == '1')


def usable(fy, b, a):
    """A cell fit to compare. The guards are the document's own, stated in §2."""
    return (fy not in EXCLUDED_YEARS and b and a and not b[1] and not a[1]
            and b[0] >= 10_000 and a[0] >= 1_000 and 0.02 <= a[0] / b[0] <= 20)


def group(pred):
    out = collections.defaultdict(lambda: [0, 0])
    for (k, fy), v in cell.items():
        if not pred(k):
            continue
        b, a = v.get('settled'), v.get('actual')
        if usable(fy, b, a):
            out[fy][0] += b[0]
            out[fy][1] += a[0]
    return dict(out)


print('Recomputing every figure in budget-vs-actual.md\n')

print('FY21, the year that is excluded')
pairs = [(v['settled'][0], v['actual'][0]) for (k, fy), v in cell.items()
         if fy == 2021 and 'settled' in v and 'actual' in v and v['settled'][0] > 10_000]
same = sum(1 for b, a in pairs if abs(b - a) < 1)
present('lines with both figures', f'{len(pairs)} lines')
present('identical to the dollar', f'{same} of {len(pairs)}')

print('\nThe groups, five years each')
for name, pred in (
        ('Everything measured', lambda k: True),
        ('Special education staff',
         lambda k: ('special ed' in k or 'specl ed' in k) and 'tuition' not in k),
        ('Out-of-district tuition', lambda k: 'tuition' in k),
        ('Special education, all in',
         lambda k: 'special ed' in k or 'specl ed' in k or 'tuition' in k)):
    g = group(pred)
    for fy in sorted(g):
        b, a = g[fy]
        present(f'{name} FY{fy % 100}', f'{(a / b - 1) * 100:+.1f}%')

print('\nThe consistency test')
per = collections.defaultdict(list)
for (k, fy), v in cell.items():
    b, a = v.get('settled'), v.get('actual')
    if usable(fy, b, a):
        per[k].append(a[0] / b[0] - 1)
multi = {k: v for k, v in per.items() if len(v) >= 4}
always = [k for k, v in multi.items()
          if all(d > 0.02 for d in v) or all(d < -0.02 for d in v)]
present('lines with four or more usable years', f'{len(multi)} lines')
present('of those, missing the same way every year', f'Seven of them'
        if len(always) == 7 else f'{len(always)} of them')

print('\nThe FY25 source disagreement')
wb = [r for r in csv.DictReader(open(os.path.join(DATA, 'lps-budget-lines.csv')))
      if r['kind'] == 'line']
t = lambda c: sum(float(r[c] or 0) for r in wb)
# Three published salary totals and two expense totals, so six budgets for one year.
SAL = {'workbook row 399': 16_809_123, 'workbook row 403': 17_156_461,
       'FY26 document': 17_188_342}
EXP = {'workbook': 8_165_299, 'FY26 document': 7_695_034}
import itertools
combos = sorted(s + e for s, e in itertools.product(SAL.values(), EXP.values()))
act = t('fy25_actual')
present('FY25 actual', money(act))
for v in SAL.values():
    present('a published FY25 salary total', money(v))
for v in EXP.values():
    present('a published FY25 expense total', money(v))
present('the lowest budget these support', money(min(combos)))
present('the highest', money(max(combos)))
present('the spread', money(max(combos) - min(combos)))
present('over budget at the lowest', money(act - min(combos)))
present('under budget at the highest', money(max(combos) - act))
present('the workbook disagreeing with itself', money(17_156_461 - 16_809_123))

print('\nFigures the document must NOT still contain')
for r in ['13% a year while the rest of the budget grew 3.4%',
          'roughly three-quarters of a million']:
    n = TEXT.count(r)
    ok = n == 0
    if not ok:
        FAILS.append(f'retired claim still present: {r}')
    print(f"  {'OK  ' if ok else 'STALE'}  retired: {r[:52]:<54} {n}")

print()
if FAILS:
    print(f'FAILED — {len(FAILS)} figure(s) do not match the data:')
    for f in FAILS:
        print('   -', f)
    sys.exit(1)
print('PASSED — every figure in the analysis matches what the data produces.')
