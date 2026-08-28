"""Check every growth assumption against the district's own later budgets.

BUDGET TO BUDGET ONLY. This script used to compare an FY23 actual to an FY26 budget and
call the result growth. It is not. Budgets for some lines run 7% above what gets spent, so
that comparison measures escalation plus the step from spent to budgeted, and it put the
special education escalator 1.5 points too high.

The model projects appropriations. Every rate in it must therefore be derived from
appropriations. Actual spending is a different quantity and a different question, and it
lives in notes/BUDGET-VS-ACTUAL.md.

The comparison that IS valid is FY25 adopted -> FY26 final -> FY27 level service. Level
service is the district's own arithmetic for "the same services at next year's prices",
which is the definition of an escalator, so it is the right endpoint. It is only two
years, and that is stated rather than hidden.

Run after any change to the buckets or the rates.

Two things it deliberately does NOT do:

  * conclude. A three-year CAGR off a small base is not a trend. Utilities look like 17%
    a year until you see that electricity spiked once in FY23 and has been flat since,
    and maintenance looks like 27% until you see a one-time move to a contracted service.
    So it prints the year-by-year beside the rate and leaves the judgement to a person.
  * only look at buckets. The buckets are the thing that was wrong last time. It also
    ranks every function group in the budget by size and growth, because the next miss
    will be in a line nobody has bucketed yet.

    python3 scripts/backtest_rates.py
"""
import csv
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'model'))
from finance import DEFAULT_ASSUMPTIONS, expense_base, ESCALATOR_GROUPS  # noqa: E402
try:                       # only exists once special education has its own bucket
    from finance import is_sped  # noqa: E402
except ImportError:
    def is_sped(_row):
        return False

CSV = 'sources/data/lps-budget-lines.csv'
# Budgets only. Every column here is a number somebody voted or proposed, never a number
# somebody spent -- mixing the two is the bug this script exists to prevent.
YEARS = ['fy25_budget', 'fy26_final', 'fy27_level_service', 'fy27_balanced']
LABEL = {'fy25_budget': 'FY25 bud', 'fy26_final': 'FY26 bud',
         'fy27_level_service': 'FY27 LS', 'fy27_balanced': 'FY27 adopted'}
# FY25 adopted to FY27 level service, two years. The endpoint is level service rather than
# the adopted budget because adopted contains cuts, and a cut is a policy decision, not
# cost escalation.
TRAIL = ['fy25_budget', 'fy27_level_service']
TRAIL_YEARS = 2

FORBIDDEN = ('_actual', '_encumb')

# Material enough that being wrong about it moves the gap by real money.
BIG = 300_000
FAST = 0.08


def num(row, col):
    try:
        return float(row[col])
    except (TypeError, ValueError):
        return 0.0


def cagr(a, b, years):
    return (b / a) ** (1 / years) - 1 if a > 0 and b > 0 else None


def bucket_of(row):
    if is_sped(row):
        return 'sped'
    code = (row['function_group'] or '')[:4]
    if row['section'] == 'SALARIES' and code not in ESCALATOR_GROUPS:
        return 'salaries'
    return ESCALATOR_GROUPS.get(code, 'other')


def main():
    # Refuse to run at all if an actuals column has crept into the year list.
    bad = [c for c in YEARS + TRAIL if any(f in c for f in FORBIDDEN)]
    if bad:
        sys.exit(f'actuals column in a budget-only comparison: {bad}')

    rows = [r for r in csv.DictReader(open(CSV)) if r['kind'] == 'line'
            and 'TOTAL' not in (r['line_item'] or '').upper()]

    # ---- 1. every modeled bucket against its own history -------------------
    agg = defaultdict(lambda: defaultdict(float))
    for r in rows:
        k = bucket_of(r)
        for c in YEARS:
            agg[k][c] += num(r, c)

    print('ASSUMPTIONS vs WHAT THE LINE ACTUALLY DID')
    print(f"{'bucket':<14}{'assumed':>9}{'observed':>10}{'delta':>9}   " +
          ''.join(f'{LABEL[c]:>12}' for c in YEARS))
    print('-' * 96)
    flags = []
    for k in sorted(agg, key=lambda x: -agg[x]['fy27_balanced']):
        assumed = DEFAULT_ASSUMPTIONS.get(k)
        if assumed is None:
            continue
        v = agg[k]
        obs = cagr(v[TRAIL[0]], v[TRAIL[1]], TRAIL_YEARS)
        d = None if obs is None else obs - assumed
        mark = ''
        if d is not None and d > 0.02:
            mark = '  UNDER-MODELLED'
            flags.append((k, assumed, obs))
        elif d is not None and d < -0.02:
            mark = '  over-modeled'
            flags.append((k, assumed, obs))
        print(f'{k:<14}{assumed * 100:>8.1f}%'
              + (f'{obs * 100:>9.1f}%{d * 100:>8.1f}' if obs is not None else f"{'--':>9}{'--':>9}")
              + '   ' + ''.join(f'{v[c]:>12,.0f}' for c in YEARS) + mark)

    # ---- 2. every function group, bucketed or not ---------------------------
    print('\n\nEVERY FUNCTION GROUP, BY SIZE AND GROWTH')
    print('The next miss will be in a line nobody has bucketed. Anything big and fast is')
    print('listed; the year-by-year is there because a CAGR off a low base lies.\n')
    grp = defaultdict(lambda: defaultdict(float))
    for r in rows:
        grp[(r['function_group'] or 'ungrouped').strip()][YEARS[0]] += 0  # ensure key
        for c in YEARS:
            grp[(r['function_group'] or 'ungrouped').strip()][c] += num(r, c)

    cands = []
    for k, v in grp.items():
        if v['fy27_balanced'] < BIG:
            continue
        g = cagr(v[TRAIL[0]], v[TRAIL[1]], TRAIL_YEARS)
        if g is not None and g >= FAST:
            cands.append((g, k, v))
    cands.sort(reverse=True, key=lambda x: x[0])

    print(f"{'function group':<50}{'CAGR':>7}   " + ''.join(f'{LABEL[c]:>12}' for c in YEARS))
    print('-' * 118)
    for g, k, v in cands:
        print(f'{k[:48]:<50}{g * 100:>6.1f}%   ' + ''.join(f'{v[c]:>12,.0f}' for c in YEARS))

    # ---- 3. data quality ----------------------------------------------------
    # A line that goes to zero and reappears under a new name is a rename, not a cut, and
    # it produces a -100% growth rate that looks like a finding.
    print('\n\nLINES THAT MAY HAVE BEEN RENAMED OR RECLASSIFIED')
    print('Zero in one year with money either side. Not findings -- artefacts to ignore.\n')
    for r in rows:
        vals = [num(r, c) for c in YEARS]
        for i in range(1, len(vals) - 1):
            if vals[i] == 0 and vals[i - 1] > 1000 and vals[i + 1] > 1000:
                print(f"  {(r['function_group'] or '')[:34]:<36}{r['line_item'][:28]:<30}"
                      + ' '.join(f'{x:>10,.0f}' for x in vals))
                break

    print('\n')
    if flags:
        print('SUMMARY — assumptions more than two points from observed:')
        for k, a, o in flags:
            print(f'  {k:<14} assumed {a * 100:.1f}%  observed {o * 100:.1f}%')
    else:
        print('SUMMARY — every assumption within two points of observed.')
    print('\nJudgement still required. A rate can be right and the history wrong, if the')
    print('history contains a one-off. Read the year-by-year before changing anything.')


if __name__ == '__main__':
    main()
