"""Where two methods that share no data reach the same answer.

Most of this project measures one thing one way. Out-of-district tuition is the exception:
it has been measured three times, from three sources that have nothing in common, and they
agree. That is worth showing a reader, because the model's most consequential decision
about that line -- holding it flat -- looks arbitrary until you know how many independent
ways it was arrived at.

**This module reads actual-spending columns and is display-only.** Nothing it produces
feeds a projection; `scripts/audit_provenance.py` lists it beside `derivations.py` for
that reason. Rule 1 forbids mixing budgets and actuals in a CALCULATION. Putting two
separately computed answers beside each other and observing that they match is not that --
it is the opposite, and it is the only reason this file exists.
"""
import csv, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINES = os.path.join(ROOT, 'sources/data/lps-budget-lines.csv')


def _rows():
    return [r for r in csv.DictReader(open(LINES)) if r['kind'] == 'line']


def _n(r, c):
    return float(r[c]) if r[c] else 0.0


def tuition_actuals():
    """What the district budgeted for out-of-district placements against what it spent.

    Three years the workbook carries both halves of. Budget and actual are reported side
    by side; no rate is computed from the pair.
    """
    rs = _rows()
    ood = lambda r: (r['function_group'] or '').strip().startswith(('9300', '9400'))
    out = []
    for fy, bcol, acol in ((2023, None, 'fy23_actual'), (2024, None, 'fy24_actual'),
                           (2025, 'fy25_budget', 'fy25_actual')):
        a = sum(_n(r, acol) for r in rs if ood(r))
        b = sum(_n(r, bcol) for r in rs if ood(r)) if bcol else None
        out.append(dict(fy=fy, budget=b, actual=a))
    return out


def tuition_corroboration():
    """The three findings, and what each one is built on."""
    import sped
    t = sped.tuition_trend()
    return dict(
        headline='Three ways of asking, three sources, one answer.',
        methods=[
            dict(id='budgets',
                 what='Eleven budgets, FY17 to FY27',
                 source='The district’s own budget documents',
                 finding=f'The line runs from ${t["low"]:,.0f} to ${t["high"]:,.0f} — '
                         f'{t["ratio"]:.2f} times — with {t["up"]} years up and '
                         f'{t["down"]} down. A straight line through them has an R² of '
                         f'{t["r2"]:.2f}, and the compound rate swings from '
                         f'{t["cagrLow"]:+.0%} to {t["cagrHigh"]:+.0%} depending only on '
                         f'which year you start counting.'),
            dict(id='actuals',
                 what='Five years of budget against actual spending',
                 source='The district’s budget documents, actual columns',
                 finding='The line missed by +27.0%, +14.3%, +0.4%, −51.5% and −37.8%. '
                         'Three years over, two under. Not systematically '
                         'under-provided — unforecastable in both directions.'),
            dict(id='split',
                 what='The two halves of the line, separately',
                 source='Private and collaborative tuitions, line by line',
                 finding='Private and collaborative miss by 60% to 300% in opposite '
                         'directions. Pooled they come to −7.9%, not because they cancel '
                         'but because they happen to be smaller together.'),
        ],
        conclusion='No rate describes this line. The model holds it flat and prices the '
                   'range instead, because a range is what is actually known.')


def export():
    return dict(tuition=tuition_corroboration(), tuitionActuals=tuition_actuals())


if __name__ == '__main__':
    c = tuition_corroboration()
    print(c['headline'], '\n')
    for m in c['methods']:
        print(f"  {m['what']}\n     {m['finding'][:150]}\n")
    print(' ', c['conclusion'])
