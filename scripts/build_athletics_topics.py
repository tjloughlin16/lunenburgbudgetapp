#!/usr/bin/env python3
"""Athletics, split into topic pages: eight pages and the athletics hub.

    python3 scripts/build_athletics_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_athletics_topics.py --check   # fail if any output would change

WHY THIS EXISTS. scripts/topics.py has the model: one question per page, under five minutes,
facts first, two to four conclusions resting on them. The athletics shelf lists eight pages
that this script owns; the four athletic-transportation pages on the same shelf are written
by build_transportation.py and are not touched here.

IT COMPUTES NOTHING NEW THAT IT CAN READ INSTEAD. Every figure comes from a payload or a
dataset already in the repository, and the script refuses to write if two of them stop
agreeing where they are supposed to:

  sources/data/munis-school-ytd.csv     the town's MUNIS year-end (period 13) budget reports,
                                        school general fund and school special funds,
                                        FY2023-FY2026. A printout of the books: PROOF (13a).
  fy28/public/data/spending-what-comes-in.json
                                        the same ledger, already summed by year for function
                                        3510 and fund 1301 -- asserted equal to our own sums.
  fy28/public/data/athletics.json       build_athletics_charts.py: the fund's cashbook by year
                                        (fund_1301_cash_journal), the district's by-sport
                                        workbook (HAND-BUILT), participation, fee categories,
                                        the verified meeting quotes.
  fy28/public/data/model.json           athletics.costSources: the three district per-team
                                        cost columns for FY2024, side by side (HAND-BUILT).
  fy28/public/data/what-families-pay.json
                                        the fee register and the vote that set the FY2026 fees.

RULE 13a GOVERNS. The three per-team cost columns are sheets people assembled; they disagree
by a multiple and are shown as separate facts, never averaged, never reconciled into one. A
figure from the MUNIS reports outranks them and the labels say which is which.

RULE 1. A budget is compared only with a budget and spending only with spending. The one place
budget and spending meet is the underspend page, where `left` is the ledger's own column
(revised budget less spent less still owed), not a difference we computed across documents.

RULE 11. A town budget line is the town's net share, never what athletics costs.
"""
import argparse
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
from brief import step  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'sources', 'data')
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT_DIR = os.path.join(PUB, 'topics')
MUNIS = os.path.join(D, 'munis-school-ytd.csv')
MANIFEST = os.path.join(D, 'archive-manifest.csv')
MINUTES = os.path.join(ROOT, 'sources', 'meetings', 'text')
CHART_SOURCE = '/data/spending-what-comes-in.json'

MINE = [t for t, (_, home, gen) in REG.TOPICS.items()
        if home == 'athletics' and gen == 'build_athletics_topics.py']


def fail(msg):
    raise SystemExit('build_athletics_topics: ' + msg)


def load(name):
    return json.load(open(os.path.join(PUB, name), encoding='utf-8'))


def usd2(x):
    x = float(x)
    return ('-$' if x < 0 else '$') + format(abs(x), ',.2f')


def pct1(a, b):
    return round(100.0 * a / b, 1)


# --------------------------------------------------------------------- the ledger

def ledger():
    """Function 3510 (athletics) from the period-13 reports: the general fund (0100) and the
    athletics revolving fund (1301), by year, account by account."""
    rows = [r for r in csv.DictReader(open(MUNIS, encoding='utf-8'))
            if r['period'] == '13' and r['account'].split('-')[3] == '3510'
            and r['fund'] in ('0100', '1301')]
    out = {}
    for r in rows:
        fy, pot = int(r['fiscal_year']), 'town' if r['fund'] == '0100' else 'fund'
        d = out.setdefault(fy, {}).setdefault(pot, dict(rows=[], original=0.0, revised=0.0,
                                                         spent=0.0, owed=0.0, left=0.0))
        d['rows'].append(r)
        for k, col in (('original', 'original_approp'), ('revised', 'revised_budget'),
                       ('spent', 'ytd_expended'), ('owed', 'encumbrances'),
                       ('left', 'available_budget')):
            d[k] += float(r[col] or 0)
    if sorted(out) != [2023, 2024, 2025, 2026]:
        fail('the period-13 reports no longer hold FY2023-FY2026 for function 3510: %s'
             % sorted(out))
    return out


def said_from(block, i=0, kind='minutes'):
    """One quotation from a block athletics.json already verified against the minutes."""
    m = re.search(r'(\d{4}-\d{2}-\d{2})', block['url'])
    date = m.group(1)
    q = block['quotes'][i]['text']
    return dict(quote=q, board=block['board'], date=date, href=block['url'],
                label='%s %s, %s' % (block['board'], kind, date))


def said_file(rel, quote, board, kind='minutes'):
    """A quotation we assert here, verbatim, against our copy of the minutes."""
    path = os.path.join(MINUTES, rel)
    text = ' '.join(open(path, encoding='utf-8').read().split())
    if ' '.join(quote.split()) not in text:
        fail('quote is not verbatim in %s: %r' % (rel, quote))
    date = re.search(r'(\d{4}-\d{2}-\d{2})', rel).group(1)
    return dict(quote=quote, board=board, date=date,
                href='/docs/minutes/text/' + rel, label='%s %s, %s' % (board, kind, date))


def sources():
    man = {r['key']: r for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    spec = {
        'gf26': ('town-ledgers/expenses/glytdbud-expense-fy2026-p13-gf-school.xlsx',
                 'Town of Lunenburg — Town Accountant (MUNIS)'),
        'gf25': ('town-ledgers/expenses/glytdbud-expense-fy2025-p13-gf-school.xlsx',
                 'Town of Lunenburg — Town Accountant (MUNIS)'),
        'gf24': ('town-ledgers/expenses/glytdbud-expense-fy2024-p13-gf-school.xlsx',
                 'Town of Lunenburg — Town Accountant (MUNIS)'),
        'sp26': ('town-ledgers/expenses/glytdbud-expense-fy2026-p13-special-school.xlsx',
                 'Town of Lunenburg — Town Accountant (MUNIS)'),
        'sp25': ('town-ledgers/expenses/glytdbud-expense-fy2025-p13-special-school.xlsx',
                 'Town of Lunenburg — Town Accountant (MUNIS)'),
        'sp24': ('town-ledgers/expenses/glytdbud-expense-fy2024-p13-special-school.xlsx',
                 'Town of Lunenburg — Town Accountant (MUNIS)'),
        'cash24': ('town-ledgers/account-details/account-details-fy2024-fund1301.xlsx',
                   'Town of Lunenburg — Town Accountant (MUNIS)'),
        'cash25': ('town-ledgers/account-details/account-details-fy2025-fund1301.xlsx',
                   'Town of Lunenburg — Town Accountant (MUNIS)'),
        'cash26': ('town-ledgers/account-details/account-details-fy2026-fund1301.xlsx',
                   'Town of Lunenburg — Town Accountant (MUNIS)'),
        'workbook': ('town-ledgers/account-details/athletics-by-sport-fy2024-fy2026.xlsx',
                     'Lunenburg Public Schools'),
        'feecounts': ('town-ledgers/account-details/athletic-fee-counts-fy2026.docx',
                      'Lunenburg Public Schools'),
        'bysport': ('district-budget/docs/athletic-program-costs-by-sport.pdf',
                    'Lunenburg Public Schools'),
        'costs1': ('budget-workbooks/finance-committee/fy26-budget/department-presentations/'
                   'lunenburg-public-schools/athletics-costs-1.xlsx', 'Lunenburg Public Schools'),
        'funds26': ('budget-workbooks/school-funds-fy26.xlsx', 'Lunenburg Public Schools'),
        'faq': ('district-budget/docs/lhs-athletics-faq.pdf', 'Lunenburg Public Schools'),
        'fy19': ('district-budget/docs/fy19-proposed-athletics-budget.pdf',
                 'Lunenburg Public Schools'),
    }
    out = {}
    for k, (key, pub) in spec.items():
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        out[k] = dict(label='%s — %s' % (pub, key.split('/')[-1]), href='/docs/' + key)
    ours = {
        'd-munis': ('munis-school-ytd.csv', 'the MUNIS year-end reports, one row an account'),
        'd-cash': ('fund-1301-cash-journal.csv', 'the fund’s cashbook, every posting'),
        'd-sport': ('athletics-by-sport.csv', 'the by-sport workbook, cell by cell'),
        'd-fincom': ('athletics-fincom.csv', 'the second per-sport sheet, cell by cell'),
        'd-fees': ('athletic-fee-schedule.csv', 'every athletic fee, with its source line'),
    }
    for k, (f, what) in ours.items():
        if not os.path.exists(os.path.join(ROOT, 'fy28', 'public', 'docs', 'data', f)):
            fail('/docs/data/%s is not published' % f)
        out[k] = dict(label='Lunenburg Budget Project — %s (%s)' % (f, what),
                      href='/docs/data/' + f)
    return out


# --------------------------------------------------------------------- the pages

def build():
    A = load('athletics.json')
    S = load('spending-what-comes-in.json')['athletics']
    CS = load('model.json')['athletics']['costSources']
    W = load('what-families-pay.json')
    L = ledger()
    src = sources()
    U = lambda v: figure(v, C.usd(v))
    U2 = lambda v: figure(v, usd2(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    f, con = LD.fact, TP.conclusion

    # Our sums of the ledger must equal the published payload's, year by year, or the two
    # pages would disagree about the same report.
    sy = {r['fy']: r for r in S['years']}
    for fy in sorted(L):
        for pot, key in (('town', 'gf_spent'), ('fund', 'fund_spent')):
            if abs(L[fy][pot]['spent'] - sy[fy][key]) > 0.01:
                fail('FY%d %s: ledger sums to %.2f, spending-what-comes-in says %.2f'
                     % (fy, pot, L[fy][pot]['spent'], sy[fy][key]))
    share = {fy: pct1(L[fy]['fund']['spent'], L[fy]['town']['spent'] + L[fy]['fund']['spent'])
             for fy in L}
    for fy in L:
        if abs(share[fy] - sy[fy]['fund_share_pct']) > 0.05:
            fail('FY%d fund share %.1f against the payload’s %.1f'
                 % (fy, share[fy], sy[fy]['fund_share_pct']))
    town = {fy: L[fy]['town'] for fy in L}
    fund = {fy: L[fy]['fund'] for fy in L}
    out = {}

    # ------------------------------------------------ shared facts (the hub reuses these)
    tot = CS['totals']
    if not (tot['deck'] == CS['totalLow'] and tot['workbook'] == CS['totalHigh']):
        fail('the low and high per-team totals are no longer the deck and the workbook')
    agree = CS['agreeing']
    teams = CS['count']
    fx = {}
    # PAID, NOT SPENT. Here `spent` is ytd_expended alone; the transportation pages say
    # spent for paid PLUS still owed. FY2026 is the only year with anything owed ($23,524 on
    # the town side), so its sentences say paid -- one word, one meaning, across the site.
    fx['town26'] = f('town26', U(town[2026]['spent']),
                     'town budget, paid for athletics, %s (ledger)' % C.fy(2026),
                     'published', {'y': F(2026)})
    fx['fund26'] = f('fund26', U(fund[2026]['spent']),
                     'fee fund, paid for athletics, %s (ledger)' % C.fy(2026),
                     'published', {'y': F(2026)})
    fx['deck24'] = f('deck24', U(tot['deck']),
                     '%s teams, %s, the district’s May 2024 deck' % (C.num(teams), C.fy(2024)),
                     'published', {'n': N(teams), 'y': F(2024)}, allow=('May 2024',))
    fx['bysport24'] = f('bysport24', U(tot['costsBySport']),
                        'the same teams, “Costs by Sport” sheet', 'published')
    fx['wb24'] = f('wb24', U(tot['workbook']),
                   'the same teams, district by-sport workbook', 'published')
    fx['agree'] = f('agree', N(agree, 'teams'),
                    'teams with one cost in all three sheets', 'published')
    fx['sport-gap'] = f('sport-gap', None, 'what any one sport costs, on the books', 'gap',
                        closes='the accounts-payable detail behind the fee fund’s warrants, '
                               'coded by sport')
    fac = A['counted']
    fx['facility'] = f('facility', U(fac['facility_total']),
                       'custodians, heat, utilities, grounds, all schools, %s'
                       % C.fy(fac['fy']), 'published', {'y': F(fac['fy'])})
    fx['bldg-gap'] = f('bldg-gap', None, 'athletics’ share of buildings and grounds', 'gap',
                       closes='an allocation by the district of custodial, utility and grounds '
                              'spending to its programmes')
    fx['share24'] = f('share24', P(share[2024]),
                      'fee fund’s share of athletics spending, %s' % C.fy(2024),
                      'published', {'y': F(2024)})
    fx['share25'] = f('share25', P(share[2025]),
                      'the same share, %s' % C.fy(2025), 'published', {'y': F(2025)})
    fx['share26'] = f('share26', P(share[2026]),
                      'the same share, %s' % C.fy(2026), 'published', {'y': F(2026)})
    memo = [e for e in A['memo_entries'] if e['fy'] == 2025]
    memo25 = round(sum(e['amount'] for e in memo), 2)
    flow = {r['fy']: r for r in A['fund_flow']}
    if abs(memo25 - flow[2025]['journals']) > 0.01 or len(memo) != 4:
        fail('the FY2025 expense-adjustment entries no longer sum to the year’s journals')
    fx['memo25'] = f('memo25', U(memo25),
                     'into the fee fund on %s journal entries, %s' % ('four', C.fy(2025)),
                     'published', {'y': F(2025)})

    # ---- Total athletics cost
    t24, f24 = town[2024]['spent'], fund[2024]['spent']
    both24 = round(t24 + f24, 2)
    sheet_hi = tot['workbook']
    if not both24 > sheet_hi:
        fail('the FY2024 ledger, both funds, no longer exceeds every per-team sheet total')
    unmatched = A['compare']['unmatched_total']
    names = sorted(u['item'] for u in A['compare']['unmatched'])
    if names != ['Athletic Director', 'Athletic Insurance', 'Athletic Trainer']:
        fail('the lines the workbook does not carry have changed: %s' % names)
    out['total-athletics-cost'] = TP.page(
        'total-athletics-cost',
        'No document states one total: %s sheets give %s to %s for the same teams in %s.'
        % ('three', C.usd(tot['deck']), C.usd(tot['workbook']), C.fy(2024)),
        [fx['deck24'], fx['bysport24'], fx['wb24'],
         f('town24', U(t24), 'town budget, spent on athletics, %s (ledger)' % C.fy(2024),
           'published', {'y': F(2024)}),
         f('fund24', U(f24), 'fee fund, spent on athletics, %s (ledger)' % C.fy(2024),
           'published', {'y': F(2024)}),
         f('both24', U(both24), 'the two together, %s (our sum)' % C.fy(2024), 'published',
           {'y': F(2024)}),
         fx['town26'], fx['fund26'], fx['facility'], fx['bldg-gap']],
        [con('%s district sheets put the same teams’ %s cost at %s, %s and %s.'
             % ('Three', C.fy(2024), C.usd(tot['deck']), C.usd(tot['costsBySport']),
                C.usd(tot['workbook'])),
             ['deck24', 'bysport24', 'wb24'],
             {'y': F(2024), 'a': U(tot['deck']), 'b': U(tot['costsBySport']),
              'c': U(tot['workbook'])},
             notes=[step('All three were assembled by hand, and no document says which '
                         'question each column answers.', 'gap',
                         closes='a reconciliation by the district of its own per-sport cost '
                                'statements, naming what each column counts')]),
         con('The town’s ledger shows %s spent from both funds in %s, more than any sheet’s '
             'total.' % (C.usd(both24), C.fy(2024)),
             ['town24', 'fund24', 'both24', 'wb24'], {'a': U(both24), 'y': F(2024)},
             notes=[step('Part of the gap may be scope: the workbook carries no athletic '
                         'director, trainer or insurance, %s of the %s budget. Nothing here '
                         'tests how much of the gap that explains.'
                         % (C.usd(unmatched), C.fy(2024)), 'hypothesis',
                         {'u': U(unmatched), 'y': F(2024)})]),
         con('None of these figures includes the buildings, and no published allocation says '
             'what they add.', ['facility', 'bldg-gap'])],
        sources=[src['bysport'], src['costs1'], src['workbook'], src['gf24'], src['sp24'],
                 src['gf26'], src['sp26'], src['d-munis']],
        said=[said_from(A['disclaimer'], 0)],
        finding_figures={'a': U(tot['deck']), 'b': U(tot['workbook']), 'y': F(2024)})

    # ---- Town budget and fee fund
    moved25 = round(town[2025]['revised'] - town[2025]['original'], 2)
    if not moved25 > 0:
        fail('the FY2025 town athletics budget no longer rose during the year')
    hist = {r['fy']: r for r in A['both_sides']}
    for fy in (2014, 2015, 2016, 2017):
        if hist[fy]['revolving_state'] != 'published' or hist[fy]['general_basis'] != 'restated actual':
            fail('FY%d in the FY2019 document is no longer a restated actual on both sides' % fy)
    old = [hist[fy] for fy in (2014, 2015, 2016, 2017)]
    table_pots = dict(caption='Athletics spending by fund, by year', views=[
        dict(key='ledger', label='The town’s ledger', total_col=2, kinds=['ledger'] * 4,
             columns=['Town budget, spent', 'Fee fund, spent', 'The two', 'Fee fund’s share'],
             rows=[dict(label=C.fy(fy), cells=[
                 C.usd(town[fy]['spent']), C.usd(fund[fy]['spent']),
                 C.usd(town[fy]['spent'] + fund[fy]['spent']), C.pct(share[fy])])
                 for fy in sorted(L, reverse=True)],
             note='MUNIS year-end (period 13) reports, function 3510 in the general fund and '
                  'fund 1301. Spent is what the ledger records as expended at the close. The '
                  'fee fund’s FY2025 figure is net of four journal entries marked expense '
                  'adjustments.'),
        dict(key='fy19doc', label='The district’s FY2019 budget document',
             total_col=2, kinds=['stated'] * 4,
             columns=['Town budget', 'Fee fund', 'The two', 'Fee fund’s share'],
             rows=[dict(label=C.fy(r['fy']), cells=[
                 C.usd(r['general']), C.usd(r['revolving']), C.usd(r['all_in']),
                 C.pct(100 * r['fund_share'])]) for r in sorted(old, key=lambda r: -r['fy'])],
             note='The only document that ever printed both sides line by line. These are the '
                  'years it marks as actual; it is a district restatement, not the ledger.')])
    out['town-budget-and-fee-fund'] = TP.page(
        'town-budget-and-fee-fund',
        'The fee fund paid %s of athletics spending in %s and %s in %s, on the town’s books.'
        % (C.pct(share[2024]), C.fy(2024), C.pct(share[2025]), C.fy(2025)),
        [fx['town26'], fx['fund26'], fx['share24'], fx['share25'], fx['share26'],
         f('share17', P(100 * hist[2017]['fund_share']),
           'fee fund’s share, %s, district %s document' % (C.fy(2017), C.fy(2019)),
           'published', {'y': F(2017), 'd': F(2019)}),
         f('moved25', U(moved25),
           'added to the town’s athletics budget during %s' % C.fy(2025), 'published',
           {'y': F(2025)}),
         fx['memo25']],
        [con('The fee fund’s share of athletics spending fell from %s in %s to %s in %s.'
             % (C.pct(share[2024]), C.fy(2024), C.pct(share[2025]), C.fy(2025)),
             ['share24', 'share25', 'share26'],
             {'a': P(share[2024]), 'y': F(2024), 'b': P(share[2025]), 'z': F(2025)},
             notes=[step('The fund’s %s spending is net of %s journal entries labelled expense '
                         'adjustments, and what they moved is not published.'
                         % (C.fy(2025), 'four'), 'gap', {'y': F(2025)},
                         closes='the memos the town ledger names beside those entries')]),
         con('In %s the town’s athletics budget rose %s during the year, by transfers.'
             % (C.fy(2025), C.usd(moved25)), ['moved25', 'memo25'],
             {'y': F(2025), 'm': U(moved25)},
             notes=[step('One reading is that charges moved from the fee fund to the town '
                         'budget. It fits the timing; nothing here tests it.', 'hypothesis')]),
         con('A town athletics line that rises may be a change in which fund pays, not in '
             'what athletics costs.', ['share24', 'share25', 'share17'])],
        chart=dict(id='spending-what-comes-in-athletics', source=CHART_SOURCE),
        table=table_pots,
        said=[said_file('school-committee/2025-03-12-minutes-7098.txt',
                        'Splitting everything into revolving funds is not a good way to manage '
                        'finances. We need to lay out all revenues and all expenses.',
                        'School Committee')],
        sources=[src['gf26'], src['gf25'], src['gf24'], src['sp26'], src['sp25'], src['sp24'],
                 src['fy19'], src['d-munis']],
        finding_figures={'a': P(share[2024]), 'y': F(2024), 'b': P(share[2025]),
                         'z': F(2025)})

    # ---- Cost per sport
    by = {s['name']: s for s in CS['sports']}
    wide = by[CS['widest']]
    track = by['Outdoor Track']
    att = A['attribution']
    if agree != 0:
        fail('%d teams now agree across the three sheets; the cost-per-sport page says none do'
             % agree)
    if att['sport_mentions'] != 0:
        fail('a fee-fund disbursement now names a sport; the cost-per-sport page says none does')
    sport_rows = [dict(label=s['name'] + (' (MS)' if s['level'] == 'MS' else ''), cells=[
        usd2(s['columns']['deck']), usd2(s['columns']['costsBySport']),
        usd2(s['columns']['workbook'])]) for s in CS['sports']]
    sport_rows.append(dict(label='All %s teams' % C.num(teams), cells=[
        usd2(tot['deck']), usd2(tot['costsBySport']), usd2(tot['workbook'])]))
    out['cost-per-sport'] = TP.page(
        'cost-per-sport',
        'Not one of %s teams carries the same %s cost in all three district sheets.'
        % (C.num(teams), C.fy(2024)),
        [fx['agree'],
         f('lax-lo', U2(wide['columns']['deck']), 'boys’ lacrosse, %s, the May 2024 deck'
           % C.fy(2024), 'published', {'y': F(2024)}, allow=('May 2024',)),
         f('lax-hi', U2(wide['columns']['workbook']), 'boys’ lacrosse, the by-sport workbook',
           'published'),
         f('track-lo', U2(track['columns']['deck']), 'outdoor track, %s, the May 2024 deck'
           % C.fy(2024), 'published', {'y': F(2024)}, allow=('May 2024',)),
         f('track-mid', U2(track['columns']['costsBySport']),
           'outdoor track, the “Costs by Sport” sheet', 'published'),
         f('track-hi', U2(track['columns']['workbook']), 'outdoor track, the by-sport workbook',
           'published'),
         f('payments', N(att['disbursements'], 'payments'),
           'fee fund disbursements, %s to %s' % (C.fy(min(att['years'])), C.fy(max(att['years']))),
           'published', {'a': F(min(att['years'])), 'b': F(max(att['years']))}),
         f('named', N(att['sport_mentions'], 'payments'), 'of them naming a sport',
           'published'),
         fx['sport-gap']],
        [con('Not one of the %s teams carries the same %s cost in all three district sheets.'
             % (C.num(teams), C.fy(2024)), ['agree'], {'n': N(teams), 'y': F(2024)},
             notes=[step('All three sheets were assembled by hand; none is the ledger.',
                         'gap', closes='a reconciliation by the district of its own per-sport '
                                       'cost statements, naming what each column counts')]),
         con('Boys’ lacrosse is stated at %s in one sheet and %s in another, for the same year.'
             % (usd2(wide['columns']['deck']), usd2(wide['columns']['workbook'])),
             ['lax-lo', 'lax-hi'],
             {'a': U2(wide['columns']['deck']), 'b': U2(wide['columns']['workbook'])},
             notes=[step('The columns may answer different questions, a season’s direct cost '
                         'against an all-in one. Nothing published tests that.',
                         'hypothesis')]),
         con('The town’s books cannot settle it: none of the fee fund’s %s payments names a sport.'
             % C.num(att['disbursements']), ['payments', 'named', 'sport-gap'],
             {'n': N(att['disbursements'], 'payments')})],
        table=dict(caption='%s cost per team, as three district sheets state it' % C.fy(2024),
                   views=[dict(key='teams', label='Three sheets, side by side', total_col=-1,
                               kinds=['stated'] * 3,
                               columns=['May 2024 deck', '“Costs by Sport”', 'By-sport workbook'],
                               rows=sport_rows,
                               note='Every column is a sheet somebody assembled, not the '
                                    'ledger. They are set side by side and never averaged.')]),
        said=[said_from(A['by_sport_said'], 0), said_from(A['by_sport_said'], 1),
              said_from(A['by_sport_said'], 2)],
        sources=[src['bysport'], src['costs1'], src['workbook'], src['cash26'], src['d-sport'],
                 src['d-fincom'], src['d-cash']],
        finding_figures={'n': N(teams), 'y': F(2024)})

    # ---- Spending by category
    cat = {r['fy']: r for r in A['categories']}
    c24 = cat[2024]
    acct = {(r['org'], r['obj']): r for r in town[2026]['rows']}
    if len(acct) != len(town[2026]['rows']):
        fail('two FY2026 athletics rows share an org and object')
    facct = {}
    for r in fund[2026]['rows']:
        facct[r['obj']] = facct.get(r['obj'], 0.0) + float(r['ytd_expended'] or 0)
    coaches26 = float(acct[('S3066671', '519003')]['ytd_expended'])
    director26 = float(acct[('S3066671', '511026')]['ytd_expended'])
    trainer26 = float(acct[('S3066671', '511029')]['ytd_expended'])
    officials26 = float(acct[('S3066672', '535021')]['ytd_expended']) + float(acct[('S3066672', '535021')]['revised_budget'])
    pos26, sal26 = facct['531006'], facct['519999']
    if officials26 != 0:
        fail('the town budget now carries athletic officials; the category page says it does not')
    if abs(pos26 - A['fy26_fund']['spending'] + sal26 + facct['545001']) > 0.01:
        fail('the fee fund’s FY2026 accounts no longer sum to the fund’s own report')
    cats = A['category_order']
    out['spending-by-category'] = TP.page(
        'spending-by-category',
        'Coaches and buses cost most on the district’s sheet; the town’s officials account held '
        '%s in %s.' % (C.usd(0), C.fy(2026)),
        [f('wb-coaches', U(c24['Coaches']), 'coaches, %s, district workbook' % C.fy(2024),
           'published', {'y': F(2024)}),
         f('wb-bus', U(c24['Transportation']), 'buses, %s, district workbook' % C.fy(2024),
           'published', {'y': F(2024)}),
         f('wb-officials', U(c24['Officials']), 'officials, %s, district workbook' % C.fy(2024),
           'published', {'y': F(2024)}),
         f('wb-else', U(c24['Everything else']), 'everything else, %s, district workbook'
           % C.fy(2024), 'published', {'y': F(2024)}),
         f('gf-coaches', U(coaches26), 'coaches, town budget, %s (ledger)' % C.fy(2026),
           'published', {'y': F(2026)}),
         f('gf-director', U(director26), 'athletic director, town budget, %s' % C.fy(2026),
           'published', {'y': F(2026)}),
         f('gf-trainer', U(trainer26), 'athletic trainer, town budget, %s' % C.fy(2026),
           'published', {'y': F(2026)}),
         f('gf-officials', U(officials26), 'officials account, town budget, %s (ledger)' % C.fy(2026),
           'published', {'y': F(2026)}),
         f('fund-pos', U(pos26), 'fee fund, purchased services, %s (ledger)' % C.fy(2026),
           'published', {'y': F(2026)}),
         f('fund-sal', U(sal26), 'fee fund, salaries, %s (ledger)' % C.fy(2026), 'published',
           {'y': F(2026)})],
        [con('On the district’s %s sheet, coaches and buses were the two largest costs.'
             % C.fy(2024), ['wb-coaches', 'wb-bus', 'wb-officials', 'wb-else'],
             {'y': F(2024)}),
         con('The town’s officials account held %s in %s; the fee fund bought %s of services.'
             % (C.usd(0), C.fy(2026), C.usd(pos26)), ['gf-officials', 'fund-pos'],
             {'z': U(0), 'y': F(2026), 'p': U(pos26)},
             notes=[step('What those services were, vendor by vendor, is not published.', 'gap',
                         closes='the fee fund’s purchase-of-service detail by vendor, from the '
                                'Town Accountant')]),
         con('The athletic director and trainer, %s in %s, are not on the district’s by-sport '
             'workbook.' % (C.usd(director26 + trainer26), C.fy(2026)),
             ['gf-director', 'gf-trainer'],
             {'a': U(director26 + trainer26), 'y': F(2026)})],
        table=dict(caption='Athletics by category, on the district’s workbook', views=[dict(
            key='categories', label='District by-sport workbook', total_col=len(cats),
            kinds=['stated'] * (len(cats) + 1), columns=cats + ['Total'],
            rows=[dict(label=C.fy(r['fy']), cells=[C.usd(r[k]) for k in cats] + [C.usd(r['total'])])
                  for r in sorted(A['categories'], key=lambda r: -r['fy'])],
            note='A sheet the district assembled, every sport and season summed. It is not the '
                 'ledger and it carries no director, trainer or insurance.')]),
        sources=[src['workbook'], src['gf26'], src['sp26'], src['funds26'], src['d-sport'],
                 src['d-munis']],
        finding_figures={'z': U(0), 'y': F(2026)})

    # ---- Participation
    pt = {r['fy']: r for r in A['participation_totals']}
    mix = {r['fy']: r for r in A['fee_mix']}
    part_rows = []
    for fy in sorted(pt, reverse=True):
        cells = []
        for lvl in ('HS', 'MS'):
            for season in ('Fall', 'Winter', 'Spring'):
                v = next(r['athletes'] for r in A['participation']
                         if r['fy'] == fy and r['level'] == lvl and r['season'] == season)
                cells.append(C.num(v))
        cells.append(C.num(pt[fy]['total']))
        part_rows.append(dict(label=C.fy(fy), cells=cells))
    for fy in pt:
        if pt[fy]['hs'] + pt[fy]['ms'] != pt[fy]['total']:
            fail('FY%d participation: levels no longer sum to the total' % fy)
    out['participation'] = TP.page(
        'participation',
        'The district counted %s sport participations in %s, against %s in %s.'
        % (C.num(pt[2026]['total']), C.fy(2026), C.num(pt[2024]['total']), C.fy(2024)),
        [f('part24', N(pt[2024]['total'], 'participations'), 'participations, %s'
           % C.fy(2024), 'published', {'y': F(2024)}),
         f('part25', N(pt[2025]['total'], 'participations'), 'participations, %s'
           % C.fy(2025), 'published', {'y': F(2025)}),
         f('part26', N(pt[2026]['total'], 'participations'), 'participations, %s'
           % C.fy(2026), 'published', {'y': F(2026)}),
         f('hs26', N(pt[2026]['hs'], 'participations'), 'of them high school, %s'
           % C.fy(2026), 'published', {'y': F(2026)}),
         f('ms26', N(pt[2026]['ms'], 'participations'), 'of them middle school, %s'
           % C.fy(2026), 'published', {'y': F(2026)}),
         f('waive24', N(mix[2024]['Full Waiver'], 'participations'),
           'fee fully waived, %s' % C.fy(2024), 'published', {'y': F(2024)}),
         f('waive25', N(mix[2025]['Full Waiver'], 'participations'),
           'fee fully waived, %s' % C.fy(2025), 'published', {'y': F(2025)}),
         f('students', None, 'how many different students play', 'gap',
           closes='a count of distinct students by year from the district’s athletic '
                  'registration system')],
        [con('Participations fell from %s in %s to %s in %s on the district’s workbook.'
             % (C.num(pt[2024]['total']), C.fy(2024), C.num(pt[2026]['total']), C.fy(2026)),
             ['part24', 'part25', 'part26'],
             {'a': N(pt[2024]['total']), 'y': F(2024), 'b': N(pt[2026]['total']),
              'z': F(2026)}),
         con('A participation is one student in one season, so these are not counts of '
             'children.', ['part26', 'students']),
         con('Full fee waivers rose from %s in %s to %s in %s.'
             % (C.num(mix[2024]['Full Waiver']), C.fy(2024), C.num(mix[2025]['Full Waiver']),
                C.fy(2025)), ['waive24', 'waive25'],
             {'a': N(mix[2024]['Full Waiver']), 'y': F(2024), 'b': N(mix[2025]['Full Waiver']),
              'z': F(2025)})],
        table=dict(caption='Participations by season and school', views=[dict(
            key='seasons', label='District by-sport workbook', total_col=6, kinds=['stated'] * 7,
            columns=['High school, fall', 'High school, winter', 'High school, spring',
                     'Middle school, fall', 'Middle school, winter', 'Middle school, spring',
                     'All'],
            rows=part_rows,
            note='A sheet the district assembled. One student playing three seasons counts '
                 'three times. Its out-of-district rows print negative counts and are left out.')]),
        sources=[src['workbook'], src['feecounts'], src['d-sport']],
        finding_figures={'a': N(pt[2026]['total']), 'y': F(2026), 'b': N(pt[2024]['total']),
                         'z': F(2024)})

    # ---- Athletic fee
    fee = {(r['fy'], r['level'], r['item']): r['amount'] for r in A['fees']}
    sched = {(int(r['fy']), r['level'], r['item']): float(r['amount'])
             for r in csv.DictReader(open(os.path.join(D, 'athletic-fee-schedule.csv'),
                                          encoding='utf-8'))}
    for k, v in fee.items():
        if sched.get(k) != v:
            fail('the fee register and athletics.json disagree on %s' % (k,))
    # FY2027 IS NOT STATED. The fee register marks every FY2027 amount `source not held`:
    # "nothing about it can be quoted -- the amount included". So the pages state the
    # published FY2025 -> FY2026 rise and carry FY2027 as a gap with what would settle it.
    hs25, hs26 = sched[(2025, 'HS', 'full_pay')], sched[(2026, 'HS', 'full_pay')]
    FEE27_CLOSES = 'the district’s FY2027 athletic fee schedule, as sent to families in August 2026'
    ms25, ms26 = sched[(2025, 'MS', 'full_pay')], sched[(2026, 'MS', 'full_pay')]
    cap25, cap26 = sched[(2025, 'HS', 'family_cap')], sched[(2026, 'ANY', 'family_cap')]
    sib = sched[(2026, 'HS', 'sibling_discount_pct')]
    red26 = sched[(2026, 'HS', 'reduced_fee')]
    chk = next(r for r in A['fee_check'] if r['level'] == 'High school')
    if not chk['under_top_tier']:
        fail('FY2026 high school fees banked per participation no longer come in under the rate')
    vote = next(s for s in W['said'] if s['key'] == 'thevote')
    cell = lambda k, fmt=C.usd: fmt(sched[k]) if k in sched else None
    fee_rows = []
    for fy in (2026, 2025, 2024):
        second = cell((fy, 'HS', 'second_child'))
        if fy == 2026:
            second = '%s off' % C.pct(sib, 0)
        fee_rows.append(dict(label=C.fy(fy), cells=[
            cell((fy, 'HS', 'full_pay')), second, cell((fy, 'MS', 'full_pay')),
            cell((fy, 'HS', 'reduced_fee')),
            cell((fy, 'HS', 'family_cap')) or cell((fy, 'ANY', 'family_cap'))]))
    out['athletic-fee'] = TP.page(
        'athletic-fee',
        'The high school fee for a first child, a season, went from %s in %s to %s in %s.'
        % (C.usd(hs25), C.fy(2025), C.usd(hs26), C.fy(2026)),
        [f('hs25', U(hs25), 'high school, first child, %s' % C.fy(2025), 'published',
           {'y': F(2025)}),
         f('hs26', U(hs26), 'high school, first child, %s' % C.fy(2026), 'published',
           {'y': F(2026)}),
         f('hs27', None, 'high school, first child, %s' % C.fy(2027), 'gap', {'y': F(2027)},
           closes=FEE27_CLOSES),
         f('ms25', U(ms25), 'middle school, first child, %s' % C.fy(2025), 'published',
           {'y': F(2025)}),
         f('ms26', U(ms26), 'middle school, first child, %s' % C.fy(2026), 'published',
           {'y': F(2026)}),
         f('sib26', P(sib, 0), 'off for a sibling, from %s' % C.fy(2026), 'published',
           {'y': F(2026)}),
         f('cap25', U(cap25), 'family cap a season, %s' % C.fy(2025), 'published',
           {'y': F(2025)}),
         f('cap26', U(cap26), 'family cap from %s, no period stated' % C.fy(2026),
           'published', {'y': F(2026)}),
         f('red26', U(red26), 'reduced fee, high school, %s' % C.fy(2026), 'published',
           {'y': F(2026)}),
         f('banked26', U2(chk['per_participation']),
           'banked per high school participation, %s' % C.fy(2026), 'estimate',
           {'y': F(2026)})],
        [con('The first-child high school fee rose from %s in %s to %s in %s.'
             % (C.usd(hs25), C.fy(2025), C.usd(hs26), C.fy(2026)), ['hs25', 'hs26', 'hs27'],
             {'a': U(hs25), 'y': F(2025), 'b': U(hs26), 'z': F(2026)},
             notes=[step('A new fee for %s was announced in an email this archive does not '
                         'hold, so its amount is not stated here.' % C.fy(2027), 'gap',
                         {'y': F(2027)}, allow=('August 2026',), closes=FEE27_CLOSES)]),
         con('The %s family cap states no period; the cap it replaced was %s a season.'
             % (C.usd(cap26), C.usd(cap25)), ['cap25', 'cap26'],
             {'a': U(cap26), 'b': U(cap25)},
             notes=[step('Read per season or per year, the same cap is a different bill for '
                         'the same family.', 'gap',
                         closes='the district’s athletic fee schedule as published to families, '
                                'stating the period the cap covers')]),
         con('In %s the fee fund banked %s per high school participation, under the %s rate.'
             % (C.fy(2026), usd2(chk['per_participation']), C.usd(hs26)),
             ['banked26', 'hs26', 'sib26', 'red26'],
             {'y': F(2026), 'a': U2(chk['per_participation']), 'b': U(hs26)},
             notes=[step('Our division: the fund’s own net fee revenue over the workbook’s '
                         'participations. Net means after the payment processor’s charge.',
                         'gap', closes='the fee receipts by family and by fee category from '
                                       'the district’s payment system')])],
        table=dict(caption='The athletic fee, a season, by year', views=[dict(
            key='fees', label='As set or stated', total_col=-1, kinds=['stated'] * 5,
            columns=['High school, first child', 'Second child', 'Middle school, first child',
                     'Reduced fee', 'Family cap'],
            rows=fee_rows,
            note='From the athletics FAQ, the district workbook and the School Committee vote '
                 'of 26 February 2025. FY2027 is left out: its source is not held. The newer '
                 'family cap states no period.')]),
        said=[dict(quote=vote['quote'], board=vote['board'], date=vote['date'],
                   href=vote['cite'], label='%s minutes, %s' % (vote['board'], vote['date']))],
        sources=[src['faq'], src['workbook'], src['funds26'], src['d-fees']],
        finding_figures={'a': U(hs25), 'y': F(2025), 'b': U(hs26), 'z': F(2026)})

    # ---- Fee fund ledger
    if abs(flow[2025]['without_journals'] - (flow[2025]['closing'] - memo25)) > 0.01:
        fail('the FY2025 close without journals no longer equals close less the four entries')
    jshare = pct1(memo25, flow[2025]['receipts'])
    flow_rows = [dict(label=C.fy(fy), cells=[
        C.usd(r['opening']), C.usd(r['receipts']), C.usd(r['payments']), C.usd(r['journals']),
        C.usd(r['closing'])]) for fy, r in sorted(flow.items(), reverse=True)]
    out['fee-fund-ledger'] = TP.page(
        'fee-fund-ledger',
        'The fee fund’s cash fell %s in %s; four journal entries then brought in %s in %s.'
        % (C.usd(-flow[2024]['net']), C.fy(2024), C.usd(memo25), C.fy(2025)),
        [f('open24', U(flow[2024]['opening']), 'cash at the start of %s' % C.fy(2024),
           'published', {'y': F(2024)}),
         f('net24', U(flow[2024]['net']), 'net change in cash, %s' % C.fy(2024), 'published',
           {'y': F(2024)}),
         f('close24', U(flow[2024]['closing']), 'cash at the end of %s' % C.fy(2024),
           'published', {'y': F(2024)}),
         f('receipts25', U(flow[2025]['receipts']), 'all money in, %s' % C.fy(2025),
           'published', {'y': F(2025)}),
         fx['memo25'],
         f('jshare', P(jshare), 'of the money in, %s, from those entries' % C.fy(2025),
           'published', {'y': F(2025)}),
         f('without25', U(flow[2025]['without_journals']),
           '%s close without them (our arithmetic)' % C.fy(2025), 'estimate', {'y': F(2025)}),
         f('close26', U(flow[2026]['closing']), 'cash on the export’s last day, %s'
           % C.fy(2026), 'published', {'y': F(2026)}),
         f('memo-gap', None, 'what the journal entries moved, and from where', 'gap',
           closes='the memos the ledger names beside each entry, from the Town Accountant')],
        [con('The fund’s cash fell by %s in %s, to %s at the year’s end.'
             % (C.usd(-flow[2024]['net']), C.fy(2024), C.usd(flow[2024]['closing'])),
             ['open24', 'net24', 'close24'],
             {'a': U(-flow[2024]['net']), 'y': F(2024), 'b': U(flow[2024]['closing'])}),
         con('In %s, %s of the money into the fund came on %s entries labelled expense '
             'adjustments.' % (C.fy(2025), C.pct(jshare), 'four'),
             ['receipts25', 'memo25', 'jshare', 'memo-gap'], {'y': F(2025), 'p': P(jshare)},
             notes=[step('An entry like this fits a charge moved to another fund, a transfer '
                         'in, or a correction. The ledger cannot tell them apart.', 'gap',
                         closes='the memos the ledger names beside each entry')]),
         con('Take those entries away and the fund closes %s at %s, by our arithmetic.'
             % (C.fy(2025), C.usd(flow[2025]['without_journals'])), ['without25', 'memo25'],
             {'y': F(2025), 'a': U(flow[2025]['without_journals'])},
             notes=[step('A resident told the School Committee the fund ran a deficit. These '
                         'figures fit that account; nothing here tests it.', 'hypothesis')])],
        table=dict(caption='The fee fund’s cash, by year', views=[dict(
            key='cash', label='The fund’s cashbook', total_col=4, kinds=['ledger'] * 5,
            columns=['Opening cash', 'Money in', 'Paid out', 'Of money in: journal entries',
                     'Closing cash'],
            rows=flow_rows,
            note='MUNIS journal exports for fund 1301. Each year’s close ties to the next '
                 'year’s printed opening. The latest year stops on 12 June 2026.')]),
        said=[said_file('school-committee/2025-09-03-minutes-7385.txt',
                        'in the past 6 months or so there have been things that have come up, '
                        'athletic revolving fund was running in a deficit, I was told over '
                        '$100,000', 'School Committee'),
              said_file('finance-committee/2025-07-08-minutes-7295.txt',
                        'She emphasized the need for all revolving accounts to have a budget, '
                        'even if they are not town meeting revolving accounts, to prevent '
                        'negative balances from going unnoticed.', 'Finance Committee')],
        sources=[src['cash24'], src['cash25'], src['cash26'], src['funds26'], src['d-cash']],
        finding_figures={'a': U(-flow[2024]['net']), 'y': F(2024), 'b': U(memo25),
                         'z': F(2025)})

    # ---- FY2026 athletics underspend
    t26 = town[2026]
    if abs(t26['revised'] - t26['spent'] - t26['owed'] - t26['left']) > 0.01:
        fail('the FY2026 athletics accounts no longer foot: budget less spent less owed')
    left_pct = pct1(t26['left'], t26['revised'])
    sec = acct[('S3066671', '511032')]
    if float(sec['ytd_expended']) != 0 or float(sec['revised_budget']) <= 0:
        fail('the athletics secretary account no longer shows a budget with nothing spent')
    rec, new = acct[('S3066672', '555048')], acct[('S3066672', '555050')]
    eq_left = float(rec['available_budget']) + float(new['available_budget'])
    rec_pct = pct1(float(rec['ytd_expended']), float(rec['revised_budget']))
    biggest = max(t26['rows'], key=lambda r: float(r['available_budget']))
    if biggest['obj'] != '511032':
        fail('the secretary account is no longer the largest unspent athletics account')
    under_rows = [dict(label=r['description'].capitalize(), cells=[
        C.usd(float(r['revised_budget'])), C.usd(float(r['ytd_expended'])),
        C.usd(float(r['encumbrances'])), C.usd(float(r['available_budget']))])
        for r in sorted(t26['rows'], key=lambda r: -float(r['revised_budget']))
        if any(float(r[k] or 0) for k in ('revised_budget', 'ytd_expended'))]
    under_rows.append(dict(label='All athletics accounts', cells=[
        C.usd(t26['revised']), C.usd(t26['spent']), C.usd(t26['owed']), C.usd(t26['left'])]))
    eq = A['counted']['equipment']['said']
    seq = A['helmets_sequel']
    out['fy2026-athletics-underspend'] = TP.page(
        'fy2026-athletics-underspend',
        'Athletics closed %s with %s of its %s town budget unspent, on the town’s ledger.'
        % (C.fy(2026), C.usd(t26['left']), C.usd(t26['revised'])),
        [f('rev26', U(t26['revised']), 'athletics budget after transfers, %s' % C.fy(2026),
           'published', {'y': F(2026)}),
         f('spent26', U(t26['spent']), 'spent by the close', 'published'),
         f('owed26', U(t26['owed']), 'committed and still owed at the close', 'published'),
         f('left26', U(t26['left']), 'left unspent', 'published'),
         f('leftpct', P(left_pct), 'of the budget left unspent', 'published'),
         f('sec', U(float(sec['revised_budget'])), 'athletics secretary, with nothing spent',
           'published'),
         f('coach-left', U(float(acct[('S3066671', '519003')]['available_budget'])),
           'left on the coaches line', 'published'),
         f('eq-left', U(eq_left), 'left on the two equipment lines', 'published'),
         f('rec-pct', P(rec_pct), 'of the reconditioning budget spent', 'published')],
        [con('Athletics closed %s with %s of its %s budget unspent, %s.'
             % (C.fy(2026), C.usd(t26['left']), C.usd(t26['revised']), C.pct(left_pct)),
             ['rev26', 'spent26', 'owed26', 'left26', 'leftpct'],
             {'y': F(2026), 'a': U(t26['left']), 'b': U(t26['revised']), 'p': P(left_pct)}),
         con('The largest piece was %s budgeted for an athletics secretary, with nothing spent.'
             % C.usd(float(sec['revised_budget'])), ['sec', 'coach-left'],
             {'a': U(float(sec['revised_budget']))},
             notes=[step('Whether the post was vacant or paid from another line is not '
                         'published.', 'gap',
                         closes='the district’s staffing roster for the athletic office')]),
         con('The equipment lines left %s unspent in the year a helmet request was raised in '
             'public.' % C.usd(eq_left), ['eq-left', 'rec-pct'], {'a': U(eq_left)},
             notes=[step('Reconditioning a helmet is not buying one, and nothing here dates '
                         'the request against any decision on it.', 'gap',
                         closes='the athletic department’s equipment requests and purchase '
                                'orders for the year')])],
        table=dict(caption='Athletics accounts at the close', views=[dict(
            key='accounts', label='Town general fund, function 3510', total_col=3,
            kinds=['ledger'] * 4, columns=['Budget after transfers', 'Spent', 'Still owed',
                                           'Left'],
            rows=under_rows,
            note='The MUNIS year-end (period 13) report. Left is the report’s own column: '
                 'budget less spent less still owed.')]),
        said=[said_from(eq, 0),
              dict(quote=seq['quotes'][0]['text'], board=seq['board'],
                   date=re.search(r'(\d{4}-\d{2}-\d{2})', seq['url']).group(1),
                   href=seq['url'], label='%s agenda, %s' % (
                       seq['board'], re.search(r'(\d{4}-\d{2}-\d{2})', seq['url']).group(1)))],
        sources=[src['gf26'], src['d-munis']],
        finding_figures={'y': F(2026), 'a': U(t26['left']), 'b': U(t26['revised'])})

    # ---- the hub
    fees_hub = [f('fee25', U(hs25), 'high school fee, first child, %s' % C.fy(2025),
                  'published', {'y': F(2025)}),
                f('fee26', U(hs26), 'the same fee, %s' % C.fy(2026), 'published',
                  {'y': F(2026)}),
                f('part26h', N(pt[2026]['total'], 'participations'),
                  'sport participations, %s' % C.fy(2026), 'published', {'y': F(2026)})]
    unspent = f('unspent26', U(t26['left']), 'town athletics budget unspent, %s'
                % C.fy(2026), 'published', {'y': F(2026)})
    tiers = [
        LD.tier('What it costs', [fx['town26'], fx['fund26'], fx['deck24'], fx['wb24'],
                                  fx['bldg-gap']]),
        LD.tier('Who pays, and how it moved', [fx['share24'], fx['share25']] + fees_hub),
        LD.tier('What is not settled', [fx['memo25'], unspent, fx['agree'], fx['sport-gap']]),
    ]
    mx = LD.matrix(
        [('town', 'Town budget'), ('fund', 'Fee fund'), ('sheets', 'District sheets'),
         ('families', 'Families')],
        [('cost', 'What it costs'), ('change', 'How it moved'), ('open', 'Not settled')],
        {('town', 'cost'): ['town26'], ('fund', 'cost'): ['fund26'],
         ('sheets', 'cost'): ['deck24', 'wb24'], ('families', 'cost'): ['part26h'],
         ('fund', 'change'): ['share24', 'share25'], ('families', 'change'): ['fee25', 'fee26'],
         ('town', 'open'): ['unspent26', 'bldg-gap'], ('fund', 'open'): ['memo25'],
         ('sheets', 'open'): ['agree', 'sport-gap']})
    hub_ladder = LD.ladder(tiers, [
        LD.conclusion('The town’s ledger shows %s paid for athletics in %s, and the fee fund %s.'
                      % (C.usd(town[2026]['spent']), C.fy(2026), C.usd(fund[2026]['spent'])),
                      ['town26', 'fund26'],
                      {'a': U(town[2026]['spent']), 'y': F(2026), 'b': U(fund[2026]['spent'])}),
        LD.conclusion('District sheets put the same teams’ %s cost anywhere from %s to %s.'
                      % (C.fy(2024), C.usd(tot['deck']), C.usd(tot['workbook'])),
                      ['deck24', 'wb24', 'agree'],
                      {'y': F(2024), 'a': U(tot['deck']), 'b': U(tot['workbook'])}),
        LD.conclusion('The fee fund paid %s of athletics spending in %s and %s in %s.'
                      % (C.pct(share[2024]), C.fy(2024), C.pct(share[2025]), C.fy(2025)),
                      ['share24', 'share25', 'memo25'],
                      {'a': P(share[2024]), 'y': F(2024), 'b': P(share[2025]), 'z': F(2025)}),
        LD.conclusion('The high school fee for a first child rose from %s in %s to %s in %s.'
                      % (C.usd(hs25), C.fy(2025), C.usd(hs26), C.fy(2026)),
                      ['fee25', 'fee26'],
                      {'a': U(hs25), 'y': F(2025), 'b': U(hs26), 'z': F(2026)}),
        LD.conclusion('Nothing published says what any one sport costs, or what the buildings '
                      'add.', ['sport-gap', 'bldg-gap']),
    ], matrix=mx)
    out['athletics'] = TP.hub(
        'athletics',
        'Athletics is paid from two pots, the town budget and a fee fund. The town’s ledger shows '
        '%s paid in %s and the fee fund %s; the district’s own sheets disagree on what each team '
        'costs, by a multiple.' % (C.usd(town[2026]['spent']), C.fy(2026),
                                   C.usd(fund[2026]['spent'])),
        hub_ladder, chart=dict(id='spending-what-comes-in-athletics', source=CHART_SOURCE),
        table=table_pots,
        answer_figures={'a': U(town[2026]['spent']), 'y': F(2026), 'b': U(fund[2026]['spent'])})

    if sorted(k for k in out if k != 'athletics') != sorted(MINE):
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
        print('athletics topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
