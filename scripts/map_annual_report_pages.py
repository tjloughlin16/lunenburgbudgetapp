"""Every financial page in every annual town report, and whether anything has read it.

    python3 scripts/map_annual_report_pages.py
    python3 scripts/map_annual_report_pages.py --check

Writes `sources/data/annual-report-pages.csv`, newest report first.

WHY, IN TJ'S WORDS: *"i think we probalby need to amke sure we capture everything that
needs to be ingested from those reports then, directly in the backlog."*

The stabilization work showed the shape of the problem. A table family was worked for
weeks and a better one sat unread in the same reports -- not because anybody decided to
skip it, but because nothing anywhere said it existed. The backlog counted ROWS in
datasets that had already been built, so a table with no extractor contributed nothing to
it and was invisible by construction. A backlog that can only see work already started is
not a backlog.

This maps the other direction: from the PAGES, to what is on them, to whether any dataset
has taken anything from that page. What comes out is the real queue.

HOW A PAGE IS JUDGED READ. Most `report_*` tables carry the `page` they came from, so a
page is `read` when some dataset holds a row citing it. That is a coarse test and it is
honest about being coarse -- one row from a page marks the page read, and a table whose
bottom half was dropped still counts. It measures whether a page has been LOOKED at, not
whether it was exhausted; `verify_report_tables.py` is what measures the second thing.

WHAT `subject` IS. A guess, from the headings the page prints, and it says so. It exists
to group the queue -- twenty pages of `special-revenue` are one job, not twenty -- and
never to assert what a figure means. Where no heading survives the scan the subject is
`unknown`, which is a statement about our scan rather than about the page.

`reversed` is a page whose OCR came out upside down: its text is mirrored and no extractor
can see a figure on it at all. Those are not a reading job, they are a re-OCR job, and
mixing the two makes the queue lie about its own size.
"""
import argparse
import collections
import csv
import glob
import json

import db_freshness
import io
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_tables as T  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
OUT = os.path.join(ROOT, 'sources', 'data', 'annual-report-pages.csv')

# THE SHARED PATTERN, not a local one. This file had its own, and it required cents --
# so every page of FY2025's Town Meeting warrant, which is nothing but `$50,000` and
# `$75,000`, counted as having no figures at all and was never classified as financial.
# The town writes round sums in the warrant and cents in the ledger tables, and a script
# that knows only one habit is blind to the other.
#
# Every money pattern in this repository should be this one. See pdf_tables.py.
MONEY = T.SCANNED_MONEY
MIN_FIGURES = 15

# Ordered: the first that matches wins, so the specific sits above the general.
SUBJECTS = [
    # TREASURER'S CASH FIRST, and the order is the whole point of this list.
    #
    # Every Treasurer's Cash page lists the stabilization funds by name -- `Bartholomew
    # Stabilization Fund`, `TD BankNorth Zoning Stabilization` -- so with
    # `trust-and-stabilization` above it, every one of them matched that instead and the
    # queue said the town published four cash pages in fifteen years. It publishes one
    # almost every year: FY2011, FY2013-FY2025, found by searching the OCR for the
    # heading directly.
    #
    # The rule the ordering encodes: the more SPECIFIC heading wins. "Treasurer's Cash
    # as of 6/30/2024" names one table; "stabilization" is a word that appears on any
    # page listing a fund, including this one.
    #
    # AND THE APOSTROPHE IS NOT RELIABLE. FY2019 p44 is the same table and prints
    # `Total Treasurer Cash as of 06/30/2019` -- no `'s` -- so a pattern that required
    # one reported that year as having no cash page.
    ('treasurers-cash', r"treasurer\S{0,3}\s+cash"),
    # FY2025 p25 is headed exactly `BALANCE SHEET` and was landing in `unknown`,
    # because the pattern wanted the FY2011-FY2023 wording. The bare heading is
    # the newer one.
    #
    # AND THE PATTERN MATCHED NOTHING AT ALL FOR ANY YEAR. It was written with `\\s`
    # inside an r-string, which is a literal backslash followed by `s` -- so it wanted
    # the characters `combined\s+balance`, which no page prints. The whole subject was
    # empty: sixteen COMBINED BALANCE SHEET pages, FY2011-FY2025, one in almost every
    # report, all sitting in `unknown` while the subject that names them held zero rows.
    # A count of zero read as *the town does not print one*; it meant our regex could
    # not be matched by any text.
    #
    # `combining` is the FY2024-FY2025 wording (`Combining Balance Sheet - Enterprise
    # Funds`), and the bare `balance sheet` is anchored to nothing because the headings
    # arrive joined with ` | ` rather than as lines.
    # AND FY2019 p28 CARRIES NO HEADING AT ALL -- the banner did not survive the scan,
    # so the only words on the town's FY2019 balance sheet are the ones the statement
    # itself must print: `TOTAL ASSETS` and `LIABILITIES and FUND EQUITY`. Rule 13c:
    # the heading was missing from our OCR, not from the page.
    ('balance-sheet',
     r'combin(?:ed|ing)\s+balance\s+sheet|all\s+fund\s+types'
     r'|\bbalance\s+sheet\b|liabilities\s+and\s+fund\s+equity'
     r'|total\s+assets'),
    # AND IT SITS ABOVE THE FUND SUBJECTS, not below them. A combined balance sheet
    # lists every fund type the town has, so `DUE FROM/TO TRUST FUNDS/SRF/ENTERPRISE`
    # -- one LINE on FY2019 p28 -- filed the whole statement as a trust table. The
    # statement outranks any fund named inside it.
    # `opeb` because FY2021 heads both pages of the summary `TRUST AND OPEB FUNDS` --
    # not `trust funds` -- and page 1 of 2 carries no fund with `stabilization` in its
    # name, so only page 2 was ever classified.
    ('trust-and-stabilization',
     r'stabilization|trust\s+fund|held\s+by\s+other\s+banks|bartholomew|\bopeb\b'),
    # A REVOLVING FUND IS A SPECIAL REVENUE FUND, and the town's own table of them --
    # `Revolving Fund | FY19 Spending Limit`, voted at Town Meeting -- never uses the
    # words `special revenue` anywhere on the page.
    #
    # IT HAS TO BE THE HEADER ROW, NOT THE WORDS. A bare `revolving fund` took FY2021
    # p140 -- the omnibus budget article -- away from `appropriations`, because the
    # vote transfers $44,318.19 from the Artificial Turf Revolving Fund and says so in
    # a sentence. A fund named in prose is not a table of funds.
    ('special-revenue',
     r'special\s+revenue|revolving\s+funds?\s*\|\s*(?:fy\s*\d|department|spending)'),
    ('receivables', r'receivable'),
    ('tax-collection',
     r'collection\s+of\s+taxes|taxes\s*&\s*excise|tax\s+liens|tax\s+recap'),
    # MONTY TECH IS A DIFFERENT DISTRICT and its pages sit inside Lunenburg's report.
    # They have to be their own subject or they silently join Lunenburg's own series:
    # the assessment tables carry sixteen OTHER towns' figures, and `Net School
    # Spending` on a Monty Tech budget summary is not Lunenburg's net school spending.
    # Above `debt` because a Monty Tech budget summary prints `BONDS (Principal &
    # Interest)` and would otherwise be filed as the town's debt.
    ('regional-school',
     r'monty\s+tech|montachusett|community\s+assessments|assessment\s+history'
     r'|net\s+school\s+spending'),
    # THE DEBT SCHEDULES NAME THE BORROWING, NOT THE TABLE. Eleven pages across six
    # years print `MASS WATER POOL 5*`, `MEADOW WOODS-SEWER GENERAL OBLIGATION`,
    # `GRAND TOTAL PRINCIPAL & INTEREST` and `Total Outstanding Indebtedness` and
    # never the words `debt schedule`.
    ('debt',
     r'debt\s+(repayment|schedule|limit)|outstanding\s+debt|bonds?\s+payable'
     r'|indebtedness|general\s+obligation|mass\s+water\s+pool'
     r'|water\s+pol+ution\s+abatement|grand\s+total\s+principal'
     r'|principal\s*(?:&|and)\s*interest'),
    # THE TOWN CHANGED THE TABLE AFTER FY2023, which is why the newest two years
    # looked like they had no budget in them at all. Through FY2023 the department
    # figures are a summary section headed `GENERAL FUND APPROPRIATIONS / SUMMARY &
    # CLASSIFICATION OF ACCOUNTS`; from FY2024 they are the warrant's `FY 2025 Omnibus
    # Budget` table -- Line No. | Account | VOTED -- and the old heading appears nowhere.
    #
    # Same data, different table, different section of the report. `omnibus` is the word
    # that finds the new one, and it has to sit HERE rather than in a new subject,
    # because a reader asking what the town appropriated does not care which layout the
    # year happened to use.
    ('appropriations',
     r'appropriat|budget\s+report|expenditures?\b|omnibus\s+budget'),
    # `\bwages\b` alone, because FY2011 p98 heads its column just `WAGES`, and
    # `salary schedule` is the FY2015 grade-and-step table. Below `appropriations`
    # deliberately: a budget page full of `Payroll-Clerical` lines is an
    # appropriations page.
    ('payroll', r'gross\s+wages|\bwages\b|payroll|salar(y|ies)'),
    ('valuation', r'valuation|assessed\s+value|new\s+growth'),
    ('elections', r'election|ballot|precinct'),
    ('vital-records', r'births?\b|deaths?\b|marriages?'),
    ('officials', r'town\s+officials|appointed|elected\s+officials'),
    ('capital', r'capital\s+(project|plan|outlay)'),
    ('cultural-council', r'cultural\s+council'),
    ('enrollment', r'enrollment|mcas'),
]
SUBJECTS = [(k, re.compile(v, re.I)) for k, v in SUBJECTS]

# WHAT EACH SUBJECT WOULD BE WORTH, and WHY -- keyed to questions this project has
# already registered as unanswerable in `money-gaps.csv`, or to a page it already
# publishes. TJ: "can you classify the annual report info left to bee extract by
# importance you see? IS there anything that answers any open questions we have, or
# support anything we already report on?"
#
# The ranking is a JUDGEMENT and is written down here so it can be argued with rather
# than inferred from what somebody happened to work on next. `answers` names a registered
# gap wherever one exists, because a gap with a named remedy is a plan and one without is
# a grievance.
PRIORITY = {
    'special-revenue': (1,
        'The load-bearing one. CLAUDE.md rule 11: grants, circuit breaker, school choice, '
        'revolving funds and gifts pay for real staff and appear NOWHERE in the budget, so '
        'a line that rises because a grant ended looks identical to one that rises because '
        'the district grew. Closes the registered gaps "What any special revenue fund '
        'bought" and "Grants received in earlier years", and bears on "Which fund pays '
        'which post".'),
    'balance-sheet': (2,
        'The whole town in one statement, which this project does not have at all. Closes '
        '"What the town held town-wide at 30 June 2024 and 30 June 2025" and bears '
        'directly on "Why the Town\u2019s undesignated fund balance and DLS\u2019s free cash '
        'differ" \u2014 a discrepancy /free-cash currently records and cannot explain.'),
    'debt': (3,
        'IT HAD NO ENTRY AT ALL and fell through to 99, so 34 unread pages \u2014 the '
        'second-largest block here \u2014 were sorting below `unknown`. The reason to '
        'rank it high is one line of `model/finance.py`: `excluded_debt=2_199_352.52`, a '
        'figure TYPED INTO THE MODEL, and debt-excluded borrowing is a real component of '
        'the levy the town raises. The repayment schedules state principal and interest '
        'BY YEAR and BY BORROWING, which makes debt service the one large expense that is '
        'knowable years ahead rather than projected \u2014 rule 3\u2019s "set by '
        'contract" category, of which this project currently derives none. Two printed '
        'tables wear this label: the repayment schedule and the five-year outstanding '
        'statement; they are different grains and must not be summed together.'),
    'receivables': (3,
        'What is owed to the town and has not been collected. Thirty pages over twelve '
        'years, and nothing here measures it; it is the other half of the tax-collection '
        'picture the property-owners and tax-bill pages tell from the levy side.'),
    'trust-and-stabilization': (4,
        'The thread already being worked. Sixteen pages remain, and they are the years '
        'where the general Stabilization Fund is still missing from the series on '
        '/analysis/stabilization-funds.'),
    'tax-collection': (5,
        'Collections and liens by year. Supports the same reports as receivables and is '
        'the series behind "what the town actually took in" as against what it committed.'),
    'payroll': (6,
        'Gross wages by name already exist for fifteen years; these are the pages that '
        'extract did not reach. It bounds "Whether a budgeted position was filled" '
        'without settling it \u2014 a roster carries no FTE and no funding source.'),
    'valuation': (7,
        'Assessed value by class. /commercial-base and /property-owners are built on the '
        'state\u2019s certification of this; the town\u2019s own printing is the check on it.'),
    'capital': (8, 'Capital projects and what they cost. Bears on "Debt service by project".'),
    'regional-school': (8,
        'Monty Tech: the OTHER school district Lunenburg pays into, and a line the town '
        'budget carries as a single assessment. These pages print the assessment for '
        'every member town and twenty years of assessment history, which is the only '
        'published basis for asking whether Lunenburg\u2019s share is moving with its '
        'enrolment. It is NOT Lunenburg district money and must never be summed with it.'),
    'appropriations': (9, 'Already the largest dataset here at 4,665 rows; these are stragglers.'),
    'enrollment': (10, 'DESE publishes this directly and is the better source.'),
    'elections': (11, 'Complete at 2,012 rows; not a money question.'),
    'vital-records': (12, 'Complete; not a money question.'),
    'treasurers-cash': (13, 'Now extracted by scripts/extract_treasurers_cash.py.'),
    'cultural-council': (13,
        'Grant awards of a few hundred dollars each, published in full. Small, and '
        'complete as printed.'),
    'unknown': (14,
        'A statement about our SCAN, not about the page: the heading is what the scanner '
        'lost. These have to be looked at before they can be ranked.'),
}

# `read` IS KEPT, DERIVED, so nothing already reading this file breaks: it is yes when a
# page is proven or unproven, which is what `state == 'read'` used to mean. `proved_by`
# names the datasets whose own check closed, so a PROVEN page can be audited back to the
# identity that proved it rather than taken on the state's word.
FIELDS = ['fy', 'page', 'subject', 'priority', 'state', 'read', 'figures',
          'figures_reversed', 'read_by', 'proved_by', 'failed_by', 'refused_by',
          'heading', 'answers', 'document']


def unreversed(t):
    r = t[::-1]
    for a, b in (('S', '$'), ('E', '3'), ('Z', '2'), ('B', '8'), ("'", ',')):
        r = r.replace(a, b)
    return r


# WORDS DECIDE WHETHER A PAGE IS MIRRORED. NUMBERS CANNOT.
#
# The test used to be "more tokens look like money when reversed than look like money
# upright", and it is worthless, for a reason that is arithmetic rather than a tuning
# problem: `28,915,000` does not match the money pattern upright, because that pattern
# wants exactly two digits after the last separator — and REVERSED it is `000,519,82`,
# which does. So every figure printed in round thousands counts as evidence of
# reversal, and none of them counts as evidence against it.
#
# A debt schedule is nothing but round thousands. That is how "FIVE YEARS OUTSTANDING
# DEBT" came to be listed as mirrored in six different years while reading perfectly
# upright in the OCR — `28,915,000`, `15,000`, `31,763,200`. The queue then printed its
# heading through unreversed(), so it appeared in the backlog as `T83D GNIDNAT$TUO
# $RA3Y 3VIF` and looked exactly like the thing it was not. A derived classification
# quoted back as an observation, which is rule 13 in one line, and it sent two hours of
# re-OCR at seven reports that had nothing wrong with them.
#
# Mirrored TEXT is unambiguous in a way mirrored numbers never are: `Town` reverses to
# `nwoT`, and no page of English contains that. So look for common words, in both
# directions, and let the count decide. These nine appear on essentially every financial
# page the town prints, and a page carrying none of them either way is left `unread`
# rather than guessed at.
WORDS = ('the', 'and', 'total', 'town', 'fund', 'school', 'year', 'department', 'debt')
REVERSED_WORDS = tuple(w[::-1] for w in WORDS)


def reading_direction(texts):
    """`upright`, `reversed`, or None when the page says neither.

    Counts whole words rather than substrings: `eht` is inside nothing, but `dna` sits
    inside plenty of real tokens, and a substring test on short words finds itself.
    """
    toks = re.findall(r'[a-z]{3,}', ' '.join(texts).lower())
    fwd = sum(t in WORDS for t in toks)
    rev = sum(t in REVERSED_WORDS for t in toks)
    if fwd == rev:
        return None
    return 'reversed' if rev > fwd else 'upright'


# A PAGE IS READ WHEN SOMETHING EXTRACTED FIGURES FROM IT, and `report_` is a naming
# convention rather than a fact about a table. Ten tables carry `fy` and `page` and do not
# start with it -- `special_revenue_read`, `staff_roster_entries`, `stated_cuts`,
# `placement_counts` -- so 353 pages that had been read were counted as backlog, 50 of
# them in the one subject that looked like the largest thing left to do.
#
# THE EXCEPTION IS A CATALOGUE. `annual_report_survey` holds a row per page saying what is
# printed on it, which is how this map knows the pages exist at all. Counting it as a
# reading would mark every page in the archive read and leave a backlog of nothing --
# the same error in the other direction, and a far worse one, because an empty queue
# looks like success.
CATALOGUES = {'annual_report_survey', 'annual_report_pages', 'extraction_plan',
              'stabilization_pages'}

# A CATALOGUE DESCRIBES ITSELF, so it does not have to be listed by name. A file that
# carries a `state` column is tracking whether something has been READ; a file that
# carries `rows_published` is counting what somebody else produced. Neither is a reading.
# `stabilization-pages.csv` is the worked example and it is almost funny: it credited 59
# pages as read while its own `state` column called them `unread`, which took the trust
# and stabilization queue from 13 to 3 on paper and changed nothing in the archive.
CATALOGUE_COLUMNS = {'state', 'rows_published', 'figures_reversed'}

# AND THREE FILES THAT ARE ABOUT READING RATHER THAN A READING, each named because its
# columns do not give it away.
#
#   `ingest-benchmark.csv` records what it COST to attempt a page, so the attempt was
#   counted as the result -- including FY2017 p149, which returned no rows and refused.
#
#   `extraction-blocked.csv` is a refusals register that predates the `*-refused.csv`
#   convention and so is not caught by the name test. It holds two columns that do not foot
#   to the page's own printed total, and it was the only thing citing FY2015 p4 and FY2019
#   p44 -- so two pages were counted READ on the strength of a record that our reading of
#   them FAILED. That is the third instance of this one inversion; see read_pages().
#
#   `table-corrections.csv` is a log of cells corrected in ANOTHER dataset, not a table of
#   figures. All four of its pages are cited by `report-appropriations` anyway, so excluding
#   it moves no page -- which is the point of doing it before it does.
NOT_READINGS = {'annual-report-pages', 'ingest-benchmark', 'extraction-blocked',
                'table-corrections'}

# WHICH COLUMN HOLDS THE YEAR OF THE BOOK THE PAGE IS IN. Requiring the literal name `fy`
# made `outstanding-debt.csv` invisible: it names that column `report_fy`, so 1,038 proven
# rows across 34 pages joined to nothing and the queue went on printing `debt 34 pages
# unread` the day after the debt tables were read. A join that matches nothing looks
# exactly like data that is absent -- which CLAUDE.md names as the shape of four of the
# thirteen defects found in one day, and this is the fifth.
#
# THE ORDER MATTERS AND THE OMISSIONS ARE THE POINT. A page belongs to the report it was
# printed in. `as_of_fy` and `due_fy` are years a ROW is about -- the debt tables carry
# both, five as-of years per page and a schedule running to FY2047 -- and joining on
# either would credit pages in books that do not exist yet.
# `report_fy` FIRST, BECAUSE IT NAMES THE BOOK. A dataset may carry both, and where it
# does they mean different things: `fy` can be the year the MONEY belongs to, `report_fy`
# is always the report the page is in. Treasurer's Cash prints a prior-year column, so 36
# of its rows carry a `fy` one earlier than the document they were printed in -- and this
# join, which is (year, page), was crediting a reading on FY2020 page 44 to FY2019 page 44.
# Only `balance-sheet` and `treasurers-cash` carry both; balance-sheet's agree on all 774
# rows, so the reorder changes exactly the rows it was meant to.
YEAR_COLUMNS = ('report_fy', 'fy')

# AND WHICH COLUMN HOLDS THE PAGE. The same bug, one column over, and it hid three pages
# that had already been read: `enterprise-balance-sheet.csv` names its page `page_pdf`, so
# the balance-sheet queue went on asking for FY2019 p47, FY2020 p45 and FY2021 p47 while
# the enterprise sheet on each of them was extracted, checked and in the archive.
#
# `page_printed` IS EXCLUDED, and for the same reason `as_of_fy` is. It is the number the
# town printed in the corner of the page, which is not the page's index in the PDF -- the
# front matter is unnumbered, so the two differ by four to six depending on the year.
# Joining on it would credit the wrong page and there would be nothing to notice it by.
PAGE_COLUMNS = ('page', 'page_pdf')


# ------------------------------------------------------------ WHAT PROVES A PAGE
#
# TJ, 27 September 2026, after the count moved three times in one day: *"i think we need a
# different metric then. read and refused as separate? (refused need to be... rerun?!)"*
#
# The parenthesis is the evidence that the metric was wrong rather than merely noisy. A
# refused page must NEVER be rerun -- rerunning returns the same refusal and pays a model
# for it -- and `15 left` on the dashboard invited exactly that purchase.
#
# WHY `read` DRIFTS. `read` meant *any dataset mentions this page*. That is a property of
# our FILING, so it moves whenever a file is added or a column is renamed, in either
# direction, and it did twice on one day. It is not a property of the archive, and it
# answers a question nobody asked: a page one row was taken from and a page whose whole
# table foots to its own printed total are the same `read`.
#
# `proven` cannot drift that way. It depends on whether the page's own printed total agrees
# with our rows, which changes only when the arithmetic changes.
#
# FOUR STATES, AND EACH MAPS TO EXACTLY ONE ACTION. Only one of them costs model tokens:
#
#   PROVEN    rows tie to a total the page prints          nothing, it is done
#   UNPROVEN  rows exist, nothing proved them              write the check        (code)
#   REFUSED   an extractor reached it and wrote nothing    fix the extractor      (code)
#   UNREAD    nobody has looked                            read it                (TOKENS)
#
# HOW A PROOF IS RECOGNISED, and why it is a DECLARED registry rather than a sniff. The
# vocabulary is genuinely heterogeneous -- nine different columns across fifty-one
# datasets, because each table family states a different identity about itself -- and a
# script that guessed which column meant `proved` would be reading a position as a name,
# which is rule 13's own trap. So every dataset that cites a page is named below with the
# column that carries its verdict and the style that column is written in. `--check`
# FAILS when a page-citing dataset is missing from this table, because a new extractor
# landing silently in UNPROVEN would look like a finding about the archive.
VERDICT = 'verdict'       # a `checked` / `check failed` / `no check` column
YES = 'yes'              # a column whose affirmative value is the literal `yes`
CLOSED = 'closed'        # a column the extractor fills ONLY with an identity that closed,
                         # so any value in it is an affirmative and empty is silence
PROSE = 'prose'          # a check recorded in prose, or a confidence label of ours. It may
                         # well be a real check; a script cannot read it, so it never
                         # proves. The remedy is to record the verdict in a column, not to
                         # parse the sentence -- `none — the page states no total` and
                         # `Checked the identity ... it held exactly` sit in the same field
CONSTRUCTION = 'construction'  # the extractor publishes a row ONLY when it footed and
                               # registers the rest in `<name>-refused.csv`, so the row's
                               # existence is the verdict. Declared only where the code was
                               # read and says so
NOTHING = None           # nothing anywhere records a check on these rows

PROOF = {
    # the `report_*` family, all from extract_tables.py, all carrying `status`
    'appropriations': ('status', VERDICT),
    'capital-projects': ('status', VERDICT),
    'debt': ('status', VERDICT),
    'dept-activity': ('status', VERDICT),
    'elections': ('status', VERDICT),
    'enrollment-mcas': ('status', VERDICT),
    # `gross-wages.csv` AND `report-gross-wages.csv` share this label (`_label` strips the
    # `report-` prefix), and both now carry `status`. The dedicated extractor grades a wage
    # page on COVERAGE -- every money figure printed on it is captured and paired with a
    # name on its own printed row -- because a wage list prints no total to foot against.
    # TJ, 28 September 2026: *"yes there is no total, but that's fine. this table doesnt
    # intend to do that and print totals. that shouldnt be a blocker."*
    'gross-wages': ('status', VERDICT),
    'monty-tech': ('status', VERDICT),
    'officials': ('status', VERDICT),
    'trust-funds': ('status', VERDICT),
    'valuation': ('status', VERDICT),
    'vital-records': ('status', VERDICT),
    # bespoke extractors that record a verdict in the same words
    'annual-report-receipts': ('status', VERDICT),
    'capital-plans': ('status', VERDICT),
    'peg-access-fund': ('status', VERDICT),
    'special-revenue-funds': ('status', VERDICT),
    'valuation-by-class': ('status', VERDICT),
    'department-rosters': ('roster_check', VERDICT),
    'town-personnel': ('size_check', VERDICT),
    # a literal yes
    'debt-repayment-detail': ('column_foots', YES),
    'special-revenue-read': ('row_ties', YES),
    'trust-fund-balances': ('ledger_agrees', YES),
    # a column only ever filled with an identity that closed
    'outstanding-debt': ('identities_closed', CLOSED),
    'receivables': ('checked', CLOSED),
    'placement-counts': ('checks', CLOSED),
    'tax-collection': ('proof', CLOSED),
    'appropriations-supplement': ('proof', CLOSED),
    'stabilization-balances': ('basis', CLOSED),
    # published only when it footed; the rest are in the paired refusals file
    'balance-sheet': (None, CONSTRUCTION),
    # `revenue_history` exists only in the database and has no CSV, which is how it was
    # missed until the completeness check above named it. It is a DERIVED projection of
    # `annual_report_receipts`, selected `WHERE status='checked'`, so its WHERE clause is
    # the verdict and every row it holds is one that proved.
    'revenue-history': (None, CONSTRUCTION),
    # a check that exists and cannot be read mechanically
    'annual-report-reads': ('proved', PROSE),
    'salary-schedule': ('confirmed_by', PROSE),
    'stabilization-flows': ('confidence', PROSE),
    # THE PRINTED TOTAL IS NOT A PROOF OF ITSELF. These four hold the figure the page
    # prints, quoted, which is what the sibling dataset's rows are checked AGAINST. On its
    # own it proves nothing, and the page is proven only if the sibling says so.
    'balance-sheet-printed-totals': (None, NOTHING),
    'enterprise-balance-sheet-printed-totals': (None, NOTHING),
    'peg-access-printed-totals': (None, NOTHING),
    'special-revenue-printed-totals': (None, NOTHING),
    # NOTHING RECORDS A CHECK. Not a judgement about the reading: a statement that the
    # verdict was never written down, so the remedy is code and never tokens.
    'board-chairs': (None, NOTHING),
    'debt-repayment': (None, NOTHING),
    'department-staffing': (None, NOTHING),
    # PUBLISHED ONLY WHEN THE YEAR TIES, so the row's existence IS the verdict --
    # CONSTRUCTION, the same declaration `balance-sheet` and `treasurers-cash` carry.
    # `append_enterprise_balance_sheet_year.py` merges a staged edition into a COPY, runs
    # `verify_enterprise_balance_sheet.py` against it, and replaces the real files only if
    # every check passes; on failure it writes nothing at all. Its own docstring says why:
    # "a year that does not tie is not written down -- so the writing has to be what is
    # gated, not the reporting."
    #
    # Declared here having read that code, per the rule above. Registered as NOTHING it
    # reported FY2025 page 25 as unchecked while the verifier passed every column of it:
    # assets, liabilities and fund equity each footing to a total the town printed, on all
    # four funds, and the memorandum column equal to the four added across.
    'enterprise-balance-sheet': (None, CONSTRUCTION),
    'grants-history': (None, NOTHING),
    'peg-access': (None, NOTHING),
    'signatures': (None, NOTHING),
    'staff-roster-entries': (None, NOTHING),
    'stated-cuts': (None, NOTHING),
    'town-meeting-votes': (None, NOTHING),
    # PUBLISHED ONLY WHEN THE COLUMN FOOTS, so the row's existence IS the verdict --
    # CONSTRUCTION, not NOTHING. `extract_treasurers_cash.py` reconciles each column to the
    # total the page prints and takes NOTHING from a column that does not tie, writing the
    # failures to `extraction-blocked.csv`. Registered as NOTHING it reported 14 pages as
    # having no check anywhere, which was a statement about this registry and not about the
    # extractor. Declared here having read that code -- `kept` is appended only inside
    # `abs(got - total) <= TOL`.
    'treasurers-cash': (None, CONSTRUCTION),
    # the register of stabilization rows that did NOT foot. Its rows are real and published
    # with the reconciliation that fails; it is the definition of unproven.
    'stabilization-unfooted': (None, NOTHING),
}


def proof_verdict(style, value):
    """`proven`, `failed`, or None when the cell says neither."""
    if style is CONSTRUCTION:
        return 'proven'
    v = (value or '').strip()
    if style is VERDICT:
        if v == 'checked':
            return 'proven'
        return 'failed' if v == 'check failed' else None
    if style is YES:
        if v == 'yes':
            return 'proven'
        return 'failed' if v else None
    if style is CLOSED:
        return 'proven' if v else None
    return None


def _year_column(cols):
    """The first year-of-the-book column a table has, or None."""
    return next((c for c in YEAR_COLUMNS if c in cols), None)


def _page_column(cols):
    """The first PDF-page column a table has, or None."""
    return next((c for c in PAGE_COLUMNS if c in cols), None)


def _label(name):
    """One name per dataset. `report_appropriations` the table and
    `report-appropriations.csv` the file are the same reading, and listing both made every
    page look twice-read."""
    return re.sub(r'^report[-_]', '', name).replace('_', '-')


def read_pages():
    """Two dicts: who CITES each page, and what each citing dataset's check SAID.

    `{(fy, page): {label}}` and `{(fy, page): {label: {'proven'|'failed'}}}`. The second is
    what the four states are built from; see PROOF for why the verdict is looked up in a
    declared registry rather than sniffed out of a column name.

    BOTH THE CSVs AND THE DATABASE, and the CSVs matter more. CLAUDE.md is explicit that
    the CSVs are the source of truth and the database is a DERIVED read model rebuilt from
    scratch every run -- so a dataset that has just been written is real, and a dataset
    that has reached the database is merely one that has also been loaded.

    Reading only the database meant a new extractor's output was invisible to the backlog
    until somebody ran `build_db.py`, which is a step nobody remembers between finishing a
    reader and looking at the queue. With six extractors being written at once that gap is
    the difference between a live count and a stale one.
    """
    out = collections.defaultdict(set)
    said = collections.defaultdict(lambda: collections.defaultdict(set))
    for f in sorted(glob.glob(os.path.join(DATA, '*.csv'))):
        name = os.path.basename(f)[:-4]
        # A LEDGER ABOUT READING IS NOT A READING. `ingest-benchmark.csv` records what it
        # cost to attempt a page and carries `fy` and `page`, so the map counted the
        # attempt as the result -- including FY2017 p149, which returned no rows and
        # refused. That moves the number without moving the archive, which is the one
        # thing this count must never do.
        if name.replace('-', '_') in CATALOGUES or name in NOT_READINGS:
            continue
        # A REFUSAL IS NEVER A READING, AND THE COLUMN TEST WAS NOT ENOUGH.
        #
        # The rule below says a catalogue describes itself, by carrying a `state` column.
        # Four of the eight `*-refused.csv` files do not carry one -- debt-repayment-detail,
        # gross-wages, report-appropriations-supplement, salary-schedule -- so each of them
        # was CREDITING the pages it refused. Recording that an extractor could not read a
        # page marked the page read, which is the precise inversion this count must never
        # make, and it was invisible until a run added 22 refusal rows and the read count
        # went UP by two.
        #
        # Self-description is the right idea and it cannot be the only guard, because it
        # fails silently for the file that forgets. The name is a second, independent test:
        # anything called `<something>-refused` is a record of failure whatever columns it
        # happens to have.
        if name.endswith('-refused'):
            continue
        try:
            with open(f, encoding='utf-8', errors='replace') as fh:
                r = csv.DictReader(fh)
                cols = set(r.fieldnames or ())
                year, page = _year_column(cols), _page_column(cols)
                if not year or not page or cols & CATALOGUE_COLUMNS:
                    continue
                lab = _label(name)
                col, style = PROOF.get(lab, (None, NOTHING))
                for row in r:
                    try:
                        key = (int(row[year]), int(row[page]))
                    except (TypeError, ValueError):
                        continue
                    out[key].add(lab)
                    v = proof_verdict(style, row.get(col) if col else None)
                    if v:
                        said[key][lab].add(v)
        except OSError:
            continue
    if not os.path.exists(DB):
        return out, said
    db = sqlite3.connect('file:%s?mode=ro' % DB, uri=True)
    try:
        for (t,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            if t in CATALOGUES or t.replace('_', '-') in NOT_READINGS:
                continue
            cols = {r[1] for r in db.execute('PRAGMA table_info("%s")' % t)}
            # THE SAME CATALOGUE TEST AS THE CSV HALF, which this branch did not apply.
            # `capital_plans_refused` is loaded by `build_db.py` and is not in the named
            # `CATALOGUES` set, so a table whose every row says a page REFUSED was
            # crediting those pages as read -- FY2013 p12 came out `read_by=
            # capital-plans-refused`, a page nothing holds a figure for. A refusal is not
            # a reading, and keeping the test in one half of a two-half join is how it
            # stopped being true in the other.
            # The same name test as the CSV half, for the same reason: keeping a guard
            # in one half of a two-half join is how it stopped being true in the other,
            # which this function's own comment above already records happening once.
            if t.endswith('_refused'):
                continue
            year, page = _year_column(cols), _page_column(cols)
            if not year or not page or cols & CATALOGUE_COLUMNS:
                continue
            lab = _label(t)
            col, style = PROOF.get(lab, (None, NOTHING))
            sel = '"%s", "%s"' % (year, page)
            if col and col in cols:
                sel += ', "%s"' % col
            for r in db.execute('SELECT DISTINCT %s FROM "%s"' % (sel, t)):
                try:
                    key = (int(r[0]), int(r[1]))
                except (TypeError, ValueError):
                    continue
                out[key].add(lab)
                v = proof_verdict(style, r[2] if len(r) > 2 else None)
                if v:
                    said[key][lab].add(v)
    finally:
        db.close()
    return out, said


def refusals():
    """Pages an extractor READ and then refused, and who refused them.

    A THIRD STATE, because `unread` was carrying two facts that need different work.
    Ten receivables pages sat in the queue as `unread` after their rows were deleted for
    not summing to the totals the pages themselves print. Nobody had to go and read those
    pages: somebody had, and the reading failed. Calling that `unread` loses the most
    useful thing known about them -- that the page is legible, an extractor exists, and
    what is wrong is the extractor -- and it reads to anybody looking at the queue as work
    nobody has started.

    Two sources, both already written and neither previously consulted here:
      * `sources/data/*-refused.csv` -- the convention seven extractors already follow,
        one row per page with the printed total it could not close and the reason.
      * `sources/data/annual-report-reads/*.json` -- a model reading that returned no rows
        and said why in `note`. A refusal is a correct answer and is not written as data,
        so nothing else records that the page was looked at.
    """
    out = collections.defaultdict(set)
    files = sorted(glob.glob(os.path.join(DATA, '*-refused.csv')))
    # `extraction-blocked.csv` predates the `*-refused` naming and records the same thing:
    # a column that would not foot to the total its own page prints.
    files.append(os.path.join(DATA, 'extraction-blocked.csv'))
    for f in files:
        name = _label(os.path.basename(f)[:-4])
        try:
            with open(f, encoding='utf-8', errors='replace') as fh:
                r = csv.DictReader(fh)
                cols = set(r.fieldnames or ())
                year, page = _year_column(cols), _page_column(cols)
                if not year or not page:
                    continue
                for row in r:
                    try:
                        out[(int(row[year]), int(row[page]))].add(name)
                    except (TypeError, ValueError):
                        continue
        except OSError:
            continue
    for f in sorted(glob.glob(os.path.join(DATA, 'annual-report-reads', '*.json'))):
        try:
            with open(f, encoding='utf-8') as fh:
                d = json.load(fh)
            if not (d.get('rows') or []):
                out[(int(d['fy']), int(d['page']))].add('read-and-refused')
        except (OSError, ValueError, KeyError):
            continue
    return out


def subject_of(texts, whole_page=()):
    """The headings first; the WHOLE PAGE only if the headings said nothing.

    THE BANNER IS NOT THE TABLE. Forty-seven pages were `unknown` and forty-five of
    them named themselves perfectly well -- three inches further down. The town heads a
    balance sheet `TOWN OF LUNENBURG, MASSACHUSETTS`, a debt schedule `FISCAL YEAR`,
    and its bank-by-bank cash listing with an account number the scanner read as
    `0037140404`. Reading only the top ten boxes and then reporting the result as
    `unknown` is rule 13c in one line: a matcher found nothing and the finding was
    written down as a fact about the town.

    The fallback is deliberately SECOND rather than merged. Classifying on the whole
    page would change what every already-classified page is called -- any page
    mentioning `appropriated` anywhere would move -- so this can only ever turn
    `unknown` into something, and never move a page between two named subjects.
    """
    for texts in (texts, whole_page):
        joined = ' | '.join(texts)
        for name, pat in SUBJECTS:
            if pat.search(joined):
                return name
    return 'unknown'



# A PAGE THE REPORT PRINTS TWICE IS NOT TWO PAGES OF WORK.
#
# FY2017 prints its omnibus budget at pp168-169 and AGAIN, as a two-column reprint, inside
# the Article 8 warrant text at pp156-158. `extraction-plan.csv` says so in as many words --
# "USE THE p168-169 VERSION, not the p156-158 one" -- and until 28 September 2026 the plan
# parser scraped BOTH ranges out of that sentence and read the reprint too, which
# reconciled at -$7,922,127.08 and was reported for days as FY2017 being broken.
#
# Fixing the parser made those three pages stop being read, so this map called them
# `unread` -- work nobody has started -- and the unfinished count went UP by two in
# response to a correct fix. That is the counter punishing progress, and it is the third
# time in one day it has done so.
#
# They are not unread. They are a second printing of a table this archive reads properly at
# its other location, and counting them makes one table look like two. Recorded here with
# WHERE the real reading is, so the claim is checkable rather than a quiet exclusion.
REPRINTS = {
    (2017, 156): 'a two-column reprint of the omnibus budget read at FY2017 pp168-169',
    (2017, 157): 'a two-column reprint of the omnibus budget read at FY2017 pp168-169',
    (2017, 158): 'a two-column reprint of the omnibus budget read at FY2017 pp168-169',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    done, said = read_pages()
    refused = refusals()
    rows = []
    for f in sorted(glob.glob(os.path.join(OCR, '*annual-town-report.tsv'))):
        m = re.search(r'fy-(\d{4})-', f)
        if not m:
            continue
        fy = int(m.group(1))
        doc = os.path.relpath(f, ROOT)
        by_page = collections.defaultdict(list)
        for b in T.read_boxes(f):
            by_page[b['page']].append(b)
        for page, boxes in sorted(by_page.items()):
            if (fy, page) in REPRINTS:
                continue
            figs = rev = 0
            for b in boxes:
                t = (b['text'] or '').strip()
                if not t:
                    continue
                if MONEY.match(t):
                    figs += 1
                elif MONEY.match(unreversed(t)):
                    rev += 1
            if figs + rev < MIN_FIGURES:
                continue
            top = [' '.join((b['text'] or '').split())
                   for b in sorted(boxes, key=lambda b: -b['y'])[:10]]
            top = [t for t in top if len(t) > 6 and not MONEY.match(t)]
            # THE WORDS DECIDE, and only where they actually speak. `figures_reversed`
            # is still recorded because it is a real count, but it no longer classifies
            # anything: see reading_direction() for why a round-thousands table made it
            # say `reversed` about six perfectly upright debt schedules.
            direction = reading_direction(
                [' '.join((b['text'] or '').split()) for b in boxes])
            if direction == 'reversed':
                # Nothing on a mirrored page can be classified; its headings are as
                # mangled as its figures. Read them the other way round.
                top = [unreversed(t) for t in top]
            hits = done.get((fy, page), set())
            # PROVEN NEEDS A CLEAN READING, NOT A LUCKY ROW. A dataset proves this page
            # when its own check closed here AND nothing it read here failed. Taking `any
            # row passed` would call report_appropriations proven on pages where 4,870 rows
            # failed beside 157 that passed, which is the exact aggregation CLAUDE.md
            # forbids without splitting on `status`.
            verdicts = said.get((fy, page), {})
            proved = sorted(l for l, v in verdicts.items()
                            if 'proven' in v and 'failed' not in v)
            failed = sorted(l for l, v in verdicts.items() if 'failed' in v)
            # THE ORDER IS THE POINT, because each state is one action and they are not
            # interchangeable. `proven` outranks everything; a page with rows is `unproven`
            # however loudly something else refused part of it, because the rows are there
            # and what is missing is the check; `reversed` before `refused` because a
            # mirrored page is a re-OCR job rather than an extractor job; and `unread` is
            # last and is the ONLY one that costs model tokens.
            if proved:
                state = 'proven'
            elif hits:
                state = 'unproven'
            elif direction == 'reversed':
                state = 'reversed'
            elif (fy, page) in refused:
                state = 'refused'
            else:
                state = 'unread'
            page_text = [' '.join((b['text'] or '').split()) for b in boxes]
            if direction == 'reversed':
                page_text = [unreversed(t) for t in page_text]
            subj = subject_of(top, page_text)
            pri, why = PRIORITY.get(subj, (99, ''))
            rows.append(dict(
                fy=fy, page=page, subject=subj, priority=pri, answers=why, state=state,
                read=('yes' if hits else 'no'),
                figures=figs, figures_reversed=rev,
                read_by=', '.join(sorted(hits)),
                proved_by=', '.join(proved), failed_by=', '.join(failed),
                # WHO REFUSED IT, because `build_extraction_gaps.py` has to name the
                # extractor to be fixed and a gap with no named remedy is a grievance.
                refused_by=', '.join(sorted(refused.get((fy, page), ()))),
                heading=(top[0] if top else '')[:60], document=doc))

    # PRIORITY FIRST, then newest. The queue is meant to be read top-down.
    rows.sort(key=lambda r: (r['priority'], -r['fy'], r['page']))
    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    wr.writeheader()
    wr.writerows(rows)
    text = buf.getvalue()

    # A DATASET MISSING FROM `PROOF` IS A DEFECT, NOT AN UNPROVEN PAGE. A new extractor
    # whose verdict column nothing knows about would put its pages in UNPROVEN and read as
    # a finding about the archive -- the silent-zero shape CLAUDE.md names as four of
    # thirteen defects in one day. So it is named and it fails, in the run as well as in
    # `--check`, because a build that only fails under `--check` fails for nobody.
    missing = sorted({l for labs in done.values() for l in labs} - set(PROOF))
    if missing:
        print('UNDECLARED: %d dataset(s) cite a page and are not in PROOF in %s:\n    %s\n'
              'Add each with the column carrying its verdict, or (None, NOTHING) if it '
              'records none.' % (len(missing), os.path.basename(__file__),
                                 '\n    '.join(missing)), file=sys.stderr)
        return 1

    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if cur != text:
            print('STALE %s -- run: python3 scripts/map_annual_report_pages.py'
                  % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('ok -- %d financial pages mapped across %d reports'
              % (len(rows), len({r['fy'] for r in rows})))
        return 0

    # A COUNT PARTLY DERIVED FROM THE DATABASE MAY NOT BE PUBLISHED WHILE THE DATABASE
    # DISAGREES WITH ITS OWN INPUTS. `read_by()` credits a page when a CSV *or* a table in
    # lunenburg.db cites its fy and page, and on 27 September 2026 the database still held
    # 342 receivables rows that had already been deleted for not proving -- so this file
    # said `469 read, 5 left` when 459 and 15 were true, for four days, and a person found
    # it rather than a check.
    db_freshness.require_fresh(what='the annual-report page queue')

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(text)
    st = collections.Counter(r['state'] for r in rows)
    print('wrote %s -- %d financial pages across %d reports'
          % (os.path.relpath(OUT, ROOT), len(rows), len({r['fy'] for r in rows})))
    # UNITS, because these get quoted. `459 done` says nothing about what was counted
    # or what `done` means, and the queue published `469 read` off a stale database for
    # four days without anybody being able to see what the number was about.
    # FOUR STATES, EACH WITH THE ONE ACTION IT ASKS FOR, and the only one that costs
    # model tokens said out loud. `445 read, 29 refused` invited a purchase that does not
    # exist: UNREAD is what spend moves, and on this stream it is zero.
    print('  %d of %d PROVEN    rows tie to a total the page prints -- done'
          % (st['proven'], len(rows)))
    print('  %d of %d UNPROVEN  rows exist, nothing proved them -- write the check (code)'
          % (st['unproven'], len(rows)))
    print('  %d of %d REFUSED   an extractor reached it and wrote nothing -- fix the '
          'extractor (code)' % (st['refused'], len(rows)))
    print('  %d of %d UNREAD    nobody has looked -- read it (THE ONLY ONE THAT COSTS '
          'TOKENS)' % (st['unread'], len(rows)))
    print('  %d of %d reversed  the OCR came out mirrored -- re-OCR the page'
          % (st['reversed'], len(rows)))
    print('  %d of %d read, DERIVED = proven + unproven, kept so older readers of this '
          'file still work' % (st['proven'] + st['unproven'], len(rows)))
    print()
    print('  what is not proven, by subject:')
    todo = collections.Counter(r['subject'] for r in rows if r['state'] != 'proven')
    for s, n in sorted(todo.items(), key=lambda kv: PRIORITY.get(kv[0], (99,))[0]):
        yrs = sorted({r['fy'] for r in rows
                      if r['subject'] == s and r['state'] != 'proven'})
        print('    %2d. %-24s %3d pages  FY%d-FY%d'
              % (PRIORITY.get(s, (99,))[0], s, n, yrs[0], yrs[-1]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
