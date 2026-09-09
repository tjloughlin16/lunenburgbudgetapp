#!/usr/bin/env python3
"""Every figure in the BOTH-DIRECTIONS record on /if-students-leave, recomputed.

    python3 scripts/verify_if_students_leave.py

WHY A SECOND SCRIPT, when the generator already refuses to write on sixteen conditions.

Rule 9: a figure in a finished document gets RECOMPUTED, not re-read — and rule 13 says
an instrument that reformats before you see it is part of the finding. The generator reads
DESE's two workbooks directly with openpyxl and applies its own filters. This verifier
never opens those workbooks. It goes to `dese_town_enrollment` in the analysis database,
which `build_db.py` loaded by a different route, and recomputes the three series from
SQL. Two independent readers, one answer, or this fails.

THE CHECK THAT MATTERS MOST IS NOT THE ARITHMETIC. It is that the two definitions still
SELECT WHAT THEY CLAIM. Both are exclusion filters:

    out = residents of Lunenburg enrolled somewhere that is NOT Lunenburg
    in  = children enrolled in Lunenburg who do NOT live in Lunenburg

An exclusion filter has two silent failure modes and neither raises anything. Excluding
NOTHING — because the district code or the town name stopped matching — turns "children
who left" into "every child in town", and the chart still draws. Excluding EVERYTHING
turns it into zero, and a town nobody leaves looks exactly like a join that matched no
rows. So the complement of each filter is asserted to be non-empty in every single year,
and the two halves are added back to the file's own count for that year.

WHAT IT ALSO ASSERTS
  * the five spot-check years a reader was given, by value;
  * that the net is negative in every published year and the payload says so;
  * that every figure registered in the both-directions conclusion recomputes;
  * that the two gap rows this section rests on are in money_gaps, each with a `closes`;
  * that not one of these figures is typed into the .tsx (rule 2).
"""
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources/data/lunenburg.db')
PAYLOAD = os.path.join(ROOT, 'fy28/public/data/if-students-leave.json')
PAGE = os.path.join(ROOT, 'fy28/src/pages/IfStudentsLeave.tsx')

TOWN = 'Lunenburg'
LEA = '01620000'
CONCLUSION = 'the-net-is-flat-and-the-arriving-half-is-not'

# The five years quoted to this project when the section was asked for, kept as a fixture
# because a spot check somebody can read is worth more than a recomputation nobody sees.
# fy -> (out, in, net)
SPOT = {2014: (186, 51, -135), 2017: (237, 45, -192), 2020: (191, 34, -157),
        2023: (191, 21, -170), 2026: (177, 15, -162)}

GAPS = [
    'What Lunenburg receives for a child who chooses IN, and what the fall from 51 to 15 '
    'is worth',
    'How many school choice seats Lunenburg opened, by grade and by year',
]

bad = []


def check(ok, msg):
    if not ok:
        bad.append(msg)
    return ok


def main():
    if not os.path.exists(PAYLOAD):
        sys.exit('run scripts/build_if_students_leave.py first')
    d = json.load(open(PAYLOAD, encoding='utf-8'))
    B = d['flows']['both_ways']
    c = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)

    # ---------------------------------------------------------------- the filters select
    rows = c.execute(
        'SELECT fy, town, lea, SUM(students) FROM dese_town_enrollment GROUP BY 1,2,3'
    ).fetchall()
    check(rows, 'dese_town_enrollment is empty — the whole of this section reads as absent')

    years = sorted({int(r[0]) for r in rows})
    out, inn, home_out, home_in = {}, {}, {}, {}
    for fy, town, lea, n in rows:
        fy, n = int(fy), int(n or 0)
        if town == TOWN:
            (out if lea != LEA else home_out)[fy] = \
                (out if lea != LEA else home_out).get(fy, 0) + n
        if lea == LEA:
            (inn if town != TOWN else home_in)[fy] = \
                (inn if town != TOWN else home_in).get(fy, 0) + n

    for fy in years:
        check(out.get(fy, 0) > 0,
              f'FY{fy}: the outward filter selects nothing in the database either — '
              'which is what a town nobody leaves looks like')
        check(inn.get(fy, 0) > 0,
              f'FY{fy}: the arriving filter selects nothing in the database either')
        # THE COMPLEMENTS. If these are empty the filter is excluding nothing and the
        # counts above have quietly become the whole district.
        check(home_out.get(fy, 0) > 0,
              f'FY{fy}: no Lunenburg resident is recorded at LEA {LEA}, so "not our own '
              'district" excludes nothing and the outward count is every child in town')
        check(home_in.get(fy, 0) > 0,
              f'FY{fy}: no Lunenburg-resident child is recorded at LEA {LEA} on the '
              'receiving side, so "not our own town" excludes nothing')
        # And the two halves add back to what the table holds for the year.
        total_res = c.execute(
            'SELECT SUM(students) FROM dese_town_enrollment WHERE fy=? AND town=?',
            (fy, TOWN)).fetchone()[0] or 0
        check(out.get(fy, 0) + home_out.get(fy, 0) == int(total_res),
              f'FY{fy}: {out.get(fy, 0)} + {home_out.get(fy, 0)} does not add back to the '
              f'{int(total_res)} rows the table holds for Lunenburg residents')
        total_att = c.execute(
            'SELECT SUM(students) FROM dese_town_enrollment WHERE fy=? AND lea=?',
            (fy, LEA)).fetchone()[0] or 0
        check(inn.get(fy, 0) + home_in.get(fy, 0) == int(total_att),
              f'FY{fy}: {inn.get(fy, 0)} + {home_in.get(fy, 0)} does not add back to the '
              f'{int(total_att)} attending Lunenburg')

    # --------------------------------------------------------- the series, recomputed
    pay = {r['sy']: r for r in B['series']}
    check(sorted(pay) == years,
          f'the payload covers {sorted(pay)} and the database covers {years}')
    for fy in years:
        if fy not in pay:
            continue
        r = pay[fy]
        check(r['out_all'] == out[fy],
              f'FY{fy}: payload says {r["out_all"]} leaving, the database says {out[fy]}')
        check(r['in_all'] == inn[fy],
              f'FY{fy}: payload says {r["in_all"]} arriving, the database says {inn[fy]}')
        check(r['net_all'] == inn[fy] - out[fy],
              f'FY{fy}: payload net {r["net_all"]} is not {inn[fy]} − {out[fy]}')
        check(r['out_member'] + r['out_choice'] + r['out_charter'] + r['out_other']
              == r['out_all'],
              f'FY{fy}: the outward decomposition does not sum to the outward total')
        check(r['in_choice'] + r['in_tuitioned'] + r['in_foster'] + r['in_other']
              == r['in_all'],
              f'FY{fy}: the arriving decomposition does not sum to the arriving total')

    for fy, (o, i, n) in SPOT.items():
        check(fy in pay, f'FY{fy} is a spot-check year and is not in the payload')
        if fy in pay:
            got = (pay[fy]['out_all'], pay[fy]['in_all'], pay[fy]['net_all'])
            check(got == (o, i, n), f'FY{fy} spot check: expected {(o, i, n)}, got {got}')

    # ------------------------------------------------------- what the page claims about it
    check(all(r['net_all'] < 0 for r in B['series']),
          'a year of net gain exists in the series and the page says none does')
    check(B['years_net_positive'] == 0 and B['net_positive_years'] == [],
          'the payload disagrees with itself about years of net gain')
    check(B['out_first'] == out[years[0]] and B['out_last'] == out[years[-1]],
          'the first and last outward figures do not match the series')
    check(B['in_first'] == inn[years[0]] and B['in_last'] == inn[years[-1]],
          'the first and last arriving figures do not match the series')
    check(abs(B['in_change_pct'] - (inn[years[-1]] / inn[years[0]] - 1)) < 5e-5,
          'the arriving percentage change does not recompute')
    check(abs(B['out_change_pct'] - (out[years[-1]] / out[years[0]] - 1)) < 5e-5,
          'the outward percentage change does not recompute')
    check(B['net_worst'] == min(r['net_all'] for r in B['series'])
          and B['net_best'] == max(r['net_all'] for r in B['series']),
          'the net range does not match the series')
    check(sum(x['students'] for x in B['in_latest']) == B['in_last'],
          'the latest year’s arrivals by mechanism do not sum to the year')

    # THE FINDING ITSELF, as an assertion rather than as a sentence: the arriving half
    # moved by an order of magnitude more than the outward one. If that stops being true
    # the section's headline is wrong and this is the only thing that would say so.
    check(abs(B['in_change_pct']) > 5 * abs(B['out_change_pct']),
          'arriving no longer falls by several times what leaving does — the whole point '
          'of drawing three series instead of one no longer holds')

    # ------------------------------------------------------------------- the conclusion
    con = next((x for x in d['conclusions'] if x['id'] == CONCLUSION), None)
    if check(con is not None, f'the conclusion {CONCLUSION!r} is not in the payload'):
        want = {
            'years': len(B['series']), 'out_last': B['out_last'], 'sy': B['last']['sy'],
            'in_last': B['in_last'], 'out_min': B['out_min'], 'out_max': B['out_max'],
            'out_change': -B['out_change'], 'out_first': B['out_first'],
            'in_first': B['in_first'], 'net_best': -B['net_best'],
            'net_worst': -B['net_worst'],
        }
        for k, v in want.items():
            got = con['figures'].get(k, {}).get('value')
            check(got == v, f'conclusion figure {k!r} is {got!r}, recomputes to {v!r}')
        fall = con['figures'].get('in_fall', {}).get('value')
        check(fall is not None and abs(fall - (-B['in_change_pct'] * 100)) < 5e-3,
              f'conclusion figure in_fall is {fall!r} and does not recompute')
        prose = con['claim'] + ' ' + con['detail']
        for name, f in con['figures'].items():
            check(f['text'] in prose,
                  f'conclusion figure {name!r} renders as {f["text"]!r} and that string is '
                  'in neither the claim nor the detail')

    # -------------------------------------------------------------------- rule 7c, the gaps
    have = {r['what']: r for r in d['gaps']}
    for g in GAPS:
        if check(g in have, f'money_gaps no longer carries {g!r}'):
            check((have[g].get('closes') or '').strip(),
                  f'the gap {g!r} names no document that would close it — a gap with no '
                  'named remedy is a grievance, and one with a remedy is a records request')

    # ------------------------------------------------------------------------- rule 2
    # No figure from this section typed into the page. Style values (`text-[13.5px]`,
    # `minmax(...20rem)`) and `slice(2)` are the page's own, so a figure is only looked
    # for where a figure could be read as one.
    src = open(PAGE, encoding='utf-8').read()
    src = re.sub(r'\[[^\]]*\]', ' ', src)          # tailwind arbitrary values
    src = re.sub(r'slice\(\d+\)', ' ', src)
    src = re.sub(r'\{/\*.*?\*/\}', ' ', src, flags=re.S)   # comments
    src = re.sub(r'/\*.*?\*/', ' ', src, flags=re.S)
    typed = set(re.findall(r'(?<![\w.$#-])\d{2,}(?![\w.%])', src))
    for v in {abs(B['out_last']), abs(B['in_last']), abs(B['net_last']),
              abs(B['in_first']), abs(B['out_first']), abs(B['net_worst']),
              abs(B['out_max']), abs(B['out_min'])}:
        check(str(v) not in typed,
              f'{v} is typed into {os.path.relpath(PAGE, ROOT)}. Every figure on this page '
              'is interpolated from the payload (rule 2).')

    if bad:
        print('verify_if_students_leave: %d problem(s)' % len(bad))
        for b in bad:
            print('  -', b)
        sys.exit(1)
    print('verify_if_students_leave: ok — %d school years, both directions, recomputed '
          'from the database against a payload built from the workbooks. Leaving %d → %d '
          '(%+.1f%%), arriving %d → %d (%+.1f%%), net negative in %d of %d years.'
          % (len(B['series']), B['out_first'], B['out_last'], B['out_change_pct'] * 100,
             B['in_first'], B['in_last'], B['in_change_pct'] * 100,
             len(B['series']), len(B['series'])))


if __name__ == '__main__':
    main()
