#!/usr/bin/env python3
"""Every figure in the circuit-breaker conclusions, recomputed from the database.

    python3 scripts/verify_circuit_breaker.py

Rule 9, by a route that shares no code with the generator.
"""
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'circuit-breaker.json')
FAILS = []


def check(ok, msg):
    if not ok:
        FAILS.append(msg)


def main():
    d = json.load(open(OUT, encoding='utf-8'))
    by_id = {c['id']: c for c in d['conclusions']}
    f = lambda cid, k: by_id[cid]['figures'][k]['value']
    db = sqlite3.connect('file:%s?mode=ro' % DB, uri=True)
    rows = db.execute("SELECT fy, eligible_students_claimed, total_eligible_expenses, threshold_amount, total_net_claim, "
                      "total_quarterly_payment, reimb_transport FROM dese_circuit_breaker WHERE level='district' AND district='Lunenburg' ORDER BY fy").fetchall()
    last = rows[-1]
    most = max(rows, key=lambda r: r[1])
    check(f('fewer-children-each-far-more-expensive', 'kids_now') == last[1] and f('fewer-children-each-far-more-expensive', 'kids_peak') == most[1], 'children')
    check(abs(f('fewer-children-each-far-more-expensive', 'per_child_now') - last[2] / last[1]) < 1e-6, 'per child now')
    check(abs(f('fewer-children-each-far-more-expensive', 'per_child_then') - most[2] / most[1]) < 1e-6, 'per child then')
    shares = [(r[0], r[5] / r[4]) for r in rows if r[4]]
    lo = min(shares, key=lambda x: x[1]); hi = max(shares, key=lambda x: x[1])
    check(abs(f('the-state-pays-what-it-appropriated', 'low') - lo[1]) < 1e-9 and f('the-state-pays-what-it-appropriated', 'fy_low') == lo[0], 'low share')
    check(abs(f('the-state-pays-what-it-appropriated', 'high') - hi[1]) < 1e-9, 'high share')
    check(f('the-state-pays-what-it-appropriated', 'full_years') == sum(1 for _, s in shares if s >= 0.70), 'full years')
    check(abs(f('the-threshold-is-a-deduction-not-a-rate', 'per_child') - last[3] / last[1]) < 1e-6, 'threshold per child')
    check(f('the-threshold-is-a-deduction-not-a-rate', 'total') == last[3], 'threshold total')
    check(abs(f('the-threshold-is-a-deduction-not-a-rate', 'share_elig') - last[5] / last[2]) < 1e-9, 'share of eligible')
    tr = [r for r in rows if r[6]]
    check(f('transport-joined-the-reimbursement', 'first') == tr[0][6] and f('transport-joined-the-reimbursement', 'fy_first') == tr[0][0], 'transport first')
    check(f('transport-joined-the-reimbursement', 'now') == last[6], 'transport now')
    check(f('transport-joined-the-reimbursement', 'peak') == max(r[6] for r in tr), 'transport peak')
    peers = db.execute("SELECT district, total_eligible_expenses/eligible_students_claimed FROM dese_circuit_breaker WHERE level='district' AND fy=? "
                       "AND eligible_students_claimed>0 AND district NOT LIKE '%non-op%'", (last[0],)).fetchall()
    pcs = sorted(p[1] for p in peers)
    check(abs(f('lunenburgs-placements-cost-more-per-child-than-most-neighbours', 'lo') - pcs[0]) < 1e-6 and abs(f('lunenburgs-placements-cost-more-per-child-than-most-neighbours', 'hi') - pcs[-1]) < 1e-6, 'peer range')
    check(f('lunenburgs-placements-cost-more-per-child-than-most-neighbours', 'n') == len(peers), 'peer count')
    st = db.execute("SELECT eligible_students_claimed, total_eligible_expenses FROM dese_circuit_breaker WHERE level='state' AND fy=?", (last[0],)).fetchone()
    check(f('lunenburgs-placements-cost-more-per-child-than-most-neighbours', 'state_kids') == st[0] and f('lunenburgs-placements-cost-more-per-child-than-most-neighbours', 'state_elig') == st[1], 'state')
    if FAILS:
        print('FAIL:\n  ' + '\n  '.join(FAILS)); return 1
    print('PASS — every figure the circuit-breaker conclusions name recomputes from dese_circuit_breaker')
    return 0


if __name__ == '__main__':
    sys.exit(main())
