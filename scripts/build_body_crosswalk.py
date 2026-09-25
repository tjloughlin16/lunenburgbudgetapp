#!/usr/bin/env python3
"""ONE BODY, TWO PAGES: the org chart and the money, joined by name.

    python3 scripts/build_body_crosswalk.py [--check]

Writes `sources/data/body-crosswalk.csv` -- one row per body this project holds a chart
for, with the address of its money page and the address of its chart.

TJ, 25 September 2026: *"i would like to cross link the org chart and the personell pages
for each department, so we can see the trends over time when needed, or directly se the
people when needed."*

The two halves existed and had nothing between them. `/org-charts?unit=Fire%20Department`
knows who held which post in which year; `/departments/fire` knows what that department is
voted, holds and raises. A reader on either one had to know the other existed and type its
address.

THE CROSSWALK IS A DATASET, NOT A LOOKUP IN A PAGE. Both payload generators need it --
`build_org_charts.py` to send a reader to the money, `build_finance.py` to send one to the
people -- and a map written twice is the defect CLAUDE.md names sixth: three copies of one
constant, one of them gaining a key the others did not, and a page refusing to build. So it
is computed once, written down, and read by both.

THE JOIN IS ON A NAME, WHICH IS THE WEAKEST KIND, so it is measured rather than trusted.
Names differ across the two sides by case, by `Of` against `of`, by a `(board)` or `(staff)`
suffix this project added to split a body that is both, and by the word `Department` being
present on one side and not the other. Normalising for exactly those raises the match from
21 of 63 to what the run prints -- and `--check` FAILS IF THE COUNT FALLS, because a join
that silently matches less is indistinguishable from a body that stopped existing.

WHAT IS DELIBERATELY NOT MATCHED. A body with no money page is not a defect:

- **The regional district and the town's representatives to it.** Monty Tech is another
  district's chart; Lunenburg votes it an assessment and does not run it.
- **`Officers in no department`.** A holding unit for appointed posts, not a body.
- **Committees the town votes nothing to.** Most advisory committees have no account, so
  there is no money page to reach. They keep their chart and their row says why.

Rather than leaving those blank, each carries a `why`, so a body with no link reads as a
body with nothing on the other side rather than as a join that failed.
"""
import argparse
import collections
import csv
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT = os.path.join(DATA, 'body-crosswalk.csv')

FIELDS = ['unit', 'unit_kind', 'first_fy', 'last_fy', 'years', 'people_last_fy',
          'chart_url', 'money_slug', 'money_url', 'money_kind', 'board_slug',
          'board_url', 'basis', 'why']

# THE FEWEST MATCHES THIS MAY MAKE. A ratchet, in the sense `build_reading_time.py` uses
# one: it is not the right number, it is the number reached once, and a change that lowers
# it has to say so out loud. Raise it when a real match is added; never lower it to make a
# run pass.
#
# AND IT WAS MEASURED, NOT CHOSEN. The first draft of this file said 40 before anything had
# been counted, and the run made 27 -- a floor invented at a desk, which is the same defect
# as the weekly sweep being exact about a reset time nobody had checked. Then 36, with the
# map below written but not yet run: 34. This is the third number and the first measured one.
MATCHES_FLOOR = 34

# THE BODIES THE TWO SIDES CALL DIFFERENT THINGS. Ours, not either publisher's -- so each
# one is a decision and is listed rather than absorbed into `norm()`, where it would look
# like spelling. Every pair was read off the two lists side by side.
#
# `Accounting Department` against `Town Accountant` is the shape of all of them: the chart
# names the office and the finance registry names the officer who owns the account. Neither
# is wrong and no normalisation reaches from one to the other.
SAME_BODY = {
    'accounting': 'accounting',                          # Town Accountant
    'building': 'building-inspection',                   # Building Department
    'public library': 'library-board-of-trustees',       # the Library's accounts sit with its trustees
    'library trustees': 'library-board-of-trustees',
    'tax collector treasurer tax custodian': 'treasurer-collector',
    'public schools': 'school-committee',                # the district's money is the committee's
    'veterans services': 'veterans-services',
    'facilities grounds recreation': 'facilities',       # Facilities and Grounds
    'radio watch': 'dispatch',
    'public works': 'dpw',
}

# WHY A BODY HAS NO MONEY PAGE. Matched on the NORMALISED name, so a body renamed in the
# chart keeps its explanation. Anything not here and not matched is reported as a MISS and
# is a question rather than a decision.
NO_MONEY = [
    (re.compile(r'montachusett|monty'),
     'another district’s body. Lunenburg votes it an assessment and does not run it '
     '— /analysis/monty-tech is where that money is.'),
    (re.compile(r'^officers in no'),
     'not a body. A holding unit for appointed posts that sit under no department, so the '
     'chart can draw them at all.'),
    (re.compile(r'housing authority'),
     'a separate public authority with its own budget, not a town department.'),
]


def norm(name):
    """A body's name, reduced to what the two sides agree about.

    Each substitution here is a difference that was actually observed between the chart's
    names and the finance registry's, and nothing else is removed. `department` goes because
    one side writes `Building Department` and the other `Building Inspection`... which it
    does NOT fix, and that is the point of printing the misses: this normalises spelling,
    never meaning.
    """
    s = (name or '').lower()
    s = re.sub(r'\s*\((board|staff|schools|appointed post)\)\s*$', '', s)
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    s = re.sub(r'\b(the|of|and|a)\b', ' ', s)
    s = re.sub(r'\bdepartments?\b', ' ', s)
    s = re.sub(r'\btown\b', ' ', s)
    s = re.sub(r'\blunenburg\b', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def load(name):
    p = os.path.join(PUB, name)
    if not os.path.exists(p):
        raise SystemExit('no %s -- run its generator first' % name)
    return json.load(open(p, encoding='utf-8'))


def build():
    charts = load('org-charts.json')
    fin = load('finance.json')
    boards = load('boards.json')

    owners = {}
    for slug, o in fin.get('owners', {}).items():
        owners.setdefault(norm(o.get('name', '')), (slug, o.get('kind', '')))
    board_slugs = {}
    for b in boards.get('boards', []):
        board_slugs.setdefault(norm(b.get('name', '')), b.get('slug', ''))

    # THE YEAR-BY-YEAR HEADCOUNT, WHICH IS THE `trends over time` HALF OF THE REQUEST.
    # Counted off the chart's own rows rather than from a staffing dataset, because it has
    # to be the SAME quantity the chart draws -- a reader clicking from one to the other
    # must not meet two different numbers for one body and one year. It counts NAMED
    # people: a vacancy the town prints is a post, not a person (`status`).
    per = collections.defaultdict(lambda: collections.defaultdict(set))
    for r in charts.get('rows', []):
        if r.get('status') != 'filled' or not (r.get('person') or '').strip():
            continue
        per[r['unit']][r['fy']].add(r['person'].strip().lower())

    rows, matched, missed = [], 0, []
    for u in sorted(charts.get('units', []), key=lambda x: x['unit']):
        unit, kind = u['unit'], u.get('kind', '')
        years = sorted(per[unit])
        key = norm(unit)
        slug, money_kind = owners.get(key, ('', ''))
        if not slug and key in SAME_BODY:
            slug = SAME_BODY[key]
            money_kind = fin['owners'].get(slug, {}).get('kind', '')
        bslug = board_slugs.get(key, '')
        why = ''
        if slug:
            matched += 1
            same = fin['owners'].get(slug, {}).get('name', '').lower()
            basis = ('the same name on both sides' if unit.lower() == same
                     else 'ours: the chart names the office, the registry names the officer'
                     if key in SAME_BODY else 'the same name, normalised')
        else:
            basis = ''
            why = next((w for pat, w in NO_MONEY if pat.search(key)), '')
            if not why:
                missed.append((unit, kind, key))
                why = ('no account in the finance registry names this body, so there is no '
                       'money page to reach. It may be a body the town votes nothing to, '
                       'or a name the two sides spell differently — unresolved.')
        rows.append(dict(
            unit=unit, unit_kind=kind,
            first_fy=years[0] if years else '', last_fy=years[-1] if years else '',
            years=len(years),
            people_last_fy=len(per[unit][years[-1]]) if years else 0,
            chart_url='/org-charts?unit=%s' % unit.replace(' ', '%20'),
            money_slug=slug,
            money_url=(('/departments/%s' % slug) if money_kind == 'department'
                       else ('/boards/%s/finance' % slug) if slug else ''),
            money_kind=money_kind,
            board_slug=bslug, board_url=('/boards/%s' % bslug) if bslug else '',
            basis=basis, why=why))
    return rows, matched, missed


def write(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, '') for k in FIELDS})
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows, matched, missed = build()
    text = write(rows)
    bad = []
    if matched < MATCHES_FLOOR:
        bad.append('the name join matched %d bodies to a money page and the floor is %d. '
                   'A join that matches less looks exactly like a body that stopped '
                   'existing -- find out which before lowering the floor.'
                   % (matched, MATCHES_FLOOR))
    print('%d bodies; %d joined to a money page, %d to a board page, %d unresolved'
          % (len(rows), matched, sum(1 for r in rows if r['board_slug']), len(missed)))
    for unit, kind, key in missed:
        print('  ?? no money page for %-46s (%s) normalised %r' % (unit[:46], kind, key))
    if a.check:
        if not os.path.exists(OUT):
            bad.append('%s does not exist' % os.path.relpath(OUT, ROOT))
        elif open(OUT, encoding='utf-8', newline='').read() != text:
            bad.append('%s is stale' % os.path.relpath(OUT, ROOT))
        for b in bad:
            print('  !! %s' % b)
        return 1 if bad else 0
    for b in bad:
        print('  !! %s' % b)
    if bad:
        print('not written')
        return 1
    open(OUT, 'w', encoding='utf-8', newline='').write(text)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
