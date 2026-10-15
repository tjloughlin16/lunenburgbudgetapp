"""The Homes and taxes shelf: who lives in Lunenburg, the homes they own and the bill on them,
and how the tax base grows. See scripts/topics.py for the model and the title rule.

Absorbs /lunenburg-by-the-numbers (bythenumbers), /homes-and-taxes (owners),
/homes-and-students (homestudents) and the measured half of /growth (commercial development).
There is no full report: every question those four answered has one page here. The
projection on /growth -- what building would have to do to close the gap, in buildings a
year -- is the model's arithmetic in TypeScript and no payload carries it, so it is not
rebuilt here; the dials stay at /try-growth. Two pages on the shelf belong to other
categories and are only LISTED: enrolment by year (Enrolment) and spending per pupil
(School spending). One question, one page, one address.
"""
CATEGORY = dict(
    id='homes-and-taxes', shelf='Homes and taxes', title='Homes, taxes, growth', area='town',
    order=53,
    groups=[
        ('Who lives here', ['town-population', 'residents-by-age', 'households-with-children',
                            'household-income', 'income-by-age']),
        ('Homes and the bill', ['owners-and-renters', 'average-tax-bill', 'tax-bill-neighbours',
                                'home-value-and-bill', 'regional-school-share',
                                'years-in-the-home', 'bill-by-deed-year']),
        ('Growth', ['homes-and-enrolment', 'new-growth', 'business-building-pace',
                    'commercial-share']),
        ('Related pages', ['enrolment-by-year', 'per-pupil-spending']),
    ],
    elsewhere=[('/try-growth', 'Growth dials: what building would have to do'),
               ('/what-we-cannot-answer', 'What we cannot answer')])
GENERATOR = 'build_homes_and_taxes_topics.py'
TOPICS = {
    'town-population': 'Population and households',
    'residents-by-age': 'Residents by age',
    'households-with-children': 'Households with children',
    'household-income': 'Household income',
    'income-by-age': 'Income by age',
    'owners-and-renters': 'Owners and renters',
    'average-tax-bill': 'Average tax bill',
    'tax-bill-neighbours': 'Bill against neighbours',
    'home-value-and-bill': 'Home value and bill',
    'regional-school-share': 'Regional school share',
    'years-in-the-home': 'Years in the home',
    'bill-by-deed-year': 'Bill by deed year',
    'homes-and-enrolment': 'Homes and enrolment',
    'new-growth': 'New growth',
    'business-building-pace': 'Business building pace',
    'commercial-share': 'Commercial share',
}
