#!/usr/bin/env python3
"""The 4 September 2026 MUNIS records request, as the RUNS the Town would make.

    python3 scripts/build_munis_request_runs_pdf.py          # writes the PDF
    python3 scripts/build_munis_request_runs_pdf.py --check  # inputs still say what the PDF says

Writes notes/outbound/drafts/MUNIS-REQUEST-RUNS.pdf: one row per run of a MUNIS program,
most useful first, with the screen, the values to set, the boxes to check and uncheck, and
the guide page that shows each one.

TJ, 6 October 2026: *"i want to basically give them the exact munis options to use ...
multi-year and multi-fund reports can be done at one time. what can't be done at once, i
think, is the journal vs not journal."* MUNIS-REQUEST-FUNDS.xlsx lays the request out fund by
fund; this lays it out run by run, which is the shape the Town actually works in.

EVERY OPTION CARRIES A CITATION, AND THE CITATION IS CHECKED. Lunenburg publishes no MUNIS
guide, so the option names come from four other governments' guides held in
sources/peer-districts/, and from the options pages of the Town's own reports we hold. Each
citation below is a (source, page, quoted text) triple; the build refuses to write if a
quoted phrase is not on the page it is cited to (rule 13: quote the source, never your
rendering of it). Options read off a SCREENSHOT carry no text to assert and are marked
`(screenshot)` on the page, so a reader knows which ones were checked by eye.

--check rebuilds every assertion from the inputs and compares the digest of the result with
the digest printed on the PDF, so a moved input or an edited row is caught without needing
Chrome. The PDF itself is printed by Chrome, as build_analysis_pdf.py does: no new
dependency.

EVERY RUN ALSO CARRIES A STATUS against the 6 October 2026 delivery (Part 1 of the 4
September request), computed by calling `delivered()` in build_munis_request_xlsx.py rather
than re-deriving it — one place for the rule, so this PDF and MUNIS-REQUEST-FUNDS.xlsx's
"Report runs" sheet cannot disagree about what has arrived.
"""
import argparse
import csv
import hashlib
import html
import os
import re
import subprocess
import sys
from datetime import date

import openpyxl

import build_munis_request_xlsx as xlsx_mod

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'notes', 'outbound', 'drafts', 'MUNIS-REQUEST-RUNS.pdf')
REQUEST = os.path.join(ROOT, 'notes', 'outbound', 'drafts', 'RECORDS-REQUEST-TOWN-ACCOUNTANT.md')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
SPECREV = os.path.join(ROOT, 'sources', 'town-ledgers', 'fund-balances', 'special-revenue-fy2026-p09.xlsx')

CHROME = next((p for p in (
    os.environ.get('CHROME'),
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome',
) if p and os.path.exists(p)), None)

# --------------------------------------------------------------------------- the sources
GUIDES = {
    'C': ('peer-districts/munis-guide-cnmi-inquiries-reports',
          'CNMI Department of Finance, MUNIS reference guide “Inquiries & Reports”',
          'https://www.finance.gov.mp/support/document-library/documents/munis-rg-inquiries-reports.pdf'),
    'F': ('peer-districts/munis-guide-framingham-general-ledger-2020-2',
          'Tyler, Munis General Ledger procedural documentation, version 2020.2 (as served by the City of Framingham, MA)',
          'https://www.framinghamma.gov/DocumentCenter/View/44403/General-Ledger'),
    'B': ('peer-districts/munis-guide-burlingame-overview',
          'City of Burlingame, CA, “Tyler Munis Basic User Guide 1 – Overview”',
          'https://cms7files.revize.com/burlingameintranet/Finance/Tyler%20Munis/User%20Reference%20Guides/'
          'Tyler%20Munis%20Basic%20User%20Guide%201%20-%20Overview.pdf'),
    'L': ('peer-districts/munis-guide-livingston-payroll-reports',
          'Livingston County, “Instructions for MUNIS Payroll reports” (cited only for its generic export steps)',
          'https://milivcounty.gov/wp-content/uploads/Instructions-MUNIS-Payroll-Reports-0823.pdf'),
}
FY24_SCHOOL = ('budget-workbooks/finance-committee/fy26-budget/department-presentations/'
               'lunenburg-public-schools/school-budget-files-amanda-moore-foia-request-to-school-dept/')
# The Town's own reports, as held. Each is (path under sources/, what it is).
HELD = {
    'p09': ('town-ledgers/expenses/glytdbud-expense-fy2026-p09-gf-all.txt',
            'the Town’s FY2026 period 9 YTD Budget Report, general fund, options page'),
    'p12': ('town-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.txt',
            'the Town’s FY2026 period 12 YTD Budget Report, printed'),
    'p12x': ('town-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.xlsx',
             'the same report as the Town’s Excel export, sheet ACCOUNT DETAIL'),
    'peg': ('town-ledgers/expenses/glytdbud-expense-fy2026-p09-ef-peg-access.txt',
            'the Town’s FY2026 period 9 YTD Budget Report, PEG Access fund'),
    'fy24': (FY24_SCHOOL + 'text/fy24-ytd-school.pdf.txt',
             'the school department’s FY2024 period 13 YTD Budget Report, run 08/07/2024'),
    'fy23': (FY24_SCHOOL + 'text/ytd-school-budget-fy23.pdf.txt',
             'the school department’s FY2023 period 12 YTD Budget Report, run 02/28/2024'),
    'rev': ('town-ledgers/revenue/glytdbud-revenue-fy2026-p09-gf-all.txt',
            'the Town’s FY2026 period 9 YTD Budget Report, general fund revenue'),
    'fy20': ('budget-workbooks/finance-committee/fy20-budget/text/fy20-4th-quarter-summary-and-reports-1.pdf.txt',
             'the Town’s FY2020 4th-quarter revenue report, as extracted (under “31 DEPT REV - SCHOOL” the account '
             'numbers and the labels come out as two separate lists, paired here by order)'),
    'tb': ('town-ledgers/account-details/account-details-fy2026-trial-balance-fund1300.xlsx',
           'the FY2026 Account Trial Balance for fund 1300 the Town sent on 6 October 2026'),
    'ad': ('town-ledgers/account-details/account-details-fy2025-fund1301.xlsx',
           'the Account Detail export the Town sent in June 2026, sheet Journal Detail Export'),
}
VIDEO = {
    # Read from YouTube's oEmbed endpoint on 6 October 2026. Not downloaded.
    'title': 'Browse and Export to Excel - Munis 101.07',
    'channel': 'Professor Finance',
    'url': 'https://www.youtube.com/watch?v=rRJg-ICfQyI&t=346s',
    'at': '5:46',
}
SRC = os.path.join(ROOT, 'sources')

# --------------------------------------------------------------------------- delivery status
# TJ, 6 October 2026: "i want basically to see what she has already done." `delivered()` is the
# one place that knows what the 6 October delivery holds (sources/data/munis-school-ytd.csv);
# imported rather than re-derived, so a status here and in MUNIS-REQUEST-FUNDS.xlsx cannot drift
# apart.
GOT = xlsx_mod.delivered()
TB_EXISTS = xlsx_mod.TB.exists()
DELIVERED_HUMAN = date.fromisoformat(xlsx_mod.DELIVERED_ON).strftime('%-d %b %Y')


def _span(fys):
    fys = sorted(fys)
    return f'FY{fys[0]}' if len(fys) <= 1 else f'FY{fys[0]}–FY{fys[-1]}'


def run_status(report, funds):
    """('received'|'partial'|'needed', detail) for one run, computed from the same delivered()
    data the spreadsheet's "Report runs" sheet reads. `detail` is empty for 'needed': nothing
    arrived, nothing to explain."""
    if report.startswith('Every school transaction'):
        held_years = [fy for (f, item, fy) in xlsx_mod.HELD if f == '1301' and item == '2']
        if held_years and TB_EXISTS:
            return ('partial',
                    f'Fund 1301 (athletics), {_span(held_years)}, already held (received before this request, Jun '
                    f'2026). Fund 1300 FY2026 received {DELIVERED_HUMAN} as a trial balance with journal lines, '
                    'not the full Account Detail export. Every other fund, and fund 1300 for earlier years, still '
                    'needed.')
        return ('needed', '')
    if report.startswith('Year-end position'):
        d300 = [fy for fy in xlsx_mod.YEARS if ('0100/300', fy) in GOT]
        d301 = any(('0100/301', fy) in GOT for fy in xlsx_mod.YEARS)
        all_fys = [fy for fy in xlsx_mod.YEARS if all((f, fy) in GOT for f in funds)]
        if d300 and all_fys and not d301:
            return ('partial',
                    f'School department 300, {_span(d300)}, and all {len(funds)} school funds, {_span(all_fys)}, '
                    f'expense only, received {DELIVERED_HUMAN}. Department 301, every other town department, and '
                    'general-fund revenue still needed.')
        return ('needed', '')
    return ('needed', '')


def norm(s):
    s = s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    return re.sub(r'\s+', ' ', s).strip().lower()


def pages(key):
    txt = open(os.path.join(SRC, GUIDES[key][0] + '.txt'), encoding='utf-8').read()
    parts = re.split(r'===PAGE (\d+)===', txt)
    return {int(parts[i]): norm(parts[i + 1]) for i in range(1, len(parts), 2)}


PAGES = {}
PROBLEMS = []
USED = set()


def c(key, page, quote=None, shot=None):
    """A citation. `quote` must be on that page of that guide; `shot` names what a
    screenshot shows, which no text layer carries, and is marked as such."""
    if key not in PAGES:
        PAGES[key] = pages(key)
    if quote is not None and norm(quote) not in PAGES[key].get(page, ''):
        PROBLEMS.append(f'{key}{page}: not on the page: {quote!r}')
    USED.add(key)
    return f'{key}{page}' + (' (screenshot)' if shot else '')


_HELD_TEXT = {}


def h(key, quote):
    """A quotation from one of the Town's own reports we hold."""
    path = os.path.join(SRC, HELD[key][0])
    if path.endswith('.xlsx'):
        if key not in _HELD_TEXT:
            wb = openpyxl.load_workbook(path, read_only=True)
            ws = wb.worksheets[0]
            cells = [ws.title]
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                cells += [str(v) for v in row if v is not None]
                if i > 400:
                    break
            _HELD_TEXT[key] = norm(' | '.join(cells))
    elif key not in _HELD_TEXT:
        _HELD_TEXT[key] = norm(open(path, encoding='utf-8').read())
    if norm(quote) not in _HELD_TEXT[key]:
        PROBLEMS.append(f'held {key}: not in {HELD[key][0]}: {quote!r}')
    USED.add('H')
    return f'H:{key}'


# --------------------------------------------------------------------------- the inputs
def request_lists():
    text = open(REQUEST, encoding='utf-8').read()
    funds = dict(re.findall(r"\*\*(\d{4})\*\* \| ([^|]+?) \|", text))
    accounts = re.findall(r"\| `0100-01001-(\d{6})` \| ([^|]+?) \| ([\d,]+) \|", text)
    if len(funds) != 61 or len(accounts) != 10:
        PROBLEMS.append(f'request parse: {len(funds)} funds, {len(accounts)} revenue accounts; expected 61 and 10')
    return funds, accounts


def school_sweep(funds):
    """Funds a single Fund range across the school funds would sweep in that are not
    school funds: those in the FY26 special revenue report with no account in department
    300 or 301."""
    ws = openpyxl.load_workbook(SPECREV, data_only=True, read_only=True).worksheets[0]
    depts = {}
    for i, r in enumerate(ws.iter_rows(values_only=True), 1):
        if i > 8 and r[0] is not None:
            depts.setdefault(str(r[0]).strip().strip("'"), set()).add(r[2])
    lo, hi = min(funds), max(funds)
    others = sorted(f for f, d in depts.items() if lo <= f <= hi and not d & {300, 301})
    not_school = [f for f in funds if not depts.get(f, set()) & {300, 301}]
    if not_school:
        PROBLEMS.append(f'request funds with no department 300/301 account: {not_school}')
    return lo, hi, others


def fy24_funds():
    path = os.path.join(SRC, HELD['fy24'][0])
    return sorted(set(re.findall(r'^(\d{4}) [A-Z]', open(path, encoding='utf-8').read(), re.M)))


def gap(prefix):
    for r in GAP_ROWS:
        if r['what'].startswith(prefix):
            return r['what']
    PROBLEMS.append(f'money-gaps.csv: no row beginning {prefix!r}')
    return prefix


def guide_hashes():
    with open(MANIFEST, newline='') as fh:
        m = {r['key']: r['sha256'] for r in csv.DictReader(fh)}
    out = {}
    for k, (base, _, _) in GUIDES.items():
        key = base + '.pdf'
        if key not in m:
            PROBLEMS.append(f'{key} is not in the archive manifest')
            continue
        have = hashlib.sha256(open(os.path.join(SRC, key), 'rb').read()).hexdigest()
        if have != m[key]:
            PROBLEMS.append(f'{key}: sha256 {have[:12]} on disk, {m[key][:12]} in the manifest')
        out[k] = m[key]
    return out


GAP_ROWS = list(csv.DictReader(open(GAPS, encoding='utf-8')))


# --------------------------------------------------------------------------- the runs
def build_runs(funds, accounts):
    path_ytd = ('Financials > General Ledger Menu > Inquiries and Reports > YTD Budget Report',
                [c('C', 7, 'Go to Financials>General ledger Menu>Inquiries and Reports>YTD Budget Report'),
                 c('F', 94, 'Financials > General Ledger Menu > Inquiries and Reports > YTD Budget Report')])
    prog = ('Program ID glytdbud, as the Town’s reports print it', [h('p09', 'Program ID: glytdbud')])
    school_sel = [
        ('Search (or Seg Find): leave every field blank except —', [
            c('C', 7, 'Enter Org Code or leave blank for wide open search'),
            c('F', 79, 'For either search method, the program creates an active set of all accounts matching your search criteria')]),
        ('Department = 300|301  (Fund blank: every fund)', [
            c('B', 8, '710|720'), h('p09', 'Department'),
            h('fy24', 'ACCOUNTS FOR: 300 SCHOOL DEPARTMENT'),
            h('fy24', 'ACCOUNTS FOR: 301 SCHOOL NON-RECURRING EXPENSES')]),
        ('Account type = blank (expense AND revenue)', [
            c('C', 7, 'Account type: Select from drop down or leave blank for wide open search'),
            c('F', 94, 'You can select the blank option to include all account types')]),
    ]
    town_sel = [
        ('Search: leave EVERY field blank — the whole town, every fund', [
            c('C', 7, 'Enter Org Code or leave blank for wide open search'),
            c('C', 7, 'Enter Object Code or leave blank for wide open search')]),
        ('Account type = blank (expense AND revenue)', [
            c('C', 7, 'Account type: Select from drop down or leave blank for wide open search'),
            c('F', 94, 'You can select the blank option to include all account types')]),
    ]
    summary_set = [
        ('Execute this report = Now', [c('C', 7, 'Execute this report: Select from drop down (Most common option is Now)')]),
        ('Sequence 1 = Fund, Total ✓;  Sequence 2 = Department, Total ✓  (as the Town runs it)', [
            c('C', 8, 'Sequence 1: Use drop down and select Fund'),
            h('p09', 'Sequence 1 1 Y Y'), h('p09', 'Sequence 2 3 Y N')]),
        ('Order accounts by = full account', [c('F', 98, 'org/object/project or full account')]),
        ('Account description = Full', [c('C', 8, 'Account description: Use drop down and select Full'),
                                         c('F', 98, 'Determines the description that prints next to the account: full or short')]),
        ('Year/period = Within year/period, YYYY / 13', [
            c('C', 9, 'Year/Period: Use drop down and select Within year/period'),
            c('F', 98, 'If you select Within Year/Period, you must specify a fiscal year and period')]),
        ('Carry forward = Totals (GAAP)', [c('C', 9, 'Carry forward: Use drop down and select Totals (GAAP)'),
                                           c('F', 99, 'Totals (GAAP)— Includes current year and carry forward activity')]),
        ('Format type = Cents in Budget Amount', [c('F', 100, 'Standard or Cents in Budget Amount')]),
    ]
    summary_check = [
        ('Print full GL account  (C’s walkthrough leaves it off; the full number is needed)', [
            c('F', 98, 'Directs the report to print the full account number, if selected'),
                                   c('C', 8, 'Uncheck Print full GL account')]),
        ('Print report options', [c('C', 8, 'Check report options'),
                                  c('F', 98, 'append the search criteria and report option settings at the end of the report')]),
    ]
    summary_uncheck = [
        ('Totals only', [c('C', 8, 'Uncheck Totals only'),
                         c('F', 98, 'This option is only accessible when the Totals Only check box is not selected')]),
        ('Suppress zero bal accts  (C’s walkthrough checks it; every account is wanted)', [c('F', 100, 'Directs the report to exclude accounts that meet the following conditions')]),
        ('Exclude YEC journals', [c('C', 9, 'Uncheck Exclude YEC journals'),
                                  c('F', 100, 'Excludes period 13 year-end-close journals')]),
        ('Include requisition amounts', [c('C', 9, 'Uncheck requisition amounts if applicable')]),
        ('Print journal detail', [c('C', 10, 'Check Print Journal detail')]),
    ]
    detail_set = summary_set[:4] + [
        ('Year/period = Within year/period, 2026 / 13', [
            c('C', 9, 'Year/Period: Use drop down and select Within year/period')]),
        summary_set[5], summary_set[6],
        ('From Yr/Per = 2023 / 0   To Yr/Per = 2026 / 13', [
            c('C', 10, 'From Yr/Per: Choose the Yr/Pr you want to start the detail from'),
            c('F', 102, 'Define the range of years and periods for which to include account detail on the report'),
            c('F', 101, 'To include the SOY journal entries, you must use a starting period of 0')]),
        ('Sort option = Journal entries', [c('C', 10, 'Sort option: Use drop down and select Journal Entries')]),
        ('Detail format option = Standard', [c('C', 10, 'Detail format option: Use drop down and select Standard format'),
                                             c('F', 102, 'Standard—A standard report where journal detail is presented as is')]),
        ('Multiyear view = Default view', [c('C', 10, 'Multiyear view: Use drop down and select Default view')]),
        ('Journal Entry Sort pop-up (AP journals) = 3', [c('C', 11, 'Select 3 if applicable', shot='(3) Invoice')]),
    ]
    detail_check = summary_check + [
        ('Print journal detail', [c('C', 10, 'Check Print Journal detail'),
                                  c('F', 101, 'prints these detail lines for each account')]),
        ('Include budget entries  (the transfers)', [c('C', 10, 'Check Include budget entries'),
                                                     c('F', 101, 'Causes transaction type 5 journal entries to be included')]),
        ('Include encumb/liq entries  (the POs)', [c('C', 10, 'Check encumb/liq entries'),
                                                   c('F', 101, 'Includes transaction type 4 (encumbrance) journal entries')]),
        ('Include additional JE comments  (C’s walkthrough leaves it off; the comments are wanted)', [c('F', 102, 'Prints journal entry comments on the report, if selected'),
                                            c('C', 10, 'Uncheck Include additional JE comments')]),
    ]
    detail_uncheck = summary_uncheck[:4]

    lo, hi, others = school_sweep(funds)
    objects = '|'.join(a for a, _, _ in accounts)
    f24 = fy24_funds()

    runs = []

    def run(**kw):
        kw['n'] = len(runs) + 1
        runs.append(kw)
        return kw

    run(report='Every school transaction, all funds, FY2023–FY2026',
        program='YTD Budget Report, with journal detail',
        answers=['The transactions behind every school line: a price rise told apart from more bought (request item 2).',
                 'What each grant and revolving fund paid for, by object.',
                 'What each budget transfer moved, from which line to which (item 3).',
                 'Purchase orders liquidated after 30 June (item 5).'],
        gaps=[gap('Which budget line each dollar of grant and revolving money paid for'),
              gap("Why the school department's FY2024 actual spending differs"),
              gap('Whether a general fund athletics line is net of the revolving fund'),
              gap('Which fund and account each field-rental receipt'),
              gap('What put $62,231 into the School Facilities Use fund'),
              gap('Whether a rise in the paraprofessional line is more posts or a grant unwinding'),
              gap('Why a budget line came in under plan, as against by how much')],
        path=[path_ytd, prog], select=school_sel, set=detail_set, check=detail_check, uncheck=detail_uncheck,
        years=[('ONE run, FY2023 to FY2026, if the From/To range may span four years.', [
                    c('F', 102, 'Typically, this would reflect one month\'s detail, but it could be year-to-date')]),
               ('If it may not: one run per year, newest first — From YYYY/0 To YYYY/13, Year/period YYYY/13.', []),
               ('Special-education accounts: request item 2’s exception still applies — vendor number rather than name.', [])],
        output='Excel and PDF — see “Getting it out as Excel”.')
    run(report='Year-end position, every account, FY2023–FY2026 (period 13 each)',
        program='YTD Budget Report, summary',
        answers=['The final position of every account at each year’s close: budget, transfers, spent, left — '
                 'every school account, every school fund, every town department.'],
        # What is already held is in the Status column, computed from the delivered data;
        # the lines that said "we hold period 12" here were true until 6 October 2026 and
        # sat beside a status saying period 13 had arrived.
        gaps=[gap('What the schools actually spent, per line, in any year before FY2026'),
              gap('What each town department was appropriated and spent in FY2024 and FY2025'),
              gap('Which departments’ unspent appropriations produced the free cash'),
              gap('Whether a school line that stops appearing in the district'),
              gap("Why the school department's FY2024 actual spending differs")],
        path=[path_ytd, prog],
        select=town_sel,
        set=[(t, cs) for t, cs in summary_set if not t.startswith('Year/period')] + [
            ('Year/period: if your screen allows several years in one report, ONE run covering FY2023–FY2026 at '
             'period 13. Otherwise one run per year, newest first: 2026/13, 2025/13, 2023/13, 2024/13.', [
                c('C', 9, 'Year/Period: Use drop down and select Within year/period'),
                c('F', 98, 'If you select Within Year/Period, you must specify a fiscal year and period')]),
            ('The guides show one year per run; TJ has seen a multi-year run demonstrated, so ask for the combined '
             'report first.', [c('F', 98, 'you must specify a fiscal year and period')])],
        check=summary_check, uncheck=summary_uncheck,
        years=[('Combined first; if not possible, four runs: 2026/13, 2025/13, 2023/13, 2024/13.', []),
               ('FY2023, ask first: the report reaches “three years ago” at most. FY2023 is three years before 2026 and '
                'four before 2027, so it may already be out of reach if MUNIS has rolled to 2027.', [
                    c('F', 98, 'last year, two years ago, or three years ago'),
                    c('F', 99, 'For 2 and 3 years prior, the report may only be run for periods 1–13'),
                    c('C', 7, 'Reporting periods may range from three years prior to the following year')]),
               ('Narrower is fine: Department 300|301 for the school — but then the general fund revenue '
                'accounts drop out, and need Fund 0100 with Account type Revenue added as a run of their own.', [])],
        output='Excel and PDF.')
    NAMES = [('450600', 'CH 70 AID'), ('451400', 'UGGA'), ('450500', 'ABATE ELDE'), ('452600', 'MEALS TAX'),
             ('431900', 'PS TUITION'), ('473000', 'SPED REIMB'), ('452000', 'S6CH115VET'), ('450100', 'STATE LAND'),
             ('451100', 'CHARTER'), ('451800', 'RM OCC EXC')]
    if [o for o, _ in NAMES] != [a for a, _, _ in accounts]:
        PROBLEMS.append('the ten revenue accounts no longer match the request, in order')
    # TJ, 6 October 2026: isolate the school-related accounts. Chapter 70 and charter reimbursement from the
    # request, plus the Town's own FY2020 'DEPT REV - SCHOOL' and 'MSBA REIMBURSEMENT' headings.
    NAMES = [('450600', 'CH 70 AID'), ('451100', 'CHARTER'), ('431900', 'PS TUITION'),
             ('437400', 'PARKINGFEE'), ('473000', 'SPED REIMB'), ('450700', 'MSBA REIMB')]
    FY20 = {'431900': 'PRE-SCHOOL TUITION', '437400': 'STUDENT PARKING FE',
            '473000': 'MEDICAL ASSIST/SPE — Medicaid reimbursement, not the circuit breaker; label truncated',
            '450700': 'MSBA REIMB - SCHOO'}
    objects = '|'.join(o for o, _ in NAMES)
    fy20_cites = [h('fy20', '30 MSBA REIMBURSEMENT'), h('fy20', '01001 450700 MSBA REIMB - SCHOO'),
                  h('fy20', '31 DEPT REV - SCHOOL'),
                  h('fy20', '01001 431900 01001 437400 01001 473000 PRE-SCHOOL TUITION STUDENT PARKING FE MEDICAL ASSIST/SPE')]
    name_cites = [h('rev', '001 REVENUES')] + [h('rev', f'01001 {o} {n}') for o, n in NAMES]
    run(report='Every transaction on the school-related general fund revenue accounts, FY2023–FY2026',
        program='YTD Budget Report, with journal detail',
        answers=['How state aid and the other receipts arrived, and when (request item 2(c)).',
                 'Whether any receipt carries a reference tying it to what it paid for (the request’s one question).',
                 'The six, as the Town prints them in FY2026 (fund 0100, org 01001, under “001 REVENUES”): 0100-01001-'
                 + '; '.join(f'{o} {n}' + (f' (FY20: {FY20[o]})' if o in FY20 else '') for o, n in NAMES) + '.',
                 'The four department-revenue and MSBA accounts are the Town’s own “DEPT REV - SCHOOL” and '
                 '“MSBA REIMBURSEMENT” headings (FY2020 Q4 report) [H:fy20].'],
        gaps=[],
        path=[('As run 1.', [])],
        select=[('Fund = 0100', [h('p09', 'Fund 0100')]),
                ('Account type = Revenue', [c('F', 94, 'Indicates the type of account: revenue or expense')]),
                (f'Object = {objects}', [c('B', 8, '710|720'),
                                         c('B', 8, 'not all are available in all fields')] + name_cites + fy20_cites),
                ('(or Object blank: all general fund revenue — fine too)', [])],
        set=[('As run 1.', [])], check=[('As run 1.', [])], uncheck=[('As run 1.', [])],
        years=[('As run 1: one run if the range may span the years.', [])],
        output='Excel and PDF.')

    range_cites = [c('B', 8, '11500001:11500010'), c('B', 8, '11500001..11500010'), c('B', 8, '710|720'),
                   c('B', 8, 'not all are available in all fields')]
    years_po = [('ONE run for PO fiscal years 2023–2026, if the year box takes a range. The guide’s own caveat: '
                 '“not all are available in all fields”.', range_cites),
                ('Otherwise one run per PO fiscal year, newest first: 2026, 2025, 2024, 2023.', [])]
    run(report='History of every PO of PO fiscal years 2023–2026',
        program='PO Audit Report (screen title: Audit File PO History)',
        answers=['The date each PO changed — when it was received, liquidated or closed, including after 30 June '
                 '(item 5: “and dates”).'],
        gaps=[],
        path=[('Financials > Purchasing > PO Inquiry and Reports Menu > Standard PO Reports > PO Audit Report', [
            c('C', 23, 'prints a range of purchase orders showing historical information from purchase order entry through liquidation'),
            c('C', 23, "Open 'PO Audit Report' Financials > Purchasing > PO Inquiry and Reports Menu > Standard PO Reports")]),
              ('Program ID poreport', [c('C', 24, 'poreport')])],
        select=[('No account fields on this screen: it covers every Town PO of the years.', [c('C', 24, 'Inclusion Options')]),
                ('POs = 00000000 to 99999999', [c('C', 24, '00000000')])],
        set=[('PO fiscal year = 2023:2026  (or 2023..2026, or 2023|2024|2025|2026)', [c('C', 24, 'PO fiscal year')] + range_cites),
             ('Audit date = 07/01/2022 to the day it is run', [c('C', 24, 'Audit date')])],
        check=[('Include carry forward POs', [c('C', 24, 'Include carry forward POs'),
                                              c('C', 23, 'Carryforward purchase orders may be included')])],
        uncheck=[('Do NOT press Purge.', [c('C', 24, 'Purge')]),
                 ('Please say whether PO history has ever been purged, and through what date: the guide says this report '
                  '“can be used periodically to purge old history records”. If it has, the early years may be gone.', [
                     c('C', 23, 'This option can be used periodically to purge old history records')])],
        years=years_po, output='Excel (toolbar).')

    run(report='OPTIONAL — open and closed balances of every school PO, PO fiscal years 2023–2026',
        program='Encumbrance by PO Number (screen title: Open Encumbrance by PO Number)',
        answers=['Only if easy — the audit report above carries the history; this adds original vs remaining per PO, '
                 'by account (item 5).'],
        gaps=[],
        path=[('Financials > Purchasing > PO Inquiry and Reports Menu > Standard PO Reports > Encumbrance by PO Number', [
            c('C', 25, 'This report displays the original ordered amount and the remaining open balance of a PO based on PO number'),
            c('C', 25, 'Financials > Purchasing > PO Inquiry and Reports Menu > Standard PO Reports')])],
        select=[('Department = 300 to 301  (this screen takes from/to ranges)', [c('C', 25, shot='Department … to')]),
                ('POs = 00000000 to 99999999', [c('C', 25, shot='POs')])],
        set=[('Report = Detail', [c('C', 25, 'You may choose to print a summary or detail report')]),
             ('PO fiscal year = 2023:2026  (the drop-down beside the year is not explained in the guide)',
              [c('C', 25, shot='PO fiscal year')] + range_cites)],
        check=[('Include GL account information', [c('C', 25, shot='Include GL account information')]),
               ('Include zero balance POs  (a PO since closed has nothing left open)', [c('C', 25, shot='Include zero balance POs')]),
               ('Include carry forward POs', [c('C', 25, shot='Include carry forward POs')])],
        uncheck=[('—', [])],
        years=years_po, output='Excel (toolbar).')

    # Year-end position goes LAST (TJ, 6 October 2026); renumber.
    ye = [r for r in runs if r['report'].startswith('Year-end position')]
    runs[:] = [r for r in runs if r not in ye] + ye
    for i, r in enumerate(runs, 1):
        r['n'] = i
    for r in runs:
        r['status'] = run_status(r['report'], funds)
    return runs, (lo, hi, others), f24


# --------------------------------------------------------------------------- the shared boxes
def shared(funds, sweep, f24, runs):
    lo, hi, others = sweep
    enc = [r['n'] for r in runs if r['program'].startswith('Encumbrance by PO Number')]
    ye = next(r['n'] for r in runs if r['report'].startswith('Year-end position'))
    account = [
        ('Every export must carry the FULL account number as one column, like the Town’s own exports already do:', []),
        ('ACCOUNT = 0100-3-300-2330-03-2-12-1-511103  (the Town’s FY2026 YTD Budget Report in Excel)', [
            h('p12x', 'ACCOUNT'), h('p12x', '0100-3-300-2330-03-2-12-1-511103')]),
        ('ACCOUNT = 1301-0-000-0000-00-0-00-0-104000  (the Account Detail export sent in June)', [
            h('ad', 'Journal Detail Export'), h('ad', '1301-0-000-0000-00-0-00-0-104000')]),
        ('…plus ORG, OBJECT and PROJECT STRING where the report has them.', [h('ad', 'PROJECT STRING')]),
        ('The first segment is the fund and the last the object; 2330 is a DESE function code. That function code is '
         'the only thing joining the Town’s ledger to the district’s budget. The printout alone does not carry it: the '
         'printed report gives the short form, e.g. “62001901 511000”, and leaves the fund to the page heading.', [
            c('F', 79, 'Segment 1 is always Fund'), h('peg', '62001901 511000')]),
        ('YTD Budget Report: check Print full GL account (prints the full number instead of org/object/project) and '
         'Order accounts by = full account. The Town’s Excel carried the full number even when the printout did not.', [
            c('F', 98, 'This prints instead of the org/object/project codes'), h('p12', 'Print full GL account: N')]),
        ('The Town’s FY2023 school printout shows the full number when it is printed that way.', [
            h('fy23', '0100-3-300-4220-01-1-74-2-535006')]),
        ('Encumbrance by PO Number: check Include GL account information. PO Audit Report: no guide shows an account '
         'option, and its sample prints Org, Obj and Proj only — the PO number joins it to run %d.' % enc[0], [
            c('C', 25, shot='Include GL account information'), c('C', 24, 'Proj')]),
    ]
    excel = [
        ('YTD Budget Report: after Accept and Back, choose the output — Excel. A PDF of the same run too: with Print '
         'report options checked, the printout ends with the options page, which the spreadsheet does not carry.', [
            c('C', 10, 'Click on output option of your choice PDF or Excel'),
            c('F', 102, 'On the main screen, choose an output option to view, print, or save the report')]),
        ('Purchase order reports: the Excel button on the report’s own toolbar.', [
            c('C', 24, shot='Excel'), c('C', 25, shot='Excel')]),
        ('Where the export shows a list of fields to export (the Munis Office Export Filter), leave EVERY field '
         'selected -- except a payee-name column, if you choose to remove it (see “Removing payee names”). Only selected fields are exported, and MUNIS keeps the last selection — so a field unticked for an '
         'earlier export stays unticked until somebody ticks it again. Then Accept, and Open or Save the file.', [
            c('L', 6, shot='Munis Office Export Filter … Only selected fields will be exported. Your selections can be '
                           'saved for subsequent exports.'),
            c('L', 6, 'Check/ or uncheck anything you want to see or not see within this report')]),
        ('“The Excel option is almost always visible and active in the MUNIS Ribbon.”', [
            c('B', 5, 'The Excel option is almost always visible and active in the MUNIS Ribbon')]),
        (f'The export to Excel is shown in “{VIDEO["title"]}” ({VIDEO["channel"]}, YouTube) at {VIDEO["at"]}, per '
         f'TJ: {VIDEO["url"]}', ['V ' + VIDEO['at']]),
        ('Its automatic captions (YouTube’s, not a transcript) say Excel can be reached “from the Browse screen” or '
         '“from the main account inquiry screen”, and that the two give “two totally different data sets”.',
         ['V 6:00–6:13']),
        ('Please send .xlsx. If only CSV is possible, that is fine — we will import the account columns as text.', []),
    ]
    sweep_n = len(others)
    selection = [
        ('| means OR; a colon or two dots mean a RANGE. The guide’s own examples: 710|720 is “710 or 720”; '
         '11500001:11500010 is the range. It also warns not every field takes every wildcard.', [
            c('B', 8, '710|720'), c('B', 8, '11500001:11500010'), c('B', 8, '11500001..11500010'),
            c('B', 8, 'not all are available in all fields')]),
        ('The school is Department 300|301 (or 300:301 — nothing lies between). The Town’s own FY2024 period 13 '
         f'school report, headed ACCOUNTS FOR: 300 SCHOOL DEPARTMENT, printed {len(f24)} funds, expense and revenue, '
         'in one run.', [
            h('fy24', 'TOTAL REVENUES SCHOOL CHOICE R'), h('fy24', 'TOTAL EXPENSES')]),
        (f'Selecting by Fund instead does not work as well. A single range {lo}:{hi} across the school funds would also '
         f'sweep in {sweep_n} other funds that hold no school account, and a list by Fund misses the general fund’s '
         'school accounts unless 0100 is in it — which brings in every town department. Department, or blank, is the '
         'clean selection.', []),
    ]
    combine = [
        ('IN ONE RUN — every fund: the Town’s own FY2024 school report did it.', [
            h('fy24', 'ACCOUNTS FOR: 300 SCHOOL DEPARTMENT')]),
        ('IN ONE RUN — expense and revenue together: leave Account type blank. Our 4 September request split them; '
         'it need not.', [c('F', 101, 'only accessible if there are both revenue and expense accounts in the active set')]),
        ('IN ONE RUN, PROBABLY — four years of transactions: the From/To boxes take “the range of years and periods”. '
         'Multi-year runs are confirmed by TJ from a demonstration video. The guides’ own example stays inside one year.', [
            c('F', 102, 'Define the range of years and periods'), c('C', 11, shot='From yr/per 2020 1, To yr/per 2020 2')]),
        (f'POSSIBLY ONE RUN — the year-end position (run {ye}): the guides show one Year/period per run, but TJ has '
         'seen a multi-year run demonstrated, so the combined report is asked for first and one run per year is '
         'the fallback.', [c('F', 98, 'you must specify a fiscal year and period')]),
        ('SEPARATE — journal detail and the year-end summary. They are one program and one checkbox (“Follow all steps '
         'as before”), so a run is one or the other. A detail run prints its lines “for each account”, but no guide shows '
         'that output, so whether it also gives each account’s closing line is not established — hence both are asked for.', [
            c('C', 10, 'Follow all steps as before'), c('F', 101, 'prints these detail lines for each account')]),
        ('NOT SEPARATE — budget transfers and spending: Include budget entries adds the transfers to the same detail.', [
            c('F', 101, 'Causes transaction type 5 journal entries to be included in the detail of the report')]),
        ('SEPARATE — school transactions and the general fund revenue accounts: different selections; one run would '
         'need every field blank, which is four years of every Town transaction.', []),
        ('SEPARATE from the ledger runs — purchase orders: a Purchasing program.', [
            c('C', 17, 'Financials > Purchasing > PO Inquiry and Reports Menu > Standard PO Reports')]),
        ('POSSIBLY ONE RUN — the PO years: 2023:2026 in the year box (Burlingame p8 range syntax), if that field '
         'takes it; otherwise one run per year.', [c('B', 8, '11500001:11500010'),
                                                   c('B', 8, 'not all are available in all fields')]),
    ]
    return account, excel, selection, combine


# ----------------------------------------------------------- removing payee names (help, not a demand)
# The custodian asked TJ whether the vendor name can be stripped from the Account Detail export:
# one special-education fund's detail carries the names of individuals (parents/families), not
# businesses. This is help toward her own decision, not a position on what she should do.
SPED_FUNDS = ['2640', '2742', '2758', '2800', '2813', '2814']


def vendor_help(funds):
    missing = [f for f in SPED_FUNDS if f not in funds]
    if missing:
        PROBLEMS.append(f'vendor_help: funds not on the request: {missing}')
    # JUST THE STEPS (TJ, 7 October 2026: "simplify ... to just be the steps? no context").
    # Each step keeps its checked citation.
    return [
        ('Export the Account Detail report to Excel. If the export screen lets you pick columns, '
         'untick VDR NAME/ITEM DESC there.',
         [c('L', 6, 'Check/ or uncheck anything you want to see or not see within this report')]),
        ('Keep the vendor number. It is on invoice lines (source API): the reference is the 6-digit vendor '
         'number, the invoice number, then the name. Example, from the Town\u2019s 6 October trial balance: '
         '016364 190817 <name> and 016364 194356 <name> \u2014 one vendor, two invoices. In a new column '
         'VENDOR NO: =IF(AND(ISNUMBER(--LEFT(A2,6)),MID(A2,7,1)=" "),LEFT(A2,6),"") \u2014 it stays blank on '
         'lines with no vendor, such as payment batches (17 26).',
         [h('tb', '016364 190817'), h('tb', '016364 194356'), c('F', 59, 'may contain the vendor number')]),
        ('For any fund whose payees include private individuals: delete the VDR NAME/ITEM DESC column.',
         [h('ad', 'VDR NAME/ITEM DESC')]),
        ('In REFERENCE, REF1, REF3 and COMMENTS, clear any person\u2019s name; VENDOR NO still says who was '
         'invoiced.',
         [h('ad', 'REFERENCE'), h('ad', 'REF1'), h('ad', 'REF3'), h('ad', 'COMMENTS')]),
        ('For those funds: delete CHECK NO, VOUCHER and WARRANT.',
         [h('ad', 'CHECK NO'), h('ad', 'VOUCHER'), h('ad', 'WARRANT')]),
        ('Save and send.', []),
    ]


def vendor_checked():
    """One line under the steps: what they were checked against, counted from the Town\u2019s own
    exports rather than typed (TJ, 7 October 2026: \u201cput something about the data we have and
    what we got\u201d)."""
    tb = os.path.join(ROOT, 'sources', 'data', 'munis-trial-balance-journal.csv')
    ap = [r for r in csv.DictReader(open(tb, encoding='utf-8')) if r['src'].startswith('AP')]
    inv = [r for r in ap if re.match(r'^\d{6} \d', r['reference'])]
    vendors = {r['reference'][:6] for r in inv}
    if not inv or any(not r['src'] == 'API' for r in inv):
        PROBLEMS.append('vendor_checked: the trial balance no longer shows vendor numbers on invoice lines only')
    return (f'Checked against what the Town has sent us. In the 6 October trial balance for fund 1300, '
            f'{len(inv)} of {len(ap)} accounts-payable lines carry a vendor number \u2014 every one an '
            f'invoice line, {len(vendors)} vendors, each number always the same name. The other '
            f'{len(ap) - len(inv)} carry none ({sum(1 for r in ap if r["src"] == "APP")} payment batches, '
            f'{sum(1 for r in ap if r["src"] == "API" and r not in inv)} invoice lines with a blank reference), '
            f'and the formula above leaves those blank. The June Account Detail export '
            f'for fund 1301 shows payments only as batch lines, so whether a vendor number appears depends '
            f'on how the report is run.')


# --------------------------------------------------------------------------- render
CSS = """
@page { size: Letter landscape; margin: 9mm 9mm 10mm 9mm; }
* { box-sizing: border-box; }
body { font: 7.1pt/1.32 -apple-system, 'Helvetica Neue', Arial, sans-serif; color: #16130f; margin: 0; }
h1 { font-size: 14pt; margin: 0 0 2pt; }
.sub { font-size: 8.5pt; margin: 0 0 6pt; color: #333; }
table.runs { border-collapse: collapse; width: 100%; table-layout: fixed; }
table.runs th { background: #1f3a5f; color: #fff; text-align: left; padding: 3pt; font-size: 7pt; vertical-align: bottom; }
table.runs td { border: 0.5pt solid #b0b0b0; padding: 2.5pt 3pt; vertical-align: top; overflow-wrap: anywhere; }
table.runs tr { page-break-inside: avoid; }
table.runs tr:nth-child(even) td { background: #f6f7f9; }
td.n { font-size: 11pt; font-weight: 700; text-align: center; }
ul { margin: 0; padding-left: 9pt; }
li { margin: 0 0 1.5pt; }
.cite { color: #6a5d00; font-size: 6.2pt; white-space: nowrap; }
.rep { font-weight: 700; }
.prog { color: #444; }
h2 { font-size: 9.5pt; margin: 10pt 0 3pt; border-bottom: 0.6pt solid #1f3a5f; }
.boxes { display: grid; grid-template-columns: 1fr 1fr; gap: 6pt 12pt; }
.box { border: 0.6pt solid #1f3a5f; padding: 4pt 6pt; page-break-inside: avoid; }
.box h3 { font-size: 8pt; margin: 0 0 3pt; }
.foot { font-size: 6.6pt; color: #333; }
.key td { padding: 1pt 4pt; vertical-align: top; font-size: 6.6pt; }
p.status { font-size: 9pt; font-weight: 700; margin: 0 0 3pt; }
.chip { display: inline-block; padding: 1pt 5pt; border-radius: 3pt; font-size: 6.4pt; font-weight: 700;
        letter-spacing: .2pt; white-space: nowrap; }
.chip-received { background: #cdefd3; color: #1a5c2a; }
.chip-partial { background: #ffe3a8; color: #6b4600; }
.chip-needed { background: #ececec; color: #444; }
.status-detail { font-size: 6.2pt; color: #444; margin-top: 2pt; }
tr.done td { color: #888; background: #f2f2f2 !important; }
.status-in { margin-top: 5px; }
.lab { font-weight: 700; font-size: 0.85em; letter-spacing: 0.02em; margin: 2px 0 1px; }
.lab + ul { margin-top: 0; }
td .lab:not(:first-child) { margin-top: 6px; border-top: 1px solid #ddd; padding-top: 4px; }
.vendor { font-size: 8pt; line-height: 1.4; max-width: 960px; }
.vendor li { margin-bottom: 3pt; }
.vendor ol { margin: 0; padding-left: 14pt; }
"""


def esc(s):
    return html.escape(s, quote=False)


def items(lst):
    out = []
    for text, cites in lst:
        cs = ' '.join(f'<span class="cite">[{esc(x)}]</span>' for x in dict.fromkeys(cites))
        out.append(f'<li>{esc(text)} {cs}</li>')
    return '<ul>' + ''.join(out) + '</ul>'


def render(runs, account, excel, selection, combine, vendor, gaps_used, hashes):
    # Eight columns, not eleven (TJ, 7 October 2026: the table was too wide): status sits
    # under the report's name, CHECK and UNCHECK share a labelled column, and "what it
    # answers" moved to an appendix beside the gap questions it would settle.
    head = ['#', 'Report and status', 'MUNIS program / menu path', 'Selection', 'SET (value)',
            'CHECK ✓ / UNCHECK', 'Years / how many runs', 'Output']
    widths = [3, 15, 11, 12, 19, 17, 16, 7]
    CHIP_LABEL = {'received': 'RECEIVED', 'partial': 'PARTIAL', 'needed': 'STILL NEEDED'}
    CHIP_CLASS = {'received': 'chip-received', 'partial': 'chip-partial', 'needed': 'chip-needed'}
    rows = []
    for r in runs:
        state, detail = r['status']
        status_cell = f'<span class="chip {CHIP_CLASS[state]}">{CHIP_LABEL[state]}</span>'
        if detail:
            status_cell += f'<div class="status-detail">{esc(detail)}</div>'
        row_cls = ' class="done"' if state == 'received' else ''
        rows.append(f'<tr{row_cls}>' + ''.join([
            f'<td class="n">{r["n"]}</td>',
            f'<td><span class="rep">{esc(r["report"])}</span><br><span class="prog">{esc(r["program"])}</span>'
            f'<div class="status-in">{status_cell}</div></td>',
            '<td>' + items(r['path']) + '</td>',
            '<td>' + items(r['select']) + '</td>',
            '<td>' + items(r['set']) + '</td>',
            '<td><div class="lab">CHECK ✓</div>' + items(r['check'])
            + ('<div class="lab">UNCHECK</div>' + items(r['uncheck']) if r['uncheck'] else '') + '</td>',
            '<td>' + items(r['years']) + '</td>',
            f'<td>{esc(r["output"])}</td>']) + '</tr>')
    cols = ''.join(f'<col style="width:{w}%">' for w in widths)
    table = (f'<table class="runs"><colgroup>{cols}</colgroup><thead><tr>'
             + ''.join(f'<th>{esc(x)}</th>' for x in head) + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table>')

    def box(title, lst):
        return f'<div class="box"><h3>{esc(title)}</h3>{items(lst)}</div>'

    boxes = ('<div class="boxes">' + box('Every run: the full account number', account)
             + box('Getting it out as Excel (all runs)', excel)
             + box('Selecting several funds or departments at once', selection)
             + box('What can be combined into one run, and what cannot', combine) + '</div>')

    key_rows = []
    for k, (base, name, url) in GUIDES.items():
        key_rows.append(f'<tr><td><b>{k}n</b></td><td>{esc(name)}, page n. {esc(url)} — our copy: '
                        f'/docs/{esc(base)}.pdf, sha256 {hashes.get(k, "?")}</td></tr>')
    key_rows.append(f'<tr><td><b>V</b></td><td>{esc(VIDEO["title"])}, {esc(VIDEO["channel"])} (YouTube), '
                    f'at the time given. {esc(VIDEO["url"])} — not downloaded; title and channel from YouTube’s '
                    'oEmbed record.</td></tr>')
    key_rows.append('<tr><td><b>H:</b></td><td>A report the Town has already run, as we hold it: '
                    + '; '.join(f'<b>{k}</b> = {esc(v[1])}' for k, v in HELD.items()) + '.</td></tr>')
    key = '<table class="key">' + ''.join(key_rows) + '</table>'

    answers_rows = ''.join(
        f'<tr><td class="n">{r["n"]}</td><td><span class="rep">{esc(r["report"])}</span></td>'
        f'<td>{items([(a, []) for a in r["answers"]])}</td></tr>' for r in runs)
    answers = ('<table class="runs answers"><colgroup><col style="width:4%"><col style="width:26%">'
               '<col style="width:70%"></colgroup><thead><tr><th>#</th><th>Report</th><th>What it answers</th>'
               '</tr></thead><tbody>' + answers_rows + '</tbody></table>')
    gl = ''.join(f'<li>{esc(g)} <span class="cite">[run{"s" if len(ns) > 1 else ""} '
                 f'{", ".join(map(str, ns))}]</span></li>' for g, ns in gaps_used)
    n_runs = sum(1 for r in runs if r['program'] != 'Not a report in any of the four guides')
    counts = {'received': 0, 'partial': 0, 'needed': 0}
    for r in runs:
        counts[r['status'][0]] += 1
    status_line = (f'As of {DELIVERED_HUMAN}: {counts["received"]} of {n_runs} runs received, '
                   f'{counts["partial"]} partly received, {counts["needed"]} still needed.')
    vendor_box = items(vendor).replace('<ul>', '<ol>', 1).replace('</ul>', '</ol>')
    body = f"""
<h1>MUNIS report runs for the school records request of 4 September 2026</h1>
<p class="status">{status_line}</p>
<p class="sub">{n_runs} runs, most useful first — send them in this order, as each is ready. Each row gives the screen, the boxes, and the guide page that shows it. The Account Detail export for a special-education fund can carry a payee’s name — see “Removing payee names” below.</p>
{table}
<h2>Notes that apply to every row</h2>
{boxes}
<h2>Removing payee names from the Account Detail export: steps</h2>
<div class="vendor">{vendor_box}<p class="foot" style="margin-top:3pt">{esc(vendor_checked())}</p></div>
<h2>Where the option names come from</h2>
<p class="foot">Lunenburg publishes no MUNIS guide. Option names are given exactly as these guides print them — chiefly the CNMI’s guide (C) and Tyler’s 2020.2 procedures (F) — and Lunenburg’s version may label some differently. Where a guide only shows an option in a screenshot it is marked (screenshot). Anything not named in a row: leave it as the Town usually runs the report. If a box here is missing from the Town’s screen, or a run cannot be made as written, saying so is as useful as the data.</p>
{key}
<h2>Appendix: what each run answers</h2>
{answers}
<h2>Open questions from our gap register these runs would settle</h2>
<ul class="foot">{gl}</ul>
"""
    return body


def build(write=True):
    funds, accounts = request_lists()
    hashes = guide_hashes()
    runs, sweep, f24 = build_runs(funds, accounts)
    account, excel, selection, combine = shared(funds, sweep, f24, runs)
    vendor = vendor_help(funds)
    gaps_used = {}
    for r in runs:
        for g in r['gaps']:
            gaps_used.setdefault(g, []).append(r['n'])
    body = render(runs, account, excel, selection, combine, vendor, list(gaps_used.items()), hashes)
    for r in runs:
        for cell in ('path', 'select', 'set', 'check', 'uncheck', 'years'):
            if not r[cell]:
                PROBLEMS.append(f'run {r["n"]}: empty {cell}')
        cited = any(cs for cell in ('path', 'set', 'check', 'select') for _, cs in r[cell])
        if not cited and not any('As run' in t for t, _ in r['path']):
            PROBLEMS.append(f'run {r["n"]}: no citation anywhere in it')
    if PROBLEMS:
        sys.exit('refusing to write:\n  ' + '\n  '.join(PROBLEMS))
    digest = hashlib.sha256(body.encode()).hexdigest()[:16]
    stamp = (f'<p class="foot">Prepared {date.today().strftime("%-d %B %Y")} by the Lunenburg Budget Project '
             f'(lunenburgbudgetproject.org) from the guides and reports named above, by '
             f'scripts/build_munis_request_runs_pdf.py. Inputs digest {digest}.</p>')
    doc = (f'<!doctype html><html><head><meta charset="utf-8"><title>MUNIS request runs</title>'
           f'<style>{CSS}</style></head><body>{body}{stamp}</body></html>')
    return doc, digest, runs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    doc, digest, runs = build()
    if args.check:
        if not os.path.exists(OUT):
            sys.exit(f'{os.path.relpath(OUT, ROOT)} does not exist; run without --check')
        import pypdf
        text = ' '.join(p.extract_text() or '' for p in pypdf.PdfReader(OUT).pages)
        # Chrome's print-to-PDF renders "ff" as a single ligature glyph in some fonts, which
        # pypdf extracts as U+FB00 rather than two letters — quote the source, not the
        # rendering (same issue noted in build_stopped_funding.py, there against minutes text).
        text = text.replace('ﬀ', 'ff').replace('ﬁ', 'fi').replace('ﬂ', 'fl') \
                   .replace('ﬃ', 'ffi').replace('ﬄ', 'ffl')
        m = re.search(r'Inputs digest ([0-9a-f]{16})', text)
        if not m or m.group(1) != digest:
            sys.exit(f'stale: the PDF says {m.group(1) if m else "no digest"}, the inputs now give {digest}. Rebuild.')
        print(f'ok: {len(runs)} rows, every citation on its page, digest {digest}')
        return
    if not CHROME:
        sys.exit('no Chrome found')
    tmp = OUT[:-4] + '.print.html'
    open(tmp, 'w', encoding='utf-8').write(doc)
    subprocess.run([CHROME, '--headless', '--disable-gpu', '--no-pdf-header-footer',
                    '--print-to-pdf=' + OUT, '--virtual-time-budget=4000', 'file://' + tmp],
                   check=True, capture_output=True)
    os.remove(tmp)
    print(f'wrote {os.path.relpath(OUT, ROOT)} ({os.path.getsize(OUT) / 1024:.0f} KB), {len(runs)} rows, digest {digest}')


if __name__ == '__main__':
    main()
