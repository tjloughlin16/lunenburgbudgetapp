#!/usr/bin/env python3
"""School transportation: what the buses cost, what pays for them, and what the contract fixes.

    python3 scripts/build_transportation.py           # write the payload, the markdown, the charts
    python3 scripts/build_transportation.py --check   # fail if any output no longer reproduces

THE QUESTIONS, TJ's, 9 October 2026, the day the Dee Bus contract arrived by records request:

  1. SCHOOLS AGAINST ATHLETICS. Transportation for the school day -- the regular routes and
     special education -- against athletic transportation, by year, budgeted and actually
     spent, side by side. Never combined in one calculation (rule 1): a budget is compared
     only with a budget and an actual only with an actual.
  2. PER SPORT. Athletic transportation by sport and season -- and, because the bus contract
     states a per-unit rate for athletic and field trips, an estimate of how many trips each
     sport's dollars buy. That estimate is OURS and is labelled so everywhere it appears
     (rule 3).

WHERE EACH FIGURE COMES FROM, and which kind of thing it is (rule 13a):

  the general fund lines   MUNIS year-end (period 13) reports for the school general fund,
                           FY2023-FY2026 -- printouts from the accounting system, PROOF. For
                           FY2010-FY2022, the Finance Committee's general fund history workbook,
                           which pastes MUNIS exports side by side: `stated`, and used only
                           because its rows TIE to the MUNIS reports in every year both hold
                           whole. The build refuses if they stop tying.
  the budget book          the district's FY2027 budget workbook (`lps-budget-lines.csv`), for
                           the FY2027 scenarios. Its FY2025 and FY2026 budget columns are tied
                           to the MUNIS original appropriations, line by line, on every run.
  the contract             the Dee Bus bid form (Exhibit E), a scan. The rates were read off the
                           page images; this script asserts each against the scan's text layer
                           where that layer is legible, and asserts that rate x buses x days
                           reproduces every subtotal and that the subtotals foot to the printed
                           year totals and the printed Grand Total. A misread rate cannot pass.
  per sport                the district's sport-by-sport workbook (records request) and the
                           Finance Committee's copy of a second per-sport sheet. Both are
                           HAND-ASSEMBLED -- `stated` -- and they disagree; the spread is
                           published, never reconciled into one number.
  the state                DESE's End of Year Financial Report (function 3300 and out-of-district
                           transportation) as a second route to the ledger, and DESE's circuit
                           breaker schedule for the transportation reimbursement.

WHAT THIS SCRIPT REFUSES TO DO:

  * net anything. Fees, the athletic revolving fund and the circuit breaker are each their
    own column. A budget line is NET (rule 11) and the page says so beside every rate.
  * add a budget to an actual, or difference one against the other to make a rate.
  * call a trip estimate a count. Nobody publishes trips; the figure is dollars divided by
    the bid form's own average trip, at FY2026 prices, and it says so.
"""
import argparse
import csv
import html
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import conclusion, emit, figure  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ID = 'transportation'
D = os.path.join(ROOT, 'sources', 'data')
MUNIS = os.path.join(D, 'munis-school-ytd.csv')
GL = os.path.join(D, 'gl-history.csv')
BOOK = os.path.join(D, 'lps-budget-lines.csv')
LINE_HISTORY = os.path.join(D, 'line-history.csv')
BY_SPORT = os.path.join(D, 'athletics-by-sport.csv')
RECON = os.path.join(D, 'athletics-by-sport-reconciliation.csv')
FINCOM_SPORT = os.path.join(D, 'athletics-fincom.csv')
ATH_HISTORY = os.path.join(D, 'athletics-history.csv')
DESE_FUNC = os.path.join(D, 'dese-function-expenditure.csv')
DESE_CB = os.path.join(D, 'dese-circuit-breaker.csv')
CHERRY = os.path.join(D, 'dls-cherry-sheet.csv')
MUNIS_TOWN = os.path.join(D, 'munis-ledger.csv')
GAPS = os.path.join(D, 'money-gaps.csv')
MANIFEST = os.path.join(D, 'archive-manifest.csv')
BID_TXT = os.path.join(ROOT, 'sources', 'contracts', 'txt',
                       'dee-bus-bid-proposal-rates-fy26-fy30.txt')
AGREEMENT_TXT = os.path.join(ROOT, 'sources', 'contracts', 'txt',
                             'dee-bus-transportation-agreement-fy26-fy28.txt')
BOND_TXT = os.path.join(ROOT, 'sources', 'contracts', 'txt',
                        'dee-bus-performance-and-payment-bond-fy27.txt')
OVERVIEW_TXT = os.path.join(ROOT, 'sources', 'district-budget', 'text',
                            'school-department-fy26-budget-overview.txt')
OUT_MD = os.path.join(ROOT, 'sources', 'analyses', ID + '.md')
OUT_JSON = os.path.join(ROOT, 'fy28', 'public', 'data', ID + '.json')
CHART_DIR = os.path.join(ROOT, 'sources', 'analyses', 'charts')
LEA = '01620000'

# WHICH ACCOUNTS ARE TRANSPORTATION. Keyed on the account string's fourth segment (the DESE
# function code) and its last (the object code), never on the org alone -- an org can hold
# several accounts. Every general fund school account whose own description names
# transportation must land in one of these four, or the build stops: a new transportation
# account the classification does not know about would otherwise vanish from every total.
CATS = [
    ('regular', 'Regular routes', '3300', '535025'),
    ('sped', 'Special education transportation', '3300', '535026'),
    ('athletic', 'Athletic transportation', '3510', '535016'),
    ('band', 'Band and music trips', '2440', '535016'),
]
CAT_NAME = {k: n for k, n, _, _ in CATS}
CAT_KEY = {(f, o): k for k, _, f, o in CATS}
SCHOOL_DAY = ('regular', 'sped')

# The budget book's names for the same lines, tied to the ledger by amount on every run.
BOOK_LINES = {
    'regular': ['General Education Transportation'],
    'sped': ['Special Education Transportation - System'],
    'athletic': ['Athletic Transportation'],
    'band': ['M.S. Band/Music Transportation', 'H.S. Band/Music Transportation'],
}

# --------------------------------------------------------------------- the contract
#
# EXHIBIT E: BID PROPOSAL, filled in by hand by Dee Bus Service, Inc. and signed 12-27-24.
# Every value below was read off the page images (notes/findings/DEE-BUS-CONTRACT.md). It is
# held here as a declared reading and TESTED, two ways, on every run:
#
#   1. where the scan's text layer is legible, the token at the cited line must be there;
#   2. rate x buses x 180 days, and trips x rate x miles, must reproduce every subtotal, the
#      subtotals must foot to the printed year total, and the three base years must foot to
#      the printed Grand Total of $6,086,125.00, which the text layer reads cleanly.
#
# So a misread rate fails the arithmetic against a total the scan states legibly. `ocr` is
# (line in the .txt, token exactly as the text layer renders it); None where the layer is
# illegible at that point (FY2028's wait rate reads `s190°` and its total `2, 140, 14(1`).
DAYS = 180
N77, N83 = 8, 3
TRIP_ROWS = [(35, 1750), (35, 1750), (10, 500), (10, 500), (10, 500)]  # 83, 77, 65, 45, van
CONTRACT = [
    dict(fy=2026, label='Year One', optional=False, pdf_page=1, form_page=24,
         p77=485.00, p83=515.00, trip=6.50, wait=130.00, total=1922250.00,
         ocr=dict(p77=(17, '485'), p83=(24, '515'), sub77=(26, '698400'), trip=(35, '6.50'),
                  wait=(73, '130'), total=(81, '1,922, 250'))),
    dict(fy=2027, label='Year Two', optional=False, pdf_page=2, form_page=25,
         p77=523.00, p83=556.00, trip=6.65, wait=140.00, total=2023735.00,
         ocr=dict(p77=(104, '523'), p83=(110, '556'), sub77=(113, '753,120'),
                  trip=(122, '6.65'), wait=(161, '140.00'), total=(166, '2,023,735'))),
    dict(fy=2028, label='Year Three', optional=False, pdf_page=3, form_page=26,
         p77=565.00, p83=588.50, trip=6.90, wait=150.00, total=2140140.00,
         ocr=dict(p77=(186, '565'), p83=(191, '588.50'), trip=(207, '6.90'), wait=None,
                  total=None)),
    dict(fy=2029, label='Optional year four', optional=True, pdf_page=5, form_page=28,
         p77=590.00, p83=630.00, trip=7.00, wait=175.00, total=2222300.00,
         ocr=dict(p77=(300, '590.'), sub77=(306, '849,600'), trip=(316, '7.00'),
                  wait=(357, '175'), total=(364, '2,222,300'))),
    dict(fy=2030, label='Optional year five', optional=True, pdf_page=6, form_page=29,
         p77=637.20, p83=680.40, trip=7.25, wait=190.00, total=2357859.00,
         ocr=dict(p77=(386, '637.20'), sub77=(392, '917,568'), trip=(401, '7.25'),
                  wait=(440, '190.00'), total=(445, '2,357, 859'))),
]
GRAND_TOTAL = 6086125.00
GRAND_OCR = (268, '6,086,125.00')
# The bid form's own estimate of the trip work it prices: "Buses for 100 field trips, athletic
# events, or band event trips. These trips will require 6,500 miles of travel as well as
# approximately four (4) hours of 'waiting time' per trip." BID p1/24, text lines 32-33.
FORM_TRIPS, FORM_MILES, FORM_WAIT_HOURS = 100, 6500, 4
FORM_OCR = [(32, '6,500 miles'), (33, 'four (4) hours')]

# --------------------------------------------------------------------- per-sport crosswalk
#
# The district's sport-by-sport workbook (records request) names a sport one way; the Finance
# Committee's copy of `Athletics Costs (1).xlsx` names it another and sometimes prints two of
# the workbook's rows as one (cross country, track). This map is OURS and exists only so the
# two hand-built sheets can be set side by side. Nothing is averaged.
FINCOM_NAME = {
    ('Fall', 'HS', 'Boys CC'): 'HS Cross Country', ('Fall', 'HS', 'Girls CC'): 'HS Cross Country',
    ('Fall', 'HS', 'Boys Soccer'): "Boys' Soccer", ('Fall', 'HS', 'Cheer'): 'Cheer',
    ('Fall', 'HS', 'Field Hockey'): 'HS Field Hockey', ('Fall', 'HS', 'Football'): 'Football',
    ('Fall', 'HS', 'Girls Soccer'): "Girls' Soccer", ('Fall', 'HS', 'Golf'): 'Golf',
    ('Fall', 'HS', 'Unified Basketball $100'): 'Unified Basketball',
    ('Fall', 'MS', 'Cross Country'): 'MS Cross Country',
    ('Fall', 'MS', 'Field Hockey'): 'MS Field Hockey',
    ('Winter', 'HS', 'HS BasketBall - Boys'): "Boys' Basketball",
    ('Winter', 'HS', 'HS Basketball - Girls'): "Girl's Basketball",
    ('Winter', 'HS', 'Ice Hockey - Boys'): 'Boys Ice Hockey',
    ('Winter', 'HS', 'Ice Hockey - Girls'): 'Girls Ice Hockey',
    ('Winter', 'HS', 'Indoor Track - Boys'): '"Indoor Track"',
    ('Winter', 'HS', 'Indoor Track - Girls'): '"Indoor Track"',
    ('Winter', 'HS', 'Ski Team'): 'Alpine Skiing',
    ('Winter', 'MS', 'Basketball - Boys'): "MS Boys' Basketball",
    ('Winter', 'MS', 'Basketball - Girls'): "MS Girls' Basketball",
    ('Spring', 'HS', 'Baseball'): 'Baseball', ('Spring', 'HS', 'Boys Lax'): "Boys' Lacrosse",
    ('Spring', 'HS', 'Girls Lax'): "Girls' Lacrosse",
    ('Spring', 'HS', 'Boys Track'): '"Outdoor Track"',
    ('Spring', 'HS', 'Girls Track'): '"Outdoor Track"',
    ('Spring', 'HS', 'Softball'): 'Softball',
    ('Spring', 'HS', 'Unified Track ($100)'): '"Unified Track"',
}
SEASONS = ('Fall', 'Winter', 'Spring')

# --------------------------------------------------------------------- what was said (rule 15a)
#
# Re-read from the archive on every run, whitespace collapsed; a miss is fatal. Statements
# of intent, of explanation and of belief -- never used as a count.
QUOTES = [
    dict(key='contract', path='sources/meetings/text/school-committee/2025-01-08-minutes-6948.txt',
         board='School Committee', date='2025-01-08',
         quote='it is a 3 year contract with tentative increases over the 3 years',
         why='The district bringing the Dee Bus bid to the Committee, before the contract was '
             'signed in May 2025.'),
    dict(key='fincom-increases', path='sources/meetings/text/finance-committee/2025-03-06-minutes-7008.txt',
         board='Finance Committee', date='2025-03-06',
         quote='7.6% increase in Dee Bus services 7% increase in vanpool for special education '
               'transportation',
         why='How the FY2026 increase was described to the Finance Committee: a percentage, '
             'with no fleet or rate beside it.'),
    dict(key='not-200', path='sources/meetings/text/school-committee/2025-03-12-minutes-7098.txt',
         board='School Committee', date='2025-03-12', who='Mr. Beardmore',
         quote='The cost of athletic transportation is not up 200%. The way we are accounting '
               'for athletic transportation has been corrected from past practice that was '
               'done incorrectly.',
         why='A School Committee member’s explanation of the FY2026 athletic line. The '
             'by-sport workbook is consistent with it: the cost was already about three times '
             'the line in FY2024.'),
    dict(key='fee-11000', path='sources/meetings/text/finance-committee/2025-03-20-minutes-7010.txt',
         board='Finance Committee', date='2025-03-20',
         quote='The implementation of transportation fee reduced the student transportation '
               'line by $11,000.',
         why='The only statement in the record of how the new bus fee entered the budget. It '
             'is the same amount the FY2026 line was voted below the contract price.'),
    dict(key='reclass', path='sources/meetings/text/school-committee/2025-04-16-minutes-7171.txt',
         board='School Committee', date='2025-04-16',
         quote='A fourth transfer to move funds to the athletic transportation, special detail, '
               'dues and fees and the high school after school stipends, this is the first phase '
               'move making monies available in the athletic portion of the budget. We can go '
               'back and reclassify expenses that had been charged against the revolving account.',
         why='The FY2025 transfer that took the athletic transportation line from its voted '
             'amount to what it spent: costs charged to the fee fund, moved onto the town line.'),
    dict(key='requests', path='sources/meetings/text/school-committee/2025-06-04-minutes-7251.txt',
         board='School Committee', date='2025-06-04',
         quote='We have received 1,074 bus requests, and have 494 unpaid at this time.',
         why='The only count of riders in the record, taken before the first fee year began. '
             'A request is not a rider and an unpaid request is not a refusal.'),
    dict(key='contracts-asked', path='sources/meetings/text/finance-committee/2024-03-14-minutes-6469.txt',
         board='Finance Committee', date='2024-03-14',
         quote='Chris Menard asks for a copy of the bus contracts. The schools will be going out '
               'to bid for school buses in January.',
         why='Said in FY2024, the year the regular-route line ran furthest over its budget, and '
             'ten months before the bid this page reads.'),
    dict(key='renewal', path='sources/meetings/text/finance-committee/2026-02-26-minutes-7673.txt',
         board='Finance Committee', date='2026-02-26',
         quote='Chris Menard suggests the schools work on the contract as it is scheduled to be '
               'renewed in 2028.',
         why='A Finance Committee member pointing at the one transportation decision the town '
             'controls on a schedule: the contract ends on 30 June 2028.'),
    dict(key='field-trip', path='sources/meetings/text/school-committee/2026-03-04-minutes-7687.txt',
         board='School Committee', date='2026-03-04',
         quote='We will need to pay Dee Bus Company upfront and that cost is $731.50.',
         why='One trip, priced under the new contract: a class field trip. It sits inside the '
             'range this page’s per-trip estimate uses.'),
    dict(key='cut', path='sources/meetings/text/finance-committee/2026-03-26-minutes-7737.txt',
         board='Finance Committee', date='2026-03-26',
         quote='All athletic transportation would be cut saving: $127,550.',
         why='The FY2027 balanced budget, as presented to the Finance Committee.'),
    dict(key='band', path='sources/meetings/text/finance-committee/2026-03-26-minutes-7737.txt',
         board='Finance Committee', date='2026-03-26',
         quote='The transportation for Middle-High Band would be reduced to $5,000.',
         why='The same presentation. The FY2027 balanced budget in the district’s book carries '
             'nothing for either band transportation line; the minute and the book differ, and '
             'the record here does not say which held.'),
    dict(key='parent', path='sources/meetings/text/school-committee/2026-03-23-minutes-7732.txt',
         board='School Committee', date='2026-03-23',
         quote='a more creative avenue for further conversation needs to be had about the '
               'athletic transportation',
         why='A parent at public comment, on the cut. The same meeting heard a student ask why '
             'teachers were being cut while athletic transportation was not yet.'),
    dict(key='boosters', path='sources/meetings/text/school-committee/2026-07-29-minutes-7930.txt',
         board='School Committee', date='2026-07-29',
         quote='two buses will be necessary for transportation to away games',
         why='The football boosters, offering to pay for buses after the FY2027 cut.'),
    dict(key='waiver', path='sources/meetings/text/school-committee/2026-08-26-minutes-7980.txt',
         board='School Committee', date='2026-08-26',
         quote='the private transportation waiver currently included in FinalForms, which '
               'allowed student-athletes to be transported privately while district '
               'transportation was unavailable',
         why='A parent’s question: with district buses cut, athletes were being driven privately '
             'under a signed waiver. The FY2026 athletic line had come in under its revised '
             'budget.'),
    dict(key='restore', path='sources/meetings/text/school-committee/2026-08-26-minutes-7980.txt',
         board='School Committee', date='2026-08-26',
         quote='the verified transportation cost was approximately $58,880, which she rounded '
               'to $60,000. Of that amount, $10,000 would come from the additional '
               'appropriation and $50,000 from the athletic revolving account.',
         why='The Superintendent’s plan to restore high school athletic buses for FY2027. '
             'She attributed the lower figure to scheduling competitions closer to Lunenburg, '
             'more home competitions, and estimating from actual schedules.'),
    dict(key='cb-75', path='sources/meetings/text/school-committee/2025-05-07-minutes-7207.txt',
         board='School Committee', date='2025-05-07',
         quote='75% reimbursement for FY25 out of district special education transportation '
               'costs through the circuit breaker program increased from 44%',
         why='The district’s account of the state’s change to the transportation half of the '
             'circuit breaker. The state’s own schedule shows the payment rising the same year.'),
]

# The district's own written explanations, quoted from its FY2026 budget overview. Rule 7:
# these are the district's account of why a line moved, and are labelled as that.
OVERVIEW_QUOTES = {
    'dee': 'Dee Bus 7.6% line increase = $69,300',
    'vans': 'Line increase 27% = $120,406 (due to increase in number of vans and monitors '
            'needed)',
    'athletics': 'budgeted to cover full cost of transportation for athletics; athletic '
                 'revolving can not support these increased costs',
}

# The fee proposal's statement of the transportation policy, checked verbatim.
PROPOSAL_TXT = os.path.join(ROOT, 'sources', 'district-budget', 'text', 'sc-meetings',
                            '2024-2025-transportation-fee-proposal.txt')
POLICY_QUOTE = ('Beginning in the 2023-2024 school-year, Lunenburg Public Schools transports all '
                'students (K-12) who reside in Lunenburg.')
ELEVEN_QUOTE = 'LPS uses 11 buses'

# The money_gaps rows this page CITES (rule 7c). The build refuses if one has been renamed,
# because a citation to a row that no longer exists reads as a limit nobody registered.
GAP_ROWS = {
    'rates': 'What the Dee Bus rates and fleet were in FY2025, so the 7.6% FY2026 increase can '
             'be split into price and buses',
    'booked': 'Where bus fee receipts are booked',
    'sport-cost': 'Which of the three published per-sport athletics cost figures is correct',
    'net-revolving': 'Whether a general fund athletics line is net of the revolving fund',
    'trips': 'How many athletic bus trips each sport took, and what each trip cost',
    'fee-account': 'Whether the school choice fund’s SCH. CHOICE BUS FEE account is where '
                   'the student bus fees are booked',
    'vans': 'How many vans, monitors and routes special education transportation pays for, '
            'and at what rates',
    'riders': 'How many children ride the school buses, and how many pay the fee',
    'dese-fy25': 'Why DESE’s FY2025 transportation spending for Lunenburg differs from the '
                 'town ledger',
}


# --------------------------------------------------------------------- helpers

def fail(msg):
    raise SystemExit('build_transportation: ' + msg)


def num(x):
    x = (x or '').strip()
    return float(x) if x else 0.0


def segs(account):
    return account.split('-')


def cat_of(account):
    s = segs(account)
    if len(s) != 9:
        return None
    return CAT_KEY.get((s[3], s[8]))


def collapse(s):
    return re.sub(r'\s+', ' ', s).strip()


def r0(x):
    return int(round(x))


def usd2(x):
    return '$' + format(float(x), ',.2f')


def rate(x):
    """A contract unit price: cents only when it has them."""
    x = float(x)
    return ('$%s' % format(x, ',.2f')) if abs(x - round(x)) > 1e-9 else ('$%s' % format(int(round(x)), ',d'))


def pct1(a, b):
    return round(100.0 * a / b, 1)


# --------------------------------------------------------------------- the ledger

def load_ledger():
    munis = list(csv.DictReader(open(MUNIS, encoding='utf-8')))
    ml = {}
    stray = set()
    for r in munis:
        if r['period'] != '13' or r['fund'] != '0100' or r['type'] != 'E':
            continue
        c = cat_of(r['account'])
        if not c:
            if re.search(r'TRANSP|\bBUS\b', r['description'], re.I):
                stray.add((r['account'], r['description']))
            continue
        a = ml.setdefault((int(r['fiscal_year']), c), [0.0, 0.0, 0.0, 0.0])
        a[0] += num(r['original_approp'])
        a[1] += num(r['revised_budget'])
        a[2] += num(r['ytd_expended'])
        a[3] += num(r['encumbrances'])
    if stray:
        fail('general fund school accounts naming transportation that no category holds: %s'
             % sorted(stray))
    m_years = sorted({fy for fy, _ in ml})
    if m_years != [2023, 2024, 2025, 2026]:
        fail('the MUNIS year-end reports cover %s, not FY2023-FY2026' % m_years)
    for fy in m_years:
        for c in CAT_NAME:
            if (fy, c) not in ml:
                fail('FY%d has no %s account in the MUNIS report -- a join that matched nothing'
                     % (fy, c))

    gl, partial = {}, set()
    for r in csv.DictReader(open(GL, encoding='utf-8')):
        if r['sheet'] != 'general_fund' or r['department_code'] != '300':
            continue
        c = cat_of(r['account'])
        if not c:
            if re.search(r'TRANSP', r['org_desc'], re.I):
                fail('a Finance Committee workbook transportation account no category holds: %s'
                     % r['account'])
            continue
        fy = int(r['fiscal_year'])
        if r['actual_is_partial'] == 'true':
            partial.add(fy)
        a = gl.setdefault((fy, c), [0.0, 0.0, 0.0])
        a[0] += num(r['original'])
        a[1] += num(r['revised'])
        a[2] += num(r['actual'])

    # THE TIE. The workbook is used before FY2023 only because it equals the accounting
    # system's own report, to the dollar, line by line, in every year both hold whole.
    tie_years = sorted({fy for fy, _ in gl} & set(m_years) - partial)
    if len(tie_years) < 2:
        fail('fewer than two years to tie the workbook to MUNIS: %s' % tie_years)
    for fy in tie_years:
        for c in CAT_NAME:
            a, b = gl[(fy, c)], ml[(fy, c)]
            if abs(r0(a[0]) - r0(b[0])) > 1 or abs(r0(a[2]) - r0(b[2] + b[3])) > 1:
                fail('FY%d %s: the Finance Committee workbook (%s / %s) does not tie to the '
                     'MUNIS year-end report (%s / %s)' % (fy, c, a[0], a[2], b[0], b[2] + b[3]))

    rows = []
    first = min(fy for fy, _ in gl)
    for fy in range(first, max(m_years) + 1):
        src = 'munis' if fy in m_years else 'fincom'
        if src == 'fincom' and fy in partial:
            fail('FY%d would be read from a partial column' % fy)
        row = dict(fy=fy, source=src)
        for c in CAT_NAME:
            if src == 'munis':
                o, rv, ex, en = ml[(fy, c)]
            else:
                if (fy, c) not in gl:
                    fail('FY%d has no %s account in the workbook' % (fy, c))
                o, rv, ex = gl[(fy, c)]
                en = 0.0
            row[c] = dict(budget=r0(o), revised=r0(rv), spent=r0(ex + en), expended=r0(ex),
                          committed=r0(en))
        for side in ('budget', 'spent'):
            row['school_' + side] = sum(row[c][side] for c in SCHOOL_DAY)
            row['all_' + side] = sum(row[c][side] for c in CAT_NAME)
        rows.append(row)
    return rows, tie_years, ml


def load_book(ml):
    """The district's budget book: FY2027 by scenario, and its FY2025/FY2026 budget columns
    tied to the ledger's original appropriations."""
    book = list(csv.DictReader(open(BOOK, encoding='utf-8')))
    out = {}
    for c, names in BOOK_LINES.items():
        rs = [r for r in book if r['line_item'] in names and r['section'] == 'EXPENSES']
        if len(rs) != len(names):
            fail('the budget book has %d rows for %s, not %d' % (len(rs), c, len(names)))
        d = {}
        for col in ('fy25_budget', 'fy26_final', 'fy27_core', 'fy27_level_service',
                    'fy27_balanced', 'restoration_2_24_26'):
            d[col] = r0(sum(num(r[col]) for r in rs))
        d['rows'] = [int(r['row']) for r in rs]
        d['comments'] = [r['comments'] for r in rs if r['comments'].strip()]
        for col, fy in (('fy25_budget', 2025), ('fy26_final', 2026)):
            if abs(d[col] - r0(ml[(fy, c)][0])) > 1:
                fail('%s: the budget book %s (%s) does not tie to the MUNIS FY%d original '
                     'appropriation (%s)' % (c, col, d[col], fy, ml[(fy, c)][0]))
        out[c] = d
    netted = [x for x in out['regular']['comments'] if '50K' in x and 'busing fees' in x]
    if not netted:
        fail('the budget book no longer carries the busing-fee comment beside general '
             'education transportation')
    out['regular']['fee_comment'] = netted[0]
    lh = [r for r in csv.DictReader(open(LINE_HISTORY, encoding='utf-8'))
          if r['fy'] == '2027' and r['stage'] == 'proposed' and not r['variant']]
    early = {r['key']: (r0(num(r['value'])), r['source']) for r in lh
             if r['key'] in ('general ed transportation', 'athletic transportation')}
    if len(early) != 2:
        fail('line-history no longer holds the early FY2027 proposals for the two lines')
    out['early'] = early
    return out


# --------------------------------------------------------------------- the contract

def load_contract():
    lines = open(BID_TXT, encoding='utf-8').read().split('\n')

    def at(ln, tok, what):
        if tok not in lines[ln - 1]:
            fail('the bid form text layer no longer reads %r at line %d (%s): %r'
                 % (tok, ln, what, lines[ln - 1]))

    years = []
    for y in CONTRACT:
        for k, v in y['ocr'].items():
            if v:
                at(v[0], v[1], 'FY%d %s' % (y['fy'], k))
        sub77 = round(N77 * y['p77'] * DAYS, 2)
        sub83 = round(N83 * y['p83'] * DAYS, 2)
        trips = [round(n * y['trip'] * mi, 2) for n, mi in TRIP_ROWS]
        wait = round(FORM_TRIPS * y['wait'] * FORM_WAIT_HOURS, 2)
        total = round(sub77 + sub83 + sum(trips) + wait, 2)
        if abs(total - y['total']) > 0.005:
            fail('FY%d: the bid form lines sum to %s, not the printed %s -- a rate is misread'
                 % (y['fy'], total, y['total']))
        years.append(dict(fy=y['fy'], label=y['label'], optional=y['optional'],
                          pdf_page=y['pdf_page'], form_page=y['form_page'],
                          p77=y['p77'], p83=y['p83'], sub77=sub77, sub83=sub83,
                          regular=round(sub77 + sub83, 2), trip_rate=y['trip'],
                          wait_rate=y['wait'], trip_lines=round(sum(trips), 2),
                          wait_line=wait, total=y['total'],
                          ocr_lines={k: v[0] for k, v in y['ocr'].items() if v}))
    at(GRAND_OCR[0], GRAND_OCR[1], 'Grand Total')
    base = round(sum(y['total'] for y in years if not y['optional']), 2)
    if abs(base - GRAND_TOTAL) > 0.005:
        fail('the three base years sum to %s, not the printed Grand Total %s' % (base, GRAND_TOTAL))
    for ln, tok in FORM_OCR:
        at(ln, tok, 'the trip estimate')
    if sum(n for n, _ in TRIP_ROWS) != FORM_TRIPS:
        fail('the form’s trip counts no longer sum to its stated %d trips' % FORM_TRIPS)

    ag = open(AGREEMENT_TXT, encoding='utf-8').read()
    for tok in ('commence work under this Contract on July 1, 2025', 'by June 30, 2028',
                '2028/2029 school year', '2029/2030 school year', 'subject to appropriation'):
        if tok not in collapse(ag):
            fail('the agreement no longer reads %r' % tok)
    bond = collapse(open(BOND_TXT, encoding='utf-8').read())
    if '$2,019,685.00' not in bond or 'July 1, 2026 through June 30, 2027' not in bond:
        fail('the performance bond no longer reads its sum and term')

    y1 = years[0]
    per_trip_miles = FORM_MILES / FORM_TRIPS
    trip_full = round(per_trip_miles * y1['trip_rate'] + FORM_WAIT_HOURS * y1['wait_rate'], 2)
    trip_nowait = round(per_trip_miles * y1['trip_rate'], 2)
    return dict(years=years, grand=GRAND_TOTAL, n77=N77, n83=N83, days=DAYS,
                bond=2019685.00, per_trip_miles=per_trip_miles, trip_full=trip_full,
                trip_nowait=trip_nowait, wait_hours=FORM_WAIT_HOURS,
                form_trips=FORM_TRIPS, form_miles=FORM_MILES,
                form_mile_rows=sum(mi for _, mi in TRIP_ROWS))


# --------------------------------------------------------------------- athletics per sport

def clean_sport(s):
    return re.sub(r'\s*\(?\$\d+\)?\s*$', '', s).strip()


def load_sports(contract):
    rows = {}
    for r in csv.DictReader(open(BY_SPORT, encoding='utf-8')):
        if r['metric'] != 'Transportation' or r['is_numeric'] != '1':
            continue
        k = (r['season'], r['level'], r['sport'])
        rows.setdefault(k, {})[int(r['fy'])] = (num(r['value']), r['cell'])
    years = sorted({fy for v in rows.values() for fy in v})
    if years != [2024, 2025]:
        fail('the by-sport workbook carries transportation for %s, not FY2024-FY2025' % years)
    # The printed season totals, against the rows (rule 13: reconcile to the source's own
    # total, and publish where it does not tie rather than burying it).
    printed = {}
    for r in csv.DictReader(open(RECON, encoding='utf-8')):
        if r['metric'] == 'Transportation' and r['scope'] == 'ALL':
            printed[(r['season'], int(r['fy']))] = (
                num(r['printed']) if r['printed'].strip() else None, r['printed_cell'],
                num(r['summed_from_rows']), r['ties'] == '1')
    seasons = []
    for s in SEASONS:
        for fy in years:
            summed = round(sum(v[fy][0] for k, v in rows.items() if k[0] == s and fy in v), 2)
            p = printed.get((s, fy))
            if not p:
                fail('no printed %s total for FY%d' % (s, fy))
            if abs(p[2] - summed) > 0.01:
                fail('%s FY%d: our row sum %s differs from the reconciliation file %s'
                     % (s, fy, summed, p[2]))
            seasons.append(dict(season=s, fy=fy, rows=summed, printed=p[0], cell=p[1],
                                ties=p[3]))
    totals = {fy: round(sum(v[fy][0] for v in rows.values() if fy in v), 2) for fy in years}

    fincom = {}
    for r in csv.DictReader(open(FINCOM_SPORT, encoding='utf-8')):
        m = re.match(r'transportation_cost_fy(\d\d)$', r['metric'])
        if m:
            fincom[(r['sport'], 2000 + int(m.group(1)))] = num(r['value'])
    fin_groups = {}
    for k, name in FINCOM_NAME.items():
        fin_groups.setdefault(name, []).append(k)
    unmapped = sorted({n for n, _ in fincom} - set(fin_groups))
    if unmapped:
        fail('the Finance Committee sheet names sports the crosswalk does not: %s' % unmapped)

    out = []
    for k, v in rows.items():
        s, lvl, sport = k
        fy25 = v.get(2025, (None, None))[0]
        fy24 = v.get(2024, (None, None))[0]
        out.append(dict(
            season=s, level=lvl, sport=clean_sport(sport), printed_name=sport,
            fy2024=round(fy24, 2) if fy24 is not None else None,
            fy2025=round(fy25, 2) if fy25 is not None else None,
            cell2024=v.get(2024, (None, None))[1], cell2025=v.get(2025, (None, None))[1],
            trips=(round(fy25 / contract['trip_full'], 1) if fy25 else None),
            trips_nowait=(round(fy25 / contract['trip_nowait'], 1) if fy25 else None),
            fincom_name=FINCOM_NAME.get(k)))
    order = {s: i for i, s in enumerate(SEASONS)}
    out.sort(key=lambda r: (order[r['season']], r['level'], -(r['fy2025'] or 0), r['sport']))

    # The two sheets, sport by sport, where the Finance Committee copy prints the sport.
    compare = []
    for name, keys in fin_groups.items():
        for fy in years:
            if (name, fy) not in fincom:
                continue
            ours = [rows[k][fy][0] for k in keys if k in rows and fy in rows[k]]
            if not ours:
                continue
            compare.append(dict(name=name.strip('"'), fy=fy, workbook=round(sum(ours), 2),
                                fincom=round(fincom[(name, fy)], 2),
                                agree=abs(sum(ours) - fincom[(name, fy)]) < 0.01))
    compare.sort(key=lambda r: (r['fy'], r['name']))

    hist = {}
    for r in csv.DictReader(open(ATH_HISTORY, encoding='utf-8')):
        if r['side'] == 'revolving' and r['item'] == 'Athletic Transportation' \
                and r['basis'] in ('actual', 'budget'):
            hist[int(r['fy'])] = dict(amount=r0(num(r['amount'])), basis=r['basis'],
                                      source=r['source'])
    if not any(h['basis'] == 'actual' for h in hist.values()):
        fail('athletics-history no longer holds the revolving fund’s actual transportation')
    ranked = sorted([r for r in out if r['fy2025']], key=lambda r: -r['fy2025'])
    return dict(rows=out, seasons=seasons, totals=totals, compare=compare, revolving=hist,
                ranked=ranked)


# --------------------------------------------------------------------- the state, and the fee

def load_state(ledger):
    func = {}
    for r in csv.DictReader(open(DESE_FUNC, encoding='utf-8')):
        if r['lea'] != LEA:
            continue
        if r['func_code'] == '3300' and r['level'] == 'detail':
            func.setdefault(int(r['fy']), {})['in'] = r0(num(r['gen_fund']))
            func[int(r['fy'])]['in_other'] = r0(num(r['grants_revolving']))
        if r['func_code'] == 'ODTR':
            func.setdefault(int(r['fy']), {})['ood'] = r0(num(r['gen_fund']))
    by = {r['fy']: r for r in ledger}
    dese = []
    for fy in sorted(func):
        d = func[fy]
        if 'in' not in d or 'ood' not in d:
            continue
        tot = d['in'] + d['ood']
        led = by[fy]['school_spent'] if fy in by else None
        dese.append(dict(fy=fy, in_district=d['in'], out_of_district=d['ood'], total=tot,
                         other_funds=d.get('in_other', 0), ledger=led,
                         diff=(tot - led) if led is not None else None))
    ties = [x['fy'] for x in dese if x['diff'] is not None and abs(x['diff']) <= 1]
    if not {2023, 2024} <= set(ties):
        fail('DESE function 3300 plus out-of-district transportation no longer ties to the '
             'ledger in FY2023 and FY2024: %s' % ties)

    cb = []
    for r in csv.DictReader(open(DESE_CB, encoding='utf-8')):
        if r['lea'] != LEA or r['level'] != 'district':
            continue
        t = num(r['reimb_transport'])
        if t:
            cb.append(dict(fy=int(r['fy']), transport=r0(t),
                           supplemental=r0(num(r['additional_supplemental_payment'])),
                           comment=r['comments']))
    cb.sort(key=lambda x: x['fy'])
    if not cb or cb[0]['fy'] != 2022:
        fail('the circuit breaker transportation reimbursement no longer starts in FY2022')

    regional = [num(r['amount']) for r in csv.DictReader(open(CHERRY, encoding='utf-8'))
                if r['name'] == 'Lunenburg' and r['line'] == 'Regional Transportation']
    if not regional or any(regional):
        fail('the Cherry Sheet no longer shows Lunenburg receiving no regional transportation '
             'reimbursement in every year')
    cherry_years = sorted({int(r['fy']) for r in csv.DictReader(open(CHERRY, encoding='utf-8'))
                           if r['name'] == 'Lunenburg' and r['line'] == 'Regional Transportation'})

    fee = {}
    for r in csv.DictReader(open(MUNIS, encoding='utf-8')):
        if r['period'] == '13' and r['fund'] == '1308' and r['obj'] == '437601':
            if r['description'].strip() != 'SCH. CHOICE BUS FEE':
                fail('account 437601 in fund 1308 is no longer described as SCH. CHOICE BUS FEE')
            fee[int(r['fiscal_year'])] = round(-num(r['ytd_expended']), 2) + 0.0
    if sorted(fee) != [2023, 2024, 2025, 2026]:
        fail('the school choice fund bus fee account is not in all four year-end reports')
    town_fee = [r for r in csv.DictReader(open(MUNIS_TOWN, encoding='utf-8'))
                if r['object'] == '437600' and r['name'] == 'STUDENTBUS']
    if not town_fee:
        fail('the town general fund STUDENTBUS revenue account is no longer in munis-ledger')
    tf = max(town_fee, key=lambda r: (int(r['fy']), int(r['period'])))
    return dict(dese=dese, dese_ties=ties, cb=cb, cherry_years=cherry_years, fee=fee,
                town_fee=dict(fy=int(tf['fy']), period=int(tf['period']),
                              revised=num(tf['revised']), expended=num(tf['expended'])))


FEE_EMAIL = os.path.join(ROOT, 'sources', 'correspondence', '2025-05-bus-fees-superintendent.txt')


def load_fees():
    t = open(FEE_EMAIL, encoding='utf-8').read()
    one = re.search(r'^\$(\d+) Families with 1 student$', t, re.M)
    two = re.search(r'^\$(\d+) Families with 2 or more students$', t, re.M)
    if not one or not two:
        fail('the May 2025 bus fee email no longer states the one-child and family rates')
    return dict(one=int(one.group(1)), family=int(two.group(1)))


def check_quotes():
    out = []
    for q in QUOTES:
        p = os.path.join(ROOT, q['path'])
        text = collapse(open(p, encoding='utf-8').read())
        if collapse(q['quote']) not in text:
            fail('quote %r is no longer verbatim in %s' % (q['key'], q['path']))
        out.append(dict(q, cite='/docs/' + q['path'][len('sources/'):].replace(
            'meetings/text/', 'minutes/text/', 1)))
    pr = collapse(open(PROPOSAL_TXT, encoding='utf-8').read())
    for t in (POLICY_QUOTE, ELEVEN_QUOTE):
        if t not in pr:
            fail('the fee proposal no longer reads %r' % t)
    ov = collapse(open(OVERVIEW_TXT, encoding='utf-8').read())
    for k, s in OVERVIEW_QUOTES.items():
        if collapse(s) not in ov:
            fail('the FY2026 budget overview no longer reads %r' % s)
    return out


def check_gaps():
    whats = {r['what'] for r in csv.DictReader(open(GAPS, encoding='utf-8'))}
    missing = [k for k, w in GAP_ROWS.items() if w not in whats]
    if missing:
        fail('money-gaps.csv no longer carries the rows this page cites: %s' % missing)
    return dict(GAP_ROWS)


# --------------------------------------------------------------------- measure

def measure():
    ledger, tie_years, ml = load_ledger()
    book = load_book(ml)
    k = load_contract()
    sp = load_sports(k)
    st = load_state(ledger)
    quotes = check_quotes()
    gaps = check_gaps()
    fees = load_fees()
    by = {r['fy']: r for r in ledger}
    last = ledger[-1]['fy']
    L = by[last]

    # Rule 1: the share is computed twice -- spent over spent, budget over budget -- and
    # never across.
    share = {r['fy']: dict(spent=pct1(r['athletic']['spent'], r['all_spent']),
                           budget=pct1(r['athletic']['budget'], r['all_budget']))
             for r in ledger}
    hi_share = max(ledger, key=lambda r: share[r['fy']]['spent'])
    lo_share = min(ledger, key=lambda r: share[r['fy']]['spent'])

    # Special education transportation: low point since FY2020, and the overruns.
    # The base for the special education trend is FY2019, the last year before the school
    # closures of 2020 -- OUR choice, and said where it is used. FY2020 and FY2021 are the
    # series' lowest points for a reason that is not a trend, and starting from either would
    # inflate the rise.
    sped_low = [r for r in ledger if r['fy'] == 2019][0]
    sped_under_run = [r['fy'] for r in ledger if 2016 <= r['fy'] <= 2023
                      and r['sped']['spent'] < r['sped']['budget']]
    if sped_under_run != list(range(2016, 2024)):
        fail('special education transportation no longer came in under budget in every year '
             'FY2016-FY2023, which the page states: %s' % sped_under_run)
    sped_over = [dict(fy=r['fy'], over=r['sped']['spent'] - r['sped']['budget'],
                      pct=pct1(r['sped']['spent'] - r['sped']['budget'], r['sped']['budget']))
                 for r in ledger if r['sped']['spent'] > r['sped']['budget']]
    recent_over = [x for x in sped_over if x['fy'] >= last - 3]

    y = {c['fy']: c for c in k['years']}
    first_k = k['years'][0]['fy']
    reg25 = by[2025]['regular']['budget']
    step = round(y[first_k]['regular'] - reg25)
    fleet_a = round(reg25 / DAYS / (N77 + N83), 2)
    fleet_b = round(reg25 / DAYS / (N77 + N83 - 1), 2)
    fy26_avg = round(y[first_k]['regular'] / DAYS / (N77 + N83), 2)
    rises = {fy: pct1(y[fy]['regular'] - y[fy - 1]['regular'], y[fy - 1]['regular'])
             for fy in sorted(y) if fy - 1 in y}
    netted = round(y[2026]['regular'] - by[2026]['regular']['budget'])
    moved_back = by[2026]['regular']['revised'] - by[2026]['regular']['budget']

    ath = sp['totals']
    fy27 = {c: book[c]['fy27_balanced'] for c in CAT_NAME}
    trips_total = round(ath[2025] / k['trip_full'], 1)
    trips_total_nowait = round(ath[2025] / k['trip_nowait'], 1)
    ath26 = by[2026]['athletic']
    trips26 = round(ath26['expended'] / k['trip_full'], 1)
    trips26_all = round(ath26['spent'] / k['trip_full'], 1)
    # Figures STATED at meetings are read out of the verified quotation, never typed.
    qd = {q['key']: q['quote'] for q in quotes}
    money = lambda t: [float(x.replace(',', '')) for x in re.findall(r'\$([\d,]+(?:\.\d+)?)', t)]
    field_trip = money(qd['field-trip'])[0]
    nums = lambda t: [int(x.replace(',', '')) for x in re.findall(r'\b\d[\d,]*\b', t)]
    requests, unpaid = nums(qd['requests'])
    reclass = by[2025]['athletic']['revised'] - by[2025]['athletic']['budget']
    if not (k['trip_nowait'] <= field_trip <= k['trip_full']):
        fail('the quoted field trip price no longer sits inside the per-trip range')
    restore, _rounded, restore_town, restore_fund = money(qd['restore'])
    p27 = y[2027]
    restore_trip_price = round(k['per_trip_miles'] * p27['trip_rate']
                               + k['wait_hours'] * p27['wait_rate'], 2)
    restore_trips = round(restore / restore_trip_price)
    top = sp['ranked'][:2]
    top5 = sum(r['fy2025'] for r in sp['ranked'][:5])
    spring25 = [s for s in sp['seasons'] if s['season'] == 'Spring' and s['fy'] == 2025][0]
    agree = sum(1 for c in sp['compare'] if c['agree'])

    return dict(
        ledger=ledger, tie_years=tie_years, book=book, contract=k, sports=sp, state=st,
        quotes=quotes, gaps=gaps, fees=fees, first=ledger[0]['fy'], last=last, L=L, share=share,
        hi_share=hi_share, lo_share=lo_share, sped_low=sped_low, sped_over=sped_over,
        recent_over=recent_over, sped_under_run=sped_under_run, step=step, reg25=reg25, fleet_a=fleet_a, fleet_b=fleet_b,
        fy26_avg=fy26_avg, rises=rises, netted=netted, moved_back=moved_back, fy27=fy27,
        trips_total=trips_total, trips_total_nowait=trips_total_nowait, trips26=trips26,
        trips26_all=trips26_all, field_trip=field_trip, restore=restore, requests=requests, unpaid=unpaid, reclass=reclass,
        restore_town=restore_town, restore_fund=restore_fund,
        restore_trip_price=restore_trip_price, restore_trips=restore_trips, top=top, top5=top5,
        spring25=spring25, agree=agree, ystep=y)


# --------------------------------------------------------------------- conclusions

def fyf(y):
    return figure(y, C.fy(y), 'fiscal year')


def build_conclusions(m):
    L, last, k, sp, st = m['L'], m['last'], m['contract'], m['sports'], m['state']
    y = m['ystep']
    rows = []

    # 1. THE SIGNATURE: schools against athletics.
    sh = m['share'][last]
    rows.append(conclusion(
        id='school-day-is-the-bill', bearing='sizes', kind='measured',
        figure='share',
        claim='Athletic buses were %s of school transportation spending in %s.'
              % (C.pct(sh['spent']), C.fy(last)),
        so_what='The school-day buses — regular routes and special education vans — were '
                '%s; band trips the rest.' % C.pct(100 - sh['spent'] - pct1(L['band']['spent'],
                                                                         L['all_spent'])),
        detail='In %s the general fund spent %s on regular routes, %s on special education '
               'transportation, %s on athletic buses and %s on band trips — %s in all. On the '
               'budget side alone, athletics was %s of what was voted. From %s to %s '
               'athletics never passed %s of what was spent, and fell as low as %s in %s.'
               % (C.fy(last), C.usd(L['regular']['spent']), C.usd(L['sped']['spent']),
                  C.usd(L['athletic']['spent']), C.usd(L['band']['spent']),
                  C.usd(L['all_spent']), C.pct(sh['budget']), C.fy(m['first']), C.fy(last),
                  C.pct(m['share'][m['hi_share']['fy']]['spent']),
                  C.pct(m['share'][m['lo_share']['fy']]['spent']), C.fy(m['lo_share']['fy'])),
        figures={'share': figure(sh['spent'], C.pct(sh['spent'])),
                 'rest': figure(100 - sh['spent'] - pct1(L['band']['spent'], L['all_spent']),
                                C.pct(100 - sh['spent'] - pct1(L['band']['spent'],
                                                               L['all_spent']))),
                 'fy': fyf(last), 'first': fyf(m['first']),
                 'reg': figure(L['regular']['spent'], C.usd(L['regular']['spent'])),
                 'sped': figure(L['sped']['spent'], C.usd(L['sped']['spent'])),
                 'ath': figure(L['athletic']['spent'], C.usd(L['athletic']['spent'])),
                 'band': figure(L['band']['spent'], C.usd(L['band']['spent'])),
                 'all': figure(L['all_spent'], C.usd(L['all_spent'])),
                 'bshare': figure(sh['budget'], C.pct(sh['budget'])),
                 'hi': figure(m['share'][m['hi_share']['fy']]['spent'],
                              C.pct(m['share'][m['hi_share']['fy']]['spent'])),
                 'lo': figure(m['share'][m['lo_share']['fy']]['spent'],
                              C.pct(m['share'][m['lo_share']['fy']]['spent'])),
                 'lofy': fyf(m['lo_share']['fy'])},
        basis='General fund school accounts, voted budget and spent at the close (expended '
              'plus still committed): MUNIS year-end reports FY2023 to FY2026, the Finance '
              'Committee’s ledger history before that. Which account is which kind is ours, '
              'by function and object code.',
        not_shown='Athletic buses the athletic fee fund paid for are not in the general fund '
                  'and not in this share: in FY2024 the district’s own sheet put athletic '
                  'transportation at about three times the general fund line. Every line is '
                  'net of whatever else pays for it (rule 11).',
        see=[('/what-sports-cost', 'What sports cost')],
    ))

    # 2. Athletics: the FY2026 rise moved who pays.
    a24 = m['ledger'][[r['fy'] for r in m['ledger']].index(2024)]['athletic']
    rows.append(conclusion(
        id='athletic-cost-was-already-there', bearing='sizes', kind='measured',
        figure='sheet24',
        claim='The district’s own sheet put %s athletic bus costs at %s; the voted line was %s.'
              % (C.fy(2024), C.usd(sp['totals'][2024]), C.usd(a24['budget'])),
        so_what='So the line’s jump to %s in %s moved who pays, as the district said; the '
                'cost was already there.' % (C.usd(L['athletic']['budget']), C.fy(last)),
        detail='The district’s sport-by-sport workbook, hand-assembled and received by records '
               'request, totals %s for %s and %s for %s. The general fund line was voted at '
               '%s in both years and spent %s and %s. The district’s FY2026 overview says the '
               'line was “budgeted to cover full cost of transportation for athletics; '
               'athletic revolving can not support these increased costs”.'
               % (C.usd(sp['totals'][2024]), C.fy(2024), C.usd(sp['totals'][2025]),
                  C.fy(2025), C.usd(a24['budget']), C.usd(a24['spent']),
                  C.usd(m['ledger'][[r['fy'] for r in m['ledger']].index(2025)]['athletic']['spent'])),
        figures={'sheet24': figure(sp['totals'][2024], C.usd(sp['totals'][2024])),
                 'sheet25': figure(sp['totals'][2025], C.usd(sp['totals'][2025])),
                 'line': figure(a24['budget'], C.usd(a24['budget'])),
                 'spent24': figure(a24['spent'], C.usd(a24['spent'])),
                 'spent25': figure(m['ledger'][[r['fy'] for r in m['ledger']].index(2025)]['athletic']['spent'],
                                   C.usd(m['ledger'][[r['fy'] for r in m['ledger']].index(2025)]['athletic']['spent'])),
                 'new': figure(L['athletic']['budget'], C.usd(L['athletic']['budget'])),
                 'fy24': fyf(2024), 'fy25': fyf(2025), 'fy': fyf(last)},
        allow=('FY2026',),
        basis='The district’s sport-by-sport workbook (records request, June 2026), row sums; '
              'the general fund athletic transportation account in the MUNIS year-end reports; '
              'the district’s FY2026 budget overview.',
        not_shown='The workbook is assembled by hand and a second district sheet gives '
                  'different figures for several of the same sports. Nothing published says how '
                  'many trips either year ran, so a change in trips and a change in who paid '
                  'cannot be fully separated.',
        see=[('/analysis/athletics-ledger', 'The athletics fee fund, line by line')],
    ))

    # 3. Per sport, and the trip estimate -- OURS.
    t0, t1 = m['top'][0], m['top'][1]
    rows.append(conclusion(
        id='trips-per-sport', bearing='sizes', kind='hypothesis', figure='trips',
        claim='Our estimate: %s athletic bus spending equals about %s trips at the new '
              'contract’s prices.' % (C.fy(2025), C.num(m['trips_total'])),
        so_what='%s buses cost the most, about %s trips; %s next. No sport topped %s.'
                % ((t0['sport'] if t0['level'] == 'HS' else 'MS ' + t0['sport']),
                   C.num(t0['trips']),
                   (t1['sport'] if t1['level'] == 'HS' else 'MS ' + t1['sport']).lower(),
                   C.usd(t0['fy2025'])),
        detail='The sheet’s %s transportation, %s, divided by the cost of the bid form’s own '
               'average trip at %s prices: %s miles at %s a mile and %s hours of waiting at %s '
               'an hour, %s. With no waiting time a trip is %s and the same dollars are about '
               '%s trips. %s prices are not held; if they were lower, the counts are higher.'
               % (C.fy(2025), C.usd(sp['totals'][2025]), C.fy(2026),
                  C.num(k['per_trip_miles']), usd2(k['years'][0]['trip_rate']),
                  C.num(k['wait_hours']), usd2(k['years'][0]['wait_rate']),
                  usd2(k['trip_full']), usd2(k['trip_nowait']),
                  C.num(m['trips_total_nowait']), C.fy(2025)),
        figures={'trips': figure(m['trips_total'], C.num(m['trips_total']), 'bus trips'),
                 'fy25': fyf(2025), 'fy26': fyf(2026),
                 'top_trips': figure(t0['trips'], C.num(t0['trips']), 'trips'),
                 'top': figure(t0['fy2025'], C.usd(t0['fy2025'])),
                 'tot': figure(sp['totals'][2025], C.usd(sp['totals'][2025])),
                 'miles': figure(k['per_trip_miles'], C.num(k['per_trip_miles']), 'miles'),
                 'mrate': figure(k['years'][0]['trip_rate'], usd2(k['years'][0]['trip_rate'])),
                 'hours': figure(k['wait_hours'], C.num(k['wait_hours']), 'hours'),
                 'wrate': figure(k['years'][0]['wait_rate'], usd2(k['years'][0]['wait_rate'])),
                 'full': figure(k['trip_full'], usd2(k['trip_full'])),
                 'nowait': figure(k['trip_nowait'], usd2(k['trip_nowait'])),
                 'tnw': figure(m['trips_total_nowait'], C.num(m['trips_total_nowait']),
                               'trips')},
        basis='OUR ESTIMATE. Dollars from the district’s sport-by-sport workbook (stated), '
              'divided by a trip priced from the Dee Bus bid form’s FY2026 rates and its own '
              'estimate of 100 trips, 6,500 miles and four hours of waiting per trip.',
        allow=('100', '6,500'),
        not_shown='Nobody publishes a trip count. A sport that rides farther, or waits longer, '
                  'buys fewer trips for the same dollars; golf and cross country may ride '
                  'short buses. The FY2025 dollars were paid under the previous contract, whose '
                  'rates were requested and not delivered.',
    ))

    # 4. The contract fixes the price, and when it ends.
    rows.append(conclusion(
        id='contract-fixes-the-price', bearing='lever', kind='measured', figure='p28',
        claim='The bus contract already fixes %s’s regular-route price: %s for %s buses.'
              % (C.fy(2028), C.usd(y[2028]['regular']), C.num(N77 + N83)),
        so_what='A known %s rise. It ends June 2028; renewal, or the two priced option years, '
                'is the decision.' % C.pct(m['rises'][2028]),
        detail='Prices per bus per day are bid for every year: %s and %s in %s rising to %s '
               'and %s in %s, for %s 77-passenger and %s 83-passenger buses, %s days. The '
               '%s budget carries %s for the line, the contract’s second-year price to the '
               'dollar. The option years are priced at %s and %s.'
               % (rate(y[2026]['p77']), rate(y[2026]['p83']), C.fy(2026), rate(y[2028]['p77']),
                  usd2(y[2028]['p83']), C.fy(2028), C.num(N77), C.num(N83), C.num(DAYS),
                  C.fy(2027), C.usd(m['book']['regular']['fy27_balanced']),
                  C.usd(y[2029]['regular']), C.usd(y[2030]['regular'])),
        figures={'p28': figure(y[2028]['regular'], C.usd(y[2028]['regular'])),
                 'buses': figure(N77 + N83, C.num(N77 + N83), 'buses'),
                 'rise': figure(m['rises'][2028], C.pct(m['rises'][2028])),
                 'fy28': fyf(2028), 'fy26': fyf(2026), 'fy27': fyf(2027),
                 'a': figure(y[2026]['p77'], rate(y[2026]['p77'])),
                 'b': figure(y[2026]['p83'], rate(y[2026]['p83'])),
                 'c': figure(y[2028]['p77'], rate(y[2028]['p77'])),
                 'd': figure(y[2028]['p83'], usd2(y[2028]['p83'])),
                 'n77': figure(N77, C.num(N77), 'buses'), 'n83': figure(N83, C.num(N83), 'buses'),
                 'days': figure(DAYS, C.num(DAYS), 'days'),
                 'b27': figure(m['book']['regular']['fy27_balanced'],
                               C.usd(m['book']['regular']['fy27_balanced'])),
                 'o29': figure(y[2029]['regular'], C.usd(y[2029]['regular'])),
                 'o30': figure(y[2030]['regular'], C.usd(y[2030]['regular']))},
        allow=('77-passenger', '83-passenger', '2028'),
        basis='The Dee Bus bid form (Exhibit E), signed 27 December 2024, every rate checked '
              'against its printed totals; the agreement’s term; the district’s FY2027 budget '
              'book.',
        not_shown='The contract prices regular routes; it does not fix how many buses run — '
                  'the form lets the district add or drop up to two a year at the same unit '
                  'prices. The contract’s price is not what the town will pay: the line is '
                  'voted net of anything else that pays for it.',
    ))

    # 5. The 7.6%, what it is and what cannot be settled.
    rows.append(conclusion(
        id='the-seven-point-six', bearing='sizes', kind='measured', figure='step',
        claim='%s’s 7.6%% bus increase is the new contract’s first-year price over the old '
              'budget line.' % C.fy(2026),
        so_what='Whether it bought a price rise or an extra bus cannot be told without the old '
                'contract.',
        detail='The contract’s %s regular-route price is %s; the %s line was %s; the difference '
               'is %s. If the old line paid for the same %s buses it averaged %s a bus a day '
               'against %s now, and all of the rise is price. If it paid for %s, it averaged %s '
               'and the rise is a bus.'
               % (C.fy(2026), C.usd(y[2026]['regular']), C.fy(2025), C.usd(m['reg25']),
                  C.usd(m['step']), C.num(N77 + N83), usd2(m['fleet_a']), usd2(m['fy26_avg']),
                  C.num(N77 + N83 - 1), usd2(m['fleet_b'])),
        figures={'step': figure(m['step'], C.usd(m['step'])), 'fy26': fyf(2026),
                 'fy25': fyf(2025),
                 'p26': figure(y[2026]['regular'], C.usd(y[2026]['regular'])),
                 'b25': figure(m['reg25'], C.usd(m['reg25'])),
                 'n': figure(N77 + N83, C.num(N77 + N83), 'buses'),
                 'n1': figure(N77 + N83 - 1, C.num(N77 + N83 - 1), 'buses'),
                 'fa': figure(m['fleet_a'], usd2(m['fleet_a'])),
                 'fb': figure(m['fleet_b'], usd2(m['fleet_b'])),
                 'f26': figure(m['fy26_avg'], usd2(m['fy26_avg']))},
        allow=('7.6%',),
        basis='The district’s FY2026 budget overview (“Dee Bus 7.6% line increase = $69,300”); '
              'the contract’s FY2026 prices; the FY2025 general education transportation '
              'budget, budget to budget.',
        not_shown='The FY2025 rates and fleet were requested and not delivered. A district '
                  'presentation says eleven buses were in use; that is a statement, not a rate.',
    ))

    # 6. Special education transportation: the line that moves.
    lo = m['sped_low']
    over = m['recent_over']
    rows.append(conclusion(
        id='sped-transport-is-the-variable', bearing='sizes', kind='measured', figure='now',
        claim='Special education transportation spending rose from %s in %s to %s in %s.'
              % (C.usd(lo['sped']['spent']), C.fy(lo['fy']), C.usd(L['sped']['spent']),
                 C.fy(last)),
        so_what='It ran over its voted budget in %s; the district cites more vans and '
                'monitors.' % ' and '.join(C.fy(x['fy']) for x in over),
        detail='%s is the base because it is the last year before the 2020 school closures — our '
               'choice. The line came in under budget every year from %s to %s. Overruns: %s. '
               'The state’s circuit breaker paid back %s for out-of-district '
               'transportation in %s and %s in %s — never netted here, and it covers only '
               'children placed outside the district. The district’s FY2026 overview gives the '
               'line’s rise as a 7%% rate increase and more vans and monitors.'
               % (C.fy(lo['fy']), C.fy(m['sped_under_run'][0]), C.fy(m['sped_under_run'][-1]),
                  '; '.join('%s over in %s' % (C.usd(x['over']), C.fy(x['fy'])) for x in over),
                  C.usd(st['cb'][-2]['transport']), C.fy(st['cb'][-2]['fy']),
                  C.usd(st['cb'][-1]['transport']), C.fy(st['cb'][-1]['fy'])),
        figures=dict({'low': figure(lo['sped']['spent'], C.usd(lo['sped']['spent'])),
                      'now': figure(L['sped']['spent'], C.usd(L['sped']['spent'])),
                      'lofy': fyf(lo['fy']), 'fy': fyf(last),
                      'cb1': figure(st['cb'][-2]['transport'], C.usd(st['cb'][-2]['transport'])),
                      'cb2': figure(st['cb'][-1]['transport'], C.usd(st['cb'][-1]['transport'])),
                      'cbfy1': fyf(st['cb'][-2]['fy']),
                      'u0': fyf(m['sped_under_run'][0]), 'u1': fyf(m['sped_under_run'][-1])},
                     **{'o%d' % x['fy']: figure(x['over'], C.usd(x['over'])) for x in over},
                     **{'ofy%d' % x['fy']: fyf(x['fy']) for x in over}),
        allow=('7%', '2020'),
        basis='General fund special education transportation account, voted against spent at '
              'the close; DESE’s circuit breaker schedule, transportation column; the '
              'district’s FY2026 budget overview.',
        not_shown='The van contract is not in the archive, so how much of the rise is price, '
                  'routes, children or monitors cannot be split. The cause given is the '
                  'district’s; nothing here tests it.',
        see=[('/analysis/special-education-costs', 'Special education costs')],
    ))

    # 7. The fee, netted.
    rows.append(conclusion(
        id='fee-netted-from-the-line', bearing='lever', kind='measured', figure='net',
        claim='The %s bus line was voted %s under the contract price, then topped back up '
              'mid-year.' % (C.fy(2026), C.usd(m['netted'])),
        so_what='The Finance Committee was told the bus fee cut the line by that much; where '
                'the fees are booked is unstated.',
        detail='Voted %s; contract price %s; transfers of %s during the year brought the line '
               'to %s, all of it spent. Where the fee receipts landed is not stated anywhere; an '
               'account named SCH. CHOICE BUS FEE in the school choice fund took in %s in %s and '
               '%s in %s, after nothing in %s and %s.'
               % (C.usd(m['L']['regular']['budget']), C.usd(y[2026]['regular']),
                  C.usd(m['moved_back']), C.usd(m['L']['regular']['revised']),
                  usd2(st['fee'][2025]), C.fy(2025), usd2(st['fee'][2026]), C.fy(2026),
                  C.fy(2023), C.fy(2024)),
        figures={'net': figure(m['netted'], C.usd(m['netted'])), 'fy26': fyf(2026),
                 'voted': figure(m['L']['regular']['budget'], C.usd(m['L']['regular']['budget'])),
                 'price': figure(y[2026]['regular'], C.usd(y[2026]['regular'])),
                 'rev': figure(m['L']['regular']['revised'], C.usd(m['L']['regular']['revised'])),
                 'f25': figure(st['fee'][2025], usd2(st['fee'][2025])),
                 'f26': figure(st['fee'][2026], usd2(st['fee'][2026])),
                 'fy25': fyf(2025), 'fy23': fyf(2023), 'fy24': fyf(2024)},
        basis='MUNIS FY2026 year-end report, account 535025, original appropriation and '
              'transfers; the contract’s FY2026 price; Finance Committee minutes, 20 March '
              '2025; MUNIS fund 1308 account 437601.',
        not_shown='That the fund 1308 receipts are the bus fees is a hypothesis: the account '
                  'is named for school choice, and nothing published ties it to the fee. The '
                  'number of families who paid is not published.',
        see=[('/what-families-pay', 'What families pay')],
    ))

    # 8. FY2027: athletic buses cut, and the restoration plan.
    rows.append(conclusion(
        id='fy27-athletic-buses', bearing='lever', kind='measured', figure='restore',
        claim='%s’s budget cut athletic buses to %s; restoring high school buses was put at %s.'
              % (C.fy(2027), C.usd(m['fy27']['athletic']), C.usd(m['restore'])),
        so_what='The August plan: %s from the town and %s from the athletics fee fund.'
                % (C.usd(m['restore_town']), C.usd(m['restore_fund'])),
        detail='The balanced budget carried %s; the %s level-service budget had carried %s. The Superintendent told the '
               'School Committee on 26 August 2026 the lower figure came from scheduling '
               'competitions closer to Lunenburg, more home games and actual schedules. At %s '
               'contract prices %s is about %s of the bid form’s average trips — our estimate.'
               % (C.usd(m['fy27']['athletic']), C.fy(2027),
                  C.usd(m['book']['athletic']['fy27_level_service']), C.fy(2027),
                  C.usd(m['restore']), C.num(m['restore_trips'])),
        figures={'zero': figure(m['fy27']['athletic'], C.usd(m['fy27']['athletic'])),
                 'restore': figure(m['restore'], C.usd(m['restore'])),
                 'town': figure(m['restore_town'], C.usd(m['restore_town'])),
                 'fund': figure(m['restore_fund'], C.usd(m['restore_fund'])),
                 'fy27': fyf(2027),
                 'ls': figure(m['book']['athletic']['fy27_level_service'],
                              C.usd(m['book']['athletic']['fy27_level_service'])),
                 'tr': figure(m['restore_trips'], C.num(m['restore_trips']), 'trips')},
        allow=('26 August 2026',),
        basis='The district’s FY2027 budget book, balanced and level-service scenarios; School '
              'Committee minutes, 26 August 2026, as minuted; the contract’s FY2027 rates for '
              'our trip estimate.',
        not_shown='The $58,880 is the Superintendent’s figure as minuted, not a contract or a '
                  'ledger amount, and whether Special Town Meeting funded it is not in this '
                  'archive’s ledgers yet. Middle school buses are not in it.',
    ))
    return emit(ID, rows)


# --------------------------------------------------------------------- sources

DESE_NAME = 'Massachusetts Department of Elementary and Secondary Education'


def sources():
    man = {r['key']: r for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    spec = [
        ('contracts/pdf/dee-bus-bid-proposal-rates-fy26-fy30.pdf',
         'Lunenburg Public Schools / Dee Bus Service, Inc.', 'quoted',
         'Exhibit E: Bid Proposal, pages 24-29 of the Invitation for Bids, filled in and signed '
         '12-27-24; delivered as “Daily Transportation Rates 25-28.pdf”. Records request of '
         '9 October 2026 (sources/contracts/PROVENANCE-records-request-2026-10-09.md)'),
        ('contracts/pdf/dee-bus-transportation-agreement-fy26-fy28.pdf',
         'Lunenburg Public Schools / Dee Bus Service, Inc.', 'quoted',
         'the executed agreement: term 1 July 2025 to 30 June 2028, two optional one-year '
         'extensions, subject to appropriation'),
        ('contracts/pdf/dee-bus-first-amendment-2025.pdf',
         'Lunenburg Public Schools / Dee Bus Service, Inc.', 'quoted',
         'the First Amendment, which changes only the bonds'),
        ('contracts/pdf/dee-bus-performance-and-payment-bond-fy27.pdf',
         'United Casualty and Surety Insurance Company', 'quoted',
         'the FY2027 performance and payment bonds'),
        ('town-ledgers/expenses/glytdbud-expense-fy2026-p13-gf-school.xlsx',
         'Town of Lunenburg — Town Accountant (MUNIS)', 'munis_school_ytd',
         'the school general fund year-end budget report, FY2026 period 13; FY2023 to FY2025 '
         'beside it under the same name. Records request '
         '(sources/town-ledgers/expenses/PROVENANCE-fy2023-fy2026-p13-school.md)'),
        ('town-ledgers/expenses/glytdbud-expense-fy2026-p13-special-school.xlsx',
         'Town of Lunenburg — Town Accountant (MUNIS)', 'munis_school_ytd',
         'the school special funds year-end report, FY2026 period 13: fund 1308 (school choice) '
         'and fund 1301 (athletics); FY2023 to FY2025 beside it'),
        ('budget-workbooks/finance-committee/fy26-budget/general-fund-budget-vs-actuals-history.xlsx',
         'Lunenburg Finance Committee', 'gl-history.csv',
         'the general fund original budget, revised budget and actual, every account, '
         'FY2010-FY2025, assembled from MUNIS exports; used for FY2010-FY2022 because its '
         'transportation rows tie to the MUNIS reports'),
        ('budget-workbooks/fy27-proposals.xlsx', 'Lunenburg Public Schools', 'lps_budget_lines',
         'the district’s FY2027 budget workbook: every scenario, with the comments column'),
        ('district-budget/docs/school-department-fy26-budget-overview.pdf',
         'Lunenburg Public Schools', 'quoted',
         'the FY2026 budget overview: the 7.6%, the vans, the athletics line'),
        ('district-budget/docs/sc-meetings/2024-2025-transportation-fee-proposal.pdf',
         'Lunenburg Public Schools', 'quoted',
         'Transportation: Bus Fee Proposal, presented to the School Committee in 2024-2025'),
        ('town-ledgers/account-details/athletics-by-sport-fy2024-fy2026.xlsx',
         'Lunenburg Public Schools', 'athletics_by_sport',
         'the district’s sport-by-sport athletics workbook (publisher’s name “Copy of '
         'Athletics 24.25 (1).xlsx”), received by records request 17 June 2026. Hand-assembled'),
        ('budget-workbooks/finance-committee/fy26-budget/department-presentations/'
         'lunenburg-public-schools/athletics-costs-1.xlsx', 'Lunenburg Public Schools',
         'athletics_fincom', 'Athletics Costs (1).xlsx, a second per-sport sheet, from the '
         'Finance Committee’s FY2026 budget files. Hand-assembled'),
        ('state-dese/district-expenditures-by-function.xlsx', DESE_NAME,
         'dese_function_expenditure', 'End of Year Financial Report, function 3300 and '
         'out-of-district transportation, general fund'),
        ('state-dese/dese-circuit-breaker.xlsx', DESE_NAME, 'dese_circuit_breaker',
         'the circuit breaker reimbursement schedule, transportation column, by year of payment'),
        ('correspondence/2025-05-bus-fees-superintendent.txt', 'Lunenburg Public Schools',
         'quoted', 'the Superintendent’s May 2025 bus fee email: the FY2026 fee schedule'),
        ('correspondence/2026-08-17-bus-routes-and-fees-superintendent.txt',
         'Lunenburg Public Schools', 'quoted',
         'the Superintendent’s August 2026 email: the FY2027 routes and fees; the route list '
         'excludes special education vans'),
    ]
    out = []
    for key, pub, tbl, note in spec:
        r = man.get(key)
        if not r:
            fail('%s is not in archive-manifest.csv' % key)
        out.append(dict(path='sources/' + key, sha256=r.get('sha256', ''),
                        bytes=int(r.get('bytes') or 0), url=r.get('upstream', ''),
                        docs_url='/docs/' + key, filename=key.split('/')[-1], table=tbl,
                        publisher=pub, note=note))
    return out


# --------------------------------------------------------------------- the payload

def payload(m, rows):
    L, last, k, sp, st = m['L'], m['last'], m['contract'], m['sports'], m['state']
    by_year = []
    for r in m['ledger']:
        d = dict(fy=r['fy'], source=r['source'])
        for c in CAT_NAME:
            d[c + '_budget'] = r[c]['budget']
            d[c + '_spent'] = r[c]['spent']
        d['school_budget'] = r['school_budget']
        d['school_spent'] = r['school_spent']
        d['all_budget'] = r['all_budget']
        d['all_spent'] = r['all_spent']
        d['athletic_share_spent'] = m['share'][r['fy']]['spent']
        d['athletic_share_budget'] = m['share'][r['fy']]['budget']
        by_year.append(d)
    b = m['book']
    fy27 = dict(fy=2027, source='budget book (balanced)')
    for c in CAT_NAME:
        fy27[c + '_budget'] = b[c]['fy27_balanced']
        fy27[c + '_spent'] = None
    fy27['school_budget'] = sum(b[c]['fy27_balanced'] for c in SCHOOL_DAY)
    fy27['school_spent'] = None
    fy27['all_budget'] = sum(b[c]['fy27_balanced'] for c in CAT_NAME)
    fy27['all_spent'] = None
    by_year.append(fy27)

    ath = []
    for r in m['ledger']:
        h = sp['revolving'].get(r['fy'])
        ath.append(dict(fy=r['fy'], line_budget=r['athletic']['budget'],
                        line_spent=r['athletic']['spent'],
                        sheet_total=sp['totals'].get(r['fy']),
                        fund_stated=h['amount'] if h and h['basis'] == 'actual' else None))
    ath.append(dict(fy=2027, line_budget=b['athletic']['fy27_balanced'], line_spent=None,
                    sheet_total=None, fund_stated=None))

    reg_line = [dict(fy=r['fy'], budget=r['regular']['budget'], spent=r['regular']['spent'],
                     contract=None) for r in m['ledger']]
    reg_line.append(dict(fy=2027, budget=b['regular']['fy27_balanced'], spent=None,
                         contract=None))
    for c in k['years']:
        hit = [x for x in reg_line if x['fy'] == c['fy']]
        if hit:
            hit[0]['contract'] = c['regular']
        else:
            reg_line.append(dict(fy=c['fy'], budget=None, spent=None, contract=c['regular'],
                                 optional=c['optional']))
    for x in reg_line:
        x.setdefault('optional', False)

    cbm = {x['fy']: x['transport'] for x in st['cb']}
    sped = [dict(fy=r['fy'], budget=r['sped']['budget'], spent=r['sped']['spent'],
                 cb_transport=cbm.get(r['fy'])) for r in m['ledger']]
    sped.append(dict(fy=2027, budget=b['sped']['fy27_balanced'], spent=None, cb_transport=None))

    sports = [dict(season=r['season'], level=r['level'], sport=r['sport'],
                   label='%s %s · %s' % (r['level'], r['sport'], r['season']),
                   fy2024=r['fy2024'], fy2025=r['fy2025'], trips=r['trips'],
                   trips_nowait=r['trips_nowait']) for r in sp['rows']]

    return dict(
        generated_by='scripts/build_transportation.py',
        about='What Lunenburg’s school buses cost, by year since %s: the school day against '
              'athletics, budgeted and spent; athletics by sport; and what the Dee Bus contract '
              'fixes through %s.' % (C.fy(m['first']), C.fy(2028)),
        grain='DOLLARS, school general fund, the budget voted before the year beside what was '
              'spent at its close (expended plus still committed), %s; never added together. '
              'Per-sport dollars are the district’s hand-assembled sheets (stated). Every trip '
              'count is OUR ESTIMATE.' % C.fyspan(m['first'], last),
        stats=[
            dict(value=C.usd(L['all_spent']),
                 label='spent on school transportation in %s — every general fund line: '
                       'regular routes, special education, athletics, band' % C.fy(last),
                 tone='var(--series-cost)'),
            dict(value=C.pct(m['share'][last]['spent']),
                 label='of that was athletic buses — %s of spending; %s of the budget voted'
                       % (C.usd(L['athletic']['spent']), C.pct(m['share'][last]['budget']))),
            dict(value=C.usd(m['ystep'][2028]['regular']),
                 label='the contract’s fixed %s price for the %s regular-route buses, '
                       '%s days' % (C.fy(2028), C.num(N77 + N83), C.num(DAYS))),
            dict(value='≈%s trips' % C.num(m['trips_total']),
                 label='what %s athletic bus spending buys at the new contract’s prices — '
                       'OUR ESTIMATE' % C.fy(2025)),
        ],
        conclusions=rows,
        by_year=by_year,
        by_year_keys=[dict(key=c, name=CAT_NAME[c]) for c, _, _, _ in CATS],
        athletics=ath,
        sports=sports,
        sport_seasons=sp['seasons'],
        sport_compare=sp['compare'],
        contract=dict(years=k['years'], regular_line=sorted(reg_line, key=lambda x: x['fy']),
                      grand_total=k['grand'], buses=dict(p77=N77, p83=N83), days=DAYS,
                      trip_full=k['trip_full'], trip_nowait=k['trip_nowait'],
                      per_trip_miles=k['per_trip_miles'], wait_hours=k['wait_hours'],
                      bond=k['bond']),
        sped=sped,
        dese=st['dese'],
        circuit_breaker=st['cb'],
        bus_fee_account=[dict(fy=fy, receipts=v) for fy, v in sorted(st['fee'].items())],
        said=[dict(key=q['key'], board=q['board'], date=q['date'], quote=q['quote'],
                   why=q['why'], cite=q['cite']) for q in m['quotes']],
        not_established=[
            'How many athletic bus trips any sport took, or what any one trip cost. Every trip '
            'figure here is dollars divided by the bid form’s own average trip.',
            'The FY2025 Dee Bus rates and fleet, so whether FY2026’s 7.6% was price or a bus.',
            'Where the student bus fees are booked; the school choice fund account named for a '
            'bus fee is a candidate, not an established destination.',
            'What the special education van contract charges, and for how many vans, monitors '
            'and routes.',
            'How many children ride the buses, or how many families paid the fee.',
            'How much of athletic transportation the athletic fee fund paid in FY2025 and '
            'FY2026; it books transportation inside one purchase-of-service account with '
            'officials, uniforms and ice time.',
            'Why DESE’s FY2025 transportation figure differs from the town ledger.',
        ],
        gaps=[dict(key=k_, what=w) for k_, w in m['gaps'].items()],
        sources=sources(),
    )


# --------------------------------------------------------------------- markdown

def render_md(m, rows):
    L, last, k, sp, st, b = m['L'], m['last'], m['contract'], m['sports'], m['state'], m['book']
    y = m['ystep']
    w = []
    a = w.append
    byfy = {r['fy']: r for r in m['ledger']}

    a('# School transportation: what the buses cost, and who pays\n\n')
    a('**What Lunenburg spends on school buses — the school day against athletics, budgeted and '
      'spent, every year since %s — athletics sport by sport, and what the new Dee Bus '
      'contract fixes through %s.**\n\n' % (C.fy(m['first']), C.fy(2028)))
    a('![Two bars a year, %s to %s: the transportation budget voted before the year (pale) and '
      'what was spent at its close (solid), each split into regular routes, special education, '
      'athletics and band. Athletics is the thin top slice: %s of spending in %s. %s shows '
      'the budget only.](charts/transportation-schools-athletics.svg)\n\n'
      % (C.fy(m['first']), C.fy(2027), C.pct(m['share'][last]['spent']), C.fy(last),
         C.fy(2027)))

    # ---- the short version: the conclusions, in prose
    a('## The short version\n\n')
    for c in rows:
        tag = ' *(our estimate — a hypothesis, not a measurement)*' if c['kind'] == 'hypothesis' else ''
        a('**%s**%s %s\n\n' % (c['claim'], tag, c['so_what']))
    a('Every line on this page is a general fund budget line, and a budget line is **net**: it '
      'is what the town raises after anything else that pays for the thing — bus fees, the '
      'athletic fee fund, state reimbursement — has been taken off (rule 11). None of those is '
      'netted into any figure here; each has its own column.\n\n')
    a('---\n\n')

    # ---- the charts
    a('## The charts\n\n')
    a('![Athletic transportation by year: the general fund line voted and spent, beside the '
      'full cost where a district document states one — the fee fund’s share FY2014 to FY2017 '
      'and the district’s by-sport sheet for FY2024 and FY2025.](charts/transportation-athletics.svg)\n\n')
    a('![Athletic transportation by sport, FY2024 and FY2025, from the district’s by-sport '
      'workbook, grouped by season. Hover a bar for the trip estimate.](charts/transportation-sports.svg)\n\n')
    a('![Regular-route buses: the general fund line voted each year, and the price the Dee Bus '
      'contract fixes for FY2026 to FY2028, with the two optional years.](charts/transportation-contract.svg)\n\n')
    a('![Special education transportation: voted and spent each year, with the circuit '
      'breaker’s transportation reimbursement beside it, never netted.](charts/transportation-sped.svg)\n\n')

    # ---- 1. schools vs athletics
    a('## 1. The school day against athletics\n\n')
    a('### In plain terms\n\n')
    a('Almost all of what the schools spend on buses is the school day: the eleven Dee Bus '
      'buses on regular routes and the special education vans. Athletic buses were %s of spending in %s and '
      'have been between %s and %s every year since %s. That is the general fund only — '
      'athletic buses the fee fund paid for are not in it (section 2).\n\n'
      % (C.pct(m['share'][last]['spent']), C.fy(last),
         C.pct(m['share'][m['lo_share']['fy']]['spent']),
         C.pct(m['share'][m['hi_share']['fy']]['spent']), C.fy(m['first'])))
    a('### The evidence\n\n')
    a('Budget is the original appropriation voted before the year. Spent is expended plus '
      'still committed at the year-end close. **The two are side by side and never combined**: '
      'the athletic share is computed once on spending and once on budget.\n\n')
    a('| FY | school day, budget | school day, spent | athletic, budget | athletic, spent | '
      'band, budget | band, spent | athletic share of spending | athletic share of budget | source |\n')
    a('|---|---:|---:|---:|---:|---:|---:|---:|---:|---|\n')
    for r in m['ledger']:
        a('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |\n' % (
            C.fy(r['fy']), C.usd(r['school_budget']), C.usd(r['school_spent']),
            C.usd(r['athletic']['budget']), C.usd(r['athletic']['spent']),
            C.usd(r['band']['budget']), C.usd(r['band']['spent']),
            C.pct(m['share'][r['fy']]['spent']), C.pct(m['share'][r['fy']]['budget']),
            'MUNIS' if r['source'] == 'munis' else 'FinCom workbook'))
    a('| %s | %s | — | %s | — | %s | — | — | %s | budget book, balanced |\n\n' % (
        C.fy(2027), C.usd(sum(b[c]['fy27_balanced'] for c in SCHOOL_DAY)),
        C.usd(b['athletic']['fy27_balanced']), C.usd(b['band']['fy27_balanced']),
        C.pct(pct1(b['athletic']['fy27_balanced'],
                   sum(b[c]['fy27_balanced'] for c in CAT_NAME)))))
    a('The school day split, %s: regular routes voted %s and spent %s; special education '
      'voted %s and spent %s. Band trips were %s spent against %s voted.\n\n'
      % (C.fy(last), C.usd(L['regular']['budget']), C.usd(L['regular']['spent']),
         C.usd(L['sped']['budget']), C.usd(L['sped']['spent']), C.usd(L['band']['spent']),
         C.usd(L['band']['budget'])))
    bq = [q for q in m['quotes'] if q['key'] == 'band'][0]
    a('**Band and music trips in %s.** The balanced budget carries %s for both band '
      'transportation lines. The Finance Committee was told on 26 March 2026: *“%s”* '
      '([minutes](%s)). The book and the minute differ, and the record here does not say which '
      'held.\n\n' % (C.fy(2027), C.usd(b['band']['fy27_balanced']), bq['quote'], bq['cite']))
    a('**A second route.** DESE’s End of Year Financial Report gives the same school-day '
      'spending as in-district transportation (function 3300) plus out-of-district '
      'transportation, general fund. It equals the town ledger’s regular plus special '
      'education lines to the dollar in %s. ' % ', '.join(C.fy(x) for x in st['dese_ties']))
    near = [x['fy'] for x in st['dese'] if x['diff'] is not None and 1 < abs(x['diff']) <= 500]
    if near:
        a('Within %s in %s. ' % (C.usd(max(abs(x['diff']) for x in st['dese'] if x['fy'] in near)),
                                 ', '.join(C.fy(f) for f in near)))
    dd = {x['fy']: x['diff'] for x in st['dese'] if x['diff'] is not None}
    pairs = [f for f in dd if f + 1 in dd and abs(dd[f]) > 500 and abs(dd[f] + dd[f + 1]) <= 1]
    for f in pairs:
        a('%s and %s differ by %s in opposite directions, so the two years together tie; one '
          'payment booked in different years by the two would look like that (a hypothesis). '
          % (C.fy(f), C.fy(f + 1), C.usd(abs(dd[f]))))
    rest = [f for f in sorted(dd) if abs(dd[f]) > 500 and f not in pairs
            and f - 1 not in pairs and f != 2025]
    if rest:
        a('%s differ by more, in both directions. ' % ', '.join(C.fy(f) for f in rest))
    d25 = [x for x in st['dese'] if x['fy'] == 2025]
    if d25 and d25[0]['diff']:
        a('In %s DESE reports %s against the ledger’s %s, %s apart; nothing published here '
          'explains the difference (registered: *%s*).'
          % (C.fy(2025), C.usd(d25[0]['total']), C.usd(d25[0]['ledger']),
             C.usd(abs(d25[0]['diff'])), m['gaps']['dese-fy25']))
    a(' DESE splits in-district from out-of-district, which is not the town’s regular / '
      'special education split, so only the sum is compared.\n\n')
    a('### What this does not show\n\n')
    a('- **What athletic buses cost in all.** The general fund line is net of the athletic fee '
      'fund (rule 11), and the fund paid more of athletic transportation than the town did in '
      'every year a district document reports both as actual, FY2014 to FY2017 (section 2).\n')
    a('- **Cost per rider.** No count of riders is published (registered: *%s*). The only '
      'count in the record is %s.\n'
      % (m['gaps']['riders'], '%s bus requests in June 2025, %s of them unpaid at the time'
         % (C.num(m['requests']), C.num(m['unpaid']))))
    a('- **Monty Tech.** Students at the regional vocational school ride its buses; Lunenburg '
      'pays for them inside the Monty Tech assessment, whose transportation-and-operating part '
      'is not split. It is a town appropriation, not a school line, and is not on this page.\n\n')

    # ---- 2. athletics
    a24 = byfy[2024]['athletic']
    a25 = byfy[2025]['athletic']
    a('## 2. Athletic transportation: what it costs and who has paid\n\n')
    a('### In plain terms\n\n')
    a('The athletic bus line in the town budget used to be a fraction of what athletic buses '
      'cost; the athletic fee fund — what families pay to play — covered the rest. In %s the '
      'district’s own sheet put the cost at %s while the voted line was %s. From %s the line '
      'was set to carry the full cost, and the district said so at the time. In %s the '
      'balanced budget cut it to %s.\n\n'
      % (C.fy(2024), C.usd(sp['totals'][2024]), C.usd(a24['budget']), C.fy(2026), C.fy(2027),
         C.usd(b['athletic']['fy27_balanced'])))
    a('### The evidence\n\n')
    a('| FY | general fund line, budget | general fund line, spent | fee fund, stated by the district | full cost, district by-sport sheet (stated) |\n')
    a('|---|---:|---:|---:|---:|\n')
    for r in m['ledger']:
        h = sp['revolving'].get(r['fy'])
        if r['fy'] < 2014 and not h:
            continue
        a('| %s | %s | %s | %s | %s |\n' % (
            C.fy(r['fy']), C.usd(r['athletic']['budget']), C.usd(r['athletic']['spent']),
            (C.usd(h['amount']) + (' (budget)' if h['basis'] == 'budget' else ''))
            if h else '—',
            C.usd(sp['totals'][r['fy']]) if r['fy'] in sp['totals'] else '—'))
    a('| %s | %s | — | — | — |\n\n' % (C.fy(2027), C.usd(b['athletic']['fy27_balanced'])))
    a('The fee fund figures for FY2014 to FY2019 are the district’s FY19 athletics budget '
      'document (`district-budget/docs/fy19-proposed-athletics-budget.pdf`), actual to FY2017. '
      'Nothing published states the fund’s share after that; it books transportation inside one '
      'purchase-of-service account with officials, uniforms and ice time (registered: *%s*).\n\n'
      % m['gaps']['net-revolving'])
    a('**The district’s own words.** Its FY2026 budget overview, on the athletics line: *“%s”*. '
      'At the School Committee on 12 March 2025, a member: *“%s”* ([minutes](%s)).\n\n'
      % (OVERVIEW_QUOTES['athletics'],
         [q for q in m['quotes'] if q['key'] == 'not-200'][0]['quote'],
         [q for q in m['quotes'] if q['key'] == 'not-200'][0]['cite']))
    rq = [q for q in m['quotes'] if q['key'] == 'reclass'][0]
    a('**%s, the year it moved.** The line was voted at %s and %s was transferred in during the '
      'year, to %s, all of it spent. The School Committee approved the transfer on 16 April '
      '2025: *“%s”* ([minutes](%s)).\n\n'
      % (C.fy(2025), C.usd(a25['budget']), C.usd(m['reclass']), C.usd(a25['revised']),
         rq['quote'], rq['cite']))
    a('**%s, the new contract’s first athletic year**, the general fund line spent %s and had '
      '%s still committed at the close, %s in all against %s voted. At the contract’s prices '
      'the amount paid out is about %s of the bid form’s average trips, or %s counting what '
      'was still committed — our estimate (section 3).\n\n'
      % (C.fy(2026), C.usd(L['athletic']['expended']), C.usd(L['athletic']['committed']),
         C.usd(L['athletic']['spent']), C.usd(L['athletic']['budget']),
         C.num(m['trips26']), C.num(m['trips26_all'])))
    a('### What this does not show\n\n')
    a('- **Whether teams rode more or less.** Dollars moved between two payers; no trip count '
      'is published for any year (registered: *%s*).\n' % m['gaps']['trips'])
    a('- **That the sheet is right.** It is assembled by hand, and the district has not stood '
      'behind any per-sport figure (registered: *%s*).\n\n' % m['gaps']['sport-cost'])

    # ---- 3. per sport
    a('## 3. Sport by sport, and what the dollars buy in trips\n\n')
    a('### In plain terms\n\n')
    a('In %s no single sport’s buses cost more than %s. The five biggest together were %s of '
      'the %s total. Priced at the new contract’s rates, the whole %s total buys about %s '
      'trips of the kind the bid form assumes — **our estimate**, not a count.\n\n'
      % (C.fy(2025), C.usd(m['top'][0]['fy2025']), C.usd(m['top5']), C.usd(sp['totals'][2025]),
         C.fy(2025), C.num(m['trips_total'])))
    a('### The evidence\n\n')
    a('From the district’s sport-by-sport workbook; the cell is the workbook’s own. **Trips are '
      'OUR ESTIMATE**: %s dollars divided by %s, the bid form’s average trip at %s prices '
      '(%s miles at %s a mile plus %s hours of waiting at %s an hour). The second trip column '
      'assumes no waiting, %s a trip, and is the ceiling.\n\n'
      % (C.fy(2025), usd2(k['trip_full']), C.fy(2026), C.num(k['per_trip_miles']),
         usd2(k['years'][0]['trip_rate']), C.num(k['wait_hours']),
         usd2(k['years'][0]['wait_rate']), usd2(k['trip_nowait'])))
    a('| season | level | sport | %s | %s | trips, %s — OUR ESTIMATE | trips with no waiting — OUR ESTIMATE |\n'
      % (C.fy(2024), C.fy(2025), C.fy(2025)))
    a('|---|---|---|---:|---:|---:|---:|\n')
    for r in sp['rows']:
        a('| %s | %s | %s | %s | %s | %s | %s |\n' % (
            r['season'], r['level'], r['sport'],
            usd2(r['fy2024']) if r['fy2024'] is not None else '—',
            usd2(r['fy2025']) if r['fy2025'] is not None else '—',
            C.num(r['trips']) if r['trips'] else '—',
            C.num(r['trips_nowait']) if r['trips_nowait'] else '—'))
    a('| **all** | | | **%s** | **%s** | **%s** | **%s** |\n\n'
      % (usd2(sp['totals'][2024]), usd2(sp['totals'][2025]), C.num(m['trips_total']),
         C.num(m['trips_total_nowait'])))
    a('**Season totals against the workbook’s own.** ')
    bad = [s for s in sp['seasons'] if not s['ties']]
    good = [s for s in sp['seasons'] if s['ties']]
    a('%s of %s season totals the workbook prints equal the sum of its own rows. ' %
      (C.num(len(good)), C.num(len(sp['seasons']))))
    for s in bad:
        a('%s %s prints %s in cell %s while its rows sum to %s; this page uses the rows. '
          % (s['season'], C.fy(s['fy']),
             usd2(s['printed']) if s['printed'] is not None else 'nothing',
             s['cell'], usd2(s['rows'])))
    a('\n\n**A second district sheet disagrees.** The Finance Committee’s copy of *Athletics '
      'Costs (1).xlsx* prints transportation for %s sport-years that can be matched to the '
      'workbook; %s agree to the cent and %s do not. Both are hand-built; neither is a '
      'ledger (rule 13a). The ones that differ:\n\n'
      % (C.num(len(sp['compare'])), C.num(m['agree']), C.num(len(sp['compare']) - m['agree'])))
    a('| FY | sport | by-sport workbook | Finance Committee copy |\n|---|---|---:|---:|\n')
    for c in sp['compare']:
        if not c['agree']:
            a('| %s | %s | %s | %s |\n' % (C.fy(c['fy']), c['name'], usd2(c['workbook']),
                                          usd2(c['fincom'])))
    a('\n**One trip, priced.** On 4 March 2026 a teacher told the School Committee a class '
      'field trip would cost *“%s”*: one Dee Bus trip under the new contract, between this '
      'page’s no-waiting and four-hour prices of %s and %s ([minutes](%s)).\n\n'
      % (usd2(m['field_trip']), usd2(k['trip_nowait']), usd2(k['trip_full']),
         [q for q in m['quotes'] if q['key'] == 'field-trip'][0]['cite']))
    a('### What this does not show\n\n')
    a('- **A count of trips.** The estimate assumes every trip is the bid form’s average: %s '
      'miles and %s hours of waiting. Trips differ — a golf match and a football game are not '
      'the same bus — so a sport’s estimate is a scale, not its schedule.\n'
      % (C.num(k['per_trip_miles']), C.num(k['wait_hours'])))
    a('- **The prices actually paid in %s.** Those dollars were paid under the previous '
      'contract, whose rates were requested on 9 October 2026 and not delivered. If they were '
      'lower than %s’s, every trip estimate here is too low.\n' % (C.fy(2025), C.fy(2026)))
    a('- **The bid form’s own arithmetic.** Its trip lines multiply a trip count by the rate by '
      'a mileage figure (%s × rate × %s and so on); the mileage figures sum to %s, not the '
      '%s its estimate states. The subtotal is a quantity for comparing bids, not a forecast, '
      'and this page uses only the stated average trip.\n\n'
      % (C.num(TRIP_ROWS[0][0]), C.num(TRIP_ROWS[0][1]), C.num(k['form_mile_rows']),
         C.num(k['form_miles'])))

    # ---- 4. the contract
    a('## 4. The Dee Bus contract: what is fixed, and what the 7.6% was\n\n')
    a('### In plain terms\n\n')
    a('The district signed a three-year contract with Dee Bus Service for 1 July 2025 to 30 '
      'June 2028, with two optional one-year extensions. It fixes a price **per bus per day** '
      'for every year in advance, so the regular-route cost for %s is already known: %s for '
      'eleven buses for %s days. The district bid it under the state procurement law, to be '
      'awarded on the lowest three-year total, and the %s budget carries the contract’s price to the dollar — the planning '
      'number a board can start from rather than estimate.\n\n'
      % (C.fy(2028), C.usd(y[2028]['regular']), C.num(DAYS), C.fy(2027)))
    a('### The evidence\n\n')
    a('Every rate below was read off the scanned bid form and checked two ways on every build: '
      'against the scan’s text layer where it is legible, and by recomputing every subtotal '
      'and footing it to the year totals and the Grand Total the form prints, %s.\n\n'
      % usd2(k['grand']))
    a('| year | 77-passenger, per bus per day | 83-passenger | regular routes: %s + %s buses × %s days | trip rate (per mile) | waiting, per hour | year total as printed | bid form page |\n'
      % (C.num(N77), C.num(N83), C.num(DAYS)))
    a('|---|---:|---:|---:|---:|---:|---:|---|\n')
    for c in k['years']:
        a('| %s%s | %s | %s | %s | %s | %s | %s | p%d (IFB p%d) |\n' % (
            C.fy(c['fy']), ' (optional)' if c['optional'] else '', usd2(c['p77']),
            usd2(c['p83']), usd2(c['regular']), usd2(c['trip_rate']), usd2(c['wait_rate']),
            usd2(c['total']), c['pdf_page'], c['form_page']))
    a('\nThe regular-route price rises %s into %s and %s into %s, then %s and %s in the '
      'optional years. The form allows the fleet to move by up to two buses a year at the same '
      'unit prices. The %s performance bond is %s.\n\n'
      % (C.pct(m['rises'][2027]), C.fy(2027), C.pct(m['rises'][2028]), C.fy(2028),
         C.pct(m['rises'][2029]), C.pct(m['rises'][2030]), C.fy(2027), usd2(k['bond'])))
    early = b['early']['general ed transportation']
    a('**The budget against the contract, budget to budget.** %s voted %s for the line. %s was '
      'voted at %s, %s below the contract price, and transfers brought it to %s (section 5). '
      'An earlier %s projection (`%s`) carried %s; the balanced budget carried %s, the '
      'contract’s second-year price exactly.\n\n'
      % (C.fy(2025), C.usd(m['reg25']), C.fy(2026), C.usd(L['regular']['budget']),
         C.usd(m['netted']), C.usd(L['regular']['revised']), C.fy(2027), early[1],
         C.usd(early[0]), C.usd(b['regular']['fy27_balanced'])))
    old = [r for r in m['ledger'] if r['fy'] in (2023, 2024)]
    cq = [q for q in m['quotes'] if q['key'] == 'contracts-asked'][0]
    a('**The old contract’s last years ran over.** The regular-route line spent %s against %s '
      'voted. The district’s fee proposal states that *“%s”* — one '
      'possible reason, offered as a hypothesis; nothing here tests it. On 14 March 2024 a '
      'Finance Committee member asked for the contracts: *“%s”* ([minutes](%s)).\n\n'
      % (' and '.join('%s in %s' % (C.usd(r['regular']['spent']), C.fy(r['fy'])) for r in old),
         ' and '.join(C.usd(r['regular']['budget']) for r in old), POLICY_QUOTE, cq['quote'],
         cq['cite']))
    a('**The 7.6%%.** The district’s FY2026 overview prints *“%s”*. The contract’s first-year '
      'price, %s, less the %s budget, %s, is %s — %s of it. So the 7.6%% is a **line** '
      'increase: the new contract’s price over the old budget. The old price per bus is not '
      'known, and the same %s fits two fleets:\n\n'
      % (OVERVIEW_QUOTES['dee'], C.usd(y[2026]['regular']), C.fy(2025), C.usd(m['reg25']),
         C.usd(m['step']), C.pct(pct1(m['step'], m['reg25']), 2), C.usd(m['reg25'])))
    a('- *Hypothesis A, the same %s buses:* %s averaged %s a bus a day against %s’s %s — all of '
      'the 7.6%% is price.\n' % (C.num(N77 + N83), C.fy(2025), usd2(m['fleet_a']), C.fy(2026),
                                 usd2(m['fy26_avg'])))
    a('- *Hypothesis B, %s buses:* %s averaged %s a bus a day, more than the new 77-passenger '
      'price — the rise is the eleventh bus.\n\n' % (C.num(N77 + N83 - 1), C.fy(2025),
                                                    usd2(m['fleet_b'])))
    a('The record leans to A, as a statement rather than a count: a district presentation '
      'filed under 2024-2025 says *“%s”*. What would settle it is registered: '
      '*%s*.\n\n' % (ELEVEN_QUOTE, m['gaps']['rates']))
    a('### What this does not show\n\n')
    a('- **What was paid.** A contract prices a fleet; the ledger shows %s spent the line’s '
      'revised budget exactly, %s. That is an actual and enters no calculation above.\n'
      % (C.fy(2026), C.usd(L['regular']['spent'])))
    a('- **Special education.** The contract covers regular routes and trip buses; the '
      'August 2026 route list *“does not include Van Pool Special Education bussing”*.\n')
    a('- **How many bids were received.** The rest of the Invitation for Bids was not in the '
      'delivery.\n\n')

    # ---- 5. what pays for it
    a('## 5. What pays for it: the fee, the fee fund, the state\n\n')
    a('### In plain terms\n\n')
    a('Four things besides the town’s budget touch school transportation, and none of them '
      'shows in a budget line. A **bus fee** started in %s — %s for one child and %s for two '
      'or more, free or reduced for families who qualify. The **athletic fee fund** has paid '
      'part of athletic buses. The state’s **circuit breaker** pays back part of the cost of '
      'transporting children placed out of district. And Lunenburg receives **no regional '
      'transportation reimbursement**, because it is not a regional district.\n\n'
      % (C.fy(2026), C.usd(m['fees']['one']), C.usd(m['fees']['family'])))
    a('### The evidence\n\n')
    a('**The fee, netted from the line.** On 20 March 2025 the Finance Committee was told: '
      '*“%s”* ([minutes](%s)). The %s regular-route line was voted at %s, %s below the '
      'contract’s %s, and %s was transferred in during the year. The district’s FY2027 '
      'workbook asks the same question in its comments column beside the line: *“%s”* (row '
      '%d). The %s balanced figure equals the contract price, so it is not netted.\n\n'
      % ([q for q in m['quotes'] if q['key'] == 'fee-11000'][0]['quote'],
         [q for q in m['quotes'] if q['key'] == 'fee-11000'][0]['cite'], C.fy(2026),
         C.usd(L['regular']['budget']), C.usd(m['netted']), C.usd(y[2026]['regular']),
         C.usd(m['moved_back']), b['regular']['fee_comment'], b['regular']['rows'][0],
         C.fy(2027)))
    a('**Where the fees went is not stated anywhere** (registered: *%s*). The town’s general '
      'fund revenue account `STUDENTBUS` shows %s at FY%d period %d. One account is a '
      'candidate — **a hypothesis**: in the school choice fund (1308), account 437601, '
      '`SCH. CHOICE BUS FEE`, took in:\n\n'
      % (m['gaps']['booked'], usd2(st['town_fee']['expended']), st['town_fee']['fy'],
         st['town_fee']['period']))
    a('| FY | receipts |\n|---|---:|\n')
    for fy, v in sorted(st['fee'].items()):
        a('| %s | %s |\n' % (C.fy(fy), usd2(v)))
    a('\nThe receipts begin in %s, the year the first fees fell due (by 1 June 2025, for the '
      'year starting that July). That fits the fees and does not establish them: the account '
      'is named for school choice (registered: *%s*).\n\n'
      % (C.fy(2025), m['gaps']['fee-account']))
    a('**The circuit breaker’s transportation payments**, DESE’s schedule, by year paid:\n\n')
    a('| FY paid | transportation reimbursement | note |\n|---|---:|---|\n')
    for x in st['cb']:
        a('| %s | %s | %s |\n' % (C.fy(x['fy']), C.usd(x['transport']), x['comment'] or ''))
    a('\nDESE’s file shows no transportation reimbursement before %s. It is money returned '
      'for out-of-district placements only, and it is a separate column everywhere on this '
      'page.\n\n' % C.fy(st['cb'][0]['fy']))
    a('**Regional transportation.** The Cherry Sheet shows Lunenburg receiving nothing under '
      'that line in every year %s — regional districts are reimbursed for busing and '
      'single-town districts are not.\n\n' % C.fyspan(st['cherry_years'][0], st['cherry_years'][-1]))
    a('### What this does not show\n\n')
    a('- **How much the fee raised.** Neither the number of families who paid nor the total '
      'collected is published.\n')
    a('- **Whether the fee covers its share.** That needs both the receipts and the riders; '
      'neither is held.\n\n')

    # ---- 6. special education transportation
    over_all = m['sped_over']
    a('## 6. Special education transportation\n\n')
    a('### In plain terms\n\n')
    a('This is the transportation line that moves. Spending was %s in %s, the last year '
      'before the 2020 school closures, and %s in %s. Regular routes are priced by contract in '
      'advance; special education transportation depends on where children with a plan need to '
      'go. It came in under its voted budget every year from %s to %s, and over it in %s.\n\n'
      % (C.usd(m['sped_low']['sped']['spent']), C.fy(m['sped_low']['fy']),
         C.usd(L['sped']['spent']), C.fy(last), C.fy(m['sped_under_run'][0]),
         C.fy(m['sped_under_run'][-1]), ' and '.join(C.fy(x['fy']) for x in m['recent_over'])))
    a('### The evidence\n\n')
    a('| FY | voted | spent | over (+) or under | circuit breaker, transportation, paid that year |\n'
      '|---|---:|---:|---:|---:|\n')
    cbm = {x['fy']: x['transport'] for x in st['cb']}
    for r in m['ledger']:
        if r['fy'] < 2016:
            continue
        d = r['sped']['spent'] - r['sped']['budget']
        a('| %s | %s | %s | %s | %s |\n' % (C.fy(r['fy']), C.usd(r['sped']['budget']),
                                           C.usd(r['sped']['spent']),
                                           ('+' if d > 0 else '') + C.usd(d),
                                           C.usd(cbm[r['fy']]) if r['fy'] in cbm else '—'))
    a('| %s | %s | — | — | — |\n\n' % (C.fy(2027), C.usd(b['sped']['fy27_balanced'])))
    a('The district’s FY2026 overview gives the line’s rise as *“Rate increase 7%%”* and *“%s”*. '
      'That is the district’s explanation; nothing here tests it.\n\n' % OVERVIEW_QUOTES['vans'])
    a('### What this does not show\n\n')
    a('- **Price against volume.** The van contract is not in the archive (registered: *%s*).\n'
      % m['gaps']['vans'])
    a('- **What it costs per child.** No count of children transported is published.\n')
    a('- **The full special education picture.** Tuition and in-district costs are on '
      '[/analysis/special-education-costs](/analysis/special-education-costs).\n\n')

    # ---- what was said
    a('## What was said\n\n')
    a('From the town’s published minutes, searched with `scripts/search_minutes.py` for '
      '*Dee Bus*, *athletic transportation*, *bus fee*, *bus fees*, *late bus*, *vanpool*, '
      '*van pool*, *special education transportation*, *transportation waiver* and '
      '*passenger vans*. Every quotation is re-read from the archive on every build.\n\n')
    for q in m['quotes']:
        a('- *“%s”* — %s, %s%s ([minutes](%s)). %s\n'
          % (q['quote'], q['board'], q['date'], (', ' + q['who']) if q.get('who') else '',
             q['cite'], q['why']))
    a('\n*Late bus* found nothing in the town’s minutes. That is a statement about the '
      'documents searched, not about the meetings.\n\n')

    # ---- persona review
    a('## Read as each reader\n\n')
    a('`notes/process/PERSONAS.md`, run before publishing.\n\n')
    a('- **Already sure the schools are not straight with them.** The worst-looking facts are on '
      'the first screen at full size: the athletic line was about a third of what athletic buses '
      'cost in %s, with families’ fees covering the rest, and nobody has said where the new bus '
      'fees are booked. The first draft kept the second of those in an expansion; it is now the '
      'supporting line of its card.\n' % C.fy(2024))
    a('- **Hears it second-hand.** The sentence they will repeat is the first card: athletic '
      'buses were %s of school transportation spending in %s. True as worded, on the general '
      'fund it names, and the card says the rest was the school day.\n'
      % (C.pct(m['share'][last]['spent']), C.fy(last)))
    a('- **Close to the boards.** No finding names a person. Two people are quoted, each for '
      'something said on the record: a School Committee member’s explanation of the athletic '
      'line, and a Finance Committee member’s request for the contracts.\n')
    a('- **Finance Committee.** One thing to do: the contract ends 30 June 2028 and its option '
      'years are already priced, so the renewal — and the old contract the 7.6% question needs '
      '— can be asked for before the FY2029 budget rather than during it.\n')
    a('- **School Committee.** *Did the bus fee lower the bill?* is answered in section 5: it '
      'lowered the voted line by %s and the line was topped back up.\n' % C.usd(m['netted']))
    a('- **Select Board.** Nothing here compares the town side with the school side; the Monty '
      'Tech buses, a town appropriation, are named and left out.\n')
    a('- **The parent whose programme is on the list.** Every sport is findable by name in '
      'section 3. Band was not, in the first draft: the %s balanced budget carries nothing for '
      'band trips while the Finance Committee was told they would be reduced, and both are now '
      'in section 1.\n' % C.fy(2027))
    a('- **Somebody with one concrete thing (the meeting search).** Three lines here ran over or '
      'under budget, and each was searched. Athletic transportation came in under its revised '
      'budget in %s, the year before it was cut, while athletes were then being driven '
      'privately under a signed waiver — quoted. The regular-route line ran over in %s and %s; '
      'a Finance Committee member asked for the bus contracts that spring — quoted. Special '
      'education transportation ran over in %s; the search found only the district’s account of '
      'the state’s reimbursement, and no resident speaking to it.\n'
      % (C.fy(2026), C.fy(2023), C.fy(2024),
         ' and '.join(C.fy(x['fy']) for x in m['recent_over'])))
    a('- **Grilled.** The first draft measured the special education rise from %s, its lowest '
      'year — a year of school closures. It now starts from %s and says why.\n\n'
      % (C.fy(2020), C.fy(m['sped_low']['fy'])))

    # ---- method
    a('## Method and classification\n\n')
    a('Analysis, October 2026. Every figure is computed by `scripts/build_transportation.py` '
      'and recomputed by a different route by `scripts/verify_transportation.py`.\n\n')
    a('- **Which accounts.** General fund school accounts, by function and object code: '
      'regular routes 3300/535025, special education 3300/535026, athletics 3510/535016, band '
      'and music 2440/535016. Every general fund school account whose description names '
      'transportation must be one of these, or the build stops. The grouping is ours.\n')
    a('- **Two ledgers, tied.** %s are the MUNIS year-end reports. Earlier years are the '
      'Finance Committee’s ledger history, used because its transportation rows equal the '
      'MUNIS reports to the dollar in %s; the build refuses if they stop.\n'
      % (C.fyspan(2023, last), ' and '.join(C.fy(x) for x in m['tie_years'])))
    a('- **Budget** is the original appropriation; **spent** is expended plus still committed '
      'at the close. They are never added, and no rate here runs from one to the other.\n')
    a('- **Trips** are OUR ESTIMATE wherever they appear.\n\n')

    # ---- sources
    a('## Sources\n\n')
    for s in sources():
        a('- **%s** — %s. `%s` sha256 `%s`\n' % (s['publisher'], s['note'], s['path'],
                                                s['sha256'][:12]))
    a('\nGenerated by `scripts/build_transportation.py`; every figure in the summary is '
      'recomputed by `scripts/verify_transportation.py` by a different route.\n')
    return ''.join(w)


# --------------------------------------------------------------------- the SVGs, for /docs and the PDF

COL = {'regular': '#2a78d6', 'sped': '#8e3a95', 'athletic': '#eb6834', 'band': '#9ca3af',
       'ink': '#111827', 'muted': '#6b7280', 'grid': '#e5e7eb', 'fund': '#0e8a6b'}
HEAD = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" font-family="system-ui,'
        'sans-serif" font-size="11"><rect width="100%%" height="100%%" fill="#ffffff"/>')


def nice_top(v, step):
    return max(step, -((-v) // step) * step)


def axis(o, W, L, R, y, hi, step):
    v = 0
    while v <= hi:
        o.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="%s"/>'
                 '<text x="%d" y="%.1f" text-anchor="end" fill="%s">%s</text>'
                 % (L, W - R, y(v), y(v), COL['grid'], L - 6, y(v) + 4, COL['muted'],
                    html.escape(C.usd(v))))
        v += step


def legend(o, items, x0, y0):
    x = x0
    for name, col, kind in items:
        if kind == 'line':
            o.append('<line x1="%d" x2="%d" y1="%d" y2="%d" stroke="%s" stroke-width="2"/>'
                     % (x, x + 16, y0 + 5, y0 + 5, col))
            x += 20
        else:
            o.append('<rect x="%d" y="%d" width="10" height="10" fill="%s"%s/>'
                     % (x, y0, col, ' fill-opacity="0.4"' if kind == 'pale' else ''))
            x += 14
        o.append('<text x="%d" y="%d" fill="%s">%s</text>' % (x, y0 + 9, COL['ink'],
                                                            html.escape(name)))
        x += int(6.2 * len(name)) + 16


def svg_schools(pay):
    rows = pay['by_year']
    W, H, L, R, T, B = 780, 400, 70, 12, 40, 44
    hi = nice_top(max(max(r['all_budget'] or 0, r['all_spent'] or 0) for r in rows), 500000)
    y = lambda v: T + (H - T - B) * (1 - v / hi)
    slot = (W - L - R) / len(rows)
    bw = slot * 0.36
    o = [HEAD % (W, H)]
    axis(o, W, L, R, y, hi, 500000)
    keys = [c for c, _, _, _ in CATS]
    for j, r in enumerate(rows):
        x0 = L + slot * j + slot * 0.12
        for side, off, op in (('budget', 0, 0.4), ('spent', bw + 1, 1.0)):
            base = 0
            for c in keys:
                v = r.get('%s_%s' % (c, side))
                if not v:
                    continue
                o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" '
                         'fill-opacity="%s"/>' % (x0 + off, y(base + v), bw,
                                                  max(0.5, y(base) - y(base + v)), COL[c], op))
                base += v
        if j % 2 == 0 or j == len(rows) - 1:
            o.append('<text x="%.1f" y="%d" text-anchor="middle" fill="%s">%s</text>'
                     % (L + slot * (j + 0.5), H - 26, COL['muted'], "FY'%02d" % (r['fy'] % 100)))
    legend(o, [(CAT_NAME[c], COL[c], 'box') for c in keys], L, 10)
    o.append('<text x="%d" y="%d" fill="%s">left bar, pale: budget voted before the year; right '
             'bar, solid: spent at the close. General fund. %s budget only.</text>'
             % (L, H - 8, COL['muted'], C.fy(rows[-1]['fy'])))
    o.append('</svg>\n')
    return ''.join(o)


def line_path(seq, x, y):
    return ' '.join('%s%.1f,%.1f' % ('M' if n == 0 else 'L', x(j), y(v))
                    for n, (j, v) in enumerate(seq))


def svg_athletics(pay):
    rows = pay['athletics']
    W, H, L, R, T, B = 780, 360, 64, 12, 40, 40
    vals = [v for r in rows for v in (r['line_budget'], r['line_spent'], r['sheet_total'],
                                      (r['fund_stated'] or 0) + (r['line_spent'] or 0))
            if v]
    hi = nice_top(max(vals), 25000)
    y = lambda v: T + (H - T - B) * (1 - v / hi)
    slot = (W - L - R) / len(rows)
    o = [HEAD % (W, H)]
    axis(o, W, L, R, y, hi, 25000)
    for j, r in enumerate(rows):
        x0 = L + slot * j + slot * 0.15
        bw = slot * 0.34
        if r['line_budget'] is not None:
            o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" '
                     'fill-opacity="0.4"/>' % (x0, y(r['line_budget']), bw,
                                               max(0.5, y(0) - y(r['line_budget'])),
                                               COL['athletic']))
        if r['line_spent'] is not None:
            o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                     % (x0 + bw + 1, y(r['line_spent']), bw,
                        max(0.5, y(0) - y(r['line_spent'])), COL['athletic']))
        if r['fund_stated']:
            top = r['line_spent'] + r['fund_stated']
            o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                     % (x0 + bw + 1, y(top), bw, y(r['line_spent']) - y(top), COL['fund']))
        if r['sheet_total']:
            cx = x0 + bw * 1.5
            o.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s"/>'
                     % (cx, y(r['sheet_total']), COL['ink']))
        if j % 2 == 0 or j == len(rows) - 1:
            o.append('<text x="%.1f" y="%d" text-anchor="middle" fill="%s">%s</text>'
                     % (L + slot * (j + 0.5), H - 24, COL['muted'], "FY'%02d" % (r['fy'] % 100)))
    legend(o, [('line, budget', COL['athletic'], 'pale'), ('line, spent', COL['athletic'], 'box'),
               ('fee fund, stated (FY14-FY17)', COL['fund'], 'box')], L, 10)
    o.append('<circle cx="%d" cy="%d" r="4" fill="%s"/><text x="%d" y="%d" fill="%s">full '
             'cost, district by-sport sheet (stated)</text>'
             % (L + 520, 15, COL['ink'], L + 528, 19, COL['ink']))
    o.append('<text x="%d" y="%d" fill="%s">Athletic transportation, general fund line and what '
             'district documents state beyond it.</text>' % (L, H - 6, COL['muted']))
    o.append('</svg>\n')
    return ''.join(o)


def svg_sports(pay):
    rows = [r for r in pay['sports'] if (r['fy2024'] or r['fy2025'])]
    W, L, R, T, rowh = 780, 230, 20, 36, 18
    H = T + rowh * len(rows) + 30
    hi = nice_top(max(max(r['fy2024'] or 0, r['fy2025'] or 0) for r in rows), 2000)
    x = lambda v: L + (W - L - R) * v / hi
    o = [HEAD % (W, H)]
    v = 0
    while v <= hi:
        o.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="%s"/><text x="%.1f" y="%d" '
                 'text-anchor="middle" fill="%s">%s</text>'
                 % (x(v), x(v), T - 4, H - 26, COL['grid'], x(v), H - 12, COL['muted'],
                    html.escape(C.usd(v))))
        v += 2000
    for i, r in enumerate(rows):
        yy = T + i * rowh
        o.append('<text x="%d" y="%d" text-anchor="end" fill="%s">%s</text>'
                 % (L - 6, yy + 12, COL['ink'], html.escape(r['label'])))
        if r['fy2024']:
            o.append('<rect x="%d" y="%d" width="%.1f" height="7" fill="%s" fill-opacity="0.4"/>'
                     % (L, yy + 2, x(r['fy2024']) - L, COL['athletic']))
        if r['fy2025']:
            o.append('<rect x="%d" y="%d" width="%.1f" height="7" fill="%s"/>'
                     % (L, yy + 9, x(r['fy2025']) - L, COL['athletic']))
    legend(o, [('FY2024', COL['athletic'], 'pale'), ('FY2025', COL['athletic'], 'box')], L, 10)
    o.append('</svg>\n')
    return ''.join(o)


def svg_contract(pay):
    rows = [r for r in pay['contract']['regular_line'] if r['fy'] >= 2016]
    W, H, L, R, T, B = 780, 340, 76, 12, 40, 40
    hi = nice_top(max(max(r['budget'] or 0, r['contract'] or 0) for r in rows), 250000)
    y = lambda v: T + (H - T - B) * (1 - v / hi)
    slot = (W - L - R) / len(rows)
    o = [HEAD % (W, H)]
    axis(o, W, L, R, y, hi, 250000)
    cx = lambda j: L + slot * (j + 0.5)
    for j, r in enumerate(rows):
        if r['budget']:
            o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s" '
                     'fill-opacity="0.55"/>' % (cx(j) - slot * 0.3, y(r['budget']), slot * 0.6,
                                                y(0) - y(r['budget']), COL['regular']))
        o.append('<text x="%.1f" y="%d" text-anchor="middle" fill="%s">%s</text>'
                 % (cx(j), H - 24, COL['muted'], "FY'%02d" % (r['fy'] % 100)))
    seq = [(j, r['contract']) for j, r in enumerate(rows) if r['contract']]
    o.append('<path d="%s" fill="none" stroke="%s" stroke-width="2.4"/>'
             % (line_path(seq, cx, y), COL['ink']))
    for j, v in seq:
        opt = rows[j].get('optional')
        o.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s"/>'
                 % (cx(j), y(v), '#ffffff' if opt else COL['ink']))
        o.append('<circle cx="%.1f" cy="%.1f" r="4" fill="none" stroke="%s"/>'
                 % (cx(j), y(v), COL['ink']))
    legend(o, [('regular-route line, voted', COL['regular'], 'box'),
               ('contract price (hollow: optional years)', COL['ink'], 'line')], L, 10)
    o.append('</svg>\n')
    return ''.join(o)


def svg_sped(pay):
    rows = [r for r in pay['sped'] if r['fy'] >= 2016]
    W, H, L, R, T, B = 780, 340, 70, 12, 40, 40
    hi = nice_top(max(max(r['budget'] or 0, r['spent'] or 0) for r in rows), 100000)
    y = lambda v: T + (H - T - B) * (1 - v / hi)
    slot = (W - L - R) / len(rows)
    o = [HEAD % (W, H)]
    axis(o, W, L, R, y, hi, 100000)
    cx = lambda j: L + slot * (j + 0.5)
    for j, r in enumerate(rows):
        if r['cb_transport']:
            o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                     % (cx(j) - slot * 0.22, y(r['cb_transport']), slot * 0.44,
                        y(0) - y(r['cb_transport']), COL['fund']))
        o.append('<text x="%.1f" y="%d" text-anchor="middle" fill="%s">%s</text>'
                 % (cx(j), H - 24, COL['muted'], "FY'%02d" % (r['fy'] % 100)))
    for key, dash in (('budget', ' stroke-dasharray="5 4"'), ('spent', '')):
        seq = [(j, r[key]) for j, r in enumerate(rows) if r[key] is not None]
        o.append('<path d="%s" fill="none" stroke="%s" stroke-width="2.2"%s/>'
                 % (line_path(seq, cx, y), COL['sped'], dash))
    legend(o, [('voted (dashed)', COL['sped'], 'line'), ('spent', COL['sped'], 'line'),
               ('circuit breaker, transportation, paid', COL['fund'], 'box')], L, 10)
    o.append('</svg>\n')
    return ''.join(o)


# --------------------------------------------------------------------- main

def outputs():
    m = measure()
    rows = build_conclusions(m)
    pay = payload(m, rows)
    return {
        OUT_JSON: json.dumps(pay, indent=1, ensure_ascii=False, sort_keys=True) + '\n',
        OUT_MD: render_md(m, rows),
        os.path.join(CHART_DIR, '%s-schools-athletics.svg' % ID): svg_schools(pay),
        os.path.join(CHART_DIR, '%s-athletics.svg' % ID): svg_athletics(pay),
        os.path.join(CHART_DIR, '%s-sports.svg' % ID): svg_sports(pay),
        os.path.join(CHART_DIR, '%s-contract.svg' % ID): svg_contract(pay),
        os.path.join(CHART_DIR, '%s-sped.svg' % ID): svg_sped(pay),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    outs = outputs()
    if a.check:
        stale = []
        for p, text in outs.items():
            cur = open(p, encoding='utf-8').read() if os.path.exists(p) else None
            if cur != text:
                stale.append(os.path.relpath(p, ROOT))
        if stale:
            print('STALE %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('%s: %d outputs current' % (ID, len(outs)))
        return 0
    for p, text in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('wrote %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
