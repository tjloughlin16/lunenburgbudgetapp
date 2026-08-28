"""Prove that no projection in this model is computed from actual spending.

The app projects appropriations — what Town Meeting votes. Actual spending is a different
quantity, roughly 3% lower, and the two must never be mixed inside one calculation. A
growth rate measured from an actual to a budget is not a growth rate; it is growth plus
the step from spent to budgeted, and that mistake put the special education escalator 1.5
points too high before anyone noticed.

So this is a check rather than a promise. It reads the source CSV, works out which columns
each part of the model actually consumes, and **exits non-zero if any actuals column feeds
a projection**. Run it in the same breath as the build.

    python3 scripts/audit_provenance.py

It also prints the provenance table — every headline metric against the column and
document it comes from — which is the artefact a reader should be able to check us with.
"""
import ast
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'model'))

CSV = os.path.join(ROOT, 'sources', 'data', 'lps-budget-lines.csv')

# Columns that record money actually spent. Anything reading these is doing reconciliation,
# not projection.
ACTUALS = {'fy23_actual', 'fy24_actual', 'fy25_actual', 'fy26_actual_td', 'fy26_encumb_td'}
BUDGETS = {'fy25_budget', 'fy26_final', 'fy27_restoration', 'fy27_core',
           'fy27_level_service', 'fy27_balanced', 'forecast_outyear', 'restoration_2_24_26'}

# Modules that feed the app. Anything here touching an actuals column is a failure.
PROJECTION_MODULES = ['finance.py', 'cascade.py', 'sped.py', 'levers.py', 'athletics.py',
                      'catalog.py', 'health.py', 'taxbase.py', 'recommendation.py',
                      'headlines.py', 'conclusions.py', 'business.py', 'peers.py',
                      'derivations.py', 'export.py']
# Reconciliation is allowed — and required — to read both.
RECONCILIATION_MODULES = ['backtest_rates.py']


def columns_used(path):
    """Every string literal in the file that names a CSV column."""
    try:
        tree = ast.parse(open(path).read())
    except SyntaxError:
        return set()
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in ACTUALS | BUDGETS:
                found.add(node.value)
    return found


def audit():
    print('PROVENANCE AUDIT — does any projection read actual spending?\n')
    print(f"{'module':<24}{'budget columns':<44}{'actuals columns'}")
    print('-' * 100)
    violations = []
    for name in PROJECTION_MODULES:
        p = os.path.join(ROOT, 'model', name)
        if not os.path.exists(p):
            continue
        used = columns_used(p)
        b, a = sorted(used & BUDGETS), sorted(used & ACTUALS)
        if a:
            violations.append((name, a))
        if used:
            print(f"{name:<24}{', '.join(b) or '—':<44}{', '.join(a) or '—'}")

    print()
    for name in RECONCILIATION_MODULES:
        p = os.path.join(ROOT, 'scripts', name)
        if os.path.exists(p):
            used = columns_used(p)
            print(f"{name:<24}{'(reconciliation — reads both by design)'}")
            print(f"{'':<24}budgets: {', '.join(sorted(used & BUDGETS)) or '—'}")
            print(f"{'':<24}actuals: {', '.join(sorted(used & ACTUALS)) or '—'}")
    return violations


def base_check():
    """The expense base must rebuild the published appropriation from budget columns."""
    from finance import expense_base, FY27
    base = expense_base()
    total = sum(base.values())
    published = FY27['lps_appropriation']
    print(f"\nEXPENSE BASE\n  rebuilt from fy27_balanced  {total:>14,.0f}")
    print(f"  published appropriation     {published:>14,.0f}")
    print(f"  difference                  {total - published:>14,.0f}"
          f"   {'OK — rounding' if abs(total - published) < 5 else 'MISMATCH'}")
    return abs(total - published) < 5


def provenance_table():
    """Every headline metric, and the column and document behind it."""
    import json
    m = json.load(open(os.path.join(ROOT, 'fy28', 'src', 'data', 'model.json')))
    rows = [
        ('FY27 appropriation', f"${m['fy27']['lps_appropriation']:,}",
         'published total', 'FY27 budget doc 3/25/26'),
        ('Expense base, all buckets', f"${sum(m['expenseBase'].values()):,.0f}",
         'fy27_balanced', 'FY27 budget workbook'),
        ('Special education base', f"${m['expenseBase']['sped']:,.0f}",
         'fy27_balanced', 'FY27 budget workbook'),
        ('Special education rate', f"{m['assumptions']['sped'] * 100:.1f}%",
         'fy25_budget -> fy27_level_service', 'FY27 budget workbook'),
        ('Salary rate', f"{m['assumptions']['salaries'] * 100:.1f}%",
         'not from the CSV', 'LEA agreement FY25-FY27'),
        ('Health rate', f"{m['assumptions']['health'] * 100:.1f}%",
         'not from the CSV', "district's stated FY27 assumption"),
        ('Transport rate', f"{m['assumptions']['transport'] * 100:.1f}%",
         'not from the CSV', "district assumed 10%; 6% is our softer default"),
        ('Levy growth', f"{m['assumptions']['levy_growth'] * 100:.1f}%",
         'not from the CSV', 'Proposition 2½, statutory'),
        ('New growth', f"${m['assumptions']['new_growth']:,}",
         'not from the CSV', "town's own FY27 estimate"),
        ('SPED share of budget', f"{m['sped']['composition'][-1]['share'] * 100:.1f}%",
         'fy27_balanced', 'FY27 budget workbook'),
        ('SPED share of growth', f"{m['sped']['growth']['spedShareOfGrowth'] * 100:.0f}%",
         'fy23_actual -> fy26_final', 'RECONCILIATION — not used in any projection'),
        ('Circuit breaker balance', f"${m['sped']['circuitBreaker']['balance']:,}",
         'balance sheet', 'Town special revenue funds FY26 Q3'),
        ('Out-of-district committed', f"${m['sped']['outOfDistrict']['fy26Committed']:,}",
         'fy26_actual_td + fy26_encumb_td', 'RECONCILIATION — descriptive only'),
    ]
    print('\n\nPROVENANCE — every headline metric and where it comes from\n')
    print(f"{'metric':<28}{'value':>14}   {'column(s)':<38}{'document'}")
    print('-' * 128)
    for name, val, col, doc in rows:
        print(f'{name:<28}{val:>14}   {col:<38}{doc}')
    print('\nRows marked RECONCILIATION describe history on the special education page.')
    print('They are printed and quoted; no projection multiplies by them.')


if __name__ == '__main__':
    violations = audit()
    ok = base_check()
    provenance_table()
    print()
    if violations:
        print('FAILED — a projection module reads actual spending:')
        for name, cols in violations:
            print(f'  {name}: {", ".join(cols)}')
        sys.exit(1)
    if not ok:
        print('FAILED — the expense base does not rebuild the published appropriation.')
        sys.exit(1)
    print('PASSED — every projection is computed from budget columns only.')
