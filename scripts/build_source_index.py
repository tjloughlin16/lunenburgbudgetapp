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
    {'id': 'peers', 'name': 'Neighboring districts', 'url': None},
    {'id': 'request', 'name': 'Obtained from the Town by records request', 'url': None},
    {'id': 'us', 'name': 'Built by this project', 'url': None},
]

# Which documents came to us because somebody asked for them, rather than because they
# were posted. Worth marking for two reasons: it is the honest answer to "is all of this
# public", and a reader who wants these for themselves needs to know the route is a
# request rather than a link.
BY_REQUEST = {'q3-fy26/', 'xlsx/school-funds-fy26.xlsx'}

# Two halves, and the divide matters more than any grouping inside them. Everything above
# the line was published by the town, the district, the state or a neighboring district.
# Everything below it we made. A reader who cannot tell those apart cannot judge either.
SECTIONS = {
    'theirs': dict(
        title='Published by the town, the district and the state',
        blurb='Primary documents. We did not write any of these and we did not commission '
              'them. {byrequest} came from the Town by records request and say so on their '
              'row; the rest were already public. Where a document is unreadable or says '
              'something inconvenient, it is here anyway.'),
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
GROUPS = [
    {
        'section': 'theirs', 'id': 'district-budget', 'origin': 'school',
        'title': 'The district budget, line by line',
        'blurb': 'The FY27 budget in every published version. Nearly every figure in this '
                 'analysis traces to one of these five documents.',
        'items': [
            ('xlsx/fy27-proposals.xlsx', 'FY27 budget workbook, 25 March 2026', 3,
             'The richest single document here. 1,197 rows: FY23–FY25 actuals, FY26 final '
             'budget plus actuals-to-date and encumbrances, and all four FY27 scenarios. '
             'Every budget-line figure on this site comes from this workbook.'),
            ('xlsx/fy27-budget-projection-3-25-26.xlsx', 'The same workbook, as circulated to the Finance Committee', 2,
             'Data-identical to the file above across every budget column; the differences '
             'are an unused scratch column and one ratio row. Kept so anyone working from '
             'the Finance Committee copy can confirm they match.'),
            ('xlsx/fy27-budget-projection-2-24-26.xlsx', 'Earlier budget workbook, 24 February 2026', 1,
             'The 24 February version, before the restoration list was revised. Useful only '
             'for tracking what changed between drafts.'),
            ('pdf/fy27-final-budget-doc.pdf', 'FY27 proposed budget document, 25 March 2026', 3,
             'The printed line-item budget: FY26 final against the Restoration, Core and '
             'Balanced scenarios. 351 line items.'),
            ('pdf/fy27-projections-3-23-26.pdf', 'FY27 line-item projections, 23 March 2026', 3,
             'The version that carries the Level Service column, so all five scenarios sit '
             'side by side. This is the document that settles what "level service" cost.'),
            ('pdf/fy27-projections-3-16-26.pdf', 'FY27 line-item projections, 16 March 2026', 1,
             'An earlier draft with the restoration figures still in.'),
            ('pdf/fy27-multi-scenario-addendum.pdf', 'Multi-Scenario Financial Analysis', 3,
             'The narrative behind the four scenarios: what each one is, the cut and '
             'restoration lists, headcounts, impact statements, and the comparative '
             'summary. The source of every FTE count quoted here.'),
            ('pdf/town-additional-revenue-plan.pdf', 'Additional Town Revenue Spending Plan', 3,
             'The $453,722 of positions added back at the September 2026 Special Town '
             'Meeting, with the district’s reasoning for each.'),
            ('pdf/fy27-balanced-slides-3-23-26.pdf', 'Balanced budget slide deck, 23 March 2026', 1,
             'Presented to the School Committee. Image-only — no text layer, so nothing '
             'in it could be quoted or checked.'),
            ('pdf/fy27-sc-slidedeck-3-23-26.pdf', 'School Committee deck, 23 March 2026', 1,
             'Also image-only, and also unreadable without optical character recognition.'),
        ],
    },
    {
        'section': 'theirs', 'id': 'town-budget', 'origin': 'town',
        'title': 'Town budget, revenue and the override',
        'blurb': 'How much money the town has, where the Proposition 2½ formula puts the '
                 'ceiling, and what happened at the ballot in May 2026.',
        'items': [
            ('pdf/town-fy27-budget-press-release.pdf', 'Town Manager’s FY27 budget release, 17 April 2026', 3,
             'The revenue formula in full — levy limit, new growth, excluded debt, state '
             'aid, local receipts — plus all three budget scenarios by category, the cut '
             'lists and the tax impact per household. The backbone of the revenue model.'),
            ('pdf/town-2026-election-unofficial-results.pdf', 'Election results, 16 May 2026', 3,
             'Both override questions defeated roughly two to one, in every precinct. '
             'Precinct-by-precinct tallies.'),
            ('pdf/town-fy27-operating-budgets-balanced-tier1-tier2.pdf', 'Operating budgets: Balanced, Tier 1, Tier 2', 3,
             'The omnibus by department under all three funding scenarios — what each '
             'override tier would have bought, department by department.'),
            ('pdf/town-fy27-detailed-budget.pdf', 'Detailed town budget by line', 2,
             'Line-item town budget by organization and object code, including the Monty '
             'Tech assessment.'),
            ('pdf/town-atm-2026-booklet-warrant.pdf', 'Annual Town Meeting booklet and warrant, 2026', 2,
             'The full 52-page warrant, including the revolving fund authorisations under '
             'Article 6.'),
            ('pdf/town-2026-election-warrant.pdf', 'Ballot question language', 1,
             'The exact wording voters saw for both override questions.'),
            ('pdf/town-article13-fy27-capital-plan.pdf', 'FY27 capital plan, Article 13', 1,
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
            ('q3-fy26/town-special-revenue-fy26-q3.xlsx', 'Special revenue funds, 31 March 2026', 3,
             'Every special revenue and revolving fund the town holds, with opening balance, '
             'receipts, spending and closing balance. Includes the special education circuit '
             'breaker account, which appears in no budget document.'),
            ('q3-fy26/town-trust-agency-fy26-q3.xlsx', 'Trust, agency and stabilization funds, 31 March 2026', 3,
             'All stabilization and trust fund balances — general stabilization, OPEB, '
             'vehicle and equipment, conservation, and the rest.'),
            ('q3-fy26/fincom-memo-fy26-q3.docx', 'Finance Director’s memo to the Finance Committee', 3,
             'The covering memo, dated 11 August 2026. Reports revenue and expenditure '
             'against budget, and gives the finance department’s own account of why '
             'quarterly reporting had lapsed.'),
            ('q3-fy26/town-general-fund-revenue-fy26-q3.pdf', 'General fund revenue, 31 March 2026', 2,
             'Revenue collected against budget by account. Local receipts came in at 116% '
             'of budget.'),
            ('q3-fy26/town-general-fund-expenditures-fy26-q3.pdf', 'General fund expenditures, 31 March 2026', 2,
             'Spending against budget by department, including the school department line.'),
            ('q3-fy26/fincom-deck-fy26-q3.pptx', 'Finance Committee presentation, 13 August 2026', 1,
             'The slides that accompanied the memo.'),
            ('q3-fy26/ef-sewer-revenue-fy26-q3.pdf', 'Sewer enterprise fund — revenue', 1,
             'Enterprise funds are self-supporting and separate from the general fund. '
             'Included for completeness.'),
            ('q3-fy26/ef-sewer-expenditures-fy26-q3.pdf', 'Sewer enterprise fund — expenditures', 1,
             'Self-supporting; does not bear on the school budget.'),
            ('q3-fy26/ef-water-revenue-fy26-q3.pdf', 'Water enterprise fund — revenue', 1,
             'Self-supporting; does not bear on the school budget.'),
            ('q3-fy26/ef-water-expenditures-fy26-q3.pdf', 'Water enterprise fund — expenditures', 1,
             'Self-supporting; does not bear on the school budget.'),
            ('q3-fy26/ef-solid-waste-revenue-fy26-q3.pdf', 'Solid waste enterprise fund — revenue', 1,
             'Self-supporting; does not bear on the school budget.'),
            ('q3-fy26/ef-solid-waste-expenditures-fy26-q3.pdf', 'Solid waste enterprise fund — expenditures', 1,
             'Self-supporting; does not bear on the school budget.'),
            ('q3-fy26/ef-peg-access-revenue-fy26-q3.pdf', 'Cable and broadband enterprise fund — revenue', 1,
             'Self-supporting; does not bear on the school budget.'),
            ('q3-fy26/ef-peg-access-expenditures-fy26-q3.pdf', 'Cable and broadband enterprise fund — expenditures', 1,
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
            ('xlsx/school-funds-fy26.xlsx', 'School gift, athletics and choice funds, FY26 year-end', 3,
             'Full-year reconciliation of three funds: opening balance, revenue by source, '
             'spending by category, closing balance. The only place actual athletics fee '
             'collections appear — $188,944 in FY26.'),
        ],
    },
    {
        'section': 'theirs', 'id': 'tax-base', 'origin': 'town',
        'title': 'Tax base, Chapter 70 and peers',
        'blurb': 'Where the town’s money comes from, what the state contributes, and how '
                 'Lunenburg’s spending compares to its neighbors.',
        'items': [
            ('pdf/tax-classification-fy23.pdf', 'Tax Classification Hearing, FY2023', 3,
             'The single most valuable town document found. Carries year-by-year new growth '
             'FY18–FY23, assessed value by class, average single-family bills back to '
             'FY19, and excess levy capacity — series that appear nowhere else.'),
            ('xlsx/ch70-fy27-summary.xlsx', 'DESE Chapter 70 summary, FY27', 3,
             'Foundation enrollment, foundation budget, required local contribution, Chapter '
             '70 aid and required net school spending, for every district in the state.'),
            ('xlsx/dese-all-districts.xlsx', 'DESE per-pupil expenditures, FY2018–FY2024', 3,
             'Spending by category and per pupil, Lunenburg against eleven peer districts, '
             'with enrollment. Note: this is in-district expenditure, which by DESE’s '
             'definition excludes out-of-district tuition.'),
            ('pdf/town-revenue-prop25-presentation.pdf', 'Finance Committee deck on Proposition 2½', 2,
             'Levy ceiling against levy limit against actual levy, and the state analysis '
             'showing assessed value outpacing the levy since 2017.'),
            ('pdf/assessors-agenda-11-19-2025.pdf', 'Board of Assessors agenda, 19 November 2025', 1,
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
            ('pdf/health-insurance-rates-2025.pdf', 'Health insurance rates, 2025', 3,
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
            ('pdf/athletic-program-costs-by-sport.pdf', 'Athletic program costs by sport', 3,
             'Cost and participation for all 25 sports. The basis for every fee calculation '
             'on this site.'),
            ('pdf/lhs-athletics-faq.pdf', 'High school athletics fee schedule', 2,
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
            ('business/merged_dataset.csv', 'Business certificate records', 2,
             '711 records — certificate number, dates, name, owner, address, status and '
             'renewal chain. Note these are sole proprietor and partnership filings only; '
             'corporations register with the state and are not here.'),
            ('business/categorized.csv', 'Business records by industry', 2,
             '554 records tagged by industry category, which is what shows that most new '
             'registrations are at residential addresses.'),
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
            ('analyses/budget-vs-actual.md', 'Budget versus actual', 2,
             'Did what the town budgeted match what it spent? Written for two readers \u2014 '
             'plain terms and the evidence, side by side. Deliberately separate from the '
             'app\u2019s projection, and it says why. Unfinished: it names what it cannot '
             'see without the town\u2019s accounting records.'),
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
            ('data/sped-teacher-history.csv',
             'Special education teachers, eight budgets', 3,
             'What the district budgeted for special education teachers, FY20 to FY27, by '
             'school. Grew 2.67% a year against a 3.5% agreement — below contract, which '
             'means fewer of them each year. The largest component of the in-district '
             'escalator, and the last one to stop being taken from a contract. Rebuild '
             'with scripts/extract_budget_history.py.'),
            ('data/sped-para-history.csv',
             'Special education paraprofessionals, ten budgets', 3,
             'What the district budgeted for special education aides, FY18 to FY27, by '
             'school, read out of its own budget documents in the mirror above. Budget '
             'columns only, one budget stage held constant. The line grew 12.8% a year '
             'with an R-squared of 0.89 while the contract governing these staff gives '
             '2.0% — which is the evidence the in-district escalator rests on. Rebuild '
             'with scripts/extract_budget_history.py.'),
            ('data/sped-transport-history.csv',
             'Special education transportation, nine budgets', 2,
             'The same extraction for the special education bus line, FY19 to FY27. A '
             'much weaker trend than the aides — R-squared 0.33 — and said to be one.'),
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
SKIP_DIRS = {'minutes', 'txt', 'contracts/txt', 'district-budget-page',
             'town-site', 'dese'}
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
    if not os.path.exists(dst) or os.path.getsize(dst) != size:
        shutil.copy2(src, dst)
    return size, None


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
    idx = os.path.join(SRC, 'district-budget-page', 'index.csv')
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
    idx = os.path.join(SRC, 'minutes', 'index.csv')
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
        'textFiles': sum(len(f) for _, _, f in os.walk(os.path.join(SRC, 'minutes', 'text'))),
        'note': 'Every agenda and set of minutes the town publishes, across all boards. The '
                'scanned originals are not committed to the repository — they run to about '
                '400MB and are re-fetchable — but the extracted text of all of them is, and '
                'that is what the analysis actually reads.',
        'rebuild': 'python3 scripts/fetch_agendas.py --from 2025 && python3 scripts/extract_minutes.py',
    }


def main():
    catalogued, groups, missing = set(), [], []

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

            txt = os.path.splitext(rel)[0] + '.txt'
            txt_alt = rel.replace('pdf/', 'txt/').replace('.pdf', '.txt')
            text_rel = next((t for t in (txt, txt_alt)
                             if os.path.exists(os.path.join(SRC, t))), None)
            if text_rel:
                publish(text_rel)

            by_request = any(rel.startswith(pfx) for pfx in BY_REQUEST)
            items.append({
                'path': rel, 'title': title, 'stars': stars, 'what': what,
                **({'byRequest': True} if by_request else {}),
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

    # Hash what we already build on, so the mirror can mark its own duplicates.
    import hashlib

    def sha(path):
        m = hashlib.sha256()
        with open(path, 'rb') as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b''):
                m.update(chunk)
        return m.hexdigest()

    catalogued_hashes = {}
    for g in groups:
        for i in g['items']:
            fp = os.path.join(SRC, i['path'])
            if os.path.exists(fp):
                catalogued_hashes[sha(fp)] = i['path']
    for g in [
        district_page_group(catalogued_hashes),
        mirror_group('town-site', 'town-site',
                     'The town’s budget and finance documents, mirrored',
                     'Every budget-relevant document linked from the town’s finance pages '
                     '— {n} of them, including the audited financial statements and the '
                     'year-end reports. Reached by walking the budget hub, town meetings '
                     'and finances, and the finance-adjacent department pages rather than '
                     'by enumerating the document store, which would have meant thousands '
                     'of files about dog licenses.', 'town', catalogued_hashes),
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
    ref_items = [i for g in groups if g['section'] == 'reference' for i in g['items']]
    ref_overlap = sum(1 for i in ref_items if i.get('alsoUsed'))
    sections = {
        k: dict(v, blurb=v['blurb'].format(
            byrequest=by_request_count, total=len(ref_items),
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
                f'neighboring district, and can be found again at the links above. Where a '
                f'document was unreadable, or says something inconvenient, it is listed '
                f'anyway.',
    }

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
