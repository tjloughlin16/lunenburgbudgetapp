#!/usr/bin/env python3
"""Every department's budget, FY2010 to FY2025, and why only the schools show a gap.

    python3 scripts/build_department_budgets.py           # write the payload, the markdown, the charts
    python3 scripts/build_department_budgets.py --check   # fail if any of them is stale

TJ, 5 October 2026: "start to build modeling for budgeting for other departments now, and
see why other departments don't create or have deficits compared to the schools."

WHAT THIS MEASURES, AND THE ONE THING IT CANNOT.

The Finance Committee's general fund history (`sources/data/gl-history.csv`) gives every
department's ORIGINAL budget, its transfers, its REVISED budget and what it actually spent,
FY2010-FY2025, by MUNIS account. So four questions have measured answers:

  1. how fast each part of the budget's STARTING figure grew, budget to budget (rule 1:
     original against original, never an actual against a budget);
  2. which part pulls hardest on the levy -- share times growth above the levy limit's own
     growth (rule 4: rank by pull, never by size or rate);
  3. how each department spends its budget once it has it -- what is left unspent, what
     reached it by transfer, and whether anyone ends a year over;
  4. the schools against the rest with health insurance on the same footing.

The fifth -- why the schools report a "deficit" and the town's departments do not -- is NOT
answerable from this ledger, because a deficit in that sense is level-service NEED minus
what revenue allows, and nothing in a ledger records need. What the ledger can do is rule
things out: it shows neither side ends a year over its budget, so the word does not mean
an operating deficit. The explanations that remain are hypotheses and are written as such.

GROUPS ARE OURS. The ledger codes each department to a MUNIS function (the account's
second segment). Those are used as booked in one table. The comparison groups below are
OUR grouping, chosen so that like is measured against like, and the page says so:

  schools            department 300 and 301, LESS the employee-benefit objects inside them
  town departments   functions 1, 2, 4, 5, 6 -- less the Reserve Fund and Salary Reserve,
                     which are pools transferred out to other departments during the year
  insurance & benefits  every 5700xx benefit object in the school department, plus all of
                     function 9 (health, Medicare, life, workers' comp, unemployment,
                     liability)
  county retirement  department 820
  debt               function 7
  assessments        Monty Tech (310), state assessments (825), regional planning (841)
  reserves           132 Reserve Fund, 133 Salary Reserve

WHY HEALTH INSURANCE COMES OUT OF BOTH SIDES rather than being allocated. The school's own
health insurance is booked inside the school department; the town's is booked in a
separate Insurance department, which until FY2022 also carried every retiree's insurance,
the school's retirees included, in one undivided line. Any allocation of that line would
be OUR number. Taking benefits out of both sides needs no allocation at all, so it is the
headline method; the as-booked comparison and the one comparison the ledger's own labels
support (FY2022 on, where a SCHOOL RETIREES line exists) are shown beside it.

THE BENCHMARK IS THE LEVY LIMIT, LESS VOTED OVERRIDES. DLS certifies the limit each year
(`dls-new-growth.csv`, `prior_levy_limit` -- the limit of the year BEFORE the row's fy).
It grows by 2.5% plus new growth, and an override raises it. The FY2025 school override is
subtracted (compounded at 2.5% to the last year) so the benchmark is what the levy could
grow by without a vote. That choice is OURS and is named as ours on the page.
"""
import argparse
import html
import collections
import csv
import json
import math
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

import conclusions as C  # noqa: E402
from conclusions import conclusion, emit, figure  # noqa: E402

ID = 'department-budgets'
GL = os.path.join(ROOT, 'sources', 'data', 'gl-history.csv')
NEW_GROWTH = os.path.join(ROOT, 'sources', 'data', 'dls-new-growth.csv')
OVERRIDES = os.path.join(ROOT, 'sources', 'data', 'dls-override-votes.csv')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
FY27_TOWN = os.path.join(ROOT, 'sources', 'data', 'town-budget-fy26-fy27.csv')
OUT_MD = os.path.join(ROOT, 'sources', 'analyses', '%s.md' % ID)
OUT_JSON = os.path.join(ROOT, 'fy28', 'public', 'data', '%s.json' % ID)
CHART_DIR = os.path.join(ROOT, 'sources', 'analyses', 'charts')
DOR_CODE = '162'
LEVY_RATE = 0.025          # Proposition 2 1/2, statutory -- used ONLY to carry an override forward

# Employee-benefit objects. Every one is a 5700xx object whose printed description names an
# insurance or a benefit -- read off the ledger, listed here so the choice is reviewable.
BENEFIT_OBJECTS = {
    '570001': 'health insurance', '570002': 'life insurance', '570003': 'Medicare',
    '570004': 'insurance cost control', '570005': "workers' compensation",
    '570008': 'unemployment compensation', '570009': 'town retirees health insurance',
    '570010': 'liability insurance', '570016': 'Chapter 32B committee expenses',
    '570018': 'school retirees health insurance',
}
SCHOOL_DEPTS = ('300', '301')
RESERVE_DEPTS = ('132', '133')
ASSESSMENT_DEPTS = ('310', '825', '841')
RETIREMENT_DEPT = '820'
SCHOOL_RETIREES_OBJECT = '570018'
TOWN_RETIREES_OBJECT = '570009'
SNOW_DEPT = '423'

GROUPS = [
    ('schools', 'Schools', 'the school department, with its health insurance and other '
     'benefits taken out'),
    ('town', 'Town departments', 'general government, public safety, public works, human '
     'services, culture and recreation, less the two reserve pools'),
    ('benefits', 'Insurance & benefits', 'health, Medicare, life, workers’ compensation, '
     'unemployment and liability insurance, from both sides'),
    ('retirement', 'County retirement', 'the Worcester Regional Retirement System '
     'assessment, for town and school members alike'),
    ('debt', 'Debt', 'principal and interest on the town’s borrowing'),
    ('assessments', 'Assessments', 'Monty Tech, the state’s cherry sheet charges and the '
     'regional planning commission'),
    ('reserves', 'Reserves', 'the Reserve Fund and the Salary Reserve, transferred out to '
     'departments during the year'),
]
GROUP_NAME = {k: n for k, n, _ in GROUPS}

# The town's MUNIS function codes, as the account string carries them. Checked against
# the department names in the ledger: every department sits in exactly one function, and
# the names fit (police and fire in 2, the school and Monty Tech in 3, debt in 7, the
# retirement and state assessments in 8, insurance in 9). Two are coded where a reader
# might not look: Facilities & Grounds (193) and Parks & Recreation (650) are in 4.
FUNCTIONS = {
    '1': 'General government', '2': 'Public safety', '3': 'Education',
    '4': 'Public works & facilities', '5': 'Human services', '6': 'Culture & recreation',
    '7': 'Debt service', '8': 'Retirement & state assessments',
    '9': 'Insurance & benefits (town side)',
}

WORDS = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
         'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen']


def word(n):
    return WORDS[n] if 0 <= n < len(WORDS) else C.num(n)


ACRONYMS = {'WRRS', 'MTC', 'IT'}


def nice(name):
    """The ledger prints names in capitals; this is them in ordinary case, acronyms kept."""
    return ' '.join(w if w in ACRONYMS else w[:1] + w[1:].lower() for w in name.split())


def f(x):
    return float(x) if x not in (None, '') else 0.0


def signed_points(x):
    """A pull, in points a year, with a typographic minus."""
    s = '%.2f' % abs(x)
    return ('+' if x >= 0 else '−') + s + ' points'


def rate_pct(x):
    return C.pct(x * 100)


def cagr(a, b, n):
    return (b / a) ** (1.0 / n) - 1 if a > 0 and b > 0 and n > 0 else None


# ---------------------------------------------------------------- loading

def load_gl():
    rows = [r for r in csv.DictReader(open(GL, encoding='utf-8'))
            if r['sheet'] == 'general_fund']
    if not rows:
        raise SystemExit('REFUSED: no general_fund rows in %s' % GL)
    return rows


def function_of(r):
    return r['account'].split('-')[1]


def group_of(r):
    d, fn = r['department_code'], function_of(r)
    if d in SCHOOL_DEPTS:
        return 'benefits' if r['object'] in BENEFIT_OBJECTS else 'schools'
    if d in RESERVE_DEPTS:
        return 'reserves'
    if fn == '9':
        return 'benefits'
    if d == RETIREMENT_DEPT:
        return 'retirement'
    if fn == '7':
        return 'debt'
    if d in ASSESSMENT_DEPTS:
        return 'assessments'
    if fn in ('1', '2', '4', '5', '6'):
        return 'town'
    raise SystemExit('REFUSED: account %s (department %s, function %s) falls in no group'
                     % (r['account'], d, fn))


def load_levy():
    """Levy limit by fiscal year: the `prior_levy_limit` printed on the NEXT year's row."""
    lim = {}
    for r in csv.DictReader(open(NEW_GROWTH, encoding='utf-8')):
        if r['dor_code'] == DOR_CODE and r['prior_levy_limit']:
            lim[int(r['fy']) - 1] = float(r['prior_levy_limit'])
    ovr, both = [], []
    for r in csv.DictReader(open(OVERRIDES, encoding='utf-8')):
        if r['dor_code'] != DOR_CODE or r['vote_type'] != 'Override':
            continue
        row = dict(fy=int(r['fy']), amount=float(r['amount']), date=r['vote_date'],
                   description=r['description'], result=r['result'])
        if r['result'] == 'WIN':
            ovr.append(row)
        # The override questions that named BOTH sides, as DLS records the description.
        if 'town and school' in r['description'].lower():
            both.append(row)
    return lim, ovr, both


# ---------------------------------------------------------------- measuring

M = ('original', 'transfers_1', 'transfers_2', 'revised', 'actual')


def tally(rows, key):
    out = collections.defaultdict(lambda: collections.defaultdict(lambda: dict.fromkeys(M, 0.0)))
    for r in rows:
        k = key(r)
        if k is None:
            continue
        cell = out[k][int(r['fiscal_year'])]
        for m in M:
            cell[m] += f(r[m])
    return out


def growth_row(series, first, last, total_first, levy_ex):
    a, b = series.get(first, {}).get('original', 0.0), series.get(last, {}).get('original', 0.0)
    g = cagr(a, b, last - first)
    steps = []
    for y in range(first + 1, last + 1):
        p, c = series.get(y - 1, {}).get('original', 0.0), series.get(y, {}).get('original', 0.0)
        if p > 0 and c > 0:
            steps.append((y, c / p - 1))
    share = a / total_first if total_first else 0.0
    big = max(steps, key=lambda s: abs(s[1])) if steps else (None, None)
    return dict(first=a, last=b, rate=g, share_first=share,
                pull=(share * (g - levy_ex) * 100) if g is not None else None,
                median_step=statistics.median(s for _, s in steps) if steps else None,
                big_step_fy=big[0], big_step=big[1],
                series={str(y): round(series.get(y, {}).get('original', 0.0), 2)
                        for y in range(first, last + 1)})


def execution_row(series, years):
    rv = sum(series.get(y, {}).get('revised', 0.0) for y in years)
    ac = sum(series.get(y, {}).get('actual', 0.0) for y in years)
    og = sum(series.get(y, {}).get('original', 0.0) for y in years)
    tin = sum(series.get(y, {}).get('transfers_1', 0.0) for y in years)
    tout = sum(series.get(y, {}).get('transfers_2', 0.0) for y in years)
    resid = sum(series.get(y, {}).get('revised', 0.0) - series.get(y, {}).get('original', 0.0)
                - series.get(y, {}).get('transfers_1', 0.0)
                - series.get(y, {}).get('transfers_2', 0.0) for y in years)
    over_orig = [y for y in years if series.get(y, {}).get('actual', 0.0)
                 > series.get(y, {}).get('original', 0.0) + 1.0]
    over_rev = [y for y in years if series.get(y, {}).get('actual', 0.0)
                > series.get(y, {}).get('revised', 0.0) + 1.0]
    return dict(original=og, revised=rv, actual=ac, turnback=rv - ac,
                spent=(ac / rv) if rv else None, turnback_rate=((rv - ac) / rv) if rv else None,
                net_transfers=tin + tout, residual=resid,
                over_original=over_orig, over_revised=over_rev)


def measure():
    rows = load_gl()
    years = sorted({int(r['fiscal_year']) for r in rows})
    first, last = years[0], years[-1]
    partial = sorted({int(r['fiscal_year']) for r in rows if r['actual_is_partial'] == 'true'})
    exec_years = [y for y in years if y not in partial]
    exec_last = exec_years[-1]

    lim, ovr, both = load_levy()
    for y in (first, last):
        if y not in lim:
            raise SystemExit('REFUSED: no DLS levy limit for FY%d' % y)
    in_window = [o for o in ovr if first < o['fy'] <= last]
    carried = sum(o['amount'] * (1 + LEVY_RATE) ** (last - o['fy']) for o in in_window)
    n = last - first
    levy_with = cagr(lim[first], lim[last], n)
    levy_ex = cagr(lim[first], lim[last] - carried, n)
    levy_ex_prev = cagr(lim[first], lim[last - 1] - sum(
        o['amount'] * (1 + LEVY_RATE) ** (last - 1 - o['fy']) for o in in_window
        if o['fy'] <= last - 1), n - 1)

    by_group = tally(rows, group_of)
    by_func = tally(rows, function_of)
    by_dept = tally(rows, lambda r: r['department_code'])
    names = {}
    dept_group, dept_func = {}, {}
    for r in rows:
        names[r['department_code']] = r['department']
        dept_func[r['department_code']] = function_of(r)
        dept_group.setdefault(r['department_code'], set()).add(group_of(r))
    tot = {y: sum(by_dept[d][y]['original'] for d in by_dept) for y in years}

    groups = []
    for k, name, about in GROUPS:
        g = growth_row(by_group[k], first, last, tot[first], levy_ex)
        g.update(key=k, name=name, about=about,
                 share_last=by_group[k][last]['original'] / tot[last],
                 rate_prev=cagr(by_group[k][first]['original'],
                                by_group[k][last - 1]['original'], n - 1),
                 execution=execution_row(by_group[k], exec_years))
        groups.append(g)
    gsum = sum(by_group[k][first]['original'] for k in by_group)
    if abs(gsum - tot[first]) > 0.5:
        raise SystemExit('REFUSED: groups sum to %.2f against a fund total of %.2f'
                         % (gsum, tot[first]))

    funcs = []
    for code in sorted(by_func):
        g = growth_row(by_func[code], first, last, tot[first], levy_ex)
        g.update(code=code, name=FUNCTIONS.get(code, 'function %s' % code),
                 share_last=by_func[code][last]['original'] / tot[last])
        funcs.append(g)
    unknown = [c for c in by_func if c not in FUNCTIONS]
    if unknown:
        raise SystemExit('REFUSED: function codes with no name: %s' % unknown)

    depts = []
    for d in sorted(by_dept):
        g = growth_row(by_dept[d], first, last, tot[first], levy_ex)
        g.update(code=d, name=nice(names[d]), function=dept_func[d],
                 groups=sorted(dept_group[d]),
                 execution=execution_row(by_dept[d], exec_years))
        depts.append(g)

    # ---- like for like
    def sum_where(pred, y, m='original'):
        return sum(f(r[m]) for r in rows if int(r['fiscal_year']) == y and pred(r))

    is_school_dept = lambda r: r['department_code'] in SCHOOL_DEPTS
    school_booked = {y: sum_where(is_school_dept, y) for y in years}
    school_health = {y: sum_where(lambda r: is_school_dept(r) and r['object'] == '570001', y)
                     for y in years}
    retiree_years = [y for y in years if sum_where(
        lambda r: r['object'] == SCHOOL_RETIREES_OBJECT, y) > 0]
    labelled_first = retiree_years[0] if retiree_years else None
    lfl = dict(
        booked=dict(schools=cagr(school_booked[first], school_booked[last], n),
                    town=groups[1]['rate'],
                    schools_first=school_booked[first], schools_last=school_booked[last]),
        benefits_out=dict(schools=groups[0]['rate'], town=groups[1]['rate']),
        school_health=dict(first=school_health[first], last=school_health[last],
                           rate=cagr(school_health[first], school_health[last], n)),
    )
    if labelled_first:
        ln = last - labelled_first
        s_lab = {y: school_booked[y] + sum_where(
            lambda r: r['object'] == SCHOOL_RETIREES_OBJECT, y) for y in (labelled_first, last)}
        t_lab = {y: by_group['town'][y]['original'] + sum_where(
            lambda r: r['object'] == TOWN_RETIREES_OBJECT, y) for y in (labelled_first, last)}
        lfl['labelled'] = dict(
            first=labelled_first, last=last,
            schools=cagr(s_lab[labelled_first], s_lab[last], ln),
            town=cagr(t_lab[labelled_first], t_lab[last], ln),
            schools_first=s_lab[labelled_first], schools_last=s_lab[last],
            town_first=t_lab[labelled_first], town_last=t_lab[last])

    # ---- the residual: what entered a revised budget outside any recorded transfer
    acct = {(r['account'], int(r['fiscal_year'])): r for r in rows}
    pos = neg = fit = 0
    pos_amt = fit_amt = 0.0
    res_years = collections.Counter()
    for (a, y), r in acct.items():
        res = f(r['revised']) - f(r['original']) - f(r['transfers_1']) - f(r['transfers_2'])
        if abs(res) < 0.5:
            continue
        res_years[y] += 1
        if res < 0:
            neg += 1
            continue
        pos += 1
        pos_amt += res
        prev = acct.get((a, y - 1))
        if prev and f(prev['revised']) - f(prev['actual']) >= res - 0.5:
            fit += 1
            fit_amt += res
    residual = dict(rows=pos + neg, positive=pos, negative=neg, amount=pos_amt,
                    bounded_rows=fit, bounded_amount=fit_amt,
                    account_years=len(acct), years_with=len(res_years))

    # ---- departments that end a year over their revised budget
    over_rev = [(d['code'], d['name'], y) for d in depts for y in d['execution']['over_revised']]
    operating = {d['code'] for d in depts if set(d['groups']) & {'schools', 'town'}}
    op_over = [(c, n_, y) for c, n_, y in over_rev if c in operating]

    # The school lines that moved most into the last year, by dollars -- derived so the
    # hypothesis that names them cannot name the wrong ones.
    moves = collections.defaultdict(lambda: [0.0, 0.0, ''])
    for r in rows:
        if r['department_code'] in SCHOOL_DEPTS and r['object'] not in BENEFIT_OBJECTS:
            y = int(r['fiscal_year'])
            if y in (last - 1, last):
                k = r['org_desc']
                moves[k][0 if y == last - 1 else 1] += f(r['original'])
    school_moves = sorted(([k, v[0], v[1]] for k, v in moves.items()),
                          key=lambda x: -(x[2] - x[1]))[:3]
    snow = next(d for d in depts if d['code'] == SNOW_DEPT)

    return dict(first=first, last=last, exec_years=exec_years, exec_last=exec_last,
                partial=partial, levy=lim, op_over=op_over, both_sides=both, school_moves=school_moves,
                years=years, overrides=in_window, carried=carried,
                levy_with=levy_with, levy_ex=levy_ex, levy_ex_prev=levy_ex_prev,
                total=tot, total_rate=cagr(tot[first], tot[last], n),
                groups=groups, funcs=funcs, depts=depts, lfl=lfl, residual=residual,
                over_revised=over_rev, snow=snow, n_depts=len(depts))


# ---------------------------------------------------------------- conclusions

def yfig(y):
    return figure(int(y), C.fy(y), 'fiscal year')


def spanfig(a, b):
    return figure([int(a), int(b)], C.fyspan(a, b), 'fiscal years')


def over_line(op_over):
    """Who among the school and town departments ever ended a year over its final budget."""
    names = sorted({n_ for _, n_, _ in op_over})
    times = {1: 'once', 2: 'twice'}.get(len(op_over), '%s times' % word(len(op_over)))
    if not op_over:
        return 'No school or town department ended any year over its final budget.'
    if len(names) == 1:
        return ('No school or town department ended a year over budget except %s, %s.'
                % (names[0].lower(), times))
    return ('Only %s school or town departments ever ended a year over their final budget.'
            % word(len(names)))


def build_conclusions(m):
    G = {g['key']: g for g in m['groups']}
    sch, town, ret = G['schools'], G['town'], G['retirement']
    first, last, xl = m['first'], m['last'], m['exec_last']
    span = C.fyspan(first, last)
    xspan = C.fyspan(first, xl)
    nx = len(m['exec_years'])
    rows = []

    t_rate, s_rate = rate_pct(town['rate']), rate_pct(sch['rate'])
    tp, sp = rate_pct(town['rate_prev']), rate_pct(sch['rate_prev'])
    booked = rate_pct(m['lfl']['booked']['schools'])
    rows.append(conclusion(
        id='town-departments-grew-faster-than-the-schools',
        claim='Town departments’ starting budgets grew %s a year; the schools’ grew %s.'
              % (t_rate, s_rate),
        so_what='%s, with health insurance taken out of both so they are measured alike.'
                % span,
        figures={'t': figure(town['rate'] * 100, t_rate, 'a year, town departments'),
                 's': figure(sch['rate'] * 100, s_rate, 'a year, the schools'),
                 'tp': figure(town['rate_prev'] * 100, tp, 'a year, town, to FY%d' % (last - 1)),
                 'sp': figure(sch['rate_prev'] * 100, sp, 'a year, schools, to FY%d' % (last - 1)),
                 'b': figure(m['lfl']['booked']['schools'] * 100, booked,
                             'a year, schools as booked'),
                 'span': spanfig(first, last), 'ovr': yfig(last)},
        figure='t', kind='measured', bearing='sizes',
        detail='Measured on each year’s ORIGINAL budget, budget to budget. Stopping a year '
               'earlier, before the FY%d override, the gap is wider: town %s, schools %s. '
               'With the school’s own health insurance left in, as the ledger books it, '
               'the schools grew %s.' % (last, tp, sp, booked),
        basis='Finance Committee general fund history, ORIGINAL budget by account; our '
              'grouping, stated on the page.',
        not_shown='A budget line is net: grants, circuit breaker and fees pay school costs '
                  'this ledger never sees, so slower appropriation growth is not slower '
                  'cost growth. Nor is it need.',
        see=[('/when-grants-end', 'When grants end')],
    ))

    pt, ps = signed_points(town['pull']), signed_points(sch['pull'])
    lx = rate_pct(m['levy_ex'])
    rows.append(conclusion(
        id='ranked-by-pull-town-departments-lead',
        claim='Ranked by pull on the levy, town departments lead at %s a year.' % pt,
        so_what='The schools sit at %s: their starting budget grew slower than the levy '
                'limit’s %s.' % (ps, lx),
        figures={'pt': figure(town['pull'], pt, 'a year of pull, town departments'),
                 'ps': figure(sch['pull'], ps, 'a year of pull, schools'),
                 'lx': figure(m['levy_ex'] * 100, lx, 'a year, levy limit less overrides'),
                 'y0': yfig(first)},
        figure='pt', kind='measured', bearing='sizes',
        detail='Pull is each group’s %s share of the budget times how far its growth ran '
               'above the levy limit’s, so it weighs size and speed together. The levy '
               'benchmark has the voted override taken back out — our choice, so it '
               'measures what the levy grows by without a vote.' % C.fy(first),
        basis='Original budgets as above; DLS certified levy limits and the DLS override '
              'register.',
        not_shown='The levy is not all revenue: state aid and local receipts pay part of '
                  'every line. Debt is partly paid outside the limit by exclusions.',
    ))

    rr = rate_pct(ret['rate'])
    rows.append(conclusion(
        id='the-county-retirement-assessment-grew-fastest',
        claim='The county retirement assessment grew %s a year — the fastest of any group.'
              % rr,
        so_what='It pays pensions for town and school members alike, and nothing published '
                'splits it.',
        figures={'r': figure(ret['rate'] * 100, rr, 'a year, county retirement'),
                 'a': figure(ret['first'], C.usd(ret['first']), 'in %s' % C.fy(first)),
                 'b': figure(ret['last'], C.usd(ret['last']), 'in %s' % C.fy(last)),
                 'y0': yfig(first), 'y1': yfig(last)},
        figure='r', kind='measured', bearing='sizes',
        detail='From %s in %s to %s in %s. It sits on the town’s side of the ledger, so a '
               'school-versus-town comparison that leaves it there flatters the schools by '
               'whatever their share of it is.' % (C.usd(ret['first']), C.fy(first),
                                                   C.usd(ret['last']), C.fy(last)),
        basis='Department 820, WRRS assessment, original budget.',
        not_shown='The school share. Teachers are in the state’s system, not this one; '
                  'every other school employee who is a member is in it, unsplit.',
        see=[('/what-we-cannot-answer', 'What we cannot answer')],
    ))

    se, te = sch['execution'], town['execution']
    ss, ts = C.pct(se['spent'] * 100), C.pct(te['spent'] * 100)
    rows.append(conclusion(
        id='the-schools-leave-less-unspent',
        claim='The schools spent %s of their final budgets, %s; town departments %s.'
              % (ss, xspan, ts),
        so_what=over_line(m['op_over']),
        figures={'ss': figure(se['spent'] * 100, ss, 'of final budget spent, schools'),
                 'ts': figure(te['spent'] * 100, ts, 'of final budget spent, town'),
                 'tb': figure(te['turnback'], C.usd(te['turnback']), 'left unspent, town'),
                 'sb': figure(se['turnback'], C.usd(se['turnback']), 'left unspent, schools'),
                 'span': spanfig(first, xl), 'py': yfig(m['last'])},
        figure='ss', kind='measured', bearing='sizes',
        detail='Over the %s complete years the town departments left %s unspent and the '
               'schools %s. %s is excluded because its actual is part-year.'
               % (word(nx), C.usd(te['turnback']), C.usd(se['turnback']), C.fy(m['last'])),
        basis='REVISED budget against ACTUAL, summed by group, complete years only.',
        not_shown='Why. Unspent money can be a vacancy, a cautious estimate or a deferred '
                  'purchase; the ledger records the dollars, not the reason.',
    ))

    sn = m['snow']['execution']
    yrs = len(m['exec_years'])
    no = len(sn['over_original'])
    n_txt = '%d of %d years' % (no, yrs)
    rows.append(conclusion(
        id='snow-and-ice-is-the-budget-that-runs-over',
        claim='%s spent above its starting budget in %s.' % (m['snow']['name'], n_txt),
        so_what='It is the one budget state law lets run over; transfers then cover it.',
        figures={'n': figure(no, n_txt, 'years over the starting budget'),
                 'x': figure(sn['net_transfers'], C.usd(sn['net_transfers']),
                             'moved in by transfer, net')},
        figure='n', kind='measured', bearing='sizes',
        detail='Over the same years %s was moved into it by transfer, net. Massachusetts '
               'General Laws chapter 44, section 31D allows snow and ice spending past the '
               'appropriation if the appropriation is at least the prior year’s.'
               % C.usd(sn['net_transfers']),
        allow=('44', '31D'),
        basis='Department 423, original against actual; transfers in and out.',
        not_shown='Whether the starting figure is set low on purpose. That is how the '
                  'statute is commonly used, and nothing here tests it.',
    ))

    rs = m['residual']
    share_fit = rs['bounded_amount'] / rs['amount'] if rs['amount'] else 0.0
    ra, rf = C.usd(rs['amount']), C.pct(share_fit * 100, 0)
    rows.append(conclusion(
        id='money-reached-budgets-outside-any-recorded-transfer',
        claim='%s reached departments’ budgets mid-year with no transfer recorded for it.'
              % ra,
        so_what='%s of it fits money carried forward from the year before. That is a '
                'hypothesis.' % rf,
        figures={'a': figure(rs['amount'], ra, 'added outside recorded transfers, %s'
                             % span),
                 'f': figure(share_fit * 100, rf, 'of it within the prior year’s unspent'),
                 'r': figure(rs['positive'], C.num(rs['positive']), 'account-years')},
        figure='a', kind='hypothesis', bearing='sizes',
        detail='On %s account-years the revised budget exceeds original plus transfers. '
               'For %s of those dollars the same account had at least that much unspent '
               'the year before, which is what a carried-forward encumbrance would look '
               'like. The rest fits a supplemental appropriation.' % (C.num(rs['positive']), rf),
        basis='Revised minus original minus both transfer columns, by account and year.',
        not_shown='What any of it was. The ledger prints the revised figure, not the vote '
                  'or the carry-forward behind it.',
        see=[('/what-we-cannot-answer', 'What we cannot answer')],
    ))

    both = sorted(m['both_sides'], key=lambda o: -o['amount'])
    if both:
        big = both[0]
        amt = C.usd(big['amount'])
        rest = ' and '.join(C.usd(o['amount']) for o in both[1:])
        rows.append(conclusion(
            id='priced-at-level-service-the-town-showed-a-gap-too',
            claim='The %s override voted in %s was for town and school budgets alike.'
                  % (amt, big['date'][:4]),
            so_what='In a year the town priced level service, the ask covered its own '
                    'departments too.',
            figures={'o': figure(big['amount'], amt, 'override asked, town and school'),
                     'y': figure(int(big['date'][:4]), big['date'][:4], 'calendar year of the vote'),
                     **({'r': figure([o['amount'] for o in both[1:]], rest,
                                     'the other question')} if rest else {})},
            figure='o', kind='measured', bearing='lever',
            detail='Voted %s and lost%s; DLS records the larger as “%s”. That February the Town '
                   'Manager asked department heads for a level service budget, and the Select '
                   'Board then worked a balanced and an unbalanced budget department by '
                   'department. The ledger itself holds no request or level-service column '
                   'for any year, so a “deficit” is need minus revenue and need is not in it.'
                   % (big['date'], (', as was a second question for %s' % rest) if rest else '',
                      big['description']),
            allow=(big['date'], big['description']),   # DLS's own words, quoted
            basis='DLS override register; Finance Committee minutes, 12 February 2026; '
                  'Select Board minutes, 16 March 2026.',
            not_shown='Whether the town’s departments would have shown a gap in earlier years '
                      'if priced the same way. Their past requests to the Town Manager would '
                      'settle it.',
            see=[('/override', 'The override')],
        ))
    return rows


# ---------------------------------------------------------------- the markdown

def table(head, align, body):
    out = ['| ' + ' | '.join(head) + ' |',
           '|' + '|'.join('---:' if a == 'r' else '---' for a in align) + '|']
    out += ['| ' + ' | '.join(r) + ' |' for r in body]
    return '\n'.join(out) + '\n'


def rp(x):
    return '—' if x is None else ('%.1f%%' % (x * 100)).replace('-', '\u2212')


def pp(x):
    return '—' if x is None else ('%+.2f' % x).replace('-', '−')


def render_md(m, rows):
    G = {g['key']: g for g in m['groups']}
    first, last, xl = m['first'], m['last'], m['exec_last']
    w = []
    a = w.append
    a('# Every department’s budget, against the schools\n\n')
    a('**How fast each part of the general fund’s starting budget grew from %s to %s, '
      'which part pulls hardest on the levy, how each side spends what it is given — and '
      'what “deficit” can and cannot mean in this ledger.**\n\n' % (C.fy(first), C.fy(last)))
    a('Analysis, October 2026. A draft for review. Every figure is computed from the '
      'Finance Committee’s general fund history by `scripts/build_department_budgets.py`; '
      'the grouping, the benchmark and the treatment of health insurance are ours and are '
      'marked as ours where they are used.\n\n---\n\n')

    a('## The short version\n\n')
    for c in rows:
        tag = ' *(a hypothesis)*' if c['kind'] == 'hypothesis' else ''
        a('**%s**%s %s\n\n' % (c['claim'], tag, c['so_what']))
    a('---\n\n')

    # ---- growth
    a('## How each part of the budget grew\n\n')
    a('![Lines indexed to 100 in %s for each group’s starting budget and for the levy '
      'limit less overrides. Town departments end highest of the operating groups at %s a '
      'year; the schools run below the levy line at %s a year; county retirement climbs '
      'fastest; debt ends near where it began.](charts/%s-index.svg)\n\n'
      % (C.fy(first), rp(G['town']['rate']), rp(G['schools']['rate']), ID))
    a('### In plain terms\n\n')
    a('From %s to %s the general fund’s starting budget grew %s a year, from %s to %s. '
      'Town departments grew %s a year and the schools, with health insurance taken out, '
      '%s. The levy limit, with the %s override taken back out, grew %s a year — so the '
      'schools’ starting budget grew more slowly than the levy and the town’s faster.\n\n'
      % (C.fy(first), C.fy(last), rp(m['total_rate']), C.usd(m['total'][first]),
         C.usd(m['total'][last]), rp(G['town']['rate']), rp(G['schools']['rate']),
         C.fy(last), rp(m['levy_ex'])))
    a('### The evidence\n\n')
    body = []
    for g in m['groups']:
        body.append([g['name'], C.usd(g['first']), C.usd(g['last']), rp(g['rate']),
                     rp(g['rate_prev']), rp(g['median_step']),
                     '%s (%s)' % (rp(g['big_step']), C.fy(g['big_step_fy']))
                     if g['big_step_fy'] else '—',
                     '%.1f%%' % (g['share_first'] * 100), '%.1f%%' % (g['share_last'] * 100)])
    body.append(['**all**', '**%s**' % C.usd(m['total'][first]),
                 '**%s**' % C.usd(m['total'][last]), '**%s**' % rp(m['total_rate']),
                 '', '', '', '100%', '100%'])
    a(table(['group', C.fy(first), C.fy(last), 'a year', 'a year to %s' % C.fy(last - 1),
             'median year', 'largest single year', 'share %s' % C.fy(first),
             'share %s' % C.fy(last)], 'lrrrrrrrr', body))
    a('\n*a year* is compound growth of the ORIGINAL budget, budget to budget. *median '
      'year* and *largest single year* are there because a rate over fifteen years can be '
      'one step and fourteen flat years — read them before reading the rate.\n\n')
    a('**The levy limit**, from the Division of Local Services: %s in %s and %s in %s, '
      '%s a year. That includes %s voted by override (%s). Taken back out, carried '
      'forward at 2.5%%, the limit grew %s a year. **Our choice**: the benchmark is the '
      'second figure, because the question is what the levy grows by without a vote.\n\n'
      % (C.usd(m['levy'][first]), C.fy(first), C.usd(m['levy'][last]), C.fy(last),
         rp(m['levy_with']), C.usd(sum(o['amount'] for o in m['overrides'])),
         '; '.join('%s, %s, “%s”' % (C.fy(o['fy']), o['date'], o['description'])
                   for o in m['overrides']) or 'none', rp(m['levy_ex'])))
    a('### What this does not show\n\n')
    a('- **Cost.** A budget line is net (rule 11). The school appropriation is what the '
      'town raises after grants, circuit breaker, school choice and revolving funds have '
      'paid their part; a line that rises may mean a grant ended. The town’s lines are net '
      'too, of whatever receipts offset them.\n'
      '- **Need.** A starting budget is what was voted. It is the outcome of a request, a '
      'recommendation and a vote, and it does not say what level service would have '
      'cost.\n'
      '- **Service.** A department can hold its dollars and cut its hours, or gain dollars '
      'because a service moved into it from elsewhere. Several town lines show single-year '
      'steps large enough to be exactly that (see the department table).\n\n')

    # ---- pull
    a('## Which part pulls hardest on the levy\n\n')
    a('![Diverging bars, one per group, of pull on the levy in points a year. Town '
      'departments run furthest right at %s, county retirement next at %s; the schools at '
      '%s and debt at %s run left.](charts/%s-pull.svg)\n\n'
      % (pp(G['town']['pull']), pp(G['retirement']['pull']), pp(G['schools']['pull']),
         pp(G['debt']['pull']), ID))
    a('**Pull** is a group’s share of the %s budget times how far its growth ran above the '
      'levy limit’s %s a year, in points a year (rule 4). Neither size nor rate means '
      'anything alone: the schools are the largest group and pull the other way; county '
      'retirement is small and pulls hard.\n\n' % (C.fy(first), rp(m['levy_ex'])))
    body = [[g['name'], '%.1f%%' % (g['share_first'] * 100), rp(g['rate']), pp(g['pull'])]
            for g in sorted(m['groups'], key=lambda g: -g['pull'])]
    a(table(['group', 'share %s' % C.fy(first), 'a year', 'pull, points a year'],
            'lrrr', body))
    a('\n**As the town books it**, by MUNIS function — no grouping of ours. Function 3 is '
      'the school department with its health insurance in it, plus Monty Tech; function 9 '
      'is the town’s insurance department, which until %s also carried every retiree’s '
      'health insurance, the schools’ included.\n\n'
      % C.fy(m['lfl']['labelled']['first'] if m['lfl'].get('labelled') else last))
    body = [[f_['code'], f_['name'], C.usd(f_['first']), C.usd(f_['last']), rp(f_['rate']),
             pp(f_['pull'])] for f_ in sorted(m['funcs'], key=lambda x: -x['pull'])]
    a(table(['function', 'name', C.fy(first), C.fy(last), 'a year', 'pull'], 'llrrrr', body))
    a('\n### What this does not show\n\n')
    a('- **The levy is not all of the revenue.** State aid, local receipts and free cash '
      'pay for part of every line. The whole starting budget grew %s a year, slower than '
      'the levy limit — which says the rest of the revenue grew more slowly than the levy, '
      'or the levy was not raised to its limit, or both. This ledger cannot say which.\n'
      '- **Debt is not like for like.** Part of it is paid by debt exclusions, outside the '
      'levy limit altogether, so its pull against the limit is overstated in both '
      'directions.\n\n' % rp(m['total_rate']))

    # ---- like for like
    lfl = m['lfl']
    a('## The schools against the rest, like for like\n\n')
    a('The school department books its own employees’ health insurance inside its budget. '
      'The town books its employees’ insurance in a separate department, and until %s '
      'booked every retiree’s insurance there too, the schools’ retirees included, in one '
      'line. So the ledger’s own boundary puts a large, fast-moving cost on the school side '
      'for actives and on the town side for retirees.\n\n'
      % C.fy(lfl['labelled']['first'] if lfl.get('labelled') else last))
    a('**The method used for the headline is ours, and it allocates nothing**: every '
      'benefit object is taken out of the school department and set beside the town’s '
      'insurance department as one group. That needs no split of any shared line, which '
      'is why it was chosen over an allocation.\n\n')
    body = [
        ['as booked — school department whole, town departments', rp(lfl['booked']['schools']),
         rp(lfl['booked']['town']), C.fyspan(first, last)],
        ['**benefits out of both (the headline)**', '**%s**' % rp(lfl['benefits_out']['schools']),
         '**%s**' % rp(lfl['benefits_out']['town']), C.fyspan(first, last)],
    ]
    if lfl.get('labelled'):
        L = lfl['labelled']
        body.append(['by the ledger’s own labels — school retirees’ insurance to the '
                     'schools, town retirees’ to the town', rp(L['schools']), rp(L['town']),
                     C.fyspan(L['first'], L['last'])])
    a(table(['method', 'schools, a year', 'town departments, a year', 'years'], 'lrrl', body))
    a('\nThe school’s own health insurance line grew %s a year, %s to %s. The third '
      'method is the only allocation the ledger’s names support, and only from %s, when a '
      'line called SCHOOL RETIREES HLTH INSURANCE first appears; before that the retirees '
      'of both sides share one line and no year can be split without inventing the '
      'split.\n\n'
      % (rp(lfl['school_health']['rate']), C.usd(lfl['school_health']['first']),
         C.usd(lfl['school_health']['last']),
         C.fy(lfl['labelled']['first']) if lfl.get('labelled') else '—'))
    a('### What this does not show\n\n')
    a('- **The rest of what the town pays for the schools.** County retirement covers '
      'school members who are not teachers; Medicare, liability insurance and the '
      'facilities and technology departments may serve both sides. None is split in any '
      'published document, so in every method above those costs stay on the town’s side. '
      'These are registered gaps.\n'
      '- **Whether any service moved between the two sides** during the fifteen years. A '
      'move would show as growth on one side and a fall on the other, and the ledger '
      'alone cannot tell it from a real change.\n\n')

    # ---- departments
    a('## Department by department\n\n')
    a('Every department with a starting budget in both %s and %s, ranked by pull. The '
      '*largest single year* column is the first thing to read: a department whose growth '
      'is one step is a department that took something on or had something moved into it, '
      'and a rate measured across that step is not a trend (rule 6).\n\n'
      % (C.fy(first), C.fy(last)))
    ds = [d for d in m['depts'] if d['pull'] is not None]
    body = []
    for d in sorted(ds, key=lambda d: -d['pull']):
        body.append([d['code'], d['name'], GROUP_NAME[d['groups'][0]] if len(d['groups']) == 1
                     else ' / '.join(GROUP_NAME[g] for g in d['groups']),
                     C.usd(d['first']), C.usd(d['last']), rp(d['rate']), rp(d['median_step']),
                     '%s (%s)' % (rp(d['big_step']), C.fy(d['big_step_fy']))
                     if d['big_step_fy'] else '—', pp(d['pull'])])
    a(table(['dept', 'name', 'group', C.fy(first), C.fy(last), 'a year', 'median year',
             'largest single year', 'pull'], 'lllrrrrrr', body))
    gone = [d for d in m['depts'] if d['pull'] is None]
    a('\n%s departments have no starting budget in one of the two years and carry no '
      'rate: %s.\n\n' % (word(len(gone)).capitalize(),
                         ', '.join('%s (%s)' % (d['name'], d['code']) for d in gone)))

    # ---- execution
    xs = C.fyspan(first, xl)
    a('## How each side spends what it is given\n\n')
    a('%s, the complete years — %s is excluded because its actual is part-year. *Final '
      'budget* is the REVISED budget, after transfers. *Net transfers* nets transfers in '
      'against transfers out, so moves between a department’s own lines cancel. *Outside '
      'transfers* is revised minus original minus both transfer columns: money that '
      'reached the budget with no transfer recorded for it.\n\n' % (xs, C.fy(m['last'])))
    body = []
    for g in m['groups']:
        e = g['execution']
        body.append([g['name'], C.usd(e['revised']), C.usd(e['actual']), C.usd(e['turnback']),
                     rp(e['turnback_rate']), C.usd(e['net_transfers']), C.usd(e['residual'])])
    a(table(['group', 'final budget', 'spent', 'unspent', 'unspent rate', 'net transfers',
             'outside transfers'], 'lrrrrrr', body))
    a('\nA GROUP can end a year over while every department in it ends inside: the '
      'schools’ benefits were taken out of the school department above, and the school '
      'department moves money between its own lines. So whether anybody ran over is read '
      'department by department, below.\n')
    a('\n**Departments that ended a year over their final budget**, of %s departments '
      'across %s years: %s.\n\n'
      % (word(m['n_depts']), word(len(m['exec_years'])),
         '; '.join('%s (%s), %s' % (n_, c, C.fy(y)) for c, n_, y in m['over_revised'])
         or 'none'))
    a('State assessments are charged on the cherry sheet by the Commonwealth rather than '
      'spent by a department, so a year over budget there is a charge that arrived larger '
      'than estimated — that reading is ours, from what the line is, and the ledger does '
      'not state it.\n\n')
    big = sorted([d for d in m['depts'] if d['execution']['revised'] >= 300000],
                 key=lambda d: -d['execution']['turnback_rate'])
    body = []
    for d in big:
        e = d['execution']
        body.append([d['code'], d['name'], C.usd(e['revised']), C.usd(e['turnback']),
                     rp(e['turnback_rate']), C.usd(e['net_transfers']), C.usd(e['residual']),
                     str(len(e['over_original'])), str(len(e['over_revised']))])
    a('Every department with at least $300,000 of final budget across those years, most '
      'unspent first:\n\n')
    a(table(['dept', 'name', 'final budget', 'unspent', 'rate', 'net transfers',
             'outside transfers', 'years over starting', 'years over final'],
            'llrrrrrrr', body))
    rs = m['residual']
    a('\n### Money that arrived outside a recorded transfer\n\n')
    a('On %s of %s account-years — %s — the revised '
      'budget is not original plus the two transfer columns. All but %s of them are '
      'positive, adding %s in total. **A hypothesis, tested once**: if this is a '
      'carried-forward encumbrance, the same account must have had at least that much '
      'unspent the year before. %s of the %s account-years pass, carrying %s of the '
      'dollars; the rest do not and need another explanation — a supplemental '
      'appropriation at a special Town Meeting is the obvious candidate, and nothing here '
      'tests it.\n\n'
      % (C.num(rs['rows']), C.num(rs['account_years']),
         'every one of the %s years has some' % word(len(m['years']))
         if rs['years_with'] == len(m['years'])
         else '%s of the %s years have some' % (word(rs['years_with']), word(len(m['years']))),
         word(rs['negative']),
         C.usd(rs['amount']), C.num(rs['bounded_rows']), C.num(rs['positive']),
         C.usd(rs['bounded_amount'])))

    # ---- deficit
    a('## What “deficit” can mean here\n\n')
    a('**Not an operating deficit.** A Massachusetts department may not spend past its '
      'appropriation without a vote or a transfer, and the ledger shows it: %s The schools '
      'spend closer to their budget than the town’s departments do, and still end inside '
      'it.\n\n' % over_line(m['op_over']))
    a('**What the schools call a deficit is a planning figure**: what the district says '
      'level service would cost next year, minus what the town’s revenue allows it. That '
      'is need minus revenue, and need is not a column in any ledger. So this data can '
      'say how fast each side’s budget grew and how each side spent it; it cannot say '
      'whether either side’s budget was enough.\n\n')
    both = sorted(m['both_sides'], key=lambda o: -o['amount'])
    if both:
        a('**When the town priced level service, its departments showed a gap too.** On 12 '
          'February 2026 the Finance Committee’s minutes record that the Town Manager “has '
          'requested the department heads provide a level sever budget and provide an '
          'explanation for any line item above the level service request” (sic). On 16 '
          'March the Select Board worked through “the "balanced budget" and the '
          '"unbalanced budget," with the unbalanced budget representing the core services '
          'override scenario”, department by department. The override questions that '
          'followed, %s, were for both sides: %s. Compare %s, the one override won inside '
          'this ledger’s years, which DLS records as “%s”.\n\n'
          '[Finance Committee, 12 February 2026](/docs/minutes/text/finance-committee/'
          '2026-02-12-minutes-7645.txt) · [Select Board, 16 March 2026](/docs/minutes/text/'
          'select-board/2026-03-16-minutes-7716.txt)\n\n'
          % (both[0]['date'],
             '; '.join('%s, “%s”, %s' % (C.usd(o['amount']), o['description'],
                                         'lost' if o['result'] == 'LOSS' else 'won')
                       for o in both),
             '; '.join('%s in %s' % (C.usd(o['amount']), C.fy(o['fy']))
                       for o in m['overrides']) or 'none',
             '; '.join(o['description'] for o in m['overrides'])))
    if os.path.exists(FY27_TOWN):
        a('The FY2027 requested-against-balanced figures for the town’s departments are now '
          'in `sources/data/town-budget-fy26-fy27.csv`; they are not yet read by this '
          'report.\n\n')
    else:
        a('The one place a town department’s level-service figure might exist is its '
          'budget request to the Town Manager. For FY2027 those requests are being '
          'extracted separately; for every earlier year none is in this archive, and the '
          'gap is registered.\n\n')

    # ---- hypotheses
    a('## What could explain the difference — hypotheses, each with its test\n\n')
    a('None of these is established. Each is a reading that fits the measurements, '
      'written down with the document that would settle it.\n\n')
    hyp = [
        ('**The process.** The School Committee builds from need and publishes the '
         'shortfall; in most years the town’s departments are built to a revenue figure '
         'the Town Manager sets, so a shortfall is absorbed before it is ever a number. '
         'FY2027 is one test of it and fits: the year the town asked for level-service '
         'budgets, its side showed a gap too. One year is not a pattern.',
         'each town department’s request to the Town Manager against the recommendation, '
         'for several years.'),
        ('**Grants holding the school line down, then letting go.** The schools’ starting '
         'budget grew %s a year from %s to %s and then %s in %s alone, the year of the '
         'override. The lines that moved most into %s: %s. Federal relief money paying '
         'for costs like these in the middle years, and then ending, would produce that '
         'shape; so would an override restoring what earlier years had cut.'
         % (rp(G['schools']['rate_prev']), C.fy(first), C.fy(last - 1),
            rp(G['schools']['series'] and (G['schools']['last']
                                           / float(G['schools']['series'][str(last - 1)]) - 1)),
            C.fy(last), C.fy(last),
            '; '.join('%s, %s to %s' % (nice(k), C.usd(a_), C.usd(b_))
                      for k, a_, b_ in m['school_moves'])),
         'the district’s grant and revolving fund expenditures by year (DESE End of Year '
         'Financial Report, schedule 1 by fund).'),
        ('**The cost structure.** School costs are dominated by contracted salary '
         'schedules and placements the district must make; town costs include more '
         'discretionary lines that can be held.',
         'the share of each side’s budget in salaries and mandated placements, by '
         'object, with the contracts beside it.'),
        ('**Costs that sit on the town side but serve both.** County retirement, Medicare, '
         'retirees’ insurance before %s, and possibly facilities and technology.' %
         C.fy(lfl['labelled']['first'] if lfl.get('labelled') else last),
         'the WRRS valuation by member unit and the Chapter 32B enrollment schedule.'),
    ]
    for h, test in hyp:
        a('- %s *Would settle it:* %s\n' % (h, test))
    a('\n')

    a('## What this does not show\n\n')
    a('- Whether any budget was **adequate**. Growth of an appropriation is not growth of '
      'need, and a budget that grew slowly may have been cut or may have been enough.\n'
      '- **Cost**. Every figure is a net general fund appropriation; grants, fees, '
      'revolving and enterprise funds are not in it, on either side.\n'
      '- **People**. Dollars are not staff. Nothing here counts a position.\n'
      '- **%s actuals**. Part-year, and excluded from every spending measure.\n'
      '- **Whether the workbook is the books**. It was assembled from MUNIS exports by the '
      'Finance Committee; every year ties to its own printed Grand Total to the cent, and '
      'FY2024’s school lines agree with the period 13 ledger on 253 of 265 lines. That is '
      'strong, and it is still a workbook somebody assembled (rule 13a).\n\n'
      % C.fy(m['last']))

    a('## Gaps registered by this report\n\n')
    a('Each is a row in `sources/data/money-gaps.csv` and appears at '
      '[/what-we-cannot-answer](/what-we-cannot-answer):\n\n')
    for g in GAPS:
        a('- %s\n' % g[1])
    a('\nAlready registered and cited here: the school share of the county retirement '
      'assessment; the school share of the town’s health insurance before the retiree '
      'split; the school share of Medicare and the insurance reserves.\n\n')

    a('## Sources\n\n')
    for s in sources():
        a('- **%s** — %s `%s`%s\n' % (s['publisher'], s['note'], s['path'],
                                      (' sha256 `%s…`' % s['sha256'][:16]) if s['sha256'] else ''))
    a('\nComputed by `scripts/build_department_budgets.py`; every figure in the short '
      'version is recomputed independently by `scripts/verify_department_budgets.py`.\n')
    return ''.join(w)


# The gaps this report hit, as registered in money-gaps.csv. The text here is the `what`
# column -- the generator does not WRITE the registry (it is append-only and shared), it
# only lists what it relies on, and the verifier asserts each one is present.
GAPS = [
    ('money_out', 'What a level-service budget for each town department would have cost, '
     'year by year'),
    ('money_out', 'What the money was that reached departments’ revised budgets outside '
     'any recorded transfer'),
    ('money_out', 'Whether a town department’s budget growth is more service or a cost '
     'moved into it from another budget'),
    ('money_in', 'Why the general fund’s starting budget grew more slowly than the levy '
     'limit, FY2010 to FY2025'),
]


def sources():
    man = {}
    try:
        man = {r['key']: r for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    except OSError:
        pass
    out = []
    for key, pub, table_, note in (
        ('budget-workbooks/finance-committee/fy26-budget/general-fund-budget-vs-actuals-history.xlsx',
         'Lunenburg Finance Committee', 'gl_history',
         'the general fund budget against actual, every account, FY2010–FY2025, assembled '
         'from MUNIS exports; received by public records request on 4 October 2026. Read '
         'into sources/data/gl-history.csv by scripts/extract_gl_history.py.'),
        ('state-dls/new_growth-2026-09-26-3b8980b0efc3.xlsx',
         'Massachusetts Division of Local Services', 'dls_new_growth',
         'certified new growth and the prior year’s levy limit, every town, by year.'),
        ('state-dls/OverrideUnderrideVotes.xlsx',
         'Massachusetts Division of Local Services', 'dls_override_votes',
         'every Proposition 2½ override, underride and exclusion vote on record.'),
    ):
        r = man.get(key, {})
        out.append(dict(path='sources/' + key, sha256=r.get('sha256', ''),
                        bytes=int(r.get('bytes') or 0), url=r.get('upstream', ''),
                        docs_url='/docs/' + key, filename=key.split('/')[-1],
                        table=table_, publisher=pub, note=note))
    return out


# ---------------------------------------------------------------- payload

def payload(m, rows):
    G = {g['key']: g for g in m['groups']}
    first, last = m['first'], m['last']
    idx_groups = ['schools', 'town', 'benefits', 'retirement', 'debt']
    levy_series = {y: m['levy'][y] for y in range(first, last + 1) if y in m['levy']}
    # The index chart's levy line is the CERTIFIED limit, with the in-window overrides taken
    # back out from the year each took effect -- the same benchmark the pull uses.
    lx = {}
    for y, v in levy_series.items():
        lx[y] = v - sum(o['amount'] * (1 + LEVY_RATE) ** (y - o['fy'])
                        for o in m['overrides'] if o['fy'] <= y)
    index_series = []
    for y in range(first, last + 1):
        pt = dict(fy=y)
        for k in idx_groups:
            pt[k] = round(100 * G[k]['series'][str(y)] / G[k]['first'], 2)
        pt['levy'] = round(100 * lx[y] / lx[first], 2) if y in lx else None
        index_series.append(pt)

    def strip(g):
        return {k: v for k, v in g.items() if k != 'series'}

    return dict(
        generated_by='scripts/build_department_budgets.py',
        about='Every department’s starting budget from %s to %s, against the levy and '
              'against the schools — and what “deficit” can and cannot mean in this ledger.'
              % (C.fy(first), C.fy(last)),
        grain='DOLLARS of general fund appropriation. Growth is the ORIGINAL budget, budget '
              'to budget; spending is the REVISED budget against ACTUAL, %s only. Groups, the '
              'benchmark and the treatment of health insurance are ours.'
              % C.fyspan(first, m['exec_last']),
        first_fy=first, last_fy=last, exec_last_fy=m['exec_last'],
        stats=[
            dict(value=rate_pct(G['town']['rate']), tone='var(--series-cost)',
                 label='a year, growth of the town departments’ starting budgets, %s'
                       % C.fyspan(first, last)),
            dict(value=rate_pct(G['schools']['rate']),
                 label='a year, the schools’, with health insurance taken out of both sides'),
            dict(value=rate_pct(m['levy_ex']),
                 label='a year, the levy limit’s, with the %s override taken back out'
                       % C.fy(last)),
        ],
        levy=dict(limit={str(y): v for y, v in levy_series.items()},
                  rate_with_overrides=m['levy_with'], rate_without_overrides=m['levy_ex'],
                  overrides=m['overrides']),
        total=dict(first=m['total'][first], last=m['total'][last], rate=m['total_rate']),
        groups=[dict(strip(g), series=g['series']) for g in m['groups']],
        index_series=index_series,
        index_keys=[dict(key=k, name=GROUP_NAME[k]) for k in idx_groups]
        + [dict(key='levy', name='Levy limit, less overrides')],
        functions=[strip(x) for x in m['funcs']],
        departments=[strip(d) for d in m['depts']],
        like_for_like=m['lfl'],
        residual=m['residual'],
        over_revised=[dict(code=c, name=n_, fy=y) for c, n_, y in m['over_revised']],
        sources=sources(),
        not_established=[
            'Whether any department’s budget was adequate: a ledger records what was voted '
            'and spent, never what level service would have cost.',
            'What the money that reached revised budgets outside any recorded transfer was.',
            'The school share of the county retirement assessment, of Medicare, and of '
            'retirees’ health insurance before the ledger split it.',
            'How much of the schools’ appropriation growth is cost growth and how much is '
            'grants, circuit breaker or fees starting or stopping.',
            'Whether a town department’s growth is more service or a cost moved into it.',
        ],
        conclusions=emit(ID, rows),
    )


# ---------------------------------------------------------------- the SVGs, for /docs and the PDF

PALETTE = {'schools': '#2b6cb0', 'town': '#dc2626', 'benefits': '#ea8c00',
           'retirement': '#7c3aed', 'debt': '#2f8f4e', 'assessments': '#0d9488',
           'reserves': '#92400e', 'levy': '#6b7280'}


def svg_index(pay):
    W, H, L, R, T, B = 760, 380, 56, 190, 20, 36
    pts = pay['index_series']
    keys = [k['key'] for k in pay['index_keys']]
    vals = [p[k] for p in pts for k in keys if p.get(k) is not None]
    lo, hi = min(vals), max(vals)
    lo, hi = math.floor(lo / 50) * 50, math.ceil(hi / 50) * 50
    x = lambda i: L + (W - L - R) * i / (len(pts) - 1)
    y = lambda v: T + (H - T - B) * (1 - (v - lo) / (hi - lo))
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" font-family="system-ui,'
         'sans-serif" font-size="11"><rect width="100%%" height="100%%" fill="#ffffff"/>' % (W, H)]
    for v in range(int(lo), int(hi) + 1, 50):
        o.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#e5e7eb"/>'
                 '<text x="%d" y="%.1f" text-anchor="end" fill="#6b7280">%d</text>'
                 % (L, W - R, y(v), y(v), L - 6, y(v) + 4, v))
    for i, p in enumerate(pts):
        if i % 3 == 0 or i == len(pts) - 1:
            o.append('<text x="%.1f" y="%d" text-anchor="middle" fill="#6b7280">FY%d</text>'
                     % (x(i), H - 14, p['fy']))
    labels = []
    for k in keys:
        seq = [(i, p[k]) for i, p in enumerate(pts) if p.get(k) is not None]
        d = ' '.join('%s%.1f,%.1f' % ('M' if j == 0 else 'L', x(i), y(v))
                     for j, (i, v) in enumerate(seq))
        dash = ' stroke-dasharray="5 4"' if k == 'levy' else ''
        o.append('<path d="%s" fill="none" stroke="%s" stroke-width="2.2"%s/>'
                 % (d, PALETTE[k], dash))
        labels.append([y(seq[-1][1]), k, seq[-1][1]])
    labels.sort()
    for j in range(1, len(labels)):
        if labels[j][0] - labels[j - 1][0] < 14:
            labels[j][0] = labels[j - 1][0] + 14
    names = {k['key']: k['name'] for k in pay['index_keys']}
    for yy, k, v in labels:
        o.append('<text x="%d" y="%.1f" fill="%s">%s %d</text>'
                 % (W - R + 6, yy + 4, PALETTE[k], html.escape(names[k]), round(v)))
    o.append('</svg>\n')
    return ''.join(o)


def svg_pull(pay):
    gs = sorted(pay['groups'], key=lambda g: -g['pull'])
    W, row, L, T = 760, 30, 190, 16
    H = T + row * len(gs) + 30
    m_ = max(abs(g['pull']) for g in gs)
    mid = L + (W - L - 80) / 2
    sc = ((W - L - 80) / 2 - 50) / m_     # 50px each side for the value label
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" font-family="system-ui,'
         'sans-serif" font-size="11"><rect width="100%%" height="100%%" fill="#ffffff"/>' % (W, H)]
    o.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="#6b7280"/>'
             % (mid, mid, T - 4, H - 26))
    for i, g in enumerate(gs):
        yy = T + i * row
        wdt = abs(g['pull']) * sc
        x0 = mid if g['pull'] >= 0 else mid - wdt
        o.append('<text x="%d" y="%d" text-anchor="end" fill="#111827">%s</text>'
                 % (L - 8, yy + 15, html.escape(g['name'])))
        o.append('<rect x="%.1f" y="%d" width="%.1f" height="18" fill="%s"/>'
                 % (x0, yy + 3, wdt, PALETTE[g['key']]))
        tx = x0 + wdt + 4 if g['pull'] >= 0 else x0 - 4
        o.append('<text x="%.1f" y="%d" text-anchor="%s" fill="#374151">%s</text>'
                 % (tx, yy + 15, 'start' if g['pull'] >= 0 else 'end', pp(g['pull'])))
    o.append('<text x="%.1f" y="%d" text-anchor="middle" fill="#6b7280">points a year of '
             'pull on the levy limit</text>' % (mid, H - 8))
    o.append('</svg>\n')
    return ''.join(o)


# ---------------------------------------------------------------- main

def outputs():
    m = measure()
    rows = build_conclusions(m)
    pay = payload(m, rows)
    md = render_md(m, rows)
    return {
        OUT_JSON: json.dumps(pay, indent=1, ensure_ascii=False, sort_keys=True) + '\n',
        OUT_MD: md,
        os.path.join(CHART_DIR, '%s-index.svg' % ID): svg_index(pay),
        os.path.join(CHART_DIR, '%s-pull.svg' % ID): svg_pull(pay),
    }


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
        print('%s: %d outputs current' % (ID, len(outs)))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
