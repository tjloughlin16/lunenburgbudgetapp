#!/usr/bin/env python3
"""WHO ACTUALLY LIVES IN LUNENBURG -- age, households, income by age, and tenure.

    python3 scripts/build_lunenburg_by_the_numbers.py
    python3 scripts/build_lunenburg_by_the_numbers.py --check

Writes `fy28/public/data/lunenburg-by-the-numbers.json`, which /lunenburg-by-the-numbers
renders. Every figure is recomputed from `census_acs` in the database and, by a second
route straight off the CSV, in scripts/verify_lunenburg_by_the_numbers.py.

WHY THIS PAGE EXISTS. The override argument in this town runs on two claims about people
-- that seniors on fixed incomes cannot carry it, and that schools serve about 30% of
homes -- and until the Census tables were fetched this project could check neither. It
held DESE's detail on 1,568 children and effectively nothing about the other ten thousand
residents. So the two groups whose interests are weighed against each other in public were
one measured in depth and one not measured at all, and that asymmetry has shaped every
argument in town without anybody naming it. `money_gaps` registered exactly that, and
named these tables as what would close it.

THE TWO TRAPS THIS PAGE LIVES OR DIES ON, both asserted here rather than avoided by care.

1.  EVERY FIGURE IS A SAMPLE ESTIMATE WITH A MARGIN, AND THE MARGINS ARE WIDE. A DESE
    enrolment count is a census of children: 1,568 means 1,568. ACS for a town of 11,804
    is a small sample -- households with a child under 18 is 1,477 +/- 198. So every
    figure this page publishes carries its margin, aggregates carry the root of the sum
    of squares rather than one band's margin, and `moe_text` is built beside every
    estimate so a page cannot render one without the other.

    The Census's own sentinels are not numbers and are never printed as numbers:
    -666666666 means the estimate is not available, -222222222 and -333333333 mean no
    margin could be computed, and -555555555 means the estimate is CONTROLLED to an
    independent total and has no sampling error -- which is not a margin of zero. The
    loader nulls them; this refuses to publish a figure it cannot state a margin for.

2.  THE RANK IS NOT THE FACT. THE BAND IS. Lunenburg's median household income computes
    to rank 167 of 350 Massachusetts municipalities, and 205 of those 350 have an
    interval that overlaps Lunenburg's. So the rank is arithmetic and nearly meaningless
    as a ranking, and the honest, stronger claim is that the town's income is
    statistically indistinguishable from most of the state. BOTH are computed here and
    published together, because a rank printed without its overlap count is precisely the
    false precision this page exists to avoid, and it would be us doing it.

RULE 7 ON EVERY SENTENCE. That 16.8% of residents are 65 or over is a measurement. What
that implies about how they vote, what they can afford beyond the income table, or what
they want, is not -- and none of it is here.

RULE 8. This is not an argument and not an audit. The senior-versus-family split is the
axis the override argument runs on, and the page hands both sides the same numbers. Where
the town's own rough claim turns out to be about right -- "about 30% of homes" against a
measured 32.6% -- it says so.

RULE 11 APPLIES SIDEWAYS. Nothing on this page is a budget line, so the net-versus-gross
trap does not arise; the one dollar figure that meets a budget figure is the per-pupil
comparison, and it is a DESE all-district statistic rather than an appropriation.

RULE 1 IS WHY THERE IS NO REAL-TERMS ANYTHING. This archive holds no price index, so no
figure here is deflated and no income is described as having risen or fallen in real
terms. Two nominal medians five years apart, both estimates, and the page says so.
"""
import argparse
import csv
import json
import math
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import conclusions as C                                              # noqa: E402
from conclusions import conclusion, emit, figure                     # noqa: E402
from build_special_education import (                                # noqa: E402
    MINUTES, ROOT, archive, coverage, fail,
)

DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
CSV = os.path.join(ROOT, 'sources', 'data', 'census-acs.csv')
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')
OUT = os.path.join(PUB, 'lunenburg-by-the-numbers.json')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
DOCS = os.path.join(ROOT, 'fy28', 'public', 'docs')

LEA = '01620000'
NEW, OLD = 2023, 2018                 # the two 5-year releases, which do not overlap
WINDOW = {2023: '2019–2023', 2018: '2014–2018'}

# B01001 is sex by age, and the variable numbers ARE the age bands. Male 003-025 and
# female 027-049 run through the same 23 bands in the same order, which is why the bands
# are declared once and each carries its pair. Nothing here is read off a label: the
# source publishes no label column, so the mapping is declared, asserted against the
# table's own total, and the assertion is what makes it checkable.
AGE_BANDS = [
    ('under 5', 5, 3), ('5 to 9', 10, 4), ('10 to 14', 15, 5), ('15 to 17', 18, 6),
    ('18 and 19', 20, 7), ('20', 21, 8), ('21', 22, 9), ('22 to 24', 25, 10),
    ('25 to 29', 30, 11), ('30 to 34', 35, 12), ('35 to 39', 40, 13),
    ('40 to 44', 45, 14), ('45 to 49', 50, 15), ('50 to 54', 55, 16),
    ('55 to 59', 60, 17), ('60 and 61', 62, 18), ('62 to 64', 65, 19),
    ('65 and 66', 67, 20), ('67 to 69', 70, 21), ('70 to 74', 75, 22),
    ('75 to 79', 80, 23), ('80 to 84', 85, 24), ('85 and over', 200, 25),
]
FEMALE_OFFSET = 24                    # male 003 and female 027 are the same band

# The five groups the page draws. Upper bound is exclusive and comes off the band table
# above, so a band cannot be in two groups and none can be left out -- asserted below.
AGE_GROUPS = [
    ('children', 'Under 18', 0, 18),
    ('young', '18 to 24', 18, 25),
    ('early', '25 to 44', 25, 45),
    ('middle', '45 to 64', 45, 65),
    ('senior', '65 and over', 65, 999),
]

INCOME_AGES = [
    ('B19049_002E', 'Under 25'),
    ('B19049_003E', '25 to 44'),
    ('B19049_004E', '45 to 64'),
    ('B19049_005E', '65 and over'),
]

# WHAT THE TOWN SAID, rule 15a. Re-read out of the extracted minutes on every run; a miss
# is fatal. None of these is a measurement -- each is what somebody said about who lives
# here, placed beside the figures that bear on it.
QUOTES = [
    dict(key='fixed-incomes', board='finance-committee', date='2026-01-27',
         kind='minutes', doc='7619',
         quote='particularly seniors on fixed incomes, a $3,000,000 override would '
               'translate to approximately $600 per year in additional taxes, a '
               'significant burden',
         why='A Finance Committee member at the Tri-Board meeting, on whether an override '
             'is necessary. This is the claim the income-by-age table can finally be set '
             'beside: a household headed by someone 65 or over has a median income a '
             'little over half that of a 45-to-64 household. It establishes what was '
             'said. It does not establish what any particular household can afford, '
             'which no table here measures.'),
    dict(key='both-halves', board='master-plan-steering-committee', date='2024-04-05',
         kind='minutes', doc='6494',
         quote='young families are looking for smaller houses with some land, but '
               'developers are building large houses that young families cannot afford',
         why='The Master Plan Steering Committee, in the same minute that records an '
             'aging population looking for accessible and affordable options. Both halves '
             'of the town appear in one paragraph, which is the shape this page is trying '
             'to keep: the same numbers handed to both sides.'),
]

SEARCHED = ['fixed income', 'seniors', 'young families', 'aging population',
            'census', 'town census']

# The limits already registered in `money-gaps.csv`, cited rather than restated -- rule
# 7c: the registry outranks the page. A row that has been renamed or removed fails the
# build, because a page citing a limit nobody else can see is a page whose caveat is
# invisible to everyone who did not read it.
GAP_WHAT = (
    'How many Lunenburg homes have a child in the LUNENBURG PUBLIC SCHOOLS — as opposed '
    'to a child under 18?',
    'Who actually lives in Lunenburg — how many are over 65, how many households have a '
    'child in the schools, and what each group can afford?',
    'How much of the property tax levy is paid by households headed by someone 65 or '
    'over?',
)

# A published table does not lose most of itself. If a query comes back short, something
# moved underneath it and writing the result would publish a truncated record as a whole
# one.
MIN_MUNICIPALITIES = 300
MIN_PEER_YEARS = 15


# ------------------------------------------------------------------ the estimates

def q(db, sql, *args):
    return db.execute(sql, args).fetchall()


def cells(db):
    """Every usable town estimate, keyed (vintage, variable) -> (estimate, margin).

    A row whose margin did not survive as a number is NOT loaded into this map. Every
    figure this page publishes has to be able to state its margin, and a sentinel read as
    a margin of zero is the single worst thing that could happen to this page.
    """
    out, sentinels = {}, []
    for v, var, est, moe, est_raw, moe_raw in q(db, """
            SELECT vintage, variable, estimate, moe, estimate_raw, moe_raw
            FROM census_acs WHERE level='town'"""):
        if est is None or moe is None:
            sentinels.append(dict(vintage=v, variable=var, estimate_raw=est_raw,
                                  moe_raw=moe_raw))
            continue
        out[(v, var)] = (float(est), float(moe))
    if not out:
        fail('census_acs returned no usable town estimate. A join that matches nothing '
             'looks exactly like a town nobody has measured')
    return out, sorted(sentinels, key=lambda r: (r['vintage'], r['variable']))


def one(cs, vintage, var, what):
    if (vintage, var) not in cs:
        fail('%s (%s, %s) is not a usable estimate with a margin, so it cannot be '
             'published' % (what, vintage, var))
    return cs[(vintage, var)]


def total(parts):
    """A sum of ACS cells, with the margin the Census's own method gives it.

    The margin of a sum is the ROOT OF THE SUM OF THE SQUARES of the parts' margins, not
    the sum of them and certainly not one of them. Twelve age cells summed to the
    65-and-over count give +/- 309, where the largest single band is +/- 212.
    """
    e = sum(p[0] for p in parts)
    return e, math.sqrt(sum(p[1] ** 2 for p in parts))


def ratio(sub, tot):
    """A share, as a percentage, with the margin the Census publishes the formula for.

    MOE(p) = sqrt(MOE(sub)^2 - p^2 * MOE(tot)^2) / tot, and where that radicand goes
    negative the Census says to use the ratio form with a PLUS. Both branches are here
    and `conservative` records which one was taken, because the second is the wider and a
    reader should be able to see that it was used.
    """
    p = sub[0] / tot[0]
    rad = sub[1] ** 2 - (p ** 2) * (tot[1] ** 2)
    if rad > 0:
        m = math.sqrt(rad) / tot[0]
        conservative = False
    else:
        m = math.sqrt(sub[1] ** 2 + (p ** 2) * (tot[1] ** 2)) / tot[0]
        conservative = True
    return p * 100.0, m * 100.0, conservative


def distinguishable(a, b):
    """Do two ACS estimates differ by more than their combined margin?

    The Census's own test for whether two estimates are different at all. The combined
    margin is the root of the sum of the squares; anything smaller than it is not a
    change, however confidently it could be written as one.
    """
    d = b[0] - a[0]
    m = math.sqrt(a[1] ** 2 + b[1] ** 2)
    return d, m, abs(d) > m


# ------------------------------------------------------------------ renderings

def n(x):
    return format(int(round(x)), ',d')


def usd(x):
    return C.usd(x)


def pm(est, moe, money=False):
    """An estimate and its margin, as one string. Nothing on this page renders an ACS
    figure without one."""
    f = usd if money else n
    return '%s ± %s' % (f(est), f(moe))


def pct(x, dp=1):
    return '%.*f%%' % (dp, x)


def est_row(label, pair, money=False):
    return dict(label=label, estimate=pair[0], moe=pair[1],
                text=pm(pair[0], pair[1], money),
                estimate_text=(usd if money else n)(pair[0]),
                moe_text=(usd if money else n)(pair[1]))


# ------------------------------------------------------------------ the age shape

def age_group_vars(lo, hi):
    """The B01001 variables in one age group, male and female, from the band table."""
    out = []
    prev = 0
    for _label, upper, male in AGE_BANDS:
        band_lo, band_hi = prev, upper
        prev = upper
        if band_lo >= lo and band_hi <= hi:
            out.append('B01001_%03dE' % male)
            out.append('B01001_%03dE' % (male + FEMALE_OFFSET))
    return out


def ages(cs, vintage):
    """The five age groups, each with its own margin, checked against the printed total.

    THE CHECK IS THE POINT. The band-to-variable mapping is declared in this file and
    read off no label, so the only thing that makes it trustworthy is that the five
    groups sum -- exactly, to the person -- to the total the table itself publishes. If
    the Census renumbers B01001 or a band is dropped from `AGE_GROUPS`, this fails rather
    than publishing a town with people missing from it.
    """
    pop = one(cs, vintage, 'B01001_001E', 'total population')
    groups, used = [], []
    for key, label, lo, hi in AGE_GROUPS:
        vs = age_group_vars(lo, hi)
        if not vs:
            fail('the age group %r selects no B01001 variable' % label)
        used += vs
        pair = total([one(cs, vintage, v, label) for v in vs])
        share = ratio(pair, pop)
        groups.append(dict(key=key, label=label, estimate=pair[0], moe=pair[1],
                           estimate_text=n(pair[0]), moe_text=n(pair[1]),
                           text=pm(pair[0], pair[1]), share=share[0], share_moe=share[1],
                           share_text=pct(share[0]), share_moe_text=pct(share[1]),
                           share_conservative=share[2], cells=len(vs)))
    if len(set(used)) != len(used):
        fail('an age band is in two groups at once, so the town would be counted twice')
    summed = sum(g['estimate'] for g in groups)
    if abs(summed - pop[0]) > 0.5:
        fail('the five age groups sum to %s and B01001 publishes %s for %s. The band '
             'mapping in this file no longer matches the table' % (n(summed), n(pop[0]),
                                                                   vintage))
    return dict(vintage=vintage, window=WINDOW[vintage],
                population=est_row('Population', pop), groups=groups)


# ------------------------------------------------------------------ households, income

def households(cs, vintage):
    hh = one(cs, vintage, 'B11005_001E', 'households')
    kid = one(cs, vintage, 'B11005_002E', 'households with a child under 18')
    nokid = one(cs, vintage, 'B11005_011E', 'households with no child under 18')
    share = ratio(kid, hh)
    summed = kid[0] + nokid[0]
    if abs(summed - hh[0]) > 0.5:
        fail('B11005: households with a child (%s) plus households without (%s) is %s, '
             'against a printed total of %s' % (n(kid[0]), n(nokid[0]), n(summed),
                                                n(hh[0])))
    return dict(vintage=vintage, window=WINDOW[vintage],
                households=est_row('Households', hh),
                with_child=est_row('With a child under 18', kid),
                without_child=est_row('With no child under 18', nokid),
                share=share[0], share_moe=share[1],
                share_text=pct(share[0]), share_moe_text=pct(share[1]))


def tenure(cs, vintage):
    occ = one(cs, vintage, 'B25003_001E', 'occupied housing units')
    own = one(cs, vintage, 'B25003_002E', 'owner-occupied')
    rent = one(cs, vintage, 'B25003_003E', 'renter-occupied')
    if abs(own[0] + rent[0] - occ[0]) > 0.5:
        fail('B25003: owners plus renters is %s against a printed total of %s'
             % (n(own[0] + rent[0]), n(occ[0])))
    share = ratio(own, occ)
    return dict(vintage=vintage, window=WINDOW[vintage],
                occupied=est_row('Occupied homes', occ),
                owner=est_row('Owner-occupied', own),
                renter=est_row('Renter-occupied', rent),
                owner_share=share[0], owner_share_moe=share[1],
                owner_share_text=pct(share[0]), owner_share_moe_text=pct(share[1]))


def income(db, cs, vintage):
    """Median household income overall, and by age of householder.

    A MEDIAN IS NOT A SUM, and nothing here adds one to another or averages the four age
    medians into the overall one -- they are four separate estimates of four separate
    distributions and the arithmetic that would combine them does not exist in this file.

    The under-25 band is published as a sentinel in both vintages, which is a real fact
    about the data and is carried as one: `unavailable` names the band and says why,
    rather than leaving a hole a reader would read as a zero.
    """
    allhh = one(cs, vintage, 'B19049_001E', 'median household income')
    rows, unavailable = [], []
    for var, label in INCOME_AGES:
        if (vintage, var) not in cs:
            raw = q(db, 'SELECT estimate_raw, moe_raw FROM census_acs WHERE vintage=? '
                        'AND variable=? AND level=?', vintage, var, 'town')
            unavailable.append(dict(label=label, variable=var,
                                    estimate_raw=raw[0][0] if raw else '',
                                    moe_raw=raw[0][1] if raw else ''))
            continue
        rows.append(est_row(label, cs[(vintage, var)], money=True))
    if not rows:
        fail('no income band survived for %s, so the income table would be empty' % vintage)
    return dict(vintage=vintage, window=WINDOW[vintage],
                all_households=est_row('All households', allhh, money=True),
                bands=rows, unavailable=unavailable)


def senior_gap(inc):
    """What a 65-and-over household's median is, as a share of a 45-to-64 household's.

    A ratio of two medians and nothing more. It is not a statement about any household
    and it is not income over a lifetime -- these are different households measured in
    the same five years.
    """
    by = {r['label']: r for r in inc['bands']}
    a, b = by.get('65 and over'), by.get('45 to 64')
    if not a or not b:
        fail('the income table no longer carries both the 45-to-64 and the 65-and-over '
             'band, so the comparison cannot be made')
    share = 100.0 * a['estimate'] / b['estimate']
    return dict(senior=a, middle=b, share=share, share_text=pct(share),
                difference=b['estimate'] - a['estimate'],
                difference_text=usd(b['estimate'] - a['estimate']))


# ------------------------------------------------------------------ the rank, and the band

def rank(db, vintage):
    """Where Lunenburg's median household income sits among Massachusetts municipalities
    -- and how many of them it cannot be told apart from.

    BOTH, TOGETHER, ALWAYS. The rank is arithmetic on a column of estimates and it is
    nearly meaningless as a ranking, because the intervals are wide and most of them
    overlap. Publishing the rank alone would be this project committing the exact false
    precision it tells everybody else to avoid.

    Two counts, and they answer slightly different questions:

      * `overlap` -- municipalities whose own interval intersects Lunenburg's. The
        cruder and more conservative reading, and the one a reader can see on a chart.
      * `indistinguishable` -- municipalities the Census's own significance test cannot
        separate from Lunenburg. Stricter, so it is the smaller number, and it is
        published beside the first rather than instead of it.
    """
    rows = q(db, """SELECT geography, estimate, moe, estimate_raw, moe_raw
                    FROM census_acs WHERE level='municipality' AND vintage=?""", vintage)
    if len(rows) < MIN_MUNICIPALITIES:
        fail('the statewide income table holds %d municipalities for %s; Massachusetts '
             'has 351, so something has filtered it and a rank off it is a rank of a '
             'subset' % (len(rows), vintage))
    me = [r for r in rows if r[0].startswith('Lunenburg town')]
    if len(me) != 1:
        fail('%d rows name Lunenburg in the %s statewide income table' % (len(me), vintage))
    lun_e, lun_m = float(me[0][1]), float(me[0][2])

    # A municipality with no computable margin cannot be tested against Lunenburg either
    # way, so it is excluded from BOTH counts and counted out loud. All of them are
    # top-coded -- the Census prints $250,001 for a median above its top bracket -- and
    # every one is far above Lunenburg, so their exclusion cannot inflate the overlap.
    no_margin = [dict(geography=r[0], estimate_raw=r[3], moe_raw=r[4])
                 for r in rows if r[2] is None]
    usable = [(r[0], float(r[1]), float(r[2])) for r in rows if r[2] is not None]

    ordered = sorted(rows, key=lambda r: -float(r[1]))
    place = [i for i, r in enumerate(ordered, 1) if r[0].startswith('Lunenburg town')][0]

    lo, hi = lun_e - lun_m, lun_e + lun_m
    overlap = [g for g in usable if g[1] + g[2] >= lo and g[1] - g[2] <= hi]
    indis = [g for g in usable if not distinguishable((g[1], g[2]), (lun_e, lun_m))[2]]
    over_names = {g[0] for g in overlap}
    over_ranks = [i for i, r in enumerate(ordered, 1) if r[0] in over_names]

    values = sorted(float(r[1]) for r in rows)
    mid = values[len(values) // 2] if len(values) % 2 else (
        values[len(values) // 2 - 1] + values[len(values) // 2]) / 2.0
    return dict(
        vintage=vintage, window=WINDOW[vintage],
        estimate=lun_e, moe=lun_m, text=pm(lun_e, lun_m, money=True),
        estimate_text=usd(lun_e), moe_text=usd(lun_m),
        low=lo, high=hi, low_text=usd(lo), high_text=usd(hi),
        rank=place, municipalities=len(rows),
        rank_text='%d of %d' % (place, len(rows)),
        overlap=len(overlap), overlap_text='%d of %d' % (len(overlap), len(rows)),
        overlap_share=100.0 * len(overlap) / len(rows),
        overlap_share_text=pct(100.0 * len(overlap) / len(rows)),
        best_rank_in_band=min(over_ranks), worst_rank_in_band=max(over_ranks),
        indistinguishable=len(indis),
        indistinguishable_text='%d of %d' % (len(indis), len(rows)),
        no_margin=len(no_margin), no_margin_places=no_margin,
        state_median=mid, state_median_text=usd(mid),
        distribution=histogram(values, lun_e))


def histogram(values, mark):
    """The statewide distribution in $20,000 bins, with the bin Lunenburg falls in named.

    A rank is a position in a queue and tells a reader nothing about the shape of the
    queue. This is the shape: how many towns are where, and which column the town is
    standing in.
    """
    step = 20000
    top = int(max(values) // step + 1) * step
    bins = []
    for lo in range(0, top, step):
        hi = lo + step
        count = sum(1 for v in values if lo <= v < hi)
        # TWO LABELS ON PURPOSE. `label` is the axis tick and is as short as a tick can
        # be -- thirteen bins of "$100k–$120k" set at an angle collide with each other on
        # a phone, and a chart whose own axis is unreadable is worse than one bin wide.
        # `range_label` is the full range, and it is what the table twin prints.
        bins.append(dict(low=lo, high=hi, count=count,
                         label='$%dk' % (lo // 1000),
                         range_label='$%dk–$%dk' % (lo // 1000, hi // 1000),
                         is_lunenburg=lo <= mark < hi))
    if sum(b['count'] for b in bins) != len(values):
        fail('the income histogram drops municipalities, so it is not the distribution')
    return bins


# ------------------------------------------------------------------ the pairing

def per_pupil(db):
    """Where Lunenburg sits among Massachusetts DISTRICTS on per-pupil spending.

    THE PAIRING THIS PAGE IS FOR, and the reason both halves are computed here rather
    than quoted from /what-other-districts-spend: a figure read off another page's prose
    is a derived thing quoted as an observed one, and this one has to be set beside the
    income rank in the same sentence.

    THE TWO RANKS ARE NOT THE SAME KIND OF RANK, and the payload says so in its own
    fields. One is 350 MUNICIPALITIES on a sample estimate with a margin; this is 318
    DISTRICTS on a figure DESE computes from returns, including charter and virtual
    districts, with no margin at all. They cannot be differenced, subtracted or
    averaged; they can be read side by side, which is what a reader wants.
    """
    rows = q(db, """SELECT fy, districts, lunenburg_per_pupil, lunenburg_rank_of_districts,
                           per_pupil_median, per_pupil_basis
                    FROM dese_function_statewide
                    WHERE level='total' AND func_cat_code='TTPP'
                    ORDER BY fy""")
    if len(rows) < MIN_PEER_YEARS:
        fail('the statewide per-pupil series came back with %d years; expected at least '
             '%d' % (len(rows), MIN_PEER_YEARS))
    out = []
    for fy, districts, pp, rank_text, median, basis in rows:
        m = re.match(r'^(\d+) of (\d+)$', (rank_text or '').strip())
        if not m:
            fail('the statewide per-pupil rank for FY%s reads %r, which this does not '
                 'know how to read. Rule 13: quote the source, never your rendering of '
                 'it' % (fy, rank_text))
        place, of = int(m.group(1)), int(m.group(2))
        if of != districts:
            fail('FY%s: the rank is out of %d and the row counts %d districts'
                 % (fy, of, districts))
        out.append(dict(fy=fy, districts=districts, per_pupil=pp, rank=place,
                        rank_text='%d of %d' % (place, of),
                        percentile_from_bottom=100.0 * (of - place + 1) / of,
                        median=median, basis=basis))
    worst = max(r['percentile_from_bottom'] for r in out)
    last = out[-1]
    return dict(first_fy=out[0]['fy'], last_fy=last['fy'], years=len(out), series=out,
                last=last, worst_percentile_from_bottom=worst,
                worst_percentile_text=pct(worst),
                below_median_years=sum(1 for r in out if r['per_pupil'] < r['median']),
                bottom_quarter_years=sum(1 for r in out
                                         if r['percentile_from_bottom'] <= 25.0))


def children(db):
    """The district's own enrolment, which is a COUNT and not an estimate.

    It is on this page for one reason: to say what a margin is, by standing next to one.
    1,568 children means 1,568 children; 1,979 residents aged 65 or over means somewhere
    between 1,670 and 2,288, and the two numbers must not be read as the same kind of
    thing even when they are printed in the same size.
    """
    rows = q(db, """SELECT fy, total_cnt FROM dese_enrollment
                    WHERE lea=? AND org_level='district' ORDER BY fy DESC LIMIT 1""", LEA)
    if not rows:
        fail('dese_enrollment returned no district row, so the count of children cannot '
             'be set beside the estimates')
    return dict(fy=int(rows[0][0]), students=int(rows[0][1]),
                students_text=n(rows[0][1]))


# ------------------------------------------------------------------ 2018 against 2023

def changes(cs, db, new, old):
    """Every comparison between the two vintages, and whether it survives the margins.

    THE HONEST SECTION IS THE ONE THAT MOSTLY SAYS NO. Fifteen measures, each tested
    against the combined margin of its two estimates, and the payload carries the result
    of every test rather than only the ones that passed -- because a table of the three
    that moved, with the twelve that did not quietly dropped, is a page claiming far more
    than the data says.

    The two five-year windows do not overlap -- 2014-2018 and 2019-2023 -- which is what
    makes the comparison permissible at all. Consecutive ACS releases share four years of
    sample and are not independent.
    """
    a_age, b_age = ages(cs, old), ages(cs, new)
    a_hh, b_hh = households(cs, old), households(cs, new)
    a_ten, b_ten = tenure(cs, old), tenure(cs, new)
    a_inc, b_inc = income(db, cs, old), income(db, cs, new)

    tests = []

    def add(label, kind, a, b, money=False, unit='', short=None):
        d, m, sig = distinguishable(a, b)
        tests.append(dict(
            label=label, short=short or label, kind=kind, unit=unit,
            old=a[0], old_moe=a[1], old_text=pm(a[0], a[1], money),
            new=b[0], new_moe=b[1], new_text=pm(b[0], b[1], money),
            difference=d, combined_moe=m, distinguishable=sig,
            difference_text=('%s%s' % ('+' if d >= 0 else '−',
                                       (usd if money else n)(abs(d)))),
            combined_moe_text=(usd if money else n)(m),
            verdict='clears its margin' if sig else 'inside the margin'))

    def pctpoints(label, a, b, short=None):
        d, m, sig = distinguishable(a, b)
        tests.append(dict(
            label=label, short=short or label, kind='share', unit='% of the town',
            old=a[0], old_moe=a[1], old_text='%s ± %s' % (pct(a[0]), pct(a[1])),
            new=b[0], new_moe=b[1], new_text='%s ± %s' % (pct(b[0]), pct(b[1])),
            difference=d, combined_moe=m, distinguishable=sig,
            difference_text='%s%.1f points' % ('+' if d >= 0 else '−', abs(d)),
            combined_moe_text='%.1f points' % m,
            verdict='clears its margin' if sig else 'inside the margin'))

    add('Population', 'count',
        (a_age['population']['estimate'], a_age['population']['moe']),
        (b_age['population']['estimate'], b_age['population']['moe']), unit='residents')
    for key, label, short in (('senior', 'Residents 65 and over', 'Residents 65+'),
                              ('children', 'Residents under 18', 'Residents under 18')):
        ga = [g for g in a_age['groups'] if g['key'] == key][0]
        gb = [g for g in b_age['groups'] if g['key'] == key][0]
        add(label, 'count', (ga['estimate'], ga['moe']), (gb['estimate'], gb['moe']),
            unit='residents', short=short)
        pctpoints(label.replace('Residents ', 'Share of the town ').strip(),
                  (ga['share'], ga['share_moe']), (gb['share'], gb['share_moe']),
                  short=short.replace('Residents', 'Share'))
    add('Households', 'count',
        (a_hh['households']['estimate'], a_hh['households']['moe']),
        (b_hh['households']['estimate'], b_hh['households']['moe']), unit='households')
    add('Households with a child under 18', 'count',
        (a_hh['with_child']['estimate'], a_hh['with_child']['moe']),
        (b_hh['with_child']['estimate'], b_hh['with_child']['moe']), unit='households',
        short='Homes with a child')
    pctpoints('Share of households with a child under 18',
              (a_hh['share'], a_hh['share_moe']), (b_hh['share'], b_hh['share_moe']),
              short='Share with a child')
    add('Median household income', 'money',
        (a_inc['all_households']['estimate'], a_inc['all_households']['moe']),
        (b_inc['all_households']['estimate'], b_inc['all_households']['moe']),
        money=True, unit='a year', short='Median income')
    a_by = {r['label']: r for r in a_inc['bands']}
    b_by = {r['label']: r for r in b_inc['bands']}
    for label in sorted(set(a_by) & set(b_by)):
        add('Median income, householder %s' % label, 'money',
            (a_by[label]['estimate'], a_by[label]['moe']),
            (b_by[label]['estimate'], b_by[label]['moe']), money=True, unit='a year',
            short='Income, householder %s' % label.replace(' and over', '+'))
    add('Owner-occupied homes', 'count',
        (a_ten['owner']['estimate'], a_ten['owner']['moe']),
        (b_ten['owner']['estimate'], b_ten['owner']['moe']), unit='households',
        short='Owner-occupied')
    pctpoints('Share of homes owner-occupied',
              (a_ten['owner_share'], a_ten['owner_share_moe']),
              (b_ten['owner_share'], b_ten['owner_share_moe']),
              short='Share owner-occupied')
    add('Renter-occupied homes', 'count',
        (a_ten['renter']['estimate'], a_ten['renter']['moe']),
        (b_ten['renter']['estimate'], b_ten['renter']['moe']), unit='households',
        short='Renter-occupied')

    survived = [t for t in tests if t['distinguishable']]
    return dict(old=old, new=new, old_window=WINDOW[old], new_window=WINDOW[new],
                tests=tests, compared=len(tests), survived=len(survived),
                inside_the_margin=len(tests) - len(survived),
                survived_text='%d of %d' % (len(survived), len(tests)),
                survived_labels=[t['label'] for t in survived])


# ------------------------------------------------------------------ provenance, rule 12

def sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


CENSUS = 'United States Census Bureau'
API = ('https://api.census.gov/data/%d/acs/acs5')


def documents(db):
    """The raw API responses, each hashed on disk against the hash recorded when it was
    fetched, and each checked to be SERVED.

    An API answer is a document and rule 12 does not exempt it for being JSON. Two things
    are asserted rather than assumed: the bytes on disk are still the bytes the figures
    were read from, and the copy published at /docs/ exists -- a citation pointing at an
    address that 404s is not a citation.
    """
    rows = q(db, """SELECT DISTINCT vintage, "table", source_file, sha256, about
                    FROM census_acs ORDER BY vintage DESC, "table" """)
    if not rows:
        fail('census_acs names no source file, so nothing on this page has an address')
    out = []
    for vintage, table, source_file, digest, about in rows:
        src = os.path.join(ROOT, 'sources', 'state-census', source_file)
        if not os.path.exists(src):
            fail('%s is not on disk, and every figure on this page was read from it'
                 % source_file)
        got = sha256(src)
        if got != digest:
            fail('%s hashes to %s and census-acs.csv records %s. The document these '
                 'figures were read from has changed underneath them'
                 % (source_file, got[:12], digest[:12]))
        served = os.path.join(DOCS, 'state-census', source_file)
        if not os.path.exists(served):
            fail('%s is cited on this page and is not published at /docs/state-census/. '
                 'Copy it into fy28/public/docs/state-census/ -- a citation nobody can '
                 'follow is not a citation' % source_file)
        if sha256(served) != digest:
            fail('the published copy of %s is not the file the figures came from'
                 % source_file)
        out.append(dict(
            path='sources/state-census/' + source_file, sha256=digest,
            bytes=os.path.getsize(src), url=API % vintage,
            docs_url='/docs/state-census/' + source_file,
            table='%s, %s' % (table, WINDOW[vintage]),
            publisher=CENSUS, note=about))
    out.append(dict(
        path='sources/data/census-acs.csv', sha256=sha256(CSV),
        bytes=os.path.getsize(CSV),
        url='https://www.census.gov/programs-surveys/acs/',
        docs_url='/data/census-acs.csv',
        table='Every estimate, with its margin',
        publisher='Built by this project, from the responses above',
        note='One row per estimate per vintage, the margin of error in the same row. '
             'Written by scripts/fetch_census_acs.py, which refuses to write if the API '
             'returns anything that is not JSON.'))
    return out


def said():
    out = []
    for spec in QUOTES:
        rel = '%s/%s/%s-%s-%s.txt' % (MINUTES, spec['board'], spec['date'],
                                      spec['kind'], spec['doc'])
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            fail('%s is not here -- a quote on this page is attributed to a document that '
                 'is not in the archive' % rel)
        text = re.sub(r'\s+', ' ', open(path, encoding='utf-8', errors='replace').read())
        if re.sub(r'\s+', ' ', spec['quote']) not in text:
            fail('the quote attributed to %s %s is no longer in %s -- quote the source, '
                 'never your rendering of it' % (spec['board'], spec['date'], rel))
        out.append(dict(
            key=spec['key'], board=spec['board'].replace('-', ' ').title(),
            date=spec['date'], quote=spec['quote'], why=spec['why'], kind=spec['kind'],
            cite='/docs/' + rel.replace('sources/', ''),
            town='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_%s%s%s-%s'
                 % (spec['date'][5:7], spec['date'][8:10], spec['date'][:4], spec['doc'])))
    return out


def searched():
    a = archive()
    return [dict(term=t, documents=sum(1 for b in a['bodies']
                                       if re.search(re.escape(t), b, re.I)))
            for t in SEARCHED]


def gaps():
    with open(GAPS, encoding='utf-8') as fh:
        by_what = {r['what'].strip(): r for r in csv.DictReader(fh)}
    out = []
    for what in GAP_WHAT:
        r = by_what.get(what)
        if not r:
            fail('money-gaps.csv no longer registers %r. Rule 7c: the registry outranks '
                 'the page, so a page whose limits are not in the registry must not '
                 'publish' % what)
        out.append(dict(side=r['side'], what=r['what'], why=r['why']))
    return out


# ------------------------------------------------------------------ what it does not show

def not_established(rk, ch, pp, sentinels):
    return [
        'That any of these figures is a count. Every one is a five-year SAMPLE estimate '
        'with a margin of error, and two figures whose intervals overlap are not '
        'different. The town’s own population total is measured to ±%s; a '
        'single age band inside it is not.'
        % n(rk['population_moe'] if 'population_moe' in rk else 19),
        'That %s households have a child in the LUNENBURG PUBLIC SCHOOLS. The Census '
        'counts a child under 18, which includes Monty Tech, private and charter '
        'children and children not yet of school age, so the figure is a ceiling.'
        % ch['with_child_text'],
        'That Lunenburg is richer or poorer than a town it out-ranks. %s of the %s '
        'municipalities have an income interval that overlaps this town’s, so a '
        'rank of %s is arithmetic rather than a finding.'
        % (n(rk['overlap']), n(rk['municipalities']), rk['rank_text']),
        'That the income rank and the per-pupil rank measure the same population. One is '
        '%s municipalities on a sample estimate; the other is %s school districts on a '
        'figure DESE computes from returns, and it includes charter and virtual districts '
        'that are not municipal.' % (n(rk['municipalities']), n(pp['last']['districts'])),
        'Anything about what a household can AFFORD. Income is not wealth, not savings, '
        'not equity in a house and not a tax bill, and nothing in this archive joins a '
        'property tax payment to the age of the person who paid it.',
        'Anything in real terms. This archive holds no price index, so no figure here is '
        'deflated and no change described is a change in purchasing power.',
        'Anything at all from %d published sentinel(s) — the Census’s codes for '
        '"no estimate" and "no computable margin". They are not zeros and are not '
        'printed as figures.' % sentinels,
        'Why any of this is so. Every figure here is a measurement of who lives in this '
        'town; a reason for it would be a hypothesis, and this page states none.',
    ]


# ------------------------------------------------------------------ conclusions

def build_conclusions(age, hh, ten, inc, gap, rk, pp, ch, chg):
    """What this page establishes, written by the thing that computed the figures.

    `allow` carries the AGE BANDS and the SURVEY WINDOWS. Neither is a derived figure:
    "65 or over" is the Census's own category name and "2019-2023" is the name of a
    release, so they are declared here as exceptions rather than being registered as
    quantities nobody computed -- which is what rule 2's escape hatch is for, and it is
    written down so it can be reviewed.
    """
    senior = [g for g in age['groups'] if g['key'] == 'senior'][0]
    AGES = ('65 or over', '65 and over', 'under 18', '45-to-64', 'under-25')
    WINDOWS = (chg['old_window'], chg['new_window'])
    rows = []

    rows.append(conclusion(
        id='a-sixth-of-the-town-is-65-or-over',
        claim='%s residents are 65 or over — %s of the town, on a five-year sample.'
              % (senior['text'], senior['share_text']),
        so_what='A group about the size of the %s children in the schools, and measured '
                'far less exactly.' % ch['students_text'],
        figure='senior', bearing='sizes', kind='measured',
        allow=AGES,
        figures={
            'senior': figure(senior['estimate'], senior['text'], 'residents 65 or over'),
            'share': figure(senior['share'], senior['share_text']),
            'students': figure(ch['students'], ch['students_text']),
            'low': figure(senior['estimate'] - senior['moe'],
                          n(senior['estimate'] - senior['moe'])),
            'high': figure(senior['estimate'] + senior['moe'],
                           n(senior['estimate'] + senior['moe'])),
        },
        detail='The count is a sum of twelve age cells, so its margin is the root of the '
               'sum of their squares, and the interval it describes runs from %s to %s. '
               'The enrolment figure beside it is a DESE count of children rather than a '
               'sample estimate, which is the difference this whole page turns on: %s '
               'means exactly that, and this does not.'
               % (n(senior['estimate'] - senior['moe']),
                  n(senior['estimate'] + senior['moe']), ch['students_text']),
        basis='Census Bureau, American Community Survey five-year estimates, table '
              'B01001, %s, for Lunenburg town; DESE enrolment for the latest published '
              'year.' % age['window'],
        not_shown='Nothing about what this group wants, can afford, or how it votes. An '
                  'age is an age.'))

    rows.append(conclusion(
        id='a-third-of-homes-have-a-child-under-18',
        claim='%s of %s households have a child under 18 — %s of them.'
              % (hh['with_child']['text'], hh['households']['estimate_text'],
                 hh['share_text']),
        so_what='The rough claim heard in town, that schools serve about a third of '
                'homes, is fair on this measure.',
        figure='withchild', bearing='sizes', kind='measured',
        allow=AGES,
        figures={
            'withchild': figure(hh['with_child']['estimate'], hh['with_child']['text'],
                                'households with a child under 18'),
            'households': figure(hh['households']['estimate'],
                                 hh['households']['estimate_text']),
            'share': figure(hh['share'], hh['share_text']),
            'sharemoe': figure(hh['share_moe'], hh['share_moe_text']),
        },
        detail='This is a CEILING on homes with a child in the Lunenburg public schools '
               'rather than that figure: it counts children at Monty Tech, at private and '
               'charter schools, and children not yet of school age. The share carries a '
               'margin of %s in its own right, so about a third is the honest reading and '
               'any exact fraction is not.' % hh['share_moe_text'],
        basis='Census Bureau, American Community Survey five-year estimates, table '
              'B11005, %s, for Lunenburg town.' % hh['window'],
        not_shown='Which households have a child in the town’s own schools. Nothing '
                  'published joins a child to a household to a school, and that is a '
                  'registered gap.',
        see=[('what-families-pay', 'What a family actually pays')]))

    rows.append(conclusion(
        id='a-senior-household-earns-about-half',
        claim='A household headed by someone 65 or over has a median income of %s.'
              % gap['senior']['text'],
        so_what='That is %s of a 45-to-64 household’s %s — the gap under the '
                '“fixed incomes” argument.'
                % (gap['share_text'], gap['middle']['estimate_text']),
        figure='senior', bearing='sizes', kind='measured',
        allow=AGES,
        figures={
            'senior': figure(gap['senior']['estimate'], gap['senior']['text']),
            'middle': figure(gap['middle']['estimate'], gap['middle']['estimate_text']),
            'share': figure(gap['share'], gap['share_text']),
        },
        detail='Two medians of two different sets of households in the same five years. '
               'It is not one household’s income falling as it ages, and it says '
               'nothing about savings, equity or a tax bill — none of which this '
               'archive holds by age at all. The under-25 band is published as a sentinel '
               'in both releases and is not a figure.',
        basis='Census Bureau, American Community Survey five-year estimates, table '
              'B19049, %s, for Lunenburg town.' % inc['window'],
        not_shown='What any household can afford. Income is not wealth, and no record '
                  'here joins a property tax payment to the age of the person paying it.'))

    rows.append(conclusion(
        id='four-in-five-homes-are-owner-occupied',
        claim='%s of occupied homes are owner-occupied — %s households.'
              % (ten['owner_share_text'], ten['owner']['estimate_text']),
        so_what='A rise in the levy reaches most households as a bill they receive, '
                'rather than through a rent.',
        figure='ownershare', bearing='sizes', kind='measured',
        figures={
            'ownershare': figure(ten['owner_share'], ten['owner_share_text']),
            'owner': figure(ten['owner']['estimate'], ten['owner']['estimate_text']),
            'renter': figure(ten['renter']['estimate'], ten['renter']['text']),
        },
        detail='The remaining %s homes are renter-occupied. A renting household pays '
               'property tax through its rent rather than on a bill, which is a different '
               'thing to experience and the same thing to fund; nothing here measures how '
               'much of a levy increase reaches a rent, or how fast.'
               % ten['renter']['text'],
        basis='Census Bureau, American Community Survey five-year estimates, table '
              'B25003, %s, for Lunenburg town.' % ten['window'],
        not_shown='What any household pays. Tenure is not a tax bill, and the town '
                  'publishes no split of the levy by who pays it.',
        see=[('overrides', 'What an override would cost')]))

    rows.append(conclusion(
        id='ordinary-on-income-near-the-bottom-on-spending',
        claim='Ordinary income for Massachusetts, and %s districts on spending for each '
              'pupil.' % pp['last']['rank_text'],
        so_what='Both are true at once, and this town has not had the two put side by '
                'side before.',
        figure='overlap', bearing='sizes', kind='measured',
        figures={
            'overlap': figure(rk['overlap'], n(rk['overlap']),
                              'towns we cannot be told apart from'),
            'rank': figure(rk['rank'], rk['rank_text']),
            'pprank': figure(pp['last']['rank'], pp['last']['rank_text']),
            'ppyears': figure(pp['bottom_quarter_years'], pp['ppyears_text']),
        },
        detail='Lunenburg’s median household income ranks %s Massachusetts '
               'municipalities — and %s of them have an income interval that overlaps '
               'this town’s, so the rank is arithmetic and the band is the finding. '
               'On spending for each pupil the town sits in the bottom quarter of '
               'Massachusetts districts in %s measured years. The two are not the same '
               'kind of rank: one is municipalities on a sample estimate with a margin, '
               'the other is districts on a figure DESE computes from returns.'
               % (rk['rank_text'], n(rk['overlap']), pp['ppyears_text']),
        basis='Census table B19013 for every Massachusetts municipality, %s; DESE’s '
              'all-district per-pupil expenditure, every published year.' % rk['window'],
        not_shown='Any relation between the two. Nothing here establishes what a town of '
                  'this income should spend for each pupil, and the two ranks are drawn '
                  'over different sets.',
        see=[('what-other-districts-spend',
              'What other districts spend, for each pupil')]))

    rows.append(conclusion(
        id='most-of-what-changed-is-inside-the-margin',
        claim='Only %s measures compared across the two five-year windows clear their '
              'margins.' % chg['survived_text'],
        so_what='The town changed less than any table of five-year differences would make '
                'it look.',
        figure='survived', bearing='sizes', kind='measured',
        allow=AGES + WINDOWS,
        figures={
            'survived': figure(chg['survived'], chg['survived_text'],
                               'comparisons that clear their margins'),
        },
        detail='The windows are %s and %s, which do not overlap — consecutive ACS '
               'releases share four years of sample and may not be differenced at all. '
               'What survives: %s. Everything else, including the share of residents 65 '
               'or over and the share of households with a child under 18, moved by less '
               'than the combined margin of its own two estimates, which is not a change.'
               % (chg['old_window'], chg['new_window'],
                  '; '.join(chg['survived_labels'])),
        basis='Census Bureau, American Community Survey five-year estimates, tables '
              'B01001, B11005, B19049 and B25003, the two releases side by side.',
        not_shown='That nothing changed. A difference inside the margin is one this '
                  'instrument cannot see, which is not the same as one that did not '
                  'happen.'))

    return emit('bythenumbers', rows)


# ------------------------------------------------------------------ build

def build():
    db = sqlite3.connect(DB)
    try:
        cs, sentinels = cells(db)
        age = ages(cs, NEW)
        hh = households(cs, NEW)
        ten = tenure(cs, NEW)
        inc = income(db, cs, NEW)
        gap = senior_gap(inc)
        rk = rank(db, NEW)
        rk['population_moe'] = age['population']['moe']
        pp = per_pupil(db)
        pp['ppyears_text'] = '%d of %d' % (pp['bottom_quarter_years'], pp['years'])
        ch = children(db)
        ch['with_child_text'] = hh['with_child']['text']
        chg = changes(cs, db, NEW, OLD)

        older = dict(ages=ages(cs, OLD), households=households(cs, OLD),
                     tenure=tenure(cs, OLD), income=income(db, cs, OLD))

        return dict(
            generated_by='scripts/build_lunenburg_by_the_numbers.py',
            about='Who lives in Lunenburg — how many people, how old, in how many '
                  'households, owning or renting, and on what income — from the '
                  'Census Bureau’s five-year estimates, every figure with its '
                  'margin of error.',
            grain='RESIDENTS AND HOUSEHOLDS, as five-year SAMPLE ESTIMATES. Not a count: '
                  'the American Community Survey samples a town of 11,804 and publishes '
                  'a margin of error with every figure. Two estimates whose intervals '
                  'overlap are not different. Nothing here is a dollar of budget, a '
                  'child in a classroom or a tax bill.',
            vintage=NEW, window=WINDOW[NEW], previous_vintage=OLD,
            previous_window=WINDOW[OLD],
            ages=age, households=hh, tenure=ten, income=inc, senior_gap=gap,
            rank=rk, per_pupil=pp, children=ch, change=chg, previous=older,
            sentinels=dict(rows=len(sentinels), detail=sentinels, meanings=[
                dict(code='-666666666', field='estimate',
                     means='no estimate could be published for this cell'),
                dict(code='-222222222', field='margin',
                     means='no margin of error could be computed'),
                dict(code='-333333333', field='margin',
                     means='the estimate is top-coded, so no margin applies'),
                dict(code='-555555555', field='margin',
                     means='the estimate is CONTROLLED to an independent total and has '
                           'no sampling error — which is not a margin of zero'),
            ]),
            sources=documents(db),
            said=said(), searched=searched(), minutes=coverage(),
            gaps=gaps(),
            not_established=not_established(rk, ch, pp, len(sentinels)),
            closes='The town census. It counts every resident by name, age and household '
                   'each year, it is compiled by the Town Clerk, and it is the one record '
                   'that would replace every estimate on this page with a count — '
                   'including the two things the Census cannot say: which households have '
                   'a child in the Lunenburg public schools, and what the people in them '
                   'pay in property tax.',
            conclusions=build_conclusions(age, hh, ten, inc, gap, rk, pp, ch, chg),
        )
    finally:
        db.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    data = build()

    if args.check:
        if not os.path.exists(OUT):
            print('MISSING %s' % os.path.relpath(OUT, ROOT))
            return 1
        with open(OUT, encoding='utf-8') as fh:
            have = json.load(fh)
        if have != data:
            print('STALE %s — run: python3 scripts/build_lunenburg_by_the_numbers.py'
                  % os.path.relpath(OUT, ROOT))
            return 1
        print('ok — %s reproduces from the database' % os.path.relpath(OUT, ROOT))
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write('\n')
    print('%s: %s, %s' % (os.path.relpath(OUT, ROOT),
                          data['ages']['population']['text'] + ' residents',
                          data['window']))
    senior = [g for g in data['ages']['groups'] if g['key'] == 'senior'][0]
    print('  %s aged 65 or over (%s); %s households, %s with a child under 18 (%s)'
          % (senior['text'], senior['share_text'],
             data['households']['households']['text'],
             data['households']['with_child']['text'],
             data['households']['share_text']))
    print('  median household income %s: rank %s, and %s municipalities overlap it'
          % (data['rank']['text'], data['rank']['rank_text'], data['rank']['overlap']))
    print('  %d of %d comparisons between %s and %s clear their margins'
          % (data['change']['survived'], data['change']['compared'],
             data['change']['old_window'], data['change']['new_window']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
