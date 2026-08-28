"""Where every figure on this site comes from, tied to the document it came from.

The site asks a resident to accept arithmetic about their own tax bill. "Our sources are
public" is a claim; a numbered citation under the number itself is a check somebody can
actually run.

Two things every entry records:

  * the document, by its path in the published archive, so a reader can download the
    same file we read
  * the BASIS -- which column of it, and whether that column is a budget or actual
    spending

The basis matters more than it looks. A budget is what somebody voted; an actual is what
got spent, and for some lines they differ by 7%. Mixing them produces a growth rate that
is partly growth and partly the step between the two. Every projection on this site is
computed from budget columns only, and `basis` is how a reader confirms that rather than
taking our word for it.

Verify with:  python3 scripts/audit_provenance.py
"""
import sped

# kind: 'budget'    a number somebody voted or proposed
#       'published' a figure stated in a document, not computed by us
#       'contract'  a rate set by a signed agreement
#       'statute'   fixed by law
#       'ours'      our own estimate or projection, built from the above
CITATIONS = [
    dict(id='fy27-approp', metric='The FY27 school budget',
         value='$26,572,288',
         kind='published', basis='Total, Balanced scenario',
         doc='pdf/fy27-final-budget-doc.pdf',
         source='FY27 proposed budget document, 25 March 2026'),

    dict(id='expense-base', metric='What the schools spend, by line',
         value='351 line items',
         kind='budget', basis='column fy27_balanced — the adopted budget, not actual spending',
         doc='xlsx/fy27-proposals.xlsx',
         source='FY27 budget workbook, 25 March 2026'),

    dict(id='cuts', metric='Positions cut from the budget now in force',
         value='9.2 FTE, $1,174,933',
         kind='published',
         basis='The district\u2019s own Scenario D reduction list, plus the program lines '
               'the workbook shows falling between Level Service and Balanced. Two items '
               'make up the difference from the addendum\u2019s own subtotal: Middle '
               'School custodial hours ($9,661, from the workbook) and the 0.2 Music '
               'Teacher at Turkey Hill ($14,488) \u2014 the district listed that post with '
               'no dollar figure, so the amount is OURS, priced from the high school '
               'music position.',
         doc='pdf/fy27-multi-scenario-addendum.pdf',
         source='Multi-Scenario Financial Analysis, §5, with the FY27 workbook'),

    dict(id='override', metric='Override questions passed, and what they would have cost',
         value='0 of 2',
         kind='published', basis='Precinct tallies; tax impact from the Town Manager',
         doc='pdf/town-2026-election-unofficial-results.pdf',
         source='Town election results, 16 May 2026'),

    dict(id='levy', metric='Revenue: levy limit, new growth, excluded debt, state aid',
         value='$49,963,990 omnibus',
         kind='published', basis='The revenue formula as the Town published it',
         doc='pdf/town-fy27-budget-press-release.pdf',
         source="Town Manager's FY27 budget release, 17 April 2026"),

    dict(id='prop25', metric='Proposition 2½ levy growth',
         value='2.5%',
         kind='statute', basis='Massachusetts General Laws c.59 §21C',
         doc='pdf/town-revenue-prop25-presentation.pdf',
         source='Finance Committee deck on Proposition 2½'),

    dict(id='salaries', metric='Salary growth',
         value='4.0% a year',
         kind='contract', basis='2.5 / 4.0 / 3.5% scale increases plus steps worth ~3.3%',
         doc='contracts/pdf/dese-teacher-contract.pdf',
         source='Lunenburg Education Association agreement, FY25–FY27'),

    dict(id='health', metric='Health insurance growth',
         value='9.0% a year',
         kind='published', basis="The district's own stated FY27 assumption",
         doc='pdf/health-insurance-rates-2025.pdf',
         source='Health insurance rates 2025, and the FY27 budget narrative'),

    dict(id='sped-tuition', metric='Out-of-district special education growth',
         value='8.0% a year',
         kind='ours', basis='Our estimate. The district publishes no rate for this line.',
         doc='xlsx/fy27-proposals.xlsx',
         source='FY27 budget workbook, lines 9300 and 9400'),

    dict(id='sped', metric='Special education growth, in district',
         value=f'{sped.RATE:.2%} a year',
         kind='ours',
         basis=('OURS. It is what the staff in this line are contracted to receive, '
                'weighted by how much of the line each group is: '
                + ', '.join(f"{u['label'].lower()} at {u['rate']:.1%} across "
                            f"{u['share']:.0%} of it" for u in sped.UNITS
                            if u['id'] != 'unbargained')
                + '. The bus contract publishes no escalator, so its figure is what the '
                'budgets show that line doing. '
               f'It is deliberately NOT the rate the line itself did. That figure is '
               f'{sped.WHOLE_LINE_RATE:.2%}, and it is one hiring decision rather than a '
               f'trend: paraprofessionals rose {sped.PARA_FY27_RATE:.0%} in FY27, which was '
               f'{sped.PARA_SHARE_OF_RISE:.0%} of the whole year\u2019s increase, while '
               f'every other part of special education fell. Those aides are already inside '
               f'the amount this model starts from, so escalating it at '
               f'{sped.WHOLE_LINE_RATE:.2%} would assume they are hired again every year. '
               'The assumption this rate does make is that the FY27 hiring was a step and '
               'not the first year of a climb. Nothing in a budget can test that \u2014 a '
               'budget shows dollars per line and never shows people, and the district does '
               'not publish staff counts. The full range is published beside the rate.'),
         doc='xlsx/fy27-proposals.xlsx',
         source='FY27 budget workbook, columns fy25_budget, fy26_final and '
                'fy27_level_service, with the LEA and AFSCME agreements'),

    dict(id='ch70', metric='Chapter 70 aid and the foundation budget',
         value='$9,349,335',
         kind='published', basis='DESE preliminary FY27 Chapter 70',
         doc='xlsx/ch70-fy27-summary.xlsx',
         source='DESE Chapter 70 summary, FY27'),

    dict(id='taxbase', metric='New growth, assessed value by class, average tax bill',
         value='FY18–FY23 series',
         kind='published', basis="The Assessors' own year-by-year tables",
         doc='pdf/tax-classification-fy23.pdf',
         source='Tax Classification Hearing, FY2023'),

    dict(id='athletics', metric='What each sport costs, and how many play it',
         value='25 sports',
         kind='published', basis='Cost and participation per sport, FY24',
         doc='pdf/athletic-program-costs-by-sport.pdf',
         source='Athletic program costs by sport'),

    dict(id='fees', metric='What families pay in athletic and bus fees',
         value='$400 first child',
         kind='published', basis="Superintendent's email, August 2026; prior schedule from the FAQ",
         doc='pdf/lhs-athletics-faq.pdf',
         source='High school athletics fee schedule'),

    dict(id='peers', metric='How neighboring districts compare',
         value='11 districts',
         kind='published', basis='In-district expenditure per pupil, FY2018–FY2024',
         doc='xlsx/dese-all-districts.xlsx',
         source='DESE per-pupil expenditures'),

    dict(id='gap', metric='The projected FY28 gap',
         value='our projection',
         kind='ours',
         basis='Computed from the FY27 adopted budget and the growth rates above. '
               'There is no FY28 budget yet — that work starts in January 2027.',
         doc='xlsx/fy27-proposals.xlsx',
         source='Built by this project from the FY27 budget workbook'),
]

KIND_LABEL = {
    'budget': 'Budget document',
    'published': 'Published figure',
    'contract': 'Signed agreement',
    'statute': 'Set by law',
    'ours': 'Our projection',
}


def export():
    by_id = {c['id']: i + 1 for i, c in enumerate(CITATIONS)}
    return dict(
        items=[dict(c, n=by_id[c['id']]) for c in CITATIONS],
        kindLabels=KIND_LABEL,
        note='Every projection on this site is computed from budget columns — what was '
             'voted or proposed — never from actual spending. The two are different '
             'quantities and mixing them produces a growth rate that is partly growth '
             'and partly the difference between them.',
    )


if __name__ == '__main__':
    for i, c in enumerate(CITATIONS, 1):
        print(f"[{i:>2}] {c['metric']}")
        print(f"     {KIND_LABEL[c['kind']]} · {c['basis']}")
        print(f"     {c['source']}  ->  sources/{c['doc']}")
