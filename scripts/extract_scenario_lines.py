#!/usr/bin/env python3
"""EVERY LINE THE SCENARIOS DIFFER ON -- the full cut list, from the documents that carry it.

    python3 scripts/extract_scenario_lines.py            # write sources/data/budget-seasons/fy27-lines.csv
    python3 scripts/extract_scenario_lines.py --check    # ...and fail if it no longer reproduces

TJ, 14 September 2026: "this needs to handle LOTS of cuts. $600k worth of cuts is a lot. You
can review those on the town's budget page for the full list." Two documents carry it, line
by line, with one column per scenario:

  * the district's FY27 PROPOSED BUDGET of 23 March 2026 -- FY26 final, then Restoration,
    Core, Level Service, Balanced -- 409 lines, footed to TOTAL ACTUALS & BUDGET;
  * the town's FY 2027 OPERATING BUDGETS (Balanced, Tier 1, Tier 2) -- FY24 expended, FY25
    budgeted, FY25 actual, FY26 budgeted, then Balanced, Tier 1, Tier 2 -- footed to Total
    Omnibus.

A CUT is a line where the balanced budget is below level service (school) -- that is what
the no-override budget removed. What an override tier would have RESTORED is a line where
the tier is above balanced. Both are read off the columns; nothing is inferred. Every
figure ties to the document's own printed total (rule 13), and the file refuses to write
if it does not.

`category` is the nearest heading ABOVE the line in the text layer, and the PDF's text order
puts some salary lines before their heading, so a salary line can carry the previous
section's code. The line label and the figures are exact; the category is a hint.

Positions are not in these tables by name -- a salary line is a salary line -- so the FTE
behind a cut comes from the district's Balanced Budget slides of the same date and is
recorded by hand in fy27.csv against the line it belongs to.
"""
import argparse
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'sources', 'data', 'budget-seasons', 'fy27-lines.csv')
SCHOOL = os.path.join(ROOT, 'sources', 'district-budget', 'text', 'fy27-budget-projections-as-of-3-23-26.txt')
TOWN = os.path.join(ROOT, 'sources', 'town-budget', 'text', '3769-fy-2027-operating-budgets-balanced-tier-1-tier2.txt')
# A money token: '$1,234.56', '($1,234)', a bare '237207.96' or '22,700,360.21$' (the town's sheet
# has both), 'n/a' for a moved line, and a lone dash for the district's zero.
MONEY = re.compile(r'\(?\$-?[\d,]+(?:\.\d+)?\)?|(?<![\w$])\d{1,3}(?:,\d{3})*(?:\.\d+)?\$?(?![\w$])|(?<![\w$])\d{4,}\.\d+(?![\w$])|\bn/a\b|(?<=\s)-(?=\s|$)')
COLS = ['side', 'document', 'category', 'line', 'level_service', 'balanced', 'tier1_core', 'tier2_restoration',
        'cut', 'tier1_restores', 'tier2_restores']


def num(tok):
    if tok == 'n/a':
        return None
    if tok == '-':
        return 0.0
    neg = tok.startswith('(')
    v = float(tok.strip('()$ ').replace(',', ''))
    return -v if neg else v


def parse(path, ncols, take, short_ok=False):
    """Lines that end in `ncols` money tokens: the label is what precedes them. `take` maps
    column positions to the four scenario columns we keep."""
    rows, category = [], ''
    for raw in open(path, encoding='utf-8'):
        line = raw.strip()
        if not line or line.startswith('==='):
            continue
        m = re.match(r'^(\d{4})\s*-\s*(.+)$', line)
        if m and '$' not in line:
            category = line               # '2305 - E.S. Teachers -General Education': a heading, whatever dashes it holds
            continue
        found = list(MONEY.finditer(line))
        toks = [x.group(0) for x in found]
        starts = [x.start() for x in found]
        if len(toks) == ncols - 1 and short_ok == 'lead':
            toks = [None] + toks          # the first (prior-year) column left blank: 'E.S. Music $500 $500 $500 $500'
            starts = [starts[0]] + starts
        elif len(toks) == ncols - 1 and short_ok == 'actual':
            toks = toks[:2] + [None] + toks[2:]   # the town's FY25-actual column left blank ('APDC Expenses'); the tiers foot
            starts = starts[:2] + [starts[2]] + starts[2:]
        if len(toks) < ncols:
            continue
        toks, starts = toks[-ncols:], starts[-ncols:]
        label = line[:starts[0]].strip().rstrip(':').strip()   # the label is what precedes the LAST ncols tokens
        if not label or re.match(r'^(total|subtotal|grand)', label, re.I):
            continue
        vals = [num(t) if t is not None else None for t in toks]
        rows.append(dict(category=category, line=label, **{k: vals[i] for k, i in take.items()}))
    return rows


def total_of(path, label_rx, ncols):
    for raw in open(path, encoding='utf-8'):
        if re.match(label_rx, raw.strip(), re.I):
            toks = MONEY.findall(raw)[-ncols:]
            return [num(t) for t in toks]
    raise SystemExit('no printed total matching %s in %s' % (label_rx, path))


def build():
    out = []
    # SCHOOL: FY26, Restoration, Core, Level Service, Balanced
    school = parse(SCHOOL, 5, dict(tier2_restoration=1, tier1_core=2, level_service=3, balanced=4), short_ok='lead')
    tot = total_of(SCHOOL, r'^TOTAL ACTUALS & BUDGET', 5)
    sums = [sum((r[k] or 0) for r in school) for k in ('tier2_restoration', 'tier1_core', 'level_service', 'balanced')]
    for got, want, name in zip(sums, tot[1:], ('restoration', 'core', 'level service', 'balanced')):
        if abs(got - want) > 2:                  # the document's own rounding
            raise SystemExit('school %s column sums to %.0f, the document prints %.0f' % (name, got, want))
    for r in school:
        out.append(dict(side='school', document='sources/district-budget/docs/fy27-budget-projections-as-of-3-23-26.pdf', **r))
    # TOWN: FY24 exp, FY25 bud, FY25 act, FY26 bud, Balanced, Tier 1, Tier 2 -- lines with n/a are moved lines
    town = [r for r in parse(TOWN, 7, dict(balanced=4, tier1_core=5, tier2_restoration=6), short_ok='actual') if r['balanced'] is not None]
    tot = total_of(TOWN, r'^Total Omnibus', 7)
    sums = [sum((r[k] or 0) for r in town) for k in ('balanced', 'tier1_core', 'tier2_restoration')]
    for got, want, name in zip(sums, tot[4:], ('balanced', 'tier 1', 'tier 2')):
        if abs(got - want) > 2:
            raise SystemExit('town %s column sums to %.2f, the document prints %.2f' % (name, got, want))
    for r in town:
        out.append(dict(side='town', document='sources/town-budget/docs/3769-fy-2027-operating-budgets-balanced-tier-1-tier2.pdf', level_service=None, **r))
    for r in out:
        b = r['balanced'] or 0
        r['cut'] = round((r['level_service'] or 0) - b, 2) if r['level_service'] is not None and (r['level_service'] or 0) > b else 0
        r['tier1_restores'] = round((r['tier1_core'] or 0) - b, 2) if (r['tier1_core'] or 0) > b else 0
        r['tier2_restores'] = round((r['tier2_restoration'] or 0) - b, 2) if (r['tier2_restoration'] or 0) > b else 0
    return [r for r in out if r['cut'] or r['tier1_restores'] or r['tier2_restores']]


def render(rows):
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow({k: ('' if r.get(k) is None else (('%.2f' % r[k]).rstrip('0').rstrip('.') if isinstance(r.get(k), float) else r[k])) for k in COLS})
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows = build()
    text = render(rows)
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        print('ok — %s reproduces (%d lines)' % (os.path.relpath(OUT, ROOT), len(rows)) if have == text else 'STALE ' + OUT)
        return 0 if have == text else 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(text)
    sch = [r for r in rows if r['side'] == 'school']; twn = [r for r in rows if r['side'] == 'town']
    print('%s: %d lines the scenarios differ on' % (os.path.relpath(OUT, ROOT), len(rows)))
    print('  school: %d lines cut below level service, $%s; tier 1 restores $%s on %d lines; tier 2 $%s on %d'
          % (sum(1 for r in sch if r['cut']), format(round(sum(r['cut'] for r in sch)), ','),
             format(round(sum(r['tier1_restores'] for r in sch)), ','), sum(1 for r in sch if r['tier1_restores']),
             format(round(sum(r['tier2_restores'] for r in sch)), ','), sum(1 for r in sch if r['tier2_restores'])))
    print('  town:   tier 1 restores $%s on %d lines; tier 2 $%s on %d'
          % (format(round(sum(r['tier1_restores'] for r in twn)), ','), sum(1 for r in twn if r['tier1_restores']),
             format(round(sum(r['tier2_restores'] for r in twn)), ','), sum(1 for r in twn if r['tier2_restores'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
