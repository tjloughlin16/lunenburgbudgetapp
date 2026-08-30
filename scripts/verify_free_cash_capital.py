#!/usr/bin/env python3
"""Every figure in the capital section of `analyses/free-cash.md`, recomputed.

Rule 9: a finished document is re-checked against the data by script, not re-read. Rule 13:
the check asserts the NUMBER derived from the data, not that a sentence is present -- an
earlier verifier in this project passed on a false claim because it only looked for prose.

Each figure below is computed from `model/freecash.py` and the extracts under it, then
required to appear in the document. If the model moves and the prose does not, this fails.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'model'))
import freecash as fc  # noqa: E402

DOC = os.path.join(ROOT, 'sources', 'analyses', 'free-cash.md')
WANTED = os.path.join(ROOT, 'notes', 'DATA-WANTED.md')

cap = fc.capital_consequence()
if cap is None:
    sys.exit('capital-plan-fy27.csv is missing; nothing to verify')

# Whitespace-normalised: a figure split across a line wrap is still stated.
text = re.sub(r'\s+', ' ', open(DOC).read())
wanted = re.sub(r'\s+', ' ', open(WANTED).read())
fails = []


def money(n):
    return f'${n:,.0f}'


def require(where, name, value, doc):
    if value not in doc:
        fails.append(f'{where}: {name} = {value} does not appear')


# --- the funding table, straight off the plan's own history ---------------------------
hist = {h['fy']: h for h in cap['history']}
for fy in (2024, 2025, 2026):
    require('free-cash.md', f'FY{fy} free cash into capital',
            money(hist[fy]['freeCash']), text)
    require('free-cash.md', f'FY{fy} capital plan total', money(hist[fy]['total']), text)

require('free-cash.md', 'ten-year average free cash', money(cap['averageFromFreeCash']), text)
require('free-cash.md', 'ten-year average programme',
        money(round(sum(h['total'] for h in cap['history']) / len(cap['history']))), text)
require('free-cash.md', 'FY27 planned from free cash', money(cap['plannedFromFreeCash']), text)
require('free-cash.md', 'FY27 programme total', money(cap['programmeTotal']), text)
require('free-cash.md', 'the unfunded queue', money(cap['queueValue']), text)

# --- the claims the section is built on -----------------------------------------------
ceiling = cap['redirectCeiling']
if ceiling != round(fc.spendable(fc.BAND_LOW)):
    fails.append(f'redirect ceiling {ceiling} is not the draw to the band floor')

years = cap['yearsRedirectExceedsFreeCash']
recomputed = sum(1 for h in cap['history'] if ceiling > h['freeCash'])
if years != recomputed:
    fails.append(f'yearsRedirectExceedsFreeCash says {years}, the history gives {recomputed}')

# The sentence claims "seven of those ten years" and "1.21x what it gave last year". Both
# are derived here rather than trusted, and the spelled-out word is checked as a word.
SPELLED = {7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten'}
if f'{SPELLED.get(years, years)} of those {SPELLED.get(cap["yearsCovered"])} years' not in text:
    fails.append(f'free-cash.md: the count of years is not stated as '
                 f'"{SPELLED.get(years, years)} of those {SPELLED.get(cap["yearsCovered"])} years"')

last = cap['lastYear']
mult = round(ceiling / last['freeCash'], 2)
if f'{mult:.2f}× what it gave last year' not in text:
    fails.append(f'free-cash.md: the multiple against FY{last["fy"]} is not stated as {mult:.2f}x')

# --- the two readings of what stops, at the three draws the table prints ---------------
def at(redirect):
    return min(cap['atDraw'], key=lambda d: abs(d['redirect'] - redirect))


for row_redirect in (300_000, 500_000, ceiling):
    d = at(row_redirect)
    if d['strictLost'] < d['resequencedLost']:
        fails.append(f'at {row_redirect}: the rigid reading loses less than the re-sequenced '
                     f'one, which cannot happen')
    if d['resequencedLost'] < d['lost']:
        fails.append(f'at {row_redirect}: re-sequenced loss is below the dollars removed')

# The three-row table in the document. Redirect amounts there are round numbers chosen for
# reading; recompute both readings AT THOSE AMOUNTS rather than at the model's own stops.
import csv as _csv
rows = list(_csv.DictReader(open(os.path.join(ROOT, 'sources', 'data',
                                              'capital-plan-fy27.csv'))))
# Only the convertible programme. Stabilization money is restricted to vehicles and
# equipment, so a free cash redirect cannot strand what it pays for -- the model excludes
# it, and this check has to exclude it the same way or it is testing a different model.
funded = sorted([(int(r['rank']), float(r['cost'])) for r in rows
                 if r.get('funded', 'yes') == 'yes'
                 and r.get('funding') != 'stabilization'], key=lambda x: -x[0])
costs = [c for _, c in funded]


def strict(R):
    lost = 0.0
    for _, c in funded:
        if lost >= R:
            break
        lost += c
    return round(lost)


def closest(R):
    import itertools
    best = None
    for k in range(1, len(costs) + 1):
        for combo in itertools.combinations(costs, k):
            s = sum(combo)
            if s >= R and (best is None or s < best):
                best = s
    return round(best)


for R in (300_000, 500_000, ceiling):
    require('free-cash.md', f'rigid reading at {R}', money(strict(R)), text)
    require('free-cash.md', f're-sequenced reading at {R}', money(closest(R)), text)

# The overshoot the document quotes, at the draw it quotes it for.
over = (strict(300_000) - 300_000) / 300_000 * 100
if f'{over:.0f}%' not in text:
    fails.append(f'free-cash.md: the overshoot at $300,000 is {over:.0f}%, not as stated')

# --- the funding split, which decides what a draw can strand at all -------------------
require('free-cash.md', 'restricted stabilization money', money(cap['restrictedTotal']), text)
require('free-cash.md', 'convertible programme', money(cap['convertibleTotal']), text)
require('free-cash.md', 'raise and appropriate', money(cap['plannedFromTaxation']), text)
for i in cap['restrictedItems']:
    require('free-cash.md', f'restricted project rank {i["rank"]}', money(i['cost']), text)
if cap['restrictedTotal'] + cap['convertibleTotal'] != cap['programmeTotal']:
    fails.append('the funding split does not sum to the programme')
if cap['convertibleTotal'] != cap['plannedFromFreeCash'] + cap['plannedFromTaxation']:
    fails.append('the convertible programme is not free cash plus taxation')
# Nothing restricted may appear in what any draw strands.
restricted_ranks = {i['rank'] for i in cap['restrictedItems']}
for d in cap['atDraw']:
    hit = restricted_ranks & {p['rank'] for p in d['projects']}
    if hit:
        fails.append(f'draw of {d["redirect"]} strands restricted project(s) {sorted(hit)}')

# --- DATA-WANTED 3e rests on the same figures -----------------------------------------
require('DATA-WANTED.md', 'the unfunded queue', money(cap['queueValue']), wanted)
require('DATA-WANTED.md', 'FY27 programme total', money(cap['programmeTotal']), wanted)
require('DATA-WANTED.md', 'FY27 planned from free cash', money(cap['plannedFromFreeCash']),
        wanted)
require('DATA-WANTED.md', 'ten-year average free cash', money(cap['averageFromFreeCash']),
        wanted)
require('DATA-WANTED.md', 'rigid reading at 500,000', money(strict(500_000)), wanted)

if fails:
    print('FAIL')
    for f in fails:
        print('  -', f)
    sys.exit(1)
print(f'ok — {len(cap["history"])} years of capital funding, both printed averages tie, '
       f'and every figure in the capital section of free-cash.md recomputes')
