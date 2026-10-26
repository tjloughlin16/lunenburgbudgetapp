#!/usr/bin/env python3
"""THE SCHOOL BUDGET, ALL FUNDS: every budget line with every fund behind it. A hub and six pages.

    python3 scripts/build_school_all_funds.py           # write fy28/public/data/topics/*.json
                                                        #   and fy28/public/data/school-all-funds-model.json, and sources/analyses/school-all-funds.md
    python3 scripts/build_school_all_funds.py --check   # fail if any output would change

    school-all-funds          /school-all-funds                            the hub
    school-money-in           /school-all-funds/school-money-in            what came in, from where
    budget-lines-all-funds    /school-all-funds/budget-lines-all-funds     every line: voted, GF, other funds
    outside-the-general-fund  /school-all-funds/outside-the-general-fund   fund x line x payee
    unspent-by-fund           /school-all-funds/unspent-by-fund            receipts, spending, balance
    grant-coding              /school-all-funds/grant-coding               H2: is grant spending on a line?
    sped-all-funds            /special-education/sped-all-funds            H1: special education, filtered
    sped-grants               /special-education/sped-grants               every special education stream outside the vote

Phase 3 of notes/MASTER-PLAN.md (items 11-15 and the two hypotheses). TJ, 22 October 2026: "the
schools' 'budget' is just the general fund. They layer in grants and stuff to their
PowerPoints, but how that gets budgeted is SUPER unclear."

WHAT IT READS. `scripts/journal.py` only, for the journal: its loader, its source-code
columns, its special education list, and -- section 6 -- the fund groups and the function-code
classes this report introduced. Nothing here re-decides any of those.

WHAT A FIGURE IS (rule 11). A posting to a school account in the Town's MUNIS journal,
FY2023 p0 to FY2026 p13. Not what anything costs: benefits and costs the Town books outside the
school department are not in it. FY2026 is not closed in this run (journal.OPEN_FY).

THE RECONCILIATION (rule 13: tie to a printed total, refuse otherwise). Before a figure is
written, `reconcile()` requires, to the cent:
  1. every account the Town's published period-13 spreadsheets hold (`munis-school-ytd.csv`,
     general fund and special funds, FY2023-FY2026): the journal's actual, original budget,
     transfers and encumbrances equal the spreadsheet's, account by account, year by year; and
     every spreadsheet account the journal lacks prints zero;
  2. every account in FY2026: the journal's lines sum to the figures the report itself prints
     (`munis-school-journal-accounts.csv`).
Two INDEPENDENT documents are compared and reported, not required (they are other publishers'
classifications of the same money): the FY2023 annual town report's special revenue
roll-forward, and DESE's End of Year Financial Report for FY2023.

THE FUNCTION CODE (journal.function_class). A line is a code the general fund budget is voted
on. Spending on 0000 or on a heading (1000, 2000, 2300, 2400, 4000) is UNATTRIBUTED: shown as
its own row, never spread across lines by us.

RULE 7. Every figure is a posting. Why a grant was booked to a heading, why a balance grew, why
special education spending ran past its voted budget -- none of it is in a ledger, and each page
says so beside the figure, with the document that would settle it.

THE REDACTION. Providers are named; recipients are not (memory: redaction principle). The
payee table on the outside-funds page lists only the largest named payees, so no masked
family's amount can be read off it by subtraction.
"""
import argparse
import csv
import json
import os
import re
import statistics
import sys
from collections import defaultdict
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP
import topic_blocks as TB  # noqa: E402
import topics as REG  # noqa: E402
from brief import step  # noqa: E402
import journal as J  # noqa: E402

OUT_DIR = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics')
# The model's own payload: every figure the pages use, and the reconciliation counts, for the
# verifier and for anybody who wants the numbers rather than the pages.
# Named -model so it can never be mistaken for a report payload: /analysis/<id> fetches
# /data/<id>.json, and the markdown below is served there as /analysis/school-all-funds.
MODEL_OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'school-all-funds-model.json')
# The markdown (rule 7d): what /docs serves, what the PDF is rendered from, and what an agent
# that cannot run JavaScript reads. Written from the SAME pages in the same pass, so the two
# cannot disagree. UNLISTED (sources/analyses/UNLISTED): the topic pages are the doors.
MD_OUT = os.path.join(ROOT, 'sources', 'analyses', 'school-all-funds.md')
ME = os.path.basename(__file__)
HUB = 'school-all-funds'
MINE = sorted(t for t, (_, _, gen) in REG.TOPICS.items() if gen == ME)
DATA = os.path.join(ROOT, 'sources', 'data')
YTD_CSV = os.path.join(DATA, 'munis-school-ytd.csv')
AR_CSV = os.path.join(DATA, 'special-revenue-read.csv')
EOYR_CSV = os.path.join(DATA, 'eoyr-schedule1.csv')
CHERRY_CSV = os.path.join(DATA, 'dls-cherry-sheet.csv')
Y = J.YEARS
F0, F1 = Y[0], Y[-1]
LAST_CLOSED = F1 - 1
GROUPS = J.FUND_GROUPS
OUTSIDE = GROUPS[1:]
CENT = Decimal('0.005')

# WHICH ANNUAL-REPORT ROW IS WHICH FUND. Declared one at a time, by name: the FY2023 annual town
# report's special revenue schedule (special-revenue-read.csv) names the school's carrying
# funds in words, the journal by number. The pairing is a NAME match; the figures are then
# compared, never used to make it.
AR_FUND = {
    '1300': 'Recovery for Lost Books',
    '1301': 'Chapter 658 School Athletics',
    '1302': 'Adult Education',
    '1305': 'After School Activities',
    '1306': 'School Facilities Use',
    '1308': 'School Choice',
    '1310': 'Greenthumb Revolving',
    '1311': 'School Gift Fund',
    '1312': 'Extended Day Revolving Fund',
    '2200': 'School Lunch',
    '2640': '50/50 Grant Sped Tuitions',
    '9002': 'Custodian Special Details',
}
# DESE's End of Year Financial Report, Schedule 1, section C.2, line 3080 (TOTAL GRANT & SPECIAL
# FUND EXPENDITURES), FY2023: the column, and the journal funds that are the same money.
EOYR_PAIRS = [
    ('Revolving and Special Funds Circuit Breaker', 'circuit breaker', lambda a: a['fund'] == '2640'),
    ('School Nutrition', 'school lunch', lambda a: a['fund'] == '2200'),
    ('Sch Choice & Other Day Tuition', 'school choice', lambda a: a['fund'] == '1308'),
    ('Private Grants & Gifts', 'school gift fund', lambda a: a['fund'] == '1311'),
    ('IDEA FC 240', 'IDEA grants (#240)',
     lambda a: J.fund_group(a) == 'Grants' and J.grant_code(a['fund_name']) == '240'),
]
# Names for codes DESE's chart does not print, or prints only as a heading. Ours, said as ours.
CODE_NAMES = {
    '0000': 'No function code',
    '1000': 'Administration (heading only)',
    '2000': 'Instruction (heading only)',
    '2300': 'Teaching (heading only)',
    '2400': 'Instructional materials (heading only)',
    '4000': 'Operations (heading only)',
    '0300': 'Salary reserve',
}
SERIES = [('1', 'Administration'), ('2', 'Instruction'), ('3', 'Other student services'),
          ('4', 'Buildings and operations'), ('5', 'Benefits and fixed charges'),
          ('7', 'Equipment'), ('9', 'Tuition to other schools')]
TOP_LINES = 16          # lines drawn in the ranking, beside the unattributed row
TOP_PAYEES = 12
# THE SPECIAL EDUCATION STREAMS OUTSIDE THE VOTE, by DESE fund code (sped-grants). Named with
# journal.GRANT_PROGRAM. The page refuses if these and the circuit breaker stop adding to the
# other-funds spending on sped-all-funds, so a new stream cannot be silently left off.
SG_CODES = ('240', '262', '252', '264', '274', '298')
ALLOC_CSV = os.path.join(DATA, 'dese-entitlement-allocations.csv')
CB_JSON = os.path.join(ROOT, 'fy28', 'public', 'data', 'circuit-breaker.json')
MIN_AID_JSON = os.path.join(ROOT, 'fy28', 'public', 'data', 'minimum-aid.json')
BENEFITS_CLOSES = ('the Town’s schedule of school benefits and town-side costs, by fund')


def fail(msg):
    raise SystemExit('build_school_all_funds: ' + msg)


def fl(x):
    return float(x)


def D(s):
    return Decimal(str(round(float(s or 0), 2)))


# ======================================================================== reconciliation

def reconcile():
    """Tie the journal to every printed total that covers it, or refuse to write anything."""
    A, L = J.accounts(), J.lines()
    j = defaultdict(Decimal)
    for r in L:
        j[(r['fy'], r['account'], r['posts_to'])] += r['amt']
    cols = (('ytd_expended', 'actual'), ('original_approp', 'original_budget'),
            ('transfers_adjustments', 'transfer'), ('encumbrances', 'encumbrance'))
    held, rows, bad, zero_absent = set(), 0, [], 0
    outside_dept = defaultdict(Decimal)
    outside_fund = defaultdict(Decimal)
    for y in csv.DictReader(open(YTD_CSV, encoding='utf-8', newline='')):
        fy, acc = int(y['fiscal_year']), y['account']
        if acc not in A:
            # The spreadsheets carry a few accounts in department 000 -- investment income the
            # Town books on a fund's own revenue line, outside the school department. Report 1 is
            # the school department's accounts, so these are absent by scope. Any other absence
            # with figures in it refuses.
            if any(D(y[c]) for c, _ in cols) and J.department(acc) in J.DISTRICT_DEPTS:
                bad.append('%s %s is in the period-13 spreadsheet with figures and not in the '
                           'journal' % (fy, acc))
            outside_dept[fy] += D(y['ytd_expended'])
            outside_fund[(fy, y['fund'])] += D(y['ytd_expended'])
            zero_absent += 1
            continue
        rows += 1
        held.add((fy, acc))
        for c, p in cols:
            if abs(D(y[c]) - j[(fy, acc, p)]) > CENT:
                bad.append('%s %s %s: spreadsheet %s, journal %s' % (fy, acc, c, y[c], j[(fy, acc, p)]))
    printed = 0
    for acc, a in A.items():
        for c, p in (('original_approp', 'original_budget'), ('transfers_adjustments', 'transfer'),
                     ('ytd_actual', 'actual'), ('encumbrances', 'encumbrance')):
            if abs(Decimal(a[c]) - j[(F1, acc, p)]) > CENT:
                bad.append('FY%d %s %s: report prints %s, lines sum to %s'
                           % (F1, acc, c, a[c], j[(F1, acc, p)]))
        printed += 1
    if bad:
        fail('the journal does not tie to the printed totals:\n  ' + '\n  '.join(bad[:20]))
    # How much of each year's spending the spreadsheets cover, so the tie is not oversold.
    cov = defaultdict(Decimal)
    for r in L:
        a = A[r['account']]
        if r['posts_to'] == 'actual' and J.is_expense(a):
            cov[(r['fy'], 'all')] += abs(r['amt'])
            if (r['fy'], r['account']) in held:
                cov[(r['fy'], 'held')] += abs(r['amt'])
    return dict(ytd_rows=rows, ytd_accounts=len({a for _, a in held}), ytd_outside_dept=zero_absent,
                ytd_outside_dept_amount={y: fl(outside_dept[y]) for y in Y},
                _outside_fund=outside_fund,
                printed_accounts=printed,
                coverage={y: fl(100 * cov[(y, 'held')] / cov[(y, 'all')]) for y in Y})


def annual_report_tie(m, rc):
    """FY2023: the journal's receipts and spending per carrying fund against the annual town
    report's special revenue schedule. Reported fund by fund; a difference is shown, not hidden."""
    ar = {r['fund']: r for r in csv.DictReader(open(AR_CSV, encoding='utf-8', newline=''))
          if r['fy'] == str(F0) and r['group'] == 'SCHOOL DEPARTMENT'}
    out = []
    for f, name in AR_FUND.items():
        if name not in ar:
            fail('the FY%d annual report has no school fund named %r' % (F0, name))
        r = ar[name]
        rec, sp = m['fund_rec'].get((F0, f), 0.0), m['fund_cash'].get((F0, f), 0.0)
        ar_rec, ar_sp = float(r['receipts'] or 0), float(r['disbursements'] or 0)
        # Investment income the Town books on the fund's revenue line outside the school
        # department (department 000): in the town report's receipts, not in Report 1.
        inv = -fl(rc['_outside_fund'].get((F0, f), Decimal(0)))
        out.append(dict(fund=f, name=m['fund_name'][f], ar_name=name, interest=inv,
                        ties_with_interest=abs(rec + inv - ar_rec) < 0.005 and abs(sp - ar_sp) < 0.005,
                        forward=float(r['forward'] or 0), carried=float(r['carried'] or 0),
                        receipts=rec, ar_receipts=ar_rec, spent=sp, ar_spent=ar_sp,
                        ties=abs(rec - ar_rec) < 0.005 and abs(sp - ar_sp) < 0.005,
                        net_ties=abs((rec - sp) - (ar_rec - ar_sp)) < 0.005))
    return out


def eoyr_tie(m):
    rows = {r['column']: float(r['amount']) for r in csv.DictReader(open(EOYR_CSV, encoding='utf-8'))
            if r['fiscal_year'] == 'FY%d' % F0 and r['line'] == '3080'}
    A = J.accounts()
    out = []
    for col, label, pred in EOYR_PAIRS:
        if col not in rows:
            fail('EOYR FY%d line 3080 has no column %r' % (F0, col))
        ours = sum(v for (y, acc), v in m['acct_cash'].items() if y == F0 and pred(A[acc]))
        out.append(dict(column=col, label=label, eoyr=rows[col], journal=round(ours),
                        ties=abs(rows[col] - round(ours)) < 0.5))
    return out


# ======================================================================== the model

def code_names():
    """DESE's name for each function code, from the EOYR's own row labels; ours for the rest."""
    names = {}
    for r in csv.DictReader(open(EOYR_CSV, encoding='utf-8')):
        if r['section'].startswith('C.2') and re.fullmatch(r'\d{4}', r['function_code']):
            n = re.sub(r'\s*\(\d{4}\)\s*$', '', r['description']).strip()
            names.setdefault(r['function_code'], n)
    names.update(CODE_NAMES)
    return names


def model():
    """Every figure the pages use, on TWO bases, each for one kind of question (journal.py,
    WHAT "SPENT" MEANS):

      SPENT (`J.is_spent`: payments plus what was still owed at the year end) -- everything a
        page shows as spent beside a budget or a vote: `exp`, and so `spent`, `all`, `outside`,
        `unattr`, the line table, the grant coding (`by_fund_code`), special education, and an
        ended grant's spending against its loaded budget (`fund_spent`).
      CASH (`posts_to == 'actual'` alone) -- what a fund paid out: `fund_cash`, which rolls a
        balance forward (an order not yet paid has not left the fund, so a balance is receipts
        less payments) and ties to the annual town report's disbursements; `acct_cash`, which
        ties to DESE's End of Year report; and `payee`, which is invoices PAID to a payee.
    The ties compare with what those documents print, which is actuals; only the presented
    spending changes basis. In a closed year the two are equal (the close zeroes the
    encumbrances), so the difference is FY2026's open orders."""
    A, L = J.accounts(), J.lines()
    m = dict(fund_name={a['fund']: a['fund_name'] for a in A.values()})
    m['acct_cash'] = defaultdict(float)
    exp = defaultdict(float)           # (fy, group, code) -> spent (payments plus owed)
    gfb = defaultdict(float)           # (fy, code, 'voted'|'revised') -> general fund budget
    rec = defaultdict(float)           # (fy, group) -> receipts
    fund_rec, fund_bud = defaultdict(float), defaultdict(float)
    fund_cash = defaultdict(float)     # (fy, fund) -> payments only: balances and the town report tie
    fund_spent = defaultdict(float)    # (fy, fund) -> spent, against a fund's loaded budget
    by_fund_code = defaultdict(float)  # (fy, fund, code) -> spent outside the general fund
    payee = defaultdict(float)         # (group, payee) -> four-year invoices PAID outside the GF
    sped = defaultdict(float)          # (fy, side, column)
    for r in L:
        a = A[r['account']]
        g, code, amt = J.fund_group(a), J.function(r['account']), fl(r['amt'])
        if J.is_expense(a):
            if J.is_spent(r):
                exp[(r['fy'], g, code)] += amt
                fund_spent[(r['fy'], a['fund'])] += amt
                if g != 'General fund':
                    by_fund_code[(r['fy'], a['fund'], code)] += amt
            if r['posts_to'] == 'actual':
                m['acct_cash'][(r['fy'], r['account'])] += amt
                fund_cash[(r['fy'], a['fund'])] += amt
                if g != 'General fund':
                    p = J.payee(r)
                    if p is not None and p is not J.MASKED and J.KIND_OF[r['source']] == 'invoice':
                        payee[(g, p)] += amt
            elif r['posts_to'] in ('original_budget', 'transfer'):
                fund_bud[(r['fy'], a['fund'])] += amt
                if g == 'General fund':
                    gfb[(r['fy'], code, 'revised')] += amt
                    if r['posts_to'] == 'original_budget' or J.is_netting(r):
                        gfb[(r['fy'], code, 'voted')] += amt
            if J.in_sped_total(a):
                side = 'gf' if g == 'General fund' else 'out'
                col = 'original_budget' if J.is_netting(r) else r['posts_to']   # voted is net
                sped[(r['fy'], side, col)] += amt
                if side == 'out' and r['posts_to'] == 'actual':
                    sped[(r['fy'], 'fund:' + J.sped_fund(a), 'actual')] += amt
                sped[(r['fy'], side + ':' + J.component(a), col)] += amt
                if J.is_spent(r):
                    sped[(r['fy'], 'spent', J.sped_fund(a), J.component(a))] += amt
                    # The grant PROGRAM, by DESE's fund code: one column each on sped-all-funds.
                    gc = J.grant_code(a['fund_name']) if side == 'out' and a['fund'] != '2640' else None
                    if gc:
                        sped[(r['fy'], 'spent', 'code:' + gc, J.component(a))] += amt
        elif J.is_revenue(a) and r['posts_to'] == 'actual':
            rec[(r['fy'], g)] -= amt
            fund_rec[(r['fy'], a['fund'])] -= amt
    # What the open year still owes, by group: the whole difference between the two bases.
    m['owed'] = {(y, g): sum(fl(r['amt']) for r in L if r['fy'] == y and r['posts_to'] == 'encumbrance'
                             and J.is_expense(A[r['account']]) and J.fund_group(A[r['account']]) == g)
                 for y in Y for g in GROUPS}
    for (y, g), v in m['owed'].items():
        if y != F1 and abs(v) > 0.005:
            fail('%s is closed but its %s still carries %.2f owed; the pages say only %s does'
                 % (C.fy(y), g, v, C.fy(F1)))
    m.update(exp=exp, gfb=gfb, rec=rec, fund_rec=fund_rec, fund_cash=fund_cash,
             fund_spent=fund_spent, fund_bud=fund_bud, by_fund_code=by_fund_code, payee=payee,
             sped=sped)
    codes = sorted({k[2] for k in exp} | {k[1] for k in gfb})
    m['codes'] = codes
    m['cls'] = {c: J.function_class(c) for c in codes}
    m['names'] = code_names()
    for c in codes:
        if c not in m['names']:
            # The ledger's own most common account description for the code: named, not invented.
            descs = defaultdict(int)
            for a in A.values():
                if J.function(a['account']) == c and J.is_expense(a):
                    descs[a['account_description']] += 1
            m['names'][c] = max(descs, key=lambda d: (descs[d], d)).title() if descs else c
    # ---- per-year totals
    tot = lambda y, g: sum(v for (yy, gg, _), v in exp.items() if yy == y and gg == g)
    m['spent'] = {(y, g): tot(y, g) for y in Y for g in GROUPS}
    m['gf_voted'] = {y: sum(v for (yy, _, k), v in gfb.items() if yy == y and k == 'voted') for y in Y}
    m['gf_revised'] = {y: sum(v for (yy, _, k), v in gfb.items() if yy == y and k == 'revised') for y in Y}
    m['all'] = {y: sum(m['spent'][(y, g)] for g in GROUPS) for y in Y}
    m['outside'] = {y: m['all'][y] - m['spent'][(y, 'General fund')] for y in Y}
    m['unattr'] = {y: sum(v for (yy, g, c), v in exp.items()
                          if yy == y and g != 'General fund' and m['cls'][c] in ('none', 'heading'))
                   for y in Y}
    m['receipts'] = {(y, g): rec.get((y, g), 0.0) for y in Y for g in OUTSIDE}
    ch70 = {int(r['fy']): float(r['amount']) for r in csv.DictReader(open(CHERRY_CSV, encoding='utf-8'))
            if r['name'] == 'Lunenburg' and r['line'] == 'Chapter 70' and r['flow'] == 'Receipts'}
    m['ch70'] = {y: ch70[y] for y in Y}
    return m


# ======================================================================== H2: grant coding

def grant_coding(m):
    """Per grant fund and year: how much of its spending is on a line, a heading, or no code."""
    A = J.accounts()
    out = defaultdict(lambda: defaultdict(float))
    for (y, f, c), v in m['by_fund_code'].items():
        a = next(x for x in A.values() if x['fund'] == f)
        if J.fund_group(a) != 'Grants':
            continue
        out[(f, y)][m['cls'][c]] += v
    return out


def idea_years(m, gc):
    """The IDEA entitlement grant (#240), year by year: dollars on a budget line."""
    A = J.accounts()
    funds = sorted({a['fund'] for a in A.values() if J.fund_group(a) == 'Grants'
                    and J.grant_code(a['fund_name']) == '240'})
    rows = {}
    for y in Y:
        on = {k: sum(gc[(f, y)].get(k, 0.0) for f in funds) for k in J.FUNCTION_CLASSES}
        rows[y] = on
    return funds, rows


def grant_year(name):
    """The fiscal year a grant fund is named for: 'FY24 #240' -> 2024. None if unnamed."""
    mm = re.match(r"\s*FY\s*'?\s*(\d\d)(?!\d)", name)
    return 2000 + int(mm.group(1)) if mm else None


def read_allocations(codes=SG_CODES):
    """{(code, fy): dollars}: DESE's entitlement allocations to Lunenburg (district 0162), every
    year the file lists -- for the special education codes by default, or for `codes` (None:
    every code). Per code; build_serf_topics.read_idea sums #240 and #262 from the same file,
    and build() asserts the two agree."""
    out = {}
    for r in csv.DictReader(open(ALLOC_CSV, encoding='utf-8')):
        c = r['fund_code'].lstrip('0')
        if r['district_code'] == '0162' and (codes is None or c in codes):
            if (c, int(r['fy'])) in out:
                fail('DESE allocations list %s for %s twice' % (c, r['fy']))
            out[(c, int(r['fy']))] = float(r['amount'])
    return out


# ======================================================================== trend charts
# ONE GRANT'S HISTORY, AS A LINE (TJ, 26 October 2026: "add trend line graphs for each grant so
# we can see how they are trending and what the average is or projected amount for the next
# year"). Shared by sped-grants and school-money-in, so a grant's trend is drawn one way.
# LINES SHOW TRENDS, BARS SHOW COMPOSITION: each stream on its own scale (a shared one
# flattens the small grants), its average as a reference line, and next year as its own track
# -- a published figure where one exists, else OUR estimate at the median yearly change.

_U = lambda v: figure(v, C.usd(v))
_F = lambda v: figure(v, C.fy(v), 'fiscal year')
_P = lambda v, dp=1: figure(v, C.pct(v, dp))
_N = lambda v, unit=None: figure(v, C.num(v), unit)


def alloc_trend(alloc, k, who):
    """One code's allocations: (years, values, average, median yearly change, next year at it)."""
    ys_ = sorted(y for (c, y) in alloc if c == k)
    if ys_ != list(range(ys_[0], ys_[-1] + 1)):
        fail('%s: #%s skips an allocation year' % (who, k))
    v = [alloc[(k, y)] for y in ys_]
    step_ = statistics.median(b / a_ - 1 for a_, b in zip(v, v[1:]))
    return ys_, v, statistics.mean(v), step_, v[-1] * (1 + step_)


def fell(v):
    """Years in a row the series fell, latest first."""
    n = 0
    while n + 1 < len(v) and v[-1 - n] < v[-2 - n]:
        n += 1
    return n


def trend_chart(title, ys_, hist_name, hist, nxt_y, nxt, nxt_name, nxt_basis, avg, avg_label,
                note, so, place='chart', note_allow=()):
    """A stream's history as a line, with its average, and next year as its own track in its
    own basis (the district's listing, DESE's announcement, or our estimate) -- a segment from
    the last real year, so it reads as a continuation, not a fact. nxt_y None: an ended
    stream, drawn with no next year."""
    xs = list(ys_) + ([nxt_y] if nxt_y else [])
    tracks = [TP.track(hist_name, list(hist) + ([None] if nxt_y else []), 'published', 'line')]
    if nxt_y:
        tracks.append(TP.track(nxt_name, [None] * (len(ys_) - 1) + [hist[-1], nxt], nxt_basis, 'line'))
    return TB.chart(TP.series(title, [C.fy(y) for y in xs], tracks, '$', kind='line',
                              reference=None if avg is None else (avg, avg_label), note=note[0],
                              note_figures=note[1], note_allow=note_allow),
                    place=place, so=so)


def alloc_trend_chart(alloc, k, name, who, place='chart'):
    """An entitlement grant's allocations by award year, with next year as OUR estimate."""
    ys_, v, avg, st, est = alloc_trend(alloc, k, who)
    nm = '%s (#%s)' % (name, k)
    return trend_chart(
        '%s, allocated each year' % name, ys_, nm + ', allocated', v, ys_[-1] + 1,
        round(est), 'Next year, our estimate', 'estimate', avg,
        'Average, %s to %s' % (C.fy(ys_[0]), C.fy(ys_[-1])),
        ('DESE’s allocations by award year; %s is announced. The dashed end '
         'is ours: %s moved by the median yearly change, %s.'
         % (C.fy(ys_[-1]), C.fy(ys_[-1]), C.pct(100 * st)),
         {'y': _F(ys_[-1]), 'p': _P(100 * st)}),
        ('An average of %s a year, and %s announced for %s. At its usual yearly '
         'change %s would be about %s: our estimate, not an award.%s'
         % (C.usd(avg), C.usd(v[-1]), C.fy(ys_[-1]), C.fy(ys_[-1] + 1), C.usd(round(est)),
            (' It fell in each of the last %s years, so the estimate may run high.'
             % C.num(fell(v))) if fell(v) >= 2 else ''),
         dict({'a': _U(avg), 'b': _U(v[-1]), 'y': _F(ys_[-1]), 'z': _F(ys_[-1] + 1),
               'c': _U(round(est))}, **({'n': _N(fell(v))} if fell(v) >= 2 else {}))),
        place=place)


# ======================================================================== pages

def sources():
    return [
        dict(label='Lunenburg Budget Project — munis-school-journal.csv (every school journal '
                   'line, FY2023–FY2026, our redacted reading of the Town’s Report 1)',
             href=J.PUBLIC['journal']),
        dict(label='Lunenburg Budget Project — munis-school-journal-accounts.csv (every school '
                   'account, with the FY2026 figures the report prints)', href=J.PUBLIC['accounts']),
        dict(label='Town of Lunenburg — period-13 MUNIS spreadsheets, school general fund and '
                   'special funds, FY2023–FY2026 (munis-school-ytd.csv), tied account by account',
             href='/docs/data/munis-school-ytd.csv'),
        dict(label='Town of Lunenburg — how the journal reached us, and what was redacted',
             href='/docs/town-ledgers/account-details/PROVENANCE-fy2023-fy2026-p13-school-journal.md'),
    ]


def build():
    rc = reconcile()
    m = model()
    art = annual_report_tie(m, rc)
    rc.pop('_outside_fund')
    eo = eoyr_tie(m)
    gc = grant_coding(m)
    U = lambda v: figure(v, C.usd(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    f, con = LD.fact, TP.conclusion
    pc = lambda a, b: 100.0 * (b - a) / a
    years = [C.fy(y) for y in Y]
    open_note = '%s is not yet closed in this run.' % C.fy(F1)
    # Said wherever a page shows spending beside a budget (journal.py, WHAT "SPENT" MEANS). Its
    # only figure is the open year, so it carries note_figures {'y': F(F1)} like open_note.
    spent_note = 'Spent includes what was still owed; only %s owed any.' % C.fy(F1)
    owed1 = sum(m['owed'][(F1, g)] for g in GROUPS)
    out = {}
    sp = m['spent']
    gfs = {y: sp[(y, 'General fund')] for y in Y}

    # ================================================== budget-lines-all-funds
    y1 = F1
    line_rows = []
    for c in m['codes']:
        v = m['gfb'].get((y1, c, 'voted'), 0.0)
        g = m['exp'].get((y1, 'General fund', c), 0.0)
        o = sum(m['exp'].get((y1, gg, c), 0.0) for gg in OUTSIDE)
        if v or g or o:
            line_rows.append(dict(code=c, name=m['names'][c], cls=m['cls'][c], voted=v, gf=g,
                                  out=o, all=g + o))
    lines_only = [r for r in line_rows if r['cls'] == 'line']
    un = [r for r in line_rows if r['cls'] in ('none', 'heading')]
    un_total = sum(r['all'] for r in un)
    un_out = sum(r['out'] for r in un)
    out_on_lines = sum(r['out'] for r in lines_only)
    n_lines = len(lines_only)
    n_lines_out = sum(1 for r in lines_only if abs(r['out']) >= 0.5)
    all1, out1 = m['all'][y1], m['outside'][y1]
    if abs(sum(r['all'] for r in line_rows) - all1) > 0.01:
        fail('the line table does not foot to every fund spent in %s' % C.fy(y1))
    big = sorted(lines_only, key=lambda r: -r['out'])[0]
    lx = {}
    lx['voted'] = f('voted', U(m['gf_voted'][y1]), 'voted, general fund, %s' % C.fy(y1), 'published', {'y': F(y1)})
    lx['gf'] = f('gf', U(gfs[y1]), 'spent from the general fund, %s' % C.fy(y1), 'published', {'y': F(y1)})
    lx['out'] = f('out', U(out1), 'spent from every other fund, %s' % C.fy(y1), 'published', {'y': F(y1)})
    lx['all'] = f('all', U(all1), 'spent from every fund, %s' % C.fy(y1), 'published', {'y': F(y1)})
    lx['onlines'] = f('onlines', U(out_on_lines), 'other funds, on a voted budget line', 'published')
    lx['unattr'] = f('unattr', U(un_out), 'other funds, on no line', 'published')
    lx['nlines'] = f('nlines', N(n_lines, 'lines'), 'budget lines with a vote, %s' % C.fy(y1), 'published', {'y': F(y1)})
    lx['nout'] = f('nout', N(n_lines_out, 'lines'), 'of them with other funds spent on them', 'published')
    lx['why'] = f('why', None, 'what each grant on no line paid for', 'gap',
                  closes='the district’s grant budgets and DESE final expenditure reports, by function code')

    def lrow(r):
        # general fund + other funds = every fund, printed side by side, so they foot
        (g, o), a = C.footed([r['gf'], r['out']])
        return dict(label='%s %s' % (r['code'], r['name']),
                    cells=[C.usd(r['voted']), C.usd(g), C.usd(o), C.usd(a)])
    views = []
    for s, label in SERIES:
        rs = [r for r in lines_only if r['code'].startswith(s)]
        if rs:
            views.append(dict(key='s' + s, label=label, total_col=3, kinds=['ledger'] * 4,
                              columns=['Voted, general fund', 'General fund spent',
                                       'Other funds spent', 'Every fund'],
                              rows=[lrow(r) for r in sorted(rs, key=lambda r: r['code'])]))
    other = [r for r in line_rows if r['cls'] in ('none', 'heading', 'other')]
    views.append(dict(key='unattributed', label='On no budget line', total_col=3, kinds=['ledger'] * 4,
                      columns=['Voted, general fund', 'General fund spent', 'Other funds spent',
                               'Every fund'],
                      rows=[lrow(r) for r in sorted(other, key=lambda r: r['code'])],
                      note='0000 is no function at all; a heading names a group of lines and no one '
                           'line. Food services (3400) is a real code with no voted line: lunch is '
                           'paid entirely from its own fund.'))
    year_rows = []
    for y in Y:
        part = lambda k: sum(v for (yy, g, c), v in m['exp'].items()
                             if yy == y and g != 'General fund' and m['cls'][c] in k)
        onl, oth = part(('line',)), part(('other',))
        if abs(gfs[y] + onl + m['unattr'][y] + oth - m['all'][y]) > 0.01:
            fail('the year view does not foot in %s' % C.fy(y))
        parts, whole = C.footed([gfs[y], onl, m['unattr'][y], oth])
        year_rows.append(dict(label=C.fy(y), cells=[C.usd(m['gf_voted'][y])]
                              + [C.usd(x) for x in parts] + [C.usd(whole)]))
    views.append(dict(key='years', label='Every year', total_col=5, kinds=['ledger'] * 6,
                      columns=['Voted, general fund', 'General fund spent', 'Other funds, on a line',
                               'Other funds, on no line', 'Other funds, other code', 'Every fund'],
                      rows=year_rows,
                      note='On no line is function 0000 or a heading. Other code is a real code '
                           'with no voted line, mostly food services.'))
    rank = sorted(lines_only, key=lambda r: -r['all'])[:TOP_LINES]
    un_label = 'On no line (0000 and headings)'
    rank_rows = [('%s %s' % (r['code'], r['name'][:38]), [r['gf'], r['out']]) for r in rank]
    rank_rows.append((un_label, [sum(r['gf'] for r in un), un_out]))
    out['budget-lines-all-funds'] = TP.page(
        'budget-lines-all-funds',
        'In %s other funds spent %s beside the general fund; %s of it sat on no budget line.'
        % (C.fy(y1), C.usd(out1), C.usd(un_out)),
        list(lx.values()),
        [con('The general fund was voted %s for %s and spent %s; all funds together, %s.'
             % (C.usd(m['gf_voted'][y1]), C.fy(y1), C.usd(gfs[y1]), C.usd(all1)),
             ['voted', 'gf', 'all'],
             {'a': U(m['gf_voted'][y1]), 'y': F(y1), 'b': U(gfs[y1]), 'c': U(all1)},
             notes=[step('Spent includes what was still owed when the report was run: %s, every '
                         'fund.' % C.usd(owed1), 'measured', {'w': U(owed1)}),
                    step(open_note + ' These are postings to school accounts, not what the '
                         'schools cost in full.', 'gap', {'y': F(F1)}, closes=BENEFITS_CLOSES)]),
         con('Other funds spent on %s of the %s voted lines; %s landed on one.'
             % (C.num(n_lines_out), C.num(n_lines), C.usd(out_on_lines)),
             ['nlines', 'nout', 'onlines'],
             {'a': N(n_lines_out, 'lines'), 'b': N(n_lines, 'lines'), 'c': U(out_on_lines)},
             notes=[step('The largest was %s %s: %s from other funds.'
                         % (big['code'], big['name'], C.usd(big['out'])), 'gap',
                         {'a': U(big['out'])}, allow=(big['code'],),
                         closes='the fund-by-fund budget for each line, as the district builds it')]),
         con('%s of other-fund spending had no line: function 0000 or a heading.' % C.usd(un_out),
             ['unattr', 'why'], {'a': U(un_out)}, allow=('0000',),
             notes=[step('It is shown as its own row and not spread across lines: the ledger '
                         'does not say which line it served.', 'gap',
                         closes='the district’s grant budgets and DESE final expenditure reports, '
                                'by function code')])],
        chart=TP.ranking('Largest budget lines, every fund', rank_rows, '$', highlight=un_label,
                         stack=['General fund', 'Other funds'],
                         note='%s spending by function code. The highlighted row is spending on '
                              'no line. %s' % (C.fy(y1), spent_note),
                         note_figures={'y': F(y1)}),
        table=dict(caption='Every budget line, %s: voted, and spent from every fund' % C.fy(y1),
                   views=views),
        sources=sources(),
        finding_figures={'y': F(y1), 'a': U(out1), 'b': U(un_out)})
    out['budget-lines-all-funds']['not_established'] = [
        'Which line spending booked to 0000 or a heading served.',
        'How the district decides which fund pays for which part of a line.',
        'The FY2026 figures after the close.',
    ]

    # ================================================== grant-coding (H2)
    idea_funds, idea = idea_years(m, gc)
    share = lambda d: 100.0 * d.get('line', 0.0) / sum(d.values()) if sum(d.values()) else None
    gtot = {y: defaultdict(float) for y in Y}
    for (fnd, y), d in gc.items():
        for k, v in d.items():
            gtot[y][k] += v
    g_line = {y: share(gtot[y]) for y in Y}
    i_line = {y: share(idea[y]) for y in Y}
    i_none = {y: idea[y].get('none', 0.0) for y in Y}
    # THE IDEA GRANT, ONE GRANT AT A TIME (#240, named for its fiscal year): how each was booked
    # over its whole life in the run. A grant is set up once, so the coding is a property of the
    # grant, not of the year its money was spent.
    ig = {}
    for fnd in idea_funds:
        gy = grant_year(m['fund_name'][fnd])
        d = defaultdict(float)
        codes = set()
        for (y, ff, c), v in m['by_fund_code'].items():
            if ff == fnd:
                d[m['cls'][c]] += v
                if abs(v) >= 0.5:
                    codes.add(c)
        t = sum(d.values())
        if gy and abs(t) >= 0.5:
            ig[gy] = dict(fund=fnd, total=t, codes=sorted(codes), **{k: d.get(k, 0.0) for k in J.FUNCTION_CLASSES})
    old = [gy for gy in sorted(ig) if gy < 2025]
    new = [gy for gy in sorted(ig) if gy >= 2025]
    if not old or not new or any(abs(ig[gy]['line']) >= 0.5 for gy in old):
        fail('the IDEA conclusion assumes the earlier grants put nothing on a voted line')
    old_codes = sorted({c for gy in old for c in ig[gy]['codes']})
    g25, g26 = ig.get(2025), ig.get(2026)
    if not (g25 and g26 and g25['none'] > g25['total'] / 2):
        fail('the IDEA conclusion assumes the FY2025 grant is mostly on 0000')
    gx = {}
    for y in Y:
        gx['g%d' % y] = f('g%d' % y, P(g_line[y]), 'grant spending on a voted line, %s' % C.fy(y),
                          'published', {'y': F(y)})
    for gy in old:
        gx['i%d' % gy] = f('i%d' % gy, U(ig[gy]['heading']), '%s IDEA grant, on headings' % C.fy(gy),
                           'published', {'y': F(gy)})
    gx['n25'] = f('n25', U(g25['none']), '%s IDEA grant, no function code' % C.fy(2025), 'published',
                  {'y': F(2025)})
    gx['t25'] = f('t25', U(g25['total']), '%s IDEA grant, spent in all' % C.fy(2025), 'published',
                  {'y': F(2025)})
    gx['h26'] = f('h26', U(g26['heading']), '%s IDEA grant, on heading 2000' % C.fy(2026), 'published',
                  {'y': F(2026)}, allow=('2000',))
    gx['why'] = f('why', None, 'why the coding changed', 'gap',
                  closes='the business office’s account set-up for each grant')
    gt = {y: sum(gtot[y].values()) for y in Y}
    gunat = {y: gtot[y].get('none', 0.0) + gtot[y].get('heading', 0.0) for y in Y}
    stack_rows = [TP.track(lab, [gtot[y].get(k, 0.0) for y in Y], 'published')
                  for k, lab in (('line', 'On a voted line'), ('heading', 'On a heading'),
                                 ('none', 'No function code'), ('other', 'Other code'))
                  if any(abs(gtot[y].get(k, 0.0)) >= 0.5 for y in Y)]
    gr_rows = []
    for (fnd, y), d in sorted(gc.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        t = sum(d.values())
        if abs(t) < 10000:
            continue
        gr_rows.append(dict(label='%s %s, %s' % (fnd, m['fund_name'][fnd].strip(), C.fy(y)),
                            cells=[C.usd(t), C.usd(d.get('line', 0.0)), C.usd(d.get('heading', 0.0)),
                                   C.usd(d.get('none', 0.0))]))
    i_rows = [dict(label='%s grant (fund %s)' % (C.fy(gy), ig[gy]['fund']),
                   cells=[C.usd(ig[gy]['total']), C.usd(ig[gy]['line']), C.usd(ig[gy]['heading']),
                          C.usd(ig[gy]['none']), ', '.join(ig[gy]['codes'])]) for gy in sorted(ig)]
    oldspan = '%s to %s' % (C.fy(old[0]), C.fy(old[-1]))
    out['grant-coding'] = TP.page(
        'grant-coding',
        'Grant spending on a voted budget line went from %s in %s to %s in %s.'
        % (C.pct(g_line[F0]), C.fy(F0), C.pct(g_line[F1]), C.fy(F1)),
        list(gx.values()),
        [con('The IDEA grants for %s were booked to headings, never to a voted line.' % oldspan,
             ['i%d' % gy for gy in old], {'y': F(old[0]), 'z': F(old[-1])},
             notes=[step('Their codes were %s: teaching and instructional materials, but no '
                         'single line.' % ', '.join(old_codes), 'gap', allow=tuple(old_codes),
                         closes='the IDEA grant budgets the district filed with DESE, by function code')]),
         con('The %s grant put %s of its %s on no function code at all.'
             % (C.fy(2025), C.usd(g25['none']), C.usd(g25['total'])), ['n25', 't25', 'h26'],
             {'y': F(2025), 'a': U(g25['none']), 'b': U(g25['total'])},
             notes=[step('The %s grant went to the heading 2000, instruction: %s.'
                         % (C.fy(2026), C.usd(g26['heading'])), 'gap',
                         {'y': F(2026), 'a': U(g26['heading'])}, allow=('2000',),
                         closes='the business office’s account set-up for each grant'),
                    step('Why it changed is not in the ledger. A new account set-up, a new '
                         'person, or a choice to code at the grant level all fit.', 'hypothesis')]),
         con('Across every grant, %s of %s spent in %s was on no line.'
             % (C.usd(gunat[F1]), C.usd(gt[F1]), C.fy(F1)),
             ['g%d' % F1, 'why'], {'a': U(gunat[F1]), 'b': U(gt[F1]), 'y': F(F1)},
             notes=[step('The district’s End of Year report to the state puts its grant spending '
                         'on function codes; this ledger mostly does not.', 'gap',
                         closes='the district’s End of Year Financial Report working papers, '
                                'grant columns by function')])],
        chart=TP.series('Grant spending by how it is coded', years, stack_rows, '$', kind='bar',
                        stacked=True,
                        note='Spending in grant funds; a voted line is a code the general fund '
                             'budget is voted on (ours). %s' % spent_note,
                        note_figures={'y': F(F1)}),
        table=dict(caption='How grant spending is coded', views=[
            dict(key='idea', label='IDEA grant (#240), grant by grant', total_col=0,
                 kinds=['ledger'] * 5,
                 columns=['Spent', 'On a voted line', 'On a heading', 'No code', 'Codes used'],
                 rows=i_rows,
                 note='Every IDEA entitlement grant with spending in the run, over its whole life.'),
            dict(key='grants', label='Every grant over $10,000, by year', total_col=0,
                 kinds=['ledger'] * 4, columns=['Spent', 'On a voted line', 'On a heading', 'No code'],
                 rows=gr_rows[:30],
                 note='Fund number and the Town’s name for it, cut at thirty characters by the report.')]),
        sources=sources(),
        finding_figures={'a': P(g_line[F0]), 'y': F(F0), 'b': P(g_line[F1]), 'z': F(F1)})
    out['grant-coding']['not_established'] = [
        'Why the IDEA grant moved from headings to no code in FY2025.',
        'Which line any grant dollar on 0000 or a heading served.',
        'Whether the district budgets a grant to lines anywhere outside the ledger.',
    ]

    # ================================================== school-money-in
    rin = m['receipts']
    rin_tot = {y: sum(rin[(y, g)] for g in OUTSIDE) for y in Y}
    grant_rec = {y: rin[(y, 'Grants')] for y in Y}
    # Grant receipts by program (DESE code), four years.
    A = J.accounts()
    # GRANTS BY NAME (TJ, 26 October 2026: "breakdown the grants by the name"). Each grant fund's
    # spending, under journal.grant_program's name; award years of one program add together. The
    # years must add to the Grants bar the hub and this page draw.
    rep = {}
    for a in A.values():
        rep.setdefault(a['fund'], a)
    gname = defaultdict(float)
    for (y, fnd), v in m['fund_spent'].items():
        if y in Y and J.fund_group(rep[fnd]) == 'Grants':
            gname[(y, J.grant_program(rep[fnd]))] += v
    for y in Y:
        if abs(sum(v for (yy, _), v in gname.items() if yy == y) - sp[(y, 'Grants')]) > 0.01:
            fail('%s: the grants by name do not add to the Grants spending' % C.fy(y))
    if not (all(round(gname.get((F1, J.GRANT_PROGRAM[c]), 0.0)) == 0 for c in ('115', '119'))
            and max((v, nm) for (y, nm), v in gname.items() if y == F1)[1] == J.GRANT_PROGRAM['240']):
        fail('the hub says the pandemic grants paid nothing in %s and IDEA is the largest grant' % F1)
    g4 = defaultdict(float)
    for (y, nm), v in gname.items():
        g4[nm] += v
    gnames = [nm for nm in sorted(g4, key=lambda k: -g4[k]) if round(g4[nm])]
    prog = defaultdict(float)
    for (y, fnd), v in m['fund_rec'].items():
        a = next(x for x in A.values() if x['fund'] == fnd)
        if J.fund_group(a) == 'Grants':
            prog[J.grant_code(a['fund_name']) or 'none'] += v
    # The codes the table names, under journal.GRANT_PROGRAM's names, as every page names them.
    PROG = {k: '%s (#%s)' % (J.GRANT_PROGRAM[k], k)
            for k in ('240', '305', '119', '115', '117', '237', '140', '309', '252', '262')}
    prog_rows = [dict(label=PROG.get(k, 'Other grants'), cells=[C.usd(v)])
                 for k, v in sorted(prog.items(), key=lambda kv: -kv[1]) if k in PROG]
    prog_rows.append(dict(label='Other grants', cells=[C.usd(sum(v for k, v in prog.items() if k not in PROG))]))
    mx = {}
    mx['gfv'] = f('gfv', U(m['gf_voted'][F1]), 'general fund, voted, %s' % C.fy(F1), 'published', {'y': F(F1)})
    mx['ch70'] = f('ch70', U(m['ch70'][F1]), 'Chapter 70 aid to the town, %s' % C.fy(F1), 'published', {'y': F(F1)},
                  allow=('70',))
    mx['r0'] = f('r0', U(rin_tot[LAST_CLOSED]), 'received by every other fund, %s' % C.fy(LAST_CLOSED),
                 'published', {'y': F(LAST_CLOSED)})
    mx['rev'] = f('rev', U(rin[(LAST_CLOSED, 'Revolving funds and lunch')]),
                  'fees, lunch and gifts, %s' % C.fy(LAST_CLOSED), 'published', {'y': F(LAST_CLOSED)})
    mx['cb'] = f('cb', U(rin[(LAST_CLOSED, 'Circuit breaker')]), 'circuit breaker, %s' % C.fy(LAST_CLOSED),
                 'published', {'y': F(LAST_CLOSED)})
    mx['gr'] = f('gr', U(grant_rec[LAST_CLOSED]), 'grants, %s' % C.fy(LAST_CLOSED), 'published', {'y': F(LAST_CLOSED)})
    mx['gr1'] = f('gr1', U(grant_rec[F1]), 'grants received so far, %s' % C.fy(F1), 'published', {'y': F(F1)})
    mx['cap'] = f('cap', None, 'capital money voted to the schools', 'gap',
                  closes='the Town Meeting capital articles, FY2023–FY2026, by school account')
    ch_share = 100.0 * m['ch70'][F1] / m['gf_voted'][F1]
    # GENERAL AID AND GRANTS, side by side (TJ, 26 October 2026, after sped-grants: "we need a
    # similar page for ALL grants ... we may have the page already? but need this same info
    # there too"). Chapter 70 is GENERAL aid, paid into the town's general fund toward the
    # school budget; every grant is CATEGORICAL, restricted to its purpose. Never one total.
    # Three stages, never subtracted (rule 1): Chapter 70 as DESE set it, grant ALLOCATIONS as
    # DESE announced them, grant SPENDING as the ledger shows it.
    ma = json.load(open(MIN_AID_JSON, encoding='utf-8'))
    c70 = {r['fy']: float(r['aid']) for r in ma['series']}
    for y in Y:
        if abs(c70[y] - m['ch70'][y]) > 0.5:
            fail('school-money-in: Chapter 70 %s is %.0f in DESE’s calculation and %.0f on the '
                 'cherry sheet; the page draws one as the other' % (y, c70[y], m['ch70'][y]))
    c70y = sorted(c70)
    if c70y != list(range(c70y[0], c70y[-1] + 1)) or c70y[-1] != F1:
        fail('school-money-in: DESE’s Chapter 70 series is not continuous to %s' % F1)
    ch_next = {int(r['fy']): float(r['amount']) for r in csv.DictReader(open(CHERRY_CSV, encoding='utf-8'))
               if r['name'] == 'Lunenburg' and r['line'] == 'Chapter 70' and r['flow'] == 'Receipts'}
    if F1 + 1 not in ch_next:
        fail('school-money-in: the cherry sheet has no Chapter 70 for %s' % (F1 + 1))
    last = ma['series'][-1]
    floor = sorted(ma['on_floor'])
    if not (last['fy'] == F1 and F1 in floor and abs(last['change'] - last['minimum_aid']) < 0.5):
        fail('school-money-in: the Chapter 70 meaning says %s’s rise was the minimum aid alone' % F1)
    # Allocations: every code DESE lists for Lunenburg. A year is HELD when DESE's district page
    # for it lists any grant (extract_dese_entitlements reconciles that page to its own total),
    # so a code missing from a held year was not allocated that year -- not merely unread.
    alloc_all = read_allocations(None)
    held = sorted({y for (_, y) in alloc_all})
    if held != list(range(held[0], held[-1] + 1)):
        fail('school-money-in: DESE allocation years held are not continuous: %s' % held)
    # The yearly federal grants: allocated in every year held from FORMULA0 on.
    YEARLY = ('240', '305', '140', '309', '262')
    PANDEMIC = ('113', '115', '119', '252', '264', '302')
    FORMULA0 = 2019
    if any((k, y) not in alloc_all for k in YEARLY for y in held if y >= FORMULA0):
        fail('school-money-in: a yearly grant has no allocation in a held year from %s' % FORMULA0)
    if FORMULA0 - 1 in held and all((k, FORMULA0 - 1) in alloc_all for k in YEARLY):
        fail('school-money-in: all five yearly grants start before %s now' % FORMULA0)
    pan_al = {y: sum(alloc_all.get((k, y), 0.0) for k in PANDEMIC) for y in held}
    pan_years = [y for y in held if pan_al[y]]
    other = sorted({k for (k, _) in alloc_all} - set(YEARLY) - set(PANDEMIC))
    if any(sum(1 for (k2, _) in alloc_all if k2 == k) > 1 for k in other):
        fail('school-money-in: a grant with several years of allocations is not drawn: %s' % other)
    fg = {y: sum(alloc_all[(k, y)] for k in YEARLY) for y in held if y >= FORMULA0}
    fg_pc = pc(fg[FORMULA0], fg[F1])
    c70_pc = pc(c70[FORMULA0], c70[F1])
    if not (c70_pc > 0 > fg_pc):
        fail('school-money-in: the conclusion says Chapter 70 rose and the yearly grants fell')
    dese_name = {}
    for r in csv.DictReader(open(ALLOC_CSV, encoding='utf-8')):
        if r['district_code'] == '0162':
            dese_name[r['fund_code'].lstrip('0')] = r['grant_name']
    gnm = lambda k: J.GRANT_PROGRAM.get(k, dese_name[k])
    # Grant SPENDING by name (gname, above): the four largest streams, ESSER's two together.
    ESSER = [J.GRANT_PROGRAM['115'], J.GRANT_PROGRAM['119']]
    esser = {y: sum(gname.get((y, nm), 0.0) for nm in ESSER) for y in Y}
    if not (esser[F0] > 0 and abs(esser[F1]) < 0.005):
        fail('school-money-in: ESSER is said to have paid in %s and nothing in %s' % (F0, F1))
    esser_last = max(y for y in Y if round(esser[y]))
    big = [nm for nm in gnames if nm not in ESSER][:3]
    comp = [('ESSER II and III, ended', ESSER)] + [(nm, [nm]) for nm in big]
    named = {nm for _, ns in comp for nm in ns}
    comp_tracks = [TP.track(lab, [sum(gname.get((y, nm), 0.0) for nm in ns) for y in Y], 'published', 'bar')
                   for lab, ns in comp]
    comp_tracks.append(TP.track('Other grants', [sum(v for (yy, nm), v in gname.items()
                                                     if yy == y and nm not in named) for y in Y],
                                'published', 'bar'))
    for i, y in enumerate(Y):
        if abs(sum(t['values'][i] for t in comp_tracks) - sp[(y, 'Grants')]) > 0.01:
            fail('school-money-in: the grant bands do not add to grant spending in %s' % y)
    if not rin[(LAST_CLOSED, 'Revolving funds and lunch')] > grant_rec[LAST_CLOSED]:
        fail('school-money-in: the meaning says fees and lunch brought in more than grants')
    drop = sp[(F0, 'Grants')] - sp[(F1, 'Grants')]
    if not (drop > 0 and esser[F0] > drop / 2):
        fail('school-money-in: the conclusion says ESSER was most of the fall in grant spending')
    mx['fg0'] = f('fg0', U(fg[FORMULA0]), 'yearly federal grants allocated, %s' % C.fy(FORMULA0), 'published',
                  {'y': F(FORMULA0)})
    mx['fg1'] = f('fg1', U(fg[F1]), 'yearly federal grants allocated, %s' % C.fy(F1), 'published', {'y': F(F1)})
    mx['gs0'] = f('gs0', U(sp[(F0, 'Grants')]), 'every grant, spent, %s' % C.fy(F0), 'published', {'y': F(F0)})
    mx['gs1'] = f('gs1', U(sp[(F1, 'Grants')]), 'every grant, spent or owed, %s' % C.fy(F1), 'published',
                  {'y': F(F1)})
    # ---- the blocks: what each kind of money is, then each one's trend
    floor_txt = ', '.join(C.fy(y) for y in floor)
    floor_figs = {'f%d' % i: F(y) for i, y in enumerate(floor)}
    explain = TB.explain('General aid and grants', [
        ('**Chapter 70 is general aid.** The state pays it into the town’s general fund toward the '
         'school budget, and it may be spent on anything that budget covers. Lunenburg was held at '
         'the formula’s minimum-aid floor in %s.' % floor_txt, floor_figs, ('70',)),
        '**Every grant is categorical.** It may be spent only on the purpose it was given for, and '
        'most are paid after the money is spent. So the two are shown side by side here, never '
        'added into one total.',
        '**Allocated is not spent.** An allocation is what DESE says the district may draw; spending '
        'is what the ledger shows. Different stages, never subtracted.',
    ], place='chart', tone='define')
    t_c70 = trend_chart(
        'General state aid, set each year', c70y, 'Chapter 70 aid, as DESE set it', [c70[y] for y in c70y],
        F1 + 1, ch_next[F1 + 1], 'Cherry sheet (state)', 'published', statistics.mean(c70.values()),
        'Average, %s to %s' % (C.fy(c70y[0]), C.fy(c70y[-1])),
        ('DESE’s Chapter 70 calculation by fiscal year; %s is the state’s cherry sheet.' % C.fy(F1 + 1),
         {'y': F(F1 + 1)}),
        ('%s rose %s, the formula’s minimum aid alone. Every grant together spent %s in %s: '
         'restricted money beside this general aid.'
         % (C.fy(F1), C.usd(last['change']), C.usd(sp[(LAST_CLOSED, 'Grants')]), C.fy(LAST_CLOSED)),
         {'y': F(F1), 'a': U(last['change']), 'b': U(sp[(LAST_CLOSED, 'Grants')]), 'z': F(LAST_CLOSED)}),
        note_allow=('70',))
    t_comp = TB.chart(TP.series('Grant spending, by grant', years, comp_tracks, '$', kind='bar',
                                stacked=True, totals=True,
                                note='Spent or still owed at the close, every award year of a grant '
                                     'together. %s' % open_note, note_figures={'y': F(F1)}),
                      place='chart',
                      so=('ESSER paid %s in %s and nothing after %s; whatever it paid for is now paid '
                          'from another fund or not at all, and the ledger cannot say which.'
                          % (C.usd(esser[F0]), C.fy(F0), C.fy(esser_last)),
                          {'a': U(esser[F0]), 'y': F(F0), 'z': F(esser_last)}))
    t_alloc = [alloc_trend_chart(alloc_all, k, gnm(k), 'school-money-in') for k in YEARLY]
    t_pan = trend_chart(
        'Pandemic relief grants, allocated', held, 'Pandemic relief, allocated',
        [pan_al[y] for y in held], None, None, None, None, None, None,
        ('ESSER I, II and III and three American Rescue Plan grants, by award year. Ended: no '
         'next year.', None),
        ('Allocated only in %s, %s in all, and nothing in any year since: the one grant stream '
         'here that has ended.' % (' and '.join(C.fy(y) for y in pan_years), C.usd(sum(pan_al.values()))),
         dict({'p%d' % i: F(y) for i, y in enumerate(pan_years)}, a=U(sum(pan_al.values())))))
    al_years = [y for y in held if y >= min(pan_years)]
    al_rows = [dict(label='%s (#%s)' % (gnm(k), k),
                    cells=[C.usd(alloc_all[(k, y)]) if (k, y) in alloc_all else '' for y in al_years])
               for k in sorted({k for (k, y) in alloc_all if y in al_years},
                               key=lambda k: -sum(alloc_all.get((k, y), 0.0) for y in al_years))]
    out['school-money-in'] = TP.page(
        'school-money-in',
        'In %s Chapter 70 aid was %s and every grant spent %s: general aid beside restricted money.'
        % (C.fy(LAST_CLOSED), C.usd(c70[LAST_CLOSED]), C.usd(sp[(LAST_CLOSED, 'Grants')])),
        list(mx.values()),
        [con('The general fund was voted %s for %s; Chapter 70 aid to the town was %s of that.'
             % (C.usd(m['gf_voted'][F1]), C.fy(F1), C.pct(ch_share)),
             ['gfv', 'ch70'], {'a': U(m['gf_voted'][F1]), 'y': F(F1), 'p': P(ch_share)}, allow=('70',),
             so='This part of the vote rests on a state formula the town does not set, and '
                'Lunenburg is held at its floor.',
             notes=[step('Chapter 70 is paid to the town, not to a school account, so it is shown '
                         'beside the vote, never added to it.', 'gap', allow=('70',),
                         closes='the town’s revenue ledger for the school appropriation, by source')]),
         con('In %s other funds took in %s: %s from fees, lunch and gifts, %s from grants.'
             % (C.fy(LAST_CLOSED), C.usd(rin_tot[LAST_CLOSED]),
                C.usd(rin[(LAST_CLOSED, 'Revolving funds and lunch')]), C.usd(grant_rec[LAST_CLOSED])),
             ['r0', 'rev', 'gr', 'cb', 'gr1'],
             {'y': F(LAST_CLOSED), 'a': U(rin_tot[LAST_CLOSED]),
              'b': U(rin[(LAST_CLOSED, 'Revolving funds and lunch')]), 'c': U(grant_rec[LAST_CLOSED])},
             so='Fees and lunch bring in more than grants do, and each fund may be spent only on '
                'what it was collected for.',
             notes=[step('%s grants had received %s when the report was run. Most grants are paid '
                         'after the money is spent, so an open year looks short.'
                         % (C.fy(F1), C.usd(grant_rec[F1])), 'gap', {'y': F(F1), 'a': U(grant_rec[F1])},
                         closes='the DESE grant payment history (GEM$) for each school grant')]),
         con('%s to %s, Chapter 70 rose %s; the five yearly federal grants’ allocations fell %s.'
             % (C.fy(FORMULA0), C.fy(F1), C.pct(c70_pc), C.pct(-fg_pc)), ['ch70', 'fg0', 'fg1'],
             {'y': F(FORMULA0), 'z': F(F1), 'a': P(c70_pc), 'b': P(-fg_pc)}, allow=('70',),
             so='The outside money that grew is general aid already inside the vote; the restricted '
                'grants did not grow.',
             notes=[step('Both are amounts the state and DESE set, not receipts or spending, and '
                         'neither is adjusted for prices. The five are IDEA, its preschool grant, '
                         'Title I, Title IIA and Title IV.', 'measured')]),
         con('Grant spending fell from %s in %s to %s in %s; %s of the fall was ESSER ending.'
             % (C.usd(sp[(F0, 'Grants')]), C.fy(F0), C.usd(sp[(F1, 'Grants')]), C.fy(F1), C.usd(esser[F0])),
             ['gs0', 'gs1'],
             {'a': U(sp[(F0, 'Grants')]), 'y': F(F0), 'b': U(sp[(F1, 'Grants')]), 'z': F(F1),
              'c': U(esser[F0])},
             so='The pandemic money has run out; what it paid for is now paid from another fund or '
                'not at all.',
             notes=[step(open_note + ' Spent includes what was still owed at the close.', 'gap',
                         {'y': F(F1)},
                         closes='the Town’s journal report for %s, run after the year is closed' % C.fy(F1))])],
        chart=TP.series('Money in outside the general fund', years, [
            TP.track(g, [rin[(y, g)] for y in Y], 'published') for g in OUTSIDE
            if any(abs(rin[(y, g)]) >= 0.5 for y in Y)], '$', kind='bar', stacked=True,
            note='Receipts posted to school revenue accounts. Capital money is voted by Town '
                 'Meeting and arrives as budget, not receipts. %s' % open_note,
            note_figures={'y': F(F1)}),
        blocks=[explain, t_c70, t_comp] + t_alloc + [t_pan],
        table=dict(caption='Money in, by source', views=[
            dict(key='years', label='By year', total_col=None, kinds=['ledger'] * 5,
                 columns=['Voted, general fund', 'Chapter 70 (beside)', 'Fees, lunch, gifts',
                          'Circuit breaker', 'Grants'],
                 rows=[dict(label=C.fy(y), cells=[C.usd(m['gf_voted'][y]), C.usd(m['ch70'][y]),
                                                  C.usd(rin[(y, 'Revolving funds and lunch')]),
                                                  C.usd(rin[(y, 'Circuit breaker')]),
                                                  C.usd(grant_rec[y])]) for y in Y],
                 note='Chapter 70 is the town’s aid, from the state’s cherry sheet; it pays part of '
                      'the voted budget and is not added to it.'),
            dict(key='grants', label='Grants by program, four years', total_col=None, kinds=['ledger'],
                 columns=['Received'], rows=prog_rows,
                 note='By the DESE grant number in the fund’s name.'),
            dict(key='alloc', label='Grants allocated by DESE', total_col=None,
                 kinds=['published'] * len(al_years), columns=[C.fy(y) for y in al_years], rows=al_rows,
                 note='DESE’s entitlement allocations to Lunenburg by award year. Blank: DESE allocated '
                      'nothing that year. Allocated is not spent.')]),
        sources=sources() + [dict(label='Massachusetts DLS — cherry sheet receipts, Chapter 70 '
                                        '(dls-cherry-sheet.csv)', href='/docs/data/dls-cherry-sheet.csv'),
                             dict(label='Massachusetts DESE — Chapter 70 key factors, every year '
                                        '(dese-ch70-key-factors.xlsx)', href=ma['source']['docs_url']),
                             dict(label='Massachusetts DESE — entitlement grant allocations, by district and fund '
                                        'code (dese-entitlement-allocations.csv)',
                                  href='/docs/data/dese-entitlement-allocations.csv')],
        finding_figures={'y': F(LAST_CLOSED), 'a': U(c70[LAST_CLOSED]), 'b': U(sp[(LAST_CLOSED, 'Grants')])},
        finding_allow=('70',))
    out['school-money-in']['not_established'] = [
        'What each grant was awarded by the state, against what the ledger loaded as its budget.',
        'Capital articles voted to the schools: they arrive as budget, not as receipts.',
        'What ESSER paid for after it ended: another fund, or nothing.',
    ]
    money_in = dict(
        chapter70_dese={str(y): c70[y] for y in c70y}, chapter70_next={str(F1 + 1): ch_next[F1 + 1]},
        yearly_codes=list(YEARLY), pandemic_codes=list(PANDEMIC), formula_from=FORMULA0,
        yearly_allocated={str(y): v for y, v in fg.items()},
        pandemic_allocated={str(y): v for y, v in pan_al.items()},
        grants_spent={str(y): round(sp[(y, 'Grants')], 2) for y in Y},
        esser_spent={str(y): round(esser[y], 2) for y in Y},
        by_grant={str(y): {nm: round(v, 2) for (yy, nm), v in sorted(gname.items()) if yy == y and round(v, 2)}
                  for y in Y})

    # ================================================== outside-the-general-fund
    ogrp = {y: {g: sp[(y, g)] for g in OUTSIDE} for y in Y}
    grant_rows = [dict(label=nm, cells=[C.usd(gname.get((y, nm), 0.0)) if round(gname.get((y, nm), 0.0))
                                        else '' for y in Y] + [C.usd(g4[nm])]) for nm in gnames]
    grant_rows.append(dict(label='All grants', cells=[C.usd(sp[(y, 'Grants')]) for y in Y]
                           + [C.usd(sum(sp[(y, 'Grants')] for y in Y))]))
    grant_view = dict(key='grants', label='Grants, by name', total_col=len(Y),
                      kinds=['ledger'] * (len(Y) + 1), columns=[C.fy(y) for y in Y] + ['Four years'],
                      rows=grant_rows,
                      note='Spent or still owed at the close, every award year of a grant together. '
                           'Named by DESE fund code where the fund carries one, otherwise by the '
                           'fund’s own name.')
    four = {g: sum(ogrp[y][g] for y in Y) for g in OUTSIDE}
    out4 = sum(four.values())
    share_out = {y: 100.0 * m['outside'][y] / m['all'][y] for y in Y}
    # fund x code, four years, the largest cells
    fc = defaultdict(float)
    for (y, fnd, c), v in m['by_fund_code'].items():
        fc[(fnd, c)] += v
    fc_rows = [dict(label='%s %s' % (fnd, m['fund_name'][fnd].strip()),
                    cells=['%s %s' % (c, m['names'][c][:30]), C.usd(v)])
               for (fnd, c), v in sorted(fc.items(), key=lambda kv: -kv[1])[:25]]
    pay = sorted(((p, v) for (g, p), v in m['payee'].items()), key=lambda kv: -kv[1])
    pay_tot = defaultdict(float)
    pay_grp = defaultdict(lambda: defaultdict(float))
    for (g, p), v in m['payee'].items():
        pay_tot[p] += v
        pay_grp[p][g] += v
    top = sorted(pay_tot, key=lambda p: (-pay_tot[p], p))[:TOP_PAYEES]
    pay_rows = [dict(label=p, cells=[C.usd(pay_grp[p].get(g, 0.0)) for g in OUTSIDE])
                for p in top]
    lead = top[0]
    ox = {}
    ox['o0'] = f('o0', U(m['outside'][F0]), 'spent outside the general fund, %s' % C.fy(F0), 'published', {'y': F(F0)})
    ox['o1'] = f('o1', U(m['outside'][F1]), 'spent outside the general fund, %s' % C.fy(F1), 'published', {'y': F(F1)})
    ox['s0'] = f('s0', P(share_out[F0]), 'of all school spending, %s' % C.fy(F0), 'published', {'y': F(F0)})
    ox['s1'] = f('s1', P(share_out[F1]), 'of all school spending, %s' % C.fy(F1), 'published', {'y': F(F1)})
    ox['four'] = f('four', U(out4), 'outside the general fund, four years', 'published')
    for g, k in (('Revolving funds and lunch', 'rv'), ('Grants', 'gr'), ('Circuit breaker', 'cb'),
                 ('Capital and other', 'cp')):
        ox[k] = f(k, U(four[g]), '%s, four years' % g.lower(), 'published')
    ox['lead'] = f('lead', U(pay_tot[lead]), 'largest payee, %s, four years' % lead[:20], 'published',
                   allow=tuple(re.findall(r'\d+', lead[:20])))
    out['outside-the-general-fund'] = TP.page(
        'outside-the-general-fund',
        'Funds outside the voted budget spent %s in four years: %s of school spending in %s.'
        % (C.usd(out4), C.pct(share_out[F1]), C.fy(F1)),
        list(ox.values()),
        [con('Spending outside the general fund was %s in %s and %s in %s.'
             % (C.usd(m['outside'][F0]), C.fy(F0), C.usd(m['outside'][F1]), C.fy(F1)),
             ['o0', 'o1', 's0', 's1'],
             {'a': U(m['outside'][F0]), 'y': F(F0), 'b': U(m['outside'][F1]), 'z': F(F1)},
             notes=[step('Federal pandemic grants (ESSER) ended in %s; capital spending rose after.'
                         % C.fy(F0 + 1), 'gap', {'y': F(F0 + 1)},
                         closes='the district’s ESSER final expenditure reports')]),
         con('Four years: fees and lunch %s, grants %s, the circuit breaker %s.'
             % (C.usd(four['Revolving funds and lunch']), C.usd(four['Grants']),
                C.usd(four['Circuit breaker'])),
             ['rv', 'gr', 'cb', 'cp', 'four'],
             {'a': U(four['Revolving funds and lunch']), 'b': U(four['Grants']),
              'c': U(four['Circuit breaker'])},
             notes=[step('Capital articles and other funds added %s; fees and lunch include gifts.'
                         % C.usd(four['Capital and other']), 'gap', {'a': U(four['Capital and other'])},
                         closes='the Town Meeting capital articles, FY2023–FY2026, by school account',
                         allow=('2023', '2026'))]),
         con('The largest single payee outside the general fund was %s: %s.'
             % (lead, C.usd(pay_tot[lead])), ['lead'], {'a': U(pay_tot[lead])},
             allow=tuple(re.findall(r'\d+', lead)),
             notes=[step('Invoices only. Pay runs and journal entries name no payee, and families '
                         'paid for their own child are not named anywhere here.', 'gap',
                         closes='the accounts-payable detail behind each warrant, by fund')])],
        chart=TP.series('Spending outside the general fund', years, [
            TP.track(g, [ogrp[y][g] for y in Y], 'published') for g in OUTSIDE], '$', kind='bar',
            stacked=True, note='Spending in every school fund but the general fund. %s' % spent_note,
            note_figures={'y': F(F1)}),
        table=dict(caption='What is paid outside the general fund', views=[grant_view,
            dict(key='fundline', label='By fund and line, four years', total_col=None,
                 kinds=['ledger', 'ledger'], columns=['Function code', 'Spent'], rows=fc_rows,
                 note='The twenty-five largest fund-and-line pairs, %s.' % C.fyspan(F0, F1)),
            dict(key='payees', label='Largest named payees, four years', total_col=None,
                 kinds=['ledger'] * len(OUTSIDE), columns=list(OUTSIDE), rows=pay_rows,
                 note='Invoices paid, by fund group. The table stops at the largest payees, so no '
                      'family’s payment can be read off it by subtraction.')]),
        sources=sources(),
        finding_figures={'a': U(out4), 'b': P(share_out[F1]), 'y': F(F1)})
    out['outside-the-general-fund']['not_established'] = [
        'What the schools cost in full: benefits and town-side costs are booked outside these accounts.',
        'Which child or family any masked payment was for; they are never named.',
    ]

    # ================================================== unspent-by-fund
    carry = [r for r in art]
    tied = sum(1 for r in carry if r['ties'])
    int_tied = sum(1 for r in carry if r['ties_with_interest'] and not r['ties'])
    net_tied = sum(1 for r in carry if r['net_ties'] and not r['ties_with_interest'])
    untied = [r for r in carry if not (r['ties_with_interest'] or r['net_ties'])]
    # A BALANCE IS CASH, so the roll-forward takes payments only (fund_cash), not spent: an order
    # still owed at the end of FY2026 has not left the fund, and the town report's balance it
    # starts from is a cash balance too. What those funds still owed is shown beside it (owed4).
    bal = []
    for r in carry:
        fnd = r['fund']
        later = sum(m['fund_rec'].get((y, fnd), 0.0) - m['fund_cash'].get((y, fnd), 0.0) for y in Y[1:])
        bal.append(dict(r, end=r['carried'] + later,
                        rec4=sum(m['fund_rec'].get((y, fnd), 0.0) for y in Y),
                        exp4=sum(m['fund_cash'].get((y, fnd), 0.0) for y in Y),
                        owed=m['fund_spent'].get((F1, fnd), 0.0) - m['fund_cash'].get((F1, fnd), 0.0)))
    bal.sort(key=lambda r: -r['end'])
    start_tot = sum(r['carried'] for r in bal)
    end_tot = sum(r['end'] for r in bal)
    # Ended grants: named for FY2023 or FY2024. Award = the budget the ledger loaded for them.
    ended = []
    for fnd, nm in m['fund_name'].items():
        a = next(x for x in A.values() if x['fund'] == fnd)
        if J.fund_group(a) != 'Grants' or grant_year(nm) not in (F0, F0 + 1):
            continue
        aw = sum(m['fund_bud'].get((y, fnd), 0.0) for y in Y)
        spent = sum(m['fund_spent'].get((y, fnd), 0.0) for y in Y)   # against a budget: spent
        if aw or spent:
            ended.append(dict(fund=fnd, name=nm.strip(), award=aw, spent=spent, left=aw - spent))
    ended.sort(key=lambda r: -r['left'])
    aw_tot = sum(r['award'] for r in ended)
    n_over = sum(1 for r in ended if r['left'] < 0)
    left_tot = sum(r['left'] for r in ended if r['left'] > 0)
    lead_b = bal[0]
    ux = {}
    ux['start'] = f('start', U(start_tot), 'in fees, lunch and the circuit breaker, end of %s' % C.fy(F0),
                    'published', {'y': F(F0)})
    ux['end'] = f('end', U(end_tot), 'the same funds, end of %s, our roll-forward' % C.fy(F1), 'estimate',
                  {'y': F(F1)})
    ux['lead'] = f('lead', U(lead_b['end']), '%s, end of %s' % (lead_b['ar_name'], C.fy(F1)), 'estimate',
                   {'y': F(F1)}, allow=tuple(re.findall(r'\d+', lead_b['ar_name'])))
    ux['tied'] = f('tied', N(tied, 'funds'), 'of %s tie to the town report, %s' % (C.num(len(carry)), C.fy(F0)),
                   'published', {'n': N(len(carry), 'funds'), 'y': F(F0)})
    ux['award'] = f('award', U(aw_tot), 'budget loaded for %s and %s grants' % (C.fy(F0), C.fy(F0 + 1)),
                    'published', {'y': F(F0), 'z': F(F0 + 1)})
    ux['left'] = f('left', U(left_tot), 'of it never spent', 'published')
    ux['lapse'] = f('lapse', None, 'whether unspent grant money carried or lapsed', 'gap',
                    closes='DESE’s final expenditure report and carryover approval for each grant')
    out['unspent-by-fund'] = TP.page(
        'unspent-by-fund',
        'Fees, lunch and the circuit breaker held %s at the end of %s; by our count, %s by %s.'
        % (C.usd(start_tot), C.fy(F0), C.usd(end_tot), C.fy(F1)),
        list(ux.values()),
        [con('These funds keep what they do not spend. %s held the most: %s by our count.'
             % (lead_b['ar_name'], C.usd(lead_b['end'])), ['start', 'end', 'lead'],
             {'a': U(lead_b['end'])}, allow=tuple(re.findall(r'\d+', lead_b['ar_name'])),
             notes=[step('Our roll-forward: the town report’s %s balance, plus every receipt, less '
                         'every payment in the journal since. A balance is cash: %s orders still owed are not taken off.'
                         % (C.fy(F0), C.fy(F1)), 'gap', {'y': F(F0), 'z': F(F1)}, allow=('30 June 2026',),
                         closes='the Town Accountant’s special revenue balances at 30 June 2026')]),
         con('%s of %s funds tie to the town report to the cent for %s, receipts and spending both.'
             % (C.num(tied), C.num(len(carry)), C.fy(F0)),
             ['tied'], {'a': N(tied, 'funds'), 'b': N(len(carry), 'funds'), 'y': F(F0)},
             notes=[step('%s more ties once its interest, booked outside the school department, is '
                         'added; %s ties on the net; %s does not: %s.'
                         % (C.num(int_tied), C.num(net_tied), C.num(len(untied)),
                            ', '.join(r['ar_name'] for r in untied)), 'gap',
                         {'a': N(int_tied, 'funds'), 'b': N(net_tied, 'funds'),
                          'c': N(len(untied), 'funds')},
                         closes='the Town Accountant’s FY2023 detail for each school special revenue fund',
                         allow=('2023',))]),
         con('%s and %s grants were loaded with %s of budget; %s of it was never spent.'
             % (C.fy(F0), C.fy(F0 + 1), C.usd(aw_tot), C.usd(left_tot)), ['award', 'left', 'lapse'],
             {'y': F(F0), 'z': F(F0 + 1), 'a': U(aw_tot), 'b': U(left_tot)},
             notes=[step('Most grants are paid as they are spent, so an unspent award is usually '
                         'money never drawn, not money held.', 'gap',
                         closes='DESE’s final expenditure report and carryover approval for each grant'),
                    step('A loaded budget is not always the award: two FY2026 funds each carry a '
                         'Title I budget, and one has spent nothing.', 'gap', allow=('2026',),
                         closes='DESE’s grant award notices for each school grant')])],
        chart=TP.ranking('Balances that carry, by fund', [(r['ar_name'], r['end']) for r in bal
                                                          if abs(r['end']) >= 1000][:12], '$',
                         basis='estimate', highlight=lead_b['ar_name'],
                         note='Our roll-forward to the end of %s from the town report’s %s balance '
                              'and the journal. %s' % (C.fy(F1), C.fy(F0), open_note),
                         note_figures={'y': F(F1), 'z': F(F0)}),
        table=dict(caption='Unspent money by fund', views=[
            dict(key='carry', label='Funds that carry', total_col=None, kinds=['ledger'] * 4,
                 columns=['End of %s, town report' % C.fy(F0), 'Received, four years', 'Spent, four years',
                          'End of %s, our roll-forward' % C.fy(F1)],
                 rows=[dict(label='%s %s' % (r['fund'], r['ar_name']),
                            cells=[C.usd(r['carried']), C.usd(r['rec4']), C.usd(r['exp4']), C.usd(r['end'])])
                       for r in bal]),
            dict(key='tie', label='Tie to the town report, %s' % C.fy(F0), total_col=None, kinds=['ledger'] * 4,
                 columns=['Received, journal', 'Received, town report', 'Spent, journal', 'Spent, town report'],
                 rows=[dict(label='%s %s' % (r['fund'], r['ar_name']),
                            cells=[C.usd(r['receipts']), C.usd(r['ar_receipts']), C.usd(r['spent']),
                                   C.usd(r['ar_spent'])]) for r in carry]),
            dict(key='grants', label='%s and %s grants' % (C.fy(F0), C.fy(F0 + 1)), total_col=None,
                 kinds=['ledger'] * 3, columns=['Budget loaded', 'Spent', 'Not spent'],
                 rows=[dict(label='%s %s' % (r['fund'], r['name']),
                            cells=[C.usd(r['award']), C.usd(r['spent']), C.usd(r['left'])])
                       for r in ended][:30],
                 note='Not spent adds up each grant’s shortfall; %s spent more than its loaded '
                      'budget and offsets nothing.' % ('%s grants' % C.num(n_over)))]),
        sources=sources() + [dict(label='Town of Lunenburg — FY2023 annual town report, special '
                                        'revenue schedule (special-revenue-read.csv)',
                                  href='/docs/data/special-revenue-read.csv')],
        finding_figures={'a': U(start_tot), 'y': F(F0), 'b': U(end_tot), 'z': F(F1)})
    out['unspent-by-fund']['not_established'] = [
        'The balances at 30 June 2026 as the Town Accountant states them; ours are a roll-forward.',
        'Whether an unspent grant award was carried into the next grant year or simply not drawn.',
    ]

    # ================================================== sped-all-funds (H1)
    s = m['sped']
    gv = {y: s[(y, 'gf', 'original_budget')] for y in Y}
    gr = {y: gv[y] + s[(y, 'gf', 'transfer')] for y in Y}
    # SPENT INCLUDES WHAT WAS STILL OWED AT THE CLOSE (the year-end encumbrance), the basis
    # build_sped_costs.py and /special-education/special-education-overruns use. On actual
    # alone FY2026 reads $17,928 under its vote; with the $79,537 encumbered, $61,609 over --
    # two pages of this site must not say opposite things about one year (22 October 2026).
    ga = {y: s[(y, 'gf', 'actual')] + s[(y, 'gf', 'encumbrance')] for y in Y}
    oa = {y: s[(y, 'out', 'actual')] + s[(y, 'out', 'encumbrance')] for y in Y}
    al = {y: ga[y] + oa[y] for y in Y}
    over = {y: al[y] - gv[y] for y in Y}
    under = {y: gv[y] - ga[y] for y in Y}
    yu = [y for y in Y if under[y] > 0]
    yo = [y for y in Y if under[y] <= 0]
    if len(yo) != 1:
        fail('the H1 conclusion names one year the general fund ran over its vote; %d now do'
             % len(yo))
    y_over = yo[0]
    if not all(over[y] > 0 for y in Y):
        fail('the H1 conclusion assumes every fund together passed the vote every year')
    sf = lambda y, k: s.get((y, 'fund:' + k, 'actual'), 0.0)
    hx = {}
    for y in (F0, F1):
        hx['v%d' % y] = f('v%d' % y, U(gv[y]), 'voted, general fund, %s' % C.fy(y), 'published', {'y': F(y)})
        hx['a%d' % y] = f('a%d' % y, U(al[y]), 'spent, every fund, %s' % C.fy(y), 'published', {'y': F(y)})
    hx['nund'] = f('nund', N(len(yu), 'years'), 'of %s the general fund came in under its vote'
                   % C.num(len(Y)), 'published', {'n': N(len(Y))})
    hx['umax'] = f('umax', U(max(under[y] for y in yu)), 'general fund under its vote, largest year',
                   'published')
    hx['gfo'] = f('gfo', U(-under[y_over]), 'general fund over its vote, %s' % C.fy(y_over),
                  'published', {'y': F(y_over)})
    hx['omin'] = f('omin', U(min(oa.values())), 'paid by other funds, smallest year', 'published')
    hx['omax'] = f('omax', U(max(oa.values())), 'paid by other funds, largest year', 'published')
    osh = {y: 100.0 * oa[y] / al[y] for y in Y}
    if not osh[F1] < osh[F0]:
        fail('the share conclusion assumes other funds paid a smaller share in %d than in %d' % (F1, F0))
    hx['osh0'] = f('osh0', P(osh[F0]), 'paid outside the general fund, %s' % C.fy(F0), 'published', {'y': F(F0)})
    hx['osh1'] = f('osh1', P(osh[F1]), 'paid outside the general fund, %s' % C.fy(F1), 'published', {'y': F(F1)})
    hx['intent'] = f('intent', None, 'whether the vote counted on other funds', 'gap',
                     closes='the district’s budget build for special education, with the grant '
                            'and circuit breaker offsets it assumed')
    # THE TABLE: one year per view. Rows are what the money paid for; columns the general fund's
    # vote, then spending by the fund that paid. Its bottom row must be the by-year figures above.
    comps = [c for c, _, inn, _ in J.COMPONENTS if inn]
    # EACH GRANT BY NAME (TJ, 26 October 2026: "break down the 'other funds spent' into the
    # actual list of funds"). The ledger names a fund by year and DESE code ('FY24 #240'); the
    # name shown is journal.GRANT_PROGRAM's, the one map every page uses, with the code beside it.
    PROGRAM = J.GRANT_PROGRAM
    used = sorted({k[2][5:] for k in s if len(k) == 4 and k[1] == 'spent' and str(k[2]).startswith('code:')
                   and k[0] in Y and s[k]},
                  key=lambda c: -sum(v for k, v in s.items() if len(k) == 4 and k[2] == 'code:' + c))
    if set(used) - set(PROGRAM):
        fail('a special education grant code has no name here: %s' % sorted(set(used) - set(PROGRAM)))
    paid_by = (('General fund spent', ('General fund',)), ('Circuit breaker', ('Circuit breaker',))) + \
        tuple(('%s (#%s)' % (PROGRAM[c], c), ('code:' + c,)) for c in used)

    def sped_year(y):
        sp = lambda c, fns: sum(s.get((y, 'spent', fn, c), 0.0) for fn in fns)
        # Only the grants that paid this year: a column of zeros is width a phone does not have.
        pb = paid_by[:2] + tuple(x for x in paid_by[2:] if any(sp(c, x[1]) for c in comps))
        rows, tot = [], [0.0] * (len(pb) + 2)
        for c in comps:
            v = [s.get((y, 'gf:' + c, 'original_budget'), 0.0)] + [sp(c, fns) for _, fns in pb]
            v.append(sum(v[1:]))
            tot = [t + x for t, x in zip(tot, v)]
            rows.append(dict(label=J.COMPONENT_LABEL[c], cells=[C.usd(x) for x in v]))
        for got, want, what in ((tot[0], gv[y], 'voted'), (tot[1], ga[y], 'general fund spent'),
                                (tot[-1], al[y], 'every fund')):
            if abs(got - want) > 0.005:
                raise SystemExit('sped-all-funds %s: the components\' %s is %.2f, the year\'s is %.2f'
                                 % (y, what, got, want))
        rows.append(dict(label='All of it', cells=[C.usd(x) for x in tot]))
        return dict(key='fy%d' % y, label=C.fy(y), total_col=len(pb) + 1, kinds=['ledger'] * (len(pb) + 2),
                    columns=['Voted, general fund'] + [n for n, _ in pb] + ['Every fund spent'],
                    rows=rows,
                    note='Only the general fund has a vote; the circuit breaker and grants are spent '
                         'without one. Spent includes what was still owed at the close. Each grant is '
                         'named with its DESE fund code. Chapter 70 is not a column: it is '
                         'state aid paid into the general fund, so it is inside general fund spent.'
                         + (' %s is not yet closed.' % C.fy(y) if y == F1 else ''))

    out['sped-all-funds'] = TP.page(
        'sped-all-funds',
        'Special education spending passed its voted budget every year, and other funds paid the '
        'difference.',
        list(hx.values()),
        [con('Every fund spent %s on special education in %s, against %s voted.'
             % (C.usd(al[F1]), C.fy(F1), C.usd(gv[F1])), ['v%d' % F1, 'a%d' % F1, 'v%d' % F0, 'a%d' % F0],
             {'a': U(al[F1]), 'y': F(F1), 'b': U(gv[F1])},
             notes=[step('In %s it was %s against %s. %s' % (C.fy(F0), C.usd(al[F0]), C.usd(gv[F0]), open_note),
                         'gap', {'y': F(F0), 'a': U(al[F0]), 'b': U(gv[F0]), 'z': F(F1)},
                         closes='the Town’s journal report for %s, run after the year is closed' % C.fy(F1))]),
         con('The general fund itself came in under its vote in %s of %s years; %s ran %s over.'
             % (C.num(len(yu)), C.num(len(Y)), C.fy(y_over), C.usd(-under[y_over])),
             ['nund', 'umax', 'gfo'],
             {'a': N(len(yu)), 'n': N(len(Y)), 'y': F(y_over), 'b': U(-under[y_over])},
             notes=[step('Spent includes what was still owed when the year closed, as on the '
                         'overruns page.', 'measured')]),
         con('Other funds paid %s to %s a year on top: the circuit breaker and grants.'
             % (C.usd(min(oa.values())), C.usd(max(oa.values()))), ['omin', 'omax', 'intent'],
             {'a': U(min(oa.values())), 'b': U(max(oa.values()))},
             notes=[step('So outside money paid for more than the general fund budgeted, in every '
                         'year. Whether the vote was set expecting it to is not in a ledger.',
                         'hypothesis'),
                    step('Special education here is the accounts the ledger labels so; work paid '
                         'from other accounts is not counted.', 'gap',
                         closes='the district’s End of Year Financial Report, special education '
                                'program, all funds')]),
         con('Other funds paid %s of it in %s and %s in %s.'
             % (C.pct(osh[F0]), C.fy(F0), C.pct(osh[F1]), C.fy(F1)), ['osh0', 'osh1'],
             {'a': P(osh[F0]), 'y': F(F0), 'b': P(osh[F1]), 'z': F(F1)},
             notes=[step('Why less came from other funds is not in a ledger: a smaller '
                         'reimbursement, a balance held back, or costs moved are all possible.',
                         'hypothesis')])],
        chart=TP.series('Special education budget and spending', years, [
            TP.track('General fund spent', [ga[y] for y in Y], 'published', 'bar'),
            TP.track('Other funds spent', [oa[y] for y in Y], 'published', 'bar'),
            TP.track('Voted, general fund', [gv[y] for y in Y], 'published', 'line')], '$',
            kind='bar', stacked=True,
            note='Bars are spending, stacked by fund; the line is the general fund budget voted for '
                 'the same accounts. %s' % open_note, note_figures={'y': F(F1)}),
        table=dict(caption='Special education: what was voted, what was spent, and which fund paid',
                   views=[sped_year(y) for y in reversed(Y)]),
        sources=sources())
    out['sped-all-funds']['not_established'] = [
        'Whether the special education vote was set expecting the circuit breaker and grants to pay '
        'the rest.',
        'What special education costs in full, including benefits and work on unlabelled accounts.',
    ]

    # ================================================== sped-grants
    # EVERY SPECIAL EDUCATION STREAM OUTSIDE THE VOTE, BY NAME (TJ, 26 October 2026: "we ALSO
    # need a general 'special education grants' page that does it all"). Spending is the same
    # `sped` accumulation as sped-all-funds above (spent or still owed at the close), so the two
    # pages cannot disagree: the streams must add to that page's "other funds" every year.
    # Allocations are DESE's (read_allocations); they are a budget-side figure and are shown
    # beside spending, never subtracted from it (rule 1).
    SG = [c for c in SG_CODES]
    sg_name = {c: PROGRAM[c] for c in SG}
    sg_name['CB'] = 'Circuit breaker'
    sg_keys = ['CB'] + SG
    sg_fn = lambda k: 'Circuit breaker' if k == 'CB' else 'code:' + k
    sg_c = lambda y, k, c: s.get((y, 'spent', sg_fn(k), c), 0.0)
    sg_y = {(y, k): sum(sg_c(y, k, c) for c in comps) for y in Y for k in sg_keys}
    sg_t = {y: sum(sg_y[(y, k)] for k in sg_keys) for y in Y}
    for y in Y:
        if abs(sg_t[y] - oa[y]) > 0.005:
            fail('sped-grants %s: the named streams add to %.2f; other funds paid %.2f on '
                 'sped-all-funds -- a stream is missing from SG_CODES' % (y, sg_t[y], oa[y]))
    alloc = read_allocations()
    # The same rule as build_serf_topics.read_idea (#240 plus #262): asserted, so the two pages'
    # IDEA figures cannot drift apart. TODO: move both into one shared reader.
    import build_serf_topics as _serf
    for y, v in _serf.read_idea().items():
        if abs(v - alloc.get(('240', y), 0.0) - alloc.get(('262', y), 0.0)) > 0.005:
            fail('sped-grants: IDEA allocation %s differs from build_serf_topics.read_idea' % y)
    # Each award: a ledger fund named for one award year of one program.
    awards = []
    for fnd, nm in m['fund_name'].items():
        a = rep[fnd]
        gc_ = J.grant_code(nm) if J.fund_group(a) == 'Grants' else None
        if gc_ not in SG:
            continue
        spent_y = {y: m['fund_spent'].get((y, fnd), 0.0) for y in Y}
        loaded = sum(m['fund_bud'].get((y, fnd), 0.0) for y in Y)
        if not (any(round(v, 2) for v in spent_y.values()) or round(loaded, 2)):
            continue
        gy = grant_year(nm)
        if gy is None:
            fail('sped-grants: fund %s %r names no award year' % (fnd, nm))
        awards.append(dict(fund=fnd, code=gc_, gy=gy, spent=spent_y, loaded=loaded))
    awards.sort(key=lambda r: (SG.index(r['code']), r['gy']))
    for y in Y:
        for k in SG:
            got = sum(r['spent'][y] for r in awards if r['code'] == k)
            if abs(got - sg_y[(y, k)]) > 0.005:
                fail('sped-grants %s #%s: the awards add to %.2f, the stream to %.2f' % (y, k, got, sg_y[(y, k)]))
    # The circuit breaker: what DESE paid, by fiscal year of payment, beside the ledger.
    cbj = json.load(open(CB_JSON, encoding='utf-8'))
    cb_paid = {r['fy']: float(r['paid']) for r in cbj['series']}
    cb_rec = {y: m['fund_rec'].get((y, '2640'), 0.0) for y in Y}
    if abs(cb_rec[F0] - cb_paid[F0]) > 0.5:
        fail('sped-grants: the circuit breaker fund received %.2f in %s; DESE paid %.2f'
             % (cb_rec[F0], F0, cb_paid[F0]))
    lag = cb_paid[F0 + 1] - cb_rec[F0 + 1]
    if not (lag > 0 and abs((cb_rec[F0 + 2] - cb_paid[F0 + 2]) - lag) < 0.5):
        fail('sped-grants: the conclusion says part of %s’s circuit breaker payment was booked '
             'in %s; it no longer reads that way' % (F0 + 1, F0 + 2))
    cb_short = cb_paid[F1] - cb_rec[F1]
    if not cb_short > 0:
        fail('sped-grants: the conclusion says the fund booked less than DESE paid in %s' % F1)
    # IDEA (#240): rose every award year to a peak, then fell every year after.
    i240 = sorted(y for (c, y) in alloc if c == '240')
    peak = max(i240, key=lambda y: alloc[('240', y)])
    if not (all(alloc[('240', b)] > alloc[('240', a_)] for a_, b in zip(i240, i240[1:]) if b <= peak)
            and all(alloc[('240', b)] < alloc[('240', a_)] for a_, b in zip(i240, i240[1:]) if a_ >= peak)
            and peak < i240[-1]):
        fail('sped-grants: the IDEA conclusion says it rose every year, then fell')
    n_fall = sum(1 for y in i240 if y > peak)
    # Pandemic IDEA (#252, #264): allocated once, spent in F0, nothing after.
    PAN = [c for c in SG if c in ('252', '264')]
    if sorted({y for (c, y) in alloc if c in PAN}) != [F0 - 1]:
        fail('sped-grants: the pandemic IDEA grants are said to be allocated in %s only' % (F0 - 1))
    pan = {y: sum(sg_y[(y, k)] for k in PAN) for y in Y}
    if not (pan[F0] > 0 and all(abs(pan[y]) < 0.005 for y in Y[1:])):
        fail('sped-grants: the pandemic IDEA grants are said to have paid in %s only' % F0)
    pan_c = {c: sum(sg_c(F0, k, c) for k in PAN) for c in comps}
    pan_top = max(pan_c, key=lambda c: pan_c[c])
    # Preschool IDEA (#262): the open year's award loaded and unspent; the three before it
    # spent wholly in their own year.
    pre = {r['gy']: r for r in awards if r['code'] == '262'}
    pre_prev = [gy for gy in sorted(pre) if F0 <= gy < F1]
    if not (F1 in pre and abs(sum(pre[F1]['spent'].values())) < 0.005 and pre[F1]['loaded'] > 0
            and len(pre_prev) == len(Y) - 1
            and all(abs(pre[gy]['spent'][gy] - sum(pre[gy]['spent'].values())) < 0.005
                    and pre[gy]['spent'][gy] > 0 for gy in pre_prev)):
        fail('sped-grants: the preschool conclusion says %s’s award is unspent and the three '
             'before were spent in their own year' % F1)
    if abs(pre[F1]['loaded'] - alloc[('262', F1)]) > 0.005:
        fail('sped-grants: the preschool award loaded differs from DESE’s allocation')
    sgx = {}
    for y in (F0, F1):
        sgx['sg-t%d' % y] = f('sg-t%d' % y, U(sg_t[y]), 'paid by grants and the circuit breaker, %s' % C.fy(y),
                             'published', {'y': F(y)})
    sgx['sg-ipk'] = f('sg-ipk', U(alloc[('240', peak)]), 'IDEA allocated, %s, the peak' % C.fy(peak),
                      'published', {'y': F(peak)})
    sgx['sg-ilast'] = f('sg-ilast', U(alloc[('240', i240[-1])]), 'IDEA allocated, %s' % C.fy(i240[-1]),
                        'published', {'y': F(i240[-1])})
    sgx['sg-cbp'] = f('sg-cbp', U(cb_paid[F1]), 'circuit breaker paid by DESE, %s' % C.fy(F1), 'published',
                      {'y': F(F1)})
    sgx['sg-cbr'] = f('sg-cbr', U(cb_rec[F1]), 'booked received in the fund, %s' % C.fy(F1), 'published',
                      {'y': F(F1)})
    sgx['sg-cbs'] = f('sg-cbs', U(sg_y[(F1, 'CB')]), 'spent from the fund, %s' % C.fy(F1), 'published',
                      {'y': F(F1)})
    sgx['sg-cbwhy'] = f('sg-cbwhy', None, 'where the rest of the payment was booked', 'gap',
                        closes='the Town Treasurer’s record of each %s circuit breaker payment: '
                               'date received and fund credited' % C.fy(F1))
    sgx['sg-pan'] = f('sg-pan', U(pan[F0]), 'pandemic IDEA spent, %s, its last year' % C.fy(F0), 'published',
                      {'y': F(F0)})
    sgx['sg-pre'] = f('sg-pre', U(pre[F1]['loaded']), 'preschool IDEA award loaded, %s' % C.fy(F1),
                      'published', {'y': F(F1)})
    sgx['sg-pre0'] = f('sg-pre0', U(sum(pre[F1]['spent'].values())), 'of it spent by the close',
                       'published')
    # Five bands, the chart's limit: the two small groups drawn together, each named in full in
    # the table below by journal.GRANT_PROGRAM.
    SMALL = [c for c in SG if c not in PAN + ['240', '262']]
    bands = [('Circuit breaker', ['CB']), (sg_name['240'], ['240']), (sg_name['262'], ['262']),
             ('Pandemic IDEA, ended', PAN), ('Program improvement grants', SMALL)]
    if sorted(k for _, ks in bands for k in ks) != sorted(sg_keys):
        fail('sped-grants: the chart bands do not hold every stream once')
    sg_tracks = [TP.track(nm, [sum(sg_y[(y, k)] for k in ks) for y in Y], 'published', 'bar')
                 for nm, ks in bands]
    # THE TABLES. Every row foots: the streams to sg_t (= sped-all-funds' other funds), the
    # awards to the streams, asserted above.
    yr_rows = [dict(label='%s (#%s)' % (sg_name[k], k) if k != 'CB' else 'Circuit breaker (fund 2640)',
                    cells=[C.usd(sg_y[(y, k)]) if round(sg_y[(y, k)]) else '' for y in Y]
                    + [C.usd(sum(sg_y[(y, k)] for y in Y))]) for k in sg_keys]
    yr_rows.append(dict(label='All of it', cells=[C.usd(sg_t[y]) for y in Y] + [C.usd(sum(sg_t.values()))]))
    aw_rows = []
    for r in awards:
        al_ = alloc.get((r['code'], r['gy']))
        aw_rows.append(dict(
            label='%s (#%s), %s award' % (sg_name[r['code']], r['code'], C.fy(r['gy'])),
            cells=[C.usd(al_) if al_ is not None else 'not listed', C.usd(r['loaded'])]
            + [C.usd(r['spent'][y]) if round(r['spent'][y]) else '' for y in Y]
            + [C.usd(sum(r['spent'].values()))]))
    cb_rows = [dict(label='Paid by DESE, by year of payment', cells=[C.usd(cb_paid[y]) for y in Y]),
               dict(label='Booked received in fund 2640', cells=[C.usd(cb_rec[y]) for y in Y]),
               dict(label='Spent from fund 2640', cells=[C.usd(sg_y[(y, 'CB')]) for y in Y])]

    def card(title, keys, sub, so):
        rows = [(J.COMPONENT_LABEL[c], C.usd(sum(sg_c(y, k, c) for y in Y for k in keys)), None)
                for c in comps if round(sum(sg_c(y, k, c) for y in Y for k in keys))]
        tot = sum(sg_y[(y, k)] for y in Y for k in keys)
        if abs(sum(sum(sg_c(y, k, c) for y in Y for k in keys) for c in comps) - tot) > 0.005:
            fail('sped-grants: card %r does not foot' % title)
        rows.append((('All of it, %s' % C.fyspan(F0, F1), {'y': F(F0), 'z': F(F1)}), C.usd(tot), None))
        return TB.panel(title, rows, sub=sub, so=so)
    cb4 = {c: sum(sg_c(y, 'CB', c) for y in Y) for c in comps}
    i4 = {c: sum(sg_c(y, '240', c) for y in Y) for c in comps}
    cb_top, i_top = max(cb4, key=cb4.get), max(i4, key=i4.get)
    if cb_top != 'tuition' or i_top != 'pay':
        fail('sped-grants: the cards say the circuit breaker mostly paid tuition and IDEA mostly pay')
    pay_blocks = TB.panels('What each one pays for', [
        card(('IDEA (#240)', None, ('240',)), ['240'],
             'Federal, by formula. Each award is spent over up to three school years.',
             'Mostly staff pay: the grant pays for people, so a smaller award is a question about posts.'),
        card('Circuit breaker', ['CB'],
             'Not a grant: the state repaying part of last year’s costliest placements.',
             'Mostly tuition: it follows the placements it repays, so it moves with them a year late.'),
        card(('Preschool IDEA (#262)', None, ('262',)), ['262'],
             'Federal, by formula, for children aged three to five.',
             'Small and steady: it changes little from year to year.'),
        card('Ended and small grants', PAN + SMALL,
             'Pandemic IDEA, ended; and the program improvement grants.',
             'Money that has stopped: whatever it paid for is now paid by another fund or not at all.'),
    ], place='chart')

    # TRENDS, ONE CHART PER STREAM. TJ, 26 October 2026: "add trend line graphs for each grant
    # so we can see how they are trending and what the average is or projected amount for the
    # next year". Each on its own scale (a shared one flattens the small grants), each with its
    # average as a reference line and the next year: a PUBLISHED figure where one exists (IDEA's
    # announced allocation; the district's initial circuit breaker listing), else OUR estimate --
    # the last figure moved by the median yearly change, drawn as an estimate and labelled so.
    # The ended grants get no next year.
    deck = open(os.path.join(ROOT, 'sources', 'correspondence', 'text',
                             '2026-10-22-special-education-funding-superintendent-finance-committee.pptx.txt'),
                encoding='utf-8').read()
    CB27 = 818087
    if '$818,087' not in deck or 'FY27 initial' not in deck:
        fail('sped-grants: the deck no longer gives the FY2027 initial circuit breaker listing')
    cbs = {r['fy']: r['paid'] for r in json.load(open(CB_JSON, encoding='utf-8'))['series']}
    cby = sorted(cbs)
    if cby[-1] != F1:
        fail('sped-grants: the circuit breaker file does not end at %s' % F1)
    cb_avg = statistics.mean(cbs.values())
    # The composition is the stacked bars at the top of this page; these are each stream's
    # trend, as lines (trend_chart).
    t_cb = trend_chart('Circuit breaker, paid each year', cby, 'Paid, by year of payment',
                       [cbs[y] for y in cby], F1 + 1, CB27,
                       'Initial listing (district)', 'stated', cb_avg,
                       'Average, %s to %s' % (C.fy(cby[0]), C.fy(cby[-1])),
                       ('DESE’s payments by the year paid; the next year is the district’s initial '
                        'listing, which DESE revises during the year.', None),
                       ('It swings: %s at its lowest, %s at its highest, against an average of %s. The '
                        '%s listing, %s, is above every year paid.'
                        % (C.usd(min(cbs.values())), C.usd(max(cbs.values())), C.usd(cb_avg), C.fy(F1 + 1),
                           C.usd(CB27)),
                        {'a': U(min(cbs.values())), 'b': U(max(cbs.values())), 'c': U(cb_avg),
                         'y': F(F1 + 1), 'd': U(CB27)}))
    if not CB27 > max(cbs.values()):
        fail('sped-grants: the trend says the FY2027 listing is above every year paid')
    t_idea = [alloc_trend_chart(alloc, k, sg_name[k], 'sped-grants') for k in ('240', '262')]
    out['sped-grants'] = TP.page(
        'sped-grants',
        'Special education grants and the circuit breaker paid %s in %s and %s in %s.'
        % (C.usd(sg_t[F0]), C.fy(F0), C.usd(sg_t[F1]), C.fy(F1)),
        list(sgx.values()),
        [con('IDEA rose every year to %s for %s, then fell %s years running, to %s for %s.'
             % (C.usd(alloc[('240', peak)]), C.fy(peak), C.num(n_fall), C.usd(alloc[('240', i240[-1])]),
                C.fy(i240[-1])), ['sg-ipk', 'sg-ilast'],
             {'a': U(alloc[('240', peak)]), 'y': F(peak), 'n': N(n_fall),
              'b': U(alloc[('240', i240[-1])]), 'z': F(i240[-1])},
             so='The largest grant has stopped growing, so none of the next rise in special '
                'education costs is covered by it.',
             notes=[step('An allocation is what DESE awards; spending is what the ledger shows. '
                         'They are different stages, shown side by side and never subtracted.',
                         'measured')]),
         con('DESE paid %s of circuit breaker in %s; the fund booked %s received and spent %s.'
             % (C.usd(cb_paid[F1]), C.fy(F1), C.usd(cb_rec[F1]), C.usd(sg_y[(F1, 'CB')])),
             ['sg-cbp', 'sg-cbr', 'sg-cbs', 'sg-cbwhy'],
             {'a': U(cb_paid[F1]), 'y': F(F1), 'b': U(cb_rec[F1]), 'c': U(sg_y[(F1, 'CB')])},
             so=('The rest may be booked later, as %s of %s’s was, or booked elsewhere; '
                 'the ledger cannot say which.' % (C.usd(lag), C.fy(F0 + 1))),
             so_figures={'a': U(lag), 'y': F(F0 + 1)},
             notes=[step('%s is not yet closed in this run.' % C.fy(F1), 'gap', {'y': F(F1)},
                         closes='the Town’s journal report for %s, run after the year is closed' % C.fy(F1)),
                    step('How the reimbursement is worked out, and Chapter 70, which is general '
                         'state aid and not a special education grant, are on the circuit breaker '
                         'page.', 'measured', allow=('70',),
                         cite=('/special-education/circuit-breaker', 'Circuit breaker'))]),
         con('The two pandemic IDEA grants paid %s in %s and nothing after; DESE allocated them once.'
             % (C.usd(pan[F0]), C.fy(F0)), ['sg-pan'], {'a': U(pan[F0]), 'y': F(F0)},
             so='What they paid for, mostly %s, either moved to another fund or stopped; the ledger '
                'cannot tell which.' % J.COMPONENT_LABEL[pan_top].lower()),
         con('Preschool IDEA’s %s award, %s, had nothing spent by the close; the %s before were spent in-year.'
             % (C.fy(F1), C.usd(pre[F1]['loaded']), C.num(len(pre_prev))), ['sg-pre', 'sg-pre0'],
             {'y': F(F1), 'a': U(pre[F1]['loaded']), 'n': N(len(pre_prev))},
             so='Small, but the one award here with nothing spent; whether it was spent after the '
                'close is not in this ledger.')],
        finding_figures={'a': U(sg_t[F0]), 'y': F(F0), 'b': U(sg_t[F1]), 'z': F(F1)},
        chart=TP.series('Special education money outside the vote', years, sg_tracks, '$', kind='bar',
                        stacked=True, totals=True,
                        note='Spent or still owed at the close, by the fund that paid. %s' % open_note,
                        note_figures={'y': F(F1)}),
        # The combined 'IDEA allocations by award year' line chart was dropped 26 October 2026:
        # it repeated the per-stream trend lines below, and its shared scale flattened preschool.
        table=dict(caption='Special education money outside the vote, by year', views=[dict(
            key='years', label='By year', total_col=len(Y), kinds=['ledger'] * (len(Y) + 1),
            columns=years + ['Four years'], rows=yr_rows,
            note='Spent or still owed at the close. The bottom row is the other-funds figure on '
                 'Special education, all funds.')]),
        tables=[dict(caption='Each grant award: allocated, loaded and spent', views=[dict(
            key='awards', label='By award', total_col=len(Y) + 2, kinds=['published', 'ledger'] + ['ledger'] * (len(Y) + 1),
            columns=['Allocated by DESE', 'Loaded in the ledger'] + years + ['Spent, these years'],
            rows=aw_rows,
            note='Allocated and loaded are budgets; spent is the ledger, and is not subtracted from '
                 'either. Loaded and spent count %s only: an older award’s earlier figures are not '
                 'in this journal. Not listed: DESE’s file does not list that award.'
                 % C.fyspan(F0, F1))]),
                dict(caption='The circuit breaker: paid, received and spent', views=[dict(
                    key='cb', label='Circuit breaker', total_col=None, kinds=['ledger'] * len(Y),
                    columns=years, rows=cb_rows,
                    note='DESE’s payment is by the fiscal year it was paid; the fund’s receipts and '
                         'spending are the Town’s ledger.')])],
        blocks=[TB.explain('Grants and a reimbursement', [
            'The grants are federal awards DESE allocates to each district by formula. The '
            'circuit breaker is not a grant: it is the state repaying part of the previous '
            'year’s costliest placements.'], place='chart'), t_cb] + t_idea + [pay_blocks],
        sources=sources() + [
            dict(label='Massachusetts DESE — entitlement grant allocations, by district and fund '
                       'code (dese-entitlement-allocations.csv)',
                 href='/docs/data/dese-entitlement-allocations.csv'),
            dict(label='Massachusetts DESE — circuit breaker reimbursements, every district '
                       '(dese-circuit-breaker.xlsx)', href='/docs/state-dese/dese-circuit-breaker.xlsx')])
    out['sped-grants']['not_established'] = [
        'Where the rest of the latest circuit breaker payment was booked, if anywhere.',
        'What the pandemic IDEA grants’ work was paid from after they ended, or whether it stopped.',
        'Grants that pay special education from accounts the ledger does not label so.',
    ]

    # ================================================== the hub
    hb = dict(
        v=f('h-v', U(m['gf_voted'][F1]), 'general fund, voted, %s' % C.fy(F1), 'published', {'y': F(F1)}),
        g=f('h-g', U(m['spent'][(F1, 'General fund')]), 'general fund, spent or owed, %s' % C.fy(F1), 'published',
            {'y': F(F1)}),
        a=f('h-a', U(m['all'][F1]), 'spent from every fund, %s' % C.fy(F1), 'published', {'y': F(F1)}),
        o=f('h-o', U(m['outside'][F1]), 'spent outside the general fund, %s' % C.fy(F1), 'published', {'y': F(F1)}),
        u=f('h-u', U(m['unattr'][F1]), 'of it on no budget line', 'published'),
        w=f('h-w', U(owed1), 'of all spent, owed and not yet paid, %s' % C.fy(F1), 'published',
            {'y': F(F1)}),
        i=f('h-i', P(g_line[F1]), 'grant spending on a voted line, %s' % C.fy(F1), 'published', {'y': F(F1)}),
        i1=f('h-i1', U(g25['none']), '%s IDEA grant with no code at all' % C.fy(2025), 'published',
             {'y': F(2025)}),
        b=f('h-b', U(end_tot), 'held in funds that carry, end of %s, our count' % C.fy(F1), 'estimate',
            {'y': F(F1)}),
        s=f('h-s', U(oa[F1]), 'special education paid outside the vote, %s' % C.fy(F1), 'published', {'y': F(F1)}),
        t=f('h-t', N(rc['ytd_accounts'], 'accounts'), 'tied to the Town’s spreadsheets, to the cent', 'published'),
    )
    hub_ladder = LD.ladder([
        # THE ORDER IS THE ARITHMETIC: the vote, then spending in two parts, then their sum.
        # Shown as voted / every fund / outside, a reader added the vote to the outside spending
        # and got a total the page does not print (TJ, 23 October 2026): the vote is a budget
        # and the other two are spending (rule 1), so they never sum.
        LD.tier('Money in and out', [hb['v'], hb['g'], hb['o'], hb['a'], hb['u'], hb['w']]),
        LD.tier('How it is booked', [hb['i'], hb['i1'], hb['b'], hb['s'], hb['t']]),
    ], [
        LD.conclusion('%s: the general fund spent %s of %s voted; other funds added %s.'
                      % (C.fy(F1), C.usd(m['spent'][(F1, 'General fund')]), C.usd(m['gf_voted'][F1]),
                         C.usd(m['outside'][F1])), ['h-v', 'h-g', 'h-o', 'h-a'],
                      {'y': F(F1), 'g': U(m['spent'][(F1, 'General fund')]), 'a': U(m['gf_voted'][F1]),
                       'o': U(m['outside'][F1])}),
        LD.conclusion('Of %s spent outside it, %s was booked to no budget line.'
                      % (C.usd(m['outside'][F1]), C.usd(m['unattr'][F1])), ['h-o', 'h-u'],
                      {'a': U(m['outside'][F1]), 'b': U(m['unattr'][F1])}),
        LD.conclusion('Special education ran past its vote every year; other funds paid the rest.',
                      ['h-s']),
    ])
    eo_t = sum(1 for e in eo if e['ties'])
    tie_rows = [
        dict(label='Period-13 spreadsheets, %s' % C.fyspan(F0, F1),
             cells=['%s accounts, %s account-years' % (C.num(rc['ytd_accounts']), C.num(rc['ytd_rows'])),
                    'every one ties to the cent; they hold %s to %s of each year’s spending'
                    % (C.pct(min(rc['coverage'].values()), 0), C.pct(max(rc['coverage'].values()), 0))]),
        dict(label='The report’s own printed totals, %s' % C.fy(F1),
             cells=['%s accounts' % C.num(rc['printed_accounts']), 'every one ties to the cent']),
        dict(label='Town report, special revenue, %s' % C.fy(F0),
             cells=['%s funds' % C.num(len(art)),
                    '%s tie to the cent; see Unspent money by fund' % C.num(sum(1 for r in art if r['ties']))]),
        dict(label='DESE End of Year report, %s' % C.fy(F0),
             cells=['%s fund columns' % C.num(len(eo)),
                    '%s tie to the dollar: %s' % (C.num(eo_t), ', '.join(e['label'] for e in eo if e['ties']))
                    + ''.join('; %s differs by %s' % (e['label'], C.usd(abs(e['eoyr'] - e['journal'])))
                              for e in eo if not e['ties'])]),
    ]
    out[HUB] = TP.hub(
        HUB,
        'The voted school budget is the general fund. Every fund together spent %s in %s, %s more, '
        'and these pages show where it came from and which lines it paid.'
        % (C.usd(m['all'][F1]), C.fy(F1), C.usd(m['all'][F1] - m['gf_voted'][F1])),
        hub_ladder,
        chart=TP.series('School spending by fund', years, [
            TP.track(g, [sp[(y, g)] for y in Y], 'published') for g in GROUPS], '$', kind='bar',
            stacked=True, note='Spending in every school fund. %s' % spent_note, note_figures={'y': F(F1)}),
        table=dict(caption='How these figures tie to what the Town and the state printed', views=[dict(
            key='ties', label='Reconciliation', total_col=None, kinds=['ledger', 'ledger'],
            columns=['Compared with', 'Result'], rows=tie_rows,
            note='The first two must hold to the cent or nothing on these pages is written. The '
                 'last two are other publishers’ readings of the same money, compared and shown.')]),
        answer_figures={'a': U(m['all'][F1]), 'y': F(F1), 'b': U(m['all'][F1] - m['gf_voted'][F1])},
        # The Grants bar above, by name (TJ, 26 October 2026: "breakdown the grants by the name").
        # The twelve largest, the rest together; every grant by year is on Paid outside the
        # general fund.
        blocks=[TB.chart(TP.ranking(
            'Grant spending, by grant',
            [(nm, g4[nm]) for nm in gnames[:12]]
            + ([('%s other grants' % C.num(len(gnames) - 12), sum(g4[nm] for nm in gnames[12:]))]
               if len(gnames) > 12 else []), '$',
            note='%s, spent or still owed at the close, every award year of a grant together.'
                 % C.fyspan(F0, F1), note_figures={'y': F(F0), 'z': F(F1)}),
            place='chart',
            so=('The two pandemic grants paid nothing in %s; IDEA, %s over four years, is the '
                'largest grant still paying.' % (C.fy(F1), C.usd(g4[J.GRANT_PROGRAM['240']])),
                {'y': F(F1), 'a': U(g4[J.GRANT_PROGRAM['240']])}))])

    if sorted(k for k in out if k != HUB) != MINE:
        fail('the pages built are not the pages the registry gives this script: %s vs %s'
             % (sorted(out), MINE))

    # ---- the model payload: every headline figure, by name, for the verifier
    figs = dict(
        years=list(Y), reconciliation=rc,
        gf_voted={str(y): round(m['gf_voted'][y], 2) for y in Y},
        gf_spent={str(y): round(gfs[y], 2) for y in Y},
        all_spent={str(y): round(m['all'][y], 2) for y in Y},
        outside_spent={str(y): round(m['outside'][y], 2) for y in Y},
        spent_basis='payments plus what was still owed (journal.SPENT: %s)' % ', '.join(J.SPENT),
        by_group={str(y): {g: round(sp[(y, g)], 2) for g in GROUPS} for y in Y},
        owed={str(y): {g: round(m['owed'][(y, g)], 2) for g in GROUPS} for y in Y},
        unattributed={str(y): round(m['unattr'][y], 2) for y in Y},
        receipts={str(y): {g: round(rin[(y, g)], 2) for g in OUTSIDE} for y in Y},
        chapter70={str(y): m['ch70'][y] for y in Y},
        idea={str(y): {k: round(v, 2) for k, v in idea[y].items()} for y in Y},
        idea_funds=idea_funds,
        idea_by_grant={str(gy): {k: (round(v, 2) if isinstance(v, float) else v) for k, v in d.items()} for gy, d in ig.items()},
        grant_line_share={str(y): round(g_line[y], 4) for y in Y},
        sped={str(y): dict(voted=round(gv[y], 2), gf_spent=round(ga[y], 2), outside=round(oa[y], 2))
              for y in Y},
        sped_grants=dict(
            streams={str(y): {k: round(sg_y[(y, k)], 2) for k in sg_keys} for y in Y},
            total={str(y): round(sg_t[y], 2) for y in Y},
            cb_paid={str(y): cb_paid[y] for y in Y},
            cb_received={str(y): round(cb_rec[y], 2) for y in Y},
            allocations={'%s-%d' % k: v for k, v in sorted(alloc.items())},
            awards=[dict(fund=r['fund'], code=r['code'], award_fy=r['gy'], loaded=round(r['loaded'], 2),
                         spent={str(y): round(r['spent'][y], 2) for y in Y}) for r in awards]),
        carry=[dict(fund=r['fund'], carried_fy2023=r['carried'], end=round(r['end'], 2),
                    owed_fy2026=round(r['owed'], 2)) for r in bal],
        annual_report_tie=[{k: r[k] for k in ('fund', 'ar_name', 'receipts', 'ar_receipts', 'spent',
                                              'ar_spent', 'ties', 'net_ties')} for r in art],
        eoyr_tie=eo,
        ended_grants=dict(award=round(aw_tot, 2), never_spent=round(left_tot, 2)),
        money_in=money_in,
        lines=[{k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()} for r in line_rows],
    )
    return out, figs


def markdown(pages):
    """The pages as one document, in shelf order: each page's finding, its conclusions with what
    is not known beneath them, its tables, what it does not establish, and its sources."""
    cat = REG.category(HUB)
    order = [HUB] + [t for _, ids in cat['groups'] for t in ids if t in pages]
    # A page this script builds for another shelf (sped-grants) still belongs in the document.
    order += sorted(t for t in pages if t not in order)
    hub = pages[HUB]
    o = ['# %s' % hub['title'], '', hub['answer']['text'], '',
         '*Generated by `scripts/build_school_all_funds.py` from the school MUNIS journal. Every '
         'figure is a posting to a school account, %s, and %s is not yet closed. The pages '
         'are at /%s.*' % (C.fyspan(F0, F1), C.fy(F1), HUB), '']

    def table(t):
        out = []
        for v in t['views']:
            out += ['**%s — %s**' % (t['caption'], v['label']), '',
                    '| | ' + ' | '.join(v['columns']) + ' |',
                    '|---|' + '---:|' * len(v['columns'])]
            out += ['| %s | %s |' % (r['label'], ' | '.join(c or '' for c in r['cells']))
                    for r in v['rows']]
            if v.get('note'):
                out += ['', '*%s*' % v['note']]
            out.append('')
        return out
    for c in hub['ladder']['conclusions']:
        o.append('- %s' % c['text'])
    o.append('')
    if hub.get('table'):
        o += table(hub['table'])
    for t in order[1:]:
        p = pages[t]
        o += ['## %s' % p['title'], '', '**%s**' % p['finding']['text'], '']
        for c in p['conclusions']:
            o.append('- %s' % c['text'])
            for n in c.get('notes', []):
                tag = {'gap': 'not known'}.get(n['kind'], n['kind'])
                o.append('  - *%s:* %s%s' % (tag, n['text'],
                                            (' — closes: %s' % n['closes']) if n.get('closes') else ''))
        o.append('')
        if p.get('table'):
            o += table(p['table'])
        if p.get('not_established'):
            o += ['What this does not establish:', ''] + ['- %s' % x for x in p['not_established']] + ['']
        o += ['Sources: ' + '; '.join('[%s](%s)' % (s['label'], s['href']) for s in p['sources']), '']
    return '\n'.join(o).rstrip() + '\n'


def outputs():
    pages, figs = build()
    o = {os.path.join(OUT_DIR, '%s.json' % t): json.dumps(p, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
         for t, p in pages.items()}
    o[MODEL_OUT] = json.dumps(figs, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
    o[MD_OUT] = markdown(pages)
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    outs = outputs()
    if a.check:
        stale = [os.path.relpath(p, ROOT) for p, text in outs.items()
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != text]
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('school budget, all funds: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        os.replace(tmp, p)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
