#!/usr/bin/env python3
"""THE TWO-YEAR SURPLUS: FY2025 and FY2026 together, by category and by line.

    python3.11 scripts/build_two_year_surplus.py           # write fy28/public/data/topics/two-year-surplus.json
    python3.11 scripts/build_two_year_surplus.py --check   # fail if it would change

    two-year-surplus   /fy2026-closeout/two-year-surplus   Two-year surplus

TJ, 26 November 2026: "generate another page.... surplus analysis, which looks at the COMBINED
surpluses from FY25 and FY26, totalling in all cateogires, to say what lines have the most unspent
amounts."

ONE FOOTING FOR BOTH YEARS. FY2025's closed report leaves out the orders it still owed at its
close ($72,171.70, re-opened in FY2026 as carried-forward budget); FY2026's report counts its open
orders as spent. So FY2025 is counted the way FY2026 is -- each account's period-13 leftover less
the orders closed out of it (the journal's YEC lines) -- the same footing Surplus by year and the
hub use. The two years then sum to $554,945.16 + $482,118.07, asserted below.

WHAT IS OURS: the categories (each account placed by its DESE function and object code,
build_journal_surplus_topics.cat_of), the two-year sums, and the $50,000 bar for naming a
category's overrun (the hub's 'heavily' bar). Every figure is the ledger's. No cause is stated.
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
import journal as J  # noqa: E402
import build_journal_surplus_topics as JS  # noqa: E402
import build_fy2026_closeout_topics as CT  # noqa: E402

ID = 'two-year-surplus'
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % ID)
PAY = os.path.join(ROOT, 'fy28', 'public', 'data', 'fy%d-school-surplus.json')
YEARS = (2025, 2026)
BIG = 50000          # a category's two-year overrun is named at this size (the hub's bar)
TOP = 10             # lines in the "most left" sum
D0 = Decimal(0)
# Categories with a page of their own on this shelf.
PAGE_OF = {'paras': 'fy2026-paraprofessional-overrun', 'counselors': 'fy2026-psychologist-line',
           'tuition': 'fy2026-tuition-lines', 'transport': 'special-education-transportation'}


def fail(msg):
    sys.exit('build_two_year_surplus: ' + msg)


def fl(x):
    return float(round(Decimal(x), 2))


def near(a, b, tol=0.005):
    return abs(float(a) - float(b)) <= tol


def data():
    d = JS.data()
    A = J.accounts()
    scope = [r for r in J.lines() if J.in_surplus_scope(A[r['account']])]
    # Orders owed at the FY2025 close, by account and by category: the journal's YEC lines.
    yec_a, yec_c = defaultdict(lambda: D0), defaultdict(lambda: D0)
    for r in scope:
        if r['source'] == 'YEC' and r['fy'] == 2025:
            yec_a[r['account']] -= r['amt']
            yec_c[JS.cat_of(r)] -= r['amt']
    if sum(yec_a.values()) != d['closed'][2025]:
        fail('the orders closed out of FY2025, by account, no longer sum to the carry-forward')
    owed = {2025: d['left'][2025] - d['closed'][2025], 2026: d['left'][2026]}

    acct = defaultdict(lambda: {y: D0 for y in YEARS})
    acat = {}
    for (y, c, a), v in d['acct_left'].items():
        if y in YEARS:
            acct[a][y] += v - (yec_a.get(a, D0) if y == 2025 else D0)
            acat[a] = c
    cat = defaultdict(lambda: {y: D0 for y in YEARS})
    for (y, c), v in d['cat_left'].items():
        if y in YEARS:
            cat[c][y] += v - (yec_c.get(c, D0) if y == 2025 else D0)
    for y in YEARS:
        if sum(v[y] for v in acct.values()) != owed[y] or sum(v[y] for v in cat.values()) != owed[y]:
            fail('FY%d accounts or categories no longer sum to what was left, same footing' % y)
    total = owed[2025] + owed[2026]
    hub = json.load(open(os.path.join(ROOT, 'fy28', 'public', 'data', 'topics',
                                      'fy2026-closeout.json'), encoding='utf-8'))
    hub_text = json.dumps(hub, ensure_ascii=False)
    for y in YEARS:
        if C.usd(fl(owed[y])) not in hub_text:
            fail('the hub no longer states FY%d as %s' % (y, C.usd(fl(owed[y]))))

    # Labels and budgets, per category, from the two years' surplus payloads.
    label, budget = {}, defaultdict(float)
    for y in YEARS:
        for c in json.load(open(PAY % (y % 100), encoding='utf-8'))['causes']['categories']:
            label[c['key']] = c['label']
            budget[c['key']] += c['revised']
    if set(cat) - set(label):
        fail('a category in the journal has no label in the surplus payloads')
    cats = [dict(key=k, label=label[k], y25=fl(v[2025]), y26=fl(v[2026]),
                 both=fl(v[2025] + v[2026]), budget=round(budget[k], 2))
            for k, v in cat.items() if v[2025] or v[2026]]
    cats.sort(key=lambda c: -c['both'])
    lines = [dict(account=a, desc=d['acct_desc'][a], cat=acat[a], y25=fl(v[2025]),
                  y26=fl(v[2026]), both=fl(v[2025] + v[2026])) for a, v in acct.items()]
    lines.sort(key=lambda r: -r['both'])
    import build_fy2026_school_surplus as SP
    early = fl(SP.data()['early'])
    return dict(early=early, total=fl(total), owed={y: fl(owed[y]) for y in YEARS}, cats=cats, lines=lines,
                closed25=fl(d['closed'][2025]))


def sources():
    s = CT.sources()
    out = [dict(s['p13-26'], key='p13-26'), dict(s['p13-25'], key='p13-25'),
           dict(s['d-munis'], key='d-munis')]
    out += [dict(x, key=k) for x, k in zip(JS.sources(), ('journal', 'accounts', 'provenance'))]
    return out


def page(f):
    U = lambda v: C.usd(v)
    UF = lambda v: figure(v, C.usd(v))
    F = lambda y: figure(y, C.fy(y), 'fiscal year')
    P = lambda v, dp=0: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    fact, con = LD.fact, TP.conclusion
    total, cats, lines = f['total'], f['cats'], f['lines']
    by = {c['key']: c for c in cats}
    if not near(total, f['owed'][2025] + f['owed'][2026]):
        fail('the two years no longer sum')

    # Tuition: the two lines, by account.
    priv = next(r for r in lines if r['desc'] == 'SPED TUITIONS-PRIVATE')
    coll = next(r for r in lines if r['desc'] == 'COLLABORATIVE TUITIONS')
    if lines[0] is not priv or lines[-1] is not coll:
        fail('the page says private tuition left the most and collaborative went furthest over')
    if not near(priv['both'] + coll['both'], by['tuition']['both']):
        fail('private and collaborative no longer make up the tuition category')
    priv_share = 100 * priv['both'] / total

    # Outside tuition: the two largest leftovers, and the teachers' share for comparison.
    rest = [c for c in cats if c['key'] != 'tuition']
    a1, a2 = rest[0], rest[1]
    if (a1['key'], a2['key']) != ('buildings', 'counselors'):
        fail('the page names upkeep and counselors as the largest leftovers outside tuition')
    pct = lambda c: 100 * c['both'] / c['budget']
    tch = by['teachers']
    if not pct(a1) > 10 * pct(tch):
        fail('the page says upkeep left a far larger share of its budget than teachers')

    # Categories past budget over the two years, at the hub's bar.
    big_over = [c for c in cats if c['both'] <= -BIG]
    if [c['key'] for c in sorted(big_over, key=lambda c: c['both'])] != ['sped_services', 'paras',
                                                                         'transport']:
        fail('the page names paras, special-ed services and transportation as the overruns')
    over_sum = round(sum(c['both'] for c in big_over), 2)
    if not all(c['y25'] > 0 > c['y26'] for c in big_over):
        fail('the page says each overrun left money in FY2025 and went over in FY2026')

    # Lines: under against over, and the ten that left most.
    under = round(sum(r['both'] for r in lines if r['both'] > 0), 2)
    over = round(-sum(r['both'] for r in lines if r['both'] < 0), 2)
    if not near(under - over, total):
        fail('lines under and over no longer net to the two-year surplus')
    top = round(sum(r['both'] for r in lines[:TOP]), 2)
    if not top > total:
        fail('the page says the ten lines that left most left more than the whole surplus')
    n_under = sum(1 for r in lines if r['both'] > 0)
    n_over = sum(1 for r in lines if r['both'] < 0)

    facts = [
        fact('total', UF(total), 'left unspent, %s and %s together (our sum)'
             % (C.fy(2025), C.fy(2026)), 'published', {'a': F(2025), 'b': F(2026)}),
        fact('priv', UF(priv['both']), 'left on private tuition, two years', 'published'),
        fact('coll', UF(-coll['both']), 'collaborative tuition past budget, two years',
             'published'),
        fact('bldg', UF(a1['both']), 'left on building & grounds upkeep', 'published'),
        fact('cnsl', UF(a2['both']), 'left on counselors & psychologists', 'published'),
        fact('tch', UF(tch['both']), 'left on teachers & substitutes', 'published'),
        fact('ovr', UF(-over_sum), 'past budget, the three largest overruns', 'published'),
        fact('under', UF(under), 'left on %s lines that came in under' % C.num(n_under),
             'published', {'n': N(n_under)}),
        fact('over', UF(over), 'spent past budget on %s lines' % C.num(n_over), 'published',
             {'n': N(n_over)}),
        fact('top', UF(top), 'left on the %s lines that left most' % C.num(TOP), 'published',
             {'n': N(TOP)}),
    ]
    conclusions = [
        con('Private tuition left %s over the two years; collaborative ran %s past its budget.'
            % (U(priv['both']), U(-coll['both'])), ['priv', 'coll', 'total'],
            {'p': UF(priv['both']), 'c': UF(-coll['both'])},
            so='Net, the two left %s; private tuition alone is %s of the two-year total.'
               % (U(by['tuition']['both']), C.pct(priv_share, 0)),
            so_figures={'t': UF(by['tuition']['both']), 's': P(priv_share)}),
        con('Building upkeep left %s and counselors & psychologists %s, the most outside tuition.'
            % (U(a1['both']), U(a2['both'])), ['bldg', 'cnsl', 'tch'],
            {'a': UF(a1['both']), 'b': UF(a2['both'])},
            so='Upkeep left %s of its two years’ budget; teachers left %s, %s of theirs.'
               % (C.pct(pct(a1), 1), U(tch['both']), C.pct(pct(tch), 1)),
            so_figures={'u': P(pct(a1), 1), 't': UF(tch['both']), 'p': P(pct(tch), 1)}),
        con('Paraprofessionals, special-ed contracted services and transportation ran %s past budget.'
            % U(-over_sum), ['ovr'], {'o': UF(-over_sum)},
            so='Each left money in %s and went over in %s.' % (C.fy(2025), C.fy(2026)),
            so_figures={'a': F(2025), 'b': F(2026)}),
        con('Lines under budget left %s over the two years; lines past budget used %s of it.'
            % (U(under), U(over)), ['under', 'over', 'top'], {'u': UF(under), 'o': UF(over)},
            so='The %s lines that left most left %s, more than the two-year surplus.'
               % (C.num(TOP), U(top)), so_figures={'n': N(TOP), 't': UF(top)}),
    ]

    hrefs = {by[k]['label']: REG.path(t) for k, t in PAGE_OF.items() if k in by}
    chart = TP.ranking(
        'Left unspent over two years, by category',
        [(c['label'], c['both']) for c in cats], '$', hrefs=hrefs,
        note='%s and %s added, school general fund. %s counts orders owed at its close as spent, '
             'as %s does. Below zero is past budget.'
             % (C.fy(2025), C.fy(2026), C.fy(2025), C.fy(2026)),
        note_figures={'a': F(2025), 'b': F(2026)})

    cat_table = dict(
        caption='Left unspent by category, each year and together',
        views=[dict(
            key='categories', label='School general fund, period 13', total_col=2,
            kinds=['ledger', 'ledger', 'estimate', 'estimate'],
            columns=[C.fy(2025), C.fy(2026), 'Two years', 'Share of two years’ budget'],
            rows=[dict(label=c['label'], cells=[C.usd(c['y25']), C.usd(c['y26']), C.usd(c['both']),
                                               C.pct(pct(c), 1) if c['budget'] else '—'])
                  for c in cats]
            + [dict(label='All categories', cells=[
                C.usd(f['owed'][2025]), C.usd(f['owed'][2026]), C.usd(total), '—'])],
            note='Categories are ours, each account placed by its DESE function and object code. '
                 '%s is the closed year less the %s of orders it still owed at the close, which '
                 '%s paid from carried-forward budget.'
                 % (C.fy(2025), C.usd(f['closed25']), C.fy(2026)))])

    def line_row(r):
        return dict(label=r['desc'],
                    cells=[C.usd(r['y25']), C.usd(r['y26']), C.usd(r['both'])])
    lines_table = dict(
        caption='The lines that left the most, and the ones furthest past budget',
        views=[
            dict(key='most', label='Left the most', total_col=2, kinds=['ledger', 'ledger', 'estimate'],
                 columns=[C.fy(2025), C.fy(2026), 'Two years'],
                 rows=[line_row(r) for r in lines[:15]],
                 note='One row an account, named as the ledger prints it. A name can repeat: each school has its own account.'),
            dict(key='past', label='Furthest past budget', total_col=2,
                 kinds=['ledger', 'ledger', 'estimate'],
                 columns=[C.fy(2025), C.fy(2026), 'Two years'],
                 rows=[line_row(r) for r in lines[::-1][:10]],
                 note='Collaborative tuition includes the %s of %s invoices charged on 30 June.'
                      % (C.usd(f['early']), C.fy(2027)))])

    cite = TP.cite
    flow = [
        'finding',
        cite(('chart', 0), 'p13-26', 'p13-25', 'journal', 'd-munis'),
        ('conclusion', 1), ('conclusion', 2),
        cite(('table', 0), 'p13-26', 'p13-25', 'journal', 'accounts'),
        cite(('table', 1), 'p13-26', 'p13-25', 'journal', 'accounts', 'provenance'),
        ('conclusion', 0), ('conclusion', 3),
        'sources',
    ]
    return TP.page(
        ID,
        '%s and %s together left %s; private tuition alone left %s of it.'
        % (C.fy(2025), C.fy(2026), U(total), U(priv['both'])),
        facts, conclusions, chart=chart, table=cat_table, tables=[lines_table],
        sources=sources(), flow=flow,
        finding_figures={'a': F(2025), 'b': F(2026), 't': UF(total), 'p': UF(priv['both'])})


def render(f=None):
    p = page(f or data())
    p['not_established'] = [
        'Why any line came in under or over budget, in either year.',
        'Whether a line under budget in both years was budgeted above what it needed, or held '
        'spending back.',
    ]
    return json.dumps(p, indent=1, ensure_ascii=False, sort_keys=True) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text = render()
    if a.check:
        if not os.path.exists(OUT) or open(OUT, encoding='utf-8').read() != text:
            print('STALE %s' % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('two-year surplus: current')
        return 0
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    os.replace(tmp, OUT)
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
