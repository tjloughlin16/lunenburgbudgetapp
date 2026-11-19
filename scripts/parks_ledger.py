"""THE PARKS LEDGER, READ ONCE: funds 1500 (Park Revolving) and 1523 (Park Gift) posting by
posting, and the general fund's Parks department (650) account by account at the close.
Shared by scripts/build_parks_ledger.py (the fund pages and the two topic pages) so a figure on
a fund page and the same figure on a topic page are one computation (rule 7d).

    sources/data/munis-parks-journal.csv   our redacted reading of the Town's MUNIS journal for
                                           both funds, FY2023 to the FY2026 close (5 Nov 2026)
    sources/data/munis-ledger.csv          our tied reading of the period-13 general fund
                                           reports, FY2025 and FY2026 (department 650)

SIGNS. The journal prints a receipt as a credit (negative) and a payment as a debit. Every
function here turns them to the reader's: money IN positive, money OUT positive.

TWO READINGS HERE ARE OURS, and every caller labels them so:
  - the SALES MONTH of a registration deposit, read from the month its description names
    (`PROG/SEP2024 PARK MYREC CARD P` -> September 2024). The Town did not post by sales month;
    the clerk typed the month into the memo.
  - the PROGRAMME a payment was for, read from its description and payee (`SOCCER PROGRAMS`,
    `3 STEP SPORTS LLC` -> Soccer). Nothing in the books carries a programme code.
"""
import csv
import io
import os
import re
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'sources', 'data')
JOURNAL = os.path.join(D, 'munis-parks-journal.csv')
LEDGER = os.path.join(D, 'munis-ledger.csv')
YEARS = (2023, 2024, 2025, 2026)
MON = ['Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
MONTH_NO = [7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6]
LONG_MON = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June', 7: 'July',
            8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'}


def fail(msg):
    raise SystemExit('parks_ledger: ' + msg)


def rows():
    return list(csv.DictReader(io.open(JOURNAL, encoding='utf-8')))


# ----------------------------------------------------------------- what each posting IS
# (source code, posts_to) -> (kind id, label). Read off the journal's own source column; the
# meanings are MUNIS's (CRP cash receipt, API invoice, BUA budget, PO* purchase orders).
KINDS = [
    ('in', 'Money in', 'a receipt deposited to the fund, net of any refund on the same line'),
    ('out', 'Money out', 'a payment to a vendor, or a journal entry moving cost in or out'),
    ('order', 'Purchase orders', 'money set aside for an order, and released as it is paid; '
                                 'not spending in itself'),
    ('limit', 'Spending limit', 'the amount the fund was authorised to spend that year'),
]


def kind(r):
    s, p = r['source'], r['posts_to']
    if p == 'actual':
        return 'in' if r['side'] == 'revenue' else 'out'
    if p == 'encumbrance':
        return 'order'
    if p == 'transfer':
        return 'limit'
    fail('a posting this module does not know: source %s, posts_to %s' % (s, p))


SOURCE_LABEL = {'CRP': 'Receipt', 'API': 'Invoice paid', 'APM': 'Invoice corrected',
                'GEN': 'Journal entry', 'BUA': 'Budget posted', 'POE': 'Order opened',
                'POL': 'Order paid down', 'POM': 'Order changed', 'SOY': 'Order carried in',
                'YEC': 'Order closed at year end'}


def reader_amount(r):
    """Money in positive for a receipt; money out positive for a payment; an order or a budget
    as the journal prints it."""
    a = float(r['amount'])
    return -a if r['side'] == 'revenue' else a


# ----------------------------------------------------------------- registration deposits
_MONTH = {'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'PRIL': 4, 'MAY': 5, 'JUN': 6, 'JUL': 7,
          'AUG': 8, 'SEP': 9, 'OC': 10, 'NOV': 11, 'DEC': 12}
_MONTH_RE = re.compile(r'(?:^|[/ ])(JAN|FEB|MAR|APR|PRIL|MAY|JUN|JUL|AUG|SEP|OC|NOV|DEC)'
                       r'[A-Z]*\s?(20\d\d|\d\d)(?!\d)')


def is_myrec(r):
    """A registration-system line: a deposit, a refund or a card charge. The memo is cut at thirty
    characters, so `MYREC` is often truncated away (`RPOG REFUND/JULY2025 PARK MYRE`, `PROG/DEC2024
    CHARGES PARK MYRE`); a fee line that names a month of sales is one too. Reading only `MYREC`
    left out $2,901.35 of FY2025 refunds and charges; with them counted the books come to within
    $45.34 of MyRec's own FY2025 sales reports (build_parks_topics.py, registration-sales, pins it)."""
    if r['fund'] != '1500' or r['side'] != 'revenue' or r['account_description'] == 'INVESTMENT INCOME':
        return False
    return 'MYREC' in r['description'].replace(' ', '') or sales_month(r['description']) is not None


def sales_month(desc):
    """(fiscal year of the sale, calendar month) named in a MyRec deposit's description."""
    m = _MONTH_RE.search(desc)
    if not m:
        return None
    mo = _MONTH[m.group(1)]
    y = int(m.group(2))
    y = y + 2000 if y < 100 else y
    return (y + 1 if mo >= 7 else y), mo


def myrec_kind(r):
    a = reader_amount(r)
    if a > 0:
        return 'deposit'
    return 'refund' if 'REF' in r['description'] or 'RPOG' in r['description'] else 'charge'


def sales_months():
    """{(sale fy, month): [row, ...]}: every MyRec line placed under the month its description
    names, whichever year it posted in, plus the same-day corrections that undo a duplicate
    deposit (`PARK REVOLVING USER FEES`, equal and opposite to a MyRec line posted that day).
    Refuses if any MyRec line names no month, or a correction matches nothing."""
    R = rows()
    out = defaultdict(list)
    by_day = defaultdict(list)
    for r in R:
        if not is_myrec(r):
            continue
        sm = sales_month(r['description'])
        if not sm:
            fail('a registration deposit names no month: %r' % r['description'])
        out[sm].append(r)
        by_day[r['effective_date']].append((sm, r))
    for r in R:
        if r['fund'] == '1500' and r['side'] == 'revenue' and r['description'] == 'PARK REVOLVING USER FEES':
            hit = [sm for sm, m in by_day[r['effective_date']]
                   if abs(abs(float(m['amount'])) - abs(float(r['amount']))) < 0.005
                   and (float(m['amount']) > 0) != (float(r['amount']) > 0)]
            if not hit:
                fail('a same-day correction matches no registration deposit: %s %s'
                     % (r['effective_date'], r['amount']))
            out[hit[0]].append(dict(r, _correction='1'))
    return out


def month_grid():
    """{fy: [{'mo', 'net', 'deposits', 'lines'}] x 12} for the four years, July first. `net` is
    every line placed there, refunds, card charges and corrections included."""
    sm = sales_months()
    out = {}
    for fy in YEARS:
        cells = []
        for mo in MONTH_NO:
            ls = sorted(sm.get((fy, mo), []), key=lambda r: (r['effective_date'], r['amount']))
            dep = sum(reader_amount(r) for r in ls if not r.get('_correction') and myrec_kind(r) == 'deposit')
            net = sum(reader_amount(r) for r in ls)
            cells.append(dict(mo=mo, net=round(net, 2), deposits=round(dep, 2), lines=ls))
        out[fy] = cells
    return out


# ----------------------------------------------------------------- what payments were FOR
# OUR READING, first match wins: (group, words in the payee or the description). Nothing in
# the books carries a programme; every caller says so beside the figures.
PROGRAMMES = [
    ('Soccer', ('SOCCER',)),
    ('STEM and science', ('STEM', 'SCIENCE')),
    ('Multisports', ('MULTISPORT',)),
    ('Art', ('ART PROGRAM', 'PAINT NI')),
    ('Yoga', ('YOGA',)),
    ('Junior zookeepers', ('ZOOKEEPER',)),
    ('Spring fair', ('SPRING FAIR',)),
    ('Movie nights and events', ('MOVIE', 'CARDBOAR', 'REC DIRECTOR PROGR')),
    ('Beach staff and swim', ('BEACH SALAR', 'BEACH OVERAGE', '1P24', 'LIFEGUARD', 'WSI',
                              'SWIM')),
    ('Beach building', ('TOWN BEACH BUILDIN',)),
    ('Repairs and grounds', ('REPAIR', 'MARSHALL PARK', 'VETERANS PARK', 'PLAYGROUND', 'DOORS',
                             'ELECTRICITY', 'SIGN FOR', 'FLAGS', 'CLEANING')),
    ('Registration system', ('MYRECDEPT', 'MY REC', 'MYREC')),
    ('Supplies', ('SUPPLI', 'SUP', 'P-CARD')),
    ('Moved by journal entry', ('ADJ EXP',)),
]
PROGRAMME_NAMES = [p for p, _ in PROGRAMMES]


def programme(r):
    hay = ' '.join((r['vendor'], r['description'], r['account_description'], r['doc_no'])).upper()
    for name, words in PROGRAMMES:
        if any(w in hay for w in words):
            return name
    fail('a payment no programme rule reads: %s %r %r' % (r['effective_date'], r['vendor'], r['description']))


def payments(fund='1500'):
    return [r for r in rows() if r['fund'] == fund and r['side'] == 'expense' and r['posts_to'] == 'actual']


def spend_by_programme():
    """{fy: {programme: dollars}}; refuses unless each year sums to the fund's payments."""
    out = {fy: defaultdict(float) for fy in YEARS}
    tot = defaultdict(float)
    for r in payments():
        fy = int(r['fiscal_year'])
        out[fy][programme(r)] += float(r['amount'])
        tot[fy] += float(r['amount'])
    for fy in YEARS:
        if abs(sum(out[fy].values()) - tot[fy]) > 0.005:
            fail('FY%d: programmes do not sum to the payments' % fy)
    return {fy: {k: round(v, 2) for k, v in out[fy].items()} for fy in YEARS}


# The FY2025 MyRec products a programme group sold, by the words in the product name -- the
# same reading, applied to the sales report. A product no rule reads stays `Other programmes`.
SALES_GROUP = [
    ('Soccer', ('SOCCER',)),
    ('STEM and science', ('STEM', 'SCIENCE')),
    ('Multisports', ('MA SPORTS LEAGUES', 'MULTISPORT')),
    ('Art', ('PAINTED GOAT', 'ART')),
    ('Yoga', ('YOGA',)),
    ('Junior zookeepers', ('ZOOKEEPER',)),
    ('Beach staff and swim', ('SWIM', 'BEACH')),
]


def sales_group(name):
    u = name.upper()
    for g, words in SALES_GROUP:
        if any(w in u for w in words):
            return g
    return 'Other programmes'


def myrec_sales():
    """[(group, product, total)] from the FY2025 MyRec program and membership reports."""
    out = []
    for r in csv.DictReader(io.open(os.path.join(D, 'parks-myrec-sales-fy2025.csv'), encoding='utf-8')):
        out.append((sales_group(r['program']), r['program'], float(r['total'])))
    return out


# ----------------------------------------------------------------- department 650
GF_COLS = ('original', 'transfers', 'revised', 'expended', 'encumbered', 'available')


def dept650():
    """{fy: [account row]} at the close (period 13), FY2025 and FY2026, in the report's order.
    Each account must foot: revised - expended - encumbered = available."""
    out = defaultdict(list)
    for r in csv.DictReader(io.open(LEDGER, encoding='utf-8')):
        if (r['dept'] == '650' and r['level'] == 'account' and r['account_type'] == 'expense'
                and r['period'] == '13' and r['fund'] == '0100'):
            x = dict(account=r['account'], object=r['object'], name=r['name'], doc=r['doc_id'],
                     **{c: round(float(r[c] or 0), 2) for c in GF_COLS})
            if abs(x['revised'] - x['expended'] - x['encumbered'] - x['available']) > 0.005:
                fail('department 650 account %s FY%s does not foot' % (r['account'], r['fy']))
            if abs(x['original'] + x['transfers'] - x['revised']) > 0.005:
                fail('department 650 account %s FY%s: voted + transfers != budget' % (r['account'], r['fy']))
            out[int(r['fy'])].append(x)
    if sorted(out) != [2025, 2026]:
        fail('department 650 at the close is not FY2025 and FY2026: %s' % sorted(out))
    return dict(out)
