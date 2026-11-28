#!/usr/bin/env python3
"""FY2026 year end, split into topic pages: twelve pages and the fy2026-closeout hub.

    python3 scripts/build_fy2026_closeout_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_fy2026_closeout_topics.py --check   # fail if any output would change

WHY THIS EXISTS. scripts/topics.py has the model. This shelf absorbs four reports --
fy26-closeout (the school department at period 12), fy26-closeout-town (the other 67
departments at period 12), fy26-school-surplus (the school department at period 13, the
closed year) and fy25-school-surplus -- which between them answer the same few questions
two and three times. Each question gets one page here. Two pages on the shelf belong to
other categories and are only listed: special education transportation and the FY2026
athletics underspend.

WHICH LEDGER ANSWERS WHICH QUESTION. The school department is held at period 13 (the closed
year, run 6 October 2026), so every school figure here is read from it. The town's other
departments are held only to period 12 (June, run 1 September 2026, books still open), so
every town figure here says period 12 in its label. The two are never added together.

IT COMPUTES WHAT IT CAN FROM THE LEDGER AND READS THE REST. Every school total, count and
account is recomputed from sources/data/munis-school-ytd.csv and asserted equal to the
payload build_school_surplus.py wrote, so the two pages cannot disagree about one report.
What this script cannot recompute without duplicating that generator -- the category map,
the FY2027 workbook ties, the circuit breaker's tuition -- it reads from the payload.

  sources/data/munis-school-ytd.csv   MUNIS year-to-date reports, period 13, FY2023-FY2026,
                                      school general fund. A printout of the books (13a).
  sources/data/munis-ledger.csv       MUNIS year-to-date report, every general fund
                                      department, FY2026 period 12.
  fy28/public/data/fy26-school-surplus.json, fy25-school-surplus.json
                                      build_school_surplus.py: categories, FY2027 workbook
                                      figures (lps-budget-lines.csv, Balanced column), the
                                      circuit breaker's tuition, the verified quotes.

THE WORDS. "Paid" is ytd_expended alone. "Spent" is paid plus still committed (encumbered).
"Left" and "over" are the ledger's own available column: revised budget less paid less
committed. Nothing here subtracts a budget from an actual across documents (rule 1); an
FY2027 budget and an FY2026 figure are set side by side and never differenced.

TWO KNOWN DEFECTS IN fy26-closeout.md ARE NOT REPEATED. Athletics' underspend is function
3510 alone (the athletics page owns it; this shelf only lists it), and account 519104 is
"P/R UNIFIED SPORTS COACH" in MUNIS, not sports uniforms. Neither figure is stated here.
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
import topic_blocks as TB  # noqa: E402
import topics as REG  # noqa: E402
from brief import step as _step  # noqa: E402


def step(text, kind, figures=None, allow=(), closes=None):
    """brief.step, with the fiscal years a `closes` line names declared as literals: they
    name a document (the FY2026 transfer schedule), they are not figures."""
    lits = tuple(allow) + tuple(re.findall(r'FY\d{4}', closes or ''))
    return _step(text, kind, figures, lits, closes=closes)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'sources', 'data')
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT_DIR = os.path.join(PUB, 'topics')
MUNIS = os.path.join(D, 'munis-school-ytd.csv')
LEDGER = os.path.join(D, 'munis-ledger.csv')
MANIFEST = os.path.join(D, 'archive-manifest.csv')
MINUTES = os.path.join(ROOT, 'sources', 'meetings', 'text')
SRC26 = '/data/fy26-school-surplus.json'
HUB = 'fy2026-closeout'

# Every page this script writes, wherever it is homed: the three June town pages moved to the
# town year end (TJ, 26 November 2026) and are still written here.
MINE = [t for t, (_, home, gen) in REG.TOPICS.items()
        if gen == 'build_fy2026_closeout_topics.py']


def fail(msg):
    raise SystemExit('build_fy2026_closeout_topics: ' + msg)


def load(name):
    return json.load(open(os.path.join(PUB, name), encoding='utf-8'))


def near(a, b, tol=0.01):
    return abs(float(a) - float(b)) <= tol


def usd2(x):
    x = float(x)
    return ('-$' if x < 0 else '$') + format(abs(x), ',.2f')


# --------------------------------------------------------------------- the ledgers

def school(fy):
    """Department 300, period 13, every expense account the report prints."""
    rows = [r for r in csv.DictReader(open(MUNIS, encoding='utf-8'))
            if r['fiscal_year'] == str(fy) and r['period'] == '13'
            and r['report'] == 'gf-school' and r['type'] == 'E']
    if not rows:
        fail('no FY%d period-13 school general fund rows' % fy)
    for r in rows:
        for k in ('original_approp', 'transfers_adjustments', 'revised_budget', 'ytd_expended',
                  'encumbrances', 'available_budget'):
            r[k] = float(r[k] or 0)
        r['function'] = int(r['account'].split('-')[3])
    return rows


def town12():
    """Every general fund account at FY2026 period 12, as the town's report printed it."""
    rows = [r for r in csv.DictReader(open(LEDGER, encoding='utf-8'))
            if r['fy'] == '2026' and r['period'] == '12' and r['fund'] == '0100']
    if not rows:
        fail('no FY2026 period-12 general fund rows in munis-ledger.csv')
    for r in rows:
        for k in ('original', 'transfers', 'revised', 'expended', 'encumbered', 'available'):
            r[k] = float(r[k] or 0)
    return rows


def tot(rows, keys):
    return {k: round(sum(r[k] for r in rows), 2) for k in keys}


SK = ('original_approp', 'transfers_adjustments', 'revised_budget', 'ytd_expended',
      'encumbrances', 'available_budget')
TK = ('original', 'transfers', 'revised', 'expended', 'encumbered', 'available')


def said_file(rel, quote, board, kind='minutes'):
    """A quotation asserted here, verbatim, against our copy of the minutes."""
    text = ' '.join(open(os.path.join(MINUTES, rel), encoding='utf-8').read().split())
    if ' '.join(quote.split()) not in text:
        fail('quote is not verbatim in %s: %r' % (rel, quote))
    date = re.search(r'(\d{4}-\d{2}-\d{2})', rel).group(1)
    return dict(quote=quote, board=board, date=date,
                href='/docs/minutes/text/' + rel, label='%s %s, %s' % (board, kind, date))


def sources():
    man = {r['key'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    acct = 'Town of Lunenburg — Town Accountant (MUNIS)'
    spec = {
        'p13-26': ('town-ledgers/expenses/glytdbud-expense-fy2026-p13-gf-school.xlsx', acct),
        'p13-25': ('town-ledgers/expenses/glytdbud-expense-fy2025-p13-gf-school.xlsx', acct),
        'p13-24': ('town-ledgers/expenses/glytdbud-expense-fy2024-p13-gf-school.xlsx', acct),
        'p13-23': ('town-ledgers/expenses/glytdbud-expense-fy2023-p13-gf-school.xlsx', acct),
        'sp26': ('town-ledgers/expenses/glytdbud-expense-fy2026-p13-special-school.xlsx', acct),
        'p12': ('town-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.xlsx', acct),
        'wb27': ('budget-workbooks/fy27-proposals.xlsx', 'Lunenburg Public Schools'),
        'sc0729': ('meetings/school-committee/2026-07-29-minutes-7930.pdf',
                   'Lunenburg School Committee'),
        'sc1105': ('meetings/school-committee/2025-11-05-minutes-7496.docx',
                   'Lunenburg School Committee'),
        'sc0917': ('meetings/school-committee/2025-09-17-minutes-7408.pdf',
                   'Lunenburg School Committee'),
    }
    out = {}
    for k, (key, pub) in spec.items():
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        out[k] = dict(label='%s — %s' % (pub, key.split('/')[-1]), href='/docs/' + key)
    ours = {
        'd-munis': ('munis-school-ytd.csv', 'the period-13 school reports, one row an account'),
        'd-ledger': ('munis-ledger.csv', 'the period-12 general fund report, one row an account'),
        'd-wb': ('lps-budget-lines.csv', 'the FY2027 district workbook, line by line'),
        'd-je': ('munis-school-journal-entries.csv', 'the school journal, each entry joined to its other side'),
    }
    for k, (f, what) in ours.items():
        if not os.path.exists(os.path.join(ROOT, 'fy28', 'public', 'docs', 'data', f)):
            fail('/docs/data/%s is not published' % f)
        out[k] = dict(label='Lunenburg Budget Project — %s (%s)' % (f, what),
                      href='/docs/data/' + f)
    return out


# --------------------------------------------------------------------- the pages

def build():
    S = load('fy26-school-surplus.json')
    S25 = load('fy25-school-surplus.json')
    A = S['audit']
    src = sources()
    U = lambda v: figure(v, C.usd(v))
    U2 = lambda v: figure(v, usd2(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    f, con = LD.fact, TP.conclusion
    out = {}

    # ------------------------------------------------ the school ledger, recomputed
    L = {fy: school(fy) for fy in (2023, 2024, 2025, 2026)}
    s26 = tot(L[2026], SK)
    s25 = tot(L[2025], SK)
    for k, pk in (('original_approp', 'original'), ('transfers_adjustments', 'transfers'),
                  ('revised_budget', 'revised'), ('ytd_expended', 'expended'),
                  ('encumbrances', 'encumbered'), ('available_budget', 'available')):
        if not near(s26[k], S['totals'][pk]):
            fail('FY2026 %s: ledger %.2f, surplus payload %.2f' % (k, s26[k], S['totals'][pk]))
        if not near(s25[k], S25['totals'][pk]):
            fail('FY2025 %s: ledger %.2f, surplus payload %.2f' % (k, s25[k], S25['totals'][pk]))
    if not near(s26['revised_budget'] - s26['ytd_expended'] - s26['encumbrances'],
                s26['available_budget']):
        fail('the FY2026 school report no longer foots: revised less paid less committed')
    left26, enc26, rev26 = s26['available_budget'], s26['encumbrances'], s26['revised_budget']
    paid26 = s26['ytd_expended']
    ceiling = round(left26 + enc26, 2)
    left_pct = round(100 * left26 / rev26, 1)

    # period 12, the same department, from the other report
    T = town12()
    p12s = [r for r in T if r['dept'] == '300']
    p12 = tot(p12s, TK)
    if not near(p12['available'], S['period12']['totals']['available']):
        fail('period-12 school unspent no longer matches the surplus payload')
    moved = round(left26 - p12['available'], 2)
    if not near(moved, S['moved_since_p12']):
        fail('the move between the two runs is not the payload’s')
    if not near(p12['expended'], paid26):
        fail('school payments changed between period 12 and period 13; the pages say they did not')

    # over and under, by year
    def over_of(rows):
        o = [r for r in rows if r['available_budget'] < -0.004]
        return len(o), round(sum(r['available_budget'] for r in o), 2)
    by_year = {y['fy']: y for y in A['overdrawn']['by_year']}
    over = {}
    for fy in L:
        n, amt = over_of(L[fy])
        if n != by_year[fy]['accounts_over'] or not near(amt, by_year[fy]['over']):
            fail('FY%d accounts over budget: ledger %d / %.2f, payload %d / %.2f'
                 % (fy, n, amt, by_year[fy]['accounts_over'], by_year[fy]['over']))
        over[fy] = (n, amt)
    under26 = round(sum(r['available_budget'] for r in L[2026] if r['available_budget'] > 0.004), 2)
    if not near(under26, S['causes']['under_total']):
        fail('FY2026 under-budget total does not match the payload')
    over26_rows = [r for r in L[2026] if r['available_budget'] < -0.004]
    no_tr = sum(1 for r in over26_rows if r['transfers_adjustments'] <= 0.004)
    if no_tr != A['overdrawn']['accounts_over_no_transfer_in']:
        fail('accounts over with no transfer in: %d against the payload’s %d'
             % (no_tr, A['overdrawn']['accounts_over_no_transfer_in']))
    gross_in = round(sum(r['transfers_adjustments'] for r in L[2026]
                         if r['transfers_adjustments'] > 0), 2)
    gross_out = round(sum(r['transfers_adjustments'] for r in L[2026]
                          if r['transfers_adjustments'] < 0), 2)
    if not (near(gross_in, by_year[2026]['transfers_in'])
            and near(gross_out, by_year[2026]['transfers_out'])):
        fail('FY2026 gross transfers do not match the payload')
    net_tr = s26['transfers_adjustments']

    acct = {r['account']: r for r in L[2026]}
    if len(acct) != len(L[2026]):
        fail('two FY2026 school rows share an account string')

    # ------------------------------------------------ shared facts
    fx = {}
    fx['left26'] = f('left26', U(left26), 'left unspent, school general fund, %s' % C.fy(2026),
                     'published', {'y': F(2026)})
    fx['enc26'] = f('enc26', U(enc26), 'still committed to open purchase orders', 'published')
    fx['rev26'] = f('rev26', U(rev26), 'school budget after transfers, %s' % C.fy(2026),
                    'published', {'y': F(2026)})
    fx['paid26'] = f('paid26', U(paid26), 'paid by the close (period 13)', 'published',
                     allow=('13',))
    fx['ceiling'] = f('ceiling', U(ceiling), 'left if every open order is released (our sum)',
                      'published')
    fx['leftpct'] = f('leftpct', P(left_pct), 'of the school budget left unspent', 'published')

    # ---- FY2026 school surplus: FOLDED INTO THE HUB, 26 October 2026 (TJ: "this page seems
    # useless ... i think this data was shown on the main page"). It opened on the hub's own
    # figure and chart; what only it held -- the two runs of the report, and what the Committee
    # heard in July -- is the hub's table now. Its address opens the hub (routes.ts TOPIC_MERGED).
    told = S['stated']
    runs_table = dict(
        caption='The school general fund, %s, two runs of one report' % C.fy(2026),
        views=[dict(
            key='runs', label='Period 12 and period 13', total_col=-1, kinds=['ledger'] * 2,
            columns=['June report (period 12)', 'Closed year (period 13)'],
            rows=[dict(label=lab, cells=[usd2(p12[a_]), usd2(s26[b_])])
                  for lab, a_, b_ in (
                      ('Voted', 'original', 'original_approp'),
                      ('Moved by transfer, net', 'transfers', 'transfers_adjustments'),
                      ('Budget after transfers', 'revised', 'revised_budget'),
                      ('Paid', 'expended', 'ytd_expended'),
                      ('Still committed', 'encumbered', 'encumbrances'),
                      ('Left unspent', 'available', 'available_budget'))],
            note='MUNIS year-to-date budget reports for department 300, run 1 September and '
                 '6 October 2026; between them the figure moved %s and no payment changed. Left '
                 'is the report’s own column: budget less paid less still committed. In July the '
                 'School Committee heard the year would close “well below” the %s returned the '
                 'year before (minutes, 29 July 2026). On the footing FY2025’s closed report '
                 'uses, FY2026 is up to %s; counting orders owed, %s.'
                 % (usd2(moved), C.usd(told['returned_fy25']), C.usd(ceiling), C.usd(left26)))])
    if told['returned_fy25'] != 600000.0:
        fail('the July minutes figure in the payload changed')

    # ---- Surplus by category, WITH the lines over budget (26 October 2026). Lines over budget
    # was the other half of this page's own net -- the $1,201,434 -- and TJ called it "similarly
    # useless" on its own. One page now holds both halves, side by side, and the history of the
    # overruns; fy2026-lines-over-budget opens here (routes.ts TOPIC_MERGED).
    cats = {c['key']: c for c in S['causes']['categories']}
    if not near(sum(c['unspent'] for c in cats.values()), left26):
        fail('the categories no longer sum to the FY2026 unspent figure')
    disc = S['causes']['discretionary']
    b, cs, te, pa, sv = (cats[k] for k in ('buildings', 'counselors', 'teachers', 'paras',
                                           'sped_services'))
    top3 = sorted(cats.values(), key=lambda c: -c['unspent'])[:3]
    if [c['key'] for c in top3] != ['buildings', 'counselors', 'teachers']:
        fail('the three categories that left the most have changed: %s' % [c['key'] for c in top3])
    worst = min(cats.values(), key=lambda c: c['unspent'])
    if worst['key'] != 'paras':
        fail('paraprofessionals are no longer the largest category overrun')
    top5 = A['overdrawn']['top5']
    top5_sum = round(sum(r['available'] for r in top5), 2)
    for r in top5:
        if not near(acct[r['account']]['available_budget'], r['available']):
            fail('top overrun %s no longer matches the ledger' % r['account'])
    ch = A['chronic']
    chron = round(-(sum(y['gap'] for y in ch['electricity']['years'])
                    + sum(y['gap'] for y in ch['therapy']['years'])), 2)
    if not near(chron, A['chronic_total']):
        fail('the electricity and therapy shortfall does not sum to the payload’s')
    for k in ('electricity', 'therapy'):
        if ch[k]['over_years'] != 4:
            fail('%s was not voted below its spending in all four years' % k)
    if not (over[2025][0] < 10 < min(over[y][0] for y in (2023, 2024, 2026))):
        fail('the meaning says FY2025 alone closed with only a handful of accounts past budget')
    if not b['pct_of_revised'] > 10 * te['pct_of_revised']:
        fail('the upkeep conclusion assumes upkeep left a far larger share than teachers')
    # The page itself moved to build_fy2026_school_surplus.py on 24 November 2026 (it became
    # FY2026 school surplus, at the same address); the checks above still guard the figures the
    # hub shares with it.

    # ---- Year-end transfers
    gv = A['given']
    given = [r for r in L[2026] if r['transfers_adjustments'] > 0.004
             and r['available_budget'] > 0.004]
    g_in = round(sum(r['transfers_adjustments'] for r in given), 2)
    g_left = round(sum(r['available_budget'] for r in given), 2)
    if len(given) != gv['accounts'] or not near(g_in, gv['transfers_in']) \
            or not near(g_left, gv['left']):
        fail('accounts given money that ended unspent: %d / %.2f / %.2f against the payload'
             % (len(given), g_in, g_left))
    dues = acct['0100-3-300-1110-01-1-01-2-535003']
    if not (near(dues['transfers_adjustments'], 13500) and dues['available_budget'] > 13500):
        fail('school committee dues no longer received $13,500 and ended with more left')
    july = A['overdrawn']['july_total']
    if len(A['overdrawn']['july_transfers']) != 10 or \
            not near(sum(A['overdrawn']['july_transfers']), july):
        fail('the 29 July minutes no longer list ten transfers summing to the total')
    out['fy2026-school-transfers'] = TP.page(
        'fy2026-school-transfers',
        'Transfers moved %s into school accounts and %s out; the department ended %s up, net.'
        % (C.usd(gross_in), C.usd(-gross_out), C.usd(net_tr)),
        [f('in', U(gross_in), 'moved into school accounts, %s' % C.fy(2026), 'published',
           {'y': F(2026)}),
         f('out', U(-gross_out), 'moved out of school accounts', 'published'),
         f('net', U(net_tr), 'net into the school department', 'published'),
         f('july', U2(july), 'ten transfers itemised in the 29 July minutes', 'published',
           allow=('29 July',)),
         f('given-n', N(len(given), 'accounts'), 'accounts given money that then ended under',
           'published'),
         f('given-in', U(g_in), 'what those accounts were given, net', 'published'),
         f('given-left', U(g_left), 'what they still had left at the close', 'published'),
         f('dues-in', U(dues['transfers_adjustments']), 'moved into School Committee dues',
           'published'),
         f('dues-left', U(dues['available_budget']), 'left on that line at the close',
           'published'),
         f('counterparty', None, 'where the net came from, and by whose vote', 'gap',
           closes='the FY2026 transfer schedule by account, with the counterparty and the '
                  'vote for each')],
        [con('Transfers moved %s in and %s out; the department ended %s up, net.'
             % (C.usd(gross_in), C.usd(-gross_out), C.usd(net_tr)),
             ['in', 'out', 'net', 'counterparty'],
             {'i': U(gross_in), 'o': U(-gross_out), 'n': U(net_tr)},
             so='The gross moved was several times the net, so the net hides how much was '
                'reshuffled; the ledger cannot say who voted which part.',
             notes=[step('The ledger is net per account and names no counterparty, so it '
                         'cannot say which transfer was which.', 'gap',
                         closes='the FY2026 transfer schedule by account, with the '
                                'counterparty and the vote for each')]),
         con('The 29 July minutes itemise ten transfers totalling %s, account by account.'
             % usd2(july), ['july'], {'j': U2(july)}, allow=('29 July',),
             so='Credit where the record shows it: part of the year-end movement was put before '
                'the Committee account by account, in public.'),
         con('%s accounts were given %s by transfer and still closed with %s left.'
             % (C.num(len(given)), C.usd(g_in), C.usd(g_left)),
             ['given-n', 'given-in', 'given-left'],
             {'n': N(len(given)), 'i': U(g_in), 'l': U(g_left)},
             so='Money moved into lines that did not need it by the close, so a transfer is a '
                'forecast made during the year, not a measure of need.'),
         con('School Committee dues got %s, minuted as for a search invoice, and closed with %s '
             'left.'
             % (C.usd(dues['transfers_adjustments']), C.usd(dues['available_budget'])),
             ['dues-in', 'dues-left'],
             {'i': U(dues['transfers_adjustments']), 'l': U(dues['available_budget'])},
             so='A transfer minuted for one purpose left its line with more than it was given, '
                'so the minute and the ledger do not yet reconcile.',
             notes=[step('Whatever paid the search invoice, this line shows no payment of it. '
                         'Nothing held reconciles the two.', 'gap',
                         closes='the superintendent search invoice and the entry that paid it')])],
        chart=TP.series(
            'School transfers in and out', [C.fy(fy) for fy in sorted(by_year)],
            [TP.track('Moved into accounts', [by_year[fy]['transfers_in'] for fy in sorted(by_year)],
                      'published', 'bar'),
             TP.track('Moved out of accounts', [-by_year[fy]['transfers_out']
                                                for fy in sorted(by_year)], 'published', 'bar')],
            '$', kind='bar',
            note='Gross, summed account by account from the period-13 reports. The ledger names '
                 'no counterparty for any of it.', note_allow=('13',)),
        table=dict(caption='Accounts given money in %s that closed with money left'
                   % C.fy(2026), views=[dict(
                       key='given', label='Department 300, period 13', total_col=-1,
                       kinds=['ledger'] * 4,
                       columns=['Voted', 'Moved in, net', 'Paid', 'Left'],
                       rows=[dict(label=r['description'].capitalize(), cells=[
                           C.usd(r['original']), C.usd(r['transfers']), C.usd(r['spent']),
                           C.usd(r['available'])]) for r in gv['rows'][:8]],
                       note='The eight largest of the accounts by what was left. Left is '
                            'budget less paid less still committed.')]),
        said=[said_file('school-committee/2026-07-29-minutes-7930.txt',
                        'a series of year-end line-item transfers needed to cover overages '
                        'within the FY26 budget', 'School Committee'),
              said_file('school-committee/2026-07-29-minutes-7930.txt',
                        'additional year-end transfers may still be forthcoming',
                        'School Committee'),
              said_file('school-committee/2025-11-05-minutes-7496.txt',
                        'transfer $13,500 from admin tech contracts to school committee dues, '
                        'to cover superintendent search invoice', 'School Committee')],
        sources=[src['p13-26'], src['sc0729'], src['sc1105'], src['d-munis']],
        finding_figures={'i': U(gross_in), 'o': U(-gross_out), 'n': U(net_tr)})

    # ---- Surplus and FY2027 budget: FOLDED INTO THE HUB, 26 October 2026 (TJ: "this too ...
    # seems useless"). Its whole finding was two figures side by side that explain nothing about
    # each other; that is one line on the hub, said with the same caution.
    cut = A['fy27_cut']
    if not near(cut['level_service'] - cut['balanced'], cut['gap']):
        fail('the FY2027 level-service gap no longer foots')
    fx['gap27'] = f('gap27', U(cut['gap']), '%s school budget, set below level service'
                    % C.fy(2027), 'published', {'y': F(2027)})

    # ---- FY2025 school surplus: FOLDED INTO Surplus by year (surplus-bridge, written by
    # build_journal_surplus_topics.py), 26 October 2026. Its figure is one of that page's four
    # years, and its one finding -- the closed ledger above what the Committee was told -- is a
    # conclusion there. Its address opens that page (routes.ts TOPIC_MERGED).
    if s25['encumbrances'] != 0:
        fail('FY2025 now carries open purchase orders; Surplus by year says it carries none')

    # ---- Tuition at year end
    tu = A['tuition']
    lines = tu['lines']
    gf_tu = [r for r in L[2026] if r['function'] >= 9000]
    gf_tu_spent = round(sum(r['ytd_expended'] + r['encumbrances'] for r in gf_tu), 2)
    if not near(gf_tu_spent, tu['general_fund_fy26']):
        fail('general fund tuition, spent and committed, does not match the payload')
    priv = acct['0100-3-300-9300-51-1-06-2-535019']
    coll = acct['0100-3-300-9400-51-1-06-2-535023']
    for r, k in ((priv, 'private'), (coll, 'collab')):
        if not (near(r['original_approp'], lines[k]['voted'])
                and near(r['ytd_expended'], lines[k]['spent'])):
            fail('%s tuition no longer matches the payload' % k)
    if not near(priv['ytd_expended'] + priv['encumbrances'] + coll['ytd_expended']
                + coll['encumbrances'], gf_tu_spent):
        fail('general fund tuition is no longer exactly the private and collaborative lines')
    priv_pct = round(100 * priv['ytd_expended'] / priv['revised_budget'])
    coll_pct = round(100 * coll['ytd_expended'] / coll['revised_budget'])
    cby = {r['fy']: r for r in tu['by_year']}
    if not ((priv_pct - 100) * (coll_pct - 100) < 0
            and cby[2026]['cb_share_pct'] < cby[2023]['cb_share_pct']):
        fail('the tuition meanings assume the lines missed in opposite directions and the '
             'circuit breaker share fell')
    # THE WALK (TJ, 25 November 2026, on this table drawn in chat: "that table is insanely good
    # ... make sure thats on one fo the hub report pages"). From every bill charged to the
    # collaborative line to what the general fund paid and how far past budget, each step a
    # journal or ledger figure, and the arithmetic asserted so no step can drift from the others.
    import build_journal_surplus_topics as JSW
    import build_circuit_breaker_surplus as CBW
    cbd = CBW.data()
    w_own, w_early, w_cb = (float(cbd['own']), float(cbd['years'][2026]['early']),
                            float(cbd['charged']))
    w_all = round(w_own + w_early, 2)
    w_gf = coll['ytd_expended'] + coll['encumbrances']
    if not near(w_all - w_cb, w_gf):
        fail('the walk no longer foots: bills %s + early %s - circuit breaker %s != paid %s'
             % (w_own, w_early, w_cb, w_gf))
    if not near(w_gf - coll['revised_budget'], -coll['available_budget']):
        fail('the walk’s over-budget step no longer matches the ledger’s available column')
    walk = dict(caption='Collaborative tuition, from the bills to the budget', views=[dict(
        key='walk', label='%s, school general fund and fund 2640' % C.fy(2026), total_col=0,
        kinds=['ledger'],
        columns=['Amount'],
        rows=[dict(label='This year’s collaborative tuition bills', cells=[C.usd(w_own)]),
              dict(label='+ next year’s (%s) invoices, charged on 30 June' % C.fy(2027),
                   cells=[C.usd(w_early)]),
              dict(label='= everything charged to the line', cells=[C.usd(w_all)]),
              dict(label='− moved to the circuit breaker, 29 June', cells=[C.usd(-w_cb)]),
              dict(label='= what the general fund paid', cells=[C.usd(w_gf)]),
              dict(label='Budget, the general fund’s share', cells=[C.usd(coll['revised_budget'])]),
              dict(label='Over budget', cells=[C.usd(-coll['available_budget'])])],
        note='Each step is read from the school journal or the period-13 report, and the '
             'arithmetic is checked when the page is built. The budget is the line net of the '
             'circuit breaker money the vote counted on.', note_allow=('13', '2640'))])
    out['fy2026-tuition-lines'] = TP.page(
        'fy2026-tuition-lines',
        '%s budgets %s for the two tuition lines on which %s spent %s.'
        % (C.fy(2027), C.usd(tu['fy27']), C.fy(2026), C.usd(gf_tu_spent)),
        [f('priv-b', U(priv['revised_budget']), 'private tuition, %s budget' % C.fy(2026),
           'published', {'y': F(2026)}),
         f('priv-p', U(priv['ytd_expended']), 'private tuition, paid', 'published'),
         f('coll-b', U(coll['revised_budget']), 'collaborative tuition, budget', 'published'),
         f('coll-p', U(coll['ytd_expended']), 'collaborative tuition, paid', 'published'),
         f('both', U(gf_tu_spent), 'both lines, spent (paid and committed)', 'published'),
         f('w-all', U(w_all), 'collaborative tuition, everything charged to the line',
           'published'),
         f('w-over', U(-coll['available_budget']), 'collaborative tuition, past its budget',
           'published'),
         f('fy27', U(tu['fy27']), 'both lines, %s budget (district workbook)' % C.fy(2027),
           'published', {'y': F(2027)}),
         f('cb26', U(tu['circuit_breaker_fy26']), 'tuition from the circuit breaker fund, %s'
           % C.fy(2026), 'published', {'y': F(2026)}),
         f('cb-share26', P(cby[2026]['cb_share_pct']), 'circuit breaker’s share of tuition, %s'
           % C.fy(2026), 'published', {'y': F(2026)}),
         f('cb-share23', P(cby[2023]['cb_share_pct']), 'the same share, %s' % C.fy(2023),
           'published', {'y': F(2023)}),
         f('children', None, 'how many children either figure pays for', 'gap',
           closes='the tuition invoices by service period, and the FY2027 placement list '
                  'with the fund expected to pay each')],
        [con('Collaborative tuition charged %s; the general fund paid %s of it, %s past budget.'
             % (C.usd(w_all), C.usd(w_gf), C.usd(-coll['available_budget'])),
             ['w-all', 'coll-p', 'coll-b', 'w-over'],
             {'a': U(w_all), 'g': U(w_gf), 'o': U(-coll['available_budget'])},
             so='The circuit breaker took %s of it on 29 June, and %s was next year’s invoices.'
                % (C.usd(w_cb), C.usd(w_early)), so_figures={'c': U(w_cb), 'e': U(w_early)},
             so_allow=('29 June',)),
         con('Private tuition paid %s of its budget; collaborative tuition paid %s of its.'
             % (C.pct(priv_pct, 0), C.pct(coll_pct, 0)), ['priv-b', 'priv-p', 'coll-b', 'coll-p'],
             {'a': P(priv_pct, 0), 'b': P(coll_pct, 0)},
             so='The two tuition lines missed in opposite directions, so their combined budget '
                'was closer than either line was.',
             notes=[step('A shift from private to collaborative placements fits; so do rate '
                         'changes, recoding, and budgets struck high or low. Placement counts '
                         'by year are not published.', 'hypothesis')]),
         con('%s budgets %s for the two lines; %s spent %s on them.'
             % (C.fy(2027), C.usd(tu['fy27']), C.fy(2026), C.usd(gf_tu_spent)),
             ['fy27', 'both', 'children'],
             {'y': F(2027), 'a': U(tu['fy27']), 'z': F(2026), 'b': U(gf_tu_spent)},
             so='The next budget assumes far less general fund tuition than this year spent; '
                'what it rests on is the question for that line.',
             notes=[step('Placements ending, more expected from the circuit breaker, and '
                         'FY2027 tuition prepaid from FY2026 money all fit. None is tested '
                         'here.', 'hypothesis', allow=('FY2027', 'FY2026'))]),
         con('The circuit breaker paid %s of tuition in %s, against %s in %s.'
             % (C.pct(cby[2026]['cb_share_pct']), C.fy(2026), C.pct(cby[2023]['cb_share_pct']),
                C.fy(2023)), ['cb26', 'cb-share26', 'cb-share23'],
             {'a': P(cby[2026]['cb_share_pct']), 'y': F(2026),
              'b': P(cby[2023]['cb_share_pct']), 'z': F(2023)},
             so='The circuit breaker covers a smaller share of tuition than it did, so more of it '
                'falls on the school general fund.',
             notes=[step('Why its share fell is not measured: the reimbursement follows the '
                         'year of the cost at a rate the state sets, and the fund’s balance '
                         'is not held.', 'gap',
                         closes='the circuit breaker fund’s balance and claims by year, from '
                                'the district')])],
        chart=TP.series(
            'Out-of-district tuition, by who paid', [C.fy(r['fy']) for r in tu['by_year']],
            [TP.track('General fund', [r['general_fund'] for r in tu['by_year']], 'published',
                      'bar'),
             TP.track('Circuit breaker', [r['circuit_breaker'] for r in tu['by_year']],
                      'published', 'bar')],
            '$', kind='bar', stacked=True,
            note='Paid and committed, period 13. A general fund line is the town’s share, not '
                 'the cost.', note_allow=('13',)),
        table=dict(caption='Out-of-district tuition, by who paid', views=[dict(
            key='funds', label='General fund and circuit breaker, spent', total_col=2,
            kinds=['ledger'] * 4,
            columns=['General fund', 'Circuit breaker', 'Both', 'Circuit breaker share'],
            rows=[dict(label=C.fy(r['fy']), cells=[
                C.usd(r['general_fund']), C.usd(r['circuit_breaker']), C.usd(r['total']),
                C.pct(r['cb_share_pct'])]) for r in sorted(tu['by_year'], key=lambda r: -r['fy'])],
            note='Period-13 reports, general fund functions 9000 and up and fund 2640, paid '
                 'and committed. A general fund line is the town’s share, not the cost.')]),
        tables=[walk],
        sources=[dict(src['p13-26'], key='p13-26'), dict(src['sp26'], key='sp26'),
                 dict(src['wb27'], key='wb27'), dict(src['d-munis'], key='d-munis'),
                 dict(src['d-wb'], key='d-wb'), dict(JSW.sources()[0], key='journal')],
        flow=['finding',
              TP.cite(('table', 1), 'journal', 'p13-26', 'sp26'), ('conclusion', 0),
              ('conclusion', 1),
              TP.cite(('chart', 0), 'p13-26', 'sp26', 'd-munis'), ('conclusion', 3),
              TP.cite(('table', 0), 'p13-26', 'sp26', 'd-munis', 'wb27', 'd-wb'),
              ('conclusion', 2),
              'sources'],
        finding_figures={'y': F(2027), 'a': U(tu['fy27']), 'z': F(2026), 'b': U(gf_tu_spent)})

    # ---- Paraprofessional overrun
    kinder = [acct[a] for a in A['kinder']['accounts']]
    k_paid = round(sum(r['ytd_expended'] for r in kinder), 2)
    if any(r['original_approp'] or r['transfers_adjustments'] for r in kinder) \
            or not near(k_paid, A['kinder']['spent']):
        fail('the kindergarten accounts no longer show $0 budget, no transfer, and the payload’s '
             'spending')
    sped = [r for r in L[2026] if r['function'] == 2330 and r['org'].startswith('S25')
            and r['revised_budget'] > 0 and r['obj'] == '511203']
    sped_over = [r for r in sped if r['available_budget'] < -0.004]
    sped_paid = round(sum(r['ytd_expended'] for r in sped), 2)
    sped_net = round(sum(r['available_budget'] for r in sped), 2)
    cr = A['credit']
    if len(sped) != 5 or len(sped_over) != 5 or not near(sped_paid, cr['sped_paras_paid_fy26']) \
            or not near(sped_net, cr['sped_paras_over_fy26']):
        fail('the special-education paraprofessional lines no longer match the payload')
    para_rows = sorted([r for r in L[2026] if r['function'] == 2330 and r['ytd_expended']],
                       key=lambda r: r['available_budget'])
    if any(r['available_budget'] >= 0 for r in para_rows) or len(kinder) != 2 \
            or not all(r in para_rows for r in kinder):
        fail('the paraprofessional chart note no longer holds: every paying account over, '
             'two kindergarten accounts among them')
    # ---- Psychologist line
    psy = [r for r in L[2026] if r['obj'] == '511023' and r['revised_budget'] > 0]
    zero = [r for r in psy if r['ytd_expended'] == 0]
    if len(psy) != 4 or len(zero) != 1 or zero[0]['account'] != A['psych']['account']:
        fail('the psychologist accounts no longer show four lines with one paying nothing')
    full = [r for r in psy if r['ytd_expended'] >= r['revised_budget']]
    if len(full) != 3:
        fail('the other three psychologist lines no longer paid their budgets in full or over')
    soc = [r for r in L[2026] if r['obj'] == '511024' and r['revised_budget'] > 0]
    soc_left = round(sum(r['available_budget'] for r in soc), 2)
    z = zero[0]
    if any(r['transfers_adjustments'] for r in psy + soc):
        fail('a psychologist or social worker line now received a transfer')
    # ---- STAFF LINES (27 November 2026, the closeout review; TJ: "each of the sections is
    # effectively the same"). Paraprofessional overrun and Psychologist line were two pages whose
    # sharpest finding was the comparison between them, so they are one page that leads on it:
    # two kinds of staff line in one appropriation, one left money and one ran past its budget.
    # Rule 11: a budget line is dollars, not people -- nothing here says who was hired or left.
    if not (cs['unspent'] > 0 > pa['unspent']):
        fail('Staff lines says counselors left money while paraprofessionals ran over')
    fx_s = [
        f('cs-left', U(cs['unspent']), 'left on counselor and psychologist lines, net', 'published'),
        f('pa-over', U(-pa['unspent']), 'paraprofessional lines past budget, net', 'published'),
        f('k-budget', U(0), 'kindergarten aides, budget and transfers', 'published'),
        f('k-paid', U2(k_paid), 'kindergarten aides, paid', 'published'),
        f('k-27', U(A['kinder']['fy27']), 'kindergarten aides, %s budget' % C.fy(2027),
          'published', {'y': F(2027)}),
        f('sp-over', U(-sped_net), 'special-education aide lines over, together', 'published'),
        f('sp-27', U(cr['sped_paras_fy27']), 'those aides, %s budget (district workbook)'
          % C.fy(2027), 'published', {'y': F(2027)}),
        f('sp-paid', U(sped_paid), 'those aides, paid, %s' % C.fy(2026), 'published',
          {'y': F(2026)}),
        f('z-b', U(z['revised_budget']), 'psychologist account %s, budget' % z['org'],
          'published', allow=(z['org'],)),
        f('z-27', U(A['psych']['fy27']), 'the same line, %s budget (district workbook)'
          % C.fy(2027), 'published', {'y': F(2027)}),
        f('post', None, 'whether the post was vacant, on leave, or paid elsewhere', 'gap',
          closes='the position-control roster by month, and payroll by account')]
    # MOVED BETWEEN FUNDS (TJ, 28 November 2026): how much of the overrun is cost that journal
    # reclasses moved onto the para lines from other school funds (fy26-school-surplus.json,
    # categories[].between_funds, from journal_join.between_funds).
    pa_bf = pa['between_funds']
    if pa_bf is None or not 0 < pa_bf < -pa['unspent']:
        fail('Staff lines says reclasses from other funds account for part, not all, of the para overrun')
    pa_moved = step('Of that, %s is cost journal reclasses moved onto the para lines from other school '
                    'funds; without it they ran %s over.' % (C.usd(pa_bf), C.usd(-pa['unspent'] - pa_bf)),
                    'measured', {'m': U(pa_bf), 'r': U(-pa['unspent'] - pa_bf)})
    cons_s = [
        con('Counselor and psychologist lines left %s; paraprofessional lines ran %s past budget.'
            % (C.usd(cs['unspent']), C.usd(-pa['unspent'])), ['cs-left', 'pa-over'],
            {'c': U(cs['unspent']), 'p': U(-pa['unspent'])},
            so='Within one appropriation the two roughly offset, so the school total shows '
               'neither.',
            notes=[pa_moved,
                   step('That one paid for the other is a hypothesis. Late hires, contract steps '
                        'and hours fit the same two numbers, and no headcount is published.',
                        'hypothesis')]),
        con('Two kindergarten aide accounts with no budget and no transfer paid %s.'
            % usd2(k_paid), ['k-budget', 'k-paid', 'k-27'], {'k': U2(k_paid)},
            so='Money was spent where none was voted or moved, and the %s budget carries %s for '
               'these accounts.' % (C.fy(2027), C.usd(A['kinder']['fy27'])),
            so_figures={'y': F(2027), 'z': U(A['kinder']['fy27'])},
            notes=[step('A recoding, a grant expected to cover it, and an overrun awaiting a '
                        'transfer all fit. Nothing here chooses between them.', 'hypothesis')]),
        con('All %s special-education aide lines closed over, by %s; %s budgets them at %s.'
            % (C.num(len(sped)), C.usd(-sped_net), C.fy(2027), C.usd(cr['sped_paras_fy27'])),
            ['sp-over', 'sp-27', 'sp-paid'],
            {'n': N(len(sped)), 'o': U(-sped_net), 'y': F(2027), 'a': U(cr['sped_paras_fy27'])},
            so='Every line ran over, a pattern across the service; the next budget can be read '
               'against what they cost this year.'),
        con('One of four psychologist lines, %s budgeted, paid nothing; %s budgets it at %s.'
            % (C.usd(z['revised_budget']), C.fy(2027), C.usd(A['psych']['fy27'])),
            ['z-b', 'z-27', 'post'],
            {'b': U(z['revised_budget']), 'y': F(2027), 'a': U(A['psych']['fy27'])},
            so='The other %s paid in full; whether this post is filled decides whether the money '
               'is spent or left again.' % C.num(len(full)), so_figures={'n': N(len(full))},
            notes=[step('A line paying nothing fits a vacancy, a leave, a person paid from another '
                        'account, or a coding change. The ledger shows dollars.', 'gap',
                        closes='the position-control roster by month, and payroll by account')])]
    two = TB.panels('Two kinds of staff line', [
        dict(title='Paraprofessionals', rows=[
            ('Budget after transfers', C.usd(pa['revised']), None),
            ('Paid and owed', C.usd(pa['expended'] + pa['encumbered']), None),
            ('Past budget', C.usd(-pa['unspent']), 'bad')]),
        dict(title='Counselors and psychologists', rows=[
            ('Budget after transfers', C.usd(cs['revised']), None),
            ('Paid and owed', C.usd(cs['expended'] + cs['encumbered']), None),
            ('Left', C.usd(cs['unspent']), 'good')])],
        so='One ran past its budget by about what the other left.')
    sup = sorted(psy + soc, key=lambda r: (r['obj'], r['org']))
    out['fy2026-staff-lines'] = TP.page(
        'fy2026-staff-lines',
        'Counselor and psychologist lines left %s in %s; paraprofessional lines ran %s over.'
        % (C.usd(cs['unspent']), C.fy(2026), C.usd(-pa['unspent'])),
        fx_s, cons_s,
        chart=TP.ranking(
            'Paraprofessional accounts past budget',
            [(r['description'].capitalize(), -r['available_budget']) for r in para_rows], '$',
            highlight=[r['description'].capitalize() for r in kinder],
            note='Function 2330, period 13: every account that paid anything closed over. The '
                 'two kindergarten accounts had no budget at all.', note_allow=('2330', '13')),
        also=[TP.series(
            'School psychologist accounts', ['Psychologist, %s' % r['org']
                                             for r in sorted(psy, key=lambda r: r['org'])],
            [TP.track('Budget', [r['revised_budget'] for r in sorted(psy, key=lambda r: r['org'])],
                      'published', 'bar'),
             TP.track('Paid', [r['ytd_expended'] for r in sorted(psy, key=lambda r: r['org'])],
                      'published', 'bar')],
            '$', kind='bar',
            note='Object 511023, one account per building, period 13. None received a transfer.',
            note_allow=('511023', '13'))],
        table=dict(caption='Paraprofessional accounts that paid anything, %s' % C.fy(2026),
                   views=[dict(
                       key='paras', label='Function 2330, period 13', total_col=-1,
                       kinds=['ledger'] * 4,
                       columns=['Voted', 'Moved in, net', 'Paid', 'Left'],
                       rows=[dict(label=r['description'].capitalize(), cells=[
                           C.usd(r['original_approp']), C.usd(r['transfers_adjustments']),
                           C.usd(r['ytd_expended']), C.usd(r['available_budget'])])
                           for r in sorted(para_rows, key=lambda r: r['available_budget'])],
                       note='A budget line is dollars, not people: a line over budget does not '
                            'say more aides were hired.')]),
        tables=[dict(caption='Psychologist and social worker accounts, %s' % C.fy(2026),
                     views=[dict(
                         key='support', label='Objects 511023 and 511024, period 13',
                         total_col=-1, kinds=['ledger'] * 3,
                         columns=['Budget', 'Paid', 'Left'],
                         rows=[dict(label='%s (%s)' % (r['description'].capitalize(), r['org']),
                                    cells=[C.usd(r['revised_budget']), C.usd(r['ytd_expended']),
                                           C.usd(r['available_budget'])]) for r in sup],
                         note='One account per building. None received a transfer in.')])],
        blocks=[two],
        said=[said_file('school-committee/2026-07-29-minutes-7930.txt',
                        '$81,075.96 from the High School Special Education Resource Room '
                        'Teacher account to Hospital Tutoring and the ACE, Primary School, '
                        'Elementary School, Middle School and High School Special Education '
                        'Paraprofessional accounts to cover overages in those areas',
                        'School Committee')],
        sources=[dict(src['p13-26'], key='p13'), dict(src['wb27'], key='wb27'),
                 dict(src['sc0729'], key='sc0729'), dict(src['d-munis'], key='d-munis'),
                 dict(src['d-wb'], key='d-wb'), dict(src['d-je'], key='d-je')],
        flow=['finding',
              TP.cite(('block', 0), 'p13', 'd-munis', 'd-je'), ('conclusion', 0),
              TP.cite(('chart', 0), 'p13', 'd-munis'), ('conclusion', 1), ('conclusion', 2),
              TP.cite(('table', 0), 'p13', 'd-munis', 'wb27', 'd-wb'), 'said',
              TP.cite(('chart', 1), 'p13', 'd-munis'), ('conclusion', 3),
              TP.cite(('table', 1), 'p13', 'd-munis', 'wb27', 'd-wb', 'sc0729'),
              'sources'],
        finding_figures={'c': U(cs['unspent']), 'y': F(2026), 'p': U(-pa['unspent'])})

    # ------------------------------------------------ the town, period 12
    tw = [r for r in T if r['dept'] not in ('300', '301')]
    t = tot(tw, TK)
    depts = len({r['dept'] for r in tw})
    t_over = [r for r in tw if r['available'] < -0.5]
    t_under = [r for r in tw if r['available'] > 0.5]
    t_over_amt = round(-sum(r['available'] for r in t_over), 2)
    t_under_amt = round(sum(r['available'] for r in t_under), 2)
    s_over12 = sum(1 for r in p12s if r['available'] < -0.5)
    t_ceiling = round(t['available'] + t['encumbered'], 2)
    tr = [r for r in tw if r['dept'] in ('993', '996')]
    if len(tr) != 2 or any(not near(r['revised'], r['expended']) for r in tr):
        fail('the two transfer accounts no longer spend their revised budgets exactly')
    tr_o = round(sum(r['original'] for r in tr), 2)
    tr_e = round(sum(r['expended'] for r in tr), 2)
    if not near(t['expended'] + t['encumbered'] + t['available'], t['revised'], 0.05):
        fail('the town report no longer foots: paid + committed + left != budget')
    if not len(t_over) / len(tw) < s_over12 / len(p12s):
        fail('the meaning says accounts past budget were rarer on the town side')
    if not (gross_in > 3 * net_tr > 0):
        fail('the transfers meaning says the gross was several times the net')
    out['fy2026-town-unspent'] = TP.page(
        'fy2026-town-unspent',
        'In June, before the close, town departments stood %s under a %s budget.'
        % (C.usd(t['available']), C.usd(t['revised'])),
        [f('t-rev', U(t['revised']), 'town budget after transfers, %s, period 12' % C.fy(2026),
           'published', {'y': F(2026)}, allow=('12',)),
         f('t-paid', U(t['expended']), 'paid by June', 'published'),
         f('t-enc', U(t['encumbered']), 'still committed in June', 'published'),
         f('t-left', U(t['available']), 'left unspent in June', 'published'),
         f('t-ceil', U(t_ceiling), 'left if every open order is released (our sum)',
           'published'),
         f('t-n', N(len(tw), 'accounts'), 'town accounts, across %s departments' % C.num(depts),
           'published', {'d': N(depts)}),
         f('t-over', N(len(t_over), 'accounts'), 'town accounts over budget in June',
           'published'),
         f('s-over', N(s_over12, 'accounts'), 'school accounts over in June, of %s'
           % C.num(len(p12s)), 'published', {'n': N(len(p12s))}),
         f('tr-o', U(tr_o), 'voted for transfers to capital and stabilization', 'published'),
         f('tr-e', U(tr_e), 'moved to capital and stabilization by June', 'published'),
         f('p13', None, 'the town general fund at the close (period 13)', 'gap',
           allow=('13',), closes='the town general fund’s FY2026 period-13 budget report')],
        [con('In June the town stood %s under budget: %s under on %s accounts, %s over on %s.'
             % (C.usd(t['available']), C.usd(t_under_amt), C.num(len(t_under)),
                C.usd(t_over_amt), C.num(len(t_over))),
             ['t-rev', 't-paid', 't-enc', 't-left', 't-over', 't-n'],
             {'a': U(t['available']), 'u': U(t_under_amt), 'n': N(len(t_under)),
              'o': U(t_over_amt), 'm': N(len(t_over))},
             so='The town is a June reading with books still open, so its figure is not yet the '
                'year’s final one.'),
         con('%s of %s town accounts were over in June; %s of %s school accounts were.'
             % (C.num(len(t_over)), C.num(len(tw)), C.num(s_over12), C.num(len(p12s))),
             ['t-over', 't-n', 's-over'],
             {'a': N(len(t_over)), 'b': N(len(tw)), 'c': N(s_over12), 'd': N(len(p12s))},
             so='Accounts past budget were rarer on the town side than in the schools, in the '
                'same month of the same year.',
             notes=[step('Tighter school budgets, readier town transfers, and different '
                         'coding all fit; nothing here separates them.', 'hypothesis')]),
         con('Two transfer accounts voted %s moved %s to capital and stabilization funds.'
             % (C.usd(tr_o), C.usd(tr_e)), ['tr-o', 'tr-e'], {'o': U(tr_o), 'e': U(tr_e)},
             so='Part of the year’s budget went to reserves and capital by vote during the year, '
                'moved on purpose rather than left over.',
             notes=[step('The ledger records that these budgets grew, not what vote funded '
                         'the growth.', 'gap',
                         closes='the FY2026 Town Meeting votes funding the capital and '
                                'stabilization transfers')]),
         con('%s was still committed in June; released in full, the figure reaches %s.'
             % (C.usd(t['encumbered']), C.usd(t_ceiling)), ['t-enc', 't-ceil', 'p13'],
             {'e': U(t['encumbered']), 'c': U(t_ceiling)},
             so='Until the close, the town’s leftover is a range, as the schools’ was before theirs.')],
        chart=TP.ranking(
            'Town accounts under and over in June',
            [('Left on accounts under budget', t_under_amt),
             ('Spent past budget on the others', t_over_amt),
             ('Net left unspent', t['available'])], '$', highlight='Net left unspent',
            note='Town departments, period 12, before the close: %s accounts under, %s over.'
                 % (C.num(len(t_under)), C.num(len(t_over))),
            note_figures={'n': N(len(t_under)), 'm': N(len(t_over))}, note_allow=('12',)),
        table=dict(caption='The town general fund, %s, as of June' % C.fy(2026), views=[dict(
            key='town', label='67 departments, period 12', total_col=-1, kinds=['ledger'],
            columns=['Town departments'],
            rows=[dict(label=lab, cells=[usd2(t[k])]) for lab, k in (
                ('Voted', 'original'), ('Moved by transfer, net', 'transfers'),
                ('Budget after transfers', 'revised'), ('Paid', 'expended'),
                ('Still committed', 'encumbered'), ('Left unspent', 'available'))],
            note='MUNIS year-to-date report run 1 September 2026, every general fund '
                 'department except the schools (300 and 301). Zero-balance accounts were '
                 'suppressed. Books still open.')]),
        sources=[src['p12'], src['d-ledger']],
        finding_figures={'a': U(t['available']), 'r': U(t['revised'])})
    if depts != 67:
        fail('the town report no longer covers 67 departments; the table label says it does')

    # ---- Snow and Reserve Fund
    snow = [r for r in tw if r['dept'] == '423']
    sn = tot(snow, TK)
    wages = next(r for r in snow if r['object'] == '513000')
    rf = next(r for r in tw if r['dept'] == '132')
    rb = next(r for r in tw if r['dept'] == '133' and r['object'] == '517000')
    if rf['expended'] != 0 or rf['transfers'] != 0 or wages['transfers'] != 0:
        fail('the Reserve Fund or the snow wages line now shows movement')
    w_pct = round(100 * wages['expended'] / wages['revised'])
    if not (2.5 < sn['expended'] / sn['original'] < 3.5 and w_pct > 100):
        fail('the snow meanings assume about three times the vote, and wages over budget')
    out['fy2026-snow-and-reserve-fund'] = TP.page(
        'fy2026-snow-and-reserve-fund',
        'Snow removal paid %s against %s voted; the %s Reserve Fund paid nothing.'
        % (C.usd(sn['expended']), C.usd(sn['original']), C.usd(rf['original'])),
        [f('sn-o', U(sn['original']), 'snow removal, voted, %s' % C.fy(2026), 'published',
           {'y': F(2026)}),
         f('sn-t', U(sn['transfers']), 'added by transfer, net', 'published'),
         f('sn-r', U(sn['revised']), 'snow budget after transfers', 'published'),
         f('sn-p', U(sn['expended']), 'snow removal, paid by June (period 12)', 'published',
           allow=('12',)),
         f('sn-over', U(-sn['available']), 'over its budget after transfers', 'published'),
         f('w-b', U(wages['revised']), 'snow wages, budget, no transfer in', 'published'),
         f('w-p', U(wages['expended']), 'snow wages, paid', 'published'),
         f('w-pct', P(w_pct, 0), 'of the wages budget paid', 'published'),
         f('rf', U(rf['original']), 'Reserve Fund, voted', 'published'),
         f('rf-p', U(0), 'Reserve Fund, paid or moved', 'published'),
         f('rb', U(rb['original']), 'retirement buy-back reserve, unused', 'published')],
        [con('Snow removal paid %s against %s voted and %s after transfers.'
             % (C.usd(sn['expended']), C.usd(sn['original']), C.usd(sn['revised'])),
             ['sn-o', 'sn-t', 'sn-r', 'sn-p', 'sn-over'],
             {'p': U(sn['expended']), 'o': U(sn['original']), 'r': U(sn['revised'])},
             so='Snow paid about three times its vote, so the vote was a starting figure, not a '
                'forecast of this winter.'),
         con('The wages line, %s budgeted, paid %s with no transfer in.'
             % (C.usd(wages['revised']), C.usd(wages['expended'])), ['w-b', 'w-p', 'w-pct'],
             {'b': U(wages['revised']), 'p': U(wages['expended'])},
             so='The overrun on wages was never covered by a transfer, so it rests on the other '
                'snow lines and the town’s close.'),
         con('The %s Reserve Fund paid nothing and moved nothing in the same year.'
             % C.usd(rf['original']), ['rf', 'rf-p', 'rb'], {'r': U(rf['original'])},
             so='The contingency meant for overruns went unused in a year snow ran over, so it is '
                'still there at the close.',
             notes=[step('A contingency nobody needed, a policy of leaving it, or a reserve '
                         'nobody asked to use all fit; nothing here separates them.',
                         'hypothesis')])],
        chart=TP.series(
            'Snow removal and the Reserve Fund',
            ['Snow removal', 'Snow wages', 'Reserve Fund'],
            [TP.track('Voted', [sn['original'], wages['original'], rf['original']], 'published',
                      'bar'),
             TP.track('After transfers', [sn['revised'], wages['revised'], rf['revised']],
                      'published', 'bar'),
             TP.track('Paid by June', [sn['expended'], wages['expended'], rf['expended']],
                      'published', 'bar')],
            '$', kind='bar',
            note='Period 12, books still open. The Reserve Fund’s paid bar is a true zero.',
            note_allow=('12',)),
        table=dict(caption='Snow removal, department 423, as of June', views=[dict(
            key='snow', label='Period 12', total_col=-1, kinds=['ledger'] * 4,
            columns=['Voted', 'Moved in, net', 'Paid', 'Left'],
            rows=[dict(label=r['name'], cells=[
                C.usd(r['original']), C.usd(r['transfers']), C.usd(r['expended']),
                C.usd(r['available'])]) for r in sorted(snow, key=lambda r: r['available'])]
            + [dict(label='Department 423', cells=[
                C.usd(sn['original']), C.usd(sn['transfers']), C.usd(sn['expended']),
                C.usd(sn['available'])])],
            note='Account names as MUNIS prints them. Books still open in June.')]),
        sources=[src['p12'], src['d-ledger']],
        finding_figures={'p': U(sn['expended']), 'o': U(sn['original']), 'r': U(rf['original'])})

    # ---- School retiree insurance
    ins = [r for r in tw if r['dept'] == '914']
    ins_paid = round(sum(r['expended'] for r in ins), 2)
    sr = next(r for r in ins if r['name'] == 'SCHRETHLTH')
    hi = next(r for r in ins if r['name'] == 'HEALTH INS')
    rest = round(ins_paid - sr['expended'], 2)
    # The school department pays its OWN staff health insurance, on one account. Read off
    # the page (every function-5000 account), not inferred from a search that found nothing.
    shi = [r for r in L[2026] if r['function'] == 5200 and r['obj'] == '570001']
    if len(shi) != 1 or shi[0]['ytd_expended'] <= 0:
        fail('the school department no longer carries one paid health insurance account')
    shi_paid = shi[0]['ytd_expended']
    out['fy2026-school-retiree-insurance'] = TP.page(
        'fy2026-school-retiree-insurance',
        'An account named for school retiree health paid %s from the town’s insurance '
        'department.' % C.usd(sr['expended']),
        [f('ins', U(ins_paid), 'town insurance department, paid by June', 'published'),
         f('sr-b', U(sr['revised']), 'SCHRETHLTH, budget, %s' % C.fy(2026), 'published',
           {'y': F(2026)}),
         f('sr-p', U(sr['expended']), 'SCHRETHLTH, paid by June (period 12)', 'published',
           allow=('12',)),
         f('rest', U(rest), 'the rest of the insurance department, paid', 'published'),
         f('hi', U(hi['expended']), 'HEALTH INS, town department, paid by June', 'published'),
         f('shi', U(shi_paid), 'school ledger’s HEALTH INSURANCE account, paid, %s'
           % C.fy(2026), 'published', {'y': F(2026)}),
         f('split', None, 'whether any town HEALTH INS covers school staff', 'gap',
           closes='the health insurance billing by employer group, town and school, from the '
                  'Town')],
        [con('The town’s insurance department paid %s by June; %s was on SCHRETHLTH.'
             % (C.usd(ins_paid), C.usd(sr['expended'])), ['ins', 'sr-b', 'sr-p'],
             {'i': U(ins_paid), 's': U(sr['expended'])},
             so='If the name means what it says, a school cost sits on the town’s side, outside '
                'the school budget.',
             notes=[step('Reading SCHRETHLTH as school retiree health insurance is ours, '
                         'from the account name.', 'gap',
                         closes='the Town Accountant’s chart of accounts naming account 570018',
                         allow=('570018',))]),
         con('The school ledger carries its own health insurance account: %s paid in %s.'
             % (C.usd(shi_paid), C.fy(2026)), ['shi'],
             {'s': U(shi_paid), 'y': F(2026)},
             so='The school ledger pays its own staff insurance; anything the town side carries '
                'for the schools is on top of it.'),
         con('Whether any of the town’s other %s covers school staff is not split out.'
             % C.usd(rest), ['rest', 'hi', 'split'], {'r': U(rest)},
             so='Until the billing is split by employer, the school share of town insurance is '
                'unknown, not zero.')],
        chart=TP.ranking(
            'The insurance department, paid by June',
            [(r['name'], r['expended']) for r in ins], '$', highlight='SCHRETHLTH',
            note='Department 914, period 12, account names as MUNIS prints them. The school '
                 'ledger’s own insurance account is a different report and is not drawn here.',
            note_allow=('914', '12')),
        table=dict(caption='Department 914, insurance, as of June', views=[dict(
            key='ins', label='Period 12', total_col=-1, kinds=['ledger'] * 3,
            columns=['Budget', 'Paid', 'Left'],
            rows=[dict(label=r['name'], cells=[C.usd(r['revised']), C.usd(r['expended']),
                                               C.usd(r['available'])])
                  for r in sorted(ins, key=lambda r: -r['expended'])],
            note='Account names as MUNIS prints them. A school cost carried by the town is '
                 'one reason the school budget is not what the schools cost.')]),
        sources=[src['p12'], src['p13-26'], src['d-ledger'], src['d-munis']],
        finding_figures={'s': U(sr['expended'])})

    # ------------------------------------------------ the hub
    # ONE FOOTING FOR TWO YEARS (26 October 2026). FY2025's closed report leaves out the orders
    # it still owed at its close (they were paid from FY2026's carried-forward budget); FY2026's,
    # run before its close, counts its open orders as spent. The hub set the two side by side as
    # printed. It now states FY2025 counted the way FY2026 is, read from the journal module
    # Surplus by year uses, so the two pages cannot disagree.
    import build_journal_surplus_topics as JS
    jd = JS.data()
    if not (near(float(jd['left'][2025]), s25['available_budget'])
            and near(float(jd['left'][2026]), left26)):
        fail('the journal no longer reproduces the period-13 figures the hub states')
    owed25 = round(float(jd['left'][2025] - jd['closed'][2025]), 2)
    wv, why_left = why_it_was_left(L, left26, JS)
    h = dict(
        left=fx['left26'], enc=fx['enc26'], leftpct=fx['leftpct'],
        under=f('h-under', U(under26), 'left on school accounts under budget', 'published'),
        over=f('h-over', U(-over[2026][1]), 'spent past budget on the rest', 'published'),
        n26=f('h-n26', N(over[2026][0], 'accounts'), 'school accounts past budget, %s'
              % C.fy(2026), 'published', {'y': F(2026)}),
        n25=f('h-n25', N(over[2025][0], 'accounts'), 'the same count, %s' % C.fy(2025),
              'published', {'y': F(2025)}),
        left25=f('h-left25', U(owed25), '%s, counted the same way (our sum)' % C.fy(2025),
                 'published', {'y': F(2025)}),
        grant=f('h-grant', U(wv['may26']), 'tuition paid by the special education grant, %s'
                % C.fy(2026), 'published', {'y': F(2026)}),
        priv=f('h-priv', U(wv['priv']), 'left on private tuition, the largest leftover',
               'published'),
        tuit=f('h-tuit', U(gf_tu_spent), 'out-of-district tuition, spent, %s' % C.fy(2026),
               'published', {'y': F(2026)}),
        kind=f('h-kind', U(k_paid), 'kindergarten aides paid, with no budget', 'published'),
        town=f('h-town', U(t['available']), 'town departments under budget in June',
               'published'),
        snow=f('h-snow', U(sn['expended']), 'snow removal, paid by June', 'published'),
        counter=f('h-counter', None, 'where the net transfers came from', 'gap',
                  closes='the FY2026 transfer schedule by account, with the counterparty and '
                         'the vote for each'),
        tp13=f('h-tp13', None, 'the town general fund at the close', 'gap',
               closes='the town general fund’s FY2026 period-13 budget report'),
    )
    # THE HUB IS THE CONCLUSIONS LAYER, AS A PYRAMID -- a test, 25 November 2026. TJ: "it just has
    # to give what they need to know" ... "we need more of a pyrmaid". The answer is the year in
    # one sentence; a range chart of the five readings; then four findings, known to new, each
    # linking to the one page that proves it; then the sections. No account numbers and no
    # circuit breaker mechanics: those are a level down. The email chain is one quiet clause
    # (TJ: "use it as subtle context"). The reversed figure is never offered as the 'real'
    # surplus: the vote was net of circuit breaker money, so reversing leaves planned money
    # unused (TJ: "that's a different type of problem").
    import build_fy2026_school_surplus as SP
    sf = SP.data()
    if not near(sf['left'], left26):
        fail('FY2026 school surplus and the hub disagree on what was left')
    if not near(sf['left25'], owed25):
        fail('FY2026 school surplus and the hub disagree on FY2025, counted the same way')
    charged, rev_ = sf['charged'], sf['reversed']
    share = sf['share']
    pv, co = acct[SP.CB.PRIVATE], acct[SP.CB.COLLAB]
    if not (pv['available_budget'] > 0 > co['available_budget']):
        fail('private tuition no longer left money while collaborative ran past budget')
    link = lambda tid: dict(href=REG.path(tid), title=REG.TOPICS[tid][0])
    owed = {y: round(float(jd['left'][y] - jd['closed'][y]), 2) for y in (2023, 2024, 2025)}
    owed[2026] = left26
    base = max(owed[2023], owed[2024])
    # "about": the two years were $32,022 and $31,705, so the hub says it to the thousand, not
    # to the dollar (a figure to the dollar behind "about" reads as a typo).
    about = round(base, -3)
    if not all(abs(owed[y] - about) < 500 for y in (2023, 2024)):
        fail('FY2023 and FY2024 are no longer both within $500 of %s' % C.usd(about))
    def point(text, rests, figs, so, so_figs=None, allow=(), so_allow=(), to=None):
        c = LD.conclusion(text, rests, figs, allow, so=so, so_figures=so_figs, so_allow=so_allow)
        c['link'] = link(to)
        return c
    plan = float(sf['plan'])
    hx = dict(
        plan=f('h-plan', U(plan), 'circuit breaker the vote counted on for tuition', 'published'),
        charged=f('h-charged', U(float(charged)), 'charged to it, all on 29 June', 'published',
                  allow=('29 June',)),
        early=f('h-early', U(float(sf['early'])), '%s collaborative tuition, charged to %s'
                % (C.fy(2027), C.fy(2026)), 'published', {'a': F(2027), 'b': F(2026)}),
        snow=h['snow'],
    )
    co_over = -co['available_budget']
    if not (co_over == max(-r['available_budget'] for r in L[2026])):
        fail('collaborative tuition is no longer the largest overrun; finding three says it is')
    if not (plan > float(charged)):
        fail('finding two says the circuit breaker was charged less than the vote counted on')
    # THE HUB'S TOP, REWRITTEN IN THE REVIEW PASS (27 November 2026, T-VPW4S). TJ: "looks like
    # each of the sections is effectively the same. the summary at the top is longer than the
    # detailed sections." It had three blocks -- In short, The year in five paragraphs, What the
    # school year shows -- about 1,160 words leading on the same six figures three times. Now:
    # the two big numbers, the four years, and ONE bridge of the four pieces that make the
    # surplus, with three conclusions under it, each linking to the page that proves it. Every
    # piece stays its own step (TJ, 26 November 2026: "i dont wnt to see those 2 as 1 thing
    # that 'cancel'. each has to sit on its own merit").
    cats = {c['key']: c for c in load('fy26-school-surplus.json')['causes']['categories']}
    pv_left, co_over_ = pv['available_budget'], -co['available_budget']
    if not near(pv_left - co_over_, cats['tuition']['unspent'], 100):
        fail('private and collaborative no longer net to out-of-district tuition, within $100')
    if abs(pv['transfers_adjustments']) > 0.004 or abs(co['transfers_adjustments']) > 0.004:
        fail('a tuition line now carries a transfer; the hub says neither was moved')
    oth = [c for k, c in cats.items() if k != 'tuition']
    oth_under = round(sum(c['unspent'] for c in oth if c['unspent'] > 0), 2)
    oth_over = round(-sum(c['unspent'] for c in oth if c['unspent'] < 0), 2)
    # The category nets carry the tuition category net, which differs from the two accounts by a
    # few dollars of minor tuition lines; the bridge must foot to the cent, so the residue rides
    # on "other spending under" and is asserted small.
    resid = round(left26 - (pv_left - co_over_ + oth_under - oth_over), 2)
    if abs(resid) > 100:
        fail('the four pieces no longer make up the school surplus, within $100')
    oth_under = round(oth_under + resid, 2)
    early_ = float(sf['early'])
    upper_ = round(left26 + early_, 2)
    if not (w_cb + early_ > left26):
        fail('the hub says the two year-end entries moved more than the whole surplus')
    bridge = TB.chart(TP.bridge(
        'What the surplus is made of', ('On budget', 0),
        [('Private tuition under', pv_left), ('Collaborative tuition over', -co_over_),
         ('Other lines under', oth_under), ('Other lines over', -oth_over)],
        ('Left, %s' % C.fy(2026), left26), '$',
        note='School general fund, period 13, paid and still owed. Other lines are every other '
             'kind of spending, under and over kept apart.', note_allow=('13',)),
        place='lead',
        so=('Four separate misses, two each way; the surplus is what is left when they are added.',
            None, ()))
    # ---- IN SHORT, CONSOLIDATED (27 November 2026). TJ, on the first pass that deleted the three
    # summary blocks outright: "i said consolidate al the duplicate info, not remove it all". So
    # every distinct point from In short, The year in five paragraphs and What the school year
    # shows is kept, and each is said ONCE, here. Written for a reader with no context (TJ, 26
    # November 2026): every term in plain words where it first appears. Nothing states why a
    # line moved (rule 7); each paragraph names what would answer it where that is known.
    pv_all, pv_cb = {}, {}
    tu_all = {}
    for r in csv.DictReader(open(MUNIS, encoding='utf-8')):
        if (r['period'] == '13' and r['type'] == 'E' and r['fund'] in ('0100', '2640')
                and r['fiscal_year'] in ('2023', '2024', '2025', '2026')):
            y, v = int(r['fiscal_year']), float(r['ytd_expended'] or 0) + float(r['encumbrances'] or 0)
            if r['obj'] == '535019':
                pv_all[y] = pv_all.get(y, 0) + v
                if r['fund'] == '2640':
                    pv_cb[y] = pv_cb.get(y, 0) + v
            if r['obj'] in ('535019', '535022', '535023'):
                tu_all[y] = tu_all.get(y, 0) + v
    tu_all = {y: round(v, 2) for y, v in tu_all.items()}
    if sorted(pv_all) != [2023, 2024, 2025, 2026] or sorted(tu_all) != [2023, 2024, 2025, 2026]:
        fail('tuition across both funds needs FY2023-FY2026 at period 13')
    pv_spent = pv['ytd_expended'] + pv['encumbrances']
    co_spent = co['ytd_expended'] + co['encumbrances']
    if not near(pv_all[2026] - pv_cb.get(2026, 0), pv_spent):
        fail('the general fund half of private tuition no longer matches the line')
    if abs(pv_cb.get(2026, 0)) > 0.004:
        fail('In short says the circuit breaker paid no private tuition in FY2026')
    cb_sh = [round(100 * pv_cb.get(y, 0) / pv_all[y]) for y in (2023, 2024, 2025)]
    cb_lo, cb_hi = min(cb_sh), max(cb_sh)
    if not cb_lo > 0:
        fail('In short says the circuit breaker paid part of private tuition in FY2023-FY2025')
    if not all(tu_all[a_] < tu_all[b_] for a_, b_ in ((2023, 2024), (2024, 2025), (2025, 2026))):
        fail('In short says tuition across both funds rose every year, FY2023-FY2026')
    if not near(tu_all[2026], pv_all[2026] + w_all, 1):
        fail('FY2026 tuition across both funds no longer equals private plus collaborative')
    t27 = load('fy26-school-surplus.json')['audit']['tuition']['lines']
    tu27 = round(t27['private']['fy27'] + t27['collab']['fy27'], 2)
    tu26_own = round(tu_all[2026] - early_, 2)
    pv_pct = 100 * pv_left / pv['revised_budget']
    co_pct = 100 * co_over_ / co['revised_budget']
    bldg, cnsl, tch = (cats[k]['unspent'] for k in ('buildings', 'counselors', 'teachers'))
    # Moved between funds (TJ, 28 November 2026): teacher cost moved OFF the general fund (negative),
    # para cost moved ON (positive); the paragraph below says so and would read wrong otherwise.
    te_bf, pa_bf_ = cats['teachers']['between_funds'], cats['paras']['between_funds']
    if te_bf is None or pa_bf_ is None or not (te_bf < 0 < pa_bf_) or not (tch + te_bf > 0):
        fail('The year in detail says reclasses moved teacher cost off and para cost on; they no longer do')
    hov = {c['key'] for c in oth if c['unspent'] < 0}
    if not (bldg > 0 and cnsl > 0 and tch > 0 and hov >= {'paras', 'sped_services', 'transport'}):
        fail('In short names upkeep, counselors and teachers under; paras, special-ed services and '
             'transportation over')
    wl = {x['id']: x['value'] for x in load('topics/why-it-was-left.json')['facts']}
    wf = lambda k: figure(wl[k]['value'], wl[k]['text'])
    m_ab = re.fullmatch(r'(\d+) of (\d+)', wl['above']['text'])
    m_fe = re.fullmatch(r'(\d+) of (\d+)', wl['fell']['text'])
    if not (m_ab and m_fe and m_ab.group(1) == m_ab.group(2) == m_fe.group(2)):
        fail('In short says every kind that left the most was budgeted above last year’s spending')
    nk, nf = int(m_ab.group(1)), int(m_fe.group(1))
    import build_fy2026_town_closeout as TC
    town_left = round(sum(r['available'] for r in TC.ledger()[2026] if r['dept'] not in TC.SCHOOL), 2)
    why = ('the payroll by position and date, which separates a post left vacant from every other '
           'cause, and the year’s grant award records')
    D = ('29 June', '30 June', '6 October')
    # IN SHORT IS SHORT (TJ, 27 November 2026: "we cannot use the phrase 'in short' and have 10
    # paragraps" ... "these paragraphs are the hub-level details that show below"). One line per
    # point, its figure in it; The year in detail, below the charts, says each in full.
    takeaways = TB.explain('In short', [
        ('Tuition missed both ways: private schools came in %s under budget, collaboratives %s over.'
         % (C.usd(pv_left), C.usd(co_over_)), {'a': U(pv_left), 'b': U(co_over_)}),
        ('Outside tuition, lines under budget left %s and lines over budget took %s.'
         % (C.usd(oth_under), C.usd(oth_over)), {'a': U(oth_under), 'b': U(oth_over)}),
        ('Some spending did not recur: %s vendors paid in both years before were paid %s less, '
         'net of every other route.' % (wl['nstop']['text'], wl['dropnet']['text']),
         {'n': wf('nstop'), 'd': wf('dropnet')}),
        ('Tuition, across both funds, rose every year: %s in %s, %s in %s.'
         % (C.usd(tu_all[2023]), C.fy(2023), C.usd(tu_all[2026]), C.fy(2026)),
         {'a': U(tu_all[2023]), 'b': F(2023), 'c': U(tu_all[2026]), 'd': F(2026)}),
        ('Two entries on %s and %s made the surplus smaller, by %s and %s.'
         % ('29 June', '30 June', C.usd(w_cb), C.usd(early_)),
         {'b': U(w_cb), 'c': U(early_)}, D),
        ('There is no deficit: what was left returns to the town’s general fund.', None),
    ], place='lead', tone='callout')
    detail = TB.explain('The year in detail', [
        ('**Tuition for students placed outside Lunenburg’s schools missed its budget badly, in '
         'both directions.** Private special education schools were budgeted at %s and cost %s: %s '
         'under, %s. Collaboratives (programs run jointly by several districts) were budgeted at %s '
         'and the school budget paid %s: %s over, %s. Each is its own miss; no transfer covered '
         'one with the other.'
         % (C.usd(pv['revised_budget']), C.usd(pv_spent), C.usd(pv_left), C.pct(pv_pct, 0),
            C.usd(co['revised_budget']), C.usd(co_spent), C.usd(co_over_), C.pct(co_pct, 0)),
         {'a': U(pv['revised_budget']), 'b': U(pv_spent), 'c': U(pv_left), 'd': P(pv_pct, 0),
          'e': U(co['revised_budget']), 'f': U(co_spent), 'g': U(co_over_), 'h': P(co_pct, 0)}),
        ('**Outside tuition, the kinds of spending that finished under left %s, and the ones that '
         'ran over took %s.** Building upkeep left %s, counselors and psychologists %s and teachers '
         '%s; paraprofessionals, special education contracted services and transportation ran over.'
         % (C.usd(oth_under), C.usd(oth_over), C.usd(bldg), C.usd(cnsl), C.usd(tch)),
         {'a': U(oth_under), 'b': U(oth_over), 'c': U(bldg), 'd': U(cnsl), 'e': U(tch)}),
        ('**Part of both staff figures is money moved between funds.** Journal reclasses moved %s of '
         'teacher cost from the general fund to other school funds, and %s of paraprofessional cost '
         'onto it; without those moves teachers left %s and paraprofessionals ran %s over. The '
         'journal shows the moves, not why they were made.'
         % (C.usd(-te_bf), C.usd(pa_bf_), C.usd(tch + te_bf), C.usd(-cats['paras']['unspent'] - pa_bf_)),
         {'a': U(-te_bf), 'b': U(pa_bf_), 'c': U(tch + te_bf), 'd': U(-cats['paras']['unspent'] - pa_bf_)}),
        ('**What the budget assumed, and the ledger does not show.** All %s kinds of spending that '
         'left the most were budgeted above what they spent the year before, and %s then spent less '
         'again; building upkeep was budgeted %s above its %s spending. A psychologist account and a '
         'social worker account posted no payroll in months that paid %s the year before, and %s '
         'vendors paid in both of the two years before were paid %s less, after every other route the money could have taken. '
         'Why is an open question; what would answer it: %s.'
         % (C.num(nk), C.num(nf), wl['upk']['text'], C.fy(2025), wl['lost']['text'],
            wl['nstop']['text'], wl['dropnet']['text'], why),
         {'k': N(nk), 'f': N(nf), 'u': wf('upk'), 'y': F(2025), 'l': wf('lost'), 'n': wf('nstop'),
          'd': wf('dropnet')}),
        ('**Tuition costs more every year.** It is paid from two places: the school budget, and the '
         'circuit breaker, the state’s reimbursement for high-cost special education. Counting both, '
         'it rose from %s in %s to %s, %s and %s in %s. The circuit breaker paid none of the private '
         'school tuition in %s, after paying %s–%s of it in each of the three years before.'
         % (C.usd(tu_all[2023]), C.fy(2023), C.usd(tu_all[2024]), C.usd(tu_all[2025]),
            C.usd(tu_all[2026]), C.fy(2026), C.fy(2026), str(cb_lo), C.pct(cb_hi, 0)),
         {'a': U(tu_all[2023]), 'b': F(2023), 'c': U(tu_all[2024]), 'd': U(tu_all[2025]),
          'e': U(tu_all[2026]), 'f': F(2026), 'g': figure(cb_lo, str(cb_lo)),
          'h': figure(cb_hi, C.pct(cb_hi, 0))}),
        ('**Two accounting entries in the year’s last two days both made the surplus smaller.** On '
         '%s, %s of collaborative tuition already charged to the school budget was moved onto the '
         'circuit breaker, where the budget had planned %s; the Town Manager questioned it in '
         'writing, and it still stood on %s. On %s, %s of next year’s (%s) tuition bills were '
         'charged to %s and paid in July. %s budgets this tuition at %s; %s spent %s on it, not '
         'counting the bills paid early.'
         % ('29 June', C.usd(w_cb), C.usd(plan), '6 October', '30 June', C.usd(early_), C.fy(2027),
            C.fy(2026), C.fy(2027), C.usd(tu27), C.fy(2026), C.usd(tu26_own)),
         {'b': U(w_cb), 'p': U(plan), 'c': U(early_), 'd': F(2027), 'e': F(2026), 'f': U(tu27),
          'g': U(tu26_own)}, D),
        ('**There is no deficit.** The school budget as a whole stayed under, and what was left '
         'returns to the town’s general fund. The town’s own departments closed %s %s under budget.'
         % (C.fy(2026), C.usd(town_left)), {'y': F(2026), 't': U(town_left)}),
    ], place='lead', tone='plain', links=[
        (REG.TOPICS['fy2026-tuition-lines'][0], REG.path('fy2026-tuition-lines')),
        (REG.TOPICS['fy2026-tuition-paid-early'][0], REG.path('fy2026-tuition-paid-early')),
        (REG.TOPICS['why-it-was-left'][0], REG.path('why-it-was-left')),
        (REG.TOPICS['fy2026-staff-lines'][0], REG.path('fy2026-staff-lines')),
        (REG.category('fy2026-town-closeout')['title'], REG.path('fy2026-town-closeout'))])

    # THE FOUR YEARS, at the top (TJ, 25 November 2026: "FY 25 was an anomaly and it was a huge
    # problem for the town you have to look before FY 25"). Same footing every year: orders still
    # owed at the close counted as spent. The reversal is not drawn: it is a possible event with
    # its own consequences, on the surplus page, never a reading of the surplus (TJ: "the
    # reversal is a distraction").
    if not (min(owed[2025], owed[2026]) > 10 * base):
        fail('the four-year chart says FY2025 and FY2026 each left over ten times FY2023-FY2024')
    years = [C.fy(y) for y in sorted(owed)]
    four = TB.chart(TP.series(
        'School budget left at year end', years,
        [TP.track('Left unspent, orders owed counted as spent', [owed[y] for y in sorted(owed)],
                  'published', 'bar')], '$', kind='bar',
        note='School general fund, closed-year reports, the same footing every year. Earlier years '
             'are not held.'),
        place='lead',
        so=('Two years landed within about %s of budget; the next two left more than ten times '
            'that.' % C.usd(about), {'b': U(about)}, ()))


    # THE TWO NUMBERS (TJ, 25 November 2026: "the official surplus in a big number, and the
    # upper-end surplus number if you count the prepay"). The first is the period-13 report's own
    # figure; the second is our sum, the same figure with next year's invoices left to next year,
    # and is drawn as ours. The reversal of the 29 June entry is not a reading (TJ: "the reversal
    # is a distraction") and is not drawn.
    upper = round(left26 + float(sf['early']), 2)
    if not near(upper, float(sf['no_prepay'])):
        fail('the upper figure no longer matches the surplus page’s own sum')
    big_ = TB.custom('big-figures', 'The school surplus', dict(figures=[
        dict(value=C.usd(left26), kind='published', tag='Official, the Town’s closed-year report',
             label='left unspent in the school budget, %s' % C.fy(2026)),
        dict(value=C.usd(upper), kind='estimate', tag='Our sum',
             label='if the %s of %s invoices charged to %s had waited for %s'
                   % (C.usd(float(sf['early'])), C.fy(2027), C.fy(2026), C.fy(2027)))]),
        place='lead', figures=(C.usd(left26), C.usd(upper), C.usd(float(sf['early'])),
                               C.fy(2026), C.fy(2027)),
        alt='The FY2026 school surplus: the official figure, and the higher figure with next '
            'year’s invoices left to next year.',
        so=('The official figure is what the year closed on. The higher one is our sum: the '
            'same ledger, with the year’s last tuition payment left to the year it was for.',
            None, ()))
    owed25 = float(sf['left25'])
    if not upper > owed25:
        fail('the big figures say FY2026 without the prepayment left more than FY2025')
    big = TB.claims(big_, [point(
        'Had the %s bills waited, %s would have left %s, more than %s’s %s.'
        % (C.fy(2027), C.fy(2026), C.usd(upper), C.fy(2025), C.usd(owed25)),
        ['h-up', 'h-25'], {'y': F(2027), 'z': F(2026), 'u': U(upper), 'x': F(2025), 'a': U(owed25)},
        'The official figure fell from %s; counted for its own year, the surplus grew.'
        % C.fy(2025), so_figs={'x': F(2025)}, to='fy2026-tuition-paid-early')], [
        f('h-up', U(upper), 'left, had those invoices waited (our sum)', 'estimate'),
        f('h-25', U(owed25), 'left in %s, counted the same way' % C.fy(2025), 'published',
          {'y': F(2025)})])

    # Each section of the hub is a noun and a figure (TJ: no sentences for the categories). The
    # figures are computed here, or read from the payload that computes them, never typed.
    burn = {x['id']: x for x in load('topics/budget-burndown.json')['facts']}['m26']
    if burn['label']['text'] != 'left at end of March, FY2026':
        fail('Budget burndown’s FY2026 March figure has moved; re-read it for the section label')
    group_figures = {
        'How big': '%s left' % C.usd(left26),
        'Tuition': '%s past budget, collaborative' % C.usd(co_over_),
        'Where it was left': '%s left on lines under budget' % C.usd(under26),
        'When': '%s left at the end of March' % burn['value']['text'],
        'Controls': '%s moved in by transfer' % C.usd(gross_in),
    }
    if set(group_figures) != {g for g, _ in REG.category(HUB)['groups']}:
        fail('the section figures no longer name the registry’s sections')

    out[HUB] = TP.hub(
        HUB,
        'This is the school budget’s year end. Before %s it finished within about %s of budget; '
        '%s left %s, the second year in a row far above that.'
        % (C.fy(2025), C.usd(about), C.fy(2026), C.usd(left26)),
        None, blocks=[big, takeaways, four, bridge, detail],
        answer_figures={'z': F(2025), 'b': U(about), 'y': F(2026), 'a': U(left26)})
    out[HUB]['group_figures'] = group_figures

    if sorted(k for k in out if k != HUB) != sorted(MINE):
        fail('the pages built are not the pages the registry gives this script: %s'
             % sorted(set(MINE) ^ set(out)))
    return out


# ------------------------------------------------ why it was left
# TJ, 26 October 2026: the candidate causes are "really huge potential conclusions" and belong
# on the hub. Each row is what the ledger MEASURES for one candidate; none states a cause,
# because no document does (rule 7). Category nets are build_school_surplus.py's own table,
# so this block and Surplus by category cannot disagree.
SALARY_CATS = ('teachers', 'counselors', 'paras', 'admin', 'custodians', 'athletics_staff',
               'nurses', 'reserve', 'details')
OVER_CATS = ('sped_services', 'transport', 'utilities')
GRANT_QUOTE = 'taking certain tuitions out of the grants'


def why_it_was_left(L, left26, JS):
    import build_school_surplus as SS
    J = JS.J
    U = lambda v: figure(v, C.usd(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    by = {y: {c['key']: c for c in SS.causes(L[y])} for y in (2023, 2024, 2025, 2026)}
    c26 = by[2026]
    if not near(sum(c['unspent'] for c in c26.values()), left26):
        fail('the category table no longer sums to what FY2026 left')
    net = lambda keys: round(sum(c26[k]['unspent'] for k in keys), 2)
    sal, over3 = net(SALARY_CATS), net(OVER_CATS)
    upkeep = net(('buildings', 'supplies'))
    aides = round(c26['paras']['over'], 2)
    ben = c26['benefits']['unspent']
    ben23, ben24 = by[2023]['benefits']['unspent'], by[2024]['benefits']['unspent']
    if not (ben > 0 > ben23 and ben24 < 0):
        fail('benefits no longer ran over in FY2023 and FY2024 and under in FY2026')
    # The areas under budget in every year held: Repeat underspending's six.
    every = sorted(k for k in c26 if all(by[y].get(k, {}).get('unspent', 0) > 0 for y in by))
    if every != sorted(['teachers', 'counselors', 'custodians', 'buildings', 'athletics',
                        'supplies']):
        fail('the areas under every year are no longer Repeat underspending\'s six: %s' % every)

    acct = lambda desc: [r for r in L[2026] if r['description'] == desc]
    priv, coll = acct('SPED TUITIONS-PRIVATE'), acct('COLLABORATIVE TUITIONS')
    if len(priv) != 1 or len(coll) != 1:
        fail('expected one private and one collaborative tuition account in FY2026')
    priv, coll = priv[0], coll[0]
    if max(L[2026], key=lambda r: r['available_budget']) is not priv:
        fail('private tuition is no longer the school account with the largest leftover')

    actual = [r for r in J.lines() if J.COLUMN_OF[r['source']] == 'actual']
    may = lambda fy, gf: round(float(sum(r['amt'] for r in actual if r['fy'] == fy
                                         and 'MAY INST' in r['vendor'].upper()
                                         and (r['fund'] == '0100') == gf)), 2)
    may25_gf, may26_grant = may(2025, True), may(2026, False)
    if not all(r['fund_name'].endswith('#240') for r in actual if r['fy'] == 2026
               and 'MAY INST' in r['vendor'].upper() and r['fund'] != '0100'):
        fail('May Institute was paid in FY2026 from a fund other than the general fund and IDEA')
    early = round(float(sum(r['amt'] for r in actual if r['fy'] == 2026 and r['fund'] == '0100'
                            and r['vendor'].startswith('FLLAC')
                            and (r['doc_no'] or '').startswith('27L2KEY'))), 2)
    if not near(early, 189276.75):
        fail('the year-end FLLAC payment is no longer the Year-end tuition payment page\'s')
    import glob
    cap = glob.glob(os.path.join(ROOT, 'sources', 'data', 'youtube-transcripts',
                                 'school-committee', '2026-09-16-*.json'))
    if len(cap) != 1 or not TP.verbatim_in(GRANT_QUOTE, JS._captions(cap[0])):
        fail('the 16 September 2026 grants remark is no longer in the captions')

    rows = [
        TB.check_row(
            'A federal grant paid a private placement',
            ('Private tuition left %s of %s. May Institute, paid %s by the general fund in %s, '
             'was paid %s by the special education grant in %s. Said in September: “%s”.'
             % (C.usd(priv['available_budget']), C.usd(priv['revised_budget']),
                C.usd(may25_gf), C.fy(2025), C.usd(may26_grant), C.fy(2026), GRANT_QUOTE),
             {'a': U(priv['available_budget']), 'b': U(priv['revised_budget']),
              'c': U(may25_gf), 'y': F(2025), 'd': U(may26_grant), 'z': F(2026)}),
            {0}),
        TB.check_row(
            'Collaborative tuition ran past budget',
            ('%s past, with no transfer in. %s of it paid invoices numbered for %s, on 30 June '
             '(Year-end tuition payment).'
             % (C.usd(-coll['available_budget']), C.usd(early), C.fy(2027)),
             {'a': U(-coll['available_budget']), 'b': U(early), 'y': F(2027)}, ('30 June',)),
            {1}),
        TB.check_row(
            'Salary lines, taken together',
            ('%s left net, after aides ran %s past budget. A vacancy, a leave and a budget set '
             'above pay look the same in a ledger.' % (C.usd(sal), C.usd(-aides)),
             {'a': U(sal), 'b': U(-aides)}),
            {0, 1, 2}),
        TB.check_row(
            'Building upkeep and supplies',
            ('%s left. In dollars, upkeep was further behind its usual March pace than any other '
             'area (Budget burndown); no document records a decision to hold it.' % C.usd(upkeep),
             {'a': U(upkeep)}),
            {0, 2}),
        TB.check_row(
            'Health insurance and benefits',
            ('%s left; in %s and %s the same lines ran %s and %s past budget.'
             % (C.usd(ben), C.fy(2023), C.fy(2024), C.usd(-ben23), C.usd(-ben24)),
             {'a': U(ben), 'y': F(2023), 'z': F(2024), 'b': U(-ben23), 'c': U(-ben24)}),
            {0}),
        TB.check_row(
            'Therapy, buses and electricity',
            ('%s past budget, net. Contracted therapy and electricity were voted below their '
             'spending in all four years held (the year’s school surplus page).' % C.usd(-over3),
             {'a': U(-over3)}),
            {1, 2}),
    ]
    vals = dict(priv=priv['available_budget'], priv_budget=priv['revised_budget'],
                may25=may25_gf, may26=may26_grant)
    return vals, TB.checks(
        'Why it was left', ['Left money', 'Used money', 'Same every year'], rows,
        place='body', first='What the ledger shows', second='Measured',
        note=('School accounts at the %s close, counting orders still owed; with the smaller '
              'lines they net to %s. A ledger records payments, never the reason for one. The '
              'September remark is from machine captions of the School Committee, a finding aid.'
              % (C.fy(2026), C.usd(left26)), {'y': F(2026), 'a': U(left26)}),
        so=('The leftover has several sources, not one. Over half of the largest account’s was '
            'a change of payer, not a cut; the steadiest sit in areas under budget every year.'))


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
        print('fy2026-closeout topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
