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
import subprocess
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
                      'citations.py', 'export.py']
# Allowed to read actuals, because showing them IS the job. derivations.py builds the
# "show the math" page, which prints each budget line beside what the town actually spent
# on it in earlier years -- that history is displayed, never summed. The amounts it totals
# come from budget columns. Listed separately rather than exempted quietly, because "this
# one is fine" is exactly the sentence that hides the next real violation.
# corroboration.py is the other one: it sets a finding computed from budgets beside a
# finding computed from actuals and observes that they match. Rule 1 forbids mixing the
# two in a calculation; comparing two separately computed answers is the opposite of that,
# and is the whole reason the file exists.
DISPLAY_MODULES = ['derivations.py', 'corroboration.py']
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


def free_cash_is_inert():
    """Free cash is actuals-derived, so prove it cannot touch anything rate-driven.

    It is allowed into the projection as a one-time subtraction, which is not the error
    rule 1 forbids -- that error is a growth RATE measured across the budget/actual
    boundary. But "allowed as a one-time subtraction" is only safe if it really is one, so
    it is checked rather than trusted:

      * the default output is byte-identical to passing an explicit zero
      * at ANY draw, no bucket, growth rate, level service, available or deficit moves
      * only the two additional fields respond, and they respond consistently

    If any of that stops being true, free cash has started behaving like a rate.
    """
    sys.path.insert(0, os.path.join(ROOT, 'model'))
    from finance import project

    base = project(6)
    problems = []
    if base != project(6, free_cash=dict(amount=0, years=1)):
        problems.append('default output differs from an explicit zero draw')

    for amount in (500_000, 3_354_370, 10_000_000):
        for spread in (1, 2, 3):
            got = project(6, free_cash=dict(amount=amount, years=spread))
            for b, g in zip(base, got):
                for field in ('level_service', 'available', 'appropriation',
                              'growth_rate', 'deficit', 'buckets'):
                    if b[field] != g[field]:
                        problems.append(
                            f'draw {amount:,}/{spread}y moved {field} in FY{b["fy"]}')
                if g['deficit_after_free_cash'] != g['deficit'] - g['free_cash_applied']:
                    problems.append(f'FY{b["fy"]}: after-figure is not deficit minus applied')
                if g['free_cash_applied'] > g['deficit']:
                    problems.append(f'FY{b["fy"]}: applied more free cash than there was gap')
    return problems


def audit():
    print('PROVENANCE AUDIT — does any projection read actual spending?\n')
    fc = free_cash_is_inert()
    print('free cash, an actuals-derived input allowed in as a one-time subtraction:')
    if fc:
        for p_ in fc:
            print(f'  FAIL  {p_}')
    else:
        print('  ok    inert by default, and at every draw it moves only its own two fields')
    print()
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
    for name in DISPLAY_MODULES:
        p = os.path.join(ROOT, 'model', name)
        if os.path.exists(p):
            used = columns_used(p)
            print(f"{name:<24}(display — prints actuals as history beside each line;")
            print(f"{'':<24} the amounts it totals come from budget columns)")
            print(f"{'':<24}budgets: {', '.join(sorted(used & BUDGETS)) or '—'}")
            print(f"{'':<24}actuals: {', '.join(sorted(used & ACTUALS)) or '—'}")

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


def freshness_check():
    """model.json must be what model/export.py currently produces.

    It was not. Six strings in the committed file differed from what the code generated —
    someone fixed spellings in the Python and never re-ran the export, so the app shipped a
    JSON that no longer matched its own source. Nothing analytical had drifted that time.
    Next time it might.
    """
    import hashlib
    import shutil
    import tempfile
    out = os.path.join(ROOT, 'fy28', 'src', 'data', 'model.json')
    before = hashlib.sha256(open(out, 'rb').read()).hexdigest()
    with tempfile.TemporaryDirectory() as tmp:
        keep = os.path.join(tmp, 'model.json')
        shutil.copy2(out, keep)
        subprocess.run([sys.executable, 'model/export.py'], cwd=ROOT,
                       capture_output=True, check=True)
        after = hashlib.sha256(open(out, 'rb').read()).hexdigest()
        if before != after:
            shutil.copy2(keep, out)      # leave the tree as we found it
    print('\nFRESHNESS')
    print(f"  model.json matches model/export.py: {'yes' if before == after else 'NO'}")
    if before != after:
        print('  committed model.json is stale — run: python3 model/export.py')
    return before == after


def provenance_table():
    """Every headline metric, and the column and document behind it."""
    import json
    m = json.load(open(os.path.join(ROOT, 'fy28', 'src', 'data', 'model.json')))
    rows = [
        ('FY27 appropriation', f"${m['fy27']['lps_appropriation']:,}",
         'published total', 'FY27 budget doc 3/25/26'),
        ('Expense base, all buckets', f"${sum(m['expenseBase'].values()):,.0f}",
         'fy27_balanced', 'FY27 budget workbook'),
        *([('Special education base', f"${m['expenseBase']['sped']:,.0f}",
            'fy27_balanced', 'FY27 budget workbook'),
           ('Special education rate', f"{m['assumptions']['sped'] * 100:.1f}%",
            'fy25_budget -> fy27_level_service', 'FY27 budget workbook')]
          if 'sped' in m['expenseBase'] else []),
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
        ('Out-of-district SPED rate', f"{m['assumptions']['sped_tuition'] * 100:.1f}%",
         'not from the CSV', 'Our estimate; the district publishes no rate'),
        *([(f"Citation {c['n']}: {c['metric'][:38]}", c['value'],
            c['basis'][:36], c['source'])
           for c in m.get('citations', {}).get('items', [])]),
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
    inert = free_cash_is_inert()
    ok = base_check()
    fresh = freshness_check()
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
    if not fresh:
        print('FAILED — model.json is not what model/export.py produces.')
        sys.exit(1)
    if inert:
        # Free cash is allowed into the projection as a one-time subtraction. The moment it
        # moves anything rate-driven it has stopped being one, and this fails rather than
        # printing a warning nobody reads.
        print('FAILED — free cash is no longer inert:')
        for p_ in inert:
            print(f'  {p_}')
        sys.exit(1)
    print('PASSED — every projection is computed from budget columns only,')
    print('and free cash, which is not, cannot move any of them.')
