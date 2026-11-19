#!/usr/bin/env python3
"""THE PARKS LEDGER, TO THE POSTING: a page for each parks fund and account, and two topic pages
that read across them.

    python3 scripts/build_parks_ledger.py           # write the payloads below
    python3 scripts/build_parks_ledger.py --check   # fail if any would change

TJ, 19 November 2026: *"for the school accounts, i can drop in and see the actual ledger. i
cant figure out how to do that here"* and *"i thought we were building a page that compared
year over year to identify what changed in either revenue or spending"*. Earlier: *"how much we
earn from each program, like soccer, beach, activities"* and *"where did they spend? On what?
for which program"*. And the rule that followed: every fund and every account has its own page.

WRITES
  fy28/public/data/town-funds/<slug>.json   ONE TOWN FUND OR LINE, any fund: the payload
                                            pages/TownFund.tsx draws at /town-funds/<slug> or
                                            /town-lines/<slug>. Its shape is documented there.
                                            Funds 1500 and 1523 and department 650 are the
                                            first three; another fund is another payload.
  fy28/public/data/town-funds/index.json    every such page: code, name, address
  fy28/public/data/topics/parks-year-changes.json
  fy28/public/data/topics/parks-programmes.json

Every figure is read through scripts/parks_ledger.py, which says which readings are ours (the
sales month a deposit names; the programme a payment was for).
"""
import argparse
import datetime
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topic_blocks as TB  # noqa: E402
from brief import step  # noqa: E402
import parks_ledger as L  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
FUND_DIR = os.path.join(PUB, 'town-funds')
TOPIC_DIR = os.path.join(PUB, 'topics')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')

# The three pages this script owns. Address = base + slug. `measure` is the id the accounts
# registry (sources/data/fund-owners.csv) gives the same thing, so build_finance.py can link it.
ITEMS = {
    'park-revolving-1500': dict(base='/town-funds/', code='1500', name='Park Revolving Fund',
                                measure='sr-1500'),
    'park-gift-1523': dict(base='/town-funds/', code='1523', name='Park Gift Fund',
                           measure='sr-1523'),
    'parks-recreation-650': dict(base='/town-lines/', code='650', name='Parks and Recreation',
                                 measure='gf-650'),
}
PARKS_BOARD = dict(name='Parks Commission', href='/boards/parks-commission/finance#accounts')


def fail(msg):
    raise SystemExit('build_parks_ledger: ' + msg)


def path_of(slug):
    return ITEMS[slug]['base'] + slug


def usd2(x):
    x = float(x)
    return ('-$' if x < -0.004 else '$') + format(abs(x), ',.2f')


def day(iso):
    d = datetime.date.fromisoformat(iso)
    return '%d %s %d' % (d.day, d.strftime('%b'), d.year)


def span(fy):
    return '1 July %d to 30 June %d' % (fy - 1, fy)


def load(name):
    return json.load(open(os.path.join(PUB, name), encoding='utf-8'))


def docs(key, label):
    import csv
    man = {r['key'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    if key not in man:
        fail('%s is not in archive-manifest.csv (rule 12)' % key)
    return dict(label=label, href='/docs/' + key)


def data_src(f, label):
    if not os.path.exists(os.path.join(ROOT, 'fy28', 'public', 'docs', 'data', f)):
        fail('/docs/data/%s is not published' % f)
    return dict(label='Lunenburg Budget Project — %s (%s)' % (f, label), href='/docs/data/' + f)


SRC_JOURNAL = lambda: data_src('munis-parks-journal.csv',
                               'funds 1500 and 1523, every posting FY2023 to the FY2026 close, '
                               'our redacted reading of the Town’s MUNIS journal')
SRC_P13 = lambda: data_src('munis-gf-p13-reading.csv',
                           'the general fund at the close, FY2025 and FY2026, our reading')
SRC_MYREC = lambda: data_src('parks-myrec-sales-fy2025.csv', 'both FY2025 MyRec sales reports, footed')


def short_acct(desc):
    return desc.title().replace('Park ', '').replace('Of ', 'of ').replace('And ', 'and ')


# ======================================================================== the fund pages
READ_FUND = [
    dict(h='One row is one posting',
         p='Each row is a line the Town Accountant’s system (MUNIS) printed for this fund: the date it '
           'posted, who was paid or what was deposited, the memo typed with it, and the amount.'),
    dict(h='Money in',
         p='Mostly monthly deposits from MyRec, the department’s registration system. The memo names '
           'the month the sales were made in, as PROG/SEP2024 PARK MYREC. Refunds and card charges '
           'post against them, so a month can net below its deposit. A few receipts name a league.'),
    dict(h='Money out',
         p='Invoices paid to instructors, contractors and suppliers, and journal entries that move a '
           'cost between this fund and the general fund. Only these and money in change the balance.'),
    dict(h='Purchase orders',
         p='When an order is placed the system sets money aside (order opened) and releases it as the '
           'invoice is paid (order paid down). They show what was committed. They are not spending.'),
    dict(h='Spending limit',
         p='Each July a budget is posted to the fund, the amount it may spend that year. It is a '
           'limit, not money; the memo names who asked for it.'),
    dict(h='The account name is the clerk’s choice',
         p='Which fee account a deposit lands in (programme, beach, field) is typed with it. In May '
           'and June 2026 registration deposits were posted to beach fees, so the split between the '
           'three is not reliable. The total is.'),
]


def fund_posting(r):
    k = L.kind(r)
    a = L.reader_amount(r)
    who = r['vendor'] or ('MyRec deposit' if L.is_myrec(r) else
                          'Journal entry' if r['source'] == 'GEN' else
                          'Budget' if r['source'] == 'BUA' else
                          'Other deposit' if r['source'] == 'CRP' else '—')
    return dict(d=day(r['effective_date']), iso=r['effective_date'], acct=r['account'],
                kind=k, how=L.SOURCE_LABEL.get(r['source'], r['source']), who=who,
                what=r['description'], ref=r['journal'], amt=usd2(a), n=round(a, 2),
                masked=bool(r['masked']))


def fund_item(slug):
    it = ITEMS[slug]
    code = it['code']
    P = load('parks.json')
    R = [r for r in L.rows() if r['fund'] == code]
    if not R:
        fail('fund %s has no postings' % code)
    acct_name = {r['account']: short_acct(r['account_description']) for r in R}
    acct_obj = {r['account']: r['object'] for r in R}
    acct_side = {r['account']: r['side'] for r in R}
    years = list(L.YEARS)
    cols = [dict(id='in', label='Taken in', means='receipts, net of refunds'),
            dict(id='out', label='Paid out', means='invoices paid and journal entries'),
            dict(id='limit', label='Spending limit', means='the budget posted to the fund'),
            dict(id='rows', label='Postings', means='lines in the journal, every kind')]
    acc_years, post_years, stats = {}, {}, {}
    J = {y['fy']: y for y in P['journal']['years']} if code == '1500' else {}
    for fy in years:
        ys = [r for r in R if int(r['fiscal_year']) == fy]
        sums = defaultdict(lambda: dict(inn=0.0, out=0.0, limit=0.0, rows=0))
        for r in ys:
            s = sums[r['account']]
            k = L.kind(r)
            a = L.reader_amount(r)
            s['rows'] += 1
            if k == 'in':
                s['inn'] += a
            elif k == 'out':
                s['out'] += a
            elif k == 'limit':
                s['limit'] += a
        accts = sorted(acct_name, key=lambda a: (acct_side[a] != 'revenue', acct_obj[a]))
        rows_ = []
        for a in accts:
            s = sums.get(a, dict(inn=0.0, out=0.0, limit=0.0, rows=0))
            rows_.append(dict(key=a, code=acct_obj[a], name=acct_name[a],
                              side='in' if acct_side[a] == 'revenue' else 'out',
                              t={'in': usd2(s['inn']) if acct_side[a] == 'revenue' else '—',
                                 'out': usd2(s['out']) if acct_side[a] != 'revenue' else '—',
                                 'limit': usd2(s['limit']) if s['limit'] else '—',
                                 'rows': C.num(s['rows'])},
                              n={'in': round(s['inn'], 2), 'out': round(s['out'], 2),
                                 'limit': round(s['limit'], 2), 'rows': s['rows']}))
        tin = round(sum(x['n']['in'] for x in rows_), 2)
        tout = round(sum(x['n']['out'] for x in rows_), 2)
        if J and (abs(tin - J[fy]['received']) > 0.005 or abs(tout - J[fy]['spent']) > 0.005):
            fail('fund %s FY%d: accounts do not sum to parks.json’s year' % (code, fy))
        total = dict(name='All accounts', t={'in': usd2(tin), 'out': usd2(tout),
                                            'limit': usd2(sum(x['n']['limit'] for x in rows_)) if any(x['n']['limit'] for x in rows_) else '—',
                                            'rows': C.num(len(ys))})
        acc_years[C.fy(fy)] = dict(rows=rows_, total=total)
        post_years[C.fy(fy)] = [fund_posting(r) for r in
                                sorted(ys, key=lambda r: (r['effective_date'], r['journal'], r['line']))]
        if code == '1500':
            stats[C.fy(fy)] = [dict(value=usd2(J[fy]['opening']), label='in the fund on 1 July'),
                               dict(value=usd2(J[fy]['received']), label='taken in'),
                               dict(value=usd2(J[fy]['spent']), label='paid out'),
                               dict(value=usd2(J[fy]['closing']), label='in the fund at the close')]
        else:
            gh = {h['fy']: h for h in P['gift']['history']}
            st = [dict(value=usd2(tin), label='taken in'), dict(value=usd2(tout), label='paid out'),
                  dict(value=C.num(len(ys)), label='postings in the journal')]
            if fy in gh:
                st.append(dict(value=usd2(gh[fy]['closing']),
                               label='balance at 30 June, annual town report'))
            else:
                cur = P['gift']['current']
                st.append(dict(value=usd2(cur['closing']), label='balance at 31 March 2026, '
                                                                 'special-revenue report'))
            stats[C.fy(fy)] = st
    srcs = [SRC_JOURNAL(), docs('town-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx',
                                'Town of Lunenburg — Town Accountant (MUNIS), FY26 special-revenue '
                                'report, 31 March 2026')]
    related = [dict(label='Park revolving fund, the story', href='/boards/parks-commission/reports/park-revolving-fund'),
               dict(label='Year-over-year changes', href=TP_PATH('parks-year-changes')),
               dict(label='Programme spending', href=TP_PATH('parks-programmes'))]
    if code == '1523':
        related = [dict(label='Smaller parks funds', href=TP_PATH('other-parks-funds'))]
    related += [dict(label=ITEMS[s]['name'], href=path_of(s)) for s in ITEMS if s != slug]
    about = {
        '1500': 'Programme, field and beach fees, kept in a revolving fund the department spends on '
                'the parks that raise them, outside the Town Meeting vote.',
        '1523': 'Gifts given to the parks. One gift in four years of the journal.',
    }[code]
    across = dict(label='Every year, account by account', columns=[C.fy(y) for y in years], rows=[
        dict(name=x['name'], side=x['side'],
             cells=[acc_years[C.fy(fy)]['rows'][i]['t']['in' if x['side'] == 'in' else 'out'] for fy in years])
        for i, x in enumerate(acc_years[C.fy(years[-1])]['rows'])],
        note='Money in for an income account, money out for a spending account.')
    return dict(
        across=across,
        slug=slug, path=path_of(slug), code=code, name=it['name'],
        kicker='Fund %s · special revenue · %s' % (code, 'revolving' if code == '1500' else 'gift'),
        owner=PARKS_BOARD, about=about,
        years=[C.fy(y) for y in years], spans={C.fy(y): span(y) for y in years},
        as_of='The Town’s MUNIS journal for this fund, %s, to the FY2026 close.'
              % 'July 2022 onward',
        stats=stats,
        accounts=dict(columns=cols, years=acc_years),
        postings=dict(kinds=[dict(id=k, label=l, means=m) for k, l, m in L.KINDS],
                      shown=['in', 'out'], years=post_years,
                      masked='A payer who is a private person paying a fee is masked.'),
        postings_none=None,
        read=READ_FUND, related=related, sources=srcs,
        generated_by='scripts/build_parks_ledger.py')


GF_LABEL = dict(original='Voted', transfers='Transfers', revised='Budget', expended='Spent',
                encumbered='Owed at the close', available='Left')
GF_MEANS = dict(original='what Town Meeting voted', transfers='moved in or out during the year',
                revised='voted plus transfers', expended='paid by the close',
                encumbered='ordered and not yet paid', available='budget less spent and owed')


def line_item(slug):
    it = ITEMS[slug]
    G = L.dept650()
    years = sorted(G)
    acc_years, stats = {}, {}
    for fy in years:
        rows_ = []
        for x in sorted(G[fy], key=lambda x: x['object']):
            zero = all(abs(x[c]) < 0.005 for c in L.GF_COLS)
            rows_.append(dict(key=x['account'], code=x['object'], name=x['name'].title(),
                              side='out', zero=zero,
                              t={c: usd2(x[c]) for c in L.GF_COLS}, n={c: x[c] for c in L.GF_COLS}))
        tot = {c: round(sum(x[c] for x in G[fy]), 2) for c in L.GF_COLS}
        acc_years[C.fy(fy)] = dict(rows=rows_, total=dict(name='Department 650',
                                                         t={c: usd2(tot[c]) for c in L.GF_COLS}))
        stats[C.fy(fy)] = [dict(value=usd2(tot['original']), label='voted by Town Meeting'),
                           dict(value=usd2(tot['revised']), label='budget after transfers'),
                           dict(value=usd2(tot['expended'] + tot['encumbered']),
                                label='spent, counting what was owed'),
                           dict(value=usd2(tot['available']), label='left at the close')]
    GS = gf_spent()
    objs = sorted({o for fy in L.YEARS for o in GS[fy]})
    across = dict(label='Every year, account by account', columns=[C.fy(y) for y in L.YEARS], rows=[
        dict(name=GF_NAME[o], side='out', cells=[usd2(GS[fy].get(o, 0)) for fy in L.YEARS]) for o in objs],
        note='Spent. FY2023 and FY2024 from the Finance Committee’s workbook, assembled by hand from '
             'MUNIS exports; FY2025 and FY2026 from MUNIS at the close, counting what was still owed.')
    P = load('parks.json')
    for fy in years:
        c = P['closed'][str(fy)]
        if abs(c['revised'] - sum(x['revised'] for x in G[fy])) > 0.005:
            fail('department 650 FY%d disagrees with parks.json' % fy)
    return dict(
        across=across,
        slug=slug, path=path_of(slug), code='650', name=it['name'],
        kicker='General fund · department 650 · voted by Town Meeting',
        owner=PARKS_BOARD,
        about='What Town Meeting votes the Parks department each year from the general fund, mostly '
              'taxes, account by account.',
        years=[C.fy(y) for y in years], spans={C.fy(y): span(y) for y in years},
        as_of='The Town’s general fund budget report at the close (period 13), unaudited.',
        stats=stats,
        accounts=dict(columns=[dict(id=c, label=GF_LABEL[c], means=GF_MEANS[c]) for c in L.GF_COLS],
                      years=acc_years),
        postings=None,
        postings_none='The report at the close prints each account’s totals, not the payments behind '
                      'them, so this page stops at the account. The FY2024 Parks report that does list '
                      'payments is held as a scanned image and is not yet read.',
        gaps=[dict(label='Which payments make up these accounts', href='/what-we-cannot-answer')],
        read=[dict(h='One row is one account',
                   p='Salaries, purchase of service and department expenses, as the Town numbers them. '
                     'Voted plus transfers is the budget; the budget less what was spent and what was '
                     'still owed is what was left.'),
              dict(h='This is not everything the parks cost',
                   p='Fees in the Park Revolving Fund pay for programmes and repairs beside this '
                     'budget, and other departments pay for some grounds work.')],
        related=[dict(label='Parks budget', href=TP_PATH('parks-budget')),
                 dict(label='Parks spending', href=TP_PATH('parks-spending'))]
        + [dict(label=ITEMS[s]['name'], href=path_of(s)) for s in ITEMS if s != slug],
        sources=[SRC_P13(),
                 docs('town-ledgers/expenses/glytdbud-expense-fy2024-p13-gf-parks.pdf',
                      'Town of Lunenburg — Town Accountant (MUNIS), FY2024 Parks report with '
                      'payments, image only')],
        generated_by='scripts/build_parks_ledger.py')


def TP_PATH(tid):
    import topics as REG
    return REG.path(tid)


# ======================================================================== the topic pages
FYS = tuple(C.fy(y) for y in L.YEARS)


def conc(*a, **k):
    """TP.conclusion, with the four fiscal years declared as literals in what it means."""
    k['so_allow'] = tuple(k.get('so_allow', ())) + FYS
    return TP.conclusion(*a, **k)

GF_NAME = {'511000': 'Park supervisor salary', '512100': 'Town beach salaries',
           '512107': 'Salaries programming', '531006': 'Purchase of service',
           '531043': 'Department expenses'}


def gf_spent():
    """{fy: {object: dollars spent}} for department 650, by the Town's accounts. FY2023 and FY2024
    from the Finance Committee's workbook (assembled from MUNIS exports: STATED, rule 13a);
    FY2025 and FY2026 from MUNIS at the close, expended plus still owed (evidence)."""
    import csv
    out = {fy: defaultdict(float) for fy in L.YEARS}
    for r in csv.DictReader(open(os.path.join(ROOT, 'sources', 'data', 'gl-history.csv'), encoding='utf-8')):
        if r['sheet'] == 'general_fund' and r['department_code'] == '650' and r['fiscal_year'] in ('2023', '2024'):
            if r['actual_is_partial'] == 'true':
                fail('the workbook’s FY%s Parks actual is partial' % r['fiscal_year'])
            out[int(r['fiscal_year'])][r['object']] += float(r['actual'] or 0)
    for fy, xs in L.dept650().items():
        for x in xs:
            out[fy][x['object']] += x['expended'] + x['encumbered']
    for fy in L.YEARS:
        for o in out[fy]:
            if abs(out[fy][o]) > 0.005 and o not in GF_NAME:
                fail('department 650 spent from an account this page does not name: %s' % o)
    return {fy: {o: round(v, 2) for o, v in out[fy].items() if abs(v) > 0.005} for fy in L.YEARS}


def year_changes(src):
    """MONEY IN AND OUT, by the Town's own accounts. TJ, 19 November 2026: "where they get their
    money from in categories that are clear ... without us making up those categories ... the ins
    and the outs the same way we did with the school ... compare over time". Every row here is an
    account the Town named; the one grouping that is ours (a deposit's sales month) is labelled."""
    P = load('parks.json')
    J = {y['fy']: y for y in P['journal']['years']}
    U = lambda v: figure(v, C.usd(v))
    U2 = lambda v: figure(v, usd2(v))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    f, con = LD.fact, conc
    grid = L.month_grid()
    R = L.rows()
    GF = gf_spent()
    yrs = list(L.YEARS)
    X = [C.fy(y) for y in yrs]

    # ---------------- money in: where the parks' money came from, by account
    def acct_in(fund, desc, fy):
        return round(sum(L.reader_amount(r) for r in R if r['fund'] == fund and r['side'] == 'revenue'
                         and r['posts_to'] == 'actual' and r['account_description'] == desc
                         and int(r['fiscal_year']) == fy), 2)
    IN = [('General fund, mostly taxes', {fy: round(sum(GF[fy].values()), 2) for fy in yrs},
           'department 650, what it spent'),
          ('Program fees', {fy: acct_in('1500', 'PARK PROGRAM FEES', fy) for fy in yrs}, 'fund 1500'),
          ('Beach fees', {fy: acct_in('1500', 'BEACH FEES', fy) for fy in yrs}, 'fund 1500'),
          ('Field fees', {fy: acct_in('1500', 'PARK FIELD FEES', fy) for fy in yrs}, 'fund 1500'),
          ('Investment income', {fy: acct_in('1500', 'INVESTMENT INCOME', fy) for fy in yrs}, 'fund 1500'),
          ('Gifts', {fy: acct_in('1523', 'CONTRIBUTIONS AND DONATIONS', fy) for fy in yrs}, 'fund 1523')]
    for fy in yrs:
        if abs(sum(v[fy] for n, v, _ in IN[1:5]) - J[fy]['received']) > 0.005:
            fail('FY%d: fund 1500’s accounts do not sum to what it took in' % fy)
    fees = {fy: round(sum(v[fy] for n, v, _ in IN[1:4]), 2) for fy in yrs}
    my = {fy: round(sum(L.reader_amount(r) for r in R if L.is_myrec(r) and int(r['fiscal_year']) == fy), 2)
          for fy in yrs}
    drop = round(fees[2025] - fees[2026], 2)
    my_drop = round(my[2025] - my[2026], 2)
    other_rise = round(my_drop - drop, 2)       # other fees moved the other way
    if other_rise <= 0:
        fail('other fee receipts no longer rose in FY2026; rewrite the finding')
    if my_drop < 0.9 * drop:
        fail('registration deposits are no longer almost all of the FY2026 fee drop')
    gf = IN[0][1]

    # ---------------- money out: every account that paid for the parks
    OUT = []
    for o in sorted({o for fy in yrs for o in GF[fy]}):
        OUT.append(('%s, general fund' % GF_NAME[o], {fy: GF[fy].get(o, 0.0) for fy in yrs}, 0))
    for desc in ('PURCHASE OF SERVICE', 'SUPPLIES', 'TOWN BEACH SALARIES'):
        v = {fy: round(sum(float(r['amount']) for r in L.payments() if r['account_description'] == desc
                           and int(r['fiscal_year']) == fy), 2) for fy in yrs}
        OUT.append(('%s, fee fund' % desc.capitalize(), v, 2))
    for fy in yrs:
        if abs(sum(v[fy] for _, v, c in OUT if c == 2) - J[fy]['spent']) > 0.005:
            fail('FY%d: fund 1500’s accounts do not sum to what it paid out' % fy)
    out_tot = {fy: round(sum(v[fy] for _, v, _c in OUT), 2) for fy in yrs}
    in_tot = {fy: round(sum(v[fy] for _, v, _u in IN), 2) for fy in yrs}

    in_chart = TP.series(
        'Where the parks money came from', X,
        [TP.track('General fund, mostly taxes', [gf[fy] for fy in yrs], 'published', 'bar')]
        + [TP.track(n, [v[fy] for fy in yrs], 'published', 'bar') for n, v, _ in IN[1:4]],
        '$', kind='bar', stacked=True, totals=True,
        note='General fund: what department 650 spent, FY2023 and FY2024 from the Finance Committee '
             'workbook. Fees: fund 1500, net of refunds. Interest and gifts: the table.',
        note_allow=('650', '1500', 'FY2023', 'FY2024'))
    out_chart = TP.series(
        'Where it went, account by account', X,
        [TP.track(n, [v[fy] for fy in yrs], 'published', 'bar', colour=c) for n, v, c in OUT],
        '$', kind='bar', multiples=True,
        note='The Town’s own accounts: the first five panels are the general fund, the last three the '
             'fee fund. FY2024 includes cost moved out by journal entry.', note_allow=('FY2024',))

    # ---------------- what changed in money in: deposits by the sales month they name
    empty = {fy: [L.MON[i] for i, c in enumerate(grid[fy]) if not any(
        L.myrec_kind(r) == 'deposit' and not r.get('_correction') for r in c['lines'])] for fy in yrs}
    if empty[2026] != ['Sep', 'Oct', 'Nov', 'Mar', 'Apr'] or empty[2025] or empty[2024] \
            or empty[2023] != ['Sep', 'Oct', 'Nov', 'Feb']:
        fail('the months with no deposit changed: %s -- rewrite the page' % empty)
    same25 = round(sum(grid[2025][L.MON.index(m)]['deposits'] for m in empty[2026]), 2)
    figs, lits, gy = set(), set(), []
    for fy in yrs:
        cells = []
        for i, c in enumerate(grid[fy]):
            lines = []
            for r in c['lines']:
                k = 'correction' if r.get('_correction') else L.myrec_kind(r)
                lines.append(dict(d=day(r['effective_date']), what=r['description'],
                                  acct=short_acct(r['account_description']), k=k,
                                  amt=usd2(L.reader_amount(r)), posted=C.fy(int(r['fiscal_year']))))
                figs.update([lines[-1]['d'], lines[-1]['amt'], lines[-1]['posted']])
                lits.update([r['description'], lines[-1]['acct']])
            cells.append(dict(m=L.MON[i], net=c['net'], t=usd2(c['net']) if lines else '',
                              ts=C.usd(c['net']) if lines else '',
                              has=any(x['k'] == 'deposit' for x in lines), lines=lines))
            if lines:
                figs.update([usd2(c['net']), C.usd(c['net'])])
        tot = round(sum(c['net'] for c in grid[fy]), 2)
        te = '%s of 12 months with no deposit' % C.num(len(empty[fy]))
        gy.append(dict(fy=C.fy(fy), t=usd2(tot), t_empty=te, cells=cells))
        figs.update([C.fy(fy), usd2(tot), te])
    months_block = TB.custom(
        'park-sales-months', 'Registration deposits by month of sale', dict(
            years=gy, max=max(c['net'] for y in gy for c in y['cells']), months=L.MON,
            text=dict(pick='Tap a month for every deposit, refund and card charge that names it.',
                      none='No deposit names this month.', posted='posted in',
                      deposit='Deposit', refund='Refund', charge='Card charges',
                      correction='Correction, same day',
                      ours='Each line is placed by the month its memo names, whichever year it '
                           'posted in. That placing is our reading of the memo.')),
        place='body', figures=sorted(figs), allow=sorted(lits | {'12'}),
        basis=('record', 'The fund’s MUNIS journal, to the FY2026 close'),
        so=('FY2026 has no deposit for five months of sales; FY2024 and FY2025 had one every month.',
            None, ('FY2026', 'FY2024', 'FY2025')))

    # ---------------- what changed in money out: who the fee fund paid
    pay = defaultdict(lambda: defaultdict(float))
    for r in L.payments():
        pay[r['vendor'] or 'Journal entry'][int(r['fiscal_year'])] += float(r['amount'])
    payees = sorted(pay, key=lambda p: -max(abs(pay[p][fy]) for fy in yrs))
    KEEP = 24                                   # a table holds 30 rows; the rest are summed
    rest = defaultdict(float)
    for p in payees[KEEP:]:
        for fy in yrs:
            rest[fy] += pay[p][fy]
    n_rest = len(payees) - KEEP
    payees = payees[:KEEP]
    cols = X + ['FY2025 to FY2026']
    ycells = lambda v: [C.usd(v.get(fy, 0)) for fy in yrs] + [C.usd(v.get(2026, 0) - v.get(2025, 0))]
    table = dict(caption='Money in and out, account by account', views=[
        dict(key='in', label='Money in', total_col=None, kinds=['ledger'] * 5, columns=cols,
             rows=[dict(label=n, cells=ycells(v)) for n, v, _ in IN]
             + [dict(label='All money in', cells=ycells(in_tot))],
             note='The Town’s account names. General fund: what department 650 spent.'),
        dict(key='out', label='Money out', total_col=None, kinds=['ledger'] * 5, columns=cols,
             rows=[dict(label=n, cells=ycells(v)) for n, v, _ in OUT]
             + [dict(label='All money out', cells=ycells(out_tot))],
             note='General fund FY2023 and FY2024 from the Finance Committee workbook; FY2025 and '
                  'FY2026 from MUNIS at the close, counting what was still owed.'),
        dict(key='payees', label='Fee fund, by payee', total_col=None, kinds=['ledger'] * 5,
             columns=cols, rows=[dict(label=p.title() if p.isupper() else p, cells=ycells(pay[p]))
                                 for p in payees]
             + ([dict(label='%s smaller payees' % C.num(n_rest), cells=ycells(rest))] if n_rest > 0 else []),
             note='Payees as the journal prints them, cut at twenty characters. Every payment, with '
                  'its memo, is on the fund’s own page.')])
    out_chg = {n: round(v[2026] - v[2025], 2) for n, v, _ in OUT}
    pos_gf = out_chg['Purchase of service, general fund']
    pos_fee = out_chg['Purchase of service, fee fund']
    if not (pos_gf > 15000 and pos_fee < -15000):
        fail('purchase of service no longer moved between the funds in FY2026; rewrite')
    facts = [
        f('gf26', U2(gf[2026]), 'from the general fund, FY2026', 'published', allow=('FY2026',)),
        f('fees25', U2(fees[2025]), 'fees taken in, FY2025', 'published', allow=('FY2025',)),
        f('fees26', U2(fees[2026]), 'fees taken in, FY2026', 'published', allow=('FY2026',)),
        f('mydrop', U2(my_drop), 'fall in registration income, FY2025 to FY2026', 'published',
          allow=('FY2025', 'FY2026')),
        f('empty26', figure(len(empty[2026]), '%s of 12' % C.num(len(empty[2026])), 'months'),
          'sales months with no deposit, FY2026', 'published', allow=('FY2026',)),
        f('empty23', figure(len(empty[2023]), '%s of 12' % C.num(len(empty[2023])), 'months'),
          'sales months with no deposit, FY2023', 'published', allow=('FY2023',)),
        f('same25', U2(same25), 'deposited for those five months, FY2025', 'published', allow=('FY2025',)),
        f('out25', U2(out_tot[2025]), 'money out, every account, FY2025', 'published', allow=('FY2025',)),
        f('out26', U2(out_tot[2026]), 'money out, every account, FY2026', 'published', allow=('FY2026',)),
        f('posgf', U2(pos_gf), 'more on purchase of service, general fund, FY2026', 'published',
          allow=('FY2026',)),
        f('posfee', U2(-pos_fee), 'less on purchase of service, fee fund, FY2026', 'published',
          allow=('FY2026',)),
        f('sales26', None, 'FY2026 registration sales, by month', 'gap', allow=('FY2026',),
          closes='MyRec’s FY2026 sales report, or the fund’s FY2027 journal'),
    ]
    conclusions = [
        con('Fees fell %s in FY2026: registration income fell %s and other fees rose %s.'
            % (C.usd(drop), C.usd(my_drop), C.usd(other_rise)),
            ['fees25', 'fees26', 'mydrop'], {'a': U(drop), 'b': U(my_drop), 'c': U(other_rise)},
            allow=('FY2026',),
            so='Program fees fell most, but May and June 2026 deposits went to beach fees, so read '
               'the total, not the split.', so_allow=('2026',)),
        con('No FY2026 deposit names September, October, November, March or April sales.',
            ['empty26', 'same25', 'sales26'], allow=('FY2026',),
            notes=[step('Sales not made, and sales deposited after 30 June 2026 or elsewhere, fit '
                        'the same journal; nothing held tells them apart.', 'gap',
                        allow=('FY2026', '30', '2026', 'FY2027'),
                        closes='MyRec’s FY2026 sales report, or the fund’s FY2027 journal')],
            so='The same five months brought in %s the year before.' % C.usd(same25),
            so_figures={'a': U(same25)}),
        con('FY2023 also lacked deposits for %s months of sales; FY2024 and FY2025 had all twelve.'
            % C.num(len(empty[2023])), ['empty23'], {'n': N(len(empty[2023]), 'months')},
            allow=('FY2023', 'FY2024', 'FY2025'),
            so='An empty stretch has happened before, so FY2026 alone does not show a trend.'),
        con('Purchase of service rose %s in the general fund in FY2026 and fell %s in the fee fund.'
            % (C.usd(pos_gf), C.usd(-pos_fee)), ['posgf', 'posfee', 'out26'],
            {'a': U(pos_gf), 'b': U(-pos_fee)}, allow=('FY2026',),
            notes=[step('The same services paid from a different fund, and two unrelated changes, '
                        'fit the totals; the general fund report prints no payments to tell.', 'gap',
                        allow=('FY2026', '650'),
                        closes='the general fund’s FY2026 payments for department 650')],
            so='Spending moved between the two funds’ accounts more than it changed in total.'),
    ]
    page = TP.page(
        'parks-year-changes',
        'Parks fees fell %s in FY2026, all of it in registration income, which fell %s.'
        % (C.usd(drop), C.usd(my_drop)),
        facts, conclusions, chart=in_chart, also=[out_chart], table=table,
        sources=[src['journal'], src['p13'], src['gl']],
        finding_figures={'a': U(drop), 'b': U(my_drop)}, finding_allow=('FY2026',),
        flow=['finding', TP.cite(('chart', 0), 0, 1, 2), TP.cite(('chart', 1), 0, 1, 2),
              TP.cite('ladder', 0, 1, 2), TP.cite(months_block, 0), 'related',
              TP.cite(('table', 0), 0, 1, 2), 'sources'])
    return page, dict(drop=drop, my_drop=my_drop, empty=empty)


def programmes(src):
    P = load('parks.json')
    J = {y['fy']: y for y in P['journal']['years']}
    U = lambda v: figure(v, C.usd(v))
    U2 = lambda v: figure(v, usd2(v))
    f, con = LD.fact, conc
    SP = L.spend_by_programme()
    CLASS = [('Programmes', ('Soccer', 'STEM and science', 'Multisports', 'Art', 'Yoga',
                             'Junior zookeepers')),
             ('Events', ('Spring fair', 'Movie nights and events')),
             ('Beach', ('Beach staff and swim', 'Beach building')),
             ('Repairs and grounds', ('Repairs and grounds',)),
             ('Running the department', ('Registration system', 'Supplies', 'Moved by journal entry'))]
    if sorted(p for _, ps in CLASS for p in ps) != sorted(L.PROGRAMME_NAMES):
        fail('the chart classes do not cover every programme group')
    cls = {name: {fy: round(sum(SP[fy].get(p, 0) for p in ps), 2) for fy in L.YEARS} for name, ps in CLASS}
    chart = TP.series(
        'What the fee fund paid for', [C.fy(y) for y in L.YEARS],
        [TP.track(name, [cls[name][fy] for fy in L.YEARS], 'estimate', 'bar') for name, _ in CLASS],
        '$', kind='bar', stacked=True, totals=True,
        note='Fund 1500’s payments, grouped by what each memo and payee name. The grouping is ours; '
             'a journal entry in FY2024 moved cost out, below zero.', note_allow=('1500', 'FY2024'))
    prog = cls['Programmes']
    # FY2025: sold through MyRec against paid out, by programme
    sales = defaultdict(float)
    for g, _, t in L.myrec_sales():
        sales[g] += t
    pairs = []
    for g in ('Soccer', 'STEM and science', 'Multisports', 'Art', 'Yoga', 'Junior zookeepers',
              'Beach staff and swim'):
        pairs.append((g, round(sales.get(g, 0), 2), SP[2025].get(g, 0)))
    pairs.append(('Other programmes', round(sales.get('Other programmes', 0), 2), None))
    sold_tot = round(sum(sales.values()), 2)
    t2 = dict(caption='FY2025: sold and paid, by programme', views=[dict(
        key='fy25', label='FY2025', total_col=None, kinds=['ledger', 'ledger', 'ledger'],
        columns=['Sold through MyRec', 'Paid out from fund 1500', 'Sold less paid'],
        rows=[dict(label=g, cells=[C.usd(s), C.usd(p) if p is not None else '—',
                                   C.usd(s - p) if p is not None else '—']) for g, s, p in pairs],
        note='MyRec’s sales report against the fund’s payments, matched by programme name: our '
             'reading. Staff time paid from the general fund is in neither.')])
    t1 = dict(caption='Every programme group, four years', views=[dict(
        key='all', label='Paid out', total_col=None, kinds=['ledger'] * 4,
        columns=[C.fy(y) for y in L.YEARS],
        rows=[dict(label=p, cells=[C.usd(SP[fy].get(p, 0)) for fy in L.YEARS])
              for p in L.PROGRAMME_NAMES if any(SP[fy].get(p) for fy in L.YEARS)]
        + [dict(label='All payments', cells=[C.usd(J[fy]['spent']) for fy in L.YEARS])],
        note='Each payment is on the fund’s own page, with its memo and payee.')])
    how = TB.explain('How payments were grouped', [
        ('The Town’s accounts do not name programmes: almost every fee-fund payment is in one '
         'account, Purchase of Service. The programme here is our reading of the memo and payee the '
         'Town printed: SOCCER PROGRAMS paid to 3 STEP SPORTS LLC is soccer.', None, ('3 STEP SPORTS LLC',)),
        ('Income by programme exists for FY2025 only, in the registration system’s sales report. '
         'Other years record monthly deposits, not programmes.', None, ('FY2025',))],
        place='body', tone='define')
    stem = SP[2025].get('STEM and science', 0)
    stem_sold = sales.get('STEM and science', 0)
    facts = [
        f('prog25', U2(prog[2025]), 'paid for programmes, FY2025', 'estimate', allow=('FY2025',)),
        f('prog26', U2(prog[2026]), 'paid for programmes, FY2026', 'estimate', allow=('FY2026',)),
        f('stem25', U2(stem), 'paid for STEM, FY2025', 'estimate', allow=('FY2025',)),
        f('stemsold', U2(stem_sold), 'STEM sold through MyRec, FY2025', 'published', allow=('FY2025',)),
        f('beach23', U2(SP[2023]['Beach building']), 'the beach building renovation, FY2023',
          'published', allow=('FY2023',)),
        f('sold25', U2(sold_tot), 'everything MyRec sold, FY2025', 'published', allow=('FY2025',)),
        f('income', None, 'income by programme, FY2023, FY2024, FY2026', 'gap',
          allow=('FY2023', 'FY2024', 'FY2026'),
          closes='MyRec’s programme sales reports for those years'),
    ]
    conclusions = [
        con('The fund paid %s for programmes in FY2025 and %s in FY2026, on our grouping.'
            % (C.usd(prog[2025]), C.usd(prog[2026])), ['prog25', 'prog26'],
            {'a': U(prog[2025]), 'b': U(prog[2026])}, allow=('FY2025', 'FY2026'),
            so='Programme payments fell by more than half in a year when deposits halved too.'),
        con('STEM sold %s through MyRec in FY2025 and the fund paid its provider %s.'
            % (C.usd(stem_sold), C.usd(stem)), ['stem25', 'stemsold'],
            {'a': U(stem_sold), 'b': U(stem)}, allow=('FY2025',),
            so='The largest programme took in more than it was paid for, on these two records.'),
        con('The largest single payment in four years was %s to renovate the beach building.'
            % C.usd(SP[2023]['Beach building']), ['beach23'], {'a': U(SP[2023]['Beach building'])},
            so='Fee money paid for a building, not only for programmes.'),
    ]
    page = TP.page(
        'parks-programmes',
        'The fee fund paid %s for programmes in FY2025 and %s in FY2026.' % (C.usd(prog[2025]), C.usd(prog[2026])),
        facts, conclusions, chart=chart, table=t1, tables=[t2], sources=[src['journal'], src['myrec']],
        finding_figures={'a': U(prog[2025]), 'b': U(prog[2026])}, finding_allow=('FY2025', 'FY2026'),
        flow=['finding', TP.cite(('chart', 0), 0), TP.cite(('table', 1), 0, 1), TP.cite('ladder', 0, 1),
              TP.cite(how, 0, 1), 'related', TP.cite(('table', 0), 0), 'sources'])
    return page


# ======================================================================== write
def outputs():
    src = dict(journal=SRC_JOURNAL(), myrec=SRC_MYREC(), p13=SRC_P13(),
               gl=docs('budget-workbooks/finance-committee/fy26-budget/general-fund-budget-vs-actuals-history.xlsx',
                       'Lunenburg Finance Committee — general fund budget against actuals, FY2010–FY2025, '
                       'assembled from MUNIS exports'))
    out = {}
    items = {s: (fund_item(s) if ITEMS[s]['base'] == '/town-funds/' else line_item(s)) for s in ITEMS}
    for s, p in items.items():
        out[os.path.join(FUND_DIR, '%s.json' % s)] = p
    out[os.path.join(FUND_DIR, 'index.json')] = dict(
        items=[dict(slug=s, path=path_of(s), code=ITEMS[s]['code'], name=ITEMS[s]['name'],
                    measure=ITEMS[s]['measure']) for s in ITEMS],
        generated_by='scripts/build_parks_ledger.py')
    yc, _ = year_changes(src)
    out[os.path.join(TOPIC_DIR, 'parks-year-changes.json')] = yc
    out[os.path.join(TOPIC_DIR, 'parks-programmes.json')] = programmes(src)
    return {p: json.dumps(v, indent=1, ensure_ascii=False, sort_keys=True) + '\n' for p, v in out.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    outs = outputs()
    if a.check:
        stale = [os.path.relpath(p, ROOT) for p, t in outs.items()
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != t]
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('parks ledger: %d outputs current' % len(outs))
        return 0
    for p, t in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(t)
        os.replace(tmp, p)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
