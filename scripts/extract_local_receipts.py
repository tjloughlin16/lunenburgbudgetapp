#!/usr/bin/env python3.11
"""Local receipts: what the town ESTIMATED, against what it COLLECTED, by year and by type.

Writes sources/data/local-receipts-estimates.csv -- one row per fiscal year x receipt type x
measure (estimate or actual) x stage, each with the document, the page or slide, a coordinate
and the value as printed.

    python3.11 scripts/extract_local_receipts.py           # write the CSV
    python3.11 scripts/extract_local_receipts.py --check   # rebuild, tie, compare; exit 1 on drift
    python3.11 scripts/extract_local_receipts.py --proof   # against the state's free cash proof

WHY THE STAGE COLUMN MATTERS. A local receipts "estimate" is not one number. In one year the
town has, at least: the Town Manager's projection in the preliminary budget deck, the original
estimate entered in MUNIS, and the REVISED estimate the books carry at year end (changed during
the year, usually at the tax recap). They differ by a great deal -- FY2025 motor vehicle excise
is 1,771,640 original and 1,850,000 revised -- and "collections beat the estimate by X" means a
different X against each. So every estimate row says which stage it is, in the document's own
column heading, and nothing here adds two stages together.

WHAT EACH SOURCE IS (rule 13a). MUNIS printouts are the accounting system's own; the audited
statement's budgetary comparison is audited; the Town Manager's decks are presentations typed
from those books, cross-checked here against the printout for the same year where both exist.

HOW EACH TABLE IS PROVED. Every table is tied to an identity its own page prints -- a group's
original plus adjustments equals its revised figure, the groups sum to the printed GRAND TOTAL,
a deck's column sums to the "Local Receipts: $X" its revenue slide states, an audited actual
minus its final budget equals the printed variance. A table that does not tie stops the write.

Documents surveyed and NOT read are in SKIPPED below, each with the reason (rule 13c).
"""
import csv
import io
import os
import re
import sys
import itertools
import zipfile
from collections import defaultdict
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources')
OUT = os.path.join(SRC, 'data', 'local-receipts-estimates.csv')
PROOF = os.path.join(SRC, 'data', 'free-cash-proof.csv')
VERSIONS = os.path.join(SRC, 'data', 'town-budget-versions.csv')

FIELDS = ['fiscal_year', 'receipt_type', 'category', 'measure', 'stage', 'value',
          'document', 'page_or_slide', 'coordinate', 'basis', 'tie']

FAILS = []


def fail(msg):
    FAILS.append(msg)


def D(s):
    """A printed figure to a Decimal. MUNIS prints revenue negative and zero as '.00'."""
    s = s.strip().replace('$', '').replace(',', '').replace('*', '').replace(' ', '')
    neg = s.startswith('(') and s.endswith(')')
    s = s.strip('()')
    if s in ('-', ''):
        return Decimal(0)
    v = Decimal(s)
    return -v if neg else v


def txt(doc_key):
    """The extracted text beside a document: <dir>/text/<basename>.txt (pdf, pptx) -- or, for
    the town-budget mirror, text/<basename without the extension>.txt."""
    d, b = os.path.split(doc_key)
    for cand in (os.path.join(SRC, d, 'text', b + '.txt'),
                 os.path.join(SRC, os.path.dirname(d), 'text', os.path.splitext(b)[0] + '.txt')):
        if os.path.exists(cand):
            return io.open(cand, encoding='utf-8').read()
    raise SystemExit('no text extract for %s' % doc_key)


def pages(text):
    """{page number: [lines]} from a text extract marked ===PAGE n===."""
    out, cur = {}, None
    for line in text.split('\n'):
        m = re.match(r'===PAGE (\d+)===', line)
        if m:
            cur = int(m.group(1))
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return out


# ---- the category we group each printed label under. OUR grouping, named for the MUNIS
# ---- revenue groups (which are the Division of Local Services' local receipt classes).
CATEGORY = [
    # the audited statement's GAAP lines, each wider than one MUNIS group: kept as their own
    (r'motor vehicle and other excise', 'motor vehicle and other excise'),
    (r'^miscellaneous$', 'miscellaneous'),
    (r'motor ve|^mve', 'motor vehicle excise'),
    (r'meal|other excise|cannabis|boat', 'other excise'),
    (r'penalt', 'penalties and interest'),
    (r'pilot|in lieu', 'payments in lieu of taxes'),
    (r'school', 'departmental revenue: schools'),
    (r'cemeter', 'departmental revenue: cemeteries'),
    (r'dept revenue other|other departmental|ambulance', 'departmental revenue: other'),
    (r'licens', 'licenses and permits'),
    (r'special assess', 'special assessments'),
    (r'fines', 'fines and forfeits'),
    (r'investment', 'investment income'),
    (r'misc\.? recurring', 'miscellaneous recurring'),
    (r'misc', 'miscellaneous non-recurring'),
    (r'room', 'other excise'),
    (r'charges for serv', 'charges for services'),
    (r'^rentals', 'rentals'),
    (r'librar', 'departmental revenue: libraries'),
    (r'recreation', 'departmental revenue: recreation'),
    (r'medicaid', 'medicaid reimbursement'),
    (r'roll back', 'roll back taxes'),
    (r'tax liens', 'tax liens'),
    (r'^fees and rentals', 'fees and rentals'),
    (r'^fees', 'fees'),
]
# Groups a MUNIS general-fund revenue printout carries that are NOT local receipts.
NOT_LOCAL = {'30', '42', '45', '98'}   # MSBA, tax levy, state aid, other financing sources


def category(label):
    lo = re.sub(r'^\d\d\s+', '', label.lower())
    if lo.startswith('local receipts') or lo.startswith('total'):
        return 'total'
    for pat, cat in CATEGORY:
        if re.search(pat, lo):
            return cat
    fail('no category for printed label %r' % label)
    return ''


ROWS = []


def emit(fy, label, measure, stage, value, doc, where, coord, basis, tie):
    ROWS.append({'fiscal_year': fy, 'receipt_type': label, 'category': category(label),
                 'measure': measure, 'stage': stage, 'value': '%.2f' % value, 'document': doc,
                 'page_or_slide': where, 'coordinate': coord, 'basis': basis, 'tie': tie})


# ================================================================================================
# 1. MUNIS printout with a text layer: FY2025 period 12, glytdbud "GENERAL FUND REPORT".
# ================================================================================================
FY25_MUNIS = ('budget-workbooks/finance-committee/fy27-budget/department-presentations/'
              'preliminary-budget-presentation-2.19.26/fy25-local-receipts.pdf')
NUM = r'(-?[\d,]*\.\d\d)'


def munis_text(doc, fy):
    pg = pages(txt(doc))
    groups, grand = [], None
    for p, lines in sorted(pg.items()):
        code = None
        for i, line in enumerate(lines):
            m = re.match(r'^(\d\d)\s+([A-Z][A-Z &\-]+?)\s*$', line.strip())
            if m:
                code = m.group(1)
            m = re.match(r'^\s*TOTAL ([A-Z][A-Z &\-]+?)\s+' + r'\s+'.join([NUM] * 6), line)
            if m and m.group(1) != 'REVENUES':
                v = [D(x) for x in m.groups()[1:]]
                groups.append((code, m.group(1).strip(), v, p, i + 1))
            m = re.match(r'^\s*GRAND TOTAL\s+' + r'\s+'.join([NUM] * 6), line)
            if m:
                grand = [D(x) for x in m.groups()]
    if not groups or grand is None:
        fail('%s: no groups or no GRAND TOTAL read' % doc)
        return
    for code, name, v, p, ln in groups:
        if v[0] + v[1] != v[2]:
            fail('%s %s: original + adjustments != revised' % (doc, name))
    for k in range(6):
        if sum(g[2][k] for g in groups) != grand[k]:
            fail('%s: column %d does not sum to GRAND TOTAL' % (doc, k))
    tie = 'groups sum to the printed GRAND TOTAL; original + adjustments = revised per group'
    for code, name, v, p, ln in groups:
        coord = 'TOTAL %s line (page %d, text line %d)' % (name, p, ln)
        for meas, stage, val in (('estimate', 'ORIGINAL APPROP', v[0]),
                                 ('estimate', 'REVISED BUDGET', v[2]),
                                 ('actual', 'YTD EXPENDED (collected)', v[3])):
            emit(fy, '%s %s' % (code, name), meas, stage, -val, doc, 'p%d' % p, coord,
                 'ledger: MUNIS printout', tie)


# ================================================================================================
# 2. MUNIS printout held ONLY as a picture: FY2024 period 13, "FY24 RECEIPTS BY CATEGORY",
#    page 5 of the FY24 year-end report. pdf_kind calls that page an image; it is in the
#    searchable-PDF backlog. Transcribed from the page image, and every digit is then held by
#    three identities the page prints: original + adjustments = revised, revised - actual =
#    remaining, and each column sums to GRAND TOTAL. A misread digit cannot pass all three.
# ================================================================================================
FY24_DOC = 'town-budget/docs/2419-fy24-year-end-report.pdf'
FY24_P5 = [  # code, name as printed, ORIGINAL ESTIM REV, ESTIM REV ADJSTMTS, REVISED EST REV,
    #          ACTUAL YTD REVENUE, REMAINING REVENUE
    ('13', 'FINES & FORFEITS', '13,263.00', '-1,250.00', '12,013.00', '26,808.39', '-14,795.39'),
    ('26', 'OTHER EXCISE', '100,980.00', '.00', '100,980.00', '140,933.50', '-39,953.50'),
    ('30', 'MSBA REIMBURSEMENT', '474,239.00', '-474,239.00', '.00', '.00', '.00'),
    ('31', 'DEPT REV - SCHOOL', '60,207.00', '.00', '60,207.00', '150,100.74', '-89,893.74'),
    ('40', 'TAX LIENS', '.00', '.00', '.00', '105,019.59', '-105,019.59'),
    ('41', 'PAYMT IN LIEU OF TAX', '1,648.00', '.00', '1,648.00', '1,609.65', '38.35'),
    ('42', 'TAX LEVY', '30,548,749.95', '945,140.54', '31,493,890.49', '31,175,162.79', '318,727.70'),
    ('43', 'FEES', '176,052.00', '.00', '176,052.00', '285,988.14', '-109,936.14'),
    ('44', 'LICENSES & PERMITS', '331,188.00', '.00', '331,188.00', '427,164.86', '-95,976.86'),
    ('45', 'STATE AID', '10,258,395.00', '388,499.00', '10,646,894.00', '10,256,028.28', '390,865.72'),
    ('46', 'ROLL BACK TAXES', '.00', '.00', '.00', '11,512.35', '-11,512.35'),
    ('47', 'DEPT REVENUE OTHER', '257,370.00', '.00', '257,370.00', '388,281.23', '-130,911.23'),
    ('48', 'INVESTMENT INCOME', '25,000.00', '60,600.00', '85,600.00', '414,577.73', '-328,977.73'),
    ('49', 'DEPT REV CEMETERIES', '4,100.00', '-600.00', '3,500.00', '4,050.00', '-550.00'),
    ('50', 'MOTOR VEHICLE EXCISE', '1,771,640.00', '50,000.00', '1,821,640.00', '2,069,581.56', '-247,941.56'),
    ('70', 'SPECIAL ASSESSMENTS', '11,844.00', '.00', '11,844.00', '6,060.00', '5,784.00'),
    ('71', 'PENALTIES & INTEREST', '200,000.00', '-60,000.00', '140,000.00', '141,252.84', '-1,252.84'),
    ('98', 'OTHER FIN SOURCE', '3,093,903.86', '-717,933.51', '2,375,970.35', '2,375,970.35', '.00'),
    ('99', 'MISC NON RECURRING', '215,698.50', '.00', '215,698.50', '407,825.25', '-192,126.75'),
]
FY24_GRAND = ('47,544,278.31', '190,217.03', '47,734,495.34', '48,387,927.25', '-653,431.91')


def munis_fy24():
    rows = [(c, n, [D(x) for x in vals]) for c, n, *vals in FY24_P5]
    for c, n, v in rows:
        if v[0] + v[1] != v[2]:
            fail('FY24 p5 %s: original + adjustments != revised' % n)
        if v[2] - v[3] != v[4]:
            fail('FY24 p5 %s: revised - actual != remaining' % n)
    grand = [D(x) for x in FY24_GRAND]
    for k in range(5):
        if sum(v[k] for _, _, v in rows) != grand[k]:
            fail('FY24 p5: column %d does not sum to GRAND TOTAL' % k)
    tie = ('read from the page image; every row closes original + adjustments = revised and '
           'revised - actual = remaining, and every column sums to the printed GRAND TOTAL')
    for c, n, v in rows:
        if c in NOT_LOCAL:
            continue
        for meas, stage, val in (('estimate', 'ORIGINAL ESTIM REV', v[0]),
                                 ('estimate', 'REVISED EST REV', v[2]),
                                 ('actual', 'ACTUAL YTD REVENUE', v[3])):
            emit(2024, '%s %s' % (c, n), meas, stage, val, FY24_DOC, 'p5',
                 'row %s %s (FOR 2024 13)' % (c, n), 'ledger: MUNIS printout, image page', tie)


# ================================================================================================
# 3. The audited statement, FY2023: Required Supplementary Information, budgetary comparison.
#    Page 62 prints the budget columns with labels; page 63 prints the actual and variance
#    columns WITHOUT labels, in the same row order. That order is proved, not assumed: for
#    every row, actual - final budget must equal the printed variance.
# ================================================================================================
FY23_DOC = 'town-budget/docs/2420-fy23-lunenburg-financial-statements.pdf'
FY23_ROWS = ['Real estate and personal property taxes', 'Tax liens',
             'Motor vehicle and other excise taxes', 'Penalties and interest on taxes',
             'Fees and rentals', 'Payments in lieu of taxes', 'Licenses and permits',
             'Fines and forfeitures', 'Intergovernmental', 'Investment income', 'Miscellaneous']
FY23_NOT_LOCAL = {'Real estate and personal property taxes', 'Intergovernmental'}


def audited_fy23():
    pg = pages(txt(FY23_DOC))
    budget = {}
    for ln in pg[62]:
        for lab in FY23_ROWS:
            if ln.strip().startswith(lab) or (lab.startswith('Real estate') and ln.startswith('net of tax')):
                nums = re.findall(r'\$?\s*(-|\(?[\d,]+\)?)\s*(?=\s|$)', ln.split('…')[-1])
                nums = [n for n in nums if n.strip()]
                if len(nums) == 4:
                    budget[lab] = [D(n) for n in nums]
        if ln.strip().startswith('TOTAL REVENUES'):
            budget['TOTAL'] = [D(n) for n in re.findall(r'(-|[\d,]{2,})', ln.split('…')[-1])][:4]
    actual_lines = [ln for ln in pg[63] if re.match(r'^\s*\$?\s*[\d,(]', ln)]
    act = []
    for ln in actual_lines[:len(FY23_ROWS) + 1]:
        nums = re.findall(r'\(?[\d,]+\)?|(?<!\S)-(?!\S)', ln.replace('$', ''))
        act.append([D(n) for n in nums])
    if set(budget) != set(FY23_ROWS) | {'TOTAL'}:
        fail('FY23 RSI p62: read %d of %d rows' % (len(budget), len(FY23_ROWS) + 1))
        return
    for lab, a in zip(FY23_ROWS + ['TOTAL'], act):
        final = budget[lab][3]
        if a[0] - final != a[2]:
            fail('FY23 RSI %s: actual - final budget != printed variance' % lab)
    for k in range(4):
        if sum(budget[lab][k] for lab in FY23_ROWS) != budget['TOTAL'][k]:
            fail('FY23 RSI: budget column %d does not sum to TOTAL REVENUES' % k)
    if sum(a[0] for a in act[:-1]) != act[-1][0]:
        fail('FY23 RSI: actuals do not sum to TOTAL REVENUES')
    tie = ('p63 rows placed by p62 order, proved by actual - final budget = printed variance on '
           'every row; both pages sum to TOTAL REVENUES')
    for lab, a in zip(FY23_ROWS, act):
        if lab in FY23_NOT_LOCAL:
            continue
        b = budget[lab]
        for meas, stage, val, p in (('estimate', 'Original Budget', b[2], 'p62'),
                                    ('estimate', 'Final Budget', b[3], 'p62'),
                                    ('actual', 'Actual Budgetary Amounts', a[0], 'p63')):
            emit(2023, lab, meas, stage, val, FY23_DOC, p, 'row %s (YEAR ENDED JUNE 30, 2023)' % lab,
                 'audited: budgetary comparison (RSI)', tie)


# ================================================================================================
# 4. The Town Manager's decks: "Local Receipts Estimate", thirteen receipt types, three columns.
#    Read off the slide text (label, then one line per column); the slide found by opening the
#    pptx. Each estimate column is tied to the "Local Receipts: $X" the deck's revenue slide or
#    the table's own title prints.
# ================================================================================================
FC = 'budget-workbooks/finance-committee/'
DECKS = [
    # document, the anchor line before the table, {column as printed: (fy, measure)},
    # the printed total that ties an estimate column: (column, text that prints it)
    (FC + 'fy26-budget/preliminary-budget-presentation.pptx', 'FY 2026 \nLocal Receipts Estimate\nReceipt Type',
     {'FY 25 Projected': (2025, 'estimate'), 'FY 24 Actual': (2024, 'actual'),
      'FY 26 Projected': (2026, 'estimate')},
     ('FY 26 Projected', 'Local Receipts: $3,360,524')),
    (FC + 'fy27-budget/department-presentations/preliminary-budget-presentation-2.19.26/'
          'preliminary-budget-presentation-2.19.26-final.pptx', 'FY 2027 Local Receipts Estimate\nReceipt Type',
     {'FY 25 Actual': (2025, 'actual'), 'FY 26 Budget': (2026, 'estimate'),
      'FY 27 Budget': (2027, 'estimate')},
     ('FY 27 Budget', 'Local Receipts: $3,360,524.00')),
    (FC + 'fy27-budget/updated-budget-fincom-3.26.27.pptx', 'FY 2027 Local Receipts: $3,535,524\nReceipt Type',
     {'FY 25 Actual': (2025, 'actual'), 'FY 26 Budget': (2026, 'estimate'),
      'FY 27 Budget': (2027, 'estimate')},
     ('FY 27 Budget', 'FY 2027 Local Receipts: $3,535,524')),
]
MONEY = re.compile(r'^\$[\d,]+(\.\d\d)?\*{0,2}$')


def slide_of(pptx, needle):
    """The slide number whose XML holds `needle` (first occurrence)."""
    with zipfile.ZipFile(os.path.join(SRC, pptx)) as z:
        names = sorted((n for n in z.namelist() if re.match(r'ppt/slides/slide\d+\.xml$', n)),
                       key=lambda n: int(re.findall(r'\d+', n)[0]))
        for n in names:
            x = z.read(n).decode('utf-8', 'replace')
            if needle in re.sub(r'<[^>]+>', '', x):
                return int(re.findall(r'\d+', n)[0])
    return None


def deck(doc, anchor, cols, total):
    text = txt(doc)
    i = text.find(anchor)
    if i < 0:
        fail('%s: table anchor not found' % doc)
        return
    lines = [l.strip() for l in text[i + len(anchor):].split('\n')]
    heads, k = [], 0
    while len(heads) < len(cols):
        if lines[k]:
            heads.append(lines[k])
        k += 1
    if heads != list(cols):
        fail('%s: column headings read %r' % (doc, heads))
        return
    table = []
    while k + len(cols) < len(lines):
        lab, vals = lines[k], lines[k + 1:k + 1 + len(cols)]
        if not lab or not all(MONEY.match(v) for v in vals):
            break
        table.append((lab.replace('&amp;', '&'), vals))
        k += 1 + len(cols)
    if len(table) != 13:
        fail('%s: read %d receipt types, expected 13' % (doc, len(table)))
    col, printed = total
    j = heads.index(col)
    s = sum(D(v[j]) for _, v in table)
    if '$' + format(s, ',') not in printed and '$' + format(s, ',.2f') not in printed:
        fail('%s: %s sums to %s, the deck prints %r' % (doc, col, s, printed))
    if printed not in text:
        fail('%s: the printed total %r is not in the deck' % (doc, printed))
    slide = slide_of(doc, 'Receipt Type')
    for lab, vals in table:
        for h, v in zip(heads, vals):
            fy, meas = cols[h]
            tie = ('column sums to "%s", printed in the deck' % printed if h == col else
                   'cross-checked to the MUNIS printout for the year' if meas == 'actual' else
                   'no total printed for this column')
            emit(fy, lab, meas, h, D(v), doc, 'slide %s' % slide, 'row %s, column %s%s' % (
                lab, h, ' (marked %s on the slide)' % v[len(v.rstrip('*')):] if v.endswith('*') else ''),
                 'presentation: Town Manager budget deck', tie)

# ================================================================================================
# 4b. The Division of Local Services' 23-line local receipts table, as the Town Manager prints it
#     in each preliminary budget message and five-year forecast: two years of actuals beside two
#     years of estimates, or two budget years beside five projected years. Each column is tied
#     to the TOTAL line the page prints. A "Difference: Actual over ..." line, where printed, is
#     checked against the ESTIMATE for that year in the earlier message -- the page compares
#     across documents, so the check does too.
# ================================================================================================
TB = 'town-budget/docs/'
A, E, F = 'actual', 'estimate', 'forecast'
DOR = [
    # document, page, columns as (fiscal year, measure, heading as printed)
    (TB + 'a76-fiscal-year-2022-budget-message-and-preliminary-budget-recommendation.pdf', 10,
     [(2019, A, 'FY2019 Actual'), (2020, A, 'FY2020 Actual'), (2021, E, 'FY2021 Estimate'),
      (2022, E, 'FY2022 Estimate')]),
    (TB + 'a73-fy23-preliminary-budget-message.pdf', 10,
     [(2020, A, 'FY2020 Actual'), (2021, A, 'FY2021 Actual'), (2022, E, 'FY2022 Estimate'),
      (2023, E, 'FY2023 Estimate')]),
    (TB + 'a187-fy24-town-manager-preliminary-budget-message-and-proposal.pdf', 12,
     [(2021, A, 'FY2021 Actual'), (2022, A, 'FY2022 Actual'), (2023, E, 'FY2023 Estimate'),
      (2024, E, 'FY2024 Estimate')]),
    (TB + 'a135-fy25-budget-message-and-proposal-for-bos-and-fc.pdf', 11,
     [(2022, A, 'FY2022 Actual'), (2023, A, 'FY2023 Actual'), (2024, E, 'FY2024 Estimated'),
      (2025, E, 'FY2025 Estimated')]),
    (TB + 'a190-fy19-fy23-financial-forecast-presentation.pdf', 13,
     [(2017, E, 'FY2017 Budget'), (2018, E, 'FY2018 Budget')] +
     [(y, F, 'FY%d Projected' % y) for y in range(2019, 2024)]),
    (TB + 'a191-fy20-fy24-financial-forecast-presentation.pdf', 14,
     [(2018, E, 'FY2018 Budget'), (2019, E, 'FY2019 Budget')] +
     [(y, F, 'FY%d Projected' % y) for y in range(2020, 2025)]),
    (TB + 'a192-fy21-fy25-financial-forecast-presentation.pdf', 16,
     [(2019, E, 'FY2019 Budget'), (2020, E, 'FY2020 Budget')] +
     [(y, F, 'FY%d Projected' % y) for y in range(2021, 2026)]),
    (TB + 'a193-fy22-fy26-financial-forecast-presentation.pdf', 17,
     [(2020, E, 'FY2020 Budget'), (2021, E, 'FY2021 Budget')] +
     [(y, F, 'FY%d Projected' % y) for y in range(2022, 2027)]),
]
CELL = r'(?:[\d,]+|-)'
DIFFS = []
TOLERANCE_PHRASE = 'within $1 rounding tolerance'   # notes/process/TOLERANCES.md; do not reword
# Columns whose rows miss their printed TOTAL by more than the $1 allowance. Left OUT of the
# table, named here so the count cannot grow unseen; each is a projection in a spreadsheet
# printout, where display rounding of seven columns is the likely cause (a hypothesis).
NOT_CLOSED = {
    ('town-budget/docs/a191-fy20-fy24-financial-forecast-presentation-pdf.pdf', 14, 'FY2021 Projected'),
    ('town-budget/docs/a191-fy20-fy24-financial-forecast-presentation-pdf.pdf', 14, 'FY2024 Projected'),
}   # $3 and $2 off across 25 rounded cells; a wider tolerance needs TJ's approval first
NOT_CLOSED_SEEN = set()   # (document, page, fiscal year, printed difference, actual)


def dor_doc(key):
    """The archive key for a town-budget document, by its number prefix (the mirror keeps the
    publisher's filename, which these specs abbreviate)."""
    pre = os.path.basename(key).split('-')[0] + '-'
    hits = [f for f in os.listdir(os.path.join(SRC, 'town-budget', 'docs')) if f.startswith(pre)]
    if len(hits) != 1:
        fail('%s: %d documents carry that number' % (pre, len(hits)))
        return key
    return 'town-budget/docs/' + hits[0]


def dor(doc, page, cols):
    doc = dor_doc(doc)
    lines = pages(txt(doc)).get(page, [])
    n = len(cols)
    heads = ' '.join(lines)
    for fy, _, h in cols:
        if 'FY%d' % fy not in heads or h.split(' ', 1)[1] not in heads:
            fail('%s p%d: heading %r not on the page' % (doc, page, h))
    table, partial, total, diff = [], [], None, None
    for ln in lines:
        t = ln.strip()
        m = re.match(r'^(\d+[a-c]?)\.\s+(.*?[A-Za-z)])\s*((?:%s\s*)*)$' % CELL, t)
        if m:
            vals = m.group(3).split()
            if len(vals) == n:
                table.append((m.group(1), m.group(2), vals, 'line as printed'))
            elif any(v != '-' for v in vals):
                partial.append((m.group(1), m.group(2), vals))
            continue
        m = re.match(r'^TOTAL Local Receipts.*?((?:\s+%s){%d})\s*$' % (CELL, n), t)
        if m:
            total = m.group(1).split()
        m = re.match(r'^Difference:.*?((?:\s+%s)+)\s*$' % CELL, t)
        if m:
            diff = m.group(1).split()
    if total is None or len(table) < 10:
        fail('%s p%d: read %d lines and %s total' % (doc, page, len(table), 'a' if total else 'no'))
        return
    # A line printed with a blank cell (k figures for n columns) is placed by the TOTALS: the one
    # arrangement, in printed order, under which every column closes. Never by guessing.
    for no, lab, vals in partial:
        resid = [D(total[k]) - sum(D(v[k]) for _, _, v, _ in table) for k in range(n)]
        fits = []
        for pos in itertools.combinations(range(n), len(vals)):
            cells = ['-'] * n
            for k, v in zip(pos, vals):
                cells[k] = v
            # placement only decides WHERE a figure goes; whether the column closes is tested
            # afterwards under the $1 policy. A $5 window separates 1,376 from nothing.
            if all(abs(resid[k] - D(cells[k])) <= 5 for k in range(n)):
                fits.append(cells)
        # arrangements that differ only in where a dash or a blank sits carry the same figures
        fits = list({tuple(c if c != '-' else '' for c in f): f for f in fits}.values())
        if len(fits) != 1:
            fail('%s p%d: line %s (%d of %d figures) fits %d arrangements' % (
                doc, page, no, len(vals), n, len(fits)))
            continue
        table.append((no, lab, fits[0], 'printed with a blank cell; placed in the one arrangement '
                      'its column TOTALS allow'))
    for k, d in enumerate(diff or []):
        if d != '-' and cols[k][1] == A:
            DIFFS.append((doc, page, cols[k][0], D(d), D(total[k])))
    for k, (fy, meas, h) in enumerate(cols):
        gap = D(total[k]) - sum(D(v[k]) for _, _, v, _ in table)
        if (doc, page, h) in NOT_CLOSED:
            if gap == 0 or abs(gap) <= 1:
                fail('%s p%d %s closes now; take it out of NOT_CLOSED' % (doc, page, h))
            NOT_CLOSED_SEEN.add((doc, page, h))
            continue
        if gap == 0:
            tie = 'column sums to the TOTAL Local Receipts line printed on the page'
        elif abs(gap) <= 1:
            tie = ('column against the printed TOTAL Local Receipts: %s (printed differs by $%s)'
                   % (TOLERANCE_PHRASE, abs(gap)))
        else:
            fail('%s p%d: column %s sums to %s, TOTAL prints %s' % (
                doc, page, h, total[k] and sum(D(v[k]) for _, _, v, _ in table), total[k]))
            continue
        for no, lab, vals, how in table:
            if vals[k] == '-':
                continue
            emit(fy, lab, meas, h, D(vals[k]), doc, 'p%d' % page,
                 'line %s. %s, column %s (%s)' % (no, lab, h, how),
                 'presentation: Town Manager budget message', tie)


# ================================================================================================
# 5. Totals only: the Town Manager's revenue/expense workbook, the "Local Receipts" row. Read
#    from town-budget-versions.csv, which carries every sheet of that workbook; one row per
#    printed column, from the last sheet (4.2.20), whose earlier columns repeat every sheet's.
# ================================================================================================
WB_DOC = FC + 'fy25-budget/town-manager-material/line-item-detail-2-13-24.xlsx'
WB_SHEET = 'Rev-Exp 4.2.20'


def workbook_totals():
    seen = set()
    for r in csv.DictReader(io.open(VERSIONS, encoding='utf-8')):
        if r['sheet'] != WB_SHEET or r['description'] != 'Local Receipts':
            continue
        col = r['column'].strip()
        m = re.match(r'FY ?(\d\d)', col)
        if not m or col in seen:
            continue
        seen.add(col)
        meas = 'actual' if 'ACTUAL' in col else 'estimate'
        emit(2000 + int(m.group(1)), 'Local Receipts', meas, col, Decimal(r['value']), WB_DOC,
             'sheet %s' % WB_SHEET, 'row Local Receipts, column %s' % col,
             'workbook: Town Manager revenue/expense sheet', 'total only; no parts printed')
    if not seen:
        fail('workbook: no Local Receipts row read from %s' % VERSIONS)


# Surveyed, and not read into the table -- with the reason (rule 13c). Duplicates of a table
# that IS read are listed so a later survey does not mistake them for unread tables.
SKIPPED = [
    (FC + 'fy20-budget/fy20-4th-quarter-revised-summary-and-reports.pdf',
     'MUNIS FY2020 p12 printout; the OCR scatters cells away from their labels. Read it from the '
     'page images, tied to its GRAND TOTAL, as the FY2024 page was. FY2020 by type is read from '
     'the FY2022 and FY2023 budget messages meanwhile.'),
    (FC + 'fy20-budget/fy20-4th-quarter-summary-and-reports-1.pdf', 'the same printout as above'),
    (FC + 'fy27-budget/department-presentations/preliminary-budget-presentation-2.19.26/'
          'preliminary-budget-presentation-2.19.26-final-v.2.27.26.pptx', 'duplicate of -final.pptx'),
    (FC + 'fy27-budget/department-presentations/preliminary-budget-presentation-2.19.26/'
          'preliminary-budget-presentation-2.19.26-final.pdf', 'PDF of the same deck'),
    ('town-budget/docs/3585 (FY27 preliminary budget presentation, pdf)', 'PDF of the 2.19.26 deck'),
    (FC + 'fy27-budget/triboard-material/preliminary-revenue-presentation.pptx',
     'its table is the FY26 deck\'s, figure for figure, under an FY27 title'),
    ('town-budget/docs/2419-fy24-year-end-report.pdf p7',
     'FY24 LOCAL RECEIPTS: the same MUNIS figures as p5, which is read, without roll back taxes'),
    ('town-budget/docs/a77, a74, a188, a136, a87, a84, a81',
     'presentation copies of the budget messages a76, a73, a187, a135, a89, a83, a85'),
    ('town-budget/docs/a193 p18', 'FY2020 projection against actual: the FY2020 Budget column of '
     'a193 p17 beside the FY2020 Actual of a76, both read'),
    ('town-budget/docs/a89 p7, a83 p9 (FY2017-FY2021)',
     'columns headed "After Recap": not established whether that means collected or the '
     'estimate as set at the recap, and the two documents disagree for FY2017 and FY2019'),
    ('town-budget/docs/a112, a113, a114, a116, a118, a120 (FY2008-FY2020)',
     'by-type tables whose column headings did not survive text extraction, or are scattered '
     'one cell per line; read them from the page images. a113 p4 is the FY2015 tax recap page 3 '
     '(DOR form, actual FY2014 and estimated FY2015) with lines 1 and 2 lost in extraction'),
    ('town-budget/docs/a53, a62, a64-a66, a72, a79, a82, a85, a91, a115, a138, a157, a162, '
     'a168, a170-a172, a189, 1591, 3765, 4090',
     'a single Local Receipts total per year; the workbook series covers FY2003-FY2021, and '
     'these later totals are not yet read'),
    (FC + 'fy26-budget/draft-rev-dist.-proj-fy26-update-2.27.25.xlsx',
     'totals only, and its two sheets disagree about FY26 (3,261,689.5 and 3,360,524)'),
    ('town-annual-reports (FY2011-FY2025)',
     'the Treasurer prints cash receipts by account, with no estimate beside them; a different '
     'grain from a budget-to-actual comparison'),
]


def build():
    global ROWS
    ROWS = []
    munis_text(FY25_MUNIS, 2025)
    munis_fy24()
    audited_fy23()
    for d in DECKS:
        deck(*d)
    for d in DOR:
        dor(*d)
    workbook_totals()
    cross_checks()
    for k in NOT_CLOSED:
        if k not in NOT_CLOSED_SEEN:
            fail('NOT_CLOSED names %s p%d %s, which was not read' % k)
    ROWS.sort(key=lambda r: (r['fiscal_year'], r['measure'], r['document'], r['stage'], r['receipt_type']))
    return ROWS


def difference_lines():
    """A message's printed 'Difference: Actual over ...' beside actual minus each ESTIMATE held
    for that year. Reported, not asserted: the estimate is in another document, and a
    cross-document check takes no tolerance (notes/process/TOLERANCES.md)."""
    out = []
    for doc, page, fy, d, act in DIFFS:
        ests = defaultdict(Decimal)
        for r in ROWS:
            if (r['fiscal_year'] == fy and r['measure'] == 'estimate'
                    and r['basis'] == 'presentation: Town Manager budget message'):
                ests[(r['document'], r['stage'])] += Decimal(r['value'])
        out.append((doc, page, fy, d, [(k, act - e) for k, e in sorted(ests.items())]))
    return out


def cross_checks():
    """A deck's ACTUAL column against the MUNIS printout for the same year, category by
    category. The deck rounds FY2024 to the dollar; within 50 cents is rounding, nothing else."""
    munis = defaultdict(Decimal)
    for r in ROWS:
        if r['basis'].startswith('ledger') and r['measure'] == 'actual':
            munis[(r['fiscal_year'], r['category'])] += Decimal(r['value'])
    for r in ROWS:
        if r['basis'] == 'presentation: Town Manager budget deck' and r['measure'] == 'actual':
            m = munis.get((r['fiscal_year'], r['category']))
            if m is None:
                fail('cross-check: no MUNIS %s for %s' % (r['category'], r['fiscal_year']))
            elif m != Decimal(r['value']) and abs(m - Decimal(r['value'])) < 1:
                r['tie'] = ('equals the MUNIS printout for the year within $1 rounding tolerance '
                            '(the deck prints whole dollars)')
            elif m != Decimal(r['value']):
                fail('cross-check: deck %s %s %s against MUNIS %s' % (
                    r['fiscal_year'], r['category'], r['value'], m))


def proof_years():
    """For each year the state's free cash proof covers: CL#6 against what the table holds.

    CL#6 is the state's 'Excess/Shortfall Local Receipts'. For FY2024 it equals collections over
    the REVISED estimate INCLUDING tax liens and roll back taxes, to the dollar -- so that is the
    scope compared. It is printed beside the other scopes; nothing is forced to agree."""
    proof = {}
    for r in csv.DictReader(io.open(PROOF, encoding='utf-8')):
        if r['town'] == 'Lunenburg' and 'Local Receipts' in r['line']:
            proof[int(r['year'])] = Decimal(r['amount'])
    out = []
    for fy in sorted(proof):
        held = [r for r in ROWS if r['fiscal_year'] == fy and r['category'] != 'total']
        acts, ests = defaultdict(Decimal), defaultdict(Decimal)
        for r in held:
            key = (os.path.basename(r['document']), r['stage'])
            if r['measure'] == 'actual':
                acts[key] += Decimal(r['value'])
            elif r['measure'] == 'estimate':
                ests[key] += Decimal(r['value'])
        out.append({'fy': fy, 'cl6': proof[fy], 'pairs': [
            (a, av, e, ev) for a, av in sorted(acts.items()) for e, ev in sorted(ests.items())]})
    return out


def write(rows):
    tmp = OUT + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, FIELDS, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, OUT)


def render(rows):
    s = io.StringIO()
    w = csv.DictWriter(s, FIELDS, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    return s.getvalue()


def main():
    rows = build()
    if FAILS:
        print('REFUSED -- %d check(s) failed, nothing written:' % len(FAILS))
        for f in FAILS:
            print('  ' + f)
        return 1
    if '--proof' in sys.argv:
        print('Printed "Difference: Actual over ..." lines, beside actual minus each estimate held:')
        for doc, page, fy, d, comps in difference_lines():
            print('  FY%d  printed %s  (%s p%d)' % (fy, format(d, ','), os.path.basename(doc)[:40], page))
            for (edoc, stage), v in comps:
                print('        minus %-18s in %-40s = %s' % (stage, os.path.basename(edoc)[:40], format(v, ',')))
        print()
        for line in proof_years():
            print('FY%d  state CL#6 (excess/shortfall local receipts) %s' % (line['fy'], format(line['cl6'], ',')))
            if not line['pairs']:
                print('      nothing by type held for this year')
            for (ad, ast), av, (ed, est), ev in line['pairs']:
                d = av - ev
                print('      %-24s %-25s minus %-24s %-22s = %14s  %s' % (
                    ad[:24], ast[:25], ed[:24], est[:22], format(d, ',.2f'),
                    'EQUALS CL#6' if d == line['cl6'] else 'CL#6 differs by ' + format(line['cl6'] - d, '+,.2f')))
        return 0
    if '--check' in sys.argv:
        cur = io.open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if cur != render(rows):
            print('STALE: %s does not reproduce; run without --check' % os.path.relpath(OUT, ROOT))
            return 1
        print('OK: %d rows reproduce, every table tied, every deck actual equal to MUNIS or within $1 rounding tolerance'
              % len(rows))
        return 0
    write(rows)
    yrs = sorted({r['fiscal_year'] for r in rows})
    print('wrote %d rows, FY%d-FY%d, to %s' % (len(rows), yrs[0], yrs[-1], os.path.relpath(OUT, ROOT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
