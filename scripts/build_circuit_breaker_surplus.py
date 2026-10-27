#!/usr/bin/env python3
"""THE CIRCUIT BREAKER AND THE FY2026 SURPLUS: one topic page.

    python3 scripts/build_circuit_breaker_surplus.py           # write fy28/public/data/topics/fy2026-circuit-breaker.json
    python3 scripts/build_circuit_breaker_surplus.py --check   # fail if it would change

    fy2026-circuit-breaker   /fy2026-closeout/fy2026-circuit-breaker   Circuit breaker and surplus

TJ, 26 October 2026, reading the line table on the FY breakdown page: private tuition left
$522,629 and collaborative tuition ran $434,108 over, in one category -- *"i think we truly need
to call out this circuit breaker problem for the surplus, and how it relates to collab tuition."*

WHAT IT RESTS ON, all measured:
  - the district's FY2026 budget book (`3-12-25-town-manager-39-s-budget.txt` line 298): the
    collaborative tuition line is voted NET of the circuit breaker -- $782,867 gross, a
    `Circuit Breaker` line of -$480,204, so $302,663 voted (rule 11: a budget line is net);
  - the school journal: what the circuit breaker fund (2640) paid toward tuition, and when; the
    29 June 2026 entry that charged $333,494.89 of collaborative tuition the general fund had
    paid to that fund instead; the general fund's own tuition spending and the FY2027 invoices
    it paid early (`fy_breakdown.model`, whose verifier ties every line to the period-13 report);
  - the Town's special-revenue report at 31 March 2026 for the fund's balance.

WHAT IS OURS (rule 7): which IDEA grant spending counts toward private tuition (a payee match,
drawn in the estimate colour), and every WHY. Nothing held says why the reimbursement was
charged in one entry at year end, and the page says so.
"""
import argparse
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
import topic_blocks as TB  # noqa: E402
import journal as J  # noqa: E402
import fy_breakdown as FB  # noqa: E402
import build_journal_surplus_topics as JS  # noqa: E402  (the shared sources and quotations)

ID = 'fy2026-circuit-breaker'
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % ID)
Y0, Y1 = 2025, 2026
PRIVATE = '0100-3-300-9300-51-1-06-2-535019'
COLLAB = '0100-3-300-9400-51-1-06-2-535023'
TUITION = ('535019', '535023')       # the two tuition objects, in every fund
CB_FUND = '2640'
D0 = Decimal(0)


def fail(msg):
    raise SystemExit('build_circuit_breaker_surplus: ' + msg)


def fl(x):
    return float(x)


def book():
    """The FY2025 and FY2026 columns of the budget book's collaborative tuition lines."""
    text = ' '.join(open(JS.BOOK_TEXT, encoding='utf-8').read().split())
    g = re.search(r'Collaborative Tuitions ([\d,]+) ([\d,]+) ', text)
    o = re.search(r'Circuit Breaker \(70% = \$[\d,]+\) \(75% = [\d,]+\)-([\d,]+) -([\d,]+) ', text)
    if not g or not o:
        fail('the collaborative tuition lines are no longer in %s' % JS.BOOK_TEXT)
    n = lambda s: Decimal(s.replace(',', ''))
    return {Y0: (n(g.group(1)), n(o.group(1))), Y1: (n(g.group(2)), n(o.group(2)))}


def data():
    m = FB.model()
    rows = {(r['fy'], r['account']): r for r in m['rows'] if r['account']}
    A = J.accounts()
    cb = [r for r in J.lines() if r['fund'] == CB_FUND]
    actual = lambda r: J.COLUMN_OF[r['source']] == 'actual' and r['source'] != 'CRP'
    years = {}
    for y in J.YEARS:
        p, c = rows[(y, PRIVATE)], rows[(y, COLLAB)]
        idea = sum((v for r in (p, c) for (_, py), v in r['payers'].items() if py.startswith('IDEA')), D0)
        # the circuit breaker's own tuition spending, on its own accounts: a record, not a match
        cbt = sum((r['amt'] for r in cb if r['fy'] == y and J.is_spent(r) and r['source'] != 'YEC'
                   and r['account'].split('-')[-1] in TUITION), D0)
        years[y] = dict(
            gf=p['gf_cost'] + c['gf_cost'], cb=cbt, idea=idea, early=p['prepaid'] + c['prepaid'],
            drawn_early=sum((r['amt'] for r in cb if r['fy'] == y and actual(r)
                             and r['effective_date'][5:7] != '06'), D0),
            drawn_june=sum((r['amt'] for r in cb if r['fy'] == y and actual(r)
                            and r['effective_date'][5:7] == '06'), D0),
            received=-sum((r['amt'] for r in cb if r['fy'] == y and r['source'] == 'CRP'), D0),
            last_receipt=max((r['effective_date'] for r in cb if r['fy'] == y and r['source'] == 'CRP'),
                             default=None),
            voted_collab=c['voted'], left=m['years'][y]['left'])
    recl = [r for r in J.lines() if r['fy'] == Y1 and r['source'] == 'GEN'
            and r['account'] == COLLAB and r['amt'] < 0]
    if len(recl) != 1 or recl[0]['effective_date'] != '2026-06-29':
        fail('the page assumes one 29 June 2026 entry charged collaborative tuition to the fund')
    other = [r for r in J.lines() if r['journal'] == recl[0]['journal'] and r['fy'] == Y1
             and r is not recl[0]]
    if not (len(other) == 1 and other[0]['fund'] == CB_FUND and other[0]['amt'] == -recl[0]['amt']):
        fail('the 29 June entry is no longer collaborative tuition onto the circuit breaker alone')
    charged = -recl[0]['amt']
    c26 = rows[(Y1, COLLAB)]
    own = c26['gf_cost'] + charged                 # FY2026's own collaborative bills, before the charge
    if c26['voted'] - own - c26['prepaid'] + charged != c26['left']:
        fail('the collaborative bridge does not close to what the line left')
    # The fund's balance: held at 1 July 2025 and at 31 March 2026 as the Town printed it, and
    # at 30 June after the charge (our arithmetic; nothing else posted to the fund in April-June).
    import openpyxl
    ws = openpyxl.load_workbook(os.path.join(ROOT, JS.SPECREV), read_only=True,
                                data_only=True).worksheets[0]
    sr = [r for r in ws.iter_rows(values_only=True) if r and r[0] == int(CB_FUND)]
    if len(sr) != 1:
        fail('fund %s is not one row in %s' % (CB_FUND, JS.SPECREV))
    q = lambda v: Decimal(str(v)).quantize(Decimal('0.01'))
    held_jul, held_mar = -q(sr[0][8]), -q(sr[0][15])
    if held_jul + years[Y1]['received'] - years[Y1]['drawn_early'] != held_mar:
        fail('the special-revenue report no longer foots with the journal for fund %s' % CB_FUND)
    if any(r['fy'] == Y1 and actual(r) and r['effective_date'] > '2026-03-31'
           and r['effective_date'][5:7] != '06' for r in cb):
        fail('fund %s spent between April and May %d; the year-end balance needs it' % (CB_FUND, Y1))
    return dict(m=m, years=years, book=book(), charged=charged, own=own, collab=c26,
                private=rows[(Y1, PRIVATE)], held_jul=held_jul, held_mar=held_mar,
                held_end=held_mar - years[Y1]['drawn_june'], journal=recl[0]['journal'])


def page(d):
    U = lambda v: figure(fl(v), C.usd(fl(v)))
    F = lambda y: figure(y, C.fy(y), 'fiscal year')
    P = lambda v: figure(v, C.pct(v, 0))
    y0, y1, bk = d['years'][Y0], d['years'][Y1], d['book']
    gross, plan = bk[Y1]
    # the book prints whole dollars; the journal's vote is $302,662.56
    if abs(gross - plan - d['collab']['voted']) >= 1:
        fail('the book’s FY2026 gross less the circuit breaker is not the voted collaborative line')
    short = plan - d['charged']
    without = y1['left'] - d['charged']
    share = 100 * fl(d['charged']) / fl(y1['left'])
    if not (y0['drawn_early'] > 100 * y1['drawn_early'] and short > 0 and d['held_end'] > short
            and y1['last_receipt'] < '2026-01-01' and y1['idea'] > 0 and y0['idea'] == 0):
        fail('the conclusions assume FY2025 drew the fund through the year, FY2026 did not, the '
             'fund held more than the shortfall, the state paid by December, and IDEA paid '
             'private tuition in FY2026 alone')
    oct22 = ' '.join(JS._captions(JS.OCT22_CAPTIONS).split())
    if ' '.join(JS.OCT22_QUOTE.lower().split()) not in oct22.lower():
        fail('the Finance Committee quotation is no longer in its captions')
    f, con = LD.fact, TP.conclusion
    receipt = JS.long_date(y1['last_receipt']) if hasattr(JS, 'long_date') else None
    receipt = receipt or '%d %s %s' % (int(y1['last_receipt'][8:]), (
        'January February March April May June July August September October November '
        'December').split()[int(y1['last_receipt'][5:7]) - 1], y1['last_receipt'][:4])
    facts = [
        f('plan', U(plan), 'circuit breaker the FY2026 vote counted on, collaborative',
          'published', allow=('FY2026',)),
        f('charged', U(d['charged']), 'charged to it, in one entry on 29 June 2026', 'published',
          allow=('29 June 2026',)),
        f('short', U(short), 'counted on, never charged', 'published'),
        f('early0', U(y0['drawn_early']), 'drawn from the fund July to May, FY2025', 'published',
          allow=('2025',)),
        f('early1', U(y1['drawn_early']), 'drawn from the fund July to May, FY2026', 'published',
          allow=('2026',)),
        f('mar', U(d['held_mar']), 'held in the fund at 31 March 2026', 'published',
          allow=('31 March 2026',)),
        f('end', U(d['held_end']), 'held after the 29 June charge', 'published',
          allow=('29 June',)),
        f('idea', U(y1['idea']), 'IDEA grant paid toward private tuition, FY2026', 'estimate',
          allow=('2026',)),
        f('prepaid', U(y1['early']), 'FY2027 tuition paid early, from the general fund',
          'published', allow=('2027',)),
        f('without', U(without), 'left in FY2026 without the 29 June charge', 'published',
          allow=('2026', '29 June')),
        f('left', U(y1['left']), 'left in FY2026, orders owed counted', 'published',
          allow=('2026',)),
    ]
    conclusions = [
        con('The vote counted on %s of circuit breaker; %s was charged, on 29 June.'
            % (C.usd(fl(plan)), C.usd(fl(d['charged']))), ['plan', 'charged', 'short'],
            {'a': U(plan), 'b': U(d['charged'])}, allow=('29 June',),
            so='Collaborative tuition is voted net of it, so the line ran over until then. The '
               'fund still held %s afterwards.' % C.usd(fl(d['held_end'])),
            so_figures={'e': U(d['held_end'])}),
        con('July to May the fund paid %s of tuition in %s and %s in %s.'
            % (C.usd(fl(y0['drawn_early'])), C.fy(Y0), C.usd(fl(y1['drawn_early'])), C.fy(Y1)),
            ['early0', 'early1', 'mar'],
            {'a': U(y0['drawn_early']), 'y': F(Y0), 'b': U(y1['drawn_early']), 'z': F(Y1)},
            so='The state’s money was in by %s; until 29 June the school budget carried the '
               'whole tuition bill.' % receipt, so_allow=(receipt, '29 June')),
        con('Without the 29 June charge %s would have left %s; with it, %s.'
            % (C.fy(Y1), C.usd(fl(without)), C.usd(fl(y1['left']))), ['without', 'left', 'charged'],
            {'y': F(Y1), 'a': U(without), 'b': U(y1['left'])}, allow=('29 June',),
            so='%s of the surplus is that one entry, which changed which fund paid, not what '
               'anything cost.' % C.pct(share, 0), so_figures={'p': P(share)}),
        con('The general fund, not the circuit breaker, paid %s of %s tuition early.'
            % (C.usd(fl(y1['early'])), C.fy(Y1 + 1)), ['prepaid'],
            {'a': U(y1['early']), 'y': F(Y1 + 1)},
            so='At the Finance Committee on 22 October the circuit breaker was named as the '
               'account allowed to prepay a first quarter.', so_allow=('22 October',)),
    ]
    yrs = J.YEARS
    col = lambda k: [fl(d['years'][y][k]) for y in yrs]
    cs = d['collab']
    return TP.page(
        ID,
        'FY2026’s vote counted on %s of circuit breaker for collaborative tuition; %s came, '
        'on 29 June.' % (C.usd(fl(plan)), C.usd(fl(d['charged']))),
        facts, conclusions,
        chart=TP.series(
            'Out-of-district tuition, by who paid', [C.fy(y) for y in yrs],
            [TP.track('School general fund, this year’s tuition', col('gf'), 'published', 'bar'),
             TP.track('Circuit breaker', col('cb'), 'published', 'bar'),
             TP.track('IDEA grant (our match, by payee)', col('idea'), 'estimate', 'bar'),
             TP.track('Next year’s tuition, paid early', col('early'), 'published', 'bar')],
            '$', kind='bar', stacked=True,
            note='Private and collaborative tuition together, every fund. The circuit breaker is '
                 'what fund 2640 charged to tuition accounts. Orders still owed are counted.',
            note_allow=('2640',)),
        also=[TP.bridge(
            'Collaborative tuition, vote to left', ('Voted, net of the circuit breaker', fl(cs['voted'])),
            [('This year’s bills, paid by the school budget', -fl(d['own'])),
             ('Next year’s first quarter, paid early', -fl(cs['prepaid'])),
             ('Charged to the circuit breaker, 29 June', fl(d['charged']))],
            ('Left', fl(cs['left'])), '$',
            note='%s. School general fund account 9400 535023; the charge is journal %s.'
                 % (C.fy(Y1), d['journal']),
            note_figures={'y': F(Y1)}, note_allow=('9400', '535023', d['journal']))],
        blocks=[
            TB.explain('A line voted net of the circuit breaker', [
                ('The budget book prints collaborative tuition twice: **%s** for the tuition, and '
                 'a **Circuit Breaker** line of **−%s** beneath it. Town Meeting votes the '
                 'difference, **%s**. So the line is voted on the assumption that the state’s '
                 'reimbursement will pay part of the bills.'
                 % (C.usd(fl(gross)), C.usd(fl(plan)), C.usd(fl(cs['voted']))),
                 {'g': U(gross), 'p': U(plan), 'v': U(cs['voted'])}, ()),
                'The reimbursement does not arrive in the line. It sits in its own fund, and pays '
                'a bill only when a bill is charged to that fund. Until then the school budget '
                'pays, and the line shows as over budget. A charge to the fund afterwards '
                'lowers what the school budget spent, so it raises what was left.',
                'What the school budget leaves unspent returns to the town as free cash. What the '
                'circuit breaker fund leaves stays in the fund, to be spent within a year of '
                'arriving (DESE).'],
                place='lead', tone='define'),
            TB.panels('Counted on, and charged', [
                TB.panel(t, [
                    ('Collaborative tuition, gross (book)', C.usd(fl(bk[y][0])), None),
                    ('Circuit breaker counted on (book)', C.usd(fl(bk[y][1])), None),
                    ('Collaborative tuition, voted', C.usd(fl(d['years'][y]['voted_collab'])), None),
                    ('Circuit breaker charged to tuition', C.usd(fl(d['years'][y]['cb'])), None),
                    ('of it, July to May', C.usd(fl(d['years'][y]['drawn_early'])),
                     'good' if y == Y0 else 'bad'),
                    ('of it, in June', C.usd(fl(d['years'][y]['drawn_june'])), None)])
                for y, t in ((Y0, 'The year before'), (Y1, 'The year of this surplus'))],
                place='body',
                note='The budget book’s figures, and the journal’s. The year before, the vote was '
                     'set by a July entry that took the circuit breaker off the line.',
                so=('One year drew the fund as bills came in and charged more than the vote '
                    'counted on; the next charged less, all of it on 29 June.', None, ('29 June',))),
            TB.panels('The circuit breaker fund, through the year', [
                TB.panel('As the Town printed it', [
                    ('Held at the start of the year', C.usd(fl(d['held_jul'])), None),
                    ('Received from the state', C.usd(fl(y1['received'])), 'good'),
                    ('Spent, July to March', C.usd(fl(y1['drawn_early'])), None),
                    ('Held at the end of March', C.usd(fl(d['held_mar'])), None)]),
                TB.panel('At year end (our sum)', [
                    ('Tuition charged to it in June', C.usd(fl(d['charged'])), None),
                    ('Held at year end', C.usd(fl(d['held_end'])), None)])],
                place='body',
                note='The Town’s special-revenue report at the end of March, then the school '
                     'journal; nothing else posted to the fund from April to June.',
                so=('While the collaborative line ran over, the fund that was counted on to pay '
                    'part of it held more than %s.' % C.usd(fl(d['held_mar'])),
                    {'h': U(d['held_mar'])}, ())),
            TB.explain('What the record shows, and does not', [
                ('**Shows.** The circuit breaker paid tuition bills as they came in %s, %s and '
                 '%s. In %s it paid %s before June, while the state’s %s for the year was in the '
                 'fund by %s. The IDEA grant paid %s toward private tuition that year, by our '
                 'match on the payee.'
                 % (C.fy(2023), C.fy(2024), C.fy(Y0), C.fy(Y1), C.usd(fl(y1['drawn_early'])),
                    C.usd(fl(y1['received'])), receipt, C.usd(fl(y1['idea']))),
                 {'a': F(2023), 'b': F(2024), 'c': F(Y0), 'd': F(Y1), 'e': U(y1['drawn_early']),
                  'r': U(y1['received']), 'i': U(y1['idea'])}, (receipt,)),
                ('**Does not show.** Why the fund was left untouched until 29 June: a late claim, '
                 'a choice to keep the money for later, or an ordinary year-end clean-up all fit '
                 'the same postings. Nothing held says which.', None, ('29 June',)),
                '**Would settle it.** The district’s year-end close memo for the school budget, and '
                'the circuit breaker claim with the state’s payment schedule. Both are on What we '
                'cannot answer.'],
                place='end', tone='plain')],
        said=[dict(quote=JS.OCT22_QUOTE, board='Finance Committee', date='2026-10-22',
                   href=JS.OCT22_HREF, label='Finance Committee recording (machine captions)')],
        sources=JS.sources() + [
            dict(label='Lunenburg Public Schools — FY2026 budget, 3-12-25 Town Manager’s budget '
                       '(collaborative tuition and its circuit breaker line)', href=JS.BOOK),
            dict(label='Town of Lunenburg — special-revenue-fy2026-p09.xlsx (fund balances, '
                       '31 March 2026)',
                 href='/docs/town-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx'),
            dict(label='DESE — circuit breaker FAQ (spending within a year of receipt)',
                 href=JS.DESE_CB_FAQ),
            dict(label='Finance Committee recording, 22 October 2026', href=JS.OCT22_HREF)],
        finding_figures={'a': U(plan), 'b': U(d['charged'])}, finding_allow=('FY2026', '29 June'))


def render(d=None):
    p = page(d or data())
    p['not_established'] = [
        'Why the circuit breaker was not drawn from July to May in FY2026.',
        'Whether the 29 June charge and the 30 June early payment were decided together.',
        'Whether the IDEA grant paying private tuition was planned in the FY2026 budget.',
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
        print('circuit breaker surplus: current')
        return 0
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, OUT)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
