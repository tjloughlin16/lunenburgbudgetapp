"""The Health insurance shelf: what the town and the schools budget for health insurance, how
fast it grows, how Lunenburg compares, and what Chapter 32B lets the town change. See
scripts/topics.py for the model and the title rule.

Absorbs /health-insurance-what-it-costs ('insurance') and /health-insurance ('healthlever').
Two pages on this shelf belong to other categories and are only LISTED here: school retiree
insurance at the FY2026 year end (FY2026 closeout) and the employee benefits group of the
omnibus (Department budgets). One question, one page, one address.
"""
CATEGORY = dict(
    id='health-insurance', shelf='Health insurance', title='Health insurance costs', area='town',
    order=54,
    groups=[
        ('What is budgeted', ['health-insurance-department', 'school-health-insurance',
                              'retiree-health-accounts', 'district-health-line']),
        ('Premiums and other towns', ['health-plans-and-premiums', 'health-state-reported',
                                      'health-towns-compared', 'health-growth-over-time']),
        ('What the town can change', ['health-insurance-options', 'pec-agreement']),
        ('Related pages', ['fy2026-school-retiree-insurance', 'town-employee-benefits']),
    ])
GENERATOR = 'build_health_insurance_topics.py'
TOPICS = {
    'health-insurance-department': 'Insurance department',
    'school-health-insurance': 'School health insurance',
    'retiree-health-accounts': 'Retiree health accounts',
    'district-health-line': 'District health line',
    'health-plans-and-premiums': 'Plans and premiums',
    'health-state-reported': 'State-reported spending',
    'health-towns-compared': 'Towns compared',
    'health-growth-over-time': 'Growth over time',
    'health-insurance-options': 'Options under the law',
    'pec-agreement': 'PEC agreement',
}
