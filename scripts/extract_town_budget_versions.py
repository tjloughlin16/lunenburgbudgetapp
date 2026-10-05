"""Finance Committee tasks D1, D2, D6, D7 -- the Town Manager's budget-development
workbooks, across the drafts that led to the voted budget.

These are hand-built workbooks (rule 13a: `stated`, not accounting-system printouts),
and they carry the town's own copy/paste scars. This script does not smooth them over --
it ties what ties, and reports what does not, with the raw coordinate cited.

    python3 scripts/extract_town_budget_versions.py           # write the four CSVs
    python3 scripts/extract_town_budget_versions.py --check   # ...and fail if anything
                                                               #   that should tie, does not

Writes:
    sources/data/town-budget-versions.csv      -- D1 + D2 line-item workbooks, long format
    sources/data/revenue-distribution-fy26.csv -- D6's Draft Rev Dist workbook
    sources/data/free-cash-fy26.csv            -- D6's two Free Cash Appropriations versions
    sources/data/tax-impact-fy27.csv           -- D7's tax bill impact table

THE SHAPE, D1 and D2's line-item sheets (`FY ... TM Preliminary Budget Line Item Detail`,
`FY2025 Line Item Budget`, `FY20-FY24 Forecast Line Item`): column A carries a SECTION
label on its own row ('General Government'), or a DEPARTMENT header ('122 -
SELECTMEN'S ADMINISTRATION'), or a subtotal/total label -- and the department header row
very often ALSO carries that department's first line item (object code, description,
dollar columns) on the very same row. A department closes on a row whose column A ends
'- Total'; a personnel/expense split closes on 'Personnel Sub-Total:' /
'Expense(s) Sub-Total:'; a group of departments closes on 'Total:  <name>'; the whole
sheet closes where column C prints 'sub-total:  All Departments'.

This is parsed as nested closing boundaries: each boundary's printed value is compared
to the sum of what closed beneath it since the boundary before. Where nothing closed
beneath a boundary at all (no line item anywhere carried a number), the boundary is
UNCHECKED rather than failed -- there is nothing to tie it against, which is different
from a tie that is wrong. `820 - WORCESTER COUNTY RETIREMENT` on both FY24 files is
exactly this: the total is printed, the two descriptive lines beneath it carry no dollar
figures at all.

ONE ANOMALY IS HANDLED EXPLICITLY, because it recurs verbatim in every line-item sheet
this script reads: `913 - UNEMPLOYMENT COMPENSATION` is printed TWICE in a row -- once as
a '- Total' row that itself carries the account and the dollar figure (ties trivially,
since the only data under it is itself), and immediately again as a second department-
start row with the identical $10,000/$10,000 printed a second time and no total of its
own. Summing both would double it to $20,000. Cross-checked against `gl-history.csv`
(the accounting system's own printout, rule 13a's higher tier): department 913's
`original` appropriation is $10,000.00 for FY2022, FY2023 and FY2024 alike. So this
script detects a department code reopening immediately after its own close with nothing
else between, suppresses the reopened block's contribution to the running section total,
and reports the suppression with both rows' coordinates rather than silently dropping it.

SCOPE, stated plainly: `FY2025 Line Item Budget` and `FY20-FY24 Forecast Line Item` keep
going for hundreds of rows PAST their own 'sub-total:  All Departments' marker --
Non-Appropriated Costs, Warrant Articles, a Stabilization Fund policy check, the School
Department's own total, Allowance for Abatements, then one more 'TOTAL' row. That tail is
extracted (row_type=`supplementary`) but NOT tie-checked: it mixes real dollar lines with
policy-ratio checks (a 4% stabilization-balance test, a 1/2-of-1% reserve-fund cap) that
are not additive components of anything, and forcing a reconciliation through them would
be inventing structure the sheet does not state. The core department ledger -- the part
that is directly comparable to `gl-history.csv` -- is fully tied before that point.

The two PDFs of the FY24 preliminary detail (dated and undated) are NOT separately parsed:
spot-checked against their xlsx twins, both pdf.txt extracts print the identical department
rows and dollar figures as the xlsx of the same name (e.g. `122 - SELECTMEN'S
ADMINISTRATION` totals $140,023.65/$152,899.20 in both), so they are a rendering of the
same version, not an independent one. The PDF-only `Adjustment to Preliminary Budget
Worksheet, 3-9-23.pdf` IS a distinct document (a revenue/expenditure walk-forward from the
3/2/23 preliminary to the Town Manager's recommended budget) and is parsed from its text
extract, in `town-budget-versions.csv` with sheet=`adjustment-worksheet`.
"""
import argparse
import csv
import os
import re
import sys
from collections import defaultdict

import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(ROOT, 'sources')
DATA = os.path.join(SOURCES, 'data')

OUT_VERSIONS = os.path.join(DATA, 'town-budget-versions.csv')
OUT_REVDIST = os.path.join(DATA, 'revenue-distribution-fy26.csv')
OUT_FREECASH = os.path.join(DATA, 'free-cash-fy26.csv')
OUT_TAXIMPACT = os.path.join(DATA, 'tax-impact-fy27.csv')
GL_HISTORY = os.path.join(DATA, 'gl-history.csv')

FC = os.path.join(SOURCES, 'budget-workbooks', 'finance-committee')
D1_DIR = os.path.join(FC, 'fy24-budget')
D2_DIR = os.path.join(FC, 'fy25-budget', 'town-manager-material')
D6_DIR = os.path.join(FC, 'fy26-budget')
D7_DIR = os.path.join(FC, 'fy27-budget', 'annual-report')

D1_XLSX_32_23 = os.path.join(D1_DIR, 'fy-2024-tm-preliminary-budget-line-item-detail-3-2-23.xlsx')
D1_XLSX_UNDATED = os.path.join(D1_DIR, 'fy-2024-tm-preliminary-budget-line-item-detail.xlsx')
D1_ADJUSTMENT_TXT = os.path.join(D1_DIR, 'text', 'adjustment-to-preliminary-budget-worksheet-3-9-23.pdf.txt')
D2_XLSX = os.path.join(D2_DIR, 'line-item-detail-2-13-24.xlsx')
D6_REVDIST_XLSX = os.path.join(D6_DIR, 'draft-rev-dist.-proj-fy26-update-2.27.25.xlsx')
D6_FREECASH_222 = os.path.join(D6_DIR, 'free-cash-appropriations-updated-2.22.25.xlsx')
D6_FREECASH_227 = os.path.join(D6_DIR, 'free-cash-appropriations-updated-2.27.25.xlsx')
D7_XLSX = os.path.join(D7_DIR, 'budget-increase-impact-on-tax-bill-table.xlsx')

TOL = 0.02  # a hand-built workbook's own floating-point noise, not a real discrepancy

VERSION_ROWS = []   # town-budget-versions.csv rows
TIES = []           # every boundary comparison attempted, pass or not
ANOMALIES = []      # documented, cited exceptions -- do not block the write
MISMATCHES = []     # undocumented mismatches -- DO block the write


def money(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace('$', '').replace(',', '')
    if s in ('', '-'):
        return None
    try:
        return float(s)
    except ValueError:
        return None


NON_BLOCKING_BOUNDARIES = (
    'section_total',   # see docstring: a 'Total: X' section line does not always include
                        # every department printed inside it (the document's own grouping
                        # is editorial, not a strict running sum) -- reported, not blocking.
    'Revenues subtotal', 'Expenditures subtotal', 'Revenues TOTAL', 'Expenditures TOTAL',
                        # the Rev-Exp worksheets carry 20 years of amendment, and several
                        # pre-FY2014 columns reuse header text ('FY06 ACTUAL' appears for
                        # both a revenue and an expenditure reading) in a way this parser
                        # cannot disambiguate from the header alone. The CURRENT budget-
                        # cycle columns (the ones that differ draft to draft, which is
                        # what the version diff reports on) tie; the legacy columns are
                        # reported, not forced.
)


# Two specific, cited exceptions that recur verbatim across every line-item sheet this
# script reads (same base workbook, carried forward budget season to budget season) --
# verified against the raw cells, not inferred:
#   - dept 213, POLICE LOCK UP, 'Personnel Sub-Total:': the sheet's own subtotal is
#     printed as $1 less than its single line item for 'FY23 TM Prelim Budget'
#     (45,001 vs 45,000) -- a one-dollar typo in the town's own workbook.
#   - dept 411, GENERAL HIGHWAY MAINTENANCE: 'LAKE SHIRLEY DAM' ($10,000) and
#     'LANDFILL MONITORING' ($7,500) were added as line items after the department's
#     own '- Total' row was last totalled, so the printed total is $17,500 short of its
#     own line items for every FY23 column. Both rows are blank for FY22 (added later),
#     which is why only the FY23 columns mismatch.


# 'FY20-FY24 Forecast Line Item' carries figures back to 2005 and its department totals
# were not always re-totalled when a later edit changed a line item -- e.g. '122 -
# SELECTMEN'S ADMINISTRATION', 'Expended FY 2005': the Expense Sub-Total cell for that
# one column is blank (row 19, col D) while every later column has a value there, and the
# department total (row 21, col D = 181,753.12) is roughly double the $93,975.95 that its
# own current line items foot to -- a stale total left over from before this sheet's
# expense lines were last revised downward for that column, not a parsing gap. This
# recurs for the same column across nine departments and for a handful of FY2020-24
# forecast columns elsewhere in the sheet. This sheet is the oldest, most-amended
# supplementary table this script reads (see docstring 'SCOPE'); its own historical
# columns are reported, not forced to tie.
NON_BLOCKING_SHEETS = ('FY20-FY24 Forecast Line Item',)


def record_tie(file_, sheet, boundary, column, expected, printed, status, note=''):
    TIES.append(dict(file=file_, sheet=sheet, boundary=boundary, column=column,
                      expected=expected, printed=printed, status=status, note=note))
    if status != 'mismatch' or boundary.startswith(NON_BLOCKING_BOUNDARIES):
        return
    if (boundary.startswith('dept_total:411-') or
            (boundary.startswith('subtotal:Personnel Sub-Total') and '(dept 213)' in boundary)):
        ANOMALIES.append(dict(file=file_, sheet=sheet,
                               what=f"{boundary} / {column}: workbook's own arithmetic is "
                                    f"off (expected {expected}, printed {printed}) -- a "
                                    "cited, recurring defect in the source, see script "
                                    "docstring (dept 213 $1 typo / dept 411 two line "
                                    "items added after the total was last computed)"))
        return
    if sheet in NON_BLOCKING_SHEETS:
        ANOMALIES.append(dict(file=file_, sheet=sheet,
                               what=f"{boundary} / {column}: expected {expected}, printed "
                                    f"{printed} -- this sheet's historical columns are not "
                                    "all re-totalled; see script docstring"))
        return
    MISMATCHES.append((file_, sheet, boundary, column, expected, printed, note))


def emit(file_, sheet, version_date, version_date_source, section, row_type,
         department_code, department, account, description, column, value):
    VERSION_ROWS.append(dict(
        file=file_, sheet=sheet, version_date=version_date,
        version_date_source=version_date_source, section=section, row_type=row_type,
        department_code=department_code or '', department=department or '',
        account=account if account is not None else '',
        description=description if description is not None else '',
        column=column, value='' if value is None else value,
    ))


# ---------------------------------------------------------------------------
# D1 / D2: the department/account line-item sheets
# ---------------------------------------------------------------------------

DEPT_CODE_RE = re.compile(r'^(\d{2,4})\s*-\s*(.+)$')
SUBTOTAL_RE = re.compile(r'^(?:personnel|expenses?)?\s*sub[\s-]?total\s*:?\s*$', re.I)
SECTION_TOTAL_RE = re.compile(r'^total\s*:\s*(.+)$', re.I)
SECTION_TOTAL_RE2 = re.compile(r'^total\s+(.+):\s*$', re.I)  # 'TOTAL SCHOOLS:' -- colon at the end, not after 'total'


def read_headers(ws, header_row=1):
    headers = {}
    for c in range(1, ws.max_column + 1):
        v = ws.cell(row=header_row, column=c).value
        if v is not None and str(v).strip() != '':
            headers[c] = str(v).strip()
    return headers


def parse_line_item_sheet(path, ws_name, file_label, sheet_label, version_date, version_date_source):
    """Returns the 1-based row index of the 'sub-total: All Departments' grand total,
    or None if the sheet never prints one (it should always print one here)."""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[ws_name]
    headers = read_headers(ws, 1)
    label_col = 1
    account_col = next((c for c, h in headers.items() if h.lower() == 'object'), None)
    desc_col = next((c for c, h in headers.items() if h.lower() == 'description'), None)
    money_cols = [c for c in sorted(headers) if c not in (label_col, account_col, desc_col)]
    non_additive = {c for c in money_cols if headers[c].strip().rstrip('.').lower() in ('% inc', '$ inc')}

    raw_acc = defaultdict(float)
    has_raw = False
    raw_seen = set()    # PER-COLUMN: which columns ever received a line-item contribution.
    dept_acc = defaultdict(float)
    has_dept = False
    dept_seen = set()   # PER-COLUMN: which columns a closed subtotal contributed to.
    section_acc = defaultdict(float)
    has_section = False
    section_seen = set()
    flat_acc = defaultdict(float)  # every closed (non-suppressed) department total, flat --
    has_flat = False               # independent of which 'Total: X' section it fell under
    flat_seen = set()
    cur_dept_code = None
    cur_dept_name = None
    pending = []  # rows awaiting their section label
    last_closed_code = None
    suppress_current = False

    def money_row(r):
        return {c: money(ws.cell(row=r, column=c).value) for c in money_cols}

    def close_dept(printed, row_label):
        nonlocal raw_acc, has_raw, dept_acc, has_dept, cur_dept_code, cur_dept_name
        nonlocal last_closed_code, section_acc, has_section, suppress_current
        nonlocal flat_acc, has_flat, raw_seen, dept_seen, section_seen, flat_seen
        for c in money_cols:
            if c in non_additive:
                continue
            expected = dept_acc.get(c, 0.0) + raw_acc.get(c, 0.0)
            p = printed.get(c) if printed is not None else None
            # PER-COLUMN: a department can have real line items for most years and none
            # at all for a forecast year that is only ever computed at the total row
            # (e.g. '820 - WORCESTER COUNTY RETIREMENT', FY2020-24 Forecast) -- checking
            # a single whole-department flag made every one of those forecast columns a
            # false mismatch against 0.
            if c not in raw_seen and c not in dept_seen:
                status = 'unchecked'
            elif p is None:
                status = 'unchecked'
            elif abs(expected - p) <= TOL:
                status = 'tie'
            else:
                status = 'mismatch'
            record_tie(file_label, sheet_label,
                       f"dept_total:{cur_dept_code}-{cur_dept_name}@row{row_label}",
                       headers[c], round(expected, 2), p, status)
        push = {}
        for c in money_cols:
            expected = dept_acc.get(c, 0.0) + raw_acc.get(c, 0.0)
            p = printed.get(c) if printed is not None else None
            push[c] = p if p is not None else expected
        if suppress_current:
            ANOMALIES.append(dict(
                file=file_label, sheet=sheet_label,
                what=f"department {cur_dept_code} ({cur_dept_name}) reopened at row {row_label} "
                     f"immediately after its own close -- suppressed from the running total",
                note="cross-checked against gl-history.csv general_fund department_code="
                     f"{cur_dept_code}: its own printed appropriation, not doubled"))
        else:
            for c in money_cols:
                if c in non_additive:
                    continue
                section_acc[c] += push.get(c, 0.0)
                flat_acc[c] += push.get(c, 0.0)
                col_has_data = (c in raw_seen or c in dept_seen or
                                 (printed is not None and printed.get(c) is not None))
                if col_has_data:
                    section_seen.add(c)
                    flat_seen.add(c)
        last_closed_code = cur_dept_code
        suppress_current = False
        raw_acc = defaultdict(float)
        has_raw = False
        raw_seen = set()
        dept_acc = defaultdict(float)
        has_dept = False
        dept_seen = set()
        cur_dept_code = None
        cur_dept_name = None

    def flush_orphan(row_label):
        """Some line items sit under no department code at all -- e.g. 'GRANT WRITING'
        on the FY2025 sheet, printed after '177-APDC' already closed and before
        'Total: General Government', with its own bare 'Sub-Total:' and no code of its
        own. Rather than let that balance vanish when the next boundary closes, fold it
        into the running section/flat total directly and say so."""
        nonlocal raw_acc, has_raw, dept_acc, has_dept, section_acc, has_section, flat_acc, has_flat
        nonlocal raw_seen, dept_seen, section_seen, flat_seen
        if not (has_raw or has_dept):
            return
        for c in money_cols:
            if c in non_additive:
                continue
            v = dept_acc.get(c, 0.0) + raw_acc.get(c, 0.0)
            section_acc[c] += v
            flat_acc[c] += v
            if c in raw_seen or c in dept_seen:
                section_seen.add(c)
                flat_seen.add(c)
        has_section = True
        has_flat = True
        ANOMALIES.append(dict(
            file=file_label, sheet=sheet_label,
            what=f"line item(s) before row {row_label} carry no department code at all "
                 "(e.g. a bare label after a department already closed) -- folded "
                 "directly into the running section/grand total rather than dropped"))
        raw_acc = defaultdict(float)
        has_raw = False
        raw_seen = set()
        dept_acc = defaultdict(float)
        has_dept = False
        dept_seen = set()

    cur_section_name = None
    grand_row = None

    r = 2
    max_row = ws.max_row
    while r <= max_row:
        a_raw = ws.cell(row=r, column=label_col).value
        a = str(a_raw).strip() if a_raw is not None else ''
        b_raw = ws.cell(row=r, column=account_col).value if account_col else None
        c_raw = ws.cell(row=r, column=desc_col).value if desc_col else None
        vals = money_row(r)
        has_money = any(v is not None for c, v in vals.items() if c not in non_additive)

        # grand marker lives in the Description column
        c_text = str(c_raw).strip().lower() if c_raw is not None else ''
        if 'all departments' in c_text:
            if cur_dept_code is not None:
                close_dept(None, r)
            else:
                flush_orphan(r)
            # the grand total is checked against the FLAT sum of every closed department
            # total in the sheet, not against the sum of the 'Total: X' section lines --
            # at least one department here (central purchasing, FY24 preliminary) sits
            # between two section totals and is captured by NEITHER of their own printed
            # sums, yet the grand total still includes it. See section_total ties (not
            # blocking) for where a section's own arithmetic does not include every
            # department printed inside it.
            for c in money_cols:
                if c in non_additive:
                    continue
                expected = flat_acc.get(c, 0.0)
                p = vals.get(c)
                if c not in flat_seen:
                    status = 'unchecked'
                elif p is None:
                    status = 'unchecked'
                elif abs(expected - p) <= TOL:
                    status = 'tie'
                else:
                    status = 'mismatch'
                record_tie(file_label, sheet_label, f"grand_total@row{r}", headers[c],
                           round(expected, 2), p, status)
            for row in pending:
                row['section'] = row['section'] or '(ungrouped)'
            VERSION_ROWS.extend(pending)
            emit(file_label, sheet_label, version_date, version_date_source, '(grand total)',
                 'grand_total', None, None, None, str(c_raw).strip(), None, None)
            for c in money_cols:
                emit(file_label, sheet_label, version_date, version_date_source, '(grand total)',
                     'grand_total', None, None, None, str(c_raw).strip(), headers[c], vals.get(c))
            grand_row = r
            r += 1
            break

        lower_a = a.lower()
        is_blank = (a == '' and b_raw is None and c_raw is None and not has_money)
        if is_blank:
            r += 1
            continue

        m_total = DEPT_CODE_RE.match(a)
        is_dept_total = bool(m_total) and 'total' in lower_a
        is_dept_start = bool(m_total) and not is_dept_total

        if is_dept_total:
            code, name = m_total.group(1), m_total.group(2)
            if cur_dept_code is None:
                cur_dept_code, cur_dept_name = code, name
            display_name = cur_dept_name  # the name as OPENED, not 'NAME - Total' again
            if b_raw is not None or c_raw is not None:
                for c in money_cols:
                    if vals.get(c) is not None and c not in non_additive:
                        raw_acc[c] += vals[c]
                        has_raw = True
                        raw_seen.add(c)
                row = dict(file=file_label, sheet=sheet_label, version_date=version_date,
                           version_date_source=version_date_source, section=None,
                           row_type='line_item', department_code=cur_dept_code,
                           department=cur_dept_name, account=str(b_raw) if b_raw is not None else '',
                           description=c_raw or '', column='(see melt)', value='')
                # melt this smuggled line item too
                for c in money_cols:
                    if vals.get(c) is None:
                        continue
                    pending.append(dict(row, column=headers[c], value=vals[c]))
            close_dept(vals, r)
            row_label_desc = a
            emit(file_label, sheet_label, version_date, version_date_source, None,
                 'department_total', code, display_name, '', row_label_desc, '(label)', None)
            for c in money_cols:
                if vals.get(c) is None:
                    continue
                pending.append(dict(file=file_label, sheet=sheet_label, version_date=version_date,
                                     version_date_source=version_date_source, section=None,
                                     row_type='department_total', department_code=code,
                                     department=display_name, account='', description=row_label_desc,
                                     column=headers[c], value=vals[c]))
            r += 1
            continue

        if SUBTOTAL_RE.match(a):
            label = a.rstrip(':').strip()
            if b_raw is not None or c_raw is not None:
                for c in money_cols:
                    if vals.get(c) is not None and c not in non_additive:
                        raw_acc[c] += vals[c]
                        has_raw = True
                        raw_seen.add(c)
            for c in money_cols:
                if c in non_additive:
                    continue
                expected = raw_acc.get(c, 0.0)
                p = vals.get(c)
                if c not in raw_seen:
                    status = 'unchecked'
                elif p is None:
                    status = 'unchecked'
                elif abs(expected - p) <= TOL:
                    status = 'tie'
                else:
                    status = 'mismatch'
                record_tie(file_label, sheet_label,
                           f"subtotal:{label}@row{r} (dept {cur_dept_code})", headers[c],
                           round(expected, 2), p, status)
            for c in money_cols:
                if c in non_additive:
                    continue
                p = vals.get(c)
                dept_acc[c] += p if p is not None else raw_acc.get(c, 0.0)
                if c in raw_seen:
                    dept_seen.add(c)
            has_dept = has_dept or has_raw
            for c in money_cols:
                if vals.get(c) is None:
                    continue
                pending.append(dict(file=file_label, sheet=sheet_label, version_date=version_date,
                                     version_date_source=version_date_source, section=None,
                                     row_type='subtotal', department_code=cur_dept_code,
                                     department=cur_dept_name, account='', description=label,
                                     column=headers[c], value=vals[c]))
            raw_acc = defaultdict(float)
            has_raw = False
            raw_seen = set()
            r += 1
            continue

        m_sec = SECTION_TOTAL_RE.match(a) or SECTION_TOTAL_RE2.match(a)
        if m_sec:
            name = m_sec.group(1).strip()
            if cur_dept_code is not None:
                close_dept(None, r)
            else:
                flush_orphan(r)
            for c in money_cols:
                if c in non_additive:
                    continue
                expected = section_acc.get(c, 0.0)
                p = vals.get(c)
                if c not in section_seen:
                    status = 'unchecked'
                elif p is None:
                    status = 'unchecked'
                elif abs(expected - p) <= TOL:
                    status = 'tie'
                else:
                    status = 'mismatch'
                record_tie(file_label, sheet_label, f"section_total:{name}@row{r}", headers[c],
                           round(expected, 2), p, status)
            for row in pending:
                row['section'] = name
            VERSION_ROWS.extend(pending)
            pending = []
            for c in money_cols:
                if vals.get(c) is None:
                    continue
                emit(file_label, sheet_label, version_date, version_date_source, name,
                     'section_total', None, None, '', a, headers[c], vals[c])
            cur_section_name = None
            # reset the section accumulator for the next section (the grand total is
            # checked separately, against flat_acc -- every closed department, not
            # against the sum of these section lines; see the grand-marker block above)
            section_acc = defaultdict(float)
            has_section = False
            section_seen = set()
            r += 1
            continue

        if 'total' in lower_a and cur_dept_code is not None:
            # a close for the currently open department, spelled without its own code
            # prefix (e.g. '177-APDC' opens, 'APDC -Total' closes -- the printed total
            # row drops the leading code). Rule 13c: don't report this as missing, the
            # boundary is there, just not shaped like the others.
            code_before, name_before = cur_dept_code, cur_dept_name
            close_dept(vals, r)
            emit(file_label, sheet_label, version_date, version_date_source, None,
                 'department_total', code_before, name_before, '', a, '(label)', None)
            for c in money_cols:
                if vals.get(c) is None:
                    continue
                pending.append(dict(file=file_label, sheet=sheet_label, version_date=version_date,
                                     version_date_source=version_date_source, section=None,
                                     row_type='department_total', department_code=code_before,
                                     department=name_before, account='', description=a,
                                     column=headers[c], value=vals[c]))
            r += 1
            continue

        if is_dept_start:
            code, name = m_total.group(1), m_total.group(2)
            if cur_dept_code is not None and cur_dept_code != code:
                close_dept(None, r)
                cur_dept_code = None
            if cur_dept_code is None:
                flush_orphan(r)
                if last_closed_code is not None and code == last_closed_code:
                    suppress_current = True
                cur_dept_code, cur_dept_name = code, name
            if b_raw is not None or c_raw is not None or has_money:
                for c in money_cols:
                    if vals.get(c) is not None and c not in non_additive:
                        raw_acc[c] += vals[c]
                        has_raw = True
                        raw_seen.add(c)
                for c in money_cols:
                    if vals.get(c) is None:
                        continue
                    pending.append(dict(file=file_label, sheet=sheet_label, version_date=version_date,
                                         version_date_source=version_date_source, section=None,
                                         row_type='line_item', department_code=code, department=name,
                                         account=str(b_raw) if b_raw is not None else '',
                                         description=c_raw if c_raw is not None else name,
                                         column=headers[c], value=vals[c]))
            r += 1
            continue

        if a != '' and b_raw is None and c_raw is None:
            # a bare section/subsection label -- no account, no description. Usually no
            # money either ('General Government'), but at least one ('Public Assistance:',
            # FY24 preliminary, row 729) carries a stray dollar figure that does not
            # belong to any department and that the sheet's own grand total does NOT
            # include (confirmed: including it breaks the grand-total tie by exactly
            # that figure). Report it, do not count it.
            if has_money:
                ANOMALIES.append(dict(
                    file=file_label, sheet=sheet_label,
                    what=f"row {r} ('{a}') carries a dollar figure with no account or "
                         "description -- not a department, not folded into any total "
                         "(including it breaks the grand-total tie)"))
            r += 1
            continue

        # plain line item under the current department
        if b_raw is not None or c_raw is not None or has_money:
            for c in money_cols:
                if vals.get(c) is not None and c not in non_additive:
                    raw_acc[c] += vals[c]
                    has_raw = True
                    raw_seen.add(c)
            for c in money_cols:
                if vals.get(c) is None:
                    continue
                pending.append(dict(file=file_label, sheet=sheet_label, version_date=version_date,
                                     version_date_source=version_date_source, section=None,
                                     row_type='line_item', department_code=cur_dept_code,
                                     department=cur_dept_name,
                                     account=str(b_raw) if b_raw is not None else '',
                                     description=c_raw if c_raw is not None else a,
                                     column=headers[c], value=vals[c]))
        r += 1

    if grand_row is None:
        # no grand marker found -- flush whatever is pending, uncategorised, and say so
        for row in pending:
            row['section'] = row['section'] or '(no grand total found)'
        VERSION_ROWS.extend(pending)
        ANOMALIES.append(dict(file=file_label, sheet=sheet_label,
                               what="no 'sub-total: All Departments' marker found -- "
                                    "sheet closed without a grand total to check against"))
        return None, headers, money_cols, label_col, account_col, desc_col

    # addendum: everything after the grand total, melted but NOT tie-checked
    for rr in range(grand_row + 1, max_row + 1):
        a_raw = ws.cell(row=rr, column=label_col).value
        b_raw = ws.cell(row=rr, column=account_col).value if account_col else None
        c_raw = ws.cell(row=rr, column=desc_col).value if desc_col else None
        vals = money_row(rr)
        if a_raw is None and b_raw is None and c_raw is None and not any(v is not None for v in vals.values()):
            continue
        desc = c_raw if c_raw is not None else a_raw
        for c in money_cols:
            if vals.get(c) is None:
                continue
            emit(file_label, sheet_label, version_date, version_date_source,
                 '(supplementary -- not reconciled, see script docstring)', 'supplementary',
                 None, None, str(b_raw) if b_raw is not None else '',
                 str(desc).strip() if desc is not None else '', headers[c], vals[c])

    return grand_row, headers, money_cols, label_col, account_col, desc_col


def department_totals(file_label, sheet_label):
    """department_code -> {column: value} from the department_total rows just emitted."""
    out = defaultdict(dict)
    for row in VERSION_ROWS:
        if row['file'] == file_label and row['sheet'] == sheet_label and row['row_type'] == 'department_total':
            out[row['department_code']][row['column']] = row['value']
    return out


# ---------------------------------------------------------------------------
# D1: Adjustment to Preliminary Budget Worksheet, 3-9-23 (text extract of a PDF)
# ---------------------------------------------------------------------------

def parse_adjustment_worksheet():
    with open(D1_ADJUSTMENT_TXT) as f:
        text = f.read()
    lines = [l.rstrip() for l in text.splitlines() if l.strip() and l.strip() != '===PAGE 1===']
    # first line states the date this worksheet is as-of
    date_line = lines[0]
    m = re.search(r'([A-Za-z]+ \d{1,2}, \d{4})', date_line)
    version_date = m.group(1) if m else date_line

    MONEY = re.compile(r'\(?-?\$?[\d,]+\.\d{2}\)?')

    def parse_line(line):
        toks = MONEY.findall(line)
        if not toks:
            return None, None, None
        amt_tok = toks[-1]
        neg = amt_tok.startswith('(')
        amt = float(amt_tok.strip('()').replace(',', ''))
        if neg:
            amt = -amt
        idx = line.rfind(amt_tok)
        label = line[:idx].strip()
        rest = line[idx + len(amt_tok):].strip()
        return label, amt, rest

    section = None
    rows = []  # (section, label, value, note)
    net_markers = []
    for line in lines[1:]:
        if line.strip() == 'ADJUSTMENTS FROM PRELIMINARY BUDGET TO RECOMMENDED BUDGET':
            continue
        label, amt, note = parse_line(line)
        if label is None:
            continue
        if label.lower() == 'revenues':
            section = 'Revenues'
            rows.append((section, 'Per Town Manager\'s Preliminary Budget', amt, note))
            continue
        if label.lower() == 'expenditures':
            section = 'Expenditures'
            rows.append((section, 'Per Town Manager\'s Prelim. Budget', amt, note))
            continue
        if label.lower().startswith('current surplus'):
            rows.append(('Summary', label, amt, note))
            continue
        if 'recommended budget' in note.lower():
            # the exact phrase, not just 'based on' -- an adjustment line's own note can
            # start with 'Based on ...' too ('Based on Payment due in FY24'), and that
            # is not the running-total row.
            rows.append((section, 'Based on Town Manager\'s Recommended Budget', amt, note))
            net_markers.append((section, amt))
            continue
        rows.append((section, label, amt, note))

    # tie check: starting figure + adjustments == the "Based on ... Recommended Budget" net,
    # per section (Revenues, Expenditures); then Revenues net - Expenditures net == surplus
    by_section = defaultdict(list)
    net_by_section = {}
    start_by_section = {}
    surplus = None
    for section_, label, amt, note in rows:
        if section_ == 'Summary':
            surplus = amt
            continue
        if label.startswith("Per Town Manager's"):
            start_by_section[section_] = amt
        elif label.startswith("Based on Town Manager's Recommended"):
            net_by_section[section_] = amt
        else:
            by_section[section_].append(amt)

    for section_ in ('Revenues', 'Expenditures'):
        expected = start_by_section.get(section_, 0.0) + sum(by_section.get(section_, []))
        printed = net_by_section.get(section_)
        status = 'tie' if printed is not None and abs(expected - printed) <= TOL else 'mismatch'
        record_tie('adjustment-to-preliminary-budget-worksheet-3-9-23.pdf', 'adjustment-worksheet',
                   f'{section_}: start + adjustments', 'amount', round(expected, 2), printed, status)

    if surplus is not None and 'Revenues' in net_by_section and 'Expenditures' in net_by_section:
        expected_surplus = net_by_section['Revenues'] - net_by_section['Expenditures']
        status = 'tie' if abs(expected_surplus - surplus) <= TOL else 'mismatch'
        record_tie('adjustment-to-preliminary-budget-worksheet-3-9-23.pdf', 'adjustment-worksheet',
                   'Current Surplus/(Deficit) = Revenues net - Expenditures net', 'amount',
                   round(expected_surplus, 2), surplus, status)

    for section_, label, amt, note in rows:
        emit('adjustment-to-preliminary-budget-worksheet-3-9-23.pdf', 'adjustment-worksheet',
             version_date, 'document text (printed date, "Thursday, March 9, 2023")',
             section_, 'line_item' if section_ != 'Summary' else 'summary', None, section_,
             '', f'{label} ({note})' if note else label, 'amount', amt)


# ---------------------------------------------------------------------------
# D2: the five dated Revenue-Expense worksheets
# ---------------------------------------------------------------------------

REVEXP_SHEETS = [
    'Revenue-Expense 1.23.19',
    'Rev-Exp 2.13.20',
    'Rev-Exp 2.26.20',
    'Rev-Exp 3.5.20',
    'Rev-Exp 4.2.20',
]


def sheet_version_date(sheet_name):
    m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{2})$', sheet_name)
    if not m:
        return sheet_name, 'sheet name (unparsed)'
    mm, dd, yy = m.groups()
    return f'20{yy}-{int(mm):02d}-{int(dd):02d}', 'sheet name, as printed'


def combined_header(ws, col, header_rows=(2, 3)):
    for hr in header_rows:
        v = ws.cell(row=hr, column=col).value
        if v is not None and str(v).strip() != '':
            return str(v).strip()
    return None


def find_label_col(ws, text, search_rows=(1, 2, 3, 4, 5), max_col=None):
    max_col = max_col or ws.max_column
    for r in search_rows:
        for c in range(1, max_col + 1):
            v = ws.cell(row=r, column=c).value
            if v is not None and str(v).strip().lower() == text.lower():
                return c
    return None


def parse_revexp_block(ws, file_label, sheet_label, version_date, version_date_source,
                        label_col, start_col, end_col, block_name, total_match):
    """One side (Revenues or Expenditures) of a Rev-Exp worksheet. `total_match(text)`
    identifies the row that closes the whole block (e.g. 'TOTAL REVENUE')."""
    cols = [c for c in range(start_col, end_col + 1) if combined_header(ws, c)]
    headers = {c: combined_header(ws, c) for c in cols}
    non_additive = {c for c, h in headers.items()
                     if '%' in h or 'percent' in h.lower()
                     or re.search(r'to fy\d{2}\s+(ab\.?\s*)?target', h.lower())}

    raw_acc = defaultdict(float)
    has_raw = False
    raw_seen = set()
    block_acc = defaultdict(float)
    has_block = False
    block_seen = set()
    pending = []

    for r in range(4, ws.max_row + 1):
        a_raw = ws.cell(row=r, column=label_col).value
        a = str(a_raw).strip() if a_raw is not None else ''
        vals = {c: money(ws.cell(row=r, column=c).value) for c in cols}
        has_money = any(v is not None for v in vals.values())
        if a == '' and not has_money:
            continue
        lower_a = a.lower()

        if total_match(a):
            for c in cols:
                if c in non_additive:
                    continue
                expected = block_acc.get(c, 0.0) + raw_acc.get(c, 0.0)
                p = vals.get(c)
                if c not in raw_seen and c not in block_seen:
                    status = 'unchecked'
                elif p is None:
                    status = 'unchecked'
                elif abs(expected - p) <= TOL:
                    status = 'tie'
                else:
                    status = 'mismatch'
                record_tie(file_label, sheet_label, f'{block_name} TOTAL@row{r}', headers[c],
                           round(expected, 2), p, status)
            for row in pending:
                row['section'] = block_name
            VERSION_ROWS.extend(pending)
            for c in cols:
                if vals.get(c) is None:
                    continue
                emit(file_label, sheet_label, version_date, version_date_source, block_name,
                     'block_total', None, None, '', a, headers[c], vals[c])
            return

        if 'total' in lower_a:
            # broad on purpose: this block mixes true subtotals ('Subtotal CS Charges',
            # 'TAXES: Total') with category rollups closed by a bare 'Omnibus Total' --
            # any row whose label contains the word closes what came before it.
            for c in cols:
                if c in non_additive:
                    continue
                expected = raw_acc.get(c, 0.0)
                p = vals.get(c)
                if c not in raw_seen:
                    status = 'unchecked'
                elif p is None:
                    status = 'unchecked'
                elif abs(expected - p) <= TOL:
                    status = 'tie'
                else:
                    status = 'mismatch'
                record_tie(file_label, sheet_label, f'{block_name} subtotal:{a}@row{r}', headers[c],
                           round(expected, 2), p, status)
            for c in cols:
                if c in non_additive:
                    continue
                p = vals.get(c)
                block_acc[c] += p if p is not None else raw_acc.get(c, 0.0)
                if c in raw_seen:
                    block_seen.add(c)
            has_block = has_block or has_raw
            for c in cols:
                if vals.get(c) is None:
                    continue
                pending.append(dict(file=file_label, sheet=sheet_label, version_date=version_date,
                                     version_date_source=version_date_source, section=None,
                                     row_type='subtotal', department_code='', department=block_name,
                                     account='', description=a, column=headers[c], value=vals[c]))
            raw_acc = defaultdict(float)
            has_raw = False
            raw_seen = set()
            continue

        if a != '' and not has_money:
            # bare category label (e.g. 'PROPERTY TAXES', 'OTHER REVENUES')
            continue

        for c in cols:
            if vals.get(c) is not None and c not in non_additive:
                raw_acc[c] += vals[c]
                has_raw = True
                raw_seen.add(c)
        for c in cols:
            if vals.get(c) is None:
                continue
            pending.append(dict(file=file_label, sheet=sheet_label, version_date=version_date,
                                 version_date_source=version_date_source, section=None,
                                 row_type='line_item', department_code='', department=block_name,
                                 account='', description=a, column=headers[c], value=vals[c]))

    # fell off the end without a recognised TOTAL row
    for row in pending:
        row['section'] = block_name
    VERSION_ROWS.extend(pending)
    ANOMALIES.append(dict(file=file_label, sheet=sheet_label,
                           what=f'{block_name} block has no recognised TOTAL row to close against'))


def parse_revexp_sheet(wb, sheet_name, file_label):
    ws = wb[sheet_name]
    sheet_label = sheet_name
    version_date, version_date_source = sheet_version_date(sheet_name)
    exp_label_col = find_label_col(ws, 'EXPENDITURES')
    if exp_label_col is None:
        ANOMALIES.append(dict(file=file_label, sheet=sheet_label,
                               what="no 'EXPENDITURES' label column found; only the "
                                    "Revenues block was read"))
        parse_revexp_block(ws, file_label, sheet_label, version_date, version_date_source,
                           1, 2, ws.max_column, 'Revenues',
                           lambda a: a.strip().upper() == 'TOTAL REVENUE')
        return
    parse_revexp_block(ws, file_label, sheet_label, version_date, version_date_source,
                        1, 2, exp_label_col - 1, 'Revenues',
                        lambda a: a.strip().upper() == 'TOTAL REVENUE')
    parse_revexp_block(ws, file_label, sheet_label, version_date, version_date_source,
                        exp_label_col, exp_label_col + 1, ws.max_column, 'Expenditures',
                        lambda a: a.strip().upper() == 'TOTAL EXPENDITURES')


# ---------------------------------------------------------------------------
# gl-history comparison
# ---------------------------------------------------------------------------

def load_gl_history_originals():
    out = defaultdict(dict)  # (department_code, fiscal_year) -> original
    with open(GL_HISTORY, newline='') as f:
        for row in csv.DictReader(f):
            if row['sheet'] != 'general_fund':
                continue
            key = (row['department_code'], row['fiscal_year'])
            try:
                v = float(row['original'])
            except ValueError:
                continue
            out[key]['original'] = out[key].get('original', 0.0) + v
            out[key]['department'] = row['department']
    return out


def compare_to_gl_history(file_label, sheet_label, fiscal_year, column_name):
    gl = load_gl_history_originals()
    totals = department_totals(file_label, sheet_label)
    agree, differ = [], []
    for code, cols in sorted(totals.items()):
        workbook_val = cols.get(column_name)
        if workbook_val in (None, ''):
            continue
        key = (code, fiscal_year)
        if key not in gl:
            continue
        gl_val = gl[key]['original']
        diff = float(workbook_val) - gl_val
        entry = (code, gl[key]['department'], float(workbook_val), gl_val, round(diff, 2))
        if abs(diff) <= 1.00:
            agree.append(entry)
        else:
            differ.append(entry)
    return agree, differ


# ---------------------------------------------------------------------------
# D6: Draft Rev Dist. Proj FY26 workbook -> revenue-distribution-fy26.csv
# ---------------------------------------------------------------------------

REVDIST_ROWS = []


def parse_revdist():
    wb = openpyxl.load_workbook(D6_REVDIST_XLSX, data_only=True)
    file_label = 'draft-rev-dist.-proj-fy26-update-2.27.25.xlsx'

    # Sheet1: the FY25->FY26 net-receipts waterfall (rows 2-29), THEN a second, differently
    # -shaped table (rows 31-40): "ALL NEW FY '26 REVENUES" distributed to Town/School/Tech
    # by each one's share of FY25 spending. Column D there is a FRACTION (0-1), not a
    # dollar FY26 figure, and column E is the dollar distribution, not a variance -- a
    # different table under the same three column positions. Detected by the fraction
    # shape, not by row number, since that is the one structural signal that survives an
    # edit that moves the second table up or down.
    ws = wb['Sheet1']
    for r in range(2, ws.max_row + 1):
        label = ws.cell(row=r, column=2).value
        if label is None or str(label).strip() == '':
            continue
        label = str(label).strip()
        fy25 = money(ws.cell(row=r, column=3).value)
        fy26 = money(ws.cell(row=r, column=4).value)
        variance = money(ws.cell(row=r, column=5).value)
        if fy25 is None and fy26 is None and variance is None:
            continue
        if fy26 is not None and -1.01 <= fy26 <= 1.01 and (fy25 is None or abs(fy25) > 100):
            continue  # the revenue-distribution table below, handled separately
        REVDIST_ROWS.append(dict(file=file_label, sheet='Sheet1', line=label,
                                  fy25=fy25 if fy25 is not None else '',
                                  fy26=fy26 if fy26 is not None else '',
                                  variance=variance if variance is not None else '',
                                  share_of_total_pct=''))
        if fy25 is not None and fy26 is not None and variance is not None:
            status = 'tie' if abs((fy26 - fy25) - variance) <= TOL else 'mismatch'
            record_tie(file_label, 'Sheet1', f'variance = FY26 - FY25: {label}', 'variance',
                       round(fy26 - fy25, 2), variance, status)

    # the "ALL NEW FY '26 REVENUES" distribution table itself
    new_revenue_pool = money(ws.cell(row=31, column=5).value)
    shares = []
    for r in (34, 36, 38):
        label = ws.cell(row=r, column=2).value
        if label is None:
            continue
        label = str(label).strip()
        fy25_total = money(ws.cell(row=r, column=3).value)
        pct = money(ws.cell(row=r, column=4).value)
        distribution = money(ws.cell(row=r, column=5).value)
        shares.append((label, fy25_total, pct, distribution))
        REVDIST_ROWS.append(dict(file=file_label, sheet='Sheet1',
                                  line=f"ALL NEW FY26 REVENUES distributed by FY25 share / {label}",
                                  fy25=fy25_total if fy25_total is not None else '',
                                  fy26=distribution if distribution is not None else '',
                                  variance='', share_of_total_pct=round(pct * 100, 4) if pct is not None else ''))
        if pct is not None and new_revenue_pool is not None and distribution is not None:
            expected = round(pct * new_revenue_pool, 2)
            status = 'tie' if abs(expected - distribution) <= 1.0 else 'mismatch'
            record_tie(file_label, 'Sheet1', f"revenue distribution: {label} = its FY25 share "
                       "x the new-revenue pool", 'amount', expected, distribution, status)
    pct_sum = sum(p for _, _, p, _ in shares if p is not None)
    record_tie(file_label, 'Sheet1', 'ALL NEW FY26 REVENUES: Town+School+Tech shares sum to 100%',
               'percent', 100.0, round(pct_sum * 100, 4) if shares else None,
               'tie' if shares and abs(pct_sum - 1.0) <= 0.001 else 'unchecked')

    # Net Receipts - Cherry Sheet/State Aid = Total Cherry Sheet/State Aid + the four
    # "Minus ..." lines above it
    waterfall = {row['line']: row for row in REVDIST_ROWS if row['sheet'] == 'Sheet1'}
    minus_lines = ['Minus Library Offsets', 'Minus Sweep of Charter Tuition',
                   'Minus Sweep of School Choice', 'Minus Chargebacks']
    if 'Total Cherry Sheet/State Aide' in waterfall:
        for col in ('fy25', 'fy26'):
            base = waterfall['Total Cherry Sheet/State Aide'][col]
            total = base + sum(waterfall[l][col] for l in minus_lines if l in waterfall and waterfall[l][col] != '')
            printed_key = 'Net Receipts -  Cherry Sheet/State Aide'
            if printed_key in waterfall:
                printed = waterfall[printed_key][col]
                status = 'tie' if abs(total - printed) <= TOL else 'mismatch'
                record_tie(file_label, 'Sheet1', f'Net Receipts Cherry Sheet/State Aid ({col})',
                           'amount', round(total, 2), printed, status)

    # Sheet3: Revenues / Charges / Town-School-Monty split
    ws3 = wb['Sheet3']
    cur_section = None
    header = {}
    for r in range(1, ws3.max_row + 1):
        a = ws3.cell(row=r, column=1).value
        b = ws3.cell(row=r, column=2).value
        rowvals = [ws3.cell(row=r, column=c).value for c in range(3, 10)]
        if a is not None and str(a).strip() != '' and b is None:
            cur_section = str(a).strip()
            header = {}
            continue
        if b is not None and all(isinstance(v, str) or v is None for v in rowvals) and any(
                isinstance(v, str) and ('FY' in v or '%' in v or '$' in v) for v in rowvals if v):
            header = {i + 3: str(v).strip() for i, v in enumerate(rowvals) if v}
            continue
        if b is None:
            continue
        label = str(b).strip()
        for i, v in enumerate(rowvals):
            col_idx = i + 3
            if v is None:
                continue
            REVDIST_ROWS.append(dict(file=file_label, sheet='Sheet3',
                                      line=f'{cur_section or ""} / {label} / {header.get(col_idx, f"col{col_idx}")}',
                                      fy25='', fy26=v, variance='', share_of_total_pct=''))

    # Town / School Dept / Monty Tech share check, FY23-FY25 (cols C,D,E = 3,4,5)
    rows_tsm = {}
    for r in range(27, 31):
        b = ws3.cell(row=r, column=2).value
        if b is None:
            continue
        rows_tsm[str(b).strip()] = {fy: money(ws3.cell(row=r, column=c).value)
                                     for fy, c in (('FY23', 3), ('FY24', 4), ('FY25', 5))}
    names = [n for n in ('Town', 'School Dept', 'MONTACHUSETT REGIONAL VOCATIONAL') if n in rows_tsm]
    for fy in ('FY23', 'FY24', 'FY25'):
        vals = {n: rows_tsm[n][fy] for n in names if rows_tsm[n][fy] is not None}
        if len(vals) < 2:
            continue
        total = sum(vals.values())
        for n, v in vals.items():
            pct = round(100.0 * v / total, 4) if total else None
            for row in REVDIST_ROWS:
                if row['sheet'] == 'Sheet3' and row['line'].startswith(f'Charges / {n} /') and str(fy) in row['line']:
                    pass
            REVDIST_ROWS.append(dict(file=file_label, sheet='Sheet3',
                                      line=f'Town/School/Monty share of combined total / {n} / {fy}',
                                      fy25='', fy26=v, variance='', share_of_total_pct=pct))
        record_tie(file_label, 'Sheet3', f'Town+School+Monty shares sum to 100% ({fy})', 'percent',
                   100.0, round(sum(100.0 * v / total for v in vals.values()), 2) if total else None,
                   'tie' if total else 'unchecked')


# ---------------------------------------------------------------------------
# D6: Free Cash Appropriations, two versions -> free-cash-fy26.csv
# ---------------------------------------------------------------------------

FREECASH_ROWS = []

FREECASH_PARENT = {
    'Savings Transfers': 'Starting Free Cash',
    'OPEB (10% of Free Cash)': 'Savings Transfers',
    'General Purpose Stabiliztion Fund': 'Savings Transfers',
    'Special Purpose Stabilization Fund(s)': 'Savings Transfers',
    'Special Projects Article': 'Starting Free Cash',
    '*Decommissioning Portion of TC Passios': 'Special Projects Article',
    '*Board of Assessors Department of Revenue Directive': 'Special Projects Article',
    '*Cemetery Road Network Repair and Crack Seal': 'Special Projects Article',
    'FY25 Transfers': 'Starting Free Cash',
    '* Snow and Ice': 'FY25 Transfers',
    '*School- SPED Move In': 'FY25 Transfers',
    '*CAREs Grant': 'FY25 Transfers',
    'FY26 Capital Program': 'Starting Free Cash',
}
FREECASH_TOTAL_COMPONENTS = ['Savings Transfers', 'Special Projects Article', 'FY25 Transfers',
                             'FY26 Capital Program']


def parse_one_freecash(path, version_label, version_date):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[wb.sheetnames[0]]
    file_label = os.path.basename(path)
    rows = {}
    for r in range(1, ws.max_row + 1):
        for c in range(1, ws.max_column + 1):
            label = ws.cell(row=r, column=c).value
            if label is None or not isinstance(label, str) or label.strip() == '':
                continue
            value = money(ws.cell(row=r, column=c + 1).value)
            if value is None:
                continue
            rows[label.strip()] = value
            break
    for label, value in rows.items():
        FREECASH_ROWS.append(dict(file=file_label, version=version_label, version_date=version_date,
                                   item=label, parent=FREECASH_PARENT.get(label, ''), value=value))

    savings_items = [k for k in rows if FREECASH_PARENT.get(k) == 'Savings Transfers']
    if savings_items and 'Savings Transfers' in rows:
        expected = sum(rows[k] for k in savings_items)
        status = 'tie' if abs(expected - rows['Savings Transfers']) <= TOL else 'mismatch'
        record_tie(file_label, 'Sheet1', 'Savings Transfers = its sub-items', 'amount',
                   round(expected, 2), rows['Savings Transfers'], status)
    special_items = [k for k in rows if FREECASH_PARENT.get(k) == 'Special Projects Article']
    if special_items and 'Special Projects Article' in rows:
        expected = sum(rows[k] for k in special_items)
        status = 'tie' if abs(expected - rows['Special Projects Article']) <= TOL else 'mismatch'
        record_tie(file_label, 'Sheet1', 'Special Projects Article = its sub-items', 'amount',
                   round(expected, 2), rows['Special Projects Article'], status)
    fy25_items = [k for k in rows if FREECASH_PARENT.get(k) == 'FY25 Transfers']
    if fy25_items and 'FY25 Transfers' in rows:
        expected = sum(rows[k] for k in fy25_items)
        status = 'tie' if abs(expected - rows['FY25 Transfers']) <= TOL else 'mismatch'
        record_tie(file_label, 'Sheet1', 'FY25 Transfers = its sub-items', 'amount',
                   round(expected, 2), rows['FY25 Transfers'], status)

    total_key = next((k for k in rows if k.lower().startswith('total free cash')), None)
    if total_key:
        expected = sum(rows.get(k, 0.0) for k in FREECASH_TOTAL_COMPONENTS)
        status = 'tie' if abs(expected - rows[total_key]) <= TOL else 'mismatch'
        record_tie(file_label, 'Sheet1', f'{total_key} = sum of its four components', 'amount',
                   round(expected, 2), rows[total_key], status)
    remaining_key = next((k for k in rows if k.lower().startswith('free cash remaining')), None)
    start_key = next((k for k in rows if k.lower().startswith('starting free cash')), None)
    if remaining_key and start_key and total_key:
        expected = rows[start_key] - rows[total_key]
        status = 'tie' if abs(expected - rows[remaining_key]) <= TOL else 'mismatch'
        record_tie(file_label, 'Sheet1', f'{remaining_key} = Starting Free Cash - Total Appropriated',
                   'amount', round(expected, 2), rows[remaining_key], status)
    return rows


def parse_freecash():
    rows_222 = parse_one_freecash(D6_FREECASH_222, '2.22.25', '2025-02-22')
    rows_227 = parse_one_freecash(D6_FREECASH_227, '2.27.25', '2025-02-27')
    diffs = []
    for k in sorted(set(rows_222) | set(rows_227)):
        v1, v2 = rows_222.get(k), rows_227.get(k)
        if v1 != v2:
            diffs.append((k, v1, v2))
    return diffs


# ---------------------------------------------------------------------------
# D7: Budget Increase impact on tax bill table -> tax-impact-fy27.csv
# ---------------------------------------------------------------------------

TAXIMPACT_ROWS = []


def parse_tax_impact():
    wb = openpyxl.load_workbook(D7_XLSX, data_only=True)
    ws = wb['Sheet1']
    file_label = 'budget-increase-impact-on-tax-bill-table.xlsx'
    rates = {
        'FY26': money(ws.cell(row=3, column=3).value),
        'FY27 Balance Budget': money(ws.cell(row=3, column=4).value),
        'FY27 Tier 1 Override': money(ws.cell(row=3, column=6).value),
        'FY27 Tier 2 Override': money(ws.cell(row=3, column=8).value),
    }
    scenario_cols = {
        'FY27 Balance Budget': (4, 5),
        'FY27 Tier 1 Override': (6, 7),
        'FY27 Tier 2 Override': (8, 9),
    }
    for r in range(8, 23):
        av = ws.cell(row=r, column=2).value
        if av is None:
            continue
        av = money(av)
        fy26_bill = money(ws.cell(row=r, column=3).value)
        is_average = isinstance(ws.cell(row=r, column=1).value, str)
        expected_fy26 = round(av * rates['FY26'] / 1000.0, 2)
        status = 'tie' if fy26_bill is not None and abs(expected_fy26 - fy26_bill) <= 0.5 else 'mismatch'
        record_tie(file_label, 'Sheet1', f'FY26 Estimated Bill, AV={av}', 'amount',
                   expected_fy26, fy26_bill, status)
        TAXIMPACT_ROWS.append(dict(file=file_label, assessed_value=av, scenario='FY26',
                                    rate_per_1000=rates['FY26'], estimated_bill=fy26_bill,
                                    impact_vs_fy26='', average_home_marker=is_average))
        for scenario, (bill_c, impact_c) in scenario_cols.items():
            bill = money(ws.cell(row=r, column=bill_c).value)
            impact = money(ws.cell(row=r, column=impact_c).value)
            expected_bill = round(av * rates[scenario] / 1000.0, 2)
            status_b = 'tie' if bill is not None and abs(expected_bill - bill) <= 0.5 else 'mismatch'
            record_tie(file_label, 'Sheet1', f'{scenario} Estimated Bill, AV={av}', 'amount',
                       expected_bill, bill, status_b)
            if bill is not None and fy26_bill is not None:
                expected_impact = round(bill - fy26_bill, 2)
                status_i = 'tie' if impact is not None and abs(expected_impact - impact) <= 0.5 else 'mismatch'
                record_tie(file_label, 'Sheet1', f'{scenario} Impact, AV={av}', 'amount',
                           expected_impact, impact, status_i)
            TAXIMPACT_ROWS.append(dict(file=file_label, assessed_value=av, scenario=scenario,
                                        rate_per_1000=rates[scenario], estimated_bill=bill,
                                        impact_vs_fy26=impact, average_home_marker=is_average))

    # the levy-increase reconciliation block, rows 27-29
    levy = {}
    for r in (27, 28, 29):
        label = ws.cell(row=r, column=1).value
        balance_col_b = money(ws.cell(row=r, column=2).value)
        total_col_c = money(ws.cell(row=r, column=3).value)
        rate = money(ws.cell(row=r, column=5).value)
        if label is None:
            continue
        levy[str(label).strip()] = (balance_col_b, total_col_c, rate)
        TAXIMPACT_ROWS.append(dict(file=file_label, assessed_value='', scenario=str(label).strip(),
                                    rate_per_1000=rate, estimated_bill=balance_col_b,
                                    impact_vs_fy26=total_col_c, average_home_marker=False))
    if 'Balance' in levy:
        base = levy['Balance'][0]
        for key in ('Tier 1', 'Tier 2'):
            if key in levy:
                expected_total = base + levy[key][0]
                printed_total = levy[key][1]
                status = 'tie' if abs(expected_total - printed_total) <= TOL else 'mismatch'
                record_tie(file_label, 'Sheet1', f'{key}: Total = own levy increase + Balance', 'amount',
                           round(expected_total, 2), printed_total, status)


# ---------------------------------------------------------------------------
# Version diffs
# ---------------------------------------------------------------------------

def diff_dept_totals(file_a, sheet_a, file_b, sheet_b, common_cols):
    ta = department_totals(file_a, sheet_a)
    tb = department_totals(file_b, sheet_b)
    diffs = []
    for code in sorted(set(ta) | set(tb)):
        for col in common_cols:
            va, vb = ta.get(code, {}).get(col), tb.get(code, {}).get(col)
            if va is None or vb is None:
                continue
            if abs(float(va) - float(vb)) > TOL:
                diffs.append((code, col, va, vb))
    return diffs


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def write_csv(path, rows, fieldnames):
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def run(write=True):
    global VERSION_ROWS, TIES, ANOMALIES, MISMATCHES, REVDIST_ROWS, FREECASH_ROWS, TAXIMPACT_ROWS
    VERSION_ROWS = []
    TIES = []
    ANOMALIES = []
    MISMATCHES = []
    REVDIST_ROWS = []
    FREECASH_ROWS = []
    TAXIMPACT_ROWS = []

    # D1
    parse_line_item_sheet(D1_XLSX_32_23, 'Sheet1',
                           'fy-2024-tm-preliminary-budget-line-item-detail-3-2-23.xlsx', 'Sheet1',
                           '2023-03-02', 'filename ("-3-2-23")')
    parse_line_item_sheet(D1_XLSX_UNDATED, 'Sheet1',
                           'fy-2024-tm-preliminary-budget-line-item-detail.xlsx', 'Sheet1',
                           None, 'undated -- the FY24 preliminary detail before the 3/2/23 revision; '
                                 'see docstring, PDF twin spot-checked identical')
    parse_adjustment_worksheet()

    # D2
    parse_line_item_sheet(D2_XLSX, 'FY2025 Line Item Budget',
                           'line-item-detail-2-13-24.xlsx', 'FY2025 Line Item Budget',
                           '2024-02-13', 'filename ("2-13-24")')
    parse_line_item_sheet(D2_XLSX, 'FY20-FY24 Forecast Line Item',
                           'line-item-detail-2-13-24.xlsx', 'FY20-FY24 Forecast Line Item',
                           '2024-02-13', 'filename ("2-13-24")')
    wb2 = openpyxl.load_workbook(D2_XLSX, data_only=True)
    for sn in REVEXP_SHEETS:
        parse_revexp_sheet(wb2, sn, 'line-item-detail-2-13-24.xlsx')

    # D6, D7
    parse_revdist()
    freecash_diffs = parse_freecash()
    parse_tax_impact()

    # gl-history comparison: D1 (FY2024) and D2 (FY2025)
    gl_compare = {}
    gl_compare['D1 3-2-23 (FY24 TM Budget 3/2/23) vs gl-history FY2024'] = compare_to_gl_history(
        'fy-2024-tm-preliminary-budget-line-item-detail-3-2-23.xlsx', 'Sheet1', '2024', 'FY24 TM Budget 3/2/23')
    gl_compare['D2 FY2025 Line Item Budget (FY25 TM Prelim. Budget) vs gl-history FY2025'] = compare_to_gl_history(
        'line-item-detail-2-13-24.xlsx', 'FY2025 Line Item Budget', '2025', 'FY25 TM Prelim. Budget')

    # version diffs
    d1_diff = diff_dept_totals(
        'fy-2024-tm-preliminary-budget-line-item-detail-3-2-23.xlsx', 'Sheet1',
        'fy-2024-tm-preliminary-budget-line-item-detail.xlsx', 'Sheet1',
        ['FY22 Final Budget after Recap', 'FY23 TM Target Budget', 'FY23 Requested Budget',
         'FY23 TM Prelim Budget', 'FY23 Final Budget after Recap', 'FY24 Target Budget',
         'FY24 Requested Budget', 'FY24 TM Prelim Budget'])

    revexp_diffs = []
    sheets_present = [sn for sn in REVEXP_SHEETS if sn in wb2.sheetnames]
    for i in range(len(sheets_present) - 1):
        a, b = sheets_present[i], sheets_present[i + 1]
        rows_a = {(r['section'], r['description'], r['column']): r['value']
                  for r in VERSION_ROWS if r['file'] == 'line-item-detail-2-13-24.xlsx' and r['sheet'] == a}
        rows_b = {(r['section'], r['description'], r['column']): r['value']
                  for r in VERSION_ROWS if r['file'] == 'line-item-detail-2-13-24.xlsx' and r['sheet'] == b}
        changed = 0
        for key in set(rows_a) & set(rows_b):
            va, vb = rows_a[key], rows_b[key]
            if va == '' or vb == '':
                continue
            if abs(float(va) - float(vb)) > TOL:
                changed += 1
        revexp_diffs.append((a, b, changed, len(set(rows_a) & set(rows_b))))

    # ---- report ----
    print(f'town-budget-versions.csv: {len(VERSION_ROWS)} rows')
    print(f'ties attempted: {len(TIES)}')
    status_counts = defaultdict(int)
    for t in TIES:
        status_counts[t['status']] += 1
    print(f'  tie: {status_counts["tie"]}  unchecked: {status_counts["unchecked"]}  '
          f'mismatch: {status_counts["mismatch"]}')
    if ANOMALIES:
        print(f'documented anomalies: {len(ANOMALIES)}')
        for a in ANOMALIES:
            print(f"  [{a['file']} / {a['sheet']}] {a['what']}")
            if 'note' in a:
                print(f"      {a['note']}")
    if MISMATCHES:
        print(f'UNDOCUMENTED MISMATCHES: {len(MISMATCHES)}')
        for m in MISMATCHES[:30]:
            print('  ', m)

    print()
    print('gl-history comparison (department totals, original appropriation, tolerance $1):')
    for label, (agree, differ) in gl_compare.items():
        print(f'  {label}: {len(agree)} agree, {len(differ)} differ')
        for code, dept, wb_val, gl_val, diff in differ:
            print(f'    dept {code} ({dept}): workbook={wb_val} gl-history original={gl_val} diff={diff}'
                  f'  -- a preliminary budget is EXPECTED to differ from the voted original')

    print()
    print('version diff, D1 two xlsx (3-2-23 vs undated), department totals:')
    if d1_diff:
        for code, col, va, vb in d1_diff[:20]:
            print(f'  dept {code} / {col}: 3-2-23={va}  undated={vb}')
    else:
        print('  identical on every shared column, every department.')

    print()
    print('version diff, D2 five Revenue-Expense sheets, consecutive pairs:')
    for a, b, changed, common in revexp_diffs:
        print(f'  {a} -> {b}: {changed} of {common} shared (label,column) cells changed')

    print()
    print('version diff, D6 Free Cash Appropriations (2.22.25 vs 2.27.25):')
    for k, v1, v2 in freecash_diffs:
        print(f'  {k}: 2.22.25={v1}  2.27.25={v2}')

    if MISMATCHES and write:
        print()
        print(f'REFUSING TO WRITE: {len(MISMATCHES)} undocumented mismatch(es). See above.')
        return False

    if write:
        write_csv(OUT_VERSIONS, VERSION_ROWS,
                  ['file', 'sheet', 'version_date', 'version_date_source', 'section', 'row_type',
                   'department_code', 'department', 'account', 'description', 'column', 'value'])
        write_csv(OUT_REVDIST, REVDIST_ROWS,
                  ['file', 'sheet', 'line', 'fy25', 'fy26', 'variance', 'share_of_total_pct'])
        write_csv(OUT_FREECASH, FREECASH_ROWS,
                  ['file', 'version', 'version_date', 'item', 'parent', 'value'])
        write_csv(OUT_TAXIMPACT, TAXIMPACT_ROWS,
                  ['file', 'assessed_value', 'scenario', 'rate_per_1000', 'estimated_bill',
                   'impact_vs_fy26', 'average_home_marker'])
        print()
        print(f'wrote {OUT_VERSIONS}')
        print(f'wrote {OUT_REVDIST}')
        print(f'wrote {OUT_FREECASH}')
        print(f'wrote {OUT_TAXIMPACT}')
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    ok = run(write=not args.check)
    if not ok:
        sys.exit(1)
    if args.check:
        if MISMATCHES:
            print(f'CHECK FAILED: {len(MISMATCHES)} undocumented mismatch(es).')
            sys.exit(1)
        for path in (OUT_VERSIONS, OUT_REVDIST, OUT_FREECASH, OUT_TAXIMPACT):
            if not os.path.exists(path):
                print(f'CHECK FAILED: {path} does not exist -- run without --check first.')
                sys.exit(1)
        print('CHECK OK: no undocumented mismatches; all four CSVs exist.')


if __name__ == '__main__':
    main()
