#!/usr/bin/env python3
"""The Monty Tech assessment -- what sets it, and what it has done.

    python3 scripts/build_monty_tech.py
    python3 scripts/build_monty_tech.py --check

Writes `fy28/public/data/monty-tech.json`, which /monty-tech renders.

WHAT THIS PAGE IS ABOUT. Montachusett Regional Vocational Technical -- "Monty Tech" -- is
the larger of the two routes Lunenburg children take out of the town's own schools: 97 of
them in FY2026 against 58 under school choice, and it has risen in seven of the last eight
years. Nothing else on this site measures it. It is also structurally UNLIKE every other
line here, because it is an ASSESSMENT on a member town of a regional district rather than
an appropriation the town sets.

THE TRAP THIS GENERATOR EXISTS TO AVOID, stated first because it is the whole difficulty.

`report_monty_tech` -- 70 rows, all from ONE edition -- is Monty Tech's own budget book
reprinted inside Lunenburg's FY2017 annual town report. Its `column_meaning` is EMPTY and
its `status` is `no check`, which is rule 13's named trap exactly: `v1` there is an
ORDINAL, the first column of that page that held figures, not a column name. Its label
column has also absorbed the first printed figure (`Chapter 70   13,764,000`). NOTHING on
this page comes from that table and this generator asserts that it stays untouched.

The appropriation series in `report_appropriations` is better and still not clean. Every
row is `check failed` or `no check` -- the extractor's own reconciliation, failing -- and
CLAUDE.md forbids aggregating without splitting on `status`. So those figures are
CANDIDATES here, never established, they are drawn differently from the established
series, and every one carries its status beside it.

WHAT IS ESTABLISHED, AND HOW. The state-mandated part of the assessment is DERIVED, by
subtraction, from two columns of one DESE workbook that this project already holds:

    Lunenburg's required contribution to Monty Tech
        = the TOWN's required local contribution      (dese_ch70_contribution)
        - the SCHOOL DISTRICT's required local contribution  (dese_ch70_aid_factor)

That is a derivation and it is treated as one. It is checked at four separate points
against figures the district's own business director gave the Finance Committee in three
different years -- FY2023 $1,012,282, FY2024 $1,127,113, FY2026 $1,270,711, and the
foundation enrollment moving 83 to 94 -- and the generator refuses to write if any of those
four stops matching to the dollar.

THE APPORTIONMENT RULE IS MEASURED, NOT DESCRIBED. Two things fall straight out of the
same workbook and both are asserted here rather than asserted in prose:

1.  The town's TOTAL required contribution is set by WEALTH, not by enrollment.
    `target_local_contribution` equals `combined_effort_yield` in every year here -- the
    82.5%-of-foundation cap never binds -- so the town-wide obligation is a function of
    property value and resident income and of nothing about where children go to school.
2.  That total is split between the two districts in EXACT proportion to each district's
    share of the town's foundation budget. Checked to a tenth of a basis point; it holds
    in 19 of the 20 years published, and the one year it does not is named.

So the assessment is not apportioned among member towns by their enrollment share, which is
what "regional assessment" leads a reader to assume. It is Chapter 70's minimum required
local contribution, computed for the town as a whole and divided by foundation budget.

RULE 11 APPLIES WITH FULL FORCE AND THE PAGE LEADS WITH IT. The assessment is what
Lunenburg is BILLED. It is not what educating those children costs: Chapter 70 aid is paid
to the regional district directly, and everything else on that district's revenue side --
grants, competitive awards, its own choice receipts -- never touches this line. This
archive holds no Monty Tech budget book, so the cost side is a gap and is registered as
one.

RULE 1. Nothing here differences a budget against an actual. The appropriation candidates
are appropriations; the FY2026 ledger figure is what the accounting system says was
expended against an appropriation of the same amount; the DESE series is one formula
calculation per year throughout. Where two stages appear side by side the page says so.

RULE 2. Not one figure is typed into the page. Everything arrives from this file.
"""
import argparse
import collections
import csv
import json
import os
import re
import sqlite3
import sys

# The conclusions this report states, as DATA rather than as sentences in a page. See
# scripts/conclusions.py.
import conclusions as C
from conclusions import conclusion, emit, figure

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'monty-tech.json')
MINUTES = 'sources/meetings/text'

LPS_LEA = '01620000'          # Lunenburg Public Schools, in DESE's district tables
MT_LEA = '08320000'           # Montachusett Regional Vocational Technical.
#                               A district NAME is a rendering; the LEA is the key.
TOWN = 'Lunenburg'
LEDGER_FY = 2026
LEDGER_DEPT = '310'
LEDGER_PERIOD = '12'

# A series does not lose a decade. If a query comes back short, something moved underneath
# and publishing it would present a truncated series as a whole one.
MIN_REQUIRED_YEARS = 18
MIN_STUDENT_YEARS = 12
MIN_CANDIDATES = 10

# The four points at which the DERIVED required-contribution series is checked against a
# figure somebody stated in public, in a different document, in a different year. If one
# of these stops matching, the subtraction has stopped meaning what the page says it means
# and nothing is written.
CORROBORATION = [
    dict(fy=2023, field='mt_rlc', value=1012282,
         board='finance-committee', date='2022-03-23', doc='2056',
         who='the Monty Tech Business Director, to the Finance Committee',
         what='Lunenburg’s FY2023 required minimum contribution to Monty Tech'),
    dict(fy=2023, field='mt_fe', value=94,
         board='finance-committee', date='2022-03-23', doc='2056',
         who='the Monty Tech Business Director, to the Finance Committee',
         what='Lunenburg’s FY2023 foundation enrollment at Monty Tech'),
    dict(fy=2024, field='mt_rlc', value=1127113,
         board='finance-committee', date='2023-03-22', doc='92',
         who='the Monty Tech Business Director, to the Finance Committee',
         what='Lunenburg’s FY2024 required minimum contribution to Monty Tech'),
    dict(fy=2026, field='mt_rlc', value=1270711,
         board='finance-committee', date='2025-03-06', doc='7008',
         who='the Monty Tech Business Director, to the Finance Committee',
         what='Lunenburg’s FY2026 required minimum contribution to Monty Tech'),
    dict(fy=2026, field='mt_fb_per_pupil', value=20827,
         board='finance-committee', date='2025-03-06', doc='7008',
         who='the Monty Tech Business Director, to the Finance Committee',
         what='the FY2026 foundation budget for each Lunenburg pupil at Monty Tech'),
]

# The town's own five-year forecast of this line, printed in a Select Board packet in
# January 2021 and projecting 2.5% a year. Read as a series so the miss is arithmetic.
FORECAST = dict(
    board='select-board', date='2021-01-19', doc='5244', kind='minutes',
    base_fy=2021, base=888684.00,
    series=[(2022, 910901.10), (2023, 933673.63), (2024, 957015.47),
            (2025, 980940.85), (2026, 1005464.38)],
    label='Monty Tech Assessment 888,684.00 910,901.10 933,673.63 957,015.47 '
          '980,940.85 1,005,464.38')

QUOTES = [
    dict(key='governed', board='finance-committee', date='2022-03-23', kind='minutes',
         doc='2056', who='the Monty Tech Business Director',
         quote='96 percent of the Monty Tech assessment is governed by the state, which '
               'determines contribution by average income and property values in town',
         why='The mechanism, said out loud to the Finance Committee in 2022. The DESE '
             'workbook agrees with the shape of it: in FY2023 the state-required minimum '
             'was 96.0% of what the town appropriated, and the remaining 4.0% was '
             'itemised in the same presentation as transportation and capital.'),
    dict(key='fe-83-94', board='finance-committee', date='2022-03-23', kind='minutes',
         doc='2056', who='the Monty Tech Business Director',
         quote='foundation enrollment has increased from 83 to 94, which increases the '
               'town’s required minimum contribution to $1,012,282 (a $140,597 increase) '
               'for Monty Tech, which is 8.2 percent of all L',
         why='Two of the four figures this page checks its own derivation against. '
             'Subtracting the school district’s required local contribution from the '
             'town’s, in DESE’s workbook, gives 83 and 94 foundation pupils and '
             '$1,012,282 — independently, from a document neither party wrote.'),
    dict(key='half-and-half', board='finance-committee', date='2026-02-05',
         kind='minutes', doc='7631', who='the Monty Tech Business Director',
         quote='DESE determines how much local communities contribute using their '
               'calculations and formula. The calculation includes half the income for '
               'town residents and half of the value of the property value in the town',
         why='Said four years later, about the same formula. It is why the town’s total '
             'obligation does not move when a child changes school: the inputs are '
             'property value and resident income.'),
    dict(key='reduce', board='finance-committee', date='2026-02-05', kind='minutes',
         doc='7631', who='a Finance Committee member and the Superintendent-Director',
         quote='what if anything can be done to reduce the contribution that Lunenburg '
               'needs to pay. Tom Brown states there is potential to change but that '
               'requires a change to the formula',
         why='The question this page exists to answer, asked at a public meeting, and '
             'answered the same way the arithmetic answers it.'),
    dict(key='agreement', board='finance-committee', date='2026-02-05', kind='minutes',
         doc='7631', who='a Finance Committee member and the Superintendent-Director',
         quote='Chris Menard inquires about the district agreement whether it’s indeﬁnite '
               'or if it can be renegotiated. Tom Brown believes the agreement is '
               'ongoing. He is also aware of some amendments, but they are very rare.',
         why='The nearest thing in the record to the regional agreement itself, which '
             'this archive does not hold. It is a recollection given at a meeting, not '
             'the document, and it is printed here as that.'),
    dict(key='fy26-required', board='finance-committee', date='2025-03-06',
         kind='minutes', doc='7008', who='the Monty Tech Business Director',
         quote='The total contribution needed from Lunenburg is $1,270,711.',
         why='The third check on the derivation, for FY2026, to the dollar. It is also '
             'the figure a reader is most likely to mistake for the assessment: the town '
             'appropriated more than this, and the difference is transportation and '
             'capital.'),
    dict(key='fy24-required', board='finance-committee', date='2023-03-22',
         kind='minutes', doc='92', who='the Monty Tech Business Director',
         quote='totaling $1,127,113 going to Monty Tech, which amounts to 6.62 percent '
               'of Monty Tech’s operating budget',
         why='The fourth check, for FY2024 — and rule 11 in one line from the other '
             'direction: what Lunenburg is billed is a small share of what the district '
             'spends, because Chapter 70 and everything else on its revenue side pay the '
             'rest.'),
    dict(key='reduction', board='finance-committee', date='2021-10-14', kind='minutes',
         doc='2096', who='the Town Manager',
         quote='a reduction in the Monty Tech Assessment will cover that cost',
         why='The one year in twelve where the appropriation candidate does NOT sit '
             'comfortably above the state-required minimum. An assessment certified '
             'downward mid-year is a thing that happens to this line, and it is a reason '
             'to read a single year of it carefully.'),
    dict(key='increment', board='finance-committee', date='2026-02-19', kind='minutes',
         doc='7657', who='the Finance Director',
         quote='The Monty Tech Assessment stands at $117,858.00, leaving $1,256,405.89 '
               'to be allocated between the School and Town budgets',
         why='Two quantities are called “the Monty Tech Assessment” in the town’s own '
             'record and they differ by a factor of eleven. This one is the INCREASE '
             'taken off new revenue before the rest is split — the arithmetic in the '
             'sentence proves it — and the assessment itself is the larger figure this '
             'page charts.'),
    dict(key='disentangle', board='school-committee', date='2026-03-23', kind='minutes',
         doc='7732', who='public comment',
         quote='we\'d have to disentangle ourselves from Monty Tech',
         why='Said at a School Committee meeting in March 2026, about bringing '
             'vocational programmes back into Lunenburg’s own schools. It is the only '
             'place in the searched record where leaving the district is raised, and it '
             'is printed because the page owes a reader who is thinking about it the '
             'arithmetic rather than a verdict.'),
    dict(key='aligned', board='finance-committee', date='2026-01-08', kind='minutes',
         doc='7592', who='the Finance Committee',
         quote='The Committee agrees that Monty Techs assessment should be aligned with '
               'the Lunenberg Public Schools',
         why='What the Finance Committee wants the line to do. Whether it can be made to '
             'do that is the subject of this page: the state-required part is 95% of it '
             'and is set by a formula the town is not a party to.'),
]

SEARCHED = ['Monty Tech', 'Montachusett', 'vocational', 'assessment', 'regional',
            'foundation enrollment', 'required minimum contribution']

# ---------------------------------------------------------------------------
# FIGURES READ OFF A PRINTED DOCUMENT, EACH WITH ITS COORDINATE AND ITS RAW LINE.
#
# Rule 13: cite a coordinate and the raw value. Every entry below names the extracted
# text file, an ANCHOR that must appear in it verbatim (whitespace collapsed, and nothing
# else changed), and the values this page publishes off that anchor. `read_figures`
# refuses to write unless the anchor is present AND every value's own printed form is
# inside it -- so a figure here cannot drift from the document it claims to come from,
# and a re-extraction that changes the page fails the build instead of the page.
#
# WHAT KIND OF DOCUMENT EACH IS (rule 13a). None of these is an accounting printout.
# Three are budget books -- arguments somebody assembled -- and they are labelled that
# way. The reason they carry weight anyway is that the DESE-sourced pages inside them
# reproduce, to the dollar, a state workbook this project holds independently; that check
# is `assert_printed_apportionment` below and it fails the build if it stops holding.
# ---------------------------------------------------------------------------
FIGURES = [
    dict(key='parts-fy26-fy27',
         doc='town-budget/docs/3583-fy27-monty-tech-budget-presentation-pdf.pdf',
         text='town-budget/text/3583-fy27-monty-tech-budget-presentation-pdf.txt',
         title='FY27 Monty Tech Budget Presentation',
         what='“Lunenburg 2-Year Assessment Comparison” — Lunenburg’s assessment for '
              'FY2026 and FY2027, in the four parts the district assesses in.',
         basis='the district’s own budget book. A sheet somebody assembled, not a '
               'printout from an accounting system.',
         anchor="Lunenburg 2-Year AssessmentComparison",
         row="20262,103,516$ 1,270,711$ 47,577$ 16,233$ -$ 1,334,521$ 101 1610 13,213$ "
             "20272,251,170$ 1,378,183$ 74,196$ -$ -$ 1,452,379$ 104 1612 13,965$",
         values=dict(
             fy26_foundation_budget=2103516, fy26_required=1270711,
             fy26_transport=47577, fy26_capital=16233, fy26_total=1334521,
             fy26_foundation_enrollment=101, fy26_attending=1610, fy26_per_pupil=13213,
             fy27_foundation_budget=2251170, fy27_required=1378183,
             fy27_transport=74196, fy27_total=1452379,
             fy27_foundation_enrollment=104, fy27_attending=1612, fy27_per_pupil=13965)),
    dict(key='parts-fy24',
         doc='town-budget/docs/a103-fy24-monty-tech-budget-for-public-hearing-march-08-2023-pdf.pdf',
         text='town-budget/text/a103-fy24-monty-tech-budget-for-public-hearing-march-08-2023-pdf.txt',
         title='FY24 Monty Tech Budget for Public Hearing, 8 March 2023',
         what='The “Community Assessments” table — Lunenburg’s FY2024 assessment in the '
              'same four parts, beside its FY2023 approved assessment.',
         basis='the district’s own budget book. A sheet somebody assembled.',
         anchor='Lunenburg 97 1,954,986 1,127,113 34,700 19,577 0 1,181,390 94 '
                '1,054,376 127,014',
         row='Lunenburg 97 1,954,986 1,127,113 34,700 19,577 0 1,181,390 94 1,054,376 '
             '127,014',
         values=dict(
             fy24_foundation_enrollment=97, fy24_foundation_budget=1954986,
             fy24_required=1127113, fy24_transport=34700, fy24_capital=19577,
             fy24_total=1181390,
             fy23_foundation_enrollment=94, fy23_total=1054376, change=127014)),
    dict(key='district-budget',
         doc='town-budget/docs/3583-fy27-monty-tech-budget-presentation-pdf.pdf',
         text='town-budget/text/3583-fy27-monty-tech-budget-presentation-pdf.txt',
         title='FY27 Monty Tech Budget Presentation',
         what='“FY 2027 Budget Summary” — the whole district’s budget, its Chapter 70 '
              'aid, and what all eighteen member towns are assessed between them. The '
              'rule 11 page: what Lunenburg is billed against what the district spends.',
         basis='the district’s own budget book. A sheet somebody assembled.',
         anchor='Total Budget$34,641,344 $35,516,660',
         row='Net School Spending30,990,41431,796,495806,0812.60% … Total '
             'Budget$34,641,344 $35,516,660 $875,3162.53% … Estimated Ch. 70 18,762,805 '
             '18,872,680 … (1)REQUIRED MINIMUM CONTRIBUTION$12,227,609 $12,923,815 … '
             '(2)NET TRANSPORTATION & OTHER OPERATING$700,930 $1,045,165 … (3)NET '
             'CAPITAL ASSESSMENT$250,000 $0 … TOTAL ASSESSMENT (All Budgets) '
             '$13,178,539 $13,968,980',
         values=dict(
             fy26_budget=34641344, fy27_budget=35516660,
             fy26_nss=30990414, fy27_nss=31796495,
             fy26_ch70=18762805, fy27_ch70=18872680,
             fy26_all_required=12227609, fy27_all_required=12923815,
             fy26_all_transport=700930, fy27_all_transport=1045165,
             fy26_all_capital=250000,
             fy26_all_assessments=13178539, fy27_all_assessments=13968980)),
    dict(key='members',
         doc='town-budget/docs/3583-fy27-monty-tech-budget-presentation-pdf.pdf',
         text='town-budget/text/3583-fy27-monty-tech-budget-presentation-pdf.txt',
         title='FY27 Monty Tech Budget Presentation',
         what='DESE’s apportionment sheet for the district itself — every one of the '
              'eighteen member towns, its foundation enrollment at Monty Tech and its '
              'required minimum contribution, for FY2026 and FY2027.',
         basis='DESE’s Chapter 70 calculation, reprinted inside the district’s budget '
               'book.',
         anchor='Total 1,488 1,465 -23 12,227,609 12,923,815 696,206',
         row='832 Montachusett · LEA Member FY26 FY27 Change FY26 FY27 Change · Total '
             '1,488 1,465 -23 12,227,609 12,923,815 696,206 · … · 162 Lunenburg 101 104 '
             '3 1,270,711 1,378,183 107,472',
         values=dict(fy26_members=1488, fy27_members=1465,
                     fy26_required=12227609, fy27_required=12923815)),
    dict(key='lunenburg-member',
         doc='town-budget/docs/3583-fy27-monty-tech-budget-presentation-pdf.pdf',
         text='town-budget/text/3583-fy27-monty-tech-budget-presentation-pdf.txt',
         title='FY27 Monty Tech Budget Presentation',
         what='Lunenburg’s own line in that sheet — the fifth independent confirmation '
              'of the required-contribution figure this page derives.',
         basis='DESE’s Chapter 70 calculation, reprinted inside the district’s budget '
               'book.',
         anchor='162 Lunenburg 101 104 3 1,270,711 1,378,183 107,472',
         row='162 Lunenburg 101 104 3 1,270,711 1,378,183 107,472',
         values=dict(fy26_fe=101, fy27_fe=104, fy26_required=1270711,
                     fy27_required=1378183, change=107472)),
    dict(key='dese-apportionment',
         doc='town-budget/docs/3583-fy27-monty-tech-budget-presentation-pdf.pdf',
         text='town-budget/text/3583-fy27-monty-tech-budget-presentation-pdf.txt',
         title='FY27 Monty Tech Budget Presentation',
         what='DESE’s own sheet, “FY27 Chapter 70 Apportionment of Local Contribution '
              'Across School Districts — 162 Lunenburg”, reprinted. It states the split '
              'this page derives, for FY2026, as published figures rather than as a '
              'subtraction.',
         basis='DESE’s Chapter 70 calculation, reprinted inside the district’s budget '
               'book. Checked against this project’s own copy of the state workbook.',
         anchor="Each district's share of municipality's combined FY26 foundation91.30% "
                "8.70% 100.00%",
         row='1 FY26 foundation enrollment1,603 101 1,704 · 2 FY26 foundation '
             'budget22,073,946 2,103,516 24,177,462 · 3 Each district’s share of '
             'municipality’s combined FY26 foundation91.30% 8.70% 100.00% · 4 FY26 '
             'required contribution13,334,631 1,270,711 14,605,342',
         values=dict(lps_fe=1603, mt_fe=101, town_fe=1704,
                     lps_fb=22073946, mt_fb=2103516, town_fb=24177462,
                     lps_rlc=13334631, mt_rlc=1270711, town_rlc=14605342)),
    dict(key='town-book',
         doc='town-budget/docs/3769-fy-2027-operating-budgets-balanced-tier-1-tier2.pdf',
         text='town-budget/text/3769-fy-2027-operating-budgets-balanced-tier-1-tier2.txt',
         title='FY2027 Operating Budgets (Balanced, Tier 1, Tier 2)',
         what='The Town’s own budget book, Schools section — the Monty Tech line for '
              'FY2024 expended, FY2025 budgeted, FY2025 actual, FY2026 budgeted and the '
              'three FY2027 scenarios. The only place the FY2025 figures appear.',
         basis='the Town’s budget book. Assembled from the Town Accountant’s figures, '
               'and not itself a ledger printout.',
         anchor='Monty Tech Assessment $1,181,390.18 $1,225,646.00 $1,224,162.00 '
                '$1,334,521.00 $1,452,426.00 $1,452,426.00 $1,452,426.00',
         row='Monty Tech Assessment $1,181,390.18 $1,225,646.00 $1,224,162.00 '
             '$1,334,521.00 $1,452,426.00 $1,452,426.00 $1,452,426.00',
         values=dict(fy24_expended=1181390.18, fy25_budgeted=1225646.00,
                     fy25_actual=1224162.00, fy26_budgeted=1334521.00,
                     fy27_balanced=1452426.00)),
    dict(key='method',
         doc='town-annual-reports/docs/4124-fy-2017-annual-town-report.pdf',
         text='town-annual-reports/text/4124-fy-2017-annual-town-report.txt',
         title='FY2017 Annual Town Report, printed page 146',
         what='The district’s own statement of how it apportions an assessment, printed '
              'inside Lunenburg’s annual town report: four parts, with transportation '
              'and other operating divided by each town’s 1 October enrollment share and '
              'capital divided by its school-attending children in grades 1 to 12.',
         basis='the district’s own description of its method, reprinted by the Town. It '
               'is a statement of practice, not the regional agreement that binds it.',
         anchor="Each Community's assessment is made up of four parts: ~ Required "
                "Minimum Contribution (set by the State) ~ Transportation & Other "
                "Operating Expenses above Minimum Net School Spending ~ Capital Outlay "
                "~ Bonds (assessed based upon the Capital apportionment)",
         row="DETERMINATION OF ASSESSMENT RATIOS · Each Community's assessment is made "
             "up of four parts: ~ Required Minimum Contribution (set by the State) ~ "
             "Transportation & Other Operating Expenses above Minimum Net School "
             "Spending ~ Capital Outlay ~ Bonds (assessed based upon the Capital "
             "apportionment)",
         values={}),
    dict(key='method-operating',
         doc='town-annual-reports/docs/4124-fy-2017-annual-town-report.pdf',
         text='town-annual-reports/text/4124-fy-2017-annual-town-report.txt',
         title='FY2017 Annual Town Report, printed page 146',
         what='The operating ratio, stated as a formula.',
         basis='the district’s own description of its method, reprinted by the Town.',
         anchor='The number of students from each member community enrolled at '
                'Montachusett R egional Vocational Technical School divided by total '
                'Montachusett Regional Vocational Technical School Day school '
                'enrollment of member communities on October 1, 2017 equals the '
                'operating ratio.',
         row='TRANSPORTATION & OTHER OPERATING BUDGET - (determined by each Communities '
             'enrollment, October 1, 2017) · The number of students from each member '
             'community enrolled … divided by total … Day school enrollment of member '
             'communities on October 1, 2017 equals the operating ratio.',
         values={}),
    dict(key='method-capital',
         doc='town-annual-reports/docs/4124-fy-2017-annual-town-report.pdf',
         text='town-annual-reports/text/4124-fy-2017-annual-town-report.txt',
         title='FY2017 Annual Town Report, printed page 146',
         what='The capital ratio, stated as a formula.',
         basis='the district’s own description of its method, reprinted by the Town.',
         anchor='The number of students from each member community enrolled in Grades 1 '
                'through 12 divided by the total number of students enrolled in Grades '
                '1 through 12 of 18 member communities equals the capital assessment '
                'ratio.',
         row='CAPITAL BUDGET - (determined by each Communities school attending '
             'children, grades 1 - 12, October 1, 2017) · The number of students … '
             'enrolled in Grades 1 through 12 divided by the total number of students '
             'enrolled in Grades 1 through 12 of 18 member communities equals the '
             'capital assessment ratio.',
         values={}),
]

CITES_GAPS = [
    'What Monty Tech spends, and on what',
    'How the Monty Tech assessment splits between operating, transportation and capital',
    'Why the district and the town state different FY2027 Monty Tech assessments',
    'How the Montachusett regional agreement apportions costs among its member towns',
    'How many Lunenburg applicants Monty Tech turns away',
    'Why DESE’s foundation enrollment for Lunenburg at Monty Tech differs from its own '
    'October headcount',
]

DOCS = [
    dict(key='state-dese/dese-ch70-key-factors.xlsx',
         what='DESE’s Chapter 70 key factors — the municipal contribution sheet (income, '
              'property, combined effort yield, required local contribution, by town) '
              'and the district aid sheet (foundation enrollment, foundation budget, '
              'required local contribution, Chapter 70 aid, by district). Every '
              'established figure on this page is a subtraction between those two '
              'sheets.',
         publisher='Massachusetts Department of Elementary and Secondary Education',
         stage='the Chapter 70 calculation for each fiscal year. A formula '
               'calculation, not a budget and not an actual.'),
    dict(key='data/dese-town-enrollment.csv',
         what='Every Lunenburg-resident student, by the district they actually attend '
              'and the programme they are there under. The source of the student counts '
              'on this page.',
         publisher='Massachusetts Department of Elementary and Secondary Education '
                   '(extracted by this project)',
         stage='reported as of 1 October each year. A headcount, not a foundation '
               'enrollment — the two are different counts and this page keeps them '
               'apart.'),
    dict(key='town-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.xlsx',
         what='The Town’s MUNIS year-to-date budget report for the general fund, FY2026 '
              'period 12. The only Monty Tech figure on this page that came out of an '
              'accounting system rather than off a printed page.',
         publisher='Town of Lunenburg (obtained by records request)',
         stage='what the books say was appropriated and expended. Rule 13a: a printout '
               'from the accounting system, not a sheet somebody assembled.'),
]


def fail(msg):
    raise SystemExit('%s\nNothing written.' % msg)


def q(db, sql, *args):
    cur = db.execute(sql, args)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def flat(path):
    """The extracted text of one meeting document, whitespace collapsed and NOTHING else
    changed. Ligatures stay as the extractor produced them: normalising them would make
    every quote here a rendering of a rendering."""
    return re.sub(r'\s+', ' ', open(path, encoding='utf-8', errors='replace').read())


def minutes_path(board, date, kind, doc):
    rel = '%s/%s/%s-%s-%s.txt' % (MINUTES, board, date, kind, doc)
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        fail('%s is not here — this page attributes something to a document the archive '
             'does not hold' % rel)
    return rel, path


def town_url(kind, date, doc):
    return ('https://www.lunenburgma.gov/AgendaCenter/ViewFile/%s/_%s%s%s-%s'
            % ('Minutes' if kind == 'minutes' else 'Agenda',
               date[5:7], date[8:10], date[:4], doc))


def manifest_index():
    have = {}
    with open(MANIFEST, encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            have[row['key']] = row
    return have


def read_figures():
    """Every figure this page takes off a printed page, asserted against that page.

    The anchor must be present in the extracted text, whitespace collapsed and nothing
    else changed. Each published value's own printed form must be inside the anchor or
    inside the line the anchor sits on. A figure that cannot be found in the document it
    names is not published and nothing is written."""
    have = manifest_index()
    out = {}
    for spec in FIGURES:
        path = os.path.join(ROOT, 'sources', spec['text'])
        if not os.path.exists(path):
            fail('%s is not here — this page reads figures off it.' % spec['text'])
        lines = open(path, encoding='utf-8', errors='replace').read().splitlines()
        anchor = re.sub(r'\s+', ' ', spec['anchor']).strip()
        # A table lands on one line and a paragraph wraps over several, so the anchor is
        # looked for in a line and then in a window of lines starting at each one. `hit`
        # is the line the anchor STARTS on, and `span` how many lines it runs over --
        # both are published, because a coordinate that is only approximately right is
        # not a coordinate.
        hit = span = None
        for width in (1, 4, 8, 16):
            for i in range(len(lines)):
                if anchor not in re.sub(r'\s+', ' ', ' '.join(lines[i:i + width])):
                    continue
                # Narrow to the smallest window that still holds the anchor, from the
                # left and then from the right, so the coordinate is the line the anchor
                # actually starts on rather than wherever the search window opened.
                lo, hi = i, i + width
                while lo < hi - 1 and anchor in re.sub(
                        r'\s+', ' ', ' '.join(lines[lo + 1:hi])):
                    lo += 1
                while hi > lo + 1 and anchor in re.sub(
                        r'\s+', ' ', ' '.join(lines[lo:hi - 1])):
                    hi -= 1
                hit, span = lo + 1, hi - lo
                break
            if hit:
                break
        if hit is None:
            fail('the anchor for %r is no longer in %s. Quote the source, never your '
                 'rendering of it (rule 13):\n  %s' % (spec['key'], spec['text'], anchor))
        blob = re.sub(r'\s+', ' ', ' '.join(lines[hit - 1:hit - 1 + span]))
        for name, value in spec['values'].items():
            # A document may print a thousands separator or not -- this one prints
            # `1,270,711$` and `1610` on the same line -- so both forms are accepted and
            # at least one of them must be there.
            forms = ([format(value, ',.2f'), format(value, '.2f')]
                     if isinstance(value, float)
                     else [format(value, ','), str(value)])
            if not any(f in blob for f in forms):
                fail('%s: %s is published as %s and neither that nor %s is on line %d of '
                     '%s.' % (spec['key'], name, forms[0], forms[1], hit, spec['text']))
        doc = have.get(spec['doc'])
        if not doc:
            fail('%s is not in the archive manifest (rule 12).' % spec['doc'])
        out[spec['key']] = dict(
            key=spec['key'], title=spec['title'], what=spec['what'],
            basis=spec['basis'], line=hit, lines=span, row=spec['row'],
            text='sources/' + spec['text'], path='sources/' + spec['doc'],
            docs_url='/docs/' + spec['doc'], text_url='/docs/' + spec['text'],
            filename=spec['doc'].split('/')[-1],
            sha256=doc['sha256'], bytes=int(doc['bytes']),
            url=(doc['upstream'] or '').split(' ')[0],
            values=dict(spec['values']))
    return out


def assert_printed_apportionment(req, fig):
    """The derivation, against DESE's own apportionment sheet as the district reprinted it.

    This is the strongest check on the page. Everything else derives Lunenburg's Monty
    Tech share by subtracting one column of a state workbook from another. Here the split
    is PRINTED -- enrollment, foundation budget, share and required contribution, for both
    districts and the town -- and it must agree with the subtraction to the dollar."""
    printed = fig['dese-apportionment']['values']
    row = next((r for r in req if r['fy'] == 2026), None)
    if not row:
        fail('FY2026 is not in the derived series and the printed apportionment sheet is '
             'checked against it.')
    pairs = [('mt_fe', 'mt_fe'), ('lps_fe', 'lps_fe'), ('town_fe', 'town_fe'),
             ('mt_fb', 'mt_fb'), ('lps_fb', 'lps_fb'), ('town_fb', 'town_fb'),
             ('mt_rlc', 'mt_rlc'), ('lps_rlc', 'lps_rlc'), ('town_rlc', 'town_rlc')]
    for ours, theirs in pairs:
        if abs(row[ours] - printed[theirs]) > 0.51:
            fail('FY2026 %s derives to %s and DESE’s own apportionment sheet prints %s. '
                 'The subtraction this page rests on has stopped agreeing with the '
                 'published split.' % (ours, row[ours], printed[theirs]))
    if abs(round(row['rlc_share'] * 100, 2) - 8.70) > 0.005:
        fail('FY2026 Monty Tech share derives to %.4f%% and the sheet prints 8.70%%.'
             % (row['rlc_share'] * 100))
    return dict(fy=2026, fields=len(pairs), printed_share_pct=8.70,
                derived_share_pct=round(row['rlc_share'] * 100, 2))


def assessment(fig, led, req):
    """The assessment itself, year by year, from the documents that state it.

    THREE KINDS OF ROW AND THE PAGE NEVER MERGES THEM: what the district assessed (its
    own budget books), what the town appropriated (its budget book), and what the town's
    accounting system says it paid (the ledger). Where more than one exists for a year,
    all of them are published and any difference is stated rather than resolved."""
    p26 = fig['parts-fy26-fy27']['values']
    p24 = fig['parts-fy24']['values']
    tb = fig['town-book']['values']
    by_fy = {r['fy']: r for r in req}

    rows = [
        dict(fy=2023, required=p24['fy23_total'] and None, total=p24['fy23_total'],
             transport=None, capital=None,
             foundation_budget=None, foundation_enrollment=p24['fy23_foundation_enrollment'],
             source='parts-fy24', kind='assessed',
             note='Stated by the district as the prior year’s approved assessment in its '
                  'FY2024 book. The FY2023 annual town report carries the same figure '
                  'and this project cannot establish which printed column it sits in, '
                  'so the district’s statement is what is published here.'),
        dict(fy=2024, required=p24['fy24_required'], total=p24['fy24_total'],
             transport=p24['fy24_transport'], capital=p24['fy24_capital'],
             foundation_budget=p24['fy24_foundation_budget'],
             foundation_enrollment=p24['fy24_foundation_enrollment'],
             source='parts-fy24', kind='assessed', note=''),
        dict(fy=2025, required=by_fy[2025]['mt_rlc'] if 2025 in by_fy else None,
             total=tb['fy25_budgeted'], transport=None, capital=None,
             foundation_budget=by_fy[2025]['mt_fb'] if 2025 in by_fy else None,
             foundation_enrollment=by_fy[2025]['mt_fe'] if 2025 in by_fy else None,
             source='town-book', kind='appropriated',
             note='The only year with no budget book in this archive. The total is the '
                  'Town’s appropriation; the required minimum and the foundation figures '
                  'are DESE’s, so the four-part split cannot be stated.'),
        dict(fy=2026, required=p26['fy26_required'], total=p26['fy26_total'],
             transport=p26['fy26_transport'], capital=p26['fy26_capital'],
             foundation_budget=p26['fy26_foundation_budget'],
             foundation_enrollment=p26['fy26_foundation_enrollment'],
             source='parts-fy26-fy27', kind='assessed', note=''),
        dict(fy=2027, required=p26['fy27_required'], total=p26['fy27_total'],
             transport=p26['fy27_transport'], capital=0,
             foundation_budget=p26['fy27_foundation_budget'],
             foundation_enrollment=p26['fy27_foundation_enrollment'],
             source='parts-fy26-fy27', kind='assessed',
             note='The Town’s own FY2027 budget book carries this line at $1,452,426 in '
                  'all three of its scenarios — $47 more than the district’s figure. '
                  'Neither document acknowledges the other.'),
    ]
    for r in rows:
        r['identity'] = None
        if r['required'] is not None and r['transport'] is not None:
            parts = r['required'] + r['transport'] + (r['capital'] or 0)
            r['identity'] = round(parts - r['total'], 2)
            if abs(r['identity']) > 0.51:
                fail('FY%d: the four parts sum to %s and the district prints a total of '
                     '%s. The page states that identity.'
                     % (r['fy'], parts, r['total']))
        if r['required'] and r['total']:
            r['required_share'] = round(r['required'] / r['total'], 6)
            r['above_minimum'] = round(r['total'] - r['required'], 2)

    # The ledger and the district's FY2026 figure must agree, or one of the two central
    # sentences on this page is wrong.
    if abs(led['original'] - p26['fy26_total']) > 0.005:
        fail('the Town’s ledger says the FY2026 Monty Tech appropriation was %s and the '
             'district’s own book says it assessed %s.'
             % (led['original'], p26['fy26_total']))
    if abs(tb['fy26_budgeted'] - led['original']) > 0.005:
        fail('the Town’s FY2027 budget book states FY2026 at %s and the ledger at %s.'
             % (tb['fy26_budgeted'], led['original']))

    return rows, dict(
        fy27_district=p26['fy27_total'], fy27_town=tb['fy27_balanced'],
        fy27_gap=round(tb['fy27_balanced'] - p26['fy27_total'], 2),
        fy25_budgeted=tb['fy25_budgeted'], fy25_actual=tb['fy25_actual'],
        fy25_gap=round(tb['fy25_actual'] - tb['fy25_budgeted'], 2),
        fy24_district=p24['fy24_total'], fy24_town=tb['fy24_expended'],
        fy24_gap=round(tb['fy24_expended'] - p24['fy24_total'], 2),
        fy26_ties=True,
        district_per_pupil=p26['fy26_per_pupil'],
        district_per_pupil_fy27=p26['fy27_per_pupil'],
    )


def district(fig, led):
    """RULE 11, WITH THE DOCUMENT BEHIND IT. What Lunenburg is billed against what the
    district spends, and what pays the rest."""
    d = fig['district-budget']['values']
    p = fig['parts-fy26-fy27']['values']
    out = []
    for fy, budget, ch70, req_all, tr, cap, tot in [
            (2026, d['fy26_budget'], d['fy26_ch70'], d['fy26_all_required'],
             d['fy26_all_transport'], d['fy26_all_capital'], d['fy26_all_assessments']),
            (2027, d['fy27_budget'], d['fy27_ch70'], d['fy27_all_required'],
             d['fy27_all_transport'], 0, d['fy27_all_assessments'])]:
        lun = p['fy%d_total' % (fy - 2000)]
        lun_fe = p['fy%d_foundation_enrollment' % (fy - 2000)]
        members = fig['members']['values']['fy%d_members' % (fy - 2000)]
        if abs((req_all + tr + cap) - tot) > 0.51:
            fail('FY%d: the district’s three assessment components sum to %s and it '
                 'prints a total of %s.' % (fy, req_all + tr + cap, tot))
        out.append(dict(
            fy=fy, budget=budget, ch70=ch70, all_assessments=tot,
            all_required=req_all, all_transport=tr, all_capital=cap,
            ch70_share=round(ch70 / budget, 6),
            assessment_share=round(tot / budget, 6),
            other_share=round((budget - ch70 - tot) / budget, 6),
            lunenburg=lun, lunenburg_of_assessments=round(lun / tot, 6),
            lunenburg_of_budget=round(lun / budget, 6),
            lunenburg_fe=lun_fe, members_fe=members,
            lunenburg_fe_share=round(lun_fe / members, 6)))
    return out


def documents():
    have = {}
    with open(MANIFEST, encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            have[row['key']] = row
    out = []
    for d in DOCS:
        row = have.get(d['key'])
        if not row:
            fail('%s is not in the archive manifest. A figure without its document is '
                 'not publishable (rule 12).' % d['key'])
        out.append(dict(d, path='sources/' + d['key'], sha256=row['sha256'],
                        bytes=int(row['bytes']), url=row['upstream'] or '',
                        docs_url='/docs/' + d['key'],
                        filename=d['key'].split('/')[-1]))
    return out


def assert_untouched(db):
    """`report_monty_tech` must stay unusable, and must stay VISIBLY unusable.

    It is Monty Tech's own budget reprinted in one annual town report, its column_meaning
    is empty and its status is `no check`. Nothing on this page reads it. If it ever
    acquires a column meaning somebody should decide deliberately to use it, rather than
    have a page start using it because a filter stopped excluding anything."""
    rows = q(db, "SELECT DISTINCT edition, column_meaning, status FROM report_monty_tech")
    if not rows:
        fail('report_monty_tech is empty. It is not read by this page, but the page says '
             'in its own text why it is not, and that sentence is now about nothing.')
    if any(r['column_meaning'] for r in rows) or {r['status'] for r in rows} != {'no check'}:
        fail('report_monty_tech now states a column meaning or a status other than '
             '`no check`. This page says in prose that it does not, and that prose is '
             'now wrong. Decide deliberately whether the table is usable.')
    return dict(rows=q(db, 'SELECT COUNT(*) n FROM report_monty_tech')[0]['n'],
                editions=sorted({r['edition'] for r in rows}))


def required(db):
    """The state-mandated part of the assessment, FY by FY.

    DERIVED BY SUBTRACTION, and the whole page depends on the subtraction meaning what it
    says: Lunenburg belongs to exactly two districts, so the town's required local
    contribution minus its own district's is what is required for the other one."""
    rows = q(db, """
        SELECT t.fy,
               t.town_foundation_enrollment  AS town_fe,
               d.foundation_enrollment       AS lps_fe,
               t.town_foundation_budget      AS town_fb,
               d.foundation_budget           AS lps_fb,
               t.required_local_contribution AS town_rlc,
               d.required_local_contribution AS lps_rlc,
               t.combined_effort_yield       AS cey,
               t.target_local_contribution   AS target
          FROM dese_ch70_contribution t
          JOIN dese_ch70_aid_factor d ON d.fy = t.fy AND d.lea = ?
         WHERE t.municipality = ?
         ORDER BY t.fy""", LPS_LEA, TOWN)
    if len(rows) < MIN_REQUIRED_YEARS:
        fail('the town/district contribution join returned %d years, fewer than %d. A '
             'join that matches nothing looks exactly like data that is absent.'
             % (len(rows), MIN_REQUIRED_YEARS))

    out = []
    for r in rows:
        mt_fe = r['town_fe'] - r['lps_fe']
        mt_fb = r['town_fb'] - r['lps_fb']
        mt_rlc = r['town_rlc'] - r['lps_rlc']
        if mt_fe <= 0 or mt_fb <= 0 or mt_rlc <= 0:
            fail('FY%d: the town figures are not larger than the district figures, so '
                 'the subtraction that produces the Monty Tech share has stopped being a '
                 'subtraction.' % r['fy'])
        out.append(dict(
            fy=r['fy'],
            town_fe=round(r['town_fe'], 2), lps_fe=round(r['lps_fe'], 2),
            mt_fe=round(mt_fe, 2),
            town_fb=round(r['town_fb'], 2), lps_fb=round(r['lps_fb'], 2),
            mt_fb=round(mt_fb, 2),
            town_rlc=round(r['town_rlc'], 2), lps_rlc=round(r['lps_rlc'], 2),
            mt_rlc=round(mt_rlc, 2),
            rlc_share=round(mt_rlc / r['town_rlc'], 6),
            fb_share=round(mt_fb / r['town_fb'], 6),
            fe_share=round(mt_fe / r['town_fe'], 6),
            mt_fb_per_pupil=round(mt_fb / mt_fe, 2),
            lps_fb_per_pupil=round(r['lps_fb'] / r['lps_fe'], 2),
            wealth_bound=abs(r['target'] - r['cey']) < 1.0,
        ))
    return out


def apportionment(req):
    """THE SPLIT RULE, MEASURED. The share of the town's required contribution that falls
    to Monty Tech equals its share of the town's foundation budget, to a tenth of a basis
    point, in every year but one. That is the apportionment rule, and it is measured here
    rather than described from a document, because the archive holds no document that
    states it."""
    tol = 1e-5
    exact = [r for r in req if abs(r['rlc_share'] - r['fb_share']) < tol]
    off = [r for r in req if abs(r['rlc_share'] - r['fb_share']) >= tol]
    if len(exact) < len(req) - 2:
        fail('the foundation-budget apportionment identity now fails in %d of %d years. '
             'The page states it as the rule that splits the town’s contribution, and it '
             'is no longer that.' % (len(off), len(req)))
    worst = max(off, key=lambda r: abs(r['rlc_share'] - r['fb_share']), default=None)
    return dict(
        years=len(req), exact=len(exact), tolerance=tol,
        off=[dict(fy=r['fy'], gap_pp=round(100 * (r['rlc_share'] - r['fb_share']), 4))
             for r in off],
        worst_fy=worst['fy'] if worst else None,
        worst_gap_pp=round(100 * (worst['rlc_share'] - worst['fb_share']), 4) if worst else None,
    )


def wealth(req):
    """THE TOWN TOTAL IS SET BY WEALTH, not by enrollment -- asserted, not assumed.

    DESE takes the lower of the town's combined effort yield (property value and resident
    income) and 82.5% of its foundation budget. If the cap ever binds, enrollment starts
    entering the town's total and the page's central sentence stops being true."""
    bound = [r['fy'] for r in req if r['wealth_bound']]
    if len(bound) != len(req):
        fail('the 82.5%%-of-foundation cap binds in %s. The page says the town’s total '
             'obligation is set by wealth rather than by enrollment, and in those years '
             'it is not.' % [r['fy'] for r in req if not r['wealth_bound']])
    return dict(years=len(req), wealth_bound_years=len(bound),
                cap_pct=0.825,
                first_fy=req[0]['fy'], last_fy=req[-1]['fy'])


def corroborate(req):
    """The derivation, against what somebody said in a room, four times."""
    by_fy = {r['fy']: r for r in req}
    out = []
    for c in CORROBORATION:
        row = by_fy.get(c['fy'])
        if not row:
            fail('FY%d is not in the derived series and a public statement is checked '
                 'against it.' % c['fy'])
        got = row[c['field']]
        if abs(got - c['value']) > 0.51:
            fail('FY%d %s derives to %s and %s stated %s. The subtraction has stopped '
                 'meaning what this page says it means.'
                 % (c['fy'], c['field'], got, c['who'], c['value']))
        rel, path = minutes_path(c['board'], c['date'], 'minutes', c['doc'])
        out.append(dict(fy=c['fy'], field=c['field'], stated=c['value'], derived=got,
                        who=c['who'], what=c['what'], board=c['board'].replace('-', ' ').title(),
                        date=c['date'], cite='/docs/' + rel.replace('sources/', ''),
                        town=town_url('minutes', c['date'], c['doc'])))
    return out


def ledger(db):
    """FY2026, out of the accounting system. The only figure here of that kind."""
    rows = q(db, """
        SELECT doc_id, fy, period, fund, dept, org, object, account, name,
               original, revised, expended, encumbered, available, pct_used
          FROM munis_ledger
         WHERE dept = ? AND fy = ? AND period = ?""", LEDGER_DEPT, LEDGER_FY, LEDGER_PERIOD)
    if len(rows) != 1:
        fail('the FY%d period %s ledger returned %d rows for dept %s, not 1.'
             % (LEDGER_FY, LEDGER_PERIOD, len(rows), LEDGER_DEPT))
    r = rows[0]
    if 'MONTY' not in (r['name'] or '').upper():
        fail('dept %s in the FY%d ledger is now called %r. This page names it.'
             % (LEDGER_DEPT, LEDGER_FY, r['name']))
    r['original'] = float(r['original'])
    r['revised'] = float(r['revised'])
    r['expended'] = float(r['expended'])
    r['available'] = float(r['available'])
    return r


def candidates(db, req, led):
    """The annual-report appropriation figures. CANDIDATES, never established.

    Only the accountant's schedule, only where the page states an identity that fixes
    which printed column is which, and every one keeps its `status` so nothing can be
    aggregated without splitting on it."""
    rows = q(db, """
        SELECT fy, edition, page, panel, "group", label, table_family, v1, v2, v3,
               n_values, ruler_spanned, unparsed_cells, column_meaning, status
          FROM report_appropriations
         WHERE label = 'Monty Tech Assessment'
           AND table_family = 'accountant-schedule'
         ORDER BY fy""")
    if not rows:
        fail('no Monty Tech rows in report_appropriations. A join that matches nothing '
             'looks exactly like a line the town never had.')

    prov = {r['edition']: r for r in q(
        db, "SELECT * FROM dataset_document WHERE dataset='report-appropriations'")}
    by_fy = {r['fy']: r for r in req}

    out = []
    for r in rows:
        established_columns = (r['column_meaning'] or '').startswith('v1=appropriated')
        v1 = float(r['v1']) if r['v1'] else None
        d = prov.get(r['edition'])
        if not d:
            fail('%s has no row in dataset_document, so an appropriation figure would be '
                 'published with no document behind it (rule 12).' % r['edition'])
        q_row = by_fy.get(r['fy'])
        out.append(dict(
            fy=r['fy'], edition=r['edition'], page=r['page'], value=v1,
            available=float(r['v2']) if r['v2'] else None,
            expended=float(r['v3']) if r['v3'] else None,
            status=r['status'], column_meaning=r['column_meaning'] or '',
            columns_established=established_columns,
            ruler_spanned=(r['ruler_spanned'] or '') == 'yes',
            n_values=int(r['n_values'] or 0),
            unparsed=(r['unparsed_cells'] or '').strip(),
            usable=bool(established_columns and v1),
            required=q_row['mt_rlc'] if q_row else None,
            over=round(v1 - q_row['mt_rlc'], 2) if (v1 and q_row) else None,
            over_pct=round(v1 / q_row['mt_rlc'] - 1, 6) if (v1 and q_row) else None,
            document=d['document'], publisher_label=d['publisher_label'],
            sha256=d['sha256'], upstream=d['upstream'].split(' ')[0],
            docs_url='/docs/town-annual-reports/' + d['document'],
        ))

    usable = [c for c in out if c['usable']]
    if len(usable) < MIN_CANDIDATES:
        fail('only %d annual-report figures have an established column meaning, fewer '
             'than %d. The page draws a series off them.' % (len(usable), MIN_CANDIDATES))
    if any(c['status'] not in ('check failed', 'no check') for c in usable):
        fail('an annual-report Monty Tech row now has a status other than `check failed` '
             'or `no check`. The page says every one of them fails its own '
             'reconciliation, and that sentence is now wrong — which is better news than '
             'it sounds and still has to be written down.')

    # The shape of the check the page rests on: every candidate should sit ABOVE the
    # state-required minimum, because the assessment is that minimum plus transportation
    # and capital. If one falls below, the extraction and the formula disagree about the
    # world and the page must say which years.
    below = [c['fy'] for c in usable if c['over'] is not None and c['over'] < 0]
    ratios = [c['over_pct'] for c in usable if c['over_pct'] is not None]
    band = [c for c in usable if c['over_pct'] is not None and c['over_pct'] >= 0.03]
    ledger_over = round(led['original'] / by_fy[LEDGER_FY]['mt_rlc'] - 1, 6)
    return out, dict(
        n=len(usable), first_fy=usable[0]['fy'], last_fy=usable[-1]['fy'],
        below=below, in_band=len(band),
        min_pct=round(min(ratios), 6), max_pct=round(max(ratios), 6),
        outlier_fy=min(usable, key=lambda c: c['over_pct'])['fy'],
        outlier_pct=round(min(ratios), 6),
        ledger_fy=LEDGER_FY, ledger_over_pct=ledger_over,
    )


def students(db):
    """Where Lunenburg's children actually are, by the LEA rather than by a district NAME.

    A Monty Tech child is `Resident/Member` -- a resident member of a district Lunenburg
    belongs to. That is not the same category as school choice and the page never merges
    them."""
    rows = q(db, """
        SELECT fy, enrollment_reason, lea, district, students
          FROM dese_town_enrollment
         WHERE town = ?""", TOWN)
    if not rows:
        fail('no Lunenburg rows in dese_town_enrollment.')
    years = sorted({r['fy'] for r in rows})
    if len(years) < MIN_STUDENT_YEARS:
        fail('only %d years of resident enrollment.' % len(years))

    names = {r['district'] for r in rows if r['lea'] == MT_LEA}
    if not names:
        fail('LEA %s (Montachusett Regional Vocational Technical) matched no Lunenburg '
             'resident rows. The page counts them.' % MT_LEA)

    out = []
    for fy in years:
        yr = [r for r in rows if r['fy'] == fy]
        mt = sum(r['students'] or 0 for r in yr if r['lea'] == MT_LEA)
        choice = sum(r['students'] or 0 for r in yr
                     if r['enrollment_reason'] == 'School Choice Program')
        charter = sum(r['students'] or 0 for r in yr
                      if r['enrollment_reason'] == 'Charter School')
        lps = sum(r['students'] or 0 for r in yr if r['lea'] == LPS_LEA)
        total = sum(r['students'] or 0 for r in yr)
        out.append(dict(fy=fy, monty_tech=mt, school_choice=choice, charter=charter,
                        in_lunenburg=lps, all_resident=total,
                        mt_share=round(mt / total, 6) if total else None))
    return out, dict(district_names=sorted(names), lea=MT_LEA,
                     first_fy=years[0], last_fy=years[-1])


def counts(req, stu):
    """THE TWO STUDENT COUNTS, side by side and never merged.

    DESE publishes a 1 October headcount of Lunenburg residents at Monty Tech, and a
    FOUNDATION enrollment used by the Chapter 70 formula. They are different numbers for
    the same year, and the difference is not noise: the district told the Finance
    Committee in 2022 that Lunenburg students attending trade programmes at other
    districts become part of the Monty Tech assessment."""
    by_fy = {r['fy']: r for r in stu}
    out = []
    for r in req:
        s = by_fy.get(r['fy'])
        if not s:
            continue
        out.append(dict(fy=r['fy'], headcount=s['monty_tech'],
                        foundation=r['mt_fe'],
                        difference=round(r['mt_fe'] - s['monty_tech'], 2)))
    if not out:
        fail('the foundation enrollment and the headcount share no year. The page prints '
             'them beside each other.')
    return out


def forecast(req, led):
    rel, path = minutes_path(FORECAST['board'], FORECAST['date'], FORECAST['kind'],
                             FORECAST['doc'])
    if re.sub(r'\s+', ' ', FORECAST['label']) not in flat(path):
        fail('the Select Board’s own five-year projection of this line is no longer in '
             '%s. Quote the source, never your rendering of it.' % rel)
    rate = FORECAST['series'][0][1] / FORECAST['base'] - 1
    actual = led['original']
    last_fy, last_proj = FORECAST['series'][-1]
    if last_fy != LEDGER_FY:
        fail('the projection ends at FY%d and the ledger figure is FY%d.'
             % (last_fy, LEDGER_FY))
    req_by = {r['fy']: r for r in req}
    return dict(
        board=FORECAST['board'].replace('-', ' ').title(), date=FORECAST['date'],
        cite='/docs/' + rel.replace('sources/', ''),
        town=town_url(FORECAST['kind'], FORECAST['date'], FORECAST['doc']),
        rate=round(rate, 4),
        quote=FORECAST['label'],
        series=[dict(fy=fy, projected=v,
                     required=req_by[fy]['mt_rlc'] if fy in req_by else None)
                for fy, v in FORECAST['series']],
        base_fy=FORECAST['base_fy'], base=FORECAST['base'],
        actual_fy=LEDGER_FY, actual=actual, projected=last_proj,
        miss=round(actual - last_proj, 2),
        miss_pct=round(actual / last_proj - 1, 6),
        required_cagr=round((req_by[LEDGER_FY]['mt_rlc'] / req_by[FORECAST['base_fy']]['mt_rlc'])
                            ** (1 / (LEDGER_FY - FORECAST['base_fy'])) - 1, 6),
    )


def said():
    out = []
    for spec in QUOTES:
        rel, path = minutes_path(spec['board'], spec['date'], spec['kind'], spec['doc'])
        if re.sub(r'\s+', ' ', spec['quote']) not in flat(path):
            fail('the quote attributed to %s %s is no longer in %s — quote the source, '
                 'never your rendering of it (rule 13).'
                 % (spec['board'], spec['date'], rel))
        out.append(dict(
            key=spec['key'], board=spec['board'].replace('-', ' ').title(),
            date=spec['date'], quote=spec['quote'], why=spec['why'], who=spec['who'],
            kind='Minutes' if spec['kind'] == 'minutes' else 'Agenda',
            cite='/docs/' + rel.replace('sources/', ''),
            town=town_url(spec['kind'], spec['date'], spec['doc'])))
    return out


def searched():
    """Each term with its DENOMINATOR. A grep that finds nothing prints nothing, and
    nothing reads as nobody said it."""
    idx = os.path.join(ROOT, 'sources/meetings/index.csv')
    if not os.path.exists(idx):
        fail('sources/meetings/index.csv is not here — a search of nothing is not a search')
    readable = []
    for r in csv.DictReader(open(idx, encoding='utf-8')):
        stem = os.path.splitext(r['path'])[0] if r['path'].strip() else ''
        txt = os.path.join(ROOT, MINUTES, stem + '.txt') if stem else ''
        if stem and os.path.exists(txt):
            readable.append(txt)
    if not readable:
        fail('no meeting document is readable — refusing to publish a count of what '
             'nobody said')
    bodies = [open(t, encoding='utf-8', errors='replace').read() for t in readable]
    terms = [dict(term=t,
                  documents=sum(1 for b in bodies if re.search(re.escape(t), b, re.I)))
             for t in SEARCHED]
    if not any(t['documents'] for t in terms):
        fail('not one search term matched any document. The archive did not go quiet; '
             'something is wrong with the read.')

    cov = os.path.join(ROOT, 'sources/data/minutes-searchable.csv')
    if not os.path.exists(cov):
        fail('sources/data/minutes-searchable.csv is not here — the searchable share '
             'cannot be typed')
    tally = collections.Counter()
    for r in csv.DictReader(open(cov, encoding='utf-8')):
        for k in ('held', 'searchable', 'unsearchable', 'image_scan'):
            tally[k] += int(r[k] or 0)
    if not tally['searchable'] or tally['held'] != tally['searchable'] + tally['unsearchable']:
        fail('minutes-searchable.csv does not reconcile — refusing to publish a coverage '
             'figure that does not add up')
    return terms, dict(held=tally['held'], searchable=tally['searchable'],
                       unsearchable=tally['unsearchable'],
                       image_scan=tally['image_scan'],
                       searchable_share=round(tally['searchable'] / tally['held'], 4))


def split_gap(gap):
    why, closes = gap['why'], None
    marker = '— closes:'
    if marker in why:
        why, closes = why.split(marker, 1)
        why, closes = why.strip(), closes.strip()
    return dict(side=gap['side'], what=gap['what'], why=why, closes=closes)


def gaps():
    rows = list(csv.DictReader(open(GAPS, encoding='utf-8')))
    if not rows:
        fail('money-gaps.csv is empty.')
    by_what = {r['what']: r for r in rows}
    missing = [w for w in CITES_GAPS if w not in by_what]
    if missing:
        fail('this page cites money_gaps rows that are not in the register: %s\n'
             'Rule 7c: the registry outranks the page.' % missing)
    for w in CITES_GAPS:
        if '— closes:' not in by_what[w]['why']:
            fail('the money_gaps row %r has no “— closes:” half. A gap with no named '
                 'remedy is a grievance; a gap with one is a records request.' % w)
    return [split_gap(by_what[w]) for w in CITES_GAPS]


def build():
    db = sqlite3.connect(DB)
    untouched = assert_untouched(db)
    req = required(db)
    app = apportionment(req)
    wea = wealth(req)
    corr = corroborate(req)
    led = ledger(db)
    cand, cand_meta = candidates(db, req, led)
    stu, stu_meta = students(db)
    cnt = counts(req, stu)
    fc = forecast(req, led)
    fig = read_figures()
    printed = assert_printed_apportionment(req, fig)
    assess, assess_meta = assessment(fig, led, req)
    dist = district(fig, led)
    terms, minutes = searched()

    first, last = req[0], req[-1]
    latest_stu = stu[-1]
    prev_stu = [s for s in stu if s['fy'] == latest_stu['fy'] - 1]

    # Growth measured over the span where BOTH counts exist, so a per-student figure is
    # never a ratio of two different year ranges.
    fy_a = max(first['fy'], stu[0]['fy'])
    a = next(r for r in req if r['fy'] == fy_a)

    headline = dict(
        ledger_fy=LEDGER_FY,
        assessment=led['original'],
        expended=led['expended'],
        account=led['account'],
        required=last['mt_rlc'],
        discretionary=round(led['original'] - last['mt_rlc'], 2),
        required_share=round(last['mt_rlc'] / led['original'], 6),
        students=latest_stu['monty_tech'],
        foundation=last['mt_fe'],
        per_student=round(led['original'] / latest_stu['monty_tech'], 2),
        school_choice=latest_stu['school_choice'],
        larger_than_choice=latest_stu['monty_tech'] > latest_stu['school_choice'],
        rlc_share=last['rlc_share'], fe_share=last['fe_share'],
        fb_share=last['fb_share'],
        mt_fb_per_pupil=last['mt_fb_per_pupil'],
        lps_fb_per_pupil=last['lps_fb_per_pupil'],
        foundation_ratio=round(last['mt_fb_per_pupil'] / last['lps_fb_per_pupil'], 4),
        from_fy=fy_a, to_fy=last['fy'],
        required_from=a['mt_rlc'], required_to=last['mt_rlc'],
        required_pct=round(last['mt_rlc'] / a['mt_rlc'] - 1, 6),
        students_from=stu[0]['monty_tech'], students_to=latest_stu['monty_tech'],
        students_pct=round(latest_stu['monty_tech'] / stu[0]['monty_tech'] - 1, 6),
        town_rlc_from=a['town_rlc'], town_rlc_to=last['town_rlc'],
        town_rlc_pct=round(last['town_rlc'] / a['town_rlc'] - 1, 6),
        lps_rlc_pct=round(last['lps_rlc'] / a['lps_rlc'] - 1, 6),
        rise_years=sum(1 for i in range(1, len(stu))
                       if stu[i]['monty_tech'] > stu[i - 1]['monty_tech']),
        of_years=len(stu) - 1,
    )
    # THE RUN, MEASURED. "It has grown every year since" is the sentence this line
    # invites and it is not true here: the count falls in FY2018, FY2019 and FY2025. The
    # longest unbroken rise and the low point are computed so the prose cannot overstate
    # them.
    run = best = 0
    best_end = stu[0]['fy']
    for i in range(1, len(stu)):
        if stu[i]['monty_tech'] > stu[i - 1]['monty_tech']:
            run += 1
            if run > best:
                best, best_end = run, stu[i]['fy']
        else:
            run = 0
    low = min(stu, key=lambda s: s['monty_tech'])
    headline.update(
        longest_rise=best, longest_rise_to=best_end,
        longest_rise_from=best_end - best,
        low_fy=low['fy'], low=low['monty_tech'],
        since_low_pct=round(latest_stu['monty_tech'] / low['monty_tech'] - 1, 6),
        count_gap_min=min(c['difference'] for c in cnt),
        count_gap_max=max(c['difference'] for c in cnt),
    )
    d26 = dist[0]
    fy26 = next(r for r in assess if r['fy'] == LEDGER_FY)
    fy27 = next(r for r in assess if r['fy'] == LEDGER_FY + 1)
    headline.update(
        transport=fy26['transport'], capital=fy26['capital'],
        above_minimum=fy26['above_minimum'],
        next_fy=fy27['fy'], next_total=fy27['total'],
        next_pct=round(fy27['total'] / fy26['total'] - 1, 6),
        district_budget=d26['budget'], district_ch70=d26['ch70'],
        district_ch70_share=d26['ch70_share'],
        district_assessments=d26['all_assessments'],
        district_assessment_share=d26['assessment_share'],
        of_district_budget=d26['lunenburg_of_budget'],
        of_all_assessments=d26['lunenburg_of_assessments'],
        of_members=d26['lunenburg_fe_share'],
        members_fe=d26['members_fe'],
        district_per_pupil=assess_meta['district_per_pupil'],
    )
    if prev_stu:
        headline['students_prev'] = prev_stu[0]['monty_tech']

    # The year the Select Board's five-year projection started from, so the conclusion
    # about that projection can compare the two things that actually moved over its span
    # -- the town-wide requirement and Monty Tech's share of it -- rather than describe
    # them. Neither is a price, and that is the point of the conclusion.
    fc_base = next(r for r in req if r['fy'] == fc['base_fy'])

    return {
        'about': 'What Lunenburg is assessed for Montachusett Regional Vocational '
                 'Technical, what sets that figure, and what neither the town nor the '
                 'district publishes about it.',
        'ledger_fy': LEDGER_FY,
        'first_fy': first['fy'], 'last_fy': last['fy'],
        'headline': headline,
        # WHAT A RESIDENT SHOULD TAKE AWAY, computed here rather than written on the
        # page. The argument in this town is about vocational enrollment rising and the
        # assessment rising with it; these say what that money actually is. Rule 8: what
        # it means for planning, never what anybody got wrong -- and the eleven
        # annual-report rows that fail their own reconciliation are a footnote about a
        # DOCUMENT, so they are in `not_established` and not here.
        'conclusions': emit('monty-tech', [
            conclusion(
                id='a-child-moving-there-moves-the-bill',
                bearing='sizes',
                claim='The single amount the state requires Lunenburg to pay for schools, split between two districts',
                so_what='A child moving to Monty Tech does not add to the town’s bill. It moves part of it.',
                lede='A Lunenburg child enrolling at Monty Tech does not add to what the '
                      'town has to raise for schools. It moves part of it: the state sets '
                      'ONE required contribution for the whole town and splits it between '
                      'the town\u2019s two districts.',
                detail='In %s that single town-wide requirement was %s, of which Monty '
                       'Tech\u2019s share was %s and Lunenburg Public Schools\u2019 %s. '
                       'The town-wide total is the lesser of what the state calculates '
                       'from Lunenburg\u2019s property values and resident income and a '
                       'cap on the local share of its foundation budget \u2014 and the '
                       'wealth figure is the binding one in all %s years DESE publishes, '
                       'so enrollment never enters it. The split is each district\u2019s '
                       'share of the town\u2019s foundation budget, and that identity '
                       'holds to a tenth of a basis point in %s of those years.'
                       % (C.fy(last['fy']), C.usd(last['town_rlc']), C.usd(last['mt_rlc']),
                          C.usd(last['lps_rlc']), C.num(wea['years']),
                          C.num(app['exact'])),
                figures={
                    'fy': figure(last['fy'], C.fy(last['fy'])),
                    'town_required': figure(last['town_rlc'], C.usd(last['town_rlc'])),
                    'monty_tech': figure(last['mt_rlc'], C.usd(last['mt_rlc'])),
                    'lunenburg_schools': figure(last['lps_rlc'], C.usd(last['lps_rlc'])),
                    'years': figure(wea['years'], C.num(wea['years'])),
                    'identity_years': figure(app['exact'], C.num(app['exact'])),
                },
                figure='town_required',
                kind='measured',
                basis='DESE\u2019s Chapter 70 key factors workbook, %s to %s: the '
                      'municipal contribution sheet for Lunenburg minus the district aid '
                      'sheet for Lunenburg Public Schools, year by year. Checked against '
                      'DESE\u2019s own apportionment sheet as Monty Tech reprinted it in '
                      'its FY2027 budget presentation, and against three figures the '
                      'district\u2019s business director gave the Finance Committee in '
                      'three different years.'
                      % (C.fy(first['fy']), C.fy(last['fy'])),
                not_shown='That the town is therefore indifferent to where a child '
                          'enrolls. The state sets a larger foundation budget for a '
                          'vocational pupil than for one in the town\u2019s own schools, '
                          'so a move shifts more than a proportionate slice of the bill; '
                          'the assessment also carries transportation and capital above '
                          'the state minimum, which the district apportions by enrollment '
                          'and not by foundation budget; and nothing here says what '
                          'Lunenburg\u2019s own schools stop spending when a child '
                          'leaves.',
                allow=('70',),
                see=[('/what-the-state-requires-us-to-spend',
                      'what the state requires the town to spend'),
                     ('/if-students-leave', 'what happens when students leave')],
            ),
            conclusion(
                id='the-assessment-is-a-bill-not-a-cost',
                bearing='sizes',
                claim='Billed to Lunenburg for Monty Tech, which is not what a place there costs',
                so_what='State aid paid straight to the school covers most of its budget, and none of that is in this bill.',
                lede='What Lunenburg is billed for Monty Tech is not what a Monty Tech '
                      'place costs. The town\u2019s %s is %s of the district\u2019s '
                      'budget while Lunenburg\u2019s children are %s of its foundation '
                      'enrollment.'
                      % (C.usd(d26['lunenburg']), C.pct(d26['lunenburg_of_budget'] * 100),
                         C.pct(d26['lunenburg_fe_share'] * 100)),
                detail='Monty Tech\u2019s %s budget is %s. Chapter 70 aid paid straight '
                       'to the district covers %s of it, and assessments on all eighteen '
                       'member towns together cover %s; the rest is the district\u2019s '
                       'own receipts, and none of that appears in Lunenburg\u2019s bill. '
                       'So this line measures what the town raises, and it can move in a '
                       'year when nothing at the school costs any more or any less.'
                       % (C.fy(d26['fy']), C.usd(d26['budget']),
                          C.pct(d26['ch70_share'] * 100),
                          C.pct(d26['assessment_share'] * 100)),
                figures={
                    'fy': figure(d26['fy'], C.fy(d26['fy'])),
                    'bill': figure(d26['lunenburg'], C.usd(d26['lunenburg'])),
                    'of_budget': figure(d26['lunenburg_of_budget'] * 100,
                                        C.pct(d26['lunenburg_of_budget'] * 100)),
                    'of_enrollment': figure(d26['lunenburg_fe_share'] * 100,
                                            C.pct(d26['lunenburg_fe_share'] * 100)),
                    'district_budget': figure(d26['budget'], C.usd(d26['budget'])),
                    'ch70_share': figure(d26['ch70_share'] * 100,
                                         C.pct(d26['ch70_share'] * 100)),
                    'assessment_share': figure(d26['assessment_share'] * 100,
                                               C.pct(d26['assessment_share'] * 100)),
                },
                figure='bill',
                kind='measured',
                basis='the district\u2019s own FY2027 budget presentation \u2014 its '
                      '\u201cFY 2027 Budget Summary\u201d page for the budget, the '
                      'Chapter 70 estimate and the total assessed on all eighteen towns, '
                      'and its member-town apportionment sheet for Lunenburg\u2019s own '
                      'line. The town\u2019s side is its MUNIS year-to-date budget '
                      'report, general fund, which carries the same total to the cent.',
                not_shown='What a Lunenburg place at Monty Tech costs. This archive holds '
                          'two of the district\u2019s budget books and no series, no '
                          'all-funds report after a year closed, and nothing that '
                          'attributes any of the district\u2019s spending to one member '
                          'town\u2019s children. The bill can be tracked; the cost '
                          'cannot.',
                allow=('70', '2027'),
                see=[('/state-aid', 'how state aid is set'),
                     ('/what-we-cannot-answer', 'what nobody publishes')],
            ),
            conclusion(
                id='not-an-escalator',
                bearing='lever',
                claim='The actual Monty Tech bill, against a forecast that carried it forward at an inflation rate',
                so_what='This is set by a state formula, not by a price, so it cannot be planned like an ordinary cost.',
                lede='This line cannot be planned as an ordinary cost escalator. Carried '
                      'forward at %s a year it reached %s for %s, and the assessment came '
                      'in at %s.'
                      % (C.pct(fc['rate'] * 100), C.usd(fc['projected']),
                         C.fy(fc['actual_fy']), C.usd(fc['actual'])),
                detail='Over the same span the state-required minimum inside the '
                       'assessment compounded at %s a year, and Monty Tech\u2019s share '
                       'of the town\u2019s foundation budget \u2014 the fraction that '
                       'decides how much of one town-wide requirement lands here \u2014 '
                       'went from %s to %s. Neither of those is a price, and neither is '
                       'inside an inflation assumption. A town that wants this line '
                       'forecast has to forecast the Chapter 70 formula and the split, '
                       'which is a different exercise and a harder one.'
                       % (C.pct(fc['required_cagr'] * 100),
                          C.pct(fc_base['fb_share'] * 100),
                          C.pct(last['fb_share'] * 100)),
                figures={
                    'rate': figure(fc['rate'] * 100, C.pct(fc['rate'] * 100)),
                    'projected': figure(fc['projected'], C.usd(fc['projected'])),
                    'fy': figure(fc['actual_fy'], C.fy(fc['actual_fy'])),
                    'actual': figure(fc['actual'], C.usd(fc['actual'])),
                    'required_cagr': figure(fc['required_cagr'] * 100,
                                            C.pct(fc['required_cagr'] * 100)),
                    'share_from': figure(fc_base['fb_share'] * 100,
                                         C.pct(fc_base['fb_share'] * 100)),
                    'share_to': figure(last['fb_share'] * 100,
                                       C.pct(last['fb_share'] * 100)),
                },
                figure='actual',
                kind='measured',
                basis='the five-year forecast of this line printed in a Select Board '
                      'packet in January 2021, read as a series out of the minutes, '
                      'against the town\u2019s MUNIS ledger for the last year of it and '
                      'against the DESE-derived required-contribution series for the '
                      'same span.',
                not_shown='Why the projection was built that way, or that any other rate '
                          'would have been better. It is one packet, it states a series '
                          'and no method, and nothing here establishes what was assumed. '
                          'What is established is that the quantity being projected is '
                          'set by a state formula rather than by a price.',
                allow=('70', '2021'),
                see=[('/rate-register', 'every rate this project uses, and its source'),
                     ('/why-we-only-get-minimum-aid', 'why the formula lands where it does')],
            ),
        ]),
        'required': req,
        'apportionment': app,
        'wealth': wea,
        'corroboration': corr,
        'ledger': led,
        'candidates': cand,
        'candidates_meta': cand_meta,
        'students': stu,
        'students_meta': stu_meta,
        'counts': cnt,
        'forecast': fc,
        'report_monty_tech': untouched,
        'figures': fig,
        'printed_apportionment': printed,
        'assessment': assess,
        'assessment_meta': assess_meta,
        'district': dist,
        'said': said(),
        'searched': terms,
        'minutes': minutes,
        'documents': documents(),
        'gaps': gaps(),
        'not_established': [
            'What Monty Tech spends over time, or what a Lunenburg place there costs. '
            'The assessment is what the town is BILLED. The archive holds two of the '
            'district’s own budget books — FY2024 and FY2027 — and no series, no year '
            'before FY2024, and no all-funds figure reported after a year closed. So '
            'the bill can be tracked and the cost cannot.',
            'How the assessment divides between operating, transportation and capital '
            'in FY2025, or in any of the eleven annual-report years. The four-part '
            'split is published for FY2024, FY2026 and FY2027 and stated in prose at a '
            'meeting for FY2023. Everywhere else only the total exists.',
            'That the eleven annual-report figures are right. Every one of them fails '
            'the extractor’s own reconciliation, so they are drawn as candidates. What '
            'can be said is that each sits above the independently derived state '
            'minimum by a margin consistent with transportation and capital — which is '
            'a check on their shape, not a check on their values.',
            'Why the district’s FY2027 assessment and the Town’s FY2027 budget line '
            'differ by $47. Both are in the archive, neither mentions the other, and '
            'every other year where two figures exist ties to the dollar or to '
            'eighteen cents.',
            'Why the number of Lunenburg children at Monty Tech has risen. A count is '
            'the outcome of families applying and of Monty Tech admitting, and the '
            'lottery exists precisely because more apply than can be admitted. Nothing '
            'here separates demand from capacity, and the district told the Finance '
            'Committee in February 2026 that it did not know how many Lunenburg '
            'students had been turned away.',
            'Why DESE’s foundation enrollment and DESE’s own October headcount of '
            'Lunenburg residents at Monty Tech disagree in every year, by between '
            'eight below and fifteen above. Both are published; nothing reconciles '
            'them, so every per-student figure on this page names its denominator.',
            'That the town could reduce the assessment by deciding to. Roughly 95% of '
            'it is the Chapter 70 minimum required local contribution, computed by the '
            'state from Lunenburg’s property value and resident income and apportioned '
            'by foundation budget. No Lunenburg vote sets it, and no Lunenburg vote '
            'admits or refuses a child to the school.',
            'What the regional agreement says. The apportionment METHOD is on the '
            'record — the district printed it in the FY2017 annual town report — but '
            'the instrument that binds it is not in this archive, so nothing here can '
            'say whether the ratios can be changed, how bonds would be apportioned, or '
            'what withdrawing from the district would involve.',
        ],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
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
            print('STALE %s — run: python3 scripts/build_monty_tech.py'
                  % os.path.relpath(OUT, ROOT))
            return 1
        print('ok — %s reproduces from the database' % os.path.relpath(OUT, ROOT))
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write('\n')

    h = data['headline']
    print('%s: FY%d–FY%d' % (os.path.relpath(OUT, ROOT), data['first_fy'], data['last_fy']))
    print('  FY%d assessment $%s (ledger, %s) — state minimum $%s, %.1f%% of it'
          % (h['ledger_fy'], format(round(h['assessment']), ','), h['account'],
             format(round(h['required']), ','), h['required_share'] * 100))
    print('  %g students, $%s each; school choice %g'
          % (h['students'], format(round(h['per_student']), ','), h['school_choice']))
    print('  FY%d–FY%d: state minimum %+.1f%%, students %+.1f%%; town-wide %+.1f%%, '
          'Lunenburg schools %+.1f%%'
          % (h['from_fy'], h['to_fy'], h['required_pct'] * 100, h['students_pct'] * 100,
             h['town_rlc_pct'] * 100, h['lps_rlc_pct'] * 100))
    A = data['apportionment']
    print('  apportionment identity holds in %d of %d years (worst miss FY%s, %s pp)'
          % (A['exact'], A['years'], A['worst_fy'], A['worst_gap_pp']))
    W = data['wealth']
    print('  town total wealth-bound in %d of %d years — enrollment does not enter it'
          % (W['wealth_bound_years'], W['years']))
    C = data['candidates_meta']
    print('  %d annual-report candidates FY%d–FY%d, every one above the state minimum '
          'by %.1f%%–%.1f%% (outlier FY%d)'
          % (C['n'], C['first_fy'], C['last_fy'], C['min_pct'] * 100,
             C['max_pct'] * 100, C['outlier_fy']))
    F = data['forecast']
    print('  the town’s own FY%d projection at %.1f%%/yr: $%s. Actual $%s — %+.1f%%'
          % (F['actual_fy'], F['rate'] * 100, format(round(F['projected']), ','),
             format(round(F['actual']), ','), F['miss_pct'] * 100))
    print('  %d corroborations of the derivation against public statements, all exact'
          % len(data['corroboration']))
    P = data['printed_apportionment']
    print('  DESE’s own FY%d apportionment sheet, reprinted by the district: %d fields, '
          'all agreeing with the subtraction (%.2f%% printed, %.2f%% derived)'
          % (P['fy'], P['fields'], P['printed_share_pct'], P['derived_share_pct']))
    M = data['assessment_meta']
    print('  the four parts, FY%d: $%s minimum + $%s transport + $%s capital = $%s'
          % (LEDGER_FY,
             format(round(data['headline']['required']), ','),
             format(round(data['headline']['transport']), ','),
             format(round(data['headline']['capital']), ','),
             format(round(data['headline']['assessment']), ',')))
    print('  FY2027: district $%s, town budget book $%s — %+d'
          % (format(round(M['fy27_district']), ','),
             format(round(M['fy27_town']), ','), M['fy27_gap']))
    D = data['district'][0]
    print('  rule 11: district budget $%s, Chapter 70 %.1f%%, all 18 assessments %.1f%%; '
          'Lunenburg %.2f%% of the budget and %.2f%% of the foundation enrollment'
          % (format(round(D['budget']), ','), D['ch70_share'] * 100,
             D['assessment_share'] * 100, D['lunenburg_of_budget'] * 100,
             D['lunenburg_fe_share'] * 100))
    return 0


if __name__ == '__main__':
    sys.exit(main())
