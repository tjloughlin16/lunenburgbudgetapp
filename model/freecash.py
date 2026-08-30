"""Free cash: what it is, how much is spendable, and why it cannot bend the curve.

Two claims are argued about locally — that the town is too conservative and sitting on
money, and that free cash is "not up to standard" so the town is rebuilding. The reading is
in `sources/analyses/free-cash.md`; this module is the arithmetic behind the page.

**Rule 1 is the constraint that shapes this file.** The projection is built from budget
columns only. Free cash is derived from ACTUALS — it is, definitionally, the variance
between what was appropriated and what happened. The two must never meet inside a
calculation. So nothing here feeds `finance.project`, and nothing here escalates. What it
does is place two clearly-labelled quantities side by side and do subtraction, which is
arithmetic rather than a model.

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


def export(deficits):
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
    )
