#!/usr/bin/env python3
"""CAPITAL RANKINGS, FY2023-FY2027: every capital request, every ranking the year's documents
print for it, and whether it was funded -- one row per request per fiscal year.

    python3.11 scripts/extract_capital_rankings.py           # write sources/data/capital-rankings.csv
    python3.11 scripts/extract_capital_rankings.py --check   # fail if it would change

TJ, 20 November 2026: *"i want to see the ranking year over year"* and *"i want to clik into a FY
and see what was asked for by department, then what was prioritized, in rank order"*.

RANKING SCHEMES ARE NEVER MERGED. Each is its own column, quoted from its own page or cell:

    cpc_rank           the Capital Planning Committee's priority number
    tm_rank            the Town Manager's priority number (FY2023-FY2025; later decks print none)
    collins_score      the UMass Collins Center points the request scored
    composite_average  the average of the members' individual ranks (FY2024, FY2025, FY2027)
    dept_rank          the department's own priority (only FY2025's workbook prints it)
    member_ranks       each member's rank, as the sheet heads the columns

`funded` is what the OUTCOME document says, never a cutoff we choose, and `outcome_basis` says
which document and what kind of record it is. Where Town Meeting's vote is known only from the
recording (FY2027), the basis says so.

`department` is OUR grouping, so that a department can be followed across years whose documents
name it differently ("Town Facilities", "Facilities and Grounds", "Facilities and Parks").
It is read off the project number's prefix (FM, DPW, INFRA, LPS, PD, FD, IT, GG) where one is
printed, and off the printed department where none is (FY2026, FY2027). `department_as_printed`
keeps the document's own word. The grouping is ours and the generator says so -- and it is
CHECKED: for FY2023, FY2024, FY2025 and FY2027 it reproduces, to the dollar, every department
total the year's own document prints (`printed_department_totals`).

WHAT EACH YEAR RESTS ON
  FY2023  requests: a75 pp6-7 (30, $4,043,049 printed). Ranks: a75 p9 (the 20 in the plan: TM,
          CPC, Collins) and p30 (the 10 not included: TM/CPC "n/30"; no Collins printed).
          Funded: Article 6, May 2022 ATM, as printed in the FY2022 annual report p142, read by
          extract_capital_plans.py into capital-plans.csv (23 projects, $2,162,849).
  FY2024  requests: a195 pp7-8 (29, $2,941,010). Ranks: a195 p10 (6) and p18 (23): TM, CPC,
          Collins; a194 (one page): members' ranks and their composite. Funded: the FY2023
          annual report pp163-164, Article 6 table, a PICTURE: rows 1-8 on p163 read by eye on
          20 November 2026, rows 9-12 on p164 also in the Textract read. Twelve projects,
          printed total $2,025,010.00, of which $986,000 is ARPA money the table marks as not
          requiring a Town Meeting vote. The final table renumbers TM and CPC after two
          removals; the ranks here are a195's, the full list.
  FY2025  everything ranked: the CPC workbook, sheet Ordered (35 rows): column A composite
          order (= CPC priority on 1504), E department priority, H Collins, I amount, J-N the
          five members' ranks (headed by initials), O their average (headed `Column1`). TM ranks: 1504 p11 (10) and p22 (25), which prints
          TM 23 twice and no 31 -- kept as printed. Funded: Article 6, May 2024 ATM, FY2024
          annual report, total appropriation $1,317,119.98 = the ten on p11.
  FY2026  only what the two Option tables print: FY2025 annual report pp138-139, read by
          extract_capital_options.py into capital-program-options.csv. The CPC's full ranked
          list is not held, so the ranks missing from 1-22 are missing here too, and no
          request total exists. Funded: Option 2, voted at the May 2025 ATM (same report).
  FY2027  every request is ranked: fy27-capital-plan.xlsx, sheet FY27 Capital (22 rows, CPC
          rank, average, amount); members' ranks from the version 2 priorities list (only one
          member's column is filled). Funded: Article 13 of the May 2026 ATM warrant (booklet
          3765 p30), ranks 1-12, $1,830,203. Town Meeting's vote is held only as the recording.
"""
import argparse
import csv
import io
import os
import re
import sys
from decimal import Decimal

import openpyxl
from pypdf import PdfReader

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'sources', 'data', 'capital-rankings.csv')
S = lambda *p: os.path.join(ROOT, 'sources', *p)

A75 = 'town-budget/docs/a75-fy23-capital-plan-presentation-pdf.pdf'
A194 = 'town-budget/docs/a194-fy24-composite-project-ranking-by-capital-planning-committee-pdf.pdf'
A195 = 'town-budget/docs/a195-fy24-town-manager-capital-plan-presentation-pdf.pdf'
D1504 = 'town-budget/docs/1504-fy25-fy34-town-manager-preliminary-capital-plan-presentation.pdf'
CPC25 = ('budget-workbooks/finance-committee/fy25-budget/capital-planning-committee-files/'
         'fy25-capital-requests-by-department-final-cpc.xlsx')
PLAN27 = 'budget-workbooks/finance-committee/fy27-budget/capital-planning/fy27-capital-plan.xlsx'
PRI27 = ('budget-workbooks/finance-committee/fy27-budget/capital-planning/dept-requests/'
         'fy27-capital-planning-committee-priorities-list-version-2-menard.xlsx')
PRE27 = 'budget-workbooks/finance-committee/fy27-budget/capital-planning/preliminary-capital-program-2.1.26.pdf'
W2026 = 'town-budget/docs/3765-town-meeting-booklet-including-warrant.pdf'
AR22 = 'town-annual-reports/docs/4129-fy-2022-annual-town-report.pdf'
AR23 = 'town-annual-reports/docs/4131-fy-2023-annual-town-report.pdf'
AR24 = 'town-annual-reports/docs/4132-fy-2024-annual-town-report.pdf'
AR25 = 'town-annual-reports/docs/4130-fy-2025-annual-town-report.pdf'
PRE26 = 'budget-workbooks/finance-committee/fy26-budget/preliminary-fy26-capital-program-presentation.pptx'

# FY2024's final plan, Article 6 of the May 2023 ATM: the FY2023 annual report pp163-164 is a
# picture. Read by eye on 20 November 2026 (p163, rows 1-8) and against the Textract read
# (p164, rows 9-12). The printed total is checked below against the sum of these rows' amounts
# as a195 states them, so a misread project number cannot pass.
FY24_FINAL = ['FD17-03', 'LPS23-08', 'LPS23-09', 'LPS23-10', 'DPW17-14', 'DPW23-18', 'LPS20-05',
              'FD23-01', 'INFRA21-03', 'DPW23-16', 'FM19-07A-2', 'FM23-03']
FY24_FINAL_TOTAL = Decimal('2025010.00')        # p164, both columns' TOTAL row: $2,025,010.00
FY24_ARPA = ['FD17-03', 'DPW17-14', 'DPW23-18']  # starred on p163; $986,000, no ATM vote needed

COLUMNS = ['fiscal_year', 'project_number', 'project', 'department', 'department_as_printed',
           'amount', 'cpc_rank', 'cpc_ranked_of', 'tm_rank', 'collins_score', 'composite_average',
           'dept_rank', 'member_ranks', 'tm_preliminary', 'funded', 'outcome_basis', 'rank_source',
           'outcome_source', 'notes']

PREFIX = [('INFRA', 'Public Works'), ('DPW', 'Public Works'), ('FM', 'Facilities'), ('LPS', 'Schools'),
          ('PD', 'Police'), ('FD', 'Fire'), ('IT', 'IT'), ('GG', 'General government')]
PRINTED = {'DPW': 'Public Works', 'Public Works': 'Public Works', 'Facilities': 'Facilities',
           'Schools': 'Schools', 'Police': 'Police', 'Fire': 'Fire', 'IT': 'IT'}


def fail(msg):
    raise SystemExit('extract_capital_rankings: ' + msg)


def dept_of(cip, printed):
    if cip:
        for p, d in PREFIX:
            if cip.upper().startswith(p):
                return d
        fail('no department for project number %r' % cip)
    if printed not in PRINTED:
        fail('no department for printed %r' % printed)
    return PRINTED[printed]


def key(cip):
    """One spelling per project number: `DPW 17-14` and `DPW17-14`, `LPS19-3-B` and `LPS19-03-B`."""
    k = re.sub(r'\s+', '', cip.upper())
    return re.sub(r'-0(\d)', r'-\1', k)


def money(s):
    return Decimal(re.sub(r'[$,\s]', '', s))


def num(v):
    """A figure as the CSV writes it: no trailing .00 on whole dollars."""
    d = Decimal(str(v)).quantize(Decimal('0.01'))
    return str(d.quantize(Decimal(1))) if d == d.to_integral() else str(d)


_pdf = {}


def page(doc, n):
    if doc not in _pdf:
        p = S(doc)
        if not os.path.exists(p):
            fail('missing %s -- python3.11 scripts/sync_archive.py --pull' % p)
        _pdf[doc] = PdfReader(p)
    return _pdf[doc].pages[n - 1].extract_text() or ''


def sheet(doc, name):
    p = S(doc)
    if not os.path.exists(p):
        fail('missing %s -- python3.11 scripts/sync_archive.py --pull' % p)
    return openpyxl.load_workbook(p, data_only=True)[name]


CIP = r'((?:INFRA|DPW|FM|LPS|PD|FD|IT|GG)\s?\d{2}-[0-9A-Z]+(?:-[0-9A-Z]+)*)'


def row(**k):
    r = {c: '' for c in COLUMNS}
    r.update({c: ('' if v is None else str(v)) for c, v in k.items()})
    return r


# ------------------------------------------------------------------ FY2023
def fy2023():
    req = {}
    for n in (6, 7):
        for ln in page(A75, n).splitlines():
            m = re.match(r'^' + CIP + r' (Town Facilities|Town Manager|Planning|Police|Schools|Highway) (.+?) ([\d,]+)\s*$', ln.strip())
            if m:
                req[key(m.group(1))] = (m.group(1), m.group(2), m.group(3).strip(), money(m.group(4)))
    total = re.search(r'Total Capital Requests ([\d,]+)', page(A75, 7))
    if len(req) != 30 or sum(v[3] for v in req.values()) != money(total.group(1)):
        fail('FY2023: %d requests summing %s, the deck prints 30 and %s'
             % (len(req), sum(v[3] for v in req.values()), total.group(1)))
    ranks = {}
    for ln in page(A75, 9).splitlines():
        m = re.match(r'^(\d+) (\d+) (\d+) ' + CIP + r' (DPW|Planning Board|Police|Schools|Town Manager)', ln.strip())
        if m:
            ranks[key(m.group(4))] = dict(tm=int(m.group(1)), cpc=int(m.group(2)), collins=int(m.group(3)),
                                          printed=m.group(5), src='%s p9' % A75)
    for m in re.finditer(r'(\d+)/30 (\d+)/30\s*' + CIP, page(A75, 30)):
        ranks[key(m.group(3))] = dict(tm=int(m.group(1)), cpc=int(m.group(2)), collins=None,
                                      printed=None, src='%s p30' % A75)
    if set(ranks) != set(req) or sorted(r['cpc'] for r in ranks.values()) != list(range(1, 31)) \
            or sorted(r['tm'] for r in ranks.values()) != list(range(1, 31)):
        fail('FY2023: ranked %s against requested %s' % (sorted(set(ranks) ^ set(req)), len(req)))
    # Funded: Article 6 of May 2022 as the FY2022 annual report prints it (capital-plans.csv).
    funded, total = {}, None
    for r in csv.DictReader(open(S('data', 'capital-plans.csv'), encoding='utf-8')):
        if r['edition'] == 'FY2022' and r['page'] == '142' and r['plan_fiscal_year'] == '2023':
            m = re.search(CIP, r['project'])
            funded[key(m.group(1))] = Decimal(r['cost'])
            total = Decimal(r['printed_total'])
    if len(funded) != 23 or sum(funded.values()) != total or not set(funded) <= set(req):
        fail('FY2023: the adopted plan read %d projects summing %s against %s'
             % (len(funded), sum(funded.values()), total))
    out = []
    for k, (cip, printed, title, amt) in req.items():
        rk = ranks[k]
        if k in funded and funded[k] != amt:
            fail('FY2023 %s: adopted at %s, requested at %s' % (cip, funded[k], amt))
        out.append(row(fiscal_year=2023, project_number=cip, project=title, department=dept_of(cip, None),
                       department_as_printed=printed, amount=num(amt), cpc_rank=rk['cpc'], cpc_ranked_of=30,
                       tm_rank=rk['tm'], collins_score=rk['collins'],
                       tm_preliminary='yes' if rk['collins'] is not None else 'no',
                       funded='yes' if k in funded else 'no',
                       outcome_basis="Town Meeting vote, Town Clerk's record",
                       rank_source=rk['src'], outcome_source='%s p142 (Article 6, May 2022 ATM)' % AR22,
                       notes='requests list %s pp6-7' % A75))
    return out


# ------------------------------------------------------------------ FY2024
def fy2024():
    req = {}
    dept = None
    for n in (7, 8):
        for ln in page(A195, n).splitlines():
            ln = ln.strip()
            m = re.match(r'^(Facilities and Grounds|Fire Department|Public Works|School Department) ', ln)
            if m:
                dept, ln = m.group(1), ln[len(m.group(0)):]
            m = re.match(r'^' + CIP + r' (.+?) \$([\d,]+\.\d\d)$', ln)
            if m and dept:
                req[key(m.group(1))] = (m.group(1), dept, m.group(2).strip(), money(m.group(3)))
    total = re.search(r'Total Departments \$([\d,.]+)', page(A195, 8))
    if len(req) != 29 or sum(v[3] for v in req.values()) != money(total.group(1)):
        fail('FY2024: %d requests summing %s, the deck prints 29 and %s'
             % (len(req), sum(v[3] for v in req.values()), total.group(1)))
    ranks = {}
    for n, pat in ((10, r'^(\d+) (\d+) (\d+) ' + CIP + r' '), (18, r'^(\d+) (\d+) (\d+) ' + CIP + r' ')):
        for ln in page(A195, n).splitlines():
            m = re.match(pat, ln.strip())
            if m:
                ranks[key(m.group(4))] = dict(tm=int(m.group(1)), cpc=int(m.group(2)), collins=int(m.group(3)),
                                              src='%s p%d' % (A195, n), prelim=(n == 10))
    if set(ranks) != set(req) or sorted(r['cpc'] for r in ranks.values()) != list(range(1, 30)):
        fail('FY2024: ranks and requests differ: %s' % sorted(set(ranks) ^ set(req)))
    comp = {}
    t194 = page(A194, 1)
    for m in re.finditer(r'(?:^|\n)(.+?) ' + CIP + r' \$([\d,]+\.\d\d) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) ([\d.]+)', t194):
        comp[key(m.group(2))] = dict(collins=int(m.group(4)), members=[int(m.group(i)) for i in range(5, 10)],
                                     avg=m.group(10))
    heads = re.findall(r'(\w+) \nRANKING', t194)[:5]
    if set(comp) != set(req) or len(heads) != 5:
        fail('FY2024: a194 read %d rows and %d member heads' % (len(comp), len(heads)))
    for k in req:
        if comp[k]['collins'] != ranks[k]['collins']:
            fail('FY2024 %s: Collins %s on a194, %s on a195' % (k, comp[k]['collins'], ranks[k]['collins']))
    fin = [key(c) for c in FY24_FINAL]
    if not set(fin) <= set(req) or sum(req[k][3] for k in fin) != FY24_FINAL_TOTAL:
        fail('FY2024: the final twelve sum to %s, p164 prints %s'
             % (sum(req[k][3] for k in fin if k in req), FY24_FINAL_TOTAL))
    out = []
    for k, (cip, printed, title, amt) in req.items():
        rk, c = ranks[k], comp[k]
        note = 'requests list %s pp7-8; members and composite %s' % (A195, A194)
        if k in [key(x) for x in FY24_ARPA]:
            note += '; funded with ARPA money, which the Article 6 table marks as not needing a Town Meeting vote'
        out.append(row(fiscal_year=2024, project_number=cip, project=title, department=dept_of(cip, None),
                       department_as_printed=printed, amount=num(amt), cpc_rank=rk['cpc'], cpc_ranked_of=29,
                       tm_rank=rk['tm'], collins_score=rk['collins'], composite_average=c['avg'],
                       member_ranks='; '.join('%s %d' % (h, v) for h, v in zip(heads, c['members'])),
                       tm_preliminary='yes' if rk['prelim'] else 'no', funded='yes' if k in fin else 'no',
                       outcome_basis="Town Meeting vote and the Town Manager's final plan, Town Clerk's record",
                       rank_source=rk['src'], outcome_source='%s pp163-164 (Article 6, May 2023 ATM)' % AR23,
                       notes=note))
    return out


# ------------------------------------------------------------------ FY2025
def fy2025():
    ws = sheet(CPC25, 'Ordered')
    head = [c.value for c in ws[1]]
    members = head[9:14]
    if head[:9] != [None, 'Department', 'Sub Department', 'Original Order', 'Dept Priority', 'Project Number',
                    'Request Title', 'Collins Score', 'FY2025'] or len([m for m in members if m]) != 5 or head[14] != 'Column1':
        fail('FY2025: the Ordered sheet heading moved: %s' % head)
    rows = {}
    for r in ws.iter_rows(min_row=2, max_row=ws.max_row):
        v = [c.value for c in r]
        if v[0] is None or v[5] is None:
            continue
        rows[key(v[5])] = dict(cell=r[0].row, cpc=int(v[0]), dept=v[1], dr=int(v[4]), cip=v[5].strip(),
                               title=v[6].strip(), collins=int(v[7]), amt=Decimal(str(v[8])),
                               members=[int(x) for x in v[9:14]], avg=v[14])
    if len(rows) != 35 or sorted(r['cpc'] for r in rows.values()) != list(range(1, 36)):
        fail('FY2025: %d ranked rows' % len(rows))
    tm = {}
    for n in (11, 22):
        for ln in page(D1504, n).splitlines():
            m = re.match(r'^(\d+) (\d+) (\d+) ' + CIP + r' ', ln.strip())
            if m:
                tm[key(m.group(4))] = dict(tm=int(m.group(1)), cpc=int(m.group(2)), collins=int(m.group(3)),
                                           src='%s p%d' % (D1504, n), prelim=(n == 11))
    if set(tm) != set(rows):
        fail('FY2025: 1504 and the workbook name different projects: %s' % sorted(set(tm) ^ set(rows)))
    for k, r in rows.items():
        if (tm[k]['cpc'], tm[k]['collins']) != (r['cpc'], r['collins']):
            fail('FY2025 %s: 1504 prints CPC %s Collins %s, the workbook %s and %s'
                 % (k, tm[k]['cpc'], tm[k]['collins'], r['cpc'], r['collins']))
    voted = None
    txt = open(S('town-annual-reports', 'text', '4132-fy-2024-annual-town-report.txt'), encoding='utf-8').read()
    m = re.search(r'total appropri-?\s*ation of \$([\d,.]+) to fund the FY25 Capital Plan', txt)
    if not m:
        fail('FY2025: the Article 6 vote total did not read')
    voted = money(m.group(1))
    ten = [k for k in rows if tm[k]['prelim']]
    if len(ten) != 10 or sum(rows[k]['amt'] for k in ten) != voted:
        fail('FY2025: the TM ten sum to %s, Article 6 voted %s' % (sum(rows[k]['amt'] for k in ten), voted))
    dup = sorted(t['tm'] for t in tm.values())
    out = []
    for k, r in sorted(rows.items(), key=lambda kv: kv[1]['cpc']):
        note = 'workbook %s, sheet Ordered, row %d' % (CPC25, r['cell'])
        if dup.count(tm[k]['tm']) > 1:
            note += '; TM priority %d is printed twice on p22 and 31 not at all' % tm[k]['tm']
        out.append(row(fiscal_year=2025, project_number=r['cip'], project=r['title'], department=dept_of(r['cip'], None),
                       department_as_printed=r['dept'], amount=num(r['amt']), cpc_rank=r['cpc'], cpc_ranked_of=35,
                       tm_rank=tm[k]['tm'], collins_score=r['collins'], composite_average=num(r['avg']).rstrip('0').rstrip('.') if r['avg'] is not None else '',
                       dept_rank=r['dr'],
                       member_ranks='; '.join('%s %d' % (h, v) for h, v in zip(members, r['members'])),
                       tm_preliminary='yes' if tm[k]['prelim'] else 'no', funded='yes' if k in ten else 'no',
                       outcome_basis="Town Meeting vote, Town Clerk's record (total equals the Town Manager's ten)",
                       rank_source='%s, sheet Ordered, row %d; TM rank %s' % (CPC25, r['cell'], tm[k]['src']),
                       outcome_source='%s (Article 6, May 2024 ATM)' % AR24, notes=note))
    return out


# ------------------------------------------------------------------ FY2026
def fy2026():
    opts = {1: [], 2: []}
    for r in csv.DictReader(open(S('data', 'capital-program-options.csv'), encoding='utf-8')):
        if r['program_fy'] == '2026' and r['kind'] == 'project' and r['project'] != 'Contingency':
            opts[int(r['option'])].append(r)
    txt = open(S('town-annual-reports', 'text', '4130-fy-2025-annual-town-report.txt'), encoding='utf-8').read()
    if 'VOTED Option 2 as presented' not in txt:
        fail('FY2026: the Option 2 vote did not read')
    name = lambda r: (r['cpc_ranking'], r['project'])
    two = {name(r) for r in opts[2]}
    seen, out = set(), []
    for r in opts[1] + opts[2]:
        if name(r) in seen:
            continue
        seen.add(name(r))
        rank = r['cpc_ranking'] if r['cpc_ranking'].isdigit() else ''
        in1 = name(r) in {name(x) for x in opts[1]}
        out.append(row(fiscal_year=2026, project=r['project'], department=dept_of(None, r['department']),
                       department_as_printed=r['department'], amount=r['project_cost'], cpc_rank=rank,
                       tm_preliminary='yes' if in1 else 'no', funded='yes' if name(r) in two else 'no',
                       outcome_basis="Town Meeting vote, Town Clerk's record (Option 2 voted)",
                       rank_source='%s p%s, Option %s' % (AR25, r['page'], r['option']),
                       outcome_source='%s p139 (May 2025 ATM, Option 2)' % AR25,
                       notes='; '.join(x for x in [('CPC rank printed as %r' % r['cpc_ranking']) if not rank else '',
                                        'in Option %s only' % r['option'] if (in1 != (name(r) in two)) else
                          'in both options'] if x)))
    return sorted(out, key=lambda r: (int(r['cpc_rank']) if r['cpc_rank'] else 99, r['project']))


# ------------------------------------------------------------------ FY2027
def fy2027():
    ws = sheet(PLAN27, 'FY27 Capital')
    if [c.value for c in ws[1]][:6] != ['CPC Rank', 'Department', 'Project', 'Project Cost',
                                        'Ranking based on average', 'Cumulative cost']:
        fail('FY2027: the plan workbook heading moved')
    rows = []
    for r in ws.iter_rows(min_row=2, max_row=ws.max_row):
        v = [c.value for c in r]
        if isinstance(v[0], int):
            rows.append(dict(cell=r[0].row, cpc=v[0], dept=v[1], title=v[2].strip(), amt=Decimal(str(v[3])), avg=v[4]))
    total = ws.cell(24, 4).value
    if len(rows) != 22 or sum(r['amt'] for r in rows) != Decimal(str(total)):
        fail('FY2027: %d rows summing %s against D24 %s' % (len(rows), sum(r['amt'] for r in rows), total))
    pri = sheet(PRI27, 'Sheet1')
    ph = [c.value for c in pri[1]]
    mem = {}
    for r in pri.iter_rows(min_row=2, max_row=pri.max_row):
        v = [c.value for c in r]
        if isinstance(v[1], int) and v[4]:
            mem[v[1]] = '; '.join('%s %s' % (h, x) for h, x in zip(ph[6:11], v[6:11]) if x is not None)
    # Article 13, the May 2026 warrant p30: ranks and amounts of the funded twelve.
    t = page(W2026, 30)
    art = re.findall(r'(?m)^(\d{1,2}) (DPW|Police|Fire|Schools|Facilities|IT) ', t)
    cum = re.findall(r'([\d,]+) ([\d,]+) [\d,]+\s*$', t, re.M)
    funded = {int(a) for a, _ in art}
    if funded != set(range(1, 13)):
        fail('FY2027: Article 13 ranks read as %s' % sorted(funded))
    printed = re.search(r'funds the \$([\d,]+) FY 2027 Program', page(W2026, 31))
    if sum(r['amt'] for r in rows if r['cpc'] in funded) != money(printed.group(1)):
        fail('FY2027: ranks 1-12 sum to %s, the summary prints %s'
             % (sum(r['amt'] for r in rows if r['cpc'] in funded), printed.group(1)))
    # The Town Manager's preliminary program, 1 February 2026, p8: cost, project, department and
    # CPC rank run together in the text layer, then the printed Total.
    t8 = page(PRE27, 8)
    pre = re.findall(r'(\d{1,3}(?:,\d{3})*)([^\d].+?)(DPW|Police|Fire|Schools|Facilities|IT)(\d{1,2}) ', t8)
    pre_ranks = {int(x[3]) for x in pre}
    ptot = re.search(r'([\d,]+)Total', t8)
    if not pre or sum(money(x[0]) for x in pre) != money(ptot.group(1)) \
            or any(money(x[0]) != next(r['amt'] for r in rows if r['cpc'] == int(x[3])) for x in pre):
        fail('FY2027: the preliminary program read %s against its Total %s' % (pre, ptot and ptot.group(1)))
    out = []
    for r in rows:
        out.append(row(fiscal_year=2027, project=r['title'], department=dept_of(None, r['dept']),
                       department_as_printed=r['dept'], amount=num(r['amt']), cpc_rank=r['cpc'], cpc_ranked_of=22,
                       composite_average=num(r['avg']).rstrip('0').rstrip('.'), member_ranks=mem.get(r['cpc'], ''),
                       tm_preliminary='yes' if r['cpc'] in pre_ranks else 'no',
                       funded='yes' if r['cpc'] in funded else 'no',
                       outcome_basis='the warrant article; Town Meeting passed it, known from the recording only',
                       rank_source='%s, sheet FY27 Capital, row %d; preliminary program %s p8' % (PLAN27, r['cell'], PRE27),
                       outcome_source='%s p30 (Article 13, May 2026 ATM)' % W2026,
                       notes='members %s' % PRI27 if mem.get(r['cpc']) else ''))
    return out, pre_ranks


def printed_department_totals():
    """{fy: {our department: the total the year's own document prints}}. OUR grouping must
    reproduce every one of them, or a department's share on the page is our invention."""
    out = {2023: {}, 2024: {}, 2025: {}, 2027: {}}
    m23 = {'Facilities': 'Facilities', 'General Govt.': 'General government', 'Police': 'Police',
           'Schools': 'Schools', 'Infrastructure': 'Public Works', 'Highway': 'Public Works'}
    for n in (6, 7):
        for name, v in re.findall(r'TOTAL (Facilities|General Govt\.|Police|Schools|Infrastructure|Highway) ([\d,]+)',
                                  page(A75, n)):
            d = m23[name]
            out[2023][d] = out[2023].get(d, 0) + money(v)
    m24 = {'Facilities and Grounds': 'Facilities', 'Fire Department': 'Fire', 'Public Works': 'Public Works',
           'School Department': 'Schools'}
    for name, v in re.findall(r'Total (Facilities and Grounds|Fire Department|Public Works|School Department) \$([\d,.]+)',
                              page(A195, 7) + page(A195, 8)):
        out[2024][m24[name]] = money(v)
    m25 = {'Facilities and Parks': 'Facilities', 'Fire Department': 'Fire', 'Police Department': 'Police',
           'Public Works': 'Public Works', 'School Department': 'Schools', 'Information Technology': 'IT'}
    for r in csv.DictReader(open(S('data', 'capital-requests.csv'), encoding='utf-8')):
        if r['version'] == 'fy25-town-manager-dept-totals' and r['amount_kind'] == 'dept_total':
            out[2025][m25[r['department']]] = Decimal(r['amount'])
    ws = sheet(PLAN27, 'FY27 Capital')
    for rr in range(27, 33):
        name, v = ws.cell(rr, 3).value, ws.cell(rr, 4).value
        out[2027][PRINTED[name.replace('Total ', '')]] = Decimal(str(v))
    return out


def build():
    r27, pre = fy2027()
    rows = fy2023() + fy2024() + fy2025() + fy2026() + r27
    for fy, want in printed_department_totals().items():
        got = {}
        for r in rows:
            if r['fiscal_year'] == str(fy):
                got[r['department']] = got.get(r['department'], 0) + Decimal(r['amount'])
        if got != want:
            fail('FY%d: our department grouping %s does not reproduce the printed totals %s' % (fy, got, want))
    for r in rows:
        if r['funded'] not in ('yes', 'no'):
            fail('%s %s: funded %r' % (r['fiscal_year'], r['project'], r['funded']))
    rows.sort(key=lambda r: (r['fiscal_year'], int(r['cpc_rank']) if r['cpc_rank'] else 999, r['project']))
    buf = io.StringIO()
    w = csv.DictWriter(buf, COLUMNS, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue(), rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text, rows = build()
    by = {}
    for r in rows:
        by.setdefault(r['fiscal_year'], [0, 0])
        by[r['fiscal_year']][0] += 1
        by[r['fiscal_year']][1] += r['funded'] == 'yes'
    summary = ', '.join('FY%s %d ranked/%d funded' % (y, n, f) for y, (n, f) in sorted(by.items()))
    if a.check:
        if not os.path.exists(OUT) or open(OUT, encoding='utf-8').read() != text:
            print('STALE %s' % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('capital rankings: current (%s)' % summary)
        return 0
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as fh:
        fh.write(text)
    os.replace(tmp, OUT)
    print('wrote %s (%s)' % (os.path.relpath(OUT, ROOT), summary))
    return 0


if __name__ == '__main__':
    sys.exit(main())
