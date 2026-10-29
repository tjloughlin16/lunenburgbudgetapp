#!/usr/bin/env python3
"""SURPLUS IN FOUR PARTS: one fiscal year's school surplus broken into what was voted above
cost, what transfers moved, what other funds paid, and what belonged to another year. One topic
page on the FY2026 closeout shelf, from `fy_breakdown.py`.

    python3 scripts/build_fy_breakdown.py           # write fy28/public/data/topics/fy-breakdown.json
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
import csv
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
import fy_payees as PY  # noqa: E402
import fy_salaries as SAL  # noqa: E402
import fy_web as WEB  # noqa: E402
import fy_items as ITEMS  # noqa: E402

ID = 'fy-breakdown'
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % ID)
# Every row behind every line, one file a year, fetched when a line is opened (TJ, 27 October
# 2026: "show all the journal entry rows for the line in 'expenses' tab ... what the out of
# district tuition spend was spent on, line by line, and what source paid it").
LINES_DIR = os.path.join(ROOT, 'fy28', 'public', 'data', 'fy-breakdown')
SCHOOL = 'School budget'
D0 = Decimal(0)

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
    lab = {'payee': 'paid the same vendor', 'moved': 're-charged to it by journal entry',
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


def school_entries():
    """(fy, journal) -> the school lines' postings in every journal entry (GEN/GRV), for the
    entries that re-book spending between school lines rather than to another fund."""
    A = J.accounts()
    out = defaultdict(list)
    for r in J.lines():
        if r['source'] in ('GEN', 'GRV') and J.is_expense(A[r['account']]):
            out[(r['fy'], r['journal'])].append(r)
    return out


def is_recharge(x, rech):
    """A posting that belongs to one of a line's re-charges, `rech` a set of (journal, part):
    the whole entry (part None), one memo of a journal that held others, or a tuple of memos --
    the halves of one correction keyed under different memos (fy_breakdown.entries)."""
    memo = x['description'].strip()
    return ((x['journal'], None) in rech or (x['journal'], memo) in rech
            or any(j == x['journal'] and isinstance(p, tuple) and memo in p for j, p in rech))


def entry_rows(T, r, entries, names):
    """A line's journal entries that are not re-charges to or from another fund: spending
    re-booked between school lines, a correction, an accrual. Each: date, memo, what this line
    gained or lost, and the other school lines in the entry -- or that the other side is
    outside the school's books."""
    if not r['account']:
        return []
    rech = {(mv['journal'], mv['part']) for mv in r['fund_moves']}
    A = J.accounts()
    out = []
    mine, kept = defaultdict(Decimal), {}
    for (fy, j), rs in entries.items():
        if fy != r['fy'] or (j, None) in rech:
            continue
        # a batch: only the memos that were a re-charge leave; the rest of it is still an entry
        rs = [x for x in rs if not is_recharge(x, rech)]
        v = sum((x['amt'] for x in rs if x['account'] == r['account']), D0)
        if v:
            mine[j], kept[j] = v, rs
    for j, v in sorted(mine.items(), key=lambda kv: min(x['effective_date'] for x in kept[kv[0]])):
        rs = kept[j]
        others = defaultdict(Decimal)
        for x in rs:
            if x['account'] != r['account'] and J.in_surplus_scope(A[x['account']]):
                others[x['account']] += x['amt']
        funds = defaultdict(Decimal)
        for x in rs:
            if not J.in_surplus_scope(A[x['account']]):
                funds[FB.payer(A[x['account']])] += x['amt']
        missing = -sum((x['amt'] for x in rs), D0)        # what the school's journal lacks
        side = [dict(name=T.lit(names.get(a, A[a]['account_description'].strip().title())),
                     text=T.usd(abs(w))) for a, w in sorted(others.items(), key=lambda kv: -abs(kv[1])) if w][:6]
        side += [dict(name=T.lit(f), text=T.usd(abs(w))) for f, w in funds.items() if w]
        if missing:
            # the entry does not balance inside the school's journal: its other side is posted
            # somewhere this journal does not hold
            side.append(dict(name='the Town’s books, outside the school’s journal',
                             text=T.usd(abs(missing))))
        out.append(dict(date=T.lit(long_date(min(x['effective_date'] for x in rs))),
                        memo=T.lit(sorted({x['description'].strip() for x in rs if x['account'] == r['account']})[0] or 'no memo'),
                        journal=T.lit(j), dir='in' if v > 0 else 'out', text=T.usd(abs(v)), others=side))
    return out


# THE BUDGET WALK, original to final (TJ, 27 October 2026: "whats the best idea of how to reconcile
# the 'initial' budget plus the adjusted budget?" -- then "Flagging which lines were most adjusted
# from the initial budget to the final budget"). The shape governments report a budget in -- the
# budgetary comparison schedule, original then final then actual (GASB 34) -- line by line: voted,
# transfers, last year's orders carried in, final. A line is FLAGGED where its final budget is at
# least half again or half less than the vote and the change is at least $5,000, or where the vote
# was nothing and the line was funded anyway. Both thresholds are ours, and the page says so.
ADJ_SHARE, ADJ_MIN = Decimal('0.5'), Decimal('5000')


def signed(T, v):
    return ('+' if v > 0 else '−' if v < 0 else '') + T.usd(abs(v))


def budget_walk(r, T):
    final = r['voted'] + r['transfers'] + r['carried_budget']
    adj = final - r['voted']
    pct = (adj / r['voted']) if r['voted'] else None
    flag = abs(adj) >= ADJ_MIN and (pct is None or abs(pct) >= ADJ_SHARE)
    return dict(
        walk=T.lit('Voted %s · transfers %s · carried in %s · final %s'
                   % (T.usd(r['voted']), signed(T, r['transfers']), T.usd(r['carried_budget']), T.usd(final))),
        adj=round(fl(adj), 2), adj_t=signed(T, adj) if adj else '',
        adj_pct=T.lit('%s%s%%' % ('+' if adj > 0 else '−', C.num(round(abs(100 * pct))))) if pct is not None and adj else
                (T.lit('not voted') if adj and not r['voted'] else ''),
        flag=bool(flag))


def budget_changes_data(m, T):
    """BUDGET CHANGES AFTER THE VOTE (TJ, 27 October 2026: "it needs to be more visible ... a
    different table specifically for adjusted budget, showing top X expandable"). Every line whose
    final budget is not what was voted, largest change first, each with the transfers that made
    the change -- date, memo, and the lines on the other side -- and the orders carried in."""
    names = {r['account']: line_name(r) for r in m['rows'] if r['account']}
    years = []
    for fy in YEARS():
        rows = []
        for r in m['rows']:
            if r['fy'] != fy or not r['account']:
                continue
            bw = budget_walk(r, T)
            if not bw['adj']:
                continue
            if sum((x['amount'] for x in r['moves_in']), D0) != r['transfers']:
                fail('FY%d %s: its transfers do not sum to the change they make' % (fy, r['account']))
            final = r['voted'] + r['transfers'] + r['carried_budget']
            rows.append(dict(
                cat=S.CAT_LABEL[r['category']], line=T.lit(names[r['account']]), acct=T.lit(r['account']),
                voted=T.usd(r['voted']), transfers=signed(T, r['transfers']) if r['transfers'] else '',
                carried=T.usd(r['carried_budget']) if r['carried_budget'] else '', final=T.usd(final),
                n_voted=round(fl(r['voted']), 2), n_transfers=round(fl(r['transfers']), 2),
                n_carried=round(fl(r['carried_budget']), 2), n_final=round(fl(final), 2), **bw,
                moves=[dict(date=T.lit(long_date(x['date'])), memo=T.lit(x['memo'].strip() or 'no memo'),
                            v=signed(T, x['amount']), n=round(fl(x['amount']), 2),
                            others=[dict(line=T.lit(names.get(o['account'], o['description'].strip().title())),
                                         v=signed(T, o['amount'])) for o in x.get('others', [])])
                       for x in sorted(r['moves_in'], key=lambda x: x['date'])]))
        rows.sort(key=lambda r: -abs(r['adj']))
        years.append(dict(fy=T.fy(fy), rows=rows, n_flag=sum(1 for r in rows if r['flag']),
                          n=len(rows)))
    return dict(years=years, show=10, text=dict(
        cat='Category', line='School line', voted='Voted', transfers='Transfers', carried='Carried in',
        final='Final budget', change='Change', show_all='Show all', show_fewer='Show the first',
        sort='Click a heading to sort',
        lines='lines changed after the vote', flagged='flagged', close='Close',
        open='Open a line for the transfers that changed it',
        moves='Transfers', no_moves='No transfers: the change is last year’s orders carried in.',
        other_side='The other side of the entry', carried_note='Last year’s orders, carried in with their budget:',
        flag_means=T.lit('Flagged: the final budget is half again or half less than the vote, by at '
                         'least %s, or the line was not voted. Thresholds of ours.' % T.usd(ADJ_MIN))))


def lines_data(m, T):
    """Every line, every year, as two sums. The school budget's own, to what was left, with
    cost moved by journal entry shown apart from what it spent; and what the line cost from
    every fund, where a move and a grant paying directly are two different terms. TJ, 26
    October 2026: "money added from other funds REDUCES the general fund... depends how its
    done doesnt it?" It does: a move changes Left, paying directly does not."""
    years = []
    for fy in YEARS():
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
                chip_n=chip_counts(T, r))
            if round(r['other_year_spent']):
                row['spent_note'] = 'of which %s paid for another year' % T.usd(r['other_year_spent'])
            if r['account']:
                row['bw'] = budget_walk(r, T)
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
                    scroll='More columns: scroll the table sideways',
                    sum='The sum', moves='Transfers in or out', nomoves='No budget transferred.',
                    shared='Many lines gave and many got in this one entry, and the books do not '
                           'say which line’s money went to which. The other side, all together:',
                    into='from', outof='to', in_='In', out='Out',
                    tab_summary='Summary', tab_expenses='Expenses', tab_analysis='Analysis',
                    tab_moves='Transfers and re-charges',
                    mv_transfers='Budget transfers',
                    mv_transfers_def='Permission to spend, moved between lines by a vote or an '
                                     'approved transfer. No bill moves; the budget does.',
                    mv_recharges='Re-charges to and from other funds',
                    mv_recharges_def='Bills the school budget had already paid, re-booked to a '
                                     'grant or another fund (or back). The budget does not move; '
                                     'who paid the bill does.',
                    mv_entries='Journal entries between school lines',
                    mv_entries_def='Bills re-booked from one school line to another, or a '
                                   'correction. The budget does not move; which line carries '
                                   'the bill does.',
                    mv_none='None this year.', mv_with='with', mv_in='Onto this line',
                    mv_out='Off this line',
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
                    any_payee='Every payee', any_memo='Every memo', clear_filters='Clear',
                    an_click='Click a bar to see its rows on the Expenses tab.',
                    for_what='for', paid_to='paid to',
                    ex_note='One row per invoice, payroll warrant or journal entry. A purchase '
                            'order shows only what it still owed at year end; one fully paid '
                            'shows as its invoices. Payroll rows are whole pay runs, with no '
                            'names. A bill re-charged to another fund is listed twice: taken '
                            'off the school budget, and under the fund that paid it.',
                    payers='Other funds that paid toward this line',
                    none='No other fund paid toward this line.',
                    unmatched='Other funds’ spending not matched to any line',
                    lines='Line', category='Category', footing='Spent counts orders still owed at year end, so for '
                    '%s and earlier Left can differ from the Town’s printed report by '
                    'those orders.' % C.fy(max(y for y in YEARS() if y != J.OPEN_FY))))


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
        off_all = sum((x['off'] for x in m['moves'] if x['fy'] == fy), D0)
        off_june = sum((x['off'] for x in m['moves'] if x['fy'] == fy and x['date'][5:7] == '06'), D0)
        june = T.lit('%s of the %s re-charged off the school budget in %s was re-charged in June.'
                     % (T.usd(off_june), T.usd(off_all), C.fy(fy))) if off_all else ''
        years.append(dict(fy=T.fy(fy), june=june, a0=T.lit(monday(date(fy - 1, 7, 1)).isoformat()),
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


def year_facts(m, T):
    """THE YEAR IN FIGURES, for every year, switched by the page's picker (TJ, 27 October 2026:
    "make the facts and conclusions switch with the year"). Each fact is a figure the model
    computes; each conclusion states two of them side by side and what follows, nothing about
    why (rule 7)."""
    monday = lambda d: d - timedelta(days=d.weekday())
    files = line_files(m)
    out = []
    for fy in YEARS():
        y = m['years'][fy]
        rs = [r for r in m['rows'] if r['fy'] == fy and r['account']]
        under = sum((r['left'] for r in rs if r['left'] > 0), D0)
        over = -sum((r['left'] for r in rs if r['left'] < 0), D0)
        n_under = sum(1 for r in rs if r['left'] > 0)
        n_over = sum(1 for r in rs if r['left'] < 0)
        off = sum((r['moved_off'] for r in rs), D0)
        on = sum((r['moved_on'] for r in rs), D0)
        direct = sum((r['other_funds'] for r in m['rows'] if r['fy'] == fy), D0) - off
        moved = sum((t['moved'] for t in m['transfers'] if t['fy'] == fy), D0)
        wk = defaultdict(Decimal)
        for rows in files[fy].values():
            for x in rows:
                if x['d'] and not x['k'].startswith(RECHARGE):
                    wk[monday(date.fromisoformat(x['d']))] += x['v']
        big = max(wk, key=lambda w: wk[w])
        if under - over != y['left']:
            fail('FY%d: under less over is not what was left' % fy)
        facts = [
            dict(v=T.usd(y['left']), label='left on the school lines, orders owed counted'),
            dict(v=T.usd(under), label=T.lit('left on the %s lines that ended under budget'
                                             % C.num(n_under))),
            dict(v=T.usd(over), label=T.lit('spent past budget on the %s lines that ran over'
                                            % C.num(n_over))),
            dict(v=T.usd(moved), label='budget moved between lines by transfer'),
            dict(v=T.usd(off), label='bills re-charged off the school budget'),
            dict(v=T.usd(on), label='bills re-charged back onto it'),
            dict(v=T.usd(direct), label='paid by other funds from the start (our match)',
                 estimate=True),
            dict(v=T.usd(wk[big]), label=T.lit('spent or owed in the biggest week, starting %s'
                                               % long_date(big.isoformat()))),
        ]
        if y['prepaid']:
            facts.append(dict(v=T.usd(y['prepaid']), label=T.lit(
                'of %s tuition paid early' % C.fy(fy + 1))))
        if y['carried_unpaid']:
            facts.append(dict(v=T.usd(y['carried_unpaid']), label=T.lit(
                '%s orders carried in and never paid' % C.fy(fy - 1))))
        cons = [dict(
            claim=T.lit('%s left %s: %s on lines under budget, less %s spent past budget on '
                        'the rest.' % (T.fy(fy), T.usd(y['left']), T.usd(under), T.usd(over))),
            so=T.lit('The surplus is a net. %s lines ran over and were covered by leftovers '
                     'elsewhere in the same budget.' % C.num(n_over)))]
        if off or on:
            net = off - on
            cons.append(dict(
                claim=T.lit('Journal entries re-charged %s of bills off the school budget and '
                            '%s back onto it.' % (T.usd(off), T.usd(on))),
                so=T.lit('Net, they %s Left by %s. The bills cost the same either way; only '
                         'the fund that paid them changed.'
                         % ('raised' if net > 0 else 'lowered', T.usd(abs(net))))))
        cons.append(dict(
            claim=T.lit('Grants and other funds paid %s toward these lines from the start.'
                        % T.usd(direct)),
            so='That money never passed through the school budget, so Left does not show it. '
               'Which line it counts toward is our match, by payee or kind of work.'))
        if y['prepaid']:
            cons.append(dict(
                claim=T.lit('%s paid %s of %s tuition before its year began.'
                            % (T.fy(fy), T.usd(y['prepaid']), T.fy(fy + 1))),
                so=T.lit('Paid from %s’s budget, it is spending that year did not need: without '
                         'it, %s would have left %s.'
                         % (T.fy(fy), T.fy(fy), T.usd(y['left'] + y['prepaid'])))))
        elif y['carried_unpaid']:
            cons.append(dict(
                claim=T.lit('%s of %s’s orders were carried in and never paid.'
                            % (T.usd(y['carried_unpaid']), T.fy(fy - 1))),
                so='The budget carried in for them was not spent, so it ends the year as Left.'))
        out.append(dict(fy=T.fy(fy), facts=facts, conclusions=cons))
    return dict(years=out, text=dict(
        facts='The figures', conclusions='What they show', means='What it means:',
        estimate='Our estimate'))


# ACROSS THE YEAR LINE (TJ, 27 October 2026: "watching the money cross boundaries is really what
# we're trying to represent here. This is a money relationship page more than anything"). It
# began as a list of odd things, after FY2026 was found paying FY2027's collaborative tuition
# early; the odd things turned out to be one kind of thing -- money crossing 1 July or 30 June.
# So each year shows what came IN across its first day and what went OUT across its last:
#   in:  last year's orders, carried in with their budget -- paid this year, or never paid;
#        this year's bills, paid ahead by last year
#   out: this year's orders still owed on 30 June, carried to next year; next year's bills paid
#        early; what was left, which lapses at the close; and entries posted to this year after
#        it ended
# Each crossing is measured on BOTH sides where both are held, and must tie: one year's orders
# carried out are the next year's carried in, to the cent. Money crossing between FUNDS is the
# rest of the page (the plan chart, the re-charges); this block is the line between years.
MEMO_DATE = re.compile(r'(?<!\d)(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})(?!\d)')


def memo_dates(text):
    out = []
    for mo, d, y in MEMO_DATE.findall(text or ''):
        y = int(y) + (2000 if len(y) == 2 else 0)
        try:
            out.append(date(y, int(mo), int(d)))
        except ValueError:
            continue
    return out


def owed_at_close(m):
    """(fy, account) -> orders still open on 30 June, read off the journal's encumbrance postings
    before the close (`YEC`). For a closed year it must equal what the close zeroed."""
    A = J.accounts()
    owed, closed = defaultdict(Decimal), defaultdict(Decimal)
    for r in J.lines():
        if not (J.is_expense(A[r['account']]) and J.in_surplus_scope(A[r['account']])):
            continue
        if r['source'] == 'YEC':
            closed[(r['fy'], r['account'])] -= r['amt']
        elif r.get('posts_to') == 'encumbrance':
            owed[(r['fy'], r['account'])] += r['amt']
    for k in set(owed) | set(closed):
        if k[0] != J.OPEN_FY and owed[k] != closed[k]:
            fail('FY%d %s: open orders %s, the close zeroed %s' % (k[0], k[1], owed[k], closed[k]))
    return owed


def year_line_data(m, T):
    names = {r['account']: line_name(r) for r in m['rows'] if r['account']}
    owed = owed_at_close(m)
    top = lambda pairs, n=5: [dict(what=T.lit(names[a]), v=T.usd(v)) for a, v in
                              sorted(pairs, key=lambda p: -p[1])[:n] if v]
    years = []
    for fy in YEARS():
        rs = [r for r in m['rows'] if r['fy'] == fy and r['account']]
        tot = lambda k: sum((r[k] for r in rs), D0)
        end, prev, nxt = date(fy, 6, 30), fy - 1, fy + 1
        carried, unpaid, early = tot('carried_budget'), tot('carried_unpaid'), tot('prepaid')
        carried_spent = tot('other_year_spent') - early
        if carried_spent + unpaid != carried:
            fail('FY%d: carried in %s is not paid %s plus never paid %s'
                 % (fy, carried, carried_spent, unpaid))
        out_owed = sum((v for (y, _), v in owed.items() if y == fy), D0)
        if nxt in YEARS():
            want = sum((r['carried_budget'] for r in m['rows'] if r['fy'] == nxt and r['account']), D0)
            if out_owed != want:
                fail('FY%d: owed on 30 June %s, carried into FY%d %s' % (fy, out_owed, nxt, want))
        if prev in YEARS():
            ahead = sum((r['prepaid'] for r in m['rows'] if r['fy'] == prev and r['account']), D0)
        late = []
        for x in m['moves']:
            if x['fy'] == fy and [d for d in memo_dates(x['description']) if d > end]:
                v = max(x['off'], x['onto'])
                late.append((v, x['description'], x['date'], max(memo_dates(x['description'])), x['journal'],
                             're-charge %s the school budget' % ('off' if x['off'] >= x['onto'] else 'onto')))
        for t in m['transfers']:
            if t['fy'] == fy and [d for d in memo_dates(t['description']) if d > end]:
                late.append((t['moved'], t['description'], t['date'], max(memo_dates(t['description'])),
                             t['journal'], 'transfer between lines'))
        late.sort(key=lambda z: (z[3], -z[0]))
        left = tot('left')
        inn = [dict(id='carried', label=T.lit('%s’s orders, carried in' % C.fy(prev)), v=T.usd(carried),
                    n=fl(carried),
                    parts=[dict(id='paid', label='paid or still owed this year', v=T.usd(carried_spent),
                                n=fl(carried_spent)),
                           dict(id='never', label='never paid: ends the year as Left', v=T.usd(unpaid),
                                n=fl(unpaid))],
                    means=T.lit('Last year’s budget, carried in with orders placed before 30 June. What is '
                          'never paid lapses into this year’s Left, though this year’s own budget '
                          'did not leave it.'),
                    items=top([(r['account'], r['carried_unpaid']) for r in rs]),
                    items_h='Never paid, largest lines')]
        if prev in YEARS():
            inn.append(dict(id='ahead', label=T.lit('This year’s bills, paid ahead by %s' % C.fy(prev)),
                            v=T.usd(ahead), n=fl(ahead), parts=[], items=[], items_h='',
                            means='Bills for this year paid from last year’s budget. This year spends '
                                  'less for them, so its Left is higher by the same amount.'))
        else:
            inn.append(dict(id='ahead', label=T.lit('This year’s bills, paid ahead by %s' % C.fy(prev)),
                            v=None, n=0, parts=[], items=[], items_h='',
                            means=T.lit('%s is not in the journal we hold, so this cannot be read.'
                                        % C.fy(prev))))
        out = [dict(id='owed', label=T.lit('Orders still owed on 30 June, carried to %s' % C.fy(nxt)),
                    v=T.usd(out_owed), n=fl(out_owed), parts=[], items_h='Largest lines',
                    items=top([(a, v) for (y, a), v in owed.items() if y == fy]),
                    means='Counted as spent this year, paid next year. Next year carries in the '
                          'budget for them.' + ('' if nxt in YEARS() else T.lit(
                              ' %s’s books are not in the journal yet, so the other side cannot '
                              'be checked.' % C.fy(nxt)))),
               dict(id='early', label=T.lit('%s’s bills, paid early' % C.fy(nxt)), v=T.usd(early),
                    n=fl(early), parts=[], items_h='',
                    items=[dict(what=T.lit(names[r['account']]), v=T.usd(r['prepaid']))
                           for r in rs if r['prepaid']],
                    means='Spending this year did not need. Without it, this year would have left '
                          'that much more, and next year starts with the bill already paid.'),
               dict(id='left', label='Left, which lapses at the close', v=T.usd(left), n=fl(max(left, D0)),
                    parts=[], items=[], items_h='',
                    means='What the school budget did not spend. It does not carry to next year: '
                          'the year closes and the budget for next year is voted fresh.'),
               dict(id='late', label='Entries posted to this year after it ended',
                    v=T.lit('%s %s' % (C.num(len(late)), 'entry' if len(late) == 1 else 'entries')),
                    n=0, parts=[], items_h=T.lit('Posted to 30 June, memo dated later'),
                    items=[dict(what=T.lit('%s · %s, memo dated %s' % (desc.strip(), kind,
                                                                        long_date(md.isoformat()))),
                                v=T.usd(v)) for v, desc, _, md, _, kind in late],
                    means=T.lit('The books stay open for weeks after 30 June, so this is ordinary. It '
                                'shows how much of the year was settled after it ended, and that a '
                                'report printed in June shows a different year.'
                                + ('' if fy != J.OPEN_FY else ' %s’s close is not in the journal '
                                   'we hold, so its count may still grow.' % C.fy(fy))))]
        years.append(dict(fy=T.fy(fy), prev=T.fy(prev), next=T.fy(nxt), inn=inn, out=out,
                          span=T.lit('1 July %d to 30 June %d' % (fy - 1, fy))))
    # a fact the page was built to show; checked while FY2026 is on the page
    y26 = next((y for y in years if y['fy'] == C.fy(2026)), None)
    if y26 and next(o for o in y26['out'] if o['id'] == 'early')['n'] < 189000:
        fail('the FY2026 tuition paid early is no longer on the year line')
    return dict(years=years, text=dict(h_in=T.lit('Came in across 1 July'), h_out=T.lit('Went out across 30 June'),
                                       from_='from', to='to', unread='cannot be read'))


# WHICH YEARS THE PAGE CAN SHOW, read off the data (TJ, 27 October 2026: "as soon as we ingest
# the same data from munis.. the FY should auto-unlock and be available in the breakout.. or we
# need some hook that knows when a breakout can be built based on the data or what data to ask
# for"). A year is READY when every input the page cannot do without is held; it then appears
# on the page with no edit. The year after the last one held is listed with what it is missing,
# each missing input worded as the records request that would close it -- the same report, with
# the same options, the Town produced last time
# (town-ledgers/account-details/PROVENANCE-fy2023-fy2026-p13-school-journal.md).
JOURNAL_ASK = ('MUNIS YEAR-TO-DATE BUDGET REPORT (glytdbud) with journal detail, %s period 0 to '
               'period 13: Print journal detail Y, Include budget entries Y, Incl encumb/liq entries '
               'Y; school accounts in fund 0100 and every school special fund. In Excel if MUNIS '
               'can export it.')
P13_ASK = ('MUNIS YEAR-TO-DATE BUDGET REPORT (glytdbud) at period 13 for %s, %s, Print totals '
           'only N, Suppress zero balance accounts N, as an Excel export.')


def readiness():
    """[dict(fy, ready, inputs=[dict(id, label, held, required, ask)])] for every year the journal
    holds and the one after it."""
    if '_ready' in _MEMO:
        return _MEMO['_ready']
    ytd = defaultdict(set)
    for r in csv.DictReader(open(os.path.join(ROOT, 'sources', 'data', 'munis-school-ytd.csv'),
                                 encoding='utf-8')):
        if r['period'] == '13':
            ytd[int(r['fiscal_year'])].add(r['report'])
    out = []
    for fy in list(J.YEARS) + [J.YEARS[-1] + 1]:
        name = C.fy(fy)
        inputs = [
            dict(id='journal', label='The school journal, every posting', held=fy in J.YEARS,
                 required=True, ask=JOURNAL_ASK % name),
            dict(id='gf13', label='The period-13 report, school general fund',
                 held='gf-school' in ytd[fy], required=True,
                 ask=P13_ASK % (name, 'the school department’s general fund accounts')),
            dict(id='sp13', label='The period-13 report, school special funds',
                 held='special-school' in ytd[fy], required=True,
                 ask=P13_ASK % (name, 'every school special fund')),
            dict(id='close', label='The year’s close, posted in the journal',
                 held=fy in J.YEARS and fy != J.OPEN_FY, required=False,
                 ask='The same journal report again once the Town has closed %s, so the year-end '
                     'entries are in it.' % name),
            dict(id='book', label='The year’s approved school budget, read', held=fy in PLAN_BOOKS,
                 required=False, ask=None)]
        # a period-13 report and a close exist only once the year has ended, so every ask for a
        # year the journal does not hold yet says when it can be answered
        if fy not in J.YEARS:
            for i in inputs:
                if i['ask']:
                    i['ask'] = 'After %s ends on 30 June %d: %s' % (name, fy, i['ask'])
        out.append(dict(fy=fy, inputs=inputs,
                        ready=all(i['held'] for i in inputs if i['required'])))
    _MEMO['_ready'] = out
    return out


def YEARS():
    """The years every block on the page shows: the ready ones."""
    ys = tuple(r['fy'] for r in readiness() if r['ready'])
    if not ys:
        fail('no year has every input the page needs')
    return ys


def readiness_data(T):
    """The block at the foot of the page: what each year holds, and what the next would need."""
    rows = []
    for r in readiness():
        if r['ready'] and all(i['held'] for i in r['inputs']):
            continue                      # nothing to say about a year with everything
        rows.append(dict(fy=T.fy(r['fy']), ready=r['ready'], inputs=[
            dict(label=T.lit(i['label']), held=i['held'], required=i['required'],
                 ask=T.lit(i['ask']) if i['ask'] and not i['held'] else None) for i in r['inputs']]))
    return dict(years=rows, text=dict(
        ready='On this page', waiting='Not on this page yet: it appears when the required inputs are held',
        held='held', missing='missing', optional='optional', ask='To ask the Town for',
        how='Every year the journal holds and the one after it, checked against the data each '
            'time the page is built.'))


_MEMO = {}


def ledger_doc(fy, scope):
    """The period-13 report for a year, by the archive's naming rule -- and refused if we do not
    hold it, rather than linking an address that does not open."""
    rel = 'town-ledgers/expenses/glytdbud-expense-fy%d-p13-%s.xlsx' % (fy, scope)
    if not any(r['key'].endswith(rel) for r in csv.DictReader(
            open(os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv'), encoding='utf-8'))):
        fail('no period-13 %s report for FY%d in the archive manifest' % (scope, fy))
    return '/docs/' + rel


def page(m):
    # EVERY YEAR THE JOURNAL HOLDS, none named (TJ, 27 October 2026: "these pages shouldnt be
    # specific to each year. it should auto-create for the FY based on the data"). The page's
    # own facts and conclusions compare the years by RULE -- the least and most left, the most
    # re-charged off and onto -- so a year added to the journal takes its place without an edit.
    mv = {y: sum((x['off'] - x['onto'] for x in m['moves'] if x['fy'] == y), D0) for y in YEARS()}
    f = LD.fact
    left = {y: m['years'][y]['left'] for y in YEARS()}
    first, last = YEARS()[0], YEARS()[-1]

    def con(text, rests, figs, so):
        return TP.conclusion(text, rests, figs, so=so[0], so_figures=so[1], so_allow=so[2])
    facts = [f('left%d' % y, U(left[y]), 'left on the school lines, %s' % C.fy(y), 'published',
               label_figures={'y': F(y)}) for y in YEARS()] + [
        f('moved%d' % y, U(abs(mv[y])), ('taken off the school budget by re-charges, %s, net' if mv[y] >= 0
                                          else 'added to it by re-charges, %s, net') % C.fy(y),
          'published', label_figures={'y': F(y)}) for y in YEARS()]
    lo, hi = min(YEARS(), key=lambda y: left[y]), max(YEARS(), key=lambda y: left[y])
    conclusions = [
        con('The school lines left as little as %s in %s and as much as %s in %s.'
            % (C.usd(fl(left[lo])), C.fy(lo), C.usd(fl(left[hi])), C.fy(hi)),
            ['left%d' % y for y in YEARS()],
            {'a': U(left[lo]), 'x': F(lo), 'b': U(left[hi]), 'y': F(hi)},
            so=('The same budget process, years apart by that much. Each year’s own figures, '
                'below, show what moved in it.', None, ()))]
    off_y, on_y = max(YEARS(), key=lambda y: mv[y]), min(YEARS(), key=lambda y: mv[y])
    if mv[off_y] > 0 and mv[on_y] < 0:
        conclusions.append(con(
            'Re-charges took %s off the school budget in %s and added %s to it in %s.'
            % (C.usd(fl(mv[off_y])), C.fy(off_y), C.usd(fl(-mv[on_y])), C.fy(on_y)),
            ['moved%d' % off_y, 'moved%d' % on_y],
            {'a': U(mv[off_y]), 'y': F(off_y), 'b': U(-mv[on_y]), 'z': F(on_y)},
            so=('A swing of %s between two years, made by entries after the spending; the bills '
                'cost the same either way.' % C.usd(fl(mv[off_y] - mv[on_y])),
                {'s': U(mv[off_y] - mv[on_y])}, ())))
    else:
        w = off_y if mv[off_y] > 0 else on_y
        conclusions.append(con(
            'Re-charges moved the most in %s: %s, net, %s the school budget.'
            % (C.fy(w), C.usd(fl(abs(mv[w]))), 'off' if mv[w] > 0 else 'onto'),
            ['moved%d' % y for y in YEARS()], {'y': F(w), 'a': U(abs(mv[w]))},
            so=('Made by entries after the spending; the bills cost the same either way.', None, ())))
    T = Texts()
    lines = lines_data(m, T)
    figures = year_facts(m, T)
    plan = plan_data(m, T)
    yline = year_line_data(m, T)
    sources = funds_data(m, T)
    overlap = overlap_data(m, T)
    for oy, sy in zip(overlap['years'], sources['years']):
        for gr in oy['groups']:
            want = sum(r['n']['total'] for r in sy['rows'] if r['group'] == gr['id'])
            if abs(sum(gr['n'].values()) - want) > 0.05:
                fail('%s %s: the bands hold %.2f, the table of funds %.2f'
                     % (oy['fy'], gr['id'], sum(gr['n'].values()), want))
    # the two readings of the same money agree: by fund, summed by who paid, is level 1's
    for py_, sy in zip(plan['years'], sources['years']):
        for o in py_['others']:
            want = o['start'] + o['later'] + o['unmatched'] + (py_['cb']['paid'] if o['id'] == 'cb' else 0)
            got = sum(r['n']['total'] for r in sy['rows'] if r['group'] == o['id'])
            if abs(want - got) > 0.05:
                fail('%s %s: by fund %.2f, level 1 %.2f' % (py_['fy'], o['id'], got, want))
        if any(r['group'] == 'gf' for r in sy['rows']):
            fail('%s: a general fund row in the table of other funds' % sy['fy'])
    weeks = year_weeks(m, T)
    ready = readiness_data(T)
    by_line = line_funds_data(m, T)
    changes = budget_changes_data(m, T)
    payees = payees_data(m, T)
    salaries = salaries_data(m, T)
    fund_moves = moves_data(m, T)
    # the bridge block's sentence, held to every year it is shown with: other funds are most of
    # the gap between the plan and what happened, and more than half of them on no school line
    for y in plan['years']:
        st = {b['id']: b['n'] for b in y['bridge']}
        gap = y['totals']['happened'] - y['totals']['plan']
        if not (st['other'] + st['none'] > gap / 2 and st['none'] > st['other']):
            fail('%s: the bridge says the gap is mostly other funds, most on no line; it is not' % y['fy'])
    return TP.page(
        ID,
        'The school lines left %s in %s and %s in %s; pick a year to see what moved in it.'
        % (C.usd(fl(left[first])), C.fy(first), C.usd(fl(left[last])), C.fy(last)),
        facts, conclusions,
        chart=TP.series(
            'What the school lines left, by year', [C.fy(y) for y in YEARS()],
            [TP.track('Left, orders still owed counted', [fl(m['years'][y]['left']) for y in YEARS()],
                      'published', 'bar')], '$', kind='bar',
            note='School general fund, department 300. Every line’s Left in the table above, '
                 'summed.', note_allow=('300',)),
        blocks=[
            TB.custom('fy-year-picker', 'Fiscal year', dict(
                bare=True, years=[C.fy(y) for y in YEARS()], label='Change year',
                spans={C.fy(y): '1 July %d to 30 June %d' % (y - 1, y) for y in YEARS()}),
                      place='top', figures=[C.fy(y) for y in YEARS()],
                      allow=['1 July %d to 30 June %d' % (y - 1, y) for y in YEARS()],
                      alt='The fiscal year every chart on this page shows',
                      so=('Every chart below shows the year picked here, and a line opened from '
                          'the table opens in that year.', None, ())),
            TB.custom('fy-plan', 'The plan and what happened', plan, place='top',
                      figures=sorted(T.figures), allow=sorted(T.literals),
                      basis=('reading', 'Our placing of other funds’ spending on the lines'),
                      alt='Bar chart, one fiscal year: the school general fund against its '
                          'budget, the circuit breaker against the offset the year’s book printed '
                          'under collaborative tuition, and what other funds paid toward the '
                          'school lines, each bar starting at the plan',
                      so=('Where the general fund ends under its budget, the grey part is bills '
                          're-charged to other funds after it paid them, not spending it avoided; '
                          'the circuit breaker row shows whether the money the book counted on '
                          'came.', None, ())),
            TB.custom('fy-bridge', 'From the plan to what happened', dict(
                years=[dict(fy=y['fy'], bridge=y['bridge'],
                            totals=dict(plan=y['totals']['plan'], happened=y['totals']['happened'],
                                        t=dict(plan=y['totals']['t']['plan'], happened=y['totals']['t']['happened'])))
                       for y in plan['years']],
                text=dict(a_plan=plan['text']['a_plan'], a_happened=plan['text']['a_happened'])),
                      place='top', figures=sorted(T.figures), allow=sorted(T.literals),
                      basis=('reading', 'Our placing of other funds’ spending on the lines'),
                      alt='Bridge chart, one fiscal year: the plan, then a step for each reason '
                          'what happened differs from it -- what the general fund left unspent, '
                          'the circuit breaker against what the book counted on, other funds '
                          'toward school lines and on none -- ending at what happened; every bar '
                          'on one scale from zero',
                      so=('The gap between the plan and what happened is mostly money no budget '
                          'book plans for: other funds, much of it on no school line.', None, ())),
            TB.custom('fy-year-line', 'Across the year line', yline, place='top',
                      figures=sorted(T.figures), allow=sorted(T.literals),
                      basis=('record', 'Every posting on the school lines; each crossing tied to the other year'),
                      alt='Diagram for one fiscal year: money that came in across 1 July from the '
                          'year before -- orders carried in, paid or never paid, and bills paid '
                          'ahead -- and money that went out across 30 June -- orders still owed, '
                          'next year’s bills paid early, what was left, and entries posted after '
                          'the year ended',
                      so=('Every crossing changes what the year’s own figures say without any '
                          'bill costing more or less: a year can look under budget because last '
                          'year paid its bills, or over because it paid next year’s.', None, ())),
            TB.custom('fy-year-weeks', 'Every week of the year', weeks, place='top',
                      figures=sorted(T.figures), allow=sorted(T.literals),
                      basis=('record', 'Every posting on the school lines, by week'),
                      alt='Bar chart, one fiscal year at a time: every week from July to June, '
                          'what every school line spent or still owed that week, stacked by who '
                          'paid or by kind of posting, with bills re-charged to other funds below '
                          'the line',
                      so=('Re-charges are journal entries, so they land when the books are '
                          'adjusted, not when the bills were paid. The line under the totals says '
                          'how much of the year’s landed in June.', None, ())),
            TB.custom('fy-budget-changes', 'Budget changes after the vote', changes, place='top',
                      figures=sorted(T.figures), allow=sorted(T.literals),
                      basis=('record', 'Every budget transfer in the journal'),
                      alt='Table, one fiscal year: every school line whose final budget differs from '
                          'the vote, largest change first -- voted, transfers, orders carried in, '
                          'final, and the change -- with the largest shown and the rest behind a '
                          'button; a line opens the transfers that changed it',
                      so=('A line’s final budget can be far from what Town Meeting voted. Compare '
                          'spending to the final budget and the line can look on target when the '
                          'vote was not.', None, ())),
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
            TB.custom('fy-line-funds', 'School lines other funds paid', by_line, place='top',
                      figures=sorted(T.figures), allow=sorted(T.literals),
                      basis=('reading', 'Our placing of other funds’ spending on the lines'),
                      alt='Table, one fiscal year: each school budget line other funds paid toward, '
                          'with the fund, its kind, how the money was placed on the line, the '
                          'amount, the line’s budget and the share of its cost; sortable and '
                          'filterable by kind of fund',
                      so=('Re-charged money is in the journal; the rest is our match by payee or '
                          'function code. A line here is one the school budget did not pay for '
                          'alone.', None, ())),
            TB.custom('fy-source-table', 'What other funds paid for', sources, place='top',
                      figures=sorted(T.figures), allow=sorted(T.literals),
                      basis=('reading', 'Our placing of other funds’ spending on the lines'),
                      alt='Table of every fund other than the school budget that spent on the '
                          'schools in one fiscal year: what it paid toward school lines, re-charges '
                          'to and from the school budget, capital articles and spending on no '
                          'school line, each fund opening on where its money went and every posting',
                      so=('A fund’s money reaches the schools in different ways: some pays for the '
                          'same things a school line pays for, and much pays for things no school '
                          'line covers.', None, ())),
            TB.custom('fy-payees', 'Who the schools paid', payees, place='top',
                      figures=sorted(T.figures), allow=sorted(T.literals),
                      basis=('record', 'Every invoice in the journal, every school fund'),
                      alt='Table, one fiscal year: every payee the schools paid by invoice from any '
                          'fund, against the year before, with the change; payees new this year '
                          'and payees not paid this year called out; a payee opens on what was '
                          'bought from it, the lines and funds that paid it, and every payment',
                      so=('Who was paid, and how that moved, is the plainest view of what the '
                          'money bought. A payee new or gone is a change to ask about, not a '
                          'finding by itself: a contract can be re-let, a vendor renamed.', None, ())),
            TB.custom('fy-salaries', 'Salaries paid outside the general fund', salaries, place='top',
                      figures=sorted(T.figures), allow=sorted(T.literals),
                      basis=('record', 'Every pay posting in the journal; moves name both ends'),
                      alt='Two tables, one fiscal year: school salary lines whose pay a journal '
                          'entry moved to or from another fund, with the share another fund carried '
                          'in the end; and every other fund’s pay, by whether it was moved to or '
                          'from a school line, booked to the same kind of work, or on no school line',
                      so=('A salary line can end below the pay it ran because a grant took part of '
                          'it at year end, or above because it took pay back. Most grant pay sits on '
                          'no school line: the ledger names a kind of work, never a post.',
                          None, ())),
            TB.custom('fy-fund-moves', 'Cost moved between funds', fund_moves, place='top',
                      figures=sorted(T.figures), allow=sorted(T.literals),
                      basis=('record', 'Every journal entry naming two funds; the pairing is the books’'),
                      alt='List, one fiscal year: every pair of funds a journal entry re-booked cost '
                          'between, grant awards of the same programme first, each with the fund it '
                          'came from, the fund it went to, the net and how many entries; a row opens '
                          'its entries with date, memo and journal number, reversals marked',
                      so=('A grant’s costs can be re-booked from one year’s award to another’s after '
                          'they are paid, so an award’s total is not what that year’s work cost.',
                          None, ())),
            TB.custom('fy-overlap', 'Overlap with the school budget', overlap, place='top',
                      figures=sorted(T.figures), allow=sorted(T.literals),
                      basis=('reading', 'Our matching of other funds’ spending to school lines'),
                      alt='Bar chart, one fiscal year: other funds’ spending in bands from the '
                          'strongest overlap with the school budget (the same bills, the same vendor, '
                          'the same function code) to none (cannot tell, separate), in all and by '
                          'who paid; and on the school lines other funds paid toward, the share '
                          'they paid',
                      so=('Overlap shows where other funds paid for what the school budget also '
                          'pays for. It does not show whether that money added to the school '
                          'budget or stood in for it; the books do not record that.', None, ())),
            TB.custom('fy-year-facts', 'The year in figures', figures, place='top',
                      figures=sorted(T.figures), allow=sorted(T.literals),
                      basis=('record', 'Computed from every posting on the school lines'),
                      alt='The picked year’s figures and what they show',
                      so=('Each figure is the year picked at the top; pick another and they '
                          'change with it.', None, ())),
            TB.custom('fy-readiness', 'Years and what they need', ready, place='top',
                      figures=sorted(T.figures), allow=sorted(T.literals),
                      basis=('record', 'What the archive holds, checked when the page is built'),
                      alt='List of fiscal years: for each year the page does not show in full, '
                          'which inputs are held and which are missing, with the records request '
                          'that would close each missing one',
                      so=('A year joins this page the day its data is held. What is missing for '
                          'the next one is a records request, worded here.', None, ())),
            # LAST (TJ, 28 October 2026: "move that to the bottom of the page. Its likely too detailed
            # and will overwhelm people")
            TB.custom('fy-web', 'How the funds and lines connect', web_data(T), place='top',
                      figures=sorted(T.figures), allow=sorted(T.literals),
                      basis=('reading', 'Our placing of other funds’ spending on the lines'),
                      alt='Network diagram, one fiscal year: every fund that spent on the schools '
                          'as a block on the left and every school line as a block on the right, '
                          'with an arrow for each way money connected them -- paid from the start, '
                          're-charged later, moved back, the same kind of work, on no school line -- '
                          'and budget transfers between lines as dashed arcs; a block opens the list '
                          'of its arrows with their amounts',
                      so=('The arrows are where the money met the lines: a line with several arrows '
                          'into it was paid for by more than the school budget. No arrow runs from '
                          'one line’s leftover to another’s overrun, because the books never record '
                          'one.', None, ())),
            # APPENDIX (TJ, 28 October 2026: "put this context on the breakout page as an appendix
            # info section ... about how its difficult to match grant money"). No figure: the
            # audit it summarises is ours and not yet in the model (notes/HANDOFF-FY-BREAKDOWN.md)
            TB.explain('Why grant money is hard to match', [
                '**Some money shown as on no school line pays for the same things a school line '
                'does.** Grants and fee funds book their payroll to accounts named for a kind of work, '
                'often with no function code, so no match rule here can tie it to a line, even when it '
                'pays the same staff.',
                'We read every such dollar, group by group. The largest part is grant pay for special '
                'education aides, guidance counselors and teachers: the Town’s own year-end corrections '
                'move that pay to and from those very lines, which shows where it belongs. Most of the '
                'rest is the funds’ own programmes: lunch, extended day, trips and exam fees.',
                'So this page understates what other funds pay toward the school lines. Placing that '
                'money on the lines it supports is a further reading of ours, not yet made here.',
            ], place='end', tone='define'),
        ],
        sources=[
            dict(label='Lunenburg Budget Project — munis-school-journal.csv (every school '
                       'journal line, every fund, %s–%s, our redacted reading of the '
                       'Town’s Report 1)' % (C.fy(first), C.fy(last)), href=J.PUBLIC['journal']),
            dict(label='Lunenburg Budget Project — munis-school-journal-accounts.csv',
                 href=J.PUBLIC['accounts']),
            dict(label='Town of Lunenburg — school general fund period-13 reports, %s–%s '
                       '(each line tied to the cent)' % (C.fy(first), C.fy(last)),
                 href=ledger_doc(last, 'gf-school')),
            dict(label='Town of Lunenburg — school special funds period-13 reports (every fund '
                       'they print tied to the cent)',
                 href=ledger_doc(last, 'special-school')),
            dict(label='Town of Lunenburg — how the journal reached us, and what was redacted',
                 href='/docs/town-ledgers/account-details/'
                      'PROVENANCE-fy2023-fy2026-p13-school-journal.md')],
        finding_figures={'a': U(left[first]), 'x': F(first), 'b': U(left[last]), 'y': F(last)},
        # HIDDEN, NOT RELEASED (TJ, 26 October 2026: "put this page into a hidden section where
        # we wont release it"). Built as a draft: outside the shelf registry, so it is on no
        # shelf, in no topics.json, not in the sitemap and not prerendered. The address still
        # opens for anybody given it.
        draft=dict(title='FY breakdown', home='school-all-funds'))


# THE PLAN, AS PRINTED (TJ, 27 October 2026: "if collab tuition is voted net of circuit breaker,
# we need to show that ... compare what happened with the general fund and cb to make sure it
# matches the plan"). Each year's approved book. The only offset any of the four prints is the
# circuit breaker, under collaborative tuition; it is read off the book, never typed, and must
# tie: the printed gross less the printed offset is what the ledger says was voted.
PLAN_BOOKS = {2023: 'fy23-approved-budget', 2024: 'fy24-approved-budget',
              2025: 'fy25-final-approved-budget-expenses-6-5-24',
              2026: 'final-fy26-town-manager-39-s-target-budget-approved-3-12-25'}
COLLAB = '535023'
NUM = re.compile(r'-?\(?\$?\s*[\d,]+(?:\.\d+)?\)?')


def nums(text):
    out = []
    for t in NUM.findall(text):
        neg = t.startswith('-') or t.startswith('(')
        v = Decimal(re.sub(r'[^\d.]', '', t))
        out.append(-v if neg else v)
    return out


def printed_plan(m):
    """fy -> dict(gross, offset or None, line numbers, raw lines, book): collaborative tuition
    and the circuit breaker line under it, in that year's approved book, tied to the ledger."""
    voted = {r['fy']: r['voted'] for r in m['rows'] if (r['account'] or '').endswith('-' + COLLAB)}
    out = {}
    for fy in YEARS():
        book = PLAN_BOOKS.get(fy)
        # A YEAR WHOSE BOOK IS NOT MAPPED YET still gets its page: the plan is the ledger's vote,
        # and the circuit breaker offset is marked UNREAD -- never "printed none", which is a
        # statement about a book nobody opened (rule 13c). Mapping it is one line above.
        if book is None:
            out[fy] = dict(gross=voted[fy], offset=None, line=None, raw=[], book=None)
            continue
        path = os.path.join(ROOT, 'sources', 'district-budget', 'text', book + '.txt')
        lines = open(path, encoding='utf-8').read().split('\n')
        at = [i for i, t in enumerate(lines) if t.startswith('Collaborative Tuitions ')]
        if len(at) != 1:
            fail('%s: %d collaborative tuition lines, not one' % (book, len(at)))
        i = at[0]
        gross = [v for v in nums(lines[i][len('Collaborative Tuitions'):]) if v > 0]
        cb = lines[i + 1] if lines[i + 1].startswith('Circuit Breaker (') else None
        if cb is None:
            if voted[fy] not in gross:
                fail('%s prints no circuit breaker line, and no column of collaborative tuition is '
                     'the %s the ledger says was voted' % (book, voted[fy]))
            out[fy] = dict(gross=voted[fy], offset=None, line=i + 1, raw=[lines[i]], book=book)
            continue
        # past the label's two percentage groups, "(70% = $422,408) (75% = 452,580)"
        offs = [-v for v in nums(re.sub(r'^Circuit Breaker(\s*\([^)]*%[^)]*\))*', '', cb)) if v < 0]
        # tied to the precision the book prints: to the cent where it prints cents, to the
        # dollar where it prints whole dollars
        ties = lambda g, o: (g - o == voted[fy] or (g == g.to_integral() and o == o.to_integral()
                                                    and abs(g - o - voted[fy]) < Decimal('0.5')))
        # every pairing, not column by column: a book can print an actual beside the tuition
        # line and none beside the circuit breaker, so the columns do not line up
        hit = sorted({(g, o) for g in gross for o in offs if ties(g, o)})
        if len(hit) != 1:
            fail('%s: %d pairings of collaborative tuition less its circuit breaker line make the '
                 '%s the ledger says was voted, not one' % (book, len(hit), voted[fy]))
        out[fy] = dict(gross=hit[0][0], offset=hit[0][1], line=i + 1, raw=[lines[i], cb], book=book)
    return out


def plan_data(m, T):
    """Level 1: the school general fund against its budget, the circuit breaker against what the
    book counted on, and the other funds the book printed nothing about -- every year."""
    plan = printed_plan(m)
    groups = [g for g in PAYERS if g[0] != 'gf']
    years = []
    for fy in YEARS():
        rs = [r for r in m['rows'] if r['fy'] == fy]
        ln = [r for r in rs if r['account']]
        tot = lambda f: sum((f(r) for r in ln), D0)
        budget = tot(lambda r: r['voted'] + r['transfers'] + r['carried_budget'])
        spent, off, on = tot(lambda r: r['gf_spent']), tot(lambda r: r['moved_off']), tot(lambda r: r['moved_on'])
        before = spent + off - on
        left = tot(lambda r: r['left'])
        if budget - spent != left:
            fail('FY%d: budget %s less spent %s is not left %s' % (fy, budget, spent, left))
        # who else paid toward the lines, and how: re-charged after the school budget paid, or
        # paid from the start. The circuit breaker's payments on collaborative tuition are the
        # part the book counted on; everything else is beyond what it prints.
        start, later = defaultdict(Decimal), defaultdict(Decimal)
        cb_collab = D0
        for r in rs:
            if sum(r['how'].values(), D0) != r['other_funds']:
                fail('FY%d %s: who paid does not sum to what other funds paid' % (fy, r['account']))
            for (rule, py, _), v in r['how'].items():
                g = payer_group(py)
                if g == 'cb' and (r['account'] or '').endswith('-' + COLLAB):
                    cb_collab += v
                    continue
                (later if rule == 'moved' else start)[g] += v
        un = defaultdict(Decimal)
        for (py, _), v in m['years'][fy]['unmatched'].items():
            un[payer_group(py)] += v
        if set(un) - {g for g, _ in groups}:
            fail('FY%d: money on no line from %s, which the level-1 chart has no colour for'
                 % (fy, sorted(set(un) - {g for g, _ in groups})))
        pl = plan[fy]
        offset = pl['offset']
        # UNSPENT (TJ, 27 October 2026: "the end of the spend chart to show unspent money too"):
        # what each source allocated to the year and did not spend. Only the school budget and
        # the circuit breaker the book counted on HAVE an allocation for the year; the next
        # tuition paid early is drawn apart, inside what the general fund spent.
        early = m['years'][fy]['prepaid']
        if early != sum((r['prepaid'] for r in ln), D0):
            fail('FY%d: tuition paid early, by line, is not the year’s' % fy)
        gf_un = max(left, D0)
        cb_un = max(offset - cb_collab, D0) if offset is not None else D0
        # the absolute view: the plan is the budget plus what the book counted on; what happened
        # is what every fund paid toward the school lines
        planned = budget + (offset or D0)
        happened = spent + cb_collab + sum(start.values(), D0) + sum(later.values(), D0)
        if abs(happened - tot(lambda r: r['gf_spent'] + r['other_funds'])
               - sum((r['other_funds'] for r in rs if not r['account']), D0)) > Decimal('0.01'):
            fail('FY%d: what happened %s is not what every fund paid toward the lines' % (fy, happened))
        # THE BRIDGE (TJ, 27 October 2026, of the difference chart it replaces: "the hardest to
        # understand"). From the plan to what happened in four steps, each one reason, summing
        # exactly: what the general fund left unspent, the circuit breaker against what the book
        # counted on, and what other funds paid -- toward school lines, then on none.
        other_on = sum(start.values(), D0) + sum(later.values(), D0)
        unm = sum(un.values(), D0)
        cb_step = cb_collab - (offset or D0)
        # ONE NAME A STEP, EVERY YEAR (TJ, 29 October 2026: "'circuit breaker' shows up in various
        # flavors"): the label is constant and the year's qualifier is `sub`; `means` is the hover
        steps = [('gf', -left, 'General fund', 'left unspent' if left >= 0 else 'spent past its budget',
                  'Its budget less what it spent, after bills were re-charged to and from other funds.'),
                 ('cb', cb_step, 'Circuit breaker', ('counted on, not charged' if cb_step < 0
                                                     else 'charged beyond what was counted on')
                  if offset is not None else 'the book did not count on it'
                  if pl['book'] else 'against a book not read yet',
                  'Charged to collaborative tuition, against the offset the year’s book printed.'
                  if offset is not None else 'This year’s book printed no offset, so all of it is beyond the plan.'
                  if pl['book'] else 'This year’s approved book is not mapped yet, so what it counted on is unknown.'),
                 ('other', other_on, 'Other funds', 'toward school lines',
                  T.lit('Grants, fees and other funds, on the same lines the budget pays for; %s of it '
                        're-charged from the school budget after it paid.' % T.usd(sum(later.values(), D0)))),
                 ('none', unm, 'Other funds', 'on no school line',
                  'School spending the books give no school line for: we cannot say which line it paid toward.')]
        if planned + sum((v for _, v, _, _, _ in steps), D0) != happened + unm:
            fail('FY%d: the bridge does not land on what happened' % fy)
        bridge = [dict(id=i, n=fl(v), v=('+' if v > 0 else '−' if v < 0 else '') + T.usd(abs(v)),
                       label=l, sub=q, means=w) for i, v, l, q, w in steps]
        years.append(dict(
            bridge=bridge, unread=pl['book'] is None,
            fy=T.fy(fy), book=T.lit('/docs/district-budget/docs/%s.pdf' % pl['book']) if pl['book'] else None,
            book_line=T.lit(str(pl['line'])) if pl['line'] else None, raw=[T.lit(x) for x in pl['raw']],
            gf=dict(budget=fl(budget), before=fl(before), off=fl(off), on=fl(on), spent=fl(spent),
                    left=fl(left), early=fl(early), unspent=fl(gf_un),
                    t=dict(early=T.usd(early), own=T.usd(spent - early), unspent=T.usd(gf_un), used=T.usd(budget - gf_un), budget=T.usd(budget), before=T.usd(before), off=T.usd(off),
                           on=T.usd(on), spent=T.usd(spent), left=T.usd(left),
                           under=T.usd(budget - before), voted=T.usd(tot(lambda r: r['voted'])),
                           transfers=T.usd(tot(lambda r: r['transfers'])),
                           carried=T.usd(tot(lambda r: r['carried_budget'])))),
            # `lines`: everything the circuit breaker spent on school lines, collaborative tuition or
            # not -- the level-1 chart draws it as ONE part (TJ, 29 October 2026: "we dont NEED to know
            # WHERE they were spent")
            cb=dict(plan=None if offset is None else fl(offset), paid=fl(cb_collab), unspent=fl(cb_un),
                    lines=fl(cb_collab + start['cb'] + later['cb']),
                    t=dict(plan=None if offset is None else T.usd(offset), paid=T.usd(cb_collab),
                           lines=T.usd(cb_collab + start['cb'] + later['cb']),
                           unspent=T.usd(cb_un), used=None if offset is None else T.usd(offset - cb_un),
                           gross=T.usd(pl['gross']),
                           net=T.usd(pl['gross'] - (offset or D0)),
                           diff=None if offset is None else T.usd(abs(cb_collab - offset)))),
            others=[dict(id=g, start=fl(start[g]), later=fl(later[g]), unmatched=fl(un[g]),
                         t=dict(start=T.usd(start[g]), later=T.usd(later[g]),
                                paid=T.usd(start[g] + later[g]), unmatched=T.usd(un[g]),
                                all=T.usd(start[g] + later[g] + un[g])))
                    for g, _ in groups],
            # TJ, 27 October 2026: "how far beyond the budget spending went, and from where" --
            # so what happened is EVERY school dollar, money on no line included, by who paid
            totals=dict(plan=fl(planned), happened=fl(happened + sum(un.values(), D0)),
                        unmatched=fl(sum(un.values(), D0)), unspent=fl(gf_un + cb_un),
                        t=dict(unspent=T.usd(gf_un + cb_un), plan=T.usd(planned), happened=T.usd(happened + sum(un.values(), D0)),
                               beyond=T.usd(happened + sum(un.values(), D0) - planned))),
            others_t=dict(start=T.usd(sum(start.values(), D0)), later=T.usd(sum(later.values(), D0)),
                          paid=T.usd(sum(start.values(), D0) + sum(later.values(), D0)),
                          all=T.usd(sum(start.values(), D0) + sum(later.values(), D0) + sum(un.values(), D0)),
                          unmatched=T.usd(sum(un.values(), D0)))))
    text = dict(
        lg_gf='School general fund: spent before re-charges, against its budget',
        lg_off='Re-charged off it to other funds', lg_on='Re-charged back onto it',
        lg_cb='Circuit breaker on collaborative tuition, against what the book counted on',
        less='less than the plan', more='more than the plan',
        r_gf='School general fund', budget='Budget', left='left', over='over by',
        before='Spent before re-charges',
        r_cb='Circuit breaker, collaborative tuition', counted='Counted on in the book',
        none_printed='The book printed no offset', unread='This year’s approved book is not read yet', charged='charged', charged_of='charged of',
        r_other='Other funds', not_printed='No book printed these as part of the plan',
        from_start='paid from the start', later='re-charged after the school budget paid',
        unmatched_note='Hatched: {v} of it is on no school line; we cannot say which line it paid toward.',
        h_plan='The plan', voted='Voted', transfers='Transfers in or out',
        carried='Last year’s orders carried in',
        collab_gross='Collaborative tuition, before the offset', collab_net='Collaborative tuition, voted',
        none='none printed', not_read='book not read yet', h_gf='The school general fund',
        under='Budget less spent before re-charges', spent='Spent, after re-charges',
        left_row='Left', charged_row='Charged to the circuit breaker',
        cb_diff='Charged, against what was counted on',
        of_later='of which re-charged after the school budget paid',
        other_total='Other funds, toward the school lines', other_all='Other funds, everything spent',
        all_total='Everything spent, every fund',
        beyond_row='Beyond the plan',
        unmatched_row='Other funds, on no school line',
        printed='The lines as the year’s book prints them',
        h_abs='In dollars',
        a_plan='The plan', a_plan_sub='Budget, and the circuit breaker the book counted on',
        a_happened='What happened', a_happened_sub='Every school dollar spent, by who paid',
        a_beyond='beyond the plan', on_no_line='on no school line', hatched_part='Hatched: spent on no school line',
        unmatched_row_note='hatched in the charts',
        a_gf_budget='School general fund budget', a_gf_spent='School general fund, after re-charges',
        a_gf_early='School general fund, next year’s tuition paid early',
        a_gf_unspent='School general fund, unspent', a_cb_unspent='Circuit breaker, counted on, not charged',
        a_gf_used='School general fund budget, spent', a_cb_used='Circuit breaker, counted on and charged',
        a_unspent='unspent', a_unspent_sub='Outlined at the end: planned and not spent',
        a_unspent_note=('Unspent is shown for the school general fund and the circuit breaker the book '
                        'counted on, the two with an allocation for the year. Most grants and '
                        'revolving funds print no budget for the year, so theirs is not drawn.'),
        a_cb_plan='Circuit breaker, counted on', a_cb_paid='Circuit breaker, collaborative tuition', book='Approved budget book', line='line',
        # ONE LABEL PER FUND under the bars, its total, no parts (TJ, 29 October 2026: "'circuit
        # breaker' shows up in various flavors", then "i dont want the subbullets on these items")
        g_gf='School general fund', g_cb='Circuit breaker', g_unspent='Unspent',
        table_h='The figures behind the chart')
    return dict(years=years, text=text,
                groups=[dict(id=g, label=('Circuit breaker, other lines' if g == 'cb' else l))
                        for g, l in groups])


# WHAT EACH SOURCE PAID FOR (TJ, 27 October 2026: "what the non-general fund paid for, in a
# table. so that we know per source what was paid for"). The big table reads by school line; this
# reads by fund, every dollar it spent, and where each went: onto a school line, onto the same
# kind of work, re-charged to or from the school budget, a capital article, or no school line.
# Named for the EVIDENCE, not for what the money was for (TJ: "i dont know how thats different
# than 'same kind of work'"): a payee match places a bill on one line; a function code only on
# a category -- payroll has no payee, so a fund's staff can only ever match this way.
SRC_COLS = [('payee', 'Same vendor as a school line',
             'Bills this fund paid itself, to a payee the school budget also paid from a line -- '
             'May Institute, say, paid from IDEA and from private tuition. Placed on that line. '
             'Our match, by payee.'),
            ('function', 'Same function code as a school line',
             'Spending with no payee to match -- payroll, mostly -- booked under the same function '
             'code as a school line. Placed on a category, not a line. Our match, by code.'),
            ('later', 'Re-charged from the school budget',
             'The school budget paid these bills first; a journal entry later put them on this fund.'),
            ('back', 'Re-charged back to the school budget',
             'This fund paid first; a journal entry later put the bills back on the school budget.'),
            ('capital', 'Capital articles',
             'Spending from an article Town Meeting voted apart from the operating budget.'),
            ('between', 'Moved between funds',
             'Cost a journal entry re-booked onto this fund from another fund (or, below zero, off it '
             'to another), with no school line in the move. No cash moves; the cost was already paid.'),
            ('none', 'On no school line',
             'School spending the books give no school line for: a function the school budget has '
             'no line for, a general heading, or no function at all.'),
            ('total', 'Total', 'Everything this fund spent in the year, orders still owed counted.')]
KIND_WHERE = {'payee': 'same vendor as', 'function': 'same function code as', 'later': 're-charged from',
              'back': 're-charged back to', 'capital': 'capital article', 'none': 'on no school line',
              'between': 're-booked'}


def fund_label(f, A=None):
    """A fund's name for reading: the site's one map (journal.grant_program -- "Athletic fee fund
    (Chapter 658)" for 1301, a DESE program for a grant), the year a grant or article names, and
    its number. TJ, 27 October 2026, of `Chapter 658 Revolving Fund · 1301`: "is that the athletic
    revolving account?" -- the printed name did not say, so it goes underneath, not first."""
    A = A or J.accounts()
    if f not in _FUND_ACCT:
        for a in A.values():
            _FUND_ACCT.setdefault(a['fund'], a)
    a = _FUND_ACCT[f]
    name = J.grant_program(a)
    yy = re.match(r"\s*FY\s*'?(\d\d)", a['fund_name'])
    return '%s%s · %s' % (name, ', %s' % C.fy(2000 + int(yy.group(1))) if yy else '', f)


_FUND_ACCT = {}


def fund_names():
    """fund -> its name as the journal prints it."""
    out = {}
    for r in J.lines():
        out.setdefault(r['fund'], r['fund_name'].strip())
    return out


# Why a dollar is on no school line, in words a reader can use, beside its function code
NO_LINE = {'booked to a heading': 'a general heading',
           'booked to no function': 'no function code',
           'a function the general fund has no line for': 'no school line for this function'}


def where_text(kind, dest, names):
    if kind in ('payee', 'later', 'back'):
        return names.get(dest, dest)
    if kind == 'function':
        return S.CAT_LABEL[dest]
    if kind == 'none':
        return dest
    if kind == 'between':
        return 'between funds by journal entry'
    return 'a capital article'


def funds_data(m, T):
    """One row per fund per year: its spending in the six ways it can land, summing to its total."""
    A = J.accounts()
    fname = fund_names()
    names = {r['account']: line_name(r) for r in m['rows'] if r['account']}
    years = []
    for fy in YEARS():
        rows = []
        for (y, f), d in sorted(m['src'].items()):
            if y != fy:
                continue
            col = defaultdict(Decimal)
            for (kind, _), v in d.items():
                col[kind] += v
            col['total'] = sum(d.values(), D0)
            if all(round(v) == 0 for v in col.values()):
                continue
            # who paid, from the fund's own postings: fund 0100 holds the school budget AND the
            # Town's other general fund accounts, and only the second reach this table
            py = fund_group(m, A, fy, f)
            rows.append(dict(
                key=T.lit(f), name=T.lit(fund_label(f, A)), printed=T.lit(fname[f]), program=T.lit(py),
                cat=dict(PAYERS)[payer_group(py)] if payer_group(py) != 'gf' else 'General fund, outside the school budget',
                group=payer_group(py),
                n={k: round(fl(col[k]), 2) for k, _, _ in SRC_COLS},
                t={k: T.usd(col[k]) for k, _, _ in SRC_COLS}))
        years.append(dict(fy=T.fy(fy), rows=rows,
                          total=T.usd(sum((sum(d.values(), D0) for (y, _), d in m['src'].items() if y == fy), D0))))
    return dict(years=years, columns=[dict(id=k, label=l, means=w) for k, l, w in SRC_COLS],
                groups=[dict(id=g, label=l) for g, l in PAYERS if g != 'gf'],
                text=dict(source='Fund', category='Kind of fund', read=(
                    'Every fund other than the school budget that spent money on the schools this '
                    'year, and where each dollar went. Open a fund for what it paid for.'),
                    tab_where='Where it went', tab_what='What it bought', tab_rows='Every posting',
                    c_memo='Memo', c_to='Paid to', c_where='Where it went', c_amount='Amount', c_date='Date',
                    c_kind='Kind', c_account='Its account', all_kinds='Every kind of posting',
                    bought_note='Each payment once, under the fullest memo it carries; payroll by the account it paid.',
                    by_payee='Paid to', by_account='By its own account', went='Went to',
                    close='Close', loading='Loading…', failed='Could not load this year’s postings.',
                    none='None.', sum='Every fund', all_rows='postings shown',
                    all_cats='Every kind', scroll='More columns: scroll the table sideways',
                    filter='Filter by payee, memo, account or where it went',
                    tab_moves='Moved between funds', mv=MOVES_TEXT,
                    mv_classes=[dict(id=k, label=v) for k, v in MOVE_CLASS.items()]))


# WHICH SCHOOL LINES OTHER FUNDS PAID TOWARD (TJ, 27 October 2026: "which of the school budget
# lines were paid by non general fund money ... athletics lines XYZ - paid by FUND X - an
# amount"). The sister of the table of funds: the same placements, read by LINE. One row per
# school line and fund, and how we know -- a re-charge is in the journal; a payee or a function
# code is our match. A function-code match places money on a category, never on one line, and
# says so.
HOW_PLACED = [('later', 'Re-charged from the school budget',
               'The school budget paid the bills; a journal entry later put them on this fund. In the journal.'),
              ('back', 'Re-charged back to the school budget',
               'This fund paid first; a journal entry later put the bills on the school budget. Negative here.'),
              ('payee', 'Same vendor as the line',
               'The fund paid a vendor this line also pays. It may have bought something different '
               '-- read the memos and what the fund booked it as. Our match.'),
              ('function', 'Same function code, category only',
               'Spending with no payee to match -- payroll mostly -- under a function code of this '
               'category. Our match, and it cannot say which line.')]


def evidence(rows, T, n=6):
    """What a fund's postings on one line SAY: each payment once, under the fullest memo it has.
    MUNIS posts a purchase as three -- the order (POE, its memo whole), the invoice (API, the memo
    cut short) and, in the invoice's own journal entry, the order released (POL) -- so an invoice
    takes its order's memo through the release beside it: same journal, same vendor, same amount.
    An order still open at year end is listed as owed. -> [dict(memo, v, d)] largest first."""
    po = {}
    for r in rows:
        if r['source'] == 'POE':
            po.setdefault(r['doc_no'], r['description'].strip())
    rel = {}
    for r in rows:
        if r['source'] == 'POL':
            rel[(r['journal'], r['vendor'], -r['amt'])] = r['doc_no']
    by, when = defaultdict(Decimal), {}
    net = defaultdict(Decimal)
    for r in rows:
        if r['source'] in ORDERS:
            net[r['doc_no']] += r['amt']
            continue
        doc = rel.get((r['journal'], r['vendor'], r['amt']))
        memo = po.get(doc) or r['description'].strip() or 'no memo'
        by[memo] += r['amt']
        when[memo] = min(when.get(memo, r['effective_date']), r['effective_date'])
    for doc, v in net.items():
        if v:
            memo = '%s (still owed)' % (po.get(doc) or 'order')
            by[memo] += v
            when.setdefault(memo, '')
    out = sorted(((k, v) for k, v in by.items() if abs(v) >= Decimal('0.5')), key=lambda kv: -abs(kv[1]))
    return [dict(memo=T.lit(k), v=signed(T, v) if v < 0 else T.usd(v),
                 d=T.lit(long_date(when[k])) if when.get(k) else '') for k, v in out[:n]], max(0, len(out) - n)


def line_funds_data(m, T):
    A = J.accounts()
    fname = fund_names()
    line = {(r['fy'], r['account']): r for r in m['rows'] if r['account']}
    years = []
    for fy in YEARS():
        rows, check = [], defaultdict(Decimal)
        posted = defaultdict(list)                     # (fund, kind, where) -> its postings
        for (y, f), rs_ in m['src_rows'].items():
            if y == fy:
                for r, k, w in rs_:
                    posted[(f, k, w)].append(r)
        for (y, f), d in sorted(m['src'].items()):
            if y != fy:
                continue
            g = payer_group(fund_group(m, A, fy, f))
            if g == 'gf':
                continue
            for (kind, where), v in d.items():
                if kind not in ('later', 'back', 'payee', 'function') or not v:
                    continue
                check[(f, kind)] += v
                if kind == 'function':
                    cat, name, budget, cost = where, T.lit('%s, no single line' % S.CAT_LABEL[where]), None, None
                else:
                    r = line[(fy, where)]
                    cat, name = r['category'], T.lit(line_name(r))
                    budget = r['voted'] + r['transfers'] + r['carried_budget']
                    cost = r['all_funds_cost']
                ev, more = evidence(posted[(f, kind, where)], T)
                # what the FUND booked it as: its own accounts, largest first -- beside the school
                # line it was matched to, the plainest sign of a match that bought something else
                own = defaultdict(Decimal)
                for r in posted[(f, kind, where)]:
                    own['%s · %s' % (A[r['account']]['org_name'].strip().title(),
                                     A[r['account']]['account_description'].strip().title())] += r['amt']
                rows.append(dict(
                    memos=ev, more=more,
                    booked=[T.lit(k) for k, v in sorted(own.items(), key=lambda kv: -kv[1]) if v][:2],
                    cat=T.lit(S.CAT_LABEL[cat]), line=name, acct=T.lit(where if kind != 'function' else ''),
                    fund=T.lit(fund_label(f, A)), printed=T.lit(fname[f]), group=g, how=kind,
                    n=round(fl(v), 2), t=T.usd(v),
                    budget=T.usd(budget) if budget is not None else '',
                    share=T.lit('%d%%' % round(100 * v / cost)) if cost and v > 0 else ''))
        # the same money the table of funds shows, by fund and by kind, to the cent
        for (y, f), d in m['src'].items():
            if y != fy or payer_group(fund_group(m, A, fy, f)) == 'gf':
                continue
            for kind in ('later', 'back', 'payee', 'function'):
                want = sum((v for (k, _), v in d.items() if k == kind), D0)
                if want != check[(f, kind)]:
                    fail('FY%d fund %s %s: by line %s, by fund %s' % (fy, f, kind, check[(f, kind)], want))
        # ONE ROW PER LINE (TJ, 27 October 2026: "group lines together ... that are the same
        # school line, aggregates, but listing the funds paying it, with details available by
        # clicking"): the line's total from other funds, its share of the line's cost, and the
        # fund rows under it
        by = defaultdict(list)
        for r in rows:
            by[(r['cat'], r['line'], r['acct'])].append(r)
        groups = []
        for (cat, name, acct), rs in by.items():
            v = sum((Decimal(str(r['n'])) for r in rs), D0)
            lr = line.get((fy, acct)) if acct else None
            cost = lr['all_funds_cost'] if lr else None
            bud = (lr['voted'] + lr['transfers'] + lr['carried_budget']) if lr else None
            # AGAINST THE BUDGET (TJ, 27 October 2026: "'Percent of the budgeted amount' ... this
            # will highlight the lines that get subsidized by other sources"): other funds' money
            # as a share of what the school budget gave the line. Over 100% is more from other
            # funds than from the budget; a line budgeted at nothing has no share, and says so.
            pb = (v / bud) if bud and bud > 0 else None
            pv = (v / lr['voted']) if lr and lr['voted'] > 0 else None
            bw = budget_walk(lr, T) if lr else None
            groups.append(dict(cat=cat, line=name, acct=acct, n=round(fl(v), 2), t=T.usd(v),
                               budget=rs[0]['budget'], pb=round(fl(pb), 4) if pb is not None else None,
                               pv=round(fl(pv), 4) if pv is not None else None,
                               pv_t=T.lit('%s%%' % C.num(round(100 * pv))) if pv is not None
                               else (T.lit('not voted') if lr else ''),
                               bw=bw,
                               pb_t=T.lit('%s%%' % C.num(round(100 * pb))) if pb is not None
                               else (T.lit('no budget') if lr else ''),
                               share=T.lit('%d%%' % round(100 * v / cost)) if cost and v > 0 else '',
                               groups=sorted({r['group'] for r in rs}),
                               funds=sorted(rs, key=lambda r: -r['n'])))
        groups.sort(key=lambda g: (g['cat'], g['line']))
        total = sum((v for v in check.values()), D0)
        if abs(sum((Decimal(str(g['n'])) for g in groups), D0) - total) > Decimal('0.05'):
            fail('FY%d: the lines do not sum to what other funds paid toward them' % fy)
        years.append(dict(fy=T.fy(fy), lines=groups, total=T.usd(total), n_rows=len(rows)))
    return dict(years=years, how=[dict(id=k, label=l, means=w) for k, l, w in HOW_PLACED],
                groups=[dict(id=g, label=l) for g, l in PAYERS if g != 'gf'],
                text=dict(cat='Category', line='School line', fund='Fund', kind='Kind of fund',
                          how='How we know', paid='Paid toward it', budget='Final budget',
                          share='Share of the line’s cost',
                          of_budget='Against the final budget',
                          of_budget_means='What other funds paid toward the line, as a share of its '
                                          'final budget: voted, plus transfers, plus orders carried in. '
                                          'Over 100% means more came from other funds than the budget '
                                          'gave the line.',
                          of_voted='Against the vote',
                          of_voted_means='What other funds paid toward the line, as a share of what '
                                         'Town Meeting voted for it. Far above the final-budget share '
                                         'means transfers topped the line up during the year.',
                          changed='Changed after the vote',
                          changed_means=T.lit('Final budget less the vote: transfers and orders carried '
                                              'in. Flagged where it moved by half or more and by at '
                                              'least %s -- thresholds of ours.' % T.usd(ADJ_MIN)),
                          share_means='What this fund paid, as a share of everything the line cost from every fund.',
                          budget_means=T.lit('The line’s final budget: what was voted, plus or minus transfers, plus last year’s orders carried in. It ties to the Town’s period-13 report.'),
                          all_kinds='Every kind', filter='Filter by line, category or fund',
                          scroll='More columns: scroll the table sideways', sum='Every row',
                          lines='school lines', funds='funds', fund_one='fund', close='Close',
                          booked='The fund booked it as:', more='more payments',
                          open='Open a line for the funds that paid toward it'))


# OVERLAP (TJ, 27 October 2026: "these other sources of funds are complimenting or supplementing
# some aspects of the school budget and we can tell by the overlap ... calculate the supplement.
# which is a separate concept than the 'on no school line'"). Other funds' money in bands, from
# the strongest overlap with the school budget to none: the same bills, the same vendor, the same
# function code, cannot tell, and separate. Bills re-charged BACK are drawn apart, negative.
# Overlap is all the books can show. Whether it SUPPLEMENTED the school budget (paid for more)
# or SUPPLANTED it (paid what it would have paid) is what would have happened otherwise, which
# no ledger records -- the block says so, and never calls a dollar either.
BANDS = [('bills', 'The same bills', 'The school budget paid them; a journal entry put them on this fund.'),
         ('payee', 'The same vendor', 'Paid to a vendor the school budget also paid from a line; possibly for something else.'),
         ('code', 'The same function code', 'No payee to match, booked under a school line’s function code.'),
         ('unknown', 'Cannot tell', 'Booked to a general heading or to no function at all.'),
         ('separate', 'Separate', 'A function the school budget has no line for, or a capital article.')]


def band_of(kind, where):
    if kind == 'later':
        return 'bills'
    if kind == 'back':
        return 'back'
    if kind == 'payee':
        return 'payee'
    if kind == 'function':
        return 'code'
    if kind == 'capital' or (kind == 'none' and where == 'a function the general fund has no line for'):
        return 'separate'
    return 'unknown'


def fund_group(m, A, fy, f):
    """Who paid, from the fund's own postings (fund 0100 holds the school budget and the Town's
    other general fund accounts; only the second are other funds)."""
    pys = {FB.payer(A[r['account']]) for r, _, _ in m['src_rows'].get((fy, f), [])}
    if len(pys) != 1:
        fail('FY%d fund %s: its postings name %s payers' % (fy, f, sorted(pys) or 'no'))
    return pys.pop()


def overlap_data(m, T):
    A = J.accounts()
    keys = [b for b, _, _ in BANDS] + ['back']
    years = []
    for fy in YEARS():
        tot = defaultdict(Decimal)
        by = defaultdict(lambda: defaultdict(Decimal))
        for (y, f), d in m['src'].items():
            if y != fy:
                continue
            g = payer_group(fund_group(m, A, fy, f))
            for (kind, where), v in d.items():
                b = band_of(kind, where)
                tot[b] += v
                by[g][b] += v
        whole = sum(tot.values(), D0)
        if whole != sum((sum(d.values(), D0) for (y, _), d in m['src'].items() if y == fy), D0):
            fail('FY%d: the bands do not hold every other-fund dollar' % fy)
        over = tot['bills'] + tot['payee'] + tot['code']
        # on the school lines other funds paid toward: what the school budget paid (after
        # re-charges) and what other funds paid, so a re-charged bill is counted once
        ln = [r for r in m['rows'] if r['fy'] == fy and r['account'] and round(r['other_funds'], 2)]
        gf = sum((r['gf_spent'] for r in ln), D0)
        of = sum((r['other_funds'] for r in ln), D0)
        pack = lambda d: dict(n={k: round(fl(d[k]), 2) for k in keys}, t={k: T.usd(d[k]) for k in keys})
        years.append(dict(
            fy=T.fy(fy), all=pack(tot), whole=T.usd(whole), over=T.usd(over),
            over_pct=T.lit('%d%%' % round(over / whole * 100)) if whole else '',
            groups=[dict(id=g, **pack(by[g]), total=T.usd(sum(by[g].values(), D0)))
                    for g, _ in PAYERS if g in by],
            lines=dict(n=T.lit(str(len(ln))), gf=T.usd(gf), other=T.usd(of), cost=T.usd(gf + of),
                       gf_v=round(fl(gf), 2), other_v=round(fl(of), 2),
                       share=T.lit('%d%%' % round(of / (gf + of) * 100)) if gf + of else '')))
    return dict(years=years, bands=[dict(id=b, label=l, means=w) for b, l, w in BANDS],
                groups=[dict(id=g, label=l) for g, l in PAYERS if g != 'gf'],
                text=dict(
                    back='Re-charged back to the school budget',
                    back_means='This fund paid first; a journal entry put the bills back on the school budget.',
                    all='Every other fund', overlap='overlap with what the school budget pays for',
                    of='of', strong='Strongest overlap', none_='No overlap',
                    h_bands='How much of other funds’ money overlaps the school budget',
                    h_groups='By who paid', h_lines='On the school lines other funds paid toward',
                    lines_a='school lines', school='School budget, after re-charges',
                    other='Other funds', share='paid by other funds'))


def fund_texts(m):
    """/data/fy-breakdown/funds-<year>.json: per fund, where its money went (`w`: [kind, where,
    text, amount]), what it bought by its own account (`a`) and by payee (`p`), and every
    posting (`r`: [iso, date, kind, payee, memo, its account, went to, text, amount])."""
    names = {r['account']: line_name(r) for r in m['rows'] if r['account']}
    moved = {y['fy']: y['groups'] for y in moves_data(m, Texts())['years']}
    files = {}
    for fy in YEARS():
        body = {}
        for (y, f), d in sorted(m['src'].items()):
            if y != fy:
                continue
            # WHERE, IN PLAIN WORDS (TJ, 27 October 2026, of "booked to a heading": "a mistake in
            # the app" -- it said nothing): a school line by name, or "No school line" with the
            # function code the fund booked it under
            codes = defaultdict(set)
            for r, kind, dest in m['src_rows'].get((fy, f), []):
                codes[(kind, dest)].add(r['account'].split('-')[3])
            plain = lambda k, dest: (
                'No school line · function %s, %s' % ('/'.join(sorted(codes[(k, dest)])), NO_LINE[dest])
                if k == 'none' else where_text(k, dest, names))
            w = [[KIND_WHERE[k] if k != 'none' else '', plain(k, dest), money(v), round(fl(v), 2)]
                 for (k, dest), v in sorted(d.items(), key=lambda kv: -abs(kv[1])) if round(v, 2)]
            # WHAT IT BOUGHT: each payment once under its fullest memo (an invoice takes its
            # order's memo through the release in the same journal entry), who it was paid to,
            # and where it went
            rows_ = m['src_rows'].get((fy, f), [])
            po = {r['doc_no']: r['description'].strip() for r, _, _ in rows_ if r['source'] == 'POE'}
            rel = {(r['journal'], r['vendor'], -r['amt']): r['doc_no'] for r, _, _ in rows_ if r['source'] == 'POL'}
            bought = defaultdict(Decimal)
            for r, kind, dest in rows_:
                if r['source'] in ORDERS:
                    continue
                # payroll's memo is a warrant number; the account it paid says what it was
                memo = ('Payroll · %s' % r['org_name'].strip().title() if r['source'] in ('PRJ', 'PRH')
                        else po.get(rel.get((r['journal'], r['vendor'], r['amt']))) or r['description'].strip() or 'no memo')
                bought[(memo, payee(r) or KIND.get(r['source'], r['source']), plain(kind, dest))] += r['amt']
            owed = defaultdict(Decimal)
            for r, kind, dest in rows_:
                if r['source'] in ORDERS:
                    owed[(r['doc_no'], payee(r), plain(kind, dest))] += r['amt']
            for (doc, who, where), v in owed.items():
                if v:
                    bought[('%s (still owed)' % po.get(doc, 'order'), who or 'Order', where)] += v
            b = [[k[0], k[1], k[2], money(v), round(fl(v), 2)]
                 for k, v in sorted(bought.items(), key=lambda kv: -abs(kv[1])) if round(v, 2)]
            acct, pay = defaultdict(Decimal), defaultdict(Decimal)
            rs = []
            for r, kind, dest in m['src_rows'].get((fy, f), []):
                acct[r['account_description'].strip().title()] += r['amt']
                pay[payee(r) or KIND.get(r['source'], r['source'])] += r['amt']
                went = ('journal entry %s' % dest) if kind == 'journal' else plain(kind, dest) if kind == 'none' else '%s %s' % (
                    KIND_WHERE[kind], where_text(kind, dest, names))
                rs.append([r['effective_date'], long_date(r['effective_date']),
                           KIND.get(r['source'], 'Order' if r['source'] in ORDERS else r['source']),
                           payee(r), r['description'].strip(), r['account_description'].strip().title(),
                           went, money(r['amt']), round(fl(r['amt']), 2)])
            rs.sort(key=lambda x: (x[0], -abs(x[8])))
            srt = lambda dd: [[k, money(v), round(fl(v), 2)] for k, v in sorted(dd.items(), key=lambda kv: -abs(kv[1])) if round(v, 2)]
            body[f] = dict(w=w, b=b, a=srt(acct), p=srt(pay), r=rs)
            # the cost re-booked between this fund and another, as the page's block shows it
            mv = [g for g in moved.get(C.fy(fy), []) if f in g['funds']]
            if mv:
                body[f]['mv'] = mv
        files[os.path.join(LINES_DIR, 'funds-%d.json' % fy)] = json.dumps(
            dict(fy=C.fy(fy), funds=body), ensure_ascii=False, sort_keys=True,
            separators=(',', ':')) + '\n'
    return files


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
    fund on the other side. `recharge`: (journal, part) -> (verb, funds, ...), `is_recharge`."""
    out, orders = [], defaultdict(list)
    for r in rows:
        if r['source'] in ORDERS:
            orders[r['doc_no']].append(r)
            continue
        if recharge and is_recharge(r, recharge):
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
    for (j, _), (verb, funds, v, d, memo) in (recharge or {}).items():
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
                recharge[(mv['journal'], mv['part'])] = (verb, funds, mv['amount'], mv['date'], mv['memo'])
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
    payee_of = lambda x: x['p'] or x['k']
    memo_of = lambda x: memo_key(x['m'])
    rows_text = lambda n: '%s %s' % (C.num(n), 'row' if n == 1 else 'rows')

    def bars(label, other):
        """Bars by `label`, each [name, rows, [[fund, amount]], total, filter key, what it was
        for]: under a payee, its memos; under a memo, its payees (TJ: "what are we paying FLLAC
        for?!" and "who are we paying to do THAT MEMO")."""
        tot = defaultdict(lambda: defaultdict(Decimal))
        cnt = defaultdict(int)
        sub = defaultdict(lambda: defaultdict(Decimal))
        subn = defaultdict(lambda: defaultdict(int))
        for x in spend:
            k = label(x)
            if k:
                tot[k][x['f']] += x['v']
                cnt[k] += 1
                o = other(x) or '(no memo)'
                sub[k][o] += x['v']
                subn[k][o] += 1
        order = sorted(tot, key=lambda k: -sum(tot[k].values()))
        top, rest = order[:TOP], order[TOP:]
        out = [[k, rows_text(cnt[k]), [[fi[f], round(fl(v), 2)] for f, v in sorted(tot[k].items())],
                money(sum(tot[k].values(), D0)), k,
                [[o, rows_text(subn[k][o]), money(v)] for o, v in
                 sorted(sub[k].items(), key=lambda kv: -abs(kv[1]))[:4]]] for k in top]
        if rest:
            agg = defaultdict(Decimal)
            for k in rest:
                for f, v in tot[k].items():
                    agg[f] += v
            out.append(['%s more' % C.num(len(rest)), rows_text(sum(cnt[k] for k in rest)),
                        [[fi[f], round(fl(v), 2)] for f, v in sorted(agg.items())],
                        money(sum(agg.values(), D0)), '', []])
        return out, cnt
    payees, _ = bars(payee_of, memo_of)
    memos, mc = bars(memo_of, payee_of)
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


def popup_moves(m):
    """fy -> line key -> what the popup's Transfers and re-charges tab lists that the table does
    not show: `m`, the budget transfers with their other sides; `j`, journal entries re-booking
    spending between school lines. In the line files rather than the page payload, where they
    were half of its two megabytes and read only when a line is opened."""
    T = Texts()                 # a line file is data, like its expense rows; not digit-checked
    names = {r['account']: line_name(r) for r in m['rows'] if r['account']}
    entries = school_entries()
    out = defaultdict(dict)
    for r in m['rows']:
        if not r['account']:
            continue
        mv, j = move_rows(T, r['moves_in'], names), entry_rows(T, r, entries, names)
        if mv or j:
            out[r['fy']][line_key(r)] = dict(m=mv, j=j)
    return out


def line_texts(m):
    """The files, compact. Funds and kinds are indexed. Per line: `r`, each row [iso date, date,
    kind, payee, memo, reference, fund, amount as text, amount]; `t`, what each fund paid in
    all, [fund, text, amount]; `g`, by payee and fund, [payee, fund, rows, text, amount]."""
    files = {}
    moves = popup_moves(m)
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
                    fi[x['f']], money(x['v']), round(fl(x['v']), 2), memo_key(x['m'])]
                   for x in sorted(rs, key=lambda x: (x['d'] or '9', -abs(x['v'])))],
                t=[[fi[f], money(v), round(fl(v), 2)] for f, v in
                   sorted(tot.items(), key=lambda kv: (kv[0] != SCHOOL, -abs(kv[1])))],
                g=[[p_, fi[f], cnt[(p_, f)], money(v), round(fl(v), 2)] for (p_, f), v in
                   sorted(grp.items(), key=lambda kv: -abs(kv[1]))])
        files[os.path.join(LINES_DIR, 'lines-%d.json' % fy)] = json.dumps(
            dict(fy=C.fy(fy), funds=funds, kinds=kinds, lines=body, mv=moves.get(fy, {})), ensure_ascii=False,
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


def web_files(m):
    return WEB.files(m, line_name, fund_label, fund_group, payer_group, S.CAT_LABEL, money, LINES_DIR, fail)


WEB_KINDS = [
    ('paid', 'Paid from the start', 'The fund paid toward the line itself; our match, by the same payee'),
    ('later', 'Re-charged later', 'The school budget paid, then the bill was re-charged to the fund by journal entry'),
    ('back', 'Moved back', 'A bill the fund had paid was moved back onto the school budget'),
    ('kind', 'Same kind of work', 'Our match by function code, to a category, never to one line'),
    ('none', 'On no school line', 'Spending the books give no school line'),
    ('capital', 'Capital articles', 'A capital article’s own project'),
    ('fund', 'Cost re-booked to another fund', 'A journal entry re-booked a cost already paid from '
             'one fund to another; the arrow runs the way the cost moved, from the fund that gave it '
             'up to the fund that took it on'),
    ('between', 'Between funds', 'The rest of what was moved from one fund to another by journal '
                'entry, where the books do not pair the two'),
    ('transfer', 'Budget transfers', 'Budget moved from one line to another; budget, not spending'),
    ('school', 'School budget’s own spending', 'What the school budget spent on each line, after re-charges'),
]


def web_data(T):
    return dict(years=[T.fy(y) for y in YEARS()],
                kinds=[dict(id=k, label=l, means=w) for k, l, w in WEB_KINDS],
                text=dict(only_touched='Only lines other funds touched', gf_only='general fund only', zoom_in='Zoom in', zoom_out='Zoom out',
                          fit='Fit', how='Drag to move · ctrl + scroll to zoom · a block to focus its arrows',
                          loading='Loading…', failed='Could not load this year’s web.',
                          col_funds='Funds', col_sinks='Not on a school line', a_fund='Fund',
                          a_line='School line', a_sink='Not on a school line', clear='Clear',
                          pick='Hover or tap a block to see every arrow in and out of it, with amounts.',
                          rank='Order lines by', rank_size='Size', rank_sources='Most sources',
                          rank_share='Most from other funds',
                          key_many=T.lit('funds connected; filled at 3 or more (our threshold)'),
                          key_big=T.lit('share paid by other funds; strong at 25% or more (our threshold)'),
                          st_sources='funds other than the general fund',
                          st_share='of its cost paid by other funds',
                          find='Find a line or fund', found='found',
                          only_gf='Paid by the general fund alone this year: no other fund touched it.'))


MOVE_CLASS = {'award': 'Same grant, another year’s award', 'grant': 'Grant to another grant',
              'grant-revolving': 'Grant and a revolving or lunch fund', 'circuit-breaker': 'Circuit breaker',
              'general-fund': 'General fund outside the school budget', 'other': 'Between other funds',
              'unpaired': 'Not paired in the books'}


MOVES_TEXT = dict(
    lead='re-booked between funds by journal entry in', entries='entries', entry='entry',
    award_lead='between awards of the same grant', undone_lead='in entries that undo each other',
    what=('A journal entry re-books a cost already paid -- by payroll or a bill -- from one fund to '
          'another. No cash moves; the books change which fund carries the cost.'),
    cancels='Cancelled out: reversed in the same year',
    later='to a later award', earlier='to an earlier award', c_journal='Journal entry',
    school='The same entry also moved cost on or off a school line.',
    unpaired=('Several funds gave and several took, in amounts that do not match: the books do not say '
              'which cost went where.'),
    none='No cost was re-booked between two funds this year.',
    open='Open a row for its entries')


def moves_data(m, T):
    """COST RE-BOOKED BETWEEN FUNDS (TJ, 28 October 2026: "we also need to show that grant money is
    moved across years too.... FY25 moving to FY26 grants"). Every entry in the model's
    `fund_moves_between`, grouped by the two funds it moved cost between, so one grant's award-to-
    award moves read as one row: from, to, net, how many entries; each entry beneath it with its
    date, memo and journal, and a reversal marked on both ends. An entry the books do not pair
    (several funds gave, several took) is its own group, named so."""
    A = J.accounts()
    # fund 0100 outside department 300 is the Town's side of the general fund, as the table of funds names it
    name = lambda f: fund_label(f, A) if f != '0100' else 'General fund, outside the school budget · 0100'
    years = []
    for fy in YEARS():
        mvs = [e for e in m['fund_moves_between'] if e['fy'] == fy]
        date_of = {e['id']: long_date(e['date']) for e in m['fund_moves_between']}
        groups = defaultdict(list)                 # key -> [(entry, gave, got, amount, cls, dir)]
        for e in mvs:
            for p in e['pairs']:
                groups[tuple(sorted((p['gave'], p['got'])))].append((e, p['gave'], p['got'], p['amount'], p['cls'], p['dir']))
            if not e['paired']:
                groups[('unpaired', e['id'])].append((e, None, None, e['moved'], 'unpaired', None))
        out = []
        for k, items in groups.items():
            cls = items[0][4]
            if cls == 'unpaired':
                e = items[0][0]
                a = T.lit(' · '.join(name(f) for f in sorted(e['unpaired_gave'])))
                b = T.lit(' · '.join(name(f) for f in sorted(e['unpaired_got'])))
                net, x, y, dir_ = e['moved'], None, None, None
            else:
                x, y = k
                net = sum((v if g == x else -v for _, g, _, v, _, _ in items), D0)
                if net < 0 or (net == 0 and items[0][1] == y):
                    x, y, net = y, x, -net
                a, b = T.lit(name(x)), T.lit(name(y))
                dir_ = move_class_dir(x, y)
            rows = []
            for e, g, r, v, _, _ in sorted(items, key=lambda it: (it[0]['date'], it[0]['id'])):
                rev = (T.lit('reverses the entry of %s' % date_of[e['reverses']]) if e['reverses']
                       else T.lit('reversed by the entry of %s' % date_of[e['reversed_by']]) if e['reversed_by'] else '')
                rows.append(dict(
                    d=T.lit(long_date(e['date'])), iso=T.lit(e['date']), memo=T.lit(' · '.join(e['memos'])),
                    j=T.lit(e['journal']), rev=rev, school=e['with_school'],
                    a=T.lit(name(g)) if g else a, b=T.lit(name(r)) if r else b,
                    t=T.usd(v), n=round(fl(v), 2)))
            prog = FB.payer(FB.fund_acct(x)) if cls == 'award' else ''
            out.append(dict(cls=cls, prog=T.lit(prog), a=a, b=b, dir=dir_, t=T.usd(net), n=round(fl(net), 2),
                            cancels=net == 0, count=len(rows),
                            gross=T.usd(sum((v for _, _, _, v, _, _ in items), D0)), rows=rows,
                            funds=sorted(k if cls != 'unpaired' else
                                         set(items[0][0]['unpaired_gave']) | set(items[0][0]['unpaired_got']))))
        order = list(MOVE_CLASS)
        out.sort(key=lambda g: (order.index(g['cls']), g['prog'], -abs(g['n']), g['a']))
        moved = sum((e['moved'] for e in mvs), D0)
        award = sum((p['amount'] for e in mvs for p in e['pairs'] if p['cls'] == 'award'), D0)
        if abs(sum((Decimal(str(r['n'])) for g in out for r in g['rows']), D0) - moved) > Decimal('0.01') * (len(mvs) + 1):
            fail('FY%d: the moves between funds do not sum to what the entries moved' % fy)
        undone = sum((e['moved'] for e in mvs if e['reverses'] or e['reversed_by']), D0)
        years.append(dict(fy=T.fy(fy), groups=out, n=len(mvs), t=T.usd(moved), t_award=T.usd(award),
                          t_undone=T.usd(undone) if undone else '',
                          n_award=sum(1 for e in mvs if any(p['cls'] == 'award' for p in e['pairs']))))
    return dict(years=years, classes=[dict(id=k, label=v) for k, v in MOVE_CLASS.items()], text=MOVES_TEXT)


def move_class_dir(a, b):
    return FB.move_class(a, b)[1]


def salaries_data(m, T):
    return dict(years=SAL.data(m, T, line_name, fund_label, S.CAT_LABEL, long_date, fail),
                links=[dict(href='/school-all-funds/pay-from-grants-and-fees', label='Pay from grants and fees'),
                       dict(href='/school-all-funds/pay-moved-between-funds', label='Pay moved between funds')],
                text=dict(
        lead='of school pay ended on funds other than the general fund in', of_all='of all school pay',
        how='How it got there:',
        s_run='paid directly by those funds, never on the general fund',
        s_took='paid by the general fund first, then re-charged off school salary lines to them',
        s_gave='they paid first, then moved back onto the general fund’s salary lines',
        s_between='moved between other funds, net',
        s_adj='other entries, net',
        tab_lines='School salary lines', tab_funds='By fund',
        lines_read=('General fund salary lines where a year-end journal entry moved pay to or from another '
                    'fund. A re-charge is not a payment back: the general fund paid, and the entry moved the '
                    'cost onto the grant, so the grant covers it and the line goes down. Open a line for its entries.'),
        funds_read=('Every other fund’s pay, by how it got there. Most was paid directly by the fund and '
                    'never touched the general fund. Open a fund for the kinds of work it was booked to.'),
        c_line='School line', c_cat='Category', c_before='General fund paid', c_off='Re-charged to other funds',
        c_on='Moved back from other funds', c_kept='General fund kept', c_share='% kept',
        m_before=('What the general fund paid on this line, before any year-end entry moved pay to or from '
                  'another fund. The same measure as General fund paid in Who the schools paid.'),
        m_off=('The general fund paid this pay, then a journal entry moved the cost to a grant or fee fund. '
               'No money is paid back: the entry moves the expense, so the fund covers it and the line goes down.'),
        m_on=('Another fund paid this pay directly, then a journal entry moved the cost onto this line, so '
              'the general fund covers it.'),
        m_kept='What the general fund carried on the line in the end: paid, less re-charged, plus moved back.',
        m_share=('General fund kept over general fund paid, the same measure as % general fund kept in Who '
                 'the schools paid. Under 100% is pay other funds took; over 100% is pay it took on from them.'),
        carried='other funds took some', took_on='took on other funds’ pay',
        entries='The entries', to='to', no_lines='No salary line had pay moved this year.',
        c_fund='Fund', c_run='Paid directly by the fund', c_moved='Moved by journal entry, net',
        c_adj='Other entries', c_total='Its pay in the end',
        m_run=('Pay this fund paid directly. It was never on the general fund. Its accounts name a kind '
               'of work, never a post, so it cannot be pinned to one school line.'),
        m_moved=('Pay moved onto this fund by journal entry, less pay moved off it. The other side can be '
                 'a general fund salary line (a re-charge, or a move back, in the other tab) or another '
                 'fund. Below zero, it handed more back than it took.'),
        m_adj='Entries on its pay accounts that are not moves between funds: accruals, reversals, an invoice.',
        m_total='Paid directly, plus moved by journal entry, plus other entries.',
        kinds='What it paid directly, by what it was booked to:',
        tab_regular='Paid every pay period',
        regular_read=T.lit('Accounts outside the general fund that pay a steady amount run after run: at least 8 '
                           'pay runs within 25% of the account’s own typical run (our thresholds). That is what a '
                           'post looks like in a payroll that never names people; season-end stipends show as '
                           'lumps. Open one for every run and any entry that moved its pay onto a general fund line.'),
        c_account='Fund and account', c_steady='Steady runs', c_typical='Typical run', c_steady_total='Steady pay',
        c_rest='Other pay', c_total_pay='All its pay',
        m_steady='Pay runs within 25% of the typical run: the steady part, a payment made every period.',
        m_typical='The median of the runs it paid: what one period of the steady payment looks like.',
        m_steady_total='The steady runs added up: a floor on what the regular payment cost this year, since part runs are left out.',
        m_rest='Everything else on the account: season-end stipends, part runs, adjustments.',
        has_moves='pay moved onto a general fund line',
        runs_note='Every pay run, in order, by warrant:', moves_h='Pay moved onto general fund lines by journal entry',
        no_moves_r='No journal entry moved its pay to or from a general fund line this year.', from_='from',
        limit=T.lit('Pay is wages, object 51, less benefits; the same definition as'),
        **{'from': 'from'}))


def payee_files(m):
    return PY.files(m, line_name, fund_label, money, long_date, LINES_DIR, fail)


def payees_data(m, T):
    """The block's own payload: per year, how many were paid, how many new and how many not paid
    again. The rows are in /data/fy-breakdown/payees-<year>.json (fy_payees.py)."""
    _, summary = payee_files(m)
    years = [dict(fy=T.fy(s['fy']), prev=T.fy(s['prev']) if s['prev'] else None, n=s['n'], new=s['new'],
                  dropped=s['dropped'], total=T.usd(s['total']), new_total=T.usd(s['new_total']),
                  dropped_total=T.usd(s['dropped_total']), gf=T.usd(s['gf']),
                  gf_share=T.lit('%d%%' % s['gf_share'].quantize(Decimal(1))),
                  kept=T.usd(s['kept']), kept_share=T.lit('%d%%' % s['kept_share'].quantize(Decimal(1))),
                  back=T.usd(s['back'])) for s in summary]
    return dict(years=years, show=30, text=dict(
        payee='Payee', payees='payees', change='Change', gf='General fund paid', gf_share='% general fund paid',
        gf_of='paid by the general fund', kept='General fund kept', kept_share='% general fund kept',
        kept_of='kept after re-charges', ours='our allocation',
        kept_means=('Of what this payee was paid, the share the general fund still carried after re-charges. '
                    'Re-charges are posted to a line, not an invoice, so each line’s re-charged share '
                    'is applied to every payment on it: our allocation.'),
        back_l='moved back onto the general fund from other funds, not spread over payees', payments='Payments', paid_in='payees paid in',
        new='New this year', dropped='Not paid this year', new_l='new', dropped_l='not paid again',
        every='Every payee', in_='in', filter='Filter by payee, memo or line', open='Open a payee for what was bought',
        loading='Loading…', failed='Could not load this year’s payees.', close='Close', more_lines='more',
        show_all='Show all', show_fewer='Show the first', rows_shown='rows shown',
        no_prev='the journal starts this year, so there is no year before to compare',
        tab_what='What was bought', tab_lines='Lines and funds', tab_rows='Every payment',
        what_note='each payment under the fullest memo it carries, summed by memo and line',
        lines_note='A school line is the school budget; any other is the fund’s own account, with the fund named.',
        shown_before='Not paid this year. Shown: what it was paid in', school='School budget',
        c_memo='Memo', c_line='Line or account', c_fund='Fund', c_amount='Amount', c_date='Date',
        grain=('General fund is fund 0100: the school budget and the district’s curriculum accounts. '
               'Kept is after re-charges, our allocation by line; budget transfers move budget, not '
               'payments, so they do not change it. '
               'Payments by invoice, in the year they were posted, from every school fund. Not pay, '
               'not orders still owed, and not what the Town charges the schools by journal entry -- '
               'health premiums among it -- so a payee whose bills moved to journal entries shows a '
               'drop that is not a cut. New and not paid again compare with the year before only.'),
        **{'in': 'in'}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    m = FB.model()
    outs = {OUT: render(m), **line_texts(m), **fund_texts(m), **payee_files(m)[0], **web_files(m)}
    # one page per school line and per fund, sliced from the outputs above (fy_items.py)
    outs.update(ITEMS.files(m, outs, OUT, LINES_DIR, money, fail, plan={COLLAB: printed_plan(m)}))
    gone = ITEMS.orphans(LINES_DIR, outs)
    if a.check:
        stale = [os.path.relpath(p, ROOT) for p, text in outs.items()
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != text]
        stale += ['%s (no longer written)' % os.path.relpath(p, ROOT) for p in gone]
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('fy breakdown: current')
        return 0
    for p in gone:                     # a slug that no longer exists: its file goes too
        os.remove(p)
        print('removed %s' % os.path.relpath(p, ROOT))
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
