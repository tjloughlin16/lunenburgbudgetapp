#!/usr/bin/env python3
"""What the town spends against the minimum the state requires — 33 years of it.

THE ONE MEASURE MASSACHUSETTS ACTUALLY ENFORCES. Chapter 70 sets a required net school
spending figure for every district, and a town that falls below it is out of compliance.
Everything else on this site is a budget the town chose; this is the floor underneath.

WHAT THE SERIES SHOWS, and it is not the story anybody tells about Lunenburg: the town
spent at the state median as recently as FY2018 -- 1.2978 against a median of 1.2978,
rank 181 of 361 -- and has fallen away since, to 1.1598 and rank 238 of 362 in FY2024.
That is the worst position since FY2005. The usual framing is that Lunenburg has always
been a low spender. Against this measure it was not.

RULE 1 IS THE WHOLE DIFFICULTY, and the data hands us the answer rather than hiding it:
`nss_stage` says ACTUAL for FY1994-FY2024 and BUDGETED for FY2025-FY2026. Those are two
stages of one quantity. A budgeted ratio and an actual ratio may not be differenced, and
a trend line drawn through both is a trend through a change of instrument. So the two are
carried in separate arrays, labelled, and the generator refuses to emit a single combined
series at all -- there is no field here that a caller could accidentally treat as one.

WHY THE RANK MATTERS MORE THAN THE RATIO. The ratio moves when the REQUIREMENT moves, and
the requirement is recomputed every year from enrolment and municipal wealth. The rank
against every other district in the same year removes that: it asks where Lunenburg sits
among districts all facing the same formula in the same year.

    python3 scripts/build_spending_vs_required.py
    python3 scripts/build_spending_vs_required.py --check
"""
import argparse
import json
import re
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'spending-vs-required.json')
LEA = '01620000'
MIN_YEARS = 25


def build():
    if not os.path.exists(DB):
        raise SystemExit('%s is missing. Run scripts/build_db.py.' % DB)
    db = sqlite3.connect(DB)

    rows = db.execute("""
        SELECT fy, nss_stage, required_nss, net_school_spending, nss_pct_of_required,
               reconciles
        FROM dese_ch70_formula WHERE lea=? AND level='district'
          AND net_school_spending IS NOT NULL
        ORDER BY fy""", (LEA,)).fetchall()
    if len(rows) < MIN_YEARS:
        raise SystemExit('only %d years of net school spending; expected at least %d. '
                         'Nothing written.' % (len(rows), MIN_YEARS))

    stages = {r[1] for r in rows}
    if not stages <= {'actual', 'budgeted'}:
        raise SystemExit('unexpected nss_stage values %r. This file splits on stage and '
                         'refuses to guess where a new one belongs. Nothing written.'
                         % sorted(stages))
    unreconciled = [r[0] for r in rows if r[5] != 'yes']
    if unreconciled:
        raise SystemExit('these years do not reconcile: %r. Nothing written.' % unreconciled)

    # `lunenburg_rank_of_districts` is a STRING like "103 of 368", not a number. It is a
    # rendering of two facts stuck together -- rule 13's shape, in a column -- so it is
    # split back apart here rather than being formatted or compared as text.
    def _rank(v):
        m = re.match(r'\s*(\d+)\s+of\s+(\d+)', str(v or ''))
        return (int(m.group(1)), int(m.group(2))) if m else (None, None)

    state = {(fy): (med, lun, rank, n, basis) for fy, basis, med, lun, rank, n in db.execute(
        """SELECT fy, basis, median, lunenburg, lunenburg_rank_of_districts, districts
           FROM dese_ch70_statewide WHERE measure LIKE '%net school spending%'""")}
    if not state:
        raise SystemExit('the statewide comparison matched nothing. A join that matches '
                         'nothing looks exactly like a district nobody ranks. '
                         'Nothing written.')

    def pack(stage):
        out = []
        for fy, st, req, nss, pct, _ in rows:
            if st != stage:
                continue
            s = state.get(fy)
            rk, of = _rank(s[2]) if s else (None, None)
            out.append({
                'fy': fy, 'required': round(req), 'spent': round(nss),
                'ratio': round(pct, 4),
                'above_required': round(nss - req),
                'state_median': round(s[0], 4) if s else None,
                'rank': rk,
                'districts': of or (s[3] if s else None),
                # THE COUNTERFACTUAL, per year and labelled. What the town would have
                # spent at the state's median ratio. Arithmetic on a published median,
                # not a claim that anybody could or should have spent it.
                'at_state_median': round(req * s[0]) if s else None,
                'short_of_median': round(req * s[0] - nss) if s else None,
            })
        return out

    actual = pack('actual')
    budgeted = pack('budgeted')
    if not actual:
        raise SystemExit('no ACTUAL years survived the split. Nothing written.')

    ranked = [a for a in actual if a['rank']]
    best = min(ranked, key=lambda a: a['rank'])
    worst_recent = min(ranked, key=lambda a: -a['fy'])
    at_or_above = [a for a in ranked if a['state_median'] and a['ratio'] >= a['state_median']]

    return {
        'about': 'Lunenburg’s net school spending against the minimum Chapter 70 requires, '
                 'and against every other district in the same year.',
        'source': {
            'table': 'dese_ch70_formula and dese_ch70_statewide',
            'publisher': 'Massachusetts Department of Elementary and Secondary Education',
            'note': 'Required net school spending is the floor Chapter 70 sets. A district '
                    'below it is out of compliance. This is the one spending measure the '
                    'state enforces rather than observes.',
        },
        'stage_warning': 'nss_stage is ACTUAL for FY%d–FY%d and BUDGETED for FY%d–FY%d. '
                         'These are two stages of one quantity and are never differenced, '
                         'never averaged, and never drawn as one line.'
                         % (actual[0]['fy'], actual[-1]['fy'],
                            budgeted[0]['fy'], budgeted[-1]['fy'])
                         if budgeted else 'All years are the ACTUAL stage.',
        'actual': actual,
        'budgeted': budgeted,
        'best_rank': best,
        'latest_actual': actual[-1],
        'years_at_or_above_median': len(at_or_above),
        'years_measured': len(ranked),
        'not_established': [
            'WHETHER THIS IS A CHOICE OR A CEILING. The levy limit, two failed overrides, '
            'the district’s request and Town Meeting’s vote all resolve into this one '
            'number, and nothing here separates them.',
            'WHAT THE MONEY WOULD HAVE BOUGHT. The gap to the median is arithmetic on a '
            'published median. It is not a costed programme and nobody has proposed it.',
            'THAT THE RATIO MEASURES EFFORT. It moves when the REQUIREMENT moves, and the '
            'requirement is recomputed each year from enrolment and municipal wealth. That '
            'is why the rank against other districts is carried beside it.',
        ],
        'closes': 'Nothing further is needed to measure this — DESE publishes it annually. '
                  'What is not published is WHY a district lands where it does, which is a '
                  'question about town meetings rather than about data.',
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    data = build()
    if args.check:
        if not os.path.exists(OUT):
            print('MISSING %s' % os.path.relpath(OUT, ROOT)); return 1
        with open(OUT, encoding='utf-8') as fh:
            if json.load(fh) != data:
                print('STALE %s — run: python3 scripts/build_spending_vs_required.py'
                      % os.path.relpath(OUT, ROOT)); return 1
        print('ok — %s reproduces from the database' % os.path.relpath(OUT, ROOT)); return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True); fh.write('\n')
    b, l = data['best_rank'], data['latest_actual']
    print('%s: %d actual years, %d budgeted'
          % (os.path.relpath(OUT, ROOT), len(data['actual']), len(data['budgeted'])))
    print('  best rank  FY%d  %.4f vs median %.4f — rank %d of %d'
          % (b['fy'], b['ratio'], b['state_median'], b['rank'], b['districts']))
    print('  latest     FY%d  %.4f vs median %.4f — rank %d of %d'
          % (l['fy'], l['ratio'], l['state_median'], l['rank'], l['districts']))
    print('  at or above the median in %d of %d measured years'
          % (data['years_at_or_above_median'], data['years_measured']))
    print('  FY%d gap to the median ratio: $%s'
          % (l['fy'], format(l['short_of_median'], ',')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
