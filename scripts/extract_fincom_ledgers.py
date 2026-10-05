"""Parse the Finance Committee delivery's four school/town ledger reports (A1-A4 of
`sources/data/finance-committee-tasks.csv`) into one normalised CSV.

    python3 scripts/extract_fincom_ledgers.py            # the four reports
    python3 scripts/extract_fincom_ledgers.py --check    # ...and fail if one does not tie,
                                                          # or the CSV is stale

Writes `sources/data/fincom-ledgers.csv`.

Reuses `extract_munis_report.py`'s own primitives (`money()`, the `GRAND` and account-
string regexes, and -- for A4 -- its `ACCOUNT` regex directly) rather than re-deriving
them. These four documents live under `sources/budget-workbooks/finance-committee/`, not
`sources/town-ledgers/`, which is why `extract_munis_report.py` itself never reads them --
it walks one folder on purpose (rule: never hardcode a folder, but also never widen an
existing, working glob to pull in documents it was not written for). Paths are **derived**
from `sources/data/finance-committee-delivery.csv` by the same regex
`sources/data/finance-committee-tasks.csv` states for each task, never hardcoded.

Four documents, four printed shapes -- rule 13c's lesson, paid in full on this delivery:

1.  **A1 (FY24, period 13) and A3a (FY25, period 7) print the SAME three-tier shape**:
    a 4-digit FUND header (bare, or after `ACCOUNTS FOR:`), then a PROJECT line (a code of
    5-8 characters, sometimes `S`-prefixed), then one or more 6-digit OBJECT lines, then a
    values line. The only way to tell a PROJECT line from an OBJECT line -- both can be a
    bare 6-digit code followed by text -- is to look at the line AFTER it: an object is
    followed by six numbers, a project by another code line. Digit-count alone cannot do
    it; a 4-digit code is reserved for a fund in both documents by observation (checked:
    never found immediately followed by a value line), so that length is treated as fund
    on sight.

2.  **Which of FUND or DEPARTMENT is the outer loop differs between the two, and it
    changes what "the fund's own total" means.** A1's `ACCOUNTS FOR:` carries the
    DEPARTMENT (300, then 301), and each department prints its OWN "TOTAL GENERAL FUND"
    -- fund 0100 is totalled twice, once per department, and the two totals do not add
    the same way a reader might guess (17,686.00 is the whole of dept 301's fund-0100
    slice, not a rounding slip against dept 300's 22,883,442.00). A3a's `ACCOUNTS FOR:`
    carries the FUND instead, and department is the nested loop, so fund 0100's one total
    spans BOTH of its departments. Tying "by fund name" alone would silently merge A1's
    two same-named totals into one wrong number. The fix used here needs no department
    tracking at all: bucket by FUND **RUN** -- a new bucket starts only when the fund
    value itself changes, so two separated appearances of 0100 (A1) get different
    buckets and one continuous appearance (A3a) keeps one. A lower-level subtotal
    ("TOTAL SCHOOL DEPARTMENT", "TOTAL REVENUES", "TOTAL EXPENSES", "GRAND TOTAL") is
    recognised by matching the printed label against the department name in scope (or
    the fixed set of report-level labels) and excluded from the fund-run total, so the
    last total line actually belonging to a fund is the one checked.

3.  **A2 (FY23, period 12) prints the full dashed account string** on the account's own
    line (`0100-3-300-4220-01-1-74-2-535006`), values on the next -- the twin of
    `extract_munis_report.py`'s own `ACCOUNT_STRING`/xlsx path, just typed into the PDF
    text instead of a spreadsheet cell. Its options page declares no `Account type` at
    all; the filter that actually scoped it to expenses is `Object  5*` on the Find
    Criteria page, read directly rather than guessed.

4.  **A3b (the Sept-2024 NB-Action district report) prints the account string AND its
    six values on ONE line, with no `%` on the percentage** -- and at first pass looked
    like it carried no total anywhere (a case-sensitive `grep TOTAL` finds nothing). It
    is not an absence: the report prints `Total 0100 GENERAL FUND ...`, mixed case,
    which is rule 13c by name -- a pattern that does not match is not an absence; the
    page had to be read again before this ties. Two account lines were also found
    jammed object-code-to-description with no space (`535006CONTRACTED SERVICES`,
    the same run-on `extract_munis_report.py`'s own docstring warns about), and one row
    prints a cent value with a single decimal digit (`34164.8`, not `34164.80`) -- a
    fact about this report's own export, not a parsing choice; both are handled without
    inventing a digit.

    This document states its fiscal year only in prose, once, as a page footer
    (`FY 25 LUNENBURG PUBLIC SCHOOLS QUARTERLY BUDGET REPORT`) and never states a period
    number anywhere on any of its seven pages. Rather than infer one from the filename
    (`...91224...`, plausibly 9/12/24) -- which would be exactly the derived-quoted-as-
    observed error rule 13 exists to stop -- every A3b row carries `period=unstated`.
    That value can never be mistaken for a year-end period (12 or 13), which is what the
    task's done_when actually requires.

5.  **A4 (FY25, period 12, town general-fund revenue) matches `extract_munis_report.py`'s
    own `ACCOUNT` regex verbatim** -- org/object/name/six-values/pct on one joined line,
    exactly the shape that regex was written for. It is parsed by calling that regex
    directly, not a reimplementation. Revenue is printed as a credit (negative); the sign
    is kept exactly as printed, matching that script's own first rule.

Every report here is reconciled to its own printed total before anything is written, and
the run refuses to write ANY output if one does not tie -- there is no partial-exclusion
path, because across these five source files every one of them ties, and a silent partial
write is a worse failure mode than a loud refusal while this stays true.
"""
import argparse
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import extract_munis_report as munis  # noqa: E402  (reuse money(), GRAND, ACCOUNT, NUM)

OUT = os.path.join(ROOT, 'sources', 'data', 'fincom-ledgers.csv')
TASKS_CSV = os.path.join(ROOT, 'sources', 'data', 'finance-committee-tasks.csv')
DELIVERY_CSV = os.path.join(ROOT, 'sources', 'data', 'finance-committee-delivery.csv')

FIELDS = ['report_key', 'fiscal_year', 'period', 'fund', 'fund_name', 'org', 'object',
          'account', 'description', 'original', 'transfers', 'revised', 'ytd_actual',
          'encumbrances', 'available', 'account_type']

money = munis.money


def num_re(n):
    return r'\s+'.join('(%s)' % munis.NUM for _ in range(n))


VALUES6 = re.compile(r'^\s*' + num_re(6))
FUND_BARE = re.compile(r"^(\d{4})\s+([A-Z][A-Z0-9 /&'\".,#()-]*?)\s*$")
DEPT_BARE = re.compile(r"^(\d{3})\s+([A-Z][A-Z0-9 /&'\".,#()-]*?)\s*$")
ACCOUNTS_FOR = re.compile(r"^ACCOUNTS FOR:\s*(\d+)?\s*([A-Z][^\n]*?)?\s*$")
CODE_LINE = re.compile(r"^([A-Z]?\d{4,8})\s+([A-Z0-9][^\n]*?)\s*$")
FOR_HDR = re.compile(r'^\s*FOR\s+(\d{4})\s+(\d{2})\b', re.MULTILINE)
PAGE_MARK = re.compile(r'^===PAGE (\d+)===$')
TOTAL_LINE = re.compile(r'^\s*(TOTAL|GRAND TOTAL)\b(.*)$')
# The full dashed MUNIS account string: fund-?-dept-FUNC-?-?-?-?-object (rule 13's own
# comment on extract_munis_report.ACCOUNT_STRING; this is the whole thing, not the prefix).
ACCOUNT_FULL = re.compile(r'^(\d{4}-\d-\d{3}-\d{4}-\d{2}-\d-\d{2}-\d-(\d{6}))\s*(.*)$')
# A3b's own number shape allows ONE decimal digit (observed: `34164.8`), not just two.
A3B_NUM = r'-?[\d,]*\.\d{1,2}|-?[\d,]+'


def _num_re_custom(pattern, n):
    return r'\s+'.join('(%s)' % pattern for _ in range(n))


A3B_VALUES6 = re.compile(r'^\s*' + _num_re_custom(A3B_NUM, 6))
A3B_LINE = re.compile(r'^(\d{4}-\d-\d{3}-\d{4}-\d{2}-\d-\d{2}-\d-(\d{6}))\s*(.+?)\s+'
                       + _num_re_custom(A3B_NUM, 6) + r'\s+-?[\d.]+\s*$')
A3B_TOTAL = re.compile(r'^Total\s+(.+?)\s+' + _num_re_custom(A3B_NUM, 6) + r'\s+-?[\d.]+\s*$',
                        re.IGNORECASE)

TOL_ROUNDED = ('original', 'transfers', 'revised')
COLS = ('original', 'transfers', 'revised', 'ytd_actual', 'encumbrances', 'available')


def account_type_of(object_code):
    """4xxxxx = revenue, 5xxxxx = expense -- the only two prefixes ever observed on a
    real leaf object across these five documents (checked, not assumed: every object
    code this script emits was printed immediately above a values line)."""
    d = object_code[0]
    if d == '4':
        return 'revenue'
    if d == '5':
        return 'expense'
    raise ValueError('object %r starts with unrecognised digit %r' % (object_code, d))


def check_tie(got, want):
    notes = []
    ok = True
    for i, c in enumerate(COLS):
        tol = 1.0 if c in TOL_ROUNDED else 0.005
        d = abs(got[i] - want[i])
        if d > tol:
            ok = False
            notes.append('%s: %.2f vs stated %.2f' % (c, got[i], want[i]))
    return ok, ('; '.join(notes) if notes else 'ties')


# --------------------------------------------------------------------------- A1 / A3a ---

def parse_hierarchical(path, report_key, fiscal_year, period):
    """Fund > project > object > values, with fund-RUN bucketing (see module docstring
    point 2) and dept/report-level total lines excluded by label match."""
    lines = open(path, encoding='utf-8', errors='replace').read().split('\n')
    n = len(lines)
    page = 1
    cur_dept_name = None
    cur_fund, cur_fund_name = None, None
    cur_org = None
    fund_run_id = -1
    rows = []
    fund_totals = {}       # (fund_run_id, fund) -> (page, vals)   [last one wins]
    grand = None
    i = 0

    def set_fund(code, name):
        nonlocal cur_fund, cur_fund_name, fund_run_id
        if code != cur_fund:
            fund_run_id += 1
        cur_fund, cur_fund_name = code, name

    def is_boiler(l):
        s = l.strip()
        return (l.startswith('TOWN OF LUNENBURG') or l.startswith('Report generated') or
                l.startswith('User:') or l.startswith('Program ID') or
                s.startswith('Page') or
                ('APPROP' in l and ('TRANFRS' in l or 'ADJSMTS' in l or 'ADJSTMTS' in l)) or
                s == '' or '** END OF REPORT' in l or
                s.startswith('YTD BUDGET REPORT') or
                s.startswith('YEAR-TO-DATE BUDGET REPORT') or
                s.startswith('GENERAL FUND REPORT'))

    while i < n:
        l = lines[i]
        pm = PAGE_MARK.match(l)
        if pm:
            page = int(pm.group(1)); i += 1; continue
        if is_boiler(l):
            i += 1; continue
        if FOR_HDR.match(l):
            i += 1; continue
        af = ACCOUNTS_FOR.match(l)
        if af:
            code, name = af.group(1), (af.group(2) or '').strip()
            if code and len(code) == 4:
                set_fund(code, name)
            elif code and len(code) == 3:
                cur_dept_name = name
            i += 1; continue
        tl = TOTAL_LINE.match(l)
        if tl:
            label, rest = tl.group(1), tl.group(2)
            vm = VALUES6.match(rest)
            if vm:
                vals = [money(vm.group(k)) for k in range(1, 7)]
            else:
                vm2 = VALUES6.match(lines[i + 1]) if i + 1 < n else None
                if vm2:
                    vals = [money(vm2.group(k)) for k in range(1, 7)]
                    i += 1
                else:
                    vals = None
            if vals is not None:
                text_label = rest.strip()
                if label == 'GRAND TOTAL':
                    grand = vals
                elif text_label in ('REVENUES', 'EXPENSES'):
                    pass
                elif cur_dept_name and (text_label == cur_dept_name or
                                         cur_dept_name.startswith(text_label) or
                                         text_label.startswith(cur_dept_name)):
                    pass  # a department-level subtotal, not a fund total
                else:
                    fund_totals[(fund_run_id, cur_fund)] = (page, vals)
            i += 1; continue
        fb = FUND_BARE.match(l)
        if fb:
            set_fund(fb.group(1), fb.group(2).strip())
            i += 1; continue
        db = DEPT_BARE.match(l)
        if db:
            cur_dept_name = db.group(2).strip()
            i += 1; continue
        cl = CODE_LINE.match(l)
        if cl:
            code, desc = cl.group(1), cl.group(2).strip()
            if re.match(r'^\d{4}$', code):
                set_fund(code, desc)
                i += 1; continue
            nxt = lines[i + 1] if i + 1 < n else ''
            vm = VALUES6.match(nxt)
            if vm:
                vals = [money(vm.group(k)) for k in range(1, 7)]
                rows.append(dict(
                    report_key=report_key, fiscal_year=fiscal_year, period=period,
                    fund=cur_fund, fund_name=cur_fund_name, org=cur_org, object=code,
                    account='', description=desc, original=vals[0], transfers=vals[1],
                    revised=vals[2], ytd_actual=vals[3], encumbrances=vals[4],
                    available=vals[5], account_type=account_type_of(code),
                    _fund_run=(fund_run_id, cur_fund), _page=page))
                i += 2; continue
            else:
                cur_org = code
                i += 1; continue
        # An orphaned values-only line (a total's figures pushed onto the next page by
        # a page break) or other boilerplate we don't need -- never a data row, since a
        # data row is only ever emitted from the CODE_LINE branch above.
        i += 1

    sums = {}
    for r in rows:
        key = r['_fund_run']
        s = sums.setdefault(key, [0.0] * 6)
        for i2, c in enumerate(COLS):
            s[i2] += r[c]
    fund_ties = []
    for key, s in sums.items():
        ft = fund_totals.get(key)
        if ft is None:
            fund_ties.append((key, None, s, False, 'no fund total line found'))
            continue
        page_n, vals = ft
        ok, note = check_tie(s, vals)
        fund_ties.append((key, page_n, s, ok, note))

    grand_ok, grand_note = (None, 'no GRAND TOTAL printed')
    if grand is not None:
        total = [0.0] * 6
        for r in rows:
            for i2, c in enumerate(COLS):
                total[i2] += r[c]
        grand_ok, grand_note = check_tie(total, grand)

    for r in rows:
        del r['_fund_run'], r['_page']
    return rows, fund_ties, (grand, grand_ok, grand_note)


# --------------------------------------------------------------------------------- A2 ---

def parse_account_twoline(path, report_key):
    text = open(path, encoding='utf-8', errors='replace').read()
    per = munis.PERIOD.search(text)
    if not per:
        raise SystemExit('%s: no Year/Period: on its options page' % path)
    fy, period = int(per.group(1)), int(per.group(2))
    fh = FOR_HDR.search(text)
    if fh and (int(fh.group(1)), int(fh.group(2))) != (fy, period):
        raise SystemExit('%s: FOR header %s disagrees with Year/Period %s'
                          % (path, fh.groups(), per.groups()))
    fund_m = re.search(r'^Fund\s+(\S+)\s*$', text, re.MULTILINE)
    fund = fund_m.group(1) if fund_m else None
    if not fund or '|' in fund:
        raise SystemExit('%s: Find Criteria Fund is not a single value (%r)'
                          % (path, fund))

    lines = text.split('\n')
    rows = []
    i, n = 0, len(lines)
    while i < n:
        m = ACCOUNT_FULL.match(lines[i])
        if m:
            acct, obj, desc = m.group(1), m.group(2), m.group(3).strip()
            nxt = lines[i + 1] if i + 1 < n else ''
            vm = VALUES6.match(nxt)
            if vm:
                vals = [money(vm.group(k)) for k in range(1, 7)]
                rows.append(dict(
                    report_key=report_key, fiscal_year=fy, period=period,
                    fund=fund, fund_name='GENERAL FUND' if fund == '0100' else '',
                    org='', object=obj, account=acct, description=desc,
                    original=vals[0], transfers=vals[1], revised=vals[2],
                    ytd_actual=vals[3], encumbrances=vals[4], available=vals[5],
                    account_type=account_type_of(obj)))
                i += 2; continue
        i += 1

    g = munis.GRAND.search(text)
    grand = [money(g.group(k)) for k in range(1, 7)] if g else None
    grand_ok, grand_note = (None, 'no GRAND TOTAL printed')
    if grand is not None:
        total = [0.0] * 6
        for r in rows:
            for i2, c in enumerate(COLS):
                total[i2] += r[c]
        grand_ok, grand_note = check_tie(total, grand)
    # Single fund, single run: the fund tie and the grand tie are the same check.
    fund_ties = [((0, fund), None, None, grand_ok, grand_note)]
    return rows, fund_ties, (grand, grand_ok, grand_note)


# --------------------------------------------------------------------------------- A4 ---

def parse_joined_oneline(path, report_key, fund, fund_name, account_type):
    """A4's shape matches extract_munis_report.ACCOUNT verbatim; call it directly."""
    text = open(path, encoding='utf-8', errors='replace').read()
    fh = FOR_HDR.search(text)
    if not fh:
        raise SystemExit('%s: no "FOR <fy> <period>" header found' % path)
    fy, period = int(fh.group(1)), int(fh.group(2))

    rows = []
    for m in munis.ACCOUNT.finditer(text):
        vals = [money(m.group(k)) for k in range(4, 10)]
        obj = m.group(2)
        rows.append(dict(
            report_key=report_key, fiscal_year=fy, period=period,
            fund=fund, fund_name=fund_name, org=m.group(1), object=obj, account='',
            description=m.group(3).strip(), original=vals[0], transfers=vals[1],
            revised=vals[2], ytd_actual=vals[3], encumbrances=vals[4], available=vals[5],
            account_type=account_type))

    g = munis.GRAND.search(text)
    grand = [money(g.group(k)) for k in range(1, 7)] if g else None
    grand_ok, grand_note = (None, 'no GRAND TOTAL printed')
    if grand is not None:
        total = [0.0] * 6
        for r in rows:
            for i2, c in enumerate(COLS):
                total[i2] += r[c]
        grand_ok, grand_note = check_tie(total, grand)
    fund_ties = [((0, fund), None, None, grand_ok, grand_note)]
    return rows, fund_ties, (grand, grand_ok, grand_note)


# -------------------------------------------------------------------------------- A3b ---

def parse_account_flat_oneline(path, report_key, fiscal_year):
    text = open(path, encoding='utf-8', errors='replace').read()
    lines = text.split('\n')
    rows = []
    for l in lines:
        s = l.strip()
        if not s or l.startswith('===PAGE') or s.startswith('ACCOUNT ') or s.startswith('FY '):
            continue
        m = A3B_LINE.match(l)
        if not m:
            continue
        acct, obj, desc = m.group(1), m.group(2), m.group(3).strip()
        vals = [money(m.group(k)) for k in range(4, 10)]
        rows.append(dict(
            report_key=report_key, fiscal_year=fiscal_year, period='unstated',
            fund=acct[:4], fund_name='GENERAL FUND' if acct[:4] == '0100' else '',
            org='', object=obj, account=acct, description=desc,
            original=vals[0], transfers=vals[1], revised=vals[2], ytd_actual=vals[3],
            encumbrances=vals[4], available=vals[5], account_type=account_type_of(obj)))

    totals = {}
    for l in lines:
        t = A3B_TOTAL.match(l)
        if t:
            vals = [money(t.group(k)) for k in range(2, 8)]
            totals[t.group(1).strip()] = vals
    # Single fund in this document (0100 GENERAL FUND); its one printed total is both
    # the fund total and this report's grand total.
    grand = totals.get('0100 GENERAL FUND')
    grand_ok, grand_note = (None, 'no total printed')
    if grand is not None:
        total = [0.0] * 6
        for r in rows:
            for i2, c in enumerate(COLS):
                total[i2] += r[c]
        grand_ok, grand_note = check_tie(total, grand)
    fund_ties = [((0, '0100'), None, None, grand_ok, grand_note)]
    return rows, fund_ties, (grand, grand_ok, grand_note)


# -------------------------------------------------------------------------- discovery ---

def load_tasks():
    with open(TASKS_CSV, newline='', encoding='utf-8') as f:
        return {row['id']: row for row in csv.DictReader(f)}


def load_delivery():
    with open(DELIVERY_CSV, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def resolve(task_id, tasks, delivery):
    """Find the delivered, filed path(s) for a task's `documents` regex -- never a
    hardcoded path. Returns a list of (key, text_path)."""
    pattern = re.compile(tasks[task_id]['documents'])
    out = []
    for row in delivery:
        if row['disposition'] != 'filed':
            continue
        if not pattern.search(row['delivered_as']):
            continue
        key = row['key']
        pdf_path = os.path.join(ROOT, 'sources', key)
        text_path = os.path.join(os.path.dirname(pdf_path), 'text',
                                  os.path.basename(pdf_path) + '.txt')
        if not os.path.exists(text_path):
            raise SystemExit('%s: matched %s but no extracted text at %s'
                              % (task_id, key, text_path))
        out.append((key, text_path))
    if not out:
        raise SystemExit('%s: documents pattern %r matched nothing in %s'
                          % (task_id, tasks[task_id]['documents'], DELIVERY_CSV))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    tasks = load_tasks()
    delivery = load_delivery()

    all_rows = []
    failures = []

    def report(task_id, doc_label, key, rows, fund_ties, grand_info):
        grand, grand_ok, grand_note = grand_info
        print('\n%s (%s)' % (task_id, doc_label))
        print('  %s' % key)
        print('  %d rows' % len(rows))
        bad_funds = 0
        for fkey, page, sums, ok, note in fund_ties:
            if not ok:
                bad_funds += 1
                where = (' (page %s)' % page) if page else ''
                print('  FUND %s%s: MISMATCH %s' % (fkey, where, note))
        if bad_funds == 0:
            print('  every fund section ties (%d fund run(s))' % len(fund_ties))
        else:
            print('  %d of %d fund run(s) do NOT tie' % (bad_funds, len(fund_ties)))
        print('  report total: %s' % grand_note)
        ok_overall = (bad_funds == 0) and (grand_ok is True)
        if not ok_overall:
            failures.append((task_id, key, bad_funds, grand_ok, grand_note))
        return ok_overall

    # A1 -- FY24 year-end (period 13), school, every fund.
    for key, path in resolve('A1', tasks, delivery):
        rows, fund_ties, grand_info = parse_hierarchical(path, key, 2024, 13)
        ok = report('A1', 'FY24 school year-end, every fund', key, rows, fund_ties, grand_info)
        if ok:
            all_rows.extend(rows)

    # A2 -- FY23, period 12, school (fund 0100 only, filtered to expense objects).
    for key, path in resolve('A2', tasks, delivery):
        rows, fund_ties, grand_info = parse_account_twoline(path, key)
        ok = report('A2', 'FY23 school, period 12', key, rows, fund_ties, grand_info)
        if ok:
            all_rows.extend(rows)

    # A3 -- FY25 part-year, two documents, two different shapes.
    for key, path in resolve('A3', tasks, delivery):
        if 'school-fy25-ytd-budget-report' in path.lower():
            rows, fund_ties, grand_info = parse_hierarchical(path, key, 2025, 7)
            ok = report('A3', 'FY25 school, period 7 (July-January), PART-YEAR',
                         key, rows, fund_ties, grand_info)
        else:
            rows, fund_ties, grand_info = parse_account_flat_oneline(path, key, 2025)
            ok = report('A3', 'FY25 school, period UNSTATED (Sept 2024 per task), '
                         'PART-YEAR', key, rows, fund_ties, grand_info)
        if ok:
            all_rows.extend(rows)

    # A4 -- FY25, period 12, town general fund revenue.
    for key, path in resolve('A4', tasks, delivery):
        rows, fund_ties, grand_info = parse_joined_oneline(
            path, key, '0100', 'GENERAL FUND', 'revenue')
        ok = report('A4', 'FY25 town general fund revenue, period 12', key, rows,
                     fund_ties, grand_info)
        if ok:
            all_rows.extend(rows)

    if failures:
        print('\n%d report(s) do not reconcile; REFUSING to write %s:' % (len(failures), OUT))
        for task_id, key, bad_funds, grand_ok, grand_note in failures:
            print('  %s %s: %d fund mismatch(es); report total %s'
                  % (task_id, key, bad_funds, grand_note))
        return 1

    stale = False
    if args.check and os.path.exists(OUT):
        with open(OUT, newline='', encoding='utf-8') as f:
            existing = f.read()
        fresh = _render(all_rows)
        if existing != fresh:
            print('\n%s is stale: re-derived output differs from what is on disk' % OUT)
            stale = True

    if not args.check or not os.path.exists(OUT):
        with open(OUT, 'w', newline='', encoding='utf-8') as f:
            f.write(_render(all_rows))
        print('\nwrote %s -- %d rows' % (os.path.relpath(OUT, ROOT), len(all_rows)))
    elif not stale:
        print('\n%s is current -- %d rows' % (os.path.relpath(OUT, ROOT), len(all_rows)))

    return 1 if stale else 0


def _render(rows):
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS)
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


if __name__ == '__main__':
    sys.exit(main())
