"""Free cash: what it is, how much is spendable, and why it cannot bend the curve.

Two claims are argued about locally — that the town is too conservative and sitting on
money, and that free cash is "not up to standard" so the town is rebuilding. The reading is
in `sources/analyses/free-cash.md`; this module is the arithmetic behind the page.

**Rule 1 is the constraint that shapes this file, and this file deliberately bends it.**
The projection is built from budget columns only. Free cash is derived from ACTUALS — it is
definitionally the variance between what was appropriated and what happened. Rule 1 exists
because a growth RATE measured across that boundary is partly growth and partly the step
between the two, which is what put the special education escalator 1.5 points high.

Free cash is fed into `finance.project` here, and it is not that error: it is a one-time
subtraction applied after every rate has run, touching no bucket, no escalator and no growth
rate, and never carried into the next year's base. The difference between "a rate across the
boundary" and "a labelled one-time amount subtracted at the end" is the whole of why this is
allowed.

That distinction is worth nothing as a promise, so it is proven. `project` leaves `deficit`
untouched and reports free cash in two ADDITIONAL fields, so a caller that knows nothing
about this gets exactly the numbers it got before — enabling the feature cannot move
anything else on the site. `scripts/audit_provenance.py` asserts it at nine different draws
and fails the build if any bucket, rate, level service or deficit ever moves.

**The band is single-sourced and that is stated wherever it is used.** 5-7% appears in one
document in the archive: the Town's own FY27 budget press release, quoting DLS. We hold no
DLS publication saying it. The band is load-bearing — at a lower threshold the same balance
is above the range rather than inside it — so it travels with that caveat attached.

The one finding worth reading twice: at a normal year's underspending Lunenburg generates
about 4% of budget in free cash, which is below the bottom of the band it is measured
against. The current 6.55% exists because 2025's unspent appropriations were 2.49 times the
town's own four-year average.
"""

# --- what the Town publishes, and what we can reproduce ------------------------------
# Three different figures are all called "the operating budget" and none of them is the
# same number. No conclusion turns on the difference -- every version is inside 5-7% --
# but a ratio quoted to two decimals should not rest on a soft denominator silently.
BUDGET_BASE = 51_189_961          # FY26 original appropriation, town-ledger-fy26-q3.csv
BUDGET_REVISED = 51_531_199       # the same report's revised column at Q3
TOWN_IMPLIED_BASE = 50_441_654    # what the Town's published 6.65% implies. Not reproducible

# sources/dls-free-cash/free-cash-proof-lunenburg.xlsx, certified column for 2025
CERTIFIED = 3_354_370
IDENTIFIED = 3_716_282
UNSPENT_2025 = 2_457_761
UNSPENT_AVG_2021_24 = 986_340

# DLS certifies less than it identifies and we do not hold the reason, so the gap is
# carried as an observed ratio rather than explained.
CERTIFIED_RATIO = round(CERTIFIED / IDENTIFIED, 4)

BAND_LOW, BAND_HIGH = 0.05, 0.07
BAND_SOURCE = ("Town of Lunenburg, FY27 budget press release, page 6, quoting DLS. This is "
               "the only source in the archive for the 5-7% band, and it is the Town "
               "quoting the state rather than the state itself.")

# The Town's own ten-year account, quoted rather than computed -- we hold five years.
TOWN_HISTORY = ("In the last 10 years, Lunenburg has been below DLS free cash "
                "recommendations for seven years, only meeting this recommendation in "
                "2022, 2023, and 2026.")

# DLS labels the proof by the calendar year of the 1 July certification; the Town labels
# the same money by the fiscal year it can be spent in. Confirmed, not assumed: Lunenburg's
# three largest certified balances are 2021, 2022 and 2025, and adding one gives exactly
# the three years the Town names above.
YEAR_OFFSET_NOTE = ("DLS dates free cash to the 1 July it is certified; the Town dates it "
                    "to the fiscal year it can be spent in. They are one year apart.")

HISTORY = [(2021, 2_666_962), (2022, 2_923_290), (2023, 1_870_612),
           (2024, 2_270_060), (2025, 3_354_370)]

# 2025 unspent appropriations as a multiple of each town's own 2021-24 average. Lunenburg
# is the outlier by a wide margin, which is what makes 2025 an event rather than a stance.
PEER_MULTIPLES = [('Lunenburg', 2.49), ('Ayer', 1.44), ('Groton', 1.37), ('Littleton', 1.13),
                  ('Westford', 1.13), ('Shirley', 1.14), ('Townsend', 1.31),
                  ('Upton', 0.72), ('Uxbridge', 0.40)]


# --- comparing nine towns, when the source carries no denominator ----------------
# The obvious question about the peer table is the one the source cannot answer: how does
# each town's free cash sit against the 5-7% band? That needs each town's operating budget,
# and the DLS proof carries no population, budget, revenue or levy for any town -- ours or
# theirs. So Littleton's $10.0M against Shirley's $266K says nothing about which is closer
# to its own target, and a percentage-of-budget column would have to be invented.
#
# What the proof DOES support is composition, because a share has no size. Unspent
# appropriations as a fraction of a town's own identified free cash is comparable across
# towns of any size, and it answers the version of the question that matters here: is
# Lunenburg's balance built the same way everybody else's is?
#
# It is a different measure from PEER_MULTIPLES above and the two disagree in a useful way.
# On the multiple -- 2025 against a town's own four-year average -- Lunenburg is the clear
# outlier. On composition it is the highest of nine but inside a cluster. Both belong on
# the page; neither is the percentage-of-budget figure, and the page must not imply it is.
UNSPENT_LINE = 'Add Unencumbered/Unexpended Appropriations (CL#11)'
PEER_DENOMINATOR_NOTE = (
    'The Division of Local Services proof carries no denominator — no population, budget, '
    'revenue or levy for any town, including Lunenburg. So free cash as a share of each '
    'town’s operating budget cannot be computed from it, and is not shown. Composition is '
    'shown instead, because a share compares across towns of different size and an '
    'absolute dollar figure does not.')


def peer_composition(year='2025'):
    """Unspent appropriations as a share of each town's own identified free cash.

    Comparable across towns because it is a ratio. Read beside PEER_MULTIPLES, not instead
    of it: one measures how unusual this year was for that town, the other what the balance
    is made of.
    """
    import csv as _csv, os as _os
    path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                         'sources', 'data', 'free-cash-proof.csv')
    if not _os.path.exists(path):
        return []
    got = {}
    for r in _csv.DictReader(open(path)):
        if r['year'] != year:
            continue
        d = got.setdefault(r['town'], {})
        if r['role'] == 'identified_total':
            d['identified'] = float(r['amount'])
        elif r['role'] == 'component' and r['line'] == UNSPENT_LINE:
            d['unspent'] = float(r['amount'])
    out = [dict(town=t, identified=round(v['identified']), unspent=round(v['unspent']),
                unspentShare=round(v['unspent'] / v['identified'], 4))
           for t, v in got.items() if v.get('identified')]
    return sorted(out, key=lambda x: -x['unspentShare'])


def share(amount=CERTIFIED, base=BUDGET_BASE):
    """Free cash as a share of the operating budget."""
    return amount / base


def spendable(target, base=BUDGET_BASE):
    """Dollars released by drawing the balance down to `target` (a fraction of budget).

    Negative when the target is above the current balance, which is the honest answer to
    "what would it take to reach 7%" -- money that would have to be added, not released.
    Targets below zero are not modelled: a town cannot certify negative free cash and have
    it mean the same thing.
    """
    return CERTIFIED - base * max(target, 0.0)


def normal_year_certified():
    """What a year certifies when unspent appropriations are at their own recent average.

    Everything in the 2025 proof is held constant except the one component that moved, and
    the certified/identified ratio is carried across unchanged. It is a counterfactual on
    one line, not a forecast.
    """
    identified = IDENTIFIED - (UNSPENT_2025 - UNSPENT_AVG_2021_24)
    return round(identified * CERTIFIED_RATIO)


NORMAL_CERTIFIED = normal_year_certified()
NORMAL_SHARE = NORMAL_CERTIFIED / BUDGET_BASE


def years_covered(deficits, target):
    """How far a draw-down to `target` goes against a run of projected deficits.

    `deficits` is [(fy, amount)] from the projection, which is built from budget columns
    only. Free cash is actuals-derived. They are subtracted here and nowhere else, and the
    result is labelled as deferral rather than as a closed gap -- the money is one-time by
    construction, and DLS's own guidance is that it should not fund ongoing operations.
    """
    left = spendable(target)
    out = []
    for fy, amount in deficits:
        covered = left >= amount
        left -= amount
        out.append(dict(fy=fy, deficit=amount, covered=covered, remaining=round(left)))
    return out


# What a policy can actually sustain. Free cash is a FLOW, not a stock you refill at will:
# each year the town certifies whatever the variances produced. A standing policy of
# appropriating free cash every year is bounded by that flow, and the flow in an ordinary
# year is what NORMAL_CERTIFIED says -- about 4% of budget, below the floor of the band.
#
# The paradox worth stating plainly, because it is the honest answer to "be less
# conservative": the flow is generated BY the underspending. Two thirds of the 2025 balance
# is money appropriated and not spent. Budget more tightly and the gap you were going to
# fill with free cash shrinks the free cash you were going to fill it with. You cannot bank
# on both.
SUSTAINABLE_DRAW = NORMAL_CERTIFIED


# The stops a policy argument actually uses: through the recommended band, a few points
# either side of it, and all the way to zero. Named rather than numbered, because "the
# bottom of the recommended range" is the thing people say.
POLICY_STOPS = [
    (0.08, 'above the recommended range'),
    (0.07, 'top of the recommended range'),
    (0.06, 'middle of the recommended range'),
    (0.05, 'bottom of the recommended range'),
    (0.04, 'below the range — and about what a normal year generates'),
    (0.03, 'well below the range'),
    (0.02, 'well below the range'),
    (0.01, 'nearly nothing held back'),
    (0.00, 'spend everything, hold no reserve'),
]


def policy_ladder(project_fn, years=6):
    """Each policy stop: what it releases once, what it sustains yearly, and the gap after.

    The two parts do different work and the page must not blur them. Moving to a lower
    target releases the accumulated balance ONCE. Holding it there releases the annual flow
    EVERY year — and that annual figure does not depend on the target at all, which is the
    thing most likely to be misread. A lower target does not generate more money; it
    releases the stock sooner and then you are living on the flow either way.
    """
    out = []
    for target, label in POLICY_STOPS:
        one_time = max(spendable(target), 0.0)
        once = project_fn(years, free_cash=dict(one_time=one_time))
        both = project_fn(years, free_cash=dict(one_time=one_time,
                                                annual=SUSTAINABLE_DRAW))
        out.append(dict(
            target=target, label=label, oneTime=round(one_time),
            annual=SUSTAINABLE_DRAW,
            inBand=BAND_LOW <= target <= BAND_HIGH,
            years=[dict(fy=r['fy'], before=r['deficit_before_free_cash'],
                        applied=r['free_cash_applied'], after=r['deficit'])
                   for r in both],
            # Two separate questions, and keeping them apart is the point of this table.
            # Drawing the balance to a lower target is a ONE-OFF. Appropriating the annual
            # flow is the POLICY. The second dwarfs the first, and the second does not
            # depend on the target at all -- which is the thing most likely to be misread
            # about "be less conservative".
            gapLeftOneTimeOnly=sum(r['deficit'] for r in once),
            gapLeftWithPolicy=sum(r['deficit'] for r in both)))
    return out


def scenarios(project_fn, years=6):
    """Every draw the page offers, computed by the REAL projection.

    Precomputed rather than reimplemented in TypeScript. The alternative is the same rule
    written twice in two languages, which is a drift waiting to happen — and the one number
    people will quote from this site is "what would spending it buy".

    Targets run from 0% (spend everything, which nobody proposes and everybody asks about)
    to 8%. Spread is how many years the draw is stretched over.
    """
    out = []
    for t in range(0, 9):
        target = t / 100
        amount = max(spendable(target), 0.0)
        for spread in (1, 2, 3):
            rows = project_fn(years, free_cash=dict(amount=amount, years=spread))
            out.append(dict(
                target=target, spread=spread, released=round(amount),
                years=[dict(fy=r['fy'], deficit=r['deficit'],
                            applied=r['free_cash_applied'],
                            after=r['deficit_after_free_cash']) for r in rows]))
    return out


def override_contrast(project_fn, levy_cap, amount, years=6):
    """The same dollars once, versus permanently. This is the question people ask.

    Free cash and an override are opposites, and the contrast is the clearest statement of
    this site's argument that exists: a level against a slope. The override is modelled the
    way `fy28/src/model/rates.ts` models it and the way a ballot question actually works --
    the whole amount reaches the schools in year one, then compounds at the levy cap. It is
    NOT `finance.project`'s `override_amount`, which is added every year and answers a
    different question.

    Note what the numbers show and the page must not overstate: an override of this size
    does not close the gap either. It grows at 2.5% while the gap grows faster, so it loses
    ground every year. Only a change in the cost rates changes direction.
    """
    base = project_fn(years, free_cash=None)
    fc = project_fn(years, free_cash=dict(amount=amount, years=1))
    out = []
    for i, (b, f) in enumerate(zip(base, fc)):
        ov = amount * (1 + levy_cap) ** i
        out.append(dict(fy=b['fy'], deficit=b['deficit'],
                        freeCashApplied=f['free_cash_applied'],
                        afterFreeCash=f['deficit_after_free_cash'],
                        overrideValue=round(ov),
                        afterOverride=round(b['deficit'] - ov)))
    return dict(amount=round(amount), levyCap=levy_cap, years=out,
                cumulativeNone=sum(r['deficit'] for r in out),
                cumulativeFreeCash=sum(r['afterFreeCash'] for r in out),
                cumulativeOverride=sum(r['afterOverride'] for r in out))


# --- the capital programme, and what a redirect actually costs it --------------------
# The FY27 capital plan prints ten years of its own funding sources and an Average row
# under them. Both are read from `sources/data/capital-funding-history.csv` and the average
# is reconciled to the figure the plan itself prints, because rule 13's failure is an
# extract that quietly disagrees with the total its own source shows. The extract was two
# rows short of that for a while -- FY19 and FY20 were missing -- and nothing noticed,
# because the average beside them was typed rather than computed.
PLAN_PRINTED_AVG_FREE_CASH = 591_285.74   # town-article13-fy27-capital-plan.txt, "Average" row
PLAN_PRINTED_AVG_TOTAL = 1_287_612.33     # the same row, whole-programme column
PLANNED_FROM_FREE_CASH = 991_627          # ATM 2026 warrant, Article 13, FY27
PLANNED_FROM_TAXATION = 244_576           # capital plan p.9, "Raise and Appropriate"
# The Vehicle Use Special Purpose Stabilization Fund. Adopted at the 2017 Annual Town
# Meeting for "Funding Future Capital Needs for Vehicles and Equipment", it requires a 2/3
# vote and it cannot become school money -- so a third of the FY27 capital programme is
# NOT convertible into anything else, and a model that lets the reader cut it for money
# back is inventing dollars.
#
# The plan footnotes exactly two projects "*Funded from Vehicle Use Special Purpose
# Stabilization Fund": Engine 2 at $335,000 (p.15) and the Front End Loader at $259,000
# (p.23). They sum to the $594,000 the plan's own funding page shows against that fund,
# which is how the assignment is known rather than guessed -- no project-by-project
# funding table is published.
PLANNED_FROM_STABILIZATION = 594_000      # capital plan p.9, Special Purpose Stabilization


def _funding_history():
    """Free cash into the capital programme, year by year, from the plan's own table."""
    import csv as _csv
    import os as _os
    root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    path = _os.path.join(root, 'sources', 'data', 'capital-funding-history.csv')
    if not _os.path.exists(path):
        return []
    return [dict(fy=int(r['fy']), total=float(r['total']), freeCash=float(r['free_cash']))
            for r in _csv.DictReader(open(path))]


def capital_consequence():
    """What redirecting free cash costs the capital programme.

    Free cash is the capital programme's largest funding source -- averaging $591,286 a
    year over the plan's own ten-year table and $991,627 planned for FY27 -- so a dollar
    redirected to the schools is a dollar capital does not have. Saying "$794,872 is
    available within the guideline" without saying that is half the story.

    **Two different quantities, and the page must not merge them.**

    *Dollars* is arithmetic and needs no assumption: redirect $R and the programme is
    funded by $R less. That is the honest headline and it is exact.

    *Which projects stop* is not arithmetic. It is a claim about how the Capital Planning
    Committee would behave, and this module reports it as a RANGE between two behaviours
    rather than as a number:

    - `strictLost` -- the committee holds its published ranking rigid and takes items off
      the bottom until the money is found. Because the list is lumpy this OVERSHOOTS: rank
      7 is a $494,500 roof and the four items below it come to $199,449, so ANY draw over
      that reaches the roof and removes $693,949 whether it needed $300,000 or $500,000.
    - `resequencedLost` -- the committee re-sequences, dropping whatever combination comes
      closest to the money removed. At $500,000 that is $500,000 exactly.

    The overshoot between them is not a cost. It is the **integrality gap** -- the price of
    assuming indivisible items in a fixed order -- and reporting it as the loss overstates a
    $300,000 redirect by 131%. There is $1,437,005 of ranked, costed, unfunded work in the
    queue to substitute into, so the rigid reading is the less likely of the two.

    **And only part of the programme is in play at all.** $594,000 of the $1,830,203 is the
    Vehicle Use Special Purpose Stabilization Fund, restricted to vehicles and equipment, so
    cancelling what it pays for frees nothing for the schools. A draw can strand $1,236,203,
    not the whole programme. An earlier version of this took items off the bottom of the
    full funded list and stranded a $259,000 front end loader with free cash that never paid
    for it.

    **Nothing here establishes which one happens.** We hold no instance of the committee
    re-ranking after a funding cut; the ranking is evidence of preference, not of
    procedure. `notes/DATA-WANTED.md` §3e names what would settle it.

    What survives either way, and is the reason the section exists at all: there is a
    queue, so no dollar removed gains slack anywhere.
    """
    import csv as _csv
    import itertools as _it
    import os as _os
    root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    path = _os.path.join(root, 'sources', 'data', 'capital-plan-fy27.csv')
    if not _os.path.exists(path):
        return None
    items = [dict(rank=int(r['rank']), dept=r['dept'], project=r['project'],
                  cost=float(r['cost']), funded=r.get('funded', 'yes'),
                  funding=r.get('funding', 'free_cash_or_taxation'))
             for r in _csv.DictReader(open(path))]
    funded = [i for i in items if i.get('funded', 'yes') == 'yes']
    unfunded = [i for i in items if i.get('funded', 'yes') != 'yes']
    total = sum(i['cost'] for i in funded)

    # Restricted money cannot be redirected and cannot be freed by redirecting something
    # else, so it is not in the set a draw can strand. Reconciled to the plan's own funding
    # page in both directions before anything is computed from it.
    restricted = [i for i in funded if i['funding'] == 'stabilization']
    convertible = [i for i in funded if i['funding'] != 'stabilization']
    restricted_total = sum(i['cost'] for i in restricted)
    convertible_total = sum(i['cost'] for i in convertible)
    if abs(restricted_total - PLANNED_FROM_STABILIZATION) > 0.01:
        raise AssertionError(
            f'the projects marked stabilization total {restricted_total:,.2f}; the capital '
            f'plan shows {PLANNED_FROM_STABILIZATION:,.2f} against that fund')
    if abs(convertible_total - (PLANNED_FROM_FREE_CASH + PLANNED_FROM_TAXATION)) > 0.01:
        raise AssertionError(
            f'the rest of the funded programme totals {convertible_total:,.2f}; free cash '
            f'plus taxation is '
            f'{PLANNED_FROM_FREE_CASH + PLANNED_FROM_TAXATION:,.2f}')

    by_rank_desc = sorted(convertible, key=lambda i: -i['rank'])

    def falls(redirect):
        """Off the bottom of the published ranking, in order, until the money is found."""
        lost, names = 0.0, []
        for it in by_rank_desc:
            if lost >= redirect:
                break
            lost += it['cost']
            names.append(dict(rank=it['rank'], dept=it['dept'], project=it['project'],
                              cost=round(it['cost'])))
        return round(lost), names

    costs = [i['cost'] for i in convertible]

    def closest_fit(redirect):
        """The least the programme can lose and still find `redirect`, re-sequencing freely.

        Twelve funded items, so this enumerates all 4,096 subsets rather than approximating.
        """
        if redirect <= 0:
            return 0
        best = None
        for k in range(1, len(costs) + 1):
            for combo in _it.combinations(costs, k):
                s = sum(combo)
                if s >= redirect and (best is None or s < best):
                    best = s
        return round(best) if best is not None else round(convertible_total)

    history = _funding_history()
    avg = (sum(h['freeCash'] for h in history) / len(history)) if history else None
    # Rule 13. The plan prints its own Average; if ours does not reproduce it the extract
    # is missing rows, which is exactly how this was wrong before.
    avg_total = (sum(h['total'] for h in history) / len(history)) if history else None
    for got, printed, what in ((avg, PLAN_PRINTED_AVG_FREE_CASH, 'free cash into capital'),
                               (avg_total, PLAN_PRINTED_AVG_TOTAL, 'the whole programme')):
        if got is not None and abs(got - printed) > 0.01:
            raise AssertionError(
                f'capital-funding-history.csv averages {got:,.2f} for {what}; the FY27 '
                f'capital plan prints {printed:,.2f} in its own Average row. The extract '
                f'does not tie to its source.')

    redirect_ceiling = spendable(BAND_LOW)
    last = history[-1] if history else None

    return dict(
        programmeTotal=round(total),
        plannedFromFreeCash=PLANNED_FROM_FREE_CASH,
        averageFromFreeCash=round(avg) if avg is not None else None,
        # The plan's own ten-year funding table. It is what makes the redirect ceiling
        # measurable against something other than this one exceptional year.
        history=[dict(fy=h['fy'], total=round(h['total']), freeCash=round(h['freeCash']))
                 for h in history],
        lastYear=(dict(fy=last['fy'], total=round(last['total']),
                       freeCash=round(last['freeCash']),
                       redirectAsMultiple=round(redirect_ceiling / last['freeCash'], 2))
                  if last and last['freeCash'] else None),
        # In how many of the plan's own years the ceiling exceeds the WHOLE free cash
        # contribution to capital. This is the capital-side twin of the normal-year
        # finding: the draw is affordable in this year and in few others.
        yearsRedirectExceedsFreeCash=sum(1 for h in history
                                         if redirect_ceiling > h['freeCash']),
        yearsCovered=len(history),
        redirectCeiling=round(redirect_ceiling),
        # Ranked, costed, and already below the funding line before free cash is touched.
        # This is what makes a dollar removed a dollar of requested work not done: there is
        # a queue, so nothing gains slack.
        queueValue=round(sum(i['cost'] for i in unfunded)),
        queueCount=len(unfunded),
        items=[dict(rank=i['rank'], dept=i['dept'], project=i['project'],
                    cost=round(i['cost']), funded=i['funded'] == 'yes',
                    funding=i['funding']) for i in items],
        # A third of the programme is the Vehicle Use Special Purpose Stabilization Fund,
        # which is restricted to vehicles and equipment. It is not money the schools could
        # have had, so it is not in what a draw can strand.
        plannedFromTaxation=PLANNED_FROM_TAXATION,
        restrictedTotal=round(restricted_total),
        convertibleTotal=round(convertible_total),
        restrictedItems=[dict(rank=i['rank'], dept=i['dept'], project=i['project'],
                              cost=round(i['cost'])) for i in restricted],
        atDraw=[dict(redirect=round(spendable(t / 100)),
                     # Dollars out of the programme. Exact, and equal to the redirect --
                     # capped at the programme, which cannot lose more than it holds.
                     lost=round(min(max(spendable(t / 100), 0), convertible_total)),
                     strictLost=falls(max(spendable(t / 100), 0))[0],
                     resequencedLost=closest_fit(max(spendable(t / 100), 0)),
                     projects=falls(max(spendable(t / 100), 0))[1])
                for t in range(0, 9)],
    )


def export(deficits, project_fn=None, levy_cap=0.025):
    return dict(
        certified=CERTIFIED, identified=IDENTIFIED,
        budgetBase=BUDGET_BASE, budgetRevised=BUDGET_REVISED,
        townImpliedBase=TOWN_IMPLIED_BASE, townPublishedShare=0.0665,
        currentShare=round(share(), 4),
        bandLow=BAND_LOW, bandHigh=BAND_HIGH, bandSource=BAND_SOURCE,
        townHistory=TOWN_HISTORY, yearOffsetNote=YEAR_OFFSET_NOTE,
        history=[dict(year=y, certified=v) for y, v in HISTORY],
        unspent2025=UNSPENT_2025, unspentAvg=UNSPENT_AVG_2021_24,
        certifiedRatio=CERTIFIED_RATIO,
        normalCertified=NORMAL_CERTIFIED, normalShare=round(NORMAL_SHARE, 4),
        peerMultiples=[dict(town=t, multiple=m) for t, m in PEER_MULTIPLES],
        peerComposition=peer_composition(),
        peerDenominatorNote=PEER_DENOMINATOR_NOTE,
        deficits=[dict(fy=fy, amount=a) for fy, a in deficits],
        ladder=[dict(target=t / 100, released=round(spendable(t / 100)),
                     covers=years_covered(deficits, t / 100))
                for t in range(0, 9)],
        # Computed by finance.project itself, so what the page shows is what the model
        # produces rather than a second implementation of the same rule.
        scenarios=scenarios(project_fn) if project_fn else [],
        overrideContrast=(override_contrast(project_fn, levy_cap, spendable(BAND_LOW))
                          if project_fn else None),
        sustainableDraw=SUSTAINABLE_DRAW,
        policyStops=[dict(target=t, label=l) for t, l in POLICY_STOPS],
        policyLadder=policy_ladder(project_fn) if project_fn else [],
        capital=capital_consequence(),
    )
