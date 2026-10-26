#!/usr/bin/env python3
"""The school surplus, read from the MUNIS journal: the bridge from FY2025 to FY2026, and the
lines under budget in both years. Two topic pages.

    python3 scripts/build_journal_surplus_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_journal_surplus_topics.py --check   # fail if either output would change

    surplus-bridge        /fy2026-closeout/surplus-bridge        Surplus, step by step
    surplus-repeat-lines  /fy2026-closeout/surplus-repeat-lines  Under budget twice

Both on the FY2026 closeout shelf, in the group "Surplus from the journal"
(scripts/topic_registry/fy2026_closeout.py; notes/plans/MUNIS-JOURNAL-REPORTS.md, Hub B;
the method is notes/plans/SCHOOL-SURPLUS-BRIDGE.md).

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

    # ================================================== surplus-repeat-lines
    cl = d['cat_left']
    both = [c for c in CATS if cl[(Y0, c)] > 0 and cl[(Y1, c)] > 0]
    every = [c for c in CATS if all(cl[(y, c)] > 0 for y in J.YEARS)]
    both.sort(key=lambda c: -(cl[(Y0, c)] + cl[(Y1, c)]))
    b0, b1 = sum(cl[(Y0, c)] for c in both), sum(cl[(Y1, c)] for c in both)
    e4 = sum(cl[(y, c)] for c in every for y in J.YEARS)
    lead = both[0]
    # Line by line: every account, by its MUNIS number -- the Town Manager's grain.
    al = defaultdict(lambda: D0)
    for (y, _, a), v in d['acct_left'].items():
        al[(y, a)] += v
    accts = sorted({a for (_, a) in al})
    under = lambda a, y: al[(y, a)] > Decimal('0.005')
    a_both = sorted([a for a in accts if under(a, Y0) and under(a, Y1)],
                    key=lambda a: (-(al[(Y0, a)] + al[(Y1, a)]), a))
    a_every = {a for a in accts if all(under(a, y) for y in J.YEARS)}
    ab0, ab1 = sum(al[(Y0, a)] for a in a_both), sum(al[(Y1, a)] for a in a_both)
    shown = a_both[:ACCOUNT_ROWS]
    sh_share = 100.0 * fl(sum(al[(y, a)] for a in shown for y in (Y0, Y1))) / fl(ab0 + ab1)
    sh0 = 100.0 * fl(b0) / fl(s0)
    if not (b0 < s0 and b1 > s1):
        fail('the first conclusion assumes the repeat categories left part of FY%d’s surplus '
             'and more than all of FY%d’s' % (Y0, Y1))
    if not all(cl[(Y0, c)] > 0 for c in CATS):
        fail('the first conclusion’s note assumes every category was under in FY%d' % Y0)
    if not set(every) <= set(both):
        fail('a category under every year must be under in both')
    ncat = len(CATS)
    rx = {}
    rx['n'] = f('n', N(len(both), 'categories'), 'of %d under budget both years' % ncat,
                'published', {'n': N(ncat, 'categories')})
    rx['b0'] = f('b0', U(b0), 'they left, %s' % C.fy(Y0), 'published', {'y': F(Y0)})
    rx['b1'] = f('b1', U(b1), 'they left, %s, not yet closed' % C.fy(Y1), 'published',
                 {'y': F(Y1)})
    rx['s0'] = f('s0', U(s0), 'the whole surplus, %s' % C.fy(Y0), 'published', {'y': F(Y0)})
    rx['s1'] = f('s1', U(s1), 'the whole surplus, %s, before the close' % C.fy(Y1), 'published',
                 {'y': F(Y1)})
    rx['e'] = f('e', N(len(every), 'categories'), 'under budget every year, %s'
                % C.fyspan(J.YEARS[0], J.YEARS[-1]), 'published',
                {'y': figure(J.YEARS[0], C.fyspan(J.YEARS[0], J.YEARS[-1]), 'fiscal years')})
    rx['e4'] = f('e4', U(e4), 'they left over the four years', 'published')
    rx['l0'] = f('l0', U(cl[(Y0, lead)]), '%s, %s' % (S.CAT_SHORT[lead], C.fy(Y0)), 'published',
                 {'y': F(Y0)})
    rx['l1'] = f('l1', U(cl[(Y1, lead)]), '%s, %s' % (S.CAT_SHORT[lead], C.fy(Y1)), 'published',
                 {'y': F(Y1)})
    rx['an'] = f('an', N(len(a_both), 'accounts'), 'of %s left money both years'
                 % C.num(len(accts)), 'published', {'n': N(len(accts), 'accounts')})
    rx['ab1'] = f('ab1', U(ab1), 'those accounts left, %s' % C.fy(Y1), 'published',
                  {'y': F(Y1)})
    rx['why'] = f('why', None, 'whether budgeted high or run lean', 'gap',
                  closes='the district’s line-by-line budget build-up, with the basis for '
                         'each amount')
    labels_every = [S.CAT_SHORT[c] for c in every]
    listing = ', '.join(labels_every[:-1]) + ' and ' + labels_every[-1]
    out['surplus-repeat-lines'] = TP.page(
        'surplus-repeat-lines',
        '%s budget areas came in under every year from %s to %s; %s of %d did in both %s and %s.'
        % (C.num(len(every)), C.fy(J.YEARS[0]), C.fy(J.YEARS[-1]), C.num(len(both)), ncat,
           C.fy(Y0), C.fy(Y1)),
        list(rx.values()),
        [con('Over those four years, the %s areas left %s between them.'
             % (C.num(len(every)), C.usd(fl(e4))),
             ['e', 'e4'],
             {'n': N(len(every), 'categories'), 'a': U(e4)},
             so='These areas ran under four years running, so each next budget has a record of '
                'years to be set against, not one year’s result.',
             notes=[step('They are %s.' % listing, 'measured')]),
         con('The %s under both years left %s in %s, %s of its surplus; in %s, %s, more than all of it.'
             % (C.num(len(both)), C.usd(fl(b0)), C.fy(Y0), C.pct(sh0, 0), C.fy(Y1), C.usd(fl(b1))),
             ['n', 'b0', 'b1', 's0', 's1'],
             {'n': N(len(both), 'categories'), 'a': U(b0), 'y': F(Y0), 'p': P(sh0, 0), 'b': U(b1), 'z': F(Y1)},
             so='In %s the repeat underspends were larger than the whole surplus: overruns '
                'elsewhere absorbed the rest, so the total hides slack.' % C.fy(Y1),
             so_figures={'y': F(Y1)},
             notes=[step('The surplus as printed was %s, then %s. In %s every category came in under; '
                         'in %s, the categories that ran over used the difference.'
                         % (C.usd(fl(s0)), C.usd(fl(s1)), C.fy(Y0), C.fy(Y1)), 'measured',
                         {'a': U(s0), 'b': U(s1), 'y': F(Y0), 'z': F(Y1)})]),
         con('%s left the most of them over the two years: %s, then %s.'
             % (S.CAT_LABEL[lead], C.usd(fl(cl[(Y0, lead)])), C.usd(fl(cl[(Y1, lead)]))),
             ['l0', 'l1'],
             {'a': U(cl[(Y0, lead)]), 'b': U(cl[(Y1, lead)])},
             so='Its leftover grew almost four times over in a year; it is the one area where '
                'the newer slack is concentrated.'),
         con('Line by line, %s of %s accounts left money in both years; in %s they left %s.'
             % (C.num(len(a_both)), C.num(len(accts)), C.fy(Y1), C.usd(fl(ab1))),
             ['an', 'ab1', 'why'],
             {'n': N(len(a_both), 'accounts'), 'm': N(len(accts), 'accounts'), 'y': F(Y1),
              'a': U(ab1)},
             so='The pattern holds at the grain the Town Manager named in public, line by line, not '
                'only in category totals.',
             notes=[step('The table lists the %s that left the most, %s of the money, by '
                         'account number; %s of them left money in all four years.'
                         % (C.num(len(shown)), C.pct(sh_share, 0),
                            C.num(sum(a in a_every for a in shown))), 'measured',
                         {'n': N(len(shown), 'accounts'), 'p': P(sh_share, 0),
                          'e': N(sum(a in a_every for a in shown), 'accounts')}),
                    step('An account budgeted high and one run lean leave the same postings; '
                         'the journal cannot tell them apart.', 'hypothesis')])],
        chart=TP.ranking('Under budget in both years, by category',
                         [(S.CAT_LABEL[c], [fl(cl[(Y0, c)]), fl(cl[(Y1, c)])]) for c in both],
                         '$', highlight=[S.CAT_LABEL[c] for c in every],
                         stack=[C.fy(Y0), C.fy(Y1)],
                         note='Left unspent, net of accounts that ran over. Strong bars: under '
                              'budget all four years, %s. %s is not yet closed.'
                              % (C.fyspan(J.YEARS[0], J.YEARS[-1]), C.fy(Y1)),
                         note_figures={'r': figure(J.YEARS[0], C.fyspan(J.YEARS[0], J.YEARS[-1]),
                                                   'fiscal years'), 'y': F(Y1)}),
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
        sources=sources(),
        finding_figures={'n': N(len(both), 'categories'), 'm': N(ncat, 'categories'),
                         'y': F(Y0), 'z': F(Y1), 'e': N(len(every), 'categories'),
                         'f': F(J.YEARS[0]), 'g': F(J.YEARS[-1])})
    out['surplus-repeat-lines']['not_established'] = [
        'Whether a category under budget every year was budgeted high, run lean, or paid in '
        'part from another fund.',
        'Why any one account left money: the journal records postings, not reasons.',
        'The FY2026 figures after the close.',
    ]

    out.update(burndown_pages())
    out['surplus-suggestions'] = suggestions_page(d)
    out[PREPAID] = prepaid_page(d)
    if sorted(out) != MINE:
        fail('the pages built are not the pages the registry gives this script: %s vs %s'
             % (sorted(out), MINE))
    return out, d


# ================================================== surplus suggestions
# TJ, 20 October 2026: "so what should the school committee DO or the superintendent to correct
# for this next year?" and "can you put this into a SURPLUS suggestions page". Rule 8 governs it:
# each card is a PLANNING OPTION with what it costs and who bears it, and the question it raises
# for the budget; the page gives the district the credit the record supports; nothing on it
# names a cause, because none of the options depends on one. The page's own conclusions stay
# measurements (topic.py refuses an instruction there); the options live in the cards.
FINCOM_JUNE = '/docs/minutes/text/finance-committee/2026-06-11-minutes-7845.txt'
FINCOM_JUNE_QUOTE = ('The documents needed on this topic were not provided but should be '
                     'available for the next meeting.')


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


def suggestions_page(d):
    import build_buildings_topics as BB
    src = os.path.join(ROOT, 'sources', 'meetings', 'text',
                       FINCOM_JUNE.split('/docs/minutes/text/')[1])
    if FINCOM_JUNE_QUOTE not in ' '.join(open(src, encoding='utf-8').read().split()):
        fail('the Finance Committee quotation is no longer verbatim in %s' % FINCOM_JUNE)
    U = lambda v: figure(fl(v), C.usd(fl(v)))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    f, con = LD.fact, TP.conclusion
    A = J.accounts()
    gf = [r for r in J.lines() if J.in_surplus_scope(A[r['account']])]
    # ---- the leftover, by account, every year
    al = defaultdict(lambda: D0)
    for (y, _, a), v in d['acct_left'].items():
        al[(y, a)] += v
    accts = sorted({a for (_, a) in al})
    every = [a for a in accts if all(al[(y, a)] > Decimal('0.005') for y in J.YEARS)]
    s25 = spread([al[(Y0, a)] for a in accts])
    s26 = spread([al[(Y1, a)] for a in accts])
    over = {y: -sum((al[(y, a)] for a in accts if al[(y, a)] < 0), D0) for y in (Y0, Y1)}
    cl = d['cat_left']
    cats_every = [c for c in CATS if all(cl[(y, c)] > 0 for y in J.YEARS)]
    # ---- timing: the burndown's March
    bud, cum = curves(gf, lambda r: r['fy'])
    mar = {y: left_pct(bud, cum, y, MARCH) for y in J.YEARS}
    # ---- year-end transfers between lines
    moved = defaultdict(lambda: D0)
    for r in gf:
        if r['source'] == 'BUA' and not J.is_carry_forward(r) and int(r['period']) == JUNE \
                and r['amt'] > 0:
            moved[r['fy']] += r['amt']
    # ---- building upkeep, from its own generator
    bd = BB.data()
    up_o = (bd['orig'][J.YEARS[0]], bd['orig'][Y1])
    up_s = (bd['spent'][J.YEARS[0]], bd['spent'][Y1])
    grow = lambda a, b: 100.0 * (fl(b) - fl(a)) / fl(a)
    cat = lambda r: S.category_of(dict(account=r['account'], obj=r['object']))
    up_lines = [r for r in gf if cat(r) == 'buildings']
    # By ACCOUNT, as the ledger counts them: one order split across two accounts is two releases.
    up_rel = {}
    for a in sorted({r['account'] for r in up_lines}):
        _, rel_a, _ = BB.orders([r for r in up_lines if r['account'] == a])
        up_rel.update({(a, k): v for k, v in rel_a.items()})
    cbs_lines = [r for r in up_lines if r['account'] == BB.SERVICES]
    _, cbs_rel, cbs_soy = BB.orders(cbs_lines)
    carried_rel = sum((v for k, v in cbs_rel.items() if cbs_soy[k] > 0), D0)
    released = sum(up_rel.values(), D0)
    book = BB.book()
    (gl0, ga0), (gl1, ga1) = BB.GROUNDS
    # ---- the circuit breaker
    monthly = defaultdict(lambda: D0)
    for r in J.sped_actuals():
        if J.sped_fund(A[r['account']]) == 'Circuit breaker' and r['fy'] == Y1:
            monthly['june' if int(r['period']) == JUNE else 'early'] += r['amt']
    cb_off = Decimal(CB_BOOK.split()[1].replace(',', '').lstrip('-'))
    # ---- what the record gives the district credit for (rule 8)
    up26 = [a for a in bd['accounts'] if any(bd['acct'][(Y1, a, k)] for k in ('orig', 'trans', 'spent', 'enc'))]
    up_over = [a for a in up26 if bd['acct_left'](Y1, a) < 0]
    if up_over:
        fail('the credit conclusion assumes no upkeep account ran over in FY%d' % Y1)
    open26 = d['piece'].get((Y1, 'encumbrance'), D0)
    if not (len(every) > 20 and mar[Y1] > mar[J.YEARS[0]] and s25['top'] < s25['total'] / 10):
        fail('the suggestions page’s conclusions no longer match the data')

    fx = dict(
        n25=f('n25', N(s25['n'], 'accounts'), 'left money in %s' % C.fy(Y0), 'published', {'y': F(Y0)}),
        top=f('top', P(100.0 * fl(s25['top']) / fl(s25['total']), 0), 'of it on the largest one',
              'published'),
        every=f('every', N(len(every), 'accounts'), 'under budget every year, %s'
                % C.fyspan(J.YEARS[0], Y1), 'published',
                {'y': figure(J.YEARS[0], C.fyspan(J.YEARS[0], Y1), 'fiscal years')}),
        m23=f('m23', P(mar[J.YEARS[0]]), 'budget left at end of March, %s' % C.fy(J.YEARS[0]),
              'published', {'y': F(J.YEARS[0])}),
        m26=f('m26', P(mar[Y1]), 'budget left at end of March, %s' % C.fy(Y1), 'published',
              {'y': F(Y1)}),
        rel=f('rel', U(released), 'upkeep orders released unpaid, %s' % C.fy(Y1), 'published',
              {'y': F(Y1)}),
        cb=f('cb', U(cb_off), 'tuition budget set lower for the circuit breaker', 'published'),
        mv=f('mv', U(moved[Y0]), 'moved between lines in June, %s' % C.fy(Y0), 'published',
             {'y': F(Y0)}),
        ov=f('ov', U(over[Y1]), 'spent past budget, %s, before its close' % C.fy(Y1), 'published',
             {'y': F(Y1)}),
        uo=f('uo', N(len(up26), 'accounts'), 'upkeep accounts, none over budget', 'published'),
    )
    q = lambda label, rows: dict(title=label, columns=[''], rows=[(k, [v]) for k, v in rows])
    fy = C.fy
    cards = [
        dict(id='actuals', open=True, label='Build next year’s lines from actual spending',
             account='Who: the Superintendent and the business manager, with the School Committee',
             left=C.num(len(every)), value_label='accounts under budget every year, %s'
             % C.fyspan(J.YEARS[0], Y1),
             shape='%s of %s accounts, and %s of %s budget areas, left money in every year from %s '
                   'to %s.' % (C.num(len(every)), C.num(len(accts)), C.num(len(cats_every)),
                               C.num(len(CATS)), fy(J.YEARS[0]), fy(Y1)),
             figures=[('Upkeep budget, %s' % C.fyspan(J.YEARS[0], Y1), '+' + C.pct(grow(*up_o), 0)),
                      ('Upkeep spending', '+' + C.pct(grow(*up_s), 0))],
             sections=[q('The option', [
                 ('The question for the budget', 'What is each line’s request against its last '
                  'three years of actual spending, and what is the basis where it is higher?'),
                 ('What it costs', 'Less cushion: some lines will run short in the year and need a '
                  'transfer the Committee votes, in the open.'),
                 ('Who bears it', 'The business office, in a longer budget build; the Committee, in '
                  'more transfer votes.')])],
             quotes=[dict(quote=TM_QUOTE, href=TM_HREF,
                          label='The Town Manager, Select Board minutes, 9 September 2025')],
             unknown='why these lines are set above what they spend: caution, a level-service rule '
                     'carried forward and vacancies all fit.',
             closes='the district’s line-by-line budget build-up, with the basis for each line'),
        dict(id='reforecast', label='Reforecast the year in February or March',
             account='Who: the business manager reports; the School Committee decides',
             left=C.pct(mar[Y1]), value_label='of the budget left at the end of March, %s' % fy(Y1),
             shape='At the end of March %s had %s left; %s had %s. The gap opens in February.'
                   % (fy(Y1), C.pct(mar[Y1]), fy(J.YEARS[0]), C.pct(mar[J.YEARS[0]])),
             figures=[('March, %s' % fy(2024), C.pct(mar[2024])), ('March, %s' % fy(Y0), C.pct(mar[Y0]))],
             sections=[q('The option', [
                 ('The question for the budget', 'What does the spring forecast say will lapse, '
                  'line by line, and should any of it be moved before June by transfer?'),
                 ('What it costs', 'Staff time, and a risk of buying for its own sake: a forecast '
                  'surplus would fund priorities already planned, not whatever can be ordered.'),
                 ('Who bears it', 'The business office; the Committee, which votes the transfers.')])],
             quotes=[],
             unknown='how much of a spring gap is timing, as with health insurance posted in June, '
                     'and how much will lapse.',
             closes='a spring year-end forecast by line, from the business office'),
        dict(id='orders', label='Review open purchase orders every quarter',
             account='Who: the business office',
             left=C.usd(fl(released)), value_label='building upkeep orders released unpaid, %s' % fy(Y1),
             shape='%s of %s’s orders on contracted building services were budgeted again in %s and '
                   'closed unpaid on 30 June.' % (C.usd(fl(carried_rel)), fy(Y0), fy(Y1)),
             figures=[('Open orders when the %s report ran' % fy(Y1), C.usd(fl(open26)))],
             sections=[q('The option', [
                 ('The question for the budget', 'Which open orders are still needed, and which '
                  'should be closed so the money is seen as available before June?'),
                 ('What it costs', 'A quarterly review in the business office; nothing else.'),
                 ('Who bears it', 'The business office.')])],
             quotes=[],
             unknown='whether a released order’s job was done another way.',
             closes='the facilities work orders, matched to each purchase order'),
        dict(id='circuit-breaker', label='Budget the circuit breaker in the open',
             account='Who: the business manager',
             left=C.usd(fl(cb_off)), value_label='collaborative tuition budgeted lower, for the '
             'circuit breaker',
             shape='The reimbursement arrived as one June entry of %s; July to May the fund paid %s.'
                   % (C.usd(fl(monthly['june'])), C.usd(fl(monthly['early']))),
             figures=[],
             sections=[q('The option', [
                 ('The question for the budget', 'What is tuition’s gross cost, what circuit '
                  'breaker money is expected, and how do the two compare each quarter?'),
                 ('What it costs', 'Two lines where there is one; a quarterly reconciliation.'),
                 ('Who bears it', 'The business manager.')])],
             quotes=[],
             unknown='why the reimbursement was taken in one entry at year end.',
             closes='the district’s circuit breaker claim and the state’s payment schedule'),
        dict(id='ledger', label='Check the ledger against the voted budget',
             account='Who: the business office, once a year',
             left=C.num(2), value_label='grounds lines loaded the other way round',
             shape='The budget book puts %s on grounds contracted services and %s on grounds '
                   'supplies; MUNIS holds them the other way round.'
                   % (C.usd(fl(book[gl0][1])), C.usd(fl(book[gl1][1]))),
             figures=[],
             sections=[q('The option', [
                 ('The question for the budget', 'Does every MUNIS line hold the figure the '
                  'Committee voted for it?'),
                 ('What it costs', 'A one-time comparison when the budget is loaded.'),
                 ('Who bears it', 'The business office.')])],
             quotes=[],
             unknown='whether any other line was loaded differently from the book.',
             closes='the voted budget against the MUNIS original appropriation, line by line'),
        dict(id='monthly', label='Report budget against actual every month',
             account='Who: the School Committee, as a standing item',
             left=C.usd(fl(moved[Y0])), value_label='moved between lines in June, %s' % fy(Y0),
             shape='After those transfers %s ran over by %s; %s, before its own, by %s.'
                   % (fy(Y0), C.usd(fl(over[Y0])), fy(Y1), C.usd(fl(over[Y1]))),
             figures=[],
             sections=[q('The option', [
                 ('The question for the budget', 'What does this month’s year-to-date report show, '
                  'line by line, against the plan?'),
                 ('What it costs', 'Little: MUNIS already prints the report each month.'),
                 ('Who bears it', 'The business office prepares it; the Committee reads it.')])],
             quotes=[dict(quote=FINCOM_JUNE_QUOTE, href=FINCOM_JUNE,
                          label='Finance Committee minutes, 11 June 2026, on year-end transfers')],
             unknown='which lines the June transfers covered, and why.',
             closes='the FY2025 year-end transfer memos, with the line each covered'),
    ]
    led = TP.check_ledger(TP.ledger(
        'Six options, each with what it costs',
        'Options, not findings: each rests on the figures above it, and none depends on knowing '
        'why the money was left. Open a card for the question it raises for the budget.', cards),
        'surplus-suggestions')
    page = TP.page(
        'surplus-suggestions',
        'The surplus came from many small leftovers, year after year, not one line; these '
        'options follow from that.',
        list(fx.values()),
        [con('%s’s leftover was spread over %s accounts; the largest held %s of it.'
             % (fy(Y0), C.num(s25['n']), C.pct(100.0 * fl(s25['top']) / fl(s25['total']), 0)),
             ['n25', 'top'],
             {'y': F(Y0), 'n': N(s25['n'], 'accounts'),
              'p': P(100.0 * fl(s25['top']) / fl(s25['total']), 0)},
             so='No single line explains the surplus, so a remedy aimed at one account would '
                'leave most of it in place.',
             notes=[step('Half of it sat on %s accounts and four fifths on %s.'
                         % (C.num(s25['half']), C.num(s25['most'])), 'measured',
                         {'a': N(s25['half'], 'accounts'), 'b': N(s25['most'], 'accounts')})]),
         con('%s accounts left money in every year from %s to %s.'
             % (C.num(len(every)), fy(J.YEARS[0]), fy(Y1)), ['every'],
             {'n': N(len(every), 'accounts'), 'a': F(J.YEARS[0]), 'b': F(Y1)},
             so='These are the accounts where a budget built from recent spending would differ '
                'most from the one voted.'),
         con('By the end of March %s had %s of its budget left, against %s in %s.'
             % (fy(Y1), C.pct(mar[Y1]), C.pct(mar[J.YEARS[0]]), fy(J.YEARS[0])), ['m23', 'm26'],
             {'y': F(Y1), 'a': P(mar[Y1]), 'b': P(mar[J.YEARS[0]]), 'z': F(J.YEARS[0])},
             so='The surplus was visible in the monthly report by spring, months before the '
                'close and before the next budget was voted.'),
         con('None of the %s building upkeep accounts ran over in %s.' % (C.num(len(up26)), fy(Y1)),
             ['uo'], {'n': N(len(up26), 'accounts'), 'y': F(Y1)},
             so='Credit where the ledger shows it: upkeep was kept inside its budget on every '
                'account, and an emergency went to a public vote.',
             notes=[step('And %s’s unbudgeted emergency cabling went to the Finance Committee as a '
                         'Reserve Fund vote, in the open.' % fy(Y0), 'measured', {'y': F(Y0)},
                         cite=(BB.FINCOM, 'Finance Committee minutes, 13 February 2025'))])],
        chart=TP.parts(
            'How spread out the leftover was',
            [('Largest %s accounts' % C.num(s25['half']), fl(sum(s25['v'][:s25['half']], D0))),
             ('Next %s' % C.num(s25['most'] - s25['half']),
              fl(sum(s25['v'][s25['half']:s25['most']], D0))),
             ('The other %s' % C.num(s25['n'] - s25['most']), fl(sum(s25['v'][s25['most']:], D0)))],
            '$',
            note='%s, the accounts that came in under budget, by how much each left. %s, because '
                 'nothing in it ran over to offset it.' % (fy(Y0), fy(Y0)),
            note_figures={'y': F(Y0)}),
        sources=sources() + [
            dict(label='Town of Lunenburg — Select Board minutes, 9 September 2025', href=TM_HREF),
            dict(label='Town of Lunenburg — Finance Committee minutes, 11 June 2026', href=FINCOM_JUNE)],
        finding_figures={})
    page['ledger'] = led
    page['not_established'] = [
        'Why the lines are budgeted above what they spend: nothing here tests a cause, and none of '
        'the options needs one.',
        'Whether 1.8 per cent unspent is unusual: no peer district’s year-end variance is in hand.',
        'The FY2026 figures after the close.',
    ]
    return page


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
SC_MINUTES = 'sources/meetings/text/school-committee'
SPECREV = 'sources/town-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx'
BOOK26_TEXT = ('sources/district-budget/text/'
               'final-fy26-sc-approved-budget-3-12-25-with-level-service-budget.txt')
DESE_CB_FAQ = 'https://www.doe.mass.edu/finance/circuitbreaker/faq.html'


def _captions(path):
    return ' '.join(x['text'] for x in
                    json.load(open(os.path.join(ROOT, path), encoding='utf-8'))['segments'])


def prepaid_page(d):
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
    # The record: no warrant for 18 June to 5 July, and no advance-tuition vote, in the minutes.
    mins = sorted(glob.glob(os.path.join(ROOT, SC_MINUTES, '2026-0[4-8]-*minutes*.txt')))
    text = {os.path.basename(m)[:10]: ' '.join(open(m, encoding='utf-8').read().split()) for m in mins}
    # Every warrant period the Committee approved, as (month, day) of its first and last day.
    spans = [((int(a), int(b)), (int(c), int(e))) for t in text.values() for a, b, c, e in
             re.findall(r'[Ww]arrants:? (\d+)/(\d+)(?:/\d+)? (?:to|-|–) (\d+)/(\d+)', t)]
    if not spans:
        fail('no warrant periods read from the School Committee minutes; the pattern broke')
    if any(lo <= (7, 5) and hi >= (6, 18) for lo, hi in spans):
        fail('a School Committee warrant covering 18 June to 5 July now appears in the minutes')
    if any(re.search(r'71D|\bprepa(?:y|id|ying|yment)\b|advance (?:tuition|payment)|'
                     r'tuitions? in advance', t, re.I) for t in text.values()):
        fail('a School Committee minute now mentions advance tuition; re-read it')
    if not TP.verbatim_in(JUL29_QUOTE, open(os.path.join(ROOT, JUL29_TEXT), encoding='utf-8').read()):
        fail('the 29 July quotation is no longer in the minutes')
    for q, p_ in ((FEB4_ASK, FEB4_CAPTIONS), (OCT22_QUOTE, OCT22_CAPTIONS)):
        if not TP.verbatim_in(q, _captions(p_)):
            fail('a quotation is no longer in the captions %s' % p_)

    fx = {}
    fx['paid'] = f('paid', U2(paid), 'paid to FLLAC from the general fund, 30 June 2026',
                   'published', allow=('30 June 2026',))
    fx['n'] = f('n', N(len(early), 'invoices'), 'invoices, all numbered for %s' % C.fy(Y1 + 1),
                'published', {'y': F(Y1 + 1)})
    fx['r27'] = f('r27', U2(std[Y1 + 1]), 'the quarterly rate on those invoices', 'published')
    fx['r26'] = f('r26', U2(std[Y1]), 'the rate on every %s-numbered invoice' % C.fy(Y1),
                  'published', {'y': F(Y1)})
    fx['recl'] = f('recl', U2(out_gf), 'charged to the circuit breaker instead, 29 June 2026',
                   'published', allow=('29 June 2026',))
    fx['before'] = f('before', U(paid_before), 'already paid on the line before 30 June',
                     'published', allow=('30 June',))
    fx['budget'] = f('budget', U(budget), 'the line’s %s budget, never added to by transfer'
                     % C.fy(Y1), 'published', {'y': F(Y1)})
    fx['left'] = f('left', U(d['left'][Y1]), '%s left, as reported' % C.fy(Y1), 'published',
                   {'y': F(Y1)})
    fx['without'] = f('without', U(without), '%s left without the payment (our sum)' % C.fy(Y1),
                      'published', {'y': F(Y1)})
    fx['owed25'] = f('owed25', U(owed[Y0]), '%s left, counted the same way' % C.fy(Y0),
                     'published', {'y': F(Y0)})
    fx['period'] = f('period', None, 'the service period the invoices bill', 'gap',
                     closes='FLLAC’s invoices 27L2KEY11 to 27L2KEY19, with their service dates',
                     allow=('27', '11', '19'))
    fx['approval'] = f('approval', None, 'who approved the payment', 'gap',
                       closes='the signed warrant that paid check %s, with the School '
                              'Committee’s approval of it' % check, allow=(check,))
    conclusions = [
        con('On 30 June the general fund paid %s on %s FLLAC invoices numbered, and priced, '
            'for %s.' % (C.usd(fl(paid)), C.num(len(early)), C.fy(Y1 + 1)),
            ['paid', 'n', 'r27', 'r26', 'period'],
            {'a': U(paid), 'n': N(len(early)), 'y': F(Y1 + 1)}, allow=('30 June',),
            so='If they pay for %s, %s’s surplus reads %s smaller than what %s needed for itself.'
               % (C.fy(Y1 + 1), C.fy(Y1), C.usd(fl(paid)), C.fy(Y1)),
            so_figures={'y': F(Y1 + 1), 'z': F(Y1), 'a': U(paid)},
            notes=[step('That they bill %s’s first quarter is our reading: each invoice prefix '
                        'was paid in its own year, %s had paid four quarters, and the rate is '
                        'new.' % (C.fy(Y1 + 1), C.fy(Y1)),
                        'hypothesis', {'y': F(Y1 + 1), 'z': F(Y1)})]),
        con('Taken back out, %s left %s, more than %s’s %s counted the same way.'
            % (C.fy(Y1), C.usd(fl(without)), C.fy(Y0), C.usd(fl(owed[Y0]))),
            ['left', 'without', 'owed25'],
            {'y': F(Y1), 'a': U(without), 'z': F(Y0), 'b': U(owed[Y0])},
            so='In July the Committee heard %s would close well below %s. That holds as reported '
               'and reverses with this payment taken out.' % (C.fy(Y1), C.fy(Y0)),
            so_figures={'y': F(Y1), 'z': F(Y0)}),
        con('The day before, %s of %s tuition was charged to the circuit breaker instead of the '
            'general fund.' % (C.usd(fl(out_gf)), C.fy(Y1)), ['recl'],
            {'a': U(out_gf), 'y': F(Y1)},
            so='General fund money unspent at year end returns to the town as free cash; circuit '
               'breaker money, the district says, can carry a year.',
            notes=[step('That the two entries were made together, for that purpose, is a '
                        'hypothesis; moving tuition onto the circuit breaker at year end is '
                        'routine, and no document links them.', 'hypothesis')]),
        con('No School Committee minutes record an advance-tuition vote or a warrant for '
            '18 June to 5 July.', ['approval', 'before', 'budget'],
            allow=('18 June', '5 July'),
            so='The line had already paid more than its budget, and no transfer covered it; the '
               'signed warrant would show who approved the payment.',
            notes=[step('Approval may exist off the minutes: year-end warrants are often signed '
                        'between meetings.', 'gap',
                        closes='the signed warrant for check %s' % check, allow=(check,))])]

    # The circuit breaker fund itself: what came in (CRP receipts) and what it paid, by year.
    cb = [r for r in J.lines() if r['fund'] == '2640']
    cb_in = [-fl(sum((r['amt'] for r in cb if r['fy'] == y and r['source'] == 'CRP'), D0))
             for y in J.YEARS]
    cb_out = [fl(sum((r['amt'] for r in cb if r['fy'] == y and J.COLUMN_OF[r['source']] == 'actual'
                      and r['source'] != 'CRP'), D0)) for y in J.YEARS]
    cb_early = fl(sum((r['amt'] for r in cb if r['fy'] == Y1 and r['source'] == 'API'), D0))
    if not (max(cb_in) == cb_in[J.YEARS.index(Y0)] and cb_in[J.YEARS.index(Y0)]
            > cb_out[J.YEARS.index(Y0)] and cb_early < 10000):
        fail('the circuit breaker block assumes FY%d took in the most and FY%d paid almost '
             'nothing before June' % (Y0, Y1))
    # The fund's balance, from the Town's special-revenue report at 31 March 2026 (period 9,
    # published with the period-9 package), carried to 30 June with the journal's own entries.
    # DESE: "FY26 reimbursements must be spent ... in FY26 and/or FY27, and cannot be carried
    # into FY28" (circuit breaker FAQ, question 10). One fund, 2640, holds every year's money,
    # so which dollars are "older" is our arithmetic: what the fund held on 1 July 2025, less
    # what FY2026 spent before the re-charge, could only be FY2025's or earlier.
    import openpyxl
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
    # When the fund was DRAWN, FY2025 against FY2026: what the budget book planned it to pay,
    # what it paid July to May, and in June (payments and re-charges; receipts excluded).
    drawn = lambda y, june: fl(sum((r['amt'] for r in cb if r['fy'] == y
                                    and J.COLUMN_OF[r['source']] == 'actual' and r['source'] != 'CRP'
                                    and (r['effective_date'][5:7] == '06') == june), D0))
    # Planned: FY2025 the ADJ FY25 journal line; FY2026 the circuit breaker offset the FY2026
    # budget book prints under 9400 Collaborative Tuitions, read from our copy of the book.
    book26 = ' '.join(open(os.path.join(ROOT, BOOK26_TEXT), encoding='utf-8').read().split())
    m26 = re.search(r'Circuit Breaker \(70% = \$[\d,]+\) \(75% = [\d,]+\) \([\d,.]+\)\$ '
                    r'\(([\d,.]+)\)\$', book26)
    if not m26:
        fail('the FY2026 circuit breaker offset is no longer in %s' % BOOK26_TEXT)
    plan = {Y0: fl(-d['adj']), Y1: float(m26.group(1).replace(',', ''))}
    if not (drawn(Y0, False) > 100 * drawn(Y1, False) and drawn(Y1, True) > drawn(Y0, True)):
        fail('the timing block assumes FY%d drew the fund through the year and FY%d in June'
             % (Y0, Y1))
    older = open_bal - sr_exp           # what could only be FY2025's money or earlier
    june_bal = mar_bal - out_gf          # after the 29 June re-charge (our arithmetic)
    if not (out_gf > older > 0 and june_bal < sr_rev):
        fail('the circuit breaker block assumes the re-charge used all the older money')
    yrs = J.YEARS
    same = [fl(sum((r['amt'] for r in rows if r['fy'] == y and r not in early), D0)) for y in yrs]
    ahead = [fl(sum((r['amt'] for r in early if r['fy'] == y), D0)) for y in yrs]
    record = [
        ('4 February 2026', 'School Committee', 'Prepaying special education tuition named as a use '
         'for a large year-end leftover; an open conversation called for if leftover is spent '
         'before it reaches free cash', 'recording'),
        ('24 June 2026', 'School Committee', 'Four line-item transfers and the carry-forward '
         'orders voted; no tuition payment among them', 'minutes, recording'),
        ('29 June 2026', 'Journal', 'Collaborative tuition the general fund had paid charged to '
         'the circuit breaker instead', 'journal %s' % recl[0]['journal']),
        ('30 June 2026', 'Journal', 'Nine FLLAC invoices numbered for %s paid from the general '
         'fund, check %s' % (C.fy(Y1 + 1), check), 'journal %s' % jnl),
        ('29 July 2026', 'School Committee', 'Told %s would close well below the year before'
         % C.fy(Y1), 'minutes'),
        ('22 October 2026', 'Finance Committee', 'Prepaying a first quarter from circuit breaker '
         'money explained as a rule; this payment not mentioned', 'recording'),
    ]
    page = TP.page(
        PREPAID,
        'On 30 June 2026 the school general fund paid %s on FLLAC invoices numbered for %s.'
        % (C.usd(fl(paid)), C.fy(Y1 + 1)),
        list(fx.values()), conclusions,
        chart=TP.series(
            'FLLAC tuition paid, by year it was paid', [C.fy(y) for y in yrs],
            [TP.track('Invoices numbered for that year', same, 'published', 'bar'),
             TP.track('Invoices numbered for the next year', ahead, 'published', 'bar')],
            '$', kind='bar', stacked=True,
            note='Every FLLAC payment on a tuition account, every fund. The year is FLLAC’s '
                 'invoice number; a few invoices carry none.'),
        also=[TP.series(
            'What was left, with and without the payment', [C.fy(Y0), C.fy(Y1)],
            [TP.track('Left, counting orders still owed', [fl(owed[Y0]), fl(owed[Y1])],
                      'published', 'bar'),
             TP.track('Without the 30 June payment (our sum)', [None, fl(without)], 'estimate',
                      'bar')],
            '$', kind='bar',
            note='School general fund, department 300. Counting orders owed is the footing on '
                 'Surplus by year.', note_allow=('300',))],
        blocks=[TB.explain('A payment, not a transfer', [
            'A **transfer** moves budget from one line to another; no money leaves, and the '
            'School Committee votes each one. A **reclass** moves a cost already paid from one '
            'fund to another. A **payment** sends money to a vendor, on a warrant.',
            ('The 30 June entry is a payment. It was charged to a line that had already spent past '
             'its budget, and was covered, inside the school total, by other lines’ leftovers.',
             None, ('30 June',))],
            place='lead', tone='define'),
            TB.chart(TP.series(
                'The circuit breaker fund, in and out', [C.fy(y) for y in J.YEARS],
                [TP.track('Received from the state', cb_in, 'published', 'bar'),
                 TP.track('Paid out, or charged to it', cb_out, 'published', 'bar')],
                '$', kind='bar',
                note='Fund 2640, from the school journal. The fund’s balance is not in the '
                     'journal, so what would have expired is not known.', note_allow=('2640',)),
                place='body',
                so=('%s took in the most and %s paid almost nothing from it until the 29 June '
                    're-charge. That it was spent before receipts expired fits, as a hypothesis.'
                    % (C.fy(Y0), C.fy(Y1)), {'y': F(Y0), 'z': F(Y1)}, ('29 June',))),
            TB.panels('The circuit breaker fund, before and after', [
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
                note='One fund holds every year’s money, so older money is what it held at the '
                     'start of the year less what the year spent before June. The Town’s '
                     'special-revenue report, then the school journal.',
                so=('Without the re-charge, %s would have passed the state’s one-year limit. The '
                    're-charge used all of it, and %s carries into %s.'
                    % (C.usd(fl(older)), C.usd(fl(june_bal)), C.fy(Y1 + 1)),
                    {'a': U(older), 'b': U(june_bal), 'y': F(Y1 + 1)})),
            TB.panels('When the circuit breaker was drawn', [
                TB.panel('The year before', [
                    ('Planned to pay tuition (budget)', C.usd(plan[Y0]), None),
                    ('Drawn July to May', C.usd(drawn(Y0, False)), 'good'),
                    ('Drawn in June', C.usd(drawn(Y0, True)), None),
                    ('Left in the fund at year end', C.usd(fl(open_bal)), None)]),
                TB.panel('The year of this surplus', [
                    ('Planned to pay tuition (budget)', C.usd(plan[Y1]), None),
                    ('Drawn July to May', C.usd(drawn(Y1, False)), 'bad'),
                    ('Drawn in June', C.usd(drawn(Y1, True)), None),
                    ('Left in the fund at year end (ours)', C.usd(fl(june_bal)), None)])],
                place='body',
                note='The state pays each year’s reimbursement for the year before, and the money '
                     'is spent within a year of arriving, or not at all. Month by month: Special '
                     'education burndown.',
                so=('One year drew the fund as bills came in; the next left it untouched until the '
                    'year’s last days. Why is not in any document held.', None, ())),
            TB.explain('The record, in order', [
                ('**%s, %s.** %s. (%s)' % (w, b_, c_, e_), None,
                 tuple(re.findall(r'\d[\d,]*', '%s %s %s' % (w, c_, e_))))
                for w, b_, c_, e_ in record], place='body', tone='plain'),
            TB.explain('What the record shows, and does not', [
                ('**Allowed.** State law lets a school committee approve paying up to three months '
                 'of tuition in advance (G.L. c. 71, s. 71D), and the state’s Division of Local '
                 'Services uses this case as its example: a July to September bill, due 30 June, '
                 'charged to the year that is ending.', None, ('71', '71D', '30 June')),
                ('**Not announced.** Every June and July 2026 meeting of the School Committee, '
                 'Finance Committee and Select Board was read, minutes and recordings. None '
                 'mentions this payment or the re-charge to the circuit breaker. No minutes record '
                 'an advance-tuition vote, or a warrant covering the last two weeks of June.',
                 None, ('2026',)),
                ('**Not yet held.** The signed warrant, FLLAC’s invoices with their service '
                 'dates, and the School Committee’s September year-end budget reviews. Each is a '
                 'registered gap, listed on What we cannot answer.', None, ())],
                place='end', tone='plain')],
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
        sources=sources() + [
            dict(label='Lunenburg School Committee — 2026-07-29-minutes-7930.pdf',
                 href='/docs/meetings/school-committee/2026-07-29-minutes-7930.pdf'),
            dict(label='Lunenburg School Committee — 2026-06-24 minutes',
                 href='/docs/minutes/text/school-committee/2026-06-24-minutes-7869.txt'),
            dict(label='School Committee recording, 4 February 2026', href=FEB4_HREF),
            dict(label='Finance Committee recording, 22 October 2026', href=OCT22_HREF),
            dict(label='G.L. c. 71, s. 71D — advance payment of tuition',
                 href='https://malegislature.gov/Laws/GeneralLaws/PartI/TitleXII/Chapter71/section71D'),
            dict(label='Town of Lunenburg — special-revenue-fy2026-p09.xlsx (fund balances, '
                       '31 March 2026)',
                 href='/docs/town-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx'),
            dict(label='DESE — circuit breaker FAQ, question 10 (the one-year carry-forward)',
                 href=DESE_CB_FAQ),
            dict(label='Division of Local Services — prepayment from prior fiscal year funds',
                 href='https://www.mass.gov/info-details/ask-dls-prepayment-from-prior-fiscal-year-funds')],
        finding_figures={'a': U(paid), 'y': F(Y1 + 1)}, finding_allow=('30 June 2026',))
    page['not_established'] = [
        'What service period the invoices bill: the journal records no dates of service.',
        'Who approved the payment, and whether the School Committee voted advance tuition.',
        'Whether the 29 June reclass and the 30 June payment were made together on purpose.',
        'Whether this happened before FY2023: the journal begins there.',
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
