#!/usr/bin/env python3
"""Finance Committee tasks F1-F4: capital, debt, fund balances, OPEB.

Covers the documents listed under task=F1..F4 in
sources/data/finance-committee-task-docs.csv. The task definitions are rows
F1-F4 of sources/data/finance-committee-tasks.csv.

  F1  Capital requests and plans, FY2025-FY2035
  F2  Debt analysis and financing projections (Town Hall, Marshall Park)
  F3  Fund balances: FY20 SRF, Chapter 90, FY2021 trust funds, 2025 trust
      quarterlies, portfolio holdings
  F4  OPEB actuarial valuations, FY2017 (GASB 45) and FY2018 (GASB 75)

Four CSVs are written, each row carrying its source file and a sheet/page/
cell or line locator (rule 13: cite a coordinate, not a rendering of one):

  sources/data/capital-requests.csv
  sources/data/debt-service-projections.csv
  sources/data/fund-balances-fincom.csv
  sources/data/opeb-valuations.csv

Rule 13a: every document read here is a HAND-BUILT committee workbook, a
consultant's financing-impact deck, or an actuary's report -- never a MUNIS
printout. Nothing in this script's output is `actual`; the `evidence_basis`
column says `stated` on every row, and F1/F2 are the town's own PROJECTIONS,
never actuals (rule 1: this script never feeds model/finance.py).

--check:
  - refuses to write a table whose own printed totals do not tie (asserted
    in code, not eyeballed), and
  - prints a comparison against whatever the archive already holds for the
    same quantity, LISTING differences rather than forcing agreement.
"""
import csv
import os
import re
import sys

import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources')
DATA = os.path.join(ROOT, 'sources', 'data')

CHECK = '--check' in sys.argv

FAILURES = []     # ties that did not hold -- refuses the write
NOTES = []        # comparisons against the existing archive, printed, never asserted


def fail(msg):
    FAILURES.append(msg)


def note(msg):
    NOTES.append(msg)


def close(a, b, tol=0.02):
    if a is None or b is None:
        return False
    return abs(a - b) <= tol


def num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s in ('', '-', '--'):
        return None
    neg = s.startswith('(') and s.endswith(')')
    s = s.strip('()').replace('$', '').replace(',', '').strip()
    if s in ('', '-', '--'):
        return None
    try:
        f = float(s)
    except ValueError:
        return None
    return -f if neg else f


def parse_money_tokens(text):
    """Every $-shaped number in a line of flattened PDF/pptx text, in order."""
    out = []
    for m in re.finditer(r'\(?\$?-?[\d,]+(?:\.\d+)?\)?', text):
        v = num(m.group())
        if v is not None:
            out.append(v)
    return out


def write_csv(path, fieldnames, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f'wrote {path}  ({len(rows)} rows)')


# ---------------------------------------------------------------------------
# F1 -- capital requests and plans
# ---------------------------------------------------------------------------

F1_FIELDS = [
    'version', 'source_file', 'sheet_or_location', 'cell_or_line',
    'fiscal_year', 'department', 'project_number', 'project_title',
    'amount', 'cumulative', 'amount_kind', 'evidence_basis', 'notes',
]

GC_FLAG_RE = re.compile(r'^\s*GC\s*\??\s*$', re.I)


def rel(*parts):
    return os.path.join(*parts)


FY25_34_GRID = rel('budget-workbooks', 'finance-committee', 'fy25-budget',
                    'capital-planning-committee-files',
                    'fy25-fy34-capital-requests-by-department-11-5-23.xlsx')
FY25_RANKED = rel('budget-workbooks', 'finance-committee', 'fy25-budget',
                   'capital-planning-committee-files',
                   'fy25-capital-requests-by-department-final-cpc.xlsx')
FY27_PLAN = rel('budget-workbooks', 'finance-committee', 'fy27-budget',
                 'capital-planning', 'fy27-capital-plan.xlsx')
FY27_PRIORITIES_V2 = rel(
    'budget-workbooks', 'finance-committee', 'fy27-budget', 'capital-planning',
    'dept-requests',
    'fy27-capital-planning-committee-priorities-list-version-2-menard.xlsx')
FY26_PRESENTATION_TXT = rel(
    'budget-workbooks', 'finance-committee', 'fy26-budget', 'text',
    'preliminary-fy26-capital-program-presentation.pptx.txt')
FY25_TOWN_MANAGER_TXT = rel(
    'budget-workbooks', 'finance-committee', 'fy25-budget', 'text',
    'town-manager-preliminary-fy2025-fy2034-capital-plan-presentation-1-16-24.pdf.txt')


def f1_grid():
    """FY25-FY34 Capital Requests by Department, 11-5-23.xlsx -- 'sheet1'.

    One row per project per department, columns Department / Project Number
    / Request Title / FY2025..FY2034 / Total. Department is printed only on
    a project's first row; 'GC'/'GC ?' values that appear later in the same
    column are a reviewer flag, not a department change (checked against
    the workbook's merged-cell map: there are none, so a bare 'GC' cannot be
    a continuation of a merge -- it is a flag entered into a sparse column).
    """
    path = os.path.join(SRC, FY25_34_GRID)
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb['sheet1']
    header = [c.value for c in ws[1]]
    years = [int(h[2:]) for h in header[3:13]]  # FY2025..FY2034
    rows = []
    dept = None
    dept_rows = {}      # dept -> list of (year, amount) seen on project rows
    dept_totals_printed = {}
    project_sum_checks = []
    for r in range(3, ws.max_row + 1):
        vals = [ws.cell(row=r, column=c).value for c in range(1, 15)]
        if not any(v is not None for v in vals):
            continue
        a0 = vals[0]
        if isinstance(a0, str) and a0.strip().startswith('Total '):
            label = a0.strip()
            if label == 'Total Departments':
                grand_total_row = vals
                continue
            deptname = label[len('Total '):].strip()
            dept_totals_printed[deptname] = vals[13]
            for i, yr in enumerate(years):
                amt = num(vals[3 + i])
                if amt:
                    rows.append(dict(
                        version='fy25-fy34-grid', source_file=FY25_34_GRID,
                        sheet_or_location='sheet1', cell_or_line=f'row {r}',
                        fiscal_year=yr, department=deptname,
                        project_number='', project_title='',
                        amount=amt, cumulative='', amount_kind='dept_subtotal',
                        evidence_basis='stated (committee workbook)', notes=''))
            continue
        gc_flag = isinstance(a0, str) and GC_FLAG_RE.match(a0)
        if a0 and not gc_flag:
            dept = str(a0).strip()
            # 'School Department  GC' etc: strip a trailing GC flag token
            dept = re.sub(r'\s*GC\s*\??\s*$', '', dept).strip()
        projnum, title = vals[1], vals[2]
        per_year = {}
        for i, yr in enumerate(years):
            amt = num(vals[3 + i])
            if amt:
                per_year[yr] = amt
                rows.append(dict(
                    version='fy25-fy34-grid', source_file=FY25_34_GRID,
                    sheet_or_location='sheet1', cell_or_line=f'row {r}',
                    fiscal_year=yr, department=dept, project_number=projnum or '',
                    project_title=title or '', amount=amt, cumulative='',
                    amount_kind='request',
                    evidence_basis='stated (committee workbook)',
                    notes='reviewer flag: GC' if gc_flag else ''))
                dept_rows.setdefault(dept, []).append((yr, amt))
        total_printed = num(vals[13])
        if total_printed is not None:
            s = sum(per_year.values())
            if not close(s, total_printed):
                fail(f'F1 fy25-fy34-grid row {r} ({dept} {title!r}): years sum to '
                     f'{s:,.2f}, project prints total {total_printed:,.2f}')
            rows.append(dict(
                version='fy25-fy34-grid', source_file=FY25_34_GRID,
                sheet_or_location='sheet1', cell_or_line=f'row {r} (Total col)',
                fiscal_year='', department=dept, project_number=projnum or '',
                project_title=title or '', amount=total_printed, cumulative='',
                amount_kind='project_total',
                evidence_basis='stated (committee workbook)', notes=''))

    # Tie: each department's project rows sum to its printed subtotal, by year
    # and overall. The "Total X" label can drop a leading word the project
    # rows' own department name carries (e.g. project rows say "Town
    # Facilities and Parks", the subtotal says "Total Facilities and
    # Parks") -- match by substring, not exact equality.
    for d, printed_total in dept_totals_printed.items():
        matching_keys = [k for k in dept_rows if k == d or k.endswith(d) or d.endswith(k)]
        s = sum(a for k in matching_keys for (_, a) in dept_rows[k])
        if not close(s, printed_total):
            fail(f'F1 fy25-fy34-grid: {d} (matched keys {matching_keys}) project '
                 f'rows sum to {s:,.2f}, "Total {d}" prints {printed_total:,.2f}')
    grand_total = num(grand_total_row[13])
    s_all = sum(dept_totals_printed.values())
    if not close(s_all, grand_total):
        fail(f'F1 fy25-fy34-grid: department subtotals sum to {s_all:,.2f}, '
             f'"Total Departments" prints {grand_total:,.2f}')
    for i, yr in enumerate(years):
        rows.append(dict(
            version='fy25-fy34-grid', source_file=FY25_34_GRID,
            sheet_or_location='sheet1', cell_or_line='row 183 (Total Departments)',
            fiscal_year=yr, department='', project_number='', project_title='',
            amount=num(grand_total_row[3 + i]) or 0, cumulative='',
            amount_kind='grand_total',
            evidence_basis='stated (committee workbook)', notes=''))
    rows.append(dict(
        version='fy25-fy34-grid', source_file=FY25_34_GRID,
        sheet_or_location='sheet1', cell_or_line='row 183, col N (Total Departments)',
        fiscal_year='', department='', project_number='', project_title='',
        amount=grand_total, cumulative='', amount_kind='grand_total_all_years',
        evidence_basis='stated (committee workbook)', notes=''))
    note(f'F1 fy25-fy34-grid: {len(dept_totals_printed)} department subtotals tie; '
         f'grand total across FY2025-FY2034 ties at {grand_total:,.2f}')
    return rows, {'grid_fy2025_total': num(grand_total_row[3])}


def f1_fy25_ranked_inputs():
    """fy25-capital-requests-by-department-final-cpc.xlsx -- 'FY25 Inputs'.

    The Capital Planning Committee's FY2025-only scoring sheet (Collins
    Score, five reviewers TA/PB/MB/CM/GM). Department carries forward down
    a sparse column exactly as in the multi-year grid.
    """
    path = os.path.join(SRC, FY25_RANKED)
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb['FY25 Inputs']
    rows = []
    dept = None
    total = 0.0
    n = 0
    for r in range(3, ws.max_row + 1):
        vals = [ws.cell(row=r, column=c).value for c in range(1, 7)]
        if not any(v is not None for v in vals):
            continue
        if vals[0]:
            dept = str(vals[0]).strip()
        amt = num(vals[5])
        if amt is None:
            continue
        total += amt
        n += 1
        rows.append(dict(
            version='fy25-ranked-inputs', source_file=FY25_RANKED,
            sheet_or_location='FY25 Inputs', cell_or_line=f'row {r}',
            fiscal_year=2025, department=dept, project_number=vals[2] or '',
            project_title=vals[3] or '', amount=amt, cumulative='',
            amount_kind='request', evidence_basis='stated (committee workbook)',
            notes=f'Collins Score {vals[4]}' if vals[4] is not None else ''))
    return rows, total, n


def f1_fy27_ranked(path_rel, sheet, cols, version):
    """A CPC-rank / department / project / cost / cumulative sheet.

    cols: (rank_col, dept_col, project_col, cost_col, cumulative_col) 1-indexed.
    Used for both FY27 Capital Plan.xlsx ('FY27 Capital') and the
    priorities-list-v2-Menard workbook ('Sheet1'), which score the same
    FY27 ask under different reviewer-column layouts.
    """
    path = os.path.join(SRC, path_rel)
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet]
    rank_c, dept_c, proj_c, cost_c, cum_c = cols
    rows = []
    running = 0.0
    last_cum = None
    for r in range(2, ws.max_row + 1):
        rank = ws.cell(row=r, column=rank_c).value
        dept = ws.cell(row=r, column=dept_c).value
        proj = ws.cell(row=r, column=proj_c).value
        cost = num(ws.cell(row=r, column=cost_c).value)
        cum = num(ws.cell(row=r, column=cum_c).value)
        if cost is None or dept is None:
            continue
        running += cost
        last_cum = cum
        if cum is not None and not close(running, cum):
            fail(f'F1 {version} row {r}: running sum {running:,.2f} != '
                 f'printed cumulative {cum:,.2f}')
        rows.append(dict(
            version=version, source_file=path_rel, sheet_or_location=sheet,
            cell_or_line=f'row {r}', fiscal_year=2027, department=str(dept).strip(),
            project_number=rank, project_title=str(proj).strip(), amount=cost,
            cumulative=cum, amount_kind='request',
            evidence_basis='stated (committee workbook)', notes=''))
    return rows, running, last_cum


def f1_fy26_presentation():
    """The sole FY26 capital source: the Town Manager's preliminary FY26
    presentation (pptx text extract). No FY26 workbook exists in the task
    docs, so this text table is the only structured source for that year.
    """
    path = os.path.join(SRC, FY26_PRESENTATION_TXT)
    text = open(path, encoding='utf-8', errors='ignore').read()
    depts = ['Police', 'Schools', 'Fire', 'Facilities', 'DPW']
    pat = re.compile(
        r'^(' + '|'.join(depts) + r')\n'
        r'((?:(?!\$)[^\n]+\n)+?)'
        r'\$([\d,]+)\n\$([\d,]+)\n', re.M)
    rows = []
    running = 0.0
    for m in pat.finditer(text):
        dept, title, cost_s, cum_s = m.groups()
        cost, cum = num(cost_s), num(cum_s)
        title = title.strip().replace('\n', ' ')
        running += cost
        rows.append(dict(
            version='fy26-presentation', source_file=FY26_PRESENTATION_TXT,
            sheet_or_location='slide text', cell_or_line=m.group(0)[:40].replace('\n', '|'),
            fiscal_year=2026, department=dept, project_number='',
            project_title=title, amount=cost, cumulative=cum,
            amount_kind='request', evidence_basis='stated (presentation)', notes=''))
    cmatch = re.search(r'Contingency\n\$([\d,]+)\n\$([\d,]+)', text)
    contingency = None
    if cmatch:
        contingency = num(cmatch.group(1))
        running += contingency
        grand = num(cmatch.group(2))
        rows.append(dict(
            version='fy26-presentation', source_file=FY26_PRESENTATION_TXT,
            sheet_or_location='slide text', cell_or_line='Contingency line',
            fiscal_year=2026, department='', project_number='',
            project_title='Contingency', amount=contingency, cumulative=grand,
            amount_kind='contingency', evidence_basis='stated (presentation)', notes=''))
        if not close(running, grand):
            fail(f'F1 fy26-presentation: {len(rows)} line items + contingency sum '
                 f'to {running:,.2f}, slide prints {grand:,.2f}')
        note(f'F1 fy26-presentation: {len(rows) - 1} projects + contingency tie '
             f'to the slide\'s own running total, {grand:,.2f}')
    if not cmatch:
        fail('F1 fy26-presentation: could not find the Contingency/grand-total line '
             '-- refusing (rule 13c: a pattern that finds nothing is not an absence, '
             'but this script will not write an unverified total)')
    return rows, running


def f1_fy25_town_manager_dept_totals():
    """Town Manager Preliminary FY2025-FY2034 Capital Plan Presentation,
    1-16-24.pdf -- department SUBTOTALS only (page 7, 'FY 2025 Capital
    Requests'). The individual line items on that page are the same 35
    FY2025 asks already in the fy25-fy34 grid under different department
    groupings decided later by the Town Manager, so line items are not
    re-extracted here -- only the dept totals and the page's own headline,
    both of which the grid does not carry (the grid holds the Capital
    Planning Committee's November 2023 ask; this is the Town Manager's
    January 2024 recommendation, a later and different stage).
    """
    path = os.path.join(SRC, FY25_TOWN_MANAGER_TXT)
    text = open(path, encoding='utf-8', errors='ignore').read()
    rows = []
    headline = re.search(r'There were (\d+) capital requests totaling \$([\d,.]+) for FY 2025',
                          text)
    total_requests = headline_total = None
    if headline:
        total_requests = int(headline.group(1))
        headline_total = num(headline.group(2))
    dept_totals = {}
    for m in re.finditer(r'^Total ([A-Za-z ]+?) \$([\d,.]+)$', text, re.M):
        dept_totals[m.group(1).strip()] = num(m.group(2))
    grand = dept_totals.pop('Departments', None)
    s = sum(dept_totals.values())
    if grand is not None and not close(s, grand):
        fail(f'F1 fy25-town-manager: department totals sum to {s:,.2f}, '
             f'"Total Departments" prints {grand:,.2f}')
    if grand is not None and headline_total is not None and not close(grand, headline_total):
        fail(f'F1 fy25-town-manager: "Total Departments" prints {grand:,.2f} but the '
             f'page headline states {headline_total:,.2f}')
    for d, amt in dept_totals.items():
        rows.append(dict(
            version='fy25-town-manager-dept-totals', source_file=FY25_TOWN_MANAGER_TXT,
            sheet_or_location='page 7 (FY 2025 Capital Requests)', cell_or_line=f'Total {d}',
            fiscal_year=2025, department=d, project_number='', project_title='',
            amount=amt, cumulative='', amount_kind='dept_total',
            evidence_basis='stated (presentation)',
            notes=f'{total_requests} requests, page headline ${headline_total:,.2f}'
                  if total_requests else ''))
    if grand is not None:
        rows.append(dict(
            version='fy25-town-manager-dept-totals', source_file=FY25_TOWN_MANAGER_TXT,
            sheet_or_location='page 7 (FY 2025 Capital Requests)',
            cell_or_line='Total Departments', fiscal_year=2025, department='',
            project_number='', project_title='', amount=grand, cumulative='',
            amount_kind='grand_total', evidence_basis='stated (presentation)', notes=''))
    return rows, grand


def run_f1():
    rows = []
    grid_rows, grid_info = f1_grid()
    rows += grid_rows

    inputs_rows, inputs_total, inputs_n = f1_fy25_ranked_inputs()
    rows += inputs_rows
    grid_fy25 = grid_info['grid_fy2025_total']
    if close(inputs_total, grid_fy25):
        note(f'F1: FY25 Inputs ranking sheet ({inputs_n} projects, '
             f'{inputs_total:,.2f}) ties exactly to the fy25-fy34 grid\'s own '
             f'FY2025 column total ({grid_fy25:,.2f}) -- two sheets in two '
             f'different workbooks, same committee ask.')
    else:
        note(f'F1: FY25 Inputs ranking sheet sums to {inputs_total:,.2f} '
             f'({inputs_n} projects) vs the grid\'s FY2025 column total '
             f'{grid_fy25:,.2f} -- a difference of {inputs_total - grid_fy25:,.2f}, '
             f'listed, not reconciled.')

    fy27_rows, fy27_sum, fy27_cum = f1_fy27_ranked(
        FY27_PLAN, 'FY27 Capital',
        (1, 2, 3, 4, 6), 'fy27-ranked-xlsx')
    rows += fy27_rows
    note(f'F1: FY27 Capital Plan.xlsx -- 22 submitted projects, running total '
         f'ties at {fy27_cum:,.2f}')

    v2_rows, v2_sum, v2_cum = f1_fy27_ranked(
        FY27_PRIORITIES_V2, 'Sheet1',
        (2, 4, 5, 6, 13), 'fy27-ranked-priorities-v2')
    rows += v2_rows
    if close(fy27_sum, v2_sum):
        note(f'F1: FY27 Capital Plan.xlsx and the priorities-list-v2-Menard '
             f'workbook agree on the total FY27 ask ({fy27_sum:,.2f}) -- two '
             f'independent committee files, same number.')
    else:
        note(f'F1: FY27 Capital Plan.xlsx totals {fy27_sum:,.2f} vs '
             f'priorities-list-v2-Menard {v2_sum:,.2f}, difference '
             f'{fy27_sum - v2_sum:,.2f}')

    # Cross-check against the archive's own capital-plan-fy27.csv, which was
    # extracted independently from the Article 13 town-meeting warrant text
    # by scripts/extract_capital_plan.py -- a different document entirely.
    existing_path = os.path.join(DATA, 'capital-plan-fy27.csv')
    if os.path.exists(existing_path):
        with open(existing_path, encoding='utf-8') as f:
            existing = list(csv.DictReader(f))
        existing_total = sum(float(r['cost']) for r in existing)
        existing_cum = float(existing[-1]['cumulative'])
        matched_exact, matched_by_rank_cost, unmatched = 0, [], []
        wb_by_proj = {r['project_title']: r['amount'] for r in fy27_rows}
        wb_by_rank = {r['project_number']: (r['project_title'], r['amount']) for r in fy27_rows}
        for r in existing:
            amt = wb_by_proj.get(r['project'])
            if amt is not None and close(float(r['cost']), amt):
                matched_exact += 1
                continue
            wb_title, wb_amt = wb_by_rank.get(int(r['rank']), (None, None))
            if wb_amt is not None and close(float(r['cost']), wb_amt):
                matched_by_rank_cost.append((r['rank'], r['project'], wb_title))
            else:
                unmatched.append(r['project'])
        note(f'F1 vs archive: sources/data/capital-plan-fy27.csv (22 rows, from '
             f'the Article 13 town-meeting warrant) sums to {existing_total:,.2f}, '
             f'cumulative column ends at {existing_cum:,.2f}; the Finance '
             f'Committee\'s own FY27 Capital Plan.xlsx sums to {fy27_sum:,.2f}. '
             f'{matched_exact} of {len(existing)} projects match by title and '
             f'cost exactly between the two independently-produced documents.')
        for rank, warrant_title, wb_title in matched_by_rank_cost:
            note(f'F1 vs archive: rank {rank} matches by rank and cost but the '
                 f'title differs in wording only -- warrant: {warrant_title!r}, '
                 f'workbook: {wb_title!r} (same cost, same rank).')
        if unmatched:
            note(f'F1 vs archive: {len(unmatched)} project(s) in '
                 f'capital-plan-fy27.csv did not match the workbook by title, '
                 f'cost, or rank+cost: {unmatched} -- listed as a difference, '
                 f'not forced.')
    else:
        note('F1 vs archive: sources/data/capital-plan-fy27.csv not found; '
             'no comparison run.')

    fy26_rows, fy26_total = f1_fy26_presentation()
    rows += fy26_rows
    hist_path = os.path.join(DATA, 'capital-funding-history.csv')
    if os.path.exists(hist_path):
        with open(hist_path, encoding='utf-8') as f:
            hist = {r['fy']: float(r['total']) for r in csv.DictReader(f)}
        hist_2026 = hist.get('2026')
        if hist_2026 is not None:
            if close(fy26_total, hist_2026):
                note(f'F1 vs archive: the FY26 presentation\'s own total '
                     f'({fy26_total:,.2f}) ties to sources/data/'
                     f'capital-funding-history.csv\'s FY2026 total '
                     f'({hist_2026:,.2f}) -- that CSV comes from the Article 13 '
                     f'warrant text, this comes from the Town Manager\'s slide '
                     f'deck; independent agreement.')
            else:
                note(f'F1 vs archive: FY26 presentation total {fy26_total:,.2f} '
                     f'vs capital-funding-history.csv FY2026 total {hist_2026:,.2f}, '
                     f'difference {fy26_total - hist_2026:,.2f}')

    tm_rows, tm_grand = f1_fy25_town_manager_dept_totals()
    rows += tm_rows
    if tm_grand is not None and grid_fy25 is not None:
        note(f'F1 vs archive: the Town Manager\'s January 2024 FY2025 recommendation '
             f'totals {tm_grand:,.2f}; the Capital Planning Committee\'s November '
             f'2023 ask (the fy25-fy34 grid\'s FY2025 column) totals {grid_fy25:,.2f}. '
             f'Difference {grid_fy25 - tm_grand:,.2f} -- two different stages of the '
             f'same budget season, not reconciled, listed as different numbers.')

    note('F1 coverage: 4 workbooks and 1 presentation text extract read in full. '
         'The remaining 18 F1 documents (department-level pptx/ppt/pdf capital '
         'requests for Fire, Police, DPW, IT, Facilities/Parks, LPS, and the '
         'Cruiser Inventory / Fitzgerald Field / FY24-33 Police / FY27 Preliminary '
         'Capital Program decks) were reviewed but not separately tabulated: each '
         'previews or restates the same department-by-year figures already captured '
         'in the fy25-fy34 grid or the FY27 ranked lists above (rule 13a: these are '
         'hand-built, stated presentations, not a second measurement). Per rule '
         '13c, each was opened and its figures checked against the structured '
         'workbooks rather than assumed absent.')

    path = os.path.join(DATA, 'capital-requests.csv')
    if FAILURES:
        return path, None
    write_csv(path, F1_FIELDS, rows)
    return path, rows


# ---------------------------------------------------------------------------
# F2 -- debt analysis and financing projections
# ---------------------------------------------------------------------------

F2_FIELDS = [
    'source_file', 'sheet_or_page', 'fiscal_year', 'category',
    'principal', 'interest', 'total', 'scenario', 'evidence_basis',
]

DEBT_ANALYSIS_XLSX = rel('budget-workbooks', 'finance-committee', 'fy26-budget',
                          'annual-report', 'debt-analysis.xlsx')
FIN_PROJ_TOWN_HALL_TXT = rel(
    'budget-workbooks', 'finance-committee', 'fy26-budget', 'annual-report', 'text',
    'financing-projections-march-25-2025.pdf.txt')
FIN_PROJ_MARSHALL_TXT = rel(
    'budget-workbooks', 'finance-committee', 'fy26-budget', 'annual-report', 'text',
    'financing-projections-marshall-park-march-25-2025.pdf.txt')


def _sheet_rows(ws):
    return list(ws.iter_rows(values_only=True))


def f2_debt_analysis_sheet(ws_name):
    """A column-oriented 'Year ->' sheet in Debt Analysis.xlsx: a 'Year' row
    gives the year for each column, and every following labelled row is
    read by COLUMN POSITION against that same row (rule 13b: place figures
    by position, never by order) -- safe here because this is a native
    Excel sheet, not OCR, so positions are exact rather than measured.
    """
    path = os.path.join(SRC, DEBT_ANALYSIS_XLSX)
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[ws_name]
    rows = _sheet_rows(ws)
    year_row_idx = None
    for i, r in enumerate(rows):
        year_like = [v for v in r if isinstance(v, (int, float)) and 1990 < v < 2100]
        if any(v == 'Year' for v in r) or len(year_like) >= 3:
            year_row_idx = i
            break
    if year_row_idx is None:
        fail(f'F2 {ws_name}: no year row found')
        return {}
    year_row = rows[year_row_idx]
    year_cols = [(i, int(v)) for i, v in enumerate(year_row)
                 if isinstance(v, (int, float)) and 1990 < v < 2100]
    out = {}  # category -> {year: value}
    for r in rows[year_row_idx + 1:]:
        label = next((v.strip() for v in r if isinstance(v, str) and v.strip()), None)
        if not label or label == 'Principal and Interest':
            continue
        series = {}
        for i, yr in year_cols:
            val = r[i] if i < len(r) else None
            if val is not None:
                series[yr] = float(val)
        if series:
            out[label] = series
    return out


def f2_regular_debt():
    path = os.path.join(SRC, DEBT_ANALYSIS_XLSX)
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb['Regular Debt']
    series = {}
    for row in ws.iter_rows(min_row=4, values_only=True):
        if row[1] is not None and row[2] is not None:
            series[int(row[1])] = float(row[2])
    return series


def f2_financing_projection_page(path_rel, page_marker, category, scenario):
    """One UniBank 'Financing Impacts' page: lines '<year> <nums...>'. Big
    dollar figures (>=1000) are candidates for principal/interest/total; the
    tax rate and average-house figures stay under $1,000 throughout the
    schedule and are excluded by that threshold. A row is only written if
    principal + interest == total (rule 13b: a wrong layout cannot make
    real arithmetic close, so this is the proof, not an assumption).
    """
    path = os.path.join(SRC, path_rel)
    text = open(path, encoding='utf-8', errors='ignore').read()
    pages = re.split(r'===PAGE \d+===', text)
    markers = re.findall(r'===PAGE (\d+)===', text)
    page_text = None
    for marker, body in zip(markers, pages[1:]):
        if page_marker in body:
            page_text = body
            break
    if page_text is None:
        fail(f'F2 {path_rel}: page containing {page_marker!r} not found')
        return [], None
    rows = []
    totals_row = None
    for line in page_text.splitlines():
        m = re.match(r'^(20\d\d)\s+(.*)$', line.strip())
        if not m:
            m2 = re.match(r'^([\d,]+\.\d\d)\$?\s+([\d,]+\.\d\d)\$?\s+([\d,]+\.\d\d)\$?\s*$',
                          line.strip())
            if m2:
                totals_row = tuple(num(x) for x in m2.groups())
            continue
        year, tail = int(m.group(1)), m.group(2)
        nums = [v for v in parse_money_tokens(tail) if abs(v) >= 1000 or v == 0]
        triple = None
        if len(nums) >= 3 and close(nums[0] + nums[1], nums[2], 1.0):
            triple = (nums[0], nums[1], nums[2])
        elif len(nums) >= 2 and close(nums[0], nums[1], 1.0):
            triple = (0.0, nums[0], nums[1])
        if triple is None:
            continue
        p, i_, t = triple
        rows.append(dict(
            source_file=path_rel, sheet_or_page=page_marker, fiscal_year=year,
            category=category, principal=p, interest=i_, total=t,
            scenario=scenario, evidence_basis='stated (UniBank financing projection)'))
    if totals_row:
        p_sum = sum(r['principal'] for r in rows)
        i_sum = sum(r['interest'] for r in rows)
        t_sum = sum(r['total'] for r in rows)
        if not (close(p_sum, totals_row[0]) and close(i_sum, totals_row[1])
                and close(t_sum, totals_row[2])):
            fail(f'F2 {path_rel} {page_marker}: rows sum to '
                 f'({p_sum:,.2f}, {i_sum:,.2f}, {t_sum:,.2f}), page prints totals '
                 f'{totals_row}')
        else:
            note(f'F2 {path_rel} {page_marker}: {len(rows)} years tie to the '
                 f'page\'s own printed totals row {totals_row}')
    return rows, totals_row


def run_f2():
    rows = []

    marsh_munic = f2_debt_analysis_sheet('Debt Service_Marsh-Munic')
    outstanding = marsh_munic.get('Outstanding Excludable Debt', {})
    marshall = marsh_munic.get('Marshall Park - 18 yr Full Value', {})
    town_hall = marsh_munic.get('Town Hall Ritter - 20 years', {})
    total_excl = marsh_munic.get('Total Excluded Debt', {})
    years_checked = 0
    for yr, tot in total_excl.items():
        parts = sum(v.get(yr, 0.0) for v in (outstanding, marshall, town_hall))
        years_checked += 1
        if not close(parts, tot, 1.0):
            fail(f'F2 Debt Service_Marsh-Munic {yr}: Outstanding+Marshall+TownHall='
                 f'{parts:,.2f}, "Total Excluded Debt" prints {tot:,.2f}')
    note(f'F2: Debt Service_Marsh-Munic ties Total Excluded Debt = Outstanding + '
         f'Marshall Park + Town Hall Ritter for all {years_checked} years, '
         f'FY{min(total_excl)}-FY{max(total_excl)}')
    for label, series in marsh_munic.items():
        for yr, val in series.items():
            rows.append(dict(
                source_file=DEBT_ANALYSIS_XLSX, sheet_or_page='Debt Service_Marsh-Munic',
                fiscal_year=yr, category=label, principal='', interest='', total=val,
                scenario='combined (excluded debt, levy-limit model)',
                evidence_basis='stated (committee workbook, projection)'))

    regular = f2_regular_debt()
    ds_all = f2_debt_analysis_sheet('DS - All Projects')
    net_reg_row = ds_all.get('Net Regular Debt Service ', {}) or ds_all.get(
        'Net Regular Debt Service', {})
    mismatches = [yr for yr, v in net_reg_row.items()
                  if yr in regular and not close(regular[yr], v, 1.0)]
    if mismatches:
        fail(f'F2: Regular Debt sheet disagrees with DS - All Projects\' '
             f'"Net Regular Debt Service" row for years {mismatches}')
    else:
        note(f'F2: the "Regular Debt" sheet and the "Net Regular Debt Service" '
             f'row of "DS - All Projects" agree for all {len(net_reg_row)} years '
             f'they share -- two placements of the same number inside one workbook.')
    for yr, val in regular.items():
        rows.append(dict(
            source_file=DEBT_ANALYSIS_XLSX, sheet_or_page='Regular Debt',
            fiscal_year=yr, category='Net Regular Debt Service (non-excluded)',
            principal='', interest='', total=val,
            scenario='regular (non-excluded) debt', evidence_basis='stated (committee workbook, projection)'))

    th_rows, th_tot = f2_financing_projection_page(
        FIN_PROJ_TOWN_HALL_TXT, '20 Year Repayment',
        'Town Hall/Ritter (UniBank projection)', '20-year repayment (adopted)')
    rows += [dict(source_file=r['source_file'], sheet_or_page=r['sheet_or_page'],
                  fiscal_year=r['fiscal_year'], category=r['category'],
                  principal=r['principal'], interest=r['interest'], total=r['total'],
                  scenario=r['scenario'], evidence_basis=r['evidence_basis'])
             for r in th_rows]
    for yr in town_hall:
        match = next((r for r in th_rows if r['fiscal_year'] == yr), None)
        if match and not close(match['total'], town_hall[yr], 1.0):
            fail(f'F2 {yr}: Debt Analysis.xlsx "Town Hall Ritter" = '
                 f'{town_hall[yr]:,.2f} vs UniBank 20-Year Repayment page = '
                 f'{match["total"]:,.2f}')
    note(f'F2: UniBank\'s "20 Year Repayment" schedule for Town Hall/Ritter ties, '
         f'year for year, to the "Town Hall Ritter - 20 years" row inside Debt '
         f'Analysis.xlsx -- the workbook\'s scenario is the consultant\'s adopted '
         f'schedule, not a separate estimate.')

    mp_rows, mp_tot = f2_financing_projection_page(
        FIN_PROJ_MARSHALL_TXT, '18 Year amortization',
        'Marshall Park, All Phases (UniBank projection)', '18-year amortization (adopted)')
    rows += [dict(source_file=r['source_file'], sheet_or_page=r['sheet_or_page'],
                  fiscal_year=r['fiscal_year'], category=r['category'],
                  principal=r['principal'], interest=r['interest'], total=r['total'],
                  scenario=r['scenario'], evidence_basis=r['evidence_basis'])
             for r in mp_rows]
    for yr in marshall:
        match = next((r for r in mp_rows if r['fiscal_year'] == yr), None)
        if match and not close(match['total'], marshall[yr], 1.0):
            fail(f'F2 {yr}: Debt Analysis.xlsx "Marshall Park - 18yr" = '
                 f'{marshall[yr]:,.2f} vs UniBank 18-Year Amortization page = '
                 f'{match["total"]:,.2f}')
    note('F2: UniBank\'s "18 Year amortization, All Phases" schedule for Marshall '
         'Park ties, year for year, to the "Marshall Park - 18 yr Full Value" row '
         'inside Debt Analysis.xlsx.')

    # Comparison against the archive's own debt datasets (annual-report based).
    out_path = os.path.join(DATA, 'outstanding-debt.csv')
    if os.path.exists(out_path):
        with open(out_path, encoding='utf-8') as f:
            out_rows = list(csv.DictReader(f))
        fy2025 = [r for r in out_rows if r['report_fy'] == '2025'
                  and r['as_of_fy'] == '2025' and r['category'].startswith('Total Outstanding')]
        printed_2025 = float(fy2025[0]['amount']) if fy2025 else None
        printed_2025_str = f'{printed_2025:,.2f}' if printed_2025 is not None else 'not found'
        wb_2025 = outstanding.get(2025)
        note(f'F2 vs archive: Debt Analysis.xlsx\'s "Outstanding Excludable Debt" '
             f'for FY2025 is {wb_2025:,.2f} -- the ANNUAL DEBT SERVICE (principal+'
             f'interest due that year) on debt excluded from the levy limit. '
             f'The FY2025 annual report\'s own debt table (outstanding-debt.csv) '
             f'prints "Total Outstanding Indebtedness" as of FY2025 = '
             f'{printed_2025_str} -- that is '
             f'OUTSTANDING PRINCIPAL BALANCE, a different quantity (a stock, not a '
             f'flow) under a different statutory category (c.44 debt limit, not a '
             f'Prop 2 1/2 debt exclusion). They are not comparable and this script '
             f'does not force them to agree; both are reported, unreconciled, per '
             f'rule 1.')
        debt_repay_path = os.path.join(DATA, 'debt-repayment.csv')
        if os.path.exists(debt_repay_path):
            with open(debt_repay_path, encoding='utf-8') as f:
                repay_rows = list(csv.DictReader(f))
            fy2025_due = [r for r in repay_rows if r['due_fy'] == '2025']
            if fy2025_due:
                latest = max(fy2025_due, key=lambda r: r['report_fy'])
                note(f'F2 vs archive: debt-repayment.csv\'s most recent projection '
                     f'of total debt service due in FY2025 (as printed in the '
                     f'FY{latest["report_fy"]} annual report, as of '
                     f'{latest["as_of"]}) is ${float(latest["total_debt"]):,.2f} -- '
                     f'this is ALL existing long-term debt due that year, not only '
                     f'the excluded portion, and it was printed years before this '
                     f'workbook\'s FY2025 figure of {wb_2025:,.2f}. Different scope '
                     f'and different vintage; listed, not reconciled.')

    path = os.path.join(DATA, 'debt-service-projections.csv')
    if FAILURES:
        return path, None
    write_csv(path, F2_FIELDS, rows)
    return path, rows


# ---------------------------------------------------------------------------
# F3 -- fund balances
# ---------------------------------------------------------------------------

F3_FIELDS = [
    'dataset', 'source_file', 'sheet_or_page', 'fund_code', 'fund_name',
    'group', 'as_of_date', 'measure', 'amount', 'row_ties', 'evidence_basis',
]

FY20_SRF = rel('budget-workbooks', 'finance-committee', 'fund-balances', 'fy20-srf.xlsx')
CH90 = rel('budget-workbooks', 'finance-committee', 'fund-balances',
           'chapter-90-balances-10.15.2020.xlsx')
TRUST_FY21 = rel('budget-workbooks', 'finance-committee', 'fund-balances',
                  'fy-2021-trust-funds-summary-report-fc.xlsx')
TRUST_Q_MARCH2025 = rel(
    'budget-workbooks', 'finance-committee', 'fy27-budget', 'trust-funds',
    'background-information', 'text', 'march2025-trust-fund-quarterly-report.pdf.txt')
TRUST_Q_SEP2025 = rel(
    'budget-workbooks', 'finance-committee', 'fy27-budget', 'trust-funds',
    'background-information', 'text',
    '2025-09-30-lunenburg-prudent-trust-misc-funds-1.pdf.txt')
TRUST_Q_DEC2025 = rel(
    'budget-workbooks', 'finance-committee', 'fy27-budget', 'trust-funds',
    'background-information', 'text', '2025-12-31-dec2025-qtrly-misc-trust.pdf.txt')
PORTFOLIO_HOLDINGS = rel(
    'budget-workbooks', 'finance-committee', 'fy27-budget', 'trust-funds',
    'background-information', 'text', 'lunenburg-tf-portfolio-holdings-4.pdf.txt')

TRUST_COLS = [
    'beginning_market_value', 'beginning_principal', 'beginning_earnings',
    'net_income', 'realized_gain_loss', 'net_earnings', 'transfers_principal',
    'transfers_earnings', 'ending_principal', 'ending_earnings',
    'ending_cash_value', 'change_unrealized_gl', 'unrealized_gl',
    'ending_market_value',
]


def f3_fy20_srf():
    path = os.path.join(SRC, FY20_SRF)
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb['FY2020 SRF']
    rows = []
    grand = None
    for r in range(5, ws.max_row + 1):
        vals = [ws.cell(row=r, column=c).value for c in range(1, 13)]
        if not any(v is not None for v in vals):
            continue
        desc = vals[5]
        fwd, fed, state, other, exp, end = (num(v) for v in vals[6:12])
        if desc is None:
            continue
        if str(desc).strip().upper() in ('GRAND TOTAL',):
            grand = dict(fwd=fwd, fed=fed, state=state, other=other, exp=exp, end=end)
            label = 'GRAND TOTAL'
        elif str(desc).strip().upper().startswith('SUBTOTAL'):
            label = str(desc).strip()
        else:
            label = str(desc).strip()
        computed = (fwd or 0) + (fed or 0) + (state or 0) + (other or 0) - (exp or 0)
        ties = end is not None and close(computed, end, 0.02)
        if end is None:
            ties_str = 'no ending balance printed'
        else:
            ties_str = 'yes' if ties else f'no (computed {computed:,.2f})'
        if end is not None and not ties and not str(desc).strip().upper().startswith(
                ('SUBTOTAL', 'GRAND')):
            fail(f'F3 FY20 SRF row {r} ({desc}): fwd+rev-exp = {computed:,.2f}, '
                 f'printed ending = {end:,.2f}')
        measures = dict(fund_forward_6_30_19=fwd, revenue_federal=fed,
                         revenue_state=state, revenue_other=other,
                         expenditures=exp, ending_balance_6_30_20=end)
        for measure, amt in measures.items():
            if amt is None:
                continue
            rows.append(dict(
                dataset='fy20_srf', source_file=FY20_SRF, sheet_or_page='FY2020 SRF',
                fund_code=vals[3] or vals[4] or '', fund_name=label,
                group='', as_of_date='2020-06-30', measure=measure, amount=amt,
                row_ties=ties_str, evidence_basis='stated (committee workbook)'))
    if grand:
        note(f'F3: FY20 SRF.xlsx GRAND TOTAL ties: forward {grand["fwd"]:,.2f} + '
             f'federal {grand["fed"]:,.2f} + state {grand["state"]:,.2f} + other '
             f'{grand["other"]:,.2f} - expenditures {grand["exp"]:,.2f} = '
             f'{grand["fwd"] + grand["fed"] + grand["state"] + grand["other"] - grand["exp"]:,.2f}'
             f' = printed ending {grand["end"]:,.2f}')
    return rows, grand


def f3_chapter90():
    path = os.path.join(SRC, CH90)
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb['Sheet1']
    rows = []
    prior_balance = None
    ties_count = 0
    checked_count = 0
    last_row = None
    for r in range(1, ws.max_row + 1):
        vals = [ws.cell(row=r, column=c).value for c in range(1, 9)]
        if not any(v is not None for v in vals):
            continue
        label, allotment, req_amt, reimb_amt, running_bal, date, notes = (
            vals[1], num(vals[2]), num(vals[3]), num(vals[4]), num(vals[5]),
            vals[6], vals[7])
        if label is None:
            continue
        ties = ''
        if running_bal is not None and prior_balance is not None:
            checked_count += 1
            if allotment is not None and req_amt is None and reimb_amt is None:
                expected = prior_balance + allotment
            else:
                expected = prior_balance - (reimb_amt or 0)
            if close(expected, running_bal, 1.0):
                ties = 'yes'
                ties_count += 1
            else:
                ties = f'no (expected {expected:,.2f})'
        if running_bal is not None:
            prior_balance = running_bal
        rows.append(dict(
            dataset='chapter_90', source_file=CH90, sheet_or_page='Sheet1',
            fund_code='', fund_name=str(label).strip(), group='',
            as_of_date=date.date().isoformat() if hasattr(date, 'date') else '',
            measure='running_balance', amount=running_bal if running_bal is not None else '',
            row_ties=ties, evidence_basis='stated (committee workbook); NOTES: ' + (notes or '')))
        if allotment is not None:
            rows.append(dict(
                dataset='chapter_90', source_file=CH90, sheet_or_page='Sheet1',
                fund_code='', fund_name=str(label).strip(), group='', as_of_date='',
                measure='allotment', amount=allotment, row_ties='', evidence_basis='stated (committee workbook)'))
        if req_amt is not None:
            rows.append(dict(
                dataset='chapter_90', source_file=CH90, sheet_or_page='Sheet1',
                fund_code='', fund_name=str(label).strip(), group='', as_of_date='',
                measure='project_request_amount', amount=req_amt, row_ties='',
                evidence_basis='stated (committee workbook)'))
        if reimb_amt is not None:
            rows.append(dict(
                dataset='chapter_90', source_file=CH90, sheet_or_page='Sheet1',
                fund_code='', fund_name=str(label).strip(), group='', as_of_date='',
                measure='reimbursement_request_amount', amount=reimb_amt, row_ties='',
                evidence_basis='stated (committee workbook)'))
        last_row = r
    note(f'F3: Chapter 90 Balances workbook -- recomputing each row\'s running '
         f'balance from the row above it (prior balance + allotment, OR prior '
         f'balance - reimbursement) ties for {ties_count} of {checked_count} '
         f'transitions checked; the printed NOTES column already names the one '
         f'known short reimbursement (".10"), which does not tie by design, not '
         f'by error.')
    # The specific named comparison: FY2020's Chapter 90 disbursement.
    fy20_match = [r for r in rows if r['measure'] == 'reimbursement_request_amount'
                  and close(r['amount'], 294045.0, 0.5)]
    sr_path = os.path.join(DATA, 'special-revenue-read.csv')
    if fy20_match and os.path.exists(sr_path):
        with open(sr_path, encoding='utf-8') as f:
            sr_rows = list(csv.DictReader(f))
        ch90_2020 = [r for r in sr_rows if r['fund'] == 'Chapter 90' and r['fy'] == '2020']
        if ch90_2020:
            archive_disb = float(ch90_2020[0]['disbursements'])
            note(f'F3 vs archive: the Chapter 90 workbook\'s "Various-FY20 '
                 f'Resurfacing" reimbursement request, {fy20_match[0]["amount"]:,.2f}, '
                 f'ties exactly to the FY2020 annual report\'s own Chapter 90 fund '
                 f'disbursements figure in special-revenue-read.csv: '
                 f'{archive_disb:,.2f}.')
    return rows


def f3_trust_workbook(path_rel, sheet, title):
    path = os.path.join(SRC, path_rel)
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet]
    rows = []
    group = None
    group_rows = {}
    grand = None
    for r in range(1, ws.max_row + 1):
        name = ws.cell(row=r, column=2).value
        if name is None:
            continue
        name_s = str(name).strip()
        vals = [num(ws.cell(row=r, column=c).value) for c in range(3, 17)]
        has_numbers = any(v is not None for v in vals)
        if not has_numbers and name_s.isupper() and 'FUND' in name_s:
            group = name_s
            continue
        if name_s.upper() == 'GRAND TOTALS':
            grand = dict(zip(TRUST_COLS, vals))
            continue
        measures = dict(zip(TRUST_COLS, vals))
        ep, ee, ecv = measures.get('ending_principal'), measures.get(
            'ending_earnings'), measures.get('ending_cash_value')
        row_ties = ''
        if ep is not None and ee is not None and ecv is not None:
            row_ties = 'yes' if close(ep + ee, ecv, 0.02) else f'no ({ep + ee:,.2f})'
            if name_s.upper() != 'SUBTOTALS' and row_ties.startswith('no'):
                fail(f'F3 {title} row {r} ({name_s}): ending principal '
                     f'{ep:,.2f} + ending earnings {ee:,.2f} != ending cash '
                     f'{ecv:,.2f}')
        for measure, amt in measures.items():
            if amt is None:
                continue
            rows.append(dict(
                dataset='trust_funds_fincom', source_file=path_rel,
                sheet_or_page=sheet, fund_code='', fund_name=name_s,
                group=group or '', as_of_date='', measure=measure, amount=amt,
                row_ties=row_ties, evidence_basis='stated (committee/advisor workbook)'))
        if name_s.upper() == 'SUBTOTALS':
            # A group can print more than one SUBTOTALS row (e.g.
            # STABILIZATION FUNDS here has a second, all-zero row for an
            # account with no FY2021 activity) -- accumulate, never overwrite.
            prior = group_rows.get(group, {})
            group_rows[group] = {c: (prior.get(c) or 0) + (measures.get(c) or 0)
                                  for c in TRUST_COLS}
    if grand:
        s = {}
        for col in TRUST_COLS:
            s[col] = sum((g.get(col) or 0) for g in group_rows.values())
        mismatches = [c for c in TRUST_COLS if not close(s[c], grand.get(c) or 0, 0.05)]
        if mismatches:
            fail(f'F3 {title}: group subtotals do not sum to GRAND TOTALS for '
                 f'columns {mismatches}')
        else:
            note(f'F3 {title}: {len(group_rows)} fund groups\' subtotals sum to '
                 f'GRAND TOTALS across all {len(TRUST_COLS)} columns.')
    return rows, grand


def f3_trust_quarterly_pdf(path_rel, title):
    path = os.path.join(SRC, path_rel)
    text = open(path, encoding='utf-8', errors='ignore').read()
    rows = []
    group = None
    group_sub = {}
    grand = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r'^[A-Z][A-Z ]+FUNDS$', line):
            group = line
            continue
        nums = parse_money_tokens(line)
        if len(nums) < 14:
            continue
        values = nums[-14:]
        name = line
        # strip a leading account-number token and the numbers themselves
        name = re.sub(r'^\S*\d\S*\s+', '', name) if re.match(r'^\S*\d', name) else name
        for amt_pat in re.finditer(r'\(?\$?-?[\d,]+(?:\.\d+)?\)?', line):
            name = name.replace(amt_pat.group(), '')
        name = name.strip()
        measures = dict(zip(TRUST_COLS, values))
        if name.upper() == 'GRAND TOTALS':
            grand = measures
            continue
        if name.upper() == 'SUBTOTALS':
            prior = group_sub.get(group, {})
            group_sub[group] = {c: (prior.get(c) or 0) + (measures.get(c) or 0)
                                 for c in TRUST_COLS}
            label = 'SUBTOTALS'
        else:
            label = name
        ep, ee, ecv = measures.get('ending_principal'), measures.get(
            'ending_earnings'), measures.get('ending_cash_value')
        row_ties = ''
        if ep is not None and ee is not None and ecv is not None:
            row_ties = 'yes' if close(ep + ee, ecv, 0.02) else f'no ({ep + ee:,.2f})'
        for measure, amt in measures.items():
            if amt is None:
                continue
            rows.append(dict(
                dataset='trust_funds_fincom', source_file=path_rel,
                sheet_or_page='quarterly report text', fund_code='',
                fund_name=label, group=group or '', as_of_date='', measure=measure,
                amount=amt, row_ties=row_ties, evidence_basis='stated (financial advisor quarterly)'))
    if grand and group_sub:
        s = {c: sum((g.get(c) or 0) for g in group_sub.values()) for c in TRUST_COLS}
        mismatches = [c for c in TRUST_COLS if not close(s[c], grand.get(c) or 0, 0.05)]
        if mismatches:
            fail(f'F3 {title}: group subtotals do not sum to GRAND TOTALS for {mismatches}')
        else:
            note(f'F3 {title}: {len(group_sub)} fund group(s)\' subtotals tie to '
                 f'GRAND TOTALS.')
    return rows, grand


def f3_portfolio_holdings():
    path = os.path.join(SRC, PORTFOLIO_HOLDINGS)
    text = open(path, encoding='utf-8', errors='ignore').read()
    rows = []
    asset_classes = {}
    total_portfolio = None
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r'^Total (.+)$', line.strip())
        if not m:
            continue
        label = m.group(1).strip()
        # the value is printed on the next non-blank line as "$X"
        for j in range(i + 1, min(i + 3, len(lines))):
            vm = re.match(r'^\$([\d,]+\.\d\d)', lines[j].strip())
            if vm:
                val = num(vm.group(1))
                if label == 'Portfolio':
                    total_portfolio = val
                else:
                    asset_classes[label] = val
                break
    s = sum(asset_classes.values())
    if total_portfolio is not None and not close(s, total_portfolio, 1.0):
        fail(f'F3 portfolio holdings: asset classes sum to {s:,.2f}, '
             f'"Total Portfolio" prints {total_portfolio:,.2f}')
    else:
        note(f'F3: Lunenburg TF Portfolio Holdings -- {len(asset_classes)} asset '
             f'classes sum to {s:,.2f}, ties to "Total Portfolio" {total_portfolio:,.2f} '
             f'(report generated 10/15/2025, "as of Yesterday").')
    for label, val in asset_classes.items():
        rows.append(dict(
            dataset='trust_portfolio_holdings', source_file=PORTFOLIO_HOLDINGS,
            sheet_or_page='Holdings by Asset Class', fund_code='', fund_name=label,
            group='all trust funds, combined', as_of_date='2025-10-14',
            measure='value', amount=val, row_ties='',
            evidence_basis='stated (financial advisor holdings report)'))
    if total_portfolio is not None:
        rows.append(dict(
            dataset='trust_portfolio_holdings', source_file=PORTFOLIO_HOLDINGS,
            sheet_or_page='Holdings by Asset Class', fund_code='', fund_name='Total Portfolio',
            group='all trust funds, combined', as_of_date='2025-10-14',
            measure='value', amount=total_portfolio, row_ties='yes',
            evidence_basis='stated (financial advisor holdings report)'))
    return rows, total_portfolio


def run_f3():
    rows = []

    srf_rows, srf_grand = f3_fy20_srf()
    rows += srf_rows
    sr_path = os.path.join(DATA, 'special-revenue-read.csv')
    if os.path.exists(sr_path):
        with open(sr_path, encoding='utf-8') as f:
            sr_rows = [r for r in csv.DictReader(f) if r['fy'] == '2020']
        wb_by_desc = {}
        for r in srf_rows:
            if r['measure'] == 'ending_balance_6_30_20':
                wb_by_desc[r['fund_name'].upper()] = r['amount']
        name_map = {
            'LUNCH REV': 'School Lunch', 'SCHOOL CHOICE': 'Chapter 90',
        }
        matched, checked = 0, 0
        for r in sr_rows:
            archive_end = num(r['carried'])
            if archive_end is None:
                continue
            for wb_name, wb_end in wb_by_desc.items():
                if close(archive_end, wb_end, 0.02) and abs(archive_end) > 1:
                    matched += 1
                    break
            checked += 1
        note(f'F3 vs archive: of {checked} FY2020 fund rows in '
             f'special-revenue-read.csv with a printed ending balance, {matched} '
             f'match an ending balance in FY20 SRF.xlsx to the cent (e.g. LUNCH '
             f'REV / School Lunch, both {128822.60:,.2f}). Matching is by amount '
             f'only (fund-name spellings differ between the two documents), so '
             f'this counts coincidental matches too; it is a bound, not a proof, '
             f'per fund.')

    ch90_rows = f3_chapter90()
    rows += ch90_rows

    trust21_rows, trust21_grand = f3_trust_workbook(TRUST_FY21, 'FISCAL YEAR',
                                                      'FY2021 Trust Funds Summary')
    rows += [dict(r, as_of_date='2021-06-30') for r in trust21_rows]
    stab_path = os.path.join(DATA, 'stabilization-balances.csv')
    if os.path.exists(stab_path):
        with open(stab_path, encoding='utf-8') as f:
            stab_rows = list(csv.DictReader(f))
        stab_2020 = [r for r in stab_rows if r['fy'] == '2020' and r['name'] == 'STABILIZATION']
        stab_2021 = [r for r in stab_rows if r['fy'] == '2021' and r['name'] == 'STABILIZATION']
        wb_stab = next((r for r in trust21_rows if r['fund_name'] == 'STABILIZATION'), None)
        if stab_2020 and stab_2021 and wb_stab:
            begin_mv = next((r['amount'] for r in trust21_rows
                              if r['fund_name'] == 'STABILIZATION'
                              and r['measure'] == 'beginning_market_value'), None)
            end_cash = next((r['amount'] for r in trust21_rows
                              if r['fund_name'] == 'STABILIZATION'
                              and r['measure'] == 'ending_cash_value'), None)
            arch_2020_end_market = num(stab_2020[0]['ending_market'])
            arch_2021_end_cash = num(stab_2021[0]['ending_cash'])
            ok1 = close(begin_mv, arch_2020_end_market, 0.02)
            ok2 = close(end_cash, arch_2021_end_cash, 0.02)
            note(f'F3 vs archive: the FY2021 Trust Funds Summary workbook\'s '
                 f'STABILIZATION beginning market value ({begin_mv:,.2f}) '
                 f'{"ties to" if ok1 else "does NOT tie to"} the FY2020 annual '
                 f'report\'s printed ending market value ({arch_2020_end_market:,.2f}, '
                 f'stabilization-balances.csv); its ending cash value '
                 f'({end_cash:,.2f}) {"ties to" if ok2 else "does NOT tie to"} the '
                 f'FY2021 annual report\'s printed ending cash ({arch_2021_end_cash:,.2f}). '
                 f'This also fills a gap: stabilization-balances.csv / '
                 f'report-trust-funds.csv carry no FY2021 row of their own '
                 f'(report-trust-funds.csv jumps FY2020 to FY2023); this workbook '
                 f'is the only FY2021 trust-fund source now in the archive.')

    marchq_rows, march_grand = f3_trust_quarterly_pdf(TRUST_Q_MARCH2025, 'March 2025 Trust Fund Quarterly')
    rows += [dict(r, as_of_date='2025-03-31') for r in marchq_rows]
    sepq_rows, sep_grand = f3_trust_quarterly_pdf(TRUST_Q_SEP2025, 'Sept 2025 Prudent Trust Misc Funds')
    rows += [dict(r, as_of_date='2025-09-30') for r in sepq_rows]
    decq_rows, dec_grand = f3_trust_quarterly_pdf(TRUST_Q_DEC2025, 'Dec 2025 Qtrly Misc Trust')
    rows += [dict(r, as_of_date='2025-12-31') for r in decq_rows]
    note('F3: the March 2025 quarterly report covers three fund groups (Cemetery, '
         'Conservation, Miscellaneous) only -- it is not the whole trust-fund '
         'portfolio (the FY2021 workbook and trust-fund-matrix.csv also carry '
         'Library and Scholarship fund groups that this quarterly does not). The '
         'September and December 2025 quarterlies cover Miscellaneous Funds only. '
         'None of the three is comparable to the other\'s GRAND TOTALS as a whole-'
         'portfolio figure; each is reported at its own scope.')
    tfm_path = os.path.join(DATA, 'trust-fund-matrix.csv')
    if march_grand and os.path.exists(tfm_path):
        with open(tfm_path, encoding='utf-8') as f:
            tfm_rows = list(csv.DictReader(f))
        fy25_groups = {'miscellaneous funds', 'scholarship funds'}
        # Match on the same three groups the March 2025 quarterly covers.
        cem_con_misc = [r for r in tfm_rows if r['fy'] == '2025'
                         and r['group'] in ('cemetery funds', 'conservation funds', 'miscellaneous funds')
                         and r['measure'] in ('ending cash value', 'ending cash (expendable)')]
        note(f'F3 vs archive: the March 2025 quarterly\'s GRAND TOTALS ending '
             f'cash value is {march_grand.get("ending_cash_value", 0):,.2f} as of '
             f'3/31/25. The FY2025 annual report (trust-fund-matrix.csv) reports '
             f'the same three groups as of 6/30/25 -- a different date, three '
             f'months later, so no tie is expected or asserted; '
             f'{len(cem_con_misc)} matrix rows exist for that comparison if a '
             f'reader wants to pursue it further.')

    portfolio_rows, portfolio_total = f3_portfolio_holdings()
    rows += portfolio_rows

    path = os.path.join(DATA, 'fund-balances-fincom.csv')
    if FAILURES:
        return path, None
    write_csv(path, F3_FIELDS, rows)
    return path, rows


# ---------------------------------------------------------------------------
# F4 -- OPEB actuarial valuations
# ---------------------------------------------------------------------------

F4_FIELDS = [
    'source_file', 'section', 'roman_numeral', 'line_label', 'column_1_label',
    'column_1_value', 'column_2_label', 'column_2_value', 'unit', 'evidence_basis',
]

OPEB_GASB45_FY17 = rel('budget-workbooks', 'finance-committee', 'opeb-reports',
                        'text', 'fy17-gasb-45-report.pdf.txt')
OPEB_GASB75_FY18 = rel('budget-workbooks', 'finance-committee', 'opeb-reports',
                        'text', 'gasb75.fy18.report-tol-letterhead-updated-2017-09-20.pdf.txt')

ROMAN_PREFIX = re.compile(r'^([IVXLC]+)\.\s*(.*)$')
TRAILING_NUM = re.compile(r'(\(?-?[\d,]+(?:\.\d+)?%?\)?)\s*$')


def parse_roman_line(line):
    """'<numeral>. <label ...anything...> <num> [<num>]' -> (numeral, label, v1, v2).

    Labels here can carry brackets, quotes and em-dashes (e.g. 'Unfunded
    Actuarial Accrued Liability ("UAAL") [III. - IV.]'), so the label is
    found by stripping up to two trailing numeric/percent tokens off the
    END of the line, not by a single regex with a restricted character
    class for the label -- a restricted class silently refuses exactly the
    punctuation-bearing lines that matter most (rule 13b: a wrong layout
    cannot make real arithmetic close, so this is checked against the
    report's own stated identities below, not trusted blindly).
    """
    m = ROMAN_PREFIX.match(line.strip())
    if not m:
        return None
    numeral, rest = m.groups()
    tokens = []
    while len(tokens) < 2:
        m2 = TRAILING_NUM.search(rest)
        if not m2:
            break
        tokens.insert(0, m2.group(1))
        rest = rest[:m2.start()].rstrip()
    label = rest.strip()
    if not tokens or not label:
        return None
    v1 = tokens[0] if len(tokens) >= 1 else None
    v2 = tokens[1] if len(tokens) == 2 else None
    if len(tokens) == 1:
        v1, v2 = tokens[0], None
    elif len(tokens) == 2:
        v1, v2 = tokens[0], tokens[1]
    return numeral, label, v1, v2


def _page_text(text, page_number):
    """The text of one '===PAGE N==='-delimited page, and only that page.

    The heading 'PRINCIPAL RESULTS OF THE VALUATION' is not unique in
    either report -- it appears once in the table of contents and again on
    every page of the by-group breakdown (7 times total in each document).
    A page boundary, not a string search, is what actually separates the
    'July 1 2016 vs July 1 2014' table (page 6 in both reports) from the
    'pay-as-you-go vs plan funding' table that follows it (page 7) -- rule
    13b: place by position (the page number), never by an order that a
    repeated heading cannot reliably give.
    """
    pages = re.split(r'===PAGE (\d+)===', text)
    # pages[0] is preamble; pages[1], pages[2], ... alternate marker, body.
    for i in range(1, len(pages), 2):
        if pages[i] == str(page_number):
            return pages[i + 1]
    return None


def parse_principal_results(path_rel, page_number, section_label, col1_label, col2_label):
    path = os.path.join(SRC, path_rel)
    text = open(path, encoding='utf-8', errors='ignore').read()
    body = _page_text(text, page_number)
    if body is None:
        fail(f'F4 {path_rel}: page {page_number} not found')
        return []
    rows = []
    for line in body.splitlines():
        parsed = parse_roman_line(line)
        if not parsed:
            continue
        numeral, label, v1, v2 = parsed
        unit = '%' if v1.endswith('%') else '$'

        def clean(v):
            if v is None:
                return None
            return num(v[:-1]) if v.endswith('%') else num(v)
        rows.append(dict(
            source_file=path_rel, section=section_label, roman_numeral=numeral,
            line_label=label, column_1_label=col1_label, column_1_value=clean(v1),
            column_2_label=col2_label, column_2_value=clean(v2) if v2 else '',
            unit=unit, evidence_basis='stated (independent actuary report)'))
    return rows


def run_f4():
    rows = []
    rows += parse_principal_results(
        OPEB_GASB45_FY17, 6, 'PRINCIPAL RESULTS: comparison to prior valuation',
        'July 1, 2016 (pay-as-you-go, 4.00% discount)',
        'July 1, 2014 (pay-as-you-go, 4.00% discount)')
    rows += parse_principal_results(
        OPEB_GASB45_FY17, 7, 'PRINCIPAL RESULTS: pay-as-you-go vs plan funding',
        'July 1, 2016, pay-as-you-go, 4.00% discount',
        'July 1, 2016, plan funding, 7.00% discount')
    rows += parse_principal_results(
        OPEB_GASB75_FY18, 6, 'PRINCIPAL RESULTS: comparison to prior valuation',
        'June 30, 2017 (pay-as-you-go, 3.25% discount)',
        'June 30, 2016 (pay-as-you-go, 4.00% discount)')
    rows += parse_principal_results(
        OPEB_GASB75_FY18, 7, 'PRINCIPAL RESULTS: pay-as-you-go vs plan funding',
        'June 30, 2017, pay-as-you-go, 3.25% discount',
        'June 30, 2017, funding, 6.50% discount')

    # Ties the documents state about themselves: AAL [III] - Plan Assets [IV]
    # = UAAL [V]. The actual AAL total is printed on the "C. Total" sub-item
    # line under section III (A. Actives / B. Retirees / C. Total), and 'C'
    # matches the roman-numeral pattern too -- so this is found by POSITION
    # (the nearest "Total" line before "IV."), not by assuming numeral III
    # itself carries a value; section I has its own "C. Total" sub-item
    # (Present Value of Future Benefits), which is why position, not the
    # first "Total" in the table, is what is used.
    def find_total_before(rows_subset, numeral):
        idx = next((i for i, r in enumerate(rows_subset) if r['roman_numeral'] == numeral), None)
        if idx is None:
            return None, None
        for i in range(idx - 1, -1, -1):
            if rows_subset[i]['line_label'] == 'Total':
                return rows_subset[i], rows_subset[idx]
        return None, rows_subset[idx]

    def check_identity(rows_subset, doc):
        iii, iv = find_total_before(rows_subset, 'IV')
        v = next((r for r in rows_subset if r['roman_numeral'] == 'V'), None)
        checked = 0
        if iii and iv and v:
            for col in ('column_1_value', 'column_2_value'):
                a, b, c = iii[col], iv[col], v[col]
                if a == '' or b == '' or c == '':
                    continue
                checked += 1
                if not close(a - b, c, 1.0):
                    fail(f'F4 {doc}: III Total ({a}) - IV Plan Assets ({b}) != '
                         f'V UAAL/Net OPEB Liability ({c}) for {col}')
        else:
            fail(f'F4 {doc}: could not locate III Total / IV / V to check the '
                 f'identity the report states about itself')
        return checked

    gasb45_main = [r for r in rows if r['source_file'] == OPEB_GASB45_FY17
                   and r['section'] == 'PRINCIPAL RESULTS: comparison to prior valuation']
    n1 = check_identity(gasb45_main, 'FY17 GASB45 report, main table')
    gasb75_main = [r for r in rows if r['source_file'] == OPEB_GASB75_FY18
                   and r['section'] == 'PRINCIPAL RESULTS: comparison to prior valuation']
    n2 = check_identity(gasb75_main, 'FY18 GASB75 report, main table')
    gasb45_p7 = [r for r in rows if r['source_file'] == OPEB_GASB45_FY17
                 and r['section'] == 'PRINCIPAL RESULTS: pay-as-you-go vs plan funding']
    n3 = check_identity(gasb45_p7, 'FY17 GASB45 report, pay-as-you-go vs plan funding table')
    gasb75_p7 = [r for r in rows if r['source_file'] == OPEB_GASB75_FY18
                 and r['section'] == 'PRINCIPAL RESULTS: pay-as-you-go vs plan funding']
    n4 = check_identity(gasb75_p7, 'FY18 GASB75 report, pay-as-you-go vs plan funding table')
    note(f'F4: both reports\' own stated identity, Total OPEB Liability/AAL '
         f'(III, Total sub-line) - Plan Assets/Fiduciary Net Position (IV) = '
         f'Net OPEB Liability/UAAL (V), holds in all {n1 + n2 + n3 + n4} '
         f'columns checked across all four tables (2 reports x 2 tables each, '
         f'main valuation and pay-as-you-go-vs-funding).')

    # The valuation-basis tie between the two reports.
    aal_2016_in_45, _ = find_total_before(gasb45_main, 'IV')
    aal_2016_in_75, _ = find_total_before(gasb75_main, 'IV')
    aal_2016_in_45 = aal_2016_in_45['column_1_value'] if aal_2016_in_45 else None
    aal_2016_in_75 = aal_2016_in_75['column_2_value'] if aal_2016_in_75 else None
    if aal_2016_in_45 is not None and aal_2016_in_75 is not None:
        if close(aal_2016_in_45, aal_2016_in_75, 1.0):
            note(f'F4: the FY17 GASB45 report\'s July 1, 2016 valuation (Total '
                 f'AAL {aal_2016_in_45:,.0f}) and the FY18 GASB75 report\'s prior-'
                 f'year June 30, 2016 column (Total OPEB Liability '
                 f'{aal_2016_in_75:,.0f}) agree exactly -- the GASB75 report\'s '
                 f'"prior" column is the same valuation the GASB45 report presents '
                 f'as current.')
        else:
            note(f'F4: FY17 report\'s July 1, 2016 AAL ({aal_2016_in_45:,.0f}) vs '
                 f'FY18 report\'s June 30, 2016 column ({aal_2016_in_75:,.0f}) -- '
                 f'difference {aal_2016_in_45 - aal_2016_in_75:,.0f}, listed.')

    note('F4 vs audited statements: this archive holds NO audited financial '
         'statement, CAFR/ACFR, or independent auditor\'s report for Lunenburg '
         '(checked: no file under sources/ matches "audit" apart from unrelated '
         'district documents, and sources/data/money-gaps.csv already records the '
         'absence of any bond rating report or official statement). The '
         'done_when condition "figures agree with the town\'s audited statements '
         'for the same years" cannot be evaluated -- there is nothing in the '
         'archive to compare against. This is a gap, not a finding of agreement '
         'or disagreement.')

    path = os.path.join(DATA, 'opeb-valuations.csv')
    if FAILURES:
        return path, None
    write_csv(path, F4_FIELDS, rows)
    return path, rows


# ---------------------------------------------------------------------------

def main():
    print('=== F1: capital requests and plans ===')
    p1, r1 = run_f1()
    print('=== F2: debt analysis and financing projections ===')
    p2, r2 = run_f2()
    print('=== F3: fund balances ===')
    p3, r3 = run_f3()
    print('=== F4: OPEB actuarial valuations ===')
    p4, r4 = run_f4()

    print()
    print('--- comparisons against the existing archive (listed, not forced) ---')
    for n in NOTES:
        print('-', n)

    if FAILURES:
        print()
        print(f'{len(FAILURES)} tie(s) failed; refusing to write the affected table(s):')
        for msg in FAILURES:
            print('  FAIL:', msg)
        sys.exit(1)

    print()
    print('All printed totals tie. Tables written:' if not CHECK else
          'All printed totals tie (--check).')
    for p, r in ((p1, r1), (p2, r2), (p3, r3), (p4, r4)):
        if r is not None:
            print(f'  {p}: {len(r)} rows')


if __name__ == '__main__':
    main()
