"""SCHOOL MONEY THAT GOES TO THE TOWN: what the schools bring in that the Town books as its own
general fund receipt, by year, read from the documents that print it. One module, three readers:
the preschool report (build_preschool.py), the FY breakdown's section (build_fy_breakdown.py) and
the Town general fund page (build_town_funds.py) -- so the three cannot disagree (rule 7d).

TJ, 29 October 2026: *"i also want the preschool money to go into the FY breakdown page ... it
might have to be its own section to show the additional funds ... a fund page slug for the town
general fund ... it should work the same as the schools."*

WHICH RECEIPTS. The Town's own grouping, not ours: its MUNIS revenue report puts three accounts
under department 31, `DEPT REV - SCHOOL` (the FY2020 fourth-quarter report, FinCom), and its
budget presentations name the same three -- "Dept. Revenue- Schools (Pre-School Tuition, Parking,
Special Education Reimbursement)". All three are general fund 0100, department 01001.

    431900  PRE-SCHOOL TUITION (MUNIS "PS TUITION")        families' preschool tuition
    437400  STUDENT PARKING FE (annual reports: STUDENT PARKING FEES)
    473000  MEDICAL ASSIST/SPED (annual reports: SCHOOL BASED MEDICARE REIMB; FY2026 "SPED REIMB")

WHERE EACH YEAR COMES FROM, every figure read from a document, never typed:
  * FY2011-FY2022: the annual town report's receipts schedule. Where the page was read by eye
    and footed to its own printed category totals (pages-read.csv, `checked`), that reading is
    used -- it supersedes the generic extract (annual-report-receipts.csv), which is used only
    for the rest. FY2021's extract read `$11.648.82` as 11.64; the page reading has 11,648.82.
  * FY2020: the Town's own MUNIS fourth-quarter report in the Finance Committee's FY20 files
    (fy20-q4-reports.csv), which also prints the ESTIMATE. The annual report for FY2020 prints the
    same tuition figure (p24), and our extract of that page missed the row.
  * FY2025: the Town's MUNIS local-receipts report in the Finance Committee's FY27 files
    (fincom-ledgers.csv): estimate and received, account by account.
  * FY2024: only the three together, "FY 24 Actual", on a slide of the Town Manager's FY2026
    budget presentation to the Finance Committee -- a figure a person put on a slide (rule 13a).
  * FY2026: only the three together, "FY 26 Budget", on the FY2027 presentation. The Town's
    MUNIS revenue report to 31 March 2026 holds each account, but it prints the report user's
    MUNIS login and first name, and that is the reason this archive keeps such PDFs private
    (redactions.csv, the period-13 rows); it has no row in the register, so nothing here reads it.
  * FY2023: not read. The annual report prints its receipts as a 93 dpi image
    (page-blocked.csv, FY2023 p25) and no other held document prints the year.

Checks, or nothing is returned: the FY2025 accounts sum to the FY2027 slide's "FY 25 Actual" and
their estimates to the FY2026 slide's "FY 25 Projected", to the dollar.
"""
import csv
import os
import re
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
D0 = Decimal(0)

ACCOUNTS = [
    dict(id='preschool', account='431900', name='Preschool tuition',
         printed=('PRE-SCHOOL TUITION', 'PRE-SCHOOL T UIT ION', 'PS TUITION'),
         what='What families pay for the Primary School’s preschool.'),
    dict(id='parking', account='437400', name='Student parking fees',
         printed=('STUDENT PARKING FEES', 'STUDENT PARKING FE', 'PARKINGFEE'),
         what='What high school students pay to park.'),
    dict(id='medical', account='473000', name='School medical reimbursement',
         printed=('SCHOOL BASED MEDICARE REIMB', 'MEDICAL ASSIST/SPE', 'SPED REIMB'),
         what='Reimbursement for school health services, named “Medical assist/SPED” in the Town’s books.'),
]
BY_ACCOUNT = {a['account']: a for a in ACCOUNTS}

DOCS = dict(
    annual='/docs/town-annual-reports/docs/%s',
    q4='/docs/budget-workbooks/finance-committee/fy20-budget/fy20-4th-quarter-revised-summary-and-reports.pdf',
    fy25='/docs/budget-workbooks/finance-committee/fy27-budget/department-presentations/'
         'preliminary-budget-presentation-2.19.26/fy25-local-receipts.pdf',
    pres26='/docs/budget-workbooks/finance-committee/fy26-budget/preliminary-budget-presentation.pptx',
    pres27='/docs/budget-workbooks/finance-committee/fy27-budget/department-presentations/'
           'preliminary-budget-presentation-2.19.26/preliminary-budget-presentation-2.19.26-final.pptx',
)
PRES_TEXT = dict(
    pres26=os.path.join(ROOT, 'sources/budget-workbooks/finance-committee/fy26-budget/text/'
                              'preliminary-budget-presentation.pptx.txt'),
    pres27=os.path.join(ROOT, 'sources/budget-workbooks/finance-committee/fy27-budget/department-presentations/'
                              'preliminary-budget-presentation-2.19.26/text/preliminary-budget-presentation-2.19.26-final.pptx.txt'))
PRES_LABEL = 'Dept. Revenue- Schools (Pre-School Tuition, Parking, Special Education Reimbursement)'

# FY2021's extract is the case that made the page reading necessary: it carries 11.64 for
# preschool tuition. The join to pages-read.csv must find that row, or nothing is returned.
MUST_READ = (2021, '431900')
# Rows our extract holds that were read by eye against the page before use (rule 13c): the
# printed row, label and figure side by side. FY2019 p30 by image; FY2011-FY2013 and FY2016 by
# the OCR's own row pairing, label and figure on one printed line.
EYE_CHECKED = {(2019, '431900'): 'read by eye, p30'}

FIRST_FY = 2011
YEARS_SHOWN = tuple(range(FIRST_FY, 2027))


def _money(s):
    return Decimal(s.replace('$', '').replace(',', '').strip())


def _pres(key, column):
    """The slide's three-together figure, by its column heading."""
    lines = [l.strip() for l in open(PRES_TEXT[key], encoding='utf-8')]
    i = lines.index(PRES_LABEL)
    j = lines.index('Receipt Type')
    heads = lines[j + 1:j + 4]
    if column not in heads:
        raise SystemExit('school_receipts: %s has no column %r (has %s)' % (key, column, heads))
    return _money(lines[i + 1 + heads.index(column)])


def series():
    """{fy: {account: dict(received, estimate, basis, doc, page, check)}, plus a 'together' entry
    for the years only the three combined are printed}."""
    out = {fy: {} for fy in YEARS_SHOWN}
    names = {p: a['account'] for a in ACCOUNTS for p in a['printed']}
    annual = lambda fy: FIRST_FY <= fy <= 2022 and fy != 2020
    extract_doc = {}
    for r in csv.DictReader(open(os.path.join(DATA, 'annual-report-receipts.csv'), encoding='utf-8')):
        fy = int(r['fy'])
        acct = names.get(r['source'].strip())
        extract_doc[(fy, int(r['page']))] = r['document']
        if not acct or not annual(fy):
            continue
        out[fy][acct] = dict(received=_money(r['amount']), estimate=None, basis='published',
                             check=EYE_CHECKED.get((fy, acct), r['status']),
                             doc=DOCS['annual'] % r['document'], page=int(r['page']),
                             src='Annual town report, FY%d, receipts, p%s' % (fy, r['page']))
    # The page read by eye supersedes the extract (CLAUDE.md, "The annual town reports").
    for r in csv.DictReader(open(os.path.join(DATA, 'pages-read.csv'), encoding='utf-8')):
        fy, page = int(r['fy']), int(r['page'])
        acct = names.get(r['fund_name'].split('::')[-1].strip())
        if not acct or not annual(fy) or r['status'] != 'checked':
            continue
        doc = r['document'] or extract_doc.get((fy, page))
        if not doc:
            raise SystemExit('school_receipts: FY%d p%d read by eye, but no document names it' % (fy, page))
        out[fy][acct] = dict(received=_money(r['value']), estimate=None, basis='published',
                             check='read by eye; footed to the page’s printed totals',
                             doc=DOCS['annual'] % doc, page=page,
                             src='Annual town report, FY%d, receipts, p%d' % (fy, page))
    if not out[MUST_READ[0]].get(MUST_READ[1], {}).get('check', '').startswith('read by eye'):
        raise SystemExit('school_receipts: FY%d %s was not found in pages-read.csv' % MUST_READ)
    for r in csv.DictReader(open(os.path.join(DATA, 'fy20-q4-reports.csv'), encoding='utf-8')):
        if r['doc_version'] != 'revised' or r['level'] != 'account':
            continue
        m = re.match(r'01001 (\d{6})', r['label'])
        if m and m.group(1) in BY_ACCOUNT:
            out[2020][m.group(1)] = dict(received=-_money(r['ytd']), estimate=-_money(r['original']),
                                         basis='published', check='the Town’s MUNIS report',
                                         doc=DOCS['q4'], page=int(r['page']),
                                         src='Town MUNIS revenue report, FY2020 year end, p%s' % r['page'])
    for r in csv.DictReader(open(os.path.join(DATA, 'fincom-ledgers.csv'), encoding='utf-8')):
        if r['fiscal_year'] == '2025' and r['org'] == '01001' and r['object'] in BY_ACCOUNT \
                and 'local-receipts' in r['report_key']:
            out[2025][r['object']] = dict(received=-_money(r['ytd_actual']), estimate=-_money(r['original']),
                                          basis='published', check='the Town’s MUNIS report',
                                          doc=DOCS['fy25'], page=None,
                                          src='Town MUNIS local receipts report, FY2025 year end')
    # the three together, where nothing finer is printed; and the ties
    out[2024]['together'] = dict(received=_pres('pres26', 'FY 24 Actual'), estimate=None, basis='stated',
                                 doc=DOCS['pres26'], page=None, check='a slide',
                                 src='Town Manager’s FY2026 budget presentation, local receipts slide')
    out[2026]['together'] = dict(received=None, estimate=_pres('pres27', 'FY 26 Budget'), basis='stated',
                                 doc=DOCS['pres27'], page=None, check='a slide',
                                 src='Town Manager’s FY2027 budget presentation, local receipts slide')
    f25 = out[2025]
    if len([a for a in f25 if a in BY_ACCOUNT]) != 3:
        raise SystemExit('school_receipts: FY2025 does not hold all three accounts')
    if sum(f25[a['account']]['received'] for a in ACCOUNTS) != _pres('pres27', 'FY 25 Actual'):
        raise SystemExit('school_receipts: FY2025 accounts do not sum to the FY2027 slide’s FY 25 Actual')
    if sum(f25[a['account']]['estimate'] for a in ACCOUNTS) != _pres('pres26', 'FY 25 Projected'):
        raise SystemExit('school_receipts: FY2025 estimates do not sum to the FY2026 slide’s FY 25 Projected')
    if '431900' not in out[2020] or out[2020]['431900']['received'] <= 0:
        raise SystemExit('school_receipts: FY2020 tuition did not read')
    return out


def tuition():
    """Preschool tuition alone: {fy: entry or None}."""
    s = series()
    return {fy: s[fy].get('431900') for fy in YEARS_SHOWN}


WHY_MISSING = {
    2023: 'Not readable: the FY2023 annual report prints its receipts as a 93 dpi image.',
    2024: 'Printed only with parking and medical reimbursement, as one figure on a slide.',
    2026: 'Only the Town’s estimate for the three together is public; the receipts to 31 March are in a report not cleared for publication here.',
}
