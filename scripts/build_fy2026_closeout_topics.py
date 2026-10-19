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
SRC25 = '/data/fy25-school-surplus.json'
HUB = 'fy2026-closeout'

MINE = [t for t, (_, home, gen) in REG.TOPICS.items()
        if home == HUB and gen == 'build_fy2026_closeout_topics.py']


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

    # ---- FY2026 school surplus
    told = S['stated']
    out['fy2026-school-surplus'] = TP.page(
        'fy2026-school-surplus',
        'The school general fund closed %s with %s unspent and uncommitted, %s of its budget.'
        % (C.fy(2026), C.usd(left26), C.pct(left_pct)),
        [fx['rev26'], fx['paid26'], fx['enc26'], fx['left26'], fx['leftpct'], fx['ceiling'],
         f('p12', U(p12['available']), 'the same figure in the June report (period 12)',
           'published', allow=('12',)),
         f('moved', U2(moved), 'change between the two runs', 'published'),
         f('told', U(told['returned_fy25']), 'returned the year before, as the Committee '
           'heard in July', 'published'),
         f('fate', None, 'whether each open order is paid or released', 'gap',
           closes='the Town Accountant’s list of FY2026 encumbrances carried into FY2027, '
                  'by account'),
         f('free-cash', None, 'what reaches the town as certified free cash', 'gap',
           closes='the state’s FY2026 free cash certification for Lunenburg')],
        [con('The school budget closed %s with %s left, %s of %s.'
             % (C.fy(2026), C.usd(left26), C.pct(left_pct), C.usd(rev26)),
             ['rev26', 'paid26', 'left26', 'leftpct'],
             {'y': F(2026), 'a': U(left26), 'p': P(left_pct), 'b': U(rev26)}),
         con('Another %s is committed to open orders; released in full, the figure reaches %s.'
             % (C.usd(enc26), C.usd(ceiling)), ['enc26', 'ceiling', 'fate'],
             {'e': U(enc26), 'c': U(ceiling)},
             notes=[step('Paid, an order leaves the figure where it is; released, it raises it. '
                         'The ledger shows the commitment, not its fate.', 'gap',
                         closes='the Town Accountant’s list of FY2026 encumbrances carried '
                                'into FY2027, by account')]),
         con('Between the September and October runs the figure moved %s; no payment changed.'
             % usd2(moved), ['p12', 'moved'], {'m': U2(moved)}),
         con('In July the Committee heard it would be well below about %s; %s is below it, '
             '%s above.' % (C.usd(told['returned_fy25']), C.usd(left26), C.usd(ceiling)),
             ['told', 'left26', 'ceiling'],
             {'t': U(told['returned_fy25']), 'a': U(left26), 'c': U(ceiling)})],
        chart=dict(id='fy26-school-surplus-waterfall', source=SRC26),
        table=dict(caption='The school general fund, %s, two runs of one report' % C.fy(2026),
                   views=[dict(
                       key='runs', label='Period 12 and period 13', total_col=-1,
                       kinds=['ledger'] * 2,
                       columns=['June report (period 12)', 'Closed year (period 13)'],
                       rows=[dict(label=lab, cells=[usd2(p12[a]), usd2(s26[b])])
                             for lab, a, b in (
                                 ('Voted', 'original', 'original_approp'),
                                 ('Moved by transfer, net', 'transfers', 'transfers_adjustments'),
                                 ('Budget after transfers', 'revised', 'revised_budget'),
                                 ('Paid', 'expended', 'ytd_expended'),
                                 ('Still committed', 'encumbered', 'encumbrances'),
                                 ('Left unspent', 'available', 'available_budget'))],
                       note='MUNIS year-to-date budget reports for department 300, run 1 '
                            'September and 6 October 2026. Left is the report’s own column: '
                            'budget less paid less still committed.')]),
        said=[said_file('school-committee/2026-07-29-minutes-7930.txt',
                        'the approximately $600,000 that had been returned', 'School Committee'),
              said_file('school-committee/2026-07-29-minutes-7930.txt',
                        'he was confident the remaining amount would be well below that figure',
                        'School Committee')],
        sources=[src['p13-26'], src['p12'], src['sc0729'], src['d-munis'], src['d-ledger']],
        finding_figures={'y': F(2026), 'a': U(left26), 'p': P(left_pct)})
    if told['returned_fy25'] != 600000.0:
        fail('the July minutes figure in the payload changed')

    # ---- Surplus by category
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
    out['fy2026-surplus-by-category'] = TP.page(
        'fy2026-surplus-by-category',
        'Accounts under budget left %s and accounts over used %s of it; the net is %s.'
        % (C.usd(under26), C.usd(-over[2026][1]), C.usd(left26)),
        [f('under', U(under26), 'left on accounts that came in under', 'published'),
         f('over', U(-over[2026][1]), 'spent past budget on the accounts that went over',
           'published'),
         f('bldg', U(b['unspent']), 'left on building and grounds upkeep', 'published'),
         f('bldg-pct', P(b['pct_of_revised']), 'of the upkeep budget left', 'published'),
         f('couns', U(cs['unspent']), 'left on counselors and psychologists, net', 'published'),
         f('teach', U(te['unspent']), 'left on teachers and substitutes, net', 'published'),
         f('teach-pct', P(te['pct_of_revised']), 'of the teacher budget left', 'published'),
         f('paras', U(pa['unspent']), 'paraprofessionals, net (over budget)', 'published'),
         f('disc', U(disc['unspent']), 'left in supplies, upkeep, equipment and the like (ours)',
           'estimate'),
         f('disc-pct', P(disc['share_pct']), 'of the surplus in those lines (our grouping)',
           'estimate'),
         f('why', None, 'what any dollar was bought, or when', 'gap',
           closes='the school general fund journal by month, from the Town Accountant')],
        [con('The %s is a net: %s left on some accounts, %s spent past others.'
             % (C.usd(left26), C.usd(under26), C.usd(-over[2026][1])),
             ['under', 'over', 'paras'],
             {'a': U(left26), 'u': U(under26), 'o': U(-over[2026][1])}),
         con('Building upkeep left the most, %s of its budget; teachers left %s of theirs.'
             % (C.pct(b['pct_of_revised']), C.pct(te['pct_of_revised'])),
             ['bldg', 'bldg-pct', 'teach', 'teach-pct', 'couns'],
             {'b': P(b['pct_of_revised']), 't': P(te['pct_of_revised'])}),
         con('By our grouping, %s of the surplus sat in lines a decision to buy less moves.'
             % C.pct(disc['share_pct']), ['disc', 'disc-pct', 'why'],
             {'p': P(disc['share_pct'])},
             notes=[step('A hold on purchasing fits. So do orders slipping past year end, '
                         'lines budgeted high, and other funds paying. The ledger cannot tell '
                         'them apart.', 'hypothesis'),
                    step('Which lines count as discretionary is our judgement, not the '
                         'district’s.', 'gap',
                         closes='a statement by the district of which FY2026 purchases it '
                                'held back, and when')])],
        chart=dict(id='fy26-school-surplus-causes', source=SRC26),
        table=dict(caption='Where the %s school surplus was left, by category' % C.fy(2026),
                   views=[dict(
                       key='categories', label='Department 300, period 13', total_col=3,
                       kinds=['ledger'] * 4,
                       columns=['Budget after transfers', 'Paid', 'Still committed', 'Left'],
                       rows=[dict(label=c['label'], cells=[
                           C.usd(c['revised']), C.usd(c['expended']), C.usd(c['encumbered']),
                           C.usd(c['unspent'])]) for c in S['causes']['categories']]
                       + [dict(label='All categories', cells=[
                           C.usd(rev26), C.usd(paid26), C.usd(enc26), C.usd(left26)])],
                       note='Every account is placed in one category by its DESE function and '
                            'object code. The categories are ours; the figures are the '
                            'ledger’s.')]),
        sources=[src['p13-26'], src['d-munis']],
        finding_figures={'u': U(under26), 'o': U(-over[2026][1]), 'a': U(left26)})

    # ---- Lines over budget
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
    out['fy2026-lines-over-budget'] = TP.page(
        'fy2026-lines-over-budget',
        '%s school accounts closed %s past their budgets; in %s, %s did.'
        % (C.num(over[2026][0]), C.fy(2026), C.fy(2025), C.num(over[2025][0])),
        [f('n26', N(over[2026][0], 'accounts'), 'accounts past budget at the %s close'
           % C.fy(2026), 'published', {'y': F(2026)}),
         f('amt26', U(-over[2026][1]), 'by how much, together', 'published'),
         f('n25', N(over[2025][0], 'accounts'), 'accounts past budget, %s' % C.fy(2025),
           'published', {'y': F(2025)}),
         f('n24', N(over[2024][0], 'accounts'), 'accounts past budget, %s' % C.fy(2024),
           'published', {'y': F(2024)}),
         f('n23', N(over[2023][0], 'accounts'), 'accounts past budget, %s' % C.fy(2023),
           'published', {'y': F(2023)}),
         f('notr', N(no_tr, 'accounts'), 'of the %s past budget, given no transfer in'
           % C.fy(2026), 'published', {'y': F(2026)}),
         f('top5', U(-top5_sum), 'past budget on the five largest overruns', 'published'),
         f('chron', U(chron), 'electricity and therapy, voted below spending, four years',
           'published'),
         f('elec27', U(ch['electricity']['fy27']), 'electricity, %s budget (district workbook)'
           % C.fy(2027), 'published', {'y': F(2027)}),
         f('elec26', U(ch['electricity']['paid26']), 'electricity, paid in %s' % C.fy(2026),
           'published', {'y': F(2026)})],
        [con('%s accounts closed %s past budget by %s; in %s, %s did.'
             % (C.num(over[2026][0]), C.fy(2026), C.usd(-over[2026][1]), C.fy(2025),
                C.num(over[2025][0])), ['n26', 'amt26', 'n25'],
             {'n': N(over[2026][0]), 'y': F(2026), 'a': U(-over[2026][1]), 'z': F(2025),
              'm': N(over[2025][0])}),
         con('%s and %s closed like %s, with %s and %s accounts over.'
             % (C.fy(2023), C.fy(2024), C.fy(2026), C.num(over[2023][0]), C.num(over[2024][0])),
             ['n23', 'n24', 'n26'],
             {'a': F(2023), 'b': F(2024), 'y': F(2026), 'n': N(over[2023][0]),
              'm': N(over[2024][0])},
             notes=[step('That %s’s transfers were a deliberate reconciliation after its '
                         'surplus became public is a hypothesis; nothing here records it.'
                         % C.fy(2025), 'hypothesis', {'z': F(2025)})]),
         con('%s of the %s accounts past budget received no transfer in during the year.'
             % (C.num(no_tr), C.num(over[2026][0])), ['notr', 'n26'],
             {'k': N(no_tr), 'n': N(over[2026][0])}),
         con('Electricity and contracted therapy were voted below their spending in all four '
             'years held, by %s.' % C.usd(chron), ['chron', 'elec27', 'elec26'],
             {'c': U(chron)},
             notes=[step('Buildings moving load from gas to electricity, rates, and the solar '
                         'arrangement all fit the electricity line; none is tested here.',
                         'hypothesis')])],
        chart=TP.series(
            'School accounts past budget at the close', [C.fy(fy) for fy in sorted(over)],
            [TP.track('Accounts past budget', [over[fy][0] for fy in sorted(over)],
                      'published', 'bar')],
            'accounts', kind='bar',
            note='Department 300, period 13 of each year: accounts whose own available column '
                 'closed below zero.', note_allow=('300', '13')),
        table=dict(caption='School accounts past their budgets at the close, by year', views=[
            dict(key='years', label='Department 300, period 13', total_col=-1,
                 kinds=['ledger'] * 3,
                 columns=['Accounts past budget', 'By how much', 'Transfers in, gross'],
                 rows=[dict(label=C.fy(fy), cells=[
                     C.num(over[fy][0]), C.usd(-over[fy][1]),
                     C.usd(by_year[fy]['transfers_in'])]) for fy in (2026, 2025, 2024, 2023)],
                 note='Past budget means the report’s own available column is below zero: '
                      'budget less paid less still committed.'),
            dict(key='top', label='The five largest, %s' % C.fy(2026), total_col=-1,
                 kinds=['ledger'] * 4,
                 columns=['Voted', 'Paid', 'Still committed', 'Past budget'],
                 rows=[dict(label=r['description'].capitalize(), cells=[
                     C.usd(r['original']), C.usd(r['spent']), C.usd(r['encumbered']),
                     C.usd(-r['available'])]) for r in top5],
                 note='Kindergarten aides had no budget and received no transfer. The '
                      'collaborative tuition line is read on its own page.')]),
        sources=[src['p13-26'], src['p13-25'], src['p13-24'], src['p13-23'], src['wb27'],
                 src['d-munis'], src['d-wb']],
        finding_figures={'n': N(over[2026][0]), 'y': F(2026), 'z': F(2025),
                         'm': N(over[2025][0])})

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
             notes=[step('The ledger is net per account and names no counterparty, so it '
                         'cannot say which transfer was which.', 'gap',
                         closes='the FY2026 transfer schedule by account, with the '
                                'counterparty and the vote for each')]),
         con('The 29 July minutes itemise ten transfers totalling %s, account by account.'
             % usd2(july), ['july'], {'j': U2(july)}, allow=('29 July',)),
         con('%s accounts were given %s by transfer and still closed with %s left.'
             % (C.num(len(given)), C.usd(g_in), C.usd(g_left)),
             ['given-n', 'given-in', 'given-left'],
             {'n': N(len(given)), 'i': U(g_in), 'l': U(g_left)}),
         con('School Committee dues got %s, minuted as for a search invoice, and closed with %s '
             'left.'
             % (C.usd(dues['transfers_adjustments']), C.usd(dues['available_budget'])),
             ['dues-in', 'dues-left'],
             {'i': U(dues['transfers_adjustments']), 'l': U(dues['available_budget'])},
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

    # ---- Surplus and FY2027 budget
    cut = A['fy27_cut']
    if not near(cut['level_service'] - cut['balanced'], cut['gap']):
        fail('the FY2027 level-service gap no longer foots')
    out['fy2026-surplus-and-fy2027'] = TP.page(
        'fy2026-surplus-and-fy2027',
        'The %s school budget was set %s below level service; %s then closed %s unspent.'
        % (C.fy(2027), C.usd(cut['gap']), C.fy(2026), C.usd(left26)),
        [f('level', U(cut['level_service']), '%s school budget, level service' % C.fy(2027),
           'published', {'y': F(2027)}),
         f('balanced', U(cut['balanced']), '%s school budget, the no-override budget'
           % C.fy(2027), 'published', {'y': F(2027)}),
         f('gap', U(cut['gap']), 'the difference between the two', 'published'),
         fx['left26'], fx['ceiling'],
         f('free-cash', None, 'what reaches the town as certified free cash', 'gap',
           closes='the state’s FY2026 free cash certification for Lunenburg')],
        [con('The %s school budget was set %s below level service.'
             % (C.fy(2027), C.usd(cut['gap'])), ['level', 'balanced', 'gap'],
             {'y': F(2027), 'g': U(cut['gap'])}),
         con('%s then closed with %s unspent, %s if every open order is released.'
             % (C.fy(2026), C.usd(left26), C.usd(ceiling)), ['left26', 'ceiling'],
             {'y': F(2026), 'a': U(left26), 'c': U(ceiling)}),
         con('The budget was drawn up months before the close; set side by side, neither '
             'explains the other.', ['gap', 'left26']),
         con('Unspent school money returns to the town; what is certified as free cash is not '
             'yet known.', ['left26', 'free-cash'],
             notes=[step('Whether any of it reaches the schools again is a Town Meeting '
                         'decision, and none is recorded here.', 'gap',
                         closes='the state’s FY2026 free cash certification for Lunenburg, and '
                                'the Town Meeting votes that appropriate it')])],
        chart=TP.ranking(
            'The cut beside the surplus',
            [('%s, below level service' % C.fy(2027), cut['gap']),
             ('%s, left unspent' % C.fy(2026), left26),
             ('%s, if every order is released' % C.fy(2026), ceiling)], '$',
            note='A budget and a ledger, set side by side and never subtracted: the budget was '
                 'drawn up months before the close.'),
        sources=[src['wb27'], src['p13-26'], src['d-wb'], src['d-munis']],
        finding_figures={'y': F(2027), 'g': U(cut['gap']), 'z': F(2026), 'a': U(left26)})

    # ---- FY2025 school surplus
    w25 = S25['waterfall']
    dist = w25['district_figure']
    diff25 = round(s25['available_budget'] - dist, 2)
    if not near(diff25, S25['diff'] if isinstance(S25['diff'], (int, float)) else
                S25['diff'].get('amount', diff25)):
        fail('the FY2025 gap against the district figure is not the payload’s')
    if s25['encumbrances'] != 0:
        fail('FY2025 now carries open purchase orders; the page says it carries none')
    pct25 = round(100 * s25['available_budget'] / s25['revised_budget'], 1)
    cats25 = {c['key']: c for c in S25['causes']['categories']}
    out['fy2025-school-surplus'] = TP.page(
        'fy2025-school-surplus',
        '%s closed with %s unspent, %s more than the figure the School Committee was given.'
        % (C.fy(2025), C.usd(s25['available_budget']), C.usd(diff25)),
        [f('rev25', U(s25['revised_budget']), 'school budget after transfers, %s' % C.fy(2025),
           'published', {'y': F(2025)}),
         f('out25', U(-s25['transfers_adjustments']), 'moved out of the school budget, net',
           'published'),
         f('paid25', U(s25['ytd_expended']), 'paid by the close', 'published'),
         f('left25', U(s25['available_budget']), 'left unspent at the close', 'published'),
         f('pct25', P(pct25), 'of the budget left unspent', 'published'),
         f('enc25', U(0), 'still committed', 'published'),
         f('dist', U2(dist), 'the figure the Committee was given, 17 September 2025',
           'published', allow=('17 September 2025',)),
         f('diff', U(diff25), 'the closed ledger above that figure (our arithmetic)',
           'estimate'),
         f('paras25', U(cats25['paras']['unspent']), 'left on paraprofessionals, %s'
           % C.fy(2025), 'published', {'y': F(2025)}),
         f('paras26', U(pa['unspent']), 'paraprofessionals, %s, net' % C.fy(2026),
           'published', {'y': F(2026)})],
        [con('%s closed with %s left, %s of its budget, and nothing still committed.'
             % (C.fy(2025), C.usd(s25['available_budget']), C.pct(pct25)),
             ['rev25', 'paid25', 'left25', 'pct25', 'enc25'],
             {'y': F(2025), 'a': U(s25['available_budget']), 'p': P(pct25)}),
         con('The Committee was told %s; the closed ledger shows %s more.'
             % (usd2(dist), C.usd(diff25)), ['dist', 'diff', 'left25'],
             {'d': U2(dist), 'x': U(diff25)},
             notes=[step('Entries posted after the September meeting fit; no single account '
                         'or pair of accounts makes up the gap, and this ledger cannot test '
                         'it.', 'hypothesis')]),
         con('Paraprofessionals left %s in %s; in %s they ran %s over.'
             % (C.usd(cats25['paras']['unspent']), C.fy(2025), C.fy(2026),
                C.usd(-pa['unspent'])), ['paras25', 'paras26'],
             {'a': U(cats25['paras']['unspent']), 'y': F(2025), 'z': F(2026),
              'b': U(-pa['unspent'])})],
        chart=dict(id='fy25-school-surplus-waterfall', source=SRC25),
        said=[said_file('school-committee/2025-09-17-minutes-7408.txt',
                        'the surplus number has gone up to $603,885.97, the change is due to '
                        'closing out purchase orders from FY25.', 'School Committee'),
              said_file('school-committee/2025-09-17-minutes-7408.txt',
                        'double booking of the para salaries, the music program and supply '
                        'line cuts', 'School Committee')],
        sources=[src['p13-25'], src['sc0917'], src['d-munis']],
        finding_figures={'y': F(2025), 'a': U(s25['available_budget']), 'x': U(diff25)})

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
        [con('Private tuition paid %s of its budget; collaborative tuition paid %s of its.'
             % (C.pct(priv_pct, 0), C.pct(coll_pct, 0)), ['priv-b', 'priv-p', 'coll-b', 'coll-p'],
             {'a': P(priv_pct, 0), 'b': P(coll_pct, 0)},
             notes=[step('A shift from private to collaborative placements fits; so do rate '
                         'changes, recoding, and budgets struck high or low. Placement counts '
                         'by year are not published.', 'hypothesis')]),
         con('%s budgets %s for the two lines; %s spent %s on them.'
             % (C.fy(2027), C.usd(tu['fy27']), C.fy(2026), C.usd(gf_tu_spent)),
             ['fy27', 'both', 'children'],
             {'y': F(2027), 'a': U(tu['fy27']), 'z': F(2026), 'b': U(gf_tu_spent)},
             notes=[step('Placements ending, more expected from the circuit breaker, and '
                         'FY2027 tuition prepaid from FY2026 money all fit. None is tested '
                         'here.', 'hypothesis', allow=('FY2027', 'FY2026'))]),
         con('The circuit breaker paid %s of tuition in %s, against %s in %s.'
             % (C.pct(cby[2026]['cb_share_pct']), C.fy(2026), C.pct(cby[2023]['cb_share_pct']),
                C.fy(2023)), ['cb26', 'cb-share26', 'cb-share23'],
             {'a': P(cby[2026]['cb_share_pct']), 'y': F(2026),
              'b': P(cby[2023]['cb_share_pct']), 'z': F(2023)},
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
        sources=[src['p13-26'], src['sp26'], src['wb27'], src['d-munis'], src['d-wb']],
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
    out['fy2026-paraprofessional-overrun'] = TP.page(
        'fy2026-paraprofessional-overrun',
        'Paraprofessional accounts ran %s over in %s; %s of it was paid against no budget.'
        % (C.usd(-pa['unspent']), C.fy(2026), C.usd(k_paid)),
        [f('rev', U(pa['revised']), 'paraprofessional budget after transfers, %s' % C.fy(2026),
           'published', {'y': F(2026)}),
         f('paid', U(pa['expended']), 'paid on paraprofessionals', 'published'),
         f('over', U(-pa['unspent']), 'over budget, net', 'published'),
         f('k-budget', U(0), 'kindergarten aides, budget and transfers', 'published'),
         f('k-paid', U2(k_paid), 'kindergarten aides, paid', 'published'),
         f('sp-n', N(len(sped_over), 'accounts'), 'special-education aide lines over, of %s'
           % C.num(len(sped)), 'published', {'n': N(len(sped))}),
         f('sp-over', U(-sped_net), 'those lines over budget, together', 'published'),
         f('sp-paid', U(sped_paid), 'special-education aides, paid, %s' % C.fy(2026),
           'published', {'y': F(2026)}),
         f('sp-27', U(cr['sped_paras_fy27']), 'the same aides, %s budget (district workbook)'
           % C.fy(2027), 'published', {'y': F(2027)}),
         f('k-27', U(A['kinder']['fy27']), 'kindergarten aides, %s budget' % C.fy(2027),
           'published', {'y': F(2027)})],
        [con('Paraprofessional accounts paid %s against %s budgeted, %s over.'
             % (C.usd(pa['expended']), C.usd(pa['revised']), C.usd(-pa['unspent'])),
             ['rev', 'paid', 'over'],
             {'p': U(pa['expended']), 'r': U(pa['revised']), 'o': U(-pa['unspent'])}),
         con('Two kindergarten aide accounts with no budget and no transfer paid %s.'
             % usd2(k_paid), ['k-budget', 'k-paid', 'k-27'], {'k': U2(k_paid)},
             notes=[step('A recoding, a grant expected to cover it, and an overrun awaiting a '
                         'transfer all fit. Nothing here chooses between them.', 'hypothesis'),
                    step('No document held connects the spending to a decision.', 'gap',
                         closes='the FY2026 year-end transfer schedule by account, with the '
                                'authority for each')]),
         con('All %s special-education aide lines closed over, by %s together.'
             % (C.num(len(sped)), C.usd(-sped_net)), ['sp-n', 'sp-over'],
             {'n': N(len(sped)), 'o': U(-sped_net)}),
         con('%s budgets those aides at %s; %s paid them %s.'
             % (C.fy(2027), C.usd(cr['sped_paras_fy27']), C.fy(2026), C.usd(sped_paid)),
             ['sp-27', 'sp-paid'],
             {'y': F(2027), 'a': U(cr['sped_paras_fy27']), 'z': F(2026), 'b': U(sped_paid)})],
        chart=TP.ranking(
            'Paraprofessional accounts past budget',
            [(r['description'].capitalize(), -r['available_budget']) for r in para_rows], '$',
            highlight=[r['description'].capitalize() for r in kinder],
            note='Function 2330, period 13: every account that paid anything closed over. The '
                 'two kindergarten accounts had no budget at all.', note_allow=('2330', '13')),
        table=dict(caption='Paraprofessional accounts that paid anything, %s' % C.fy(2026),
                   views=[dict(
                       key='paras', label='Function 2330, period 13', total_col=-1,
                       kinds=['ledger'] * 4,
                       columns=['Voted', 'Moved in, net', 'Paid', 'Left'],
                       rows=[dict(label=r['description'].capitalize(), cells=[
                           C.usd(r['original_approp']), C.usd(r['transfers_adjustments']),
                           C.usd(r['ytd_expended']), C.usd(r['available_budget'])])
                           for r in sorted([r for r in L[2026] if r['function'] == 2330
                                            and r['ytd_expended']],
                                           key=lambda r: r['available_budget'])],
                       note='A budget line is dollars, not people: a line over budget does not '
                            'say more aides were hired.')]),
        said=[said_file('school-committee/2026-07-29-minutes-7930.txt',
                        '$81,075.96 from the High School Special Education Resource Room '
                        'Teacher account to Hospital Tutoring and the ACE, Primary School, '
                        'Elementary School, Middle School and High School Special Education '
                        'Paraprofessional accounts to cover overages in those areas',
                        'School Committee')],
        sources=[src['p13-26'], src['wb27'], src['sc0729'], src['d-munis'], src['d-wb']],
        finding_figures={'o': U(-pa['unspent']), 'y': F(2026), 'k': U(k_paid)})

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
    out['fy2026-psychologist-line'] = TP.page(
        'fy2026-psychologist-line',
        'One of four school psychologist accounts, %s budgeted, paid nothing in %s.'
        % (C.usd(z['revised_budget']), C.fy(2026)),
        [f('z-b', U(z['revised_budget']), 'psychologist account %s, budget, %s'
           % (z['org'], C.fy(2026)), 'published', {'y': F(2026)}, allow=(z['org'],)),
         f('z-p', U(0), 'paid on it all year', 'published'),
         f('full', N(len(full), 'accounts'), 'other psychologist lines paid in full or over',
           'published'),
         f('z-27', U(A['psych']['fy27']), 'the same line, %s budget (district workbook)'
           % C.fy(2027), 'published', {'y': F(2027)}),
         f('soc', U(soc_left), 'left on the four social worker lines', 'published'),
         f('couns', U(cs['unspent']), 'left on counselors and psychologists, net', 'published'),
         f('paras', U(-pa['unspent']), 'paraprofessionals over budget, net, same year',
           'published'),
         f('post', None, 'whether the post was vacant, on leave, or paid elsewhere', 'gap',
           closes='the position-control roster by month, and payroll by account')],
        [con('One of four psychologist lines, %s budgeted, paid nothing all year.'
             % C.usd(z['revised_budget']), ['z-b', 'z-p', 'post'], {'b': U(z['revised_budget'])},
             notes=[step('A line paying nothing fits a vacancy, a leave, a person paid from '
                         'another account, or a coding change. The ledger shows dollars.',
                         'gap', closes='the position-control roster by month, and payroll '
                                       'by account')]),
         con('The other %s psychologist lines paid their budgets in full or slightly over.'
             % C.num(len(full)), ['full'], {'n': N(len(full))}),
         con('%s budgets the same line at %s.' % (C.fy(2027), C.usd(A['psych']['fy27'])),
             ['z-27'], {'y': F(2027), 'a': U(A['psych']['fy27'])}),
         con('Counselor and psychologist lines left %s while paraprofessionals ran %s over.'
             % (C.usd(cs['unspent']), C.usd(-pa['unspent'])), ['couns', 'paras', 'soc'],
             {'c': U(cs['unspent']), 'p': U(-pa['unspent'])},
             notes=[step('That one paid for the other is a hypothesis. Late hires, contract '
                         'steps and hours fit the same two numbers, and no headcount is '
                         'published.', 'hypothesis')])],
        chart=TP.series(
            'School psychologist accounts', ['Psychologist, %s' % r['org']
                                             for r in sorted(psy, key=lambda r: r['org'])],
            [TP.track('Budget', [r['revised_budget'] for r in sorted(psy, key=lambda r: r['org'])],
                      'published', 'bar'),
             TP.track('Paid', [r['ytd_expended'] for r in sorted(psy, key=lambda r: r['org'])],
                      'published', 'bar')],
            '$', kind='bar',
            note='Object 511023, one account per building, period 13. None received a transfer.',
            note_allow=('511023', '13')),
        table=dict(caption='Psychologist and social worker accounts, %s' % C.fy(2026),
                   views=[dict(
                       key='support', label='Objects 511023 and 511024, period 13',
                       total_col=-1, kinds=['ledger'] * 3,
                       columns=['Budget', 'Paid', 'Left'],
                       rows=[dict(label='%s (%s)' % (r['description'].capitalize(), r['org']),
                                  cells=[C.usd(r['revised_budget']), C.usd(r['ytd_expended']),
                                         C.usd(r['available_budget'])])
                             for r in sorted(psy + soc, key=lambda r: (r['obj'], r['org']))],
                       note='One account per building. None received a transfer in.')]),
        sources=[src['p13-26'], src['wb27'], src['d-munis'], src['d-wb']],
        finding_figures={'b': U(z['revised_budget']), 'y': F(2026)})

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
              'o': U(t_over_amt), 'm': N(len(t_over))}),
         con('%s of %s town accounts were over in June; %s of %s school accounts were.'
             % (C.num(len(t_over)), C.num(len(tw)), C.num(s_over12), C.num(len(p12s))),
             ['t-over', 't-n', 's-over'],
             {'a': N(len(t_over)), 'b': N(len(tw)), 'c': N(s_over12), 'd': N(len(p12s))},
             notes=[step('Tighter school budgets, readier town transfers, and different '
                         'coding all fit; nothing here separates them.', 'hypothesis')]),
         con('Two transfer accounts voted %s moved %s to capital and stabilization funds.'
             % (C.usd(tr_o), C.usd(tr_e)), ['tr-o', 'tr-e'], {'o': U(tr_o), 'e': U(tr_e)},
             notes=[step('The ledger records that these budgets grew, not what vote funded '
                         'the growth.', 'gap',
                         closes='the FY2026 Town Meeting votes funding the capital and '
                                'stabilization transfers')]),
         con('%s was still committed in June; released in full, the figure reaches %s.'
             % (C.usd(t['encumbered']), C.usd(t_ceiling)), ['t-enc', 't-ceil', 'p13'],
             {'e': U(t['encumbered']), 'c': U(t_ceiling)})],
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
             {'p': U(sn['expended']), 'o': U(sn['original']), 'r': U(sn['revised'])}),
         con('The wages line, %s budgeted, paid %s with no transfer in.'
             % (C.usd(wages['revised']), C.usd(wages['expended'])), ['w-b', 'w-p', 'w-pct'],
             {'b': U(wages['revised']), 'p': U(wages['expended'])}),
         con('The %s Reserve Fund paid nothing and moved nothing in the same year.'
             % C.usd(rf['original']), ['rf', 'rf-p', 'rb'], {'r': U(rf['original'])},
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
             notes=[step('Reading SCHRETHLTH as school retiree health insurance is ours, '
                         'from the account name.', 'gap',
                         closes='the Town Accountant’s chart of accounts naming account 570018',
                         allow=('570018',))]),
         con('The school ledger carries its own health insurance account: %s paid in %s.'
             % (C.usd(shi_paid), C.fy(2026)), ['shi'],
             {'s': U(shi_paid), 'y': F(2026)}),
         con('Whether any of the town’s other %s covers school staff is not split out.'
             % C.usd(rest), ['rest', 'hi', 'split'], {'r': U(rest)})],
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
    h = dict(
        left=fx['left26'], enc=fx['enc26'], leftpct=fx['leftpct'],
        under=f('h-under', U(under26), 'left on school accounts under budget', 'published'),
        over=f('h-over', U(-over[2026][1]), 'spent past budget on the rest', 'published'),
        n26=f('h-n26', N(over[2026][0], 'accounts'), 'school accounts past budget, %s'
              % C.fy(2026), 'published', {'y': F(2026)}),
        n25=f('h-n25', N(over[2025][0], 'accounts'), 'the same count, %s' % C.fy(2025),
              'published', {'y': F(2025)}),
        left25=f('h-left25', U(s25['available_budget']), 'left unspent at the %s close'
                 % C.fy(2025), 'published', {'y': F(2025)}),
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
    tiers = [
        LD.tier('What was left', [h['left'], h['leftpct'], h['enc'], h['left25'], h['town']]),
        LD.tier('What moved inside it', [h['under'], h['over'], h['n26'], h['n25'], h['tuit'],
                                         h['kind'], h['snow']]),
        LD.tier('What is not settled', [h['counter'], h['tp13']]),
    ]
    mx = LD.matrix(
        [('school', 'School department'), ('town', 'Town departments')],
        [('left', 'What was left'), ('moved', 'What moved'), ('open', 'Not settled')],
        {('school', 'left'): ['left26', 'leftpct', 'enc26', 'h-left25'],
         ('town', 'left'): ['h-town'],
         ('school', 'moved'): ['h-under', 'h-over', 'h-n26', 'h-n25', 'h-tuit', 'h-kind'],
         ('town', 'moved'): ['h-snow'],
         ('school', 'open'): ['h-counter'], ('town', 'open'): ['h-tp13']})
    hub_ladder = LD.ladder(tiers, [
        LD.conclusion('The school general fund closed %s with %s left, %s of its budget.'
                      % (C.fy(2026), C.usd(left26), C.pct(left_pct)),
                      ['left26', 'leftpct', 'enc26'],
                      {'y': F(2026), 'a': U(left26), 'p': P(left_pct)}),
        LD.conclusion('That is a net: %s left on some accounts, %s spent past others.'
                      % (C.usd(under26), C.usd(-over[2026][1])), ['h-under', 'h-over'],
                      {'u': U(under26), 'o': U(-over[2026][1])}),
        LD.conclusion('%s school accounts closed past budget; in %s, %s did.'
                      % (C.num(over[2026][0]), C.fy(2025), C.num(over[2025][0])),
                      ['h-n26', 'h-n25'],
                      {'n': N(over[2026][0]), 'z': F(2025), 'm': N(over[2025][0])}),
        LD.conclusion('Kindergarten aides were paid %s with no budget and no transfer.'
                      % C.usd(k_paid), ['h-kind'], {'k': U(k_paid)}),
        LD.conclusion('In June the town stood %s under; snow removal had paid %s.'
                      % (C.usd(t['available']), C.usd(sn['expended'])), ['h-town', 'h-snow',
                                                                          'h-tp13'],
                      {'t': U(t['available']), 's': U(sn['expended'])}),
    ], matrix=mx)
    out[HUB] = TP.hub(
        HUB,
        'The school general fund closed %s with %s unspent, %s of its budget, at period 13. '
        'Town departments stood %s under in June, before their close.'
        % (C.fy(2026), C.usd(left26), C.pct(left_pct), C.usd(t['available'])),
        hub_ladder, chart=dict(id='fy26-school-surplus-waterfall', source=SRC26),
        answer_figures={'y': F(2026), 'a': U(left26), 'p': P(left_pct), 't': U(t['available'])},
        answer_allow=('13',))

    if sorted(k for k in out if k != HUB) != sorted(MINE):
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
