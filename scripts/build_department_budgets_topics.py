#!/usr/bin/env python3
"""Town departments, split into topic pages: what Town Meeting votes each department, how
fast each grows against the levy cap, and who stands behind the money.

    python3 scripts/build_department_budgets_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_department_budgets_topics.py --check   # fail if any output would change

WHAT THIS ABSORBS. /analysis/town-budgets, /analysis/town-personnel and the twelve
/analysis/town-budget-* department documents. Each department document answered the same
templated questions about one group; here a department gets one page, the two smallest-but-
one are pooled with the smallest, and the cross-department questions (share, growth against
the cap, the voted total, staff counts) get one page each.

IT COMPUTES NOTHING NEW THAT IT CAN READ INSTEAD. Every figure comes from a payload already
built and --checked by another generator, and the script refuses to write when the payloads
stop agreeing with each other or with a sentence written here:

  fy28/public/data/town-budgets.json        build_town_budgets.py: the twelve group totals of
                                            the FY2023-FY2025 omnibus budgets, each footed to
                                            the printed grand total; the voted total
                                            FY2012-FY2026; `excess`, rule 4's measure.
  fy28/public/data/town-budget-<slug>.json  the same generator: each group's printed lines.
  fy28/public/data/town-personnel.json      build_town_personnel.py: what each department
                                            prints about its own staff, in its own form.
  scripts/build_town_personnel.py           read-only: BUDGET_GROUP, which budget group each
                                            counting department sits in, and NO_COUNT, why
                                            the others print none. One place, not two.

WHAT IT DOES NOT USE, AND WHY.

  * /analysis/department-budgets (the general ledger, FY2010-FY2025) is UNLISTED -- a draft
    TJ has not put on the site. Building pages from its figures would publish it by another
    door, so nothing here reads it.
  * The Town's FY26 budget workbook (sources/data/town-budget-fy26-fy27.csv) holds FY2026
    department figures and requests. Nothing has turned it into a checked payload yet, so
    FY2026 below the total is registered on the pages as unread, not as unpublished.
  * School staff. The school rosters are the School staffing shelf's
    (printed-school-rosters), and the two counts on the site disagree; they are not
    restated here.

RULE 11. Every figure is a NET APPROPRIATION: what Town Meeting voted the town to raise for
that group, after whatever grants, fees and receipts pay part of it. Never a cost.

RULE 4. Departments are ranked by `excess` -- the group's FY2025 dollars times how far its
FY2023-FY2025 growth ran past the 2.5% the levy may rise by -- never by size and never by
rate. The measure is ours and is marked `estimate`; build_town_personnel.py's sibling
(town_budget_data.py) explains why the older `pull` index is not used: it does not add up.

RULE 7. The omnibus states amounts and no reasons. Every reason offered here is a note of
kind `hypothesis`, and says so.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
from brief import step  # noqa: E402
import build_town_personnel as BTP  # noqa: E402  (read-only: BUDGET_GROUP, NO_COUNT)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT_DIR = os.path.join(PUB, 'topics')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
AR = os.path.join(ROOT, 'sources', 'town-annual-reports', 'text')
CID = 'department-budgets'

MINE = [t for t, (_, home, gen) in REG.TOPICS.items()
        if home == CID and gen == 'build_department_budgets_topics.py']


def fail(msg):
    raise SystemExit('build_department_budgets_topics: ' + msg)


def load(name):
    return json.load(open(os.path.join(PUB, name), encoding='utf-8'))


def norm(s):
    return ' '.join((s or '').split())


def sources():
    import csv
    man = {r['key'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    town = 'Town of Lunenburg'
    spec = {
        'ar22': 'town-annual-reports/docs/4129-fy-2022-annual-town-report.pdf',
        'ar23': 'town-annual-reports/docs/4131-fy-2023-annual-town-report.pdf',
        'ar24': 'town-annual-reports/docs/4132-fy-2024-annual-town-report.pdf',
        'ar25': 'town-annual-reports/docs/4130-fy-2025-annual-town-report.pdf',
    }
    out = {}
    for k, key in spec.items():
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        out[k] = dict(label='%s — annual town report — %s' % (town, key.split('/')[-1]),
                      href='/docs/' + key)
    for k, f, what in (('d-approp', 'report-appropriations.csv',
                        'the omnibus budgets, read line by line'),
                       ('d-staff', 'department-staffing.csv',
                        'what each department says it employs, as printed')):
        if not os.path.exists(os.path.join(ROOT, 'fy28', 'public', 'docs', 'data', f)):
            fail('/docs/data/%s is not published' % f)
        out[k] = dict(label='Lunenburg Budget Project — %s (%s)' % (f, what),
                      href='/docs/data/' + f)
    out['tb'] = dict(label='Lunenburg Budget Project — town-budgets.json (the twelve groups, '
                           'footed to each printed total)', href='/data/town-budgets.json')
    out['tp'] = dict(label='Lunenburg Budget Project — town-personnel.json (staff counts as '
                           'each department prints them)', href='/data/town-personnel.json')
    return out


def dept_src(slug):
    p = 'town-budget-%s.json' % slug
    if not os.path.exists(os.path.join(PUB, p)):
        fail('%s is missing' % p)
    return dict(label='Lunenburg Budget Project — %s (its printed lines)' % p, href='/data/' + p)


def cagr(a, b, n):
    return ((b / a) ** (1.0 / n) - 1) * 100


# --------------------------------------------------------------------- the pages

def build():
    TB = load('town-budgets.json')
    TPL = load('town-personnel.json')
    src = sources()
    ys = TB['detail_years']
    if ys != [2023, 2024, 2025]:
        fail('the omnibus detail years are no longer FY2023-FY2025: %s' % ys)
    Y0, Y1 = 'FY%d' % ys[0], 'FY%d' % ys[-1]
    CAP = TB['levy_cap']
    if CAP != 2.5:
        fail('the levy cap reference is no longer 2.5%')
    D = {d['slug']: d for d in TB['departments']}
    if len(D) != 12:
        fail('there are no longer twelve groups')
    DP = {s: load('town-budget-%s.json' % s) for s in D}
    for s, p in DP.items():
        if abs(p['department']['last'] - D[s]['last']) > 0.005:
            fail('%s: the department payload and town-budgets.json disagree' % s)
    total = TB['voted_total']
    if abs(sum(d['last'] for d in D.values()) - total) > 0.01:
        fail('the twelve groups no longer sum to the voted total')
    if abs(TB['reconcile']['2025']['difference']) > 0.005:
        fail('FY2025 no longer foots to its printed grand total')

    U = lambda v: figure(v, C.usd(v))
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    f, con = LD.fact, TP.conclusion
    ROW = lambda d: d['name']
    by_excess = sorted(D.values(), key=lambda d: -d['excess'])
    out = {}

    # shared tiles for one department
    def voted(id, s):
        return f(id, U(D[s]['last']), 'voted, %s' % Y1, 'published', allow=(Y1,))

    def rate(id, s):
        return f(id, P(D[s]['rate']), 'a year, %s to %s' % (Y0, Y1), 'published',
                 allow=(Y0, Y1))

    def share(id, s):
        return f(id, P(D[s]['share']), 'of the voted budget, %s' % Y1, 'published', allow=(Y1,))

    def excess(id, s):
        return f(id, U(D[s]['excess']), 'a year above what 2.5% growth carries (ours)',
                 'estimate', allow=('2.5%',))

    net_gap = step('A voted line is net: what the town raises after grants, fees and other '
                   'receipts pay their part. It is not what the service costs.', 'gap',
                   closes='the town’s grant and revolving fund reports, by department')
    why_gap = lambda what: step('The omnibus states amounts and no reasons, so why %s moved '
                                'is not shown here.' % what, 'gap',
                                closes='the department’s budget request and narrative to the '
                                       'Finance Committee for that year')

    def lines_table(s, caption):
        mv = DP[s]['movers']
        rows = [dict(label=m['label'].lstrip('| '), cells=[C.usd(m['first']), C.usd(m['last']),
                                              ('+' if m['change'] >= 0 else '') + C.usd(m['change'])])
                for m in mv if m['first'] is not None and m['last'] is not None]
        return dict(caption=caption, views=[dict(
            key='lines', label='Lines, as printed', total_col=1, kinds=['ledger'] * 3,
            columns=[Y0, Y1, 'Change'], rows=rows,
            note='Lines that appear in both omnibus budgets under the same printed label. '
                 'A line whose label changed is not joined.')])

    # ------------------------------------------------ the whole budget: shares
    top4 = sorted(D.values(), key=lambda d: -d['last'])[:4]
    top4_share = sum(d['share'] for d in top4)
    if [d['slug'] for d in top4] != ['schools', 'protection', 'unclassified', 'maturing-debt']:
        fail('the four largest groups are no longer schools, protection, benefits and debt')
    small = [d for d in D.values() if d['share'] < 2]
    smallest = min(D.values(), key=lambda d: d['last'])
    if smallest['slug'] != 'central-purchasing':
        fail('Central Purchasing is no longer the smallest group')
    sch = D['schools']
    out['town-budget-shares'] = TP.page(
        'town-budget-shares',
        'Schools are %s of the %s Town Meeting voted for %s; the next three groups together '
        'are %s.' % (C.pct(sch['share']), C.usd(total), Y1, C.pct(top4_share - sch['share'])),
        [f('total', U(total), 'voted for twelve groups, %s' % Y1, 'published', allow=(Y1,)),
         f('schools', P(sch['share']), 'of it to the schools', 'published'),
         f('protection', P(D['protection']['share']), 'to police, fire and inspectors',
           'published'),
         f('benefits', P(D['unclassified']['share']), 'to employee benefits and reserves',
           'published'),
         f('debt', P(D['maturing-debt']['share']), 'to debt service', 'published'),
         f('top4', P(top4_share), 'in those four groups together', 'published'),
         f('small', N(len(small), 'groups'), 'each under 2% of the budget', 'published',
           allow=('2%',)),
         f('smallest', U(smallest['last']), 'Central Purchasing, the smallest group',
           'published'),
         f('asked', None, 'each department’s budget request', 'gap',
           closes='each department’s budget request to the Finance Committee, %s' % Y1)],
        [con('Four groups — schools, police and fire, benefits and debt — are %s of the voted '
             'budget.' % C.pct(top4_share), ['top4', 'schools', 'protection', 'benefits', 'debt'],
             {'a': P(top4_share)},
             notes=[net_gap]),
         con('%s groups are each under %s; together they are %s.'
             % (C.num(len(small)), '2%', C.pct(sum(d['share'] for d in small))),
             ['small', 'smallest'],
             {'n': N(len(small)), 'b': P(sum(d['share'] for d in small))}, allow=('2%',)),
         con('The omnibus is what was voted, already balanced; a cut lives in the difference '
             'from the request.', ['asked', 'total'])],
        chart=dict(id='town-budgets-share', source='/data/town-budgets.json'),
        table=dict(caption='The voted budget, by group', views=[dict(
            key='share', label=Y1, total_col=0, kinds=['ledger', 'ledger'],
            columns=['Voted', 'Share'],
            rows=[dict(label=ROW(d), cells=[C.usd(d['last']), C.pct(d['share'])])
                  for d in sorted(D.values(), key=lambda d: -d['last'])],
            note='The twelve group totals the omnibus prints, which foot to its printed grand '
                 'total. Share is ours, of that total.')]),
        sources=[src['ar24'], src['d-approp'], src['tb']],
        finding_figures={'a': P(sch['share']), 'b': U(total),
                         'c': P(top4_share - sch['share'])},
        finding_allow=(Y1,))

    # ------------------------------------------------ growth above the cap (rule 4)
    above = [d for d in D.values() if d['rate'] > CAP]
    T0 = sum(d['first'] for d in D.values())
    tot_rate = cagr(T0, total, ys[-1] - ys[0])
    sum_ex = sum(d['excess'] for d in D.values())
    if [d['slug'] for d in by_excess[:2]] != ['unclassified', 'schools']:
        fail('benefits and the schools are no longer the two largest by excess')
    fastest = max(D.values(), key=lambda d: d['rate'])
    if fastest['slug'] != 'solid-waste':
        fail('solid waste is no longer the fastest-growing group')
    rank_fast = [d['slug'] for d in by_excess].index('solid-waste') + 1
    nonsch = [d for d in D.values() if d['slug'] not in ('schools', 'maturing-debt')]
    r_rest = cagr(sum(d['first'] for d in nonsch), sum(d['last'] for d in nonsch),
                  ys[-1] - ys[0])
    ORD = {1: 'first', 2: 'second', 3: 'third', 4: 'fourth', 5: 'fifth', 6: 'sixth'}
    out['town-budget-growth'] = TP.page(
        'town-budget-growth',
        'Ranked by dollars above the %s levy cap, employee benefits push the budget hardest, '
        'then the schools.' % C.pct(CAP),
        [f('cap', P(CAP), 'a year the levy may rise, before new growth', 'statute'),
         f('all', P(tot_rate), 'a year, the whole voted budget, %s to %s' % (Y0, Y1),
           'published', allow=(Y0, Y1)),
         f('above', figure(len(above), '%s of %s' % (len(above), len(D)), 'groups'),
           'groups growing faster than the cap', 'published'),
         f('ben', U(D['unclassified']['excess']), 'benefits, a year above the cap (ours)',
           'estimate'),
         f('sch', U(sch['excess']), 'schools, a year above the cap (ours)', 'estimate'),
         f('gg', U(D['general-government']['excess']),
           'general government, a year above the cap (ours)', 'estimate'),
         f('sw-rate', P(fastest['rate']), 'a year, trash and recycling, the fastest',
           'published'),
         f('sw', U(fastest['excess']), 'trash and recycling, above the cap (ours)', 'estimate'),
         f('debt', U(D['maturing-debt']['excess']), 'debt service, against the cap (ours)',
           'estimate'),
         f('sum', U(sum_ex), 'all twelve, a year above the cap (ours)', 'estimate'),
         f('rest', P(r_rest), 'a year, all but schools and debt', 'published')],
        [con('Benefits are %s of the budget and push %s a year past the cap; the schools, %s, '
             'push %s.' % (C.pct(D['unclassified']['share']), C.usd(D['unclassified']['excess']),
                           C.pct(sch['share']), C.usd(sch['excess'])),
             ['ben', 'sch'],
             {'a': P(D['unclassified']['share']), 'b': U(D['unclassified']['excess']),
              'c': P(sch['share']), 'd': U(sch['excess'])}),
         con('Trash and recycling grew fastest, %s a year, and ranks %s by dollars above the cap.'
             % (C.pct(fastest['rate']), ORD[rank_fast]), ['sw-rate', 'sw'],
             {'a': P(fastest['rate'])}),
         con('Outside the schools and debt, the groups grew %s a year; the schools grew %s.'
             % (C.pct(r_rest), C.pct(sch['rate'])), ['rest', 'sch'],
             {'a': P(r_rest), 'b': P(sch['rate'])}),
         con('Debt service falling offsets much of the rest: all twelve net to %s a year above '
             'the cap.' % C.usd(sum_ex), ['debt', 'sum'], {'a': U(sum_ex)},
             notes=[step('The cap limits the levy, not the budget. State aid, local receipts and '
                         'new growth also pay for these lines.', 'gap',
                         closes='the Division of Local Services tax rate recapitulation for '
                                'each year')])],
        chart=dict(id='town-budgets-pull', source='/data/town-budgets.json'),
        table=dict(caption='Each group against the levy cap', views=[dict(
            key='growth', label='%s to %s' % (Y0, Y1), total_col=3,
            kinds=['ledger', 'ledger', 'ledger', 'ledger'],
            columns=[Y0, Y1, 'A year', 'Above the cap, a year (ours)'],
            rows=[dict(label=ROW(d), cells=[C.usd(d['first']), C.usd(d['last']), C.pct(d['rate']),
                                            C.usd(d['excess'])]) for d in by_excess],
            note='Ranked by the last column: the group’s own dollars times how far its compound '
                 'growth ran past the cap. Neither its size nor its rate alone ranks it.')]),
        sources=[src['ar22'], src['ar23'], src['ar24'], src['tb']],
        finding_figures={'a': P(CAP)})

    # ------------------------------------------------ the voted total
    # ONLY THE CHECKED YEARS ARE COMPARED. The first draft called FY2026 "the largest one-year
    # rise since FY2012" and gave a 4.0% FY2012-FY2025 rate, both resting on totals whose
    # check FAILED -- CLAUDE.md: `status` splits the rows, "and nothing may be aggregated
    # without splitting on it". FY2022 and FY2025 tie to their own parts; FY2026 is printed
    # as prose with no table under it. The table keeps every year, with its status beside it.
    tots = {t['fy']: t['voted'] for t in TB['totals']}
    status = {t['fy']: t['status'] for t in TB['totals']}
    if sorted(tots) != list(range(2012, 2027)):
        fail('the voted totals no longer run FY2012-FY2026')
    if not (status[2022] == status[2025] == 'checked'):
        fail('FY2022 and FY2025 are no longer the checked totals this page compares')
    steps = {y: (tots[y] / tots[y - 1] - 1) * 100 for y in range(2013, 2027)}
    pr = TB['prose']
    other = sum(a for n, a in pr['parts'] if n != 'raised and appropriated')
    if abs(sum(a for _, a in pr['parts']) - pr['total']) > 0.01:
        fail('Article 10’s funding sources no longer sum to its total')
    r2225 = cagr(tots[2022], tots[2025], 3)
    out['town-voted-total'] = TP.page(
        'town-voted-total',
        'The voted total was %s for FY2025 and %s for FY2026, a %s rise.'
        % (C.usd(tots[2025]), C.usd(tots[2026]), C.pct(steps[2026])),
        [f('t22', U(tots[2022]), 'voted total, FY2022, ties to its parts', 'published',
           allow=('FY2022',)),
         f('t25', U(tots[2025]), 'voted total, FY2025, ties to its parts', 'published',
           allow=('FY2025',)),
         f('t26', U(tots[2026]), 'voted total, FY2026, Article 10, printed as prose',
           'published', allow=('FY2026', '10')),
         f('step26', P(steps[2026]), 'rise into FY2026', 'published', allow=('FY2026',)),
         f('rate', P(r2225), 'a year, FY2022 to FY2025', 'published', allow=('FY2022', 'FY2025')),
         f('other', U(other), 'of FY2026 not ‘raised and appropriated’', 'published',
           allow=('FY2026',)),
         f('unchecked', None, 'the other years’ totals, tied to their parts', 'gap',
           closes='a reading of each year’s omnibus table that foots to the total it prints'),
         f('detail', None, 'FY2026 by department', 'gap', allow=('FY2026',),
           closes='the Town’s FY26 omnibus budget workbook, which this archive holds and no '
                  'page has yet read')],
        [con('The FY2026 voted total is %s above FY2025’s.' % C.pct(steps[2026]),
             ['t25', 't26', 'step26', 'other'], {'a': P(steps[2026])}, allow=('FY2026', 'FY2025'),
             notes=[step('Whether the FY2025 and FY2026 totals cover the same funds is not '
                         'checked; the FY2026 vote names other funds as sources.', 'gap',
                         allow=('FY2025', 'FY2026', '10', '2025'),
                         closes='the funding sources of the FY2025 omnibus vote, set beside '
                                'Article 10 of 2025')]),
         con('Between the two totals that tie to their parts, FY2022 and FY2025, it grew %s a '
             'year.' % C.pct(r2225), ['t22', 't25', 'rate', 'unchecked'], {'a': P(r2225)},
             allow=('FY2022', 'FY2025')),
         con('The annual report prints FY2026 as prose: no department table sits beneath it.',
             ['t26', 'detail'], allow=('FY2026',))],
        chart=dict(id='town-budgets-total', source='/data/town-budgets.json'),
        table=dict(caption='The voted total, by year', views=[dict(
            key='total', label='Voted', total_col=0, kinds=['ledger', 'ledger', 'ledger'],
            columns=['Voted', 'Change', 'Ties to its parts'],
            rows=[dict(label='FY%d' % y, cells=[
                C.usd(tots[y]), C.pct(steps[y]) if y in steps else None,
                'yes' if status[y] == 'checked' else
                'printed as prose' if y == 2026 else 'not checked'])
                  for y in sorted(tots, reverse=True)],
            note='The grand total each annual report prints at the foot of its omnibus, for '
                 'the year ahead. Only a year that ties to its parts is compared on this page. '
                 'The last year is Article 10 of the May 2025 Annual Town Meeting.')]),
        sources=[src['ar25'], src['ar24'], src['d-approp'], src['tb']],
        finding_figures={'a': U(tots[2025]), 'b': U(tots[2026]), 'c': P(steps[2026])},
        finding_allow=('FY2026', 'FY2025'))

    # ------------------------------------------------ schools in the omnibus
    mv = {m['label']: m for m in DP['schools']['movers']}
    sd, mt = mv['School Department'], mv['Monty Tech Assessment']
    if abs(sd['last'] + mt['last'] - sch['last']) > 0.5:
        fail('the school group is no longer the School Department plus Monty Tech')
    r_sd, r_mt = cagr(sd['first'], sd['last'], 2), cagr(mt['first'], mt['last'], 2)
    n_faster = len([d for d in D.values() if d['rate'] > sch['rate']])
    out['town-schools-line'] = TP.page(
        'town-schools-line',
        'The schools are %s of the voted budget and grew %s a year, %s to %s.'
        % (C.pct(sch['share']), C.pct(sch['rate']), Y0, Y1),
        [voted('voted', 'schools'), share('share', 'schools'), rate('rate', 'schools'),
         excess('excess', 'schools'),
         f('sd', U(sd['last']), 'School Department line, %s' % Y1, 'published', allow=(Y1,)),
         f('sd-rate', P(r_sd), 'a year, the School Department line', 'published'),
         f('mt', U(mt['last']), 'Monty Tech assessment, %s' % Y1, 'published', allow=(Y1,)),
         f('mt-rate', P(r_mt), 'a year, the Monty Tech assessment', 'published'),
         f('all-in', None, 'what the schools cost with grants and receipts', 'gap',
           closes='DESE’s End of Year Financial Report, which separates spending by fund')],
        [con('The School Department line grew %s a year; the Monty Tech assessment beside it, '
             '%s.' % (C.pct(r_sd), C.pct(r_mt)), ['sd-rate', 'mt-rate', 'sd', 'mt'],
             {'a': P(r_sd), 'b': P(r_mt)}),
         con('The largest group grew slower than %s of the other %s: %s a year, %s past the cap.'
             % (C.num(n_faster), C.num(len(D) - 1), C.pct(sch['rate']), C.usd(sch['excess'])),
             ['rate', 'excess', 'share'],
             {'n': N(n_faster), 'm': N(len(D) - 1), 'a': P(sch['rate']),
              'b': U(sch['excess'])},
             notes=[net_gap,
                    step('Part of the school appropriation is Chapter 70 aid, set by the state '
                         'rather than the town; the State aid shelf has its share.', 'gap',
                         allow=('70',),
                         closes='the Chapter 70 summary for the year, on the State aid shelf')])],
        table=lines_table('schools', 'The school group’s lines'),
        sources=[src['ar22'], src['ar24'], src['tb'], dept_src('schools')],
        finding_figures={'a': P(sch['share']), 'b': P(sch['rate'])}, finding_allow=(Y0, Y1))

    # ------------------------------------------------ police, fire and inspectors
    pr_ = D['protection']
    fire = sorted(TPL['fire'], key=lambda r: r['fy'])
    f0, f1 = fire[0], fire[-1]
    if not (f1['career'] > f0['career'] and f1['on_call_low'] < f0['on_call_low']):
        fail('career firefighters no longer rose while the on-call roll fell')
    emp = {e['department']: e for e in TPL['employers']}
    pol = emp['Police Department']
    rng = lambda r: figure(r['on_call_low'], '%d–%d' % (r['on_call_low'], r['on_call_high']),
                           'on-call firefighters')
    out['town-public-safety'] = TP.page(
        'town-public-safety',
        'Police, fire and the inspectors were voted %s for %s, %s of the budget.'
        % (C.usd(pr_['last']), Y1, C.pct(pr_['share'])),
        [voted('voted', 'protection'), share('share', 'protection'), rate('rate', 'protection'),
         excess('excess', 'protection'),
         f('c0', N(f0['career'], 'firefighters'), 'career firefighters, FY%s' % f0['fy'],
           'published', allow=('FY%s' % f0['fy'],)),
         f('c1', N(f1['career'], 'firefighters'), 'career firefighters, FY%s' % f1['fy'],
           'published', allow=('FY%s' % f1['fy'],)),
         f('o0', rng(f0), 'on call, as the department states it, FY%s' % f0['fy'], 'published',
           allow=('FY%s' % f0['fy'],)),
         f('o1', rng(f1), 'on call, FY%s' % f1['fy'], 'published', allow=('FY%s' % f1['fy'],)),
         f('police', N(pol['people'], 'people'), 'named on the Police roster, FY%s'
           % pol['last_fy'], 'published', allow=('FY%s' % pol['last_fy'],)),
         f('split', None, 'the group split into police, fire and the rest', 'gap',
           closes='the Police, Fire and Radio Watch subtotals the omnibus prints, not yet read '
                  'into a dataset')],
        [con('The group grew %s a year, %s past the cap in dollars.'
             % (C.pct(pr_['rate']), C.usd(pr_['excess'])), ['rate', 'excess', 'voted'],
             {'a': P(pr_['rate']), 'b': U(pr_['excess'])},
             notes=[why_gap('the group')]),
         con('Career firefighters went from %s to %s while the on-call roll fell from %s to %s.'
             % (f0['career'], f1['career'], rng(f0)['text'], rng(f1)['text']),
             ['c0', 'c1', 'o0', 'o1'],
             {'a': N(f0['career']), 'b': N(f1['career']), 'c': rng(f0), 'd': rng(f1)},
             notes=[step('A count is people present, not funded posts, and a career post and '
                         'an on-call post are not the same job.', 'gap',
                         closes='the Fire Department’s establishment of posts, with FTE')]),
         con('Which part of the group moved is not read yet: the omnibus prints its subtotals.',
             ['split'])],
        chart=dict(id='town-personnel-fire', source='/data/town-personnel.json'),
        table=dict(caption='The Fire Department, as it states its strength', views=[dict(
            key='fire', label='Fire', total_col=0, kinds=['ledger', 'ledger'],
            columns=['Career', 'On call'],
            rows=[dict(label='FY%s' % r['fy'], cells=[str(r['career']), '%d–%d'
                                                      % (r['on_call_low'], r['on_call_high'])])
                  for r in reversed(fire)],
            note='Printed in the prose of the department’s own annual report; the on-call roll '
                 'is stated as a range.')]),
        sources=[src['ar24'], src['ar25'], src['tb'], src['d-staff'], src['tp']],
        finding_figures={'a': U(pr_['last']), 'b': P(pr_['share'])}, finding_allow=(Y1,))

    # ------------------------------------------------ employee benefits
    bn = D['unclassified']
    mv = {m['label']: m for m in DP['unclassified']['movers']}
    gh, rf, sr = mv['Group Health Insurance'], mv['Reserve Fund'], mv['Salary Reserve Fund']
    if DP['unclassified']['movers'][0]['label'] != 'Group Health Insurance':
        fail('group health is no longer the line that moved most in benefits')
    gh_share = 100 * gh['last'] / bn['last']
    out['town-employee-benefits'] = TP.page(
        'town-employee-benefits',
        'Employee benefits grew %s a year, the most dollars past the cap of any group; group '
        'health is %s of it.' % (C.pct(bn['rate']), C.pct(gh_share, 0)),
        [voted('voted', 'unclassified'), share('share', 'unclassified'),
         rate('rate', 'unclassified'), excess('excess', 'unclassified'),
         f('gh0', U(gh['first']), 'Group Health Insurance, %s' % Y0, 'published', allow=(Y0,)),
         f('gh1', U(gh['last']), 'Group Health Insurance, %s' % Y1, 'published', allow=(Y1,)),
         f('gh-share', P(gh_share, 0), 'of the group, group health, %s' % Y1, 'published',
           allow=(Y1,)),
         f('rf', U(rf['last']), 'Reserve Fund, %s' % Y1, 'published', allow=(Y1,)),
         f('sr', U(sr['last']), 'Salary Reserve Fund, %s' % Y1, 'published', allow=(Y1,)),
         f('whose', None, 'whose insurance the group health line pays', 'gap',
           closes='the insurance accounts by object: town staff, town retirees and school '
                  'retirees')],
        [con('Group Health Insurance rose %s, %s of the group’s whole rise.'
             % (C.usd(gh['change']), C.pct(100 * gh['change'] / bn['change'], 0)),
             ['gh0', 'gh1', 'voted'],
             {'a': U(gh['change']), 'b': P(100 * gh['change'] / bn['change'], 0)},
             notes=[why_gap('group health')]),
         con('The two reserve funds went from %s to %s together, %s to %s.'
             % (C.usd(rf['first'] + sr['first']), C.usd(rf['last'] + sr['last']), Y0, Y1),
             ['rf', 'sr'], {'a': U(rf['first'] + sr['first']), 'b': U(rf['last'] + sr['last'])},
             allow=(Y0, Y1),
             notes=[step('A reserve is voted here and, if used, transferred to other lines '
                         'during the year.', 'gap',
                         closes='the Finance Committee’s Reserve Fund transfer votes for the '
                                'year')]),
         con('Which employees and retirees the group health line covers is not printed in the '
             'omnibus.', ['whose'])],
        table=lines_table('unclassified', 'The benefits group’s lines'),
        sources=[src['ar22'], src['ar24'], src['tb'], dept_src('unclassified')],
        finding_figures={'a': P(bn['rate']), 'b': P(gh_share, 0)})

    # ------------------------------------------------ debt service
    db = D['maturing-debt']
    mv = {m['label']: m for m in DP['maturing-debt']['movers']}
    pp, ii = mv['Principal-Loans'], mv['Interest-Loans']
    fall = db['first'] - db['last']
    if [d['slug'] for d in D.values() if d['rate'] < 0] != ['maturing-debt']:
        fail('debt service is no longer the only group that fell')
    if not (-pp['change'] > fall * 0.8):
        fail('principal is no longer most of the fall in debt service')
    out['town-debt-service'] = TP.page(
        'town-debt-service',
        'Debt service fell from %s to %s, %s to %s, the only one of the twelve groups to fall.'
        % (C.usd(db['first']), C.usd(db['last']), Y0, Y1),
        [f('d0', U(db['first']), 'voted, %s' % Y0, 'published', allow=(Y0,)),
         voted('d1', 'maturing-debt'), share('share', 'maturing-debt'),
         f('fall', U(fall), 'less a year by %s' % Y1, 'published', allow=(Y1,)),
         f('p1', U(pp['last']), 'principal, %s' % Y1, 'published', allow=(Y1,)),
         f('pfall', U(-pp['change']), 'less principal than in %s' % Y0, 'published', allow=(Y0,)),
         f('i1', U(ii['last']), 'interest, %s' % Y1, 'published', allow=(Y1,)),
         excess('excess', 'maturing-debt'),
         f('which', None, 'which bonds finished', 'gap',
           closes='the debt repayment schedule in the annual town report, not yet read'),
         f('excl', None, 'how much is paid outside the levy limit', 'gap',
           closes='the debt exclusions voted, as the tax rate recapitulation lists them')],
        [con('Principal fell %s of the %s; interest fell less.'
             % (C.usd(-pp['change']), C.usd(fall)), ['pfall', 'fall', 'p1', 'i1'],
             {'a': U(-pp['change']), 'b': U(fall)}),
         con('The total budget still rose while debt fell; the omnibus does not say where the '
             'room went.', ['fall', 'excess'],
             notes=[step('Bonds finishing with none issued to replace them would produce this '
                         'shape; the schedule that would show it is not read.', 'hypothesis')]),
         con('How much of it is paid outside the levy limit, by exclusion vote, is not shown '
             'here.', ['excl', 'which'])],
        table=lines_table('maturing-debt', 'The debt group’s lines'),
        sources=[src['ar22'], src['ar24'], src['tb'], dept_src('maturing-debt')],
        finding_figures={'a': U(db['first']), 'b': U(db['last'])}, finding_allow=(Y0, Y1))

    # ------------------------------------------------ general government
    gg = D['general-government']
    gl = [l for l in DP['general-government']['lines']['2025'] if l['amount']]
    big_line = max(gl, key=lambda l: l['amount'])
    mvs = DP['general-government']['movers']
    a1 = mvs[0]
    if a1['label'] != "Assessor's Administration" or big_line['label'] != 'Information Technology Dept.':
        fail('the assessor line is no longer the largest mover, or IT the largest line')
    ass = emp['Board of Assessors']
    out['town-general-government'] = TP.page(
        'town-general-government',
        'The town’s own administration grew %s a year, %s past the cap in dollars, third of '
        'the twelve.' % (C.pct(gg['rate']), C.usd(gg['excess'])),
        [voted('voted', 'general-government'), share('share', 'general-government'),
         rate('rate', 'general-government'), excess('excess', 'general-government'),
         f('it', U(big_line['amount']), 'Information Technology, its largest line, %s' % Y1,
           'published', allow=(Y1,)),
         f('a0', U(a1['first']), "Assessor's Administration, %s" % Y0, 'published', allow=(Y0,)),
         f('a1', U(a1['last']), "Assessor's Administration, %s" % Y1, 'published', allow=(Y1,)),
         f('posts', N(ass['people'], 'posts'), 'Assessing office posts, FY%s' % ass['last_fy'],
           'published', allow=('FY%s' % ass['last_fy'],)),
         f('posts0', N(ass['first'], 'posts'), 'Assessing office posts, FY%s' % ass['first_fy'],
           'published', allow=('FY%s' % ass['first_fy'],))],
        [con("Assessor's Administration rose %s, the most of any line in the group."
             % C.usd(a1['change']), ['a0', 'a1'], {'a': U(a1['change'])},
             notes=[step('The Assessing office printed %s posts in FY%s and %s in FY%s; whether '
                         'that is what the rise paid for is not shown.'
                         % (ass['first'], ass['first_fy'], ass['people'], ass['last_fy']),
                         'hypothesis', {'a': N(ass['first']), 'b': N(ass['people'])},
                         allow=('FY%s' % ass['first_fy'], 'FY%s' % ass['last_fy']))]),
         con('Its largest single line in %s is Information Technology, at %s.'
             % (Y1, C.usd(big_line['amount'])), ['it'], {'a': U(big_line['amount'])},
             allow=(Y1,)),
         con('The group grew %s a year: %s of the budget, %s past the cap in dollars.'
             % (C.pct(gg['rate']), C.pct(gg['share']), C.usd(gg['excess'])),
             ['rate', 'share', 'excess'],
             {'a': P(gg['rate']), 'b': P(gg['share']), 'c': U(gg['excess'])},
             notes=[why_gap('each office')])],
        table=lines_table('general-government', 'General government’s lines'),
        sources=[src['ar22'], src['ar24'], src['tb'], dept_src('general-government'),
                 src['d-staff']],
        finding_figures={'a': P(gg['rate']), 'b': U(gg['excess'])})
    if [d['slug'] for d in by_excess].index('general-government') != 2:
        fail('general government is no longer third by excess')

    # ------------------------------------------------ public works
    pw = D['public-works']
    mv = {m['label']: m for m in DP['public-works']['movers']}
    ghm = mv['General Highway Maintenance']
    snow = next(l for l in DP['public-works']['lines']['2025'] if l['label'] == 'Snow Removal Expense')
    if not ghm['change'] > pw['change']:
        fail('general highway maintenance no longer rose more than the whole group')
    out['town-public-works'] = TP.page(
        'town-public-works',
        'Public works grew %s a year, close to the cap; one line rose more than the whole group.'
        % C.pct(pw['rate']),
        [voted('voted', 'public-works'), share('share', 'public-works'),
         rate('rate', 'public-works'), excess('excess', 'public-works'),
         f('change', U(pw['change']), 'the group’s rise, %s to %s' % (Y0, Y1), 'published',
           allow=(Y0, Y1)),
         f('ghm0', U(ghm['first']), 'General Highway Maintenance, %s' % Y0, 'published',
           allow=(Y0,)),
         f('ghm1', U(ghm['last']), 'General Highway Maintenance, %s' % Y1, 'published',
           allow=(Y1,)),
         f('snow', U(snow['amount']), 'Snow Removal Expense voted, %s' % Y1, 'published',
           allow=(Y1,))],
        [con('General Highway Maintenance rose %s while the group rose %s, so other lines fell.'
             % (C.usd(ghm['change']), C.usd(pw['change'])), ['ghm0', 'ghm1', 'change'],
             {'a': U(ghm['change']), 'b': U(pw['change'])},
             notes=[why_gap('the highway line')]),
         con('Snow removal is voted at %s; state law lets a town spend past its snow budget.'
             % C.usd(snow['amount']), ['snow'], {'a': U(snow['amount'])})],
        table=lines_table('public-works', 'Public works’ lines'),
        sources=[src['ar22'], src['ar24'], src['tb'], dept_src('public-works')],
        finding_figures={'a': P(pw['rate'])})

    # ------------------------------------------------ facilities and grounds
    fg = D['facilities-grounds']
    fl = {l['label']: l['amount'] for l in DP['facilities-grounds']['lines']['2025'] if l['amount']}
    text22 = norm(open(os.path.join(AR, '4129-fy-2022-annual-town-report.txt'),
                       encoding='utf-8').read())
    a7 = ('ARTICLE 7. To see if the Town will vote to approve a reorganization of the Public '
          'Works Department')
    if a7 not in text22 or 'VOTED (Yes -136, No -28) to approve the Administrative Organization ' \
                          'Plan' not in text22:
        fail('the FY2022 report no longer prints Article 7 and its 136-28 vote as quoted')
    out['town-facilities-grounds'] = TP.page(
        'town-facilities-grounds',
        'Facilities and grounds were voted %s for %s and grew %s a year.'
        % (C.usd(fg['last']), Y1, C.pct(fg['rate'])),
        [voted('voted', 'facilities-grounds'), share('share', 'facilities-grounds'),
         rate('rate', 'facilities-grounds'), excess('excess', 'facilities-grounds'),
         f('fgl', U(fl['Facilities & Grounds']), 'the Facilities & Grounds line, %s' % Y1,
           'published', allow=(Y1,)),
         f('pb', U(fl['Public Buildings']), 'Public Buildings, %s' % Y1, 'published', allow=(Y1,)),
         f('park', U(fl['Park Department']), 'Park Department, %s' % Y1, 'published',
           allow=(Y1,)),
         f('vote', figure(136, '136–28', 'votes'), 'Article 7, May 2022, reorganising Public '
           'Works', 'published', allow=('7', '2022')),
         f('report', None, 'a Facilities report in the annual town report', 'gap',
           closes='a department report in the annual town report; none appears FY2023 to '
                  'FY2025'),
         f('staff', None, 'how many people Facilities employs', 'gap',
           closes='a Facilities staff listing or establishment of posts')],
        [con('The vote that reorganised Public Works passed %s to %s at the May 2022 Annual '
             'Town Meeting.' % ('136', '28'), ['vote'], allow=('136', '28', '2022'),
             notes=[step('That the reorganisation created this budget group is our reading of '
                         'the plan’s title; the plan itself is on file with the Town Clerk.',
                         'gap', closes='the Administrative Organization Plan of April 2022',
                         allow=('2022',))]),
         con('Its three lines are Facilities & Grounds, Public Buildings and the Park Department.',
             ['fgl', 'pb', 'park']),
         con('A group voted %s files no report of its own and prints no staff count.'
             % C.usd(fg['last']), ['report', 'staff'], {'a': U(fg['last'])})],
        table=lines_table('facilities-grounds', 'Facilities and grounds’ lines'),
        sources=[src['ar22'], src['ar23'], src['ar24'], src['ar25'], src['tb'],
                 dept_src('facilities-grounds')],
        finding_figures={'a': U(fg['last']), 'b': P(fg['rate'])}, finding_allow=(Y1,))

    # ------------------------------------------------ trash and recycling
    sw = D['solid-waste']
    if len([l for l in DP['solid-waste']['lines']['2025'] if l['amount']]) != 1:
        fail('trash and recycling is no longer one voted line')
    out['town-solid-waste'] = TP.page(
        'town-solid-waste',
        'Trash and recycling grew %s a year, the fastest of the twelve, from %s to %s.'
        % (C.pct(sw['rate']), C.usd(sw['first']), C.usd(sw['last'])),
        [f('v0', U(sw['first']), 'voted, %s' % Y0, 'published', allow=(Y0,)),
         voted('v1', 'solid-waste'), rate('rate', 'solid-waste'), share('share', 'solid-waste'),
         excess('excess', 'solid-waste'),
         f('contract', None, 'the hauling contract’s price schedule', 'gap',
           closes='the town’s collection contract and its annual price terms')],
        [con('It grew fastest and is %s of the budget: %s a year past the cap in dollars.'
             % (C.pct(sw['share']), C.usd(sw['excess'])), ['rate', 'share', 'excess'],
             {'a': P(sw['share']), 'b': U(sw['excess'])}),
         con('The group is one line, Recycling Program, so the omnibus cannot show what in it '
             'rose.', ['v0', 'v1', 'contract'],
             notes=[step('A step in a collection contract’s price would produce this shape; '
                         'nothing here tests it.', 'hypothesis')])],
        sources=[src['ar22'], src['ar24'], src['tb'], dept_src('solid-waste')],
        finding_figures={'a': P(sw['rate']), 'b': U(sw['first']), 'c': U(sw['last'])})

    # ------------------------------------------------ library
    lb = D['library']
    lib = emp['Library']
    out['town-library'] = TP.page(
        'town-library',
        'The library was voted %s for %s, %s of the budget, growing %s a year.'
        % (C.usd(lb['last']), Y1, C.pct(lb['share']), C.pct(lb['rate'])),
        [f('v0', U(lb['first']), 'voted, %s' % Y0, 'published', allow=(Y0,)),
         voted('v1', 'library'), share('share', 'library'), rate('rate', 'library'),
         excess('excess', 'library'),
         f('staff', N(lib['people'], 'people'), 'staff the library stated, FY%s, its only count'
           % lib['last_fy'], 'published', allow=('FY%s' % lib['last_fy'],))],
        [con('Its rate is high and its size small: %s a year past the cap in dollars.'
             % C.usd(lb['excess']), ['rate', 'share', 'excess'], {'a': U(lb['excess'])}),
         con('The library is one voted line, so what inside it rose is not in the omnibus.',
             ['v0', 'v1'], notes=[why_gap('the library line')]),
         con('Its only printed staff count is from FY%s.' % lib['last_fy'], ['staff'],
             allow=('FY%s' % lib['last_fy'],))],
        sources=[src['ar22'], src['ar24'], src['tb'], dept_src('library'), src['d-staff']],
        finding_figures={'a': U(lb['last']), 'b': P(lb['share']), 'c': P(lb['rate'])},
        finding_allow=(Y1,))

    # ------------------------------------------------ smaller departments
    asst, hs, cp = D['assistance'], D['health-sanitation'], D['central-purchasing']
    trio = [asst, hs, cp]
    t_share = sum(d['share'] for d in trio)
    t_ex = sum(d['excess'] for d in trio)
    hl = {l['label']: l['amount'] for l in DP['health-sanitation']['lines']['2025'] if l['amount']}
    nash = hl['Nashoba Board of Health'] + hl['Nashoba Nursing']
    out['town-smaller-departments'] = TP.page(
        'town-smaller-departments',
        'Veterans and elder services, health, and central purchasing are %s of the budget '
        'together.' % C.pct(t_share),
        [f('asst', U(asst['last']), 'Council on Aging and veterans, %s' % Y1, 'published',
           allow=(Y1,)),
         f('asst-rate', P(asst['rate']), 'a year, Council on Aging and veterans', 'published'),
         f('hs', U(hs['last']), 'health and sanitation, %s' % Y1, 'published', allow=(Y1,)),
         f('hs-rate', P(hs['rate']), 'a year, health and sanitation', 'published'),
         f('nash', U(nash), 'of it to the Nashoba board and nursing', 'published'),
         f('cp', U(cp['last']), 'Central Purchasing, %s' % Y1, 'published', allow=(Y1,)),
         f('cp-rate', P(cp['rate']), 'a year, Central Purchasing, under the cap', 'published'),
         f('ex', U(t_ex), 'the three, a year above the cap (ours)', 'estimate'),
         f('asst-lines', None, 'Council on Aging and veterans, line by line', 'gap',
           closes='the Council on Aging and Veterans subtotals the omnibus prints, not yet read')],
        [con('Together they are %s of the budget and %s a year past the cap in dollars.'
             % (C.pct(t_share), C.usd(t_ex)), ['asst', 'hs', 'cp', 'ex'],
             {'a': P(t_share), 'b': U(t_ex)}),
         con('Of health and sanitation, %s, or %s, goes to the regional Nashoba board and '
             'nursing.' % (C.usd(nash), C.pct(100 * nash / hs['last'], 0)), ['nash', 'hs'],
             {'a': U(nash), 'b': P(100 * nash / hs['last'], 0)}),
         con('Central Purchasing grew %s a year, under the cap.' % C.pct(cp['rate']),
             ['cp-rate', 'cp'], {'a': P(cp['rate'])})],
        table=dict(caption='The three smaller groups', views=[dict(
            key='small', label='%s to %s' % (Y0, Y1), total_col=1,
            kinds=['ledger'] * 4, columns=[Y0, Y1, 'A year', 'Above the cap (ours)'],
            rows=[dict(label=ROW(d), cells=[C.usd(d['first']), C.usd(d['last']),
                                            C.pct(d['rate']), C.usd(d['excess'])]) for d in trio],
            note='Group totals as the omnibus prints them. The Council on Aging and Veterans '
                 'lines are not yet read into a dataset.')]),
        sources=[src['ar22'], src['ar24'], src['tb'], dept_src('assistance'),
                 dept_src('health-sanitation'), dept_src('central-purchasing')],
        finding_figures={'a': P(t_share)})

    # ------------------------------------------------ town staff counts
    town_emp = [e for e in TPL['employers'] if e['department'] != 'Schools']
    if len(town_emp) != 8:
        fail('there are no longer eight town departments that print a count')
    forms = sorted({e['kind'] for e in town_emp})
    stale = [e for e in town_emp if int(e['last_fy']) < 2023]
    slug = lambda n: n.lower().replace(' ', '-').replace('department-of-', '')
    facts = []
    for e in sorted(town_emp, key=lambda e: -e['people']):
        unit = 'posts' if 'establishment' in e['kind'] else 'people'
        name = e['department'].replace(' Department', '').replace('Department of ', '')
        facts.append(f(slug(e['department']), N(e['people'], unit), '%s, %s, FY%s'
                       % (name, unit, e['last_fy']), 'published', allow=('FY%s' % e['last_fy'],)))
    facts.append(f('total', None, 'one town-wide headcount by department', 'gap',
                   closes='a payroll listing by department; the gross wages list stopped '
                          'naming departments after FY2016'))
    ids = [x['id'] for x in facts]
    out['town-staff-counts'] = TP.page(
        'town-staff-counts',
        '%s town departments print a staff count, in %s different forms that cannot be added up.'
        % (C.num(len(town_emp)), C.num(len(forms))),
        facts,
        [con('The %s counts come in %s forms: named rosters, posts, ranges and a stated '
             'number.' % (C.num(len(town_emp)), C.num(len(forms))), ids[:-1] + ['total'],
             {'a': N(len(town_emp)), 'b': N(len(forms))},
             notes=[step('A count is people present, not funded posts; a post can be vacant and '
                         'still printed, or cut and its holder moved.', 'gap',
                         closes='each department’s establishment of posts, with FTE')]),
         con('%s of the %s last printed a count before FY2023.'
             % (C.num(len(stale)), C.num(len(town_emp))),
             [slug(e['department']) for e in stale], {'a': N(len(stale)), 'b': N(len(town_emp))},
             allow=('FY2023',))],
        chart=dict(id='town-personnel-counts', source='/data/town-personnel.json'),
        table=dict(caption='Each department’s own count', views=[dict(
            key='counts', label='Latest', total_col=0, kinds=['ledger', 'ledger', 'ledger'],
            columns=['Count', 'Year', 'What it counts'],
            rows=[dict(label=e['department'], cells=[C.num(e['people']), 'FY%s' % e['last_fy'],
                                                     e['kind']])
                  for e in sorted(town_emp, key=lambda e: -e['people'])],
            note='As each department prints it in its own annual report. School staff are on '
                 'the School staffing shelf.')]),
        sources=[src['ar25'], src['ar24'], src['d-staff'], src['tp']],
        finding_figures={'a': N(len(town_emp)), 'b': N(len(forms))})

    # ------------------------------------------------ budgets without headcounts
    counted_groups = {BTP.BUDGET_GROUP[e['department']] for e in TPL['employers']
                      if e['department'] in BTP.BUDGET_GROUP}
    names = {d['name']: d for d in D.values()}
    if not counted_groups <= set(names):
        fail('a budget group in BUDGET_GROUP is not one of the twelve')
    uncounted = [names[n] for n in names if n not in counted_groups]
    kinds = {n: BTP.NO_COUNT[n][0] for n in (d['name'] for d in uncounted)}
    spend = [d for d in uncounted if kinds[d['name']] == 'a category of spending']
    bought = [d for d in uncounted if kinds[d['name']] == 'bought as a service']
    quiet = [d for d in uncounted if kinds[d['name']] not in ('a category of spending',
                                                              'bought as a service')]
    # NO_COUNT's own words for Facilities are a judgement ("no paper trail"); the table says
    # what was looked for and not found, which is all this page can stand behind (rule 8).
    SHOW = {'a department with a budget and no paper trail':
            'a department; no report or count printed'}
    if [d['slug'] for d in quiet] != ['facilities-grounds']:
        fail('Facilities is no longer the one uncounted group that is a department')
    out['town-headcount-coverage'] = TP.page(
        'town-headcount-coverage',
        '%s of the %s budget groups have a published staff count behind them; one department '
        'with a budget has none.' % (C.num(len(counted_groups)), C.num(len(D))),
        [f('counted', figure(len(counted_groups), '%d of %d' % (len(counted_groups), len(D)),
                             'groups'), 'groups with at least one staff count', 'published'),
         f('spend', U(sum(d['last'] for d in spend)), 'in %s groups that employ nobody: debt, '
           'benefits, purchasing' % C.num(len(spend)), 'published', {'n': N(len(spend))}),
         f('bought', U(sum(d['last'] for d in bought)), 'in %s groups bought as a service'
           % C.num(len(bought)), 'published', {'n': N(len(bought))}),
         f('fac', U(quiet[0]['last']), 'Facilities and grounds, %s, with no count' % Y1,
           'published', allow=(Y1,)),
         f('fac-gap', None, 'the people behind Facilities and grounds', 'gap',
           closes='a Facilities staff listing or establishment of posts')],
        [con('Of the %s uncounted groups, %s are categories of spending and %s are bought '
             'services.' % (C.num(len(uncounted)), C.num(len(spend)), C.num(len(bought))),
             ['spend', 'bought', 'counted'],
             {'a': N(len(uncounted)), 'b': N(len(spend)), 'c': N(len(bought))}),
         con('Facilities and grounds is the one department voted money with no staff count '
             'anywhere.', ['fac', 'fac-gap'],
             notes=[step('A group with a count is not a group that is counted: General '
                         'Government prints two offices’ staff and none for the rest.', 'gap',
                         closes='each office’s establishment of posts')])],
        table=dict(caption='Groups with no staff count', views=[dict(
            key='none', label=Y1, total_col=0, kinds=['ledger', 'ledger'],
            columns=['Voted', 'Why there is no count'],
            rows=[dict(label=ROW(d), cells=[C.usd(d['last']), SHOW.get(kinds[d['name']],
                                                                         kinds[d['name']])])
                  for d in sorted(uncounted, key=lambda d: -d['last'])],
            note='Why: our reading of each group’s printed lines and of the annual report’s '
                 'department pages.')]),
        sources=[src['ar24'], src['ar25'], src['tb'], src['tp'], src['d-staff']],
        finding_figures={'a': N(len(counted_groups)), 'b': N(len(D))})

    # ------------------------------------------------ the hub
    h = {}
    h['h-total'] = f('h-total', U(total), 'voted for twelve groups, %s' % Y1, 'published',
                     allow=(Y1,))
    h['h-sch'] = f('h-sch', P(sch['share']), 'of it to the schools', 'published')
    h['h-top4'] = f('h-top4', P(top4_share), 'in the four largest groups', 'published')
    h['h-26'] = f('h-26', U(tots[2026]), 'voted for FY2026; the report prints no department table',
                  'published', allow=('FY2026',))
    h['h-cap'] = f('h-cap', P(CAP), 'a year the levy may rise, before new growth', 'statute')
    h['h-above'] = f('h-above', figure(len(above), '%s of %s' % (len(above), len(D)), 'groups'),
                     'groups growing faster than the cap', 'published')
    h['h-ben'] = f('h-ben', U(bn['excess']), 'benefits, a year above the cap (ours)', 'estimate')
    h['h-sch-ex'] = f('h-sch-ex', U(sch['excess']), 'schools, a year above the cap (ours)',
                      'estimate')
    h['h-debt'] = f('h-debt', U(fall), 'less for debt service, %s than %s' % (Y1, Y0),
                    'published', allow=(Y1, Y0))
    h['h-forms'] = f('h-forms', N(len(town_emp), 'departments'),
                     'town departments printing a staff count', 'published')
    h['h-asked'] = f('h-asked', None, 'each department’s budget request', 'gap',
                     closes='department budget requests to the Finance Committee')
    h['h-service'] = f('h-service', None, 'whether any service was reduced', 'gap',
                       closes='each department’s activity figures, year by year')
    tiers = [
        LD.tier('What is voted', [h['h-total'], h['h-sch'], h['h-top4'], h['h-26']]),
        LD.tier('How it grows', [h['h-cap'], h['h-above'], h['h-ben'], h['h-sch-ex'],
                                 h['h-debt']]),
        LD.tier('What is not shown', [h['h-forms'], h['h-asked'], h['h-service']]),
    ]
    hub_ladder = LD.ladder(tiers, [
        LD.conclusion('Schools are %s of the %s voted budget; four groups are %s of it.'
                      % (C.pct(sch['share']), Y1, C.pct(top4_share)), ['h-sch', 'h-top4', 'h-total'],
                      {'a': P(sch['share']), 'b': P(top4_share)}, allow=(Y1,)),
        LD.conclusion('By dollars past the cap, benefits push hardest (%s a year), then the '
                      'schools (%s).' % (C.usd(bn['excess']), C.usd(sch['excess'])),
                      ['h-ben', 'h-sch-ex', 'h-cap'],
                      {'a': U(bn['excess']), 'b': U(sch['excess'])}),
        LD.conclusion('%s groups grew faster than the cap from %s to %s.'
                      % ('%s of %s' % (len(above), len(D)), Y0, Y1), ['h-above', 'h-cap'],
                      {'a': figure(len(above), '%s of %s' % (len(above), len(D)))},
                      allow=(Y0, Y1)),
        LD.conclusion('Debt service fell %s while the total still rose.' % C.usd(fall),
                      ['h-debt'], {'a': U(fall)}),
        LD.conclusion('A voted budget is already balanced: requests and service levels are not '
                      'in it.', ['h-asked', 'h-service']),
        LD.conclusion('%s town departments print a staff count, in forms that cannot be added.'
                      % C.num(len(town_emp)), ['h-forms'], {'a': N(len(town_emp))}),
    ])
    out[CID] = TP.hub(
        CID,
        'Town Meeting voted %s across twelve groups for %s; the schools are %s. Ranked by dollars '
        'past the %s levy cap, employee benefits push the budget hardest, then the schools.'
        % (C.usd(total), Y1, C.pct(sch['share']), C.pct(CAP)),
        hub_ladder,
        chart=dict(id='town-budgets-share', source='/data/town-budgets.json'),
        answer_figures={'a': U(total), 'b': P(sch['share']), 'c': P(CAP)},
        answer_allow=(Y1,))

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
        print('department budgets topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
