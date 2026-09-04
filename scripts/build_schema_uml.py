#!/usr/bin/env python3
"""Draw the database as it actually is, not as its CREATE statements claim.

    python3 scripts/build_schema_uml.py            # writes notes/reference/data-model/schema.mmd

WHY THIS IS GENERATED AND NOT DRAWN

A hand-drawn schema diagram is out of date the first time a column is added, and nobody
notices, because a picture cannot fail a test. This reads the live database and emits
Mermaid, so the diagram is a function of the schema rather than a claim about it.

WHY IT DOES NOT ONLY READ FOREIGN KEYS

Because there are six of them, across 29 tables and 241 columns. This schema expresses
almost none of its relationships as constraints -- `budget_figure.doc_id` points at
`document` as surely as `crosswalk.doc_id` does, and only the second one says so. A
diagram of the declared keys would be an accurate drawing of six edges and a false
picture of the database.

So relationships come from two places and are drawn differently:

  DECLARED   a real FOREIGN KEY. The schema asserts it.
  VERIFIED   a column that carries the same name as another table's primary key, whose
             values were CHECKED against it by running the join. The match rate is on
             the edge, because "there is a doc_id column" and "every doc_id resolves"
             are different facts and only the second is worth drawing.

A candidate that matches nothing is not drawn at all -- a same-named column that never
resolves is a coincidence, and an edge for it would be a lie in the shape of a line.
"""
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
OUT = os.path.join(ROOT, 'notes', 'reference', 'data-model', 'schema.mmd')

# Joins this project relies on that no constraint expresses. The last one is the join
# between the district's budget and the town's books, and it is a SUBSTRING match on a
# label rather than a key, which is exactly why it is worth drawing as its own kind.
CONVENTIONS = [
    ('doc_id',     'document',       'doc_id',         '='),
    ('line_key',   'budget_line',    'line_key',       '='),
    ('account_id', 'account',        'account_id',     '='),
    ('fund',       'fund',           'fund',           '='),
    ('period',     'fiscal_period',  'period',         '='),
    ('function',   'budget_line',    'function_group', 'prefix'),
]


def main():
    if not os.path.exists(DB):
        print(f'no database at {DB} -- run scripts/build_db.py', file=sys.stderr)
        return 1
    db = sqlite3.connect(DB)
    q = lambda s, *a: db.execute(s, a).fetchall()

    tables = [r[0] for r in q("SELECT name FROM sqlite_master WHERE type='table' "
                              "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    cols = {t: list(db.execute(f'PRAGMA table_info("{t}")')) for t in tables}
    counts = {t: q(f'SELECT COUNT(*) FROM "{t}"')[0][0] for t in tables}

    declared, edges = set(), []
    for t in tables:
        for fk in db.execute(f'PRAGMA foreign_key_list("{t}")'):
            declared.add((t, fk[3], fk[2]))
            edges.append((t, fk[2], fk[3], 'declared', None))

    # Verify the conventions by running each join rather than trusting the column name.
    for t in tables:
        names = [c[1] for c in cols[t]]
        for col, target, tcol, kind in CONVENTIONS:
            if t == target or col not in names:
                continue
            if (t, col, target) in declared:
                continue
            total = q(f'SELECT COUNT(*) FROM "{t}" WHERE "{col}" IS NOT NULL')[0][0]
            if not total:
                continue
            if kind == '=':
                hit = q(f'SELECT COUNT(*) FROM "{t}" a JOIN "{target}" b '
                        f'ON b."{tcol}" = a."{col}"')[0][0]
            else:
                hit = q(f'SELECT COUNT(*) FROM "{t}" a WHERE EXISTS ('
                        f'SELECT 1 FROM "{target}" b WHERE substr(b."{tcol}",1,4) = a."{col}")')[0][0]
            if hit:
                edges.append((t, target, col, 'verified', f'{hit:,}/{total:,}'))

    TYPE = {'INTEGER': 'int', 'REAL': 'real', 'TEXT': 'text'}
    out = ['erDiagram']
    for a, b, col, kind, rate in sorted(edges):
        # many-to-one in every case here: a fact row points at one row of a dimension.
        label = col if kind == 'declared' else f'{col} {rate}'
        out.append(f'    {b.upper()} ||--o{{ {a.upper()} : "{label}"')
    for t in tables:
        out.append(f'    {t.upper()} {{')
        pk = [c[1] for c in cols[t] if c[5]]
        fkcols = {e[2] for e in edges if e[0] == t}
        for c in cols[t]:
            typ = TYPE.get((c[2] or '').upper().split('(')[0], 'text')
            tag = 'PK' if c[1] in pk else ('FK' if c[1] in fkcols else '')
            out.append(f'        {typ} {c[1]}{" " + tag if tag else ""}')
        out.append(f'        %% {counts[t]:,} rows')
        out.append('    }')

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as fh:
        fh.write('\n'.join(out) + '\n')
    dec = sum(1 for e in edges if e[3] == 'declared')
    print(f'wrote {os.path.relpath(OUT, ROOT)}')
    print(f'  {len(tables)} tables, {sum(len(c) for c in cols.values())} columns')
    print(f'  {len(edges)} relationships: {dec} declared as foreign keys, '
          f'{len(edges) - dec} verified by running the join')
    return 0


if __name__ == '__main__':
    sys.exit(main())
