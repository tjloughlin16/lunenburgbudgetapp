#!/usr/bin/env python3
"""Parks and recreation, split into topic pages: ten pages and the parks hub.

    python3 scripts/build_parks_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_parks_topics.py --check   # fail if any output would change

WHY THIS EXISTS. scripts/topics.py has the model: one question per page, under five minutes,
facts first, one to four conclusions resting on them. This shelf absorbs /parks-and-recreation
and /youth-sports.

IT COMPUTES NOTHING NEW THAT IT CAN READ INSTEAD, and it keeps four kinds of document apart:

  fy28/public/data/parks.json        build_parks.py: the FY2026 MUNIS appropriation (dept 650,
                                     period 12) and the fund report (31 March 2026), fund 1500's
                                     annual-report series, the smaller parks funds. EVIDENCE.
  sources/data/special-revenue-read.csv
                                     the annual reports' special-revenue schedules, FY2011-
                                     FY2023, every row tied to its own identity (row_ties=yes).
  sources/data/special-revenue-funds.csv
                                     FY2024 and FY2025: the reports print a BALANCE ONLY.
  fy28/public/data/youth-sports.json build_youth_sports.py: funds 1306, 1545, 1500 off the same
                                     FY26 MUNIS report; the district's receipts workbook
                                     (STATED); the Superintendent's email (STATED).
  sources/data/gl-history.csv        the Finance Committee's budget-against-actual workbook,
                                     FY2010-FY2025, ASSEMBLED from MUNIS exports: STATED (13a),
                                     and labelled so. Where the annual report printed the vote,
                                     the two are compared and the disagreements shown.
  sources/data/parks-myrec-sales-fy2025.csv
                                     the registration system's two FY2025 sales printouts --
                                     what that system recorded, not what reached the books.
  the grounds-maintenance bid        read by build_parks.bid(): a vendor's offer (STATED).

RULE 11. A revolving fund's receipts are not what the parks cost, and the Parks appropriation
is not either: it is the general fund's share, beside fee funds that pay for other parts.

RULE 1. Budget is compared with budget and spending with spending, except on the spending
page, where the left-over figure is the ledger's own column (FY2026) or the workbook's final
budget less its actual (earlier years), and says which.
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
from brief import step  # noqa: E402
import build_parks as BP  # noqa: E402  (read-only: bid(), myrec())

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'sources', 'data')
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT_DIR = os.path.join(PUB, 'topics')
MANIFEST = os.path.join(D, 'archive-manifest.csv')
CID = 'parks'

MINE = [t for t, (_, home, gen) in REG.TOPICS.items()
        if home == CID and gen == 'build_parks_topics.py']


def fail(msg):
    raise SystemExit('build_parks_topics: ' + msg)


def load(name):
    return json.load(open(os.path.join(PUB, name), encoding='utf-8'))


def usd2(x):
    x = float(x)
    return ('-$' if x < 0 else '$') + format(abs(x), ',.2f')


def cell(x):
    return None if x is None else C.usd(x)


# --------------------------------------------------------------------- the data

def gl_parks():
    """Department 650 in the Finance Committee's workbook, summed over its accounts by year."""
    out = defaultdict(lambda: dict(original=0.0, revised=0.0, actual=0.0, partial=False, n=0))
    for r in csv.DictReader(open(os.path.join(D, 'gl-history.csv'), encoding='utf-8')):
        if r['sheet'] == 'general_fund' and r['department_code'] == '650':
            y = out[int(r['fiscal_year'])]
            for k in ('original', 'revised', 'actual'):
                y[k] += float(r[k] or 0)
            y['partial'] = y['partial'] or r['actual_is_partial'] == 'true'
            y['n'] += 1
    if sorted(out) != list(range(2010, 2026)):
        fail('the workbook no longer holds Parks for FY2010-FY2025: %s' % sorted(out))
    for y in out.values():
        for k in ('original', 'revised', 'actual'):
            y[k] = round(y[k], 2)
    return dict(out)


def printed_votes():
    """The Park Department line as the annual report prints the omnibus vote for the NEXT
    year, at three coordinates read and cited: (edition, page, line_no) -> v1."""
    want = {2023: ('FY2022', '148', ''), 2024: ('FY2023', '167', '72B'),
            2025: ('FY2024', '143', '72B')}
    got = {}
    for r in csv.DictReader(open(os.path.join(D, 'report-appropriations.csv'), encoding='utf-8')):
        if r['label'] != 'Park Department' or r['table_family'] != 'omnibus-budget' or not r['v1']:
            continue
        for fy, (ed, page, line) in want.items():
            if (r['edition'], r['page'], r['line_no']) == (ed, page, line):
                got[fy] = float(r['v1'])
    if sorted(got) != sorted(want):
        fail('the printed Park Department votes are not where they were: %s' % sorted(got))
    return got


def read_series(fund):
    """A fund's tied annual-report rows, FY2011-FY2023."""
    rows = [r for r in csv.DictReader(open(os.path.join(D, 'special-revenue-read.csv'),
                                           encoding='utf-8')) if r['fund'] == fund]
    out = {}
    for r in rows:
        if r['row_ties'] != 'yes':
            fail('%s FY%s no longer ties to its own row identity' % (fund, r['fy']))
        n = lambda v: float(v) if v not in ('', None) else None
        out[int(r['fy'])] = dict(forward=n(r['forward']), receipts=n(r['receipts']),
                                 disbursed=n(r['disbursements']), carried=n(r['carried']),
                                 page=int(r['page']), document=r['document'])
    if sorted(out) != list(range(2011, 2024)):
        fail('%s: the tied series is no longer FY2011-FY2023: %s' % (fund, sorted(out)))
    return out


def balances(code):
    """FY2024 and FY2025 as the annual reports print them: a balance, no flows."""
    out = {}
    for r in csv.DictReader(open(os.path.join(D, 'special-revenue-funds.csv'), encoding='utf-8')):
        if not r['fund'].startswith(code + ' '):
            continue
        if r['fy'] == '2024' and r['fund_balance']:
            out[2024] = float(r['fund_balance'])
        if (r['fy'] == '2025' and r['columns_as_printed'].startswith('Fund Balance 6/30/2025')
                and r['v1']):
            out[2025] = float(r['v1'])
    if sorted(out) != [2024, 2025]:
        fail('fund %s: the FY2024/FY2025 balances are not both read: %s' % (code, sorted(out)))
    return out


def sources():
    man = {r['key'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    town, mun = 'Town of Lunenburg', 'Town of Lunenburg — Town Accountant (MUNIS)'
    spec = {
        'gf26': ('town-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.xlsx', mun),
        'sr26': ('town-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx', mun),
        'trust26': ('town-ledgers/fund-balances/trust-agency-fy2026-p09.xlsx', mun),
        'glwb': ('budget-workbooks/finance-committee/fy26-budget/'
                 'general-fund-budget-vs-actuals-history.xlsx', 'Lunenburg Finance Committee'),
        'ar11': ('town-annual-reports/docs/4117-fy-2011-annual-town-report.pdf', town),
        'ar22': ('town-annual-reports/docs/4129-fy-2022-annual-town-report.pdf', town),
        'ar23': ('town-annual-reports/docs/4131-fy-2023-annual-town-report.pdf', town),
        'ar24': ('town-annual-reports/docs/4132-fy-2024-annual-town-report.pdf', town),
        'ar25': ('town-annual-reports/docs/4130-fy-2025-annual-town-report.pdf', town),
        'myprog': ('town-ledgers/account-details/parks-program-financials-fy2025-myrec.pdf',
                   'Parks & Recreation — MyRec, by records request'),
        'mymem': ('town-ledgers/account-details/parks-membership-sales-fy2025-myrec.pdf',
                  'Parks & Recreation — MyRec, by records request'),
        'bid': ('town-ledgers/purchase-orders/po-closed-fy2025-parks-grounds-bid.pdf',
                'a contractor, by records request'),
        'receipts': ('town-ledgers/account-details/field-rental-receipts-fy2024-fy2026-lysa.xlsx',
                     'Lunenburg Public Schools, by records request'),
        'parkspage': ('town-supplementary/docs/board-283-parks-commission.html',
                      '%s — Parks Commission page' % town),
        'email': ('correspondence/2026-09-18-school-field-maintenance-superintendent.txt',
                  'Lunenburg Public Schools — the Superintendent, by email'),
    }
    out = {}
    for k, (key, pub) in spec.items():
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        out[k] = dict(label='%s — %s' % (pub, key.split('/')[-1]), href='/docs/' + key)
    for k, f, what in (
            ('d-gl', 'gl-history.csv', 'the Finance Committee workbook, one row an account'),
            ('d-read', 'special-revenue-read.csv', 'the annual reports’ fund schedules, tied'),
            ('d-funds', 'special-revenue-funds.csv', 'the same schedules, every edition'),
            ('d-approp', 'report-appropriations.csv', 'the omnibus budgets, line by line'),
            ('d-myrec', 'parks-myrec-sales-fy2025.csv', 'both MyRec reports, footed'),
            ('d-receipts', 'field-rental-receipts-lysa.csv', 'the seven receipts'),
            ('d-maint', 'school-field-maintenance.csv', 'the email’s figures, all stated')):
        if not os.path.exists(os.path.join(ROOT, 'fy28', 'public', 'docs', 'data', f)):
            fail('/docs/data/%s is not published' % f)
        out[k] = dict(label='Lunenburg Budget Project — %s (%s)' % (f, what),
                      href='/docs/data/' + f)
    return out


# --------------------------------------------------------------------- the pages

def build():
    P = load('parks.json')
    Y = load('youth-sports.json')
    src = sources()
    U = lambda v: figure(v, C.usd(v))
    U2 = lambda v: figure(v, usd2(v))
    PC = lambda v, dp=0: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    f, con = LD.fact, TP.conclusion
    out = {}

    a26 = P['appropriation']
    fund = P['fund']
    f26 = fund['current']
    gl = gl_parks()
    votes = printed_votes()
    funds = {x['fund']: x for x in Y['funds']}
    # The two payloads read the same fund 1500 row off the same report; they must agree.
    if abs(funds[1500]['available'] - f26['closing']) > 0.005:
        fail('parks.json and youth-sports.json disagree on fund 1500 at 31 March 2026')

    # ================================================================ Parks budget
    if abs(gl[2025]['original'] - votes[2025]) > 0.005:
        fail('the workbook’s FY2025 Parks budget no longer equals the printed vote')
    diff = {fy: round(gl[fy]['original'] - votes[fy], 2) for fy in (2023, 2024)}
    if not all(abs(v) > 1 for v in diff.values()):
        fail('the FY2023/FY2024 workbook figures now agree with the printed vote; '
             'rewrite the disagreement fact')
    v10, v26 = gl[2010]['original'], a26['original']
    grew = 100.0 * (v26 / v10 - 1)
    rate = 100.0 * ((v26 / v10) ** (1.0 / 16) - 1)
    voted = {fy: gl[fy]['original'] for fy in gl}
    voted[2026] = v26
    steps = {fy: voted[fy] - voted[fy - 1] for fy in range(2011, 2027)}
    big = max(steps, key=steps.get)
    if big != 2020:
        fail('the largest one-year step in the Parks vote is no longer FY2020: FY%d' % big)
    budget_rows = []
    for fy in range(2026, 2009, -1):
        budget_rows.append(dict(label=C.fy(fy), cells=[
            C.usd(voted[fy]) if fy < 2026 else None,
            C.usd(votes[fy]) if fy in votes else None,
            C.usd(v26) if fy == 2026 else None]))
    out['parks-budget'] = TP.page(
        'parks-budget',
        'The Parks budget voted for FY2026 was %s, against %s in FY2010.' % (C.usd(v26),
                                                                            C.usd(v10)),
        [f('v26', U(v26), 'voted for Parks, FY2026 (ledger, original budget)', 'published',
           allow=('FY2026',)),
         f('v10', U(v10), 'voted for Parks, FY2010 (Finance Committee workbook)', 'published',
           allow=('FY2010',)),
         f('grew', PC(grew), 'more in FY2026 than in FY2010 (ours)', 'estimate',
           allow=('FY2026', 'FY2010')),
         f('rate', PC(rate, 1), 'a year, compounded, FY2010 to FY2026 (ours)', 'estimate',
           allow=('FY2010', 'FY2026')),
         f('cap', figure(2.5, '2.5%'), 'a year, the levy limit’s growth before new growth',
           'statute'),
         f('v19', U(voted[2019]), 'voted for Parks, FY2019 (workbook)', 'published',
           allow=('FY2019',)),
         f('v20', U(voted[2020]), 'voted for Parks, FY2020 (workbook)', 'published',
           allow=('FY2020',)),
         f('wb23', U(gl[2023]['original']), 'FY2023 budget in the workbook', 'published',
           allow=('FY2023',)),
         f('ar23', U(votes[2023]), 'FY2023 vote as the annual report prints it', 'published',
           allow=('FY2023',)),
         f('wb24', U(gl[2024]['original']), 'FY2024 budget in the workbook', 'published',
           allow=('FY2024',)),
         f('ar24', U(votes[2024]), 'FY2024 vote as the annual report prints it', 'published',
           allow=('FY2024',))],
        [con('The Parks budget grew %s a year from FY2010 to FY2026, against a %s levy limit.'
             % (C.pct(rate, 1), '2.5%'), ['v10', 'v26', 'rate', 'cap'],
             {'r': PC(rate, 1), 'c': figure(2.5, '2.5%')}, allow=('FY2010', 'FY2026'),
             notes=[step('Fee funds also pay for the parks and are not in this line, so a rise '
                         'may partly be cost moving off the fees. Nothing here tests that.',
                         'hypothesis')]),
         con('The largest one-year step was FY2020: %s, up from %s.'
             % (C.usd(voted[2020]), C.usd(voted[2019])), ['v19', 'v20'],
             {'a': U(voted[2020]), 'b': U(voted[2019])}, allow=('FY2020',),
             notes=[step('What the added money was for is not stated beside the vote.', 'gap',
                         allow=('FY2020',),
                         closes='the FY2020 Parks budget request, or the Town Manager’s '
                                'FY2020 budget message')]),
         con('Workbook and printed vote differ: FY2023 %s against %s; FY2024 %s against %s.'
             % (C.usd(gl[2023]['original']), C.usd(votes[2023]),
                                     C.usd(gl[2024]['original']), C.usd(votes[2024])),
             ['wb23', 'ar23', 'wb24', 'ar24'],
             {'a': U(gl[2023]['original']), 'b': U(votes[2023]),
              'c': U(gl[2024]['original']), 'd': U(votes[2024])}, allow=('FY2023', 'FY2024'),
             notes=[step('Nothing here says which is right; the workbook was assembled by '
                         'hand from MUNIS exports.', 'gap', allow=('FY2023', 'FY2024', '650'),
                         closes='the MUNIS original-budget report for department 650, FY2023 '
                                'and FY2024')])],
        table=dict(caption='The Parks budget as voted, by year', views=[dict(
            key='voted', label='Voted', total_col=-1, kinds=['stated', 'ledger', 'ledger'],
            columns=['Finance Committee workbook', 'Annual report vote', 'MUNIS ledger'],
            rows=budget_rows,
            note='The workbook’s original budget for department 650, summed over its 16 '
                 'accounts; the annual report’s omnibus line where it was read and cited; '
                 'FY2026 from the MUNIS period-12 report. Votes, not spending.')]),
        sources=[src['glwb'], src['d-gl'], src['ar22'], src['ar23'], src['ar24'],
                 src['d-approp'], src['gf26']],
        finding_figures={'a': U(v26), 'b': U(v10)}, finding_allow=('FY2026', 'FY2010'))

    # ================================================================ Parks spending
    cut_years = [fy for fy in range(2011, 2019) if gl[fy]['revised'] < gl[fy]['original']]
    if len(cut_years) != 8:
        fail('the Parks budget is no longer lowered in every year FY2011-FY2018')
    full = [fy for fy in range(2010, 2025) if not gl[fy]['partial']]
    left = {fy: round(gl[fy]['revised'] - gl[fy]['actual'], 2) for fy in full}
    left_sum = round(sum(left.values()), 2)
    under = [fy for fy in full if left[fy] > 0.005]
    cut12 = round(gl[2012]['original'] - gl[2012]['revised'], 2)
    if not gl[2025]['partial']:
        fail('the workbook’s FY2025 actual is no longer partial; widen the spending range')
    spend_rows = [dict(label=C.fy(fy), cells=[
        C.usd(gl[fy]['original']), C.usd(gl[fy]['revised']), C.usd(gl[fy]['actual']),
        C.usd(left[fy])]) for fy in sorted(full, reverse=True)]
    out['parks-spending'] = TP.page(
        'parks-spending',
        # PERIOD 12, NOT THE CLOSE: the town is held only to June (FY2026 closeout says the
        # same). So "by June", "paid" and "not yet used" -- never "the year's end".
        'By June, before the close, Parks had paid %s of a %s FY2026 budget; %s was not yet used.'
        % (C.usd(a26['expended']), C.usd(a26['revised']), C.usd(a26['available'])),
        [f('rev26', U(a26['revised']), 'revised Parks budget, FY2026, at period 12', 'published',
           allow=('FY2026', '12')),
         f('exp26', U(a26['expended']), 'paid, FY2026 (ledger, period 12, unaudited)',
           'published', allow=('FY2026', '12')),
         f('enc26', U(a26['encumbered']), 'still owed at period 12, FY2026 (ledger)',
           'published', allow=('FY2026', '12')),
         f('avl26', U(a26['available']), 'not yet used at period 12, FY2026 (ledger’s column)',
           'published', allow=('FY2026', '12')),
         f('cuts', N(len(cut_years), 'years'), 'years, FY2011–FY2018, with the budget '
           'lowered mid-year', 'published', allow=('FY2011', 'FY2018')),
         f('cut12', U(cut12), 'taken off the Parks budget during FY2012 (workbook)',
           'published', allow=('FY2012',)),
         f('under', N(len(under), 'years'), 'years of %s ending under the final budget'
           % C.num(len(full)), 'published', {'n': N(len(full))}),
         f('leftsum', U(left_sum), 'left unspent, FY2010–FY2024 in all (our sum)', 'estimate',
           allow=('FY2010', 'FY2024')),
         f('fund-out', U(f26['spent']), 'spent from the parks fee fund, July–March FY2026',
           'published', allow=('FY2026',))],
        [con('In FY2026 Parks paid %s and owed %s of a %s budget; %s was left.'
             % (C.usd(a26['expended']), C.usd(a26['encumbered']), C.usd(a26['revised']),
                C.usd(a26['available'])), ['rev26', 'exp26', 'enc26', 'avl26'],
             {'a': U(a26['expended']), 'b': U(a26['encumbered']), 'c': U(a26['revised']),
              'd': U(a26['available'])}, allow=('FY2026',),
             notes=[step('Period 12 is before the books close; the closed year may differ.',
                         'gap', allow=('FY2026', '12', '13'), closes='the MUNIS period-13 report for the general fund, '
                                       'FY2026')]),
         con('The budget was lowered during the year in all %s years from FY2011 to FY2018.'
             % C.num(len(cut_years)), ['cuts', 'cut12'], {'n': N(len(cut_years))},
             allow=('FY2011', 'FY2018'),
             notes=[step('Where the money went, and why, is not in the workbook.', 'gap',
                         allow=('650',),
                         closes='the transfer votes behind department 650’s mid-year '
                                'adjustments')]),
         con('In %s of %s years Parks ended under its final budget, %s in all.'
             % (C.num(len(under)), C.num(len(full)), C.usd(left_sum)), ['under', 'leftsum'],
             {'a': N(len(under)), 'b': N(len(full)), 'c': U(left_sum)}),
         con('None of this counts what the parks fee fund spends, %s from July to March FY2026.'
             % C.usd(f26['spent']), ['fund-out'], {'a': U(f26['spent'])},
             allow=('FY2026',))],
        table=dict(caption='The Parks budget against spending, by year', views=[dict(
            key='workbook', label='Finance Committee workbook', total_col=3,
            kinds=['stated'] * 4,
            columns=['Voted', 'Final budget', 'Spent', 'Left'],
            rows=spend_rows,
            note='Department 650, summed over its accounts. Left is the final budget less '
                 'the actual, our subtraction. FY2025’s actual is marked partial in the '
                 'workbook and is left out.')]),
        sources=[src['gf26'], src['glwb'], src['d-gl'], src['sr26']],
        finding_figures={'a': U(a26['expended']), 'b': U(a26['revised']),
                         'c': U(a26['available'])}, finding_allow=('FY2026',))

    # ================================================================ Park revolving fund
    pser = read_series('Park User Fees')
    pbal = balances('1500')
    hist = {h['fy']: h for h in fund['history']}
    for fy, r in pser.items():
        if abs((hist[fy]['closing'] or 0) - (r['carried'] or 0)) > 0.005:
            fail('fund 1500 FY%d: parks.json and the tied series disagree' % fy)
    if abs(pbal[2025] - hist[2025]['closing']) > 0.005:
        fail('fund 1500 FY2025 balance no longer matches parks.json')
    gap25 = round(pbal[2025] - f26['opening'], 2)
    if abs(gap25) < 1:
        fail('the FY2025 close and the FY26 opening now agree; rewrite the fund page')
    peak = max(pser, key=lambda y: pser[y]['receipts'] or 0)
    zero = sorted(fy for fy in pser if pser[fy]['carried'] == 0)
    if zero != [2015, 2016]:
        fail('the fund no longer ended at zero in exactly FY2015 and FY2016: %s' % zero)
    prow = []
    for fy in range(2025, 2010, -1):
        if fy in pser:
            r = pser[fy]
            prow.append(dict(label=C.fy(fy), cells=[cell(r['receipts']), cell(r['disbursed']),
                                                    cell(r['carried'])]))
        else:
            prow.append(dict(label=C.fy(fy), cells=[None, None, C.usd(pbal[fy])]))
    out['park-revolving-fund'] = TP.page(
        'park-revolving-fund',
        'The parks’ fee fund held %s at 31 March 2026; it ended FY2015 and FY2016 at zero.'
        % C.usd(f26['closing']),
        [f('held', U(f26['closing']), 'in the Park Revolving Fund, 31 March 2026', 'published',
           allow=('31', '2026')),
         f('in26', U(f26['revenue']), 'taken in, July–March FY2026', 'published',
           allow=('FY2026',)),
         f('out26', U(f26['spent']), 'spent, July–March FY2026', 'published',
           allow=('FY2026',)),
         f('open26', U(f26['opening']), 'opening balance, FY2026 (ledger)', 'published',
           allow=('FY2026',)),
         f('close25', U(pbal[2025]), 'balance at 30 June 2025, annual report', 'published',
           allow=('30', '2025')),
         f('close11', U(pser[2011]['carried']), 'balance at the end of FY2011', 'published',
           allow=('FY2011',)),
         f('zero', N(len(zero), 'years'), 'years ending at zero, FY2011–FY2023', 'published',
           allow=('FY2011', 'FY2023')),
         f('peak', U(pser[peak]['receipts']), 'taken in during %s, the most FY2011–FY2023'
           % C.fy(peak), 'published', allow=(C.fy(peak), 'FY2011', 'FY2023')),
         f('flows', None, 'receipts and spending, FY2024 and FY2025', 'gap',
           allow=('FY2024', 'FY2025'),
           closes='the FY2024 and FY2025 special-revenue reports for fund 1500')],
        [con('The fund ended %s and %s at zero, and held %s by 30 June 2025.'
             % ('FY2015', 'FY2016', C.usd(pbal[2025])), ['zero', 'close25', 'close11'],
             {'a': U(pbal[2025])}, allow=('FY2015', 'FY2016', '30', '2025')),
         con('From July to March FY2026 it took in %s and spent %s.'
             % (C.usd(f26['revenue']), C.usd(f26['spent'])), ['in26', 'out26', 'held'],
             {'a': U(f26['revenue']), 'b': U(f26['spent'])}, allow=('FY2026',),
             notes=[step('Receipts are what users paid, not what the parks cost to run.',
                         'gap', closes='the department’s costs across the general fund and its '
                                       'own funds, in one statement')]),
         con('The annual report’s 30 June 2025 balance is %s more than the ledger’s FY2026 '
             'opening.' % C.usd(gap25), ['close25', 'open26'], {'a': U(gap25)},
             allow=('30', '2025', 'FY2026'),
             notes=[step('An audit adjustment, an encumbrance or a misprint all fit; nothing '
                         'here tests which.', 'gap', allow=('FY2025', '1500'),
                         closes='the FY2025 special-revenue report and fund 1500’s journal')])],
        table=dict(caption='The Park Revolving Fund by year', views=[dict(
            key='fund', label='Annual town reports', total_col=2, kinds=['ledger'] * 3,
            columns=['Taken in', 'Spent', 'Balance'], rows=prow,
            note='FY2011–FY2023 printed as Park User Fees, each row tying forward + receipts '
                 '− disbursements = carried. FY2024 and FY2025 print a balance only.')]),
        sources=[src['sr26'], src['ar11'], src['ar23'], src['ar24'], src['ar25'],
                 src['d-read'], src['d-funds']],
        finding_figures={'a': U(f26['closing'])},
        finding_allow=('31', '2026', 'FY2015', 'FY2016'))

    # ================================================================ Smaller parks funds
    gift = P['gift']
    other = {o['id']: o for o in P['other_funds']}
    ghist = {h['fy']: h for h in gift['history']}
    flat_bal = ghist[2016]['closing']
    if any(abs(ghist[fy]['closing'] - flat_bal) > 0.005 for fy in range(2016, 2026)):
        fail('the Park Gift Fund no longer stood still FY2016-FY2025')
    g26 = gift['current']
    small = [other['sr-1529'], other['sr-1532'], other['tr-8126']]
    small_sum = round(sum(o['current']['closing'] for o in small), 2)
    cap = other['cp-3108']
    out['other-parks-funds'] = TP.page(
        'other-parks-funds',
        'The Park Gift Fund took in %s in FY2011 and stood at %s from FY2016 to FY2025.'
        % (C.usd(ghist[2011]['revenue']), C.usd(flat_bal)),
        [f('g11', U(ghist[2011]['revenue']), 'taken in by the Park Gift Fund, FY2011',
           'published', allow=('FY2011',)),
         f('g13', U(ghist[2013]['revenue']), 'taken in by it, FY2013', 'published',
           allow=('FY2013',)),
         f('gflat', U(flat_bal), 'its balance at every year end, FY2016–FY2025', 'published',
           allow=('FY2016', 'FY2025')),
         f('g26in', U(g26['revenue']), 'taken in by it, July–March FY2026', 'published',
           allow=('FY2026',)),
         f('g26', U(g26['closing']), 'its balance, 31 March 2026', 'published',
           allow=('31', '2026')),
         f('small', U2(small_sum), 'skate park, Marshall Park and playground funds, together',
           'published'),
         f('capital', U(cap['current']['closing']), 'in the Marshall Park design account, '
           'FY2025', 'published', allow=('FY2025',))],
        [con('The Park Gift Fund took in %s in FY2011 and %s in FY2013.'
             % (C.usd(ghist[2011]['revenue']), C.usd(ghist[2013]['revenue'])),
             ['g11', 'g13'], {'a': U(ghist[2011]['revenue']), 'b': U(ghist[2013]['revenue'])},
             allow=('FY2011', 'FY2013')),
         con('It ended every year from FY2016 to FY2025 at %s, then took in %s in FY2026.'
             % (C.usd(flat_bal), C.usd(g26['revenue'])), ['gflat', 'g26in', 'g26'],
             {'b': U(flat_bal), 'a': U(g26['revenue'])},
             allow=('FY2016', 'FY2025', 'FY2026'),
             notes=[step('Who gave, and for what, is not in the fund reports.', 'gap',
                         allow=('1523',),
                         closes='the receipt detail for fund 1523')]),
         con('Three smaller parks funds hold %s between them at 31 March 2026.'
             % usd2(small_sum), ['small'], {'a': U2(small_sum)}, allow=('31', '2026'))],
        sources=[src['sr26'], src['trust26'], src['ar11'], src['ar23'], src['d-read']],
        finding_figures={'a': U(ghist[2011]['revenue']), 'b': U(flat_bal)},
        finding_allow=('FY2011', 'FY2016', 'FY2025'))

    # ================================================================ Registration sales
    sales = BP.myrec()
    prog = [r for r in sales if r['report'] == 'program']
    mem = [r for r in sales if r['report'] == 'membership']
    m = P['myrec']
    tot = sum(r['total'] for r in sales)
    if abs(tot - m['total']) > 0.005:
        fail('the MyRec CSV and parks.json disagree on the FY2025 total')
    nonres = sum(r['nonres_total'] for r in sales)
    nonres_n = sum(r['nonres_count'] for r in sales)
    all_n = sum(r['total_count'] for r in sales)
    top = max(prog, key=lambda r: r['total'])
    nothing = [r for r in prog if abs(r['total']) < 0.005]
    neg = [r for r in prog if r['total'] < 0]
    beach = [r for r in mem if r['program'] == '2025 BEACH PASSES'][0]
    out['registration-sales'] = TP.page(
        'registration-sales',
        'The registration system recorded %s in FY2025, and non-residents paid %s of it.'
        % (C.usd(tot), C.pct(100 * nonres / tot, 0)),
        [f('tot', U(tot), 'recorded by MyRec, FY2025, both reports', 'published',
           allow=('FY2025',)),
         f('prog', U(m['program_total']), 'programme sales, %s programmes'
           % C.num(len(prog)), 'published', {'n': N(len(prog))}),
         f('progn', N(m['program_n'], 'registrations'), 'programme registrations', 'published'),
         f('mem', U(m['membership_total']), 'beach passes and memberships', 'published'),
         f('beach', N(beach['total_count'], 'passes'), '2025 beach passes sold, for %s'
           % C.usd(beach['total']), 'published', {'b': U(beach['total'])}, allow=('2025',)),
         f('nonres', PC(100 * nonres / tot), 'of the money paid by non-residents', 'published'),
         f('nonresn', N(nonres_n, 'registrations'), 'registrations by non-residents, of %s'
           % C.num(all_n),
           'published', {'n': N(all_n)}),
         f('top', U(top['total']), 'the largest programme, %s' % top['program'],
           'published', allow=(top['program'],)),
         f('nothing', N(len(nothing), 'programmes'), 'programmes recording no money at all',
           'published'),
         f('books', None, 'how much of it reached the town’s books', 'gap',
           closes='the FY2025 special-revenue report and fund 1500’s journal')],
        [con('Programmes brought in %s and beach passes and memberships %s.'
             % (C.usd(m['program_total']), C.usd(m['membership_total'])),
             ['prog', 'progn', 'mem', 'beach'],
             {'a': U(m['program_total']), 'b': U(m['membership_total'])}),
         con('One programme, %s, was %s of the programme money.'
             % (top['program'], C.pct(100 * top['total'] / m['program_total'], 0)),
             ['top', 'prog'], {'a': PC(100 * top['total'] / m['program_total'])},
             allow=(top['program'],)),
         con('Non-residents made %s of %s registrations and paid %s.'
             % (C.num(nonres_n), C.num(all_n), C.usd(nonres)), ['nonresn', 'nonres'],
             {'a': N(nonres_n), 'b': N(all_n), 'c': U(nonres)}),
         con('A sales report is what the system recorded, not what the town deposited.',
             ['tot', 'books', 'nothing'],
             notes=[step('%s programmes recorded net refunds; costs and waivers are not in a '
                         'sales report.' % C.num(len(neg)).capitalize(), 'gap',
                         {'n': N(len(neg))},
                         closes='the cost of each programme, from the department’s own '
                                'accounts')])],
        table=dict(caption='What MyRec recorded, FY2025', views=[dict(
            key='sales', label='MyRec sales reports', total_col=2, kinds=['ledger'] * 3,
            columns=['Residents', 'Non-residents', 'Total'],
            rows=[dict(label=r['program'],
                       cells=[usd2(r['res_total']), usd2(r['nonres_total']), usd2(r['total'])])
                  for r in sorted(sales, key=lambda r: -r['total'])],
            note='Two printouts from the registration system, 1 July 2024 to 30 June 2025, '
                 'each footed to the totals it prints. Negative figures are refunds.')]),
        sources=[src['myprog'], src['mymem'], src['d-myrec']],
        finding_figures={'a': U(tot), 'b': PC(100 * nonres / tot)}, finding_allow=('FY2025',))

    # ================================================================ Grounds bid
    bid_rows, bid_total = BP.bid()
    if bid_total != P['bid']['total']:
        fail('the grounds bid total no longer matches parks.json')
    mar = [r for r in bid_rows if r['park'] == 'Marshall Park'][0]
    mow = sum(r['mowing'] for r in bid_rows if r['mowing'])
    mown = [r for r in bid_rows if r['mowing']]
    share = 100.0 * bid_total / voted[2025]
    out['grounds-maintenance-bid'] = TP.page(
        'grounds-maintenance-bid',
        'A contractor bid %s for one year of grounds work at %s parks, from 1 July 2024.'
        % (C.usd(bid_total), 'six'),
        [f('bid', U(bid_total), 'bid for year one, six parks, from July 2024', 'published',
           allow=('2024',)),
         f('marshall', U(mar['year_one']), 'of it for Marshall Park', 'published'),
         f('mow', U(mow), 'of it for mowing, at %s parks' % C.num(len(mown)), 'published',
           {'n': N(len(mown))}),
         f('v25', U(voted[2025]), 'voted for Parks, FY2025', 'published', allow=('FY2025',)),
         f('share', PC(share), 'the bid as a share of that vote (ours)', 'estimate'),
         f('taken', None, 'whether the bid was accepted, and what was paid', 'gap',
           closes='the purchase order and the FY2025 payments against it')],
        [con('The bid priced Marshall Park at %s, the most of the %s.'
             % (C.usd(mar['year_one']), 'six'), ['marshall', 'bid'], {'a': U(mar['year_one'])}),
         con('The year-one bid equals %s of the %s voted for Parks in FY2025.'
             % (C.pct(share, 0), C.usd(voted[2025])), ['bid', 'v25', 'share'],
             {'a': PC(share), 'b': U(voted[2025])}, allow=('FY2025',),
             notes=[step('A bid is a vendor’s offer, and which account would pay it is not '
                         'stated.', 'gap',
                         closes='the purchase order and the account it was charged to')])],
        table=dict(caption='The grounds bid by park, year one', views=[dict(
            key='bid', label='The bid sheet', total_col=1, kinds=['stated', 'stated'],
            columns=['Mowing', 'Year one, all work'],
            rows=[dict(label=r['park'], cells=[cell(r['mowing']), C.usd(r['year_one'])])
                  for r in bid_rows],
            note='The sheet’s own Location Total line, read from its text layer. A bid, not '
                 'a payment.')]),
        sources=[src['bid'], src['glwb'], src['d-gl']],
        finding_figures={'a': U(bid_total)}, finding_allow=('1', '2024', 'six'))

    # ================================================================ School facilities fund
    sser = read_series('School Facilities Use')
    sbal = balances('1306')
    s26 = funds[1306]
    if abs(sbal[2025] - s26['opening']) > 0.005:
        fail('fund 1306: the FY2025 annual-report balance no longer equals the FY26 opening')
    jump = round(sbal[2025] - sbal[2024], 2)
    best_fy = max(sser, key=lambda y: sser[y]['receipts'] or 0)
    best = sser[best_fy]['receipts']
    if not jump > best:
        fail('fund 1306’s FY2025 rise no longer exceeds its best year of receipts')
    srow = []
    for fy in range(2025, 2010, -1):
        if fy in sser:
            r = sser[fy]
            srow.append(dict(label=C.fy(fy), cells=[cell(r['receipts']), cell(r['disbursed']),
                                                    cell(r['carried'])]))
        else:
            srow.append(dict(label=C.fy(fy), cells=[None, None, C.usd(sbal[fy])]))
    out['school-facilities-fund'] = TP.page(
        'school-facilities-fund',
        'The schools’ rental fund rose %s in FY2025, more than its receipts in any year '
        'FY2011–FY2023.' % C.usd(jump),
        [f('in26', U(s26['revenue']), 'into fund 1306, July–March FY2026', 'published',
           allow=('1306', 'FY2026')),
         f('out26', U(s26['expenditure']), 'spent from it, July–March FY2026', 'published',
           allow=('FY2026',)),
         f('held26', U(s26['available']), 'held, 31 March 2026', 'published',
           allow=('31', '2026')),
         f('b24', U2(sbal[2024]), 'balance at 30 June 2024, annual report', 'published',
           allow=('30', '2024')),
         f('b25', U2(sbal[2025]), 'balance at 30 June 2025, annual report', 'published',
           allow=('30', '2025')),
         f('jump', U(jump), 'the rise in FY2025 (our subtraction)', 'estimate',
           allow=('FY2025',)),
         f('best', U(best), 'taken in during %s, the most FY2011–FY2023' % C.fy(best_fy),
           'published', allow=(C.fy(best_fy), 'FY2011', 'FY2023')),
         f('flows25', None, 'what went in and out in FY2025', 'gap', allow=('FY2025',),
           closes='the FY2025 special-revenue report, or fund 1306’s journal')],
        [con('Groups renting school buildings and fields pay into fund 1306; it held %s at 31 '
             'March 2026.' % C.usd(s26['available']), ['in26', 'out26', 'held26'],
             {'a': U(s26['available'])}, allow=('1306', '31', '2026'),
             notes=[step('Who paid, and for what, is not in a balance report.', 'gap',
                         allow=('1306',),
                         closes='fund 1306’s receipt detail, by payer')]),
         con('It went from %s to %s in FY2025, a rise of %s.'
             % (usd2(sbal[2024]), usd2(sbal[2025]), C.usd(jump)), ['b24', 'b25', 'jump'],
             {'a': U2(sbal[2024]), 'b': U2(sbal[2025]), 'c': U(jump)}, allow=('FY2025',)),
         con('No year from FY2011 to FY2023 took in more than %s.' % C.usd(best),
             ['best', 'jump', 'flows25'], {'a': U(best)}, allow=('FY2011', 'FY2023'),
             notes=[step('A transfer in, less charged to the fund, or a year of high rent all '
                         'fit the two balances; nothing here tests which.', 'hypothesis')])],
        table=dict(caption='School Facilities Use, fund 1306, by year', views=[dict(
            key='fund', label='Annual town reports', total_col=2, kinds=['ledger'] * 3,
            columns=['Taken in', 'Spent', 'Balance'], rows=srow,
            note='FY2011–FY2023 each row ties forward + receipts − disbursements = carried; '
                 'FY2018 closed in deficit. FY2024 and FY2025 print a balance only.')]),
        sources=[src['sr26'], src['email'], src['ar11'], src['ar23'], src['ar24'], src['ar25'],
                 src['d-read'], src['d-funds']],
        finding_figures={'a': U(jump)}, finding_allow=('FY2025', 'FY2011', 'FY2023'))

    # ================================================================ School field upkeep
    mt = {r['item']: r for r in Y['maintenance']}
    for r in Y['maintenance']:
        if r['basis'] != 'stated':
            fail('a field-maintenance figure is no longer marked stated')
    autumn = float(mt['Landscaper, mowing the athletic grass fields, autumn']['amount'])
    spring = float(mt['Landscaper, mowing the athletic grass fields, spring']['amount'])
    repair = float(mt['Landscaper, summer field repair']['amount'])
    allg = float(mt['All fields and grounds maintenance']['amount'])
    veh = float(mt['Of that: vehicle and equipment maintenance and repair']['amount'])
    out['school-field-upkeep'] = TP.page(
        'school-field-upkeep',
        'The district says it pays to mow its grass fields from the fund the field rent goes '
        'into.',
        [f('mow', U(autumn + spring), 'mowing, autumn and spring, FY2024 (stated)', 'published',
           allow=('FY2024',)),
         f('repair', U(repair), 'summer field repair, 2023 (stated)', 'published',
           allow=('2023',)),
         f('all', U(allg), 'all fields and grounds work, FY2024, approximate (stated)',
           'published', allow=('FY2024',)),
         f('veh', U(veh), 'of that, vehicles and equipment, which also plough', 'published'),
         f('ledger', None, 'what fund 1306 actually paid for grounds', 'gap', allow=('1306',),
           closes='fund 1306’s FY2024 expenditure detail')],
        [con('The district puts mowing at %s for the autumn and spring of FY2024, paid from '
             'fund 1306.' % C.usd(autumn + spring), ['mow', 'ledger'],
             {'a': U(autumn + spring)}, allow=('FY2024', '1306')),
         con('It puts all fields and grounds work at about %s for FY2024, vehicles included.'
             % C.usd(allg), ['all', 'veh', 'repair'], {'a': U(allg)}, allow=('FY2024',),
             notes=[step('These are the district’s figures in an email, not a printout from '
                         'the books.', 'gap', allow=('1306', 'FY2024'),
                         closes='fund 1306’s expenditure detail and the grounds accounts, '
                                'FY2024')])],
        sources=[src['email'], src['d-maint']])

    # ================================================================ Youth league payments
    rec = Y['receipts']
    rtot = round(sum(r['amount'] for r in rec), 2)
    if abs(rtot - Y['receipts_total']) > 0.005:
        fail('the receipts no longer sum to youth-sports.json’s total')
    byfy = defaultdict(float)
    for r in rec:
        byfy[r['fy']] += r['amount']
    leagues = Y['leagues']
    payer = 'Lunenburg Youth Soccer Association'
    if payer not in leagues:
        fail('the contact list no longer names %s' % payer)
    out['youth-league-payments'] = TP.page(
        'youth-league-payments',
        'One league’s field payments are on record: %s across %s receipts, FY2024 to FY2026.'
        % (usd2(rtot), C.num(len(rec))),
        [f('rtot', U2(rtot), 'paid by %s (stated)' % payer, 'published', allow=(payer,)),
         f('rn', N(len(rec), 'receipts'), 'receipts in the district’s workbook, FY2024–FY2026',
           'published', allow=('FY2024', 'FY2026')),
         f('r25', U(byfy['FY2025']), 'of it listed under FY2025', 'published',
           allow=('FY2025',)),
         f('clubs', N(len(leagues), 'organisations'), 'sports organisations the Parks page '
           'lists as contacts', 'published'),
         f('others', None, 'what any other group pays for a field', 'gap',
           closes='the receipt detail for fund 1306 and fund 1500, by payer')],
        [con('The district’s workbook lists %s receipts from %s, %s in all.'
             % (C.num(len(rec)), payer, usd2(rtot)), ['rtot', 'rn', 'r25'],
             {'n': N(len(rec)), 'a': U2(rtot)}, allow=(payer,),
             notes=[step('It is the group a records request asked about first; nothing here '
                         'compares it with any other.', 'gap', allow=('1306',),
                         closes='every field-use receipt, by payer, from fund 1306’s journal')]),
         con('The town’s Parks page lists %s sports organisations as contacts it does not run.'
             % C.num(len(leagues)), ['clubs', 'others'], {'n': N(len(leagues))})],
        table=dict(caption='Receipts from the one league on record', views=[dict(
            key='receipts', label='The district’s workbook', total_col=1,
            kinds=['stated', 'stated'], columns=['Fiscal year as listed', 'Amount'],
            rows=[dict(label=r['date'], cells=[r['fy'], usd2(r['amount'])]) for r in rec],
            note='Typed into a workbook by the district’s business office. The fiscal year is '
                 'as the workbook lists it; one receipt dated July 2024 is listed under FY2024.'
                 )]),
        sources=[src['receipts'], src['d-receipts'], src['parkspage']],
        finding_figures={'a': U2(rtot), 'n': N(len(rec))},
        finding_allow=('FY2024', 'FY2026'))
    if not any(r['date'] == '2024-07-08' and r['fy'] == 'FY2024' for r in rec):
        fail('the July 2024 receipt is no longer listed under FY2024; fix the table note')

    # ================================================================ Artificial turf fund
    t26 = funds[1545]
    tbal = balances('1545')
    if abs(tbal[2025] - t26['opening']) > 0.005:
        fail('fund 1545: the FY2025 annual-report balance no longer equals the FY26 opening')
    plan = Y['said'][0]
    if plan['date'] != '2016-05-03':
        fail('the 2016 turf plan is no longer the first record in youth-sports.json')
    amts = [float(x.replace(',', '')) for x in re.findall(r'\$([\d,]+)', plan['what'])]
    if len(amts) < 2 or abs(amts[0] + amts[1] - t26['revenue']) > 0.005:
        fail('the 2016 plan’s first two sums no longer add to the turf fund’s FY2026 revenue')
    out['artificial-turf-fund'] = TP.page(
        'artificial-turf-fund',
        'The Artificial Turf fund took in %s in FY2026 and held %s at 31 March 2026.'
        % (C.usd(t26['revenue']), C.usd(t26['available'])),
        [f('in', U(t26['revenue']), 'into fund 1545, July–March FY2026', 'published',
           allow=('1545', 'FY2026')),
         f('out', U(t26['expenditure']), 'spent from it, July–March FY2026', 'published',
           allow=('FY2026',)),
         f('held', U(t26['available']), 'held, 31 March 2026', 'published',
           allow=('31', '2026')),
         f('b24', U(tbal[2024]), 'balance at 30 June 2024, annual report', 'published',
           allow=('30', '2024')),
         f('b25', U(tbal[2025]), 'balance at 30 June 2025, annual report', 'published',
           allow=('30', '2025')),
         f('split', None, 'who paid the FY2026 receipts', 'gap', allow=('FY2026',),
           closes='the receipt detail for fund 1545')],
        [con('The fund took in %s and spent %s from July to March FY2026.'
             % (C.usd(t26['revenue']), C.usd(t26['expenditure'])), ['in', 'out', 'held'],
             {'a': U(t26['revenue']), 'b': U(t26['expenditure'])}, allow=('FY2026',),
             notes=[step('Machine captions of the Select Board on 3 May 2016 describe %s a year '
                         'from a cell tower and %s from a youth league; the two add to this '
                         'year’s receipts. No ledger splits them.'
                         % (C.usd(amts[0]), C.usd(amts[1])), 'hypothesis',
                         {'a': U(amts[0]), 'b': U(amts[1])}, allow=('3', '2016'))]),
         con('Its balance rose from %s at 30 June 2024 to %s at 31 March 2026.'
             % (C.usd(tbal[2024]), C.usd(t26['available'])), ['b24', 'b25', 'held', 'split'],
             {'a': U(tbal[2024]), 'b': U(t26['available'])},
             allow=('30', '2024', '31', '2026'))],
        sources=[src['sr26'], src['ar24'], src['ar25'], src['d-funds']],
        finding_figures={'a': U(t26['revenue']), 'b': U(t26['available'])},
        finding_allow=('FY2026', '31', '2026'))

    # ================================================================ the hub
    tiers = [
        LD.tier('What the town votes', [
            f('h-v26', U(v26), 'voted for Parks, FY2026', 'published', allow=('FY2026',)),
            f('h-exp26', U(a26['expended']), 'paid by period 12, FY2026', 'published',
              allow=('FY2026', '12')),
            f('h-rate', PC(rate, 1), 'a year, the vote’s growth since FY2010 (ours)',
              'estimate', allow=('FY2010',))]),
        LD.tier('The funds beside it', [
            f('h-park', U(f26['closing']), 'in the parks fee fund, 31 March 2026', 'published',
              allow=('31', '2026')),
            f('h-myrec', U(tot), 'recorded by the registration system, FY2025', 'published',
              allow=('FY2025',)),
            f('h-1306', U(s26['available']), 'in the schools’ rental fund, 31 March 2026',
              'published', allow=('31', '2026')),
            f('h-1545', U(t26['available']), 'in the turf fund, 31 March 2026', 'published',
              allow=('31', '2026'))]),
        LD.tier('What is not settled', [
            f('h-jump', U(jump), 'the rental fund’s unexplained FY2025 rise', 'estimate',
              allow=('FY2025',)),
            f('h-books', None, 'how much of the registration money reached the books', 'gap',
              closes='the FY2025 special-revenue report and fund 1500’s journal'),
            f('h-payers', None, 'who pays to use the fields', 'gap',
              closes='the receipt detail for funds 1306, 1500 and 1545, by payer')]),
    ]
    hub_ladder = LD.ladder(tiers, [
        LD.conclusion('Town Meeting voted Parks %s for FY2026; its budget grew %s a year since '
                      'FY2010.' % (C.usd(v26), C.pct(rate, 1)), ['h-v26', 'h-rate'],
                      {'a': U(v26), 'r': PC(rate, 1)}, allow=('FY2026', 'FY2010')),
        LD.conclusion('The parks’ own fee fund held %s at 31 March 2026, outside the vote.'
                      % C.usd(f26['closing']), ['h-park', 'h-myrec'], {'a': U(f26['closing'])},
                      allow=('31', '2026')),
        LD.conclusion('The schools’ rental fund held %s and the turf fund %s at 31 March 2026.'
                      % (C.usd(s26['available']), C.usd(t26['available'])),
                      ['h-1306', 'h-1545', 'h-payers'],
                      {'a': U(s26['available']), 'b': U(t26['available'])},
                      allow=('31', '2026')),
        LD.conclusion('The schools’ rental fund rose %s in FY2025, and no schedule shows why.'
                      % C.usd(jump), ['h-jump'], {'a': U(jump)}, allow=('FY2025',)),
        LD.conclusion('What the registration money became on the town’s books is not published.',
                      ['h-myrec', 'h-books']),
    ])
    out[CID] = TP.hub(
        CID,
        'Town Meeting voted the Parks department %s for FY2026. Beside it, a fee fund held %s '
        'at 31 March 2026, and rent for school fields goes to a school fund. Neither fund is '
        'part of the vote.' % (C.usd(v26), C.usd(f26['closing'])),
        hub_ladder,
        answer_figures={'a': U(v26), 'b': U(f26['closing'])},
        answer_allow=('FY2026', '31', '2026'))

    if sorted(k for k in out if k != CID) != sorted(MINE):
        fail('the pages built are not the pages the registry gives this script: %s'
             % sorted(set(MINE) ^ set(out)))
    return out


def outputs():
    return {os.path.join(OUT_DIR, '%s.json' % t):
            json.dumps(p, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
            for t, p in build().items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    outs = outputs()
    if a.check:
        stale = []
        for p, text in outs.items():
            cur = open(p, encoding='utf-8').read() if os.path.exists(p) else None
            if cur != text:
                stale.append(os.path.relpath(p, ROOT))
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('parks topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
