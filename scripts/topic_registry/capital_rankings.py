"""The capital planning shelf: every capital request the Town's departments made for FY2023 to
FY2027, how the Capital Planning Committee, the Town Manager and the Collins Center scoring
ranked it, and whether it was funded. One page per fiscal year. See scripts/topics.py.

TJ, 20 November 2026: *"i want to see the ranking year over year"* and *"i want to clik into a FY
and see what was asked for by department, then what was prioritized, in rank order. with data to
show breakdowns and percents by department of who got prioritized"*. So the hub is the years
side by side and each spoke is one year -- and, on TJ's word ("1 page with FY tabs or a
dropdown"), the hub draws every year's page in a tab (topic.py hub(tabs=)), so it reads as one page
while each year keeps its own address. Every figure is sources/data/capital-rankings.csv,
written by scripts/extract_capital_rankings.py.
"""
CATEGORY = dict(
    id='capital-rankings', shelf='Capital planning', title='Capital planning rankings', area='town',
    order=55,
    groups=[
        ('Each year as its own page', ['capital-fy2027', 'capital-fy2026', 'capital-fy2025', 'capital-fy2024',
                              'capital-fy2023']),
    ])
GENERATOR = 'build_capital_rankings.py'
TOPICS = {
    'capital-fy2023': 'FY2023 capital plan',
    'capital-fy2024': 'FY2024 capital plan',
    'capital-fy2025': 'FY2025 capital plan',
    'capital-fy2026': 'FY2026 capital plan',
    'capital-fy2027': 'FY2027 capital plan',
}
