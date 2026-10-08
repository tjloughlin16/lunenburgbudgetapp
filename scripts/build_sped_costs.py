#!/usr/bin/env python3
"""Special education: what a bad year has cost, and what a reserve for one would have needed.

    python3 scripts/build_sped_costs.py           # write the payload, the markdown, the charts
    python3 scripts/build_sped_costs.py --check   # fail if any output no longer reproduces

THE QUESTION, TJ's, 8 October 2026: *"how much would be wise to have to spend for
surprises mid-year for in and out of district tuition?"* -- after asking for "a report on
in district and out of district special education costs. Trend data if we have it,
averages for each, and combined average", and then: *"Ideally, the report includes being
able to understand how many people come in or leave mid-year."*

So the report opens with the SURPRISE, measured, and everything else -- the trend, the
averages, the counts of children -- is the evidence underneath it.

WHAT "A SURPRISE" IS HERE, and why comparing a budget to an actual is allowed in this one
report. Rule 1 forbids mixing budgets and actuals in ONE CALCULATION THAT PROJECTS OR
MEASURES GROWTH, because a rate measured from an actual to a budget is part growth and part
the step between the two. Here the step between the two IS the quantity: how far spending
at the close of a year landed from the budget voted before it began. Nothing below grows a
budget from an actual, and nothing here feeds the model.

THE LEDGER, IN TWO PIECES, and which one is proof (rule 13a):

  FY2023-FY2026   the Town's MUNIS year-end (period 13) reports for the school general
                  fund AND the school special funds -- printouts from the accounting
                  system, published after review (`redactions.csv`).
  FY2010-FY2022   the Finance Committee's general fund history workbook -- per-year MUNIS
                  exports pasted side by side by a person. `stated`, not proof. Its school
                  rows are CHECKED here against the MUNIS reports for the two years both
                  cover in full, FY2023 and FY2024, and the build refuses if they differ.
                  Its FY2025 column is partial (`actual_is_partial`) and is never used.

WHICH ACCOUNTS ARE SPECIAL EDUCATION -- OURS, and the classification is stated where it is
used. The account string's fourth segment is the function code; its fifth segment is `51`
on every general fund school account whose own description names special education
(asserted below, not assumed) except special education transportation, which sits under
the transportation programme. So:

    out-of-district tuition   functions 9100, 9300, 9400 with segment 51
    transportation            the account the Town names SPECIAL ED TRANSPORTATION
    in district               every other segment-51 account, LESS the two accounts the
                              district's own budget book labels as English Language
                              Learner costs (sped-and-the-curve.md drew the same line)

That `51` means "special education" is an inference from the labels, not a published
chart of accounts, and it is registered as a gap.

WHAT THIS SCRIPT REFUSES TO DO:

  * net the circuit breaker into anything. It is a separate column everywhere.
  * call a dollar-per-child figure what a placement costs. It is labelled OUR ESTIMATE
    every time it appears, because it is a net ledger total divided by a headcount taken
    on a single day (rule 7: a proxy is never the thing). /what-special-education-costs
    refuses to compute it at all; this report computes it because TJ asked for averages
    per child, and says on its face what that refusal was protecting against.
  * read DESE's caseload-movement file as placements. It counts children entering and
    leaving SERVICES, and says nothing about where they were taught.
"""
import argparse
import csv
import html
import json
import os
import re
import sqlite3
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conclusions as C  # noqa: E402
from conclusions import conclusion, emit, figure  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ID = 'special-education-costs'
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
GL = os.path.join(ROOT, 'sources', 'data', 'gl-history.csv')
MUNIS = os.path.join(ROOT, 'sources', 'data', 'munis-school-ytd.csv')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
Q3 = os.path.join(ROOT, 'sources', 'data', 'school-special-revenue-fy26-q3.csv')
SRR = os.path.join(ROOT, 'sources', 'data', 'special-revenue-read.csv')
CB_FUND_NAME = '50/50 Grant Sped Tuitions'   # fund 2640 as the annual report names it
OUT_MD = os.path.join(ROOT, 'sources', 'analyses', ID + '.md')
OUT_JSON = os.path.join(ROOT, 'fy28', 'public', 'data', ID + '.json')
CHART_DIR = os.path.join(ROOT, 'sources', 'analyses', 'charts')
LEA = '01620000'

# The two segment-51 accounts the district's FY27 budget workbook labels as English
# Language Learner costs -- "District Wide Specials (ELL)" and "ELL General Supplies".
# Tied below, by amount, to `lps_budget_lines` for FY2026, so a renumbering fails loudly.
ELL = {
    '0100-3-300-2310-51-0-06-1-511001': 'District Wide Specials (ELL)',
    '0100-3-300-2110-51-0-04-2-545001': 'ELL General Supplies',
}
OOD_FUNCS = ('9100', '9300', '9400')
TRANSPORT = re.compile(r'^SPECIAL ED(UCATION)? TRANSPORTATION$', re.I)
SPED_LABEL = re.compile(r'\bSPED\b|SPEC\.? ?ED\b|SPECIAL ED', re.I)
GROUPS = ('ood', 'indist', 'trans')
NAMES = {'ood': 'Out-of-district tuition', 'indist': 'In-district special education',
         'trans': 'Special education transportation'}

# WHAT WAS SAID, rule 15a. Every quote is re-read from the archive on each run, whitespace
# collapsed, and a miss is fatal. Statements of intent and of belief -- never counts.
QUOTES = [
    dict(key='april', path='sources/meetings/text/school-committee/2024-02-28-minutes-6439.txt',
         board='School Committee', date='2024-02-28',
         quote='April 1st is the deadline, if a student enters the district before this date '
               'our school incurs the cost, if it is after this date the sending school '
               'assumes the expense for the rest of the year and the following year',
         why='The district’s account of when a child who moves in becomes Lunenburg’s '
             'cost. It is a statement at a meeting, not the regulation, and nothing in this '
             'archive holds the rule itself; if it holds, a placement arriving after 1 April '
             'does not reach this budget until the year after next.'),
    dict(key='nine', path='sources/meetings/text/school-committee/2024-02-28-minutes-6439.txt',
         board='School Committee', date='2024-02-28',
         quote='we currently have 9 out of district stud ents and next year we will have 9',
         why='Said in February 2024, a few days before the town’s own 1 March count '
             'for the same year, which is in the table above. The broken word is what the '
             'extracted minutes render to.'),
    dict(key='skyrocket', path='sources/meetings/text/school-committee/2024-01-24-minutes-6375.txt',
         board='School Committee', date='2024-01-24',
         quote='Our out of District placements have skyrocketed',
         why='Said in the middle of FY2024 — one of the years the tuition line ran over '
             'the budget voted for it, and the year it ran furthest over counting the '
             'circuit breaker account. The count of children placed barely moved that year; '
             'the dollars did. Dollars are not children.'),
    dict(key='fourteen', path='sources/meetings/text/school-committee/2024-02-28-minutes-6439.txt',
         board='School Committee', date='2024-02-28',
         quote='Ms. Brzozoski regarding the 14% increase in tuition, when did we find out '
               'about this?',
         why='A second route to a surprise that no count of children shows: the price of a '
             'place rising after the budget is built. The minutes record the question and '
             'not the answer, and which tuition the rise applied to is not stated.'),
    dict(key='carryover', path='sources/meetings/text/finance-committee/2024-03-14-minutes-6469.txt',
         board='Finance Committee', date='2024-03-14',
         quote='Dave Passion questions how the 14% increase was absorbed last year. Julianna '
               'Hanscom states it is probably absorbed with a lot of the carry over for the '
               'circuit breaker monies and that’s why that account has gone down.',
         why='The district’s own account, as minuted in March 2024, of the circuit breaker '
             'balance being drawn down to absorb a tuition rise. “Probably” is in the minutes: '
             'a belief stated at a meeting, not a measurement.'),
    dict(key='radar', path='sources/meetings/text/school-committee/2026-02-04-minutes-7634.txt',
         board='School Committee', date='2026-02-04',
         quote='we currently have students on our radar that may require out of district '
               'placement and we have also had students move into the district that require '
               'out of district placements',
         why='Mid-year arrivals, named in the middle of FY2026. Evidence that it happens; '
             'not a count of how often.'),
    dict(key='nineteen', path='sources/meetings/text/school-committee/2026-08-26-minutes-7980.txt',
         board='School Committee', date='2026-08-26',
         quote='The administration reported that 19 out-of-district placements were then '
               'anticipated.',
         why='An anticipated count for FY2027, as minuted. It is a forecast reported at a '
             'meeting, not a census taken on any date, and it is set beside the town’s '
             'own counts in the reserve section.'),
    dict(key='establish', path='sources/meetings/text/select-board/2025-10-07-minutes-7441.txt',
         board='Select Board', date='2025-10-07',
         quote='The fund requires a majority vote of both the School Committee and the Select '
               'Board to expend. The total balance cannot exceed 2% of annual net school '
               'spending.',
         why='The Town Manager’s description of the reserve, as minuted. The statute '
             'itself is not in this archive, so the cap used below is the cap as described.'),
    dict(key='urgency', path='sources/meetings/text/select-board/2025-10-21-minutes-7466.txt',
         board='Select Board', date='2025-10-21',
         quote='Member McLeod expressed lingering concern about potential budget impacts if '
               'the reserve were to reduce urgency around special education line-item funding.',
         why='The argument against, on the record: that a reserve can become a reason to '
             'budget the line itself short. The voted line is measured on this page against '
             'what was spent, every year back to FY2010, so whether that happens will be '
             'visible in the years after the reserve is funded.'),
]
TOWN_MEETING = dict(
    path='sources/town-annual-reports/text/4130-fy-2025-annual-town-report.txt',
    heading='SPECIAL TOWN MEETING November 18, 2025',
    quote='VOTED (Yes 65, No 24, Abstain 1) to accept the provisions of MGL Chapter 40, '
          'Section 13E, to establish a Special Education Reserve Fund to be utilized in the '
          'upcoming fiscal years, to pay, without further appropriation, for unanticipated or '
          'unbudgeted costs of special education and recovery high school programs, '
          'out-of-district tuition or transportation.',
    fincom='Finance Committee Recommends Disapproval.')
AGENDA = dict(path='sources/meetings/text/school-committee/2026-10-07-agenda-8058.txt',
              quote='Vote an Amount to Fund the Special Education Reserve Fund Approved at '
                    'November 2026 Town Meeting')

# WHAT WAS SAID ABOUT THE SIZE OF THE RESERVE, autumn 2026. The town has not yet published
# minutes for these meetings, so the only record in this archive is the machine captions of
# the recordings -- OURS, derived, and a FINDING AID: a caption model hears "fifteen
# hundred", "$1,500" and "$50" alike. Each is re-found verbatim in the caption file on every
# build, its timestamp computed, and it is cited as THE VIDEO AT THAT MOMENT, never as a
# record. A figure in one is what the captions render, to be checked against the video.
SC = 'sources/data/youtube-transcripts/school-committee/'
CAPTIONS = [
    dict(key='overages', file=SC + '2026-10-07-kPZcnFd5COw.json', board='School Committee',
         date='2026-10-07',
         quote='if our overages were almost $600,000 this year, we should put some more money away'),
    dict(key='one', file=SC + '2026-10-07-kPZcnFd5COw.json', board='School Committee',
         date='2026-10-07', quote='So 300,000 out of district possibly.'),
    dict(key='average', file=SC + '2026-10-07-kPZcnFd5COw.json', board='School Committee',
         date='2026-10-07',
         quote='the average price of 150,000 per child, which is just an average, not the '
               'exact amount'),
    dict(key='fifteen', file=SC + '2026-10-07-kPZcnFd5COw.json', board='School Committee',
         date='2026-10-07',
         quote='if we have 15 outofd district placements at the end by the end of this year, '
               'we\'re talking about spending about 2,250,000 on out of district placements'),
    dict(key='motion', file=SC + '2026-10-07-kPZcnFd5COw.json', board='School Committee',
         date='2026-10-07',
         quote='We\'re going to request $300,000 in free cash if the free cash is certified at '
               'the November town meeting'),
    dict(key='range', file=SC + '2025-11-19-6PZ-J-oIAkQ.json', board='School Committee',
         date='2025-11-19', quote='they\'re probably ranging between 3 and 800,000 right now'),
]

# HOW THE CIRCUIT BREAKER WORKS, in the district's own words. The statute (M.G.L. c.71B
# s.5A) is not in this archive; this presentation to the School Committee is, and every
# line of the mechanism the report states is quoted from it and re-read on every build.
# It is the district's DESCRIPTION of the programme, and the report says so each time.
CB_DOC = 'sources/district-budget/text/sc-meetings/2023-2024-circuit-breaker-presentation.txt'
CB_PDF = 'district-budget/docs/sc-meetings/2023-2024-circuit-breaker-presentation.pdf'
CB_QUOTES = dict(
    threshold='four times the state average foundation budget per pupil (as calculated under '
              'the chapter 70 program). For FY24, the threshold is $51,721',
    share='the state reimburses approximately 75 percent of the costs above that threshold '
          '(however it has been as low as 40%).',
    eligible='In-District as well as Out–of-District costs are eligible.',
    prior='Circuit breaker reimbursements are for the district\'s prior year\'s expenses.',
    first='September: receive 1st quarterly reimbursement payment',
    last='June: receive 4th quarterly reimbursement payment',
    account='Circuit breaker reimbursements should be deposited into a special education '
            'reimbursement account.',
    spend='These funds may be expended by the school committee in the year received or in '
          'the following',
    vote='for any special education- related purposes, without further appropriation.',
    plan='the appropriating authority can and should consider the projected reimbursements',
)


def fail(msg):
    raise SystemExit('build_sped_costs: %s. Nothing written.' % msg)


def squash(s):
    return re.sub(r'\s+', ' ', s)


def text_of(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        fail('%s is not here -- a quote is attributed to a document not in the archive' % rel)
    return squash(open(p, encoding='utf-8', errors='replace').read())


def segs(acct):
    p = acct.split('-')
    if len(p) < 9:
        fail('account %r does not have nine segments' % acct)
    return p


def group_of(acct, desc):
    p = segs(acct)
    if p[0] != '0100':
        return None
    if TRANSPORT.match(desc.strip()):
        return 'trans'
    if p[4] != '51':
        return None
    if acct in ELL:
        return 'ell'
    if p[3] in OOD_FUNCS:
        return 'ood'
    return 'indist'


def num(x):
    return float(x) if x not in (None, '') else 0.0


# ------------------------------------------------------------------------- the ledger

def load_ledger():
    """Every special education general fund account, by year, from the two ledgers."""
    munis = list(csv.DictReader(open(MUNIS, encoding='utf-8')))
    # THE CLASSIFICATION, ASSERTED. Every general fund school account whose own name says
    # special education must be in segment 51 or be the transportation account.
    stray = sorted({(r['account'], r['description']) for r in munis
                    if r['type'] == 'E' and r['account'].startswith('0100-')
                    and SPED_LABEL.search(r['description'])
                    and segs(r['account'])[4] != '51'
                    and not TRANSPORT.match(r['description'].strip())})
    if stray:
        fail('special education accounts outside segment 51: %s' % stray)

    ml = {}   # (fy, group) -> [original, revised, spent]
    cb = {}   # fy -> dict of fund 2640 figures
    for r in munis:
        fy = int(r['fiscal_year'])
        if r['period'] != '13':
            continue
        fund = segs(r['account'])[0]
        if fund == '2640':
            d = cb.setdefault(fy, {'tuition': 0.0, 'other': 0.0, 'receipts': 0.0})
            if r['type'] == 'R':
                d['receipts'] += -num(r['ytd_expended'])
            elif segs(r['account'])[3] in OOD_FUNCS:
                d['tuition'] += num(r['ytd_expended']) + num(r['encumbrances'])
            else:
                d['other'] += num(r['ytd_expended']) + num(r['encumbrances'])
            continue
        if r['type'] != 'E':
            continue
        g = group_of(r['account'], r['description'])
        if not g:
            continue
        a = ml.setdefault((fy, g), [0.0, 0.0, 0.0])
        a[0] += num(r['original_approp'])
        a[1] += num(r['revised_budget'])
        a[2] += num(r['ytd_expended']) + num(r['encumbrances'])
    m_years = sorted({fy for fy, _ in ml})
    if m_years != [2023, 2024, 2025, 2026]:
        fail('the MUNIS year-end reports cover %s, not FY2023-FY2026' % m_years)

    gl = {}
    partial = set()
    for r in csv.DictReader(open(GL, encoding='utf-8')):
        if r['sheet'] != 'general_fund' or r['department_code'] != '300':
            continue
        g = group_of(r['account'], r['org_desc'])
        if not g:
            continue
        fy = int(r['fiscal_year'])
        if r['actual_is_partial'] == 'true':
            partial.add(fy)
        a = gl.setdefault((fy, g), [0.0, 0.0, 0.0])
        a[0] += num(r['original'])
        a[1] += num(r['revised'])
        a[2] += num(r['actual'])

    # THE TIE. The assembled workbook is used for FY2010-FY2022 only because it matches
    # the accounting system's own reports, to the dollar, in every year both hold whole.
    tie_years = sorted({fy for fy, _ in gl} & set(m_years) - partial)
    if len(tie_years) < 2:
        fail('fewer than two years to tie the assembled workbook to MUNIS: %s' % tie_years)
    for fy in tie_years:
        for g in GROUPS + ('ell',):
            a, b = gl.get((fy, g), [0, 0, 0]), ml.get((fy, g), [0, 0, 0])
            if abs(round(a[0]) - round(b[0])) > 1 or abs(round(a[2]) - round(b[2])) > 1:
                fail('FY%d %s: the Finance Committee workbook (%s / %s) does not tie to the '
                     'MUNIS year-end report (%s / %s)' % (fy, g, a[0], a[2], b[0], b[2]))

    rows = []
    first_gl = min(fy for fy, _ in gl)
    for fy in range(first_gl, max(m_years) + 1):
        src = 'munis' if fy in m_years else 'fincom'
        book = ml if src == 'munis' else gl
        if fy in partial and src == 'fincom':
            fail('FY%d would be read from a partial column' % fy)
        row = dict(fy=fy, source=src)
        for g in GROUPS:
            o, rv, s = book.get((fy, g), [0.0, 0.0, 0.0])
            if not o and not s:
                fail('FY%d has no %s accounts at all -- a join that matches nothing' % (fy, g))
            row[g] = dict(original=round(o), revised=round(rv), spent=round(s),
                          variance=round(s) - round(o),
                          variance_pct=round(100.0 * (round(s) - round(o)) / round(o), 1))
        rows.append(row)
    return rows, cb, tie_years, sorted(partial)


def ell_tie(db):
    """The two ELL accounts, matched by FY2026 amount to the budget book's ELL lines."""
    book = dict(db.execute("SELECT line_item, fy26_final FROM lps_budget_lines WHERE "
                           "line_item IN ('District Wide Specials (ELL)','ELL General Supplies')"
                           ).fetchall())
    led = {}
    for r in csv.DictReader(open(MUNIS, encoding='utf-8')):
        if r['fiscal_year'] == '2026' and r['account'] in ELL:
            led[ELL[r['account']]] = num(r['original_approp'])
    for name in ELL.values():
        if name not in book or name not in led or abs(num(book[name]) - led[name]) > 1:
            fail('the ELL account %r no longer ties to the budget book (%s vs %s)'
                 % (name, book.get(name), led.get(name)))
    return {k: round(v) for k, v in led.items()}


# --------------------------------------------------------------------- the rest of it

def load_state(db):
    dese = {}
    for fy, code, g, gr, t in db.execute(
            "SELECT fy, func_code, gen_fund, grants_revolving, total FROM "
            "dese_function_expenditure WHERE lea=? AND level='detail' AND func_code IN "
            "('9300','9400') ORDER BY fy", (LEA,)):
        d = dese.setdefault(fy, {'gen_fund': 0.0, 'other_funds': 0.0, 'all_funds': 0.0})
        d['gen_fund'] += g or 0
        d['other_funds'] += gr or 0
        d['all_funds'] += t or 0
    if len(dese) < 15:
        fail('DESE out-of-district tuition came back with %d years' % len(dese))
    func = {}
    for fy, code, t in db.execute(
            "SELECT fy, func_code, total FROM dese_function_expenditure WHERE lea=? AND "
            "level='detail' AND func_code IN ('9300','9400')", (LEA,)):
        func.setdefault(fy, {})[code] = t or 0
    breaker = {fy: dict(paid=round(p or 0), tuition=round(t or 0), transport=round(tr or 0),
                        students=int(s or 0))
               for fy, p, t, tr, s in db.execute(
                   "SELECT fy, total_quarterly_payment, reimb_instruction_tuition, "
                   "reimb_transport, eligible_students_claimed FROM dese_circuit_breaker "
                   "WHERE lea=? AND level='district' ORDER BY fy", (LEA,))}
    if len(breaker) < 18:
        fail('the circuit breaker schedule came back with %d years' % len(breaker))
    placed = {}
    for fy, tot, col, day, res, src in db.execute(
            "SELECT fy, total, collaborative, day, residential, document FROM placement_counts "
            "ORDER BY fy"):
        placed[int(fy)] = dict(total=int(tot), collaborative=col, day=day, residential=res,
                               source=src)
    if len(placed) < 14:
        fail('the placement counts came back with %d years' % len(placed))
    sped = {}
    for fy, ind, cnt in db.execute(
            "SELECT fy, indicator, measure_cnt FROM dese_sped_program WHERE lea=? AND "
            "geo_level='district' AND indicator_category='In District/Out of District'",
            (LEA,)):
        sped.setdefault(fy, {})[{'In-District': 'in_district', 'Out-of-District':
                                  'out_of_district', 'Total Students with Disabilities':
                                  'total'}[ind]] = int(cnt)
    for fy, d in sped.items():
        if d['in_district'] + d['out_of_district'] != d['total']:
            fail('DESE FY%d: in plus out of district does not equal its own total' % fy)
    move = [dict(fy=fy, on_iep=int(i), moved_in=int(mi), moved_out=int(mo),
                 repeats_prior_year=rp == 'yes')
            for fy, i, mi, mo, rp in db.execute(
                "SELECT fy, on_iep_cnt, moved_in_cnt, moved_out_cnt, repeats_prior_year FROM "
                "dese_sped_movement WHERE lea=? AND geo_level='district' AND grades='K-12' "
                "ORDER BY fy", (LEA,))]
    if len(move) < 6:
        fail('the caseload movement rows came back with %d years' % len(move))
    nss = {fy: dict(nss=round(n), stage=st) for fy, n, st in db.execute(
        "SELECT fy, net_school_spending, nss_stage FROM dese_ch70_formula WHERE lea=? AND "
        "net_school_spending IS NOT NULL ORDER BY fy", (LEA,))}
    return dese, breaker, placed, sped, move, nss, func


def said():
    out = []
    for q in QUOTES:
        if squash(q['quote']) not in text_of(q['path']):
            fail('the quote attributed to %s %s is no longer in %s' % (q['board'], q['date'],
                                                                    q['path']))
        out.append(dict(key=q['key'], board=q['board'], date=q['date'], quote=q['quote'],
                        why=q['why'], cite='/docs/' + q['path'][len('sources/'):]))
    tm = text_of(TOWN_MEETING['path'])
    for k in ('heading', 'quote', 'fincom'):
        if squash(TOWN_MEETING[k]) not in tm:
            fail('the Town Meeting vote is no longer in the FY2025 annual report as quoted (%s)' % k)
    if squash(AGENDA['quote']) not in text_of(AGENDA['path']):
        fail('the School Committee agenda item is no longer as quoted')
    cbt = text_of(CB_DOC)
    for k, q in CB_QUOTES.items():
        if squash(q) not in cbt:
            fail('the circuit breaker presentation no longer says %r (%s)' % (q, k))
    m = re.search(r'Yes (\d+), No (\d+), Abstain (\d+)', TOWN_MEETING['quote'])
    vote = dict(yes=int(m.group(1)), no=int(m.group(2)), abstain=int(m.group(3)),
                date='2025-11-18', cite='/docs/' + TOWN_MEETING['path'][len('sources/'):],
                quote=TOWN_MEETING['quote'])
    caps = []
    for c in CAPTIONS:
        j = json.load(open(os.path.join(ROOT, c['file']), encoding='utf-8'))
        txt, at = '', []
        for seg in j['segments']:
            at.append((len(txt), seg['start']))
            txt += seg['text'] + ' '
        txt = squash(txt)
        # positions shift under squash only where whitespace collapses; re-find on the
        # squashed string and map back by counting segments up to that point instead.
        k = txt.find(squash(c['quote']))
        if k < 0:
            fail('the caption %r is no longer in %s' % (c['quote'], c['file']))
        n, acc = 0, ''
        for seg in j['segments']:
            nxt = squash(acc + seg['text'] + ' ')
            if len(nxt) > k:
                break
            acc, n = nxt, n + 1
        t = int(j['segments'][min(n, len(j['segments']) - 1)]['start'])
        caps.append(dict(key=c['key'], board=c['board'], date=c['date'], quote=c['quote'],
                         seconds=t, at='%d:%02d:%02d' % (t // 3600, t % 3600 // 60, t % 60),
                         cite='%s&t=%ds' % (j['video_url'], t)))
    return out, vote, caps


def med(xs):
    return statistics.median(xs)


def measure():
    db = sqlite3.connect(DB)
    ledger, cb2640, tie_years, partial = load_ledger()
    ell = ell_tie(db)
    dese, breaker, placed, sped, move, nss, func = load_state(db)
    quotes, vote, captions = said()

    first, last = ledger[0]['fy'], ledger[-1]['fy']
    n_years = len(ledger)
    munis_first = min(r['fy'] for r in ledger if r['source'] == 'munis')

    # ---- the surprise, by line group, against the budget VOTED before the year began
    per = {}
    for g in GROUPS:
        v = [(r['fy'], r[g]['variance'], r[g]['variance_pct']) for r in ledger]
        over = [x for x in v if x[1] > 0]
        worst = max(v, key=lambda x: x[1])
        worst_pct = max(v, key=lambda x: x[2])
        per[g] = dict(
            years_over=len(over), years=len(v), worst_fy=worst[0], worst=worst[1],
            worst_pct=worst[2], worst_pct_fy=worst_pct[0], worst_pct_value=worst_pct[2],
            median_variance=round(med([x[1] for x in v])),
            median_overrun=round(med([x[1] for x in over])) if over else 0,
            best_fy=min(v, key=lambda x: x[1])[0], best=min(v, key=lambda x: x[1])[1],
            avg_spent=round(statistics.mean(r[g]['spent'] for r in ledger)),
            avg_spent_recent=round(statistics.mean(r[g]['spent'] for r in ledger[-5:])),
            spent_first=ledger[0][g]['spent'], spent_last=ledger[-1][g]['spent'])

    # The reserve a year would have needed: each line's overrun, not netted against any
    # other line's underspend -- a reserve exists so the overrun need not be found elsewhere.
    need = []
    for r in ledger:
        gross = sum(max(0, r[g]['variance']) for g in GROUPS)
        net = sum(r[g]['variance'] for g in GROUPS)
        tuition_transport = sum(max(0, r[g]['variance']) for g in ('ood', 'trans'))
        need.append(dict(fy=r['fy'], gross=gross, net=net, tuition_transport=tuition_transport))
    worst_need = max(need, key=lambda x: x['gross'])
    years_needing = [x for x in need if x['gross'] > 0]
    med_need = round(med([x['gross'] for x in need]))
    recent = [x for x in need if x['fy'] >= munis_first]
    worst_recent = max(recent, key=lambda x: x['gross'])

    # ---- every fund, the four closed years the accounting system prints in full
    allfunds = []
    for r in ledger:
        if r['source'] != 'munis':
            continue
        c = cb2640.get(r['fy'], {'tuition': 0.0, 'other': 0.0, 'receipts': 0.0})
        tot = r['ood']['spent'] + round(c['tuition'])
        allfunds.append(dict(fy=r['fy'], gf_original=r['ood']['original'],
                             gf_spent=r['ood']['spent'], cb_fund_spent=round(c['tuition']),
                             cb_fund_other=round(c['other']), cb_fund_receipts=round(c['receipts']),
                             all_spent=tot, above_voted=tot - r['ood']['original'],
                             above_voted_pct=round(100.0 * (tot - r['ood']['original'])
                                                   / r['ood']['original'], 1),
                             dese_paid=breaker.get(r['fy'], {}).get('paid')))
    worst_all = max(allfunds, key=lambda x: x['above_voted'])
    # The ledger's receipts against the state's payment schedule. They do not agree year by
    # year; find the consecutive pairs whose SUM agrees, which is a timing difference rather
    # than a missing payment.
    pairs = []
    for a, b in zip(allfunds, allfunds[1:]):
        if a['dese_paid'] is None or b['dese_paid'] is None:
            continue
        if a['cb_fund_receipts'] + b['cb_fund_receipts'] == a['dese_paid'] + b['dese_paid'] \
                and a['cb_fund_receipts'] != a['dese_paid']:
            pairs.append(dict(fy_a=a['fy'], fy_b=b['fy'], total=a['dese_paid'] + b['dese_paid'],
                              shifted=a['dese_paid'] - a['cb_fund_receipts']))
    receipts_tie = [x['fy'] for x in allfunds if x['dese_paid'] == x['cb_fund_receipts']]

    # ---- WHO PAID THE TUITION, and the circuit breaker beside it. One row per spending
    # year. The total is DESE's End of Year Financial Report (functions 9300 + 9400, every
    # fund) wherever DESE has published the year; the town's year-end report splits the
    # part DESE calls "other funds" into the circuit breaker account (fund 2640) and the
    # rest, for the years it covers. FY2026 is not yet in DESE's file, so for it only the
    # town's two funds are shown and the remainder is NOT ESTABLISHED, never zero.
    af = {x['fy']: x for x in allfunds}
    who = []
    for fy in range(first, last + 1):
        d, b, nb = dese.get(fy), breaker.get(fy), breaker.get(fy + 1)
        row = dict(fy=fy, received=b['paid'] if b else None,
                   earned=nb['paid'] if nb else None,
                   gf=None, cb_account=None, other=None, other_unsplit=None, total=None)
        if d:
            gf, oth = round(d['gen_fund']), round(d['other_funds'])
            row.update(gf=gf, total=gf + oth)
            if fy in af:
                # THE TIE that lets two sources sit in one stack: DESE's general fund
                # figure and the town's ledger must be the same dollars.
                if abs(gf - af[fy]['gf_spent']) > 1:
                    fail('FY%d: DESE general fund tuition %s does not tie to the town ledger %s'
                         % (fy, gf, af[fy]['gf_spent']))
                cba = af[fy]['cb_fund_spent']
                if cba > oth + 1:
                    fail('FY%d: the circuit breaker account paid more tuition (%s) than DESE '
                         'reports from every non-general fund (%s)' % (fy, cba, oth))
                row.update(cb_account=cba, other=max(0, oth - cba), basis='dese+munis')
            else:
                row.update(other_unsplit=oth, basis='dese')
        elif fy in af:
            row.update(gf=af[fy]['gf_spent'], cb_account=af[fy]['cb_fund_spent'],
                       basis='munis')
        else:
            continue
        who.append(row)
    if len(who) < 15:
        fail('the who-paid series came back with %d years' % len(who))
    split = [r for r in who if r['basis'] == 'dese+munis']
    big_other = max(split, key=lambda r: r['other'])
    cb_last = max(breaker)
    cb_now = dict(fy=cb_last, paid=breaker[cb_last]['paid'], for_fy=cb_last - 1,
                  ledger_received=af.get(cb_last, {}).get('cb_fund_receipts'))
    # The decomposition of the worst every-fund year, which the conclusion states.
    wa = max(allfunds, key=lambda x: x['above_voted'])
    gf_over = wa['gf_spent'] - wa['gf_original']
    if gf_over + wa['cb_fund_spent'] != wa['above_voted']:
        fail('the every-fund overrun does not decompose into the general fund overrun plus '
             'the circuit breaker account')
    gf_need_that_year = next(x for x in need if x['fy'] == wa['fy'])['gross']

    # ---- the trend, on one basis per series
    trend = []
    by = {r['fy']: r for r in ledger}
    for fy in range(min(min(dese), first), last + 1):
        r = by.get(fy)
        d = dese.get(fy)
        b = breaker.get(fy)
        trend.append(dict(
            fy=fy,
            indist_spent=r['indist']['spent'] if r else None,
            ood_gf_spent=r['ood']['spent'] if r else None,
            trans_spent=r['trans']['spent'] if r else None,
            ood_all_funds=round(d['all_funds']) if d else None,
            ood_dese_gen_fund=round(d['gen_fund']) if d else None,
            cb_paid=b['paid'] if b else None))
    dese_years = sorted(dese)
    ood_all_avg = round(statistics.mean(dese[y]['all_funds'] for y in dese_years))
    ood_all_avg_recent = round(statistics.mean(dese[y]['all_funds'] for y in dese_years[-5:]))
    combined = [r['indist']['spent'] + r['ood']['spent'] for r in ledger]
    combined_avg = round(statistics.mean(combined))
    combined_avg_recent = round(statistics.mean(combined[-5:]))
    ood_share = [round(100.0 * r['ood']['spent'] / (r['indist']['spent'] + r['ood']['spent']), 1)
                 for r in ledger]
    cb_years = [y for y in dese_years if y in breaker]
    cb_avg = round(statistics.mean(breaker[y]['paid'] for y in cb_years))

    # ---- OUR ESTIMATE: dollars per child. Labelled every time.
    per_placed = []
    for fy in sorted(placed):
        if fy in dese:
            per_placed.append(dict(fy=fy, children=placed[fy]['total'],
                                   all_funds=round(dese[fy]['all_funds']),
                                   per_child=round(dese[fy]['all_funds'] / placed[fy]['total'])))
    pp_med = round(med([x['per_child'] for x in per_placed]))
    pp_last = per_placed[-1]
    pp_recent = per_placed[-4:]
    pp_recent_med = round(med([x['per_child'] for x in pp_recent]))
    per_served = []
    for fy in sorted(sped):
        if fy in by:
            r = by[fy]
            per_served.append(dict(
                fy=fy, in_district_children=sped[fy]['in_district'],
                all_children=sped[fy]['total'], indist_spent=r['indist']['spent'],
                per_child_in_district=round(r['indist']['spent'] / sped[fy]['in_district']),
                combined_gf=r['indist']['spent'] + r['ood']['spent'],
                per_child_combined=round((r['indist']['spent'] + r['ood']['spent'])
                                         / sped[fy]['total'])))

    # ---- movement: two counts a few months apart, and the year-to-year step
    snap = []
    for fy in sorted(sped):
        if fy in placed:
            snap.append(dict(fy=fy, october=sped[fy]['out_of_district'],
                             march=placed[fy]['total'],
                             net=placed[fy]['total'] - sped[fy]['out_of_district']))
    biggest_mid = max(snap, key=lambda x: x['net'])
    yoy = []
    ys = sorted(placed)
    for a, b in zip(ys, ys[1:]):
        yoy.append(dict(fy=b, change=placed[b]['total'] - placed[a]['total']))
    biggest_yoy = max(yoy, key=lambda x: x['change'])
    recent_yoy = [x for x in yoy if x['fy'] >= pp_recent[0]['fy']]
    biggest_recent_yoy = max(recent_yoy, key=lambda x: x['change'])

    # ---- TWO BASES FOR A BAD YEAR, the four closed years the ledger prints in full.
    # AFTER the circuit breaker account: `need`, above -- what exceeded BOTH sources.
    # BEFORE it: the same rule, with the account's tuition spending put back on the
    # tuition line. The account pays tuition EVERY year, overrun or not (asserted below),
    # so this counts routine spending as surprise. It is an UPPER BOUND on the cash a
    # buffer would need if the account were empty, never a measure of surprise.
    bases = []
    for r in ledger:
        if r['fy'] not in af:
            continue
        c = af[r['fy']]['cb_fund_spent']
        before = (max(0, r['ood']['spent'] + c - r['ood']['original'])
                  + max(0, r['indist']['variance']) + max(0, r['trans']['variance']))
        after = next(x for x in need if x['fy'] == r['fy'])['gross']
        bases.append(dict(fy=r['fy'], after=after, before=before, cb_tuition=c))
    if not all(b['cb_tuition'] > 0 for b in bases):
        fail('the circuit breaker account did not pay tuition in every closed year; the '
             'report says it does')
    T300, T500 = 300000, 500000
    after_over_300 = sum(1 for x in need if x['gross'] > T300)
    before_over_300 = sum(1 for b in bases if b['before'] > T300)
    before_within_500 = sum(1 for b in bases if b['before'] <= T500)
    worst_before = max(bases, key=lambda b: b['before'])

    # ---- THE ACCOUNT ITSELF: in, out, and a balance derived from one snapshot.
    snap_row = None
    for r in csv.DictReader(open(Q3, encoding='utf-8')):
        if (r['fund'] or '').lstrip("'") == '2640':
            snap_row = r
    if not snap_row:
        fail('fund 2640 is not in the FY26 March special revenue report')
    q3_bal, q3_rev, q3_exp = (num(snap_row['balance']), num(snap_row['revenue']),
                              num(snap_row['expenditure']) + num(snap_row['salaries'])
                              + num(snap_row['encumbered']))
    if round(q3_rev) != af[last]['cb_fund_receipts']:
        fail('the March snapshot revenue %s is not the FY%d year-end receipt %s'
             % (q3_rev, last, af[last]['cb_fund_receipts']))
    # THE YEAR-END BALANCE, the same way /analysis/sitting-on-money builds it, so the two
    # reports cannot disagree: the annual town report's own Special Revenue schedule
    # ("50/50 Grant Sped Tuitions", special-revenue-read.csv, every row tying to the printed
    # total) through FY2023, then the 30 June 2023 balance carried forward through the
    # period-13 ledgers. The March 2026 report is used only to CHECK the carry.
    raw = {}
    for r in csv.DictReader(open(MUNIS, encoding='utf-8')):
        if r['period'] == '13' and r['fund'] == '2640':
            d = raw.setdefault(int(r['fiscal_year']), [0.0, 0.0, 0.0])
            if r['type'] == 'R':
                d[0] += -num(r['ytd_expended'])
            else:
                d[1] += num(r['ytd_expended']) + num(r['encumbrances'])
                d[2] += num(r['revised_budget'])
    acct = []
    for r in sorted(csv.DictReader(open(SRR, encoding='utf-8')), key=lambda r: int(r['fy'])):
        if r['fund'] == CB_FUND_NAME:
            fy = int(r['fy'])
            acct.append(dict(fy=fy, opening=num(r['forward']), received=num(r['receipts']),
                             spent=num(r['disbursements']), closing=num(r['carried']),
                             budgeted=raw.get(fy, [0, 0, 0])[2], source='annual report'))
    if [a['fy'] for a in acct] != list(range(acct[0]['fy'], acct[-1]['fy'] + 1)):
        fail('the annual report balances for the circuit breaker account are not consecutive')
    if acct[-1]['fy'] in raw and abs(acct[-1]['received'] - raw[acct[-1]['fy']][0]) > 0.01:
        fail('the annual report receipts for FY%d do not equal fund 2640 in MUNIS'
             % acct[-1]['fy'])
    for fy in sorted(y for y in raw if y > acct[-1]['fy']):
        o = acct[-1]['closing']
        acct.append(dict(fy=fy, opening=o, received=raw[fy][0], spent=raw[fy][1],
                         closing=o + raw[fy][0] - raw[fy][1], budgeted=raw[fy][2],
                         source='carried through the year-end ledger'))
    for a_ in acct:
        for k in ('opening', 'received', 'spent', 'closing', 'budgeted'):
            a_[k] = round(a_[k], 2)
    implied = q3_bal - q3_rev + q3_exp
    if abs(implied - next(a_ for a_ in acct if a_['fy'] == last)['opening']) > 0.01:
        fail('the carried 30 June %d balance does not equal the opening the March report '
             'implies (%s)' % (last - 1, implied))
    acct_snap = dict(balance=round(q3_bal, 2), received=round(q3_rev, 2), spent=round(q3_exp, 2),
                     as_of='2026-03-31', fy=last)
    peak = max(acct, key=lambda a_: a_['closing'])
    recent6 = acct[-7:]
    fell = sum(1 for p_, q_ in zip(recent6, recent6[1:]) if q_['closing'] < p_['closing'])
    pre = [a_ for a_ in acct if a_['fy'] in dese and a_['fy'] < munis_first]
    ties = [a_['fy'] for a_ in pre if abs(a_['spent'] - round(dese[a_['fy']]['other_funds'])) <= 2]
    acct_summary = dict(peak=peak, last=acct[-1], fell=fell, of=len(recent6) - 1,
                        dese_ties=ties, dese_years=len(pre))

    # ---- PER CHILD BY TYPE -- OUR ESTIMATE, and a test of whether it can be made at all.
    # DESE splits tuition by school type (9300 non-public, 9400 collaborative); the town's
    # 1 March count splits children into collaborative, day and residential. Day and
    # residential are BOTH non-public here as far as the dollars go, so they are summed.
    m_first_pp = pp_recent[0]['fy']
    by_type = []
    for fy, p in sorted(placed.items()):
        f = func.get(fy)
        if not f or not p['collaborative'] or p['day'] is None or p['residential'] is None:
            continue
        col, nonpub = int(p['collaborative']), int(p['day']) + int(p['residential'])
        by_type.append(dict(fy=fy, collaborative=col, day=int(p['day']),
                            residential=int(p['residential']),
                            tuition_9400=round(f.get('9400', 0)), tuition_9300=round(f.get('9300', 0)),
                            per_collaborative=round(f.get('9400', 0) / col),
                            per_nonpublic=round(f.get('9300', 0) / nonpub) if nonpub else None))
    bt_recent = [x for x in by_type if x['fy'] >= m_first_pp]
    low_collab = min(bt_recent, key=lambda x: x['per_collaborative'])
    np_recent_med = round(med([x['per_nonpublic'] for x in bt_recent]))
    avg = next(c for c in captions if c['key'] == 'average')['quote']
    said_per_child = int(re.search(r'average price of ([\d,]+) per child', avg).group(1)
                         .replace(',', ''))

    # ---- the reserve, as Town Meeting created it, and its cap AS DESCRIBED
    cap_fy = max(y for y in nss if y <= last)
    cap = round(0.02 * nss[cap_fy]['nss'])

    # Scenarios -- OURS. Children times our per-child estimate.
    scen = [dict(children=1, per_child=pp_recent_med, total=pp_recent_med),
            dict(children=biggest_mid['net'], per_child=pp_recent_med,
                 total=biggest_mid['net'] * pp_recent_med)]

    # The largest OVERRUN, as a share of the voted line -- the direction a reserve covers.
    in_band = max(r['indist']['variance_pct'] for r in ledger)
    return dict(
        first=first, last=last, n_years=n_years, munis_first=munis_first,
        tie_years=tie_years, partial=partial, ell=ell, ledger=ledger, per=per, need=need,
        worst_need=worst_need, years_needing=len(years_needing), med_need=med_need,
        worst_recent=worst_recent, allfunds=allfunds, worst_all=worst_all, pairs=pairs,
        receipts_tie=receipts_tie, trend=trend, dese_first=dese_years[0],
        dese_last=dese_years[-1], ood_all_avg=ood_all_avg,
        ood_all_avg_recent=ood_all_avg_recent, combined_avg=combined_avg,
        combined_avg_recent=combined_avg_recent, ood_share_min=min(ood_share),
        ood_share_max=max(ood_share), cb_avg=cb_avg, cb_years=cb_years,
        breaker=breaker, per_placed=per_placed, pp_med=pp_med, pp_last=pp_last,
        pp_recent=pp_recent, pp_recent_med=pp_recent_med, per_served=per_served,
        snap=snap, biggest_mid=biggest_mid, yoy=yoy, biggest_yoy=biggest_yoy,
        biggest_recent_yoy=biggest_recent_yoy, move=move, cap=cap, cap_fy=cap_fy,
        cap_nss=nss[cap_fy], scen=scen, in_band=in_band, quotes=quotes, vote=vote,
        placed=placed, sped=sped, dese=dese, who=who, big_other=big_other, cb_now=cb_now,
        gf_over=gf_over, gf_need_that_year=gf_need_that_year, bases=bases, T300=T300,
        T500=T500, after_over_300=after_over_300, before_over_300=before_over_300,
        before_within_500=before_within_500, worst_before=worst_before, acct=acct,
        acct_snap=acct_snap, acct_summary=acct_summary, by_type=by_type, bt_recent=bt_recent, low_collab=low_collab,
        np_recent_med=np_recent_med, said_per_child=said_per_child, captions=captions)


# --------------------------------------------------------------------- conclusions

def build_conclusions(m):
    """Six cards, in the order a resident needs them: the answer (how much a bad year
    took), where the swing comes from, what the circuit breaker account adds, when the
    state's money arrives, the size of one placement, and the reserve that now exists.
    Every dollar figure says its basis in the card itself -- general fund or every fund,
    before or after the circuit breaker account -- because a reader quoting one at a
    meeting will not carry the footnote with it."""
    P, rows = m['per'], []
    o, t, i = P['ood'], P['trans'], P['indist']
    w = m['worst_need']
    span = C.fyspan(m['first'], m['last'])

    rows.append(conclusion(
        id='the-worst-year-in-seventeen',
        bearing='lever',
        claim='In the worst of %s years, special education needed %s more than its voted budget.'
              % (C.num(m['n_years']), C.usd(w['gross'])),
        so_what='That was %s; the median year needed %s. General fund: what exceeded the '
                'circuit breaker account too.' % (C.fy(w['fy']), C.usd(m['med_need'])),
        detail='Each year from %s, the tuition, in-district and transportation lines are set '
               'against the budget the town voted before the year began, and every line’s '
               'overrun is added up without netting it against another line’s underspend. '
               '%s of the %s years needed something. These are general fund figures, measured '
               'after whatever tuition the district charged to its circuit breaker account that '
               'year — so they are what exceeded both sources. A reserve sized to '
               'the worst year would have covered every one of them — a rule we chose, not a '
               'figure any document recommends.'
               % (span, C.num(m['years_needing']), C.num(m['n_years'])),
        figures={'n': figure(m['n_years'], C.num(m['n_years']), 'years'),
                 'worst': figure(w['gross'], C.usd(w['gross'])),
                 'fy': figure(w['fy'], C.fy(w['fy'])),
                 'span': figure(m['first'], span),
                 'needing': figure(m['years_needing'], C.num(m['years_needing']), 'years'),
                 'median': figure(m['med_need'], C.usd(m['med_need']))},
        figure='worst', kind='measured',
        basis='General fund budget voted before the year against spending at the close, '
              'account by account: MUNIS year-end reports %s, the Finance Committee’s '
              'ledger history before that. The grouping of accounts is ours.'
              % C.fyspan(m['munis_first'], m['last']),
        not_shown='What a future year will need. Seventeen years hold one bad year of each '
                  'kind at most, and the split between the general fund and the circuit '
                  'breaker account is the district’s choice each year.'))

    rows.append(conclusion(
        id='tuition-misses-both-ways',
        bearing='sizes',
        claim='Out-of-district tuition is the swing: over its voted budget in %s of %s years.'
              % (C.num(o['years_over']), C.num(o['years'])),
        so_what='The worst, %s, was %s over. In-district spending never ran more than %s over.'
                % (C.fy(o['worst_fy']), C.usd(o['worst']), C.pct(m['in_band'])),
        detail='The tuition line is a forecast, made months ahead, of which children will '
               'need a placement and at what price. In the other years it came in under, by '
               'as much as %s, and the median year landed %s from it — a line that misses in '
               'both directions is unpredictable rather than under-budgeted. Transportation '
               'ran over in %s years, by as much as %s in %s. All general fund.'
               % (C.usd(-o['best']), C.usd(o['median_variance']), C.num(t['years_over']),
                  C.usd(t['worst']), C.fy(t['worst_fy'])),
        figures={'over': figure(o['years_over'], C.num(o['years_over']), 'years over budget'),
                 'years': figure(o['years'], C.num(o['years']), 'years'),
                 'fy': figure(o['worst_fy'], C.fy(o['worst_fy'])),
                 'worst': figure(o['worst'], C.usd(o['worst'])),
                 'band': figure(m['in_band'], C.pct(m['in_band'])),
                 'best': figure(-o['best'], C.usd(-o['best'])),
                 'median': figure(o['median_variance'], C.usd(o['median_variance'])),
                 't_over': figure(t['years_over'], C.num(t['years_over']), 'years'),
                 't_worst': figure(t['worst'], C.usd(t['worst'])),
                 't_fy': figure(t['worst_fy'], C.fy(t['worst_fy']))},
        figure='over', kind='measured',
        basis='General fund accounts in functions 9100, 9300 and 9400, special education '
              'programme, original budget against spent, %s; in-district is every other '
              'special education account less two English learner accounts. Ours.' % span,
        not_shown='Why any year missed. A placement that began or ended mid-year, a tuition '
                  'rate set after the budget, and money moved to the circuit breaker account '
                  'all look the same from the ledger.'))

    wb, T3, T5 = m['worst_before'], m['T300'], m['T500']
    nb = len(m['bases'])
    rows.append(conclusion(
        id='the-300000-question',
        bearing='lever',
        claim='Measured after the circuit breaker account, no year in %s needed more than %s.'
              % (C.num(m['n_years']), C.usd(T3)),
        so_what='Counting that account’s routine tuition as surprise, %s of %s recent years '
                'did; %s covers %s of %s.'
                % (C.num(m['before_over_300']), C.num(nb), C.usd(T5),
                   C.num(m['before_within_500']), C.num(nb)),
        detail='The first basis is the general fund after the circuit breaker account: what '
               'exceeded both sources, and what a surprise reserve has had to cover. The second '
               'puts the account’s tuition spending back on the tuition line, so it is an upper '
               'bound — what a buffer would need in cash if the account were empty. Its worst '
               'year is %s at %s. The reserve’s cap, as described, is %s.'
               % (C.fy(wb['fy']), C.usd(wb['before']), C.usd(m['cap'])),
        figures={'n': figure(m['n_years'], C.num(m['n_years']), 'years'),
                 't300': figure(T3, C.usd(T3)),
                 'over': figure(m['before_over_300'], C.num(m['before_over_300']), 'years'),
                 'nb': figure(nb, C.num(nb), 'years'),
                 't500': figure(T5, C.usd(T5)),
                 'within': figure(m['before_within_500'], C.num(m['before_within_500']), 'years'),
                 'wfy': figure(wb['fy'], C.fy(wb['fy'])),
                 'wbefore': figure(wb['before'], C.usd(wb['before'])),
                 'cap': figure(m['cap'], C.usd(m['cap']))},
        figure='t300', kind='measured',
        basis='Original general fund budget against spending at the close, every special '
              'education line, overruns added without netting; the second basis adds fund '
              '2640 tuition spending from the MUNIS year-end reports, %s. The rule is ours.'
              % C.fyspan(m['munis_first'], m['last']),
        not_shown='What the next year will need, and how much of the account is already '
                  'spoken for: nothing published says what the district plans to spend from it.'))

    ac, sm, sn = m['acct'], m['acct_summary'], m['acct_snap']
    bs = m['bases']
    lo_ = min(b['cb_tuition'] for b in bs)
    hi_ = max(b['cb_tuition'] for b in bs)
    b23 = next(a for a in ac if a['budgeted'] > 1)
    pk, ls = sm['peak'], sm['last']
    rows.append(conclusion(
        id='the-account-pays-tuition-every-year',
        bearing='sizes',
        claim='The circuit breaker account pays tuition every year, not only when the budget '
              'runs over.',
        so_what='It paid %s to %s of tuition a year, %s to %s. At 30 June %s it held %s.'
                % (C.usd(lo_), C.usd(hi_), C.fy(bs[0]['fy']), C.fy(bs[-1]['fy']),
                   '%d' % ls['fy'], C.usd(ls['closing'])),
        detail='It is a routine second source for tuition, not a fund that only catches '
               'overruns: in %s the ledger shows %s budgeted in it for tuition. So how much of '
               'any overrun it absorbed cannot be told from the ledger. Its year-end balance '
               'peaked at %s in %s and fell in %s of the last %s years.'
               % (C.fy(b23['fy']), C.usd(b23['budgeted']), C.usd(pk['closing']), C.fy(pk['fy']),
                  C.num(sm['fell']), C.num(sm['of'])),
        figures={'lo': figure(lo_, C.usd(lo_)), 'hi': figure(hi_, C.usd(hi_)),
                 'a': figure(bs[0]['fy'], C.fy(bs[0]['fy'])),
                 'b': figure(bs[-1]['fy'], C.fy(bs[-1]['fy'])),
                 'year': figure(ls['fy'], '%d' % ls['fy']),
                 'bal': figure(ls['closing'], C.usd(ls['closing'])),
                 'bfy': figure(b23['fy'], C.fy(b23['fy'])),
                 'budget': figure(b23['budgeted'], C.usd(b23['budgeted'])),
                 'peak': figure(pk['closing'], C.usd(pk['closing'])),
                 'pfy': figure(pk['fy'], C.fy(pk['fy'])),
                 'fell': figure(sm['fell'], C.num(sm['fell']), 'years'),
                 'of': figure(sm['of'], C.num(sm['of']), 'years')},
        figure='hi', kind='measured',
        basis='MUNIS year-end reports for the school special funds, fund 2640, %s; year-end '
              'balances from the annual town reports’ Special Revenue schedule to FY2023, then '
              'carried through the year-end ledgers — the same series /analysis/sitting-on-money '
              'uses.' % C.fyspan(bs[0]['fy'], bs[-1]['fy']),
        not_shown='Whether the voted tuition line is set net of expected circuit breaker '
                  'money, and how much of the balance is earmarked for the next year.',
        allow=('30 June',)))

    n = m['cb_now']
    rows.append(conclusion(
        id='the-refund-arrives-a-year-later',
        bearing='lever',
        claim='The state pays back part of a year’s high special education costs the year '
              'after.',
        so_what='%s brought %s, for %s’s costs. A surprise this year is repaid, in part, '
                'next year.' % (C.fy(n['fy']), C.usd(n['paid']), C.fy(n['for_fy'])),
        detail='As the district described it to the School Committee: for a child whose '
               'costs pass a threshold — four times the state’s average foundation budget per '
               'pupil — the state reimburses about three-quarters of the cost above it, for '
               'the prior year’s expenses, in quarterly payments from September to June. The '
               'money goes into the circuit breaker account, not the general fund or the new '
               'reserve, and this year’s surprise is paid back only next year.',
        figures={'fy': figure(n['fy'], C.fy(n['fy'])),
                 'paid': figure(n['paid'], C.usd(n['paid'])),
                 'for': figure(n['for_fy'], C.fy(n['for_fy']))},
        figure='paid', kind='measured',
        basis='DESE circuit breaker reimbursement file, by fiscal year of payment; the '
              'mechanism quoted from the district’s Circuit Breaker Program Overview to the '
              'School Committee, 2023-2024.',
        not_shown='The statute’s own terms (M.G.L. c.71B s.5A is not in this archive), and '
                  'how much of any one placement comes back: the payment covers in-district '
                  'and transport costs too.'))

    s = m['scen'][1]
    rows.append(conclusion(
        id='a-placement-is-a-six-figure-step',
        bearing='sizes',
        claim='One more child placed out of district is roughly %s a year. Our estimate.'
              % C.usd(m['pp_recent_med']),
        so_what='Every fund’s tuition divided by children placed on 1 March, median %s to '
                '%s. A scale, not a price.'
                % (C.fy(m['pp_recent'][0]['fy']), C.fy(m['pp_recent'][-1]['fy'])),
        detail='Our estimate, and only that. It is not what a placement costs: a residential '
               'placement and a collaborative day place are priced very differently, children '
               'placed for part of the year are counted or missed depending on the day, and '
               'transportation is in another line. The count rose by %s within %s between '
               'DESE’s October count and the town’s March one, and %s children at this '
               'estimate is about %s — two different counts set side by side, which may '
               'partly be a difference in what each counts.'
               % (C.num(m['biggest_mid']['net']), C.fy(m['biggest_mid']['fy']),
                  C.num(s['children']), C.usd(s['total'])),
        figures={'pp': figure(m['pp_recent_med'], C.usd(m['pp_recent_med'])),
                 'a': figure(m['pp_recent'][0]['fy'], C.fy(m['pp_recent'][0]['fy'])),
                 'b': figure(m['pp_recent'][-1]['fy'], C.fy(m['pp_recent'][-1]['fy'])),
                 'rise': figure(m['biggest_mid']['net'], C.num(m['biggest_mid']['net']),
                                'children'),
                 'fy': figure(m['biggest_mid']['fy'], C.fy(m['biggest_mid']['fy'])),
                 'n': figure(s['children'], C.num(s['children']), 'children'),
                 'total': figure(s['total'], C.usd(s['total']))},
        figure='pp', kind='hypothesis',
        basis='DESE End of Year Financial Report, functions 9300 and 9400, all funds; '
              'divided by the placement count in the annual town report (SIMS, 1 March). '
              'The division is ours.',
        not_shown='What any one placement costs. No document in this archive prices one, and '
                  'the count is a single day’s snapshot.',
        allow=('1 March',)))

    return emit(ID, rows)


# --------------------------------------------------------------------- the markdown

def table(head, align, body):
    out = ['| ' + ' | '.join(head) + ' |',
           '|' + '|'.join('---:' if a == 'r' else '---' for a in align) + '|']
    out += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in body]
    return '\n'.join(out) + '\n'


def sgn(x):
    return ('+' if x > 0 else '') + C.usd(x)


def spct(x):
    return ('+' if x > 0 else '') + C.pct(x)


def dash(x, f=C.usd):
    return '—' if x is None else f(x)


def render_md(m, rows):
    P = m['per']
    o, t, i = P['ood'], P['trans'], P['indist']
    span = C.fyspan(m['first'], m['last'])
    w = []
    a = w.append
    a('# Special education: how much a bad year needs\n\n')
    a('**How far special education spending has landed from the budget voted for it, every '
      'year since %s — and what that says about holding money back for mid-year '
      'surprises.**\n\n' % C.fy(m['first']))
    a('![Bars, one group per fiscal year %s, of how far each special education line landed '
      'from the budget voted for it, general fund: out-of-district tuition, in-district, and '
      'transportation. Above the line is an overrun. Tuition swings furthest in both '
      'directions; its largest overrun is %s in %s.](charts/%s-surprise.svg)\n\n'
      % (span, C.usd(o['worst']), C.fy(o['worst_fy']), ID))
    a('## The short version\n\n')
    for c in rows:
        tag = ' *(a hypothesis, not a measurement)*' if c['kind'] == 'hypothesis' else ''
        a('**%s**%s %s\n\n' % (c['claim'], tag, c['so_what']))
    a('---\n\n')

    # ---------------------------------------------------------------- 0. the request
    T3, T5 = m['T300'], m['T500']
    cap_ = {c['key']: c for c in m['captions']}
    a('## The %s request, against the record\n\n' % C.usd(T5))
    a('### The same years, on two bases\n\n')
    body = [[C.fy(b['fy']), C.usd(b['after']), C.usd(b['before']), C.usd(b['cb_tuition']),
             'yes' if b['before'] > T3 else 'no'] for b in m['bases']]
    a(table(['FY', '(a) general fund, after the circuit breaker account — what exceeded both',
             '(b) counting the account’s tuition as surprise — an upper bound',
             'tuition the account paid that year', '(b) above %s?' % C.usd(T3)],
            'lrrrl', body))
    wn = m['worst_need']
    a('\n*%s, the four closed years the year-end reports print in full; every special '
      'education line, overruns added without netting (our rule).* On basis (a), across all '
      '%s years since %s, no year passed %s; the worst was %s, in %s.\n\n'
      % (C.fyspan(m['munis_first'], m['last']), C.num(m['n_years']), C.fy(m['first']),
         C.usd(T3), C.usd(wn['gross']), C.fy(wn['fy'])))
    sn = m['acct_snap']
    b23 = next(x for x in m['acct'] if x['budgeted'] > 1)
    a('- **(b) is the closest the ledger comes to “what hits us mid-year”** — the cash a '
      'buffer would have to find if the circuit breaker account could not be used in time. '
      'In %s the account had spent %s by 31 March and charged its %s of tuition after that, '
      'so through the year the general fund carried the bills; that is observed for %s only.\n'
      % (C.fy(sn['fy']), C.usd(sn['spent']),
         C.usd(next(b for b in m['bases'] if b['fy'] == sn['fy'])['cb_tuition']), C.fy(sn['fy'])))
    a('- **But (b) overstates.** The account pays tuition every year, overrun or not — in %s '
      'the ledger budgeted %s in it for tuition — so (b) counts planned spending as surprise.\n'
      % (C.fy(b23['fy']), C.usd(b23['budgeted'])))
    a('- **(a) is what the town’s budget ultimately absorbed**, and it is the basis this page '
      'uses to size a reserve — our choice. On it, %s would have covered every year; on (b), %s covers %s '
      'of %s, and the reserve’s cap as described is %s.\n\n'
      % (C.usd(T3), C.usd(T5), C.num(m['before_within_500']), C.num(len(m['bases'])),
         C.usd(m['cap'])))
    a('### What was said\n\n')
    a('The town has not yet published minutes for these meetings. These are our machine '
      'captions of the recordings — a finding aid, not a record: open the video at the '
      'moment given and check every figure there.\n\n')
    for k in ('overages', 'one', 'average', 'fifteen', 'motion', 'range'):
        c = cap_[k]
        a('- *"%s"* — %s, %s, [video at %s](%s)\n' % (c['quote'], c['board'], c['date'],
                                                      c['at'], c['cite']))
    a('\nA request for %s, and the words *two kids* or *two students* beside a reserve, were '
      'not found. Searched: the town’s minutes and our captions for the School Committee, '
      'Finance Committee and Select Board since 1 July 2025, for *500,000*, *five hundred*, '
      '*half a million*, *buffer*, *two kids*, *two students*, *two placements* and '
      '*reserve*. That is a statement about this archive, not about the meetings — a meeting '
      'not yet captioned, or said outside one, would not show here. What the captions do '
      'hold is the School Committee voting to request %s on 7 October 2026 — to be checked '
      'against the video.\n\n' % (C.usd(T5),
                                                                            C.usd(T3)))
    a('### Is %s two children?\n\n' % C.usd(T3))
    a('At the %s per child the captions render, %s is two. Our own estimate — every fund’s '
      'tuition divided by children placed on 1 March — has a median of %s for %s, and was %s '
      'in %s. *(Our estimate, a hypothesis, not a price.)*\n\n'
      % (C.usd(m['said_per_child']), C.usd(T3), C.usd(m['pp_recent_med']),
         C.fyspan(m['pp_recent'][0]['fy'], m['pp_recent'][-1]['fy']),
         C.usd(max(m['pp_recent'], key=lambda x: x['per_child'])['per_child']),
         C.fy(max(m['pp_recent'], key=lambda x: x['per_child'])['fy'])))
    body = [[C.fy(x['fy']), C.num(x['collaborative']), C.num(x['day']), C.num(x['residential']),
             C.usd(x['tuition_9400']), C.usd(x['tuition_9300']), C.usd(x['per_collaborative']),
             C.usd(x['per_nonpublic'])] for x in m['bt_recent']]
    a(table(['FY', 'collaborative, 1 March', 'day', 'residential',
             'tuition to collaboratives (DESE 9400)', 'tuition to non-public schools (DESE 9300)',
             'per collaborative child — OUR ESTIMATE', 'per day or residential child — OUR ESTIMATE'],
            'lrrrrrrr', body))
    lc = m['low_collab']
    a('\n**A cost by type of placement cannot be derived here.** The counts split by type and '
      'the dollars split by type of school, but they do not line up: %s gives %s per '
      'collaborative child, which is no tuition. Day and residential places are both '
      'non-public schools in the dollars, so they cannot be separated, and nothing in this '
      'archive prices a residential place against a day place — so this page does not say '
      'which costs more. The day-or-residential column has a median of %s over these years; '
      'treat it as a hypothesis.\n\n'
      % (C.fy(lc['fy']), C.usd(lc['per_collaborative']), C.usd(m['np_recent_med'])))
    a('### Arrivals, not the net\n\n')
    a('Every figure on this page is a NET result at the close of a year: children who arrived, '
      'less children who left, less anything else that came in under budget. A surprise of '
      'hundreds of thousands a year may describe arrivals alone, and arrivals are not '
      'published. A dated log of placements would settle it; it is the '
      'gap registered as *How many children enter or leave an out-of-district placement '
      'during a school year, and when?*\n\n---\n\n')

    # ---------------------------------------------------------------- 1. the surprise
    a('## How far each year landed from its budget\n\n')
    a('### In plain terms\n\n')
    a('Before each year begins the town votes a budget for special education. At the close '
      'of the year the accounting system records what was spent. The difference is the '
      'surprise. Across %s years, the out-of-district tuition line ran over in %s and under '
      'in the rest; transportation ran over in %s; the in-district lines ran over in %s, and '
      'never by more than %s.\n\n'
      % (C.num(m['n_years']), C.num(o['years_over']), C.num(t['years_over']),
         C.num(i['years_over']), C.pct(m['in_band'])))
    a('### The evidence\n\n')
    body = []
    for r, n in zip(m['ledger'], m['need']):
        body.append([C.fy(r['fy']),
                     C.usd(r['ood']['original']), C.usd(r['ood']['spent']), sgn(r['ood']['variance']),
                     C.usd(r['indist']['original']), C.usd(r['indist']['spent']),
                     sgn(r['indist']['variance']),
                     C.usd(r['trans']['original']), C.usd(r['trans']['spent']),
                     sgn(r['trans']['variance']),
                     C.usd(n['gross']),
                     'MUNIS year-end' if r['source'] == 'munis' else 'FinCom history'])
    a(table(['FY', 'tuition voted', 'tuition spent', 'miss', 'in-district voted',
             'in-district spent', 'miss', 'transport voted', 'transport spent', 'miss',
             'overruns, added', 'ledger'], 'lrrrrrrrrrrl', body))
    a('\n*%s, %s years.* **voted** is the ORIGINAL general fund budget — what Town Meeting '
      'appropriated before the year began. **spent** is expended plus encumbered at the '
      'close (only %s carries an encumbrance). **overruns, added** is every line’s '
      'overrun summed without netting any line’s underspend against it: the amount a '
      'reserve would have had to supply if nothing else in the school budget were moved. '
      '**That rule is ours.** Netting the three lines instead, the worst year is %s, %s.\n\n'
      % (span, C.num(m['n_years']), C.fy(m['last']),
         C.fy(max(m['need'], key=lambda x: x['net'])['fy']),
         sgn(max(m['need'], key=lambda x: x['net'])['net'])))
    a('**Comparing a budget to an actual is allowed here, and only here.** Rule 1 of this '
      'project forbids mixing the two in a growth rate or a projection, because the step '
      'between them contaminates the rate. In this section the step between them is the '
      'thing being measured. Nothing below grows a budget from an actual.\n\n')
    r25 = next((r for r in m['ledger'] if r['fy'] == 2025), None)
    if r25:
        tot25 = sum(r25[g]['variance'] for g in GROUPS)
        ow = lambda x: '%s %s' % (C.usd(abs(x)), 'over' if x > 0 else 'under')
        a('**Is this FY2025 again?** FY2025 is the year the schools finished with money '
          'unspent. Its three special education lines together came in %s the budget voted '
          'for them, %s of it on tuition. In %s, the latest closed year, they came in %s.\n\n'
          % (ow(tot25), C.usd(abs(r25['ood']['variance'])), C.fy(m['last']),
             ow(m['need'][-1]['net'])))
    a('**What was said in the overrun years.** Statements, not measurements.\n\n')
    for q in m['quotes']:
        if q['key'] in ('skyrocket', 'fourteen'):
            a('> *"%s"* — %s, %s ([minutes](%s))\n\n%s\n\n'
              % (q['quote'], q['board'], q['date'], q['cite'], q['why']))
    a('**Which ledger.** %s onward is the Town’s MUNIS year-end (period 13) report — a '
      'printout from the accounting system. Before that it is the Finance Committee’s '
      'general fund history workbook, which a person assembled from per-year exports. It is '
      'used because, for %s, its special education rows match the MUNIS reports to the '
      'dollar on both the voted budget and the spending, and the build refuses to run if '
      'they stop matching. Its %s column is marked partial and is not used.\n\n'
      % (C.fy(m['munis_first']), ' and '.join(C.fy(y) for y in m['tie_years']),
         ', '.join(C.fy(y) for y in m['partial'])))
    a('### What this does not show\n\n')
    a('Why any year missed. A child placed or leaving mid-year, a tuition rate the state set '
      'after the budget was built, a vacancy, and a payment moved to the circuit breaker '
      'account all produce the same row. It also does not show the size of a bad year that '
      'has not happened: %s years is the whole of what the ledger holds, and the reserve '
      'rule above covers the worst of them, not the worst possible.\n\n---\n\n'
      % C.num(m['n_years']))

    # ---------------------------------------------------------------- 2. the circuit breaker
    a('## How the circuit breaker fits in\n\n')
    who = m['who']
    split = [r for r in who if r['basis'] == 'dese+munis']
    a('![Stacked bars, one per fiscal year %s, of out-of-district tuition by who paid it: the '
      'general fund, the circuit breaker account, and other funds — split for %s, and only '
      'the town’s two funds for %s. Beside them, a line for the circuit breaker money the '
      'state paid that year, and a dashed line for the money that year’s costs earned, paid '
      'the year after. The dashed line is the solid one moved a year to the left: that shift '
      'is the lag.](charts/%s-circuit-breaker.svg)\n\n'
      % (C.fyspan(who[0]['fy'], who[-1]['fy']), C.fyspan(split[0]['fy'], split[-1]['fy']),
         C.fy(who[-1]['fy']), ID))
    a('### In plain terms\n\n')
    Q = CB_QUOTES
    a('The circuit breaker is the state paying back part of the cost of the most expensive '
      'children’s services. As the district explained it to the School Committee:\n\n')
    a('- **Who qualifies.** A child whose costs pass a threshold of *"%s"*. Above it, *"%s"* '
      '*"%s"*\n' % (Q['threshold'], Q['share'], Q['eligible']))
    a('- **When.** *"%s"* The state pays in four instalments, from *"%s"* to *"%s"*.\n'
      % (Q['prior'], Q['first'], Q['last']))
    a('- **Where it goes.** *"%s"* — fund 2640 in the town’s ledger. *"%s"* fiscal year '
      '*"%s"* The town does not vote it.\n' % (Q['account'], Q['spend'], Q['vote']))
    a('- **What that means for a surprise.** A tuition bill that runs over this year is paid '
      'back, in part, next year — into that account, not into the general fund or the new '
      'reserve. What can help in the middle of a year is whatever is already in the account '
      'from last year’s payment.\n\n')
    a('*Quoted from the district’s Circuit Breaker Program Overview to the School Committee, '
      '2023-2024 ([PDF](/docs/%s)). That is the district’s description; the statute, Mass. '
      'General Laws chapter 71B section 5A, is not in this archive, so the threshold and '
      'the share are as the district stated them.*\n\n' % CB_PDF)
    a('### The evidence\n\n')
    body = []
    for r in who:
        if r['basis'] == 'dese':
            cba, oth = '—', '%s (all non-general funds together)' % C.usd(r['other_unsplit'])
        elif r['basis'] == 'dese+munis':
            cba, oth = C.usd(r['cb_account']), C.usd(r['other'])
        else:
            cba, oth = C.usd(r['cb_account']), 'not yet published'
        body.append([C.fy(r['fy']), C.usd(r['gf']), cba, oth, dash(r['total']),
                     dash(r['received']), dash(r['earned'])])
    a(table(['FY', 'tuition paid by the general fund', 'by the circuit breaker account',
             'by other funds', 'tuition, every fund', 'circuit breaker received that year '
             '(for the year before)', 'circuit breaker earned by that year’s costs (received '
             'the year after)'], 'lrrrrrr', body))
    a('\n*%s. Tuition is out-of-district tuition, functions 9300 and 9400. The general fund '
      'and every-fund totals are DESE’s End of Year Financial Report; for %s the '
      'circuit breaker account is the town’s year-end report for fund 2640, and other funds '
      'are DESE’s non-general-fund total less that account. DESE’s general fund figure ties '
      'to the town’s ledger to the dollar in each of those years, and the build refuses if it '
      'stops. %s is the town’s ledger alone, because DESE has not yet published it. The two '
      'circuit breaker columns are DESE’s payment file, keyed by year of payment, and cover '
      'in-district and transport costs as well as tuition.*\n\n'
      % (C.fyspan(who[0]['fy'], who[-1]['fy']), C.fyspan(split[0]['fy'], split[-1]['fy']),
         C.fy(who[-1]['fy'])))
    sm, sn = m['acct_summary'], m['acct_snap']
    a('**A routine second source, not an overflow.** The circuit breaker account paid tuition '
      'in every closed year the ledger reports, overrun or not, beside the general fund — so '
      'how much of any overrun it absorbed cannot be told from the ledger. Every general fund '
      'figure on this page is measured after whatever was charged to it: what exceeded both. '
      'Before %s the account’s own disbursements, as the annual report prints them, equal '
      'DESE’s non-general-fund tuition to within %s in %s of %s years, so the grey bars are '
      'probably mostly this account; year by year that is not established.\n\n'
      % (C.fy(m['munis_first']), C.usd(2), C.num(len(sm['dese_ties'])),
         C.num(sm['dese_years'])))
    a('**The cushion that already exists.** The account’s balance at each year end:\n\n')
    body = [[C.fy(x['fy']), C.usd(x['opening']), C.usd(x['received']), C.usd(x['spent']),
             C.usd(x['closing']), x['source']] for x in m['acct']]
    a(table(['FY', 'balance, 1 July', 'received', 'spent', 'balance, 30 June', 'from'],
            'lrrrrl', body))
    pk, ls = sm['peak'], sm['last']
    a('\n*The same series /analysis/sitting-on-money uses: the annual town report’s Special '
      'Revenue schedule (“%s”) through %s, then carried through the year-end ledgers.* It '
      'peaked at %s at the close of %s and was %s at 30 June %s, falling in %s of the last %s '
      'years. Within %s, the Town’s special revenue report showed %s on 31 March, a snapshot '
      'taken before the year’s tuition was charged: %s had been spent from it by then, %s by '
      'the close. The carried 30 June %s '
      'balance equals the opening that report implies, to the cent.\n\n'
      % (CB_FUND_NAME, C.fy(max(a_['fy'] for a_ in m['acct'] if a_['source'] == 'annual report')),
         C.usd(pk['closing']), C.fy(pk['fy']), C.usd(ls['closing']), ls['fy'],
         C.num(sm['fell']), C.num(sm['of']), C.fy(sn['fy']), C.usd(sn['balance']),
         C.usd(sn['spent']), C.usd(ls['spent']), sn['fy'] - 1))
    q = next(x for x in m['quotes'] if x['key'] == 'carryover')
    a('> *"%s"* — %s, %s ([minutes](%s))\n\n%s\n\n'
      % (q['quote'], q['board'], q['date'], q['cite'], q['why']))
    body = [[C.fy(x['fy']), C.usd(x['gf_original']), C.usd(x['gf_spent']),
             C.usd(x['cb_fund_spent']), C.usd(x['all_spent']), sgn(x['above_voted']),
             spct(x['above_voted_pct']), C.usd(x['cb_fund_receipts']),
             dash(x['dese_paid'])] for x in m['allfunds']]
    a(table(['FY', 'tuition voted (general fund)', 'spent, general fund',
             'spent, circuit breaker account', 'spent, both',
             'both, above the general fund line voted (counts the account’s routine spending)',
             'as a share of it', 'circuit breaker received (town ledger)',
             'circuit breaker paid (state schedule)'], 'lrrrrrrrr', body))
    a('\n*%s, MUNIS year-end reports for the school general fund and the school special '
      'funds.* The account also paid %s in these years for things other than tuition.\n\n'
      % (C.fyspan(m['munis_first'], m['last']),
         C.usd(sum(x['cb_fund_other'] for x in m['allfunds']))))
    if m['pairs']:
        p = m['pairs'][0]
        a('**The ledger and the state agree, a year apart.** The receipts the ledger books '
          'and the payments the state’s schedule lists match in %s. Where they do not, '
          'the difference moves between years: %s and %s together come to %s in both, with '
          '%s booked a year later than the state lists it. In %s the ledger booked %s of '
          'the %s the state lists.\n\n'
          % (', '.join(C.fy(y) for y in m['receipts_tie']) or 'no year',
             C.fy(p['fy_a']), C.fy(p['fy_b']), C.usd(p['total']), C.usd(p['shifted']),
             C.fy(m['cb_now']['fy']), C.usd(m['cb_now']['ledger_received']),
             C.usd(m['cb_now']['paid'])))
    bo = m['big_other']
    if bo['other'] != bo['received']:
        fail('the FY%d remainder no longer equals the state payment; rewrite the paragraph'
             % bo['fy'])
    a('**One figure we cannot explain.** In %s, DESE’s total for tuition from funds other '
      'than the general fund is %s more than the circuit breaker account paid — and %s is '
      'also, to the dollar, the circuit breaker payment the state lists for %s. That may be a '
      'coincidence or a reporting choice; nothing here says which, and it is registered as a '
      'gap. In the other years the remainder is %s.\n\n'
      % (C.fy(bo['fy']), C.usd(bo['other']), C.usd(bo['other']), C.fy(bo['fy']),
         ' and '.join('%s in %s' % (C.usd(r['other']), C.fy(r['fy']))
                      for r in split if r['fy'] != bo['fy'])))
    a('### What this does not show\n\n')
    a('Whether the district plans on the account. If the general fund tuition line is built '
      'expecting the circuit breaker to pay part, the amount above it is a plan rather than '
      'a surprise. The district’s own presentation says *"%s"* for the following year when '
      'deliberating on the general fund budget; nothing published says whether '
      'Lunenburg’s line does — the same open question `sped-and-funds.md` asks of '
      'the FY27 line. Nor does this show how much of any one placement comes back: the '
      'state’s payment covers in-district and transport costs too, and is not split by '
      'child.\n\n---\n\n' % CB_QUOTES['plan'])

    # ---------------------------------------------------------------- 3. trend + averages
    a('## The trend, and the averages\n\n')
    a('![Lines by fiscal year: in-district special education spending, out-of-district '
      'tuition from the general fund, out-of-district tuition from every fund as DESE '
      'reports it, and the circuit breaker reimbursement paid, %s to %s.](charts/%s-trend.svg)\n\n'
      % (C.fy(m['trend'][0]['fy']), C.fy(m['trend'][-1]['fy']), ID))
    a('### In plain terms\n\n')
    a('Over %s, in-district special education averaged %s a year of general fund spending '
      'and out-of-district tuition %s. Together, on that same basis, %s a year; over the last '
      'five years, %s. Counting every fund, as the state reports it, out-of-district tuition '
      'averaged %s a year over %s, and the circuit breaker paid back an average of %s a '
      'year.\n\n'
      % (span, C.usd(i['avg_spent']), C.usd(o['avg_spent']), C.usd(m['combined_avg']),
         C.usd(m['combined_avg_recent']), C.usd(m['ood_all_avg']),
         C.fyspan(m['dese_first'], m['dese_last']), C.usd(m['cb_avg'])))
    a('### The evidence\n\n')
    body = [[C.fy(x['fy']), dash(x['indist_spent']), dash(x['ood_gf_spent']),
             dash(x['trans_spent']), dash(x['ood_all_funds']), dash(x['cb_paid'])]
            for x in m['trend']]
    a(table(['FY', 'in district, spent (general fund)', 'tuition, spent (general fund)',
             'transportation, spent (general fund)', 'tuition, every fund (DESE)',
             'circuit breaker paid (DESE)'], 'lrrrrr', body))
    a('\n*%s.* Each column is ONE basis and they are never added across: the first three are '
      'the town’s ledger, closed-year spending, general fund only; the fourth is '
      'DESE’s End of Year Financial Report, functions 9300 and 9400, every fund; the '
      'fifth is the state’s payment schedule, by year of PAYMENT, and each payment '
      'answers for the year before.\n\n' % C.fyspan(m['trend'][0]['fy'], m['trend'][-1]['fy']))
    body = [
        ['In-district special education (general fund, ours)', span, C.usd(i['avg_spent']),
         C.usd(i['avg_spent_recent'])],
        ['Out-of-district tuition (general fund)', span, C.usd(o['avg_spent']),
         C.usd(o['avg_spent_recent'])],
        ['**Combined, in district and out (general fund)**', span,
         '**%s**' % C.usd(m['combined_avg']), '**%s**' % C.usd(m['combined_avg_recent'])],
        ['Special education transportation (general fund)', span, C.usd(t['avg_spent']),
         C.usd(t['avg_spent_recent'])],
        ['Out-of-district tuition, every fund (DESE)', C.fyspan(m['dese_first'], m['dese_last']),
         C.usd(m['ood_all_avg']), C.usd(m['ood_all_avg_recent'])],
    ]
    a(table(['average a year of', 'span', 'whole span', 'last five years'], 'llrr', body))
    a('\n**Why the combined figure is general fund only, and transportation sits apart.** '
      'The in-district lines and the general fund tuition line come from the same ledger, '
      'the same fund and the same years, so adding them is like with like. Tuition from '
      'every fund comes from a different return and has no in-district counterpart — DESE '
      'publishes no in-district special education total — so it is not added to anything. '
      'Transportation is one account, and the circuit breaker reimburses the '
      'out-of-district part of it, so it cannot be put on either side. Out-of-district tuition was between %s and %s of the general fund '
      'combined figure across the span.\n\n' % (C.pct(m['ood_share_min']), C.pct(m['ood_share_max'])))
    a('### What this does not show\n\n')
    a('What special education costs. Every general fund figure here is NET (rule 11): grant-'
      'funded staff, the circuit breaker account and anything paid from a revolving fund are '
      'missing from it, and the in-district total rests on a classification of accounts that '
      'is ours. The averages describe what the town’s budget carried, not the cost of '
      'educating any child.\n\n---\n\n')

    # ---------------------------------------------------------------- 4. per child
    a('## Per child — our estimate, and what it is not\n\n')
    a('### In plain terms\n\n')
    a('Dividing a year’s tuition, from every fund, by the number of children the town '
      'counted as placed gives %s per child as the median of %s, and %s in %s. That is our '
      'arithmetic on two published numbers. It is not the price of a placement.\n\n'
      % (C.usd(m['pp_recent_med']), C.fyspan(m['pp_recent'][0]['fy'], m['pp_recent'][-1]['fy']),
         C.usd(m['pp_last']['per_child']), C.fy(m['pp_last']['fy'])))
    a('### The evidence\n\n')
    body = [[C.fy(x['fy']), C.usd(x['all_funds']), C.num(x['children']), C.usd(x['per_child'])]
            for x in m['per_placed']]
    a(table(['FY', 'tuition, every fund (DESE)', 'children placed, 1 March (town)',
             'per child — OUR ESTIMATE'], 'lrrr', body))
    a('\n*%s.* Median over the whole span %s.\n\n'
      % (C.fyspan(m['per_placed'][0]['fy'], m['per_placed'][-1]['fy']), C.usd(m['pp_med'])))
    body = [[C.fy(x['fy']), C.num(x['in_district_children']), C.usd(x['indist_spent']),
             C.usd(x['per_child_in_district']), C.num(x['all_children']),
             C.usd(x['combined_gf']), C.usd(x['per_child_combined'])] for x in m['per_served']]
    a(table(['FY', 'children with a plan, in district (DESE)', 'in-district spent (general fund, ours)',
             'per child in district — OUR ESTIMATE', 'children with a plan, all (DESE)',
             'in district + tuition (general fund)', 'per child, combined — OUR ESTIMATE'],
            'lrrrrrr', body))
    a('\n*%s, the years DESE publishes the in-district count.* DESE counts children with a '
      'plan in October; the town counts placements in March.\n\n'
      % C.fyspan(m['per_served'][0]['fy'], m['per_served'][-1]['fy']))
    a('### What this does not show\n\n')
    a('/what-special-education-costs refuses to compute any of these, and its reasons stand: '
      'the dollars and the children come from different returns with different rules. Each '
      'figure here is a net ledger total divided by a headcount taken on one day. It misses '
      'the circuit breaker reimbursement on the in-district side, grant-funded staff, '
      'transportation, and every child placed or served for part of a year. A child in '
      'district also costs the general education budget, which none of these lines carry. '
      'Read them as orders of magnitude for planning, never as a price.\n\n---\n\n')

    # ---------------------------------------------------------------- 5. movement
    a('## How many children arrive or leave mid-year\n\n')
    a('### In plain terms\n\n')
    bm = m['biggest_mid']
    a('Nothing published counts children entering or leaving an out-of-district placement '
      'during a year. What can be shown is two counts taken months apart: DESE’s in '
      'October and the town’s in March. The largest rise between them was %s, in %s. '
      'From one March to the next, the largest rise was %s, in %s, and %s in the last few '
      'years (%s).\n\n'
      % (C.num(bm['net']), C.fy(bm['fy']), C.num(m['biggest_yoy']['change']),
         C.fy(m['biggest_yoy']['fy']), C.num(m['biggest_recent_yoy']['change']),
         C.fy(m['biggest_recent_yoy']['fy'])))
    a('### The evidence\n\n')
    body = [[C.fy(x['fy']), C.num(x['october']), C.num(x['march']),
             ('+' if x['net'] > 0 else '') + C.num(x['net'])] for x in m['snap']]
    a(table(['FY', 'placed out of district, October (DESE)', 'placed, 1 March (town)',
             'net change'], 'lrrr', body))
    a('\n*%s.* A NET change: a child who arrived and another who left between the two dates '
      'cancel to zero, and a child placed and returned between them is in neither count.\n\n'
      % C.fyspan(m['snap'][0]['fy'], m['snap'][-1]['fy']))
    body = []
    for fy in sorted(m['placed']):
        p = m['placed'][fy]
        ch = next((x['change'] for x in m['yoy'] if x['fy'] == fy), None)
        body.append([C.fy(fy), C.num(p['total']), p['collaborative'] or '—', p['day'] or '—',
                     p['residential'] or '—',
                     '—' if ch is None else ('+' if ch > 0 else '') + C.num(ch)])
    a(table(['FY', 'children placed, 1 March', 'collaborative', 'day', 'residential',
             'change from the year before'], 'lrrrrr', body))
    a('\n*%s, the town’s count from the Special Services report in each annual town '
      'report (SIMS, 1 March).* FY2021 is recovered from FY2022’s back-reference; its '
      'split is not printed. See `PROVENANCE-placement-counts.md`.\n\n'
      % C.fyspan(min(m['placed']), max(m['placed'])))
    body = [[C.fy(x['fy']), C.num(x['on_iep']), C.num(x['moved_in']), C.num(x['moved_out']),
             'identical to the year before — not a second year' if x['repeats_prior_year'] else '']
            for x in m['move']]
    a(table(['FY', 'on a plan, K-12', 'moved in', 'moved out', 'note'], 'lrrrl', body))
    a('\n*DESE, Students Moving In and Out of Special Education Services (8aww-sugs), %s.* '
      'This counts children entering and leaving SERVICES — gaining or ending a plan — and '
      'not placements. The file carries no definition column; the reading is from its '
      'title, and the statewide figures fit it.\n\n'
      % C.fyspan(m['move'][0]['fy'], m['move'][-1]['fy']))
    a('**What was said.** None of this is a count.\n\n')
    for q in m['quotes']:
        if q['key'] in ('april', 'nine', 'radar', 'nineteen'):
            a('> *"%s"* — %s, %s ([minutes](%s))\n\n%s\n\n'
              % (q['quote'], q['board'], q['date'], q['cite'], q['why']))
    a('### What this does not show\n\n')
    a('How many children arrived or left during any year, or when. The two snapshots may '
      'also differ because DESE and the town count differently, which is why they agree in '
      'some years and not others — see the gap registered as *How many out-of-district '
      'placements are children who arrived already placed*. A dated log of placements would '
      'settle it.\n\n---\n\n')

    # ---------------------------------------------------------------- 6. the reserve
    a('## Sizing a reserve — our arithmetic, not a recommendation\n\n')
    a('### In plain terms\n\n')
    s1, s2 = m['scen']
    a('**This page sizes a reserve on one basis: the general fund, measured after whatever '
      'was charged to the circuit breaker account — what exceeded both sources.** The '
      'account pays tuition every year, so counting its spending as surprise overstates; '
      'that upper bound is shown beside it, labelled. How much goes on the account, and when '
      'in the year, is the district’s choice. Every row is our arithmetic.\n\n')
    wa = m['worst_all']
    body = [
        ['**General fund, after the circuit breaker account** — the worst year, every '
         'line’s overrun added', '%s (%s)' % (span, C.fy(m['worst_need']['fy'])),
         '**%s**' % C.usd(m['worst_need']['gross'])],
        ['General fund, after the circuit breaker account — the worst of the four years with '
         'year-end reports', '%s (%s)' % (C.fyspan(m['munis_first'], m['last']),
                                         C.fy(m['worst_recent']['fy'])),
         C.usd(m['worst_recent']['gross'])],
        ['General fund, after the circuit breaker account — the median year', span,
         C.usd(m['med_need'])],
        ['UPPER BOUND, counting the circuit breaker account’s routine tuition as surprise — '
         'worst year', '%s (%s)' % (C.fyspan(m['munis_first'], m['last']),
                                    C.fy(m['worst_before']['fy'])),
         C.usd(m['worst_before']['before'])],
        ['The circuit breaker account’s balance at 30 June %d — a cushion that already exists'
         % m['acct_summary']['last']['fy'], C.fy(m['acct_summary']['last']['fy']),
         C.usd(m['acct_summary']['last']['closing'])],
        ['One unplanned placement at the per-child estimate (every fund)',
         C.fyspan(m['pp_recent'][0]['fy'], m['pp_recent'][-1]['fy']), C.usd(s1['total'])],
        ['%s unplanned placements — the largest rise between October and March (every fund)'
         % C.num(s2['children']), C.fy(m['biggest_mid']['fy']), C.usd(s2['total'])],
        ['The reserve’s cap, 2%% of %s net school spending, as described' % C.fy(m['cap_fy']),
         C.fy(m['cap_fy']), C.usd(m['cap'])],
    ]
    a(table(['measure', 'from', 'amount'], 'llr', body))
    a('\n### What changes what a reserve must cover\n\n')
    a('- **The circuit breaker pays a year late, and into its own account.** A placement '
      'that starts in September is reimbursed, in part, the following year at the earliest, '
      'and the payment lands in the circuit breaker account rather than the reserve. See *How '
      'the circuit breaker fits in*.\n')
    q = next(x for x in m['quotes'] if x['key'] == 'april')
    a('- **A child who moves in late may not land on this budget at all that year.** The '
      'district told the School Committee on %s that a child entering after 1 April is the '
      'sending district’s cost for the rest of that year and the next. That is a '
      'statement at a meeting; the rule itself is not in this archive.\n' % q['date'])
    q = next(x for x in m['quotes'] if x['key'] == 'nineteen')
    fc = int(re.search(r'(\d+) out-of-district placements', q['quote']).group(1))
    lastp = max(m['placed'])
    since = max((y for y in m['placed'] if m['placed'][y]['total'] >= fc), default=None)
    a('- **The forecast for FY2027 is well above the recent counts.** The School Committee '
      'was told on %s that %s placements were anticipated. The town counted %s on 1 March '
      '%s%s. If the forecast holds, the per-child estimate above puts the difference at '
      'about %s a year — our arithmetic on a forecast, not a measurement.\n\n'
      % (q['date'], C.num(fc), C.num(m['placed'][lastp]['total']), lastp,
         ('; the last year it counted %s or more was %s' % (C.num(fc), C.fy(since)))
         if since else '; it has never counted that many',
         C.usd((fc - m['placed'][lastp]['total']) * m['pp_recent_med'])))
    a('- **What would have shown a bad year coming.** A placement log with start and end '
      'dates, and a statement of how much of the tuition line the district expects the '
      'circuit breaker account to pay. Neither is published; both are registered as gaps, '
      'and both are things a Finance Committee could ask for before voting the line.\n\n')
    a('### The reserve that now exists\n\n')
    v = m['vote']
    a('> *"%s"* — Special Town Meeting, 18 November 2025 ([FY2025 annual town report](%s)). '
      'The Finance Committee recommended disapproval.\n\n' % (v['quote'], v['cite']))
    for q in m['quotes']:
        if q['key'] in ('establish', 'urgency'):
            a('> *"%s"* — %s, %s ([minutes](%s))\n\n%s\n\n'
              % (q['quote'], q['board'], q['date'], q['cite'], q['why']))
    a('The School Committee’s agenda for 7 October 2026 carries an item to *"%s"*. The '
      'amount, and whether "November 2026" is the date of a coming vote or a misprint for '
      'November 2025, are not established here.\n\n' % AGENDA['quote'])
    a('### What this does not show\n\n')
    a('What the town should hold. A reserve sized to the worst of %s years covers the worst '
      'of %s years. The per-child scenarios rest on our estimate. And the statute’s own '
      'terms — the cap, who may spend it, what counts as unanticipated — are taken from how '
      'they were described at a meeting, because chapter 40 section 13E is not in this '
      'archive.\n\n---\n\n' % (C.num(m['n_years']), C.num(m['n_years'])))

    # ---------------------------------------------------------------- persona review
    a('## Read as each reader\n\n')
    a('`notes/process/PERSONAS.md`, run before publishing.\n\n')
    a('- **Already sure the schools are not straight with them.** The largest figure on the '
      'page — %s in %s, counting the circuit breaker account’s routine tuition as surprise — '
      'is in the summary, labelled as the upper bound it is, and so is the fact that '
      'in-district spending never ran more than %s over.\n'
      % (C.usd(m['worst_before']['before']), C.fy(m['worst_before']['fy']), C.pct(m['in_band'])))
    a('- **Hears it second-hand.** The sentence they will repeat is the first card: in the '
      'worst of %s years special education needed %s more than its voted budget. It is true '
      'as worded, on the general fund basis it names; it is not a statement that '
      'anybody overspent, because tuition came in under budget in most years.\n'
      % (C.num(m['n_years']), C.usd(m['worst_need']['gross'])))
    a('- **Close to the boards.** No finding names a person. The one person named is '
      'quoted for an argument made on the record at a public meeting.\n')
    a('- **Finance Committee.** One thing to do differently: ask, before voting the tuition '
      'line, how much of it the district expects the circuit breaker account to pay, and '
      'for the placement count it was built on.\n')
    a('- **School Committee.** *Is this FY2025 again?* is answered in the first section.\n')
    a('- **Select Board.** Nothing here compares the town side with the school side.\n')
    a('- **Somebody with one concrete thing.** The meeting archive was searched for '
      '*out of district*, *special education reserve*, *13E*, *mid-year*, *move into the '
      'district* and *unanticipated*, in the town’s published minutes and agendas; every '
      'quotation on this page came out of that search and is re-read from the archive on '
      'every build. Machine transcripts of the recordings were not searched for this '
      'page.\n\n')

    # ---------------------------------------------------------------- method + sources
    a('## Method and classification\n\n')
    a('Analysis, October 2026. A draft for review. Every figure is computed by '
      '`scripts/build_sped_costs.py`; the grouping of accounts, the reserve rule and every '
      'per-child figure are ours and say so where they appear.\n\n')
    a('- **Which accounts.** In the town’s account string the fourth segment is the '
      'function code and the fifth is `51` on every general fund school account whose own '
      'description names special education — checked on every run — except special '
      'education transportation. Out-of-district tuition is functions 9100, 9300 and 9400 '
      'in that segment. In-district is every other account in it, less two the district’s '
      'budget book labels as English learner costs (%s), tied to the budget book by amount '
      'on every run. Reading `51` as "special education" is ours.\n'
      % ', '.join('%s, %s in %s' % (k, C.usd(v), C.fy(2026)) for k, v in m['ell'].items()))
    a('- **Spent** is expended plus encumbered at the year-end close.\n')
    a('- **Per-child figures** divide a dollar total by a headcount and are labelled OUR '
      'ESTIMATE wherever they appear.\n')
    a('- **Nothing is netted.** The circuit breaker is always its own column.\n\n')
    a('## Sources\n\n')
    for s in sources():
        a('- **%s** — %s. `%s`%s\n' % (s['publisher'], s['note'], s['path'],
                                      (' sha256 `%s`' % s['sha256'][:12]) if s['sha256'] else ''))
    a('\nGenerated by `scripts/build_sped_costs.py`; every figure in the summary is '
      'recomputed by `scripts/verify_sped_costs.py` by a different route.\n')
    return ''.join(w)


def sources():
    man = {}
    try:
        man = {r['key']: r for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    except OSError:
        pass
    out = []
    spec = [
        ('town-ledgers/expenses/glytdbud-expense-fy2026-p13-gf-school.xlsx',
         'Town of Lunenburg — Town Accountant (MUNIS)', 'munis_school_ytd',
         'the school general fund year-end budget report, FY2026 period 13; the FY2023, FY2024 '
         'and FY2025 reports sit beside it under the same name. Obtained by public records '
         'request (sources/town-ledgers/expenses/PROVENANCE-fy2023-fy2026-p13-school.md)'),
        ('town-ledgers/expenses/glytdbud-expense-fy2026-p13-special-school.xlsx',
         'Town of Lunenburg — Town Accountant (MUNIS)', 'munis_school_ytd',
         'the school special funds year-end report, FY2026 period 13, including fund 2640, the '
         'circuit breaker account; FY2023 to FY2025 beside it'),
        ('budget-workbooks/finance-committee/fy26-budget/general-fund-budget-vs-actuals-history.xlsx',
         'Lunenburg Finance Committee', 'gl-history.csv',
         'the general fund original budget, revised budget and actual, every account, '
         'FY2010-FY2025, assembled from MUNIS exports; used for FY2010-FY2022 after its school '
         'rows tie to the MUNIS reports'),
        ('state-dese/district-expenditures-by-function.xlsx', DESE_NAME,
         'dese_function_expenditure', 'End of Year Financial Report, functions 9300 and 9400, '
         'general fund and every other fund'),
        ('state-dese/dese-circuit-breaker.xlsx', DESE_NAME, 'dese_circuit_breaker',
         'the circuit breaker reimbursement schedule, by fiscal year of payment'),
        (CB_PDF, 'Lunenburg Public Schools', 'quoted',
         'Circuit Breaker Program Overview, presented to the School Committee in 2023-2024: '
         'the threshold, the share, the timing and the account, as the district describes '
         'them'),
        ('state-dese/dese-sped-program-characteristics.xlsx', DESE_NAME, 'dese_sped_program',
         'children with a plan, in district and out of district'),
        ('state-dese/dese-sped-movement.xlsx', DESE_NAME, 'dese_sped_movement',
         'children moving in and out of special education services'),
        ('state-dese/dese-ch70-district-profile.xlsx', DESE_NAME, 'dese_ch70_formula',
         'net school spending, for the reserve cap'),
        ('town-annual-reports/text/4130-fy-2025-annual-town-report.txt', 'Town of Lunenburg',
         'placement_counts', 'the FY2025 annual town report: the Special Town Meeting vote on '
         'the reserve, and the last year of the placement counts read out of every report '
         'FY2011-FY2025 (sources/data/placement-counts.csv)'),
    ]
    for key, pub, tbl, note in spec:
        r = man.get(key)
        if not r:
            fail('%s is not in archive-manifest.csv' % key)
        out.append(dict(path='sources/' + key, sha256=r.get('sha256', ''),
                        bytes=int(r.get('bytes') or 0), url=r.get('upstream', ''),
                        docs_url='/docs/' + key, filename=key.split('/')[-1], table=tbl,
                        publisher=pub, note=note))
    return out


DESE_NAME = 'Massachusetts Department of Elementary and Secondary Education'


# --------------------------------------------------------------------- the payload

def payload(m, rows):
    P = m['per']
    return dict(
        generated_by='scripts/build_sped_costs.py',
        about='How much a bad year of special education has needed beyond its voted budget, '
              'every year %s, set against the request to fund the new reserve, and how the '
              'circuit breaker account fits around it.'
              % C.fyspan(m['first'], m['last']),
        grain='DOLLARS, general fund, budget voted before the year against spending at its '
              'close, %s; every fund for %s. Children are counted separately and never '
              'netted into the dollars; every dollar-per-child figure is OUR ESTIMATE.'
              % (C.fyspan(m['first'], m['last']), C.fyspan(m['munis_first'], m['last'])),
        first_fy=m['first'], last_fy=m['last'], munis_first_fy=m['munis_first'],
        stats=[
            dict(value=C.usd(m['worst_need']['gross']), tone='var(--series-cost)',
                 label='needed beyond the voted special education budget in the worst year, '
                       '%s — general fund, after the circuit breaker account; %s'
                       % (C.fy(m['worst_need']['fy']), C.fyspan(m['first'], m['last']))),
            dict(value=C.usd(m['acct_summary']['last']['closing']),
                 label='in the circuit breaker account at 30 June %d — the school’s own '
                       'cushion beside any new reserve; %s at its %s high'
                       % (m['acct_summary']['last']['fy'],
                          C.usd(m['acct_summary']['peak']['closing']),
                          C.fy(m['acct_summary']['peak']['fy']))),
            dict(value=C.usd(m['cb_now']['paid']),
                 label='circuit breaker paid by the state in %s, for %s’s costs — into the '
                       'circuit breaker account, not the general fund'
                       % (C.fy(m['cb_now']['fy']), C.fy(m['cb_now']['for_fy']))),
            dict(value=C.usd(m['cap']),
                 label='the most the new special education reserve can hold — 2%% of %s net '
                       'school spending, as described' % C.fy(m['cap_fy'])),
        ],
        surprise=[dict(fy=r['fy'], source=r['source'],
                       ood=r['ood']['variance'], indist=r['indist']['variance'],
                       trans=r['trans']['variance'], need=n['gross'])
                  for r, n in zip(m['ledger'], m['need'])],
        surprise_keys=[dict(key=g, name=NAMES[g]) for g in GROUPS],
        ledger=m['ledger'],
        per_line={g: {k: v for k, v in m['per'][g].items()} for g in GROUPS},
        need=dict(worst=m['worst_need'], median=m['med_need'], years_needing=m['years_needing'],
                  worst_recent=m['worst_recent']),
        all_funds=m['allfunds'],
        receipts_timing=m['pairs'],
        request=dict(bases=m['bases'], thresholds=[m['T300'], m['T500']],
                     after_over_300=m['after_over_300'], before_over_300=m['before_over_300'],
                     before_within_500=m['before_within_500'], worst_before=m['worst_before'],
                     said=m['captions'], said_per_child=m['said_per_child'],
                     by_type=m['bt_recent'], nonpublic_median=m['np_recent_med'],
                     captions_note='Machine captions of the recordings: a finding aid, not a '
                                   'record. Check each at the video timestamp.'),
        cb_account=dict(years=m['acct'], snapshot=m['acct_snap'], summary=m['acct_summary']),
        circuit_breaker=dict(
            rows=m['who'],
            keys=[dict(key='gf', name='General fund'),
                  dict(key='cb_account', name='Circuit breaker account'),
                  dict(key='other', name='Other funds'),
                  dict(key='other_unsplit', name='Every non-general fund, not split')],
            lines=[dict(key='received', name='Circuit breaker received that year'),
                   dict(key='earned', name='Earned by that year’s costs, received next year')],
            basis='Bars: out-of-district tuition (functions 9300 and 9400) by fund — DESE End '
                  'of Year Financial Report, with the circuit breaker account (fund 2640) from '
                  'the town’s year-end reports where they exist; the last year is the town '
                  'ledger alone. Lines: DESE circuit breaker payments, by year of payment.',
            now=m['cb_now'], unexplained=m['big_other'],
            mechanism=dict(source='/docs/' + CB_PDF, quotes=CB_QUOTES,
                           note='The district’s description to the School Committee, '
                                '2023-2024. The statute is not in this archive.')),
        trend=m['trend'],
        averages=dict(indist=P['indist']['avg_spent'], ood_gf=P['ood']['avg_spent'],
                      trans=P['trans']['avg_spent'], combined_gf=m['combined_avg'],
                      combined_gf_recent=m['combined_avg_recent'],
                      ood_all_funds=m['ood_all_avg'], ood_all_funds_recent=m['ood_all_avg_recent'],
                      ood_all_funds_span=[m['dese_first'], m['dese_last']],
                      circuit_breaker=m['cb_avg']),
        per_child=dict(label='OUR ESTIMATE -- a net total divided by a one-day headcount; not '
                             'what a placement or a child’s services cost',
                       placed=m['per_placed'], median=m['pp_med'],
                       recent_median=m['pp_recent_med'], served=m['per_served']),
        movement=dict(snapshots=m['snap'], year_to_year=m['yoy'], services=m['move'],
                      biggest_mid_year=m['biggest_mid'], biggest_year_to_year=m['biggest_yoy']),
        reserve=dict(cap=m['cap'], cap_fy=m['cap_fy'], nss=m['cap_nss'], vote=m['vote'],
                     scenarios=m['scen'], agenda=AGENDA['quote']),
        said=m['quotes'],
        sources=sources(),
        not_established=[
            'How many children entered or left an out-of-district placement during any year, '
            'or when. Only two snapshots a few months apart are published, and they are taken '
            'by different bodies.',
            'What a single placement costs. Every per-child figure here is a total divided '
            'by a one-day count.',
            'Whether the district builds the general fund tuition line expecting the circuit '
            'breaker account to pay part of it.',
            'That segment 51 of the town’s account string means special education. It is '
            'read from the account names; the chart of accounts is not published.',
            'The terms of Mass. General Laws chapter 40 section 13E as written, and how much '
            'the new reserve holds.',
            'Why DESE’s FY2024 figure for tuition paid from funds other than the general fund '
            'exceeds what the circuit breaker account paid by exactly the circuit breaker '
            'payment the state lists for FY2024.',
            'Whether the voted tuition line is set net of expected circuit breaker money '
            '(the district’s budget narrative for the tuition line would say), and how much of '
            'the circuit breaker balance is earmarked for the next year (its spending plan '
            'would say).',
            'How many children ARRIVED in an out-of-district placement during any year; every '
            'figure here is net of departures and other savings.',
            'Any cost by type of placement: the counts and the dollars split by type do not '
            'line up.',
            'The circuit breaker mechanism as the statute states it. The threshold, the share '
            'and the timing here are the district’s description to the School Committee.',
        ],
        conclusions=rows,
    )


# --------------------------------------------------------------------- the SVGs, for /docs and the PDF

COL = {'ood': '#2a78d6', 'indist': '#eb6834', 'trans': '#a3357f',
       'ood_all': '#12428f', 'cb': '#0ca30c'}


def svg_surprise(pay):
    rows = pay['surprise']
    W, H, L, R, T, B = 780, 380, 70, 16, 34, 40
    vals = [r[g] for r in rows for g in GROUPS]
    lo, hi = min(vals), max(vals)
    step = 100000
    lo, hi = (lo // step) * step, -((-hi) // step) * step
    y = lambda v: T + (H - T - B) * (hi - v) / (hi - lo)
    slot = (W - L - R) / len(rows)
    bw = slot * 0.26
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" font-family="system-ui,'
         'sans-serif" font-size="11"><rect width="100%%" height="100%%" fill="#ffffff"/>' % (W, H)]
    v = lo
    while v <= hi:
        o.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="%s"/>'
                 '<text x="%d" y="%.1f" text-anchor="end" fill="#6b7280">%s</text>'
                 % (L, W - R, y(v), y(v), '#6b7280' if v == 0 else '#e5e7eb', L - 6, y(v) + 4,
                    html.escape(C.usd(v))))
        v += step
    for j, r in enumerate(rows):
        x0 = L + slot * j + slot * 0.11
        for k, g in enumerate(GROUPS):
            val = r[g]
            top, bot = (y(val), y(0)) if val >= 0 else (y(0), y(val))
            o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                     % (x0 + k * bw, top, bw - 1, max(0.5, bot - top), COL[g]))
        o.append('<text x="%.1f" y="%d" text-anchor="middle" fill="#6b7280">%s</text>'
                 % (L + slot * (j + 0.5), H - 22, "FY'%02d" % (r['fy'] % 100)))
    x = L
    for g in GROUPS:
        o.append('<rect x="%d" y="10" width="10" height="10" fill="%s"/><text x="%d" y="19" '
                 'fill="#111827">%s</text>' % (x, COL[g], x + 14, html.escape(NAMES[g])))
        x += 14 + 7 * len(NAMES[g]) + 18
    o.append('<text x="%d" y="%d" fill="#6b7280">spent minus the budget voted before the '
             'year; above zero is an overrun. %s</text>'
             % (L, H - 6, html.escape(C.fyspan(rows[0]['fy'], rows[-1]['fy']))))
    o.append('</svg>\n')
    return ''.join(o)


def svg_trend(pay):
    pts = pay['trend']
    keys = [('indist_spent', 'In district, general fund', COL['indist']),
            ('ood_gf_spent', 'Tuition, general fund', COL['ood']),
            ('ood_all_funds', 'Tuition, every fund (DESE)', COL['ood_all']),
            ('cb_paid', 'Circuit breaker paid', COL['cb'])]
    W, H, L, R, T, B = 780, 380, 80, 190, 16, 36
    vals = [p[k] for p in pts for k, _, _ in keys if p.get(k) is not None]
    hi = -((-max(vals)) // 500000) * 500000
    x = lambda i: L + (W - L - R) * i / (len(pts) - 1)
    y = lambda v: T + (H - T - B) * (1 - v / hi)
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" font-family="system-ui,'
         'sans-serif" font-size="11"><rect width="100%%" height="100%%" fill="#ffffff"/>' % (W, H)]
    v = 0
    while v <= hi:
        o.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#e5e7eb"/>'
                 '<text x="%d" y="%.1f" text-anchor="end" fill="#6b7280">%s</text>'
                 % (L, W - R, y(v), y(v), L - 6, y(v) + 4, html.escape(C.usd(v))))
        v += 500000
    for j, p in enumerate(pts):
        if j % 2 == 0 or j == len(pts) - 1:
            o.append('<text x="%.1f" y="%d" text-anchor="middle" fill="#6b7280">%s</text>'
                     % (x(j), H - 14, "FY'%02d" % (p['fy'] % 100)))
    labels = []
    for k, name, col in keys:
        seq = [(j, p[k]) for j, p in enumerate(pts) if p.get(k) is not None]
        d = ' '.join('%s%.1f,%.1f' % ('M' if n == 0 else 'L', x(j), y(val))
                     for n, (j, val) in enumerate(seq))
        o.append('<path d="%s" fill="none" stroke="%s" stroke-width="2.2"/>' % (d, col))
        labels.append([y(seq[-1][1]), name, col])
    labels.sort()
    for n in range(1, len(labels)):
        if labels[n][0] - labels[n - 1][0] < 14:
            labels[n][0] = labels[n - 1][0] + 14
    for yy, name, col in labels:
        o.append('<text x="%d" y="%.1f" fill="%s">%s</text>' % (W - R + 6, yy + 4, col,
                                                                html.escape(name)))
    o.append('</svg>\n')
    return ''.join(o)


def svg_cb(pay):
    cb = pay['circuit_breaker']
    rows = cb['rows']
    stack = [('gf', COL['ood']), ('cb_account', COL['cb']), ('other', '#9ca3af'),
             ('other_unsplit', '#cbd5e1')]
    W, H, L, R, T, B = 780, 400, 74, 16, 52, 40
    tops = [sum(r[k] or 0 for k, _ in stack) for r in rows]
    tops += [r[k] for r in rows for k in ('received', 'earned') if r[k] is not None]
    hi = -((-max(tops)) // 500000) * 500000
    y = lambda v: T + (H - T - B) * (1 - v / hi)
    slot = (W - L - R) / len(rows)
    cx = lambda j: L + slot * (j + 0.5)
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" font-family="system-ui,'
         'sans-serif" font-size="11"><rect width="100%%" height="100%%" fill="#ffffff"/>' % (W, H)]
    v = 0
    while v <= hi:
        o.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#e5e7eb"/>'
                 '<text x="%d" y="%.1f" text-anchor="end" fill="#6b7280">%s</text>'
                 % (L, W - R, y(v), y(v), L - 6, y(v) + 4, html.escape(C.usd(v))))
        v += 500000
    for j, r in enumerate(rows):
        base = 0
        for k, col in stack:
            val = r[k] or 0
            if val:
                o.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                         % (cx(j) - slot * 0.32, y(base + val), slot * 0.64,
                            y(base) - y(base + val), col))
            base += val
        o.append('<text x="%.1f" y="%d" text-anchor="middle" fill="#6b7280">%s</text>'
                 % (cx(j), H - 22, "FY'%02d" % (r['fy'] % 100)))
    for k, dash_ in (('received', ''), ('earned', ' stroke-dasharray="5 4"')):
        seq = [(j, r[k]) for j, r in enumerate(rows) if r[k] is not None]
        d = ' '.join('%s%.1f,%.1f' % ('M' if n == 0 else 'L', cx(j), y(val))
                     for n, (j, val) in enumerate(seq))
        o.append('<path d="%s" fill="none" stroke="#111827" stroke-width="2"%s/>' % (d, dash_))
    x = L
    names = {k['key']: k['name'] for k in cb['keys']}
    for k, col in stack:
        o.append('<rect x="%d" y="8" width="10" height="10" fill="%s"/><text x="%d" y="17" '
                 'fill="#111827">%s</text>' % (x, col, x + 14, html.escape(names[k])))
        x += 14 + 6 * len(names[k]) + 16
    x = L
    for ln, dash_ in zip(cb['lines'], ('', ' stroke-dasharray="5 4"')):
        o.append('<line x1="%d" x2="%d" y1="32" y2="32" stroke="#111827" stroke-width="2"%s/>'
                 '<text x="%d" y="36" fill="#111827">%s</text>'
                 % (x, x + 18, dash_, x + 24, html.escape(ln['name'])))
        x += 24 + 6 * len(ln['name']) + 22
    o.append('<text x="%d" y="%d" fill="#6b7280">out-of-district tuition by who paid it; lines '
             'are the state&#8217;s circuit breaker payments. %s</text>'
             % (L, H - 6, html.escape(C.fyspan(rows[0]['fy'], rows[-1]['fy']))))
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
        os.path.join(CHART_DIR, '%s-surprise.svg' % ID): svg_surprise(pay),
        os.path.join(CHART_DIR, '%s-trend.svg' % ID): svg_trend(pay),
        os.path.join(CHART_DIR, '%s-circuit-breaker.svg' % ID): svg_cb(pay),
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
