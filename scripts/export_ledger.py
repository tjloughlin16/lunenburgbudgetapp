"""Export the ledger page's data from the analysis database.

The app reads JSON, not SQLite, so this is the same shape of step as `model/export.py`:
one file, computed from the database, regenerated after any change to the data.

    python3 scripts/build_db.py && python3 scripts/export_ledger.py

Writes `fy28/public/data/ledger.json`, fetched at runtime by the data room page.

Three things this file is careful about, all of them rule 13:

*   **Completeness is derived, never asserted.** The coverage matrix does not read a
    hand-written list of what we have. It asks the database what is present for each
    fiscal year and reports the answer, so a document that gets added shows up without
    anybody remembering to tick a box, and one that is missing cannot be quietly marked
    present.

*   **`partial` is a state.** We hold FY26 Q3 as a DEPARTMENT ROLLUP -- the whole district
    is one row. Marking that cell `obtained` would say we can trace a line into it, and we
    cannot. A rollup and a line-level report are not the same document.

*   **Budget and actual are only compared when they came from the same document.** The
    per-line series carries the document behind each half, and a year where they differ is
    flagged rather than silently subtracted.
"""
import json
import os
import sqlite3
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
# public/, not src/: this is fetched at runtime rather than bundled. Half a megabyte of
# ledger has no business in the main bundle of a page nobody else reads, and keeping it
# out means the data room is not prerendered into a static file either.
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'ledger.json')

# What a fiscal year needs before any of the questions on that page can be answered for
# it. This is the STANDARD -- the same rows for every year -- and the point of publishing
# it is that the empty cells are the argument.
ROW_DEFS = [
    dict(id='proposed', group='Budget documents', label='Proposed budget, line level',
         why='The superintendent’s request. Establishes what was asked for.'),
    dict(id='settled', group='Budget documents', label='Approved budget, line level',
         why='What the School Committee and Town Meeting settled on. The base every rate is measured from.'),
    dict(id='restated', group='Budget documents', label='Prior-year actuals, restated',
         why='A later budget document re-presenting the year. A restatement, not a ledger.'),
    dict(id='approp', group='The town’s ledger', label='Appropriation as voted',
         why='MUNIS original appropriation. What Town Meeting actually voted, before transfers.'),
    dict(id='q1', group='The town’s ledger', label='Q1 spend report (period 3)',
         why='First quarter. Needed for the seasonal baseline that makes a burn rate mean anything.'),
    dict(id='q2', group='The town’s ledger', label='Q2 spend report (period 6)',
         why='Half year.'),
    dict(id='q3', group='The town’s ledger', label='Q3 spend report (period 9)',
         why='Three quarters. The last point at which a surplus could still be redirected.'),
    dict(id='q4', group='The town’s ledger', label='Year-end close (period 13)',
         why='After the lapse period. The surplus IS the available column on this report.'),
    dict(id='po', group='The town’s ledger', label='Purchase orders closed after close',
         why='The step that moved FY25 from $582,115.44 to $603,885.97. Not recoverable from one report run.'),
    dict(id='revenue', group='Funding sources', label='Revenue ledger',
         why='Chapter 70, local receipts, and transfers in. The expense side cannot see any of it.'),
    dict(id='funds', group='Funding sources', label='Revolving and grant fund activity',
         why='What the general fund line is net OF. Rule 11.'),
    dict(id='grants', group='Funding sources', label='Grant awards listed',
         why='What was awarded. Not a mapping onto the lines a grant paid for -- nobody publishes that.'),
]


def rows(db, sql, *args):
    db.row_factory = sqlite3.Row
    return [dict(r) for r in db.execute(sql, args).fetchall()]


def coverage(db):
    """Ask the database what exists for each year. Nothing here is hand-maintained."""
    stage_years = {}
    for r in rows(db, """SELECT fy, stage, COUNT(*) n, COUNT(DISTINCT doc_id) docs,
                                SUM(documents_disagree) dis
                         FROM budget_figure GROUP BY fy, stage"""):
        stage_years[(r['fy'], r['stage'])] = r

    # Ledger presence, and CRUCIALLY the grain: a department rollup is not a line-level
    # report and the matrix must not say it is.
    ledger = {}
    for r in rows(db, """SELECT l.fy, l.period, a.account_type, a.level,
                                COUNT(*) n, COUNT(DISTINCT l.doc_id) docs
                         FROM ledger_snapshot l JOIN account a USING (account_id)
                         WHERE a.fund = '0100'
                         GROUP BY l.fy, l.period, a.account_type, a.level"""):
        ledger[(r['fy'], r['period'], r['account_type'])] = r

    funds = {r['fy']: r for r in rows(
        db, 'SELECT fy, COUNT(*) n FROM fund_activity GROUP BY fy')}
    grants = {}
    for r in rows(db, 'SELECT fy, COUNT(*) n FROM grant_award GROUP BY fy'):
        if str(r['fy']).isdigit():
            grants[int(r['fy'])] = r

    years = sorted({y for y, _ in stage_years} | {y for y, _, _ in ledger}
                   | set(funds) | set(grants))

    def cell(state, n=0, docs=0, note=None):
        c = dict(state=state)
        if n:
            c['n'] = n
        if docs:
            c['docs'] = docs
        if note:
            c['note'] = note
        return c

    def stage_cell(fy, stage):
        r = stage_years.get((fy, stage))
        if not r:
            return cell('missing')
        note = None
        if r['dis']:
            note = '%d of %d lines: documents disagree' % (r['dis'], r['n'])
        return cell('partial' if r['dis'] else 'obtained', r['n'], r['docs'], note)

    def ledger_cell(fy, period, kind='expense'):
        r = ledger.get((fy, period, kind))
        if not r:
            return cell('missing')
        if r['level'] == 'department':
            return cell('partial', r['n'], r['docs'],
                        'department rollup only — the district is one row')
        return cell('obtained', r['n'], r['docs'], 'account level')

    cells = {}
    for fy in years:
        c = {
            'proposed': stage_cell(fy, 'proposed'),
            'settled': stage_cell(fy, 'settled'),
            'restated': stage_cell(fy, 'actual'),
            'q1': ledger_cell(fy, 3), 'q2': ledger_cell(fy, 6),
            'q3': ledger_cell(fy, 9), 'q4': ledger_cell(fy, 13),
            'revenue': (ledger_cell(fy, 9, 'revenue')
                        if (fy, 9, 'revenue') in ledger else cell('missing')),
            # The appropriation as voted is the `original` column of any ledger report for
            # that year, so it exists exactly when some ledger report does.
            'approp': (cell('obtained', note='from the ledger’s original column')
                       if any(k[0] == fy for k in ledger) else cell('missing')),
            # Never held for any year. Requested from the Town Manager, 2 September 2026.
            'po': cell('missing'),
            'funds': (cell('obtained', funds[fy]['n']) if fy in funds else cell('missing')),
            'grants': (cell('obtained', grants[fy]['n']) if fy in grants
                       else cell('missing')),
        }
        cells[str(fy)] = c
    return dict(years=years, rowDefs=ROW_DEFS, cells=cells)


def line_series(db):
    """Per budget line, one row per year, with both halves and where each came from.

    Budget and actual are taken from `budget_figure`, whose two halves are read from the
    same row of the same document -- which is what makes the pair sound. The workbook is
    carried alongside rather than merged: it is a different document and a restatement.
    """
    meta = {r['line_key']: r for r in rows(
        db, 'SELECT line_key, label, section, function_group FROM budget_line')}

    series = {}
    for r in rows(db, """SELECT line_key, label, fy, stage, value, documents_disagree,
                                doc_id
                         FROM budget_figure ORDER BY line_key, fy"""):
        s = series.setdefault(r['line_key'], {})
        y = s.setdefault(r['fy'], dict(fy=r['fy']))
        y[r['stage']] = r['value']
        y.setdefault('docs', {})[r['stage']] = r['doc_id']
        if r['documents_disagree']:
            y['disagree'] = True
        if r['label'] and r['line_key'] not in meta:
            meta[r['line_key']] = dict(line_key=r['line_key'], label=r['label'],
                                       section=None, function_group=None)

    wb = {}
    for r in rows(db, """SELECT line_key, fy, column_kind, value, row
                         FROM workbook_figure WHERE row_kind='line'"""):
        meta.setdefault(r['line_key'], dict(line_key=r['line_key'],
                                            label=r['line_key'], section=None,
                                            function_group=None))
        wb.setdefault(r['line_key'], {}).setdefault(r['fy'], {})[r['column_kind']] = \
            dict(value=r['value'], row=r['row'])

    # The two sources name lines differently and only 48 keys overlap, so the union is
    # taken and every record says which source it came from. Merging them on a fuzzy name
    # match would be the crosswalk problem all over again, one level down.
    out = []
    for k in sorted(set(series) | set(wb)):
        byyear = series.get(k, {})
        m = meta.get(k, dict(label=k, section=None, function_group=None))
        years = []
        for fy in sorted(byyear):
            y = byyear[fy]
            budget = y.get('settled', y.get('proposed'))
            stage = 'settled' if 'settled' in y else ('proposed' if 'proposed' in y else None)
            actual = y.get('actual')
            row = dict(fy=fy)
            if budget is not None:
                row['budget'] = round(budget, 2)
                row['stage'] = stage
            if actual is not None:
                row['actual'] = round(actual, 2)
            # Only a pair drawn from the SAME document gets a variance.
            if budget is not None and actual is not None and stage:
                same = y.get('docs', {}).get(stage) == y.get('docs', {}).get('actual')
                row['sameDoc'] = bool(same)
                if same:
                    row['variance'] = round(actual - budget, 2)
            if y.get('disagree'):
                row['disagree'] = True
            years.append(row)
        src = ([  'documents'] if byyear else []) + (['workbook'] if k in wb else [])
        rec = dict(key=k, label=m.get('label') or k, section=m.get('section'),
                   group=m.get('function_group'), years=years, sources=src)
        if k in wb:
            rec['workbook'] = {str(fy): {ck: v['value'] for ck, v in cols.items()}
                               for fy, cols in wb[k].items()}
            rec['row'] = min(v['row'] for cols in wb[k].values() for v in cols.values())
        out.append(rec)
    out.sort(key=lambda r: (r['group'] or '￿', r['label']))
    return out


def totals(db):
    """Year totals, from the one source that prints both halves of the same year."""
    out = []
    for r in rows(db, """SELECT fy,
                           SUM(CASE WHEN column_kind IN ('budget','final_budget')
                                    THEN value END) budget,
                           SUM(CASE WHEN column_kind='actual' THEN value END) actual,
                           SUM(CASE WHEN column_kind='actual_to_date'
                                    THEN value END) actual_td,
                           SUM(CASE WHEN column_kind='encumbered_to_date'
                                    THEN value END) encumbered_td
                         FROM workbook_figure WHERE row_kind='line'
                         GROUP BY fy ORDER BY fy"""):
        if not any((r['budget'], r['actual'], r['actual_td'])):
            continue                      # a forecast column is not a year of data
        rec = dict(fy=r['fy'], budget=r['budget'], actual=r['actual'],
                   actualToDate=r['actual_td'], encumberedToDate=r['encumbered_td'],
                   source='workbook')
        if r['budget'] and r['actual']:
            rec['surplus'] = round(r['budget'] - r['actual'], 2)
            rec['surplusPct'] = round((r['budget'] - r['actual']) / r['budget'] * 100, 2)
        elif r['budget'] and r['actual_td'] is not None:
            # FY26 is incomplete by construction: the workbook's own column is headed
            # 'Actuals to date'. Committed = spent + encumbered, which is what the
            # available column would net against -- NOT a surplus.
            committed = (r['actual_td'] or 0) + (r['encumbered_td'] or 0)
            rec['committed'] = round(committed, 2)
            rec['uncommitted'] = round(r['budget'] - committed, 2)
            rec['partial'] = True
        out.append(rec)
    return out


def ledger_departments(db):
    return rows(db, """SELECT a.dept, a.name, l.fy, l.period, l.original, l.transfers,
                              l.revised, l.expended, l.encumbered, l.available,
                              l.pct_used, l.doc_id
                       FROM ledger_snapshot l JOIN account a USING (account_id)
                       WHERE a.level='department' AND a.account_type='expense'
                         AND a.fund='0100'
                       ORDER BY l.available DESC""")


def funding(db):
    return dict(
        revenue=rows(db, """SELECT object, name, fy, period, budgeted, received,
                                   pct_received, doc_id
                            FROM v_revenue WHERE fund='0100'
                              AND (budgeted <> 0 OR received <> 0)
                            ORDER BY budgeted DESC"""),
        interfund=rows(db, """SELECT fund, object, name, fy, budgeted, received
                              FROM v_interfund WHERE budgeted <> 0 OR received <> 0"""),
        funds=rows(db, """SELECT fund, name, kind, restriction, fy, revenue, spent,
                                 closing_balance FROM v_fund_year
                          ORDER BY closing_balance DESC"""),
    )


def main():
    if not os.path.exists(DB):
        print('no database; run scripts/build_db.py first')
        return 1
    db = sqlite3.connect(DB)

    try:
        commit = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = None

    data = dict(
        coverage=coverage(db),
        lines=line_series(db),
        totals=totals(db),
        departments=ledger_departments(db),
        funding=funding(db),
        meta=dict(
            commit=commit or None,
            counts={t: db.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0]
                    for t in ('document', 'account', 'fund', 'ledger_snapshot',
                              'budget_figure', 'workbook_figure', 'budget_line',
                              'crosswalk', 'fund_activity', 'grant_award')},
            # Stated on the page, because an empty crosswalk is the reason the
            # line-level budget-to-actual question cannot be answered from the ledger.
            lineSourceOverlap=None,   # filled below
            crosswalkNote=('No budget line is mapped to a ledger account. District lines '
                           'are named, MUNIS rows are coded, and no document maps one to '
                           'the other. The line-level MUNIS reports would.'),
        ),
    )
    # How far the two line-name spaces actually overlap. Stated on the page, because a
    # reader looking at 696 lines should know they are not 696 comparable series.
    both = sum(1 for l in data['lines'] if len(l['sources']) == 2)
    data['meta']['lineSourceOverlap'] = dict(
        total=len(data['lines']), both=both,
        documentsOnly=sum(1 for l in data['lines'] if l['sources'] == ['documents']),
        workbookOnly=sum(1 for l in data['lines'] if l['sources'] == ['workbook']))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, separators=(',', ':'))
    size = os.path.getsize(OUT)
    print('wrote %s -- %.1f KB' % (os.path.relpath(OUT, ROOT), size / 1024))
    print('  %d lines, %d years of coverage, %d department rows'
          % (len(data['lines']), len(data['coverage']['years']),
             len(data['departments'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
