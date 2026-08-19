"""The six numbers, stated once, above everything else.

Each is derived elsewhere in the model; this module only assembles them so the banner
and the conclusions cannot drift apart.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from cascade import run, PRESETS
from finance import DEFAULT_ASSUMPTIONS
from taxbase import value_needed, AVG_COMMERCIAL_VALUE, MIX_VALUE, BUSINESSES
from health import split_change
from athletics import (PROGRAM_TOTAL_LEVEL_SERVICE, PROGRAM_TOTAL_ADOPTED,
                       PROGRAM_TOTAL_TRAVEL, EFFECTIVE_ATHLETIC_FEE,
                       CHARGEABLE_PARTICIPATIONS, SPORTS)

_years = run(PRESETS['school_committee']['order'], DEFAULT_ASSUMPTIONS, 5)
_gaps = [y['deficit'] for y in _years]
AVG_GAP_3YR = round(sum(_gaps[:3]) / 3)

# Only high-school participations can be charged: MS teams are unfunded.
_N = CHARGEABLE_PARTICIPATIONS


def _ath_revenue(fee, current=EFFECTIVE_ATHLETIC_FEE, dropoff=5, waiver=12):
    increase = max(0, fee - current)
    return fee * _N * (1 - waiver / 100) * max(0, 1 - (increase / 100) * (dropoff / 100))


_peak_fee, _peak_rev = max(((f, _ath_revenue(f)) for f in range(0, 3001, 5)),
                           key=lambda x: x[1])

# Against the honest basis: the teams that survived, able to travel.
_self_fund = next((f for f in range(0, 3001, 5)
                   if _ath_revenue(f) >= PROGRAM_TOTAL_TRAVEL), None)
_self_fund_nobus = next((f for f in range(0, 3001, 5)
                         if _ath_revenue(f) >= PROGRAM_TOTAL_ADOPTED), None)

_ACT_CAP, _ACT_P = 106_244, 375


def _act_revenue(fee, dropoff=6, waiver=15):
    return fee * _ACT_P * (1 - waiver / 100) * max(0, 1 - (fee / 100) * (dropoff / 100))


_act_fee = next((f for f in range(0, 3001, 5) if _act_revenue(f) >= _ACT_CAP), None)

_health = split_change(0.70)
_biz_value = value_needed(AVG_GAP_3YR)

HEADLINES = [
 dict(id='gap', label='The hole, every year',
      value=f'${AVG_GAP_3YR:,}',
      sub='Average annual shortfall FY28–FY30, after each year’s cuts compound',
      anchor='years', tone='critical'),

 dict(id='business', label='What business growth would have to deliver',
      value=f'${_biz_value/1e6:.1f}M',
      sub=f'of new commercial value every year — about {round(_biz_value/AVG_COMMERCIAL_VALUE)} '
          f'more average businesses a year, on top of the {BUSINESSES} the town has, or '
          f'{_biz_value/MIX_VALUE:.0f} typical developments',
      anchor='tax-base', tone='neutral'),

 dict(id='extras', label='Cutting every sport, band and club',
      value='$644,031',
      sub='All athletics, all arts and music, all clubs — eliminated entirely. Covers one '
          'year, once, and then the column is empty',
      anchor='the-money', tone='neutral'),

 dict(id='health', label='Health insurance, shifted 75/25 → 70/30',
      value=f"${round(_health['districtSaves']*0.75):,}",
      sub=f"in year one after the 25% owed back to employees "
          f"(${_health['districtSaves']:,} headline) — and it costs a family on the "
          f"broadest plan ${_health['perPlan'][0]['familyDelta']:,} a year",
      anchor='levers', tone='good'),

 dict(id='athletics_fee', label='Athletic fee that would make sports self-funding',
      value=f'${_self_fund}',
      sub=f'a season, against the ${PROGRAM_TOTAL_TRAVEL:,} it costs to field the teams '
          f'that survived AND get them to away games. Against the '
          f'${PROGRAM_TOTAL_ADOPTED:,} the budget actually funds — which pays for no '
          f'transportation at all — it is ${_self_fund_nobus}. Restoring the full '
          f'${PROGRAM_TOTAL_LEVEL_SERVICE:,} program is out of reach at any fee',
      anchor='fees', tone='critical'),

 dict(id='band_fee', label='Activity fee to make band, music and clubs self-funding',
      value=f'${_act_fee}',
      sub=f'per student per activity, covering the ${_ACT_CAP:,} those programs cost. '
          f'Reachable — but a steep charge for a school club',
      anchor='fees', tone='neutral'),
]

if __name__ == '__main__':
    for h in HEADLINES:
        print(f"{h['value']:>14}  {h['label']}")
        print(f"{'':>14}  {h['sub']}\n")
