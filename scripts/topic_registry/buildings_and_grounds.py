"""The Buildings and grounds shelf. See scripts/topics.py for the model and the title rule.

Started 20 October 2026 (notes/plans/BUILDINGS-AND-GROUNDS.md, Hub F of
notes/plans/MUNIS-JOURNAL-REPORTS.md). TJ: *"what reports do we need to convey this to the
voters to make THEM the experts?"* -- so the pages are SCAFFOLDED: each teaches the idea the
next one needs, in reading order, and the conclusion page comes with its proof.

The reader the figures are written for is the Town Manager (notes/process/PERSONAS.md, 8):
every figure ties to MUNIS by account number. Planned, not yet built: how the budget is set,
upkeep over the year, who does the work, building money from every fund, questions for the
budget.
"""
CATEGORY = dict(
    start=['upkeep-ledger', 'upkeep-budget-vs-spending'],
    id='buildings-and-grounds', shelf='Buildings and grounds', title='Building upkeep',
    area='school', order=27,
    groups=[
        (None, ['upkeep-ledger', 'upkeep-spending', 'upkeep-budget-vs-spending',
                'upkeep-surplus-every-dollar', 'upkeep-skipped']),
        ('Account by account', ['contracted-building-services']),
    ])
GENERATOR = 'build_buildings_topics.py'
TOPICS = {
    'upkeep-spending': 'What upkeep buys',
    'upkeep-budget-vs-spending': 'Upkeep budget and spending',
    'contracted-building-services': 'Contracted building services',
    'upkeep-surplus-every-dollar': 'Upkeep surplus, every dollar',
    'upkeep-skipped': 'Usual purchases skipped',
    'upkeep-ledger': 'Upkeep leftover by account',
}
