#!/usr/bin/env python3
"""WHAT THE ACTIVITY FEES PAY FOR: the school's After School Activities fund (1305), FY2023-FY2026.

    python3 scripts/build_activities_fund_topics.py           # write fy28/public/data/topics/activities-fund.json
    python3 scripts/build_activities_fund_topics.py --check   # fail if it would change

    activities-fund   /school-all-funds/activities-fund   After-school activities fund

On the School budget, all funds shelf, group "Who grants and fees pay for" (scripts/topic_registry/
school_all_funds.py, through TOPIC_GENERATORS). TJ, 28 October 2026: "people always ask me 'what
is the activities fee for'... now we know. lets build a topic page". It grew out of the FY
breakdown, where fund 1305 showed $178,540 of FY2026 spending under function 2000 with no school
line, and TJ chose a page of its own over calling it out there.

WHAT IS MEASURED, from the school journal (journal.py), and refused if it stops being true:
  * MONEY IN is the net of the payments posted to the fund's income accounts, which the Town
    titles by school: HIGH / MIDDLE / ELEM / PRIMARY SCHOOL ACTIVITY FEES, and DISTRICT WIDE
    REVENUE. Mostly deposits (`CRP`), less refunds paid back to families off the same accounts.
    Orders opened on an income account (`POE`/`POL`/`POM`) are not money and are left out.
    A PAYMENT off an income account (`API`) is spending, under its payee: FY2025's Nature's
    Classroom bills were paid that way, and as a refund they would have hidden inside income.
  * MONEY OUT is the site's SPENT (journal.SPENT: payments plus what is still owed) on the fund's
    expense accounts, which the Town codes three ways only: SALARIES REVOLVING FUNDS, PURCHASE
    OF SERVICE, GENERAL SUPPLIES, all under function 2000.
  * WHO WAS PAID is the payee the journal prints. The GROUPING of payees is ours (PAYEES below),
    declared one organisation at a time, by what the organisation IS -- a bus company, an exam
    board, a hotel -- and never by what the trip was for. Pay is the Town's own code.

THE NAME IS THE TOWN'S, ON PURPOSE. The fund is called After School Activities and its income
accounts ACTIVITY FEES; the School Committee's $70 STUDENT ACTIVITY FEE (rate-register.csv) is a
different thing until something shows it is deposited here -- the district also keeps student
activity accounts outside the Town's books altogether (money-gaps.csv), and its payment portal
sells an Afterschool Activity Fee and Field Trips as separate items. So the page answers what
this fund paid for, and never what the $70 pays for.

WHAT IS NOT: how much of the income is the student activity fee and how much is families paying
the fund for one named trip, exam or prom.
Some deposit memos name the trip (`ELEM SCH ACTIVITY/NATURE'S CLA`, `LHS TESTING/HSACT`); most
say only the school. The journal posts deposits in batches, so it cannot split them. Registered
in money-gaps.csv. Nor what the fund held at any year end: a balance, also registered.

THE REDACTION (memory: redaction-principle-recipients-not-providers). Only an organisation named
in PAYEES gets a row. Every other payee -- which includes every person reimbursed, refunded or
paid for a class fund -- is inside "every other payee", never a row of its own.
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
from brief import step  # noqa: E402
import journal as J  # noqa: E402

OUT_DIR = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics')
ME = os.path.basename(__file__)
TID = 'activities-fund'
MINE = sorted(t for t, (_, _, gen) in REG.TOPICS.items() if gen == ME)
FUND = '1305'
Y = J.YEARS
F0, F1 = Y[0], Y[-1]
ZERO = Decimal(0)
NAMED_MIN = Decimal(1500)        # a declared payee gets its own table row from four-year spending this size
RATES = os.path.join(ROOT, 'sources', 'data', 'rate-register.csv')
YTD = os.path.join(ROOT, 'sources', 'data', 'munis-school-ytd.csv')
INTEREST = '480100'      # INVESTMENT INCOME: department 000, so on the Town's report and not in the school journal
SPLIT_CLOSES = ('the deposit detail behind each batch, by activity, and which account the student '
                'activity fee is paid into')
BALANCE_CLOSES = ('the Town’s special revenue fund balance report at each year’s close, for the '
                  'After School Activities fund')

# WHO EACH ORGANISATION IS, declared one at a time (ours). The key is journal.vendor_key() of the
# payee the journal prints, cut where the Town cuts it.
PAYEES = {
    'nc': ('Nature’s Classroom', ['NATURES CLASSROOM']),
    'exam': ('Exam boards', ['COLLEGE BOARD', 'AP EXAMINATIONS', 'EDUCATIONAL TESTING',
                             'LANGUAGE TESTING']),
    'bus': ('Bus and limousine companies', ['DEE BUS SERVICE INC', 'BUCKINGHAM BUS COMPA',
                                            'YANKEE LINE, INC', 'VAN POOL', 'FIRST CHOICE LIMOUSI',
                                            'KNIGHTS AIRPORT LIMO']),
    'venue': ('Hotels and function venues', ['WACHUSETT MOUNTAIN', 'CHOCKSETT INN INC',
                                             'COLONIAL HOTEL']),
    'trip': ('Museums, parks and performers', [
        'JEMAZ INC', 'CANOBIE LAKE PARK CO', 'PAWTUCKET RED SOX', 'KRAFT SOCCER LLC',
        'SOUTHWICK WILD ANIMA', 'BEAVER BROOK ASSOC', 'CROCODILE RIVER MUSI', 'MUSEUM OF SCIENCE',
        'DAVID FRENCH MUSIC C', 'ANIMAL ADVENTURES', 'WORCESTER CENTER FOR', 'MOBILE ED PRODUCTION',
        'CONCORD MUSEUM', 'EASTERN STATES EXPOS', 'DISCOVERY MUSEUM', 'MOUNT WACHUSETT COMM',
        'OLD STURBRIDGE INC', 'MASSACHUSETTS AUDUBO', 'ECOTARIUM', 'GILLETTE STADIUM',
        'ROTASPRING FARM']),
    'audit': ('Audit firm', ['POWERS AND SULLIVAN']),
}
GROUP_OF = {v: k for k, (_, vs) in PAYEES.items() for v in vs}
# A PAYMENT POSTED TO AN INCOME ACCOUNT AND THEN MOVED to an expense account by journal entry:
# Nature's Classroom, $51,120.00, FY2024. The payment is counted where it was posted, so the
# entry that moved it is left out of both sides (it nets to nothing; asserted).
MOVED = ('2024/03/000922',)
# AN ENTRY THAT NAMES ITS PAYEE ONLY IN THE MEMO: a refund of an overpayment, deposited against
# the expense account ("NATURE'S CLASSROOM OVERPAY"). Declared, and checked against the amount.
RECLASS = {'2024/05/000612': ('NATURES CLASSROOM', Decimal('-6500.00'))}
ORDER = ['pay', 'nc', 'exam', 'bus', 'venue', 'trip', 'audit', 'rest']
LABEL = dict({k: n for k, (n, _) in PAYEES.items()}, pay='Pay', rest='Every other payee')
SCHOOLS = [('hs', 'High school', '436600', 'HS'), ('ms', 'Middle school', '436400', 'MS'),
           ('es', 'Elementary', '436500', 'ES'), ('ps', 'Primary', '436900', 'PS'),
           ('dw', 'District-wide', '432000', 'SYSTEM')]
NAMED_MEMO = re.compile(r'NATURE|TESTING|\bAP\b|\bPROM\b|EXAM')


def fail(msg):
    raise SystemExit('build_activities_fund_topics: ' + msg)


def data():
    A = J.accounts()
    L = [r for r in J.lines() if r['fund'] == FUND]
    if not L:
        fail('the journal holds no line on fund %s' % FUND)
    t = defaultdict(Decimal)

    def spend(r, y, school, g, p=None):
        if g not in ('pay', 'rest'):
            t[('payee', y, p)] += r['amt']
        t[('out', y)] += r['amt']
        t[('out', y, g)] += r['amt']
        t[('out', y, school)] += r['amt']

    def group(p):
        return GROUP_OF.get(p, 'rest') if isinstance(p, str) else 'rest'

    for r in L:
        a, y = A[r['account']], r['fy']
        if r['journal'] in MOVED:
            continue
        if J.is_revenue(a):
            # orders opened on an income account are not money
            if r['posts_to'] != 'actual':
                continue
            code = next((s for s, _, obj, _ in SCHOOLS if r['object'] == obj), None)
            if code is None:
                fail('an income line on %s is on no school account' % r['account'])
            # A PAYMENT OFF AN INCOME ACCOUNT IS SPENDING. FY2025's Nature's Classroom bills were
            # paid that way; counted as a refund they would hide in a smaller income
            if r['source'] == 'API':
                p = J.payee(r)
                spend(r, y, code, group(p), p)
                t[('api_in', y)] += r['amt']
                continue
            t[('in', y)] -= r['amt']
            t[('in', y, code)] -= r['amt']
            if r['source'] == 'CRP':
                t[('dep', y)] -= r['amt']
                if NAMED_MEMO.search(r['description'].upper()):
                    t[('named', y)] -= r['amt']
            continue
        if not J.is_expense(a):
            fail('%s is neither income nor expense' % r['account'])
        if not J.is_spent(r):
            continue
        if J.function(r['account']) != '2000':
            fail('%s is not under function 2000; the page says every expense is' % r['account'])
        if r['posts_to'] == 'encumbrance':
            t[('enc', y, r['account'])] += r['amt']
            # A CLOSED YEAR IS READ OFF ITS PAYMENTS. The close (`YEC`) zeroes an open order with
            # no vendor on the line, so counting encumbrances by payee would put an order under
            # its vendor and its zeroing under nobody. In a closed year they net to nothing on
            # every account (asserted below), so leaving them out moves no total.
            if y != J.OPEN_FY:
                continue
        school = next((s for s, _, _, org in SCHOOLS if r['org_name'].startswith(org)), None)
        if school is None:
            fail('%s spends from an org the page does not name: %s' % (r['account'], r['org_name']))
        if r['object'] == '519999':
            spend(r, y, school, 'pay')
        else:
            p = RECLASS.get(r['journal'], (None, None))[0] or J.payee(r)
            spend(r, y, school, group(p), p)
    for k in [k for k in t if k[0] == 'enc' and k[1] != J.OPEN_FY]:
        if t[k] != 0:
            fail('FY%d %s: orders do not net to nothing over a closed year' % (k[1], k[2]))
    for jr in MOVED:
        hit = [r for r in L if r['journal'] == jr]
        if not hit or sum((r['amt'] for r in hit), ZERO) != 0:
            fail('journal entry %s no longer moves money within the fund and back to nothing' % jr)
    for jr, (p, amt) in RECLASS.items():
        hit = [r for r in L if r['journal'] == jr and J.is_expense(A[r['account']])]
        if sum((r['amt'] for r in hit), ZERO) != amt:
            fail('journal entry %s no longer moves %s on an expense account' % (jr, amt))
    tie(t, L, A)
    for y in Y:
        if sum((t[('out', y, g)] for g in ORDER), ZERO) != t[('out', y)]:
            fail('FY%d: the groups do not sum to the spending' % y)
        if sum((t[('in', y, s)] for s, *_ in SCHOOLS), ZERO) != t[('in', y)]:
            fail('FY%d: the schools do not sum to the income' % y)
        if sum((t[('out', y, s)] for s, *_ in SCHOOLS), ZERO) != t[('out', y)]:
            fail('FY%d: the schools do not sum to the spending' % y)
    return t


def tie(t, L, A):
    """THE TOWN'S OWN TOTALS. The period-13 report (munis-school-ytd.csv, `special-school`) prints
    fund 1305 account by account. Every year, the journal's expense postings must equal what it
    prints expended, to the cent, and its income postings what it prints received less the
    interest -- which posts on department 000 and so never reaches the school journal. The
    interest is read from the report and shown as its own figure."""
    p = defaultdict(Decimal)
    for r in csv.DictReader(open(YTD, encoding='utf-8')):
        if r['fund'] != FUND or r['period'] != '13' or r['report'] != 'special-school':
            continue
        y = int(r['fiscal_year'])
        k = 'int' if r['obj'] == INTEREST else r['type']
        p[(y, k)] += Decimal(r['ytd_expended'])
        if r['type'] == 'E':
            p[(y, 'enc')] += Decimal(r['encumbrances'])
    for y in Y:
        if not p[(y, 'E')]:
            fail('FY%d: the period-13 report holds no fund %s' % (y, FUND))
        je = sum((r['amt'] for r in L if r['fy'] == y and r['posts_to'] == 'actual'
                  and J.is_expense(A[r['account']])), ZERO)
        jr = sum((r['amt'] for r in L if r['fy'] == y and r['posts_to'] == 'actual'
                  and J.is_revenue(A[r['account']])), ZERO)
        if je != p[(y, 'E')] or p[(y, 'enc')] != 0:
            fail('FY%d: the journal spent %s; the report prints %s expended and %s owed'
                 % (y, je, p[(y, 'E')], p[(y, 'enc')]))
        if jr != p[(y, 'R')]:
            fail('FY%d: the journal received %s; the report prints %s less interest' % (y, jr, p[(y, 'R')]))
        t[('int', y)] = -p[(y, 'int')]
        t[('town_out', y)] = p[(y, 'E')]


def fee():
    """The student activity fee as the School Committee last set it in this run, from the rate
    register: (amount, fiscal year, date voted). Interpolated, never typed (rule 2)."""
    rows = [r for r in csv.DictReader(open(RATES, encoding='utf-8'))
            if r['category'] == 'activity_fee' and r['value'] and r['status'] == 'verified']
    if not rows:
        fail('rate-register.csv holds no verified student activity fee')
    r = max(rows, key=lambda r: int(r['fy']))
    return Decimal(r['value']), int(r['fy']), r['set_on']


def long_date(iso):
    y, m, d = (int(x) for x in iso.split('-'))
    return '%d %s %d' % (d, ('January February March April May June July August September October '
                             'November December').split()[m - 1], y)


def sources():
    return [
        dict(label='Lunenburg Budget Project — munis-school-journal.csv (every school journal '
                   'line, FY2023–FY2026, our redacted reading of the Town’s Report 1)',
             href=J.PUBLIC['journal']),
        dict(label='Lunenburg Budget Project — munis-school-journal-accounts.csv (every school '
                   'account, fund 1305 among them)', href=J.PUBLIC['accounts']),
        dict(label='Town of Lunenburg — how the journal reached us, and what was redacted',
             href='/docs/town-ledgers/account-details/'
                  'PROVENANCE-fy2023-fy2026-p13-school-journal.md'),
        dict(label='Lunenburg School Committee — minutes, 7 May 2025 (the student activity fee)',
             href='/docs/meetings/text/school-committee/2025-05-07-minutes-7207.txt'),
    ]


def build():
    t = data()
    U = lambda v: figure(float(v), C.usd(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v: figure(float(v), C.pct(v, 0))
    f, con = LD.fact, TP.conclusion
    fv = lambda x: float(x)
    four = lambda k: sum((t[(k[0], y) + k[1:]] for y in Y), ZERO)
    span = C.fyspan(F0, F1)
    SP = figure(F0, span, 'fiscal years')

    out4, in4 = four(('out',)), four(('in',))
    g4 = {g: four(('out', g)) for g in ORDER}
    trips = g4['nc'] + g4['bus'] + g4['trip'] + g4['venue']
    named4, dep4 = four(('named',)), four(('dep',))
    amount, fee_fy, fee_date = fee()

    px = {}
    px['in'] = f('in', U(t[('in', F1)]), 'paid into the fund, %s' % C.fy(F1), 'published', {'y': F(F1)})
    px['out'] = f('out', U(t[('out', F1)]), 'spent from it, %s' % C.fy(F1), 'published', {'y': F(F1)})
    px['nc'] = f('nc', U(g4['nc']), 'to Nature’s Classroom, four years', 'published')
    px['pay'] = f('pay', U(g4['pay']), 'in pay, four years', 'published')
    px['exam'] = f('exam', U(g4['exam']), 'to exam boards, four years', 'published')
    px['bus'] = f('bus', U(g4['bus']), 'to bus and limousine companies, four years', 'published')
    px['venue'] = f('venue', U(g4['venue']), 'to hotels and function venues, four years', 'published')
    px['trip'] = f('trip', U(g4['trip']), 'to museums, parks and performers, four years', 'published')
    px['int'] = f('int', U(t[('int', F1)]), 'interest the Town credited the fund, %s' % C.fy(F1),
                  'published', {'y': F(F1)})
    px['named'] = f('named', U(named4), 'deposited under a memo naming a trip, test or prom', 'published')
    px['split'] = f('split', None, 'how much of the income is the student activity fee', 'gap',
                    closes=SPLIT_CLOSES)
    px['bal'] = f('bal', None, 'what the fund held at any year end', 'gap', closes=BALANCE_CLOSES)

    share = 100 * trips / out4
    # what this page counts as spent beyond the Town's own `expended`: payments posted to income
    # accounts and never moved. Positive, or the note under conclusion 3 is wrong
    extra = out4 - four(('town_out',))
    if not extra > 0:
        fail('the page no longer counts more spending than the Town’s report prints')
    trips1 = sum((t[('out', F1, g)] for g in ('nc', 'bus', 'trip', 'venue')), ZERO)
    if not (trips > g4['pay'] > g4['exam'] and trips1 > t[('out', F1, 'pay')]):
        fail('the finding says trips were the largest use, then pay; the figures no longer agree')
    if not out4 > in4:
        fail('conclusion 3 says the fund spent more than it took in')
    concl = [
        con('Over %s the fund spent %s, and %s of it went on trips: the trip, the bus and the venue.'
            % (span, C.usd(out4), C.pct(share, 0)),
            ['nc', 'bus', 'trip', 'venue'], {'s': SP, 'a': U(out4), 'p': P(share)},
            so='Outings are the largest use of what families pay into this fund; pay is the next.',
            notes=[step('Nature’s Classroom alone was %s. Trips are our grouping of the payees, by '
                        'what each organisation is.' % C.usd(g4['nc']), 'measured',
                        {'a': U(g4['nc'])})]),
        con('Pay was %s and exam boards %s; the rest was supplies and smaller payees.'
            % (C.usd(g4['pay']), C.usd(g4['exam'])), ['pay', 'exam'],
            {'a': U(g4['pay']), 'b': U(g4['exam'])},
            so='The fund is not only trips: pay and AP exam fees run through it too.',
            notes=[step('Pay is the Town’s own code, SALARIES REVOLVING FUNDS; who was paid is '
                        'masked, so which posts it paid is not in the journal.', 'measured'),
                   step('The fund also paid an audit firm %s.' % C.usd(g4['audit']), 'measured',
                        {'a': U(g4['audit'])})]),
        con('The fund took in %s over the same years, %s less than it spent.'
            % (C.usd(in4), C.usd(out4 - in4)), ['in', 'out', 'int', 'bal'],
            {'a': U(in4), 'b': U(out4 - in4)},
            so='It spent money it already held as well as what came in; how much it held is unknown.',
            notes=[step('Spent here is %s more than the Town’s report prints expended: bills it '
                        'paid off the income accounts, which that report counts as less income.'
                        % C.usd(extra), 'measured', {'a': U(extra)}),
                   step('The Town credited %s of interest in %s, so the fund held a balance. What '
                        'it held is not in what we have.' % (C.usd(t[('int', F1)]), C.fy(F1)),
                        'gap', {'a': U(t[('int', F1)]), 'y': F(F1)}, closes=BALANCE_CLOSES)]),
        con('Of %s deposited, %s carried a memo naming a trip, a test or a prom.'
            % (C.usd(dep4), C.usd(named4)), ['named', 'split'],
            {'a': U(dep4), 'b': U(named4)},
            so='Some of the income is families paying for one trip or exam; how much is unknown.',
            notes=[step('Most deposits name only the school. The journal posts them in batches, '
                        'so it cannot say how much was the student activity fee.', 'gap',
                        closes=SPLIT_CLOSES)]),
    ]

    xs = [C.fy(y) for y in Y]
    # FIVE TRACKS, a chart's limit: the table below keeps every group apart
    bands = [('Pay', ['pay']), ('Nature’s Classroom', ['nc']),
             ('Other trips, buses and venues', ['trip', 'bus', 'venue']),
             ('Exam boards', ['exam']), ('Everything else', ['audit', 'rest'])]
    if sorted(g for _, gs in bands for g in gs) != sorted(ORDER):
        fail('the chart bands do not hold every group once')
    chart = TP.series('What the fund paid for', xs,
                      [TP.track(n, [fv(sum((t[('out', y, g)] for g in gs), ZERO)) for y in Y],
                                'published') for n, gs in bands],
                      '$', kind='bar', stacked=True,
                      note='Spent: payments plus what is still owed. Payees grouped by what each '
                           'organisation is, our grouping.')
    also = [TP.series('Money in and money out', xs, [
        TP.track('Paid in', [fv(t[('in', y)]) for y in Y], 'published'),
        TP.track('Spent', [fv(t[('out', y)]) for y in Y], 'published')], '$', kind='bar',
        note='Paid in is deposits less refunds, on the income accounts the Town titles by school.'),
        TP.series('Each school, paid in and spent', [n for _, n, _, _ in SCHOOLS], [
            TP.track('Paid in', [fv(four(('in', s))) for s, *_ in SCHOOLS], 'published'),
            TP.track('Spent', [fv(four(('out', s))) for s, *_ in SCHOOLS], 'published')],
            '$', kind='bar',
            note='Four years together. District-wide holds the system-wide pay account.')]

    # ---- the table: who was paid, by year. Named organisations only (the redaction, above)
    cols = [C.fy(y) for y in Y] + ['Four years']
    rows, shown = [], []
    payees = {k[2] for k in t if k[0] == 'payee'}
    for g in ORDER:
        if g in ('pay', 'rest'):
            continue
        for p in sorted((p for p in payees if GROUP_OF[p] == g), key=lambda p: (-four(('payee', p)), p)):
            if four(('payee', p)) < NAMED_MIN:
                continue
            shown.append(p)
            rows.append(dict(label='%s · %s' % (p, LABEL[g]),
                             cells=[C.usd(t[('payee', y, p)]) for y in Y] + [C.usd(four(('payee', p)))]))
    rest = {y: t[('out', y)] - t[('out', y, 'pay')] - sum((t[('payee', y, p)] for p in shown), ZERO)
            for y in Y}
    rows.append(dict(label='Every other payee, people and refunds among them',
                     cells=[C.usd(rest[y]) for y in Y] + [C.usd(sum(rest.values(), ZERO))]))
    rows.append(dict(label='Pay', cells=[C.usd(t[('out', y, 'pay')]) for y in Y] + [C.usd(g4['pay'])]))
    rows.append(dict(label='Every payee', cells=[C.usd(t[('out', y)]) for y in Y] + [C.usd(out4)]))
    if len(rows) > TP.TABLE_ROWS_MAX:
        fail('%d rows; the table holds %d' % (len(rows), TP.TABLE_ROWS_MAX))
    table = dict(caption='Who the fund paid, by year', views=[dict(
        key='payees', label='By payee', total_col=4, kinds=['ledger'] * len(cols), columns=cols,
        rows=rows, note='Organisations paid %s or more over four years, named as the journal '
                        'prints them. People are never named.' % C.usd(NAMED_MIN))])

    page = TP.page(
        TID,
        'The after-school activities fund spent %s in %s. Trips were its largest use, then pay.'
        % (C.usd(t[('out', F1)]), C.fy(F1)),
        list(px.values()), concl, chart=chart, also=also, tables=[table], sources=sources(),
        finding_figures={'a': U(t[('out', F1)]), 'y': F(F1)})
    page['not_established'] = [
        'Whether the student activity fee is paid into this fund at all. The School Committee last '
        'set it at %s on %s; the district also keeps student activity accounts outside the Town’s '
        'books, and the journal cannot say which one the fee reaches.'
        % (C.usd(amount), long_date(fee_date)),
        'What any trip cost a family, or how many children went. The journal holds dollars, '
        'never children.',
        'Which posts the pay paid. The payroll lines carry no name and no position.',
        'What the fund held at the end of any year. A balance is not in the journal.',
        'Whether every activity the schools run passes through this fund. The athletic fee has a '
        'fund of its own (1301).',
    ]
    if [TID] != MINE:
        fail('the registry gives this script %s; it builds %s' % (MINE, [TID]))
    return {TID: page}


def outputs():
    pages = build()
    return {os.path.join(OUT_DIR, '%s.json' % t):
            json.dumps(p, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
            for t, p in pages.items()}


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
        print('after-school activities fund: %d output current' % len(outs))
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
