#!/usr/bin/env python3
"""EVERY FIGURE ON /school-all-funds/carried-over-orders, RECOMPUTED BY ANOTHER ROUTE.

    python3 scripts/verify_carryover.py

The generator (build_carryover_topics.py) reads the journal CSV through journal.py, in Decimal,
one Python pass. This reads the DATABASE copy of the same journal (sources/data/lunenburg.db,
table munis_school_journal) with SQL, in integer CENTS, and joins carried orders to their
payments in SQL rather than through dictionaries. It shares one thing with the generator on
purpose: the special education account list (journal.in_sped_total), because that is the
site's ONE definition and a second copy would be a defect.

It checks, and fails on any difference:
  1. the identities: for each close FY2023-FY2025, per fund group, YEC zeroes what the next
     year's SOY reopens and what its carry-forward BUA re-budgets, all three equal;
  2. per account and per line: the YEC amounts and the next SOY amounts are the same multiset;
  3. every figure in the payload's facts, the comparison table (both views), the chart, and the
     totals row of each budget-line view.
It refuses if the database does not hold the CSV's row count (a stale database proves nothing).
"""
import csv
import json
import os
import sqlite3
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
import journal as J  # noqa: E402

DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
PAGE = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', 'carried-over-orders.json')
Y = (2023, 2024, 2025, 2026)
CLOSES = (2023, 2024, 2025)
bad = []


def usd_c(c):
    return C.usd(c / 100.0)


def main():
    if not os.path.exists(DB):
        print('verify_carryover: %s is absent; run build_db.py' % DB, file=sys.stderr)
        return 1
    db = sqlite3.connect(DB)
    n_csv = sum(1 for _ in csv.DictReader(open(J.JOURNAL_CSV, encoding='utf-8')))
    n_db = db.execute('SELECT COUNT(*) FROM munis_school_journal').fetchone()[0]
    if n_csv != n_db:
        print('verify_carryover: database holds %d journal lines, the CSV %d; rebuild it'
              % (n_db, n_csv), file=sys.stderr)
        return 1
    sped = sorted(a for a, r in J.accounts().items() if r['fund'] == '0100' and J.in_sped_total(r))
    db.execute('CREATE TEMP TABLE sped(account TEXT PRIMARY KEY)')
    db.executemany('INSERT INTO sped VALUES (?)', [(a,) for a in sped])
    db.execute("""CREATE TEMP VIEW j AS SELECT fiscal_year fy, source, posts_to, fund, account,
                  doc_type, doc_no, description,
                  CAST(ROUND(amount * 100) AS INTEGER) c,
                  CASE WHEN fund = '0100' THEN 'gf' ELSE 'other' END grp,
                  account IN (SELECT account FROM sped) is_sped
                  FROM munis_school_journal WHERE object LIKE '5%'""")

    def by(sql, scope):
        where = {'gf': "grp = 'gf'", 'other': "grp = 'other'", 'sped': 'is_sped = 1'}[scope]
        return dict(db.execute(sql.replace('$W', where)).fetchall())

    R = {}
    for s in ('gf', 'other', 'sped'):
        R[('vote', s)] = by("SELECT fy, SUM(c) FROM j WHERE $W AND source = 'BUC' GROUP BY fy", s)
        R[('spent', s)] = by("SELECT fy, SUM(c) FROM j WHERE $W AND posts_to IN ('actual', "
                             "'encumbrance') GROUP BY fy", s)
        R[('owed', s)] = by("SELECT fy, SUM(c) FROM j WHERE $W AND posts_to = 'encumbrance' GROUP BY fy", s)
        R[('out', s)] = by("SELECT fy, -SUM(c) FROM j WHERE $W AND source = 'YEC' GROUP BY fy", s)
        R[('in', s)] = by("SELECT fy, SUM(c) FROM j WHERE $W AND source = 'SOY' GROUP BY fy", s)
        R[('cf', s)] = by("SELECT fy, SUM(c) FROM j WHERE $W AND source = 'BUA' AND description "
                          "LIKE 'ENCUMBRANCE CARRY FORWARD%' GROUP BY fy", s)
        # what happened to a carried order in the year it was reopened: its POL (paid) and POM
        # (closed) lines, joined to the SOY line in SQL
        wo = "o.grp = '%s'" % s if s != 'sped' else 'o.is_sped = 1'
        for k, src in (('paid', 'POL'), ('closed', 'POM')):
            R[(k, s)] = dict(db.execute(
                """SELECT o.fy, -SUM(p.c) FROM j o JOIN j p ON p.fy = o.fy AND p.doc_no = o.doc_no
                   AND p.account = o.account AND p.source = ? AND p.doc_type = 'PO'
                   WHERE o.source = 'SOY' AND """ + wo + ' GROUP BY o.fy', (src,)).fetchall())
    g = lambda k, s, y: R[(k, s)].get(y, 0)

    # 1. the identities, per fund group
    for s in ('gf', 'other', 'sped'):
        for y in CLOSES:
            a, b, c = g('out', s, y), g('in', s, y + 1), g('cf', s, y + 1)
            if not a == b == c:
                bad.append('FY%d %s: YEC %s, next SOY %s, next carry-forward %s' % (y, s, a, b, c))
            if g('owed', s, y):
                bad.append('FY%d %s: a closed year owes %s' % (y, s, g('owed', s, y)))
    # 2. per account, per line
    for y in CLOSES:
        yec, soy = defaultdict(list), defaultdict(list)
        for acct, c in db.execute("SELECT account, -c FROM j WHERE fy = ? AND source = 'YEC'", (y,)):
            yec[acct].append(c)
        for acct, c in db.execute("SELECT account, c FROM j WHERE fy = ? AND source = 'SOY'", (y + 1,)):
            soy[acct].append(c)
        for acct in set(yec) | set(soy):
            if sorted(yec[acct]) != sorted(soy[acct]):
                bad.append('FY%d %s: YEC lines %s, next SOY lines %s' % (y, acct, yec[acct], soy[acct]))
    lines_checked = sum(1 for _ in db.execute("SELECT 1 FROM j WHERE source = 'SOY' AND fy > 2023"))

    # 3. the payload
    p = json.load(open(PAGE, encoding='utf-8'))
    facts = {f['id']: (f['value'] or {}).get('text') for f in p['facts']}

    def want(fid, text):
        if facts.get(fid) != text:
            bad.append('fact %s: page says %r, recomputed %r' % (fid, facts.get(fid), text))
    ymax = max(CLOSES, key=lambda y: g('out', 'gf', y))
    want('out', usd_c(g('out', 'gf', ymax)))
    want('share', C.pct(100.0 * g('out', 'gf', ymax) / g('vote', 'gf', ymax), 2))
    want('cf', usd_c(g('cf', 'gf', ymax + 1)))
    car3 = sum(g('in', 'gf', y + 1) for y in CLOSES)
    paid3 = sum(g('paid', 'gf', y + 1) for y in CLOSES)
    want('paid', C.pct(100.0 * paid3 / car3, 0))
    want('closed', usd_c(sum(g('closed', 'gf', y + 1) for y in CLOSES)))
    moved = {s: {y: g('spent', s, y) - g('paid', s, y) + (g('paid', s, y + 1) if y in CLOSES else 0)
                 for y in Y} for s in ('gf', 'sped')}
    shift = {y: moved['gf'][y] - g('spent', 'gf', y) for y in Y}
    want('shift', usd_c(max(abs(v) for v in shift.values())))
    want('b25', usd_c(g('vote', 'gf', 2025) - g('spent', 'gf', 2025)))
    want('m25', usd_c(g('vote', 'gf', 2025) - moved['gf'][2025]))
    want('sped', usd_c(sum(g('paid', 'sped', y) for y in Y)))
    want('owed', usd_c(g('owed', 'gf', 2026) + g('owed', 'other', 2026)))
    # the comparison table, both views
    t1 = p['tables'][0]
    for v, s in zip(t1['views'], ('gf', 'sped')):
        for r, y in zip(v['rows'], Y):
            exp = [usd_c(g('vote', s, y)), usd_c(g('spent', s, y)), usd_c(-g('paid', s, y)),
                   usd_c(g('paid', s, y + 1)) if y in CLOSES else None, usd_c(moved[s][y]),
                   usd_c(g('spent', s, y) - g('vote', s, y)), usd_c(moved[s][y] - g('vote', s, y))]
            if r['label'] != C.fy(y) or r['cells'] != exp:
                bad.append('table %s %s: page %s, recomputed %s' % (s, r['label'], r['cells'], exp))
    # the chart
    ch = {t['name']: t['texts'] for t in p['chart']['series']}
    exp = {'Carried in, general fund': [usd_c(g('in', 'gf', y)) for y in Y],
           'Carried out, general fund': [usd_c(g('out', 'gf', y)) if y in CLOSES else None for y in Y],
           'Carried in, other funds': [usd_c(g('in', 'other', y)) for y in Y],
           'Carried out, other funds': [usd_c(g('out', 'other', y)) if y in CLOSES else None for y in Y]}
    if ch != exp:
        bad.append('chart: page %s, recomputed %s' % (ch, exp))
    # each budget-line view's totals row: carried, paid, closed, carried again (all funds)
    for v, y in zip(p['tables'][1]['views'], Y):
        tin = g('in', 'gf', y) + g('in', 'other', y)
        tp = g('paid', 'gf', y) + g('paid', 'other', y)
        tc = g('closed', 'gf', y) + g('closed', 'other', y)
        exp = [usd_c(tin), usd_c(tp), usd_c(tc), usd_c(tin - tp - tc)]
        if v['rows'][-1]['cells'] != exp:
            bad.append('budget lines %s: totals %s, recomputed %s' % (v['label'], v['rows'][-1]['cells'], exp))

    if bad:
        print('verify_carryover: %d failure(s)' % len(bad), file=sys.stderr)
        for b in bad:
            print('  ' + b, file=sys.stderr)
        return 1
    print('verify_carryover: %d facts, %d table rows, the chart and %d budget-line totals agree; '
          'YEC = next SOY = carry-forward for %d closes x 3 scopes, and %d reopened lines match '
          'their close line for line' % (len([f for f in facts.values() if f]), 8, len(Y),
                                         len(CLOSES), lines_checked))
    return 0


if __name__ == '__main__':
    sys.exit(main())
