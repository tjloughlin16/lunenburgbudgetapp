"""Build the public source catalogue the app renders under "The documents".

Why a script rather than a hand-written JSON: the catalogue makes a public claim — "here
is every document this analysis is built on". A hand-maintained list drifts the moment a
file is renamed, and a source index that lies is worse than no source index. So the
descriptions are curated here (they are editorial judgement, not derivable), and
everything checkable is checked:

  * every catalogued file must exist, or the build fails
  * sizes and page-or-row counts come from the files themselves
  * every primary file on disk must be catalogued, or the build fails

That second check is the one that matters. Adding a document to sources/ without
describing it is the normal way an index goes stale, so it is an error rather than a
silent omission.

The meeting archive is handled separately. 1,383 documents cannot be a list a person
reads, so it is summarized as a corpus with per-board counts, built from minutes/index.csv.

    python3 scripts/build_source_index.py

Writes fy28/src/data/sources.json.
"""
import csv
import hashlib
import re
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources')
OUT = os.path.join(ROOT, 'fy28', 'src', 'data', 'sources.json')
DOCS = os.path.join(ROOT, 'fy28', 'public', 'docs')

# Cloudflare Pages refuses a single asset over 25MB. Files above it are published anyway
# and flagged, never altered: a source document that has been resampled to fit a host is
# no longer the document, and a reader who diffs our copy against the town's is exactly
# the reader this page is for. Where a file exceeds this, the host has to change.
MAX_BYTES = 25 * 1024 * 1024

# Files too large for the site's own host are served from R2, which has no per-file cap
# and, more to the point, no egress charge -- a public archive should not have a bill that
# scales with how much the public reads it. Keyed by path so the exception is visible here
# rather than hidden in the catalogue.
ELSEWHERE = {
    'contracts/pdf/dese-teacher-contract.pdf':
        'https://pub-5baef0f2604545c398a39a176e400e34.r2.dev/'
        'contracts/pdf/dese-teacher-contract.pdf',
}

SCHOOL_HUB = ('https://www.lunenburgschools.net/department-directory/'
              'superintendent-of-schools/school-budget-information')
TOWN_HUB = 'https://www.lunenburgma.gov/835/2026-Annual-Town-Meeting-FY27-Budget-Hub'

# Origins are cited per group rather than per file: the town and district publish through
# document hubs and portals that do not give stable per-document URLs, so a per-file link
# would rot faster than the archive it points at.
ORIGINS = [
    {'id': 'school', 'name': 'Lunenburg Public Schools', 'url': SCHOOL_HUB},
    {'id': 'town', 'name': 'Town of Lunenburg', 'url': TOWN_HUB},
    {'id': 'dese', 'name': 'Massachusetts DESE', 'url': 'https://www.doe.mass.edu/'},
    # The free cash proofs were filed under DESE, which is the wrong department: they are
    # the Department of Revenue's, and the distinction is not cosmetic. DESE sets Chapter
    # 70; DOR certifies free cash. A reader tracing a figure needs to be sent to the right
    # agency, and the report is one form submission away rather than one link.
    {'id': 'dls', 'name': 'Massachusetts DOR, Division of Local Services',
     'url': 'https://dls-gw.dor.state.ma.us/gateway/dlspublic/'
            'certificationfreecashpublicreport/certificationfreecashpublic'},
    {'id': 'peers', 'name': 'Neighboring districts', 'url': None},
    {'id': 'request', 'name': 'Obtained from the Town by records request', 'url': None},
    {'id': 'us', 'name': 'Built by this project', 'url': None},
]

# Which documents came to us because somebody asked for them, rather than because they
# were posted. Worth marking for two reasons: it is the honest answer to "is all of this
# public", and a reader who wants these for themselves needs to know the route is a
# request rather than a link.
BY_REQUEST = {'munis-ledgers/', 'budget-workbooks/school-funds-fy26.xlsx'}

# Two halves, and the divide matters more than any grouping inside them. Everything above
# the line was published by the town, the district, the state or a neighboring district.
# Everything below it we made. A reader who cannot tell those apart cannot judge either.
SECTIONS = {
    'theirs': dict(
        title='Published by the town, the district and the state',
        blurb='Primary documents. We did not write any of these and we did not commission '
              'them. {byrequest} came from the Town by records request and say so on their '
              'row; {given}; the rest were already public. {linked} of '
              'them link back to the exact '
              'file the publisher put up, and {verified} of those addresses have been '
              'checked the only way an address can be \u2014 by downloading what is there '
              'now and matching it against our copy, byte for byte. A link that merely '
              'looks right is not a source. {unlinked} still have no address of their own, '
              'and they are three different things: state reports built on form '
              'submission, where the page and the jurisdiction are the whole answer; a '
              'table we built here from a document that is itself listed above; and '
              'documents gathered before the mirror existed, where nobody wrote down '
              'where they came from. Only the last is a gap, it is a gap on our side and '
              'not the town\u2019s, and it is named in notes/findings/DATA-WANTED.md. Where a '
              'document is unreadable or says something inconvenient, it is here anyway.'),
    'reference': dict(
        title='Everything else the district and the town publish',
        blurb='Mirrored here so it is available and so no figure has to be looked up over '
              'the network. {unused} of these {total} feed no number on this site. The '
              'other {overlap} are byte-identical copies of primary sources listed above — '
              'kept, and marked as such on their row, because a mirror with the '
              'load-bearing documents quietly removed is no longer a copy of the '
              'publisher’s page. It is all here because a document nobody kept is a '
              'document nobody can check, and because we would rather hold what we did '
              'not use than be asked why we did not look.'),
    'ours': dict(
        title='Written by this project, not by the town',
        blurb='Everything below this line is ours. It is not town information, it carries '
              'no official standing, and nobody at the district or the Town has reviewed '
              'or approved it. It is one resident’s reading of the documents above, '
              'published so it can be argued with — which means checked against those '
              'documents, and disagreed with where the reading is wrong.'),
}

# stars: 3 = load-bearing, a conclusion rests on it · 2 = corroborating · 1 = context
def _line_history_counts():
    """The counts in the catalogue entry below, read from the file they describe.

    They were typed, and they drifted: the entry said 417 distinct lines while the
    extractor produced 415, and then 416 when a parsing fix recovered two of the largest
    salary lines in the budget. A figure typed into prose beside a computed one is the
    only thing here that can be silently wrong (rule 2), and a catalogue is prose.
    """
    path = os.path.join(ROOT, 'sources/data/line-history.csv')
    if not os.path.exists(path):
        return (0, 0, 0)
    rows = list(csv.DictReader(open(path, encoding='utf-8')))
    return (len(rows), len({r['source'] for r in rows}), len({r['key'] for r in rows}))


_LH = _line_history_counts()

GROUPS = [
    {
        'section': 'theirs', 'id': 'district-budget', 'origin': 'school',
        'title': 'The district budget, line by line',
        'blurb': 'The FY27 budget in every published version. Nearly every figure in this '
                 'analysis traces to one of these five documents.',
        'items': [
            ('budget-workbooks/fy27-proposals.xlsx', 'FY27 budget workbook, 25 March 2026', 3,
             'The richest single document here. 1,197 rows: FY23–FY25 actuals, FY26 final '
             'budget plus actuals-to-date and encumbrances, and all four FY27 scenarios. '
             'Every budget-line figure on this site comes from this workbook.'),
            ('budget-workbooks/fy27-budget-projection-3-25-26.xlsx', 'The same workbook, as circulated to the Finance Committee', 2,
             'Data-identical to the file above across every budget column; the differences '
             'are an unused scratch column and one ratio row. Kept so anyone working from '
             'the Finance Committee copy can confirm they match.'),
            ('budget-workbooks/PROVENANCE.md', 'Where the three FY27 workbooks came from', 2,
             'Written by us. The workbooks carry the site\u2019s most load-bearing figures '
             'and the one the model reads has no recorded address. This records what the '
             'files say about themselves \u2014 all three created by the district\u2019s '
             'Business Administrator, one last saved by the Finance Committee member who '
             'sent it \u2014 and, kept separate, what that does not establish: metadata '
             'says who authored a file, never who gave it to us.'),
            ('budget-workbooks/fy27-budget-projection-2-24-26.xlsx', 'Earlier budget workbook, 24 February 2026', 1,
             'The 24 February version, before the restoration list was revised. Useful only '
             'for tracking what changed between drafts.'),
            ('district-budget/docs/final-budget-document.pdf', 'FY27 proposed budget document, 25 March 2026', 3,
             'The printed line-item budget: FY26 final against the Restoration, Core and '
             'Balanced scenarios. 351 line items.'),
            ('district-budget/docs/fy27-budget-projections-as-of-3-23-26.pdf', 'FY27 line-item projections, 23 March 2026', 3,
             'The version that carries the Level Service column, so all five scenarios sit '
             'side by side. This is the document that settles what "level service" cost.'),
            ('district-budget/docs/fy27-budget-projections-as-of-3-16-26-with-restorations.pdf', 'FY27 line-item projections, 16 March 2026', 1,
             'An earlier draft with the restoration figures still in.'),
            ('district-budget/docs/budget-addendum-multi-scenario-financial-analysis.pdf', 'Multi-Scenario Financial Analysis', 3,
             'The narrative behind the four scenarios: what each one is, the cut and '
             'restoration lists, headcounts, impact statements, and the comparative '
             'summary. The source of every FTE count quoted here.'),
            ('district-budget/docs/additional-town-revenue-spending-plan.pdf', 'Additional Town Revenue Spending Plan', 3,
             'The $453,722 of positions added back at the September 2026 Special Town '
             'Meeting, with the district’s reasoning for each.'),
            ('district-budget/docs/balanced-budget-slides-3-23-26.pdf', 'Balanced budget slide deck, 23 March 2026', 1,
             'Presented to the School Committee. Image-only — no text layer, so nothing '
             'in it could be quoted or checked.'),
            ('district-budget/docs/slide-deck-from-the-sc-meeting-3-23-26.pdf', 'School Committee deck, 23 March 2026', 1,
             'Also image-only, and also unreadable without optical character recognition.'),
        ],
    },
    {
        'section': 'theirs', 'id': 'town-budget', 'origin': 'town',
        'title': 'Town budget, revenue and the override',
        'blurb': 'How much money the town has, where the Proposition 2½ formula puts the '
                 'ceiling, and what happened at the ballot in May 2026.',
        'items': [
            ('town-budget/docs/4090-click-here-for-a-release-on-quot-understanding-lunenburg-apos-s-fy27-budget-how-.pdf', 'Town Manager’s FY27 budget release, 17 April 2026', 3,
             'The revenue formula in full — levy limit, new growth, excluded debt, state '
             'aid, local receipts — plus all three budget scenarios by category, the cut '
             'lists and the tax impact per household. The backbone of the revenue model.'),
            ('town-supplementary/docs/town-2026-election-unofficial-results.pdf', 'Election results, 16 May 2026', 3,
             'Both override questions defeated roughly two to one, in every precinct. '
             'Precinct-by-precinct tallies.'),
            ('town-budget/docs/3769-fy-2027-operating-budgets-balanced-tier-1-tier2.pdf', 'Operating budgets: Balanced, Tier 1, Tier 2', 3,
             'The omnibus by department under all three funding scenarios — what each '
             'override tier would have bought, department by department.'),
            ('town-budget/docs/4082-fy-2027-detailed-budget.pdf', 'Detailed town budget by line', 2,
             'Line-item town budget by organization and object code, including the Monty '
             'Tech assessment.'),
            ('town-budget/docs/3765-town-meeting-booklet-including-warrant.pdf', 'Annual Town Meeting booklet and warrant, 2026', 2,
             'The full 52-page warrant, including the revolving fund authorisations under '
             'Article 6.'),
            ('town-budget/docs/4161-2026-annual-town-election-warrant.pdf', 'Ballot question language', 1,
             'The exact wording voters saw for both override questions.'),
            ('town-budget/docs/4111-article-13-fy-2027-capital-plan.pdf', 'FY27 capital plan, Article 13', 1,
             'Capital requests, separate from the operating budget.'),
        ],
    },
    {
        'section': 'theirs', 'id': 'quarterly', 'origin': 'town',
        'title': 'Quarterly financial reports, FY26 Q3',
        'blurb': 'The town’s financial position as of 31 March 2026, reported in August 2026 '
                 '— the first quarterly report after a near-complete turnover of the finance '
                 'office. This is where the funds held outside the operating budget appear.',
        'items': [
            ('munis-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx', 'Special revenue funds, 31 March 2026', 3,
             'Every special revenue and revolving fund the town holds, with opening balance, '
             'receipts, spending and closing balance. Includes the special education circuit '
             'breaker account, which appears in no budget document.'),
            ('munis-ledgers/fund-balances/trust-agency-fy2026-p09.xlsx', 'Trust, agency and stabilization funds, 31 March 2026', 3,
             'All stabilization and trust fund balances — general stabilization, OPEB, '
             'vehicle and equipment, conservation, and the rest.'),
            ('town-budget/docs/fincom-memo-fy26-q3.docx', 'Finance Director’s memo to the Finance Committee', 3,
             'The covering memo, dated 11 August 2026. Reports revenue and expenditure '
             'against budget, and gives the finance department’s own account of why '
             'quarterly reporting had lapsed.'),
            ('munis-ledgers/revenue/glytdbud-revenue-fy2026-p09-gf-all.pdf', 'General fund revenue, 31 March 2026', 2,
             'Revenue collected against budget by account. Local receipts came in at 116% '
             'of budget.'),
            ('munis-ledgers/expenses/glytdbud-expense-fy2026-p09-gf-all.pdf', 'General fund expenditures, 31 March 2026', 2,
             'Spending against budget by department, including the school department line.'),
            ('town-budget/docs/fincom-deck-fy26-q3.pptx', 'Finance Committee presentation, 13 August 2026', 1,
             'The slides that accompanied the memo.'),
            ('munis-ledgers/revenue/glytdbud-revenue-fy2026-p09-ef-sewer.pdf', 'Sewer enterprise fund — revenue', 1,
             'Enterprise funds are self-supporting and separate from the general fund. '
             'Included for completeness.'),
            ('munis-ledgers/expenses/glytdbud-expense-fy2026-p09-ef-sewer.pdf', 'Sewer enterprise fund — expenditures', 1,
             'Self-supporting; does not bear on the school budget.'),
            ('munis-ledgers/revenue/glytdbud-revenue-fy2026-p09-ef-water.pdf', 'Water enterprise fund — revenue', 1,
             'Self-supporting; does not bear on the school budget.'),
            ('munis-ledgers/expenses/glytdbud-expense-fy2026-p09-ef-water.pdf', 'Water enterprise fund — expenditures', 1,
             'Self-supporting; does not bear on the school budget.'),
            ('munis-ledgers/revenue/glytdbud-revenue-fy2026-p09-ef-solid-waste.pdf', 'Solid waste enterprise fund — revenue', 1,
             'Self-supporting; does not bear on the school budget.'),
            ('munis-ledgers/expenses/glytdbud-expense-fy2026-p09-ef-solid-waste.pdf', 'Solid waste enterprise fund — expenditures', 1,
             'Self-supporting; does not bear on the school budget.'),
            ('munis-ledgers/revenue/glytdbud-revenue-fy2026-p09-ef-peg-access.pdf', 'Cable and broadband enterprise fund — revenue', 1,
             'Self-supporting; does not bear on the school budget.'),
            ('munis-ledgers/expenses/glytdbud-expense-fy2026-p09-ef-peg-access.pdf', 'Cable and broadband enterprise fund — expenditures', 1,
             'Self-supporting; does not bear on the school budget.'),
        ],
    },
    {
        'section': 'theirs', 'id': 'school-funds', 'origin': 'request',
        'title': 'School funds held outside the budget',
        'blurb': 'Revolving and gift accounts that belong to the schools but never appear in '
                 'the operating appropriation. Obtained by records request, and a record of '
                 'money actually received and spent rather than budgeted.',
        'items': [
            ('budget-workbooks/school-funds-fy26.xlsx', 'School gift, athletics and choice funds, FY26 year-end', 3,
             'Full-year reconciliation of three funds: opening balance, revenue by source, '
             'spending by category, closing balance. The only place actual athletics fee '
             'collections appear — $188,944 in FY26.'),
        ],
    },
    {
        'section': 'theirs', 'id': 'dese-staffing', 'origin': 'dese',
        'title': 'State staffing and spending counts',
        'blurb': 'What the state records Lunenburg employing and spending, by year. It '
                 'carries the quantity the district\u2019s own budget documents cannot '
                 'give: how many paraprofessionals there are.',
        'items': [
            ('dese/district-spending-categories.csv',
             'Staffing and spending by category, FY09\u2013FY25', 3,
             'Massachusetts DESE, via the state open-data portal. Teacher FTE, '
             'paraprofessional FTE, in-district pupils, per-pupil expenditure by function '
             'and student demographics, every year since 2009. The paraprofessional count '
             'is the one figure that lets a budget line be read as staffing rather than as '
             'dollars \u2014 and it says the para budget has grown roughly six times '
             'faster than the number of paras. Rebuild with scripts/fetch_dese.py.'),
        ]},
    {
        'section': 'theirs', 'id': 'tax-base', 'origin': 'town',
        'title': 'Tax base, Chapter 70 and peers',
        'blurb': 'Where the town’s money comes from, what the state contributes, and how '
                 'Lunenburg’s spending compares to its neighbors.',
        'items': [
            ('town-budget/docs/tax-classification-fy23.pdf', 'Tax Classification Hearing, FY2023', 3,
             'The single most valuable town document found. Carries year-by-year new growth '
             'FY18–FY23, assessed value by class, average single-family bills back to '
             'FY19, and excess levy capacity — series that appear nowhere else.'),
            ('budget-workbooks/ch70-fy27-summary.xlsx', 'DESE Chapter 70 summary, FY27', 3,
             'Foundation enrollment, foundation budget, required local contribution, Chapter '
             '70 aid and required net school spending, for every district in the state.'),
            ('budget-workbooks/dese-all-districts.xlsx', 'DESE per-pupil expenditures, FY2018–FY2024', 3,
             'Spending by category and per pupil, Lunenburg against eleven peer districts, '
             'with enrollment. Note: this is in-district expenditure, which by DESE’s '
             'definition excludes out-of-district tuition.'),
            ('town-budget/docs/1591-town-revenue-amp-proposition-2-5-presentation.pdf', 'Finance Committee deck on Proposition 2½', 2,
             'Levy ceiling against levy limit against actual levy, and the state analysis '
             'showing assessed value outpacing the levy since 2017.'),
            ('town-supplementary/docs/assessors-agenda-11-19-2025.pdf', 'Board of Assessors agenda, 19 November 2025', 1,
             'Context on the classification process.'),
        ],
    },
    {
        'section': 'theirs', 'id': 'contracts', 'origin': 'school',
        'title': 'Union contracts and salary schedules',
        'blurb': 'Where the 4% salary growth assumption comes from. Most are page scans, read '
                 'with optical character recognition.',
        'items': [
            ('contracts/data/lea-teacher-salary-schedule.csv', 'Teacher salary schedule, FY25–FY27', 3,
             'Thirteen steps by ten lanes by three years, rebuilt from the printed FY25 grid '
             'and the contract’s own multipliers.'),
            ('contracts/pdf/dese-teacher-contract.pdf', 'Lunenburg Education Association agreement', 3,
             'Runs 1 July 2024 to 30 June 2027. Raises of 2.5%, 4.0% and 3.5%, plus step '
             'increases worth about 3.32% a year. Expires at the end of FY27, so FY28 is '
             'the first year of an agreement nobody has negotiated.'),
            ('contracts/pdf/paraprofessional-fy26-fy28.pdf', 'Paraprofessional agreement, FY26–FY28', 2,
             'Raises of 3.0%, 2.0% and 2.0%. Runs to 30 June 2028.'),
            ('contracts/pdf/paraprofessional-salary-fy26-fy28.pdf', 'Paraprofessional salary schedule', 2,
             'The rate grid behind the agreement.'),
            ('contracts/pdf/custodial-2023-2026.pdf', 'Custodial agreement, 2023–2026', 2,
             'The expiring custodial contract.'),
            ('contracts/pdf/custodial-moa-2026.pdf', 'Custodial memorandum of agreement, 2026', 2,
             'Successor terms: 3.5%, 2.5%, 2.5% through FY29.'),
            ('contracts/pdf/nonaffiliated-salary-schedule.pdf', 'Non-affiliated salary schedule', 1,
             'Staff outside any bargaining unit.'),
            ('contracts/pdf/nonaffiliated-benefits.pdf', 'Non-affiliated benefits', 1,
             'Benefit terms for the same group.'),
            ('contracts/pdf/dese-superintendent-contract.pdf', 'Superintendent contract template', 1,
             'A DESE template from 2018–21, not a current Lunenburg agreement. No current '
             'administrator contract is public — a real gap.'),
            ('contracts/pdf/dese-administrator-contract.pdf', 'Administrator contract template', 1,
             'Also an expired DESE template, 2019–22.'),
            ('town-supplementary/docs/health-insurance-rates-2025.pdf', 'Health insurance rates, 1 July 2026', 3,
             'Plan-by-plan premiums and the town’s 75/25 contribution split — the basis '
             'for every health insurance figure here.'),
        ],
    },
    {
        'section': 'theirs', 'id': 'peers', 'origin': 'peers',
        'title': 'What neighboring districts did',
        'blurb': 'Primary FY27 budget documents from comparable districts. The comparison is '
                 'only fair if it comes from their own books rather than from reporting.',
        'items': [
            ('peers/groton-dunstable-fy27-budget-book.pdf', 'Groton-Dunstable FY27 budget book', 3,
             '132 pages. Three consecutive years of cuts, a budget below level service, and '
             'an override the district says is needed "now and in the foreseeable future". '
             'Also states plainly that it plans to offset $2M of costs with circuit breaker '
             'funding.'),
            ('peers/ashburnham-westminster-fy27-presentation.pdf', 'Ashburnham-Westminster FY27 budget', 3,
             'The district that made the opposite choice — explicitly preserved athletics, '
             'arts and music, and cut two elementary teaching positions instead.'),
            ('peers/ashburnham-westminster-fy27-detail.pdf', 'Ashburnham-Westminster line detail', 2,
             'The line-item version of the same budget.'),
            ('peers/ayer-shirley-fy27-expenses.pdf', 'Ayer-Shirley FY27 expenses', 2,
             'Level-service budget by function. Health insurance up 14.4% — the steepest '
             'in the group.'),
            ('peers/north-middlesex-finance-subcommittee.pdf', 'North Middlesex budget summit notes', 2,
             'A $64,000 deficit at 3% growth against $1.5M at 5%. Roughly 30% of students '
             'receive special education, far above the state average.'),
            ('peers/wachusett-fy27-budget-presentation.pdf', 'Wachusett FY27 budget presentation', 2,
             'Member-town assessments, enrollment by town, and a discretionary contribution '
             'up 9.21%.'),
        ],
    },
    {
        'section': 'theirs', 'id': 'fees', 'origin': 'school',
        'title': 'Fees and program costs',
        'blurb': 'What families pay, and what the programs cost to run.',
        'items': [
            ('district-budget/docs/athletic-program-costs-by-sport.pdf', 'Athletic program costs by sport', 3,
             'Cost and participation for all 25 sports. The basis for every fee calculation '
             'on this site.'),
            ('district-budget/docs/lhs-athletics-faq.pdf', 'High school athletics fee schedule', 2,
             'The superseded schedule — $250, $140 and $85 with a $475 family cap. Still '
             'the only fee table published anywhere, though the fee rose to $400 for '
             '2026-27. A family checking the website today gets the wrong number.'),
        ],
    },
    {
        'section': 'theirs', 'id': 'business', 'origin': 'town',
        'title': 'Business registrations',
        'blurb': 'Town Clerk business certificate records, cleaned and categorised, behind the '
                 'commercial growth argument.',
        'items': [
            ('data/business/merged_dataset.csv', 'Business certificate records', 2,
             '711 records — certificate number, dates, name, owner, address, status and '
             'renewal chain. Note these are sole proprietor and partnership filings only; '
             'corporations register with the state and are not here.'),
            ('data/business/categorized.csv', 'Business records by industry', 2,
             '554 records tagged by industry category, which is what shows that most new '
             'registrations are at residential addresses.'),
        ],
    },
    {
        'section': 'theirs', 'id': 'dls', 'origin': 'dls',
        'title': 'Free cash, certified — Lunenburg and eight comparable towns',
        'blurb': 'The Division of Local Services publishes a Free Cash Proof for every '
                 'community: the year-end calculation of what a town may appropriate '
                 'without raising taxes, broken into its components. Downloaded 30 August '
                 '2026. These reconcile to themselves twice over — 81 checks across nine '
                 'towns and five years, all tying to the dollar. They carry no denominator '
                 'of any kind, so the absolute figures do not compare between towns of '
                 'different size; the composition, being a share, does.',
        'items': [
            ('dls/free-cash-proof-lunenburg.xlsx',
             'Lunenburg free cash proof, 2021–2025', 3,
             'Certified free cash rose from $2,666,962 to $3,354,370 over the five years. '
             'Two thirds of the 2025 figure is money appropriated and not spent.'),
            ('dls/PROVENANCE.md', 'Where these came from, and what they cannot do', 2,
             'Written by us. Records the exclusion of a tenth file supplied as Abington '
             'which contains Lunenburg’s data in all 102 cells, and states plainly that no '
             'denominator appears anywhere in these workbooks.'),
            ('dls/free-cash-proof-ayer.xlsx', 'Ayer', 1, 'Peer comparison.'),
            ('dls/free-cash-proof-groton.xlsx', 'Groton', 1, 'Peer comparison.'),
            ('dls/free-cash-proof-littleton.xlsx', 'Littleton', 1, 'Peer comparison.'),
            ('dls/free-cash-proof-shirley.xlsx', 'Shirley', 1, 'Peer comparison.'),
            ('dls/free-cash-proof-townsend.xlsx', 'Townsend', 1, 'Peer comparison.'),
            ('dls/free-cash-proof-upton.xlsx', 'Upton', 1, 'Peer comparison.'),
            ('dls/free-cash-proof-uxbridge.xlsx', 'Uxbridge', 1, 'Peer comparison.'),
            ('dls/free-cash-proof-westford.xlsx', 'Westford', 1, 'Peer comparison.'),
        ],
    },
    {
        'section': 'theirs', 'id': 'athletics-ledger', 'origin': 'request',
        'title': 'The athletics ledger, obtained by records request',
        'blurb': 'Answered by the Town on 17 June 2026, to a request by a resident. These '
                 'are the first documents in this archive that record money moving on a '
                 'date — the cashbook of the athletics revolving fund for three full '
                 'fiscal years — rather than a prior year re-presented inside next year’s '
                 'budget argument. The request form is not published: it carries the '
                 'requester’s home address and telephone number, and no figure depends on '
                 'them. Provenance, the town’s own filenames and a sha256 for each file '
                 'are in PROVENANCE.md, listed below.',
        'items': [
            ('munis-ledgers/expenses/PROVENANCE-fy2026-p12.md',
             'Where the FY26 period 12 report came from', 2,
             'The email, the sender, the date, both filenames as sent, and the sha256 of '
             'each. Also what the report is NOT: period 12 rather than the year-end close, '
             'expenditures only, and with zero balance accounts suppressed. And the '
             'reconciliation that establishes the spreadsheet and the printout are one '
             'report, since only the printout states a period.'),
            ('munis-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.xlsx',
             'FY26 year-to-date budget report, period 12 \u2014 spreadsheet', 3,
             'The first ACCOUNT-LEVEL general fund expenditure report in this archive. '
             'Every prior one was run with Print totals only: Y, which renders the whole '
             'school district as a single row; here it is 258 accounts, each with an org '
             'code, an object code and a description. Sent by Jennifer Warren, Town '
             'Manager, on 2 September 2026, produced the evening before by Karen Barrett, '
             'Town Accountant. The sender\u2019s filename is '
             '\u201cFY26 BUDGET YEAR TO DATE REPORT (9-1-2026).xlsx\u201d. It carries the '
             'appropriation columns UN-ROUNDED, which the printed form does not. '
             '**Period 12, not 13** \u2014 June, with the books not yet closed; the Town '
             'Manager\u2019s covering note says the figures \u201care likely to continue '
             'to adjust as we continue the year-end reconciliation process\u201d. Zero '
             'balance accounts are suppressed, so an account absent here is not '
             'necessarily absent from the ledger.'),
            ('munis-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.pdf',
             'FY26 year-to-date budget report, period 12 \u2014 as printed', 28,
             'The same report as MUNIS prints it, and the only one of the pair that states '
             'its own parameters: Year/Period 2026/12, Print totals only: N, Suppress zero '
             'bal accts: Y, Account type Expense, program glytdbud. The spreadsheet states '
             'no period at all, so the two are asserted to be one report by reconciling '
             'the spreadsheet\u2019s 635 account rows to this file\u2019s own printed '
             'GRAND TOTAL \u2014 expended $52,163,984.85 and encumbrances $529,325.69 '
             'agree to the cent. The three appropriation columns differ by under a dollar '
             'because this file rounds them and the spreadsheet does not, which settles '
             'something the project had only been able to back-solve: the rounding is in '
             'the printing, not in the ledger. The sender\u2019s filename is '
             '\u201cPrint_ YEAR-TO-DATE BUDGET REPORT.pdf\u201d.'),
            ('munis-ledgers/account-details/account-details-fy2025-fund1301.xlsx',
             'Athletics revolving fund, journal detail, FY2025', 3,
             'Every receipt and payment in fund 1301 for FY2025, with effective and posting '
             'dates. The town’s filename is FY25 Account_Detail.xlsx. Despite the name it '
             'is one account only — 1301-0-000-0000-00-0-00-0-104000, CASH. Four general '
             'journal entries described only as an adjustment "per memo" account for '
             '$254,121.18 of the $390,299.87 that came in.'),
            ('munis-ledgers/account-details/account-details-fy2024-fund1301.xlsx',
             'Athletics revolving fund, journal detail, FY2024', 3,
             'The same export for FY2024, the year the fund’s cash fell by $103,852.53. Its '
             'opening balance is a row the town prints, which is what lets the three years '
             'be chained and checked. The town’s filename is FY24 Account_Detail_.xlsx.'),
            ('munis-ledgers/account-details/account-details-fy2026-fund1301.xlsx',
             'Athletics revolving fund, journal detail, FY2026', 2,
             'FY2026 to 12 June 2026 — eighteen days short of year-end, so not a closed '
             'year. Its payroll total ties to the cent to the salary line in the fund’s own '
             'year-end reconciliation. The town’s filename is FY26 Account_Detail.xlsx.'),
            ('munis-ledgers/account-details/athletics-by-sport-fy2024-fy2026.xlsx',
             'Athletics by sport, three school years', 3,
             'The district’s own operating workbook: one row per sport, with participation '
             'counts by fee category and cost lines for officials, coaches, transportation, '
             'uniforms and the rest, for 23/24, 24/25 and 25/26. The only document here that '
             'puts a cost against a sport. It also states the high school fee for each year, '
             'which is how we learned the 2025-26 rate was $325 and not the $250 the model '
             'assumed. Its own totals do not all tie, and which ones do not is published '
             'alongside it. The town’s filename is Copy of Athletics 24.25 (1).xlsx.'),
            ('munis-ledgers/account-details/athletic-fee-counts-fy2026.docx',
             'Athletic fee counts, 2025-2026', 2,
             'One page: participation counts by fee category for each season of 2025-26 — '
             'full pay, reduced fee, sibling discounts and full waivers. The only source '
             'giving those counts for that year; the workbook’s columns for it are empty. '
             '79 full waivers against 455 full-pay. The town’s filename is '
             'ATHLETIC FEES 2025.docx.'),
        ],
    },
    {
        'section': 'ours', 'id': 'analyses', 'origin': 'us',
        'title': 'Our analyses',
        'blurb': 'What we concluded, written up so it can be argued with. These are the '
                 'only documents here we wrote — everything else in this archive was '
                 'published by somebody else. Where one of them turned out to be wrong, the '
                 'correction is in the document rather than quietly removed.',
        'items': [
            ('analyses/show-your-work.md',
             'Show your work: every calculation, opened up', 3,
             'The method document. Every figure this project publishes, with its inputs, '
             'the formula, a worked example in real dollars, and — beside each one — '
             'whether it is somebody else’s figure, a contract, a statute, our '
             'measurement or our assumption. Fifteen sections: the projection itself, '
             'why each escalator is what it is, special education, out-of-district '
             'tuition, health insurance, free cash, athletic fees, the levers, the cut '
             'cascade, the tax base and overrides, an assumption register ranked by what each one moves, and what none of it can compute. '
             'GENERATED from the live model by scripts/build_show_your_work.py, so it '
             'cannot drift from the code — run it with --check to prove the copy you '
             'are reading is current. Written to be usable by an assistant checking a '
             'number as well as by a resident following the argument.'),
            ('analyses/fy27-and-the-override.md', 'The FY27 budget and the override', 3,
             'Where things stand: the adopted budget, the four scenarios, what the balanced '
             'budget cut, the override result, the town\u2019s revenue mechanics, and the '
             'first-cut FY28 arithmetic. The foundation the rest of this rests on.'),
            ('analyses/fy27-cut-reconciliation.md', 'Two right numbers: reconciling the FY27 cut', 3,
             'The FY27 budget was cut by $1,174,933 and by $761,000, and both are correct. '
             'A line-by-line bridge between them, and the three places the district\u2019s '
             'own documents disagree with each other. Includes a correction to an earlier '
             'version of this analysis.'),
            ('analyses/sped-and-the-curve.md', 'Special education and the curve', 3,
             'The FY27 level-service budget rises 3.98%. Strip out one line \u2014 '
             'out-of-district tuition, budgeted down 46% \u2014 and it rises 6.23%. What that '
             'one-off is doing to the rate, and what it risks for FY28. Budget columns '
             'only; no actual spending is used anywhere in it.'),
            ('analyses/charts/fy26-school-budget.svg',
             'FY26 school department: what happened to the budget', 1,
             'One stacked bar \u2014 spent, encumbered, unspent \u2014 as parts of the '
             'revised budget. The unspent slice is 1.8% and is the one the headline '
             'reports.'),
            ('analyses/charts/fy26-school-spend.svg',
             'FY26 school department: where the money went', 1,
             'The ten largest accounts by spending, with everything else folded into one '
             'recessive bar.'),
            ('analyses/charts/fy26-town-budget.svg',
             'FY26 town: what happened to the budget', 1,
             'The same stacked bar for the other 67 departments.'),
            ('analyses/charts/fy26-town-variance.svg',
             'FY26 town: the biggest misses, both directions', 1,
             'The same diverging bar for the town side, where 18 accounts overspend '
             'against the school department\u2019s 56.'),
            ('analyses/charts/fy26-town-spend.svg',
             'FY26 town: where the money went', 1,
             'The ten largest town accounts by spending.'),
            ('analyses/charts/fy26-school-variance.svg',
             'FY26 school department: the biggest misses, both directions', 1,
             'A diverging bar chart, the seven largest overspends and the seven largest '
             'underspends on one zero line. Deliberately not a pie: two of the three '
             'questions these charts answer are about VARIANCE, a signed quantity, and a '
             'pie cannot show a negative. Colours were run through a palette validator '
             'rather than chosen by eye. Rebuild with scripts/build_closeout_charts.py.'),
            ('analyses/fy26-closeout-town.md',
             'FY26 on the town side, as the books stood in June', 2,
             'The same account-level ledger read for the other 67 departments. Snow '
             'removal cost $1,038,092 against an appropriation of $355,571 \u2014 292% '
             '\u2014 while the town\u2019s $185,000 Reserve Fund went entirely unused. '
             '$3.3M left the operating budget for capital and stabilization. And '
             '$1,262,376 of school retiree health insurance sits in a town department, '
             'invisible in the school budget, which is part of why DESE\u2019s all-funds '
             'figure exceeds the appropriation. The town overspends on 18 of 376 accounts '
             'where the schools overspend on 57 of 259 \u2014 a fact with four '
             'explanations and no way here to choose between them. Period 12, so nothing '
             'in it is a surplus. Verified by scripts/verify_fy26_closeout_town.py.'),
            ('analyses/fy26-closeout.md', 'FY26, as the books stood in June', 2,
             'The first account-level ledger this project has held, read line by line. '
             'The school department was $482,101 under budget at period 12 \u2014 the '
             'small remainder of $1,683,534 unspent across 160 accounts against $1,201,433 '
             'overspent across 56. Carries the kindergarten paraprofessional question: the '
             'FY26 approved budget published a \u2212100% cut to that line, $99,064 was '
             'spent on it anyway with no appropriation and no transfer, and three readings '
             'fit the record equally well. Period 12 is NOT the year-end close, so nothing '
             'in it is a surplus. Every figure is recomputed by '
             'scripts/verify_fy26_closeout.py; a PDF is published beside it.'),
            ('analyses/connecting-the-budget.md',
             'What connects the school budget to the Town\u2019s books, and what does not', 2,
             'How far a dollar can be followed from what was budgeted to what was spent. '
             'It works for the department as a whole \u2014 both school departments '
             'reconcile to $1.93 \u2014 and by category, where 41 of the budget\u2019s 45 '
             'function codes meet the code carried inside the Town\u2019s account numbers. '
             'It stops below that: MUNIS shortens account names to ten characters, so '
             'MS GUIDANC and HS GUIDANC are both 2710 where the budget has a row per '
             'school, and no single line can be followed into the ledger by anyone, inside '
             'the Town or outside it. The category comparison holds for FY2026 period 12 '
             'and no other period, because that is the one report that arrived as a '
             'spreadsheet rather than a PDF \u2014 the printed form drops the account '
             'string, and the account string is the join.'),
            ('analyses/connecting-the-budget.pdf',
             'The same analysis, rendered for reading on paper', 3,
             'A rendering of analyses/connecting-the-budget.md, not a separate document '
             'and not a separate source. Built by scripts/build_analysis_pdf.py; a copy '
             'accompanies the request sent to the Town. If the two ever differ, the '
             'markdown is the one every figure was verified against.'),
            ('analyses/fy26-closeout.pdf',
             'The FY26 closeout analysis, rendered for reading on paper', 3,
             'A rendering of analyses/fy26-closeout.md, built by '
             'scripts/build_analysis_pdf.py. The markdown is the source; every figure in '
             'it is recomputed by scripts/verify_fy26_closeout.py.'),
            ('analyses/budget-vs-actual.md', 'Budget versus actual', 2,
             'Did what the town budgeted match what it spent? Written for two readers \u2014 '
             'plain terms and the evidence, side by side. Deliberately separate from the '
             'app\u2019s projection, and it says why. Unfinished: it names what it cannot '
             'see without the town\u2019s accounting records.'),
            ('analyses/athletics.md', 'Athletics: what it costs and who pays', 2,
             'The one program where both sides of the money are visible, and therefore a '
             'test case for the whole budget: how far is an appropriation from what a '
             'thing costs? Very far. The district published athletics against the '
             'revolving fund once, for FY19, and in every year that document reports as '
             'actual the fund paid more of athletic transportation than the town did. '
             'Also what an "actual" on this line really is \u2014 in the one ledger view we '
             'have, a purchase order with nothing yet paid. Verify with '
             'scripts/verify_athletics.py.'),
            ('analyses/free-cash.md',
             'Free cash: is Lunenburg hoarding, or rebuilding?', 3,
             'Two claims about the same number — that the town is too conservative, and '
             'that its free cash is not up to standard — set against the DLS proof for nine '
             'towns. It does not settle the argument, and says why in the first paragraph: '
             'a standard for free cash is a ratio and these files are a numerator. What it '
             'does establish is the shape. Two thirds of Lunenburg’s 2025 free cash is money '
             'appropriated and not spent, up from 31% in 2023 — a balance built from '
             'underspending is a different thing from one built from revenue beating '
             'forecast, and they imply different remedies.'),
            ('analyses/athletics-ledger.md',
             'The athletics ledger: what a cashbook shows that a budget line cannot', 3,
             'Written from the records request answered on 17 June 2026 — the first dated '
             'record of money moving that this project has held for anything touching the '
             'school budget. The fund’s cash for three years, tied end to end against the '
             'opening balances the town itself prints. Four journal entries, described only '
             'as an adjustment made per a memo we do not hold, carry 65% of one year’s '
             'receipts. What the district’s own workbook says athletics cost, against what '
             'the town appropriated for it: 44% in FY2024. And why none of that measures '
             'special education, while still changing what we should believe about it. '
             'Every figure recomputed by scripts/verify_records_request_2026_06.py.'),
            ('analyses/sped-and-funds.md', 'Special education and the funds outside the budget', 2,
             'Special education as a cost driver, out-of-district tuition, the circuit '
             'breaker account, and the school and town money held outside the operating '
             'appropriation. Carries a correction notice at the top \u2014 two growth figures '
             'in it were derived on a basis we no longer stand behind.'),
            ('analyses/peer-districts.md', 'What other districts did', 2,
             'The comparison across neighboring districts, and the order in which things '
             'actually get cut when an override fails.'),
        ],
    },
    {
        'section': 'ours', 'id': 'derived', 'origin': 'us',
        'title': 'Built by this project',
        'blurb': 'Machine-readable extracts. Derived from the documents above and '
                 'rebuildable from them.',
        'items': [
            ('data/lps-budget-lines.csv', 'Budget lines, tidy CSV', 3,
             '356 rows extracted from the district workbook — section, function group, '
             'line item, and one column per fiscal year and scenario. Line sums tie to the '
             'printed totals within about $2 for FY25–FY27. Rebuild with '
             'scripts/extract_lps_budget.py.'),
            ('munis-ledgers/account-details/PROVENANCE-fund1301.md',
             'Provenance for the 17 June 2026 records request', 2,
             'Written by us, filed with the documents it describes: where each one came '
             'from, the town’s own filename for it, a sha256, and what each file '
             'actually contains as opposed to what its name suggests. Rule 12 asks for all '
             'of that at the same time as the document rather than retrofitted, and this '
             'is what that looks like. It also records what is deliberately not published '
             'and why.'),
            ('data/capital-plan-fy27.csv',
             'The FY27 capital programme, ranked by the town', 3,
             'All 22 projects the departments requested, in the Capital Planning '
             'Committee’s own rank order, with cost and the running total the town prints '
             'beside it — and a flag for the twelve that got funded. $3,267,208 requested '
             'against $1,830,203 funded, so $1,437,005 of ranked work is already below the '
             'line. That queue is why taking a dollar out of free cash costs a dollar of '
             'capital: nothing gains slack, the line just moves up. Rebuild with '
             'scripts/extract_capital_plan.py, which checks every row against the '
             'document’s own cumulative column and refuses to write if one disagrees.'),
            ('data/capital-funding-history.csv',
             'How the capital programme has been paid for', 2,
             'Eight years of capital funding split by source — free cash, taxation, '
             'unexpended prior-year capital — each row reconciled to the total it prints. '
             'Free cash is the largest and steadiest source, averaging $591,286 a year on '
             'the town’s own figures, which is what makes redirecting it a trade rather '
             'than a saving. Two of the ten published years are deliberately excluded: '
             'they carry footnoted figures whose column cannot be told reliably.'),
            ('data/free-cash-proof.csv',
             'Free cash, nine towns, five years, line by line', 3,
             '630 rows: town, year, proof line, amount, the role that line plays in the '
             'calculation, and the cell it came from. Rebuild with '
             'scripts/extract_free_cash.py, which reconciles every town-year against two '
             'totals the source prints itself and refuses to write if any of the 81 checks '
             'fails.'),
            ('data/rate-register.csv',
             'Every rate, with the year it applies to and who set it', 3,
             'Athletic fees, bus fees, collective bargaining raises, facilities and the '
             'fees the district’s payment portal sells — 62 rates, each carrying the fiscal '
             'year it applies to, the document that set it and the date. Built after FY26 '
             'athletic fees were modelled at $250 a season when the district had voted '
             '$325: not a wrong number, a right number from the wrong year, taken from a '
             'schedule that states its rates and never states which year they cover. It '
             'deliberately includes rates we do NOT use and the ten we cannot state at all, '
             'because a fee the town charges and does not publish is a finding rather than '
             'a blank. Rebuild with scripts/build_rate_register.py.'),
            ('data/athletic-fee-schedule.csv',
             'Athletic fees, by fiscal year, with their sources', 3,
             'The detail behind the register: every athletic fee tier for FY24 to FY27, '
             '27 of the 31 figures verified against a spreadsheet cell or a direct '
             'quotation from the School Committee vote that set them. The script refuses '
             'to write if any figure stops matching its source. Rebuild with '
             'scripts/extract_fee_schedule.py.'),
            ('data/fund-1301-cash-journal.csv',
             'The athletics revolving fund’s cashbook, three years', 3,
             '277 rows — every receipt and payment in fund 1301 for FY2024, FY2025 and '
             'FY2026 to 12 June 2026, with dates, warrant references and the town’s own '
             'comments. One column, running_balance_derived, is ours and not the town’s: '
             'MUNIS exports rows, not a balance, and many rows are backdated, so the order '
             'is a reconstruction and is named as one. Rebuild with '
             'scripts/extract_fund1301_ledger.py, which refuses to write unless each '
             'year’s closing balance equals the opening balance the town prints for the '
             'next.'),
            ('data/athletics-by-sport.csv',
             'Athletics by sport, long form', 3,
             '960 rows: season, level, sport, year, metric, value — and the cell each value '
             'came from, so any figure can be checked against the workbook without '
             'trusting this file. The three season sheets do not share a column layout, so '
             'the extractor reads the header rows rather than assuming positions. Rebuild '
             'with scripts/extract_athletics_by_sport.py.'),
            ('data/athletics-by-sport-reconciliation.csv',
             'Where the district’s workbook does not add up', 2,
             'Every total the sport workbook prints, against the sum of the rows above it: '
             '342 checks, of which 271 tie and 71 do not. Published rather than quietly '
             'handled, because whether a column ties is a property of the document and '
             'anyone resting a figure on one needs to know. The Spring 2024-25 '
             'transportation total is blank while the rows beneath it hold $18,242.50.'),
            ('data/school-special-revenue-fy26-q3.csv',
             'The school\u2019s funds outside the appropriation', 3,
             'All 62 grant and revolving accounts the school department holds, from the '
             'town\u2019s special revenue ledger \u2014 obtained by records request, FY26 to '
             '31 March 2026. Fund number, the town\u2019s own name, revenue, salaries paid, '
             'expenditure and balance. The only source here showing GRANT MONEY PAYING '
             'SALARIES, which is what settles whether a general fund line is growing '
             'because the district grew or because a grant stopped paying. Rebuild with '
             'scripts/extract_special_revenue.py.'),
            ('data/town-ledger-fy26-q3.csv',
             'The town\u2019s own ledger, FY26 to 31 March', 3,
             'All 67 general fund departments as the Town Accountant\u2019s system prints '
             'them: original appropriation, transfers and adjustments, revised budget, '
             'year-to-date expended, encumbrances. Extracted from '
             'munis-ledgers/expenses/glytdbud-expense-fy2026-p09-gf-all.pdf, which came from the Town '
             'by records request rather than off a website. This is the only source here '
             'that shows money MOVING between lines during a year \u2014 28 of the 67 '
             'departments had some, $489,411 in and $148,177 out, of which $76,394 went to '
             'the school department. The extract reconciles to the report\u2019s own GRAND '
             'TOTAL before it will write; an earlier version silently dropped 16 '
             'departments whose figures printed as \u201c.00\u201d. Rebuild with '
             'scripts/extract_town_ledger.py.'),
            ('data/gross-school-budget-fy2026.xlsx',
             'The gross school budget, FY26 \u2014 spreadsheet', 5,
             'The district\u2019s own budget in the district\u2019s own shape \u2014 same '
             'sections, same 78 function groups, same line names, same order \u2014 with '
             'two things added that their version cannot show: what was actually spent, '
             'and what other money paid for the same thing. Where either is not held the '
             'cell says so in amber rather than being left blank, because a blank reads '
             'as zero and the whole reason a net budget misleads is that nothing marks it '
             'net. Five sheets: the budget, the 258 ledger accounts (a DIFFERENT '
             'structure, kept separate because no published document maps one to the '
             'other), the funds outside the general fund, what is missing and who has it, '
             'and a reconciliation proving the net column still ties to the '
             'district\u2019s published appropriation. Rebuild with '
             'scripts/build_gross_budget_xlsx.py.'),
            ('data/fy26-code-reconciliation.xlsx',
             'FY26 school budget against the town ledger, by function code \u2014 '
             'spreadsheet', 5,
             'The district\u2019s FY26 budget line by line with the Town Accountant\u2019s '
             'ledger beside it, summed by function code on both sides. The join is the '
             'function code in the fourth segment of the MUNIS account string '
             '(0100-3-300-2330-51-2-13-1-511203), which is the same code the '
             'district\u2019s workbook prints over each group \u2014 the crosswalk the '
             'gross budget spreadsheet had to leave empty. THE DISTRICT\u2019S WORKBOOK '
             'DOES NOT SUM BY CODE, so every code here carries its own two sums and '
             'their difference: 9 of 46 do not agree. Within a code, lines are paired by '
             'AMOUNT, which is not a key \u2014 it shows a figure of that size exists on '
             'both sides, never that the two are the same line \u2014 and every row says '
             'how it was paired. 23 rows pair with nothing, and 6 accounts were spent '
             'against with neither an appropriation nor a transfer. Rebuild with '
             'scripts/build_code_reconciliation_xlsx.py.'),
            ('data/munis-ledger.csv',
             'Every MUNIS budget report we hold, one table', 3,
             'The Town Accountant\u2019s year-to-date budget reports \u2014 expenditures '
             'and revenues, general fund and enterprise funds \u2014 parsed into one '
             'normalised table by scripts/extract_munis_report.py, which reads the format '
             'rather than one file, so reports for other years load with no new code. '
             'Each report reconciles to its own printed GRAND TOTAL before it is written. '
             'Revenue is kept NEGATIVE exactly as MUNIS prints it. Two things this found: '
             'ef-solid-waste-expenditures-fy26-q3.txt is not an expenditure report \u2014 '
             'it declares Account type Revenue and duplicates the file named -revenue-, so '
             'no solid waste expenditure report is held at all; and the sewer report '
             'covers four funds whose headers our text extraction runs together, so a fund '
             'is positional rather than per-row.'),
            ('data/account-names.csv',
             'What the ledger\u2019s account codes mean \u2014 our readings', 3,
             'The town\u2019s ledger prints ten-character abbreviations and stops: '
             '`SCHRETHLTH`, `COLL TUITI`, `KINDAIDREG`. Nothing published expands them. '
             'So these 80 readings are OURS, and each records the basis it rests on: '
             '**district document** where the district\u2019s own budget prints the full '
             'line name (7), **department name** where the department it sits in settles '
             'it (17), **department context** where the org or object code does (16), and '
             '**plain reading** where the abbreviation is unambiguous English (40). Keyed '
             'on department, because the same code means different things in different '
             'places \u2014 `REG TRANS` is school busing in department 300 and a regional '
             'transit assessment in department 825. The verifiers fail if either closeout '
             'analysis names a code with no entry here.'),
            ('data/stated-figures.csv',
             'Figures the town stated about itself, with the quote', 3,
             'Not ours and not computed from anything here. The FY25 school surplus as the '
             'district stated it \u2014 $582,115.44 on 3 September 2025 and $603,885.97 on '
             '17 September after purchase orders were closed \u2014 each with who said it, '
             'the minutes it is quoted from and the line number. Recorded separately from '
             'everything we derive, because the town\u2019s closing figure is arrived at '
             'by closing its books and we cannot do that arithmetic from what we hold.'),
            ('data/dese-radar.csv',
             'DESE\u2019s own figures, every district, FY2009\u2013FY2025', 3,
             'The state\u2019s RADAR district comparison: enrollment, demographics, '
             'staffing FTE, MCAS and per-pupil expenditure by function, ACROSS ALL FUNDS, '
             'for all 421 Massachusetts districts. The first view of Lunenburg school '
             'spending here that is neither the town\u2019s general fund nor written by '
             'the district, so it bounds from outside the money the budget document cannot '
             'see. Three cautions travel with it: DESE counts costs the school budget does '
             'not carry, so its total must never be subtracted from the town\u2019s '
             'appropriation to produce \u201chidden money\u201d; it says all funds and '
             'gives one number, so it cannot say which dollar came from a grant; and its '
             'paraprofessional figure is FTE from the state\u2019s staffing collection, '
             'not a headcount. Each district-year is checked against DESE\u2019s own '
             'printed in-district total \u2014 16 fail, all charter schools, and Lunenburg '
             'ties in all 17 years. Rebuild with scripts/extract_dese_radar.py.'),
            ('data/lunenburg.db',
             'The whole analysis database, SQLite', 3,
             'Every figure on this site in one queryable file, built by '
             'scripts/build_db.py from the CSVs above, which remain the source of truth. '
             'It is a derived read model: dropped and rebuilt from scratch on every run, '
             'never edited by hand, because a row in a database has no address, no '
             'publisher filename and no checksum. Every fact row carries the document it '
             'came from. Also served as a read-only JSON API at /api/index, with '
             '/api/schema stating the grain of each table and the four ways to get a '
             'confident wrong answer out of it.'),
            ('data/athletics-history.csv',
             'Athletics, both sides of the money, FY14\u2013FY26', 3,
             'Every line of the town\u2019s athletics appropriation and every line of the '
             'fee-funded Chapter 658 revolving fund, for each year either was published. '
             'The FY14\u2013FY19 half is reconstructed from the district\u2019s own FY19 '
             'athletics budget and CHECKED against that document\u2019s stated column '
             'totals \u2014 five of six years tie to the dollar on each side, and the script '
             'refuses to write if any year is off by more than the document\u2019s own '
             'rounding. FY20\u2013FY23 has no fund side because nobody published one, which '
             'is the finding rather than a gap in our reading. Feeds the athletics page '
             'and no projection. Rebuild with scripts/extract_athletics_history.py.'),
            ('data/document-basis.csv',
             'What produced each document\u2019s figures', 3,
             'Every document in this archive classified by SOURCE TYPE: ledger (the '
             'accounting system \u2014 a figure exists because a transaction did), '
             'restatement (a prior year re-presented inside a document written by the '
             'party that spent it), forward (proposed, requested, level service, '
             'balanced), or narrative. Each row quotes the raw header text the '
             'classification rests on, with its line number or cell reference, so any row '
             'can be checked in one grep; workbook rows also record which columns are '
             'HIDDEN. Of 216 documents, 15 are ledger-basis and exactly one of those '
             'reaches school budget lines. Rebuild with '
             'scripts/classify_document_basis.py.'),
            ('data/grants-history.csv',
             'Grant income by grant, FY20\u2013FY24', 3,
             'Every entitlement and competitive grant the district reports receiving, by '
             'name and amount, read out of the Grants History pages of the FY25 '
             'superintendent\u2019s budget update. This is the only place in anything '
             'Lunenburg publishes where the funding streams outside the general fund are '
             'named and priced \u2014 which is what rule 11 says the budget documents '
             'cannot do. Read from one deck deliberately: several presentations carry '
             'grant pages, so all three are read and every row names its document, its '
             'page, the district\u2019s own link, our copy and the file\u2019s sha256 \u2014 '
             'which matters because the district\u2019s copy of the main source now asks '
             'for a Google sign-in and ours is the one a resident can open. Where two '
             'decks state a grant differently both statements are kept and marked. '
             'Rebuild with scripts/extract_grants.py.'),
            ('data/link-status.csv',
             'Whether each source document is still public', 2,
             'For every archived document that records where its publisher put it, '
             'whether that address still opens. On 29 August 2026 it mostly did not: 57 '
             'of 184 returned a Google sign-in wall, every one of them a Drive or Docs '
             'link, while the town\u2019s own web server answered 81 of 81. The district '
             'was asked to reopen them and did \u2014 on 31 August the same 187 came back '
             '186 open. Both readings are the archive\u2019s reason for existing, '
             'measured. Rebuild with scripts/check_source_links.py.'),
            ('data/copy-status.csv',
             'Whether the publisher\u2019s copy is still our copy', 2,
             'The question underneath the one above. A link can still open and serve a '
             'different document \u2014 a Drive file can be replaced in place without its '
             'URL changing, and nothing in a link check would notice. So every address is '
             'fetched and the result compared to our copy by sha256. It also separates '
             'the ways bytes can differ without the document differing: a Google Doc is '
             're-zipped on every export, and a PDF can be re-saved with a heading\u2019s '
             'line-break in a new place. Only one of those is a change. Rebuild with '
             'scripts/verify_source_copies.py.'),
            ('data/variance-by-group.csv',
             'Budget against actual, every group and year', 3,
             'The whole-budget sweep behind analyses/budget-vs-actual.md \u00a72b: every '
             'function group, every year, with net and gross variance, churn and spread. '
             'Churn is what the first attempt at this lacked \u2014 ranking groups by net '
             'hides any group whose over- and under-spends cancel, which is how athletics '
             'was missed. Rebuild with scripts/analyze_variance.py.'),
            ('data/line-history.csv',
             'Every budget line, budget and actual, year by year', 3,
             f'{_LH[0]:,} readings from {_LH[1]} of the district\u2019s budget documents, '
             f'normalised to {_LH[2]:,} distinct lines, each column mapped to the fiscal '
             'year and kind the '
             'document itself states. Both budget and actual columns are kept, which is '
             'what analyses/budget-vs-actual.md needs and what no projection may read. '
             'The lines do not sum back to the district totals, so the analysis asks '
             'which lines miss and how often rather than apportioning the total. Rebuild '
             'with scripts/extract_line_history.py.'),
            ('data/line-history-disagreements.csv',
             'Where two documents state the same budget line differently', 3,
             'Every figure each document states for a line the archive marks as '
             'contested, and which statement the ordering kept. It exists because '
             '`documents_disagree` was a flag, and a flag is the least a reader can be '
             'told: the completeness matrix called a year partial on the strength of it '
             'and could not say whether that meant one line out of 282 or a third of the '
             'year \u2014 while the losing figure had been discarded, so nothing could '
             'show the dispute even if it wanted to. Nothing here decides which document '
             'is right. It also separates the cases that are OURS: the district prints '
             'Dues/Meetings under three function groups, and matching lines by their '
             'printed name collapses them into a disagreement no document is having. '
             'Rebuild with scripts/extract_line_history.py.'),
            ('data/line-history-coverage.csv',
             'What the line reader could and could not read, document by document', 3,
             'One row for every document on the district\u2019s budget page, whether or '
             'not a figure came out of it, with the reason when none did \u2014 quoted '
             'from that document\u2019s own header line and its line number. It exists '
             'because the file above reports only what was read, so a document held and '
             'never parsed was indistinguishable from a document the town never '
             'published, and the coverage matrix reported both as absent. Most of the '
             'archive\u2019s budget page is in the second category. Rebuild with '
             'scripts/extract_line_history.py.'),
            ('data/total-salaries-history.csv',
             'District total salaries, budget and actual by year', 3,
             'What the district budgeted for salaries and what it spent, FY14 to FY27, '
             'read out of its own budget documents in the mirror above. Both kinds of '
             'column are kept and labelled, which is what makes a budget-versus-actual '
             'comparison possible \u2014 and no projection reads the actual columns; '
             'scripts/audit_provenance.py fails the build if one does. Rebuild with '
             'scripts/extract_budget_history.py.'),
            ('data/total-expenses-history.csv',
             'District total expenses, budget and actual by year', 3,
             'The same for non-salary expenses. Read alongside the salary series in '
             'analyses/budget-vs-actual.md, which also records where the documents '
             'disagree with themselves.'),
            ('data/sped-teacher-history.csv',
             'Special education teachers, eight budgets', 3,
             'What the district budgeted for special education teachers, FY20 to FY27, by '
             'school. Grew 2.67% a year against a 3.5% agreement — below contract, which '
             'means fewer of them each year. The largest component of the in-district '
             'escalator, and the last one to stop being taken from a contract. Rebuild '
             'with scripts/extract_budget_history.py.'),
            ('data/sped-para-history.csv',
             'Special education paraprofessionals, ten budgets', 3,
             'What the district budgeted for special education paras, FY18 to FY27, by '
             'school, read out of its own budget documents in the mirror above. Budget '
             'columns only, one budget stage held constant. The line grew 12.8% a year '
             'with an R-squared of 0.89 while the contract governing these staff gives '
             '2.0% — which is the evidence the in-district escalator rests on. Rebuild '
             'with scripts/extract_budget_history.py.'),
            ('data/sped-transport-history.csv',
             'Special education transportation, nine budgets', 2,
             'The same extraction for the special education bus line, FY19 to FY27. A '
             'much weaker trend than the paras — R-squared 0.33 — and said to be one.'),
            ('data/ood-tuition-history.csv',
             'Out-of-district tuition, eleven budgets', 3,
             'What the district budgeted for out-of-district special education tuition, '
             'FY17 to FY27, read out of its own budget documents in the mirror above. '
             'Budget columns only, and one budget stage held constant throughout — a '
             'fiscal year has several budget figures for this line at different stages '
             'and they are far apart, so a series that took whichever number each '
             'document led with would be a walk across stages rather than a trend. Three '
             'of its years reproduce the FY27 workbook exactly. Rebuild with '
             'scripts/extract_tuition_history.py.'),
            ('contracts/CONTRACTS.md', 'Research notes: union contracts', 2,
             'What each agreement pays, when it expires, how the figures were verified, and '
             'what is still missing.'),
            ('MANIFEST.md', 'Source manifest', 2,
             'The working index of every file here, with provenance and known gaps.'),
        ],
    },
]

KIND = {'.pdf': 'PDF', '.xlsx': 'Spreadsheet', '.csv': 'Data', '.md': 'Notes',
        '.docx': 'Document', '.pptx': 'Slides', '.txt': 'Text'}

# Catalogued by group above, or deliberately not a "document": extracted text mirrors its
# own source, and the meeting archive is summarized as a corpus instead.
SKIP_DIRS = {'meetings', 'contracts/txt', 'district-budget',
             'town-budget', 'town-supplementary', 'town-annual-reports', 'dese'}
SKIP_FILES = {'supplemental.csv'}


def page_count(path):
    """Pages for a PDF, rows for a spreadsheet or CSV. Best effort — a count that cannot
    be read is simply absent rather than fatal, because it is decoration, not evidence."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == '.pdf':
            import pypdf
            return len(pypdf.PdfReader(path).pages), 'pages'
        if ext == '.xlsx':
            import openpyxl
            wb = openpyxl.load_workbook(path, read_only=True)
            return max(ws.max_row for ws in wb.worksheets), 'rows'
        if ext == '.csv':
            with open(path, newline='') as fh:
                return sum(1 for _ in fh) - 1, 'rows'
        if ext == '.md':
            with open(path) as fh:
                return sum(1 for _ in fh), 'lines'
    except Exception:
        pass
    return None, None


def publish(rel):
    """Copy a source file, byte for byte, to where the site can serve it.

    Verbatim is the whole point. These are primary documents, and the reader this page
    exists for is the one who downloads ours and compares it to the town's -- so a copy
    that differs by a single byte would be a worse failure than not publishing at all.
    Returns the served size and whether it is too large for the current host.
    """
    src = os.path.join(SRC, rel)
    size = os.path.getsize(src)
    if rel in ELSEWHERE:
        # Hosted off-site. Copying it into the build as well would ship 53MB the host
        # refuses to serve, so the local copy is deliberately absent.
        return size, ELSEWHERE[rel]

    dst = os.path.join(DOCS, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    # Re-copy only when it would actually differ, so a rebuild is not 128MB of writes.
    #
    # SIZE IS NOT CONTENT. This compared getsize() alone and therefore never republished
    # a document whose edit happened to preserve its length. `budget-vs-actual.md` sat
    # stale on the site at exactly 34,380 bytes against a source of exactly 34,380 bytes,
    # publishing "24,573 readings across 31 documents" where the repository said 24,337
    # across 32. Nothing reported it, because the test could not see it.
    #
    # So size is the cheap reject and the hash is the answer. Hashing only when the sizes
    # already match keeps the rebuild fast and makes a same-length edit impossible to
    # miss -- which matters here more than most places, because rule 12 promises a reader
    # that our published copy is the bytes we hold.
    if not os.path.exists(dst) or os.path.getsize(dst) != size:
        shutil.copy2(src, dst)
    elif _sha(dst) != _sha(src):
        shutil.copy2(src, dst)
    return size, None


def _sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()




# Whether the publisher's own copy still opens.
#
# Checked by scripts/check_source_links.py and read here rather than tested during the
# build -- one request per document is slow and the answer does not change hourly.
#
# It changes what a link on the sources page MEANS. On 29 August 2026, 57 of 184 upstream
# links returned a Google sign-in wall, including the FY27 proposed budget document that
# the site's central figure comes from. A link that opens a login screen reads to a
# resident as though this project is citing something it cannot show. So a restricted
# document keeps its address, for anyone who has access, and is marked: our copy is the
# public one.
def link_status():
    path = os.path.join(SRC, 'data/link-status.csv')
    if not os.path.exists(path):
        return {}
    with open(path, newline='') as fh:
        return {r['path']: (r['public'] == '1', r['code'], r['checked'])
                for r in csv.DictReader(fh)}


LINKS = None            # populated once in main(); see link_status()


# Whether the publisher's copy is still OUR copy.
#
# The link check answers "does it open". This answers the question underneath it: if it
# opens, are the bytes the same? A Drive file can be replaced in place without its URL
# changing, and nothing in a link check would notice.
#
# Written by scripts/verify_source_copies.py. Read here rather than measured, for the same
# reason as the link status: it is one download per document.
def copy_status():
    path = os.path.join(SRC, 'data/copy-status.csv')
    if not os.path.exists(path):
        return {}
    # Best state per path. A document with two published addresses is verified if either
    # of them served it -- the question is whether our copy is the publisher's copy, and
    # one matching address answers that. The CSV keeps every row.
    rank = ['identical', 'resaved', 'reflowed', 'repackaged', 'differs', 'restricted',
            'unreachable']
    best = {}
    with open(path, newline='') as fh:
        for r in csv.DictReader(fh):
            cur = best.get(r['path'])
            if cur is None or rank.index(r['state']) < rank.index(cur):
                best[r['path']] = r['state']
    return best


COPIES = None           # populated once in main(); see copy_status()



# Rule 12: a source link must reach the FILE, not the page that lists it. An index gets
# reorganised and the document a figure rests on stops being findable from it.
#
# Checked on every build rather than trusted, because the failure is silent -- a link that
# still resolves, to a page that no longer holds what it used to.
#
# Two shapes were added on 31 August 2026. Neither is an inference from the URL's look:
# each was added only after the address was fetched and the bytes it returned matched our
# copy's sha256, which is the same standard the links themselves are held to.
#
#   AgendaCenter/ViewFile/...  the town serves meeting documents from here rather than
#                              DocumentCenter, and it is a file, not an index
#   educatorcontractsdownload  DESE returns the contract PDF itself; the org code and the
#                              contract type are both in the query string
FILE_LINK = re.compile(
    r'(/file/d/[\w-]+|open\?id=[\w-]+|/(document|spreadsheets|presentation)/d/[\w-]+'
    r'|/DocumentCenter/View/\d+|/AgendaCenter/ViewFile/\w+/_[\w-]+'
    r'|educatorcontractsdownload\.aspx\?[^\s]*orgcode='
    r'|\.(pdf|xlsx|xls|csv|docx|txt)(\?|$)'
    r'|/resource/[\w-]{9}\.|/d/[\w-]{9}$)', re.I)

# Addresses that are as deep as they go. DESE builds these reports on form submission, so
# there is no file URL to give; the page plus the parameters is the whole answer. Anything
# excused here needs a reason written beside it.
FORM_ONLY = {
    'https://profiles.doe.mass.edu/statereport/selectedpopulations.aspx':
        'DESE generates this on submission — district 01620000, one year per request. '
        'No direct file URL exists.',
    'https://dls-gw.dor.state.ma.us/gateway/dlspublic/'
    'certificationfreecashpublicreport/certificationfreecashpublic':
        'The DLS Gateway builds the free cash report on submission — jurisdiction and '
        'fiscal year chosen from dropdowns, held in session. There is no file URL. '
        'Lunenburg is 162; the eight comparison towns are all on the same list.',
    'https://profiles.doe.mass.edu/profiles/finance.aspx?orgcode=01620000&orgtypecode=5'
    '&dropDownOrgCode=2':
        'This IS the per-district page, not an index of them \u2014 the org code is in '
        'the URL and 01620000 is Lunenburg, checked against the educator-contract '
        'endpoints already verified here. DESE renders it rather than serving a file, so '
        'there is nothing deeper to link. The underlying figures are also in '
        'doe.mass.edu/research/radar/district-comparison.xlsx, which IS a file and is '
        'linked as one.',
}


def check_links(groups):
    """Warn about any source link that points at an index rather than a document."""
    bad = [(g['title'], i['title'], i['upstream'])
           for g in groups for i in g['items']
           if i.get('upstream') and not FILE_LINK.search(i['upstream'])
           and i['upstream'] not in FORM_ONLY]
    for gt, it, u in bad:
        print(f'    INDEX LINK  {it[:44]} -> {u[:60]}')
        print(f'                link the file, not the page that lists it (rule 12)')
    return len(bad)


def sha(path):
    """A file's sha256. The archive's unit of identity: two files with the same hash are
    the same document however they were named or wherever they were found."""
    m = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            m.update(chunk)
    return m.hexdigest()


# Where a primary source can be linked back to the publisher's own page.
#
# The mirrors record an upstream URL and a sha256 for every file they hold. A primary
# source that is byte-identical to one of them is the same document, so its link is
# already known and does not have to be maintained by hand -- which is the only kind of
# link that stays right.
#
# This matters more than it looks. The archive's whole claim is that a reader can check a
# figure against the document it came from, and until now the 170 documents that feed
# nothing carried a link home while the 58 that feed everything did not.

# Where a primary source came from, when we know and the mirrors do not.
#
# Most primary sources get their link by hash-matching against a mirror -- see
# upstream_by_hash. That only works for documents the mirror also holds. Anything fetched
# straight from a publisher, like the state's open-data endpoints, has no mirror row to
# match against, so its address is recorded here by hand.
#
# This is the place to add a link for any of the primary sources that still lack one. The
# blurb on the sources page counts them, so the number goes down as entries are added.
SOURCE_URLS = {
    # --- Verified against the publisher, 31 August 2026 -------------------------------
    #
    # Every link in this block but two was checked the only way a link can be: the file
    # was downloaded from it and its sha256 compared to our copy, and every one of those
    # matched to the byte. The two exceptions are the non-affiliated salary schedule and
    # benefits, which are still behind a sign-in wall; they are marked where they sit and
    # they are the only entries here given without the bytes having been matched.
    #
    # A link that merely looks right is rule 13's exact failure -- something derived quoted
    # as though it were observed -- so nothing else goes in here on the strength of a
    # matching title. `scripts/verify_source_copies.py` re-runs the comparison.
    #
    # The occasion for adding them: the district reopened its Google Drive. On 29 August
    # 2026, 57 of 187 upstream links returned a sign-in wall; on 31 August, 1 did. What
    # had been unverifiable became checkable, and 82 of the 87 mirrored district documents
    # came back byte-identical to the copies archived on 17 August. (Of the other five,
    # three are Google Docs that re-zip on export, one is the same presentation re-saved
    # under a second Drive id, and one is the 2020 hearing notice that is still walled.)

    # School employee contracts, from the district's HR page. The anchor text on that
    # page is the label; the file is what the sha matched.
    'contracts/pdf/custodial-2023-2026.pdf':
        'https://drive.google.com/file/d/1TEAfls-FpbxdztLzjlmUIuXYdO-DUcOp/view',
    'contracts/pdf/custodial-moa-2026.pdf':
        'https://drive.google.com/file/d/1sQpGjV0WqURuhcmde6C8qZkrsVoOMJCn/view',
    'contracts/pdf/paraprofessional-fy26-fy28.pdf':
        'https://drive.google.com/file/d/1RIXSUui7D-dSglzXg_yhQRrdXooNRVsc/view',
    'contracts/pdf/paraprofessional-salary-fy26-fy28.pdf':
        'https://drive.google.com/file/d/1NCXXh3kcYwWamsZu4sJkg6BKSbnJrD2J/view',
    # Posted by the district under "Non-affiliated Employees:" and still behind a Drive
    # sign-in wall on 31 August, when everything on the budget page had reopened. So the
    # address is recorded and the bytes are NOT claimed to have been checked: these two
    # are the only sources here whose link we give without having matched it. Our copies
    # were taken from these links on 20 August 2026.
    'contracts/pdf/nonaffiliated-salary-schedule.pdf':
        'https://drive.google.com/file/d/0B-TXWy9uLFrVelNCaVFfSnpXbzA/view',
    'contracts/pdf/nonaffiliated-benefits.pdf':
        'https://drive.google.com/file/d/0B-TXWy9uLFrVZlRWd0ctTjg0ZWs/view',
    # DESE publishes the contracts districts file with it. Generated per org code and
    # type, but the URL carries both, so it is a file address and not a form.
    'contracts/pdf/dese-teacher-contract.pdf':
        'https://profiles.doe.mass.edu/statereport/'
        'educatorcontractsdownload.aspx?orgcode=01620000&type=T',
    'contracts/pdf/dese-administrator-contract.pdf':
        'https://profiles.doe.mass.edu/statereport/'
        'educatorcontractsdownload.aspx?orgcode=01620000&type=A',
    'contracts/pdf/dese-superintendent-contract.pdf':
        'https://profiles.doe.mass.edu/statereport/'
        'educatorcontractsdownload.aspx?orgcode=01620000&type=S',

    # Neighboring districts. Four of the six are hosted by somebody other than the
    # district -- two content networks and two member towns' own document centres --
    # which is why none of these could be found from a district budget page.
    'peers/groton-dunstable-fy27-budget-book.pdf':
        'https://files-backend.assets.thrillshare.com/documents/asset/uploaded_file/'
        '2198/Gdrsd/a9c839f0-1ed0-4e9a-b125-32a1c58ca85d/Budget-Book-FY27-01.28.26.pdf',
    'peers/ashburnham-westminster-fy27-presentation.pdf':
        'https://files.smartsites.parentsquare.com/6739/'
        'ashburnham_westminster_budget27_presentation_1.pdf',
    'peers/ashburnham-westminster-fy27-detail.pdf':
        'https://files.smartsites.parentsquare.com/6739/fy27_budget_detail.pdf',
    'peers/ayer-shirley-fy27-expenses.pdf':
        'https://www.ayer.ma.us/DocumentCenter/View/13478',
    'peers/wachusett-fy27-budget-presentation.pdf':
        'https://www.rutlandma.gov/DocumentCenter/View/3583',
    'peers/north-middlesex-finance-subcommittee.pdf':
        'https://resources.finalsite.net/images/v1764774508/nmrsdorg/'
        'bregkjqfing6b9eyfqzz/2025-12-01-FinancePacket.pdf',

    # The town's own web server, which has never lost a link: 81 of 81 on 29 August and
    # again on 31 August.
    'town-supplementary/docs/town-2026-election-unofficial-results.pdf':
        'https://www.lunenburgma.gov/DocumentCenter/View/4193',
    'town-budget/docs/tax-classification-fy23.pdf':
        'https://www.lunenburgma.gov/DocumentCenter/View/138',
    # The town publishes this in AgendaCenter rather than DocumentCenter, and our own
    # meeting archive holds the identical file at the same address.
    'town-supplementary/docs/assessors-agenda-11-19-2025.pdf':
        'https://www.lunenburgma.gov/AgendaCenter/ViewFile/Agenda/_11192025-7512',
    # The town's own name for this file is "Health Insurance Rates July 1, 2026". Ours
    # says 2025 and is wrong; the memo inside is dated 21 April 2026 and sets the rates
    # for the plan year beginning 1 July 2026. The catalogue title has been corrected;
    # the filename is left alone because it is what every prior figure was read from.
    'town-supplementary/docs/health-insurance-rates-2025.pdf':
        'https://www.lunenburgma.gov/DocumentCenter/View/225',

    # DESE's preliminary FY27 Chapter 70 summary -- the Governor's budget figures, not a
    # final appropriation. Which matters: rule 11 turns on Chapter 70 being set in the
    # Governor's budget rather than by anything Lunenburg does.
    'budget-workbooks/ch70-fy27-summary.xlsx':
        'https://www.doe.mass.edu/finance/chapter70/fy2027/p-summary-district.xlsx',

    # The superseded athletics fee schedule, still the only one posted publicly. Hosted
    # by the schedule vendor rather than the school -- an address that outlives no
    # reorganisation, which is exactly why our copy exists.
    'district-budget/docs/lhs-athletics-faq.pdf':
        'https://tts-livesite.rschooltoday.com/sites/lunenburghs.rschoolteams.com/'
        'files/files/Private_User/jbunnell/Frequently%20Asked%20Questions.pdf',

    # --- Recorded earlier ------------------------------------------------------------
    'dese/district-spending-categories.csv':
        'https://educationtocareer.data.mass.gov/resource/er3w-dyti.csv'
        '?DIST_CODE=01620000&$limit=5000',
    # Not the portal's front door, which is an index and tells a reader nothing. This is
    # the dataset the per-pupil figures come out of; the workbook was generated from it by
    # hand on 9 March 2026, which is why the link is to the data rather than to a file.
    'budget-workbooks/dese-all-districts.xlsx':
        'https://educationtocareer.data.mass.gov/d/er3w-dyti',
}


# An address that is not a URL.
#
# Rule 12 asks for "where it came from, as deeply as it goes", and is explicit that a
# document which did not come off a website still has an address: a records request and
# its date, an email and who sent it, a meeting packet. So these are not gaps waiting for
# a link. They are the answer, in the form the answer takes.
#
# **On naming a person.** The records request in sources/munis-ledgers/account-details/
# deliberately does NOT name the resident who made it, and that is not inconsistent with
# naming somebody here. The distinction is the capacity they acted in. A private resident
# asking the town a question is not part of any address a reader needs; a member of the
# Finance Committee circulating a budget workbook is acting as a town official, and which
# official is exactly the thing that tells a reader what the document is. Where the
# capacity is private, the role goes in and the name stays out.
PROVIDED_BY = {
    'budget-workbooks/fy27-budget-projection-3-25-26.xlsx':
        'Sent directly to this project by Ana Lockwood, a member of the Lunenburg Finance '
        'Committee, under her own filename \u201cFY27 School Department Budget Projection '
        'as of 3.25.26\u201d. Not downloaded from a public page.',
}


def upstream_by_hash():
    known = {}
    for sub in ('district-budget', 'town-budget', 'town-supplementary',
            'town-annual-reports', 'dese'):
        idx = os.path.join(SRC, sub, 'index.csv')
        if not os.path.exists(idx):
            continue
        with open(idx, newline='') as fh:
            for r in csv.DictReader(fh):
                if r.get('sha256') and r.get('upstream'):
                    known[r['sha256']] = r['upstream']
    return known


def mirror_group(sub, gid, title, blurb, origin, catalogued_hashes):
    """A crawled mirror, described from its own manifest rather than by hand.

    Curating a blurb for every one of these would go stale faster than it could be
    written, and the label the publisher gave each file is the honest description.
    Anything byte-identical to a document the analysis is built on is marked, so the
    overlap between "held" and "used" is visible rather than implied.
    """
    idx = os.path.join(SRC, sub, 'index.csv')
    if not os.path.exists(idx):
        return None
    items = []
    with open(idx, newline='') as fh:
        for r in csv.DictReader(fh):
            if not r['local']:
                continue
            rel = os.path.relpath(os.path.join(ROOT, r['local']), SRC)
            size = int(r['bytes'])
            used = catalogued_hashes.get(r['sha256'])
            text_rel = (os.path.relpath(os.path.join(ROOT, r['text']), SRC)
                        if r['text'] else None)
            # Over the host's per-file cap and not worth a second home: kept in the
            # archive, named here, but not served. Said rather than silently dropped.
            oversize = size > MAX_BYTES
            if not oversize:
                publish(rel)
            if text_rel:
                publish(text_rel)
            ext = os.path.splitext(rel)[1].lower()
            items.append({
                'path': rel, 'title': r['label'], 'stars': 2 if used else 1,
                'what': (f'Also catalogued above as a source this analysis is built on '
                         f'({used}). Same file, byte for byte.' if used else
                         'Mirrored from the publisher. Not used in any figure on this site.'),
                'kind': KIND.get(ext, ext.lstrip('.').upper()),
                'bytes': size,
                'url': ('' if oversize else '/docs/' + rel),
                **({'textUrl': '/docs/' + text_rel} if text_rel else {}),
                'upstream': r['upstream'],
                **({'upstreamRestricted': True}
                   if (LINKS or {}).get(rel, (True,))[0] is False else {}),
                **({'alsoUsed': used} if used else {}),
                **({'heldOnly': True} if oversize else {}),
            })
    items.sort(key=lambda i: (-i['stars'], i['title']))
    return {'section': 'reference', 'id': gid, 'origin': origin,
            'title': title, 'blurb': blurb.format(n=len(items)), 'items': items}


def district_page_group(catalogued_hashes):
    """The district's whole budget page, mirrored.

    Eighty-seven documents going back to FY18, all of them Google Drive links on a page
    that could change tomorrow. Generated from the crawler's own manifest rather than
    described by hand -- eighty-seven curated blurbs would go stale faster than they could
    be written, and the label the district gave each file is the honest description.

    Anything byte-identical to a document we actually build on is marked, so a reader can
    see at a glance which of these are load-bearing and which are just held.
    """
    idx = os.path.join(SRC, 'district-budget', 'index.csv')
    if not os.path.exists(idx):
        return None
    items = []
    with open(idx, newline='') as fh:
        for r in csv.DictReader(fh):
            if not r['local']:
                continue
            rel = os.path.relpath(os.path.join(ROOT, r['local']), SRC)
            used = catalogued_hashes.get(r['sha256'])
            text_rel = (os.path.relpath(os.path.join(ROOT, r['text']), SRC)
                        if r['text'] else None)
            publish(rel)
            if text_rel:
                publish(text_rel)
            ext = os.path.splitext(rel)[1].lower()
            items.append({
                'path': rel, 'title': r['label'], 'stars': 2 if used else 1,
                'what': (f'Also catalogued above as the source for part of this analysis '
                         f'({used}). Same file, byte for byte.' if used else
                         'Mirrored from the district budget page. Not used in any figure '
                         'on this site.'),
                'kind': KIND.get(ext, ext.lstrip('.').upper()),
                'bytes': int(r['bytes']),
                'url': '/docs/' + rel,
                **({'textUrl': '/docs/' + text_rel} if text_rel else {}),
                'upstream': r['upstream'],
                **({'upstreamRestricted': True}
                   if (LINKS or {}).get(rel, (True,))[0] is False else {}),
                **({'alsoUsed': used} if used else {}),
            })
    items.sort(key=lambda i: (-i['stars'], i['title']))
    return {
        'section': 'reference', 'id': 'district-page', 'origin': 'school',
        'title': 'The district budget page, mirrored in full',
        'blurb': f'Every document linked from the district\u2019s budget information page '
                 f'\u2014 {len(items)} of them, back to FY18. Each row links to our copy '
                 f'and to the district\u2019s original. Text has been extracted from all '
                 f'but one, including eleven scans that had no text layer until we read '
                 f'them.',
        'items': items,
    }


def build_corpus():
    """The meeting archive, summarized. index.csv is the record of what was fetched."""
    idx = os.path.join(SRC, 'meetings', 'index.csv')
    if not os.path.exists(idx):
        return None
    boards, kinds, dates, fetched = Counter(), Counter(), [], 0
    with open(idx, newline='') as fh:
        for row in csv.DictReader(fh):
            board = row.get('board') or row.get('board_slug') or ''
            boards[board] += 1
            kinds[(row.get('kind') or '').lower()] += 1
            if (row.get('path') or '').strip():
                fetched += 1
            d = (row.get('date') or '').strip()
            if d:
                dates.append(d)
    pretty = lambda s: s.replace('-', ' ').title().replace('Pacc', 'PACC')
    return {
        'boards': [{'name': pretty(b), 'documents': n} for b, n in boards.most_common()],
        'boardCount': len(boards),
        'listed': sum(boards.values()),
        'fetched': fetched,
        'agendas': kinds.get('agenda', 0),
        'minutes': kinds.get('minutes', 0),
        'from': min(dates) if dates else None,
        'to': max(dates) if dates else None,
        'textFiles': sum(len(f) for _, _, f in os.walk(os.path.join(SRC, 'meetings', 'text'))),
        'note': 'Every agenda and set of minutes the town publishes, across all boards. The '
                'scanned originals are not committed to the repository — they run to about '
                '400MB and are re-fetchable — but the extracted text of all of them is, and '
                'that is what the analysis actually reads.',
        'rebuild': 'python3 scripts/fetch_agendas.py --from 2025 && python3 scripts/extract_minutes.py',
    }


def main():
    catalogued, groups, missing = set(), [], []

    global LINKS, COPIES
    LINKS = link_status()
    COPIES = copy_status()
    known_upstream = upstream_by_hash()

    for g in GROUPS:
        items = []
        for rel, title, stars, what in g['items']:
            path = os.path.join(SRC, rel)
            if not os.path.exists(path):
                missing.append(rel)
                continue
            catalogued.add(rel)
            ext = os.path.splitext(rel)[1].lower()
            count, unit = page_count(path)
            served, elsewhere = publish(rel)

            # Where the extracted text sits beside a document. `docs/` -> `text/` is the
            # convention every mirror uses; `pdf/` -> `txt/` was the old top-level format
            # split, kept because a few addresses still refer to it.
            txt = os.path.splitext(rel)[0] + '.txt'
            cands = (txt,
                     rel.replace('/docs/', '/text/').replace('.pdf', '.txt'),
                     rel.replace('pdf/', 'txt/').replace('.pdf', '.txt'))
            text_rel = next((t for t in cands
                             if os.path.exists(os.path.join(SRC, t))), None)
            if text_rel:
                publish(text_rel)

            by_request = any(rel.startswith(pfx) for pfx in BY_REQUEST)
            # A hand-recorded address wins: it is the endpoint we actually
            # fetched, not a copy of the same bytes found somewhere else.
            link = SOURCE_URLS.get(rel) or known_upstream.get(sha(path))
            given = PROVIDED_BY.get(rel)
            st = LINKS.get(rel)
            items.append({
                'path': rel, 'title': title, 'stars': stars, 'what': what,
                **({'byRequest': True} if by_request else {}),
                **({'upstream': link} if link else {}),
                **({'upstreamRestricted': True} if st and not st[0] else {}),
                # When the link was last tried, from the check itself rather than typed
                # into the component. The page used to say "as of 29 Aug 2026" in JSX; it
                # was still saying it after the district reopened everything on 31 August,
                # which is rule 2 in the smallest possible form.
                **({'upstreamCheckedOn': st[2]} if st and not st[0] else {}),
                **({'providedBy': given} if given else {}),
                'kind': KIND.get(ext, ext.lstrip('.').upper()),
                'bytes': served,
                'url': elsewhere or ('/docs/' + rel),
                **({'count': count, 'unit': unit} if count else {}),
                **({'textUrl': '/docs/' + text_rel} if text_rel else {}),
                # Said plainly: a reader should know when a file comes from somewhere
                # other than this site, and it is still the same bytes either way.
                **({'offsite': True} if elsewhere else {}),
            })
        # Load-bearing first, then largest — a reader scanning a group should meet the
        # documents a conclusion actually rests on before the ones kept for completeness.
        items.sort(key=lambda i: (-i['stars'], -i['bytes']))
        groups.append({**{k: v for k, v in g.items() if k != 'items'}, 'items': items})

    if missing:
        sys.exit('catalogued but not on disk:\n  ' + '\n  '.join(missing))

    # The check that keeps this honest: anything primary on disk must be described.
    uncatalogued = []
    for dirpath, dirnames, filenames in os.walk(SRC):
        rel_dir = os.path.relpath(dirpath, SRC)
        rel_dir = '' if rel_dir == '.' else rel_dir
        dirnames[:] = [d for d in dirnames
                       if os.path.join(rel_dir, d).replace(os.sep, '/') not in SKIP_DIRS]
        if rel_dir.split('/')[0] in SKIP_DIRS:
            continue
        for fn in filenames:
            rel = os.path.join(rel_dir, fn).replace(os.sep, '/')
            if fn.startswith('.') or fn in SKIP_FILES or rel in catalogued:
                continue
            if os.path.splitext(fn)[1].lower() in ('.txt',):
                continue
            uncatalogued.append(rel)
    if uncatalogued:
        sys.exit('on disk but not catalogued — describe it in GROUPS or add it to SKIP:\n  '
                 + '\n  '.join(sorted(uncatalogued)))

    # Hashes: the mirror marks its own duplicates, and a primary source finds its link.
    catalogued_hashes = {}
    for g in groups:
        for i in g['items']:
            fp = os.path.join(SRC, i['path'])
            if os.path.exists(fp):
                catalogued_hashes[sha(fp)] = i['path']
    for g in [
        district_page_group(catalogued_hashes),
        mirror_group('town-budget', 'town-budget',
                     'The town’s budget and finance documents, mirrored',
                     'Every budget-relevant document linked from the town’s finance pages '
                     '— {n} of them, including the audited financial statements and the '
                     'year-end reports. Reached by walking the budget hub, town meetings '
                     'and finances, and the finance-adjacent department pages rather than '
                     'by enumerating the document store, which would have meant thousands '
                     'of files about dog licenses.', 'town', catalogued_hashes),
        mirror_group('town-supplementary', 'town-supplementary',
                     'The town’s supplementary documents, mirrored',
                     'The other {n} documents from the same town pages: tax billing and '
                     'exemption forms, the senior work-off programme, police policies, '
                     'HR forms, grant notices and an infrastructure assessment. Split out '
                     'because a folder called budget should hold budgets — data, '
                     'spreadsheets and plans — and these are supplementary to it. '
                     'Nothing was discarded: they are mirrored on the same terms as '
                     'everything else, and several bear on the budget indirectly.',
                     'town', catalogued_hashes),
        mirror_group('town-annual-reports', 'town-annual-reports',
                     'The town’s annual reports',
                     'One report per year, {n} of them, mirrored from the town’s own '
                     'document store. Kept apart from the budget documents because they '
                     'are a retrospective series rather than a plan: each one carries '
                     'the year’s audited financial statements alongside department '
                     'narratives, vital statistics and committee reports, and the money '
                     'is a part of it rather than the point of it.',
                     'town', catalogued_hashes),
        mirror_group('dese', 'dese', 'State enrollment data',
                     'Lunenburg’s selected-population counts from the state, FY19 to FY26 '
                     '— {n} files. The count of students with disabilities is the one '
                     'quantity the budget cannot supply: special education spending is '
                     'staff numbers times contract rates, and a budget only shows the '
                     'product.', 'dese', catalogued_hashes),
    ]:
        if g and g['items']:
            groups.append(g)
            catalogued.update(i['path'] for i in g['items'])

    all_items = [i for g in groups for i in g['items']]

    # Every claim the page makes about its own composition is measured here and formatted
    # into the section blurbs below, so that adding a document cannot leave a sentence
    # describing an archive that no longer exists.
    by_request_count = sum(1 for i in all_items if i.get('byRequest'))
    # Stated rather than left to be noticed: the documents every figure rests on are the
    # ones least able to be traced back, which is the wrong way round.
    restricted = sum(1 for i in all_items if i.get('upstreamRestricted'))
    linked = sum(1 for g in groups if g['section'] == 'theirs'
                 for i in g['items'] if i.get('upstream'))
    # The remainder, counted rather than described. On 31 August 2026 this dropped from 57
    # to 16 in one pass, and the sentence that used to explain the 57 -- "gathered before
    # the mirror existed" -- had stopped being true of most of what was left. A count that
    # moves under a fixed explanation is rule 14 in miniature.
    # A document handed over by a named official has an address; it just is not a URL.
    # Counting it as unlinked would report a gap that has been closed.
    # Built as a phrase rather than a number dropped into a fixed sentence, because the
    # sentence has to read either way and there is currently exactly one of these.
    n_given = sum(1 for g in groups if g['section'] == 'theirs'
                  for i in g['items'] if i.get('providedBy'))
    given_count = (
        'one more was handed over by somebody acting in a town role, and they are named '
        'on its row' if n_given == 1 else
        f'{n_given} more were handed over by people acting in a town role, each named on '
        'the row')
    unlinked = sum(1 for g in groups if g['section'] == 'theirs'
                   for i in g['items']
                   if not i.get('upstream') and not i.get('byRequest')
                   and not i.get('providedBy'))
    # Counted, not claimed. "Repackaged", "resaved" and "reflowed" are the same document
    # arriving in a different container -- a Google Doc re-zipped on export, a PDF re-saved
    # by another producer, a text run split in a different place -- and they count as
    # verified because the content matched. "Differs" does not, and neither does a link
    # nobody has been able to fetch.
    verified = sum(1 for g in groups if g['section'] == 'theirs'
                   for i in g['items']
                   if COPIES.get(i['path']) in ('identical', 'repackaged', 'resaved',
                                                'reflowed'))
    ref_items = [i for g in groups if g['section'] == 'reference' for i in g['items']]
    ref_overlap = sum(1 for i in ref_items if i.get('alsoUsed'))
    sections = {
        k: dict(v, blurb=v['blurb'].format(
            byrequest=by_request_count, total=len(ref_items), linked=linked,
            unlinked=unlinked, verified=verified, given=given_count,
            overlap=ref_overlap, unused=len(ref_items) - ref_overlap))
        for k, v in SECTIONS.items()
    }
    # No commit stamp. Writing the current HEAD into the file guaranteed it was dirty the
    # moment it was committed, so every commit needed a follow-up commit for the stamp,
    # for ever. The generated date is enough, and a file that cannot be clean is a file
    # nobody trusts the diff of.

    # The town's own URL for all 1,383 meeting documents lives in this one file, so it is
    # the thing worth handing a reader who wants the archive rather than our summary of it.
    corpus_index = 'minutes/index.csv'
    if os.path.exists(os.path.join(SRC, corpus_index)):
        publish(corpus_index)

    doc = {
        'generated': date.today().isoformat(),
        'origins': ORIGINS,
        'sections': sections,
        'groups': groups,
        'corpus': build_corpus(),
        'corpusIndexUrl': '/docs/' + corpus_index,
        'totals': {
            'documents': len(all_items),
            'groups': len(groups),
            'bytes': sum(i['bytes'] for i in all_items),
            'loadBearing': sum(1 for i in all_items if i['stars'] == 3),
        },
        # Counts interpolated, never typed. A categorical claim about the corpus goes
        # stale exactly the way a dollar figure does, and this one already had: the page
        # said nothing was obtained by request while carrying fifteen documents that were,
        # one group of which says so in its own blurb.
        'note': f'Every document this analysis is built on. Nothing here is private or paid '
                f'for. {by_request_count} came from the Town by records request and are '
                f'marked; the rest were published by the district, the town, the state or a '
                f'neighboring district. {restricted} of them are no longer open at the '
                f'address their publisher used \u2014 checked 29 August 2026, and all but a '
                f'handful were Google Drive links that now ask for a sign-in. Our copies '
                f'stay open, and every row carries a sha256 so anyone who still has access '
                f'can check them against the originals. Where a '
                f'document was unreadable, or says something inconvenient, it is listed '
                f'anyway.',
    }

    check_links(groups)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    mb = doc['totals']['bytes'] / 1e6
    print(f"{OUT}: {doc['totals']['documents']} documents in {len(groups)} groups, {mb:.0f}MB")
    print(f"  published verbatim to {DOCS}")
    for i in all_items:
        if i.get('offsite'):
            print(f"    offsite  {i['path']} ({i['bytes']/1e6:.0f}MB) -> {i['url']}")
        elif i['bytes'] > MAX_BYTES:
            print(f"    OVERSIZE {i['path']} is {i['bytes']/1e6:.0f}MB — over the "
                  f"{MAX_BYTES/1024/1024:.0f}MiB per-file limit and has no ELSEWHERE entry")
    if doc['corpus']:
        c = doc['corpus']
        print(f"  + meeting archive: {c['fetched']} documents across {c['boardCount']} boards")


if __name__ == '__main__':
    main()
