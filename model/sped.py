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
LEA_RATE = 0.035          # teachers' agreement, FY27
AFSCME_RATE = 0.020       # paraprofessionals' agreement, FY28
TRANSPORT_RATE = (649_953 / 565_734) - 1     # measured; no published vendor escalator
UNBARGAINED_RATE = 0.0    # substitutes and supplies, flat in all three budgets

CONTRACT_UNITS = [
    ('professional', 'Professional staff', 'Teachers’ agreement (LEA)', LEA_RATE,
     lambda r: is_sped(r) and not any(f(r) for f in (
         _part_pred('paras'), _part_pred('transport'), _part_pred('subs')))),
    ('paras', 'Paraprofessionals', 'Paraprofessionals’ agreement (AFSCME 503)',
     AFSCME_RATE, _part_pred('paras')),
    ('transport', 'Transport', 'Vendor contract; no published escalator',
     TRANSPORT_RATE, _part_pred('transport')),
    ('unbargained', 'Substitutes and supplies', 'Not bargained', UNBARGAINED_RATE,
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
         what='What every other part of the line did while the aides were being hired. '
              'Below the levy cap.'),
    dict(id='contracts', rate=RATE, used=True,
         label='What the staff are contracted to receive',
         what='The two agreements at their published rates and the buses at what the '
              'budgets did, each weighted by its share of the line. Assumes the FY27 '
              'hiring was a step rather than the first year of a climb.'),
    dict(id='whole', rate=WHOLE_LINE_RATE,
         label='The whole line, two budgets',
         what='Includes the one-time 39% increase in aides, which was 108% of that '
              'year’s rise. Compounding it assumes the hiring repeats.'),
    dict(id='fy27', rate=FY27_ALONE_RATE,
         label='FY27 by itself',
         what='The single year the hiring happened. One observation.'),
]


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
        transportRates=dict(
            recent=TRANSPORT_RATE, twoYear=(649_953 / 445_328) ** 0.5 - 1,
            districtAssumption=0.10),
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
