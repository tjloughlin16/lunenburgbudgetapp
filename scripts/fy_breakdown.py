#!/usr/bin/env python3
"""ONE FISCAL YEAR, BROKEN DOWN: why a school general fund line ended with money left over,
in four measured parts. The model; `build_fy_breakdown.py` writes the page from it and
`verify_fy_breakdown.py` recomputes it by a different route.

    import fy_breakdown as FB
    m = FB.model()                     # every year, every line, the four parts
    python3 scripts/fy_breakdown.py    # print the year totals and the two worked cases

TJ, 26 October 2026: *"there HAS to be a way to see why they had leftover money."* The answer
here is an IDENTITY, not an estimate (notes/HANDOFF-FY-BREAKDOWN.md). For every line of the
school general fund (fund 0100, department 300, `journal.in_surplus_scope`):

    left on the line  =  voted - all-funds cost      (1) voted above what it cost, all funds
                      +  transfers in, less out      (2) budget moved between lines (BUA)
                      +  paid by other funds         (3) grants, circuit breaker, fees, capital
                      +  carried, less paid for      (4) another year's money: orders carried
                         another year                    in less what they paid; next year's
                                                         invoices paid early

It is accounting arithmetic. What the general fund spent on a line is the line's all-funds
cost, less what other funds paid of it, plus what it paid for other years; and what was left
is what was voted, plus transfers and carried budget, less what it spent. Every term is
measured off the journal, so the four sum to what was left to the cent or this refuses.

WHAT IS MEASURED AND WHAT IS OURS (rule 7). Terms 2 and 4 are postings the Town made, read
off their source codes. Term 3 is OUR reading: which other-fund spending counts toward which
general fund line is a match rule, declared below, and every dollar carries the rule that
placed it. Term 1 is what is left once 3 is placed, so (1) + (3) is a measurement and the
split between them is our reading. Other-fund money no rule places stays UNMATCHED, its own
row, and is never folded into term 1 (rule 13, a join that matches nothing).

THE FOOTING: counting orders still owed (TJ, 23 October 2026: spent = payments plus owed). A
closed year's close (`YEC`) zeroes its open orders and next year re-opens them (`SOY`) against
carried-forward budget; here the closed year keeps them as spent, and the year that pays them
sees carried budget in and payments out -- term 4. So FY2025 is $554,945, not the $627,117
its period-13 report prints, and every year is on the footing FY2026's report already uses.

THE MATCH RULES for term 3, in order; a line of another fund's spending is placed by the first
that applies, and only once:

  a. MOVED BY JOURNAL ENTRY. A `GEN`/`GRV` journal whose expense lines touch the surplus scope
     and another fund and net to zero (within a dollar). The books name both ends, so this is
     the one rule that is not a reading: the other fund's line is the general fund line's cost
     moved. Paired with the scope lines of opposite sign, same function code first, shared in
     proportion to their size. Only cost moved ONTO another fund is placed this way. A cost
     moved back onto the general fund was first booked by the other fund, and is left with that
     account, where it nets against the booking it reverses: the IDEA grant's aide payroll
     (fund 2813, function 0000, unmatched) moved onto the general fund's aide lines in June
     2026 is $205,645 out of that account's unmatched pay, not a negative on the aide lines. This generalises build_pay_by_fund_topics' pay moves to every
     expense (the 29 June 2026 reclass of collaborative tuition onto the circuit breaker is not
     pay).
  b. SAME PAYEE. A shown payee (`journal.payee`) the general fund paid by invoice from a scope
     line in any year of the run. Placed on that payee's scope line of the same function code
     if there is one, else on the scope line that paid it most over the four years. This is
     what catches the IDEA grant booking May Institute's tuition as contracted services.
  c. SAME FUNCTION. The other fund's own function code is one the general fund budget is voted
     on (`journal.function_class == 'line'`). Placed on a CATEGORY (build_school_surplus's,
     by its own `category_of`), not a line: a function code names a kind of work, and spreading
     it over the accounts that share it would be an allocation we invented. So each category
     carries one extra row, `same function, other funds`, whose left is zero.
  -. UNMATCHED. Everything else: lunch, extended day, spending booked to a heading (2000) or
     to no function (0000) with a payee the general fund never paid. Shown, never placed.

CAPITAL ARTICLES are not matched by payee or function (rules b and c), only by a journal entry
naming both ends (rule a). A capital article is its own Town Meeting appropriation for a
project; that the HVAC contractor it pays also services the buildings on a general fund line
makes it the same payee, not the same cost. Ours, and it moves real money: about $818,000 of
FY2026 capital spending would otherwise land on operating lines.

PAYROLL has no payee (journal.PAYROLL_GRAIN), so pay reaches term 3 only through rule a (moved
by journal entry) or rule c (a grant salary account on a voted function code).

WHAT IS NOT HELD. The special funds the period-13 report prints tie to the journal to the cent
(`tie_special`); the journal also holds funds that report leaves out (prior-year grant awards,
capital articles), and both are used. Spending the school's ledger never sees -- benefits
charged on the town side, student activity accounts -- is not here (money-gaps).
"""
import csv
import os
import re
import sys
from collections import defaultdict
from decimal import ROUND_HALF_EVEN, Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import journal as J  # noqa: E402
import build_school_surplus as S  # noqa: E402

ROOT = J.ROOT
P13 = os.path.join(J.DATA, 'munis-school-ytd.csv')
D0 = Decimal(0)
CENT = Decimal('0.01')
TERMS = ('voted_above_cost', 'transfers', 'other_funds', 'another_year')
TERM_LABEL = {'voted_above_cost': 'Voted above what it cost',
              'transfers': 'Moved in or out by transfer',
              'other_funds': 'Paid by other funds',
              'another_year': 'Another year’s money'}
RULES = ('moved', 'payee', 'function')
RULE_LABEL = {'moved': 'moved by journal entry', 'payee': 'same payee',
              'function': 'same function code', 'unmatched': 'not matched to any line'}
FUNC_ROW = 'same function, other funds'

# NEXT YEAR'S INVOICES PAID EARLY. FLLAC numbers its invoices by the school year they bill
# (`25L2KEY..` FY2025, `26..`, `27..`), each prefix with its own quarterly rate -- our reading
# of the numbering, corroborated in notes/HANDOFF-SURPLUS-PAGES.md. A scope invoice whose
# prefix names a LATER year than the one paying it is next year's tuition. No other payee's
# invoice numbers carry a year, so no other prepayment can be read; the only one this finds is
# FY2026's $189,276.75. Applied to the surplus scope only: the one later-prefixed invoice in
# another fund (`26L2KEY46`, circuit breaker, April 2025) is FY2025's fourth quarter with a
# mistyped prefix -- the one number missing from FY2025's KEY41-47 run -- and stays FY2025.
PREPAID = re.compile(r'^(\d\d)L2KEY')


def fail(msg):
    raise SystemExit('fy_breakdown: ' + msg)


def is_prepaid(r):
    m = PREPAID.match(r['doc_no']) if r['source'] in ('API', 'APM') else None
    return bool(m) and int(m.group(1)) > r['fy'] % 100


def is_capital(a):
    return J.fund_group(a) == 'Capital and other'


def cat_of(account):
    return S.category_of(dict(account=account, obj=account.split('-')[-1]))


def payer(a):
    """Who paid, for reading: a grant by its program name, the other groups by name."""
    g = J.fund_group(a)
    if g == 'General fund':
        return 'General fund' if J.in_surplus_scope(a) else 'General fund, outside the school budget'
    if g == 'Grants':
        return J.grant_program(a)
    return g


def share(total, weights):
    """`total` split over `weights` (key -> positive Decimal) to the cent, largest remainder."""
    w = sum(weights.values())
    raw = {k: total * v / w for k, v in weights.items()}
    out = {k: v.quantize(CENT, rounding='ROUND_DOWN') if total >= 0 else
           -((-v).quantize(CENT, rounding='ROUND_DOWN')) for k, v in raw.items()}
    rest = total - sum(out.values())
    step = CENT if rest > 0 else -CENT
    for k in sorted(raw, key=lambda k: (-(abs(raw[k] - out[k])), k)):
        if rest == 0:
            break
        out[k] += step
        rest -= step
    return out


def tie_special():
    """Every fund the period-13 special funds report prints, against the journal's actuals for
    it, to the cent. Returns (funds tied, funds the journal holds that the report omits)."""
    A = J.accounts()
    rep = defaultdict(Decimal)
    for r in csv.DictReader(open(P13, encoding='utf-8', newline='')):
        if r['report'] == 'special-school' and r['type'] == 'E':
            rep[(int(r['fiscal_year']), r['fund'])] += Decimal(r['ytd_expended']).quantize(CENT)
    jr = defaultdict(Decimal)
    for r in J.lines():
        a = A[r['account']]
        if J.is_expense(a) and r['posts_to'] == 'actual' and a['fund'] != '0100':
            jr[(r['fy'], a['fund'])] += r['amt']
    tied, extra = set(), set()
    for k in set(rep) | set(jr):
        if k in rep and k in jr:
            if rep[k] != jr[k]:
                fail('fund %s in FY%d: the report prints %s, the journal sums %s'
                     % (k[1], k[0], rep[k], jr[k]))
            tied.add(k)
        elif k in jr:
            extra.add(k)
        elif rep[k] != 0:
            fail('fund %s in FY%d is in the report and not the journal' % (k[1], k[0]))
    return tied, extra


def model():
    A, L = J.accounts(), J.lines()
    exp = [r for r in L if J.is_expense(A[r['account']])]
    scope = lambda r: J.in_surplus_scope(A[r['account']])

    # ---------------------------------------------------- the scope lines, measured
    line = defaultdict(lambda: defaultdict(Decimal))      # (fy, account) -> piece -> amount
    carried = defaultdict(set)                            # (fy, account) -> carried-in PO numbers
    for r in exp:
        if scope(r) and r['source'] == 'SOY':
            carried[(r['fy'], r['account'])].add(r['doc_no'])
    prepaid = []
    for r in exp:
        if not scope(r):
            continue
        k, p = (r['fy'], r['account']), line[(r['fy'], r['account'])]
        if r['source'] == 'BUC' or J.is_netting(r):
            p['voted'] += r['amt']
        elif J.is_carry_forward(r):
            p['carried_budget'] += r['amt']
        elif r['source'] == 'BUA':
            p['transfers'] += r['amt']
        elif r['source'] == 'YEC':
            p['closed'] += r['amt']           # left out: the owed footing keeps the order spent
        else:
            p['gf_spent'] += r['amt']
            if r['doc_no'] in carried[k] and r['source'] != 'SOY':
                if r['source'] == 'POL':
                    p['carried_paid'] -= r['amt']       # a liquidation is the payment it records
                p['carried_enc'] += r['amt']
            elif r['source'] == 'SOY':
                p['carried_enc'] += r['amt']
            if is_prepaid(r):
                p['prepaid'] += r['amt']
                prepaid.append(r)

    # ---------------------------------------------------- other funds' spending, placed
    def other_spent(r):
        return (not scope(r)) and J.is_spent(r) and r['source'] != 'YEC'

    placed = defaultdict(lambda: defaultdict(Decimal))    # (fy, account) -> rule -> amount
    by_payer = defaultdict(Decimal)                       # (fy, account, rule, payer)
    func_cat = defaultdict(Decimal)                       # (fy, category, payer)
    how = defaultdict(lambda: defaultdict(Decimal))       # (fy, account) -> (rule, payer, how)
    func_codes = defaultdict(set)
    unmatched = defaultdict(Decimal)                      # (fy, category or '', payer, why)
    done = set()

    # rule a: moved by journal entry
    jr = defaultdict(list)
    for r in exp:
        if r['source'] in ('GEN', 'GRV'):
            jr[(r['fy'], r['journal'])].append(r)
    moves = []
    for (fy, j), rs in sorted(jr.items()):
        if len({r['fund'] for r in rs}) < 2 or abs(sum(r['amt'] for r in rs)) > 1:
            continue
        sc, ot = [r for r in rs if scope(r)], [r for r in rs if not scope(r)]
        if not sc or not ot:
            continue
        off = sum((o['amt'] for o in ot if o['amt'] > 0), D0)
        onto = sum((o['amt'] for o in ot if o['amt'] < 0), D0)
        for o in ot:
            if o['amt'] <= 0:
                continue        # a cost taken back: placed with its own account (docstring, a)
            opp = [s for s in sc if s['amt'] < 0]
            same = [s for s in opp if J.function(s['account']) == J.function(o['account'])]
            pool = same or opp
            if not pool or o['amt'] == 0:
                continue
            w = defaultdict(Decimal)
            for s in pool:
                w[s['account']] += abs(s['amt'])
            for acct, amt in share(o['amt'], w).items():
                placed[(fy, acct)]['moved'] += amt
                by_payer[(fy, acct, 'moved', payer(A[o['account']]))] += amt
                how[(fy, acct)][('moved', payer(A[o['account']]), '%s · %s' % (
                    o['effective_date'], o['description'].strip() or 'no memo'))] += amt
            done.add(id(o))
        by = defaultdict(Decimal)
        for o in ot:
            by[payer(A[o['account']])] += o['amt']
        moves.append(dict(fy=fy, journal=j, date=rs[0]['effective_date'], off=off, onto=onto,
                          by_payer=dict(by), categories=sorted({cat_of(r['account']) for r in sc}),
                          description=sorted({r['description'].strip() for r in rs})[0]))

    # rule b: same payee
    paid = defaultdict(lambda: defaultdict(Decimal))      # payee -> scope account -> invoices
    for r in exp:
        if scope(r) and r['source'] in ('API', 'APM'):
            p = J.payee(r)
            if p is not None and p is not J.MASKED:
                paid[p][r['account']] += r['amt']
    for r in exp:
        if id(r) in done or not other_spent(r):
            continue
        p = J.payee(r)
        if p is None or p is J.MASKED or p not in paid or is_capital(A[r['account']]):
            continue
        g = paid[p]
        same = [a for a in g if J.function(a) == J.function(r['account'])]
        acct = max(same or g, key=lambda a: (g[a], a))
        placed[(r['fy'], acct)]['payee'] += r['amt']
        by_payer[(r['fy'], acct, 'payee', payer(A[r['account']]))] += r['amt']
        how[(r['fy'], acct)][('payee', payer(A[r['account']]), p)] += r['amt']
        done.add(id(r))

    # rule c: same function code, on a category; the rest unmatched
    for r in exp:
        if id(r) in done or not other_spent(r):
            continue
        a, f = A[r['account']], J.function(r['account'])
        if is_capital(a):
            unmatched[(r['fy'], payer(a), 'a capital article')] += r['amt']
        elif J.function_class(f) == 'line':
            func_cat[(r['fy'], cat_of(r['account']), payer(a))] += r['amt']
            func_codes[(r['fy'], cat_of(r['account']), payer(a))].add(f)
        else:
            why = {'heading': 'booked to a heading', 'none': 'booked to no function',
                   'other': 'a function the general fund has no line for'}[J.function_class(f)]
            unmatched[(r['fy'], payer(a), why)] += r['amt']

    # ---------------------------------------------------- transfers, line by line
    # For each line, every transfer journal it was in: the amount it gave or got, and the lines
    # on the other side. Where either side is ONE line the pairing is exact; where many gave and
    # many got in one entry, the books do not say which giver funded which receiver, and
    # `paired` is False.
    line_transfers = defaultdict(list)
    for t in transfers():
        for mine, other in ((t['gave'], t['got']), (t['got'], t['gave'])):
            for x in mine:
                cps = [dict(account=o['account'], description=o['description'],
                            amount=o['amount']) for o in other]
                if t['outside'] and (x['amount'] > 0) == (t['outside'] > 0):
                    cps.append(dict(account=None, description='outside the school budget',
                                    amount=-t['outside']))
                exact = len(cps) == 1 or len(mine) == 1
                if len(cps) == 1:
                    # one line on the other side: this line's own amount is what passed between them
                    cps[0]['amount'] = -x['amount']
                line_transfers[(t['fy'], x['account'])].append(dict(
                    date=t['date'], memo=t['description'], amount=x['amount'],
                    paired=exact, others=cps))

    # ---------------------------------------------------- the identity, line by line
    # A payee's line may have no postings of its own in the year; it still carries what was
    # placed on it, with nothing voted. Without this the money placed there would vanish.
    for k in list(placed):
        line[k]                                   # noqa: B018 -- creates the empty line
    rows = []
    for (fy, acct), p in sorted(line.items()):
        o = sum(placed[(fy, acct)].values(), D0)
        cost_gf = p['gf_spent'] - p['prepaid'] - p['carried_paid'] - p['carried_enc']
        another = p['carried_budget'] - p['carried_paid'] - p['carried_enc'] - p['prepaid']
        t = dict(voted_above_cost=p['voted'] - cost_gf - o, transfers=p['transfers'],
                 other_funds=o, another_year=another)
        left = p['voted'] + p['transfers'] + p['carried_budget'] - p['gf_spent']
        if sum(t.values()) != left:
            fail('FY%d %s: the four parts do not sum to what was left' % (fy, acct))
        rows.append(dict(fy=fy, account=acct, category=cat_of(acct),
                         gf_spent=p['gf_spent'],
                         other_year_spent=p['prepaid'] + p['carried_paid'] + p['carried_enc'],
                         how=dict(how[(fy, acct)]), moves_in=line_transfers.get((fy, acct), []),
                         description=A[acct]['account_description'].strip(),
                         org=A[acct]['org_name'].strip(), voted=p['voted'],
                         gf_cost=cost_gf, all_funds_cost=cost_gf + o, left=left,
                         printed_left=left - p['closed'], prepaid=p['prepaid'],
                         carried_budget=p['carried_budget'],
                         carried_unpaid=p['carried_budget'] - p['carried_paid'] - p['carried_enc'],
                         by_rule={k: placed[(fy, acct)][k] for k in ('moved', 'payee')},
                         payers={(rl, py): v for (y, ac, rl, py), v in by_payer.items()
                                 if y == fy and ac == acct},
                         **t))
    for (fy, cat, py), v in sorted(func_cat.items()):
        rows.append(dict(fy=fy, account=None, category=cat, description=FUNC_ROW, org='',
                         voted=D0, gf_cost=D0, all_funds_cost=v, left=D0, printed_left=D0,
                         gf_spent=D0, other_year_spent=D0, moves_in=[],
                         how={('function', py, 'function code %s' % '/'.join(
                             sorted(func_codes[(fy, cat, py)]))): v},
                         prepaid=D0, carried_budget=D0, carried_unpaid=D0,
                         by_rule={'function': v}, payers={('function', py): v},
                         voted_above_cost=-v, transfers=D0, other_funds=v, another_year=D0))

    if sum((sum(v.values(), D0) for v in placed.values()), D0) != sum(
            (r['other_funds'] for r in rows if r['account']), D0):
        fail('money placed on a line is missing from the rows')
    years = {}
    for fy in J.YEARS:
        rs = [r for r in rows if r['fy'] == fy]
        tot = {t: sum((r[t] for r in rs), D0) for t in TERMS}
        left = sum((r['left'] for r in rs), D0)
        if sum(tot.values()) != left:
            fail('FY%d: the four totals do not sum to what was left' % fy)
        printed = sum((r['printed_left'] for r in rs), D0)
        if fy != J.OPEN_FY and printed - left != -sum(
                (line[(fy, a)]['closed'] for (y, a) in line if y == fy), D0):
            fail('FY%d: the two footings do not differ by the orders closed' % fy)
        rule = defaultdict(Decimal)
        for r in rs:
            for k, v in r['by_rule'].items():
                rule[k] += v
        years[fy] = dict(left=left, printed_left=printed, terms=tot, by_rule=dict(rule),
                         unmatched={(py, why): v for (y, py, why), v in unmatched.items()
                                    if y == fy},
                         prepaid=sum((r['prepaid'] for r in rs), D0),
                         carried_unpaid=sum((r['carried_unpaid'] for r in rs), D0),
                         carried_budget=sum((r['carried_budget'] for r in rs), D0))
    return dict(rows=rows, years=years, moves=moves, prepaid=prepaid, transfers=transfers(),
                tie=tie_special(), flows=flows(rows, unmatched))


def transfers():
    """Every budget transfer between school lines (`BUA`, not a carry-forward, not the FY2025
    netting), one entry per journal: when, what the Town wrote, which lines gave and which got.
    Both ends are named, so these are the only line-to-line pairings the books record. A
    journal that does not net to zero brought budget in from outside department 300 (the
    Reserve Fund, a Town Meeting vote, department 301) or sent it out; `outside` says how much."""
    A = J.accounts()
    js = defaultdict(list)
    for r in J.lines():
        if (J.in_surplus_scope(A[r['account']]) and r['source'] == 'BUA'
                and not J.is_carry_forward(r) and not J.is_netting(r) and r['amt'] != 0):
            js[(r['fy'], r['journal'])].append(r)
    out = []
    for (fy, j), rs in sorted(js.items()):
        side = lambda pos: sorted(({'account': r['account'], 'category': cat_of(r['account']),
                                     'description': A[r['account']]['account_description'].strip(),
                                     'amount': r['amt']} for r in rs if (r['amt'] > 0) == pos),
                                   key=lambda x: -abs(x['amount']))
        out.append(dict(fy=fy, journal=j, date=min(r['effective_date'] for r in rs),
                        description=sorted({r['description'].strip() for r in rs})[0],
                        gave=side(False), got=side(True),
                        moved=sum((r['amt'] for r in rs if r['amt'] > 0), D0),
                        outside=sum((r['amt'] for r in rs), D0)))
    return out


def flows(rows, unmatched):
    """The alluvial's data: (fy, category, payer) -> all-funds cost of this year's work. The
    general fund's own part per category, every placed other-fund dollar on the category of the
    line it was placed on, and the unmatched money in one grey block per year."""
    out = defaultdict(Decimal)
    for r in rows:
        if r['account']:
            out[(r['fy'], r['category'], 'General fund')] += r['gf_cost']
        for (_, py), v in r['payers'].items():
            out[(r['fy'], r['category'], py)] += v
    for (fy, py, _), v in unmatched.items():
        out[(fy, 'unmatched', py)] += v
    return dict(out)


def main():
    m = model()
    for fy, y in m['years'].items():
        print('FY%d  left %s (printed %s)' % (fy, f"{y['left']:,.2f}", f"{y['printed_left']:,.2f}"))
        for t in TERMS:
            print('   %-28s %16s' % (TERM_LABEL[t], f"{y['terms'][t]:,.2f}"))
        print('   by rule', {k: f'{v:,.0f}' for k, v in y['by_rule'].items()},
              'unmatched', f"{sum(y['unmatched'].values(), D0):,.0f}")
    for acct in ('0100-3-300-9300-51-1-06-2-535019', '0100-3-300-9400-51-1-06-2-535023'):
        r = next(r for r in m['rows'] if r['fy'] == 2026 and r['account'] == acct)
        print(r['description'], {t: f'{r[t]:,.2f}' for t in TERMS + ('left', 'voted', 'gf_cost')},
              {k: f'{v:,.2f}' for k, v in r['payers'].items()})


if __name__ == '__main__':
    main()
