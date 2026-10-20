#!/usr/bin/env python3
"""Buildings and grounds: what building upkeep buys, and its budget against its spending. The
hub and two topic pages, from the school MUNIS journal.

    python3 scripts/build_buildings_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_buildings_topics.py --check   # fail if any output would change

    buildings-and-grounds       /buildings-and-grounds                            the hub
    upkeep-spending             /buildings-and-grounds/upkeep-spending            What upkeep buys
    upkeep-budget-vs-spending   /buildings-and-grounds/upkeep-budget-vs-spending  Upkeep budget and spending

THE LINE. "Building & grounds upkeep", the surplus pages' category: every non-salary account in
DESE functions 4000-4999 of general fund department 300 except utilities, by
build_school_surplus.category_of -- so the figures here are the figures on the surplus pages.

WHAT IT BUYS is grouped by TYPE OF WORK, and that grouping is OURS: each payee is assigned in
`sources/data/building-payee-trades.csv` by what its invoices say, one row each, with the
description it was assigned from. A payee not in that file is "Other repairs and supplies";
the generator says how much of each year that holds, so a growing "other" is visible.

RECURRING is MEASURED: a payee paid on the line in at least three of the four years. A payee
paid in one or two years is a project or a one-off, which is a reading of the pattern, and the
page says so.

THE BUDGET BOOK. `3-12-25-town-manager-39-s-budget.txt`, the district's FY2026 budget book of
12 March 2025, is read for each upkeep line it prints (BOOK_LINES): the FY2025 budget and the
FY2026 figure in its last column, parsed from the document on every build, never typed.

RULE 7. That the budget grew faster than spending is arithmetic. WHY spending did not rise to
meet it is not in a ledger: two explanations fit the same postings, and the page gives both.
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
import build_school_surplus as S  # noqa: E402

OUT_DIR = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics')
ME = os.path.basename(__file__)
HUB = 'buildings-and-grounds'
MINE = sorted(t for t, (_, _, gen) in REG.TOPICS.items() if gen == ME)
CAT = 'buildings'
TRADES_CSV = os.path.join(ROOT, 'sources', 'data', 'building-payee-trades.csv')
OTHER = 'Other repairs and supplies'
Y0, Y1, F0 = 2025, 2026, J.YEARS[0]
D0 = Decimal(0)
BOOK = '/docs/district-budget/docs/3-12-25-town-manager-39-s-budget.pdf'
BOOK_TEXT = os.path.join(ROOT, 'sources', 'district-budget', 'text',
                         '3-12-25-town-manager-39-s-budget.txt')
# The book's label for each upkeep line, and the MUNIS account the line is budgeted on.
BOOK_LINES = [
    ('Maint. of Buildings/Contracted Services', '0100-3-300-4220-01-1-74-2-535006'),
    ('Maint. of Bldg Supplies/System', '0100-3-300-4220-99-1-74-2-541002'),
    ('Emergency Expenditures', '0100-3-300-4220-99-1-74-2-545004'),
    ('Networking Contracted Service', '0100-3-300-4400-99-1-52-2-535006'),
    ('Maint. of Grounds/Contrctd Serv', '0100-3-300-4210-01-1-74-2-535006'),
    ('Maint of Grounds Supplies/System', '0100-3-300-4210-99-1-74-2-545003'),
]
GROUNDS = BOOK_LINES[4:]        # the pair the ledger holds the other way round (measured)
NUM = r'(-?[\d,]+)'
MARK = 10000                    # a cell is marked when it moved this much (TJ, 20 October 2026)
MARK_NOTE = ' ▲ ▼ mark a change of $10,000 or more.'
YEAR_PAIRS = [(i, i - 1) for i in range(1, len(J.YEARS))]


def fail(msg):
    raise SystemExit('build_buildings_topics: ' + msg)


def fl(x):
    return float(x)


def sources():
    return [
        dict(label='Lunenburg Budget Project — munis-school-journal.csv (every school journal '
                   'line, FY2023–FY2026, our redacted reading of the Town’s Report 1)',
             href=J.PUBLIC['journal']),
        dict(label='Lunenburg Public Schools — budget book, 12 March 2025 (4210 Maintenance of '
                   'Grounds, 4220 Maintenance of Buildings, 4400 Networking)', href=BOOK),
        dict(label='Lunenburg Budget Project — building-payee-trades.csv (our grouping of each '
                   'payee by type of work)', href='/docs/data/building-payee-trades.csv'),
    ]


def book():
    """{label: (FY2025 budgeted, FY2026 last column)}, read from the book's text."""
    text = open(BOOK_TEXT, encoding='utf-8').read()
    out = {}
    for label, _ in BOOK_LINES:
        m = re.search(re.escape(label) + r'\s+' + r'\s+'.join([NUM] * 5) + r'\s+-?[\d.]+%', text)
        if not m:
            fail('the book no longer prints %r with five figures' % label)
        n = [Decimal(g.replace(',', '')) for g in m.groups()]
        out[label] = (n[0], n[4])
    return out


def trades():
    t = {}
    for r in csv.DictReader(open(TRADES_CSV, encoding='utf-8', newline='')):
        if r['payee'] in t:
            fail('%s is in the trades file twice' % r['payee'])
        if not r['basis'].strip():
            fail('%s has no basis in the trades file' % r['payee'])
        t[r['payee']] = r['trade']
    return t


def data():
    A = J.accounts()
    cat = lambda r: S.category_of(dict(account=r['account'], obj=r['object']))
    L = [r for r in J.lines() if J.in_surplus_scope(A[r['account']]) and cat(r) == CAT]
    d = dict(A=A)
    acct = defaultdict(lambda: D0)       # (fy, account, piece)
    for r in L:
        piece = 'orig' if r['source'] == 'BUC' else {'transfer': 'trans', 'actual': 'spent',
                                                     'encumbrance': 'enc'}.get(r['posts_to'])
        acct[(r['fy'], r['account'], piece)] += r['amt']
    d['acct'] = acct
    d['accounts'] = sorted({a for (_, a, _) in acct})
    yr = lambda y, p: sum((v for (yy, _, pp), v in acct.items() if yy == y and pp == p), D0)
    d['orig'] = {y: yr(y, 'orig') for y in J.YEARS}
    d['trans'] = {y: yr(y, 'trans') for y in J.YEARS}
    d['spent'] = {y: yr(y, 'spent') for y in J.YEARS}
    d['enc'] = {y: yr(y, 'enc') for y in J.YEARS}
    d['left'] = {y: d['orig'][y] + d['trans'][y] - d['spent'][y] - d['enc'][y] for y in J.YEARS}
    d['acct_left'] = lambda y, a: (acct[(y, a, 'orig')] + acct[(y, a, 'trans')]
                                   - acct[(y, a, 'spent')] - acct[(y, a, 'enc')])
    # payees and type of work
    T = trades()
    pv = defaultdict(lambda: D0)
    for r in L:
        if r['posts_to'] != 'actual':
            continue
        p = J.payee(r)
        if p is J.MASKED:
            fail('a masked payee is on building upkeep; this page lists payees')
        pv[(p, r['fy'])] += r['amt']
    payees = sorted({p for (p, _) in pv if p})
    unmapped = [p for p in payees if p not in T]
    d['trade'] = defaultdict(lambda: D0)
    for (p, y), v in pv.items():
        d['trade'][(T.get(p, OTHER) if p else OTHER, y)] += v
    d['trades'] = sorted({t for (t, _) in d['trade']},
                         key=lambda t: (t == OTHER, -sum(fl(d['trade'][(t, y)]) for y in J.YEARS)))
    d['unmapped_share'] = {y: 100.0 * fl(sum(pv[(p, y)] for p in unmapped)) / fl(d['spent'][y])
                           for y in J.YEARS}
    yp = {p: sum(1 for y in J.YEARS if pv[(p, y)] > 0) for p in payees}
    d['recurring'] = {y: sum((pv[(p, y)] for p in payees if yp[p] >= 3), D0) for y in J.YEARS}
    d['oneoff'] = {y: sum((pv[(p, y)] for p in payees if yp[p] <= 2), D0) for y in J.YEARS}
    d['nopayee'] = {y: pv[(None, y)] for y in J.YEARS}
    oo = sorted((p for p in payees if yp[p] <= 2), key=lambda p: -fl(pv[(p, Y0)]))
    d['oneoff_top'] = [(p, pv[(p, Y0)]) for p in oo[:3]]
    d['payees'] = len(payees)
    # the same payees, paid from capital articles (every fund numbered 3xxx)
    ps = set(payees)
    cap = defaultdict(lambda: D0)
    for r in J.lines():
        if r['posts_to'] == 'actual' and r['fund'].startswith('3') and J.payee(r) in ps:
            cap[r['fy']] += r['amt']
    d['capital'] = {y: cap[y] for y in J.YEARS}
    d['book'] = book()
    return d


def build():
    d = data()
    U = lambda v: figure(fl(v), C.usd(fl(v)))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=0: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    f, con = LD.fact, TP.conclusion
    pct = lambda a, b: 100.0 * (fl(b) - fl(a)) / fl(a)
    out = {}
    o0, o1 = d['orig'][F0], d['orig'][Y1]
    s0, s1 = d['spent'][F0], d['spent'][Y1]
    po, ps = pct(o0, o1), pct(s0, s1)
    if not po > 2 * ps > 0:
        fail('the finding assumes the budget grew more than twice as fast as spending')

    # ================================================== upkeep-budget-vs-spending
    B = d['book']
    raised = [a for lab, a in BOOK_LINES if B[lab][1] > B[lab][0]]
    # The grounds pair: the book's two figures sit on the other account in the ledger.
    (gl0, ga0), (gl1, ga1) = GROUNDS
    orig = lambda a, y: d['acct'][(y, a, 'orig')]
    swapped = orig(ga0, Y1) == B[gl1][1] and orig(ga1, Y1) == B[gl0][1] and B[gl0][1] != B[gl1][1]
    if not swapped:
        fail('the grounds note assumes the ledger holds the book’s two grounds figures the other '
             'way round; it no longer does')
    for lab, a in BOOK_LINES[:4]:
        if orig(a, Y1) != B[lab][1]:
            fail('%s: the ledger’s FY%d budget %s is not the book’s %s' % (lab, Y1, orig(a, Y1), B[lab][1]))
    l_raised = sum((d['acct_left'](Y1, a) for a in raised), D0)
    share = 100.0 * fl(l_raised) / fl(d['left'][Y1])
    db, ds = o1 - d['orig'][Y0], d['spent'][Y1] - d['spent'][Y0]
    after_open = d['left'][Y1] - d['enc'][Y1]
    if not (db > 0 > ds and d['capital'][Y1] > d['capital'][Y0]):
        fail('the conclusions assume FY%d’s budget rose, spending fell and capital rose' % Y1)
    fx = {}
    fx['o0'] = f('o0', U(o0), 'original budget, %s' % C.fy(F0), 'published', {'y': F(F0)})
    fx['o1'] = f('o1', U(o1), 'original budget, %s' % C.fy(Y1), 'published', {'y': F(Y1)})
    fx['s0'] = f('s0', U(s0), 'spent, %s' % C.fy(F0), 'published', {'y': F(F0)})
    fx['s1'] = f('s1', U(s1), 'spent, %s, before the close' % C.fy(Y1), 'published', {'y': F(Y1)})
    fx['db'] = f('db', U(db), 'more budget in %s than %s' % (C.fy(Y1), C.fy(Y0)), 'published',
                 {'y': F(Y1), 'z': F(Y0)})
    fx['ds'] = f('ds', U(-ds), 'less spent in %s than %s' % (C.fy(Y1), C.fy(Y0)), 'published',
                 {'y': F(Y1), 'z': F(Y0)})
    fx['left'] = f('left', U(d['left'][Y1]), 'left unspent, %s' % C.fy(Y1), 'published', {'y': F(Y1)})
    fx['lr'] = f('lr', U(l_raised), 'of it on the lines the book raised', 'published')
    fx['enc'] = f('enc', U(d['enc'][Y1]), 'still on order, %s' % C.fy(Y1), 'published', {'y': F(Y1)})
    fx['c0'] = f('c0', U(d['capital'][Y0]), 'same payees, capital funds, %s' % C.fy(Y0),
                 'published', {'y': F(Y0)})
    fx['c1'] = f('c1', U(d['capital'][Y1]), 'same payees, capital funds, %s' % C.fy(Y1),
                 'published', {'y': F(Y1)})
    fx['why'] = f('why', None, 'the basis for each FY2026 increase', 'gap', allow=('FY2026',),
                  closes='the district’s line-by-line basis for the FY2026 maintenance budget, '
                         'and the facilities work-order history, FY2023–FY2026')
    book_rows = []
    for lab, a in BOOK_LINES:
        vals = [fl(B[lab][0]), fl(B[lab][1]), None, None, None, None]
        book_rows.append(dict(label=lab, marks=TP.change_marks(vals, [(1, 0)], MARK), cells=[
            C.usd(fl(B[lab][0])), C.usd(fl(B[lab][1])),
            C.pct(pct(B[lab][0], B[lab][1]), 0) if B[lab][0] else '',
            C.usd(fl(orig(a, Y1))), C.usd(fl(d['acct'][(Y1, a, 'spent')])),
            C.usd(fl(d['acct_left'](Y1, a)))]))
    acct_rows = []
    for a in sorted(d['accounts'], key=lambda a: -fl(d['acct_left'](Y1, a))):
        if all(abs(fl(d['acct'][(y, a, p)])) < 500 for y in J.YEARS for p in ('orig', 'spent')):
            continue
        vals = [fl(orig(a, y)) for y in (Y0, Y1)] + [fl(d['acct'][(y, a, 'spent')]) for y in (Y0, Y1)] + [None]
        acct_rows.append(dict(label='%s (%s)' % (d['A'][a]['account_description'].title(), a),
                              marks=TP.change_marks(vals, [(1, 0), (3, 2)], MARK),
                              cells=[C.usd(fl(orig(a, y))) for y in (Y0, Y1)]
                              + [C.usd(fl(d['acct'][(y, a, 'spent')])) for y in (Y0, Y1)]
                              + [C.usd(fl(d['acct_left'](Y1, a)))]))
    out['upkeep-budget-vs-spending'] = TP.page(
        'upkeep-budget-vs-spending',
        'Building upkeep’s budget rose %s from %s to %s; what it spent rose %s.'
        % (C.pct(po, 0), C.fy(F0), C.fy(Y1), C.pct(ps, 0)),
        list(fx.values()),
        [con('The original budget went from %s to %s; spending from %s to %s.'
             % (C.usd(fl(o0)), C.usd(fl(o1)), C.usd(fl(s0)), C.usd(fl(s1))),
             ['o0', 'o1', 's0', 's1'],
             {'a': U(o0), 'b': U(o1), 'c': U(s0), 'd': U(s1)},
             notes=[step('The district’s budget book prints the %s increases in its first %s '
                         'column, before the year began.' % (C.fy(Y1), C.fy(Y1)), 'measured',
                         {'y': F(Y1)}, cite=(BOOK, 'LPS budget book, 12 March 2025')),
                    step('Transfers during the year were small: %s in %s.'
                         % (C.usd(fl(d['trans'][Y1])), C.fy(Y1)), 'measured',
                         {'a': U(d['trans'][Y1]), 'y': F(Y1)})]),
         con('In %s the budget rose %s and spending fell %s.'
             % (C.fy(Y1), C.usd(fl(db)), C.usd(fl(-ds))),
             ['db', 'ds'], {'y': F(Y1), 'a': U(db), 'b': U(-ds)},
             notes=[step('%s’s spending included payees paid in one or two years only; the '
                         'largest, %s, was paid %s.' % (C.fy(Y0), d['oneoff_top'][0][0].title(),
                                                        C.usd(fl(d['oneoff_top'][0][1]))),
                         'measured', {'y': F(Y0), 'a': U(d['oneoff_top'][0][1])})]),
         con('%s of %s’s %s left sits on the lines the book raised for %s.'
             % (C.usd(fl(l_raised)), C.fy(Y1), C.usd(fl(d['left'][Y1])), C.fy(Y1)),
             ['left', 'lr', 'enc'],
             {'a': U(l_raised), 'y': F(Y1), 'b': U(d['left'][Y1])},
             notes=[step('That is %s. If every open order is paid, %s is still left.'
                         % (C.pct(share, 0), C.usd(fl(after_open))), 'measured',
                         {'p': P(share), 'a': U(after_open)}),
                    step('The ledger holds the book’s two grounds lines the other way round; '
                         'together they are the same.', 'measured')]),
         con('The same payees were paid %s from capital funds in %s, against %s in %s.'
             % (C.usd(fl(d['capital'][Y1])), C.fy(Y1), C.usd(fl(d['capital'][Y0])), C.fy(Y0)),
             ['c0', 'c1', 'why'],
             {'a': U(d['capital'][Y1]), 'y': F(Y1), 'b': U(d['capital'][Y0]), 'z': F(Y0)},
             notes=[step('Two readings fit: the increases were set higher than the work, or new '
                         'systems bought with capital needed fewer repairs.', 'hypothesis'),
                    step('The journal cannot tell them apart.', 'gap',
                         closes='the facilities work-order history, FY2023–FY2026',
                         allow=('FY2023', 'FY2026'))])],
        chart=TP.series('Upkeep budget and spending, by year', [C.fy(y) for y in J.YEARS], [
            TP.track('Spent', [fl(d['spent'][y]) for y in J.YEARS], 'published', 'bar'),
            TP.track('Original budget', [fl(d['orig'][y]) for y in J.YEARS], 'published', 'line')],
            '$',
            note='General fund department 300, non-salary accounts in DESE functions 4000–4999 '
                 'except utilities. %s is before its close.' % C.fy(Y1),
            note_figures={'y': F(Y1)}, note_allow=('300', '4000–4999')),
        table=dict(caption='Building upkeep, line by line', views=[
            dict(key='book', label='Budget book against ledger, %s' % C.fy(Y1), total_col=None,
                 kinds=['stated', 'stated', 'stated', 'ledger', 'ledger', 'ledger'],
                 columns=['Book, %s' % C.fy(Y0), 'Book, %s' % C.fy(Y1), 'Increase',
                          'Ledger budget', 'Spent', 'Left'],
                 rows=book_rows,
                 note='The book’s figures as printed; the ledger’s original budget on the account '
                      'each line is set on. The two grounds lines are held the other way round.'
                      + MARK_NOTE),
            dict(key='accounts', label='Every account', total_col=None, kinds=['ledger'] * 5,
                 columns=['Budget, %s' % C.fy(Y0), 'Budget, %s' % C.fy(Y1),
                          'Spent, %s' % C.fy(Y0), 'Spent, %s' % C.fy(Y1), 'Left, %s' % C.fy(Y1)],
                 rows=acct_rows,
                 note='Original budgets; left includes transfers and open orders. MUNIS account '
                      'numbers.' + MARK_NOTE)]),
        sources=sources(),
        finding_figures={'a': P(po), 'y': F(F0), 'z': F(Y1), 'b': P(ps)})
    out['upkeep-budget-vs-spending']['not_established'] = [
        'Why spending did not rise to meet the budget: set higher than the work, or fewer '
        'repairs after capital projects, fit the same postings.',
        'The basis the district used for each FY2026 increase.',
        'The FY2026 figures after the close.',
    ]

    # ================================================== upkeep-spending
    tr, TRS = d['trade'], d['trades']
    top = TRS[0]
    rec, one = d['recurring'], d['oneoff']
    rlo, rhi = min(rec.values()), max(rec.values())
    if d['unmapped_share'][Y1] > 10:
        fail('more than 10%% of FY%d is unmapped; add its payees to the trades file' % Y1)
    mover_up = max((t for t in TRS if t not in (OTHER, top)), key=lambda t: fl(tr[(t, Y1)] - tr[(t, Y0)]))
    mover_dn = min((t for t in TRS if t != OTHER), key=lambda t: fl(tr[(t, Y1)] - tr[(t, Y0)]))
    tx = {}
    tx['rlo'] = f('rlo', U(rlo), 'lowest year, recurring payees', 'published')
    tx['rhi'] = f('rhi', U(rhi), 'highest year, recurring payees', 'published')
    tx['one0'] = f('one0', U(one[Y0]), 'one- and two-year payees, %s' % C.fy(Y0), 'published',
                   {'y': F(Y0)})
    tx['one23'] = f('one23', U(one[F0]), 'one- and two-year payees, %s' % C.fy(F0), 'published',
                    {'y': F(F0)})
    tx['top0'] = f('top0', U(min(tr[(top, y)] for y in J.YEARS)), '%s, lowest year' % top.lower(),
                   'published')
    tx['top1'] = f('top1', U(max(tr[(top, y)] for y in J.YEARS)), '%s, highest year' % top.lower(),
                   'published')
    tx['up0'] = f('up0', U(tr[(mover_up, Y0)]), '%s, %s' % (mover_up.lower(), C.fy(Y0)),
                  'published', {'y': F(Y0)})
    tx['up1'] = f('up1', U(tr[(mover_up, Y1)]), '%s, %s' % (mover_up.lower(), C.fy(Y1)),
                  'published', {'y': F(Y1)})
    tx['dn0'] = f('dn0', U(tr[(mover_dn, Y0)]), '%s, %s' % (mover_dn.lower(), C.fy(Y0)),
                  'published', {'y': F(Y0)})
    tx['dn1'] = f('dn1', U(tr[(mover_dn, Y1)]), '%s, %s' % (mover_dn.lower(), C.fy(Y1)),
                  'published', {'y': F(Y1)})
    tx['pay'] = f('pay', N(d['payees'], 'payees'), 'paid on the line in four years', 'published')
    names = lambda ps: ', '.join(p.title() for p, _ in ps)
    row = lambda lab, vs: dict(label=lab, cells=[C.usd(v) for v in vs],
                               marks=TP.change_marks(vs, YEAR_PAIRS, MARK))
    trade_rows = [row(t, [fl(tr[(t, y)]) for y in J.YEARS]) for t in TRS]
    trade_rows.append(row('Every type of work', [fl(d['spent'][y]) for y in J.YEARS]))
    out['upkeep-spending'] = TP.page(
        'upkeep-spending',
        'Most of building upkeep is steady work: %s to %s a year to payees paid year after year.'
        % (C.usd(fl(rlo)), C.usd(fl(rhi))),
        list(tx.values()),
        [con('%s is the largest type of work, %s to %s a year.'
             % (top, C.usd(fl(min(tr[(top, y)] for y in J.YEARS))),
                C.usd(fl(max(tr[(top, y)] for y in J.YEARS)))),
             ['top0', 'top1'],
             {'a': U(min(tr[(top, y)] for y in J.YEARS)), 'b': U(max(tr[(top, y)] for y in J.YEARS))},
             notes=[step('Grouped by us, by what each payee’s invoices say; the grouping is a '
                         'published file anyone can check.', 'measured')]),
         con('Payees paid in only one or two years took %s in %s, against %s in %s.'
             % (C.usd(fl(one[Y0])), C.fy(Y0), C.usd(fl(one[F0])), C.fy(F0)),
             ['one0', 'one23', 'rlo', 'rhi'],
             {'a': U(one[Y0]), 'y': F(Y0), 'b': U(one[F0]), 'z': F(F0)},
             notes=[step('The largest in %s: %s.' % (C.fy(Y0), names(d['oneoff_top'])),
                         'measured', {'y': F(Y0)}),
                    step('Paid in one or two years reads as a project; the journal does not label '
                         'it one.', 'hypothesis')]),
         con('%s rose from %s to %s in %s.'
             % (mover_up, C.usd(fl(tr[(mover_up, Y0)])), C.usd(fl(tr[(mover_up, Y1)])), C.fy(Y1)),
             ['up0', 'up1'],
             {'a': U(tr[(mover_up, Y0)]), 'b': U(tr[(mover_up, Y1)]), 'y': F(Y1)}),
         con('%s fell from %s to %s in %s.'
             % (mover_dn, C.usd(fl(tr[(mover_dn, Y0)])), C.usd(fl(tr[(mover_dn, Y1)])), C.fy(Y1)),
             ['dn0', 'dn1'],
             {'a': U(tr[(mover_dn, Y0)]), 'b': U(tr[(mover_dn, Y1)]), 'y': F(Y1)})],
        chart=TP.series('What building upkeep paid for, by year', [C.fy(y) for y in J.YEARS], [
            TP.track(t, [fl(tr[(t, y)]) for y in J.YEARS], 'published', 'bar', colour=i % 5)
            for i, t in enumerate(TRS)], '$', kind='bar', multiples=True,
            note='Each panel is one type of work, on one scale. Grouped by us from each payee’s '
                 'invoices. %s is before its close.' % C.fy(Y1),
            note_figures={'y': F(Y1)}),
        also=[TP.series('Recurring and one-time payees', [C.fy(y) for y in J.YEARS], [
            TP.track('Paid three or four years', [fl(rec[y]) for y in J.YEARS], 'published', 'bar'),
            TP.track('Paid one or two years', [fl(one[y]) for y in J.YEARS], 'published', 'bar')],
            '$', kind='bar', stacked=True,
            note='A payee is recurring if paid on the line in at least three of the four years.')],
        table=dict(caption='Building upkeep by type of work', views=[dict(
            key='trades', label='By year', total_col=None, kinds=['ledger'] * len(J.YEARS),
            columns=[C.fy(y) for y in J.YEARS], rows=trade_rows,
            note='Invoices paid, plus journal entries and refunds under other. Our grouping: '
                 'building-payee-trades.csv.' + MARK_NOTE)]),
        sources=sources(),
        finding_figures={'a': U(rlo), 'b': U(rhi)})
    out['upkeep-spending']['not_established'] = [
        'Which building, or which job, each payment was for: invoices describe the work in '
        'twenty characters or fewer.',
        'Whether a payee paid in one or two years was a project, a replacement or a one-off repair.',
    ]

    # ================================================== contracted-building-services
    out['contracted-building-services'] = contracted_page(d, U, F, P, N)
    out['upkeep-surplus-every-dollar'] = every_dollar_page(d, U, F, P, N)
    out['upkeep-skipped'] = skipped_page(d, U, F, P, N)

    # ================================================== the hub
    h = dict(
        o0=f('h-o0', U(o0), 'original budget, %s' % C.fy(F0), 'published', {'y': F(F0)}),
        o1=f('h-o1', U(o1), 'original budget, %s' % C.fy(Y1), 'published', {'y': F(Y1)}),
        s0=f('h-s0', U(s0), 'spent, %s' % C.fy(F0), 'published', {'y': F(F0)}),
        s1=f('h-s1', U(s1), 'spent, %s' % C.fy(Y1), 'published', {'y': F(Y1)}),
        left=f('h-left', U(d['left'][Y1]), 'left unspent, %s' % C.fy(Y1), 'published', {'y': F(Y1)}),
        rlo=f('h-rlo', U(rlo), 'recurring work, lowest year', 'published'),
        rhi=f('h-rhi', U(rhi), 'recurring work, highest year', 'published'),
        one=f('h-one', U(one[Y0]), 'one- and two-year payees, %s' % C.fy(Y0), 'published',
              {'y': F(Y0)}),
        cap=f('h-cap', U(d['capital'][Y1]), 'same payees, capital funds, %s' % C.fy(Y1),
              'published', {'y': F(Y1)}),
    )
    hub_ladder = LD.ladder([
        LD.tier('What it buys', [h['rlo'], h['rhi'], h['one']]),
        LD.tier('Budget and spending', [h['o0'], h['o1'], h['s0'], h['s1'], h['left'], h['cap']]),
    ], [
        LD.conclusion('The budget went from %s to %s in four years; spending from %s to %s.'
                      % (C.usd(fl(o0)), C.usd(fl(o1)), C.usd(fl(s0)), C.usd(fl(s1))),
                      ['h-o0', 'h-o1', 'h-s0', 'h-s1'],
                      {'a': U(o0), 'b': U(o1), 'c': U(s0), 'd': U(s1)}),
        LD.conclusion('Recurring work costs %s to %s a year; projects come and go on top.'
                      % (C.usd(fl(rlo)), C.usd(fl(rhi))), ['h-rlo', 'h-rhi', 'h-one'],
                      {'a': U(rlo), 'b': U(rhi)}),
        LD.conclusion('In %s the same payees were paid %s more from capital funds.'
                      % (C.fy(Y1), C.usd(fl(d['capital'][Y1] - d['capital'][Y0]))), ['h-cap'],
                      {'y': F(Y1), 'a': U(d['capital'][Y1] - d['capital'][Y0])}),
    ])
    out[HUB] = TP.hub(
        HUB,
        'Building upkeep’s budget nearly doubled in four years, %s to %s, while spending grew '
        'about a third. These pages show what it buys, and where the difference sits.'
        % (C.usd(fl(o0)), C.usd(fl(o1))),
        hub_ladder,
        chart=out['upkeep-budget-vs-spending']['chart'],
        answer_figures={'a': U(o0), 'b': U(o1)})

    if sorted(k for k in out if k != HUB) != MINE:
        fail('the pages built are not the pages the registry gives this script: %s vs %s'
             % (sorted(out), MINE))
    return out


# ONE ACCOUNT, all four years: third-party building services (TJ, 20 October 2026: "having $75k
# unspent from there is interesting").
SERVICES = '0100-3-300-4220-01-1-74-2-535006'
RESERVE_MEMO = 'RSF TRANSFER APPROVED 2/13/25'
FINCOM = '/docs/minutes/text/finance-committee/2025-02-13-minutes-6995.txt'
FINCOM_QUOTE = ('The entire building needs to be re-cabled to have a drop line in every single '
                'classroom for the connection. The additional cost of $60,000 was not in the '
                'original budget.')
# The Finance Committee asked the district who holds these contracts and when they end
# (questions of 26 February 2026); the district's written answer names five contractors.
QA = ('/docs/budget-workbooks/finance-committee/fy27-budget/department-presentations/'
      'school-department/fy2027-school-department-q-and-a.docx')
QA_TEXT = os.path.join(ROOT, 'sources', 'budget-workbooks', 'finance-committee', 'fy27-budget',
                       'department-presentations', 'school-department', 'text',
                       'fy2027-school-department-q-and-a.docx.txt')
QA_ANSWER = ('Maint. of Buildings/Contracted Services $269,510.00 Who is contracted. Provide '
             'contract end date. DI-Rock Electric Rockwell Roofing Renaud HVAC and Controls '
             'Johnson Controls Daikin Applied Americas Maint. of Bldg Supplies/System')
FINCOM_VOTE = ('There was a motion to transfer $58,320 from the reserve fund to the school '
               'department contracted services')


def contracted_page(d, U, F, P, N):
    src = os.path.join(ROOT, 'sources', 'meetings', 'text',
                       FINCOM.split('/docs/minutes/text/')[1])
    text = ' '.join(open(src, encoding='utf-8').read().split())
    for q in (FINCOM_QUOTE, FINCOM_VOTE):
        if q not in text:
            fail('the Finance Committee quotation is no longer verbatim in %s' % FINCOM)
    if QA_ANSWER not in ' '.join(open(QA_TEXT, encoding='utf-8').read().split()):
        fail('the district’s contractor answer is no longer verbatim in %s' % QA_TEXT)
    f, con = LD.fact, TP.conclusion
    a = SERVICES
    L = [r for r in J.lines() if r['account'] == a]
    # PURCHASE ORDERS: each commits money to a named vendor for a stated job. A release (POM)
    # in FY2026 is an order closed or cut without being paid; a carried-in order (SOY) came
    # from FY2025 and was budgeted again by the carry-forward.
    po = {}
    for r in L:
        if r['source'] == 'POE' and r['doc_no'] not in po:
            po[r['doc_no']] = dict(date=r['effective_date'], vendor=r['vendor'],
                                   job=r['description'].strip())
    pom, soy, poe26 = defaultdict(lambda: D0), defaultdict(lambda: D0), defaultdict(lambda: D0)
    for r in L:
        if r['fy'] != Y1:
            continue
        if r['source'] == 'POM':
            pom[r['doc_no']] += r['amt']
        elif r['source'] == 'SOY':
            soy[r['doc_no']] += r['amt']
        elif r['source'] == 'POE':
            poe26[r['doc_no']] += r['amt']
    released = {k: -v for k, v in pom.items() if v < 0}
    if any(k not in po for k in released):
        fail('a released order has no opening line in the journal')
    rel = sum(released.values(), D0)
    rel_c = sum((v for k, v in released.items() if soy[k] > 0), D0)
    carried = sorted((k for k in released if soy[k] > 0), key=lambda k: -fl(released[k]))
    if not rel_c > 0:
        fail('the orders conclusion assumes carried-in orders were released')
    g = lambda y, p: d['acct'][(y, a, p)]
    rf = [r['amt'] for r in L if r['source'] == 'BUA' and r['description'] == RESERVE_MEMO]
    if len(rf) != 1 or rf[0] <= 0:
        fail('expected one Reserve Fund transfer to contracted building services')
    rf = rf[0]
    pv, cum = defaultdict(lambda: D0), defaultdict(lambda: D0)
    for r in L:
        if r['posts_to'] == 'actual':
            pv[(J.payee(r), r['fy'])] += r['amt']
            cum[(r['fy'], int(r['period']))] += r['amt']
    payees = sorted({p for (p, _) in pv if p})
    yp = {p: sum(1 for y in J.YEARS if pv[(p, y)] > 0) for p in payees}
    rec = {y: sum((pv[(p, y)] for p in payees if yp[p] >= 3), D0) for y in J.YEARS}
    over = [y for y in (2024, Y0) if g(y, 'spent') > g(y, 'orig')]
    if over != [2024, Y0]:
        fail('the first conclusion assumes FY2024 and FY2025 spent past the original budget')
    net25 = g(Y0, 'spent') - rf
    above = g(Y1, 'orig') - net25
    left = d['acct_left'](Y1, a)
    if not (above > 0 and rec[Y1] < rec[Y0] and left > 0):
        fail('the FY%d conclusions no longer match the account' % Y1)
    run = lambda y, p: sum((cum[(y, q)] for q in range(1, p + 1)), D0)
    spring = {y: run(y, 12) - run(y, 9) for y in (Y0, Y1)}
    stopped = sorted((p for p in payees if yp[p] >= 3 and pv[(p, Y0)] > 0 and pv[(p, Y1)] <= 0),
                     key=lambda p: -fl(pv[(p, Y0)]))
    fx = dict(
        o24=f('o24', U(g(2024, 'orig')), 'original budget, %s' % C.fy(2024), 'published', {'y': F(2024)}),
        s24=f('s24', U(g(2024, 'spent')), 'spent, %s' % C.fy(2024), 'published', {'y': F(2024)}),
        o25=f('o25', U(g(Y0, 'orig')), 'original budget, %s' % C.fy(Y0), 'published', {'y': F(Y0)}),
        s25=f('s25', U(g(Y0, 'spent')), 'spent, %s' % C.fy(Y0), 'published', {'y': F(Y0)}),
        rf=f('rf', U(rf), 'Reserve Fund transfer, 13 February 2025', 'published',
             allow=('13 February 2025',)),
        rel=f('rel', U(rel), 'ordered, then released unpaid, %s' % C.fy(Y1), 'published', {'y': F(Y1)}),
        o26=f('o26', U(g(Y1, 'orig')), 'original budget, %s' % C.fy(Y1), 'published', {'y': F(Y1)}),
        s26=f('s26', U(g(Y1, 'spent')), 'spent, %s, before the close' % C.fy(Y1), 'published',
              {'y': F(Y1)}),
        left=f('left', U(left), 'left unspent, %s' % C.fy(Y1), 'published', {'y': F(Y1)}),
        r25=f('r25', U(rec[Y0]), 'recurring service payees, %s' % C.fy(Y0), 'published', {'y': F(Y0)}),
        r26=f('r26', U(rec[Y1]), 'recurring service payees, %s' % C.fy(Y1), 'published', {'y': F(Y1)}),
        relc=f('relc', U(rel_c), 'of it, orders carried in from %s' % C.fy(Y0), 'published',
               {'y': F(Y0)}),
    )
    payee_rows = [dict(label=p.title(), cells=[C.usd(fl(pv[(p, y)])) for y in J.YEARS]
                       + ['yes' if yp[p] >= 3 else 'no'],
                       marks=TP.change_marks([fl(pv[(p, y)]) for y in J.YEARS] + [None],
                                             YEAR_PAIRS, MARK))
                  for p in sorted(payees, key=lambda p: -sum(fl(pv[(p, y)]) for y in J.YEARS))[:25]]
    page = TP.page(
        'contracted-building-services',
        'Third-party building services left %s in %s, after two years of spending past the budget.'
        % (C.usd(fl(left)), C.fy(Y1)),
        list(fx.values()),
        [con('It spent past its original budget two years running: %s against %s, %s against %s.'
             % (C.usd(fl(g(2024, 'spent'))), C.usd(fl(g(2024, 'orig'))),
                C.usd(fl(g(Y0, 'spent'))), C.usd(fl(g(Y0, 'orig')))),
             ['o24', 's24', 'o25', 's25'],
             {'a': U(g(2024, 'spent')), 'b': U(g(2024, 'orig')),
              'c': U(g(Y0, 'spent')), 'e': U(g(Y0, 'orig'))}),
         con('%s’s largest item, %s of emergency cabling, was paid by a Reserve Fund transfer.'
             % (C.fy(Y0), C.usd(fl(rf))), ['rf'], {'y': F(Y0), 'a': U(rf)},
             notes=[step('The Finance Committee voted it 4–0 on 13 February 2025, for 911 and PA '
                         'compliance.', 'measured', allow=('4–0', '13 February 2025', '911'),
                         cite=(FINCOM, 'Finance Committee minutes, 13 February 2025')),
                    step('%s’s budget was then %s, %s above %s’s spending without the cabling. '
                         'No document we hold states the basis.'
                         % (C.fy(Y1), C.usd(fl(g(Y1, 'orig'))), C.usd(fl(above)), C.fy(Y0)),
                         'gap', {'y': F(Y1), 'a': U(g(Y1, 'orig')), 'b': U(above), 'z': F(Y0)},
                         closes='the district’s basis for the FY2026 Maintenance of Buildings '
                                'contracted services line', allow=('FY2026',))]),
         con('In %s, %s ordered from named vendors was released unpaid; %s had been carried in.'
             % (C.fy(Y1), C.usd(fl(rel)), C.usd(fl(rel_c))),
             ['rel', 'relc', 'o26'],
             {'y': F(Y1), 'a': U(rel), 'b': U(rel_c)},
             notes=[step('Among them: %s. The table lists every order.'
                         % '; '.join('%s, “%s”, %s' % (po[k]['vendor'].title(), po[k]['job'].title(),
                                                        C.usd(fl(released[k]))) for k in carried[:2]),
                         'measured', {'k%d' % i: U(released[k]) for i, k in enumerate(carried[:2])},
                         allow=tuple(po[k]['job'].title() for k in carried[:2])),
                    step('Released is not the same as not done: another order, a warranty or a '
                         'dropped job all close an order this way.', 'hypothesis'),
                    step('Asked for each contract and its end date, the district named five '
                         'contractors and gave no dates.', 'gap', cite=(QA, 'LPS answers to the Finance Committee, FY2027'),
                         closes='the facilities work orders for FY2026, and each service contract '
                                'with its scope and term', allow=('FY2026',))]),
         con('%s spent %s; recurring service payees fell from %s to %s.'
             % (C.fy(Y1), C.usd(fl(g(Y1, 'spent'))), C.usd(fl(rec[Y0])), C.usd(fl(rec[Y1]))),
             ['s26', 'left', 'r25', 'r26'],
             {'y': F(Y1), 'a': U(g(Y1, 'spent')), 'b': U(rec[Y0]), 'c': U(rec[Y1])},
             notes=[step('Paid every year before and nothing in %s: %s. April to June spent %s, '
                         'against %s.' % (C.fy(Y1), ', '.join(p.title() for p in stopped[:3]),
                                          C.usd(fl(spring[Y1])), C.usd(fl(spring[Y0]))),
                         'measured', {'y': F(Y1), 'a': U(spring[Y1]), 'b': U(spring[Y0])}),
                    step('Fewer door and security calls after the capital work at Turkey Hill '
                         'fits the timing; nothing in the journal says so.', 'hypothesis')])],
        chart=TP.series('Contracted building services, by year', [C.fy(y) for y in J.YEARS], [
            TP.track('Spent', [fl(g(y, 'spent')) for y in J.YEARS], 'published', 'bar'),
            TP.track('Original budget', [fl(g(y, 'orig')) for y in J.YEARS], 'published', 'line')],
            '$', note='%s’s spending includes %s of cabling paid by a Reserve Fund transfer. '
                      'Account %s.' % (C.fy(Y0), C.usd(fl(rf)), a),
            note_figures={'y': F(Y0), 'a': U(rf)}, note_allow=(a,)),
        also=[TP.series('Spent through the year', X_MONTHS, [
            TP.track(C.fy(y), [fl(run(y, p)) for p in range(0, 13)], 'published', 'line')
            for y in (2024, Y0, Y1)], '$',
            note='Cumulative payments, July to June.')],
        said=[dict(quote=FINCOM_QUOTE, board='Finance Committee', date='2025-02-13', href=FINCOM,
                   label='Finance Committee minutes, 13 February 2025')],
        table=dict(caption='Who was paid from contracted building services', views=[dict(
            key='released', label='Orders closed unpaid, %s' % C.fy(Y1), total_col=None,
            kinds=['ledger'] * 5,
            columns=['Ordered', 'Vendor', 'The job, as the order states it', 'Carried in',
                     'Released'],
            rows=[dict(label=k, cells=[po[k]['date'], po[k]['vendor'].title(), po[k]['job'],
                                        'yes' if soy[k] > 0 else 'no', C.usd(fl(released[k]))])
                  for k in sorted(released, key=lambda k: -fl(released[k]))],
            note='Purchase order numbers as MUNIS records them. Released: closed or reduced in '
                 '%s without payment; %s in all.' % (C.fy(Y1), C.usd(fl(rel)))), dict(
            key='payees', label='Payees, by year', total_col=None, kinds=['ledger'] * 5,
            columns=[C.fy(y) for y in J.YEARS] + ['Recurring'], rows=payee_rows,
            note='Names as MUNIS prints them, cut at twenty characters. Recurring: paid in at '
                 'least three of the four years. Johnson Controls and '
                 'Johnson Controls US are separate vendor records in MUNIS; we do not merge them.'
                 + MARK_NOTE)]),
        sources=sources() + [dict(label='Town of Lunenburg — Finance Committee minutes, 13 February '
                                        '2025 (2025-02-13-minutes-6995)', href=FINCOM),
                             dict(label='Lunenburg Public Schools — FY2027 School Department Q&A, '
                                        'answers to the Finance Committee', href=QA)],
        finding_figures={'a': U(left), 'y': F(Y1)})
    page['not_established'] = [
        'The basis the district used to set the FY2026 figure at its level.',
        'Whether the jobs on released orders were done some other way, or not done.',
        'Why recurring service payees were paid less in FY2026.',
        'Whether a new payee did work an old one used to do.',
    ]
    return page


# EVERY DOLLAR OF ONE YEAR'S LEFTOVER (TJ, 20 October 2026: "take the buildings and grounds
# surplus, and put it on one page where every dollar came from"). Where it came from (the
# original appropriation, the encumbrances carried in, every transfer with its memo), where it
# went (every payee), what is still committed, and what is left -- and every table foots to the
# leftover to the cent, or the page is refused.
PAYEE_VIEW = 30                 # rows per payee view: every payee is listed, across views
SLICES = 7                      # accounts drawn as their own slice of the leftover; the rest as one
LABEL_OF = {                    # plain names for the slices; the table keeps MUNIS's, with numbers
    '0100-3-300-4220-01-1-74-2-535006': 'Contracted building services',
    '0100-3-300-4220-99-1-74-2-545004': 'Emergency expenditures',
    '0100-3-300-4220-99-1-74-2-541002': 'Building maintenance supplies',
    '0100-3-300-4230-99-1-74-2-525009': 'Fire safety and furniture repair',
    '0100-3-300-4400-99-1-52-2-535006': 'Networking services',
    '0100-3-300-4110-99-1-74-2-541001': 'Custodial supplies',
    '0100-3-300-4210-99-1-74-2-545003': 'Grounds supplies',
}


def every_dollar_page(d, U, F, P, N):
    f, con = LD.fact, TP.conclusion
    A = d['A']
    cat = lambda r: S.category_of(dict(account=r['account'], obj=r['object']))
    L = [r for r in J.lines() if r['fy'] == Y1 and J.in_surplus_scope(A[r['account']])
         and cat(r) == CAT]
    T = trades()
    pieces = defaultdict(lambda: D0)        # (account, piece)
    pay, pay_acct, trade = defaultdict(lambda: D0), defaultdict(set), defaultdict(lambda: D0)
    moves = []
    for r in L:
        a = r['account']
        if r['source'] == 'BUC':
            pieces[(a, 'orig')] += r['amt']
        elif r['posts_to'] == 'transfer':
            pieces[(a, 'carry' if J.is_carry_forward(r) else 'trans')] += r['amt']
            if not J.is_carry_forward(r):
                moves.append(r)
        elif r['posts_to'] == 'actual':
            pieces[(a, 'paid')] += r['amt']
            p = J.payee(r)
            if p is J.MASKED:
                fail('a masked payee is on building upkeep')
            key = p or 'Journal entries and refunds'
            pay[key] += r['amt']
            pay_acct[key].add(A[a]['account_description'].title())
            trade[T.get(p, OTHER) if p else OTHER] += r['amt']
        else:
            pieces[(a, 'open')] += r['amt']
    tot = lambda k: sum((v for (_, kk), v in pieces.items() if kk == k), D0)
    orig, carry, trans, paid, open_ = (tot(k) for k in ('orig', 'carry', 'trans', 'paid', 'open'))
    left = orig + carry + trans - paid - open_
    if left != d['left'][Y1]:
        fail('every dollar does not foot: %s against the page’s %s' % (left, d['left'][Y1]))
    if sum(pay.values(), D0) != paid or sum(trade.values(), D0) != paid:
        fail('the payees or the types of work do not foot to what was paid')
    accts = sorted({a for (a, _) in pieces}, key=lambda a: -fl(
        pieces[(a, 'orig')] + pieces[(a, 'carry')] + pieces[(a, 'trans')] - pieces[(a, 'paid')]
        - pieces[(a, 'open')]))
    al = {a: pieces[(a, 'orig')] + pieces[(a, 'carry')] + pieces[(a, 'trans')]
          - pieces[(a, 'paid')] - pieces[(a, 'open')] for a in accts}
    under = sum((v for v in al.values() if v > 0), D0)
    over = sum((v for v in al.values() if v < 0), D0)
    # Against FY2025, account by account: budget (original plus transfers) and spending.
    bud = lambda a, y: d['acct'][(y, a, 'orig')] + d['acct'][(y, a, 'trans')]
    sp = lambda a, y: d['acct'][(y, a, 'spent')]
    db = sum((bud(a, Y1) - bud(a, Y0) for a in d['accounts']), D0)
    ds = sum((sp(a, Y1) - sp(a, Y0) for a in d['accounts']), D0)
    left0 = d['left'][Y0]
    if left0 + db - ds - open_ != left:
        fail('the leftover’s sources do not foot: %s + %s - %s - %s != %s' % (left0, db, ds, open_, left))
    big = [a for a in accts if al[a] > 0][:SLICES]
    small = [a for a in accts if a not in big]
    small_left = sum((al[a] for a in small), D0)
    nxt = big[1:7]
    nxt_left = sum((al[a] for a in nxt), D0)
    cbs = SERVICES
    if accts[0] != cbs:
        fail('the page leads with contracted building services; it is no longer the largest')
    em = '0100-3-300-4220-99-1-74-2-545004'
    em_before = [sp(em, y) for y in J.YEARS[:-1]]
    if not (bud(em, Y1) >= 3 * bud(em, Y0) and sp(em, Y1) < bud(em, Y1) / 2):
        fail('the emergency conclusion no longer matches the account')
    fx = dict(
        left=f('left', U(left), 'left unspent, %s' % C.fy(Y1), 'published', {'y': F(Y1)}),
        cbs=f('cbs', U(al[cbs]), 'of it, contracted building services', 'published'),
        nxt=f('nxt', U(nxt_left), 'of it, the next six accounts', 'published'),
        under=f('under', N(sum(1 for v in al.values() if v > 0), 'accounts'),
                'of %s left money; none ran over' % C.num(len(accts)), 'published',
                {'n': N(len(accts), 'accounts')}),
        left0=f('left0', U(left0), 'left unspent, %s' % C.fy(Y0), 'published', {'y': F(Y0)}),
        db=f('db', U(db), 'more budget than %s' % C.fy(Y0), 'published', {'y': F(Y0)}),
        ds=f('ds', U(-ds), 'less spent than %s' % C.fy(Y0), 'published', {'y': F(Y0)}),
        open=f('open', U(open_), 'still on order, %s' % C.fy(Y1), 'published', {'y': F(Y1)}),
        cbsd=f('cbsd', U(sp(cbs, Y0) - sp(cbs, Y1)), 'contracted services, less spent', 'published'),
        cbsb=f('cbsb', U(bud(cbs, Y1) - bud(cbs, Y0)), 'contracted services, more budget', 'published'),
        emb=f('emb', U(bud(em, Y1)), 'emergency budget, %s' % C.fy(Y1), 'published', {'y': F(Y1)}),
        ems=f('ems', U(sp(em, Y1)), 'emergency spending, %s' % C.fy(Y1), 'published', {'y': F(Y1)}),
    )
    acct_rows = []
    for a in accts:
        vals = [fl(bud(a, Y0)), fl(bud(a, Y1)), fl(sp(a, Y0)), fl(sp(a, Y1)), None, None]
        acct_rows.append(dict(
            label='%s (%s)' % (A[a]['account_description'].title(), a),
            marks=TP.change_marks(vals, [(1, 0), (3, 2)], MARK),
            cells=[C.usd(v) for v in vals[:4]] + [C.usd(fl(pieces[(a, 'open')])), C.usd(fl(al[a]))]))
    acct_rows.append(dict(label='Every account', cells=[
        C.usd(fl(v)) for v in (sum((bud(a, Y0) for a in d['accounts']), D0),
                               orig + carry + trans, d['spent'][Y0], paid, open_, left)]))
    order = sorted(pay, key=lambda p: (p == 'Journal entries and refunds', -fl(pay[p])))
    payee_views = []
    for i in range(0, len(order), PAYEE_VIEW):
        chunk = order[i:i + PAYEE_VIEW]
        payee_views.append(dict(
            key='payees-%d' % (i // PAYEE_VIEW + 1),
            label='Payees %d–%d' % (i + 1, i + len(chunk)), total_col=None,
            kinds=['ledger'] * 3, columns=['Type of work', 'Account', 'Paid, %s' % C.fy(Y1)],
            rows=[dict(label=p.title() if p != 'Journal entries and refunds' else p,
                       cells=[T.get(p, OTHER) if p != 'Journal entries and refunds' else '',
                              '; '.join(sorted(pay_acct[p])), C.usd(fl(pay[p]))]) for p in chunk],
            note='Every payee paid on building upkeep in %s, largest first; the views together '
                 'foot to %s. Names as MUNIS prints them, cut at twenty characters.'
                 % (C.fy(Y1), C.usd(fl(paid)))))
    move_rows = [dict(label=r['description'].strip() or '(no memo)', cells=[
        '%s (%s)' % (A[r['account']]['account_description'].title(), r['account']),
        r['effective_date'], C.usd(fl(r['amt']))])
        for r in sorted(moves, key=lambda r: (r['effective_date'], r['account']))]
    page = TP.page(
        'upkeep-surplus-every-dollar',
        'Building upkeep left %s in %s: %s on one account, the rest on %s others.'
        % (C.usd(fl(left)), C.fy(Y1), C.usd(fl(al[cbs])), C.num(sum(1 for v in al.values() if v > 0) - 1)),
        list(fx.values()),
        [con('Contracted building services holds %s of the %s; the next six accounts hold %s.'
             % (C.usd(fl(al[cbs])), C.usd(fl(left)), C.usd(fl(nxt_left))),
             ['left', 'cbs', 'nxt', 'under'],
             {'a': U(al[cbs]), 'b': U(left), 'c': U(nxt_left)},
             notes=[step('None of the %s accounts spent past its budget, so nothing inside the '
                         'figure offsets it.' % C.num(len(accts)), 'measured',
                         {'n': N(len(accts), 'accounts')})]),
         con('Against %s, the line had %s more budget and spent %s less.'
             % (C.fy(Y0), C.usd(fl(db)), C.usd(fl(-ds))),
             ['left0', 'db', 'ds', 'open'],
             {'y': F(Y0), 'a': U(db), 'b': U(-ds)},
             notes=[step('So %s left in %s became %s, less %s still on order.'
                         % (C.usd(fl(left0)), C.fy(Y0), C.usd(fl(left)), C.usd(fl(open_))),
                         'measured', {'a': U(left0), 'y': F(Y0), 'b': U(left), 'c': U(open_)})]),
         con('Contracted building services spent %s less than in %s, on %s more budget.'
             % (C.usd(fl(sp(cbs, Y0) - sp(cbs, Y1))), C.fy(Y0), C.usd(fl(bud(cbs, Y1) - bud(cbs, Y0)))),
             ['cbsd', 'cbsb'],
             {'a': U(sp(cbs, Y0) - sp(cbs, Y1)), 'y': F(Y0), 'b': U(bud(cbs, Y1) - bud(cbs, Y0))},
             notes=[step('Its own page lists each payee and every order released unpaid; Usual '
                         'purchases skipped lists what was usually bought and was not.',
                         'measured')]),
         con('Emergency expenditures were budgeted %s and spent %s; before, %s to %s a year.'
             % (C.usd(fl(bud(em, Y1))), C.usd(fl(sp(em, Y1))), C.usd(fl(min(em_before))),
                C.usd(fl(max(em_before)))),
             ['emb', 'ems'],
             {'a': U(bud(em, Y1)), 'b': U(sp(em, Y1)), 'c': U(min(em_before)), 'e': U(max(em_before))},
             notes=[step('The budget book raised it from %s, a 200%% increase.'
                         % C.usd(fl(bud(em, Y0))), 'measured', {'a': U(bud(em, Y0))},
                         allow=('200%',), cite=(BOOK, 'LPS budget book, 12 March 2025'))])],
        chart=TP.parts(
            'Where the leftover sits',
            [(LABEL_OF.get(a, A[a]['account_description'].title()), fl(al[a])) for a in big]
            + ([('%s smaller accounts' % C.num(len([a for a in small if al[a] > 0])), fl(small_left))]
               if small_left > 0 else []),
            '$', highlight=LABEL_OF[cbs],
            note='The %s left on building upkeep in %s, by the account it was left on.'
                 % (C.usd(fl(left)), C.fy(Y1)),
            note_figures={'a': U(left), 'y': F(Y1)}),
        also=[TP.bridge(
            'How the leftover grew from %s' % 'last year',
            ('Left unspent, %s' % C.fy(Y0), fl(left0)),
            [('More budget', fl(db)), ('Less spent', fl(-ds)), ('Still on order', -fl(open_))],
            ('Left unspent, %s' % C.fy(Y1), fl(left)), '$',
            note='Budget is the original appropriation plus every transfer, each year.')],
        table=dict(caption='Building upkeep, %s, every dollar' % C.fy(Y1), views=[
            dict(key='accounts', label='Where it sits', total_col=5, kinds=['ledger'] * 6,
                 columns=['Budget, %s' % C.fy(Y0), 'Budget, %s' % C.fy(Y1), 'Spent, %s' % C.fy(Y0),
                          'Spent, %s' % C.fy(Y1), 'On order', 'Left'],
                 rows=acct_rows,
                 note='Every account on the line, foots to %s. Budget includes transfers. MUNIS '
                      'account numbers.' % C.usd(fl(left)) + MARK_NOTE)]
            + payee_views
            + [dict(key='transfers', label='Transfers', total_col=None, kinds=['ledger'] * 3,
                    columns=['Account', 'Posted', 'Amount'], rows=move_rows,
                    note='Every transfer other than the carried-in encumbrances, with the memo '
                         'MUNIS records.')]),
        sources=sources(),
        finding_figures={'a': U(left), 'y': F(Y1), 'b': U(al[cbs]),
                         'n': N(sum(1 for v in al.values() if v > 0) - 1, 'accounts')})
    page['not_established'] = [
        'Which building or job each payment was for.',
        'Why each account left what it left: the postings show where the money went, not why '
        'it did not go further.',
        'The FY2026 figures after the close.',
    ]
    return page


# WHAT USUALLY GETS BOUGHT AND DID NOT (TJ, 20 October 2026: "from previous years, can we
# identify things we didnt get this year? Like, 'usually we ..... pay for paint, but that year
# we didnt'"). The unit is the PAYEE -- the thing the journal records -- with what its invoices
# say. USUAL is OUR definition: paid in every one of the three closed years, FY2023-FY2025, and
# its average over them. SKIPPED: FY2026 under half of usual, or nothing. A payee paid in two
# of the three years and nothing in FY2026 is listed apart, as an occasional purchase.
SKIP_SHARE = Decimal('0.5')
DESC_SKIP = re.compile(r'^[\d\s/#.-]*$|^LUNENBUR|^CUST#|^ACCOUNT|^BLANKET', re.I)


def what_for(descs):
    """The most common invoice description that says something -- not a customer number."""
    for text, _ in descs.most_common():
        if not DESC_SKIP.search(text):
            return text
    return ''


def skipped_page(d, U, F, P, N):
    from collections import Counter
    f, con = LD.fact, TP.conclusion
    A = d['A']
    T = trades()
    cat = lambda r: S.category_of(dict(account=r['account'], obj=r['object']))
    pv, desc = defaultdict(lambda: D0), defaultdict(Counter)
    for r in J.lines():
        if r['posts_to'] == 'actual' and J.in_surplus_scope(A[r['account']]) and cat(r) == CAT:
            p = J.payee(r)
            if p is J.MASKED:
                fail('a masked payee is on building upkeep')
            if p:
                pv[(p, r['fy'])] += r['amt']
                desc[p][r['description'].strip()[:30]] += 1
    closed = J.YEARS[:-1]
    usual = {p: sum((pv[(p, y)] for y in closed), D0) / len(closed)
             for p in {p for (p, _) in pv} if all(pv[(p, y)] > 0 for y in closed)}
    skipped = sorted((p for p in usual if pv[(p, Y1)] < SKIP_SHARE * usual[p]),
                     key=lambda p: fl(pv[(p, Y1)] - usual[p]))
    stopped = [p for p in skipped if pv[(p, Y1)] <= 0]
    occasional = sorted((p for p in {p for (p, _) in pv} if p not in usual
                         and sum(1 for y in closed if pv[(p, y)] > 0) == 2 and pv[(p, Y1)] <= 0
                         and sum((pv[(p, y)] for y in closed), D0) > 1000),
                        key=lambda p: -fl(sum((pv[(p, y)] for y in closed), D0)))
    short = sum((usual[p] - pv[(p, Y1)] for p in skipped), D0)
    new = sorted((p for p in {p for (p, _) in pv} if pv[(p, Y1)] > 0
                  and all(pv[(p, y)] <= 0 for y in closed)), key=lambda p: -fl(pv[(p, Y1)]))
    small = [p for p in stopped if usual[p] < 1000]
    if not (len(stopped) >= 2 and small):
        fail('the skipped conclusions assume at least two stopped payees, some of them small')
    big2 = [p for p in stopped if p not in small][:2]
    # The same TYPE OF WORK, new payees: is the stopped work being paid to somebody else?
    tw = T.get(big2[0], OTHER)
    if T.get(big2[1], OTHER) != tw:
        fail('the fourth conclusion assumes the two largest stopped payees do one type of work')
    tw_usual = usual[big2[0]] + usual[big2[1]]
    tw_new = [p for p in new if T.get(p, OTHER) == tw]
    tw_new_sum = sum((pv[(p, Y1)] for p in tw_new), D0)
    if not tw_new:
        fail('the fourth conclusion assumes new payees in the same type of work')
    label = lambda p: '%s, %s' % (p.title(), what_for(desc[p]).lower())
    fx = dict(
        n=f('n', N(len(skipped), 'payees'), 'usual payees under half their usual', 'estimate'),
        s=f('s', N(len(stopped), 'payees'), 'of them paid nothing at all', 'estimate'),
        short=f('short', U(short), 'below their usual, together', 'estimate'),
        u0=f('u0', U(usual[big2[0]]), '%s, usual a year' % big2[0].title()[:24], 'estimate'),
        u1=f('u1', U(usual[big2[1]]), '%s, usual a year' % big2[1].title()[:24], 'estimate'),
        nw=f('nw', N(len(new), 'payees'), 'paid in %s and in no year before' % C.fy(Y1), 'published',
             {'y': F(Y1)}),
        tw=f('tw', U(tw_new_sum), 'new payees, %s, %s' % (tw.lower()[:24], C.fy(Y1)), 'published',
             {'y': F(Y1)}),
        why=f('why', None, 'whether the work was done some other way', 'gap',
              closes='the facilities work orders for FY2026, by building and job'),
    )
    rows = [dict(label=p.title(), cells=[T.get(p, OTHER), what_for(desc[p])]
                 + [C.usd(fl(pv[(p, y)])) for y in J.YEARS] + [C.usd(fl(usual[p]))],
                 marks=TP.change_marks([None, None] + [fl(pv[(p, y)]) for y in J.YEARS] + [None],
                                       [(5, 4)], MARK))
            for p in skipped]
    occ_rows = [dict(label=p.title(), cells=[T.get(p, OTHER), what_for(desc[p])]
                     + [C.usd(fl(pv[(p, y)])) for y in J.YEARS])
                for p in occasional]
    new_rows = [dict(label=p.title(), cells=[T.get(p, OTHER), what_for(desc[p]),
                                             C.usd(fl(pv[(p, Y1)]))]) for p in new[:30]]
    page = TP.page(
        'upkeep-skipped',
        '%s payees the schools used every year were paid under half as usual in %s; %s got '
        'nothing.' % (C.num(len(skipped)), C.fy(Y1), C.num(len(stopped))),
        list(fx.values()),
        [con('Paid every year from %s to %s, %s payees fell %s below their usual in %s.'
             % (C.fy(closed[0]), C.fy(closed[-1]), C.num(len(skipped)), C.usd(fl(short)), C.fy(Y1)),
             ['n', 'short'],
             {'a': F(closed[0]), 'b': F(closed[-1]), 'n': N(len(skipped), 'payees'), 'c': U(short),
              'y': F(Y1)},
             notes=[step('Usual is our measure: the average of %s to %s.'
                         % (C.fy(closed[0]), C.fy(closed[-1])), 'estimate',
                         {'a': F(closed[0]), 'b': F(closed[-1])})]),
         con('%s and %s, usually %s and %s a year, were paid nothing in %s.'
             % (big2[0].title(), big2[1].title(), C.usd(fl(usual[big2[0]])), C.usd(fl(usual[big2[1]])),
                C.fy(Y1)),
             ['s', 'u0', 'u1'],
             {'a': U(usual[big2[0]]), 'b': U(usual[big2[1]]), 'y': F(Y1)},
             notes=[step('Their invoices read: %s.' % '; '.join('“%s”' % what_for(desc[p]).lower()
                                                               for p in big2), 'measured',
                         allow=tuple(what_for(desc[p]).lower() for p in big2))]),
         con('Small yearly purchases stopped too: %s.' % '; '.join(
             '%s' % what_for(desc[p]).lower() for p in small[:3]),
             ['s'], {}, allow=tuple(what_for(desc[p]).lower() for p in small[:3]),
             notes=[step('Each paid in all three years before; nothing on this line in %s.'
                         % C.fy(Y1), 'measured', {'y': F(Y1)})]),
         con('New %s payees were paid %s in %s, against the %s the two usually got.'
             % (tw.lower(), C.usd(fl(tw_new_sum)), C.fy(Y1), C.usd(fl(tw_usual))),
             ['tw', 'u0', 'u1', 'nw', 'why'],
             {'a': U(tw_new_sum), 'y': F(Y1), 'b': U(tw_usual)},
             notes=[step('They are %s: invoices read %s.'
                         % (', '.join(p.title() for p in tw_new),
                            '; '.join('“%s”' % what_for(desc[p]).lower() for p in tw_new)),
                         'measured', allow=tuple(what_for(desc[p]).lower() for p in tw_new)),
                    step('So part of the work may have moved to new vendors. Johnson Controls US '
                         'is likewise a separate vendor record from Johnson Controls.', 'hypothesis'),
                    step('Nothing paid on this line is not the same as not done; a payment from '
                         'another account looks the same.', 'measured')])],
        chart=TP.ranking('Below their usual, by payee',
                         [(p.title(), fl(pv[(p, Y1)] - usual[p])) for p in skipped], '$',
                         highlight=[p.title() for p in stopped], basis='estimate',
                         note='%s against each payee’s %s to %s average. Highlighted: paid '
                              'nothing.' % (C.fy(Y1), C.fy(closed[0]), C.fy(closed[-1])),
                         note_figures={'y': F(Y1), 'a': F(closed[0]), 'b': F(closed[-1])}),
        table=dict(caption='What building upkeep usually buys, and did not in %s' % C.fy(Y1), views=[
            dict(key='skipped', label='Usual, and skipped', total_col=None,
                 kinds=['ledger'] * 6 + ['estimate'],
                 columns=['Type of work', 'Invoices read', C.fy(2023), C.fy(2024), C.fy(2025),
                          C.fy(Y1), 'Usual'],
                 rows=rows,
                 note='Paid in every year %s to %s, and in %s under half of that average. '
                      'Invoice text as MUNIS prints it, cut short.' % (C.fy(closed[0]),
                                                                      C.fy(closed[-1]), C.fy(Y1))
                      + MARK_NOTE),
            dict(key='occasional', label='Occasional, not bought', total_col=None,
                 kinds=['ledger'] * 6,
                 columns=['Type of work', 'Invoices read'] + [C.fy(y) for y in J.YEARS],
                 rows=occ_rows,
                 note='Paid in two of the three years before, over $1,000 together, and nothing '
                      'in %s.' % C.fy(Y1)),
            dict(key='new', label='New in %s' % C.fy(Y1), total_col=None, kinds=['ledger'] * 3,
                 columns=['Type of work', 'Invoices read', C.fy(Y1)], rows=new_rows,
                 note='Paid in %s and in none of the three years before.' % C.fy(Y1))]),
        sources=sources(),
        finding_figures={'n': N(len(skipped), 'payees'), 'y': F(Y1), 's': N(len(stopped), 'payees')})
    page['not_established'] = [
        'Whether a skipped purchase was made some other way: another account, another fund, '
        'a new vendor record, or a contract that changed.',
        'Which building each payment was for.',
    ]
    return page


X_MONTHS = ['Start', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']


def outputs():
    return {os.path.join(OUT_DIR, '%s.json' % t):
            json.dumps(p, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
            for t, p in build().items()}


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
        print('buildings and grounds topics: %d outputs current' % len(outs))
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
