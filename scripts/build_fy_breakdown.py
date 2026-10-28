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

ID = 'fy-breakdown'
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % ID)
# Every row behind every line, one file a year, fetched when a line is opened (TJ, 27 October
# 2026: "show all the journal entry rows for the line in 'expenses' tab ... what the out of
# district tuition spend was spent on, line by line, and what source paid it").
LINES_DIR = os.path.join(ROOT, 'fy28', 'public', 'data', 'fy-breakdown')
SCHOOL = 'School budget'
Y0, Y1 = 2025, 2026
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


def school_entries():
    """(fy, journal) -> the school lines' postings in every journal entry (GEN/GRV), for the
    entries that re-book spending between school lines rather than to another fund."""
    A = J.accounts()
    out = defaultdict(list)
    for r in J.lines():
        if r['source'] in ('GEN', 'GRV') and J.is_expense(A[r['account']]):
            out[(r['fy'], r['journal'])].append(r)
    return out


def entry_rows(T, r, entries, names):
    """A line's journal entries that are not re-charges to or from another fund: spending
    re-booked between school lines, a correction, an accrual. Each: date, memo, what this line
    gained or lost, and the other school lines in the entry -- or that the other side is
    outside the school's books."""
    if not r['account']:
        return []
    rech = {mv['journal'] for mv in r['fund_moves']}
    A = J.accounts()
    out = []
    mine = defaultdict(Decimal)
    for (fy, j), rs in entries.items():
        if fy != r['fy'] or j in rech:
            continue
        v = sum((x['amt'] for x in rs if x['account'] == r['account']), D0)
        if v:
            mine[j] = v
    for j, v in sorted(mine.items(), key=lambda kv: min(x['effective_date'] for x in entries[(r['fy'], kv[0])])):
        rs = entries[(r['fy'], j)]
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


def lines_data(m, T):
    """Every line, every year, as two sums. The school budget's own, to what was left, with
    cost moved by journal entry shown apart from what it spent; and what the line cost from
    every fund, where a move and a grant paying directly are two different terms. TJ, 26
    October 2026: "money added from other funds REDUCES the general fund... depends how its
    done doesnt it?" It does: a move changes Left, paying directly does not."""
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
                chip_n=chip_counts(T, r))
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


def year_facts(m, T):
    """THE YEAR IN FIGURES, for every year, switched by the page's picker (TJ, 27 October 2026:
    "make the facts and conclusions switch with the year"). Each fact is a figure the model
    computes; each conclusion states two of them side by side and what follows, nothing about
    why (rule 7)."""
    monday = lambda d: d - timedelta(days=d.weekday())
    files = line_files(m)
    out = []
    for fy in J.YEARS:
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
    for fy in J.YEARS:
        rs = [r for r in m['rows'] if r['fy'] == fy and r['account']]
        tot = lambda k: sum((r[k] for r in rs), D0)
        end, prev, nxt = date(fy, 6, 30), fy - 1, fy + 1
        carried, unpaid, early = tot('carried_budget'), tot('carried_unpaid'), tot('prepaid')
        carried_spent = tot('other_year_spent') - early
        if carried_spent + unpaid != carried:
            fail('FY%d: carried in %s is not paid %s plus never paid %s'
                 % (fy, carried, carried_spent, unpaid))
        out_owed = sum((v for (y, _), v in owed.items() if y == fy), D0)
        if nxt in J.YEARS:
            want = sum((r['carried_budget'] for r in m['rows'] if r['fy'] == nxt and r['account']), D0)
            if out_owed != want:
                fail('FY%d: owed on 30 June %s, carried into FY%d %s' % (fy, out_owed, nxt, want))
        if prev in J.YEARS:
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
        if prev in J.YEARS:
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
                          'budget for them.' + ('' if nxt in J.YEARS else T.lit(
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
    y26 = next(y for y in years if y['fy'] == C.fy(2026))
    if next(o for o in y26['out'] if o['id'] == 'early')['n'] < 189000:
        fail('the FY2026 tuition paid early is no longer on the year line')
    return dict(years=years, text=dict(h_in=T.lit('Came in across 1 July'), h_out=T.lit('Went out across 30 June'),
                                       from_='from', to='to', unread='cannot be read'))


def page(m):
    mv = lambda y:sum((x['off'] - x['onto'] for x in m['moves'] if x['fy'] == y), D0)
    mv0, mv1 = mv(Y0), mv(Y1)
    if not mv0 < 0 < mv1:
        fail('the page says re-charges ran onto the school budget in FY%d and off it in FY%d'
             % (Y0, Y1))
    f = LD.fact
    left = {y: m['years'][y]['left'] for y in J.YEARS}

    def con(text, rests, figs, so):
        return TP.conclusion(text, rests, figs, so=so[0], so_figures=so[1], so_allow=so[2])
    # The page's own facts and conclusions compare the years, so they hold whichever year the
    # picker shows; each year's own are in the block it switches (year_facts).
    facts = [f('left%d' % y, U(left[y]), 'left on the school lines, %s' % C.fy(y), 'published',
               label_figures={'y': F(y)}) for y in J.YEARS] + [
        f('moved1', U(mv1), 'taken off the school budget by re-charges, %s, net' % C.fy(Y1),
          'published', label_figures={'y': F(Y1)}),
        f('moved0', U(-mv0), 'added to it by re-charges, %s, net' % C.fy(Y0), 'published',
          label_figures={'y': F(Y0)})]
    conclusions = [
        con('The school lines left %s and %s in %s and %s, then %s and %s.'
            % (C.usd(fl(left[2023])), C.usd(fl(left[2024])), C.fy(2023), C.fy(2024),
               C.usd(fl(left[2025])), C.usd(fl(left[2026]))),
            ['left2023', 'left2024', 'left2025', 'left2026'],
            {'a': U(left[2023]), 'b': U(left[2024]), 'x': F(2023), 'z': F(2024),
             'c': U(left[2025]), 'd': U(left[2026])},
            so=('Two years near nothing, then two near half a million. Each year’s own figures, '
                'above, show what moved in it.', None, ())),
        con('Re-charges added %s to the school budget’s spending in %s and took %s off in %s.'
            % (C.usd(fl(-mv0)), C.fy(Y0), C.usd(fl(mv1)), C.fy(Y1)), ['moved0', 'moved1'],
            {'a': U(-mv0), 'y': F(Y0), 'b': U(mv1), 'z': F(Y1)},
            so=('A swing of %s between two years, made by entries after the spending; the bills '
                'cost the same either way.' % C.usd(fl(mv1 - mv0)), {'s': U(mv1 - mv0)}, ())),
    ]
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
    if {mv['date'][5:7] for mv in m['moves'] if mv['fy'] == Y1} != {'06'}:
        fail('the weekly chart says every %d re-charge was in June' % Y1)
    return TP.page(
        ID,
        'The school lines left %s in %s and %s in %s; pick a year to see what moved in it.'
        % (C.usd(fl(left[2023])), C.fy(2023), C.usd(fl(left[Y1])), C.fy(Y1)),
        facts, conclusions,
        chart=TP.series(
            'What the school lines left, by year', [C.fy(y) for y in J.YEARS],
            [TP.track('Left, orders still owed counted', [fl(m['years'][y]['left']) for y in J.YEARS],
                      'published', 'bar')], '$', kind='bar',
            note='School general fund, department 300. Every line’s Left in the table above, '
                 'summed.', note_allow=('300',)),
        blocks=[
            TB.custom('fy-year-picker', 'Fiscal year', dict(
                bare=True, years=[C.fy(y) for y in J.YEARS], label='Change year',
                spans={C.fy(y): '1 July %d to 30 June %d' % (y - 1, y) for y in J.YEARS}),
                      place='top', figures=[C.fy(y) for y in J.YEARS],
                      allow=['1 July %d to 30 June %d' % (y - 1, y) for y in J.YEARS],
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
            TB.custom('fy-overlap', 'Overlap with the school budget', overlap, place='top',
                      figures=sorted(T.figures), allow=sorted(T.literals),
                      basis=('reading', 'Our matching of other funds’ spending to school lines'),
                      alt='Bar chart, one fiscal year: other funds’ spending in bands from the '
                          'strongest overlap with the school budget (the same bills, the same payee, '
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
        finding_figures={'a': U(left[2023]), 'x': F(2023), 'b': U(left[Y1]), 'y': F(Y1)},
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
    for fy, book in PLAN_BOOKS.items():
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
    for fy in J.YEARS:
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
        steps = [('gf', -left, 'General fund left unspent' if left >= 0 else 'General fund spent past its budget',
                  'Its budget less what it spent, after bills were re-charged to and from other funds.'),
                 ('cb', cb_step, ('Circuit breaker, counted on and not charged' if cb_step < 0
                                  else 'Circuit breaker, charged beyond what was counted on')
                  if offset is not None else 'Circuit breaker, which the book did not count on',
                  'Charged to collaborative tuition, against the offset the year’s book printed.'
                  if offset is not None else 'This year’s book printed no offset, so all of it is beyond the plan.'),
                 ('other', other_on, 'Other funds, toward school lines',
                  T.lit('Grants, fees and other funds, on the same lines the budget pays for; %s of it '
                        're-charged from the school budget after it paid.' % T.usd(sum(later.values(), D0)))),
                 ('none', unm, 'Other funds, on no school line',
                  'School spending the books give no school line for: we cannot say which line it paid toward.')]
        if planned + sum((v for _, v, _, _ in steps), D0) != happened + unm:
            fail('FY%d: the bridge does not land on what happened' % fy)
        bridge = [dict(id=i, n=fl(v), v=('+' if v > 0 else '−' if v < 0 else '') + T.usd(abs(v)),
                       label=l, means=w) for i, v, l, w in steps]
        years.append(dict(
            bridge=bridge,
            fy=T.fy(fy), book=T.lit('/docs/district-budget/docs/%s.pdf' % pl['book']),
            book_line=T.lit(str(pl['line'])), raw=[T.lit(x) for x in pl['raw']],
            gf=dict(budget=fl(budget), before=fl(before), off=fl(off), on=fl(on), spent=fl(spent),
                    left=fl(left), early=fl(early), unspent=fl(gf_un),
                    t=dict(early=T.usd(early), own=T.usd(spent - early), unspent=T.usd(gf_un), used=T.usd(budget - gf_un), budget=T.usd(budget), before=T.usd(before), off=T.usd(off),
                           on=T.usd(on), spent=T.usd(spent), left=T.usd(left),
                           under=T.usd(budget - before), voted=T.usd(tot(lambda r: r['voted'])),
                           transfers=T.usd(tot(lambda r: r['transfers'])),
                           carried=T.usd(tot(lambda r: r['carried_budget'])))),
            cb=dict(plan=None if offset is None else fl(offset), paid=fl(cb_collab), unspent=fl(cb_un),
                    t=dict(plan=None if offset is None else T.usd(offset), paid=T.usd(cb_collab),
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
        none_printed='The book printed no offset', charged='charged', charged_of='charged of',
        r_other='Other funds', not_printed='No book printed these as part of the plan',
        from_start='paid from the start', later='re-charged after the school budget paid',
        unmatched_note='Hatched: {v} of it is on no school line; we cannot say which line it paid toward.',
        h_plan='The plan', voted='Voted', transfers='Transfers in or out',
        carried='Last year’s orders carried in',
        collab_gross='Collaborative tuition, before the offset', collab_net='Collaborative tuition, voted',
        none='none printed', h_gf='The school general fund',
        under='Budget less spent before re-charges', spent='Spent, after re-charges',
        left_row='Left', charged_row='Charged to the circuit breaker',
        cb_diff='Charged, against what was counted on',
        of_later='of which re-charged after the school budget paid',
        other_total='Other funds, toward the school lines', other_all='Other funds, everything spent',
        all_total='Everything spent, every fund',
        beyond_row='Beyond the plan',
        unmatched_row='Other funds, on no school line',
        printed='The lines as the year’s book prints them',
        h_abs='In dollars', h_diff='From the plan to what happened', bridge_cut='The two totals are cut short at the left, so the steps between them show.',
        a_plan='The plan', a_plan_sub='Budget, and the circuit breaker the book counted on',
        a_happened='What happened', a_happened_sub='Every school dollar spent, by who paid',
        a_beyond='beyond the plan', on_no_line='on no school line',
        unmatched_row_note='hatched in the charts',
        a_gf_budget='School general fund budget', a_gf_spent='School general fund, after re-charges',
        a_gf_early='School general fund, next year’s tuition paid early',
        a_gf_unspent='School general fund, unspent', a_cb_unspent='Circuit breaker, counted on, not charged',
        a_gf_used='School general fund budget, spent', a_cb_used='Circuit breaker, counted on and charged',
        a_unspent='unspent', a_unspent_sub='Outlined at the end: planned and not spent',
        a_unspent_note=('Unspent is shown for the school general fund and the circuit breaker the book '
                        'counted on, the two with an allocation for the year. Most grants and '
                        'revolving funds print no budget for the year, so theirs is not drawn.'),
        a_cb_plan='Circuit breaker, counted on', a_cb_paid='Circuit breaker, collaborative tuition', book='Approved budget book', line='line')
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
SRC_COLS = [('payee', 'Same payee as a school line',
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
            ('none', 'On no school line',
             'School spending the books give no school line for: a function the school budget has '
             'no line for, a general heading, no function at all, or the rest of a journal entry.'),
            ('total', 'Total', 'Everything this fund spent in the year, orders still owed counted.')]
KIND_WHERE = {'payee': 'same payee as', 'function': 'same function code as', 'later': 're-charged from',
              'back': 're-charged back to', 'capital': 'capital article', 'none': 'on no school line',
              'between': 'on no school line'}


def fund_names():
    """fund -> its name as the journal prints it."""
    out = {}
    for r in J.lines():
        out.setdefault(r['fund'], r['fund_name'].strip())
    return out


def where_text(kind, dest, names):
    if kind in ('payee', 'later', 'back'):
        return names.get(dest, dest)
    if kind == 'function':
        return S.CAT_LABEL[dest]
    if kind == 'none':
        return dest
    if kind == 'between':
        return 'moved between funds by journal entry'
    return 'a capital article'


def funds_data(m, T):
    """One row per fund per year: its spending in the six ways it can land, summing to its total."""
    A = J.accounts()
    fname = fund_names()
    names = {r['account']: line_name(r) for r in m['rows'] if r['account']}
    years = []
    for fy in J.YEARS:
        rows = []
        for (y, f), d in sorted(m['src'].items()):
            if y != fy:
                continue
            col = defaultdict(Decimal)
            for (kind, _), v in d.items():
                col['none' if kind == 'between' else kind] += v
            col['total'] = sum(d.values(), D0)
            if all(round(v) == 0 for v in col.values()):
                continue
            # who paid, from the fund's own postings: fund 0100 holds the school budget AND the
            # Town's other general fund accounts, and only the second reach this table
            py = fund_group(m, A, fy, f)
            rows.append(dict(
                key=T.lit(f), name=T.lit('%s · %s' % (fname[f].title(), f)), program=T.lit(py),
                cat=dict(PAYERS)[payer_group(py)] if payer_group(py) != 'gf' else 'General fund, outside the school budget',
                group=payer_group(py),
                n={k: round(fl(col[k]), 2) for k, _, _ in SRC_COLS},
                t={k: T.usd(col[k]) for k, _, _ in SRC_COLS}))
        years.append(dict(fy=T.fy(fy), rows=rows,
                          total=T.usd(sum((sum(d.values(), D0) for (y, _), d in m['src'].items() if y == fy), D0))))
    return dict(years=years, columns=[dict(id=k, label=l, means=w) for k, l, w in SRC_COLS],
                groups=[dict(id=g, label=l) for g, l in PAYERS if g != 'gf'],
                text=dict(source='Fund', category='Who paid', read=(
                    'Every fund other than the school budget that spent money on the schools this '
                    'year, and where each dollar went. Open a fund for what it paid for.'),
                    tab_where='Where it went', tab_what='What it bought', tab_rows='Every posting',
                    by_payee='Paid to', by_account='By its own account', went='Went to',
                    close='Close', loading='Loading…', failed='Could not load this year’s postings.',
                    none='None.', sum='Every fund', all_rows='postings shown',
                    all_cats='Every source', scroll='More columns: scroll the table sideways',
                    filter='Filter by payee, memo, account or where it went'))


# OVERLAP (TJ, 27 October 2026: "these other sources of funds are complimenting or supplementing
# some aspects of the school budget and we can tell by the overlap ... calculate the supplement.
# which is a separate concept than the 'on no school line'"). Other funds' money in bands, from
# the strongest overlap with the school budget to none: the same bills, the same payee, the same
# function code, cannot tell, and separate. Bills re-charged BACK are drawn apart, negative.
# Overlap is all the books can show. Whether it SUPPLEMENTED the school budget (paid for more)
# or SUPPLANTED it (paid what it would have paid) is what would have happened otherwise, which
# no ledger records -- the block says so, and never calls a dollar either.
BANDS = [('bills', 'The same bills', 'The school budget paid them; a journal entry put them on this fund.'),
         ('payee', 'The same payee', 'Paid to a payee the school budget also paid from a line.'),
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
    for fy in J.YEARS:
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
    files = {}
    for fy in J.YEARS:
        body = {}
        for (y, f), d in sorted(m['src'].items()):
            if y != fy:
                continue
            w = [[KIND_WHERE[k], where_text(k, dest, names), money(v), round(fl(v), 2)]
                 for (k, dest), v in sorted(d.items(), key=lambda kv: -abs(kv[1])) if round(v, 2)]
            acct, pay = defaultdict(Decimal), defaultdict(Decimal)
            rs = []
            for r, kind, dest in m['src_rows'].get((fy, f), []):
                acct[r['account_description'].strip().title()] += r['amt']
                pay[payee(r) or KIND.get(r['source'], r['source'])] += r['amt']
                went = ('journal entry %s' % dest) if kind == 'journal' else '%s %s' % (
                    KIND_WHERE[kind], where_text(kind, dest, names))
                rs.append([r['effective_date'], long_date(r['effective_date']),
                           KIND.get(r['source'], 'Order' if r['source'] in ORDERS else r['source']),
                           payee(r), r['description'].strip(), r['account_description'].strip().title(),
                           went, money(r['amt']), round(fl(r['amt']), 2)])
            rs.sort(key=lambda x: (x[0], -abs(x[8])))
            srt = lambda dd: [[k, money(v), round(fl(v), 2)] for k, v in sorted(dd.items(), key=lambda kv: -abs(kv[1])) if round(v, 2)]
            body[f] = dict(w=w, a=srt(acct), p=srt(pay), r=rs)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    m = FB.model()
    outs = {OUT: render(m), **line_texts(m), **fund_texts(m)}
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
