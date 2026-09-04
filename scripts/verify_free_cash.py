"""Recompute every figure in sources/analyses/free-cash.md from the source workbooks.

Rule 9, and the sharper version rule 13 adds: derive the value first, then require the
document to state it. A check that merely finds a sentence passes while the sentence is
wrong.

This one matters more than most because the document sits in the middle of a live
disagreement — whether Lunenburg is hoarding free cash or rebuilding it — and both sides
will read it looking for a number to quote.

    python3 scripts/verify_free_cash.py

Exit status is the number of failures.
"""
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, 'sources', 'analyses', 'free-cash.md')
FC = os.path.join(ROOT, 'sources', 'data', 'free-cash-proof.csv')
LEDGER = os.path.join(ROOT, 'sources', 'data', 'town-ledger-fy26-q3.csv')

TEXT = open(DOC).read().replace('−', '-').replace('$', '')
# For checking QUOTATIONS: markdown wraps lines and adds emphasis markers, so a verbatim
# quote from a source is never byte-identical in the document even when it is correct.
# Collapse whitespace and drop bold/italic markers, then compare.
# Blockquote markers survive whitespace collapsing and break a verbatim match in the
# middle of a wrapped quotation, which is exactly where quotations live. Strip them first.
FLAT = re.sub(r'\s+', ' ',
              re.sub(r'^>\s?', '', TEXT.replace('**', '').replace('*', ''), flags=re.M))
FAILS, CHECKS = [], 0

UNEX = 'Add Unencumbered/Unexpended Appropriations (CL#11)'
IDENT = 'Identified Free Cash July 1,'


def says(label, value, fmt=',.0f'):
    global CHECKS
    CHECKS += 1
    forms = [value] if isinstance(value, str) else [format(value, fmt)]
    if not isinstance(value, str) and fmt == ',.0f':
        forms.append(format(value, ',.2f'))
    if any(f in TEXT for f in forms):
        print(f'  ok    {label:<52} {forms[0]}')
    else:
        print(f'  FAIL  {label:<52} {forms[0]}  <- not in the document')
        FAILS.append(label)


rows = list(csv.DictReader(open(FC)))
cert = {(r['town'], int(r['year'])): float(r['amount']) for r in rows if r['role'] == 'certified'}
line = {}
for r in rows:
    line[(r['town'], int(r['year']), r['line'])] = float(r['amount'])
towns = sorted({r['town'] for r in rows})
years = sorted({int(r['year']) for r in rows})

print('1. the certified table')
for t in towns:
    for y in years:
        says(f'{t} {y}', cert[(t, y)])

print('\n2. the composition table')
for t in towns:
    for y in years:
        pct = line[(t, y, UNEX)] / line[(t, y, IDENT)] * 100 if line[(t, y, IDENT)] else 0
        says(f'{t} {y} unspent share', f'{pct:.0f}%')

print('\n3. Lunenburg 2025, the proof as printed in the document')
for k in [UNEX, 'Excess/Shortfall Local Receipts (CL#6)',
          'Add Prior Year Free Cash Not Appropriated (CL#12)',
          'Excess/Shortfall Cherry Sheet Receipts (CL#8)', 'Other Adjustments',
          'Add Actual Revenue Received but not Estimated (CL#7)',
          'Net Change in Adjustment to Free Cash',
          'Prior & Current Year Outstanding Receivables Total', IDENT]:
    says(k[:48], line[('Lunenburg', 2025, k)])

print('\n4. the ratio, and its denominator')
budget = sum(float(r['revised'] or 0) for r in csv.DictReader(open(LEDGER)))
says('FY26 general fund budget', budget)
says('departments in it', str(len(list(csv.DictReader(open(LEDGER))))))
ratio = cert[('Lunenburg', 2025)] / budget * 100
says('free cash as a share of that budget', f'{ratio:.2f}%')

print('\n5. the town’s own statement, quoted from its press release')
# The curated copy under sources/txt/ was a byte-identical duplicate of the town's
# own mirrored file and was deleted in the 4 September reorganisation. This is the
# publisher's copy, under the publisher's own filename, which rule 12 wants anyway.
PR = os.path.join(ROOT, 'sources', 'town-budget', 'text',
                  '4090-click-here-for-a-release-on-quot-understanding-lunenburg-'
                  'apos-s-fy27-budget-how-.txt')
pr = re.sub(r'\s+', ' ', open(PR, encoding='utf-8', errors='ignore').read())
for quote in ['5-7% of its annual budget',
              'certified a record $3.354 million in free cash',
              '6.65% of the operating budget',
              'been below DLS free cash recommendations for',
              'only meeting this recommendation in 2022, 2023, and 2026',
              'paraprofessional salaries were ultimately covered by newly identified grants']:
    CHECKS += 1
    q = re.sub(r'\s+', ' ', quote)
    inpr = q in pr
    intext = re.sub(r'\\s+', ' ', q.replace('$', '')) in FLAT
    if inpr and intext:
        print(f'  ok    quoted verbatim from the press release: {q[:52]}')
    else:
        print(f'  FAIL  {q[:52]}  in press release={inpr} in document={intext}')
        FAILS.append(f'quote: {q[:32]}')

print('\n5b. the denominators')
orig = sum(float(r['original'] or 0) for r in csv.DictReader(open(LEDGER)))
says('FY26 original appropriation', orig)
says('ratio on the original appropriation', f'{cert[("Lunenburg", 2025)] / orig * 100:.2f}%')
says("the denominator the town's 6.65% implies", cert[('Lunenburg', 2025)] / 0.0665)

print('\n5c. the year-label mapping, derived not assumed')
CHECKS += 1
top3 = sorted(sorted(years, key=lambda y: -cert[('Lunenburg', y)])[:3])
mapped = [y + 1 for y in top3]
if mapped == [2022, 2023, 2026]:
    print(f'  ok    three largest DLS years {top3} +1 = {mapped}, the town’s own three')
else:
    print(f'  FAIL  three largest {top3} +1 = {mapped}, town says [2022, 2023, 2026]')
    FAILS.append('year mapping')

print('\n6. the movements the prose claims')
CHECKS += 1
fall = (cert[('Lunenburg', 2023)] / cert[('Lunenburg', 2022)] - 1) * 100
if f'{abs(fall):.0f}%' in TEXT:
    print(f"  ok    {'Lunenburg 2022->2023 fall':<52} {fall:.0f}%")
else:
    print(f'  FAIL  Lunenburg fell {fall:.0f}% 2022->2023')
    FAILS.append('2022-23 fall')
for t, lo, hi in (('Shirley', 2021, 2025), ('Townsend', 2021, 2025)):
    ch = (cert[(t, hi)] / cert[(t, lo)] - 1) * 100
    says(f'{t} {lo}->{hi}', f'{ch:.0f}%')

CHECKS += 1
peak = max(years, key=lambda y: cert[('Lunenburg', y)])
if peak == 2025:
    print(f"  ok    {'Lunenburg 2025 is its highest of the five':<52} yes")
else:
    print(f'  FAIL  Lunenburg peaks in {peak}, not 2025')
    FAILS.append('peak year')

CHECKS += 1
lowest = min(towns, key=lambda t: line[(t, 2025, UNEX)] / line[(t, 2025, IDENT)])
if lowest == 'Uxbridge':
    print(f"  ok    {'Uxbridge has the lowest 2025 unspent share':<52} {lowest}")
else:
    print(f'  FAIL  the lowest 2025 unspent share is {lowest}, not Uxbridge')
    FAILS.append('uxbridge claim')

print('\n7. the reconciliations the document claims')
CHECKS += 1
n = len(towns) * len(years) + len(towns) * (len(years) - 1)
if str(n) in TEXT:
    print(f"  ok    {'number of reconciliations':<52} {n}")
else:
    print(f'  FAIL  {n} reconciliations, document says otherwise')
    FAILS.append('reconciliation count')

print(f'\n{CHECKS} checks, {len(FAILS)} failed')
for f in FAILS:
    print(f'  - {f}')
sys.exit(len(FAILS))
