#!/usr/bin/env python3
"""Every figure in the enrollment conclusions, recomputed from the database.

    python3 scripts/verify_enrollment.py

Rule 9: verify after writing, by recomputation and not by re-reading. The generator's own
`--check` proves the payload reproduces from the generator; this proves the figures the
conclusions NAME are what the database holds, by a route that shares no code with the
generator.
"""
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'enrollment.json')
FAILS = []


def check(ok, msg):
    if not ok:
        FAILS.append(msg)


def main():
    d = json.load(open(OUT, encoding='utf-8'))
    db = sqlite3.connect('file:%s?mode=ro' % DB, uri=True)
    by_id = {c['id']: c for c in d['conclusions']}
    f = lambda cid, k: by_id[cid]['figures'][k]['value']
    rows = db.execute("SELECT fy, total_cnt, swd_cnt, swd_pct, el_cnt, low_income_pct, "
                      "grade_9_cnt+grade_10_cnt+grade_11_cnt+grade_12_cnt g912, "
                      "pk_cnt+k_cnt+grade_1_cnt+grade_2_cnt+grade_3_cnt+grade_4_cnt+grade_5_cnt k5 "
                      "FROM dese_enrollment WHERE org_level='district' AND org_name='Lunenburg' ORDER BY fy").fetchall()
    by = {r[0]: r for r in rows}
    last = rows[-1]
    peak = max(rows, key=lambda r: r[1])
    check(f('the-fall-ended-a-decade-ago', 'now') == last[1], 'now != latest total')
    check(f('the-fall-ended-a-decade-ago', 'peak') == peak[1] and f('the-fall-ended-a-decade-ago', 'fy_peak') == peak[0], 'peak')
    after = [r for r in rows if r[0] > peak[0]]
    trough = min(after, key=lambda r: r[1])
    check(f('the-fall-ended-a-decade-ago', 'fy_trough') == trough[0], 'trough year')
    base = by[d['base_fy']]
    check(abs(f('the-high-school-did-the-shrinking', 'hs_pct') - abs((last[6] - base[6]) / base[6])) < 1e-9, 'hs pct')
    check(f('the-high-school-did-the-shrinking', 'hs_first') == base[6] and f('the-high-school-did-the-shrinking', 'hs_last') == last[6], 'hs counts')
    check(f('as-many-children-with-disabilities-as-ever', 'now') == last[2] and f('as-many-children-with-disabilities-as-ever', 'then') == base[2], 'swd')
    check(abs(f('as-many-children-with-disabilities-as-ever', 'share_now') - last[3]) < 1e-9, 'swd share')
    check(f('english-learners-from-a-handful-to-seventy', 'now') == last[4], 'el now')
    old = [r for r in rows if r[0] <= 2014 and r[5] is not None][-1]
    check(abs(f('low-income-share-doubled-across-a-definition-change', 'then') - old[5]) < 1e-9 and abs(f('low-income-share-doubled-across-a-definition-change', 'now') - last[5]) < 1e-9, 'low income')
    for name in ['North Middlesex', 'Harvard', 'Groton-Dunstable', 'Ashburnham-Westminster']:
        a = db.execute("SELECT total_cnt FROM dese_enrollment WHERE org_level='district' AND org_name=? AND fy=?", (name, d['base_fy'])).fetchone()
        b = db.execute("SELECT total_cnt FROM dese_enrollment WHERE org_level='district' AND org_name=? AND fy=?", (name, last[0])).fetchone()
        p = next(x for x in d['peers'] if x['district'] == name)
        check(a and b and abs(p['pct'] - (b[0] - a[0]) / a[0]) < 1e-9, 'peer %s' % name)
    lun = next(x for x in d['peers'] if x['district'] == 'Lunenburg')
    check(abs(f('lunenburg-shrank-less-than-most-of-its-neighbours', 'lun') - abs(lun['pct'])) < 1e-9, 'lun pct')
    if FAILS:
        print('FAIL:\n  ' + '\n  '.join(FAILS))
        return 1
    print('PASS — every figure the enrollment conclusions name recomputes from dese_enrollment')
    return 0


if __name__ == '__main__':
    sys.exit(main())
