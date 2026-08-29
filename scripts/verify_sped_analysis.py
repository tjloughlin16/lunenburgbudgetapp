"""Recompute every figure in the special education analysis, and fail if one has drifted.

Rule 9: a figure in a finished document gets re-checked against the data by script, not
re-read. Prose drifts during editing and the version that ships is the one nobody checked
-- this file already shipped a risk table computed against a model that had since moved,
by as much as $200,245 on one row.

Everything here is recomputed from budget columns. The document's own numbers are the
expectations; where the two disagree the document is wrong, because the data is the thing
that gets regenerated and the prose is the thing that gets edited.

    python3 scripts/verify_sped_analysis.py
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'model'))
DOC = os.path.join(ROOT, 'sources/analyses/sped-and-the-curve.md')

import sped                                            # noqa: E402
from finance import project                            # noqa: E402

TEXT = open(DOC, encoding='utf-8').read()
# The same text with emphasis stripped, so `| **277** |` still matches `| 277 |`.
PLAIN = TEXT.replace('**', '')
FAILS = []


def present(label, needle):
    """The document must contain this string, bold markers aside.

    Figures get emphasised during editing -- `| 277 |` becomes `| **277** |` -- and a
    checker that cannot see through that reports drift where there is none, which is
    worse than not checking, because it trains somebody to ignore the output.
    """
    ok = needle in TEXT or needle in PLAIN
    if not ok:
        FAILS.append(f'{label}: "{needle}" not found in the document')
    print(f"  {'OK  ' if ok else 'GONE'}  {label:<46} {needle}")


def money(v):
    return f'${v:,.0f}'


def pct(v, d=2):
    return f'{v*100:.{d}f}%'


print('Recomputing every figure in sped-and-the-curve.md\n')

y = sped.level_service_year()
print('The level-service year')
present('FY26 budget', money(y['fy26']))
present('FY27 level service', money(y['fy27']))
present('published rate', pct(y['published']))
present('underlying rate', pct(y['underlying']))
present('points bent down', f"{y['bend']*100:.2f}")
present('tuition FY26', money(y['tuition_fy26']))
present('tuition FY27', money(y['tuition_fy27']))
present('tuition change', money(-y['tuition_change']))

# The short version is the first thing anybody reads and the last thing anybody
# re-checks, so its figures are verified like the rest.
print('The short version')
present('published rate', pct(y['published']))
present('underlying rate', pct(y['underlying']))
present('rate in use', f"{sped.RATE:.2%}")
present('paras, compound', f"{sped.PARA_TREND['cagr']:.2%}")
present('teachers, compound', f"{sped.TEACHER_TREND['cagr']:.2%}")

print('\nWhat counts as special education')
c = sped.classified()
present('lines counted', f"{len(c['counted'])} lines")
present('classification total', money(c['total']))
present('groups taken whole', f"**{len(c['groups'])} function groups")
present('lines caught by name', f"{c['byName']} lines")
# By name, not by position: the excluded list grows, and an index silently starts
# checking a different row rather than failing.
_ge = next(e for e in c['excluded'] if e['group'].startswith('2330'))
present('general-ed paras, FY25', money(_ge['fy25']))
_ell = next(e for e in c['excluded'] if e['group'].startswith('English Language'))
present('ELL removed from the line', money(_ell['amount']))
if abs(c['total'] - sped.total(sped.FY27BAL, sped.is_sped)) > 1:
    FAILS.append('the classified lines do not sum to the projection base')

print('\nThe decomposition')
for part in sped.decomposition():
    if part['id'] in ('paras',):
        present(part['label'], money(part['fy27'] - part['fy26']))

print('\nThe rate and its range')
present('whole line, two budgets', pct(sped.WHOLE_LINE_RATE))
present('line apart from the paras', pct(sped.EX_PARAS_RATE))
present('paraprofessional step', money(sped.PARA_FY27_CHANGE))
present('para share of the year', f'{sped.PARA_SHARE_OF_RISE*100:.0f}%')

print('\nThe tuition risk table, priced against the live model')
for r in sped.tuition_risk():
    present(f"gap at {money(r['tuition'])}", money(r['gap']))
    if r['delta']:
        present(f"delta at {money(r['tuition'])}", money(r['delta']))

print('\nThe student series')
st = sped.students()
for d in st:
    present(f'FY{d["fy"]} count', f"| {d['n']} ")
present('series length', f'All {len(st)} years')

print('\nParaprofessionals, ten budgets — step or climb')
P = sped.PARA_TREND
present('first / last', f"${P['first']:,.0f} \u2192 ${P['last']:,.0f}")
present('ratio', f"{P['ratio']:.2f}")
present('compound rate', f"{P['cagr']*100:+.2f}%")
present('R-squared', f"R\u00b2 = {P['r2']:.2f}")
present('years up/down', f"{P['up']} / {P['down']}")
present('rate in use', f"{sped.RATE:.2%}")

TR = sped.TRANSPORT_TREND
print('\nSpecial education transport, nine budgets')
present('compound rate', f"{TR['cagr']*100:+.2f}%")
present('R-squared', f"R\u00b2 = {TR['r2']:.2f}")

print('\nSpecial education teachers, eight budgets')
TE = sped.TEACHER_TREND
present('compound rate', f"{TE['cagr']*100:+.2f}%")
present('R-squared', f"R\u00b2 = {TE['r2']:.2f}")
present('below contract', f"{sped.LEA_RATE*100:.1f}%")

print('\nOut-of-district tuition, eleven budgets')
T = sped.tuition_trend()
h = sped.tuition_history()
present('budget count', f"{T['n']}, FY{h[0]['fy'] % 100} to FY{h[-1]['fy'] % 100}")
present('low', money(T['low']))
present('high', money(T['high']))
present('ratio', f"{T['ratio']:.2f}")
present('average', money(T['mean']))
present('R-squared', f"R² = {T['r2']:.2f}")
present('biggest fall', f"{-T['biggestFall'][0]*100:.1f}% in FY{T['biggestFall'][1] % 100}")
present('biggest rise', f"{T['biggestRise'][0]*100:.0f}% in FY{T['biggestRise'][1] % 100}")
for d in h:
    present(f'FY{d["fy"]} budgeted', money(d['total']))

print('\nFigures the document must NOT still contain')
RETIRED = ['$613,238', '$857,084', '$1,021,908', '$1,148,377',
           'there is no second 46%']
for r in RETIRED:
    # 2.48% survives inside the correction note, which explains why it is retired; what
    # must not survive is the sentence that used it as the model's floor.
    hits = TEXT.count(r)
    limit = 0 if r.startswith('$') else 1
    ok = hits <= limit
    if not ok:
        FAILS.append(f'retired figure still present {hits}x: {r}')
    print(f"  {'OK  ' if ok else 'STALE'}  retired {r:<44} {hits} occurrence(s)")

print()
if FAILS:
    print(f'FAILED — {len(FAILS)} figure(s) in the document do not match the data:')
    for f in FAILS:
        print('   -', f)
    sys.exit(1)
print('PASSED — every figure in the analysis matches what the model computes.')
