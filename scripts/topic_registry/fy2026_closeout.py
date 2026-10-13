"""The FY2026 closeout shelf. See scripts/topics.py for the model and the title rule.

Absorbs fy26-closeout, fy26-closeout-town, fy26-school-surplus and fy25-school-surplus. Two
pages on its shelf belong to other categories and are only LISTED here: special education
transportation's FY2026 overrun (transportation) and the FY2026 athletics underspend
(athletics). One question, one page, one address.
"""
CATEGORY = dict(
    id='fy2026-closeout', shelf='FY2026 closeout', title='FY2026 year end', area='town',
    order=51,
    groups=[
        (None, ['fy2026-school-surplus', 'fy2026-surplus-by-category',
                'fy2026-lines-over-budget', 'fy2026-school-transfers',
                'fy2026-surplus-and-fy2027', 'fy2025-school-surplus']),
        ('School lines', ['fy2026-tuition-lines', 'fy2026-paraprofessional-overrun',
                          'fy2026-psychologist-line', 'special-education-transportation',
                          'fy2026-athletics-underspend']),
        ('Town side', ['fy2026-town-unspent', 'fy2026-snow-and-reserve-fund',
                       'fy2026-school-retiree-insurance']),
    ])
GENERATOR = 'build_fy2026_closeout_topics.py'
TOPICS = {
    'fy2026-school-surplus': 'FY2026 school surplus',
    'fy2026-surplus-by-category': 'Surplus by category',
    'fy2026-lines-over-budget': 'Lines over budget',
    'fy2026-school-transfers': 'Year-end transfers',
    'fy2026-surplus-and-fy2027': 'Surplus and FY2027 budget',
    'fy2025-school-surplus': 'FY2025 school surplus',
    'fy2026-tuition-lines': 'Tuition at year end',
    'fy2026-paraprofessional-overrun': 'Paraprofessional overrun',
    'fy2026-psychologist-line': 'Psychologist line',
    'fy2026-town-unspent': 'Town unspent balance',
    'fy2026-snow-and-reserve-fund': 'Snow and Reserve Fund',
    'fy2026-school-retiree-insurance': 'School retiree insurance',
}
