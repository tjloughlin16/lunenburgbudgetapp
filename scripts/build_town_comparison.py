#!/usr/bin/env python3
"""HOW LUNENBURG COMPARES: its neighbours, its peers, the towns that resemble it, and the
places its children actually go.

    python3 scripts/build_town_comparison.py
    python3 scripts/build_town_comparison.py --check

Writes, from one pass over one set of figures (rule 7d):

    fy28/public/data/towns-like-us.json      the payload: stats, grain, conclusions, map, tables
    sources/analyses/towns-like-us.md        the document /docs serves and the PDF renders

THE SLUG IS NOT `how-we-compare`, and that is not a style preference. `routes.ts` already
maps `how-we-compare` as a typo alias onto /what-other-districts-spend, with a comment
rejecting it as a page name because it *reads as a verdict*. A report at
/analysis/how-we-compare would have worked -- the alias keys on the first path segment --
while anybody typing the bare slug landed somewhere else entirely. `towns-like-us` is the
question a resident actually asks, which is this repo's own naming rule.

FOUR COMPARISON SETS, AND THE REASON THERE ARE FOUR RATHER THAN ONE. Every one of them
answers a different question, and folding them together is how a comparison stops meaning
anything:

  * NEIGHBOURS -- the six towns that share a border. Computed from the Census TIGER boundary
    polygons by shared vertices, not from memory: Ashby, Fitchburg, Lancaster, Leominster,
    Shirley, Townsend. Ashby was missing from every comparison this project published until
    26 September 2026, which is exactly why the set is derived rather than listed.
  * PEERS -- the towns this project has compared Lunenburg with since the free-cash work.
    They are OURS. Nothing in the town's record names a cohort: `search_minutes.py
    "comparable communities"` finds a 2023 salary survey citing "the 8 communities that were
    surveyed" and never names them. So this set is labelled as our choice everywhere.
  * TWINS -- the towns the MATH picks, out of all 351. Two cohorts, because TJ asked for both
    and they are not the same question: one matched on what a town IS, one on what it DOES.
  * DESTINATIONS -- where Lunenburg children are actually schooled. Not a peer set at all.
    `per-pupil-spending.md` already draws this line and it is kept here.

WHY THE TWINS ARE RESTRICTED TO SINGLE-TOWN K-12 DISTRICTS. In a regional district the
school bill is split across member towns with different tax bills, different commercial
bases and different votes, so "the same tax bill as us" is not even defined for one. A
single-town K-12 district is the only shape where town finance and school finance are the
same taxpayer -- which is Lunenburg's own shape. 161 of the 351 towns qualify.

AND THE GRADE-SPAN TEST IS A PUBLISHED FACT, NOT A PROXY. The first version admitted any
district that reported a grade-10 MCAS score, and DESE reports those by district of
RESIDENCE -- so Sturbridge came third on structural similarity while being `Burgess
Elementary`, PK-06, with Tantasqua running its high school. Two of the first six candidates
were elementary or middle districts. The test now reads `grades_served` off DESE's
school-level file: does this district operate a school reaching grade 12. Rule 13 -- a
proxy that nearly works is the dangerous kind.

WHAT MATCHING ON AN OUTCOME COSTS, stated because the report leans on it. A cohort matched
on per-pupil spending cannot then be used to ask whether Lunenburg spends like its cohort;
the answer was assumed. So the STRUCTURAL cohort is matched only on things a town does not
choose -- how many children, how poor, how many need services, how valuable the housing,
how much of the base is commercial -- and spending, bills, overrides and their trends are
compared afterwards. The BEHAVIOURAL cohort is the other half of what TJ asked for and is
read the other way round: these towns act like Lunenburg, and the question is whether they
look like it. They do not, and that is the finding.
"""
import argparse
import csv
import json
import math
import os
import statistics as st
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from conclusions import conclusion, figure, emit, usd, pct  # noqa: E402

OUT_JSON = os.path.join(ROOT, 'fy28', 'public', 'data', 'towns-like-us.json')
CHARTS = os.path.join(ROOT, 'sources', 'analyses', 'charts')
OUT_MD = os.path.join(ROOT, 'sources', 'analyses', 'towns-like-us.md')
REPORT = 'towns-like-us'

BILLS = os.path.join(ROOT, 'sources', 'data', 'dls-avg-tax-bill.csv')
VALUES = os.path.join(ROOT, 'sources', 'data', 'dls-assessed-values.csv')
GROWTH = os.path.join(ROOT, 'sources', 'data', 'dls-new-growth.csv')
OVERRIDES = os.path.join(ROOT, 'sources', 'data', 'dls-override-votes.csv')
DESE = os.path.join(ROOT, 'sources', 'state-dese', 'er3w-dyti.json')
SPANS = os.path.join(ROOT, 'sources', 'state-dese', 'i5up-aez6-grades-served.json')
DEST = os.path.join(ROOT, 'sources', 'data', 'dese-town-enrollment.csv')
SHAPES = os.path.join(ROOT, 'sources', 'state-census', 'tigerweb-cousub-massachusetts.json')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')

# The year every figure is taken at. The tax year and the school year are DIFFERENT
# quantities with different calendars and are never averaged: FY2026 is the last year DLS
# has set a rate for every town, SY2025 the last year DESE has published spending for.
FY = 2026
SY = 2025
BASE_FY = 2011        # fifteen years of tax bills; every town has one
BASE_SY = 2011        # the earliest school year with per-pupil for every district here

NEIGHBOURS = ['Ashby', 'Fitchburg', 'Lancaster', 'Leominster', 'Shirley', 'Townsend']
PEERS = ['Ayer', 'Groton', 'Harvard', 'Littleton', 'Westford']

# Each town's district, for the neighbours and peers. Three of the six neighbours are in a
# REGIONAL district and one is shared, which is the first thing this comparison teaches:
# "every bordering town's school district" is not six districts and is not one-to-one with
# towns. Ashby and Townsend are both North Middlesex; Ayer and Shirley are both Ayer Shirley.
DISTRICT_OF = {
    'Lunenburg': 'Lunenburg', 'Ashby': 'North Middlesex', 'Fitchburg': 'Fitchburg',
    'Lancaster': 'Nashoba', 'Leominster': 'Leominster',
    'Shirley': 'Ayer Shirley School District', 'Townsend': 'North Middlesex',
    'Ayer': 'Ayer Shirley School District', 'Groton': 'Groton-Dunstable',
    'Harvard': 'Harvard', 'Littleton': 'Littleton', 'Westford': 'Westford',
}

# A district name that is not a municipality: charters, the Commonwealth virtual schools,
# the regional vocational schools. None of them has one town's tax base behind it.
NOT_A_TOWN = ('Charter', 'Vocational', 'Virtual', 'Academy', 'Collaborative',
              'Agricultural', 'Technical', '(District)')

# WHAT THE TOWN'S OWN ASSESSOR FOUND, quoted from the minute rather than paraphrased.
#
# Rule 15a: a verifier checks the figures and cannot check that anybody's question was
# answered, so every report gets searched against what people actually said. Searching the
# record for `commercial tax base` found the Select Board's tax classification hearing of
# 25 November 2025, where the Principal Assessor had already priced the exact question this
# report's central correlation implies -- for this town, at this year's values.
#
# THESE ARE STATED FIGURES, NOT OURS (rule 13a): a hearing presentation is a sheet somebody
# assembled, however official the setting. They are carried here with the sentence each one
# comes from, and `check_classification()` re-reads the minute on every run and refuses to
# build if any of them has stopped being in it -- which is rule 13's cite-a-coordinate made
# mechanical for a text document.
#
# Two of them ARE checkable and both reconcile to the cent against the state's own file:
# the average single-family bill and the average single-family value. That is what makes
# the rest of her arithmetic worth repeating.
CLASSIFICATION = dict(
    minutes='meetings/text/select-board/2025-11-25-minutes-7534.txt',
    url='https://lunenburgbudgetproject.org/docs/minutes/text/select-board/2025-11-25-minutes-7534.txt',
    town_url='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_11252025-7534',
    date='2025-11-25', date_text='25 November 2025',
    rate=14.39, res_rate=13.70, cip_rate=21.58,
    shift=1.50, shift_text='1.50',
    saving=224.25, cip_cost=2336.75, home=350000,
    avg_bill=7443.89, avg_value=517296,
    quotes=[
        'The estimated Fiscal Year 2026 single tax rate was projected at $14.39 per thousand',
        'average assessed value of $517,296, would be $7,443.89',
        'At the maximum allowable CIP shift of 1.50, the residential tax rate would decrease '
        'to $13.70 per thousand while the commercial tax rate would rise to $21.58 per thousand',
        'a savings of only $224.25 for a $350,000 residential property',
        'a tax increase of approximately $2,336.75 for a comparable commercial property',
        'only 112 have adopted a split tax rate',
    ],
)


def check_classification():
    """Every quoted sentence is still verbatim in the minute it came from.

    A figure read out of a text document and typed into a constant is exactly the thing
    rule 2 forbids, and the only honest way to keep one is to assert the source still says
    it. This refuses to build otherwise, naming the sentence that moved."""
    path = os.path.join(ROOT, 'sources', CLASSIFICATION['minutes'])
    if not os.path.exists(path):
        raise SystemExit('%s is not on disk. Run scripts/sync_archive.py --pull.'
                         % CLASSIFICATION['minutes'])
    with open(path, encoding='utf-8', errors='replace') as fh:
        text = ' '.join(fh.read().split())
    missing = [q for q in CLASSIFICATION['quotes'] if ' '.join(q.split()) not in text]
    if missing:
        raise SystemExit('the Select Board minute of %s no longer contains:\n  %s'
                         % (CLASSIFICATION['date_text'], '\n  '.join(missing)))


def usd2(n):
    """A rate or a bill to the cent, because the minute prints it to the cent and rule 13
    says quote the source rather than a rounding of it."""
    return '$%s' % format(float(n), ',.2f')


# WHAT THE STRUCTURAL COHORT IS MATCHED ON: things a town does not decide. `log` marks the
# ones spanning orders of magnitude, where a ratio is the comparable difference.
IS_KEYS = [('size', True), ('lowinc', False), ('ell', False), ('swd', False),
           ('oodpct', False), ('value', True), ('income', True), ('cip', False)]
# AND THE BEHAVIOURAL COHORT: what it charges, what it spends, how it votes, and the trend
# in each -- TJ, 26 September 2026: *"who tends like us, looks like us, passes overrides
# like us, spends the same as us, same tax bill for residents"*.
DOES_KEYS = [('bill', True), ('pinc', False), ('pp', True), ('put', False), ('won', False),
             ('billcagr', False), ('ppcagr', False), ('enrchg', False), ('ngpct', False)]


# ---- reading -----------------------------------------------------------------------

def rows(path):
    with open(path, encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def town_name(tiger):
    """A TIGER county-subdivision name as DLS spells the municipality.

    Massachusetts prints four shapes and all four are in the file: `Lunenburg town`,
    `Leominster city`, `Agawam Town city` (a town that reorganised as a city and kept the
    word), and `Manchester-by-the-Sea town` against DLS's `Manchester By The Sea`. Fourteen
    towns fell out of the join before this handled them, which looked exactly like fourteen
    towns with no boundary."""
    n = tiger
    for suffix in (' Town city', ' town', ' city', ' Town'):
        if n.endswith(suffix):
            n = n[:-len(suffix)]
            break
    if n == 'Manchester-by-the-Sea':
        return 'Manchester By The Sea'
    return n


def dese_by_year():
    with open(DESE, encoding='utf-8') as fh:
        raw = json.load(fh)
    out = {}
    for r in raw:
        v = num(r.get('ind_value'))
        if v is None:
            continue
        out.setdefault(r['sy'], {}).setdefault(r['dist_name'], {})[
            (r['ind_cat'], r['ind_subcat'])] = v
    return out


def k12_districts():
    """Districts operating a school that reaches grade 12 -- read off DESE's own
    `grades_served`, never inferred from which tests a district reports."""
    with open(SPANS, encoding='utf-8') as fh:
        raw = json.load(fh)
    span = {}
    for r in raw:
        if r.get('sy') != str(SY):
            continue
        g = r.get('grades_served')
        if not g or '-' not in g:
            continue
        lo_s, hi_s = g.split('-')[0], g.split('-')[-1]
        lo = 0 if lo_s in ('PK', 'K') else (int(lo_s) if lo_s.isdigit() else None)
        hi = 0 if hi_s in ('PK', 'K') else (int(hi_s) if hi_s.isdigit() else None)
        if lo is None or hi is None:
            continue
        cur = span.setdefault(r['dist_name'], [99, -1])
        cur[0] = min(cur[0], lo)
        cur[1] = max(cur[1], hi)
    return {n for n, (lo, hi) in span.items() if lo == 0 and hi >= 12}


def cagr(a, b, years):
    if not a or not b or a <= 0 or years <= 0:
        return None
    return ((b / a) ** (1.0 / years) - 1) * 100


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = st.mean(xs), st.mean(ys)
    num_ = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
    return num_ / den if den else None


# ---- the frame ---------------------------------------------------------------------

def build_frame():
    """Every single-town K-12 district with all fourteen measures, plus the raw lookups."""
    bill, value, income, pinc, rank, prate = {}, {}, {}, {}, {}, {}
    for r in rows(BILLS):
        b = num(r['avg_sf_bill'])
        if b is None:
            continue
        k = (r['municipality'], int(r['fy']))
        bill[k] = b
        value[k] = num(r['avg_sf_value'])
        income[k] = num(r['income_per_capita'])
        pinc[k] = num(r['bill_pct_of_income'])
        prate[k] = num(r['bill_pct_of_value'])
        rank[k] = int(r['rank']) if r['rank'] else None
    cip = {(r['municipality'], int(r['fy'])): num(r['cip_pct'])
           for r in rows(VALUES) if num(r['cip_pct']) is not None}
    ng = {}
    for r in rows(GROWTH):
        v = num(r['levy_pct_of_prior_limit'])
        if v is not None:
            ng.setdefault(r['municipality'], []).append((int(r['fy']), v))
    ov = {}
    for r in rows(OVERRIDES):
        if r['vote_type'] == 'Override':
            ov.setdefault(r['municipality'], []).append(r)

    dese = dese_by_year()
    towns = {m for (m, _) in bill}
    single = sorted(k12_districts() & towns)
    if 'Lunenburg' not in single:
        raise SystemExit('Lunenburg is not in the single-town K-12 set -- the join broke')
    if len(single) < 100:
        raise SystemExit('only %d single-town K-12 districts joined; expected ~170. A join '
                         'that matches almost nothing looks exactly like data that is '
                         'absent.' % len(single))

    frame = {}
    for t in single:
        now, then = dese.get(str(SY), {}).get(t, {}), dese.get(str(BASE_SY), {}).get(t, {})
        hc = now.get(('Student Demographics', 'Student Headcount'))
        hc0 = then.get(('Student Demographics', 'Student Headcount'))
        fte = now.get(('Student Enrollment', 'Total FTE Pupils'))
        fte0 = then.get(('Student Enrollment', 'Total FTE Pupils'))
        ood = now.get(('Student Enrollment', 'Out-of-District FTE Pupils'))
        pp = now.get(('Expenditures Per Pupil', 'Total Expenditures'))
        pp0 = then.get(('Expenditures Per Pupil', 'Total Expenditures'))
        growth = [v for (y, v) in ng.get(t, []) if FY - 9 <= y <= FY]
        quests = ov.get(t, [])
        if not all([hc, hc0, fte, fte0, pp, pp0, growth]) or (t, FY) not in bill or (t, FY) not in cip:
            continue
        rec = dict(
            town=t,
            size=hc, lowinc=now.get(('Student Demographics', 'Low-Income % Headcount')),
            ell=now.get(('Student Demographics', 'English learner % Headcount')),
            swd=now.get(('Student Demographics', 'Students with disabilities % Headcount')),
            oodpct=100.0 * (ood or 0) / fte,
            value=value[(t, FY)], income=income[(t, FY)], cip=cip[(t, FY)],
            bill=bill[(t, FY)], pinc=pinc[(t, FY)], rank=rank[(t, FY)],
            prate=prate[(t, FY)], pp=pp, fte=fte,
            # TOTAL spending, so the per-pupil ratio can be split from its denominator.
            # Per-pupil times FTE is DESE's own arithmetic run backwards; it is a derived
            # figure and is labelled as one wherever it appears.
            total=pp * fte, total0=pp0 * fte0,
            ngpct=st.mean(growth), put=len(quests),
            won=len([q for q in quests if q['result'] == 'WIN']),
            won_amt=sum(num(q['amount']) or 0 for q in quests if q['result'] == 'WIN'),
            billcagr=cagr(bill.get((t, BASE_FY)), bill[(t, FY)], FY - BASE_FY),
            ppcagr=cagr(pp0, pp, SY - BASE_SY),
            totalcagr=cagr(pp0 * fte0, pp * fte, SY - BASE_SY),
            enrchg=100.0 * (fte - fte0) / fte0)
        if all(v is not None for v in rec.values()):
            frame[t] = rec
    return frame, dict(bill=bill, value=value, income=income, pinc=pinc, rank=rank,
                       prate=prate, cip=cip, ng=ng, ov=ov, dese=dese)


def cohort(frame, keys, n=10):
    """The towns nearest Lunenburg in a standardised space, closest first.

    Distance is the ROOT MEAN squared z-difference rather than the sum, so a cohort matched
    on eight measures and one matched on nine are on the same scale and can be printed in
    one table. A z-score is the right unit here because the measures are in dollars,
    percentages and counts, and no weighting between them is defensible -- which is itself
    worth saying out loud: the cohort is a statement about these nine measures given equal
    weight, not about similarity in general."""
    names = [k for k, _ in keys]
    X = {t: {k: (math.log(frame[t][k]) if lg else frame[t][k]) for k, lg in keys}
         for t in frame}
    sd = {k: st.pstdev([X[t][k] for t in X]) for k in names}
    if min(sd.values()) <= 0:
        raise SystemExit('a matching measure has no spread across %d towns' % len(X))
    me = X['Lunenburg']
    out = sorted(
        (math.sqrt(sum(((X[t][k] - me[k]) / sd[k]) ** 2 for k in names) / len(names)), t)
        for t in X if t != 'Lunenburg')
    return [dict(town=t, distance=round(d, 3)) for d, t in out[:n]], [t for _, t in out]


def destinations():
    """Where Lunenburg children were schooled in the report's fiscal year, and what kind of
    thing each place is.

    FOUR KINDS, and the split is the finding rather than a tidying step. A tax bill can only
    be set beside a destination that ONE town's taxpayers fund."""
    rs = [r for r in rows(DEST) if r['town'] == 'Lunenburg' and r['fy'] == str(FY)]
    if not rs:
        raise SystemExit('no FY%d destination rows for Lunenburg in %s'
                         % (FY, os.path.relpath(DEST, ROOT)))
    tot = {}
    for r in rs:
        tot[r['district']] = tot.get(r['district'], 0) + int(r['students'])
    out = []
    for d, n in sorted(tot.items(), key=lambda kv: -kv[1]):
        if d == 'Lunenburg':
            kind = 'own'
        elif 'Montachusett Regional Vocational' in d:
            # Lunenburg is one of its eighteen member towns and pays an assessment, so a
            # child here is not leaving the tax base. sources/analyses/monty-tech.md.
            kind = 'assessed'
        elif any(x in d for x in NOT_A_TOWN):
            kind = 'no-town'
        elif d in DISTRICT_OF.values() or d not in DISTRICT_OF:
            kind = 'one-town' if d in DISTRICT_OF or d in ('Gardner',) else 'regional'
        else:
            kind = 'regional'
        out.append(dict(district=d, students=n, kind=kind))
    # A single-town district IS a municipality; that is the test, not a list.
    munis = {r['municipality'] for r in rows(BILLS)}
    for o in out:
        if o['kind'] == 'regional' and o['district'] in munis:
            o['kind'] = 'one-town'
        if o['kind'] == 'one-town' and o['district'] not in munis:
            o['kind'] = 'regional'
    return out


def map_shapes(shown):
    """Simplified boundaries and real centroids for the towns this report names.

    The archived fetch is the publisher's response and is frozen; what the page gets is a
    DERIVED simplification -- every nth vertex, coordinates to four decimals -- because a
    4 MB payload for a locator map is a page nobody on a phone waits for. Four decimals is
    about 11 metres, which is finer than any line this map draws."""
    with open(SHAPES, encoding='utf-8') as fh:
        fc = json.load(fh)
    want = set(shown)
    feats = {}
    for f in fc['features']:
        name = town_name(f['properties']['NAME'])
        if name not in want:
            continue
        rings = (f['geometry']['coordinates'] if f['geometry']['type'] == 'Polygon'
                 else [r for poly in f['geometry']['coordinates'] for r in poly])
        simple = []
        for ring in rings:
            step = max(1, len(ring) // 60)
            pts = [[round(x, 4), round(y, 4)] for x, y in ring[::step]]
            if len(pts) > 3:
                pts.append(pts[0])
                simple.append(pts)
        feats[name] = dict(
            rings=simple,
            lat=float(f['properties']['CENTLAT']),
            lon=float(f['properties']['CENTLON']))
    missing = sorted(want - set(feats))
    if missing:
        raise SystemExit('no boundary for %s -- the TIGER name join failed, which is not '
                         'the same as a town having no boundary' % ', '.join(missing))
    # The whole state, faintly, so a reader can see WHERE these towns are. Coarser still:
    # an outline needs less detail than a filled shape a name sits on.
    outline = []
    for f in fc['features']:
        rings = (f['geometry']['coordinates'] if f['geometry']['type'] == 'Polygon'
                 else [r for poly in f['geometry']['coordinates'] for r in poly])
        for ring in rings:
            step = max(1, len(ring) // 24)
            pts = [[round(x, 3), round(y, 3)] for x, y in ring[::step]]
            if len(pts) > 3:
                outline.append(pts)
    return feats, outline


def sources_block():
    """Every document a figure here rests on, with its address, its bytes and its sha256."""
    # THE MANIFEST KEYS ON `key`, not `path`. It is an archive key relative to sources/.
    man = {r['key']: r for r in rows(MANIFEST)} if os.path.exists(MANIFEST) else {}
    idx = {}
    for d in ('state-dls', 'state-dese', 'state-census'):
        p = os.path.join(ROOT, 'sources', d, 'index.csv')
        if os.path.exists(p):
            for r in rows(p):
                idx[r['local']] = r
    # NAME THE EXPORT THE FIGURES WERE ACTUALLY READ FROM. Each extract records its own
    # `source_file`, so this asks the CSV rather than guessing from the filenames on disk --
    # and guessing got it wrong: sorting the candidates put the legacy undated export last,
    # because '-' sorts before '.', so every DLS source here cited a file today's figures did
    # not come from. Rule 13, in the provenance block of all places.
    read_from = {}
    for csv_name, folder in (('dls-avg-tax-bill.csv', 'state-dls'),
                             ('dls-assessed-values.csv', 'state-dls'),
                             ('dls-new-growth.csv', 'state-dls'),
                             ('dls-override-votes.csv', 'state-dls')):
        path = os.path.join(ROOT, 'sources', 'data', csv_name)
        if os.path.exists(path):
            first = next(iter(rows(path)), {})
            if first.get('source_file'):
                read_from[csv_name] = '%s/%s' % (folder, first['source_file'])

    wanted = [
        ('dls-avg-tax-bill.csv', 'Massachusetts DOR, Division of Local Services',
         'Average single-family tax bill, value, parcels, income per capita and rank, all '
         '351 municipalities, FY1988 onward.'),
        ('dls-assessed-values.csv', 'Massachusetts DOR, Division of Local Services',
         'Assessed value by class, so the commercial-industrial-personal share is the '
         'state’s certified figure rather than ours.'),
        ('dls-new-growth.csv', 'Massachusetts DOR, Division of Local Services',
         'New growth certified onto the levy limit each year, and the prior year’s limit '
         'it is measured against.'),
        ('dls-override-votes.csv', 'Massachusetts DOR, Division of Local Services',
         'Every Proposition 2½ override and underride put to a town, with the date, the '
         'tallies and the result.'),
    ]
    out = []
    for csv_name, publisher, note in wanted:
        path = read_from.get(csv_name)
        if not path:
            raise SystemExit('%s does not record the export it was read from -- rerun its '
                             'fetcher' % csv_name)
        if path not in man:
            raise SystemExit('%s says it was read from %s, which is not in the manifest'
                             % (csv_name, path))
        row = man[path]
        cat = idx.get(path, {})
        out.append(dict(path='sources/' + path, publisher=publisher, note=note,
                        table=cat.get('title'), url=cat.get('url'),
                        docs_url='/docs/' + path, sha256=row.get('sha256'),
                        bytes=int(row.get('bytes') or 0)))
    for path, publisher, table, note, url in (
        ('state-dese/er3w-dyti.json', 'Massachusetts DESE',
         'District indicators, SY2009–SY%d' % SY,
         'Per-pupil expenditure by category, enrolment in and out of district, and student '
         'demographics, for every district in the state.',
         'https://educationtocareer.data.mass.gov/resource/er3w-dyti.json'),
        ('state-dese/i5up-aez6-grades-served.json', 'Massachusetts DESE',
         'Grades served, by school, SY2019–SY%d' % SY,
         'Which grades each school actually serves — the published fact that decides '
         'whether a district runs a high school.',
         'https://educationtocareer.data.mass.gov/resource/i5up-aez6.json'),
        (CLASSIFICATION['minutes'], 'Town of Lunenburg, Select Board',
         'Tax classification hearing, %s' % CLASSIFICATION['date_text'],
         'The Principal Assessor\u2019s split-rate analysis: the single rate, the average '
         'bill, and what the largest shift the statute allows onto commercial property '
         'would be worth. Quoted rather than paraphrased, and re-read on every build.',
         CLASSIFICATION['town_url']),
        ('state-census/tigerweb-cousub-massachusetts.json', 'US Census Bureau, TIGERweb',
         'County subdivisions, Massachusetts',
         'Town boundaries and centroids: which towns share a border with Lunenburg, and '
         'where each one is on the map.',
         'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/'
         'Places_CouSub_ConCity_SubMCD/MapServer/1/query'),
    ):
        row = man.get(path, {})
        out.append(dict(path='sources/' + path, publisher=publisher, note=note, table=table,
                        url=url, docs_url='/docs/' + path, sha256=row.get('sha256'),
                        bytes=int(row.get('bytes') or 0)))
    return out


# ---- what it means -----------------------------------------------------------------

def build_conclusions(frame, corr, twins_is, twins_does, overlap10, overlap25, dest, sets):
    # THE FIRST YEAR THE OVERRIDE FILE COVERS, read off the file rather than typed. It is a
    # boundary of the data and appears in two conclusions; if DLS ever publishes earlier
    # votes both sentences move with it.
    first_override_fy = 'FY%d' % sets['first_override_fy']
    L = frame['Lunenburg']
    towns = sorted(frame)
    n = len(frame)
    tw = [c['town'] for c in twins_is]
    more = [t for t in tw if frame[t]['pp'] > L['pp']]
    cheaper = [t for t in tw if frame[t]['bill'] < L['bill']]
    pp_order = sorted(towns, key=lambda t: -frame[t]['pp'])
    pp_rank = pp_order.index('Lunenburg') + 1
    group = tw + ['Lunenburg']
    g_order = sorted(group, key=lambda t: -frame[t]['totalcagr'])
    g_rank = g_order.index('Lunenburg') + 1
    lost_more = [t for t in tw if frame[t]['enrchg'] < L['enrchg']]

    by_kind = {}
    for d in dest:
        by_kind[d['kind']] = by_kind.get(d['kind'], 0) + d['students']
    left = sum(v for k, v in by_kind.items() if k != 'own')

    nb = {t: frame.get(t) for t in sets['neighbours']}
    ov_put = {t: len(sets['ov'].get(t, [])) for t in sets['neighbours'] + ['Lunenburg']}
    ov_won = {t: len([q for q in sets['ov'].get(t, []) if q['result'] == 'WIN'])
              for t in ov_put}
    loudest = max(sets['neighbours'], key=lambda t: ov_put[t])
    silent = [t for t in sets['neighbours'] if ov_put[t] == 0]

    rows_out = [
        conclusion(
            id='the-bill-is-the-house',
            claim='The tax bill tracks home value (r %s) and income (r %s). New growth: r %s.'
                  % (corr['value_bill_t'], corr['income_bill_t'], corr['ng_bill_t']),
            detail=(
                'Across the %d Massachusetts towns that run their own K–12 district, the '
                'average single-family tax bill correlates with the average single-family '
                'value at r %s and with DOR income per capita at r %s. Those two sit close '
                'enough that nothing here separates them, and they are largely measuring the '
                'same thing: towns with expensive houses have wealthy households in them. '
                'Against the new growth a town certifies onto its levy limit — the measure '
                'of what it built — the correlation is r %s, which is no relationship at '
                'all. The commercial share of the base does a little better at r %s, and '
                'still nothing like the house.'
                % (n, corr['value_bill_t'], corr['income_bill_t'], corr['ng_bill_t'],
                   corr['cip_bill_t'])),
            figures={
                'value_bill': figure(corr['value_bill'], corr['value_bill_t'],
                                     'correlation between average home value and average tax '
                                     'bill, %d towns' % n),
                'ng_bill': figure(corr['ng_bill'], corr['ng_bill_t']),
                'income_bill': figure(corr['income_bill'], corr['income_bill_t']),
                'cip_bill': figure(corr['cip_bill'], corr['cip_bill_t']),
                'n': figure(n, str(n)),
            },
            figure='value_bill',
            kind='measured',
            bearing='sizes',
            allow=('12',),
            basis=('dls-avg-tax-bill.csv and dls-new-growth.csv at FY%d, over the %d '
                   'single-town K–12 districts. Pearson correlation on the levels.'
                   % (FY, n)),
            not_shown=(
                'Which way any of it runs. A town with expensive houses can afford a higher '
                'bill and also chooses one; nothing here separates the two. And a '
                'correlation across towns in one year is not what would happen to one '
                'town’s bill if its commercial base grew — that is a different '
                'question, asked on /growth.'),
            so_what=('What a household pays follows what its house is worth and what it '
                     'earns, not what the town built.'),
            see=[('/growth', 'What commercial growth would have to look like'),
                 ('/analysis/commercial-base', 'The commercial base, as certified')]),

        conclusion(
            id='the-town-already-priced-the-shift',
            claim='Shifting the most the law allows onto commercial saves a %s home %s a year.'
                  % (usd(CLASSIFICATION['home']), usd2(CLASSIFICATION['saving'])),
            detail=(
                'The correlation above says a commercial base does not show up as a smaller '
                'residential bill. Lunenburg’s own Principal Assessor priced exactly '
                'that, for this town, at the Select Board’s tax classification hearing '
                'on %s. Lunenburg levies a SINGLE rate, %s per thousand in FY%d. At the '
                'maximum allowable CIP shift of %s the residential rate would fall to %s and '
                'the commercial rate rise to %s — worth %s to a %s home, and about %s '
                'more on a comparable commercial property. Her figures reconcile to the '
                'state’s: the minute states an average single-family bill of %s on an '
                'average value of %s, and the Division of Local Services publishes %s on %s.'
                % (CLASSIFICATION['date_text'], usd2(CLASSIFICATION['rate']), FY,
                   CLASSIFICATION['shift_text'], usd2(CLASSIFICATION['res_rate']),
                   usd2(CLASSIFICATION['cip_rate']), usd2(CLASSIFICATION['saving']),
                   usd(CLASSIFICATION['home']), usd2(CLASSIFICATION['cip_cost']),
                   usd2(CLASSIFICATION['avg_bill']), usd(CLASSIFICATION['avg_value']),
                   usd(L['bill']), usd(L['value']))),
            figures={
                'saving': figure(CLASSIFICATION['saving'], usd2(CLASSIFICATION['saving']),
                                 'a year off a %s home, at the largest shift onto commercial '
                                 'the statute permits' % usd(CLASSIFICATION['home'])),
                'home': figure(CLASSIFICATION['home'], usd(CLASSIFICATION['home'])),
                'cip_cost': figure(CLASSIFICATION['cip_cost'], usd2(CLASSIFICATION['cip_cost'])),
                'rate': figure(CLASSIFICATION['rate'], usd2(CLASSIFICATION['rate'])),
                'res_rate': figure(CLASSIFICATION['res_rate'], usd2(CLASSIFICATION['res_rate'])),
                'cip_rate': figure(CLASSIFICATION['cip_rate'], usd2(CLASSIFICATION['cip_rate'])),
                'shift': figure(CLASSIFICATION['shift'], CLASSIFICATION['shift_text']),
                'avg_bill': figure(CLASSIFICATION['avg_bill'], usd2(CLASSIFICATION['avg_bill'])),
                'avg_value': figure(CLASSIFICATION['avg_value'], usd(CLASSIFICATION['avg_value'])),
                'dls_bill': figure(L['bill'], usd(L['bill'])),
                'dls_value': figure(L['value'], usd(L['value'])),
                'fy': figure(FY, 'FY%d' % FY),
                'when': figure(CLASSIFICATION['date'], CLASSIFICATION['date_text']),
            },
            figure='saving',
            kind='measured',
            bearing='lever',
            basis=('Select Board minutes, %s, the tax classification hearing: the Principal '
                   'Assessor’s split-rate analysis as the minute records it. The average '
                   'bill and average value in the same minute are compared against '
                   'dls-avg-tax-bill.csv at FY%d.' % (CLASSIFICATION['date_text'], FY)),
            not_shown=(
                'We did not recompute her split-rate arithmetic; the rates and the two '
                'property figures are as the minute states them, and rule 13a applies — '
                'a figure a person assembled is stated, however official the document. What '
                'raises confidence is the part that CAN be checked: her average bill and '
                'average value match the state’s file for the same year exactly. The '
                'minute also reports that of the 351 communities only 112 have adopted a '
                'split rate and only 7 of those have a CIP share at or below a tenth; '
                'nothing held here lists which towns split, so that count is hers and is not '
                'verified.'),
            so_what=('The town\u2019s assessor recommended against it. A shift moves the bill '
                     'between classes, not the levy.'),
            see=[('/growth', 'What commercial growth would have to look like')]),
        conclusion(
            id='the-look-alikes-spend-more',
            claim='Of the towns most like Lunenburg, %d of %d spend more per pupil and %d charge less.'
                  % (len(more), len(tw), len(cheaper)),
            detail=(
                'The %d towns are chosen by distance in a standardised space on eight things '
                'a town does not decide: how many children, how many are low income, how many '
                'are English learners, how many have disabilities, how many are placed out of '
                'district, the average house, income per capita and the commercial share of '
                'the base. Spending and bills are deliberately NOT among them, so they can be '
                'compared afterwards rather than assumed. Lunenburg’s %s per pupil in '
                'SY%d is %s of %d; the %d towns run from %s to %s.'
                % (len(tw), usd(L['pp']), SY, ordinal(pp_rank), n, len(tw),
                   usd(min(frame[t]['pp'] for t in tw)),
                   usd(max(frame[t]['pp'] for t in tw)))),
            figures={
                'more': figure(len(more), '%d of %d' % (len(more), len(tw)),
                               'look-alike towns spending more per pupil than Lunenburg'),
                'cheaper': figure(len(cheaper), str(len(cheaper))),
                'tw': figure(len(tw), str(len(tw))),
                'pp': figure(L['pp'], usd(L['pp'])),
                'pp_rank': figure(pp_rank, ordinal(pp_rank)),
                'n': figure(n, str(n)),
                'sy': figure(SY, 'SY%d' % SY),
                'pp_lo': figure(min(frame[t]['pp'] for t in tw),
                                usd(min(frame[t]['pp'] for t in tw))),
                'pp_hi': figure(max(frame[t]['pp'] for t in tw),
                                usd(max(frame[t]['pp'] for t in tw))),
            },
            figure='more',
            kind='measured',
            bearing='sizes',
            basis=('DESE per-pupil total expenditures at SY%d and DLS bills at FY%d, over '
                   'the %d-town frame; cohort by root-mean z-distance on the eight '
                   'structural measures.' % (SY, FY, n)),
            not_shown=(
                'That any of them educates a child better, or worse. Per-pupil spending is '
                'all funds divided by full-time-equivalent pupils and says nothing about '
                'outcomes. Nor is it the town’s bill: it includes state aid, grants, '
                'circuit breaker and every other fund, so a town spending more per pupil is '
                'not necessarily taxing more for it.'),
            so_what='Lunenburg is %s of %d comparable districts on spending per pupil.'
                    % (ordinal(pp_rank), n),
            see=[('/analysis/per-pupil-spending', 'Per-pupil spending, in full')]),

        conclusion(
            id='the-denominator-does-most-of-it',
            claim='On TOTAL school spending growth Lunenburg is %s of %d: %s a year.'
                  % (ordinal(g_rank), len(group), pct(L['totalcagr'], 1)),
            detail=(
                'Per-pupil spending is a ratio, and the gap above is mostly its denominator. '
                'Total spending — per-pupil times full-time-equivalent pupils, which is '
                'DESE’s own arithmetic run backwards — grew %s a year at Lunenburg '
                'from SY%d to SY%d, against %s to %s across the same %d towns, putting it %s '
                'of %d. What separates them is pupils: Lunenburg’s full-time-equivalent '
                'enrolment fell %s, and %d of the %d look-alikes fell further, one of them by '
                '%s. Across the whole frame, losing enrolment and raising per-pupil spending '
                'go together at r %s.'
                % (pct(L['totalcagr'], 1), BASE_SY, SY,
                   pct(min(frame[t]['totalcagr'] for t in tw), 1),
                   pct(max(frame[t]['totalcagr'] for t in tw), 1), len(tw),
                   ordinal(g_rank), len(group), pct(abs(L['enrchg']), 1),
                   len(lost_more), len(tw),
                   pct(abs(min(frame[t]['enrchg'] for t in tw)), 1),
                   corr['enr_pp_t'])),
            figures={
                'g_rank': figure(g_rank, ordinal(g_rank)),
                'group': figure(len(group), str(len(group))),
                'total_cagr': figure(L['totalcagr'], pct(L['totalcagr'], 1),
                                     'a year growth in Lunenburg’s total school '
                                     'spending, SY%d–SY%d' % (BASE_SY, SY)),
                'lo': figure(min(frame[t]['totalcagr'] for t in tw),
                             pct(min(frame[t]['totalcagr'] for t in tw), 1)),
                'hi': figure(max(frame[t]['totalcagr'] for t in tw),
                             pct(max(frame[t]['totalcagr'] for t in tw), 1)),
                'tw': figure(len(tw), str(len(tw))),
                'enr': figure(abs(L['enrchg']), pct(abs(L['enrchg']), 1)),
                'lost_more': figure(len(lost_more), str(len(lost_more))),
                'worst': figure(abs(min(frame[t]['enrchg'] for t in tw)),
                                pct(abs(min(frame[t]['enrchg'] for t in tw)), 1)),
                'enr_pp': figure(corr['enr_pp'], corr['enr_pp_t']),
                'base_sy': figure(BASE_SY, 'SY%d' % BASE_SY),
                'sy': figure(SY, 'SY%d' % SY),
            },
            figure='total_cagr',
            kind='measured',
            bearing='sizes',
            basis=('DESE per-pupil total expenditures and total FTE pupils, SY%d and SY%d, '
                   'multiplied per district; compound annual rate over %d years.'
                   % (BASE_SY, SY, SY - BASE_SY)),
            not_shown=(
                'Why Lunenburg held its enrolment while these towns did not. Births, housing '
                'turnover, school choice and the boundary of who counts all move that number '
                'and none of them is separated here. Total spending is also all funds, so '
                'part of the growth is state aid and grants rather than the town’s levy '
                '— the split is not published per line.'),
            so_what=('It kept its pupils. The look-alikes lost more, which lifts per-pupil '
                     'without spending more.'),
            see=[('/analysis/enrollment', 'Who is in the schools')]),

        conclusion(
            id='look-alikes-are-not-act-alikes',
            claim='%d of %d \u2014 no town is closest to Lunenburg on both what it is and what it does.'
                  % (len(overlap10), len(twins_is)),
            detail=(
                'Two cohorts were built from the same %d towns. One matches on structure — '
                'children, need, housing, income, commercial base. The other matches on '
                'behaviour — the tax bill, the bill as a share of income, per-pupil '
                'spending, how many override questions have been put and won, and the trend '
                'in the bill, in spending and in enrolment. The closest %d lists share %s. '
                'Widen both to %d and %d towns appear on both. The nearest on structure is %s '
                'at a distance of %s; the nearest on behaviour is %s at %s.'
                % (len(frame), len(twins_is), 'no town' if not overlap10 else
                   '%d town(s)' % len(overlap10), 25, len(overlap25),
                   twins_is[0]['town'], '%.3f' % twins_is[0]['distance'],
                   twins_does[0]['town'], '%.3f' % twins_does[0]['distance'])),
            figures={
                'overlap': figure(len(overlap10), '%d of %d' % (len(overlap10), len(twins_is)),
                                  'towns in both closest lists — structure and behaviour'),
                'ten': figure(len(twins_is), str(len(twins_is))),
                'wide': figure(len(overlap25), str(len(overlap25))),
                'twentyfive': figure(25, '25'),
                'n': figure(len(frame), str(len(frame))),
                'is_near': figure(twins_is[0]['distance'], '%.3f' % twins_is[0]['distance']),
                'does_near': figure(twins_does[0]['distance'],
                                    '%.3f' % twins_does[0]['distance']),
            },
            figure='overlap',
            kind='measured',
            bearing='sizes',
            basis=('Both cohorts computed over the same %d-town frame; membership of the two '
                   'closest-%d lists intersected, then the closest-25 lists.'
                   % (len(frame), len(twins_is))),
            not_shown=(
                'That either cohort is the right one. A distance is a statement about the '
                'measures given equal weight and nothing more; a different weighting gives '
                'different towns. What the empty intersection does show is that the answer '
                'to "who is like us" depends entirely on which question is being asked.'),
            so_what=('%d towns make the closest 25 on both. Resembling Lunenburg and acting '
                     'like it are different.' % len(overlap25))),

        conclusion(
            id='an-override-stays-in-the-bill',
            claim='Towns that have won more overrides charge higher bills: r %s across %d towns.'
                  % (corr['won_bill_t'], len(frame)),
            detail=(
                'Every override the state records for these towns since %s, counted by '
                'wins, correlates with the FY%d average single-family bill at r %s. '
                'Lunenburg has put %d questions and won %d, raising %s of permanent levy '
                'capacity. An override is not a one-year charge: it raises the levy limit for '
                'ever, and the limit compounds at 2.5%% a year from wherever it is left. That '
                'is the mechanism the statute describes, and it is why a vote taken decades '
                'ago is still inside today’s bill.'
                % (first_override_fy, FY, corr['won_bill_t'], L['put'], L['won'],
                   usd(L['won_amt']))),
            figures={
                'won_bill': figure(corr['won_bill'], corr['won_bill_t'],
                                   'correlation between overrides won and the average tax '
                                   'bill, %d towns' % len(frame)),
                'put': figure(L['put'], str(L['put'])),
                'won': figure(L['won'], str(L['won'])),
                'won_amt': figure(L['won_amt'], usd(L['won_amt'])),
                'n': figure(len(frame), str(len(frame))),
                'fy': figure(FY, 'FY%d' % FY),
                'since': figure(int(first_override_fy[2:]), first_override_fy),
            },
            figure='won_bill',
            kind='measured',
            bearing='sizes',
            allow=('2.5',),
            basis=('dls-override-votes.csv, wins per town, against dls-avg-tax-bill.csv at '
                   'FY%d, over the %d-town frame.' % (FY, len(frame))),
            not_shown=(
                'Which causes which, and it matters here. A town with a higher bill may pass '
                'overrides because it can afford them, rather than having a higher bill '
                'because it passed them. The correlation is equally consistent with both, and '
                'with a third thing — wealth — driving each. Nor does a won amount '
                'mean the town levied it: an override raises the ceiling, and a town may sit '
                'below its own limit.'),
            so_what=('Lunenburg won %s of permanent capacity across %d wins. A won override '
                     'never expires.' % (usd(L['won_amt']), L['won'])),
            see=[('/analysis/fy27-and-the-override', 'The FY27 override')]),

        conclusion(
            id='where-the-children-actually-go',
            claim='Of %d Lunenburg children schooled elsewhere, %d go where one town’s taxes pay.'
                  % (left, by_kind.get('one-town', 0)),
            detail=(
                'In FY%d, %s Lunenburg children were enrolled somewhere other than '
                'Lunenburg’s own schools, out of %s in total. %d of them are at '
                'Montachusett Regional Vocational Technical, which Lunenburg is a member of '
                'and pays an assessment to — so that is not a departure from the tax '
                'base. %d are at charter or Commonwealth virtual schools, which no single '
                'town funds. %d are in regional districts split across member towns with '
                'different bills. That leaves %d at districts one town’s taxpayers pay '
                'for, where a tax bill can honestly be set beside a per-pupil figure.'
                % (FY, '{:,}'.format(left), '{:,}'.format(sum(by_kind.values())),
                   by_kind.get('assessed', 0), by_kind.get('no-town', 0),
                   by_kind.get('regional', 0), by_kind.get('one-town', 0))),
            figures={
                'one_town': figure(by_kind.get('one-town', 0),
                                   str(by_kind.get('one-town', 0)),
                                   'of the %d children schooled outside Lunenburg’s own '
                                   'schools attend one that a single town’s taxpayers fund'
                                   % left),
                'left': figure(left, '{:,}'.format(left)),
                'total': figure(sum(by_kind.values()), '{:,}'.format(sum(by_kind.values()))),
                'assessed': figure(by_kind.get('assessed', 0), str(by_kind.get('assessed', 0))),
                'no_town': figure(by_kind.get('no-town', 0), str(by_kind.get('no-town', 0))),
                'regional': figure(by_kind.get('regional', 0), str(by_kind.get('regional', 0))),
                'fy': figure(FY, 'FY%d' % FY),
            },
            figure='one_town',
            kind='measured',
            bearing='sizes',
            basis=('dese-town-enrollment.csv, Lunenburg rows at FY%d, grouped by what kind '
                   'of district each destination is.' % FY),
            not_shown=(
                'What any of it costs. A count of children is not a tuition, a charter '
                'assessment or an assessment share — rule 11 — and this says '
                'nothing about which fund pays. It also cannot say why a family chose a '
                'destination; the file records where a child is enrolled and nothing else.'),
            so_what=('%d are at Monty Tech, which Lunenburg helps fund; %d at charters or '
                     'virtual schools.' % (by_kind.get('assessed', 0),
                                           by_kind.get('no-town', 0))),
            see=[('/analysis/monty-tech', 'The Monty Tech assessment'),
                 ('/analysis/per-pupil-spending', 'What the destinations spend')]),

        conclusion(
            id='the-neighbours-vote-nothing-alike',
            claim='%s has put %d override questions and won %d. Lunenburg put %d, won %d.'
                  % (loudest, ov_put[loudest], ov_won[loudest], ov_put['Lunenburg'],
                     ov_won['Lunenburg']),
            detail=(
                'Across the six towns that share a border with Lunenburg, the number of '
                'Proposition 2½ questions put since %s runs from %d to %d. %s is the '
                'highest at %d questions and %d wins; %s. Lunenburg sits at %d and %d. The '
                'towns are adjacent, their school costs move with the same contracts and the '
                'same state aid formula, and their appetite for asking differs by a factor of '
                '%s.'
                % (first_override_fy, min(ov_put[t] for t in sets['neighbours']),
                   max(ov_put[t] for t in sets['neighbours']), loudest, ov_put[loudest],
                   ov_won[loudest],
                   ('%s has never put one' % silent[0]) if silent
                   else 'the lowest is %d' % min(ov_put[t] for t in sets['neighbours']),
                   ov_put['Lunenburg'], ov_won['Lunenburg'],
                   '%.0f' % (ov_put[loudest] / max(1, ov_put['Lunenburg'])))),
            figures={
                'loud_put': figure(ov_put[loudest], str(ov_put[loudest]),
                                   'override questions %s has put to its voters since %s, '
                                   'of which %d carried'
                                   % (loudest, first_override_fy, ov_won[loudest])),
                'loud_won': figure(ov_won[loudest], str(ov_won[loudest])),
                'lun_put': figure(ov_put['Lunenburg'], str(ov_put['Lunenburg'])),
                'lun_won': figure(ov_won['Lunenburg'], str(ov_won['Lunenburg'])),
                'lo': figure(min(ov_put[t] for t in sets['neighbours']),
                             str(min(ov_put[t] for t in sets['neighbours']))),
                'hi': figure(max(ov_put[t] for t in sets['neighbours']),
                             str(max(ov_put[t] for t in sets['neighbours']))),
                'factor': figure(ov_put[loudest] / max(1, ov_put['Lunenburg']),
                                 '%.0f' % (ov_put[loudest] / max(1, ov_put['Lunenburg']))),
                'since': figure(int(first_override_fy[2:]), first_override_fy),
            },
            figure='loud_put',
            kind='measured',
            bearing='sizes',
            allow=('2',),
            basis=('dls-override-votes.csv, override rows only, counted per town over every '
                   'year the file covers.'),
            not_shown=(
                'What a question was FOR. The file gives a department and a description, and '
                'a town that asks nine times for a fire truck is not a town that asks nine '
                'times for teachers. Nor does a low count mean a town never needed the money: '
                'it may have cut instead, used a debt exclusion — which is outside the '
                'levy limit and not in this file at all — or never brought a question '
                'that would have lost.'),
            so_what=('Adjacent towns under the same cost pressure differ %sx in how often '
                     'they ask.' % ('%.0f' % (ov_put[loudest] / max(1, ov_put['Lunenburg'])))),
            see=[('/analysis/fy27-and-the-override', 'The FY27 override')]),
    ]
    return emit(REPORT, rows_out)


def ordinal(n):
    if 10 <= n % 100 <= 20:
        return '%dth' % n
    return '%d%s' % (n, {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th'))


# ---- the payload and the document ---------------------------------------------------

def table_row(frame, raw, t, role, district):
    r = frame.get(t)
    bill = raw['bill'].get((t, FY))
    return dict(
        town=t, role=role, district=district,
        bill=bill, value=raw['value'].get((t, FY)), pinc=raw['pinc'].get((t, FY)),
        rank=raw['rank'].get((t, FY)), cip=raw['cip'].get((t, FY)),
        pp=(raw['dese'].get(str(SY), {}).get(district, {})
            .get(('Expenditures Per Pupil', 'Total Expenditures'))),
        ngpct=(st.mean([v for (y, v) in raw['ng'].get(t, []) if FY - 9 <= y <= FY])
               if raw['ng'].get(t) else None),
        put=len(raw['ov'].get(t, [])),
        won=len([q for q in raw['ov'].get(t, []) if q['result'] == 'WIN']),
        won_amt=sum(num(q['amount']) or 0 for q in raw['ov'].get(t, [])
                    if q['result'] == 'WIN'),
        billcagr=cagr(raw['bill'].get((t, BASE_FY)), bill, FY - BASE_FY) if bill else None,
        in_frame=t in frame,
        enrchg=r['enrchg'] if r else None,
        totalcagr=r['totalcagr'] if r else None)


def build():
    check_classification()
    frame, raw = build_frame()
    L = frame['Lunenburg']
    # THE MINUTE AND THE STATE FILE MUST AGREE. They are independent records of the same two
    # quantities, and the whole reason the assessor's other figures are worth repeating is
    # that these two reconcile. If they ever stop, the report may not lean on her arithmetic.
    for what, mine, theirs in (('average single-family bill', L['bill'], CLASSIFICATION['avg_bill']),
                               ('average single-family value', L['value'], CLASSIFICATION['avg_value'])):
        if abs(mine - theirs) > 1.0:
            raise SystemExit('the %s does not reconcile: DLS says %s, the Select Board '
                             'minute of %s says %s' % (what, usd2(mine),
                                                       CLASSIFICATION['date_text'], usd2(theirs)))
    towns = sorted(frame)

    def corr_of(a, b):
        v = pearson([frame[t][a] for t in towns], [frame[t][b] for t in towns])
        return v, ('%+.2f' % v)

    corr = {}
    for name, a, b in (('value_bill', 'value', 'bill'), ('income_bill', 'income', 'bill'),
                       ('ng_bill', 'ngpct', 'bill'), ('cip_bill', 'cip', 'bill'),
                       ('cip_ng', 'cip', 'ngpct'), ('won_bill', 'won', 'bill'),
                       ('enr_pp', 'enrchg', 'ppcagr'), ('pp_bill', 'pp', 'bill')):
        corr[name], corr[name + '_t'] = corr_of(a, b)

    twins_is, all_is = cohort(frame, IS_KEYS, 10)
    twins_does, all_does = cohort(frame, DOES_KEYS, 10)
    overlap10 = [t for t in all_is[:10] if t in all_does[:10]]
    overlap25 = [t for t in all_is[:25] if t in all_does[:25]]
    dest = destinations()

    sets = dict(neighbours=NEIGHBOURS, peers=PEERS, ov=raw['ov'],
                first_override_fy=min(int(q['fy']) for qs in raw['ov'].values() for q in qs))
    cons = build_conclusions(frame, corr, twins_is, twins_does, overlap10, overlap25,
                             dest, sets)

    local = ([table_row(frame, raw, 'Lunenburg', 'lunenburg', 'Lunenburg')]
             + [table_row(frame, raw, t, 'neighbour', DISTRICT_OF[t]) for t in NEIGHBOURS]
             + [table_row(frame, raw, t, 'peer', DISTRICT_OF[t]) for t in PEERS])
    twin_rows = ([table_row(frame, raw, 'Lunenburg', 'lunenburg', 'Lunenburg')]
                 + [dict(table_row(frame, raw, c['town'], 'structural', c['town']),
                         distance=c['distance']) for c in twins_is]
                 + [dict(table_row(frame, raw, c['town'], 'behavioural', c['town']),
                         distance=c['distance']) for c in twins_does])

    shown = sorted({r['town'] for r in local} | {r['town'] for r in twin_rows})
    shapes, outline = map_shapes(shown)
    pp_rank = sorted(towns, key=lambda t: -frame[t]['pp']).index('Lunenburg') + 1

    payload = dict(
        generated_by='scripts/build_town_comparison.py',
        about=('How Lunenburg compares with the towns it borders, the towns this project '
               'uses as peers, the towns the math says resemble it, and the places its '
               'children are actually schooled: tax bills, overrides, per-pupil spending '
               'and the commercial share of the base.'),
        grain=('Two calendars, never mixed. Tax figures are FY%d, the last year the '
               'Division of Local Services has a rate for every town: an AVERAGE '
               'single-family bill on an AVERAGE single-family assessment, which is not any '
               'one house. School figures are SY%d, the last year DESE has published '
               'spending: dollars per full-time-equivalent pupil, ALL FUNDS, so state aid '
               'and grants are inside it and it is not what the town raises. An override row '
               'is a question PUT to a ballot, not a dollar levied.' % (FY, SY)),
        fy=FY, sy=SY, base_fy=BASE_FY, base_sy=BASE_SY,
        frame_size=len(frame),
        stats=[
            dict(value=usd(L['bill']),
                 label='average single-family tax bill in Lunenburg, FY%d' % FY),
            dict(value='%s of 351' % ordinal(L['rank']),
                 label='where that bill ranks among Massachusetts towns'),
            dict(value=usd(L['pp']),
                 label='per pupil, all funds, SY%d — %s of %d comparable districts'
                       % (SY, ordinal(pp_rank), len(frame))),
            dict(value='%d of %d' % (L['won'], L['put']),
                 label='Proposition 2½ override questions Lunenburg has won of those put'),
            dict(value=pct(L['cip'], 1),
                 label='of the tax base is commercial, industrial or personal property'),
        ],
        conclusions=cons,
        correlations=[
            dict(key=k, r=corr[k], text=corr[k + '_t'], label=lab)
            for k, lab in (('value_bill', 'average home value → tax bill'),
                           ('income_bill', 'income per capita → tax bill'),
                           ('pp_bill', 'per-pupil spending → tax bill'),
                           ('won_bill', 'overrides won → tax bill'),
                           ('cip_bill', 'commercial share → tax bill'),
                           ('cip_ng', 'commercial share → new growth'),
                           ('ng_bill', 'new growth → tax bill'),
                           ('enr_pp', 'enrolment change → per-pupil growth'))],
        local=local,
        twins=twin_rows,
        overlap10=overlap10, overlap25=overlap25,
        destinations=dest,
        map=dict(towns=shapes, outline=outline,
                 roles={r['town']: r['role'] for r in local + twin_rows}),
        sources=sources_block(),
        not_established=[
            'Whose comparison set is right. The six neighbours are computed from boundary '
            'polygons and are a fact; the five peers are OUR choice, and nothing in the '
            'town’s own record names a cohort of comparable communities for tax '
            'purposes. The twins are a distance in a space we chose the axes of.',
            'What any destination costs. A count of children enrolled somewhere is not a '
            'tuition, an assessment or a share of one, and nothing here says which fund '
            'pays for any of it.',
            'The tax burden behind a regional district. Nashoba, North Middlesex, Ayer '
            'Shirley and Montachusett are funded by assessments on member towns with '
            'different bills, and no dataset here holds the membership lists or the '
            'apportionment, so no single bill can stand for any of them.',
            'Whether a town spending more per pupil educates a child better. Per-pupil '
            'spending is an input. Nothing in this report is an outcome measure.',
            'Which way any correlation runs. Every figure here is a cross-section of one '
            'year across many towns, which cannot separate a town choosing a higher bill '
            'from a town able to afford one.',
        ],
    )
    return payload, frame, raw, corr, twins_is, twins_does, overlap10, overlap25, dest


# ---- the pictures for readers who cannot run a component --------------------------
#
# Rule 7f: a chart on the WEB page is a component drawn from the payload, never an image.
# These SVGs exist for the other three readers the markdown serves -- /docs, the PDF, and
# an agent that runs no JavaScript -- and `fy28/src/components/analysisCharts.tsx` renders
# the component in the figure's place for everybody else. Same payload, one set of figures.

ROLE_FILL = {
    'lunenburg': '#1d4ed8', 'neighbour': '#0e7490', 'peer': '#7c3aed',
    'structural': '#b45309', 'behavioural': '#be123c',
}
ROLE_LABEL = {
    'lunenburg': 'Lunenburg', 'neighbour': 'shares a border', 'peer': 'peer (our choice)',
    'structural': 'looks like Lunenburg', 'behavioural': 'behaves like Lunenburg',
}
ROLE_ORDER = ('lunenburg', 'neighbour', 'peer', 'structural', 'behavioural')


def esc(t):
    return (str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;'))


def projection(outline):
    """Equirectangular, corrected for latitude, fitted to the drawing area.

    At 42 degrees north a degree of longitude covers cos(42) of what a degree of latitude
    covers -- about three quarters. Ignoring that is what makes a hand-rolled map of
    Massachusetts look stretched sideways, and it is the one piece of arithmetic this map
    needs to get right."""
    xs = [x for ring in outline for x, _ in ring]
    ys = [y for ring in outline for _, y in ring]
    return min(xs), max(xs), min(ys), max(ys)


def map_svg(payload):
    """Massachusetts, with every town this report names filled and pinned.

    A REAL MAP OF REAL BOUNDARIES, which is what was asked for: the outlines are the Census
    TIGER polygons for every town in the state, and each named town is filled by which
    comparison set it belongs to with a pin at its published centroid. Nothing is drawn by
    hand or placed by eye -- a town's position here is the Census Bureau's CENTLAT/CENTLON."""
    m = payload['map']
    W, pad, top = 756, 10, 74
    lon0, lon1, lat0, lat1 = projection(m['outline'])
    kx = math.cos(math.radians((lat0 + lat1) / 2))
    # THE HEIGHT IS DERIVED FROM THE STATE'S OWN SHAPE, not chosen. Fixing both dimensions
    # and scaling to fit left a band of dead space down each side, because Massachusetts
    # with its islands is wider than it is tall by a ratio no round number matches.
    k = (W - 2 * pad) / ((lon1 - lon0) * kx)
    H = int(round(top + pad + (lat1 - lat0) * k))
    offx, offy = pad, top

    def px(lon, lat):
        return (offx + (lon - lon0) * kx * k, offy + (lat1 - lat) * k)

    roles_used = [r for r in ROLE_ORDER if r in set(m['roles'].values())]
    alt = ('A map of Massachusetts. Every town is outlined; the %d towns this report '
           'compares are filled and pinned at their Census centroids, coloured by whether '
           'they border Lunenburg, are peers this project chose, resemble Lunenburg on '
           'structure, or behave like it.' % len(m['towns']))
    o = ["<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 %d %d' width='%d' "
         "height='%d' role='img' aria-label='%s' font-family='system-ui, -apple-system, "
         "sans-serif'>" % (W, H, W, H, esc(alt)),
         "<rect width='%d' height='%d' fill='#ffffff'/>" % (W, H),
         "<text x='%d' y='24' font-size='15' font-weight='700' fill='#111827'>Who Lunenburg "
         "is compared with, and where they are</text>" % pad,
         "<text x='%d' y='42' font-size='11.5' fill='#4b5563'>Every Massachusetts town "
         "outlined; the %d compared here are filled, at their Census centroids.</text>"
         % (pad, len(m['towns']))]
    lx = pad
    for r in roles_used:
        o.append("<circle cx='%.1f' cy='58' r='4.5' fill='%s'/>" % (lx + 5, ROLE_FILL[r]))
        o.append("<text x='%.1f' y='62' font-size='10.5' fill='#374151'>%s</text>"
                 % (lx + 13, esc(ROLE_LABEL[r])))
        lx += 16 + 5.8 * len(ROLE_LABEL[r]) + 12
    for ring in m['outline']:
        o.append("<polyline points='%s' fill='none' stroke='#e5e7eb' stroke-width='0.5'/>"
                 % ' '.join('%.1f,%.1f' % px(x, y) for x, y in ring))
    for name in sorted(m['towns']):
        fill = ROLE_FILL[m['roles'][name]]
        for ring in m['towns'][name]['rings']:
            o.append("<polygon points='%s' fill='%s' fill-opacity='0.30' stroke='%s' "
                     "stroke-width='0.9'/>"
                     % (' '.join('%.1f,%.1f' % px(x, y) for x, y in ring), fill, fill))
    for name in sorted(m['towns']):
        sh, fill = m['towns'][name], ROLE_FILL[m['roles'][name]]
        cx, cy = px(sh['lon'], sh['lat'])
        r = 5 if m['roles'][name] == 'lunenburg' else 3
        o.append("<circle cx='%.1f' cy='%.1f' r='%d' fill='%s' stroke='#ffffff' "
                 "stroke-width='1.2'/>" % (cx, cy, r, fill))
    # ONLY LUNENBURG IS LABELLED ON THE PICTURE. Thirty-two names at this scale is a smear,
    # and the tables below name every one of them, which the map cannot do and need not. The
    # interactive component labels on hover instead -- which is rule 7f's whole point about
    # what an image cannot give a reader.
    if 'Lunenburg' in m['towns']:
        cx, cy = px(m['towns']['Lunenburg']['lon'], m['towns']['Lunenburg']['lat'])
        # ABOVE AND LEFT, on a leader, with a white plate under it. Set beside the pin it
        # landed on top of the peer towns, which are immediately east -- the one place on
        # this map guaranteed to be crowded, because the peers were chosen for being near.
        tx, ty = cx - 74, cy - 26
        o.append("<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='#1d4ed8' "
                 "stroke-width='1'/>" % (cx, cy, tx + 66, ty + 3))
        o.append("<rect x='%.1f' y='%.1f' width='68' height='16' rx='3' fill='#ffffff' "
                 "fill-opacity='0.92'/>" % (tx - 2, ty - 9))
        o.append("<text x='%.1f' y='%.1f' font-size='11.5' font-weight='700' "
                 "fill='#1d4ed8'>Lunenburg</text>" % (tx, ty + 3))
    o.append('</svg>')
    return '\n'.join(o) + '\n'


def drivers_svg(payload):
    """What moves a tax bill: each correlation as one signed bar."""
    cs = payload['correlations']
    W, rowh, top = 756, 30, 90
    H = top + rowh * len(cs) + 22
    mid, half = 480, 180
    strongest = max(cs, key=lambda c: abs(c['r']))
    weakest = min(cs, key=lambda c: abs(c['r']))
    alt = ('Eight correlations across the %d Massachusetts towns that run their own '
           'K-12 district, drawn as signed bars. The strongest is %s at %s; the weakest is '
           '%s at %s.' % (payload['frame_size'], strongest['label'], strongest['text'],
                          weakest['label'], weakest['text']))
    o = ["<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 %d %d' width='%d' "
         "height='%d' role='img' aria-label='%s' font-family='system-ui, -apple-system, "
         "sans-serif'>" % (W, H, W, H, esc(alt)),
         "<rect width='%d' height='%d' fill='#ffffff'/>" % (W, H),
         "<text x='10' y='24' font-size='15' font-weight='700' fill='#111827'>What actually "
         "moves a tax bill</text>",
         "<text x='10' y='42' font-size='11.5' fill='#4b5563'>Correlation across the %d "
         "towns that run their own K–12 district. Tax figures FY%d, school figures "
         "SY%d.</text>" % (payload['frame_size'], payload['fy'], payload['sy']),
         "<text x='10' y='60' font-size='10.5' fill='#6b7280'>A bar to the right is a "
         "positive relationship, to the left negative. Neither says which way causation "
         "runs.</text>",
         "<line x1='%d' y1='%d' x2='%d' y2='%d' stroke='#9ca3af' stroke-width='1'/>"
         % (mid, top - 8, mid, top + rowh * len(cs) - 8)]
    for i, c in enumerate(cs):
        y = top + i * rowh
        w = max(abs(c['r']) * half, 1.0)
        x = mid if c['r'] >= 0 else mid - w
        fill = '#1d4ed8' if c['r'] >= 0 else '#be123c'
        o.append("<text x='%d' y='%.1f' font-size='11.5' fill='#374151' text-anchor='end'>"
                 "%s</text>" % (mid - half - 16, y, esc(c['label'])))
        o.append("<rect x='%.1f' y='%.1f' width='%.1f' height='13' rx='2' fill='%s' "
                 "fill-opacity='0.85'/>" % (x, y - 10, w, fill))
        o.append("<text x='%d' y='%.1f' font-size='11' font-weight='600' fill='#111827'>"
                 "%s</text>" % (mid + half + 14, y, esc(c['text'])))
    o.append('</svg>')
    return '\n'.join(o) + '\n'


def money(v):
    return usd(v) if v is not None else '—'


def num_or_dash(v, fmt='%.1f'):
    return (fmt % v) if v is not None else '—'


def markdown(payload, frame):
    """The document. Same figures, one pass, no second set of arithmetic.

    Rule 7f: the charts a web reader gets are COMPONENTS drawn from the payload. This file
    is what /docs serves, what the PDF renders from and what an agent that runs no
    JavaScript reads, so the same findings appear here as tables."""
    L = frame['Lunenburg']
    P = payload
    C = CLASSIFICATION
    out = []
    w = out.append

    w('# How Lunenburg compares: neighbours, peers, look-alikes and destinations')
    w('')
    w('Analysis, generated by `scripts/build_town_comparison.py`. Every figure below is '
      'computed from the documents listed at the end; nothing is typed.')
    w('')
    w('> **Four comparison sets, because they answer four questions.** The six towns that '
      'share a border. The five this project uses as peers. The towns the math picks out of '
      'all 351. And the places Lunenburg children are actually schooled, which is not a '
      'peer set at all.')
    w('')
    w('![%s](charts/towns-like-us-map.svg)' % (
        'A map of Massachusetts with every town outlined and the %d towns this report '
        'compares filled and pinned at their Census centroids, coloured by whether they '
        'border Lunenburg, are peers this project chose, resemble Lunenburg on structure, '
        'or behave like it.' % len(P['map']['towns'])))
    w('')
    w('## The short version')
    w('')
    for c in P['conclusions']:
        w('- **%s** %s' % (c['claim'], c['so_what']))
    w('')
    w('## What the figures count')
    w('')
    w(P['grain'])
    w('')

    w('## The towns Lunenburg borders, and the towns it is compared with')
    w('')
    w('Six neighbours, computed from the Census boundary polygons by shared vertices rather '
      'than from memory. Five peers, which are this project’s own choice — nothing '
      'in the town’s record names a cohort.')
    w('')
    w('| Town | Role | School district | Avg bill FY%d | Rank of 351 | Bill as %% of income '
      '| Per pupil SY%d | Commercial %% | Overrides won/put |'
      % (P['fy'], P['sy']))
    w('|---|---|---|---:|---:|---:|---:|---:|---:|')
    for r in P['local']:
        w('| %s | %s | %s | %s | %s | %s | %s | %s | %d of %d |'
          % (r['town'], ROLE_LABEL[r['role']], r['district'], money(r['bill']),
             r['rank'] if r['rank'] else '—', num_or_dash(r['pinc'], '%.2f%%'),
             money(r['pp']), num_or_dash(r['cip'], '%.1f%%'), r['won'], r['put']))
    w('')
    others = [r for r in P['local'] if r['town'] != 'Lunenburg' and r['pp']]
    above = [r for r in others if r['pp'] > L['pp']]
    if len(above) == len(others):
        w('**Every one of the eleven spends more per pupil than Lunenburg\u2019s %s.** The '
          'nearest is %s at %s, %s more; the highest is %s at %s. Read that beside the '
          'enrolment column further down before drawing anything from it \u2014 per-pupil '
          'spending is a ratio, and these districts have not all kept the same number of '
          'children.'
          % (money(L['pp']), min(above, key=lambda r: r['pp'])['town'],
             money(min(above, key=lambda r: r['pp'])['pp']),
             money(min(above, key=lambda r: r['pp'])['pp'] - L['pp']),
             max(above, key=lambda r: r['pp'])['town'],
             money(max(above, key=lambda r: r['pp'])['pp'])))
        w('')
    w('**Three of the six neighbours are in a regional district, and two of those share '
      'one.** Ashby and Townsend are both North Middlesex; Lancaster is in Nashoba; Shirley '
      'is in Ayer Shirley with Ayer. So "every bordering town’s school district" is not '
      'six districts, and a per-pupil figure beside a town is sometimes a figure that town '
      'shares with others.')
    w('')

    w('## The trend: what actually moves a tax bill')
    w('')
    w('Correlations across the %d Massachusetts towns that run their own K–12 district '
      '— the only shape in which town finance and school finance are the same '
      'taxpayer, which is Lunenburg’s own shape.' % P['frame_size'])
    w('')
    w('![%s](charts/towns-like-us-drivers.svg)' % (
        'Eight correlations drawn as signed bars, across the %d towns that run their own '
        'K\u201312 district. Average home value and income per capita both track the average '
        'tax bill closely; certified new growth against the tax bill is effectively nothing. '
        'A bar to the right is a positive relationship and to the left negative; neither says '
        'which way causation runs.' % P['frame_size']))
    w('')
    w('| Relationship | r |')
    w('|---|---:|')
    for c in P['correlations']:
        w('| %s | %s |' % (c['label'], c['text']))
    w('')
    w('**The bill is the house, and the household.** Home value and income per capita '
      'track the bill almost identically and nothing here separates them \u2014 they are '
      'largely measuring the same thing. Nothing about the commercial base comes close, and '
      'certified new growth, the measure of what a town built, has no relationship to the '
      'bill at all. What a commercial base shows up as is new growth itself, which is levy '
      'CAPACITY rather than a smaller bill.')
    w('')
    w('*What this does not show.* Which way any of it runs, and it cannot: this is one '
      'year read across many towns. A town with expensive houses can afford a higher bill '
      'and also chooses one. What would settle the question for Lunenburg specifically is '
      'not a comparison at all — it is the town’s own levy history against its own '
      'new growth, which is on [what growth would have to look like](/growth).')
    w('')

    w('### The town has already priced this, for this town')
    w('')
    w('Lunenburg levies a **single tax rate** and decides every November what share of the '
      'levy each class of property bears. At the Select Board\u2019s tax classification '
      'hearing on %s the Principal Assessor priced the maximum shift onto commercial, '
      'industrial and personal property. The minute:' % C['date_text'])
    w('')
    for q in [C['quotes'][0]] + C['quotes'][2:5]:
        w('> \u201c%s\u201d' % q)
        w('>')
    w('> \u2014 Select Board minutes, %s ([our copy](%s), [the town\u2019s](%s))'
      % (C['date_text'], C['url'], C['town_url']))
    w('')
    w('**Her arithmetic reconciles to the state\u2019s file.** The same minute states an '
      'average single-family bill of %s on an average value of %s; the Division of Local '
      'Services publishes %s on %s for the same year. Two independent records of the same '
      'two quantities, agreeing to the cent \u2014 which is what makes the rest of the '
      'analysis worth repeating, because the split-rate figures themselves are hers and we '
      'have not recomputed them.'
      % (usd2(C['avg_bill']), money(C['avg_value']), money(L['bill']), money(L['value'])))
    w('')
    w('She recommended against a split rate, noting that Lunenburg\u2019s commercial share '
      'is under a tenth of the base \u2014 this report computes %s for FY%d. **A shift '
      'moves the bill between classes. It does not reduce the levy**, which is set before '
      'any of this and is what the correlation above is really saying.'
      % (num_or_dash(L['cip'], '%.1f%%'), P['fy']))
    w('')
    w('## The towns the math says look like Lunenburg')
    w('')
    w('Two cohorts over the same %d towns. **Structural** matches on eight things a town '
      'does not decide: how many children, how many are low income, English learners or '
      'have disabilities, how many are placed out of district, the average house, income '
      'per capita, and the commercial share of the base. **Behavioural** matches on nine '
      'things it does: the bill, the bill as a share of income, per-pupil spending, override '
      'questions put and won, and the trend in the bill, in spending and in enrolment.'
      % P['frame_size'])
    w('')
    w('Spending and bills are deliberately absent from the structural cohort. A cohort '
      'matched on per-pupil spending cannot then be asked whether Lunenburg spends like its '
      'cohort — the answer would have been assumed.')
    w('')
    w('| Town | Cohort | Distance | Avg bill FY%d | Per pupil SY%d | Commercial %% | '
      'Overrides won/put | Enrolment since SY%d |' % (P['fy'], P['sy'], P['base_sy']))
    w('|---|---|---:|---:|---:|---:|---:|---:|')
    for r in P['twins']:
        w('| %s | %s | %s | %s | %s | %s | %d of %d | %s |'
          % (r['town'], ROLE_LABEL[r['role']], num_or_dash(r.get('distance'), '%.3f'),
             money(r['bill']), money(r['pp']), num_or_dash(r['cip'], '%.1f%%'),
             r['won'], r['put'], num_or_dash(r['enrchg'], '%+.1f%%')))
    w('')
    if not P['overlap10']:
        w('**No town appears in both closest-ten lists.** Widen each to twenty-five and %d '
          'do: %s.' % (len(P['overlap25']), ', '.join(P['overlap25'])))
    else:
        w('**In both closest-ten lists: %s.**' % ', '.join(P['overlap10']))
    w('')
    w('*What this does not show.* That either cohort is the right one. A distance is a '
      'statement about these measures given EQUAL WEIGHT and nothing more, and no weighting '
      'between dollars, percentages and counts is defensible enough to prefer. What the '
      'empty intersection does establish is that "who is like us" has no single answer.')
    w('')
    w('*And the grade-span test is a published fact, not a proxy.* An earlier version of '
      'this cohort admitted any district reporting a grade-10 MCAS score, and DESE reports '
      'those by district of RESIDENCE — so an elementary district whose teenagers '
      'attend a regional high school came third on structural similarity. Membership now '
      'reads `grades_served` off DESE’s school-level file: does this district operate a '
      'school reaching grade 12.')
    w('')

    w('### A per-pupil figure you may have heard, which is not this one')
    w('')
    w('Monty Tech\u2019s superintendent told the Finance Committee on 6 March 2025 that '
      '\u201cThe foundational budget per pupil spent is $20,827.\u201d That is a different '
      'school and a different quantity: a **foundation budget** is a Chapter 70 formula '
      'output \u2014 the state\u2019s model of what an adequate education costs \u2014 and '
      'it is thousands of dollars away from what any district actually spends. Every '
      'per-pupil figure in this report is SPENDING, all funds, reported after the year '
      'closed. ([the minute](https://lunenburgbudgetproject.org/docs/minutes/text/'
      'finance-committee/2025-03-06-minutes-7008.txt))')
    w('')
    w('## Where Lunenburg children are actually schooled')
    w('')
    w('Not a peer set. This is enrolment: where children who live in Lunenburg went in '
      'FY%d, and what kind of thing each place is — because a tax bill can only be set '
      'beside a district that one town’s taxpayers fund.' % P['fy'])
    w('')
    w('| Destination | Children | What funds it |')
    w('|---|---:|---|')
    kinds = {'own': 'Lunenburg’s own schools',
             'assessed': 'an assessment Lunenburg itself pays, as a member town',
             'one-town': 'one town’s taxpayers',
             'regional': 'assessments on several member towns, with different bills',
             'no-town': 'no single town — a charter or Commonwealth virtual school'}
    for d in P['destinations']:
        w('| %s | %s | %s |'
          % (d['district'], '{:,}'.format(d['students']), kinds[d['kind']]))
    w('')
    w('*What this does not show.* What any of it costs. A count of children is not a '
      'tuition, a charter assessment or a share of a regional assessment — and nothing '
      'here says which fund pays. Nor why a family chose a destination: the file records an '
      'enrolment and nothing else.')
    w('')

    w('## Who this was read for')
    w('')
    w('`notes/process/PERSONAS.md` carries six readers and one test each, every concern '
      'quoted from a real public meeting. The review of this report is recorded there. Two '
      'of its findings are in the report above and would not have been: the Principal '
      'Assessor had already priced the commercial shift for this town, and the town has '
      'never published a list of comparable communities \u2014 which makes every '
      '\u201ccompared with similar towns\u201d claim, including this one, rest on a set '
      'nobody has agreed.')
    w('')
    w('## The sources')
    w('')
    for s in P['sources']:
        w('- **%s** — %s' % (s['publisher'], s['note']))
        w('  `%s`%s' % (s['path'], '  · sha256 `%s`' % s['sha256'][:16] if s['sha256'] else ''))
        if s['url']:
            w('  Publisher’s address: %s' % s['url'])
    w('')
    w('## What this report cannot establish')
    w('')
    for t in P['not_established']:
        w('- %s' % t)
    w('')
    w('Three of these are registered in `sources/data/money-gaps.csv` and appear on '
      '[what we cannot answer](/what-we-cannot-answer), each with the one document that '
      'would close it: the town’s own list of comparable communities, the '
      'apportionment behind each regional district’s assessment, and what Lunenburg '
      'pays per child for each destination outside its schools.')
    w('')
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    payload, frame, raw, corr, t_is, t_does, o10, o25, dest = build()
    md = markdown(payload, frame)
    fresh = json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=False) + '\n'
    pics = {os.path.join(CHARTS, 'towns-like-us-map.svg'): map_svg(payload),
            os.path.join(CHARTS, 'towns-like-us-drivers.svg'): drivers_svg(payload)}

    if a.check:
        bad = []
        for path, want in [(OUT_JSON, fresh), (OUT_MD, md)] + sorted(pics.items()):
            if not os.path.exists(path):
                bad.append('%s does not exist' % os.path.relpath(path, ROOT))
            elif open(path, encoding='utf-8').read() != want:
                bad.append('%s is stale' % os.path.relpath(path, ROOT))
        if bad:
            print('STALE — run build_town_comparison.py\n  ' + '\n  '.join(bad))
            return 1
        print('ok — %s and %s both reproduce'
              % (os.path.relpath(OUT_JSON, ROOT), os.path.relpath(OUT_MD, ROOT)))
        return 0

    with open(OUT_JSON, 'w', encoding='utf-8') as fh:
        fh.write(fresh)
    with open(OUT_MD, 'w', encoding='utf-8') as fh:
        fh.write(md)
    for path, svg in pics.items():
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(svg)
    L = frame['Lunenburg']
    print('%s + %s' % (os.path.relpath(OUT_JSON, ROOT), os.path.relpath(OUT_MD, ROOT)))
    print('  frame: %d single-town K-12 districts; %d conclusions; %d towns on the map'
          % (len(frame), len(payload['conclusions']), len(payload['map']['towns'])))
    print('  %s' % ', '.join(os.path.basename(p) for p in sorted(pics)))
    print('  structural:  %s' % ', '.join('%s %.3f' % (c['town'], c['distance']) for c in t_is[:3]))
    print('  behavioural: %s' % ', '.join('%s %.3f' % (c['town'], c['distance']) for c in t_does[:3]))
    print('  in both closest ten: %s' % (', '.join(o10) if o10 else 'none'))
    print('  Lunenburg FY%d bill %s (%s of 351); %s per pupil SY%d'
          % (FY, usd(L['bill']), ordinal(L['rank']), usd(L['pp']), SY))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
