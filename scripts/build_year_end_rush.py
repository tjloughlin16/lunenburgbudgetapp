#!/usr/bin/env python3
"""WAS THERE A YEAR-END SPENDING RUSH IN FY2026? Five timing tests on the school general fund,
FY2026 against FY2023-FY2025, and the leftover the year would have reported without the late
spending. Writes notes/findings/FY26-YEAR-END-RUSH.md.

    python3 scripts/build_year_end_rush.py           # write the finding
    python3 scripts/build_year_end_rush.py --check   # fail if the file no longer reproduces

TJ, 24 November 2026: *"we need to figure out if there was a 'Mad dash of spending' at year end
due to a large deficit. im told there was, but i want to see how we can detect that..... and
compare it to previous years"* -- and later: *"i think there was MORE unspent than it seems ...
but they spent a maddash to bring that number down even further."*

SCOPE. The school general fund as `journal.in_surplus_scope` defines it (fund 0100, department
300), expense accounts. The timing tests (1, 2, 3, 5) read DISCRETIONARY lines only, declared
in `GROUPS` by object code: salaries, benefits, utilities, transportation, tuition and
insurance are left out, because their timing is set by pay runs, meters, routes and
placements rather than by a decision to buy. Test 4 reads every line.

THE MEASURE OF A LATE ORDER. A purchase order is dated by when it was OPENED (its first `POE`)
and valued at what it finally came to in that year: the amount opened plus every later change
(`POM`), so an order cut back or closed unspent counts only for what it kept. Paying it moves
money from the open-order column to the actual column and changes nothing. An order still open
at the close is spent on this site (journal.SPENT) and counts in full. Two things are left out
on purpose, and the finding says so: invoices paid with no order at all, and journal entries
(`GEN`) that move costs onto grants -- year-end clean-up that runs the other way and, netted
in, swamped every year's signal when it was tried (24 November 2026).

WHAT IS OURS (rule 3). Every timing table is a measurement off the journal. The bridge's
"above the usual" layer is OUR estimate: it compares a year with a baseline of the other
years, and the method is printed beside it. The leftover as reported is
`fy_breakdown.model()`'s, counted the FY2026 way in every year (open orders at the close
subtracted), so the four years compare like for like.
"""
import argparse
import os
import sys
from collections import defaultdict
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import journal as J  # noqa: E402
import fy_breakdown as FB  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'notes', 'findings', 'FY26-YEAR-END-RUSH.md')
YEARS = (2023, 2024, 2025, 2026)
Y1 = 2026
BASE = (2023, 2024, 2025)
WINDOW = '05-15'          # the late window opens 15 May and runs to 30 June
D0 = Decimal(0)
# Anchors the brief quotes, asserted so the prose cannot drift from the model.
ANCHOR_LEFT = Decimal('482118.07')
ANCHOR_PREPAID = Decimal('189276.75')
ANCHOR_RECLASS = Decimal('333494.89')
RECLASS_JOURNAL = (2026, '2026/12/000692')
GAP_WHAT = 'What a purchase ordered in the last six weeks of a school year was for'

# DISCRETIONARY, by object code. Our classification, declared. A code is in a group by its
# first digits unless EXCLUDED names it.
GROUPS = [
    ('supplies', 'Supplies: custodial, building, office, general', ('54',)),
    ('instruction', 'Instructional materials and books', ('55',)),
    ('equipment', 'Equipment, technology and repairs', ('52',)),
    ('capital', 'Equipment purchases and capital improvement', ('58',)),
    ('services', 'Contracted services, dues and fees', ('53',)),
]
EXCLUDED = {
    'utilities': ('521', '523'),
    'transportation': ('535016', '535025', '535026'),
    'tuition': ('535007', '535019', '535022', '535023', '535027', '535028', '535029'),
    'insurance': ('535018',),
    'stipend': ('535017',),
}
_EXCL = tuple(c for cs in EXCLUDED.values() for c in cs)


def group(obj):
    if obj.startswith(_EXCL):
        return None
    for g, _, prefixes in GROUPS:
        if obj.startswith(prefixes):
            return g
    return None


LABEL = {g: l for g, l, _ in GROUPS}


def fail(msg):
    raise SystemExit('build_year_end_rush: ' + msg)


def usd(v, cents=False):
    v = Decimal(v)
    s = '{:,.2f}'.format(abs(v)) if cents else '{:,.0f}'.format(abs(v))
    return ('-$' if v < 0 else '$') + s


def pct(n, d):
    return '{:.1f}%'.format(100 * n / d) if d else '--'


def late(r):
    return r['effective_date'] >= '%d-%s' % (r['fy'], WINDOW)


def level_gap():
    """FY2027 level service and balanced proposals, read off the workbook (row 404)."""
    import openpyxl
    wb = openpyxl.load_workbook(os.path.join(ROOT, 'sources', 'budget-workbooks', 'fy27-proposals.xlsx'),
                                data_only=True, read_only=True)
    ws = wb['FY27 Budget Projection']
    if (ws['B404'].value or '').strip() != 'TOTAL ACTUALS & BUDGET:' \
            or ws['L5'].value != 'Level Service Proposed' or ws['M5'].value != 'Balanced Proposed':
        fail('fy27-proposals.xlsx row 404 / columns L, M no longer hold the totals cited')
    return Decimal(str(ws['L404'].value)), Decimal(str(ws['M404'].value))


def model():
    A = J.accounts()
    scope = [r for r in J.lines() if J.in_surplus_scope(A[r['account']])
             and J.is_expense(A[r['account']]) and r['fy'] in YEARS]
    disc = [r for r in scope if group(r['object'])]
    m = {'scope': scope, 'disc': disc}

    # 1. orders opened late
    t1 = {}
    for y in YEARS:
        po = [r for r in disc if r['fy'] == y and r['source'] == 'POE']
        lp = [r for r in po if late(r)]
        t1[y] = dict(n=len({r['doc_no'] for r in po}), n_late=len({r['doc_no'] for r in lp}),
                     usd=sum((r['amt'] for r in po), D0), usd_late=sum((r['amt'] for r in lp), D0))
    m['t1'] = t1

    # 2. invoices paid in June
    t2 = {}
    for y in YEARS:
        inv = [r for r in disc if r['fy'] == y and r['source'] in ('API', 'APM')]
        jun = [r for r in inv if r['effective_date'][5:7] == '06']
        d30 = [r for r in inv if r['effective_date'] == '%d-06-30' % y]
        t2[y] = dict(usd=sum((r['amt'] for r in inv), D0), jun=sum((r['amt'] for r in jun), D0),
                     d30=sum((r['amt'] for r in d30), D0))
    m['t2'] = t2

    # 3. orders open at 30 June: every encumbrance posting but the close. In a closed year
    # this equals minus the close (YEC) to the cent, asserted; FY2026 has not been closed.
    t3 = {}
    for y in YEARS:
        rs = [r for r in disc if r['fy'] == y and r['posts_to'] == 'encumbrance'
              and r['source'] != 'YEC']
        open_ = sum((r['amt'] for r in rs), D0)
        yec = sum((r['amt'] for r in disc if r['fy'] == y and r['source'] == 'YEC'), D0)
        if y != Y1 and open_ != -yec:
            fail('FY%d open orders %s do not equal the close %s' % (y, open_, -yec))
        # which orders were opened late: net open by order, attributed by its POE date
        by_po = defaultdict(lambda: D0)
        opened = {}
        for r in rs:
            by_po[r['doc_no']] += r['amt']
            if r['source'] == 'POE':
                opened.setdefault(r['doc_no'], r)
        open_late = sum((v for k, v in by_po.items() if k in opened and late(opened[k])), D0)
        all_scope = sum((r['amt'] for r in scope if r['fy'] == y
                         and r['posts_to'] == 'encumbrance' and r['source'] != 'YEC'), D0)
        t3[y] = dict(open=open_, open_late=open_late, all_scope=all_scope)
    m['t3'] = t3

    # 4. next-year costs charged to this year: fy_breakdown.is_prepaid, the one definition
    pre = [r for r in scope if FB.is_prepaid(r)]
    m['t4'] = {y: sum((r['amt'] for r in pre if r['fy'] == y), D0) for y in YEARS}
    m['t4_rows'] = pre
    if m['t4'][Y1] != ANCHOR_PREPAID or any(m['t4'][y] for y in BASE):
        fail('next-year charges no longer FY2026 only at %s: %s' % (ANCHOR_PREPAID, m['t4']))

    # 5. vendors paid only in June (discretionary invoices; masked payees never named)
    t5 = {}
    for y in YEARS:
        inv = [r for r in disc if r['fy'] == y and r['source'] in ('API', 'APM')
               and r['amt'] > 0]
        months = defaultdict(set)
        tot = defaultdict(lambda: D0)
        for r in inv:
            p = J.payee(r)
            if p is J.MASKED:
                continue
            months[p].add(r['effective_date'][5:7])
            tot[p] += r['amt']
        only = {p for p, ms in months.items() if ms == {'06'}}
        t5[y] = dict(vendors=len(months), only=len(only), usd=sum(tot.values(), D0),
                     only_usd=sum((tot[p] for p in only), D0),
                     top=sorted(((tot[p], p) for p in only), reverse=True)[:8])
    m['t5'] = t5

    # Orders by group, opened before the window or inside it, at their final value in the year.
    opened = {}
    for r in disc:
        if r['source'] == 'POE':
            k = (r['fy'], r['doc_no'])
            opened[k] = min(opened.get(k, r['effective_date']), r['effective_date'])
    dec = defaultdict(lambda: D0)
    for r in disc:
        k = (r['fy'], r['doc_no'])
        if r['source'] in ('POE', 'POM') and k in opened:
            dec[(r['fy'], group(r['object']), opened[k] >= '%d-%s' % (r['fy'], WINDOW))] += r['amt']
    m['dec'] = dec
    # The largest late orders of FY2026, by final value; a masked payee is never named.
    big = defaultdict(lambda: D0)
    first = {}
    for r in disc:
        k = (r['fy'], r['doc_no'])
        if (r['fy'] == Y1 and r['source'] in ('POE', 'POM') and k in opened
                and opened[k] >= '%d-%s' % (Y1, WINDOW)):
            big[r['doc_no']] += r['amt']
            if r['source'] == 'POE':
                first.setdefault(r['doc_no'], r)
    m['big'] = [(v, opened[(Y1, k)], first[k]) for k, v in
                sorted(big.items(), key=lambda kv: (-kv[1], kv[0]))[:10]]
    for y in YEARS:
        t1[y]['net_late'] = sum((dec[(y, g, True)] for g in LABEL), D0)
        t1[y]['net'] = t1[y]['net_late'] + sum((dec[(y, g, False)] for g in LABEL), D0)

    # The baseline: for each group, late orders over early orders in the OTHER years of
    # FY2023-FY2025, pooled. Expected late orders = that ratio times the year's own early orders.
    exp = {}
    for y in YEARS:
        others = [b for b in BASE if b != y]
        for g in LABEL:
            e = sum((dec[(b, g, False)] for b in others), D0)
            lt = sum((dec[(b, g, True)] for b in others), D0)
            ratio = lt / e if e else D0
            exp[(y, g)] = (dec[(y, g, False)] * ratio).quantize(Decimal('0.01'))
    m['exp'] = exp

    fb = FB.model()['years']
    m['left'] = {y: fb[y]['left'] for y in YEARS}
    m['printed_left'] = {y: fb[y]['printed_left'] for y in YEARS}
    if m['left'][Y1] != ANCHOR_LEFT or J.left([r for r in scope if r['fy'] == Y1]) != ANCHOR_LEFT:
        fail('FY2026 leftover is no longer %s' % ANCHOR_LEFT)

    recl = [r for r in scope if (r['fy'], r['journal']) == RECLASS_JOURNAL and r['source'] == 'GEN']
    if sum((r['amt'] for r in recl), D0) != -ANCHOR_RECLASS:
        fail('the 29 June reclass is no longer -%s on the general fund' % ANCHOR_RECLASS)
    m['reclass'] = ANCHOR_RECLASS
    return m


def render(m):
    t1, t2, t3, t4, t5, dec, exp = (m[k] for k in ('t1', 't2', 't3', 't4', 't5', 'dec', 'exp'))
    fy = lambda y: 'FY%d' % y
    late_tot = {y: sum((dec[(y, g, True)] for g in LABEL), D0) for y in YEARS}
    year_tot = {y: late_tot[y] + sum((dec[(y, g, False)] for g in LABEL), D0) for y in YEARS}
    exp_tot = {y: sum((exp[(y, g)] for g in LABEL), D0) for y in YEARS}
    excess = {y: late_tot[y] - exp_tot[y] for y in YEARS}
    before = {y: m['left'][y] + t4[y] + excess[y] for y in YEARS}
    share = {y: late_tot[y] / year_tot[y] for y in YEARS}
    peer = min(BASE, key=lambda b: abs(share[b] - share[Y1]))
    lo = sorted(b for b in BASE if b != peer)
    if not all(share[Y1] > Decimal('1.5') * share[b] for b in lo):
        fail('the prose says FY2026 ordered late at about twice the pace of %s; it no longer does' % lo)
    o = []
    w = o.append

    w('# A year-end spending rush in FY2026? Five tests, against FY2023-FY2025\n')
    w('<!-- GENERATED by scripts/build_year_end_rush.py from sources/data/munis-school-journal.csv. '
      'Do not edit by hand; --check fails if this file no longer reproduces. -->\n')
    w('Scope: the school general fund (fund 0100, department 300), the lines that make up the '
      'reported leftover. Window: 15 May to 30 June. FY2026 has not been closed in this run of '
      'the journal, so its open orders can still move.\n')

    w('## What the data shows\n')
    w('- **Next year\'s bills paid early: %s in %s, nothing in the three years before.** '
      'Nine collaborative tuition invoices numbered for %s were charged to %s on 30 June. '
      'Without them %s would have reported %s left, not %s.'
      % (usd(t4[Y1], True), fy(Y1), fy(Y1 + 1), fy(Y1), fy(Y1), usd(m['left'][Y1] + t4[Y1]),
         usd(m['left'][Y1], True)))
    w('- **Late orders: %s of %s\'s discretionary orders, by final value, were opened after '
      '15 May** (%s). In the three years before: %s. So %s ordered late at about the pace of '
      '%s, and about twice the pace of %s and %s. Against the three-year pattern that is %s '
      'more than usual (our estimate, method below).'
      % (pct(late_tot[Y1], year_tot[Y1]), fy(Y1), usd(late_tot[Y1]),
         ', '.join('%s %s' % (fy(b), pct(late_tot[b], year_tot[b])) for b in BASE), fy(Y1),
         fy(peer), fy(lo[0]), fy(lo[1]), usd(excess[Y1])))
    top3 = m['big'][:3]
    if (not all('CHROMEBOOK' in r['description'].upper() for _, _, r in top3)
            or sorted({d for _, d, _ in top3}) != ['%d-06-10' % Y1, '%d-06-25' % Y1]):
        fail('the prose says the three largest late orders were Chromebooks ordered 10 and 25 June')
    chrome = sum((v for v, _, _ in top3), D0)
    jun_hi = max(t2[b]['jun'] / t2[b]['usd'] for b in BASE)
    if not t2[Y1]['jun'] / t2[Y1]['usd'] > jun_hi:
        fail('the prose says FY2026 paid a larger June share than any baseline year')
    w('- **June payments: %s of %s\'s discretionary invoices were paid in June (%s), more than in '
      'any of the three years before (%s).** %s of it is dated 30 June. The three largest '
      'orders opened after 15 May were Chromebooks, %s together, ordered 10 and 25 June (test 1).'
      % (pct(t2[Y1]['jun'], t2[Y1]['usd']), fy(Y1), usd(t2[Y1]['jun']),
         ', '.join('%s %s' % (fy(b), pct(t2[b]['jun'], t2[b]['usd'])) for b in BASE),
         usd(t2[Y1]['d30']), usd(chrome)))
    w('- **Orders still open at 30 June: %s on discretionary lines in %s**, against %s, %s and '
      '%s in the three years before; %s of it ordered after 15 May.'
      % (usd(t3[Y1]['open']), fy(Y1), usd(t3[2023]['open']), usd(t3[2024]['open']),
         usd(t3[2025]['open']), usd(t3[Y1]['open_late'])))
    w('- **The other way: %s of collaborative tuition was moved off the general fund onto the '
      'circuit breaker on 29 June 2026.** Without that entry the leftover would have been '
      'smaller by the same amount. It is shown separately below and never netted in.\n'
      % usd(m['reclass'], True))

    w('## The leftover before the late spending\n')
    w('Reported leftover is what each year left unspent and uncommitted, counted the FY2026 way '
      'in every year (orders still open at the close subtracted), from `fy_breakdown.py`. The '
      'layers above it are added back.\n')
    w('| | ' + ' | '.join(fy(y) for y in YEARS) + ' |')
    w('|---|' + '---:|' * len(YEARS))
    w('| Leftover as reported | ' + ' | '.join(usd(m['left'][y], y == Y1) for y in YEARS) + ' |')
    w('| + next year\'s bills charged to this year (measured) | '
      + ' | '.join(usd(t4[y], y == Y1) if t4[y] else '--' for y in YEARS) + ' |')
    w('| + late discretionary spending above the usual (**our estimate**) | '
      + ' | '.join(usd(excess[y]) for y in YEARS) + ' |')
    w('| **= leftover before the late spending (our estimate)** | '
      + ' | '.join('**%s**' % usd(before[y]) for y in YEARS) + ' |')
    w('| *separately: charged to the circuit breaker instead, 29 June* | '
      + ' | '.join(usd(m['reclass'], True) if y == Y1 else '--' for y in YEARS) + ' |\n')
    w('**How the "above the usual" line is estimated (ours).** For each discretionary group, the '
      'ratio is orders opened 15 May-30 June over orders opened before 15 May, each at its final '
      'value in the year (opened, plus later changes and cancellations), pooled across the OTHER '
      'baseline years (%s is compared with %s-%s; each baseline year with the other two). That '
      'ratio, applied to the year\'s own early orders, is the late ordering the year would have '
      'had at the usual pace; the line is the actual late orders less that. A negative figure '
      'means less than usual. The baseline is only three years and one of them (FY2024) ordered '
      'late at the FY2026 pace, so the estimate is sensitive to which years are in it. Open '
      'orders at 30 June are not a third layer: a late order still open is already in this '
      'line. Invoices paid with no order, and journal entries moving costs onto grants, are '
      'not in it.\n'
      % (fy(Y1), fy(BASE[0]), fy(BASE[-1])))
    w('By group, %s:\n' % fy(Y1))
    w('| Discretionary group | Ordered before 15 May | Ordered 15 May-30 June | Usual late orders '
      '(our estimate) | Above the usual |')
    w('|---|---:|---:|---:|---:|')
    for g in LABEL:
        a, b, e = dec[(Y1, g, False)], dec[(Y1, g, True)], exp[(Y1, g)]
        w('| %s | %s | %s | %s | %s |' % (LABEL[g], usd(a), usd(b), usd(e), usd(b - e)))
    w('| **All discretionary** | %s | %s | %s | %s |\n'
      % (usd(year_tot[Y1] - late_tot[Y1]), usd(late_tot[Y1]), usd(exp_tot[Y1]), usd(excess[Y1])))

    w('## The five tests\n')
    w('Discretionary lines only, except test 4. Discretionary is ours, declared by object code in '
      'the generator: supplies (54xxxx), instructional materials (55xxxx), equipment and repairs '
      '(52xxxx less utilities), equipment purchases and capital (58xxxx), contracted services, '
      'dues and fees (53xxxx less transportation, tuition, athletic insurance and the physician '
      'stipend). Salaries, benefits, utilities, transportation and tuition are left out.\n')

    w('### 1. Purchase orders opened 15 May-30 June\n')
    w('| | Orders opened, year | of which after 15 May | Dollars as opened, year | of which after 15 May | At final value, year | of which after 15 May |')
    w('|---|---:|---:|---:|---:|---:|---:|')
    for y in YEARS:
        r = t1[y]
        w('| %s | %d | %d (%s) | %s | %s (%s) | %s | %s (%s) |' % (fy(y), r['n'], r['n_late'],
          pct(r['n_late'], r['n']), usd(r['usd']), usd(r['usd_late']), pct(r['usd_late'], r['usd']),
          usd(r['net']), usd(r['net_late']), pct(r['net_late'], r['net'])))
    w('\nFinal value is the amount opened plus later changes and cancellations. FY2024 shows why '
      'it matters: it opened %s of orders after 15 May and kept %s of them.\n'
      % (usd(t1[2024]['usd_late']), usd(t1[2024]['net_late'])))
    w('The ten largest orders opened after 15 May %d, at final value:\n' % Y1)
    w('| Opened | Order | Payee | Account | Order description | Final value |')
    w('|---|---|---|---|---|---:|')
    for v, d, r in m['big']:
        p = J.payee(r)
        w('| %s | `%s` | %s | %s | %s | %s |' % (d, r['doc_no'], 'masked' if p is J.MASKED else p,
          r['account_description'].title(), r['description'].strip(), usd(v, True)))
    w('')
    w('### 2. Discretionary invoices paid in June\n')
    w('| | Invoices paid, year | Paid in June | June share | of which dated 30 June |')
    w('|---|---:|---:|---:|---:|')
    for y in YEARS:
        r = t2[y]
        w('| %s | %s | %s | %s | %s |' % (fy(y), usd(r['usd']), usd(r['jun']), pct(r['jun'], r['usd']),
                                        usd(r['d30'])))
    w('\nAn invoice paid in June may settle an order placed months earlier, so this test measures '
      'when money left, not when it was ordered. Test 1 and the bridge measure the order.\n')
    w('### 3. Orders still open at 30 June (carried into the next year)\n')
    w('| | Discretionary orders open | of which ordered after 15 May | All school general fund orders open |')
    w('|---|---:|---:|---:|')
    for y in YEARS:
        r = t3[y]
        w('| %s | %s | %s | %s |' % (fy(y), usd(r['open']), usd(r['open_late']), usd(r['all_scope'])))
    w('\nIn FY2023-FY2025 this is what the year-end close carried forward, to the cent. FY2026 has '
      'not been closed, so its figure is the orders open when the Town ran the report.\n')
    w('### 4. Next year\'s costs charged to this year\n')
    w('| | Invoices numbered for the next fiscal year, charged to this one |')
    w('|---|---:|')
    for y in YEARS:
        w('| %s | %s |' % (fy(y), usd(t4[y], True) if t4[y] else '--'))
    rows = m['t4_rows']
    w('\nThe search covers every invoice on every school general fund line. Only one payee\'s '
      'invoice numbers carry a fiscal year (FLLAC: `26L2KEY..` in FY2026, `25L2KEY..` in FY2025), '
      'so only that payee\'s prepayments can be read off the number (`fy_breakdown.is_prepaid`). '
      'In %s: %d invoices `%s` to `%s`, journal `%s`, check %s, dated %s. The invoice descriptions '
      'the journal carries are cut to eighteen characters, so a search of them for "FY27" or a '
      'service period has little power: nothing was found, and that is a statement about the '
      'instrument, not about the invoices.\n'
      % (fy(Y1), len(rows), min(r['doc_no'] for r in rows), max(r['doc_no'] for r in rows),
         rows[0]['journal'], rows[0]['check_no'], rows[0]['effective_date']))
    w('### 5. Vendors paid only in June\n')
    w('| | Vendors paid on discretionary lines | Paid only in June | Dollars to June-only vendors | share of the year\'s discretionary invoices |')
    w('|---|---:|---:|---:|---:|')
    for y in YEARS:
        r = t5[y]
        w('| %s | %d | %d | %s | %s |' % (fy(y), r['vendors'], r['only'], usd(r['only_usd']),
                                         pct(r['only_usd'], r['usd'])))
    w('\nThe largest June-only payees in %s: %s. Masked payees are left out of this test and '
      'never named.\n' % (fy(Y1), '; '.join('%s %s' % (p, usd(v)) for v, p in t5[Y1]['top'])))

    w('## What it does not show\n')
    w('- **Why.** Nothing in the journal records the reason for an order. A late order can be a '
      'rush to use money before it lapses, a purchase planned for the summer when buildings are '
      'empty, a delayed delivery, or an order held until the year\'s tuition and special education '
      'costs were known. The data cannot tell these apart.')
    w('- **What was bought, or whether it was needed.** The journal gives a vendor, an account and '
      'an eighteen-character description. Registered as a gap: *%s* (`money-gaps.csv`).' % GAP_WHAT)
    w('- **The size of any deficit.** Nothing here measures a deficit in FY2026 or FY2027. It '
      'measures when money was committed.')
    w('- **FY2026 is not closed.** Its open orders, and so its leftover, can still move at the '
      'close.\n')

    w('## A possible explanation, offered as a hypothesis\n')
    w('TJ was told there was a "mad dash of spending" at the FY2026 year end because of a large '
      'deficit. Two readings of "deficit" lead to two different hypotheses, and the tests bear on '
      'them differently:\n')
    w('1. **A rush to spend a leftover before it lapses.** Unspent general fund money returns to '
      'the town at the close. If this were the cause, late discretionary orders would run above '
      'the usual pace. What the tests found: %s ordered late at about twice the pace of %s and %s but '
      'at the pace of %s, and paid a larger share of its invoices in June than any of the three. '
      'Consistent with a rush; also consistent with %s\'s pattern recurring, and the three-year '
      'baseline cannot separate the two.'
      % (fy(Y1), fy(lo[0]), fy(lo[1]), fy(peer), fy(peer)))
    lv, bal = level_gap()
    w('2. **Prepaying a short year.** The district\'s FY2027 balanced proposal was %s below its '
      'level-service proposal (`budget-workbooks/fy27-proposals.xlsx`, sheet `FY27 Budget '
      'Projection`, `L404` = %s Level Service Proposed, `M404` = %s Balanced Proposed). '
      'If this were the cause, FY2027 costs '
      'would be charged to FY2026 money. What the tests found: one instance of that shape, %s '
      'of FLLAC tuition numbered for %s, and none in the three years before. It is the largest '
      'layer in the bridge. Whether it was paid early to ease %s, or because the invoices '
      'arrived then, nothing here says.\n'
      % (usd(lv - bal), usd(lv, True), usd(bal, True), usd(t4[Y1], True), fy(Y1 + 1), fy(Y1 + 1)))
    w('Nothing here establishes either motive. The timing is measured; the reason is not. What '
      'would settle it: the purchase orders opened after 15 May 2026 with their requisitions and '
      'approvals, and FLLAC\'s invoices `27L2KEY11`-`27L2KEY19` with their service dates.\n')
    return '\n'.join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text = render(model())
    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if cur != text:
            sys.exit('build_year_end_rush: %s is stale; re-run without --check' % OUT)
        print('build_year_end_rush: %s reproduces' % os.path.relpath(OUT, ROOT))
        return
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(text)
    os.replace(tmp, OUT)
    print('wrote', os.path.relpath(OUT, ROOT))


if __name__ == '__main__':
    main()
