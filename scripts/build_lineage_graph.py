#!/usr/bin/env python3
"""The archive as a graph: which report produced which field, and what that lets you ask.

    python3 scripts/build_lineage_graph.py      # writes notes/data-model/lineage.json

WHY A GRAPH AND NOT ANOTHER SCHEMA DIAGRAM

Because the question this project keeps having to answer is not "what joins to what" but
"can we answer X" -- and in a graph that is the same question. A question needs a key; a
key lives on a field; a field comes from a table; a table is loaded from an extract; an
extract comes from a report somebody produced. **If a path runs all the way from the
question to a report, the question is answerable. If it stops, the gap is exactly where
the path stops**, and that tells you which document to ask for rather than that something
is missing somewhere.

It also makes the unanswerable ones legible. "Where does the school spend the Chapter 70
money" needs a key joining revenue to expenditure. No field carries one, so the path ends
at the key with nothing behind it -- and no document will extend it, because the key does
not exist in municipal accounting at all. That is a different shape of failure from "we
have not been sent the report yet", and on a graph you can see which one you are looking
at.

WHAT IS DERIVED AND WHAT IS ASSIGNED

  DERIVED   table -> extract, read out of build_db.py's own `rows(...)` calls
            table -> field and the primary keys, read from the live schema
            key coverage, by running the join
  ASSIGNED  extract -> report. Which Town report produced a CSV is our labelling, and it
            is written here in one place rather than implied across a dozen documents.
"""
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
OUT = os.path.join(ROOT, 'notes', 'data-model', 'lineage.json')

# Which report the Town or district runs to produce each extract. Assigned, not derived.
REPORT = {
    'munis-ledger': 'Year-to-date budget report (glytdbud)',
    'town-ledger-fy26-q3': 'Year-to-date budget report (glytdbud)',
    'lps-budget-lines': 'The district budget workbook',
    'line-history': 'The district budget workbook',
    'school-special-revenue-fy26-q3': 'Special revenue report',
    'fund-1301-cash-journal': 'Account Detail (athletics only)',
    'dese-radar': 'DESE, all funds',
    'grants-history': 'The district budget workbook',
    'athletics-by-sport': 'Records request, June 2026',
    'athletic-fee-schedule': 'Records request, June 2026',
    'document-basis': 'Written by this project',
    'copy-status': 'Written by this project',
    'link-status': 'Written by this project',
    'stated-figures': 'Meeting minutes and letters',
    'variance-by-group': 'Written by this project',
}

# A question and the link it turns on. A LOOKUP needs one key; a CONNECTIVITY question
# needs two things joined, and those are the ones worth modelling, because a key can fail
# to bridge in three different ways and only one of them is visible in a schema.
QUESTIONS = [
    ('What was appropriated for the schools?',                  'department'),
    ('How much state aid came in?',                             'account_id'),
    ('What did one account spend?',                             'account_id'),
    ('What is in each revolving fund?',                         'fund'),
    ('What did athletics pay, transaction by transaction?',     'period'),
    ('Is a category over budget?',                              'function'),
    # Connectivity. Each needs two sides brought together.
    ('Do the town and the district agree, by category?',        'function'),
    ('Do the school revolving funds appear in the ledger?',     'fund-both-sides'),
    ('What did state aid pay for?',                             'revenue-to-expense'),
    ('Which categories does state aid pay for?',                'revenue-to-expense'),
    ('Which budget line does a revolving fund pay for?',        'fund-to-line'),
    ('Did a grant pay for these staff?',                        'grant-to-account'),
    ('Which school does this spending belong to?',              'line-to-account'),
]

# Keys, and the field that carries them. A `bridge` is checked further: the column can be
# on both sides and the VALUES still not meet, which is the failure a diagram cannot show.
KEYS = {
    'department':         dict(field='dept',       note='the department code, 300 and 301'),
    'function':           dict(field='function',   note='the DESE category code, 2710 and 2305',
                               bridge=("SELECT DISTINCT function FROM account WHERE function IS NOT NULL",
                                       "SELECT DISTINCT substr(function_group,1,4) FROM budget_line "
                                       "WHERE function_group IS NOT NULL AND function_group != ''")),
    'account_id':         dict(field='account_id', note='the MUNIS account number'),
    'fund':               dict(field='fund',       note='the fund code, 0100 and 1301'),
    'period':             dict(field='period',     note='the fiscal period, 1 to 13'),
    'line_key':           dict(field='line_key',   note='the budget line, by its printed name'),
    'doc_id':             dict(field='doc_id',     note='the document a figure came from'),
    'fund-both-sides':    dict(field=None,
                               note='the fund column is on both sides and the values do not meet',
                               bridge=("SELECT DISTINCT fund FROM fund_activity",
                                       "SELECT DISTINCT fund FROM account")),
    'grant-to-account':   dict(field=None, note='no field ties a grant to an account'),
    'line-to-account':    dict(field=None, note='no field ties a budget line to an account'),
    'fund-to-line':       dict(field=None, note='no field ties a fund to a budget line'),
    'revenue-to-expense': dict(field=None, note='no field ties money in to money out'),
}

# What a failed link means, which is the whole point of separating them.
VERDICT = {
    'joins':     'the key is carried and the two sides share values',
    'disjoint':  'the column is on both sides and no value appears in both',
    'one-sided': 'only one side carries the key',
    'none':      'no field anywhere carries such a key',
}


COLUMN = ['question', 'key', 'table', 'extract', 'report']
ROW_H, TOP = 27, 48
# Font size and label side per column. Questions read right-to-left into their node so the
# column scans as a list; everything else reads outward.
FONT = {'question': 11, 'key': 9.5, 'table': 9.5, 'extract': 9.5, 'report': 9.5}
ANCHOR = {'question': 'end', 'key': 'start', 'table': 'start', 'extract': 'start',
          'report': 'start'}
GAP = 34          # clear space between a column's longest label and the next column
RADIUS = {'question': 7, 'key': 6.5, 'table': 4.5, 'extract': 4.5, 'report': 7}


def text_width(label, fs):
    """Close enough for layout. Getting this wrong is what ran labels off the canvas."""
    return len(label) * fs * 0.53


def layout(nodes, edges):
    """Fixed columns, ordered to minimise crossings. Computed here, not in the browser.

    A force simulation settles somewhere different on every load and reads as scattered
    even when the graph is simple -- the eye cannot tell a meaningful position from a
    lucky one. The chain here is strictly ordered (question, key, table, extract, report),
    which is a layered graph, so the layout is solved once and shipped as coordinates.

    Ordering within a column is the barycentre heuristic: put each node at the average
    height of the things it connects to in the neighbouring column, sort, repeat. Sweeping
    both directions a few times is what stops the edges crossing.
    """
    cols = {k: [n for n in nodes if n['kind'] == k] for k in COLUMN}
    nbr = {n['id']: set() for n in nodes}
    for e in edges:
        nbr[e['source']].add(e['target'])
        nbr[e['target']].add(e['source'])

    order = {k: {n['id']: i for i, n in enumerate(cols[k])} for k in COLUMN}
    for sweep in range(8):
        seq = COLUMN[1:] if sweep % 2 == 0 else COLUMN[-2::-1]
        for k in seq:
            ref = COLUMN[COLUMN.index(k) - 1] if sweep % 2 == 0 else COLUMN[COLUMN.index(k) + 1]
            def bary(n):
                pos = [order[ref][m] for m in nbr[n['id']] if m in order[ref]]
                return sum(pos) / len(pos) if pos else order[k][n['id']]
            cols[k].sort(key=bary)
            order[k] = {n['id']: i for i, n in enumerate(cols[k])}

    # Place the columns from the labels rather than from guessed coordinates. The first
    # version hardcoded five x positions and both end columns ran off the canvas: the
    # question labels extend LEFT from their node and the report labels extend RIGHT, and
    # neither was in the width. A diagram that clips is worse than one that is ugly,
    # because the reader cannot tell that anything is missing.
    widest = {k: max((text_width(n['label'], FONT[k]) for n in cols[k]), default=0)
              for k in COLUMN}

    x = 12 + widest['question'] + RADIUS['question'] + 8      # room for left-hand labels
    for k in COLUMN:
        for n in cols[k]:
            n['x'] = round(x)
        x += RADIUS[k] + 8 + widest[k] + GAP if k != 'question' else RADIUS[k] + GAP + 40
    width = round(x - GAP + 24)

    tallest = max(len(v) for v in cols.values())
    height = TOP + tallest * ROW_H + 34
    for k in COLUMN:
        run = cols[k]
        # Centre each column against the tallest, so short columns do not hug the top.
        pad = (tallest - len(run)) / 2
        for i, n in enumerate(run):
            n['y'] = round(TOP + (pad + i) * ROW_H)
    for n in nodes:
        n['col'] = COLUMN.index(n['kind'])
        n['anchor'] = ANCHOR[n['kind']]
        n['font'] = FONT[n['kind']]
        n['r'] = RADIUS[n['kind']]
    nodes.append(dict(id='__canvas', kind='meta', label='', width=width, height=height,
                      columns=[dict(kind=k, x=cols[k][0]['x']) for k in COLUMN]))
    return width, height


def main():
    if not os.path.exists(DB):
        print(f'no database at {DB} -- run scripts/build_db.py', file=sys.stderr)
        return 1
    db = sqlite3.connect(DB)
    q = lambda s: db.execute(s).fetchall()

    # DERIVED: table <- extract, from the loader's own rows() calls.
    src = open(os.path.join(ROOT, 'scripts', 'build_db.py')).read()
    feeds, cur = {}, None
    for line in src.splitlines():
        m = re.search(r"rows\('([a-z0-9-]+)'\)", line)
        if m:
            cur = m.group(1)
        for t in re.findall(r'INSERT (?:OR \w+ )?INTO "?(\w+)"?', line):
            if cur:
                feeds.setdefault(t, set()).add(cur)

    tables = [r[0] for r in q("SELECT name FROM sqlite_master WHERE type='table' "
                              "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    for t in tables:                       # load_reference names the table after the CSV
        feeds.setdefault(t, {t.replace('_', '-')})

    nodes, edges = [], []
    seen = set()

    def node(nid, kind, label, **kw):
        if nid in seen:
            return nid
        seen.add(nid)
        nodes.append(dict(id=nid, kind=kind, label=label, **kw))
        return nid

    for t in tables:
        n = q(f'SELECT COUNT(*) FROM "{t}"')[0][0]
        cols = [c[1] for c in db.execute(f'PRAGMA table_info("{t}")')]
        node(f'table:{t}', 'table', t, rows=n, fields=len(cols))
        for csv in sorted(feeds.get(t, [])):
            if not os.path.exists(os.path.join(ROOT, 'sources', 'data', csv + '.csv')):
                continue
            node(f'extract:{csv}', 'extract', csv + '.csv')
            edges.append(dict(source=f'extract:{csv}', target=f'table:{t}', rel='loads into'))
            rpt = REPORT.get(csv)
            if rpt:
                node(f'report:{rpt}', 'report', rpt)
                edges.append(dict(source=f'report:{rpt}', target=f'extract:{csv}',
                                  rel='extracted from'))
        for kname, spec in KEYS.items():
            field = spec['field']
            if field and field in cols:
                node(f'key:{kname}', 'key', field, note=spec['note'])
                total = q(f'SELECT COUNT(*) FROM "{t}" WHERE "{field}" IS NOT NULL')[0][0]
                if total:
                    edges.append(dict(source=f'table:{t}', target=f'key:{kname}',
                                      rel='keyed by', rows=total))

    # Verify each bridge by intersecting the two value sets, rather than trusting that a
    # column of the same name on both sides means the sides meet. `fund` is on both and
    # shares nothing: the ledger holds enterprise funds, the school's revolving funds are
    # a different set entirely, and a diagram drawn from column names shows a join there.
    state = {}
    for kname, spec in KEYS.items():
        carried = any(e['target'] == f'key:{kname}' for e in edges)
        if spec.get('bridge'):
            a, b = spec['bridge']
            shared = q(f'SELECT COUNT(*) FROM ({a} INTERSECT {b})')[0][0]
            state[kname] = 'joins' if shared else 'disjoint'
            spec['shared'] = shared
        else:
            state[kname] = 'joins' if carried else 'none'
        node(f'key:{kname}', 'key', spec['field'] or kname, note=spec['note'],
             state=state[kname], shared=spec.get('shared'),
             missing=state[kname] != 'joins')

    for text, kname in QUESTIONS:
        st = state[kname]
        node(f'q:{text}', 'question', text, answerable=st == 'joins', state=st,
             verdict=VERDICT[st])
        edges.append(dict(source=f'q:{text}', target=f'key:{kname}', rel='needs'))

    layout(nodes, edges)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as fh:
        json.dump(dict(nodes=nodes, edges=edges), fh, indent=1)

    kinds = {}
    for n in nodes:
        kinds[n['kind']] = kinds.get(n['kind'], 0) + 1
    dead = [(n['label'], n.get('state')) for n in nodes
            if n['kind'] == 'question' and not n.get('answerable')]
    print(f'wrote {os.path.relpath(OUT, ROOT)}')
    print('  ' + ', '.join(f'{v} {k}' for k, v in sorted(kinds.items())) +
          f', {len(edges)} edges')
    print(f'  {len(dead)} question(s) that cannot be answered:')
    for label, st in dead:
        print(f'      [{st:<9}] {label}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
