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
TM_MINUTES = '/docs/minutes/text/select-board/2025-09-09-minutes-7393.txt'
TM_QUOTE = ('the FY26 budget, which was developed by the prior team, would need to be reviewed '
            'line by line to determine whether the same assumptions that produced the FY25 '
            'surplus are embedded in the current year\'s budget')
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


def build():
    verbatim()
    d = data()
    U = lambda v: figure(fl(v), C.usd(fl(v)))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    f, con = LD.fact, TP.conclusion
    pc = lambda y, p: d['piece'].get((y, p), D0)
    out = {}

    # ================================================== surplus-bridge
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
    if not (s1 < s0 and db > 0 and ds > 0 and open1 > 0):
        fail('the bridge conclusions assume the surplus fell while budget and spending rose')
    pay_pct = 100.0 * fl(dv('payroll')) / fl(pc(Y0, 'payroll'))
    inv_pct = 100.0 * fl(dv('invoice')) / fl(pc(Y0, 'invoice'))
    with301 = s1 + d['left301']
    if d['left301'] >= 0:
        fail('the department 301 note assumes the curriculum line ran over')
    tr0, tr1 = pc(Y0, 'transfer'), pc(Y1, 'transfer')
    closed = [d['closed'][y] for y in J.YEARS[:-1]]
    if not open1 > max(closed):
        fail('the open-orders conclusion assumes FY%d holds more than any closed year' % Y1)

    fx = {}
    fx['s0'] = f('s0', U(s0), 'left unspent, %s' % C.fy(Y0), 'published', {'y': F(Y0)})
    fx['s1'] = f('s1', U(s1), 'left unspent, %s, before the close' % C.fy(Y1), 'published',
                 {'y': F(Y1)})
    fx['db'] = f('db', U(db), 'more budget in %s than in %s' % (C.fy(Y1), C.fy(Y0)), 'published',
                 {'y': F(Y1), 'z': F(Y0)})
    fx['ds'] = f('ds', U(ds), 'more spent in %s than in %s' % (C.fy(Y1), C.fy(Y0)), 'published',
                 {'y': F(Y1), 'z': F(Y0)})
    fx['open'] = f('open', U(open1), 'open encumbrances, %s' % C.fy(Y1), 'published',
                   {'y': F(Y1)})
    fx['pay'] = f('pay', U(dv('payroll')), 'more through payroll', 'published')
    fx['inv'] = f('inv', U(dv('invoice')), 'more through vendor invoices', 'published')
    fx['je'] = f('je', U(dv('journal entry')), 'more through journal entries', 'published')
    fx['adj'] = f('adj', U(-d['adj']), 'off collaborative tuitions, 1 July 2024', 'published',
                  allow=('1 July 2024',))
    fx['tr0'] = f('tr0', U(tr0), 'transfers and adjustments, %s' % C.fy(Y0), 'published',
                  {'y': F(Y0)})
    fx['tr1'] = f('tr1', U(tr1), 'transfers and adjustments, %s' % C.fy(Y1), 'published',
                  {'y': F(Y1)})
    fx['max'] = f('max', U(s1 + open1), 'left before open orders, %s' % C.fy(Y1), 'published',
                  {'y': F(Y1)})

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
    piece_rows.append(dict(label='Left unspent', cells=[C.usd(fl(d['left'][y])) for y in J.YEARS]))

    out['surplus-bridge'] = TP.page(
        'surplus-bridge',
        '%s’s leftover is %s to %s, depending on %s of purchase orders still open.'
        % (C.fy(Y1), C.usd(fl(s1)), C.usd(fl(s1 + open1)), C.usd(fl(open1))),
        list(fx.values()),
        [con('Before open orders, %s left %s, more than %s’s %s: the budget grew more than '
             'spending.' % (C.fy(Y1), C.usd(fl(s1 + open1)), C.fy(Y0), C.usd(fl(s0))),
             ['s0', 's1', 'db', 'ds', 'open', 'max'],
             {'y': F(Y1), 'a': U(s1 + open1), 'z': F(Y0), 'b': U(s0)},
             notes=[step('%s, plus %s more budget, less %s more spent and %s in open orders, '
                         'is %s.' % (C.usd(fl(s0)), C.usd(fl(db)), C.usd(fl(ds)),
                                     C.usd(fl(open1)), C.usd(fl(s1))), 'measured',
                         {'s': U(s0), 'a': U(db), 'b': U(ds), 'c': U(open1), 't': U(s1)}),
                    step('%s is not closed: every open order paid leaves %s; any released adds '
                         'back, up to %s.' % (C.fy(Y1), C.usd(fl(s1)), C.usd(fl(s1 + open1))),
                         'gap', {'y': F(Y1), 'a': U(s1), 'b': U(s1 + open1)},
                         closes='the Town’s journal report for %s, run after the year is closed'
                                % C.fy(Y1)),
                    step('Scope: department 300, as in the period-13 report. Department 301 '
                         '(curriculum adoption) ran %s over; with it, %s.'
                         % (C.usd(fl(-d['left301'])), C.usd(fl(with301))),
                         'measured', {'a': U(-d['left301']), 'b': U(with301)},
                         allow=('300', '301', '13'))]),
         con('Payroll rose %s, %s; vendor invoices %s, %s; journal entries %s.'
             % (C.usd(fl(dv('payroll'))), C.pct(pay_pct), C.usd(fl(dv('invoice'))),
                C.pct(inv_pct), C.usd(fl(dv('journal entry')))),
             ['pay', 'inv', 'je'],
             {'a': U(dv('payroll')), 'p': P(pay_pct), 'b': U(dv('invoice')), 'q': P(inv_pct),
              'c': U(dv('journal entry'))},
             notes=[step('Payroll lines are per account per pay run, never per person: dollars '
                         'here are not staff.', 'gap',
                         closes='the district’s position control list, with FTE and funding '
                                'source by year')]),
         con('Transfers and adjustments, beyond carried-forward encumbrances: %s in %s, %s in %s.'
             % (C.usd(fl(tr0)), C.fy(Y0), C.usd(fl(tr1)), C.fy(Y1)),
             ['tr0', 'tr1', 'adj'],
             {'a': U(tr0), 'y': F(Y0), 'b': U(tr1), 'z': F(Y1)},
             notes=[step('%s of %s’s is one line on collaborative tuitions, 1 July 2024 (ADJ '
                         'FY25 BUDGET). The district’s budget book prints that figure there as '
                         'the circuit breaker offset.' % (C.usd(fl(-d['adj'])), C.fy(Y0)),
                         'measured', {'a': U(-d['adj']), 'y': F(Y0)},
                         allow=('1 July 2024', 'FY25'),
                         cite=(BOOK, 'LPS budget book, 12 March 2025, 9400 Collaborative Tuitions')),
                    step('The journal entry itself does not name the circuit breaker.', 'gap',
                         closes='the backup for journal 2025/01/000564',
                         allow=('2025/01/000564',))]),
         con('Encumbrances carried out of each closed year: %s. %s has %s open.'
             % (yrs_closed, C.fy(Y1), C.usd(fl(open1))),
             ['open'],
             dict({'y': F(Y1), 'o': U(open1)},
                  **{'c%d' % i: U(v) for i, v in enumerate(closed)}),
             notes=[step('Each closed year’s encumbrances came back the next July as budget, '
                         'to the cent; the %s close decides how much of the %s does.'
                         % (C.fy(Y1), C.usd(fl(open1))), 'measured',
                         {'y': F(Y1), 'o': U(open1)})])],
        chart=TP.bridge(
            'From one year’s surplus to the next',
            ('Left unspent, %s' % C.fy(Y0), fl(s0)),
            [('Original appropriation', fl(dv('original_budget'))),
             ('Encumbrances carried forward', fl(dv('carry_forward'))),
             ('Other transfers and adjustments', fl(dv('transfer'))),
             ('Payroll', -fl(dv('payroll'))),
             ('Vendor invoices', -fl(dv('invoice'))),
             ('Journal entries', -fl(dv('journal entry'))),
             ('Cash receipts credited', -fl(dv('receipt'))),
             ('Open encumbrances', -fl(open1))],
            ('Left unspent, %s' % C.fy(Y1), fl(s1)), '$',
            note='Each step is the change from %s to %s and its effect on what was left. '
                 'School general fund, department 300.' % (C.fy(Y0), C.fy(Y1)),
            note_figures={'y': F(Y0), 'z': F(Y1), 'd': N(int(J.SURPLUS_DEPT), 'department')}),
        table=dict(caption='The surplus, %s to %s' % (C.fy(Y0), C.fy(Y1)), views=[
            dict(key='categories', label='By category', total_col=None, kinds=['ledger'] * 7,
                 columns=['Left, %s' % C.fy(Y0), 'Budget', 'Payroll', 'Vendor invoices',
                          'Journal entries', 'Encumbered', 'Left, %s' % C.fy(Y1)],
                 rows=cat_rows,
                 note='Each middle column is that piece’s effect on what was left; negative is '
                      'spending that rose or budget that fell. Journal entries move spending '
                      'between lines after it is paid, so a row’s payroll and journal entries '
                      'can run opposite ways.'),
            dict(key='pieces', label='Every year', total_col=None,
                 kinds=['ledger'] * len(J.YEARS), columns=[C.fy(y) for y in J.YEARS],
                 rows=piece_rows,
                 note='Budget, less every way money left, less what was still on order. %s is '
                      'not yet closed.' % C.fy(J.OPEN_FY))]),
        sources=sources(),
        finding_figures={'y': F(Y1), 'a': U(s1), 'b': U(s1 + open1), 'o': U(open1)})
    out['surplus-bridge']['not_established'] = [
        'Why any line came in under or over: the journal records postings, not reasons.',
        'How much of the FY2026 orders still open will be paid, carried or cancelled.',
        'Whether any cost moved to a grant or revolving fund; the next topics follow that.',
        'Whether the FY2025 reduction on collaborative tuitions is the circuit breaker offset '
        'the budget book prints: the amount and account match; the entry does not say.',
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
             notes=[step('They are %s.' % listing, 'measured')]),
         con('The %s under both years left %s in %s, %s of its surplus; in %s, %s, more than all of it.'
             % (C.num(len(both)), C.usd(fl(b0)), C.fy(Y0), C.pct(sh0, 0), C.fy(Y1), C.usd(fl(b1))),
             ['n', 'b0', 'b1', 's0', 's1'],
             {'n': N(len(both), 'categories'), 'a': U(b0), 'y': F(Y0), 'p': P(sh0, 0), 'b': U(b1), 'z': F(Y1)},
             notes=[step('The surplus was %s, then %s. In %s every category came in under; '
                         'in %s, the categories that ran over used the difference.'
                         % (C.usd(fl(s0)), C.usd(fl(s1)), C.fy(Y0), C.fy(Y1)), 'measured',
                         {'a': U(s0), 'b': U(s1), 'y': F(Y0), 'z': F(Y1)})]),
         con('%s left the most of them over the two years: %s, then %s.'
             % (S.CAT_LABEL[lead], C.usd(fl(cl[(Y0, lead)])), C.usd(fl(cl[(Y1, lead)]))),
             ['l0', 'l1'],
             {'a': U(cl[(Y0, lead)]), 'b': U(cl[(Y1, lead)])}),
         con('Line by line, %s of %s accounts left money in both years; in %s they left %s.'
             % (C.num(len(a_both)), C.num(len(accts)), C.fy(Y1), C.usd(fl(ab1))),
             ['an', 'ab1', 'why'],
             {'n': N(len(a_both), 'accounts'), 'm': N(len(accts), 'accounts'), 'y': F(Y1),
              'a': U(ab1)},
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
        said=[dict(quote=TM_QUOTE, board='Select Board', date='2025-09-09', href=TM_MINUTES,
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
    if sorted(out) != MINE:
        fail('the pages built are not the pages the registry gives this script: %s vs %s'
             % (sorted(out), MINE))
    return out, d


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
             notes=[step('June carries the year-end journal entries, which move spending '
                         'between lines and months.', 'measured')]),
         con('June ended with %s unspent in %s, against %s in %s.'
             % (pc(L[(Y1, JUNE)]), C.fy(Y1), pc(L[(2023, JUNE)]), C.fy(2023)),
             ['j23', 'j26'],
             {'a': P(L[(Y1, JUNE)]), 'y': F(Y1), 'b': P(L[(2023, JUNE)]), 'z': F(2023)},
             notes=[step('Spending only: %s’s open purchase orders are not counted until paid.'
                         % C.fy(Y1), 'measured', {'y': F(Y1)})]),
         con('%s had %s left in March against a usual %s, and still %s in June.'
             % (S.CAT_LABEL[lead], pc(Lc[(Y1, lead, MARCH)]), pc(lg[1]), pc(Lc[(Y1, lead, JUNE)])),
             ['lead', 'leadu', 'leadj'],
             {'a': P(Lc[(Y1, lead, MARCH)]), 'b': P(lg[1]), 'c': P(Lc[(Y1, lead, JUNE)])},
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
             ['so0', 'so1'], {'a': U(so[Y1]), 'b': U(so[Y0]), 'y': F(Y0)}),
         con('Tuition spent %s of its %s budget by December; %s in %s.'
             % (C.pct(t_dec[Y1], 0), C.fy(Y1), C.pct(t_dec[Y0], 0), C.fy(Y0)),
             ['t0', 't1'],
             {'a': P(t_dec[Y1], 0), 'y': F(Y1), 'b': P(t_dec[Y0], 0), 'z': F(Y0)}),
         con('Contracted services still had %s of the budget left in December and ended June %s over.'
             % (C.pct(con_dec, 0), C.pct(-con_jun, 0)),
             ['cd', 'cj'], {'a': P(con_dec, 0), 'b': P(-con_jun, 0)},
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
                 'budget not yet spent. Psychologists are outside it.',
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
