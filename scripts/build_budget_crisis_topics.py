#!/usr/bin/env python3
"""The Budget crisis shelf: the /crisis walkthrough (fy28/src/pages/Walkthrough.tsx) broken into
a hub and topic pages, one question each.

    python3 scripts/build_budget_crisis_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_budget_crisis_topics.py --check   # fail if any output would change

WHY. TJ, 18 October 2026: the walkthrough is ~10,000 words in eleven rooms; residents should be
able to look straight at one piece of it. Each room's question is a page here, or a page another
shelf already answers and the registry LISTS here (scripts/topic_registry/budget_crisis.py has
the room-by-room map). Nothing is copied.

WHERE EACH FIGURE COMES FROM.

  fy28/public/data/model.json   everything. Its `fy27`, `expenseBase` and `assumptions` are the
                                Python model's (model/finance.py, written by model/export.py);
                                `programs` and `levers` the catalogue; `taxBase` the tax base
                                and the DLS new-growth series; `facts` the FY27 record.
  the projection, PORTED        The walkthrough computes in TypeScript (fy28/src/model/rates.ts,
                                answers.ts, walk.ts). The pieces these pages need are short exact
                                formulas over model.json -- run(), nextYear(), the bisections for
                                the state-aid and new-growth rates, the attribution -- and are
                                ported below line for line. Two checks hold the port honest,
                                every run: run()'s gaps must equal model.json freeCash.deficits,
                                which model/finance.py wrote (the Python engine), and every value
                                these pages print must equal what the TypeScript produces, run
                                read-only through esbuild and node (ts_values, below).

RULE 3. Everything the projection yields is OUR estimate and is kinded `estimate`; the rates
it runs on are assumptions this project chose (model.json `assumptions`). The levy cap is
statute. The FY2027 appropriation, the restored salaries, state aid and new growth history
are published.

LEFT OUT, and why. The walkthrough's twelve priced "packages" (rates.ts PACKAGES, with
firstYearsFor and its solves) are a large scenario engine, not a short formula: not ported.
Its "the average home is a wash" comparison is not reproduced: taxBase.homesPerPupil is itself
derived as localCostPerPupil / schoolShareOfBill (model/taxbase.py), so "what a home pays"
against "what a home's pupils cost" is the same quantity divided back out -- equal by
construction, not by measurement (rule 13).
"""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
from brief import step  # noqa: E402

PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT_DIR = os.path.join(PUB, 'topics')
TS_MODEL = os.path.join(ROOT, 'fy28', 'src', 'model')
ESBUILD = os.path.join(ROOT, 'fy28', 'node_modules', '.bin', 'esbuild')
HUB = 'crisis'

MINE = [t for t, (_, home, gen) in REG.TOPICS.items()
        if home == HUB and gen == 'build_budget_crisis_topics.py']

LABELS = {    # the walkthrough's own names for the seven lines (rates.ts RATE_LINES)
    'salaries': 'Salaries', 'health': 'Health insurance',
    'sped': 'Special education, in district', 'transport': 'Transportation',
    'sped_tuition': 'Out-of-district special education', 'utilities': 'Utilities',
    'other': 'Everything else'}
BUCKETS = ['salaries', 'health', 'transport', 'sped', 'sped_tuition', 'utilities', 'other']
LONG = 30          # rates.ts LONG: the horizon the long-run revenue rate is read at
HORIZON = 6        # answers.ts GAPS: project(6)
DECADE = 10


def fail(msg):
    raise SystemExit('build_budget_crisis_topics: ' + msg)


def jsround(x):
    """Math.round, which rounds .5 up; Python's round() rounds it to even."""
    return math.floor(x + 0.5)


# --------------------------------------------------------------------- the projection, ported

class Model:
    def __init__(self, M):
        self.M = M
        self.A, self.F, self.E, self.T = M['assumptions'], M['fy27'], M['expenseBase'], M['taxBase']
        self.BASE = {k: self.E[k] + (self.F['stm_addbacks'] if k == 'salaries' else 0)
                     for k in BUCKETS}
        self.TOTAL = sum(self.BASE[k] for k in BUCKETS)
        self.RATES = {k: self.A[k] for k in BUCKETS}
        self.LEVY_CAP = self.A['levy_growth']

    def run(self, years, rates=None, new_growth=None, aid_growth=None):
        """rates.ts run() at the default scenario's levers (no cut, override, fee or free cash),
        which is also engine.ts project() and model/finance.py project()."""
        A, F = self.A, self.F
        rates = rates or self.RATES
        ng = A['new_growth'] if new_growth is None else new_growth
        ag = A['state_aid_growth'] if aid_growth is None else aid_growth
        b = dict(self.BASE)
        levy, aid, rec = F['levy_limit'], F['state_aid'], F['local_receipts']
        approp = F['lps_appropriation'] + F['stm_appropriation']
        wedge = (F['levy_limit'] + F['excluded_debt'] + F['state_aid'] + F['local_receipts']
                 - F['omnibus'])
        prev, out = F['omnibus'], []
        for i in range(years):
            levy = levy * (1 + A['levy_growth']) + ng
            aid *= 1 + ag
            rec *= 1 + A['local_receipts_growth']
            town = levy + F['excluded_debt'] + aid + rec - wedge
            growth = town / prev - 1
            prev = town
            approp = approp * (1 + growth) + A['override_amount']
            revenue = approp + A['athletic_fee_revenue']
            for k in BUCKETS:
                b[k] *= 1 + rates[k]
            cost = sum(b[k] for k in BUCKETS)
            out.append(dict(fy=2028 + i, cost=jsround(cost), revenue=jsround(revenue),
                            gap=jsround(cost - revenue), growth=growth))
        return out

    def blended(self, rates=None):
        rates = rates or self.RATES
        return sum(self.BASE[k] / self.TOTAL * rates[k] for k in BUCKETS)


def compute(M):
    m = Model(M)
    A, F, T = m.A, m.F, m.T
    o = {}
    base6 = m.run(HORIZON)
    eng = [jsround(d['amount']) for d in M['freeCash']['deficits']]
    if [y['gap'] for y in base6] != eng:
        fail('the ported run() no longer matches model.json freeCash.deficits (model/finance.py): '
             '%s vs %s' % ([y['gap'] for y in base6], eng))
    o['years'] = base6
    # answers.ts GAPS: cumulative, and the part new that year
    o['fresh'] = [jsround(y['gap'] if i == 0 else y['gap'] - base6[i - 1]['gap'] * (1 + y['growth']))
                  for i, y in enumerate(base6)]
    o['decade'] = m.run(DECADE)
    long = m.run(LONG)
    o['long'] = long
    o['blended'] = m.blended()
    o['target'] = long[-1]['growth']                       # longRunTarget
    o['rev28'] = base6[0]['growth']                        # BASELINE_REVENUE_GROWTH
    o['levy_cap'] = m.LEVY_CAP
    o['base'] = m.BASE
    o['total'] = m.TOTAL
    o['weights'] = {k: m.BASE[k] / m.TOTAL for k in BUCKETS}
    o['rates'] = m.RATES
    o['approp27'] = F['lps_appropriation'] + F['stm_appropriation']
    o['addbacks'] = F['stm_addbacks']
    o['enrollment'] = T['enrollment']

    # walk.ts LEVEL_SERVICE and rates.ts nextYear()
    g = base6[0]
    o['cost28'] = g['cost']
    o['increase'] = jsround(g['cost'] - m.TOTAL)
    allowed = g['revenue'] - o['approp27']
    o['allowed'] = jsround(allowed)
    d = dict(levy=F['levy_limit'] * A['levy_growth'], new_growth=A['new_growth'],
             aid=F['state_aid'] * A['state_aid_growth'],
             receipts=F['local_receipts'] * A['local_receipts_growth'])
    dtown = sum(d.values())
    o['sources'] = {k: jsround(v / dtown * allowed) for k, v in d.items()}
    o['line_amount'] = {k: jsround(m.BASE[k] * m.RATES[k]) for k in BUCKETS}
    o['line_share'] = {k: jsround(allowed * m.BASE[k] / m.TOTAL) for k in BUCKETS}
    o['line_multiple'] = {k: m.BASE[k] * m.RATES[k] / (allowed * m.BASE[k] / m.TOTAL)
                          for k in BUCKETS}
    o['consumed'] = sum(o['line_amount'].values()) / allowed     # nextYear(): costTotal / allowed

    # answers.ts ATTRIBUTION: each line held to the levy cap, the projection rerun
    o['contributes'] = {}
    for k in BUCKETS:
        r = dict(m.RATES)
        r[k] = m.LEVY_CAP
        o['contributes'][k] = g['gap'] - m.run(1, rates=r)[0]['gap']
    capped = m.run(HORIZON, rates={k: m.LEVY_CAP for k in BUCKETS})
    o['if_none_28'], o['if_none_32'] = capped[0]['gap'], capped[4]['gap']

    # rates.ts salaryRateToBalance and workforceShrink, with the walkthrough's clamp at zero
    w = o['weights']
    others = sum(w[k] * m.RATES[k] for k in BUCKETS if k != 'salaries')
    o['salary_to_balance'] = (o['target'] - others) / w['salaries']
    positions = []
    for p in M['programs']:
        positions += [p] * (p.get('repeatable') or 1)
    positions = [p for p in positions if p['fte'] > 0]
    o['cost_per_fte'] = jsround(sum(p['cost'] for p in positions)
                                / sum(p['fte'] for p in positions))
    line = max(o['salary_to_balance'], 0)
    contract = m.RATES['salaries']
    per_year = (1 + contract) / (1 + line) - 1
    o['shrink_line'] = line
    o['shrink_per_year'] = m.BASE['salaries'] * per_year / o['cost_per_fte']
    o['shrink_after20'] = 1 - ((1 + line) / (1 + contract)) ** 20

    # rates.ts aidGrowthToSustain (bisection) and ch70OnlyGrowth
    def holds(ag):
        y = m.run(LONG, aid_growth=ag)
        return o['blended'] <= y[-1]['growth'] + 0.0002 and y[-1]['gap'] <= 0
    lo, hi = A['state_aid_growth'], 0.30
    if not holds(hi):
        fail('no state aid rate up to 30% holds; the page would have nothing to say')
    for _ in range(60):
        mid = (lo + hi) / 2
        if holds(mid):
            hi = mid
        else:
            lo = mid
    o['aid_rate'] = hi
    ch70 = T['ch70']['aid']
    other = F['state_aid'] - ch70
    gr = 0
    for n in range(1, LONG + 1):
        need = F['state_aid'] * (1 + hi) ** n - other * (1 + A['state_aid_growth']) ** n
        if need > 0:
            gr = max(gr, (need / ch70) ** (1 / n) - 1)
    o['ch70_rate'] = gr
    o['ch70'] = ch70
    o['state_aid'] = F['state_aid']
    o['aid_assumed'] = A['state_aid_growth']
    o['aid_share_town'] = F['state_aid'] / F['omnibus']
    o['ch70_at_need'] = [ch70 * (1 + gr) ** n for n in range(1, DECADE + 1)]
    o['ch70_at_base'] = [ch70 * (1 + A['state_aid_growth']) ** n for n in range(1, DECADE + 1)]
    o['ch70_extra'] = jsround(sum(a - b for a, b in zip(o['ch70_at_need'], o['ch70_at_base'])))
    o['foundation'] = T['ch70']['foundationBudget']
    o['above_foundation'] = F['lps_appropriation'] - T['ch70']['foundationBudget']

    # answers.ts DEVELOPMENT: growthToHold (bisection) and devPlan
    def to_hold(years):
        lo, hi = 0, 20_000_000
        for _ in range(80):
            mid = (lo + hi) / 2
            if max(y['gap'] for y in m.run(years, new_growth=mid)) <= 0:
                hi = mid
            else:
                lo = mid
        return hi
    need = {n: to_hold(n) for n in (1, 5, 10)}
    o['ng_needed'] = jsround(need[5])
    o['ng_same_1_5_10'] = jsround(need[1]) == jsround(need[5]) == jsround(need[10])
    mix = next((a['value'] for a in T['archetypes'] if a['id'] == 'mix'), T['mixValue'])
    o['mix'] = mix
    o['ng_value'] = jsround((need[5] - T['currentNewGrowthRevenue']) * 1000 / T['rate'])
    o['ng_developments'] = ((need[5] - T['currentNewGrowthRevenue']) * 1000 / T['rate']) / mix
    o['ng_assumed'] = T['currentNewGrowthRevenue']
    d0 = m.run(1, new_growth=0)[0]['gap']
    d1 = m.run(1, new_growth=1_000_000)[0]['gap']
    o['share'] = (d0 - d1) / 1_000_000
    o['ng_history'] = T['newGrowthHistory']
    best = max(T['newGrowthHistory'], key=lambda h: h['amount'])
    o['ng_best'] = best
    o['ng_last'] = T['newGrowthHistory'][-1]

    # rates.ts CUT_OPTIONS and ALL_CUTS; answers.ts yearsCovered
    extra = [p for p in M['programs'] if p['cat'] in ('athletics', 'arts', 'activities')
             and p['status'] in ('funded', 'restoring')]
    extra_total = jsround(sum(p['cost'] for p in extra))
    ath = M['facts']['athleticsRemaining']
    admin = next(l for l in M['levers'] if l['id'] == 'admin_cut')
    lawful = [r for r in admin['rungs'] if not r['blocked']]
    tech = next(l for l in M['levers'] if l['id'] == 'tech_cut')
    o['cuts'] = dict(athletics=ath, extras=jsround(extra_total - ath), tech=jsround(tech['cap']),
                     admin=jsround(sum(r['amount'] for r in lawful)))
    o['tech_basis'], o['tech_max'] = tech['basis'], tech['max']
    o['admin_count'] = len(lawful)
    o['admin_blocked'] = len(admin['rungs']) - len(lawful)
    o['admin_fte'] = sum(r['fte'] for r in lawful)
    o['all_cuts'] = sum(o['cuts'].values())
    grow = m.RATES['other']
    n = 0
    for i, y in enumerate(base6):
        if o['all_cuts'] * (1 + grow) ** i >= y['gap']:
            n += 1
        else:
            break
    o['cuts_years'] = n
    o['cuts_growth'] = grow
    return o


# --------------------------------------------------------------------- the TypeScript, as a check

TS_ENTRY = """
import { MODEL, COST_GROWTH_BLENDED } from '%(m)s/engine'
import { LEVEL_SERVICE } from '%(m)s/walk'
import * as R from '%(m)s/rates'
import * as Q from '%(m)s/answers'
const N = R.nextYear()
const T = R.longRunTarget(R.DEFAULT_SCENARIO)
const aid = R.aidGrowthToSustain(R.DEFAULT_SCENARIO)
const sal = R.salaryRateToBalance(R.DEFAULT_RATES, T)
const shrink = R.workforceShrink(Math.max(sal, 0), R.DEFAULT_RATES.salaries)
console.log(JSON.stringify({
  blended: COST_GROWTH_BLENDED, target: T, rev28: R.BASELINE_REVENUE_GROWTH,
  gaps: Q.GAPS.map(g => g.cumulative), fresh: Q.GAPS.map(g => g.fresh),
  cost28: LEVEL_SERVICE.costsNextYear, increase: LEVEL_SERVICE.increase,
  allowed: N.allowed, sources: N.sources.map(s => s.toSchools),
  lines: Object.fromEntries(N.costs.map(c => [c.key, [c.amount, c.share, c.multiple]])),
  consumed: N.consumed,
  contributes: Object.fromEntries(Q.ATTRIBUTION.lines.map(l => [l.key, l.contributes])),
  ifNone: Q.ATTRIBUTION.ifNothingOutran,
  salary: sal, cpf: R.COST_PER_FTE, shrink: [shrink.positionsPerYear, shrink.after20],
  aid, ch70: R.ch70OnlyGrowth(aid), aboveFoundation: R.STATE_AID.aboveFoundation,
  share: R.SHARE, dev: [Q.DEVELOPMENT.fiveYear.needed, Q.DEVELOPMENT.fiveYear.value,
                        Q.DEVELOPMENT.fiveYear.developments, Q.DEVELOPMENT.oneYear.needed,
                        Q.DEVELOPMENT.tenYear.needed],
  cuts: R.CUT_OPTIONS.map(c => c.amount), allCuts: R.ALL_CUTS,
  cutsYears: Q.yearsCovered(R.ALL_CUTS, R.DEFAULT_RATES.other),
  run10: R.run(10, R.DEFAULT_SCENARIO).map(y => [y.cost, y.revenue]),
}))
"""


def ts_values():
    if not os.path.exists(ESBUILD):
        fail('fy28/node_modules/.bin/esbuild is missing; run npm install in fy28/')
    with tempfile.TemporaryDirectory() as tmp:
        entry = os.path.join(tmp, 'entry.ts')
        with open(entry, 'w', encoding='utf-8') as fh:
            fh.write(TS_ENTRY % {'m': TS_MODEL})
        js = subprocess.run([ESBUILD, entry, '--bundle', '--platform=node', '--format=esm',
                             '--log-level=error'], capture_output=True, text=True)
        if js.returncode:
            fail('esbuild could not bundle the projection:\n' + js.stderr)
        r = subprocess.run(['node', '--input-type=module'], input=js.stdout,
                           capture_output=True, text=True)
        if r.returncode:
            fail('node could not run the projection:\n' + r.stderr)
    return json.loads(r.stdout)


def parity(o, ts):
    """Every value these pages print, against the TypeScript the walkthrough renders."""
    def same(name, a, b):
        ok = (a == b) if isinstance(a, int) and isinstance(b, int) else abs(a - b) < 1e-9
        if not ok:
            fail('the Python port disagrees with the TypeScript on %s: %r vs %r' % (name, a, b))
    for name, a, b in [('blended', o['blended'], ts['blended']), ('target', o['target'], ts['target']),
                       ('rev28', o['rev28'], ts['rev28']), ('cost28', o['cost28'], ts['cost28']),
                       ('increase', o['increase'], ts['increase']),
                       ('allowed', o['allowed'], ts['allowed']), ('consumed', o['consumed'], ts['consumed']),
                       ('if none, FY2028', o['if_none_28'], ts['ifNone']['fy28']),
                       ('if none, FY2032', o['if_none_32'], ts['ifNone']['fy32']),
                       ('salary rate', o['salary_to_balance'], ts['salary']),
                       ('cost per FTE', o['cost_per_fte'], ts['cpf']),
                       ('positions a year', o['shrink_per_year'], ts['shrink'][0]),
                       ('after twenty', o['shrink_after20'], ts['shrink'][1]),
                       ('aid rate', o['aid_rate'], ts['aid']), ('ch70 rate', o['ch70_rate'], ts['ch70']),
                       ('above foundation', o['above_foundation'], ts['aboveFoundation']),
                       ('share', o['share'], ts['share']),
                       ('new growth needed', o['ng_needed'], ts['dev'][0]),
                       ('new value', o['ng_value'], ts['dev'][1]),
                       ('developments', o['ng_developments'], ts['dev'][2]),
                       ('all cuts', o['all_cuts'], ts['allCuts']),
                       ('years the cuts cover', o['cuts_years'], ts['cutsYears'])]:
        same(name, a, b)
    same('gaps', 0, 0 if [y['gap'] for y in o['years']] == ts['gaps'] else 1)
    same('fresh', 0, 0 if o['fresh'] == ts['fresh'] else 1)
    same('sources', 0, 0 if list(o['sources'].values()) == ts['sources'] else 1)
    same('cut options', 0, 0 if [o['cuts'][k] for k in ('athletics', 'extras', 'tech', 'admin')]
         == ts['cuts'] else 1)
    same('run10', 0, 0 if [[y['cost'], y['revenue']] for y in o['decade']] == ts['run10'] else 1)
    same('one, five, ten years', 0, 0 if o['ng_same_1_5_10'] == (ts['dev'][0] == ts['dev'][3]
                                                                  == ts['dev'][4]) else 1)
    for k in BUCKETS:
        same('line %s' % k, o['line_amount'][k], ts['lines'][k][0])
        same('share %s' % k, o['line_share'][k], ts['lines'][k][1])
        same('multiple %s' % k, o['line_multiple'][k], ts['lines'][k][2])
        same('contributes %s' % k, o['contributes'][k], ts['contributes'][k])


# --------------------------------------------------------------------- sources

def sources():
    pub = os.path.join(ROOT, 'fy28', 'public')
    spec = {
        'model': ('/data/model.json',
                  'Lunenburg Budget Project — model.json (the projection; ours)'),
        'method': ('/docs/analyses/show-your-work.md',
                   'Lunenburg Budget Project — show-your-work.md (every rate the projection uses)'),
        'lines': ('/docs/data/lps-budget-lines.csv',
                  'Lunenburg Budget Project — lps-budget-lines.csv (the FY27 budget, line by line)'),
        'newgrowth': ('/docs/data/dls-new-growth.csv',
                      'Lunenburg Budget Project — dls-new-growth.csv (the state’s certified new '
                      'growth, by year)'),
        'cherry': ('/docs/data/dls-cherry-sheet.csv',
                   'Lunenburg Budget Project — dls-cherry-sheet.csv (every cherry sheet line)'),
    }
    out = {}
    for k, (href, label) in spec.items():
        if not os.path.exists(os.path.join(pub, href.lstrip('/'))):
            fail('%s is not served from fy28/public' % href)
        out[k] = dict(href=href, label=label)
    import csv
    man = {r['key'] for r in csv.DictReader(open(os.path.join(ROOT, 'sources', 'data',
                                                              'archive-manifest.csv'),
                                                 encoding='utf-8'))}
    for k, key, label in [
            ('workbook', 'budget-workbooks/fy27-proposals.xlsx',
             'Lunenburg Public Schools — FY27 budget workbook — fy27-proposals.xlsx'),
            ('budget', 'district-budget/docs/final-budget-document.pdf',
             'Lunenburg Public Schools — FY27 budget document — final-budget-document.pdf')]:
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        out[k] = dict(href='/docs/' + key, label=label)
    return out


# --------------------------------------------------------------------- the pages

def build():
    M = json.load(open(os.path.join(PUB, 'model.json'), encoding='utf-8'))
    B = 2000 + int(M['meta']['base_year'][2:])      # 'FY27': the adopted budget the run starts from
    o = compute(M)
    parity(o, ts_values())
    src = sources()
    S = lambda *k: [src[x] for x in k]
    U = lambda v: figure(v, C.usd(v))
    F = lambda y: figure(y, C.fy(y), 'fiscal year')
    P = lambda x, dp=2: figure(x * 100, C.pct(x * 100, dp))      # x is a fraction
    # A RATE carries its period in the tile itself. TJ, 19 October 2026: "5.18%. Nobody knows
    # what that means" -- a bare percent reads as a share; '5.18% a year' cannot.
    PY = lambda x, dp=2: figure(x * 100, C.pct(x * 100, dp) + ' a year', 'percent a year')
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    D1 = lambda v, unit: figure(v, '%.1f %s' % (v, unit), unit)
    f, con = LD.fact, TP.conclusion
    out = {}

    Y = o['years']
    fy = [y['fy'] for y in Y]
    g28, g29, glast = Y[0]['gap'], Y[1]['gap'], Y[-1]['gap']
    f28, f29, flast = F(fy[0]), F(fy[1]), F(fy[-1])
    R, W = o['rates'], o['weights']
    if fy[0] != B + 1:
        fail('the projection no longer starts the year after model.json base_year')
    if not all(y['gap'] > 0 for y in o['long']):
        fail('the projection is no longer short in every year to FY%d; the hub says it is'
             % o['long'][-1]['fy'])
    if not all(o['fresh'][i] > 0 for i in range(len(Y))):
        fail('a year no longer adds to the gap; projected-gap says each does')

    # ------------------------------------------------ projected school gap
    out['projected-gap'] = TP.page(
        'projected-gap',
        'Run forward on our assumed rates, the schools are %s short in %s and %s in %s.'
        % (C.usd(g28), C.fy(fy[0]), C.usd(glast), C.fy(fy[-1])),
        [f('approp', U(o['approp27']), 'the school budget, FY2027, as adopted', 'published',
           {'y': F(B)}),
         f('g28', U(g28), 'projected gap, %s (ours)' % C.fy(fy[0]), 'estimate', {'y': f28}),
         f('g29', U(g29), 'projected gap, %s (ours)' % C.fy(fy[1]), 'estimate', {'y': f29}),
         f('new29', U(o['fresh'][1]), 'of it new in %s (ours)' % C.fy(fy[1]), 'estimate',
           {'y': f29}),
         f('glast', U(glast), 'projected gap, %s (ours)' % C.fy(fy[-1]), 'estimate',
           {'y': flast}),
         f('sal', PY(R['salaries'], 1), 'salary growth, assumed (ours)', 'estimate'),
         f('health', PY(R['health'], 1), 'health insurance cost growth, assumed (ours)',
           'estimate'),
         f('none', None, 'a published FY2028 school budget', 'gap', {'y': F(fy[0])},
           closes='The district’s proposed %s budget, not yet presented' % C.fy(fy[0]))],
        [con('Each year’s gap holds the last: %s of %s’s %s is new that year.'
             % (C.usd(o['fresh'][1]), C.fy(fy[1]), C.usd(g29)), ['g29', 'new29'],
             {'a': U(o['fresh'][1]), 'y': f29, 'b': U(g29)},
             notes=[step('So the yearly figures are not added together: %s already includes %s.'
                         % (C.fy(fy[-1]), C.fy(fy[0])), 'measured',
                         {'a': flast, 'b': f28})]),
         con('It assumes salaries grow %s a year and health insurance %s a year; both are ours.'
             % (C.pct(R['salaries'] * 100, 1), C.pct(R['health'] * 100, 1)), ['sal', 'health'],
             {'a': P(R['salaries'], 1), 'b': P(R['health'], 1)},
             notes=[step('Every rate, and where it came from, is in the method document.',
                         'measured', cite=(src['method']['href'], 'show-your-work.md'))]),
         con('No board has published an FY2028 figure; this is our arithmetic on FY2027’s budget.',
             ['approp', 'g28', 'none'], {'a': F(fy[0]), 'b': F(B)})],
        chart=TP.series('Projected school gap by year', [C.fy(v) for v in fy], [
            TP.track('Gap that year (ours)', [y['gap'] for y in Y], 'estimate', 'bar'),
            TP.track('New that year (ours)', o['fresh'], 'estimate', 'bar')], '$',
            note='Each year’s gap includes the years before it; the second bar is the part '
                 'that is new.'),
        table=dict(caption='The projection, year by year (ours)', views=[dict(
            key='years', label='Level service against revenue',
            note='Our projection from the FY2027 adopted budget, at the rates model.json assumes.',
            columns=['Level service cost', 'Revenue for the schools', 'Gap', 'New that year'],
            kinds=['ledger'] * 4,
            rows=[dict(label=C.fy(y['fy']), cells=[C.usd(y['cost']), C.usd(y['revenue']),
                                                   C.usd(y['gap']), C.usd(o['fresh'][i])])
                  for i, y in enumerate(Y)])]),
        sources=S('model', 'method', 'workbook'),
        finding_figures={'a': U(g28), 'y': f28, 'b': U(glast), 'z': flast})

    # ------------------------------------------------ level service cost
    amt = o['line_amount']
    ranked = sorted(BUCKETS, key=lambda k: -amt[k])
    top2 = ranked[:2]
    if top2 != ['salaries', 'health']:
        fail('salaries and health insurance are no longer the two largest increases')
    top2_share = (amt['salaries'] + amt['health']) / o['increase']
    out['level-service-cost'] = TP.page(
        'level-service-cost',
        'Keeping the same schools costs %s more in %s, by our estimate: %s in all.'
        % (C.usd(o['increase']), C.fy(fy[0]), C.usd(o['cost28'])),
        [f('approp', U(o['approp27']), 'the school budget, FY2027, as adopted', 'published',
           {'y': F(B)}),
         f('addbacks', U(o['addbacks']), 'salaries restored at the September Special Town Meeting',
           'published'),
         f('pupils', N(o['enrollment'], 'pupils'), 'pupils, held the same next year', 'published'),
         f('cost28', U(o['cost28']), 'level service, %s (ours)' % C.fy(fy[0]), 'estimate',
           {'y': f28}),
         f('increase', U(o['increase']), 'more than at FY2027 prices (ours)', 'estimate',
           {'y': F(B)}),
         f('sal', U(amt['salaries']), 'of it salaries, at %s (ours)' % C.pct(R['salaries'] * 100, 1),
           'estimate', {'r': P(R['salaries'], 1)}),
         f('health', U(amt['health']), 'health insurance, at %s (ours)'
           % C.pct(R['health'] * 100, 1), 'estimate', {'r': P(R['health'], 1)}),
         f('top2', P(top2_share, 1), 'of the cost rise is salaries plus insurance (ours)', 'estimate')],
        [con('Level service is the same staff, buses and buildings; %s of it buys nothing new.'
             % C.usd(o['increase']), ['increase', 'pupils'], {'a': U(o['increase'])}),
         con('Salaries add %s and health insurance %s: %s of the cost rise.'
             % (C.usd(amt['salaries']), C.usd(amt['health']), C.pct(top2_share * 100, 1)),
             ['sal', 'health', 'top2'],
             {'a': U(amt['salaries']), 'b': U(amt['health']), 'c': P(top2_share, 1)}),
         con('The %s restored in September carries into %s as salary.'
             % (C.usd(o['addbacks']), C.fy(fy[0])), ['addbacks', 'cost28'],
             {'a': U(o['addbacks']), 'y': f28},
             notes=[step('Its money was one year of state receipts above budget and a fund '
                         'transfer; model/finance.py records neither as recurring.', 'measured')])],
        chart=TP.ranking('Cost increase by line', [(LABELS[k], amt[k]) for k in BUCKETS], '$',
                         basis='estimate',
                         note='Each line’s FY2027 cost grown one year at the rate model.json '
                              'assumes for it. Out-of-district tuition is held flat.',
                         note_figures={'y': F(B)}),
        table=dict(caption='The increase, line by line (ours)', views=[dict(
            key='lines', label='%s level service' % C.fy(fy[0]),
            note='FY2027 cost is the adopted budget’s lines plus the salaries restored in '
                 'September.', columns=['%s cost' % C.fy(B), 'Assumed growth', 'Increase'],
            kinds=['ledger'] * 3,
            rows=[dict(label=LABELS[k], cells=[C.usd(o['base'][k]), C.pct(R[k] * 100, 2),
                                                C.usd(amt[k])]) for k in ranked])]),
        sources=S('model', 'lines', 'workbook', 'method'),
        finding_figures={'a': U(o['increase']), 'y': f28, 'b': U(o['cost28'])})

    # ------------------------------------------------ FY2028 revenue increase
    sv = o['sources']
    out['fy2028-revenue-increase'] = TP.page(
        'fy2028-revenue-increase',
        'The schools’ share of new revenue in %s is %s by our estimate, against %s of costs.'
        % (C.fy(fy[0]), C.usd(o['allowed']), C.usd(o['increase'])),
        [f('allowed', U(o['allowed']), 'more for the schools, %s (ours)' % C.fy(fy[0]),
           'estimate', {'y': f28}),
         f('cap', PY(o['levy_cap'], 1), 'most the levy may rise without an override, Proposition 2½',
           'statute', allow=('Proposition 2½',)),
         f('levy', U(sv['levy']), 'of it from the levy limit’s rise (ours)', 'estimate'),
         f('ng', U(sv['new_growth']), 'from new growth (ours)', 'estimate'),
         f('aid', U(sv['aid']), 'from state aid (ours)', 'estimate'),
         f('rec', U(sv['receipts']), 'from local receipts (ours)', 'estimate'),
         f('rate', PY(o['rev28'], 2), 'school revenue growth, %s (ours)' % C.fy(fy[0]),
           'estimate', {'y': f28}),
         f('increase', U(o['increase']), 'level service costs more (ours)', 'estimate'),
         f('consumed', P(o['consumed'], 0), 'the cost rise, as a share of the new revenue (ours)',
           'estimate'),
         f('g28', U(g28), 'projected gap, %s (ours)' % C.fy(fy[0]), 'estimate', {'y': f28})],
        [con('The levy limit may rise %s a year; that is %s of the schools’ %s.'
             % (C.pct(o['levy_cap'] * 100, 1), C.usd(sv['levy']), C.usd(o['allowed'])),
             ['cap', 'levy', 'allowed'],
             {'a': P(o['levy_cap'], 1), 'b': U(sv['levy']), 'c': U(o['allowed'])},
             notes=[step('Proposition 2½ was a 1980 statewide ballot question; the cap is a fixed '
                         'percentage, not tied to any price.', 'measured',
                         allow=('Proposition 2½', '1980'))]),
         con('New growth, state aid and receipts lift school revenue growth to %s a year in %s.'
             % (C.pct(o['rev28'] * 100, 2), C.fy(fy[0])), ['ng', 'aid', 'rec', 'rate'],
             {'a': P(o['rev28'], 2), 'y': f28}),
         con('Costs rise %s as much as revenue; with September’s salaries the gap is %s.'
             % (C.pct(o['consumed'] * 100, 0), C.usd(g28)), ['increase', 'consumed', 'g28'],
             {'a': P(o['consumed'], 0), 'b': U(g28)})],
        chart=TP.parts('Where the new school revenue comes from', [
            ('Levy limit rise', sv['levy']), ('New growth', sv['new_growth']),
            ('State aid', sv['aid']), ('Local receipts', sv['receipts'])], '$', basis='estimate',
            note='Each source’s share of the town’s added revenue, applied to the schools’ part '
                 'of it. Our arithmetic.'),
        sources=S('model', 'method', 'cherry'),
        finding_figures={'y': f28, 'a': U(o['allowed']), 'b': U(o['increase'])})

    # ------------------------------------------------ gap by cost line
    ct = o['contributes']
    by_ct = sorted(BUCKETS, key=lambda k: -ct[k])
    if by_ct[0] != 'health':
        fail('health insurance no longer puts the most into the FY2028 gap')
    fits = [k for k in BUCKETS if o['line_multiple'][k] <= 1]
    if sorted(fits) != ['other', 'sped_tuition'] or R['sped_tuition'] != 0:
        fail('the lines that fit their share are no longer "everything else" and the tuition '
             'line held flat; the page says they are')
    if not (o['if_none_28'] > 0 > o['if_none_32']):
        fail('with every line at the cap, FY2028 is no longer short and FY2032 no longer spare')
    out['gap-by-cost-line'] = TP.page(
        'gap-by-cost-line',
        'Health insurance puts %s into the %s gap from %s of the school budget (ours).'
        % (C.usd(ct['health']), C.fy(fy[0]), C.pct(W['health'] * 100, 1)),
        [f('hct', U(ct['health']), 'health insurance’s part of the gap (ours)', 'estimate'),
         f('hw', P(W['health'], 1), 'of the school budget is health insurance (our grouping)', 'estimate'),
         f('sct', U(ct['salaries']), 'salaries’ part of the gap (ours)', 'estimate'),
         f('sw', P(W['salaries'], 1), 'of the school budget is salaries (our grouping)', 'estimate'),
         f('dct', U(ct['sped']), 'special education in district, its part (ours)', 'estimate'),
         f('oct', U(ct['other']), 'everything else, its part (ours)', 'estimate'),
         f('ow', P(W['other'], 1), 'of the school budget is everything else (our grouping)', 'estimate'),
         f('orate', PY(R['other'], 1), 'growth in everything else, assumed (ours)', 'estimate'),
         f('tut', PY(R['sped_tuition'], 0), 'out-of-district tuition growth, held flat (ours)',
           'estimate'),
         f('none28', U(o['if_none_28']), 'the %s gap if no line outran the cap (ours)'
           % C.fy(fy[0]), 'estimate', {'y': f28}),
         f('none32', U(-o['if_none_32']), 'spare in %s on the same path (ours)' % C.fy(fy[4]),
           'estimate', {'y': F(fy[4])})],
        [con('Salaries are %s of the school budget and put in %s; size alone does not rank a line.'
             % (C.pct(W['salaries'] * 100, 1), C.usd(ct['salaries'])), ['sw', 'sct', 'hct', 'hw'],
             {'a': P(W['salaries'], 1), 'b': U(ct['salaries'])},
             notes=[step('Each line is held to the levy cap alone and the projection rerun; what '
                         'leaves the gap is that line’s part.', 'estimate')]),
         con('Everything else is %s of the school budget, growing %s a year, and puts in %s.'
             % (C.pct(W['other'] * 100, 1), C.pct(R['other'] * 100, 1), C.usd(ct['other'])),
             ['ow', 'orate', 'oct'],
             {'a': P(W['other'], 1), 'b': P(R['other'], 1), 'c': U(ct['other'])},
             notes=[step('It and out-of-district tuition are the two lines inside their share of '
                         'new revenue; tuition only because we hold it at %s.'
                         % C.pct(R['sped_tuition'] * 100, 0), 'estimate',
                         {'a': P(R['sped_tuition'], 0)})]),
         con('With no line above the cap, %s is still %s short; %s has %s spare.'
             % (C.fy(fy[0]), C.usd(o['if_none_28']), C.fy(fy[4]), C.usd(-o['if_none_32'])),
             ['none28', 'none32'],
             {'y': f28, 'a': U(o['if_none_28']), 'z': F(fy[4]), 'b': U(-o['if_none_32'])})],
        chart=TP.ranking('Each line’s part of the gap', [(LABELS[k], ct[k]) for k in BUCKETS],
                         '$', highlight='Health insurance', basis='estimate',
                         note='What leaves the FY2028 gap when that line alone grows at the levy '
                              'cap. Tuition is below zero: it is held flat, under the cap.',
                         note_figures={'y': f28}),
        table=dict(caption='Size against growth, by line (ours)', views=[dict(
            key='lines', label='Rule 4: weight times excess rate',
            note='Share of the FY2027 cost base, the growth model.json assumes, and the part of '
                 'the FY2028 gap each line puts in.',
            columns=['Share of budget', 'Assumed growth', 'Part of the gap'],
            kinds=['ledger'] * 3,
            rows=[dict(label=LABELS[k], cells=[C.pct(W[k] * 100, 1), C.pct(R[k] * 100, 2),
                                                C.usd(ct[k])]) for k in by_ct])]),
        sources=S('model', 'lines', 'method'),
        finding_figures={'a': U(ct['health']), 'y': f28, 'b': P(W['health'], 1)})

    # ------------------------------------------------ cost and revenue growth
    L = o['long']
    spread = (o['blended'] - o['rev28']) * 100
    out['cost-and-revenue-growth'] = TP.page(
        'cost-and-revenue-growth',
        'Keeping today’s schools costs %s more each year; revenue grows %s a year in %s, then less.'
        % (C.pct(o['blended'] * 100, 2), C.pct(o['rev28'] * 100, 2), C.fy(fy[0])),
        [f('blended', PY(o['blended'], 2), 'cost growth, keeping today’s schools as they are (ours)',
           'estimate'),
         f('rev28', PY(o['rev28'], 2), 'school revenue growth, %s (ours)' % C.fy(fy[0]),
           'estimate', {'y': f28}),
         f('revlast', PY(L[-1]['growth'], 2), 'school revenue growth, %s (ours)' % C.fy(L[-1]['fy']),
           'estimate', {'y': F(L[-1]['fy'])}),
         f('cap', PY(o['levy_cap'], 1), 'levy limit growth, set by Proposition 2½', 'statute',
           allow=('Proposition 2½',)),
         f('spread', figure(spread, C.points(spread, 2), 'points'), 'cost growth minus revenue growth, %s (ours)'
           % C.fy(fy[0]), 'estimate', {'y': f28}),
         f('ng', U(o['ng_assumed']), 'new growth a year, held flat (ours)', 'estimate'),
         f('g37', U(o['decade'][-1]['gap']), 'projected gap, %s (ours)' % C.fy(o['decade'][-1]['fy']),
           'estimate', {'y': F(o['decade'][-1]['fy'])})],
        [con('Two rates %s apart: the gap grows every year at these rates, to %s by %s.'
             % (C.points(spread, 2), C.usd(o['decade'][-1]['gap']), C.fy(o['decade'][-1]['fy'])),
             ['blended', 'rev28', 'spread', 'g37'],
             {'a': figure(spread, C.points(spread, 2), 'points'), 'b': U(o['decade'][-1]['gap']),
              'y': F(o['decade'][-1]['fy'])}),
         con('Revenue growth falls to %s a year by %s: new growth is a flat %s, a shrinking share.'
             % (C.pct(L[-1]['growth'] * 100, 2), C.fy(L[-1]['fy']), C.usd(o['ng_assumed'])),
             ['revlast', 'ng', 'cap'],
             {'a': P(L[-1]['growth'], 2), 'y': F(L[-1]['fy']), 'b': U(o['ng_assumed'])}),
         con('A cut lowers costs once; it leaves the growth of %s a year where it was.'
             % C.pct(o['blended'] * 100, 2), ['blended'], {'a': P(o['blended'], 2)},
             notes=[step('That is the model’s arithmetic: a cut changes the level of the cost '
                         'line, never its growth rate.', 'estimate')])],
        chart=TP.series('Cost and revenue growth rates', [C.fy(y['fy']) for y in L], [
            TP.track('Cost of today’s schools (ours)', [o['blended'] * 100] * len(L), 'estimate'),
            TP.track('School revenue (ours)', [y['growth'] * 100 for y in L], 'estimate')], '%',
            decimals=2, reference=(o['levy_cap'] * 100, 'The levy cap'), from_zero=False,
            note='Both are our projection. Costs hold their blended rate; revenue drifts toward '
                 'the cap as flat new growth shrinks as a share.'),
        sources=S('model', 'method'),
        finding_figures={'a': P(o['blended'], 2), 'b': P(o['rev28'], 2), 'y': f28})

    # ------------------------------------------------ long-run balance rate
    sh = W['salaries'] + W['health']
    if o['salary_to_balance'] >= 0:
        fail('a salary rate at or above zero now balances; the page says none does')
    out['long-run-balance-rate'] = TP.page(
        'long-run-balance-rate',
        'To balance for good, school costs could grow %s a year; our rates give %s a year.'
        % (C.pct(o['target'] * 100, 2), C.pct(o['blended'] * 100, 2)),
        [f('target', PY(o['target'], 2), 'school revenue growth by %s (ours)' % C.fy(L[-1]['fy']),
           'estimate', {'y': F(L[-1]['fy'])}),
         f('blended', PY(o['blended'], 2), 'cost growth, keeping today’s schools as they are (ours)',
           'estimate'),
         f('salrate', PY(o['salary_to_balance'], 2), 'salary line change needed to balance (ours)',
           'estimate'),
         f('sal', PY(R['salaries'], 1), 'salary growth, assumed (ours)', 'estimate'),
         f('health', PY(R['health'], 1), 'health insurance cost growth, assumed (ours)', 'estimate'),
         f('sh', P(sh, 1), 'of the budget is salaries plus insurance (our grouping)', 'estimate'),
         f('pos', D1(o['shrink_per_year'], 'positions'), 'lost a year if the salary line is frozen (ours)',
           'estimate'),
         f('after20', P(o['shrink_after20'], 0), 'of positions gone after twenty years frozen (ours)',
           'estimate'),
         f('cpf', U(o['cost_per_fte']), 'a position, our catalogue’s average', 'estimate')],
        [con('To balance with every other line at our rates, the salary line falls %s a year.'
             % C.pct(-o['salary_to_balance'] * 100, 2), ['salrate', 'target'],
             {'a': P(-o['salary_to_balance'], 2)},
             notes=[step('The bar is revenue growth %s years out, once flat new growth has '
                         'mostly stopped counting.' % C.num(LONG), 'estimate',
                         {'n': N(LONG, 'years')})]),
         con('Frozen at zero while pay rises %s a year, it loses %s positions a year, %s in twenty years.'
             % (C.pct(R['salaries'] * 100, 1), '%.1f' % o['shrink_per_year'],
                C.pct(o['shrink_after20'] * 100, 0)), ['pos', 'after20', 'sal', 'cpf'],
             {'a': P(R['salaries'], 1), 'b': figure(o['shrink_per_year'],
                                                    '%.1f' % o['shrink_per_year'], 'positions'),
              'c': P(o['shrink_after20'], 0)},
             notes=[step('Positions are priced at %s each, salary and benefits, from our '
                         'catalogue of budget lines.' % C.usd(o['cost_per_fte']), 'estimate',
                         {'a': U(o['cost_per_fte'])})]),
         con('Salaries and health insurance are %s of the budget: one bargained, one bought by '
             'the Town.' % C.pct(sh * 100, 1), ['sh', 'health', 'sal'], {'a': P(sh, 1)})],
        chart=TP.series('Assumed growth by cost line', [LABELS[k] for k in BUCKETS], [
            TP.track('Assumed yearly growth (ours)', [R[k] * 100 for k in BUCKETS], 'estimate',
                     'bar')], '%', decimals=2,
            reference=(o['target'] * 100, 'Long-run revenue growth (ours)'),
            note='Every line above the reference grows faster than the schools’ revenue can in '
                 'the long run. Tuition is held flat.'),
        sources=S('model', 'method', 'lines'),
        finding_figures={'a': P(o['target'], 2), 'b': P(o['blended'], 2)})

    # ------------------------------------------------ all cuts combined
    cu = o['cuts']
    if o['cuts_years'] != 2:
        fail('every cut together no longer covers exactly %s and %s; the page and hub say it does'
             % (C.fy(fy[0]), C.fy(fy[1])))
    gap_after = Y[o['cuts_years']]
    out['all-cuts-combined'] = TP.page(
        'all-cuts-combined',
        'Every sport, club, lawful office line and most technology: %s (ours), enough for %s and %s.'
        % (C.usd(o['all_cuts']), C.fy(fy[0]), C.fy(fy[1])),
        [f('ath', U(cu['athletics']), 'every sport still funded, FY2027 adopted', 'published',
           {'y': F(B)}),
         f('ext', U(cu['extras']), 'band, chorus, clubs and art supplies (our grouping)',
           'estimate'),
         f('tech', U(cu['tech']), 'technology, %s of %s (ours)'
           % (C.pct(o['tech_max'], 0), C.usd(o['tech_basis'])), 'estimate',
           {'p': figure(o['tech_max'], C.pct(o['tech_max'], 0)), 'b': U(o['tech_basis'])}),
         f('admin', U(cu['admin']), 'office and admin lines not required by law (ours)',
           'estimate'),
         f('adminn', figure(o['admin_count'], '%d lines' % o['admin_count'], 'lines'),
           'office and admin budget lines among them', 'estimate'),
         f('adminf', figure(o['admin_fte'], C.num(o['admin_fte']) + ' FTE', 'FTE'),
           'positions among them', 'estimate'),
         f('all', U(o['all_cuts']), 'all four together (ours)', 'estimate'),
         f('g28', U(g28), 'projected gap, %s (ours)' % C.fy(fy[0]), 'estimate', {'y': f28}),
         f('gafter', U(gap_after['gap']), 'projected gap, %s (ours)' % C.fy(gap_after['fy']),
           'estimate', {'y': F(gap_after['fy'])})],
        [con('Together they cover %s and %s; %s’s gap of %s is larger than all of it.'
             % (C.fy(fy[0]), C.fy(fy[1]), C.fy(gap_after['fy']), C.usd(gap_after['gap'])),
             ['all', 'g28', 'gafter'],
             {'a': f28, 'b': f29, 'y': F(gap_after['fy']), 'c': U(gap_after['gap'])},
             notes=[step('Even with the saving grown %s a year, as the line it came from would '
                         'have.' % C.pct(o['cuts_growth'] * 100, 1), 'estimate',
                         {'a': P(o['cuts_growth'], 1)})]),
         con('Administration is the largest piece: %s across %s lines and %s positions.'
             % (C.usd(cu['admin']), C.num(o['admin_count']), C.num(o['admin_fte'])),
             ['admin', 'adminn', 'adminf'],
             {'a': U(cu['admin']), 'n': N(o['admin_count'], 'lines'),
              'f': N(o['admin_fte'], 'positions')},
             notes=[step('Which roles state law requires is our reading: %s lines, the '
                         'superintendent and principals among them, are left out.'
                         % C.num(o['admin_blocked']), 'estimate',
                         {'n': N(o['admin_blocked'], 'lines')})]),
         con('This list is our grouping of the catalogue; no board has proposed cutting all of it.',
             ['ath', 'ext', 'tech'])],
        chart=TP.parts('Every nameable cut, by group', [
            ('Every sport', cu['athletics']), ('Band, chorus, clubs, art', cu['extras']),
            ('Most of technology', cu['tech']), ('Office and admin lines', cu['admin'])], '$',
            basis='estimate',
            note='Our grouping, at FY2027 adopted amounts. Sports are the district’s figure; '
                 'the rest is ours.', note_figures={'y': F(B)}),
        sources=S('model', 'workbook', 'budget'),
        finding_figures={'a': U(o['all_cuts']), 'y': f28, 'z': f29})

    # ------------------------------------------------ development needed
    best, last = o['ng_best'], o['ng_last']
    if not o['ng_same_1_5_10']:
        fail('the new growth needed for one, five and ten years no longer agree; the page says '
             'the first year binds')
    vs_best = o['ng_needed'] / best['amount']
    hist = o['ng_history']
    out['development-needed'] = TP.page(
        'development-needed',
        'Growth alone would need %s of new levy a year (ours); the best year on record added %s.'
        % (C.usd(o['ng_needed']), C.usd(best['amount'])),
        [f('need', U(o['ng_needed']), 'new growth a year, to hold the gap (ours)', 'estimate'),
         f('assumed', U(o['ng_assumed']), 'a year, already in the projection (ours)', 'estimate'),
         f('last', U(last['amount']), 'new growth certified, %s' % C.fy(last['fy']), 'published',
           {'y': F(last['fy'])}),
         f('best', U(best['amount']), 'the most in any year, %s' % C.fy(best['fy']), 'published',
           {'y': F(best['fy'])}),
         f('times', figure(vs_best, '%.1f times' % vs_best, 'times'), 'the need, against the best year',
           'estimate'),
         f('value', U(o['ng_value']), 'new assessed value a year, beyond that (ours)', 'estimate'),
         f('dev', D1(o['ng_developments'], 'a year'), 'developments, at our mixed archetype',
           'estimate'),
         f('mix', U(o['mix']), 'our archetype development’s value', 'estimate'),
         f('share', P(o['share'], 1), 'of each new tax dollar that reaches the schools (ours)',
           'estimate')],
        [con('The schools keep %s of each new tax dollar, so growth works at about half its face.'
             % C.pct(o['share'] * 100, 1), ['share'], {'a': P(o['share'], 1)}),
         con('%s a year is %s the best year on record, %s.'
             % (C.usd(o['ng_needed']), '%.1f times' % vs_best, C.fy(best['fy'])),
             ['need', 'best', 'times', 'last'],
             {'a': U(o['ng_needed']), 'b': figure(vs_best, '%.1f times' % vs_best, 'times'),
              'y': F(best['fy'])},
             notes=[step('New growth counts every class of property, homes included; the '
                         'certified series does not split out commerce alone here.', 'measured')]),
         con('That is %s of new value a year, about %s developments at %s each.'
             % (C.usd(o['ng_value']), '%.1f' % o['ng_developments'], C.usd(o['mix'])),
             ['value', 'dev', 'mix'],
             {'a': U(o['ng_value']), 'b': figure(o['ng_developments'],
                                                 '%.1f' % o['ng_developments'], 'developments'),
              'c': U(o['mix'])},
             notes=[step('The same rate holds one year or ten at these rates: the first year is '
                         'the hardest.', 'estimate')])],
        chart=TP.series('New growth added to the levy', [C.fy(h['fy']) for h in hist], [
            TP.track('Certified new growth', [h['amount'] for h in hist], 'published', 'bar')],
            '$', reference=(o['ng_needed'], 'Needed every year (ours)'),
            note='The state’s certified new growth, every class of property. The line is our '
                 'estimate of what would hold the gap.'),
        table=dict(caption='Certified new growth, by year', views=[dict(
            key='years', label='Division of Local Services', note='Every class of property.',
            columns=['New growth'], kinds=['ledger'],
            rows=[dict(label=C.fy(h['fy']), cells=[C.usd(h['amount'])])
                  for h in reversed(hist[-20:])])]),
        sources=S('model', 'newgrowth', 'method'),
        finding_figures={'a': U(o['ng_needed']), 'b': U(best['amount'])})

    # ------------------------------------------------ Chapter 70 needed
    dec = [B + 1 + i for i in range(DECADE)]
    CH = ('Chapter 70',)
    out['chapter-70-needed'] = TP.page(
        'chapter-70-needed',
        'For state aid alone to hold the gap, Chapter 70 would grow %s a year (ours); we assume %s a year.'
        % (C.pct(o['ch70_rate'] * 100, 2), C.pct(o['aid_assumed'] * 100, 2)),
        [f('ch70', U(o['ch70']), 'Chapter 70, FY2027', 'published', {'y': F(B)}, allow=CH),
         f('aid', U(o['state_aid']), 'all state aid, FY2027', 'published', {'y': F(B)}),
         f('share', P(o['aid_share_town'], 1), 'of the town’s revenue is state aid (our division)',
           'estimate'),
         f('assumed', PY(o['aid_assumed'], 2), 'state aid growth, assumed (ours)',
           'estimate'),
         f('aidrate', PY(o['aid_rate'], 2), 'state aid growth needed to close the gap (ours)',
           'estimate'),
         f('chrate', PY(o['ch70_rate'], 2), 'Chapter 70 growth needed, if it alone closes it (ours)', 'estimate',
           allow=CH),
         f('need37', U(o['ch70_at_need'][-1]), 'Chapter 70 in %s at that rate (ours)'
           % C.fy(dec[-1]), 'estimate', {'y': F(dec[-1])}, allow=CH),
         f('base37', U(o['ch70_at_base'][-1]), 'at our assumed rate (ours)', 'estimate'),
         f('extra', U(o['ch70_extra']), 'more Chapter 70 over ten years than we count (ours)',
           'estimate', allow=CH),
         f('above', U(o['above_foundation']), 'FY2027 budget above foundation (our subtraction)',
           'estimate', {'y': F(B)})],
        [con('To hold the gap, all state aid would grow %s a year; Chapter 70 alone, %s a year.'
             % (C.pct(o['aid_rate'] * 100, 2), C.pct(o['ch70_rate'] * 100, 2)),
             ['aidrate', 'chrate', 'aid', 'ch70'],
             {'a': P(o['aid_rate'], 2), 'b': P(o['ch70_rate'], 2)}, allow=CH,
             notes=[step('Chapter 70 is the school part of state aid; the rest is held at our '
                         'assumed rate.', 'estimate', allow=CH)]),
         con('By %s that is %s of Chapter 70, against %s at our assumed rate.'
             % (C.fy(dec[-1]), C.usd(o['ch70_at_need'][-1]), C.usd(o['ch70_at_base'][-1])),
             ['need37', 'base37', 'assumed'],
             {'y': F(dec[-1]), 'a': U(o['ch70_at_need'][-1]), 'b': U(o['ch70_at_base'][-1])},
             allow=CH),
         con('Over ten years, %s more Chapter 70 than the projection already counts.'
             % C.usd(o['ch70_extra']), ['extra'], {'a': U(o['ch70_extra'])}, allow=CH),
         con('The FY2027 school budget is %s above the state’s foundation budget.'
             % C.usd(o['above_foundation']), ['above'], {'y': F(B), 'a': U(o['above_foundation'])},
             notes=[step('Foundation budget %s, from the state’s FY2027 Chapter 70 figures in '
                         'model.json.' % C.usd(o['foundation']), 'measured',
                         {'a': U(o['foundation']), 'y': F(B)}, allow=CH)])],
        chart=TP.series('Chapter 70 at two growth rates', [C.fy(y) for y in dec], [
            TP.track('At the rate needed (ours)', o['ch70_at_need'], 'estimate'),
            TP.track('At our assumed rate (ours)', o['ch70_at_base'], 'estimate')], '$',
            note='Both are our projection from FY2027’s Chapter 70.', note_figures={'y': F(B)},
            note_allow=CH),
        sources=S('model', 'cherry', 'method'),
        finding_figures={'a': P(o['ch70_rate'], 2), 'b': P(o['aid_assumed'], 2)},
        finding_allow=CH)

    # ------------------------------------------------ the hub
    h = {}
    h['g28'] = f('h-g28', U(g28), 'projected gap, %s (ours)' % C.fy(fy[0]), 'estimate', {'y': f28})
    h['glast'] = f('h-glast', U(glast), 'projected gap, %s (ours)' % C.fy(fy[-1]), 'estimate',
                   {'y': flast})
    h['inc'] = f('h-inc', U(o['increase']), 'more for level service, %s (ours)' % C.fy(fy[0]),
                 'estimate', {'y': f28})
    h['allowed'] = f('h-allowed', U(o['allowed']), 'more revenue for the schools (ours)',
                     'estimate')
    h['blended'] = f('h-blended', PY(o['blended'], 2), 'cost growth, keeping today’s schools as they are',
                     'estimate')
    h['rev'] = f('h-rev', PY(o['rev28'], 2), 'school revenue growth, %s (ours)' % C.fy(fy[0]),
                 'estimate', {'y': f28})
    h['cap'] = f('h-cap', PY(o['levy_cap'], 1), 'levy limit growth, set by Proposition 2½', 'statute',
                 allow=('Proposition 2½',))
    h['hct'] = f('h-hct', U(ct['health']), 'health insurance’s part of the gap (ours)',
                 'estimate')
    h['cuts'] = f('h-cuts', U(o['all_cuts']), 'every nameable cut, together (ours)', 'estimate')
    h['need'] = f('h-need', U(o['ng_needed']), 'new growth a year to hold the gap (ours)',
                  'estimate')
    h['ch70'] = f('h-ch70', PY(o['ch70_rate'], 2), 'Chapter 70 growth needed to close the gap (ours)',
                  'estimate', allow=CH)
    tiers = [
        LD.tier('The gap', [h['g28'], h['glast'], h['inc'], h['allowed']]),
        LD.tier('The rates', [h['blended'], h['rev'], h['cap'], h['hct']]),
        LD.tier('What would hold it', [h['cuts'], h['need'], h['ch70']]),
    ]
    hub_ladder = LD.ladder(tiers, [
        LD.conclusion('On our arithmetic the schools are %s short in %s and %s in %s.'
                      % (C.usd(g28), C.fy(fy[0]), C.usd(glast), C.fy(fy[-1])), ['h-g28', 'h-glast'],
                      {'a': U(g28), 'y': f28, 'b': U(glast), 'z': flast}),
        LD.conclusion('Level service wants %s more in %s; revenue brings %s.'
                      % (C.usd(o['increase']), C.fy(fy[0]), C.usd(o['allowed'])),
                      ['h-inc', 'h-allowed'], {'a': U(o['increase']), 'y': f28,
                                               'b': U(o['allowed'])}),
        LD.conclusion('Costs grow %s a year; revenue %s a year, slowing toward the %s cap.'
                      % (C.pct(o['blended'] * 100, 2), C.pct(o['rev28'] * 100, 2),
                         C.pct(o['levy_cap'] * 100, 1)), ['h-blended', 'h-rev', 'h-cap'],
                      {'a': P(o['blended'], 2), 'b': P(o['rev28'], 2), 'c': P(o['levy_cap'], 1)}),
        LD.conclusion('Health insurance puts the most into the gap: %s of %s.'
                      % (C.usd(ct['health']), C.usd(g28)), ['h-hct', 'h-g28'],
                      {'a': U(ct['health']), 'b': U(g28)}),
        LD.conclusion('Every nameable cut together, %s, covers %s and %s only.'
                      % (C.usd(o['all_cuts']), C.fy(fy[0]), C.fy(fy[1])), ['h-cuts'],
                      {'a': U(o['all_cuts']), 'y': f28, 'z': f29}),
        LD.conclusion('Growth would need %s of new levy a year; or Chapter 70 growing %s a year.'
                      % (C.usd(o['ng_needed']), C.pct(o['ch70_rate'] * 100, 2)),
                      ['h-need', 'h-ch70'],
                      {'a': U(o['ng_needed']), 'b': P(o['ch70_rate'], 2)}, allow=CH),
    ])
    D = o['decade']
    out[HUB] = TP.hub(
        HUB,
        'On our projection the school budget is %s short in %s and short every year after: '
        'keeping today’s schools costs %s more each year, while revenue grows %s a year and '
        'slows. A cut lowers the cost line once; only a rate changes where it heads.'
        % (C.usd(g28), C.fy(fy[0]), C.pct(o['blended'] * 100, 2), C.pct(o['rev28'] * 100, 2)),
        hub_ladder,
        chart=TP.series('Level service cost and school revenue', [C.fy(y['fy']) for y in D], [
            TP.track('Level service cost (ours)', [y['cost'] for y in D], 'estimate'),
            TP.track('Revenue for the schools (ours)', [y['revenue'] for y in D], 'estimate')],
            '$', from_zero=False,
            note='Our projection from the FY2027 adopted budget. The space between the lines is '
                 'the gap, and it widens every year.', note_figures={'y': F(B)}),
        answer_figures={'a': U(g28), 'y': f28, 'b': P(o['blended'], 2), 'c': P(o['rev28'], 2)})

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
        print('budget crisis topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
