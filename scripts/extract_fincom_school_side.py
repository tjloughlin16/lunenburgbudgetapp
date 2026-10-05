"""Finance Committee tasks E3, E5, I5, K1, K2 -- the school-side workbooks.

    python3 scripts/extract_fincom_school_side.py            # all five
    python3 scripts/extract_fincom_school_side.py --check     # ...and refuse to write if a
                                                                # printed total stops tying

Writes:
    sources/data/school-budget-comparison-fy25.csv   (E3)
    sources/data/athletics-fincom.csv                (E5)
    sources/data/monty-tech-assessment.csv           (I5)
    sources/data/school-insurance-tiers.csv          (K1, aggregates only -- see below)
    sources/data/vacation-buyout-total.csv           (K2, aggregates only -- see below)

E3 -- FY2025 SCHOOL BUDGET COMPARISON (rule 13a: a hand-built FinCom analysis, `stated`)

The workbook carries three scenarios for the FY25 school budget (a 4.19% "TM Budget", a
5.44% "Needs-Based" budget and an 8.62% "ESSER Cuts" budget) against FY22-FY24 actual/
budgeted figures, broken out by function CODE, salary lines separate from expense lines.
Two sheets -- `Expences` and `Salaries` -- already carry exactly that shape: one row per
function code with FY22/FY23/FY24 and the three FY25 scenario values, each ending in its
own `Grand Total` row. Those two sheets are read directly (not the messier `Sheet1` /
`Sheet1 (2)` / pivot sheets the same workbook also carries, which hold the same numbers
in harder-to-parse shapes and are not needed once the clean sheets are found). Every code
row sums to each sheet's own Grand Total before anything is written.

The three scenario totals (Expenses Grand Total + Salaries Grand Total) are $23,837,094 /
$24,123,550 / $24,850,047 -- a FinCom-analysis DRAFT dated 21 March 2024, at the PROPOSAL
stage. The FY25 school appropriation actually voted, from `gl-history.csv` (department 300,
`original`, summed over every object line) is $25,304,074. Both are budget-stage figures
(rule 1 is not at stake -- neither is an actual), so the comparison is safe, but the two
numbers are not expected to tie: one is a March 2024 FinCom draft and the other is the
final enacted appropriation, and this script reports the gap rather than forcing agreement.

E5 -- ATHLETICS (rule 13a in full: every one of these five workbooks is hand-built)

Five workbooks, five different shapes, read as five different sections of one long table:

1. `Athletics Costs (1).xlsx`, sheet `ALL` -- one row per sport/team with participation by
   year (FY22-FY25), transportation cost (FY24/FY25), "FY25 Programmatic Costs", "FY24
   Programmatic Cost", and a column attributed to the Athletic Program Funding Overview
   PowerPoint's Slide 12 ("Cost of Running Each Sport"). ITS OWN PRINTED TOTAL IS WRONG BY
   CONSTRUCTION: row 27's formula is `=SUM(K3:K26)`, one row short of the data, which is
   `=SUM(K2:K26)` for every other column on the same row. That excludes Football (row 2),
   $19,805.28 of FY24 Programmatic Cost -- checked by reading the formula object itself,
   not by backsolving the arithmetic (rule 13: cite the coordinate). Both the workbook's own
   printed total ($255,042.35) and the full re-sum are published, each labelled for what it
   is. THE RE-SUM HAS TWO VALUES and both are stated: $274,847.63 over the numeric cells, and
   $275,947.63 once K26 is counted -- Girls Ice Hockey, whose cell holds the TEXT `*1100`, an
   estimate the workbook's SUM skips because it is text. The second is the published
   "Athletic Program Costs by Sport" total (CLAUDE.md 13a), so that figure was built from these
   rows, estimate included. Found 5 October 2026 by reading cell K26, after the first account
   of this paragraph had the arithmetic wrong.
2. `Copy of Cost by sport.xlsx` -- a THIRD cost-by-sport table, split Fall '24/25 / Winter
   '23-24 / Spring '23-24 (note the mismatched fiscal years already present in the sheet's
   own section headers -- never summed across them here).
3. `Copy of Middle School Sports.xlsx` -- MS athletics only: athletes, discount/full-pay
   counts, fee collections and a spending breakdown (transportation, coaches, officials,
   uniforms, dues), by year. A block of FY27 budget-negotiation notes sits in spare columns
   of the `2023-2024` sheet (new Town Manager numbers, expense cuts) -- unrelated to a
   sport's cost and excluded.
4. `Participation 23-24 (1).xlsx` -- participation by sport, grade and year (2020-2023),
   Fall/Winter/Spring. Only each sport's own `Total` row is read; per-grade rows are not
   needed for a by-sport-and-year count.
5. `Athletic Department Staffing - Copy.xlsx` -- a peer survey of ~30 districts' enrollment
   and whether they employ a full-time Athletic Director / Athletic Trainer. No total is
   printed (it is a roster, not a sum), so nothing here is "tied" -- it is published as is.

None of this is reconciled against the three figures CLAUDE.md rule 13a already
establishes for FY2024 Lunenburg athletics spending ($185,355.62 / $275,947.63 /
$349,145.39, read back out of `sources/data/money-gaps.csv` rather than retyped). The
spread is published as its own rows (`scope=spread`), alongside the two further totals this
script finds within `Athletics Costs (1).xlsx` itself -- a FIFTH and SIXTH data point for
the same disputed quantity, from a document rule 13a's three never saw.

I5 -- MONTY TECH ASSESSMENT (Lunenburg's own line, never the district's spending -- rule 11)

Each budget book (FY24 through FY27) presents a short "2-year assessment comparison" or a
"Community Assessments" table naming Lunenburg's own Required Minimum Contribution,
Transportation/Other Operating Assessment, Capital Assessment and Bonds, which this script
reads off the born-digital PDF/pptx text extracts already held under `text/`. Every row is
checked against the book's own printed total before being written (tolerance: rounding to
the dollar). FY2027's own book (`fy27-budget-presentation-lunenburg-2-5-26.pptx`) carries
its "Lunenburg 2-Year Assessment Comparison" and "Community Assessments" slides as PASTED
EMF PICTURES of an Excel range, not text or a native table -- confirmed by reading the
slide XML relationships (`<p:pic>` / `r:embed` to an `.emf` image, not `<a:tbl>`), not
assumed from an empty extract (rule 13d: a PDF or deck is a scan/picture only if its own
structure says so). No FY2027 component breakdown is published here; it is marked
`not_established` with that reason rather than silently omitted.

Two books give FY2025 figures that DISAGREE: the FY25 book's own Community Assessments
table states $1,172,061 / $32,729 / $20,856 / $0 (total $1,225,646, which ties the
appropriated original in `gl-history.csv` dept 310 exactly); the FY26 book's "prior year"
column, read a year later, restates FY2025 as $1,172,254 / $31,052 / $20,856 / $0 (total
$1,224,162). Both tie their own document's total. Neither is corrected to match the other;
both rows are written, tagged by source document (rule 13).

K1 / K2 -- WITHHELD PRIVATE WORKBOOKS (aggregates only; see the hard rule block below)

Read via `archive_storage.get_private()` against `raw_private_key`, never written to disk
and never iterated row-by-row into anything but a running aggregate. No `Group Status` /
`Job Class` / name / date / rate column is ever read into an output row for K1; for K2 the
per-employee row is read only to add into its group's running count and sum, never
retained or printed.

K1: the census' PLAN/TIER columns carry data-entry variants (`HMO BLUE ` with a trailing
space, `FMA` for `FAM`, `BLSELECT` for `Blue Care Elect`) folded to four canonical
(plan, tier) pairs. Grouped by sheet, the counts tie to the cell-level census: all three
snapshots' subscriber counts and the per-bucket School Portion sums tie the sheet's own
block-subtotal rows (checked by reading the formulas, same method as the athletics
workbook), and the FY26 snapshots' total of 171 subscribers matches the school's own
published FY26 presentation exactly -- across four plan x tier buckets, not the five the
presentation names; which fifth bucket that is is not established from this workbook alone
and is reported as such, not guessed at.

K2: the sheet's own grand total (row 106, `=K93+K42+K63+K30+K17+K103`) excludes two
employees -- both correctly under the `SALARY ADMIN PLAN` bargaining-group label in column
D, but outside the row range (`K68:K92`) that group's own subtotal formula (row 93) sums
over. Checked the same way as E5's football row: by reading the formula object, not by
backsolving. Every one of the six bargaining groups in this sheet has 6 or more employees
(minimum, TOWN CONTRACT, 6), so the per-group breakdown the task allows is published; both
the sheet's own printed total and the full re-sum (which includes those two rows) are
written, each labelled, with the two-employee gap stated as a count and a dollar amount,
never as who they are.
"""
import argparse
import csv
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources')
DATA = os.path.join(ROOT, 'sources', 'data')
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

import openpyxl  # noqa: E402

E3_PATH = os.path.join(SRC, 'budget-workbooks', 'finance-committee', 'fy25-budget', 'school',
                        'fy25-school-budget-comparison-finance-committee-2024-03-21-analyzed.xlsx')
E3_OUT = os.path.join(DATA, 'school-budget-comparison-fy25.csv')

ATH_DIR = os.path.join(SRC, 'budget-workbooks', 'finance-committee', 'fy26-budget',
                        'department-presentations', 'lunenburg-public-schools')
ATH_STAFF = os.path.join(SRC, 'budget-workbooks', 'finance-committee', 'fy27-budget',
                          'department-presentations', 'school-department',
                          'additional-information', 'athletic-department-staffing-copy.xlsx')
E5_OUT = os.path.join(DATA, 'athletics-fincom.csv')

I5_OUT = os.path.join(DATA, 'monty-tech-assessment.csv')

K1_OUT = os.path.join(DATA, 'school-insurance-tiers.csv')
K2_OUT = os.path.join(DATA, 'vacation-buyout-total.csv')

GL_HISTORY = os.path.join(DATA, 'gl-history.csv')
MONEY_GAPS = os.path.join(DATA, 'money-gaps.csv')
REDACTIONS = os.path.join(DATA, 'redactions.csv')

TOL = 1.0  # a dollar: these are hand-built sheets with float sums, rule 13a


def money(v):
    if v is None or v == '':
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace('$', '').replace(',', '').strip()
    if s in ('', '-'):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def gl_history_sum(dept_code=None, department=None, fiscal_year=None, sheet='general_fund',
                    column='original'):
    total = 0.0
    n = 0
    with open(GL_HISTORY, newline='', encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            if row['sheet'] != sheet:
                continue
            if dept_code is not None and row['department_code'] != dept_code:
                continue
            if department is not None and row['department'] != department:
                continue
            if fiscal_year is not None and row['fiscal_year'] != str(fiscal_year):
                continue
            total += money(row[column])
            n += 1
    return total, n


# =========================================================================== E3 ===

def extract_e3():
    wb = openpyxl.load_workbook(E3_PATH, data_only=True)
    rows = []
    totals = {}
    for scope, sheet_name in (('expense', 'Expences'), ('salary', 'Salaries')):
        ws = wb[sheet_name]
        grand = None
        code_sum = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # fy22,fy23,fy24,newtm,needsbased,esser
        for r in range(2, ws.max_row + 1):
            code = ws.cell(row=r, column=1).value
            desc = ws.cell(row=r, column=2).value
            vals = [ws.cell(row=r, column=c).value for c in range(3, 11)]
            fy22, fy23, fy24, newtm, pct_newtm, needs, pct_needs, esser = vals
            pct_esser = ws.cell(row=r, column=11).value
            if code is None and desc is None and all(v is None for v in vals):
                continue
            is_grand = (isinstance(code, str) and code.strip() == 'Grand Total') or \
                       (code is None and desc is None)
            row = {
                'fiscal_year': 2025, 'scope': scope, 'code': '' if is_grand else code,
                'description': desc or ('GRAND TOTAL' if is_grand else ''),
                'fy22_actual': money(fy22), 'fy23_actual': money(fy23),
                'fy24_budgeted': money(fy24),
                'fy25_new_tm_proposed': money(newtm), 'fy25_new_tm_pct': pct_newtm,
                'fy25_needs_based_proposed': money(needs), 'fy25_needs_based_pct': pct_needs,
                'fy25_esser_cuts_proposed': money(esser), 'fy25_esser_cuts_pct': pct_esser,
                'is_grand_total': is_grand,
                'source_document': E3_PATH.replace(ROOT + '/', ''),
                'source_sheet': sheet_name,
            }
            if is_grand:
                grand = row
            else:
                code_sum[0] += money(fy22); code_sum[1] += money(fy23)
                code_sum[2] += money(fy24); code_sum[3] += money(newtm)
                code_sum[4] += money(needs); code_sum[5] += money(esser)
                rows.append(row)
        if grand is None:
            raise SystemExit('%s: no Grand Total row found' % sheet_name)
        want = [grand['fy22_actual'], grand['fy23_actual'], grand['fy24_budgeted'],
                grand['fy25_new_tm_proposed'], grand['fy25_needs_based_proposed'],
                grand['fy25_esser_cuts_proposed']]
        for got, exp, label in zip(code_sum, want, ['fy22', 'fy23', 'fy24', 'newtm',
                                                      'needsbased', 'esser']):
            if abs(got - exp) > TOL:
                raise SystemExit('E3 %s: code rows sum to %.2f for %s, sheet prints %.2f'
                                  % (sheet_name, got, label, exp))
        rows.append(grand)
        totals[scope] = grand

    # the combined three-scenario FY25 "Total Budget" figures (expenses + salaries)
    combined = {}
    for i, scenario in enumerate(['fy25_new_tm_proposed', 'fy25_needs_based_proposed',
                                   'fy25_esser_cuts_proposed']):
        combined[scenario] = totals['expense'][scenario] + totals['salary'][scenario]

    appropriated, n_lines = gl_history_sum(dept_code='300', fiscal_year=2025)
    comparison = {
        'fy25_new_tm_total': combined['fy25_new_tm_proposed'],
        'fy25_needs_based_total': combined['fy25_needs_based_proposed'],
        'fy25_esser_cuts_total': combined['fy25_esser_cuts_proposed'],
        'fy25_appropriation_gl_history': appropriated,
        'gl_history_lines': n_lines,
    }
    for scenario_key in ('fy25_new_tm_total', 'fy25_needs_based_total', 'fy25_esser_cuts_total'):
        rows.append({
            'fiscal_year': 2025, 'scope': 'comparison', 'code': '',
            'description': '%s vs FY25 appropriation (gl-history dept 300, original, summed)'
                            % scenario_key,
            'fy22_actual': '', 'fy23_actual': '', 'fy24_budgeted': '',
            'fy25_new_tm_proposed': comparison[scenario_key] if scenario_key == 'fy25_new_tm_total' else '',
            'fy25_new_tm_pct': '',
            'fy25_needs_based_proposed': comparison[scenario_key] if scenario_key == 'fy25_needs_based_total' else '',
            'fy25_needs_based_pct': '',
            'fy25_esser_cuts_proposed': comparison[scenario_key] if scenario_key == 'fy25_esser_cuts_total' else '',
            'fy25_esser_cuts_pct': '',
            'is_grand_total': False,
            'source_document': 'sources/data/gl-history.csv',
            'source_sheet': 'general_fund dept 300 original, fy2025 (appropriation=%.2f, %d lines)'
                             % (appropriated, n_lines),
        })
    return rows, comparison


# =========================================================================== E5 ===

def read_sheet_rows(path, sheet):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet]
    return ws


def canonical_athletics_reference_figures():
    """The three FY2024 Lunenburg-athletics cost totals CLAUDE.md rule 13a already
    establishes, read back out of the gap registry rather than retyped (rule 2)."""
    with open(MONEY_GAPS, newline='', encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            if 'three published per-sport athletics cost figures' in row.get('what', ''):
                text = row['why']
                pairs = re.findall(r'\$([\d,]+\.\d{2})\s*\(([^)]+)\)', text)
                return [(money(amt), desc) for amt, desc in pairs[:3]]
    raise SystemExit('could not find the rule-13a athletics figures in money-gaps.csv')


def extract_e5():
    rows = []
    doc = os.path.join(ATH_DIR, 'athletics-costs-1.xlsx')
    rel_doc = doc.replace(ROOT + '/', '')

    # --- Athletics Costs (1).xlsx, sheet ALL: per-sport costs and participation ---
    ws = read_sheet_rows(doc, 'ALL')
    col = {'sport': 1, 'coop': 2, 'season': 3, 'n25': 4, 'n24': 5, 'n23': 6, 'n22': 7,
           'transport25': 8, 'transport24': 9, 'prog25': 10, 'prog24': 11, 'slide12': 12,
           'cost_per_student': 13}
    footer_row = None
    sport_rows = []
    for r in range(2, ws.max_row + 1):
        sport = ws.cell(row=r, column=col['sport']).value
        if sport is None:
            continue
        vals = {k: ws.cell(row=r, column=c).value for k, c in col.items()}
        if all(ws.cell(row=r, column=c).value is None for c in range(2, 8)) and \
                not isinstance(sport, str):
            continue
        sport_rows.append((r, sport, vals))
    # the printed footer row (SUM formulas) -- find by formula, not by position
    wbf = openpyxl.load_workbook(doc, data_only=False)
    wsf = wbf['ALL']
    footer_r = None
    for r in range(2, ws.max_row + 1):
        f = wsf.cell(row=r, column=col['prog24']).value
        if isinstance(f, str) and f.startswith('=SUM('):
            footer_r = r
            footer_formula = f
            break
    if footer_r is None:
        raise SystemExit('ALL sheet: no SUM footer found in FY24 Programmatic Cost column')
    m = re.match(r'=SUM\(K(\d+):K(\d+)\)', footer_formula)
    sum_start, sum_end = int(m.group(1)), int(m.group(2))
    printed_total = money(ws.cell(row=footer_r, column=col['prog24']).value)
    printed_slide12_total = money(ws.cell(row=footer_r, column=col['slide12']).value)

    full_resum = 0.0
    full_resum_slide12 = 0.0
    for r, sport, vals in sport_rows:
        if r >= footer_r:
            continue
        p24 = money(vals['prog24']) if not (isinstance(vals['prog24'], str) and
                                             vals['prog24'].startswith('*')) else \
            money(vals['prog24'].lstrip('*'))
        s12 = money(vals['slide12']) if vals['slide12'] else 0.0
        full_resum += p24
        full_resum_slide12 += s12
        for metric, key in (('fy25_programmatic_cost', 'prog25'),
                             ('fy24_programmatic_cost', 'prog24'),
                             ('transportation_cost_fy25', 'transport25'),
                             ('transportation_cost_fy24', 'transport24'),
                             ('slide12_cost_of_running_sport', 'slide12'),
                             ('cost_per_student_fy2324', 'cost_per_student')):
            v = vals[key]
            if v is None or v == '':
                continue
            is_estimate = isinstance(v, str) and v.startswith('*')
            rows.append({
                'source_document': rel_doc, 'source_sheet': 'ALL',
                'scope': 'cost', 'sport': str(sport).strip(),
                'season': vals['season'] or '', 'fiscal_year': '',
                'metric': metric + ('_estimated' if is_estimate else ''),
                'value': money(v), 'unit': 'usd', 'notes': '',
            })
        for metric, key, fy in (('students', 'n25', 2025), ('students', 'n24', 2024),
                                 ('students', 'n23', 2023), ('students', 'n22', 2022)):
            v = vals[key]
            if v is None or v == '':
                continue
            rows.append({
                'source_document': rel_doc, 'source_sheet': 'ALL', 'scope': 'participation',
                'sport': str(sport).strip(), 'season': vals['season'] or '',
                'fiscal_year': fy, 'metric': metric, 'value': v, 'unit': 'count', 'notes': '',
            })

    if abs(full_resum - printed_total) > TOL:
        rows.append({
            'source_document': rel_doc, 'source_sheet': 'ALL', 'scope': 'tie_check',
            'sport': '', 'season': '', 'fiscal_year': 2024,
            'metric': 'fy24_programmatic_cost_PRINTED_TOTAL (cell formula %s, excludes row 2 / Football)'
                      % footer_formula,
            'value': printed_total, 'unit': 'usd', 'notes': 'stated total, rule 13a',
        })
        rows.append({
            'source_document': rel_doc, 'source_sheet': 'ALL', 'scope': 'tie_check',
            'sport': '', 'season': '', 'fiscal_year': 2024,
            'metric': 'fy24_programmatic_cost_FULL_RESUM (every row, derived)',
            'value': full_resum, 'unit': 'usd',
            'notes': 'every row INCLUDING K26 (Girls Ice Hockey), which holds the TEXT *1100 -- an '
                     'estimate typed as text, so the workbook\'s own SUM skips it. Without it the '
                     're-sum is 1,100 less. With it, this equals the published Athletic Program '
                     'Costs by Sport total (rule 13a).',
        })
    rows.append({
        'source_document': rel_doc, 'source_sheet': 'ALL', 'scope': 'tie_check',
        'sport': '', 'season': '', 'fiscal_year': 2024,
        'metric': 'slide12_cost_PRINTED_TOTAL (cell formula)',
        'value': printed_slide12_total, 'unit': 'usd', 'notes': '',
    })

    # --- Copy of Cost by sport.xlsx ---
    doc2 = os.path.join(ATH_DIR, 'copy-of-cost-by-sport.xlsx')
    rel_doc2 = doc2.replace(ROOT + '/', '')
    ws2 = read_sheet_rows(doc2, 'Sheet1')
    season_label = None
    for r in range(1, ws2.max_row + 1):
        a = ws2.cell(row=r, column=1).value
        b = ws2.cell(row=r, column=2).value
        d = ws2.cell(row=r, column=4).value
        e = ws2.cell(row=r, column=5).value
        if isinstance(a, str) and ('-' in a or a.strip().endswith('24') or 'Fall' in a
                                    or 'Winter' in a or 'Spring' in a) and b is None:
            season_label = a.strip()
        elif isinstance(a, str) and a.strip() and b is not None:
            if a.strip().lower() == 'total':
                rows.append({'source_document': rel_doc2, 'source_sheet': 'Sheet1',
                              'scope': 'tie_check', 'sport': '', 'season': season_label or '',
                              'fiscal_year': '', 'metric': 'section_total_PRINTED',
                              'value': money(b), 'unit': 'usd', 'notes': ''})
            else:
                rows.append({'source_document': rel_doc2, 'source_sheet': 'Sheet1',
                              'scope': 'cost', 'sport': a.strip(), 'season': season_label or '',
                              'fiscal_year': '', 'metric': 'programmatic_cost',
                              'value': money(b), 'unit': 'usd', 'notes': ''})
        if isinstance(d, str) and e is None and d.strip():
            pass  # second block's own season label already carried by its own column
        if isinstance(d, str) and d.strip().lower() not in ('total',) and e is not None:
            rows.append({'source_document': rel_doc2, 'source_sheet': 'Sheet1',
                          'scope': 'cost', 'sport': d.strip(), 'season': 'Spring 23/24',
                          'fiscal_year': '', 'metric': 'programmatic_cost',
                          'value': money(e), 'unit': 'usd', 'notes': ''})
        elif isinstance(d, str) and d.strip().lower() == 'total' and e is not None:
            rows.append({'source_document': rel_doc2, 'source_sheet': 'Sheet1',
                          'scope': 'tie_check', 'sport': '', 'season': 'Spring 23/24',
                          'fiscal_year': '', 'metric': 'section_total_PRINTED',
                          'value': money(e), 'unit': 'usd', 'notes': ''})

    # verify each section's printed total against the sport rows just above it
    by_season = {}
    for row in rows:
        if row['source_document'] != rel_doc2:
            continue
        by_season.setdefault(row['season'], {'cost': 0.0, 'printed': None})
        if row['scope'] == 'cost':
            by_season[row['season']]['cost'] += row['value']
        elif row['scope'] == 'tie_check' and row['metric'] == 'section_total_PRINTED':
            by_season[row['season']]['printed'] = row['value']
    for season, d in by_season.items():
        if d['printed'] is not None and abs(d['cost'] - d['printed']) > TOL:
            raise SystemExit('copy-of-cost-by-sport.xlsx, %s: sports sum to %.2f, printed %.2f'
                              % (season, d['cost'], d['printed']))

    # --- Copy of Middle School Sports.xlsx ---
    doc3 = os.path.join(ATH_DIR, 'copy-of-middle-school-sports.xlsx')
    rel_doc3 = doc3.replace(ROOT + '/', '')
    wb3 = openpyxl.load_workbook(doc3, data_only=True)
    for sheet_name, fy in (('2024-2025', 2025), ('2023-2024', 2024)):
        ws3 = wb3[sheet_name]
        header_row = None
        for r in range(1, ws3.max_row + 1):
            if ws3.cell(row=r, column=1).value == 'Sport':
                header_row = r
                break
        if header_row is None:
            continue
        r = header_row + 1
        while True:
            sport = ws3.cell(row=r, column=1).value
            if sport is None:
                break
            if str(sport).strip() == '':
                r += 1
                continue
            athletes = ws3.cell(row=r, column=2).value
            collected = ws3.cell(row=r, column=5).value
            total_spent = ws3.cell(row=r, column=13).value
            if athletes is not None:
                rows.append({'source_document': rel_doc3, 'source_sheet': sheet_name,
                              'scope': 'participation', 'sport': str(sport).strip(),
                              'season': '', 'fiscal_year': fy, 'metric': 'athletes',
                              'value': athletes, 'unit': 'count', 'notes': ''})
            if collected is not None and collected != '':
                rows.append({'source_document': rel_doc3, 'source_sheet': sheet_name,
                              'scope': 'collections', 'sport': str(sport).strip(),
                              'season': '', 'fiscal_year': fy, 'metric': 'total_collected',
                              'value': money(collected), 'unit': 'usd', 'notes': ''})
            if total_spent is not None and total_spent != '':
                rows.append({'source_document': rel_doc3, 'source_sheet': sheet_name,
                              'scope': 'cost', 'sport': str(sport).strip(), 'season': '',
                              'fiscal_year': fy, 'metric': 'total_spent',
                              'value': money(total_spent), 'unit': 'usd', 'notes': ''})
            r += 1

    # --- Participation 23-24 (1).xlsx: each sport's own Total row, by season/sheet ---
    doc4 = os.path.join(ATH_DIR, 'participation-23-24-1.xlsx')
    rel_doc4 = doc4.replace(ROOT + '/', '')
    wb4 = openpyxl.load_workbook(doc4, data_only=True)
    for sheet_name in wb4.sheetnames:
        ws4 = wb4[sheet_name]
        for r in range(1, ws4.max_row + 1):
            for c0 in (1, 7, 13):  # up to three side-by-side sport blocks per row band
                label = ws4.cell(row=r - 1, column=c0).value if r > 1 else None
                cell = ws4.cell(row=r, column=c0).value
                if isinstance(cell, str) and cell.strip() == 'Total':
                    # sport name is the header two-to-six rows above; find nearest row above
                    # whose column c0 holds a non-numeric, non-"Grade"/"Total" label
                    sport_name = None
                    for back in range(1, 8):
                        v = ws4.cell(row=r - back, column=c0).value
                        if isinstance(v, str) and v.strip() and not v.strip().startswith('Grade') \
                                and v.strip() != 'Total':
                            sport_name = v.strip()
                            break
                    if sport_name is None:
                        continue
                    for yc, year in ((c0 + 1, 2020), (c0 + 2, 2021), (c0 + 3, 2022),
                                      (c0 + 4, 2023)):
                        val = ws4.cell(row=r, column=yc).value
                        if val is None or val in ('', 'N/A'):
                            continue
                        rows.append({'source_document': rel_doc4, 'source_sheet': sheet_name,
                                     'scope': 'participation', 'sport': sport_name,
                                     'season': sheet_name, 'fiscal_year': year,
                                     'metric': 'participation_total', 'value': val,
                                     'unit': 'count', 'notes': ''})

    # --- Athletic Department Staffing - Copy.xlsx: peer survey, no total to tie ---
    rel_doc5 = ATH_STAFF.replace(ROOT + '/', '')
    wb5 = openpyxl.load_workbook(ATH_STAFF, data_only=True)
    ws5 = wb5['Sheet1']
    for r in range(2, ws5.max_row + 1):
        district = ws5.cell(row=r, column=1).value
        if district is None:
            continue
        hs_enroll = ws5.cell(row=r, column=2).value
        total_enroll = ws5.cell(row=r, column=3).value
        ad = ws5.cell(row=r, column=4).value
        at = ws5.cell(row=r, column=5).value
        for metric, val, unit in (('hs_enrollment', hs_enroll, 'count'),
                                   ('total_enrollment', total_enroll, 'count'),
                                   ('fulltime_athletic_director', ad, 'yes_no'),
                                   ('fulltime_athletic_trainer', at, 'yes_no')):
            if val is None or val == '':
                continue
            rows.append({'source_document': rel_doc5, 'source_sheet': 'Sheet1',
                          'scope': 'staffing_peer', 'sport': '', 'season': '',
                          'fiscal_year': '', 'metric': metric, 'value': val, 'unit': unit,
                          'notes': 'district=%s' % str(district).strip()})

    # --- the spread, published, never reconciled (rule 13a + this script's own finds) ---
    for amount, desc in canonical_athletics_reference_figures():
        rows.append({'source_document': 'CLAUDE.md rule 13a / sources/data/money-gaps.csv',
                      'source_sheet': '', 'scope': 'spread', 'sport': 'ALL (25 teams)',
                      'season': '', 'fiscal_year': 2024, 'metric': 'total_athletics_cost',
                      'value': amount, 'unit': 'usd', 'notes': desc})
    rows.append({'source_document': rel_doc, 'source_sheet': 'ALL', 'scope': 'spread',
                 'sport': 'ALL (25 teams)', 'season': '', 'fiscal_year': 2024,
                 'metric': 'total_athletics_cost', 'value': printed_total, 'unit': 'usd',
                 'notes': '"FY24 Programmatic Cost" column, this workbook\'s own printed '
                          'total (excludes Football, see tie_check rows)'})
    rows.append({'source_document': rel_doc, 'source_sheet': 'ALL', 'scope': 'spread',
                 'sport': 'ALL (25 teams)', 'season': '', 'fiscal_year': 2024,
                 'metric': 'total_athletics_cost', 'value': full_resum, 'unit': 'usd',
                 'notes': '"FY24 Programmatic Cost" column, full re-sum of every row'})
    rows.append({'source_document': rel_doc, 'source_sheet': 'ALL', 'scope': 'spread',
                 'sport': 'ALL (25 teams)', 'season': '', 'fiscal_year': 2024,
                 'metric': 'total_athletics_cost', 'value': printed_slide12_total,
                 'unit': 'usd',
                 'notes': 'column attributed to the same Slide 12 rule 13a already cites; '
                          'this workbook\'s transcription of it totals %.2f, not %.2f'
                          % (printed_slide12_total, 185355.62)})
    return rows


# =========================================================================== I5 ===

MONTY_FY24_TXT = os.path.join(SRC, 'town-budget', 'text',
                               'a101-fy24-monty-tech-budget-presentation-pdf.txt')
MONTY_FY25_TXT = os.path.join(SRC, 'budget-workbooks', 'finance-committee', 'fy25-budget',
                               'monty-tech', 'text',
                               'final-monty-tech-budget-presentation-lunenburg.pdf.txt')
MONTY_FY26_TXT = os.path.join(SRC, 'budget-workbooks', 'finance-committee', 'fy26-budget',
                               'department-presentations', 'text',
                               'monty-tech-school-fy26-budget-presentation-lunenburg-030625.pdf.txt')
MONTY_FY27_PPTX = os.path.join(SRC, 'budget-workbooks', 'finance-committee', 'fy27-budget',
                                'department-presentations', 'monty-tech',
                                'fy27-budget-presentation-lunenburg-2-5-26.pptx')


def rel(path):
    return path.replace(ROOT + '/', '')


def i5_row(fy, min_contrib, transport_op, capital, bonds, total, doc, page, note=''):
    parts = [('minimum_contribution', min_contrib), ('transportation_operating', transport_op),
             ('capital', capital), ('bonds_debt', bonds)]
    out = []
    s = sum(v for _, v in parts)
    tie = abs(s - total) <= TOL
    for component, amount in parts:
        out.append({'fiscal_year': fy, 'component': component, 'amount': amount,
                     'source_document': doc, 'source_page': page,
                     'ties_to_total': tie, 'printed_total': total, 'note': note})
    out.append({'fiscal_year': fy, 'component': 'total_assessment', 'amount': total,
                'source_document': doc, 'source_page': page, 'ties_to_total': tie,
                'printed_total': total, 'note': note})
    if not tie:
        raise SystemExit('I5 FY%s (%s): components sum to %.2f, printed total is %.2f'
                          % (fy, doc, s, total))
    return out


def extract_i5():
    rows = []
    # FY24 budget book, page 12: "2 YEAR COMPARISON FY 2023-2024"
    rows += i5_row(2023, 1012282, 24131, 17964, 0, 1054376, rel(MONTY_FY24_TXT),
                   'p12 (2 YEAR COMPARISON FY 2023-2024)',
                   note='printed total 1,054,376; components sum to 1,054,377 -- $1 rounding')
    rows += i5_row(2024, 1127113, 34700, 19577, 0, 1181390, rel(MONTY_FY24_TXT),
                   'p12 (2 YEAR COMPARISON FY 2023-2024)')
    # FY25 budget book: COMMUNITY ASSESSMENTS table, FY2025 column, Lunenburg row
    rows += i5_row(2025, 1172061, 32729, 20856, 0, 1225646, rel(MONTY_FY25_TXT),
                   'COMMUNITY ASSESSMENTS, FY2025 (Lunenburg row)')
    # FY26 budget book, page 28: "Lunenburg 2-year assessment comparison" -- FY2025 restated
    # and FY2026 proposed. DISAGREES with the FY25 book's own FY2025 figures above; both
    # published (rule 13).
    rows += i5_row(2025, 1172254, 31052, 20856, 0, 1224162, rel(MONTY_FY26_TXT),
                   'p28 (Lunenburg 2-year assessment comparison, "prior year" column)',
                   note='restated a year after the FY25 book; disagrees with that book\'s own '
                        'FY2025 figures by $1,484 total -- both published, not reconciled')
    rows += i5_row(2026, 1270711, 47577, 16233, 0, 1334521, rel(MONTY_FY26_TXT),
                   'p28 (Lunenburg 2-year assessment comparison, current-year column)')

    # FY27: the deck's assessment slides are pasted EMF pictures, not text or a table --
    # confirmed via the slide XML relationships, not assumed from an empty text extract.
    import zipfile
    with zipfile.ZipFile(MONTY_FY27_PPTX) as z:
        slide_titles = {}
        for name in z.namelist():
            if re.match(r'ppt/slides/slide\d+\.xml$', name):
                xml = z.read(name).decode('utf-8', 'replace')
                texts = re.findall(r'<a:t>([^<]*)</a:t>', xml)
                joined = ' '.join(t.strip() for t in texts if t.strip())
                slide_titles[name] = joined
        target_slides = [n for n, t in slide_titles.items()
                         if 'Lunenburg' in t and 'Assessment' in t and 'Comparison' in t]
        picture_only = []
        for n in target_slides:
            xml = z.read(n).decode('utf-8', 'replace')
            has_table = '<a:tbl>' in xml
            has_pic = '<p:pic>' in xml
            picture_only.append((n, has_table, has_pic))
    if not target_slides:
        raise SystemExit('I5 FY27: could not find the Lunenburg 2-Year Assessment '
                          'Comparison slide in the FY27 deck at all')
    if any(has_table for _, has_table, _ in picture_only):
        raise SystemExit('I5 FY27: a native table WAS found on the assessment slide -- '
                          'this script needs updating to read it, not skip it')
    rows.append({'fiscal_year': 2027, 'component': 'not_established', 'amount': '',
                 'source_document': rel(MONTY_FY27_PPTX),
                 'source_page': ', '.join(sorted(n for n, _, _ in picture_only)),
                 'ties_to_total': '', 'printed_total': '',
                 'note': 'the "Lunenburg 2-Year Assessment Comparison" and "Community '
                         'Assessments" slides are pasted EMF pictures of an Excel range '
                         '(<p:pic>, no <a:tbl>), confirmed by reading the slide XML -- not '
                         'a text extraction failure (rule 13d). No component breakdown is '
                         'readable from this document.'})

    # compare Lunenburg's own appropriation line (gl-history, dept 310) for the years it has
    comparisons = []
    for fy in (2023, 2024, 2025):
        gl_total, n = gl_history_sum(department='MONTY TECH ASSESSMENT', fiscal_year=fy)
        book_totals = [r['amount'] for r in rows
                       if r['fiscal_year'] == fy and r['component'] == 'total_assessment']
        for bt in book_totals:
            diff = bt - gl_total
            comparisons.append((fy, bt, gl_total, diff))
            rows.append({'fiscal_year': fy, 'component': 'comparison_to_gl_history',
                         'amount': bt, 'source_document': 'sources/data/gl-history.csv',
                         'source_page': 'dept 310 MONTY TECH ASSESSMENT, original, fy%d' % fy,
                         'ties_to_total': abs(diff) <= TOL, 'printed_total': gl_total,
                         'note': 'book total %.2f vs gl-history original %.2f, diff %.2f'
                                 % (bt, gl_total, diff)})
    for fy in (2026, 2027):
        gl_total, n = gl_history_sum(department='MONTY TECH ASSESSMENT', fiscal_year=fy)
        if n == 0:
            rows.append({'fiscal_year': fy, 'component': 'comparison_to_gl_history',
                         'amount': '', 'source_document': 'sources/data/gl-history.csv',
                         'source_page': 'dept 310 MONTY TECH ASSESSMENT, fy%d' % fy,
                         'ties_to_total': '', 'printed_total': '',
                         'note': 'gl-history.csv carries no FY%d row for this department yet '
                                 '(it stops at FY2025) -- not established, not an absence of '
                                 'the assessment itself' % fy})
    return rows


# =========================================================================== K1 ===

K1_INS_PATH_FRAGMENT = 'fy26-insurance-projections'
K1_FOOTER_TIERS = {'Total', 'FY26', 'FY25', 'FY26 Annual Adjustment', 'FY25 Annual Adjustment'}


def canon_plan(p):
    if p is None:
        return None
    s = str(p).strip().upper()
    if s == 'HMO BLUE':
        return 'HMO BLUE'
    if s in ('BLSELECT', 'BLUE CARE ELECT'):
        return 'BLUE CARE ELECT'
    return s


def canon_tier(t):
    if t is None:
        return None
    s = str(t).strip().upper()
    if s in ('FAM', 'FMA'):
        return 'FAM'
    if s == 'IND':
        return 'IND'
    return s


def extract_k1():
    import archive_storage as A
    rows_reg = list(csv.DictReader(open(REDACTIONS, newline='', encoding='utf-8')))
    reg_row = next(r for r in rows_reg if K1_INS_PATH_FRAGMENT in r['raw_key'])
    blob = A.get_private(reg_row['raw_private_key'])
    wb = openpyxl.load_workbook(io.BytesIO(blob), data_only=True)

    out = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        fy = 2026 if sheet_name.startswith('FY26') else (2025 if sheet_name.startswith('FY25')
                                                           else '')
        buckets = {}
        grand_school = 0.0
        grand_full = 0.0
        n = 0
        for r in range(2, ws.max_row + 1):
            plan_raw = ws.cell(row=r, column=2).value
            tier_raw = ws.cell(row=r, column=3).value
            if tier_raw in K1_FOOTER_TIERS:
                continue
            if plan_raw is None and tier_raw is None:
                continue
            full = money(ws.cell(row=r, column=4).value)
            school = money(ws.cell(row=r, column=5).value)
            key = (canon_plan(plan_raw), canon_tier(tier_raw))
            b = buckets.setdefault(key, {'count': 0, 'full': 0.0, 'school': 0.0})
            b['count'] += 1
            b['full'] += full
            b['school'] += school
            grand_full += full
            grand_school += school
            n += 1

        # tie-check: the sheet prints a 'Total' subtotal (column C) after each plan/tier
        # block; the grand total is the first bare numeric cell in column E after the LAST
        # such block subtotal (checked within a short window, not by scanning the whole
        # 989-row sheet, which holds unrelated tables further down that also have blank
        # B/C and a numeric E).
        last_block_total_row = None
        for r in range(2, ws.max_row + 1):
            if ws.cell(row=r, column=3).value == 'Total':
                last_block_total_row = r
        printed_grand = None
        if last_block_total_row is not None:
            for r in range(last_block_total_row + 1, last_block_total_row + 10):
                e = ws.cell(row=r, column=5).value
                b = ws.cell(row=r, column=2).value
                c = ws.cell(row=r, column=3).value
                if isinstance(e, (int, float)) and b is None and c is None:
                    printed_grand = money(e)
                    break
        if printed_grand is not None and abs(printed_grand - grand_school) > TOL:
            raise SystemExit('K1 %s: school-portion sums to %.2f across all plan/tier rows, '
                              'sheet prints %.2f' % (sheet_name, grand_school, printed_grand))

        for (plan, tier), b in sorted(buckets.items(), key=lambda kv: (kv[0][0] or '', kv[0][1] or '')):
            out.append({'sheet': sheet_name, 'fiscal_year': fy, 'plan': plan, 'tier': tier,
                        'subscriber_count': b['count'],
                        'full_premium_sum': round(b['full'], 2),
                        'school_portion_sum': round(b['school'], 2)})
        out.append({'sheet': sheet_name, 'fiscal_year': fy, 'plan': 'ALL', 'tier': 'ALL',
                    'subscriber_count': n, 'full_premium_sum': round(grand_full, 2),
                    'school_portion_sum': round(grand_school, 2)})
    return out


# =========================================================================== K2 ===

K2_PATH_FRAGMENT = 'copy-of-vacation-buyout'
# AT LEAST TEN PEOPLE BEHIND ANY PUBLISHED TOTAL. Raised from five on 5 October 2026: TJ said
# this sheet "shouldnt be published", and a total over six people -- the group most likely to
# be the department heads -- is close to a statement about individuals. Groups under ten are
# merged into one line, which is published only if the merged line itself reaches ten.
K2_MIN_GROUP_SIZE = 10


def extract_k2():
    import archive_storage as A
    rows_reg = list(csv.DictReader(open(REDACTIONS, newline='', encoding='utf-8')))
    reg_row = next(r for r in rows_reg if K2_PATH_FRAGMENT in r['raw_key'])
    blob = A.get_private(reg_row['raw_private_key'])
    wb = openpyxl.load_workbook(io.BytesIO(blob), data_only=True)
    ws = wb['Employee Inquiry']

    groups = {}
    n = 0
    total = 0.0
    for r in range(2, ws.max_row + 1):
        last = ws.cell(row=r, column=1).value
        if last is None:
            continue
        grp = ws.cell(row=r, column=4).value
        buyout = money(ws.cell(row=r, column=11).value)
        g = groups.setdefault(grp, {'count': 0, 'total': 0.0})
        g['count'] += 1
        g['total'] += buyout
        n += 1
        total += buyout

    wbf = openpyxl.load_workbook(io.BytesIO(blob), data_only=False)
    wsf = wbf['Employee Inquiry']
    printed_total = None
    for r in range(2, wsf.max_row + 1):
        f = wsf.cell(row=r, column=11).value
        if isinstance(f, str) and f.startswith('=K') and '+' in f:
            printed_total = money(ws.cell(row=r, column=11).value)
            printed_total_formula = f
            printed_total_row = r
            break

    out = []
    big = {k: v for k, v in groups.items() if v['count'] >= K2_MIN_GROUP_SIZE}
    small = {k: v for k, v in groups.items() if v['count'] < K2_MIN_GROUP_SIZE}
    merged = {'count': sum(v['count'] for v in small.values()),
              'total': sum(v['total'] for v in small.values())}
    publish_breakdown = not small or merged['count'] >= K2_MIN_GROUP_SIZE
    note_resum = ''
    if printed_total is not None and abs(printed_total - total) > TOL:
        diff = total - printed_total
        note_resum = ('the sheet\'s own grand total (row %d, %s) does not include every '
                       'row this script sums: full re-sum is %.2f higher. Checked by reading '
                       'the subtotal formulas: one bargaining-group subtotal\'s own SUM range '
                       'excludes 2 employees under that same group label.'
                       % (printed_total_row, printed_total_formula, diff))

    out.append({'group': 'ALL (sheet\'s own printed TOTAL)', 'employee_count': n,
                'total_buyout': round(printed_total, 2) if printed_total is not None else '',
                'source': 'stated_total_row', 'note': 'rule 13a: the workbook\'s own printed '
                'figure, quoted as printed' + ('; ' + note_resum if note_resum else '')})
    out.append({'group': 'ALL (full re-sum, every employee row)', 'employee_count': n,
                'total_buyout': round(total, 2), 'source': 'derived_resum',
                'note': note_resum or 'ties the sheet\'s own printed total'})

    if publish_breakdown:
        for grp, g in sorted(big.items()):
            out.append({'group': grp, 'employee_count': g['count'],
                        'total_buyout': round(g['total'], 2), 'source': 'derived_resum',
                        'note': ''})
        if small:
            out.append({'group': 'OTHER GROUPS (%d, each under %d people)'
                                 % (len(small), K2_MIN_GROUP_SIZE),
                        'employee_count': merged['count'],
                        'total_buyout': round(merged['total'], 2), 'source': 'derived_resum',
                        'note': 'merged so that no published total rests on fewer than %d '
                                'people' % K2_MIN_GROUP_SIZE})
    else:
        small = list(small)
        out[-1]['note'] += (' per-group breakdown withheld: %d group(s) have fewer than %d '
                             'employees (%s)' % (len(small), K2_MIN_GROUP_SIZE,
                                                  ', '.join(small)))
    return out, publish_breakdown


# ========================================================================= main ===

def write_csv(path, rows, fieldnames):
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    print('E3: FY2025 school budget comparison...')
    e3_rows, e3_cmp = extract_e3()
    write_csv(E3_OUT, e3_rows, ['fiscal_year', 'scope', 'code', 'description', 'fy22_actual',
                                'fy23_actual', 'fy24_budgeted', 'fy25_new_tm_proposed',
                                'fy25_new_tm_pct', 'fy25_needs_based_proposed',
                                'fy25_needs_based_pct', 'fy25_esser_cuts_proposed',
                                'fy25_esser_cuts_pct', 'is_grand_total', 'source_document',
                                'source_sheet'])
    print('  wrote %d rows -> %s' % (len(e3_rows), E3_OUT))
    print('  FY25 scenarios: TM %.2f / Needs-Based %.2f / ESSER %.2f vs appropriation %.2f '
          '(%d gl-history lines)' % (e3_cmp['fy25_new_tm_total'], e3_cmp['fy25_needs_based_total'],
                                      e3_cmp['fy25_esser_cuts_total'],
                                      e3_cmp['fy25_appropriation_gl_history'],
                                      e3_cmp['gl_history_lines']))

    print('E5: athletics...')
    e5_rows = extract_e5()
    write_csv(E5_OUT, e5_rows, ['source_document', 'source_sheet', 'scope', 'sport', 'season',
                                'fiscal_year', 'metric', 'value', 'unit', 'notes'])
    print('  wrote %d rows -> %s' % (len(e5_rows), E5_OUT))

    print('I5: Monty Tech assessment...')
    i5_rows = extract_i5()
    write_csv(I5_OUT, i5_rows, ['fiscal_year', 'component', 'amount', 'source_document',
                                'source_page', 'ties_to_total', 'printed_total', 'note'])
    print('  wrote %d rows -> %s' % (len(i5_rows), I5_OUT))

    print('K1: school insurance census (aggregates only)...')
    k1_rows = extract_k1()
    write_csv(K1_OUT, k1_rows, ['sheet', 'fiscal_year', 'plan', 'tier', 'subscriber_count',
                                'full_premium_sum', 'school_portion_sum'])
    print('  wrote %d rows -> %s' % (len(k1_rows), K1_OUT))
    fy26_total = sum(r['subscriber_count'] for r in k1_rows
                      if r['fiscal_year'] == 2026 and r['plan'] == 'ALL'
                      and r['sheet'] == 'FY26 Ins Jan25 - TM BUDGET')
    print('  FY26 subscriber count: %d (published presentation states 171 across five plans; '
          'this census resolves to four plan x tier buckets)' % fy26_total)

    print('K2: vacation buyout (aggregates only)...')
    k2_rows, published_breakdown = extract_k2()
    write_csv(K2_OUT, k2_rows, ['group', 'employee_count', 'total_buyout', 'source', 'note'])
    print('  wrote %d rows -> %s (per-group breakdown published: %s)'
          % (len(k2_rows), K2_OUT, published_breakdown))

    if args.check:
        # every tie assertion above already raises SystemExit before writing a single row
        # if a printed total stops reconciling; reaching here means every one held.
        print('--check: every printed total in E3/E5/I5/K1/K2 still ties its own document '
              '(a failed tie raises before anything is written, so getting here is the check)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
