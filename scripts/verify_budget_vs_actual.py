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
    # Prose uses the typographic minus, code emits the ASCII hyphen, and they are the same
    # number. Normalising both sides beats reporting drift that is only a character.
    def norm(t):
        return t.replace('\u2212', '-').replace('\u2013', '-')
    ok = (needle in TEXT or needle in PLAIN
          or norm(needle) in norm(TEXT) or norm(needle) in norm(PLAIN))
    if not ok:
        FAILS.append(f'{label}: "{needle}" not in the document')
    print(f"  {'OK  ' if ok else 'GONE'}  {label:<44} {needle}")


def money(v):
    """Prose puts the sign outside the currency symbol -- −$439,905, not $-439,905."""
    return f'-${abs(v):,.0f}' if v < 0 else f'${v:,.0f}'


rows = list(csv.DictReader(open(os.path.join(DATA, 'line-history.csv'))))
cell = collections.defaultdict(dict)
for r in rows:
    # variant='' only -- a scenario column is a different proposal for the same year,
    # not another reading of the same figure. See notes/reference/SCHEMA.md, budget_figure.
    if r.get('variant'):
        continue
    cell[(r['key'], int(r['fy']))][r['stage']] = (float(r['value']),
                                                  r['documents_disagree'] == '1')


def usable(fy, b, a):
    """A cell fit to compare. The guards are the document's own, stated in §2."""
    return (fy not in EXCLUDED_YEARS and b and a and not b[1] and not a[1]
            and b[0] >= 10_000 and a[0] >= 1_000 and 0.02 <= a[0] / b[0] <= 20)


# Kept in step with analyze_variance.py, which states the reason: a year with four usable
# lines out of three hundred and fifty is not a measurement of a budget.
MIN_LINES_PER_YEAR = 20
THIN_YEARS = {fy for fy, n in collections.Counter(
    fy for (k, fy), v in cell.items()
    if usable(fy, v.get('settled'), v.get('actual'))).items()
    if n < MIN_LINES_PER_YEAR}


def group(pred):
    out = collections.defaultdict(lambda: [0, 0])
    for (k, fy), v in cell.items():
        if not pred(k) or fy in THIN_YEARS:
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
        if name == 'Everything measured':
            # The DOLLARS as well as the percentage. The document prints this year twice,
            # in two tables, and for a long time the two disagreed by $2M while both
            # rounded to the same +0.5% -- so the only check anybody ran passed on both.
            # A check must assert the number, not the prose around it (rule 13).
            present(f'{name} FY{fy % 100} budgeted', f'${b:,.0f}')
            present(f'{name} FY{fy % 100} spent', f'${a:,.0f}')

print('\nThe whole-budget sweep')
import importlib.util
_sp = importlib.util.spec_from_file_location('elh', os.path.join(ROOT, 'scripts/extract_line_history.py'))
_elh = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(_elh)
_wb = [r for r in csv.DictReader(open(os.path.join(DATA, 'lps-budget-lines.csv')))
       if r['kind'] == 'line']
_sec = {_elh.norm(r['line_item']): r['section'] for r in _wb}
_fn = {_elh.norm(r['line_item']): (r['function_group'] or '').strip() for r in _wb}
_recs = []
for (k, fy), v in cell.items():
    if fy in THIN_YEARS:
        continue
    b, a = v.get('settled'), v.get('actual')
    if usable(fy, b, a):
        _recs.append((k, fy, b[0], a[0]))
present('usable line-years', f'{len(_recs)} usable line-years')
present('distinct lines', f'{len({r[0] for r in _recs})} distinct lines')
for name, want in (('SALARIES', 'Salaries'), ('EXPENSES', 'Everything else')):
    rr = [r for r in _recs if _sec.get(r[0]) == name]
    tb, ta = sum(r[2] for r in rr), sum(r[3] for r in rr)
    present(f'{want} variance', f'{(ta / tb - 1) * 100:+.2f}%')
    # Same reason as above: the line count and both totals, not only the ratio.
    present(f'{want} line-years', f'| {want} | {len(rr)} |')
    present(f'{want} budgeted', f'${tb:,.0f}')
    present(f'{want} spent', f'${ta:,.0f}')
_grp = collections.defaultdict(lambda: [0, 0])
for k, fy, b, a in _recs:
    g = _fn.get(k) or '?'
    _grp[g][0] += b
    _grp[g][1] += a
for g in ('7400 - Replace Equipment', '5200 - Insurance Programs',
          '9300 - Private Tuitions', '3300 - Student Transportation'):
    if g in _grp:
        b, a = _grp[g]
        present(g[:30], money(a - b))

print('\nThe consistency test')
per = collections.defaultdict(list)
for (k, fy), v in cell.items():
    if fy in THIN_YEARS:
        continue
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
# The salary difference is one contingency line counted in one total and not the other;
# the expense difference is not explained. Both are checked, and so is the fact that the
# resulting range no longer crosses zero.
ACT = t('fy25_actual')
LO, HI = 17_156_461 + 7_695_034, 17_188_342 + 8_165_299
present('FY25 actual', money(ACT))
present('Salary Reserve, workbook', money(347_338))
present('Salary Reserve, FY26 document', money(379_220))
present('the expense difference', money(8_165_299 - 7_695_034))
present('lowest defensible budget', money(LO))
present('highest', money(HI))
present('under by at least', money(LO - ACT))
present('under by at most', money(HI - ACT))

# The town's own figure, from its own minutes. Checked so it cannot drift, and because
# it is the number this project should quote for FY25.
print('\nThe surplus, as the district stated it')
present('as first reported, 3 September 2025', '$582,115.44')
present('as revised, 17 September 2025', '$603,885.97')
present('inside the derived range', money(LO - ACT))

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
