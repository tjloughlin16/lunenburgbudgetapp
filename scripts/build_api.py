"""Publish the analysis database as a read-only API, for people and for agents.

    python3 scripts/build_db.py && python3 scripts/build_api.py

Writes `fy28/public/api/*.json` and `fy28/public/data/lunenburg.db`.

This is layer 0 and layer 1 of the API: the database itself, downloadable, and a set of
named resources at stable addresses. There is no computation per request and nothing to
rate limit, because every answer is a file. `/api/query` over D1 comes later and slots in
behind the same `/api/` prefix, so no address published here has to change.

---------------------------------------------------------------------------------------
WHY THE SHAPE IS WHAT IT IS
---------------------------------------------------------------------------------------

The consumer is increasingly an agent rather than a person with a scraper, and an agent
fails differently. It will not read a caveat on a web page, it will happily join two
tables that must not be joined, and it will state the result with total confidence. So:

*   **Every resource carries `provenance`.** The documents behind the rows, with their
    URL and sha256. A figure returned without its address is rule 13 in API form -- the
    derived thing quoted as though observed -- and the fix is to make the address
    impossible to drop.

*   **`/api/schema` teaches rather than lists.** Column names are the least useful thing
    to publish. What a caller needs is the GRAIN of each table, the sign convention on
    revenue, the rounded appropriation columns, and the fact that the crosswalk is empty.
    Those are the four ways to get a confident wrong answer out of this database.

*   **The safe path is the easy path.** Named resources exist so that the common
    questions never require anybody to write a join. A caller who has to write SQL to ask
    "how did this line move" is a caller who will eventually write the wrong SQL.

*   **`caveats` travels with the data, not beside it.** Each resource names, in-band, the
    specific ways its own rows get misread.

Everything here is generated. Nothing is hand-maintained, so it cannot drift from the
database it describes.
"""
import glob
import hashlib
import json
import os
import shutil
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
PUB = os.path.join(ROOT, 'fy28', 'public')
API = os.path.join(PUB, 'api')
SITE = 'https://lunenburgbudgetproject.org'

# What each table is, at what grain, and the specific way its rows get misread. This is
# the part of the schema that is worth publishing; the column list is derivable.
TABLES = {
    'ledger_snapshot': dict(
        grain='one row per account, fiscal year, PERIOD and document',
        what='The town\'s own books, from the MUNIS year-to-date budget report. Period 13 '
             'is the year-end close, after purchase orders are closed in the lapse period.',
        caveats=[
            'The surplus for a closed year IS the `available` column at period 13.',
            '`transfers` is CUMULATIVE, not incremental. Movement between two periods is '
            'the difference of the column, never the later value.',
            '`original`, `transfers` and `revised` are printed rounded to whole dollars '
            'while `expended`, `encumbered` and `available` carry cents. A single row '
            'therefore does not reconcile to itself by a few pence, and a sum of N rows '
            'cannot equal a printed grand total exactly. Allow one dollar per row.',
            'Revenue rows are stored NEGATIVE, exactly as MUNIS prints them. Check '
            '`account.account_type` before doing arithmetic across account types.',
        ]),
    'budget_figure': dict(
        grain='one row per budget line, fiscal year, STAGE and document',
        what='What a budget document said a line would be, or was. Stage is proposed, '
             'settled or actual.',
        caveats=[
            'A STAGE IS NOT A PERIOD. There is no join between this table and '
            '`ledger_snapshot` and nothing should invent one.',
            'An "actual" here is a RESTATEMENT: a prior year re-presented by the people '
            'who spent it, inside the argument for the next budget. It is not a ledger '
            'figure.',
            'These lines do NOT sum back to the district totals -- between 0.1% and 1.6% '
            'out. Never apportion a total across them.',
            '`documents_disagree` marks a figure two documents state differently. The '
            'documents disagree with themselves by up to 1.5%, which is larger than most '
            'variances anybody wants to measure.',
            'FY2021 is unusable: 117 of 120 lines print the budget under an "actual" '
            'heading. Exclude it.',
        ]),
    'workbook_figure': dict(
        grain='one row per worksheet row, fiscal year and COLUMN, from one workbook',
        what='The FY27 projection workbook, unpivoted. The only source holding both '
             'halves of FY25.',
        caveats=[
            'Filter `row_kind = \'line\'`. The sheet\'s own TOTAL rows are loaded too, so '
            'that a line sum can be reconciled to the total the source itself prints; '
            'summing without the filter double-counts by roughly 4x.',
            'Every file in the archive carrying FY25 actuals is this same workbook saved '
            'four times. Two of them agreeing is not corroboration.',
        ]),
    'account': dict(
        grain='one row per ledger account',
        what='The conformed dimension. Both revenue and expense, every fund.',
        caveats=[
            '`level` says what we hold. `department` means the report was a rollup and '
            'the whole school district is one row (`0100-300`). `account` means full GL '
            'detail.',
            'As of 2 September 2026 the general fund REVENUE report is at account level '
            'and the EXPENDITURE report is not. Every dollar coming in is visible per '
            'account; the schools\' spending is one row.',
        ]),
    'crosswalk': dict(
        grain='one row per budget line mapped to a ledger account',
        what='EMPTY, and that is the honest state rather than an oversight.',
        caveats=[
            'District budget lines are NAMED; MUNIS rows are CODED; the workbook\'s '
            'function-group codes appear nowhere in the MUNIS report. Three code spaces, '
            'none shared, and no published document maps one to another.',
            'Therefore NO budget line can currently be traced into an actual in the '
            'ledger. Any answer claiming otherwise is wrong.',
        ]),
    'fund_activity': dict(
        grain='one row per fund, fiscal year, period and document',
        what='What a revolving, grant or gift fund took in, spent and carried.',
        caveats=[
            'A FUND BALANCE ROLLS FORWARD. A DEPARTMENT APPROPRIATION LAPSES. They are '
            'printed in the same units and are not the same quantity. Never union this '
            'table with `ledger_snapshot`.',
        ]),
    'grant_award': dict(
        grain='one row per grant per fiscal year',
        what='What a budget document says was awarded.',
        caveats=[
            'This is NOT a mapping onto the operating lines a grant paid for. Nobody '
            'publishes that. The Town\'s statement of 1 September 2026 -- that about '
            '$287,000 of out-of-district tuition was charged to the FY26 IDEA grant '
            'rather than the operating budget -- is the first instance of it being named '
            'at all.',
        ]),
    'document': dict(
        grain='one row per source document',
        what='Provenance. Where a document came from, what produced its figures, and '
             'whether our copy still matches the publisher\'s.',
        caveats=[
            '`basis` is what produced the figures: ledger, restatement, forward budget, '
            'or narrative. Of the ledger documents, exactly one reaches school budget '
            'lines.',
            '`hidden_columns` records what a reader opening the file does NOT see. Two '
            'copies of one workbook hide different columns, so "the workbook contains '
            'FY23 actuals" and "there is no FY23 column" were both true at once.',
        ]),
    'fund': dict(grain='one row per fund', what='Funds and their restrictions.',
                caveats=['A general fund line is NET of whatever a grant, fee or '
                         'revolving fund already paid for the thing.']),
    'budget_line': dict(grain='one row per named budget line',
                        what='Lines as the district\'s documents name them.',
                        caveats=['No account code: the documents do not print one.']),
    'fiscal_period': dict(grain='one row per accounting period',
                          what='Named periods. 13 is the year-end close.', caveats=[]),
}

# The four ways to get a confident wrong answer out of this database, stated once at the
# top of the schema because a caller who reads nothing else may read this.
READ_FIRST = [
    'Never mix a BUDGET with an ACTUAL in one calculation. They differ by up to 59% on '
    'some lines, and a growth rate measured from one to the other is partly growth and '
    'partly the step between them.',
    'A budget line is NET -- what the town must raise after grants, fees and state aid. '
    'It is not what the thing costs. A line can rise because a grant ended and no cost '
    'changed at all.',
    'A STAGE (proposed / settled / actual) is not a PERIOD (1-13). `budget_figure` and '
    '`ledger_snapshot` do not join, and joining them produces a plausible wrong number.',
    'NO budget line is mapped to a ledger account. The crosswalk table is empty on '
    'purpose. Budget-to-actual at line level cannot be answered from this database yet.',
]


def q(db, sql, *a):
    db.row_factory = sqlite3.Row
    return [dict(r) for r in db.execute(sql, a).fetchall()]


_DOCS = None


def _doc_index(db):
    """doc_id -> document row, resolvable by full path OR by bare filename.

    `budget_figure.doc_id` carries the filename a document was read under
    (`fy24-approved-budget.txt`) while `document.doc_id` is the archive path. All 20 of
    them resolve by basename and none resolves exactly, so a straight IN () lookup
    returned NOTHING and every per-line file shipped with an empty provenance block --
    the one guarantee this API makes, quietly broken. Hence the basename fallback, and
    hence `unresolved` below rather than a silent empty list.
    """
    global _DOCS
    if _DOCS is None:
        rows = q(db, """SELECT doc_id, path, basis, url, copy_state,
                               local_sha256 AS sha256 FROM document""")
        _DOCS = {}
        for r in rows:
            _DOCS[r['doc_id']] = r
            _DOCS.setdefault(os.path.basename(r['path'] or r['doc_id']), r)
    return _DOCS


def provenance(db, doc_ids):
    """The documents behind a result, with the address and the bytes.

    Returns a dict rather than a list so that a document we cannot resolve is REPORTED
    rather than omitted. An address quietly missing is worse than an address known to be
    missing, and this is the exact place that distinction gets lost.
    """
    idx = _doc_index(db)
    ids = sorted({d for d in doc_ids if d})
    found, missing = [], []
    for i in ids:
        r = idx.get(i)
        if r:
            found.append(dict(r, cited_as=i))
        else:
            missing.append(i)
    out = dict(documents=found, count=len(found))
    if missing:
        out['unresolved'] = missing
        out['warning'] = ('These figures cite a document not present in the document '
                          'table, so no address can be given for them. Treat any figure '
                          'resting on them as uncheckable.')
    return out


def write(name, payload):
    path = os.path.join(API, name + '.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, separators=(',', ':'))
    return os.path.getsize(path)


def resource(db, name, rows, doc_field='doc_id', caveats=(), about=''):
    """One published resource: the rows, what they are, and where they came from."""
    return dict(
        resource=name, about=about, count=len(rows),
        caveats=list(caveats),
        provenance=provenance(db, [r.get(doc_field) for r in rows]),
        rows=rows,
    )


def slug(key):
    """A filename an agent can construct from a line_key without guessing."""
    out = ''.join(c if (c.isalnum() or c in '-_') else '-' for c in key.lower())
    while '--' in out:
        out = out.replace('--', '-')
    return out.strip('-')[:80] or 'line'


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()



# Every table in the database, fetchable. Not just the eight with a hand-written resource.
#
# An agent asked what this project holds on paraprofessionals, read `/api/index`, found
# eight endpoints and none of them about staffing, and concluded "none of it holds
# headcount". It was wrong: `staff_roster_entries` has 3,815 rows. The schema even named
# the table -- in a row-count map, with no grain, no caveats and no address. A table an
# agent can see the size of and cannot fetch is worse than one it cannot see at all,
# because it looks like a dead end rather than a missing feature.
#
# So every table is published. Large ones are split by fiscal year rather than truncated,
# because the alternative -- a 3 MB blob -- is a resource nobody can afford to fetch, and
# this API already learned that with the budget lines.
# Caveats for tables that have no hand-written entry in TABLES but need one anyway.
EXTRA_CAVEATS = {
    'staff_roster_entries': ['POSITION IS OUR CLASSIFICATION AND IT FAILS IN SOME YEARS. It is mapped from the printed job title, and the print changes: FY2012 says "Tutor", FY2013 "Aide", FY2014 "Paraprofessional" — and once "Paraprotessional", an OCR typo that drops that person from the count. FY2015 printed the page in two columns, which the extractor collapsed, leaving five people with no title at all. So a series counting paraprofessionals in the Kindergarten section reads 0, 5, 4, 4, 0 for FY2011–FY2015 across roughly the same five people. THE ZEROS ARE EXTRACTION FAILURES, NOT STAFFING. Found by an assistant reading the rows, not by any check here. Use `role_raw`, which is what the report actually printed, before trusting `position`.'],
}

SHARD_ABOVE = 400 * 1024
YEAR_COLUMNS = ('fy', 'fiscal_year', 'edition', 'year')


def year_column(cols):
    for c in YEAR_COLUMNS:
        if c in cols:
            return c
    return None


def publish_tables(db, written, already):
    """Publish every table that has no hand-written resource of its own."""
    names = [t for (t,) in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    listed = []
    for name in names:
        if name in already:
            continue
        cols = [c[1] for c in db.execute('PRAGMA table_info("%s")' % name)]
        rows = q(db, 'SELECT * FROM "%s"' % name)
        doc_field = 'doc_id' if 'doc_id' in cols else (
            'document' if 'document' in cols else None)
        meta = TABLES.get(name, {})
        about = meta.get('what') or (
            f'The `{name}` table, published whole. See /api/schema for its grain.')
        caveats = list(meta.get('caveats', ())) + EXTRA_CAVEATS.get(name, [])

        def payload(rs, note=''):
            body = resource(db, name, rs, doc_field=doc_field or 'doc_id',
                            caveats=caveats, about=about + note)
            body['columns'] = cols
            body['source'] = f'{SITE}/docs/data/{name.replace("_", "-")}.csv'
            return body

        whole = payload(rows)
        size = len(json.dumps(whole, separators=(',', ':')))
        yc = year_column(cols)
        if size <= SHARD_ABOVE or not yc:
            written['api/' + name] = write(name, whole)
            listed.append(dict(url=f'{SITE}/api/{name}', rows=len(rows),
                               bytes=written['api/' + name]))
            continue

        # Too large to hand to a caller in one piece: an index plus one file per year.
        by_year = {}
        for r in rows:
            by_year.setdefault(str(r.get(yc) or 'undated'), []).append(r)
        parts = []
        for yr, rs in sorted(by_year.items()):
            key = f'{name}/{yr}'
            written['api/' + key] = write(key, payload(
                rs, f' This file is {yc} {yr} only.'))
            parts.append(dict(url=f'{SITE}/api/{key}', **{yc: yr},
                              rows=len(rs), bytes=written['api/' + key]))
        idx = dict(resource=name, about=about, count=len(rows), columns=cols,
                   caveats=caveats,
                   note=f'{len(rows):,} rows is more than one fetch should carry, so this '
                        f'is an index. Each file below is one {yc}.',
                   source=f'{SITE}/docs/data/{name.replace("_", "-")}.csv',
                   parts=parts)
        written['api/' + name] = write(name, idx)
        listed.append(dict(url=f'{SITE}/api/{name}', rows=len(rows),
                           bytes=written['api/' + name], splitBy=yc, parts=len(parts)))
    return listed


def main():
    if not os.path.exists(DB):
        print('no database; run scripts/build_db.py first')
        return 1
    db = sqlite3.connect(DB)
    written = {}

    # ---- layer 0: the database itself, downloadable, with its bytes named ------------
    pub_db = os.path.join(PUB, 'data', 'lunenburg.db')
    os.makedirs(os.path.dirname(pub_db), exist_ok=True)
    shutil.copyfile(DB, pub_db)
    digest = sha256_of(pub_db)

    counts = {t: db.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0]
              for (t,) in db.execute(
                  "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}
    views = [v for (v,) in db.execute(
        "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")]

    written['data/lunenburg.db'] = os.path.getsize(pub_db)

    # ---- layer 1: named resources ---------------------------------------------------
    written['api/schema'] = write('schema', dict(
        about='The Lunenburg budget analysis database. Read `readFirst` before computing '
              'anything.',
        readFirst=READ_FIRST,
        rebuiltFrom='The CSVs in sources/data/ are the source of truth. This database is '
                    'a derived read model, dropped and rebuilt from scratch on every run. '
                    'Nothing is ever edited in it.',
        download=dict(url=f'{SITE}/data/lunenburg.db', sha256=digest,
                      bytes=os.path.getsize(pub_db), format='SQLite 3',
                      note='The whole database. Query it yourself; it is the same file '
                           'every figure below comes from.'),
        tables={name: dict(
            rows=counts.get(name, 0),
            grain=meta['grain'], what=meta['what'], caveats=meta['caveats'],
            columns=[c[1] for c in db.execute('PRAGMA table_info("%s")' % name)])
            for name, meta in TABLES.items() if name in counts},
        otherTables={t: counts[t] for t in counts if t not in TABLES},
        views=views,
        license='Public documents, republished. Cite the document, not this API.',
    ))

    written['api/coverage'] = write('coverage', dict(
        resource='coverage',
        about='What this project holds for each fiscal year, derived from the database '
              'rather than from a maintained list. An empty cell is a real gap.',
        caveats=['`partial` on a ledger row means the report was a DEPARTMENT ROLLUP -- '
                 'the whole school district is one row -- so it cannot be traced to a '
                 'budget line.'],
        rows=q(db, """SELECT l.fy, l.period, a.account_type, a.level,
                             COUNT(*) rows, COUNT(DISTINCT l.doc_id) documents
                      FROM ledger_snapshot l JOIN account a USING (account_id)
                      GROUP BY l.fy, l.period, a.account_type, a.level
                      ORDER BY l.fy, l.period"""),
        stages=q(db, """SELECT fy, stage, COUNT(*) rows,
                               COUNT(DISTINCT doc_id) documents,
                               SUM(documents_disagree) disagreeing
                        FROM budget_figure GROUP BY fy, stage ORDER BY fy, stage"""),
    ))

    written['api/ledger'] = write('ledger', resource(
        db, 'ledger',
        q(db, """SELECT a.fund, f.name fund_name, a.dept, a.org, a.object, a.name,
                        a.account_type, a.level, l.fy, l.period,
                        l.original, l.transfers, l.revised, l.expended, l.encumbered,
                        l.available, l.pct_used, l.rounded_columns, l.doc_id
                 FROM ledger_snapshot l JOIN account a USING (account_id)
                      LEFT JOIN fund f ON f.fund = a.fund
                 ORDER BY a.fund, a.dept, a.org, a.object"""),
        caveats=TABLES['ledger_snapshot']['caveats'],
        about='The town\'s books. Every account, every period we hold.'))

    # Lines are published as an INDEX plus one file per line, not as a single 1.6 MB
    # blob. The consumer is an agent with a context window: a resource nobody can afford
    # to fetch is not published, it is merely present. Discover here, then fetch one.
    all_lines = q(db, """SELECT line_key, label, fy, stage, value, documents_disagree,
                                doc_id
                         FROM budget_figure ORDER BY line_key, fy, stage""")
    meta = {r['line_key']: r for r in q(
        db, 'SELECT line_key, label, section, function_group FROM budget_line')}
    by_line = {}
    for r in all_lines:
        by_line.setdefault(r['line_key'], []).append(r)

    index, taken = [], {}
    for key in sorted(by_line):
        sl = slug(key)
        # Two different keys must never collide onto one file.
        if sl in taken:
            n = taken[sl] = taken[sl] + 1
            sl = '%s-%d' % (sl, n)
        else:
            taken[sl] = 1
        rows_ = by_line[key]
        m = meta.get(key, {})
        years = sorted({r['fy'] for r in rows_})
        index.append(dict(
            line_key=key, label=m.get('label') or rows_[0]['label'] or key,
            function_group=m.get('function_group'), section=m.get('section'),
            first_fy=years[0], last_fy=years[-1], years=len(years),
            figures=len(rows_),
            stages=sorted({r['stage'] for r in rows_}),
            url=f'{SITE}/api/lines/{sl}'))
        write('lines/' + sl, resource(
            db, 'lines/' + sl, rows_,
            caveats=TABLES['budget_figure']['caveats'],
            about='One budget line, every year and stage a document states it.'))

    # A line that stops existing must stop being published. These files are written one
    # per line and nothing ever removed them, so a key that disappeared -- because a
    # parsing fix stopped inventing it, or because a document was re-read -- left a live
    # endpoint serving figures the database no longer holds. Two of them were budget
    # lines called `all-federal-grants-offsets-applied-revolving-account-...`, read out
    # of a prose paragraph. An endpoint nobody can get to is unreachable; an endpoint
    # that answers with a retired figure is worse.
    live = set(taken) | {'%s-%d' % (k, n) for k, c in taken.items()
                         for n in range(2, c + 1)}
    removed = 0
    for f in glob.glob(os.path.join(API, 'lines', '*.json')):
        if os.path.basename(f)[:-5] not in live:
            os.remove(f)
            removed += 1
    if removed:
        print('  removed %d retired line endpoint(s)' % removed)

    written['api/lines'] = write('lines', dict(
        resource='lines',
        about='Index of the budget lines the district\'s BUDGET DOCUMENTS name. Fetch a '
              'line\'s `url` for its figures; the full set is deliberately not published '
              'as one file, because a resource nobody can afford to fetch is not '
              'published. NOTE: this is not every line in the archive. The FY27 workbook '
              'names lines the documents do not, and only 48 names appear in both; those '
              'lines are reachable through /api/workbook. The two are not merged on a '
              'name match, which would be a guess wearing a join\'s clothes.',
        caveats=TABLES['budget_figure']['caveats'],
        count=len(index), figures=len(all_lines), rows=index))

    # The workbook is split by fiscal year for the same reason.
    wb_years = [r['fy'] for r in q(
        db, 'SELECT DISTINCT fy FROM workbook_figure ORDER BY fy')]
    for fy in wb_years:
        write('workbook/fy%d' % fy, resource(
            db, 'workbook/fy%d' % fy,
            q(db, """SELECT row, line_key, fy, column_kind, value, row_kind, doc_id
                     FROM workbook_figure WHERE fy=? ORDER BY row""", fy),
            caveats=TABLES['workbook_figure']['caveats'],
            about='The FY27 projection workbook for one fiscal year, cell-quotable.'))
    written['api/workbook'] = write('workbook', dict(
        resource='workbook',
        about='The FY27 projection workbook, unpivoted, one file per fiscal year.',
        caveats=TABLES['workbook_figure']['caveats'],
        rows=[dict(fy=fy, url=f'{SITE}/api/workbook/fy{fy}') for fy in wb_years]))

    written['api/totals'] = write('totals', dict(
        resource='totals',
        about='Whole-year budget against actual, from the one source printing both.',
        caveats=['These are RESTATEMENTS. The town\'s own closing figure for FY25 is '
                 '$603,885.97, arrived at by closing the books rather than by subtracting '
                 'two columns, and it is the better number to quote.',
                 'A year with only one half produces no variance and none is shown.'],
        rows=q(db, """SELECT fy,
                        SUM(CASE WHEN column_kind IN ('budget','final_budget')
                                 THEN value END) budget,
                        SUM(CASE WHEN column_kind='actual' THEN value END) actual,
                        SUM(CASE WHEN column_kind='actual_to_date' THEN value END)
                            actual_to_date,
                        SUM(CASE WHEN column_kind='encumbered_to_date' THEN value END)
                            encumbered_to_date
                      FROM workbook_figure WHERE row_kind='line'
                      GROUP BY fy ORDER BY fy"""),
    ))

    written['api/funding'] = write('funding', dict(
        resource='funding',
        about='Where the money comes from: revenue, transfers between funds, and the '
              'revolving and grant funds beside the operating budget.',
        caveats=['Revenue in `revenue` is sign-corrected to read as an inflow. In the '
                 'underlying `ledger_snapshot` table it is stored NEGATIVE, as MUNIS '
                 'prints it.',
                 'A fund balance rolls forward; an appropriation lapses. Do not add them.'],
        revenue=q(db, 'SELECT * FROM v_revenue ORDER BY budgeted DESC'),
        interfund=q(db, 'SELECT * FROM v_interfund'),
        stateAid=q(db, 'SELECT * FROM v_state_aid'),
        funds=q(db, 'SELECT * FROM v_fund_year ORDER BY closing_balance DESC'),
        grants=q(db, 'SELECT * FROM grant_award ORDER BY fy, name'),
    ))

    written['api/documents'] = write('documents', dict(
        resource='documents',
        about='Every source document: what produced its figures, where it lives, and '
              'whether our copy still matches the publisher\'s.',
        caveats=TABLES['document']['caveats'],
        rows=q(db, """SELECT doc_id, path, source_type, basis, ledger_at, hidden_columns,
                             url, link_state, copy_state, local_sha256, remote_sha256
                      FROM document ORDER BY path"""),
    ))

    # Everything else in the database, fetchable rather than merely named.
    curated = {'ledger_snapshot', 'budget_figure', 'account', 'fund', 'document',
               'budget_line', 'workbook_figure', 'fiscal_period', 'crosswalk',
               'fund_activity', 'grant_award'}
    tables_listed = publish_tables(db, written, curated)
    written['api/tables'] = write('tables', dict(
        resource='tables',
        about='Every dataset in this project, fetchable. One entry per table in the '
              'database, with its size in bytes so a caller can decide before fetching. '
              'The curated endpoints in /api/index are joins and roll-ups over these; '
              'this is the raw grain.',
        note='A table larger than 400KB is published as an index plus one file per '
             'fiscal year rather than as one blob.',
        count=len(tables_listed),
        tables=sorted(tables_listed, key=lambda t: t['url']),
    ))

    # The index goes last so it can report the real sizes.
    endpoints = [
        dict(url=f'{SITE}/api/schema', about='Read this first. Grain, conventions, and '
             'the four ways to get a confident wrong answer.'),
        dict(url=f'{SITE}/api/coverage', about='What we hold for each fiscal year.'),
        dict(url=f'{SITE}/api/ledger', about='The town\'s books, every account and period.'),
        dict(url=f'{SITE}/api/lines', about='Index of every budget line. Each row '
             'carries the URL of that one line\'s figures.'),
        dict(url=f'{SITE}/api/workbook', about='The FY27 workbook, one file per year.'),
        dict(url=f'{SITE}/api/totals', about='Whole-year budget against actual.'),
        dict(url=f'{SITE}/api/funding', about='Revenue, transfers, funds and grants.'),
        dict(url=f'{SITE}/api/documents', about='Provenance for every source.'),
        dict(url=f'{SITE}/api/tables', about='EVERY dataset in the project, fetchable, '
             'with its size. Staff rosters, placement counts, annual-report extracts — '
             'the raw grain the endpoints above are built from.'),
        dict(url=f'{SITE}/data/lunenburg.db', about='The whole database, SQLite. '
             f'sha256 {digest}.'),
    ]
    for e in endpoints:
        key = 'api/' + e['url'].rsplit('/', 1)[1] if '/api/' in e['url'] \
            else 'data/lunenburg.db'
        e['bytes'] = written.get(key)

    written['api/index'] = write('index', dict(
        api='Lunenburg Budget Project — read-only data API',
        about='An independent archive of the Lunenburg, Massachusetts town and school '
              'budget. Everything here is derived from documents the town and district '
              'published, and every row can be traced back to one.',
        readFirst=READ_FIRST,
        endpoints=endpoints,
        format='Static JSON. No authentication, no rate limit, nothing computed per '
               'request. Cache freely. Every endpoint states its own size in `bytes` so '
               'a caller can decide before fetching; nothing here exceeds 200 KB except '
               'the database download itself.',
        generatedFrom='scripts/build_api.py, from sources/data/lunenburg.db',
        alsoSee={
            'llms.txt': f'{SITE}/llms.txt',
            'method': f'{SITE}/docs/analyses/show-your-work.md',
            'schemaNotes': 'notes/reference/SCHEMA.md in the repository',
        },
        contact=f'{SITE}/sources',
    ))

    # ---- layer 3: the two addresses an agent probes before asking anything ----------
    #
    # `/openapi.json` and `/.well-known/ai-plugin.json` are what a program fetches to find
    # out whether a site has an API at all. Both returned 261KB of the app shell with a
    # 200 -- the soft 404 that `functions/_notfound.js` was written against, sitting just
    # outside the three prefixes it covers. An agent that asks the standard question gets
    # HTML, and either throws or, worse, parses something.
    #
    # They are answered properly rather than 404'd, because there IS an API and this is
    # where a caller looks for it.
    paths = {}
    for e in endpoints:
        if '/api/' not in e['url']:
            continue
        p_ = e['url'].split('lunenburgbudgetproject.org', 1)[1]
        paths[p_] = {'get': {
            'summary': e['about'],
            'responses': {'200': {
                'description': f"{e.get('bytes') or 0} bytes of JSON",
                'content': {'application/json': {'schema': {'type': 'object'}}}}}}}
    for t in tables_listed:
        p_ = t['url'].split('lunenburgbudgetproject.org', 1)[1]
        note = (f"{t['rows']:,} rows, split by {t['splitBy']} into {t['parts']} files"
                if t.get('splitBy') else f"{t['rows']:,} rows")
        paths[p_] = {'get': {
            'summary': f'The `{p_.rsplit("/", 1)[1]}` table. {note}.',
            'responses': {'200': {
                'description': f"{t['bytes']} bytes of JSON",
                'content': {'application/json': {'schema': {'type': 'object'}}}}}}}

    written['api/openapi'] = write('openapi', dict({
        'openapi': '3.1.0',
        'info': dict(
            title='Lunenburg Budget Project — read-only data API',
            version=UPDATED if 'UPDATED' in globals() else '1',
            description='An independent archive of the Lunenburg, Massachusetts town and '
                        'school budget. Static JSON, no authentication, no rate limit, '
                        'nothing computed per request. Read /api/schema before computing '
                        'anything: it states the grain of every table and the specific '
                        'ways to get a confident wrong answer out of this data.'),
        'servers': [dict(url=SITE)],
        'paths': paths,
    }))
    shutil.copyfile(os.path.join(API, 'openapi.json'),
                    os.path.join(PUB, 'openapi.json'))
    written['openapi.json'] = os.path.getsize(os.path.join(PUB, 'openapi.json'))

    wk = os.path.join(PUB, '.well-known')
    os.makedirs(wk, exist_ok=True)
    with open(os.path.join(wk, 'ai-plugin.json'), 'w', encoding='utf-8') as fh:
        json.dump(dict(
            schema_version='v1',
            name_for_human='Lunenburg Budget Project',
            name_for_model='lunenburg_budget',
            description_for_human='An independent, checkable archive of the Lunenburg, '
                                  'Massachusetts town and school budget.',
            description_for_model='Read ' + SITE + '/llms.txt first — it is written for '
                                  'you and states what this archive holds and what it '
                                  'does not. Every dataset is fetchable at '
                                  + SITE + '/api/tables, sized so you can decide before '
                                  'asking. Every figure traces to a published document '
                                  'with a URL and a sha256.',
            api=dict(type='openapi', url=f'{SITE}/openapi.json'),
            guide=f'{SITE}/llms.txt',
            index=f'{SITE}/api/index',
            contact_email=None,
            legal_info_url=f'{SITE}/sources',
        ), fh, indent=1)
    written['.well-known/ai-plugin.json'] = os.path.getsize(
        os.path.join(wk, 'ai-plugin.json'))

    print('Published the database as an API\n')
    for k in sorted(written):
        print('  %-24s %8.1f KB' % (k, written[k] / 1024))
    print('\n  sha256(lunenburg.db) = %s' % digest)
    return 0


if __name__ == '__main__':
    sys.exit(main())
