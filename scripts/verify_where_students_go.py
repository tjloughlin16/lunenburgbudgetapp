#!/usr/bin/env python3
"""Every figure /where-students-go-instead states, recomputed from the database.

WHY THIS EXISTS SEPARATELY FROM `build_special_education.py --check`. That check asks
whether the payload still reproduces from the generator. It cannot ask whether the
generator is RIGHT: a generator and its own output agree by construction, and the whole
family of defects this repo keeps finding is a derived thing quoted as an observed one
(rule 13). So every figure below is computed here by a DIFFERENT route -- SQL written
against the raw table, not the generator's Python -- and compared.

That is not a formality. The FIRST version of this page's outflow figure came from a
second generator, `build_where_students_go.py`, which defined "in district" as the
Resident/Member rows minus the Montachusett rows. It reads like the obvious definition
and it is wrong: two Lunenburg children at a state-run school are Resident/Member rows of
a district that is not Lunenburg, so they were counted as being in Lunenburg's schools.
It published 184 where the measured figure is 186. Both generators agreed with
themselves. Only a second route found it, and that generator is now deleted.

WHAT IS CHECKED:

  1. The 13-year series -- total, in-district, elsewhere, share -- row by row.
  2. The three-route decomposition, and that the three plus the residual FOOT to the
     elsewhere figure in every year. A decomposition that does not sum is not one.
  3. The change percentages the lead insight states, recomputed from the endpoints.
  4. Every named receiving district in the latest year.
  5. Both directions of school choice.
  6. RULE 2, structurally: no bare figure is typed into the page's prose. The page is
     the only surface a reader sees, and a correct payload rendered beside a hardcoded
     number is exactly the failure this project has shipped three times.

    python3 scripts/verify_where_students_go.py
"""
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'sped-leaving.json')
PAGE = os.path.join(ROOT, 'fy28', 'src', 'pages', 'SpedLeaving.tsx')
TOWN = 'Lunenburg'
LEA = '01620000'
MONTY = '08320000'

# The only literal numbers allowed to stand in the page's prose, and neither is a
# measurement. `grade 9` NAMES a grade -- it is the hypothesis the page refuses to adopt,
# and writing it as a derived value would be absurd. Anything else that appears here is a
# figure somebody typed, which is rule 2's whole subject.
ALLOWED = ['grade 9']

fails = []
checks = 0


def eq(what, got, want):
    global checks
    checks += 1
    if got != want:
        fails.append('%s: page says %r, the database says %r' % (what, got, want))


def main():
    db = sqlite3.connect(DB)
    with open(PAYLOAD, encoding='utf-8') as fh:
        d = json.load(fh)

    # ------------------------------------------------------- 1. the series, row by row
    years = [r[0] for r in db.execute(
        'SELECT DISTINCT fy FROM dese_town_enrollment WHERE town=? ORDER BY fy', (TOWN,))]
    eq('the years covered', [s['fy'] for s in d['series']], years)
    if not years:
        fails.append('no years for %s at all -- a join that matches nothing looks '
                     'exactly like a town with no children' % TOWN)
        return report()

    for fy in years:
        tot, here = db.execute(
            'SELECT SUM(students), SUM(CASE WHEN lea=? THEN students ELSE 0 END) '
            'FROM dese_town_enrollment WHERE town=? AND fy=?', (LEA, TOWN, fy)).fetchone()
        s = next(x for x in d['series'] if x['fy'] == fy)
        eq('FY%d resident total' % fy, s['total'], int(tot))
        eq('FY%d in Lunenburg' % fy, s['in_lunenburg'], int(here))
        eq('FY%d educated elsewhere' % fy, s['elsewhere'], int(tot - here))
        eq('FY%d share elsewhere' % fy, s['elsewhere_pct'],
           round(100.0 * (tot - here) / tot, 2))

    # -------------------------------------------------- 2. the three routes, and they FOOT
    for r in d['routes']:
        fy = r['fy']
        monty, choice, charter, elsewhere = db.execute(
            'SELECT SUM(CASE WHEN lea=? THEN students ELSE 0 END),'
            '       SUM(CASE WHEN enrollment_reason=? THEN students ELSE 0 END),'
            '       SUM(CASE WHEN enrollment_reason=? THEN students ELSE 0 END),'
            '       SUM(CASE WHEN lea<>? THEN students ELSE 0 END) '
            'FROM dese_town_enrollment WHERE town=? AND fy=?',
            (MONTY, 'School Choice Program', 'Charter School', LEA, TOWN, fy)).fetchone()
        eq('FY%d Monty Tech' % fy, r['monty_tech'], int(monty))
        eq('FY%d school choice out' % fy, r['school_choice'], int(choice))
        eq('FY%d charter' % fy, r['charter'], int(charter))
        eq('FY%d elsewhere (route table)' % fy, r['elsewhere'], int(elsewhere))
        # The decomposition must foot. This is the check the page's own prose rests on
        # when it says the residual is reported rather than folded into a route.
        eq('FY%d the three routes plus the residual foot to elsewhere' % fy,
           r['monty_tech'] + r['school_choice'] + r['charter'] + r['other'],
           r['elsewhere'])
        if r['other'] < 0:
            fails.append('FY%d: a negative residual (%d)' % (fy, r['other']))

    # ------------------------------------- 3. the change percentages the insight states
    first, last = d['routes'][0], d['routes'][-1]
    for k in ('monty_tech', 'school_choice', 'charter', 'elsewhere', 'in_lunenburg'):
        want = round(100.0 * (last[k] - first[k]) / first[k], 1) if first[k] else None
        eq('%s FY%d->FY%d change' % (k, first['fy'], last['fy']),
           d['route_change'][k]['pct'], want)
        eq('%s first' % k, d['route_change'][k]['first'], first[k])
        eq('%s last' % k, d['route_change'][k]['last'], last[k])

    # ----------------------------------------- 4. every named district in the latest year
    latest = years[-1]
    want = sorted(((r[0], int(r[1])) for r in db.execute(
        'SELECT district, SUM(students) FROM dese_town_enrollment '
        'WHERE town=? AND fy=? AND lea<>? GROUP BY district', (TOWN, latest, LEA))),
        key=lambda r: (-r[1], r[0]))
    eq('every receiving district in FY%d' % latest,
       [(r['district'], r['students']) for r in d['elsewhere_latest']], want)

    # ------------------------------------------------ 5. school choice, both directions
    for row in d['net']:
        inb = db.execute(
            'SELECT COALESCE(SUM(students),0) FROM dese_town_enrollment '
            'WHERE lea=? AND town<>? AND enrollment_reason=? AND fy=?',
            (LEA, TOWN, 'School Choice Program', row['fy'])).fetchone()[0]
        eq('FY%d arriving under school choice' % row['fy'], row['in'], int(inb))
        eq('FY%d net school choice' % row['fy'], row['net'], row['in'] - row['out'])

    # -------------------------------------------------------- 6. rule 2, structurally
    #
    # A figure typed into the page is the one thing no recomputation above can catch.
    # Strip the JSX expressions (everything inside braces is derived by definition), the
    # comments and the class names, and no multi-digit number may survive in what is left
    # -- that residue IS the prose a reader sees.
    src = open(PAGE, encoding='utf-8').read()
    src = src[src.index('  return ('):]          # the JSX only, never the locals above it
    src = re.sub(r'/\*.*?\*/', ' ', src, flags=re.S)
    src = re.sub(r'\{[^{}]*(\{[^{}]*\}[^{}]*)*\}', ' ', src)   # every derived expression
    text = ' '.join(re.findall(r'>([^<>{}]*)<', src))             # the TEXT NODES: the prose
    for ok in ALLOWED:
        text = text.replace(ok, ' ')
    typed = [t for t in re.findall(r'\b\d[\d,]*\b', text)]
    global checks
    checks += 1
    if typed:
        fails.append('rule 2: %s typed into the page prose rather than derived'
                     % ', '.join(sorted(set(typed))))

    return report()


def report():
    print('%d checks against %s' % (checks, os.path.relpath(DB, ROOT)))
    for f in fails:
        print('  FAIL  %s' % f)
    if fails:
        print('%d FAILED' % len(fails))
        return 1
    print('ok — every figure on /where-students-go-instead recomputes from the database')
    return 0


if __name__ == '__main__':
    sys.exit(main())
