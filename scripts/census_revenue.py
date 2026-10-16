#!/usr/bin/env python3
"""Where a school district's money comes from, by source, off the Census Bureau's FY2024 Annual
Survey of School System Finances -- Lunenburg's schools and Monty Tech, side by side.

    python3 scripts/census_revenue.py        # print both districts, every source, in dollars

WHY. TJ, 16 October 2026: people in town say *"monty tech makes most of its money by grants and
fundraising"* -- *"we need to show that, and compare lunenburg's grants and how they compare."*
The district's own budget summary cannot answer it: grants and gifts are outside the operating
budget it sets out. The Census table is the one document here that counts EVERY revenue source
for both districts the same way, so it is the like-for-like comparison.

WHAT IS ASSERTED. The documentation (state-census/census-school24doc.docx) states that TOTALREV
is TFEDREV + TSTREV + TLOCREV, and lists the items each of those sums. All four identities are
checked for both districts, so a source missed here cannot hide in a remainder.

WHAT "GRANTS" MEANS HERE, and whose choice it is: OURS. Every federal dollar to a school district
is a grant, so `federal` is the narrow measure. `state_programs` adds the state's categorical
and competitive money (career and technical, school meals, all other, nonspecified), which is
where a state award such as a Clean Energy Center grant lands; it leaves out Chapter 70,
transportation reimbursement and the benefits the state pays on a district's behalf, none of
which anybody applies for. `donations` is the survey's own item, U50, private contributions.
"""
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = 'state-census/census-elsec24.xlsx'
DOC_KEY = 'state-census/census-school24doc.docx'
PATH = os.path.join(ROOT, 'sources', KEY)
CACHE = os.path.join(ROOT, 'build', 'cache')
FY = 2024
IDS = {'2507080': 'lunenburg', '2508050': 'monty'}
VERSION = 1

# The documentation's own lists, in its order.
FEDERAL = ('C14 C15 C19 C22 C23 C26 C27 B11 C20 C25 C36 B10 B12 B14 B13').split()
STATE = ('C01 C04 C05 C06 C07 C08 C09 C10 C11 C12 C13 C24 C35 C38 C39').split()
LOCAL = ('T02 T06 T09 T15 T40 T99 D11 D23 A07 A08 A09 A11 A13 A15 A20 A40 '
         'U11 U22 U30 U50 U97').split()
STATE_PROGRAMS = ('C04', 'C05', 'C06', 'C07', 'C08', 'C09', 'C10', 'C13', 'C24', 'C35', 'C39')
TOWNS = ('T02', 'D23')   # a parent town's appropriation; a regional district's member towns


def fail(msg):
    raise SystemExit('census_revenue: ' + msg)


def _rows():
    if not os.path.exists(PATH):
        fail('%s is not here; run sync_archive.py --pull.' % KEY)
    sha = hashlib.sha256(open(PATH, 'rb').read()).hexdigest()
    cp = os.path.join(CACHE, 'census-revenue-v%d-%s.json' % (VERSION, sha[:16]))
    if os.path.exists(cp):
        return json.load(open(cp, encoding='utf-8'))
    import openpyxl
    ws = openpyxl.load_workbook(PATH, read_only=True).worksheets[0]
    want = ('NAME', 'YRDATA', 'TOTALREV', 'TFEDREV', 'TSTREV', 'TLOCREV') + tuple(FEDERAL + STATE + LOCAL)
    rows, head = {}, None
    for r in ws.iter_rows(values_only=True):
        if head is None:
            head = list(r)
            miss = [f for f in want if f not in head]
            if miss:
                fail('%s: no column %s' % (KEY, miss))
            continue
        x = dict(zip(head, r))
        if x['NCESID'] in IDS:
            rows[x['NCESID']] = {f: x[f] for f in want}
    os.makedirs(CACHE, exist_ok=True)
    with open(cp + '.tmp', 'w', encoding='utf-8') as fh:
        json.dump(rows, fh)
    os.replace(cp + '.tmp', cp)
    return rows


def revenue():
    """{'lunenburg': {...}, 'monty': {...}}, every figure in DOLLARS (the file's thousands times
    1,000), with the groupings the Monty Tech revenue page draws."""
    rows = _rows()
    out = {}
    for nid, who in IDS.items():
        x = rows.get(nid)
        if x is None or str(x['YRDATA']) != str(FY)[2:]:
            fail('%s: no FY%d row for NCES id %s' % (KEY, FY, nid))
        g = lambda items: sum(x[c] or 0 for c in items)
        for total, items in (('TFEDREV', FEDERAL), ('TSTREV', STATE), ('TLOCREV', LOCAL)):
            if x[total] != g(items):
                fail('%s %s: %s is %s, its items sum to %s' % (KEY, nid, total, x[total], g(items)))
        if x['TOTALREV'] != x['TFEDREV'] + x['TSTREV'] + x['TLOCREV']:
            fail('%s %s: TOTALREV is not federal + state + local' % (KEY, nid))
        k = lambda v: v * 1000
        d = dict(name=x['NAME'], nces=nid, fy=FY,
                 total=k(x['TOTALREV']), federal=k(x['TFEDREV']), state=k(x['TSTREV']),
                 local=k(x['TLOCREV']),
                 ch70=k(x['C01']), transport=k(x['C12']), on_behalf=k(x['C38']),
                 capital_aid=k(x['C11']),
                 state_programs=k(g(STATE_PROGRAMS)),
                 towns=k(g(TOWNS)), donations=k(x['U50']),
                 meals_federal=k(x['C25']))
        if d['ch70'] + d['transport'] + d['on_behalf'] + d['capital_aid'] + d['state_programs'] != d['state']:
            fail('%s %s: the state groupings do not add to TSTREV' % (KEY, nid))
        d['other_local'] = d['local'] - d['towns'] - d['donations']
        d['grants'] = d['federal'] + d['state_programs']
        d['grants_and_donations'] = d['grants'] + d['donations']
        d['state_and_towns'] = d['ch70'] + d['towns']
        d['state_rest'] = d['transport'] + d['on_behalf'] + d['capital_aid']
        parts = (d['federal'], d['state_programs'], d['donations'], d['ch70'], d['state_rest'],
                 d['towns'], d['other_local'])
        if sum(parts) != d['total']:
            fail('%s %s: the page\'s seven parts do not add to TOTALREV' % (KEY, nid))
        out[who] = d
    return out


if __name__ == '__main__':
    json.dump(revenue(), sys.stdout, indent=1)
    print()
