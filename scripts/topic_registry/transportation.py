"""The Transportation shelf. See scripts/topics.py for the model and the title rule."""
CATEGORY = dict(
    id='transportation', shelf='Transportation', title='School bus costs', area='school', order=10,
    full_report=('/analysis/transportation', 'School transportation, the full report'),
    groups=[
        (None, ['dee-bus-contract', 'special-education-transportation',
                'state-reimbursement', 'bus-fee', 'fy2027-bus-budget']),
        ('Athletic transportation', ['athletic-bus-funding', 'fy2027-athletic-bus-cut',
                                     'bus-cost-by-sport', 'away-trips-by-sport']),
    ])
GENERATOR = 'build_transportation.py'
TOPICS = {
    'dee-bus-contract': 'Dee Bus contract',
    'special-education-transportation': 'Special education transportation',
    'state-reimbursement': 'State reimbursement',
    'bus-fee': 'Bus fee',
    'fy2027-bus-budget': 'FY2027 bus budget',
    'athletic-bus-funding': 'Athletic bus funding',
    'fy2027-athletic-bus-cut': 'FY2027 athletic bus cut',
    'bus-cost-by-sport': 'Bus cost by sport',
    'away-trips-by-sport': 'Away trips by sport',
}
