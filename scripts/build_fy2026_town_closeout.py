#!/usr/bin/env python3
"""FY2026 town year end: the town (non-school) departments at the close.

    python3 scripts/build_fy2026_town_closeout.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_fy2026_town_closeout.py --check   # fail if any output would change

WHY THIS EXISTS. The school budget's year end has its own hub (fy2026-closeout, under
/school-all-funds). TJ, 26 November 2026, reading it: "i think we ned a related [hub] for the
town too, all other deparmtents". The school hub's town pages read June (period 12), before
the books closed; the town's closed-year report (period 13) has since been answered and read.
This hub is the town side at the close, in the school hub's shape: two big figures, the
heavily under and over accounts as a chart, then talking points each linked to the page that
proves it.

WHAT "TOWN" MEANS HERE. Every general fund department except the schools: 300 (the school
department) and 301 (school non-recurring expenses), as the school hub's own town page
already draws it. It keeps the lines the TOWN budget carries on the schools' behalf --
school retirees' health insurance (914) and the Monty Tech assessment (310) -- because they
are town appropriations, voted and paid on the town side, and says so by name.

THE LEDGER. sources/data/munis-ledger.csv, fund 0100, period 13, FY2025 and FY2026: our
reading of the Town's closed-year general fund reports (the PDFs are withheld,
redactions.csv; the reading is published as munis-gf-p13-reading.csv). Before anything is
written, every column of each year is summed across ALL departments and tied to the report's
own printed grand total (munis-gf-p13-reading-totals.csv), to the cent (rule 13).

THE WORDS. "Paid" is expended. "Still owed" is encumbered, counted as spent. "Left" is the
ledger's own available column: revised budget less paid less owed; negative is "over".

THE TWO YEARS ARE NOT ON ONE FOOTING. FY2026's closed report counts orders still owed at the
close as spent; FY2025's prints no orders owed at all. So FY2025's figure is stated as printed
and never differenced against FY2026's (the school hub met the same thing and settled it from
the school journal; no town journal is held). Earlier closed years are not held: the Finance
Committee's FY2010-FY2025 history is a workbook somebody assembled (rule 13a), and is not used.

"HEAVILY", the school hub's bar: at least $50,000 AND at least 4% of the line's budget, either
way. Applied to ACCOUNTS, not departments: the insurance department nets three accounts that
miss in opposite directions by up to a quarter of a million dollars, and TJ's rule is to split
anything that nets opposite misses. An account whose payments are NEGATIVE (a correction
credited back) is not counted as underspent; the snow overtime line is one, and is named.
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topic_blocks as TB  # noqa: E402
import topics as REG  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'sources', 'data')
PUB = os.path.join(ROOT, 'fy28', 'public')
OUT_DIR = os.path.join(PUB, 'data', 'topics')
LEDGER = os.path.join(D, 'munis-ledger.csv')
TOTALS = os.path.join(D, 'munis-gf-p13-reading-totals.csv')
GL = os.path.join(D, 'gl-history.csv')
DEPTS = os.path.join(D, 'departments.csv')
HUB = 'fy2026-town-closeout'
SCHOOL = ('300', '301')
K = ('original', 'transfers', 'revised', 'expended', 'encumbered', 'available')
BIG, SHARE = 50000, 4.0
RESERVE, SALARY_RESERVE, INSURANCE, SNOW, POLICE = '132', '133', '914', '423', '210'
TO_CAPITAL, TO_STAB = '993', '996'
SCHOOL_RETIREES, TOWN_RETIREES, TOWN_ACTIVE = '570018', '570009', '570001'
SNOW_OT = '513000'

# The town's MUNIS function codes, as build_department_budgets.py names them.
FUNCTIONS = {
    '1': 'General government', '2': 'Public safety', '3': 'Education (Monty Tech)',
    '4': 'Public works & facilities', '5': 'Human services', '6': 'Culture & recreation',
    '7': 'Debt service', '8': 'Retirement & state assessments',
    '9': 'Insurance, benefits & transfers',
}

# PLAIN NAMES for the accounts the hub names (rule 7b: MUNIS prints 'POLICE SARGENTS
# SALARIES' and 'SUPPLIES SNOW'; nobody speaks that). Labels, not figures. An account that
# reaches the heavily lists without one here stops the build rather than print the code's name.
PLAIN = {
    ('914', '570018'): 'School retirees’ health insurance',
    ('914', '570009'): 'Town retirees’ health insurance',
    ('914', '570001'): 'Town employees’ health insurance',
    ('914', '570003'): 'Town Medicare contributions',
    ('132', '578000'): 'The Reserve Fund',
    ('210', '511004'): 'Police sergeants’ salaries',
    ('210', '511006'): 'Police patrol officers’ salaries',
    ('423', '531029'): 'Snow and ice supplies',
}

MINE = [t for t, (_, home, gen) in REG.TOPICS.items()
        if home == HUB and gen == 'build_fy2026_town_closeout.py']


def fail(msg):
    raise SystemExit('build_fy2026_town_closeout: ' + msg)


def near(a, b, tol=0.01):
    return abs(float(a) - float(b)) <= tol


def usd2(x):
    x = float(x)
    return ('-$' if x < 0 else '$') + format(abs(x), ',.2f')


def tot(rows):
    return {k: round(sum(r[k] for r in rows), 2) for k in K}


# --------------------------------------------------------------------- the ledger

def ledger():
    """{fy: every fund 0100 account at period 13}, tied to the report's printed grand total."""
    rows = {}
    for r in csv.DictReader(open(LEDGER, encoding='utf-8')):
        if r['period'] == '13' and r['fund'] == '0100' and r['account_type'] == 'expense':
            for k in K:
                r[k] = float(r[k] or 0)
            rows.setdefault(int(r['fy']), []).append(r)
    if sorted(rows) != [2025, 2026]:
        fail('expected FY2025 and FY2026 at period 13, found %s' % sorted(rows))
    printed = {int(r['fy']): r for r in csv.DictReader(open(TOTALS, encoding='utf-8'))
               if r['period'] == '13'}
    for fy, rs in rows.items():
        t = tot(rs)
        for k in K:
            if not near(t[k], float(printed[fy][k])):
                fail('FY%d %s: accounts sum to %.2f, the report prints %s'
                     % (fy, k, t[k], printed[fy][k]))
        for r in rs:
            if not near(r['revised'] - r['expended'] - r['encumbered'], r['available'], 0.02):
                fail('FY%d %s does not foot' % (fy, r['account']))
    return rows


def names():
    """Department code -> name. MUNIS's own department names (the Finance Committee's history
    carries them, latest year); our department register for codes that came later; for the
    transfer departments, their one account's printed name."""
    n = {}
    for r in csv.DictReader(open(GL, encoding='utf-8')):
        if r['sheet'] == 'general_fund':
            n[r['department_code']] = r['department']
    for r in csv.DictReader(open(DEPTS, encoding='utf-8')):
        codes = r['dept_codes'].split(';')
        for c in codes:
            # MUNIS's name field holds 30 characters; a name that fills it was cut short
            if len(codes) == 1 or len(n.get(c, '')) >= 30:
                if c not in n or len(n[c]) >= 30:
                    n[c] = r['name']
    return n


def title(s):
    small = {'and', 'of', 'to', 'the', 'for', 'on'}
    keep = {'DPW', 'COA', 'IT', 'PEG', 'II', 'III'}
    w = s.replace('/', ' / ').split()
    out = [x if x in keep else (x.lower() if i and x.lower() in small else x.capitalize())
           for i, x in enumerate(w)]
    return ' '.join(out).replace(' / ', '/').replace("'S", "'s").replace('’S', '’s')


# --------------------------------------------------------------------- sources

def sources():
    out = {}
    for k, f, what in (
            ('d-p13', 'munis-gf-p13-reading.csv',
             'the general fund at the close, FY2025 and FY2026, our reading of the Town’s '
             'closed-year reports'),
            ('d-tot', 'munis-gf-p13-reading-totals.csv',
             'the grand totals those reports print, which the reading ties to'),
            ('d-ledger', 'munis-ledger.csv', 'the same reading, one row an account')):
        if not os.path.exists(os.path.join(PUB, 'docs', 'data', f)):
            fail('/docs/data/%s is not published' % f)
        out[k] = dict(key=k, label='Lunenburg Budget Project — %s (%s)' % (f, what),
                      href='/docs/data/' + f)
    return out


# --------------------------------------------------------------------- the pages

def build():
    L = ledger()
    nm = names()
    src = sources()
    U = lambda v: figure(v, C.usd(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=0: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    f, con = LD.fact, TP.conclusion
    out = {}

    town = {fy: [r for r in rs if r['dept'] not in SCHOOL] for fy, rs in L.items()}
    t26, t25 = tot(town[2026]), tot(town[2025])
    if t25['encumbered'] != 0:
        fail('FY2025 now prints orders owed at its close; the footing note says it prints none')
    left26, rev26, owed26 = t26['available'], t26['revised'], t26['encumbered']
    left_pct = round(100 * left26 / rev26, 1)
    ceiling = round(left26 + owed26, 2)

    # departments, FY2026
    dep = {}
    for r in town[2026]:
        dep.setdefault(r['dept'], []).append(r)
    dt = {d: tot(rs) for d, rs in dep.items()}
    live = {d: t for d, t in dt.items() if t['revised'] or t['expended']}
    for d in live:
        if d not in nm:
            rs = [r for r in dep[d] if r['revised'] or r['expended']]
            if len(rs) != 1:
                fail('department %s has no name and more than one account' % d)
            nm[d] = rs[0]['name']
    dn = {d: title(nm[d]) for d in live}
    acct = {(r['dept'], r['object']): r for r in town[2026]}

    over = [r for r in town[2026] if r['available'] < -0.5]
    under = [r for r in town[2026] if r['available'] > 0.5]
    over_amt = round(-sum(r['available'] for r in over), 2)
    under_amt = round(sum(r['available'] for r in under), 2)
    dep_over = [d for d, t in live.items() if t['available'] < -0.5]
    if not (len(dep_over) == 1 and dep[dep_over[0]][0]['dept'].startswith('99')
            and 'TRANSFER' in nm.get(dep_over[0], '') + ' '.join(r['name'] for r in dep[dep_over[0]])):
        fail('the one line over as a whole is no longer a single transfer; the points say it is')
    xo = live[dep_over[0]]

    # heavily, account by account
    def heavy_of(rs):
        h = [r for r in rs if r['revised'] > 0 and r['expended'] >= 0
             and abs(r['available']) >= BIG and 100 * abs(r['available']) / r['revised'] >= SHARE]
        return (sorted((r for r in h if r['available'] > 0), key=lambda r: -r['available']),
                sorted((r for r in h if r['available'] < 0), key=lambda r: r['available']))
    hu, ho = heavy_of(town[2026])
    if not (hu and ho):
        fail('no account is heavily under or heavily over; the talking points need rewriting')
    ot = acct[(SNOW, SNOW_OT)]
    if not (ot['expended'] < 0 and ot['available'] >= BIG):
        fail('snow overtime no longer has negative payments clearing the bar; the note names it')

    def aname(r):
        if (r['dept'], r['object']) not in PLAIN:
            fail('account %s-%s (%s) is in a heavily list with no plain name'
                 % (r['dept'], r['object'], r['name']))
        return PLAIN[(r['dept'], r['object'])]

    # insurance: three accounts, opposite ways
    ins = dt[INSURANCE]
    sr, tr_, ta = (acct[(INSURANCE, o)] for o in (SCHOOL_RETIREES, TOWN_RETIREES, TOWN_ACTIVE))
    if not (sr['available'] > 0 > tr_['available'] and ta['available'] < 0 < ins['available']):
        fail('insurance no longer nets school retirees under against town health over')
    if not (100 * abs(ins['available']) / ins['revised'] < SHARE):
        fail('the insurance department now clears the heavily bar as a whole; the point says it does not')

    # reserves
    rf = acct[(RESERVE, '578000')]
    if not (rf['expended'] == 0 and rf['transfers'] == 0 and rf['available'] == rf['original']):
        fail('the Reserve Fund now shows movement; the point says none of it was used')
    sres = acct[(SALARY_RESERVE, '578000')]
    sres_moved = round(-sres['transfers'], 2)
    if not sres_moved > 0:
        fail('the salary reserve no longer moved money out to departments')

    # transfers to capital and stabilization, raised during the year
    tc, ts = dt[TO_CAPITAL], dt[TO_STAB]
    for t in (tc, ts):
        if not (near(t['revised'], t['expended']) and t['revised'] > t['original']):
            fail('a transfer account no longer spends a budget raised during the year')
    tr_o = round(tc['original'] + ts['original'], 2)
    tr_e = round(tc['expended'] + ts['expended'], 2)
    tr_up = round(tr_e - tr_o, 2)
    if not (tr_up > left26):
        fail('the transfers point says the raise exceeded the whole leftover')

    # snow
    sn = dt[SNOW]
    if not (near(sn['available'], 0) and sn['revised'] > 2 * sn['original']):
        fail('snow no longer closed to the dollar on a budget more than doubled')

    # police
    pol = dt[POLICE]
    pol_h = [r for r in hu if r['dept'] == POLICE]
    if len(pol_h) != 2:
        fail('two police salary accounts were heavily under; no longer')

    # ------------------------------------------------ the topic: departments at close
    top = sorted(live, key=lambda d: -live[d]['available'])
    shown = [d for d in top if live[d]['available'] >= 10000]
    if not 5 <= len(shown) <= 20:
        fail('%d departments left $10,000 or more; the chart is sized for 5 to 20' % len(shown))
    top_share = round(100 * sum(live[d]['available'] for d in shown) / under_amt)
    # one view a MUNIS function (the account string's second segment), so no view passes 30 rows
    fn_of = {}
    for d in live:
        fns = {r['account'].split('-')[1] for r in dep[d]}
        if len(fns) != 1:
            fail('department %s sits in more than one function' % d)
        fn_of[d] = fns.pop()
    views = []
    for fn in sorted(set(fn_of.values())):
        ds = sorted((d for d in live if fn_of[d] == fn), key=lambda d: -live[d]['revised'])
        ft = {k: round(sum(live[d][k] for d in ds), 2) for k in K}
        rows = [dict(label='%s (%s)' % (dn[d], d), cells=[usd2(live[d][k]) for k in
                     ('revised', 'expended', 'encumbered', 'available')]) for d in ds]
        if len(ds) > 1:
            rows.append(dict(label='Total', cells=[usd2(ft[k]) for k in
                             ('revised', 'expended', 'encumbered', 'available')]))
        views.append(dict(key='f%s' % fn, label=FUNCTIONS[fn], total_col=-1,
                          kinds=['ledger'] * 4, columns=['Budget', 'Paid', 'Still owed', 'Left'],
                          rows=rows,
                          note='Departments in this function, largest budget first. Budget is '
                               'after transfers.'))
        if len(rows) > 30:
            fail('function %s has %d rows; a table view holds 30' % (fn, len(rows)))
    if not near(sum(live[d]['available'] for d in live), left26):
        fail('the departments do not add to the town total')
    out['fy2026-town-departments'] = TP.page(
        'fy2026-town-departments',
        'Town departments closed %s %s under a %s budget, %s of it.'
        % (C.fy(2026), C.usd(left26), C.usd(rev26), C.pct(left_pct, 1)),
        [f('rev', U(rev26), 'town budget after transfers, %s' % C.fy(2026), 'published',
           {'y': F(2026)}),
         f('left', U(left26), 'left unspent at the close', 'published'),
         f('owed', U(owed26), 'still owed at the close, counted as spent', 'published'),
         f('under', U(under_amt), 'left on accounts under budget', 'published'),
         f('overamt', U(over_amt), 'spent past budget on the others', 'published'),
         f('nunder', N(len(under), 'accounts'), 'accounts under budget', 'published'),
         f('nover', N(len(over), 'accounts'), 'accounts over budget', 'published'),
         f('ndep', N(len(dep_over), 'departments'), 'department codes over as a whole, a transfer',
           'published'),
         f('nshown', N(len(shown), 'departments'), 'departments that left $10,000 or more',
           'published', allow=('$10,000',)),
         f('share', P(top_share), 'their share of the money left under budget', 'published'),
         f('left25', U(t25['available']), 'left at the %s close, as printed' % C.fy(2025),
           'published', {'y': F(2025)}),
         f('foot', None, 'orders still owed at the FY2025 close', 'gap', allow=('FY2025',),
           closes='the town’s FY2025 encumbrance carry-forward list, by account')],
        [con('%s town departments left %s or more each; together, %s of what was left under '
             'budget.' % (C.num(len(shown)), C.usd(10000), C.pct(top_share, 0)),
             ['nshown', 'share', 'under'],
             {'a': N(len(shown)), 'b': U(10000), 'c': P(top_share)},
             so='The leftover is concentrated: most of it sits in a handful of departments.'),
         con('%s accounts closed under budget, leaving %s; %s ran over, by %s.'
             % (C.num(len(under)), C.usd(under_amt), C.num(len(over)), C.usd(over_amt)),
             ['nunder', 'under', 'nover', 'overamt'],
             {'a': N(len(under)), 'b': U(under_amt), 'c': N(len(over)), 'd': U(over_amt)},
             so='The net figure hides money moving both ways: the overruns sit inside it, '
                'netted against the leftovers.'),
         con('Only %s line ran over as a whole: a transfer to a special revenue fund, by %s.'
             % (C.num(len(dep_over)), C.usd(-xo['available'])), ['ndep', 'left', 'owed', 'rev'],
             {'a': N(len(dep_over)), 'b': U(-xo['available'])},
             so='Account by account the year had misses both ways; department by department it '
                'almost always landed under.'),
         con('%s left %s at its close, as printed, with no orders shown still owed.'
             % (C.fy(2025), C.usd(t25['available'])), ['left25', 'foot'],
             {'y': F(2025), 'a': U(t25['available'])},
             so='The two years are not on one footing, so the difference between them is not a '
                'measure of anything until the FY2025 orders owed are known.',
             so_allow=('FY2025',))],
        chart=TP.ranking(
            'Money left by department',
            [(dn[d], live[d]['available']) for d in shown], '$',
            note='%s, period 13, the closed year. Departments that left at least %s.'
                 % (C.fy(2026), C.usd(10000)),
            note_figures={'y': F(2026), 'b': U(10000)}, note_allow=('13',)),
        table=dict(caption='Every town department at the %s close' % C.fy(2026), views=views),

        sources=[src['d-p13'], src['d-tot'], src['d-ledger']],
        finding_figures={'y': F(2026), 'a': U(left26), 'r': U(rev26), 'p': P(left_pct, 1)},
        flow=['finding', TP.cite(('chart', 0), 'd-p13', 'd-tot'), ('conclusion', 0),
              ('conclusion', 1), ('conclusion', 2),
              TP.cite(('table', 0), 'd-p13', 'd-ledger'), ('conclusion', 3), 'sources'])

    # ------------------------------------------------ the hub
    link = 'fy2026-town-departments'
    tp_figs = []

    def tp(text, to, *figs):
        tp_figs.extend(figs)
        return dict(text=text, href=REG.path(to), page=REG.TOPICS[to][0])

    def h_point(r):
        u_ = r['available']
        U_, P_ = C.usd(abs(u_)), C.pct(100 * abs(u_) / r['revised'], 0)
        if u_ > 0:
            text = '%s left %s of its budget unspent, %s.' % (aname(r), U_, P_)
        else:
            text = '%s ran %s past its budget, %s over.' % (aname(r), U_, P_)
        return tp(text, link, U_, P_)

    groups = [
        dict(title='How big', points=[
            tp('Town (non-school) departments closed %s %s under a %s budget: %s.'
               % (C.fy(2026), C.usd(left26), C.usd(rev26), C.pct(left_pct, 1)),
               link, C.usd(left26), C.usd(rev26), C.pct(left_pct, 1)),
            tp('%s accounts left %s; %s ran over by %s. No operating department was over as a whole.'
               % (C.num(len(under)), C.usd(under_amt), C.num(len(over)), C.usd(over_amt)),
               link, C.num(len(under)), C.usd(under_amt), C.num(len(over)), C.usd(over_amt)),
            tp('%s left %s as printed, with no orders still owed shown, so the two years are '
               'not on one footing.' % (C.fy(2025), C.usd(t25['available'])),
               link, C.usd(t25['available']))]),
        dict(title='Where it came from', points=[
            tp('Insurance netted %s under: school retirees’ health insurance left %s while town '
               'retirees’ ran %s over and active employees’ %s over.'
               % (C.usd(ins['available']), C.usd(sr['available']), C.usd(-tr_['available']),
                  C.usd(-ta['available'])),
               link, C.usd(ins['available']), C.usd(sr['available']), C.usd(-tr_['available']),
               C.usd(-ta['available'])),
            tp('The %s Reserve Fund was not used; the salary reserve moved %s out to departments.'
               % (C.usd(rf['original']), C.usd(sres_moved)),
               link, C.usd(rf['original']), C.usd(sres_moved)),
            tp('Police left %s, %s of it on two salary accounts.'
               % (C.usd(pol['available']), C.usd(sum(r['available'] for r in pol_h))),
               link, C.usd(pol['available']), C.usd(sum(r['available'] for r in pol_h))),
        ]),
        dict(title='During the year', points=[
            tp('Transfers to capital and stabilization were voted at %s and grew to %s during '
               'the year, all of it moved.' % (C.usd(tr_o), C.usd(tr_e)),
               link, C.usd(tr_o), C.usd(tr_e)),
            tp('Snow removal’s budget went from %s to %s and closed with nothing left.'
               % (C.usd(sn['original']), C.usd(sn['revised'])),
               link, C.usd(sn['original']), C.usd(sn['revised']))]),
        dict(title='Heavily underspent', points=[h_point(r) for r in hu]),
        dict(title='Heavily overspent', points=[h_point(r) for r in ho]),
    ]
    points = TB.custom(
        'talking-points', 'What the town year shows', dict(groups=groups), place='lead',
        figures=tuple(tp_figs) + (C.fy(2025), C.fy(2026)),
        allow=tuple({p_['href'] for g in groups for p_ in g['points']}),
        basis=('record', 'the town’s closed-year general fund reports'),
        alt='The town year’s talking points, each linked to the page that shows it.',
        so=('Heavily means at least %s and at least %s of the account’s budget, either way. '
            'Each point is a measurement; none of them says why.'
            % (C.usd(BIG), C.pct(SHARE, 0)), {'b': U(BIG), 's': figure(SHARE, C.pct(SHARE, 0))},
            ()))

    chart = TB.chart(TP.ranking(
        'Accounts furthest from budget',
        [(aname(r), [r['available'], 0]) for r in hu]
        + [(aname(r), [0, -r['available']]) for r in ho], '$',
        stack=['Left unspent', 'Ran past budget'],
        note='%s, period 13. Accounts at least %s and %s from their budget. Snow overtime, '
             'paid below zero, is left out.' % (C.fy(2026), C.usd(BIG), C.pct(SHARE, 0)),
        note_figures={'y': F(2026), 'b': U(BIG), 's': figure(SHARE, C.pct(SHARE, 0))},
        note_allow=('13',)),
        place='lead',
        so=('The largest misses run both ways, and three of them sit in one department: '
            'insurance.', None, ()))

    big = TB.custom('big-figures', 'The town leftover', dict(figures=[
        dict(value=C.usd(left26), kind='published', tag='Official, the Town’s closed-year report',
             label='left unspent by town departments, %s' % C.fy(2026)),
        dict(value=C.usd(ceiling), kind='estimate', tag='Our sum',
             label='if the %s still owed at the close were released' % C.usd(owed26))]),
        place='lead', figures=(C.usd(left26), C.usd(ceiling), C.usd(owed26), C.fy(2026)),
        alt='The FY2026 town leftover: the official figure, and the higher figure if every '
            'order still owed were released.',
        so=('The official figure is what the year closed on. The higher one is our sum: the '
            'same ledger, with orders still owed at the close counted as unspent.', None, ()))

    why = TB.explain('Why this page exists', [
        'This is the town (non-school) budget’s year end, the counterpart of the school '
        'budget’s. It holds what matters most from the closed-year report, a sentence each; '
        'every point links to the page with the evidence.'], place='end', tone='plain')

    if not (hu[0] is sr and ho[0] is tr_):
        fail('the answer says the largest misses both ways were in health insurance')
    out[HUB] = TP.hub(
        HUB,
        'This is the town (non-school) budget’s year end. Town departments closed %s %s under a '
        '%s budget; the largest misses, both ways, were in health insurance.'
        % (C.fy(2026), C.usd(left26), C.usd(rev26)),
        None, blocks=[big, chart, points, why],
        answer_figures={'y': F(2026), 'a': U(left26), 'r': U(rev26)})
    out[HUB]['group_figures'] = {
        'By department': '%s left' % C.usd(left26),
        'June readings': 'before the close',
    }
    if set(out[HUB]['group_figures']) != {g for g, _ in REG.category(HUB)['groups']}:
        fail('the section figures no longer name the registry’s sections')

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
        stale = [os.path.relpath(p, ROOT) for p, text in outs.items()
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != text]
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('fy2026-town-closeout topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
