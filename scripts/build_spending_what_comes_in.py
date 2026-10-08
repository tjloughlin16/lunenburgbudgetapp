#!/usr/bin/env python3
"""Are we spending what comes in? -- report 7 of notes/REPORTS-TO-GENERATE.md, for the schools.

    python3 scripts/build_spending_what_comes_in.py           # write the .md, the payload, the charts
    python3 scripts/build_spending_what_comes_in.py --check   # fail if any of them is stale

TJ, 5 October 2026: *"are we spending what we are earning? If we take in a ton of money from
fees and grants, are we actually spending it?"*

THIS IS THE FLOW VIEW OF THE FUNDS /analysis/sitting-on-money HOLDS AS BALANCES. That report
answers "what is held at each 30 June"; this one answers "what came in and what went out in
each year", fund by fund, for the four CLOSED years the MUNIS period-13 ledgers cover,
FY2023-FY2026. The fund grouping and names are IMPORTED from build_sitting_on_money.py --
one table, one place -- and the two reports are made to agree:

  * FY2024-FY2026: each fund's in-minus-out here must equal the change in the balance the
    published sitting-on-money payload carries. Same ledger, so this is a consistency check,
    not an independent one, and it is said so.
  * FY2023: the annual town report prints each fund's receipts, disbursements and balances
    -- a different document. Receipts and disbursements are compared fund by fund with the
    ledger, the report's own forward + net = carried identity is tested, and the report's
    opening balance is compared with the previous report's closing one. Every miss is
    published, not smoothed.
  * the 30 June 2025 balances are already proved to the cent against the Town's March 2026
    special revenue report by sitting-on-money's own chain, which refuses to build if not.

WHAT "PAYS ITS OWN WAY" CAN MEAN HERE (rule 11). A fee fund that takes in more than it
spends covers the costs BOOKED TO IT. Custodians, utilities, administration and benefits
booked in the general fund are not in it. The only place the ledger lets that be tested is
where the general fund books spending under the SAME DESE function code as the fund: that
is computed for every fee and lunch fund, and it is true of athletics alone.

Nothing here explains WHY a fund spent more or less than came in. Where a document says
why, it is quoted as what that document says; everything else is a hypothesis (rule 7).
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conclusions import conclusion, emit, figure, usd, pct  # noqa: E402
import build_sitting_on_money as SOM  # noqa: E402  -- the fund grouping, in ONE place

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
ID = 'spending-what-comes-in'
MD = os.path.join(ROOT, 'sources', 'analyses', ID + '.md')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', ID + '.json')
CHARTS = os.path.join(ROOT, 'sources', 'analyses', 'charts')
CHART_NAMES = ('kinds', 'funds', 'athletics')
MUNIS = os.path.join(DATA, 'munis-school-ytd.csv')
SRF = os.path.join(DATA, 'special-revenue-read.csv')
GAPS = os.path.join(DATA, 'money-gaps.csv')
SOM_PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'sitting-on-money.json')
MINUTES = os.path.join(ROOT, 'sources', 'meetings', 'text')
YEARS = (2023, 2024, 2025, 2026)
TOL = 0.005
# Dates and years are not derived figures; they are declared to the rule-2 check as literals.
DATES = ('30 June 2022', '30 June 2026', 'FY2023–FY2026', 'FY2022', 'FY2023', 'FY2024',
         'FY2025', 'FY2026')


def fail(msg):
    raise SystemExit('build_spending_what_comes_in: REFUSING TO WRITE -- ' + msg)


money = SOM.money
usdk = SOM.usdk

# ======================================================================================
# THE KINDS. Five come from sitting-on-money's table; two are ours, for the funds that
# table does not carry (it carries the fourteen funds an annual report balance can be
# matched to). OURS: a 2xxx fund that is not lunch or the circuit breaker is a grant, by
# MUNIS's own numbering; a 13xx fund outside the fourteen is "other", and must be empty.
# ======================================================================================
KINDS = [(k, l) for k, l in SOM.SCHOOL_CATS] + [
    ('grants', 'Grants (federal and state, every other 2xxx fund)'),
]
SHORT = dict(SOM.SHORT, grants='Grants')
COLOR = dict(SOM.CAT_COLOR, grants='#64748b')
# How a resident says each fund, for the cards only; the tables keep the report's names.
PLAIN = {'2640': 'the circuit breaker', '1308': 'school choice', '2200': 'lunch',
         '1301': 'athletics', '1305': 'after-school activities', '1312': 'extended day',
         '1306': 'facilities rental', '1302': 'adult education', '1300': 'lost books',
         '1310': 'Greenthumb', '1314': 'vending', '1311': 'the school gift fund',
         '1315': 'the Family Network gift fund', '1549': 'the technology gift fund'}
if set(PLAIN) != set(SOM.SCHOOL_FUNDS):
    raise SystemExit('PLAIN names a different set of funds than sitting-on-money carries')


def kind_of(fund):
    if fund in SOM.SCHOOL_FUNDS:
        return SOM.SCHOOL_FUNDS[fund][0]
    if fund.startswith('2'):
        return 'grants'
    return 'other'


# ======================================================================================
# 1. THE FLOWS, read from the ledger here rather than borrowed, so the reconciliation
#    with sitting-on-money is two reads of one ledger meeting, not one read agreeing with
#    itself.
# ======================================================================================

def flows():
    rev, exp, enc = defaultdict(float), defaultdict(float), defaultdict(float)
    names, func = {}, defaultdict(float)
    for r in csv.DictReader(open(MUNIS, encoding='utf-8')):
        if r['report'] != 'special-school' or r['period'] != '13':
            continue
        y = int(r['fiscal_year'])
        if y not in YEARS:
            fail('a special-school year %d outside %s' % (y, YEARS))
        f = r['fund']
        v = money(r['ytd_expended'])
        if r['type'] == 'R':
            rev[(f, y)] += -v          # MUNIS prints revenue as a credit
        elif r['type'] == 'E':
            exp[(f, y)] += v
            enc[(f, y)] += money(r['encumbrances'])
            func[(f, r['account'].split('-')[3], y)] += v
        else:
            fail('row type %r' % r['type'])
    funds = sorted({f for f, _y in list(rev) + list(exp)})
    return funds, rev, exp, enc, func


def fund_names():
    """MUNIS's own fund titles, from the March 2026 special revenue report."""
    out = {}
    for r in csv.DictReader(open(SOM.Q3, encoding='utf-8')):
        out[r['fund'].lstrip("'")] = r['name'].strip()
    return out


def gf_by_function():
    t = defaultdict(float)
    for r in csv.DictReader(open(MUNIS, encoding='utf-8')):
        if r['report'] == 'gf-school' and r['period'] == '13':
            t[(r['account'].split('-')[3], int(r['fiscal_year']))] += money(r['ytd_expended'])
    return t


# A function code that says nothing about WHICH programme: the 1000s-of-a-series codes
# (2000, 4000, 0000) and 5200, benefits, which every programme has. A match on one of
# these is not a match on the programme. Ours, and it is stated on the page.
GENERIC = ('0000', '2000', '4000', '5200')

# ======================================================================================
# 2. THE ANNUAL REPORT'S FY2023 ROWS, for the reconciliation
# ======================================================================================

def annual_report():
    """Rows by name for the fourteen (whose names are unique), and EVERY row for totals --
    the schedule prints some grant names twice (two `FY23 #262` lines in FY2023), so a dict
    keyed by name would silently drop one."""
    rows, every = defaultdict(dict), defaultdict(list)
    docs = {}
    for r in csv.DictReader(open(SRF, encoding='utf-8')):
        if r['group'] != 'SCHOOL DEPARTMENT' or r['fy'] not in ('2022', '2023'):
            continue
        y = int(r['fy'])
        every[y].append(r)
        rows[y][r['fund']] = r
        docs[y] = r['document']
    for f, (_c, n) in SOM.SCHOOL_FUNDS.items():
        for y in (2022, 2023):
            if sum(1 for r in every[y] if r['fund'] == n) != 1:
                fail('%r is printed other than once in the FY%d schedule' % (n, y))
    return rows, every, docs


QUOTES = [
    dict(file='school-committee/2025-01-08-minutes-6948.txt', date='8 January 2025',
         body='School Committee',
         who='the district, presenting the school choice and facilities revolving accounts',
         text='these accounts are following the same patterns as other revolving accounts, '
              'which is the money coming in is not enough to cover the money going out',
         url='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_01082025-6948'),
    dict(file='school-committee/2025-02-05-minutes-7006.txt', date='5 February 2025',
         body='School Committee', who='the minutes, on the unaffiliated salary schedule',
         text='this is primarily for the extended day staff, which is a self-sustaining program '
              'and has no budgetary impact',
         url='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_02052025-7006'),
    dict(file='school-committee/2023-11-15-minutes-3952.txt', date='15 November 2023',
         body='School Committee', who='the district, presenting the athletics report',
         text='We could be looking at an increase in athletic fees in the next two years.',
         url='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_11152023-3952'),
    dict(file='school-committee/2026-08-26-minutes-7980.txt', date='26 August 2026',
         body='School Committee', who='the Superintendent, on restoring athletic transportation',
         text='Of that amount, $10,000 would come from the additional appropriation and $50,000 '
              'from the athletic revolving account.',
         url='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_08262026-7980'),
    dict(file='school-committee/2026-08-26-minutes-7980.txt', date='26 August 2026',
         body='School Committee', who='the same meeting',
         text='Town Meeting could not appropriate school revolving funds or circuit-breaker '
              'funds, which were school funds and, in some cases, restricted to specific purposes',
         url='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_08262026-7980'),
    dict(file='school-committee/2025-03-12-minutes-7098.txt', date='12 March 2025',
         body='School Committee', who='a resident, in public comment on the FY26 athletics cuts',
         text='I don\'t have the full picture for each sport because of this lack of information '
              'regarding cost to particular athletic programs',
         url='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_03122025-7098'),
    dict(file='school-committee/2025-03-12-minutes-7098.txt', date='12 March 2025',
         body='School Committee', who='another resident, the same evening',
         text='Splitting everything into revolving funds is not a good way to manage finances. We '
              'need to lay out all revenues and all expenses.',
         url='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_03122025-7098'),
    dict(file='finance-committee/2025-06-12-minutes-7273.txt', date='12 June 2025',
         body='Finance Committee', who='the minutes, summarising members',
         text='There are issues with finance management and the inability to see where grant '
              'money and revolving funds are being moved and spent.',
         url='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_06122025-7273'),
]


def check_quotes():
    for q in QUOTES:
        p = os.path.join(MINUTES, q['file'])
        if not os.path.exists(p):
            fail('%s is not on disk -- run sync_archive.py --pull' % q['file'])
        if SOM.flat(q['text']) not in SOM.flat(open(p, encoding='utf-8').read()):
            fail('quote not verbatim in %s: %r' % (q['file'], q['text'][:60]))


# Gaps this report cites. The first two are its own; the rest were registered by others and
# this report hits the same wall.
GAP_WHATS = [
    'Which school special revenue funds the period-13 special funds report leaves out',
    'What a fee-funded school programme costs that is not booked to its own fund',
    'Whether a general fund athletics line is net of the revolving fund',
    'What share of the schools’ grounds, custodial, heating and utility cost is athletics',
    'What the school grant funds held at 30 June 2024, 2025 and 2026',
    'What the town’s own special revenue funds held at 30 June 2024, 2025 and 2026',
]


def check_gaps():
    have = {r['what'].strip() for r in csv.DictReader(open(GAPS, encoding='utf-8'))}
    missing = [w for w in GAP_WHATS if w not in have]
    if missing:
        fail('these gaps are cited and not in money-gaps.csv: %s' % missing)


# ======================================================================================
# CHARTS FOR /docs AND THE PDF (the web page draws components; rule 7f)
# ======================================================================================
INK, MUTED, GRID = SOM.INK, SOM.MUTED, SOM.GRID
IN_C, OUT_C = '#2f8f4e', '#dc2626'


def kinds_svg(kinds):
    W, H = 960, 520
    cols, pw, ph = 3, 300, 200
    top = max(max(y['in'], y['out']) for k in kinds for y in k['years'])
    b = ['<text x="16" y="24" font-size="14" font-weight="700" fill="%s">Money in and money '
         'out of the school funds, by kind, FY2023 to FY2026</text>' % INK]
    for i, k in enumerate(kinds):
        ox, oy = 20 + (i % cols) * (pw + 15), 50 + (i // cols) * (ph + 30)
        base, plot = oy + ph - 20, ph - 60
        b.append('<text x="%d" y="%d" font-size="12" font-weight="700" fill="%s">%s</text>'
                 % (ox, oy + 12, INK, SOM.esc(k['short'])))
        b.append('<text x="%d" y="%d" font-size="10.5" fill="%s">four years: in %s, out %s, net %s</text>'
                 % (ox, oy + 27, MUTED, usdk(k['in']), usdk(k['out']), usdk(k['net'])))
        b.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (ox, base, ox + pw - 10, base, GRID))
        gw = (pw - 10) / len(k['years'])
        for j, y in enumerate(k['years']):
            x = ox + j * gw + 6
            for m, (key, c) in enumerate((('in', IN_C), ('out', OUT_C))):
                h = y[key] / top * plot
                b.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                         % (x + m * (gw - 12) / 2, base - h, (gw - 12) / 2 - 2, h, c))
            b.append('<text x="%.1f" y="%d" font-size="10" text-anchor="middle" fill="%s">FY%d</text>'
                     % (x + (gw - 12) / 2, base + 13, MUTED, y['fy']))
    b.append('<rect x="20" y="%d" width="10" height="10" fill="%s"/><text x="34" y="%d" font-size="11" '
             'fill="%s">came in (revenue)</text>' % (H - 18, IN_C, H - 9, INK))
    b.append('<rect x="170" y="%d" width="10" height="10" fill="%s"/><text x="184" y="%d" font-size="11" '
             'fill="%s">went out (expenditure)</text>' % (H - 18, OUT_C, H - 9, INK))
    return SOM.svg_wrap(W, H, 'Money in and out of the school funds by kind', b)


def funds_svg(funds):
    rows = [f for f in funds if f['active'] and f['kind'] != 'grants']
    W, rh = 900, 26
    H = 70 + rh * len(rows) + 30
    lab, cw = 300, 140
    top = max(abs(y['net']) for f in rows for y in f['years'])
    b = ['<text x="16" y="24" font-size="14" font-weight="700" fill="%s">Each fund, in minus out, '
         'every year (green: more came in; red: more went out)</text>' % INK]
    for j, y in enumerate(YEARS):
        b.append('<text x="%d" y="52" font-size="11" text-anchor="middle" fill="%s">FY%d</text>'
                 % (lab + j * cw + cw / 2, MUTED, y))
    for i, f in enumerate(rows):
        yy = 62 + i * rh
        b.append('<text x="16" y="%d" font-size="11" fill="%s">%s (%s)</text>'
                 % (yy + 15, INK, SOM.esc(f['name']), f['fund']))
        for j, y in enumerate(f['years']):
            cx = lab + j * cw + cw / 2
            w = abs(y['net']) / top * (cw / 2 - 6)
            x = cx if y['net'] >= 0 else cx - w
            b.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s"/>' % (cx, yy + 2, cx, yy + 20, GRID))
            b.append('<rect x="%.1f" y="%d" width="%.1f" height="16" fill="%s"/>'
                     % (x, yy + 3, w, IN_C if y['net'] >= 0 else OUT_C))
    return SOM.svg_wrap(W, H, 'Each school fund, in minus out, by year', b)


def athletics_svg(ath):
    W, H, L, B, T = 760, 320, 70, 250, 50
    top = max(y['gf_spent'] + y['fund_spent'] for y in ath['years'])
    scale = (B - T) / top
    gw = (W - L - 20) / len(ath['years'])
    b = ['<text x="16" y="24" font-size="14" font-weight="700" fill="%s">Athletics spending '
         'as booked: the general fund and the fee fund, with what the fees brought in</text>' % INK,
         '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (L, B, W - 20, B, GRID)]
    for i, y in enumerate(ath['years']):
        x = L + i * gw + 20
        bw = gw - 60
        h1, h2 = y['gf_spent'] * scale, y['fund_spent'] * scale
        b.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#2b6cb0"/>' % (x, B - h1, bw, h1))
        b.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>' % (x, B - h1 - h2, bw, h2, IN_C))
        fy_ = B - y['fees_in'] * scale
        b.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="3"/>'
                 % (x - 6, fy_, x + bw + 6, fy_, INK))
        b.append('<text x="%.1f" y="%.1f" font-size="10" text-anchor="middle" fill="%s">%s</text>'
                 % (x + bw / 2, B - h1 - h2 - 5, INK, usdk(y['gf_spent'] + y['fund_spent'])))
        b.append('<text x="%.1f" y="%d" font-size="10.5" text-anchor="middle" fill="%s">FY%d</text>'
                 % (x + bw / 2, B + 15, MUTED, y['fy']))
    b.append('<rect x="%d" y="%d" width="10" height="10" fill="#2b6cb0"/><text x="%d" y="%d" font-size="10.5" '
             'fill="%s">general fund, function 3510</text>' % (L, H - 40, L + 14, H - 31, INK))
    b.append('<rect x="%d" y="%d" width="10" height="10" fill="%s"/><text x="%d" y="%d" font-size="10.5" '
             'fill="%s">athletics fee fund 1301</text>' % (L + 210, H - 40, IN_C, L + 224, H - 31, INK))
    b.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="3"/><text x="%d" y="%d" '
             'font-size="10.5" fill="%s">fees received into fund 1301</text>'
             % (L + 400, H - 35, L + 420, H - 35, INK, L + 426, H - 31, INK))
    return SOM.svg_wrap(W, H, 'Athletics spending as booked', b)


# ======================================================================================
# THE REPORT
# ======================================================================================

def build():
    check_quotes()
    check_gaps()
    funds, rev, exp, enc, func = flows()
    names = fund_names()
    gf = gf_by_function()
    ar, ar_every, ar_docs = annual_report()

    # ---- every fund must have a kind, and "other" must be empty --------------------
    for f in funds:
        if kind_of(f) == 'other' and any(abs(rev[(f, y)]) + abs(exp[(f, y)]) > TOL for y in YEARS):
            fail('fund %s is neither one of the fourteen nor a grant, and it moved money' % f)
        if f not in names:
            fail('fund %s has no MUNIS name in the March 2026 report' % f)
    for f in SOM.SCHOOL_FUNDS:
        if f not in funds:
            fail('sitting-on-money fund %s is not in the special-funds ledger' % f)

    # ---- per fund ------------------------------------------------------------------
    som = json.load(open(SOM_PAYLOAD, encoding='utf-8'))
    som_bal = {r['fund']: {int(k): v for k, v in r['balances'].items()} for r in som['school_funds']}
    _years, _by, fund_year, _printed = SOM.srf()
    fund_rows = []
    for f in funds:
        k = kind_of(f)
        if k == 'other':
            continue
        ys = [dict(fy=y, **{'in': round(rev[(f, y)], 2), 'out': round(exp[(f, y)], 2),
                            'net': round(rev[(f, y)] - exp[(f, y)], 2)}) for y in YEARS]
        t_in, t_out = sum(y['in'] for y in ys), sum(y['out'] for y in ys)
        row = dict(fund=f, kind=k, munis_name=names[f],
                   name=SOM.SCHOOL_FUNDS[f][1] if f in SOM.SCHOOL_FUNDS else names[f].title(),
                   years=ys, total_in=round(t_in, 2), total_out=round(t_out, 2),
                   net=round(t_in - t_out, 2),
                   years_out_above_in=sum(1 for y in ys if y['net'] < -TOL),
                   active=any(abs(y['in']) + abs(y['out']) > TOL for y in ys))
        if f in SOM.SCHOOL_FUNDS:
            row['balance_2022'] = round(fund_year[(f, 2022)], 2)
            row['balance_2026'] = round(som_bal[f][2026], 2)
        fund_rows.append(row)
    fourteen = [r for r in fund_rows if r['fund'] in SOM.SCHOOL_FUNDS]
    by_fund = {r['fund']: r for r in fund_rows}

    # ---- per kind ------------------------------------------------------------------
    kinds = []
    for k, label in KINDS:
        rs = [r for r in fund_rows if r['kind'] == k]
        ys = []
        for i, y in enumerate(YEARS):
            a = sum(r['years'][i]['in'] for r in rs)
            o = sum(r['years'][i]['out'] for r in rs)
            ys.append({'fy': y, 'in': round(a, 2), 'out': round(o, 2), 'net': round(a - o, 2)})
        kinds.append(dict(key=k, label=label, short=SHORT[k], funds=len(rs),
                          active_funds=sum(1 for r in rs if r['active']), years=ys,
                          **{'in': round(sum(y['in'] for y in ys), 2),
                             'out': round(sum(y['out'] for y in ys), 2),
                             'net': round(sum(y['net'] for y in ys), 2)},
                          years_out_above_in=sum(1 for y in ys if y['net'] < -TOL)))
    kd = {k['key']: k for k in kinds}

    # ---- RECONCILIATION with sitting-on-money and the annual report ----------------
    recon = []
    for r in fourteen:
        f, name = r['fund'], SOM.SCHOOL_FUNDS[r['fund']][1]
        # (a) FY2024-FY2026: the change in the published balance must equal in minus out.
        for i, y in enumerate(YEARS[1:], start=1):
            d = (som_bal[f][y] - som_bal[f][y - 1]) - r['years'][i]['net']
            if abs(d) > 0.01:
                fail('fund %s FY%d: sitting-on-money balance moved %.2f, in minus out is %.2f'
                     % (f, y, som_bal[f][y] - som_bal[f][y - 1], r['years'][i]['net']))
        # (b) FY2023, against the annual report -- a different document.
        a23, a22 = ar[2023].get(name), ar[2022].get(name)
        if not a23 or not a22:
            fail('fund %s %r is missing from the FY2022 or FY2023 annual report' % (f, name))
        y0 = r['years'][0]
        recon.append(dict(
            fund=f, name=name,
            ar_receipts=money(a23['receipts']), ledger_in=y0['in'],
            ar_disbursements=money(a23['disbursements']), ledger_out=y0['out'],
            receipts_diff=round(money(a23['receipts']) - y0['in'], 2),
            disbursements_diff=round(money(a23['disbursements']) - y0['out'], 2),
            identity_diff=round(money(a23['forward']) + y0['net'] - money(a23['carried']), 2),
            continuity_diff=round(money(a23['forward']) - money(a22['carried']), 2),
            som_2023=round(som_bal[f][2023], 2), ar_carried_2023=money(a23['carried'])))
        if abs(som_bal[f][2023] - money(a23['carried'])) > 0.01:
            fail('fund %s: sitting-on-money starts FY2023 at %.2f, the report printed %.2f'
                 % (f, som_bal[f][2023], money(a23['carried'])))
    for x in recon:
        x['ties'] = all(abs(x[k]) < 0.01 for k in ('receipts_diff', 'disbursements_diff',
                                                   'identity_diff', 'continuity_diff'))
    misses = [x for x in recon if not x['ties']]
    n14 = len(fourteen)
    net14 = round(sum(r['net'] for r in fourteen), 2)
    bal22 = round(sum(r['balance_2022'] for r in fourteen), 2)
    bal26 = round(sum(r['balance_2026'] for r in fourteen), 2)
    drift = round((bal26 - bal22) - net14, 2)
    # carried23 - carried22 = ledger net + (opening - previous closing) - (identity miss), so
    # the four-year balance change and the four-year net may differ ONLY by what the annual
    # report itself does not tie; anything else is an error in this script.
    drift_parts = round(sum(x['continuity_diff'] - x['identity_diff'] for x in recon), 2)
    if abs(drift - drift_parts) > 0.01:
        fail('balance change %.2f less net %.2f leaves %.2f the misses do not explain (%.2f)'
             % (bal26 - bal22, net14, drift, drift_parts))

    # FY2023 coverage: the whole school schedule against the whole special-funds report.
    ar23_in = round(sum(money(r['receipts']) for r in ar_every[2023]), 2)
    ar23_out = round(sum(money(r['disbursements']) for r in ar_every[2023]), 2)
    led23_in = round(sum(rev[(f, 2023)] for f in funds), 2)
    led23_out = round(sum(exp[(f, 2023)] for f in funds), 2)

    # ---- the general fund on the same function -------------------------------------
    fee_funds = [f for f, (c, _n) in SOM.SCHOOL_FUNDS.items() if c in ('fees', 'lunch')]
    function_test = []
    for f in fee_funds:
        codes = sorted({fn for (ff, fn, _y), v in func.items() if ff == f and abs(v) > TOL})
        for fn in codes:
            fund_sp = round(sum(func[(f, fn, y)] for y in YEARS), 2)
            gf_sp = round(sum(gf[(fn, y)] for y in YEARS), 2)
            function_test.append(dict(fund=f, name=SOM.SCHOOL_FUNDS[f][1], function=fn,
                                      generic=fn in GENERIC, fund_spent=fund_sp, gf_spent=gf_sp))
    testable = [t for t in function_test if not t['generic'] and t['gf_spent'] > TOL]
    if [t['function'] for t in testable] != ['3510']:
        fail('the shared-function test now finds %s, not athletics alone -- re-read the page'
             % [(t['fund'], t['function']) for t in testable])
    untestable = sorted({t['name'] for t in function_test if t['fund'] != '1301'})
    lunch_codes = sorted({t['function'] for t in function_test if t['fund'] == '2200' and not t['generic']})
    lunch_gf = round(sum(gf[(fn, y)] for fn in lunch_codes for y in YEARS), 2)

    ath_years = [dict(fy=y, gf_spent=round(gf[('3510', y)], 2),
                      fund_spent=round(exp[('1301', y)], 2), fees_in=round(rev[('1301', y)], 2))
                 for y in YEARS]
    ath_gf = round(sum(y['gf_spent'] for y in ath_years), 2)
    ath_fund = round(sum(y['fund_spent'] for y in ath_years), 2)
    ath_fees = round(sum(y['fees_in'] for y in ath_years), 2)
    ath_fund_share = round(100 * ath_fund / (ath_fund + ath_gf), 1)
    ath_fee_share = round(100 * ath_fees / (ath_fund + ath_gf), 1)
    for y in ath_years:
        y['fund_share_pct'] = round(100 * y['fund_spent'] / (y['fund_spent'] + y['gf_spent']), 1)
    ath = dict(years=ath_years, gf_spent=ath_gf, fund_spent=ath_fund, fees_in=ath_fees,
               fund_share_pct=ath_fund_share, fee_share_pct=ath_fee_share)

    # ---- lunch: where its money comes from -----------------------------------------
    lunch_src = defaultdict(float)
    for r in csv.DictReader(open(MUNIS, encoding='utf-8')):
        if r['report'] == 'special-school' and r['fund'] == '2200' and r['type'] == 'R':
            lunch_src[r['description'].strip()] += -money(r['ytd_expended'])
    fed = lunch_src.get('FEDERAL REVENUE THROUGH STATE', 0.0)
    if not fed:
        fail('no federal line in the lunch fund -- the description changed')
    lunch_fed_pct = round(100 * fed / sum(lunch_src.values()), 1)
    lunch_fees = lunch_src.get('USER CHARGES', 0.0)
    lunch_fee_pct = round(100 * lunch_fees / sum(lunch_src.values()), 1)

    # ---- persistence ----------------------------------------------------------------
    persist = [r for r in fourteen if r['years_out_above_in'] >= 3]
    persist_names = [r['name'] for r in persist]
    pl = [PLAIN[r['fund']] for r in persist]
    plain_list = ', '.join(pl[:-1]) + ' and ' + pl[-1] if len(pl) > 1 else pl[0]
    ext = by_fund['1312']
    ext_short = round(sum(-y['net'] for y in ext['years'][1:]), 2)
    if not all(y['net'] < 0 for y in ext['years'][1:]):
        fail('extended day no longer spent more than came in in each of FY2024-FY2026')
    enc_total = round(sum(enc.values()), 2)
    # Sentences below name years; these hold them to the data (rule 2 for years).
    if not (ext['years'][0]['net'] > 0):
        fail('extended day no longer took in more than it spent in FY2023')
    if not all(by_fund['2200']['years'][i]['net'] > 0 for i in (0, 1, 2)) or by_fund['2200']['years'][3]['net'] >= 0:
        fail('lunch no longer covered FY2023-FY2025 and fell short in FY2026')
    if not all(by_fund[f]['years'][i]['net'] < 0 for f in ('1308', '1306') for i in (0, 1)):
        fail('school choice and facilities use no longer both drew down in FY2023 and FY2024')
    if [x['fund'] for x in misses] != ['1301', '1310'] and abs(drift) < 0.01:
        fail('the FY2023 misses changed; re-read the sentence that explains them')

    WORDS = SOM.WORDS
    nw = WORDS[n14]
    kinds_down = [k for k in kinds if k['key'] in dict(SOM.SCHOOL_CATS) and k['net'] < 0]
    gifts = kd['gifts']
    if gifts['net'] <= 0 or len(kinds_down) != len(SOM.SCHOOL_CATS) - 1:
        fail('the kinds no longer split four down and gifts up -- re-read the claims')

    # =================================================================================
    # CONCLUSIONS
    # =================================================================================
    conc = emit(ID, [
        conclusion(
            id='the-school-funds-drew-down',
            claim='The schools’ %s own funds spent %s more than came in over four years.'
                  % (nw, usd(-net14)),
            so_what='That money came out of balances built up to FY2022: it was spent, not held back.',
            detail='FY2023 to FY2026, the %s fee, choice, lunch, gift and circuit-breaker funds took '
                   'in %s and spent %s. Their combined balance fell from %s at 30 June 2022 to %s at '
                   '30 June 2026. Every kind spent more than it took in except the gift funds, which '
                   'took in %s more than they spent.'
                   % (nw, usd(sum(r['total_in'] for r in fourteen)), usd(sum(r['total_out'] for r in fourteen)),
                      usd(bal22), usd(bal26), usd(gifts['net'])),
            figures={'net': figure(-net14, usd(-net14)),
                     'in': figure(sum(r['total_in'] for r in fourteen), usd(sum(r['total_in'] for r in fourteen))),
                     'out': figure(sum(r['total_out'] for r in fourteen), usd(sum(r['total_out'] for r in fourteen))),
                     'bal22': figure(bal22, usd(bal22)), 'bal26': figure(bal26, usd(bal26)),
                     'gifts': figure(gifts['net'], usd(gifts['net']))},
            figure='net', kind='measured', bearing='sizes', allow=DATES,
            basis='`munis-school-ytd.csv`, special-school, period 13, FY2023-FY2026 (revenue and '
                  'expense per fund); balances from /analysis/sitting-on-money.',
            not_shown='Why each fund drew down. Spending a balance down can be a plan to use '
                      'accumulated fees, a fee set below cost, or one-time purchases; the ledger '
                      'gives amounts, not reasons.'),
        conclusion(
            id='three-funds-every-year',
            claim='%s of the %s funds spent more than came in, in three of the four years.'
                  % (WORDS[len(persist)].capitalize(), nw),
            so_what='%s: a pattern, not one bad year.' % plain_list.capitalize(),
            detail='Counted per fund, FY2023 to FY2026: a year counts when expenditure exceeded '
                   'revenue. No fund did it in all four years.',
            figures={'n': figure(len(persist), WORDS[len(persist)].capitalize(), unit='funds')},
            figure='n', kind='measured', bearing='sizes', allow=DATES,
            basis='`munis-school-ytd.csv`, special-school, period 13.',
            not_shown='Whether the pattern continues. Four closed years is what the ledgers cover.'),
        conclusion(
            id='extended-day-not-covering',
            claim='Extended day, minuted as self-sustaining, spent %s more than it took in since FY2024.'
                  % usd(ext_short),
            so_what='Its fees stopped covering its own booked spending; it ran on its balance instead.',
            detail='It took in more than it spent in FY2023 and less in each of FY2024, FY2025 and '
                   'FY2026. Carried forward, its balance stood at %s at 30 June 2026; that year-end '
                   'is carried through the ledger, not yet checked against a second document.'
                   % usd(ext['balance_2026']),
            figures={'short': figure(ext_short, usd(ext_short)),
                     'bal': figure(ext['balance_2026'], usd(ext['balance_2026']))},
            figure='short', kind='measured', bearing='lever', allow=DATES,
            basis='`munis-school-ytd.csv`, fund 1312; School Committee minutes, 5 February 2025.',
            not_shown='Why: a fee held while wages rose, more staff, fewer families, or a cost '
                      'recoded into the fund would all look the same here.'),
        conclusion(
            id='athletics-fees-pay-a-share',
            claim='Athletics fees paid for %s of the athletics spending the books show, FY2023–FY2026.'
                  % pct(ath_fee_share),
            so_what='The general fund carried most of it, under the same athletics function code.',
            detail='The fee fund spent %s and the general fund %s under function 3510, the only '
                   'fee-funded programme where both book to the same code. In FY2025 the fee fund '
                   'spent %s while the general fund spent %s.'
                   % (usd(ath_fund), usd(ath_gf), usd(ath_years[2]['fund_spent']), usd(ath_years[2]['gf_spent'])),
            figures={'share': figure(ath_fee_share, pct(ath_fee_share)),
                     'fund': figure(ath_fund, usd(ath_fund)), 'gf': figure(ath_gf, usd(ath_gf)),
                     'f25': figure(ath_years[2]['fund_spent'], usd(ath_years[2]['fund_spent'])),
                     'g25': figure(ath_years[2]['gf_spent'], usd(ath_years[2]['gf_spent']))},
            figure='share', kind='measured', bearing='lever', allow=DATES + ('3510',),
            basis='`munis-school-ytd.csv`: special-school fund 1301 and gf-school function 3510, '
                  'period 13.',
            not_shown='The whole cost of athletics: fields, custodians, utilities and buses booked '
                      'elsewhere are not in either figure (registered gaps).'),
        conclusion(
            id='lunch-is-federal-money',
            claim='School lunch runs on federal money: %s of its receipts, against %s from sales.'
                  % (pct(lunch_fed_pct), pct(lunch_fee_pct)),
            so_what='Whether lunch “pays its own way” is a question about reimbursement, not about prices.',
            detail='Four years, FY2023 to FY2026. In FY2026 it spent %s more than it took in, and its '
                   'balance fell to %s.' % (usd(-by_fund['2200']['years'][3]['net']), usd(by_fund['2200']['balance_2026'])),
            figures={'fed': figure(lunch_fed_pct, pct(lunch_fed_pct)),
                     'fee': figure(lunch_fee_pct, pct(lunch_fee_pct)),
                     'n26': figure(-by_fund['2200']['years'][3]['net'], usd(-by_fund['2200']['years'][3]['net'])),
                     'b26': figure(by_fund['2200']['balance_2026'], usd(by_fund['2200']['balance_2026']))},
            figure='fed', kind='measured', bearing='sizes', allow=DATES,
            basis='`munis-school-ytd.csv`, fund 2200 revenue lines, period 13.',
            not_shown='Whether FY2026’s shortfall is late reimbursement booked after the close or '
                      'a real loss; nothing here separates them.'),
    ])

    # =================================================================================
    # THE MARKDOWN
    # =================================================================================
    b = []
    w = b.append
    w('# Are we spending what comes in? The school funds, FY2023 to FY2026\n')
    w('**For each school fund outside the voted budget: what came in, what went out, every closed '
      'year the town’s ledger covers.**\n')
    w('---\n')
    w('## The short version\n')
    w('![Six small panels, one per kind of school fund, each with a pair of bars per year for money '
      'in and money out, FY2023 to FY2026: fee-funded, school choice, lunch and circuit breaker spent '
      'more than came in over the four years; gifts took in more; grants show a large FY2026 gap.]'
      '(charts/%s-kinds.svg)\n' % ID)
    w('**Yes: more than came in.** Over FY2023 to FY2026 the schools’ %s own funds (fees, school choice, '
      'lunch, gifts and the circuit breaker) took in %s and spent %s: **%s more out than in.** The '
      'difference came out of balances that had built up to a peak at 30 June 2022 (%s); by 30 June '
      '2026 they held %s. See [/analysis/sitting-on-money](/analysis/sitting-on-money) for the '
      'balances year by year.\n'
      % (nw, usd(sum(r['total_in'] for r in fourteen)), usd(sum(r['total_out'] for r in fourteen)),
         usd(-net14), usd(bal22), usd(bal26)))
    w('**Not every fund covers its own spending, even on its own books.** %s spent more than came '
      'in in three of the four years. Extended day — minuted in February 2025 as *“a self-sustaining '
      'program”* — spent %s more than it took in across FY2024 to FY2026.\n'
      % (plain_list[0].upper() + plain_list[1:], usd(ext_short)))
    w('**Athletics fees matched %s of the athletics spending the books show**, FY2023 to FY2026. '
      'The general fund booked %s of that spending under the same function code; the fee fund booked '
      'the other %s, partly from its balance. Athletics is the only fee-funded programme where the '
      'two can be set side by side.\n' % (pct(ath_fee_share), pct(100 - ath_fund_share), pct(ath_fund_share)))
    w('---\n')

    # ---- by kind
    w('## By kind, every year\n')
    w('Revenue and expenditure as the period-13 ledger books them (`munis-school-ytd.csv`, '
      '`report = special-school`). **Net** is in minus out: negative means the fund spent more than '
      'it took in that year, which for a revolving fund draws on its balance.\n')
    w('| kind | funds with activity | %s | four years in | four years out | net | years out > in |'
      % ' | '.join('FY%d net' % y for y in YEARS))
    w('|---|---:|%s---:|---:|---:|---:|' % ('---:|' * len(YEARS)))
    for k in kinds:
        w('| %s | %d | %s | %s | %s | **%s** | %d of %d |'
          % (k['label'], k['active_funds'], ' | '.join(usd(y['net']) for y in k['years']),
             usd(k['in']), usd(k['out']), usd(k['net']), k['years_out_above_in'], len(YEARS)))
    w('')
    w('**Grants are different and are shown apart.** A reimbursement grant spends first and is paid '
      'after, so a year of more out than in is usually timing, not a drawdown. FY2026 books %s of '
      'grant revenue against %s of grant spending; whether the rest arrives after the close, sits in '
      'a fund this report does not carry, or both, the ledger cannot say (registered gap). The grants '
      'are counted in no total above the fold.\n' % (usd(kd['grants']['years'][3]['in']), usd(kd['grants']['years'][3]['out'])))

    # ---- by fund
    w('## Fund by fund\n')
    w('![One row per school fund with activity (grants apart), one cell per year: a green bar where more came in '
      'than went out, red where more went out.](charts/%s-funds.svg)\n' % ID)
    w('The %s funds sitting-on-money carries, with their balance at each end of the four years. '
      'Names are the annual report’s; the number is MUNIS’s.\n' % nw)
    w('| fund | kind | %s | four-year net | years out > in | 30 June 2022 | 30 June 2026 |'
      % ' | '.join('FY%d in / out' % y for y in YEARS))
    w('|---|---|%s---:|---:|---:|---:|' % ('---:|' * len(YEARS)))
    for r in sorted(fourteen, key=lambda r: r['net']):
        w('| %s (%s) | %s | %s | **%s** | %d | %s | %s |'
          % (r['name'], r['fund'], SHORT[r['kind']],
             ' | '.join('%s / %s' % (usd(y['in']), usd(y['out'])) for y in r['years']),
             usd(r['net']), r['years_out_above_in'], usd(r['balance_2022']), usd(r['balance_2026'])))
    w('')
    gr = [r for r in fund_rows if r['kind'] == 'grants' and r['active']]
    w('The %d grant funds with activity, for completeness (no balances: none is published after '
      '30 June 2023 — registered gap):\n' % len(gr))
    w('| fund | MUNIS name | %s | four-year net |' % ' | '.join('FY%d in / out' % y for y in YEARS))
    w('|---|---|%s---:|' % ('---:|' * len(YEARS)))
    for r in sorted(gr, key=lambda r: r['fund']):
        w('| %s | %s | %s | %s |' % (r['fund'], r['munis_name'],
                                     ' | '.join('%s / %s' % (usd(y['in']), usd(y['out'])) for y in r['years']),
                                     usd(r['net'])))
    w('')

    # ---- pays its own way
    w('## Do the revolving funds pay their own way?\n')
    w('![Stacked bars per year: athletics spending booked to the general fund under function 3510 '
      'and to the athletics fee fund, with a line for the fees the fund received.](charts/%s-athletics.svg)\n' % ID)
    w('**On their own books, the test is simple: did each year’s revenue cover each year’s spending?** '
      'The tables above answer it. **The harder question is whether the general fund carries costs '
      'of the same programme** — and the ledger can answer that in exactly one place.\n')
    w('A fund’s spending is booked to a DESE function code. Where the general fund books spending '
      'under the same, programme-specific code, the two can be set side by side. Of the fee and lunch '
      'funds, **only athletics (function 3510) meets that test.** The others book to codes that name '
      'no programme — 2000 (instruction, generally), 4000 (operations), 5200 (benefits) — so whether '
      'the general fund carries any of their custodians, utilities, administration or benefits cannot '
      'be shown from this ledger: %s. That is not evidence that it does not; it is the limit of the '
      'instrument (registered gap). The lunch fund books food service to function %s, and the general '
      'fund books %s there in four years.\n'
      % (', '.join(untestable), ', '.join(lunch_codes) or 'none', usd(lunch_gf)))
    w('| year | general fund, function 3510 | fee fund 1301 spent | fee fund share of the two | fees received |')
    w('|---|---:|---:|---:|---:|')
    for y in ath_years:
        w('| FY%d | %s | %s | %s | %s |' % (y['fy'], usd(y['gf_spent']), usd(y['fund_spent']),
                                            pct(y['fund_share_pct']), usd(y['fees_in'])))
    w('| **four years** | **%s** | **%s** | **%s** | **%s** |' % (usd(ath_gf), usd(ath_fund),
                                                               pct(ath_fund_share), usd(ath_fees)))
    w('')
    w('**What the data shows.** The athletics fee fund paid %s of the athletics spending booked in '
      'either fund, and the fees themselves equal %s of it. The fund’s share swung from %s in FY2023 '
      'to %s in FY2025.\n'
      % (pct(ath_fund_share), pct(ath_fee_share), pct(ath_years[0]['fund_share_pct']),
         pct(ath_years[2]['fund_share_pct'])))
    w('**What it does not show.** Why the split moved. Costs may have been moved between the two '
      'deliberately, the fund may have been rested to rebuild its balance (it took in %s more than it '
      'spent in FY2025), or a general fund line may be budgeted net of the revolving fund (registered '
      'gap). And it is not the whole cost of athletics: fields, custodians and utilities sit in other '
      'general fund functions and are in neither column (registered gap). **Rule 11 applies to every '
      'fund here: covering its costs means covering the costs booked to it.**\n'
      % usd(by_fund['1301']['years'][2]['net']))
    w('**Lunch is not a fee-funded programme.** Over the four years %s of its receipts were federal '
      'reimbursement through the state and %s were sales. It covered its booked spending in FY2023, '
      'FY2024 and FY2025 and fell %s short in FY2026; with federal money that dominant, a shortfall at '
      'the close may be a reimbursement booked after it — a hypothesis nothing here tests.\n'
      % (pct(lunch_fed_pct), pct(lunch_fee_pct), usd(-by_fund['2200']['years'][3]['net'])))
    w('**School choice and the circuit breaker are not fee funds either.** School choice is tuition '
      'the state pays for children who come in from other towns; the circuit breaker is the state’s '
      'reimbursement for high-cost special education. Both are meant to be spent, and both may lawfully '
      'carry a balance. Their four-year drawdowns (%s and %s) are spending of money already received.\n'
      % (usd(-kd['choice']['net']), usd(-kd['cb']['net'])))

    # ---- reconciliation
    w('## Does this agree with sitting-on-money?\n')
    w('**FY2024 to FY2026: yes, every fund, every year, to the cent** — the change in each balance '
      'sitting-on-money publishes equals in minus out here. That is two reads of one ledger agreeing, '
      'not a second document; the independent check is sitting-on-money’s own, which proves the 30 '
      'June 2025 balances against the Town’s March 2026 report.\n')
    w('**FY2023, against the annual town report (a different document): %d of the %s funds tie on '
      'every test** — receipts, disbursements, the report’s own forward-plus-net-equals-carried, and '
      'its opening balance against the FY2022 report’s closing one.\n' % (n14 - len(misses), nw))
    if misses:
        w('| fund | receipts: report less ledger | disbursements: report less ledger | forward + ledger net − carried | FY2023 opening − FY2022 closing |')
        w('|---|---:|---:|---:|---:|')
        for x in misses:
            w('| %s (%s) | %s | %s | %s | %s |' % (x['name'], x['fund'], usd(x['receipts_diff']),
                                                  usd(x['disbursements_diff']), usd(x['identity_diff']),
                                                  usd(x['continuity_diff'])))
        w('')
    if abs(drift) < 0.01:
        w('Across all %s, the balance fell %s from 30 June 2022 to 30 June 2026, and in minus out over '
          'the same four years sums to %s: they agree to the cent, because each miss above cancels '
          'within its own fund (the same amount on both sides of athletics; Greenthumb’s FY2023 '
          'opening balance is above its FY2022 closing one by the same amount the ledger books as an '
          'FY2023 receipt).\n'
          % (nw, usd(bal22 - bal26), usd(net14)))
    else:
        w('Across all %s, the balance fell %s from 30 June 2022 to 30 June 2026 and in minus out sums to '
          '%s; the %s between them is exactly the annual-report misses above, and nothing else.\n'
          % (nw, usd(bal22 - bal26), usd(net14), usd(drift)))
    w('**Coverage.** The FY2023 annual report prints %s received and %s spent across every school '
      'special revenue fund; the period-13 special funds report carries %s and %s. The difference is '
      'funds that report does not carry (registered gap). The %s funds are all in '
      'it; the grant totals here are only what it holds.\n'
      % (usd(ar23_in), usd(ar23_out), usd(led23_in), usd(led23_out), nw))

    # ---- what was said
    w('## What was said\n')
    w('Searched in the minutes for revolving funds, self-sustaining programmes, athletic fees and '
      'lunch (`scripts/search_minutes.py`). Each quote is checked verbatim against the minutes it '
      'cites every time this report is built.\n')
    for q in QUOTES:
        w('- **%s, %s** — %s: *“%s”* ([minutes](%s))' % (q['body'], q['date'], q['who'], q['text'], q['url']))
    w('')
    w('The first matches the ledger: school choice and facilities use both spent more than came in '
      'in FY2023 and FY2024. The second says extended day pays for itself; on its own books its fees '
      'stopped covering its spending from FY2024 and it ran on its balance. Whether the general fund '
      'carries any of its cost cannot be tested (it books to codes that name no programme), so “no '
      'budgetary impact” is neither confirmed nor contradicted here — but by the carried figure the '
      'balance that cushioned it is gone. The fourth and fifth are the same thing from two '
      'sides: a use of the athletics fund’s balance, which stood at %s at 30 June 2026 by '
      'sitting-on-money’s carried figure, and the limit on who may spend it.\n'
      % usd(by_fund['1301']['balance_2026']))
    w('**The two from 12 March 2025 were said in FY2025, the year the FY26 sports cuts were argued.** That year the '
      'athletics fee fund spent %s while %s of fees came in, the general fund booked %s under '
      'athletics, and the fund closed the year holding %s. Whether any of that balance was already '
      'committed, or could lawfully have carried a sport under discussion, the ledger cannot say. '
      'This report is the revenue-and-expense layout the second of them asks for, for the funds '
      'the ledgers carry.\n'
      % (usd(ath_years[2]['fund_spent']), usd(ath_years[2]['fees_in']), usd(ath_years[2]['gf_spent']),
         usd(som_bal['1301'][2025])))

    not_est = [
        'Why any fund spent more or less than it took in — the ledger gives amounts, not reasons.',
        'The whole cost of any fee-funded programme: costs booked to the general fund under generic '
        'function codes cannot be attributed (registered gap).',
        'Whether a general fund athletics line is budgeted net of the revolving fund (registered gap).',
        'Whether the FY2026 grant and lunch shortfalls are reimbursements booked after the close '
        '(registered gap).',
        'School funds the period-13 special funds report does not carry (registered gap).',
        'The FY2026 balances against any second document; they are carried through the ledger.',
        'The town’s own special revenue funds: these ledgers are the schools’ alone, and the town’s '
        'receipts and disbursements are read only to FY2023 (registered gap).',
        'Encumbrances: %s is still committed in these funds at the closes and is not counted as '
        'spent.' % usd(enc_total),
    ]
    w('## What it does not show\n')
    for x in not_est:
        w('- ' + x)
    w('')
    w('## Closes with\n')
    w('Each is a row in `sources/data/money-gaps.csv`:\n')
    for g in GAP_WHATS:
        w('- %s' % g)
    w('')
    w('## Method\n')
    w('- Revenue is the period-13 `ytd_expended` on revenue rows, sign reversed (MUNIS prints '
      'revenue as a credit); expenditure is `ytd_expended` on expense rows. Encumbrances are not '
      'counted as spent.')
    w('- The fund grouping is sitting-on-money’s, imported from `build_sitting_on_money.py`. Grants '
      '(every other 2xxx fund) are ours, by MUNIS’s numbering. Two 13xx funds outside the fourteen '
      'moved no money in any of the four years; the generator refuses to build if that changes.')
    w('- The shared-function test reads the DESE function code (the fourth segment of the account) '
      'on both sides; codes 0000, 2000, 4000 and 5200 name no programme and are not counted as a match. '
      'The generator refuses to build if the test ever finds a programme other than athletics.')
    w('- Verified by `scripts/verify_spending_what_comes_in.py`, which recomputes every conclusion '
      'figure by a second route.\n')
    w('## Sources\n')
    man = SOM.manifest()
    srcs = []
    for y in YEARS:
        srcs.append(SOM.source(man, 'town-ledgers/expenses/glytdbud-expense-fy%d-p13-special-school.xlsx' % y,
                               'munis_school_ytd', 'Town of Lunenburg (MUNIS), by records request',
                               'School special funds, period 13: each fund’s revenue and expense for '
                               'FY%d. Delivered 6 October 2026.' % y))
        srcs.append(SOM.source(man, 'town-ledgers/expenses/glytdbud-expense-fy%d-p13-gf-school.xlsx' % y,
                               'munis_school_ytd', 'Town of Lunenburg (MUNIS), by records request',
                               'School general fund, period 13, FY%d: spending by DESE function, '
                               'used for athletics (3510).' % y))
    for y in (2022, 2023):
        key = ar_docs[y][len('sources/'):]
        srcs.append(SOM.source(man, key, 'special_revenue_read', 'Town of Lunenburg',
                               'Annual town report FY%d, Special Revenue Funds schedule: each school '
                               'fund’s forward, receipts, disbursements and carried. The FY2023 '
                               'reconciliation.' % y))
    srcs.append(SOM.source(man, 'town-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx',
                           'school_special_revenue_fy26_q3', 'Town of Lunenburg (MUNIS), by records request',
                           'Every school special revenue fund to 31 March 2026: used here for MUNIS’s '
                           'fund names only.'))
    for q in QUOTES:
        stem = 'meetings/%s/%s.' % (q['file'].split('/')[0], os.path.basename(q['file'])[:-4])
        keys = sorted(k for k in man if k.startswith(stem))
        if not keys:
            fail('no archived document for the minutes %s (rule 12)' % q['file'])
        srcs.append(SOM.source(man, keys[0], 'minutes', 'Lunenburg %s' % q['body'],
                               'Minutes of %s: "%s"' % (q['date'], q['text'])))
    seen, uniq = set(), []
    for s in srcs:
        if s['path'] not in seen:
            seen.add(s['path'])
            uniq.append(s)
    srcs = uniq
    w('| document | what it gives here |')
    w('|---|---|')
    for s in srcs:
        w('| [%s](%s) | %s |' % (s['filename'], s['docs_url'], s['note'].replace('|', '/')))
    md = '\n'.join(b) + '\n'

    # =================================================================================
    # THE PAYLOAD
    # =================================================================================
    pay = dict(
        generated_by='scripts/build_spending_what_comes_in.py',
        about='For each school fund outside the voted budget: what came in and what went out, '
              'FY2023 to FY2026, and whether the revolving funds cover their own booked costs.',
        grain='DOLLARS of revenue and expenditure per fund per fiscal year, as the MUNIS period-13 '
              'ledger books them — flows, not balances. Balances are sitting-on-money’s.',
        stats=[
            dict(value=usd(-net14), tone='var(--series-cost)',
                 label='more spent than came in, FY2023–FY2026, across the schools’ %s fee, choice, '
                       'lunch, gift and circuit-breaker funds' % nw),
            dict(value='%s of %s' % (len(persist), n14),
                 label='funds that spent more than they took in, in three of the four years'),
            dict(value=pct(ath_fee_share),
                 label='of booked athletics spending matched by athletics fees, FY2023–FY2026'),
        ],
        years=list(YEARS),
        kinds=kinds,
        funds=fund_rows,
        athletics=ath,
        function_test=function_test,
        lunch_sources={k: round(v, 2) for k, v in sorted(lunch_src.items())},
        reconciliation=dict(fy2023=recon, balance_2022=bal22, balance_2026=bal26, net=net14,
                            difference=drift,
                            coverage_2023=dict(annual_report_in=ar23_in, annual_report_out=ar23_out,
                                               ledger_in=led23_in, ledger_out=led23_out)),
        encumbrances=enc_total,
        quotes=QUOTES,
        gaps=GAP_WHATS,
        sources=srcs,
        not_established=not_est,
        conclusions=conc,
    )
    pay_text = json.dumps(pay, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
    svgs = {'kinds': kinds_svg(kinds), 'funds': funds_svg(fund_rows), 'athletics': athletics_svg(ath)}
    return md, pay_text, svgs


def outputs(md, pay_text, svgs):
    out = [(MD, md), (PAYLOAD, pay_text)]
    for n in CHART_NAMES:
        out.append((os.path.join(CHARTS, '%s-%s.svg' % (ID, n)), svgs[n]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args(argv)
    md, pay_text, svgs = build()
    out = outputs(md, pay_text, svgs)
    if a.check:
        stale = [os.path.relpath(p, ROOT) for p, t in out
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != t]
        if stale:
            print('STALE: %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('%s.md, its payload and its three charts are current' % ID)
        return 0
    for p, t in out:
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            fh.write(t)
        os.replace(tmp, p)
    print('wrote %s' % ', '.join(os.path.relpath(p, ROOT) for p, _ in out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
