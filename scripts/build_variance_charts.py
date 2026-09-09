#!/usr/bin/env python3
"""The budget-versus-actual page's series, pre-rendered from the database.

    python3 scripts/build_variance_charts.py            # write it
    python3 scripts/build_variance_charts.py --check    # fail if it is stale

WHY A FILE AND NOT A QUERY. The page could ask /api/query for all of this at load. It
must not: D1's free tier stops at 5 million rows read a day and a single join across the
big tables here reads 19,006, so a few hundred page loads would take the endpoint dark
until tomorrow. Everything on the page is the same for every reader until the database is
rebuilt, so it is computed once, here, and served as a static file.

WHY THE VIEW IS NOT USED AS WRITTEN. `v_line_budget_vs_actual` pivots the stages of a
line-year and reports `MAX(documents_disagree)` across ALL of them -- so a line whose
PROPOSED column two documents disagree about is reported as a line-year whose budget and
actual are in dispute. There are 253 such proposed cells and 51 real ones, and the
difference moved every figure on this page by about 15%. The pivot below carries the flag
PER STAGE, which is the reading the analysis and `analyze_variance.py` both take.

RULE 1, WHICH IS THE SUBJECT HERE RATHER THAN AN OBSTACLE. Comparing a year's budget to
that same year's actual is what this file does and what the page is for. What it never
does is measure a rate of change from an actual in one year to a budget in another: that
is partly growth and partly the step between two different kinds of column. Nothing here
produces a growth rate at all, and the page says so where a reader might be tempted.

WHAT THIS RECONCILES TO. Every function group computed here is checked against
`variance_by_group`, the table `analyze_variance.py` writes, and the script refuses to
write if a single one disagrees or if the join matches nothing. A join that matches
nothing looks exactly like data that is absent.
"""
import argparse
import collections
import csv
import importlib.util
import json
import os
import sqlite3
import statistics as st
import sys

# The conclusions this report states, as DATA rather than as sentences in a page. See
# scripts/conclusions.py.
import conclusions as C
from conclusions import conclusion, emit, figure

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources/data/lunenburg.db')
OUT = os.path.join(ROOT, 'fy28/public/data/budget-vs-actual.json')
REPORTS = os.path.join(ROOT, 'fy28/public/data/reports.json')

# FY21's "actual" column is its budget in all but one line -- the books were not closed
# when the document went out. Stated in the analysis; enforced here so it cannot be
# quietly reinstated by a future pass.
EXCLUDED_YEARS = {2021}
# A year with four usable lines out of three hundred and fifty is not a measurement of a
# budget. Kept in step with analyze_variance.py, which states the same floor.
MIN_LINES_PER_YEAR = 20
# The guard rails on one comparable cell, each one the analysis's own.
MIN_BUDGET = 10_000
MIN_ACTUAL = 1_000
RATIO_BAND = (0.02, 20)
# "Missed the same way in every year" needs a floor, or a line that lands within a tenth
# of a percent five times running counts as a systematic overspend.
SAME_WAY = 0.02
# A group has drifted when its first two measured years and its last two are this far
# apart. Five points is the analysis's threshold.
DRIFT = 0.05

# ---------------------------------------------------------------------------------------
# WHAT THE SECOND COLUMN ACTUALLY IS, AND WHY THE PAGE HAS TO SAY SO.
#
# `budget_figure.stage = 'restated'` was called `actual` until 7 September 2026, and the
# rename is the whole point: not one of the documents behind those rows is an accounting
# record. Every one is a district budget book, and `document-basis.csv` classifies each as
# `restatement` -- a prior year re-presented inside a document written by the party that
# spent it -- or `forward`. None is `ledger`.
#
# Rule 13 lists this exact error in its own table: "the actuals sheet" against "a forward
# budget workbook with a column headed ACTUALS". So the basis is JOINED per document and
# per year rather than described, the join is asserted to match, and the page renders what
# the join returns.
#
# The consequence a resident needs is one sentence long: a budget book cannot show money
# moved between lines mid-year, because approved transfers never appear in one -- and
# mid-year movement is exactly what an over-budgeting question is about.
BASIS_CSV = os.path.join(ROOT, 'sources/data/document-basis.csv')
RESTATED_STAGE = 'restated'


def norm_fn():
    """The workbook's line names, normalised the way the extractor normalised them.

    The mapping from a line to its section and function group lives in the FY27 workbook,
    keyed on the printed line item; `budget_figure` is keyed on the normalised form. The
    one function that produced those keys is the extractor's, so it is imported rather
    than reimplemented -- a second copy of a normaliser is a second thing to drift.
    """
    sp = importlib.util.spec_from_file_location(
        'elh', os.path.join(ROOT, 'scripts/extract_line_history.py'))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m.norm


PIVOT = """
SELECT  b.line_key,
        b.fy,
        MAX(b.label)                                                AS label,
        MAX(CASE WHEN b.stage = 'settled' THEN b.value END)         AS settled,
        MAX(CASE WHEN b.stage = 'restated' THEN b.value END)         AS actual,
        MAX(CASE WHEN b.stage = 'settled'
                 THEN b.documents_disagree END)                     AS settled_disputed,
        MAX(CASE WHEN b.stage = 'restated'
                 THEN b.documents_disagree END)                     AS actual_disputed
FROM    budget_figure b
-- variant='' or a scenario column wins the MAX and is reported as the year's budget. A
-- document stating four FY27 proposals states four figures, not four opinions about one.
WHERE   b.variant = ''
GROUP BY b.line_key, b.fy
"""


def excluded(r):
    """Why this cell cannot be compared, or None. Every exclusion is stated, none silent."""
    b, a = r['settled'], r['actual']
    if r['fy'] in EXCLUDED_YEARS:
        return 'FY21 — the actual column is the budget'
    if b is None or a is None:
        return 'only one of the two figures is published'
    if r['settled_disputed'] or r['actual_disputed']:
        return 'two documents state different figures'
    if b < MIN_BUDGET:
        return f'budget under ${MIN_BUDGET:,}'
    if a < MIN_ACTUAL or not (RATIO_BAND[0] <= a / b <= RATIO_BAND[1]):
        return 'implausible ratio — a parse artefact'
    return None


def build():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    norm = norm_fn()

    wb = list(db.execute("SELECT * FROM lps_budget_lines WHERE kind = 'line'"))
    section = {norm(r['line_item']): r['section'] for r in wb}
    group_of = {norm(r['line_item']): (r['function_group'] or '').strip() for r in wb}
    if not section:
        sys.exit('lps_budget_lines returned no lines — the workbook join is empty, which '
                 'is not the same thing as a workbook with no lines in it.')

    rows = list(db.execute(PIVOT))
    recs, dropped = [], collections.Counter()
    for r in rows:
        why = excluded(r)
        if why:
            if r['settled'] is not None or r['actual'] is not None:
                dropped[why] += 1
            continue
        recs.append(dict(key=r['line_key'], label=(r['label'] or '').strip(), fy=r['fy'],
                         budgeted=r['settled'], spent=r['actual']))

    per_year = collections.Counter(r['fy'] for r in recs)
    thin = {fy: n for fy, n in per_year.items() if n < MIN_LINES_PER_YEAR}
    for fy, n in sorted(thin.items()):
        dropped[f'FY{fy % 100} — only {n} usable lines in the whole year'] += n
    recs = [r for r in recs if r['fy'] not in thin]
    if not recs:
        sys.exit('no usable line-years survived the guards — the pivot matched nothing.')

    years = sorted({r['fy'] for r in recs})

    # ------------------------------------------------------------------ by year
    by_year = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for r in recs:
        by_year[r['fy']][0] += r['budgeted']
        by_year[r['fy']][1] += r['spent']
        by_year[r['fy']][2] += 1
    year_rows = [dict(fy=fy, lines=n, budgeted=b, spent=a, net=a - b, pct=a / b - 1)
                 for fy, (b, a, n) in sorted(by_year.items())]

    # ------------------------------------------------- salaries against the rest
    sec = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for r in recs:
        k = section.get(r['key']) or 'UNFILED'
        sec[k][0] += r['budgeted']
        sec[k][1] += r['spent']
        sec[k][2] += 1
    SEC_LABEL = {'SALARIES': 'Salaries', 'EXPENSES': 'Everything else',
                 'UNFILED': 'Lines the FY27 workbook no longer carries'}
    section_rows = [dict(section=SEC_LABEL.get(k, k), line_years=n,
                         budgeted=b, spent=a, pct=a / b - 1)
                    for k, (b, a, n) in sorted(sec.items(), key=lambda kv: -kv[1][2])]

    # ------------------------------------------------------------ function groups
    grp = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0.0]))
    for r in recs:
        g = group_of.get(r['key']) or '(unmapped)'
        grp[g][r['fy']][0] += r['budgeted']
        grp[g][r['fy']][1] += r['spent']

    groups = []
    for g, ys in grp.items():
        order = sorted(ys)
        b = sum(ys[y][0] for y in order)
        a = sum(ys[y][1] for y in order)
        devs = [ys[y][1] / ys[y][0] - 1 for y in order]
        gross = sum(abs(ys[y][1] - ys[y][0]) for y in order)
        net = a - b
        direction = None
        if len(order) >= 4:
            if all(d > SAME_WAY for d in devs):
                direction = 'over every year'
            elif all(d < -SAME_WAY for d in devs):
                direction = 'under every year'
            else:
                direction = 'both ways'
        drift = (st.mean(devs[-2:]) - st.mean(devs[:2])) if len(order) >= 4 else None
        groups.append(dict(
            group=g, years=len(order), budgeted=b, spent=a, net=net, gross=gross,
            churn=(gross / abs(net)) if abs(net) > 1 else None,
            worst=min(devs), best=max(devs), direction=direction,
            drift=drift if drift is not None and abs(drift) > DRIFT else None,
            by_year=[dict(fy=y, budgeted=ys[y][0], spent=ys[y][1],
                          pct=ys[y][1] / ys[y][0] - 1) for y in order]))
    groups.sort(key=lambda r: -r['budgeted'])

    # THE RECONCILIATION. `variance_by_group` is written by analyze_variance.py from the
    # CSVs; this file is computed from the database. They are two routes to the same
    # figure and they have to agree, or one of the two guards above has moved. A join
    # that matches nothing looks exactly like data that is absent, so the match itself is
    # asserted before the totals are.
    published = {r['function_group']: r for r in db.execute('SELECT * FROM variance_by_group')}
    matched = [g for g in groups if g['group'] in published]
    if len(matched) < len(published):
        sys.exit(f'variance_by_group has {len(published)} groups and only {len(matched)} '
                 f'of them were recomputed here. The group join is broken, not empty.')
    off = [g['group'] for g in matched
           if abs(float(published[g['group']]['net']) - g['net']) > 1]
    if off:
        sys.exit('these groups do not reconcile against variance_by_group:\n  '
                 + '\n  '.join(off))

    # --------------------------------------- the spread of every single line-year
    # An ordered set of bins around zero. The point of the chart is that the total sits in
    # the middle bin and the line-years do not, so the bins are the finding rather than a
    # rendering choice, and they live here rather than in the page.
    EDGES = [-1.0, -0.5, -0.25, -0.10, -0.05, -0.02,
             0.02, 0.05, 0.10, 0.25, 0.50, 1.0, 99.0]
    LABELS = ['under 50%+', '25–50% under', '10–25% under', '5–10% under', '2–5% under',
              'within 2%', '2–5% over', '5–10% over', '10–25% over', '25–50% over',
              '50–100% over', 'over 100%+']
    counts = [0] * (len(EDGES) - 1)
    for r in recs:
        d = r['spent'] / r['budgeted'] - 1
        for i in range(len(EDGES) - 1):
            if EDGES[i] <= d < EDGES[i + 1]:
                counts[i] += 1
                break
    spread = [dict(bin=LABELS[i], lo=EDGES[i], hi=EDGES[i + 1], count=counts[i],
                   centred=(LABELS[i] == 'within 2%'))
              for i in range(len(counts))]

    # ------------------------------------------------------------ line consistency
    per_line = collections.defaultdict(list)
    for r in recs:
        per_line[r['key']].append(r)
    label_of = {r['key']: r['label'] for r in recs}
    multi = {k: v for k, v in per_line.items() if len(v) >= 4}
    same_way = []
    for k, v in multi.items():
        devs = [x['spent'] / x['budgeted'] - 1 for x in v]
        if all(d > SAME_WAY for d in devs) or all(d < -SAME_WAY for d in devs):
            same_way.append(dict(
                line=label_of[k], years=len(v), mean_pct=st.mean(devs),
                mean_dollars=st.mean([x['spent'] - x['budgeted'] for x in v]),
                direction='over' if devs[0] > 0 else 'under'))
    same_way.sort(key=lambda r: -abs(r['mean_dollars']))

    movers = []
    for k, v in per_line.items():
        movers.append(dict(line=label_of[k], years=len(v),
                           net=sum(x['spent'] - x['budgeted'] for x in v),
                           budgeted=sum(x['budgeted'] for x in v),
                           by_year=[dict(fy=x['fy'], pct=x['spent'] / x['budgeted'] - 1)
                                    for x in sorted(v, key=lambda y: y['fy'])]))
    movers.sort(key=lambda r: -r['net'])

    # --------------------------------------------------- the two named line series
    def series(match):
        out = collections.defaultdict(lambda: [0.0, 0.0, 0])
        for r in recs:
            if match(r['key']):
                out[r['fy']][0] += r['budgeted']
                out[r['fy']][1] += r['spent']
                out[r['fy']][2] += 1
        return [dict(fy=fy, budgeted=b, spent=a, lines=n, pct=a / b - 1)
                for fy, (b, a, n) in sorted(out.items())]

    tuition = series(lambda k: 'tuition' in k)
    sped_staff = series(lambda k: ('special ed' in k or 'specl ed' in k)
                        and 'tuition' not in k)
    if not tuition or not sped_staff:
        sys.exit('the tuition or special-education staffing filter matched no lines. An '
                 'empty series is a broken filter, not a district with no placements.')

    # ------------------------------------------------------------------ FY21 itself
    fy21 = [r for r in rows if r['fy'] == 2021 and r['settled'] is not None
            and r['actual'] is not None and r['settled'] > MIN_BUDGET]
    identical = sum(1 for r in fy21 if abs(r['settled'] - r['actual']) < 1)
    ordinary = []
    for fy in years:
        pairs = [r for r in rows if r['fy'] == fy and r['settled'] is not None
                 and r['actual'] is not None and r['settled'] > MIN_BUDGET]
        if len(pairs) >= MIN_LINES_PER_YEAR:
            same = sum(1 for r in pairs if abs(r['settled'] - r['actual']) < 1)
            ordinary.append(dict(fy=fy, lines=len(pairs), identical=same,
                                 share=same / len(pairs)))

    # ------------------------------------------- where the documents disagree, kept
    disagree = list(db.execute("""
        SELECT fy, stage, COUNT(*) AS cells
        FROM   (SELECT DISTINCT line_key, fy, stage FROM budget_figure
                WHERE variant = '' AND documents_disagree = 1)
        GROUP BY fy, stage ORDER BY fy, stage"""))
    kept = list(db.execute("""
        SELECT label, fy, stage, COUNT(DISTINCT value) AS readings,
               MIN(CAST(value AS REAL)) AS lo, MAX(CAST(value AS REAL)) AS hi
        FROM   line_history_disagreements
        WHERE  stage IN ('settled', 'actual')
        GROUP BY label, fy, stage
        HAVING readings > 1
        ORDER BY (hi - lo) DESC LIMIT 8"""))

    # ------------------------------ WHICH YEARS ARE WHICH: the evidence behind column two
    #
    # FAIL CLOSED. A join that matches nothing looks exactly like data that is absent, and
    # here an empty join would publish a page claiming no document supports any year.
    if not os.path.exists(BASIS_CSV):
        sys.exit(f'{os.path.relpath(BASIS_CSV, ROOT)} is not here. Every year on this page '
                 'is labelled with the basis of the documents behind it, and an unlabelled '
                 'year is the error this page was rewritten to stop making.')
    basis_of = {r['path']: r for r in csv.DictReader(open(BASIS_CSV, encoding='utf-8'))}
    if not basis_of:
        sys.exit('document-basis.csv has no rows — the classification is empty, which is '
                 'not the same thing as documents with no classification.')

    doc_rows = list(db.execute(
        'SELECT fy, doc_id, COUNT(*) AS rows_n FROM budget_figure '
        'WHERE stage = ? AND variant = \'\' GROUP BY fy, doc_id ORDER BY fy, doc_id',
        (RESTATED_STAGE,)))
    if not doc_rows:
        sys.exit(f'no budget_figure rows at stage={RESTATED_STAGE!r}. The page is built on '
                 'them; an empty result is a broken stage name, not a district that never '
                 'reported a prior year.')
    unclassified = sorted({r['doc_id'] for r in doc_rows if r['doc_id'] not in basis_of})
    if unclassified:
        sys.exit('these documents supply the second column and are not classified in '
                 'document-basis.csv, so the page cannot say what they are:\n  '
                 + '\n  '.join(unclassified))

    ledger_years = sorted({r['fy'] for r in db.execute(
        'SELECT DISTINCT fy FROM ledger_snapshot')})
    ledger_snapshots = [
        dict(doc=r['doc_id'], fy=r['fy'], period=r['period'], accounts=r['accounts'])
        for r in db.execute(
            'SELECT doc_id, fy, period, COUNT(*) AS accounts FROM ledger_snapshot '
            'GROUP BY doc_id, fy, period ORDER BY fy, period, doc_id')]
    ledger_accounts = sum(r['accounts'] for r in ledger_snapshots)
    if not ledger_years or not ledger_accounts:
        sys.exit('ledger_snapshot is empty. The page states which years ARE ledger-backed; '
                 'with no rows it would state that none are, which is a different claim.')
    ledger_docs = [dict(path=r['path'], why=(r['ledger_why'] or '').strip())
                   for r in sorted((v for v in basis_of.values()
                                    if v['source_type'] == 'ledger'),
                                   key=lambda v: v['path'])]
    if not ledger_docs:
        sys.exit('document-basis.csv classifies no document as a ledger. The page names '
                 'them; an empty list would read as an archive with no accounting record '
                 'in it at all.')

    per_year = collections.defaultdict(lambda: collections.Counter())
    docs_year = collections.defaultdict(set)
    for r in doc_rows:
        per_year[r['fy']][basis_of[r['doc_id']]['source_type']] += r['rows_n']
        docs_year[r['fy']].add(r['doc_id'])
    measured = set(years)
    basis_by_year = [
        dict(fy=fy,
             rows=sum(per_year[fy].values()),
             source_types=dict(sorted(per_year[fy].items())),
             documents=sorted(docs_year[fy]),
             ledger_backed=fy in ledger_years,
             measured=fy in measured)
        for fy in sorted(per_year)]

    doc_types = collections.Counter(
        basis_of[d]['source_type'] for d in {r['doc_id'] for r in doc_rows})
    evidence = dict(
        stage=RESTATED_STAGE,
        documents=len({r['doc_id'] for r in doc_rows}),
        document_types=dict(sorted(doc_types.items())),
        by_year=basis_by_year,
        # The one snapshot that answers the question this page asks -- the deepest
        # period, the most accounts -- named rather than left for a reader to pick out of
        # eleven. It is the FY2026 general fund at period 12.
        ledger=dict(years=ledger_years, snapshots=ledger_snapshots,
                    deepest=max(ledger_snapshots,
                                key=lambda r: (r['fy'], r['period'], r['accounts'])),
                    accounts=ledger_accounts, documents=ledger_docs),
        measured_years_ledger_backed=sorted(measured & set(ledger_years)),
        measured_years_restated_only=sorted(measured - set(ledger_years)))

    # ---------------------------------------------------- the registry, rule 7c
    #
    # The limit this page states -- that over-budgeting cannot be settled before FY2026
    # because both halves of the comparison come out of the same budget book -- is a
    # REGISTERED gap, not an observation invented here. The registry outranks the page, so
    # the page quotes the row rather than paraphrasing it, and the build fails if the row
    # goes away: a limit stated in one paragraph of one page is invisible to everybody who
    # did not read that page.
    gaps = [dict(side=r['side'], what=r['what'], why=r['why'])
            for r in db.execute('SELECT side, what, why FROM money_gaps')
            if 'per line, in any year before' in r['what']
            or 'came in under plan' in r['what']]
    if not gaps:
        sys.exit('no money_gaps row covers what this page cannot settle. Rule 7c says that '
                 'limit is registered rather than written into one page, and the join that '
                 'reads it back matched nothing.')

    # ------------------------------------------- the analysis this page stands on
    reports = json.load(open(REPORTS, encoding='utf-8'))
    by_id = {r['id']: r for r in reports['reports']}
    doc = by_id.get('budget-vs-actual')
    if doc is None:
        sys.exit('reports.json no longer carries budget-vs-actual. The page links to the '
                 'analysis by id; a missing id is a broken link, not an absent document.')

    # The two questions this sweep is structurally unable to answer, each of which HAS
    # been answered somewhere else. Resolved through reports.json rather than typed as
    # URLs, so a renamed analysis breaks the build here instead of shipping a dead link.
    RELATED = [
        ('athletics-ledger',
         'Where a general-fund line is net of what fees already paid for, read against the '
         'revolving fund that paid it.'),
        ('fy26-closeout',
         'The one year the town\'s own ledger can be read line by line — including the '
         'transfers a budget document cannot show.'),
        ('connecting-the-budget',
         'What can be followed from what was budgeted to what was spent, and the level at '
         'which it stops.'),
    ]
    related = []
    for rid, why in RELATED:
        r = by_id.get(rid)
        if r is None:
            sys.exit(f'reports.json no longer carries {rid}, which this page links to.')
        related.append(dict(id=rid, title=r['title'], why=why,
                            url=r['markdown']['url'], words=r['words']))

    # ---------------------------------------------------- what this page CONCLUDES
    #
    # RULE 8 IS THE WHOLE DIFFICULTY HERE. This is the report most at risk of turning
    # into an audit, and "line X overspent by Y%" is an accusation with a number on it,
    # not a finding. What a resident actually needs from a budget-against-spending sweep
    # is what a budget can and cannot tell them: which parts of it are dependable, which
    # are structurally unforecastable, and whether the thing everybody says at meetings --
    # that the schools ask for more than they need -- is in the documents. It is not, and
    # rule 8 asks for that to be said with the same weight as anything else.
    #
    # The documentary half stays out. That both columns before FY2026 come out of the
    # same budget book is a REGISTERED gap (`gaps`, above) and a stage note inside each
    # conclusion -- never a conclusion of its own. A defect in a document is a footnote.
    worst_year = max(year_rows, key=lambda r: abs(r['pct']))
    within2 = sum(s['count'] for s in spread if s['centred'])
    big_miss = sum(s['count'] for s in spread if s['hi'] <= -0.25 or s['lo'] >= 0.25)
    by_section = {r['section']: r for r in section_rows}
    sal, rest = by_section['Salaries'], by_section['Everything else']
    t_over = max(r['pct'] for r in tuition)
    t_under = min(r['pct'] for r in tuition)
    sped_worst = max(abs(r['pct']) for r in sped_staff)
    sw_under = sum(1 for r in same_way if r['direction'] == 'under')
    concl = [
        conclusion(
            id='the-total-is-dependable-and-the-lines-are-not',
            claim='Budget rows that landed within two per cent of their own plan',
            so_what='The bottom line is dependable and any single row in it is not. A budget is a plan, not a promise.',
            lede=(
                'No measured year’s reported spending landed further than %s from the '
                'budget printed beside it — and underneath that, only %s of %s line-years '
                'landed within %s of their own line. The total is dependable; any single '
                'line in it is not.'
                % (C.pct(100 * abs(worst_year['pct'])), C.num(within2), C.num(len(recs)),
                   C.pct(100 * SAME_WAY, 0))),
            detail=(
                'That is what a budget of this kind is: a plan whose parts absorb one '
                'another. Salaries came in %s under across %s line-years and everything '
                'else %s over across %s, and the two very nearly cancel. Underneath them '
                '%s of the %s line-years missed by more than a quarter, in both '
                'directions. So a resident or a Finance Committee member can rely on the '
                'bottom line and should not read one line’s number as a forecast of that '
                'line. Both columns come out of the district’s own budget books — a budget '
                'printed beside a prior year the same publisher restated — so this is a '
                'pattern in what the district reports about itself, not a reading of the '
                'town’s books.'
                % (C.pct(100 * abs(sal['pct'])), C.num(sal['line_years']),
                   C.pct(100 * rest['pct']), C.num(rest['line_years']),
                   C.num(big_miss), C.num(len(recs)))),
            figures={
                'worst': figure(100 * abs(worst_year['pct']),
                                C.pct(100 * abs(worst_year['pct']))),
                'within2': figure(within2, C.num(within2), 'of %s' % C.num(len(recs))),
                'line_years': figure(len(recs), C.num(len(recs))),
                'band': figure(100 * SAME_WAY, C.pct(100 * SAME_WAY, 0)),
                'salaries_pct': figure(100 * abs(sal['pct']), C.pct(100 * abs(sal['pct']))),
                'salaries_line_years': figure(sal['line_years'], C.num(sal['line_years'])),
                'rest_pct': figure(100 * rest['pct'], C.pct(100 * rest['pct'])),
                'rest_line_years': figure(rest['line_years'], C.num(rest['line_years'])),
                'big_miss': figure(big_miss, C.num(big_miss)),
            },
            figure='within2',
            kind='measured',
            basis=(
                'budget_figure, stage `settled` against stage `restated`, each year against '
                'its own year, %s–%s. The %s documents behind the second column are '
                'classified in document-basis.csv as restatements and forward budget books; '
                'none is an accounting record. FY21 is excluded because its restated column '
                'is its budget, and years with fewer than %d usable lines are excluded.'
                % (C.fy(years[0]), C.fy(years[-1]), C.num(evidence['documents']),
                   MIN_LINES_PER_YEAR)),
            not_shown=(
                'Whether a line coming in under is a saving. A post left vacant, a service '
                'that did not happen, a grant that paid instead, money moved to another '
                'line and a line over-budgeted from the start all produce the same smaller '
                'number, and a budget document cannot show an approved mid-year transfer at '
                'all. Both columns are also the town’s net general-fund share, so a line '
                'that rose because a grant ended looks exactly like a line that got more '
                'expensive.'),
            see=[('/money-outside-the-budget', 'the funds these two columns never show'),
                 ('/what-we-cannot-answer', 'what cannot be answered')],
        ),
        conclusion(
            id='nothing-in-this-budget-is-quietly-over-provided',
            claim='School budget rows that miss the same way every year, all by small amounts',
            so_what='The misses look like noise rather than lines quietly over-provided.',
            lede=(
                'Only %s of the %s school budget lines with four or more measured years '
                'miss the same way in every one of them, and the largest averages %s. The '
                'misses in this budget look like noise, not like lines quietly '
                'over-provided.'
                % (C.num(len(same_way)), C.num(len(multi)),
                   C.usd(abs(same_way[0]['mean_dollars'])))),
            detail=(
                '%s of the %s land under their own line and the rest over, and every one of '
                'them is small: the largest is special education transportation at %s a '
                'year below plan, and the next is %s. A padded budget shows up as the same '
                'lines over-provided year after year, and that pattern is not in these '
                'documents. What it establishes is a pattern in the district’s own budget '
                'books restating themselves — the %s ledger is the only accounting record '
                'the archive holds for school spending, and it is not one of the measured '
                'years.'
                % (C.num(sw_under), C.num(len(same_way)),
                   C.usd(abs(same_way[0]['mean_dollars'])),
                   C.usd(abs(same_way[1]['mean_dollars'])),
                   C.fy(evidence['ledger']['deepest']['fy']))),
            figures={
                'same_way': figure(len(same_way), C.num(len(same_way)),
                                   'of %s rows' % C.num(len(multi))),
                'lines': figure(len(multi), C.num(len(multi))),
                'largest': figure(abs(same_way[0]['mean_dollars']),
                                  C.usd(abs(same_way[0]['mean_dollars']))),
                'next': figure(abs(same_way[1]['mean_dollars']),
                               C.usd(abs(same_way[1]['mean_dollars']))),
                'under': figure(sw_under, C.num(sw_under)),
                'ledger_fy': figure(evidence['ledger']['deepest']['fy'],
                                    C.fy(evidence['ledger']['deepest']['fy'])),
            },
            figure='same_way',
            kind='measured',
            basis=(
                'Every line with four or more usable line-years in the %s–%s sweep, each '
                'year’s settled budget against the same year’s restated figure out of the '
                'district’s own budget books. A line counts as missing the same way only '
                'where it is more than %s off in every one of its years.'
                % (C.fy(years[0]), C.fy(years[-1]), C.pct(100 * SAME_WAY, 0))),
            not_shown=(
                'That a line missing the same way every year was set wrong. A line reliably '
                'under can be a service the town reliably does not use all of, and a '
                'restatement cannot distinguish that from an estimate set too high. Nor '
                'does the absence of a pattern here cover the lines the sweep never '
                'reaches: most of the workbook’s lines are published at only one stage in '
                'any given year and are not measured at all.'),
            see=[('/reports', 'the written analysis behind this page')],
        ),
        conclusion(
            id='tuition-is-the-line-nobody-can-forecast',
            claim='How far below plan out-of-district tuition landed in its worst measured year',
            so_what='The schools do not set that price or choose how many need it. Their own staffing lands within six per cent.',
            lede=(
                'Out-of-district tuition is the line nobody can forecast: across %s '
                'measured years the district’s own books report it from %s over the budget '
                'to %s under, while special education staffing never missed by more '
                'than %s.'
                % (C.num(len(tuition)), C.pct(100 * t_over), C.pct(100 * abs(t_under)),
                   C.pct(100 * sped_worst))),
            detail=(
                'When a child’s plan requires a school the district cannot provide, the '
                'town pays another school: it does not set the price, does not choose how '
                'many children need it, and cannot say no. The part the district does '
                'control behaves nothing like it — special education staffing lands within '
                '%s in every one of those years. So a budget can be expected to be about '
                'right on the staffing and cannot be expected to be right on the '
                'placements, and a year in which tuition lands far from plan is not '
                'evidence that anybody planned badly. Both columns are the district '
                'restating its own budget book rather than a ledger.'
                % C.pct(100 * sped_worst)),
            figures={
                'years': figure(len(tuition), C.num(len(tuition))),
                'over': figure(100 * t_over, C.pct(100 * t_over)),
                'under': figure(100 * abs(t_under), C.pct(100 * abs(t_under))),
                'sped_worst': figure(100 * sped_worst, C.pct(100 * sped_worst)),
            },
            figure='under',
            kind='measured',
            basis=(
                'The lines whose keys carry `tuition`, and the special education staffing '
                'lines that do not, summed per year and compared budget against restated '
                'figure within the same year, %s–%s, out of the district’s own budget '
                'books. No rate of change is taken across the two kinds of column.'
                % (C.fy(years[0]), C.fy(years[-1]))),
            not_shown=(
                'Why any year missed. A tuition line under plan can be fewer placements, '
                'cheaper placements, a placement that started part way through the year, or '
                'cost carried by the circuit breaker reimbursement or another fund that '
                'never appears in the appropriation. And dollars are not children: none of '
                'these columns counts a placement.'),
            see=[('/what-special-education-costs', 'what special education actually costs'),
                 ('/who-ends-up-out-of-district', 'who ends up out of district')],
        ),
    ]

    return dict(
        conclusions=emit('budget-vs-actual', concl),
        generated_by='scripts/build_variance_charts.py',
        source='sources/data/lunenburg.db — budget_figure, lps_budget_lines, '
               'variance_by_group, line_history_disagreements',
        coverage=dict(
            line_years=len(recs), lines=len({r['key'] for r in recs}),
            first_fy=years[0], last_fy=years[-1], years=years,
            groups=len(groups),
            excluded=[dict(why=w, line_years=n) for w, n in dropped.most_common()],
            excluded_total=sum(dropped.values()),
            workbook_lines=len(section),
            workbook_lines_never_measured=len(set(section) - {r['key'] for r in recs}),
            min_lines_per_year=MIN_LINES_PER_YEAR, min_budget=MIN_BUDGET,
            same_way_threshold=SAME_WAY, drift_threshold=DRIFT),
        evidence=evidence,
        gaps=gaps,
        by_year=year_rows,
        sections=section_rows,
        groups=groups,
        spread=spread,
        within_2pct=sum(s['count'] for s in spread if s['centred']),
        same_way=same_way,
        lines_with_four_years=len(multi),
        biggest_over=movers[:8],
        biggest_under=movers[::-1][:8],
        tuition=tuition,
        sped_staff=sped_staff,
        fy21=dict(lines=len(fy21), identical=identical,
                  share=identical / len(fy21) if fy21 else 0,
                  ordinary=ordinary),
        disagreements=dict(
            cells=sum(r['cells'] for r in disagree),
            by_year=[dict(fy=r['fy'], stage=r['stage'], cells=r['cells'])
                     for r in disagree],
            widest=[dict(line=r['label'], fy=r['fy'], stage=r['stage'],
                         readings=r['readings'], lo=r['lo'], hi=r['hi'])
                    for r in kept]),
        related=related,
        analysis=dict(title=doc['title'], about=doc['about'], words=doc['words'],
                      updated=doc['updated'], markdown=doc['markdown']['url'],
                      pdf=(doc.get('pdf') or {}).get('url')),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='fail if the published file is not what this would write')
    a = ap.parse_args()
    payload = json.dumps(build(), indent=1, sort_keys=True) + '\n'
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if have != payload:
            print(f'STALE — {os.path.relpath(OUT, ROOT)} is not what the database '
                  f'now produces. Run scripts/build_variance_charts.py.')
            return 1
        print(f'ok — {os.path.relpath(OUT, ROOT)} reproduces from the database')
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(payload)
    d = json.loads(payload)
    print(f"wrote {os.path.relpath(OUT, ROOT)} — {d['coverage']['line_years']} usable "
          f"line-years, {d['coverage']['lines']} lines, {d['coverage']['groups']} groups, "
          f"FY{d['coverage']['first_fy'] % 100}–FY{d['coverage']['last_fy'] % 100}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
