#!/usr/bin/env python3
"""Is anyone sitting on money? Town and schools -- report 9 of notes/REPORTS-TO-GENERATE.md.

    python3 scripts/build_sitting_on_money.py           # write the .md, the payload, the charts
    python3 scripts/build_sitting_on_money.py --check   # fail if any of them is stale

TJ, 5 October 2026: *"There are theories running around that the school (and now im
questioning the town) are not spending a ton of money they have. I need to figure out how
to show that."* And the caution the report list carries with it: *do not conclude from one
snapshot ... growth across YEARS is the finding.* So every pot here is a SERIES of year-end
balances, each from the document that prints it, and no two documents are ever added.

THE POTS, AND WHERE EACH ONE IS READ
  * special revenue funds, town and school, FY2011-FY2023: `special-revenue-read.csv`, the
    annual reports' schedule read off the page, every row and every printed GRAND TOTAL
    tying (PROVENANCE-special-revenue-read.md). This script refuses to write if a year's
    funds do not sum to the total the report prints.
  * fourteen school funds carried on to FY2026: the 30 June 2023 balance above, plus each
    year's revenue less expense from the MUNIS period-13 ledgers (`munis-school-ytd.csv`).
    The chain is PROVED, not assumed: its 30 June 2025 balance must equal, to the cent, the
    opening balance implied by the Town's 31 March 2026 special revenue report
    (`school-special-revenue-fy26-q3.csv`), a different document. A fund that does not
    tie is refused, not drawn.
  * the school general fund's turnback at the close, FY2023-FY2026: period-13
    `available_budget`, department 300.
  * free cash: the Town's fact sheet (FY2015-FY2025 closes) and the state's free cash
    proof (FY2021-FY2025 closes, with components). The two must agree where they overlap.
  * the general stabilization fund: `stabilization-balances.csv`, FY2011-FY2024, each
    year closed on the identities its own table prints.
  * unspent of the final budget, schools against the rest of the general fund,
    FY2010-FY2024: `gl-history.csv` -- the Finance Committee's ASSEMBLED workbook, so
    `stated` (rule 13a), and labelled so wherever it is used.

Nothing here explains WHY a balance moved. Where a document says why, it is quoted as what
that document says; everything else is a hypothesis and is labelled one (rule 7).
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conclusions import conclusion, emit, figure  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
ID = 'sitting-on-money'
MD = os.path.join(ROOT, 'sources', 'analyses', ID + '.md')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', ID + '.json')
CHARTS = os.path.join(ROOT, 'sources', 'analyses', 'charts')
CHART_NAMES = ('balances', 'school', 'turnback')

SRF = os.path.join(DATA, 'special-revenue-read.csv')
SRF_TOTALS = os.path.join(DATA, 'special-revenue-printed-totals.csv')
MUNIS = os.path.join(DATA, 'munis-school-ytd.csv')
Q3 = os.path.join(DATA, 'school-special-revenue-fy26-q3.csv')
FC_SHEET = os.path.join(DATA, 'free-cash-history-fincom.csv')
FC_PROOF = os.path.join(DATA, 'free-cash-proof.csv')
STAB = os.path.join(DATA, 'stabilization-balances.csv')
GL = os.path.join(DATA, 'gl-history.csv')
GAPS = os.path.join(DATA, 'money-gaps.csv')
MANIFEST = os.path.join(DATA, 'archive-manifest.csv')
MINUTES = os.path.join(ROOT, 'sources', 'meetings', 'text')
# The Town's FY27 budget release, quoted for the guide it cites. Checked verbatim on every build.
RELEASE_KEY = ('town-budget/docs/4090-click-here-for-a-release-on-quot-understanding-lunenburg-'
               'apos-s-fy27-budget-how-.pdf')
RELEASE_TEXT = os.path.join(ROOT, 'sources', 'town-budget', 'text', os.path.basename(RELEASE_KEY)[:-4] + '.txt')
GUIDE = '5-7% of its annual budget'


def fail(msg):
    raise SystemExit('build_sitting_on_money: REFUSING TO WRITE -- ' + msg)


def usd(v):
    v = round(float(v))
    return ('-$%s' if v < 0 else '$%s') % format(abs(v), ',d')


def usdk(v):
    v = float(v)
    if abs(v) >= 1e6:
        return '$%.1fM' % (v / 1e6)
    if abs(v) >= 1e3:
        return '$%dk' % round(v / 1e3)
    return '$%d' % round(v)


def money(s):
    return float(s) if (s or '').strip() not in ('', '-') else 0.0


# ======================================================================================
# 1. THE ANNUAL REPORTS' SPECIAL REVENUE SCHEDULE, FY2011-FY2023
# ======================================================================================

# WHICH SCHOOL FUND IS WHICH, by the name the annual report prints. Ours, read off the
# names -- the report prints no fund numbers. The circuit breaker is printed as
# "50/50 Grant Sped Tuitions"; that it IS the circuit breaker is established below, not
# assumed: its FY2023 receipts equal MUNIS fund 2640 SPECIAL ED CIRCUIT BREAKER's to the cent.
SCHOOL_FUNDS = {
    # munis fund : (category, the name the annual report prints)
    '2640': ('cb', '50/50 Grant Sped Tuitions'),
    '1308': ('choice', 'School Choice'),
    '2200': ('lunch', 'School Lunch'),
    '1301': ('fees', 'Chapter 658 School Athletics'),
    '1305': ('fees', 'After School Activities'),
    '1312': ('fees', 'Extended Day Revolving Fund'),
    '1306': ('fees', 'School Facilities Use'),
    '1302': ('fees', 'Adult Education'),
    '1300': ('fees', 'Recovery for Lost Books'),
    '1310': ('fees', 'Greenthumb Revolving'),
    '1314': ('fees', 'Vending Machine Revolving'),
    '1311': ('gifts', 'School Gift Fund'),
    '1315': ('gifts', 'Family Network Gift Fund'),
    '1549': ('gifts', 'Technology for School Children Gift Fund'),
}
FEE_NAMED = ('athletics', 'after-school', 'extended day', 'rentals')
N_FEES = sum(1 for c, _n in SCHOOL_FUNDS.values() if c == 'fees')
WORDS = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
         'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen']
N_WORD = WORDS[len(SCHOOL_FUNDS)]
NAME_TO_FUND = {name: f for f, (_c, name) in SCHOOL_FUNDS.items()}
SCHOOL_CATS = [
    ('cb', 'Circuit breaker (special education reimbursement)'),
    ('choice', 'School choice tuition received'),
    ('lunch', 'School lunch'),
    ('fees', 'Fee-funded revolving funds (%s and %s more)'
     % (', '.join(FEE_NAMED), WORDS[N_FEES - len(FEE_NAMED)])),
    ('gifts', 'Gift funds'),
]
SHORT = {'cb': 'Circuit breaker', 'choice': 'School choice', 'lunch': 'Lunch',
         'fees': 'Fee-funded revolving', 'gifts': 'Gifts'}

# THE TOWN'S SPECIAL REVENUE, split three ways because the three are different kinds of
# money. The enterprise funds are the five PROVENANCE-special-revenue-read.md names as
# sitting inside this schedule; the federal relief funds are the three pandemic accounts.
ENTERPRISE = ('Water Enterprise Fund', 'Sewer Enterprise Fund', 'Sewer Betterment Fund',
              'Solid Waste/Recycling Enterprise Fund', 'PEG Access Enterprise Fund')
RELIEF = ('ARPA Funds', 'Cares Act Funding - COVID', 'FEMA #4496 - COVID Grant')


def srf():
    rows = list(csv.DictReader(open(SRF, encoding='utf-8')))
    printed = {int(r['fy']): float(r['carried'])
               for r in csv.DictReader(open(SRF_TOTALS, encoding='utf-8'))}
    by = defaultdict(float)
    fund_year = {}
    for r in rows:
        y = int(r['fy'])
        v = money(r['carried'])
        n = r['fund']
        if r['group'] == 'SCHOOL DEPARTMENT':
            f = NAME_TO_FUND.get(n)
            k = SCHOOL_FUNDS[f][0] if f else 'school_other'
            if f:
                fund_year[(f, y)] = fund_year.get((f, y), 0.0) + v
        elif n in ENTERPRISE:
            k = 'enterprise'
        elif n in RELIEF:
            k = 'relief'
        else:
            k = 'town_other'
        by[(y, k)] += v
        by[(y, 'all')] += v
        if r['group'] == 'SCHOOL DEPARTMENT':
            by[(y, 'school_all')] += v
    years = sorted({int(r['fy']) for r in rows})
    # THE CATEGORIES MUST PARTITION THE PRINTED TOTAL, or a fund fell out of the split.
    for y in years:
        if abs(by[(y, 'all')] - printed[y]) > 0.005:
            fail('FY%d special revenue funds sum to %.2f, the report prints %.2f'
                 % (y, by[(y, 'all')], printed[y]))
        parts = sum(by[(y, k)] for k in ('cb', 'choice', 'lunch', 'fees', 'gifts',
                                         'school_other', 'enterprise', 'relief',
                                         'town_other'))
        if abs(parts - printed[y]) > 0.005:
            fail('FY%d categories do not partition the total' % y)
    for name in ENTERPRISE + RELIEF:
        if not any(r['fund'] == name for r in rows):
            fail('no fund named %r in the schedule -- the split matches nothing' % name)
    for f, (_c, name) in SCHOOL_FUNDS.items():
        if (f, 2023) not in fund_year:
            fail('school fund %s %r has no FY2023 row to carry forward' % (f, name))
    return years, by, fund_year, printed


# ======================================================================================
# 2. THE FOURTEEN SCHOOL FUNDS, CARRIED TO FY2026 AND PROVED AGAINST MARCH 2026
# ======================================================================================

def munis_special():
    net = defaultdict(float)       # (fund, fy) -> revenue less expense
    rev = defaultdict(float)
    exp = defaultdict(float)
    for r in csv.DictReader(open(MUNIS, encoding='utf-8')):
        if r['report'] != 'special-school' or r['period'] != '13':
            continue
        k = (r['fund'], int(r['fiscal_year']))
        v = money(r['ytd_expended'])
        if r['type'] == 'R':
            rev[k] += -v               # MUNIS prints revenue as a credit
        else:
            exp[k] += v
        net[k] += -v
    return net, rev, exp


def q3_opening():
    """The 1 July 2025 balance each fund's 31 March 2026 line implies: balance less what came
    in, plus what went out. An independent document, so it can prove the chain."""
    out, bal = {}, {}
    for r in csv.DictReader(open(Q3, encoding='utf-8')):
        f = r['fund'].lstrip("'")
        bal[f] = float(r['balance'])
        out[f] = (float(r['balance']) - float(r['revenue']) + float(r['salaries'])
                  + float(r['expenditure']) + float(r['encumbered']))
    return out, bal


def chain(fund_year):
    net, rev, exp = munis_special()
    opening, q3bal = q3_opening()
    bal = {}
    for f in SCHOOL_FUNDS:
        b = fund_year[(f, 2023)]
        bal[(f, 2023)] = b
        for y in (2024, 2025, 2026):
            b = b + net[(f, y)]
            bal[(f, y)] = b
        if f not in opening:
            fail('fund %s is not in the March 2026 report; the chain cannot be proved' % f)
        if abs(bal[(f, 2025)] - opening[f]) > 0.005:
            fail('fund %s: the chain gives %.2f at 30 June 2025, the March 2026 report '
                 'implies %.2f' % (f, bal[(f, 2025)], opening[f]))
    return bal, rev, exp, opening, q3bal


# ======================================================================================
# 3. THE SCHOOL GENERAL FUND AT THE CLOSE
# ======================================================================================

def school_gf():
    t = defaultdict(lambda: defaultdict(float))
    for r in csv.DictReader(open(MUNIS, encoding='utf-8')):
        if r['report'] != 'gf-school' or r['period'] != '13':
            continue
        y = int(r['fiscal_year'])
        for k in ('original_approp', 'transfers_adjustments', 'revised_budget',
                  'ytd_expended', 'encumbrances', 'available_budget'):
            t[y][k] += money(r[k])
    return {y: {k: round(v, 2) for k, v in d.items()} for y, d in sorted(t.items())}


# ======================================================================================
# 4. FREE CASH
# ======================================================================================

def free_cash():
    sheet = {}
    for r in csv.DictReader(open(FC_SHEET, encoding='utf-8')):
        # The fact sheet labels a certification by the year it is SPENT in; the balance it
        # certifies is the one at the close of the year before. "FY2026, certified
        # 3/11/2026" is free cash as of 1 July 2025 -- the FY2025 close.
        close = int(r['fiscal_year']) - 1
        sheet[close] = dict(amount=float(r['certified_free_cash']),
                            certified=r['date_certified'], pct=r['pct_of_budget'],
                            budget=float(r['prior_year_operating_budget']))
    proof = defaultdict(dict)
    for r in csv.DictReader(open(FC_PROOF, encoding='utf-8')):
        if r['town'] != 'Lunenburg':
            continue
        proof[int(r['year'])][r['line']] = float(r['amount'])
    for y, d in proof.items():
        c = d.get('Current Year Calculation')
        if y in sheet and abs(sheet[y]['amount'] - c) > 0.5:
            fail('free cash at the FY%d close: the Town prints %.0f, the state %.0f'
                 % (y, sheet[y]['amount'], c))
    if not proof:
        fail('no Lunenburg rows in the free cash proof')
    return sheet, dict(proof)


PROOF_LINES = [
    ('receipts', 'Excess/Shortfall Local Receipts (CL#6)', 'Local receipts above the estimate'),
    ('cherry', 'Excess/Shortfall Cherry Sheet Receipts (CL#8)', 'State aid above the estimate'),
    ('unspent', 'Add Unencumbered/Unexpended Appropriations (CL#11)',
     'Appropriations not spent or committed'),
    ('unused', 'Add Prior Year Free Cash Not Appropriated (CL#12)',
     'Last year’s free cash nobody appropriated'),
]


# ======================================================================================
# 5. STABILIZATION, 6. GL HISTORY
# ======================================================================================

def stabilization():
    out = {}
    for r in csv.DictReader(open(STAB, encoding='utf-8')):
        if r['name'].strip() != 'STABILIZATION':
            continue
        y = int(r['fy'])
        if y in out:
            fail('two general STABILIZATION rows for FY%d' % y)
        out[y] = dict(amount=float(r['ending_cash']), page=int(r['page']),
                      basis=r['basis'], document=r['document'])
    return dict(sorted(out.items()))


def unspent_share():
    t = defaultdict(lambda: [0.0, 0.0])
    for r in csv.DictReader(open(GL, encoding='utf-8')):
        if r['sheet'] != 'general_fund' or r['actual_is_partial'] == 'true':
            continue
        y = int(r['fiscal_year'])
        if y > 2024:
            continue
        side = 'school' if r['department_code'] in ('300', '301') else 'rest'
        t[(side, y)][0] += money(r['revised'])
        t[(side, y)][1] += money(r['actual'])
    years = sorted({y for _s, y in t})
    rows = []
    for y in years:
        row = dict(fy=y)
        for side in ('school', 'rest'):
            rv, ac = t[(side, y)]
            row[side + '_revised'] = round(rv, 2)
            row[side + '_unspent'] = round(rv - ac, 2)
            row[side + '_pct'] = round(100 * (rv - ac) / rv, 2)
        rows.append(row)
    tot = {}
    for side in ('school', 'rest'):
        rv = sum(t[(side, y)][0] for y in years)
        ac = sum(t[(side, y)][1] for y in years)
        tot[side] = dict(revised=round(rv, 2), unspent=round(rv - ac, 2),
                         pct=round(100 * (rv - ac) / rv, 2))
    return rows, tot


# ======================================================================================
# 7. WHAT WAS SAID -- verbatim, checked against the minutes
# ======================================================================================

QUOTES = [
    dict(file='school-committee/2026-08-26-minutes-7980.txt',
         date='26 August 2026', body='School Committee',
         who='a resident, speaking for herself in public comment',
         text='She referenced balances in several school-related accounts and questioned '
              'whether any portion of those funds could legally or appropriately be used to '
              'reduce pressure on the operating budget',
         url='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_08262026-7980'),
    dict(file='school-committee/2026-08-26-minutes-7980.txt',
         date='26 August 2026', body='School Committee',
         who='the same speaker, just before',
         text='referenced an estimated cost of approximately $19,350 to restore certain middle '
              'school sports',
         url='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_08262026-7980'),
    dict(file='finance-committee/2024-03-14-minutes-6469.txt',
         date='14 March 2024', body='Finance Committee',
         who='the district’s Director of Special Services, asked how the previous year’s '
             'tuition increase had been absorbed',
         text='it is probably absorbed with a lot of the carry over for the circuit breaker '
              'monies and that’s why that account has gone down',
         url='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_03142024-6469'),
    dict(file='school-committee/2025-01-08-minutes-6948.txt',
         date='8 January 2025', body='School Committee',
         who='the district, presenting the school choice and facilities revolving accounts',
         text='these accounts are following the same patterns as other revolving accounts, '
              'which is the money coming in is not enough to cover the money going out',
         url='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_01082025-6948'),
    dict(file='finance-committee/2026-05-28-minutes-7828.txt',
         date='28 May 2026', body='Finance Committee',
         who='two Finance Committee members',
         text='for the last 10 years the town has not collected less than 4 million dollars '
              'in local receipts. This year’s estimate is 3.535 million.',
         url='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_05282026-7828'),
    dict(file='finance-committee/2026-05-28-minutes-7828.txt',
         date='28 May 2026', body='Finance Committee',
         who='the same meeting',
         text='suggests having an analyst review all of the town’s policies on free cash and '
              'estimates',
         url='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_05282026-7828'),
]


def flat(s):
    return ' '.join(s.replace('ﬁ', 'fi').replace('ﬂ', 'fl').split())


def check_quotes():
    if flat(GUIDE) not in flat(open(RELEASE_TEXT, encoding='utf-8').read()):
        fail('the FY27 release no longer reads %r' % GUIDE)
    for q in QUOTES:
        p = os.path.join(MINUTES, q['file'])
        if not os.path.exists(p):
            fail('%s is not on disk -- run sync_archive.py --pull' % q['file'])
        if flat(q['text']) not in flat(open(p, encoding='utf-8').read()):
            fail('quote not verbatim in %s: %r' % (q['file'], q['text'][:60]))


# ======================================================================================
# 8. THE GAPS THIS REPORT REGISTERS -- the join must match (rule 7c)
# ======================================================================================

GAP_WHATS = [
    'What the town’s own special revenue funds held at 30 June 2024, 2025 and 2026',
    'What the school grant funds held at 30 June 2024, 2025 and 2026',
    'Why local receipts come in above the town’s own estimate',
    'How much of free cash is the schools’',
]


def check_gaps():
    have = {r['what'].strip() for r in csv.DictReader(open(GAPS, encoding='utf-8'))}
    missing = [w for w in GAP_WHATS if w not in have]
    if missing:
        fail('these gaps are cited and not in money-gaps.csv: %s' % missing)


# ======================================================================================
# SOURCES (rule 12)
# ======================================================================================

def manifest():
    return {r['key']: r for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}


def source(man, key, table, publisher, note):
    r = man.get(key)
    if not r:
        fail('%s is not in the archive manifest (rule 12)' % key)
    return dict(path='sources/' + key, sha256=r['sha256'], bytes=int(r['bytes']),
                url=(r.get('upstream') or '').strip(), docs_url='/docs/' + key,
                filename=key.split('/')[-1], table=table, publisher=publisher, note=note)


def sources(man, srf_docs):
    out = []
    for key in srf_docs:
        out.append(source(man, key, 'special_revenue_read', 'Town of Lunenburg',
                          'Annual town report, Special Revenue Funds schedule: each fund’s '
                          'balance carried forward at 30 June. Read off the page; every row '
                          'and the printed GRAND TOTAL tie (special-revenue-read.csv).'))
    for y in (2023, 2024, 2025, 2026):
        out.append(source(man, 'town-ledgers/expenses/glytdbud-expense-fy%d-p13-special-school.xlsx' % y,
                          'munis_school_ytd', 'Town of Lunenburg (MUNIS), by records request',
                          'School special funds, period 13: each fund’s revenue and expense for '
                          'the year. Delivered 6 October 2026.'))
        out.append(source(man, 'town-ledgers/expenses/glytdbud-expense-fy%d-p13-gf-school.xlsx' % y,
                          'munis_school_ytd', 'Town of Lunenburg (MUNIS), by records request',
                          'School general fund, department 300, period 13: budget, spent, '
                          'encumbered and available at the close.'))
    out.append(source(man, 'town-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx',
                      'school_special_revenue_fy26_q3', 'Town of Lunenburg (MUNIS), by records request',
                      'Every school special revenue fund to 31 March 2026, with its balance. '
                      'Used here only to PROVE the carried-forward balances, never as a year-end.'))
    out.append(source(man, 'state-dls/free-cash-proof-lunenburg.xlsx', 'free_cash_proof',
                      'Massachusetts Division of Local Services',
                      'The state’s free cash proof, 2021-2025: the certified figure and the '
                      'components it is built from.'))
    out.append(source(man, 'budget-workbooks/finance-committee/fy27-budget/tm-warrant/free-cash-fact-sheet.docx',
                      'free_cash_history_fincom', 'Town of Lunenburg',
                      'The Town’s free cash fact sheet in the FY27 warrant materials: each '
                      'certification since 2015, its date, and its share of the prior budget.'))
    out.append(source(man, 'budget-workbooks/finance-committee/fy26-budget/general-fund-budget-vs-actuals-history.xlsx',
                      'gl_history', 'Lunenburg Finance Committee (assembled from MUNIS exports)',
                      'Revised budget and actual for every general fund account, FY2010-FY2025. '
                      'A workbook a person assembled: stated, not proof (rule 13a).'))
    out.append(source(man, RELEASE_KEY, 'town_budget', 'Town of Lunenburg',
                      'The FY27 budget release, which cites the guide: "%s".' % GUIDE))
    for q in QUOTES:
        stem = 'meetings/%s/%s.' % (q['file'].split('/')[0], os.path.basename(q['file'])[:-4])
        keys = sorted(k for k in man if k.startswith(stem))
        if not keys:
            fail('no archived document for the minutes %s (rule 12)' % q['file'])
        out.append(source(man, keys[0], 'minutes', 'Lunenburg %s' % q['body'],
                          'Minutes of %s: "%s"' % (q['date'], q['text'])))
    seen, uniq = set(), []
    for s in out:
        if s['path'] not in seen:
            seen.add(s['path'])
            uniq.append(s)
    return uniq


# ======================================================================================
# CHARTS FOR /docs AND THE PDF (the web page draws components; rule 7f)
# ======================================================================================

FONT = 'system-ui, -apple-system, &quot;Segoe UI&quot;, sans-serif'
INK, MUTED, GRID = '#1f2328', '#5b6470', '#d8dbe0'
POT_COLOR = {'free_cash': '#2b6cb0', 'stabilization': '#0d9488', 'town_other': '#ea8c00',
             'enterprise': '#7c3aed', 'relief': '#92400e', 'school': '#dc2626'}
CAT_COLOR = {'cb': '#dc2626', 'choice': '#2b6cb0', 'lunch': '#ea8c00', 'fees': '#2f8f4e',
             'gifts': '#7c3aed'}


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def svg_wrap(w, h, title, body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
            'font-family="%s" role="img" aria-label="%s">\n<rect width="%d" height="%d" fill="#ffffff"/>\n%s\n</svg>\n'
            % (w, h, w, h, FONT, esc(title), w, h, '\n'.join(body)))


def balances_svg(pots, years):
    W, cols, cw, ch = 900, 3, 280, 150
    rows = (len(pots) + cols - 1) // cols
    H = 40 + rows * (ch + 46)
    top = max(max(p['value'] for p in pot['points']) for pot in pots)
    b = ['<text x="16" y="24" font-size="14" font-weight="700" fill="%s">Held at each 30 June, '
         'one panel per pot, one dollar scale</text>' % INK]
    for i, pot in enumerate(pots):
        cx = 16 + (i % cols) * (cw + 14)
        cy = 44 + (i // cols) * (ch + 46)
        b.append('<text x="%d" y="%d" font-size="12" font-weight="700" fill="%s">%s</text>'
                 % (cx, cy + 12, INK, esc(pot['label'])))
        base = cy + 26 + ch - 24
        span = ch - 34
        bw = (cw - 10) / len(years)
        b.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s"/>'
                 % (cx, base, cx + cw, base, GRID))
        pts = {p['fy']: p['value'] for p in pot['points']}
        for j, y in enumerate(years):
            if y not in pts:
                continue
            v = pts[y]
            hpx = abs(v) / top * span
            yy = base - hpx if v >= 0 else base
            b.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                     % (cx + j * bw + 1, yy, bw - 2, max(hpx, 0.8), POT_COLOR[pot['key']]))
        first, last = pot['points'][0], pot['points'][-1]
        b.append('<text x="%d" y="%.1f" font-size="10" fill="%s">FY%d %s → FY%d %s</text>'
                 % (cx, base + 14, MUTED, first['fy'], usdk(first['value']),
                    last['fy'], usdk(last['value'])))
    b.append('<text x="16" y="%d" font-size="10" fill="%s">Years run FY%d–FY%d left to right in '
             'every panel; a gap is a year no document read here prints.</text>'
             % (H - 8, MUTED, years[0], years[-1]))
    return svg_wrap(W, H, 'Year-end balances by pot', b)


def school_svg(series):
    W, H, L, B, T = 900, 330, 70, 270, 40
    pos = max(sum(max(r[k], 0) for k, _ in SCHOOL_CATS) for r in series)
    neg = min(sum(min(r[k], 0) for k, _ in SCHOOL_CATS) for r in series)
    scale = (B - T) / (pos - neg)
    zero = B + neg * scale
    bw = (W - L - 20) / len(series)
    b = [('<text x="16" y="24" font-size="14" font-weight="700" fill="%s">The same %s school '
          'funds at each 30 June, by kind</text>' % (INK, N_WORD)),
         '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s"/>' % (L, zero, W - 20, zero, GRID)]
    for i, r in enumerate(series):
        x = L + i * bw + 3
        up, down = zero, zero
        for k, _ in SCHOOL_CATS:
            v = r[k]
            h = abs(v) * scale
            if v >= 0:
                up -= h
                y = up
            else:
                y = down
                down += h
            b.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                     % (x, y, bw - 6, h, CAT_COLOR[k]))
        tot = sum(r[k] for k, _ in SCHOOL_CATS)
        b.append('<text x="%.1f" y="%.1f" font-size="9" text-anchor="middle" fill="%s">%s</text>'
                 % (x + (bw - 6) / 2, up - 4, INK, usdk(tot)))
        b.append('<text x="%.1f" y="%d" font-size="9.5" text-anchor="middle" fill="%s">FY%02d</text>'
                 % (x + (bw - 6) / 2, B + 30, MUTED, r['fy'] % 100))
    lx = L
    for k, _ in SCHOOL_CATS:
        b.append('<rect x="%d" y="%d" width="10" height="10" fill="%s"/>' % (lx, H - 18, CAT_COLOR[k]))
        b.append('<text x="%d" y="%d" font-size="10.5" fill="%s">%s</text>' % (lx + 14, H - 9, INK, SHORT[k]))
        lx += 150
    return svg_wrap(W, H, 'School funds by kind', b)


def turnback_svg(rows):
    W, H, L, B, T = 760, 300, 70, 240, 40
    top = max(max(r.get('school') or 0, r.get('town_wide') or 0) for r in rows)
    scale = (B - T) / top
    gw = (W - L - 20) / len(rows)
    b = ['<text x="16" y="24" font-size="14" font-weight="700" fill="%s">Unspent appropriations '
         'at each close</text>' % INK,
         '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (L, B, W - 20, B, GRID)]
    for i, r in enumerate(rows):
        x0 = L + i * gw + 8
        for j, (k, c) in enumerate((('town_wide', '#2b6cb0'), ('school', '#dc2626'))):
            v = r.get(k)
            if v is None:
                continue
            h = v * scale
            x = x0 + j * (gw - 16) / 2
            b.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                     % (x, B - h, (gw - 16) / 2 - 3, h, c))
            b.append('<text x="%.1f" y="%.1f" font-size="9" text-anchor="middle" fill="%s">%s</text>'
                     % (x + ((gw - 16) / 2 - 3) / 2, B - h - 4, INK, usdk(v)))
        b.append('<text x="%.1f" y="%d" font-size="10" text-anchor="middle" fill="%s">FY%d</text>'
                 % (x0 + (gw - 16) / 2, B + 16, MUTED, r['fy']))
    b.append('<rect x="%d" y="%d" width="10" height="10" fill="#2b6cb0"/><text x="%d" y="%d" '
             'font-size="10.5" fill="%s">Whole town (state free cash proof)</text>' % (L, H - 22, L + 14, H - 13, INK))
    b.append('<rect x="%d" y="%d" width="10" height="10" fill="#dc2626"/><text x="%d" y="%d" '
             'font-size="10.5" fill="%s">School department 300 (MUNIS, period 13)</text>' % (L + 260, H - 22, L + 274, H - 13, INK))
    return svg_wrap(W, H, 'Unspent appropriations at the close', b)


# ======================================================================================
# THE REPORT
# ======================================================================================

def build():
    check_quotes()
    check_gaps()
    years, by, fund_year, printed = srf()
    bal, rev, exp, opening, q3bal = chain(fund_year)
    gf = school_gf()
    sheet, proof = free_cash()
    stab = stabilization()
    us_rows, us_tot = unspent_share()
    man = manifest()

    # ---- the school series, same fourteen funds every year -------------------------
    school_series = []
    for y in years:
        row = dict(fy=y, basis='annual report')
        for k, _ in SCHOOL_CATS:
            row[k] = round(by[(y, k)], 2)
        school_series.append(row)
    for y in (2024, 2025, 2026):
        row = dict(fy=y, basis='carried from FY2023 through MUNIS' +
                   (', proved against March 2026' if y <= 2025 else ''))
        for k, _ in SCHOOL_CATS:
            row[k] = round(sum(bal[(f, y)] for f, (c, _n) in SCHOOL_FUNDS.items() if c == k), 2)
        school_series.append(row)
    # A check the categorised FY2023 total agrees with the per-fund chain start.
    s23 = sum(bal[(f, 2023)] for f in SCHOOL_FUNDS)
    if abs(s23 - sum(school_series[years.index(2023)][k] for k, _ in SCHOOL_CATS)) > 0.005:
        fail('FY2023 %s-fund total disagrees between the two routes')
    for r in school_series:
        r['total'] = round(sum(r[k] for k, _ in SCHOOL_CATS), 2)
    stot = {r['fy']: r['total'] for r in school_series}
    peak = max(school_series, key=lambda r: r['total'])
    s_first, s_last = school_series[0], school_series[-1]

    cb = {r['fy']: r['cb'] for r in school_series}
    cb_peak_fy = max(cb, key=lambda y: cb[y])
    cb_fell = [y for y in sorted(cb) if y - 1 in cb and cb[y] < cb[y - 1] and y >= cb_peak_fy + 1]
    lunch26 = bal[('2200', 2026)]

    # ---- turnback ------------------------------------------------------------------
    unspent_proof = {y: d['Add Unencumbered/Unexpended Appropriations (CL#11)'] for y, d in proof.items()}
    tb_years = sorted(set(unspent_proof) | set(gf))
    turnback = [dict(fy=y, school=gf[y]['available_budget'] if y in gf else None,
                     town_wide=unspent_proof.get(y)) for y in tb_years]
    share = {y: round(100 * gf[y]['available_budget'] / unspent_proof[y], 1)
             for y in gf if y in unspent_proof}

    # ---- free cash -----------------------------------------------------------------
    fc_years = sorted(sheet)
    fc_first, fc_last = fc_years[0], fc_years[-1]
    fc_fell = sum(1 for a, c in zip(fc_years, fc_years[1:]) if sheet[c]['amount'] < sheet[a]['amount'])
    receipts = {y: proof[y]['Excess/Shortfall Local Receipts (CL#6)'] for y in proof}
    rc_years = [y for y in sorted(receipts) if receipts[y] >= 1e6]
    rc_min = min(receipts[y] for y in rc_years)
    if rc_years != list(range(rc_years[0], rc_years[-1] + 1)) or rc_years[-1] != max(receipts):
        fail('the years with receipts above a million are not one unbroken run to the latest')
    unused = {y: proof[y]['Add Prior Year Free Cash Not Appropriated (CL#12)'] for y in proof}

    # ---- town special revenue ------------------------------------------------------
    town_series = []
    for y in years:
        town_series.append(dict(fy=y, enterprise=round(by[(y, 'enterprise')], 2),
                                relief=round(by[(y, 'relief')], 2),
                                town_other=round(by[(y, 'town_other')], 2),
                                school_all=round(by[(y, 'school_all')], 2),
                                printed_total=printed[y]))
    t23 = town_series[-1]
    town23 = t23['enterprise'] + t23['relief'] + t23['town_other']
    arpa_ent = t23['enterprise'] + t23['relief']
    arpa_ent_pct = 100 * arpa_ent / town23
    t11 = town_series[0]

    stab_years = sorted(stab)
    st_first, st_last = stab_years[0], stab_years[-1]

    # ---- the pots, for the signature chart -----------------------------------------
    pots = [
        dict(key='school', label='The schools’ own %s funds' % N_WORD,
             who='School Committee, without a Town Meeting vote',
             points=[dict(fy=r['fy'], value=r['total']) for r in school_series]),
        dict(key='free_cash', label='Free cash (certified)',
             who='Town Meeting, for any lawful purpose',
             points=[dict(fy=y, value=sheet[y]['amount']) for y in fc_years]),
        dict(key='stabilization', label='General stabilization fund',
             who='Town Meeting, by a two-thirds vote',
             points=[dict(fy=y, value=stab[y]['amount']) for y in stab_years]),
        dict(key='town_other', label='Town special revenue, other',
             who='Each fund under its own statute or vote',
             points=[dict(fy=r['fy'], value=r['town_other']) for r in town_series]),
        dict(key='enterprise', label='Water, sewer, trash and cable enterprises',
             who='Town Meeting, for that utility only',
             points=[dict(fy=r['fy'], value=r['enterprise']) for r in town_series]),
        dict(key='relief', label='Federal pandemic relief (ARPA, CARES)',
             who='Under federal rules, with federal deadlines',
             points=[dict(fy=r['fy'], value=r['relief']) for r in town_series if r['relief']]),
    ]
    all_years = list(range(min(years), 2027))

    # =================================================================================
    # CONCLUSIONS
    # =================================================================================
    F = figure
    yr = lambda y: 'FY%d' % y
    rows = []

    rows.append(conclusion(
        id='the-schools-funds-peaked-and-have-fallen',
        claim='The schools’ fee, choice, lunch and circuit-breaker funds held %s at 30 June 2026.'
              % usd(s_last['total']),
        so_what='They rose to %s in %s and have fallen since: not growing now.'
                % (usd(peak['total']), yr(peak['fy'])),
        figure='last',
        figures=dict(last=F(s_last['total'], usd(s_last['total']),
                            'held by the same %s school funds, 30 June 2026' % N_WORD),
                     peak=F(peak['total'], usd(peak['total'])),
                     first=F(s_first['total'], usd(s_first['total']))),
        detail='The same %s funds every year, from %s at 30 June %d. Through %s each '
               'balance is the annual report’s own; after it, the 30 June 2023 balance is '
               'carried through the period-13 ledgers, and the 30 June 2025 result matches the '
               'Town’s March 2026 report to the cent for every fund. The grant funds are '
               'not in this total.' % (N_WORD, usd(s_first['total']), s_first['fy'], yr(2023)),
        kind='measured', bearing='sizes',
        basis='`special-revenue-read.csv` (FY2011-FY2023, ties to every printed total); '
              '`munis-school-ytd.csv` period 13 (FY2024-FY2026); proved against '
              '`school-special-revenue-fy26-q3.csv`.',
        not_shown='What the balances were spent on, or whether a lower balance means a '
                  'programme cost more, took in less, or was deliberately drawn down.',
        allow=('30 June 2026', '30 June 2023', '30 June 2025', '30 June %d' % s_first['fy'],
               yr(peak['fy']), yr(2023), 'March 2026', '13'),
        see=[('/money-outside-the-budget', 'The money outside the budget')]))

    rows.append(conclusion(
        id='free-cash-has-grown-most',
        claim='Certified free cash rose from %s at the %s close to %s at the %s close.'
              % (usd(sheet[fc_first]['amount']), yr(fc_first), usd(sheet[fc_last]['amount']),
                 yr(fc_last)),
        so_what='%s of the prior year’s budget by the Town’s own count, against %s then. '
                'Spent only by Town Meeting.' % (sheet[fc_last]['pct'], sheet[fc_first]['pct']),
        figure='last',
        figures=dict(last=F(sheet[fc_last]['amount'], usd(sheet[fc_last]['amount']),
                            'certified free cash, as of 1 July 2025'),
                     first=F(sheet[fc_first]['amount'], usd(sheet[fc_first]['amount'])),
                     pct=F(float(sheet[fc_last]['pct'].rstrip('%')), sheet[fc_last]['pct']),
                     firstpct=F(float(sheet[fc_first]['pct'].rstrip('%')), sheet[fc_first]['pct']),
                     fell=F(fc_fell, '%d' % fc_fell, 'years'),
                     steps=F(len(fc_years) - 1, '%d' % (len(fc_years) - 1), 'years'),
                     rose=F(len(fc_years) - 1 - fc_fell, '%d' % (len(fc_years) - 1 - fc_fell), 'years')),
        detail='Not a steady climb: it fell in %d of %d years and rose in %d. The state’s '
               'own proof agrees with every figure it covers. Free cash is not held by any '
               'department: Town Meeting appropriates it. The Town’s FY27 budget release '
               'cites a state guide of %s.'
               % (fc_fell, len(fc_years) - 1, len(fc_years) - 1 - fc_fell, GUIDE),
        kind='measured', bearing='lever',
        basis='`free-cash-history-fincom.csv` (the Town’s fact sheet) checked against '
              '`free-cash-proof.csv` (the Division of Local Services).',
        not_shown='Whether the balance is too high or too low: the guide is a range, and '
                  'how much of each year’s free cash was then appropriated is in '
                  '/analysis/free-cash, not here.',
        allow=(yr(fc_first), yr(fc_last), '1 July 2025', 'FY27', GUIDE),
        see=[('/analysis/free-cash', 'Free cash: hoarding, or rebuilding?')]))

    g26, g25, g24, g23 = gf[2026], gf[2025], gf[2024], gf[2023]
    rows.append(conclusion(
        id='the-school-turnback-goes-to-the-town',
        claim='The school general fund closed FY2026 with %s unspent; FY2025 with %s.'
              % (usd(g26['available_budget']), usd(g25['available_budget'])),
        so_what='Not kept by the schools: the state’s free cash calculation adds unspent '
                'appropriations back for the town.',
        figure='y26',
        figures=dict(y26=F(g26['available_budget'], usd(g26['available_budget']),
                           'unspent in the school general fund at the FY2026 close'),
                     y25=F(g25['available_budget'], usd(g25['available_budget'])),
                     y24=F(g24['available_budget'], usd(g24['available_budget'])),
                     y23=F(g23['available_budget'], usd(g23['available_budget'])),
                     enc=F(g26['encumbrances'], usd(g26['encumbrances']))),
        detail='%s in FY2023 and %s in FY2024, so the last two years are larger. A further %s '
               'was still committed to open purchase orders at the FY2026 close. The state’s '
               'free cash proof adds unspent, uncommitted appropriations back as one of its '
               'lines, which is how this money reaches free cash.'
               % (usd(g23['available_budget']), usd(g24['available_budget']),
                  usd(g26['encumbrances'])),
        kind='measured', bearing='sizes',
        basis='`munis-school-ytd.csv`, report gf-school, period 13, `available_budget` summed; '
              'the free cash proof’s line CL#11.',
        not_shown='Why more was left in FY2025 and FY2026; which accounts it sat in is in the '
                  'FY25 and FY26 school surplus reports.',
        allow=('FY2026', 'FY2025', 'FY2024', 'FY2023', 'CL#11'),
    ))

    rows.append(conclusion(
        id='the-schools-share-of-what-went-unspent',
        claim='The schools were %s of the %s the town left unspent at the FY2025 close.'
              % (usd(g25['available_budget']), usd(unspent_proof[2025])),
        so_what='%s%% — the rest of the general fund left the larger part, and no published '
                'document says which departments.' % share[2025],
        figure='share',
        figures=dict(share=F(share[2025], '%s%%' % share[2025],
                             'of the town’s unspent appropriations at the FY2025 close was the schools’'),
                     school=F(g25['available_budget'], usd(g25['available_budget'])),
                     town=F(unspent_proof[2025], usd(unspent_proof[2025])),
                     s24=F(share[2024], '%s%%' % share[2024]),
                     s23=F(share[2023], '%s%%' % share[2023])),
        detail='%s%% at the FY2024 close and %s%% at the FY2023 close. Two documents, set side '
               'by side: the state’s proof prints one town-wide line, and the school figure is '
               'department 300’s own ledger. The remainder is everything else the town '
               'appropriated, which nothing published splits by department.'
               % (share[2024], share[2023]),
        kind='measured', bearing='sizes',
        basis='`free-cash-proof.csv` line CL#11 against `munis-school-ytd.csv` gf-school '
              'period 13 `available_budget`.',
        not_shown='Which town departments or articles make up the remainder: registered as a '
                  'gap, closed by a departmental turnback schedule.',
        allow=('FY2025', 'FY2024', 'FY2023', '300'),
        see=[('/what-we-cannot-answer', 'What we cannot answer')]))

    rows.append(conclusion(
        id='receipts-above-estimate-feed-free-cash',
        claim='Receipts above the town’s estimate added over %s a year to free cash, %s–%s.'
              % (usd(1e6), yr(rc_years[0]), yr(rc_years[-1])),
        so_what='Where the town sets its revenue estimate is a decision, and it decides part '
                'of how big free cash gets.',
        figure='min',
        figures=dict(min=F(rc_min, usd(rc_min),
                           'the smallest of those years’ receipts above estimate'),
                     million=F(1e6, usd(1e6)),
                     max=F(max(receipts[y] for y in rc_years),
                           usd(max(receipts[y] for y in rc_years)))),
        detail='The state’s proof shows between %s and %s a year. On 28 May 2026 a Finance '
               'Committee member said the town had not collected less than four million in '
               'local receipts in ten years, against an estimate of 3.535 million. Why the '
               'estimate is set where it is is a hypothesis here; nothing tests it.'
               % (usd(rc_min), usd(max(receipts[y] for y in rc_years))),
        kind='measured', bearing='lever',
        basis='`free-cash-proof.csv`, line CL#6, Lunenburg; Finance Committee minutes of '
              '28 May 2026.',
        not_shown='Whether the margin is deliberate caution, receipts that grew faster than '
                  'anyone could forecast, or one-time money; each fits the same line.',
        allow=tuple(yr(y) for y in rc_years) + ('28 May 2026', '3.535', 'CL#6'),
    ))

    rows.append(conclusion(
        id='most-town-special-revenue-is-not-free-to-spend',
        claim='Of %s in town special revenue funds at 30 June 2023, %s%% was ARPA or utility money.'
              % (usd(town23), '%.0f' % arpa_ent_pct),
        so_what='Federal relief with federal deadlines, and water, sewer, trash and cable money '
                'kept for ratepayers.',
        figure='pct',
        figures=dict(pct=F(round(arpa_ent_pct, 1), '%.0f%%' % arpa_ent_pct,
                           'of town special revenue at 30 June 2023 was federal relief or enterprise'),
                     total=F(town23, usd(town23)),
                     other=F(t23['town_other'], usd(t23['town_other'])),
                     other11=F(t11['town_other'], usd(t11['town_other'])),
                     relief=F(t23['relief'], usd(t23['relief'])),
                     ent=F(t23['enterprise'], usd(t23['enterprise']))),
        detail='Federal relief %s and enterprises %s. Everything else the town held in special '
               'revenue came to %s, against %s at 30 June 2011. Later years are printed in a '
               'different table this project has not yet read.'
               % (usd(t23['relief']), usd(t23['enterprise']), usd(t23['town_other']),
                  usd(t11['town_other'])),
        kind='measured', bearing='sizes',
        basis='`special-revenue-read.csv`, FY2011-FY2023, non-school funds, split by name.',
        not_shown='What the town funds held at 30 June 2024, 2025 or 2026: registered as a gap.',
        allow=('30 June 2023', '30 June 2011', '30 June 2024, 2025 or 2026'),
    ))

    rows.append(conclusion(
        id='the-general-stabilization-fund-is-growing',
        claim='The general stabilization fund grew from %s in %s to %s in %s.'
              % (usd(stab[st_first]['amount']), yr(st_first), usd(stab[st_last]['amount']),
                 yr(st_last)),
        so_what='A reserve by design: spending it takes a two-thirds vote of Town Meeting.',
        figure='last',
        figures=dict(last=F(stab[st_last]['amount'], usd(stab[st_last]['amount']),
                            'in the general stabilization fund, 30 June %d' % st_last),
                     first=F(stab[st_first]['amount'], usd(stab[st_first]['amount']))),
        detail='Year-end cash, each year closed on the identities its own table prints. The '
               'special-purpose stabilization funds are counted separately in '
               '/analysis/stabilization-funds.',
        kind='measured', bearing='sizes',
        basis='`stabilization-balances.csv`, name STABILIZATION, `ending_cash`.',
        not_shown='How much of the growth is deposits voted by Town Meeting and how much is '
                  'interest.',
        allow=(yr(st_first), yr(st_last)),
        see=[('/analysis/stabilization-funds', 'Stabilization funds')]))

    rows.append(conclusion(
        id='the-circuit-breaker-is-being-drawn-down',
        claim='The circuit breaker fund closed FY2026 at %s, down from %s at its %s high.'
              % (usd(cb[2026]), usd(cb[cb_peak_fy]), yr(cb_peak_fy)),
        so_what='It fell in %d of the %d years since: received and spent, not piling up.'
                % (len(cb_fell), 2026 - cb_peak_fy),
        figure='last',
        figures=dict(last=F(cb[2026], usd(cb[2026]),
                            'in the circuit breaker fund, 30 June 2026'),
                     peak=F(cb[cb_peak_fy], usd(cb[cb_peak_fy])),
                     fell=F(len(cb_fell), '%d' % len(cb_fell), 'years'),
                     span=F(2026 - cb_peak_fy, '%d' % (2026 - cb_peak_fy), 'years')),
        detail='The state reimburses part of high-cost special education after the year; the '
               'district may carry it forward. In March 2024 the district told the Finance '
               'Committee a tuition rise was probably absorbed by circuit breaker carry-over, '
               'which is why the account had gone down.',
        kind='measured', bearing='sizes',
        basis='`special-revenue-read.csv` (“50/50 Grant Sped Tuitions”), then fund 2640 '
              'in `munis-school-ytd.csv`; identified by FY2023 receipts equal to the cent.',
        not_shown='Which children’s costs the carry-over paid for in any year.',
        allow=('FY2026', yr(cb_peak_fy), 'March 2024', '2640', 'FY2023', '50/50'),
        see=[('/what-special-education-costs', 'What special education costs')]))

    conc = emit(ID, rows)

    # =================================================================================
    # THE MARKDOWN
    # =================================================================================
    b = []
    w = b.append
    w('# Is anyone sitting on money? Town and schools\n')
    w('**Every pot of money the town and the schools hold outside the voted budget, as a '
      'balance at each 30 June, for as many years as a document prints it.**\n')
    w('---\n')
    w('## The short version\n')
    w('![Six small panels, one per pot of money, each a bar per year-end on one dollar scale: '
      'the schools’ ⟨N⟩ funds rise to %s in %s and fall to %s by FY2026; free cash rises '
      'from %s to %s; the general stabilization fund rises; the enterprise funds '
      'rise; federal relief appears from FY2020.](charts/%s-balances.svg)\n'
      % (usd(peak['total']), yr(peak['fy']), usd(s_last['total']), usd(sheet[fc_first]['amount']),
         usd(sheet[fc_last]['amount']), ID))
    w('**The schools’ own funds grew to a peak in %s and have fallen since.** The ⟨N⟩ school '
      'funds that take in fees, tuition, lunch money, gifts and the state’s special education '
      'reimbursement went from %s at 30 June %d to %s at 30 June %d, and were at %s by 30 June '
      '2026.\n'
      % (yr(peak['fy']), usd(s_first['total']), s_first['fy'], usd(peak['total']), peak['fy'],
         usd(s_last['total'])))
    w('**What the schools leave unspent in their budget goes back to the town.** %s at the '
      'FY2026 close, %s at the FY2025 close — and the state’s free cash calculation counts it '
      'in. At the FY2025 close the schools were %s%% of the town’s unspent appropriations.\n'
      % (usd(g26['available_budget']), usd(g25['available_budget']), share[2025]))
    w('**What has grown is held by the town.** Certified free cash went from %s (%s close) to %s '
      '(%s close); the general stabilization fund from %s to %s. Both are spent only by Town '
      'Meeting vote.\n'
      % (usd(sheet[fc_first]['amount']), yr(fc_first), usd(sheet[fc_last]['amount']), yr(fc_last),
         usd(stab[st_first]['amount']), usd(stab[st_last]['amount'])))
    w('---\n')

    # ---- schools -------------------------------------------------------------------
    w('## The schools’ own funds, every year end\n')
    w('![Stacked bars, FY2011 to FY2026, of the same ⟨N⟩ school funds by kind: circuit '
      'breaker, school choice, lunch, fee-funded revolving funds and gifts.](charts/%s-school.svg)\n' % ID)
    w('The same ⟨N⟩ funds every year. **FY2011–FY2023** are the annual report’s own '
      'balances. **FY2024–FY2026** carry each fund’s 30 June 2023 balance forward through the '
      'period-13 ledgers (revenue less expense); the 30 June 2025 result equals, to the cent, the '
      'opening balance the Town’s March 2026 special revenue report implies for **every one of the '
      '⟨N⟩**. FY2026 has no independent check yet.\n')
    w('| 30 June | circuit breaker | school choice | lunch | fee-funded | gifts | total | basis |')
    w('|---|---:|---:|---:|---:|---:|---:|---|')
    for r in school_series:
        w('| %s | %s | %s | %s | %s | %s | **%s** | %s |'
          % (yr(r['fy']), usd(r['cb']), usd(r['choice']), usd(r['lunch']), usd(r['fees']),
             usd(r['gifts']), usd(r['total']), r['basis']))
    w('')
    w('**Not in these totals: the grant funds and a handful of small accounts** — %s at 30 June '
      '2023, net, because reimbursement grants spend before they are paid and so sit below zero '
      'at a year end. Their later balances cannot be carried: the annual report names a grant by '
      'year, MUNIS numbers it, and nothing published maps one to the other. Registered as a gap.\n'
      % usd(by[(2023, 'school_other')]))
    w('**Lunch fell to %s at 30 June 2026** after spending %s against %s taken in during FY2026. '
      'The ledger shows the amounts; why — a costlier year, reimbursements that arrive after the '
      'close, or both — is a hypothesis nothing here tests.\n'
      % (usd(lunch26), usd(exp[('2200', 2026)]), usd(rev[('2200', 2026)])))
    w('### The circuit breaker\n')
    w('Printed in the annual report as “50/50 Grant Sped Tuitions”. That it is the circuit breaker '
      'is shown, not assumed: its FY2023 receipts, %s, equal MUNIS fund 2640 SPECIAL ED CIRCUIT '
      'BREAKER’s to the cent. It peaked at %s at 30 June %d and has fallen in %d of the %d years '
      'since, to %s.\n'
      % (usd(rev[('2640', 2023)]), usd(cb[cb_peak_fy]), cb_peak_fy, len(cb_fell),
         2026 - cb_peak_fy, usd(cb[2026])))
    w('| 30 June | balance | in that year | out that year |')
    w('|---|---:|---:|---:|')
    for y in (2023, 2024, 2025, 2026):
        w('| %s | %s | %s | %s |' % (yr(y), usd(cb[y]), usd(rev[('2640', y)]), usd(exp[('2640', y)])))
    w('')

    w('### The school budget’s turnback at the close\n')
    w('![Grouped bars: the town’s unspent appropriations from the state’s free cash proof, '
      'FY2021 to FY2025, beside the school department’s unspent general fund at period 13, '
      'FY2023 to FY2026.](charts/%s-turnback.svg)\n' % ID)
    w('| fiscal year | school budget, revised | spent | still committed | **unspent at the close** | town-wide unspent (state proof) | schools’ share |')
    w('|---|---:|---:|---:|---:|---:|---:|')
    for y in tb_years:
        g = gf.get(y)
        tw = unspent_proof.get(y)
        w('| %s | %s | %s | %s | %s | %s | %s |'
          % (yr(y), usd(g['revised_budget']) if g else '—', usd(g['ytd_expended']) if g else '—',
             usd(g['encumbrances']) if g else '—', ('**%s**' % usd(g['available_budget'])) if g else '—',
             usd(tw) if tw is not None else '—', ('%s%%' % share[y]) if y in share else '—'))
    w('')
    w('The school figures are department 300 only, from reports all run on 6 October 2026, so '
      'FY2023–FY2025 show the closed years as the system holds them now. The state’s figure is '
      'its free cash proof’s line CL#11, *unencumbered/unexpended appropriations*, for the whole '
      'town. FY2026 has no state figure yet.\n')

    # ---- town ----------------------------------------------------------------------
    w('## Free cash\n')
    w('| close of | certified | certified on | of the prior budget |')
    w('|---|---:|---|---:|')
    for y in fc_years:
        w('| %s | %s | %s | %s |' % (yr(y), usd(sheet[y]['amount']), sheet[y]['certified'], sheet[y]['pct']))
    w('')
    w('What the state’s proof says each certification was built from, for the five years it '
      'covers. These are four of its lines, not all of them, so they do not sum to the total.\n')
    w('| close of | ' + ' | '.join(lbl for _k, _l, lbl in PROOF_LINES) + ' | certified |')
    w('|---|' + '---:|' * (len(PROOF_LINES) + 1))
    for y in sorted(proof):
        w('| %s | %s | %s |' % (yr(y), ' | '.join(usd(proof[y][l]) for _k, l, _lbl in PROOF_LINES),
                                usd(proof[y]['Current Year Calculation'])))
    w('')
    w('*Last year’s free cash nobody appropriated* is the nearest thing in the record to money '
      'left unused: between %s and %s a year.\n'
      % (usd(min(unused.values())), usd(max(unused.values()))))

    w('## The town’s special revenue funds\n')
    w('From the same annual report schedule as the school funds, FY2011–FY2023. Split three '
      'ways because they are three kinds of money. The split is ours, by fund name.\n')
    w('| 30 June | water, sewer, trash, cable | federal relief | everything else | all school funds | printed total |')
    w('|---|---:|---:|---:|---:|---:|')
    for r in town_series:
        w('| %s | %s | %s | %s | %s | %s |' % (yr(r['fy']), usd(r['enterprise']), usd(r['relief']),
                                               usd(r['town_other']), usd(r['school_all']),
                                               usd(r['printed_total'])))
    w('')
    w('*Everything else* swings because some of its funds are reimbursement grants — Chapter 90 '
      'road money among them — that spend first and are paid later, so they sit below zero at a '
      'year end. **FY2024 and FY2025 are printed in a different table** (a balance detail with no '
      'receipts or disbursements) that this project has not yet read, and FY2026’s annual report '
      'is not yet published. Registered as a gap.\n')

    w('## The general stabilization fund\n')
    w('| 30 June | ending cash | page |')
    w('|---|---:|---:|')
    for y in stab_years:
        w('| %s | %s | %d |' % (yr(y), usd(stab[y]['amount']), stab[y]['page']))
    w('')

    w('## Unspent of the final budget: the schools against the rest of the general fund\n')
    w('From the Finance Committee’s budget-against-actual workbook — **a workbook somebody '
      'assembled from MUNIS exports, not a printout, so `stated`** (rule 13a). Revised budget less '
      'actual; an amount carried forward on an open purchase order is not separated, so this is '
      'not the same quantity as the turnback above.\n')
    w('| fiscal year | schools unspent | share | rest of the general fund unspent | share |')
    w('|---|---:|---:|---:|---:|')
    for r in us_rows:
        w('| %s | %s | %.1f%% | %s | %.1f%% |' % (yr(r['fy']), usd(r['school_unspent']), r['school_pct'],
                                                usd(r['rest_unspent']), r['rest_pct']))
    w('| **FY%d–FY%d** | **%s** | **%.1f%%** | **%s** | **%.1f%%** |'
      % (us_rows[0]['fy'], us_rows[-1]['fy'], usd(us_tot['school']['unspent']), us_tot['school']['pct'],
         usd(us_tot['rest']['unspent']), us_tot['rest']['pct']))
    w('')
    w('*The rest of the general fund* is every department outside 300 and 301 — town departments, '
      'but also debt, insurance and assessments such as Monty Tech’s. It is not a measure of town '
      'departments alone.\n')

    # ---- side by side --------------------------------------------------------------
    w('## Held at 30 June 2023, side by side\n')
    w('The last year end for which every pot here is read. **Not added together**: they are '
      'different kinds of money, decided by different people, and a sum would count restricted '
      'and unrestricted money as one.\n')
    w('| pot | held | who can spend it (our summary of the statute or rule, not quoted) |')
    w('|---|---:|---|')
    n_school_2023 = sum(1 for r in csv.DictReader(open(SRF, encoding='utf-8'))
                        if r['fy'] == '2023' and r['group'] == 'SCHOOL DEPARTMENT')
    snap = [
        ('Free cash, certified as of 1 July 2023', sheet[2023]['amount'], 'Town Meeting, for any lawful purpose'),
        ('General stabilization fund', stab[2023]['amount'], 'Town Meeting, two-thirds vote'),
        ('All school special revenue funds (%d, grants included)' % n_school_2023, by[(2023, 'school_all')],
         'School Committee, each fund under its own statute, without a Town Meeting vote'),
        ('Water, sewer, trash and cable enterprise funds', t23['enterprise'], 'Town Meeting, for that utility only'),
        ('Federal pandemic relief', t23['relief'], 'Under federal rules and deadlines'),
        ('Other town special revenue funds', t23['town_other'], 'Each fund under its own statute or vote'),
    ]
    for name, v, who in snap:
        w('| %s | %s | %s |' % (name, usd(v), who))
    w('')

    # ---- what was said -------------------------------------------------------------
    w('## What was said\n')
    w('Searched in the minutes for unspent balances, revolving funds, the circuit breaker and '
      'free cash (`scripts/search_minutes.py`). Each quote is checked verbatim against the minutes '
      'it cites every time this report is built.\n')
    for q in QUOTES:
        w('- **%s, %s** — %s: *“%s”* ([minutes](%s))' % (q['body'], q['date'], q['who'], q['text'], q['url']))
    w('')
    w('The first is the question this report answers, and the second is the concrete thing it was '
      'asked for. **The athletics revolving fund (1301) held %s at 30 June 2026** by the carried '
      'figures above. Whether it may lawfully pay for middle school sports, and what else is '
      'already committed against it, the ledger cannot say. The third and fourth describe school '
      'balances falling, which is what the ledgers show; they are the district’s statements and '
      'are quoted as that. The last two are about the receipts line above.\n'
      % usd(bal[('1301', 2026)]))

    # ---- limits --------------------------------------------------------------------
    not_est = [
        'What any balance was spent on, or why a balance rose or fell — the ledgers give amounts, '
        'not reasons.',
        'What the town’s own special revenue funds held after 30 June 2023 (registered gap).',
        'What the school grant funds held after 30 June 2023 (registered gap).',
        'Which town departments make up the unspent appropriations that are not the schools’ '
        '(registered gap).',
        'Why receipts come in above the estimate (registered gap).',
        'The FY2026 school balances against any second document; they are carried, and the carry '
        'is proved only to 30 June 2025.',
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
    w('- Special revenue: `special-revenue-read.csv`; each year’s funds are summed and must equal '
      'the GRAND TOTAL the report prints (`special-revenue-printed-totals.csv`) or nothing is written.')
    w('- The school chain: ⟨N⟩ funds matched by name to MUNIS fund numbers (ours); the match '
      'is tested by the 30 June 2025 balance meeting the March 2026 report’s implied opening for '
      'every fund, to the cent.')
    fw23 = {r['fund']: money(r['forward']) for r in csv.DictReader(open(SRF, encoding='utf-8'))
            if r['fy'] == '2023' and r['group'] == 'SCHOOL DEPARTMENT'}
    net23, _r, _e = munis_special()
    miss = [(f, n, fw23[n] + net23[(f, 2023)] - fund_year[(f, 2023)]) for f, (_c, n) in SCHOOL_FUNDS.items()
            if abs(fw23[n] + net23[(f, 2023)] - fund_year[(f, 2023)]) >= 0.01]
    w('- A second test of the same matching: for FY2023 itself, the annual report’s opening '
      'balance plus the MUNIS year’s revenue less expense equals the report’s closing balance '
      'for %d of the ⟨N⟩ funds. %s' % (len(SCHOOL_FUNDS) - len(miss), ' '.join(
          '%s (%s) misses by %s, revenue MUNIS records in FY2023 and the report does not; the '
          'chain starts from the printed balance, so it does not enter the figures.'
          % (n, f, usd(d)) for f, n, d in miss)))
    w('- Free cash: the Town’s fact sheet labels a certification by the year it is spent in; it is '
      'shown here at the close it measures. Every overlapping year agrees with the state’s proof.')
    w('- Verified by `scripts/verify_sitting_on_money.py`, which recomputes every conclusion '
      'figure by a second route.\n')
    w('## Sources\n')
    srf_docs = sorted({r['document'][len('sources/'):]
                       for r in csv.DictReader(open(SRF, encoding='utf-8'))
                       if r['document'].startswith('sources/')})
    srcs = sources(man, srf_docs)
    w('| document | what it gives here |')
    w('|---|---|')
    for s in srcs:
        w('| [%s](%s) | %s |' % (s['filename'], s['docs_url'], s['note'].replace('|', '/')))
    md = ('\n'.join(b) + '\n').replace('⟨N⟩', N_WORD)

    # =================================================================================
    # THE PAYLOAD
    # =================================================================================
    pay = dict(
        generated_by='scripts/build_sitting_on_money.py',
        about='Every pot of money the town and the schools hold outside the voted budget, as a '
              'balance at each 30 June, and whether it is growing.',
        grain='DOLLARS held at a 30 June, fund by fund, for as many years as a document prints '
              'it — balances, not flows — except the turnback, which is one year’s unspent '
              'appropriation at the close. Series from different documents are set side by '
              'side and never added.',
        stats=[
            dict(value=usd(s_last['total']), tone='var(--series-cost)',
                 label='held by the schools’ ⟨N⟩ fee, choice, lunch, gift and circuit-breaker '
                       'funds at 30 June 2026 — %s at the %s peak' % (usd(peak['total']), yr(peak['fy']))),
            dict(value=usd(sheet[fc_last]['amount']),
                 label='certified free cash at the %s close, held by the town — %s at the %s close'
                       % (yr(fc_last), usd(sheet[fc_first]['amount']), yr(fc_first))),
            dict(value=usd(g26['available_budget']),
                 label='left unspent in the school general fund at the FY2026 close, which goes '
                       'back to the town'),
        ],
        pots=pots,
        years=all_years,
        school_categories=[dict(key=k, label=l, short=SHORT[k]) for k, l in SCHOOL_CATS],
        school_series=school_series,
        school_funds=[dict(fund=f, category=c, name=n,
                           balances={str(y): round(bal[(f, y)], 2) for y in (2023, 2024, 2025, 2026)},
                           march_2026_implied_opening=round(opening[f], 2),
                           march_2026_balance=round(q3bal[f], 2))
                      for f, (c, n) in SCHOOL_FUNDS.items()],
        school_other_2023=round(by[(2023, 'school_other')], 2),
        circuit_breaker=dict(peak_fy=cb_peak_fy, fell_years=cb_fell,
                             flows={str(y): dict(received=round(rev[('2640', y)], 2),
                                                 spent=round(exp[('2640', y)], 2))
                                    for y in (2023, 2024, 2025, 2026)}),
        turnback=turnback,
        school_gf=gf,
        school_share_of_unspent=share,
        free_cash=[dict(fy=y, **sheet[y]) for y in fc_years],
        free_cash_proof={str(y): {k: proof[y][l] for k, l, _ in PROOF_LINES}
                         | dict(certified=proof[y]['Current Year Calculation'])
                         for y in sorted(proof)},
        town_series=town_series,
        stabilization=[dict(fy=y, **stab[y]) for y in stab_years],
        unspent_share=dict(rows=us_rows, totals=us_tot),
        quotes=QUOTES,
        gaps=GAP_WHATS,
        sources=srcs,
        not_established=not_est,
        conclusions=conc,
    )
    pay_text = json.dumps(pay, indent=1, ensure_ascii=False, sort_keys=True).replace('⟨N⟩', N_WORD) + '\n'
    svgs = {
        'balances': balances_svg(pots, all_years),
        'school': school_svg(school_series),
        'turnback': turnback_svg(turnback),
    }
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
