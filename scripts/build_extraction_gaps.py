#!/usr/bin/env python3
"""What this project has READ but cannot yet TRUST, registered as gaps.

    python3 scripts/build_extraction_gaps.py           # merge `extraction` rows into money-gaps.csv
    python3 scripts/build_extraction_gaps.py --check   # fail if they have drifted

TJ, 20 September 2026, on discovering that stabilization fund history was unusable only
because he asked for it: "we need to surface these gaps so I dont find them with
questions like this."

THE GAP THIS CLOSES IS ABOUT US, NOT THE TOWN. Every other side in money-gaps.csv records
something the town does not publish. This one records something the town DID publish,
that we read, and that nothing has yet reconciled -- 13,405 rows off sixteen annual
reports, of which 409 are checked. The rows are in the database and served by the API, so
a reader or an agent can query them and get a confident-looking answer off a table that is
54% check-failed.

`status` is what stands between that and a wrong number, and CLAUDE.md says nothing may be
aggregated without splitting on it. That rule works and it is invisible: it lives in a
reference note, while the data itself is one query away on a public endpoint. So the
shortfall belongs where every other limit of this archive is published.

WHY GENERATED. The counts move every time an extractor improves, and a hand-typed "3.1%
checked" would be wrong the first time somebody fixed a ruler -- rule 2, on a figure that
is exactly the kind this project keeps getting caught by.

WHY IT MERGES RATHER THAN REWRITES. money-gaps.csv has several authors and was clobbered
twice in one day. This replaces only the rows whose side is `extraction` and leaves every
other row exactly as found, byte for byte, including the file's newline convention.
"""
import argparse
import csv
import io
import os
import collections
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN = os.path.join(ROOT, 'sources', 'data', 'extraction-plan.csv')
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
SIDE = 'extraction'

# Only families where the shortfall actually costs a reader an answer. A dataset of names
# and dates does not need a reconciliation to be useful; one carrying DOLLARS does, and
# those are the ones somebody will try to trend.
PLAN_DATASET = {
    'report_trust_funds': 'trust_funds',
    'report_appropriations': 'appropriations',
    'report_capital_projects': 'capital_projects',
    'report_debt': 'debt',
    'report_gross_wages': 'gross_wages',
}

WORTH_SAYING = {
    'report_trust_funds': ('the stabilization and trust fund balances',
                           'how much the town holds in reserve, and how that has moved'),
    'report_appropriations': ('what Town Meeting appropriated, article by article',
                              'what the town voted to spend, year over year'),
    'report_capital_projects': ('the capital projects and what they cost',
                                'what the town has built and what it paid'),
    'report_debt': ('the debt schedule',
                    'what the town owes and when it falls due'),
    'report_gross_wages': ('gross wages, name by name',
                           'what the town pays its people in total'),
}


def counts():
    db = sqlite3.connect(DB)
    out = {}
    for table, (what, why) in WORTH_SAYING.items():
        try:
            rows = dict(db.execute(
                'SELECT status, COUNT(*) FROM %s GROUP BY status' % table).fetchall())
        except sqlite3.OperationalError:
            continue
        total = sum(rows.values())
        if not total:
            continue
        out[table] = dict(what=what, why=why, total=total,
                          checked=rows.get('checked', 0),
                          failed=rows.get('check failed', 0),
                          nocheck=rows.get('no check', 0))
    return out


def difficulty(table):
    """What the per-year survey in extraction-plan.csv says about this family.

    THE SURVEY IS THE POINT. A reader told only that 54% of rows failed will assume
    neglect. The plan says otherwise: somebody opened every page and wrote down what was
    wrong with it -- mirrored layouts, a missing fund-name column, two years with
    different column counts. Ten of seventeen trust-fund years need real PDF geometry
    rather than text, which is a different and larger job than fixing a ruler, and saying
    so is the difference between a backlog and an accusation.
    """
    name = PLAN_DATASET.get(table)
    if not name or not os.path.exists(PLAN):
        return None
    rows = [r for r in csv.DictReader(open(PLAN, encoding='utf-8'))
            if r.get('dataset') == name]
    if not rows:
        return None
    c = collections.Counter((r.get('extractable') or '?').strip() for r in rows)
    return dict(years=len(rows), counts=c,
                checkable=sum(1 for r in rows if (r.get('checkable') or '').strip() == 'yes'))


def gap_rows():
    rows = []
    for table, c in sorted(counts().items()):
        if c['checked'] == c['total']:
            continue
        pct = c['checked'] / c['total'] * 100
        rows.append({
            'side': SIDE,
            'what': 'Can we trust %s enough to chart %s?' % (c['what'], c['why']),
            'why': why_for(table, c),
        })
    return rows


def why_for(table, c):
    base = ('%s of %s rows in `%s` are reconciled to a total the document itself prints — '
            '%s failed that check and %s were never checked. The figures are read and '
            'published, so a query returns them and they look confident; only the '
            '`status` column says otherwise.'
            % ('{:,}'.format(c['checked']), '{:,}'.format(c['total']), table,
               '{:,}'.format(c['failed']), '{:,}'.format(c['nocheck'])))
    d = difficulty(table)
    if d:
        hard = d['counts'].get('not without geometry', 0)
        messy = d['counts'].get('messy', 0)
        clean = d['counts'].get('clean', 0)
        base += (' Every page was surveyed before anyone tried: of %d years, %d need real '
                 'PDF geometry rather than text, %d are messy and %d are clean — mirrored '
                 'layouts, rows offset from their own names, a missing fund-name column, '
                 'and column counts that change between years. %d of %d years do print a '
                 'grand total to reconcile against, so the anchor exists.'
                 % (d['years'], hard, messy, clean, d['checkable'], d['years']))
    return base + (' — closes: a geometry-aware extractor for this table family, tied to '
                   'the printed total on each page. The per-year survey is in '
                   '`sources/data/extraction-plan.csv`.')


def read_existing():
    with open(GAPS, 'rb') as fh:
        raw = fh.read()
    nl = '\r\n' if b'\r\n' in raw else '\n'
    text = raw.decode('utf-8')
    rows = list(csv.DictReader(io.StringIO(text)))
    return rows, nl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    existing, nl = read_existing()
    kept = [r for r in existing if (r.get('side') or '') != SIDE]
    mine = gap_rows()
    if not mine:
        print('nothing to register')
        return 0

    merged = kept + mine
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=['side', 'what', 'why'], lineterminator=nl)
    w.writeheader()
    for r in merged:
        w.writerow({k: r.get(k, '') for k in ('side', 'what', 'why')})
    out = buf.getvalue()

    current = open(GAPS, encoding='utf-8').read()
    if a.check:
        if out != current:
            print('money-gaps.csv is stale for side=%s — run: '
                  'python3 scripts/build_extraction_gaps.py' % SIDE, file=sys.stderr)
            return 1
        print('%d %s gap(s), current' % (len(mine), SIDE))
        return 0

    with open(GAPS, 'w', encoding='utf-8', newline='') as fh:
        fh.write(out)
    print('registered %d %s gap(s); %d other row(s) untouched' % (len(mine), SIDE, len(kept)))
    for r in mine:
        print('  ' + r['what'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
