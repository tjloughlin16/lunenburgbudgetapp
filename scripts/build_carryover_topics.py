#!/usr/bin/env python3
"""ORDERS CARRIED FROM ONE SCHOOL YEAR INTO THE NEXT, and what that does to a comparison with the vote.

    python3 scripts/build_carryover_topics.py           # write fy28/public/data/topics/carried-over-orders.json
    python3 scripts/build_carryover_topics.py --check   # fail if it would change

    carried-over-orders   /school-all-funds/carried-over-orders   Carried-over orders

On the School budget, all funds shelf, group "Left unspent" (scripts/topic_registry/
school_all_funds.py, through TOPIC_GENERATORS). TJ, 23 October 2026: "is it possible our budget
is off because we keep carrying over things? can we create a page or view or tab of the
carryover year to year."

WHAT A CARRIED ORDER IS, as the journal records it (measured here, and refused if it stops
being true -- `tie()`):
  * at a year's close, `YEC` ("YEAR END LIQUIDATION") lines zero every purchase order still open
    on an account. They carry no PO number and no vendor;
  * on 1 July the next year, `SOY` ("ENCUMBRANCE OUTSTANDING PURCH") lines reopen them, one line
    per order and account, WITH the PO number and the vendor. Per account, the multiset of SOY
    amounts equals the multiset of the previous year's YEC amounts, line for line;
  * and a `BUA` transfer described `ENCUMBRANCE CARRY FORWARD <year>` (journal.is_carry_forward)
    raises that account's budget by the same amount, to the cent. So the REVISED budget carries
    the order's money with it; the ORIGINAL vote (`BUC`) does not.
During the next year each reopened order is drawn down by payments (`POL`, a liquidation posted
with the invoice) or closed without one (`POM`). What is still open at that close is carried
again. `FY2026` is not closed in this run (journal.OPEN_FY).

THE COMPARISON THE PAGE MAKES (rule 1: budget against spending, same year, nothing projected).
SPENT is the site's definition (journal.SPENT): payments plus what is still owed. In a closed
year that is the payments, because the close zeroes what is owed. A year's spending therefore
INCLUDES payments on orders carried in from the year before and EXCLUDES orders carried out to
the year after, which are paid and counted next year. "Moved back" re-assigns those payments to
the year that carried them: spent - paid on orders carried in + paid next year on orders carried
out. OUR arithmetic, labelled as ours. It moves only what was PAID: an order closed unpaid was
never spent in either year. For FY2026 nothing is moved out, because what FY2026 still owes is
already inside its spent by the definition.

A liquidation is what an invoice DREW DOWN on the order; an invoice can differ from it by a
little (one pays $931.01 against $931.31 liquidated), and the difference is booked as an
ordinary payment of the year. That is the grain of this page and it says so.

RULE 7. The size of the shift is measured. Whether carrying orders is "why the budget is off"
is a hypothesis, and the page says so beside the figure. Why an order was open on 30 June, and
why one was closed unpaid, is in no ledger (sources/data/money-gaps.csv).

EXPENSE ACCOUNTS ONLY. Every YEC and SOY line is on an expense account (refused otherwise). One
order sat on a REVENUE account through a close without either: PO 23002087 (DEE BUS SERVICE,
$1,092.00) on 1305-...-436500, opened in FY2023 period 12, never zeroed at the FY2023 close, and
closed unpaid by a POM in FY2024. It is not spending and it was not carried by the mechanism this
page describes, so it is outside every scope here; `tie()` asserts that no closed year leaves an
expense account owing anything.

THE REDACTION. Vendors are shown as the journal prints them. A masked payee is never a row of
its own: it is inside "every other order", which also holds named vendors.
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
from build_school_all_funds import code_names  # noqa: E402  (DESE's names; one copy)

OUT_DIR = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics')
ME = os.path.basename(__file__)
TID = 'carried-over-orders'
MINE = sorted(t for t, (_, _, gen) in REG.TOPICS.items() if gen == ME)
Y = J.YEARS
F0, F1 = Y[0], Y[-1]
CLOSES = [y for y in Y if y != J.OPEN_FY]           # years whose close is in the run
ZERO = Decimal(0)
TOP_ORDERS = 12
SCOPES = ('gf', 'sped', 'other')
WHY_CLOSES = ('the district’s year-end list of open purchase orders, with the reason each was '
              'kept open or closed')


def fail(msg):
    raise SystemExit('build_carryover_topics: ' + msg)


def scope_of(a):
    """gf: every general fund expense account; sped: the general fund's special education
    accounts in the total (journal.in_sped_total) -- a subset of gf; other: every other fund."""
    s = set()
    if not J.is_expense(a):
        return s
    if a['fund'] == '0100':
        s.add('gf')
        if J.in_sped_total(a):
            s.add('sped')
    else:
        s.add('other')
    return s


def line_names():
    """code_names() (DESE's own row labels, one copy, in build_school_all_funds.py), plus the
    codes DESE prints only inside a combined row -- `Equipment (7300, 7400)` -- named by that row,
    and the district's own codes DESE's chart does not hold (2310, 2357: money-gaps.csv)."""
    import csv
    import re
    names = code_names()
    for r in csv.DictReader(open(os.path.join(ROOT, 'sources', 'data', 'eoyr-schedule1.csv'),
                                 encoding='utf-8')):
        codes = [c.strip() for c in r['function_code'].split(',')]
        if len(codes) > 1 and all(re.fullmatch(r'\d{4}', c) for c in codes):
            for c in codes:
                names.setdefault(c, r['description'].strip())
    return lambda code: '%s %s' % (code, names.get(code, '(district code, not in DESE’s chart)'))


def data():
    A = J.accounts()
    L = J.lines()
    sc = lambda r: scope_of(A[r['account']])
    if any(r['source'] in ('YEC', 'SOY') and not J.is_expense(A[r['account']]) for r in L):
        fail('a carried order posts to a non-expense account; the scopes assume none does')

    # ---- every year's totals, by scope
    tot = defaultdict(Decimal)        # (key, fy, scope)
    for r in L:
        for s in sc(r):
            k = r['fy'], s
            if r['source'] == 'YEC':
                tot[('out',) + k] -= r['amt']
            if r['source'] == 'SOY':
                tot[('in',) + k] += r['amt']
            if J.is_carry_forward(r):
                tot[('cf',) + k] += r['amt']
            if r['posts_to'] == 'original_budget':
                tot[('vote',) + k] += r['amt']
            if r['posts_to'] == 'transfer':
                tot[('transfer',) + k] += r['amt']
            if J.is_spent(r):
                tot[('spent',) + k] += r['amt']
            if r['posts_to'] == 'encumbrance':
                tot[('owed',) + k] += r['amt']

    # ---- the carried orders, one per SOY line
    # The order's own description is on its POE line. Some orders were opened on one account and
    # carried on another (Nature's Classroom, PO 23001909: opened on a revolving-fund revenue
    # account), so the PO number alone is the fallback.
    poe, poe_doc = {}, {}
    for r in L:
        if r['source'] == 'POE':
            poe.setdefault((r['doc_no'], r['account']), r['description'].strip())
            poe_doc.setdefault(r['doc_no'], r['description'].strip())
    after = defaultdict(lambda: defaultdict(Decimal))
    for r in L:
        if r['posts_to'] == 'encumbrance' and r['doc_type'] == 'PO' and r['source'] != 'SOY':
            after[(r['fy'], r['doc_no'], r['account'])][r['source']] += r['amt']
    soy = [r for r in L if r['source'] == 'SOY']
    if len({(r['fy'], r['doc_no'], r['account']) for r in soy}) != len(soy):
        fail('two SOY lines share a year, PO and account; an order is no longer one line')
    soy_amt = {(r['fy'], r['doc_no'], r['account']): r['amt'] for r in soy}
    orders = []
    for r in soy:
        k = (r['fy'], r['doc_no'], r['account'])
        got = after.get(k, {})
        if set(got) - {'POL', 'POM'}:
            fail('carried order %s on %s posts %s; only POL and POM are read' % (k[1], k[2], sorted(got)))
        paid, closed = -got.get('POL', ZERO), -got.get('POM', ZERO)
        again = r['amt'] - paid - closed
        nxt = soy_amt.get((r['fy'] + 1, r['doc_no'], r['account']), ZERO)
        if r['fy'] == J.OPEN_FY:
            # Not closed: what is left is still owed, and is inside FY2026's spent already.
            pass
        elif again != nxt:
            fail('order %s on %s: %s left open at the FY%d close, but FY%d reopens %s'
                 % (r['doc_no'], r['account'], again, r['fy'], r['fy'] + 1, nxt))
        a = A[r['account']]
        orders.append(dict(
            into=r['fy'], po=r['doc_no'], account=r['account'], scopes=sc(r),
            vendor=None if J.is_masked_payee(r) else ' '.join(r['vendor'].split()),
            desc=poe.get((r['doc_no'], r['account'])) or poe_doc.get(r['doc_no']),
            code=J.function(r['account']),
            group=J.fund_group(a), carried=r['amt'], paid=paid, closed=closed, again=again))
    for o in orders:
        for s in o['scopes']:
            for f in ('paid', 'closed', 'again'):
                tot[(f + '_in', o['into'], s)] += o[f]
    return dict(tot=tot, orders=orders)


def tie(d):
    """Rule 13: the per-year identities the page rests on, recomputed per ACCOUNT and per LINE,
    not only in total. Returns the counts it checked."""
    A = J.accounts()
    L = J.lines()
    n = 0
    for y in CLOSES:
        yec, soy, cf = defaultdict(list), defaultdict(list), defaultdict(Decimal)
        for r in L:
            if r['fy'] == y and r['source'] == 'YEC':
                yec[r['account']].append(-r['amt'])
            if r['fy'] == y + 1 and r['source'] == 'SOY':
                soy[r['account']].append(r['amt'])
            if r['fy'] == y + 1 and J.is_carry_forward(r):
                cf[r['account']] += r['amt']
        for acct in set(yec) | set(soy) | set(cf):
            if sorted(yec[acct]) != sorted(soy[acct]):
                fail('FY%d close: account %s zeroes %s and FY%d reopens %s'
                     % (y, acct, sorted(yec[acct]), y + 1, sorted(soy[acct])))
            if sum(soy[acct], ZERO) != cf[acct]:
                fail('FY%d: account %s reopens %s and its carry-forward is %s'
                     % (y + 1, acct, sum(soy[acct], ZERO), cf[acct]))
            n += len(soy[acct])
    t = d['tot']
    for y in Y:
        for s in SCOPES:
            if t[('cf', y, s)] != t[('in', y, s)]:
                fail('FY%d %s: carry-forward %s, reopened %s' % (y, s, t[('cf', y, s)], t[('in', y, s)]))
            if y in CLOSES and t[('out', y, s)] != t[('in', y + 1, s)]:
                fail('FY%d %s: carried out %s, FY%d reopened %s'
                     % (y, s, t[('out', y, s)], y + 1, t[('in', y + 1, s)]))
            if y in CLOSES and t[('owed', y, s)] != 0:
                fail('FY%d %s: a closed year still owes %s' % (y, s, t[('owed', y, s)]))
            parts = t[('paid_in', y, s)] + t[('closed_in', y, s)] + t[('again_in', y, s)]
            if parts != t[('in', y, s)]:
                fail('FY%d %s: paid + closed + again is %s, carried in %s' % (y, s, parts, t[('in', y, s)]))
    if t[('out', J.OPEN_FY, 'gf')] != 0:
        fail('FY%d has a close in this run; the page says it does not' % J.OPEN_FY)
    return n


def effect(t, s):
    """Per year: vote, spent as booked, paid on orders carried in, paid next year on orders
    carried out, and spent with carry-overs moved back."""
    out = {}
    for y in Y:
        pin = t[('paid_in', y, s)]
        pout = t[('paid_in', y + 1, s)] if y in CLOSES else ZERO
        b = t[('spent', y, s)]
        out[y] = dict(vote=t[('vote', y, s)], booked=b, pin=pin, pout=pout,
                      moved=b - pin + pout)
    return out


def sources():
    return [
        dict(label='Lunenburg Budget Project — munis-school-journal.csv (every school journal '
                   'line, FY2023–FY2026, our redacted reading of the Town’s Report 1)',
             href=J.PUBLIC['journal']),
        dict(label='Lunenburg Budget Project — munis-school-journal-accounts.csv (every school '
                   'account, with the FY2026 figures the report prints)',
             href=J.PUBLIC['accounts']),
        dict(label='Town of Lunenburg — how the journal reached us, and what was redacted',
             href='/docs/town-ledgers/account-details/'
                  'PROVENANCE-fy2023-fy2026-p13-school-journal.md'),
    ]


def build():
    d = data()
    checked = tie(d)
    t = d['tot']
    name = line_names()
    U = lambda v: figure(float(v), C.usd(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=1: figure(float(v), C.pct(v, dp))
    f, con = LD.fact, TP.conclusion
    fv = lambda x: float(x)

    gf, sp = effect(t, 'gf'), effect(t, 'sped')
    out_gf = {y: t[('out', y, 'gf')] for y in CLOSES}
    share = {y: 100 * out_gf[y] / t[('vote', y, 'gf')] for y in CLOSES}
    ymax = max(CLOSES, key=lambda y: out_gf[y])
    # The three closes in the run, and what the following year did with them.
    car3 = sum((t[('in', y + 1, 'gf')] for y in CLOSES), ZERO)
    paid3 = sum((t[('paid_in', y + 1, 'gf')] for y in CLOSES), ZERO)
    closed3 = sum((t[('closed_in', y + 1, 'gf')] for y in CLOSES), ZERO)
    shift = {y: gf[y]['moved'] - gf[y]['booked'] for y in Y}
    ys = max(Y, key=lambda y: abs(shift[y]))
    smax = max(abs(shift[y]) / gf[y]['vote'] * 100 for y in Y)
    sped_paid = sum((t[('paid_in', y, 'sped')] for y in Y), ZERO)
    sped_car = sum((t[('in', y, 'sped')] for y in Y), ZERO)
    if sped_paid != 0:
        fail('a special education order carried on the general fund was paid; conclusion 4 says none was')
    if any(sp[y]['moved'] != sp[y]['booked'] for y in Y):
        fail('the special education comparison moves; conclusion 4 says it does not')
    y25 = F1 - 1
    if not (gf[y25]['booked'] < gf[y25]['vote'] and gf[y25]['moved'] < gf[y25]['booked']):
        fail('conclusion 3 says FY%d was under its vote and further under moved back' % y25)
    owed26 = t[('owed', J.OPEN_FY, 'gf')] + t[('owed', J.OPEN_FY, 'other')]
    under = lambda y, k: gf[y]['vote'] - gf[y][k]

    px = {}
    px['out'] = f('out', U(out_gf[ymax]), 'general fund orders carried out of %s, the most'
                  % C.fy(ymax), 'published', {'y': F(ymax)})
    px['share'] = f('share', P(share[ymax], 2), 'of the %s general fund vote' % C.fy(ymax),
                    'published', {'y': F(ymax)})
    px['cf'] = f('cf', U(t[('cf', ymax + 1, 'gf')]), 'added to the %s budget for them'
                 % C.fy(ymax + 1), 'published', {'y': F(ymax + 1)})
    px['paid'] = f('paid', P(100 * paid3 / car3, 0), 'of orders carried out of %s paid the next year'
                   % C.fyspan(CLOSES[0], CLOSES[-1]), 'published',
                   {'y': figure(CLOSES[0], C.fyspan(CLOSES[0], CLOSES[-1]), 'fiscal years')})
    px['closed'] = f('closed', U(closed3), 'of them closed the next year with nothing paid',
                     'published')
    px['shift'] = f('shift', U(abs(shift[ys])), 'largest move in a year’s spending, %s, moved back'
                    % C.fy(ys), 'estimate', {'y': F(ys)})
    px['b25'] = f('b25', U(under(y25, 'booked')), '%s general fund under its vote, as booked'
                  % C.fy(y25), 'published', {'y': F(y25)})
    px['m25'] = f('m25', U(under(y25, 'moved')), '%s under its vote, carry-overs moved back'
                  % C.fy(y25), 'estimate', {'y': F(y25)})
    px['sped'] = f('sped', U(sped_paid), 'special education orders carried and paid next year',
                   'published')
    px['owed'] = f('owed', U(owed26), 'owed at the end of the run, %s, every fund, not closed'
                   % C.fy(J.OPEN_FY), 'published', {'y': F(J.OPEN_FY)})
    px['why'] = f('why', None, 'why an order was still open on 30 June', 'gap',
                  allow=('30',), closes=WHY_CLOSES)

    oy = CLOSES
    concl = [
        con('The general fund carried %s, %s and %s of open orders out of %s, %s and %s.'
            % (C.usd(out_gf[oy[0]]), C.usd(out_gf[oy[1]]), C.usd(out_gf[oy[2]]),
               C.fy(oy[0]), C.fy(oy[1]), C.fy(oy[2])),
            ['out', 'share'],
            {'a': U(out_gf[oy[0]]), 'b': U(out_gf[oy[1]]), 'c': U(out_gf[oy[2]]),
             'x': F(oy[0]), 'y': F(oy[1]), 'z': F(oy[2])},
            notes=[step('The most, in %s, was %s of that year’s vote. Every other fund together '
                        'carried %s, %s and %s.'
                        % (C.fy(ymax), C.pct(share[ymax], 2), C.usd(t[('out', oy[0], 'other')]),
                           C.usd(t[('out', oy[1], 'other')]), C.usd(t[('out', oy[2], 'other')])),
                        'measured',
                        {'y': F(ymax), 'p': P(share[ymax], 2),
                         'a': U(t[('out', oy[0], 'other')]), 'b': U(t[('out', oy[1], 'other')]),
                         'c': U(t[('out', oy[2], 'other')])})]),
        con('Each order’s budget went with it: the next year’s budget rose by exactly the amount '
            'carried, outside the vote.',
            ['cf', 'out'],
            notes=[step('Of %s carried out of the three closes, %s was paid the next year and %s '
                        'was closed with nothing paid, which returned that budget to its line.'
                        % (C.usd(car3), C.usd(paid3), C.usd(closed3)), 'measured',
                        {'a': U(car3), 'b': U(paid3), 'c': U(closed3)}),
                   step('Why an order was still open on 30 June, or why one was closed without '
                        'payment, is in no ledger.', 'gap', allow=('30',), closes=WHY_CLOSES)]),
        con('Moving carried orders back to the year that ordered them shifts general fund '
            'spending by %s at most.' % C.usd(abs(shift[ys])),
            ['shift', 'b25', 'm25'],
            {'a': U(abs(shift[ys]))},
            notes=[step('That is at most %s of a year’s vote. Whether carrying orders is why the '
                        'budget looks off is a hypothesis; the shift is what is measured.'
                        % C.pct(smax, 2), 'hypothesis', {'p': P(smax, 2)}),
                   step('%s as booked was %s under its vote; moving its carry-overs back makes it '
                        '%s under, not less.' % (C.fy(y25), C.usd(under(y25, 'booked')),
                                                C.usd(under(y25, 'moved'))), 'measured',
                        {'y': F(y25), 'a': U(under(y25, 'booked')), 'b': U(under(y25, 'moved'))})]),
        con('Special education’s gap to its vote does not move: none of its carried orders was '
            'paid the next year.',
            ['sped'],
            notes=[step('Its accounts carried %s in four years, all of it closed unpaid.'
                        % C.usd(sped_car), 'measured', {'a': U(sped_car)})]),
    ]

    # ---- the signature: carried out against carried in, by year
    xs = [C.fy(y) for y in Y]
    chart = TP.series('Orders carried out and carried in', xs, [
        TP.track('Carried in, general fund', [fv(t[('in', y, 'gf')]) for y in Y], 'published'),
        TP.track('Carried out, general fund', [fv(out_gf[y]) if y in CLOSES else None for y in Y],
                 'published'),
        TP.track('Carried in, other funds', [fv(t[('in', y, 'other')]) for y in Y], 'published'),
        TP.track('Carried out, other funds',
                 [fv(t[('out', y, 'other')]) if y in CLOSES else None for y in Y], 'published')],
        '$', kind='bar',
        note='Carried in opens a year on 1 July; carried out is what its close left open. %s is '
             'not closed in this run.' % C.fy(J.OPEN_FY),
        note_figures={'y': F(J.OPEN_FY)}, note_allow=('1',))
    also = [TP.series('Spending against the vote, two ways', xs, [
        TP.track('As booked', [fv(gf[y]['booked'] - gf[y]['vote']) for y in Y], 'published'),
        TP.track('Carry-overs moved back, our arithmetic',
                 [fv(gf[y]['moved'] - gf[y]['vote']) for y in Y], 'estimate')],
        '$', kind='bar',
        note='General fund spent less its original vote. Below zero is under the vote.')]

    # ---- table 1: the comparison, general fund and special education, the same columns
    cols = ['Original vote', 'Spent, as booked', 'Less paid on orders carried in',
            'Plus paid next year on orders carried out', 'Spent, moved back',
            'Booked less vote', 'Moved back less vote']

    def eview(key, label, e, note):
        rows = [dict(label=C.fy(y), cells=[
            C.usd(e[y]['vote']), C.usd(e[y]['booked']), C.usd(-e[y]['pin']),
            C.usd(e[y]['pout']) if y in CLOSES else None, C.usd(e[y]['moved']),
            C.usd(e[y]['booked'] - e[y]['vote']), C.usd(e[y]['moved'] - e[y]['vote'])])
            for y in Y]
        return dict(key=key, label=label, total_col=4, kinds=['ledger'] * len(cols),
                    columns=cols, rows=rows, note=note)
    t1 = dict(caption='Spent against the original vote, as booked and with carry-overs moved back',
              views=[eview('gf', 'General fund', gf,
                           'Spent is payments plus what is still owed. %s is not closed, and what '
                           'it still owes is already in its spent.' % C.fy(J.OPEN_FY)),
                     eview('sped', 'Special education, general fund', sp,
                           'The general fund’s special education accounts in the total '
                           '(journal.py). School psychologists are outside it.')])

    # ---- table 2: by budget line and fund group, one view per close
    def label_close(y):
        return 'Out of %s' % C.fy(y - 1)
    lcols = ['Carried', 'Paid next year', 'Closed unpaid', 'Carried again']
    by_line = defaultdict(lambda: defaultdict(Decimal))
    for o in d['orders']:
        k = (o['code'], o['group'])
        for fld in ('carried', 'paid', 'closed', 'again'):
            by_line[(o['into'], k)][fld] += o[fld]
    lviews = []
    for y in Y:
        ks = sorted((k for (yy, k) in by_line if yy == y),
                    key=lambda k: (-by_line[(y, k)]['carried'], k))
        rows = []
        for code, grp in ks:
            v = by_line[(y, (code, grp))]
            rows.append(dict(label='%s · %s' % (name(code), grp),
                             cells=[C.usd(v[x]) for x in ('carried', 'paid', 'closed', 'again')]))
        if len(rows) > TP.TABLE_ROWS_MAX - 1:
            fail('%s carried orders on %d lines; the table holds %d' % (C.fy(y), len(rows), TP.TABLE_ROWS_MAX))
        tt = [sum((by_line[(y, k)][x] for k in ks), ZERO) for x in ('carried', 'paid', 'closed', 'again')]
        rows.append(dict(label='Every line', cells=[C.usd(x) for x in tt]))
        lviews.append(dict(key='l%d' % y, label=label_close(y), total_col=0,
                           kinds=['ledger'] * 4, columns=lcols, rows=rows,
                           note='Reopened on 1 July %d, and what %s did with them.%s'
                                % (y - 1, C.fy(y), ' Not yet closed.' if y == J.OPEN_FY else '')))
    t2 = dict(caption='Carried orders by budget line and fund', views=lviews)

    # ---- table 3: the largest carried orders, one view per close
    ocols = ['Ordered for', 'Budget line', 'Fund', 'Carried', 'Paid next year', 'Closed unpaid',
             'Carried again']
    oviews = []
    for y in Y:
        os_ = sorted((o for o in d['orders'] if o['into'] == y),
                     key=lambda o: (-o['carried'], o['po'], o['account']))
        named = [o for o in os_ if o['vendor']][:TOP_ORDERS]
        rest = [o for o in os_ if o not in named]
        if rest and all(not o['vendor'] for o in rest):
            fail('%s: every order outside the table is masked, so its amount could be read off'
                 % C.fy(y))
        rows = []
        for o in named:
            rows.append(dict(label='%s · PO %s' % (o['vendor'], o['po']), cells=[
                o['desc'] or 'not in this run (ordered before %s)' % C.fy(F0), name(o['code']),
                o['group'], C.usd(o['carried']), C.usd(o['paid']), C.usd(o['closed']),
                C.usd(o['again'])]))
        if rest:
            rows.append(dict(label='Every other order (%d)' % len(rest), cells=[
                None, None, None] + [C.usd(sum((o[x] for o in rest), ZERO))
                                     for x in ('carried', 'paid', 'closed', 'again')]))
        rows.append(dict(label='All %d carried orders' % len(os_), cells=[None, None, None] + [
            C.usd(sum((o[x] for o in os_), ZERO)) for x in ('carried', 'paid', 'closed', 'again')]))
        oviews.append(dict(key='o%d' % y, label=label_close(y), total_col=3,
                           kinds=['ledger'] * len(ocols), columns=ocols, rows=rows,
                           note='One row per order and account. Vendor and description as the '
                                'journal prints them, cut at twenty and thirty characters.'))
    t3 = dict(caption='The largest carried orders', views=oviews)

    page = TP.page(
        TID,
        'The general fund carried at most %s of open orders into a new year, and the budget went '
        'with them.' % C.usd(out_gf[ymax]),
        list(px.values()), concl, chart=chart, also=also, tables=[t1, t2, t3],
        sources=sources(), finding_figures={'a': U(out_gf[ymax])})
    page['not_established'] = [
        'Why any order was still open on 30 June, or why one was closed without being paid. '
        'Neither is in a ledger.',
        'Whether carrying orders is why a year’s spending looks off against its vote. What is '
        'measured is how far moving them back shifts it.',
        'Which year’s money an invoice truly belonged to beyond the order it drew down: an '
        'invoice can differ from the amount it liquidated.',
        'Whether an order closed with nothing paid was bought again on a new order. The journal '
        'ties a payment to its order, never one order to the one before it; in a revolving fund, '
        'Nature’s Classroom’s carried order was closed and the same amount paid on a new one.',
        'What FY2026 will carry out: its close is not in this run.',
    ]
    if [TID] != MINE:
        fail('the registry gives this script %s; it builds %s' % (MINE, [TID]))
    model = dict(
        checked_lines=checked,
        years={str(y): {s: {k: str(t[(k, y, s)]) for k in
                            ('vote', 'spent', 'out', 'in', 'cf', 'paid_in', 'closed_in', 'again_in', 'owed')}
                        for s in SCOPES} for y in Y},
        effect={s: {str(y): {k: str(v) for k, v in e[y].items()} for y in Y}
                for s, e in (('gf', gf), ('sped', sp))})
    return {TID: page}, model


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
        print('carried-over orders: %d output current' % len(outs))
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
