#!/usr/bin/env python3
"""Growth and the tax rate: /homes-and-taxes/growth-and-tax-rate.

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

    # ------------------------------------------------------------ facts
    f = LD.fact
    facts = [
        f('r-exist', R(r_exist), 'rate against existing values, %s–%s (ours)'
          % (C.fy(a['fy']), C.fy(z['fy'])), 'estimate', allow=(C.fy(a['fy']), C.fy(z['fy']))),
        f('r-dev', R(r_dev), 'rate against development, same years (ours)', 'estimate'),
        f('cap', figure(2.5, '2.5%', 'a year'), 'growth in the levy limit the statute allows', 'statute'),
        f('jump-e', P(jump['existing']), 'existing values, %s, the biggest rise' % C.fy(jump['fy']),
          'estimate', {'y': FY(jump['fy'])}),
        f('jump-r', P(jump['rate_chg']), 'the rate the same year', 'published'),
        f('jump-d', P(jump['dev'], 2), 'added by development that year', 'published'),
        f('v-real', P(h['value_growth'], 0), 'average home value after inflation, %s–%s' % (h['first'], h['base']),
          'estimate', allow=(h['first'], h['base'])),
        f('b-real', P(h['bill_growth'], 0), 'average tax bill after inflation, same years', 'estimate'),
        f('ov', U(float(ov['amount'])), 'override won for %s, the latest' % C.fy(ov_last),
          'published', {'y': FY(ov_last)}),
        f('gap-de', None, 'debt exclusions, which also raise the rate', 'gap',
          closes='the Division of Local Services’ debt exclusion votes for Lunenburg, or the tax '
                 'recapitulation sheets, which list each excluded debt by year'),
    ]

    # ------------------------------------------------------------ conclusions
    con = TP.conclusion
    conclusions = [
        con('The rate tracked existing home values (%.2f), not development (%.2f).' % (r_exist, r_dev),
            ['r-exist', 'r-dev'], {'a': R(r_exist), 'b': R(r_dev)},
            so='Building more does not lower the rate on its own. When existing homes gain value, the '
               'rate falls; when they lose it, the rate climbs.'),
        con('In %s existing values rose %s and the rate fell %s; development added %s.'
            % (C.fy(jump['fy']), '%.1f%%' % jump['existing'], '%.1f%%' % abs(jump['rate_chg']),
               '%.2f%%' % jump['dev']),
            ['jump-e', 'jump-r', 'jump-d'],
            {'y': FY(jump['fy']), 'e': P(jump['existing']), 'r': P(abs(jump['rate_chg'])), 'd': P(jump['dev'], 2)},
            so='Development that year was %s of the base, against %s in a typical year; the fall in '
               'the rate tracks the %s rise in existing values.'
               % ('%.2f%%' % jump['dev'], '%.2f%%' % med_dev, '%.1f%%' % jump['existing']),
            so_figures={'d': P(jump['dev'], 2), 'm': P(med_dev, 2), 'e': P(jump['existing'])}),
        con('New growth pays at last year’s rate and adds to the limit beyond %s.' % '2.5%',
            ['cap'], {'c': figure(2.5, '2.5%')},
            so='What development buys is revenue for the town without raising existing bills. That is '
               'its case, and it is a real one; a lower rate is not.'),
        con('After inflation the average home rose %s%% and the average bill %s%%.'
            % (h['value_growth'], h['bill_growth']), ['v-real', 'b-real'],
            {'v': P(h['value_growth'], 0), 'b': P(h['bill_growth'], 0)},
            so='A falling rate has not meant a falling bill. The %s bill, grown only with inflation, '
           'would be %s today; the actual bill is %s.'
           % (h['first'], C.usd(h['kept_pace']['bill']), C.usd(h['kept_pace']['actual'])),
        so_figures={'k': U(h['kept_pace']['bill']), 'n': U(h['kept_pace']['actual'])}, so_allow=(h['first'],)),
    ]

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
                 value_growth=h['value_growth'], bill_growth=h['bill_growth'], jump=h['jump'], dip=h['dip'], bill_cagr=h['bill_cagr'], overrides=h['overrides'],
                 rows=[{k: r[k] for k in ('fy', 'value', 'bill', 'value_cpi', 'bill_cpi', 'value_real',
                                          'bill_real', 'bill_p25', 'bill_p25_real', 'share', 'rate', 'rate_printed', 'parcels')}
                       for r in h['rows']])
    homes_block = TB.custom(
        'homes-against-inflation', 'Home value and tax bill against inflation', hdata, place='body',
        allow=(h['first'], h['base'], h['jump']['fy0'], h['jump']['fy1'], h['dip']['fy0'], h['dip']['fy1'])
        + tuple(o['fy'] for o in h['overrides']),
        alt='Two panels: the average single-family tax bill and home value, %s to %s, each beside its '
            '%s figure grown only with inflation.' % (h['first'], h['base'], h['first']),
        so=('The %s bill, %s, grown only with inflation would be %s today; the actual bill is %s.'
            % (h['first'], C.usd(h['kept_pace']['bill0']), C.usd(h['kept_pace']['bill']),
               C.usd(h['kept_pace']['actual'])),
            {'a': U(h['kept_pace']['bill0']), 'k': U(h['kept_pace']['bill']), 'n': U(h['kept_pace']['actual'])},
            (h['first'],)))

    # ------------------------------------------------------------ how it works (statute, a definition first)
    how = TB.explain('Why the rate moves the way it does', [
        ('The town may raise its property tax levy by 2.5% a year (Proposition 2½), plus the tax on '
         'new construction, plus anything voters add by override or debt exclusion.', None, ('2.5%', '2½')),
        'New construction is taxed at the previous year’s rate, and that tax is added to the limit. '
        'It adds value and levy together, so on its own it leaves the rate about where it was.',
        'The rate is the levy divided by the value of everything taxed. When existing property gains '
        'value faster than the levy grows, the same levy is spread thinner and the rate falls.',
    ], place='lead', tone='define')

    gaps = TB.explain('What this page does not separate', [
        'Debt exclusions, which raise the levy outside the limit. The state’s vote file used here '
        'carries overrides only.',
        ('Overrides passed for %s. Each raises the levy, and so the rate, in its year; the table '
         'marks them.' % ', '.join(C.fy(y) for y in ov_years), None, tuple(C.fy(y) for y in ov_years)),
        'Our existing-value line also absorbs revaluation, abatements and class shifts, which the '
        'state’s files do not separate from market change.',
    ], place='end', tone='plain')

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
    hk = ['h%d' % i for i in range(len(h['sources']))]
    cite = TP.cite
    return TP.page(
        TID,
        'The tax rate followed what existing homes were worth (%.2f), not how much was built (%.2f).'
        % (r_exist, r_dev),
        facts, conclusions, chart=sig, table=table, sources=sources,
        also=[dev_chart],
        finding_figures={'a': R(r_exist), 'b': R(r_dev)},
        blocks=[how, homes_block, gaps],
        flow=['finding', cite(('chart', 0), 'ng', 'av', 'tr', *tk), cite(('block', 0), 'tr'), cite('ladder', 'ng', 'av', 'tr', *tk, *hk),
              cite(('chart', 1), 'ng', *tk, *hk), cite(('block', 1), *hk), cite(('block', 2), 'ov'), 'related',
              cite(('table', 0), 'ng', 'av', 'tr', 'ov', *tk), 'sources'])


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
