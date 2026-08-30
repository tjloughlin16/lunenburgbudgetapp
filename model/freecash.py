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
    )
