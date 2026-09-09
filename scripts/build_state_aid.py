#!/usr/bin/env python3
"""The state-aid drill-in page's series, pre-rendered from the archive.

    python3 scripts/build_state_aid.py            # write it
    python3 scripts/build_state_aid.py --check    # fail if it is stale

WHY A FILE AND NOT A QUERY. Same as every other drill-in here: the answer is identical
for every reader until the database is rebuilt, and D1's free tier stops at 5 million
rows read a day. The page fetches one static JSON and never touches /api/query.

WHAT THIS PAGE IS. Rule 11's last paragraph, measured. An appropriation is not the
town's bill: the bill is what is left after state aid, and state aid is set in the
Governor's budget and the Legislature's, not in Lunenburg. A year where aid rises and
the appropriation rises with it is not the same year as one where aid is flat and the
town covers the difference -- and the expense side of the budget cannot tell them apart.

FIVE QUANTITIES, NEVER ADDED, AND NEVER DIFFERENCED ACROSS EACH OTHER (rules 1 and 13):

  1. CHAPTER 70 RECEIVED -- what the town actually banked, from the Receipts page of an
     annual town report. An ACTUAL.
  2. CHAPTER 70 BUDGETED -- the estimate the FY2026 appropriation was built on, from the
     town's own MUNIS revenue ledger. A BUDGET. Never joined to (1) to make a rate.
  3. THE CHERRY SHEET ESTIMATE ERROR -- the Division of Local Services' own
     `Excess/Shortfall Cherry Sheet Receipts (CL#8)` line on the free cash proof. This is
     (1) minus (2) as the STATE computes it, for all cherry sheet receipts together, and
     it is the only place in this archive where the two stages are subtracted by somebody
     entitled to subtract them.
  4. THE FORMULA -- DESE's FY27 Chapter 70 district summary. Not money received; the
     calculation that decides how much will be.
  5. THE MODEL'S ASSUMPTION -- `model/finance.py` grows total state aid at the rate this
     script READS from DEFAULT_ASSUMPTIONS rather than typing. It was 2.0% with nothing
     behind it; since 7 September 2026 it is derived -- see notes/findings/STATE-AID-RATE.md.

RULE 1 IS THE WHOLE DIFFICULTY. It would be easy and wrong to run a growth rate from the
FY2022 receipt to the FY2026 budget: that is partly growth and partly the step between an
actual and an estimate. Every rate here is computed inside one stage, the stage is named
on the chart, and `assert_one_stage()` refuses to write if a rate is ever asked for
across two.

RULE 13. The DESE workbook is quoted by cell, its column headings are asserted before a
figure is read out of them, and its Lunenburg row is checked against `model/taxbase.CH70`
-- two independent routes to the same eight numbers. Every minutes quote on the page is
asserted to appear, verbatim after whitespace normalisation, in the minutes file it is
attributed to; a quote that has drifted stops the build rather than shipping.

RULE 15a. The five quotes are what the town actually SAID about state aid in the years
these figures cover, found with scripts/search_minutes.py. One of them states a figure --
"35% of the entire school budget in Lunenburg is covered by chapter 70 funds" -- which is
recomputed here from the ledger rather than repeated.

WHAT IT REFUSES TO WRITE ON. Nine joins that could silently match nothing:
  1. a 45xx revenue object appearing that this project has not classified;
  2. no Chapter 70 row in the FY2026 ledger;
  3. either school appropriation department missing;
  4. fewer than three CHECKED Chapter 70 receipt years;
  5. the free cash proof yielding no Lunenburg CL#8 series, or no peers;
  6. the DESE workbook's headings or Lunenburg row disagreeing with `model/taxbase`;
  7. a minutes quote no longer present in its own document;
  8. no `money_gaps` row about state aid -- rule 7c says a limit this page hits is
     registered there, and a page that renders an empty gap box has lost its register;
  9. `reports.json` no longer carrying an analysis this page is built from.
"""
import argparse
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'model'))

DB = os.path.join(ROOT, 'sources/data/lunenburg.db')
OUT = os.path.join(ROOT, 'fy28/public/data/state-aid.json')
REPORTS = os.path.join(ROOT, 'fy28/public/data/reports.json')
CH70_XLSX = 'sources/budget-workbooks/ch70-fy27-summary.xlsx'
MINUTES = 'sources/meetings/text'

TOWN = 'Lunenburg'
LEDGER_FY = 2026
CL8 = 'Excess/Shortfall Cherry Sheet Receipts (CL#8)'

# THE SCHOOL APPROPRIATION, as the town's own ledger departments. The same two the
# health-insurance generator uses; naming them in one place each is deliberate, because
# the alternative is a page quietly measuring a different denominator.
SCHOOL_DEPTS = ('300', '301')

# EVERY 45xx REVENUE OBJECT IN THE GENERAL FUND, and what kind of money it is.
#
# `object LIKE '45%'` is what `v_state_aid` selects, and it is NOT all state aid and not
# only state aid. Two of these are LOCAL OPTION TAXES: the town votes them, the state
# collects them and remits them, and they are not on the Cherry Sheet at all. Calling
# them aid would inflate every total on this page, so they are classified out and their
# amount is stated rather than hidden.
#
# The split between `school` and `general` is made ON THE PRINTED NAME ONLY. It says
# which receipts NAME the schools, not which ones end up paying for them -- and rule 11
# means those are different questions. `connecting-the-budget.md` establishes that the
# state aid accounts share no organisation code with any expense account, 0 of 222, so
# what any of this actually paid for is not knowable from the ledger.
#
# An object code appearing here that is not in this map STOPS THE BUILD. An unclassified
# account would otherwise be drawn as a bar with no meaning on it.
OBJECT_CLASS = {
    '450000': ('general', 'STATE REVENUE — a header account, zero in every column'),
    '450100': ('general', 'State-owned land — payment in lieu of taxes on state property'),
    '450200': ('general', 'Veterans’ abatement reimbursement'),
    '450300': ('general', 'Abatement reimbursement — surviving spouses'),
    '450400': ('general', 'Abatement reimbursement — the blind'),
    '450500': ('general', 'Abatement reimbursement — the elderly'),
    '450600': ('school', 'Chapter 70 school aid'),
    '450700': ('school', 'School building assistance reimbursement'),
    '450800': ('general', 'Additional aid — local aid'),
    '450900': ('school', 'School transportation reimbursement'),
    '451000': ('general', 'Municipal stabilisation'),
    '451100': ('school', 'Charter school reimbursement'),
    '451200': ('general', 'Professional development'),
    '451300': ('school', 'Minimum teacher salary'),
    '451400': ('general', 'Unrestricted General Government Aid'),
    '451500': ('general', 'Chapter 81 highway aid'),
    '451700': ('general', 'Local aid adjustment'),
    '451800': ('local_option', 'Room occupancy excise — a local tax the state collects'),
    '451900': ('general', 'Additional assistance'),
    '452000': ('general', 'Veterans’ benefits — Chapter 115 §6 reimbursement'),
    '452100': ('general', 'Highway reconstruction'),
    '452200': ('general', 'Quinn Bill police education reimbursement'),
    '452300': ('general', 'Municipal relief'),
    '452400': ('general', 'Forest cutting'),
    '452500': ('general', 'Zoning incentive'),
    '452600': ('local_option', 'Meals tax — a local tax the state collects'),
    '452700': ('general', 'Additional aid — estimated'),
    '452800': ('general', 'Additional aid — appropriated'),
    '452900': ('school', 'School cost reimbursement'),
}

# THE CHAPTER 70 RECEIPT SERIES, and the one column of it we may publish.
#
# `annual_report_receipts` splits into three by `status`, and nothing may be aggregated
# without splitting on it. Only `checked` rows carry a figure onto the chart. The rest are
# drawn as GAPS, with the reason -- because a bar chart that omits a year reads as a
# continuous series, and two of the unchecked years hold figures like 7.53 and 7.77 where
# the extractor lost the thousands separators. A year whose figure is visibly not dollars
# is exactly the year that must not be plotted, and exactly the year a reader deserves to
# be told about.
CH70_NAMES = ('CH 70 SCHOOL AID', 'ICH 70 SCHOOL AID')

STATUS_REASON = {
    'no check': 'the receipts page states no total this extract can be reconciled to',
    'check failed': 'the extract does not reconcile to the totals that page prints',
}

# WHAT THE TOWN SAID. Rule 15a: every one of these was found by running
# scripts/search_minutes.py over the meeting archive, and every one is asserted below to
# still be in the file it is attributed to.
QUOTES = [
    dict(key='estimate',
         board='school-committee', date='2025-10-01', doc='7432', kind='minutes',
         quote='the school budget is based on an estimate of chapter 70 number, this '
               'year there is an additional $202,185, in order for the school to get '
               'this money it needs to be on the warrant for the Town meeting in '
               'November',
         why='The town budgets against an ESTIMATE of Chapter 70, and when the real '
             'number comes in higher the difference does not simply become school '
             'spending. It takes a warrant article at Town Meeting.'),
    dict(key='share',
         board='school-committee', date='2026-06-24', doc='7869', kind='minutes',
         quote='35% of the entire school budget in Luneburg is covered by chapter 70 '
               'funds',
         why='A figure stated at a public meeting. It is recomputed from the town’s own '
             'revenue and expense ledgers below rather than repeated.'),
    dict(key='formula',
         board='school-committee', date='2026-04-01', doc='7748', kind='minutes',
         quote='I am hoping we will get the override and limp through a few years and '
               'that the Chapter 70 formula changes',
         why='The formula is the thing the town is waiting on, and it is decided at the '
             'State House.'),
    dict(key='schoolchoice',
         board='finance-committee', date='2026-01-27', doc='7619', kind='minutes',
         quote='school choice enrollment revenue, which has declined from approximately '
               '$500,000 to $112,000 on the cherry sheet',
         why='School choice tuition is a cherry sheet line, and a Finance Committee '
             'member named its decline as one of two things the boards must address '
             'before asking voters for an override. This archive holds no Cherry Sheet, '
             'so it can report that this was SAID and cannot check the figure — which is '
             'the gap registered below, stated by somebody in the room before we found '
             'it.'),
    dict(key='assessments',
         board='finance-committee', date='2026-02-19', doc='7657', kind='minutes',
         quote='Cherry Sheet Assessments: $1,069,349',
         why='The Cherry Sheet has a charges side as well as a receipts side. The town’s '
             'FY27 revenue plan subtracts this before anything is available to '
             'appropriate.'),
]

# The analyses this page rests on, quoted so a reader can go and read them.
RELATED = [
    ('fy27-and-the-override',
     'Where the FY27 state aid figures come from — the Town Manager’s own revenue '
     'arithmetic, including the enacted budget landing above the Governor’s proposal'),
    ('connecting-the-budget',
     'Why state aid cannot be traced to anything it paid for: the aid accounts share no '
     'organisation code with any expense account'),
    ('show-your-work',
     'Every rate the projection uses and what each one rests on — including the state '
     'aid growth rate, which is recorded there as having no stated source'),
    ('free-cash',
     'The free cash proof these cherry sheet variances are one line of'),
]

CENT = 0.005


def fail(msg):
    sys.exit(f'build_state_aid: {msg}')


def q(c, sql, *a):
    return [dict(r) for r in c.execute(sql, a)]


def one(c, sql, args, what):
    rows = q(c, sql, *args)
    if len(rows) != 1:
        fail(f'{len(rows)} rows for {what} — expected exactly one, so the join that '
             'reads it either matched nothing or matched too much')
    return rows[0]


def cagr(first, last, years):
    if not first or not last or years <= 0 or first <= 0 or last <= 0:
        return None
    return round((last / first) ** (1.0 / years) - 1.0, 6)


def assert_one_stage(rows, stage, what):
    """A rate may only be computed inside one stage (rule 1)."""
    bad = sorted({r['stage'] for r in rows if r['stage'] != stage})
    if bad:
        fail(f'{what}: a rate was asked for across stages {[stage] + bad} — a growth rate '
             'measured from an actual to a budget is partly growth and partly the step '
             'between the two')


# --------------------------------------------------------------------------- the ledger

def ledger(c):
    rows = q(c, """SELECT object, name, budgeted, revised, received, still_to_come,
                          pct_received, doc_id, period
                   FROM   v_revenue
                   WHERE  object LIKE '45%' AND fy = ?
                   ORDER  BY object""", LEDGER_FY)
    if not rows:
        fail(f'no 45xx revenue rows for FY{LEDGER_FY} — the state aid join matched nothing')

    unknown = sorted({r['object'] for r in rows if r['object'] not in OBJECT_CLASS})
    if unknown:
        fail(f'FY{LEDGER_FY} revenue objects this project has not classified: '
             f'{", ".join(unknown)} — an unclassified account would be drawn as a bar '
             'with no meaning on it. Add it to OBJECT_CLASS.')

    accounts = []
    for r in rows:
        kind, meaning = OBJECT_CLASS[r['object']]
        accounts.append(dict(
            object=r['object'], printed=r['name'].strip(), meaning=meaning, kind=kind,
            budgeted=round(r['budgeted'] or 0.0, 2),
            received=round(r['received'] or 0.0, 2),
            still_to_come=round(r['still_to_come'] or 0.0, 2),
            pct_received=r['pct_received']))

    ch70 = next((a for a in accounts if a['object'] == '450600'), None)
    if ch70 is None or ch70['budgeted'] <= 0:
        fail(f'no Chapter 70 row with a figure in the FY{LEDGER_FY} ledger — object '
             '450600 is the account this whole page is about')

    def tot(kinds, field):
        return round(sum(a[field] for a in accounts if a['kind'] in kinds), 2)

    total_rev = one(c, """SELECT SUM(budgeted) AS budgeted, SUM(received) AS received,
                                 COUNT(*) AS accounts, MIN(period) AS period
                          FROM   v_revenue WHERE fy = ?""",
                    (LEDGER_FY,), 'the general fund revenue total')

    depts = [one(c, """SELECT a.dept, a.name, l.original, l.doc_id
                       FROM   ledger_snapshot l JOIN account a USING (account_id)
                       WHERE  a.dept = ? AND a.level = 'department'
                              AND a.account_type = 'expense' AND l.fy = ?""",
                 (d, LEDGER_FY), f'school appropriation department {d}')
             for d in SCHOOL_DEPTS]
    appropriation = round(sum(d['original'] for d in depts), 2)
    if appropriation <= 0:
        fail('the school appropriation came out at or below zero — the department join '
             'matched nothing usable')

    omnibus = one(c, """SELECT SUM(l.original) AS total, COUNT(*) AS depts
                        FROM   ledger_snapshot l JOIN account a USING (account_id)
                        WHERE  a.level = 'department' AND a.account_type = 'expense'
                               AND l.fy = ?""", (LEDGER_FY,), 'the omnibus budget')

    aid_budget = tot(('school', 'general'), 'budgeted')
    return dict(
        fy=LEDGER_FY, period=rows[0]['period'], doc_id=rows[0]['doc_id'],
        accounts=accounts,
        aid_budgeted=aid_budget,
        aid_received=tot(('school', 'general'), 'received'),
        school_named_budgeted=tot(('school',), 'budgeted'),
        general_named_budgeted=tot(('general',), 'budgeted'),
        local_option_budgeted=tot(('local_option',), 'budgeted'),
        local_option_received=tot(('local_option',), 'received'),
        local_option_accounts=[a['printed'] for a in accounts
                               if a['kind'] == 'local_option' and a['budgeted']],
        ch70=ch70,
        with_a_figure=sum(1 for a in accounts if a['budgeted'] or a['received']),
        revenue_total=round(total_rev['budgeted'], 2),
        revenue_accounts=total_rev['accounts'],
        aid_share_of_revenue=round(aid_budget / total_rev['budgeted'], 4),
        school_appropriation=appropriation,
        school_departments=[dict(dept=d['dept'], name=d['name'].strip(),
                                 original=round(d['original'], 2)) for d in depts],
        school_doc_id=depts[0]['doc_id'],
        omnibus=round(omnibus['total'], 2), omnibus_departments=omnibus['depts'],
        ch70_share_of_school=round(ch70['budgeted'] / appropriation, 4),
        town_share_of_school=round((appropriation - ch70['budgeted']) / appropriation, 4),
        town_share_dollars=round(appropriation - ch70['budgeted'], 2),
    )


# ----------------------------------------------------- Chapter 70 received, year by year

def receipts(c):
    rows = q(c, """SELECT fy, source, amount, status, document, page
                   FROM   annual_report_receipts
                   WHERE  source IN (%s)
                   ORDER  BY fy""" % ','.join('?' * len(CH70_NAMES)), *CH70_NAMES)
    if not rows:
        fail('no Chapter 70 rows in annual_report_receipts — the receipts join matched '
             'nothing')

    by_fy = {}
    for r in rows:
        fy = int(r['fy'])
        # A year printed on two pages of the same edition appears twice, identically.
        prev = by_fy.get(fy)
        if prev and abs(prev['amount'] - float(r['amount'])) > CENT:
            fail(f'FY{fy}: two different Chapter 70 receipt figures in the same edition '
                 f'({prev["amount"]:,.2f} and {float(r["amount"]):,.2f}) — this extract '
                 'cannot say which the report printed')
        by_fy[fy] = dict(fy=fy, amount=float(r['amount']), status=r['status'],
                         document=r['document'], page=r['page'])

    span = list(range(min(by_fy), max(by_fy) + 1))
    series = []
    for fy in span:
        r = by_fy.get(fy)
        if r is None:
            series.append(dict(fy=fy, amount=None, status='absent', stage='actual',
                               why='no Chapter 70 row was extracted from that edition',
                               unpublished_figure=None, document=None, page=None))
            continue
        ok = r['status'] == 'checked'
        series.append(dict(
            fy=fy, amount=round(r['amount'], 2) if ok else None,
            status=r['status'], stage='actual',
            why=None if ok else STATUS_REASON.get(r['status'], r['status']),
            unpublished_figure=round(r['amount'], 2) if not ok else None,
            document=r['document'], page=r['page']))

    checked = [r for r in series if r['status'] == 'checked']
    if len(checked) < 3:
        fail(f'only {len(checked)} CHECKED Chapter 70 receipt years — a series with '
             'fewer than three established points is not a series, and the unchecked '
             'years hold figures that are visibly not dollars')

    assert_one_stage(checked, 'actual', 'the Chapter 70 receipt growth rate')
    first, last = checked[0], checked[-1]
    growth = dict(
        first_fy=first['fy'], last_fy=last['fy'],
        first=first['amount'], last=last['amount'],
        years=last['fy'] - first['fy'],
        change=round(last['amount'] - first['amount'], 2),
        pct=round(last['amount'] / first['amount'] - 1.0, 6),
        cagr=cagr(first['amount'], last['amount'], last['fy'] - first['fy']),
        stage='actual')
    return dict(series=series, span=span,
                checked=[r['fy'] for r in checked],
                not_checked=[dict(fy=r['fy'], status=r['status'], why=r['why'],
                                  unpublished_figure=r['unpublished_figure'])
                             for r in series if r['status'] != 'checked'],
                growth=growth)


# ------------------------------------------------------------ the Cherry Sheet estimate

def variance(c):
    rows = q(c, """SELECT town, year, line, amount, source_file, source_ref
                   FROM   free_cash_proof WHERE line = ? ORDER BY town, year""", CL8)
    if not rows:
        fail(f'no "{CL8}" rows — the free cash proof join matched nothing')

    towns = {}
    for r in rows:
        towns.setdefault(r['town'], []).append(dict(
            year=int(r['year']), amount=float(r['amount']),
            source_file=r['source_file'], source_ref=r['source_ref']))
    if TOWN not in towns:
        fail(f'no {TOWN} row on the cherry sheet variance line — this page cannot be '
             'built without the town it is about')
    peers = sorted(t for t in towns if t != TOWN)
    if not peers:
        fail('no peer towns on the cherry sheet variance line — the comparison panel '
             'would be a single bar labelled as a comparison')

    certified = {int(r['year']): float(r['amount']) for r in q(
        c, """SELECT year, amount FROM free_cash_proof
              WHERE town = ? AND role = 'certified'""", TOWN)}
    if not certified:
        fail(f'no certified free cash rows for {TOWN} — the denominator the variance is '
             'expressed against matched nothing')

    def summary(name):
        s = towns[name]
        amounts = [r['amount'] for r in s]
        return dict(
            town=name, years=[r['year'] for r in s],
            series=[dict(year=r['year'], amount=round(r['amount'], 2)) for r in s],
            best=round(max(amounts), 2), worst=round(min(amounts), 2),
            swing=round(max(amounts) - min(amounts), 2),
            mean_abs=round(sum(abs(a) for a in amounts) / len(amounts), 2),
            over=sum(1 for a in amounts if a > 0), under=sum(1 for a in amounts if a < 0))

    lun = summary(TOWN)
    peer_rows = sorted((summary(p) for p in peers), key=lambda r: -r['swing'])
    for r in lun['series']:
        cert = certified.get(r['year'])
        r['certified'] = round(cert, 2) if cert else None
        r['share_of_certified'] = (round(r['amount'] / cert, 4) if cert else None)

    ranked = sorted([lun] + peer_rows, key=lambda r: -r['swing'])
    return dict(
        line=CL8, town=lun, peers=peer_rows,
        years=sorted({r['year'] for r in rows}),
        rank=1 + ranked.index(lun), of=len(ranked),
        source_file=rows[0]['source_file'], source_ref=towns[TOWN][0]['source_ref'],
        peer_max_swing=max(r['swing'] for r in peer_rows),
        town_names=[r['town'] for r in ranked])


# ------------------------------------------------------------------- DESE's own formula

def formula(peer_towns):
    try:
        import openpyxl
    except ImportError:                                     # pragma: no cover
        fail('openpyxl is not installed, and the DESE Chapter 70 summary is a workbook')
    from taxbase import CH70, LPS_APPROPRIATION, ENROLLMENT

    path = os.path.join(ROOT, CH70_XLSX)
    if not os.path.exists(path):
        fail(f'{CH70_XLSX} is not on disk — run scripts/sync_archive.py --pull')
    ws = openpyxl.load_workbook(path, data_only=True)['alldistricts']

    # RULE 13: assert what the sheet SAYS before reading a figure out of it. A positional
    # column is not a column name, and these headings are the only thing that makes
    # column G "Chapter 70 aid" rather than "the seventh column".
    title = (ws['A4'].value or '').strip()
    if title != 'FY27 Chapter 70 district summary':
        fail(f'A4 reads {title!r}, not the FY27 Chapter 70 district summary — this is '
             'not the sheet the column meanings below were established from')
    # The fiscal year, READ OFF THE SHEET'S OWN TITLE rather than typed. Rule 2 covers a
    # year as much as an amount: the page says "the FY27 calculation" in four places and
    # every one of them has to move when the workbook does.
    m = re.match(r'FY(\d\d) ', title)
    if not m:
        fail(f'A4 reads {title!r} and no fiscal year can be read out of it')
    sheet_fy = 2000 + int(m.group(1))
    heads = {'A6': 'LEA', 'B6': 'District', 'C6': 'Operating status*',
             'D6': 'Foundation enrollment', 'E6': 'Foundation budget',
             'F6': 'Required contribution', 'G6': 'Chapter 70 \naid',
             'H6': 'Required \nnet school spending'}
    for cell, want in heads.items():
        got = ws[cell].value
        if got != want:
            fail(f'{cell} reads {got!r}, expected {want!r} — the column meanings this '
                 'page quotes are no longer the ones the sheet prints')

    rows, row_lun = [], None
    for r in range(7, ws.max_row + 1):
        name = ws.cell(r, 2).value
        if not name:
            continue
        name = name.strip()
        operating = ws.cell(r, 3).value == 1
        fnd = ws.cell(r, 5).value or 0
        aid = ws.cell(r, 7).value or 0
        rec = dict(row=r, district=name, operating=operating,
                   enrollment=ws.cell(r, 4).value or 0,
                   foundation=float(fnd), required=float(ws.cell(r, 6).value or 0),
                   aid=float(aid), nss=float(ws.cell(r, 8).value or 0))
        rec['aid_share'] = round(aid / fnd, 6) if fnd else None
        rows.append(rec)
        if name == TOWN:
            row_lun = rec
    if row_lun is None:
        fail(f'no {TOWN} row in {CH70_XLSX} — the district lookup matched nothing')

    # TWO ROUTES TO EIGHT NUMBERS. model/taxbase.CH70 was typed from this same sheet by
    # hand; if the two ever disagree, one of them is wrong and the page must not pick.
    want = dict(foundationEnrollment=row_lun['enrollment'],
                foundationBudget=round(row_lun['foundation']),
                requiredContribution=round(row_lun['required']),
                aid=round(row_lun['aid']), requiredNSS=round(row_lun['nss']))
    for k, v in want.items():
        if abs(CH70[k] - v) > 1:
            fail(f'model/taxbase.CH70[{k!r}] is {CH70[k]:,} and row {row_lun["row"]} of '
                 f'{CH70_XLSX} says {v:,} — two routes to the same DESE figure disagree')

    # THE IDENTITY THE SHEET ITSELF STATES, and the thing that makes this page's central
    # claim a measurement rather than a reading: required contribution + Chapter 70 aid =
    # required net school spending, exactly, in DESE's own columns F, G and H. It is what
    # licenses saying the state decides BOTH halves of the minimum — how much Lunenburg
    # must put in, and how much the state puts in on top.
    if abs(row_lun['required'] + row_lun['aid'] - row_lun['nss']) > 1:
        fail(f'row {row_lun["row"]}: F+G is '
             f'{row_lun["required"] + row_lun["aid"]:,.0f} against H of '
             f'{row_lun["nss"]:,.0f} — the identity this page rests on no longer holds '
             'in the sheet, so the two halves may not be drawn as two halves of one bar')

    operating = [r for r in rows if r['operating'] and r['foundation'] > 0]
    if len(operating) < 100:
        fail(f'only {len(operating)} operating districts read out of the workbook — the '
             'statewide distribution this page ranks against matched almost nothing')
    shares = sorted(r['aid_share'] for r in operating)
    mid = len(shares) // 2
    median = shares[mid] if len(shares) % 2 else (shares[mid - 1] + shares[mid]) / 2
    below = sum(1 for s in shares if s < row_lun['aid_share'])

    # The peer towns on the cherry-sheet panel that DO NOT appear here, and why. A town in
    # a regional school district has its Chapter 70 paid to the region, so its row is
    # zero -- which is a fact about school governance, not a town getting no aid, and a
    # reader comparing the two panels will otherwise conclude the second.
    return dict(
        source=CH70_XLSX, sheet='alldistricts', row=row_lun['row'], fy=sheet_fy,
        as_of=str(ws['I1'].value)[:10] if ws['I1'].value else None,
        district=row_lun['district'],
        cells={'enrollment': f'D{row_lun["row"]}', 'foundation': f'E{row_lun["row"]}',
               'required': f'F{row_lun["row"]}', 'aid': f'G{row_lun["row"]}',
               'nss': f'H{row_lun["row"]}'},
        enrollment=row_lun['enrollment'], foundation=row_lun['foundation'],
        required=row_lun['required'], aid=row_lun['aid'], nss=row_lun['nss'],
        aid_share=row_lun['aid_share'],
        required_share=round(row_lun['required'] / row_lun['foundation'], 6),
        # The two halves of the minimum, against the total they sum to EXACTLY. These are
        # the shares the page draws, because these are the ones that add to one.
        aid_share_of_nss=round(row_lun['aid'] / row_lun['nss'], 6),
        required_share_of_nss=round(row_lun['required'] / row_lun['nss'], 6),
        aid_per_pupil=round(row_lun['aid'] / row_lun['enrollment'], 2),
        foundation_per_pupil=round(row_lun['foundation'] / row_lun['enrollment'], 2),
        operating_districts=len(operating),
        median_aid_share=round(median, 6),
        rank=len(operating) - below, percentile=round(below / len(operating), 4),
        lps_appropriation=LPS_APPROPRIATION, enrollment_actual=ENROLLMENT,
        appropriation_over_nss=round(LPS_APPROPRIATION - row_lun['nss'], 2),
        # THE PEER TOWNS FROM THE CHERRY-SHEET PANEL, classified. Four of the eight are
        # members of regional school districts, so their Chapter 70 is paid to the region
        # and their row on this sheet is zero. That is a fact about school governance, not
        # a town receiving no aid — and a reader who meets the two panels in sequence will
        # otherwise conclude the second. Named here so the page can say it.
        peers=[dict(district=r['district'], row=r['row'], operating=r['operating'],
                    aid=r['aid'], foundation=r['foundation'], aid_share=r['aid_share'])
               for r in rows if r['district'] in peer_towns],
    )


# -------------------------------------------------------------- how many children, four ways

# The measures DESE publishes for the district, all of which a reader would call "how many
# students". None of them is the foundation enrollment the aid is calculated on.
PUPIL_MEASURES = ('Student Headcount', 'In-District FTE Pupils',
                  'Out-of-District FTE Pupils', 'Total FTE Pupils')
LEA = '01620000'


def pupils(c, fmla):
    """Chapter 70 is paid per pupil, and 'per pupil' has four published answers.

    This block exists because the page is about to divide aid by a headcount, and the
    honest version of that division names which headcount. DESE publishes three counts for
    the district and calculates the aid on a fourth -- `Foundation enrollment` -- which is
    a different measurement taken on a different date. Rule 7: a proxy is never the thing.
    """
    rows = q(c, """SELECT fy, measure, value, reconciles FROM dese_measure
                   WHERE  lea = ? AND measure IN (%s)
                   ORDER  BY fy, measure""" % ','.join('?' * len(PUPIL_MEASURES)),
             LEA, *PUPIL_MEASURES)
    if not rows:
        fail('no DESE pupil counts — the enrollment join matched nothing, and the page '
             'divides aid by a headcount')
    unreconciled = [r for r in rows if r['reconciles'] != 'yes']
    if unreconciled:
        fail(f'{len(unreconciled)} DESE pupil rows do not reconcile to DESE’s own printed '
             'totals — a count this project has not established is not one it divides by')
    last_fy = max(int(r['fy']) for r in rows)
    latest = {r['measure']: float(r['value']) for r in rows if int(r['fy']) == last_fy}
    missing = [m for m in PUPIL_MEASURES if m not in latest]
    if missing:
        fail(f'FY{last_fy} is missing {missing} — the four counts this page sets side by '
             'side are not all present')
    counts = [dict(measure='Foundation enrollment', fy=2027, value=float(fmla['enrollment']),
                   who='DESE, FY27 Chapter 70 summary — the count the aid is calculated on',
                   is_formula=True, whole_district=True)]
    counts += [dict(measure=m, fy=last_fy, value=latest[m],
                    who='DESE district profile — the latest year published',
                    is_formula=False,
                    # Out-of-district FTE is a COMPONENT of the total, not a rival count of
                    # the district. Including it in the spread would make the headline
                    # difference the size of the out-of-district population rather than the
                    # disagreement between four ways of counting the same children.
                    whole_district=(m != 'Out-of-District FTE Pupils'))
               for m in PUPIL_MEASURES]
    whole = [c['value'] for c in counts if c['whole_district']]
    return dict(
        latest_fy=last_fy, formula_fy=2027, counts=counts,
        aid_per_foundation_pupil=fmla['aid_per_pupil'],
        spread=round(max(whole) - min(whole), 1),
        spread_low=min(whole), spread_high=max(whole),
        series=[dict(fy=int(r['fy']), measure=r['measure'], value=float(r['value']))
                for r in rows],
        series_years=sorted({int(r['fy']) for r in rows}))


# ------------------------------------------------------- the model, and what it rests on

def assumption(receipt_growth, fmla):
    from finance import DEFAULT_ASSUMPTIONS, FY27
    rate = DEFAULT_ASSUMPTIONS['state_aid_growth']
    base = FY27['state_aid']
    return dict(
        rate=rate, base=base,
        governor=11_404_917 if base - 471_121 == 11_404_917 else None,
        enacted_above_governor=471_121,
        enacted_pct=round(471_121 / (base - 471_121), 6),
        applies_to='total state aid, not Chapter 70 alone',
        ch70_share_of_base=round(fmla['aid'] / base, 4),
        # THE BACKTEST, and every caveat it needs. Rule 6 says check an assumption
        # against history; rule 1 says check like for like. This compares the model's
        # forward rate for TOTAL state aid to the measured rate for CHAPTER 70 RECEIPTS
        # over the checked years, which are two different quantities over two different
        # spans. It is a flag, not a correction, and the page says so.
        measured=receipt_growth['cagr'],
        measured_span=[receipt_growth['first_fy'], receipt_growth['last_fy']],
        gap_points=round((receipt_growth['cagr'] - rate) * 100, 2),
    )


# ----------------------------------------------------------------- what the town said

def said():
    out = []
    for spec in QUOTES:
        rel = f'{MINUTES}/{spec["board"]}/{spec["date"]}-{spec["kind"]}-{spec["doc"]}.txt'
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            fail(f'{rel} is not here — a quote on this page is attributed to a document '
                 'that is not in the archive')
        text = re.sub(r'\s+', ' ', open(path, encoding='utf-8', errors='replace').read())
        want = re.sub(r'\s+', ' ', spec['quote'])
        if want not in text:
            fail(f'the quote attributed to {spec["board"]} {spec["date"]} is no longer '
                 f'in {rel} — quote the source, never your rendering of it')
        board = spec['board'].replace('-', ' ').title()
        out.append(dict(
            key=spec['key'], board=board, date=spec['date'], quote=spec['quote'],
            why=spec['why'],
            cite=f'/docs/{rel.replace("sources/", "")}',
            town=f'https://www.lunenburgma.gov/AgendaCenter/ViewFile/'
                 f'{"Minutes" if spec["kind"] == "minutes" else "Agenda"}/'
                 f'_{spec["date"][5:7]}{spec["date"][8:10]}{spec["date"][:4]}-{spec["doc"]}'))
    return out


# --------------------------------------------------------------------------- the build

def build():
    if not os.path.exists(DB):
        fail(f'{os.path.relpath(DB, ROOT)} is not here — run scripts/build_db.py')
    c = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    c.row_factory = sqlite3.Row

    led = ledger(c)
    rec = receipts(c)
    var = variance(c)
    fmla = formula(set(var['town_names']))
    pup = pupils(c, fmla)
    asm = assumption(rec['growth'], fmla)
    quotes = said()

    # THE STATED FIGURE, RECOMPUTED. A School Committee member said Chapter 70 covers 35%
    # of the school budget. That is a claim about two numbers this project holds, so it is
    # checked rather than repeated -- and if it stopped matching, the page would say so
    # rather than quietly dropping the quote.
    corroboration = dict(
        stated=0.35, stated_by='School Committee', stated_on='2026-06-24',
        recomputed=led['ch70_share_of_school'],
        numerator=led['ch70']['budgeted'], denominator=led['school_appropriation'],
        agrees=abs(led['ch70_share_of_school'] - 0.35) < 0.01,
        note=f'Chapter 70 budgeted in the FY{LEDGER_FY} revenue ledger against the '
             f'FY{LEDGER_FY} appropriation to departments '
             f'{" and ".join(d["dept"] for d in led["school_departments"])}. Both are '
             'BUDGET figures from the same ledger, which is what makes the ratio '
             'meaningful (rule 1).')

    # WHERE WE DIFFER FROM SOMETHING ALREADY WRITTEN. Carried in the payload and rendered
    # beside the figure rather than reconciled away.
    recomputed = [
        dict(what='Chapter 70’s size in the school budget',
             where='This project’s own working notes describe Chapter 70 as "roughly '
                   '$11.4M of a $26.6M school budget"',
             ours=f'Chapter 70 alone is {led["ch70"]["budgeted"]:,.0f} in the FY'
                  f'{LEDGER_FY} revenue ledger — {led["ch70_share_of_school"] * 100:.0f}% '
                  f'of the {led["school_appropriation"]:,.0f} school appropriation',
             why='$11,404,917 is the Governor’s FY27 figure for ALL state aid to '
                 'Lunenburg, not Chapter 70 — it is the line the Town Manager’s 17 April '
                 '2026 press release calls "State aid", and it includes Unrestricted '
                 'General Government Aid and every other cherry sheet receipt. The two '
                 'figures were folded together. The School Committee’s own "35%" is the '
                 'Chapter 70 share, and it is the one that recomputes.'),
        dict(what='What the projection assumes state aid will do',
             where='show-your-work.md records the state aid growth rate as BARE — '
                   '"Nothing. No stated source and no derivation"',
             ours=f'The model grows total state aid at {asm["rate"] * 100:.1f}% a year. '
                  f'Chapter 70 RECEIPTS grew {asm["measured"] * 100:.2f}% a year across '
                  f'the {rec["growth"]["years"]} checked years FY{rec["growth"]["first_fy"]} '
                  f'to FY{rec["growth"]["last_fy"]}',
             why='These are not the same quantity over the same span, so this is not a '
                 'correction and no rate is changed here. It is the flag rule 6 asks for: '
                 'an assumption with no stated source, and a measured series that runs '
                 f'{asm["gap_points"]:.1f} points above it.'),
    ]

    gaps = q(c, 'SELECT side, what, why FROM money_gaps')
    keep = [g for g in gaps
            if any(w in (g['what'] + ' ' + g['why']).lower()
                   for w in ('state aid', 'chapter 70', 'cherry sheet', 'grant',
                             'end of year financial report', 'funding source'))]
    if not keep:
        fail('no money_gaps row mentions state aid — rule 7c says a limit this page hits '
             'is registered there, and the join that reads them back matched nothing')

    with open(REPORTS, encoding='utf-8') as fh:
        by_id = {r['id']: r for r in json.load(fh)['reports']}
    related = []
    for rid, why in RELATED:
        r = by_id.get(rid)
        if r is None:
            fail(f'reports.json no longer carries {rid}, which this page is built from')
        related.append(dict(id=rid, title=r['title'], why=why, words=r['words'],
                            updated=r['updated'], url=r['markdown']['url'],
                            pdf=(r.get('pdf') or {}).get('url')))

    def split(g):
        w = g['why']
        i = w.find('— closes:')
        return dict(side=g['side'], what=g['what'],
                    why=(w[:i].strip() if i >= 0 else w.strip()),
                    closes=(w[i + len('— closes:'):].strip() if i >= 0 else None))

    return dict(
        generated_by='scripts/build_state_aid.py',
        source='sources/data/lunenburg.db — v_revenue, ledger_snapshot, account, '
               'annual_report_receipts, free_cash_proof, money_gaps; '
               f'{CH70_XLSX}; model/finance.py; model/taxbase.py; {MINUTES}/',
        ledger=led,
        receipts=rec,
        variance=var,
        formula=fmla,
        pupils=pup,
        assumption=asm,
        said=quotes,
        corroboration=corroboration,
        recomputed=recomputed,
        gaps=[split(g) for g in keep],
        related=related,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='fail if the published file is not what this would write')
    a = ap.parse_args()
    payload = json.dumps(build(), indent=1, sort_keys=True) + '\n'
    rel = os.path.relpath(OUT, ROOT)
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if have != payload:
            print(f'STALE — {rel} is not what the archive now produces. '
                  'Run scripts/build_state_aid.py.')
            return 1
        print(f'ok — {rel} reproduces from the archive')
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(payload)
    d = json.loads(payload)
    print(f'wrote {rel} — Chapter 70 is '
          f'{d["ledger"]["ch70_share_of_school"] * 100:.1f}% of the FY'
          f'{d["ledger"]["fy"]} school appropriation; '
          f'{len(d["receipts"]["checked"])} checked receipt years of '
          f'{len(d["receipts"]["span"])}; cherry sheet variance across '
          f'{len(d["variance"]["years"])} years and {d["variance"]["of"]} towns')
    return 0


if __name__ == '__main__':
    sys.exit(main())
