#!/usr/bin/env python3
"""SURPLUS IN FOUR PARTS: one fiscal year's school surplus broken into what was voted above
cost, what transfers moved, what other funds paid, and what belonged to another year. One topic
page on the FY2026 closeout shelf, from `fy_breakdown.py`.

    python3 scripts/build_fy_breakdown.py           # write fy28/public/data/topics/fy2026-breakdown.json
    python3 scripts/build_fy_breakdown.py --check   # fail if it would change
    python3 scripts/verify_fy_breakdown.py          # every figure, by a second route

TJ, 26 October 2026: *"there HAS to be a way to see why they had leftover money."* The method,
the match rules and what is ours are in `fy_breakdown.py`'s docstring and are not repeated
here. notes/HANDOFF-FY-BREAKDOWN.md is the brief; this builds its first two parts (the data and
identity, and the alluvial that opens the page). The pool (hub and spoke) and the timeline of
moves are still to build.

THE SIGNATURE is an ALLUVIAL diagram (`fy-alluvial`, a custom block): four years side by side,
each a stack of what the school budget's lines cost from every fund, each block split by who
paid; bands carry each (block, payer) from one year to the next, so a payer change reads as a
band keeping its height and changing colour. A reader can pick one block and see it alone, at
full height -- at the scale of the whole budget a $287,108 grant payment is a hairline.
"""
import argparse
import json
import os
import re
import sys
from datetime import date, timedelta
from collections import defaultdict
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topic_blocks as TB  # noqa: E402
import journal as J  # noqa: E402
import build_school_surplus as S  # noqa: E402
import fy_breakdown as FB  # noqa: E402

ID = 'fy2026-breakdown'
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % ID)
# Every row behind every line, one file a year, fetched when a line is opened (TJ, 27 October
# 2026: "show all the journal entry rows for the line in 'expenses' tab ... what the out of
# district tuition spend was spent on, line by line, and what source paid it").
LINES_DIR = os.path.join(ROOT, 'fy28', 'public', 'data', 'fy-breakdown')
SCHOOL = 'School budget'
Y0, Y1 = 2025, 2026
D0 = Decimal(0)
PRIVATE = '0100-3-300-9300-51-1-06-2-535019'

# Who paid, in six, on the weekly chart: a chart holds five hues and a grey. IDEA is named apart from the other
# grants because it is the grant this question turned on.
PAYERS = [('gf', 'School general fund'), ('idea', 'IDEA grants'), ('grants', 'Other grants'),
          ('cb', 'Circuit breaker'), ('fees', 'Fees, revolving funds and lunch'),
          ('other', 'Capital and other appropriations')]


def payer_group(p):
    if p == 'General fund':
        return 'gf'
    if p.startswith('IDEA'):
        return 'idea'
    if p == 'Circuit breaker':
        return 'cb'
    if p == 'Revolving funds and lunch':
        return 'fees'
    if p in ('Capital and other', 'General fund, outside the school budget'):
        return 'other'
    return 'grants'


def fl(x):
    return float(x)


def U(v):
    return figure(fl(v), C.usd(fl(v)))


def F(y):
    return figure(y, C.fy(y), 'fiscal year')


MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
          'September', 'October', 'November', 'December')


def long_date(iso):
    y, mo, d = iso.split('-')
    return '%d %s %s' % (int(d), MONTHS[int(mo) - 1], y)


class Texts:
    """Every display string a custom block carries, sorted into the two kinds rule 2 knows: a
    FIGURE we formatted from a computed value, and a LITERAL quoted from the record (an account
    name, a memo, a date). `topic_blocks.custom` checks every digit against the two."""
    def __init__(self):
        self.figures, self.literals = set(), set()

    def usd(self, v):
        t = C.usd(fl(v))
        self.figures.add(t)
        return t

    def fy(self, y):
        t = C.fy(y)
        self.figures.add(t)
        return t

    def lit(self, s):
        self.literals.add(s)
        return s


def line_name(r):
    org = r['org'].title()
    d = r['description'].title()
    return d if not org or org.lower() == d.lower() else '%s · %s' % (d, org)


def how_rows(T, how):
    """Who else paid toward a line, and HOW each was matched: the payee, the journal entry, or
    the function code."""
    lab = {'payee': 'paid the same payee', 'moved': 're-charged to it by journal entry',
           'function': 'same kind of work'}
    out = []
    for (rule, py, h), v in sorted(how.items(), key=lambda kv: -abs(kv[1])):
        if round(v) == 0:
            continue
        if rule == 'moved':
            d, memo = h.split(' · ', 1)
            h = '%s, “%s”' % (long_date(d), memo)
        out.append(dict(payer=T.lit(py), rule=lab[rule], how=T.lit(h), text=T.usd(v)))
    return out


def move_rows(T, moves, names):
    out = []
    for mv in sorted(moves, key=lambda x: x['date']):
        others = sorted(mv['others'], key=lambda o: -abs(o['amount']))
        out.append(dict(
            dir='in' if mv['amount'] > 0 else 'out', date=T.lit(long_date(mv['date'])),
            memo=T.lit(mv['memo'] or 'no memo'), text=T.usd(abs(mv['amount'])),
            paired=mv['paired'],
            others=[dict(name=T.lit(names.get(o['account'], o['description'].title())
                                    if o['account'] else o['description']),
                         text=T.usd(abs(o['amount']))) for o in others]))
    return out


def chip_rows(T, r):
    """What sits behind each amount drawn as a chip: the journal entries that moved cost off a
    line or back onto it, and what other funds paid directly, each with who and how much."""
    def entries(sign):
        out = []
        for mv in sorted(r['fund_moves'], key=lambda x: (x['date'], -abs(x['amount']))):
            if (mv['amount'] < 0) != (sign < 0):
                continue
            for py, v in sorted(mv['payers'].items(), key=lambda kv: -kv[1]):
                if round(v) != 0:
                    out.append(dict(title=T.lit(py), text=T.usd(v), sub=T.lit(
                        '%s, “%s”' % (long_date(mv['date']), mv['memo']))))
        return out
    direct = [dict(title=p['payer'], sub='%s: %s' % (p['rule'], p['how']), text=p['text'])
              for p in how_rows(T, {k: v for k, v in r['how'].items() if k[0] != 'moved'})]
    return dict(off=entries(-1), on=entries(1), direct=direct)


def chip_counts(T, r):
    """What each chip's count says (TJ, 27 October 2026, on "3 sources": "'journal entries'?").
    A re-charge is a journal entry, so its chips count entries; money paid from the start is
    invoices and payroll, so that chip counts payments."""
    # Where more than one fund paid, the funds come first: who paid, then how many bills.
    n = lambda k, one, many: '%s %s' % (C.num(k), one if k == 1 else many)
    chips = chip_rows(T, r)
    funds = lambda k: len({i['title'] for i in chips[k]})
    lead = lambda k: n(funds(k), 'fund', 'funds') + ' · ' if funds(k) > 1 else ''
    out = {}
    for k, neg in (('off', True), ('on', False)):
        js = {mv['journal'] for mv in r['fund_moves'] if (mv['amount'] < 0) == neg and mv['amount']}
        if js and chips[k]:
            out[k] = T.lit(lead(k) + n(len(js), 'journal entry', 'journal entries'))
    if r['payments'] and chips['direct']:
        out['direct'] = T.lit(lead('direct') + n(r['payments'], 'payment', 'payments'))
    return out


def lines_data(m, T):
    """Every line, every year, as two sums. The school budget's own, to what was left, with
    cost moved by journal entry shown apart from what it spent; and what the line cost from
    every fund, where a move and a grant paying directly are two different terms. TJ, 26
    October 2026: "money added from other funds REDUCES the general fund... depends how its
    done doesnt it?" It does: a move changes Left, paying directly does not."""
    names = {r['account']: line_name(r) for r in m['rows'] if r['account']}
    years = []
    for fy in J.YEARS:
        rows = []
        for r in m['rows']:
            if r['fy'] != fy:
                continue
            budget = r['voted'] + r['transfers'] + r['carried_budget']
            before = r['gf_spent'] + r['moved_off'] - r['moved_on']
            direct = r['other_funds'] - r['by_rule'].get('moved', D0)
            if r['account'] and sum((mv['amount'] for mv in r['moves_in']), D0) != r['transfers']:
                raise SystemExit('build_fy_breakdown: FY%d %s: its listed transfers do not sum to '
                                 'its moved in or out' % (fy, r['account']))
            if r['account'] and budget - before + r['moved_off'] - r['moved_on'] != r['left']:
                raise SystemExit('build_fy_breakdown: FY%d %s does not read budget - spent before '
                                 'moves + moved off - moved on = left' % (fy, r['account']))
            if r['by_rule'].get('moved', D0) != r['moved_off']:
                raise SystemExit('build_fy_breakdown: FY%d %s: the cost moved off it is not what '
                                 'the other funds carry for it' % (fy, r['account']))
            nums = dict(voted=r['voted'], transfers=r['transfers'], carried=r['carried_budget'],
                        budget=budget, before=before, off=r['moved_off'], on=r['moved_on'],
                        left=r['left'], spent=r['gf_spent'], direct=direct,
                        total=r['gf_spent'] + r['other_funds'])
            if all(round(v) == 0 for v in nums.values()):
                continue        # an account with nothing voted, spent or placed on it
            row = dict(
                name=T.lit(line_name(r)) if r['account'] else 'Same kind of work, other funds',
                account=T.lit(r['account']) if r['account'] else '',
                key=T.lit(line_key(r)),
                cat=S.CAT_LABEL[r['category']], line=bool(r['account']),
                n={k: round(fl(v), 2) for k, v in nums.items()},
                t={k: T.usd(v) for k, v in nums.items()},
                chips=chip_rows(T, r),
                # under each chip, how many entries its hover lists (TJ: "a small text count of
                # the sources like '3 sources'")
                chip_n=chip_counts(T, r),
                payers=how_rows(T, r['how']),
                moves=move_rows(T, r['moves_in'], names))
            if round(r['other_year_spent']):
                row['spent_note'] = 'of which %s paid for another year' % T.usd(r['other_year_spent'])
            rows.append(row)
        un = sorted(m['years'][fy]['unmatched'].items(), key=lambda kv: -kv[1])
        years.append(dict(fy=T.fy(fy), rows=rows,
                          unmatched=[dict(payer=T.lit(py), why=why, text=T.usd(v))
                                     for (py, why), v in un if round(v) != 0],
                          unmatched_total=T.usd(sum((v for _, v in un), D0))))
    # What each column means, on hover (TJ, 26 October 2026: "can you put those definitions in a
    # hover tooltip on the column"). A transfer moves BUDGET; a move re-books SPENDING.
    means = dict(
        voted='What Town Meeting voted for this line.',
        transfers='Budget shifted to or from other lines during the year. Only the permission to '
                  'spend moves; no bills do.',
        carried='Orders from last year that were still unpaid, carried in along with the money to '
                'pay them.',
        budget='What this line was allowed to spend: voted, plus transfers, plus carried.',
        before='What the school budget spent on this line, before any bills were re-charged. '
               'Bills still owed at year end count.',
        off='The school budget paid these bills first. Later another fund paid it back the '
            'same amount. So the school budget spent less, and Left goes up.',
        on='Another fund paid these bills first. Later the school budget paid it back. So the '
           'school budget spent more, and Left goes down.',
        left='What this line had left at year end. Above zero, it added to the surplus; below '
             'zero, other lines covered it.',
        spent='What the school budget spent on this line, after the re-charges.',
        off_cost='The same bills as Re-charged to other funds: the school budget paid first, '
                 'and another fund paid it back. They still count here, because they are still '
                 'part of what this line cost.',
        direct='Another fund paid these bills itself; the school budget never did, so Left does '
               'not change. Which bills count toward this line is our match, by payee or by kind '
               'of work.',
        total='Everything this line cost, whoever paid.')
    col = lambda id_, key, label, op, group: dict(id=id_, key=key, label=label, op=op, group=group,
                                                  means=means[id_])
    return dict(years=years, cats=sorted({S.CAT_LABEL[c[0]] for c in S.CATEGORIES}),
                # TWO SUMS, side by side. A re-charge to another fund is in both: it leaves the
                # school budget's sum (raising Left) and stays in what the line cost. TJ, on
                # "moved to": it read as money going INTO the fund, when the BILL went to it.
                groups=[dict(id='budget', label='The school budget'),
                        dict(id='cost', label='What the line cost, every fund')],
                columns=[col('voted', 'voted', 'Voted', '', 'budget'),
                         col('transfers', 'transfers', 'Transfers in or out', '+', 'budget'),
                         col('carried', 'carried', 'Carried from last year', '+', 'budget'),
                         col('budget', 'budget', 'Budget', '=', 'budget'),
                         col('before', 'before', 'Spent before re-charges', '−', 'budget'),
                         col('off', 'off', 'Re-charged to other funds', '+', 'budget'),
                         col('on', 'on', 'Re-charged from other funds', '−', 'budget'),
                         col('left', 'left', 'Left', '=', 'budget'),
                         col('spent', 'spent', 'Spent by the school budget', '', 'cost'),
                         col('off_cost', 'off', 'Paid by other funds, re-charged later', '+', 'cost'),
                         col('direct', 'direct', 'Paid by other funds, from the start', '+', 'cost'),
                         col('total', 'total', 'Total spent, all funds', '=', 'cost')],
                text=dict(
                    read='Other funds can pay a line’s bills in two ways, and only one of them '
                         'changes Left. The school budget can pay first and a journal entry RE-CHARGE '
                         'the bills to a grant or another fund later: the school budget’s spending '
                         'falls and Left rises, and the line cost the same. Or the other fund can '
                         'pay FROM THE START: Left is untouched, and the line cost more than the '
                         'school budget shows. Hover or tap a circled amount to see each entry.',
                    other_funds='Other funds: grants, the circuit breaker, fees and revolving '
                                'funds, and capital articles. Re-charges are the Town’s own entries; '
                                'which spending counts as paid from the start toward a line is our '
                                'match, by payee or by kind of work.',
                    chip_off='Re-charged from this line to', chip_on='Re-charged to this line from',
                    chip_direct='Paid by other funds, from the start',
                    cost_sum='What the line cost, every fund',
                    all_cats='Every category', show='Show every line', fewer='Show only both ends',
                    between='the lines in between: show every line',
                    sum='The sum', moves='Transfers in or out', nomoves='No budget transferred.',
                    shared='Many lines gave and many got in this one entry, and the books do not '
                           'say which line’s money went to which. The other side, all together:',
                    into='from', outof='to', in_='In', out='Out',
                    tab_summary='Summary', tab_expenses='Expenses', tab_analysis='Analysis',
                    close='Close',
                    an_payee='By payee', an_memo='By memo', an_week='By week',
                    an_note='Bars are what each payee or memo was paid this year, split by the fund '
                            'that paid. Re-charges are left out: they move bills between funds and '
                            'pay nobody.',
                    an_week_note='Each bar is one week, Monday to Sunday, everything paid or still '
                                 'owed that week, by fund. A bar below the line is a week bills were '
                                 're-charged off the school budget. The shaded span is the fiscal '
                                 'year; anything to its left was posted before it began.',
                    an_recharge='Re-charged off the school budget',
                    who_paid='Who paid', every_row='Every row', by_payee='By payee',
                    every_fund='Every fund', loading='Loading every row…',
                    failed='The rows could not be loaded.', recharges='Re-charges',
                    no_recharges='No bills re-charged to or from another fund.',
                    ex_date='Date', ex_kind='What', ex_payee='Payee', ex_memo='Memo',
                    ex_ref='Reference', ex_fund='Paid by', ex_amount='Amount', ex_rows='rows',
                    ex_note='One row per invoice, payroll warrant or journal entry. A purchase '
                            'order shows only what it still owed at year end; one fully paid '
                            'shows as its invoices. Payroll rows are whole pay runs, with no '
                            'names. A bill re-charged to another fund is listed twice: taken '
                            'off the school budget, and under the fund that paid it.',
                    payers='Other funds that paid toward this line',
                    none='No other fund paid toward this line.',
                    unmatched='Other funds’ spending not matched to any line',
                    lines='Line', category='Category', footing='Spent counts orders still owed at year end, so for '
                    'FY2025 and earlier Left can differ from the Town’s printed report by '
                    'those orders.'))


KINDS = [('payroll', 'Payroll'), ('invoice', 'Invoices'), ('order', 'Orders still owed at year end'),
         ('journal', 'Journal entries'), ('receipt', 'Receipts and refunds')]


def kind_group(k):
    if k == 'Payroll':
        return 'payroll'
    if k.startswith('Invoice'):
        return 'invoice'
    if k.startswith('Order'):
        return 'order'
    if k == 'Receipt':
        return 'receipt'
    return 'journal'


def year_weeks(m, T):
    """THE WHOLE YEAR, BY WEEK (TJ, 27 October 2026: "the SAME chart, but across the whole year,
    across every spend, for every line"). Every row of every line, summed Monday to Sunday:
    by who paid (the alluvial's six payer groups) or by kind of posting; bills re-charged off
    the school budget below the line, their mirror under the receiving fund not counted twice.
    Each week keeps its largest entries, so a spike can be read where it is."""
    names = {line_key(r): (line_name(r) if r['account'] else 'Same kind of work, other funds')
             for r in m['rows']}
    monday = lambda d: d - timedelta(days=d.weekday())
    years = []
    for fy, lines in sorted(line_files(m).items()):
        byf = defaultdict(lambda: defaultdict(Decimal))
        byk = defaultdict(lambda: defaultdict(Decimal))
        rc, rb = defaultdict(Decimal), defaultdict(Decimal)   # re-charged off, and back on
        top = defaultdict(list)
        for key, rs in lines.items():
            for x in rs:
                if not x['d']:
                    continue
                w = monday(date.fromisoformat(x['d']))
                if x['k'].startswith(RECHARGE):
                    if x['f'] == SCHOOL:
                        (rc if x['v'] < 0 else rb)[w] += x['v']
                        top[w].append((key, x))
                    continue
                byf[w][payer_group('General fund' if x['f'] == SCHOOL else x['f'])] += x['v']
                byk[w][kind_group(x['k'])] += x['v']
                top[w].append((key, x))
        weeks = []
        for w in sorted(set(byf) | set(rc) | set(rb)):
            spend = sum(byf[w].values(), D0)
            big = sorted(top[w], key=lambda kx: -abs(kx[1]['v']))[:6]
            weeks.append(dict(
                w=T.lit(w.isoformat()), label=T.lit('Week of %s' % long_date(w.isoformat())),
                f=[[g, round(fl(v), 2)] for g, v in sorted(byf[w].items()) if v],
                k=[[g, round(fl(v), 2)] for g, v in sorted(byk[w].items()) if v],
                rc=round(fl(rc[w]), 2), rb=round(fl(rb[w]), 2), t=T.usd(spend),
                t_rc=T.usd(-rc[w]) if rc[w] else '', t_rb=T.usd(rb[w]) if rb[w] else '',
                top=[dict(line=T.lit(names[key]), what=T.lit(x['k']), payee=T.lit(x['p']),
                          fund=T.lit(x['f']), text=T.usd(x['v'])) for key, x in big]))
        tot = sum((sum(v.values(), D0) for v in byf.values()), D0)
        years.append(dict(fy=T.fy(fy), a0=T.lit(monday(date(fy - 1, 7, 1)).isoformat()),
                          a1=T.lit(date(fy, 6, 30).isoformat()), weeks=weeks, total=T.usd(tot),
                          recharged=T.usd(-sum(rc.values(), D0)) if rc else '',
                          back=T.usd(sum(rb.values(), D0)) if rb else ''))
    return dict(years=years, payers=[dict(id=p, label=l) for p, l in PAYERS],
                kinds=[dict(id=k, label=l) for k, l in KINDS],
                text=dict(by_fund='By who paid', by_kind='By kind', clear='Clear', recharge='Re-charged off the '
                          'school budget', back='Re-charged back onto it',
                          spent='spent or owed, every line', recharged='re-charged off the school '
                          'budget', back_total='re-charged back onto it',
                          biggest='Largest entries that week',
                          pick='Hover or tap a week for its largest entries; tap again, or press Escape, to clear.',
                          note='Every row of every school line and what other funds paid toward '
                               'them, summed Monday to Sunday: payroll runs, invoices, orders '
                               'still owed at year end and journal entries. Grey below the line '
                               'is bills re-charged off the school budget to another fund; grey '
                               'above a bar, bills re-charged back onto it. '
                               'Other funds’ spending our matching places on no line is not '
                               'here.'))


def page(m):
    y0, y1 = m['years'][Y0], m['years'][Y1]
    t0, t1 = y0['terms'], y1['terms']
    rows = {(r['fy'], r['account']): r for r in m['rows'] if r['account']}
    priv = rows[(Y1, PRIVATE)]
    idea_tuition = sum((v for (rl, py), v in priv['payers'].items() if py.startswith('IDEA')), D0)
    if priv['other_funds'] != idea_tuition:
        raise SystemExit('build_fy_breakdown: the page says the IDEA grant is all of private '
                         'tuition’s other-fund money in FY%d' % Y1)
    # Journal moves, measured on the school budget's side: cost taken off its lines, less cost
    # moved back on.
    net = lambda y: sum((mv['off'] - mv['onto'] for mv in m['moves'] if mv['fy'] == y), D0)
    mv0, mv1 = net(Y0), net(Y1)
    moves = [mv for mv in m['moves'] if mv['fy'] == Y1]
    idea_back = -sum((v for mv in moves for p, v in mv['by_payer'].items() if p.startswith('IDEA')), D0)
    if not (idea_back > 0 and {mv['date'][5:7] for mv in moves} == {'06'} and mv0 < 0 < mv1):
        raise SystemExit('build_fy_breakdown: the page says June %d entries moved IDEA pay onto '
                         'the general fund, and moves ran onto it in FY%d and off it in FY%d'
                         % (Y1, Y0, Y1))
    um1 = sum(y1['unmatched'].values(), D0)
    more = t1['other_funds'] - t0['other_funds']
    without = y1['left'] + y1['prepaid']
    f = LD.fact

    def con(text, rests, figs, so):
        return TP.conclusion(text, rests, figs, so=so[0], so_figures=so[1], so_allow=so[2])
    facts = [
        f('left', U(y1['left']), 'left on the school lines, orders owed counted', 'published'),
        f('above', U(t1['voted_above_cost']), 'voted above what the lines cost, all funds',
          'estimate'),
        f('other', U(t1['other_funds']), 'paid by other funds toward those lines', 'estimate'),
        f('transfers', U(t1['transfers']), 'budget moved in by transfer, net', 'published'),
        f('another', U(t1['another_year']), 'another year’s money, net', 'published'),
        f('prepaid', U(y1['prepaid']), 'next year’s tuition, paid this year', 'published'),
        f('carried', U(y1['carried_unpaid']), 'last year’s orders, carried in and not paid',
          'published'),
        f('moved1', U(mv1), 'cost taken off the general fund by journal entry, net',
          'published'),
        f('moved0', U(mv0), 'the same, the year before', 'published'),
        f('ideaback', U(idea_back), 'IDEA grant pay moved onto the general fund, June',
          'published'),
        f('idea', U(idea_tuition), 'IDEA grant paid toward private tuition', 'estimate'),
        f('unmatched', U(um1), 'other funds’ spending no rule places on a line', 'estimate'),
    ]
    conclusions = [
        con('Other funds paid %s toward %s’s lines; the vote alone was %s below what they cost.'
            % (C.usd(fl(t1['other_funds'])), C.fy(Y1), C.usd(fl(-t1['voted_above_cost']))),
            ['other', 'above', 'left'],
            {'a': U(t1['other_funds']), 'y': F(Y1), 'b': U(-t1['voted_above_cost'])},
            so=('A line is what is left after other funds pay, so it can end under with nothing '
                'costing less. They paid %s more than in %s.'
                % (C.usd(fl(more)), C.fy(Y0)),
                {'m': U(more), 'y': F(Y0)}, ())),
        con('The IDEA grant paid %s of private tuition; June entries moved %s of its pay onto '
            'the general fund.' % (C.usd(fl(idea_tuition)), C.usd(fl(idea_back))),
            ['idea', 'ideaback'], {'a': U(idea_tuition), 'b': U(idea_back)},
            so=('One grant changed payer both ways in one year; the voted budget shows neither. '
                'Why it paid the placement is in no document held.',
                None, ())),
        con('Journal entries took a net %s off the general fund in %s, after adding %s in %s.'
            % (C.usd(fl(mv1)), C.fy(Y1), C.usd(fl(-mv0)), C.fy(Y0)), ['moved1', 'moved0'],
            {'a': U(mv1), 'y': F(Y1), 'b': U(-mv0), 'z': F(Y0)},
            so=('A swing of %s between two years, made by entries after the spending. Each is '
                'in the journal with its date and memo.' % C.usd(fl(mv1 - mv0)),
                {'s': U(mv1 - mv0)}, ())),
        con('%s paid %s of %s tuition; %s of %s’s orders were carried in and never paid.'
            % (C.fy(Y1), C.usd(fl(y1['prepaid'])), C.fy(Y1 + 1), C.usd(fl(y1['carried_unpaid'])),
               C.fy(Y0)), ['prepaid', 'carried', 'another'],
            {'y': F(Y1), 'a': U(y1['prepaid']), 'z': F(Y1 + 1), 'b': U(y1['carried_unpaid']),
             'x': F(Y0)},
            so=('Without the early payment %s would have left %s, more than %s on the same '
                'footing.' % (C.fy(Y1), C.usd(fl(without)), C.fy(Y0)),
                {'y': F(Y1), 'w': U(without), 'z': F(Y0)}, ())),
    ]
    T = Texts()
    lines = lines_data(m, T)
    weeks = year_weeks(m, T)
    if {mv['date'][5:7] for mv in m['moves'] if mv['fy'] == Y1} != {'06'}:
        fail('the weekly chart says every %d re-charge was in June' % Y1)
    return TP.page(
        ID,
        '%s’s lines left %s; other funds paid %s of their cost, %s more than in %s.'
        % (C.fy(Y1), C.usd(fl(y1['left'])), C.usd(fl(t1['other_funds'])), C.usd(fl(more)),
           C.fy(Y0)),
        facts, conclusions,
        chart=TP.series(
            'What the school lines left, by year', [C.fy(y) for y in J.YEARS],
            [TP.track('Left, orders still owed counted', [fl(m['years'][y]['left']) for y in J.YEARS],
                      'published', 'bar')], '$', kind='bar',
            note='School general fund, department 300. Every line’s Left in the table above, '
                 'summed.', note_allow=('300',)),
        blocks=[
            TB.custom('fy-year-weeks', 'Every week of the year', weeks, place='top',
                      figures=sorted(T.figures), allow=sorted(T.literals),
                      basis=('record', 'Every posting on the school lines, by week'),
                      alt='Bar chart, one fiscal year at a time: every week from July to June, '
                          'what every school line spent or still owed that week, stacked by who '
                          'paid or by kind of posting, with bills re-charged to other funds below '
                          'the line',
                      so=('In %s every bill re-charged off the school budget was re-charged in '
                          'June.' % C.fy(Y1), {'y': F(Y1)}, ())),
            TB.custom('fy-line-table', 'Every line, budget and cost', lines, place='top',
                      figures=sorted(T.figures), allow=sorted(T.literals),
                      basis=('reading', 'Our placing of other funds’ spending on the lines'),
                      alt='Table of every school general fund line, one fiscal year at a time, '
                          'as two sums: the school budget to what was left, with cost moved to '
                          'other funds by journal entry apart from what it spent; and what the '
                          'line cost from every fund. Sortable by category and by every column',
                      so=('A line can end under because its bills were re-charged to another '
                          'fund after the school budget paid them. Sorted by category, lines '
                          'that cancel each other out sit side by side.', None, ())),
        ],
        sources=[
            dict(label='Lunenburg Budget Project — munis-school-journal.csv (every school '
                       'journal line, every fund, FY2023–FY2026, our redacted reading of the '
                       'Town’s Report 1)', href=J.PUBLIC['journal']),
            dict(label='Lunenburg Budget Project — munis-school-journal-accounts.csv',
                 href=J.PUBLIC['accounts']),
            dict(label='Town of Lunenburg — school general fund period-13 reports, FY2023–FY2026 '
                       '(each line tied to the cent)',
                 href='/docs/town-ledgers/expenses/glytdbud-expense-fy2026-p13-gf-school.xlsx'),
            dict(label='Town of Lunenburg — school special funds period-13 reports (every fund '
                       'they print tied to the cent)',
                 href='/docs/town-ledgers/expenses/glytdbud-expense-fy2026-p13-special-school.xlsx'),
            dict(label='Town of Lunenburg — how the journal reached us, and what was redacted',
                 href='/docs/town-ledgers/account-details/'
                      'PROVENANCE-fy2023-fy2026-p13-school-journal.md')],
        finding_figures={'y': F(Y1), 'l': U(y1['left']), 'o': U(t1['other_funds']),
                         'm': U(more), 'z': F(Y0)},
        # HIDDEN, NOT RELEASED (TJ, 26 October 2026: "put this page into a hidden section where
        # we wont release it"). Built as a draft: outside the shelf registry, so it is on no
        # shelf, in no topics.json, not in the sitemap and not prerendered. The address still
        # opens for anybody given it.
        draft=dict(title='Surplus in four parts', home='fy2026-closeout'))


def line_key(r):
    """The key a line's rows are filed under: its account, or for a same-kind-of-work row its
    category and payer."""
    return r['account'] or 'kind|%s|%s' % (r['category'], next(iter(r['payers']))[1])


def money(v):
    return ('-$%s' if v < 0 else '$%s') % format(abs(v).quantize(Decimal('0.01')), ',.2f')


def payee(r):
    """The payee as our redacted journal prints it; a name our redaction masked (a family, under
    the recipients-not-providers rule) says so rather than reading as no payee."""
    v = r['vendor'].strip()
    if not v and 'vendor' in r['masked']:
        return 'Name withheld (redacted)'
    return v


KIND = {'API': 'Invoice', 'APM': 'Invoice', 'PRJ': 'Payroll', 'PRH': 'Payroll',
        'GEN': 'Journal entry', 'GRV': 'Journal entry', 'CRP': 'Receipt'}
ORDERS = ('POE', 'POL', 'POM', 'SOY', 'GEL')


def expense_rows(rows, paid_by, recharge=None, carried=frozenset()):
    """One fund's postings on one line, as a reader would list them: payments and journal
    entries one by one; a purchase order's postings netted into one row -- what it still owed at
    year end -- and left out where it nets to nothing; a re-charge entry as one row naming the
    fund on the other side. `recharge`: journal -> (verb, funds)."""
    out, orders = [], defaultdict(list)
    for r in rows:
        if r['source'] in ORDERS:
            orders[r['doc_no']].append(r)
            continue
        if recharge and r['journal'] in recharge:
            continue
        kind = KIND[r['source']]
        if FB.is_prepaid(r):
            kind = 'Invoice, next year’s tuition paid early'
        out.append(dict(d=r['effective_date'], k=kind, p=payee(r),
                        m=r['description'].strip(), n=r['doc_no'].strip(), f=paid_by, v=r['amt']))
    for doc, rs in orders.items():
        v = sum((r['amt'] for r in rs), D0)
        if v == 0:
            continue
        last = max(rs, key=lambda r: r['effective_date'])
        out.append(dict(d=last['effective_date'],
                        k='Order carried from last year, still owed' if doc in carried
                        else 'Order, still owed at year end',
                        p=payee(last), m=last['description'].strip(), n=doc, f=paid_by, v=v))
    for j, (verb, funds, v, d, memo) in (recharge or {}).items():
        out.append(dict(d=d, k='%s %s' % (verb, funds), p='', m=memo, n=j, f=paid_by, v=v))
    return out


def line_files(m):
    """{fy: {key: [rows]}}, each line's rows summing to what its sums say: the school budget's
    to what it spent, the other funds' to what they paid toward it."""
    A = J.accounts()
    by_line = defaultdict(list)
    for r in J.lines():
        a = A[r['account']]
        if (J.is_expense(a) and J.in_surplus_scope(a) and r['source'] not in ('BUC', 'BUA', 'YEC')):
            by_line[(r['fy'], r['account'])].append(r)
    out = defaultdict(dict)
    for r in m['rows']:
        fy, key = r['fy'], line_key(r)
        rows = []
        if r['account']:
            mine = by_line.get((fy, r['account']), [])
            recharge = {}
            for mv in r['fund_moves']:
                funds = ', '.join(sorted(p for p, v in mv['payers'].items() if round(v)))
                verb = 'Re-charged to' if mv['amount'] < 0 else 'Re-charged from'
                recharge[mv['journal']] = (verb, funds, mv['amount'], mv['date'], mv['memo'])
            carried = {x['doc_no'] for x in mine if x['source'] == 'SOY'}
            rows = expense_rows(mine, SCHOOL, recharge, carried)
            if sum((x['v'] for x in rows), D0) != r['gf_spent']:
                fail('FY%d %s: its rows do not sum to what the school budget spent' % (fy, key))
            if r['fund_moves'] and not recharge:
                fail('FY%d %s: a re-charge with no entry' % (fy, key))
            # a re-charge to another fund is that fund's money too: listed under it as well
            for mv in r['fund_moves']:
                if mv['amount'] < 0:
                    for py, v in mv['payers'].items():
                        rows.append(dict(d=mv['date'], k='Re-charged from the school budget', p='',
                                         m=mv['memo'], n=mv['journal'], f=py, v=v))
            placed = m['placed_rows'].get((fy, r['account']), [])
            for py in sorted({FB.payer(A[x['account']]) for x in placed}):
                rows += expense_rows([x for x in placed if FB.payer(A[x['account']]) == py], py)
            for (rule, py, h), v in r['how'].items():
                if rule == 'payee' and v < 0 and h.startswith('less bills'):
                    rows.append(dict(d='', k='Re-charged back to the school budget', p='', m='',
                                     n='', f=py, v=v))
        else:
            py = next(iter(r['payers']))[1]
            rows = expense_rows(m['placed_rows'].get((fy, r['category'], py), []), py)
        other = sum((x['v'] for x in rows if x['f'] != SCHOOL), D0)
        if other != r['other_funds']:
            fail('FY%d %s: the other funds’ rows %s do not sum to what they paid, %s'
                 % (fy, key, other, r['other_funds']))
        if rows:
            out[fy][key] = rows
    return out


RECHARGE = 'Re-charged'
TOP = 12                       # payees and memos charted by name; the rest summed into one bar


def memo_key(m_):
    """A memo, for grouping: case and spacing folded, a trailing year or number dropped, since
    MUNIS appends the fiscal year to an order's lines ('DIBELS 8TH EDITION        2026')."""
    return re.sub(r'\s*\d{2,4}$', '', ' '.join(m_.upper().split())).strip()


def analysis(fy, rs, fi):
    """The Analysis tab, for one line: spending by payee and by memo, each split by the fund that
    paid, and by week from the line's first posting to 30 June. A re-charge moves bills between
    funds and pays nobody, so it is left out of the payee and memo bars and drawn on the weekly
    chart apart, below the line (its mirror under the receiving fund is not drawn twice)."""
    spend = [x for x in rs if not x['k'].startswith(RECHARGE)]
    def bars(label):
        tot = defaultdict(lambda: defaultdict(Decimal))
        cnt = defaultdict(int)
        for x in spend:
            k = label(x)
            if k:
                tot[k][x['f']] += x['v']
                cnt[k] += 1
        order = sorted(tot, key=lambda k: -sum(tot[k].values()))
        top, rest = order[:TOP], order[TOP:]
        rows_text = lambda n: '%s %s' % (C.num(n), 'row' if n == 1 else 'rows')
        out = [[k, rows_text(cnt[k]), [[fi[f], round(fl(v), 2)] for f, v in sorted(tot[k].items())],
                money(sum(tot[k].values(), D0))] for k in top]
        if rest:
            agg = defaultdict(Decimal)
            for k in rest:
                for f, v in tot[k].items():
                    agg[f] += v
            out.append(['%s more' % C.num(len(rest)), rows_text(sum(cnt[k] for k in rest)),
                        [[fi[f], round(fl(v), 2)] for f, v in sorted(agg.items())],
                        money(sum(agg.values(), D0))])
        return out, cnt
    payees, _ = bars(lambda x: x['p'] or x['k'])
    memos, mc = bars(lambda x: memo_key(x['m']))
    # memos are charted only where they group: at least two memos shared by two rows or more
    if sum(1 for n in mc.values() if n >= 2) < 2:
        memos = []
    # by week, Monday to Sunday, from the line's first posting (orders can open before July)
    start = date(fy - 1, 7, 1)
    first = min([date.fromisoformat(x['d']) for x in rs if x['d']] + [start])
    monday = lambda d: d - timedelta(days=d.weekday())
    wk = defaultdict(lambda: defaultdict(Decimal))
    for x in rs:
        if not x['d']:
            continue
        if x['k'].startswith(RECHARGE):
            if x['f'] != SCHOOL:
                continue                       # the mirror of the school budget's own row
            wk[monday(date.fromisoformat(x['d']))][-1] += x['v']
        else:
            wk[monday(date.fromisoformat(x['d']))][fi[x['f']]] += x['v']
    weeks = [[w.isoformat(), 'Week of %s' % long_date(w.isoformat()),
              [[f, round(fl(v), 2)] for f, v in sorted(vs.items()) if v],
              money(sum((v for f, v in vs.items() if f >= 0), D0)),
              money(vs.get(-1, D0)) if vs.get(-1) else '']
             for w, vs in sorted(wk.items()) if any(vs.values())]
    return dict(ap=payees, am=memos, aw=weeks, a0=monday(first).isoformat(),
                a1=date(fy, 6, 30).isoformat())


def line_texts(m):
    """The files, compact. Funds and kinds are indexed. Per line: `r`, each row [iso date, date,
    kind, payee, memo, reference, fund, amount as text, amount]; `t`, what each fund paid in
    all, [fund, text, amount]; `g`, by payee and fund, [payee, fund, rows, text, amount]."""
    files = {}
    for fy, lines in sorted(line_files(m).items()):
        funds = sorted({x['f'] for rs in lines.values() for x in rs}, key=lambda f: (f != SCHOOL, f))
        kinds = sorted({x['k'] for rs in lines.values() for x in rs})
        fi, ki = {f: i for i, f in enumerate(funds)}, {k: i for i, k in enumerate(kinds)}
        body = {}
        for key, rs in sorted(lines.items()):
            tot, grp, cnt = defaultdict(Decimal), defaultdict(Decimal), defaultdict(int)
            for x in rs:
                tot[x['f']] += x['v']
                g = (x['p'] or x['k'], x['f'])
                grp[g] += x['v']
                cnt[g] += 1
            body[key] = dict(analysis(fy, rs, fi),
                r=[[x['d'], long_date(x['d']) if x['d'] else '', ki[x['k']], x['p'], x['m'], x['n'],
                    fi[x['f']], money(x['v']), round(fl(x['v']), 2)]
                   for x in sorted(rs, key=lambda x: (x['d'] or '9', -abs(x['v'])))],
                t=[[fi[f], money(v), round(fl(v), 2)] for f, v in
                   sorted(tot.items(), key=lambda kv: (kv[0] != SCHOOL, -abs(kv[1])))],
                g=[[p_, fi[f], cnt[(p_, f)], money(v), round(fl(v), 2)] for (p_, f), v in
                   sorted(grp.items(), key=lambda kv: -abs(kv[1]))])
        files[os.path.join(LINES_DIR, 'lines-%d.json' % fy)] = json.dumps(
            dict(fy=C.fy(fy), funds=funds, kinds=kinds, lines=body), ensure_ascii=False,
            sort_keys=True, separators=(',', ':')) + '\n'
    return files


def fail(msg):
    raise SystemExit('build_fy_breakdown: ' + msg)


def render(m=None):
    p = page(m or FB.model())
    p['not_established'] = [
        'Whether any other-fund payment replaced general fund spending or added to it: the books '
        'record who paid, not what would have happened otherwise.',
        'Which line a function-code match belongs to: it is placed on a category only.',
        'What the unmatched spending paid for, beyond its fund and function code.',
        'Spending outside the school’s ledger: benefits charged on the town side, student '
        'activity accounts.',
    ]
    # Compact, unlike the other topic payloads: every line carries its transfers' other sides,
    # and indentation alone was most of two megabytes.
    return json.dumps(p, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    m = FB.model()
    outs = {OUT: render(m), **line_texts(m)}
    if a.check:
        stale = [os.path.relpath(p, ROOT) for p, text in outs.items()
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != text]
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('fy breakdown: current')
        return 0
    os.makedirs(LINES_DIR, exist_ok=True)
    for p, text in outs.items():
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        os.replace(tmp, p)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
