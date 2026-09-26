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
NSS = os.path.join(ROOT, 'sources', 'data', 'dese-ch70-formula.csv')
FUNC = os.path.join(ROOT, 'sources', 'data', 'dese-function-expenditure.csv')
CHERRY = os.path.join(ROOT, 'sources', 'data', 'dls-cherry-sheet.csv')
CH70 = os.path.join(ROOT, 'sources', 'data', 'dese-ch70-contribution.csv')
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


def town_effort():
    """WHAT EVERY TOWN IS REQUIRED TO RAISE FOR ITS OWN CHILDREN, per child, FY%d.

    THIS IS THE MEASURE THAT WORKS FOR REGIONAL TOWNS, and its absence is what made the
    first version of this report shrug at six of the eleven towns it compares. TJ: *"regional
    towns need an answer. HOW do they do it, mathematically"*.

    The answer is that the question was being asked at the wrong level. A per-pupil SPENDING
    figure belongs to a DISTRICT, and a regional district's spending cannot be split between
    its member towns -- which is true, and is why the earlier version stopped. But Chapter 70
    is computed per MUNICIPALITY whatever kind of district its children attend: DESE
    publishes, for all 351 towns, the foundation budget for that town's own children, the
    contribution the town is required to make toward it, and by subtraction what the state
    puts in. Divide each by the town's foundation enrolment and every town in Massachusetts
    is on one scale, Ashby beside Lunenburg beside Boston.

    So a regional town CAN be answered. What its taxpayers are required to put in per child
    is published; what the schools its children attend spend per pupil is published. What
    stays unknowable is only the middle step -- how a regional district's assessment is
    apportioned between its members -- and that is a narrower gap than "cannot be placed".

    WHAT IT IS NOT. A required contribution is a statutory MINIMUM, not what a town raises: a
    town may appropriate well above it and most do. And a foundation budget is the state's
    model of an adequate education, not anybody's spending. Rule 11 governs both.
    """ % FY
    out = {}
    for r in rows(CH70):
        if r['fy'] != str(FY):
            continue
        fb = num(r['town_foundation_budget'])
        rc = num(r['required_local_contribution'])
        en = num(r['town_foundation_enrollment'])
        if fb and en and fb > 0 and en > 0 and rc is not None:
            out[r['municipality']] = dict(
                children=en, foundation=fb, required=rc,
                foundation_pp=fb / en, required_pp=rc / en, state_pp=(fb - rc) / en,
                share=100.0 * (fb - rc) / fb)
    if 'Lunenburg' not in out:
        raise SystemExit('no FY%d Chapter 70 row for Lunenburg' % FY)
    return out


def taxable_value():
    """WHAT STANDS BEHIND EACH CHILD, in dollars of assessed value — the measure that
    unifies two mechanisms this report wrongly treated as separate.

    THE ERROR THIS REPLACES. The first version tested two ways a town can fund schools
    without leaning on homeowners: state money per child, and HOMES per pupil. TJ saw the
    problem immediately: *"You are suggesting new development that doesnt bring in new
    students leads to less taxes and more towards the school? Why doesnt that hold for more
    commercial business then? That seems off."*

    It is off, and he is right. A house that brings no children and a warehouse that brings
    no children do the same thing: they add taxable value without adding pupils. They are one
    mechanism, and counting HOUSES instead of measuring VALUE hid it — a count is not a
    quantity, which is rule 7's oldest complaint.

    WHAT THE CORRECTION COSTS US. On a count of homes Lunenburg looks comfortable: 2.19 per
    pupil against a median of 1.78, and the report said its tax base "is NOT thin relative to
    the number of children on it". On VALUE that is false. Lunenburg has $1.46M of taxable
    value per pupil against a median of $1.80M — 119th of 161. It has MORE houses per
    child than most towns and LESS money behind each child, because its houses are worth
    less. The claim was true of the proxy and false of the thing.

    AND IT EXPLAINS WHY BUSINESS LOOKS WEAK. Business is 8.7% of Lunenburg's base and housing
    is 91%, so commercial development moves total value per pupil slowly while a stock of
    expensive second homes moves it by multiples. Falmouth has 5.1 times Lunenburg's value
    per pupil and it is almost all residential. Same mechanism; different size of lever.
    """
    out = {}
    for r in rows(VALUES):
        if r['fy'] != str(FY):
            continue
        tot = num(r['total'])
        biz = sum(num(r[k]) or 0 for k in ('commercial', 'industrial', 'personal_property'))
        res = num(r['residential'])
        if tot and tot > 0:
            out[r['municipality']] = dict(total=tot, business=biz, residential=res or 0.0)
    if 'Lunenburg' not in out:
        raise SystemExit('no FY%d assessed-value row for Lunenburg' % FY)
    return out


def state_share():
    """What share of each town's FOUNDATION BUDGET the state expects to cover, FY%d.

    WHAT THIS IS, exactly, because it is easy to inflate. DESE publishes for every town the
    `town_foundation_budget` -- its own model of what an adequate education for that town's
    children costs -- and the `required_local_contribution`, what it requires the town to
    raise toward it. The difference is what the state expects to fund, and this is that
    difference as a share.

    IT IS NOT "the state pays X%% of our schools". The foundation budget is a formula output,
    not spending: Lunenburg's FY%d foundation is $24.2M across all the districts its children
    attend, while its district alone reported $27.1M of net school spending. And a required
    contribution is a MINIMUM, not what a town actually raises. Rule 11 governs the whole
    measure.

    IT RECONCILES. For Lunenburg the town file gives %s of its foundation covered by the
    state; DESE's district-level file for the same year gives Chapter 70 aid of $9,229,410
    against a required net school spending of $22,564,041, which is 40.9%%. Two different
    cuts of the formula, a point apart -- which is what makes the town-level figure safe to
    use for all 351.
    """ % (FY, FY, '{:.1f}%%')
    out = {}
    for r in rows(CH70):
        if r['fy'] != str(FY):
            continue
        fb, rc = num(r['town_foundation_budget']), num(r['required_local_contribution'])
        if fb and fb > 0 and rc is not None:
            out[r['municipality']] = 100.0 * (fb - rc) / fb
    if 'Lunenburg' not in out:
        raise SystemExit('no FY%d Chapter 70 contribution row for Lunenburg -- the join '
                         'matched nothing, which reads exactly like a town with no state '
                         'aid' % FY)
    return out


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


def heatmap(frame, val, effort, parcels, shapes_src=SHAPES):
    """EVERY TOWN IN MASSACHUSETTS, SHADED BY WHICHEVER MEASURE YOU PICK.

    TJ: *"i want to have the MAP be heat mapped based on whatever criteria... total pupils.
    total state funding. etc etc. basically hot and cold based on percent across min/max...
    visualize how it breaks down in the state, based on clicking a button"*

    WHY THE SHADE IS A PERCENTILE AND NOT A POSITION BETWEEN MIN AND MAX. Almost every
    measure here is badly skewed -- a handful of towns hold most of the property value, and
    Boston has forty times the pupils of Lunenburg. Shading on min-to-max gives one town a
    deep colour and washes the other 350 into an indistinguishable pale, which is a picture
    of the outlier rather than of the state. Colouring by RANK spreads the map evenly and
    lets a reader see structure -- and because that trades away magnitude, the actual value
    is on every town under the cursor, and the legend says which is which.

    WHAT IS COVERED, AND WHAT IS NOT. Chapter 70 and the tax files reach all 351
    municipalities, so anything built from them maps the whole state. Spending per pupil
    belongs to a DISTRICT, so it maps only the towns that run their own -- the rest are
    drawn unshaded rather than dropped, because a blank town is a fact about what is
    published and a missing town is a hole a reader cannot see."""
    with open(shapes_src, encoding='utf-8') as fh:
        fc = json.load(fh)
    shapes = {}
    for f in fc['features']:
        name = town_name(f['properties']['NAME'])
        geom = f['geometry']
        rings = (geom['coordinates'] if geom['type'] == 'Polygon'
                 else [r for poly in geom['coordinates'] for r in poly])
        simple = []
        for ring in rings:
            step = max(1, len(ring) // 24)
            pts = [[round(x, 3), round(y, 3)] for x, y in ring[::step]]
            if len(pts) > 3:
                pts.append(pts[0])
                simple.append(pts)
        if simple:
            shapes[name] = simple

    ch = {r['municipality']: r for r in rows(CH70) if r['fy'] == str(FY)}
    bills = {r['municipality']: num(r['avg_sf_bill']) for r in rows(BILLS)
             if r['fy'] == str(FY) and r['avg_sf_bill']}

    def town_kids(t):
        r = ch.get(t)
        return num(r['town_foundation_enrollment']) if r else None

    def per_child(t, f):
        n = town_kids(t)
        v = f(t)
        return (v / n) if (n and v) else None

    specs = [
        ('bill', 'Average tax bill on a home', 'usd',
         lambda t: bills.get(t), 'all 351 towns, FY%d' % FY),
        ('children', 'Children the town is funded for', 'count',
         town_kids, 'foundation enrolment, all 351 towns, FY%d' % FY),
        ('state_pp', 'State money per child', 'usd',
         lambda t: per_child(t, lambda x: (num(ch[x]['town_foundation_budget'])
                                           - num(ch[x]['required_local_contribution']))
                             if x in ch else None),
         'all 351 towns, FY%d' % FY),
        ('required_pp', 'What the town must raise per child', 'usd',
         lambda t: per_child(t, lambda x: num(ch[x]['required_local_contribution'])
                             if x in ch else None),
         'all 351 towns, FY%d' % FY),
        ('foundation_pp', 'What the state says each child needs', 'usd',
         lambda t: per_child(t, lambda x: num(ch[x]['town_foundation_budget'])
                             if x in ch else None),
         'foundation budget, all 351 towns, FY%d' % FY),
        # THE SPLIT ITSELF, as one number. The three Chapter 70 measures above are the two
        # sides of one identity -- foundation budget = what the town must raise + what the
        # state adds -- and a reader can hold them apart but not see them compose. This is
        # the share of that identity the state carries, which is the whole equation in a
        # single shade.
        ('state_share', 'The state\u2019s share of what it says each child needs', 'pct',
         lambda t: (100.0 * (num(ch[t]['town_foundation_budget'])
                             - num(ch[t]['required_local_contribution']))
                    / num(ch[t]['town_foundation_budget']))
         if (t in ch and num(ch[t]['town_foundation_budget'])) else None,
         'Chapter 70 equalises on property valuation and income; all 351 towns, FY%d' % FY),
        ('value_pp', 'Taxable value behind each child', 'usd',
         lambda t: per_child(t, lambda x: val[x]['total'] if x in val else None),
         'all property over foundation enrolment, FY%d' % FY),
        # THE OTHER HALF, and it was the missing one. TJ: *"which of these represents the
        # house value supporting students? i see 'business value'?"* -- the map had all
        # property together and business on its own, so the class that actually carries
        # nearly every town's school bill had no shading of its own. It is the DLS
        # RESIDENTIAL class over foundation enrolment, not total-minus-business: open space
        # and personal property are their own classes and lumping them in with houses would
        # be a proxy standing in for the thing (rule 7).
        ('residential_pp', 'House value behind each child', 'usd',
         lambda t: per_child(t, lambda x: val[x]['residential'] if x in val else None),
         'the DLS residential class over foundation enrolment, FY%d' % FY),
        ('business_share', 'Share of the tax base that is business', 'pct',
         lambda t: (100.0 * val[t]['business'] / val[t]['total']) if t in val else None,
         'FY%d' % FY),
        ('business_pp', 'Business value behind each child', 'usd',
         lambda t: per_child(t, lambda x: val[x]['business'] if x in val else None),
         'FY%d' % FY),
        ('per_pupil', 'Spent per pupil by its schools', 'usd',
         lambda t: frame[t]['pp'] if t in frame else None,
         'only towns running their own K–12 district, SY%d' % SY),
        ('above', 'Spent above what the state says its schools need', 'ratio',
         lambda t: (frame[t]['pp'] / effort[t]['foundation_pp'])
         if (t in frame and t in effort) else None,
         'only towns running their own K–12 district, SY%d' % SY),
        ('low_income', 'Share of children from low-income families', 'pct',
         lambda t: frame[t]['lowinc'] if t in frame else None,
         'only towns running their own K–12 district, SY%d' % SY),
        # A RATE, NOT A RATIO. This printed `2.14\u00d7` -- a multiplication sign on a
        # quantity that multiplies nothing. `above` is a real ratio (spending OVER the
        # foundation, so 1.27\u00d7 means 27% more than the state's figure); homes per child
        # is 2.14 houses for every one child, and the \u00d7 made it unreadable. The label
        # carries the unit, so the figure is the bare number -- rule 7b.
        ('homes_pp', 'Single-family homes per child', 'rate',
         lambda t: (parcels[t] / town_kids(t))
         if (t in parcels and town_kids(t)) else None,
         'all 351 towns, FY%d' % FY),
    ]
    measures = []
    for key, label, kind, f, note in specs:
        vals = {}
        for t in shapes:
            try:
                v = f(t)
            except (KeyError, TypeError, ZeroDivisionError):
                v = None
            if v is not None:
                vals[t] = round(v, 3)
        if len(vals) < 100:
            raise SystemExit('heat map measure %r covers only %d towns' % (key, len(vals)))
        series = sorted(vals.values())
        measures.append(dict(
            key=key, label=label, kind=kind, note=note, covered=len(vals),
            values=vals, lo=series[0], hi=series[-1],
            median=st.median(series),
            lunenburg=vals.get('Lunenburg')))
    return dict(shapes=shapes, measures=measures, n_towns=len(shapes))


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
        # NO RINGS HERE. The heat map already ships every town's polygon, including these
        # thirty-two, so carrying a second and more detailed copy put Massachusetts in the
        # payload three times over. What this block uniquely knows is the CENTROID, which is
        # where the pin goes, and that is all it keeps.
        feats[name] = dict(
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

def build_conclusions(frame, corr, twins_is, twins_does, overlap10, overlap25, dest, sets,
                      effort=None, parcels=None):
    """The eight cards, written so the METRIC carries its own meaning.

    REWRITTEN 26 SEPTEMBER 2026, after TJ read the first version and could not read it.
    Verbatim, on four separate cards: *"citizens do not understand what this means: +0.91,
    correlation between average home value and average tax bill, 161 towns"*; *"dont even
    understand the meaning of this: 224.25, a year off a $350,000 home, at the largest shift
    onto commercial the statute permits"*; *"how does THIS even mathematically make sense:
    Of the towns most like Lunenburg, 9 of 10 spend more per pupil and 7 charge less. 9 of
    10 and 7 of 10?! what does 'charge' here mean"*; and *"0 of 10 ... 10 of what?!?!"*

    Every one of those is rule 7b, which this file was supposed to be obeying: a bare number
    in a stat box, and insider vocabulary. Three lessons, and they generalise:

      * A CORRELATION COEFFICIENT IS NOT A METRIC A RESIDENT CAN USE. `r +0.91` is a real
        measurement and it is unreadable, so it belongs in the chart and the table, not on a
        card. The card carries the SLOPE instead -- about $995 more on a town's average bill
        for every extra $100,000 its average home is worth -- which is the same finding in
        the units the reader's own tax bill is printed in.
      * TWO FIGURES ON ONE CARD READ AS A PARTITION. `9 of 10 ... and 7 charge less` looked
        like 9+7 out of 10. They are two independent facts about the same ten towns, and the
        second belongs in the supporting line saying plainly that it is the same ten.
      * `0 of 10` STATES A DENOMINATOR NOBODY HAS. A count needs the noun: the card now says
        `Not one`, and the unit says of what.
    """
    L = frame['Lunenburg']
    towns = sorted(frame)
    n = len(frame)
    tw = [c['town'] for c in twins_is]
    more = [t for t in tw if frame[t]['pp'] > L['pp']]
    cheaper = [t for t in tw if frame[t]['bill'] < L['bill']]
    pp_order = sorted(towns, key=lambda t: -frame[t]['pp'])
    pp_rank = pp_order.index('Lunenburg') + 1
    group = tw + ['Lunenburg']
    g_rank = sorted(group, key=lambda t: -frame[t]['totalcagr']).index('Lunenburg') + 1
    lost_more = [t for t in tw if frame[t]['enrchg'] < L['enrchg']]
    C = CLASSIFICATION

    by_kind = {}
    for d in dest:
        by_kind[d['kind']] = by_kind.get(d['kind'], 0) + d['students']
    left = sum(v for k, v in by_kind.items() if k != 'own')

    ov_put = {t: len(sets['ov'].get(t, [])) for t in sets['neighbours'] + ['Lunenburg']}
    ov_won = {t: len([q for q in sets['ov'].get(t, []) if q['result'] == 'WIN'])
              for t in ov_put}
    loudest = max(sets['neighbours'], key=lambda t: ov_put[t])
    silent = [t for t in sets['neighbours'] if ov_put[t] == 0]
    since = 'FY%d' % sets['first_override_fy']

    E = effects(frame)
    E['ratio_t'] = '%.2f' % E['ratio']
    E['med_ratio_t'] = '%.2f' % E['med_ratio']
    G = cheap_and_generous(frame, effort, parcels)
    PR = predictors(frame, taxable_value(), effort)
    RG = regional_picture(frame, sets['dese'])
    CH = cherry_sheet(sets['dese'])

    rows_out = [
        conclusion(
            id='what-predicts-spending',
            claim='Wealth per child predicts school spending. State aid, size and poverty do not.',
            detail=(
                'Twelve things were tested against what a district spends per pupil, across '
                'all %d towns that run their own K–12 school. The strongest by a long '
                'way is how much taxable property stands behind each child: r %s, which '
                'accounts for %s of the difference between districts. How much the state '
                'sends per child accounts for %s. How many pupils a district has accounts '
                'for %s. The share of children from low-income families, %s. The share of '
                'the tax base that is business, %s. Put the five together and they account '
                'for %s of the difference — so %s of what separates a district spending '
                'the most from one spending the least is none of those things.'
                % (PR['n'], _rt(PR, 'value_pp'), pct(_re(PR, 'value_pp'), 0),
                   pct(_re(PR, 'state_pp'), 0), pct(_re(PR, 'size'), 0),
                   pct(_re(PR, 'low_income'), 0), pct(_re(PR, 'business_share'), 0),
                   pct(PR['explained_together'], 0), pct(PR['unexplained'], 0))),
            figures={
                'best': figure(_re(PR, 'value_pp'), pct(_re(PR, 'value_pp'), 0),
                               'of the difference in spending per pupil is accounted for by '
                               'how much taxable property stands behind each child — '
                               'the strongest of twelve things tested'),
                'best_r': figure(abs(_rv(PR, 'value_pp')), _rt(PR, 'value_pp')),
                'state': figure(_re(PR, 'state_pp'), pct(_re(PR, 'state_pp'), 0)),
                'size': figure(_re(PR, 'size'), pct(_re(PR, 'size'), 0)),
                'lowinc': figure(_re(PR, 'low_income'), pct(_re(PR, 'low_income'), 0)),
                'biz': figure(_re(PR, 'business_share'), pct(_re(PR, 'business_share'), 0)),
                'together': figure(PR['explained_together'], pct(PR['explained_together'], 0)),
                'unexplained': figure(PR['unexplained'], pct(PR['unexplained'], 0)),
                'n': figure(PR['n'], str(PR['n'])),
                'twelve': figure(12, 'Twelve'),
            },
            figure='best',
            kind='measured',
            bearing='sizes',
            allow=('12',),
            basis=('Pearson correlation of each measure against DESE per-pupil total '
                   'expenditure SY%d, over the %d-town frame; then standardised least '
                   'squares on the five that are not near-duplicates of one another.'
                   % (SY, PR['n'])),
            not_shown=(
                'Which way any of it runs, and what the unexplained share IS. A district '
                'with more wealth behind each child may spend more because it can, or may '
                'have attracted that wealth by spending more; one year read across many '
                'towns cannot separate those. And the %s left over is not evidence of '
                'choice — it is the absence of evidence for the four explanations '
                'people reach for. Special education caseload, debt service, contract '
                'history and regional structure are all candidates this report does not '
                'hold.' % pct(PR['unexplained'], 0)),
            so_what=('%s of the difference is none of wealth, aid, size, poverty or tax base.'
                     % pct(PR['unexplained'], 0)),
            see=[('/analysis/per-pupil-spending', 'Per-pupil spending, in full')]),

        conclusion(
            id='regionalising-and-the-overhead',
            claim='Regional districts do not spend less on administration: %s a pupil against %s.'
                  % (usd(RG['admin_regional']), usd(RG['admin_single'])),
            detail=(
                'Regionalising is argued for as a way to share overhead, so the measure is '
                'administration per pupil, which DESE publishes on its own. Across %d '
                'districts, the %d regional ones spend a median of %s a pupil on '
                'administration and the %d single-town ones spend %s. Adding instructional '
                'leadership changes nothing: %s against %s. What DOES cut overhead is SIZE '
                'rather than structure, and only somewhat — the smallest quarter of '
                'districts (median %s pupils) spend %s a pupil, the largest quarter (median '
                '%s) spend %s. Lunenburg already spends %s, which is %s of %d.'
                % (RG['n'], RG['n_regional'], usd(RG['admin_regional']), RG['n_single'],
                   usd(RG['admin_single']), usd(RG['overhead_regional']),
                   usd(RG['overhead_single']), '{:,}'.format(RG['small_pupils']),
                   usd(RG['small_admin']), '{:,}'.format(RG['big_pupils']),
                   usd(RG['big_admin']), usd(RG['lun_admin']), ordinal(RG['lun_rank']),
                   RG['n'])),
            figures={
                'admin_regional': figure(RG['admin_regional'], usd(RG['admin_regional']),
                                         'median administration spending per pupil in '
                                         'regional districts — against %s in single-town '
                                         'districts' % usd(RG['admin_single'])),
                'admin_single': figure(RG['admin_single'], usd(RG['admin_single'])),
                'oh_regional': figure(RG['overhead_regional'], usd(RG['overhead_regional'])),
                'oh_single': figure(RG['overhead_single'], usd(RG['overhead_single'])),
                'small_pupils': figure(RG['small_pupils'], '{:,}'.format(RG['small_pupils'])),
                'small_admin': figure(RG['small_admin'], usd(RG['small_admin'])),
                'big_pupils': figure(RG['big_pupils'], '{:,}'.format(RG['big_pupils'])),
                'big_admin': figure(RG['big_admin'], usd(RG['big_admin'])),
                'lun_admin': figure(RG['lun_admin'], usd(RG['lun_admin'])),
                'lun_rank': figure(RG['lun_rank'], ordinal(RG['lun_rank'])),
                'n': figure(RG['n'], str(RG['n'])),
                'n_reg': figure(RG['n_regional'], str(RG['n_regional'])),
                'n_single': figure(RG['n_single'], str(RG['n_single'])),
            },
            figure='admin_regional',
            kind='measured',
            bearing='lever',
            basis=('DESE per-pupil expenditure by category, SY%d: Administration and '
                   'Instructional Leadership, across every district operating a school '
                   'through grade 12.' % SY),
            not_shown=(
                'THE MONEY, which this tested nothing of. Regional districts receive a state '
                'transportation reimbursement under c.71 s.16C that single-town districts get '
                'nothing of \u2014 %s statewide in FY%d \u2014 and that, not administration, '
                'is the mechanism the argument actually rests on. A finding of no effect on '
                'the measure you COULD take is not a finding of no effect. And what '
                'regionalising WOULD do here is a different question again from what '
                'existing regional districts spend. Massachusetts regional districts were '
                'formed decades ago under different terms, they carry transport costs a '
                'single-town district does not, and none of that is separated here. What the '
                'figures do rule out is the simple version of the argument: that regional '
                'districts are visibly cheaper to run. On administration they are not, and '
                'Lunenburg is already among the leanest.'
                % (usd(CH['statewide_transport']), FY)),
            so_what=('On ADMINISTRATION, no. The transport money is a separate line and a '
                     'real one.'),
            see=[('/analysis/monty-tech', 'The regional district Lunenburg already belongs to')]),

        conclusion(
            id='who-gets-it-without-the-taxpayer',
            claim='%d of %d towns charge among the least and spend among the most on each pupil.'
                  % (len(G['towns']), G['n']),
            detail=(
                'Take the cheapest quarter of these towns by average single-family tax bill '
                '— %s or less — and the top quarter by spending per pupil, %s or '
                'more. %d towns are in both: %s. They are not a mystery and they are not '
                'doing anything clever. %d of them are among the communities where the '
                'state\u2019s own formula finds the least LOCAL EFFORT available \u2014 '
                'Chapter 70 measures a town by its equalized property valuation and its '
                'residents\u2019 income, and covers what those two cannot reach: the '
                'state puts in a median of %s per child across those, against %s for the '
                'middle town here. The other %d are resort and retirement towns with a great '
                'many houses and very few children — Falmouth has %.1f single-family '
                'homes for every pupil, against %.1f for the middle town, so a modest bill '
                'on a great many houses still raises a great deal per child. Lunenburg is '
                'neither: %s a year on the average home, %s per pupil, %s per child from the '
                'state and %.1f homes per pupil.'
                % (usd(G['cheap_cut']), usd(G['spend_cut']), len(G['towns']),
                   ', '.join(r['town'] for r in G['towns']), G['by_state'],
                   usd(st.median(r['state_pp'] for r in G['towns']
                                 if r['how'] in ('the state', 'both'))),
                   usd(G['med_state']), G['by_houses'],
                   max(r['homes_per_pupil'] for r in G['towns']), G['med_homes'],
                   usd(G['lun']['bill']), usd(G['lun']['pp']), usd(G['lun']['state_pp']),
                   G['lun']['homes_per_pupil'])),
            figures={
                'both': figure(len(G['towns']), '%d of %d' % (len(G['towns']), G['n']),
                               'towns in BOTH the cheapest quarter by tax bill and the top '
                               'quarter by spending per pupil'),
                'both_n': figure(len(G['towns']), str(len(G['towns']))),
                'n': figure(G['n'], str(G['n'])),
                'by_state': figure(G['by_state'], str(G['by_state'])),
                'by_houses': figure(G['by_houses'], str(G['by_houses'])),
                'cheap_cut': figure(G['cheap_cut'], usd(G['cheap_cut'])),
                'spend_cut': figure(G['spend_cut'], usd(G['spend_cut'])),
                'med_state': figure(G['med_state'], usd(G['med_state'])),
                'their_state': figure(
                    st.median(r['state_pp'] for r in G['towns']
                              if r['how'] in ('the state', 'both')),
                    usd(st.median(r['state_pp'] for r in G['towns']
                                  if r['how'] in ('the state', 'both')))),
                'top_homes': figure(max(r['homes_per_pupil'] for r in G['towns']),
                                    '%.1f' % max(r['homes_per_pupil'] for r in G['towns'])),
                'med_homes': figure(G['med_homes'], '%.1f' % G['med_homes']),
                'lun_bill': figure(G['lun']['bill'], usd(G['lun']['bill'])),
                'lun_pp': figure(G['lun']['pp'], usd(G['lun']['pp'])),
                'lun_state': figure(G['lun']['state_pp'], usd(G['lun']['state_pp'])),
                'lun_homes': figure(G['lun']['homes_per_pupil'],
                                    '%.1f' % G['lun']['homes_per_pupil']),
                'seventy': figure(70, '70'),
            },
            figure='both',
            kind='measured',
            bearing='sizes',
            allow=('70',),
            basis=('Quartile cuts on the FY%d average single-family bill and SY%d per-pupil '
                   'spending across the %d-town frame; each town in the intersection tested '
                   'against twice the frame median for state dollars per child and for '
                   'single-family homes per pupil.' % (FY, SY, G['n'])),
            not_shown=(
                'That either route is available to Lunenburg. One requires having among the '
                'least property value and income behind each child in the state, and the '
                'other requires three '
                'times the usual number of houses per child — neither is a policy '
                'anybody here can vote for. What this rules OUT is the hope that some town '
                'has found a way to fund schools well without either taxing residents or '
                'being carried; within these %d towns, none has. It also says nothing about '
                'what those schools achieve.' % G['n']),
            so_what=('%d have the least property value and income behind each child, so the '
                     'state covers it. %d have many houses.'
                     % (G['by_state'], G['by_houses'])),
            see=[('/state-aid', 'What the state actually sends')]),

        conclusion(
            id='the-bill-is-the-house',
            claim='A town’s tax bill follows house prices: about %s more per extra %s of home.'
                  % (usd(E['per100k']), usd(100000)),
            detail=(
                'Across the %d Massachusetts towns that run their own K–12 school '
                'district, what separates a high tax bill from a low one is almost entirely '
                'what the houses are worth. Every extra %s of average single-family value '
                'goes with about %s more on the average single-family tax bill. The most '
                'expensive fifth of those towns average %s a year; the cheapest fifth '
                'average %s. Income moves with it just as closely, which is the same thing '
                'said twice — towns with expensive houses have wealthy households in '
                'them.'
                % (n, usd(100000), usd(E['per100k']), usd(E['val_hi']), usd(E['val_lo']))),
            figures={
                'per100k': figure(E['per100k'], usd(E['per100k']),
                                  'more on a town’s average single-family tax bill for '
                                  'every extra %s its average home is worth' % usd(100000)),
                'per': figure(100000, usd(100000)),
                'val_hi': figure(E['val_hi'], usd(E['val_hi'])),
                'val_lo': figure(E['val_lo'], usd(E['val_lo'])),
                'n': figure(n, str(n)),
                'twelve': figure(12, '12'),
            },
            figure='per100k',
            kind='measured',
            bearing='sizes',
            allow=('12',),
            basis=('dls-avg-tax-bill.csv at FY%d over the %d single-town K–12 districts: '
                   'the least-squares slope of the average bill on the average single-family '
                   'value, and the mean bill in the top and bottom fifths by value.'
                   % (FY, n)),
            not_shown=(
                'Which way it runs. A town whose houses are worth more can afford a bigger '
                'bill and also chooses one, and nothing in a single year read across many '
                'towns separates those. Nor is this what would happen to ONE town’s '
                'bill if its houses appreciated: a revaluation moves the rate as well as the '
                'value, and the levy is set before either.'),
            so_what=('The most expensive fifth of towns average %s a year. The cheapest '
                     'fifth, %s.' % (usd(E['val_hi']), usd(E['val_lo']))),
            see=[('/growth', 'What commercial growth would have to look like')]),

        conclusion(
            id='what-taxing-business-harder-would-save',
            claim='Taxing local business at the maximum rate the law allows would save a home %s.'
                  % usd2(C['saving']),
            detail=(
                'Lunenburg charges every property the same rate — %s per thousand '
                'dollars of value in FY%d. A town may instead shift part of the levy onto '
                'commercial, industrial and personal property, and at the Select Board’s '
                'tax classification hearing on %s the Principal Assessor priced the largest '
                'shift the statute permits. It would move the residential rate to %s and the '
                'business rate to %s: a saving of %s a year on a %s home, and about %s a '
                'year more on a comparable business. She advised against it. Her figures '
                'reconcile to the state’s file — the same minute states an average '
                'bill of %s on an average value of %s, and the Division of Local Services '
                'publishes %s on %s.'
                % (usd2(C['rate']), FY, C['date_text'], usd2(C['res_rate']),
                   usd2(C['cip_rate']), usd2(C['saving']), usd(C['home']),
                   usd2(C['cip_cost']), usd2(C['avg_bill']), usd(C['avg_value']),
                   usd(L['bill']), usd(L['value']))),
            figures={
                'saving': figure(C['saving'], usd2(C['saving']),
                                 'a year off a %s home — the whole of what shifting tax '
                                 'onto local business could do for a homeowner here'
                                 % usd(C['home'])),
                'home': figure(C['home'], usd(C['home'])),
                'cip_cost': figure(C['cip_cost'], usd2(C['cip_cost'])),
                'rate': figure(C['rate'], usd2(C['rate'])),
                'res_rate': figure(C['res_rate'], usd2(C['res_rate'])),
                'cip_rate': figure(C['cip_rate'], usd2(C['cip_rate'])),
                'avg_bill': figure(C['avg_bill'], usd2(C['avg_bill'])),
                'avg_value': figure(C['avg_value'], usd(C['avg_value'])),
                'dls_bill': figure(L['bill'], usd(L['bill'])),
                'dls_value': figure(L['value'], usd(L['value'])),
                'fy': figure(FY, 'FY%d' % FY),
                'when': figure(C['date'], C['date_text']),
            },
            figure='saving',
            kind='measured',
            bearing='lever',
            basis=('Select Board minutes, %s, the tax classification hearing: the Principal '
                   'Assessor’s split-rate analysis as the minute records it, with its '
                   'average bill and average value checked against dls-avg-tax-bill.csv at '
                   'FY%d.' % (C['date_text'], FY)),
            not_shown=(
                'We did not recompute her split-rate arithmetic. Rule 13a applies: a figure '
                'a person assembled is stated, however official the setting. What raises '
                'confidence is the half that CAN be checked and does reconcile exactly. And '
                'note what a shift is not — it moves the same bill between classes of '
                'property and lowers the total the town raises by nothing at all.'),
            so_what=('The same shift adds about %s to a business. The town’s own '
                     'assessor advised against it.' % usd2(C['cip_cost'])),
            see=[('/growth', 'What commercial growth would have to look like')]),

        conclusion(
            id='not-for-want-of-aid-or-tax-base',
            claim='Lunenburg spends %s less per pupil than the middle comparable district.'
                  % usd(E['med_pp'] - L['pp']),
            detail=(
                'Of the %d Massachusetts towns that run their own K–12 district, '
                'Lunenburg is %s by spending per pupil: %s against %s for the district in '
                'the middle. The two explanations everybody reaches for are both checkable, '
                'and only one of them survives. STATE HELP: the state expects to cover %s of '
                'Lunenburg\u2019s foundation budget against %s for the middle district, '
                'which is %s of %d \u2014 more help than most, not less. THE TAX BASE is a '
                'different story, and an earlier version of this card had it wrong: counting '
                'HOMES, Lunenburg has %.1f per pupil against %.1f for the middle district and '
                'looks comfortable; counting VALUE, which is what a bill is actually levied '
                'on, it has %s per pupil against a median of %s. More houses per child than '
                'most towns, and less money behind each child. One of the two usual '
                'explanations is genuinely ruled out. The other is not.'
                % (n, ordinal(pp_rank), usd(L['pp']), usd(E['med_pp']),
                   pct(E['lun_share'], 0), pct(E['med_share'], 0),
                   ordinal(E['share_rank']), E['n_share'],
                   E['lun_homes'], E['med_homes'], usd(E['val_pp']),
                   usd(E['med_val_pp']))),
            figures={
                'gap': figure(E['med_pp'] - L['pp'], usd(E['med_pp'] - L['pp']),
                              'less per pupil than the middle of %d comparable districts '
                              '— with more state help and more homes per pupil than '
                              'most of them' % n),
                'pp': figure(L['pp'], usd(L['pp'])),
                'med_pp': figure(E['med_pp'], usd(E['med_pp'])),
                'pp_rank': figure(pp_rank, ordinal(pp_rank)),
                'n': figure(n, str(n)),
                'lun_share': figure(E['lun_share'], pct(E['lun_share'], 0)),
                'med_share': figure(E['med_share'], pct(E['med_share'], 0)),
                'share_rank': figure(E['share_rank'], ordinal(E['share_rank'])),
                'n_share': figure(E['n_share'], str(E['n_share'])),
                'lun_homes': figure(E['lun_homes'], '%.1f' % E['lun_homes']),
                'med_homes': figure(E['med_homes'], '%.1f' % E['med_homes']),
                'val_pp': figure(E['val_pp'], usd(E['val_pp'])),
                'med_val_pp': figure(E['med_val_pp'], usd(E['med_val_pp'])),
                'twelve': figure(12, '12'),
            },
            figure='gap',
            kind='measured',
            bearing='sizes',
            allow=('12',),
            basis=('DESE per-pupil total expenditures SY%d; DESE Chapter 70 municipal '
                   'contributions FY%d (town foundation budget less required local '
                   'contribution); DLS single-family parcels FY%d over DESE FTE pupils.'
                   % (SY, FY, FY)),
            not_shown=(
                'WHY. Ruling out two explanations is not finding a third, and this report '
                'does not have one. The remaining candidates — what the town chooses to '
                'appropriate, how the budget is split between the schools and the town side, '
                'debt service, other local revenue — are not separated by anything here, '
                'and a reader who takes this as evidence of any one of them has gone further '
                'than the data. Nor does spending less mean doing worse: there is no outcome '
                'measure in this report at all.'),
            so_what=('Not for want of state aid \u2014 it gets more than most. Its taxable '
                     'value per pupil is below the middle.'),
            see=[('/analysis/per-pupil-spending', 'Per-pupil spending, in full'),
                 ('/state-aid', 'What the state actually sends')]),

        conclusion(
            id='how-far-above-the-floor',
            claim='Lunenburg spends %sx what the state says its schools need. The middle town spends %sx.'
                  % (E['ratio_t'], E['med_ratio_t']),
            detail=(
                'A raw per-pupil comparison is unfair to a town with poorer children or a '
                'thinner tax base, and the state already solves that: it computes a '
                'FOUNDATION BUDGET for every town from its own children and its own wealth. '
                'Measuring each town against its OWN floor is the like-for-like comparison. '
                'Lunenburg’s foundation works out at %s per pupil and it spends %s, '
                'which is %sx — %s of %d. The middle district here spends %sx its own '
                'floor. Spending at that middle ratio would put Lunenburg at %s per pupil, '
                '%s more than it spends now. This is also the one comparison on the page '
                'closest to a decision: how far above the floor to go is what a town meeting '
                'votes on.'
                % (usd(E['foundation_pp']), usd(L['pp']), E['ratio_t'],
                   ordinal(E['ratio_rank']), E['n_ratio'], E['med_ratio_t'],
                   usd(E['at_median']), usd(E['at_median_gap']))),
            figures={
                'ratio': figure(E['ratio'], E['ratio_t'],
                                'what Lunenburg spends per pupil as a multiple of the '
                                'state says Lunenburg’s schools need — the '
                                'middle comparable district spends %sx' % E['med_ratio_t']),
                'med_ratio': figure(E['med_ratio'], E['med_ratio_t']),
                'ratio_rank': figure(E['ratio_rank'], ordinal(E['ratio_rank'])),
                'n_ratio': figure(E['n_ratio'], str(E['n_ratio'])),
                'foundation_pp': figure(E['foundation_pp'], usd(E['foundation_pp'])),
                'pp': figure(L['pp'], usd(L['pp'])),
                'at_median': figure(E['at_median'], usd(E['at_median'])),
                'gap': figure(E['at_median_gap'], usd(E['at_median_gap'])),
            },
            figure='ratio',
            kind='measured',
            bearing='lever',
            basis=('DESE per-pupil total expenditures SY%d over the town foundation budget '
                   'per foundation pupil from the FY%d Chapter 70 municipal contribution '
                   'file, for every town in the frame.' % (SY, FY)),
            not_shown=(
                'That Lunenburg SHOULD spend at the middle ratio, or that the towns above it '
                'are right to. This measures distance from a formula, not whether any amount '
                'is the correct one, and there is no outcome measure in this report. Two '
                'mechanical cautions as well: spending is ALL FUNDS, so a town winning more '
                'grants or more circuit-breaker reimbursement shows a higher ratio without '
                'its taxpayers doing anything; and the foundation budget is itself widely '
                'argued to understate what some costs — special education and health '
                'insurance above all — actually run to.'),
            so_what=('At the middle ratio Lunenburg would spend %s more per pupil.'
                     % usd(E['at_median_gap'])),
            see=[('/analysis/per-pupil-spending', 'Per-pupil spending, in full'),
                 ('/state-aid', 'What the state actually sends')]),

        conclusion(
            id='the-look-alikes-spend-more',
            claim='%d of %d towns most like Lunenburg spend more per pupil than Lunenburg does.'
                  % (len(more), len(tw)),
            detail=(
                'The %d towns are picked by the MATH, not by geography: the closest to '
                'Lunenburg on eight things a town does not choose — how many children '
                'it has, how many are from low-income families, are learning English or have '
                'a disability, how many are placed in schools outside the district, what the '
                'average house is worth, income per head, and how much of the tax base is '
                'business rather than housing. Spending and tax bills are deliberately left '
                'OUT of that matching, so they can be compared afterwards instead of '
                'assumed. Lunenburg spends %s per pupil, which is %s of %d; the ten run from '
                '%s to %s. Separately, %d of those same ten have a SMALLER average '
                'single-family tax bill than Lunenburg’s %s.'
                % (len(tw), usd(L['pp']), ordinal(pp_rank), n,
                   usd(min(frame[t]['pp'] for t in tw)), usd(max(frame[t]['pp'] for t in tw)),
                   len(cheaper), usd(L['bill']))),
            figures={
                'more': figure(len(more), '%d of %d' % (len(more), len(tw)),
                               'towns most like Lunenburg that spend more per pupil than it '
                               'does — matched on what they ARE, not what they spend'),
                'cheaper': figure(len(cheaper), str(len(cheaper))),
                'tw': figure(len(tw), str(len(tw))),
                'pp': figure(L['pp'], usd(L['pp'])),
                'pp_rank': figure(pp_rank, ordinal(pp_rank)),
                'n': figure(n, str(n)),
                'bill': figure(L['bill'], usd(L['bill'])),
                'pp_lo': figure(min(frame[t]['pp'] for t in tw),
                                usd(min(frame[t]['pp'] for t in tw))),
                'pp_hi': figure(max(frame[t]['pp'] for t in tw),
                                usd(max(frame[t]['pp'] for t in tw))),
                'eight': figure(8, 'eight'),
            },
            figure='more',
            kind='measured',
            bearing='sizes',
            basis=('DESE per-pupil total expenditures at SY%d and DLS bills at FY%d over the '
                   '%d-town frame; the ten nearest by root-mean z-distance on the eight '
                   'structural measures.' % (SY, FY, n)),
            not_shown=(
                'That any of them educates a child better or worse. Per-pupil spending is '
                'money in, not results out. It is also ALL FUNDS — state aid, grants '
                'and reimbursements are inside it — so a town spending more per pupil '
                'is not necessarily taxing its residents more to do it. And see the next '
                'card: most of this gap is the number of pupils, not the number of dollars.'),
            so_what=('%d of those same %d also have a smaller average tax bill than '
                     'Lunenburg.' % (len(cheaper), len(tw))),
            see=[('/analysis/per-pupil-spending', 'Per-pupil spending, in full')]),

        conclusion(
            id='the-denominator-does-most-of-it',
            claim='Lunenburg’s TOTAL school spending grew %s a year — %s fastest of these %d towns.'
                  % (pct(L['totalcagr'], 1), ordinal(g_rank), len(group)),
            detail=(
                'Per-pupil spending is a fraction, and the gap on the card above is mostly '
                'its bottom half. Total school spending — per-pupil multiplied by '
                'pupils, which is DESE’s own arithmetic run backwards — grew %s a '
                'year at Lunenburg between SY%d and SY%d, against %s to %s across the same '
                '%d look-alike towns. That puts Lunenburg %s of %d: the middle. What '
                'separates them is children. Lunenburg’s enrolment fell %s over those '
                'years; %d of the %d look-alikes fell further, one of them by %s. A town '
                'that loses a quarter of its pupils and holds its spending flat shows a '
                'large rise in spending PER PUPIL without spending another dollar.'
                % (pct(L['totalcagr'], 1), BASE_SY, SY,
                   pct(min(frame[t]['totalcagr'] for t in tw), 1),
                   pct(max(frame[t]['totalcagr'] for t in tw), 1), len(tw),
                   ordinal(g_rank), len(group), pct(abs(L['enrchg']), 1),
                   len(lost_more), len(tw),
                   pct(abs(min(frame[t]['enrchg'] for t in tw)), 1))),
            figures={
                'total_cagr': figure(L['totalcagr'], pct(L['totalcagr'], 1),
                                     'a year growth in Lunenburg’s TOTAL school '
                                     'spending since SY%d — the middle of its ten '
                                     'look-alike towns' % BASE_SY),
                'g_rank': figure(g_rank, ordinal(g_rank)),
                'group': figure(len(group), str(len(group))),
                'lo': figure(min(frame[t]['totalcagr'] for t in tw),
                             pct(min(frame[t]['totalcagr'] for t in tw), 1)),
                'hi': figure(max(frame[t]['totalcagr'] for t in tw),
                             pct(max(frame[t]['totalcagr'] for t in tw), 1)),
                'tw': figure(len(tw), str(len(tw))),
                'enr': figure(abs(L['enrchg']), pct(abs(L['enrchg']), 1)),
                'lost_more': figure(len(lost_more), str(len(lost_more))),
                'worst': figure(abs(min(frame[t]['enrchg'] for t in tw)),
                                pct(abs(min(frame[t]['enrchg'] for t in tw)), 1)),
                'base_sy': figure(BASE_SY, 'SY%d' % BASE_SY),
                'sy': figure(SY, 'SY%d' % SY),
            },
            figure='total_cagr',
            kind='measured',
            bearing='sizes',
            basis=('DESE per-pupil total expenditures multiplied by total FTE pupils, SY%d '
                   'and SY%d, per district; compound annual rate over %d years.'
                   % (BASE_SY, SY, SY - BASE_SY)),
            not_shown=(
                'Why Lunenburg held its enrolment while these towns did not — births, '
                'housing turnover, school choice and who gets counted all move that number '
                'and none is separated here. Total spending is also all funds, so part of '
                'the growth is state aid and grants rather than anything the town levied.'),
            so_what=('It kept its pupils. The look-alikes lost up to %s, which lifts '
                     'per-pupil without spending more.'
                     % pct(abs(min(frame[t]['enrchg'] for t in tw)), 1)),
            see=[('/analysis/enrollment', 'Who is in the schools')]),

        conclusion(
            id='look-alikes-are-not-act-alikes',
            claim='Not one of the %d towns that most resemble Lunenburg also behaves most like it.'
                  % len(twins_is),
            detail=(
                'Two lists were built from the same %d towns. The first is the %d closest on '
                'what a town IS — its children, their needs, its houses, its incomes, '
                'its business base. The second is the %d closest on what a town DOES — '
                'the size of the tax bill, the bill as a share of what people earn, spending '
                'per pupil, how many override questions it has put to voters and won, and '
                'the trend in each. The two lists have no town in common. Widen each to 25 '
                'and %d towns appear on both. The nearest on what it IS is %s; the nearest '
                'on what it DOES is %s.'
                % (len(frame), len(twins_is), len(twins_does), len(overlap25),
                   twins_is[0]['town'], twins_does[0]['town'])),
            figures={
                'overlap': figure(len(overlap10), 'Not one',
                                  'of the %d towns that most RESEMBLE Lunenburg is also one '
                                  'of the %d that BEHAVE most like it'
                                  % (len(twins_is), len(twins_does))),
                'ten': figure(len(twins_is), str(len(twins_is))),
                'ten2': figure(len(twins_does), str(len(twins_does))),
                'wide': figure(len(overlap25), str(len(overlap25))),
                'twentyfive': figure(25, '25'),
                'n': figure(len(frame), str(len(frame))),
            },
            figure='overlap',
            kind='measured',
            bearing='sizes',
            basis=('Both lists computed over the same %d-town frame; the two closest-%d '
                   'lists intersected, then the two closest-25 lists.'
                   % (len(frame), len(twins_is))),
            not_shown=(
                'That either list is the right one. A distance is a statement about the '
                'measures chosen, given equal weight, and a different weighting gives '
                'different towns. What the empty overlap does establish is that "a town like '
                'ours" has no single answer — so anybody citing one should say which '
                'kind they mean.'),
            so_what=('Who counts as “a town like ours” depends entirely on which '
                     'question you ask.')),

        conclusion(
            id='an-override-stays-in-the-bill',
            claim='Towns that have won %d or more overrides average a %s tax bill; towns with none, %s.'
                  % (E['win_cut'], usd(E['bill_many']), usd(E['bill_none'])),
            detail=(
                'Of the %d towns here, %d have never won a Proposition 2½ override and '
                'their average single-family bill is %s. The %d that have won %d or more '
                'average %s. Lunenburg has put %d questions to its voters since %s and won '
                '%d, raising %s of permanent levy capacity. An override is not a one-year '
                'charge: it lifts the ceiling on what the town may levy for good, and that '
                'ceiling then grows 2.5%% a year from wherever it was left. That is what the '
                'statute does, and it is why a vote taken decades ago is still inside '
                'today’s bill.'
                % (len(frame), E['n_none'], usd(E['bill_none']), E['n_many'], E['win_cut'],
                   usd(E['bill_many']), L['put'], since, L['won'], usd(L['won_amt']))),
            figures={
                'bill_many': figure(E['bill_many'], usd(E['bill_many']),
                                    'the average single-family tax bill in towns that have '
                                    'won %d or more overrides — against %s where none '
                                    'has ever passed' % (E['win_cut'], usd(E['bill_none']))),
                'bill_none': figure(E['bill_none'], usd(E['bill_none'])),
                'win_cut': figure(E['win_cut'], str(E['win_cut'])),
                'n_none': figure(E['n_none'], str(E['n_none'])),
                'n_many': figure(E['n_many'], str(E['n_many'])),
                'put': figure(L['put'], str(L['put'])),
                'won': figure(L['won'], str(L['won'])),
                'won_amt': figure(L['won_amt'], usd(L['won_amt'])),
                'n': figure(len(frame), str(len(frame))),
                'since': figure(int(since[2:]), since),
            },
            figure='bill_many',
            kind='measured',
            bearing='sizes',
            allow=('2.5', '2'),
            basis=('dls-override-votes.csv, wins per town, grouped against the FY%d average '
                   'single-family bill in dls-avg-tax-bill.csv over the %d-town frame.'
                   % (FY, len(frame))),
            not_shown=(
                'WHICH CAUSES WHICH, and here it matters more than anywhere else on this '
                'page. A town with a higher bill may pass overrides because its residents '
                'can afford them, rather than having a higher bill because it passed them — '
                'and wealth would produce both. The gap is equally consistent with either '
                'reading. Nor does winning an amount mean the town levied it: an override '
                'raises the ceiling, and a town may sit below its own limit.'),
            so_what=('An override lifts the levy ceiling for good, so a vote from decades ago '
                     'is still in the bill.'),
            see=[('/analysis/fy27-and-the-override', 'The FY27 override')]),

        conclusion(
            id='where-the-children-actually-go',
            claim='Only %d of %d children schooled outside Lunenburg attend a school one town funds.'
                  % (by_kind.get('one-town', 0), left),
            detail=(
                'In FY%d, %s children living in Lunenburg were enrolled somewhere other than '
                'Lunenburg’s own schools, out of %s in all. %d of them are at '
                'Montachusett Regional Vocational Technical, which Lunenburg is a member '
                'town of and pays an assessment to — so those children have not left '
                'the town’s bill, they are on a different line of it. %d are at charter '
                'or state-run online schools, which no single town funds. %d are in regional '
                'districts whose cost is split across member towns with different tax bills. '
                'That leaves %d at schools one town’s taxpayers pay for — the only '
                'ones where a tax bill can honestly be set beside a per-pupil figure.'
                % (FY, '{:,}'.format(left), '{:,}'.format(sum(by_kind.values())),
                   by_kind.get('assessed', 0), by_kind.get('no-town', 0),
                   by_kind.get('regional', 0), by_kind.get('one-town', 0))),
            figures={
                'one_town': figure(by_kind.get('one-town', 0),
                                   '%d of %d' % (by_kind.get('one-town', 0), left),
                                   'children schooled outside Lunenburg whose school is paid '
                                   'for by one town’s taxpayers'),
                'one_town_n': figure(by_kind.get('one-town', 0),
                                     str(by_kind.get('one-town', 0))),
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
                'assessment or a share of a regional assessment — and nothing here says '
                'which fund pays. Nor why a family chose a school: the file records an '
                'enrolment and nothing else.'),
            so_what=('%d are at Monty Tech, which Lunenburg pays into; %d at charter or '
                     'online schools.' % (by_kind.get('assessed', 0),
                                          by_kind.get('no-town', 0))),
            see=[('/analysis/monty-tech', 'The Monty Tech assessment'),
                 ('/analysis/per-pupil-spending', 'What the destinations spend')]),

        conclusion(
            id='the-neighbours-vote-nothing-alike',
            claim='%s has asked its voters for an override %d times and won %d. Lunenburg: %d and %d.'
                  % (loudest, ov_put[loudest], ov_won[loudest], ov_put['Lunenburg'],
                     ov_won['Lunenburg']),
            detail=(
                'Across the six towns that share a border with Lunenburg, the number of '
                'Proposition 2½ questions put to voters since %s runs from %d to %d. %s '
                'is the highest, with %d questions and %d wins; %s. Lunenburg has put %d and '
                'won %d. These towns are next to each other, their school costs move with '
                'the same contracts and the same state aid formula, and how often they ask '
                'their voters for more differs by a factor of %s.'
                % (since, min(ov_put[t] for t in sets['neighbours']),
                   max(ov_put[t] for t in sets['neighbours']), loudest, ov_put[loudest],
                   ov_won[loudest],
                   ('%s has never asked once' % silent[0]) if silent
                   else 'the lowest is %d' % min(ov_put[t] for t in sets['neighbours']),
                   ov_put['Lunenburg'], ov_won['Lunenburg'],
                   '%.0f' % (ov_put[loudest] / max(1, ov_put['Lunenburg'])))),
            figures={
                'loud_put': figure(ov_put[loudest], str(ov_put[loudest]),
                                   'override questions %s has put to its voters since %s, of '
                                   'which %d passed — Lunenburg has put %d and passed %d'
                                   % (loudest, since, ov_won[loudest], ov_put['Lunenburg'],
                                      ov_won['Lunenburg'])),
                'loud_won': figure(ov_won[loudest], str(ov_won[loudest])),
                'lun_put': figure(ov_put['Lunenburg'], str(ov_put['Lunenburg'])),
                'lun_won': figure(ov_won['Lunenburg'], str(ov_won['Lunenburg'])),
                'lo': figure(min(ov_put[t] for t in sets['neighbours']),
                             str(min(ov_put[t] for t in sets['neighbours']))),
                'hi': figure(max(ov_put[t] for t in sets['neighbours']),
                             str(max(ov_put[t] for t in sets['neighbours']))),
                'factor': figure(ov_put[loudest] / max(1, ov_put['Lunenburg']),
                                 '%.0f' % (ov_put[loudest] / max(1, ov_put['Lunenburg']))),
                'since': figure(int(since[2:]), since),
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
                'it may have cut instead, or used a debt exclusion, which sits outside the '
                'levy limit and is not in this file at all.'),
            so_what=('%s Neighbours under the same costs behave completely differently.'
                     % (('%s has never asked once.' % silent[0]) if silent else '')),
            see=[('/analysis/fy27-and-the-override', 'The FY27 override')]),
    ]
    return emit(REPORT, rows_out)


# WHAT EACH COMPARISON TOWN ACTUALLY MEANS FOR A LUNENBURG HOUSEHOLD.
#
# TJ, 26 September 2026: *"i think we need more statements citizens can understand. like,
# which towns look most like us. name them. explain how they are similar and different...
# do they pay more or less than us in property taxes? Do they pay more or less for per
# pupil? give the citizens the words to use when talking to their friends."* And then:
# *"conclusions for the other districts... are they better off, tax payers but not
# students, students but not tax payers, etc"*
#
# TWO AXES, FOUR QUADRANTS, and the names are DESCRIPTIONS rather than verdicts. "Better
# off" is a value judgement -- a town that spends less per child may be run leanly or may be
# short-changing its schools, and this file cannot tell those apart (rule 8: the job is
# helping somebody understand what would work, not scoring anybody). So the label says what
# the two numbers DO, and the reader decides what that is worth:
#
#                      spends MORE per pupil        spends LESS per pupil
#   bill LOWER    "Pays less, spends more"      "Pays less, spends less"
#   bill HIGHER   "Pays more, spends more"      "Pays more, spends less"
#
# AND THE SENTENCE IS GENERATED, never written per town (rule 2). A hand-written line about
# Douglas would go stale the day DESE publishes another year, in a paragraph nothing
# recomputes -- which is this project's oldest defect shape.

QUADRANTS = {
    (True, True): ('pays-less-spends-more', 'Pays less, spends more'),
    (False, True): ('pays-more-spends-more', 'Pays more, spends more'),
    (True, False): ('pays-less-spends-less', 'Pays less, spends less'),
    (False, False): ('pays-more-spends-less', 'Pays more, spends less'),
}

# A DIFFERENCE TOO SMALL TO SAY OUT LOUD IS NOT A DIFFERENCE. Below these, the sentence says
# "about the same" rather than naming a figure a reader would take as meaningful: $250 is
# under a fortnight's difference on a tax bill, and $500 per pupil is under 3% of Lunenburg's
# own figure. Both are stated here rather than buried, because a threshold chosen silently
# is a judgement nobody can argue with.
SAME_BILL = 250
SAME_PP = 500
# The same idea for the two explanations offered below the headline.
MORE_HOMES = 0.25          # homes per pupil
MORE_STATE = 5.0           # percentage points of the foundation budget


def _business_within_band(frame, towns, lo=400000, hi=650000):
    """What a bigger business base buys, among towns whose houses are worth about the same.

    The raw correlation between commercial share and the tax bill is -0.38, and it is
    dominated by house prices: the towns with almost no business are the expensive
    residential ones. Holding the average home inside a band around Lunenburg's removes most
    of that, and what is left is the honest size of the commercial argument."""
    band = [t for t in towns if lo <= frame[t]['value'] <= hi]
    if len(band) < 20:
        return None
    med = st.median(frame[t]['cip'] for t in band)
    more = [t for t in band if frame[t]['cip'] >= med]
    less = [t for t in band if frame[t]['cip'] < med]
    return dict(
        lo=lo, hi=hi, n=len(band), cut=round(med, 1),
        n_more=len(more), n_less=len(less),
        bill_more=round(st.mean(frame[t]['bill'] for t in more)),
        bill_less=round(st.mean(frame[t]['bill'] for t in less)),
        pp_more=round(st.mean(frame[t]['pp'] for t in more)),
        pp_less=round(st.mean(frame[t]['pp'] for t in less)))


def distributions(frame, val, effort, parcels):
    """EVERY MEASURE ON ITS OWN AXIS, with all 161 towns on it and Lunenburg marked.

    TJ: *"probably separate charts for each thing independently. Put lunenburg on a chart on
    all these different axes to view independently... All different independent charts to see
    visually?"*

    WHY A STRIP OF EVERY TOWN RATHER THAN A BAR OF A FEW. A bar chart of twelve towns answers
    `how do we compare with these twelve`, which is the question the reader brought and not
    the one that settles anything — twelve towns can be chosen to say almost anything. A
    strip showing all 161 puts the comparison towns INSIDE the distribution they came from, so
    a reader sees at once whether Lunenburg is unusual or ordinary, and how wide the spread
    is. Where a town sits is a fact; whether that position is remarkable needs the spread.

    Each row carries every value, so the chart can draw the whole distribution and the page
    can state a rank without either being computed twice."""
    L = 'Lunenburg'
    towns = [t for t in sorted(frame) if t in val and t in effort and t in parcels]
    specs = [
        ('pupils', 'Pupils in the district', lambda t: frame[t]['fte'],
         'count', 'full-time-equivalent pupils, SY%d' % SY),
        ('per_pupil', 'Spent per pupil', lambda t: frame[t]['pp'],
         'usd', 'all funds, SY%d' % SY),
        ('above', 'Spent above what the state says its schools need',
         lambda t: frame[t]['pp'] / effort[t]['foundation_pp'],
         'ratio', 'actual spending as a multiple of the town’s foundation budget'),
        ('bill', 'Average tax bill on a single-family home', lambda t: frame[t]['bill'],
         'usd', 'FY%d' % FY),
        ('bill_income', 'That bill as a share of income per head',
         lambda t: frame[t]['pinc'], 'pct', 'FY%d' % FY),
        ('value_pp', 'Taxable value behind each pupil',
         lambda t: val[t]['total'] / frame[t]['fte'], 'usd',
         'all property, FY%d, over SY%d pupils' % (FY, SY)),
        ('business_share', 'Share of the tax base that is business',
         lambda t: 100.0 * val[t]['business'] / val[t]['total'], 'pct', 'FY%d' % FY),
        ('business_pp', 'Business value behind each pupil',
         lambda t: val[t]['business'] / frame[t]['fte'], 'usd', 'FY%d' % FY),
        ('state_pp', 'State money per child', lambda t: effort[t]['state_pp'],
         'usd', 'foundation budget less the required local contribution, FY%d' % FY),
        ('required_pp', 'What the town must raise per child',
         lambda t: effort[t]['required_pp'], 'usd',
         'required local contribution, FY%d — a floor, not a ceiling' % FY),
        ('low_income', 'Share of children from low-income families',
         lambda t: frame[t]['lowinc'], 'pct', 'SY%d' % SY),
        ('enrolment', 'Change in pupils since SY%d' % BASE_SY,
         lambda t: frame[t]['enrchg'], 'pctdiff', 'full-time-equivalent'),
    ]
    out = []
    for key, label, f, kind, note in specs:
        vals = {t: f(t) for t in towns}
        order = sorted(towns, key=lambda t: -vals[t])
        series = sorted(vals.values())
        # EVERY FIGURE ON A ROW IS ROUNDED THE SAME WAY. The first version rounded the list
        # of values and not Lunenburg's own, so a check that recomputed the rank from the
        # published payload disagreed with the published rank on four measures -- near-ties
        # that rounding moved. A payload that cannot reproduce its own rank is exactly the
        # derived-figure-drifting-from-its-source defect this project keeps finding.
        r3 = lambda v: round(v, 3)
        out.append(dict(
            key=key, label=label, kind=kind, note=note,
            n=len(towns),
            lunenburg=r3(vals[L]),
            rank=order.index(L) + 1,
            median=r3(st.median(series)), lo=r3(series[0]), hi=r3(series[-1]),
            p25=r3(series[len(series) // 4]), p75=r3(series[3 * len(series) // 4]),
            values=[r3(v) for v in series],
            marks=[dict(town=t, value=round(vals[t], 3))
                   for t in ['Lunenburg'] + [x for x in NEIGHBOURS + PEERS if x in vals]]))
    return out


def _row(pr, key):
    return next(d for d in pr['single'] if d['key'] == key)


def _rv(pr, key):
    return _row(pr, key)['r']


def _rt(pr, key):
    return '%+.2f' % _row(pr, key)['r']


def _re(pr, key):
    return _row(pr, key)['explains']


def predictors(frame, val, effort):
    """WHAT ACTUALLY PREDICTS HOW MUCH A DISTRICT SPENDS PER PUPIL.

    TJ: *"we need to find the true source of the differentiating revenue for schools with
    the highest spend per pupil. the PREDICTOR of highest spend. is it state money? lowest
    pupils? wealthiest towns? business? What is it"*

    Twelve candidates, each against spending per pupil across every single-town K-12
    district, ranked by how much of the difference between districts each one accounts for.

    AND THE RESIDUAL IS THE FINDING. The strongest single predictor explains under a third.
    Everything here together explains about two fifths. Whatever separates a district
    spending $25,000 a pupil from one spending $18,000, most of it is NOT wealth, aid, size,
    poverty or tax base -- all of which are in the model.

    WHAT THIS IS NOT. A correlation across towns in one year, which cannot say which way
    anything runs and cannot rule out a cause nobody measured. The unexplained share is not
    evidence of choice; it is the ABSENCE of evidence for the four explanations people reach
    for, which is a weaker and more useful thing. Special education caseload, debt service,
    contract history and regional structure are all candidates this report does not hold."""
    T = [t for t in sorted(frame) if t in effort and t in val]
    y = [frame[t]['pp'] for t in T]

    def r(xs, ys):
        mx, my = st.mean(xs), st.mean(ys)
        num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
        den = math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
        return num / den if den else 0.0

    cands = [
        ('value_pp', 'How much taxable property stands behind each pupil',
         lambda t: val[t]['total'] / frame[t]['fte']),
        ('home_value', 'What the average home is worth', lambda t: frame[t]['value']),
        ('business_pp', 'Business value behind each pupil',
         lambda t: val[t]['business'] / frame[t]['fte']),
        ('income', 'Income per head', lambda t: frame[t]['income']),
        ('bill', 'The average tax bill', lambda t: frame[t]['bill']),
        ('required_pp', 'What the state requires the town to raise per child',
         lambda t: effort[t]['required_pp']),
        ('enrolment', 'Change in pupils since SY%d' % BASE_SY,
         lambda t: frame[t]['enrchg']),
        ('state_pp', 'How much the state sends per child',
         lambda t: effort[t]['state_pp']),
        ('business_share', 'How much of the tax base is business',
         lambda t: frame[t]['cip']),
        ('low_income', 'The share of children from low-income families',
         lambda t: frame[t]['lowinc']),
        ('size', 'How many pupils the district has (log)',
         lambda t: math.log(frame[t]['fte'])),
        ('overrides', 'How many overrides the town has won', lambda t: frame[t]['won']),
    ]
    out = []
    for key, label, f in cands:
        rr = r([f(t) for t in T], y)
        out.append(dict(key=key, label=label, r=round(rr, 3),
                        explains=round(100 * rr * rr, 1)))
    out.sort(key=lambda d: -abs(d['r']))

    # ...AND ALL OF THEM AT ONCE. Standardised least squares over the five that are not
    # near-duplicates of each other, solved by elimination so this needs no dependency.
    keys = ['value_pp', 'state_pp', 'size', 'low_income', 'enrolment']
    fns = {k: f for k, _, f in cands}

    def z(v):
        m, s = st.mean(v), st.pstdev(v)
        return [(x - m) / s for x in v] if s else [0.0] * len(v)

    X = [z([fns[k](t) for t in T]) for k in keys]
    yz = z(y)
    n, k = len(T), len(keys)
    A = [[sum(X[i][p] * X[j][p] for p in range(n)) for j in range(k)] for i in range(k)]
    b = [sum(X[i][p] * yz[p] for p in range(n)) for i in range(k)]
    for i in range(k):
        piv = A[i][i]
        for j in range(i, k):
            A[i][j] /= piv
        b[i] /= piv
        for m2 in range(k):
            if m2 != i:
                fct = A[m2][i]
                for j in range(i, k):
                    A[m2][j] -= fct * A[i][j]
                b[m2] -= fct * b[i]
    fit = [sum(b[i] * X[i][p] for i in range(k)) for p in range(n)]
    return dict(
        n=len(T), single=out,
        together=[dict(key=kk, label=next(l for k2, l, _ in cands if k2 == kk),
                       weight=round(bb, 2))
                  for kk, bb in sorted(zip(keys, b), key=lambda x: -abs(x[1]))],
        explained_together=round(100 * r(fit, yz) ** 2, 1),
        best=out[0]['key'], best_explains=out[0]['explains'],
        unexplained=round(100 - 100 * r(fit, yz) ** 2, 1))


# THE REGIONAL DISTRICTS LUNENBURG’S NEIGHBOURS BELONG TO, and their member towns.
#
# Not derivable from anything in this archive: DESE publishes a district and a municipality
# and never the membership between them. These four are read off the districts’ own names
# and their towns’ annual reports, and they are the ones this report needs because
# Lunenburg’s six neighbours sit in them. A fifth — Nashoba — is deliberately
# absent: Lancaster belongs to it, and its other members are not stated in anything held
# here, so guessing them would be inventing a fact.
REGIONAL_MEMBERS = {
    'NORTH MIDDLESEX': ['Ashby', 'Pepperell', 'Townsend'],
    'GROTON DUNSTABLE': ['Groton', 'Dunstable'],
    'AYER SHIRLEY': ['Ayer', 'Shirley'],
    'ASHBURNHAM WESTMINSTER': ['Ashburnham', 'Westminster'],
}


def regional_members():
    """WHAT EACH MEMBER TOWN OF A REGIONAL DISTRICT PUTS IN, per child.

    TJ: *"If 3 TOWNS all go to the same regional school, are we able to show what each town
    is contributing per pupil? how does that work"*

    YES FOR THE FORMULA, NO FOR THE ASSESSMENT, and the difference matters. Chapter 70 is
    computed per MUNICIPALITY, so what each member town is required to raise per child and
    what the state adds per child are published separately for Ashby, Pepperell and Townsend
    even though their children share one school system. What is NOT published anywhere
    statewide is the ASSESSMENT — what each town actually votes to pay the district —
    which is set by the regional agreement and voted town meeting by town meeting.

    AND THE TOWN FIGURES DO NOT SUM TO THE DISTRICT, WHICH IS THE INTERESTING PART. Adding
    the member towns gives 104% to 115% of the district’s own required contribution,
    because a town’s Chapter 70 figures cover ALL of that town’s children —
    including the ones at a vocational school, a charter, or another district by school
    choice — while the district’s figures cover only the children it teaches. The
    proof that this is the explanation and not an error: within each district the required
    and the foundation ratios are the SAME number to a tenth of a point, which is what
    happens when both are scaled by one thing, the share of children who attend.
    """
    ch = {r['municipality']: r for r in rows(CH70) if r['fy'] == str(FY)}
    form = {r['district']: r for r in rows(NSS) if r['fy'] == str(FY)}
    out = []
    for dist, members in sorted(REGIONAL_MEMBERS.items()):
        d = form.get(dist)
        if not d:
            continue
        req_d = num(d['required_local_contribution'])
        fnd_d = num(d['foundation_budget'])
        towns_ = []
        for m in members:
            r = ch.get(m)
            if not r:
                continue
            en = num(r['town_foundation_enrollment'])
            rq = num(r['required_local_contribution'])
            fb = num(r['town_foundation_budget'])
            if not en or not rq or not fb:
                continue
            towns_.append(dict(town=m, children=round(en),
                               required_pp=round(rq / en), state_pp=round((fb - rq) / en),
                               required=round(rq), foundation=round(fb)))
        if not towns_ or not req_d or not fnd_d:
            continue
        sum_req = sum(t['required'] for t in towns_)
        sum_fnd = sum(t['foundation'] for t in towns_)
        out.append(dict(
            district=dist.title(), members=towns_,
            district_required=round(req_d), district_foundation=round(fnd_d),
            towns_required=sum_req, towns_foundation=sum_fnd,
            required_ratio=round(100 * sum_req / req_d, 1),
            foundation_ratio=round(100 * sum_fnd / fnd_d, 1)))
    # THE IDENTITY THAT PROVES THE READING. Both ratios are the same scaling, so they must
    # agree; if they ever stop, the explanation above is wrong and this refuses to publish it.
    for r in out:
        if abs(r['required_ratio'] - r['foundation_ratio']) > 0.6:
            raise SystemExit('%s: required ratio %.1f%% but foundation ratio %.1f%% — the '
                             'member towns do not scale to the district by one factor, so the '
                             'explanation in regional_members() does not hold'
                             % (r['district'], r['required_ratio'], r['foundation_ratio']))
    return out


def regional_picture(frame, dese):
    """DOES REGIONALISING SAVE MONEY? The claim, tested on what it actually claims.

    TJ: *"YES we absolutely need regional districts called out. everyone says thats the
    solution. going regionalized"*

    The argument is about shared overhead, so the measure is ADMINISTRATION per pupil, which
    DESE publishes as its own category. This compares every single-town district with every
    regional one, and separately asks whether SIZE reduces administration — because that
    is the mechanism the argument actually proposes, and a district can get bigger without
    regionalising."""
    now = dese.get(str(SY), {})
    EX = ('Charter', 'Virtual', 'Academy', 'Collaborative', 'Agricultural', '(District)')
    k12 = k12_districts()
    rows_ = []
    for name, m in now.items():
        if name not in k12 or any(x in name for x in EX):
            continue
        adm = m.get(('Expenditures Per Pupil', 'Administration'))
        lead = m.get(('Expenditures Per Pupil', 'Instructional Leadership')) or 0
        tot = m.get(('Expenditures Per Pupil', 'Total Expenditures'))
        fte = m.get(('Student Enrollment', 'Total FTE Pupils'))
        if adm and tot and fte:
            rows_.append(dict(district=name, regional=name not in frame,
                              pupils=fte, admin=adm, overhead=adm + lead, total=tot))
    if len(rows_) < 100:
        raise SystemExit('only %d districts for the regional comparison' % len(rows_))
    single = [r for r in rows_ if not r['regional']]
    reg = [r for r in rows_ if r['regional']]
    by_size = sorted(rows_, key=lambda r: r['pupils'])
    q = len(by_size) // 4
    lun = next(r for r in rows_ if r['district'] == 'Lunenburg')
    order = sorted(rows_, key=lambda r: -r['admin'])
    return dict(
        n=len(rows_), n_single=len(single), n_regional=len(reg),
        admin_single=round(st.median(r['admin'] for r in single)),
        admin_regional=round(st.median(r['admin'] for r in reg)),
        overhead_single=round(st.median(r['overhead'] for r in single)),
        overhead_regional=round(st.median(r['overhead'] for r in reg)),
        total_single=round(st.median(r['total'] for r in single)),
        total_regional=round(st.median(r['total'] for r in reg)),
        small_pupils=round(st.median(r['pupils'] for r in by_size[:q])),
        small_admin=round(st.median(r['admin'] for r in by_size[:q])),
        big_pupils=round(st.median(r['pupils'] for r in by_size[-q:])),
        big_admin=round(st.median(r['admin'] for r in by_size[-q:])),
        lun_admin=round(lun['admin']), lun_overhead=round(lun['overhead']),
        lun_rank=order.index(lun) + 1)


def cherry_sheet(dese):
    """THE STATE AID A TOWN CANNOT GET UNLESS IT IS REGIONAL, and what Lunenburg does get.

    TJ, on the argument this town keeps having: *"transportation is the big one. are regional
    schools saving or paying for transportation? The argument is, transportation funding is a
    LOT for regional schools, earning a lot from the state."*

    HE WAS RIGHT AND THIS REPORT WAS WRONG TO CLOSE THE QUESTION. An earlier version tested
    regionalising on ADMINISTRATION, found no saving, and concluded the argument had nothing
    behind it -- while saying, correctly, that the transport mechanism could not be measured.
    It can now: `Regional Transportation` is a CHERRY SHEET line under M.G.L. c.71 s.16C, paid
    to regional school districts and to nobody else, and it is $88.2M statewide in FY%d.

    A finding of no effect on the measure you COULD take is not a finding of no effect. The
    conclusion has been narrowed to what was actually tested.

    THE SAME FILE ANSWERS THE OTHER OPEN QUESTION. School choice tuition RECEIVED is a cherry
    sheet receipt and a revolving fund at the district -- which is part of why some districts
    charge so much more of their teaching to grants and revolving accounts. Lunenburg receives
    little of it and pays a great deal out, both of which are here.""" % FY
    rows_ = [r for r in rows(CHERRY) if r['fy'] == str(FY)]
    if not rows_:
        raise SystemExit('no FY%d cherry sheet rows' % FY)
    ROLLUPS = ('Total Receipts', 'Net Receipts', 'Total Assessments')

    def pick(population, flow, line):
        return {r['name']: num(r['amount']) for r in rows_
                if r['population'] == population and r['flow'] == flow and r['line'] == line}

    transport = pick('Regional Schools', 'Receipts', 'Regional Transportation')
    now = dese.get(str(SY), {})
    local = []
    for name, amt in transport.items():
        if not amt:
            continue
        # The cherry sheet spells a district without its hyphen; DESE keeps it.
        key = ' '.join(name.upper().replace('-', ' ').split())
        match = next((d for d in now
                      if ' '.join(d.upper().replace('-', ' ').split()).startswith(key)), None)
        fte = now.get(match, {}).get(('Student Enrollment', 'Total FTE Pupils')) if match else None
        local.append(dict(district=name, amount=round(amt),
                          pupils=round(fte) if fte else None,
                          per_pupil=round(amt / fte) if fte else None))
    local.sort(key=lambda r: -(r['per_pupil'] or 0))

    lun = {}
    for flow in ('Receipts', 'Assessments'):
        lun[flow] = sorted(
            [dict(line=r['line'], amount=round(num(r['amount'])))
             for r in rows_
             if r['population'] == 'Municipalities' and r['name'] == 'Lunenburg'
             and r['flow'] == flow and r['line'] not in ROLLUPS
             and abs(num(r['amount']) or 0) > 0],
            key=lambda x: -abs(x['amount']))
    totals = {}
    for line in ROLLUPS:
        for flow in ('Receipts', 'Assessments'):
            v = pick('Municipalities', flow, line).get('Lunenburg')
            if v:
                totals[line] = round(v)
    statewide = sum(v for v in transport.values() if v)
    return dict(
        fy=FY, statewide_transport=round(statewide),
        n_regional=len([v for v in transport.values() if v]),
        local=[r for r in local if r['per_pupil']][:8],
        lunenburg=lun, totals=totals,
        lun_choice_in=round(pick('Municipalities', 'Receipts',
                                 'Sch Choice Rcvng Tuition').get('Lunenburg') or 0),
        lun_choice_out=round(pick('Municipalities', 'Assessments',
                                  'School Ch Sending Tuition').get('Lunenburg') or 0),
        lun_charter_out=round(pick('Municipalities', 'Assessments',
                                   'Chart Sch Sending Tuition').get('Lunenburg') or 0))


def outside_the_appropriation(dese):
    """WHAT THE MONEY OUTSIDE THE SCHOOL APPROPRIATION ACTUALLY IS, and who gets more of it.

    TJ, on being shown that Lunenburg draws less from outside its school budget than any
    district it can be compared with: *"woah yea looks like we need to answer ‘Everything
    else’ then! That’s a HUGE discrepancy. I dont even understand what the sources
    could be"*

    IT IS GRANTS AND REVOLVING FUNDS, and it is published. DESE’s function-code file
    reports every district’s spending split two ways at once -- by what it BUYS and by
    which fund paid: `gen_fund` against `grants_revolving`. That answers the question
    directly, and it reconciles: Lunenburg’s grants and revolving come to $3.04M against
    the $2.95M this report derives a different way, as all-funds spending less net school
    spending. Two files, two routes, the same answer.

    A REVOLVING FUND IS NOT A GRANT and the file does not separate them, which matters. A
    grant is money won from outside; a revolving fund is money the district itself takes in
    and may spend without appropriation -- athletics fees, school choice tuition RECEIVED,
    preschool tuition, food service, rentals. A district with a large school-choice intake
    looks the same here as one that writes successful grant applications, and the two are
    not the same opportunity.

    WHAT IT CANNOT SAY, and it is the question the numbers raise: WHICH fund. Harvard charges
    $4,964 a pupil of TEACHER salaries to grants and revolving where Lunenburg charges $726,
    and nothing in this file names the account. That is registered in money-gaps, with
    DESE’s End of Year Pupil and Financial Report as the document that would settle it.
    """
    rows_ = [r for r in rows(FUNC) if r['fy'] == str(SY)]
    if not rows_:
        raise SystemExit('no FY%d rows in %s' % (SY, os.path.relpath(FUNC, ROOT)))
    now = dese.get(str(SY), {})
    # The categories NEST -- `Expenditure (Admin, Instruction, ...)` is the parent of several
    # others -- so summing the file would count the same dollar four times. Only the parent
    # row is taken for the totals, and the children are read individually for the breakdown.
    out = []
    for dist in sorted({r['district'] for r in rows_}):
        top = [r for r in rows_ if r['district'] == dist
               and r['func_cat_desc'].startswith('Expenditure (')]
        m = now.get(dist, {})
        fte = m.get(('Student Enrollment', 'Total FTE Pupils'))
        if not top or not fte:
            continue
        gen = sum(num(r['gen_fund']) or 0 for r in top)
        gr = sum(num(r['grants_revolving']) or 0 for r in top)
        if gen + gr <= 0:
            continue
        parts = {}
        for cat in ('Teachers', 'Pupil Services', 'Other Teaching Services',
                    'Payments to Out-of-District Schools', 'Operations and Maintenance',
                    'Instructional Materials, Equipment and Technology',
                    'Professional Development', 'Administration'):
            v = sum(num(r['grants_revolving']) or 0 for r in rows_
                    if r['district'] == dist and r['func_cat_desc'] == cat)
            parts[cat] = round(v / fte)
        out.append(dict(
            district=dist, pupils=round(fte),
            general=round(gen), grants_revolving=round(gr),
            per_pupil=round(gr / fte), share=round(100.0 * gr / (gen + gr), 1),
            parts=parts))
    out.sort(key=lambda r: -r['per_pupil'])
    return out


def above_the_requirement(frame, dese=None):
    """WHERE THE MONEY ABOVE THE STATE’S FIGURE ACTUALLY COMES FROM.

    TJ, reading the funding chart: *"harvard. 10k from homes. 400 from business. 2500 from
    state. but still 12000 above state recommendations?! i guess my question is, where does
    the money come from for all of the ‘above state recommendations’?"*

    THE CHART COULD NOT ANSWER IT AND SHOULD NOT HAVE IMPLIED IT COULD. Its first three
    segments are the state’s formula — what a town is REQUIRED to raise and what the
    state adds — not what homes and businesses actually pay. A town appropriates well
    above its requirement, and that money is in the fourth segment with everything else.

    This splits the fourth segment where DESE publishes the pieces:

        actual net school spending − required net school spending
            = local money appropriated ABOVE what the state requires
        all-funds spending − actual net school spending
            = money that never goes through the school appropriation at all
              (grants, circuit breaker, transport, food service, capital, revolving funds)

    WHY ONLY A FEW DISTRICTS. Actual net school spending is published statewide only through
    SY2022 — DESE’s own API confirms it — and this project holds the FY2026
    district profile for Lunenburg and its immediate neighbours. So the split is exact and
    current for those, and absent elsewhere, which is said rather than filled in.

    AND THE SECOND PIECE CANNOT BE SPLIT FURTHER HERE. What share of it is a grant, the
    circuit breaker, or capital needs DESE’s End of Year Financial Report, which is
    already the named remedy on the money-gaps row about funding sources."""
    # THE REGIONAL DISTRICTS BELONG HERE, and in this town they are the argument. TJ:
    # *"YES we absolutely need regional districts called out. everyone says thats the
    # solution. going regionalized"* -- so a comparison that quietly dropped four of the six
    # districts it holds current figures for, because they happen to serve several towns,
    # was dropping exactly the ones the argument is about.
    #
    # DESE names a district differently in its two files -- `GROTON DUNSTABLE` in the
    # Chapter 70 workbook, `Groton-Dunstable` in the indicators -- so the join normalises
    # case, hyphens and spacing rather than hoping. `Ayer Shirley` is published as `Ayer
    # Shirley School District` and is matched on the longer name.
    def norm(x):
        return ' '.join(x.upper().replace('-', ' ').replace('  ', ' ').split())
    pool = dict((dese or {}).get(str(SY), {}))
    known = {norm(n): n for n in pool}
    for n in pool:
        known.setdefault(norm(n.replace(' School District', '')), n)
    known.update({norm(n): n for n in frame})

    def figures(name):
        if name in frame:
            return frame[name]['fte'], frame[name]['pp']
        d = pool.get(name, {})
        return (d.get(('Student Enrollment', 'Total FTE Pupils')),
                d.get(('Expenditures Per Pupil', 'Total Expenditures')))

    out = []
    for r in rows(NSS):
        if r['fy'] != str(FY):
            continue
        name = known.get(norm(r['district']), r['district'].strip().title())
        req, act = num(r['required_nss']), num(r['net_school_spending'])
        if not req or not act or req <= 0:
            continue
        fte, pp = figures(name)
        if not fte or not pp:
            continue
        allf = pp * fte
        out.append(dict(
            district=name, pupils=round(fte),
            regional=name not in frame,
            all_funds_pp=round(pp),
            required_nss_pp=round(req / fte),
            above_requirement_pp=round((act - req) / fte),
            outside_nss_pp=round((allf - act) / fte),
            multiple=round(act / req, 2)))
    out.sort(key=lambda r: -r['above_requirement_pp'])
    return out


def funding_stack(frame, val, effort, comparison):
    """WHERE EACH TOWN’S SCHOOL MONEY COMES FROM, per pupil, in four published parts.

    TJ: *"one visualization should be: number of pupils is the size of the bar chart. next to
    it, is the spend per pupil. And then the BAR for the spend per pupil is broken down
    by... contributions: citizen taxes, business taxes, state, (other?)"*

    THE DECOMPOSITION IS REAL, AND IT IS NOT THE OBVIOUS ONE. What cannot be done is split
    ACTUAL school spending into tax sources: no town publishes what share of its property
    tax goes to schools, which is rule 11's whole complaint. What CAN be done is split the
    spending against the STATE’S OWN MODEL of it, because every term in that model is
    published per town:

        foundation budget per pupil = what the town must raise + what the state adds
        actual spending per pupil   = foundation budget + whatever the town spends above it

    So three measured parts that sum exactly to what a district spends per pupil. The first
    is then apportioned between homes and business by each town’s own tax base, which is
    ARITHMETIC under a single rate and an approximation under a split one — said on the
    chart rather than buried here.

    The fourth part is the one the report is really about. It is what a town meeting decides,
    and it is where almost all of the difference between these towns lives."""
    L = 'Lunenburg'
    out = []
    for t in comparison:
        if t not in effort or t not in val or t not in frame:
            continue
        e, v, m = effort[t], val[t], frame[t]
        res_share = v['residential'] / v['total']
        biz_share = v['business'] / v['total']
        above = m['pp'] - e['foundation_pp']
        out.append(dict(
            town=t, pupils=round(m['fte']), per_pupil=round(m['pp']),
            from_homes=round(e['required_pp'] * res_share),
            from_business=round(e['required_pp'] * biz_share),
            from_state=round(e['state_pp']),
            above_foundation=round(above),
            required=round(e['required_pp']), foundation=round(e['foundation_pp']),
            state_share=round(e['share'], 1)))
    # THE ORDER IS THE FINDING: sorted by what a town spends above the state's figure, which
    # is the part it decides. Sorting by total per-pupil would put the towns with the most
    # expensive children at the top and say nothing.
    out.sort(key=lambda r: -r['above_foundation'])
    # Every stack must foot to the spending figure it claims to explain.
    for r in out:
        parts = r['from_homes'] + r['from_business'] + r['from_state'] + r['above_foundation']
        if abs(parts - r['per_pupil']) > 3:
            raise SystemExit('%s: the four parts sum to %d, not the %d it spends per pupil'
                             % (r['town'], parts, r['per_pupil']))
    return out


def by_dimension(frame, val, effort, parcels, near=3):
    """WHICH TOWNS ARE LIKE LUNENBURG ON EACH MEASURE, ONE MEASURE AT A TIME.

    TJ, on being told that `a town like ours` has no single answer: *"then we need a
    multi-dimensional answer. 'Based on X, we are similar to Y Z. Based on Y, we are similar
    to A, B, C'"*

    He is right, and the earlier version left a reader worse off than before they asked. Two
    cohorts that do not overlap is a true finding and a useless one on its own: it says the
    question is ill-posed without saying what to ask instead. This does — the nearest
    towns on each measure separately, so somebody arguing about school spending, or about tax
    bills, or about how many children a town has, can reach for the right set instead of one
    set used for everything.

    Nearest is plain absolute difference on the measure itself. No standardising, no
    weighting, nothing to argue with: on `average home value` the three nearest towns are
    simply the three whose average home is closest in dollars to Lunenburg's."""
    L = 'Lunenburg'
    towns = [t for t in sorted(frame) if t in val and t in effort and t in parcels]
    dims = [
        ('children', 'how many children it has',
         lambda t: frame[t]['size'], lambda v: '{:,.0f}'.format(v)),
        ('low_income', 'the share of its children from low-income families',
         lambda t: frame[t]['lowinc'], lambda v: '%.0f%%' % v),
        ('home_value', 'what the average single-family home is worth',
         lambda t: frame[t]['value'], usd),
        ('income', 'income per head',
         lambda t: frame[t]['income'], usd),
        ('business', 'how much business value stands behind each pupil',
         lambda t: val[t]['business'] / frame[t]['fte'], usd),
        ('tax_bill', 'the average single-family tax bill',
         lambda t: frame[t]['bill'], usd),
        ('per_pupil', 'what its schools spend per pupil',
         lambda t: frame[t]['pp'], usd),
        ('above_foundation', 'how far above the state\u2019s figure for its schools it spends',
         lambda t: frame[t]['pp'] / effort[t]['foundation_pp'], lambda v: '%.2fx' % v),
    ]
    out = []
    for key, label, f, fmt in dims:
        mine = f(L)
        order = sorted((t for t in towns if t != L), key=lambda t: abs(f(t) - mine))
        out.append(dict(
            key=key, label=label, lunenburg=fmt(mine),
            towns=[dict(town=t, value=fmt(f(t))) for t in order[:near]]))
    return out


def commercial_gap(frame, val, comparison):
    """HOW BIG IS THEIR BUSINESS BASE, WHAT DOES IT YIELD, AND WHAT WOULD WE NEED TO MATCH IT.

    TJ: *"this report is supposed to SHOW and compare commercial sizes to lunenburg, how much
    those businesses bring in and what WE would need to do to match that."*

    THE UNIT IS DOLLARS OF VALUE, not a share. A share is what the report has been using and
    it answers the wrong question: Westford and Lunenburg are within a point of each other on
    share (9.6% against 8.7%) while Westford's business base is $514 MILLION larger, because
    Westford is a far bigger town. What a school budget can spend is dollars, so the
    comparison has to be dollars — and per PUPIL, so a town with three times the children
    is not credited for having three times the base.

    AND THE 'WHAT WOULD WE NEED' IS AGAINST A REAL PACE. The gap is set beside the value
    Lunenburg's own assessors certify as new growth each year, so the answer is in years
    rather than in an abstract pile of money. It is a CEILING on how fast this could go: the
    comparison assumes every dollar of new growth is commercial, and most of it is housing."""
    L = 'Lunenburg'
    fte = {t: frame[t]['fte'] for t in frame}
    biz_pp = {t: val[t]['business'] / fte[t] for t in frame if t in val}
    med = st.median(biz_pp.values())
    need_median = (med - biz_pp[L]) * fte[L]
    # The levy a base yields at the town's own rate, which is what a resident can picture.
    rate = CLASSIFICATION['rate'] / 1000.0
    growth = sorted(num(r['total_value']) for r in rows(GROWTH)
                    if r['municipality'] == L and FY - 9 <= int(r['fy']) <= FY
                    and r['total_value'])
    pace = st.median(growth) if growth else None
    towns_out = []
    for t in comparison:
        if t not in val or t not in frame:
            continue
        towns_out.append(dict(
            town=t, business=round(val[t]['business']),
            share=round(100.0 * val[t]['business'] / val[t]['total'], 1),
            per_pupil=round(biz_pp[t]),
            levy=round(val[t]['business'] * rate),
            vs_lunenburg=round(val[t]['business'] - val[L]['business'])))
    towns_out.sort(key=lambda r: -r['business'])
    return dict(
        towns=towns_out, rate=CLASSIFICATION['rate'],
        lun_business=round(val[L]['business']),
        lun_share=round(100.0 * val[L]['business'] / val[L]['total'], 1),
        lun_per_pupil=round(biz_pp[L]),
        lun_levy=round(val[L]['business'] * rate),
        median_per_pupil=round(med),
        need_to_reach_median=round(need_median),
        levy_if_matched=round(need_median * rate),
        pace=round(pace) if pace else None,
        years_at_pace=round(need_median / pace, 1) if pace else None,
        n=len(biz_pp))


def cheap_and_generous(frame, effort, parcels):
    """THE QUESTION EVERYBODY ACTUALLY ASKS: is there a town that funds its schools well
    without taxing its residents hard — and if so, how does it do it?

    TJ, 26 September 2026, after reading a page full of what he correctly called tertiary
    metrics: *"are the towns with the lowest citizen tax bill able to fund their schools
    with per pupil cost without the tax payers? If so, how? Which towns have the highest per
    pupil and lowest tax bills, and how?"*

    THE TEST IS A CROSS-TABULATION, not an index. Combining a bill and a spending figure
    into one score would invent a weighting between dollars-paid and dollars-spent that
    nobody could argue with. Instead: the cheapest QUARTER of towns by average
    single-family bill, intersected with the top QUARTER by spending per pupil. A town in
    both is doing the thing the question is about, and the intersection is small enough to
    name every member.

    AND THE 'HOW' IS DECIDED BY THE DATA, not asserted. Each town in the intersection is
    tested against the two published routes by which school money can arrive without coming
    from local homeowners:

      * THE STATE COVERS WHAT LOCAL EFFORT CANNOT REACH. Chapter 70 measures a town by its
        `equalized_valuation` and its residents' `income`, turns those into a
        `combined_effort_yield`, and funds the gap up to the foundation budget. Measured here
        as dollars of state money per child, against the median of the frame.

        USE THE STATE'S OWN WORDS, and it does not say `poor`. Its vocabulary is `Lowinc` --
        only ever of STUDENTS, never of a town -- and, for a town's capacity, equalized
        valuation, income and local EFFORT. An earlier draft said `poor enough that the state
        pays`, which frames having little property value as a qualification somebody earned,
        and says it while naming Lawrence, Holyoke and Springfield, where people live.
      * THERE ARE A LOT OF HOUSES PER CHILD. A town with three times the usual number of
        homes for every pupil can raise three times as much per pupil at the same bill.
        Resort and retirement towns look like this.

    A town meeting neither test would be a third mechanism and this would say so rather than
    silently filing it under one of the two -- which is why the classification returns
    `unexplained` rather than a default.
    """
    towns = [t for t in sorted(frame) if t in effort and t in parcels]
    bills = sorted(frame[t]['bill'] for t in towns)
    pps = sorted(frame[t]['pp'] for t in towns)
    cheap_cut = bills[len(bills) // 4]
    spend_cut = pps[3 * len(pps) // 4]
    homes = {t: parcels[t] / frame[t]['fte'] for t in towns}
    med_state = st.median(effort[t]['state_pp'] for t in towns)
    med_homes = st.median(homes.values())
    med_cip = st.median(frame[t]['cip'] for t in towns)

    both = [t for t in towns
            if frame[t]['bill'] <= cheap_cut and frame[t]['pp'] >= spend_cut]
    rows_out = []
    for t in sorted(both, key=lambda t: -frame[t]['pp']):
        state_heavy = effort[t]['state_pp'] >= 2 * med_state
        homes_heavy = homes[t] >= 2 * med_homes
        # BUSINESS IS TESTED TOO, and it is the interesting negative. TJ asked for the
        # commercial aspect to be layered in; leaving it out of the classifier let a reader
        # assume nobody had checked. On the same rule as the other two -- twice the frame
        # median share of the tax base -- NO town in this set qualifies, which is a finding
        # rather than an omission and is reported as one.
        biz_heavy = frame[t]['cip'] >= 2 * med_cip
        how = ('the state' if state_heavy and not homes_heavy
               else 'houses' if homes_heavy and not state_heavy
               else 'both' if state_heavy and homes_heavy
               else 'business' if biz_heavy
               else 'unexplained')
        rows_out.append(dict(
            town=t, bill=round(frame[t]['bill']), pp=round(frame[t]['pp']),
            state_pp=round(effort[t]['state_pp']), homes_per_pupil=round(homes[t], 2),
            cip=round(frame[t]['cip'], 1), how=how, biz_heavy=biz_heavy))
    return dict(
        towns=rows_out, n=len(towns),
        cheap_cut=round(cheap_cut), spend_cut=round(spend_cut),
        med_state=round(med_state), med_homes=round(med_homes, 2),
        by_state=len([r for r in rows_out if r['how'] in ('the state', 'both')]),
        by_houses=len([r for r in rows_out if r['how'] in ('houses', 'both')]),
        by_business=len([r for r in rows_out if r['biz_heavy']]),
        med_cip=round(med_cip, 1),
        # AND THE SAME QUESTION ASKED WHERE WEALTH IS HELD ROUGHLY STILL: among towns whose
        # average home is within a band around Lunenburg's, what does a bigger business base
        # actually buy? It is the fairest test this archive can run on the commercial
        # argument, because the raw correlation is dominated by house prices.
        band=_business_within_band(frame, towns),
        unexplained=[r['town'] for r in rows_out if r['how'] == 'unexplained'],
        lun=dict(bill=round(frame['Lunenburg']['bill']), pp=round(frame['Lunenburg']['pp']),
                 state_pp=round(effort['Lunenburg']['state_pp']),
                 homes_per_pupil=round(homes['Lunenburg'], 2)))

def levers(frame, share, parcels, twins):
    """WHAT OTHER DISTRICTS DO THAT LUNENBURG DOES NOT -- and how we know.

    TJ, 26 September 2026, giving the report its actual job: *"we are trying to answer the
    questions: what are OTHER districts doing right that we aren't, and how do we know? Or
    what is lunenburg doing right/wrong compared to them, and how do we know"*

    The second half of that question is the hard one, and it is why every row here carries a
    CONFIDENCE and a CHOOSEABLE. A comparison that lists differences without saying which
    are decisions and which are circumstances hands a reader a list of things to be angry
    about, most of which nobody in this town can move. Homes per pupil is not a policy. How
    often the town asks its voters is.

    Rule 7 governs the confidence column absolutely. `measured` means the figure is computed
    from a published file. `not established` means the comparison CANNOT settle it, and that
    is said on the row rather than left for a reader to assume the first."""
    L = frame['Lunenburg']
    towns = sorted(frame)
    n = len(towns)
    med = lambda k: st.median(frame[t][k] for t in towns)
    rank = lambda k, hi=True: (sorted(towns, key=lambda t: -frame[t][k] if hi else frame[t][k])
                               .index('Lunenburg') + 1)
    homes = {t: parcels[t] / frame[t]['fte'] for t in towns if t in parcels}
    lun_homes = homes['Lunenburg']
    med_homes = st.median(homes.values())
    shared = [t for t in towns if t in share]
    med_share = st.median(share[t] for t in shared)
    share_rank = sorted(shared, key=lambda t: -share[t]).index('Lunenburg') + 1
    best_growth = max(twins + NEIGHBOURS + PEERS + ['Lunenburg'],
                      key=lambda t: frame[t]['ngpct'] if t in frame else -1)
    E = effects(frame)
    E['ratio_t'] = '%.2f' % E['ratio']
    E['med_ratio_t'] = '%.2f' % E['med_ratio']

    return [
        dict(id='above-the-floor',
             what='Spend further above what the state says your schools need',
             lunenburg='THE ONE THAT ANSWERS THE QUESTION. The state computes a foundation '
                       'budget for each town from its own children and its own wealth, so '
                       'comparing each town to its OWN floor is fair in a way a raw '
                       'per-pupil figure is not. Lunenburg spends %sx its floor; the middle '
                       'district here spends %sx. At that middle ratio Lunenburg would spend '
                       '%s more per pupil.'
                       % (E['ratio_t'], E['med_ratio_t'], usd(E['at_median_gap'])),
             evidence='DESE per-pupil expenditure SY%d over the FY%d town foundation budget '
                      'per foundation pupil.' % (SY, FY),
             confidence='measured', chooseable=True,
             caveat='Spending is all funds, so a town that wins more grants shows a higher '
                    'ratio without its taxpayers deciding anything. And this measures '
                    'distance from a formula, not whether any amount is right.'),
        dict(id='required-share',
             what='Be required to put in more',
             lunenburg='Lunenburg is required to raise %s per child. The middle '
                       'Massachusetts town is required to raise %s. The requirement follows '
                       'a town\u2019s property wealth and income, so it is not something '
                       'anybody here votes on \u2014 but it IS a floor, not a ceiling.'
                       % (usd(E['required_pp']), usd(E['med_required_pp'])),
             evidence='DESE Chapter 70 municipal contribution file, FY%d: required local '
                      'contribution over foundation enrolment.' % FY,
             confidence='measured', chooseable=False,
             caveat='A required contribution is a statutory MINIMUM. Most towns appropriate '
                    'above it, and how far above is the decision in the row above.'),
        dict(id='spends-least',
             what='Spend more on each pupil',
             lunenburg='%s per pupil, %s of %d comparable districts. The middle of those '
                       'districts spends %s — %s more than Lunenburg.'
                       % (usd(L['pp']), ordinal(rank('pp')), n, usd(med('pp')),
                          usd(med('pp') - L['pp'])),
             evidence='DESE per-pupil total expenditures, SY%d, all funds.' % SY,
             confidence='measured', chooseable=True,
             caveat='Per-pupil spending is money in, not results out. Nothing here says '
                    'whether Lunenburg is run leanly or is short of what its children need, '
                    'and no figure in this report could.'),
        dict(id='state-help',
             what='Get more help from the state',
             lunenburg='Lunenburg already does. The state expects to cover %s of its '
                       'foundation budget, against %s for the middle district here — '
                       '%s of %d. Low spending is NOT explained by thin state aid.'
                       % (pct(share['Lunenburg'], 0), pct(med_share, 0),
                          ordinal(share_rank), len(shared)),
             evidence='DESE Chapter 70 municipal contribution file, FY%d: the town '
                      'foundation budget less the required local contribution.' % FY,
             confidence='measured', chooseable=False,
             caveat='A foundation budget is the state’s formula for an adequate '
                    'education, not what anybody spends, and a required contribution is a '
                    'minimum rather than what a town raises.'),
        dict(id='value-per-pupil',
             what='Have more taxable value behind each child',
             lunenburg='CORRECTED, and it goes the other way. Counting HOMES, Lunenburg '
                       'looks comfortable: %.1f per pupil against %.1f for the middle '
                       'district. Counting VALUE \u2014 which is what a tax bill is actually '
                       'levied on \u2014 it has %s per pupil against a median of %s, %s of '
                       '%d. More houses per child than most towns and less money behind each '
                       'child, because its houses are worth less.'
                       % (lun_homes, med_homes, usd(E['val_pp']), usd(E['med_val_pp']),
                          ordinal(E['val_pp_rank']), E['n_val']),
             evidence='DLS assessed value by class FY%d over DESE full-time-equivalent '
                      'pupils SY%d; parcels from the same DLS file.' % (FY, SY),
             confidence='measured', chooseable=False,
             caveat='This is ALL taxable value \u2014 houses, flats, shops, plant. It is also '
                    'the quantity a commercial base adds to, which is why business and '
                    'housing are ONE lever here and not two: a warehouse that brings no '
                    'children and a second home that brings no children do the same thing. '
                    'What differs is size \u2014 business is %s of Lunenburg\u2019s base and '
                    'housing is the rest.' % pct(L['cip'], 1)),
        dict(id='ask-the-voters',
             what='Ask the voters for an override more often',
             lunenburg='Lunenburg has put %d questions and won %d. Towns that have won %d or '
                       'more average a %s tax bill; towns that have never won one average '
                       '%s.' % (L['put'], L['won'], 3,
                                usd(effects(frame)['bill_many']),
                                usd(effects(frame)['bill_none'])),
             evidence='DLS override and underride votes, every question since FY%d.'
                      % 1990,
             confidence='not established', chooseable=True,
             caveat='WHICH CAUSES WHICH is exactly what this cannot say. A town with a '
                    'higher bill may pass overrides because its residents can afford them, '
                    'rather than having a higher bill because it passed them — and '
                    'wealth would produce both. Asking more often is a decision; that it '
                    'would raise Lunenburg’s spending is not shown here.'),
        dict(id='grow-the-base',
             what='Grow the commercial base',
             lunenburg='%s adds %s of its levy limit in new growth each year against '
                       'Lunenburg’s %s. But across all %d towns, new growth and the tax '
                       'bill are unrelated, and the town’s own assessor priced the '
                       'largest possible shift onto business at %s a year.'
                       % (best_growth, pct(frame[best_growth]['ngpct'], 2),
                          pct(L['ngpct'], 2), n, usd2(CLASSIFICATION['saving'])),
             evidence='DLS new growth, ten-year mean to FY%d; the correlation across the '
                      'frame; Select Board minutes of %s.'
                      % (FY, CLASSIFICATION['date_text']),
             confidence='measured', chooseable=True,
             caveat='What growth buys is levy CAPACITY — room under the limit — '
                    'not a smaller bill for an existing household. Those are different '
                    'things and are routinely argued as though they were one.'),
    ]


def verdicts(frame, share, parcels, groups, bills=None, effort=None, districts=None,
             raw_pp=None):
    """One verdict per comparison town: what it does differently, and the arithmetic that
    lets it. Returns rows in the order the groups were given."""
    L = frame['Lunenburg']
    bills = bills or {}
    effort = effort or {}
    districts = districts or {}
    raw_pp = raw_pp or {}
    lun_homes = parcels['Lunenburg'] / L['fte']
    LE = effort.get('Lunenburg')
    out = []
    for role, towns in groups:
        for t in towns:
            m = frame.get(t)
            if not m or t not in parcels:
                # NOT SILENTLY DROPPED. A town in a REGIONAL district is not in the frame,
                # because its school bill is shared with other member towns and no per-pupil
                # figure belongs to its taxpayers alone. Six of the eleven neighbours and
                # peers are in that position. Omitting them would have read as an archive
                # with nothing to say about Ashby; it says instead why nobody can answer the
                # question for Ashby, which is the finding.
                # A REGIONAL TOWN IS ANSWERED AT THE TOWN LEVEL, not skipped. Chapter 70
                # is computed per municipality whatever district its children attend, so
                # what this town is REQUIRED to raise per child and what the state puts in
                # per child are published for it exactly as for Lunenburg. What its
                # children's schools spend per pupil is published too -- of the district.
                # The only step that stays unknowable is how the district's assessment is
                # split between its members.
                e = effort.get(t)
                dist = districts.get(t)
                dpp = raw_pp.get(dist)
                bill_d = (bills[t] - L['bill']) if t in bills else None
                req_d = (e['required_pp'] - LE['required_pp']) if (e and LE) else None
                out.append(dict(
                    town=t, role=role, quadrant='regional',
                    quadrant_label='In a regional district',
                    bill=bills.get(t), bill_diff=round(bill_d) if bill_d is not None else None,
                    pp=dpp, pp_diff=None, district=dist,
                    required_pp=round(e['required_pp']) if e else None,
                    required_diff=round(req_d) if req_d is not None else None,
                    state_pp=round(e['state_pp']) if e else None,
                    children=round(e['children']) if e else None,
                    homes_per_pupil=None, state_share=share.get(t),
                    sf_tax_per_pupil=None, enrchg=None, put=None, won=None, cip=None,
                    line='%s is in a regional district.' % t,
                    tail=('is required to raise %s per child, %s than Lunenburg\u2019s %s, '
                          'and the state adds %s. Its children attend %s, which spends %s '
                          'per pupil.'
                          % (usd(e['required_pp']),
                             '%s more' % usd(abs(req_d)) if req_d and req_d > 0
                             else ('%s less' % usd(abs(req_d)) if req_d else 'about the same'),
                             usd(LE['required_pp']), usd(e['state_pp']), dist or 'a regional district',
                             usd(dpp) if dpp else 'a figure this report does not hold')
                          if e and LE else
                          'is in a regional school district and DESE publishes no Chapter 70 '
                          'row for it this year.'),
                    why=[], unexplained=False))
                continue
            bill_d = m['bill'] - L['bill']
            pp_d = m['pp'] - L['pp']
            homes = parcels[t] / m['fte']
            key, label = QUADRANTS[(bill_d < 0, pp_d > 0)]

            # The headline sentence, in the reader's own units.
            def amt(d, noun):
                return ('about the same %s' % noun if abs(d) < (SAME_BILL if noun == 'tax bill'
                                                               else SAME_PP)
                        else '%s %s %s' % (usd(abs(d)), 'less' if d < 0 else 'more', noun))
            # THE NAME IS NOT IN THE SENTENCE. Both consumers print the town as a heading
            # and then the sentence, and baking it in gave `**Fitchburg** -- Fitchburg pays`.
            tail = ('pays %s on the average single-family home and spends %s on each pupil.'
                    % (amt(bill_d, 'tax bill').replace(' tax bill', ''),
                       amt(pp_d, 'per pupil').replace(' per pupil', '')))
            line = '%s %s' % (t, tail)

            # ...and WHY it can, where the archive can say. Both are mechanisms, not causes:
            # they show how the arithmetic is possible, not that either is the reason.
            why = []
            if homes - lun_homes >= MORE_HOMES:
                why.append('It has %.1f homes for every pupil against Lunenburg’s %.1f, '
                           'so more households share the cost of each child.'
                           % (homes, lun_homes))
            elif lun_homes - homes >= MORE_HOMES:
                why.append('It has only %.1f homes per pupil against Lunenburg’s %.1f, '
                           'so fewer households share each child.' % (homes, lun_homes))
            st_d = (share.get(t) or 0) - (share.get('Lunenburg') or 0)
            if st_d >= MORE_STATE:
                why.append('The state covers %s of its foundation budget against %s of '
                           'Lunenburg’s.' % (pct(share[t], 0), pct(share['Lunenburg'], 0)))
            elif st_d <= -MORE_STATE:
                why.append('The state covers only %s of its foundation budget against %s of '
                           'Lunenburg’s — it gets LESS help, not more.'
                           % (pct(share[t], 0), pct(share['Lunenburg'], 0)))
            # WHERE THE ARITHMETIC DOES NOT CLOSE, SAY SO. A town that raises less per pupil
            # from its houses, gets a smaller share from the state and still spends more has
            # money coming from somewhere this archive cannot see -- other local revenue, a
            # different split of the town budget, grants, or a reserve. That is rule 7c's
            # shape and it is stated on the card rather than left for a reader to wonder at.
            raises = parcels[t] * m['bill'] / m['fte']
            lun_raises = parcels['Lunenburg'] * L['bill'] / L['fte']
            unexplained = (pp_d > SAME_PP and raises < lun_raises and st_d < 0)
            if unexplained:
                why.append('It raises %s per pupil from single-family tax against '
                           'Lunenburg’s %s and gets a smaller share from the state, so '
                           'the extra comes from somewhere this archive cannot see.'
                           % (usd(raises), usd(lun_raises)))
            # HOW IT IS THE SAME, not only how it differs. TJ: *"explain how they are
            # similar and different"*. The cohort was matched on these, so saying which ones
            # actually landed close is the evidence that the match means anything -- and a
            # reader who is told two towns are alike will want to know in what.
            same = []
            for key_, noun, fmt, tol in (
                    # 25%, not 35%: Douglas's 1,113 children against Lunenburg's 1,563 is a
                    # 29% gap, and listing it under `Like Lunenburg` reads as a claim the
                    # numbers do not support. A tolerance that admits everything says nothing.
                    ('size', 'children', '{:,.0f}', 0.25),
                    ('lowinc', 'low-income share', '{:.0f}%', 0.20),
                    ('value', 'average home', '${:,.0f}', 0.15),
                    ('income', 'income per head', '${:,.0f}', 0.15),
                    ('swd', 'share with a disability', '{:.0f}%', 0.20)):
                a, b = m[key_], L[key_]
                if b and abs(a - b) / b <= tol:
                    same.append('%s %s to Lunenburg\u2019s %s'
                                % (noun, fmt.format(a), fmt.format(b)))
            ratio = (m['pp'] / effort[t]['foundation_pp']) if t in effort else None
            lun_ratio = (L['pp'] / LE['foundation_pp']) if LE else None
            if ratio and lun_ratio and abs(ratio - lun_ratio) >= 0.05:
                why.append('It spends %.2fx what the state says its own schools need '
                           'against Lunenburg\u2019s %.2fx.' % (ratio, lun_ratio))
            out.append(dict(
                town=t, role=role, quadrant=key, quadrant_label=label,
                same=same, above_foundation=round(ratio, 2) if ratio else None,
                required_pp=round(effort[t]['required_pp']) if t in effort else None,
                state_pp=round(effort[t]['state_pp']) if t in effort else None,
                bill=m['bill'], bill_diff=round(bill_d), pp=m['pp'], pp_diff=round(pp_d),
                homes_per_pupil=round(homes, 2), state_share=share.get(t),
                sf_tax_per_pupil=round(raises), enrchg=m['enrchg'],
                put=m['put'], won=m['won'], cip=m['cip'],
                line=line, tail=tail, why=why, unexplained=unexplained))
    return out

def effects(frame):
    """The same findings as the correlations, in units a resident's own bill is printed in.

    A CORRELATION IS NOT A QUANTITY ANYBODY CAN SPEND. `r +0.91` says the relationship is
    tight and says nothing about how much money it is; the slope says how much money it is
    and nothing about how tight. The cards carry these, the chart and the table carry the
    correlations, and neither is a substitute for the other."""
    towns = sorted(frame)
    n = len(towns)
    xs = [frame[t]['value'] for t in towns]
    ys = [frame[t]['bill'] for t in towns]
    mx, my = st.mean(xs), st.mean(ys)
    slope = (sum((a - mx) * (b - my) for a, b in zip(xs, ys))
             / sum((a - mx) ** 2 for a in xs))
    k = n // 5
    by_value = sorted(towns, key=lambda t: frame[t]['value'])
    # THE CUT IS WHERE THE GROUPS ARE, not a round number chosen to flatter the gap: three
    # or more wins is the top third of towns by wins, and zero is a real category rather
    # than a bucket edge -- 62 of the 161 have never won one.
    win_cut = 3
    none = [t for t in towns if frame[t]['won'] == 0]
    many = [t for t in towns if frame[t]['won'] >= win_cut]
    share = state_share()
    eff = town_effort()
    parcels = {r['municipality']: num(r['sf_parcels']) for r in rows(BILLS)
               if r['fy'] == str(FY) and r['sf_parcels']}
    homes = {t: parcels[t] / frame[t]['fte'] for t in towns if t in parcels}
    shared = [t for t in towns if t in share]
    # HOW FAR ABOVE THE STATE'S OWN ADEQUACY MODEL A TOWN SPENDS.
    #
    # This is the one comparison on this page that is genuinely like for like. A foundation
    # budget is computed for each town from ITS children and ITS wealth, so it already
    # absorbs the differences -- more low-income children, more English learners, a poorer
    # tax base -- that make a raw per-pupil comparison unfair. What is left, once each town
    # is measured against its own floor, is how much further than the floor it chooses to
    # go. That is the closest thing in this report to a decision.
    val = taxable_value()
    val_pp = {t: val[t]['total'] / frame[t]['fte'] for t in towns if t in val}
    ratio = {t: frame[t]['pp'] / eff[t]['foundation_pp'] for t in towns if t in eff}
    med_ratio = st.median(ratio.values())
    r_rank = sorted(ratio, key=lambda t: -ratio[t]).index('Lunenburg') + 1
    return dict(
        val_pp=round(val_pp['Lunenburg']),
        med_val_pp=round(st.median(val_pp.values())),
        val_pp_rank=sorted(val_pp, key=lambda t: -val_pp[t]).index('Lunenburg') + 1,
        n_val=len(val_pp),
        ratio=ratio['Lunenburg'], med_ratio=med_ratio,
        ratio_rank=r_rank, n_ratio=len(ratio),
        at_median=round(med_ratio * eff['Lunenburg']['foundation_pp']),
        at_median_gap=round(med_ratio * eff['Lunenburg']['foundation_pp'] - frame['Lunenburg']['pp']),
        foundation_pp=round(eff['Lunenburg']['foundation_pp']),
        required_pp=round(eff['Lunenburg']['required_pp']),
        med_required_pp=round(st.median(e['required_pp'] for e in eff.values())),
        med_pp=round(st.median(frame[t]['pp'] for t in towns)),
        lun_share=share['Lunenburg'],
        med_share=st.median(share[t] for t in shared),
        share_rank=sorted(shared, key=lambda t: -share[t]).index('Lunenburg') + 1,
        n_share=len(shared),
        lun_homes=homes['Lunenburg'],
        med_homes=st.median(homes.values()),
        per100k=round(slope * 100000),
        val_lo=round(st.mean(frame[t]['bill'] for t in by_value[:k])),
        val_hi=round(st.mean(frame[t]['bill'] for t in by_value[-k:])),
        win_cut=win_cut,
        n_none=len(none), n_many=len(many),
        bill_none=round(st.mean(frame[t]['bill'] for t in none)),
        bill_many=round(st.mean(frame[t]['bill'] for t in many)))


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

    share = state_share()
    effort = town_effort()
    parcels = {r['municipality']: num(r['sf_parcels']) for r in rows(BILLS)
               if r['fy'] == str(FY) and r['sf_parcels']}
    if 'Lunenburg' not in parcels:
        raise SystemExit('no FY%d single-family parcel count for Lunenburg' % FY)
    twins_is, all_is = cohort(frame, IS_KEYS, 10)
    twins_does, all_does = cohort(frame, DOES_KEYS, 10)
    overlap10 = [t for t in all_is[:10] if t in all_does[:10]]
    overlap25 = [t for t in all_is[:25] if t in all_does[:25]]
    dest = destinations()

    sets = dict(neighbours=NEIGHBOURS, peers=PEERS, ov=raw['ov'], dese=raw['dese'],
                first_override_fy=min(int(q['fy']) for qs in raw['ov'].values() for q in qs))
    cons = build_conclusions(frame, corr, twins_is, twins_does, overlap10, overlap25,
                             dest, sets, effort=effort, parcels=parcels)

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

    # EVERY comparison town, including the ones NOT in the frame. Filtering to the frame
    # here is what made six towns vanish from the verdicts without a word -- they are in
    # regional districts, which is a fact about them worth printing rather than a reason to
    # drop them.
    groups = [('lunenburg', ['Lunenburg']),
              ('neighbour', list(NEIGHBOURS)),
              ('peer', list(PEERS)),
              ('structural', [c['town'] for c in twins_is]),
              ('behavioural', [c['town'] for c in twins_does])]
    seen, ordered = set(), []
    for role, ts in groups:
        keep = [t for t in ts if t not in seen]
        seen.update(keep)
        ordered.append((role, keep))
    dist_pp = {d: raw['dese'].get(str(SY), {}).get(d, {})
               .get(('Expenditures Per Pupil', 'Total Expenditures'))
               for d in set(DISTRICT_OF.values())}
    val = taxable_value()
    cheap = cheap_and_generous(frame, effort, parcels)
    comm = commercial_gap(frame, val, ['Lunenburg'] + NEIGHBOURS + PEERS
                          + [c['town'] for c in twins_is])
    town_verdicts = verdicts(frame, share, parcels, ordered,
                             bills={t: raw['bill'][(t, FY)] for (t, y) in raw['bill']
                                    if y == FY},
                             effort=effort, districts=DISTRICT_OF, raw_pp=dist_pp)

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
                 label='where that bill ranks among the 351 Massachusetts towns — '
                       '1st is the highest bill in the state'),
            dict(value=usd(L['pp']),
                 label='spent per pupil in SY%d, all funds \u2014 %s of %d comparable '
                       'districts, where 1st spends the most'
                       % (SY, ordinal(pp_rank), len(frame))),
            dict(value='%d of %d' % (L['won'], L['put']),
                 label='override questions Lunenburg has won of those it has put to voters'),
            dict(value=pct(L['cip'], 1),
                 label='of Lunenburg\u2019s taxable property is business rather than '
                       'housing'),
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
        verdicts=town_verdicts,
        cheap_and_generous=cheap,
        commercial=comm,
        by_dimension=by_dimension(frame, val, effort, parcels),
        distributions=distributions(frame, val, effort, parcels),
        above_requirement=above_the_requirement(frame, raw['dese']),
        predictors=predictors(frame, val, effort),
        regional=regional_picture(frame, raw['dese']),
        regional_members=regional_members(),
        heatmap=heatmap(frame, val, effort, parcels),
        outside=outside_the_appropriation(raw['dese']),
        cherry=cherry_sheet(raw['dese']),
        funding=funding_stack(frame, val, effort,
                              ['Lunenburg'] + NEIGHBOURS + PEERS
                              + [c['town'] for c in twins_is]),
        value_per_pupil={t: round(val[t]['total'] / frame[t]['fte'])
                         for t in frame if t in val},
        their_state_median=round(st.median(
            r['state_pp'] for r in cheap['towns'] if r['how'] in ('the state', 'both'))),
        levers=levers(frame, share, parcels, [c['town'] for c in twins_is]),
        state_share={t: round(v, 1) for t, v in share.items() if t in frame},
        effort={t: {k: round(x) if k != 'share' else round(x, 1)
                    for k, x in e.items() if k != 'children'}
                for t, e in effort.items()
                if t in frame or t in NEIGHBOURS or t in PEERS},
        homes_per_pupil={t: round(parcels[t] / frame[t]['fte'], 2)
                         for t in frame if t in parcels},
        overlap10=overlap10, overlap25=overlap25,
        destinations=dest,
        # No `outline` here: the heat map already ships every town's polygon and the
        # signature map draws its faint state outline from those. One Massachusetts, not two.
        map=dict(towns=shapes,
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
            'How a regional district divides its assessment between member towns, and what '
            'each member town actually appropriates for schools. What each is REQUIRED to '
            'raise per child IS published and is used here; what is not published is the '
            'step between that minimum and the district’s books.',
            'What any town actually appropriates, anywhere in this report. A required local '
            'contribution is a statutory floor and most towns go above it; how far above is '
            'the decision this comparison is really about, and it is not in these files.',
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
    'lunenburg': 'Lunenburg', 'neighbour': 'borders us', 'peer': 'peer town',
    'structural': 'looks like us', 'behavioural': 'acts like us',
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
    # ONE MASSACHUSETTS IN THE PAYLOAD, not three. The state outline and these towns' own
    # polygons both come from the heat map's shapes, which already holds every town.
    shapes_all = payload['heatmap']['shapes']
    outline = [ring for rings in shapes_all.values() for ring in rings]
    W, pad, top = 756, 10, 74
    lon0, lon1, lat0, lat1 = projection(outline)
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
    for ring in outline:
        o.append("<polyline points='%s' fill='none' stroke='#e5e7eb' stroke-width='0.5'/>"
                 % ' '.join('%.1f,%.1f' % px(x, y) for x, y in ring))
    for name in sorted(m['towns']):
        fill = ROLE_FILL[m['roles'][name]]
        for ring in shapes_all.get(name, []):
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


# THE FOUR COLOURS OF SCHOOL MONEY. Distinct hues rather than one ramp, because the reader
# has to tell `from the state` apart from `above the state's figure` at a glance and those
# are the two the whole report turns on.
FUND_PARTS = [
    ('from_homes', 'From homes', '#3b5bbf'),
    ('from_business', 'From business', '#ea8c00'),
    ('from_state', 'From the state', '#2f8f4e'),
    ('above_foundation', 'Spent above the state’s figure', '#7c3aed'),
]


def fmt_kind(v, kind):
    """One renderer for every measure, so a page and a chart cannot format a figure two ways."""
    if kind == 'usd':
        return usd(v)
    if kind == 'pct':
        return pct(v, 1)
    if kind == 'pctdiff':
        return '%+.1f%%' % v
    if kind == 'ratio':
        return '%.2fx' % v
    return '{:,.0f}'.format(v)


HEAT = ['#f7fbff', '#d7e6f5', '#a9cbe8', '#6fa8d4', '#3d7fb8', '#1d4ed8', '#12307a']


def heat_svg(payload, key='per_pupil'):
    """THE WHOLE STATE SHADED BY ONE MEASURE, for the readers who cannot press a button.

    The web page draws this as a component with a switch across thirteen measures. A
    document cannot switch, so it shows the one the report is about -- what a district
    spends on each pupil -- and says where the rest are."""
    h = payload['heatmap']
    m = next((x for x in h['measures'] if x['key'] == key), h['measures'][0])
    W, pad = 756, 8
    xs = [x for rings in h['shapes'].values() for ring in rings for x, _ in ring]
    ys = [y for rings in h['shapes'].values() for ring in rings for _, y in ring]
    lon0, lon1, lat0, lat1 = min(xs), max(xs), min(ys), max(ys)
    kx = math.cos(math.radians((lat0 + lat1) / 2))
    top = 86
    k = (W - 2 * pad) / ((lon1 - lon0) * kx)
    H = int(round(top + pad + (lat1 - lat0) * k)) + 34

    def px(lon, lat):
        return (pad + (lon - lon0) * kx * k, top + (lat1 - lat) * k)

    order = sorted(m['values'], key=lambda t: m['values'][t])
    rank = {t: i for i, t in enumerate(order)}
    n = len(order)

    def colour(t):
        if t not in rank:
            return '#eceff3'
        i = min(len(HEAT) - 1, int((rank[t] / max(n - 1, 1)) * len(HEAT)))
        return HEAT[i]

    o = ["<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 %d %d' width='%d' height='%d' "
         "role='img' aria-label='%s' font-family='system-ui, -apple-system, sans-serif'>"
         % (W, H, W, H, esc(
             'Every Massachusetts town shaded by %s, darkest where it is highest. Lunenburg '
             'is outlined in red at %s, against a middle town of %s. Towns with no figure '
             'published are left blank.'
             % (m['label'].lower(), fmt_kind(m['lunenburg'], m['kind']),
                fmt_kind(m['median'], m['kind'])))),
         "<rect width='%d' height='%d' fill='#ffffff'/>" % (W, H),
         "<text x='10' y='22' font-size='15' font-weight='700' fill='#111827'>%s, town by "
         "town</text>" % esc(m['label']),
         "<text x='10' y='40' font-size='11.5' fill='#4b5563'>%s. Lunenburg outlined in red: "
         "%s. The middle town: %s.</text>"
         % (esc(m['note'][0].upper() + m['note'][1:]),
            fmt_kind(m['lunenburg'], m['kind']), fmt_kind(m['median'], m['kind'])),
         "<text x='10' y='56' font-size='10.5' fill='#6b7280'>Shaded by RANK, not by amount: "
         "a few towns hold most of the total on nearly every measure here.</text>"]
    lx = 10
    o.append("<text x='%d' y='78' font-size='10.5' fill='#6b7280'>%s</text>"
             % (lx, esc(fmt_kind(m['lo'], m['kind']))))
    lx += 8 + 6.0 * len(fmt_kind(m['lo'], m['kind']))
    for c in HEAT:
        o.append("<rect x='%.1f' y='69' width='26' height='11' fill='%s' stroke='#e5e7eb'/>"
                 % (lx, c))
        lx += 26
    o.append("<text x='%.1f' y='78' font-size='10.5' fill='#6b7280'>%s</text>"
             % (lx + 6, esc(fmt_kind(m['hi'], m['kind']))))
    for name, rings in sorted(h['shapes'].items()):
        fill = colour(name)
        me = name == 'Lunenburg'
        for ring in rings:
            o.append("<polygon points='%s' fill='%s' stroke='%s' stroke-width='%s'/>"
                     % (' '.join('%.1f,%.1f' % px(x, y) for x, y in ring), fill,
                        '#dc2626' if me else '#ffffff', '1.8' if me else '0.4'))
    o.append("<text x='10' y='%d' font-size='10.5' fill='#6b7280'>The web version of this "
             "report switches this map between %d measures and names every town under the "
             "cursor.</text>" % (H - 10, len(h['measures'])))
    o.append('</svg>')
    return '\n'.join(o) + '\n'


def positions_svg(payload):
    """WHERE LUNENBURG SITS ON EVERY MEASURE, one axis at a time, all towns on each.

    Small multiples rather than one combined chart: the measures are in dollars, counts,
    percentages and ratios, and any axis that held them together would be a lie about
    comparability. What repeats across the rows is the SHAPE — each is the full spread of
    the same 161 towns — so the eye compares positions, which is the only thing these
    measures have in common."""
    ds = payload['distributions']
    W = 756
    label_w, pad = 246, 12
    rowh, top = 44, 74
    H = top + rowh * len(ds) + 30
    bar_x = label_w + pad
    bar_w = W - bar_x - 96

    o = ["<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 %d %d' width='%d' height='%d' "
         "role='img' aria-label='%s' font-family='system-ui, -apple-system, sans-serif'>"
         % (W, H, W, H, esc(
             'Twelve measures, each drawn as the full spread of the %d Massachusetts towns '
             'that run their own K-12 district, with Lunenburg marked. It is 158th of 161 on '
             'spending per pupil and 82nd on the average tax bill.' % ds[0]['n'])),
         "<rect width='%d' height='%d' fill='#ffffff'/>" % (W, H),
         "<text x='10' y='22' font-size='15' font-weight='700' fill='#111827'>Where Lunenburg "
         "sits, measure by measure</text>",
         "<text x='10' y='40' font-size='11.5' fill='#4b5563'>Each line is all %d towns that "
         "run their own K–12 district, from lowest to highest. The blue mark is "
         "Lunenburg; the grey line is the middle town.</text>" % ds[0]['n'],
         "<text x='10' y='58' font-size='10.5' fill='#6b7280'>The measures are in different "
         "units and share no axis. What repeats is the SPREAD — so a position can be "
         "read against how far apart the towns actually are.</text>"]

    for i, d in enumerate(ds):
        y = top + i * rowh
        lo, hi = d['lo'], d['hi']
        span = (hi - lo) or 1.0
        def X(v):
            return bar_x + bar_w * (v - lo) / span
        o.append("<text x='10' y='%.1f' font-size='11' fill='#374151'>%s</text>"
                 % (y + 4, esc(d['label'][:54])))
        o.append("<text x='10' y='%.1f' font-size='9.5' fill='#9ca3af'>%s</text>"
                 % (y + 17, esc(d['note'][:62])))
        # the spread, every town a tick
        o.append("<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='#e5e7eb' "
                 "stroke-width='1'/>" % (bar_x, y + 8, bar_x + bar_w, y + 8))
        # THE MIDDLE HALF, SHADED. Several of these measures are badly skewed -- a handful of
        # large towns stretch the axis and press everything else against the left -- so a
        # position alone does not say whether it is ordinary. The band between the 25th and
        # 75th town answers that directly: inside it is typical, outside it is not.
        o.append("<rect x='%.1f' y='%.1f' width='%.1f' height='12' fill='#c7d2fe' "
                 "fill-opacity='0.5'/>"
                 % (X(d['p25']), y + 2, max(X(d['p75']) - X(d['p25']), 1)))
        for v in d['values']:
            o.append("<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='#9ca3af' "
                     "stroke-width='0.7' stroke-opacity='0.45'/>" % (X(v), y + 2, X(v), y + 14))
        o.append("<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='#6b7280' "
                 "stroke-width='1.4'/>" % (X(d['median']), y - 1, X(d['median']), y + 17))
        lx = X(d['lunenburg'])
        o.append("<circle cx='%.1f' cy='%.1f' r='5' fill='#1d4ed8' stroke='#ffffff' "
                 "stroke-width='1.4'/>" % (lx, y + 8))
        o.append("<text x='%.1f' y='%.1f' font-size='10.5' font-weight='700' fill='#1d4ed8' "
                 "text-anchor='%s'>%s</text>"
                 % (lx + (7 if lx < bar_x + bar_w * 0.7 else -7), y + 28,
                    'start' if lx < bar_x + bar_w * 0.7 else 'end',
                    esc(fmt_kind(d['lunenburg'], d['kind']))))
        o.append("<text x='%d' y='%.1f' font-size='10.5' fill='#111827' text-anchor='end'>"
                 "%s of %d</text>" % (W - 10, y + 12, ordinal(d['rank']), d['n']))
    o.append("<text x='10' y='%d' font-size='10.5' fill='#6b7280'>Rank counts from the "
             "highest value down: 1st has the most.</text>" % (H - 12))
    o.append('</svg>')
    return '\n'.join(o) + '\n'


def funding_svg(payload):
    """Two bars a town: how many pupils, and what is spent on each, by where it comes from.

    THE LEFT BAR IS THE DENOMINATOR, drawn at its own scale beside the thing it divides.
    Per-pupil figures are a ratio and this report has already had to correct one reading of
    them; putting the pupil count next to the spending makes the size of the school district
    visible instead of implied."""
    rows_ = payload['funding']
    W = 756
    rowh, top, gap = 26, 96, 6
    H = top + rowh * len(rows_) + 52
    name_w, pup_w, bar_x = 118, 96, 0
    bar_x = name_w + pup_w + 26
    bar_w = W - bar_x - 14
    max_pup = max(r['pupils'] for r in rows_)
    max_spend = max(r['per_pupil'] for r in rows_)

    o = ["<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 %d %d' width='%d' height='%d' "
         "role='img' aria-label='%s' font-family='system-ui, -apple-system, sans-serif'>"
         % (W, H, W, H, esc(
             'For each town, how many pupils it has and what it spends on each of them, '
             'split into what the town must raise from homes, what it raises from business, '
             'what the state adds, and what it spends above the state’s own figure. '
             'Lunenburg spends %s above that figure; the largest here is %s.'
             % (usd([r for r in rows_ if r['town'] == 'Lunenburg'][0]['above_foundation']),
                usd(max(r['above_foundation'] for r in rows_))))),
         "<rect width='%d' height='%d' fill='#ffffff'/>" % (W, H),
         "<text x='10' y='22' font-size='15' font-weight='700' fill='#111827'>Where each "
         "town’s school money comes from</text>",
         "<text x='10' y='40' font-size='11.5' fill='#4b5563'>Pupils, then dollars spent on "
         "each pupil, split by source. Sorted by how much a town spends ABOVE the figure the "
         "state calculates for it.</text>",
         "<text x='10' y='56' font-size='10.5' fill='#6b7280'>The local requirement is split "
         "between homes and business by each town’s own tax base — exact where one "
         "rate applies to all property, approximate where a town splits its rate.</text>"]
    lx = 10
    for _, label, colour in FUND_PARTS:
        o.append("<rect x='%.1f' y='68' width='10' height='10' rx='2' fill='%s'/>" % (lx, colour))
        o.append("<text x='%.1f' y='77' font-size='10.5' fill='#374151'>%s</text>"
                 % (lx + 14, esc(label)))
        lx += 20 + 5.9 * len(label) + 12
    o.append("<text x='%d' y='%d' font-size='10' fill='#6b7280'>pupils</text>"
             % (name_w + 2, top - 6))
    o.append("<text x='%d' y='%d' font-size='10' fill='#6b7280'>spent on each pupil</text>"
             % (bar_x, top - 6))

    for i, r in enumerate(rows_):
        y = top + i * rowh
        me = r['town'] == 'Lunenburg'
        if me:
            o.append("<rect x='4' y='%.1f' width='%d' height='%d' rx='3' fill='#eef2ff'/>"
                     % (y - 3, W - 8, rowh - 2))
        o.append("<text x='%d' y='%.1f' font-size='11.5' font-weight='%d' fill='#111827'>"
                 "%s</text>" % (8, y + 12, 700 if me else 400, esc(r['town'])))
        pw = max(pup_w * r['pupils'] / max_pup, 1)
        o.append("<rect x='%d' y='%.1f' width='%.1f' height='11' rx='2' fill='#9ca3af' "
                 "fill-opacity='0.55'/>" % (name_w, y + 3, pw))
        o.append("<text x='%.1f' y='%.1f' font-size='10' fill='#4b5563'>%s</text>"
                 % (name_w + pw + 4, y + 12, '{:,}'.format(r['pupils'])))
        x = bar_x
        for key, _, colour in FUND_PARTS:
            seg = bar_w * r[key] / max_spend
            if seg > 0.5:
                o.append("<rect x='%.1f' y='%.1f' width='%.1f' height='14' fill='%s'/>"
                         % (x, y + 1, seg, colour))
            x += seg
        o.append("<text x='%.1f' y='%.1f' font-size='10.5' font-weight='%d' fill='#111827'>"
                 "%s</text>" % (x + 5, y + 12, 700 if me else 400, usd(r['per_pupil'])))
    o.append("<text x='10' y='%d' font-size='10.5' fill='#6b7280'>The four parts sum exactly "
             "to what each district spends per pupil. What a town decides is the last one.</text>"
             % (H - 14))
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

    # THE TITLE IS FOUR LINES ON A PHONE, and it was. `How Lunenburg compares: neighbours,
    # peers, look-alikes and destinations` is a table of contents, not a name -- it lists the
    # sections instead of saying what the page is for. This says what a reader came to find
    # out, in six words, and the sections still announce themselves as headings.
    w('# Towns like us: what they pay, what they spend')
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
    # ONE CONTINUOUS REPORT, NO FOLD. TJ: *"for now make this one big report, no short and
    # long sections."* `Analysis.tsx` splits a document into a short version and a collapsed
    # remainder when its FIRST heading matches a known set -- `The short version`, `What this
    # establishes`, and three others. The summary is worth keeping; the split is not, on a
    # report whose argument runs the whole way down. So the heading is deliberately one the
    # matcher does not know.
    w('## What this report found')
    w('')
    for c in P['conclusions']:
        w('- **%s** %s' % (c['claim'], c['so_what']))
    w('')

    G = P['cheap_and_generous']
    w('![%s](charts/towns-like-us-positions.svg)'
      % ('Twelve measures, each drawn as the full spread of the %d Massachusetts towns that '
         'run their own K\u201312 district, with Lunenburg marked and the middle half of '
         'towns shaded. It is %s of %d on spending per pupil and %s of %d on the average tax '
         'bill.' % (P['distributions'][0]['n'],
                    ordinal([d for d in P['distributions'] if d['key'] == 'per_pupil'][0]['rank']),
                    P['distributions'][0]['n'],
                    ordinal([d for d in P['distributions'] if d['key'] == 'bill'][0]['rank']),
                    P['distributions'][0]['n'])))
    w('')
    w('![%s](charts/towns-like-us-funding.svg)'
      % ('For each town, how many pupils it has and what it spends on each of them, split '
         'into what the town must raise from homes, what it raises from business, what the '
         'state adds, and what it spends above the figure the state calculates for it.'))
    w('')
    w('## Can a town fund its schools well without taxing its residents? Only %d of %d can '
      '\u2014 and here is how' % (len(G['towns']), G['n']))
    w('')
    w('This is the question underneath every comparison anybody makes, so it goes first. '
      'Take the cheapest quarter of these %d towns by average single-family tax bill \u2014 '
      '**%s or less** \u2014 and the top quarter by spending per pupil \u2014 **%s or '
      'more**. %d towns are in both.'
      % (G['n'], money(G['cheap_cut']), money(G['spend_cut']), len(G['towns'])))
    w('')
    w('| Town | Average tax bill on a home | Spent per pupil | State money per child | '
      'Homes per pupil | How |')
    w('|---|---:|---:|---:|---:|---|')
    how_words = {'the state': 'the state pays', 'houses': 'a great many houses per child',
                 'both': 'the state pays, and many houses per child',
                 'unexplained': '**neither \u2014 unexplained**'}
    for r in G['towns']:
        w('| %s | %s | %s | %s | %.1f | %s |'
          % (r['town'], money(r['bill']), money(r['pp']), money(r['state_pp']),
             r['homes_per_pupil'], how_words[r['how']]))
    w('| **Lunenburg** | **%s** | **%s** | **%s** | **%.1f** | \u2014 |'
      % (money(G['lun']['bill']), money(G['lun']['pp']), money(G['lun']['state_pp']),
         G['lun']['homes_per_pupil']))
    w('')
    w('**There are exactly two ways, and Lunenburg has neither.** %d of the %d are among the '
      'communities where the state\u2019s own formula finds the least LOCAL EFFORT '
      'available \u2014 Chapter 70 measures a town by its equalized property valuation and '
      'its residents\u2019 income, and covers what those two cannot reach: the state puts '
      'in a median of %s per child across them, against %s for the '
      'middle town here. The other %d are resort and retirement towns \u2014 a great many '
      'houses, very few children \u2014 so a modest bill spread over %.1f homes per pupil '
      'still raises a great deal for each child. None of the %d is doing something a town '
      'could simply decide to do.'
      % (G['by_state'], len(G['towns']),
         money(P['their_state_median']), money(G['med_state']), G['by_houses'],
         max(r['homes_per_pupil'] for r in G['towns']), len(G['towns'])))
    w('')
    B = G.get('band')
    if B:
        w('**And business base is not a third way \u2014 which is worth saying plainly, '
          'because it is the lever people reach for first.** Tested on the same rule as the '
          'other two (twice the frame\u2019s median share of the tax base, %s), **%d of the '
          '%d** qualify. Nor does it do much quietly: among the %d towns whose average home '
          'is between %s and %s \u2014 the band Lunenburg\u2019s %s sits in \u2014 those '
          'with more business than the median charge %s against %s and spend %s per pupil '
          'against %s. Real, and small. The town\u2019s own assessor put the same question '
          'a different way and got %s a year.'
          % (pct(G['med_cip'], 1), G['by_business'], len(G['towns']), B['n'],
             money(B['lo']), money(B['hi']), money(L['value']),
             money(B['bill_more']), money(B['bill_less']),
             money(B['pp_more']), money(B['pp_less']), usd2(CLASSIFICATION['saving'])))
        w('')
    w('*What this does not show.* Anything about what those schools achieve \u2014 there is '
      'no outcome measure in this report. And being carried by the state is not an enviable '
      'position: it follows from having among the least property value and income behind '
      'each child in Massachusetts, with everything else that comes with that. What the table rules OUT is the hope that some town has found '
      'a third way. Within these %d, none has.' % G['n'])
    w('')

    C2 = P['commercial']
    HM = P['heatmap']
    w('## The whole state, one measure at a time')
    w('')
    # THE CAPTION HAS TO DESCRIBE BOTH SCALES, and the figures that justify each one are
    # derived rather than typed -- rule 2. The worked case is the most skewed measure on the
    # map, found by asking which one has the widest top-to-Lunenburg ratio rather than by
    # somebody remembering which it was.
    def _skew(mm):
        vals = [v for v in mm['values'].values() if v is not None]
        me = mm['values'].get('Lunenburg')
        return (max(vals) / me) if (vals and me) else 0.0
    worst = max(HM['measures'], key=_skew)
    wv = worst['values']
    wtop = max((v, t) for t, v in wv.items() if v is not None)
    wsecond = sorted((v for v in wv.values() if v is not None), reverse=True)[1]
    w('Every Massachusetts town, shaded by whichever measure you choose \u2014 %d of them, '
      'from what a home is taxed to what a district spends to what the state sends. '
      'Lunenburg is outlined in red, and every comparison town keeps its own coloured '
      'border whatever is being shaded.' % len(HM['measures']))
    w('')
    w('**Two ways to shade it, and they answer different questions.** By RANK, each shade '
      'holds the same number of towns, so the map shows which towns sit together \u2014 at '
      'the cost of every magnitude, because the step from 1st to 2nd looks like the step '
      'from 200th to 201st. By AMOUNT, each shade holds the same width of the range, so the '
      'magnitudes survive and the SKEW becomes the picture. On %s that is the finding: %s is '
      '%s and %s is %s against Lunenburg\u2019s %s, so shading by amount puts two towns at '
      'the dark end and leaves everywhere anybody lives one pale block. That is not a fault '
      'in the drawing \u2014 it is what the distribution looks like. The printed image below '
      'is the rank version; the page lets you switch.'
      % (worst['label'].lower(), wtop[1], fmt_kind(wtop[0], worst['kind']),
         [t for t, v in wv.items() if v == wsecond][0], fmt_kind(wsecond, worst['kind']),
         fmt_kind(wv['Lunenburg'], worst['kind'])))
    w('')
    w('![%s](charts/towns-like-us-heat.svg)'
      % ('Every Massachusetts town shaded by what its schools spend per pupil, darkest where '
         'it is highest, with Lunenburg outlined in red. Towns that do not run their own '
         'K\u201312 district are left blank.'))
    w('')

    PR = P['predictors']
    w('## What actually predicts how much a district spends on each pupil')
    w('')
    w('Twelve things, each tested against spending per pupil across all %d towns that run '
      'their own K\u201312 school, ranked by how much of the difference between districts '
      'each one accounts for.' % PR['n'])
    w('')
    w('| What was tested | Correlation | Accounts for |')
    w('|---|---:|---:|')
    for d in PR['single']:
        w('| %s | %+.2f | %s |' % (d['label'], d['r'], pct(d['explains'], 0)))
    w('')
    w('**It is wealth per child, and it is not close.** The next three rows are the same '
      'thing measured differently \u2014 home value, business value and income are what '
      'taxable value is made of. What is NOT in it: how much the state sends (%s), how many '
      'pupils a district has (%s), the share of children from low-income families (%s), and '
      'how much of the tax base is business (%s).'
      % (pct([d for d in PR['single'] if d['key'] == 'state_pp'][0]['explains'], 0),
         pct([d for d in PR['single'] if d['key'] == 'size'][0]['explains'], 0),
         pct([d for d in PR['single'] if d['key'] == 'low_income'][0]['explains'], 0),
         pct([d for d in PR['single'] if d['key'] == 'business_share'][0]['explains'], 0)))
    w('')
    w('**And the most important number is the one that is missing.** Put the five strongest '
      'together and they account for **%s** of the difference between districts. So **%s of '
      'what separates a district spending the most from one spending the least is none of '
      'wealth, aid, size, poverty or tax base.**'
      % (pct(PR['explained_together'], 0), pct(PR['unexplained'], 0)))
    w('')
    w('*What this does not show.* Which way any of it runs, and what that %s IS. A town with '
      'more wealth behind each child may spend more because it can, or may have attracted '
      'that wealth by spending more; one year read across many towns cannot separate them. '
      'And the unexplained share is NOT evidence of choice \u2014 it is the absence of '
      'evidence for the four explanations people reach for. Special education caseload, debt '
      'service, contract history and regional structure are all candidates this report does '
      'not hold.' % pct(PR['unexplained'], 0))
    w('')

    A = P['above_requirement']
    w('## Where the money above the state\u2019s figure actually comes from')
    w('')
    w('The chart above splits spending by the state\u2019s formula \u2014 what a town is '
      'REQUIRED to raise and what the state adds. It cannot say where the rest comes from, '
      'and it should not be read as though it could. This can, for the districts where DESE '
      'publishes actual net school spending for FY%d.' % P['fy'])
    w('')
    w('| District | Pupils | Spent per pupil, all funds | Required of it per pupil | '
      'Appropriated ABOVE the requirement | From outside the school budget | Actual against '
      'required |')
    w('|---|---:|---:|---:|---:|---:|---:|')
    for r in A:
        w('| %s%s | %s | %s | %s | %s | %s | %.2fx |'
          % (r['district'], ' *(regional)*' if r['regional'] else '',
             '{:,}'.format(r['pupils']), money(r['all_funds_pp']),
             money(r['required_nss_pp']), money(r['above_requirement_pp']),
             money(r['outside_nss_pp']), r['multiple']))
    w('')
    lun_a = [r for r in A if r['district'] == 'Lunenburg']
    top_a = A[0]
    if lun_a:
        w('**Two different things, and both matter.** %s appropriates %s a pupil above what '
          'the state requires; Lunenburg appropriates %s. And %s brings in %s a pupil from '
          'outside the school appropriation entirely, against Lunenburg\u2019s %s \u2014 '
          'what THAT is gets its own section below, because an earlier draft of this '
          'sentence listed what it assumed was in it rather than what a file says.'
          % (top_a['district'], money(top_a['above_requirement_pp']),
             money(lun_a[0]['above_requirement_pp']), top_a['district'],
             money(top_a['outside_nss_pp']), money(lun_a[0]['outside_nss_pp'])))
        w('')
    w('*What this does not show.* What is inside that last column. Net school spending '
      'excludes transport, capital and most grants, so the figure is a mix and nothing here '
      'splits it. That needs DESE\u2019s End of Year Financial Report, which separates '
      'spending by fund \u2014 already the named remedy on the money-gaps row about funding '
      'sources. And actual net school spending is published statewide only through SY2022, '
      'so this table is the districts whose current figures this archive holds.')
    w('')

    RG = P['regional']
    w('## Does regionalising save money?')
    w('')
    w('It is the answer most often offered in this town, and it is argued on shared '
      'overhead \u2014 so the measure is administration per pupil, which DESE publishes on '
      'its own.')
    w('')
    w('| | Districts | Median administration per pupil | With instructional leadership | '
      'Median spent per pupil |')
    w('|---|---:|---:|---:|---:|')
    w('| Single-town districts | %d | %s | %s | %s |'
      % (RG['n_single'], money(RG['admin_single']), money(RG['overhead_single']),
         money(RG['total_single'])))
    w('| Regional districts | %d | %s | %s | %s |'
      % (RG['n_regional'], money(RG['admin_regional']), money(RG['overhead_regional']),
         money(RG['total_regional'])))
    w('| **Lunenburg** | | **%s** | **%s** | **%s** |'
      % (money(RG['lun_admin']), money(RG['lun_overhead']), money(L['pp'])))
    w('')
    w('**On administration they are not cheaper.** What does cut overhead is SIZE rather '
      'than structure, and only somewhat: the smallest quarter of districts (median %s '
      'pupils) spend %s a pupil on administration, the largest quarter (median %s) spend '
      '%s. Lunenburg already spends %s \u2014 %s of %d, well into the lean end \u2014 so '
      'there is little administrative saving here to harvest.'
      % ('{:,}'.format(RG['small_pupils']), money(RG['small_admin']),
         '{:,}'.format(RG['big_pupils']), money(RG['big_admin']),
         money(RG['lun_admin']), ordinal(RG['lun_rank']), RG['n']))
    w('')

    OU = P['outside']
    w('### And what IS the money outside the school budget?')
    w('')
    w('It is **grants and revolving funds**, and DESE publishes it. Its function-code file '
      'reports every district\u2019s spending split two ways at once \u2014 by what it buys, '
      'and by whether the general fund or a grant or revolving account paid for it.')
    w('')
    w('| District | Pupils | General fund | Grants and revolving | Per pupil | Share of its '
      'spending | Of which, teacher pay per pupil |')
    w('|---|---:|---:|---:|---:|---:|---:|')
    for r in OU:
        me = r['district'] == 'Lunenburg'
        w('| %s%s%s | %s | %s | %s | %s | %s | %s |'
          % ('**' if me else '', r['district'], '**' if me else '',
             '{:,}'.format(r['pupils']), money(r['general']), money(r['grants_revolving']),
             money(r['per_pupil']), pct(r['share'], 1), money(r['parts']['Teachers'])))
    w('')
    lun_o = [r for r in OU if r['district'] == 'Lunenburg']
    top_o = OU[0]
    if lun_o:
        w('**It reconciles, which is why it can be trusted.** Lunenburg\u2019s grants and '
          'revolving come to %s here; this report derives %s a completely different way, as '
          'all-funds spending less net school spending. Two files, two routes, the same '
          'answer.'
          % (money(lun_o[0]['grants_revolving']),
             money([r for r in P['above_requirement'] if r['district'] == 'Lunenburg'][0]
                   ['outside_nss_pp'] * lun_o[0]['pupils'])))
        w('')
        w('**And one line does most of the work.** %s charges %s a pupil of TEACHER salaries '
          'to grants and revolving accounts. Lunenburg charges %s. That single difference is '
          'most of the gap between what the two draw from outside their appropriations.'
          % (top_o['district'], money(top_o['parts']['Teachers']),
             money(lun_o[0]['parts']['Teachers'])))
        w('')
    w('*What this does not show, and it is the question the table raises.* WHICH fund. A '
      'grant is money won from outside; a revolving fund is money the district itself takes '
      'in and may spend without an appropriation. Two kinds are evidenced directly in this '
      'archive \u2014 the athletics revolving fund, whose cashbook is held, and school '
      'choice tuition RECEIVED, which is a cherry sheet line; others such as preschool, food '
      'service and rentals are the usual sort and are named as examples, not as a claim '
      'about any district\u2019s mix. This file does not separate them, '
      'so a district with a large school-choice intake looks identical here to one that '
      'writes successful grant applications, and those are not the same opportunity. '
      '[Registered](/what-we-cannot-answer), with DESE\u2019s End of Year Pupil and '
      'Financial Report as the document that would settle it.')
    w('')

    C3 = P['cherry']
    w('### The money a town can only get by being regional')
    w('')
    w('**%s in FY%d, to %d regional districts, and to no single-town district at all.** '
      'Regional school transportation is reimbursed under M.G.L. c.71 s.16C. It is a CHERRY '
      'SHEET line, not Chapter 70 \u2014 which is why nothing else in this report could see '
      'it, and why an earlier version of the page concluded too much from finding no saving '
      'in administration.'
      % (money(C3['statewide_transport']), C3['fy'], C3['n_regional']))
    w('')
    w('| Regional district | Transportation aid, FY%d | Pupils | Per pupil |' % C3['fy'])
    w('|---|---:|---:|---:|')
    for r in C3['local']:
        w('| %s | %s | %s | %s |'
          % (r['district'], money(r['amount']), '{:,}'.format(r['pupils']),
             money(r['per_pupil'])))
    w('| **Lunenburg** | **nothing \u2014 not eligible** | **%s** | **\u2014** |'
      % '{:,}'.format(round(L['fte'])))
    w('')
    w('**So the regionalisation argument is not empty.** What it is worth here is a question '
      'this report still cannot answer \u2014 a regional district also INCURS the transport '
      'costs it is reimbursed for, and what three towns would spend merged is not observable '
      'from what other towns spend today. But it is no longer true that nothing follows from '
      'being regional.')
    w('')
    w('**And the same file answers where some of the grant and revolving money comes from.** '
      'School choice tuition RECEIVED is a cherry sheet receipt and a revolving fund at the '
      'district. Lunenburg receives %s of it and pays out %s in sending tuition, plus %s in '
      'charter sending tuition \u2014 a net exporter of children and of money.'
      % (money(C3['lun_choice_in']), money(C3['lun_choice_out']),
         money(C3['lun_charter_out'])))
    w('')
    w('| Lunenburg, FY%d | Receipts | | Assessments |' % C3['fy'])
    w('|---|---:|---|---:|')
    rec = C3['lunenburg']['Receipts']
    ass = C3['lunenburg']['Assessments']
    for i in range(max(len(rec), len(ass))):
        a = rec[i] if i < len(rec) else None
        b = ass[i] if i < len(ass) else None
        w('| %s | %s | %s | %s |'
          % (a['line'] if a else '', money(a['amount']) if a else '',
             b['line'] if b else '', money(b['amount']) if b else ''))
    for k in ('Total Receipts', 'Total Assessments', 'Net Receipts'):
        if k in C3['totals']:
            w('| **%s** | **%s** | | |' % (k, money(C3['totals'][k])))
    w('')

    RM = P['regional_members']
    w('### If three towns share one school, what does each one put in?')
    w('')
    w('Chapter 70 is computed per TOWN, never per member of a district \u2014 so each '
      'town\u2019s obligation is published separately even where the children share one '
      'school system.')
    w('')
    w('| Regional district | Member town | Its children | It must raise per child | '
      'The state adds per child |')
    w('|---|---|---:|---:|---:|')
    for r in RM:
        for i, m in enumerate(r['members']):
            w('| %s | %s | %s | %s | %s |'
              % (r['district'] if i == 0 else '', m['town'],
                 '{:,}'.format(m['children']), money(m['required_pp']),
                 money(m['state_pp'])))
    w('| *Lunenburg, for scale* | *Lunenburg* | *%s* | *%s* | *%s* |'
      % ('{:,}'.format(P['effort']['Lunenburg']['children']
                       if 'children' in P['effort']['Lunenburg'] else 0)
         if False else '{:,}'.format(round(L['fte'])),
         money(P['effort']['Lunenburg']['required_pp']),
         money(P['effort']['Lunenburg']['state_pp'])))
    w('')
    w('**Regionalising does not change Chapter 70.** The formula is computed per '
      'MUNICIPALITY from that town\u2019s equalized property valuation and its '
      'residents\u2019 income, and the district\u2019s figure is the sum of its '
      'members\u2019. Ashby\u2019s obligation is Ashby\u2019s whether it belongs to a '
      'regional district or not, and joining one would not move it. Any state money that '
      'DOES follow from being regional is a different line \u2014 the transportation '
      'reimbursement under c.71 s.16C, which is a cherry sheet item and not Chapter 70. '
      'This project holds no cherry sheet data, so it cannot measure that, and it is '
      '[registered](/what-we-cannot-answer) as the gap it is rather than argued either way.')
    w('')
    w('**What is NOT published is the assessment** \u2014 what each town actually votes to '
      'pay the district. That is fixed by the regional agreement and voted town meeting by '
      'town meeting, and it is the one link in the chain no statewide file carries.')
    w('')
    w('**And the member towns do not add up to their district, which is the useful part.** '
      'Summing them gives %s to %s of the district\u2019s own figure, because a town\u2019s '
      'Chapter 70 covers ALL of its children \u2014 including those at a vocational school, '
      'a charter or another district by choice \u2014 while the district\u2019s covers only '
      'the ones it teaches. The proof that this is the explanation rather than an error: '
      'within each district the required and foundation ratios are the same number to a '
      'tenth of a point, which is what happens when one factor scales both. This report '
      'refuses to build if they ever drift apart.'
      % (pct(min(r['required_ratio'] for r in RM), 1),
         pct(max(r['required_ratio'] for r in RM), 1)))
    w('')

    w('## How big is their business base, and what would Lunenburg need to match it?')
    w('')
    w('The commercial argument is usually made in SHARES, and shares answer the wrong '
      'question. Westford is within a point of Lunenburg on share \u2014 %s against %s '
      '\u2014 while its business base is **%s larger**, because Westford is a far bigger '
      'town. A school budget spends dollars, so this is in dollars, and per pupil, so a town '
      'with three times the children is not credited for three times the base.'
      % (pct([r for r in C2['towns'] if r['town'] == 'Westford'][0]['share'], 1)
         if any(r['town'] == 'Westford' for r in C2['towns']) else 'n/a',
         pct(C2['lun_share'], 1),
         money([r for r in C2['towns'] if r['town'] == 'Westford'][0]['vs_lunenburg'])
         if any(r['town'] == 'Westford' for r in C2['towns']) else 'n/a'))
    w('')
    w('| Town | Business, industrial and personal value | Share of its tax base | Per pupil | '
      'Levy it pays at %s per $1,000 | Against Lunenburg |' % usd2(C2['rate']))
    w('|---|---:|---:|---:|---:|---:|')
    for r in C2['towns']:
        w('| %s%s | %s | %s | %s | %s | %s |'
          % ('**' if r['town'] == 'Lunenburg' else '', r['town']
             + ('**' if r['town'] == 'Lunenburg' else ''),
             money(r['business']), pct(r['share'], 1), money(r['per_pupil']),
             money(r['levy']),
             '\u2014' if r['town'] == 'Lunenburg'
             else ('%s%s' % ('+' if r['vs_lunenburg'] > 0 else '\u2212',
                             money(abs(r['vs_lunenburg']))))))
    w('')
    w('**What Lunenburg would need.** Its business base is %s per pupil against a median of '
      '%s across the %d towns. Reaching that median means **%s of new business value** '
      '\u2014 worth about **%s a year** of levy at the current rate. Lunenburg\u2019s '
      'assessors certify a median of %s of NEW GROWTH of every kind each year, so that is '
      'roughly **%s years if every dollar of growth were commercial**, and most of it is '
      'housing. Treat the figure as a floor on the time, not an estimate of it.'
      % (money(C2['lun_per_pupil']), money(C2['median_per_pupil']), C2['n'],
         money(C2['need_to_reach_median']), money(C2['levy_if_matched']),
         money(C2['pace']), '%.0f' % C2['years_at_pace']))
    w('')
    w('**And that is the right size to judge it by.** %s a year of extra levy capacity is '
      'roughly the size of the gaps this town argues about \u2014 so commercial growth is a '
      'credible answer to *how do we stop running deficits* and is not an answer to *how do '
      'I pay less*. The two get argued as one thing. They are not: what growth buys is room '
      'under the levy limit, and the town\u2019s own assessor priced the other question '
      '\u2014 shifting tax onto the business already here \u2014 at %s a year.'
      % (money(C2['levy_if_matched']), usd2(CLASSIFICATION['saving'])))
    w('')
    w('*What this does not show.* Whether that development is wanted, what it would cost in '
      'services, roads and schools of its own, or where it would go. This is arithmetic on '
      'the tax base and nothing else. `/commercial-development` translates the same '
      'quantity into buildings at the town\u2019s own archetype values \u2014 see '
      '[what commercial growth would have to look like](/commercial-development).')
    w('')

    w('## The towns most like Lunenburg, and how they differ')
    w('')
    w('Picked by the math out of all %d, on eight things a town does not choose: how many '
      'children it has, how many are from low-income families, are learning English or have '
      'a disability, how many are schooled outside the district, what the average house is '
      'worth, income per head, and how much of the tax base is business. Tax bills and '
      'spending are deliberately kept OUT of the matching, so they can be compared '
      'afterwards rather than assumed.' % G['n'])
    w('')
    near = [v for v in P['verdicts'] if v['role'] == 'structural'][:3]
    for v in near:
        w('**%s**' % v['town'])
        if v.get('same'):
            w('')
            w('*Like Lunenburg:* %s.' % '; '.join(v['same']))
        w('')
        w('*Different:* %s%s' % (v['tail'][0].upper(), v['tail'][1:]))
        for reason in v['why']:
            w('  %s' % reason)
        w('')
    w('')

    w('## What other districts do that Lunenburg does not \u2014 and how we know')
    w('')
    w('Five things a comparison like this is usually used to argue for. Each one says where '
      'Lunenburg actually sits, whether it is something the town could DECIDE, and how much '
      'the data will carry. Two of the five turn out to be things Lunenburg already has.')
    w('')
    for lv in P['levers']:
        w('### %s' % lv['what'])
        w('')
        w('%s' % lv['lunenburg'])
        w('')
        w('*Is it a decision?* %s  *How sure?* **%s** \u2014 %s'
          % ('Yes, the town could choose differently.' if lv['chooseable']
             else 'No. This is circumstance, not policy.',
             lv['confidence'], lv['evidence']))
        w('')
        w('*%s*' % lv['caveat'])
        w('')

    w('## Town by town: do they pay more or less, and do they spend more or less?')
    w('')
    w('Every town this report compares, sorted into four plain groups. \u201cPays\u201d is '
      'the average single-family property tax bill. \u201cSpends\u201d is dollars per pupil '
      'from all funds. Neither is a verdict \u2014 a town that spends less may be run leanly '
      'or may be short of what its children need, and nothing here can tell those apart.')
    w('')
    order = ['pays-less-spends-more', 'pays-more-spends-more', 'pays-less-spends-less',
             'pays-more-spends-less', 'regional']
    labels = {v['quadrant']: v['quadrant_label'] for v in P['verdicts']}
    for q in order:
        rows_q = [v for v in P['verdicts'] if v['quadrant'] == q and v['town'] != 'Lunenburg']
        if not rows_q:
            continue
        if q == 'regional':
            # THE REGIONAL TOWNS GET THE SAME ARITHMETIC, at the level it is published.
            # An earlier version of this section said the question could not be asked of
            # them at all -- which was asking it at the wrong level, not an absence.
            w('### The %d in regional districts \u2014 and how they do it' % len(rows_q))
            w('')
            w('%s are in REGIONAL districts, so no spending figure belongs to any one of '
              'them: the money is assessed across member towns with different tax bills and '
              'separate votes. But Chapter 70 is computed per TOWN whatever district its '
              'children attend, so what each is REQUIRED to raise per child, and what the '
              'state adds per child, are published for them exactly as for Lunenburg. '
              'Lunenburg is required to raise %s per child and the state adds %s.'
              % (', '.join(sorted(v['town'] for v in rows_q)),
                 usd(P['effort']['Lunenburg']['required_pp']),
                 usd(P['effort']['Lunenburg']['state_pp'])))
            w('')
            for v in sorted(rows_q, key=lambda r: -(r['required_pp'] or 0)):
                w('**%s** \u2014 %s' % (v['town'], v['tail']))
                w('')
            w('What stays unknowable is only the middle step: how a regional '
              'district\u2019s assessment is apportioned between its member towns. That is '
              'a narrower gap than it looked like, and it is [registered]'
              '(/what-we-cannot-answer) with the document that would close it.')
            w('')
            continue
        w('### %s than Lunenburg' % labels[q])
        w('')
        for v in sorted(rows_q, key=lambda r: -abs(r['pp_diff'])):
            w('**%s** \u2014 %s' % (v['town'], v['tail']))
            for reason in v['why']:
                w('  %s' % reason)
            w('')

    w('## The towns Lunenburg borders, and the towns it is compared with')
    w('')
    w('Six neighbours, computed from the Census boundary polygons by shared vertices rather '
      'than from memory. Five peers, which are this project’s own choice — nothing '
      'in the town’s record names a cohort.')
    w('')
    w('| Town | Why it is here | School district | Average single-family tax bill, FY%d | '
      'Where that bill ranks among the 351 Massachusetts towns (1 = highest) | That bill as '
      'a share of income per head | Spending per pupil, all funds, SY%d | Share of the tax '
      'base that is business rather than housing | Overrides won of those put to voters |'
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
    w('## \u201cA town like ours\u201d, one measure at a time')
    w('')
    w('The two cohorts below have no town in common, which is a true finding and a useless '
      'one by itself: it says the question is ill-posed without saying what to ask instead. '
      'So here is what to ask instead \u2014 the three nearest towns on each measure '
      'SEPARATELY. Nearest is plain difference on the measure itself: no weighting, nothing '
      'to argue with. Somebody arguing about school spending should reach for a different '
      'row from somebody arguing about tax bills.')
    w('')
    w('| On this measure | Lunenburg | The three nearest towns |')
    w('|---|---:|---|')
    for d in P['by_dimension']:
        w('| %s | %s | %s |'
          % (d['label'][0].upper() + d['label'][1:], d['lunenburg'],
             ', '.join('%s (%s)' % (t['town'], t['value']) for t in d['towns'])))
    w('')
    w('**Almost nothing repeats down that column.** A town that matches Lunenburg on how '
      'many children it has is not the town that matches it on what those children\u2019s '
      'schools spend, and neither is the town that matches it on the tax bill. That is the '
      'honest reason \u201ccomparable communities\u201d has to be said with a measure '
      'attached \u2014 and the reason the town not publishing one of its own is a real gap '
      'rather than a pedantic complaint.')
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
    w('| Town | Which list | How far from Lunenburg (0 = identical) | Average '
      'single-family tax bill, FY%d | Spending per pupil, all funds, SY%d | Share of the tax '
      'base that is business | Overrides won of those put | Change in pupils since SY%d |'
      % (P['fy'], P['sy'], P['base_sy']))
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

    w('## This is a conversation the town is already having')
    w('')
    w('Lunenburg\u2019s own Budget Task Force spent part of its meeting of 19 August 2024 on '
      'exactly this comparison \u2014 per-pupil expenditure as the measure to judge the '
      'district by, set against other districts, and where Lunenburg\u2019s teacher pay sits '
      'in that range. There are no written minutes of that passage in the archive; what '
      'exists is the recording, and it is linked here rather than quoted because the only '
      'transcript is machine captions. A caption model hears \u201cfifteen hundred\u201d, '
      '\u201c$1,500\u201d and \u201c$50\u201d alike, so no figure from it may be repeated '
      'as something the meeting said.')
    w('')
    w('- [The Budget Task Force, 19 August 2024, at 1:26:24]'
      '(https://www.youtube.com/watch?v=l_64JaMrAzA&t=5184s)')
    w('')
    w('This report does not introduce the question. It gives the same question a published '
      'denominator: %d towns that run their own K\u201312 district, matched to Lunenburg by '
      'the things a town does not choose, rather than a handful picked to make a point.'
      % P['frame_size'])
    w('')
    w('## The questions this report could not answer, and what would answer them')
    w('')
    w('Each of these stopped a conclusion. They are registered in '
      '`sources/data/money-gaps.csv` and appear on [what we cannot '
      'answer](/what-we-cannot-answer), so the next person to hit the same wall finds them '
      'rather than describing them again in different words.')
    w('')
    w('| The question | Why it stops here | The one document that would settle it |')
    w('|---|---|---|')
    for q, why, doc in (
        ('What does Lunenburg actually appropriate above the state\u2019s minimum, year by '
         'year, beside the same for comparable towns?',
         'The required local contribution is a floor and this report measures one year of '
         'the gap above it. The gap over time is the whole decision and is not assembled '
         'anywhere.',
         'DESE\u2019s net school spending series per district \u2014 published statewide '
         'only through SY2022, and held here for FY%d for six local districts.' % P['fy']),
        ('Which fund pays the teacher salaries a district charges to grants and revolving '
         'accounts?',
         'Harvard charges %s a pupil of teacher pay to grants and revolving where Lunenburg '
         'charges %s. Part is non-resident tuition \u2014 Harvard teaches 187 children its '
         'town is not funded for, 90 of them from Devens \u2014 but that does not account '
         'for the size of it.'
         % (money([r for r in P['outside'] if r['district'] == 'Harvard'][0]['parts']['Teachers']),
            money([r for r in P['outside'] if r['district'] == 'Lunenburg'][0]['parts']['Teachers'])),
         'DESE\u2019s End of Year Pupil and Financial Report, which reports spending by '
         'individual fund.'),
        ('What would regionalising be worth to Lunenburg, once the transport reimbursement '
         'is set against the transport costs it would take on?',
         'The reimbursement side is now measured \u2014 %s statewide, nothing to a '
         'single-town district. The cost side is not: no published figure separates a '
         'district\u2019s busing cost from its reimbursement, and what three towns would '
         'spend merged is not what other merged towns spend today.'
         % money(P['cherry']['statewide_transport']),
         'The regional districts\u2019 own budgets, which state transport as a line against '
         'its reimbursement; and a regional agreement, which sets how the net is apportioned.'),
        ('How does a regional district divide its assessment between member towns, and what '
         'does each actually appropriate?',
         'Chapter 70 is published per town, so what each member is REQUIRED to raise is '
         'known. The assessment \u2014 what each town votes to pay the district \u2014 is '
         'the one link no statewide file carries.',
         'Each regional district\u2019s annual assessment schedule, voted by its member '
         'towns and filed with DESE.'),
        ('Which towns does Lunenburg consider comparable to itself?',
         'Nothing the town has published names a cohort. A 2023 Finance Committee minute '
         'cites \u201cthe 8 communities that were surveyed\u201d for a salary study and '
         'never lists them. Every \u201ccompared with similar towns\u201d claim, including '
         'this report\u2019s, rests on a set nobody has agreed.',
         'The eight-community list behind the 2023 salary survey, held by the Town '
         'Administrator or the bargaining unit that commissioned it.'),
        ('What does each place a Lunenburg child is schooled outside the district actually '
         'cost the town?',
         'DESE publishes where %d children go and nothing about what any of them costs. A '
         'count of children is not a tuition or an assessment share.'
         % sum(d['students'] for d in P['destinations'] if d['kind'] != 'own'),
         'DESE\u2019s End of Year Financial Report, which separates tuition and assessment '
         'spending by fund and receiving district.'),
    ):
        w('| %s | %s | %s |' % (q, why, doc))
    w('')
    w('**Five of the six name a document that exists and is not in this archive.** That is '
      'the useful form of a gap: a records request rather than a grievance. The sixth '
      '\u2014 what regionalising would be worth here \u2014 is the only one where no '
      'document would settle it, because the question is about a future nobody has '
      'observed.')
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
    w('## What the figures count')
    w('')
    w('%s' % P['grain'])
    w('')
    w('*This also appears at the top of the web version of this report, because a reader '
      'who is about to quote a figure needs it before they scroll. Here it sits with the '
      'method, where somebody reading the whole document will look for it.*')
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
            os.path.join(CHARTS, 'towns-like-us-funding.svg'): funding_svg(payload),
            os.path.join(CHARTS, 'towns-like-us-positions.svg'): positions_svg(payload),
            os.path.join(CHARTS, 'towns-like-us-heat.svg'): heat_svg(payload),
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
