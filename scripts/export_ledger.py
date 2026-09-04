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
import csv
import json
import os
import re
import sqlite3
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
# public/, not src/: this is fetched at runtime rather than bundled. Half a megabyte of
# ledger has no business in the main bundle of a page nobody else reads, and keeping it
# out means the data room is not prerendered into a static file either.
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'ledger.json')
# What the line reader could and could not read, written by extract_line_history.py. A
# coverage matrix built on the reader's OUTPUT cannot tell a document nobody gave us from
# a document nobody read, and it reported both as absent -- which is how a request very
# nearly went to the Superintendent for ten documents already on disk.
READER = os.path.join(ROOT, 'sources', 'data', 'line-history-coverage.csv')

# What a fiscal year needs before any of the questions on that page can be answered for
# it. This is the STANDARD -- the same rows for every year -- and the point of publishing
# it is that the empty cells are the argument.
ROW_DEFS = [
    dict(id='proposed', group='Budget documents', label='Proposed budget, line level',
         why='The superintendent’s request. Establishes what was asked for.',
         publisher='Lunenburg Public Schools',
         howToGet='Published on the district’s budget page each winter, and mirrored here '
                  'when it appears. Older years are in the meeting archive as School '
                  'Committee packets.',
         effort='public'),
    dict(id='settled', group='Budget documents', label='Approved budget, line level',
         why='What the School Committee and Town Meeting settled on. The base every rate is measured from.',
         publisher='Lunenburg Public Schools',
         howToGet='The district’s approved budget document for that year. Where a year is '
                  'missing it is usually because the document was posted to Google Drive '
                  'and the link has since been walled.',
         effort='public'),
    dict(id='restated', group='Budget documents', label='Prior-year actuals, restated',
         why='A later budget document re-presenting the year. A restatement, not a ledger.',
         publisher='Lunenburg Public Schools',
         howToGet='Appears as an ACTUALS column inside a LATER year’s budget document, so '
                  'it arrives one to three years after the year it describes. Nothing can '
                  'make it arrive sooner.',
         effort='public'),
    dict(id='approp', group='The town’s ledger', label='Appropriation as voted',
         why='MUNIS original appropriation. What Town Meeting actually voted, before transfers.',
         publisher='Town Accountant',
         howToGet='The ORIGINAL APPROP column of any MUNIS year-to-date budget report for '
                  'that year, so it arrives with any of the quarterly reports below.',
         effort='records request'),
    dict(id='q1', group='The town’s ledger', label='Q1 spend report (period 3)',
         why='First quarter. Needed for the seasonal baseline that makes a burn rate mean anything.',
         publisher='Town Accountant',
         howToGet='MUNIS YEAR-TO-DATE BUDGET REPORT (program `glytdbud`), Fund 0100, '
                  'Account type Expense, Year/Period YYYY/3, run with '
                  '**Print totals only: N** and **Suppress zero bal accts: N**.',
         effort='records request'),
    dict(id='q2', group='The town’s ledger', label='Q2 spend report (period 6)',
         why='Half year.',
         publisher='Town Accountant',
         howToGet='The same report at Year/Period YYYY/6.',
         effort='records request'),
    dict(id='q3', group='The town’s ledger', label='Q3 spend report (period 9)',
         why='Three quarters. The last point at which a surplus could still be redirected.',
         publisher='Town Accountant',
         howToGet='The same report at Year/Period YYYY/9. We hold FY26 at this period, but '
                  'run as a department rollup rather than at account level.',
         effort='records request'),
    dict(id='p12', group='The town’s ledger', label='Year-end position (period 12)',
         why='June, with the books not yet closed. Shows where a year landed; not what it '
             'finally turned back.',
         publisher='Town Accountant',
         howToGet='The same `glytdbud` report at Year/Period YYYY/12. Held for FY26, sent '
                  'by the Town Manager on 2 September 2026 in both printed and '
                  'spreadsheet form — the first account-level expenditure report in this '
                  'archive.',
         effort='records request'),
    dict(id='q4', group='The town’s ledger', label='Year-end close (period 13)',
         why='After the lapse period. The surplus IS the available column on this report.',
         publisher='Town Accountant',
         howToGet='The same report at Year/Period YYYY/13. This is the single most '
                  'valuable missing document in the archive: without it no year’s surplus '
                  'can be computed here at all.',
         effort='records request'),
    dict(id='po', group='The town’s ledger', label='Purchase orders closed after close',
         why='The step that moved FY25 from $582,115.44 to $603,885.97. Not recoverable from one report run.',
         publisher='Town Accountant',
         howToGet='A list of purchase orders closed against the fiscal year after its '
                  'initial close, with amounts and dates. Not a standard report — it has '
                  'to be asked for in those words.',
         effort='records request'),
    dict(id='revenue', group='Funding sources', label='Revenue ledger',
         why='Chapter 70, local receipts, and transfers in. The expense side cannot see any of it.',
         publisher='Town Accountant',
         howToGet='The same `glytdbud` report with Account type **Revenue**. Our FY26 copy '
                  'was already run at account level, which is why this row is green where '
                  'the expense rows beside it are not.',
         effort='records request'),
    dict(id='funds', group='Funding sources', label='Revolving and grant fund activity',
         why='What the general fund line is net OF. Rule 11.',
         publisher='Town Accountant',
         howToGet='`glytdbud` for the school grant, revolving and school choice funds — '
                  'not Fund 0100. What we hold for FY26 is a fund-balance summary, one '
                  'row per fund, which gives totals and not what they bought.',
         effort='records request'),
    dict(id='grants', group='Funding sources', label='Grant awards listed',
         why='What was awarded. Not a mapping onto the lines a grant paid for — nobody publishes that.',
         publisher='Lunenburg Public Schools',
         howToGet='Listed inside the district’s own budget documents, so it arrives with '
                  'them. The award is not the spending and never says which line it paid.',
         effort='public'),
    dict(id='dese', group='Independent check', label='DESE all-funds per pupil, by function',
         why='An outside publisher’s view of the same spending, across every fund. Bounds '
             'the total the budget document cannot see.',
         publisher='Massachusetts DESE',
         howToGet='Public download, no request needed: '
                  'doe.mass.edu/research/radar/district-comparison.xlsx. Note DESE counts '
                  'costs the school budget does not carry, so it is a second opinion and '
                  'not a like-for-like comparison.',
         effort='public'),
]


# `covers` is written as full years -- FY2025, not FY25 -- so a two-digit pattern
# reads "20" and matches nothing. It did, and every cell went back to saying missing.
COVERS_FY = re.compile(r'\bFY(\d{4})\b')


def unread_documents():
    """Documents we hold whose figures have never been extracted, by fiscal year.

    Read from `line-history-coverage.csv`, which extract_line_history.py writes on every
    run: one row per document on the district's budget page, whether or not it yielded a
    figure, with the reason when it did not.

    The year attribution is the `covers` column, which the extractor computes from the
    document's own page-top header lines and title block -- see year_candidates() there
    for why a fourteen-year chart on a slide does not count. The header line is carried
    into the cell verbatim so a reader can check it against the file.

    That is a weaker claim than an extracted figure and it is labelled as one: the cell
    state is `unread`, never `obtained`. What it rules out is the only thing it needs to
    rule out -- calling the year absent when the document is on the shelf.
    """
    if not os.path.exists(READER):
        raise SystemExit('%s is missing. Run:\n'
                         '    python3 scripts/extract_line_history.py' % READER)
    by_year, unread = {}, []
    with open(READER, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if int(r['figures'] or 0) or int(r['data_rows'] or 0) < 20:
                continue
            d = dict(document=r['document'], dataRows=int(r['data_rows']),
                     reason=r['reason'], covers=r['covers'],
                     statesInItsHeader=r['header_years'])
            unread.append(d)
            for fy in (int(y) for y in COVERS_FY.findall(r['covers'])):
                by_year.setdefault(fy, []).append(d)
    return by_year, unread


def rows(db, sql, *args):
    db.row_factory = sqlite3.Row
    return [dict(r) for r in db.execute(sql, args).fetchall()]


def coverage(db):
    """What exists for each year, WHICH DOCUMENTS back it, and what would fill a gap.

    Nothing here is hand-maintained: it asks the database what is present. A cell knows
    three things and a reader needs all three --

      state      obtained / partial / missing
      documents  the actual files the figure rests on, with their address and sha256
      needed     what to obtain, from whom, to turn it green

    The third one is the point. "We do not have FY24 Q2" is not useful on its own; "run
    glytdbud for Fund 0100, Year/Period 2024/6, Print totals only: N, and ask the Town
    Accountant" is a thing somebody can act on.
    """
    unread_by_year, unread_all = unread_documents()

    docmeta = {r['doc_id']: r for r in rows(
        db, """SELECT doc_id, path, basis, url, copy_state, local_sha256 AS sha256,
                      hidden_columns FROM document""")}
    bybase = {}
    for d in docmeta.values():
        bybase.setdefault(os.path.basename(d['path'] or d['doc_id']), d)

    def docs(ids):
        """Resolve doc_ids to addresses. budget_figure cites bare filenames; the document
        table is keyed by archive path. Unresolved ones are REPORTED, never dropped."""
        out, missing = [], []
        for i in sorted({x for x in ids if x}):
            d = docmeta.get(i) or bybase.get(os.path.basename(i))
            if d:
                out.append(dict(citedAs=i, path=d['path'], basis=d['basis'],
                                url=d['url'], sha256=d['sha256'],
                                hiddenColumns=d['hidden_columns'] or None))
            else:
                missing.append(i)
        return out, missing

    # What each document says about a contested line, so a cell can show the reader the
    # disagreement instead of just asserting there is one. Capped per cell: the point is
    # to make the dispute legible, not to publish a second copy of the archive.
    contested = {}
    for r in rows(db, """SELECT fy, stage, line_key, label, source, value, is_kept,
                                spread, kind
                         FROM v_budget_disagreement WHERE variant = ''
                         ORDER BY fy, stage, spread DESC, line_key, source"""):
        # The reference tables are loaded verbatim, every column TEXT, so the year
        # arrives as a string and would never meet the integer keys used everywhere else.
        by_cell = contested.setdefault((int(r['fy']), r['stage']), {})
        line = by_cell.setdefault(r['line_key'], dict(
            label=r['label'], spread=round(float(r['spread']), 2),
            kind=r['kind'], statements=[]))
        line['statements'].append(dict(document=os.path.basename(r['source']),
                                       value=round(float(r['value']), 2),
                                       kept=bool(int(r['is_kept']))))

    stage_docs, stage_years = {}, {}
    for r in rows(db, """SELECT fy, stage, doc_id, COUNT(*) n,
                                SUM(documents_disagree) dis
                         FROM budget_figure GROUP BY fy, stage, doc_id"""):
        k = (r['fy'], r['stage'])
        stage_docs.setdefault(k, []).append(r['doc_id'])
        agg = stage_years.setdefault(k, dict(n=0, dis=0))
        agg['n'] += r['n']
        agg['dis'] += r['dis'] or 0

    ledger, ledger_docs = {}, {}
    for r in rows(db, """SELECT l.fy, l.period, a.account_type, a.level, l.doc_id,
                                COUNT(*) n
                         FROM ledger_snapshot l JOIN account a USING (account_id)
                         WHERE a.fund = '0100'
                         GROUP BY l.fy, l.period, a.account_type, a.level, l.doc_id"""):
        k = (r['fy'], r['period'], r['account_type'])
        ledger.setdefault(k, dict(n=0, level=r['level']))
        ledger[k]['n'] += r['n']
        ledger_docs.setdefault(k, []).append(r['doc_id'])

    funds, fund_docs = {}, {}
    for r in rows(db, 'SELECT fy, doc_id, COUNT(*) n FROM fund_activity GROUP BY fy, doc_id'):
        funds[r['fy']] = funds.get(r['fy'], 0) + r['n']
        fund_docs.setdefault(r['fy'], []).append(r['doc_id'])

    grants, grant_docs = {}, {}
    for r in rows(db, 'SELECT fy, doc_id, COUNT(*) n FROM grant_award GROUP BY fy, doc_id'):
        if str(r['fy']).isdigit():
            fy = int(r['fy'])
            grants[fy] = grants.get(fy, 0) + r['n']
            grant_docs.setdefault(fy, []).append(r['doc_id'])

    dese, dese_docs = {}, {}
    for r in rows(db, """SELECT fy, doc_id, COUNT(*) n FROM dese_measure
                         WHERE lea='01620000' GROUP BY fy, doc_id"""):
        dese[r['fy']] = dese.get(r['fy'], 0) + r['n']
        dese_docs.setdefault(r['fy'], []).append(r['doc_id'])

    years = sorted({y for y, _ in stage_years} | {y for y, _, _ in ledger}
                   | set(funds) | set(grants) | set(dese))

    def cell(state, ids=(), n=0, note=None):
        found, unresolved = docs(ids)
        c = dict(state=state, documents=found)
        if n:
            c['n'] = n
        if note:
            c['note'] = note
        if unresolved:
            c['unresolvedDocuments'] = unresolved
        return c

    def stage_cell(fy, stage):
        agg = stage_years.get((fy, stage))
        if not agg:
            # Three questions, and until now they answered as one: is the document on
            # disk, is it in the document table, are its figures in a fact table? A year
            # with no figures may still have documents sitting unread in the archive, and
            # `missing` said the opposite of the truth about them.
            held = unread_by_year.get(fy)
            if held:
                c = cell('unread')
                c['heldNotRead'] = held
                c['note'] = ('%d document(s) on the district’s budget page state FY%d in '
                             'their own header and have never had their figures '
                             'extracted. Held, not missing — asking for these again would '
                             'be asking for what is already on disk.' % (len(held), fy))
                return c
            return cell('missing')
        lines = contested.get((fy, stage)) or {}
        if not agg['dis']:
            return cell('obtained', stage_docs[(fy, stage)], agg['n'])
        share = agg['dis'] / agg['n'] * 100
        note = ('%d of %d figures — %.0f%% — are stated differently by two of the '
                'documents below. The rest agree.' % (agg['dis'], agg['n'], share))
        c = cell('partial', stage_docs[(fy, stage)], agg['n'], note)
        c['contestedShare'] = round(share, 1)
        c['contested'] = agg['dis']
        # Widest disagreements first: a line two documents put $19,000 apart is worth a
        # reader's attention and one they put $12 apart is rounding.
        c['contestedLines'] = sorted(
            ({'line': k, **v} for k, v in lines.items()),
            key=lambda x: -x['spread'])[:12]
        return c

    def ledger_cell(fy, period, kind='expense'):
        r = ledger.get((fy, period, kind))
        if not r:
            return cell('missing')
        if r['level'] == 'department':
            return cell('partial', ledger_docs[(fy, period, kind)], r['n'],
                        'Run as a department rollup — the whole school district is one '
                        'row, so no budget line can be traced into it. Re-running the '
                        'same report with Print totals only: N would make this green.')
        return cell('obtained', ledger_docs[(fy, period, kind)], r['n'],
                    'Account level — full GL detail.')

    cells = {}
    for fy in years:
        approp_ids = [d for (f, _, _), ds in ledger_docs.items() if f == fy for d in ds]
        cells[str(fy)] = {
            'proposed': stage_cell(fy, 'proposed'),
            'settled': stage_cell(fy, 'settled'),
            'restated': stage_cell(fy, 'actual'),
            'q1': ledger_cell(fy, 3), 'q2': ledger_cell(fy, 6),
            'q3': ledger_cell(fy, 9), 'p12': ledger_cell(fy, 12),
            'q4': ledger_cell(fy, 13),
            'revenue': (ledger_cell(fy, 9, 'revenue')
                        if (fy, 9, 'revenue') in ledger else cell('missing')),
            # The appropriation as voted is the `original` column of any ledger report for
            # the year, so it exists exactly when some ledger report for that year does.
            'approp': (cell('obtained', approp_ids,
                            note='Read from the ORIGINAL APPROP column of the ledger '
                                 'report below.')
                       if approp_ids else cell('missing')),
            # Never held for any year. Requested from the Town Manager, 2 September 2026.
            'po': cell('missing'),
            'funds': (cell('obtained', fund_docs[fy], funds[fy])
                      if fy in funds else cell('missing')),
            'grants': (cell('obtained', grant_docs[fy], grants[fy])
                       if fy in grants else cell('missing')),
            'dese': (cell('obtained', dese_docs[fy], dese[fy],
                          'DESE’s own all-funds figures. An outside check, not a '
                          'like-for-like comparison with the town’s appropriation.')
                     if fy in dese else cell('missing')),
        }
    return dict(years=years, rowDefs=ROW_DEFS, cells=cells, unread=unread_all)


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


def totals(db, cov):
    """Year totals, and -- more importantly -- what we CANNOT say about each year.

    The difference between a budget column and an actual column is not a surplus. It is a
    subtraction of two columns in a document the district wrote about itself. The town
    arrives at its surplus by CLOSING THE BOOKS: revised appropriation, less expended,
    less encumbrances still open after purchase orders are closed in the lapse period.
    We hold no year-end ledger for any year, so we cannot do that arithmetic for any year.

    An earlier version of this printed the subtraction in a column headed "Under budget"
    with a dash everywhere else, which said two wrong things at once: that the number was
    the surplus, and that a dash meant no variance rather than no data. Each row now
    states what it IS, what is missing, and -- where the town has stated a figure of its
    own -- that figure beside ours with the gap named.
    """
    stated = {}
    for r in rows(db, 'SELECT * FROM stated_figure ORDER BY fy, stated_on'):
        stated.setdefault(r['fy'], []).append(r)

    # What a year needs before WE could compute a surplus, and whether we hold it.
    NEEDED = [('q4', 'the year-end ledger (period 13)'),
              ('po', 'purchase orders closed after the year closed')]
    # Period 12 is deliberately NOT in NEEDED. It shows where a year landed in June and
    # it is not the close: purchase orders are still open, and closing them is what moved
    # FY25 by $21,770.53. A June report makes the answer visible; it does not make it
    # final, and the Town Manager said so in the covering note.

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
        fy = r['fy']
        cells = cov['cells'].get(str(fy), {})
        blocked = [label for key, label in NEEDED
                   if cells.get(key, {}).get('state') != 'obtained']

        rec = dict(
            fy=fy, budget=r['budget'], actual=r['actual'],
            actualToDate=r['actual_td'], encumberedToDate=r['encumbered_td'],
            source='workbook',
            # Never 'surplus'. This is the distance between two columns of a restatement.
            canComputeSurplus=not blocked,
            blockedBy=blocked,
        )

        if r['budget'] is None:
            rec['halves'] = 'actual only'
            rec['whatThisIs'] = ('This workbook prints no budget column for this year, so '
                                 'there is nothing to subtract from. Not a variance of '
                                 'zero \u2014 a half we do not hold.')
        elif r['actual'] is None and r['actual_td'] is not None:
            committed = (r['actual_td'] or 0) + (r['encumbered_td'] or 0)
            rec['halves'] = 'budget and a part-year actual'
            rec['committed'] = round(committed, 2)
            rec['uncommitted'] = round(r['budget'] - committed, 2)
            rec['whatThisIs'] = ('An incomplete year. The workbook\'s own column is headed '
                                 '"Actuals to date". What is left is uncommitted budget at '
                                 'that moment, not money that came back.')
        elif r['actual'] is None:
            rec['halves'] = 'budget only'
            rec['whatThisIs'] = 'No actual column for this year in this workbook.'
        else:
            rec['halves'] = 'both'
            rec['restatementVariance'] = round(r['budget'] - r['actual'], 2)
            rec['restatementVariancePct'] = round(
                (r['budget'] - r['actual']) / r['budget'] * 100, 2)
            rec['whatThisIs'] = ('The distance between two columns of a document the '
                                 'district wrote about itself. Not a closing figure.')

        if fy in stated:
            rec['stated'] = [dict(
                amount=x['amount'], statedOn=x['stated_on'], statedBy=x['stated_by'],
                quote=x['quote'], docId=x['doc_id'], sourceRef=x['source_ref'],
                supersedes=x['supersedes'], note=x['note']) for x in stated[fy]]
            latest = max(stated[fy], key=lambda x: x['stated_on'])
            rec['townFigure'] = latest['amount']
            if 'restatementVariance' in rec:
                rec['gapToTownFigure'] = round(
                    rec['restatementVariance'] - latest['amount'], 2)
        out.append(rec)
    return out


def gross_budget(db, fy=2026, period=12):
    """The school budget as it would look if every source of money were on the page.

    THE POINT OF THIS TABLE IS ITS EMPTY COLUMNS.

    The district publishes a budget that is NET: each line is what the town must raise
    after grants, fees and reimbursements have paid for part of the thing. A line reading
    $20,000 may be a $220,000 line with $200,000 of grant behind it, and nothing in the
    document marks it. So this rebuilds the same budget with the other money beside it --
    and where that money is not held, says so in the cell rather than leaving a reader to
    assume the town's share is the whole cost.

    Every row is in one of three states, and they must stay distinguishable:

      known        we hold the figure and can name the document
      not held     we know money of this kind exists and cannot yet attribute it
      none found   we looked and there is no other funding for this line

    `none found` is deliberately NOT the default. Defaulting to it would turn "we have not
    checked" into "there is nothing there", which is the whole error this table exists to
    prevent. Until the fund-level detail arrives, every offset cell is `not held`.

    The net column reconciles to the district's own published appropriation, so the
    budget the district publishes is directly derivable from this table -- which is what
    makes it checkable rather than a parallel invention.
    """
    accounts = rows(db, """SELECT a.org, a.object, a.name, a.account_id,
                                  l.original, l.transfers, l.revised, l.expended,
                                  l.encumbered, l.available, l.doc_id
                           FROM ledger_snapshot l JOIN account a USING (account_id)
                           WHERE l.fy=? AND l.period=? AND a.dept='300'
                             AND a.level='account'
                           ORDER BY a.org, a.object""", fy, period)

    # Money we KNOW was spent on the schools outside the general fund, by fund. It cannot
    # be attributed to a line, so it sits below the table rather than being spread across
    # it. Spreading it in proportion would look right and be invented.
    unattributed = rows(db, """SELECT fa.fund, f.name, f.kind, f.restriction,
                                      fa.revenue, fa.salaries, fa.expenditure,
                                      fa.closing_balance, fa.doc_id
                               FROM fund_activity fa LEFT JOIN fund f ON f.fund = fa.fund
                               WHERE fa.fy = ?
                               ORDER BY (fa.salaries + fa.expenditure) DESC""", fy)
    for u in unattributed:
        u['spent'] = round((u['salaries'] or 0) + (u['expenditure'] or 0), 2)

    grants = rows(db, """SELECT fy, kind, name, amount, owner, doc_id
                         FROM grant_award WHERE fy = ? ORDER BY amount DESC""", str(fy))

    out = []
    for a in accounts:
        out.append(dict(
            org=a['org'], object=a['object'], label=a['name'],
            accountId=a['account_id'],
            # The town's side: held, and reconciling to the published appropriation.
            net=dict(state='known', appropriated=a['original'], transfers=a['transfers'],
                     revised=a['revised'], spent=a['expended'],
                     encumbered=a['encumbered'], unspent=a['available'],
                     docId=a['doc_id']),
            # Every other source. Not held for any line, for any year, so far.
            offsets=dict(state='not held', items=[],
                         blockedBy='Fund-level spending detail for the school grant, '
                                   'revolving and school choice funds. The same MUNIS '
                                   'report at a Fund other than 0100.'),
            gross=dict(state='unknown',
                       note='Cannot be computed until the offsets above are held. The '
                            'town’s share is a floor, never the cost.'),
        ))

    net_appropriated = sum(a['original'] or 0 for a in accounts)
    net_spent = sum(a['expended'] or 0 for a in accounts)
    known_outside = sum(u['spent'] for u in unattributed)

    return dict(
        fy=fy, period=period,
        asOf=('Period %d — the books are not closed. Period 13 is the year-end close, '
              'after purchase orders are cleared.' % period),
        rows=out,
        unattributed=unattributed,
        grants=grants,
        totals=dict(
            netAppropriated=round(net_appropriated, 2),
            netSpent=round(net_spent, 2),
            knownOutsideGeneralFund=round(known_outside, 2),
            grossFloor=round(net_spent + known_outside, 2),
            grossFloorNote=('A FLOOR, not a total. It adds what the town spent to the '
                            'non-general-fund spending we happen to hold, and we do not '
                            'hold all of it — grant funds are only partly visible and no '
                            'year is complete.'),
            attributableToLines=0,
            attributableNote=('None of the money outside the general fund can be attached '
                              'to a budget line. Attributing it in proportion to line '
                              'size would look right and be invented.'),
        ),
        legend=[
            dict(state='known', means='We hold the figure and can name the document.'),
            dict(state='not held', means='Money of this kind exists and we cannot yet '
                                         'attribute it. This is not zero.'),
            dict(state='none found', means='Checked, and there is no other funding for '
                                           'this line. Never assumed.'),
            dict(state='unknown', means='Cannot be computed from what is held.'),
        ],
    )


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

    cov = coverage(db)
    data = dict(
        coverage=cov,
        lines=line_series(db),
        totals=totals(db, cov),
        departments=ledger_departments(db),
        grossBudget=gross_budget(db),
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
