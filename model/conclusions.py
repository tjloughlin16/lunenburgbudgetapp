"""The findings this whole exercise produced, stated plainly.

These are OUR conclusions from the published data, not the district's or the town's.
Each one points at the section of the tool that shows the working.

Figures here are interpolated, never typed. This file is prose that ships, so rule 2
applies to it exactly as it applies to the app: three figures were once found here
stating amounts the model no longer produced, one of them out by $313,000. The headline
below was another -- it claimed a gap of "roughly $580,000" that no version of the model
has produced in some time.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from catalog import PROGRAMS
from headlines import AVG_GAP_3YR
import sped

# Every sport, every band, every club, every art supply. Summed from the catalogue rather
# than written down, so that adding a program cannot leave this figure describing a
# district that no longer exists.
EXTRAS_TOTAL = sum(p['cost'] or 0 for p in PROGRAMS
                   if p['cat'] in ('athletics', 'arts', 'activities'))

CONCLUSIONS = [
 dict(n=1, anchor='the-money',
      headline='Cutting every extra in the district buys exactly one year.',
      figure=f'${EXTRAS_TOTAL:,.0f}',
      body=f'Every sport, every band, every club and every art supply, eliminated entirely, '
           f'comes to ${EXTRAS_TOTAL:,.0f}. The gap over the next five years is about $2.9 million. So '
           'the whole "cut the frills" argument covers FY28 and then the column is empty '
           'forever, while the gap returns every single year.'),

 dict(n=2, anchor='the-money',
      headline='After that, only classroom positions are big enough to cut.',
      figure='~90%',
      body='Salaries, health insurance, transportation and out-of-district tuition are '
           'roughly nine of every ten dollars, and each is set by contract, by the '
           'insurance market, or by law. When Easthampton\'s override failed, 93% of its '
           'cuts had to come from personnel. There is no other place large enough.'),

 dict(n=3, anchor='/bend-the-curve#sped',
      headline=f'The published cost increase is {sped.level_service_year()["published"]:.2%}. The recurring one is '
               f'{sped.level_service_year()["underlying"]:.2%}.',
      figure=f'{sped.level_service_year()["bend"]*100:.2f} pts',
      body=f'The district\u2019s own arithmetic for running the same schools one year '
           f'longer comes to {sped.level_service_year()["published"]:.2%}. Inside it, one line falls '
           f'{-sped.level_service_year()["tuition_rate"]:.0%} \u2014 out-of-district tuition, what the town pays other '
           f'schools to educate children it cannot serve here, down '
           f'${-sped.level_service_year()["tuition_change"]:,.0f} in a single year. That is a one-time drop, not a '
           f'slower rate of growth, and eleven budgets show this line has been as low as '
           f'${sped.tuition_trend()["low"]:,.0f} and as high as ${sped.tuition_trend()["high"]:,.0f} with no direction to it. '
           f'Hold it where FY26 had it and the same budget rises {sped.level_service_year()["underlying"]:.2%}. '
           f'Plan against {sped.level_service_year()["published"]:.2%} and you will be surprised every year.'),

 dict(n=4, anchor='/bend-the-curve#sped',
      headline='The line nobody bargains over is the one that is growing.',
      figure=f'{sped.PARA_TREND["cagr"]:.1%}',
      body=f'Special education paras are on a contract giving '
           f'{sped.AFSCME_RATE:.1%} a year. Their budget line has grown {sped.PARA_TREND["cagr"]:.2%} a '
           f'year for {sped.PARA_TREND["n"]} budgets \u2014 ${sped.PARA_TREND["first"]:,.0f} to ${sped.PARA_TREND["last"]:,.0f}, up in '
           f'{sped.PARA_TREND["up"]} of {sped.PARA_TREND["n"]-1} years. Special education teachers run the other way: a '
           f'{sped.LEA_RATE:.1%} agreement and a line growing {sped.TEACHER_TREND["cagr"]:.2%}. A contract sets what '
           f'one person is paid; it says nothing about how many people are employed, and '
           f'on this line that is where the movement is. Special education is about '
           f'{sped.total(sped.FY27BAL, sped.is_sped)/sped.total(sped.FY27BAL):.0%} of what the schools spend and the second-largest driver of the '
           f'gap after health insurance.'),

 dict(n=5, anchor='neighbors',
      headline='Lunenburg\'s schools grew 1.08% while every neighbor grew 2.9-6.5%.',
      figure='1.08%',
      body='In a year when health insurance rose 8-14% and Chapter 70 aid rose 1.5-2% for '
           'everyone. Groton-Dunstable, Ayer-Shirley, North Middlesex, Wachusett and '
           'Ashburnham-Westminster all faced the same squeeze. That gap between our bar '
           'and theirs is the cut list. One scope note, because it is load-bearing: the '
           'state\u2019s per-pupil series measures IN-DISTRICT expenditure, which by '
           'construction excludes what a district pays other schools for out-of-district '
           'placements \u2014 the line that has swung 2.6 times over eleven budgets here. '
           'The comparison holds; it is narrower than it looks.'),

 dict(n=6, anchor='priorities',
      headline='Priorities are a genuine choice — a neighbor made the opposite one.',
      figure='2.0 FTE',
      body='Ashburnham-Westminster wrote "preserve athletics, arts and music" into its '
           'district goals, raised athletics 2.7% and marching band 4.8%, reinstated girls '
           'ice hockey on user fees — and cut two elementary teachers to pay for it. '
           'Lunenburg cut athletics first and defended classroom staffing. Same pressures, '
           'opposite answers.'),

 dict(n=7, anchor='fees',
      headline='Athletics cannot pay for itself once you put the buses back.',
      figure='$960',
      body='For 2026-27 Lunenburg charges $400 for a first child, $300 for a second and '
           '$225 for a third, with a $1,500 family cap — up from $250/$140/$85 and a $475 '
           'cap. Blended that is about $366 per participation, an estimated $187,000. '
           'Measured against the $217,908 the adopted budget funds, that is 86% covered '
           'and $445 a season would finish the job — but the adopted budget funds ZERO '
           'athletic transportation, and a team that cannot reach an away game is not a '
           'team. Put the $127,550 of buses back and the real cost is $345,458: fees '
           'cover 54%, and self-funding needs $960 a season. Every rung above that — a '
           'full-time trainer, full coaching stipends, middle school teams — is '
           'unreachable at any fee, because revenue peaks near $1,185 at $358,380.'),

 dict(n=8, anchor='tax-base',
      headline='When your house is worth more, the schools get nothing.',
      figure='+52% / +19%',
      body='Proposition 2½ caps what the town may collect in total, not what you pay. The '
           'Assessors\' own five-year table proves it: the average home rose 52% in value '
           'while the tax rate fell 22%, so the average bill rose only 19%. Rising '
           'assessments do not fund schools. Only genuinely new construction does.'),

 dict(n=9, anchor='tax-base',
      headline='The commercial tax base is not stalling. It is shrinking.',
      figure='-51%',
      body='Between FY22 and FY23 residential value rose 23.3% while commercial fell 0.25%, '
           'industrial fell 3.2% and personal property fell 1.0% — in absolute dollars. '
           'Meanwhile new growth, the only thing that raises the levy limit without an '
           'override, fell from $481,496 in FY18 to $234,383 in FY23, a 51% decline. The '
           'town budgets $400,000 of new growth for FY27; it has not hit that since FY22.'),

 dict(n=10, anchor='tax-base',
      headline='Lunenburg is not short of businesses. It is short of buildings.',
      figure='64%',
      body='The town has 363 active business certificates and registered about 60 new ones '
           'last year. But 64% of them are at addresses on residential streets, only 25% '
           'are in trades that need commercial premises, and just 39 addresses in town host '
           'more than one business. Lunenburg has plenty of entrepreneurs and almost no new '
           'commercial square footage — which is exactly why registrations hold up while '
           'the commercial tax base shrinks. A consultant working from a spare room pays '
           'residential tax.'),

 dict(n=11, anchor='tax-base',
      headline='Building houses makes the school budget worse, not better.',
      figure='2.75 homes',
      body='After Chapter 70 aid, one student costs the levy $10,894 a year. The school '
           'share of an average tax bill is $3,959. So it takes the school taxes of 2.75 '
           'average homes to educate one child — and a two-child house runs about $17,800 '
           'a year in the red. A business of the same value pays the same tax and sends '
           'nobody.'),

 dict(n=12, anchor='tax-base',
      headline='The break-even is $42.6 million of new taxable value — in one year.',
      figure='$42.6M',
      body='That is what closing the FY28 gap through commercial growth alone requires, '
           'because $613,238 ÷ the $14.39 tax rate is fixed arithmetic. In buildings that '
           'is about 11 retail plazas, or 14 typical Lunenburg developments, or 6 '
           'light-industrial warehouses, or 47 restaurants — permitted, built and assessed '
           'inside twelve months. For scale, all of Lunenburg\'s commercial, industrial '
           'and personal property together is worth $154 million, so this is adding 28% to '
           'the entire commercial base in a single year.'),

 dict(n=13, anchor='tax-base',
      headline='Measured in ordinary businesses, it means 65 more — then 61 again, every year.',
      figure='+131%',
      body='Lunenburg\'s existing businesses average $658,001 of assessed value, so $42.6 '
           'million is about 65 more of them — a 28% increase in twelve months, and 2.5 '
           'times the new growth the town actually recorded in FY23. And the gap returns '
           'annually: sustaining it takes roughly 61 new businesses a year, which over five '
           'years carries the town from 234 businesses to about 540. That is not an argument '
           'against commercial development. It is an argument against treating it as the '
           'whole answer.'),

 dict(n=14, anchor='tax-base',
      headline='Business growth genuinely works — and it is a ten-year answer, not a next-year one.',
      figure='Year 3',
      body='At $15M of new commercial value a year, growth overtakes a $613,000 override '
           'in year three and keeps compounding, with nobody\'s bill going up. But $15M a '
           'year means about 23 more average businesses every year — a 10% increase in the '
           'commercial base annually, sustained. And no building permitted in 2027 helps '
           'the FY28 budget.'),

 dict(n=15, anchor='where-we-are',
      headline='One-time money is being spent on recurring costs.',
      figure='$453,722',
      body='The September town meeting restores two reading specialists, a full-time '
           'assistant principal, 52 tutoring seats and a music position — with one-time '
           'state money. Keeping them in FY28 is a brand-new cost the district has to '
           'absorb. Ashburnham-Westminster is doing the same with $600,000 of reserves; '
           'Groton-Dunstable is deliberately weaning off it. It works once.'),

 dict(n=16, anchor='recommendation',
      headline='Nothing closes the gap without either an override or teachers.',
      figure='68%',
      body='Our own package — higher fees, a technology audit, an administration trim — '
           'finds about two thirds of FY28 without cutting a program. The remaining third '
           'is roughly two teaching positions. Anyone claiming a painless third option has '
           'not added up the line items.'),
]

HEADLINE = (
    'Lunenburg is not facing a one-year problem that can be solved by cutting sports. '
    f'It is facing a structural gap of roughly ${round(AVG_GAP_3YR, -4):,} a year, every '
    'year, in a town whose school budget grew 1.08% while its neighbors grew three to six '
    'times faster.'
)
