#!/usr/bin/env python3
"""Every money parser in this repo, against every shape a negative arrives in.

    python3 scripts/check_money_parsers.py

WHY THIS EXISTS

`extract_budget_history.py` ate parenthesised negatives. FY2024 on the paraprofessional
line came out $315,772 wrong — TWICE the line, because a dropped sign does not zero a
figure, it reflects it. That line feeds the in-district special education escalator, which
is a projection assumption on the published site.

It was fixed twice. The first fix handled `(1,234)` and still missed `-$157,886`, because
the shapes are not one shape and a parser can be right about some of them.

WHAT THIS CHECKS, AND WHAT IT DELIBERATELY DOES NOT

It asserts each parser on the eight forms these documents actually print. It is a FIXTURE
check, not a data check — rule 13 warns that a fixture asserts what somebody wrote rather
than what is true, so this can only prove a parser handles a shape, never that the
documents hold no ninth shape.

The real defence is different and is worth stating so nobody mistakes this for it:
**an extractor that reconciles to a total the source itself prints cannot hide a material
sign error**, because a flipped sign moves the total by twice the value. Fourteen of the
eighteen extractors have such a tie. Three do not, and they are the exposure:

  extract_budget_history.py   feeds the model's sped escalators. Fixed; nothing would
                              catch a recurrence, so it is tested here.
  extract_grants.py           reads presentation decks that print no grand total. Its
                              regex cannot represent a negative at all, so it now REFUSES
                              on one rather than dropping the row.
  extract_lps_budget.py       reads numeric cells through openpyxl, which returns a signed
                              value regardless of display format. Not at risk; listed so
                              the absence is deliberate rather than an oversight.
"""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (printed form, what it means). Every one of these appears in the documents this project
# reads; `- 1,234` with a space is the OCR of a hyphen that picked up a gap.
SHAPES = [
    ('(1,234)',     -1234.0),
    ('(1,234.56)',  -1234.56),
    ('(34.00)',     -34.0),
    ('-$1,234',     -1234.0),
    ('-1,234.56',   -1234.56),
    ('-34.00',      -34.0),
    ('- 1,234',     -1234.0),
    ('$1,234.56',    1234.56),
    ('1,234',        1234.0),
]

PARSERS = [('extract_budget_history.py', 'money')]


def load(name):
    spec = importlib.util.spec_from_file_location(
        'm_' + name.replace('.', '_'), os.path.join(ROOT, 'scripts', name))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass                       # it ran its main(); we only want the function
    return mod


def main():
    bad = []
    for name, fn_name in PARSERS:
        mod = load(name)
        fn = getattr(mod, fn_name, None)
        if fn is None:
            bad.append(f'{name}: no function named {fn_name}() — it was renamed or '
                       'removed, and this check is now asserting nothing')
            continue
        for text, want in SHAPES:
            try:
                got = fn(text)
            except Exception as e:                       # noqa: BLE001
                bad.append(f'{name}:{fn_name}({text!r}) raised {type(e).__name__}: {e}')
                continue
            if got is None or abs(float(got) - want) > 0.005:
                bad.append(f'{name}:{fn_name}({text!r}) = {got!r}, want {want}')
        print(f'  ok    {name}:{fn_name}() — {len(SHAPES)} shapes')

    # extract_grants.py must REFUSE a negative rather than parse or skip it.
    g = load('extract_grants.py')
    neg = getattr(g, 'NEGATIVE_AMOUNT', None)
    if neg is None:
        bad.append('extract_grants.py: NEGATIVE_AMOUNT is gone — a negative grant line '
                   'would be dropped without trace again')
    else:
        for t in ('Positions Savings: $(31,000)', 'Some Grant  $-31,000',
                  'Reduce Something (35,000)'):
            if not neg.search(t):
                bad.append(f'extract_grants.py: NEGATIVE_AMOUNT does not catch {t!r}')
        if neg.search('Special Education, 240 Grant  $   418,237'):
            bad.append('extract_grants.py: NEGATIVE_AMOUNT fires on an ordinary positive '
                       'line — it would refuse every run')
        print('  ok    extract_grants.py — refuses a negative it cannot represent')

    print()
    if bad:
        print(f'FAILED — {len(bad)} problem(s):')
        for b in bad:
            print('  ' + b)
        return 1
    print('PASSED — every money parser handles every printed shape of a negative.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
