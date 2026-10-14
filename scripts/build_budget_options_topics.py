#!/usr/bin/env python3
"""Budget options, split into topic pages: what each way of closing the school gap yields,
and who bears it.

    python3 scripts/build_budget_options_topics.py           # write fy28/public/data/topics/*.json
    python3 scripts/build_budget_options_topics.py --check   # fail if any output would change

WHAT THIS ABSORBS. The /override, /fees, /extras, /classrooms and /salaries lever pages and the
two analyses fy27-and-the-override.md and fy27-cut-reconciliation.md, and /what-families-pay:
three pages read off its own payload (family_fee_pages, below). Options another shelf
already answers (free cash, the stabilization fund, the athletic fee, the bus fee, the cut
lists) are listed on this shelf by the registry, not rebuilt.

WHERE EACH FIGURE COMES FROM.

  sources/data/dls-override-votes.csv   the Division of Local Services' record of every
                                        Proposition 2½ question (extract_dls_overrides.py).
  the Town's FY27 budget release        the tiers, the schools' share of each, the tax impact.
                                        Every figure is asserted verbatim against our text copy.
  the district's budget addendum        Scenario D's reductions, its variances, its headcounts,
                                        each asserted verbatim against our text copy.
  the teachers' agreement and its scale the term, the three scale increases, the FY27 scale.
  fy28/public/data/model.json           the programme catalogue and the fee levers. OURS.
  fy28/src/model/*.ts                   THE PROJECTION THE OLD LEVER PAGES RENDERED: the gap,
                                        the override sizing, the settlement table, the
                                        position arithmetic. Bundled with esbuild and run in
                                        node, read-only, so these pages state exactly what
                                        those pages stated. Its gaps are asserted equal to
                                        model/finance.py's, the Python engine, every run.

RULE 3. Everything the projection yields is OUR estimate and is kinded `estimate`. The rates
it runs on -- salaries at 4%, everything else as model.json `assumptions` -- are assumptions
we chose, and the pages say so.

RULE 13a, AND A DISAGREEMENT THIS PAGE DOES NOT RESOLVE. model.json `facts` carries the
Town's UNOFFICIAL TALLY SHEET of the May 2026 vote
(town-supplementary/docs/town-2026-election-unofficial-results.pdf), which foots precinct by
precinct to its own ballots-cast total. The state's record prints different counts, and its
yes plus no alone exceed that ballots-cast total (asserted below). Neither is the certified
count. The state's figures are shown, the Town's sheet is named beside them, and the
difference is a gap closed by the Town Clerk's certified results, which the archive does not
hold.
"""
import argparse
import csv
import glob
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(ROOT, 'model'))  # after scripts/: model/ has its own conclusions.py
import conclusions as C  # noqa: E402
from conclusions import figure  # noqa: E402
import ladder as LD  # noqa: E402
import topic as TP  # noqa: E402
import topics as REG  # noqa: E402
from brief import step  # noqa: E402
from finance import project as py_project  # noqa: E402

D = os.path.join(ROOT, 'sources', 'data')
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT_DIR = os.path.join(PUB, 'topics')
MANIFEST = os.path.join(D, 'archive-manifest.csv')
MINUTES = os.path.join(ROOT, 'sources', 'meetings', 'text')
TS_MODEL = os.path.join(ROOT, 'fy28', 'src', 'model')
ESBUILD = os.path.join(ROOT, 'fy28', 'node_modules', '.bin', 'esbuild')
RELEASE_TXT = glob.glob(os.path.join(ROOT, 'sources', 'town-budget', 'text', '4090-*.txt'))
ADDENDUM_TXT = os.path.join(ROOT, 'sources', 'district-budget', 'text',
                            'budget-addendum-multi-scenario-financial-analysis.txt')
CONTRACT_TXT = os.path.join(ROOT, 'sources', 'contracts', 'txt', 'lea-teachers-2024-2027.txt')
SCALE_CSV = os.path.join(ROOT, 'sources', 'contracts', 'data', 'lea-teacher-salary-schedule.csv')

TIER = ('Tier 1', 'Tier 2')     # the Town's names for the two questions, not figures

MINE = [t for t, (_, home, gen) in REG.TOPICS.items()
        if home == 'budget-options' and gen == 'build_budget_options_topics.py']


def fail(msg):
    raise SystemExit('build_budget_options_topics: ' + msg)


def load(name):
    return json.load(open(os.path.join(PUB, name), encoding='utf-8'))


def norm(s):
    return ' '.join((s or '').split())


def text_of(path):
    if not os.path.exists(path):
        fail('%s is not on disk' % os.path.relpath(path, ROOT))
    return norm(open(path, encoding='utf-8').read())


def verbatim(text, *needles, where='document'):
    for n in needles:
        if norm(n) not in text:
            fail('%r is no longer in the %s' % (n, where))


def said_file(rel, quote, board, kind='minutes'):
    """A quotation asserted here, verbatim, against our copy of the minutes."""
    text = text_of(os.path.join(MINUTES, rel))
    if norm(quote) not in text:
        fail('quote is not verbatim in %s: %r' % (rel, quote))
    date = re.search(r'(\d{4}-\d{2}-\d{2})', rel).group(1)
    return dict(quote=quote, board=board, date=date, href='/docs/minutes/text/' + rel,
                label='%s %s, %s' % (board, kind, date))


def sources():
    man = {r['key'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    town, lps = 'Town of Lunenburg', 'Lunenburg Public Schools'
    spec = {
        'dls': ('state-dls/OverrideUnderrideVotes.xlsx',
                'Massachusetts Division of Local Services, Override and Underride Votes'),
        'release': ('town-budget/docs/4090-click-here-for-a-release-on-quot-understanding-'
                    'lunenburg-apos-s-fy27-budget-how-.pdf', town + ' — FY27 budget release'),
        'addendum': ('district-budget/docs/budget-addendum-multi-scenario-financial-analysis.pdf',
                     lps + ' — Budget Addendum: Multi-Scenario Financial Analysis'),
        'workbook': ('budget-workbooks/fy27-proposals.xlsx', lps + ' — FY27 budget workbook'),
        'contract': ('contracts/txt/lea-teachers-2024-2027.txt',
                     'Lunenburg Education Association agreement, 2024–2027 (text)'),
        'scale': ('contracts/data/lea-teacher-salary-schedule.csv',
                  'Lunenburg Budget Project — the agreement’s salary scale, extracted'),
        'sc-0604': ('meetings/school-committee/2025-06-04-minutes-7251.pdf',
                    'School Committee minutes, 4 June 2025'),
        'sc-0507': ('meetings/school-committee/2025-05-07-minutes-7207.pdf',
                    'School Committee minutes, 7 May 2025'),
        'sb-0311': ('meetings/select-board/2025-03-11-minutes-7096.pdf',
                    'Select Board minutes, 11 March 2025'),
        'tally': ('town-supplementary/docs/town-2026-election-unofficial-results.pdf',
                  town + ' — unofficial tally sheet, Annual Town Election, 16 May 2026'),
    }
    out = {}
    for k, (key, pub) in spec.items():
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        out[k] = dict(label='%s — %s' % (pub, key.split('/')[-1]), href='/docs/' + key)
    if not os.path.exists(os.path.join(ROOT, 'fy28', 'public', 'docs', 'data',
                                       'dls-override-votes.csv')):
        fail('/docs/data/dls-override-votes.csv is not published')
    out['d-dls'] = dict(label='Lunenburg Budget Project — dls-override-votes.csv (every question '
                              'the state records)', href='/docs/data/dls-override-votes.csv')
    out['model'] = dict(label='Lunenburg Budget Project — model.json (the projection; ours)',
                        href='/data/model.json')
    return out


# --------------------------------------------------------------------- the projection

TS_ENTRY = """
import { GAPS, COST_GROWTH, CONTRACT, SETTLEMENT, COUNTERFACTUAL } from '%(m)s/answers'
import { DEFAULT_RATES, LEVY_CAP, COST_PER_FTE, HEADCOUNT, SHARE, overrideForYears,
         workforceShrink } from '%(m)s/rates'
const out = {
  GAPS, COST_GROWTH, CONTRACT, SETTLEMENT, COUNTERFACTUAL, DEFAULT_RATES, LEVY_CAP,
  COST_PER_FTE, HEADCOUNT, SHARE,
  override: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => ({ years: n, ...overrideForYears(n) })),
  shrink: workforceShrink(LEVY_CAP, DEFAULT_RATES.salaries),
}
console.log(JSON.stringify(out))
"""


def ts_model():
    """The site's TypeScript projection, run as it is: bundled by esbuild, executed by node.
    Nothing is written into the repository."""
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
        run = subprocess.run(['node', '--input-type=module'], input=js.stdout,
                             capture_output=True, text=True)
        if run.returncode:
            fail('node could not run the projection:\n' + run.stderr)
    return json.loads(run.stdout)


# --------------------------------------------------------------------- the data

def lunenburg_votes():
    rows = [r for r in csv.DictReader(open(os.path.join(D, 'dls-override-votes.csv'),
                                           encoding='utf-8'))]
    for r in rows:
        if (r['result'] == 'WIN') != (int(r['yes_votes']) > int(r['no_votes'])):
            fail('a DLS row no longer satisfies win == yes > no: %r' % r)
    ours = sorted((r for r in rows if r['municipality'] == 'Lunenburg'
                   and r['vote_type'] == 'Override'), key=lambda r: r['vote_date'])
    return rows, ours


def addendum_d(text):
    """Scenario D's reductions, read off the addendum: the priced posts and the one it left
    blank. Asserted against the FTE it states, not assumed."""
    sec = text.split('5. SCENARIO D: BALANCED BUDGET')[1].split('Program Reductions:')[0]
    sec = sec.split('Reductions:')[1]
    priced = [(float(a.replace(',', '')), float(f)) for a, f in
              re.findall(r'\$([\d,]{5,})\s+([\d.]+)', sec)]
    blank = re.findall(r'\$\s+(\.\d)\s+Music', sec)
    if len(priced) != 7 or blank != ['.2']:
        fail('Scenario D no longer lists seven priced reductions and one blank: %r' % priced)
    return dict(dollars=sum(a for a, _ in priced),
                fte=round(sum(f for _, f in priced) + float(blank[0]), 1),
                classroom=sum(f for a, f in priced if a in (205019, 171811)))


def build():
    M = load('model.json')
    TS = ts_model()
    src = sources()
    U = lambda v: figure(v, C.usd(v))
    U2 = lambda v: figure(v, '$' + format(v, ',.2f'))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    POS = lambda v: figure(v, '%.1f positions' % v, 'positions')
    f, con = LD.fact, TP.conclusion
    out = {}

    # ------------------------------------------------ the gap, both engines
    gaps = {g['fy']: g['cumulative'] for g in TS['GAPS']}
    py = [round(y['deficit']) for y in py_project(years=len(gaps))]
    if py != [gaps[fy] for fy in sorted(gaps)]:
        fail('the TypeScript and Python projections no longer agree: %s vs %s'
             % (py, [gaps[fy] for fy in sorted(gaps)]))
    if [round(d['amount']) for d in M['freeCash']['deficits']] != py:
        fail('model.json freeCash.deficits no longer matches the projection')
    g28, last_fy = gaps[28], max(gaps)
    LEVY = TS['LEVY_CAP']

    # ------------------------------------------------ override history (DLS)
    allrows, L = lunenburg_votes()
    won = [r for r in L if r['result'] == 'WIN']
    lost = [r for r in L if r['result'] == 'LOSS']
    w24 = [r for r in won if r['vote_date'] == '2024-05-18']
    l26 = sorted([r for r in L if r['vote_date'] == '2026-05-16'], key=lambda r: int(r['amount']))
    if len(L) != 10 or len(w24) != 1 or len(l26) != 2 or any(r['result'] != 'LOSS' for r in l26):
        fail('the DLS record of Lunenburg no longer reads ten questions, a 2024 win and two '
             '2026 losses')
    w24 = w24[0]
    dates = [r['vote_date'] for r in L]
    before = max(d for d in dates if d < '2024')
    if before != '1996-05-11':
        fail('the last question before 2024 is no longer May 1996')
    lull = 2024 - 1996
    sw = [r for r in allrows if r['vote_date'].startswith('2026') and r['vote_type'] == 'Override']
    MON = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()

    def qlabel(r):
        # Two questions share a date twice; the state's own department column tells them apart.
        d = '%s %s' % (MON[int(r['vote_date'][5:7]) - 1], r['vote_date'][:4])
        if sum(x['vote_date'] == r['vote_date'] for x in L) == 1:
            return d
        if r['vote_date'] == '2026-05-16':
            return '%s, %s' % (d, TIER[0] if int(r['amount']) == 2_400_000 else TIER[1])
        return '%s, %s' % (d, r['department'].split()[0].lower())
    LC = sorted(L, key=lambda r: (r['vote_date'], int(r['amount'])))   # Tier 1 before Tier 2
    hist_chart = TP.series(
        'Override questions on the ballot', [qlabel(r) for r in LC], [
            TP.track('Passed', [int(r['amount']) if r['result'] == 'WIN' else None for r in LC],
                     'published', 'bar'),
            TP.track('Failed', [int(r['amount']) if r['result'] == 'LOSS' else None for r in LC],
                     'published', 'bar')], '$', stacked=True,
        note='The amount each question asked, in the state’s record. Nothing was put between '
             'May %s and May %s.' % ('1996', '2024'), note_allow=('1996', '2024'))
    sw_won = sum(r['result'] == 'WIN' for r in sw)
    out['override-history'] = TP.page(
        'override-history',
        'The state records %s Lunenburg override questions since %s; %s passed, the last %s in May %s.'
        % (C.num(len(L)), '1989', C.num(len(won)), C.usd(w24['amount']), '2024'),
        [f('questions', N(len(L), 'questions'), 'override questions on the ballot, 1989 to 2026',
           'published', allow=('1989', '2026')),
         f('won', N(len(won), 'questions'), 'of them passed', 'published'),
         f('lost', N(len(lost), 'questions'), 'of them failed', 'published'),
         f('lull', N(lull, 'years'), 'between questions, May 1996 to May 2024', 'published',
           allow=('May 1996', 'May 2024')),
         f('w24', U(int(w24['amount'])), 'passed May 2024, “Fund Lunenburg Public Schools”',
           'published', allow=('May 2024',)),
         f('w24yes', N(int(w24['yes_votes']), 'votes'), 'yes in May 2024', 'published',
           allow=('May 2024',)),
         f('w24no', N(int(w24['no_votes']), 'votes'), 'no in May 2024', 'published',
           allow=('May 2024',)),
         f('sw', N(len(sw), 'questions'), 'override questions statewide in 2026, to date',
           'published', allow=('2026',)),
         f('swwon', N(sw_won, 'questions'), 'of them passed', 'published')],
        [con('Of %s override questions since %s, %s passed and %s failed.'
             % (C.num(len(L)), '1989', C.num(len(won)), C.num(len(lost))),
             ['questions', 'won', 'lost'],
             {'a': N(len(L)), 'b': N(len(won)), 'c': N(len(lost))}, allow=('1989',)),
         con('The state records no question at all for %s years, May %s to May %s.'
             % (C.num(lull), '1996', '2024'), ['lull'], {'a': N(lull)},
             allow=('1996', '2024')),
         con('The May %s school override passed %s to %s, for %s.'
             % ('2024', C.num(w24['yes_votes']), C.num(w24['no_votes']), C.usd(w24['amount'])),
             ['w24', 'w24yes', 'w24no'],
             {'y': N(int(w24['yes_votes'])), 'n': N(int(w24['no_votes'])),
              'a': U(int(w24['amount']))}, allow=('2024',)),
         con('Statewide, %s of %s override questions put in %s have passed.'
             % (C.num(sw_won), C.num(len(sw)), '2026'), ['sw', 'swwon'],
             {'a': N(sw_won), 'b': N(len(sw))}, allow=('2026',))],
        table=dict(caption='Every override question Lunenburg has put', views=[dict(
            key='dls', label='The state’s record', total_col=-1, kinds=['ledger'] * 4,
            columns=['Amount', 'Yes', 'No', 'Result'],
            rows=[dict(label=r['vote_date'], cells=[C.usd(r['amount']), C.num(r['yes_votes']),
                                                    C.num(r['no_votes']),
                                                    'passed' if r['result'] == 'WIN' else 'failed'])
                  for r in reversed(L)],
            note='The Division of Local Services’ record, by vote date. Its fiscal-year column '
                 'dates the May 2026 questions FY2026, though both describe FY27 budgets. Debt '
                 'and capital exclusions are not in it.')]),
        chart=hist_chart,
        sources=[src['dls'], src['d-dls']],
        finding_figures={'n': N(len(L)), 'w': N(len(won)), 'a': U(int(w24['amount']))},
        finding_allow=('1989', '2024'))

    # ------------------------------------------------ the FY2027 override
    rel = text_of(RELEASE_TXT[0]) if len(RELEASE_TXT) == 1 else fail('release text not found')
    t1, t2 = (int(r['amount']) for r in l26)
    if (t1, t2) != (2_400_000, 3_300_000):
        fail('the two May 2026 questions are no longer $2.4M and $3.3M')
    tax1, tax2, levy_only, bill = 506.95, 689.35, 175.88, 7444
    t1s, t2s = 1_600_000, 1_948_527
    verbatim(rel, 'Tier 1 Override: $52,321,641.87 - Requires a $2,400,000 Override',
             'Tier 2 Override: $53,212,536.02 - Requires a $3,300,000 Override',
             '$1,600,000 for Lunenburg Public Schools', '$1,948,527 for Lunenburg Public Schools',
             'Override- not including impact of levy limit increase above $506.95',
             'Override- not including impact of levy limit increase above $689.35',
             'adding $822,770, an increase of $175.88',
             'FY 2026 Average Single Family Tax Bill (current) $7,444', where='Town’s FY27 release')
    q1, q2 = l26
    y1, n1, y2, n2 = (int(q1['yes_votes']), int(q1['no_votes']), int(q2['yes_votes']),
                      int(q2['no_votes']))
    pc1, pc2 = 100 * y1 / (y1 + n1), 100 * y2 / (y2 + n2)
    uq1, uq2 = M['facts']['overrideQ1'], M['facts']['overrideQ2']
    if (uq1['yes'], uq1['no']) == (y1, n1):
        fail('the unofficial tally now matches the state’s record; the gap note is stale')
    cast = M['facts']['ballotsCast']
    if not (y1 + n1 > cast and y2 + n2 > cast):
        fail('the state’s yes plus no no longer exceed the tally sheet’s ballots cast')
    out['fy2027-override'] = TP.page(
        'fy2027-override',
        'Both FY2027 override questions failed on 16 May 2026: %s by %s to %s, %s by %s to %s.'
        % (C.usd(t1), C.num(y1), C.num(n1), C.usd(t2), C.num(y2), C.num(n2)),
        [f('t1', U(t1), 'Tier 1 question, 16 May 2026', 'published', allow=('16 May 2026',) + TIER),
         f('y1', N(y1, 'votes'), 'yes on Tier 1, the state’s record', 'published', allow=TIER),
         f('n1', N(n1, 'votes'), 'no on Tier 1', 'published', allow=TIER),
         f('t2', U(t2), 'Tier 2 question, the same day', 'published', allow=TIER),
         f('y2', N(y2, 'votes'), 'yes on Tier 2', 'published', allow=TIER),
         f('n2', N(n2, 'votes'), 'no on Tier 2', 'published', allow=TIER),
         f('tax1', U2(tax1), 'a year on the average home, Tier 1 (Town)', 'published', allow=TIER),
         f('tax2', U2(tax2), 'a year on the average home, Tier 2 (Town)', 'published', allow=TIER),
         f('levy', U2(levy_only), 'the levy’s ordinary rise, same home, FY2027', 'published',
           {'y': F(2027)}),
         f('bill', U(bill), 'average single-family tax bill, FY2026', 'published',
           {'y': F(2026)}),
         f('count-gap', None, 'the Town’s certified count of the vote', 'gap',
           closes='the Town Clerk’s certified results of the 16 May 2026 election')],
        [con('Tier 1 drew %s yes and Tier 2 %s, in the state’s record of the vote.'
             % (C.pct(pc1), C.pct(pc2)), ['y1', 'n1', 'y2', 'n2'],
             {'a': P(pc1), 'b': P(pc2)}, allow=TIER),
         con('The Town priced Tier 1 at %s a year on the average home, on a %s bill.'
             % ('$' + format(tax1, ',.2f'), C.usd(bill)), ['tax1', 'bill'],
             {'a': U2(tax1), 'b': U(bill)}, allow=TIER),
         con('Tier 2 was priced at %s; both sit on top of the levy’s own %s rise.'
             % ('$' + format(tax2, ',.2f'), '$' + format(levy_only, ',.2f')), ['tax2', 'levy'],
             {'a': U2(tax2), 'b': U2(levy_only)}, allow=TIER),
         con('The state’s tally is shown; the Town’s certified count is not in this archive.',
             ['count-gap', 'y1'],
             notes=[step('The Town’s unofficial tally sheet prints %s to %s on Tier 1 and %s to '
                         '%s on Tier 2, footing to its %s ballots cast; the state’s yes and no '
                         'alone sum to more.'
                         % (C.num(uq1['yes']), C.num(uq1['no']), C.num(uq2['yes']),
                            C.num(uq2['no']), C.num(cast)), 'gap',
                         {'a': N(uq1['yes']), 'b': N(uq1['no']), 'c': N(uq2['yes']),
                          'd': N(uq2['no']), 'e': N(cast)}, allow=TIER + ('16 May 2026',),
                         closes='the Town Clerk’s certified results of the 16 May 2026 '
                                'election')])],
        chart=TP.series(
            'The May vote, two counts',
            ['%s, yes' % TIER[0], '%s, no' % TIER[0], '%s, yes' % TIER[1], '%s, no' % TIER[1]], [
                TP.track('The state’s record', [y1, n1, y2, n2], 'published', 'bar'),
                TP.track('The Town’s unofficial tally sheet',
                         [uq1['yes'], uq1['no'], uq2['yes'], uq2['no']], 'published', 'bar')],
            'votes',
            note='Neither is the certified count. The state’s yes and no on each question sum to '
                 'more than the tally sheet’s %s ballots cast.' % C.num(cast),
            note_figures={'a': N(cast)}),
        sources=[src['dls'], src['d-dls'], src['tally'], src['release']],
        finding_figures={'a': U(t1), 'b': N(y1), 'c': N(n1), 'd': U(t2), 'e': N(y2),
                         'g': N(n2), 'y': F(2027)},
        finding_allow=('16 May 2026',))

    # ------------------------------------------------ how long an override lasts
    ov = {o['years']: o for o in TS['override']}
    growth = 100 * TS['COST_GROWTH']
    if not growth > 100 * LEVY:
        fail('costs no longer grow faster than the levy; the duration page is wrong')
    o5, o10 = ov[5], ov[10]
    out['override-duration'] = TP.page(
        'override-duration',
        'A school-only override that held five years would be %s by our arithmetic; ten years, %s.'
        % (C.usd(o5['levy']), C.usd(o10['levy'])),
        [f('gap28', U(g28), 'the projected school gap, %s (ours)' % C.fy(2028), 'estimate',
           {'y': F(2028)}),
         f('cap', P(100 * LEVY), 'yearly rise in the levy limit, Proposition 2½', 'statute',
           allow=('2½',)),
         f('growth', P(growth, 2), 'yearly growth in what the schools buy (ours)', 'estimate'),
         f('o1', U(ov[1]['levy']), 'school-only override that covers one year (ours)',
           'estimate'),
         f('o5', U(o5['levy']), 'one that covers five years (ours)', 'estimate'),
         f('o5h', U(o5['onAverageHome']), 'a year on the average home, for five (ours)',
           'estimate'),
         f('o10', U(o10['levy']), 'one that covers ten years (ours)', 'estimate'),
         f('o10h', U(o10['onAverageHome']), 'a year on the average home, for ten (ours)',
           'estimate')],
        [con('An override lifts the levy limit once; the higher limit then grows %s a year.'
             % C.pct(100 * LEVY), ['cap'], {'a': P(100 * LEVY)}),
         con('Our model has school costs growing %s a year, so any fixed override is overtaken in time.'
             % C.pct(growth, 2), ['growth', 'cap', 'o1'], {'a': P(growth, 2)},
             notes=[step('The growth rate is ours: salaries at the %s our model assumes and '
                         'every other line at its own assumed rate.'
                         % C.pct(100 * TS['DEFAULT_RATES']['salaries'], 1), 'gap',
                         {'a': P(100 * TS['DEFAULT_RATES']['salaries'])}, allow=('FY2028',),
                         closes='the successor teachers’ agreement and the FY2028 health '
                                'insurance rates')]),
         con('Five years takes %s, %s a year on the average home; ten takes %s.'
             % (C.usd(o5['levy']), C.usd(o5['onAverageHome']), C.usd(o10['levy'])),
             ['o5', 'o5h', 'o10', 'o10h'],
             {'a': U(o5['levy']), 'b': U(o5['onAverageHome']), 'c': U(o10['levy'])}),
         con('The cost falls on every taxpayer, at %s a year on the average home for ten years.'
             % C.usd(o10['onAverageHome']), ['o10h'], {'a': U(o10['onAverageHome'])})],
        table=dict(caption='The smallest school-only override that covers each run of years',
                   views=[dict(
                       key='size', label='Our arithmetic', total_col=-1, kinds=['stated'] * 2,
                       columns=['Override', 'Average home, a year'],
                       rows=[dict(label='%s year%s' % (C.num(n), '' if n == 1 else 's'),
                                  cells=[C.usd(ov[n]['levy']), C.usd(ov[n]['onAverageHome'])])
                             for n in sorted(ov)],
                       note='Ours: the projection with one school-only override added in FY2028 '
                            'and grown at the levy cap. The average-home figure spreads the '
                            'levy over all FY2026 assessed value.')]),
        said=[said_file('select-board/2025-03-11-minutes-7096.txt',
                        'The options discussed included a multi-year override or utilizing '
                        'one-time funds specifically free cash as a stopgap, however these funds '
                        'should not be used in an operating budget, but as a one-time '
                        'appropriation.', 'Select Board')],
        chart=TP.series('Override size by years covered',
                        ['%s year%s' % (C.num(n), '' if n == 1 else 's') for n in sorted(ov)],
                        [TP.track('School-only override (ours)', [ov[n]['levy'] for n in sorted(ov)],
                                  'estimate', 'bar')], '$',
                        note='Ours: the smallest override added in FY2028 that covers each run of '
                             'years, grown at the levy cap.', note_allow=('FY2028',)),
        sources=[src['model'], src['sb-0311']],
        finding_figures={'a': U(o5['levy']), 'b': U(o10['levy'])})

    # ------------------------------------------------ townwide or school-only
    share = 100 * TS['SHARE']
    sch_lps, omnibus = M['fy27']['lps_appropriation'], M['fy27']['omnibus']
    # SHARE is a difference of two deficits the engine ROUNDS to whole dollars, over a
    # $1,000,000 step, so it carries up to two dollars of rounding: 2e-6. Compared with the
    # exact ratio, not a rounded one -- rounding both sides let a state aid rate change
    # move the comparison across the tolerance on rounding alone (13 October 2026).
    if abs(TS['SHARE'] - sch_lps / omnibus) > 2e-6:
        fail('the schools’ share is no longer the FY27 appropriation over the omnibus')
    two = 2_000_000
    tw = round(two * omnibus / sch_lps)
    out['override-scope'] = TP.page(
        'override-scope',
        'Of the %s Tier 1 question, %s was for the schools; the May %s one named only the schools.'
        % (C.usd(t1), C.usd(t1s), '2024'),
        [f('t1', U(t1), 'Tier 1, May 2026, town and schools', 'published', allow=('May 2026',) + TIER),
         f('t1s', U(t1s), 'of it for the schools (Town)', 'published'),
         f('t2', U(t2), 'Tier 2, May 2026', 'published', allow=('May 2026',) + TIER),
         f('t2s', U(t2s), 'of Tier 2’s budget for the schools (Town)', 'published', allow=TIER),
         f('w24', U(int(w24['amount'])), 'May 2024, “Fund Lunenburg Public Schools”',
           'published', allow=('May 2024',)),
         f('share', P(share), 'schools’ share of the FY2027 omnibus (ours)', 'estimate',
           {'y': F(2027)}),
         f('tw', U(tw), 'general override giving the schools %s (ours)' % C.usd(two),
           'estimate', {'a': U(two)})],
        [con('Tier 1 put %s of %s toward the schools; Tier 2, %s of %s.'
             % (C.usd(t1s), C.usd(t1), C.usd(t2s), C.usd(t2)), ['t1', 't1s', 't2', 't2s'],
             {'a': U(t1s), 'b': U(t1), 'c': U(t2s), 'd': U(t2)}, allow=TIER),
         con('The May %s question, for %s, named the schools as its purpose.'
             % ('2024', C.usd(int(w24['amount']))), ['w24'], {'a': U(int(w24['amount']))},
             allow=('2024',)),
         con('Split at the schools’ %s share (our assumption), %s townwide gives them %s.'
             % (C.pct(share), C.usd(tw), C.usd(two)), ['share', 'tw'],
             {'a': P(share), 'b': U(tw), 'c': U(two)}),
         con('Either way the levy is raised on every taxpayer; only the use of it differs.',
             ['t1', 'w24'])],
        chart=TP.ranking('What each question was for', [
            ('%s, May 2026' % TIER[0], [t1s, t1 - t1s]),
            ('%s, May 2026' % TIER[1], [t2s, t2 - t2s]),
            ('May 2024 question', [int(w24['amount']), None])], '$',
            stack=['For the schools', 'The rest (our subtraction)'],
            note='The Town’s release gives the schools’ part of each tier. The May %s question '
                 'named only the schools.' % '2024', note_allow=('2024',)),
        sources=[src['release'], src['dls'], src['d-dls'], src['model']],
        finding_figures={'a': U(t1), 'b': U(t1s)}, finding_allow=('2024',) + TIER)

    # ------------------------------------------------ school user fees
    lev = {l['id']: l for l in M['levers']}
    act, bus = lev['activity_fees'], lev['bus_fees']
    if act['basisKnown'] is not False or bus['basisKnown'] is not False:
        fail('a fee lever’s participation is now known; the page calls it assumed')
    if bus['selfFunding'] is not None or bus['peakYield'] >= bus['cap']:
        fail('the bus fee now reaches self-funding; the page says it does not')
    if act['current'] != 0 or act['selfFunding'] is None:
        fail('the activity fee lever no longer starts at no fee and self-funds')
    if M['expenseBase']['transport'] != bus['cap']:
        fail('the bus lever’s cost is no longer the budget’s general education transport')
    if M['currentFees']['bus']['full_single'] != bus['current']:
        fail('the bus lever’s current fee is not the published fee')
    bf = json.load(open(os.path.join(OUT_DIR, 'bus-fee.json'), encoding='utf-8'))
    pub_fee = next(x for x in bf['facts'] if x['id'] == 'fee-one')['value']['value']
    requests = next(x for x in bf['facts'] if x['id'] == 'requests')['value']['value']
    if pub_fee != bus['current']:
        fail('the bus-fee topic and the lever disagree on the fee')
    # THE ACTIVITY FEE THAT IS CHARGED. This page said "whether any activity fee is charged
    # today" was unknown, while the Family fees page cited the School Committee's 7 May 2025
    # vote "for a universal increase from $55 to $70" -- two pages on one shelf disagreeing
    # (found 14 October 2026). Read from the same payload, the same quote, checked verbatim.
    act_def = load('what-families-pay.json')['household']['charge_defs']['activity:%d' % FAM_FY]
    act_now = float(re.search(r'to \$(\d+)$', act_def['quote']).group(1))
    act_gain = min(act['cap'], act['peakYield']) - act['currentYield']
    bus_gain = bus['peakYield'] - bus['currentYield']
    both = act_gain + bus_gain
    bshare = 100 * both / g28
    out['school-user-fees'] = TP.page(
        'school-user-fees',
        'At their limits, bus and activity fees would add %s by our estimate: %s of the %s gap.' % (C.usd(both), C.pct(bshare), C.fy(2028)),
        [f('both', U(both), 'added by both fees at their limits (ours)', 'estimate'),
         f('share', P(bshare), 'of the projected %s gap (ours)' % C.fy(2028), 'estimate',
           {'y': F(2028)}),
         f('busfee', U(bus['current']), 'bus fee, one rider, a year', 'published'),
         f('buscost', U(bus['cap']), 'general education buses, %s budget' % C.fy(2027),
           'published', {'y': F(2027)}),
         f('buspeak', U(bus['peakYield']), 'the most a bus fee raises, at %s (ours)'
           % C.usd(bus['peakFee']), 'estimate', {'a': U(bus['peakFee'])}),
         f('busnow', U(bus['currentYield']), 'what %s raises now, on our rider count'
           % C.usd(bus['current']), 'estimate', {'a': U(bus['current'])}),
         f('riders', N(bus['basis'], 'riders'), 'paying riders the model assumes (ours)',
           'estimate'),
         f('requests', N(requests, 'requests'), 'bus requests, June 2025', 'published',
           allow=('June 2025',)),
         f('actcost', U(act['cap']), 'music post, supplies, band buses, advisors (ours)',
           'estimate'),
         f('actfee', U(act['selfFunding']), 'activity fee that would cover them (ours)',
           'estimate'),
         f('actn', N(act['basis'], 'students'), 'activity participants the model assumes (ours)',
           'estimate'),
         f('actnow', U(act_now), 'student activity fee, a child, voted 7 May 2025', 'published',
           allow=('7 May 2025',))],   # what it pays for is the note on the activity conclusion
        [con('No bus fee covers general transport: our model peaks at %s against %s.'
             % (C.usd(bus['peakYield']), C.usd(bus['cap'])), ['buspeak', 'buscost'],
             {'a': U(bus['peakYield']), 'b': U(bus['cap'])}),
         con('An activity fee of %s would cover %s of programmes, on %s students we assumed.'
             % (C.usd(act['selfFunding']), C.usd(act['cap']), C.num(act['basis'])),
             ['actfee', 'actcost', 'actn', 'actnow'],
             {'a': U(act['selfFunding']), 'b': U(act['cap']), 'c': N(act['basis'])},
             notes=[step('Our model counts from no fee. The %s fee voted in May 2025 is not in it, '
                         'so what a higher fee adds is overstated by what %s raises, unless it pays '
                         'for other things.' % (C.usd(act_now), C.usd(act_now)), 'gap',
                         figures={'a': U(act_now)}, allow=('May 2025',),
                         closes='the district’s activity fee schedule and the fund its receipts go to')]),
         con('The model assumes %s paying riders; the district reported %s bus requests.'
             % (C.num(bus['basis']), C.num(requests)), ['riders', 'requests', 'busnow'],
             {'a': N(bus['basis']), 'b': N(requests)},
             notes=[step('Which requests pay, and at which rate, is not published, so neither '
                         'count settles the yield.', 'gap',
                         closes='the district’s count of riders by fee category')]),
         con('Both are paid by the families whose children ride or perform: %s at most.'
             % C.usd(both), ['both', 'share'], {'a': U(both)})],
        said=[said_file('school-committee/2025-06-04-minutes-7251.txt',
                        'We have received 1,074 bus requests, and have 494 unpaid at this time.',
                        'School Committee'),
              said_file('school-committee/2025-05-07-minutes-7207.txt',
                        'the committee ultimately decides for a universal increase from $55 to $70',
                        'School Committee')],
        chart=TP.parts('Fees against the projected gap', [
            ('Bus fee at its peak (ours)', bus_gain), ('Activity fee at its cap (ours)', act_gain),
            ('Left open (ours)', g28 - both)], '$', basis='estimate',
            note='The %s gap as our model projects it; each fee’s part is what it adds over '
                 'today, on participation we assumed.' % C.fy(2028), note_figures={'y': F(2028)}),
        sources=[src['model'], src['sc-0604'], src['sc-0507']],
        finding_figures={'a': U(both), 'b': P(bshare), 'y': F(2028)})

    # ------------------------------------------------ cutting the extras
    progs = M['programs']
    extra = sorted([p for p in progs if p['cat'] in ('athletics', 'arts', 'activities')
                    and p['status'] in ('funded', 'restoring')], key=lambda p: -p['cost'])
    etot = round(sum(p['cost'] for p in extra))
    efte = round(sum(p['fte'] for p in extra), 1)
    sports = next(p for p in extra if p['id'] == 'athletics_remaining')['cost']
    ath = M['athletics']
    already = ath['levelService'] - ath['adopted']
    if already != M['facts']['athleticsAlreadyCut'] or ath['adopted'] != sports:
        fail('the athletics cut no longer reads level service less adopted')
    eshort = g28 - etot
    eshare = 100 * etot / g28
    out['extracurricular-cuts'] = TP.page(
        'extracurricular-cuts',
        'Cutting every extra still funded saves %s by our grouping, %s of the %s gap.'
        % (C.usd(etot), C.pct(eshare), C.fy(2028)),
        [f('total', U(etot), 'sports, music, art and clubs still funded (ours)', 'estimate'),
         f('fte', figure(efte, '%.1f positions' % efte, 'positions'), 'of staff in them',
           'estimate'),
         f('sports', U(sports), 'sports and coaches, %s adopted budget' % C.fy(2027),
           'published', {'y': F(2027)}),
         f('already', U(already), 'athletics, level service less adopted, %s' % C.fy(2027),
           'published', {'y': F(2027)}),
         f('gap28', U(g28), 'the projected gap, %s (ours)' % C.fy(2028), 'estimate',
           {'y': F(2028)}),
         f('share', P(eshare), 'of it covered by cutting all of them (ours)', 'estimate'),
         f('short', U(eshort), 'of the %s gap left after (ours)' % C.fy(2028), 'estimate',
           {'y': F(2028)})],
        [con('Every sport, band, club and art supply still funded comes to %s, %s positions.'
             % (C.usd(etot), '%.1f' % efte), ['total', 'fte'],
             {'a': U(etot), 'b': figure(efte, '%.1f' % efte, 'positions')}),
         con('Cut entirely, they leave %s of the %s gap open (ours).'
             % (C.usd(eshort), C.fy(2028)), ['short', 'gap28', 'share'],
             {'a': U(eshort), 'y': F(2028)}),
         con('The %s budget already took %s from athletics; %s of sports remain.'
             % (C.fy(2027), C.usd(already), C.usd(sports)), ['already', 'sports'],
             {'y': F(2027), 'a': U(already), 'b': U(sports)}),
         con('The cut falls on the students in those programmes and the staff who run them.',
             ['total', 'fte'])],
        table=dict(caption='What is still funded outside the classroom', views=[dict(
            key='lines', label='The catalogue', total_col=-1, kinds=['stated'],
            columns=['Budgeted'],
            rows=[dict(label=p['name'], cells=[C.usd(p['cost'])]) for p in extra],
            note='Our programme catalogue, built from the FY27 budget lines and the September '
                 '2026 spending plan. The grouping into extras is ours.')]),
        chart=TP.parts('Extras against the projected gap', [
            ('Every extra still funded (ours)', etot), ('Left open (ours)', eshort)], '$',
            basis='estimate',
            note='The %s gap as our model projects it; the grouping into extras is ours.'
                 % C.fy(2028), note_figures={'y': F(2028)}),
        sources=[src['workbook'], src['model']],
        finding_figures={'a': U(etot), 'b': P(eshare), 'y': F(2028)})

    # ------------------------------------------------ classroom positions
    add = text_of(ADDENDUM_TXT)
    d = addendum_d(add)
    verbatim(add, 'pushing student-to-teacher ratios to 27-30 students per classroom',
             where='addendum')
    cpf, head = TS['COST_PER_FTE'], TS['HEADCOUNT']
    p28, plast = g28 / cpf, gaps[last_fy] / cpf
    out['classroom-positions'] = TP.page(
        'classroom-positions',
        'At %s a position (ours), the %s gap is %.1f positions; %s already cut %s classroom '
        'teachers.' % (C.usd(cpf), C.fy(2028), p28, C.fy(2027), C.num(d['classroom'])),
        [f('cpf', U(cpf), 'a position, our catalogue’s average cost', 'estimate'),
         f('p28', POS(p28), 'the %s gap, in positions (ours)' % C.fy(2028), 'estimate',
           {'y': F(2028)}),
         f('plast', POS(plast), 'the %s gap, in positions (ours)' % C.fy(2000 + last_fy),
           'estimate', {'y': F(2000 + last_fy)}),
         f('head', N(head, 'positions'), 'on the salary line at that average (ours)',
           'estimate'),
         f('cut4', N(d['classroom'], 'teachers'), 'classroom teachers cut, %s, Primary and '
           'Turkey Hill' % C.fy(2027), 'published', {'y': F(2027)}),
         f('size', figure(27, '27-30', 'students'), 'students a room, the district’s forecast',
           'published'),
         f('size-gap', None, 'class sizes by school and grade', 'gap',
           closes='a class-size report by school and grade for FY2027')],
        [con('The %s gap equals %.1f average positions; by %s it equals %.1f (ours).'
             % (C.fy(2028), p28, C.fy(2000 + last_fy), plast), ['p28', 'plast', 'cpf'],
             {'y': F(2028), 'a': figure(p28, '%.1f' % p28, 'positions'),
              'z': F(2000 + last_fy), 'b': figure(plast, '%.1f' % plast, 'positions')}),
         con('%s cut %s classroom teachers; the district wrote that rooms would reach 27-30.'
             % (C.fy(2027), C.num(d['classroom'])), ['cut4', 'size'],
             {'y': F(2027), 'a': N(d['classroom'])}, allow=('27-30',)),
         con('No class sizes by school and grade are published, so a cut’s effect is not '
             'measured here.', ['size-gap']),
         con('The cut falls on the students in larger classes and the staff whose posts go.',
             ['cut4'])],
        chart=TP.series('The gap counted in positions', [C.fy(2000 + y) for y in sorted(gaps)],
                        [TP.track('Projected gap in average positions (ours)',
                                  [gaps[y] / cpf for y in sorted(gaps)], 'estimate', 'bar')],
                        'positions',
                        note='Ours: each year’s projected gap divided by %s, our catalogue’s '
                             'average cost of a position.' % C.usd(cpf), note_figures={'a': U(cpf)}),
        sources=[src['addendum'], src['model']],
        finding_figures={'a': U(cpf), 'y': F(2028), 'p': figure(p28, '%.1f' % p28, 'positions'),
                         'z': F(2027), 'c': N(d['classroom'])})

    # ------------------------------------------------ FY2027: how big the cut was
    sc = M['scenarios']
    ls, bal = sc['level_service'], sc['balanced']
    diff = ls - bal
    var_d, def7, h_ls, h_bal = 868_918, 838_413, 256.5, 253
    verbatim(add, 'Variance from Level Service: -$868,918', 'Surplus / (Deficit) $838,413',
             '256.5', 'Total Expenditures $27,410,701', where='addendum')
    if '\n253 \n' not in open(ADDENDUM_TXT, encoding='utf-8').read():
        fail('the addendum’s Balanced headcount of 253 is no longer printed')
    cat_cut = [p for p in progs if p['status'] == 'cut']
    cat_tot = round(sum(p['cost'] for p in cat_cut))
    ours = next(p for p in cat_cut if p['id'] == 'music_thes_02')['cost']
    out['fy2027-cut-size'] = TP.page(
        'fy2027-cut-size',
        'The workbook puts the adopted %s school budget %s below Level Service; the addendum '
        'states %s.' % (C.fy(2027), C.usd(diff), C.usd(var_d)),
        [f('ls', U(ls), 'Level Service, the %s workbook' % C.fy(2027), 'published',
           {'y': F(2027)}),
         f('bal', U(bal), 'Balanced, as adopted', 'published'),
         f('diff', U(diff), 'between them (our subtraction)', 'published'),
         f('var', U(var_d), 'variance the addendum states for Balanced', 'published'),
         f('def7', U(def7), 'Level Service deficit, the addendum’s summary', 'published'),
         f('listed', U(d['dollars']), 'priced staff reductions it lists (our sum)', 'published'),
         f('listfte', figure(d['fte'], '%.1f FTE' % d['fte'], 'FTE'),
           'staff reductions it lists', 'published'),
         f('heads', figure(h_ls - h_bal, '%.1f FTE' % (h_ls - h_bal), 'FTE'),
           'between its own two headcounts', 'published'),
         f('catalogue', U(cat_tot), 'our catalogue’s %s cuts, all kinds' % C.num(len(cat_cut)),
           'estimate', {'n': N(len(cat_cut))}),
         f('music-gap', None, 'the price of the Turkey Hill music cut', 'gap',
           closes='the district’s price for the 0.2 music post its addendum left blank')],
        [con('The workbook gives %s; the addendum states %s and, elsewhere, %s.'
             % (C.usd(diff), C.usd(var_d), C.usd(def7)), ['diff', 'var', 'def7', 'ls', 'bal'],
             {'a': U(diff), 'b': U(var_d), 'c': U(def7)}),
         con('The addendum lists %s FTE of reductions; its two headcounts differ by %s FTE.'
             % ('%.1f' % d['fte'], '%.1f' % (h_ls - h_bal)), ['listfte', 'heads', 'listed'],
             {'a': figure(d['fte'], '%.1f' % d['fte'], 'FTE'),
              'b': figure(h_ls - h_bal, '%.1f' % (h_ls - h_bal), 'FTE')}),
         con('Our catalogue of %s cuts sums to %s, including %s we priced ourselves.'
             % (C.num(len(cat_cut)), C.usd(cat_tot), C.usd(ours)), ['catalogue', 'music-gap'],
             {'n': N(len(cat_cut)), 'a': U(cat_tot), 'b': U(ours)},
             notes=[step('The documents do not say which of the three variances the School '
                         'Committee voted against.', 'gap', allow=('March 2026',),
                         closes='the School Committee’s minutes of its March 2026 budget vote')])],
        chart=TP.ranking('One cut, measured four ways', [
            ('Workbook: Level Service less Balanced', diff),
            ('Addendum: variance for Balanced', var_d),
            ('Addendum: Level Service deficit', def7),
            ('Addendum: priced reductions (our sum)', d['dollars'])], '$',
            note='The district printed three of these; the fourth is our sum of the reductions '
                 'the addendum prices. Nothing published reconciles them.'),
        sources=[src['workbook'], src['addendum'], src['model']],
        finding_figures={'y': F(2027), 'a': U(diff), 'b': U(var_d)})

    # ------------------------------------------------ the teachers' contract
    ct = text_of(CONTRACT_TXT)
    verbatim(ct, 'to be in effect from July 1, 2024 through June 30, 2027',
             'a. FY25: Appendix B, 2.5% adjustment to salary schedule',
             'b. FY26: Appendix B, 4% adjustment to salary schedule',
             'c. FY27: Appendix B, 3.5% adjustment to salary schedule', where='agreement')
    K = TS['CONTRACT']
    if [c['pct'] for c in K['cola']] != [0.025, 0.04, 0.035] or K['expires'] != 'June 30, 2027':
        fail('the projection’s contract terms no longer match the agreement')
    scale = list(csv.DictReader(open(SCALE_CSV, encoding='utf-8')))
    low = min(scale, key=lambda r: int(r['fy27']))
    high = max(scale, key=lambda r: int(r['fy27']))
    if (low['step'], low['lane'], high['lane']) != ('1', 'Bach', 'Doctorate'):
        fail('the FY27 scale’s ends are no longer bachelor’s step 1 and doctorate')
    comp = 100 * K['compound']
    S = TS['SETTLEMENT']
    sal = 100 * TS['DEFAULT_RATES']['salaries']
    at = {round(r['rate'], 4): r for r in S['rates']}
    if S['assumed'] != TS['DEFAULT_RATES']['salaries'] or at[S['assumed']]['gap'] != g28:
        fail('the settlement table’s assumed rate no longer reproduces the gap')
    out['teacher-contract'] = TP.page(
        'teacher-contract',
        'The teachers’ agreement ends 30 June 2027; each half point on the next moves the %s '
        'gap %s (ours).' % (C.fy(2028), C.usd(S['perHalfPoint'])),
        [f('ends', figure(2027, '30 June 2027', 'date'), 'the teachers’ agreement runs to',
           'contract'),
         f('c25', P(2.5), 'scale increase, %s' % C.fy(2025), 'contract', {'y': F(2025)}),
         f('c26', P(4.0), 'scale increase, %s' % C.fy(2026), 'contract', {'y': F(2026)}),
         f('c27', P(3.5), 'scale increase, %s' % C.fy(2027), 'contract', {'y': F(2027)}),
         f('comp', P(comp, 2), 'the three, compounded', 'contract'),
         f('low', U(int(low['fy27'])), 'bachelor’s, first step, %s' % C.fy(2027), 'contract',
           {'y': F(2027)}),
         f('high', U(int(high['fy27'])), 'doctorate, top step, %s' % C.fy(2027), 'contract',
           {'y': F(2027)}),
         f('assumed', P(sal), 'yearly salary growth our model assumes', 'estimate'),
         f('half', U(S['perHalfPoint']), '%s gap, per half point settled (ours)' % C.fy(2028),
           'estimate', {'y': F(2028)}),
         f('at25', U(at[0.025]['gap']), '%s gap at a 2.5%% settlement (ours)' % C.fy(2028),
           'estimate', {'y': F(2028)}, allow=('2.5%',)),
         f('at5', U(at[0.05]['gap']), '%s gap at 5.0%% (ours)' % C.fy(2028), 'estimate',
           {'y': F(2028)}, allow=('5.0%',)),
         f('next-gap', None, 'the terms of the next agreement', 'gap',
           closes='the successor agreement, or bargaining parameters adopted in open session')],
        [con('The agreement raised the scale %s, %s and %s: %s compounded.'
             % ('2.5%', '4%', '3.5%', C.pct(comp, 2)), ['c25', 'c26', 'c27', 'comp'],
             {'a': P(comp, 2)}, allow=('2.5%', '4%', '3.5%')),
         con('Our model assumes salaries grow %s a year from %s; that is our assumption.'
             % (C.pct(sal), C.fy(2028)), ['assumed', 'next-gap'], {'a': P(sal), 'y': F(2028)}),
         con('At a %s settlement the %s gap would be %s; at %s, %s (ours).'
             % ('2.5%', C.fy(2028), C.usd(at[0.025]['gap']), '5.0%', C.usd(at[0.05]['gap'])),
             ['at25', 'at5', 'half'],
             {'y': F(2028), 'a': U(at[0.025]['gap']), 'b': U(at[0.05]['gap'])},
             allow=('2.5%', '5.0%')),
         con('A lower settlement is borne in pay by the people on the scale.',
             ['low', 'high'])],
        table=dict(caption='The gap at each settlement, everything else held', views=[dict(
            key='settle', label='Our arithmetic', total_col=-1, kinds=['stated'] * 2,
            columns=['%s gap' % C.fy(2028), '%s gap' % C.fy(2032)],
            rows=[dict(label=C.pct(100 * r['rate'], 1), cells=[C.usd(r['gap']), C.usd(r['fy32'])])
                  for r in S['rates']],
            note='Ours: the projection with only the salary growth rate changed. The rate '
                 'applies to the whole salary line, not only the teachers’ scale.')]),
        chart=TP.series('The gap at each settlement',
                        ['%s a year' % C.pct(100 * r['rate'], 1) for r in S['rates']], [
                            TP.track('%s gap (ours)' % C.fy(2028), [r['gap'] for r in S['rates']],
                                     'estimate', 'bar'),
                            TP.track('%s gap (ours)' % C.fy(2032), [r['fy32'] for r in S['rates']],
                                     'estimate', 'bar')], '$',
                        note='Ours: only the salary growth rate changes. Our model assumes %s.'
                             % C.pct(sal), note_figures={'a': P(sal)}),
        sources=[src['contract'], src['scale'], src['model']],
        finding_figures={'y': F(2028), 'a': U(S['perHalfPoint'])},
        finding_allow=('30 June 2027',))

    # ------------------------------------------------ the salary line and staffing
    CF = TS['COUNTERFACTUAL']
    sh = TS['shrink']
    cap_cf = next(s for s in CF['scenarios'] if abs(s['rate'] - LEVY) < 1e-9)
    mid = next(s for s in scale if s['step'] == '5' and s['lane'] == 'Masters')
    if int(mid['fy27']) != K['samples'][1]['pay']:
        fail('the projection’s mid-scale sample is no longer master’s step 5 at FY27')
    out['salary-line-and-staffing'] = TP.page(
        'salary-line-and-staffing',
        'Held to %s while pay rises %s, the salary line loses %.1f positions a year, by our '
        'arithmetic.' % (C.pct(100 * LEVY), C.pct(sal), sh['positionsPerYear']),
        [f('pos', POS(sh['positionsPerYear']), 'a year, line at %s, pay at %s (ours)'
           % (C.pct(100 * LEVY), C.pct(sal)), 'estimate', {'a': P(100 * LEVY), 'b': P(sal)}),
         f('ten', P(100 * sh['after10']), 'of positions gone in ten years, that way (ours)',
           'estimate'),
         f('head', N(TS['HEADCOUNT'], 'positions'), 'on the salary line, our average', 'estimate'),
         f('lea', U(CF['payroll']), 'payroll under the teachers’ agreement (our sum)',
           'estimate'),
         f('cf28', U(cap_cf['fy28']), '%s gap had raises been %s (ours)'
           % (C.fy(2028), C.pct(100 * LEVY)), 'estimate', {'y': F(2028), 'a': P(100 * LEVY)}),
         f('act28', U(CF['actual']['fy28']), 'the %s gap as projected (ours)' % C.fy(2028),
           'estimate', {'y': F(2028)}),
         f('cf32', U(cap_cf['fy32']), '%s gap on the same path (ours)' % C.fy(2032),
           'estimate', {'y': F(2032)}),
         f('act32', U(CF['actual']['fy32']), 'the %s gap as projected (ours)' % C.fy(2032),
           'estimate', {'y': F(2032)}),
         f('mid', P(100 * cap_cf['perCent']), 'less pay, master’s step 5, on that path (ours)',
           'estimate', allow=('5',))],
        [con('Holding the line to %s with %s raises removes %.1f positions a year; %s in ten.'
             % (C.pct(100 * LEVY), C.pct(sal), sh['positionsPerYear'], C.pct(100 * sh['after10'])),
             ['pos', 'ten', 'head'],
             {'a': P(100 * LEVY), 'b': P(sal),
              'c': figure(sh['positionsPerYear'], '%.1f' % sh['positionsPerYear'], 'positions'),
              'd': P(100 * sh['after10'])}),
         con('Had the last three raises been %s a year, the %s gap would be %s, not %s.'
             % (C.pct(100 * LEVY), C.fy(2028), C.usd(cap_cf['fy28']), C.usd(CF['actual']['fy28'])),
             ['cf28', 'act28', 'lea'],
             {'a': P(100 * LEVY), 'y': F(2028), 'b': U(cap_cf['fy28']),
              'c': U(CF['actual']['fy28'])}),
         con('By %s that path gives %s instead of %s: lower, and still growing.'
             % (C.fy(2032), C.usd(cap_cf['fy32']), C.usd(CF['actual']['fy32'])),
             ['cf32', 'act32'],
             {'y': F(2032), 'a': U(cap_cf['fy32']), 'b': U(CF['actual']['fy32'])}),
         con('One path costs positions, the other pay: %s less for a mid-scale teacher.'
             % C.pct(100 * cap_cf['perCent']), ['mid', 'pos'],
             {'a': P(100 * cap_cf['perCent'])})],
        table=dict(caption='If the last three raises had been smaller', views=[dict(
            key='cf', label='Our arithmetic', total_col=-1, kinds=['stated'] * 3,
            columns=['Payroll lower by', '%s gap' % C.fy(2028), '%s gap' % C.fy(2032)],
            rows=[dict(label='as settled', cells=['—', C.usd(CF['actual']['fy28']),
                                                  C.usd(CF['actual']['fy32'])])]
            + [dict(label='%s a year' % C.pct(100 * s['rate'], 1),
                    cells=[C.usd(s['lower']), C.usd(s['fy28']), C.usd(s['fy32'])])
               for s in CF['scenarios']],
            note='Ours: the teachers’ payroll in the FY27 budget lines, rebuilt as if each of '
                 'the three scale increases had been the rate shown. Steps and lanes are left '
                 'as they are.')]),
        chart=TP.series('The gap had raises been smaller',
                        ['As settled'] + ['%s a year' % C.pct(100 * s['rate'], 1)
                                          for s in CF['scenarios']], [
                            TP.track('%s gap (ours)' % C.fy(2028),
                                     [CF['actual']['fy28']] + [s['fy28'] for s in CF['scenarios']],
                                     'estimate', 'bar'),
                            TP.track('%s gap (ours)' % C.fy(2032),
                                     [CF['actual']['fy32']] + [s['fy32'] for s in CF['scenarios']],
                                     'estimate', 'bar')], '$',
                        note='Ours: the teachers’ payroll rebuilt as if each of the last three '
                             'scale increases had been the rate shown.'),
        sources=[src['contract'], src['scale'], src['workbook'], src['model']],
        finding_figures={'a': P(100 * LEVY), 'b': P(sal),
                         'c': figure(sh['positionsPerYear'], '%.1f' % sh['positionsPerYear'],
                                     'positions')})

    # ------------------------------------------------ the hub
    h = {}
    h['h-gap'] = f('h-gap', U(g28), 'the projected school gap, %s (ours)' % C.fy(2028),
                   'estimate', {'y': F(2028)})
    h['h-glast'] = f('h-glast', U(gaps[last_fy]), 'the same gap by %s (ours)'
                     % C.fy(2000 + last_fy), 'estimate', {'y': F(2000 + last_fy)})
    h['h-lost'] = f('h-lost', N(len(l26), 'questions'), 'override questions lost, 16 May 2026',
                    'published', allow=('16 May 2026',))
    h['h-o5'] = f('h-o5', U(o5['levy']), 'override covering five years (ours)', 'estimate')
    h['h-fees'] = f('h-fees', U(both), 'bus and activity fees at their limits (ours)',
                    'estimate')
    h['h-extras'] = f('h-extras', U(etot), 'every extra still funded (ours)', 'estimate')
    h['h-pos'] = f('h-pos', POS(p28), 'the %s gap, in positions (ours)' % C.fy(2028),
                   'estimate', {'y': F(2028)})
    h['h-cut27'] = f('h-cut27', U(diff), '%s budget below Level Service' % C.fy(2027),
                     'published', {'y': F(2027)})
    h['h-half'] = f('h-half', U(S['perHalfPoint']), 'per half point on the next teachers’ '
                    'settlement (ours)', 'estimate')
    h['h-ends'] = f('h-ends', figure(2027, '30 June 2027', 'date'),
                    'the teachers’ agreement runs to', 'contract')
    h['h-size-gap'] = f('h-size-gap', None, 'class sizes by school and grade', 'gap',
                        closes='a class-size report by school and grade for FY2027')
    tiers = [
        LD.tier('The gap', [h['h-gap'], h['h-glast']]),
        LD.tier('What each option yields', [h['h-o5'], h['h-fees'], h['h-extras'], h['h-pos'],
                                            h['h-half']]),
        LD.tier('What the record shows', [h['h-lost'], h['h-cut27'], h['h-ends'],
                                          h['h-size-gap']]),
    ]
    mx = LD.matrix(
        [('gap', 'The gap'), ('levy', 'Override'), ('fees', 'Fees'), ('cuts', 'Cuts'),
         ('pay', 'Pay')],
        [('yields', 'What it is worth (ours)'), ('record', 'What the record shows')],
        {('gap', 'yields'): ['h-gap', 'h-glast'], ('levy', 'yields'): ['h-o5'],
         ('fees', 'yields'): ['h-fees'], ('cuts', 'yields'): ['h-extras', 'h-pos'],
         ('pay', 'yields'): ['h-half'], ('levy', 'record'): ['h-lost'],
         ('cuts', 'record'): ['h-cut27', 'h-size-gap'], ('pay', 'record'): ['h-ends']})
    hub_ladder = LD.ladder(tiers, [
        LD.conclusion('Our model projects a %s school gap of %s, growing to %s by %s.'
                      % (C.fy(2028), C.usd(g28), C.usd(gaps[last_fy]), C.fy(2000 + last_fy)),
                      ['h-gap', 'h-glast'],
                      {'y': F(2028), 'a': U(g28), 'b': U(gaps[last_fy]),
                       'z': F(2000 + last_fy)}),
        LD.conclusion('An override covering five years is %s, paid by every taxpayer (ours).'
                      % C.usd(o5['levy']), ['h-o5', 'h-lost'], {'a': U(o5['levy'])}),
        LD.conclusion('Bus and activity fees add at most %s, paid by the families who use them.'
                      % C.usd(both), ['h-fees'], {'a': U(both)}),
        LD.conclusion('Cutting every extra saves %s; the gap is %.1f positions (ours).'
                      % (C.usd(etot), p28), ['h-extras', 'h-pos', 'h-size-gap'],
                      {'a': U(etot), 'b': figure(p28, '%.1f' % p28, 'positions')}),
        LD.conclusion('Each half point on the next teachers’ agreement moves the gap %s (ours).'
                      % C.usd(S['perHalfPoint']), ['h-half', 'h-ends'],
                      {'a': U(S['perHalfPoint'])}),
        LD.conclusion('%s was already %s below Level Service.' % (C.fy(2027), C.usd(diff)),
                      ['h-cut27'], {'y': F(2027), 'a': U(diff)}),
    ], matrix=mx)
    out['budget-options'] = TP.hub(
        'budget-options',
        'Against a projected %s gap of %s (ours), each option has a size and a payer: an '
        'override, fees, cuts to programmes or positions, reserves, or the next teachers’ settlement.'
        % (C.fy(2028), C.usd(g28)),
        hub_ladder,
        chart=TP.ranking('Each option against the gap', [
            ('Projected gap (ours)', g28), ('Every extra still funded', etot),
            ('Bus and activity fees at their limits', both),
            ('Each half point on the next settlement', S['perHalfPoint'])], '$',
            highlight='Projected gap (ours)', basis='estimate',
            note='All ours, for %s: our projection, our grouping of extras, our fee arithmetic.'
                 % C.fy(2028), note_figures={'y': F(2028)}),
        answer_figures={'y': F(2028), 'a': U(g28)})

    out.update(family_fee_pages())

    if sorted(k for k in out if k != 'budget-options') != sorted(MINE):
        fail('the pages built are not the pages the registry gives this script: %s'
             % sorted(set(MINE) ^ set(out)))
    return out

# --------------------------------------------------------------------- what a family pays
# Absorbs /what-families-pay (`families`), 14 October 2026. Every figure is read off that
# report's own payload, fy28/public/data/what-families-pay.json (build_what_families_pay.py),
# whose household bills are priced there -- nothing here prices a household. What is checked
# here is that the bill's parts still add up, and that every rate still stands verbatim in the
# document it came from.
#
# FY2026, NOT THE YEAR NOW RUNNING. The payload's own headline household is FY2027, and its
# athletic rates come from an email to families this archive does not hold
# (athletic-fee-schedule.csv: `source not held`). The Athletics shelf states that year's rate as
# a gap, and two pages on one shelf must not disagree, so these pages price the last year whose
# every rate is in a document we hold, and say so.

FAM_FY = 2026
# A count that opens a sentence is spelled; it is still the count, indexed rather than typed.
WORDS = ('No', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten',
         'Eleven', 'Twelve')
# Where each unpriced charge is NAMED, read off the start of its rate-register source. A charge
# whose source matches none of these refuses the build rather than landing in a wrong row.
NAMED_IN = (('RevTrak payment portal', 'the district’s payment portal'),
            ('Outside the universal meal', 'the cafeteria, no price list held'),
            ('School Committee minutes', 'public comment; paid to shops'),
            ('Superintendent\'s email', 'the Superintendent’s email'))
CORR = os.path.join(ROOT, 'sources', 'correspondence')


def money(v):
    """A household amount as the documents would print it: cents only where there are cents."""
    v = round(float(v), 2)
    return C.usd(v) if v == int(v) else '$' + format(v, ',.2f')


def family_fee_pages():
    W = load('what-families-pay.json')
    man = {r['key'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    spec = {
        'sc-0226': ('meetings/school-committee/2025-02-26-minutes-7076.pdf',
                    'School Committee minutes, 26 February 2025'),
        'sc-0507': ('meetings/school-committee/2025-05-07-minutes-7207.pdf',
                    'School Committee minutes, 7 May 2025'),
        'sc-0626': ('meetings/school-committee/2024-06-26-minutes-6632.pdf',
                    'School Committee minutes, 26 June 2024'),
        'bus26': ('correspondence/2025-05-bus-fees-superintendent.txt',
                  'Superintendent’s email to families on bus fees, May 2025'),
        'bus27': ('correspondence/2026-08-17-bus-routes-and-fees-superintendent.txt',
                  'Superintendent’s email to families, 17 August 2026'),
        'faq': ('district-budget/docs/lhs-athletics-faq.pdf', 'LHS Athletics FAQ'),
    }
    src = {}
    for k, (key, label) in spec.items():
        if key not in man:
            fail('%s is not in archive-manifest.csv' % key)
        src[k] = dict(label='%s — %s' % (label, key.split('/')[-1]), href='/docs/' + key)
    for name, what in (('rate-register.csv', 'every school fee and its source'),
                       ('athletic-fee-schedule.csv', 'the athletic rates, year by year'),
                       ('money-gaps.csv', 'what cannot be answered, and what would settle it')):
        if not os.path.exists(os.path.join(ROOT, 'fy28', 'public', 'docs', 'data', name)):
            fail('/docs/data/%s is not published' % name)
        src[name] = dict(label='Lunenburg Budget Project — %s (%s)' % (name, what),
                         href='/docs/data/' + name)
    src['payload'] = dict(label='Lunenburg Budget Project — what-families-pay.json (every '
                                'household priced)', href='/data/what-families-pay.json')

    M = lambda v: figure(v, money(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=0: figure(v, C.pct(v, dp))
    N = lambda v, unit=None: figure(v, C.num(v), unit)
    f, con = LD.fact, TP.conclusion
    out = {}

    # ---- the rates, each asserted against the document it came from
    sc0226 = text_of(os.path.join(MINUTES, 'school-committee', '2025-02-26-minutes-7076.txt'))
    sc0507 = text_of(os.path.join(MINUTES, 'school-committee', '2025-05-07-minutes-7207.txt'))
    bus26t = text_of(os.path.join(CORR, '2025-05-bus-fees-superintendent.txt'))
    yr = next(y for y in W['years'] if y['fy'] == FAM_FY)
    hs = yr['levels']['HS']
    if hs['ladder']['kind'] != 'percentage' or len(hs['ladder']['rates']) != 1:
        fail('the %s high school schedule is no longer one rate and a sibling percentage' % FAM_FY)
    first, sib = hs['ladder']['rates'][0], hs['ladder']['pct']
    reduced = hs['tiers']['reduced']['flat']
    verbatim(sc0226, 'increase fee for high school up to %s' % C.usd(first),
             'A %s discount for siblings' % C.pct(sib, 0),
             'Reduced fee for high school to %s' % C.usd(reduced),
             where='School Committee minutes of 26 February 2025')
    bus = {k: b['amount'] for k, b in yr['bus'].items()}
    for k, b in yr['bus'].items():
        verbatim(bus26t, b['source_ref'], where='bus fee email of May 2025')
    act = W['household']['charge_defs']['activity:%d' % FAM_FY]
    verbatim(sc0507, act['quote'], where='School Committee minutes of 7 May 2025')
    act_each = float(re.search(r'to \$(\d+)$', act['quote']).group(1))

    # ---- the households, looked up and re-added
    def bill(n, tier='full', on=True):
        b = W['household']['bills']['%d|HS|%d|1|%s|%d|%d|0' % (FAM_FY, n, tier, int(on), int(on))]
        parts = {r['id'].split(':')[0]: r['amount'] for r in b['rows']}
        if abs(sum(parts.values()) - b['floor']) > 0.005 or b['unpriced_in_bill']:
            fail('the %d-child %s bill no longer adds up to its own floor' % (n, tier))
        if any(r['band'] != 'priced' for r in b['rows']):
            fail('a %s rate is no longer priced by a document' % FAM_FY)
        return b['floor'], parts
    hh = {n: bill(n) for n in (1, 2, 3)}
    for n, (tot, p) in hh.items():
        want = first * (1 + (n - 1) * (1 - sib / 100))
        if abs(p['athletics'] - want) > 0.005 or abs(p['activity'] - act_each * n) > 0.005:
            fail('the %d-child athletic or activity fee no longer recomputes' % n)
        if p['bus'] != (bus['one student'] if n == 1 else bus['two or more students']):
            fail('the %d-child bus fee is not the published tier' % n)
    t1, t2, t3 = hh[1][0], hh[2][0], hh[3][0]
    p2 = hh[2][1]
    unpriced = [r for r in W['household']['standing'] if r['band'] == 'unpriced']
    free = [r for r in W['household']['standing'] if r['band'] == 'no charge']

    out['family-fees'] = TP.page(
        'family-fees',
        'Two high schoolers, one sport each, the bus and a club: %s in %s.' % (money(t2),
                                                                              C.fy(FAM_FY)),
        [f('two', M(t2), 'two children, one sport each, bus, a club', 'published'),
         f('one', M(t1), 'one child, the same', 'published'),
         f('three', M(t3), 'three children, the same', 'published'),
         f('ath', M(first), 'athletic fee, first child, a season', 'published'),
         f('sib', P(sib), 'off for each sibling who plays', 'published'),
         f('bus1', M(bus['one student']), 'bus, one child, a year', 'published'),
         f('bus2', M(bus['two or more students']), 'bus, two or more children, a year',
           'published'),
         f('act', M(act_each), 'activity fee, a child; no period stated', 'published'),
         f('unpriced', N(len(unpriced), 'charges'), 'further charges with no published amount',
           'published'),
         f('fy27', None, 'the %s athletic rates, in a document we hold' % C.fy(FAM_FY + 1),
           'gap', {'y': F(FAM_FY + 1)},
           closes='the Superintendent’s August 2026 fee schedule to families, which this '
                  'archive does not hold')],
        [con('Of the %s: %s athletics, %s bus and %s activity fees.'
             % (money(t2), money(p2['athletics']), money(p2['bus']), money(p2['activity'])),
             ['two', 'ath', 'sib', 'bus2', 'act'],
             {'t': M(t2), 'a': M(p2['athletics']), 'b': M(p2['bus']), 'c': M(p2['activity'])},
             notes=[step('Whether the activity fee is charged once a year, a term or an activity '
                         'is not stated; the vote names an amount only.', 'gap',
                         closes='the adopted student activity fee schedule, stating its period')]),
         con('One child is %s; a second adds %s and a third %s: one bus charge, and %s off a '
             'sibling.' % (money(t1), money(t2 - t1), money(t3 - t2), C.pct(sib, 0)),
             ['one', 'two', 'three', 'bus1', 'bus2', 'sib'],
             {'a': M(t1), 'b': M(t2 - t1), 'c': M(t3 - t2), 'p': P(sib)}),
         con('It is a floor: %s more charges a family can meet have no published amount.'
             % C.num(len(unpriced)), ['unpriced'], {'n': N(len(unpriced))}),
         con('These are %s rates; the %s athletic rates are in an email this archive does not '
             'hold.' % (C.fy(FAM_FY), C.fy(FAM_FY + 1)), ['fy27'],
             {'y': F(FAM_FY), 'z': F(FAM_FY + 1)})],
        chart=TP.series('A year of school fees, by family size',
                        ['One child', 'Two children', 'Three children'], [
            TP.track('Athletics', [hh[n][1]['athletics'] for n in (1, 2, 3)], 'published', 'bar'),
            TP.track('Bus', [hh[n][1]['bus'] for n in (1, 2, 3)], 'published', 'bar'),
            TP.track('Activity fee', [hh[n][1]['activity'] for n in (1, 2, 3)], 'published',
                     'bar')], '$', stacked=True, decimals=2,
            note='High school, %s, full fee, one sport each, riding the bus and in a club.'
                 % C.fy(FAM_FY), note_figures={'y': F(FAM_FY)}),
        said=[said_file('school-committee/2025-05-07-minutes-7207.txt',
                        'the committee ultimately decides for a universal increase from $55 to $70',
                        'School Committee')],
        sources=[src['sc-0226'], src['sc-0507'], src['bus26'], src['rate-register.csv'],
                 src['payload']],
        finding_figures={'a': M(t2), 'y': F(FAM_FY)})

    # ---- the same children, three bills
    tc = W['tier_contrast']
    if tc['fy'] != FAM_FY or tc['level'] != 'HS' or tc['sports'] != 1:
        fail('the tier contrast is no longer high school, %s, one sport each' % FAM_FY)
    n = tc['children']
    full_t = hs['tiers']['full']
    grid = {(g['children'], g['sports']): g['per_year'] for g in full_t['grid']}
    red_grid = {(g['children'], g['sports']): g['per_year'] for g in hs['tiers']['reduced']['grid']}
    if abs(grid[(n, 1)] - tc['full']) > 0.005 or abs(red_grid[(n, 1)] - tc['reduced']) > 0.005 \
            or abs(reduced * n - tc['reduced']) > 0.005 or tc['waived'] != 0:
        fail('the three bills for the same children no longer recompute')
    ratio = tc['full'] / tc['reduced']
    if round(ratio, 2) != tc['ratio']:
        fail('the full-to-reduced ratio no longer recomputes')
    faq = text_of(os.path.join(ROOT, 'sources', 'district-budget', 'text', 'lhs-athletics-faq.txt'))
    waived_q = 'Students that are on the free lunch program have the athletic fee waived'
    verbatim(faq, waived_q, where='LHS Athletics FAQ')
    out['reduced-and-waived-fees'] = TP.page(
        'reduced-and-waived-fees',
        '%s high schoolers at one sport each: %s a year at the full fee, %s reduced, %s waived.'
        % (WORDS[n], money(tc['full']), money(tc['reduced']), money(0)),
        [f('full', M(tc['full']), 'full fee, the year (our arithmetic)', 'published'),
         f('red', M(tc['reduced']), 'reduced fee, the year', 'published'),
         f('waived', M(0), 'fee waived, the year', 'published'),
         f('ratio', figure(ratio, '%.2f times' % ratio), 'full against reduced', 'published'),
         f('first', M(first), 'full fee, first child, a season', 'published'),
         f('flat', M(reduced), 'reduced fee, every child, a season', 'published'),
         f('bus2', M(bus['two or more students']), 'bus, two or more children, full', 'published'),
         f('busr', M(bus['two or more, reduced']), 'bus, two or more children, reduced',
           'published'),
         f('busq', M(bus['qualifying families']), 'bus, families who qualify', 'published'),
         f('fy27', None, 'reduced and waived rates for %s' % C.fy(FAM_FY + 1), 'gap',
           {'y': F(FAM_FY + 1)},
           closes='the district’s %s athletic fee schedule, including the reduced and waived '
                  'tiers' % C.fy(FAM_FY + 1))],
        [con('The same %s children cost one family %s a year and another %s: %.2f times.'
             % (C.num(n), money(tc['full']), money(tc['reduced']), ratio),
             ['full', 'red', 'ratio', 'first', 'flat'],
             {'n': N(n), 'a': M(tc['full']), 'b': M(tc['reduced']),
              'r': figure(ratio, '%.2f' % ratio)}),
         con('The reduced fee is a flat %s a child a season; no sibling discount is published '
             'for it.'
             % money(reduced), ['flat'], {'a': M(reduced)}),
         con('The athletics FAQ waives the fee for the free lunch program; the bus is %s for '
             'families who qualify.' % money(bus['qualifying families']),
             ['waived', 'busq', 'busr'], {'b': M(bus['qualifying families'])},
             notes=[step('The FAQ that states the waiver states no year.', 'gap',
                         closes='the district’s current athletic fee schedule, with its '
                                'waiver rule')]),
         con('No reduced or waived rate is published for %s.' % C.fy(FAM_FY + 1), ['fy27'],
             {'y': F(FAM_FY + 1)})],
        chart=TP.ranking('Athletic fee a season, by tier', [
            ('Full fee, first child', first), ('Reduced fee, every child', reduced),
            ('Waived', 0)], '$', highlight='Reduced fee, every child',
            note='High school, %s, as the School Committee voted it and the athletics FAQ states '
                 'the waiver.' % C.fy(FAM_FY), note_figures={'y': F(FAM_FY)}),
        said=[said_file('school-committee/2025-02-26-minutes-7076.txt',
                        'A 25% discount for siblings. Reduced fee for high school to $50 and $40 '
                        'for middle school with a family cap of $1500.', 'School Committee')],
        sources=[src['sc-0226'], src['faq'], src['bus26'], src['athletic-fee-schedule.csv'],
                 src['payload']],
        finding_figures={'a': M(tc['full']), 'b': M(tc['reduced']), 'c': M(0)})

    # ---- what has no price
    gaps = {g['what']: g for g in W['gaps']}
    reg = {x['item']: x for x in W['unpriced']}
    where = {}
    for r in unpriced:
        name = r['id'].split(':', 1)[1]
        s_ = reg.get(name, {}).get('source', '')
        hit = [lab for pre, lab in NAMED_IN if s_.startswith(pre)]
        if len(hit) != 1:
            fail('unpriced charge %r: its source %r names no known place' % (name, s_))
        where[name] = hit[0]
    portal = sum(1 for v in where.values() if v == NAMED_IN[0][1])
    if not free or free[0]['id'] != 'meals':
        fail('the standard school meal is no longer the no-charge row')
    bus27t = text_of(os.path.join(CORR, '2026-08-17-bus-routes-and-fees-superintendent.txt'))
    proc_q = 'RevTrak charges a small processing fee'
    verbatim(bus27t, proc_q, where='Superintendent’s email of 17 August 2026')
    out['unpriced-school-charges'] = TP.page(
        'unpriced-school-charges',
        '%s charges a Lunenburg family can meet have no published amount anywhere in this '
        'archive.' % WORDS[len(unpriced)],
        [f('unpriced', N(len(unpriced), 'charges'), 'charged, with no amount published',
           'published'),
         f('portal', N(portal, 'charges'), 'of them sold on the district’s payment portal',
           'published'),
         f('priced', N(len(hh[2][1]), 'charges'), 'priced by a document we hold, %s'
           % C.fy(FAM_FY), 'published', {'y': F(FAM_FY)}),
         f('free', N(len(free), 'charge'), 'no charge: the standard school meal', 'published'),
         f('proc', None, 'the online payment processing fee', 'gap',
           closes='the RevTrak merchant agreement or the portal’s own fee disclosure')],
        [con('%s charges have no amount in any document here, so any total a family is given is '
             'a floor.' % C.num(len(unpriced)), ['unpriced', 'priced'], {'n': N(len(unpriced))}),
         con('%s are sold on the district’s payment portal, which shows no amount to a plain fetch.'
             % C.num(portal), ['portal'], {'n': N(portal)},
             notes=[step('Preschool, extended day, field trips, parking and device repair are '
                         'among them.', 'gap',
                         closes='the district’s published schedule of student fees, with every '
                                'amount the portal charges')]),
         con('Paying online adds a processing fee; the Superintendent’s email calls it small and '
             'states no rate.', ['proc']),
         con('The standard school meal is free to every student, under the state’s universal '
             'meals funding.', ['free'])],
        chart=TP.parts('What a family can be charged, by evidence', [
            ('Priced by a document we hold', len(hh[2][1])),
            ('Charged, no amount published', len(unpriced)),
            ('No charge', len(free))], 'count',
            note='The charges a high school family can meet in %s, counted from the rate '
                 'register. Nothing here is estimated.' % C.fy(FAM_FY),
            note_figures={'y': F(FAM_FY)}),
        table=dict(caption='Charged, with no amount published', views=[dict(
            key='unpriced', label='Each charge', total_col=-1, kinds=['stated'],
            columns=['Where it is named'],
            rows=[dict(label=x, cells=[where[x]]) for x in sorted(where, key=str.lower)],
            note='Each is offered by the district or named in its own email; none has an amount '
                 'in a budget book, a warrant, a set of minutes or a fee schedule held here.')]),
        said=[said_file('school-committee/2024-06-26-minutes-6632.txt',
                        'Our students would not see any difference', 'School Committee')],
        sources=[src['bus27'], src['sc-0626'], src['rate-register.csv'], src['money-gaps.csv'],
                 src['payload']])
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
        print('budget options topics: %d outputs current' % len(outs))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
