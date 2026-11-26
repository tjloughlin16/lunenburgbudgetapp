#!/usr/bin/env python3
"""Special education, split into topic pages: eleven pages and the special education hub.

    python3 scripts/build_special_education_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_special_education_topics.py --check   # fail if any output would change

WHY THIS EXISTS. scripts/topics.py has the model: one question per page, under five minutes,
facts first, one to four conclusions resting on them. The special education shelf lists the
eleven pages this script owns, and special education transportation, which
build_transportation.py writes and which is listed here without being touched.

IT COMPUTES NOTHING NEW THAT IT CAN READ INSTEAD. Every figure comes from a payload or a
model already in the repository, and the script refuses to write if two of them stop agreeing
where they are supposed to:

  fy28/public/data/sped-cost.json            build_special_education.py: out-of-district
                                             tuition by fund from DESE's End of Year
                                             Financial Report, and the circuit breaker file.
  fy28/public/data/special-education-costs.json
                                             build_sped_costs.py: the voted budget against
                                             spending at the close, the circuit breaker
                                             account, per-child divisions (OUR ESTIMATE).
  fy28/public/data/circuit-breaker.json      build_circuit_breaker.py: DESE's reimbursement
                                             file, every year, and the neighbouring districts.
  fy28/public/data/sped-students.json        DESE's counts of children with a plan.
  fy28/public/data/sped-route.json           the town's 1 March placement counts and DESE's
                                             placement-trajectory cohorts.
  fy28/public/data/sped-regulation.json      603 CMR 28.06, parsed from the regulation itself.
  fy28/public/data/topics/sped-all-funds.json and build_school_all_funds.model()
                                             the school journal, every fund, FY2023-FY2026, for
                                             the reserve page's every-fund table (read, not
                                             recomputed; tied to the period-13 ledger above).
  model/sped.py                              BUDGET COLUMNS ONLY (rule 1): the in-district
                                             classification (ours), the tuition budgets, the
                                             paraprofessional and teacher lines.

RULE 1. The budget pages (tuition budget, in-district) read budget columns only. The one page
that sets a voted budget against spending at the close is the overruns page, where that step
IS the quantity, as build_sped_costs.py argues; nothing here grows a budget from an actual.

RULE 11. A budget line is the town's net share. The general fund column is called that, never
"the cost", and the money paid from other funds is shown beside it, never netted.

RULE 13a. Where two published counts or two of our own divisions disagree they are shown side
by side as separate facts and never averaged.
"""
import argparse
import collections
import csv
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(ROOT, 'model'))  # after scripts/: model/ has its own conclusions.py
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import circuit_breaker_how as CBH  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
from brief import step  # noqa: E402
import sped as SP  # noqa: E402

PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT_DIR = os.path.join(PUB, 'topics')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
COSTS = '/data/special-education-costs.json'

AIDES = {0: 'no aide', 1: 'one aide', 2: 'two aides'}

MINE = [t for t, (_, home, gen) in REG.TOPICS.items()
        if home == 'special-education' and gen == 'build_special_education_topics.py']


def fail(msg):
    raise SystemExit('build_special_education_topics: ' + msg)


def load(name):
    return json.load(open(os.path.join(PUB, name), encoding='utf-8'))


def said(payload, key, kind='minutes'):
    """One quotation a payload already verified against our copy of the minutes."""
    s = next((x for x in payload['said'] if x['key'] == key), None)
    if s is None:
        fail('quotation %r is no longer in its payload' % key)
    if not s['cite'].startswith('/docs/'):
        fail('quotation %r does not cite our copy' % key)
    return dict(quote=s['quote'], board=s['board'], date=s['date'], href=s['cite'],
                label='%s %s, %s' % (s['board'], kind, s['date']))


def psrc(payload):
    """The sources a payload lists, as {filename: source}."""
    out = {}
    for s in payload['sources']:
        href = s.get('docs_url') or s.get('url')
        name = s.get('filename') or href.split('/')[-1]
        out[name] = dict(label='%s — %s' % (s.get('publisher') or 'Source', name), href=href)
    return out


def sources():
    man = {r['key'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    out = {}
    for name in ('special-education-costs.json', 'sped-cost.json', 'circuit-breaker.json',
                 'sped-students.json', 'sped-route.json', 'sped-regulation.json'):
        out.update(psrc(load(name)))
    for k, (key, pub) in {
            'fy27-proposals.xlsx': ('budget-workbooks/fy27-proposals.xlsx',
                                    'Lunenburg Public Schools'),
            'paraprofessional-fy26-fy28.pdf': ('contracts/pdf/paraprofessional-fy26-fy28.pdf',
                                               'Lunenburg Public Schools and AFSCME'),
            'dese-teacher-contract.pdf': ('contracts/pdf/dese-teacher-contract.pdf',
                                          'Massachusetts DESE, educator contracts'),
    }.items():
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        out[k] = dict(label='%s — %s' % (pub, k), href='/docs/' + key)
    for f, what in (('lps-budget-lines.csv', 'every district budget line, by column'),
                    ('ood-tuition-history.csv', 'the tuition budgets, year by year'),
                    ('sped-para-history.csv', 'the paraprofessional budget line, by year'),
                    ('sped-teacher-history.csv', 'the special education teacher line, by year'),
                    ('placement-counts.csv', 'the town’s 1 March placement counts')):
        if not os.path.exists(os.path.join(ROOT, 'fy28', 'public', 'docs', 'data', f)):
            fail('/docs/data/%s is not published' % f)
        out[f] = dict(label='Lunenburg Budget Project — %s (%s)' % (f, what),
                      href='/docs/data/' + f)
    return out


def pct1(a, b):
    return round(100.0 * a / b, 1)


# --------------------------------------------------------------------- the charts
# Each page's signature (CLAUDE.md 7f; the brief is scripts/topic.py). Values are read from
# the payloads build() already reads; nothing is typed.

def _span(*maps):
    """Every year from the first any map holds to the last, so a missing year is a gap."""
    ys = sorted(set().union(*[set(m) for m in maps]))
    return list(range(ys[0], ys[-1] + 1))


def _two_child_counts(RT, CB):
    town = {r['fy']: r['total'] for r in RT['counts']}
    claim = {r['fy']: r['children'] for r in CB['series']}
    ys = _span(town, claim)
    return TP.series('Two counts of children, neither a price', [C.fy(y) for y in ys], [
        TP.track('Placed out of district, the town’s count', [town.get(y) for y in ys], 'stated'),
        TP.track('In the circuit breaker claim, DESE', [claim.get(y) for y in ys], 'published')],
        'children',
        note='The town counts placements on one day in March. The state’s claim counts children '
             'whose costs passed its threshold, in district or out, by year of payment.')


def _indexed(title, tracks, base, note):
    """Two series that are not one quantity, each as a percent of its own value in `base`.
    The division is ours, so every track is an estimate; the note says what was divided."""
    for _, m in tracks:
        if base not in m:
            fail('%s: no %s value to index on' % (title, C.fy(base)))
    ys = _span(*[m for _, m in tracks])
    return TP.series(title, [C.fy(y) for y in ys],
                     [TP.track(name, [100.0 * m[y] / m[base] if y in m else None
                                      for y in ys], 'estimate') for name, m in tracks],
                     '%', note=note, note_figures={'y': figure(base, C.fy(base), 'fiscal year')})


# --------------------------------------------------------------------- the pages

# ---------------------------------------------------------------- out-of-district tuition
# TJ, 26 November 2026: "do we have a report of out-of-district that breaks this down? Id like to
# see the funding sources over time, as well as the budget vs actual for this, and to see if theres
# a shift between private/collab. all the data that muddies the water gets very confusing" -- and,
# the same day, "you must not use the standard template for this too". So the page is composed:
# a signature drawn for it (each year, private and collaborative, by who was paid and who paid),
# the long view from the state's return with its one known misreading marked, what muddies it as
# a table of marks, then budget against spending on the two general fund lines.
#
# THE GRAIN IS THE PAYEE. fy_breakdown.model() places money from other funds on a general fund
# line by who received it (its rule a), and marks invoices numbered for a later year as prepaid.
# That is the reading the year-end pages use, and the only one under which FY2025 reads right:
# money paid to a collaborative was charged to the circuit breaker's PRIVATE account, and the
# state's End of Year return follows the account, so it shows the shift backwards.
PRIV_ACCT = '0100-3-300-9300-51-1-06-2-535019'
COLL_ACCT = '0100-3-300-9400-51-1-06-2-535023'
JOURNAL = os.path.join(ROOT, 'sources', 'data', 'munis-school-journal.csv')
YTD = os.path.join(ROOT, 'sources', 'data', 'munis-school-ytd.csv')
PLACEMENTS = os.path.join(ROOT, 'sources', 'data', 'placement-counts.csv')
# Colours: 1-3 are the site's thread hues for WHO PAID; 0 is muted, for the two minor items.
# Threads 4 and 5 are kept for the KIND OF SCHOOL (KIND_COLOUR), on every chart that splits by
# it, so no hue on this page means two things.
PAYERS = [('gf', 'General fund', 1), ('cb', 'Circuit breaker', 2), ('idea', 'IDEA grant', 3),
          ('rev', 'Revolving fund', 0)]
KIND_COLOUR = {'priv': 3, 'coll': 4}   # TopicCharts indexes from zero: threads 4 and 5
PAYER_OF = {'Circuit breaker': 'cb', 'IDEA (special education)': 'idea',
            'Revolving funds and lunch': 'rev'}


def ood_ledger():
    """Private and collaborative tuition by year and payer (the shared model), the general fund
    budget and its moves (the period-13 report and the journal), each asserted against the other."""
    import fy_breakdown as FB
    m = FB.model()
    rows = {(r['fy'], r['account']): r for r in m['rows'] if r['account'] in (PRIV_ACCT, COLL_ACCT)}
    years = sorted({fy for fy, _ in rows})
    ytd = {(int(r['fiscal_year']), r['account']): r
           for r in csv.DictReader(open(YTD, encoding='utf-8'))}
    jr = list(csv.DictReader(open(JOURNAL, encoding='utf-8')))
    out = {}
    for y in years:
        for k, acct in (('priv', PRIV_ACCT), ('coll', COLL_ACCT)):
            r, t = rows[(y, acct)], ytd[(y, acct)]
            paid = {'gf': float(r['gf_cost'])}
            for (_, who), v in r['payers'].items():
                if who not in PAYER_OF:
                    fail('%s FY%d: a payer the page has no name for: %r' % (k, y, who))
                paid[PAYER_OF[who]] = paid.get(PAYER_OF[who], 0.0) + float(v)
            early = float(r['prepaid'])
            if abs(sum(paid.values()) - float(r['all_funds_cost'])) > 0.01:
                fail('%s FY%d: the payers no longer sum to the all-funds cost' % (k, y))
            printed = float(t['ytd_expended']) + float(t['encumbrances'])
            if abs(float(r['gf_spent']) - printed) > 0.01 or abs(paid['gf'] + early - printed) > 0.01:
                fail('%s FY%d: the shared model and the period-13 report no longer agree on what '
                     'the general fund paid (%s)' % (k, y, printed))
            moves = [dict(date=x['effective_date'], amt=float(x['amount']), memo=x['description'])
                     for x in jr if x['account'] == acct and x['posts_to'] == 'transfer'
                     and int(x['fiscal_year']) == y]
            if abs(sum(x['amt'] for x in moves) - float(t['transfers_adjustments'])) > 0.01:
                fail('%s FY%d: the journal’s budget moves do not sum to the report’s' % (k, y))
            out[(y, k)] = dict(paid=paid, early=early, all=float(r['all_funds_cost']),
                               printed=printed, original=float(t['original_approp']),
                               revised=float(t['revised_budget']), moves=moves)
    # WHICH PAYEES ARE COLLABORATIVES: every vendor ever paid on a collaborative tuition account,
    # read off the journal rather than typed here. Money to one of them charged to a PRIVATE
    # account is where the account and the payee part company.
    coll_vendors = {x['vendor'] for x in jr if x['object'] == '535023' and x['vendor']
                    and x['posts_to'] == 'actual'}
    cross = collections.defaultdict(float)
    for x in jr:
        if x['object'] == '535019' and x['posts_to'] == 'actual' and x['vendor'] in coll_vendors:
            cross[int(x['fiscal_year'])] += float(x['amount'])
    # The 29 June reclass: one entry, general fund collaborative onto the circuit breaker.
    recl = [x for x in jr if x['source'] == 'GEN' and x['object'] == '535023'
            and x['posts_to'] == 'actual' and x['fund'] == '0100']
    if len(recl) != 1 or recl[0]['effective_date'] != '2026-06-29':
        fail('the page assumes one 29 June 2026 entry moved collaborative tuition to the fund')
    return out, years, dict(cross), -float(recl[0]['amount'])


def placement_counts():
    """The town's 1 March counts, where collaborative is printed as its own category and the
    parts tie to the total the report states."""
    out = {}
    for r in csv.DictReader(open(PLACEMENTS, encoding='utf-8')):
        if r['collaborative_basis'] == 'parallel category' and r['parts_tie'] == 'yes':
            out[int(r['fy'])] = dict(coll=int(r['collaborative']),
                                     priv=int(r['day']) + int(r['residential']),
                                     total=int(r['total']))
    return out


BOOK_TEXT = os.path.join(ROOT, 'sources', 'district-budget', 'text',
                         '3-12-25-town-manager-39-s-budget.txt')
BOOK_HREF = '/docs/district-budget/docs/3-12-25-town-manager-39-s-budget.pdf'


def book_offsets():
    """The circuit breaker the vote counted on: the FY2026 budget book prints it as a negative
    line under the collaborative tuitions, one column for FY2025 and one for FY2026."""
    book = ' '.join(open(BOOK_TEXT, encoding='utf-8').read().split())
    m = re.search(r'Circuit Breaker \(70% = \$[\d,]+\) \(75% = [\d,]+\)(-[\d,]+) (-[\d,]+)', book)
    if not m:
        fail('the circuit breaker offset is no longer printed in %s' % BOOK_TEXT)
    return {2025: -float(m.group(1).replace(',', '')), 2026: -float(m.group(2).replace(',', ''))}


def ood_page(CO, src, U, F, P, N, said_):
    import topic_blocks as TB
    L, years, cross, recl = ood_ledger()
    kids = placement_counts()
    off = book_offsets()
    y0, y1 = years[0], years[-1]
    f, con = LD.fact, TP.conclusion
    pc = {r['fy']: r for r in CO['per_code']}
    dese = sorted(pc)
    # ---- asserted, or nothing is written
    if not cross or set(cross) != {2025}:
        fail('the page says one year, FY2025, paid a collaborative from a private account')
    coll25_acct = pc[2025]['9400']['total']
    if abs(L[(2025, 'coll')]['all'] - cross[2025] - coll25_acct) > 2:
        fail('FY2025: by payee less the cross-charged sum is no longer the state’s 9400 figure')
    if abs(L[(2025, 'coll')]['original'] - off[2025] - L[(2025, 'coll')]['revised']
           + sum(x['amt'] for x in L[(2025, 'coll')]['moves'] if x['amt'] > 0)) > 0.01:
        fail('FY2025: the day-one cut is no longer the book’s circuit breaker offset')
    if L[(y1, 'priv')]['paid'].get('cb', 0) or L[(y0, 'priv')]['paid'].get('idea', 0):
        fail('the page says the circuit breaker paid no private tuition in FY%d' % y1)
    cbp = {y: L[(y, 'priv')]['paid'].get('cb', 0.0) for y in years}
    cbc = {y: L[(y, 'coll')]['paid'].get('cb', 0.0) for y in years}
    allp = {y: L[(y, 'priv')]['all'] for y in years}
    allc = {y: L[(y, 'coll')]['all'] for y in years}
    if not (all(allc[a] < allc[b] for a, b in zip(years, years[1:]))
            and all(allc[y] < allp[y] for y in years[:-1]) and allc[y1] > allp[y1]
            and allc[y1] - allc[y0] > allp[y1] - allp[y0]):
        fail('the page says collaborative tuition rose every year, passed private in the last '
             'year, and grew by more')
    if not (kids[max(kids)]['coll'] > kids[max(kids)]['priv']
            and all(v['coll'] <= v['priv'] for y, v in kids.items() if y < max(kids))):
        fail('the page says the last count is the first with more children in collaboratives')
    if [r['fy'] for r in CO['spend']] != dese:
        fail('sped-cost.json: spend and per_code no longer cover the same years')
    k14, k25 = kids[min(kids)], kids[max(kids)]
    early = L[(y1, 'coll')]['early']
    idea = L[(y1, 'priv')]['paid']['idea']
    dese24, led24 = CO['spend'][[r['fy'] for r in CO['spend']].index(2024)]['total'], allp[2024] + allc[2024]

    # ---- the signature: each year, by payee, split by payer
    figs = set()

    def usd(v):
        s = C.usd(v)
        figs.add(s)
        return s
    payer_name = {k: n for k, n, _ in PAYERS}
    ylines = []
    for y in years:
        figs.add(C.fy(y))
        ls = []
        for k, name, kk in (('priv', 'Paid to private schools', 'priv'),
                            ('coll', 'Paid to collaboratives', 'coll')):
            v = L[(y, k)]
            parts = [dict(payer=p, amt=round(v['paid'][p], 2), text=usd(v['paid'][p]))
                     for p, _, _ in PAYERS if v['paid'].get(p)]
            if y in kids:
                n = kids[y][kk]
                figs.add(C.num(n))
                kt = '%s %s in %s, 1 March' % (C.num(n), 'child' if n == 1 else 'children',
                                               'collaboratives' if kk == 'coll'
                                               else 'day or residential schools')
            else:
                kt = 'count for 1 March not yet published'
            ls.append(dict(name=name, total_text=usd(v['all']), kids_text=kt, parts=parts,
                           early=dict(payer='early', amt=round(v['early'], 2), text=usd(v['early']))
                           if v['early'] else None))
        ylines.append(dict(fy=C.fy(y), lines=ls))
    figs.add(C.fy(y1 + 1))
    sig = TB.custom(
        'ood-who-paid', 'Tuition by who was paid, and who paid it',
        dict(years=ylines,
             payers=[dict(key=k, label=n, colour=c) for k, n, c in PAYERS]
             + [dict(key='early', label='%s invoices paid early' % C.fy(y1 + 1), colour=0, hollow=True)],
             max=max(L[(y, k)]['all'] + L[(y, k)]['early'] for y in years for k in ('priv', 'coll')),
             note='Every fund, %s to %s, sorted by who received each payment, not by the account it '
                  'was charged to. Spent plus still owed at the close. The counts are children '
                  'placed on 1 March; they are not divided into the dollars.' % (C.fy(y0), C.fy(y1))),
        place='lead', figures=sorted(figs), allow=('1 March',),
        basis=('record', 'Town ledger, school journal, period 13'),
        alt='For each fiscal year, two bars: tuition paid to private schools and to collaboratives, '
            'each split into the general fund, the circuit breaker, the IDEA grant and a revolving fund.',
        so=('Collaborative tuition grew every year and passed private tuition in %s; the circuit '
            'breaker moved from the private bar to the collaborative one.' % C.fy(y1), {'y': F(y1)}))

    # ---- the overview above it: every year on one scale (TJ, 26 November 2026: "can we also
    # have a top chart that puts that all on 1 horizontal chart? i want to see scale easily")
    # TJ, the same day: "we neeed [it] to go more than 3 years back. it clearly shows an upward
    # trend but looking forther, actually, the trend is relatively stable" -- and then, of the
    # children: "our student counts Dropped over the years?!". So the overview runs from the
    # state's first year. Before the ledger it is the state's return, by the account charged;
    # from the ledger's first year it is the town's ledger, by payee. The change of source is a
    # marked line on the chart, never a silent splice. The children counted on 1 March ride on a
    # second axis, beside the dollars and never divided into them (rule 7).
    pre = [y for y in dese if y < y0]
    ov_years = pre + years
    ov_p = {**{y: pc[y]['9300']['total'] for y in pre}, **allp}
    ov_c = {**{y: pc[y]['9400']['total'] for y in pre}, **allc}
    ov_t = {y: ov_p[y] + ov_c[y] for y in ov_years}
    if not (all(ov_c[y] < ov_p[y] for y in ov_years[:-1]) and ov_c[y1] > ov_p[y1]):
        fail('the overview says collaborative tuition was the smaller part every year until the last')
    if abs(pc[2025]['9300']['total'] + pc[2025]['9400']['total'] - ov_t[2025]) > 2:
        fail('FY2025: the state’s every-fund total and the ledger’s no longer agree; the overview '
             'joins the two sources and says they agree where they overlap')
    pk = max(ov_years, key=lambda y: ov_t[y])
    kpk = max(kids, key=lambda y: kids[y]['total'])
    kl = max(kids)
    if not (ov_t[y1] < ov_t[pk] and kids[kl]['total'] < kids[kpk]['total']):
        fail('the overview says tuition is below its peak while the children counted fell')
    over = TB.chart(TP.series(
        'Out-of-district tuition, every fund, by kind of school', [C.fy(y) for y in ov_years],
        [TP.track('Private schools', [round(ov_p[y], 2) for y in ov_years], colour=KIND_COLOUR['priv']),
         TP.track('Collaboratives', [round(ov_c[y], 2) for y in ov_years], colour=KIND_COLOUR['coll'])],
        '$', kind='bar', stacked=True,
        secondary=dict(name='Children placed, 1 March', unit='children',
                       values=[kids[y]['total'] if y in kids else None for y in ov_years]),
        events=[(C.fy(y0), 'Town ledger from here')],
        note='To %s the state’s return, by account; from %s the town’s ledger, by who was paid. '
             'The line is children placed on 1 March, not divided into the dollars.'
             % (C.fy(pre[-1]), C.fy(y0)),
        note_figures={'a': F(pre[-1]), 'b': F(y0)}, note_allow=('1 March',)),
        so=('Tuition was %s in %s, below its %s peak of %s; the children counted fell from %s to %s.'
            % (C.usd(ov_t[y1]), C.fy(y1), C.fy(pk), C.usd(ov_t[pk]), C.num(kids[kpk]['total']),
               C.num(kids[kl]['total'])),
            {'a': U(ov_t[y1]), 'y': F(y1), 'z': F(pk), 'b': U(ov_t[pk]),
             'm': N(kids[kpk]['total']), 'n': N(kids[kl]['total'])}))

    # ---- tuition per child counted: OUR DIVISION, by TJ's decision of 26 November 2026, which
    # relaxes rule 7 for this one chart: "Add it, and you can even quote shcool committee members
    # from recent meetings doing the same math themselves publicly". The committee did, on
    # 7 October 2026 (the quotation below the chart). It is drawn as an estimate, and the note
    # says why it is not a price: the count is one day, the dollars a whole year.
    pcy = [y for y in ov_years if y in kids]
    per = {y: dict(all=ov_t[y] / kids[y]['total'], priv=ov_p[y] / kids[y]['priv'],
                   coll=ov_c[y] / kids[y]['coll']) for y in pcy}
    if any(kids[y]['priv'] + kids[y]['coll'] != kids[y]['total'] for y in pcy):
        fail('the per-child chart assumes the two kinds add to the count the report states')
    xs_k = list(range(pcy[0], pcy[-1] + 1))
    q0, q1 = pcy[0], pcy[-1]
    per_chart = TB.chart(TP.series(
        'Tuition per child counted, our estimate', [C.fy(y) for y in xs_k],
        [TP.track('Every child', [round(per[y]['all']) if y in per else None for y in xs_k], 'estimate'),
         TP.track('Private schools', [round(per[y]['priv']) if y in per else None for y in xs_k],
                  'estimate', colour=KIND_COLOUR['priv']),
         TP.track('Collaboratives', [round(per[y]['coll']) if y in per else None for y in xs_k],
                  'estimate', colour=KIND_COLOUR['coll'])],
        '$', kind='line',
        events=[(C.fy(y0), 'Town ledger from here')] if y0 in xs_k else None,
        note='Our division: a year’s tuition over the children counted on 1 March, one day. A '
             'child placed for part of a year counts as one or none, so this is not a price.',
        note_allow=('1 March',)),
        so=('By our division, tuition per child counted went from %s in %s to %s in %s.'
            % (C.usd(round(per[q0]['all'])), C.fy(q0), C.usd(round(per[q1]['all'])), C.fy(q1)),
            {'a': U(round(per[q0]['all'])), 'y': F(q0), 'b': U(round(per[q1]['all'])), 'z': F(q1)}))
    # The committee doing the same arithmetic in public, verbatim from our copy of its minutes.
    SC_MIN = 'sources/meetings/text/school-committee/2026-10-07-minutes-8058.txt'
    sc_quote = ('Using an illustrative average of $150,000 per placement, members noted that 15 '
                'placements could cost approximately $2.25 million.')
    if not TP.verbatim_in(sc_quote, open(os.path.join(ROOT, SC_MIN), encoding='utf-8').read()):
        fail('the School Committee quotation is no longer verbatim in %s' % SC_MIN)
    sc_said = dict(quote=sc_quote, board='School Committee', date='2026-10-07',
                   href='/docs/minutes/text/school-committee/2026-10-07-minutes-8058.txt',
                   label='School Committee minutes, 2026-10-07')
    # And the Select Board, three weeks later, using the same average (TJ: "you can use the one
    # you found in oct"). Only our machine captions hold it: the video at its second, a finding aid.
    OCT27 = 'sources/data/youtube-transcripts/select-board/2026-10-27-EEjHeG_q7gY.json'
    oct_quote = 'that 300,000 number was based on the average. A special ed placement of 150,000.'
    if not TP.verbatim_in(oct_quote, ' '.join(
            x['text'] for x in json.load(open(os.path.join(ROOT, OCT27), encoding='utf-8'))['segments'])):
        fail('the 27 October quotation is no longer verbatim in %s' % OCT27)
    oct_said = dict(quote=oct_quote, board='Select Board', date='2026-10-27',
                    href='https://www.youtube.com/watch?v=EEjHeG_q7gY&t=3583s',
                    label='Select Board recording (machine captions)')

    # ---- composition: each kind of school, each year, by who paid (TJ, 26 November 2026: "i
    # want another chart that shows the composition of each as well in 1 chart, over time, split
    # by private/collab"). A GROUPED stacked column chart, drawn by its own component
    # (ood-composition): the stock series chart collides eight labels and, on a phone, thins the
    # axis to every other one, dropping every collaborative bar's name. Payer colours are the
    # breakdown's below, so the two charts read as one key.
    if not (cbp[y0] > allp[y0] / 2 and cbc[2025] > allc[2025] / 2):
        fail('the composition chart says the circuit breaker paid most of private tuition in the '
             'first year and most of collaborative tuition in FY2025')
    cfigs = set()

    def cu(v):
        t = C.usd(v)
        cfigs.add(t)
        return t
    groups = []
    for y in years:
        cfigs.add(C.fy(y))
        bars = []
        for k, kind, short in (('priv', 'Private', 'Private'), ('coll', 'Collaborative', 'Collab.')):
            v = L[(y, k)]
            bars.append(dict(kind=kind, short=short, total=round(v['all'], 2), total_text=cu(v['all']),
                             parts=[dict(payer=p, amt=round(v['paid'][p], 2), text=cu(v['paid'][p]))
                                    for p, _, _ in PAYERS if v['paid'].get(p)]))
        groups.append(dict(fy=C.fy(y), bars=bars))
    step = 250000
    top = step * int(-(-max(max(allp.values()), max(allc.values())) // step))
    ticks = []
    for i in range(int(top // step) + 1):
        v = i * step
        t = '$0' if not v else ('$%gM' % (v / 1e6) if v >= 1e6 else '$%dk' % (v // 1000))
        cfigs.add(t)
        ticks.append(dict(v=v, text=t))
    compo = TB.custom(
        'ood-composition', 'Who paid, by kind of school and year',
        dict(groups=groups, payers=[dict(key=k, label=n, colour=c) for k, n, c in PAYERS],
             ticks=ticks,
             note='By who received each payment, spent plus still owed at the close. Next year’s '
                  'invoices paid early are left out.'),
        place='body', figures=sorted(cfigs),
        basis=('record', 'Town ledger, school journal, period 13'),
        alt='For each fiscal year, a private bar and a collaborative bar side by side, each split '
            'into the general fund, the circuit breaker, the IDEA grant and a revolving fund.',
        so=('The circuit breaker paid most of private tuition in %s and most of collaborative '
            'tuition in %s.' % (C.fy(y0), C.fy(2025)), {'a': F(y0), 'b': F(2025)}))

    # ---- what muddies it
    atm = next(x for x in L[(2025, 'coll')]['moves'] if x['amt'] > 0)
    muddy = TB.checks(
        'What makes the accounts hard to read',
        ['Private, by account', 'Collaborative, by account', 'The state’s return',
         'General fund budget against spending'],
        [TB.check_row('A collaborative paid from the private account',
                      ('%s: %s paid to a collaborative was charged to the circuit breaker’s private '
                       'tuition account.' % (C.fy(2025), C.usd(cross[2025])),
                       {'y': F(2025), 'a': U(cross[2025])}), [0, 1, 2]),
         TB.check_row('The budget cut to its net on the first day',
                      ('%s: the collaborative budget fell by %s on 1 July, the circuit breaker the '
                       'budget book expected; Town Meeting added %s in May.'
                       % (C.fy(2025), C.usd(off[2025]), C.usd(atm['amt'])),
                       {'y': F(2025), 'a': U(off[2025]), 'b': U(atm['amt'])}, ('1 July',)), [3]),
         TB.check_row('A grant paid a private school as contracted services',
                      ('%s: %s from the IDEA grant went to a private school, booked as contracted '
                       'services, not tuition.' % (C.fy(y1), C.usd(idea)),
                       {'y': F(y1), 'a': U(idea)}), [0]),
         TB.check_row('Circuit breaker money by journal entry',
                      ('%s: %s of collaborative tuition the general fund had paid was moved onto the '
                       'circuit breaker on 29 June.' % (C.fy(y1), C.usd(recl)),
                       {'y': F(y1), 'a': U(recl)}, ('29 June',)), [1, 3]),
         TB.check_row('Next year’s invoices paid in June',
                      ('%s: %s of collaborative invoices numbered for %s were charged on 30 June.'
                       % (C.fy(y1), C.usd(early), C.fy(y1 + 1)),
                       {'y': F(y1), 'a': U(early), 'z': F(y1 + 1)}, ('30 June',)), [1, 3]),
         TB.check_row('The state and the ledger disagree',
                      ('%s: the state’s return says %s, every fund; the ledger %s.'
                       % (C.fy(2024), C.usd(dese24), C.usd(led24)),
                       {'y': F(2024), 'a': U(dese24), 'b': U(led24)}), [2])],
        place='body', first='What it is', second='When, and how much',
        so='Each one moves a figure a reader would quote; the bars above are drawn after all of them.')

    # ---- planned against paid, by payer (the two years the book prints its offset)
    def card(y, title):
        v = L[(y, 'coll')]
        rows = [('Circuit breaker, expected', C.usd(off[y]), None),
                ('Circuit breaker, paid', C.usd(v['paid'].get('cb', 0)),
                 'bad' if v['paid'].get('cb', 0) < off[y] else None),
                ('General fund, budget', C.usd(v['revised']), None),
                ('General fund, paid', C.usd(v['paid']['gf']),
                 'bad' if v['paid']['gf'] > v['revised'] else 'good')]
        if v['early']:
            rows.append(('Next year’s invoices, paid early', C.usd(v['early']), 'muted'))
        return TB.panel(title, rows, sub=('Fiscal year %s' % C.fy(y), {'y': F(y)}))
    plan = TB.panels('Collaborative tuition, planned and paid',
                     [card(2025, 'The first year budgeted net'), card(y1, 'The latest closed year')],
                     place='body',
                     so='The budget counted on the circuit breaker; when it paid less, the general '
                        'fund paid the rest.')

    # ---- budget against spending, both lines, every year (the walk, as a table)
    def walk(k):
        rows = []
        for y in reversed(years):
            v = L[(y, k)]
            mv = sum(x['amt'] for x in v['moves'])
            rows.append(dict(label=C.fy(y), cells=[
                C.usd(v['original']), C.usd(mv) if mv else '—', C.usd(v['revised']),
                C.usd(v['printed']), C.usd(v['revised'] - v['printed'])]))
        return rows
    bva = dict(caption='General fund budget against spending', views=[
        dict(key=k, label=lab, total_col=None, kinds=['budget', 'budget', 'budget', 'ledger', 'ledger'],
             columns=['Original', 'Moved', 'Budget', 'Paid', 'Left'], rows=walk(k),
             note='Period-13 report: paid is spent plus still owed, after any amount moved to '
                  'another fund. Left below zero is past the budget.', note_allow=('13',))
        for k, lab in (('coll', 'Collaborative tuition'), ('priv', 'Private tuition'))])

    # ---- the long view, from the state's return
    xs = [C.fy(y) for y in dese]
    long_kind = TP.series(
        'Private and collaborative tuition, every fund', xs,
        [TP.track('Private schools', [pc[y]['9300']['total'] for y in dese], 'published',
                  colour=KIND_COLOUR['priv']),
         TP.track('Collaboratives', [pc[y]['9400']['total'] for y in dese], 'published',
                  colour=KIND_COLOUR['coll'],
                  labels={len(dese) - 1: 'charged to the private account, not the payee'})],
        '$', kind='line',
        note='DESE End of Year Financial Report, functions 9300 and 9400, by the account each '
             'payment was charged to.', note_allow=('9300', '9400'))
    ks = list(range(min(kids), max(kids) + 1))
    long_kids = TP.series(
        'Children placed, by kind of school', [C.fy(y) for y in ks],
        [TP.track('Day or residential schools', [kids[y]['priv'] if y in kids else None for y in ks],
                  colour=KIND_COLOUR['priv']),
         TP.track('Collaboratives', [kids[y]['coll'] if y in kids else None for y in ks],
                  colour=KIND_COLOUR['coll'])],
        'children', kind='line',
        note='The annual town report’s count on 1 March. No split is printed for %s.' % C.fy(2021),
        note_figures={'y': F(2021)}, note_allow=('1 March',))
    long_fund = TP.series(
        'Who paid, as the state reports it', xs,
        [TP.track('General fund', [CO['spend'][i]['gen_fund'] for i in range(len(dese))]),
         TP.track('Every other fund', [CO['spend'][i]['grants'] for i in range(len(dese))])],
        '$', kind='bar', stacked=True,
        note='DESE End of Year Financial Report. Other funds include the circuit breaker and '
             'grants; the return does not name them.')
    # Third on the page, under the two ledger charts (TJ, 26 November 2026: "bump it up to the top
    # third part"): whether the general fund has come to pay more, over every year the state reports.
    fund_chart = TB.chart(long_fund, so='Money outside the general fund has paid part of tuition '
                                        'in every year the state reports.')

    # ---- facts and conclusions
    fx = [
        f('c23', U(allc[y0]), 'paid to collaboratives, %s' % C.fy(y0), 'published', {'y': F(y0)}),
        f('c26', U(allc[y1]), 'paid to collaboratives, %s' % C.fy(y1), 'published', {'y': F(y1)}),
        f('p23', U(allp[y0]), 'paid to private schools, %s' % C.fy(y0), 'published', {'y': F(y0)}),
        f('p26', U(allp[y1]), 'paid to private schools, %s' % C.fy(y1), 'published', {'y': F(y1)}),
        f('cbp23', U(cbp[y0]), 'circuit breaker on private tuition, %s' % C.fy(y0), 'published',
          {'y': F(y0)}),
        f('cbc25', U(cbc[2025]), 'circuit breaker on collaborative tuition, %s' % C.fy(2025),
          'published', {'y': F(2025)}),
        f('off26', U(off[y1]), 'circuit breaker the approved budget counted on, %s' % C.fy(y1), 'published',
          {'y': F(y1)}),
        f('cbc26', U(cbc[y1]), 'circuit breaker paid, collaborative, %s' % C.fy(y1), 'published',
          {'y': F(y1)}),
        f('gf26', U(L[(y1, 'coll')]['printed']), 'general fund paid, collaborative, %s' % C.fy(y1),
          'published', {'y': F(y1)}),
        f('k14', N(k14['coll'], 'children'), 'in collaboratives of %s placed, %s'
          % (C.num(k14['total']), C.fy(min(kids))), 'published',
          {'n': N(k14['total']), 'y': F(min(kids))}),
        f('k25', N(k25['coll'], 'children'), 'in collaboratives of %s placed, %s'
          % (C.num(k25['total']), C.fy(max(kids))), 'published',
          {'n': N(k25['total']), 'y': F(max(kids))}),
        f('d25', U(coll25_acct), 'collaborative, the state’s return, %s' % C.fy(2025), 'published',
          {'y': F(2025)}),
    ]
    cons = [
        con('Tuition paid to collaboratives rose from %s in %s to %s in %s.'
            % (C.usd(allc[y0]), C.fy(y0), C.usd(allc[y1]), C.fy(y1)), ['c23', 'c26', 'p23', 'p26'],
            {'a': U(allc[y0]), 'y': F(y0), 'b': U(allc[y1]), 'z': F(y1)},
            so='Private tuition went from %s to %s over the same years, so most of the growth is '
               'collaborative.' % (C.usd(allp[y0]), C.usd(allp[y1])),
            so_figures={'a': U(allp[y0]), 'b': U(allp[y1])}),
        con('The circuit breaker paid %s of private tuition in %s and none in %s.'
            % (C.usd(cbp[y0]), C.fy(y0), C.fy(y1)), ['cbp23', 'cbc25'],
            {'a': U(cbp[y0]), 'y': F(y0), 'z': F(y1)},
            so='It paid %s of collaborative tuition in %s; a general fund line can rise simply '
               'because the repayment moved.' % (C.usd(cbc[2025]), C.fy(2025)),
            so_figures={'a': U(cbc[2025]), 'y': F(2025)}),
        con('The approved budget counted on %s of circuit breaker for collaboratives in %s; %s came.'
            % (C.usd(off[y1]), C.fy(y1), C.usd(cbc[y1])), ['off26', 'cbc26', 'gf26'],
            {'a': U(off[y1]), 'y': F(y1), 'b': U(cbc[y1])},
            so='The general fund line, budgeted net of it, paid %s, %s of it next year’s invoices.'
               % (C.usd(L[(y1, 'coll')]['printed']), C.usd(early)),
            so_figures={'a': U(L[(y1, 'coll')]['printed']), 'b': U(early)}),
        con('Children in collaboratives went from %s of %s placed in %s to %s of %s in %s.'
            % (C.num(k14['coll']), C.num(k14['total']), C.fy(min(kids)), C.num(k25['coll']),
               C.num(k25['total']), C.fy(max(kids))), ['k14', 'k25', 'd25'],
            {'a': N(k14['coll']), 'n': N(k14['total']), 'y': F(min(kids)), 'b': N(k25['coll']),
             'm': N(k25['total']), 'z': F(max(kids))},
            so='The state’s return, which follows the account, puts %s collaborative tuition '
               'at %s and shows the shift backwards.'
               % (C.fy(2025), C.usd(coll25_acct)),
            so_figures={'a': U(coll25_acct), 'y': F(2025)}),
    ]
    sources = [
        dict(src['glytdbud-expense-fy2026-p13-gf-school.xlsx'], key='gf'),
        dict(src['glytdbud-expense-fy2026-p13-special-school.xlsx'], key='special'),
        dict(label='Lunenburg Budget Project — munis-school-journal.csv (every school journal '
                   'line, FY2023–FY2026, our redacted reading of the Town’s Report 1)',
             href='/docs/data/munis-school-journal.csv', key='journal'),
        dict(label='Lunenburg Public Schools — FY2026 approved budget, 12 March 2025 (the circuit '
                   'breaker line under the tuitions)', href=BOOK_HREF, key='book'),
        dict(src['district-expenditures-by-function.xlsx'], key='dese'),
        dict(src['placement-counts.csv'], key='kids'),
    ]
    cite = TP.cite
    return TP.page(
        'out-of-district-tuition',
        'Paid to collaboratives: %s in %s, %s in %s, now more than to private schools.'
        % (C.usd(allc[y0]), C.fy(y0), C.usd(allc[y1]), C.fy(y1)),
        fx, cons, sources=sources, said=[sc_said, oct_said, said_],
        finding_figures={'a': U(allc[y0]), 'y': F(y0), 'b': U(allc[y1]), 'z': F(y1)},
        tables=[bva],
        flow=['finding',
              cite(over, 'dese', 'gf', 'special', 'journal', 'kids'),
              cite(per_chart, 'dese', 'gf', 'special', 'journal', 'kids'), 'said',
              cite(compo, 'gf', 'special', 'journal'),
              cite(fund_chart, 'dese'),
              cite(sig, 'gf', 'special', 'journal', 'kids'), ('conclusion', 0), ('conclusion', 1),
              cite(muddy, 'journal', 'gf', 'special', 'dese', 'book'),
              cite(plan, 'book', 'gf', 'special', 'journal'), ('conclusion', 2),
              cite(('table', 0), 'gf', 'journal'),
              cite(TB.chart(long_kind, so='Drawn by account, the last year turns the trend over.'),
                   'dese'),
              cite(TB.chart(long_kids, so=('%s is the first count with more children in '
                                            'collaboratives than in day or residential schools.'
                                            % C.fy(max(kids)), {'y': F(max(kids))})), 'kids'),
              ('conclusion', 3),
              'related', 'sources'])


def build():
    SC = load('special-education-costs.json')
    CO = load('sped-cost.json')
    CB = load('circuit-breaker.json')
    ST = load('sped-students.json')
    RT = load('sped-route.json')
    RG = load('sped-regulation.json')
    src = sources()
    S = lambda *names: [src[n] for n in names]
    U = lambda v: figure(v, C.usd(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    f, con = LD.fact, TP.conclusion
    out = {}

    # ------------------------------------------------ out-of-district tuition, every fund
    spend = {r['fy']: r for r in CO['spend']}
    last = CO['last']
    if spend[last['fy']] != last or abs(last['gen_fund'] + last['grants'] - last['total']) > 1:
        fail('sped-cost.json: the last year no longer foots, general fund plus other funds')
    peak = max(spend.values(), key=lambda r: r['total'])
    low = min(spend.values(), key=lambda r: r['total'])
    shi = max(spend.values(), key=lambda r: r['outside_share_pct'])
    slo = min(spend.values(), key=lambda r: r['outside_share_pct'])
    if CO['ties_count'] != len(CO['ties_years']):
        fail('sped-cost.json: ties_count disagrees with ties_years')
    # FY2024: the state's return and the town's ledger disagree, by exactly the circuit breaker
    # payment the state lists for that year. Both are shown; neither is chosen.
    af = {r['fy']: r for r in SC['all_funds']}
    dese24, munis24 = spend[2024]['total'], af[2024]['all_spent']
    if round(dese24 - munis24) != round(af[2024]['dese_paid']):
        fail('FY2024: DESE less the ledger no longer equals the state’s circuit breaker payment')
    if abs(spend[2025]['total'] - af[2025]['all_spent']) > 2:
        fail('FY2025: DESE and the ledger no longer agree on tuition, every fund')
    y25 = last['fy']
    fx = {}
    fx['total25'] = f('total25', U(last['total']),
                      'out-of-district tuition, every fund, %s' % C.fy(y25), 'published',
                      {'y': F(y25)})
    fx['gf25'] = f('gf25', U(last['gen_fund']), 'of it from the general fund, %s' % C.fy(y25),
                   'published', {'y': F(y25)})
    fx['share25'] = f('share25', P(last['outside_share_pct']),
                      'of it paid outside the general fund, %s' % C.fy(y25), 'published',
                      {'y': F(y25)})
    # The hub draws this table; the tuition page is composed below (ood_page).
    tuition_table = dict(caption='Out-of-district tuition by fund, by year', views=[dict(
        key='funds', label='DESE End of Year Financial Report', total_col=2,
        kinds=['ledger'] * 4,
        columns=['General fund', 'Grants and revolving funds', 'Every fund',
                 'Share outside the general fund'],
        rows=[dict(label=C.fy(r['fy']), cells=[C.usd(r['gen_fund']), C.usd(r['grants']),
                                                C.usd(r['total']), C.pct(r['outside_share_pct'])])
              for r in sorted(spend.values(), key=lambda r: -r['fy'])],
        note='Functions 9300 and 9400 on the district’s statutory return, closed years. The '
             'general fund column equals the district’s own restated budget figure in most '
             'years; the other column holds every non-general fund together.')])
    out['out-of-district-tuition'] = ood_page(CO, src, U, F, P, N, said(CO, 'skyrocket'))

    # ------------------------------------------------ cost per placement (OUR divisions)
    pc = SC['per_child']
    placed = {r['fy']: r for r in pc['placed']}
    recent = pc['placed'][-4:]
    if round(statistics.median([r['per_child'] for r in recent])) != pc['recent_median']:
        fail('the per-child median is no longer the median of the last four years')
    r0, r1 = recent[0]['fy'], recent[-1]['fy']
    cbl = CB['series'][-1]
    if round(cbl['eligible'] / cbl['children']) != round(cbl['per_child']):
        fail('circuit-breaker.json: per_child is no longer eligible over children claimed')
    np_med = SC['request']['nonpublic_median']
    bt = SC['request']['by_type']
    # NO DIVISIONS. The first draft of this page divided tuition by a headcount and published
    # the quotient as "our estimate" of a placement's price. CLAUDE.md rule 7: "Dollars are not
    # students... If the actual quantity is not published, the honest sentence is that we
    # cannot say -- not a number inferred from something adjacent to it." So the page states
    # the two published quantities and why they do not divide into a price. (The reserve
    # model's own per-child median is a modelling input, documented with the model.)
    p25 = placed[2025]
    out['cost-per-placement'] = TP.page(
        'cost-per-placement',
        'No published document says what one out-of-district placement costs.',
        [f('tuition25', U(p25['all_funds']),
           'out-of-district tuition, every fund, %s' % C.fy(2025), 'published', {'y': F(2025)}),
         f('kids25', N(p25['children'], 'children'),
           'children placed, 1 March, %s' % C.fy(2025), 'published', {'y': F(2025)},
           allow=('1 March',)),
         f('cbkids', N(cbl['children'], 'children'),
           'children in the circuit breaker claim, %s' % C.fy(cbl['fy']), 'published',
           {'y': F(cbl['fy'])}),
         f('price-gap', None, 'what one placement costs, by type', 'gap',
           closes='the district’s placement-level billing detail, gross of circuit breaker')],
        [con('The tuition total and the count of children placed do not divide into a price.',
             ['tuition25', 'kids25', 'price-gap'],
             notes=[step('The tuition is a closed-year total across every fund; the count is one '
                         'day in March. A child placed for part of a year is counted or missed '
                         'by the date, and a total can include costs that are not tuition for '
                         'one child.', 'gap', allow=('March',),
                         closes='the district’s placement-level billing detail, gross of circuit '
                                'breaker')]),
         con('The circuit breaker claim is not a placement count either.', ['cbkids'],
             notes=[step('It counts only children whose costs passed the threshold, in district '
                         'or out.', 'gap',
                         closes='the district’s circuit breaker claim, child by child, with names '
                                'removed')])],
        # TWO COUNTS OF CHILDREN, COUNTING DIFFERENT THINGS (rule 13a): the town's 1 March
        # placements and the children in the state's reimbursement claim. Two tracks, never
        # merged -- and no dollars on this axis, because the page's point is that no division
        # of the one by the other is a price (rule 7).
        chart=_two_child_counts(RT, CB),
        sources=S('district-expenditures-by-function.xlsx', 'placement-counts.csv',
                  'dese-circuit-breaker.xlsx'))

    # ------------------------------------------------ in-district, budget columns only
    cls = SP.classified()
    tot27 = SP.total(SP.FY27BAL, SP.is_sped)
    tot25 = SP.total(SP.FY25, SP.is_sped)
    if abs(cls['total'] - tot27) > 1:
        fail('model/sped.py: the classified lines no longer sum to the FY2027 base')
    PT, TT = SP.PARA_TREND, SP.TEACHER_TREND
    paras = {r['fy']: r for r in ST['paras']}
    p0, p1 = ST['para_first'], ST['para_last']
    fall = round(100 * (1 - p1['fte'] / p0['fte']), 1)
    para_cagr, teach_cagr = 100 * PT['cagr'], 100 * TT['cagr']
    FTE = lambda v: figure(v, '%.1f' % v, 'full-time equivalents')
    gap_fund = 'the district’s position list by fund, and the EPIMS work assignment records ' \
               'behind DESE’s count'
    para_rows = [dict(label=C.fy(r['fy']), cells=[C.usd(r['total']), r['stage'],
                                                   ('%.1f' % paras[r['fy']]['fte'])
                                                   if r['fy'] in paras else None])
                 for r in sorted(SP.PARA_SERIES, key=lambda r: -r['fy'])]
    out['in-district-special-education'] = TP.page(
        'in-district-special-education',
        'The paraprofessional budget line grew %s a year over %s budgets; the state’s FTE fell %s.'
        % (C.pct(para_cagr, 2), C.num(PT['n']), C.pct(fall)),
        [f('ind27', U(tot27), 'in district, %s balanced budget (our %s lines)'
           % (C.fy(2027), C.num(len(cls['counted']))), 'estimate',
           {'y': F(2027), 'n': N(len(cls['counted']))}),
         f('ind25', U(tot25), 'the same lines, %s budget' % C.fy(2025), 'estimate',
           {'y': F(2025)}),
         f('para0', U(PT['first']), 'paraprofessional budget line, %s' % C.fy(PT['firstFy']),
           'published', {'y': F(PT['firstFy'])}),
         f('para1', U(PT['last']), 'the same line, %s' % C.fy(PT['lastFy']), 'published',
           {'y': F(PT['lastFy'])}),
         f('pararate', P(para_cagr, 2), 'a year, compounded (our arithmetic)', 'published'),
         f('paracon', P(100 * SP.AFSCME_RATE), 'a year, paraprofessionals’ contract, %s to %s'
           % (C.fy(2026), C.fy(2028)), 'contract', {'a': F(2026), 'b': F(2028)}),
         f('teachrate', P(teach_cagr, 2), 'teacher line a year, %s budgets (ours)'
           % C.num(TT['n']), 'published', {'n': N(TT['n'])}),
         f('teachcon', P(100 * SP.LEA_RATE), 'a year, the teachers’ contract, %s' % C.fy(2027),
           'contract', {'y': F(2027)}),
         f('fte0', FTE(p0['fte']), 'paraprofessional FTE, state count, %s' % C.fy(p0['fy']),
           'published', {'y': F(p0['fy'])}),
         f('fte1', FTE(p1['fte']), 'the same count, %s' % C.fy(p1['fy']), 'published',
           {'y': F(p1['fy'])}),
         f('fund-gap', None, 'which fund pays which paraprofessional post', 'gap',
           closes=gap_fund)],
        [con('The paraprofessional line rose from %s to %s over %s budgets; the contract gives %s.'
             % (C.usd(PT['first']), C.usd(PT['last']), C.num(PT['n']), C.pct(100 * SP.AFSCME_RATE)),
             ['para0', 'para1', 'pararate', 'paracon'],
             {'a': U(PT['first']), 'b': U(PT['last']), 'n': N(PT['n']),
              'c': P(100 * SP.AFSCME_RATE)},
             notes=[step('A contract sets what one person is paid, so the rest may be more posts, '
                         'more hours, or lines recoded. Nothing here tests which.',
                         'hypothesis')]),
         con('The state counts %s paraprofessional FTE in %s and %s in %s.'
             % ('%.1f' % p0['fte'], C.fy(p0['fy']), '%.1f' % p1['fte'], C.fy(p1['fy'])),
             ['fte0', 'fte1', 'fund-gap'],
             {'a': FTE(p0['fte']), 'y': F(p0['fy']), 'b': FTE(p1['fte']), 'z': F(p1['fy'])},
             notes=[step('The documents do not explain how a rising budget line and a falling '
                         'count describe the same people; neither publisher says what its figure '
                         'counts.', 'gap', closes=gap_fund)]),
         con('The special education teacher line grew %s a year, under the %s contract raise.'
             % (C.pct(teach_cagr, 2), C.pct(100 * SP.LEA_RATE)), ['teachrate', 'teachcon'],
             {'a': P(teach_cagr, 2), 'b': P(100 * SP.LEA_RATE)}),
         con('Our in-district lines total %s for %s, against %s in %s.'
             % (C.usd(tot27), C.fy(2027), C.usd(tot25), C.fy(2025)), ['ind27', 'ind25'],
             {'a': U(tot27), 'y': F(2027), 'b': U(tot25), 'z': F(2025)},
             notes=[step('The state’s account codes have no special education total, so which '
                         'lines count is our classification.', 'gap',
                         closes='a chart of accounts from the district marking every special '
                                'education line')])],
        # The finding sets a rising budget line against a falling count of staff. Dollars and
        # FTE cannot share an axis, so each is drawn against its own value in the first year
        # both exist -- our division, and drawn as an estimate.
        chart=_indexed('Paraprofessional budget line and staff count', [
            ('Budget line, budget columns only', {r['fy']: r['total'] for r in SP.PARA_SERIES}),
            ('FTE, the state’s count', {r['fy']: r['fte'] for r in ST['paras']})],
            min(set(r['fy'] for r in SP.PARA_SERIES) & set(paras)),
            'Each as a percent of its own %s value (ours). One is dollars and one is staff, so '
            'only the directions compare.' % C.fy(min(set(r['fy'] for r in SP.PARA_SERIES)
                                                       & set(paras)))),
        table=dict(caption='Special education paraprofessionals, by year', views=[dict(
            key='paras', label='Budget line beside the state’s count', total_col=-1,
            kinds=['stated', 'stated', 'ledger'],
            columns=['Budget line', 'Which budget', 'State FTE count'],
            rows=para_rows,
            note='The budget line is from the district’s workbooks, budget columns only. The FTE '
                 'is DESE’s. They are set side by side and not reconciled; a blank is a year '
                 'the state does not print.')]),
        said=[said(ST, 'backbone'), said(ST, 'addtwo')],
        sources=S('fy27-proposals.xlsx', 'lps-budget-lines.csv', 'sped-para-history.csv',
                  'sped-teacher-history.csv', 'paraprofessional-fy26-fy28.pdf',
                  'dese-teacher-contract.pdf', 'dese-sped-indicators.xlsx'),
        finding_figures={'a': P(para_cagr, 2), 'n': N(PT['n']), 'b': P(fall)})

    # ------------------------------------------------ the circuit breaker
    cbs = {r['fy']: r for r in CB['series']}
    c26 = cbs[CB['last_fy']]
    # Over the years DESE printed a count for. FY2023 is withheld in the file (`less than 6`),
    # and a withheld count is a gap, not a zero and not a rank -- as build_special_education.py
    # and build_serf_topics.py already treat it.
    kpeak = max((r for r in CB['series'] if r['children'] is not None), key=lambda r: r['children'])
    if (kpeak['fy'], kpeak['children']) != (CO['cb_peak_students']['fy'],
                                            CO['cb_peak_students']['students']):
        fail('the two payloads disagree on the year most children were claimed')
    ident = len(CO['cb_identity_years'])
    nyears = len(CB['series'])
    if ident + len(CO['cb_identity_breaks']) != nyears:
        fail('the identity years and breaks no longer cover every year of the file')
    s10 = 100 * cbs[2010]['paid_share_of_claim']
    s23 = 100 * cbs[2023]['paid_share_of_claim']
    s26 = 100 * c26['paid_share_of_claim']
    se26 = 100 * c26['paid_share_of_eligible']
    tr0 = CO['cb_transport_first_year']
    # The Circuit breaker PAGE is written by build_serf_topics.py since 26 October 2026, merged
    # with the SERF shelf's five steps (TJ: "only have one called 'circuit breaker'"). The
    # checks above stay: the account page below reads the same payloads.

    # ------------------------------------------------ the circuit breaker account
    acct = SC['cb_account']
    yrs = {r['fy']: r for r in acct['years']}
    sm = acct['summary']
    a26, apk = sm['last'], sm['peak']
    if yrs[2026]['closing'] != a26['closing'] or yrs[apk['fy']]['closing'] != apk['closing']:
        fail('the account summary no longer matches its years')
    neg = [fy for fy in sorted(yrs) if yrs[fy]['closing'] < 0]
    if neg != [2013, 2014, 2015]:
        fail('the years the account closed below zero have changed: %s' % neg)
    lowest = min(yrs.values(), key=lambda r: r['closing'])
    n_over = sum(1 for r in yrs.values() if r['spent'] > r['received'])
    if round(cbs[2024]['paid']) != round(af[2024]['dese_paid']):
        fail('FY2024: the two payloads disagree on what the state paid')
    rt = SC['receipts_timing'][0]
    if (rt['fy_a'], rt['fy_b']) != (2024, 2025):
        fail('the receipts-timing pair is no longer FY2024 and FY2025')
    if round(af[2024]['dese_paid'] + af[2025]['dese_paid']) != round(rt['total']) or \
            round(af[2024]['cb_fund_receipts'] + af[2025]['cb_fund_receipts']) != round(rt['total']):
        fail('FY2024 and FY2025 no longer sum to the same total on both sides')
    out['circuit-breaker-account'] = TP.page(
        'circuit-breaker-account',
        'The account closed %s at %s, down from %s at the close of %s.'
        % (C.fy(2026), C.usd(a26['closing']), C.usd(apk['closing']), C.fy(apk['fy'])),
        [f('close26', U(a26['closing']), 'balance at the close of %s' % C.fy(2026), 'published',
           {'y': F(2026)}),
         f('peak', U(apk['closing']), 'balance at the close of %s, the highest' % C.fy(apk['fy']),
           'published', {'y': F(apk['fy'])}),
         f('fell', N(sm['fell'], 'years'), 'of the last %s in which the balance fell'
           % C.num(sm['of']), 'published', {'n': N(sm['of'])}),
         f('low', U(lowest['closing']), 'balance at the close of %s, the lowest' % C.fy(lowest['fy']),
           'published', {'y': F(lowest['fy'])}),
         f('cbt23', U(af[2023]['cb_fund_spent']), 'tuition paid from it, %s' % C.fy(2023),
           'published', {'y': F(2023)}),
         f('cbt26', U(af[2026]['cb_fund_spent']), 'tuition paid from it, %s' % C.fy(2026),
           'published', {'y': F(2026)}),
         f('dese24', U(af[2024]['dese_paid']), 'paid by the state, %s, its file' % C.fy(2024),
           'published', {'y': F(2024)}),
         f('rec24', U(af[2024]['cb_fund_receipts']), 'received, %s, the town’s ledger' % C.fy(2024),
           'published', {'y': F(2024)}),
         f('earmark', None, 'how much of the balance is meant for next year', 'gap',
           closes='the district’s circuit breaker spending plan for the year')],
        [con('The account closed %s at %s, down from %s at the close of %s.'
             % (C.fy(2026), C.usd(a26['closing']), C.usd(apk['closing']), C.fy(apk['fy'])),
             ['close26', 'peak', 'fell', 'earmark'],
             {'y': F(2026), 'a': U(a26['closing']), 'b': U(apk['closing']), 'z': F(apk['fy'])}),
         con('It pays tuition every year, not only in a bad one: %s in %s and %s in %s.'
             % (C.usd(af[2023]['cb_fund_spent']), C.fy(2023), C.usd(af[2026]['cb_fund_spent']),
                C.fy(2026)), ['cbt23', 'cbt26'],
             {'a': U(af[2023]['cb_fund_spent']), 'y': F(2023), 'b': U(af[2026]['cb_fund_spent']),
              'z': F(2026)},
             notes=[step('Whether the voted tuition line is set expecting this account to pay '
                         'part of it is not published.', 'gap',
                         closes='the district’s budget narrative for the tuition line')]),
         con('It closed below zero from %s to %s, at %s in %s.'
             % (C.fy(neg[0]), C.fy(neg[-1]), C.usd(lowest['closing']), C.fy(lowest['fy'])),
             ['low'], {'a': F(neg[0]), 'b': F(neg[-1]), 'c': U(lowest['closing']),
                       'y': F(lowest['fy'])}),
         con('For %s the state lists %s paid; the town’s ledger records %s received.'
             % (C.fy(2024), C.usd(af[2024]['dese_paid']), C.usd(af[2024]['cb_fund_receipts'])),
             ['dese24', 'rec24'],
             {'y': F(2024), 'a': U(af[2024]['dese_paid']), 'b': U(af[2024]['cb_fund_receipts'])},
             notes=[step('Over %s and %s both sides sum to %s, which fits a payment recorded a '
                         'year later. Nothing here tests it.'
                         % (C.fy(2024), C.fy(2025), C.usd(rt['total'])), 'hypothesis',
                         {'y': F(2024), 'z': F(2025), 't': U(rt['total'])})])],
        # A stock: the balance at each year's close, the bars below zero drawn as such.
        chart=TP.series('Circuit breaker account at year end',
                        [C.fy(y) for y in _span(yrs)],
                        [TP.track('Balance at the close', [yrs[y]['closing'] if y in yrs else None
                                                           for y in _span(yrs)], 'published')],
                        '$', kind='bar',
                        note='Fund 2640: the annual town reports to %s, the town’s year-end ledgers '
                             'after.' % C.fy(2023), note_figures={'y': F(2023)},
                        note_allow=('2640',)),
        table=dict(caption='The circuit breaker account, by year', views=[dict(
            key='account', label='Fund 2640', total_col=3, kinds=['ledger'] * 4,
            columns=['Opening', 'Received', 'Spent', 'Closing'],
            rows=[dict(label=C.fy(r['fy']), cells=[C.usd(r['opening']), C.usd(r['received']),
                                                    C.usd(r['spent']), C.usd(r['closing'])])
                  for r in sorted(acct['years'], key=lambda r: -r['fy'])],
            note='To %s, the Special Revenue schedule of each annual town report; after it, carried '
                 'through the town’s year-end ledgers.' % C.fy(2023))]),
        # TJ, 24 October 2026: how the account works, step by step, and whether each year it
        # was fully spent or overspent -- "what does it mean if the circuit breaker isnt fully
        # spent, or its overspent? I dont undersatnd."
        how_it_works=CBH.steps(acct['years']),
        also=[TP.series('Received and spent, each year', [C.fy(y) for y in sorted(yrs)], [
            TP.track('Received from the state', [round(yrs[y]['received']) for y in sorted(yrs)]),
            TP.track('Spent from the account', [round(yrs[y]['spent']) for y in sorted(yrs)])],
            '$', kind='bar',
            note='A spent bar taller than its received bar is a year the account used savings: %s '
                 'of %s years.' % (C.num(n_over), C.num(len(yrs))),
            note_figures={'a': N(n_over), 'n': N(len(yrs))})],
        said=[said(SC, 'carryover')],
        sources=S('glytdbud-expense-fy2026-p13-special-school.xlsx',
                  '4130-fy-2025-annual-town-report.txt', 'dese-circuit-breaker.xlsx'),
        finding_figures={'y': F(2026), 'a': U(a26['closing']), 'b': U(apk['closing']),
                         'z': F(apk['fy'])})

    # ------------------------------------------------ the tuition budget (budgets only)
    ly = SP.level_service_year()
    TR = SP.tuition_trend()
    th = SP.tuition_history()
    if (TR['high'], TR['highFy']) != (ly['tuition_fy26'], 2026) or th[-1]['total'] != ly['tuition_fy27']:
        fail('the tuition budgets no longer have FY2026 as the high and FY2027 as the last')
    cut = -ly['tuition_change']
    cutp = -100 * ly['tuition_rate']
    out['tuition-budget'] = TP.page(
        'tuition-budget',
        '%s budgets out-of-district tuition at %s, %s below %s, a %s cut.'
        % (C.fy(2027), C.usd(ly['tuition_fy27']), C.usd(cut), C.fy(2026), C.pct(cutp, 0)),
        [f('b26', U(ly['tuition_fy26']), 'tuition budgeted, %s, the highest' % C.fy(2026),
           'published', {'y': F(2026)}),
         f('b27', U(ly['tuition_fy27']), 'tuition budgeted, %s' % C.fy(2027), 'published',
           {'y': F(2027)}),
         f('cut', U(cut), 'less between the two budgets', 'published'),
         f('cutp', P(cutp, 0), 'the same cut, as a share', 'published'),
         f('blow', U(TR['low']), 'lowest of %s budgets, %s' % (C.num(TR['n']), C.fy(TR['lowFy'])),
           'published', {'n': N(TR['n']), 'y': F(TR['lowFy'])}),
         f('up', N(TR['up'], 'budgets'), 'that rose on the year before', 'published'),
         f('down', N(TR['down'], 'budgets'), 'that fell on the year before', 'published'),
         f('pub', P(100 * ly['published'], 2), '%s level-service rise (our arithmetic)'
           % C.fy(2027), 'published', {'y': F(2027)}),
         f('held', P(100 * ly['underlying'], 2), 'the same rise, tuition held at %s' % C.fy(2026),
           'estimate', {'y': F(2026)})],
        [con('Tuition is budgeted at %s for %s, %s below %s.'
             % (C.usd(ly['tuition_fy27']), C.fy(2027), C.usd(cut), C.fy(2026)),
             ['b26', 'b27', 'cut', 'cutp'],
             {'a': U(ly['tuition_fy27']), 'y': F(2027), 'c': U(cut), 'z': F(2026)},
             notes=[step('Whether the cut expects fewer placements or lower prices is not stated '
                         'in the budget.', 'gap', allow=(C.fy(2027),),
                         closes='the district’s budget narrative for the %s tuition line, '
                                'placement by placement' % C.fy(2027))]),
         con('Across %s budgets it ran from %s to %s, rising in %s and falling in %s.'
             % (C.num(TR['n']), C.usd(TR['low']), C.usd(TR['high']), C.num(TR['up']),
                C.num(TR['down'])), ['blow', 'b26', 'up', 'down'],
             {'n': N(TR['n']), 'a': U(TR['low']), 'b': U(TR['high']), 'u': N(TR['up']),
              'd': N(TR['down'])}),
         con('Hold tuition at %s and the %s level-service rise is %s, not %s.'
             % (C.fy(2026), C.fy(2027), C.pct(100 * ly['underlying'], 2),
                C.pct(100 * ly['published'], 2)), ['pub', 'held'],
             {'y': F(2026), 'z': F(2027), 'a': P(100 * ly['underlying'], 2),
              'b': P(100 * ly['published'], 2)})],
        # Budgets only (rule 1), as the district printed them: the two kinds of placement
        # stack into the line the finding is about.
        chart=TP.series('Out-of-district tuition, as budgeted', [C.fy(r['fy']) for r in th], [
            TP.track('Private schools', [r['private'] for r in th], 'stated'),
            TP.track('Collaboratives', [r['collaborative'] for r in th], 'stated')],
            '$', kind='bar', stacked=True,
            note='The district’s budgets: a settled figure where a later document reports one, '
                 'otherwise the proposal. Never what was spent.'),
        table=dict(caption='Out-of-district tuition, as budgeted', views=[dict(
            key='budgets', label='Budget columns only', total_col=2,
            kinds=['stated', 'stated', 'stated', 'stated'],
            columns=['Private schools', 'Collaboratives', 'Both', 'Which budget'],
            rows=[dict(label=C.fy(r['fy']), cells=[C.usd(r['private']), C.usd(r['collaborative']),
                                                    C.usd(r['total']), r['stage']])
                  for r in sorted(th, key=lambda r: -r['fy'])],
            note='Functions 9300 and 9400 in the district’s budgets: a settled figure where a later '
                 'document reports one, otherwise the proposal. Never what was spent.')]),
        said=[said(SC, 'nineteen')],
        sources=S('fy27-proposals.xlsx', 'ood-tuition-history.csv', 'lps-budget-lines.csv'),
        finding_figures={'y': F(2027), 'a': U(ly['tuition_fy27']), 'c': U(cut), 'z': F(2026),
                         'p': P(cutp, 0)})

    # ------------------------------------------------ the special education reserve
    # THE QUESTION, a board member's: "assess the proper funding level for the Special
    # Education Reserve Fund based on average and standard deviations year to year." TJ, 23
    # October 2026: one page that answers all of it -- per year, what was voted and what was
    # spent on each line, where the money came from, the need the reserve exists to cover,
    # and the sizing statistics. So this page carries five tables, each its own question:
    #   1. voted and spent, general fund, each line, every year      (special-education-costs)
    #   2. over or under the vote, and the need                       (the same ledger)
    #   3. every fund, FY2023-FY2026, one tab per year                (sped-all-funds, as built)
    #   4. the reserve levels, and what each would have covered       (ours, on table 2)
    #   5. money that came in beside it: receipts and allocations     (DESE, the town's books)
    # Table 5 is never subtracted from table 2: a receipt is not spending on a line (rule 13).
    need = SC['need']
    pl = SC['per_line']
    req = SC['request']
    nyrs = SC['last_fy'] - SC['first_fy'] + 1
    if len(SC['surprise']) != nyrs or pl['ood']['years'] != nyrs:
        fail('the surprise series no longer covers every year from first_fy to last_fy')
    # Prove the series from the ledger itself, not from the generator's own field: each
    # line's spending at the close less the budget voted before the year, and a year's need
    # is the sum of the lines that ran OVER (an underspend on one line does not pay another's
    # overrun -- OUR choice, said on the page, with the net figure beside it).
    LINES = ('indist', 'ood', 'trans')
    sur = sorted(SC['surprise'], key=lambda r: r['fy'])
    led = sorted(SC['ledger'], key=lambda r: r['fy'])
    for r, lg in zip(sur, led):
        v = {g: lg[g]['spent'] - lg[g]['original'] for g in LINES}
        if r['fy'] != lg['fy'] or any(v[g] != r[g] for g in LINES) \
                or r['need'] != sum(max(0, v[g]) for g in LINES):
            fail('special-education-costs.json: FY%s need no longer recomputes from the ledger'
                 % r['fy'])
    vals = [r['need'] for r in sur]
    net = [r['indist'] + r['ood'] + r['trans'] for r in sur]
    avg = round(statistics.mean(vals))
    sd = round(statistics.stdev(vals))        # sample SD: 17 years are a sample of years
    lv1, lv2 = avg + sd, avg + 2 * sd
    # Counted over the years a line ran over, as Reserve options counts them: a year that needed
    # nothing is met by any reserve, and counting it made the same level read 16 of 17 here and
    # 12 of 13 there (TJ, 26 October 2026: "seems to have different numbers").
    nbad = sum(1 for x in vals if x > 0)
    cov = lambda lvl: sum(1 for x in vals if 0 < x <= lvl)
    pairs = [vals[i] + vals[i + 1] for i in range(len(vals) - 1)]
    cov2 = lambda lvl: sum(1 for x in pairs if x <= lvl)
    two = max(((sur[i]['fy'], pairs[i]) for i in range(len(pairs))), key=lambda x: x[1])
    if max(vals) != need['worst']['gross']:
        fail('the worst year in the series is not need.worst')
    if sum(1 for x in vals if x > 0) != need['years_needing']:
        fail('years_needing no longer counts the years with a need')
    netover = sum(1 for x in net if x > 0)
    hidden = sum(1 for x, n_ in zip(vals, net) if x > 0 and n_ <= 0)
    if not netover < need['years_needing']:
        fail('the voted-vs-spent conclusion says fewer years ran over in total than on a line')
    rs = SC['reserve']
    if not two[1] > lv2:
        fail('the worst two-year run no longer exceeds average + 2 SD; conclusion 2 says it does')
    fy0, fy1 = C.fy(sur[0]['fy']), C.fy(sur[-1]['fy'])

    # EVERY FUND, FY2023-FY2026: the figures /special-education/sped-all-funds publishes, read
    # from its payload as published (build_school_all_funds.py computes them from the school
    # journal; nothing here computes them again). Its five components map onto this page's
    # three lines: tuition and transportation are one each, and IN-DISTRICT is contracted
    # services + staff pay + supplies. That mapping is asserted against the period-13 ledger
    # build_sped_costs.py reads, line by line and year by year: two account definitions (the
    # journal's labels, the ledger's segment 51 less ELL) that must land on the same dollars.
    AFP = load(os.path.join('topics', 'sped-all-funds.json'))
    AFMOD = load('school-all-funds-model.json')
    AFM = AFMOD['sped']

    def money(s):
        t = s.replace('−', '-')
        if not re.fullmatch(r'-?\$[\d,]+', t):
            fail('sped-all-funds: %r is not a whole-dollar figure' % s)
        return int(t.replace('$', '').replace(',', ''))
    COMP = {'ood': ('tuition',), 'trans': ('transport',), 'indist': ('contracted', 'pay', 'supplies')}
    MAP = {'ood': ('Out-of-district tuition',), 'trans': ('Transportation',),
           'indist': ('Contracted services and evaluations', 'Staff pay and benefits',
                      'Supplies, equipment and other')}
    # Since 26 October 2026 that table names each grant in its own column, only the grants that
    # paid that year (TJ: "break down the other funds spent"); they are added back to one
    # grants figure here. Rounded cell by cell, so the sum can sit a dollar or two off.
    HEAD, TAIL = ['Voted, general fund', 'General fund spent', 'Circuit breaker'], 'Every fund spent'
    every = {}            # fy -> line -> [voted, gf spent, circuit breaker, grants, every fund]
    for v in AFP['table']['views']:
        if v['columns'][:3] != HEAD or v['columns'][-1] != TAIL or \
                not all(re.search(r'\(#\d{3}\)$', c) for c in v['columns'][3:-1]):
            fail('sped-all-funds: its table columns moved: %s' % v['columns'])
        y = int(v['key'][2:])
        rows = {r['label']: (lambda xs: xs[:3] + [sum(xs[3:-1]), xs[-1]])([money(c) for c in r['cells']])
                for r in v['rows']}
        if set(rows) != {x for xs in MAP.values() for x in xs} | {'All of it'}:
            fail('sped-all-funds FY%d: its rows are not the five components and a total' % y)
        every[y] = {g: [sum(rows[c][i] for c in cs) for i in range(5)] for g, cs in MAP.items()}
        every[y]['all'] = rows['All of it']
        m = AFM[str(y)]
        for got, want in ((rows['All of it'][0], m['voted']), (rows['All of it'][1], m['gf_spent']),
                          (rows['All of it'][4], m['gf_spent'] + m['outside'])):
            if abs(got - want) > 1:
                fail('sped-all-funds FY%d: its table (%s) no longer ties to its model (%s)'
                     % (y, got, want))
        lg = next(r for r in led if r['fy'] == y)
        for g in LINES:
            for i, k in ((0, 'original'), (1, 'spent')):
                # components are rounded one by one, so three can sum a dollar or two away
                if abs(every[y][g][i] - lg[g][k]) > 2:
                    fail('FY%d %s %s: the journal\'s components (%s) and the period-13 ledger '
                         '(%s) no longer tie -- the two account definitions have parted'
                         % (y, g, k, every[y][g][i], lg[g][k]))
    EY = sorted(every)
    if EY != [y for y in range(SC['munis_first_fy'], SC['last_fy'] + 1)]:
        fail('the every-fund years %s are not the MUNIS years' % EY)
    # THE PRINTED TABLE FOOTS. The payload's cells are rounded one by one and do not add to
    # their own total by a dollar here and there; so the cents come from the same model that
    # built them (build_school_all_funds.model(), imported -- the figures are its, not a second
    # computation), and each column's three lines are footed to its total (C.footed). Every
    # fund is then the sum of the footed funds, so the rows foot too.
    import build_school_all_funds as BSAF
    cents_cb, cents_gr = {}, {}
    ms = BSAF.model()['sped']
    if {c for cs in COMP.values() for c in cs} != set(BSAF.J.IN_TOTAL):
        fail('journal.py components in the total are %s; this page maps %s'
             % (sorted(BSAF.J.IN_TOTAL), sorted(COMP)))
    FUNDS = (('General fund',), ('Circuit breaker',), ('IDEA grants', 'Other special education grants'))
    for y in EY:
        cents = {g: [sum(ms.get((y, 'gf:' + c, 'original_budget'), 0.0) for c in COMP[g])]
                 + [sum(ms.get((y, 'spent', fn, c), 0.0) for fn in fns for c in COMP[g])
                    for fns in FUNDS] for g in LINES}
        cols = [C.footed([cents[g][i] for g in LINES]) for i in range(4)]
        for j, g in enumerate(LINES):
            e = [cols[i][0][j] for i in range(4)]
            if any(abs(e[i] - every[y][g][i]) > 2 for i in range(4)):
                fail('FY%d %s: the model\'s cents %s and the published table %s part' % (y, g, e, every[y][g]))
            every[y][g] = e + [e[1] + e[2] + e[3]]
        tot = [cols[i][1] for i in range(4)]
        cents_cb[y] = sum(cents[g][2] for g in LINES)
        cents_gr[y] = sum(cents[g][3] for g in LINES)
        if any(abs(tot[i] - every[y]['all'][i]) > 1 for i in range(4)):
            fail('FY%d: the model\'s totals %s and the published table %s part' % (y, tot, every[y]['all']))
        every[y]['all'] = tot + [tot[1] + tot[2] + tot[3]]
    cbs = {y: every[y]['all'][2] for y in EY}
    worst_b = max(req['bases'], key=lambda b: b['before'])
    if worst_b['fy'] not in cbs or not worst_b['before'] > rs['cap']:
        fail('conclusion 4 says the worst year without the circuit breaker passes the cap')
    if abs(cbs[worst_b['fy']] - worst_b['cb_tuition']) > 1:
        fail('conclusion 4 says "without it": in FY%d the account paid more than tuition, so the '
             'upper bound no longer removes all of it' % worst_b['fy'])
    # The circuit breaker's tuition in table 3 must be the figure build_sped_costs.py set back
    # on the tuition line for `before` (fund 2640, functions 9100-9400).
    for b in req['bases']:
        if abs(every[b['fy']]['ood'][2] - b['cb_tuition']) > 1:
            fail('FY%d: the circuit breaker tuition in sped-all-funds (%s) is not the figure the '
                 'upper bound puts back (%s)' % (b['fy'], every[b['fy']]['ood'][2], b['cb_tuition']))

    # MONEY THAT CAME IN BESIDE IT. Three different quantities, never one column:
    #   the state's circuit breaker PAYMENT, by year of payment (DESE's file);
    #   what the town's books RECEIVED into the circuit breaker account (fund 2640);
    #   the IDEA entitlement ALLOCATION (DESE, grant code 0240), an award, spent over two years.
    paid = {r['fy']: r['paid'] for r in CB['series']}     # DESE's total quarterly payment
    # DESE lists extra relief and supplemental payments in their own columns; `paid` holds
    # neither, and the note names the years that had one rather than adding them in.
    extra_yrs = sorted(int(r['fy']) for r in csv.DictReader(open(os.path.join(
        ROOT, 'sources', 'data', 'dese-circuit-breaker.csv'), encoding='utf-8'))
        if r['lea'] == '01620000' and (r['extra_relief_payment'] or r['additional_supplemental_payment']))
    recd = {r['fy']: r['received'] for r in SC['cb_account']['years']}
    idea = {}
    for r in csv.DictReader(open(os.path.join(ROOT, 'sources', 'data',
                                              'dese-entitlement-allocations.csv'), encoding='utf-8')):
        if r['district_code'] == '0162' and r['fund_code'] == '0240':
            if int(r['fy']) in idea:
                fail('dese-entitlement-allocations.csv: two IDEA rows for Lunenburg in FY%s' % r['fy'])
            idea[int(r['fy'])] = float(r['amount'])
    if not idea:
        fail('dese-entitlement-allocations.csv: no IDEA allocation for Lunenburg')
    for y in EY:
        if abs(recd[y] - AFMOD['receipts'][str(y)]['Circuit breaker']) > 0.5:
            fail('FY%d: fund 2640 receipts in the two payloads disagree' % y)
    # THE REQUEST, as the recording's machine captions give it: a finding aid, not a record
    # (no minutes of 7 October 2026 are held). Shown as a caption in `said`, never as a fact.
    mo = next((x for x in req['said'] if x['key'] == 'motion'), None)
    if not mo or not re.search(r'\$[\d,]+', mo['quote']):
        fail('the School Committee motion is no longer in special-education-costs.json')
    inys = list(range(min(paid), max(max(paid), max(idea)) + 1))
    # The district's own deck to the Finance Committee, 22 October 2026 (rule 13a: `stated`,
    # the presenting body's figures). It prints the latest IDEA allocation; it must be DESE's.
    DECK = 'correspondence/2026-10-22-special-education-funding-superintendent-finance-committee.pptx'
    deck = open(os.path.join(ROOT, 'sources', 'correspondence', 'text',
                             os.path.basename(DECK) + '.txt'), encoding='utf-8').read()
    if '%s (0240)' % C.usd(idea[max(idea)]) not in deck:
        fail('the district deck no longer states the %s IDEA allocation DESE lists'
             % C.fy(max(idea)))

    # THE BOARD MEMBER'S TABLE, in his columns and his order (TJ relayed it verbatim, 23
    # October 2026): "Fiscal Year (10 years? FY21 had a formula change ...) / Special Education
    # Operational Budget / IDEA Grant Funding / Circuit Breaker Funding / Actual Costs".
    #   budget      the general fund vote on the three lines, as tables 2-3 define them
    #   IDEA        DESE's ALLOCATION, 0240 + 0262 (both IDEA: school age and preschool). The
    #               FY2022 ARP IDEA allocations (0252, 0264) were one-time and are named in the
    #               note, not added, so the column stays one quantity year to year
    #   circuit     what DESE PAID in the year, ALL of it: the quarterly payment plus any extra
    #   breaker     relief or supplemental payment (he asked for funding, not the schedule)
    #   actual      spending. General fund: payments plus what was still owed. Every fund:
    #               FY2023-FY2026 the journal (table 3); FY2017-FY2022 the general fund plus the
    #               annual reports' special revenue DISBURSEMENTS for fund 2640 and the special
    #               education grant funds -- spending, not receipts, so not a proxy (rule 7);
    #               checked against the journal for FY2023 below, and the difference printed
    # Every year the need series covers (TJ: "it's odd I don't see those peaks"). Where a source
    # does not reach back, the cell is empty and the note says why -- never a different kind
    # of figure in its place.
    BM0, BM1 = SC['first_fy'], SC['last_fy']
    alloc = {}
    for r in csv.DictReader(open(os.path.join(ROOT, 'sources', 'data',
                                              'dese-entitlement-allocations.csv'), encoding='utf-8')):
        if r['district_code'] == '0162':
            alloc.setdefault(int(r['fy']), {})[r['fund_code']] = float(r['amount'])
    # DESE's allocation form offers FY2017 onward (its own year list, in our snapshots under
    # sources/state-dese/entitlements/); before that there is no allocation to show.
    IDEA0 = min(alloc)
    idea_bm = {y: alloc[y].get('0240', 0) + alloc[y].get('0262', 0)
               for y in range(BM0, BM1 + 1) if y in alloc and '0240' in alloc[y]}
    if sorted(idea_bm) != list(range(IDEA0, BM1 + 1)):
        fail('the IDEA allocations are not every year from FY%d' % IDEA0)
    no262 = [y for y in idea_bm if '0262' not in alloc[y]]
    arp = {y: alloc[y].get('0252', 0) + alloc[y].get('0264', 0) for y in alloc
           if alloc[y].get('0252') or alloc[y].get('0264')}
    cbrows = {int(r['fy']): r for r in csv.DictReader(open(os.path.join(
        ROOT, 'sources', 'data', 'dese-circuit-breaker.csv'), encoding='utf-8'))
        if r['lea'] == '01620000'}
    num_ = lambda x: float(x) if x not in (None, '') else 0.0
    cb_all = {y: num_(cbrows[y]['total_quarterly_payment']) + num_(cbrows[y]['extra_relief_payment'])
              + num_(cbrows[y]['additional_supplemental_payment']) for y in range(BM0, BM1 + 1)}
    for y in range(BM0, BM1 + 1):
        if abs(num_(cbrows[y]['total_quarterly_payment']) - paid[y]) > 0.5:
            fail('FY%d: the circuit breaker CSV and circuit-breaker.json disagree' % y)
    cb_extra = [y for y in range(BM0, BM1 + 1) if cb_all[y] != paid[y]]
    # FY2021, THE FORMULA CHANGE, read off DESE's own file: the state row's transportation
    # reimbursement is empty in every year before the first one printed, and a payment
    # reimburses the year before -- so that year's COSTS are the first whose transportation
    # counted. The law that made the change is not in this archive; the file is the evidence.
    st_tr = sorted(int(r['fy']) for r in csv.DictReader(open(os.path.join(
        ROOT, 'sources', 'data', 'dese-circuit-breaker.csv'), encoding='utf-8'))
        if r['level'] == 'state' and r['reimb_transport'])
    change_fy = st_tr[0] - 1
    if change_fy != 2021 or st_tr != list(range(st_tr[0], st_tr[-1] + 1)):
        fail('the first year whose transportation the state reimbursed is FY%d, not FY2021; the '
             'board member\'s table marks FY2021' % change_fy)
    # Fund 2640 and the special education grant funds, as the annual reports' special revenue
    # schedule prints their disbursements (each row ties to the page's printed totals).
    # Named as the reports print them: the IDEA grants (94-142 #240, preschool #262 and its
    # 99-457 predecessor, ARRA and ARP IDEA), the program improvement grants (#274, #298),
    # and the other grants the reports label special education. Not the kindergarten grants.
    GRANT_RE = re.compile(r'#\s*(240|262|252|264|274|298)\b|94-142|99-457|\bIdea\b|\bSPED\b'
                          r'|^Early Childhood Program Improvement$', re.I)
    srr_cb, srr_gr = {}, {}
    for r in csv.DictReader(open(os.path.join(ROOT, 'sources', 'data', 'special-revenue-read.csv'),
                                 encoding='utf-8')):
        y = int(r['fy'])
        if r['row_ties'] != 'yes':
            continue
        if r['fund'] == '50/50 Grant Sped Tuitions':     # fund 2640, as the report names it
            srr_cb[y] = num_(r['disbursements'])
        elif GRANT_RE.search(r['fund']):
            srr_gr[y] = srr_gr.get(y, 0.0) + num_(r['disbursements'])
    if abs(srr_cb[EY[0]] - cents_cb[EY[0]]) > 0.005:
        fail('FY%d: fund 2640 disbursements in the annual report (%s) and the journal (%s) no '
             'longer tie to the cent' % (EY[0], srr_cb[EY[0]], cents_cb[EY[0]]))
    gr_gap = srr_gr[EY[0]] - cents_gr[EY[0]]
    if abs(gr_gap) > 2000:
        fail('FY%d: grant disbursements in the annual report and the journal are %.2f apart; '
             'the note says about a thousand' % (EY[0], gr_gap))
    # ONE FIGURE FOR ONE QUANTITY ON THIS PAGE. For FY2023-FY2026 every table reads the lines
    # footed from cents (table 3's `every`, the same cents as the period-13 ledger, tied above);
    # before that, the ledger's own whole dollars. `vs` is that one set: (vote, spent) per line,
    # and the over, the net and the need below are all derived from it. The need must come out
    # as the series the statistics were taken from, or the build stops.
    vs = {}
    for r in led:
        y = r['fy']
        vs[y] = ({g: (every[y][g][0], every[y][g][1]) for g in LINES} if y in every
                 else {g: (r[g]['original'], r[g]['spent']) for g in LINES})
    over_of = {y: {g: vs[y][g][1] - vs[y][g][0] for g in LINES} for y in vs}
    net_of = {y: sum(over_of[y].values()) for y in vs}
    for r in sur:
        if sum(max(0, x) for x in over_of[r['fy']].values()) != r['need']:
            fail('FY%d: the need from the footed lines is not the series the statistics use'
                 % r['fy'])
    for y in every:
        if net_of[y] != every[y]['all'][1] - every[y]['all'][0]:
            fail('FY%d: the footed lines do not add to the year\'s total' % y)
    bm = {}
    for y in range(BM0, BM1 + 1):
        lg = next(r for r in led if r['fy'] == y)
        if y in every:
            e = every[y]['all']
            bm[y] = dict(vote=e[0], gf=e[1], allf=e[4], basis='journal')
        else:
            gf = sum(lg[g]['spent'] for g in LINES)
            if (y in srr_cb) != (y in srr_gr):
                fail('FY%d: the annual report holds fund 2640 or the grants, not both' % y)
            if y in srr_cb:
                o, c = C.footed([srr_cb[y], srr_gr[y]])
                allf, basis = gf + c, 'annual report'
            else:
                allf, basis = None, 'none'
            bm[y] = dict(vote=sum(lg[g]['original'] for g in LINES), gf=gf, allf=allf, basis=basis)
    SRR0 = min(srr_cb)
    if [y for y in bm if bm[y]['basis'] == 'none'] != list(range(BM0, SRR0)):
        fail('a year inside the special revenue schedules\' span has no every-fund figure')
    BM_MARK = {'cb': '†', 'idea': '‡', 'allf': '§', 'change': '*'}
    need_of = {r['fy']: r['need'] for r in sur}       # the same series as the chart and the SD
    for y in range(BM0, BM1 + 1):
        if need_of[y] < max(0, bm[y]['gf'] - bm[y]['vote']) - 2:
            fail('FY%d: the need is below the net overrun; adding only overruns cannot do that' % y)
    for y in bm:
        if net_of[y] != bm[y]['gf'] - bm[y]['vote']:
            fail('FY%d: the ten-year table\'s net is not its own two columns' % y)
    bm_rows = [dict(
        label=C.fy(y) + (BM_MARK['change'] if y == change_fy else ''),
        cells=[C.usd(bm[y]['vote']),
               (C.usd(idea_bm[y]) + (' ' + BM_MARK['idea'] if y in no262 else ''))
               if y in idea_bm else None,
               C.usd(cb_all[y]) + (' ' + BM_MARK['cb'] if y in cb_extra else ''),
               C.usd(bm[y]['gf']),
               (C.usd(bm[y]['allf']) + (' ' + BM_MARK['allf'] if bm[y]['basis'] == 'annual report'
                                        else '')) if bm[y]['allf'] is not None else None,
               # what he is trying to calculate (TJ): the general fund against its vote, net,
               # and the page's own need -- the series the average and SD are taken from
               C.usd(net_of[y]),
               C.usd(need_of[y])])
        for y in range(BM1, BM0 - 1, -1)]
    bm_table = dict(caption='Budget, IDEA, circuit breaker and actual costs, %s to %s'
                    % (C.fy(BM0), C.fy(BM1)), views=[dict(
        key='years', label='Each year', total_col=6, kinds=['ledger'] * 7,
        columns=['Special Education Operational Budget (general fund vote)',
                 'IDEA Grant Funding (allocated)', 'Circuit Breaker Funding (received)',
                 'Actual Costs, general fund', 'Actual Costs, every fund',
                 'General fund over (under) its vote', 'Needed beyond the vote'],
        rows=bm_rows,
        note=('The first three columns do not add up to anything: the budget is net, voted after '
              'the circuit breaker and grants it expected. * %s: DESE’s file prints a '
              'transportation reimbursement for the first time, for every district, in %s, '
              'paying %s costs. A dash is a year a source does not reach: DESE\u2019s allocation '
              'pages begin at %s, and the annual reports\u2019 special revenue schedules read '
              'here at %s. Budget and general fund cover in district, out-of-district '
              'tuition and transportation; actual is payments plus what was still owed (before %s, '
              'the Finance Committee workbook’s actual, which does not say). IDEA is '
              'DESE’s allocation (0240 school age plus 0262 preschool); %s for %s the file '
              'holds 0240 only; %s’s '
              'one-time ARP IDEA, %s, is not in it. %s includes extra relief or supplemental '
              'payments (%s); it is by year paid. %s Every fund before %s adds the annual '
              'reports’ disbursements from the circuit breaker account and the special '
              'education grants: payments only. In %s the two ways differ by %s on grants and '
              'not at all on the circuit breaker. Needed beyond the vote adds each line\u2019s '
              'overrun without offsetting another line\u2019s underspend, so it can exceed the '
              'net difference beside it; the reserve statistics on this page use it.')
             % (C.fy(change_fy), C.fy(st_tr[0]), C.fy(change_fy), C.fy(IDEA0), C.fy(SRR0),
                C.fy(EY[0]), BM_MARK['idea'],
                ' and '.join(C.fy(y) for y in no262), ', '.join(C.fy(y) for y in arp),
                ', '.join(C.usd(arp[y]) for y in sorted(arp)), BM_MARK['cb'],
                ', '.join(C.fy(y) for y in cb_extra), BM_MARK['allf'], C.fy(EY[0]),
                C.fy(EY[0]), C.usd(abs(gr_gap))))])

    out['special-education-overruns'] = TP.page(
        'special-education-overruns',
        # Reopened 26 October 2026 on what the table shows (TJ: the SERF pages "seem to have
        # different numbers"): the average led here and nowhere else, and it is a sizing
        # method, which Reserve options now carries beside the other six.
        'A special education line ran over its vote in %s of %s years; the worst, %s, by %s.'
        % (C.num(need['years_needing']), C.num(nyrs), C.fy(need['worst']['fy']),
           C.usd(need['worst']['gross'])),
        [f('mean', U(avg), 'needed in an average year', 'published'),
         f('sd', U(sd), 'standard deviation, year to year', 'published'),
         f('lvl1', U(lv1), 'average + 1 SD: enough in %s of %s years'
           % (C.num(cov(lv1)), C.num(nbad)), 'published',
           {'a': N(cov(lv1)), 'n': N(nbad)}, allow=('1 SD',)),
         f('lvl2', U(lv2), 'average + 2 SD: enough in %s of %s years'
           % (C.num(cov(lv2)), C.num(nbad)), 'published',
           {'a': N(cov(lv2)), 'n': N(nbad)}, allow=('2 SD',)),
         f('worst', U(need['worst']['gross']), 'needed in the worst year, %s'
           % C.fy(need['worst']['fy']), 'published', {'y': F(need['worst']['fy'])}),
         f('two', U(two[1]), 'worst two years running, %s and %s'
           % (C.fy(two[0]), C.fy(two[0] + 1)), 'published',
           {'y': F(two[0]), 'z': F(two[0] + 1)}),
         f('cap', U(rs['cap']), 'the reserve’s legal cap', 'statute'),
         f('needing', N(need['years_needing'], 'years'), 'of %s when a line ran over its vote'
           % C.num(nyrs), 'published', {'n': N(nyrs)}),
         f('netover', N(netover, 'years'), 'of %s when all three together ran over'
           % C.num(nyrs), 'published', {'n': N(nyrs)}),
         f('oodover', N(pl['ood']['years_over'], 'years'), 'of %s when tuition ran over its vote'
           % C.num(nyrs), 'published', {'n': N(nyrs)}),
         f('cbyr', U(cbs[worst_b['fy']]), 'paid by the circuit breaker account, %s'
           % C.fy(worst_b['fy']), 'published', {'y': F(worst_b['fy'])}),
         f('upper', U(worst_b['before']), '%s need, had it paid no tuition (ours)'
           % C.fy(worst_b['fy']), 'estimate', {'y': F(worst_b['fy'])})],
        [con('The worst year, %s, needed %s; the worst two running, %s and %s, needed %s.'
             % (C.fy(need['worst']['fy']), C.usd(need['worst']['gross']), C.fy(two[0]),
                C.fy(two[0] + 1), C.usd(two[1])),
             ['worst', 'two', 'cap'],
             {'y': F(need['worst']['fy']), 'a': U(need['worst']['gross']), 'w': F(two[0]),
              'z': F(two[0] + 1), 'b': U(two[1])},
             notes=[step('The cap is G.L. c.40 §13E’s: 2%% of net school spending. What the '
                         'reserve holds is not published.', 'gap', allow=('40', '13E', '2%'),
                         closes='the amount voted into the reserve')]),
         con('A line ran over its vote in %s of %s years; the three lines together, in only %s.'
             % (C.num(need['years_needing']), C.num(nyrs), C.num(netover)),
             ['needing', 'netover', 'oodover'],
             {'a': N(need['years_needing']), 'n': N(nyrs), 'b': N(netover)},
             notes=[step('Not set out: whether money moves between lines before the reserve is '
                         'drawn. In %s years an overrun sat inside a total that came in under.'
                         % C.num(hidden), 'gap', {'h': N(hidden)},
                         closes='the Special Education Reserve Fund policy, on the Select Board '
                                'agenda for 27 October 2026', allow=('27 October 2026',))]),
         con('Average plus two standard deviations, %s, would have met %s of %s bad years; plus one, %s.'
             % (C.usd(lv2), C.num(cov(lv2)), C.num(nbad), C.num(cov(lv1))),
             ['mean', 'sd', 'lvl1', 'lvl2'],
             {'a': U(lv2), 'k': N(cov(lv2)), 'n': N(nbad), 'b': N(cov(lv1))},
             notes=[step('%s years needed nothing, so counting the years covered assumes no bell '
                         'curve.' % C.num(sum(1 for x in vals if x == 0)),
                         'gap', {'z': N(sum(1 for x in vals if x == 0))},
                         closes='a longer record: the same ledger lines before %s' % fy0,
                         allow=(fy0,))]),
         con('In %s the circuit breaker account paid %s; without it, the need was %s.'
             % (C.fy(worst_b['fy']), C.usd(cbs[worst_b['fy']]), C.usd(worst_b['before'])),
             ['cbyr', 'upper', 'cap'],
             {'y': F(worst_b['fy']), 'a': U(cbs[worst_b['fy']]), 'b': U(worst_b['before'])},
             notes=[step('In %s the circuit breaker paid by one year-end entry, so the need turns '
                         'partly on how much was charged to it at the close.'
                         % C.fy(SC['last_fy']), 'gap', {'y': F(SC['last_fy'])},
                         closes='the district’s circuit breaker spending plan for each year, '
                                'set before the year began')])],
        chart=TP.series('Needed beyond the voted budget, each year',
                        [C.fy(r['fy']) for r in sur], [
                            TP.track('Needed beyond the vote', vals, 'published'),
                            TP.track('Average', [avg] * nyrs, 'published'),
                            TP.track('Average + 1 SD', [lv1] * nyrs, 'published'),
                            TP.track('Average + 2 SD', [lv2] * nyrs, 'published')],
                        '$', kind='line', reference=(rs['cap'], 'The most the reserve may hold'),
                        note='General fund only, %s to %s: each line’s spending above its vote, '
                             'added up. Grants and the circuit breaker account are not in it.'
                             % (fy0, fy1),
                        note_figures={'y': F(sur[0]['fy']), 'z': F(sur[-1]['fy'])}),
        table=bm_table,
        tables=[dict(caption='Voted and spent, general fund, each line, every year', views=[
            dict(key='voted-spent', label='Each year', total_col=-1, kinds=['ledger'] * 7,
                 columns=['In-district, voted', 'In-district, spent', 'Tuition, voted',
                          'Tuition, spent', 'Transport, voted', 'Transport, spent', 'Read from'],
                 rows=[dict(label=C.fy(r['fy']),
                            cells=[C.usd(vs[r['fy']][g][i]) for g in LINES for i in (0, 1)]
                            + ['MUNIS' if r['source'] == 'munis' else 'FinCom sheet'])
                       for r in reversed(led)],
                 note='From %s the three lines are rounded once from cents so they add to the '
                      'year\u2019s total. Read from: the Town’s MUNIS year-end report, or the Finance Committee’s '
                      'history workbook. Voted is the budget voted before the year; spent is expended plus what was '
                      'still owed at the close. In-district is every other special education '
                      'account. The Finance Committee’s workbook is used before %s because its '
                      'rows match the MUNIS reports in the years both hold.'
                      % (C.fy(SC['munis_first_fy']), C.fy(SC['munis_first_fy'])))]),
            dict(caption='Over or under the vote, and the need it leaves', views=[
                dict(key='over', label='Each year', total_col=3, kinds=['ledger'] * 5,
                     columns=['In-district', 'Tuition', 'Transport', 'Needed', 'All three, net'],
                     rows=[dict(label=C.fy(r['fy']),
                                cells=[C.usd(over_of[r['fy']][g]) for g in LINES]
                                + [C.usd(r['need']), C.usd(net_of[r['fy']])])
                           for r in reversed(sur)],
                     note='Each line: spent at the close less the vote; negative is under. Needed '
                          'adds only the lines that ran over; net adds all three. Ledger figures; '
                          'the subtraction is ours.')]),
            dict(caption='Every fund that paid, %s to %s' % (C.fy(EY[0]), C.fy(EY[-1])), views=[
                dict(key='fy%d' % y, label=C.fy(y), total_col=5, kinds=['ledger'] * 6,
                     columns=['Voted, general fund', 'General fund spent', 'General fund over',
                              'Circuit breaker', 'Grants', 'Every fund spent'],
                     rows=[dict(label=lab, cells=[C.usd(e[0]), C.usd(e[1]), C.usd(e[1] - e[0]),
                                                  C.usd(e[2]), C.usd(e[3]), C.usd(e[4])])
                           for lab, e in (('In-district', every[y]['indist']),
                                          ('Out-of-district tuition', every[y]['ood']),
                                          ('Transportation', every[y]['trans']),
                                          ('All three', every[y]['all']))],
                     note='The school journal, as /special-education/sped-all-funds reads it. '
                          'In-district is contracted services, staff pay and supplies. Only the '
                          'general fund has a vote. Each column is rounded once from cents, so its '
                          'parts add to its total, and every table on this page prints the same '
                          'dollars.'
                          + (' %s is the last year in the run.' % C.fy(y) if y == EY[-1] else ''))
                for y in reversed(EY)]),
            dict(caption='Reserve levels, and the years each would have met', views=[
                dict(key='levels', label='Levels', total_col=0, kinds=['ledger'] * 4,
                     columns=['Amount', 'Bad years met', 'Bad years short', 'Two years running met'],
                     rows=[dict(label=l, cells=[C.usd(v), '%s of %s' % (cov(v), nbad),
                                                C.num(nbad - cov(v)),
                                                '%s of %s' % (cov2(v), len(pairs))])
                           for l, v in [
                               ('Average', avg), ('Average + 1 SD', lv1), ('Average + 2 SD', lv2),
                               ('Worst single year, %s' % C.fy(need['worst']['fy']), max(vals)),
                               ('Worst two years running, %s-%s'
                                % (C.fy(two[0]), C.fy(two[0] + 1)), two[1]),
                               ('The most the reserve may hold', rs['cap'])]],
                     note='Average and standard deviation of the %s yearly needs: the sample '
                          'standard deviation, dividing by one fewer than the number of years. '
                          'Two years running: each pair of consecutive years, for a reserve not '
                          'refilled between them. Our arithmetic on the ledger.' % nyrs)]),
            dict(caption='Money that came in beside it, by year', views=[
                dict(key='in', label='Each year', total_col=-1, kinds=['ledger'] * 3,
                     columns=['Circuit breaker, the state’s quarterly payments',
                              'Circuit breaker, received in the town’s books',
                              'IDEA grant, allocated'],
                     rows=[dict(label=C.fy(y), cells=[
                         C.usd(paid[y]) if y in paid else None,
                         C.usd(recd[y]) if y in recd else None,
                         C.usd(idea[y]) if y in idea else None]) for y in reversed(inys)],
                     note='Receipts and an award, not spending on any line, so never subtracted '
                          'from the need. The state’s payment is by year paid, and reimburses '
                          'the year before; the town books it when received. DESE lists extra '
                          'relief or supplemental payments separately in %s; they are not in the '
                          'first column. IDEA is the '
                          'entitlement grant (code 0240), spent over more than one year. The '
                          'district\u2019s deck to the Finance Committee of 22 October 2026 states '
                          'the same %s allocation, and that the reserve is separate from the '
                          'circuit breaker.' % (', '.join(C.fy(y) for y in extra_yrs),
                                                C.fy(max(idea))))])],
        said=[said(SC, 'establish'), said(SC, 'urgency'),
              dict(quote=mo['quote'], board=mo['board'], date=mo['date'], href=mo['cite'],
                   caption=True, label='%s, %s, video at %s (machine captions)'
                   % (mo['board'], mo['date'], mo['at']))],
        sources=S('glytdbud-expense-fy2026-p13-gf-school.xlsx',
                  'glytdbud-expense-fy2026-p13-special-school.xlsx',
                  'general-fund-budget-vs-actuals-history.xlsx',
                  '4130-fy-2025-annual-town-report.txt', 'dese-circuit-breaker.xlsx')
        + [s_ for s_ in AFP['sources'] if s_['href'].startswith('/docs/data/munis-school-journal')]
        + [dict(label='Massachusetts DESE — entitlement grant allocations, by district '
                      '(dese-entitlement-allocations.csv)',
                href='/docs/data/dese-entitlement-allocations.csv'),
           dict(label='Lunenburg Public Schools — special education funding, a guide for the '
                      'Finance Committee, 22 October 2026 (as presented)', href='/docs/' + DECK),
           dict(label='Special education, all funds (how the journal figures are built)',
                href='/special-education/sped-all-funds')],
        finding_figures={'k': N(need['years_needing']), 'n': N(nyrs), 'y': F(need['worst']['fy']), 'b': U(need['worst']['gross'])})

    # ------------------------------------------------ children with a plan
    cnt = {r['fy']: r for r in ST['counts']}
    s1, s0 = ST['last'], ST['lowest']
    if s1['swd'] - s0['swd'] != ST['change_count']:
        fail('sped-students.json: change_count no longer matches the two years')
    held_share = 100.0 * s1['swd'] / s0['enrolled']
    gap3 = {r['fy']: r for r in ST['third_count_gap']}
    mv = {r['fy']: r for r in ST['third_count']}
    if not mv[2025]['repeats_prior_year']:
        fail('the movement file’s FY2025 row no longer repeats FY2024')
    out['students-with-an-iep'] = TP.page(
        'students-with-an-iep',
        '%s Lunenburg children had a special education plan in %s, %s of those enrolled.'
        % (C.num(s1['swd']), C.fy(s1['fy']), C.pct(s1['share_pct'])),
        [f('swd1', N(s1['swd'], 'children'), 'with a plan, %s' % C.fy(s1['fy']), 'published',
           {'y': F(s1['fy'])}),
         f('share1', P(s1['share_pct']), 'of enrolment, %s' % C.fy(s1['fy']), 'published',
           {'y': F(s1['fy'])}),
         f('swd0', N(s0['swd'], 'children'), 'with a plan, %s, the lowest' % C.fy(s0['fy']),
           'published', {'y': F(s0['fy'])}),
         f('share0', P(s0['share_pct']), 'of enrolment, %s' % C.fy(s0['fy']), 'published',
           {'y': F(s0['fy'])}),
         # NOT the headcount. The file's denominator is its own "Total In- and
         # Out-of-District Students" row, which reads 1,581 for FY2026 where DESE's
         # 1 October headcount reads 1,568. Labelled as what it is.
         f('enr1', N(s1['enrolled'], 'children'), 'in and out of district, %s' % C.fy(s1['fy']),
           'published', {'y': F(s1['fy'])}),
         f('enr0', N(s0['enrolled'], 'children'), 'in and out of district, %s' % C.fy(s0['fy']),
           'published', {'y': F(s0['fy'])}),
         f('held', P(held_share), 'the %s share at %s enrolment (ours)'
           % (C.fy(s1['fy']), C.fy(s0['fy'])), 'estimate', {'y': F(s1['fy']), 'z': F(s0['fy'])}),
         f('prog25', N(gap3[2025]['program'], 'children'), 'with a plan, %s, DESE program file'
           % C.fy(2025), 'published', {'y': F(2025)}),
         f('mov25', N(gap3[2025]['movement'], 'children'), 'with a plan, %s, DESE movement file'
           % C.fy(2025), 'published', {'y': F(2025)}),
         f('need-gap', None, 'whether more children need services, or more are found', 'gap',
           closes='the district’s referral, evaluation and eligibility counts by year')],
        [con('%s children had a plan in %s against %s in %s, while enrolment fell.'
             % (C.num(s1['swd']), C.fy(s1['fy']), C.num(s0['swd']), C.fy(s0['fy'])),
             ['swd1', 'swd0', 'enr1', 'enr0'],
             {'a': N(s1['swd']), 'y': F(s1['fy']), 'b': N(s0['swd']), 'z': F(s0['fy'])}),
         con('The share rose from %s to %s; at %s enrolment it would read %s.'
             % (C.pct(s0['share_pct']), C.pct(s1['share_pct']), C.fy(s0['fy']), C.pct(held_share)),
             ['share0', 'share1', 'held'],
             {'a': P(s0['share_pct']), 'b': P(s1['share_pct']), 'y': F(s0['fy']),
              'c': P(held_share)}),
         con('Two DESE files count %s and %s children with a plan for %s.'
             % (C.num(gap3[2025]['program']), C.num(gap3[2025]['movement']), C.fy(2025)),
             ['prog25', 'mov25'],
             {'a': N(gap3[2025]['program']), 'b': N(gap3[2025]['movement']), 'y': F(2025)},
             notes=[step('The movement file’s %s row repeats %s’s exactly, and neither file '
                         'states its census date or who it includes.' % (C.fy(2025), C.fy(2024)),
                         'gap', {'y': F(2025), 'z': F(2024)},
                         closes='DESE’s SIMS submission detail for Lunenburg, stating the census '
                                'date and inclusion rule behind each count')]),
         con('A count of children with a plan is not established to be a measure of need.',
             ['swd1', 'need-gap'])],
        # Two DESE files count children with a plan and disagree every year they overlap
        # (rule 13a): two tracks, neither chosen.
        chart=(lambda prog, mov: TP.series(
            'Children with a plan, two DESE files', [C.fy(y) for y in _span(prog, mov)], [
                TP.track('Program file', [prog.get(y) for y in _span(prog, mov)], 'published'),
                TP.track('Movement file', [mov.get(y) for y in _span(prog, mov)], 'published')],
            'children',
            note='The movement file’s %s row repeats %s’s exactly; neither file states its census '
                 'date or who it includes.' % (C.fy(2025), C.fy(2024)),
            note_figures={'y': F(2025), 'z': F(2024)}))(
            {r['fy']: r['swd'] for r in ST['counts']}, {r['fy']: r['on_iep'] for r in ST['third_count']}),
        table=dict(caption='Children with a special education plan, by year', views=[dict(
            key='counts', label='DESE program file', total_col=-1, kinds=['ledger'] * 5,
            columns=['Enrolled', 'With a plan', 'Share', 'In district', 'Out of district'],
            rows=[dict(label=C.fy(r['fy']), cells=[C.num(r['enrolled']), C.num(r['swd']),
                                                    C.pct(r['share_pct']), C.num(r['in_district']),
                                                    C.num(r['out_of_district'])])
                  for r in sorted(ST['counts'], key=lambda r: -r['fy'])],
            note='Children, at DESE’s census date. Not dollars, not staff, not placements.')]),
        sources=S('dese-sped-program-characteristics.xlsx', 'dese-sped-movement.xlsx'),
        finding_figures={'n': N(s1['swd']), 'y': F(s1['fy']), 'p': P(s1['share_pct'])})

    # ------------------------------------------------ placements out of district
    pk, lw, la = RT['count_peak'], RT['count_low'], RT['count_last']
    tc = {r['fy']: r for r in RT['two_counts']}
    pool = {p['start']: p for p in RT['pooled']}
    sep, inc = pool['Substantially Separate Classroom'], pool['Inclusive Setting']
    if la['collaborative'] + la['day'] + la['residential'] != la['total']:
        fail('the latest placement count no longer ties to its parts')
    out['out-of-district-placements'] = TP.page(
        'out-of-district-placements',
        'The town counted %s children placed out of district in %s, against %s in %s.'
        % (C.num(la['total']), C.fy(la['fy']), C.num(pk['total']), C.fy(pk['fy'])),
        [f('c1', N(la['total'], 'children'), 'placed out of district, 1 March, %s' % C.fy(la['fy']),
           'published', {'y': F(la['fy'])}, allow=('1 March',)),
         f('cpk', N(pk['total'], 'children'), 'placed, %s, the highest' % C.fy(pk['fy']),
           'published', {'y': F(pk['fy'])}),
         f('clw', N(lw['total'], 'children'), 'placed, %s, the lowest' % C.fy(lw['fy']),
           'published', {'y': F(lw['fy'])}),
         f('coll', N(la['collaborative'], 'children'), 'in collaboratives, %s' % C.fy(la['fy']),
           'published', {'y': F(la['fy'])}),
         f('day', N(la['day'], 'children'), 'in day schools, %s' % C.fy(la['fy']), 'published',
           {'y': F(la['fy'])}),
         f('res', N(la['residential'], 'children'), 'in residential schools, %s' % C.fy(la['fy']),
           'published', {'y': F(la['fy'])}),
         f('agree', N(RT['two_counts_agree'], 'years'), 'of %s the state and town counts agree'
           % C.num(RT['two_counts_compared']), 'published', {'n': N(RT['two_counts_compared'])}),
         f('dese23', N(tc[2023]['dese'], 'children'), 'placed, %s, DESE’s count' % C.fy(2023),
           'published', {'y': F(2023)}),
         f('town23', N(tc[2023]['town'], 'children'), 'placed, %s, the town’s count' % C.fy(2023),
           'published', {'y': F(2023)}),
         f('sep', P(sep['ood_pct']), 'from a separate classroom to out of district, %s cohorts'
           % C.num(sep['years']), 'published', {'n': N(sep['years'])}),
         f('inc', P(inc['ood_pct']), 'from an inclusive setting to out of district', 'published'),
         f('span-gap', None, 'over how many years the state follows a child', 'gap',
           closes='DESE’s methodology note for the placement trajectory file, stating its '
                  'interval and cohort rule')],
        [con('The town’s count ran from %s in %s to %s in %s, and stood at %s in %s.'
             % (C.num(pk['total']), C.fy(pk['fy']), C.num(lw['total']), C.fy(lw['fy']),
                C.num(la['total']), C.fy(la['fy'])), ['cpk', 'clw', 'c1', 'coll', 'day', 'res'],
             {'a': N(pk['total']), 'y': F(pk['fy']), 'b': N(lw['total']), 'z': F(lw['fy']),
              'c': N(la['total']), 'x': F(la['fy'])},
             notes=[step('Fewer referrals, families moving, in-district programmes and children '
                         'ageing out all fit the fall. Nothing here tests which.', 'hypothesis')]),
         con('The state’s and the town’s counts agree in %s of %s years; %s read %s and %s.'
             % (C.num(RT['two_counts_agree']), C.num(RT['two_counts_compared']), C.fy(2023),
                C.num(tc[2023]['dese']), C.num(tc[2023]['town'])),
             ['agree', 'dese23', 'town23'],
             {'a': N(RT['two_counts_agree']), 'n': N(RT['two_counts_compared']), 'y': F(2023),
              'd': N(tc[2023]['dese']), 't': N(tc[2023]['town'])},
             notes=[step('The state counts in October and the town on 1 March, so a child '
                         'placed between them is in one count and not the other. Nothing here '
                         'tests whether that is all of it.', 'hypothesis', allow=('1 March',))]),
         con('%s of children starting in a separate room ended out of district, against %s from '
             'an inclusive one.' % (C.pct(sep['ood_pct']), C.pct(inc['ood_pct'])),
             ['sep', 'inc', 'span-gap'],
             {'a': P(sep['ood_pct']), 'b': P(inc['ood_pct'])},
             notes=[step('Selection fits it equally: children placed in a separate room were not '
                         'like the others to begin with. Nothing here separates the two.',
                         'hypothesis')])],
        # The town's count over fifteen years, and the state's beside it where it exists: two
        # counts of the same children on two different days (rule 13a), never merged.
        chart=(lambda town, dese: TP.series(
            'Children placed out of district', [C.fy(y) for y in _span(town, dese)], [
                TP.track('The town’s count, 1 March', [town.get(y) for y in _span(town, dese)],
                         'stated'),
                TP.track('DESE’s special education program file',
                         [dese.get(y) for y in _span(town, dese)], 'published')],
            'children',
            note='The town’s count is the Special Services report in each annual town report, '
                 'taken on 1 March. The two are set side by side and not reconciled.',
            note_allow=('1 March',)))(
            {r['fy']: r['total'] for r in RT['counts']}, {r['fy']: r['dese'] for r in RT['two_counts']}),
        table=dict(caption='Children placed out of district, by year', views=[
            dict(key='town', label='The town’s 1 March count', total_col=3, kinds=['stated'] * 4,
                 columns=['Collaborative', 'Day', 'Residential', 'All'],
                 rows=[dict(label=C.fy(r['fy']), cells=[
                     C.num(r['collaborative']) if r['collaborative'] is not None else None,
                     C.num(r['day']) if r['day'] is not None else None,
                     C.num(r['residential']) if r['residential'] is not None else None,
                     C.num(r['total'])]) for r in sorted(RT['counts'], key=lambda r: -r['fy'])],
                 note='The Special Services report in each annual town report, sourced to SIMS '
                      'Report 7. Early years count collaboratives inside day placements.'),
            dict(key='two', label='Two counts', total_col=-1, kinds=['stated', 'ledger', 'ledger'],
                 columns=['The town, 1 March', 'DESE, October', 'Difference'],
                 rows=[dict(label=C.fy(r['fy']), cells=[C.num(r['town']), C.num(r['dese']),
                                                         C.num(r['difference'])])
                       for r in sorted(RT['two_counts'], key=lambda r: -r['fy'])],
                 note='Two counts of the same children on two different days, set side by side.')]),
        said=[said(SC, 'nine'), said(RT, 'radar')],
        sources=S('placement-counts.csv', 'dese-sped-placement-trajectory.xlsx',
                  'dese-sped-program-characteristics.xlsx'),
        finding_figures={'a': N(la['total']), 'y': F(la['fy']), 'b': N(pk['total']),
                         'z': F(pk['fy'])})

    # ------------------------------------------------ hiring here instead of placing there
    out['hiring-versus-placing'] = TP.page(
        'hiring-versus-placing',
        'Placements fell while in-district budgets rose; nothing published shows one caused the '
        'other.',
        [f('h-pk', N(pk['total'], 'children'), 'placed out of district, %s' % C.fy(pk['fy']),
           'published', {'y': F(pk['fy'])}),
         f('h-last', N(la['total'], 'children'), 'placed out of district, %s' % C.fy(la['fy']),
           'published', {'y': F(la['fy'])}),
         f('h-ind25', U(tot25), 'in district, %s budget (our lines)' % C.fy(2025), 'estimate',
           {'y': F(2025)}),
         f('h-ind27', U(tot27), 'in district, %s balanced budget (our lines)' % C.fy(2027),
           'estimate', {'y': F(2027)}),
         f('h-tu26', U(ly['tuition_fy26']), 'tuition budgeted, %s' % C.fy(2026), 'published',
           {'y': F(2026)}),
         f('h-tu27', U(ly['tuition_fy27']), 'tuition budgeted, %s' % C.fy(2027), 'published',
           {'y': F(2027)}),
         f('avoid-gap', None, 'staff cost to keep one child in district', 'gap',
           closes='the district’s written basis, if one exists, for its claim that in-district '
                  'staff avoid placements')],
        [con('Placements fell from %s in %s to %s in %s, on the town’s own count.'
             % (C.num(pk['total']), C.fy(pk['fy']), C.num(la['total']), C.fy(la['fy'])),
             ['h-pk', 'h-last'],
             {'a': N(pk['total']), 'y': F(pk['fy']), 'b': N(la['total']), 'z': F(la['fy'])}),
         con('Our in-district lines rose from %s in %s to %s in %s, as tuition was budgeted down.'
             % (C.usd(tot25), C.fy(2025), C.usd(tot27), C.fy(2027)),
             ['h-ind25', 'h-ind27', 'h-tu26', 'h-tu27'],
             {'a': U(tot25), 'y': F(2025), 'b': U(tot27), 'z': F(2027)}),
         con('The two series barely overlap in time, and neither shows that hiring kept a child '
             'here.', ['h-last', 'h-ind25', 'avoid-gap'],
             notes=[step('The district argues in-district behavioural staff avoid costly '
                         'placements. That is stated intent; nothing published tests it, and '
                         'fewer referrals or families moving fit the same numbers.',
                         'hypothesis')])],
        # The two series the page sets side by side, each against its own value in the first
        # year both exist. Children and dollars are never one axis, and the chart says so.
        chart=_indexed('Placements and the paraprofessional line', [
            ('Children placed, the town’s count', {r['fy']: r['total'] for r in RT['counts']}),
            ('Paraprofessional budget line', {r['fy']: r['total'] for r in SP.PARA_SERIES})],
            min(set(r['fy'] for r in RT['counts']) & set(r['fy'] for r in SP.PARA_SERIES)),
            'Each as a percent of its own %s value (ours). Nothing here links the two, and a '
            'child is not a dollar.' % C.fy(min(set(r['fy'] for r in RT['counts'])
                                               & set(r['fy'] for r in SP.PARA_SERIES)))),
        sources=S('placement-counts.csv', 'fy27-proposals.xlsx', 'lps-budget-lines.csv'),
    )

    # ------------------------------------------------ the class-size rule
    pmt = RG['placement']
    if pmt['sub']['count'] != next(r['count'] for r in pmt['rows'] if r['label'] == 'Substantially Separate'):
        fail('sped-regulation.json: the substantially separate count disagrees with its row')
    if RG['silent_total'] != 0:
        fail('the regulation now names a limit on adults; the class-size page says it names none')
    young = next(b for b in RG['bands'] if b['band'] == 'Young children')
    tier_rows = [dict(label='%s, %s' % (t['band'], t['short'].lower()), cells=[
        C.num(t['students']), C.num(t['educators']), C.num(t['aides']), t['cite']])
        for t in sorted(RG['tiers'], key=lambda t: (t['band'], t['separateness_rank'], t['students']))]
    out['class-size-limits'] = TP.page(
        'class-size-limits',
        'A separate special education group may hold %s students to one educator, or %s with an '
        'aide.' % (C.num(RG['sub_cap']), C.num(RG['sub_aide_cap'])),
        [f('subcap', N(RG['sub_cap'], 'students'), 'most in a separate group, one educator',
           'statute'),
         f('subaide', N(RG['sub_aide_cap'], 'students'), 'most with an educator and an aide',
           'statute'),
         f('partcap', N(RG['part_cap'], 'students'), 'most in a partly separate group, two aides',
           'statute'),
         f('young', N(young['top'], 'students'), 'most in an integrated preschool class',
           'statute'),
         f('thresh', P(RG['threshold_pct'], 0), 'outside general education, above which it is separate',
           'statute'),
         f('adults', N(RG['silent_total'], 'limits'), 'the rule sets on adults in a room',
           'statute'),
         f('sep26', N(pmt['sub']['count'], 'children'), 'counted substantially separate, %s'
           % C.fy(pmt['fy']), 'published', {'y': F(pmt['fy'])}),
         f('all26', N(pmt['total'], 'children'), 'with a plan, %s' % C.fy(pmt['fy']), 'published',
           {'y': F(pmt['fy'])}),
         f('groups-gap', None, 'how many groups Lunenburg runs, and how large', 'gap',
           closes='the district’s list of special education groups by school and setting, with '
                  'students and staff, kept for DESE’s program approval')],
        [con('A separate group may not exceed %s students to one educator, or %s with an aide.'
             % (C.num(RG['sub_cap']), C.num(RG['sub_aide_cap'])), ['subcap', 'subaide', 'thresh'],
             {'a': N(RG['sub_cap']), 'b': N(RG['sub_aide_cap'])}),
         con('The more separate the group, the lower the cap: %s partly separate, %s fully.'
             % (C.num(RG['part_cap']), C.num(RG['sub_aide_cap'])), ['partcap', 'subaide', 'young'],
             {'a': N(RG['part_cap']), 'b': N(RG['sub_aide_cap'])}),
         con('The rule caps children, not adults: it sets %s limits on adults, and a plan can add '
             'aides.' % C.num(RG['silent_total']), ['adults'], {'n': N(RG['silent_total'])}),
         con('%s of %s children were counted substantially separate in %s; that is not a count '
             'of groups.' % (C.num(pmt['sub']['count']), C.num(pmt['total']), C.fy(pmt['fy'])),
             ['sep26', 'all26', 'groups-gap'],
             {'a': N(pmt['sub']['count']), 'b': N(pmt['total']), 'y': F(pmt['fy'])},
             notes=[step('The rule binds groups and the state counts children, so no staffing '
                         'number follows from anything published.', 'gap',
                         closes='the district’s list of special education groups, with the '
                                'students and staff assigned to each')])],
        # The rule itself, drawn: the most students each school-age tier allows. The separate
        # tiers are the finding, so they carry the highlight.
        chart=TP.ranking('School-age group-size limits', [
            ('%s, %s' % ('Separate' if t['separateness_rank'] == 2 else t['short'],
                         AIDES[t['aides']]), t['students'])
            for t in RG['tiers'] if t['band'] == 'School age'], 'students',
            highlight=['Separate, %s' % AIDES[t['aides']] for t in RG['tiers']
                       if t['band'] == 'School age' and t['separateness_rank'] == 2],
            note='603 CMR 28.06, school-age tiers. Every tier names one educator; an aide is what '
                 'raises the ceiling.', note_allow=('603 CMR 28.06',)),
        table=dict(caption='Group-size limits in 603 CMR 28.06', views=[dict(
            key='tiers', label='The regulation, tier by tier', total_col=-1,
            kinds=['statute'] * 4, columns=['Most students', 'Educators', 'Aides', 'Clause'],
            rows=tier_rows,
            note='Parsed from the sentences that state them. Every tier names one educator; an '
                 'aide is what raises the ceiling.')]),
        said=[said(RG, 'noformula'), said(RG, 'pullout')],
        sources=S('603cmr28-special-education-regulations.html', 'sims-datahandbook-current.docx',
                  'dese-sped-program-characteristics.xlsx'),
        finding_figures={'a': N(RG['sub_cap']), 'b': N(RG['sub_aide_cap'])})

    # ------------------------------------------------ the hub
    h = {}
    h['h-total'] = f('h-total', U(last['total']), 'out-of-district tuition, every fund, %s'
                     % C.fy(y25), 'published', {'y': F(y25)})
    h['h-gf'] = f('h-gf', U(last['gen_fund']), 'of it from the general fund, %s' % C.fy(y25),
                  'published', {'y': F(y25)})
    h['h-ind'] = f('h-ind', U(tot27), 'in district, %s balanced budget (our lines)' % C.fy(2027),
                   'estimate', {'y': F(2027)})
    h['h-worst'] = f('h-worst', U(need['worst']['gross']), 'beyond the voted budget, worst year, %s'
                     % C.fy(need['worst']['fy']), 'published', {'y': F(need['worst']['fy'])})
    h['h-paid'] = f('h-paid', U(c26['paid']), 'circuit breaker paid by the state, %s'
                    % C.fy(c26['fy']), 'published', {'y': F(c26['fy'])})
    h['h-thresh'] = f('h-thresh', U(c26['threshold']), 'threshold taken off first, %s'
                      % C.fy(c26['fy']), 'published', {'y': F(c26['fy'])})
    h['h-acct'] = f('h-acct', U(a26['closing']), 'in the circuit breaker account, close of %s'
                    % C.fy(2026), 'published', {'y': F(2026)})
    h['h-swd'] = f('h-swd', N(s1['swd'], 'children'), 'with a special education plan, %s'
                   % C.fy(s1['fy']), 'published', {'y': F(s1['fy'])})
    h['h-placed'] = f('h-placed', N(la['total'], 'children'), 'placed out of district, %s'
                      % C.fy(la['fy']), 'published', {'y': F(la['fy'])})
    h['h-tu27'] = f('h-tu27', U(ly['tuition_fy27']), 'tuition budgeted, %s, down %s'
                    % (C.fy(2027), C.pct(cutp, 0)), 'published', {'y': F(2027), 'p': P(cutp, 0)})
    h['h-price'] = f('h-price', None, 'what one placement costs', 'gap',
                     closes='the district’s placement-level billing detail, gross of circuit '
                            'breaker')
    tiers = [
        LD.tier('What it costs', [h['h-total'], h['h-gf'], h['h-ind'], h['h-tu27'], h['h-price']]),
        LD.tier('What comes back', [h['h-paid'], h['h-thresh'], h['h-acct']]),
        LD.tier('Children and surprises', [h['h-swd'], h['h-placed'], h['h-worst']]),
    ]
    hub_ladder = LD.ladder(tiers, [
        LD.conclusion('Out-of-district tuition was %s in %s; the general fund paid %s of it.'
                      % (C.usd(last['total']), C.fy(y25), C.usd(last['gen_fund'])),
                      ['h-total', 'h-gf'],
                      {'a': U(last['total']), 'y': F(y25), 'b': U(last['gen_fund'])}),
        LD.conclusion('The state repaid %s in %s, after taking %s off the top.'
                      % (C.usd(c26['paid']), C.fy(c26['fy']), C.usd(c26['threshold'])),
                      ['h-paid', 'h-thresh', 'h-acct'],
                      {'a': U(c26['paid']), 'y': F(c26['fy']), 'b': U(c26['threshold'])}),
        LD.conclusion('In the worst of %s years special education needed %s beyond its voted '
                      'budget.' % (C.num(nyrs), C.usd(need['worst']['gross'])), ['h-worst'],
                      {'n': N(nyrs), 'a': U(need['worst']['gross'])}),
        LD.conclusion('%s children had a plan in %s; %s were placed out of district in %s.'
                      % (C.num(s1['swd']), C.fy(s1['fy']), C.num(la['total']), C.fy(la['fy'])),
                      ['h-swd', 'h-placed'],
                      {'a': N(s1['swd']), 'y': F(s1['fy']), 'b': N(la['total']), 'z': F(la['fy'])}),
        LD.conclusion('Nothing published says what one placement costs, so no per-child figure '
                      'here is a price.', ['h-price', 'h-tu27', 'h-ind']),
    ])
    out['special-education'] = TP.hub(
        'special-education',
        'Out-of-district tuition was %s in %s, and %s of it was paid outside the general fund. '
        'The state repaid %s in %s through the circuit breaker, a year after the costs.'
        % (C.usd(last['total']), C.fy(y25), C.pct(last['outside_share_pct']), C.usd(c26['paid']),
           C.fy(c26['fy'])),
        # The hub's answer is tuition by who paid it and the circuit breaker coming back: the
        # registry chart that draws exactly that, by fund, with the state's payments beside.
        hub_ladder, chart=dict(id='special-education-costs-circuit-breaker', source=COSTS),
        table=tuition_table,
        answer_figures={'a': U(last['total']), 'y': F(y25), 'p': P(last['outside_share_pct']),
                        'b': U(c26['paid']), 'z': F(c26['fy'])})

    if sorted(k for k in out if k != 'special-education') != sorted(MINE):
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
        print('special education topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
