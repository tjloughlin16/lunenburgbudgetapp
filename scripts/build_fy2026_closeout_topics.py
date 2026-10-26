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
    out['fy2026-surplus-by-category'] = TP.page(
        'fy2026-surplus-by-category',
        'Accounts under budget left %s and accounts over used %s of it; the net is %s.'
        % (C.usd(under26), C.usd(-over[2026][1]), C.usd(left26)),
        [f('under', U(under26), 'left on accounts that came in under', 'published'),
         f('over', U(-over[2026][1]), 'spent past budget on the accounts that went over',
           'published'),
         f('bldg', U(b['unspent']), 'left on building and grounds upkeep', 'published'),
         f('bldg-pct', P(b['pct_of_revised']), 'of the upkeep budget left', 'published'),
         f('teach-pct', P(te['pct_of_revised']), 'of the teacher budget left', 'published'),
         f('disc-pct', P(disc['share_pct']), 'of the surplus in supplies, upkeep and such (ours)', 'estimate'),
         f('n26', N(over[2026][0], 'accounts'), 'accounts past budget at the %s close'
           % C.fy(2026), 'published', {'y': F(2026)}),
         f('n25', N(over[2025][0], 'accounts'), 'accounts past budget, %s' % C.fy(2025),
           'published', {'y': F(2025)}),
         f('notr', N(no_tr, 'accounts'), 'of the %s past budget, given no transfer in'
           % C.fy(2026), 'published', {'y': F(2026)}),
         f('paras', U(-pa['unspent']), 'paraprofessionals over budget, net', 'published'),
         f('chron', U(chron), 'electricity and therapy, voted below spending, four years',
           'published'),
         f('why', None, 'why any line came in under or over', 'gap',
           closes='the district’s line-by-line budget build-up, with the basis for each line')],
        [con('The %s is a net: %s left on some accounts, %s spent past others.'
             % (C.usd(left26), C.usd(under26), C.usd(-over[2026][1])),
             ['under', 'over', 'paras'],
             {'a': U(left26), 'u': U(under26), 'o': U(-over[2026][1])},
             so='A small net sat on large misses both ways, so how closely lines were budgeted '
                'shows in the two halves, not in the total.'),
         con('Building upkeep left %s of its budget; teachers left %s of theirs.'
             % (C.pct(b['pct_of_revised']), C.pct(te['pct_of_revised'])),
             ['bldg', 'bldg-pct', 'teach-pct', 'disc-pct', 'why'],
             {'b': P(b['pct_of_revised']), 't': P(te['pct_of_revised'])},
             so='Salaries landed close to budget. The leftover sits in a few non-salary lines, '
                'which a decision to buy less moves.',
             notes=[step('A hold on purchasing fits. So do orders slipping past year end, '
                         'lines budgeted high, and other funds paying. The ledger cannot tell '
                         'them apart.', 'hypothesis')]),
         con('%s accounts closed %s past budget; %s had %s, %s %s, and %s only %s.'
             % (C.num(over[2026][0]), C.fy(2026), C.fy(2023), C.num(over[2023][0]), C.fy(2024),
                C.num(over[2024][0]), C.fy(2025), C.num(over[2025][0])),
             ['n26', 'n25', 'notr'],
             {'n': N(over[2026][0]), 'y': F(2026), 'a': F(2023), 'b': N(over[2023][0]),
              'c': F(2024), 'd': N(over[2024][0]), 'z': F(2025), 'm': N(over[2025][0])},
             so='%s is the unusual year, not %s: most years close with dozens of lines covered '
                'from the ones that left money.' % (C.fy(2025), C.fy(2026)),
             so_figures={'z': F(2025), 'y': F(2026)},
             notes=[step('%s of the %s received no transfer in during the year.'
                         % (C.num(no_tr), C.num(over[2026][0])), 'measured',
                         {'k': N(no_tr), 'n': N(over[2026][0])}),
                    step('That %s’s transfers were a deliberate reconciliation after its '
                         'surplus became public is a hypothesis; nothing here records it.'
                         % C.fy(2025), 'hypothesis', {'z': F(2025)})]),
         con('Electricity and contracted therapy were voted below their spending in all four '
             'years held, by %s.' % C.usd(chron), ['chron'],
             {'c': U(chron)},
             so='Each year those lines are paid from leftovers elsewhere in the same budget; '
                'voting them nearer their cost shrinks both halves.',
             notes=[step('%s budgets electricity at %s; %s spent or owed %s on it.'
                         % (C.fy(2027), C.usd(ch['electricity']['fy27']), C.fy(2026),
                            C.usd(ch['electricity']['spent26'])), 'measured',
                         {'y': F(2027), 'a': U(ch['electricity']['fy27']), 'z': F(2026),
                          'b': U(ch['electricity']['spent26'])}),
                    step('Buildings moving load from gas to electricity, rates, and the solar '
                         'arrangement all fit the electricity line; none is tested here.',
                         'hypothesis')])],
        chart=dict(id='fy26-school-surplus-causes', source=SRC26),
        blocks=[TB.panels('The two halves of the net', [
            TB.panel('Left under budget', [
                ('All accounts under', C.usd(under26), None),
                ('Building and grounds upkeep', C.usd(b['unspent']), None),
                ('Counselors and psychologists', C.usd(cs['unspent']), None),
                ('Teachers and substitutes', C.usd(te['unspent']), None)]),
            TB.panel('Spent past budget', [
                ('All accounts over', C.usd(-over[2026][1]), 'bad'),
                ('The five largest overruns', C.usd(-top5_sum), 'bad'),
                ('Paraprofessionals, net', C.usd(-pa['unspent']), 'bad'),
                ('Accounts over with no transfer in', C.num(no_tr), None)])],
            place='chart',
            so='The surplus is what was left after the right-hand card was paid out of the '
               'left-hand one, inside one appropriation.')],
        also=[TP.series(
            'School accounts past budget at the close', [C.fy(fy) for fy in sorted(over)],
            [TP.track('Accounts past budget', [over[fy][0] for fy in sorted(over)],
                      'published', 'bar')],
            'accounts', kind='bar',
            note='Department 300, period 13 of each year: accounts whose own available column '
                 'closed below zero.', note_allow=('300', '13'))],
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
        tables=[dict(caption='School accounts past their budgets at the close, by year', views=[
            dict(key='years', label='Department 300, period 13', total_col=-1,
                 kinds=['ledger'] * 3,
                 columns=['Accounts past budget', 'By how much', 'Transfers in, gross'],
                 rows=[dict(label=C.fy(fy), cells=[
                     C.num(over[fy][0]), C.usd(-over[fy][1]),
                     C.usd(by_year[fy]['transfers_in'])]) for fy in (2026, 2025, 2024, 2023)],
                 note='Past budget means the report’s own available column is below zero: '
                      'budget less paid less still committed.')]),
            dict(caption='The five largest overruns, %s' % C.fy(2026), views=[
            dict(key='top', label='Department 300, period 13', total_col=-1,
                 kinds=['ledger'] * 4,
                 columns=['Voted', 'Paid', 'Still committed', 'Past budget'],
                 rows=[dict(label=r['description'].capitalize(), cells=[
                     C.usd(r['original']), C.usd(r['spent']), C.usd(r['encumbered']),
                     C.usd(-r['available'])]) for r in top5],
                 note='Kindergarten aides had no budget and received no transfer. The '
                      'collaborative tuition line is read on its own page.')])],
        sources=[src['p13-26'], src['p13-25'], src['p13-24'], src['p13-23'], src['wb27'],
                 src['d-munis'], src['d-wb']],
        finding_figures={'u': U(under26), 'o': U(-over[2026][1]), 'a': U(left26)})

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
             {'p': U(pa['expended']), 'r': U(pa['revised']), 'o': U(-pa['unspent'])},
             so='The largest overrun in the school budget, covered from lines that left money, '
                'so it does not show in the net.'),
         con('Two kindergarten aide accounts with no budget and no transfer paid %s.'
             % usd2(k_paid), ['k-budget', 'k-paid', 'k-27'], {'k': U2(k_paid)},
             so='Money was spent where none was voted or moved, and the %s budget again carries '
                '%s for these accounts.' % (C.fy(2027), C.usd(A['kinder']['fy27'])),
             so_figures={'y': F(2027), 'z': U(A['kinder']['fy27'])},
             notes=[step('A recoding, a grant expected to cover it, and an overrun awaiting a '
                         'transfer all fit. Nothing here chooses between them.', 'hypothesis'),
                    step('No document held connects the spending to a decision.', 'gap',
                         closes='the FY2026 year-end transfer schedule by account, with the '
                                'authority for each')]),
         con('All %s special-education aide lines closed over, by %s together.'
             % (C.num(len(sped)), C.usd(-sped_net)), ['sp-n', 'sp-over'],
             {'n': N(len(sped)), 'o': U(-sped_net)},
             so='Every line ran over, not one, a pattern across the service rather than one '
                'account’s surprise.'),
         con('%s budgets those aides at %s; %s paid them %s.'
             % (C.fy(2027), C.usd(cr['sped_paras_fy27']), C.fy(2026), C.usd(sped_paid)),
             ['sp-27', 'sp-paid'],
             {'y': F(2027), 'a': U(cr['sped_paras_fy27']), 'z': F(2026), 'b': U(sped_paid)},
             so='Set side by side, the next budget can be read against what these aides cost '
                'this year.')],
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
             so='A budgeted post paid nothing all year, money the budget counted on spending and '
                'did not, without the ledger saying why.',
             notes=[step('A line paying nothing fits a vacancy, a leave, a person paid from '
                         'another account, or a coding change. The ledger shows dollars.',
                         'gap', closes='the position-control roster by month, and payroll '
                                       'by account')]),
         con('The other %s psychologist lines paid their budgets in full or slightly over.'
             % C.num(len(full)), ['full'], {'n': N(len(full))},
             so='The line that paid nothing is the exception, not a pattern across the service.'),
         con('%s budgets the same line at %s.' % (C.fy(2027), C.usd(A['psych']['fy27'])),
             ['z-27'], {'y': F(2027), 'a': U(A['psych']['fy27'])},
             so='Whether the post is filled in the new year decides whether this money is spent '
                'or left again.'),
         con('Counselor and psychologist lines left %s while paraprofessionals ran %s over.'
             % (C.usd(cs['unspent']), C.usd(-pa['unspent'])), ['couns', 'paras', 'soc'],
             {'c': U(cs['unspent']), 'p': U(-pa['unspent'])},
             so='Within one appropriation the two roughly offset; the net hides both.',
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
    tiers = [
        LD.tier('What was left', [h['left'], h['leftpct'], h['enc'], h['left25'], fx['ceiling'],
                                  fx['gap27'], h['town']]),
        LD.tier('What moved inside it', [h['under'], h['over'], h['priv'], h['grant'], h['n26'],
                                         h['n25'], h['tuit'],
                                         h['kind'], h['snow']]),
        LD.tier('What is not settled', [h['counter'], h['tp13']]),
    ]
    mx = LD.matrix(
        [('school', 'School department'), ('town', 'Town departments')],
        [('left', 'What was left'), ('moved', 'What moved'), ('open', 'Not settled')],
        {('school', 'left'): ['left26', 'leftpct', 'enc26', 'h-left25', 'ceiling', 'gap27'],
         ('town', 'left'): ['h-town'],
         ('school', 'moved'): ['h-under', 'h-over', 'h-priv', 'h-grant', 'h-n26', 'h-n25',
                               'h-tuit', 'h-kind'],
         ('town', 'moved'): ['h-snow'],
         ('school', 'open'): ['h-counter'], ('town', 'open'): ['h-tp13']})
    hub_ladder = LD.ladder(tiers, [
        LD.conclusion('Counting orders still owed, the school general fund ended %s with %s '
                      'left, %s of its budget.' % (C.fy(2026), C.usd(left26), C.pct(left_pct)),
                      ['left26', 'leftpct', 'enc26', 'h-left25'],
                      {'y': F(2026), 'a': U(left26), 'p': P(left_pct)},
                      so='Counted the same way %s left %s. As printed the two years are on '
                         'different footings; Surplus by year draws both.'
                         % (C.fy(2025), C.usd(owed25)),
                      so_figures={'y': F(2025), 'a': U(owed25)}),
        LD.conclusion('That is a net: %s left on some accounts, %s spent past others.'
                      % (C.usd(under26), C.usd(-over[2026][1])), ['h-under', 'h-over'],
                      {'u': U(under26), 'o': U(-over[2026][1])},
                      so='A small net sat on large misses both ways, so how closely lines were '
                         'budgeted shows in the halves, not the total.'),
        LD.conclusion('%s school accounts closed past budget; in %s, %s did.'
                      % (C.num(over[2026][0]), C.fy(2025), C.num(over[2025][0])),
                      ['h-n26', 'h-n25'],
                      {'n': N(over[2026][0]), 'z': F(2025), 'm': N(over[2025][0])},
                      so='%s is the unusual year: %s and %s closed with %s and %s accounts past '
                         'budget.' % (C.fy(2025), C.fy(2023), C.fy(2024), C.num(over[2023][0]),
                                      C.num(over[2024][0])),
                      so_figures={'z': F(2025), 'a': F(2023), 'b': F(2024),
                                  'c': N(over[2023][0]), 'd': N(over[2024][0])}),
        LD.conclusion('Kindergarten aides were paid %s with no budget and no transfer.'
                      % C.usd(k_paid), ['h-kind'], {'k': U(k_paid)},
                      so='Money was spent where none was voted or moved, and the %s budget '
                         'again carries %s for these accounts.'
                         % (C.fy(2027), C.usd(A['kinder']['fy27'])),
                      so_figures={'y': F(2027), 'z': U(A['kinder']['fy27'])}),
        LD.conclusion('Private tuition left %s, the largest leftover; a federal grant paid %s of its bills.'
                      % (C.usd(wv['priv']), C.usd(wv['may26'])), ['h-priv', 'h-grant'],
                      {'a': U(wv['priv']), 'g': U(wv['may26'])},
                      so='The general fund paid that school %s in %s. Over half the leftover was a '
                         'change of payer, not a cut; no record says why.'
                         % (C.usd(wv['may25']), C.fy(2025)),
                      so_figures={'m': U(wv['may25']), 'y': F(2025)}),
        LD.conclusion('In June the town stood %s under; snow removal had paid %s.'
                      % (C.usd(t['available']), C.usd(sn['expended'])), ['h-town', 'h-snow',
                                                                          'h-tp13'],
                      {'t': U(t['available']), 's': U(sn['expended'])},
                      so='Snow ran far past its vote and the town still stood under in June; '
                         'its close, not yet held, settles the year.'),
    ], matrix=mx)
    out[HUB] = TP.hub(
        HUB,
        'The school general fund ended %s with %s unspent, %s of its budget, counting orders '
        'still owed. Counted the same way, %s left %s. Town departments stood %s under in June.'
        % (C.fy(2026), C.usd(left26), C.pct(left_pct), C.fy(2025), C.usd(owed25),
           C.usd(t['available'])),
        hub_ladder, chart=dict(id='fy26-school-surplus-waterfall', source=SRC26), table=runs_table,
        blocks=[why_left],
        answer_figures={'y': F(2026), 'a': U(left26), 'p': P(left_pct), 'z': F(2025),
                        'b': U(owed25), 't': U(t['available'])})

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
               'other_staff')
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
             'spending in all four years held (Surplus by category).' % C.usd(-over3),
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
