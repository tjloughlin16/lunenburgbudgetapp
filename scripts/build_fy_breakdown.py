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
import sys
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
Y0, Y1 = 2025, 2026
D0 = Decimal(0)
PRIVATE = '0100-3-300-9300-51-1-06-2-535019'

# THE ALLUVIAL'S BLOCKS: the surplus pages' eighteen categories in seven, because seven stacked
# blocks can be read and eighteen cannot. Ours; every category lands in exactly one.
GROUPS = [
    ('teaching', 'Teachers and counselors', ('teachers', 'counselors')),
    ('paras', 'Paraprofessionals', ('paras',)),
    ('staff', 'Other staff', ('admin', 'custodians', 'athletics_staff', 'other_staff')),
    ('tuition', 'Out-of-district tuition', ('tuition',)),
    ('benefits', 'Health insurance and benefits', ('benefits',)),
    ('buildings', 'Buildings and utilities', ('buildings', 'utilities')),
    ('rest', 'Services, buses, supplies, the rest',
     ('sped_services', 'transport', 'equipment', 'athletics', 'prof_dev', 'legal', 'supplies')),
]
UNMATCHED = ('unmatched', 'Other funds, not matched to a line')
GROUP_OF = {c: g for g, _, cs in GROUPS for c in cs}
if sorted(GROUP_OF) != sorted(c[0] for c in S.CATEGORIES):
    raise SystemExit('build_fy_breakdown: GROUPS must hold every surplus category once')
# Who paid, in six: a chart holds five hues and a grey. IDEA is named apart from the other
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


def alluvial_data(m):
    cells = defaultdict(Decimal)          # (fy, group, payer group)
    for (fy, cat, py), v in m['flows'].items():
        g = UNMATCHED[0] if cat == 'unmatched' else GROUP_OF[cat]
        cells[(fy, g, payer_group(py))] += v
    groups = [(g, l) for g, l, _ in GROUPS] + [UNMATCHED]
    years = []
    for fy in J.YEARS:
        blocks = []
        for g, _ in groups:
            segs = [dict(payer=p, value=round(fl(cells[(fy, g, p)]), 2),
                         text=C.usd(fl(cells[(fy, g, p)])))
                    for p, _ in PAYERS if round(cells[(fy, g, p)]) != 0]
            tot = sum((cells[(fy, g, p)] for p, _ in PAYERS), D0)
            blocks.append(dict(group=g, total=round(fl(tot), 2), text=C.usd(fl(tot)), segs=segs))
        tot = sum((cells[(fy, g, p)] for g, _ in groups for p, _ in PAYERS), D0)
        years.append(dict(fy=C.fy(fy), total=round(fl(tot), 2), text=C.usd(fl(tot)),
                          blocks=blocks))
    # A negative cell is real -- a fund whose spending on a block netted below zero in the year,
    # a refund or a charge reversed -- and a stack cannot draw it. It is listed under the
    # diagram, never dropped and never netted into another cell.
    negatives = [dict(fy=y['fy'], group=b['group'], payer=s['payer'], text=s['text'])
                 for y in years for b in y['blocks'] for s in b['segs'] if s['value'] < 0]
    for y in years:
        for b in y['blocks']:
            b['segs'] = [s for s in b['segs'] if s['value'] > 0]
    return dict(years=years, negatives=negatives,
                groups=[dict(id=g, label=l) for g, l in groups],
                payers=[dict(id=p, label=l) for p, l in PAYERS],
                text=dict(all='Every block', one='One block, at full height',
                          total='All funds', pick='Pick a block',
                          negatives='Netted below zero, not drawn:'),
                note='What each block cost from every fund, by who paid. School general fund '
                     'lines, department 300, with other funds’ spending placed on them by the '
                     'match rules below; grey is what no rule places. Orders still owed are '
                     'counted.')


MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
          'September', 'October', 'November', 'December')


def long_date(iso):
    y, mo, d = iso.split('-')
    return '%d %s %s' % (int(d), MONTHS[int(mo) - 1], y)


def fy_day(iso, fy):
    """Days since 1 July of the fiscal year's first calendar year."""
    import datetime
    return (datetime.date.fromisoformat(iso) - datetime.date(fy - 1, 7, 1)).days


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


def payer_rows(T, payers):
    out = defaultdict(Decimal)
    for (rule, py), v in payers.items():
        out[(py, rule)] += v
    return [dict(payer=T.lit(py), rule=FB.RULE_LABEL[rule], text=T.usd(v))
            for (py, rule), v in sorted(out.items(), key=lambda kv: -abs(kv[1])) if round(v) != 0]


def lines_data(m, T):
    """Every line, every year, for the sortable table and each line's own waterfall."""
    years = []
    for fy in J.YEARS:
        rows = []
        for r in m['rows']:
            if r['fy'] != fy:
                continue
            if r['account'] is None and round(r['other_funds']) == 0:
                continue
            nums = dict(voted=r['voted'], cost=r['all_funds_cost'], gf=r['gf_cost'],
                        above=r['voted_above_cost'], transfers=r['transfers'],
                        other=r['other_funds'], another=r['another_year'], left=r['left'])
            if all(round(v) == 0 for v in nums.values()):
                continue        # an account with nothing voted, spent or placed on it
            rows.append(dict(
                name=T.lit(line_name(r)) if r['account'] else 'Same function, other funds',
                account=T.lit(r['account']) if r['account'] else '',
                cat=S.CAT_LABEL[r['category']], group=GROUP_OF[r['category']],
                n={k: round(fl(v), 2) for k, v in nums.items()},
                t={k: T.usd(v) for k, v in nums.items()},
                payers=payer_rows(T, r['payers'])))
        un = sorted(m['years'][fy]['unmatched'].items(), key=lambda kv: -kv[1])
        years.append(dict(fy=T.fy(fy), rows=rows,
                          unmatched=[dict(payer=T.lit(py), why=why, text=T.usd(v))
                                     for (py, why), v in un if round(v) != 0],
                          unmatched_total=T.usd(sum((v for _, v in un), D0))))
    return dict(years=years, cats=sorted({S.CAT_LABEL[c[0]] for c in S.CATEGORIES}),
                columns=[dict(id='left', label='Left'), dict(id='voted', label='Voted'),
                         dict(id='cost', label='Cost, all funds'),
                         dict(id='above', label='Voted above cost'),
                         dict(id='transfers', label='Transfers'),
                         dict(id='other', label='Other funds'),
                         dict(id='another', label='Another year')],
                steps=dict(voted='Voted', cost='Less what it cost, all funds',
                           other='Plus what other funds paid', transfers='Plus transfers, net',
                           another='Plus another year’s money', left='Left'),
                text=dict(all_cats='Every category', show='Show every line', fewer='Show fewer',
                          payers='Who else paid, and how it was matched',
                          none='No other fund matched to this line.',
                          unmatched='Other funds’ spending not matched to any line',
                          lines='lines'))


def pool_data(m, T):
    """Under lines pour into one pool; over lines draw from it; what is left is the net."""
    years = []
    for fy in J.YEARS:
        gin, gout = defaultdict(Decimal), defaultdict(Decimal)
        nin, nout = defaultdict(int), defaultdict(int)
        for r in m['rows']:
            if r['fy'] != fy or r['account'] is None or r['left'] == 0:
                continue
            if r['left'] > 0:
                gin[r['category']] += r['left']
                nin[r['category']] += 1
            else:
                gout[r['category']] -= r['left']
                nout[r['category']] += 1
        under, over = sum(gin.values(), D0), sum(gout.values(), D0)
        if under - over != m['years'][fy]['left']:
            raise SystemExit('build_fy_breakdown: the pool of FY%d does not net to what was left' % fy)
        tr = [t for t in m['transfers'] if t['fy'] == fy]
        side = lambda g, n: [dict(cat=S.CAT_LABEL[c], value=round(fl(v), 2), text=T.usd(v),
                                  lines=T.lit('%s %s' % (C.num(n[c]), 'line' if n[c] == 1 else 'lines')))
                             for c, v in sorted(g.items(), key=lambda kv: -kv[1])]
        years.append(dict(fy=T.fy(fy), under=round(fl(under), 2), over=round(fl(over), 2),
                          t_under=T.usd(under), t_over=T.usd(over), t_left=T.usd(under - over),
                          left=round(fl(under - over), 2),
                          into=side(gin, nin), out=side(gout, nout),
                          transfers=T.usd(sum((t['moved'] for t in tr), D0)),
                          n_transfers=T.lit('%d dated entries' % len(tr))))
    return dict(years=years, text=dict(
        under='Lines that ended under', over='Lines that ran over', pool='One pool',
        left='Left at year end', lines='lines',
        transfers='Moved between lines by transfer, both ends named (on the timeline):',
        read='Nothing in the books says which leftover paid for which overrun: inside one '
             'appropriation the money is a pool. So no line is drawn from one to another.'))


def timeline_data(m, T):
    """Every recorded move, dated: transfers between lines, cost moved between funds, and
    money that crossed from one year to another."""
    lanes = [dict(id='transfer', label='Budget moved between lines (transfers)'),
             dict(id='moved', label='Cost moved between funds (journal entries)'),
             dict(id='year', label='Money crossing years')]
    years = []
    for fy in J.YEARS:
        ev = []
        for t in (t for t in m['transfers'] if t['fy'] == fy):
            def names(side):
                by = defaultdict(Decimal)
                for x in side:
                    by[S.CAT_LABEL[x['category']]] += abs(x['amount'])
                top = sorted(by, key=lambda c: -by[c])
                if not top:
                    return 'outside the school budget'
                more = len(top) - 2
                return ' and '.join(top[:2]) + (' (and %s more)' % C.num(more) if more > 0 else '')
            ev.append(dict(lane='transfer', day=fy_day(t['date'], fy), date=T.lit(long_date(t['date'])),
                           value=round(fl(t['moved']), 2), text=T.usd(t['moved']),
                           title=T.lit(t['description'] or 'No memo'),
                           detail=T.lit('From %s to %s' % (names(t['gave']), names(t['got'])))
                           + (' · %s from outside the school budget' % T.usd(t['outside'])
                              if t['outside'] > 0 else
                              ' · %s sent outside the school budget' % T.usd(-t['outside'])
                              if t['outside'] < 0 else '')))
        for mv in (x for x in m['moves'] if x['fy'] == fy):
            pay = ', '.join('%s %s' % (T.lit(p), T.usd(v)) for p, v in
                            sorted(mv['by_payer'].items(), key=lambda kv: -abs(kv[1])) if round(v))
            ev.append(dict(lane='moved', day=fy_day(mv['date'], fy), date=T.lit(long_date(mv['date'])),
                           value=round(fl(mv['off'] - mv['onto']), 2),
                           text='%s onto other funds, %s back' % (T.usd(mv['off']), T.usd(-mv['onto'])),
                           title=T.lit(mv['description'] or 'No memo'),
                           detail='Other funds: %s' % pay if pay else ''))
        y = m['years'][fy]
        if y['carried_budget']:
            ev.append(dict(lane='year', day=0, date=T.lit(long_date('%d-07-01' % (fy - 1))),
                           value=round(fl(y['carried_budget']), 2), text=T.usd(y['carried_budget']),
                           title='Orders carried in from %s' % T.fy(fy - 1),
                           detail='%s of them were never paid, and came back to this year'
                                  % T.usd(y['carried_unpaid'])))
        pre = [r for r in m['prepaid'] if r['fy'] == fy]
        if pre:
            ev.append(dict(lane='year', day=fy_day(pre[0]['effective_date'], fy),
                           date=T.lit(long_date(pre[0]['effective_date'])),
                           value=round(fl(y['prepaid']), 2), text=T.usd(y['prepaid']),
                           title='%s tuition paid from this year' % T.fy(fy + 1),
                           detail=T.lit('%d invoices numbered for the next school year' % len(pre))))
        ev.sort(key=lambda e: (e['day'], e['lane'], -e['value']))
        years.append(dict(fy=T.fy(fy), events=ev,
                          months=[T.lit(MONTHS[(6 + i) % 12][:3]) for i in range(12)]))
    return dict(years=years, lanes=lanes, text=dict(
        list='Every entry, in order', biggest='Largest first', order='In date order',
        none='Nothing recorded in this lane.'))


def table(m):
    """The four parts, by category, one view per year."""
    views = []
    for fy in J.YEARS:
        acc = defaultdict(lambda: defaultdict(Decimal))
        for r in m['rows']:
            if r['fy'] == fy:
                for t in FB.TERMS + ('left',):
                    acc[r['category']][t] += r[t]
        cats = sorted(acc, key=lambda c: -acc[c]['left'])
        rows = [dict(label=S.CAT_LABEL[c], cells=[C.usd(fl(acc[c][t])) for t in
                                                ('left',) + FB.TERMS]) for c in cats]
        y = m['years'][fy]
        rows.append(dict(label='All lines', cells=[C.usd(fl(y['left']))]
                         + [C.usd(fl(y['terms'][t])) for t in FB.TERMS]))
        views.append(dict(key=str(fy), label=C.fy(fy), total_col=None,
                          kinds=['ledger', 'estimate', 'ledger', 'estimate', 'ledger'],
                          columns=['Left', 'Voted above cost', 'Transfers', 'Other funds',
                                   'Another year'],
                          rows=rows,
                          note='Left = the four parts that follow, to the cent. Negative '
                               '“voted above cost” is a vote below what the lines cost from '
                               'every fund. Orders still owed are counted as spent.'))
    return dict(caption='The four parts, by category', views=views)


def page(m):
    y0, y1 = m['years'][Y0], m['years'][Y1]
    t0, t1 = y0['terms'], y1['terms']
    rows = {(r['fy'], r['account']): r for r in m['rows'] if r['account']}
    priv = rows[(Y1, PRIVATE)]
    idea_tuition = sum((v for (rl, py), v in priv['payers'].items() if py.startswith('IDEA')), D0)
    if priv['other_funds'] != idea_tuition:
        raise SystemExit('build_fy_breakdown: the page says the IDEA grant is all of private '
                         'tuition’s other-fund money in FY%d' % Y1)
    # Journal moves, measured: each move journal nets to zero, so the other funds' net is the
    # general fund's change with the sign turned.
    net = lambda y: sum((mv['off'] + mv['onto'] for mv in m['moves'] if mv['fy'] == y), D0)
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
    late = '%d-05-26' % Y1          # the last five weeks of the year
    gross = [(t['date'], t['moved']) for t in m['transfers'] if t['fy'] == Y1] + \
        [(mv['date'], mv['off'] - mv['onto']) for mv in m['moves'] if mv['fy'] == Y1]
    if not 2 * sum((v for dt, v in gross if dt >= late), D0) > sum((v for _, v in gross), D0):
        raise SystemExit('build_fy_breakdown: the timeline says most of FY%d’s moved money moved '
                         'after %s' % (Y1, late))
    data = alluvial_data(m)
    T = Texts()
    pool, timeline, lines = pool_data(m, T), timeline_data(m, T), lines_data(m, T)
    figs = {s for y in data['years'] for s in [y['text'], y['fy']]
            + [b['text'] for b in y['blocks']] + [x['text'] for b in y['blocks'] for x in b['segs']]}
    figs |= {n['text'] for n in data['negatives']} | {n['fy'] for n in data['negatives']}
    return TP.page(
        ID,
        '%s’s lines left %s; other funds paid %s of their cost, %s more than in %s.'
        % (C.fy(Y1), C.usd(fl(y1['left'])), C.usd(fl(t1['other_funds'])), C.usd(fl(more)),
           C.fy(Y0)),
        facts, conclusions,
        chart=TP.bridge(
            'From the vote to what was left', ('Voted above cost, all funds', fl(t1['voted_above_cost'])),
            [('Paid by other funds', fl(t1['other_funds'])),
             ('Transfers, net', fl(t1['transfers'])),
             ('Another year’s money', fl(t1['another_year']))],
            ('Left', fl(y1['left'])), '$', basis='estimate',
            note='The first two steps are our placing of other funds’ spending; their sum is '
                 'measured. The last two are postings. School general fund, department 300.',
            note_allow=('300',)),
        blocks=[
            TB.custom('fy-alluvial', 'Who paid for what, year by year', data, place='lead',
                      figures=sorted(figs, key=len, reverse=True), allow=('300',),
                      basis=('reading', 'Our placing of other funds’ spending on the lines'),
                      alt='Alluvial diagram, four fiscal years: what the school budget’s lines '
                          'cost from every fund, in seven blocks, each split by who paid, with '
                          'bands joining each block and payer from year to year',
                      so=('Follow a band: one that keeps its height and changes colour is a cost '
                          'that held while its payer changed, the move a voted budget cannot show.',
                          None, ())),
            TB.custom('fy-pool', 'One pool, not pairs', pool, place='body',
                      figures=sorted(T.figures), allow=sorted(T.literals),
                      basis=('record', 'What each line had left, as the journal records it'),
                      alt='Flow diagram, one year at a time: every category whose lines ended under '
                          'budget flows into one pool on the left; the pool flows out to every '
                          'category whose lines ran over, and what remains is what was left',
                      so=('The overruns were paid from leftovers in general, not from any one of '
                          'them. A claim that one line covered another is a reading, not a record.',
                          None, ())),
            TB.custom('fy-moves-timeline', 'Every recorded move, dated', timeline, place='body',
                      figures=sorted(T.figures), allow=sorted(T.literals),
                      basis=('record', 'Journal entries, with the Town’s own memo for each'),
                      alt='Timeline of the fiscal year, July to June, in three lanes: budget '
                          'transfers between lines, costs moved between funds by journal entry, '
                          'and money crossing from one year to another; each mark sized by amount',
                      so=('When a move was made shows whether it was planned or a year-end '
                          'adjustment. In %s most of the money moved in the last five weeks.'
                          % C.fy(Y1), {'y': F(Y1)}, ())),
            TB.explain('How the four parts are counted', [
                '**Voted above cost** is the vote, less what the line cost from every fund. '
                '**Paid by other funds** is what grants, the circuit breaker, fees and revolving '
                'funds paid toward the line. **Transfers** moved budget between lines. '
                '**Another year’s money** is orders carried in from last year, less what they '
                'paid, less next year’s bills paid early.',
                'Which other-fund dollar counts toward which line is our reading, in order: a '
                'journal entry naming both ends, then the same payee, then the same function '
                'code (placed on a category, never a line). What none of them places is shown '
                'apart, never counted as voted above cost. Capital articles are matched only by '
                'a journal entry.'],
                place='body', tone='define'),
            TB.custom('fy-line-table', 'Every line, in four parts', lines, place='end',
                      figures=sorted(T.figures), allow=sorted(T.literals),
                      basis=('reading', 'Our placing of other funds’ spending on the lines'),
                      alt='Table of every school general fund line, one fiscal year at a time, '
                          'sortable by what was left and by each of the four parts; each line '
                          'opens on its own waterfall and the other funds that paid toward it',
                      so=('Open any line to see why it ended where it did, and which fund '
                          'paid what toward it, with the rule that matched each payment.',
                          None, ())),
        ],
        tables=[table(m)],
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
    return json.dumps(p, indent=1, ensure_ascii=False, sort_keys=True) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text = render()
    if a.check:
        if not os.path.exists(OUT) or open(OUT, encoding='utf-8').read() != text:
            print('STALE %s' % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('fy breakdown: current')
        return 0
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, OUT)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
