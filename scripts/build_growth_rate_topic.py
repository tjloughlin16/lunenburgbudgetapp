#!/usr/bin/env python3
"""The tax bill, explained: /homes-and-taxes/growth-and-tax-rate (the id is the page's first name).

TJ, 3 November 2026, turning this page into the one a Facebook post sends residents to: *"we're
going to push people here so they fully understand Lunenburg's tax rate, how it gets determined,
how it gets adjusted with the data."* So it now LEADS with what raised the average bill since
FY1991, split into causes that multiply to the actual rise (burden(), below), then how a bill is
set, then what changes an existing bill. What follows is the page's first purpose, still on it.


    python3 scripts/build_growth_rate_topic.py           # write the topic payload
    python3 scripts/build_growth_rate_topic.py --check   # fail if it would change

TJ, 2 November 2026, after the homes-and-bill chart went on the historical report: *"on a
separate page, we should take the 2 new charts on the history page, and also plot the
developments over time. i assume you are saying above that as developments rise, the tax rate
decreases. id love to see that if thats true and we have the data"*.

IT IS NOT TRUE, AND THE PAGE SAYS SO WITH THE DATA. Each year's change in the residential rate
is set against two things: how much the property already on the rolls changed in value, and how
much new development added (the state's certified new growth). The rate moves with the first
and hardly at all with the second. The MECHANISM is statute, not our reading: under Proposition
2 1/2 new growth is taxed at the prior year's rate and its tax is added to the levy limit, so
development adds to the base and to the levy together; the levy limit grows 2.5% a year on top
of that, so a capped levy spread over existing property worth more is a lower rate.

WHAT IS OURS, AND SAID SO ON THE PAGE:
  * a year's change in EXISTING property = (total value - new growth value) / last year's
    total - 1. Our arithmetic on two state files; it also absorbs revaluation, abatements and
    reclassification, which the files do not separate.
  * the correlations across the years. A correlation is not a cause; the cause here is the
    statute, and the page cites it as such.
  * inflation adjustment, by the Boston-area CPI-U averaged July to June.

NOT SEPARATED: overrides (each one passed in the window is marked in the table from the state's
own vote file) and debt exclusions, which that file does not carry.

Sources, all the state's: sources/data/dls-new-growth.csv, dls-assessed-values.csv,
dls-tax-rates.csv, dls-avg-tax-bill.csv, dls-override-votes.csv; and the BLS CPI responses.
"""
import argparse
import csv
import json
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topic_blocks as TB  # noqa: E402
import topics as REG  # noqa: E402
from build_historical_report import homes  # noqa: E402

TID = 'growth-and-tax-rate'
ME = os.path.basename(__file__)
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % TID)
D = os.path.join(ROOT, 'sources', 'data')
MANIFEST = os.path.join(D, 'archive-manifest.csv')


def fail(msg):
    raise SystemExit('build_growth_rate_topic: ' + msg)


def town(name):
    out = {}
    for r in csv.DictReader(open(os.path.join(D, name), encoding='utf-8')):
        if r['municipality'] == 'Lunenburg':
            out.setdefault(int(r['fy']), r)
    return out


def one_source(rows, name):
    s = {r['source_file'] for r in rows.values()}
    if len(s) != 1:
        fail('%s: expected one source file, got %s' % (name, sorted(s)))
    return 'state-dls/' + s.pop()


# THE YEARS BEFORE THE STATE'S FILES, from the town's own annual reports (TJ, 2 November 2026:
# "can we only go back to '04 for that new page?"). sources/data/report-new-growth-history.csv,
# written by scripts/extract_new_growth_history.py: every value re-derived from the text, each
# row proved by its own arithmetic, every repeated printing agreeing. The state's files take over
# where they begin (new growth FY2003, values FY2002, rates FY2003) and agree with the town's
# figures in every overlapping year the extractor compared, except new growth in FY2004, FY2005
# and FY2009 -- after the switch, so never read here.
STATE_FROM = 2003
HIST = os.path.join(D, 'report-new-growth-history.csv')


def town_history():
    """{field: {fy: value}} from the town's reports, each fiscal year's value the same in every
    printing that carries it, or the build refuses. Valuation and rate only from rows that close."""
    out = {'total_valuation': {}, 'tax_rate': {}, 'ng_added_valuation': {}}
    files = {}
    for r in csv.DictReader(open(HIST, encoding='utf-8')):
        y = int(r['fy'])
        for k in out:
            if not r[k]:
                continue
            if k != 'ng_added_valuation' and r['status'] != 'checked':
                continue
            # A new growth row whose own revenue identity failed is used only for its VALUATION,
            # and only because another printing prints the same figure (the extractor's rule).
            v = float(r[k])
            if out[k].setdefault(y, v) != v:
                fail('%s FY%d: two printings disagree (%s, %s)' % (k, y, out[k][y], v))
            if y < STATE_FROM:
                files.setdefault(r['edition_file'], set()).add(y)
    return out, files


def years_data():
    ng, av, tr = town('dls-new-growth.csv'), town('dls-assessed-values.csv'), town('dls-tax-rates.csv')
    th, tfiles = town_history()

    def total(y):
        return float(av[y]['total']) if y in av and av[y]['total'] else th['total_valuation'].get(y)

    def rt(y):
        return float(tr[y]['residential']) if y in tr and tr[y]['residential'] else th['tax_rate'].get(y)

    def new(y):
        return (float(ng[y]['total_value']) if y in ng and ng[y]['total_value'] else None) if y >= STATE_FROM \
            else th['ng_added_valuation'].get(y)
    for y in (2002,):   # the join: the town's figure and the state's must agree where both exist
        if y in av and th['total_valuation'].get(y) not in (None, float(av[y]['total'])):
            fail('FY%d total valuation: town %s, state %s' % (y, th['total_valuation'][y], av[y]['total']))
    rows = []
    for y in range(min(th['ng_added_valuation']), max(ng) + 1):
        v, v0, n, r, r0 = total(y), total(y - 1), new(y), rt(y), rt(y - 1)
        if None in (v, v0, n, r, r0):
            continue
        rows.append(dict(fy=y, total=v, prior=v0, new=n, src='state' if y >= STATE_FROM else 'town',
                         existing=round(((v - n) / v0 - 1) * 100, 2), dev=round(n / v0 * 100, 2),
                         rate=r, rate0=r0, rate_chg=round((r / r0 - 1) * 100, 2)))
    ys = [r['fy'] for r in rows]
    if not ys or ys != list(range(ys[0], ys[-1] + 1)):
        fail('the years with all three files are not consecutive: %s' % ys)
    keys = dict(ng=one_source(ng, 'new growth'), av=one_source(av, 'assessed values'),
                tr=one_source(tr, 'tax rates'))
    return rows, keys, tfiles


def overrides():
    out = {}
    for r in csv.DictReader(open(os.path.join(D, 'dls-override-votes.csv'), encoding='utf-8')):
        if r['municipality'] == 'Lunenburg' and r['result'] == 'WIN':
            out.setdefault(int(r['fy']), []).append(r)
    return out


# ---------------------------------------------------------------- what raised the average bill
LEVY = os.path.join(D, 'dls-levy-limits.csv')


def burden(h):
    """WHY THE AVERAGE BILL ROSE, FY(first) to FY(last), as factors that multiply to the actual
    rise (TJ, 3 November 2026: "what does change the tax burden on a property owner? ... put that
    right on the page and show it"). All of it is OUR ARITHMETIC on the state's files, and the
    page says so.

    The average single-family bill is the residential levy's single-family part spread over the
    single-family parcels:  bill = levy x homes' share x single-family part / parcels.  The levy is
    the levy limit plus debt exclusions less unused room, and the limit is last year's limit grown
    2.5%, plus new growth, plus overrides (Proposition 2 1/2, G.L. c.59 s.21C). Carrying every
    year's new growth and override forward at 2.5% splits the last year's limit exactly into
    three parts: the first year's limit grown 2.5% a year, new growth, overrides. So the rise is

        x 1.025^n                                        the 2.5% a year
        x (limit without overrides) / (first limit grown)  new growth, then / parcel growth
        x (limit) / (limit without overrides)              overrides
        x (levy / limit, last) / (levy / limit, first)     debt exclusions and unused room
        x homes' share, last / first                       the levy shifting onto homes
        x the rest (single-family part of the homes' levy) -- asserted near 1

    A part's SHARE of the rise is its log over the log of the whole, which does not depend on
    the order the parts are taken in; the bridge allocates the dollar rise by those shares."""
    import math
    lv = {int(r['fy']): r for r in csv.DictReader(open(LEVY, encoding='utf-8'))}
    ov = {}
    for r in csv.DictReader(open(os.path.join(D, 'dls-override-votes.csv'), encoding='utf-8')):
        if r['municipality'] == 'Lunenburg' and r['result'] == 'WIN':
            ov[int(r['fy'])] = ov.get(int(r['fy']), 0) + int(r['amount'])
    H = {r['fy']: r for r in h['rows']}
    a, z = h['rows'][0]['fy'], h['rows'][-1]['fy']
    g = lambda y, k: float(lv[y][k])
    n = z - a
    grown = lambda v, y: v * 1.025 ** (z - y)
    base = grown(g(a, 'levy_limit'), a)
    ng_c = ov_c = 0.0
    for y in range(a + 1, z + 1):
        o = ov.get(y, 0)
        ng = g(y, 'levy_limit') - 1.025 * g(y - 1, 'levy_limit') - o
        # THE CHECK THAT HAS POWER: where the state prints the year's new growth, our derived new
        # growth must equal it plus the residual the extractor recorded (amended growth). This
        # fails if an override is missing from, or wrong in, the vote file.
        if lv[y]['new_growth'] or lv[y]['components_residual']:
            printed = float(lv[y]['new_growth'] or 0) + float(lv[y]['components_residual'] or 0)
            if lv[y]['new_growth'] and abs(ng - printed) > 1:
                fail('FY%d: derived new growth %.0f, printed %.0f' % (y, ng, printed))
        ng_c += grown(ng, y)
        ov_c += grown(o, y)
    L = g(z, 'levy_limit')
    if abs(base + ng_c + ov_c - L) > 1:
        fail('the parts do not rebuild the FY%d levy limit' % z)
    rs = lambda y: g(y, 'residential_levy') / g(y, 'total_levy_by_class')
    parcels = H[z]['parcels'] / H[a]['parcels']
    rise = H[z]['bill'] / H[a]['bill']
    f = dict(cap=1.025 ** n,
             growth=(base + ng_c) / base / parcels,
             overrides=(base + ng_c + ov_c) / (base + ng_c),
             exclusions=(g(z, 'tax_levy') / L) / (g(a, 'tax_levy') / g(a, 'levy_limit')),
             homes=rs(z) / rs(a))
    rest = rise / math.prod(f.values())
    if abs(rest - 1) > 0.02:
        fail('the parts leave %.3f of the rise unexplained; the single-family part moved' % rest)
    f['rest'] = rest
    share = {k: math.log(v) / math.log(rise) * 100 for k, v in f.items()}
    gap = H[z]['bill'] - H[a]['bill']
    dollars = {k: round(gap * share[k] / 100) for k in f}
    dollars['rest'] += gap - sum(dollars.values())     # rounding goes to the rest, to the dollar
    return dict(first=a, last=z, factor=f, share=share, dollars=dollars, parcels=parcels,
                bill0=H[a]['bill'], bill1=H[z]['bill'], rs0=rs(a) * 100, rs1=rs(z) * 100,
                de1=g(z, 'debt_exclusion'), levy1=g(z, 'tax_levy'), lv=lv, ov=ov)


def build():
    rows, keys, tfiles = years_data()
    h = homes()
    won = overrides()
    xs = [C.fy(r['fy']) for r in rows]
    a, z = rows[0], rows[-1]
    r_exist = statistics.correlation([r['existing'] for r in rows], [r['rate_chg'] for r in rows])
    r_dev = statistics.correlation([r['dev'] for r in rows], [r['rate_chg'] for r in rows])
    if not (r_exist < -0.6 and abs(r_dev) < 0.3):
        fail('the finding no longer holds: existing %.2f, development %.2f' % (r_exist, r_dev))
    jump = max(rows, key=lambda r: r['existing'])
    med_dev = round(statistics.median(r['dev'] for r in rows), 2)   # a typical year's development
    drop = min(rows, key=lambda r: r['existing'])
    big_dev = max(rows, key=lambda r: r['dev'])
    in_window = {y: v for y, v in won.items() if a['fy'] <= y <= z['fy']}
    if not in_window:
        fail('no override won in the window; the page names them')
    ov_years = sorted(in_window)
    ov_last = ov_years[-1]
    ov = in_window[ov_last][0]
    by_fy = {r['fy']: r for r in rows}
    first_h, last_h = h['rows'][0], h['rows'][-1]

    P = lambda v, d=1: figure(v, '%s%%' % format(v, '.%df' % d), 'percent')
    R = lambda v: figure(v, '%.2f' % v, 'correlation')
    U = lambda v: figure(v, C.usd(v), 'dollars')
    FY = lambda y: figure(y, C.fy(y), 'fiscal year')
    rate = lambda v: '$%.2f' % v
    RT = lambda v: figure(v, rate(v), 'dollars per $1,000')

    b = burden(h)
    sh, dl, fc = b['share'], b['dollars'], b['factor']
    F0, F1 = C.fy(b['first']), C.fy(b['last'])
    PC = lambda k: P(round(sh[k]), 0)
    votes = round(sh['overrides'] + sh['exclusions'])

    # ------------------------------------------------------------ facts
    f = LD.fact
    facts = [
        f('bill0', U(b['bill0']), 'average single-family bill, %s' % F0, 'published', allow=(F0,)),
        f('bill1', U(b['bill1']), 'average single-family bill, %s' % F1, 'published', allow=(F1,)),
        f('p25', U(h['kept_pace']['p25']), 'the %s bill grown 2.5%% a year' % F0, 'estimate', allow=(F0, '2.5%')),
        f('s-cap', PC('cap'), 'of the rise: the 2.5% a year (ours)', 'estimate', allow=('2.5%',)),
        f('s-growth', PC('growth'), 'of the rise: new growth beyond the count of homes (ours)', 'estimate'),
        f('s-votes', P(votes, 0), 'of the rise: overrides and debt exclusions (ours)', 'estimate'),
        f('s-homes', PC('homes'), 'of the rise: the levy shifting onto homes (ours)', 'estimate'),
        f('rs', P(round(b['rs1'], 1)), 'homes’ share of the levy, %s' % F1, 'published', allow=(F1,)),
        f('rs0', P(round(b['rs0'], 1)), 'homes’ share of the levy, %s' % F0, 'published', allow=(F0,)),
        f('parcels', P(round((b['parcels'] - 1) * 100), 0), 'more single-family homes, %s–%s' % (F0, F1),
          'published', allow=(F0, F1)),
        f('r-exist', R(r_exist), 'rate against existing values, %s–%s (ours)'
          % (C.fy(a['fy']), C.fy(z['fy'])), 'estimate', allow=(C.fy(a['fy']), C.fy(z['fy']))),
        f('gap-ng', None, 'new growth split into new homes, additions and businesses', 'gap',
          closes='the assessors’ new growth detail by permit type, which the state’s files do not carry'),
    ]

    # ------------------------------------------------------------ conclusions
    con = TP.conclusion
    conclusions = [
        con('Overrides and debt exclusions were %s%% of the average bill’s rise since %s.' % (votes, F0),
            ['s-votes'], {'v': P(votes, 0)}, allow=(F0,),
            so='Most of what raised the bill needed no vote. Three overrides passed in those years.'),
        con('The 2.5%% a year, compounding, was %s%%: %s grown 2.5%% a year is %s.'
            % (round(sh['cap']), C.usd(b['bill0']), C.usd(h['kept_pace']['p25'])),
            ['s-cap', 'bill0', 'p25'], {'s': PC('cap'), 'a': U(b['bill0']), 'p': U(h['kept_pace']['p25'])},
            allow=('2.5%',),
            so='The limit lets the total grow every year without asking anyone.'),
        con('New growth outran the count of homes, %s%% of the rise; homes grew %s%%.'
            % (round(sh['growth']), round((b['parcels'] - 1) * 100)),
            ['s-growth', 'parcels'], {'s': PC('growth'), 'p': P(round((b['parcels'] - 1) * 100), 0)},
            so='No existing bill rises from it. The average does, because new and enlarged homes join it '
               '(our reading).'),
        con('Homes carry %s%% of the levy, against %s%% in %s: %s%% of the rise.'
            % ('%.1f' % b['rs1'], '%.1f' % b['rs0'], F0, round(sh['homes'])),
            ['rs', 'rs0', 's-homes'], {'a': P(round(b['rs1'], 1)), 'b': P(round(b['rs0'], 1)), 's': PC('homes')},
            allow=(F0,),
            so='When businesses are a smaller part of the town, homes pay more of the same total.'),
    ]

    # ------------------------------------------------------------ the signature: what raised the bill
    bridge = TP.bridge(
        'The average bill’s rise, by cause', ('%s bill' % F0, b['bill0']),
        [('The 2.5% a year', dl['cap']),
         ('New growth beyond more homes', dl['growth']),
         ('Overrides', dl['overrides']),
         ('Debt exclusions', dl['exclusions']),
         ('Levy shifting onto homes', dl['homes']),
         ('Other', dl['rest'])],
        ('%s bill' % F1, b['bill1']), '$', basis='estimate',
        note='Ours, from the state’s levy files: each cause’s share of the rise, not taken in sequence.')

    # ------------------------------------------------------------ the signature: three lines, one unit
    sig = TP.series(
        'Home values, development and the rate', xs,
        [TP.track('Existing property, change in value (ours)', [r['existing'] for r in rows], 'estimate'),
         TP.track('New development, share of the base', [r['dev'] for r in rows], 'published'),
         TP.track('Residential tax rate, change', [r['rate_chg'] for r in rows], 'published')],
        '%', kind='line', decimals=1,
        note='Town annual reports to %s, then the Division of Local Services. The rate mirrors the first '
             'line, not the second.' % C.fy(STATE_FROM - 1), note_allow=(C.fy(STATE_FROM - 1),))

    # ------------------------------------------------------------ development in dollars, with the rate
    # The rate is a rate per $1,000, not a percent; the secondary axis must be a different unit, so
    # it is drawn as the bill-to-value share instead, which IS the rate as a percent (see
    # build_historical_report.homes, asserted equal to the state's rate every year it prints one).
    share = {r['fy']: r['share'] for r in h['rows']}
    dev_chart = TP.series(
        'New growth and the tax rate', xs,
        [TP.track('New value certified as new growth', [r['new'] for r in rows], 'published', 'bar')],
        '$', kind='bar',
        secondary=dict(name='Tax rate, as a percent of value', values=[share[r['fy']] for r in rows],
                       unit='%', basis='published', decimals=2),
        note='Town reports, then the state: new growth by year, and the rate as a percent '
             '(a $14.39 rate is 1.44%).', note_allow=('$14.39', '1.44%'))

    # ------------------------------------------------------------ the homes and the bill, from the history page
    hx = [C.fy(r['fy']) for r in h['rows']]
    # THE HISTORICAL REPORT'S OWN CHART, as a custom block: two panels, actual against the first year
    # grown only with inflation, with a toggle to today's dollars and the COLA figure under the bill
    # (TJ, 2 November 2026). One component on both pages, from one set of figures (homes()).
    hdata = dict(first=h['first'], base=h['base'], kept_pace=h['kept_pace'],
                 value_growth=h['value_growth'], bill_growth=h['bill_growth'], jump=h['jump'], dip=h['dip'], bill_cagr=h['bill_cagr'], overrides=h['overrides'], exclusions=h['exclusions'],
                 rows=[{k: r[k] for k in ('fy', 'value', 'bill', 'value_cpi', 'bill_cpi', 'value_real',
                                          'bill_real', 'bill_p25', 'bill_p25_real', 'share', 'rate', 'rate_printed', 'parcels')}
                       for r in h['rows']])
    homes_block = TB.custom(
        'homes-against-inflation', 'Home value and tax bill against inflation', hdata, place='body',
        allow=(h['first'], h['base'], h['jump']['fy0'], h['jump']['fy1'], h['dip']['fy0'], h['dip']['fy1'])
        + tuple(o['fy'] for o in h['overrides']) + tuple(e['fy'] for e in h['exclusions']),
        alt='Two panels: the average single-family tax bill and home value, %s to %s, each beside its '
            '%s figure grown only with inflation.' % (h['first'], h['base'], h['first']),
        so=('The %s bill, %s, grown only with inflation would be %s today; the actual bill is %s.'
            % (h['first'], C.usd(h['kept_pace']['bill0']), C.usd(h['kept_pace']['bill']),
               C.usd(h['kept_pace']['actual'])),
            {'a': U(h['kept_pace']['bill0']), 'k': U(h['kept_pace']['bill']), 'n': U(h['kept_pace']['actual'])},
            (h['first'],)))

    # ------------------------------------------------------------ how it works (statute, a definition first)
    how = TB.explain('How the bill is set', [
        ('The town decides the total it raises in property tax, up to a limit that grows 2.5% a year '
         'plus the tax on new construction, plus any override or debt exclusion voters approve.',
         None, ('2.5%',)),
        'The tax rate is that total divided by the value of everything taxed.',
        'A bill is the home’s assessed value times the rate: its share of the town’s total. What the '
        'town raises sets the bill; what homes are worth only decides who pays which part of it.',
    ], place='lead', tone='define')

    # ------------------------------------------------------------ what changes a bill: the mechanism
    cr = TB.check_row
    changes = TB.checks('What changes an existing bill', ['Raises it', 'Needs a vote'], [
        cr(('The 2.5% a year', None, ('2.5%',)), ('The limit grows 2.5% every year, and a town may levy up to it.',
                               None, ('2.5%',)), {0}),
        cr('Overrides', ('Raise the limit for good, and every 2.5% after is figured on the higher total.', None, ('2.5%',)),
           {0, 1}),
        cr('Debt exclusions', 'Add a building’s debt payments to the levy until the debt is paid off.',
           {0, 1}),
        cr('Unused levy room', 'A town that levied below its limit can use the room without a vote.', {0}),
        cr('New growth', 'New homes and businesses are taxed at last year’s rate; they add to the total '
                         'without raising anyone else’s bill.', set(), contrast=True),
        cr('A business closing', 'The limit does not fall when property leaves or loses value, so '
                                 'everyone else pays its share.', {0}),
        cr('Your home gaining on others', 'Your share of the total rises with your home’s share of '
                                          'the town’s value.', {0}),
        cr('Values moving together', 'Rising or falling across town, the rate moves the other way; the '
                                     'total, and so the bill, does not.', set(), contrast=True),
    ], first='Change', second='How it works', tone='bad',
        so='Only overrides and exclusions need a vote. Most of what raises a bill does not.')

    gaps = TB.explain('What this page does not separate', [
        'New growth by kind: new homes, additions and renovations, and businesses. The state’s files '
        'print one figure.',
        'One home’s bill. The average bill moves when new and enlarged homes join the average, and a '
        'home whose value rose faster than the town’s pays a larger share.',
        'Our existing-value line also absorbs revaluation, abatements and class shifts, which the '
        'state’s files do not separate from market change.',
    ], place='end', tone='plain')

    # ------------------------------------------------------------ the levy, year by year
    lv, ovv = b['lv'], b['ov']
    m = lambda y, k: C.usd(float(lv[y][k])) if lv[y][k] else '—'
    lrows = []
    for y in range(b['last'], b['first'] - 1, -1):
        r = lv[y]
        lrows.append(dict(label=C.fy(y), cells=[
            m(y, 'levy_limit'), m(y, 'new_growth'), C.usd(float(ovv[y])) if y in ovv else '',
            m(y, 'debt_exclusion'), m(y, 'tax_levy'),
            '%.1f%%' % (float(r['residential_levy']) / float(r['total_levy_by_class']) * 100)]))

    def lview(key, rs):
        return dict(key=key, label='%s to %s' % (rs[-1]['label'], rs[0]['label']), total_col=None,
                    kinds=['ledger'] * 6,
                    columns=['Levy limit', 'New growth', 'Override', 'Debt exclusion', 'Tax levy',
                             'Homes’ share'],
                    rows=rs, note='The state’s levy files. A dash: the file left the year blank because '
                                  'its parts did not add up.', note_allow=())
    mid = len(lrows) // 2
    levy_table = dict(caption='The levy, by year', views=[lview('late', lrows[:mid]), lview('early', lrows[mid:])])

    # ------------------------------------------------------------ the table
    trows = []
    for r in reversed(rows):
        ovs = won.get(r['fy'], [])
        trows.append(dict(label=C.fy(r['fy']), cells=[
            '%.1f%%' % r['existing'], '%.2f%%' % r['dev'], C.usd(r['new']), rate(r['rate']),
            '%.1f%%' % r['rate_chg'], ('override, ' + C.usd(float(ovs[0]['amount']))) if ovs else '']))
    # Two periods, the town's reports and the state's files, because a table past thirty rows is
    # refused -- and the split falls where the source changes, so each tab has one source.
    def view(key, rs, src_note):
        return dict(
            key=key, label='%s to %s' % (rs[-1]['label'], rs[0]['label']), total_col=None,
            kinds=['estimate', 'ledger', 'ledger', 'ledger', 'ledger', 'stated'],
            columns=['Existing property, value change (ours)', 'Development, share of base', 'New growth value',
                     'Residential rate', 'Rate change', 'Override won'],
            rows=rs, note='Existing change is ours: total value less new growth, against last year’s total. '
                          + src_note[0], note_allow=src_note[1])
    cut = C.fy(STATE_FROM)
    later = [r for r in trows if r['label'] >= cut]
    earlier = [r for r in trows if r['label'] < cut]
    table = dict(caption='Values, development and the rate, by year', views=[
        view('state', later, ('Every other column is the state’s.', ())),
        view('town', earlier, ('Every other column is as the town’s annual reports print it.', ()))])

    # ------------------------------------------------------------ sources
    man = {r['key']: r for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    for k in keys.values():
        if k not in man:
            fail('%s is not in archive-manifest.csv' % k)
    sources = [
        dict(key='ng', label='Division of Local Services — new growth, all years', href='/docs/' + keys['ng']),
        dict(key='av', label='Division of Local Services — assessed values by class, all years',
             href='/docs/' + keys['av']),
        dict(key='tr', label='Division of Local Services — tax rates by class, all years', href='/docs/' + keys['tr']),
        dict(key='ov', label='Division of Local Services — override and underride votes',
             href='/docs/data/dls-override-votes.csv'),
    ] + [dict(key='h%d' % i, label=s['publisher'] + ' — ' + s['label'], href=s['docs_url'])
         for i, s in enumerate(h['sources'])]
    # The annual reports the earlier years are read from, and our extract of them.
    tk = []
    for i, fn in enumerate(sorted(tfiles)):
        key = 'town-annual-reports/docs/' + fn[:-4] + '.pdf'
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        yrs = sorted(tfiles[fn])
        sources.append(dict(key='t%d' % i, label='Town of Lunenburg — %s annual town report, Assessors '
                            '(FY%d–FY%d)' % (fn.split('-')[1], yrs[0], yrs[-1]), href='/docs/' + key))
        tk.append('t%d' % i)
    sources.append(dict(key='tx', label='Lunenburg Budget Project — report-new-growth-history.csv '
                        '(every figure, its edition, line and check)',
                        href='/docs/data/report-new-growth-history.csv'))
    tk.append('tx')
    sources.append(dict(key='lv', label='Division of Local Services — levy limits, exclusions and levies by '
                        'class, FY1986–FY2026, as extracted (each row names its state files)',
                        href='/docs/data/dls-levy-limits.csv'))
    hk = ['h%d' % i for i in range(len(h['sources']))]
    cite = TP.cite
    return TP.page(
        TID,
        'Overrides and debt exclusions were %s%% of the average bill’s rise since %s; the 2.5%% a year '
        'was %s%%.' % (votes, F0, round(sh['cap'])),
        facts, conclusions, chart=bridge, tables=[table, levy_table], sources=sources,
        also=[sig, dev_chart],
        finding_figures={'v': P(votes, 0), 'c': PC('cap')}, finding_allow=(F0, '2.5%'),
        blocks=[how, changes, homes_block, gaps],
        flow=['finding', cite(('chart', 0), 'lv', 'ov', *hk), cite(('block', 0), 'lv'),
              cite('ladder', 'lv', 'ov', *hk), cite(('block', 1), 'lv'), cite(('block', 2), *hk, 'ov', 'lv'),
              cite(('chart', 1), 'ng', 'av', 'tr', *tk), cite(('chart', 2), 'ng', *tk, *hk),
              cite(('block', 3), 'ng'), 'related',
              cite(('table', 1), 'lv', 'ov'), cite(('table', 0), 'ng', 'av', 'tr', 'ov', *tk), 'sources'])


def output():
    return json.dumps(build(), indent=1, ensure_ascii=False, sort_keys=True) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if REG.TOPICS.get(TID, (None, None, None))[2] != ME:
        fail('%s is not registered to %s in scripts/topic_registry/' % (TID, ME))
    text = output()
    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else None
        if cur != text:
            print('STALE %s' % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('%s: current' % TID)
        return 0
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, OUT)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
