#!/usr/bin/env python3
"""THE TOWN GENERAL FUND, the whole of it: what comes in, what goes out, what is left at 30 June,
and which records hold each of those for which years. One topic page on the Department budgets
shelf; /town-funds/general-fund opens it.

    python3 scripts/build_town_general_fund.py           # write the topic payload
    python3 scripts/build_town_general_fund.py --check   # fail if it would change

TJ, 31 October 2026, on the page that held this address before: *"it seems focused on the
school, but its not presented that way in the url or heading ... build another page for the town
fund and show what 'should be there'."* What was there -- the three school receipts the Town
books -- is now /school-all-funds/school-receipts-to-town (build_school_receipts_to_town.py).

SO THE PAGE HAS TWO JOBS, in this order:
  1. THE FUND ITSELF. Revenue the Town planned on, by source, FY2023-FY2026, from its own revenue
     workbook (the Finance Committee's FY26 files, a draft dated 27 February 2025): the tax levy,
     state aid on the cherry sheet, local receipts. Every year's sources must add to the
     workbook's own total, or nothing is written.
  2. WHAT A FULL RECORD OF IT HOLDS -- the "should be there". Five parts of a general fund's year
     (revenue planned, revenue received, spending voted, spending at year end, the balance at 30
     June) against three stretches of years, each cell saying which record holds it, or that
     none here does. The year ranges in the cells are READ OFF THE DATASETS at build time; if a
     dataset gains or loses a year the build refuses until the cell is rewritten, because a cell
     that says "FY2011 to FY2022" is prose (rule 2).

WHAT THIS PAGE DOES NOT DO: rank the departments (Budget by department does), follow the voted
total (Voted budget total does), or explain free cash (the Free cash shelf does). It links them.
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
import topic_blocks as TB  # noqa: E402

ID = 'town-general-fund'
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % ID)
DATA = os.path.join(ROOT, 'sources', 'data')
REVDIST = os.path.join(DATA, 'revenue-distribution-fy26.csv')
DOC = dict(
    revdist='/docs/budget-workbooks/finance-committee/fy26-budget/draft-rev-dist.-proj-fy26-update-2.27.25.xlsx',
    revdist_csv='/docs/data/revenue-distribution-fy26.csv',
    freecash='/docs/budget-workbooks/finance-committee/fy27-budget/tm-warrant/free-cash-fact-sheet.docx',
    balance='/docs/data/balance-sheet.csv',
    receipts='/docs/data/annual-report-receipts.csv',
    approp='/docs/data/report-appropriations.csv',
    q3='/docs/data/town-ledger-fy26-q3.csv',
    p12='/docs/town-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.xlsx',
)
# The workbook's three revenue sources, by its own row names, and what we call them.
SOURCES = [('Total Tax Levy: Total', 'Property tax levy'),
           ('Cherry Sheet Receipts', 'State aid, cherry sheet'),
           ('Local Receipts', 'Local receipts')]
YEARS = {2023: 'FY23 BUDGETED', 2024: 'FY24 BUDGETED', 2025: 'FY25 BUDGETED', 2026: 'FY26 PROJECTED'}


def fail(msg):
    raise SystemExit('build_town_general_fund: ' + msg)


def revenue():
    """{fy: {source label: amount, 'Total': amount}} from the workbook's Revenues block."""
    out = {fy: {} for fy in YEARS}
    for r in csv.DictReader(open(REVDIST, encoding='utf-8')):
        parts = [p.strip() for p in r['line'].split(' / ')]
        if len(parts) != 3 or parts[0] != 'Revenues':
            continue
        for fy, col in YEARS.items():
            if parts[2] == col:
                out[fy][parts[1]] = float(r['fy26'])
    for fy, d in out.items():
        need = [k for k, _ in SOURCES] + ['Total']
        if any(k not in d for k in need):
            fail('FY%d: the workbook has no %s row' % (fy, [k for k in need if k not in d]))
        s = sum(d[k] for k, _ in SOURCES)
        if abs(s - d['Total']) > 0.5:
            fail('FY%d: levy, cherry sheet and local receipts sum to %.2f, the workbook prints %.2f'
                 % (fy, s, d['Total']))
    return out


def years_in(fn, keep=lambda r: True, key='fy'):
    return sorted({int(r[key]) for r in csv.DictReader(open(os.path.join(DATA, fn), encoding='utf-8')) if keep(r)})


def free_cash():
    return {int(r['fiscal_year']): r for r in csv.DictReader(
        open(os.path.join(DATA, 'free-cash-history-fincom.csv'), encoding='utf-8'))}


def balance():
    """{fy: undesignated general fund balance at 30 June}, from the combined balance sheet."""
    out = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'balance-sheet.csv'), encoding='utf-8')):
        if r['fund'] == 'general' and r['section'] == 'fund_balances' and 'UNDESIGNATED' in r['line'].upper() \
                and 'UNRESERVED' in r['line'].upper() or (r['fund'] == 'general' and r['line'] == 'UNDESIGNATED'):
            out[int(r['fy'])] = float(r['amount'])
    return out


def levy_build(fy=2026):
    """The levy limit built up, from the workbook's Revenues block: prior limit, the 2.5% step,
    new growth, debt exclusions -- and the total it prints. Must add to the cent, or nothing."""
    col = YEARS[fy]
    got = {}
    for r in csv.DictReader(open(REVDIST, encoding='utf-8')):
        parts = [x.strip() for x in r['line'].split(' / ')]
        if len(parts) == 3 and parts[0] == 'Revenues' and parts[2] == col:
            got[parts[1]] = float(r['fy26'])
    names = ['Prior Year Levy Limit', '2 1/2% Increase', 'Estimated New Growth', 'Debt Exclusions',
             'Total Tax Levy: Total']
    if any(n not in got for n in names):
        fail('FY%d levy build: the workbook lacks %s' % (fy, [n for n in names if n not in got]))
    # The sheet's summary block at its top prints its own new-growth estimate; read it, for the note.
    for r in csv.DictReader(open(REVDIST, encoding='utf-8')):
        if r['line'].strip() == 'Estimated New Growth':
            got['summary growth'] = float(r['fy25'])
    if 'summary growth' not in got:
        fail('the summary block has no Estimated New Growth row')
    if abs(sum(got[n] for n in names[:4]) - got[names[4]]) > 0.01:
        fail('FY%d: prior limit, 2.5%%, new growth and debt exclusions do not add to the levy' % fy)
    return [got[n] for n in names] + [got['summary growth']]


def page():
    R = revenue()
    fys = sorted(R)
    y0, y1 = fys[0], fys[-1]
    U = lambda v: figure(v, C.usd(v))
    F = lambda y: figure(y, C.fy(y), 'fiscal year')
    P = lambda v: figure(v, C.pct(v), '%')
    tot1, tot0 = R[y1]['Total'], R[y0]['Total']
    levy_sh = R[y1][SOURCES[0][0]] / tot1 * 100
    aid_sh = R[y1][SOURCES[1][0]] / tot1 * 100
    prior, cap, growth, debt, levy, growth_alt = levy_build(y1)
    FC = free_cash()
    fc_last = max(FC)
    fc = float(FC[fc_last]['certified_free_cash'])
    B = balance()
    b_last = max(B)

    # ---- the signature: where the money comes from, four years
    chart = TP.series(
        'Revenue the Town planned on', [C.fy(y) for y in fys],
        [TP.track(name, [R[y][k] for y in fys], 'published', 'bar') for k, name in SOURCES],
        '$', kind='bar', stacked=True, totals=True,
        note='The Town’s revenue workbook: %s to %s as budgeted, %s as projected before the year began.'
             % (C.fy(y0), C.fy(fys[-2]), C.fy(y1)),
        note_figures={'a': F(y0), 'b': F(fys[-2]), 'c': F(y1)})

    # ---- the mechanism: how the largest source is allowed to grow
    bridge = TB.chart(TP.bridge(
        'How the levy is built', ('Last year’s levy limit', prior),
        [('The 2.5% the law allows', cap), ('New growth, estimated', growth),
         ('Debt voters excluded from the cap', debt)],
        ('The levy', levy), '$',
        note='%s, from the same workbook. Its summary block estimates new growth at %s instead.'
             % (C.fy(y1), C.usd(growth_alt)), note_figures={'y': F(y1), 'g': U(growth_alt)}),
        so=('The cap lets the levy rise %s; new growth and excluded debt carry the rest.' % C.usd(cap),
            {'a': U(cap)}))

    define = TB.explain('What the general fund is', [
        '**The Town’s main operating account.** The levy, state aid and local receipts come in; Town '
        'Meeting’s budget goes out: Town departments, the School Department, Monty Tech, benefits, debt.',
        ('**What is left at 30 June becomes free cash** once the state certifies it, to spend the year '
         'after.', None, ('30',)),
        '**Not in it:** grants, revolving funds, enterprise funds such as sewer, the stabilization funds.',
    ], tone='define')

    # ---- what should be there: each part of a fund's year, against every year
    rec, app, bal = (set(years_in('annual-report-receipts.csv')), set(years_in('report-appropriations.csv')),
                     set(B))
    fc_closes = {y - 1 for y in FC}               # the fact sheet labels by the year it is spent
    span = list(range(2011, y1 + 1))
    if max(rec) != 2022 or max(app) != 2025 or max(bal) != 2022 or max(fc_closes) != 2025:
        fail('a dataset gained or lost a year: rewrite the legend notes')
    def st(row, y):
        if row == 'plan':
            return 'held' if y in R else 'none'
        if row == 'recv':
            return 'held' if y in rec else 'part' if y == 2025 else 'private' if y == y1 else 'none'
        if row == 'vote':
            return 'held' if y in app or y == y1 else 'none'
        if row == 'spent':
            return 'held' if y in app else 'part' if y == y1 else 'none'
        return 'held' if y in bal else 'part' if y in fc_closes else 'none'
    rows = [('plan', 'Revenue planned'), ('recv', 'Revenue received'), ('vote', 'Spending voted'),
            ('spent', 'Spending at year end'), ('bal', 'Balance at year end')]
    lit = tuple(C.fy(y) for y in (2022, 2023, 2025, y1)) + ('30 June', '31 March', '12', '13', '93')
    record = TB.timeline(
        'What a full record holds', ['FY' + str(y)[2:] for y in span],
        [('Each part of the year', [TB.track(lab, [st(k, y) for y in span]) for k, lab in rows])],
        [('held', 'Held here', 'good'), ('part', 'Partly held', 'neutral'),
         ('private', 'Held, not public', 'other'), ('none', 'Not held here', 'muted')],
        note=('Received after %s: only %s local receipts are public; %s’s receipts page is a 93 dpi '
              'image; a %s report to 31 March is held but prints a staff login. Spending in %s: to June '
              '(period 12), before the close (period 13). Balance after %s: certified free cash only.'
              % (C.fy(2022), C.fy(2025), C.fy(2023), C.fy(y1), C.fy(y1), C.fy(2022)), None, lit))

    f = LD.fact
    facts = [
        f('rev', U(tot1), 'revenue planned, %s' % C.fy(y1), 'published', label_figures={'y': F(y1)}),
        f('levy', P(levy_sh), 'of it from the property tax levy', 'published'),
        f('aid', U(R[y1][SOURCES[1][0]]), 'state aid on the cherry sheet, %s' % C.fy(y1), 'published',
          label_figures={'y': F(y1)}),
        f('cap', U(cap), 'levy rise the 2.5%% cap allows, %s' % C.fy(y1), 'published',
          label_figures={'y': F(y1)}, allow=('2.5%',)),
        f('growth', U(growth), 'new growth the Town estimated, %s' % C.fy(y1), 'published',
          label_figures={'y': F(y1)}),
        f('rev0', U(tot0), 'revenue budgeted, %s' % C.fy(y0), 'published', label_figures={'y': F(y0)}),
        f('fc', U(fc), 'free cash certified to spend in %s' % C.fy(fc_last), 'published',
          label_figures={'y': F(fc_last)}),
        f('bal', U(B[b_last]), 'undesignated balance at year end, %s' % C.fy(b_last), 'published',
          label_figures={'y': F(b_last)}),
        f('recv', None, 'revenue received since %s, by source' % C.fy(2022), 'gap',
          label_figures={'a': F(2022)}, closes='The Town’s MUNIS revenue report at each year’s close'),
        f('close', None, 'spending at the %s close, by department' % C.fy(y1), 'gap',
          label_figures={'y': F(y1)}, closes='The Town general fund year-to-date report, period 13, FY2026'),
    ]
    con = TP.conclusion
    conclusions = [
        con('The property tax levy is %s of the revenue the Town planned on for %s; state aid is %s.'
            % (C.pct(levy_sh), C.fy(y1), C.pct(aid_sh)), ['levy', 'aid', 'rev'],
            {'a': P(levy_sh), 'y': F(y1), 'b': P(aid_sh)},
            so='Most of the fund moves with the levy, which state law caps; state aid is set in the state budget.'),
        con('The cap let the levy rise %s for %s; the Town estimated %s more from new growth.'
            % (C.usd(cap), C.fy(y1), C.usd(growth)), ['cap', 'growth'],
            {'a': U(cap), 'y': F(y1), 'b': U(growth)},
            so='Above the cap, the levy grows only by new growth, debt voters exclude, or an override vote.'),
        con('Since %s, revenue received is public only for %s’s local receipts.' % (C.fy(2022), C.fy(2025)),
            ['recv', 'close'], {'y': F(2022), 'z': F(2025)},
            so='How each year closed, and why free cash came out where it did, cannot be read from public records here.'),
    ]
    sources = [
        dict(key='revdist', label='Town of Lunenburg — revenue distribution workbook, FY2026 projection, '
                                  '27 February 2025 (Finance Committee files)', href=DOC['revdist']),
        dict(key='freecash', label='Town of Lunenburg — Free Cash Fact Sheet, FY27 warrant packet', href=DOC['freecash']),
        dict(key='balance', label='Town of Lunenburg — annual town reports, combined balance sheet', href=DOC['balance']),
        dict(key='receipts', label='Town of Lunenburg — annual town reports, receipts schedules', href=DOC['receipts']),
        dict(key='approp', label='Town of Lunenburg — annual town reports, appropriation schedules', href=DOC['approp']),
        dict(key='q3', label='Town of Lunenburg — MUNIS general fund report, FY2026 to 31 March', href=DOC['q3']),
        dict(key='p12', label='Town of Lunenburg — MUNIS general fund report, FY2026 period 12', href=DOC['p12']),
    ]
    cite = TP.cite
    return TP.page(
        ID,
        'The Town planned on %s of general fund revenue for %s; %s of it is the property tax levy.'
        % (C.usd(tot1), C.fy(y1), C.pct(levy_sh)),
        facts, conclusions, chart=chart, sources=sources,
        finding_figures={'a': U(tot1), 'y': F(y1), 'b': P(levy_sh)},
        flow=['finding', cite(('chart', 0), 'revdist'), cite(bridge, 'revdist'), cite(define, 'freecash'),
              cite('ladder', 'revdist', 'freecash', 'balance'),
              cite(record, 'revdist', 'receipts', 'approp', 'balance', 'freecash', 'q3', 'p12'),
              'related', 'sources'],
        draft=None if ID in REG.TOPICS else dict(title='Town general fund', home='department-budgets'))


def render():
    return json.dumps(page(), ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text = render()
    if a.check:
        if not os.path.exists(OUT) or open(OUT, encoding='utf-8').read() != text:
            print('STALE %s' % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('town general fund: current')
        return 0
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, OUT)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
