#!/usr/bin/env python3
"""School transportation: what the buses cost, what pays for them, and what the contract fixes.

    python3 scripts/build_transportation.py           # write the payload, the markdown, the charts
    python3 scripts/build_transportation.py --check   # fail if any output no longer reproduces

THE QUESTIONS, TJ's, 9 October 2026, the day the Dee Bus contract arrived by records request:

  1. SCHOOLS AGAINST ATHLETICS. Transportation for the school day -- the regular routes and
     special education -- against athletic transportation, by year, budgeted and actually
     spent, side by side. Never combined in one calculation (rule 1): a budget is compared
     only with a budget and an actual only with an actual.
  2. PER SPORT. Athletic transportation by sport and season, set beside what each team's
     posted schedule implies: the away games ArbiterLive lists, the miles to each venue, and
     the contract's per-mile and per-hour rates. That bus model is OURS and is labelled so
     everywhere it appears (rule 3). It replaced, on 11 October 2026, a figure that divided
     FY2025 dollars by the bid form's long hypothetical trip at FY2026 prices -- a different
     year's price and a trip far longer than the district's own charges.

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
  * call the bus model a count. Nobody publishes trips; the schedules say where teams
    played, not whether a bus went or was shared, and the page gives both bounds.
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
         why='One trip, priced under the new contract: a class field trip. It sits between the '
             'bid form’s average trip priced with and without its four hours of waiting.'),
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
    dict(key='restore-vote', path='sources/meetings/text/school-committee/2026-08-26-minutes-7980.txt',
         board='School Committee', date='2026-08-26',
         quote='$10,000 toward the restoration of high school athletic transportation, with '
               'additional transportation funding to come from the athletic revolving fund. Ms. '
               'Young seconded the motion. The motion passed, 3-0-1',
         why='The vote on the plan: the town’s share of restored athletic buses, and the rest '
             'from the athletic fee fund.'),
    dict(key='fincom-sped27', path='sources/meetings/text/finance-committee/2026-02-26-minutes-7673.txt',
         board='Finance Committee', date='2026-02-26',
         quote='Budgeted for Special Education Transportation: $649,953',
         why='The FY2027 special education transportation budget as presented to the Finance '
             'Committee, four months before FY2026 closed past its revised budget.'),
    dict(key='restore-why', path='sources/meetings/text/school-committee/2026-08-26-minutes-7980.txt',
         board='School Committee', date='2026-08-26',
         quote='the reduced cost resulted from scheduling more competitions closer to Lunenburg, '
               'increasing home competitions, and using actual schedules and prior-year spring '
               'costs to obtain a more accurate transportation estimate',
         why='The Superintendent’s reasons for the restoration estimate, as minuted. They are '
             'her account of the figure; the page sets it beside the district’s own FY2025 '
             'sheet and the contract’s FY2027 rates without testing it.'),
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

# WHAT WAS SAID ABOUT TRACK, and it is only in the recordings. The town's minutes of these
# meetings do not record it; our machine captions do. Captions are a FINDING AID, not a record
# (a caption model mangles names and figures), so nothing here is quoted as the meeting's
# words and no figure is taken from them. Each moment is cited as the video at its timestamp,
# summarised in our words, and checked on every build: the words it is summarised from must
# still be in the caption file within the window, or the build stops.
TRANSCRIPTS = os.path.join(D, 'youtube-transcripts')
CAPTIONS = [
    dict(key='waiting', file='school-committee/2024-02-28-pn_OXfPbl9w.json', t=7535,
         words=('bus sits there', 'track competitions are often long', 'sitting and waiting'),
         board='School Committee', date='2024-02-28',
         said='The district told the Committee it pays Dee Bus for every hour a bus waits at an '
              'event, that track competitions run long, and that most of the charge is the '
              'waiting.'),
    dict(key='reggie', file='school-committee/2025-03-12-b7caO9Kd7VA.json', t=6496,
         words=('league meet is at', 'reggie lewis', 'facility to support this',
                'winter track program', 'just waiting at the event'),
         board='School Committee', date='2025-03-12',
         said='Members discussed indoor track: the league meet had moved to the Reggie Lewis '
              'Center in Boston, Lunenburg has no indoor facility of its own, and the bus is '
              'billed in full while it waits.'),
    dict(key='aac', file='athletic-advisory-council/2025-01-27-_tYwHQu995w.json', t=1901,
         words=('reggie lewis center for a track meet', 'sits there'),
         board='Athletic Advisory Council', date='2025-01-27',
         said='A bus taken to a track meet at the Reggie Lewis Center waits there most of the '
              'day; a van was raised as a cheaper way to carry a small group.'),
]


def hms(t):
    return '%d:%02d:%02d' % (t // 3600, t % 3600 // 60, t % 60)


def check_captions():
    out = []
    for c in CAPTIONS:
        d = json.load(open(os.path.join(TRANSCRIPTS, c['file']), encoding='utf-8'))
        win = ' '.join(s['text'] for s in d['segments']
                       if c['t'] - 5 <= s['start'] <= c['t'] + 180).lower()
        win = ' '.join(win.split())
        miss = [w for w in c['words'] if w not in win]
        if miss:
            fail('caption %s no longer carries %r near %s' % (c['key'], miss, hms(c['t'])))
        out.append(dict(c, url='%s&t=%ds' % (d['video_url'], c['t']), at=hms(c['t'])))
    return out


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
    # Registered 10 October 2026 from the audit pass (notes/findings/TRANSPORTATION-AUDIT.md).
    'fee-balance': 'What the athletic fee fund held at each 30 June, FY2021 to FY2026',
    'fee-pos': 'What the athletic fee fund’s high school purchase-of-service account paid for '
               'in FY2026',
    'fy24-regular': 'Why FY2024’s regular-route bus spending was higher than FY2025’s',
    # Registered 10 October 2026, with the brief: the reason outdoor track LOOKS cheapest.
    'spring25': 'Whether the FY2025 spring section of the district’s by-sport athletics '
                'workbook is complete',
    # Registered 11 October 2026, with the schedule-based bus model.
    'schedules': 'Which games Lunenburg’s athletic teams played in the seasons their posted '
                 'schedules do not cover',
    'estimate27': 'How the district built its FY2027 athletic transportation estimate',
}

# THE AUDIT PASS (notes/process/AUDIT-PASS.md). These inputs exist only for the comparisons
# the summary now leads with: the fee fund's receipts against its spending, the model's
# transport rate against the contract, and the last fee fund balance anybody published.
FUND_BAL = os.path.join(D, 'fund-balances-fincom.csv')
MODEL_JSON = os.path.join(ROOT, 'fy28', 'public', 'data', 'model.json')
# OUR choice, and said where it is used: the special education under-budget window opens in
# the first year the gap between voted and spent passed this amount. It exists so the window
# is a rule rather than a pair of years somebody picked by eye.
BIG_GAP = 100000


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
    x = float(x)
    return ('-$' if x < 0 else '$') + format(abs(x), ',.2f')


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
            # `over_revised` is computed from the unrounded amounts: spent at the close
            # against the REVISED budget, the test of control (AUDIT-PASS test 2).
            row[c] = dict(budget=r0(o), revised=r0(rv), spent=r0(ex + en), expended=r0(ex),
                          committed=r0(en), over_revised=r0(ex + en - rv),
                          transfer=r0(rv - o))
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


# --------------------------------------------------------------------- the schedules
#
# WHAT EACH TEAM PLAYED, AND WHERE. ArbiterLive is the scheduling site the district links
# from its athletics page. `extract_arbiter_schedules.py` reads it into one row per game,
# FY2022-FY2027; `build_athletics_venue_distances.py` gives each venue a round-trip driving
# distance from the high school (OpenStreetMap geocode, OSRM route). The pages themselves are
# NOT archived or republished here: the rows are cited
# as facts -- date, opponent, venue, home or away -- and nothing else is taken from them.
#
# THE BUS MODEL IS OURS, every figure of it:
#
#   cost of one trip = round-trip miles x the contract's per-mile rate
#                      + WAIT_HOURS x the contract's per-hour waiting rate
#
#   * WAIT_HOURS is the bid form's own four hours a trip, an assumption we adopt; a track
#     meet runs longer than a game, so the waiting part is always reported separately.
#   * UPPER bound: one bus for every team-game away. LOWER bound: one bus for every distinct
#     date and venue any Lunenburg team travelled to, its cost shared equally among the teams
#     there. Whether buses were in fact shared is NOT observed anywhere.
#   * Prices: each year at the contract's own rates from FY2026; FY2022-FY2025 were under the
#     previous contract, whose rates are not held (gap `rates`), so those years are priced
#     AT FY2026 PRICES and say so. Nothing here feeds a projection (rule 1).
#   * Played games only: a game marked canceled, postponed or rained out is dropped. A game
#     with no listed venue (`TBA`, `Not Listed`) or a venue with no distance is counted, and
#     carries its waiting but no miles -- so the miles part is a floor for those.
#   * Home games at a venue outside Lunenburg (hockey's home rink is in Fitchburg) are
#     counted and left OUT of both bounds: the district lists them as home, and whether a bus
#     carried the team is not recorded.
SCHED = os.path.join(D, 'athletics-schedules.csv')
SCHED_COV = os.path.join(D, 'athletics-schedules-coverage.csv')
VENUE_MILES = os.path.join(D, 'athletics-venue-distances.csv')
SHEET_XLSX = os.path.join(ROOT, 'sources', 'town-ledgers', 'account-details',
                          'athletics-by-sport-fy2024-fy2026.xlsx')
NOT_PLAYED = ('Canceled', 'Cancelled', 'Postponed', 'Rainout')
WAIT_HOURS = FORM_WAIT_HOURS
SCHED_YEARS = list(range(2022, 2028))
# OUR threshold for the flag, stated where it is used: a sheet figure BELOW the cost of the
# miles alone, on the lower bound (shared buses, no waiting at all), cannot be explained by
# the waiting assumption, because it assumes none.

# The district's by-sport sheet names a row one way and ArbiterLive names a team another.
# This crosswalk is OURS; every scheduled team must land in exactly one row or the build stops.
SHEET_TEAMS = {
    ('Fall', 'HS', 'Boys CC'): [('Cross Country', 'Boys Varsity')],
    ('Fall', 'HS', 'Girls CC'): [('Cross Country', 'Girls Varsity')],
    ('Fall', 'HS', 'Boys Soccer'): [('Soccer', 'Boys Varsity'), ('Soccer', 'Boys Junior Varsity')],
    ('Fall', 'HS', 'Cheer'): [],
    ('Fall', 'HS', 'Field Hockey'): [('Field Hockey', 'Girls Varsity'),
                                     ('Field Hockey', 'Girls Junior Varsity')],
    ('Fall', 'HS', 'Football'): [('Football', 'Boys Varsity'), ('Football', 'Boys Junior Varsity')],
    ('Fall', 'HS', 'Girls Soccer'): [('Soccer', 'Girls Varsity'),
                                     ('Soccer', 'Girls Junior Varsity')],
    ('Fall', 'HS', 'Golf'): [('Golf', 'Boys Varsity'), ('Golf', 'Boys Junior Varsity')],
    ('Fall', 'HS', 'Unified Basketball $100'): [('Basketball', 'Coed Unified')],
    ('Fall', 'MS', 'Cross Country'): [('Cross Country', 'Boys Middle School'),
                                      ('Cross Country', 'Girls Middle School'),
                                      ('Cross Country', 'Coed Middle School')],
    ('Fall', 'MS', 'Field Hockey'): [('Field Hockey', 'Girls Middle School')],
    ('Winter', 'HS', 'HS BasketBall - Boys'): [('Basketball', 'Boys Varsity'),
                                               ('Basketball', 'Boys Junior Varsity - JV'),
                                               ('Basketball', 'Boys Junior Varsity - JV2')],
    ('Winter', 'HS', 'HS Basketball - Girls'): [('Basketball', 'Girls Varsity'),
                                                ('Basketball', 'Girls Junior Varsity')],
    ('Winter', 'HS', 'Ice Hockey - Boys'): [('Hockey', 'Boys Varsity'),
                                            ('Hockey', 'Boys Junior Varsity')],
    ('Winter', 'HS', 'Ice Hockey - Girls'): [],
    ('Winter', 'HS', 'Indoor Track - Boys'): [('Track & Field - Indoor', 'Boys Varsity')],
    ('Winter', 'HS', 'Indoor Track - Girls'): [('Track & Field - Indoor', 'Girls Varsity')],
    ('Winter', 'HS', 'Ski Team'): [('Ski', 'Coed Varsity')],
    ('Winter', 'MS', 'Basketball - Boys'): [('Basketball', 'Boys Middle School')],
    ('Winter', 'MS', 'Basketball - Girls'): [('Basketball', 'Girls Middle School')],
    ('Spring', 'HS', 'Baseball'): [('Baseball', 'Boys Varsity'),
                                   ('Baseball', 'Boys Junior Varsity'),
                                   ('Baseball', 'Boys Freshman')],
    ('Spring', 'HS', 'Boys Lax'): [('Lacrosse - Boys', 'Boys Varsity'),
                                   ('Lacrosse - Boys', 'Boys Junior Varsity')],
    ('Spring', 'HS', 'Girls Lax'): [('Lacrosse - Girls', 'Girls Varsity'),
                                    ('Lacrosse - Girls', 'Girls Junior Varsity')],
    ('Spring', 'HS', 'Boys Track'): [('Track & Field - Outdoor', 'Boys Varsity')],
    ('Spring', 'HS', 'Girls Track'): [('Track & Field - Outdoor', 'Girls Varsity')],
    ('Spring', 'HS', 'Softball'): [('Softball', 'Girls Varsity'),
                                   ('Softball', 'Girls Junior Varsity')],
    ('Spring', 'HS', 'Unified Track ($100)'): [('Track & Field - Outdoor', 'Coed Unified')],
    ('Spring', 'MS', 'Softball'): [('Softball', 'Girls Middle School')],
    ('Spring', 'MS', 'Track'): [('Track & Field - Outdoor', 'Boys Middle School'),
                                ('Track & Field - Outdoor', 'Girls Middle School')],
}


def season_of(r):
    """The extract's season is by sport name. Unified basketball plays in the autumn and the
    spring as well as the winter, so for it alone the season is read off the month (ours)."""
    if r['level'] == 'Coed Unified' and r['sport'] == 'Basketball':
        mo = int(r['date'][5:7])
        return 'fall' if 8 <= mo <= 11 else 'winter' if mo in (12, 1, 2) else 'spring'
    return r['season']


def sheet_charges(cells):
    """Each figure the district typed into a by-sport transportation cell. A formula such as
    `=532.5+375` is two charges; a divisor (`/2`, the sheet halving one bus between two
    rows) is not a charge. A cell holding a bare number is one typed figure."""
    import openpyxl
    wb = openpyxl.load_workbook(SHEET_XLSX)
    out = {}
    for key, (season, cell) in cells.items():
        v = wb[season][cell].value
        if isinstance(v, str) and v.startswith('='):
            body = v[1:]
            nums = [float(x) for x in re.findall(r'(?<![/\d.])(\d+(?:\.\d+)?)', body)]
            halved = bool(re.search(r'\)\s*/\s*2\s*$', body))
            out[key] = dict(formula=v, charges=nums, halved=halved, typed=False)
        else:
            out[key] = dict(formula=None if v is None else str(v),
                            charges=[float(v)] if v else [], halved=False, typed=True)
    return out


def load_schedules(k, sp):
    y = {c['fy']: c for c in k['years']}
    price_year = lambda fy: fy if fy in y else min(y)
    per_trip = lambda fy, miles: ((miles or 0) * y[price_year(fy)]['trip_rate'],
                                  WAIT_HOURS * y[price_year(fy)]['wait_rate'])
    dist = {}
    for r in csv.DictReader(open(VENUE_MILES, encoding='utf-8')):
        dist[r['venue']] = float(r['round_trip_miles']) if r['round_trip_miles'].strip() else None
    rows = list(csv.DictReader(open(SCHED, encoding='utf-8')))
    fys = sorted({int(r['fiscal_year'][2:]) for r in rows})
    if fys != SCHED_YEARS:
        fail('the schedule extract covers %s, not FY2022-FY2027' % fys)
    team_sheet = {}
    for sk, teams in SHEET_TEAMS.items():
        for t in teams:
            if t in team_sheet:
                fail('%s is crosswalked to two sheet rows' % (t,))
            team_sheet[t] = sk
    unmapped = sorted({(r['sport'], r['level']) for r in rows} - set(team_sheet))
    if unmapped:
        fail('scheduled teams the sheet crosswalk does not place: %s' % unmapped)

    played = [r for r in rows if r['status'] not in NOT_PLAYED]
    away = [r for r in played if r['home_away'] == 'away']
    for r in away:
        if r['venue'] not in dist and r['venue'] not in ('TBA', 'Not Listed'):
            fail('away venue %r has no row in the distance file' % r['venue'])
    miles_of = lambda r: dist.get(r['venue'])

    # The lower bound's sharing: every distinct fiscal year, date and venue any team went to.
    groups = {}
    for r in away:
        groups.setdefault((r['fiscal_year'], r['date'], r['venue']), []).append(r)
    T = {}

    def team(r):
        key = (int(r['fiscal_year'][2:]), r['sport'], r['level'])
        if key not in T:
            T[key] = dict(fy=key[0], sport=r['sport'], level=r['level'],
                          school='MS' if 'Middle School' in r['level'] else 'HS',
                          sheet=team_sheet[(r['sport'], r['level'])][2],
                          home=0, away=0, trips=set(), miles=0.0, no_distance=0,
                          home_elsewhere=0, unplaced=0, hi_miles=0.0, hi_wait=0.0,
                          lo_miles=0.0, lo_wait=0.0, price_year=price_year(key[0]))
        return T[key]
    for r in played:
        t = team(r)
        if r['home_away'] == 'home':
            t['home'] += 1
            if r['venue_in_lunenburg'] == 'no':
                t['home_elsewhere'] += 1
        elif r['home_away'] == 'unknown':
            t['unplaced'] += 1
    for gk, g in groups.items():
        fy = int(gk[0][2:])
        mc, wc = per_trip(fy, miles_of(g[0]))
        for r in g:
            t = team(r)
            t['away'] += 1
            t['trips'].add(gk)
            if miles_of(r) is None:
                t['no_distance'] += 1
            else:
                t['miles'] += miles_of(r)
            t['hi_miles'] += mc
            t['hi_wait'] += wc
            t['lo_miles'] += mc / len(g)
            t['lo_wait'] += wc / len(g)
    teams = []
    for key in sorted(T, key=lambda q: (q[0], q[1], q[2])):
        t = T[key]
        t['trips'] = len(t['trips'])
        for f in ('miles', 'hi_miles', 'hi_wait', 'lo_miles', 'lo_wait'):
            t[f] = round(t[f], 2)
        t['lo'] = round(t['lo_miles'] + t['lo_wait'], 2)
        t['hi'] = round(t['hi_miles'] + t['hi_wait'], 2)
        teams.append(t)

    def total(sel):
        ts = [t for t in teams if sel(t)]
        out = {f: round(sum(t[f] for t in ts), 2) for f in
               ('away', 'miles', 'no_distance', 'home', 'home_elsewhere', 'unplaced', 'hi_miles',
                'hi_wait', 'lo_miles', 'lo_wait', 'lo', 'hi')}
        out['away'] = int(out['away'])
        return out
    by_fy = []
    for fy in SCHED_YEARS:
        d_ = total(lambda t: t['fy'] == fy)
        d_.update(fy=fy, price_year=price_year(fy),
                  trips=len({gk for gk in groups if int(gk[0][2:]) == fy}))
        by_fy.append(d_)

    # ---- the sheet against the schedules, sport by sport, the years the sheet covers.
    cells = {}
    for r in sp['rows']:
        for fy in (2024, 2025):
            c = r['cell%d' % fy]
            if c:
                cells[(r['season'], r['level'], r['printed_name'], fy)] = (r['season'], c)
    ch = sheet_charges(cells)
    compare = []
    for r in sp['rows']:
        sk = (r['season'], r['level'], r['printed_name'])
        if sk not in SHEET_TEAMS:
            fail('the by-sport sheet has a row the schedule crosswalk does not: %s' % (sk,))
        for fy in (2024, 2025):
            v = r['fy%d' % fy]
            if v is None:
                continue
            mine = [t for t in teams if t['fy'] == fy
                    and (t['sport'], t['level']) in SHEET_TEAMS[sk]]
            c = ch.get(sk + (fy,), dict(charges=[], halved=False, typed=False, formula=None))
            dist_trips = len({gk for gk, g in groups.items() if int(gk[0][2:]) == fy
                              and any((x['sport'], x['level']) in SHEET_TEAMS[sk] for x in g)})
            row = dict(season=r['season'], level=r['level'], sport=r['sport'], fy=fy,
                       sheet=v, formula=c['formula'], charges=len(c['charges']),
                       typed=c['typed'], halved=c['halved'], scheduled=bool(mine),
                       away=sum(t['away'] for t in mine), trips=dist_trips,
                       no_distance=sum(t['no_distance'] for t in mine),
                       lo=round(sum(t['lo'] for t in mine), 2),
                       hi=round(sum(t['hi'] for t in mine), 2),
                       lo_miles=round(sum(t['lo_miles'] for t in mine), 2))
            row['below_miles'] = bool(mine) and v > 0 and v < row['lo_miles']
            row['zero_with_games'] = bool(mine) and not v and row['away'] > 0
            compare.append(row)
    flagged = [c for c in compare if c['below_miles']]
    # The charges, pooled per year. Paired rows repeat one formula, so each distinct formula
    # is counted once; a typed figure is not a formula and is left out.
    med = {}
    for fy in (2024, 2025):
        seen, xs, per = set(), [], []
        for key, c in ch.items():
            if key[3] != fy or c['typed'] or c['formula'] in seen:
                continue
            seen.add(c['formula'])
            xs.extend(c['charges'])
            per.append(len(c['charges']))
        med[fy] = dict(n=len(xs), median=round(statistics.median(xs), 2),
                       per_cell=statistics.median(per), cells=len(per))
    return dict(teams=teams, by_fy=by_fy, compare=compare, flagged=flagged, charges=med,
                groups=groups, played=played, dist=dist, per_trip=per_trip,
                price_year=price_year, wait_hours=WAIT_HOURS,
                venues_without=sorted(v for v, m in dist.items() if m is None))


def schedule_test(k, S, restore):
    """The Superintendent's FY2027 reasons, against what the schedules show: the home share of
    high school games and the round-trip miles per away game, season by season, FY2024 to
    FY2027 -- like for like, on the teams whose FY2027 schedule is posted in full. Then what
    our model makes of FY2027's high school schedule so far, beside her estimate."""
    cov = list(csv.DictReader(open(SCHED_COV, encoding='utf-8')))
    stamps = {m_ for r in cov for m_ in re.findall(r'fetch date \((\d{4}-\d\d-\d\d)\)', r['basis'])}
    if len(stamps) != 1:
        fail('the coverage file no longer names one fetch date: %s' % sorted(stamps))
    fetched = stamps.pop()
    posted = {}
    for r in cov:
        if r['fiscal_year'] != 'FY2027':
            continue
        posted.setdefault(r['season'], {})[(r['sport'], r['level'])] = r
    seasons = []
    for season in ('fall', 'winter', 'spring'):
        cv = posted.get(season, {})
        hs = {t: r for t, r in cv.items() if 'Middle School' not in t[1]}
        full = sorted(t for t, r in hs.items() if r['assessment'] != 'missing'
                      and 'under half' not in r['basis'] and int(r['rows_listed']) > 0)
        short = sorted(t for t, r in hs.items() if t not in full and int(r['rows_listed']) > 0)
        none = sorted(t for t, r in hs.items() if int(r['rows_listed']) == 0)
        # A season is COMPARED only if it had begun by the date the schedules were read: one
        # not yet under way is still being posted (FY2027 hockey lists one game of a usual
        # twenty-one). Within it, only teams posted in full are compared, in every year.
        begun = any(r['date'] <= fetched for r in S['played'] if r['fiscal_year'] == 'FY2027'
                    and season_of(r) == season)
        complete = bool(full) and begun
        years = []
        for fy in (2024, 2025, 2026, 2027):
            g = [r for r in S['played'] if int(r['fiscal_year'][2:]) == fy
                 and season_of(r) == season and 'Middle School' not in r['level']
                 and (r['sport'], r['level']) in set(full)
                 and r['home_away'] in ('home', 'away')]
            h = sum(1 for r in g if r['home_away'] == 'home')
            aw = [r for r in g if r['home_away'] == 'away']
            ms = [S['dist'][r['venue']] for r in aw if S['dist'].get(r['venue']) is not None]
            years.append(dict(fy=fy, games=len(g), home=h, away=len(aw),
                              home_pct=pct1(h, len(g)) if g else None,
                              miles_avg=round(sum(ms) / len(ms), 1) if ms else None,
                              with_distance=len(ms)))
        seasons.append(dict(season=season, complete=complete, teams=full, short=short,
                            missing=none, years=years))
    # (c) FY2027 high school, as scheduled so far, at FY2027 prices; and the same teams' FY2026
    # spring and winter at FY2027 prices -- OUR assembly of a full year, for scale only.
    y27 = {c['fy']: c for c in k['years']}[2027]

    def priced(fy, season):
        lo = hi = lo_m = hi_m = lo_n = 0.0
        n = 0
        for gk, g in S['groups'].items():
            if int(gk[0][2:]) != fy:
                continue
            m_ = S['dist'].get(g[0]['venue'])
            mc = (m_ or 0) * y27['trip_rate']
            wc = WAIT_HOURS * y27['wait_rate']
            for r in g:
                if 'Middle School' in r['level'] or season_of(r) != season:
                    continue
                n += 1
                hi += mc + wc
                hi_m += mc
                lo += (mc + wc) / len(g)
                lo_m += mc / len(g)
                lo_n += 1 / len(g)
        return dict(fy=fy, season=season, away=n, lo=round(lo, 2), hi=round(hi, 2),
                    lo_miles=round(lo_m, 2), hi_miles=round(hi_m, 2), lo_trips=lo_n)
    so_far = [priced(2027, s) for s in ('fall', 'winter')]
    year26 = [priced(2026, s) for s in ('fall', 'winter', 'spring')]
    assembled = [so_far[0], year26[1], year26[2]]
    asm = {f: round(sum(p[f] for p in assembled), 2) for f in ('lo', 'hi', 'lo_miles', 'hi_miles')}
    # The waiting hours a trip that would make the assembled year, shared buses, equal her
    # estimate: arithmetic on our model, not a measurement of anybody's waiting.
    trips_lo = sum(p['lo_trips'] for p in assembled)
    be_hours = round((restore - asm['lo_miles']) / (trips_lo * y27['wait_rate']), 1)
    for p in so_far + year26:
        p['lo_trips'] = round(p['lo_trips'], 1)
    return dict(fetched=fetched, seasons=seasons, so_far=so_far, year26=year26, assembled=asm,
                trips_lo=round(trips_lo, 1), be_hours=be_hours, estimate=restore,
                rate=y27['trip_rate'], wait=y27['wait_rate'])


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


# --------------------------------------------------------------------- the audit inputs

def load_fee_funds():
    """Fund 1301 (athletics) receipts against spending, and what fund 1308 (school choice)
    does NOT do. Period 13, spending = ytd_expended + encumbrances; receipts are revenue rows,
    which MUNIS prints as negatives."""
    rows = [r for r in csv.DictReader(open(MUNIS, encoding='utf-8'))
            if r['period'] == '13' and r['fund'] in ('1301', '1308')]
    f = {}
    for r in rows:
        if r['fund'] != '1301':
            continue
        fy = int(r['fiscal_year'])
        d = f.setdefault(fy, dict(receipts=0.0, spending=0.0, hs_pos=0.0, hs_salaries=0.0))
        if r['type'] == 'R':
            d['receipts'] -= num(r['ytd_expended'])
        elif r['type'] == 'E':
            amt = num(r['ytd_expended']) + num(r['encumbrances'])
            d['spending'] += amt
            s = segs(r['account'])
            if s[3] == '3510' and s[4] == '06' and s[8] == '531006':
                d['hs_pos'] += amt
            if s[3] == '3510' and s[4] == '06' and s[8] == '519999':
                d['hs_salaries'] += amt
        else:
            fail('fund 1301 row of type %r: %s' % (r['type'], r['account']))
    if sorted(f) != [2023, 2024, 2025, 2026]:
        fail('fund 1301 is not in all four year-end reports: %s' % sorted(f))
    fund = []
    for fy in sorted(f):
        d = {k: round(v, 2) + 0.0 for k, v in f[fy].items()}
        if not d['receipts'] or not d['spending']:
            fail('FY%d fund 1301 has no receipts or no spending -- a join that matched nothing'
                 % fy)
        fund.append(dict(fy=fy, net=round(d['receipts'] - d['spending'], 2) + 0.0, **d))

    # Fund 1308: no expense account coded to transportation (function 3300, one of the
    # transportation object codes this page classifies by, or a description naming it), and
    # its transfer to the general fund is zero in every year. The page states both, so the
    # build refuses if either stops being true. (A 5350xx prefix is NOT a transportation
    # test: 535029 is course reimbursement.)
    s8 = [r for r in rows if r['fund'] == '1308' and r['type'] == 'E']
    if not s8:
        fail('fund 1308 has no expense rows -- a join that matched nothing')
    t_objs = {o for _, _, _, o in CATS}
    transport = [r['account'] for r in s8 if segs(r['account'])[3] == '3300'
                 or r['obj'] in t_objs
                 or re.search(r'TRANSP|\bBUS\b', r['description'], re.I)]
    if transport:
        fail('fund 1308 now carries a transportation-coded expense, which the page denies: %s'
             % transport)
    xfer = {}
    for r in s8:
        if 'TRANSFER' in r['description'].upper():
            fy = int(r['fiscal_year'])
            xfer[fy] = xfer.get(fy, 0.0) + num(r['ytd_expended']) + num(r['encumbrances'])
    if sorted(xfer) != [2023, 2024, 2025, 2026]:
        fail('fund 1308 has no transfer-out account in every year: %s' % sorted(xfer))
    if any(abs(v) > 0.005 for v in xfer.values()):
        fail('fund 1308 transferred money out, which the page denies: %s' % xfer)

    bal = [r for r in csv.DictReader(open(FUND_BAL, encoding='utf-8'))
           if r['fund_code'] == '1301' and r['measure'].startswith('ending_balance')]
    if len(bal) != 1:
        fail('fund-balances-fincom.csv holds %d ending balances for fund 1301, not one'
             % len(bal))
    return dict(fund=fund, by={x['fy']: x for x in fund}, xfer_years=sorted(xfer),
                last_balance=dict(amount=round(num(bal[0]['amount']), 2),
                                  as_of=bal[0]['as_of_date'], source=bal[0]['source_file']))


def load_model(book):
    """The site's projection, as published: its transport rate and its starting amount. Read,
    never changed here -- a contract rate beating a model default is flagged, not fixed."""
    mj = json.load(open(MODEL_JSON, encoding='utf-8'))
    rate_ = mj['assumptions']['transport']
    base = mj['expenseBase']['transport']
    if r0(base) != book['regular']['fy27_balanced']:
        fail('the model’s transport base (%s) is no longer the FY2027 regular-route budget '
             '(%s); the contract comparison is not like for like' % (base,
                                                                      book['regular']['fy27_balanced']))
    return dict(rate=rate_, base=base, fy28=round(base * (1 + rate_), 2))


# --------------------------------------------------------------------- measure

def measure():
    ledger, tie_years, ml = load_ledger()
    book = load_book(ml)
    k = load_contract()
    sp = load_sports(k)
    st = load_state(ledger)
    quotes = check_quotes()
    captions = check_captions()
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
    sched = load_schedules(k, sp)
    stest = schedule_test(k, sched, restore)
    top = sp['ranked'][:2]
    top5 = sum(r['fy2025'] for r in sp['ranked'][:5])
    spring25 = [s for s in sp['seasons'] if s['season'] == 'Spring' and s['fy'] == 2025][0]
    agree = sum(1 for c in sp['compare'] if c['agree'])
    audit = measure_audit(ledger, ml, book, k, sp, st, quotes, y, L, last, recent_over)

    return dict(
        audit=audit,
        ledger=ledger, tie_years=tie_years, book=book, contract=k, sports=sp, state=st,
        quotes=quotes, captions=captions, gaps=gaps, fees=fees, first=ledger[0]['fy'], last=last, L=L, share=share,
        hi_share=hi_share, lo_share=lo_share, sped_low=sped_low, sped_over=sped_over,
        recent_over=recent_over, sped_under_run=sped_under_run, step=step, reg25=reg25, fleet_a=fleet_a, fleet_b=fleet_b,
        fy26_avg=fy26_avg, rises=rises, netted=netted, moved_back=moved_back, fy27=fy27,
        sched=sched, stest=stest, field_trip=field_trip, restore=restore, requests=requests, unpaid=unpaid, reclass=reclass,
        restore_town=restore_town, restore_fund=restore_fund,
        top=top, top5=top5,
        spring25=spring25, agree=agree, ystep=y)


def measure_audit(ledger, ml, book, k, sp, st, quotes, y, L, last, recent_over):
    """The eight comparisons of notes/process/AUDIT-PASS.md, run against this page's data.
    Every figure here is a COMPARISON -- one measured thing set against another it was
    supposed to equal. Budget against budget, actual against actual, except test 2, which is
    spent against the revised budget by definition, and test 8, which sets the next budget
    beside the latest actual as a comparison and never as a projection (rule 1)."""
    by = {r['fy']: r for r in ledger}
    A = {}

    # Test 2, control: every line closed past its REVISED budget, every year.
    A['overdrawn'] = [dict(fy=r['fy'], cat=c, revised=r[c]['revised'], spent=r[c]['spent'],
                           over=r[c]['over_revised'], transfer=r[c]['transfer'])
                      for r in ledger for c in CAT_NAME if r[c]['over_revised'] >= 1]
    s26 = ml[(last, 'sped')]
    A['sped26'] = dict(voted=r0(s26[0]), revised=r0(s26[1]), expended=r0(s26[2]),
                       committed=r0(s26[3]), spent=r0(s26[2] + s26[3]),
                       over=r0(s26[2] + s26[3] - s26[1]), transfer=r0(s26[1] - s26[0]))
    if A['sped26']['over'] <= 0:
        fail('FY%d special education transportation no longer closed past its revised budget'
             % last)
    if abs(s26[1] - s26[0]) > 0.01 * A['sped26']['over']:
        fail('a transfer now covers part of the FY%d special education overrun; the card says '
             'none did' % last)
    A['sped27'] = book['sped']['fy27_balanced']
    A['sped27_margin'] = r0(book['sped']['fy27_balanced'] - (s26[2] + s26[3]))
    A['sped_rise'] = pct1(L['sped']['spent'] - by[last - 1]['sped']['spent'],
                          by[last - 1]['sped']['spent'])
    A['sped25'] = by[last - 1]['sped']['spent']
    o24 = {c: by[2024][c]['over_revised'] for c in SCHOOL_DAY}
    if not all(v > 0 for v in o24.values()):
        fail('FY2024 school-day lines no longer both closed past their revised budgets')
    A['fy24'] = dict(regular=o24['regular'], sped=o24['sped'],
                     both=r0(sum(ml[(2024, c)][2] + ml[(2024, c)][3] - ml[(2024, c)][1]
                                 for c in SCHOOL_DAY)),
                     reg_transfer=by[2024]['regular']['transfer'],
                     reg_spent=by[2024]['regular']['spent'],
                     reg25_spent=by[2025]['regular']['spent'])
    if not A['fy24']['reg_spent'] > A['fy24']['reg25_spent']:
        fail('FY2024 regular routes no longer cost more than FY2025')

    # Test 1, credibility: the special education line's DIRECTION, held for years.
    run = [r for r in ledger if 2016 <= r['fy'] <= 2023]
    under = {r['fy']: r['sped']['budget'] - r['sped']['spent'] for r in run}
    start = min(fy for fy, v in under.items() if v > BIG_GAP)
    cut = min(run, key=lambda r: r['sped']['budget'])['fy']
    prior = [r['fy'] for r in ledger if r['fy'] < cut
             and r['sped']['budget'] <= by[cut]['sped']['budget']]
    if not prior:
        fail('the FY%d special education budget is the lowest in the series' % cut)
    A['lag'] = dict(start=start, cut=cut, years=cut - start + 1,
                    sum=sum(under[f] for f in range(start, cut + 1)),
                    pre=sum(under[f] for f in range(start, 2020)),
                    lo=min(under.values()), hi=max(under.values()),
                    run0=run[0]['fy'], run1=run[-1]['fy'], all=sum(under.values()),
                    cut_budget=by[cut]['sped']['budget'], since=max(prior),
                    over=[dict(fy=x['fy'], over=x['over']) for x in recent_over])

    # Test 7, an offset that masks: FY2027 budget against FY2026 budget.
    sd26 = by[last]['school_budget']
    sd27 = sum(book[c]['fy27_balanced'] for c in SCHOOL_DAY)
    all26 = by[last]['all_budget']
    all27 = sum(book[c]['fy27_balanced'] for c in CAT_NAME)
    if sd26 != sum(book[c]['fy26_final'] for c in SCHOOL_DAY):
        fail('the FY2026 school-day budget no longer ties to the budget book')
    A['mask'] = dict(sd26=sd26, sd27=sd27, sd_rise=sd27 - sd26, sd_pct=pct1(sd27 - sd26, sd26),
                     all26=all26, all27=all27, all_pct=pct1(all27 - all26, all26),
                     ath_cut=book['athletic']['fy26_final'] - book['athletic']['fy27_balanced'],
                     band26=book['band']['fy26_final'], band27=book['band']['fy27_balanced'])
    A['mask']['offset_pct'] = pct1(A['mask']['ath_cut'], A['mask']['sd_rise'])

    # Test 3, who pays: the fee year's regular routes against the contract.
    reg = L['regular']
    if reg['spent'] != r0(y[2026]['regular']):
        fail('FY2026 regular routes no longer spent exactly the contract price')
    A['feeyear'] = dict(voted=reg['budget'], transfer=reg['transfer'], spent=reg['spent'],
                        price=y[2026]['regular'],
                        receipts=round(st['fee'][2025] + st['fee'][2026], 2))

    # Test 3 and test 4: the athletic fee fund, receipts against spending.
    ff = load_fee_funds()
    fb = ff['by']
    A['fund'] = ff
    A['fund_short'] = r0(-(fb[2023]['net'] + fb[2024]['net']))
    A['fund_ahead'] = r0(fb[2025]['net'] + fb[2026]['net'])
    if A['fund_short'] <= 0 or A['fund_ahead'] <= 0:
        fail('fund 1301 no longer ran short in FY2023-FY2024 and ahead in FY2025-FY2026')
    A['reclass25'] = by[2025]['athletic']['transfer']

    # Test 4, said against did: the FY2027 restoration split, and FY2024's town share.
    qd = {q['key']: q['quote'] for q in quotes}
    m_ = [float(x.replace(',', '')) for x in re.findall(r'\$([\d,]+(?:\.\d+)?)', qd['restore'])]
    restore, rounded, town, fundpart = m_
    if town + fundpart != rounded:
        fail('the restoration split no longer sums to the rounded figure')
    A['restore'] = dict(estimate=restore, rounded=rounded, town=town, fund=fundpart,
                        fund_pct=pct1(fundpart, rounded), town_pct=pct1(town, rounded),
                        town24_pct=pct1(by[2024]['athletic']['budget'], sp['totals'][2024]),
                        hs25=round(sum(r['fy2025'] or 0 for r in sp['rows']
                                       if r['level'] == 'HS'), 2))

    # Test 5, locked-in growth: the contract against the model's rate.
    mo = load_model(book)
    A['model'] = dict(mo, contract28=y[2028]['regular'], contract_pct=pct1(
        y[2028]['regular'] - y[2027]['regular'], y[2027]['regular']),
        gap=r0(y[2028]['regular'] - mo['fy28']))

    # Test 6, two sources, one quantity: the two per-sport sheets on the sports both print.
    c24 = [c for c in sp['compare'] if c['fy'] == 2024]
    A['sheets'] = dict(n=len(c24), agree=sum(1 for c in c24 if c['agree']),
                       workbook=round(sum(c['workbook'] for c in c24), 2),
                       fincom=round(sum(c['fincom'] for c in c24), 2),
                       widest=max(c24, key=lambda c: c['workbook'] / c['fincom']
                                  if c['fincom'] else 0))
    A['sheets']['lower_pct'] = pct1(A['sheets']['workbook'] - A['sheets']['fincom'],
                                    A['sheets']['workbook'])
    # The cheap test: identical figures in paired rows are an allocation, not a measurement.
    pairs = {}
    for r in sp['rows']:
        for fy in (2024, 2025):
            v = r['fy%d' % fy]
            if v:
                pairs.setdefault((r['season'], r['level'], fy, v), []).append(r['sport'])
    A['paired'] = sorted([dict(season=s, level=lv, fy=fy, value=v, sports=sorted(n))
                          for (s, lv, fy, v), n in pairs.items() if len(n) > 1],
                         key=lambda x: (x['fy'], SEASONS.index(x['season']), x['sports']))
    spring = {s['fy']: s for s in sp['seasons'] if s['season'] == 'Spring'}
    A['spring'] = dict(rows24=spring[2024]['rows'], rows25=spring[2025]['rows'],
                       printed25=spring[2025]['printed'],
                       fall_pct=pct1(spring[2025]['rows'] - spring[2024]['rows'],
                                     spring[2024]['rows']),
                       share_of_drop=pct1(spring[2024]['rows'] - spring[2025]['rows'],
                                          sp['totals'][2024] - sp['totals'][2025]))

    # Which TEAM's buses cost most. The workbook prints boys' and girls' rows for sports that
    # share a bus and a coach, and halves the cost between them -- the paired rows above. Read
    # row by row, a split sport sinks down the ranking; read as one team, it is added back.
    # Only the pairs the cheap test found are merged, never two sports that merely cost the
    # same, and a merged pair is asserted to be in one season at one level.
    team = {}
    for fy in (2024, 2025):
        grp = {}
        for r in sp['rows']:
            v = r['fy%d' % fy]
            if not v:
                continue
            p_ = [x for x in A['paired'] if x['fy'] == fy and r['sport'] in x['sports']
                  and x['season'] == r['season'] and x['level'] == r['level']]
            key = (r['season'], r['level'], tuple(p_[0]['sports'])) if p_ else \
                (r['season'], r['level'], (r['sport'],))
            grp[key] = round(grp.get(key, 0) + v, 2)
        team[fy] = sorted(([dict(season=k_[0], level=k_[1], sports=list(k_[2]), cost=v)
                            for k_, v in grp.items()]), key=lambda t: -t['cost'])
    it = lambda fy: [t for t in team[fy] if t['sports'] == ['Indoor Track - Boys',
                                                           'Indoor Track - Girls']][0]
    fc = {(c['fy'], c['name']): c for c in sp['compare']}
    fin_rank = {fy: sorted([c for c in sp['compare'] if c['fy'] == fy],
                           key=lambda c: -c['fincom']) for fy in (2024, 2025)}
    A['track'] = dict(
        teams=team,
        it24=it(2024)['cost'], it25=it(2025)['cost'],
        it24_row=it(2024)['cost'] / 2,
        rank24=team[2024].index(it(2024)) + 1, rank25=team[2025].index(it(2025)) + 1,
        second24=team[2024][1], second25=team[2025][1],
        fin24=fc[(2024, 'Indoor Track')]['fincom'], fin25=fc[(2025, 'Indoor Track')]['fincom'],
        fin_rank24=[c['name'] for c in fin_rank[2024]].index('Indoor Track') + 1,
        fin_rank25=[c['name'] for c in fin_rank[2025]].index('Indoor Track') + 1,
        out25_row=[r for r in sp['rows'] if r['sport'] == 'Boys Track'][0]['fy2025'],
        soccer24=[r for r in sp['rows'] if r['sport'] == 'Girls Soccer'][0]['fy2024'],
        soccer25=[r for r in sp['rows'] if r['sport'] == 'Girls Soccer'][0]['fy2025'],
    )
    if A['track']['rank24'] != 1 or A['track']['rank25'] != 1:
        fail('indoor track, read as one team, is no longer the costliest on the workbook')
    return A


# --------------------------------------------------------------------- conclusions

def fyf(y):
    return figure(y, C.fy(y), 'fiscal year')


def mi1(v):
    return '%.1f' % v


def nfmt(v):
    return C.num(v) if float(v).is_integer() else '%.1f' % v


def build_conclusions(m):
    """The summary, from the audit pass (notes/process/AUDIT-PASS.md), ranked as
    notes/findings/TRANSPORTATION-AUDIT.md ranks it: dollars at stake, weighted by whether a
    board can act on it this budget season. Every card is a COMPARISON. The contested ones
    -- the bus fee, the fee fund, the restored buses, the two sheets -- set two measured
    things side by side and end on a question for the budget, never a charge (rule 8).
    Every cause is a hypothesis and says so (rule 7)."""
    A, L, last, k, sp, st = m['audit'], m['L'], m['last'], m['contract'], m['sports'], m['state']
    y = m['ystep']
    rows = []
    U = lambda v: figure(v, C.usd(v))

    # 1. Control, and a thin margin: the special education line, FY2026.
    s = A['sped26']
    rows.append(conclusion(
        id='sped-buses-over-budget', bearing='lever', kind='measured', figure='over',
        claim='Special education buses closed %s %s past their budget, and no transfer covered it.'
              % (C.fy(last), C.usd(s['over'])),
        so_what='%s budgets %s above what %s spent, after spending rose %s in one year.'
                % (C.fy(2027), C.usd(A['sped27_margin']), C.fy(last), C.pct(A['sped_rise'])),
        detail='Voted %s and revised to %s; %s paid out and %s still committed at the close, %s '
               'in all. %s spent %s. The %s balanced budget carries %s for the line. The '
               'district’s FY2026 budget overview attributes the line’s growth to a 7%% rate '
               'increase and more vans and monitors; that is its explanation, and nothing here '
               'tests it. The School Committee holds the line during the year; the Finance '
               'Committee weighs the next budget against it.'
               % (C.usd(s['voted']), C.usd(s['revised']), C.usd(s['expended']),
                  C.usd(s['committed']), C.usd(s['spent']), C.fy(last - 1), C.usd(A['sped25']),
                  C.fy(2027), C.usd(A['sped27'])),
        figures={'over': U(s['over']), 'fy': fyf(last), 'fy27': fyf(2027),
                 'margin': U(A['sped27_margin']),
                 'rise': figure(A['sped_rise'], C.pct(A['sped_rise'])),
                 'voted': U(s['voted']), 'revised': U(s['revised']), 'paid': U(s['expended']),
                 'committed': U(s['committed']), 'spent': U(s['spent']), 'fy25': fyf(last - 1),
                 'spent25': U(A['sped25']), 'b27': U(A['sped27'])},
        allow=('7%',),
        basis='MUNIS FY2026 year-end report, special education transportation (function 3300, '
              'object 535026): original appropriation, revised budget, expended and '
              'encumbered; the district’s FY2027 budget book, balanced scenario. Spent against '
              'the REVISED budget is the test of control; the FY2027 figure is set beside '
              'FY2026’s spending as a comparison, never as a projection.',
        not_shown='Why it overran. The van contract is not in the archive, so price, routes, '
                  'children and monitors cannot be separated; the circuit breaker repays part of '
                  'out-of-district transportation a year later and is never netted here.',
        see=[('/analysis/special-education-costs', 'Special education costs')],
    ))

    # 2. Credibility: the same line's budget, against its spending, for years.
    g = A['lag']
    rows.append(conclusion(
        id='sped-budget-trailed-spending', bearing='sizes', kind='measured', figure='sum',
        claim='From %s to %s the special education bus line was budgeted %s above its spending.'
              % (C.fy(g['start']), C.fy(g['cut']), C.usd(g['sum'])),
        so_what='Its %s budget fell to %s, the lowest since %s; it then ran over in %s.'
                % (C.fy(g['cut']), C.usd(g['cut_budget']), C.fy(g['since']),
                   ' and '.join(C.fy(x['fy']) for x in g['over'])),
        detail='It came in under its voted budget every year from %s to %s, by %s to %s; %s of '
               'the gap in the window was %s to %s, before the 2020 school closures. Against '
               'the voted budget it ran over by %s. The window is ours: it opens in '
               'the first year the gap passed %s and closes in the year the budget was cut. '
               'What the data shows is a budget trailing its spending in both directions. Why '
               'is a hypothesis, untested: a budget set from the prior year’s actual would draw '
               'this shape, and so would placements arriving and leaving between budget and '
               'year.'
               % (C.fy(g['run0']), C.fy(g['run1']), C.usd(g['lo']), C.usd(g['hi']),
                  C.usd(g['pre']), C.fy(g['start']), C.fy(2019),
                  ' and '.join('%s in %s' % (C.usd(x['over']), C.fy(x['fy'])) for x in g['over']),
                  C.usd(BIG_GAP)),
        figures=dict({'sum': U(g['sum']), 'start': fyf(g['start']), 'cut': fyf(g['cut']),
                      'cutb': U(g['cut_budget']), 'since': fyf(g['since']),
                      'run0': fyf(g['run0']), 'run1': fyf(g['run1']), 'lo': U(g['lo']),
                      'hi': U(g['hi']), 'pre': U(g['pre']), 'fy19': fyf(2019),
                      'big': U(BIG_GAP)},
                     **{'o%d' % x['fy']: U(x['over']) for x in g['over']},
                     **{'ofy%d' % x['fy']: fyf(x['fy']) for x in g['over']}),
        allow=('2020',),
        basis='General fund special education transportation account, voted budget against '
              'spent at the close, every year: MUNIS year-end reports FY2023 to FY2026, the '
              'Finance Committee’s ledger history before that, tied to MUNIS where both exist.',
        not_shown='Two of the window’s years are the 2020 and 2021 closures, when buses barely '
                  'ran; the pre-closure part is given separately. How many children, vans and '
                  'routes each year paid for is not published.',
    ))

    # 3. An offset that masks: FY2027's school-day buses under a flat-looking total.
    x = A['mask']
    rows.append(conclusion(
        id='school-day-rise-offset', bearing='sizes', kind='measured', figure='sd',
        claim='%s’s school-day bus budget rises %s; the transportation total rises only %s.'
              % (C.fy(2027), C.pct(x['sd_pct']), C.pct(x['all_pct'])),
        so_what='Cutting athletic buses, %s, offset %s of the %s school-day rise.'
                % (C.usd(x['ath_cut']), C.pct(x['offset_pct'], 0), C.usd(x['sd_rise'])),
        detail='Regular routes and special education were voted %s for %s and carry %s in the '
               '%s balanced budget. All four transportation lines go from %s to %s, because '
               'athletic buses go to %s and band trips from %s to %s. Budget to budget '
               'throughout. The two lines that carry children to school are the ones rising.'
               % (C.usd(x['sd26']), C.fy(last), C.usd(x['sd27']), C.fy(2027),
                  C.usd(x['all26']), C.usd(x['all27']), C.usd(0), C.usd(x['band26']),
                  C.usd(x['band27'])),
        figures={'sd': figure(x['sd_pct'], C.pct(x['sd_pct'])),
                 'all': figure(x['all_pct'], C.pct(x['all_pct'])),
                 'cut': U(x['ath_cut']), 'off': figure(x['offset_pct'], C.pct(x['offset_pct'], 0)),
                 'rise': U(x['sd_rise']), 'fy27': fyf(2027), 'fy': fyf(last),
                 'sd26': U(x['sd26']), 'sd27': U(x['sd27']), 'all26': U(x['all26']),
                 'all27': U(x['all27']), 'zero': U(0), 'band26': U(x['band26'])},
        basis='MUNIS FY2026 original appropriations; the district’s FY2027 budget book, '
              'balanced scenario, whose FY2026 column ties to MUNIS line by line.',
        not_shown='A budget is not a cost: the regular-route rise is the contract’s second-year '
                  'price, and the special education rise is a budget, not a measured change in '
                  'routes or children.',
    ))

    # 4. Who pays: the bus fee's first year against the regular-route contract.
    f = A['feeyear']
    rows.append(conclusion(
        id='bus-fee-and-the-bill', bearing='lever', kind='measured', figure='paid',
        claim='In the bus fee’s first year, the general fund still paid the full %s bus contract.'
              % C.usd(f['spent']),
        so_what='The fee’s candidate account took in %s; its fund spent nothing on buses. What '
                'does the fee pay for?' % C.usd(st['fee'][2026]),
        detail='%s regular routes were voted at %s, %s under the contract’s %s — the amount the '
               'Finance Committee was told the fee cut — then %s was transferred in and %s '
               'spent. In the school choice fund (1308), account 437601, SCH. CHOICE BUS FEE, '
               'took in %s in %s and %s in %s, %s in two years. From %s to %s that fund has no '
               'expense account coded to transportation, and its transfer to the general fund '
               'is zero every year. Measured: the general fund paid the whole contract. A '
               'hypothesis: the fund 1308 receipts are the fees.'
               % (C.fy(last), C.usd(f['voted']), C.usd(m['netted']), C.usd(f['price']),
                  C.usd(f['transfer']), C.usd(f['spent']), usd2(st['fee'][2025]), C.fy(2025),
                  usd2(st['fee'][2026]), C.fy(2026), usd2(f['receipts']), C.fy(2023),
                  C.fy(2026)),
        figures={'paid': U(f['spent']), 'rec': U(st['fee'][2026]), 'fy': fyf(last),
                 'voted': U(f['voted']), 'net': U(m['netted']), 'price': U(f['price']),
                 'xfer': U(f['transfer']),
                 'f25': figure(st['fee'][2025], usd2(st['fee'][2025])),
                 'f26': figure(st['fee'][2026], usd2(st['fee'][2026])),
                 'both': figure(f['receipts'], usd2(f['receipts'])),
                 'fy25': fyf(2025), 'fy23': fyf(2023)},
        allow=('1308', '437601'),
        basis='MUNIS FY2026 year-end report, account 535025: original appropriation, transfers, '
              'expended; the contract’s FY2026 price; Finance Committee minutes, 20 March 2025; '
              'MUNIS school special funds, fund 1308, every account, FY2023 to FY2026.',
        not_shown='Whether the fund 1308 receipts are the fees is not established: the account '
                  'is named for school choice. How many families paid is not published. What '
                  'the fee was meant to fund is a question for the budget to answer.',
        see=[('/what-families-pay', 'What families pay')],
    ))

    # 5. Said against did: the FY2027 restoration, and the 2025 correction.
    r = A['restore']
    rows.append(conclusion(
        id='restored-buses-on-the-fee-fund', bearing='lever', kind='measured', figure='pct',
        claim='The %s plan puts %s of restored athletic buses back on the athletic fee fund.'
              % (C.fy(2027), C.pct(r['fund_pct'], 0)),
        so_what='In March 2025, moving them off it was called a correction. Nothing published '
                'yet says which practice holds.',
        detail='On 26 August 2026 the Superintendent put restoring high school buses at %s, '
               'rounded to %s: %s from the town and %s from the athletic revolving account. On '
               '12 March 2025 a School Committee member said athletic transportation accounting '
               '“has been corrected from past practice that was done incorrectly”, and in April '
               'transfers moved costs charged to the revolving account onto the town line. In '
               '%s the town line was %s of %s on the higher of the district’s two sheets, %s; '
               'the %s plan’s town share is %s.'
               % (C.usd(r['estimate']), C.usd(r['rounded']), C.usd(r['town']),
                  C.usd(r['fund']), C.fy(2024), C.usd(m['ledger'][[q['fy'] for q in m['ledger']].index(2024)]['athletic']['budget']),
                  C.usd(sp['totals'][2024]), C.pct(r['town24_pct'], 0), C.fy(2027),
                  C.pct(r['town_pct'], 0)),
        figures={'pct': figure(r['fund_pct'], C.pct(r['fund_pct'], 0)), 'fy27': fyf(2027),
                 'est': U(r['estimate']), 'rnd': U(r['rounded']), 'town': U(r['town']),
                 'fund': U(r['fund']), 'fy24': fyf(2024),
                 'line24': U(m['ledger'][[q['fy'] for q in m['ledger']].index(2024)]['athletic']['budget']),
                 'sheet24': U(sp['totals'][2024]),
                 't24': figure(r['town24_pct'], C.pct(r['town24_pct'], 0)),
                 't27': figure(r['town_pct'], C.pct(r['town_pct'], 0))},
        allow=('March 2025', '26 August 2026', '12 March 2025'),
        basis='School Committee minutes, 26 August 2026, 12 March 2025 and 16 April 2025, each '
              'quotation re-read from the archive on every build; the district’s by-sport '
              'workbook; the general fund athletic transportation account.',
        not_shown='Whether Special Town Meeting funded the town’s share is not in the ledgers '
                  'held yet. The 2025 statement concerned how costs were accounted for; whether '
                  'the plan is the same practice is the question, not a finding.',
    ))

    # 5a. The FY2027 estimate's stated reasons, against the posted schedules. A comparison of
    # two measured things -- this autumn's schedule and last autumn's -- and the reasons are
    # hers, quoted; nothing here says the estimate is wrong (rule 8).
    t = m['stest']
    fall = [x for x in t['seasons'] if x['season'] == 'fall'][0]
    if not fall['complete']:
        fail('the FY2027 autumn schedule is no longer complete enough to compare')
    fy_ = {x['fy']: x for x in fall['years']}
    a27, a26 = fy_[2027], fy_[2026]
    more = 'a larger share' if a27['home_pct'] > a26['home_pct'] else 'a smaller share'
    nearer = a27['miles_avg'] < a26['miles_avg']
    so = t['so_far'][0]
    rows.append(conclusion(
        id='fy27-schedule-against-the-estimate', bearing='lever', kind='measured',
        figure='home27',
        claim='%s’s autumn schedule puts %s of high school games at home; %s’s put %s.'
              % (C.fy(2027), C.pct(a27['home_pct']), C.fy(2026), C.pct(a26['home_pct'])),
        so_what='The %s estimate credits more home games. Away trips average %s miles round '
                'trip, against %s in %s.' % (C.fy(2027), mi1(a27['miles_avg']),
                                             mi1(a26['miles_avg']), C.fy(2026)),
        detail='The Superintendent attributed the %s estimate, %s, partly to scheduling '
               'competitions closer to Lunenburg and increasing home competitions. On the %s '
               'high school teams whose %s autumn schedule is posted in full, %s schedules %s '
               'home games of %s, %s than %s’s %s of %s; %s had %s and %s %s. Away trips, '
               'measured as driving miles from the high school to each venue, average %s miles '
               'round trip against %s, %s and %s%s. Our bus model prices the %s autumn '
               'high school schedule at %s to %s at %s rates, %s to %s of it waiting at '
               'four hours a trip; winter is partly posted and spring not at all, so no '
               'full-year figure for %s exists to set beside %s.'
               % (C.fy(2027), C.usd(t['estimate']), C.num(len(fall['teams'])), C.fy(2027),
                  C.fy(2027), C.num(a27['home']), C.num(a27['games']), more, C.fy(2026),
                  C.num(a26['home']), C.num(a26['games']), C.fy(2025), C.pct(fy_[2025]['home_pct']),
                  C.fy(2024), C.pct(fy_[2024]['home_pct']), mi1(a27['miles_avg']),
                  mi1(a26['miles_avg']), mi1(fy_[2025]['miles_avg']), mi1(fy_[2024]['miles_avg']),
                  '' if nearer else ', not shorter', C.fy(2027), C.usd(so['lo']),
                  C.usd(so['hi']), C.fy(2027), C.usd(so['lo'] - so['lo_miles']),
                  C.usd(so['hi'] - so['hi_miles']), C.fy(2027), C.usd(t['estimate'])),
        figures={'home27': figure(a27['home_pct'], C.pct(a27['home_pct'])),
                 'home26': figure(a26['home_pct'], C.pct(a26['home_pct'])),
                 'fy27': fyf(2027), 'fy26': fyf(2026), 'fy25': fyf(2025), 'fy24': fyf(2024),
                 'mi27': figure(a27['miles_avg'], mi1(a27['miles_avg']), 'miles'),
                 'mi26': figure(a26['miles_avg'], mi1(a26['miles_avg']), 'miles'),
                 'mi25': figure(fy_[2025]['miles_avg'], mi1(fy_[2025]['miles_avg']), 'miles'),
                 'mi24': figure(fy_[2024]['miles_avg'], mi1(fy_[2024]['miles_avg']), 'miles'),
                 'est': U(t['estimate']), 'teams': figure(len(fall['teams']),
                                                          C.num(len(fall['teams'])), 'teams'),
                 'h27': figure(a27['home'], C.num(a27['home']), 'games'),
                 'g27': figure(a27['games'], C.num(a27['games']), 'games'),
                 'h26': figure(a26['home'], C.num(a26['home']), 'games'),
                 'g26': figure(a26['games'], C.num(a26['games']), 'games'),
                 'p25': figure(fy_[2025]['home_pct'], C.pct(fy_[2025]['home_pct'])),
                 'p24': figure(fy_[2024]['home_pct'], C.pct(fy_[2024]['home_pct'])),
                 'lo': U(so['lo']), 'hi': U(so['hi']), 'wlo': U(so['lo'] - so['lo_miles']),
                 'whi': U(so['hi'] - so['hi_miles'])},
        basis='Every high school game ArbiterLive lists for the teams whose %s autumn schedule '
              'is posted in full, canceled and postponed games left out, read on %s; venue '
              'distances are OUR measurement, driving routes on OpenStreetMap. The quotation is '
              'the School Committee minutes of 26 August 2026, re-read on every build. The bus '
              'model is OUR ESTIMATE.' % (C.fy(2027), t['fetched']),
        not_shown='The autumn is not over: games can still be added. Whether a bus went to any '
                  'game, or was shared, is not recorded; how the district built its estimate '
                  'is not published.',
        allow=('26 August 2026', t['fetched']),
    ))

    # 6. The fee fund: receipts against spending, and the reclassification in the same card.
    ff = A['fund']['by']
    rows.append(conclusion(
        id='fee-fund-receipts-against-spending', bearing='sizes', kind='measured',
        figure='short',
        claim='The athletic fee fund spent %s more than it took in over %s and %s.'
              % (C.usd(A['fund_short']), C.fy(2023), C.fy(2024)),
        so_what='Over %s and %s it took in %s more, after costs were reclassified off it. %s '
                'draws %s.' % (C.fy(2025), C.fy(2026), C.usd(A['fund_ahead']), C.fy(2027),
                               C.usd(r['fund'])),
        detail='Receipts against spending, fund 1301: %s. The district’s FY2026 budget overview '
               'says the “athletic revolving can not support these increased costs”, which fits '
               'the first two years. The surplus came after costs moved to the town line: %s was '
               'transferred into the general fund athletic line in %s, and the fund’s high '
               'school salaries account closed that year at %s, which is what a '
               'reclassification out looks like (our reading). No balance after %s is '
               'published.'
               % ('; '.join('%s %s in, %s out' % (C.fy(q), C.usd(ff[q]['receipts']),
                                                   C.usd(ff[q]['spending'])) for q in sorted(ff)),
                  C.usd(A['reclass25']), C.fy(2025), C.usd(ff[2025]['hs_salaries']),
                  C.fy(2020)),
        figures=dict({'short': U(A['fund_short']), 'ahead': U(A['fund_ahead']),
                      'fy23': fyf(2023), 'fy24': fyf(2024), 'fy25': fyf(2025),
                      'fy26': fyf(2026), 'fy27': fyf(2027), 'draw': U(r['fund']),
                      'reclass': U(A['reclass25']), 'sal': U(ff[2025]['hs_salaries']),
                      'fy20': fyf(2020)},
                     **{'in%d' % q: U(ff[q]['receipts']) for q in ff},
                     **{'out%d' % q: U(ff[q]['spending']) for q in ff}),
        allow=('1301',),
        basis='MUNIS school special funds year-end reports, fund 1301, FY2023 to FY2026: '
              'revenue rows against expended plus encumbered; the general fund athletic '
              'transportation account’s FY2025 transfer; the FY2026 budget overview.',
        not_shown='The fund’s year-end balances are printed on different bases (cash in one year, '
                  'fund balance in another), so they are not one series. In FY2026 its '
                  'purchase-of-service account spent about what it did in FY2024; what that bought '
                  'is not itemised.',
        see=[('/athletics/fee-fund-history', 'The athletic fee fund, year by year'),
             ('/analysis/athletics-ledger', 'The athletics fee fund, line by line')],
    ))

    # 7. Locked-in growth: the contract against the model.
    mo = A['model']
    rows.append(conclusion(
        id='contract-outruns-the-model', bearing='lever', kind='measured', figure='gap',
        claim='The signed bus contract rises %s into %s; this site’s model grows the line %s.'
              % (C.pct(mo['contract_pct']), C.fy(2028), C.pct(100 * mo['rate'], 0)),
        so_what='That leaves the model’s %s regular routes %s under a price already fixed.'
                % (C.fy(2028), C.usd(mo['gap'])),
        detail='The contract fixes %s regular routes at %s for %s buses, %s days, after %s in '
               '%s — and the %s budget carries that price to the dollar. The model starts from '
               '%s and applies its default rate: %s. The contract ends 30 June 2028; two option '
               'years are priced at %s and %s. Special education transportation is not in this '
               'line; the model grows it with special education.'
               % (C.fy(2028), C.usd(mo['contract28']), C.num(N77 + N83), C.num(DAYS),
                  C.usd(y[2027]['regular']), C.fy(2027), C.fy(2027), C.usd(mo['base']),
                  C.usd(mo['fy28']), C.usd(y[2029]['regular']), C.usd(y[2030]['regular'])),
        figures={'gap': U(mo['gap']), 'cpct': figure(mo['contract_pct'], C.pct(mo['contract_pct'])),
                 'rate': figure(mo['rate'], C.pct(100 * mo['rate'], 0)), 'fy28': fyf(2028),
                 'p28': U(mo['contract28']), 'buses': figure(N77 + N83, C.num(N77 + N83), 'buses'),
                 'days': figure(DAYS, C.num(DAYS), 'days'), 'p27': U(y[2027]['regular']),
                 'fy27': fyf(2027), 'base': U(mo['base']), 'm28': U(mo['fy28']),
                 'o29': U(y[2029]['regular']), 'o30': U(y[2030]['regular'])},
        allow=('30 June 2028',),
        basis='The Dee Bus bid form (Exhibit E), every rate checked against its printed totals; '
              'the agreement’s term; the district’s FY2027 budget book; this site’s model as '
              'published (model.json: the transport rate and its starting amount). The model '
              'is OURS.',
        not_shown='The contract fixes a price per bus; it does not fix how many buses run, and '
                  'the district may add or drop up to two a year at the same unit prices.',
    ))

    # 8. Two sources, one quantity: the two per-sport sheets.
    h = A['sheets']
    wd = h['widest']
    rows.append(conclusion(
        id='two-sheets-one-cost', bearing='sizes', kind='measured', figure='hi',
        claim='The district’s two athletic bus sheets price the same %s sports at %s and %s.'
              % (C.fy(2024), C.usd(h['workbook']), C.usd(h['fincom'])),
        so_what='Both are above the %s town line. Nothing published says which sheet is right.'
                % C.usd(m['ledger'][[q['fy'] for q in m['ledger']].index(2024)]['athletic']['budget']),
        detail='The by-sport workbook (records request) and the Finance Committee’s copy of a '
               'second sheet both print transportation for %s sports in %s; %s agree to the cent '
               'and %s do not. The widest: %s, %s in one and %s in the other. The workbook’s '
               'total for every sport it lists is %s. Both are hand-assembled and neither is a '
               'ledger, so this page publishes the spread and picks neither.'
               % (C.num(h['n']), C.fy(2024), C.num(h['agree']), C.num(h['n'] - h['agree']),
                  wd['name'], usd2(wd['workbook']), usd2(wd['fincom']),
                  C.usd(sp['totals'][2024])),
        figures={'hi': U(h['workbook']), 'lo': U(h['fincom']), 'fy24': fyf(2024),
                 'line': U(m['ledger'][[q['fy'] for q in m['ledger']].index(2024)]['athletic']['budget']),
                 'n': figure(h['n'], C.num(h['n']), 'sports'),
                 'agree': figure(h['agree'], C.num(h['agree']), 'sports'),
                 'differ': figure(h['n'] - h['agree'], C.num(h['n'] - h['agree']), 'sports'),
                 'w1': figure(wd['workbook'], usd2(wd['workbook'])),
                 'w2': figure(wd['fincom'], usd2(wd['fincom'])),
                 'all': U(sp['totals'][2024])},
        basis='The district’s sport-by-sport workbook (records request, June 2026) and '
              '“Athletics Costs (1).xlsx” from the Finance Committee’s FY2026 budget files, '
              'matched sport by sport through a crosswalk that is ours; the general fund '
              'athletic transportation account.',
        not_shown='Which figure is right. Paired sports carry identical figures in both sheets, '
                  'so per-sport amounts are allocations, not measurements. No trip count is '
                  'published for any year.',
        see=[('/what-sports-cost', 'What sports cost')],
    ))
    return emit(ID, rows)


# --------------------------------------------------------------------- the brief

# THE EVIDENCE SECTIONS, by key. The brief's chains link into these headings and the markdown
# writes them, from this one table, so a link cannot point at a heading that was renamed.
H = {
    'evidence': 'The evidence, answer by answer',
    'overdrawn': 'Lines that closed the year past their revised budget',
    'lag': 'Special education: budgeted above its spending for years, then below it',
    'regular': 'Regular routes: the budget against the contract',
    'mask': 'FY2027: the school-day rise under a flat-looking total',
    'fee': 'The bus fee and the general fund',
    'fund': 'The athletic fee fund: receipts against spending',
    'restore': 'The FY2027 restoration: the plan against the sheet and the fund',
    'track': 'Which sport’s buses cost most: track, once its two rows are added together',
    'sheet': 'The sheet against the schedules',
    'sched27': 'The FY2027 estimate against the posted schedules',
    'model': 'The contract against this site’s model',
    'contract': '4. The Dee Bus contract: what is fixed, and what the 7.6% was',
    'sec2': '2. Athletic transportation: what it costs and who has paid',
    'sec5': '5. What pays for it: the fee, the fee fund, the state',
    'sec6': '6. Special education transportation',
}


def slug(text):
    """The same anchor fy28/src/lib/markdown.tsx's slugify() gives a heading."""
    t = re.sub(r'[`*_\[\]()]', '', text.lower())
    return re.sub(r'^-+|-+$', '', re.sub(r'[^a-z0-9]+', '-', t)) or 'section'


def build_brief(m):
    """The top of the page, citizen-first (notes/process/REPORT-FORMAT.md): what is going on,
    one verdict per question a resident asks, the sentence to repeat, what it rests on layer
    by layer down to the evidence or the gap, and what to ask for. Every figure registered;
    scripts/brief.py refuses anything else."""
    import brief as B
    A, L, last, sp, st, k = m['audit'], m['L'], m['last'], m['sports'], m['state'], m['contract']
    y = m['ystep']
    by = {r['fy']: r for r in m['ledger']}
    b = m['book']
    qs = {q['key']: q for q in m['quotes']}
    cap = {c['key']: c for c in m['captions']}
    U = lambda v: figure(v, C.usd(v))
    U2 = lambda v: figure(v, usd2(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    ln = lambda key, label=None: (slug(H[key]), label or H[key])
    minute = lambda key: (qs[key]['cite'], '%s minutes, %s' % (qs[key]['board'], qs[key]['date']))
    video = lambda key: (cap[key]['url'], '%s, %s, video at %s (machine captions)'
                         % (cap[key]['board'], cap[key]['date'], cap[key]['at']))

    s26, g, x, f, r, mo, tr = (A['sped26'], A['lag'], A['mask'], A['feeyear'], A['restore'],
                               A['model'], A['track'])
    over = {o['fy']: o for o in A['overdrawn'] if o['cat'] == 'regular'}
    reg25, reg26 = by[2025]['regular'], L['regular']
    if not (reg25['spent'] == reg25['budget'] and reg26['spent'] == r0(y[2026]['regular'])
            and b['regular']['fy27_balanced'] == r0(y[2027]['regular'])):
        fail('regular routes no longer match budget and contract to the dollar; the "sound" '
             'verdict rests on it')
    sp_ = A['spring']
    tr = A['track']

    chains = [
        B.chain(
            'sped', 'Is special education busing budgeted right?', 'problem',
            'Special education buses spent %s more than their %s budget, and no transfer '
            'covered it.' % (C.usd(s26['over']), C.fy(last)),
            figures={'over': U(s26['over']), 'fy': F(last)},
            steps=[
                B.step('Voted %s; %s spent by the close of the year. No school bus line has run '
                       'further past its budget in any year back to %s.'
                       % (C.usd(s26['voted']), C.usd(s26['spent']), C.fy(m['first'])),
                       'measured', {'v': U(s26['voted']), 's': U(s26['spent']),
                                    'f': F(m['first'])}, link=ln('overdrawn')),
                B.step('%s budgets %s for the line, %s above what %s spent. A Special '
                       'Education Reserve Fund, accepted on 18 November 2025, exists for '
                       'unbudgeted costs like this one.'
                       % (C.fy(2027), C.usd(A['sped27']), C.usd(A['sped27_margin']), C.fy(last)),
                       'measured', {'a': F(2027), 'b': U(A['sped27']),
                                    'c': U(A['sped27_margin']), 'd': F(last)},
                       allow=('18 November 2025',), link=ln('overdrawn')),
                B.step('It is not a one-off. From %s to %s the same line was budgeted %s above '
                       'what it spent; then it was cut, and it overran in %s.'
                       % (C.fy(g['start']), C.fy(g['cut']), C.usd(g['sum']),
                          ' and '.join(C.fy(o['fy']) for o in g['over'])),
                       'measured', dict({'a': F(g['start']), 'b': F(g['cut']), 's': U(g['sum'])},
                                        **{'o%d' % o['fy']: F(o['fy']) for o in g['over']}),
                       link=ln('lag')),
                B.step('A budget set from last year’s spending would miss in just this way; so '
                       'would children’s placements changing after the budget is set. Nothing '
                       'here tests either.', 'hypothesis', link=ln('lag')),
                B.step('How many vans, monitors and routes the line pays for is not published, '
                       'so a higher price cannot be told from more children carried.', 'gap',
                       closes='the special education van contract and a count of routes by '
                              'year, from the district'),
            ]),
        B.chain(
            'regular', 'Do the regular bus routes match the contract?', 'sound',
            'Regular bus routes now cost exactly what the Dee Bus contract says, and the %s '
            'budget carries its price, %s, to the dollar.'
            % (C.fy(2027), C.usd(b['regular']['fy27_balanced'])),
            figures={'fy': F(2027), 'p': U(b['regular']['fy27_balanced'])},
            steps=[
                B.step('%s spent its budget exactly, %s. %s spent the contract’s first-year '
                       'price exactly, %s.' % (C.fy(2025), C.usd(reg25['spent']), C.fy(last),
                                               C.usd(reg26['spent'])),
                       'measured', {'a': F(2025), 'b': U(reg25['spent']), 'c': F(last),
                                    'd': U(reg26['spent'])}, link=ln('regular')),
                B.step('Under the contract before this one the line overran: %s by %s, and %s '
                       'by %s even after %s was moved in.'
                       % (C.fy(2023), C.usd(over[2023]['over']), C.fy(2024),
                          C.usd(over[2024]['over']), C.usd(over[2024]['transfer'])),
                       'measured', {'a': F(2023), 'b': U(over[2023]['over']), 'c': F(2024),
                                    'd': U(over[2024]['over']), 'e': U(over[2024]['transfer'])},
                       link=ln('overdrawn')),
                B.step('The price is fixed but not flat: it rises %s into %s and %s into %s, '
                       'against the 2.5%% a levy may grow in a year without an override. The '
                       'contract ends on 30 June 2028.'
                       % (C.pct(m['rises'][2027]), C.fy(2027), C.pct(m['rises'][2028]),
                          C.fy(2028)),
                       'measured', {'a': P(m['rises'][2027]), 'b': F(2027),
                                    'c': P(m['rises'][2028]), 'd': F(2028)},
                       allow=('2.5%', '30 June 2028'), link=ln('contract', 'The Dee Bus contract')),
                B.step('The contract before this one has not been published, so neither why '
                       '%s cost more than %s nor whether %s’s %s rise was price or an extra bus '
                       'can be told.' % (C.fy(2024), C.fy(2025), C.fy(2026),
                                         C.pct(pct1(m['step'], m['reg25']))), 'gap',
                       {'a': F(2024), 'b': F(2025), 'c': F(2026),
                        'd': P(pct1(m['step'], m['reg25']))},
                       closes='the Dee Bus contract that ran to June 2025, requested 9 October 2026',
                       allow=('June 2025', '9 October 2026')),
            ]),
    ]

    # ---- is it getting more expensive, and where. Spent against spent, never across (rule
    # 1). The base is FY2019, the last year before the 2020 school closures -- OUR choice, the
    # same one section 6 makes and says, because FY2020 and FY2021 are the series' lowest
    # points for a reason that is not a trend.
    b0, b1 = by[2019], by[last]
    span = last - 2019
    grow = lambda c: dict(a=b0[c]['spent'], b=b1[c]['spent'],
                          pct=pct1(b1[c]['spent'] - b0[c]['spent'], b0[c]['spent']),
                          yr=round(100 * ((b1[c]['spent'] / b0[c]['spent']) ** (1 / span) - 1), 1))
    gs, gr, ga = grow('sped'), grow('regular'), grow('athletic')
    if not (gs['yr'] > 2.5 and gr['yr'] > 2.5):
        fail('special education and regular routes no longer both outgrow 2.5%% a year since '
             'FY2019: %s, %s' % (gs['yr'], gr['yr']))
    tot24, tot25 = sp['totals'][2024], sp['totals'][2025]
    if not tot25 < tot24:
        fail('the district sheet no longer shows athletic buses costing less in FY2025 than '
             'FY2024; the trend chain says the rise on the town line is who pays')
    trend = B.chain(
        'trend', 'Are buses getting more expensive, and where?', 'concern',
        'Yes, in two places. Since %s special education buses rose %s and regular routes %s, '
        'both faster than the 2.5%% a levy may grow.' % (C.fy(2019), C.pct(gs['pct'], 0),
                                                        C.pct(gr['pct'], 0)),
        figures={'f': F(2019), 's': P(gs['pct'], 0), 'r': P(gr['pct'], 0)}, allow=('2.5%',),
        steps=[
            B.step('Spent at the close of the year: special education %s in %s and %s in %s, '
                   '%s a year; regular routes %s and %s, %s a year.'
                   % (C.usd(gs['a']), C.fy(2019), C.usd(gs['b']), C.fy(last), C.pct(gs['yr']),
                      C.usd(gr['a']), C.usd(gr['b']), C.pct(gr['yr'])),
                   'measured', {'a': U(gs['a']), 'b': F(2019), 'c': U(gs['b']), 'd': F(last),
                                'e': P(gs['yr']), 'g': U(gr['a']), 'h': U(gr['b']),
                                'i': P(gr['yr'])}, link=ln('sec6')),
            B.step('Regular routes are priced in advance: the contract fixes %s for %s, %s more '
                   'than %s paid.' % (C.usd(y[2028]['regular']), C.fy(2028),
                                     C.pct(pct1(y[2028]['regular'] - gr['b'], gr['b'])),
                                     C.fy(last)),
                   'measured', {'a': U(y[2028]['regular']), 'b': F(2028),
                                'c': P(pct1(y[2028]['regular'] - gr['b'], gr['b'])),
                                'd': F(last)}, link=ln('contract', 'The Dee Bus contract')),
            B.step('Athletic buses on the town line went from %s to %s, but the district’s own '
                   'sheet already put them at %s in %s and %s in %s: the town budget, mostly '
                   'taxes, took over what player fees paid.' % (C.usd(ga['a']), C.usd(ga['b']), C.usd(tot24),
                                                C.fy(2024), C.usd(tot25), C.fy(2025)),
                   'measured', {'a': U(ga['a']), 'b': U(ga['b']), 'c': U(tot24), 'd': F(2024),
                                'e': U(tot25), 'f': F(2025)}, link=ln('sec2')),
            B.step('%s budgets school-day buses %s higher; cutting athletic buses, %s, made the '
                   'total look like %s.' % (C.fy(2027), C.pct(x['sd_pct']), C.usd(x['ath_cut']),
                                            C.pct(x['all_pct'])),
                   'measured', {'a': F(2027), 'b': P(x['sd_pct']), 'c': U(x['ath_cut']),
                                'd': P(x['all_pct'])}, link=ln('mask')),
            B.step('The district put its %s special education rise down to more vans and '
                   'monitors. Nothing published counts either, so price and volume cannot be '
                   'told apart.' % C.fy(last), 'gap', {'a': F(last)},
                   closes='the special education van contract and a count of routes by year, '
                          'from the district'),
        ])

    # ---- what offsets it: the state, and the bus fee. Money IN, kept beside the spending
    # and never netted from it (rule 11) -- the payment is not on the bus line, and which line
    # it lands against is a registered gap.
    cb = {c['fy']: c for c in st['cb']}
    cb_last, cb_first = cb[last], cb[min(cb)]
    cb_peak = max(st['cb'], key=lambda c: c['transport'])
    of_sped = pct1(cb_last['transport'], b1['sped']['spent'])
    of_all = pct1(cb_last['transport'], b1['all_spent'])
    offsets = B.chain(
        'offsets', 'Does state money or the bus fee offset the cost?', 'concern',
        # "the town's bus bill" was too short to read. TJ, 11 October 2026: it needs to say
        # the fee did not reduce what the town budgets and pays. NOT "it only changed the
        # source of funding": where the fee money lands is a registered gap (last step).
        'Only a little. The state repaid %s in %s, all for special education. The bus fee '
        'did not cut what the town spends on buses.' % (C.usd(cb_last['transport']), C.fy(last)),
        figures={'a': U(cb_last['transport']), 'b': F(last)},
        steps=[
            B.step('The state’s circuit breaker repays part of busing children placed out of '
                   'district: %s in %s, %s at its %s peak, %s in %s.'
                   % (C.usd(cb_first['transport']), C.fy(cb_first['fy']),
                      C.usd(cb_peak['transport']), C.fy(cb_peak['fy']),
                      C.usd(cb_last['transport']), C.fy(last)),
                   'measured', {'a': U(cb_first['transport']), 'b': F(cb_first['fy']),
                                'c': U(cb_peak['transport']), 'd': F(cb_peak['fy']),
                                'e': U(cb_last['transport']), 'f': F(last)}, link=ln('sec5')),
            B.step('Set beside %s spending, that is %s of special education buses and %s of all '
                   'buses. It repays the year before’s claims, not that year’s buses.'
                   % (C.fy(last), C.pct(of_sped), C.pct(of_all)),
                   'measured', {'a': F(last), 'b': P(of_sped), 'c': P(of_all)},
                   link=ln('sec5')),
            B.step('Regular routes and athletics get nothing from the state: Lunenburg is not a '
                   'regional district, and the Cherry Sheet shows no regional busing aid in any '
                   'year %s to %s.' % (C.fy(st['cherry_years'][0]), C.fy(st['cherry_years'][-1])),
                   'measured', {'a': F(st['cherry_years'][0]), 'b': F(st['cherry_years'][-1])},
                   link=ln('sec5')),
            B.step('The Finance Committee was told the new bus fee cut the line by %s. The line '
                   'was voted %s below the contract, then %s was moved back in during the year, '
                   'so the school budget still paid the whole contract.'
                   % (C.usd(m['netted']), C.usd(m['netted']), C.usd(f['transfer'])),
                   'quote', {'a': U(m['netted']), 'c': U(f['transfer'])},
                   cite=minute('fee-11000'), link=ln('fee')),
            B.step('Where the fees are booked is not established; the only account named for '
                   'them, in the school choice fund, took in %s in %s and spent nothing on '
                   'buses.' % (C.usd(st['fee'][last]), C.fy(last)), 'gap',
                   {'a': U(st['fee'][last]), 'b': F(last)},
                   closes='the account the bus fee payments are deposited to, from the Town '
                          'Accountant'),
        ])

    # ---- the athletic fee fund: how it plays into what athletic buses cost.
    fb = A['fund']['by']
    pos24, pos25, pos26 = fb[2024]['hs_pos'], fb[2025]['hs_pos'], fb[last]['hs_pos']
    if not (pos25 < pos24 / 2 and pos26 > pos24 * 0.9):
        fail('the fee fund’s high school purchase-of-service account no longer fell in FY2025 '
             'and came back in FY2026, which the athletic-fund chain states')
    line24 = by[2024]['athletic']['spent']
    ath25 = by[2025]['athletic']
    athletic = B.chain(
        'athletic-fund', 'How does the athletic fee fund play into bus costs?', 'concern',
        'In %s the town paid %s of athletic buses and player fees the rest. From %s the '
        'district moved that cost to the town budget, mostly taxes.'
        % (C.fy(2024), C.usd(line24), C.fy(2025)),
        figures={'a': F(2024), 'b': U(line24), 'c': F(2025)},
        steps=[
            B.step('The district’s by-sport sheet puts %s athletic buses at %s; its second sheet '
                   'prints %s for the %s sports both list. Either way, well above %s.'
                   % (C.fy(2024), C.usd(tot24), C.usd(A['sheets']['fincom']),
                      C.num(A['sheets']['n']), C.usd(line24)),
                   'measured', {'a': F(2024), 'b': U(tot24), 'c': U(A['sheets']['fincom']),
                                'd': figure(A['sheets']['n'], C.num(A['sheets']['n']), 'sports'),
                                'e': U(line24)}, link=ln('sec2')),
            B.step('In %s %s was moved into the town line, to %s, to “reclassify expenses that '
                   'had been charged against the revolving account”.'
                   % (C.fy(2025), C.usd(ath25['transfer']), C.usd(ath25['spent'])),
                   'quote', {'a': F(2025), 'b': U(ath25['transfer']), 'c': U(ath25['spent'])},
                   cite=minute('reclass'), link=ln('sec2')),
            B.step('The same year the fee fund’s high school purchase-of-service account, which '
                   'carried buses with officials and ice time, fell from %s to %s.'
                   % (C.usd(pos24), C.usd(pos25)),
                   'measured', {'a': U(pos24), 'b': U(pos25)}, link=ln('fund')),
            B.step('%s cut the town line to %s. On 26 August 2026 %s was restored from the town '
                   'and %s put back on the fee fund.'
                   % (C.fy(2027), C.usd(0), C.usd(r['town']), C.usd(r['fund'])),
                   'quote', {'a': F(2027), 'b': U(0), 'c': U(r['town']), 'd': U(r['fund'])},
                   allow=('26 August 2026',), cite=minute('restore-vote'), link=ln('restore')),
            B.step('In %s that fee fund account spent %s again while the town line paid %s for '
                   'athletic buses. What the fund paid for is not published.'
                   % (C.fy(last), C.usd(pos26), C.usd(L['athletic']['spent'])), 'gap',
                   {'a': F(last), 'b': U(pos26), 'c': U(L['athletic']['spent'])},
                   closes='the fee fund’s purchase-of-service detail by vendor, and its balance '
                          'at each 30 June, from the Town Accountant',
                   allow=('30 June',)),
        ])

    # ---- which sport, and can the sheet be trusted. The schedules are the second witness:
    # where each team played, how far away, and a bus model that is OURS (load_schedules).
    S = m['sched']
    cmp_ = {(c['fy'], c['level'], c['sport']): c for c in S['compare']}
    it = cmp_[(2024, 'HS', 'Indoor Track - Boys')]
    if not (it['halved'] and it['sheet'] > it['hi']):
        fail('indoor track no longer prints above the upper bound of its schedule, halved')
    ut = cmp_.get((2025, 'HS', 'Unified Track'))
    if not (ut and ut['below_miles']):
        fail('unified track FY2025 is no longer below the miles alone; the track chain names it')
    fl = S['flagged']
    itg = cmp_[(2024, 'HS', 'Indoor Track - Girls')]
    if not (itg['away'] == it['away'] and it['charges'] >= 2 * it['away']):
        fail('indoor track’s charges are no longer at least twice its away meets, per team')
    track = B.chain(
        'track', 'Which sport’s buses cost most? Can we trust the figures?', 'unknown',
        'Track costs most on the district’s sheet, %s in %s. Its posted schedule shows far '
        'fewer away meets than the sheet has charges.' % (C.usd(tr['it24']), C.fy(2024)),
        figures={'a': U(tr['it24']), 'b': F(2024)},
        steps=[
            B.step('Boys’ and girls’ indoor track each print %s for %s. Added, %s is ahead of '
                   'football’s %s and girls’ soccer’s %s.'
                   % (usd2(tr['it24_row']), C.fy(2024), usd2(tr['it24']),
                      usd2(tr['second24']['cost']), usd2(tr['soccer24'])),
                   'measured', {'a': U2(tr['it24_row']), 'b': F(2024), 'c': U2(tr['it24']),
                                'd': U2(tr['second24']['cost']), 'e': U2(tr['soccer24'])},
                   link=ln('track', 'Which sport’s buses cost most')),
            B.step('The sheet’s formula for it holds %s charges; the schedule lists %s away meets '
                   'per team. Our model, one bus a meet with four hours’ waiting at %s rates, puts each '
                   'team’s at %s.'
                   % (C.num(it['charges']), C.num(it['away']), C.fy(2026), usd2(it['hi'])),
                   'estimate', {'a': figure(it['charges'], C.num(it['charges']), 'charges'),
                                'b': figure(it['away'], C.num(it['away']), 'meets'),
                                'c': F(2026), 'd': U2(it['hi'])},
                   link=ln('sheet', 'The sheet against the schedules')),
            B.step('The other way: %s sport-years print less than the miles alone would cost. '
                   'Unified track’s %s %s covers %s away meets, %s of miles at %s rates.'
                   % (C.num(len(fl)), C.fy(2025), usd2(ut['sheet']), C.num(ut['away']),
                      usd2(ut['lo_miles']), C.fy(2026)),
                   'estimate', {'n': figure(len(fl), C.num(len(fl)), 'sport-years'),
                                'a': F(2025), 'b': U2(ut['sheet']),
                                'c': figure(ut['away'], C.num(ut['away']), 'meets'),
                                'd': U2(ut['lo_miles']), 'e': F(2026)},
                   link=ln('sheet', 'The sheet against the schedules')),
            B.step('At the School Committee, members said the indoor track league meet had '
                   'moved to the Reggie Lewis Center in Boston, and that the bus is billed in '
                   'full while it waits there.', 'caption', cite=video('reggie')),
            B.step('Whether a bus went, was shared, or waited four hours is not recorded, so '
                   'neither the sheet nor our model can be checked trip by trip.', 'gap',
                   closes='Dee Bus’s athletic invoices, each trip’s date, team, miles and '
                          'hours waiting, from the Business Office'),
        ])

    # ---- the table a resident asks for by name: what each kind of bus actually cost.
    yrs = [fy for fy in sorted(by) if 2023 <= fy <= last]
    rowc = lambda c: [U(by[fy][c]['spent']) for fy in yrs]
    costs = B.table(
        'What the buses cost, spent at the close of each year',
        [C.fy(fy) for fy in yrs],
        [dict(label='Regular routes', kind='ledger', cells=rowc('regular')),
         dict(label='Special education', kind='ledger', cells=rowc('sped')),
         dict(label='Athletics, town line', kind='ledger', cells=rowc('athletic')),
         dict(label='Band and music trips', kind='ledger', cells=rowc('band')),
         dict(label='All school buses, town', kind='ledger', total=True,
              cells=[U(by[fy]['all_spent']) for fy in yrs]),
         dict(label='Athletics, all payers (district sheet)', kind='stated',
              cells=[U(sp['totals'][fy]) if fy in sp['totals'] else None for fy in yrs])],
        'The town’s general fund at the year-end close, paid plus still owed. The last row is '
        'a sheet the district built, not the ledger; it adds what the families’ fee fund paid.')

    chains = [trend, offsets] + chains + [athletic, track]
    out = B.brief(
        'Buses are getting more expensive, in special education and in the regular-route '
        'contract. The state repays only a slice of special education busing. The athletic '
        'line rose because the district moved that cost from player fees to the town budget, '
        'mostly taxes.',
        chains, costs=costs)
    out['ladder'] = build_ladder(m, by, gs, gr, cb_last, of_all, line24,
                                 [c['id'] for c in chains])
    return out


def levy_share(fy):
    """How much of the revenue behind the town budget is property tax: the town's own
    revenue distribution, `Total Tax Levy` over `Total`, for the projected year. TJ, 12
    October 2026: "people dont understand the implication of 'from player fees to town
    budget'... we need the word 'taxes'". The town budget is not ONLY taxes -- state aid and
    local receipts are the rest -- so the page says MOSTLY, and this is the figure behind it."""
    path = os.path.join(ROOT, 'sources', 'data', 'revenue-distribution-fy26.csv')
    want = {'levy': 'Revenues / Total Tax Levy: Total / %s PROJECTED' % C.fy(fy).replace('20', '', 1),
            'total': 'Revenues / Total / %s PROJECTED' % C.fy(fy).replace('20', '', 1)}
    got = {}
    for r in csv.DictReader(open(path, encoding='utf-8')):
        for k_, line in want.items():
            if r['line'] == line:
                got[k_] = float(r['fy26'])
    if set(got) != set(want):
        fail('revenue-distribution-fy26.csv no longer prints %s' % ', '.join(sorted(set(want) - set(got))))
    share = round(100 * got['levy'] / got['total'], 1)
    if not share > 50:
        fail('property tax is no longer most of the town budget’s revenue (%s%%); the page says '
             '"mostly"' % share)
    return dict(levy=got['levy'], total=got['total'], share=share)


def build_ladder(m, by, gs, gr, cb_last, of_all, line24, chain_ids=()):
    """The fact ladder (scripts/ladder.py): bare facts, then how they change, then who
    pays, then the conclusions -- each naming the facts it rests on. Nothing typed: every
    value is a figure() off the same measurements the chains use."""
    import ladder as LD
    A, last, k, st = m['audit'], m['last'], m['contract'], m['state']
    x, s26, y = A['mask'], A['sped26'], m['ystep']
    b1 = by[last]
    U = lambda v: figure(v, C.usd(v))
    U2 = lambda v: figure(v, usd2(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    G = lambda v: figure(v, '+' + C.pct(v))          # a rise: the sign is the point
    N = lambda v: figure(v, C.num(v))
    k26 = next(c for c in k['years'] if c['fy'] == last)
    lv = levy_share(last)
    sched = next(r for r in m['sched']['by_fy'] if r['fy'] == last)
    wait = k['trip_full'] - k['trip_nowait']
    wait_pct = round(100 * wait / k['trip_full'], 1)
    LEVY = 2.5          # Proposition 2.5, M.G.L. c.59 s.21C -- statute, not ours
    if not b1['regular']['spent'] > max(b1['sped']['spent'], b1['athletic']['spent']):
        fail('regular routes are no longer the largest piece; conclusion 2 says they are')

    f = LD.fact
    t1 = LD.tier('The facts, %s' % C.fy(last), [
        f('all', U(b1['all_spent']), 'all school buses, spent, %s' % C.fy(last), 'published',
          {'y': F(last)}),
        f('regular', U(b1['regular']['spent']), 'regular routes', 'published'),
        f('sped', U(b1['sped']['spent']), 'special education vans, not the Dee Bus contract',
          'published'),
        f('athletic', U(b1['athletic']['spent']), 'athletics, on the town budget', 'published'),
        f('buses', N(k['n77'] + k['n83']), 'buses on regular routes', 'contract'),
        f('days', N(k['days']), 'school days a bus is paid for', 'contract'),
        f('bus-day', figure(k26['p77'], '%s–%s' % (C.usd(k26['p77']), C.usd(k26['p83']))),
          'one bus, one school day', 'contract'),
        f('mile', U2(k26['trip_rate']), 'a mile, field and athletic trips', 'contract'),
        f('hour', U(k26['wait_rate']), 'an hour of the driver waiting', 'contract'),
        f('trips', N(sched['trips']), 'athletic bus trips, from the posted schedules',
          'estimate'),
        f('state', U(cb_last['transport']), 'repaid by the state, special education only', 'published'),
        f('riders', None, 'children who ride', 'gap',
          closes='a count of riders by route, from the district'),
        f('vans', None, 'special education vans and monitors', 'gap',
          closes='the special education van contract and a count of routes by year'),
        f('van-rate', None, 'one van, one school day', 'gap',
          closes='the special education van contract, from the district'),
    ])
    t2 = LD.tier('How it is changing', [
        f('sped-rate', G(gs['yr']), 'a year, special education, since %s' % C.fy(2019),
          'published', {'y': F(2019)}),
        f('reg-rate', G(gr['yr']), 'a year, regular routes, since %s' % C.fy(2019),
          'published', {'y': F(2019)}),
        f('levy', P(LEVY), 'a year: the most the levy may grow, no override', 'statute'),
        f('rise27', G(m['rises'][2027]), 'contract price, into %s' % C.fy(2027),
          'contract', {'y': F(2027)}),
        f('rise28', G(m['rises'][2028]), 'contract price, into %s' % C.fy(2028),
          'contract', {'y': F(2028)}),
        f('fixed28', U(y[2028]['regular']), 'regular routes in %s, already fixed' % C.fy(2028),
          'contract', {'y': F(2028)}),
        f('over', U(s26['over']), 'special education past its %s budget' % C.fy(last),
          'published', {'y': F(last)}),
        f('wait', P(wait_pct, 0), 'of a bid-form trip is waiting: %s of %s'
          % (C.usd(wait), usd2(k['trip_full'])), 'contract',
          {'w': U(wait), 't': U2(k['trip_full'])}),
    ])
    t3 = LD.tier('Who pays, and what the budget shows', [
        f('state-share', P(of_all), 'of all buses repaid by the state', 'published'),
        f('levy-share', P(lv['share'], 0), 'of town budget revenue is property tax, %s projection' % C.fy(last), 'published', {'y': F(last)}),
        f('no-aid', U(0), 'state aid for regular routes and athletics', 'published'),
        f('ath24', U(line24), 'athletics on the town budget, %s' % C.fy(2024), 'published',
          {'y': F(2024)}),
        f('ath-sheet', U(m['sports']['totals'][2024]),
          'athletic buses, all payers, %s: district sheet' % C.fy(2024), 'published',
          {'y': F(2024)}),
        f('sd27', G(x['sd_pct']), 'school-day buses, %s budget' % C.fy(2027), 'published',
          {'y': F(2027)}),
        f('all27', G(x['all_pct']), 'all buses together, %s budget' % C.fy(2027), 'published',
          {'y': F(2027)}),
        f('cut27', U(x['ath_cut']), 'athletic buses cut from %s' % C.fy(2027), 'published',
          {'y': F(2027)}),
    ])
    lo, hi = round(gr['yr'] / LEVY), round(gs['yr'] / LEVY)
    # THE SAME FACTS, AS A MATRIX: a column per kind of bus, coloured as the charts colour
    # it, and a row per rung. Every fact is placed once; ladder.py refuses otherwise.
    mx = LD.matrix(
        [('all', 'All buses'), ('regular', 'Regular routes', 'var(--subj-1)'),
         ('sped', 'Special education', 'var(--subj-4)'),
         ('athletic', 'Athletics', 'var(--subj-2)')],
        [('cost', 'Spent, %s' % C.fy(last)), ('unit', 'What one unit costs'),
         ('volume', 'How much'), ('growth', 'Growth a year'),
         ('fixed', 'Already fixed'), ('budget', 'Budget against spending'),
         ('pays', 'Who pays')],
        {('all', 'cost'): ['all'], ('regular', 'cost'): ['regular'],
         ('sped', 'cost'): ['sped'], ('athletic', 'cost'): ['athletic'],
         ('regular', 'unit'): ['bus-day'], ('sped', 'unit'): ['van-rate'],
         ('athletic', 'unit'): ['mile', 'hour', 'wait'],
         ('all', 'volume'): ['riders'], ('regular', 'volume'): ['buses', 'days'],
         ('sped', 'volume'): ['vans'], ('athletic', 'volume'): ['trips'],
         ('all', 'growth'): ['levy'], ('regular', 'growth'): ['reg-rate'],
         ('sped', 'growth'): ['sped-rate'],
         ('regular', 'fixed'): ['rise27', 'rise28', 'fixed28'],
         ('all', 'budget'): ['sd27', 'all27'], ('sped', 'budget'): ['over'],
         ('athletic', 'budget'): ['cut27'],
         ('all', 'pays'): ['levy-share', 'state-share'], ('regular', 'pays'): ['no-aid'],
         ('sped', 'pays'): ['state'], ('athletic', 'pays'): ['ath24', 'ath-sheet']})
    con = LD.conclusion
    return LD.ladder([t1, t2, t3], [
        con('Buses are growing %s to %s times as fast as the levy may.' % (lo, hi),
            ['sped-rate', 'reg-rate', 'levy'], {'lo': N(lo), 'hi': N(hi)}, chain='trend'),
        con('The biggest piece, regular routes, is priced by contract through %s.' % C.fy(2028),
            ['regular', 'bus-day', 'rise27', 'rise28', 'fixed28'], {'y': F(2028)},
            chain='regular'),
        con('Special education grows fastest, and nothing published counts what it buys.',
            ['sped', 'sped-rate', 'over', 'vans'], chain='sped'),
        con('The %s total looks flat because athletic buses were cut, not because buses got '
            'cheaper.' % C.fy(2027), ['sd27', 'all27', 'cut27'], {'y': F(2027)}),
        con('The state repays a small share, and nothing for regular routes or athletics.',
            ['state', 'state-share', 'no-aid'], chain='offsets'),
        con('Athletic buses moved from player fees to the town budget, which property taxes '
            'mostly pay for.', ['athletic', 'ath24', 'ath-sheet', 'levy-share'],
            chain='athletic-fund'),
    ], matrix=mx, chains=chain_ids)


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

def chart_table(by_year, sheet):
    """The signature chart's figures as a table: every year it draws, one row a year, in two
    views -- spent at the close and voted before the year -- never mixed in one column (rule
    1). Formatted here so the page computes nothing. The district's by-sport sheet is its own
    column, marked `stated` (rule 13a): a sheet somebody assembled, not the ledger."""
    cols = [('regular', 'Regular routes'), ('sped', 'Special education'),
            ('athletic', 'Athletics'), ('band', 'Band and music')]
    cell = lambda v: None if v is None else C.usd(v)
    views = []
    for key, label, note in (
            ('spent', 'Spent at the close',
             'Town general fund, paid plus still owed at the year-end close. The last column is '
             'a sheet the district built, not the ledger; it adds what the families’ fee fund '
             'paid.'),
            ('budget', 'Voted before the year',
             'Town general fund, the budget voted before the year began.')):
        rows = []
        for r in sorted(by_year, key=lambda r: r['fy'], reverse=True):
            cells = [cell(r['%s_%s' % (c, key)]) for c, _ in cols]
            cells.append(cell(r['all_%s' % key]))
            if key == 'spent':
                cells.append(cell(sheet[r['fy']]) if r['fy'] in sheet else None)
            if all(c is None for c in cells):
                continue
            rows.append(dict(label=C.fy(r['fy']), cells=cells))
        head = [l for _, l in cols] + ['All buses']
        kinds = ['ledger'] * len(head)
        if key == 'spent':
            head.append('Athletics, all payers')
            kinds.append('stated')
        views.append(dict(key=key, label=label, columns=head, kinds=kinds, total_col=len(cols),
                          rows=rows, note=note))
    return dict(caption='School transportation by year', views=views)


def payload(m, rows, brief):
    L, last, k, sp, st = m['L'], m['last'], m['contract'], m['sports'], m['state']
    A = m['audit']
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

    S, T_ = m['sched'], m['stest']
    cmp_ = {(c['fy'], c['level'], c['sport']): c for c in S['compare']}

    def model(r, fy):
        c = cmp_.get((fy, r['level'], r['sport']))
        return (dict(away=c['away'], charges=c['charges'], lo=c['lo'], hi=c['hi'],
                     lo_miles=c['lo_miles']) if c and c['scheduled'] else None)
    sports = [dict(season=r['season'], level=r['level'], sport=r['sport'],
                   label='%s %s · %s' % (r['level'], r['sport'], r['season']),
                   fy2024=r['fy2024'], fy2025=r['fy2025'], model2024=model(r, 2024),
                   model2025=model(r, 2025)) for r in sp['rows']]
    schedules = dict(
        about='OUR ESTIMATE. Each team’s away games as ArbiterLive lists them (canceled, '
              'postponed and rained-out games left out), each venue’s round-trip driving miles '
              'from the high school, priced at the Dee Bus contract’s per-mile rate plus %s '
              'hours’ waiting a trip at its hourly rate. FY2022 to FY2025 are AT FY2026 '
              'PRICES; the earlier contract’s rates are not held. Upper bound: one bus per '
              'team-game. Lower bound: one bus per date and venue, shared by every Lunenburg '
              'team there. Whether buses were shared is not observed.' % C.num(WAIT_HOURS),
        source='ArbiterLive (arbiterlive.com), the scheduling site the district links; read '
               '%s. The pages are not archived or republished; the rows are cited as facts only.' % T_['fetched'],
        wait_hours=WAIT_HOURS, by_fy=S['by_fy'],
        teams=[dict((k_, v) for k_, v in t.items()) for t in S['teams']],
        sheet_compare=S['compare'], charges=S['charges'],
        venues_without_distance=S['venues_without'],
        fy2027_test=T_)

    return dict(
        generated_by='scripts/build_transportation.py',
        about='What Lunenburg’s school buses cost, by year since %s: the school day against '
              'athletics, budgeted and spent; athletics by sport; and what the Dee Bus contract '
              'fixes through %s.' % (C.fy(m['first']), C.fy(2028)),
        grain='DOLLARS, school general fund, the budget voted before the year beside what was '
              'spent at its close (expended plus still committed), %s; never added together. '
              'Per-sport dollars are the district’s hand-assembled sheets (stated). Games are '
              'counted off the posted schedules; every bus cost built from them is OUR '
              'ESTIMATE.' % C.fyspan(m['first'], last),
        # NO STAT ROW. Residents told TJ a big number with a paragraph under it leaves them
        # nothing to say; the brief's sentences carry the figures instead, each inside the
        # sentence a reader would repeat (notes/process/REPORT-FORMAT.md).
        brief={k: v for k, v in brief.items() if k != 'ladder'},
        ladder=brief['ladder'],
        audit=dict(
            overdrawn=A['overdrawn'],
            fee_fund=A['fund']['fund'],
            fee_fund_last_balance=A['fund']['last_balance'],
            school_choice_fund=dict(transportation_expense_accounts=0,
                                    transfer_out_years=A['fund']['xfer_years'],
                                    transfer_out_total=0),
            fy27_mask=A['mask'],
            sped_lag=A['lag'],
            model=dict(rate=A['model']['rate'], base=A['model']['base'],
                       fy28=A['model']['fy28'], contract_fy28=A['model']['contract28'],
                       gap=A['model']['gap']),
            sheets=dict((k_, v) for k_, v in A['sheets'].items() if k_ != 'widest'),
            paired=A['paired'],
            restore=A['restore'],
            track=dict((k_, v) for k_, v in A['track'].items()),
        ),
        captions=[dict(key=c['key'], board=c['board'], date=c['date'], at=c['at'], url=c['url'],
                       said=c['said']) for c in m['captions']],
        conclusions=rows,
        by_year=by_year,
        by_year_keys=[dict(key=c, name=CAT_NAME[c]) for c, _, _, _ in CATS],
        tables={'transportation-schools-athletics': chart_table(by_year, m['sports']['totals'])},
        athletics=ath,
        sports=sports,
        sport_seasons=sp['seasons'],
        sport_compare=sp['compare'],
        schedules=schedules,
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
            'How many athletic bus trips any sport took, or what any one trip cost. The '
            'schedules show where teams played, not whether a bus went, was shared, or how '
            'long it waited; the bus model built from them is ours and gives a range.',
            'How the district built its FY2027 athletic transportation estimate of %s.'
            % C.usd(m['restore']),
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
            'What the athletic fee fund held at any 30 June after 2020, so whether it ran below '
            'zero in FY2024, and what it holds as FY2027 draws on it.',
            'What the fee fund’s high school purchase-of-service account paid for in FY2026, '
            'the year the general fund line was budgeted to carry athletic buses in full.',
            'What made FY2024’s regular routes cost more than FY2025’s; both years ran under '
            'the contract before the current one, which is not held.',
            'Why the special education line was budgeted above its spending for years and then '
            'below it; every explanation offered here is a hypothesis.',
        ],
        gaps=[dict(key=k_, what=w) for k_, w in m['gaps'].items()],
        sources=sources(),
    )


# --------------------------------------------------------------------- markdown

def render_audit(m, rows=()):
    """The evidence for the summary's comparisons: each table first, then what it does not
    show. Run before the inventory sections, because these are what the summary leads with."""
    A, L, last, b, sp, st, k = (m['audit'], m['L'], m['last'], m['book'], m['sports'],
                                m['state'], m['contract'])
    y = m['ystep']
    byfy = {r['fy']: r for r in m['ledger']}
    qs = {q['key']: q for q in m['quotes']}
    w = []
    a = w.append
    cards = {c['id']: c for c in rows}
    lead = lambda cid: ('**%s** %s\n\n' % (cards[cid]['claim'], cards[cid]['so_what'])
                        if cid in cards else '')
    a('## %s\n\n' % H['evidence'])
    a('Each answer at the top rests on one of these. Each is one measured thing set against '
      'another it was supposed to equal; causes are hypotheses wherever they appear, and say '
      'so.\n\n')

    # ---- control
    a('### %s\n\n' % H['overdrawn'])
    a(lead('sped-buses-over-budget'))
    a('The **revised** budget is the voted budget after every transfer made during the year. A '
      'line that spent more than that closed the year overdrawn.\n\n')
    a('| FY | line | revised budget | spent at the close | past revised by | transfers during the year (negative: out) |\n'
      '|---|---|---:|---:|---:|---:|\n')
    for o in A['overdrawn']:
        a('| %s | %s | %s | %s | %s | %s |\n' % (
            C.fy(o['fy']), CAT_NAME[o['cat']], C.usd(o['revised']), C.usd(o['spent']),
            C.usd(o['over']), C.usd(o['transfer']) if o['transfer'] else '—'))
    big = max(A['overdrawn'], key=lambda o: o['over'])
    s = A['sped26']
    a('\n**%s, special education: %s past its revised budget**, the largest overrun on any '
      'transportation line in a series that begins in %s. Voted %s, revised to %s, %s paid out and %s still '
      'committed at the close. The %s budget for the line is %s, %s above what %s spent. The '
      'Finance Committee was shown that figure on 26 February 2026: *“%s”* ([minutes](%s)).\n\n'
      % (C.fy(last), C.usd(s['over']), C.fy(m['first']), C.usd(s['voted']),
         C.usd(s['revised']), C.usd(s['expended']), C.usd(s['committed']), C.fy(2027),
         C.usd(A['sped27']), C.usd(A['sped27_margin']), C.fy(last),
         qs['fincom-sped27']['quote'], qs['fincom-sped27']['cite']))
    if r0(float(re.sub(r'[^\d.]', '', qs['fincom-sped27']['quote'].split('$')[1]))) != A['sped27']:
        fail('the Finance Committee minute no longer states the FY2027 special education '
             'transportation budget the book carries')
    if (big['fy'], big['cat']) != (last, 'sped'):
        fail('the FY%d special education overrun is no longer the largest in the series' % last)
    f4 = A['fy24']
    a('**%s, both school-day lines: %s past their revised budgets together.** Regular routes '
      '%s past, after %s was transferred in; special education %s past. And %s’s regular routes '
      'spent %s, more than %s’s whole year, %s. Both years ran under the contract before the '
      'current one, which is not held, so what the extra was cannot be told (registered: '
      '*%s*). A Finance Committee member asked for the bus contracts that spring (section 4).\n\n'
      % (C.fy(2024), C.usd(f4['both']), C.usd(f4['regular']), C.usd(f4['reg_transfer']),
         C.usd(f4['sped']), C.fy(2024), C.usd(f4['reg_spent']), C.fy(2025),
         C.usd(f4['reg25_spent']), m['gaps']['fy24-regular']))

    # ---- credibility
    g = A['lag']
    a('### %s\n\n' % H['lag'])
    a(lead('sped-budget-trailed-spending'))
    a('From %s to %s the line came in under its voted budget every year, by %s to %s, %s in '
      'all. From %s, the first year the gap passed %s — our threshold — to %s, the year the '
      'budget was cut to %s, the gap was %s; %s of it fell in %s to %s, before the school '
      'closures. Then the line ran over its voted budget: %s. The year-by-year is in section '
      '6.\n\n'
      % (C.fy(g['run0']), C.fy(g['run1']), C.usd(g['lo']), C.usd(g['hi']), C.usd(g['all']),
         C.fy(g['start']), C.usd(BIG_GAP), C.fy(g['cut']), C.usd(g['cut_budget']),
         C.usd(g['sum']), C.usd(g['pre']), C.fy(g['start']), C.fy(2019),
         '; '.join('%s in %s' % (C.usd(x['over']), C.fy(x['fy'])) for x in g['over'])))
    a('*What the data shows:* a budget that trailed its spending in both directions. *What it '
      'does not show:* why. *A hypothesis, untested:* a budget set from the prior year’s actual '
      'would draw this shape, and so would placements arriving and leaving between the budget '
      'and the year. The van contract and a count of routes by year would settle it '
      '(registered: *%s*).\n\n' % m['gaps']['vans'])

    # ---- regular routes: the credit the ledger shows
    reg25, reg26 = byfy[2025]['regular'], L['regular']
    if not (reg25['spent'] == reg25['budget'] and reg26['spent'] == reg26['revised']
            and b['regular']['fy27_balanced'] == r0(y[2027]['regular'])
            and all(byfy[f_]['regular']['over_revised'] > 0 for f_ in (2023, 2024))):
        fail('the regular-route line no longer matches its budget exactly in FY2025, FY2026 and '
             'FY2027, which this section states')
    a('### %s\n\n' % H['regular'])
    a('**Regular routes are now a line a board can plan to the dollar.** %s spent its budget '
      'exactly, %s; %s spent its revised budget exactly, %s, the contract’s price; and the %s '
      'budget carries the contract’s second-year price, %s, to the dollar. The contract fixes '
      '%s too, at %s. That control was not there before: the same line closed %s and %s past '
      'its revised budget (the table above). The contract and its rates are in section 4.\n\n'
      % (C.fy(2025), C.usd(reg25['spent']), C.fy(last), C.usd(reg26['spent']), C.fy(2027),
         C.usd(b['regular']['fy27_balanced']), C.fy(2028), C.usd(y[2028]['regular']),
         C.fy(2023), C.fy(2024)))

    # ---- masking
    x = A['mask']
    a('### %s\n\n' % H['mask'])
    a(lead('school-day-rise-offset'))
    a('| line | %s voted | %s balanced budget | change |\n|---|---:|---:|---:|\n'
      % (C.fy(last), C.fy(2027)))
    for c in CAT_NAME:
        v0, v1 = b[c]['fy26_final'], b[c]['fy27_balanced']
        a('| %s | %s | %s | %s |\n' % (CAT_NAME[c], C.usd(v0), C.usd(v1),
                                       ('+' if v1 > v0 else '') + C.usd(v1 - v0)))
    a('| **school day** (regular + special education) | **%s** | **%s** | **+%s, %s** |\n'
      % (C.usd(x['sd26']), C.usd(x['sd27']), C.usd(x['sd_rise']), C.pct(x['sd_pct'])))
    a('| **all transportation** | **%s** | **%s** | **+%s, %s** |\n\n'
      % (C.usd(x['all26']), C.usd(x['all27']), C.usd(x['all27'] - x['all26']),
         C.pct(x['all_pct'])))
    a('The athletic cut, %s, offsets %s of the school-day rise. Budget to budget throughout; '
      'the regular-route rise is the contract’s second-year price.\n\n'
      % (C.usd(x['ath_cut']), C.pct(x['offset_pct'])))

    # ---- who pays: the fee
    f = A['feeyear']
    a('### %s\n\n' % H['fee'])
    a(lead('bus-fee-and-the-bill'))
    a('In %s, the fee’s first year, regular routes were voted %s and spent %s — the contract’s '
      'full price, all of it from the general fund after %s was transferred in. The candidate '
      'fee account in the school choice fund took in %s across %s and %s (section 5). In every '
      'year %s to %s that fund has **no expense account coded to transportation** — by '
      'function 3300, by the transportation object codes, or by description — and its '
      'transfer to the general fund is **zero**. So on this ledger the fee’s effect on what the '
      'town paid for regular routes is nil. What the fee does pay for is not stated in any '
      'document held here; that the fund 1308 receipts are the fees remains a hypothesis '
      '(registered: *%s*).\n\n'
      % (C.fy(last), C.usd(f['voted']), C.usd(f['spent']), C.usd(f['transfer']),
         usd2(f['receipts']), C.fy(2025), C.fy(2026), C.fy(A['fund']['xfer_years'][0]),
         C.fy(A['fund']['xfer_years'][-1]), m['gaps']['fee-account']))

    # ---- the fee fund
    ff = A['fund']
    a('### %s\n\n' % H['fund'])
    a(lead('fee-fund-receipts-against-spending'))
    a('Fund 1301, every account, at the year-end close. Receipts are the high school and middle '
      'school user charges; spending is expended plus still committed.\n\n')
    a('| FY | receipts | spending | receipts less spending | of which: high school purchase of service | high school salaries |\n'
      '|---|---:|---:|---:|---:|---:|\n')
    for q in ff['fund']:
        a('| %s | %s | %s | %s | %s | %s |\n' % (
            C.fy(q['fy']), usd2(q['receipts']), usd2(q['spending']), usd2(q['net']),
            usd2(q['hs_pos']), usd2(q['hs_salaries'])))
    fb = ff['by']
    a('\nThe district’s FY2026 budget overview says the *“%s”*. Across %s and %s the fund '
      'spent %s more than it took in, which fits that. Across %s and %s it took in %s more '
      'than it spent — **after** costs moved off it onto the town line: %s was transferred '
      'into the general fund athletic line in %s, and the fund’s high school salaries account '
      'closed that year at %s, which is what a reclassification out looks like (our reading). '
      'The %s plan draws %s from it (section 2).\n\n'
      % (OVERVIEW_QUOTES['athletics'].split('; ')[1], C.fy(2023), C.fy(2024),
         C.usd(A['fund_short']), C.fy(2025), C.fy(2026), C.usd(A['fund_ahead']),
         C.usd(A['reclass25']), C.fy(2025), usd2(fb[2025]['hs_salaries']), C.fy(2027),
         C.usd(A['restore']['fund'])))
    a('**One thing not yet explained.** In %s the town line paid %s for athletic buses, and the fund’s '
      'high school purchase-of-service account — where buses used to be charged, with officials '
      'and ice time — spent %s, about what it spent in %s, %s, when it still carried most of '
      'them. Equally consistent with that: officials and ice time rose; some buses are still '
      'charged to the fund; reclassifications landed in a different year. Nothing published '
      'separates them (registered: *%s*).\n\n'
      % (C.fy(last), C.usd(L['athletic']['spent']), usd2(fb[2026]['hs_pos']), C.fy(2024),
         usd2(fb[2024]['hs_pos']), m['gaps']['fee-pos']))
    lb = ff['last_balance']
    a('**The year-end balances are printed, on different bases.** Before them the last published '
      'was %s at 30 June %s, in the Finance Committee’s special revenue fund workbook (`%s`, '
      'stated). Each later 30 June, and the cashbook’s running total within the year, is on '
      '[the fee fund’s own page](/athletics/fee-fund-history): by our running total of the '
      'cashbook the fund’s cash went below zero inside %s, our reading of the order of '
      'postings (registered: *%s*).\n\n'
      % (usd2(lb['amount']), lb['as_of'][:4], lb['source'], C.fy(2024), m['gaps']['fee-balance']))

    # ---- the restoration
    r = A['restore']
    rq, rw = qs['restore'], qs['restore-why']
    a('### %s\n\n' % H['restore'])
    a(lead('restored-buses-on-the-fee-fund'))
    a('On 26 August 2026 the Superintendent told the School Committee *“%s”* ([minutes](%s)). '
      'That is %s of the restoration on the athletic fee fund and %s on the town. In %s the '
      'town line was %s of %s on the district’s by-sport workbook, %s — the higher of its two '
      'sheets, so on the lower one the town’s share would be larger. On 12 March 2025 a School '
      'Committee member called the move onto the town line a correction (section 2). The '
      'Committee voted the plan the same night: *“%s”* ([minutes](%s)). Both are measured; '
      'nothing published yet says which practice now holds.\n\n'
      % (rq['quote'], rq['cite'], C.pct(r['fund_pct']), C.pct(r['town_pct']), C.fy(2024),
         C.usd(byfy[2024]['athletic']['budget']), C.usd(sp['totals'][2024]),
         C.pct(r['town24_pct']), qs['restore-vote']['quote'], qs['restore-vote']['cite']))
    a('**The estimate against the sheet.** She explained that *“%s”* ([minutes](%s)). The '
      'district’s own by-sport workbook puts %s high school athletic buses at %s, and the '
      'contract’s rates rise from %s to %s: %s to %s a mile, %s to %s an hour of waiting. '
      'If %s is short, the difference lands on the fee fund or the town line. A comparison, '
      'not a forecast.\n\n'
      % (rw['quote'], rw['cite'], C.fy(2025), usd2(r['hs25']), C.fy(2026), C.fy(2027),
         usd2(y[2026]['trip_rate']), usd2(y[2027]['trip_rate']), usd2(y[2026]['wait_rate']),
         usd2(y[2027]['wait_rate']), C.usd(r['estimate'])))

    # ---- the FY2027 estimate's reasons, against the schedules
    t = m['stest']
    a('### %s\n\n' % H['sched27'])
    a(lead('fy27-schedule-against-the-estimate'))
    a('Her two reasons can be read off the schedules the district posts: the share of high '
      'school games played at home, and how far the away games are. Like for like: only the '
      'high school teams whose %s schedule for the season is posted in full, the same teams '
      'in every year, canceled and postponed games left out. A season is compared only if it '
      'had begun when the schedules were read, %s. Miles are round-trip driving miles from the '
      'high school, our measurement; an away game whose venue has no distance is left out of '
      'the average.\n\n' % (C.fy(2027), t['fetched']))
    a('| season | FY | teams compared | games | at home | home share | away | average round-trip '
      'miles per away game (games measured) |\n|---|---|---:|---:|---:|---:|---:|---:|\n')
    for se in t['seasons']:
        if not se['teams']:
            a('| %s | %s | — | — | — | — | — | not posted |\n' % (se['season'], C.fy(2027)))
            continue
        for yr in se['years']:
            a('| %s | %s | %s | %s | %s | %s | %s | %s |\n' % (
                se['season'] + ('' if se['complete'] else ' (not compared)'), C.fy(yr['fy']),
                C.num(len(se['teams'])), C.num(yr['games']), C.num(yr['home']),
                C.pct(yr['home_pct']) if yr['home_pct'] is not None else '—', C.num(yr['away']),
                '%s (%s)' % (mi1(yr['miles_avg']), C.num(yr['with_distance']))
                if yr['miles_avg'] is not None else '—'))
    fall = [se for se in t['seasons'] if se['season'] == 'fall'][0]
    win = [se for se in t['seasons'] if se['season'] == 'winter'][0]
    nm = lambda ts: ', '.join('%s (%s)' % (sp_.lower(), lv.lower()) for sp_, lv in ts)
    wy = {yr['fy']: yr for yr in win['years']}
    a('\nLeft out of the autumn comparison because its %s schedule is posted short: %s. '
      'Winter had not begun at the reading, so it is shown and not compared; posted short '
      'and left out: %s. As posted so far, the winter teams shown have %s of games at home '
      'against %s in %s — the direction the estimate describes — but the season has not '
      'begun and its schedules can still change. Spring is not posted.\n\n'
      % (C.fy(2027), nm(fall['short']), nm(win['short']), C.pct(wy[2027]['home_pct']),
         C.pct(wy[2026]['home_pct']), C.fy(2026)))
    sf, y26, asm = t['so_far'], t['year26'], t['assembled']
    a('**What the schedule so far would cost — OUR ESTIMATE, at %s rates** (%s a mile, %s an '
      'hour waiting, four hours a trip):\n\n' % (C.fy(2027), usd2(t['rate']), usd2(t['wait'])))
    a('| high school, as scheduled | away team-games | shared buses | of which waiting | one bus '
      'per team-game | of which waiting |\n|---|---:|---:|---:|---:|---:|\n')
    lab = {('fall', 2027): '%s autumn, as posted' % C.fy(2027),
           ('winter', 2027): '%s winter, posted so far' % C.fy(2027),
           ('fall', 2026): '%s autumn' % C.fy(2026), ('winter', 2026): '%s winter' % C.fy(2026),
           ('spring', 2026): '%s spring' % C.fy(2026)}
    for p_ in sf + y26:
        a('| %s | %s | %s | %s | %s | %s |\n' % (
            lab[(p_['season'], p_['fy'])], C.num(p_['away']), C.usd(p_['lo']),
            C.usd(p_['lo'] - p_['lo_miles']), C.usd(p_['hi']), C.usd(p_['hi'] - p_['hi_miles'])))
    a('\nThe %s schedule posted so far — the autumn and part of the winter — is priced at %s '
      'to %s. That is a **partial year**, set beside an estimate of %s for the whole of it. To '
      'give a full year for scale only, OUR assembly: %s’s autumn as posted with %s’s winter '
      'and spring, all at %s rates, comes to %s with shared buses and %s with one bus per '
      'team-game. Of that, the miles alone are %s to %s; the rest is waiting, and the waiting '
      'is our four hours. **Read the other way:** on that assembled year, with buses shared, '
      'the estimate leaves room for about %s hours of paid waiting a trip. Nothing here says what '
      'her estimate assumed — the minutes say it used actual schedules and prior-year spring '
      'costs, and the worksheet is not published (registered: *%s*).\n\n'
      % (C.fy(2027), C.usd(sf[0]['lo'] + sf[1]['lo']), C.usd(sf[0]['hi'] + sf[1]['hi']),
         C.usd(t['estimate']), C.fy(2027), C.fy(2026), C.fy(2027), C.usd(asm['lo']),
         C.usd(asm['hi']), C.usd(asm['lo_miles']), C.usd(asm['hi_miles']),
         '%.1f' % t['be_hours'], m['gaps']['estimate27']))

    # ---- the model
    mo = A['model']
    a(render_track(m, lead('two-sheets-one-cost')))
    a('### %s\n\n' % H['model'])
    a(lead('contract-outruns-the-model'))
    a('The contract’s regular-route price rises %s into %s and %s into %s, both already '
      'signed. This site’s model (`model/finance.py`, published in `model.json`) starts the '
      'line at the %s budget, %s, and grows it at a default %s a year: %s for %s, **%s under '
      'the %s the contract fixes**. A contracted price is stronger evidence than a default '
      'rate (rules 4 and 6), so this changes an assumption; it is reported here and the model '
      'has not been changed. Special education transportation is not in that line; the model '
      'grows it with special education.\n\n'
      % (C.pct(m['rises'][2027]), C.fy(2027), C.pct(m['rises'][2028]), C.fy(2028), C.fy(2027),
         C.usd(mo['base']), C.pct(100 * mo['rate'], 0), C.usd(mo['fy28']), C.fy(2028),
         C.usd(mo['gap']), C.usd(mo['contract28'])))

    a('### What this does not show\n\n')
    a('- **Why any line overran.** Every cause offered above is a hypothesis; the van contract, '
      'the earlier bus contract and the fee fund’s account detail would each settle one.\n')
    a('- **That anybody did anything wrong.** A variance is a difference between two '
      'figures, not a finding of fault, and several of these have more than one innocent explanation.\n')
    a('- **The fee fund’s balance**, at any 30 June after %s.\n\n' % lb['as_of'][:4])
    return ''.join(w)


def render_track(m, lead_text=''):
    """Which sport's buses cost most, read as TEAMS. The by-sport workbook halves a shared bus
    between boys' and girls' rows, so a row-by-row ranking sinks every split sport; this adds
    the paired rows back together, sets the second sheet beside it, and says what the record
    says about track -- from the recordings, as captions, never as quotation."""
    A, sp, k = m['audit'], m['sports'], m['contract']
    t, spr = A['track'], A['spring']
    y = m['ystep']
    w = []
    a = w.append
    a('### %s\n\n' % H['track'])
    a(lead_text)
    a('**Read row by row, the district’s by-sport workbook’s costliest row in %s is %s, and '
      'its outdoor track rows are among the cheapest. Read as teams, track leads.** Boys’ and '
      'girls’ indoor track print '
      'the same transportation figure, %s each in %s and %s each in %s, which is one bus split '
      'in two (section 3 lists every paired row). Added back together:\n\n'
      % (C.fy(2025), sp['ranked'][0]['sport'].lower(), usd2(t['it24_row']), C.fy(2024),
         usd2(t['it25'] / 2), C.fy(2025)))
    a('| rank | %s, by team | | %s, by team | |\n|---:|---|---:|---|---:|\n'
      % (C.fy(2024), C.fy(2025)))
    def name(x):
        bare = [re.sub(r'^(HS |Boys |Girls )|( - Boys| - Girls)$', '', n_).strip()
                for n_ in x['sports']]
        bare = [re.sub(r'^(HS |Boys |Girls )', '', n_) for n_ in bare]
        if len(x['sports']) > 1 and len(set(bare)) == 1:
            return '%s, boys and girls' % ('Outdoor Track' if bare[0] == 'Track' else bare[0])
        return re.sub(r'^HS ', '', ' + '.join(x['sports']))
    for i_ in range(5):
        p, q = t['teams'][2024][i_], t['teams'][2025][i_]
        a('| %d | %s %s | %s | %s %s | %s |\n' % (i_ + 1, p['level'], name(p), usd2(p['cost']),
                                                  q['level'], name(q), usd2(q['cost'])))
    a('\nOn the workbook, indoor track is first in both years. On the Finance Committee’s copy '
      'of the second district sheet, which prints indoor track as one row, it is %s in %s and '
      'number %d in %s, at %s and %s. Two hand-built sheets, %s apart on the same team in %s; '
      'neither is an invoice, and this page picks neither (rule 13a).\n\n'
      % ('first' if t['fin_rank25'] == 1 else 'number %d' % t['fin_rank25'], C.fy(2025),
         t['fin_rank24'], C.fy(2024), usd2(t['fin25']), usd2(t['fin24']),
         usd2(t['it24'] - t['fin24']), C.fy(2024)))
    S = m['sched']
    itc = [c for c in S['compare'] if c['fy'] == 2024 and c['sport'] == 'Indoor Track - Boys'][0]
    it5 = [c for c in S['compare'] if c['fy'] == 2025 and c['sport'] == 'Indoor Track - Boys'][0]
    it5g = [c for c in S['compare'] if c['fy'] == 2025 and c['sport'] == 'Indoor Track - Girls'][0]
    a('**Against the schedules.** ArbiterLive lists %s away meets for each indoor track team '
      'in %s, and %s for the boys and %s for the girls in %s. The sheet’s %s formula holds %s charges, halved between the two '
      'rows. Our bus model, one bus a meet with four hours of waiting at %s rates, puts %s’s '
      'listed meets at %s a team — **our estimate**, and less than half what the sheet '
      'prints. Either the schedule is short, or the waits were long, or both; the recordings '
      'below speak to the second, and nothing published measures either (section 3, '
      '*%s*).\n\n'
      % (C.num(itc['away']), C.fy(2024), C.num(it5['away']), C.num(it5g['away']), C.fy(2025),
         C.fy(2024),
         C.num(itc['charges']), C.fy(2026), C.fy(2024), usd2(itc['hi']), H['sheet']))
    if not itc['hi'] * 2 < itc['sheet']:
        fail('indoor track FY2024 is no longer more than twice its modelled upper bound')
    a('**Why outdoor track looks cheapest.** Only in %s, and only on rows whose season total the '
      'workbook prints as %s: the spring rows sum to %s, %s against %s’s %s. *A hypothesis:* the '
      'spring section was unfinished when the sheet was made; nothing here tests it '
      '(registered: *%s*).\n\n'
      % (C.fy(2025), usd2(spr['printed25']), usd2(spr['rows25']), C.pct(spr['fall_pct']),
         C.fy(2024), usd2(spr['rows24']), m['gaps']['spring25']))
    a('**What was said about track, in the recordings.** The town’s minutes of these meetings '
      'do not record it; our machine captions of the recordings do. Captions are a finding aid '
      'and not a record, so each is summarised in our words, no figure is taken from it, and '
      'each links to the video at the moment — check it there.\n\n')
    for c in m['captions']:
        a('- %s, %s, [video at %s](%s) (machine captions): %s\n'
          % (c['board'], c['date'], c['at'], c['url'], c['said']))
    a('\nThat fits the workbook read as teams: a meet in Boston is a long drive and a long wait, '
      'and the contract bills waiting by the hour, %s in %s and %s in %s. It does not measure '
      'any of it. No record of a single athletic trip — its date, team, miles or hours waiting '
      '— is published for any year (registered: *%s*).\n\n'
      % (usd2(y[2026]['wait_rate']), C.fy(2026), usd2(y[2027]['wait_rate']), C.fy(2027),
         m['gaps']['trips']))
    return ''.join(w)


def render_sec3(m):
    """Section 3: the district's per-sport sheet, and the posted schedules beside it. The
    schedule figures are counts; every dollar built from them is OUR ESTIMATE and says so."""
    sp, k, S, au = m['sports'], m['contract'], m['sched'], m['audit']
    y = m['ystep']
    w = []
    a = w.append
    byfy = {b_['fy']: b_ for b_ in S['by_fy']}
    f25 = byfy[2025]
    ch = S['charges']
    a('## 3. Sport by sport: the district’s sheet and the posted schedules\n\n')
    a('### In plain terms\n\n')
    a('In %s no single sport’s buses cost more than %s on the district’s sheet, and the five '
      'biggest together were %s of its %s. The schedules the district posts list %s away '
      'games that year, to %s different places on different days. **Our bus model** — miles to '
      'each venue at the contract’s per-mile rate, plus four hours of waiting at its hourly '
      'rate, at %s prices — puts that schedule at %s if teams going to the same place on the '
      'same day shared a bus, and %s if every team had its own. The waiting is %s to %s of it, '
      'and four hours is our assumption; the miles alone are %s to %s. The sheet’s whole total '
      'is below even the shared figure. Nobody publishes which buses ran, so the truth is not '
      'known to be anywhere in that range.\n\n'
      % (C.fy(2025), C.usd(m['top'][0]['fy2025']), C.usd(m['top5']), C.usd(sp['totals'][2025]),
         C.num(f25['away']), C.num(f25['trips']), C.fy(2026), C.usd(f25['lo']), C.usd(f25['hi']),
         C.usd(f25['lo_wait']), C.usd(f25['hi_wait']), C.usd(f25['lo_miles']),
         C.usd(f25['hi_miles'])))
    if not sp['totals'][2025] < f25['lo']:
        fail('the FY2025 sheet total is no longer below the shared-bus model')

    # ---- the schedules, by year
    a('### The schedules, year by year — OUR ESTIMATE in dollars\n\n')
    a('Every game ArbiterLive lists for a Lunenburg team, %s, with canceled, postponed and '
      'rained-out games left out. The counts are the schedules’; the miles are our measurement '
      '(driving routes on OpenStreetMap, from the high school and back); the dollars are our '
      'model. **Lower bound:** one bus for each distinct date and venue, its cost shared among '
      'every Lunenburg team there. **Upper bound:** one bus for every team-game. Whether buses '
      'were shared is not recorded anywhere. %s to %s are priced at %s rates (%s a mile, %s an '
      'hour waiting), because the earlier contract’s rates are not held (registered: *%s*); '
      '%s at its own, %s and %s.\n\n'
      % (C.fyspan(SCHED_YEARS[0], SCHED_YEARS[-1]), C.fy(SCHED_YEARS[0]), C.fy(2025),
         C.fy(2026), usd2(y[2026]['trip_rate']), usd2(y[2026]['wait_rate']), m['gaps']['rates'],
         C.fy(2027), usd2(y[2027]['trip_rate']), usd2(y[2027]['wait_rate'])))
    a('| FY | away team-games | distinct date-and-venue trips | away games with no distance | '
      'shared buses: miles | shared: waiting | **shared: total** | one bus per team: miles | '
      'per team: waiting | **per team: total** | priced at |\n'
      '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|\n')
    for b_ in S['by_fy']:
        a('| %s | %s | %s | %s | %s | %s | **%s** | %s | %s | **%s** | %s rates%s |\n' % (
            C.fy(b_['fy']), C.num(b_['away']), C.num(b_['trips']), C.num(b_['no_distance']),
            C.usd(b_['lo_miles']), C.usd(b_['lo_wait']), C.usd(b_['lo']), C.usd(b_['hi_miles']),
            C.usd(b_['hi_wait']), C.usd(b_['hi']), C.fy(b_['price_year']),
            ', schedule still being posted' if b_['fy'] == 2027 else ''))
    he = sum(b_['home_elsewhere'] for b_ in S['by_fy'])
    a('\nA game with no listed venue, or at one of the %s venues OpenStreetMap could not place, '
      'carries its waiting and no miles, so the miles column is a floor for those games. Left '
      'out of both bounds: %s home games played at a venue outside Lunenburg across the six '
      'years, most of them hockey at its home rink in Fitchburg — the district lists them as '
      'home, and whether a bus carried the team is not recorded. %s is the autumn as posted '
      'and the winter as far as it is posted; spring is not posted at all.\n\n'
      % (C.num(len(S['venues_without'])), C.num(he), C.fy(2027)))

    # ---- team by team
    a('**Away games played, team by team** (counts from the schedules; a dash is a year with '
      'no away game listed):\n\n')
    a('| sport | team | %s |\n|---|---|%s\n' % (' | '.join(C.fy(f) for f in SCHED_YEARS),
                                              '---:|' * len(SCHED_YEARS)))
    tk = sorted({(t['sport'], t['level']) for t in S['teams']})
    tv = {(t['fy'], t['sport'], t['level']): t for t in S['teams']}
    for sport_, lvl in tk:
        cells_ = []
        for f in SCHED_YEARS:
            t = tv.get((f, sport_, lvl))
            cells_.append(C.num(t['away']) if t and t['away'] else '—')
        a('| %s | %s | %s |\n' % (sport_, lvl, ' | '.join(cells_)))
    a('\nThe dollars for each team and year, both bounds and the waiting part separately, are '
      'in the page’s data (`/data/transportation.json`, `schedules.teams`).\n\n')

    # ---- the sheet against the schedules
    cmp_ = [c for c in S['compare'] if c['scheduled']]
    fl = S['flagged']
    below_lo = [c for c in cmp_ if c['sheet'] and c['sheet'] < c['lo']]
    above = [c for c in cmp_ if c['sheet'] > c['hi']]
    a('### %s\n\n' % H['sheet'])
    a('The district’s sheet beside each sport’s posted schedule, for the two years the sheet '
      'carries transportation. A *charge* is one amount typed into the sheet’s formula for '
      'that cell: `=532.5+375` is two. A cell typed as a bare number is one figure, not a '
      'formula, and is marked so. Where the sheet halves a formula between two rows (`/2`), '
      'each row shows the whole formula’s charges. The model columns are **OUR ESTIMATE** at '
      '%s prices.\n\n' % C.fy(2026))
    a('| FY | level | sport | sheet | charges in its formula | away games listed | distinct trips '
      '| model: miles alone, shared buses | model: shared, with waiting | model: one bus per '
      'team-game | reading |\n|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|\n')
    for c in sorted(S['compare'], key=lambda c: (c['fy'], c['level'], c['sport'])):
        if not c['scheduled']:
            read = 'no schedule posted'
        elif c['below_miles']:
            read = '**below the miles alone**'
        elif c['sheet'] > c['hi']:
            read = 'above the upper bound'
        elif c['sheet'] < c['lo']:
            read = 'below the shared bound with waiting'
        else:
            read = 'inside the range'
        nch = ('1 typed figure' if c['typed'] and c['charges'] else C.num(c['charges'])
               + (', halved' if c['halved'] else ''))
        a('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |\n' % (
            C.fy(c['fy']), c['level'], c['sport'], usd2(c['sheet']), nch,
            C.num(c['away']) if c['scheduled'] else '—', C.num(c['trips']) if c['scheduled'] else '—',
            usd2(c['lo_miles']) if c['scheduled'] else '—', usd2(c['lo']) if c['scheduled'] else '—',
            usd2(c['hi']) if c['scheduled'] else '—', read))
    a('\n**What the data shows.** ')
    a('%s sport-years print less than the miles alone would cost on the lower bound — shared '
      'buses and no waiting at all, so the four-hour assumption plays no part: %s. %s of the %s '
      'are in %s’s spring, the section already registered as possibly unfinished (*%s*). '
      % (C.num(len(fl)), '; '.join('%s %s %s, %s against %s away %s and %s of miles'
                                   % (C.fy(c['fy']), c['level'], c['sport'], usd2(c['sheet']),
                                      C.num(c['away']), 'game' if c['away'] == 1 else 'games',
                                      usd2(c['lo_miles'])) for c in fl),
         C.num(sum(1 for c in fl if c['fy'] == 2025 and c['season'] == 'Spring')), C.num(len(fl)),
         C.fy(2025), m['gaps']['spring25']))
    a('In the other direction, %s sport-years print more than one bus for every listed game '
      'would cost: %s. Indoor track’s %s formula holds %s charges against %s meets listed per '
      'team. Across all %s scheduled sport-years, %s fall below the shared bound once four '
      'hours of waiting is counted — which says as much about that assumption, and about the '
      'old contract’s unknown prices, as about the sheet.\n\n'
      % (C.num(len(above)), '; '.join('%s %s %s, %s against %s' % (
          C.fy(c['fy']), c['level'], c['sport'], usd2(c['sheet']), usd2(c['hi'])) for c in above),
         C.fy(2024), C.num([c for c in cmp_ if c['fy'] == 2024 and c['sport'] == 'Indoor Track - Boys'][0]['charges']),
         C.num([c for c in cmp_ if c['fy'] == 2024 and c['sport'] == 'Indoor Track - Boys'][0]['away']),
         C.num(len(cmp_)), C.num(len(below_lo))))
    a('**The charges themselves changed shape.** In %s the sheet’s formulas hold %s charges '
      'with a median of %s, a median of %s to a cell; in %s, %s charges with a median of %s, '
      'a median of %s to a cell. *A hypothesis:* the %s figures are monthly or seasonal '
      'invoice totals rather than trips; nothing here tests it, so a %s charge count is not a '
      'trip count.\n\n'
      % (C.fy(2024), C.num(ch[2024]['n']), usd2(ch[2024]['median']), nfmt(ch[2024]['per_cell']),
         C.fy(2025), C.num(ch[2025]['n']), usd2(ch[2025]['median']), nfmt(ch[2025]['per_cell']),
         C.fy(2025), C.fy(2025)))
    a('**What it does not show** is which is wrong. Every one of these fits the same numbers, '
      'and the data cannot choose between them:\n\n')
    a('- *the sheet is incomplete* — charges not yet entered when it was made;\n'
      '- *the schedule is incomplete* — ArbiterLive lists only what a coach posted, and track '
      'lists fewer meets than its formulas hold charges;\n'
      '- *buses were shared* more widely than one date and venue — teams going the same way, a '
      'single bus dropping two teams;\n'
      '- *no bus went* — a van, parents driving, or a team riding with another school;\n'
      '- *a charge is not a trip* — an invoice can cover a month, or several teams;\n'
      '- *waiting was not four hours* — a game is shorter, a meet in Boston longer.\n\n')
    a('What would settle it is the same document for every row: Dee Bus’s athletic invoices, '
      'each trip’s date, team, miles and hours waiting (registered: *%s*).\n\n'
      % m['gaps']['trips'])

    # ---- the sheet's own numbers, kept
    a('### The district’s sheet, sport by sport\n\n')
    a('From the district’s sport-by-sport workbook; the cell is the workbook’s own.\n\n')
    a('| season | level | sport | %s | %s |\n|---|---|---|---:|---:|\n'
      % (C.fy(2024), C.fy(2025)))
    for r in sp['rows']:
        a('| %s | %s | %s | %s | %s |\n' % (
            r['season'], r['level'], r['sport'],
            usd2(r['fy2024']) if r['fy2024'] is not None else '—',
            usd2(r['fy2025']) if r['fy2025'] is not None else '—'))
    a('| **all** | | | **%s** | **%s** |\n\n'
      % (usd2(sp['totals'][2024]), usd2(sp['totals'][2025])))
    a('**Season totals against the workbook’s own.** ')
    bad = [s_ for s_ in sp['seasons'] if not s_['ties']]
    good = [s_ for s_ in sp['seasons'] if s_['ties']]
    a('%s of %s season totals the workbook prints equal the sum of its own rows. ' %
      (C.num(len(good)), C.num(len(sp['seasons']))))
    for s_ in bad:
        a('%s %s prints %s in cell %s while its rows sum to %s; this page uses the rows. '
          % (s_['season'], C.fy(s_['fy']),
             usd2(s_['printed']) if s_['printed'] is not None else 'nothing',
             s_['cell'], usd2(s_['rows'])))
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
    a('\nOn the %s sports both sheets print for %s, the workbook totals %s and the Finance '
      'Committee copy %s, %s lower. This page publishes both and picks neither.\n\n'
      % (C.num(au['sheets']['n']), C.fy(2024), usd2(au['sheets']['workbook']),
         usd2(au['sheets']['fincom']), C.pct(au['sheets']['lower_pct'])))
    a('**Paired sports carry identical figures**, so a per-sport amount is an allocation, not '
      'a measurement — one bus split between two teams would print this way (a hypothesis): '
      '%s.\n\n' % '; '.join('%s %s %s, %s each' % (
          C.fy(p['fy']), p['level'], ' and '.join(p['sports']), usd2(p['value']))
          for p in au['paired']))
    spr = au['spring']
    a('**Spring %s.** Its rows sum to %s, %s against %s’s %s, and spring is %s of the whole '
      'decline from %s to %s. The workbook prints %s as the season total. *A hypothesis:* the '
      'spring section was unfinished when the sheet was made; nothing here tests it.\n'
      % (C.fy(2025), usd2(spr['rows25']), C.pct(spr['fall_pct']), C.fy(2024),
         usd2(spr['rows24']), C.pct(spr['share_of_drop']), C.fy(2024), C.fy(2025),
         usd2(spr['printed25'])))
    a('\n**One trip, priced.** On 4 March 2026 a teacher told the School Committee a class '
      'field trip would cost *“%s”*: one Dee Bus trip under the new contract, between the bid '
      'form’s average trip of %s miles priced with no waiting, %s, and with its four hours, %s '
      '([minutes](%s)).\n\n'
      % (usd2(m['field_trip']), C.num(k['per_trip_miles']), usd2(k['trip_nowait']),
         usd2(k['trip_full']), [q for q in m['quotes'] if q['key'] == 'field-trip'][0]['cite']))
    a('### What this does not show\n\n')
    a('- **A count of bus trips.** The schedules say where teams played, not whether a bus '
      'went, was shared, or how long it waited. The model gives a range and both ends are '
      'ours.\n')
    a('- **The prices actually paid before %s.** %s to %s ran under the previous contract, '
      'whose rates were requested on 9 October 2026 and not delivered; every model figure for '
      'those years is at %s prices.\n' % (C.fy(2026), C.fy(SCHED_YEARS[0]), C.fy(2025),
                                         C.fy(2026)))
    a('- **Teams with no schedule.** Cheer posts none, and some teams post none in some years '
      '(the coverage file says which); a sport with no listed games is not a sport with no '
      'buses (registered: *%s*).\n' % m['gaps']['schedules'])
    a('- **The bid form’s own arithmetic.** Its trip lines multiply a trip count by the rate by '
      'a mileage figure (%s × rate × %s and so on); the mileage figures sum to %s, not the '
      '%s its estimate states. The subtotal is a quantity for comparing bids, not a forecast; '
      'this page takes only its rates and its four hours.\n\n'
      % (C.num(TRIP_ROWS[0][0]), C.num(TRIP_ROWS[0][1]), C.num(k['form_mile_rows']),
         C.num(k['form_miles'])))
    return ''.join(w)


KIND_MD = {'measured': 'measured', 'quote': 'on the record', 'caption': 'machine captions — '
           'check the video', 'estimate': 'our estimate', 'hypothesis': 'a hypothesis — nothing '
           'here tests it', 'gap': 'not published'}


def render_brief_md(b):
    """The brief as markdown, for /docs, the PDF and any reader that cannot run the page."""
    w = []
    a = w.append
    a('## The short version\n\n')
    a('%s\n\n' % b['answer']['text'])
    t = b.get('costs')
    if t:
        a('**%s**\n\n' % t['title'])
        a('| | %s |\n|---|%s\n' % (' | '.join(t['cols']), '---:|' * len(t['cols'])))
        for r in t['rows']:
            lab = ('**%s**' % r['label']) if r['total'] else r['label']
            a('| %s | %s |\n' % (lab, ' | '.join(c['text'] if c else '—' for c in r['cells'])))
        a('\n%s\n\n' % t['note']['text'])
    l = b.get('ladder')
    if l:
        TAG = {'contract': ' *(contract)*', 'statute': ' *(law)*', 'estimate': ' *(our estimate)*',
               'gap': ' *(not published)*'}
        for i, t in enumerate(l['tiers'], 1):
            a('**%d. %s**\n\n| | |\n|---:|---|\n' % (i, t['title']))
            for f in t['facts']:
                a('| %s | %s%s |\n' % (f['value']['text'] if f['value'] else '—',
                                        f['label']['text'], TAG.get(f['kind'], '')))
            a('\n')
        a('**%d. %s**\n\n' % (len(l['tiers']) + 1, l['title']))
        ids = {f['id']: f for t in l['tiers'] for f in t['facts']}
        for i, c in enumerate(l['conclusions'], 1):
            a('%d. **%s** Rests on %s.\n' % (i, c['text'], ', '.join(
                ids[r]['value']['text'] if ids[r]['value'] else 'not published'
                for r in c['rests_on'])))
        a('\n')
    for c in b['chains']:
        a('**%s.** *%s* **%s**\n\n' % (c['label'], c['question'], c['say']['text']))
        for st_ in c['steps']:
            bits = [KIND_MD[st_['kind']]]
            if st_.get('cite'):
                bits.append('[%s](%s)' % (st_['cite']['label'], st_['cite']['href']))
            if st_.get('link'):
                bits.append('[%s](#%s)' % (st_['link']['label'], st_['link']['anchor']))
            tail = (' Would settle it: %s.' % st_['closes']) if st_.get('closes') else ''
            a('- %s%s *(%s)*\n' % (st_['text'], tail, '; '.join(bits)))
        a('\n')
    return ''.join(w)


def render_md(m, rows, brief):
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

    # ---- the short version IS the brief (notes/process/REPORT-FORMAT.md): the answer, a
    # verdict per question, the sentence to repeat, what it rests on, and what to ask for.
    a(render_brief_md(brief))
    a('---\n\n')

    # ---- the evidence each answer links into, then the charts, then the inventory
    a(render_audit(m, rows))

    a('## The charts\n\n')
    a('![Athletic transportation by year: the general fund line voted and spent, beside the '
      'full cost where a district document states one — the fee fund’s share FY2014 to FY2017 '
      'and the district’s by-sport sheet for FY2024 and FY2025.](charts/transportation-athletics.svg)\n\n')
    a('![Athletic transportation by sport, FY2024 and FY2025: the district’s by-sport workbook '
      'as bars, and beside each bar our bus model from the posted schedules, from shared buses '
      'to one bus per team, at FY2026 prices.](charts/transportation-sports.svg)\n\n')
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
    sh = m['audit']['sheets']
    a('The athletic bus line in the town budget used to be a fraction of what athletic buses '
      'cost; the athletic fee fund — what families pay to play — covered the rest. In %s the '
      'district’s by-sport workbook put the cost at %s while the voted line was %s; on the %s '
      'sports both of its sheets print, one says %s and the other %s, and the town has not '
      'said which is right. Either way the cost was above the line. From %s the line was set '
      'to carry the full cost, and the district said so at the time. In %s the balanced '
      'budget cut it to %s.\n\n'
      % (C.fy(2024), C.usd(sp['totals'][2024]), C.usd(a24['budget']), C.num(sh['n']),
         C.usd(sh['workbook']), C.usd(sh['fincom']), C.fy(2026), C.fy(2027),
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
      '%s still committed at the close, %s in all against %s voted. Section 3 sets each sport '
      'beside its posted schedule.\n\n'
      % (C.fy(2026), C.usd(L['athletic']['expended']), C.usd(L['athletic']['committed']),
         C.usd(L['athletic']['spent']), C.usd(L['athletic']['budget'])))
    a('### What this does not show\n\n')
    a('- **Whether teams rode more or less.** Dollars moved between two payers; no trip count '
      'is published for any year (registered: *%s*).\n' % m['gaps']['trips'])
    a('- **That the sheet is right.** It is assembled by hand, and the district has not stood '
      'behind any per-sport figure (registered: *%s*).\n\n' % m['gaps']['sport-cost'])

    # ---- 3. per sport, and the schedules beside it
    a(render_sec3(m))

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
    # TWO TABLES: the unit prices, then what each year's printed total is MADE OF. TJ,
    # 11 October 2026: "What's the cost breakdown in the transportation contract? I'm not
    # sure I saw it on the report." The total was printed and its parts were not -- and
    # nearly half of it is the form's trip arithmetic, which is not a forecast.
    a('**The unit prices.**\n\n')
    a('| year | 77-passenger, per bus per day | 83-passenger | trip rate (per mile) | waiting, per hour | bid form page |\n')
    a('|---|---:|---:|---:|---:|---|\n')
    for c in k['years']:
        a('| %s%s | %s | %s | %s | %s | p%d (IFB p%d) |\n' % (
            C.fy(c['fy']), ' (optional)' if c['optional'] else '', usd2(c['p77']),
            usd2(c['p83']), usd2(c['trip_rate']), usd2(c['wait_rate']),
            c['pdf_page'], c['form_page']))
    a('\n**What each year’s total is made of.** Three parts, recomputed from the prices above '
      'and footed to the total the form prints:\n\n')
    a('| year | regular routes: %s + %s buses × %s days | trip lines on the form | waiting on the form: %s trips × %s hours | year total as printed |\n'
      % (C.num(N77), C.num(N83), C.num(DAYS), C.num(FORM_TRIPS), C.num(FORM_WAIT_HOURS)))
    a('|---|---:|---:|---:|---:|\n')
    for c in k['years']:
        a('| %s%s | %s | %s | %s | %s |\n' % (
            C.fy(c['fy']), ' (optional)' if c['optional'] else '', usd2(c['regular']),
            usd2(c['trip_lines']), usd2(c['wait_line']), usd2(c['total'])))
    y26 = [c for c in k['years'] if c['fy'] == 2026][0]
    a('\n**Only the first column is a budget.** The regular routes are the whole regular-route '
      'line, and the %s budget carries that price exactly. The trip lines multiply a trip count '
      'by the rate by a mileage figure (%s × rate × %s, and so on), so %s of the %s total is a '
      'quantity for comparing bids, not spending anybody expects: the form’s own estimate is '
      '%s trips and %s miles, which at %s a mile is %s. What athletics and field trips '
      'actually cost depends on the trips run, at the per-mile and per-hour rates above.\n\n'
      % (C.fy(2027), C.num(TRIP_ROWS[0][0]), C.num(TRIP_ROWS[0][1]), C.usd(y26['trip_lines']),
         C.fy(2026), C.num(FORM_TRIPS), C.num(FORM_MILES), usd2(y26['trip_rate']),
         C.usd(FORM_MILES * y26['trip_rate'])))
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
    A = m['audit']
    a('## Read as each reader\n\n')
    a('`notes/process/PERSONAS.md`, run before publishing, again after the audit pass '
      '(`notes/process/AUDIT-PASS.md`) changed what the summary leads with, and again when the '
      'top became verdicts (`notes/process/REPORT-FORMAT.md`).\n\n')
    a('- **Already sure the schools are not straight with them.** The page used to open on '
      'athletic buses’ share of spending, which nobody disputes. It now opens on six verdicts, '
      'two of them **Does not match**: the special education line %s past its budget, and the bus '
      'fee leaving the general fund paying the full contract. Each sentence is a measurement, '
      'and every step under it says whether it is measured, on the record, or a hypothesis.\n'
      % C.usd(A['sped26']['over']))
    a('- **Hears it second-hand.** The sentence they will repeat is the bold one in each '
      'verdict: true as worded, with its figure and its year inside it.\n')
    a('- **Close to the boards.** No finding names a person. One verdict is **Matches** — regular '
      'routes planned to the dollar — and it is on the first screen, not after the problems.\n')
    a('- **Finance Committee.** Two things bear on %s: the special education line is budgeted '
      '%s above %s’s spending after overrunning, and this site’s model sits %s under a contract '
      'price already signed. The contract’s end, 30 June 2028, is in the regular-routes '
      'layers.\n'
      % (C.fy(2028), C.usd(A['sped27_margin']), C.fy(last), C.usd(A['model']['gap'])))
    a('- **School Committee.** *Did the new bus fee lower what the town pays?* and *Who pays for '
      'athletic buses?* are verdicts three and four: the general fund paid the full contract, '
      'and %s of restored athletic buses goes back on the fee fund. Each is stated as a '
      'comparison and ends on what is not yet known, not on a charge or a demand.\n'
      % C.pct(A['restore']['fund_pct'], 0))
    a('- **Select Board.** Nothing here compares the town side with the school side; the Monty '
      'Tech buses, a town appropriation, are named and left out.\n')
    a('- **The parent whose programme is on the list.** Every sport is findable by name in '
      'section 3, with both district sheets’ figures where they differ. Band trips are in '
      'section 1: the %s balanced budget carries nothing for them while the Finance Committee '
      'was told they would be reduced.\n' % C.fy(2027))
    a('- **Somebody with one concrete thing (the meeting search).** Every recent line that ran '
      'over its revised budget was searched, and so were the fee fund and the bus fee. The '
      'regular-route line ran over in %s and %s; a Finance Committee member asked for the bus '
      'contracts that spring — quoted. Athletic transportation came in under its revised '
      'budget in %s, the year before it was cut, while athletes were being driven privately '
      'under a signed waiver — quoted. Special education transportation ran over in %s; the '
      'search found the district’s account of the state’s reimbursement and the FY2027 figure '
      'shown to the Finance Committee — both quoted — and no discussion of the overrun in the '
      'minutes searched. The fee fund draw was voted on 26 August 2026 — quoted. Track buses '
      'were searched in both corpora: the town’s minutes do not record the discussion, and the '
      'recordings’ captions do — summarised and linked at the moment, never quoted.\n'
      % (C.fy(2023), C.fy(2024), C.fy(last),
         ' and '.join(C.fy(x['fy']) for x in m['recent_over'])))
    a('- **Grilled.** The first draft measured the special education rise from %s, its lowest '
      'year — a year of school closures. It now starts from %s and says why. The audit pass '
      'then found the summary was an inventory: its first card was a share nobody would '
      'dispute. The window for the special education under-budget run is ours and is stated '
      'as a rule, and the overrun is computed from the year-end report’s own cents rather than '
      'from rounded figures. On 11 October 2026 the per-sport trip figure was withdrawn: it '
      'divided %s dollars by a trip priced at %s rates, and that trip was the bid form’s long '
      'hypothetical one, so small sports read as about one trip. The schedules replaced it.\n\n'
      % (C.fy(2020), C.fy(m['sped_low']['fy']), C.fy(2025), C.fy(2026)))

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
    a('- **The bus model is OUR ESTIMATE wherever it appears.** Games are each team’s listings '
      'on ArbiterLive, the scheduling site the district links from its athletics page, read '
      'on %s by `scripts/fetch_arbiter_schedules.py` and extracted to '
      '`sources/data/athletics-schedules.csv`, with what each team-year’s listing covers in '
      '`athletics-schedules-coverage.csv`. **ArbiterLive’s pages are not archived or '
      'republished here**; the page cites the schedules as facts — '
      'date, team, opponent, venue, home or away — and takes nothing else from them. Venue '
      'miles are ours: each address geocoded on OpenStreetMap and driven from the high school '
      'and back by OSRM (`athletics-venue-distances.csv`); %s venues could not be placed. A '
      'trip costs its miles at the contract’s per-mile rate plus %s hours at its waiting rate '
      '— the bid form’s own four hours, adopted as our assumption, and always shown apart. '
      'Lower bound: one bus per date and venue, shared; upper: one per team-game. Years before '
      '%s are at %s prices. The crosswalk from a scheduled team to a row of the district’s '
      'sheet is ours (`SHEET_TEAMS`), and every scheduled team must land in one row or the '
      'build stops.\n' % (m['stest']['fetched'], C.num(len(m['sched']['venues_without'])),
                          C.num(WAIT_HOURS), C.fy(2026), C.fy(2026)))
    a('- **Every line is net.** A general fund budget line is what the town raises after '
      'anything else that pays for the thing — bus fees, the athletic fee fund, state '
      'reimbursement — has been taken off (rule 11). None of those is netted into any figure '
      'here; each has its own column.\n\n')

    # ---- sources
    a('## Sources\n\n')
    for s in sources():
        a('- **%s** — %s. `%s` sha256 `%s`\n' % (s['publisher'], s['note'], s['path'],
                                                s['sha256'][:12]))
    a('- **ArbiterLive** (arbiterlive.com), the district’s linked athletic scheduling site — '
      'every game listed for Lunenburg’s teams, %s, read %s. The pages are not archived or '
      'republished. Our extract: `sources/data/athletics-schedules.csv`; our '
      'venue distances: `sources/data/athletics-venue-distances.csv`.\n'
      % (C.fyspan(SCHED_YEARS[0], SCHED_YEARS[-1]), m['stest']['fetched']))
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
    """The sheet's dollars as bars, and OUR bus model for the same sport-year as a thin line
    from the shared-bus bound to the one-bus-per-team bound, at FY2026 prices."""
    rows = [r for r in pay['sports'] if (r['fy2024'] or r['fy2025'])]
    W, L, R, T, rowh = 780, 230, 20, 52, 18
    H = T + rowh * len(rows) + 30
    top = max(max(r['fy2024'] or 0, r['fy2025'] or 0,
                  (r['model2024'] or {}).get('hi', 0), (r['model2025'] or {}).get('hi', 0))
              for r in rows)
    hi = nice_top(top, 2000)
    x = lambda v: L + (W - L - R) * v / hi
    o = [HEAD % (W, H)]
    v = 0
    while v <= hi:
        o.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="%s"/><text x="%.1f" y="%d" '
                 'text-anchor="middle" fill="%s">%s</text>'
                 % (x(v), x(v), T - 4, H - 26, COL['grid'], x(v), H - 12, COL['muted'],
                    html.escape(C.usd(v))))
        v += 4000 if hi > 12000 else 2000
    for i, r in enumerate(rows):
        yy = T + i * rowh
        o.append('<text x="%d" y="%d" text-anchor="end" fill="%s">%s</text>'
                 % (L - 6, yy + 12, COL['ink'], html.escape(r['label'])))
        for fy, dy, op in ((2024, 2, '0.4'), (2025, 9, '1')):
            v_ = r['fy%d' % fy]
            if v_:
                o.append('<rect x="%d" y="%d" width="%.1f" height="7" fill="%s" fill-opacity="%s"/>'
                         % (L, yy + dy, x(v_) - L, COL['athletic'], op))
            md = r['model%d' % fy]
            if md:
                o.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s" '
                         'stroke-width="1.5" stroke-opacity="%s"/>'
                         % (x(md['lo']), x(md['hi']), yy + dy + 3.5, yy + dy + 3.5, COL['ink'],
                            '0.45' if fy == 2024 else '1'))
    legend(o, [('FY2024 sheet', COL['athletic'], 'pale'), ('FY2025 sheet', COL['athletic'], 'box')],
           L, 10)
    o.append('<line x1="%d" x2="%d" y1="34" y2="34" stroke="%s" stroke-width="1.5"/>'
             '<text x="%d" y="38" fill="%s">our bus model from the schedules, shared buses to '
             'one per team, at FY2026 prices (our estimate)</text>'
             % (L, L + 24, COL['ink'], L + 30, COL['muted']))
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
    brief = build_brief(m)
    pay = payload(m, rows, brief)
    md = render_md(m, rows, brief)
    # Every link the brief makes into the evidence must land on a heading the markdown
    # actually writes, or the skeptic who follows it lands nowhere.
    heads = {slug(h) for h in re.findall(r'^#{2,3} (.+)$', md, re.M)}
    dead = sorted({st_['link']['anchor'] for c in brief['chains'] for st_ in c['steps']
                   if st_.get('link')} - heads)
    if dead:
        fail('the brief links to headings the markdown does not write: %s' % dead)
    topics = build_topics(m, brief, pay)
    return {
        **{os.path.join(ROOT, 'fy28', 'public', 'data', 'topics', '%s.json' % t):
           json.dumps(p_, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
           for t, p_ in topics.items()},
        OUT_JSON: json.dumps(pay, indent=1, ensure_ascii=False, sort_keys=True) + '\n',
        OUT_MD: md,
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



# --------------------------------------------------------------------- topic pages
#
# THE REPORT, SPLIT INTO PAGES (scripts/topics.py has the model and the registry). TJ, 12
# October 2026: "nobody will ever read these full reports". The hub and nine topic pages are
# written HERE, from the same measurements and the same verified chain layers as the report,
# in the same pass -- so a page and the report cannot disagree. Facts are the ladder's own,
# looked up by id; a page adds only what the ladder does not hold.

def build_topics(m, brief, pay):
    import topic as TP
    import ladder as LD
    from brief import step
    A, last, k, st = m['audit'], m['last'], m['contract'], m['state']
    by = {r['fy']: r for r in m['ledger']}
    U = lambda v: figure(v, C.usd(v))
    U2 = lambda v: figure(v, usd2(v))
    F = lambda v: figure(v, C.fy(v), 'fiscal year')
    P = lambda v, dp=1: figure(v, C.pct(v, dp))
    N = lambda v: figure(v, C.num(v))
    fact = {f['id']: f for t in brief['ladder']['tiers'] for f in t['facts']}
    chains = {c['id']: c for c in brief['chains']}
    steps = lambda cid, *kinds: [s_ for s_ in chains[cid]['steps'] if s_['kind'] in kinds]
    link1 = lambda cid: [s_ for s_ in chains[cid]['steps'] if s_.get('link')][:1]
    qs = {q['key']: q for q in m['quotes']}
    cap = {c['key']: c for c in m['captions']}
    said = lambda *keys: [dict(quote=qs[q]['quote'], board=qs[q]['board'], date=qs[q]['date'],
                               href=qs[q]['cite'], label='%s minutes, %s'
                               % (qs[q]['board'], qs[q]['date'])) for q in keys]
    heard = lambda key: dict(quote=cap[key]['said'], board=cap[key]['board'],
                             date=cap[key]['date'], href=cap[key]['url'], caption=True,
                             label='%s, %s, video at %s (machine captions)'
                             % (cap[key]['board'], cap[key]['date'], cap[key]['at']))
    srcs = sources()
    src = lambda *parts: [dict(label='%s — %s' % (s_['publisher'], s_['filename']),
                               href=s_['docs_url'])
                          for s_ in srcs if any(p_ in s_['path'] for p_ in parts)]
    chart = lambda cid: dict(id='transportation-' + cid, source='/data/transportation.json')
    # Sources this report's list does not carry, because the report cites them in prose:
    # our schedule datasets, and the town's revenue projection behind "mostly taxes".
    SCHED = [dict(label='Lunenburg Budget Project — every game on the district’s posted '
                        'athletic schedules (ArbiterLive), FY2022–FY2027',
                  href='/docs/data/athletics-schedules.csv'),
             dict(label='Lunenburg Budget Project — road distance to every away venue',
                  href='/docs/data/athletics-venue-distances.csv')]
    REVDIST = [dict(label='Town of Lunenburg — draft-rev-dist.-proj-fy26-update-2.27.25.xlsx',
                    href='/docs/budget-workbooks/finance-committee/fy26-budget/'
                         'draft-rev-dist.-proj-fy26-update-2.27.25.xlsx')]
    f, con = LD.fact, TP.conclusion
    x, s26, fb, r = A['mask'], A['sped26'], A['fund']['by'], A['restore']
    sch = {row['fy']: row for row in m['sched']['by_fy']}
    out = {}

    # ---- the hub: the report's own top, unchanged -- answer, chart, matrix, conclusions.
    out['transportation'] = TP.hub(
        'transportation', brief['answer']['text'], brief['ladder'], brief['chains'],
        chart=chart('schools-athletics'),
        table=pay['tables']['transportation-schools-athletics'],
        answer_figures=brief['answer']['figures'], answer_allow=brief['answer']['literals'])

    # ---- Dee Bus contract
    yrs = k['years']
    contract_table = dict(caption='The Dee Bus contract, year by year', views=[dict(
        key='contract', label='As bid', total_col=4, kinds=['ledger'] * 5,
        columns=['77-passenger, a day', '83-passenger, a day', 'A trip mile', 'An hour waiting',
                 'Regular routes, the year'],
        rows=[dict(label=C.fy(c['fy']) + (' (option)' if c['optional'] else ''),
                   cells=[usd2(c['p77']), usd2(c['p83']), usd2(c['trip_rate']),
                          C.usd(c['wait_rate']), C.usd(c['regular'])]) for c in yrs],
        note='The bid form Dee Bus signed on 27 December 2024. The last two years are '
             'optional extensions.')])
    out['dee-bus-contract'] = TP.page(
        'dee-bus-contract',
        'Regular routes cost exactly the contract price, which is fixed through %s.' % C.fy(2028),
        [fact['regular'], fact['buses'], fact['days'], fact['bus-day'], fact['rise27'],
         fact['rise28'], fact['fixed28'], fact['levy']],
        [con('Regular routes now cost exactly what the Dee Bus contract says.',
             ['regular', 'bus-day'], notes=steps('regular', 'gap') + link1('regular')),
         con('The price rises faster than the levy may grow, in every year of the contract.',
             ['rise27', 'rise28', 'levy', 'fixed28'])],
        chart=chart('contract'), table=contract_table,
        said=said('contract', 'renewal', 'contracts-asked'),
        sources=src('dee-bus', 'glytdbud-expense-fy2026-p13-gf-school'),
        finding_figures={'y': F(2028)})

    # ---- Special education transportation
    # VOTED AND REVISED, BOTH SHOWN. The page's conclusion measures against the REVISED
    # budget ($67,555); against the vote it is $2 more. Side by side with only one budget
    # column, the two read as an error. Revised is the budget at the close, after transfers.
    sped_rows = [dict(label=C.fy(fy), cells=[
        C.usd(by[fy]['sped']['budget']), C.usd(by[fy]['sped']['revised']),
        C.usd(by[fy]['sped']['spent']),
        C.usd(by[fy]['sped']['spent'] - by[fy]['sped']['revised'])])
        for fy in sorted(by, reverse=True)]
    out['special-education-transportation'] = TP.page(
        'special-education-transportation',
        'The fastest-growing bus line: %s a year, and %s past its %s budget.'
        % (C.pct(A_rate(m, 'sped')), C.usd(s26['over']), C.fy(last)),
        [fact['sped'], fact['sped-rate'], fact['over'],
         f('sped27', U(A['sped27']), 'budgeted for %s' % C.fy(2027), 'published', {'y': F(2027)}),
         fact['state'], fact['vans'], fact['van-rate']],
        [con('Special education buses spent %s more than their %s budget, and no transfer '
             'covered it.' % (C.usd(s26['over']), C.fy(last)), ['over', 'sped'],
             {'o': U(s26['over']), 'y': F(last)},
             notes=steps('sped', 'hypothesis') + link1('sped')),
         con('It grows fastest of any bus line, and nothing published counts what it buys.',
             ['sped-rate', 'vans', 'van-rate'], notes=steps('sped', 'gap'))],
        chart=chart('sped'),
        table=dict(caption='Special education transportation by year', views=[dict(
            key='sped', label='Voted and spent', total_col=3, kinds=['ledger'] * 4,
            columns=['Voted', 'Revised', 'Spent', 'Spent past the revised budget'],
            rows=sped_rows,
            note='Town general fund. Voted before the year; revised is the budget at the close, '
                 'after any transfer; spent is paid plus still owed. A negative last column is '
                 'money left unspent.')]),
        said=said('fincom-sped27', 'cb-75'),
        sources=src('glytdbud-expense', 'district-expenditures-by-function'),
        finding_figures={'r': P(A_rate(m, 'sped')), 'o': U(s26['over']), 'y': F(last)})

    # ---- State reimbursement
    cb = {c['fy']: c for c in st['cb']}
    of_sped = pct1(cb[last]['transport'], by[last]['sped']['spent'])
    out['state-reimbursement'] = TP.page(
        'state-reimbursement',
        'The state repays %s of what the town spends on buses, all of it for special education.'
        % C.pct(pct1(cb[last]['transport'], by[last]['all_spent'])),
        [fact['state'], fact['state-share'],
         f('cb-sped', P(of_sped), 'of special education buses repaid', 'published'),
         fact['no-aid'], fact['sped']],
        [con('The state repays a small share, and nothing for regular routes or athletics.',
             ['state', 'state-share', 'no-aid'], notes=link1('offsets')),
         con('What it repays is last year’s claims, not this year’s buses.', ['cb-sped'])],
        # THE SMALL SHARE, DRAWN: what the state repaid beside what the buses cost, never
        # netted (rule 11). The circuit breaker pays a year's claims the year after.
        chart=TP.series(
            'What the state repays, beside the bus bill',
            [C.fy(y) for y in sorted(cb) if y <= last],
            [TP.track('All buses, spent', [by[y]['all_spent'] for y in sorted(cb) if y <= last],
                      'published', 'bar'),
             TP.track('Special education buses, spent',
                      [by[y]['sped']['spent'] for y in sorted(cb) if y <= last], 'published', 'bar'),
             TP.track('Circuit breaker, transportation',
                      [cb[y]['transport'] for y in sorted(cb) if y <= last], 'published', 'bar')],
            '$', kind='bar',
            note='Spent is the town general fund at the close. The circuit breaker is what the '
                 'state paid that year, for the year before’s claims.'),
        said=said('cb-75'),
        sources=src('circuit-breaker', 'district-expenditures'),
        finding_figures={'s': P(pct1(cb[last]['transport'], by[last]['all_spent']))})

    # ---- Bus fee
    fee_acct = st['fee'][last]
    kp = {c['fy']: c for c in k['years']}
    if round(kp[last]['regular'] - by[last]['regular']['budget']) != m['netted']:
        fail('the bus-fee chart’s contract and voted bars no longer differ by the netted amount')
    if abs(by[last]['regular']['spent'] - kp[last]['regular']) > 0.5:
        fail('regular routes no longer spent exactly the contract price; the bus-fee note says so')
    out['bus-fee'] = TP.page(
        'bus-fee',
        'The new bus fee did not lower what the school budget paid for buses in %s.' % C.fy(last),
        [f('fee-one', U(m['fees']['one']), 'a year, one child', 'published'),
         f('fee-family', U(m['fees']['family']), 'a year, two or more children', 'published'),
         f('requests', N(m['requests']), 'bus requests, June 2025', 'published', allow=('June 2025',)),
         f('unpaid', N(m['unpaid']), 'of them unpaid at the time', 'published'),
         f('netted', U(m['netted']), 'the budget was voted below the contract', 'published'),
         f('moved', U(m['moved_back']), 'moved back in during the year', 'published'),
         f('fee-acct', U(fee_acct), 'into the only account named for fees, %s' % C.fy(last),
           'published', {'y': F(last)})],
        [con('The line was voted %s below the contract, and %s was moved back in during the year.'
             % (C.usd(m['netted']), C.usd(m['moved_back'])), ['netted', 'moved'],
             {'a': U(m['netted']), 'b': U(m['moved_back'])}),
         con('Where the fee money is booked is not established.', ['fee-acct'],
             notes=steps('offsets', 'gap'))],
        chart=TP.series(
            'Regular routes against the contract',
            ['Contract price', 'Voted', 'After transfers', 'Spent'],
            [TP.track('Regular routes, %s' % C.fy(last),
                      [kp[last]['regular'], by[last]['regular']['budget'],
                       by[last]['regular']['revised'], by[last]['regular']['spent']],
                      'published', 'bar')],
            '$', kind='bar',
            note='Voted %s under the %s contract price, then %s moved back in, and %s spent: the '
                 'whole contract. Town general fund, %s.'
                 % (C.usd(m['netted']), C.usd(kp[last]['regular']), C.usd(m['moved_back']),
                    C.usd(by[last]['regular']['spent']), C.fy(last)),
            note_figures={'a': U(m['netted']), 'c': U(kp[last]['regular']),
                          'b': U(m['moved_back']), 's': U(by[last]['regular']['spent']),
                          'y': F(last)}),
        said=said('fee-11000', 'requests'),
        sources=src('glytdbud-expense', 'school-choice', 'fee'),
        finding_figures={'y': F(last)})

    # ---- FY2027 bus budget
    bud = [r_ for r_ in pay['by_year'] if r_['fy'] >= 2022]
    for r_ in bud:
        if r_['school_budget'] + r_['athletic_budget'] + r_['band_budget'] != r_['all_budget']:
            fail('FY%d: school-day, athletic and band budgets no longer sum to all buses' % r_['fy'])
    if (bud[-1]['fy'], bud[-1]['school_budget'], bud[-2]['school_budget']) != (2027, x['sd27'], x['sd26']):
        fail('the FY2027 bus-budget chart no longer ends on the school-day figures its finding states')
    sp_sped = 100.0 * (bud[-1]['sped_budget'] / bud[0]['sped_budget'] - 1)
    sp_reg = 100.0 * (bud[-1]['regular_budget'] / bud[0]['regular_budget'] - 1)
    if not sp_sped > sp_reg:
        fail('special education buses no longer rose faster than regular routes, which the '
             'bus-budget page says')
    out['fy2027-bus-budget'] = TP.page(
        'fy2027-bus-budget',
        'School-day buses rise %s in %s; the total shows %s because athletic buses were cut.'
        % (C.pct(x['sd_pct']), C.fy(2027), C.pct(x['all_pct'])),
        [fact['sd27'], fact['all27'], fact['cut27'],
         f('sd26', U(x['sd26']), 'school-day buses, %s budget' % C.fy(last), 'published',
           {'y': F(last)}),
         f('sd27v', U(x['sd27']), 'school-day buses, %s budget' % C.fy(2027), 'published',
           {'y': F(2027)}),
         f('sp0', U(bud[0]['sped_budget']), 'special education buses, %s budget'
           % C.fy(bud[0]['fy']), 'published', {'y': F(bud[0]['fy'])}),
         f('sp27', U(bud[-1]['sped_budget']), 'special education buses, %s budget' % C.fy(2027),
           'published', {'y': F(2027)}),
         f('rgp', P(sp_reg), 'regular routes, change over the same years', 'published')],
        [con('The %s total looks flat because athletic buses were cut, not because buses got '
             'cheaper.' % C.fy(2027), ['sd27', 'all27', 'cut27'], {'y': F(2027)}),
         con('Special education buses went from %s in %s to %s, up %s; regular routes rose %s.'
             % (C.usd(bud[0]['sped_budget']), C.fy(bud[0]['fy']), C.usd(bud[-1]['sped_budget']),
                C.pct(sp_sped), C.pct(sp_reg)), ['sp0', 'sp27', 'rgp'],
             {'a': U(bud[0]['sped_budget']), 'y': F(bud[0]['fy']), 'b': U(bud[-1]['sped_budget']),
              'p': P(sp_sped), 'q': P(sp_reg)},
             notes=[step('These are budgets voted, net of any reimbursement. Whether more '
                         'children ride, or the routes cost more, is not in them.', 'gap',
                         closes='the district’s special education transportation contracts and '
                                'rider counts, by year')])],
        chart=TP.series(
            'Bus budgets as voted, by kind',
            [C.fy(r_['fy']) for r_ in bud],
            # School-day buses are drawn as their two lines, because they do not move
            # together: special education transportation is the one that rises.
            [TP.track('Regular routes', [r_['regular_budget'] for r_ in bud], 'published', 'bar'),
             TP.track('Special education transportation', [r_['sped_budget'] for r_ in bud],
                      'published', 'bar'),
             TP.track('Athletic buses', [r_['athletic_budget'] for r_ in bud], 'published', 'bar'),
             TP.track('Band and music', [r_['band_budget'] for r_ in bud], 'published', 'bar')],
            '$', kind='bar', stacked=True,
            note='Budgets voted before each year, never spending (rule 1). %s is the balanced '
                 'budget book, with athletic buses at %s.' % (C.fy(2027), C.usd(0)),
            note_figures={'y': F(2027), 'z': U(0)}, note_allow=('rule 1',)),
        said=said('cut', 'band'),
        sources=src('budget', 'glytdbud-expense'),
        finding_figures={'a': P(x['sd_pct']), 'y': F(2027), 'b': P(x['all_pct'])})

    # ---- Athletic bus funding
    if not fb[2025]['hs_pos'] < fb[2024]['hs_pos'] / 4:
        fail('the fee fund purchase-of-service account no longer fell by more than three '
             'quarters in FY2025; the athletic-bus-funding page says it did')
    out['athletic-bus-funding'] = TP.page(
        'athletic-bus-funding',
        'From %s, athletic buses moved from player fees to the town budget, mostly taxes.'
        % C.fy(2025),
        [fact['athletic'], fact['ath24'], fact['ath-sheet'], fact['levy-share'],
         f('reclass', U(A['reclass25']), 'moved onto the town line in %s' % C.fy(2025),
           'published', {'y': F(2025)}),
         f('pos24', U(fb[2024]['hs_pos']), 'fee fund purchase of service, %s' % C.fy(2024),
           'published', {'y': F(2024)}),
         f('pos25', U(fb[2025]['hs_pos']), 'the same account, %s' % C.fy(2025), 'published',
           {'y': F(2025)})],
        [con('Athletic buses moved from player fees to the town budget, which property taxes '
             'mostly pay for.', ['athletic', 'ath24', 'ath-sheet', 'levy-share', 'reclass']),
         con('The fee fund account that carried buses fell by more than three quarters the '
             'same year.', ['pos24', 'pos25'], notes=steps('athletic-fund', 'gap'))],
        chart=TP.series(
            'Athletic buses, town line and fee fund',
            [C.fy(y) for y in sorted(fb) if y <= last],
            [TP.track('Town athletic bus line, spent',
                      [by[y]['athletic']['spent'] for y in sorted(fb) if y <= last],
                      'published', 'bar'),
             TP.track('Fee fund, purchase of service',
                      [fb[y]['hs_pos'] for y in sorted(fb) if y <= last], 'published', 'bar')],
            '$', kind='bar',
            note='Both from the town’s ledger. The fee fund account also carries officials, '
                 'uniforms and ice time; buses are not split out of it.'),
        said=said('reclass'),
        sources=src('glytdbud', 'athletic') + REVDIST,
        finding_figures={'y': F(2025)})

    # ---- FY2027 athletic bus cut
    if r['town'] + r['fund'] != r['rounded']:
        fail('the town and fee fund shares no longer sum to what was put back')
    out['fy2027-athletic-bus-cut'] = TP.page(
        'fy2027-athletic-bus-cut',
        '%s cut athletic buses from the town budget, then put %s back, most on the fee fund.'
        % (C.fy(2027), C.usd(r['rounded'])),
        [fact['cut27'], f('restored', U(r['rounded']), 'put back, August 2026', 'published',
           allow=('August 2026',)),
         f('from-town', U(r['town']), 'of it from the town', 'published'),
         f('from-fund', U(r['fund']), 'of it from the fee fund', 'published'),
         f('estimate', U(r['estimate']), 'the district’s estimate of the year’s buses',
           'published'),
         f('sched27', U(round(m['stest']['assembled']['lo'])),
           'the posted schedules, shared buses, %s prices' % C.fy(2027), 'estimate',
           {'y': F(2027)})],
        [con('Most of what was put back is on the fee fund: %s of %s.'
             % (C.usd(r['fund']), C.usd(r['rounded'])), ['from-fund', 'restored'],
             {'a': U(r['fund']), 'b': U(r['rounded'])}),
         con('The district’s %s estimate is below what the posted schedules would cost, by our '
             'estimate.' % C.usd(r['estimate']), ['estimate', 'sched27'], {'e': U(r['estimate'])},
             notes=steps('track', 'gap'))],
        chart=TP.series(
            'What was put back, against the estimates',
            ['Put back', 'District estimate', 'Posted schedules'],
            [TP.track('From the town budget', [r['town'], None, None], 'published', 'bar'),
             TP.track('From the fee fund', [r['fund'], None, None], 'published', 'bar'),
             TP.track('The district’s estimate', [None, r['estimate'], None], 'published', 'bar'),
             TP.track('Shared buses, contract prices',
                      [None, None, m['stest']['assembled']['lo']], 'estimate', 'bar')],
            '$', kind='bar', stacked=True,
            note='The last bar is ours, high school only: %s’s fall as posted, with %s’s winter '
                 'and spring, teams sharing buses, at %s contract prices.'
                 % (C.fy(2027), C.fy(2026), C.fy(2027)),
            note_figures={'y': F(2027), 'z': F(2026)}),
        said=said('restore', 'restore-vote', 'restore-why', 'waiver'),
        sources=src('athletic', 'bus-routes'),
        finding_figures={'y': F(2027), 'r': U(r['rounded'])})

    # ---- Bus cost by sport
    tr = A['track']
    teams24 = sorted(tr['teams'][2024] if 2024 in tr['teams'] else tr['teams']['2024'],
                     key=lambda t_: -t_['cost'])
    if abs(teams24[0]['cost'] - tr['it24']) > 0.01:
        fail('indoor track is no longer the top row of the FY2024 sheet')

    def team_label(t_):
        names = [re.sub(r'^(HS|MS)\s+', '', n_) for n_ in t_['sports']]
        heads = {n_.split(' - ')[0] for n_ in names}
        name = (names[0].split(' - ')[0] + ', boys and girls'
                if len(names) == 2 and len(heads) == 1 and ' - ' in names[0]
                else ' and '.join(names))
        return name + (' (MS)' if t_['level'] == 'MS' else '')
    out['bus-cost-by-sport'] = TP.page(
        'bus-cost-by-sport',
        'Track costs most on the district’s sheet: %s in %s, ahead of the next sport’s %s.'
        % (C.usd(round(tr['it24'])), C.fy(2024), C.usd(round(tr['second24']['cost']))),
        [f('track', U2(tr['it24']), 'indoor track, both teams, %s' % C.fy(2024), 'published',
           {'y': F(2024)}),
         f('football', U2(tr['second24']['cost']), 'the next sport down, %s' % C.fy(2024),
           'published', {'y': F(2024)}),
         f('soccer', U2(tr['soccer24']), 'girls’ soccer, %s' % C.fy(2024), 'published',
           {'y': F(2024)}),
         fact['ath-sheet'],
         f('sheet25', U(round(m['sports']['totals'][2025])), 'athletic buses, all payers, %s'
           % C.fy(2025), 'published', {'y': F(2025)})],
        [con('Indoor track costs most on the district’s sheet, ahead of every other sport.',
             ['track', 'football', 'soccer'], notes=steps('track', 'gap') + link1('track'))],
        chart=TP.ranking(
            'Athletic bus cost by team',
            [(team_label(t_), t_['cost']) for t_ in teams24[:TP.ROWS_MAX]], '$',
            highlight=[team_label(t_) for t_ in teams24[:1]], basis='stated',
            note='The %s most costly of %s teams on the district’s sheet, %s. Teams that shared '
                 'a row there share one here.' % (C.num(min(TP.ROWS_MAX, len(teams24))),
                                                    C.num(len(teams24)), C.fy(2024)),
            note_figures={'k': N(min(TP.ROWS_MAX, len(teams24))), 'n': N(len(teams24)),
                          'y': F(2024)}),
        said=[heard('reggie')],
        sources=src('athletic', 'sport') + SCHED,
        finding_figures={'t': U(round(tr['it24'])), 'y': F(2024),
                         'n': U(round(tr['second24']['cost']))})

    # ---- Away trips by sport
    s_ = sch[last]
    trip_rows = [dict(label=C.fy(row['fy']), cells=[
        C.num(row['away']), C.num(row['trips']), C.num(round(row['miles'])),
        C.usd(round(row['lo'])), C.usd(round(row['hi']))]) for row in reversed(m['sched']['by_fy'])]
    out['away-trips-by-sport'] = TP.page(
        'away-trips-by-sport',
        'The posted schedules list %s away games in %s, about %s bus trips by our estimate.'
        % (C.num(s_['away']), C.fy(last), C.num(s_['trips'])),
        [f('away', N(s_['away']), 'away games on the posted schedules', 'published'),
         fact['trips'],
         f('miles', N(round(s_['miles'])), 'road miles, round trips', 'estimate'),
         f('lo', U(round(s_['lo'])), 'if teams share buses, at %s prices' % C.fy(last),
           'estimate', {'y': F(last)}),
         f('hi', U(round(s_['hi'])), 'one bus per team, at %s prices' % C.fy(last),
           'estimate', {'y': F(last)}),
         fact['mile'], fact['hour']],
        [con('At contract prices the scheduled trips would cost %s to %s, by our estimate.'
             % (C.usd(round(s_['lo'])), C.usd(round(s_['hi']))), ['lo', 'hi', 'mile', 'hour'],
             {'a': U(round(s_['lo'])), 'b': U(round(s_['hi']))},
             notes=steps('track', 'gap'))],
        chart=TP.series(
            'Away games and bus trips by year',
            [C.fy(row['fy']) for row in m['sched']['by_fy'] if row['fy'] <= last],
            [TP.track('Away games, posted schedules',
                      [row['away'] for row in m['sched']['by_fy'] if row['fy'] <= last],
                      'published', 'bar'),
             TP.track('Bus trips', [row['trips'] for row in m['sched']['by_fy'] if row['fy'] <= last],
                      'estimate', 'bar')],
            'count', kind='bar',
            note='Trips are ours: one bus a date and venue, shared by every Lunenburg team '
                 'there. %s is left off; the year is not over.' % C.fy(2027), note_figures={'y': F(2027)}),
        table=dict(caption='Away games and bus trips by year', views=[dict(
            key='trips', label='From the posted schedules', total_col=4,
            kinds=['ledger', 'stated', 'stated', 'stated', 'stated'],
            columns=['Away games', 'Bus trips (our estimate)', 'Miles (our estimate)',
                     'Shared buses (our estimate)', 'Bus per team (our estimate)'],
            rows=trip_rows,
            note='Games are scheduled, not played, for the teams ArbiterLive lists. Every '
                 'cost is our estimate at FY2026 contract prices.')]),
        sources=SCHED + src('dee-bus-bid'),
        finding_figures={'a': N(s_['away']), 'y': F(last), 't': N(s_['trips'])})
    return out


def A_rate(m, cat):
    """A line's compound annual rate, spent to spent, FY2019 to the last closed year -- the
    same base the trend chain uses (FY2019, the last year before the 2020 closures)."""
    by = {r['fy']: r for r in m['ledger']}
    last = m['last']
    return round(100 * ((by[last][cat]['spent'] / by[2019][cat]['spent']) ** (1 / (last - 2019)) - 1), 1)


if __name__ == '__main__':
    sys.exit(main())
