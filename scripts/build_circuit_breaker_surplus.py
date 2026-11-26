#!/usr/bin/env python3
"""THE CIRCUIT BREAKER AND THE FY2026 SURPLUS: the figures, as a module (`data()`).

It built its own page, Circuit breaker and surplus, until 24 November 2026, when that page was
folded into FY2026 school surplus (scripts/build_fy2026_school_surplus.py, which reads `data()`;
the old address opens the new page through fy28/src/routes.ts TOPIC_MERGED). What follows is
the page's original brief, still true of the figures.

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
import os
import re
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import journal as J  # noqa: E402
import fy_breakdown as FB  # noqa: E402
import build_journal_surplus_topics as JS  # noqa: E402  (the shared sources and quotations)

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
