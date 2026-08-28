"""Special education, measured from budget columns only.

Every figure here comes from a column recording what somebody voted or proposed:
`fy25_budget`, `fy26_final`, `fy27_level_service`, `fy27_balanced`. No actual-spending
column is read anywhere in this file, and `scripts/audit_provenance.py` enforces that.

Why this module exists at all. The state's function codes cannot separate special
education from everything else: 2330 is paraprofessionals of both kinds and 3300 is
transportation of both. Bucketing on the code alone put about $5.7M of special education
staffing inside `salaries` at the teachers' contract rate, which averaged together two
lines that behave nothing alike.

--------------------------------------------------------------------------------------
THE RATE, AND WHY IT IS NOT WHAT THE LINE DID
--------------------------------------------------------------------------------------

The obvious number is 5.89% -- what the whole line did across three budgets. It was the
published choice for a day, and it is wrong, for the same reason this analysis says the
district's own 3.98% is wrong.

Decompose the two years and the whole thing is one line moving once:

    whole line          5,038,594 -> 5,158,207 -> 5,649,284    +2.4%, +9.5%
    paraprofessionals   1,376,893 -> 1,344,373 -> 1,874,411    -2.4%, +39.4%
    everything else     3,661,701 -> 3,813,834 -> 3,774,873    +4.2%, -1.0%

The paraprofessional increase is 108% of the FY27 rise -- every other part of special
education fell that year. Strip it out and the rest of the line grew 1.53% a year across
the two budgets, below the levy cap.

So 5.89% is not a growth rate. It is one hiring decision, averaged over two years and
then compounded forever. Rule 6 exists for exactly this: a short rate off a step change
is not a trend, and three of the six lines the back-test flagged turned out to be steps.

The distinction is the one the whole site is built on. A **level** change moves the curve
once and leaves its angle alone. A **rate** changes the angle. Those aides were hired;
their cost is already inside the $5,745,543 the model starts from. Escalating that base
at 5.89% says the district will hire 39% more aides again next year, and again the year
after. Nothing supports that.

What the model uses instead is what the people in this line are contracted to receive,
weighted by how much of the line each of them is.

--------------------------------------------------------------------------------------
WHAT THIS RATE IS NOT
--------------------------------------------------------------------------------------

It is not a claim that special education is under control, and it is not a forecast. It
assumes one specific thing: that the FY27 hiring was a step and not the first year of a
climb. If more aides are hired every year -- because more children arrive needing one,
or because the ones here need more -- this rate is too low and the model understates the
gap. Nothing in a budget column can distinguish those, because a budget shows dollars per
line and never shows people, and the district does not publish staff counts.

The range below is published beside the rate for that reason. It is not decoration.
"""
import csv, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINES = os.path.join(ROOT, 'sources/data/lps-budget-lines.csv')
DESE = os.path.join(ROOT, 'sources/dese/selected-populations.csv')

# Budget columns, in order. Named here so that nothing downstream has to remember which
# of the workbook's fifteen columns record an intention and which record a payment.
FY25, FY26, FY27LS, FY27BAL = ('fy25_budget', 'fy26_final',
                               'fy27_level_service', 'fy27_balanced')

# Function groups that are special education outright. Out-of-district tuition (9300,
# 9400) is deliberately NOT here: it keeps its own escalator, because it is set by
# placement rather than by payroll and behaves nothing like staffing.
SPED_GROUPS = {
    '2110 - Special Education',
    '2110 - Special Education Clerical',
    '2310 - Teachers Specialists - Special Education',
    '2320 - Therapeutic Services',
    '2325 - Special Education Substitutes',
    '2330 - Paraprofessionals Special Education *** (LTP notes)',
    '2800 - Psych. Services',
    '2800 - Psychological Services',
}


def is_sped(row):
    """Whether a budget line is special education, tuition aside.

    Group membership first, then the line itself for the ones inside a mixed group --
    special education transport among the bus routes, special education materials among
    each school's supplies.
    """
    group = (row['function_group'] or '').strip()
    if group.startswith(('9300', '9400')):
        return False
    if group in SPED_GROUPS:
        return True
    item = (row['line_item'] or '').lower()
    return 'special ed' in item or 'specl ed' in item


def is_tuition(row):
    return (row['function_group'] or '').strip().startswith(('9300', '9400'))


def rows():
    return [r for r in csv.DictReader(open(LINES)) if r['kind'] == 'line']


def _n(r, col):
    return float(r[col]) if r[col] else 0.0


def total(col, pred=lambda r: True, rs=None):
    return sum(_n(r, col) for r in (rs if rs is not None else rows()) if pred(r))


# --------------------------------------------------------------------- the parts
_g = lambda r: (r['function_group'] or '').strip()
_item = lambda r: (r['line_item'] or '').lower()

PARTS = [
    ('paras', 'Paraprofessionals', lambda r: '2330' in _g(r)),
    ('transport', 'Special education transport',
     lambda r: '3300' in _g(r) or 'transport' in _item(r)),
    ('therapy', 'Speech, OT and summer services',
     lambda r: '2320' in _g(r) or 'summer' in _item(r)),
    ('subs', 'Substitutes', lambda r: '2325' in _g(r)),
    ('psych', 'Psychologists and testing', lambda r: '2800' in _g(r)),
    ('teachers', 'Special education teachers', lambda r: '2310' in _g(r)),
]


def _part_pred(key):
    """The named part, with earlier parts subtracted so nothing is counted twice."""
    seen = []
    for k, _, pred in PARTS:
        if k == key:
            prior = list(seen)
            return lambda r: is_sped(r) and pred(r) and not any(p(r) for p in prior)
        seen.append(pred)
    raise KeyError(key)


def decomposition():
    """Every part of the in-district line across three budgets, plus the remainder.

    The remainder is computed rather than enumerated, so the parts always sum to the
    line: a category boundary that drifts shows up as a moving remainder instead of as
    a total that quietly stops reconciling.
    """
    rs = rows()
    out, claimed = [], []
    for key, label, _ in PARTS:
        pred = _part_pred(key)
        claimed.append(pred)
        v = [total(c, pred, rs) for c in (FY25, FY26, FY27LS)]
        out.append(dict(id=key, label=label, fy25=v[0], fy26=v[1], fy27=v[2]))
    rest = lambda r: is_sped(r) and not any(p(r) for p in claimed)
    v = [total(c, rest, rs) for c in (FY25, FY26, FY27LS)]
    out.append(dict(id='other', label='Administration, legal, supplies and contracted work',
                    fy25=v[0], fy26=v[1], fy27=v[2]))
    return out


# ---------------------------------------------------- the long series, and trend tests
# Three budget years cannot tell a step from a climb. The archive's mirror of the
# district's budget page reaches FY17, and `scripts/extract_budget_history.py` reads the
# lines out of it -- budget columns only, one budget stage held constant, validated
# against the FY27 workbook where the two overlap.
#
# What it is for: every rate below is now measured over nine or ten budgets instead of
# two, and each one carries the test of whether it is a trend at all. That test is the
# difference between out-of-district tuition, which has an R-squared of 0.10 and is
# therefore held flat, and paraprofessionals, which have 0.89 and are not.
HISTORY = {
    'tuition': 'ood-tuition-history.csv',
    'paras': 'sped-para-history.csv',
    'transport': 'sped-transport-history.csv',
    'teachers': 'sped-teacher-history.csv',
}


def history(name, workbook=None):
    """One line, budget by budget. `workbook` fills years the documents do not reach."""
    path = os.path.join(ROOT, 'sources/data', HISTORY[name])
    if not os.path.exists(path):
        return []
    by_year = {}
    for r in csv.DictReader(open(path)):
        by_year.setdefault(int(r['fy']), {})[r['stage']] = float(r['total'])
    years = sorted(set(by_year) | set(workbook or {}))
    out = []
    for fy in years:
        stages = by_year.get(fy, {})
        # A settled figure -- one reported after the year was over -- beats a proposal,
        # and the workbook beats both where it has the year, because it is the tidy
        # extract everything else on this site is computed from.
        if workbook and fy in workbook:
            v, src = workbook[fy], 'workbook'
        elif 'settled' in stages:
            v, src = stages['settled'], 'settled'
        elif 'proposed' in stages:
            v, src = stages['proposed'], 'proposed'
        else:
            continue
        out.append(dict(fy=fy, total=v, stage=src))
    return out


def trend(series):
    """Whether a series has a direction, and how much that answer depends on where you
    start. R-squared near zero means there is no rate to measure and saying one anyway is
    a choice dressed as a measurement."""
    v = [d['total'] for d in series]
    n = len(v)
    if n < 3:
        return {}
    xs = list(range(n))
    mx, my = sum(xs) / n, sum(v) / n
    slope = (sum((x - mx) * (y - my) for x, y in zip(xs, v))
             / sum((x - mx) ** 2 for x in xs))
    inter = my - slope * mx
    sst = sum((y - my) ** 2 for y in v)
    ssr = sum((y - (inter + slope * x)) ** 2 for x, y in zip(xs, v))
    end, endfy = v[-1], series[-1]['fy']
    # A zero year would make a compound rate undefined; there are none in these series,
    # and if one ever appears it should be looked at rather than divided by.
    starts = [dict(fy=d['fy'], rate=(end / d['total']) ** (1 / (endfy - d['fy'])) - 1)
              for d in series[:-1] if d['fy'] != endfy and d['total'] > 0]
    rates = [c['rate'] for c in starts]
    return dict(
        n=n, firstFy=series[0]['fy'], lastFy=endfy,
        first=v[0], last=end, low=min(v), high=max(v), ratio=max(v) / min(v),
        lowFy=series[v.index(min(v))]['fy'], highFy=series[v.index(max(v))]['fy'],
        mean=my, vsMean=end / my - 1, slope=slope, r2=1 - ssr / sst,
        up=sum(1 for i in range(n - 1) if v[i + 1] > v[i]),
        down=sum(1 for i in range(n - 1) if v[i + 1] < v[i]),
        cagr=(end / v[0]) ** (1 / (endfy - series[0]['fy'])) - 1,
        cagrByStart=starts, cagrLow=min(rates), cagrHigh=max(rates),
        biggestFall=min((v[i + 1] / v[i] - 1, series[i + 1]['fy']) for i in range(n - 1)),
        biggestRise=max((v[i + 1] / v[i] - 1, series[i + 1]['fy']) for i in range(n - 1)),
    )


def _workbook(pred):
    rs = rows()
    return {2025: total(FY25, pred, rs), 2026: total(FY26, pred, rs),
            2027: total(FY27LS, pred, rs)}


# The five school paraprofessional lines only, which is what the documents itemise. The
# workbook's 2330 group carries $2,000 more in contracted services; matching the basis is
# what makes the two agree to the dollar where they overlap.
def _para_schools(r):
    return ('2330' in _g(r) and is_sped(r)
            and 'paraprofessional' in (r['line_item'] or '').lower())


PARA_SERIES = history('paras', _workbook(_para_schools))
PARA_TREND = trend(PARA_SERIES)
TRANSPORT_SERIES = history('transport', _workbook(_part_pred('transport')))
TRANSPORT_TREND = trend(TRANSPORT_SERIES)


# The five school teacher lines, matching what the documents itemise. The workbook's 2310
# group also carries hospital tutoring and contracted evaluations, which are purchased
# services rather than staff and do not belong in a test of what staff cost.
def _teacher_schools(r):
    item = (r['line_item'] or '').lower()
    return ('2310' in _g(r) and is_sped(r)
            and ('teacher' in item or 'tchr' in item or 'teach' in item))


TEACHER_SERIES = history('teachers', _workbook(_teacher_schools))
TEACHER_TREND = trend(TEACHER_SERIES)


# ------------------------------------------------------------------ the contracts
# There is no special education bargaining unit. Professional staff are on the teachers'
# agreement and aides on the paraprofessionals'; the buses are a vendor contract and the
# substitutes and supplies are not bargained at all. So the rate this line escalates at
# is a weighted average of contracts that were signed for other reasons.
#
# The two bargained rates are published. The vendor rate is not, so it has to be measured
# -- and the measurement is sensitive, which is stated rather than smoothed over:
#
#     transport, three budgets   445,328 -> 565,734 -> 649,953
#         FY25->FY26  +27.0%     FY26->FY27  +14.9%     two-year  +20.8%/yr
#
#     resulting blend    3.72%  at the district's own FY27 transport assumption of 10%
#                        4.28%  at the single most recent year          <- used
#                        4.96%  at the two-year rate
#
# The most recent year is used because it is the one measured on the same pair of budgets
# as everything else here, and because it is the middle of the three rather than the
# convenient end. A reader who prefers either of the others can see what it costs.
# A component escalates at its CONTRACT where a contract governs it and the line behaves
# accordingly, and at what it has MEASURABLY DONE where it does not. Which of those
# applies is decided by the trend test above, not by preference:
#
#   professional staff  NOT their 3.5% agreement. Eight budgets, FY20 to FY27, growing
#                       2.67% a year with an R-squared of 0.84 -- below contract, which
#                       means headcount here has been drifting DOWN. Using the contract
#                       rate assumed it holds, and overstated this component.
#   paraprofessionals   NOT their 2.0% contract. Ten budgets, FY18 to FY27, $634,513 to
#                       $1,872,411 -- 2.95x, R-squared 0.89, eight of nine years up, and a
#                       compound rate between +11.5% and +17.0% wherever you start it.
#                       This is headcount, and no pay settlement reaches it. Pricing it at
#                       2.0% assumes the district stops adding aides.
#   transport           no published vendor escalator, so measured -- but over the whole
#                       nine years rather than the most recent one. R-squared is 0.33: a
#                       weak trend, used because it is the least bad figure available and
#                       not because the line is well behaved.
#   unbargained         substitutes and supplies, identical in every budget held.
#
# An earlier version of this file priced the aides at their contract rate, on the argument
# that FY27's 39% increase was a one-time step already sitting in the base. The argument
# was sound and its premise was false: with two budget years there is no way to tell a step
# from a climb, and the archive reaches far enough to show it is a climb.
LEA_RATE = 0.035                          # teachers' agreement, FY27 -- shown, not used
PROFESSIONAL_RATE = TEACHER_TREND['cagr']  # measured, eight budgets, R^2 = 0.84
AFSCME_RATE = 0.020                       # aides' agreement -- deliberately NOT used
PARA_RATE = PARA_TREND['cagr']            # measured, ten budgets, R^2 = 0.89
TRANSPORT_RATE = TRANSPORT_TREND['cagr']  # measured, nine budgets, R^2 = 0.33
UNBARGAINED_RATE = 0.0

CONTRACT_UNITS = [
    ('professional', 'Professional staff',
     f'Measured over {TEACHER_TREND["n"]} budgets. Their agreement gives '
     f'{LEA_RATE:.1%} and the line has run below it \u2014 headcount drifting down, not '
     f'a smaller pay rise',
     PROFESSIONAL_RATE,
     lambda r: is_sped(r) and not any(f(r) for f in (
         _part_pred('paras'), _part_pred('transport'), _part_pred('subs')))),
    ('paras', 'Paraprofessionals',
     f'Measured over {PARA_TREND["n"]} budgets rather than taken from the 2.0% contract '
     f'\u2014 this line is headcount, and no settlement reaches it',
     PARA_RATE, _part_pred('paras')),
    ('transport', 'Transport',
     f'Vendor contract with no published escalator; measured over '
     f'{TRANSPORT_TREND["n"]} budgets', TRANSPORT_RATE, _part_pred('transport')),
    ('unbargained', 'Substitutes and supplies',
     'Not bargained; identical in every budget held', UNBARGAINED_RATE,
     _part_pred('subs')),
]


def contract_blend():
    """Each unit's share of the line, and what the blend comes to."""
    rs = rows()
    line = total(FY27LS, is_sped, rs)
    out = []
    for key, label, basis, rate, pred in CONTRACT_UNITS:
        amount = total(FY27LS, pred, rs)
        out.append(dict(id=key, label=label, basis=basis, rate=rate,
                        amount=amount, share=amount / line))
    return out, sum(u['share'] * u['rate'] for u in out)


UNITS, RATE = contract_blend()


def _share(unit_id):
    return next(u['share'] for u in UNITS if u['id'] == unit_id)


# ------------------------------------------------------------------- the range
def _series(pred):
    rs = rows()
    return [total(c, pred, rs) for c in (FY25, FY26, FY27LS)]


def _cagr(s):
    return (s[2] / s[0]) ** 0.5 - 1


_whole = _series(is_sped)
_paras = _series(_part_pred('paras'))
_nopara = _series(lambda r: is_sped(r) and not _part_pred('paras')(r))

WHOLE_LINE_RATE = _cagr(_whole)          # 5.89% -- what the line did, step included
EX_PARAS_RATE = _cagr(_nopara)           # 1.53% -- the line apart from the hiring
FY27_ALONE_RATE = _whole[2] / _whole[1] - 1   # 9.52%

# What the FY27 year actually was: one line moving, and moving by more than the whole
# year's increase, because everything else in special education fell.
PARA_FY27_RATE = _paras[2] / _paras[1] - 1
PARA_FY27_CHANGE = _paras[2] - _paras[1]
PARA_SHARE_OF_RISE = PARA_FY27_CHANGE / (_whole[2] - _whole[1])

RANGE = [
    dict(id='ex_paras', rate=EX_PARAS_RATE,
         label='Special education apart from the aides, two budgets',
         what='What the rest of the line did while the aides were being added. Below the '
              'levy cap — and it is the aides, not the rest, that make this line a driver.'),
    dict(id='contracts_only', rate=(LEA_RATE * _share('professional')
                                    + AFSCME_RATE * _share('paras')),
         label='If every settlement were the whole story',
         what='The two bargained agreements at their published rates and nothing else — '
              'no bus increase, no change in how many people are employed. Published here '
              'because it is what this model used to assume, and because the gap between '
              'it and the rate above is the part of this line that pay settlements do '
              'not explain.'),
    dict(id='whole', rate=WHOLE_LINE_RATE,
         label='The whole line, two budgets',
         what='What the in-district line did between the last two budgets. Close to the '
              'rate used, and reached a different way.'),
    dict(id='contracts', rate=RATE, used=True,
         label='Each part at its contract, or at what it has measurably done',
         what='Professional staff at the teachers’ agreement; aides and buses at what ten '
              'and nine budgets show them doing, because no contract governs how many '
              'people are employed. Weighted by each part’s share of the line.'),
    dict(id='fy27', rate=FY27_ALONE_RATE,
         label='FY27 by itself',
         what='The single steepest year. One observation, and the top of the range.'),
]
RANGE.sort(key=lambda r: r['rate'])


# --------------------------------------------------- the year, and the one-off in it
def level_service_year():
    """The district's own level-service rate, and the same rate without the one-off.

    Out-of-district tuition was budgeted down 46% in a single year. That is a level
    change -- placements can come home once, and there is no second 46% -- so the
    published rate describes a year that cannot repeat.
    """
    rs = rows()
    fy26, fy27 = total(FY26, rs=rs), total(FY27LS, rs=rs)
    t26, t27 = total(FY26, is_tuition, rs), total(FY27LS, is_tuition, rs)
    flat = fy27 - t27 + t26
    return dict(fy26=fy26, fy27=fy27,
                published=fy27 / fy26 - 1,
                underlying=flat / fy26 - 1,
                bend=(flat - fy27) / fy26,
                tuition_fy26=t26, tuition_fy27=t27,
                tuition_change=t27 - t26, tuition_rate=t27 / t26 - 1)


# ------------------------------------------------------------------ tuition risk
# The widest single-assumption range in the model, and the reason it is a table of
# priced scenarios rather than a slider: a control invites a reader to pick the number
# that suits them, and the honest answer is that nobody knows which of these is right.
TUITION_SCENARIOS = [
    ('budgeted', 'As the district budgeted it for FY27', 700_142),
    ('midway', 'Midway back', 1_000_000),
    ('fy25', 'Back to the FY25 budget', 1_164_824),
    ('fy26', 'Back to the FY26 budget', 1_291_293),
]


def tuition_risk():
    """Each scenario priced against the live model. Imported late to avoid a cycle --
    finance reads RATE from this module."""
    import finance
    base = finance.expense_base()
    out = []
    for key, label, amount in TUITION_SCENARIOS:
        orig = finance.expense_base
        finance.expense_base = lambda *a, **k: {**base, 'sped_tuition': amount}
        try:
            gap = finance.project()[0]['deficit']
        finally:
            finance.expense_base = orig
        out.append(dict(id=key, label=label, tuition=amount, gap=gap))
    for r in out:
        r['delta'] = r['gap'] - out[0]['gap']
    return out


# ------------------------------------------------------------------ student counts
def students():
    """Every year the state publishes, not a chosen three.

    The document this came from quoted FY19, FY22 and FY26 -- and FY22 is the low point
    of the series. Three points chosen from eight is the shape of thing this project
    warns about everywhere else, so the whole series is carried and the app plots it.
    """
    if not os.path.exists(DESE):
        return []
    return [dict(fy=int(r['fy']), n=int(r['students_with_disabilities_n']),
                 pct=float(r['students_with_disabilities_pct']))
            for r in csv.DictReader(open(DESE))]


def export():
    y = level_service_year()
    return dict(
        rate=RATE, units=UNITS, range=RANGE, decomposition=decomposition(),
        year=y, tuitionRisk=tuition_risk(), students=students(),
        base=total(FY27BAL, is_sped), tuitionBase=total(FY27BAL, is_tuition),
        appropriation=total(FY27BAL),
        classified=classified(),
        tuitionRate=TUITION_RATE,
        tuitionHistory=tuition_history(), tuitionTrend=tuition_trend(),
        paraSeries=PARA_SERIES, paraTrend=PARA_TREND,
        professionalSeries=TEACHER_SERIES, professionalTrend=TEACHER_TREND,
        leaRate=LEA_RATE, afscmeRate=AFSCME_RATE,
        transportSeries=TRANSPORT_SERIES, transportTrend=TRANSPORT_TREND,
    )


if __name__ == '__main__':
    y = level_service_year()
    print(f"FY27 level service published {y['published']:.2%}, "
          f"underlying {y['underlying']:.2%} "
          f"(one line bends it {y['bend']*100:.2f} points)\n")
    print('The contracts that actually govern this line:')
    for u in UNITS:
        print(f"  {u['label']:<28} {u['share']:6.1%}  {u['rate']:6.2%}  {u['basis']}")
    print(f"  {'BLEND':<28} {'':6}  {RATE:6.2%}\n")
    print('The range:')
    for r in RANGE:
        print(f"  {r['rate']:6.2%}  {r['label']}{'   <- used' if r.get('used') else ''}")
    print('\nOut-of-district tuition risk:')
    for r in tuition_risk():
        delta = f"+${r['delta']:,}" if r['delta'] else '—'
        print(f"  ${r['tuition']:>10,}  FY28 gap ${r['gap']:>10,}  {delta}")


# ------------------------------------------------------- what counts, and why
# The one number on this page that is entirely ours.
#
# The state's account codes do not have a special education total. Two of the groups the
# district reports carry both kinds of cost -- 2330 is paraprofessionals general and
# special, 3300 is transportation general and special -- so any figure for "special
# education" is somebody's classification rather than a published quantity. This is ours,
# and a reader is entitled to see every line in it and add them up.
#
# The rule has exactly two parts:
#
#   1. Eight function groups are special education outright, and every line inside them
#      counts. These are listed in SPED_GROUPS.
#   2. Inside groups that carry both kinds, individual lines count when the district's own
#      label for them says special education. Eight lines, and one of them -- special
#      education transportation -- is most of the money.
#
# Out-of-district tuition is deliberately excluded and escalated separately: it is set by
# placement rather than payroll. General education paraprofessionals are excluded, which
# is the boundary most likely to be got wrong in either direction.

EXCLUDED = [
    ('2330 - Paraprofessionals General Education',
     'General education aides. The group next to the special education one, and the '
     'single boundary most likely to be crossed by accident in either direction.'),
]


def classified():
    """Every line counted, with the reason it was counted, and what sits just outside.

    Published so the total can be added up by hand. `basis` is either the function group
    -- the district's own account code -- or the district's own label for the line.
    """
    rs = rows()
    counted = []
    for r in rs:
        if not is_sped(r):
            continue
        g = (r['function_group'] or '').strip()
        counted.append(dict(
            group=g, item=(r['line_item'] or '').strip(),
            amount=_n(r, FY27BAL),
            basis='group' if g in SPED_GROUPS else 'name'))
    counted.sort(key=lambda x: -x['amount'])

    # Excluded lines carry all three budget years, not just FY27. A boundary can look
    # irrelevant in the year you happen to show and matter a great deal in the year you
    # are comparing against: general education aides are budgeted at nothing from FY26 on,
    # but they were $121,233 in FY25, which is the base year of the two-year rates above.
    excluded = []
    for group, why in EXCLUDED:
        pred = lambda r, g=group: (r['function_group'] or '').strip() == g
        excluded.append(dict(
            group=group, why=why, lines=sum(1 for r in rs if pred(r)),
            fy25=total(FY25, pred, rs), fy26=total(FY26, pred, rs),
            amount=total(FY27BAL, pred, rs)))
    excluded.append(dict(
        group='9300 / 9400 — out-of-district tuition',
        why='Special education, but escalated on its own because it is set by placement '
            'rather than by payroll, and it behaves nothing like staffing.',
        lines=sum(1 for r in rs if is_tuition(r)),
        fy25=total(FY25, is_tuition, rs), fy26=total(FY26, is_tuition, rs),
        amount=total(FY27BAL, is_tuition, rs)))

    return dict(counted=counted, excluded=excluded,
                groups=sorted(SPED_GROUPS),
                total=sum(c['amount'] for c in counted),
                byGroup=len([c for c in counted if c['basis'] == 'group']),
                byName=len([c for c in counted if c['basis'] == 'name']))


# ------------------------------------------------- out-of-district tuition, over time
# The model escalated this line at 8% a year and nothing supported the number. Its
# citation said only "our estimate", and the back-test flagged it as the worst-calibrated
# assumption in the model -- assumed 8.0%, observed -22.5%.
#
# The archive's mirror of the district's budget page reaches back to FY17, and those
# documents carry lines 9300 and 9400. `scripts/extract_tuition_history.py` reads them,
# taking the column each document itself labels as a budget and holding the budget STAGE
# constant -- a year has several budget figures at different stages and they are far
# apart, so a series that takes whichever number each document leads with is a walk across
# stages rather than a trend. Three of its years reproduce the FY27 workbook exactly,
# which is what makes the other eight worth trusting.
#
# WHAT IT SHOWS: no trend. Eleven budgets ranging from $489,918 to $1,291,293 -- a factor
# of 2.64 -- with six years up and four down and a straight-line fit of R^2 = 0.10.
#
# There is no rate here to measure, and that is the finding rather than a gap in it:
#
#     compound rate to FY27, by where you start it
#         from FY17   +0.66%      from FY22   -3.08%
#         from FY18   -0.91%      from FY23   +9.34%
#         from FY20   -2.99%      from FY26  -45.78%
#
# A figure that swings from -45.78% to +11.78% on the choice of start year is not a
# measurement of anything. Publishing 0.66% because FY17 happens to be the first year the
# archive reaches would be the same error as escalating the in-district line at 5.89% --
# an arbitrary choice wearing a measurement's clothes.
#
# So the line is held flat, and the risk is carried by the range instead, which is priced
# in TUITION_SCENARIOS above. That is the honest shape of what is known: nobody can say
# which direction this line moves next, and the useful thing to publish is how much it
# would cost to be wrong in either.
TUITION_RATE = 0.0
TUITION_HISTORY_CSV = os.path.join(ROOT, 'sources/data/ood-tuition-history.csv')


def tuition_history():
    """The series, settled figures where a later document reports one."""
    if not os.path.exists(TUITION_HISTORY_CSV):
        return []
    by_year = {}
    for r in csv.DictReader(open(TUITION_HISTORY_CSV)):
        by_year.setdefault(int(r['fy']), {})[r['stage']] = r
    out = []
    for fy in sorted(by_year):
        r = by_year[fy].get('settled') or by_year[fy]['proposed']
        out.append(dict(fy=fy, private=float(r['private']),
                        collaborative=float(r['collaborative']),
                        total=float(r['total']),
                        stage='settled' if 'settled' in by_year[fy] else 'proposed'))
    return out


def tuition_trend():
    """Whether the series has a direction. It does not, and this says so with numbers.

    The same trend test every other line here gets, so the R-squared of 0.10 on this line
    and the 0.89 on paraprofessionals are the same measurement and can be read against
    each other. That comparison is the argument: one of these lines is escalated at what
    it has done and the other is held flat, and this is why.
    """
    return trend(tuition_history())
