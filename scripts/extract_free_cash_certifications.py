#!/usr/bin/env python3
"""Lunenburg's free cash certifications, 1 July 2014 to 1 July 2025, every printed line.

    python3 scripts/extract_free_cash_certifications.py           # write
    python3 scripts/extract_free_cash_certifications.py --check   # reproduce byte for byte

Writes sources/data/free-cash-certifications.csv from the twelve PDFs in sources/state-dls/
named `free-cash-worksheet-lunenburg-<as-of>.pdf` and
`free-cash-certification-lunenburg-fy<N>-as-of-<as-of>.pdf` (see that folder's PROVENANCE.md
for where they came from: the DLS Gateway's City & Town Free Cash Report, jurisdiction 162).

WHAT IS IN THEM. Each document is the Division of Local Services' calculation of the
town's free cash: the general fund's unreserved fund balance, less the receivables that
are not yet cash, plus deferred revenue, giving the certified figure. Then one page (or
two) per enterprise fund calculating its retained earnings. Two formats:

  * 2014-2020: the older worksheet. Whole dollars. The result is printed as
    `FREE CASH, JULY 1, <year>`, so the as-of date is stated on the page.
  * 2021-2025: the Gateway's newer `Free Cash Calculation - Fiscal Year <N>`, with cents.
    The result is printed as `Free Cash Calculation for <N-1>`. So "Fiscal Year 2026" is
    the year the money can be SPENT in, and the balance is the one at the close of FY2025,
    i.e. 1 July 2025. That reading is checked, not assumed: this script asserts the
    printed `for <year>` equals N-1 for every document, and the cross-check below shows the
    state's own Free Cash Proof (`free-cash-proof.csv`, year 2025) and the Town's fact sheet
    (fiscal year 2026) both carry the FY2026 document's figure.

THE CHECKS, and nothing is written for a year that fails one.

  General fund, every year:
    (a) the itemised lines of each sub-list (other receivables; other receivables in
        deferred revenue; adjustments) sum to the total the page prints for that list;
    (b) opening balance - personal property receivable - real estate receivable
        - every receivables sub-total - free cash voted not recorded
        + deferred revenue + 60 days collections + adjustments total
        = the printed free cash result.
  Enterprise funds, every fund on every document:
    Part I:  cash - liabilities + other = the printed Part I total
             (newer form: liabilities sum to their printed Total, and cash - that Total =
             `Cash less Current Liabilities`);
    Part II: retained earnings - receivables + other = the printed Part II total
             (newer form likewise, against `Undesignated Retained Earnings Less Accounts
             Receivable`);
    Part III: fixed asset variance = debits - credits;
    and Part I's total equals Part II's, which is what the form exists to show.

  SIGNS ARE POSITIONAL, as the form lays them out: a line in a SUBTRACT block subtracts; a
  line under OTHER is added with the sign printed on it (`(207)` is -207). Labels such as
  `Add due from the General Fund` agree with that; nothing here reads a sign off a label.

  A PRINTED DASH IS NOT A NUMBER. Where the form prints `-` in an amount cell the row's
  `amount` is EMPTY and `amount_note` says `printed as a dash`; where it prints nothing,
  `amount` is empty and the note says `nothing printed`. The arithmetic above counts both
  as zero, and that is the only place a zero is supplied.

  TOLERANCE: notes/process/TOLERANCES.md. An identity may close within $1.00 only when it
  says so, in the words `within $1 rounding tolerance (printed differs by $N)`, in the
  row's `check` column. The older worksheets print whole dollars rounded from cents, so a
  footing can miss by a dollar; that is the likely cause and it is a hypothesis.

  THIS ALLOWANCE IS NOT YET IN TOLERANCES.md's TABLE. Its policy line covers "a printed
  total, or a row's own printed identity", which is what these are, but the table lists
  where the allowance is coded and this file is not on it. Approval of that row is TJ's.

READING THE PAGES. Every page has a text layer (`pdf_kind.py`: digital, every page `text`);
nothing here OCRs, and a page that needed it would stop the run. The older worksheets draw
their padding spaces ON TOP of the digits, so a naive text dump reads `411,310` as
`4 11,310`. This script ignores space glyphs entirely and rebuilds cells from the position
of the visible characters: a gap wider than GAP points starts a new cell.
"""
import argparse
import csv
import io
import os
import re
import sys
from decimal import Decimal

import pdfplumber

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'sources')
OUT = os.path.join(SRC, 'data', 'free-cash-certifications.csv')
FACT_SHEET = os.path.join(SRC, 'data', 'free-cash-history-fincom.csv')
PROOF = os.path.join(SRC, 'data', 'free-cash-proof.csv')

# (archive key, the as-of date the document is expected to state, format)
DOCS = [
    ('state-dls/free-cash-worksheet-lunenburg-2014-07-01.pdf', '2014-07-01', 'worksheet'),
    ('state-dls/free-cash-worksheet-lunenburg-2015-07-01.pdf', '2015-07-01', 'worksheet'),
    ('state-dls/free-cash-worksheet-lunenburg-2016-07-01.pdf', '2016-07-01', 'worksheet'),
    ('state-dls/free-cash-worksheet-lunenburg-2017-07-01.pdf', '2017-07-01', 'worksheet'),
    ('state-dls/free-cash-worksheet-lunenburg-2018-07-01.pdf', '2018-07-01', 'worksheet'),
    ('state-dls/free-cash-worksheet-lunenburg-2019-07-01.pdf', '2019-07-01', 'worksheet'),
    ('state-dls/free-cash-worksheet-lunenburg-2020-07-01.pdf', '2020-07-01', 'worksheet'),
    ('state-dls/free-cash-certification-lunenburg-fy2022-as-of-2021-07-01.pdf', '2021-07-01', 'gateway'),
    ('state-dls/free-cash-certification-lunenburg-fy2023-as-of-2022-07-01.pdf', '2022-07-01', 'gateway'),
    ('state-dls/free-cash-certification-lunenburg-fy2024-as-of-2023-07-01.pdf', '2023-07-01', 'gateway'),
    ('state-dls/free-cash-certification-lunenburg-fy2025-as-of-2024-07-01.pdf', '2024-07-01', 'gateway'),
    ('state-dls/free-cash-certification-lunenburg-fy2026-as-of-2025-07-01.pdf', '2025-07-01', 'gateway'),
]

FIELDS = ['as_of', 'document', 'page', 'top_pt', 'section', 'role', 'line', 'printed',
          'amount', 'amount_note', 'check']

GAP = 4.0              # points of white space that separate two cells on one row
TOLERANCE = Decimal('1.00')
TOLERANCE_PHRASE = 'within $1 rounding tolerance'   # notes/process/TOLERANCES.md: do not reword
NUM = re.compile(r'^\(?-?\$?[\d,]+(?:\.\d+)?\)?$')
TRAILING_NUM = re.compile(r'^(.*?[A-Za-z\)\.:])\s*(\(?[\d,]+(?:\.\d\d)?\)?)$')


class Refused(Exception):
    pass


# ---------------------------------------------------------------- reading the page

def cells(page):
    """[(top, [(x0, x1, text), ...]), ...] built from visible glyphs only."""
    rows = {}
    for c in page.chars:
        if not c['text'].strip():
            continue
        key = round(c['top'])
        for k in (key - 1, key + 1):
            if k in rows:
                key = k
                break
        rows.setdefault(key, []).append(c)
    out = []
    for top in sorted(rows):
        cs = sorted(rows[top], key=lambda c: c['x0'])
        groups, cur = [], [cs[0]]
        for c in cs[1:]:
            if c['x0'] - cur[-1]['x1'] > GAP:
                groups.append(cur)
                cur = [c]
            else:
                cur.append(c)
        groups.append(cur)
        row = []
        for g in groups:
            t, prev = '', None
            for c in g:
                if prev is not None and c['x0'] - prev['x1'] > 1.2:
                    t += ' '
                t += c['text']
                prev = c
            row.append((g[0]['x0'], g[-1]['x1'], t))
        out.append((top, row))
    return out


def is_amount(t):
    return t == '-' or bool(NUM.match(t))


def parse(printed):
    """(amount as Decimal or None, note)."""
    if printed == '':
        return None, 'nothing printed'
    if printed == '-':
        return None, 'printed as a dash'
    t = printed.replace('$', '').replace(',', '')
    neg = t.startswith('(') and t.endswith(')')
    t = t.strip('()')
    d = Decimal(t)
    if neg:
        return -d, 'printed in parentheses (negative)'
    return d, ''


def fmt(d, printed=''):
    if d is None:
        return ''
    if '.' in printed:
        return f'{d:.2f}'
    return str(d.quantize(Decimal(1)))


def money(d):
    s = f'{abs(d):,.2f}'
    if s.endswith('.00'):
        s = s[:-3]
    return ('-' if d < 0 else '') + s


def val(r):
    return r['_amount'] if r['_amount'] is not None else Decimal(0)


def closes(computed, printed_amt):
    """('ties' | 'within ... (printed differs by $N)' | None)."""
    diff = abs(computed - printed_amt)
    if diff == 0:
        return 'ties'
    if diff <= TOLERANCE:
        return f'{TOLERANCE_PHRASE} (printed differs by ${money(diff)})'
    return None


# ---------------------------------------------------------------- rows

class Doc:
    def __init__(self, key, as_of):
        self.key, self.as_of, self.rows = key, as_of, []

    def add(self, page, top, section, role, line, printed):
        amt, note = parse(printed)
        r = {'as_of': self.as_of, 'document': self.key, 'page': page,
             'top_pt': f'{top}', 'section': section, 'role': role, 'line': line,
             'printed': printed, 'amount': fmt(amt, printed), 'amount_note': note,
             'check': '', '_amount': amt}
        self.rows.append(r)
        return r


# ---------------------------------------------------------------- the older worksheet

def worksheet(pdf, doc):
    pages = pdf.pages
    general_fund_worksheet(pages[0], doc)
    for n in range(2, len(pages) + 1):
        enterprise_worksheet(pages[n - 1], n, doc)


def split_merged(x0, x1, t, right_edges):
    """A label that runs into its own amount: `Perpetual Care Income - Expendable1,052`.
    Split only where the cell ENDS at an amount column's right edge, so it must hold the
    amount, and only off a trailing number."""
    if any(abs(x1 - r) < 1.5 for r in right_edges):
        m = TRAILING_NUM.match(t)
        if m and m.group(1).strip():
            return [(x0, x1, m.group(1).strip(), False), (x1, x1, m.group(2), True)]
    return [(x0, x1, t, is_amount(t))]


def general_fund_worksheet(page, doc):
    rows = cells(page)
    # Amount columns by their right edge: itemised (left), second list, totals (right).
    nums = [(x1) for _, row in rows for (x0, x1, t) in row if is_amount(t)]
    if not nums:
        raise Refused('no amounts on page 1')

    def col(x1):
        return 'c1' if x1 < 300 else 'c2' if x1 < 450 else 'c3'

    edges = sorted({round(max(x for x in nums if col(x) == c), 1)
                    for c in ('c1', 'c2', 'c3') if any(col(x) == c for x in nums)})
    started, section, pending_result, done = False, None, None, False
    for top, row in rows:
        parts = []
        for x0, x1, t in row:
            parts.extend(split_merged(x0, x1, t, edges))
        labels = [(x0, t) for x0, x1, t, a in parts if not a]
        amts = {}
        for x0, x1, t, a in parts:
            if a:
                amts[col(x1)] = t
        text = ' '.join(t for _, t in labels)
        up = text.upper()
        if not started:
            started = up.startswith('FREE CASH CALCULATION')
            continue
        if done:
            continue
        m = re.match(r'FREE CASH, JULY 1, (\d{4})$', up)
        if m:
            stated = f'{m.group(1)}-07-01'
            if stated != doc.as_of:
                raise Refused(f'page states {stated}, filename says {doc.as_of}')
            if pending_result is None:
                raise Refused('no result figure above FREE CASH, JULY 1')
            ptop, printed = pending_result
            doc.add(1, ptop, 'result', 'result', text, printed)
            done = True
            continue
        if up == 'BEGIN:':
            section = 'begin'; continue
        if up in ('LESS:',):
            section = 'less'; continue
        if up == 'ADD:':
            section = 'add'; continue
        # Headers carry no amount. `Other receivables` is also an ITEM in 2014-2016, with
        # one, which is why the header is matched on its full wording.
        if up.startswith('OTHER RECEIVABLES IN DEFERRED REVENUE') and not amts:
            section = 'other receivables in deferred revenue'; continue
        if up.startswith('OTHER RECEIVABLE') and 'OVERDRAWN' in up and not amts:
            section = 'other receivables'; continue
        if up.startswith('OTHER MISCELLANEOUS ADJUSTMENTS') or up.startswith('CIRCUIT BREAKER'):
            section = 'adjustments'; continue
        if up.startswith('FREE CASH VOTED'):
            doc.add(1, top, 'less', 'subtract', text, amts.get('c3', ''))
            section = 'less'; continue
        if up.startswith('DEFERRED REVENUE') or up.startswith('60 DAYS'):
            doc.add(1, top, 'add', 'add', text, amts.get('c3', ''))
            section = 'add'; continue
        if section == 'begin' and labels:
            doc.add(1, top, 'begin', 'opening', text, amts.get('c3', ''))
            continue
        if section == 'less' and labels:
            doc.add(1, top, 'less', 'subtract', text, amts.get('c3', ''))
            continue
        # THE RESULT is a figure alone in the totals column with nothing else on its row;
        # a sub-list's total shares its row with the sub-list's own blank cells.
        if not labels and set(amts) == {'c3'} and amts['c3'] != '-':
            pending_result = (top, amts['c3'])
            continue
        if section in ('other receivables', 'other receivables in deferred revenue', 'adjustments'):
            left = [t for x0, t in labels if x0 < 225]
            right = [t for x0, t in labels if 225 <= x0 < 330]
            if left:
                doc.add(1, top, section, 'item', ' '.join(left), amts.get('c1', amts.get('c2', '')))
            if right:
                doc.add(1, top, section, 'item', ' '.join(right), amts.get('c2', ''))
            if 'c3' in amts:
                doc.add(1, top, section, 'subtotal', '(total; no label printed)', amts['c3'])
            continue
        if labels:
            raise Refused(f'p1 y={top}: line {text!r} falls in no section')
    if not done:
        raise Refused('no FREE CASH, JULY 1 line found')


def enterprise_worksheet(page, n, doc):
    rows = cells(page)
    fund = None
    for top, row in rows:
        ts = [t for _, _, t in row]
        if 'FUND' in ts and ts.index('FUND') + 1 < len(ts):
            fund = ts[ts.index('FUND') + 1]
            break
    if not fund:
        raise Refused(f'page {n}: no FUND named')
    section = f'enterprise:{fund}'
    started, part, block = False, None, None
    for top, row in rows:
        labels = [(x0, t) for x0, x1, t in row if not is_amount(t)]
        amts = [(x1, t) for x0, x1, t in row if is_amount(t)]
        text = ' '.join(t for _, t in labels)
        up = text.upper()
        if not started:
            started = up.startswith('RETAINED EARNINGS CALCULATION')
            continue
        if up == 'PART I':
            part, block = 'I', None; continue
        if up == 'PART II':
            part, block = 'II', None; continue
        if up == 'PART III':
            part, block = 'III', None; continue
        if up == 'SUBTRACT:':
            block = 'subtract'; continue
        if up == 'OTHER':
            block = 'other'; continue
        if up in ('CURRENT LIABILITIES, DESIGNATIONS OF FUND BALANCE',
                  'ACCOUNTS RECEIVABLE (NET)', 'FIXED ASSETS:') and not amts:
            continue
        if part == 'III':
            if up == 'DEBITS CREDITS':
                continue
            if up == 'TOTAL':
                left = [t for x1, t in amts if x1 < 300]
                right = [t for x1, t in amts if x1 >= 450]
                doc.add(n, top, section, 'part III debits total', 'Total (debits)', left[0] if left else '')
                doc.add(n, top, section, 'part III credits total', 'Total (credits)', right[0] if right else '')
                continue
            if up == 'FIXED ASSET VARIANCE':
                doc.add(n, top, section, 'part III variance', text, amts[0][1] if amts else '')
                return
            if labels and amts:
                raise Refused(f'p{n} y={top}: fixed asset line {text!r} not handled')
            continue
        if part is None or not labels:
            continue
        a = amts[-1][1] if amts else ''
        if up == 'CASH' and part == 'I':
            doc.add(n, top, section, 'part I cash', text, a); continue
        if up == 'RETAINED EARNINGS - UNDESIGNATED' and part == 'II':
            doc.add(n, top, section, 'part II retained earnings', text, a); continue
        if up == 'TOTAL':
            doc.add(n, top, section, f'part {part} total', text, a); continue
        if block == 'subtract':
            doc.add(n, top, section, f'part {part} subtract', text, a); continue
        if block == 'other':
            doc.add(n, top, section, f'part {part} other', text, a); continue
        raise Refused(f'p{n} y={top}: line {text!r} falls in no block')
    raise Refused(f'page {n}: no FIXED ASSET VARIANCE line')


# ---------------------------------------------------------------- the newer Gateway form

FURNITURE = ('MASSACHUSETTS DEPARTMENT', 'DIVISION OF LOCAL', 'TOWN', 'LUNENBURG',
             'FREE CASH CERTIFICATION', 'PRINTED ON', 'PAGE ')


def gateway(pdf, doc):
    fy = None
    section, role_block, fund, part = 'general', None, None, None
    gf_section = None
    for n, page in enumerate(pdf.pages, 1):
        for top, row in cells(page):
            labels = [t for x0, x1, t in row if not is_amount(t)]
            amts = [(x1, t) for x0, x1, t in row if is_amount(t)]
            text = ' '.join(labels)
            up = text.upper()
            # page furniture, wherever it falls. `Page 3 of | 10` puts a number in a cell of
            # its own, so the printed-on line is matched whether or not it carries one.
            if up.startswith('PRINTED ON') or (not amts and up.startswith(FURNITURE)):
                continue
            m = re.match(r'^Free Cash Calculation - Fiscal Year (\d{4})$', text)
            if m:
                fy = int(m.group(1))
                expect = f'{fy - 1}-07-01'
                if expect != doc.as_of:
                    raise Refused(f'Fiscal Year {fy} implies {expect}; filename says {doc.as_of}')
                continue
            m = re.match(r'^Retained Earnings Calculation - (.+) - Fiscal Year (\d{4})$', text)
            if m:
                if int(m.group(2)) != fy:
                    raise Refused(f'p{n}: enterprise page for FY{m.group(2)} in an FY{fy} document')
                if m.group(1) != fund:
                    fund, part, role_block = m.group(1), None, None
                section = f'enterprise:{fund}'
                continue
            if up.startswith('REVIEWED BY') or up.startswith('CERTIFIED ON'):
                continue
            a = amts[-1][1] if amts else ''
            if section == 'general':
                if text == 'Begin:':
                    gf_section = 'begin'; continue
                if text == 'Subtract:':
                    gf_section = 'less'; continue
                if text == 'Add:':
                    gf_section = 'add'; continue
                if text == 'Other Receivables in Deferred Revenue':
                    gf_section = 'other receivables in deferred revenue'; continue
                if text.endswith('Other Receivables, Overdrawn Accounts, Deficits'):
                    gf_section = 'other receivables'; continue
                if text.startswith('Circuit Breaker, Other Closed Accounts, Adjustments'):
                    gf_section = 'adjustments'; continue
                m = re.match(r'^Free Cash Calculation for (\d{4})$', text)
                if m:
                    if int(m.group(1)) != fy - 1:
                        raise Refused(f'result says for {m.group(1)} in an FY{fy} document')
                    doc.add(n, top, 'result', 'result', text, a)
                    continue
                if text.startswith('Free Cash Voted from Town Meeting Not Recorded'):
                    doc.add(n, top, 'less', 'subtract', text, a); gf_section = 'less'; continue
                if text.startswith('Deferred Revenue'):
                    doc.add(n, top, 'add', 'add', text, a); gf_section = 'add'; continue
                if gf_section == 'begin' and text:
                    doc.add(n, top, 'begin', 'opening', text, a); continue
                if gf_section == 'less' and text:
                    doc.add(n, top, 'less', 'subtract', text, a); continue
                if gf_section in ('other receivables', 'other receivables in deferred revenue',
                                  'adjustments'):
                    if text == 'Total':
                        doc.add(n, top, gf_section, 'subtotal', text, a)
                    elif amts:
                        doc.add(n, top, gf_section, 'item', text or '(no label printed)', a)
                    continue
                if text or amts:
                    raise Refused(f'p{n} y={top}: line {text!r} falls in no section')
                continue
            # an enterprise fund
            if text.startswith(('Enterprise Fund Number', 'Type of Enterprise Fund',
                                'Name of Enterprise Fund')):
                continue
            if text == 'Part I Cash':
                part, role_block = 'I', None
                doc.add(n, top, section, 'part I cash', text, a); continue
            if text.startswith('Current Liabilities, Designations of Fund Balance'):
                role_block = 'subtract'; continue
            if text == 'Cash less Current Liabilities':
                doc.add(n, top, section, 'part I total', text, a); role_block = None; continue
            if text == 'Part II Retained Earnings, Undesignated':
                part, role_block = 'II', None
                doc.add(n, top, section, 'part II retained earnings', text, a); continue
            if text.startswith('Accounts Receivable (net)'):
                role_block = 'subtract'; continue
            if text == 'Undesignated Retained Earnings Less Accounts Receivable':
                doc.add(n, top, section, 'part II total', text, a); role_block = None; continue
            if text == 'Fixed Assets':
                part, role_block = 'III', None; continue
            if text == 'Debits:':
                role_block = 'debits'; continue
            if text == 'Credits:':
                role_block = 'credits'; continue
            if text.startswith('Fixed Assets Variance'):
                doc.add(n, top, section, 'part III variance', text, a); continue
            if text in ('Other Liabilities', 'Other Accounts Receivable') and not amts:
                continue
            if text == 'Total':
                if part in ('I', 'II') and role_block == 'subtract':
                    doc.add(n, top, section, f'part {part} subtract total', text, a)
                elif part == 'III' and role_block in ('debits', 'credits'):
                    doc.add(n, top, section, f'part III {role_block} total', text, a)
                else:
                    raise Refused(f'p{n} y={top}: a Total outside any block')
                continue
            if amts and role_block == 'subtract' and part in ('I', 'II'):
                doc.add(n, top, section, f'part {part} subtract', text or '(no label printed)', a)
                continue
            if amts and part == 'III' and role_block in ('debits', 'credits'):
                doc.add(n, top, section, f'part III {role_block[:-1]}', text or '(no label printed)', a)
                continue
            if text or amts:
                raise Refused(f'p{n} y={top}: enterprise line {text!r} falls in no block')
    if fy is None:
        raise Refused('no "Free Cash Calculation - Fiscal Year" heading')


# ---------------------------------------------------------------- the checks

def note(r, msg):
    r['check'] = msg if not r['check'] else r['check'] + '; ' + msg


def check_general(doc):
    gf = [r for r in doc.rows if not r['section'].startswith('enterprise:')]
    subtotal = {}
    for sec in ('other receivables in deferred revenue', 'other receivables', 'adjustments'):
        items = [r for r in gf if r['section'] == sec and r['role'] == 'item']
        tots = [r for r in gf if r['section'] == sec and r['role'] == 'subtotal']
        if not items and not tots:
            continue
        if len(tots) != 1:
            raise Refused(f'{sec}: {len(tots)} printed totals, expected 1')
        t = tots[0]
        s = sum((val(r) for r in items), Decimal(0))
        ok = closes(s, val(t))
        n_amt = sum(1 for r in items if r['_amount'] is not None)
        if ok is None:
            raise Refused(f'{sec}: {len(items)} lines sum to {money(s)}, page prints {money(val(t))}')
        note(t, f'{n_amt} itemised amounts sum to {money(s)}: {ok}')
        subtotal[sec] = t
    opening = [r for r in gf if r['role'] == 'opening']
    result = [r for r in gf if r['role'] == 'result']
    if len(opening) != 1 or len(result) != 1:
        raise Refused(f'{len(opening)} opening balances and {len(result)} results')
    computed = val(opening[0])
    terms = [money(val(opening[0]))]
    for r in gf:
        if r['role'] == 'subtract':
            computed -= val(r); terms.append(f'- {money(val(r))}')
        elif r['role'] == 'subtotal' and r['section'].startswith('other receivables'):
            computed -= val(r); terms.append(f'- {money(val(r))}')
        elif r['role'] == 'subtotal' and r['section'] == 'adjustments':
            computed += val(r); terms.append(f'+ {money(val(r))}')
        elif r['role'] == 'add':
            computed += val(r); terms.append(f'+ {money(val(r))}')
    ok = closes(computed, val(result[0]))
    if ok is None:
        raise Refused(f'general fund: {" ".join(terms)} = {money(computed)}, page prints '
                      f'{money(val(result[0]))}')
    note(result[0], f'{" ".join(terms)} = {money(computed)}: {ok}')
    return result[0], ok, [r['check'] for r in subtotal.values()]


def check_enterprises(doc):
    out = []
    funds = []
    for r in doc.rows:
        if r['section'].startswith('enterprise:') and r['section'] not in funds:
            funds.append(r['section'])
    for f in funds:
        rs = [r for r in doc.rows if r['section'] == f]

        def one(role):
            hit = [r for r in rs if r['role'] == role]
            if len(hit) != 1:
                raise Refused(f'{f}: {len(hit)} rows with role {role!r}')
            return hit[0]

        results = []
        for part, start in (('I', 'part I cash'), ('II', 'part II retained earnings')):
            base = one(start)
            subs = [r for r in rs if r['role'] == f'part {part} subtract']
            others = [r for r in rs if r['role'] == f'part {part} other']
            total = one(f'part {part} total')
            subtot = [r for r in rs if r['role'] == f'part {part} subtract total']
            ssum = sum((val(r) for r in subs), Decimal(0))
            if subtot:
                st = subtot[0]
                ok = closes(ssum, val(st))
                if ok is None:
                    raise Refused(f'{f} part {part}: lines sum to {money(ssum)}, Total prints {money(val(st))}')
                note(st, f'{len(subs)} lines sum to {money(ssum)}: {ok}')
                ssum = val(st)
            osum = sum((val(r) for r in others), Decimal(0))
            computed = val(base) - ssum + osum
            ok = closes(computed, val(total))
            if ok is None:
                raise Refused(f'{f} part {part}: {money(val(base))} - {money(ssum)} + {money(osum)} = '
                              f'{money(computed)}, page prints {money(val(total))}')
            sign = '+' if osum >= 0 else '-'
            note(total, f'{money(val(base))} - {money(ssum)} {sign} {money(abs(osum))} = '
                        f'{money(computed)}: {ok}')
            results.append(total)
        if val(results[0]) != val(results[1]):
            raise Refused(f'{f}: Part I total {money(val(results[0]))} != Part II total {money(val(results[1]))}')
        note(results[1], 'equals Part I total')
        deb = [r for r in rs if r['role'] == 'part III debit']
        cre = [r for r in rs if r['role'] == 'part III credit']
        dt, ct, var = one('part III debits total'), one('part III credits total'), one('part III variance')
        for items, tot in ((deb, dt), (cre, ct)):
            if items:
                s = sum((val(r) for r in items), Decimal(0))
                ok = closes(s, val(tot))
                if ok is None:
                    raise Refused(f'{f} part III: lines sum to {money(s)}, Total prints {money(val(tot))}')
                note(tot, f'{len(items)} lines sum to {money(s)}: {ok}')
        ok = closes(val(dt) - val(ct), val(var))
        if ok is None:
            raise Refused(f'{f}: variance {money(val(var))} != debits - credits')
        note(var, f'debits {money(val(dt))} - credits {money(val(ct))} = {money(val(dt) - val(ct))}: {ok}')
        out.append((f, val(results[0]), [r['check'] for r in results]))
    return out


# ---------------------------------------------------------------- main

def build():
    rows, refused, summary = [], [], []
    for key, as_of, kind in DOCS:
        path = os.path.join(SRC, key)
        doc = Doc(key, as_of)
        try:
            with pdfplumber.open(path) as pdf:
                if not all(p.chars for p in pdf.pages):
                    raise Refused('a page has no text layer; this script does not OCR')
                (worksheet if kind == 'worksheet' else gateway)(pdf, doc)
            result, ok, subs = check_general(doc)
            ents = check_enterprises(doc)
        except Refused as exc:
            refused.append((as_of, key, str(exc)))
            continue
        rows.extend(doc.rows)
        summary.append((as_of, key, result, ok, subs, ents))
    return rows, refused, summary


def render(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n', extrasaction='ignore')
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def cross_check(summary):
    fact = {}
    with open(FACT_SHEET, newline='', encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            fact[int(r['fiscal_year'])] = Decimal(r['certified_free_cash'])
    proof = {}
    with open(PROOF, newline='', encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['town'] == 'Lunenburg' and r['role'] == 'certified':
                proof[int(r['year'])] = Decimal(r['amount'])
    print('\n  cross-check (printed result vs. the Town fact sheet, by the fiscal year it can be')
    print('  spent in = as-of year + 1; vs. the DLS Free Cash Proof "Current Year Calculation",')
    print('  by as-of year)')
    print(f"  {'as of':<11}{'printed':>12}  {'fact sheet':>12} {'':6} {'proof':>12} {'':6}")
    for as_of, key, result, ok, subs, ents in summary:
        y = int(as_of[:4])
        p = val(result)
        fs = fact.get(y + 1)
        pr = proof.get(y)

        def cmp(x):
            if x is None:
                return f"{'—':>12} {'none':6}"
            return f"{money(x):>12} {'same' if x == p else 'DIFFER':6}"
        print(f'  {as_of:<11}{money(p):>12}  {cmp(fs)} {cmp(pr)}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='rebuild and compare to the CSV on disk byte for byte')
    args = ap.parse_args()
    rows, refused, summary = build()
    text = render(rows)
    for as_of, key, why in refused:
        print(f'  REFUSED {as_of}  {key}\n          {why}')
    if args.check:
        have = open(OUT, encoding='utf-8', newline='').read() if os.path.exists(OUT) else ''
        if have != text:
            print(f'  {os.path.relpath(OUT, ROOT)} does not reproduce')
            return 1
        print(f'  {os.path.relpath(OUT, ROOT)} reproduces ({len(rows)} rows)')
        return 1 if refused else 0
    with open(OUT, 'w', encoding='utf-8', newline='') as fh:
        fh.write(text)
    print(f'  wrote {os.path.relpath(OUT, ROOT)}  ({len(rows)} rows, {len(summary)} as-of dates, '
          f'{len(refused)} refused)')
    for as_of, key, result, ok, subs, ents in summary:
        print(f'  {as_of}  free cash {money(val(result)):>12}  general fund: {ok}'
              + ''.join(f'\n              sub-list: {s}' for s in subs))
        for f, total, checks in ents:
            print(f'              {f[11:]:<28} {money(total):>12}  ' + ' | '.join(checks))
    cross_check(summary)
    return 1 if refused else 0


if __name__ == '__main__':
    sys.exit(main())
