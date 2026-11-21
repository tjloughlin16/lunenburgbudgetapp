"""The capital planning shelf: every capital request the Town's departments made for FY2023 to
FY2027, how the Capital Planning Committee, the Town Manager and the Collins Center scoring
ranked it, and whether it was funded. One page per fiscal year. See scripts/topics.py.

TJ, 20 November 2026: *"i want to see the ranking year over year"* and *"i want to clik into a FY
and see what was asked for by department, then what was prioritized, in rank order. with data to
show breakdowns and percents by department of who got prioritized"*. So the hub is the years
side by side and each spoke is one year. The years are read one at a time on their own page,
capital-years, a tab per year pinned while scrolling (topic.py tabs_page) -- TJ, 20 November 2026:
"we move the per year data to a new page under the hub ... on the hub, we keep aggregate data".
Each year keeps its own address. Every figure is sources/data/capital-rankings.csv,
written by scripts/extract_capital_rankings.py.
"""
CATEGORY = dict(
    id='capital-rankings', shelf='Capital planning', title='Capital planning rankings', area='town',
    order=55,
    groups=[
        ('Every year, one at a time', ['capital-years']),
        ('Beside the capital process', ['school-facility-jobs']),
        ('Each year as its own page', ['capital-fy2027', 'capital-fy2026', 'capital-fy2025', 'capital-fy2024',
                              'capital-fy2023']),
    ])
GENERATOR = 'build_capital_rankings.py'
# School upkeep orders that met the capital cost test without going through ranking (TJ, 21 November
# 2026: "a companion report for the schools ... projects that are WELL WITHIN the purview of capital
# planning"). Its own generator, rebuilt by the refresh whenever the school journal changes.
TOPIC_GENERATORS = {'school-facility-jobs': 'build_school_facility_jobs.py'}
TOPICS = {
    'capital-years': 'Capital plans by year',
    'capital-fy2023': 'FY2023 capital plan',
    'capital-fy2024': 'FY2024 capital plan',
    'capital-fy2025': 'FY2025 capital plan',
    'capital-fy2026': 'FY2026 capital plan',
    'capital-fy2027': 'FY2027 capital plan',
    'school-facility-jobs': 'School upkeep and capital',
}
