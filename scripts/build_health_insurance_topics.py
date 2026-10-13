#!/usr/bin/env python3
"""Health insurance, split into topic pages: ten pages and the hub.

    python3 scripts/build_health_insurance_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_health_insurance_topics.py --check   # fail if any output would change

WHAT THIS ABSORBS. /health-insurance-what-it-costs (the cost: what sits in the town's
insurance department, what is named for the schools, how fast it grows) and /health-insurance
(the lever: what Chapter 32B lets the town change, every town's spending, the PEC history).
School retiree insurance at the FY2026 year end (fy2026-closeout) and the employee benefits
group of the omnibus (department-budgets) are listed on this shelf and written elsewhere.

IT COMPUTES NOTHING NEW THAT IT CAN READ INSTEAD, and refuses to write when its sources stop
agreeing where they are supposed to:

  fy28/public/data/health-insurance.json  build_insurance_charts.py: the town's insurance
                                          department (914) account by account at FY2026
                                          period 12, the annual reports' insurance blocks
                                          FY2011-FY2023 tied to their printed subtotals, and
                                          the district book's health line by stage.
  fy28/public/data/health-options.json    build_health_options.py: the c.32B menu, one row a
                                          section, and DLS Schedule A health insurance
                                          spending for every municipality.
  fy28/public/data/model.json             model/health.py: the FY2027 premiums, read from the
                                          Town's rate letter of 21 April 2026 -- re-checked
                                          here against our text of that letter.
  sources/data/gl-history.csv             extract_gl_history.py: the Finance Committee's
                                          general fund history FY2010-FY2025. RULE 13a: a
                                          workbook ASSEMBLED from MUNIS exports, `stated`.
                                          Used only where it ties to a printed figure, and
                                          the ties are asserted below.
  sources/data/pec-history.csv            the PEC history; quotes re-checked verbatim.
  sources/contracts/txt/pec-agreement-fy27-fy29.txt   the 2026-2029 memorandum, read for
                                          its percentages and its end date.

TWO JUDGEMENT CALLS, both measured rather than chosen:

  1. REVISED, NOT ORIGINAL. The annual report's `appropriated` column equals the ledger
     history's REVISED budget to the cent in every year both hold (asserted), and FY2026's
     revised equals its original at period 12 (asserted). So the department's growth is
     revised to revised, one stage throughout -- rule 1.
  2. THE STATE'S FIGURE CHANGED WHAT IT COUNTS. DLS's health insurance spending for
     Lunenburg equals the insurance department's ACTUALS LESS MEDICARE AND LIFE INSURANCE,
     within $5, in every year FY2010-FY2023; for FY2024 it equals the WHOLE department,
     Medicare and life included, to the dollar. Asserted below, so the page stops if either
     tie breaks. Why it changed is not shown (rule 7): it is a hypothesis note, never a cause.

RULE 7 / THE OPEN QUESTION. Whether the town's own active-employee HEALTH INS line covers any
school staff is NOT settled anywhere here. Only two accounts are named for the schools.

Every option's savings is unknown: the statute says what is permitted, never what it saves.
No savings figure appears on these pages.
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
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT_DIR = os.path.join(PUB, 'topics')
DATA = os.path.join(ROOT, 'sources', 'data')
MANIFEST = os.path.join(DATA, 'archive-manifest.csv')
MINUTES = os.path.join(ROOT, 'sources', 'meetings', 'text')
RATE_LETTER = os.path.join(ROOT, 'sources', 'town-supplementary', 'text',
                           'health-insurance-rates-2025.txt')
MOA = os.path.join(ROOT, 'sources', 'contracts', 'txt', 'pec-agreement-fy27-fy29.txt')
CID = 'health-insurance'
CAP = 2.5       # checked against model.json's levy_growth below

MINE = [t for t, (_, home, gen) in REG.TOPICS.items()
        if home == CID and gen == 'build_health_insurance_topics.py']


def fail(msg):
    raise SystemExit('build_health_insurance_topics: ' + msg)


def load(name):
    return json.load(open(os.path.join(PUB, name), encoding='utf-8'))


def norm(s):
    return ' '.join((s or '').split())


def cagr(a, b, n):
    return ((b / a) ** (1.0 / n) - 1) * 100


def said_file(rel, quote, board):
    """A quotation asserted here, verbatim, against our copy of the minutes."""
    text = norm(open(os.path.join(MINUTES, rel), encoding='utf-8').read())
    if norm(quote) not in text:
        fail('quote is not verbatim in %s: %r' % (rel, quote))
    date = re.search(r'(\d{4}-\d{2}-\d{2})', rel).group(1)
    return dict(quote=quote, board=board, date=date,
                href='/docs/minutes/text/' + rel, label='%s minutes, %s' % (board, date))


def sources():
    man = {r['key'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    spec = {
        'p12': ('town-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.xlsx',
                'Town of Lunenburg — Town Accountant (MUNIS), general fund, FY2026 period 12'),
        'rates': ('town-supplementary/docs/health-insurance-rates-2025.pdf',
                  'Town of Lunenburg — Payroll & Benefits Coordinator, “Health Insurance / Open '
                  'Enrollment - July 1, 2026”, 21 April 2026'),
        'moa': ('contracts/pdf/pec-agreement-fy27-fy29.pdf',
                'Memorandum of Agreement, Town of Lunenburg and Lunenburg Public Employee '
                'Committee, 1 July 2026 to 30 June 2029 (records request)'),
        'glx': ('budget-workbooks/finance-committee/fy26-budget/'
                'general-fund-budget-vs-actuals-history.xlsx',
                'Lunenburg Finance Committee — general fund budget vs actuals history, '
                'FY2010-FY2025 (assembled from MUNIS exports)'),
        'ar23': ('town-budget/pages/FY2023.txt',
                 'Town of Lunenburg — FY2023 annual town report, budget pages (our text)'),
        'book': ('district-budget/docs/final-budget-document.pdf',
                 'Lunenburg Public Schools — FY27 budget document, 25 March 2026'),
    }
    out = {}
    for k, (key, label) in spec.items():
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        out[k] = dict(label=label, href='/docs/' + key)
    for k, f, what in (('gl', 'gl-history.csv', 'the Finance Committee’s ledger history, by account'),
                       ('dls', 'dls-health-insurance.csv',
                        'DLS Schedule A health insurance spending, every municipality'),
                       ('law', 'health-insurance-law.csv',
                        'what Chapter 32B permits and forbids, one row a section'),
                       ('pec', 'pec-history.csv', 'the PEC agreement’s history, quoted')):
        if not os.path.exists(os.path.join(ROOT, 'fy28', 'public', 'docs', 'data', f)):
            fail('/docs/data/%s is not published' % f)
        out[k] = dict(label='Lunenburg Budget Project — %s (%s)' % (f, what),
                      href='/docs/data/' + f)
    out['hi'] = dict(label='Lunenburg Budget Project — health-insurance.json (the insurance '
                           'department and the district line, by stage)',
                     href='/data/health-insurance.json')
    out['ho'] = dict(label='Lunenburg Budget Project — health-options.json (the c.32B menu and '
                           'every town’s spending)', href='/data/health-options.json')
    out['dlsweb'] = dict(label='Massachusetts Division of Local Services — Health Insurance '
                               'Expenditures (Schedule A)',
                         href='https://dls-gw.dor.state.ma.us/reports/rdPage.aspx?rdReport='
                              'ScheduleA.HealthInsurance.HealthInsExpenditures')
    out['mgl'] = dict(label='M.G.L. Chapter 32B — municipal group insurance (malegislature.gov)',
                      href='https://malegislature.gov/Laws/GeneralLaws/PartI/TitleIV/Chapter32B')
    return out


def gl_914():
    """The insurance department in the ledger history: {fy: {object: row}}."""
    out = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'gl-history.csv'), encoding='utf-8')):
        if r['sheet'] == 'general_fund' and r['department_code'] == '914':
            out.setdefault(int(r['fiscal_year']), {})[r['object']] = dict(
                original=float(r['original']), revised=float(r['revised']),
                actual=float(r['actual']), partial=r['actual_is_partial'] == 'true')
    if sorted(out) != list(range(2010, 2026)):
        fail('the ledger history no longer holds department 914 for FY2010-FY2025')
    return out


def dls_lunenburg():
    out = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'dls-health-insurance.csv'), encoding='utf-8')):
        if r['municipality'] == 'Lunenburg' and r['expenditure'] != '':
            out[int(r['fy'])] = float(r['expenditure'])
    return out


# --------------------------------------------------------------------- the pages

def build():
    HI = load('health-insurance.json')
    HO = load('health-options.json')
    MODEL = load('model.json')
    src = sources()
    if abs(MODEL['assumptions']['levy_growth'] * 100 - CAP) > 1e-9:
        fail('the model’s levy growth is no longer 2.5%')

    U = lambda v: figure(v, C.usd(v))
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    OF = lambda a, b, unit=None: figure(a, '%s of %s' % (C.num(a), C.num(b)), unit)
    FYF = lambda y: figure(y, 'FY%d' % y)
    f, con = LD.fact, TP.conclusion
    out = {}

    L = HI['ledger']
    ACC = {a['account_id']: a for a in L['accounts']}
    if (L['fy'], L['period'], L['dept']) != (2026, 12, '914') or not L['reconciles_department_row']:
        fail('the ledger block is no longer department 914 at FY2026 period 12, reconciled')
    for a in ACC.values():
        if abs(a['revised'] - a['original']) > 0.005:
            fail('%s: FY2026 revised no longer equals original at period 12' % a['account_id'])
    SR = ACC['0100-19142-570018']
    TR = ACC['0100-19142-570009']
    HA = ACC['0100-19142-570001']
    MED = ACC['0100-19142-570003']
    if (SR['printed'], TR['printed'], HA['printed'], MED['printed']) != (
            'SCHRETHLTH', 'TNRETHLTHI', 'HEALTH INS', 'MEDI'):
        fail('the FY2026 insurance accounts are no longer printed as they were')
    dept26 = L['total_original']
    G = gl_914()

    # ------------------------------------------------ the insurance department
    R = HI['reports']
    years = {y['fy']: y for y in R['years']}
    checked = [y for y in R['checked']]
    for y in checked:
        rev = sum(r['revised'] for r in G[y].values())
        if abs(rev - years[y]['printed_total']) > 0.01:
            fail('FY%d: the annual report’s appropriated total no longer equals the ledger '
                 'history’s revised budget' % y)
    tc = HI['town_change']
    if (tc['first_fy'], tc['last_fy']) != (2011, 2026):
        fail('the department series no longer runs FY2011-FY2026')
    rate_dept = tc['cagr'] * 100
    if abs(rate_dept - cagr(tc['first'], dept26, 15)) > 1e-6:
        fail('health-insurance.json’s department rate no longer reproduces')
    sr_share = 100 * SR['original'] / dept26
    named = SR['original'] + TR['original']
    unnamed = dept26 - named
    rev = {y: sum(r['revised'] for r in G[y].values()) for y in G}
    out['health-insurance-department'] = TP.page(
        'health-insurance-department',
        'The town’s insurance department grew %s a year, FY2011 to FY2026, against a %s levy '
        'cap.' % (C.pct(rate_dept), C.pct(CAP)),
        [f('d11', U(tc['first']), 'appropriated, FY2011, as the annual report prints',
           'published', allow=('FY2011',)),
         f('d26', U(dept26), 'budgeted, FY2026, the town ledger', 'published', allow=('FY2026',)),
         f('rate', P(rate_dept), 'a year, FY2011 to FY2026', 'published',
           allow=('FY2011', 'FY2026')),
         f('cap', P(CAP), 'a year the levy may rise, before new growth', 'statute'),
         f('tied', OF(len(checked), R['editions'], 'annual reports'),
           'reports whose insurance rows sum to their printed total', 'published'),
         f('sr', P(sr_share), 'of FY2026 in one account named for school retirees',
           'published', allow=('FY2026',)),
         f('unnamed', U(unnamed), 'FY2026 in accounts named for neither side', 'published',
           allow=('FY2026',)),
         f('why', None, 'why the department grew', 'gap',
           closes='premiums, enrolment by plan and the number of retirees, year by year')],
        [con('The department grew %s a year for fifteen years, faster than the %s the levy may '
             'rise.' % (C.pct(rate_dept), C.pct(CAP)), ['d11', 'd26', 'rate', 'cap'],
             {'a': P(rate_dept), 'b': P(CAP)},
             notes=[step('Premiums, who is enrolled and the number of retirees all move this '
                         'line; none is printed beside it.', 'gap',
                         closes='the town’s Chapter 32B enrollment schedule, by year',
                         allow=('32B',))]),
         con('In FY2026, %s of the department sat in the one account named for school retirees.'
             % C.pct(sr_share), ['sr', 'unnamed'], {'a': P(sr_share)}, allow=('FY2026',)),
         con('Apart from the two retiree accounts, %s carries no name saying town or school.'
             % C.usd(unnamed), ['unnamed', 'why'], {'a': U(unnamed)})],
        table=dict(caption='The insurance department, by year', views=[dict(
            key='dept', label='Revised budget', total_col=0, kinds=['stated', 'ledger'],
            columns=['Ledger history', 'Annual report prints'],
            rows=[dict(label='FY%d' % y, cells=[
                C.usd(rev[y]) if y in rev else C.usd(dept26),
                C.usd(years[y]['printed_total']) if y in checked else None])
                  for y in sorted(list(rev) + [2026], reverse=True)],
            note='The ledger history is the Finance Committee’s workbook, assembled from MUNIS '
                 'exports; it equals the annual report in every year the report’s insurance '
                 'rows tie. FY2026 is the MUNIS ledger at period 12.')]),
        sources=[src['hi'], src['ar23'], src['p12'], src['gl'], src['glx']],
        finding_figures={'a': P(rate_dept), 'b': P(CAP)},
        finding_allow=('FY2011', 'FY2026'))

    # ------------------------------------------------ the schools' health insurance
    S = HI['school']
    if not S['district_book_agrees']:
        fail('the district book no longer agrees with the ledger’s school HEALTH INS')
    if abs(S['retiree_original'] - SR['original']) > 0.005:
        fail('the school retiree figure disagrees between two blocks of health-insurance.json')
    act, tot, app = S['active']['original'], S['total_original'], S['appropriation']
    if abs(act + SR['original'] - tot) > 0.01:
        fail('the two school-named accounts no longer sum to the school total')
    ret_share = 100 * S['retiree_share_of_appropriation']
    out['school-health-insurance'] = TP.page(
        'school-health-insurance',
        'Two school accounts hold %s for FY2026; %s of it sits outside the school '
        'budget.' % (C.usd(tot), C.usd(SR['original'])),
        [f('act', U(act), 'school department HEALTH INS, FY2026 budget', 'published',
           allow=('FY2026',)),
         f('ret', U(SR['original']), 'SCHRETHLTH, in the town’s insurance department',
           'published'),
         f('tot', U(tot), 'the two accounts together', 'published'),
         f('app', U(app), 'the FY2026 school appropriation', 'published', allow=('FY2026',)),
         f('share', P(ret_share), 'the retiree account, set beside that appropriation',
           'published'),
         f('town-act', U(HA['original']), 'the town’s own HEALTH INS line, FY2026', 'published',
           allow=('FY2026',)),
         f('med', U(MED['original']), 'Medicare, the employer’s share, FY2026', 'published',
           allow=('FY2026',)),
         f('whose', None, 'school staff inside the town’s HEALTH INS or Medicare', 'gap',
           closes='the town’s Chapter 32B enrollment schedule, by department')],
        [con('The district’s book and the town ledger agree: %s on the school HEALTH INS line.'
             % C.usd(act),
             ['act'], {'a': U(act)}),
         con('School retiree health, %s, is appropriated to the town, not to the schools.'
             % C.usd(SR['original']), ['ret', 'app', 'share'], {'a': U(SR['original'])},
             notes=[step('A budget line is dollars; it does not say how many retirees it covers '
                         'or on which plans.', 'gap',
                         closes='the number of school retirees enrolled, by plan')]),
         con('Whether any of the town’s %s HEALTH INS line covers school staff is not split out.'
             % C.usd(HA['original']), ['town-act', 'med', 'whose'], {'a': U(HA['original'])})],
        table=dict(caption='Health insurance accounts named for the schools', views=[dict(
            key='school', label='FY2026', total_col=0, kinds=['ledger', 'ledger'],
            columns=['Budget', 'Account'],
            rows=[dict(label='School department HEALTH INS', cells=[C.usd(act),
                                                                    S['active']['account_id']]),
                  dict(label='School retirees (town insurance department)',
                       cells=[C.usd(SR['original']), SR['account_id']]),
                  dict(label='Together', cells=[C.usd(tot), None])],
            note='Budgets as the MUNIS ledger prints them at period 12. Accounts not named for '
                 'either side are left out, not assigned.')]),
        sources=[src['hi'], src['p12'], src['book']],
        finding_figures={'a': U(tot), 'b': U(SR['original'])}, finding_allow=('FY2026',))

    # ------------------------------------------------ retiree accounts over time
    sr_rev = {y: G[y]['570018']['revised'] for y in range(2022, 2026)}
    tr_rev = {y: G[y]['570009']['revised'] for y in range(2022, 2026)}
    ha_rev = {y: G[y]['570001']['revised'] for y in range(2010, 2026)}
    sr_orig = {y: G[y]['570018']['original'] for y in range(2022, 2026)}
    if any(G[y]['570018']['revised'] or G[y]['570009']['revised'] for y in range(2010, 2022)):
        fail('the ledger history now carries a retiree account before FY2022')
    sr_rev[2026], tr_rev[2026], ha_rev[2026] = SR['revised'], TR['revised'], HA['revised']
    if abs(sr_rev[2023] - R['school_retirees_fy2023']) > 0.005:
        fail('FY2023 school retirees: the ledger history and the annual report disagree')
    one_line_22 = years[2022]['rows'][0]
    if one_line_22['key'] != 'health_ins':
        fail('FY2022’s first insurance row is no longer the undivided health line')
    three = G[2022]['570001']['revised'] + G[2022]['570009']['revised'] + G[2022]['570018']['revised']
    if abs(three - one_line_22['appropriated']) > 0.01:
        fail('FY2022: the three ledger accounts no longer sum to the report’s one line')
    r_sr = cagr(sr_rev[2022], sr_rev[2026], 4)
    r_tr = cagr(tr_rev[2022], tr_rev[2026], 4)
    out['retiree-health-accounts'] = TP.page(
        'retiree-health-accounts',
        'School retiree health went from %s in FY2022 to %s in FY2026, %s a year.'
        % (C.usd(sr_rev[2022]), C.usd(sr_rev[2026]), C.pct(r_sr)),
        [f('sr22', U(sr_rev[2022]), 'school retirees, FY2022', 'published', allow=('FY2022',)),
         f('sr26', U(sr_rev[2026]), 'school retirees, FY2026', 'published', allow=('FY2026',)),
         f('sr-rate', P(r_sr), 'a year, school retirees', 'published'),
         f('tr22', U(tr_rev[2022]), 'town retirees, FY2022', 'published', allow=('FY2022',)),
         f('tr26', U(tr_rev[2026]), 'town retirees, FY2026', 'published', allow=('FY2026',)),
         f('tr-rate', P(r_tr), 'a year, town retirees', 'published'),
         f('one', U(one_line_22['appropriated']), 'FY2022 report: one undivided line',
           'published', allow=('FY2022',)),
         f('before', None, 'the school retiree share before FY2022', 'gap', allow=('FY2022',),
           closes='the town’s Chapter 32B enrollment schedule, which counts retirees by side')],
        [con('School retiree health grew %s a year from FY2022; town retiree health grew %s.'
             % (C.pct(r_sr), C.pct(r_tr)), ['sr22', 'sr26', 'sr-rate', 'tr-rate'],
             {'a': P(r_sr), 'b': P(r_tr)}, allow=('FY2022',),
             notes=[step('More retirees, costlier plans and a changed premium share all raise '
                         'this line; nothing published separates them.', 'gap',
                         closes='retiree enrolment by plan, year by year')]),
         con('The FY2022 annual report printed the three accounts as one line of %s.'
             % C.usd(one_line_22['appropriated']), ['one', 'sr22', 'tr22'],
             {'a': U(one_line_22['appropriated'])}, allow=('FY2022',)),
         con('Before FY2022 the health line is undivided, so the school retiree share of it is '
             'not shown.', ['before'], allow=('FY2022',))],
        table=dict(caption='The three health accounts, revised budget', views=[dict(
            key='split', label='FY2022 to FY2026', total_col=0,
            kinds=['stated', 'stated', 'stated'],
            columns=['School retirees', 'Town retirees', 'HEALTH INS line'],
            rows=[dict(label='FY%d' % y, cells=[C.usd(sr_rev[y]), C.usd(tr_rev[y]),
                                                C.usd(ha_rev[y])])
                  for y in sorted(sr_rev, reverse=True)],
            note='FY2022-FY2025 from the Finance Committee’s ledger history, an assembled '
                 'workbook; its FY2023 school retiree figure equals the annual report’s to the '
                 'cent. FY2026 is the MUNIS ledger at period 12. Original budgets differ: the '
                 'FY2022 original for school retirees was ' + C.usd(sr_orig[2022]) + '.')]),
        sources=[src['gl'], src['glx'], src['ar23'], src['p12'], src['hi']],
        finding_figures={'a': U(sr_rev[2022]), 'b': U(sr_rev[2026]), 'c': P(r_sr)},
        finding_allow=('FY2022', 'FY2026'))

    # ------------------------------------------------ the district's own line
    Dd = HI['district']
    settled = {p['fy']: p['value'] for p in Dd['settled']}
    actual = {p['fy']: p['value'] for p in Dd['actual']}
    var27 = {v['variant']: v['points'][0]['value'] for v in Dd['variants']}
    cs = Dd['change_settled']
    if (cs['first_fy'], cs['last_fy']) != (2018, 2026) or 2024 in settled:
        fail('the district’s adopted series has changed shape')
    if abs(settled[2026] - act) > 0.5:
        fail('the district’s FY2026 adopted figure no longer equals the ledger')
    if sorted(var27) != ['Balanced', 'Core Budget', 'Level Service', 'Restoration']:
        fail('the FY2027 scenarios have changed')
    lo, hi = min(var27.values()), max(var27.values())
    if var27['Balanced'] != lo:
        fail('the Balanced FY2027 scenario is no longer the lowest')
    if abs(var27['Balanced'] - MODEL['health']['budget']) > 0.5:
        fail('the Balanced FY2027 health line disagrees with model.json')
    r_set = cs['cagr'] * 100
    out['district-health-line'] = TP.page(
        'district-health-line',
        'The district’s adopted health line rose from %s in FY2018 to %s in FY2026, %s a year.'
        % (C.usd(settled[2018]), C.usd(settled[2026]), C.pct(r_set)),
        [f('s18', U(settled[2018]), 'adopted, FY2018', 'published', allow=('FY2018',)),
         f('s26', U(settled[2026]), 'adopted, FY2026', 'published', allow=('FY2026',)),
         f('rate', P(r_set), 'a year, adopted to adopted', 'published'),
         f('lo', U(lo), 'lowest FY2027 scenario, the Balanced one', 'published',
           allow=('FY2027',)),
         f('hi', U(hi), 'highest FY2027 scenario', 'published', allow=('FY2027',)),
         f('a25', U(actual[2025]), 'spent, FY2025, a different document', 'published',
           allow=('FY2025',)),
         f('s24', None, 'the adopted FY2024 figure', 'gap', allow=('FY2024',),
           closes='the district’s FY2024 adopted budget book, health insurance line')],
        [con('Adopted to adopted, the line grew %s a year from FY2018 to FY2026.' % C.pct(r_set),
             ['s18', 's26', 'rate', 's24'], {'a': P(r_set)}, allow=('FY2018', 'FY2026'),
             notes=[step('The line is what the district appropriates; it does not say how many '
                         'staff are enrolled or on which plans.', 'gap',
                         closes='enrolment by plan and tier for school employees')]),
         con('The four FY2027 scenarios put the line between %s and %s.' % (C.usd(lo), C.usd(hi)),
             ['lo', 'hi'], {'a': U(lo), 'b': U(hi)}, allow=('FY2027',)),
         con('What was spent is a separate series and is not differenced against these budgets.',
             ['a25'])],
        table=dict(caption='The district’s health insurance line', views=[
            dict(key='adopted', label='Adopted', total_col=0, kinds=['ledger'],
                 columns=['Adopted'],
                 rows=[dict(label='FY%d' % y, cells=[C.usd(settled[y])])
                       for y in sorted(settled, reverse=True)],
                 note='The district budget book’s adopted figure. No adopted FY2024 figure is '
                      'in the series this page reads.'),
            dict(key='actual', label='Spent', total_col=0, kinds=['ledger'],
                 columns=['Spent'],
                 rows=[dict(label='FY%d' % y, cells=[C.usd(actual[y])])
                       for y in sorted(actual, reverse=True)],
                 note='What the district reports spending. A different document from the '
                      'adopted budget; the two are never subtracted here.')]),
        sources=[src['hi'], src['book'], src['p12']],
        finding_figures={'a': U(settled[2018]), 'b': U(settled[2026]), 'c': P(r_set)},
        finding_allow=('FY2018', 'FY2026'))

    # ------------------------------------------------ plans and premiums
    plans = {p['id']: p for p in MODEL['health']['plans']}
    letter = norm(open(RATE_LETTER, encoding='utf-8').read()).replace('$ ', '$')
    rise = MODEL['health']['rateIncrease'] * 100
    if 'represent a %s increase' % C.pct(rise, 2) not in letter:
        fail('the rate letter no longer states the increase model.json carries')
    for p in plans.values():
        for k in ('family', 'individual'):
            if '{:,.2f}'.format(p[k]) not in letter:
                fail('%s %s premium is not in the rate letter' % (p['name'], k))
    if 'Town /School Employees' not in letter:
        fail('the rate letter is no longer addressed to town and school employees')
    share = MODEL['health']['townShare'] * 100
    M2 = lambda v: figure(v, '${:,.2f}'.format(v))
    bce, bs = plans['bce'], plans['bs']
    out['health-plans-and-premiums'] = TP.page(
        'health-plans-and-premiums',
        'Premiums rose %s from 1 July 2026; a Blue Care Elect family plan is %s a month, the '
        'town paying %s.' % (C.pct(rise, 2), '${:,.2f}'.format(bce['family']), C.pct(share, 0)),
        [f('rise', P(rise, 2), 'premium increase, plans from 1 July 2026', 'published',
           allow=('1 July 2026',)),
         f('bce', M2(bce['family']), 'a month, family, Blue Care Elect', 'published'),
         f('bs', M2(bs['family']), 'a month, family, Blue Select', 'published'),
         f('bce-i', M2(bce['individual']), 'a month, individual, Blue Care Elect', 'published'),
         f('plans', N(len(plans), 'plans'), 'plans on the rate letter', 'published'),
         f('share', P(share, 0), 'of an active plan’s premium paid by the town', 'contract'),
         f('enrol', None, 'how many people are on each plan', 'gap',
           closes='the Town’s enrolment by plan and tier, town and school')],
        [con('One rate letter, to all eligible town and school employees, lists the same plans.',
             ['rise', 'plans']),
         con('A family on Blue Care Elect costs %s a month; on Blue Select, %s.'
             % ('${:,.2f}'.format(bce['family']), '${:,.2f}'.format(bs['family'])),
             ['bce', 'bs', 'share'], {'a': M2(bce['family']), 'b': M2(bs['family'])}),
         con('Without enrolment by plan, what moving people between plans would save is not '
             'shown.', ['enrol'])],
        table=dict(caption='Monthly premiums from 1 July 2026', views=[dict(
            key='plans', label='Monthly premium', total_col=0, kinds=['ledger', 'ledger', 'ledger'],
            columns=['Family', 'Individual', 'Deductible'],
            rows=[dict(label=p['name'], cells=['${:,.2f}'.format(p['family']),
                                               '${:,.2f}'.format(p['individual']),
                                               p['deductible']])
                  for p in MODEL['health']['plans']],
            note='The total premium, before the town and employee shares. The letter prints '
                 'Access Blue Saver’s family and individual rows the other way round; they are '
                 'shown here as every other plan’s ratio implies.')]),
        sources=[src['rates'], src['moa']],
        finding_figures={'a': P(rise, 2), 'b': M2(bce['family']), 'c': P(share, 0)},
        finding_allow=('1 July 2026',))

    # ------------------------------------------------ what the state's figure contains
    DL = dls_lunenburg()
    tie = {}
    for y in range(2010, 2025):
        a = G[y]
        whole = sum(r['actual'] for r in a.values())
        health = whole - a['570003']['actual'] - a['570002']['actual']
        tie[y] = dict(whole=whole, health=health, dls=DL[y])
    early = [y for y in range(2010, 2024) if abs(tie[y]['health'] - tie[y]['dls']) <= 5]
    if early != list(range(2010, 2024)):
        fail('the DLS figure no longer ties to the health accounts FY2010-FY2023: %s' % early)
    if abs(tie[2024]['whole'] - tie[2024]['dls']) > 1 or G[2024]['570001']['partial']:
        fail('FY2024’s DLS figure no longer equals the whole department')
    if not G[2025]['570001']['partial']:
        fail('the ledger history’s FY2025 actuals are no longer partial; tie FY2025 now')
    h24 = tie[2024]['health']
    lfl = 100 * (h24 / tie[2023]['dls'] - 1)
    out['health-state-reported'] = TP.page(
        'health-state-reported',
        'The state’s figure for Lunenburg counted Medicare and life insurance in FY2024, and in '
        'no year before.',
        [f('ties', OF(len(early), len(early), 'years'), 'years FY2010-FY2023 within $5 of the '
           'health accounts', 'published', allow=('FY2010', 'FY2023', '$5')),
         f('d23', U(DL[2023]), 'state figure, FY2023', 'published', allow=('FY2023',)),
         f('d24', U(DL[2024]), 'state figure, FY2024', 'published', allow=('FY2024',)),
         f('w24', U(tie[2024]['whole']), 'whole insurance department spent, FY2024', 'published',
           allow=('FY2024',)),
         f('h24', U(h24), 'FY2024, health accounts alone', 'published', allow=('FY2024',)),
         f('lfl', P(lfl), 'FY2024 rise on the health accounts alone (ours)', 'estimate',
           allow=('FY2024',)),
         f('d25', U(DL[2025]), 'state figure, FY2025', 'published', allow=('FY2025',)),
         f('c25', None, 'which accounts FY2025’s figure counts', 'gap', allow=('FY2025',),
           closes='the town’s FY2025 Schedule A, health insurance, set against the year-end '
                  'ledger')],
        [con('Through FY2023 the state’s figure equals the department’s spending less Medicare '
             'and life insurance.', ['ties', 'd23'], allow=('FY2023',)),
         con('FY2024’s %s equals the whole department, Medicare and life included.'
             % C.usd(DL[2024]), ['d24', 'w24'], {'a': U(DL[2024])}, allow=('FY2024',),
             notes=[step('A change in what the town reported on Schedule A would produce this; '
                         'nothing here shows why it changed.', 'hypothesis')]),
         con('On the health accounts alone, FY2024 rose %s on FY2023.' % C.pct(lfl),
             ['h24', 'lfl', 'd23'], {'a': P(lfl)}, allow=('FY2024', 'FY2023')),
         con('The state’s figure is the town department only; the school department’s own '
             'health line is not in it.', ['ties', 'w24'])],
        table=dict(caption='The state’s figure against the ledger history', views=[dict(
            key='tie', label='Spent', total_col=0, kinds=['ledger', 'stated', 'stated'],
            columns=['State figure', 'Health accounts', 'Whole department'],
            rows=[dict(label='FY%d' % y, cells=[C.usd(tie[y]['dls']), C.usd(tie[y]['health']),
                                                C.usd(tie[y]['whole'])])
                  for y in sorted(tie, reverse=True)],
            note='Health accounts: the insurance department’s actual spending less Medicare and '
                 'life insurance, from the Finance Committee’s ledger history. FY2025 is left '
                 'out: the history’s FY2025 actuals are part-year.')]),
        sources=[src['dls'], src['dlsweb'], src['gl'], src['glx']],
        finding_allow=('FY2024',))

    # ------------------------------------------------ towns compared
    T = HO['town']
    pe = HO['peers']
    if (pe['from_fy'], pe['to_fy']) != (2015, 2025) or HO['by_funding']['town_is'] != 'fully insured':
        fail('the comparison window or the town’s funding type has changed')
    under4 = next(a for a in HO['achievable'] if a['threshold'] == 4.0)
    types = {t['funding']: t for t in HO['by_funding']['types']}
    fi, si = types['fully insured'], types['self-insured']
    allp = {p['municipality']: p for p in pe['all']}
    nb = [allp[n['municipality']] for n in HO['neighbours'] if n['municipality'] in allp]
    out['health-towns-compared'] = TP.page(
        'health-towns-compared',
        'On the state’s figure, which added Medicare and life in FY2024, spending grew %s a year '
        'from FY2015.' % C.pct(T['growth'], 2),
        [f('town', P(T['growth'], 2), 'a year, Lunenburg, FY2015-FY2025', 'published',
           allow=('FY2015', 'FY2025')),
         f('median', P(T['median_growth'], 2), 'a year, the median municipality', 'published'),
         f('rank', OF(T['rank'], T['of'], 'municipalities'), 'place, slowest growth first',
           'published'),
         f('under4', OF(under4['towns'], under4['of'], 'municipalities'),
           'grew under 4% a year over the decade', 'published', allow=('4%',)),
         f('fi', P(fi['median'], 2), 'median, %s fully insured towns, as Lunenburg is'
           % C.num(fi['towns']), 'published', {'n': N(fi['towns'])}),
         f('si', P(si['median'], 2), 'median, %s self-insured towns' % C.num(si['towns']),
           'published', {'n': N(si['towns'])}),
         f('content', None, 'whether every town counts the same accounts', 'gap',
           closes='each town’s Schedule A, health insurance, account by account')],
        [con('Lunenburg ranks %s by growth, slowest first.' % OF(T['rank'], T['of'])['text'],
             ['rank', 'town', 'median'], {'a': OF(T['rank'], T['of'])},
             notes=[step('If FY2025, like FY2024, counts Medicare and life insurance, part of '
                         'this rate is a change in what was counted.', 'hypothesis',
                         allow=('FY2024', 'FY2025'))]),
         con('%s municipalities held growth under %s a year over the same decade.'
             % (OF(under4['towns'], under4['of'])['text'], '4%'), ['under4'],
             {'a': OF(under4['towns'], under4['of'])}, allow=('4%',)),
         con('Levels are not compared: a self-insured town’s figure includes the employee’s '
             'share.', ['fi', 'si', 'content'])],
        table=dict(caption='The towns this project compares against', views=[dict(
            key='nb', label='FY2015 to FY2025', total_col=2, kinds=['ledger', 'ledger', 'ledger'],
            columns=['FY2015', 'FY2025', 'A year'],
            rows=[dict(label=p['municipality'], cells=[C.usd(p['first']), C.usd(p['last']),
                                                       C.pct(p['growth'], 2)])
                  for p in sorted(nb, key=lambda p: -p['growth'])],
            note='Health insurance spending as each town filed it on Schedule A. Compare the '
                 'rate, not the level; what each town’s figure contains differs.')]),
        sources=[src['dls'], src['dlsweb'], src['ho']],
        finding_figures={'a': P(T['growth'], 2)},
        finding_allow=('FY2015', 'FY2024'))

    # ------------------------------------------------ growth over time
    ry = {r['fy']: r for r in HO['recent_years']}
    if sorted(ry) != [2022, 2023, 2024, 2025]:
        fail('the recent years are no longer FY2022-FY2025')
    roll = T['rolling']
    yr = lambda y: figure(ry[y]['town'], C.pct(ry[y]['town'], 1))
    md = lambda y: figure(ry[y]['median'], C.pct(ry[y]['median'], 1))
    out['health-growth-over-time'] = TP.page(
        'health-growth-over-time',
        # THE HEADLINE STOPS AT THE BREAK. FY2024's state figure counts Medicare and life
        # insurance and no earlier year's does, so its rise is not a like-for-like number; it
        # is shown below with that said beside it, never as the line a reader repeats.
        'Filed spending rose %s in FY2023, the median town %s; FY2024’s figure counts more '
        'accounts.' % (yr(2023)['text'], md(2023)['text']),
        [f('t23', yr(2023), 'rise, FY2023, Lunenburg', 'published', allow=('FY2023',)),
         f('m23', md(2023), 'rise, FY2023, median town', 'published', allow=('FY2023',)),
         f('t24', yr(2024), 'rise, FY2024, Lunenburg', 'published', allow=('FY2024',)),
         f('m24', md(2024), 'rise, FY2024, median town', 'published', allow=('FY2024',)),
         f('lfl', P(lfl), 'FY2024 on the health accounts alone (ours)', 'estimate',
           allow=('FY2024',)),
         f('t25', yr(2025), 'rise, FY2025, Lunenburg', 'published', allow=('FY2025',)),
         f('m25', md(2025), 'rise, FY2025, median town', 'published', allow=('FY2025',)),
         f('win', OF(T['decades_under_4'], T['decades'], 'windows'),
           'ten-year windows under 4% a year', 'published', allow=('4%',)),
         f('last', FYF(T['last_decade_under_4']), 'last such window ends', 'published')],
        [con('FY2023 rose %s against a median %s.' % (yr(2023)['text'], md(2023)['text']),
             ['t23', 'm23'], {'a': yr(2023), 'b': md(2023)}, allow=('FY2023',)),
         con('FY2024’s %s compares a figure with Medicare and life to one without; health alone '
             'rose %s.'
             % (yr(2024)['text'], C.pct(lfl)), ['t24', 'm24', 'lfl'],
             {'a': yr(2024), 'b': P(lfl)}, allow=('FY2024',)),
         con('FY2025 rose %s, below the median town’s %s.' % (yr(2025)['text'], md(2025)['text']),
             ['t25', 'm25'], {'a': yr(2025), 'b': md(2025)}, allow=('FY2025',)),
         con('Its ten-year rate was under %s in %s windows, the last ending %s.'
             % ('4%', OF(T['decades_under_4'], T['decades'])['text'],
                'FY%d' % T['last_decade_under_4']), ['win', 'last'],
             {'a': OF(T['decades_under_4'], T['decades']), 'b': FYF(T['last_decade_under_4'])},
             allow=('4%',))],
        table=dict(caption='Lunenburg’s filed health spending, by period', views=[
            dict(key='recent', label='Year on year', total_col=0, kinds=['ledger', 'ledger'],
                 columns=['Lunenburg', 'Median town'],
                 rows=[dict(label='FY%d' % y, cells=[C.pct(ry[y]['town'], 1),
                                                     C.pct(ry[y]['median'], 1)])
                       for y in sorted(ry, reverse=True)],
                 note='Each year’s rise in spending as filed on Schedule A.'),
            dict(key='windows', label='Ten-year windows', total_col=0, kinds=['ledger'],
                 columns=['A year'],
                 rows=[dict(label='FY%d-FY%d' % (r['fy'] - 10, r['fy']),
                            cells=[C.pct(r['growth'], 2)]) for r in reversed(roll)],
                 note='Compound growth over each ten years of Lunenburg’s filed figure. Windows '
                      'ending FY2024 or FY2025 span the change in what the FY2024 figure counts.')]),
        sources=[src['dls'], src['dlsweb'], src['ho'], src['gl']],
        finding_figures={'a': yr(2023), 'c': md(2023)},
        finding_allow=('FY2023', 'FY2024'))

    # ------------------------------------------------ options under the law
    opts = HO['options']
    can = [o for o in opts if o['available_to_lunenburg'] != 'no']
    cannot = [o for o in opts if o['available_to_lunenburg'] == 'no']
    held = [o for o in opts if o.get('held_until')]
    if {o['held_until'] for o in held} != {'2029-06-30'}:
        fail('the PEC hold no longer ends on 30 June 2029 for every held option')
    if sorted(o['id'] for o in held) != ['join-gic-agreement', 'join-gic-unilateral', 'plan-design']:
        fail('the options the PEC agreement holds have changed')
    floor = re.search(r"fixes the town's share at (\d+)%",
                      next(o for o in opts if o['id'] == 'cut-town-share')['note'])
    if not floor:
        fail('the statutory floor is no longer stated in the cut-town-share row')
    floor = int(floor.group(1))
    out['health-insurance-options'] = TP.page(
        'health-insurance-options',
        'Chapter 32B leaves the town %s routes and bars %s; the PEC agreement holds %s of them '
        'until 30 June 2029.' % (C.num(len(can)), C.num(len(cannot)), C.num(len(held))),
        [f('can', N(len(can), 'routes'), 'routes open under Chapter 32B', 'statute',
           allow=('32B',)),
         f('cannot', N(len(cannot), 'routes'), 'barred at any threshold', 'statute'),
         f('held', N(len(held), 'routes'), 'held by the PEC agreement to 30 June 2029',
           'contract', allow=('30 June 2029',)),
         f('floor', P(floor, 0), 'least the town may pay of a premium', 'statute'),
         f('share', P(share, 0), 'what the town pays now, active plans', 'contract'),
         f('saves', None, 'what any route would save the town', 'gap',
           closes='a premium quote for Lunenburg’s enrolment from MIIA or the GIC, plan by plan')],
        [con('Plan design and both routes into the state’s GIC are held by the PEC agreement.',
             ['held'],
             notes=[step('Whether the parties may reopen it early for any reason but federal '
                         'changes is not stated.', 'gap',
                         closes='a signed amendment or side letter to the 2026-2029 memorandum',
                         allow=('2026-2029',))]),
         con('The town may never pay less than %s of a premium; it pays %s.'
             % (C.pct(floor, 0), C.pct(share, 0)), ['floor', 'share', 'cannot'],
             {'a': P(floor, 0), 'b': P(share, 0)}),
         con('The statute says what is permitted, not what it would save; no document here '
             'prices a route.', ['saves', 'can'])],
        table=dict(caption='Every route, and the section that governs it', views=[dict(
            key='law', label='Chapter 32B', total_col=0, kinds=['stated', 'stated', 'stated'],
            columns=['For Lunenburg', 'Section', 'Who decides'],
            rows=[dict(label=o['option'], cells=[o['available_to_lunenburg'], o['statute'],
                                                 o['who_decides']]) for o in opts],
            note='From our reading of each section, linked on /docs/data/health-insurance-law.csv '
                 'to malegislature.gov. A route the PEC agreement holds is open after it ends.')]),
        sources=[src['law'], src['mgl'], src['moa'], src['ho']],
        finding_figures={'a': N(len(can)), 'b': N(len(cannot)), 'c': N(len(held))},
        finding_allow=('32B', '30 June 2029'))

    # ------------------------------------------------ the PEC agreement
    moa = norm(open(MOA, encoding='utf-8').read())
    m_act = re.search(r'Town shall contribute (\d+)% of the health insurance premium and the '
                      r'employee/Non-Medicare retiree shall contribute (\d+)%', moa)
    m_medex = re.search(r'Town shall contribute (\d+)% of the health insurance premium and the '
                        r'retiree shall contribute (\d+)% of the health insurance premium for Medex',
                        moa)
    m_b = re.search(r'reimburse enrolled subscribers \(retirees and their spouse\) \$(\d+) per month',
                    moa)
    if not (m_act and m_medex and m_b) or float(m_act.group(1)) != share:
        fail('the memorandum no longer states the shares this page reads')
    if 'amends the current in-force health insurance agreement' not in moa:
        fail('the memorandum no longer says it amends the in-force agreement')
    if 'from July 1, 2026 through June 30, 2029' not in moa:
        fail('the memorandum’s term has changed')
    medex, partb = int(m_medex.group(1)), int(m_b.group(1))
    PH = list(csv.DictReader(open(os.path.join(DATA, 'pec-history.csv'), encoding='utf-8')))
    if not any(r['on'] == '2008-06-16' for r in PH):
        fail('pec-history.csv no longer dates the agreement 16 June 2008')
    out['pec-agreement'] = TP.page(
        'pec-agreement',
        'The town pays %s of active premiums under a PEC agreement that runs to 30 June 2029.'
        % C.pct(share, 0),
        [f('act', P(share, 0), 'town share, active plans', 'contract'),
         f('medex', P(medex, 0), 'town share, Medex', 'contract'),
         f('partb', figure(partb, '$%d' % partb), 'a month toward a retiree’s Medicare Part B',
           'contract'),
         f('end', figure('2029-06-30', '30 June 2029'), 'the memorandum’s term ends', 'contract'),
         f('first', figure('2008-06-16', '16 June 2008'), 'the earliest PEC agreement held',
           'contract'),
         f('base', None, 'the agreement the 2026 memorandum amends', 'gap', allow=('2026',),
           closes='the health insurance agreement in force before July 2026, which the '
                  'memorandum amends and does not attach'),
         f('s21', None, 'a vote accepting c.32B §§21–23', 'gap', allow=('c.32B', '§§21–23'),
           closes='a Town Meeting or Select Board vote accepting c.32B §§21–23, if one exists')],
        [con('The 2026 memorandum fixes the town’s share at %s for active plans and %s for Medex.'
             % (C.pct(share, 0), C.pct(medex, 0)), ['act', 'medex', 'end'],
             {'a': P(share, 0), 'b': P(medex, 0)}, allow=('2026',)),
         con('It amends “the current in-force health insurance agreement”, which it does not '
             'attach.', ['base', 'first'],
             notes=[step('The agreement the Select Board approved in April 2022 is the likeliest '
                         'candidate; nothing here states it.', 'hypothesis', allow=('2022',))]),
         con('No vote accepting the plan-design sections has been found in the record held.',
             ['s21'])],
        said=[said_file('select-board/2011-03-01-minutes-4777.txt',
                        "as of July 1st we'll be going to 75/25 of cost sharing split between "
                        "the town and employees", 'Select Board'),
              said_file('select-board/2022-04-12-minutes-5316.txt',
                        'The new agreement starts July 1 and provides another health insurance '
                        'plan option (Blue Cross Select). It provides a smaller network of '
                        'providers and a lower cost.', 'Select Board')],
        sources=[src['moa'], src['pec'], src['ho']],
        finding_figures={'a': P(share, 0)}, finding_allow=('30 June 2029',))

    # ------------------------------------------------ the hub
    h = {}
    h['h-dept'] = f('h-dept', U(dept26), 'town insurance department, FY2026', 'published',
                    allow=('FY2026',))
    h['h-act'] = f('h-act', U(act), 'school department health line, FY2026', 'published',
                   allow=('FY2026',))
    h['h-ret'] = f('h-ret', U(SR['original']), 'school retirees, in the town department',
                   'published')
    h['h-rise'] = f('h-rise', P(rise, 2), 'premium increase from 1 July 2026', 'published',
                    allow=('1 July 2026',))
    h['h-rate'] = f('h-rate', P(rate_dept), 'a year, the town department, FY2011-FY2026',
                    'published', allow=('FY2011', 'FY2026'))
    h['h-cap'] = f('h-cap', P(CAP), 'a year the levy may rise, before new growth', 'statute')
    h['h-rank'] = f('h-rank', OF(T['rank'], T['of'], 'municipalities'),
                    'place by growth, FY2015-FY2025, slowest first', 'published',
                    allow=('FY2015', 'FY2025'))
    h['h-can'] = f('h-can', N(len(can), 'routes'), 'routes open under Chapter 32B', 'statute',
                   allow=('32B',))
    h['h-whose'] = f('h-whose', None, 'school staff inside the town’s own lines', 'gap',
                     closes='the town’s Chapter 32B enrollment schedule, by department')
    h['h-saves'] = f('h-saves', None, 'what any route would save', 'gap',
                     closes='a premium quote for Lunenburg’s enrolment, plan by plan')
    tiers = [
        LD.tier('What is budgeted', [h['h-dept'], h['h-act'], h['h-ret'], h['h-rise']]),
        LD.tier('How fast it grows', [h['h-rate'], h['h-cap'], h['h-rank']]),
        LD.tier('What is not shown', [h['h-can'], h['h-whose'], h['h-saves']]),
    ]
    hub_ladder = LD.ladder(tiers, [
        LD.conclusion('The town department grew %s a year from FY2011, against a %s levy cap.'
                      % (C.pct(rate_dept), C.pct(CAP)), ['h-rate', 'h-cap', 'h-dept'],
                      {'a': P(rate_dept), 'b': P(CAP)}, allow=('FY2011',)),
        LD.conclusion('School retiree health, %s, sits in the town’s budget, not the schools’.'
                      % C.usd(SR['original']), ['h-ret', 'h-act'], {'a': U(SR['original'])}),
        LD.conclusion('Whether the town’s own health lines cover school staff is not split out.',
                      ['h-whose', 'h-dept']),
        LD.conclusion('By the state’s figures Lunenburg ranks %s; its FY2024 figure counted more '
                      'accounts.' % OF(T['rank'], T['of'])['text'], ['h-rank'],
                      {'a': OF(T['rank'], T['of'])}, allow=('FY2024',)),
        LD.conclusion('Chapter 32B leaves %s routes open; none is priced in any document held.'
                      % C.num(len(can)), ['h-can', 'h-saves'], {'a': N(len(can))},
                      allow=('32B',)),
    ])
    out[CID] = TP.hub(
        CID,
        'The town budgeted %s for its insurance department in FY2026, and the schools %s on '
        'their own health line. The department grew %s a year from FY2011, against a %s levy cap.'
        % (C.usd(dept26), C.usd(act), C.pct(rate_dept), C.pct(CAP)),
        hub_ladder,
        answer_figures={'a': U(dept26), 'b': U(act), 'c': P(rate_dept), 'd': P(CAP)},
        answer_allow=('FY2026', 'FY2011'))

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
        print('health insurance topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
