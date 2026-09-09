#!/usr/bin/env python3
"""What Lunenburg spends per pupil, against other districts -- and what a ratio hides.

    python3 scripts/build_peer_spending.py
    python3 scripts/build_peer_spending.py --check

Writes `fy28/public/data/peer-spending.json`, which /what-other-districts-spend renders.

WHAT THIS IS, PRECISELY. DESE's end-of-year finance collection: every district's spending
by function, ALL FUNDS, with a per-pupil figure DESE computes itself. FY2009-FY2025, one
stage throughout -- what districts reported after the year closed. Nothing here is a
budget, and nothing here is differenced against one (rule 1).

RULE 11 IS THE FIRST THING THE PAGE SAYS, BECAUSE THIS MEASURE IS NOT THE TOWN'S BILL.
DESE's total counts grants, revolving funds, school choice and gifts, and it counts
town-paid insurance and retirement attributed to the schools -- $3,459 a pupil for
Lunenburg in FY2025 on its own. It is NOT the school appropriation, it is NOT what
Lunenburg taxpayers pay, and the difference between it and the appropriation is not
hidden money. It is two definitions.

THE THREE THINGS THIS PAGE HAD TO GET RIGHT, EACH OF WHICH IS ASSERTED HERE.

1.  THE ROLLUP TRAP. `dese_function_expenditure` carries four levels in one table --
    total, rollup, category, detail -- and `dese_ch70_formula` and `dese_ch70_aid_factor`
    carry a STATE row with lea `00000000` beside the districts. Summing across a level or
    including the state row produces a number an order of magnitude wrong. Every query
    here names its level, and `assert_levels()` refuses to write if the levels or the
    state row stop being separable.

2.  A PER-PUPIL FIGURE IS A RATIO AND BOTH HALVES MOVE. The whole page turns on this, so
    the decomposition is exact rather than described: for each district, the FY2012-FY2025
    change in spending, the change in pupils, and the identity
    (1+spend) / (1+pupils) = (1+per pupil), checked to four decimal places.

3.  DESE USES TWO DIFFERENT DENOMINATORS AND LABELS THEM THE SAME. The `TTPP` total is
    per TOTAL FTE pupils; every other row -- the in-district rollup and all eleven
    categories -- is per IN-DISTRICT FTE pupils. Verified here against DESE's own dollar
    totals across 7 districts and 17 years, 0 exceptions. `dese_function_statewide` labels
    the TTPP row `per pupil, in-district FTE`, which is OUR label written by
    `extract_dese_finance.py` and it is wrong on that row. The page states the verified
    basis and never quotes the label -- rule 13, an instrument that reformats before you
    see it is part of the finding.

THE PEER SET IS OURS AND THE PAGE SAYS SO. RADAR covers all 421 Massachusetts districts;
this archive extracts six for size (see `extract_dese_radar.py`). No document in the
archive records the criterion by which those six were chosen. So the HEADLINE rests on
DESE's own statewide distribution -- 318 districts in FY2025, with quartiles and a rank --
and the six are used for texture, never to carry a claim on their own. That is registered
as a gap rather than argued away.

WHAT IS NOT ESTABLISHED, AND THE PAGE SAYS SO IN THOSE WORDS. Any relation between
spending and MCAS results. Whether a low figure is a choice or a constraint. What any of
it buys. Rule 7 governs the whole page: the arithmetic is exact and every explanation for
it is a hypothesis.

THE JOINS ARE ASSERTED. A join that matches nothing looks exactly like a district that
spends nothing. Every one here refuses to write rather than write an empty series.
"""
import argparse
import collections
import csv
import json
import os
import re
import sqlite3
import statistics
import sys

# The conclusions this report states, as DATA rather than as sentences in a page. See
# scripts/conclusions.py.
import conclusions as C
from conclusions import conclusion, emit, figure

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'peer-spending.json')

LEA = '01620000'
TOWN = 'Lunenburg'
MINUTES = 'sources/meetings/text'

# FY2012 is the first year all six of the CURRENT districts exist. Ayer (lea 00190000)
# and Shirley regionalised into Ayer Shirley (06160000) for FY2012, so FY2009-FY2011 hold
# a different set of six and no series may be drawn across the join without saying so.
FIRST_COMPARABLE_FY = 2012
AYER = '00190000'
AYER_SHIRLEY = '06160000'

# The finance year the page is anchored on. The Chapter 70 standing figures run one year
# further and are a DIFFERENT collection at a DIFFERENT stage; they are never differenced
# against these (rule 1).
FIN_FY = 2025
CH70_FY = 2026

# A district does not lose fourteen years of finance history. If a query comes back short,
# something moved underneath and publishing it would present a truncated series as whole.
MIN_YEARS = 14
MIN_DISTRICTS = 6

# The three workbooks, by manifest key. Read out of the manifest rather than typed, so a
# citation cannot lose its hash silently (rules 2 and 12).
DOCS = [
    dict(key='state-dese/district-expenditures-by-function.xlsx',
         what='Every district’s spending by function, all funds, with DESE’s own '
              'per-pupil figure. The source of every dollar and every per-pupil figure '
              'on this page.',
         publisher='Massachusetts Department of Elementary and Secondary Education',
         stage='reported after the year closed — end-of-year finance collection. '
               'Not a budget.'),
    dict(key='state-dese/radar-district-comparison.xlsx',
         what='DESE’s RADAR district comparison — enrollment, demographics, staffing FTE, '
              'average teacher salary and MCAS, for all 421 Massachusetts districts. The '
              'source of the denominators, the staffing and the results on this page.',
         publisher='Massachusetts Department of Elementary and Secondary Education',
         stage='reported for the fiscal year. Not a budget.'),
    dict(key='state-dese/dese-ch70-district-profile.xlsx',
         what='DESE’s Chapter 70 district profile — required local contribution, required '
              'net school spending, and what each district actually spends against it.',
         publisher='Massachusetts Department of Elementary and Secondary Education',
         stage='the Chapter 70 calculation for the fiscal year. The net school spending '
               'column carries its own stage per year and this page splits on it.'),
]

# Public comment and reports this page quotes, by board, date and the town's own document
# number. Every quote is re-read out of the extracted minutes on every run: a quote is a
# claim about a document, and an extractor can change what a document renders to.
QUOTES = [
    dict(key='bottom-ten', board='school-committee', date='2024-01-24', kind='minutes',
         doc='6375',
         quote='According to Massachusetts State reports Lunenburg per pupil expenditure '
               'is listed 361 out of 401 districts in Massachusetts. This means that '
               "we're in the top 20% for school performance while being in the bottom "
               '10% for spending',
         who='public comment',
         why='The claim this page was built to check, made at a School Committee meeting '
             'about proposed cuts. The spending half checks out on DESE’s own '
             'distribution — see the rank below, on a different district count. The '
             'performance half cannot be checked here: this archive holds MCAS for six '
             'districts and no statewide distribution of it.'),
    dict(key='little-per-pupil', board='school-committee', date='2024-01-24',
         kind='minutes', doc='6375',
         quote='Lunenburg has a long and well established history of spending little per '
               'pupil and still having an amazing school district',
         who='public comment',
         why='The long half of this is measurable and it holds: Lunenburg has been in the '
             'bottom quarter of Massachusetts districts by total per-pupil spending in '
             'every one of the seventeen years DESE publishes here.'),
    dict(key='printout', board='school-committee', date='2024-02-07', kind='minutes',
         doc='6395',
         quote='As a visual my co mment is written on a print out of school per pupil '
               'expenditures for every district in Massachusetts ranked from those '
               'spending the most to the least. Lunenburg is highlighted on the last pa',
         who='the president of the Lunenburg Education Association',
         why='The same measurement, held up at a meeting as a printed page. It is the '
             'reason this page exists at an address rather than in a spreadsheet.'),
    dict(key='materials', board='school-committee', date='2024-02-07', kind='minutes',
         doc='6395',
         quote='Teachers have learned to spend school budgeted money at the start of the '
               'y ear otherwise they and their students are penalized because a frozen '
               'budget in November means an inability to purchase needed materia ls '
               'later in the school year. Teachers and parents donate supplies',
         who='the president of the Lunenburg Education Association',
         why='Said in the same year the instructional materials, equipment and technology '
             'line is the figure below. The two are printed together because a reader '
             'with this concern will find the number anyway. It is not evidence that one '
             'caused the other, and nothing here tests that.'),
    dict(key='sharing-pd', board='school-committee', date='2024-10-16', kind='minutes',
         doc='6830',
         quote='The North Middlesex superintendent reached out to me about potentially '
               'sharing resources as we have done in the past. Professional development '
               'with north Middlesex, they were looking for other opportunities to share '
               'resources',
         who='the Superintendent of Schools',
         why='Said about the line this page finds the lowest in the set, and it is the '
             'district doing the obvious sensible thing about it. A district spending $48 '
             'a pupil on professional development that is sharing it with a neighbour is '
             'a different fact from one that is not, and neither the DESE figure nor this '
             'page could have told you which.'),
    dict(key='grant-pd', board='school-committee', date='2026-02-04', kind='minutes',
         doc='7634',
         quote='the remaining $17,000 will be dedicated to contracted professional '
               'development. This week our legislators have approved one-time earmarked '
               'funds, $36,000 is going toward touch view screens at the Primary School, '
               '$7,000 will fund IXL for our middle school students',
         who='the Superintendent of Schools',
         why='Rule 11 made concrete, in the district’s own words. This is grant money '
             'buying professional development and materials — the two lines this page '
             'finds furthest below the state. DESE counts it in the totals here, the '
             'town’s appropriation does not, and neither source says how much of either '
             'line is grant-funded in any given year.'),
    dict(key='vocational', board='school-committee', date='2026-03-23', kind='minutes',
         doc='7732',
         quote='bringing back things like vocational programs to the school, even if it '
               "means that we'd have to disentangle ourselves from Monty Tech that "
               'is something that has real long-term value',
         who='the Chair of the School Committee, in the Chair\u2019s report',
         why='Said about the district that takes more Lunenburg children than every other '
             'destination combined, in the same meeting as a balanced budget the charter '
             'compelled. It is the destination comparison above being argued about in the '
             'room: Monty Tech spends the most for each pupil of anywhere Lunenburg '
             'children go, and the town is a member and is assessed for it. Nothing here '
             'tests whether disentangling would cost the town more or less.'),
    dict(key='outcomes', board='school-committee', date='2026-06-24', kind='minutes',
         doc='7869',
         quote='neighboring districts such as Lancaster, Ayer/Shirley, Groton, Pepperell, '
               'Townsend, Leominster, and Fitchburg have faced similar challenges while '
               'achieving stronger outcomes',
         who='public comment',
         why='The comparison run the other way, after the override failed. Two of the '
             'districts named are in the set below. The MCAS section prints what this '
             'archive holds for all six and says plainly that nothing in it tests any '
             'relation to spending.'),
]

SEARCHED = ['per pupil', 'more with less', 'professional development',
            'instructional materials', 'sharing resources', 'neighboring district',
            'surrounding town', 'comparable district', 'lowest spending',
            # Rule 15a, for the destination section: what the town has said about the
            # places its children actually go.
            'Monty Tech', 'school choice', 'vocational', 'charter school']

# Rows this page CITES out of `money_gaps`. Cited by their `what`, so a renamed row fails
# the build rather than rendering a gap with no reason on it.
CITES_GAPS = [
    'How much of a receiving district’s per-pupil spending Lunenburg actually pays',
    'Why these six districts and not six others',
    'What DESE’s per-pupil figure buys',
    'Whether Lunenburg’s MCAS results are high or low for Massachusetts',
    'Whether spending less per pupil is a choice or a constraint',
]


def fail(msg):
    raise SystemExit('%s\nNothing written.' % msg)


def q(db, sql, *args):
    cur = db.execute(sql, args)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def documents():
    """The workbooks, read out of the manifest rather than typed (rules 2 and 12)."""
    have = {}
    with open(MANIFEST, encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            have[row['key']] = row
    out = []
    for d in DOCS:
        row = have.get(d['key'])
        if not row:
            fail('%s is not in the archive manifest. A figure without its document is '
                 'not publishable.' % d['key'])
        out.append(dict(d, path='sources/' + d['key'], sha256=row['sha256'],
                        bytes=int(row['bytes']), url=row['upstream'],
                        docs_url='/docs/' + d['key'],
                        filename=d['key'].split('/')[-1]))
    return out


def assert_levels(db):
    """The rollup trap, asserted rather than avoided by care.

    Three separate tables here mix rollups with detail. If the columns that separate them
    stop separating them, every total on this page silently becomes a sum of a thing and
    itself."""
    levels = {r['level'] for r in q(db, 'SELECT DISTINCT level FROM dese_function_expenditure')}
    want = {'total', 'rollup', 'category', 'detail'}
    if levels != want:
        fail('dese_function_expenditure carries levels %s, not %s. Every total on this '
             'page is scoped by level and the scoping no longer means what it meant.'
             % (sorted(levels), sorted(want)))

    # The total row must be exactly one function code, and the rollups exactly two, or
    # `level='total'` stops meaning "the district's whole spending".
    codes = {r['level']: {x['func_code'] for x in q(
        db, 'SELECT DISTINCT func_code FROM dese_function_expenditure WHERE level=?',
        r['level'])} for r in q(db, 'SELECT DISTINCT level FROM dese_function_expenditure')}
    if codes['total'] != {'TTPP'} or codes['rollup'] != {'IIII', 'OODD'}:
        fail('the total/rollup rows are %s / %s, not TTPP / IIII+OODD.'
             % (sorted(codes['total']), sorted(codes['rollup'])))

    # The state row in the Chapter 70 tables. It is 20 to 500 times any district here and
    # is separated by `level`, not by anything in the name.
    for table in ('dese_ch70_formula', 'dese_ch70_aid_factor'):
        rows = q(db, 'SELECT DISTINCT level, lea FROM %s WHERE level!=?' % table, 'district')
        if not rows:
            fail('%s no longer carries a state row distinguishable by `level`. It did, '
                 'and every district query here excludes it by that column.' % table)
        if {r['lea'] for r in rows} != {'00000000'}:
            fail('%s has non-district rows for lea %s, not just the state row.'
                 % (table, sorted({r['lea'] for r in rows})))

    # And the state row must NOT be in the finance table, where nothing excludes it.
    stray = q(db, "SELECT DISTINCT lea FROM dese_function_expenditure WHERE lea='00000000'")
    if stray:
        fail('dese_function_expenditure now carries a state row (lea 00000000). Every '
             'district query on this page would include it.')


def fte_index(db):
    rows = q(db, "SELECT lea, fy, measure, value FROM dese_measure "
                 "WHERE measure IN ('In-District FTE Pupils','Total FTE Pupils')")
    if not rows:
        fail('no FTE pupil counts matched. A per-pupil page whose denominator query '
             'returns nothing would publish ratios with no ratio in them.')
    idx = {}
    for r in rows:
        idx.setdefault((r['lea'], r['fy']), {})[r['measure']] = r['value']
    return idx


def denominators(db, fte):
    """WHICH FTE COUNT EACH PER-PUPIL FIGURE IS OVER, derived rather than believed.

    DESE publishes one column headed per-pupil and computes it over two different
    denominators: the TTPP total over TOTAL FTE pupils, everything else over IN-DISTRICT
    FTE pupils. `dese_function_statewide.per_pupil_basis` says in-district on both, and
    that string is ours, written by extract_dese_finance.py. So it is not quoted; the
    arithmetic is tested against DESE's own dollar totals, on every row, every run."""
    rows = q(db, 'SELECT lea, district, fy, level, func_code, total, per_pupil '
                 'FROM dese_function_expenditure WHERE per_pupil > 0')
    if not rows:
        fail('no per-pupil rows matched. Refusing to publish a denominator finding '
             'derived from nothing.')
    tally = collections.Counter()
    bad = []
    for r in rows:
        f = fte.get((r['lea'], r['fy']))
        if not f:
            bad.append('%s FY%d has spending and no FTE count' % (r['district'], r['fy']))
            continue
        ind = r['total'] / f['In-District FTE Pupils']
        tot = r['total'] / f['Total FTE Pupils']
        want = 'total' if r['func_code'] == 'TTPP' else 'in-district'
        got = ind if want == 'in-district' else tot
        other = tot if want == 'in-district' else ind
        if abs(got - r['per_pupil']) > 1.0:
            bad.append('%s FY%d %s: DESE prints %.0f; over %s FTE it is %.0f'
                       % (r['district'], r['fy'], r['func_code'], r['per_pupil'],
                          want, got))
        elif abs(other - r['per_pupil']) <= 1.0:
            # Not a failure -- the two counts can coincide -- but it means this row does
            # not distinguish the denominators, so it is not counted as evidence.
            tally['ambiguous'] += 1
            continue
        tally[want] += 1
    if bad:
        fail('DESE’s per-pupil column no longer reproduces from its own dollar total over '
             'the FTE count this page says it uses, in %d place(s):\n  %s'
             % (len(bad), '\n  '.join(bad[:8])))
    if not tally['total'] or not tally['in-district']:
        fail('the denominator test distinguished nothing (%s). It is the assertion that '
             'lets this page print a total and a category on the same screen.'
             % dict(tally))
    return dict(rows_tested=len(rows), total_fte=tally['total'],
                in_district_fte=tally['in-district'], ambiguous=tally['ambiguous'],
                tolerance=1.0,
                label_in_our_table='per pupil, in-district FTE',
                label_is_wrong_on='TTPP — the district total, which is over TOTAL FTE '
                                  'pupils. The label is ours, not DESE’s: it is written '
                                  'by extract_dese_finance.py.')


def district_set(db):
    rows = q(db, "SELECT DISTINCT lea, district FROM dese_function_expenditure "
                 "WHERE level='total' ORDER BY district")
    if len(rows) < MIN_DISTRICTS:
        fail('only %d districts in the finance extract; expected at least %d.'
             % (len(rows), MIN_DISTRICTS))
    span = {r['lea']: r for r in q(
        db, "SELECT lea, MIN(fy) first_fy, MAX(fy) last_fy, COUNT(*) years "
            "FROM dese_function_expenditure WHERE level='total' GROUP BY lea")}
    out = []
    for r in rows:
        s = span[r['lea']]
        out.append(dict(lea=r['lea'], district=r['district'], first_fy=s['first_fy'],
                        last_fy=s['last_fy'], years=s['years'],
                        is_lunenburg=r['lea'] == LEA,
                        in_current_set=s['last_fy'] == FIN_FY))
    if not any(o['is_lunenburg'] for o in out):
        fail('Lunenburg is not in the finance extract.')
    ayer = [o for o in out if o['lea'] == AYER]
    shirley = [o for o in out if o['lea'] == AYER_SHIRLEY]
    if not ayer or not shirley:
        fail('the Ayer / Ayer Shirley regionalisation is not visible in the extract, and '
             'the page states it as the reason its comparable span starts in FY%d.'
             % FIRST_COMPARABLE_FY)
    if ayer[0]['last_fy'] >= shirley[0]['first_fy']:
        fail('Ayer ends FY%d and Ayer Shirley begins FY%d — they overlap, so the six '
             'districts are not six in every year and the page says they are.'
             % (ayer[0]['last_fy'], shirley[0]['first_fy']))
    return out, dict(ayer_last_fy=ayer[0]['last_fy'],
                     ayer_shirley_first_fy=shirley[0]['first_fy'])


def totals(db, fte):
    rows = q(db, "SELECT fy, lea, district, gen_fund, grants_revolving, total, per_pupil "
                 "FROM dese_function_expenditure WHERE level='total' ORDER BY fy, district")
    if not rows:
        fail('the district totals query matched nothing.')
    years = sorted({r['fy'] for r in rows})
    if len(years) < MIN_YEARS:
        fail('only %d years of district totals; a truncated series would be published as '
             'the whole record.' % len(years))
    out = []
    for r in rows:
        f = fte.get((r['lea'], r['fy']))
        if not f:
            fail('%s FY%d has a spending total and no FTE count — the join did not match, '
                 'and an unmatched join looks exactly like a district with no pupils.'
                 % (r['district'], r['fy']))
        if abs(r['gen_fund'] + r['grants_revolving'] - r['total']) > 1.0:
            fail('%s FY%d: general fund plus grants and revolving is %.0f against a '
                 'printed total of %.0f. The fund split is a headline on this page.'
                 % (r['district'], r['fy'],
                    r['gen_fund'] + r['grants_revolving'], r['total']))
        out.append(dict(fy=r['fy'], lea=r['lea'], district=r['district'],
                        total=r['total'], gen_fund=r['gen_fund'],
                        grants_revolving=r['grants_revolving'],
                        grant_share=round(r['grants_revolving'] / r['total'], 4),
                        per_pupil=r['per_pupil'],
                        fte_total=f['Total FTE Pupils'],
                        fte_in_district=f['In-District FTE Pupils']))
    return out, years


def ranked(rows, key='per_pupil'):
    """Rank within the year, highest first — DESE's own convention everywhere here."""
    by_year = collections.defaultdict(list)
    for r in rows:
        by_year[r['fy']].append(r)
    for year in by_year.values():
        order = sorted(year, key=lambda r: -r[key])
        for i, r in enumerate(order):
            r['rank'] = i + 1
            r['of'] = len(order)
    return rows


def decomposition(tot):
    """(1 + spending growth) / (1 + pupil growth) = (1 + per-pupil growth), exactly.

    The page's central claim rests on this being arithmetic rather than an argument, so it
    is checked to four decimal places on every district and refuses to write if it drifts.
    """
    first = {r['district']: r for r in tot if r['fy'] == FIRST_COMPARABLE_FY}
    last = {r['district']: r for r in tot if r['fy'] == FIN_FY}
    if not first or not last:
        fail('the FY%d / FY%d totals did not both match.' % (FIRST_COMPARABLE_FY, FIN_FY))
    out = []
    for d, b in sorted(last.items()):
        a = first.get(d)
        if not a:
            fail('%s has FY%d totals and no FY%d totals; the decomposition would silently '
                 'drop a district.' % (d, FIN_FY, FIRST_COMPARABLE_FY))
        spend = b['total'] / a['total'] - 1
        pupils = b['fte_total'] / a['fte_total'] - 1
        pp = b['per_pupil'] / a['per_pupil'] - 1
        implied = (1 + spend) / (1 + pupils) - 1
        if abs(implied - pp) > 0.005:
            fail('%s: spending %+.2f%% over pupils %+.2f%% implies %+.2f%% per pupil; '
                 'DESE’s own per-pupil figures move %+.2f%%. The identity the page rests '
                 'on no longer holds.'
                 % (d, spend * 100, pupils * 100, implied * 100, pp * 100))
        out.append(dict(
            district=d, is_lunenburg=b['lea'] == LEA,
            spend_from=a['total'], spend_to=b['total'], spend_pct=round(spend, 4),
            pupils_from=a['fte_total'], pupils_to=b['fte_total'],
            pupils_pct=round(pupils, 4),
            per_pupil_from=a['per_pupil'], per_pupil_to=b['per_pupil'],
            per_pupil_pct=round(pp, 4),
            # What FY2025's money is per pupil if each district still had its FY2012
            # pupils. ARITHMETIC, not a counterfactual claim about the world: it is the
            # same numerator over the older denominator, and it is labelled that way.
            at_old_enrollment=round(b['total'] / a['fte_total']),
        ))
    out.sort(key=lambda r: -r['per_pupil_pct'])
    order = sorted(out, key=lambda r: -r['at_old_enrollment'])
    for i, r in enumerate(order):
        r['rank_at_old_enrollment'] = i + 1
    return out


def lunenburg_denominator(tot):
    """The same split for Lunenburg alone, over the years since enrollment turned."""
    series = sorted((r for r in tot if r['lea'] == LEA), key=lambda r: r['fy'])
    a, b = series[0], series[-1]
    hold = b['total'] / a['fte_total']
    return dict(
        from_fy=a['fy'], to_fy=b['fy'],
        spend_from=a['total'], spend_to=b['total'],
        spend_pct=round(b['total'] / a['total'] - 1, 4),
        pupils_from=a['fte_total'], pupils_to=b['fte_total'],
        pupils_pct=round(b['fte_total'] / a['fte_total'] - 1, 4),
        per_pupil_from=a['per_pupil'], per_pupil_to=b['per_pupil'],
        per_pupil_change=b['per_pupil'] - a['per_pupil'],
        at_old_enrollment=round(hold),
        denominator_share=round((b['per_pupil'] - hold)
                                / (b['per_pupil'] - a['per_pupil']), 4))


def statewide(db):
    rows = q(db, "SELECT fy, districts, per_pupil_p25 p25, per_pupil_median median, "
                 "per_pupil_p75 p75, per_pupil_min p_min, per_pupil_max p_max, "
                 "lunenburg_per_pupil lunenburg, lunenburg_rank_of_districts rank "
                 "FROM dese_function_statewide WHERE level='total' ORDER BY fy")
    if not rows:
        fail('the statewide distribution query matched nothing. It is what the headline '
             'rests on, precisely so that the six-district set does not have to.')
    out = []
    for r in rows:
        if r['lunenburg'] is None or r['median'] is None:
            fail('FY%d has no Lunenburg figure or no median in the statewide '
                 'distribution.' % r['fy'])
        m = re.fullmatch(r'(\d+) of (\d+)', r['rank'] or '')
        if not m:
            fail('FY%d rank reads %r, not "<n> of <N>". The page prints how many '
                 'districts spend less, which is derived from it.' % (r['fy'], r['rank']))
        rank, of = int(m.group(1)), int(m.group(2))
        if of != r['districts']:
            fail('FY%d ranks against %d districts and the row says %d.'
                 % (r['fy'], of, r['districts']))
        out.append(dict(fy=r['fy'], districts=of, p25=r['p25'], median=r['median'],
                        p75=r['p75'], p_min=r['p_min'], p_max=r['p_max'],
                        lunenburg=r['lunenburg'], rank=rank,
                        spend_less=of - rank,
                        percentile=round(1 - rank / of, 4),
                        below_median=r['median'] - r['lunenburg'],
                        in_bottom_quarter=r['lunenburg'] < r['p25']))
    return out


def statewide_categories(db):
    rows = q(db, "SELECT func_cat_code, func_desc, districts, per_pupil_median median, "
                 "lunenburg_per_pupil lunenburg, lunenburg_rank_of_districts rank "
                 "FROM dese_function_statewide WHERE level='category' AND fy=? "
                 "ORDER BY func_cat_code", FIN_FY)
    if not rows:
        fail('the statewide category query matched nothing for FY%d.' % FIN_FY)
    out = []
    for r in rows:
        if r['lunenburg'] is None or not r['rank']:
            continue          # DESE publishes no per-pupil for the out-of-district rows
        m = re.fullmatch(r'(\d+) of (\d+)', r['rank'])
        if not m:
            fail('%s ranks %r, not "<n> of <N>".' % (r['func_cat_code'], r['rank']))
        rank, of = int(m.group(1)), int(m.group(2))
        out.append(dict(code=r['func_cat_code'], desc=r['func_desc'], districts=of,
                        median=r['median'], lunenburg=r['lunenburg'], rank=rank,
                        spend_less=of - rank,
                        share_of_median=round(r['lunenburg'] / r['median'], 4)
                        if r['median'] else None,
                        in_bottom_quarter=rank > of * 0.75))
    if len(out) < 8:
        fail('only %d statewide categories carry a Lunenburg figure; the page prints a '
             'row for each.' % len(out))
    out.sort(key=lambda r: r['share_of_median'] if r['share_of_median'] else 9)
    return out


def categories(db, fte):
    """FY2025, eleven categories, six districts — and the gap against the MEDIAN peer.

    Against the MEDIAN DISTRICT and not against the median of each category, because a
    median of medians does not sum: the eleven per-category medians here differ from the
    peer median total by $206 a pupil. Taking the district whose in-district total is the
    median peer makes the decomposition add up exactly, and that is asserted."""
    rows = q(db, "SELECT func_cat_code code, func_desc desc, lea, district, total, "
                 "per_pupil FROM dese_function_expenditure "
                 "WHERE level='category' AND fy=?", FIN_FY)
    if not rows:
        fail('the FY%d category query matched nothing.' % FIN_FY)
    ind = q(db, "SELECT lea, district, total, per_pupil FROM dese_function_expenditure "
                "WHERE level='rollup' AND func_code='IIII' AND fy=?", FIN_FY)
    if len(ind) < MIN_DISTRICTS:
        fail('only %d in-district rollups in FY%d.' % (len(ind), FIN_FY))

    ind_pp = {r['district']: r['per_pupil'] for r in ind}
    lun_ind = ind_pp[TOWN]
    peers = sorted(((v, k) for k, v in ind_pp.items() if k != TOWN), reverse=True)
    med_value = statistics.median(v for v, _ in peers)
    median_peer = [k for v, k in peers if v == med_value]
    if len(median_peer) != 1:
        fail('the median peer in-district figure %s is not held by exactly one district '
             '(%s). The decomposition below is against that district by name.'
             % (med_value, median_peer))
    median_peer = median_peer[0]

    by_cat = collections.defaultdict(dict)
    desc = {}
    for r in rows:
        by_cat[r['code']][r['district']] = r['per_pupil']
        desc[r['code']] = r['desc']
    out = []
    total_gap = 0.0
    for code, m in by_cat.items():
        if TOWN not in m or median_peer not in m:
            fail('category %s is missing Lunenburg or %s in FY%d.'
                 % (code, median_peer, FIN_FY))
        lun = m[TOWN]
        gap = lun - m[median_peer]
        total_gap += gap
        vals = sorted(m.values(), reverse=True)
        peer_vals = sorted(v for k, v in m.items() if k != TOWN)
        out.append(dict(
            code=code, desc=desc[code], lunenburg=lun,
            median_peer=m[median_peer], gap=gap,
            rank=vals.index(lun) + 1, of=len(vals),
            peer_low=peer_vals[0], peer_high=peer_vals[-1],
            peer_median=statistics.median(peer_vals),
            by_district={k: v for k, v in sorted(m.items())}))
    headline_gap = lun_ind - ind_pp[median_peer]
    if abs(total_gap - headline_gap) > 1.0:
        fail('the eleven category gaps sum to %.0f and the in-district totals differ by '
             '%.0f. The page presents the first as a decomposition of the second.'
             % (total_gap, headline_gap))
    out.sort(key=lambda r: r['gap'])
    cat_median_sum = sum(r['peer_median'] for r in out)
    return out, dict(
        fy=FIN_FY, median_peer=median_peer,
        lunenburg=lun_ind, peer=ind_pp[median_peer], gap=headline_gap,
        fte_in_district=fte[(LEA, FIN_FY)]['In-District FTE Pupils'],
        gap_in_dollars=round(headline_gap
                             * fte[(LEA, FIN_FY)]['In-District FTE Pupils']),
        peer_median_of_categories=round(cat_median_sum),
        why_not_category_medians=round(cat_median_sum - ind_pp[median_peer]),
        by_district={k: v for k, v in sorted(ind_pp.items())})

# WHERE LUNENBURG'S CHILDREN ACTUALLY GO. A destination is not a peer, and the two answer
# different questions -- see destinations() below. The threshold is mechanical because a
# hand-picked destination set is an argument, exactly like the peer set this page already
# registers as a gap.
MIN_DEST_STUDENTS = 5


def destinations(db, lun_per_pupil):
    """The districts Lunenburg's children leave for, and what each of them spends.

    DESTINATIONS ARE NOT PEERS AND THE PAGE KEEPS THEM APART. A peer is a district of a
    similar shape, for asking whether a figure is normal. A destination is where resident
    children were actually educated. They are different sets, they answer different
    questions, and merging them would let a claim about one carry a claim about the other.

    THE SET IS DERIVED, NOT CHOSEN. Every district that enrolled MIN_DEST_STUDENTS or more
    Lunenburg resident children in the latest year DESE publishes, ranked by children.
    That matters: the first draft of this was the five biggest bricks-and-mortar
    destinations, every one of which spends MORE per pupil than Lunenburg -- while the two
    Commonwealth virtual districts, eight Lunenburg children each, spend LESS. A chosen
    set would have made "every destination spends more" true of the set and false of the
    world.

    TWO COLLECTIONS, TWO YEARS, NEVER DIFFERENCED (rule 1). The children are counted in
    DESE's residents-sending and enrollment-receiving files for the enrollment year; the
    spending is DESE's end-of-year finance collection for the finance year. One is a count
    of children and the other is dollars over a pupil count, so nothing here subtracts one
    from the other -- but the two years are stated wherever both appear.

    NO FOUNDATION FIGURE COMES NEAR THIS. A foundation budget per pupil is a Chapter 70
    formula output -- what the state's model says an adequate education costs -- and
    Montachusett's is about five thousand dollars BELOW what it spends. Placing the two in
    one table is the error this section was built to avoid; nothing derived from
    dese_ch70_* is read here at all, and verify_peer_spending.py asserts it.

    THE SHAPE OF EACH DISTRICT IS READ OFF DESE'S OWN NAME FOR IT, not assigned by us, so
    a reader can check it against the same string DESE publishes."""
    years = [r['fy'] for r in q(
        db, 'SELECT DISTINCT fy FROM dese_town_enrollment WHERE town=? ORDER BY fy', TOWN)]
    if not years:
        fail('no town-of-residence enrollment rows for %s. A destination table built from '
             'an empty join looks exactly like a town nobody leaves.' % TOWN)
    enr_fy = years[-1]

    rows = q(db, 'SELECT lea, district, enrollment_reason, students '
                 'FROM dese_town_enrollment WHERE town=? AND fy=?', TOWN, enr_fy)
    if not rows:
        fail('no FY%d enrollment rows for %s.' % (enr_fy, TOWN))
    cum = {r['lea']: r for r in q(
        db, 'SELECT lea, SUM(students) students, COUNT(DISTINCT fy) years '
            'FROM dese_town_enrollment WHERE town=? GROUP BY lea', TOWN)}

    where = collections.defaultdict(lambda: dict(students=0.0, reasons=[], district=None))
    for r in rows:
        if r['students'] is None:
            fail('%s FY%d carries no student count. A blank is not a zero.'
                 % (r['district'], enr_fy))
        w = where[r['lea']]
        w['students'] += r['students']
        w['reasons'].append(r['enrollment_reason'])
        w['district'] = r['district']
    if LEA not in where:
        fail('FY%d has no row for %s\'s own district, so the share who left cannot be '
             'stated against the whole.' % (enr_fy, TOWN))
    stayed = where[LEA]['students']
    away = {k: v for k, v in where.items() if k != LEA}
    left = sum(v['students'] for v in away.values())

    # DESE's all-funds per-pupil total, the SAME measure for every district here. Read out
    # of the typed table rather than the CSV mirror, and every value asserted numeric: a
    # destination whose figure would not parse must fail loudly, not vanish from a table
    # about who spends more.
    spend = {}
    for r in q(db, 'SELECT lea, district, value, reconciles FROM dese_measure '
                   'WHERE fy=? AND "group"=? AND measure=?',
               FIN_FY, 'Expenditures Per Pupil', 'Total Expenditures'):
        if not isinstance(r['value'], (int, float)):
            fail('%s FY%d per-pupil total is %r, which is not a number.'
                 % (r['district'], FIN_FY, r['value']))
        spend[r['lea']] = r
    if LEA not in spend:
        fail('no FY%d per-pupil total for %s in dese_measure.' % (FIN_FY, TOWN))
    # Two DESE collections state Lunenburg's per-pupil total and they must agree, or the
    # destination table and the rest of this page are quoting different dollars.
    if abs(spend[LEA]['value'] - lun_per_pupil) > 1.0:
        fail('RADAR says %s spends %.0f a pupil in FY%d and the finance collection says '
             '%.0f. The destination table is against the second and would be comparing '
             'two measures.' % (TOWN, spend[LEA]['value'], FIN_FY, lun_per_pupil))

    def shape(name):
        """DESE's own name for the district, read for what kind of school it is. A
        vocational, charter or virtual district is funded and shaped differently from a
        K-12 municipal district and its per-pupil figure is not like for like."""
        n = name.lower()
        if 'vocational' in n:
            return 'regional vocational technical'
        if 'virtual' in n:
            return 'Commonwealth virtual'
        if 'charter' in n:
            return 'charter'
        return 'K-12 district'

    out, short = [], []
    for lea, w in sorted(away.items(), key=lambda kv: (-kv[1]['students'], kv[0])):
        if w['students'] < MIN_DEST_STUDENTS:
            short.append(w)
            continue
        s = spend.get(lea)
        if not s:
            fail('%s took %.0f %s children in FY%d and this archive holds no FY%d '
                 'per-pupil figure for it. The set is defined by a threshold, so a '
                 'missing figure is a hole in the claim and not a district to drop -- add '
                 'lea %s to KEEP in scripts/extract_dese_radar.py.'
                 % (w['district'], w['students'], TOWN, enr_fy, FIN_FY, lea))
        gap = s['value'] - lun_per_pupil
        c = cum.get(lea) or dict(students=w['students'], years=1)
        out.append(dict(
            lea=lea, district=w['district'], shape=shape(w['district']),
            students=w['students'],
            share_of_leavers=round(w['students'] / left, 4),
            how=sorted(set(w['reasons'])),
            students_all_years=c['students'], years=c['years'],
            per_pupil=s['value'], reconciles=s['reconciles'],
            gap=gap, gap_pct=round(gap / lun_per_pupil, 6),
            spends_more=gap > 0))
    if not out:
        fail('no destination cleared %d children in FY%d. The join matched nothing and an '
             'empty destination table reads as a town nobody leaves.'
             % (MIN_DEST_STUDENTS, enr_fy))

    more = [r for r in out if r['spends_more']]
    less = [r for r in out if not r['spends_more']]
    if not more:
        fail('not one destination spends more per pupil than %s. The conclusion this '
             'section carries says the opposite and would be false.' % TOWN)
    bricks = [r for r in more if r['shape'] != 'Commonwealth virtual']
    if not bricks:
        fail('every destination spending more is a virtual district; the conclusion names '
             'the ones with buildings and there are none.')
    widest = max(bricks, key=lambda r: r['gap'])
    narrowest = min(bricks, key=lambda r: r['gap'])
    # The nearest LIKE-FOR-LIKE comparison: the largest destination that is an ordinary
    # K-12 municipal district, so a reader is not left with a vocational school as the
    # whole of the finding. Derived from DESE's own name, never named here.
    like = [r for r in out if r['shape'] == 'K-12 district']
    if not like:
        fail('no destination is an ordinary K-12 district, and the section states one as '
             'the like-for-like comparison.')
    like = max(like, key=lambda r: r['students'])

    return dict(
        enr_fy=enr_fy, fin_fy=FIN_FY, first_enr_fy=years[0], enr_years=len(years),
        threshold=MIN_DEST_STUDENTS,
        lunenburg=lun_per_pupil, stayed=stayed, left=left,
        left_share=round(left / (left + stayed), 4),
        rows=out,
        listed=len(out), listed_children=sum(r['students'] for r in out),
        below_threshold=len(short),
        below_threshold_children=sum(v['students'] for v in short),
        more=len(more), less=len(less),
        children_where_more=sum(r['students'] for r in more),
        children_where_less=sum(r['students'] for r in less),
        widest=widest, narrowest=narrowest, like_for_like=like,
        less_rows=less)


def teachers(db, fte):
    """Average salary times teachers per pupil, and it is DESE's own construction.

    The page says so, because presenting a definitional identity as a discovery is exactly
    the error rule 7 is about. What the split is FOR is that it says which half moves."""
    # SCOPED TO THE PEER SET, and the scope is a table rather than a list. `dese_measure`
    # also carries the DESTINATIONS -- the districts Lunenburg's children leave for -- and
    # those have no row in the finance collection, which is what this section joins
    # against. A destination arriving here would fail the join and read as a district with
    # no teachers. Peers and destinations are different sets and this page keeps them so.
    sal = q(db, "SELECT lea, district, measure, value FROM dese_measure WHERE fy=? AND "
                "measure IN ('Average Teacher Salary','Teacher FTE',"
                "'Teachers per 100 FTE students','Paraprofessional FTE') "
                "AND lea IN (SELECT DISTINCT lea FROM dese_function_expenditure)", FIN_FY)
    if not sal:
        fail('the FY%d staffing query matched nothing.' % FIN_FY)
    m = collections.defaultdict(dict)
    for r in sal:
        m[(r['lea'], r['district'])][r['measure']] = r['value']
    spend = {r['district']: r for r in q(
        db, "SELECT district, total, per_pupil FROM dese_function_expenditure "
            "WHERE level='category' AND func_cat_code='TCHR' AND fy=?", FIN_FY)}
    out = []
    for (lea, district), v in sorted(m.items(), key=lambda kv: kv[0][1]):
        s = spend.get(district)
        if not s:
            fail('%s has staffing and no Teachers spending in FY%d — the join did not '
                 'match.' % (district, FIN_FY))
        f = fte.get((lea, FIN_FY))
        if not f:
            fail('%s has staffing and no FTE pupils in FY%d.' % (district, FIN_FY))
        per_fte = s['total'] / v['Teacher FTE']
        ratio = 100 * v['Teacher FTE'] / f['In-District FTE Pupils']
        if abs(ratio - v['Teachers per 100 FTE students']) > 0.05:
            fail('%s: DESE prints %.2f teachers per 100 students; its own teacher FTE '
                 'over its own IN-DISTRICT FTE pupils is %.2f. The page states that '
                 'denominator.' % (district, v['Teachers per 100 FTE students'], ratio))
        out.append(dict(
            district=district, is_lunenburg=lea == LEA,
            teacher_fte=v['Teacher FTE'], para_fte=v['Paraprofessional FTE'],
            per_hundred=v['Teachers per 100 FTE students'],
            average_salary=v['Average Teacher Salary'],
            spend=s['total'], per_pupil=s['per_pupil'],
            spend_per_teacher_fte=round(per_fte),
            salary_share_of_spend_per_fte=round(per_fte / v['Average Teacher Salary'], 4),
            fte_in_district=f['In-District FTE Pupils']))
    worst = max(abs(1 - r['salary_share_of_spend_per_fte']) for r in out)
    if worst > 0.02:
        fail('DESE’s average teacher salary is no longer within 2%% of the Teachers '
             'function’s spending per teacher FTE (worst %.1f%%). The page says the '
             'identity is DESE’s own construction and would be saying something false.'
             % (worst * 100))
    out.sort(key=lambda r: -r['per_pupil'])
    return out, dict(fy=FIN_FY, worst_gap=round(worst, 4))


def demographics(db):
    # The peer set, not every district in dese_measure -- see the note in teachers().
    rows = q(db, "SELECT lea, district, measure, value FROM dese_measure WHERE fy=? AND "
                 "\"group\"='Student Demographics' "
                 "AND lea IN (SELECT DISTINCT lea FROM dese_function_expenditure)", FIN_FY)
    if not rows:
        fail('the FY%d demographics query matched nothing.' % FIN_FY)
    m = collections.defaultdict(dict)
    for r in rows:
        m[(r['lea'], r['district'])][r['measure']] = r['value']
    out = [dict(district=d, is_lunenburg=lea == LEA,
                headcount=v['Student Headcount'],
                low_income=v['Low-Income % Headcount'],
                swd=v['Students with disabilities % Headcount'],
                el=v['English learner % Headcount'])
           for (lea, d), v in sorted(m.items(), key=lambda kv: kv[0][1])]
    if len(out) < MIN_DISTRICTS:
        fail('only %d districts have FY%d demographics.' % (len(out), FIN_FY))
    return out


def mcas(db, first_fy):
    # The peer set, not every district in dese_measure -- see the note in teachers().
    rows = q(db, "SELECT fy, lea, district, measure, value FROM dese_measure "
                 "WHERE \"group\"='MCAS Performance' AND fy >= ? "
                 "AND lea IN (SELECT DISTINCT lea FROM dese_function_expenditure) "
                 "ORDER BY fy", first_fy)
    if not rows:
        fail('the MCAS query matched nothing from FY%d.' % first_fy)
    measures = sorted({r['measure'] for r in rows})
    years = sorted({r['fy'] for r in rows})
    m = collections.defaultdict(dict)
    for r in rows:
        m[(r['fy'], r['lea'], r['district'])][r['measure']] = r['value']
    out = []
    for (fy_, lea, d), v in sorted(m.items()):
        if set(v) != set(measures):
            fail('%s FY%d has %d of %d MCAS measures. The table prints a full row.'
                 % (d, fy_, len(v), len(measures)))
        out.append(dict(fy=fy_, district=d, is_lunenburg=lea == LEA, **{
            k: v[k] for k in measures}))
    return out, dict(measures=measures, years=years,
                     first_fy=years[0], last_fy=years[-1])


def standing(db):
    """The two Chapter 70 measures that point in apparently opposite directions.

    RULE 1 IS THE WHOLE OF THE CARE HERE. `net school spending as a share of required`
    carries a STAGE in its basis column -- budgeted in the recent years, actual in the
    older ones -- and the two are different quantities for the same name. The page splits
    on it and never differences across it."""
    rows = q(db, "SELECT fy, measure, basis, districts, p25, median, p75, lunenburg, "
                 "lunenburg_rank_of_districts rank FROM dese_ch70_statewide "
                 "WHERE measure IN ('net school spending as a share of required',"
                 "'required local contribution as a share of the foundation budget') "
                 "ORDER BY fy, measure")
    if not rows:
        fail('the Chapter 70 standing query matched nothing.')
    stages = collections.Counter()
    series = []
    for r in rows:
        m = re.fullmatch(r'(\d+) of (\d+)', r['rank'] or '')
        if not m:
            fail('FY%d %s ranks %r, not "<n> of <N>".'
                 % (r['fy'], r['measure'], r['rank']))
        stage = None
        if r['basis'] and r['basis'].startswith('stage: '):
            stage = r['basis'][len('stage: '):]
            stages[stage] += 1
        series.append(dict(fy=r['fy'], measure=r['measure'], basis=r['basis'],
                           stage=stage, districts=int(m.group(2)),
                           p25=r['p25'], median=r['median'], p75=r['p75'],
                           lunenburg=r['lunenburg'], rank=int(m.group(1)),
                           above=int(m.group(1)) - 1))
    if len(stages) < 2:
        fail('the net school spending measure no longer carries more than one stage (%s). '
             'The page is built around splitting on it, and rule 1 forbids differencing '
             'across it.' % dict(stages))

    latest = {}
    for s in series:
        if s['fy'] == CH70_FY:
            latest[s['measure']] = s
    if len(latest) != 2:
        fail('FY%d does not carry both standing measures.' % CH70_FY)

    # The peer set on the same two measures, out of the formula table. Split on stage,
    # state row excluded by `level`.
    peer = q(db, "SELECT district, foundation_budget fb, required_local_contribution rlc, "
                 "ch70_aid, required_nss_published rq, net_school_spending nss, "
                 "nss_stage, nss_pct_of_required pct, reconciles "
                 "FROM dese_ch70_formula WHERE fy=? AND level='district' "
                 "AND foundation_budget > 0 ORDER BY district", CH70_FY)
    if len(peer) < MIN_DISTRICTS:
        fail('only %d districts have an FY%d Chapter 70 profile.' % (len(peer), CH70_FY))
    peer_stages = {r['nss_stage'] for r in peer}
    if len(peer_stages) != 1:
        fail('the FY%d peer net school spending figures are at %s. Rule 1: they may not '
             'be compared across stages.' % (CH70_FY, sorted(peer_stages)))
    prows = []
    for r in peer:
        if r['reconciles'] != 'yes':
            fail('%s FY%d: required net school spending does not equal the required local '
                 'contribution plus Chapter 70 aid. The page reads the ratio off it.'
                 % (r['district'], CH70_FY))
        if abs(r['nss'] / r['rq'] - r['pct']) > 0.002:
            fail('%s FY%d: DESE prints %.4f of required and its own dollars give %.4f.'
                 % (r['district'], CH70_FY, r['pct'], r['nss'] / r['rq']))
        prows.append(dict(district=r['district'],
                          is_lunenburg=r['district'].upper().startswith('LUNENBURG'),
                          foundation_budget=r['fb'],
                          required_local_contribution=r['rlc'],
                          rlc_share=round(r['rlc'] / r['fb'], 4),
                          ch70_aid=r['ch70_aid'], required_nss=r['rq'],
                          net_school_spending=r['nss'], stage=r['nss_stage'],
                          pct_of_required=r['pct'],
                          nss_over_foundation=round(r['nss'] / r['fb'], 4)))

    # The town's own target local share, and how far the requirement sits below it. This
    # is what makes the two measures readable together rather than as a contradiction.
    aid = q(db, "SELECT foundation_enrollment, foundation_budget, "
                "required_local_contribution rlc, target_aid_pct, ch70_aid "
                "FROM dese_ch70_aid_factor WHERE fy=? AND lea=? AND level='district'",
            CH70_FY, LEA)
    if len(aid) != 1:
        fail('FY%d has %d Chapter 70 aid rows for Lunenburg; expected one.'
             % (CH70_FY, len(aid)))
    a = aid[0]
    con = q(db, "SELECT town_foundation_budget fb, target_local_contribution tlc, "
                "shortfall, dollar_increment, required_local_contribution rlc "
                "FROM dese_ch70_contribution WHERE fy=? AND municipality=?",
            CH70_FY, TOWN)
    if len(con) != 1:
        fail('FY%d has %d contribution rows for %s; expected one.'
             % (CH70_FY, len(con), TOWN))
    c = con[0]
    target_share = c['tlc'] / c['fb']
    actual_share = c['rlc'] / c['fb']
    district_share = a['rlc'] / a['foundation_budget']
    if abs(target_share - (1 - a['target_aid_pct'] / 100)) > 0.0005:
        fail('the target local share off the contribution sheet is %.4f and 1 minus the '
             'target aid percentage is %.4f. The page prints them as the same thing.'
             % (target_share, 1 - a['target_aid_pct'] / 100))
    if abs(actual_share - district_share) > 0.0005:
        fail('the TOWN’s required share is %.4f and the DISTRICT’s is %.4f. The page uses '
             'the district figures and says the share is the same either way because the '
             'requirement is allocated by foundation budget.'
             % (actual_share, district_share))

    return dict(
        fy=CH70_FY, series=series, stages=dict(stages), peers=prows,
        nss=latest['net school spending as a share of required'],
        rlc=latest['required local contribution as a share of the foundation budget'],
        target=dict(
            target_aid_pct=a['target_aid_pct'],
            target_local_share=round(target_share, 4),
            actual_local_share=round(actual_share, 4),
            points_below_target=round((target_share - actual_share) * 100, 2),
            statewide_target_aid_pct=41.0,
            shortfall=c['shortfall'], dollar_increment=c['dollar_increment'],
            town_foundation_budget=c['fb'], town_rlc=c['rlc'],
            district_foundation_budget=a['foundation_budget'],
            district_rlc=a['rlc'], ch70_aid=a['ch70_aid'],
            foundation_enrollment=a['foundation_enrollment']))


def said_in_meetings():
    out = []
    for spec in QUOTES:
        rel = '%s/%s/%s-%s-%s.txt' % (MINUTES, spec['board'], spec['date'],
                                      spec['kind'], spec['doc'])
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            fail('%s is not here — a quote on this page is attributed to a document that '
                 'is not in the archive' % rel)
        text = re.sub(r'\s+', ' ', open(path, encoding='utf-8', errors='replace').read())
        if re.sub(r'\s+', ' ', spec['quote']) not in text:
            fail('the quote attributed to %s %s is no longer in %s — quote the source, '
                 'never your rendering of it' % (spec['board'], spec['date'], rel))
        kind = 'Minutes' if spec['kind'] == 'minutes' else 'Agenda'
        out.append(dict(
            key=spec['key'], board=spec['board'].replace('-', ' ').title(),
            date=spec['date'], quote=spec['quote'], why=spec['why'], who=spec['who'],
            kind=kind, cite='/docs/' + rel.replace('sources/', ''),
            town='https://www.lunenburgma.gov/AgendaCenter/ViewFile/%s/_%s%s%s-%s'
                 % (kind, spec['date'][5:7], spec['date'][8:10], spec['date'][:4],
                    spec['doc'])))
    return out


def searched():
    """Each term, with its DENOMINATOR. A grep that finds nothing prints nothing, and
    nothing reads as nobody said it."""
    idx = os.path.join(ROOT, 'sources/meetings/index.csv')
    if not os.path.exists(idx):
        fail('sources/meetings/index.csv is not here — a search of nothing is not a search')
    rows = list(csv.DictReader(open(idx, encoding='utf-8')))
    readable = []
    for r in rows:
        stem = os.path.splitext(r['path'])[0] if r['path'].strip() else ''
        txt = os.path.join(ROOT, MINUTES, stem + '.txt') if stem else ''
        if stem and os.path.exists(txt):
            readable.append(txt)
    if not readable:
        fail('no meeting document is readable — refusing to publish a count of what '
             'nobody said')
    bodies = [open(t, encoding='utf-8', errors='replace').read() for t in readable]
    terms = [dict(term=t,
                  documents=sum(1 for b in bodies if re.search(re.escape(t), b, re.I)))
             for t in SEARCHED]
    if not any(t['documents'] for t in terms):
        fail('not one search term matched any document. The archive did not go quiet; '
             'something is wrong with the read.')

    cov = os.path.join(ROOT, 'sources/data/minutes-searchable.csv')
    if not os.path.exists(cov):
        fail('sources/data/minutes-searchable.csv is not here — the searchable share '
             'cannot be typed')
    tally = collections.Counter()
    for r in csv.DictReader(open(cov, encoding='utf-8')):
        for k in ('held', 'searchable', 'unsearchable', 'image_scan'):
            tally[k] += int(r[k] or 0)
    if not tally['searchable'] or tally['held'] != tally['searchable'] + tally['unsearchable']:
        fail('minutes-searchable.csv does not reconcile — refusing to publish a coverage '
             'figure that does not add up')
    return terms, dict(held=tally['held'], searchable=tally['searchable'],
                       unsearchable=tally['unsearchable'],
                       image_scan=tally['image_scan'],
                       searchable_share=round(tally['searchable'] / tally['held'], 4))


def split(gap):
    """A gap row is a question and then a reason ending in the document that closes it."""
    why = gap['why']
    closes = None
    marker = '— closes:'
    if marker in why:
        why, closes = why.split(marker, 1)
        why, closes = why.strip(), closes.strip()
    return dict(side=gap['side'], what=gap['what'], why=why, closes=closes)


def gaps():
    rows = list(csv.DictReader(open(GAPS, encoding='utf-8')))
    if not rows:
        fail('money-gaps.csv is empty.')
    by_what = {r['what']: r for r in rows}
    missing = [w for w in CITES_GAPS if w not in by_what]
    if missing:
        fail('this page cites money_gaps rows that are not in the register: %s\n'
             'Rule 7c: the registry outranks the page.' % missing)
    return [split(by_what[w]) for w in CITES_GAPS]


def build():
    if not os.path.exists(DB):
        fail('%s is not here. Run scripts/build_db.py.' % os.path.relpath(DB, ROOT))
    db = sqlite3.connect('file:%s?mode=ro' % DB, uri=True)
    try:
        assert_levels(db)
        fte = fte_index(db)
        dens = denominators(db, fte)
        districts, regionalisation = district_set(db)
        tot, years = totals(db, fte)
        ranked(tot)
        # The destination set needs Lunenburg's own per-pupil total to measure a gap
        # against, and it must be THE SAME figure the rest of the page prints rather than
        # a second one read out of a second table.
        dest = destinations(
            db, [r for r in tot if r['lea'] == LEA and r['fy'] == FIN_FY][0]['per_pupil'])
        cats, cat_headline = categories(db, fte)
        tch, tch_meta = teachers(db, fte)
        mc, mc_meta = mcas(db, FIN_FY - 2)
        sw = statewide(db)
        swc = statewide_categories(db)
        stand = standing(db)
        demo = demographics(db)
    finally:
        db.close()

    terms, minutes = searched()
    lun_last = [r for r in tot if r['lea'] == LEA and r['fy'] == FIN_FY][0]
    last_year = sorted((r for r in tot if r['fy'] == FIN_FY),
                       key=lambda r: -r['per_pupil'])
    sw_last = sw[-1]
    fund_low = min(r['grant_share'] for r in last_year)
    dec = decomposition(tot)

    # How long Lunenburg has been in the bottom quarter of the state, and how long it has
    # been fifth or sixth of six. Both derived; neither typed.
    bottom_quarter = [s['fy'] for s in sw if s['in_bottom_quarter']]
    lun_ranks = [r for r in tot if r['lea'] == LEA]
    never_above = max(r['rank'] for r in lun_ranks), min(r['rank'] for r in lun_ranks)

    # The ends of each series the conclusions name, derived here rather than picked by
    # hand: the widest and narrowest spending growth across the six, the district whose
    # pupil count fell furthest, Lunenburg's own decomposition row, and the teacher
    # extremes. A conclusion that says "the top of the set" has to be told which district
    # that is by the data.
    # The destination ends, derived rather than picked. The district with the WIDEST gap
    # and the district taking the MOST children are separate questions and the conclusion
    # names each for what it is.
    d_wide = dest['widest']
    d_like = dest['like_for_like']
    d_narrow = dest['narrowest']
    # Ordered by how far above Lunenburg each one is, smallest first, so the detail
    # reads as a RANGE. A reader who meets 43.3% first takes it for typical.
    d_more = sorted((r for r in dest['rows'] if r['spends_more']),
                    key=lambda r: r['gap_pct'])

    dec_lun = next(r for r in dec if r['is_lunenburg'])
    spend_low = min(dec, key=lambda r: r['spend_pct'])
    spend_high = max(dec, key=lambda r: r['spend_pct'])
    pupils_low = min(dec, key=lambda r: r['pupils_pct'])
    at_old_last = max(dec, key=lambda r: r['rank_at_old_enrollment'])
    tch_lun = next(r for r in tch if r['is_lunenburg'])
    pay_order = sorted(tch, key=lambda r: -r['average_salary'])
    ratio_order = sorted(tch, key=lambda r: -r['per_hundred'])
    # Lunenburg's place in each of those two orderings. Both are stated in a conclusion
    # and neither may be typed: the set is six districts and an ordering can change.
    pay_rank = [r['district'] for r in pay_order].index(tch_lun['district']) + 1
    ratio_rank = [r['district'] for r in ratio_order].index(tch_lun['district']) + 1
    pp_top = max(tch, key=lambda r: r['per_pupil'])

    return {
        'about': 'What DESE says Lunenburg spends for each pupil — against the districts '
                 'its own children leave for, against every district in Massachusetts, '
                 'and against five neighbours — with the arithmetic that says how much of '
                 'the difference is money and how much is children.',
        'not_this_page': 'Not the school appropriation, and not what a Lunenburg '
                         'household pays. DESE counts all funds — grants, revolving '
                         'funds, school choice, gifts — and counts town-paid insurance '
                         'and retirement attributed to the schools. The difference '
                         'between this and the town’s budget is two definitions, not '
                         'hidden money.',
        'fin_fy': FIN_FY, 'ch70_fy': CH70_FY,
        'first_fy': years[0], 'last_fy': years[-1], 'years': len(years),
        'first_comparable_fy': FIRST_COMPARABLE_FY,
        'regionalisation': regionalisation,
        'documents': documents(),
        'denominators': dens,
        'districts': districts,
        'headline': dict(
            fy=FIN_FY,
            per_pupil=lun_last['per_pupil'],
            total=lun_last['total'],
            gen_fund=lun_last['gen_fund'],
            grants_revolving=lun_last['grants_revolving'],
            grant_share=lun_last['grant_share'],
            grant_share_is_lowest=lun_last['grant_share'] <= fund_low + 1e-9,
            fte_total=lun_last['fte_total'],
            fte_in_district=lun_last['fte_in_district'],
            rank=lun_last['rank'], of=lun_last['of'],
            statewide_rank=sw_last['rank'], statewide_of=sw_last['districts'],
            statewide_spend_less=sw_last['spend_less'],
            statewide_median=sw_last['median'],
            statewide_below_median=sw_last['below_median'],
            statewide_p25=sw_last['p25'], statewide_p75=sw_last['p75'],
            bottom_quarter_years=len(bottom_quarter),
            bottom_quarter_of=len(sw),
            bottom_quarter_unbroken=len(bottom_quarter) == len(sw),
            best_rank=never_above[1], worst_rank=never_above[0],
        ),
        # WHAT A RESIDENT SHOULD TAKE AWAY, computed here rather than written on the
        # page. The argument in this town is whether the schools are underfunded, and it
        # is conducted with a per-pupil figure whose denominator nobody looks at. These
        # say where Lunenburg actually sits, what moved the ratio, and what the money
        # buys in teachers. Rule 8: what it means, never what anybody got wrong. The
        # denominator labelling and the peer-set criterion are findings about DOCUMENTS
        # and stay in `denominators`, `not_established` and the gaps register.
        'conclusions': emit('what-other-districts-spend', [
            # THE LEAD. A resident three sentences into this page should have met it: what
            # the town spends, against what the schools its own children attend spend.
            #
            # DESTINATIONS ARE NOT PEERS. The rest of this page compares Lunenburg with
            # districts of a similar shape, to ask whether a figure is normal. This one
            # compares it with where resident children were actually educated, which is a
            # different question and is kept a different set.
            #
            # THE PERCENTAGE LEADS AND THE DOLLARS FOLLOW. $7,800 reads as small against a
            # thirty-million-dollar budget until it is said as nearly half again for each
            # child; the dollars are what a household can picture and the percentage is
            # what makes the size of it obvious. Both are printed, neither is typed.
            #
            # THE WIDEST FIGURE CARRIES ITS CAVEAT IN THE SAME SENTENCE, because it will
            # be quoted: the district is named in full and its name says `Regional
            # Vocational Technical`. The nearest like-for-like K-12 comparison is named
            # beside it so a reader does not take the vocational figure as typical.
            conclusion(
                id='the-districts-our-children-leave-for-spend-more',
                # NOT "mostly". The count is known, so it is stated: `mostly` hedged
                # where the data does not need a hedge, and it also hid the thing the
                # hedge was there for. The exception is named in the detail by district.
                # THE CAVEAT RIDES WITH THE METRIC. 43.3% is Montachusett, a regional
                # VOCATIONAL district, and it will be quoted; if it leads, the
                # not-like-for-like has to be in the same breath rather than in a note
                # further down. The count carries the finding, in `so_what`, because
                # `most` hedges where the data does not need a hedge.
                claim='More for each pupil at Monty Tech, a regional vocational school, '
                      'than Lunenburg',
                so_what='%s of the %s children educated outside Lunenburg go to districts '
                        'that spend more for each pupil.'
                        % (C.num(dest['children_where_more']), C.num(dest['left'])),
                lede='%s of the %s Lunenburg children educated outside Lunenburg Public '
                      'Schools go to districts that spend more for each pupil than '
                      'Lunenburg does — %s more at %s, and %s more at %s.'
                      % (C.num(dest['children_where_more']), C.num(dest['left']),
                         C.pct(d_like['gap_pct'] * 100), d_like['district'],
                         C.pct(d_wide['gap_pct'] * 100), d_wide['district']),
                # THE DOLLARS AND THE PERCENTAGE TOGETHER, in that order. A percentage
                # says how big the gap is and a dollar figure says what it is; TJ, reading
                # a draft that carried only the percentage: it "should contain the dollar
                # amount paid too."
                detail='In %s the widest is %s a pupil against Lunenburg’s %s — %s more, '
                       'which is %s — and %s of the leavers go there. The size of it '
                       'depends enormously on which district: %s more at %s, %s at %s, %s '
                       'at %s, %s at %s, %s at %s. %s is the nearest like-for-like '
                       'comparison, an ordinary K-12 municipal district, at %s a pupil, '
                       '%s more. The exception is the two Commonwealth virtual districts, '
                       '%s children between them, which spend less. The children are '
                       'counted in %s and the spending measured in %s: two collections, '
                       'and nothing here is differenced across them.'
                       % (C.fy(dest['fin_fy']),
                          C.usd(d_wide['per_pupil']), C.usd(dest['lunenburg']),
                          C.usd(d_wide['gap']), C.pct(d_wide['gap_pct'] * 100),
                          C.pct(d_wide['share_of_leavers'] * 100),
                          C.usd(d_more[0]['gap']), d_more[0]['district'],
                          C.usd(d_more[1]['gap']), d_more[1]['district'],
                          C.usd(d_more[2]['gap']), d_more[2]['district'],
                          C.usd(d_more[3]['gap']), d_more[3]['district'],
                          C.usd(d_more[4]['gap']), d_more[4]['district'],
                          d_like['district'], C.usd(d_like['per_pupil']),
                          C.usd(d_like['gap']),
                          C.num(dest['children_where_less']),
                          C.fy(dest['enr_fy']), C.fy(dest['fin_fy'])),
                figures={
                    'like_pct': figure(d_like['gap_pct'] * 100,
                                       C.pct(d_like['gap_pct'] * 100)),
                    'widest_pct': figure(d_wide['gap_pct'] * 100,
                                         C.pct(d_wide['gap_pct'] * 100)),
                    'widest_share': figure(d_wide['share_of_leavers'] * 100,
                                           C.pct(d_wide['share_of_leavers'] * 100)),
                    'children_where_more': figure(dest['children_where_more'],
                                                  C.num(dest['children_where_more'])),
                    'children_left': figure(dest['left'], C.num(dest['left'])),
                    'children_where_less': figure(dest['children_where_less'],
                                                  C.num(dest['children_where_less'])),
                    'enr_fy': figure(dest['enr_fy'], C.fy(dest['enr_fy'])),
                    'fin_fy': figure(dest['fin_fy'], C.fy(dest['fin_fy'])),
                    'widest_per_pupil': figure(d_wide['per_pupil'],
                                               C.usd(d_wide['per_pupil'])),
                    'widest_gap': figure(d_wide['gap'], C.usd(d_wide['gap'])),
                    'lunenburg': figure(dest['lunenburg'], C.usd(dest['lunenburg'])),
                    'like_per_pupil': figure(d_like['per_pupil'],
                                             C.usd(d_like['per_pupil'])),
                    'gap_1': figure(d_more[0]['gap'], C.usd(d_more[0]['gap'])),
                    'gap_2': figure(d_more[1]['gap'], C.usd(d_more[1]['gap'])),
                    'gap_3': figure(d_more[2]['gap'], C.usd(d_more[2]['gap'])),
                    'gap_4': figure(d_more[3]['gap'], C.usd(d_more[3]['gap'])),
                    'gap_5': figure(d_more[4]['gap'], C.usd(d_more[4]['gap'])),
                    'like_gap': figure(d_like['gap'], C.usd(d_like['gap'])),
                },
                figure='widest_pct',
                kind='measured',
                basis='DESE’s end-of-year finance collection for the finance year, all '
                      'funds, the district per-pupil total — the same measure for every '
                      'district on this page — against DESE’s residents-sending and '
                      'enrollment-receiving files for the enrollment year, which count '
                      'Lunenburg resident children by the district that educated them. '
                      'The destination set is every district that took five or more of '
                      'them, derived on every run rather than chosen, and the generator '
                      'refuses to write if one of them has no spending figure.',
                not_shown='What the difference buys, or that any family chose on '
                          'spending. A per-pupil figure is a ratio and a district with '
                          'fewer pupils reads higher with nothing bought — the same '
                          'arithmetic this page applies to the peer set. A regional '
                          'vocational, charter or Commonwealth virtual district is funded '
                          'and shaped differently from a K-12 municipal school and its '
                          'figure is not like for like, which is why the two virtual '
                          'districts sit below Lunenburg at %s and %s a pupil. Nothing '
                          'here is a foundation budget: that is a Chapter 70 formula '
                          'output, a different measure, and it is not on this page.'
                          % (C.usd(min(r['per_pupil'] for r in dest['less_rows'])),
                             C.usd(max(r['per_pupil'] for r in dest['less_rows']))),
                see=[('/monty-tech', 'the district that takes most of them, and how the '
                                     'town is billed for it'),
                     ('/where-students-go-instead', 'where students go, year by year')],
                # `K-12` is a grade range, not a derived figure. Declared rather than
                # left invisible, which is what allow=() is for.
                allow=('K-12',),
            ),
            conclusion(
                id='the-bottom-quarter-is-the-durable-fact',
                claim='Spent for each pupil, counting every fund — below the state median',
                so_what='Lunenburg has been in the bottom quarter of Massachusetts districts in every published year.',
                lede='Lunenburg spends %s a pupil, %s below the statewide median, and it '
                      'has been in the bottom quarter of Massachusetts districts in %s of '
                      'the %s years the state publishes here.'
                      % (C.usd(lun_last['per_pupil']),
                         C.usd(sw_last['below_median']),
                         C.num(len(bottom_quarter)), C.num(len(sw))),
                detail='In %s it ranks %s of %s districts, with %s spending less, against '
                       'a median of %s and a middle half running %s to %s. This is not '
                       'the school budget and not what a household pays: DESE counts '
                       'every fund \u2014 grants, revolving funds, school choice, gifts '
                       '\u2014 and counts town-paid insurance and retirement attributed '
                       'to the schools, so it is a larger figure than the appropriation '
                       'Town Meeting votes. The distance between the two is two '
                       'definitions, not hidden money.'
                       % (C.fy(FIN_FY), C.num(sw_last['rank']),
                          C.num(sw_last['districts']), C.num(sw_last['spend_less']),
                          C.usd(sw_last['median']), C.usd(sw_last['p25']),
                          C.usd(sw_last['p75'])),
                figures={
                    'per_pupil': figure(lun_last['per_pupil'],
                                        C.usd(lun_last['per_pupil'])),
                    'below_median': figure(sw_last['below_median'],
                                           C.usd(sw_last['below_median'])),
                    'bottom_quarter_years': figure(len(bottom_quarter),
                                                   C.num(len(bottom_quarter))),
                    'years': figure(len(sw), C.num(len(sw))),
                    'fy': figure(FIN_FY, C.fy(FIN_FY)),
                    'rank': figure(sw_last['rank'], C.num(sw_last['rank'])),
                    'districts': figure(sw_last['districts'],
                                        C.num(sw_last['districts'])),
                    'spend_less': figure(sw_last['spend_less'],
                                         C.num(sw_last['spend_less'])),
                    'median': figure(sw_last['median'], C.usd(sw_last['median'])),
                    'p25': figure(sw_last['p25'], C.usd(sw_last['p25'])),
                    'p75': figure(sw_last['p75'], C.usd(sw_last['p75'])),
                },
                figure='per_pupil',
                kind='measured',
                basis='DESE\u2019s end-of-year finance collection, all funds, the '
                      'district total level only, with DESE\u2019s own statewide '
                      'distribution and its own published rank for Lunenburg. One stage '
                      'throughout: what districts reported after the year closed, never '
                      'differenced against a budget.',
                not_shown='Whether that is a choice or a constraint, and what the '
                          'difference buys. The town has a levy limit and two failed '
                          'overrides and Town Meeting votes the appropriation, so this '
                          'measure is the outcome of all of it at once and cannot be '
                          'attributed to any part of it. Nothing here relates spending to '
                          'results, and a function line is not a service.',
                see=[('/what-the-state-requires-us-to-spend',
                      'what the state requires the town to spend'),
                     ('/health-insurance',
                      'the insurance DESE counts here and the school budget does not')],
            ),
            conclusion(
                id='most-of-the-gap-is-the-denominator',
                claim='What Lunenburg would spend for each pupil at its own enrollment of thirteen years ago',
                so_what='Most of the gap with its neighbours is fewer children, not less money.',
                lede='Most of the per-pupil gap between Lunenburg and its neighbours is '
                      'the denominator. Spending grew within a narrow band across all six '
                      'districts; enrollment did not.',
                detail='From %s to %s every one of the six raised spending by between %s '
                       'and %s, and Lunenburg\u2019s %s sits inside that band. Pupil '
                       'counts are what separate them: %s here against %s at %s. Give '
                       '%s\u2019s money to each district\u2019s %s pupil count and '
                       'Lunenburg is %s a pupil, %s of %s rather than last, and %s is '
                       'last. A neighbour\u2019s higher per-pupil figure is in large part '
                       'fewer children rather than more money.'
                       % (C.fy(FIRST_COMPARABLE_FY), C.fy(FIN_FY),
                          C.pct(spend_low['spend_pct'] * 100),
                          C.pct(spend_high['spend_pct'] * 100),
                          C.pct(dec_lun['spend_pct'] * 100),
                          C.pct(dec_lun['pupils_pct'] * 100),
                          C.pct(pupils_low['pupils_pct'] * 100),
                          pupils_low['district'], C.fy(FIN_FY),
                          C.fy(FIRST_COMPARABLE_FY),
                          C.usd(dec_lun['at_old_enrollment']),
                          C.num(dec_lun['rank_at_old_enrollment']), C.num(len(dec)),
                          at_old_last['district']),
                figures={
                    'from_fy': figure(FIRST_COMPARABLE_FY, C.fy(FIRST_COMPARABLE_FY)),
                    'to_fy': figure(FIN_FY, C.fy(FIN_FY)),
                    'spend_low': figure(spend_low['spend_pct'] * 100,
                                        C.pct(spend_low['spend_pct'] * 100)),
                    'spend_high': figure(spend_high['spend_pct'] * 100,
                                         C.pct(spend_high['spend_pct'] * 100)),
                    'spend_lunenburg': figure(dec_lun['spend_pct'] * 100,
                                              C.pct(dec_lun['spend_pct'] * 100)),
                    'pupils_lunenburg': figure(dec_lun['pupils_pct'] * 100,
                                               C.pct(dec_lun['pupils_pct'] * 100)),
                    'pupils_low': figure(pupils_low['pupils_pct'] * 100,
                                         C.pct(pupils_low['pupils_pct'] * 100)),
                    'at_old_enrollment': figure(dec_lun['at_old_enrollment'],
                                                C.usd(dec_lun['at_old_enrollment'])),
                    'rank_at_old': figure(dec_lun['rank_at_old_enrollment'],
                                          C.num(dec_lun['rank_at_old_enrollment'])),
                    'districts': figure(len(dec), C.num(len(dec))),
                },
                figure='at_old_enrollment',
                kind='measured',
                basis='DESE\u2019s end-of-year finance collection against DESE\u2019s '
                      'own total FTE pupil counts, for the six districts this archive '
                      'extracts. The identity (1 + spending growth) / (1 + pupil growth) '
                      '= (1 + per-pupil growth) is checked to four decimal places on '
                      'every district before anything is written. The span starts where '
                      'it does because that is the first year all six exist in their '
                      'current form \u2014 Ayer and Shirley regionalised for it.',
                not_shown='That per-pupil spending is therefore the wrong measure, or '
                          'that a district with falling enrollment could have spent less. '
                          'Costs do not fall in step with a class, so a smaller system '
                          'genuinely does spend more for each child; this arithmetic says '
                          'where the change in the ratio came from and not whether any of '
                          'it was avoidable. The six districts are also this '
                          'project\u2019s own set and no document records the criterion, '
                          'which is why the standing claim above is against the whole '
                          'state instead.',
                see=[('/if-students-leave', 'what happens when students leave')],
            ),
            conclusion(
                id='near-the-top-on-pay-fewest-teachers',
                claim='Average teacher salary, near the top of the neighbouring districts',
                so_what='And Lunenburg employs the fewest teachers for each pupil of the group — the same money, spread wider.',
                lede='Lunenburg pays near the top of this group for a teacher and '
                      'employs the fewest of them for each pupil: %s on average, and %s '
                      'teachers for every hundred in-district pupils.'
                      % (C.usd(tch_lun['average_salary']),
                         '%.1f' % tch_lun['per_hundred']),
                detail='%s\u2019s average is the highest at %s and %s\u2019s the lowest '
                       'at %s; Lunenburg ranks %s of %s on pay and %s of %s on teachers '
                       'for each pupil, where the next lowest is %s and the highest is '
                       '%s. Teaching salaries reach %s a pupil here against %s at %s \u2014 '
                       'close to the same money for each teacher, spread across more '
                       'children.'
                       % (pay_order[0]['district'],
                          C.usd(pay_order[0]['average_salary']),
                          pay_order[-1]['district'],
                          C.usd(pay_order[-1]['average_salary']),
                          C.num(pay_rank), C.num(len(tch)),
                          C.num(ratio_rank), C.num(len(tch)),
                          '%.1f' % ratio_order[-2]['per_hundred'],
                          '%.1f' % ratio_order[0]['per_hundred'],
                          C.usd(tch_lun['per_pupil']), C.usd(pp_top['per_pupil']),
                          pp_top['district']),
                figures={
                    'salary': figure(tch_lun['average_salary'],
                                     C.usd(tch_lun['average_salary'])),
                    'per_hundred': figure(tch_lun['per_hundred'],
                                          '%.1f' % tch_lun['per_hundred']),
                    'salary_high': figure(pay_order[0]['average_salary'],
                                          C.usd(pay_order[0]['average_salary'])),
                    'salary_low': figure(pay_order[-1]['average_salary'],
                                         C.usd(pay_order[-1]['average_salary'])),
                    'pay_rank': figure(pay_rank, C.num(pay_rank)),
                    'ratio_rank': figure(ratio_rank, C.num(ratio_rank)),
                    'districts': figure(len(tch), C.num(len(tch))),
                    'per_hundred_next': figure(ratio_order[-2]['per_hundred'],
                                               '%.1f' % ratio_order[-2]['per_hundred']),
                    'per_hundred_high': figure(ratio_order[0]['per_hundred'],
                                               '%.1f' % ratio_order[0]['per_hundred']),
                    'teaching_per_pupil': figure(tch_lun['per_pupil'],
                                                 C.usd(tch_lun['per_pupil'])),
                    'teaching_per_pupil_high': figure(pp_top['per_pupil'],
                                                      C.usd(pp_top['per_pupil'])),
                },
                figure='salary',
                kind='measured',
                basis='DESE\u2019s RADAR district comparison for the finance year \u2014 '
                      'teacher FTE and average teacher salary \u2014 against DESE\u2019s '
                      'own in-district FTE pupil counts and the teaching-salary category '
                      'of its end-of-year finance collection. The salary implied by the '
                      'finance figures and RADAR\u2019s published average agree to within '
                      'a percent on every district, which is checked before anything is '
                      'written.',
                not_shown='What that means in a classroom. A teacher FTE is not a class '
                          'size and not a person, DESE does not say which fund pays for '
                          'any of them, and an average salary is an average over a '
                          'distribution this archive does not hold. Nothing here '
                          'establishes that the difference is a choice, or that either '
                          'arrangement produces different results.',
                see=[('/school-staffing', 'the people the budget buys')],
            ),
        ]),
        'destinations': dest,
        'totals': tot,
        'last_year': last_year,
        'statewide': sw,
        'statewide_categories': swc,
        'decomposition': dec,
        'lunenburg_denominator': lunenburg_denominator(tot),
        'categories': cats,
        'category_headline': cat_headline,
        'teachers': tch, 'teachers_meta': tch_meta,
        'demographics': demo,
        'mcas': mc, 'mcas_meta': mc_meta,
        'standing': stand,
        'said': said_in_meetings(),
        'searched': terms,
        'minutes': minutes,
        'gaps': gaps(),
        'not_established': [
            'That spending more would change results, or that spending less has changed '
            'them. Nothing on this page tests it, and nothing in this archive could: the '
            'six districts differ in low-income share from %.1f%% to %.1f%% of their '
            'students, and a six-district cross-section cannot separate that from '
            'anything else.'
            % (100 * min(x['low_income'] for x in demo),
               100 * max(x['low_income'] for x in demo)),
            'What DESE’s per-pupil figure buys. It is dollars over a pupil count. A '
            'function line is not a service, a paraprofessional FTE is not a person, and '
            'neither is a class size.',
            'Whether Lunenburg’s figure is a choice or a constraint. The town has a levy '
            'limit and two failed overrides; the district has a budget it proposes and a '
            'Town Meeting that votes it. This measure is the outcome of all of that at '
            'once and cannot be attributed to any part of it.',
            'That the six districts here are the right six. The set is ours — DESE’s own '
            'workbook covers all 421 districts and this archive extracts six for size — '
            'and no document records the criterion. That is why every headline on this '
            'page is against the statewide distribution rather than against the six.',
            'How much of a destination district’s higher per-pupil figure is programme '
            'and how much is a smaller denominator. This page decomposes the ratio into '
            'spending and pupils for the six comparison districts and does not do it for '
            'the destinations; a district with fewer pupils reads higher with nothing '
            'bought, and that applies to a receiving district exactly as it applies here.',
            'What Lunenburg pays towards any destination district’s spending. A receiving '
            'district’s per-pupil figure is its whole spending over its whole pupil count '
            'across every fund; Lunenburg’s side is a member-town assessment, a school '
            'choice tuition or a charter tuition, and none of the three equals it. '
            'Registered in the gaps below.',
            'That the FY%d Chapter 70 figures and the FY%d spending figures describe the '
            'same year. They do not, and they are never differenced: one is a budgeted '
            'formula calculation and the other is what districts reported after the year '
            'closed.' % (CH70_FY, FIN_FY),
        ],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    data = build()

    if args.check:
        if not os.path.exists(OUT):
            print('MISSING %s' % os.path.relpath(OUT, ROOT))
            return 1
        with open(OUT, encoding='utf-8') as fh:
            have = json.load(fh)
        if have != data:
            print('STALE %s — run: python3 scripts/build_peer_spending.py'
                  % os.path.relpath(OUT, ROOT))
            return 1
        print('ok — %s reproduces from the database' % os.path.relpath(OUT, ROOT))
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write('\n')
    h = data['headline']
    print('%s: FY%d–FY%d, %d districts'
          % (os.path.relpath(OUT, ROOT), data['first_fy'], data['last_fy'],
             len(data['districts'])))
    print('  FY%d Lunenburg $%s a pupil — %d of %d here, %d of %d statewide '
          '(%d districts spend less)'
          % (h['fy'], format(round(h['per_pupil']), ','), h['rank'], h['of'],
             h['statewide_rank'], h['statewide_of'], h['statewide_spend_less']))
    print('  statewide median $%s; below it by $%s'
          % (format(round(h['statewide_median']), ','),
             format(round(h['statewide_below_median']), ',')))
    L = data['lunenburg_denominator']
    print('  FY%d–FY%d: spending %+.1f%%, pupils %+.1f%%, per pupil %+.1f%%'
          % (L['from_fy'], L['to_fy'], L['spend_pct'] * 100, L['pupils_pct'] * 100,
             (L['per_pupil_to'] / L['per_pupil_from'] - 1) * 100))
    C = data['category_headline']
    print('  in-district gap to %s: $%s a pupil, decomposed over %d categories exactly'
          % (C['median_peer'], format(round(C['gap']), ','), len(data['categories'])))
    S = data['standing']
    print('  FY%d: required contribution %.1f%% of foundation (target %.1f%%), '
          'net school spending %.4f of required (stage: %s)'
          % (S['fy'], S['target']['actual_local_share'] * 100,
             S['target']['target_local_share'] * 100, S['nss']['lunenburg'],
             S['nss']['stage']))
    print('  denominators verified on %d rows: %d over total FTE, %d over in-district FTE'
          % (data['denominators']['rows_tested'], data['denominators']['total_fte'],
             data['denominators']['in_district_fte']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
