#!/usr/bin/env python3.11
"""SCHOOL FACILITY JOBS: every purchase order on the school building-and-grounds lines, as a
dataset and a database table, and the capital-rankings companion page that sets them against the
Town's capital test.

    python3.11 scripts/build_school_facility_jobs.py           # write the CSV and the page
    python3.11 scripts/build_school_facility_jobs.py --check   # fail if either would change

TJ, 21 November 2026: *"we probably need a companion report for the schools for /capital-rankings
that shows that the school has permanent, operational funding for projects that are WELL WITHIN
the purview of capital planning"* -- and *"i want this to be an automated thing. anytime we get new
data that can fill in the facility jobs table, that should be done automatically too"*. So this
is a generator in check_generated.CHECKS: when the school journal changes, --check goes stale and
the refresh's repair pass rebuilds the table, the database and the page with no one asking.

THE GRAIN is the PURCHASE ORDER, not the invoice: an order carries what was bought in its own
words, the date it was opened, and its total. Invoices on this journal carry only an invoice
number. `ordered` is the order as opened plus any increase (POE + positive POM); `paid` is the
encumbrance relieved by invoices (POL). An order closed without payment shows ordered > paid.
Carry-forward re-encumbrances (SOY) are not counted again.

THE SCOPE is the buildings pages' scope exactly -- general fund department 300, every non-salary
account in DESE functions 4000-4999 except utilities (build_school_surplus.category_of) -- so a
figure here and a figure on /buildings-and-grounds are the same postings.

TWO THINGS ARE OURS, and the page says so:
  * `kind` -- one-time job or recurring order -- read off each order's own description, one row
    each in sources/data/school-facility-job-kinds.csv with the words it was read from. Only
    orders of REVIEW_FLOOR or more are read. A NEW order at or over that line that is not yet in
    the file is written as `not yet read`, printed by this script, and counted on the page, so new
    data lands automatically and its reading is visibly pending rather than guessed.
  * `job` -- several orders grouped as one piece of work. The Town's own definition allows it:
    a capital item is anything costing $20,000 or more with a useful life of three years or more,
    "OR Groups of items of the same purpose that cost at least $20,000" (Article 13, FY2027
    Capital Plan, page 2). The grouping is declared in the kinds file, never inferred.

THE THRESHOLD is the Town's printed one, $20,000 (FY2024 Town Manager budget message, and the
Article 13 deck). Only the COST half of the test is measured: a ledger records no useful life.

RULE 7. That an order met the cost test is arithmetic. Whether it SHOULD have gone to capital, or
why it was bought from the operating line, is not in any ledger and the page never says it.
"""
import argparse
import csv
import io
import json
import os
import sys
from collections import OrderedDict, defaultdict
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
import topic_blocks as TB  # noqa: E402
import journal as J  # noqa: E402
import build_school_surplus as S  # noqa: E402

DATA = os.path.join(ROOT, 'sources', 'data')
OUT_CSV = os.path.join(DATA, 'school-facility-jobs.csv')
KINDS_CSV = os.path.join(DATA, 'school-facility-job-kinds.csv')
RANKINGS_CSV = os.path.join(DATA, 'capital-rankings.csv')
ID = 'school-facility-jobs'
OUT_JSON = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % ID)
D0 = Decimal(0)
THRESHOLD = Decimal(20000)
REVIEW_FLOOR = Decimal(10000)
KINDS = ('one-time job', 'recurring order')
UNREAD = 'not yet read'
BELOW = 'not read (under $10,000)'
COLUMNS = ['fiscal_year', 'po', 'opened', 'vendor', 'description', 'account', 'account_description',
           'org_name', 'ordered', 'paid', 'closed_unpaid', 'kind', 'job', 'job_ordered', 'job_paid',
           'threshold', 'meets_cost_test', 'journal', 'page', 'kind_basis']

DOCS = OrderedDict([
    ('journal', ('Town of Lunenburg — school department journal detail, FY2023–FY2026 (MUNIS), our redacted reading',
                 J.PUBLIC['journal'])),
    ('jobs', ('Lunenburg Budget Project — school-facility-jobs.csv (every order on the upkeep lines; ours)',
              '/docs/data/school-facility-jobs.csv')),
    ('kinds', ('Lunenburg Budget Project — school-facility-job-kinds.csv (each order read as a job or a '
               'recurring order, with the words it was read from; ours)', '/docs/data/school-facility-job-kinds.csv')),
    ('art13', ('Capital Planning Committee — Article 13, FY2027 Capital Plan, page 2: what counts as capital',
               '/docs/town-budget/docs/4111-article-13-fy-2027-capital-plan.pdf')),
    ('tm24', ('Town Manager — FY2024 preliminary budget message: the $20,000 threshold for capital',
              '/docs/town-budget/docs/a187-fy24-town-manager-preliminary-budget-message-and-proposal-pdf.pdf')),
    ('cpc13', ('Capital Planning Committee — minutes, 6 June 2013: Form F deleted',
               '/docs/meetings/capital-planning-committee/2013-06-06-minutes-1185.pdf')),
    ('scplan', ('School Committee — FY26–FY35 capital plan, approved 4 September 2024, page 23',
                '/docs/district-budget/docs/sc-meetings/2024-2025-fy26-fy35-capital-plan.pdf')),
    ('rank', ('Lunenburg Budget Project — capital-rankings.csv (every ranked capital request, FY2023–FY2027)',
              '/docs/data/capital-rankings.csv')),
])


def fail(msg):
    raise SystemExit('build_school_facility_jobs: ' + msg)


def fl(x):
    return float(x)


def money(v):
    return '%.2f' % v


# ------------------------------------------------------------------ the dataset

def kinds():
    out = {}
    for r in csv.DictReader(open(KINDS_CSV, encoding='utf-8', newline='')):
        if r['po'] in out:
            fail('order %s is in the kinds file twice' % r['po'])
        if r['kind'] not in KINDS:
            fail('order %s: kind %r is not one of %s' % (r['po'], r['kind'], KINDS))
        if not r['basis'].strip():
            fail('order %s has no basis in the kinds file' % r['po'])
        out[r['po']] = r
    return out


def orders():
    """{po: order}, every purchase order on the upkeep lines."""
    A = J.accounts()
    cat = lambda r: S.category_of(dict(account=r['account'], obj=r['object']))
    po = {}
    for r in J.lines():
        if r['doc_type'] != 'PO' or not J.in_surplus_scope(A[r['account']]) or cat(r) != 'buildings':
            continue
        o = po.setdefault(r['doc_no'], dict(po=r['doc_no'], ordered=D0, paid=D0, closed=D0, opened='',
                                            vendor=r['vendor'], description='', accounts=OrderedDict(),
                                            orgs=OrderedDict(), journal='', page='', pol=''))
        o['accounts'][r['account']] = r['account_description']
        o['orgs'][r['org_name']] = 1
        if r['source'] == 'POE':
            o['ordered'] += r['amt']
            o['opened'] = o['opened'] or r['effective_date']
            o['description'] = o['description'] or r['description'].strip()
            o['journal'], o['page'] = o['journal'] or r['journal'], o['page'] or r['page']
        elif r['source'] == 'POM':
            if r['amt'] > 0:
                o['ordered'] += r['amt']
            else:
                o['closed'] -= r['amt']
        elif r['source'] == 'POL':
            o['paid'] -= r['amt']
            o['pol'] = o['pol'] or r['description'][:-4].strip()
            if not o['journal']:
                o['journal'], o['page'] = r['journal'], r['page']
    for o in po.values():
        if not o['description']:      # an order opened before the journal begins: its payment's words
            o['description'] = o['pol']
        o['fy'] = 2000 + int(o['po'][:2])
    if not po:
        fail('no purchase orders found on the upkeep lines')
    return po


def table():
    """[row], the dataset, and the list of orders at or over REVIEW_FLOOR not yet read."""
    po, K = orders(), kinds()
    stale = sorted(set(K) - set(po))
    if stale:
        fail('the kinds file names orders that are not on the upkeep lines: %s' % ', '.join(stale))
    jobs = defaultdict(lambda: dict(ordered=D0, paid=D0))
    for p, o in po.items():
        if p in K and K[p]['job']:
            jobs[K[p]['job']]['ordered'] += o['ordered']
            jobs[K[p]['job']]['paid'] += o['paid']
    rows, unread = [], []
    for p in sorted(po, key=lambda p: (po[p]['fy'], p)):
        o = po[p]
        big = max(o['ordered'], o['paid']) >= REVIEW_FLOOR
        k = K.get(p)
        kind = k['kind'] if k else (UNREAD if big else BELOW)
        if kind == UNREAD:
            unread.append(o)
        job = k['job'] if k else ''
        jo, jp = (jobs[job]['ordered'], jobs[job]['paid']) if job else (o['ordered'], o['paid'])
        meets = 'paid' if jp >= THRESHOLD else ('ordered only' if jo >= THRESHOLD else 'no')
        rows.append(OrderedDict(
            fiscal_year=o['fy'], po=p, opened=o['opened'], vendor=o['vendor'], description=o['description'],
            account='; '.join(o['accounts']), account_description='; '.join(o['accounts'].values()),
            org_name='; '.join(o['orgs']), ordered=money(o['ordered']), paid=money(o['paid']),
            closed_unpaid=money(o['closed']), kind=kind, job=job, job_ordered=money(jo), job_paid=money(jp),
            threshold=money(THRESHOLD), meets_cost_test=meets, journal=o['journal'], page=o['page'],
            kind_basis=k['basis'] if k else ''))
    return rows, unread


def render_csv(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


# ------------------------------------------------------------------ the page

def school_requests():
    """{fy: [(project, amount, funded)]}: what the Schools asked capital planning for."""
    out = defaultdict(list)
    for r in csv.DictReader(open(RANKINGS_CSV, encoding='utf-8', newline='')):
        if r['department'] == 'Schools' and r['amount']:
            out[int(r['fiscal_year'])].append((r['project'], Decimal(r['amount']), r['funded'] == 'yes'))
    return out


def page(rows, unread):
    years = list(J.YEARS)
    U = lambda v: figure(fl(v), C.usd(fl(v)))
    F = lambda y: figure(y, C.fy(y), 'fiscal year')
    N = lambda n, unit: figure(n, C.num(n), unit)
    T = U(THRESHOLD)
    inwin = [r for r in rows if r['fiscal_year'] in years]

    # capital-sized one-time work: by job where grouped, by order otherwise
    work = OrderedDict()
    for r in inwin:
        if r['kind'] != 'one-time job':
            continue
        key = r['job'] or r['po']
        w = work.setdefault(key, dict(rows=[], paid=Decimal(r['job_paid']), ordered=Decimal(r['job_ordered']),
                                      meets=r['meets_cost_test'], fy=r['fiscal_year']))
        w['rows'].append(r)
    paid_jobs = [w for w in work.values() if w['meets'] == 'paid']
    open_jobs = [w for w in work.values() if w['meets'] == 'ordered only']
    if not paid_jobs:
        fail('no one-time job paid at or over the threshold; the page has nothing to say')
    paid_jobs.sort(key=lambda w: -w['paid'])
    tot = sum((w['paid'] for w in paid_jobs), D0)
    top = paid_jobs[0]
    times = fl(top['paid']) / fl(THRESHOLD)
    n_orders = sum(len(w['rows']) for w in paid_jobs)
    top_words = top['rows'][0]['description']
    if '911' not in ' '.join(r['description'] for r in top['rows']):
        fail('the largest capital-sized job is no longer the 911 work; rewrite the panels')
    top_opened = min(r['opened'] for r in top['rows'])
    if not top_opened.startswith('2024-09'):
        fail('the 911 orders were not opened in September 2024: %s' % top_opened)

    # ---- 1. the signature: every order, one dollar scale, the capital line drawn
    REQ = school_requests()
    kinds_def = [dict(key='one-time job', label='One-time job, school upkeep budget', colour=1),
                 dict(key='recurring order', label='Recurring order, school upkeep budget', colour=3),
                 dict(key='below', label='Under $10,000, not read', colour=0),
                 dict(key='unread', label='Not yet read', colour=5),
                 dict(key='request', label='Capital request by the Schools', colour=2, hollow=True)]
    FLOOR = Decimal(2000)                  # dots under this crowd the left edge; the note says so
    srows, tips, figs = [], set(), {C.usd(fl(THRESHOLD)), C.usd(fl(FLOOR))}
    for y in years:
        mine = [r for r in inwin if r['fiscal_year'] == y and Decimal(r['paid']) >= FLOOR]
        over = sum(1 for w in paid_jobs if w['fy'] == y)
        dots = []
        for r in sorted(mine, key=lambda r: Decimal(r['paid'])):
            tip = '%s · %s · %s' % (r['vendor'].title(), r['description'], C.usd(fl(Decimal(r['paid']))))
            tips.add(tip)
            k = r['kind'] if r['kind'] in KINDS else ('below' if r['kind'] == BELOW else 'unread')
            dots.append(dict(amt=fl(Decimal(r['paid'])), kind=k, tip=tip))
        paid_y = sum((Decimal(r['paid']) for r in inwin if r['fiscal_year'] == y), D0)
        n_t, t_t = C.num(over), C.usd(fl(paid_y))
        figs |= {C.fy(y), n_t, t_t}
        srows.append(dict(label=C.fy(y), sub='Paid from the upkeep budget', dots=dots, n_text=n_t,
                          total_text=t_t, group=True))
        rq = REQ.get(y, [])
        rdots = []
        for p, a, ok in sorted(rq, key=lambda x: x[1]):
            tip = '%s · %s · %s' % (p, C.usd(fl(a)), 'funded' if ok else 'not funded')
            tips.add(tip)
            rdots.append(dict(amt=fl(a), kind='request', tip=tip))
        rn = C.num(sum(1 for _, a, _ in rq if a >= THRESHOLD))
        rt = C.usd(fl(sum((a for _, a, _ in rq), D0)))
        figs |= {rn, rt}
        srows.append(dict(label='', sub='Asked of capital planning', dots=rdots, n_text=rn, total_text=rt,
                          group=False))
    ticks = [Decimal(v) for v in (2000, 20000, 200000, 2000000)]
    hi = max([fl(d['amt']) for r in srows for d in r['dots']] + [1])
    ticks = [t for t in ticks if fl(t) <= hi * 10]
    figs |= {C.usd(fl(t)) for t in ticks}
    sdata = dict(rows=srows, kinds=kinds_def, ticks=[dict(v=fl(t), text=C.usd(fl(t))) for t in ticks],
                 line=dict(v=fl(THRESHOLD), text='The Town’s capital test, %s' % C.usd(fl(THRESHOLD))),
                 text=dict(row='Fiscal year', dots='Each order or request, by its cost',
                           n='Jobs or requests over the line', total='Paid or requested'),
                 note='Orders paid %s or more are drawn; smaller ones are counted in the total. An order is '
                      'placed by what was paid against it. The scale is logarithmic: each step is ten times '
                      'the one before. A request is placed by the amount on the committee’s list.'
                      % C.usd(fl(FLOOR)))
    if not unread:
        sdata['kinds'] = [k for k in kinds_def if k['key'] != 'unread']
    strips = TB.custom('dollar-strips', 'Upkeep orders against the capital line', sdata, place='lead',
                       figures=sorted(figs), allow=sorted(tips),
                       alt='For each fiscal year, every purchase order paid from the school upkeep budget as a dot '
                           'on a dollar scale, coloured by kind, above the Schools’ capital requests for the same '
                           'year, with a dashed line at the Town’s capital threshold.',
                       so='Dots right of the dashed line on an upkeep row are orders the size of a capital request, '
                          'paid from the operating budget.')

    # ---- 2. what counts as capital (a definition a reader will otherwise supply themselves)
    define = TB.explain('What counts as capital', [
        ('The Capital Planning Committee’s definition: **any tangible item costing %s or more with a useful '
         'life of three years or longer, or groups of items of the same purpose that together cost at least '
         '%s.**' % (C.usd(fl(THRESHOLD)), C.usd(fl(THRESHOLD))), None, (C.usd(fl(THRESHOLD)),)),
        ('Only the cost test can be measured here. A purchase order records what was bought and what was '
         'paid, never how long it will last.', None, ()),
        ('Until June 2013 the committee had a form for capital items over %s bought from an operating budget '
         'or a grant, Form F. Its minutes record the form being deleted and do not record why.'
         % C.usd(10000), None, (C.usd(10000), 'June 2013')),
    ], place='body', tone='define')

    # ---- 3. the capital-sized jobs, one row each
    jrows = []
    for w in paid_jobs + open_jobs:
        first = w['rows'][0]
        name = first['description'] if len(w['rows']) == 1 else '%s, %d orders' % (first['description'], len(w['rows']))
        jrows.append(dict(label=name, cells=[
            C.fy(w['fy']), first['vendor'].title() if len({r['vendor'] for r in w['rows']}) == 1 else 'several',
            C.usd(fl(w['ordered'])), C.usd(fl(w['paid'])),
            '%.1f×' % (fl(max(w['paid'], w['ordered'])) / fl(THRESHOLD)),
            'paid' if w['meets'] == 'paid' else 'ordered, closed unpaid']))
    jobs_table = dict(caption='Capital-sized work on the upkeep budget', views=[dict(
        key='jobs', label='Every job at or over the line', kinds=['ledger'] * 6,
        columns=['Year', 'Vendor', 'Ordered', 'Paid', 'Times the line', 'Outcome'], rows=jrows,
        note='One-time jobs whose cost, grouped by purpose where several orders share one, is %s or more. '
             'The grouping and the reading of each order are ours: school-facility-job-kinds.csv.'
             % C.usd(fl(THRESHOLD)))])

    # ---- 4. the same purpose, two routes
    panels = TB.panels('One purpose, two routes', [
        TB.panel('Paid from the upkeep budget', [
            ('Opened', 'September 2024', None), ('Orders', C.num(len(top['rows'])), None),
            ('Paid', C.usd(fl(top['paid'])), 'good')],
            sub=('“NEW CABLING PROJECT FOR 911 CO” and “911 COMPLIANCE”, on the school upkeep line', None,
                 ('911',))),
        TB.panel('In the Schools’ capital plan', [
            ('Year planned', C.fy(2031), None), ('Projects', '1', None), ('Estimate', C.usd(225000), 'neutral')],
            sub=('“Districtwide Phone System Upgrade … maintain 911 compliance”, approved 4 September 2024',
                 None, ('911', '4 September 2024'))),
    ], note=('Both are the Schools’. The plan is the one the School Committee approved on 4 September 2024; '
             'the orders were opened twelve to twenty-one days later.', None,
             ('4 September 2024', 'twelve', 'twenty-one')),
        so='The same stated purpose appears on both routes; nothing held says whether the orders covered any '
           'of the planned scope.')

    # ---- 5. raw: every order of REVIEW_FLOOR or more
    big = [r for r in inwin if max(Decimal(r['ordered']), Decimal(r['paid'])) >= REVIEW_FLOOR]
    big.sort(key=lambda r: -max(Decimal(r['ordered']), Decimal(r['paid'])))
    def view(key, label, sub):
        return dict(key=key, label=label, kinds=['ledger'] * 6,
                    columns=['Year', 'Order', 'Vendor', 'Opened', 'Ordered', 'Paid'],
                    rows=[dict(label=r['description'], cells=[C.fy(r['fiscal_year']), r['po'], r['vendor'].title(),
                                                              r['opened'] or '—', C.usd(fl(Decimal(r['ordered']))),
                                                              C.usd(fl(Decimal(r['paid'])))]) for r in sub],
                    note='Purchase orders on the school upkeep lines, %s to %s, ordered or paid at %s or more, '
                         'read by us as %s. Every order of every size is school-facility-jobs.csv and the '
                         'school_facility_jobs table.' % (C.fy(years[0]), C.fy(years[-1]),
                                                           C.usd(fl(REVIEW_FLOOR)), label.lower()))
    views = [view('jobs', 'One-time jobs', [r for r in big if r['kind'] == 'one-time job']),
             view('recurring', 'Recurring orders', [r for r in big if r['kind'] == 'recurring order'])]
    rest = [r for r in big if r['kind'] not in KINDS]
    if rest:
        views.append(view('unread', 'Not yet read', rest))
    raw = dict(caption='Every order of %s or more' % C.usd(fl(REVIEW_FLOOR)), views=views)

    # ---- facts and conclusions, each under the visual it explains
    f = LD.fact
    facts = [
        f('njobs', N(len(paid_jobs), 'jobs'), 'one-time jobs paid at or over the capital line', 'published'),
        f('tot', U(tot), 'paid on those jobs, %s to %s' % (C.fy(years[0]), C.fy(years[-1])), 'published',
          label_figures={'a': F(years[0]), 'b': F(years[-1])}),
        f('line', T, 'the Town’s capital cost test', 'published'),
        f('top', U(top['paid']), 'the 911 work, paid', 'published', allow=('911',)),
        f('times', figure(times, '%.1f' % times, 'times'), 'the 911 work, as a multiple of the line', 'published',
          allow=('911',)),
        f('plan', U(225000), 'phone upgrade in the Schools’ capital plan', 'published'),
        f('planfy', F(2031), 'the year the plan places it', 'published'),
    ]
    if unread:                        # rested on by the first conclusion, built below
        facts.append(f('unread', N(len(unread), 'orders'), 'new orders of %s or more not yet read'
                       % C.usd(fl(REVIEW_FLOOR)), 'estimate', label_figures={'a': U(REVIEW_FLOOR)}))

    reqs = [a for y in years for _, a, _ in REQ.get(y, [])]
    smaller = sum(1 for a in reqs if a < top['paid'])
    con = TP.conclusion
    cons = [
        con('%s one-time jobs paid from the school upkeep budget met the %s capital test: %s in four years.'
            % (C.num(len(paid_jobs)), C.usd(fl(THRESHOLD)), C.usd(fl(tot))),
            ['njobs', 'tot', 'line'] + (['unread'] if unread else []), {'n': N(len(paid_jobs), 'jobs'), 't': T, 'a': U(tot)},
            so='Each is capital-sized by cost and was paid from the operating budget, not a capital article.'),
        con('The largest, %s of 911 compliance work in September 2024, was %s times the line.'
            % (C.usd(fl(top['paid'])), '%.1f' % times), ['top', 'times'],
            {'a': U(top['paid']), 'b': figure(times, '%.1f' % times, 'times')}, allow=('911', 'September 2024'),
            so='%s of the Schools’ %s capital requests in the same four years cost less.'
               % (C.num(smaller).capitalize(), C.num(len(reqs))),
            so_figures={'s': N(smaller, 'requests'), 'r': N(len(reqs), 'requests')}),
        con('The Schools’ capital plan lists a %s phone upgrade for %s to maintain 911 compliance.'
            % (C.usd(225000), C.fy(2031)), ['plan', 'planfy'], {'a': U(225000), 'y': F(2031)}, allow=('911',),
            so='Two routes carry the same stated purpose; which costs fall on which is not recorded.'),
    ]
    gaps = TB.explain('What the ledger does not show', [
        ('Why any of this work was bought from the upkeep budget rather than taken to capital planning. No '
         'document held records the choice.', None, ()),
        ('How long each item will last, the other half of the capital test.', None, ()),
        ('Whether the Town’s Facilities department does the same. Its contracted-services line is described '
         'as paying for “smaller projects under the %s threshold”, but its orders are not held: closes: the '
         'same MUNIS year-to-date report with journal detail, for department 193.' % C.usd(fl(THRESHOLD)),
         None, (C.usd(fl(THRESHOLD)), '193')),
    ] + ([('%s new orders of %s or more have not been read yet; they are listed as not yet read.'
           % (C.num(len(unread)), C.usd(fl(REVIEW_FLOOR))), None, (C.num(len(unread)), C.usd(fl(REVIEW_FLOOR))))]
         if unread else []), place='end', tone='plain')

    cite = TP.cite
    flow = ['finding',
            cite(strips, 'journal', 'jobs', 'rank', 'tm24'), ('conclusion', 0),
            cite(define, 'art13', 'tm24', 'cpc13'),
            cite(('table', 0), 'journal', 'jobs', 'kinds'), ('conclusion', 1),
            cite(panels, 'journal', 'scplan'), ('conclusion', 2),
            'related',
            cite(('table', 1), 'journal', 'jobs', 'kinds'),
            cite(gaps, 'journal', 'tm24'),
            'sources']
    sources = [dict(key=k, label=l, href=h) for k, (l, h) in DOCS.items()]
    finding = ('The school upkeep budget paid for %s jobs over the %s capital line in four years, %s in all.'
               % (C.num(len(paid_jobs)), C.usd(fl(THRESHOLD)), C.usd(fl(tot))))
    return TP.page(ID, finding, facts, cons, table=jobs_table, tables=[raw], sources=sources,
                   finding_figures={'n': N(len(paid_jobs), 'jobs'), 't': T, 'a': U(tot)}, flow=flow,
                   draft=None if ID in REG.TOPICS else dict(title='School upkeep and capital',
                                                            home='capital-rankings'))


def render():
    rows, unread = table()
    return render_csv(rows), json.dumps(page(rows, unread), ensure_ascii=False, sort_keys=True,
                                        separators=(',', ':')) + '\n', unread


def write(path, text):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    csv_text, page_text, unread = render()
    for o in unread:
        print('NOT YET READ: order %s, %s, %s, ordered %s paid %s -- add it to %s'
              % (o['po'], o['vendor'], o['description'], o['ordered'], o['paid'],
                 os.path.relpath(KINDS_CSV, ROOT)), file=sys.stderr)
    outs = [(OUT_CSV, csv_text), (OUT_JSON, page_text)]
    if a.check:
        stale = [p for p, t in outs if not os.path.exists(p) or open(p, encoding='utf-8').read() != t]
        for p in stale:
            print('STALE %s' % os.path.relpath(p, ROOT), file=sys.stderr)
        if stale:
            return 1
        print('school facility jobs: current')
        return 0
    for p, t in outs:
        write(p, t)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
