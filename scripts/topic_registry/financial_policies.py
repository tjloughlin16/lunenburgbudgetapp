"""The New financial policies shelf, at /financial-policies. See scripts/topics.py for the model.

TJ, 27 November 2026: a hub for the December financial policies -- the Town's rules in force, the
state's April 2024 draft that would replace them, how the reserves have moved against both, and the
policy calculator, its own page, which applies either rule set (or the reader's own) to the latest
free cash. The hub opens on conclusions, each linked to the page that shows it.

LISTED 27 November 2026 (TJ: "yea it needs to go in the menu"). It was unlisted while TJ reviewed it;
the flag that kept it off /reports, the menu, the home page's count, the search index, the sitemap
and the prerender is gone.
"""
CATEGORY = dict(
    id='financial-policies', shelf='New financial policies', title='New financial policies', area='town',
    order=51,
    start=['policy-calculator', 'financial-policy-rules'],
    groups=[
        ('The rules', ['policy-calculator', 'financial-policy-rules', 'policies-in-practice']),
        ('Behind them', ['retiree-health-liability', 'financial-policy-debate']),
    ],
    elsewhere=[('/town-reserves', 'Stabilization funds'), ('/free-cash', 'Free cash')])
# The calculator's generator writes the hub and the calculator's own page (TJ, 27 November 2026: "i
# wanted the calculator separate"); the report's generator writes the four pages.
GENERATOR = 'build_policy_calculator.py'
TOPIC_GENERATORS = {t: 'build_financial_policies.py' for t in (
    'financial-policy-rules', 'policies-in-practice', 'retiree-health-liability', 'financial-policy-debate')}
TOPICS = {
    'financial-policy-rules': 'Financial policy rules',
    'policies-in-practice': 'The rules in practice',
    'retiree-health-liability': 'Retiree health liability',
    'financial-policy-debate': 'The policy debate',
    'policy-calculator': 'Policy calculator',
}
