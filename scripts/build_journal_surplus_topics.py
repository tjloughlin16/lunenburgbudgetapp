#!/usr/bin/env python3
"""The school surplus, read from the MUNIS journal. Four topic pages on the FY2026 closeout shelf.

    python3 scripts/build_journal_surplus_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_journal_surplus_topics.py --check   # fail if either output would change

    surplus-bridge             Surplus by year
    surplus-repeat-lines       Repeat underspending (absorbed Two-year surplus and Surplus
                               suggestions, 27 November 2026)
    budget-burndown            Budget burndown
    fy2026-tuition-paid-early  Year-end tuition entries (the 29 June and 30 June entries; the
                               29 June blocks are built by build_fy2026_school_surplus.entry)

All under /school-all-funds/fy2026-closeout/ (scripts/topic_registry/fy2026_closeout.py; the
method is notes/plans/SCHOOL-SURPLUS-BRIDGE.md).

WHAT THEY READ. `scripts/journal.py` for the lines, the scope (fund 0100, department 300) and
what each line is -- budget, carried-forward orders, other transfers, payroll, invoices,
journal entries, receipts, open orders. The CATEGORIES are `build_school_surplus.py`'s, by
its own `category_of`, so a category here is exactly the category on the published surplus
pages. Nothing is re-decided.

THE SCOPE TIES. Department 300 of the general fund in the journal reproduces the period-13
`gf-school` spreadsheets to the cent on budget, transfers, actuals, open orders and what was
left, in all four years. `verify_journal_surplus_topics.py` recomputes every figure from those
spreadsheets, which is the second route rule 9 asks for.

RULE 7. A posting is a fact. Why a line came in under -- budgeted high, a vacancy, a price
that fell, a cost paid from another fund -- is not in a ledger, and the pages say so.

FY2026 IS NOT CLOSED in this run (journal.OPEN_FY): $236,766.94 of orders were still open.
"""
import argparse
import json
import os
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
import topic_blocks as TB  # noqa: E402
import journal as J  # noqa: E402
import build_school_surplus as S  # noqa: E402

OUT_DIR = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics')
ME = os.path.basename(__file__)
MINE = sorted(t for t, (_, _, gen) in REG.TOPICS.items() if gen == ME)
Y0, Y1 = 2025, 2026          # the two surplus years the published pages cover
CATS = [c[0] for c in S.CATEGORIES]
PIECES = ('original_budget', 'carry_forward', 'transfer', 'payroll', 'invoice',
          'journal entry', 'receipt', 'encumbrance')
ADJ_FY25 = 'ADJ FY25 BUDGET'   # the one July 2024 line that cut FY2025's budget (journal)
# The district's own budget book prints the same figure, on the same account, as the circuit
# breaker offset: `3-12-25-town-manager-39-s-budget.txt` line 298, under 9400 Collaborative
# Tuitions, "Circuit Breaker (70% = $422,408) (75% = 452,580)", -452,580 in the FY2025 column.
# Checked on every build (`book_line`). A match of amount and account, not a stated link: the
# journal entry does not name the circuit breaker.
# Check 218995 as the Munis check register prints it, in the line the district sent on
# 19 November 2026 (sources/correspondence/2026-11-19-check-218995-register-line.png). The
# journal carries only the effective date; this is the date the check was cut. Tied to the
# journal on every build (the twelve lines on the check must sum to `amount`).
BATCH = '5853'   # the school batch holding the nine invoices (same delivery)
CHECK = {'no': '218995', 'date': '2026-07-16', 'amount': Decimal('199364.25'),
         'href': '/docs/correspondence/2026-11-19-check-218995-register-line.png'}
BOOK = '/docs/district-budget/docs/3-12-25-town-manager-39-s-budget.pdf'
BOOK_TEXT = os.path.join(ROOT, 'sources', 'district-budget', 'text',
                         '3-12-25-town-manager-39-s-budget.txt')
BOOK_LINE = 'Circuit Breaker (70% = $422,408) (75% = 452,580)-452,580'
# The reader these pages are written for (notes/process/PERSONAS.md, 8): the Town Manager, who
# asked this in public. Quoted verbatim and checked against our copy on every build.
TM_MINUTES = '/docs/minutes/text/select-board/2025-09-09-minutes-7393.txt'   # our text, for the check
TM_HREF = '/docs/meetings/select-board/2025-09-09-minutes-7393.pdf'          # the town's own document
TM_QUOTE = ('the FY26 budget, which was developed by the prior team, would need to be reviewed '
            'line by line to determine whether the same assumptions that produced the FY25 '
            'surplus are embedded in the current year\'s budget')
# What the Committee heard when the FY2025 figure moved (17 September 2025), checked verbatim.
SC0917_TEXT = os.path.join(ROOT, 'sources', 'meetings', 'text', 'school-committee',
                           '2025-09-17-minutes-7408.txt')
SC0917_QUOTE = ('the surplus number has gone up to $603,885.97, the change is due to closing out '
                'purchase orders from FY25.')
ACCOUNT_ROWS = 30            # accounts listed line by line; the rest are counted, not listed
D0 = Decimal(0)


def fail(msg):
    raise SystemExit('build_journal_surplus_topics: ' + msg)


def sources():
    return [
        dict(label='Lunenburg Budget Project — munis-school-journal.csv (every school journal '
                   'line, FY2023–FY2026, our redacted reading of the Town’s Report 1)',
             href=J.PUBLIC['journal']),
        dict(label='Lunenburg Budget Project — munis-school-journal-accounts.csv (every '
                   'school account, with the FY2026 figures the report prints)',
             href=J.PUBLIC['accounts']),
        dict(label='Town of Lunenburg — how the journal reached us, and what was redacted',
             href='/docs/town-ledgers/account-details/'
                  'PROVENANCE-fy2023-fy2026-p13-school-journal.md'),
    ]


def verbatim():
    book = ' '.join(open(BOOK_TEXT, encoding='utf-8').read().split())
    if BOOK_LINE not in book:
        fail('the circuit breaker line is no longer in %s' % BOOK_TEXT)
    src = os.path.join(ROOT, 'sources', 'meetings', 'text',
                       TM_MINUTES.split('/docs/minutes/text/')[1])
    if TM_QUOTE not in ' '.join(open(src, encoding='utf-8').read().split()):
        fail('the Town Manager quotation is no longer verbatim in %s' % TM_MINUTES)
    if SC0917_QUOTE not in ' '.join(open(SC0917_TEXT, encoding='utf-8').read().split()):
        fail('the 17 September 2025 quotation is no longer verbatim in %s' % SC0917_TEXT)


def cat_of(r):
    return S.category_of(dict(account=r['account'], obj=r['object']))


def data():
    A = J.accounts()
    scope = [r for r in J.lines() if J.in_surplus_scope(A[r['account']])]
    if any(not J.is_expense(A[r['account']]) for r in scope):
        fail('a line in the surplus scope is not on an expense account')
    d = {}
    d['piece'] = {k: v for k, v in J.rollup(scope, 'fy', J.piece).items()}
    for (y, p) in d['piece']:
        if p not in PIECES:
            fail('a line in %d is a %r, which no bridge step holds' % (y, p))
    pc = lambda y, p: d['piece'].get((y, p), D0)
    d['left'] = {y: J.left([r for r in scope if r['fy'] == y]) for y in J.YEARS}
    for y in J.YEARS:
        b = pc(y, 'original_budget') + pc(y, 'carry_forward') + pc(y, 'transfer')
        a = sum(pc(y, p) for p in ('payroll', 'invoice', 'journal entry', 'receipt'))
        if b - a - pc(y, 'encumbrance') != d['left'][y]:
            fail('the pieces of %d do not foot to what was left' % y)
    # Orders closed out of each year (`YEC`) -- the next year's carry-forward, to the cent.
    yec = J.rollup([r for r in scope if r['source'] == 'YEC'], 'fy')
    d['closed'] = {y: -yec.get((y,), D0) for y in J.YEARS}
    for y in J.YEARS[:-1]:
        if d['closed'][y] != pc(y + 1, 'carry_forward'):
            fail('orders closed out of %d are not the carry-forward into %d' % (y, y + 1))
    adj = [r for r in scope if r['source'] == 'BUA' and r['description'] == ADJ_FY25]
    if len(adj) != 1 or adj[0]['fy'] != Y0:
        fail('expected one %r line in FY%d; found %d' % (ADJ_FY25, Y0, len(adj)))
    d['adj'], d['adj_acct'] = adj[0]['amt'], adj[0]['account_description']
    d['adj_date'] = adj[0]['effective_date']
    # Department 301, the rest of the district's own printed total (the settled answers).
    d301 = [r for r in J.lines() if r['fund'] == '0100' and J.department(r['account']) == '301']
    d['left301'] = J.left([r for r in d301 if r['fy'] == Y1])
    # By category: what was left, every year, and each piece.
    d['cat'] = {k: v for k, v in J.rollup(scope, 'fy', cat_of, J.piece).items()}
    d['cat_left'] = defaultdict(lambda: D0)
    d['acct_left'] = defaultdict(lambda: D0)
    for r in scope:
        sgn = 1 if r['posts_to'] in ('original_budget', 'transfer') else -1
        d['cat_left'][(r['fy'], cat_of(r))] += sgn * r['amt']
        d['acct_left'][(r['fy'], cat_of(r), r['account'])] += sgn * r['amt']
    for y in J.YEARS:
        if sum(d['cat_left'][(y, c)] for c in CATS) != d['left'][y]:
            fail('the categories of %d do not foot to what was left' % y)
    d['acct_desc'] = {a: A[a]['account_description'] for (_, _, a) in d['acct_left']}
    return d


def fl(x):
    return float(x)


def usd2(x):
    x = float(x)
    return ('-$' if x < 0 else '$') + format(abs(x), ',.2f')


def build():
    verbatim()
    d = data()
    U = lambda v: figure(fl(v), C.usd(fl(v)))
    U2 = lambda v: figure(fl(v), usd2(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    f, con = LD.fact, TP.conclusion
    pc = lambda y, p: d['piece'].get((y, p), D0)
    out = {}

    # ================================================== surplus-bridge: SURPLUS BY YEAR
    # Rebuilt 26 October 2026, absorbing fy2025-school-surplus (its address opens this page,
    # fy28/src/routes.ts TOPIC_MERGED). The page exists to say ONE thing the printed reports
    # hide: the years are not on the same footing.
    #
    # THE FOOTING. A closed year's close (`YEC`) zeroes the orders still owed, and the next July
    # re-opens them as carried-forward budget (`d['closed']`, asserted to the cent in data()). So
    # a CLOSED year's period-13 report prints what was left BEFORE its open orders. FY2026's was
    # run before its close and prints what was left AFTER them. Set side by side as printed --
    # the hub did, and so did the July minutes -- the two years differ in kind. Both footings are
    # drawn for every year; TJ's site-wide rule ("spent - payments plus owed", journal.py) makes
    # the owed-counted one the lead.
    s0, s1 = d['left'][Y0], d['left'][Y1]
    budget = {y: pc(y, 'original_budget') + pc(y, 'carry_forward') + pc(y, 'transfer')
              for y in (Y0, Y1)}
    spent = {y: sum(pc(y, p) for p in ('payroll', 'invoice', 'journal entry', 'receipt'))
             for y in (Y0, Y1)}
    db, ds = budget[Y1] - budget[Y0], spent[Y1] - spent[Y0]
    dv = lambda p: pc(Y1, p) - pc(Y0, p)
    open1 = pc(Y1, 'encumbrance')
    if pc(Y0, 'encumbrance') != 0:
        fail('FY%d is closed and should hold no open orders' % Y0)
    if not (s1 < s0 and db > ds > 0 and open1 > 0):
        fail('the bridge assumes the printed surplus fell while budget rose more than spending')
    if d['closed'][Y1] != 0:
        fail('FY%d now has a close posted; the footing note says it does not' % Y1)
    owed = {y: d['left'][y] - d['closed'][y] for y in J.YEARS}   # orders owed counted as spent
    printed = {y: d['left'][y] + (open1 if y == Y1 else D0) for y in J.YEARS}  # a closed report's footing
    if not (owed[Y1] < owed[Y0] and printed[Y1] > printed[Y0]):
        fail('the footing conclusion assumes FY%d is below FY%d on one footing and above on '
             'the other' % (Y1, Y0))
    early = J.YEARS[:2]
    if not all(owed[y] < owed[Y0] / 10 for y in early):
        fail('the first conclusion assumes the early years left a small fraction of FY%d' % Y0)
    pay_pct = 100.0 * fl(dv('payroll')) / fl(pc(Y0, 'payroll'))
    inv_pct = 100.0 * fl(dv('invoice')) / fl(pc(Y0, 'invoice'))
    with301 = s1 + d['left301']
    if d['left301'] >= 0:
        fail('the department 301 note assumes the curriculum line ran over')
    closed = [d['closed'][y] for y in J.YEARS[:-1]]
    if not open1 > max(closed):
        fail('the open-orders conclusion assumes FY%d holds more than any closed year' % Y1)
    # FY2025 against what the School Committee was told (the page this absorbed)
    W25 = json.load(open(os.path.join(ROOT, 'fy28', 'public', 'data', 'fy25-school-surplus.json'),
                         encoding='utf-8'))
    if abs(fl(s0) - W25['totals']['available']) > 0.01:
        fail('the journal’s FY%d left is not the period-13 report’s' % Y0)
    told = Decimal(str(W25['waterfall']['district_figure']))
    diff25 = s0 - told
    if diff25 <= 0:
        fail('the FY%d conclusion assumes the ledger shows more than the Committee was told' % Y0)

    fx = {}
    for y in J.YEARS:
        fx['o%d' % y] = f('o%d' % y, U(owed[y]), 'left, %s, counting orders owed'
                          % C.fy(y), 'published', {'y': F(y)})
    fx['p0'] = f('p0', U(printed[Y0]), 'left, %s, as its closed report prints it' % C.fy(Y0),
                 'published', {'y': F(Y0)})
    fx['p1'] = f('p1', U(printed[Y1]), '%s on that footing (our sum)' % C.fy(Y1), 'published',
                 {'y': F(Y1)})
    fx['c0'] = f('c0', U(d['closed'][Y0]), 'owed at the %s close, paid from %s’s budget'
                 % (C.fy(Y0), C.fy(Y1)), 'published', {'y': F(Y0), 'z': F(Y1)})
    fx['open'] = f('open', U(open1), 'still owed on open orders, %s' % C.fy(Y1), 'published',
                   {'y': F(Y1)})
    fx['told'] = f('told', U2(told), 'the %s figure the Committee was given' % C.fy(Y0),
                   'published', {'y': F(Y0)})
    fx['diff'] = f('diff', U(diff25), 'the closed report above that figure (our arithmetic)',
                   'estimate')
    fx['db'] = f('db', U(db), 'more budget in %s than in %s' % (C.fy(Y1), C.fy(Y0)), 'published',
                 {'y': F(Y1), 'z': F(Y0)})
    fx['ds'] = f('ds', U(ds), 'more spent in %s than in %s' % (C.fy(Y1), C.fy(Y0)), 'published',
                 {'y': F(Y1), 'z': F(Y0)})

    yrs_closed = ', '.join(C.usd(fl(v)) for v in closed)
    cat_rows = []
    order = sorted(CATS, key=lambda c: -fl(d['cat_left'][(Y1, c)] - d['cat_left'][(Y0, c)]))
    for c in order:
        g = lambda y, p: d['cat'].get((y, c, p), D0)
        bud = sum(g(Y1, p) - g(Y0, p) for p in ('original_budget', 'carry_forward', 'transfer'))
        eff = lambda ps: -sum(g(Y1, p) - g(Y0, p) for p in ps)
        cat_rows.append(dict(label=S.CAT_LABEL[c], cells=[
            C.usd(fl(d['cat_left'][(Y0, c)])), C.usd(fl(bud)), C.usd(fl(eff(['payroll']))),
            C.usd(fl(eff(['invoice']))), C.usd(fl(eff(['journal entry', 'receipt']))),
            C.usd(fl(eff(['encumbrance']))), C.usd(fl(d['cat_left'][(Y1, c)]))]))
    piece_rows = [dict(label=lab, cells=[C.usd(fl(pc(y, p))) for y in J.YEARS])
                  for p, lab in (('original_budget', 'Original appropriation (BUC)'),
                                 ('carry_forward', 'Encumbrances carried forward (BUA)'),
                                 ('transfer', 'Other transfers and adjustments (BUA)'),
                                 ('payroll', 'Payroll (PRJ, PRH)'),
                                 ('invoice', 'Vendor invoices (API, APM)'),
                                 ('journal entry', 'Journal entries (GEN, GRV)'),
                                 ('receipt', 'Cash receipts credited (CRP)'),
                                 ('encumbrance', 'Open encumbrances'))]
    piece_rows.append(dict(label='Left unspent, as the report prints it',
                           cells=[C.usd(fl(d['left'][y])) for y in J.YEARS]))
    piece_rows.append(dict(label='Owed at the close, carried to next July (YEC)',
                           cells=[C.usd(fl(d['closed'][y])) if y != Y1 else 'not yet closed'
                                  for y in J.YEARS]))
    piece_rows.append(dict(label='Left, counting orders owed',
                           cells=[C.usd(fl(owed[y])) for y in J.YEARS]))

    yspan = figure(J.YEARS[0], C.fyspan(J.YEARS[0], J.YEARS[-1]), 'fiscal years')
    bridge_chart = TP.bridge(
        'From one year’s surplus to the next',
        ('Left, %s, as printed' % C.fy(Y0), fl(s0)),
        [('Original appropriation', fl(dv('original_budget'))),
         ('Encumbrances carried forward', fl(dv('carry_forward'))),
         ('Other transfers and adjustments', fl(dv('transfer'))),
         ('Payroll', -fl(dv('payroll'))),
         ('Vendor invoices', -fl(dv('invoice'))),
         ('Journal entries', -fl(dv('journal entry'))),
         ('Cash receipts credited', -fl(dv('receipt'))),
         ('Open encumbrances', -fl(open1))],
        ('Left, %s, as printed' % C.fy(Y1), fl(s1)), '$',
        note='Each step is the change from %s to %s and its effect on what was left. '
             'School general fund, department 300.' % (C.fy(Y0), C.fy(Y1)),
        note_figures={'y': F(Y0), 'z': F(Y1), 'd': N(int(J.SURPLUS_DEPT), 'department')})
    out['surplus-bridge'] = TP.page(
        'surplus-bridge',
        'Printed, %s left %s less than %s; on one footing it is %s less, on the other %s more.'
        % (C.fy(Y1), C.usd(fl(printed[Y0] - owed[Y1])), C.fy(Y0), C.usd(fl(owed[Y0] - owed[Y1])),
           C.usd(fl(printed[Y1] - printed[Y0]))),
        list(fx.values()),
        [con('Counting orders owed, %s and %s left %s and %s; %s left %s.'
             % (C.fy(early[0]), C.fy(early[1]), C.usd(fl(owed[early[0]])),
                C.usd(fl(owed[early[1]])), C.fy(Y0), C.usd(fl(owed[Y0]))),
             ['o%d' % early[0], 'o%d' % early[1], 'o%d' % Y0],
             {'a': F(early[0]), 'b': F(early[1]), 'c': U(owed[early[0]]),
              'd': U(owed[early[1]]), 'y': F(Y0), 'e': U(owed[Y0])},
             so='Leftovers near zero were the pattern until %s. What changed that year is the '
                'question; the ledger records postings, not reasons.' % C.fy(Y0),
             so_figures={'y': F(Y0)}),
         con('%s’s closed report leaves out %s it still owed; %s’s counts %s owed as spent.'
             % (C.fy(Y0), C.usd(fl(d['closed'][Y0])), C.fy(Y1), C.usd(fl(open1))),
             ['c0', 'open', 'p0', 'o%d' % Y1],
             {'y': F(Y0), 'a': U(d['closed'][Y0]), 'z': F(Y1), 'b': U(open1)},
             so='So the two printed figures are not one measure. On %s’s footing %s is %s, above '
                '%s; counting orders owed, it is below.'
                % (C.fy(Y0), C.fy(Y1), C.usd(fl(printed[Y1])), C.fy(Y0)),
             so_figures={'y': F(Y0), 'z': F(Y1), 'a': U(printed[Y1])},
             notes=[step('Each closed year’s orders came back the next July as budget, to the '
                         'cent: %s. If %s closes the same way, its printed figure rises by what '
                         'is carried or released, up to %s.'
                         % (yrs_closed, C.fy(Y1), C.usd(fl(printed[Y1]))), 'measured',
                         dict({'y': F(Y1), 'a': U(printed[Y1])},
                              **{'c%d' % i: U(v) for i, v in enumerate(closed)})),
                    step('Whether any of the %s will be paid inside %s or carried forward.'
                         % (C.usd(fl(open1)), C.fy(Y1)), 'gap',
                         {'o': U(open1), 'y': F(Y1)},
                         allow=('13',),
                         closes='the Town’s %s period-13 report, run after the close'
                                % C.fy(Y1))]),
         con('From %s to %s the budget grew %s and spending %s: more left before orders.'
             % (C.fy(Y0), C.fy(Y1), C.usd(fl(db)), C.usd(fl(ds))),
             ['db', 'ds', 'p0', 'p1'],
             {'y': F(Y0), 'z': F(Y1), 'a': U(db), 'b': U(ds)},
             so='The budget rose faster than spending did, so more was left before orders. Payroll '
                'was %s of the extra spending.' % C.pct(100.0 * fl(dv('payroll')) / fl(ds), 0),
             so_figures={'p': P(100.0 * fl(dv('payroll')) / fl(ds), 0)},
             notes=[step('Payroll rose %s, %s; vendor invoices %s, %s; journal entries %s.'
                         % (C.usd(fl(dv('payroll'))), C.pct(pay_pct), C.usd(fl(dv('invoice'))),
                            C.pct(inv_pct), C.usd(fl(dv('journal entry')))), 'measured',
                         {'a': U(dv('payroll')), 'p': P(pay_pct), 'b': U(dv('invoice')),
                          'q': P(inv_pct), 'c': U(dv('journal entry'))}),
                    step('%s of %s’s budget change is one line on collaborative tuitions, '
                         '1 July 2024 (ADJ FY25 BUDGET). The district’s budget book prints that '
                         'figure there as the circuit breaker offset; the entry does not say so.'
                         % (C.usd(fl(-d['adj'])), C.fy(Y0)), 'measured',
                         {'a': U(-d['adj']), 'y': F(Y0)}, allow=('1 July 2024', 'FY25'),
                         cite=(BOOK, 'LPS budget book, 12 March 2025, 9400 Collaborative Tuitions'))]),
         con('The Committee was told %s for %s; the closed report shows %s more.'
             % (usd2(told), C.fy(Y0), C.usd(fl(diff25))), ['told', 'diff', 'p0'],
             {'t': U2(told), 'y': F(Y0), 'x': U(diff25)},
             so='A surplus figure moves after it is first reported, so the %s figure the '
                'Committee hears depends on the day the report is run.' % C.fy(Y1),
             so_figures={'y': F(Y1)},
             notes=[step('Entries posted after the September meeting fit; no single account '
                         'or pair of accounts makes up the gap, and this ledger cannot test '
                         'it.', 'hypothesis')])],
        chart=TP.series(
            'What was left at year end, two footings', [C.fy(y) for y in J.YEARS],
            [TP.track('Counting orders owed', [fl(owed[y]) for y in J.YEARS], 'published'),
             TP.track('As a closed year’s report prints it',
                      [fl(printed[y]) if y != Y1 else None for y in J.YEARS], 'published'),
             TP.track('%s, if it closes the same way (our sum)' % C.fy(Y1),
                      [None] * (len(J.YEARS) - 2) + [fl(printed[Y0]), fl(printed[Y1])],
                      'estimate')],
            '$', kind='line',
            note='School general fund, department 300. A closed year’s report leaves out orders '
                 'still owed at its close; they are paid from the next year’s budget.',
            note_figures={'d': N(int(J.SURPLUS_DEPT), 'department')}),
        blocks=[TB.chart(bridge_chart, place='body',
                         so=('Read step by step, the drop as printed is the open orders: '
                             'without them %s ends above %s.' % (C.fy(Y1), C.fy(Y0)),
                             {'y': F(Y1), 'z': F(Y0)}))],
        lead_quote=TP.lead_quote(
            'the approximately $600,000 that had been returned … he was confident the '
            'remaining amount would be well below that figure',
            'Business manager, as the minutes record it', 'School Committee', '2026-07-29',
            '/docs/meetings/school-committee/2026-07-29-minutes-7930.pdf',
            'School Committee minutes, 29 July 2026',
            'sources/meetings/text/school-committee/2026-07-29-minutes-7930.txt'),
        said=[dict(quote=SC0917_QUOTE, board='School Committee', date='2025-09-17',
                   href='/docs/meetings/school-committee/2025-09-17-minutes-7408.pdf',
                   label='School Committee minutes, 17 September 2025')],
        table=dict(caption='The surplus, %s to %s' % (C.fy(Y0), C.fy(Y1)), views=[
            dict(key='pieces', label='Every year', total_col=None,
                 kinds=['ledger'] * len(J.YEARS), columns=[C.fy(y) for y in J.YEARS],
                 rows=piece_rows,
                 note='Budget, less every way money left, less what was still on order. A '
                      'closed year’s close moves its open orders into next July’s budget; %s '
                      'is not yet closed. Department 300 only: department 301 (curriculum '
                      'adoption) ran %s over in %s; with it, %s left. Payroll is per account '
                      'per pay run, never per person.'
                      % (C.fy(J.OPEN_FY), C.usd(fl(-d['left301'])), C.fy(Y1), C.usd(fl(with301)))),
            dict(key='categories', label='By category', total_col=None, kinds=['ledger'] * 7,
                 columns=['Left, %s' % C.fy(Y0), 'Budget', 'Payroll', 'Vendor invoices',
                          'Journal entries', 'Encumbered', 'Left, %s' % C.fy(Y1)],
                 rows=cat_rows,
                 note='Each middle column is that piece’s effect on what was left, as printed; '
                      'negative is spending that rose or budget that fell. Journal entries move '
                      'spending between lines after it is paid.')]),
        sources=sources() + [
            dict(label='Lunenburg School Committee — 2026-07-29-minutes-7930.pdf',
                 href='/docs/meetings/school-committee/2026-07-29-minutes-7930.pdf'),
            dict(label='Lunenburg School Committee — 2025-09-17-minutes-7408.pdf',
                 href='/docs/meetings/school-committee/2025-09-17-minutes-7408.pdf')],
        finding_figures={'z': F(Y1), 'g': U(printed[Y0] - owed[Y1]), 'y': F(Y0),
                         'a': U(owed[Y0] - owed[Y1]), 'b': U(printed[Y1] - printed[Y0])})
    out['surplus-bridge']['not_established'] = [
        'Why any line came in under or over: the journal records postings, not reasons.',
        'How much of the FY2026 orders still open will be paid, carried or cancelled.',
        'Which footing the July 2026 comparison with “the approximately $600,000” used.',
        'Whether any cost moved to a grant or revolving fund.',
    ]

    # ================================================== surplus-repeat-lines: REPEAT UNDERSPENDING
    # 27 November 2026 (T-VPW4S; TJ: "each of the sections is effectively the same"): absorbs
    # Two-year surplus (its two-year chart and its gross-against-net conclusion; two_year()) and
    # Surplus suggestions (how spread out the leftover was; the accounts under every year), whose
    # addresses open this page (fy28/src/routes.ts TOPIC_MERGED). Leads on PERSISTENCE. Left out,
    # because another page owns them: what was left by the end of March (Budget burndown), and
    # building upkeep's leftover and teachers' (Surplus by category).
    cl = d['cat_left']
    both = [c for c in CATS if cl[(Y0, c)] > 0 and cl[(Y1, c)] > 0]
    every = [c for c in CATS if all(cl[(y, c)] > 0 for y in J.YEARS)]
    every.sort(key=lambda c: -sum(cl[(y, c)] for y in J.YEARS))
    e4 = sum(cl[(y, c)] for c in every for y in J.YEARS)
    if not set(every) <= set(both):
        fail('a category under every year must be under in both')
    # Line by line: every account, by its MUNIS number -- the Town Manager's grain.
    al = defaultdict(lambda: D0)
    for (y, _, a), v in d['acct_left'].items():
        al[(y, a)] += v
    accts = sorted({a for (_, a) in al})
    under = lambda a, y: al[(y, a)] > Decimal('0.005')
    a_both = sorted([a for a in accts if under(a, Y0) and under(a, Y1)],
                    key=lambda a: (-(al[(Y0, a)] + al[(Y1, a)]), a))
    a_every = {a for a in accts if all(under(a, y) for y in J.YEARS)}
    ab1 = sum(al[(Y1, a)] for a in a_both)
    shown = a_both[:ACCOUNT_ROWS]
    sh_share = 100.0 * fl(sum(al[(y, a)] for a in shown for y in (Y0, Y1))) / fl(
        sum(al[(y, a)] for a in a_both for y in (Y0, Y1)))
    if not (len(a_every) < len(a_both) and a_every <= set(a_both)):
        fail('the accounts conclusion says fewer accounts left money every year than in both')
    # How spread out each year's leftover was (from Surplus suggestions).
    s25 = spread([al[(Y0, a)] for a in accts])
    s26 = spread([al[(Y1, a)] for a in accts])
    top25 = 100.0 * fl(s25['top']) / fl(s25['total'])
    top26 = 100.0 * fl(s26['top']) / fl(s26['total'])
    if s26['v'][0] != al[(Y1, PRIVATE)]:
        fail('private tuition is no longer FY2026’s largest leftover; the page says it is')
    if not (s25['top'] < s25['total'] / 10 and top26 > 3 * top25):
        fail('the spread conclusion says FY2025 was spread thin and FY2026 concentrated')
    # The two years together (from Two-year surplus).
    tw = two_year(d)
    lines2, cats2 = tw['lines'], tw['cats']
    under2 = sum(r['both'] for r in lines2 if r['both'] > 0)
    over2 = -sum(r['both'] for r in lines2 if r['both'] < 0)
    if abs(round(under2 - over2, 2) - tw['total']) > 0.01:
        fail('lines under and over no longer net to the two-year surplus')
    top2 = sum(r['both'] for r in lines2[:TOP_LINES])
    if not top2 > tw['total']:
        fail('the page says the lines that left most left more than the two-year surplus')
    priv = next(r for r in lines2 if r['account'] == PRIVATE)
    coll = next(r for r in lines2 if r['account'] == COLLAB)
    tu = next(c for c in cats2 if c['key'] == 'tuition')
    if abs(priv['both'] + coll['both'] - tu['both']) > 0.01:
        fail('private and collaborative no longer make up the tuition category')
    yspan = C.fyspan(J.YEARS[0], J.YEARS[-1])
    YS = lambda: figure(J.YEARS[0], yspan, 'fiscal years')

    rx = {}
    rx['e'] = f('e', N(len(every), 'categories'), 'under budget every year, %s' % yspan,
                'published', {'y': YS()})
    rx['e4'] = f('e4', U(e4), 'they left over the four years', 'published')
    rx['an'] = f('an', N(len(a_both), 'accounts'), 'of %s left money both years'
                 % C.num(len(accts)), 'published', {'n': N(len(accts), 'accounts')})
    rx['ab1'] = f('ab1', U(ab1), 'those accounts left, %s' % C.fy(Y1), 'published',
                  {'y': F(Y1)})
    rx['ae'] = f('ae', N(len(a_every), 'accounts'), 'left money every year, %s' % yspan,
                 'published', {'y': YS()})
    rx['why'] = f('why', None, 'whether budgeted high or run lean', 'gap',
                  closes='the district’s line-by-line budget build-up, with the basis for '
                         'each amount')
    rx['u2'] = f('u2', U(under2), 'left on lines under budget, %s and %s (our sum)'
                 % (C.fy(Y0), C.fy(Y1)), 'published', {'y': F(Y0), 'z': F(Y1)})
    rx['o2'] = f('o2', U(over2), 'spent past budget on the other lines', 'published')
    rx['t2'] = f('t2', U(top2), 'left on the %s lines that left most' % C.num(TOP_LINES),
                 'published', {'n': N(TOP_LINES)})
    rx['n25'] = f('n25', N(s25['n'], 'accounts'), 'left money in %s' % C.fy(Y0), 'published',
                  {'y': F(Y0)})
    rx['top'] = f('top', P(top25, 0), 'of it on the largest one', 'published')
    rx['t26'] = f('t26', P(top26, 0), 'of %s’s on private tuition' % C.fy(Y1), 'published',
                  {'y': F(Y1)})
    labels_every = [S.CAT_SHORT[c] for c in every]
    listing = ', '.join(labels_every[:-1]) + ' and ' + labels_every[-1]
    shown2 = sorted([c for c in cats2 if c['key'] != 'tuition']
                    + [dict(label='Private tuition', both=priv['both']),
                       dict(label='Collaborative tuition', both=coll['both'])],
                    key=lambda c: -c['both'])
    hrefs = {c['label']: REG.path(PAGE_OF[c['key']]) for c in cats2 if c['key'] in PAGE_OF
             and c['key'] != 'tuition'}
    hrefs.update({k: REG.path('fy2026-tuition-lines')
                  for k in ('Private tuition', 'Collaborative tuition')})
    two_chart = TP.ranking(
        'Left unspent over two years, by category',
        [(c['label'], c['both']) for c in shown2], '$', hrefs=hrefs,
        note='%s and %s added, school general fund. %s counts orders owed at its close as spent, '
             'as %s does. Below zero is past budget.' % (C.fy(Y0), C.fy(Y1), C.fy(Y0), C.fy(Y1)),
        note_figures={'a': F(Y0), 'b': F(Y1)})
    spread_chart = TP.parts(
        'How spread out the leftover was',
        [('Largest %s accounts' % C.num(s25['half']), fl(sum(s25['v'][:s25['half']], D0))),
         ('Next %s' % C.num(s25['most'] - s25['half']),
          fl(sum(s25['v'][s25['half']:s25['most']], D0))),
         ('The other %s' % C.num(s25['n'] - s25['most']), fl(sum(s25['v'][s25['most']:], D0)))],
        '$',
        note='%s, the accounts that came in under budget, by how much each left. %s, because '
             'nothing in it ran over to offset it.' % (C.fy(Y0), C.fy(Y0)),
        note_figures={'y': F(Y0)})
    rl_sources = [dict(s, key=k) for s, k in zip(sources(), ('journal', 'accounts', 'provenance'))]
    import build_fy2026_closeout_topics as CT   # sources only; CT imports nothing of ours at top
    ct = CT.sources()
    rl_sources += [dict(ct[k], key=k) for k in P13]
    rl_sources += [
        dict(key='tm', label='Town of Lunenburg — Select Board minutes, 9 September 2025',
             href=TM_HREF)]
    cite = TP.cite
    out['surplus-repeat-lines'] = TP.page(
        'surplus-repeat-lines',
        '%s budget areas came in under every year from %s to %s; %s of %d did in both %s and %s.'
        % (C.num(len(every)), C.fy(J.YEARS[0]), C.fy(J.YEARS[-1]), C.num(len(both)), len(CATS),
           C.fy(Y0), C.fy(Y1)),
        list(rx.values()),
        [con('Over those four years, the %s areas left %s between them.'
             % (C.num(len(every)), C.usd(fl(e4))),
             ['e', 'e4'],
             {'n': N(len(every), 'categories'), 'a': U(e4)},
             so='These areas ran under four years running, so each next budget has a record of '
                'years to be set against, not one year’s result.',
             notes=[step('They are %s.' % listing, 'measured')]),
         con('Lines under budget left %s over %s and %s; lines past budget used %s of it.'
             % (C.usd(fl(under2)), C.fy(Y0), C.fy(Y1), C.usd(fl(over2))), ['u2', 'o2', 't2'],
             {'u': U(under2), 'y': F(Y0), 'z': F(Y1), 'o': U(over2)},
             so='The %s lines that left most left %s, more than the two years’ whole surplus, so '
                'the total hides the slack.' % (C.num(TOP_LINES), C.usd(fl(top2))),
             so_figures={'n': N(TOP_LINES), 't': U(top2)}),
         con('Line by line, %s of %s accounts left money in both years; %s did in all four.'
             % (C.num(len(a_both)), C.num(len(accts)), C.num(len(a_every))),
             ['an', 'ae', 'ab1', 'why'],
             {'n': N(len(a_both), 'accounts'), 'm': N(len(accts), 'accounts'),
              'e': N(len(a_every), 'accounts')},
             so='The pattern holds at the grain the Town Manager named in public, line by line, not '
                'only in category totals.',
             notes=[step('In %s the accounts under both years left %s. The table lists the %s '
                         'that left the most, %s of their money, by account number.'
                         % (C.fy(Y1), C.usd(fl(ab1)), C.num(len(shown)), C.pct(sh_share, 0)),
                         'measured',
                         {'y': F(Y1), 'a': U(ab1), 'n': N(len(shown), 'accounts'),
                          'p': P(sh_share, 0)}),
                    step('An account budgeted high and one run lean leave the same postings; '
                         'the journal cannot tell them apart.', 'hypothesis')]),
         con('%s’s leftover was spread over %s accounts, the largest %s; in %s private tuition held %s.'
             % (C.fy(Y0), C.num(s25['n']), C.pct(top25, 0), C.fy(Y1), C.pct(top26, 0)),
             ['n25', 'top', 't26'],
             {'y': F(Y0), 'n': N(s25['n'], 'accounts'), 'p': P(top25, 0), 'z': F(Y1),
              'q': P(top26, 0)},
             so='No single line explains %s, so a remedy aimed at one account would leave most of '
                'it in place; %s is the opposite case.' % (C.fy(Y0), C.fy(Y1)),
             so_figures={'y': F(Y0), 'z': F(Y1)},
             notes=[step('Half of %s’s sat on %s accounts and four fifths on %s.'
                         % (C.fy(Y0), C.num(s25['half']), C.num(s25['most'])), 'measured',
                         {'y': F(Y0), 'a': N(s25['half'], 'accounts'),
                          'b': N(s25['most'], 'accounts')})])],
        chart=TP.ranking('Under budget every year, by area',
                         [(S.CAT_LABEL[c], [fl(cl[(y, c)]) for y in J.YEARS]) for c in every],
                         '$', stack=[C.fy(y) for y in J.YEARS],
                         note='Left unspent each year, net of accounts in the area that ran over. '
                              '%s is not yet closed.' % C.fy(Y1),
                         note_figures={'y': F(Y1)}),
        also=[two_chart, spread_chart],
        said=[dict(quote=TM_QUOTE, board='Select Board', date='2025-09-09', href=TM_HREF,
                   label='Select Board minutes, 9 September 2025, Town Manager’s report')],
        table=dict(caption='Left unspent, line by line and by category', views=[dict(
            key='accounts', label='Accounts, both years', total_col=None,
            kinds=['ledger'] * 5,
            columns=['Account', C.fy(Y0), C.fy(Y1), 'Both years', 'Every year since %s'
                     % C.fy(J.YEARS[0])],
            rows=[dict(label=d['acct_desc'][a].title(), cells=[
                a, C.usd(fl(al[(Y0, a)])), C.usd(fl(al[(Y1, a)])),
                C.usd(fl(al[(Y0, a)] + al[(Y1, a)])), 'yes' if a in a_every else 'no'])
                for a in shown],
            note='MUNIS account numbers, general fund department 300; left unspent is the '
                 'available budget at period 13, %s before its close. Accounts in one category '
                 'can offset: tuition accounts ran far under and far over.' % C.fy(Y1)), dict(
            key='years', label='Every category', total_col=None,
            kinds=['ledger'] * (len(J.YEARS) + 1),
            columns=[C.fy(y) for y in J.YEARS] + ['Years under'],
            rows=[dict(label=S.CAT_LABEL[c],
                       cells=[C.usd(fl(cl[(y, c)])) for y in J.YEARS]
                       + ['%d of %d' % (sum(cl[(y, c)] > 0 for y in J.YEARS), len(J.YEARS))])
                  for c in sorted(CATS, key=lambda c: (-sum(cl[(y, c)] > 0 for y in J.YEARS),
                                                       -fl(cl[(Y0, c)] + cl[(Y1, c)])))],
            note='Net of accounts in the category that ran over; a negative figure is a '
                 'category over budget. Categories as on the surplus pages.')]),
        sources=rl_sources,
        flow=['finding',
              cite(('chart', 0), 'journal', *P13), ('conclusion', 0),
              cite(('chart', 1), 'journal', 'p13-26', 'p13-25', 'accounts'), ('conclusion', 1),
              cite(('table', 0), 'journal', 'accounts', 'tm', *P13), ('conclusion', 2),
              cite(('chart', 2), 'journal', 'provenance', 'p13-25'), ('conclusion', 3),
              'said', 'sources'],
        finding_figures={'n': N(len(both), 'categories'), 'm': N(len(CATS), 'categories'),
                         'y': F(Y0), 'z': F(Y1), 'e': N(len(every), 'categories'),
                         'f': F(J.YEARS[0]), 'g': F(J.YEARS[-1])})
    out['surplus-repeat-lines']['not_established'] = [
        'Whether a category under budget every year was budgeted high, run lean, or paid in '
        'part from another fund.',
        'Why any one account left money: the journal records postings, not reasons.',
        'The FY2026 figures after the close.',
    ]

    out.update(burndown_pages())
    out[PREPAID] = prepaid_page(d)
    if sorted(out) != MINE:
        fail('the pages built are not the pages the registry gives this script: %s vs %s'
             % (sorted(out), MINE))
    return out, d


# ================================================== the two years together
# From build_two_year_surplus.py, retired 27 November 2026 (T-VPW4S) when Two-year surplus folded
# into Repeat underspending. TJ, 26 November 2026: "look at the COMBINED surpluses from FY25 and
# FY26, totalling in all cateogires, to say what lines have the most unspent amounts."
#
# ONE FOOTING FOR BOTH YEARS. FY2025's closed report leaves out the orders it still owed at its
# close (re-opened in FY2026 as carried-forward budget); FY2026's report counts its open orders as
# spent. So FY2025 is counted the way FY2026 is -- each account's period-13 leftover less the
# orders closed out of it (the journal's YEC lines) -- the footing Surplus by year and the hub use.
PAY = os.path.join(ROOT, 'fy28', 'public', 'data', 'fy%d-school-surplus.json')
P13 = ('p13-26', 'p13-25', 'p13-24', 'p13-23')
PRIVATE = '0100-3-300-9300-51-1-06-2-535019'    # general fund private (out-of-district) tuition
TOP_LINES = 10            # lines in the "left most" sum
# Categories with a page of their own, linked from the two-year chart.
PAGE_OF = {'paras': 'fy2026-staff-lines', 'counselors': 'fy2026-staff-lines',
           'tuition': 'fy2026-tuition-lines', 'transport': 'special-education-transportation'}


def two_year(d):
    """FY2025 and FY2026 on one footing, by category and by account: dict(total, owed, cats,
    lines), every list sorted by what the two years left, largest first."""
    YRS = (Y0, Y1)
    A = J.accounts()
    scope = [r for r in J.lines() if J.in_surplus_scope(A[r['account']])]
    yec_a, yec_c = defaultdict(lambda: D0), defaultdict(lambda: D0)
    for r in scope:
        if r['source'] == 'YEC' and r['fy'] == Y0:
            yec_a[r['account']] -= r['amt']
            yec_c[cat_of(r)] -= r['amt']
    if sum(yec_a.values(), D0) != d['closed'][Y0]:
        fail('the orders closed out of FY%d, by account, no longer sum to the carry-forward' % Y0)
    owed = {Y0: d['left'][Y0] - d['closed'][Y0], Y1: d['left'][Y1]}
    acct = defaultdict(lambda: {y: D0 for y in YRS})
    for (y, c, a), v in d['acct_left'].items():
        if y in YRS:
            acct[a][y] += v - (yec_a.get(a, D0) if y == Y0 else D0)
    cat = defaultdict(lambda: {y: D0 for y in YRS})
    for (y, c), v in d['cat_left'].items():
        if y in YRS:
            cat[c][y] += v - (yec_c.get(c, D0) if y == Y0 else D0)
    for y in YRS:
        if sum(v[y] for v in acct.values()) != owed[y] or sum(v[y] for v in cat.values()) != owed[y]:
            fail('FY%d accounts or categories no longer sum to what was left, same footing' % y)
    total = owed[Y0] + owed[Y1]
    hub = json.dumps(json.load(open(os.path.join(OUT_DIR, 'fy2026-closeout.json'),
                                    encoding='utf-8')), ensure_ascii=False)
    for y in YRS:
        if C.usd(fl(owed[y])) not in hub:
            fail('the hub no longer states FY%d as %s' % (y, C.usd(fl(owed[y]))))
    label = {}
    for y in YRS:
        for c in json.load(open(PAY % (y % 100), encoding='utf-8'))['causes']['categories']:
            label[c['key']] = c['label']
    if set(cat) - set(label):
        fail('a category in the journal has no label in the surplus payloads')
    r2 = lambda x: round(fl(x), 2)
    cats = sorted([dict(key=k, label=label[k], both=r2(v[Y0] + v[Y1]))
                   for k, v in cat.items() if v[Y0] or v[Y1]], key=lambda c: -c['both'])
    lines = sorted([dict(account=a, both=r2(v[Y0] + v[Y1])) for a, v in acct.items()],
                   key=lambda r: -r['both'])
    return dict(total=r2(total), owed={y: r2(owed[y]) for y in YRS}, cats=cats, lines=lines)


def spread(left_by_account):
    """How spread out a leftover is: (accounts under, the largest, accounts holding half,
    accounts holding four fifths), over the accounts that came in under."""
    v = sorted((x for x in left_by_account if x > 0), reverse=True)
    tot, run, half, most = sum(v, D0), D0, None, None
    for i, x in enumerate(v, 1):
        run += x
        half = half or (i if run >= tot / 2 else None)
        most = most or (i if run >= tot * Decimal('0.8') else None)
    return dict(n=len(v), total=tot, top=v[0], half=half, most=most, v=v)


# ================================================== the burndowns
# TJ, 20 October 2026: "create a burndown chart for each year to see how they burn down, where
# they burn down, and that can show us what isnt burned down. that can also be used to see where
# special education costs come in surprisingly, how much, and when."
#
# WHAT IS DRAWN. The share of the year's FINAL budget (original appropriation plus every
# transfer posted in the year) not yet SPENT at the end of each month: actuals only, so an open
# purchase order is not spending. MUNIS period 1 is July and 12 is June; period 13 posts no
# actual in any of the four years (asserted), so June is the last point. Nothing here is an
# "ideal" straight line: payroll runs September to June, and the honest baseline is the shape
# of the other years.
MONTHS = ('Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun')
X = ['Start'] + list(MONTHS)
MARCH, DECEMBER, SEPTEMBER, JUNE = 9, 6, 3, 12
BASE = J.YEARS[:-1]          # OUR baseline for "usual pace": the three closed years, averaged
CB_BOOK = '-452,580 -480,204'   # FY2025 and FY2026 columns of the circuit breaker line


def curves(rows, key):
    """(budget, cumulative actual by period 0-12) per key(line), from journal lines."""
    bud, act = defaultdict(lambda: D0), defaultdict(lambda: D0)
    for r in rows:
        k = key(r)
        if r['posts_to'] in ('original_budget', 'transfer'):
            bud[k] += r['amt']
        elif r['posts_to'] == 'actual':
            if int(r['period']) == 13 and r['amt']:
                fail('a period-13 actual exists in %d; the burndown stops at June' % r['fy'])
            act[(k, int(r['period']))] += r['amt']
    cum = {}
    for k in bud:
        c = D0
        for p in range(0, 13):
            c += act[(k, p)]
            cum[(k, p)] = c
    return bud, cum


def left_pct(bud, cum, k, p):
    return 100.0 * (1 - fl(cum[(k, p)]) / fl(bud[k])) if bud[k] else None


def burndown_pages():
    book = ' '.join(open(BOOK_TEXT, encoding='utf-8').read().split())
    if BOOK_LINE + ' ' + CB_BOOK.split(' ', 1)[1] not in book:
        fail('the FY2026 circuit breaker offset is no longer printed in %s' % BOOK_TEXT)
    A = J.accounts()
    U = lambda v: figure(fl(v), C.usd(fl(v)))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    f, con = LD.fact, TP.conclusion
    pc = lambda v: C.pct(v, 1)
    gf = [r for r in J.lines() if J.in_surplus_scope(A[r['account']])]
    out = {}

    # ---------------------------------------------- budget-burndown
    bud, cum = curves(gf, lambda r: r['fy'])
    L = {(y, p): left_pct(bud, cum, y, p) for y in J.YEARS for p in range(13)}
    cb, cc = curves(gf, lambda r: (r['fy'], cat_of(r)))
    Lc = {(y, c, p): left_pct(cb, cc, (y, c), p) for y in J.YEARS for c in CATS for p in range(13)
          if cb[(y, c)]}
    m26, m_lo = L[(Y1, MARCH)], max(L[(y, MARCH)] for y in J.YEARS[:2])
    if not m26 > m_lo:
        fail('the first conclusion assumes FY%d had more left in March than FY2023-FY2024' % Y1)
    late = {y: L[(y, MARCH)] - L[(y, JUNE)] for y in J.YEARS}
    ahead = {}
    for c in CATS:
        if (Y1, c, MARCH) not in Lc or not all((y, c, MARCH) in Lc for y in BASE):
            continue
        avg = sum(Lc[(y, c, MARCH)] for y in BASE) / len(BASE)
        ahead[c] = (Lc[(Y1, c, MARCH)] - avg, avg, (Lc[(Y1, c, MARCH)] - avg) / 100 * fl(cb[(Y1, c)]))
    # Health insurance and benefits are posted mostly by June journal entries, so a March gap
    # on them is WHEN they are booked, not money left over; the category is named on the page
    # and kept out of the "behind and still unspent" pick, which needs both.
    POSTED_IN_JUNE = 'benefits'
    hi = ahead[POSTED_IN_JUNE]
    if not Lc[(Y1, POSTED_IN_JUNE, JUNE)] < 5:
        fail('the note assumes benefits caught up by June')
    lead = max((c for c in ahead if c != POSTED_IN_JUNE and Lc[(Y1, c, JUNE)] > 10),
               key=lambda c: ahead[c][2])
    lg = ahead[lead]
    if not 28 < Lc[(Y1, lead, JUNE)] < 100 / 3:
        fail('the meaning says %s had almost a third left in June' % lead)
    bx = {}
    bx['m23'] = f('m23', P(L[(2023, MARCH)]), 'of the budget left at end of March, %s' % C.fy(2023),
                  'published', {'y': F(2023)})
    bx['m24'] = f('m24', P(L[(2024, MARCH)]), 'left at end of March, %s' % C.fy(2024),
                  'published', {'y': F(2024)})
    bx['m25'] = f('m25', P(L[(2025, MARCH)]), 'left at end of March, %s' % C.fy(2025),
                  'published', {'y': F(2025)})
    bx['m26'] = f('m26', P(m26), 'left at end of March, %s' % C.fy(Y1), 'published', {'y': F(Y1)})
    bx['j23'] = f('j23', P(L[(2023, JUNE)], 1), 'left unspent at end of June, %s' % C.fy(2023),
                  'published', {'y': F(2023)})
    bx['j26'] = f('j26', P(L[(Y1, JUNE)], 1), 'left unspent at end of June, %s' % C.fy(Y1),
                  'published', {'y': F(Y1)})
    bx['late23'] = f('late23', P(late[2023]), 'of the budget spent April to June, %s' % C.fy(2023),
                     'published', {'y': F(2023)})
    bx['late26'] = f('late26', P(late[Y1]), 'of the budget spent April to June, %s' % C.fy(Y1),
                     'published', {'y': F(Y1)})
    bx['lead'] = f('lead', P(Lc[(Y1, lead, MARCH)]), '%s left in March, %s' % (S.CAT_SHORT[lead],
                   C.fy(Y1)), 'published', {'y': F(Y1)})
    bx['leadu'] = f('leadu', P(lg[1]), '%s, usual in March' % S.CAT_SHORT[lead], 'estimate')
    bx['leadj'] = f('leadj', P(Lc[(Y1, lead, JUNE)]), '%s left in June, %s' % (S.CAT_SHORT[lead],
                    C.fy(Y1)), 'published', {'y': F(Y1)})
    cat_rows = []
    for c in sorted(ahead, key=lambda c: -ahead[c][2]):
        cat_rows.append(dict(label=S.CAT_LABEL[c], cells=[
            pc(Lc[(Y1, c, SEPTEMBER)]), pc(Lc[(Y1, c, DECEMBER)]), pc(Lc[(Y1, c, MARCH)]),
            pc(ahead[c][1]), C.usd(ahead[c][2]), pc(Lc[(Y1, c, JUNE)])]))
    out['budget-burndown'] = TP.page(
        'budget-burndown',
        'By the end of March %s had %s of its budget left, against %s and %s in %s and %s.'
        % (C.fy(Y1), pc(m26), pc(L[(2023, MARCH)]), pc(L[(2024, MARCH)]), C.fy(2023), C.fy(2024)),
        list(bx.values()),
        [con('At the end of March, %s had %s of its budget left; %s had %s.'
             % (C.fy(Y1), pc(m26), C.fy(2025), pc(L[(2025, MARCH)])),
             ['m23', 'm24', 'm25', 'm26'],
             {'y': F(Y1), 'a': P(m26), 'z': F(2025), 'b': P(L[(2025, MARCH)])},
             so='From February the last two years spent more slowly than the two before; by spring '
                'the monthly report already showed a surplus forming.',
             notes=[step('The four years track together through January; the gap opens in '
                         'February.', 'measured'),
                    step('Against the usual pace, about %s of %s’s March gap is health insurance and benefits, posted '
                         'mostly by June journal entries; by June %s of them was left.'
                         % (C.usd(hi[2]), C.fy(Y1), pc(Lc[(Y1, POSTED_IN_JUNE, JUNE)])),
                         'estimate', {'a': U(hi[2]), 'y': F(Y1),
                                      'b': P(Lc[(Y1, POSTED_IN_JUNE, JUNE)])})]),
         con('April to June then spent %s of %s’s budget, against %s in %s.'
             % (pc(late[Y1]), C.fy(Y1), pc(late[2023]), C.fy(2023)),
             ['late23', 'late26'],
             {'a': P(late[Y1]), 'y': F(Y1), 'b': P(late[2023]), 'z': F(2023)},
             so='Over a third of a year’s budget is spent in its last quarter, so a March balance '
                'alone overstates what will be left.',
             notes=[step('June carries the year-end journal entries, which move spending '
                         'between lines and months.', 'measured')]),
         con('June ended with %s unspent in %s, against %s in %s.'
             % (pc(L[(Y1, JUNE)]), C.fy(Y1), pc(L[(2023, JUNE)]), C.fy(2023)),
             ['j23', 'j26'],
             {'a': P(L[(Y1, JUNE)]), 'y': F(Y1), 'b': P(L[(2023, JUNE)]), 'z': F(2023)},
             so='On payments alone %s kept over five times %s’s share at June; the orders still '
                'open are the rest, on Surplus by year.' % (C.fy(Y1), C.fy(2023)),
             so_figures={'y': F(Y1), 'z': F(2023)},
             notes=[step('Spending only: %s’s open purchase orders are not counted until paid.'
                         % C.fy(Y1), 'measured', {'y': F(Y1)})]),
         con('%s had %s left in March against a usual %s, and still %s in June.'
             % (S.CAT_LABEL[lead], pc(Lc[(Y1, lead, MARCH)]), pc(lg[1]), pc(Lc[(Y1, lead, JUNE)])),
             ['lead', 'leadu', 'leadj'],
             {'a': P(Lc[(Y1, lead, MARCH)]), 'b': P(lg[1]), 'c': P(Lc[(Y1, lead, JUNE)])},
             so='No other area was further behind its usual March pace in dollars, and it still '
                'had almost a third of its budget left in June.',
             notes=[step('Usual is our average of %s to %s at the same month; the usual pace '
                         'in dollars is in the table.' % (C.fy(BASE[0]), C.fy(BASE[-1])),
                         'estimate', {'a': F(BASE[0]), 'b': F(BASE[-1])})])],
        chart=TP.series('Budget left, month by month', X, [
            TP.track(C.fy(y), [round(L[(y, p)], 1) for p in range(13)], 'published', 'line')
            for y in J.YEARS], '%', decimals=1,
            note='Share of each year’s final budget not yet spent. General fund, department '
                 '300. Open purchase orders are not spending.',
            note_figures={'d': N(int(J.SURPLUS_DEPT), 'department')}),
        table=dict(caption='Where %s’s budget was still unspent' % C.fy(Y1), views=[dict(
            key='categories', label='By category', total_col=None, kinds=['ledger'] * 4
            + ['estimate', 'ledger'],
            columns=['Left, Sep', 'Left, Dec', 'Left, Mar', 'Usual, Mar', 'Ahead of usual, Mar',
                     'Left, Jun'],
            rows=cat_rows,
            note='Share of each category’s final %s budget not yet spent. Usual is our average '
                 'of %s to %s; ahead of usual is that gap applied to the %s budget.'
                 % (C.fy(Y1), C.fy(BASE[0]), C.fy(BASE[-1]), C.fy(Y1)))]),
        sources=sources(),
        finding_figures={'y': F(Y1), 'a': P(m26), 'b': P(L[(2023, MARCH)]),
                         'c': P(L[(2024, MARCH)]), 'f': F(2023), 'g': F(2024)})
    out['budget-burndown']['not_established'] = [
        'Why spending ran slower from the winter: a vacancy, a late invoice and a cost moved '
        'to another fund look the same in a month’s postings.',
        'The FY2026 figures after the close.',
    ]

    # ---------------------------------------------- sped-burndown
    sp = [r for r in gf if J.in_sped_total(A[r['account']])]
    sb, sc = curves(sp, lambda r: r['fy'])
    S_ = {(y, p): left_pct(sb, sc, y, p) for y in J.YEARS for p in range(13)}
    kb, kc = curves(sp, lambda r: (r['fy'], J.component(A[r['account']])))
    comps = [c for c, _, inn, _ in J.COMPONENTS if inn and kb[(Y1, c)]]
    K = {(y, c, p): left_pct(kb, kc, (y, c), p) for y in J.YEARS for c in comps for p in range(13)
         if kb[(y, c)]}
    # every fund, month by month
    monthly = defaultdict(lambda: D0)
    for r in J.sped_actuals():
        monthly[(r['fy'], J.sped_fund(A[r['account']]), int(r['period']))] += r['amt']
    # Two buckets a year, never a month: one month of the circuit breaker can hold a single
    # masked parent reimbursement (FY2026 November), and a bar of it would isolate that family.
    early = {y: sum(fl(monthly[(y, 'Circuit breaker', p)]) for p in range(1, JUNE)) for y in J.YEARS}
    june = {y: fl(monthly[(y, 'Circuit breaker', JUNE)]) for y in J.YEARS}
    jr = [r for r in J.sped_actuals() if r['fy'] == Y1 and int(r['period']) == JUNE
          and J.sped_fund(A[r['account']]) == 'Circuit breaker']
    if len(jr) != 1 or J.KIND_OF[jr[0]['source']] != 'journal entry' \
            or 'COLLABORATIVE' not in jr[0]['description']:
        fail('the finding assumes FY%d’s June circuit breaker is one collaborative tuition entry' % Y1)
    if not early[Y1] < 0.05 * early[Y0]:
        fail('the finding assumes almost nothing was paid before June in FY%d' % Y1)
    cb_june = june[Y1]
    gfm = lambda y, ps: sum(monthly[(y, 'General fund', p)] for p in ps)
    so = {y: gfm(y, (3, 4)) for y in (Y0, Y1)}
    con_dec, con_jun = K[(Y1, 'contracted', DECEMBER)], K[(Y1, 'contracted', JUNE)]
    t_dec = {y: 100 - K[(y, 'tuition', DECEMBER)] for y in (Y0, Y1)}
    if not (con_jun < 0 and so[Y1] > so[Y0] and t_dec[Y1] > t_dec[Y0]):
        fail('the special education conclusions no longer match the data')
    sx = {}
    sx['cb0'] = f('cb0', U(early[Y0]), 'circuit breaker, July to May, %s' % C.fy(Y0),
                  'published', {'y': F(Y0)})
    sx['cb1'] = f('cb1', U(early[Y1]), 'circuit breaker, July to May, %s' % C.fy(Y1),
                  'published', {'y': F(Y1)})
    sx['cbj'] = f('cbj', U(cb_june), 'circuit breaker, June, one entry', 'published')
    sx['off'] = f('off', U(480204), 'tuition budget set lower for circuit breaker', 'published')
    sx['so0'] = f('so0', U(so[Y0]), 'general fund, Sep and Oct, %s' % C.fy(Y0), 'published',
                  {'y': F(Y0)})
    sx['so1'] = f('so1', U(so[Y1]), 'general fund, Sep and Oct, %s' % C.fy(Y1), 'published',
                  {'y': F(Y1)})
    sx['cd'] = f('cd', P(con_dec, 0), 'contracted services budget left, December', 'published')
    sx['cj'] = f('cj', P(-con_jun, 0), 'contracted services over budget, June', 'published')
    sx['t0'] = f('t0', P(t_dec[Y0], 0), 'tuition budget spent by December, %s' % C.fy(Y0),
                 'published', {'y': F(Y0)})
    sx['t1'] = f('t1', P(t_dec[Y1], 0), 'tuition budget spent by December, %s' % C.fy(Y1),
                 'published', {'y': F(Y1)})
    comp_rows = [dict(label='%s, %s' % (J.COMPONENT_LABEL[c], C.fy(y)),
                      cells=[pc(K[(y, c, p)]) for p in (SEPTEMBER, DECEMBER, MARCH, JUNE)])
                 for c in comps for y in (Y0, Y1) if (y, c, JUNE) in K]
    out['sped-burndown'] = TP.page(
        'sped-burndown',
        'In %s the circuit breaker paid %s from July to May, then %s in one June entry.'
        % (C.fy(Y1), C.usd(early[Y1]), C.usd(cb_june)),
        list(sx.values()),
        [con('July to May, the circuit breaker paid %s in %s and %s in %s.'
             % (C.usd(early[Y0]), C.fy(Y0), C.usd(early[Y1]), C.fy(Y1)),
             ['cb0', 'cb1', 'cbj', 'off'],
             {'a': U(early[Y0]), 'y': F(Y0), 'b': U(early[Y1]), 'z': F(Y1)},
             so='Until June the general fund carried tuition the reimbursement later paid, so '
                'those lines read as further over budget than they closed.',
             notes=[step('In June one entry moved %s of collaborative tuition onto it. The '
                         'budget book set that tuition line %s lower for this money.'
                         % (C.usd(cb_june), C.usd(480204)), 'measured',
                         {'j': U(cb_june), 'a': U(480204)},
                         cite=(BOOK, 'LPS budget book, 12 March 2025, 9400 Collaborative Tuitions')),
                    step('Why the reimbursement was taken in one entry at year end is not in the '
                         'journal.', 'gap',
                         closes='the district’s circuit breaker claim and the state’s payment '
                                'schedule for %s' % C.fy(Y1), allow=(C.fy(Y1),))]),
         con('General fund special education spending in September and October: %s, against %s '
             'in %s.' % (C.usd(fl(so[Y1])), C.usd(fl(so[Y0])), C.fy(Y0)),
             ['so0', 'so1'], {'a': U(so[Y1]), 'b': U(so[Y0]), 'y': F(Y0)},
             so='The early months already showed the year running ahead of the last one, a signal '
                'the monthly report carries long before the close.'),
         con('Tuition spent %s of its %s budget by December; %s in %s.'
             % (C.pct(t_dec[Y1], 0), C.fy(Y1), C.pct(t_dec[Y0], 0), C.fy(Y0)),
             ['t0', 't1'],
             {'a': P(t_dec[Y1], 0), 'y': F(Y1), 'b': P(t_dec[Y0], 0), 'z': F(Y0)},
             so='By December most of the tuition budget was used, months before the year end '
                'showed the overrun.'),
         con('Contracted services still had %s of the budget left in December and ended June %s over.'
             % (C.pct(con_dec, 0), C.pct(-con_jun, 0)),
             ['cd', 'cj'], {'a': P(con_dec, 0), 'b': P(-con_jun, 0)},
             so='A line can look comfortable at mid-year and close far over, so its December '
                'balance says little about its year end.',
             notes=[step('The costs arrived in the second half of the year; the journal shows '
                         'when, not why.', 'measured')])],
        chart=TP.series('Circuit breaker spending, before June and in June',
                        [C.fy(y) for y in J.YEARS],
                        [TP.track('July to May', [early[y] for y in J.YEARS], 'published', 'bar'),
                         TP.track('June', [june[y] for y in J.YEARS], 'published', 'bar')], '$',
                        kind='bar', stacked=True,
                        note='Actuals on special education accounts in the circuit breaker fund. '
                             'Never shown by month: a month can hold one family’s payment.'),
        also=[TP.series('Special education budget left, month by month', X, [
            TP.track(C.fy(y), [round(S_[(y, p)], 1) for p in range(13)], 'published', 'line')
            for y in J.YEARS], '%', decimals=1,
            note='General fund special education accounts, department 300: share of the final '
                 'budget not yet spent. Psychology and equipment are outside it, as DESE decides.',
            note_figures={'d': N(int(J.SURPLUS_DEPT), 'department')})],
        table=dict(caption='Special education budget left, by what it buys', views=[dict(
            key='components', label='General fund', total_col=None, kinds=['ledger'] * 4,
            columns=['Left, Sep', 'Left, Dec', 'Left, Mar', 'Left, Jun'], rows=comp_rows,
            note='Share of each part’s final budget not yet spent; a negative figure is over '
                 'budget.')]),
        sources=sources() + [dict(label='Lunenburg Public Schools — budget book, 12 March 2025 '
                                        '(Collaborative Tuitions, circuit breaker line)',
                                  href=BOOK)],
        finding_figures={'y': F(Y1), 'e': U(early[Y1]), 'a': U(cb_june)})
    out['sped-burndown']['not_established'] = [
        'Why the FY2026 circuit breaker reimbursement was taken in one June entry.',
        'Which children or placements the early tuition payments were for.',
        'Why contracted services costs arrived late in the year.',
    ]
    return out



# ================================================== the 30 June tuition payment
# TJ, 26 October 2026: "please build a page for this specifically so i can point people to it
# related to the FY26 surplus". Found in the review of the surplus pages: on the last day of
# FY2026 the general fund paid FLLAC nine invoices whose numbers, and rate, are FY2027's.
#
# WHAT IS MEASURED: every entry, its date, fund, account, source code and check; FLLAC's own
# numbering run (`25L2KEY..` paid only in FY2025, `26..` in FY2026, `27..` only on 30 June 2026)
# and its standard quarterly rate per prefix. WHAT IS OUR READING: that the `27` invoices bill
# FY2027's first quarter -- four clues, no service dates -- and it is labelled so everywhere.
# RULE 8: the practice is lawful (G.L. c. 71 s. 71D; DLS), so the page states the EFFECT on the
# surplus figure and what the record does not show (an approval), never intent.
PREPAID = 'fy2026-tuition-paid-early'
COLLAB = '0100-3-300-9400-51-1-06-2-535023'     # general fund collaborative tuitions
FEB4_CAPTIONS = 'sources/data/youtube-transcripts/school-committee/2026-02-04-HsjpFotE9hc.json'
FEB4_HREF = 'https://www.youtube.com/watch?v=HsjpFotE9hc&t=3760s'
FEB4_QUOTE = ('what would you have done with the $556,000? Well, if I had looked at the budget '
              'and saw that, … one of the things you can do towards the end is prepay special '
              'ed tuitions.')
FEB4_ASK = ('if it\'s spent by the school district before it gets there, that there is an open '
            'transparent conversation around it')
OCT22_CAPTIONS = 'sources/data/youtube-transcripts/finance-committee/2026-10-22-wQWhIwYOc9o.json'
OCT22_HREF = 'https://www.youtube.com/watch?v=wQWhIwYOc9o&t=6585s'
OCT22_QUOTE = ('We are allowed to prepay the 1st quarter of out of district tuition from circuit '
               'Breaker accounts.')
JUL29_TEXT = 'sources/meetings/text/school-committee/2026-07-29-minutes-7930.txt'
JUL29_QUOTE = 'he was confident the remaining amount would be well below that figure'
# The 15 July 2026 minutes list the 6/18-6/30 warrant with no motion; the Chair, asked by email
# on 27 October 2026, replied at 8:50 PM (recorded in the warrant-folder thread, checked verbatim).
CHAIR_TEXT = 'sources/correspondence/2026-10-27-warrants-folder-superintendent.txt'
CHAIR_HREF = '/docs/correspondence/2026-10-27-warrants-folder-superintendent.txt'
CHAIR_QUOTE = 'It is not recorded as a vote in the minutes because no vote was taken.'
JUL15_HREF = '/docs/meetings/school-committee/2026-07-15-minutes-7901.pdf'
SC_MINUTES = 'sources/meetings/text/school-committee'
SPECREV = 'sources/town-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx'
BOOK26_TEXT = ('sources/district-budget/text/'
               'final-fy26-sc-approved-budget-3-12-25-with-level-service-budget.txt')
DESE_CB_FAQ = 'https://www.doe.mass.edu/finance/circuitbreaker/faq.html'


def _captions(path):
    return ' '.join(x['text'] for x in
                    json.load(open(os.path.join(ROOT, path), encoding='utf-8'))['segments'])


def prepaid_page(d):
    import csv
    import datetime
    import glob
    import re
    U = lambda v: figure(fl(v), C.usd(fl(v)))
    U2 = lambda v: figure(fl(v), usd2(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    f, con = LD.fact, TP.conclusion
    rows = [r for r in J.lines() if r['vendor'].startswith('FLLAC')
            and 'TUITION' in r['account_description'] and J.COLUMN_OF[r['source']] == 'actual']
    pre = lambda r: (re.match(r'(\d\d)L2KEY(\d)', r['doc_no'] or '') or [None, None, None])
    # FLLAC's run: which prefix was paid in which year, and its standard quarterly rate.
    by_prefix = defaultdict(set)
    rate = defaultdict(lambda: defaultdict(int))
    for r in rows:
        m = pre(r)
        if m[1]:
            by_prefix[int('20' + m[1])].add(r['fy'])
            rate[int('20' + m[1])][r['amt']] += 1
    # FY2023 and FY2024 were billed one total a quarter; from FY2025 one invoice a placement,
    # at a standard quarterly rate -- the most common amount under each prefix.
    std = {y: max(c, key=c.get) for y, c in rate.items() if y >= Y0}
    if sorted(std) != [Y0, Y1, Y1 + 1] or not std[Y0] < std[Y1] < std[Y1 + 1]:
        fail('the page assumes three FLLAC rates, rising, for FY%d to FY%d' % (Y0, Y1 + 1))
    # The 30 June payment: every invoice numbered for the next year, paid on the year's last day.
    early = [r for r in rows if pre(r)[1] and int('20' + pre(r)[1]) == r['fy'] + 1
             and r['effective_date'] == '%d-06-30' % r['fy']]
    paid = sum((r['amt'] for r in early), D0)
    if {r['fy'] for r in early} != {Y1} or len(early) != 9:
        fail('the page assumes nine next-year invoices paid on 30 June, all in FY%d' % Y1)
    if {r['account'] for r in early} != {COLLAB} or {r['source'] for r in early} != {'API'}:
        fail('the 30 June invoices are no longer vendor payments on the general fund line')
    if len({(r['journal'], r['check_no']) for r in early}) != 1:
        fail('the 30 June invoices are no longer one journal and one check')
    jnl, check = early[0]['journal'], early[0]['check_no']
    # THE CHECK DATE IS NOT IN THE JOURNAL, which carries only the effective date (30 June, the
    # day the expense was charged to FY2026). It is the Munis check register line the district
    # sent on 19 November 2026 (sources/correspondence/2026-11-19-check-218995-register-line.png):
    # check 218995, 07/16/2026, $199,364.25. Held here because no dataset carries it, and tied:
    # every journal line on this check must sum to that line's amount, or the date is not this
    # check's.
    if check != CHECK['no'] or sum((r['amt'] for r in J.lines() if r['check_no'] == check), D0) \
            != CHECK['amount']:
        fail('the journal lines on check %s no longer sum to the register line\'s %s'
             % (check, CHECK['amount']))
    check_day = datetime.date.fromisoformat(CHECK['date'])
    check_when = '%d %s' % (check_day.day, check_day.strftime('%B'))
    if by_prefix[Y1 + 1] != {Y1}:
        fail('FY2027-numbered invoices were paid in a year other than FY%d' % Y1)
    # The day before: the reclass onto the circuit breaker fund.
    recl = [r for r in J.lines() if r['fy'] == Y1 and r['source'] == 'GEN'
            and 'RECLASS COLLABORATIVE' in r['description']]
    out_gf = -sum((r['amt'] for r in recl if r['fund'] == '0100'), D0)
    in_cb = sum((r['amt'] for r in recl if r['fund'] == '2640'), D0)
    if out_gf != in_cb or out_gf <= 0 or {r['effective_date'] for r in recl} != {'%d-06-29' % Y1}:
        fail('the reclass is no longer one 29 June entry from the general fund to fund 2640')
    # The line, before 30 June: paid against its budget, and never a transfer.
    acct = J.accounts()[COLLAB]
    line = [r for r in J.lines() if r['account'] == COLLAB and r['fy'] == Y1]
    budget = sum((r['amt'] for r in line if r['posts_to'] in ('original_budget', 'transfer')), D0)
    if any(r['posts_to'] == 'transfer' and r['amt'] for r in line):
        fail('the collaborative tuition line now shows a transfer; the page says none covered it')
    paid_before = sum((r['amt'] for r in line if r['posts_to'] == 'actual'
                       and r['effective_date'] < '%d-06-30' % Y1), D0)
    if not paid_before > budget:
        fail('the page says the line was past its budget before 30 June')
    # No such payment in any other year we hold.
    others = [r for r in rows if r['fy'] != Y1 and pre(r)[1] and int('20' + pre(r)[1]) > r['fy']
              and r['effective_date'][5:] >= '06-01']
    if others:
        fail('a year before FY%d now shows a next-year FLLAC invoice paid in June' % Y1)
    # What it does to the surplus: FY2025 and FY2026 on one footing (Surplus by year).
    owed = {y: d['left'][y] - d['closed'][y] for y in (Y0, Y1)}
    without = d['left'][Y1] + paid
    if not (without > d['left'][Y0] > owed[Y0] > owed[Y1]):
        fail('the page says that without the payment FY%d left more than FY%d on any footing'
             % (Y1, Y0))
    # The record: the warrant for 18 June to 5 July in the minutes, and no advance-tuition vote.
    mins = sorted(glob.glob(os.path.join(ROOT, SC_MINUTES, '2026-0[4-8]-*minutes*.txt')))
    text = {os.path.basename(m)[:10]: ' '.join(open(m, encoding='utf-8').read().split()) for m in mins}
    # Every warrant period the minutes LIST, as (date of the minutes, first day, last day). A
    # listing is not an approval: no set of these minutes records a motion on its warrants.
    spans = [(dt, (int(a), int(b)), (int(c), int(e))) for dt, t in text.items() for a, b, c, e in
             re.findall(r'[Ww]arrants:? (\d+)/(\d+)(?:/\d+)? (?:to|-|–) (\d+)/(\d+)', t)]
    if not spans:
        fail('no warrant periods read from the School Committee minutes; the pattern broke')
    # Until 29 October 2026 no minutes listed a warrant covering 18 June to 5 July. The 15 July
    # minutes (posted 29 October; delivered by email 27 October) list exactly one, 6/18 to 6/30,
    # with no motion and no vote, and the Chair wrote that evening that "no vote was taken". Any
    # OTHER minutes listing that period would be the approval the page says is not on record.
    late = [(dt, lo, hi) for dt, lo, hi in spans if lo <= (7, 5) and hi >= (6, 18)]
    if [(lo, hi) for _, lo, hi in late] != [((6, 18), (6, 30))] or {dt for dt, _, _ in late} != {'2026-07-15'}:
        fail('the minutes listing a warrant for 18 June to 5 July are no longer only the 15 July '
             'minutes, 6/18 to 6/30: %s' % late)
    jul15 = re.search(r'5\. Review and Approve Line Items, Transfers, Warrants & Donations (.*?) '
                      r'6\. New Business', text.get('2026-07-15', ''))
    if not jul15:
        fail('item 5 of the 15 July minutes is no longer where the page read it')
    if re.search(r'\bmo(?:ved|tion)\b|\bsecond|\bvote|\bapprov|\bAYE\b', jul15.group(1), re.I):
        fail('item 5 of the 15 July minutes now records a motion or vote; re-read it')
    m15 = re.search(r'Warrants: 6/18/26 to 6/30/26 - \$([\d,]+\.\d\d)', jul15.group(1))
    if not m15:
        fail('the 15 July minutes no longer list the 6/18 to 6/30 warrant with its amount')
    if not TP.verbatim_in(CHAIR_QUOTE, open(os.path.join(ROOT, CHAIR_TEXT), encoding='utf-8').read()):
        fail('the Chair’s 27 October 2026 reply is no longer in %s' % CHAIR_TEXT)
    if any(re.search(r'71D|\bprepa(?:y|id|ying|yment)\b|advance (?:tuition|payment)|'
                     r'tuitions? in advance', t, re.I) for t in text.values()):
        fail('a School Committee minute now mentions advance tuition; re-read it')
    if not TP.verbatim_in(JUL29_QUOTE, open(os.path.join(ROOT, JUL29_TEXT), encoding='utf-8').read()):
        fail('the 29 July quotation is no longer in the minutes')
    for q, p_ in ((FEB4_ASK, FEB4_CAPTIONS), (OCT22_QUOTE, OCT22_CAPTIONS)):
        if not TP.verbatim_in(q, _captions(p_)):
            fail('a quotation is no longer in the captions %s' % p_)

    # WHERE THE APPROVAL WOULD BE (TJ, 26 Oct 2026). The warrant that paid check %s falls in
    # the period 18 to 30 June; the School Committee's 15 July agenda lists exactly that warrant.
    # Its minutes list the warrant with no vote (above). Amounts are read off the documents,
    # quotes off the captions.
    reg = {r['date']: r for r in csv.DictReader(open(os.path.join(ROOT, 'sources', 'data',
           'meeting-register.csv'), encoding='utf-8')) if r['board_slug'] == 'school-committee'}
    agenda = lambda dt: ' '.join(open(glob.glob(os.path.join(ROOT, SC_MINUTES, dt + '-agenda-*.txt'))[0],
                                      encoding='utf-8').read().split())
    mw = re.search(r'6/18 to 6/30 \$([\d,]+\.\d\d)', agenda('2026-07-15'))
    m24 = re.search(r'Warrants 6/2/26 to 6/17/26 \$([\d,]+\.\d\d)', text['2026-06-24'])
    if not (mw and m24):
        fail('the June warrant periods are no longer on the 15 July agenda and 24 June minutes')
    w_late, w_june = Decimal(mw.group(1).replace(',', '')), Decimal(m24.group(1).replace(',', ''))
    if Decimal(m15.group(1).replace(',', '')) != w_late:
        fail('the 15 July minutes and agenda no longer give the same 6/18 to 6/30 warrant total')
    # The 29 July warrant, read off its agenda: the whole of it is smaller than this one batch,
    # so the batch cannot be on it as presented. The page says so; this keeps it true.
    m29 = re.search(r'Warrants 7/6 to 7/20/26 \$([\d,]+\.\d\d)', agenda('2026-07-29'))
    if not m29:
        fail('the 29 July agenda no longer gives the 7/6 to 7/20 warrant total')
    w_july = Decimal(m29.group(1).replace(',', ''))
    if not w_july < paid:
        fail('the page says the 29 July warrant is smaller than the batch')
    later = [os.path.basename(x) for x in glob.glob(os.path.join(ROOT, SC_MINUTES, '2026-*.txt'))
             if os.path.basename(x)[:10] > '2026-07-15'
             # The warrant's own wording, not a bare date: the 4 November 2026 agenda lists
             # MINUTES of 6/18/25, which a bare `6/18` took for this warrant.
             and re.search(r'6/18(?:/26)?\s*(?:to|-|–)\s*6/30', open(x, encoding='utf-8').read())]
    if later:
        fail('a later School Committee document now lists the 18 to 30 June warrant: %s' % later)
    if not reg['2026-07-15']['minutes_url']:
        fail('the 15 July minutes are no longer posted on the Agenda Center; the trail says they are')
    cap = lambda dt: _captions(glob.glob(os.path.join(ROOT, 'sources', 'data', 'youtube-transcripts',
                                                      'school-committee', dt + '-*.json'))[0])
    QUOTES = {'2026-07-15': 'Transfers is next meeting',
              '2026-09-09': 'It\'s late and I don\'t have information',
              '2026-09-16': 'it looks like that large unexpended funds is in our private school tuitions'}
    for dt, q in QUOTES.items():
        if not TP.verbatim_in(q, cap(dt)):
            fail('the %s quotation is no longer in the captions' % dt)
    def links(dt, t=None):
        r_ = reg[dt]
        out_ = [dict(label='Agenda', href=r_['agenda_url'])]
        if r_['minutes_url']:
            out_.append(dict(label='Minutes', href=r_['minutes_url']))
        if r_['video_urls']:
            out_.append(dict(label='Recording', href=r_['video_urls'].split()[0] + ('&t=%ds' % t if t else ''),
                             caption=True))
        miss = ([] if r_['video_urls'] else ['No recording']) + ([] if r_['minutes_url'] else ['No minutes posted'])
        return out_, miss
    trail = []
    for dt, expected, shows, t in (
            ('2026-06-24', 'Warrants for 2 to 17 June, %s; line-item transfers; carry-forward orders.'
             % usd2(w_june), 'Four transfers and the carry-forward orders voted; no tuition payment among '
             'them. The warrants end before 30 June.', 2100),
            ('2026-07-15', 'Warrants for 18 to 30 June, %s. The district says nine batches, to '
             '30 June; batch %s is not one of them.' % (usd2(w_late), BATCH), 'The minutes list the warrant with no motion and no vote; the Chair, '
             'asked on 27 October 2026: “%s” On the recording it is raised, the talk turns to '
             'transfers (“%s”), and the meeting moves on. No later agenda or minutes lists this '
             'warrant.' % (CHAIR_QUOTE, QUOTES['2026-07-15']), 95),
            ('2026-07-29', 'Year-end line-item transfers; warrants for July.',
             'Transfers “just to cover overages”; FY2026 to close “well below” the year before. No '
             'tuition payment mentioned. The whole warrant, 6 to 20 July, is %s, less than the '
             'batch.' % usd2(w_july), 1330),
            ('2026-09-02', 'FY26 Year End Budget review.', 'Neither recorded nor minuted.', None),
            ('2026-09-09', 'FY26 Year End Budget review.', 'Passed over: “%s.”' % QUOTES['2026-09-09'],
             7555),
            ('2026-09-16', 'Warrants; a warrant article request.',
             '“%s”, and a mention of “taking certain tuitions out of the grants”.'
             % QUOTES['2026-09-16'], 690)):
        lk, miss = links(dt, t)
        d_ = datetime.date.fromisoformat(dt)
        trail.append(dict(when='%d %s %d' % (d_.day, d_.strftime('%B'), d_.year), board='School Committee',
                          expected=expected, shows=shows, links=lk, missing=miss))
    if not TP.verbatim_in('taking certain tuitions out of the grants', cap('2026-09-16')):
        fail('the 16 September grants remark is no longer in the captions')
    trail_allow = tuple(sorted({x['when'] for x in trail} | {l_['href'] for x in trail for l_ in x['links']}
                               | {'2 to 17 June', '18 to 30 June', '30 June', 'FY26', 'FY2026',
                                  '26 October 2026', '27 October 2026', BATCH, '6 to 20 July',
                                  usd2(w_july)}))

    # THE 29 JUNE ENTRY, from Surplus by category's generator (moved here 27 November 2026,
    # T-VPW4S): its facts, two conclusions and blocks are built there from its data(), which
    # ties the fund to the Town's report, the form and the thread. Tied to this page's reading.
    import build_fy2026_school_surplus as SP
    sf = SP.data()
    ent = SP.entry(sf)
    if sf['charged'] != out_gf or sf['early'] != paid or sf['journal'] != recl[0]['journal']:
        fail('the 29 June entry and the 30 June charge differ between this page and Surplus by '
             'category’s reading')

    # The circuit breaker fund's balance, from the Town's special-revenue report at 31 March 2026
    # (period 9, published with the period-9 package), carried to 30 June with the journal's own
    # entries. DESE: "FY26 reimbursements must be spent ... in FY26 and/or FY27, and cannot be
    # carried into FY28" (circuit breaker FAQ, question 10). One fund, 2640, holds every year's
    # money, so which dollars are "older" is our arithmetic: what the fund held on 1 July 2025,
    # less what FY2026 spent before the re-charge, could only be FY2025's or earlier.
    import openpyxl
    cb = [r for r in J.lines() if r['fund'] == '2640']
    ws = openpyxl.load_workbook(os.path.join(ROOT, SPECREV), read_only=True, data_only=True).worksheets[0]
    sr = [r for r in ws.iter_rows(values_only=True) if r and r[0] == 2640]
    if len(sr) != 1:
        fail('fund 2640 is not one row in %s' % SPECREV)
    open_bal, sr_rev, sr_exp, mar_bal = -Decimal(str(sr[0][8])), -Decimal(str(sr[0][10])), \
        Decimal(str(sr[0][13])), -Decimal(str(sr[0][15])).quantize(Decimal('0.01'))
    if open_bal + sr_rev - sr_exp != mar_bal:
        fail('the special-revenue report no longer foots for fund 2640')
    j_rev = -sum((r['amt'] for r in cb if r['fy'] == Y1 and r['source'] == 'CRP'), D0)
    j_api = sum((r['amt'] for r in cb if r['fy'] == Y1 and r['source'] == 'API'), D0)
    if j_rev != sr_rev or j_api != sr_exp:
        fail('the journal no longer agrees with the March report: nothing else posted to fund '
             '2640 in FY%d but the 29 June re-charge' % Y1)
    if any(r['source'] not in ('CRP', 'API', 'GEN', 'POE', 'POL', 'POM') for r in cb if r['fy'] == Y1):
        fail('fund 2640 has an FY%d entry of a kind the balance arithmetic does not handle' % Y1)
    # What the budget book planned the fund to pay, FY2026, read from our copy of the book: the
    # same figure Surplus by category reads from the circuit breaker module.
    book26 = ' '.join(open(os.path.join(ROOT, BOOK26_TEXT), encoding='utf-8').read().split())
    m26 = re.search(r'Circuit Breaker \(70% = \$[\d,]+\) \(75% = [\d,]+\) \([\d,.]+\)\$ '
                    r'\(([\d,.]+)\)\$', book26)
    if not m26:
        fail('the FY2026 circuit breaker offset is no longer in %s' % BOOK26_TEXT)
    # The book prints cents, the module whole dollars: within $1 rounding tolerance
    # (notes/process/TOLERANCES.md).
    if abs(float(m26.group(1).replace(',', '')) - fl(sf['plan'])) >= 1:
        fail('the FY2026 budget book and the circuit breaker module give different plans')
    older = open_bal - sr_exp           # what could only be FY2025's money or earlier
    june_bal = mar_bal - out_gf          # after the 29 June re-charge (our arithmetic)
    if not (out_gf > older > 0 and june_bal < sr_rev):
        fail('the circuit breaker block assumes the re-charge used all the older money')
    if older != sf['older']:
        fail('the older money differs between the Town’s report and the circuit breaker module')
    yrs = J.YEARS
    same = [fl(sum((r['amt'] for r in rows if r['fy'] == y and r not in early), D0)) for y in yrs]
    ahead = [fl(sum((r['amt'] for r in early if r['fy'] == y), D0)) for y in yrs]

    fx = {}
    fx['paid'] = f('paid', U2(paid), 'charged to %s 30 June; check %s cut %s'
                   % (C.fy(Y1), check, check_when), 'published',
                   {'y': F(Y1)}, allow=('30 June', check, check_when))
    fx['n'] = f('n', N(len(early), 'invoices'), 'invoices, all numbered for %s' % C.fy(Y1 + 1),
                'published', {'y': F(Y1 + 1)})
    fx['r27'] = f('r27', U2(std[Y1 + 1]), 'the quarterly rate on those invoices', 'published')
    fx['r26'] = f('r26', U2(std[Y1]), 'the rate on every %s-numbered invoice' % C.fy(Y1),
                  'published', {'y': F(Y1)})
    fx['before'] = f('before', U(paid_before), 'already paid on the line before 30 June',
                     'published', allow=('30 June',))
    fx['budget'] = f('budget', U(budget), 'the line’s %s budget, never added to by transfer'
                     % C.fy(Y1), 'published', {'y': F(Y1)})
    fx['period'] = f('period', None, 'the service period the invoices bill', 'gap',
                     closes='FLLAC’s invoices 27L2KEY11 to 27L2KEY19, with their service dates',
                     allow=('27', '11', '19'))
    fx['approval'] = f('approval', None, 'who approved the payment', 'gap',
                       closes='the signed original of batch %s, which the district says went to '
                              'Town Hall for the Select Board’s signature' % BATCH, allow=(BATCH,))
    facts = ent['facts'] + list(fx.values())
    conclusions = [
        ent['conclusions']['plan'],
        ent['conclusions']['draws'],
        con('%s on %s FLLAC invoices priced for %s: charged to %s on 30 June, paid %s.'
            % (C.usd(fl(paid)), C.num(len(early)), C.fy(Y1 + 1), C.fy(Y1), check_when),
            ['paid', 'n', 'r27', 'r26', 'period'],
            {'a': U(paid), 'n': N(len(early)), 'y': F(Y1 + 1), 'z': F(Y1)},
            allow=('30 June', check_when),
            so='If they pay for %s, %s’s surplus reads that much smaller than what %s needed for '
               'itself.' % (C.fy(Y1 + 1), C.fy(Y1), C.fy(Y1)),
            so_figures={'y': F(Y1 + 1), 'z': F(Y1)},
            notes=[step('That they bill %s’s first quarter is our reading: each invoice prefix '
                        'was paid in its own year, %s had paid four quarters, and the rate is '
                        'new.' % (C.fy(Y1 + 1), C.fy(Y1)),
                        'hypothesis', {'y': F(Y1 + 1), 'z': F(Y1)})]),
        con('No School Committee agenda, minutes or warrant we hold shows this payment presented '
            'or approved.', ['approval', 'before', 'budget'], {},
            so='The copy of the batch supplied has blank signature lines; the district says the '
               'originals went to Town Hall.',
            notes=[step('Approval may exist off the record: year-end warrants are often signed '
                        'between meetings.', 'gap',
                        closes='the signed original of batch %s' % BATCH, allow=(BATCH,))])]

    # THE SIGNATURE (27 November 2026): the two entries in the year's last two days, on one line.
    d29, d30 = '29 June', '30 June'
    timeline = TB.timeline(
        'Two entries in the last two days of the year', ['July to May', d29, d30, check_when],
        [(('Circuit breaker, fund 2640', None, ('2640',)), [
            TB.track('Tuition the fund paid', ['light', 'cb', None, None], event=1,
                     note=('Almost nothing from July to May; then one charge for the year’s '
                           'collaborative tuition on %s.' % d29, None, (d29,)),
                     basis=('record', 'the school journal'))]),
         ('General fund, collaborative tuition', [
             TB.track(('Reclass onto the circuit breaker: %s' % usd2(out_gf), {'a': U2(out_gf)}),
                      [None, 'cb', None, None], event=1,
                      note=('Tuition the general fund had already paid, moved by one journal entry, '
                            '%s. The vote planned %s from the fund.'
                            % (recl[0]['journal'], C.usd(fl(sf['plan']))),
                            {'p': U(sf['plan'])}, (recl[0]['journal'],)),
                      basis=('record', 'the form, the journal proof and the journal')),
             TB.track(('Nine %s invoices charged to %s: %s' % (C.fy(Y1 + 1), C.fy(Y1), usd2(paid)),
                       {'y': F(Y1 + 1), 'z': F(Y1), 'a': U2(paid)}),
                      [None, None, 'charged', 'paid'], event=2,
                      note=('Charged on the year’s last day as batch %s; check %s cut on %s.'
                            % (BATCH, check, check_when), None, (BATCH, check, check_when)),
                      basis=('record', 'the journal and the Munis check register line'))])],
        [('light', 'Little or nothing', 'muted'), ('cb', 'Charged to the circuit breaker', 'neutral'),
         ('charged', 'Charged to the year that is ending', 'other'),
         ('paid', 'Check cut', 'muted', 'outline')],
        place='lead', marker=(2, ('%s closes' % C.fy(Y1), {'y': F(Y1)})),
        note=('One account, %s, one day apart. The journal records both; no document we hold links '
              'them.' % COLLAB, None, (COLLAB,)))
    with_without = TB.chart(TP.series(
        'What was left, with and without the payment', [C.fy(Y0), C.fy(Y1)],
        [TP.track('Left, counting orders still owed', [fl(owed[Y0]), fl(owed[Y1])],
                  'published', 'bar'),
         TP.track('Without the 30 June charge (our sum)', [None, fl(without)], 'estimate',
                  'bar')],
        '$', kind='bar',
        note='School general fund, department 300. Counting orders owed is the footing on '
             'Surplus by year.', note_allow=('300',)),
        place='body',
        so=('In July the Committee heard %s would close well below %s. That holds as reported and '
            'reverses with this payment taken out.' % (C.fy(Y1), C.fy(Y0)),
            {'y': F(Y1), 'z': F(Y0)}, ()))
    fund_panels = TB.panels('The circuit breaker fund, before and after', [
        TB.panel('To the end of March, as the Town printed it', [
            ('Held at the start of the year', usd2(open_bal), None),
            ('Received this year', usd2(sr_rev), None),
            ('Spent this year, to March', usd2(sr_exp), None),
            ('Held at the end of March', usd2(mar_bal), None)]),
        TB.panel('At year end (our arithmetic)', [
            ('Older money, to be spent by year end', usd2(older), 'bad'),
            ('Tuition charged to it at year end', usd2(out_gf), None),
            ('Left at year end, all this year’s receipts', usd2(june_bal), 'good')])],
        place='body',
        note='One fund holds every year’s money, so older money is what it held at the start of '
             'the year less what the year spent before June. The Town’s special-revenue report, '
             'then the school journal.',
        so=('What the fund holds after the re-charge, %s, is all this year’s receipts, and carries '
            'into %s.' % (C.usd(fl(june_bal)), C.fy(Y1 + 1)),
            {'b': U(june_bal), 'y': F(Y1 + 1)}))
    define = TB.explain('A payment, not a transfer', [
        'A **transfer** moves budget from one line to another; no money leaves, and the '
        'School Committee votes each one. A **reclass** moves a cost already paid from one '
        'fund to another. A **payment** sends money to a vendor, on a warrant.',
        ('The 30 June entry is a payment, charged that day and paid by check on %s. It went '
         'to a line that had already spent past its budget, and was covered, inside the school '
         'total, by other lines’ leftovers.' % check_when,
         None, ('30 June', check_when))],
        place='body', tone='define')
    meeting_trail = TB.custom(
        'meeting-trail', 'Where the approval would be on the record', dict(rows=trail),
        place='body', figures=(usd2(w_june), usd2(w_late)), allow=trail_allow,
        alt='School Committee meetings from 24 June to 16 September 2026: what each '
            'agenda held, what the record shows, and links to every record that exists',
        so=('No School Committee warrant on record carries batch %s: it is not among '
            'the 15 July batches, and the 29 July warrant is smaller.' % BATCH,
            None, (BATCH, '15 July', '29 July')))
    shows = TB.explain('What the record shows, and does not', [
        ('**Allowed.** State law lets a school committee approve paying up to three months '
         'of tuition in advance (G.L. c. 71, s. 71D), and the state’s Division of Local '
         'Services uses this case as its example: a July to September bill, due 30 June, '
         'charged to the year that is ending.', None, ('71', '71D', '30 June')),
        ('**Not announced.** Every June and July 2026 meeting of the School Committee, '
         'Finance Committee and Select Board was read, minutes and recordings. None '
         'mentions this payment or the re-charge to the circuit breaker. No minutes record '
         'an advance-tuition vote. The warrant for the last two weeks of June was on the '
         'School Committee’s 15 July agenda and is in that meeting’s minutes with no '
         'motion or vote; the Chair wrote on 27 October that no vote was taken. No later '
         'agenda or minutes lists it.',
         None, ('2026', '15 July', '27 October')),
        ('**Not presented, on any record we hold.** The payment is batch %s. The '
         'district says the 15 July warrant was its batches to 30 June; the nine delivered '
         'do not include %s. The 29 July warrant, 6 to 20 July, is %s in all, less than the '
         'batch. No agenda, minutes or recording names the batch, check %s or the '
         'invoices. The copy the district supplied on 19 November 2026 has blank signature '
         'lines, and the district says the signed originals “were immediately sent to Town '
         'Hall for processing and signature by the SelectBoard.”'
         % (BATCH, BATCH, usd2(w_july), check),
         None, (BATCH, '15 July', '30 June', '29 July', '6 to 20 July', usd2(w_july),
                check, '19 November 2026')),
        ('**Not yet held.** The signed original of batch %s, and the School Committee’s '
         'September year-end budget reviews. Each is a '
         'registered gap, listed on What we cannot answer.' % BATCH, None, (BATCH,))],
        place='end', tone='plain')

    srcs = SP.entry_sources() + [
        dict(key='check', label='Lunenburg Public Schools — Munis check register line, check %s '
                                '(sent 19 November 2026)' % check, href=CHECK['href']),
        dict(key='jun24', label='Lunenburg School Committee — 2026-06-24 minutes',
             href='/docs/minutes/text/school-committee/2026-06-24-minutes-7869.txt'),
        dict(key='jul15', label='Lunenburg School Committee — 2026-07-15-minutes-7901.pdf (item '
                                '5b, the 6/18 to 6/30 warrant)', href=JUL15_HREF),
        dict(key='chair', label='Lunenburg Public Schools — the warrant-folder thread of 27 '
                                'October 2026, with the Chair’s reply (by email)', href=CHAIR_HREF),
        dict(key='feb4', label='School Committee recording, 4 February 2026', href=FEB4_HREF),
        dict(key='law', label='G.L. c. 71, s. 71D — advance payment of tuition',
             href='https://malegislature.gov/Laws/GeneralLaws/PartI/TitleXII/Chapter71/section71D'),
        dict(key='dls', label='Division of Local Services — prepayment from prior fiscal year funds',
             href='https://www.mass.gov/info-details/ask-dls-prepayment-from-prior-fiscal-year-funds'),
    ]
    hrefs = [s_['href'] for s_ in srcs]
    if len(set(hrefs)) != len(hrefs):
        fail('two sources on %s share an address: %s'
             % (PREPAID, sorted({h for h in hrefs if hrefs.count(h) > 1})))
    B = ent['blocks']
    cite = TP.cite
    flow = [
        'finding',
        cite(timeline, 'journal', 'form', 'proof', 'check', 'book'),
        cite(B['plan'], 'book', 'p13-26', 'journal', 'invoices'), ('conclusion', 0),
        cite(B['draws'], 'journal', 'specrev', 'dese'), ('conclusion', 1),
        cite(fund_panels, 'specrev', 'journal', 'dese'),
        cite(('chart', 0), 'journal', 'accounts', 'invoices'), ('conclusion', 2),
        cite(with_without, 'journal', 'p13-26'),
        cite(define, 'journal', 'check', 'law'),
        'lead_quote',
        cite(meeting_trail, 'jun24', 'jul15', 'chair', 'sc0729', 'feb4'), ('conclusion', 3),
        cite(B['trail'], 'form', 'proof', 'journal', 'thread1', 'thread2', 'thread4', 'thread6',
             'p13-26', 'fincom'),
        cite(B['reversal'], 'thread4', 'p13-26', 'book', 'journal', 'dese'),
        cite(B['explanations'], 'thread3', 'thread5', 'atr25', 'specrev', 'journal', 'dese',
             'provenance'),
        cite(B['settle'], 'thread1', 'specrev'),
        cite(shows, 'law', 'dls', 'jul15', 'chair', 'invoices'),
        cite(B['credit'], 'thread2'),
        'said', 'sources',
    ]
    page = TP.page(
        PREPAID,
        '%s, %s of tuition moved to the circuit breaker; %s, %s of %s invoices, to %s.'
        % (d29, C.usd(fl(out_gf)), d30, C.usd(fl(paid)), C.fy(Y1 + 1), C.fy(Y1)),
        facts, conclusions,
        chart=TP.series(
            'FLLAC tuition paid, by year it was paid', [C.fy(y) for y in yrs],
            [TP.track('Invoices numbered for that year', same, 'published', 'bar'),
             TP.track('Invoices numbered for the next year', ahead, 'published', 'bar')],
            '$', kind='bar', stacked=True,
            note='Every FLLAC payment on a tuition account, every fund. The year is FLLAC’s '
                 'invoice number; a few invoices carry none.'),
        lead_quote=TP.lead_quote(
            FEB4_QUOTE, 'Christopher McNamara, Business Administrator', 'School Committee',
            '2026-02-04', FEB4_HREF, 'School Committee recording, 4 February 2026',
            FEB4_CAPTIONS, caption=True),
        said=[dict(quote=FEB4_ASK, board='School Committee', date='2026-02-04',
                   href='https://www.youtube.com/watch?v=HsjpFotE9hc&t=3830s',
                   label='A speaker at the same meeting (machine captions)'),
              dict(quote=JUL29_QUOTE, board='School Committee', date='2026-07-29',
                   href='/docs/meetings/school-committee/2026-07-29-minutes-7930.pdf',
                   label='School Committee minutes, 29 July 2026, the business manager'),
              dict(quote=OCT22_QUOTE, board='Finance Committee', date='2026-10-22',
                   href=OCT22_HREF, label='Finance Committee recording (machine captions)')],
        sources=srcs, flow=flow,
        finding_figures={'a': U(out_gf), 'b': U(paid), 'y': F(Y1 + 1), 'z': F(Y1)},
        finding_allow=(d29, d30))
    page['not_established'] = [
        'Whether the school department stands by the 29 June 2026 entry, or has reversed it.',
        'Why the circuit breaker was not drawn from July to May in FY2026.',
        'Whether the 29 June charge and the 30 June prepayment were decided together.',
        'What service period the invoices bill: the journal records no dates of service.',
        'Who approved the payment, and whether the School Committee voted advance tuition.',
    ]
    return page


def outputs():
    pages, _ = build()
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
        print('journal surplus topics: %d outputs current' % len(outs))
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
