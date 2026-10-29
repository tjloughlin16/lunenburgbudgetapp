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

  a. MOVED BY JOURNAL ENTRY. A `GEN`/`GRV` entry -- ONE MEMO of a journal (`entries()`) -- whose
     expense lines touch the surplus scope and another fund, the two sides going opposite ways.
     The books name both ends, so this is the one rule that is not a reading. It is measured on
     the SCHOOL side, line by line: a school line's own negative posting in the entry is cost
     taken off it, now paid by another fund (placed on that line, `moved_off`); a positive one is cost moved back onto it
     (`moved_on`, already in what it spent). Which fund took it is shared over the funds the
     entry put money on, in proportion -- the payer split, not the amount, is the sharing. The
     other funds' lines are not read again: what each fund gave or took beyond the cost it
     took off a school line -- a move back, or cost passed between two grants in the same entry
     (on 19 June 2026 Title I took $77,777 of kindergarten pay off the school budget and, in
     the same entry, $87,302 of pay off the Student Opportunity Act grant) -- is left with that
     fund as unmatched, where it nets against the booking it reverses. This generalises
     build_pay_by_fund_topics' pay moves to every expense (the 29 June 2026 reclass of
     collaborative tuition onto the circuit breaker is not pay).
  b. SAME PAYEE. A shown payee (`journal.payee`) the general fund paid by invoice from a scope
     line in any year of the run. Placed on that payee's scope line of the same function code
     if there is one, else on the scope line that paid it most over the four years. This is
     what catches the IDEA grant booking May Institute's tuition as contracted services.
  c. SAME FUNCTION. The other fund's own function code is one the general fund budget is voted
     on (`journal.function_class == 'line'`). Placed on a CATEGORY (build_school_surplus's,
     by its own `category_of`), not a line: a function code names a kind of work, and spreading
     it over the accounts that share it would be an allocation we invented. So each category
     carries one extra row, `same function, other funds`, whose left is zero.
  -. MOVED BETWEEN FUNDS, NO SCHOOL LINE (28 October 2026). A `GEN`/`GRV` entry outside the school
     budget, one memo at a time as `entries()` reads --
     where one fund's postings net below zero and another's above. A journal entry is a
     RECLASSIFICATION: the cost was already paid, by payroll or a bill, and the entry changes
     which fund carries it; no cash moves. Booked as `between` on each fund, its net, and not
     matched to any line -- before this each half fell to rules b and c as ordinary spending, so
     one grant award showed negative spending under a function code and the next award positive.
     Line figures do not move (no school line is in it); funds' `function` and `none` give way to
     `between`. Read off the entry, never inferred: nothing here extends a correction to money it
     did not move (TJ, 28 October 2026; rule d was built and removed for doing that).
     `fund_moves_between` lists every such entry, and every memo of a rule a entry in which cost
     passed fund to fund beside the school side (the school lines read as one more party, so the
     RECLASS SCHOOL MEMO 10/11/24-6 entry reads as $111,186.16 from IDEA's FY2023 award to its
     FY2024 one): fy, journal, date, memos, what each fund gave and took, and the PAIRS -- exact
     where one fund is on a side or two amounts match to the cent, else `paired` False, the books
     not saying which giver's cost went to which receiver (the convention `transfers()` uses).
     Each pair is classed (`move_class`): one grant programme from one year's award to another's
     (`award`, to a `later` or `earlier` award, by the year the fund's name states), grant to
     grant, grant and revolving or lunch fund, and so on. An entry that exactly undoes an earlier
     one is marked on both (`reverses`, `reversed_by`).
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
# A PAYMENT, counted under a chip: an invoice paid or a payroll line. Orders, their liquidations
# and journal entries are not payments; a re-charge is counted as a journal entry instead.
PAYMENT = ('API', 'APM', 'PRJ', 'PRH')

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


def entries(jr, scope):
    """Rule a's entries: (fy, journal, rows) for each move between a school line and another fund.

    AN ENTRY IS A MEMO (TJ, 28 October 2026, deciding it: "your recommendation is the only one
    that makes sense... the other seems to create accounting bugs"). A journal with one memo is
    one entry. A journal with several is read one memo at a time, whether or not it nets as a
    whole: 2023/12/001312 nets, and holds three corrections under three memos -- school pay onto
    the school choice fund, onto a FY2021 grant, and Title I moved between two awards -- and
    reading it whole shared each school line's cost over every fund any memo touched, crediting a
    fund with cost its own memo never moved. A memo is a move when its school side and its
    other-fund side go opposite ways; that test is what keeps an accrual out (summer pay posted
    positive on both sides moves nothing). A memo that does not net (the Turkey Hill security
    system: $40,000 off a school line, $40,867 onto three grants) leaves its remainder with the
    funds of THAT memo, as `moved between funds` -- never spread over another memo's funds.

    THE ONE EXCEPTION: the halves of one correction keyed under two memos. 2025/10/000604 takes
    $13,900 of substitutes' pay off school lines under "ADJ EXP TO FY25 CSHS" and puts it on the
    school health grant under "ADJ EXP FR GF"; neither memo nets, the journal does. So in a
    journal that nets, the memos that do NOT net on their own are read together as one entry
    (`part` the tuple of their memos) -- they can only balance each other. A memo that nets on
    its own is never pooled."""
    for (fy, j), rs in sorted(jr.items()):
        if len({r['fund'] for r in rs}) < 2:
            continue
        nets = abs(sum(r['amt'] for r in rs)) <= 1
        if len({r['description'].strip() for r in rs}) == 1 and nets:
            yield fy, j, rs, None
            continue
        memo = defaultdict(list)
        for r in rs:
            memo[r['description'].strip()].append(r)
        groups = []
        pool = []
        for m_, g in sorted(memo.items()):
            if nets and abs(sum(r['amt'] for r in g)) > 1:
                pool.append((m_, g))
            else:
                groups.append((m_, g))
        if len(pool) == 1:
            groups += pool
        elif pool:
            groups.append((tuple(m_ for m_, _ in pool), [r for _, g in pool for r in g]))
        for m_, g in sorted(groups, key=lambda mg: str(mg[0])):
            s = sum((r['amt'] for r in g if scope(r)), D0)
            o = sum((r['amt'] for r in g if not scope(r)), D0)
            if s * o < 0:
                yield fy, j, g, m_


def award_year(a):
    """The fiscal year a grant award's fund name states ('FY24 IDEA #240' -> 2024), else None."""
    m = re.match(r"\s*FY\s*'?(\d\d)", a['fund_name'])
    return 2000 + int(m.group(1)) if m else None


_FUND_ACCT = {}


def fund_acct(f):
    if not _FUND_ACCT:
        for a in J.accounts().values():
            _FUND_ACCT.setdefault(a['fund'], a)
    return _FUND_ACCT[f]


MOVE_CLASSES = ('award', 'grant', 'grant-revolving', 'circuit-breaker', 'general-fund', 'other')


def move_class(a, b):
    """(class, direction) of cost moved from fund a to fund b. `award`: one grant programme, from
    one year's award to another's -- direction `later`, `earlier`, or None where a name states no
    year or both state the same one."""
    fa, fb = fund_acct(a), fund_acct(b)
    ga, gb = J.fund_group(fa), J.fund_group(fb)
    if ga == gb == 'Grants':
        if J.grant_program(fa) == J.grant_program(fb):
            ya, yb = award_year(fa), award_year(fb)
            return 'award', (None if ya is None or yb is None or ya == yb
                             else 'later' if yb > ya else 'earlier')
        return 'grant', None
    gs = {ga, gb}
    if 'Grants' in gs and 'Revolving funds and lunch' in gs:
        return 'grant-revolving', None
    if 'Circuit breaker' in gs:
        return 'circuit-breaker', None
    if 'General fund' in gs:
        return 'general-fund', None
    return 'other', None


def pair(gave, got):
    """Which giver's cost went to which receiver, where the books say: a giver and a receiver of
    the same amount to the cent, or ONE fund on a side (its amounts are the other side's). Where
    several gave and several took unequal amounts the books do not say, and what is left is
    returned unpaired -- the convention `transfers()` uses for lines."""
    g, r = dict(gave), dict(got)
    pairs = []
    for a in sorted(g):
        for b in sorted(r):
            if g[a] and g[a] == r[b]:
                pairs.append((a, b, g[a]))
                g[a] = r[b] = D0
    g = {k: v for k, v in g.items() if v}
    r = {k: v for k, v in r.items() if v}
    if len(g) == 1 and r:
        (a, va), = g.items()
        if sum(r.values()) <= va:
            for b, v in sorted(r.items()):
                pairs.append((a, b, v))
            g, r = ({a: va - sum(r.values())} if va != sum(r.values()) else {}), {}
        elif len(r) == 1:
            (b, vb), = r.items()
            pairs.append((a, b, va))
            g, r = {}, {b: vb - va}
    elif len(r) == 1 and g:
        (b, vb), = r.items()
        if sum(g.values()) <= vb:
            for a, v in sorted(g.items()):
                pairs.append((a, b, v))
            g, r = {}, ({b: vb - sum(g.values())} if vb != sum(g.values()) else {})
    return pairs, g, r


SCHOOL = 'school'           # the school budget's side of an entry, as one party in `pair()`


def fund_move(fy, j, rows, amounts, with_school):
    """One memo's move between funds: what each fund gave (cost taken off it) and took (cost put
    on it), paired where the books say. `amounts` may carry SCHOOL, the memo's school lines net,
    as one more party: its pairs are rule a's and are left out, so what remains is fund to fund.
    None unless some fund gave cost to another fund."""
    amounts = {f: v for f, v in amounts.items() if v}
    gave = {f: -v for f, v in amounts.items() if v < 0}
    got = {f: v for f, v in amounts.items() if v > 0}
    pairs, g_left, r_left = pair(gave, got)
    pairs = [p for p in pairs if SCHOOL not in p[:2]]
    fg = {f: v for f, v in g_left.items() if f != SCHOOL}
    fr = {f: v for f, v in r_left.items() if f != SCHOOL}
    if not pairs and not (fg and fr):
        return None
    gave_f, got_f = defaultdict(Decimal), defaultdict(Decimal)
    for a, b, v in pairs:
        gave_f[a] += v
        got_f[b] += v
    for f, v in fg.items():
        gave_f[f] += v
    for f, v in fr.items():
        got_f[f] += v
    rs = [r for r in rows if r['fund'] in gave_f or r['fund'] in got_f]
    out = []
    for a, b, v in pairs:
        cls, dir_ = move_class(a, b)
        out.append(dict(gave=a, got=b, amount=v, cls=cls, dir=dir_))
    return dict(fy=fy, journal=j, date=min(r['effective_date'] for r in rs),
                memos=sorted({r['description'].strip() for r in rs} - {''}) or ['no memo'],
                with_school=with_school, gave=dict(gave_f), got=dict(got_f), pairs=out,
                paired=not g_left and not r_left, unpaired_gave=fg, unpaired_got=fr,
                moved=sum((v for _, _, v in pairs), D0) + min(sum(fg.values(), D0), sum(fr.values(), D0)))


def reversals(moves):
    """An entry that exactly undoes an earlier one -- what one gave, the other took, fund by fund
    and to the cent -- is marked on both, so a page shows the pair as cancelling."""
    moves.sort(key=lambda m: (m['date'], m['journal'], m['memos']))
    seen = defaultdict(int)
    for m in moves:
        seen[m['journal']] += 1
        m['id'] = '%s#%d' % (m['journal'], seen[m['journal']])
        m['reverses'] = m['reversed_by'] = None
    for i, b in enumerate(moves):
        for a in moves[:i]:
            if a['reversed_by'] is None and a['reverses'] is None and a['gave'] == b['got'] \
                    and a['got'] == b['gave']:
                a['reversed_by'], b['reverses'] = b['id'], a['id']
                break


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
    # THE SAME MONEY, BY SOURCE (TJ, 27 October 2026: "what the non-general fund paid for ... per
    # source"). Every placement below is also kept by FUND, so one fund's spending can be read
    # whole: (fy, fund) -> (kind, where) -> amount, kind one of later (re-charged off a school
    # line onto it), back (re-charged from it back onto one), between (the rest of a journal
    # entry), payee, function, capital, none. And each fund's postings, with where each went.
    src = defaultdict(lambda: defaultdict(Decimal))
    src_rows = defaultdict(list)                          # (fy, fund) -> [(row, kind, where)]

    # rule a: moved by journal entry
    jr = defaultdict(list)
    for r in exp:
        if r['source'] in ('GEN', 'GRV'):
            jr[(r['fy'], r['journal'])].append(r)
    moves = []
    fund_moves = defaultdict(list)                        # (fy, account) -> journal moves on it
    backs = defaultdict(Decimal)                          # (fy, account, fund) -> moved back
    rem_entries = []                                      # rule a's entries, read again below
    for fy, j, rs, part in entries(jr, scope):
        sc, ot = [r for r in rs if scope(r)], [r for r in rs if not scope(r)]
        if not sc or not ot:
            continue
        off = -sum((s['amt'] for s in sc if s['amt'] < 0), D0)
        onto = sum((s['amt'] for s in sc if s['amt'] > 0), D0)
        net = defaultdict(Decimal)                        # payer -> what this entry put on it
        fnet = defaultdict(Decimal)                       # fund -> the same
        for o in ot:
            net[payer(A[o['account']])] += o['amt']
            fnet[o['fund']] += o['amt']
            done.add(id(o))
        flose = {f: -v for f, v in fnet.items() if v < 0}
        gain = {py: v for py, v in net.items() if v > 0} or {py: abs(v) for py, v in net.items()}
        lose = {py: -v for py, v in net.items() if v < 0} or {py: abs(v) for py, v in net.items()}
        memo = lambda s: s['description'].strip() or 'no memo'
        put = defaultdict(Decimal)
        # ONE posting per school account per entry: an entry can post both a debit and a credit
        # to the same line (30 June 2026, MOVE HEALTH INS FY26: -$99,017 and +$42,398 on health
        # insurance, the other side $56,619 to the revolving funds). The line's move is the net.
        acc = defaultdict(Decimal)
        for x in sc:
            acc[x['account']] += x['amt']
        sc = [dict(account=a_, amt=v, effective_date=min(x['effective_date'] for x in sc
                                                          if x['account'] == a_),
                   description=sorted({x['description'].strip() for x in sc
                                       if x['account'] == a_})[0]) for a_, v in sorted(acc.items())]
        off = -sum((x['amt'] for x in sc if x['amt'] < 0), D0)
        onto = sum((x['amt'] for x in sc if x['amt'] > 0), D0)
        for s in sc:
            if s['amt'] == 0:
                continue
            k = (fy, s['account'])
            line[k]['moved_off' if s['amt'] < 0 else 'moved_on'] += abs(s['amt'])
            split = share(abs(s['amt']), gain if s['amt'] < 0 else lose)
            # `part`: the memo this move is, when it is one memo of a batch; None, the whole entry
            fund_moves[k].append(dict(date=s['effective_date'], memo=memo(s), journal=j,
                                      part=part, amount=s['amt'], payers=split))
            if s['amt'] > 0:
                if flose:
                    for f, amt in share(s['amt'], flose).items():
                        backs[(fy, s['account'], f)] += amt
                continue
            for py, amt in split.items():
                placed[k]['moved'] += amt
                by_payer[(fy, s['account'], 'moved', py)] += amt
                how[k][('moved', py, '%s · %s' % (s['effective_date'], memo(s)))] += amt
                put[py] += amt
        # What each fund gave or took in the entry beyond the cost it took off a school line:
        # cost moved BACK onto the school budget, and cost passed between two other funds. Left
        # with the fund, where it nets against the booking it reverses (docstring, rule a).
        for py, v in net.items():
            if v - put[py] != 0:
                unmatched[(fy, py, 'moved between funds by journal entry')] += v - put[py]
        # by fund: the same entry, split the same way across the funds that gained or lost
        fgain = {f: v for f, v in fnet.items() if v > 0} or {f: abs(v) for f, v in fnet.items()}
        fput = defaultdict(Decimal)
        for x in sc:
            if x['amt'] < 0:
                for f, amt in share(-x['amt'], fgain).items():
                    src[(fy, f)][('later', x['account'])] += amt
                    fput[f] += amt
            elif x['amt'] > 0 and flose:
                for f, amt in share(x['amt'], flose).items():
                    src[(fy, f)][('back', x['account'])] -= amt
                    fput[f] -= amt
        for f, v in fnet.items():
            if v - fput[f] != 0:
                src[(fy, f)][('between', None)] += v - fput[f]
        rem_entries.append(dict(fy=fy, journal=j, rows=rs, scope=scope))
        for o in ot:
            src_rows[(fy, o['fund'])].append((o, 'journal', j))
        moves.append(dict(fy=fy, journal=j, part=part, date=rs[0]['effective_date'], off=off, onto=onto,
                          by_payer=dict(net), categories=sorted({cat_of(r['account']) for r in sc}),
                          description=sorted({r['description'].strip() for r in rs})[0]))

    # rule b: same payee
    paid_from = defaultdict(Decimal)                      # (fy, account, fund) -> placed by payee
    payments = defaultdict(int)                           # (fy, account or category) -> how many
    placed_rows = defaultdict(list)                       # (fy, account or (category, payer)) -> rows
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
        paid_from[(r['fy'], acct, r['fund'])] += r['amt']
        by_payer[(r['fy'], acct, 'payee', payer(A[r['account']]))] += r['amt']
        how[(r['fy'], acct)][('payee', payer(A[r['account']]), p)] += r['amt']
        if r['source'] in PAYMENT:
            payments[(r['fy'], acct)] += 1
        placed_rows[(r['fy'], acct)].append(r)
        src[(r['fy'], r['fund'])][('payee', acct)] += r['amt']
        src_rows[(r['fy'], r['fund'])].append((r, 'payee', acct))
        done.add(id(r))

    # A cost a fund paid directly toward a line, then moved back onto that line by journal entry
    # (30 June 2026, MOVE HEALTH INS FY26: revolving funds' MIIA premiums), is the school
    # budget's cost, not the fund's: netted off what the fund paid directly, up to what it paid,
    # and out of the move's unmatched remainder. Without this it is counted twice in what the
    # line cost, once in what the school budget spent and once as paid directly.
    fund_payer = {a['fund']: payer(a) for a in A.values()}
    for (fy, acct, f), b in sorted(backs.items()):
        n = min(b, paid_from[(fy, acct, f)])
        if n <= 0:
            continue
        py = fund_payer[f]
        placed[(fy, acct)]['payee'] -= n
        by_payer[(fy, acct, 'payee', py)] -= n
        how[(fy, acct)][('payee', py, 'less bills re-charged back to the school budget')] -= n
        src[(fy, f)][('payee', acct)] -= n          # by fund: the move back nets the payment
        src[(fy, f)][('back', acct)] += n
        unmatched[(fy, py, 'moved between funds by journal entry')] += n
        if unmatched[(fy, py, 'moved between funds by journal entry')] == 0:
            del unmatched[(fy, py, 'moved between funds by journal entry')]

    # Rule a's entries, read for what passed between two funds: one memo at a time, the school
    # lines as one party, so a memo that took pay off one grant award and put it partly on a
    # school line and partly on the next award is read as the books print it (RECLASS SCHOOL
    # MEMO 10/11/24-6). Rule a's own placements are untouched; this is the list, not the money.
    between = []
    for e in rem_entries:
        by_memo = defaultdict(list)
        for r in e['rows']:
            by_memo[r['description'].strip()].append(r)
        for _, g in sorted(by_memo.items()):
            amt = defaultdict(Decimal)
            for r in g:
                amt[SCHOOL if e['scope'](r) else r['fund']] += r['amt']
            mv = fund_move(e['fy'], e['journal'], [r for r in g if not e['scope'](r)], amt, True)
            if mv:
                between.append(mv)
    # MOVED BETWEEN FUNDS, NO SCHOOL LINE (28 October 2026). An entry whose expense lines touch
    # no school line, only two or more other funds, one giving cost up and another taking it on.
    # Read the way `entries()` reads rule a: a journal that nets is one entry, else one memo at a
    # time. Before this each half fell through to rules b and c as ordinary spending, so one award
    # of a grant showed negative spending under a function code and the other positive.
    cand = defaultdict(list)
    for r in exp:
        if r['source'] in ('GEN', 'GRV') and id(r) not in done and other_spent(r):
            cand[(r['fy'], r['journal'])].append(r)
    for (fy, j), rs in sorted(cand.items()):
        if len({r['fund'] for r in rs}) < 2:
            continue
        # one memo at a time, as `entries()` reads rule a: what passed between two funds is what
        # one memo moved, never a journal's net across unrelated memos
        by_memo = defaultdict(list)
        for r in rs:
            by_memo[r['description'].strip()].append(r)
        groups = [g for _, g in sorted(by_memo.items())]
        for g in groups:
            fnet = defaultdict(Decimal)
            for r in g:
                fnet[r['fund']] += r['amt']
            fnet = {f: v for f, v in fnet.items() if v}
            if not (any(v < 0 for v in fnet.values()) and any(v > 0 for v in fnet.values())):
                continue
            # a fund whose postings in the entry net to nothing moved nothing between funds; its
            # rows (a reclass inside one fund) go on to rule c like any other
            mine = [r for r in g if r['fund'] in fnet]
            pnet = defaultdict(Decimal)
            for r in mine:
                done.add(id(r))
                src_rows[(fy, r['fund'])].append((r, 'journal', j))
                pnet[payer(A[r['account']])] += r['amt']
            for f, v in fnet.items():
                src[(fy, f)][('between', None)] += v
            for py, v in pnet.items():
                if v:
                    unmatched[(fy, py, 'moved between funds by journal entry')] += v
            between.append(fund_move(fy, j, mine, fnet, False))
    reversals(between)

    # rule c: same function code, on a category; the rest unmatched
    for r in exp:
        if id(r) in done or not other_spent(r):
            continue
        a, f = A[r['account']], J.function(r['account'])
        if is_capital(a):
            unmatched[(r['fy'], payer(a), 'a capital article')] += r['amt']
            src[(r['fy'], r['fund'])][('capital', None)] += r['amt']
            src_rows[(r['fy'], r['fund'])].append((r, 'capital', None))
        elif J.function_class(f) == 'line':
            src[(r['fy'], r['fund'])][('function', cat_of(r['account']))] += r['amt']
            src_rows[(r['fy'], r['fund'])].append((r, 'function', cat_of(r['account'])))
            func_cat[(r['fy'], cat_of(r['account']), payer(a))] += r['amt']
            if r['source'] in PAYMENT:
                payments[(r['fy'], cat_of(r['account']), payer(a))] += 1
            placed_rows[(r['fy'], cat_of(r['account']), payer(a))].append(r)
            func_codes[(r['fy'], cat_of(r['account']), payer(a))].add(f)
        else:
            why = {'heading': 'booked to a heading', 'none': 'booked to no function',
                   'other': 'a function the general fund has no line for'}[J.function_class(f)]
            unmatched[(r['fy'], payer(a), why)] += r['amt']
            src[(r['fy'], r['fund'])][('none', why)] += r['amt']
            src_rows[(r['fy'], r['fund'])].append((r, 'none', why))

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
                         moved_off=p['moved_off'], moved_on=p['moved_on'],
                         payments=payments[(fy, acct)],
                         fund_moves=fund_moves.get((fy, acct), []),
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
                         moved_off=D0, moved_on=D0, fund_moves=[],
                         payments=payments[(fy, cat, py)],
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
    # every fund's spending, read whole, is what the placements above put somewhere
    spent = defaultdict(Decimal)
    for (fy, f), rs_ in src_rows.items():
        spent[(fy, f)] = sum((r['amt'] for r, _, _ in rs_), D0)
    for k in set(spent) | set(src):
        if sum(src[k].values(), D0) != spent[k]:
            fail('FY%d fund %s: its postings come to %s; the placements by source to %s'
                 % (k[0], k[1], spent[k], sum(src[k].values(), D0)))
    return dict(rows=rows, years=years, moves=moves, src={k: dict(v) for k, v in src.items()},
                src_rows=dict(src_rows), placed_rows=dict(placed_rows), prepaid=prepaid, transfers=transfers(),
                fund_moves_between=between,
                tie=tie_special())


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
