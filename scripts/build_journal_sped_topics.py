#!/usr/bin/env python3
"""Special education in the school MUNIS journal: who is paid. One topic page.

    python3 scripts/build_journal_sped_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_journal_sped_topics.py --check   # fail if either output would change

    sped-providers   /special-education/sped-providers   Special education providers

On the special education shelf, in the group "Who is paid, and from where"
(scripts/topic_registry/special_education.py; notes/plans/MUNIS-JOURNAL-REPORTS.md, Hub A).
/special-education/sped-all-funds was written here until 23 October 2026; it is now the
vote beside every fund, written by build_school_all_funds.py, which holds the budget.

WHAT THEY READ. Only `scripts/journal.py`: the loader, THE special education account list
(the one the extractor's redaction uses), its components and fund groups, and the payee rule.
Nothing here re-decides any of those; a second copy would be a defect.

WHAT A FIGURE IS. An ACTUAL posted to a special education expense account in the school
journal, FY2023 to FY2026, net of every reversal and reclassification posted in the run
(rule 11: a posting is what the school ledger recorded, not what a thing costs). School
psychologists are on the list and outside the total, by our choice (journal.COMPONENTS).
FY2026's close is not posted in this run, so every FY2026 figure can still move.

RULE 1. Nothing here feeds the model. The one comparison with a rate -- the general fund's
annual growth against the levy limit's 2.5% -- is a comparison, not a projection.

RULE 7. Postings are facts. Why a fund paid less, or why a provider was paid more, is not in a
ledger, and each page says so beside the figure, with the document that would settle it.

THE REDACTION (notes/plans/MUNIS-JOURNAL-REPORTS.md). Providers are named; recipients are
not. A masked payee -- a family or a child -- appears only inside a four-year aggregate across
every special education account, and no provider table is complete enough for a masked
amount to fall out of it by subtraction: the provider table stops at the largest twelve, so
what is left over mixes over a hundred named payees with the masked ones.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
from brief import step  # noqa: E402
import journal as J  # noqa: E402

OUT_DIR = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics')
ME = os.path.basename(__file__)
MINE = sorted(t for t, (_, _, gen) in REG.TOPICS.items() if gen == ME)
# What the town's own minutes say about Keystone's rates, quoted verbatim and checked against our
# copy on every build (`keystone_quote`). Searched 19 October 2026: `search_minutes.py keystone`
# finds School Committee agenda items from 2022 to 2025 ("Keystone Collaborative Update",
# "Keystone Report", "Keystone Collaborative-Property Acquisition" on 2023-06-07, for which no
# minutes are held) whose minutes only accept a report; this is the one minute that states a
# figure about Keystone's money.
KEYSTONE_MINUTES = '/docs/minutes/text/finance-committee/2024-03-14-minutes-6469.txt'
KEYSTONE_RATES = ('There is a discussion about Keystone Education Collaborative program and the '
                  'rates being raised almost 11%. Dave Passion questions how the 14% increase was '
                  'absorbed last year.')
KEYSTONE_CENSUS = '/docs/district-budget/docs/sc-meetings/2024-2025-keystone-collaborative-update.pdf'
LEVY = 2.5            # Proposition 2½: the most the levy may rise in a year (statute)
TOP_RANK = 10         # providers drawn in the signature
TOP_TABLE = 12        # providers in the table; never every payee (see the docstring)
FUNDS_DRAWN = ('General fund', 'Circuit breaker', 'IDEA grants', 'Other special education grants')
OUTSIDE = FUNDS_DRAWN[1:]
F0, F1 = J.YEARS[0], J.YEARS[-1]

BENEFITS_CLOSES = ('the district’s End of Year Financial Report, special education program, '
                   'with benefits and town-side costs by program')


def fail(msg):
    raise SystemExit('build_journal_sped_topics: ' + msg)


def sources():
    return [
        dict(label='Lunenburg Budget Project — munis-school-journal.csv (every school journal '
                   'line, FY2023–FY2026, our redacted reading of the Town’s Report 1)',
             href=J.PUBLIC['journal']),
        dict(label='Lunenburg Budget Project — munis-school-journal-accounts.csv (every '
                   'school account, with the FY2026 figures the report prints)',
             href=J.PUBLIC['accounts']),
        dict(label='Town of Lunenburg — how the journal reached us, and what was redacted',
             href='/docs/town-ledgers/account-details/'
                  'PROVENANCE-fy2023-fy2026-p13-school-journal.md'),
    ]


def times(r):
    return '%.1f times' % r


def money(x):
    return float(x)


def data():
    """Every figure both pages use, from journal.py alone."""
    A = J.accounts()
    L = J.sped_actuals()
    fund = lambda r: J.sped_fund(A[r['account']])
    comp = lambda r: J.component(A[r['account']])
    byf = J.rollup(L, 'fy', fund)
    for (_, f) in byf:
        if f not in FUNDS_DRAWN:
            fail('fund group %r posted special education actuals and is not drawn' % f)
    d = {}
    d['fund'] = {(y, f): money(byf.get((y, f), 0)) for y in J.YEARS for f in FUNDS_DRAWN}
    d['total'] = {y: sum(d['fund'][(y, f)] for f in FUNDS_DRAWN) for y in J.YEARS}
    d['gf'] = {y: d['fund'][(y, 'General fund')] for y in J.YEARS}
    d['other'] = {y: d['total'][y] - d['gf'][y] for y in J.YEARS}
    d['out_share'] = {y: 100.0 * d['other'][y] / d['total'][y] for y in J.YEARS}
    byc = J.rollup(L, 'fy', comp)
    d['comp'] = {(y, c): money(byc.get((y, c), 0)) for y in J.YEARS for c in J.IN_TOTAL}
    psy = J.rollup([r for r in J.sped_actuals(True) if comp(r) == 'psychologists'], 'fy')
    d['psy'] = {y: money(psy.get((y,), 0)) for y in J.YEARS}
    # The circuit breaker in the open year: what produced its actuals.
    cb = [r for r in L if r['fy'] == F1 and fund(r) == 'Circuit breaker']
    d['cb_kind'] = {k: money(v) for (k,), v in
                    J.rollup(cb, lambda r: J.KIND_OF[r['source']]).items()}
    reclass = [r for r in cb if J.KIND_OF[r['source']] == 'journal entry']
    if len(reclass) != 1:
        fail('the FY2026 circuit breaker was expected to post by one journal entry; it has %d'
             % len(reclass))
    d['cb_reclass'] = money(reclass[0]['amt'])
    d['cb_reclass_desc'] = reclass[0]['description']
    # The open purchase orders on these accounts when the report was run -- the FY2026 figures
    # the accounts file prints, read by the account rather than summed from lines.
    d['open'] = sum(float(a['encumbrances']) for a in A.values() if J.in_sped_total(a))

    # ---- payees: invoice lines only (pay runs and journal entries name nobody)
    inv = [r for r in L if J.KIND_OF[r['source']] == 'invoice']
    d['vend'] = {y: money(v) for (y,), v in J.rollup(inv, 'fy').items()}
    masked = [r for r in inv if J.payee(r) is J.MASKED]
    shown = [r for r in inv if J.payee(r) not in (None, J.MASKED)]
    if len(masked) + len(shown) != len(inv):
        fail('an invoice line has no payee at all')
    d['masked'] = money(sum(r['amt'] for r in masked))
    d['masked_lines'] = len(masked)
    d['masked_transport'] = money(sum(r['amt'] for r in masked if comp(r) == 'transport'))
    tot = {k: money(v) for (k,), v in J.rollup(shown, J.payee).items()}
    d['payees'] = len(tot)
    order = sorted(tot, key=lambda k: (-tot[k], k))
    d['order'] = order
    d['ptotal'] = tot
    d['pyear'] = {(k, y): money(v) for (k, y), v in J.rollup(shown, J.payee, 'fy').items()}
    d['pfund'] = {(k, f): money(v) for (k, f), v in J.rollup(shown, J.payee, fund).items()}
    d['pcomp'] = {(k, y, c): money(v)
                  for (k, y, c), v in J.rollup(shown, J.payee, 'fy', comp).items()}
    d['vend_all'] = sum(d['vend'].values())
    if abs(d['vend_all'] - d['masked'] - sum(tot.values())) > 0.005:
        fail('named plus masked payments do not foot to every invoice')
    return d


def keystone_quote():
    src = os.path.join(ROOT, 'sources', 'meetings', 'text',
                       KEYSTONE_MINUTES.split('/docs/minutes/text/')[1])
    if KEYSTONE_RATES not in ' '.join(open(src, encoding='utf-8').read().split()):
        fail('the Keystone quotation is no longer verbatim in %s' % KEYSTONE_MINUTES)


def build():
    keystone_quote()
    d = data()
    U = lambda v: figure(v, C.usd(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    f, con = LD.fact, TP.conclusion
    out = {}
    pc = lambda a, b: 100.0 * (b - a) / a
    cagr = lambda a, b, n: 100.0 * ((b / a) ** (1.0 / n) - 1)
    yrs = len(J.YEARS) - 1

    # ================================================== sped-providers
    o = d['order']
    top3 = o[:3]
    va = d['vend_all']
    s3 = 100.0 * sum(d['ptotal'][k] for k in top3) / va
    s10 = 100.0 * sum(d['ptotal'][k] for k in o[:TOP_RANK]) / va
    lead = o[0]
    l0, l1 = d['pyear'].get((lead, F0), 0.0), d['pyear'].get((lead, F1), 0.0)
    lt0 = d['pcomp'].get((lead, F0, 'tuition'), 0.0)
    lt1 = d['pcomp'].get((lead, F1, 'tuition'), 0.0)
    v0, v1 = d['vend'][F0], d['vend'][F1]
    carrier = next(k for k in o if d['pcomp'].get((k, F1, 'transport'), 0.0) > 0)
    c25, c26 = d['pyear'].get((carrier, F1 - 1), 0.0), d['pyear'].get((carrier, F1), 0.0)
    c23 = d['pyear'].get((carrier, F0), 0.0)
    if not (l1 > l0 > 0 and c26 > c25 > 0):
        fail('the provider conclusions assume both payments rose; the data no longer says so')
    if d['masked_transport'] / d['masked'] < 0.5:
        fail('the masked aggregate is no longer mostly family transport; relabel it')
    names = lambda ks: ', '.join(ks[:-1]) + ' and ' + ks[-1]
    px = {}
    px['vend'] = f('vend', U(va), 'paid to vendors for special education, %s'
                   % C.fyspan(F0, F1), 'published',
                   {'y': figure(F0, C.fyspan(F0, F1), 'fiscal years')})
    px['top3'] = f('top3', P(s3), 'of it to the three largest payees', 'published')
    px['payees'] = f('payees', N(d['payees'], 'payees'), 'payees named in those years',
                     'published')
    px['top10'] = f('top10', P(s10), 'of it to the ten largest', 'published')
    px['l0'] = f('l0', U(l0), 'to FLLAC (Keystone), %s' % C.fy(F0), 'published', {'y': F(F0)})
    px['l1'] = f('l1', U(l1), 'to FLLAC (Keystone), %s' % C.fy(F1), 'published', {'y': F(F1)})
    px['v0'] = f('v0', U(v0), 'to every vendor, %s' % C.fy(F0), 'published', {'y': F(F0)})
    px['v1'] = f('v1', U(v1), 'to every vendor, %s, not yet closed' % C.fy(F1), 'published',
                 {'y': F(F1)})
    px['c25'] = f('c25', U(c25), 'to Van Pool, %s' % C.fy(F1 - 1), 'published', {'y': F(F1 - 1)})
    px['c26'] = f('c26', U(c26), 'to Van Pool, %s' % C.fy(F1), 'published', {'y': F(F1)})
    px['masked'] = f('masked', U(d['masked']), 'to families, not named, four years, mostly '
                     'mileage', 'published')
    px['price'] = f('price', None, 'what any one child’s services cost', 'gap',
                    closes='the district’s placement-level billing detail, gross of the circuit '
                           'breaker')
    if lead != 'FLLAC (KEYSTONE)' or carrier != 'VAN POOL':
        fail('the labels name FLLAC and Van Pool; the largest payees are now %r and %r'
             % (lead, carrier))
    stack = [fn for fn in FUNDS_DRAWN if any(d['pfund'].get((k, fn)) for k in o[:TOP_RANK])]
    rank_rows = [(k, [d['pfund'].get((k, fn), 0.0) for fn in stack]) for k in o[:TOP_RANK]]
    top5 = o[:5]
    prov_rows = [dict(label=k, cells=[C.usd(d['pyear'].get((k, y), 0.0)) for y in J.YEARS])
                 for k in o[:TOP_TABLE]]
    out['sped-providers'] = TP.page(
        'sped-providers',
        'Three payees took %s of special education vendor payments; Keystone was paid %s as '
        'much by %s.' % (C.pct(s3), times(l1 / l0), C.fy(F1)),
        list(px.values()),
        [con('The ten largest of %s named payees took %s of the %s paid to vendors in four years.'
             % (C.num(d['payees']), C.pct(s10), C.usd(va)),
             ['vend', 'top3', 'top10', 'payees', 'masked', 'price'],
             {'n': N(d['payees'], 'payees'), 'a': P(s10), 'b': U(va)},
             notes=[step('A payment says who was paid, not for which child or how many, so no '
                         'figure here is a price.', 'gap',
                         closes='the district’s placement-level billing detail, gross of the '
                                'circuit breaker')]),
         con('FLLAC (Keystone) was paid %s in %s and %s in %s; all vendors rose %s.'
             % (C.usd(l0), C.fy(F0), C.usd(l1), C.fy(F1), C.pct(pc(v0, v1))),
             ['l0', 'l1', 'v0', 'v1'],
             {'a': U(l0), 'y': F(F0), 'b': U(l1), 'z': F(F1), 'p': P(pc(v0, v1))},
             allow=('FLLAC',),
             notes=[step('Most of the rise is on the tuition accounts: %s in %s, %s in %s. '
                         'Whether that is more children, longer placements or higher rates is '
                         'not in the ledger.'
                         % (C.usd(lt0), C.fy(F0), C.usd(lt1), C.fy(F1)), 'gap',
                         {'a': U(lt0), 'y': F(F0), 'b': U(lt1), 'z': F(F1)},
                         closes='Keystone’s invoices to the district, by service and month, '
                                'with student counts only'),
                    # What the documents say, as documents (rule 7): the Finance Committee's
                    # minutes record rate rises (quoted in `said`), and Keystone's own update to
                    # the School Committee reports its census, every member district together.
                    # Neither is near the rise in payments, and no document held gives
                    # Lunenburg's own count of students there.
                    step('Keystone reports its census, all member districts, up 11%% from 2021 '
                         'to September 2024; the minutes record rate rises of 14%% and almost 11%%. '
                         'Lunenburg paid it %s as much in FY2026; no document held gives its count.'
                         % times(l1 / l0), 'gap',
                         {'t': figure(l1 / l0, times(l1 / l0), 'times')},
                         allow=('14%', '11%', '2021', '2024', C.fy(F0), C.fy(F1)),
                         cite=(KEYSTONE_CENSUS, 'Keystone quarterly update, September 2024'),
                         closes='Keystone’s count of Lunenburg students by year, and its '
                                'tuition rate sheets, %s-%s' % (C.fy(F0), C.fy(F1)))]),
         con('Van Pool, the special education carrier, was paid %s more in %s than in %s.'
             % (C.pct(pc(c25, c26)), C.fy(F1), C.fy(F1 - 1)),
             ['c25', 'c26'],
             {'a': P(pc(c25, c26)), 'y': F(F1), 'z': F(F1 - 1)},
             notes=[step('Payments are not routes, riders or a rate; in %s Van Pool was paid %s.'
                         % (C.fy(F0), C.usd(c23)), 'gap', {'y': F(F0), 'a': U(c23)},
                         closes='the Van Pool contract, with its rate schedule and routes for '
                                'each year')])],
        chart=TP.ranking('Largest special education payees, by fund', rank_rows, '$',
                         highlight=top3, stack=stack,
                         note='Invoices paid, %s, by the fund each was paid from. The '
                              'report cuts names at twenty characters.'
                              % C.fyspan(F0, F1),
                         note_figures={'y': figure(F0, C.fyspan(F0, F1), 'fiscal years')}),
        also=[TP.series('Five largest payees, year by year', [C.fy(y) for y in J.YEARS], [
            TP.track(k, [d['pyear'].get((k, y), 0.0) for y in J.YEARS], 'published')
            for k in top5], '$', kind='bar', multiples=True,
            note='Each panel is one payee on the same scale. %s is not yet closed.' % C.fy(F1),
            note_figures={'y': F(F1)})],
        said=[dict(quote=KEYSTONE_RATES, board='Finance Committee', date='2024-03-14',
                   href=KEYSTONE_MINUTES, label='Finance Committee minutes, 2024-03-14')],
        table=dict(caption='The largest special education payees, by year', views=[dict(
            key='payees', label='Invoices paid, every fund', total_col=None,
            kinds=['ledger'] * len(J.YEARS), columns=[C.fy(y) for y in J.YEARS],
            rows=prov_rows,
            note='Names as the report prints them. The table stops at the largest payees, so '
                 'no family’s payment can be read off it by subtraction.')]),
        sources=sources() + [
            dict(label='Town of Lunenburg — Finance Committee minutes, 14 March 2024 '
                       '(2024-03-14-minutes-6469)', href=KEYSTONE_MINUTES),
            dict(label='Keystone Educational Collaborative — quarterly update to the School '
                       'Committee, September 2024', href=KEYSTONE_CENSUS)],
        finding_figures={'a': P(s3), 'b': figure(l1 / l0, times(l1 / l0), 'times'), 'y': F(F1)},
        )
    out['sped-providers']['not_established'] = [
        'Which child, or how many, any payment was for. Families and children are masked, and '
        'appear only inside the four-year aggregate.',
        'Which provider’s invoices the FY2026 year-end reclassification to the circuit breaker '
        'covered: the entry names no provider.',
        'Why any provider was paid more: more children, longer placements and higher rates '
        'all fit the same payments.',
    ]

    if sorted(out) != MINE:
        fail('the pages built are not the pages the registry gives this script: %s vs %s'
             % (sorted(out), MINE))
    return out, d


def outputs():
    pages, _ = build()
    return {os.path.join(OUT_DIR, '%s.json' % t):
            json.dumps(p, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
            for t, p in pages.items()}


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
        print('journal special education topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        os.replace(tmp, p)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
