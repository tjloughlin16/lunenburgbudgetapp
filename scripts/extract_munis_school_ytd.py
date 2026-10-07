"""The school department's MUNIS `glytdbud` YTD budget reports, PUBLIC pipeline.

Reads ONLY the 9 published spreadsheets the Town delivered against the 4 September 2026
records request (`sources/town-ledgers/expenses/PROVENANCE-fy2023-fy2026-p13-school.md`):

    sources/town-ledgers/expenses/glytdbud-expense-fy{2023,2024,2025,2026}-p13-gf-school.xlsx
    sources/town-ledgers/expenses/glytdbud-expense-fy{2023,2024,2025,2026}-p13-special-school.xlsx
    sources/town-ledgers/account-details/account-details-fy2026-trial-balance-fund1300.xlsx

Writes:
    sources/data/munis-school-ytd.csv              -- one row per account, all 8 reports
    sources/data/munis-trial-balance.csv            -- fund 1300, one row per account
    sources/data/munis-trial-balance-journal.csv    -- fund 1300, one row per journal line

    python3 scripts/extract_munis_school_ytd.py            # extract, tie, write
    python3 scripts/extract_munis_school_ytd.py --check     # rebuild in memory; fail if
                                                             #   any output on disk differs
                                                             #   or a tie fails; never writes

**The PDFs of these same reports are PRIVATE** (CLAUDE.md 13e) and are never read here --
only the 9 xlsx above. A private script, `extract_munis_xlsx_private.py`, cross-checks
the same workbooks against those PDFs; this file is the one place the parsing itself
lives, and that script imports it.

**Fiscal year and period come from the FILENAME, never from a PDF**, and are
cross-checked against anything the workbook itself states:

  - The eight account-detail workbooks (`glytdbud-expense-...`) state NEITHER their
    fiscal year NOR their period anywhere in the sheet -- confirmed by reading every
    cell of row 1 (the header), the first data rows, the last six rows (the sheet's own
    Total/Grand Total rows) and `wb.properties` (title/subject/description all `None`,
    only `created`/`modified`/`lastModifiedBy` are populated, and `created` is the run
    date, 10/06/2026, not a fiscal year). There is nothing in these particular workbooks
    to cross-check the filename's `fy<YYYY>-p<PP>` against; that absence is itself
    checked below (`header_map` already fails loudly if the sheet shape ever changes).
  - The trial balance workbook DOES state it: cell B5 reads `'2026 Period 1 to 13\\nAll
    Accounts \\n '`. `main()` parses that and refuses to run if it disagrees with the
    filename's `fy2026-p13`.

Two things proven by replaying the arithmetic, not assumed -- both load-bearing for the
trial balance and carried into `notes/reference/SCHEMA.md` as traps:

  1. The journal block's own Debits/Credits/Net Change columns sit ONE COLUMN TO THE LEFT
     of where those fields sit on an account header row (the journal sub-table has no
     Beginning Bal column, so its merged cells are narrower).
  2. Each account carries one journal line with `src='SOY'` ("OPENING BALANCE") whose
     debit minus credit restates that account's own Beginning Bal. The account header's
     own Debits/Credits already EXCLUDE it. It is kept here (flagged, not dropped) and
     excluded from the "journal lines sum to the account's Debits/Credits" tie.
"""
import argparse
import csv
import glob
import hashlib
import io
import os
import re
import sys

import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')

YTD_GLOB = os.path.join(ROOT, 'sources', 'town-ledgers', 'expenses',
                         'glytdbud-expense-fy*-p13-*-school.xlsx')
TB_XLSX = os.path.join(ROOT, 'sources', 'town-ledgers', 'account-details',
                        'account-details-fy2026-trial-balance-fund1300.xlsx')

YTD_OUT = os.path.join(DATA, 'munis-school-ytd.csv')
TB_ACCOUNTS_OUT = os.path.join(DATA, 'munis-trial-balance.csv')
TB_JOURNAL_OUT = os.path.join(DATA, 'munis-trial-balance-journal.csv')

FILENAME_RE = re.compile(
    r'glytdbud-expense-fy(\d{4})-p(\d{2})-(gf|special)-school\.xlsx$')
TB_PERIOD_RE = re.compile(r'(\d{4})\s*Period\s*(\d+)\s*to\s*(\d+)')

# The eight workbooks must cover exactly these (fiscal_year, report) pairs. If the Town
# delivers a ninth year or a missing one shows up, this says so rather than silently
# extracting whatever is on disk.
EXPECTED = {(fy, kind) for fy in (2023, 2024, 2025, 2026)
            for kind in ('gf-school', 'special-school')}

# The account-detail workbook's own header text, stripped. Two forms of the fifth column
# are in use across these eight files ('YTD EXPENDED' on the general-fund reports, '  YTD
# ACTUAL' -- after stripping, 'YTD ACTUAL' -- on the special-funds reports): same field,
# different label, because MUNIS prints 'YTD ACTUAL' wherever a report can show revenue
# rows and 'YTD EXPENDED' where every row is a type-E account. Mapped to one name so both
# reports land in one table.
HEADERS = {
    'FUND': 'fund', 'ORG': 'org', 'OBJ': 'obj', 'PROJECT': 'project',
    'ACCOUNT': 'account', 'ACCOUNT DESCRIPTION': 'description', 'TYPE': 'type',
    'ROLLUP': 'rollup', 'SUB-ROLLUP': 'sub_rollup',
    'ORIGINAL APPROP': 'original_approp', 'TRANFRS/ADJSMTS': 'transfers_adjustments',
    'REVISED BUDGET': 'revised_budget',
    'YTD EXPENDED': 'ytd_expended', 'YTD ACTUAL': 'ytd_expended',
    'ENCUMBRANCES': 'encumbrances', 'AVAILABLE BUDGET': 'available_budget',
    '% USED': 'pct_used',
}
FIGURE_FIELDS = ['original_approp', 'transfers_adjustments', 'revised_budget',
                  'ytd_expended', 'encumbrances', 'available_budget']

YTD_FIELDS = ['fiscal_year', 'period', 'report', 'source', 'fund', 'org', 'obj',
              'project', 'account', 'description', 'type', 'rollup', 'sub_rollup'
              ] + FIGURE_FIELDS + ['pct_used']

TB_HEADER_ROW = 8
# Columns as laid out in the workbook (1-indexed).
TB_COLS = dict(account=2, description=5, org=13, beginning=14, debits=16, credits=18,
               net_change=20, ending=23)
TB_JOURNAL_COLS = dict(period=5, journal=6, src=8, eff_date=10, reference=12,
                        debits=15, credits=17, running_net=19)
# NOT the same as TB_COLS' debits=16/credits=18/net_change=20 -- see the module
# docstring's trap (1).

TB_ACCOUNT_FIELDS = ['source', 'fiscal_year', 'period', 'fund', 'key', 'org', 'account',
                      'description', 'beginning', 'debits', 'credits', 'net_change',
                      'ending']
TB_JOURNAL_FIELDS = ['source', 'fiscal_year', 'key', 'org', 'account', 'period',
                      'journal', 'src', 'is_soy_opening_balance', 'eff_date',
                      'reference', 'debits', 'credits', 'running_balance']


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def header_map(ws):
    head = {}
    for c in range(1, ws.max_column + 1):
        v = ws.cell(1, c).value
        if v is None:
            continue
        key = str(v).strip()
        if key in HEADERS:
            head.setdefault(HEADERS[key], (c, key))
    need = set(HEADERS.values()) - set(head) - {'project', 'rollup', 'sub_rollup'}
    if need:
        raise SystemExit('missing required columns: %s' % ', '.join(sorted(need)))
    return head


def cellnum(ws, r, col):
    v = ws.cell(r, col).value
    if v is None or v == '':
        return 0.0
    return float(v)


def cellstr(ws, r, col):
    v = ws.cell(r, col).value
    return '' if v is None else str(v).strip()


def parse_account_detail(xlsx_path, fy, period, report_kind, source):
    """One workbook -> account rows, plus every level of total the sheet prints itself,
    for tying. Returns (rows, ties, summary, raw_header) where ties is a list of
    (label, ok, detail). Proven against the private PDF-cross-checked extraction; see
    `extract_munis_xlsx_private.py`, which imports this function unchanged."""
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb[wb.sheetnames[0]]
    head = header_map(ws)
    col = {k: v[0] for k, v in head.items()}
    raw_header = {k: v[1] for k, v in head.items()}

    rows = []           # account-level
    org_totals = {}      # org -> dict of figures, from the sheet's own 'Total <org> ...' row
    fund_totals = {}      # fund -> dict of figures, from 'Total <fund> <name>' row
    summary = {}         # 'Revenue Total' / 'Expense Total' / 'Grand Total' -> figures

    for r in range(2, ws.max_row + 1):
        fund = cellstr(ws, r, col['fund'])
        org = cellstr(ws, r, col['org'])
        obj = cellstr(ws, r, col['obj'])
        name = cellstr(ws, r, col['description'])
        if not fund and not org and not obj and not name:
            continue
        figs = {f: cellnum(ws, r, col[f]) for f in FIGURE_FIELDS}
        figs['pct_used'] = cellnum(ws, r, col['pct_used'])

        if name in ('Revenue Total', 'Expense Total', 'Grand Total'):
            summary[name] = figs
            continue
        if name.startswith('Total ') and not fund and org:
            # Rule 13: this IS the sheet's own printed subtotal for this org -- the
            # thing account rows are tied to, not a row to sum into anything else.
            org_totals[org] = figs
            continue
        if name.startswith('Total ') and fund and not org:
            fund_totals[fund] = figs
            continue
        if not fund or not obj:
            # Neither an account row nor a total row this script recognises. Loud, not
            # silent -- rule 13c: a row that does not match a pattern is not nothing.
            raise SystemExit('%s row %d: unrecognised row shape (fund=%r org=%r obj=%r '
                              'name=%r)' % (xlsx_path, r, fund, org, obj, name))
        rows.append(dict(
            fiscal_year=fy, period=period, report=report_kind, source=source,
            fund=fund, org=org, obj=obj,
            project=cellstr(ws, r, col['project']) if 'project' in col else '',
            account=cellstr(ws, r, col['account']),
            description=name,
            type=cellstr(ws, r, col['type']),
            rollup=cellstr(ws, r, col['rollup']) if 'rollup' in col else '',
            sub_rollup=cellstr(ws, r, col['sub_rollup']) if 'sub_rollup' in col else '',
            **figs))

    ties = []

    def cmp_figs(label, got, want, tol=0.01):
        bad = [f for f in FIGURE_FIELDS
               if abs(got.get(f, 0.0) - want.get(f, 0.0)) > tol]
        if bad:
            detail = '; '.join('%s: %.2f vs %.2f' % (f, got[f], want[f]) for f in bad)
            ties.append((label, False, detail))
        else:
            ties.append((label, True, 'ties'))

    # 1. account rows -> the sheet's own per-org Total row.
    by_org = {}
    for row in rows:
        d = by_org.setdefault(row['org'], {f: 0.0 for f in FIGURE_FIELDS})
        for f in FIGURE_FIELDS:
            d[f] += row[f]
    for org, want in org_totals.items():
        got = by_org.get(org, {f: 0.0 for f in FIGURE_FIELDS})
        cmp_figs('org %s' % org, got, want)

    # 2. org totals -> the sheet's own per-fund Total row.
    by_fund = {}
    for org, figs in org_totals.items():
        fund = next((r['fund'] for r in rows if r['org'] == org), None)
        if fund is None:
            continue
        d = by_fund.setdefault(fund, {f: 0.0 for f in FIGURE_FIELDS})
        for f in FIGURE_FIELDS:
            d[f] += figs[f]
    for fund, want in fund_totals.items():
        got = by_fund.get(fund, {f: 0.0 for f in FIGURE_FIELDS})
        cmp_figs('fund %s' % fund, got, want)

    # 3. account rows by TYPE -> Revenue Total / Expense Total.
    by_type = {'R': {f: 0.0 for f in FIGURE_FIELDS}, 'E': {f: 0.0 for f in FIGURE_FIELDS}}
    for row in rows:
        t = row['type']
        if t in by_type:
            for f in FIGURE_FIELDS:
                by_type[t][f] += row[f]
    if 'Revenue Total' in summary:
        cmp_figs('Revenue Total', by_type['R'], summary['Revenue Total'])
    if 'Expense Total' in summary:
        cmp_figs('Expense Total', by_type['E'], summary['Expense Total'])

    # 4. Revenue Total + Expense Total == Grand Total, and the Grand Total == every
    #    account row summed directly (independent of the grouping above).
    if 'Revenue Total' in summary and 'Expense Total' in summary and 'Grand Total' in summary:
        combined = {f: summary['Revenue Total'][f] + summary['Expense Total'][f]
                    for f in FIGURE_FIELDS}
        cmp_figs('Revenue Total + Expense Total vs Grand Total', combined, summary['Grand Total'])
    if 'Grand Total' in summary:
        all_sum = {f: 0.0 for f in FIGURE_FIELDS}
        for row in rows:
            for f in FIGURE_FIELDS:
                all_sum[f] += row[f]
        cmp_figs('sum of all %d account rows vs Grand Total' % len(rows),
                 all_sum, summary['Grand Total'], tol=max(0.01, 0.001 * len(rows)))

    return rows, ties, summary, raw_header


# --- trial balance ---------------------------------------------------------------------

def parse_trial_balance(xlsx_path):
    """Fund 1300 trial balance: one row per GL/budget account with Beginning Bal, Debits,
    Credits, Net Change, Ending Balance, each followed by its own journal lines.

    Returns (accounts, journal, ties, fund_summary, report_total, period_label), where
    `period_label` is the sheet's own B5 text ('2026 Period 1 to 13\\n...') -- the one
    place this workbook states its own fiscal year and period, used by `main()` to
    cross-check the filename.

    THE 'NET CHANGE' COLUMN MEANS TWO DIFFERENT THINGS AT TWO LEVELS OF THIS SHEET, and
    treating them alike would be exactly the kind of derived-quoted-as-observed mistake
    rule 13 warns about:
      - On an ACCOUNT row, Net Change is that account's Debits minus Credits for the
        whole period -- a total, matching Ending - Beginning.
      - On a JOURNAL LINE, Net Change is a RUNNING BALANCE: beginning balance plus every
        debit and minus every credit posted so far, not that line's own debit minus
        credit. Confirmed by replaying it: line 2's figure equals line 1's figure plus
        line 2's debit minus line 2's credit, for the whole account. Summing this column
        would not equal anything the report states; it is not a figure to total.
    """
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb[wb.sheetnames[0]]
    period_label = cellstr(ws, 5, 2)

    accounts = []   # dict per account/GL row
    journal = []    # dict per journal line, tagged with the account it belongs to
    fund_summary = None
    report_total = None
    cur_account = None

    r = 1
    while r <= ws.max_row:
        c2 = ws.cell(r, 2).value
        c5 = ws.cell(r, TB_JOURNAL_COLS['period']).value
        if c2 and re.match(r'^\d{4}', str(c2)) and ws.cell(r, 13).value == '':
            # The one fund-level summary row: Organization blank, account text is the
            # fund's own name ('1300 LOST BOOKS/TECH REV FUND').
            fund_summary = dict(label=str(c2),
                                 beginning=ws.cell(r, TB_COLS['beginning']).value or 0.0,
                                 debits=ws.cell(r, TB_COLS['debits']).value or 0.0,
                                 credits=ws.cell(r, TB_COLS['credits']).value or 0.0,
                                 net_change=ws.cell(r, TB_COLS['net_change']).value or 0.0,
                                 ending=ws.cell(r, TB_COLS['ending']).value or 0.0)
            r += 1
            continue
        if c2 in ('Total', 'Grand Total'):
            if report_total is None:
                report_total = {}
            report_total[c2] = dict(
                beginning=ws.cell(r, TB_COLS['beginning']).value or 0.0,
                debits=ws.cell(r, TB_COLS['debits']).value or 0.0,
                credits=ws.cell(r, TB_COLS['credits']).value or 0.0,
                net_change=ws.cell(r, TB_COLS['net_change']).value or 0.0,
                ending=ws.cell(r, TB_COLS['ending']).value or 0.0)
            r += 1
            continue
        if c2 and re.match(r'^\d{4,}', str(c2)) and ws.cell(r, 13).value not in (None, ''):
            # An account/GL row: 'Accounts' is '<org> <account>', Organization carries
            # the org code, and the five summary figures sit beside it.
            org, acct = (str(c2).split(' ', 1) + [''])[:2]
            cur_account = dict(
                org=cellstr(ws, r, 13), key=str(c2),
                account=acct.strip(), description=cellstr(ws, r, 5),
                beginning=ws.cell(r, TB_COLS['beginning']).value or 0.0,
                debits=ws.cell(r, TB_COLS['debits']).value or 0.0,
                credits=ws.cell(r, TB_COLS['credits']).value or 0.0,
                net_change=ws.cell(r, TB_COLS['net_change']).value or 0.0,
                ending=ws.cell(r, TB_COLS['ending']).value or 0.0)
            accounts.append(cur_account)
            r += 1
            continue
        if c5 == 'Per':
            # The journal column header; the data rows follow immediately.
            r += 1
            continue
        if isinstance(c5, int) and cur_account is not None:
            journal.append(dict(
                org=cur_account['org'], account=cur_account['account'],
                key=cur_account['key'], period=c5,
                journal=cellstr(ws, r, TB_JOURNAL_COLS['journal']),
                src=cellstr(ws, r, TB_JOURNAL_COLS['src']),
                eff_date=ws.cell(r, TB_JOURNAL_COLS['eff_date']).value,
                reference=cellstr(ws, r, TB_JOURNAL_COLS['reference']),
                debits=ws.cell(r, TB_JOURNAL_COLS['debits']).value or 0.0,
                credits=ws.cell(r, TB_JOURNAL_COLS['credits']).value or 0.0,
                running_balance=ws.cell(r, TB_JOURNAL_COLS['running_net']).value or 0.0))
        r += 1

    ties = []
    # Per account: Beginning + Debits - Credits == Ending, and Net Change == Debits - Credits.
    for a in accounts:
        lhs = a['beginning'] + a['debits'] - a['credits']
        if abs(lhs - a['ending']) > 0.01:
            ties.append(('%s beginning+debits-credits=ending' % a['key'], False,
                         '%.2f != %.2f' % (lhs, a['ending'])))
        nc = a['debits'] - a['credits']
        if abs(nc - a['net_change']) > 0.01:
            ties.append(('%s net change' % a['key'], False,
                         '%.2f != %.2f' % (nc, a['net_change'])))
    ties.append(('every account balances (beginning+debits-credits=ending, net=debits-credits)',
                 not any('!=' in t[2] for t in ties), '%d accounts checked' % len(accounts)))

    # One journal line per account, src 'SOY' ('OPENING BALANCE'), restates that
    # account's own Beginning Bal as a transaction -- confirmed by replaying it: its
    # debit minus credit equals the account's Beginning Bal exactly, for every account
    # that has one. The account header's own Debits/Credits columns EXCLUDE it.
    soy_by_key = {}
    for j in journal:
        if j['src'] == 'SOY':
            soy_by_key[j['key']] = j['debits'] - j['credits']
    bad_soy = []
    for a in accounts:
        if a['key'] in soy_by_key and abs(soy_by_key[a['key']] - a['beginning']) > 0.01:
            bad_soy.append('%s: SOY debit-credit %.2f vs Beginning Bal %.2f'
                           % (a['key'], soy_by_key[a['key']], a['beginning']))
    ties.append(("each account's SOY ('OPENING BALANCE') journal line equals its Beginning Bal",
                 not bad_soy, '; '.join(bad_soy) or 'ties, %d accounts had one' % len(soy_by_key)))

    # Per account: its journal lines' debits/credits sum to the account's own totals.
    by_key = {}
    for j in journal:
        if j['src'] == 'SOY':
            continue
        d = by_key.setdefault(j['key'], {'debits': 0.0, 'credits': 0.0})
        d['debits'] += j['debits']
        d['credits'] += j['credits']
    bad = []
    for a in accounts:
        got = by_key.get(a['key'], {'debits': 0.0, 'credits': 0.0})
        if abs(got['debits'] - a['debits']) > 0.01 or abs(got['credits'] - a['credits']) > 0.01:
            bad.append('%s: journal debits %.2f vs account %.2f, credits %.2f vs %.2f'
                       % (a['key'], got['debits'], a['debits'], got['credits'], a['credits']))
    ties.append(('journal lines sum to their account\'s Debits/Credits', not bad,
                 '; '.join(bad) or 'ties, %d journal lines over %d accounts with activity'
                 % (len(journal), len(by_key))))

    # All accounts -> the fund summary row, and the fund summary -> Total/Grand Total.
    total_beg = sum(a['beginning'] for a in accounts)
    total_deb = sum(a['debits'] for a in accounts)
    total_cred = sum(a['credits'] for a in accounts)
    total_net = sum(a['net_change'] for a in accounts)
    total_end = sum(a['ending'] for a in accounts)
    if fund_summary:
        ok = (abs(total_beg - fund_summary['beginning']) <= 0.01
              and abs(total_deb - fund_summary['debits']) <= 0.01
              and abs(total_cred - fund_summary['credits']) <= 0.01
              and abs(total_net - fund_summary['net_change']) <= 0.01
              and abs(total_end - fund_summary['ending']) <= 0.01)
        ties.append(('%d accounts sum to the fund summary row' % len(accounts), ok,
                     'got beg=%.2f deb=%.2f cred=%.2f net=%.2f end=%.2f vs fund row '
                     'beg=%.2f deb=%.2f cred=%.2f net=%.2f end=%.2f'
                     % (total_beg, total_deb, total_cred, total_net, total_end,
                        fund_summary['beginning'], fund_summary['debits'],
                        fund_summary['credits'], fund_summary['net_change'],
                        fund_summary['ending'])))
    if report_total:
        for label in ('Total', 'Grand Total'):
            t = report_total.get(label)
            if not t:
                continue
            ok = (abs(total_beg - t['beginning']) <= 0.01 and abs(total_deb - t['debits']) <= 0.01
                  and abs(total_cred - t['credits']) <= 0.01
                  and abs(total_net - t['net_change']) <= 0.01
                  and abs(total_end - t['ending']) <= 0.01)
            ties.append(('accounts sum to the sheet\'s own %r row' % label, ok, 'ties' if ok
                         else 'mismatch'))

    return accounts, journal, ties, fund_summary, report_total, period_label


def write_csv(fields, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields)
    w.writeheader()
    for row in rows:
        w.writerow(row)
    return buf.getvalue()


def discover_ytd_files():
    paths = sorted(glob.glob(YTD_GLOB))
    plan = []
    for p in paths:
        m = FILENAME_RE.search(os.path.basename(p))
        if not m:
            raise SystemExit('%s: filename does not match '
                              'glytdbud-expense-fy<YYYY>-p<PP>-{gf,special}-school.xlsx'
                              % p)
        fy, period, scope = int(m.group(1)), int(m.group(2)), m.group(3)
        kind = 'gf-school' if scope == 'gf' else 'special-school'
        if period != 13:
            raise SystemExit('%s: expected period 13, filename says p%02d' % (p, period))
        plan.append((p, fy, period, kind))
    got = {(fy, kind) for _, fy, _, kind in plan}
    if got != EXPECTED:
        raise SystemExit('expected ytd workbooks for %s, found %s (missing %s, extra %s)'
                          % (sorted(EXPECTED), sorted(got),
                             sorted(EXPECTED - got), sorted(got - EXPECTED)))
    return plan


def build():
    """Parse every input, tie everything, and return (ytd_rows, tb_accounts, tb_journal,
    all_ties) without writing anything. `all_ties` is a flat list of (source, label, ok,
    detail) across every tie this script checks."""
    all_rows = []
    all_ties = []
    for path, fy, period, kind in discover_ytd_files():
        source = os.path.relpath(path, ROOT)
        rows, ties, _summary, _raw_header = parse_account_detail(path, fy, period, kind, source)
        all_rows.extend(rows)
        for label, ok, detail in ties:
            all_ties.append((source, label, ok, detail))

    if not os.path.exists(TB_XLSX):
        raise SystemExit('missing %s' % os.path.relpath(TB_XLSX, ROOT))
    tb_source = os.path.relpath(TB_XLSX, ROOT)
    accounts, journal, tb_ties, _fund_summary, _report_total, period_label = \
        parse_trial_balance(TB_XLSX)

    m = TB_PERIOD_RE.search(period_label or '')
    if not m:
        raise SystemExit('%s: does not state its own fiscal year/period near B5 '
                          '(expected "<FY> Period 1 to <PP>", got %r)'
                          % (tb_source, period_label))
    stated_fy, _stated_from, stated_to = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if (stated_fy, stated_to) != (2026, 13):
        raise SystemExit('%s states FY%d period 1 to %d; filename says fy2026-p13'
                          % (tb_source, stated_fy, stated_to))

    tb_rows = []
    for a in accounts:
        tb_rows.append(dict(source=tb_source, fiscal_year=2026, period=13, fund='1300',
                             key=a['key'], org=a['org'], account=a['account'],
                             description=a['description'], beginning=a['beginning'],
                             debits=a['debits'], credits=a['credits'],
                             net_change=a['net_change'], ending=a['ending']))
    journal_rows = []
    for j in journal:
        journal_rows.append(dict(source=tb_source, fiscal_year=2026, key=j['key'],
                                  org=j['org'], account=j['account'], period=j['period'],
                                  journal=j['journal'], src=j['src'],
                                  is_soy_opening_balance=1 if j['src'] == 'SOY' else 0,
                                  eff_date=j['eff_date'], reference=j['reference'],
                                  debits=j['debits'], credits=j['credits'],
                                  running_balance=j['running_balance']))
    for label, ok, detail in tb_ties:
        all_ties.append((tb_source, label, ok, detail))

    return all_rows, tb_rows, journal_rows, all_ties


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                     help='rebuild in memory; fail if an output on disk differs or a '
                          'tie fails; never writes')
    args = ap.parse_args()

    ytd_rows, tb_rows, journal_rows, all_ties = build()

    bad = [(s, l, d) for s, l, ok, d in all_ties if not ok]
    print('Extracting the school MUNIS YTD reports and the fund 1300 trial balance\n')
    print('%d YTD account rows, %d trial-balance accounts, %d journal lines'
          % (len(ytd_rows), len(tb_rows), len(journal_rows)))
    print('ties: %d/%d pass' % (len(all_ties) - len(bad), len(all_ties)))
    for source, label, detail in bad:
        print('  FAIL %s :: %s :: %s' % (source, label, detail))

    if bad:
        print('\n%d tie(s) failed; nothing written' % len(bad))
        return 1

    outputs = [
        (YTD_OUT, write_csv(YTD_FIELDS, ytd_rows)),
        (TB_ACCOUNTS_OUT, write_csv(TB_ACCOUNT_FIELDS, tb_rows)),
        (TB_JOURNAL_OUT, write_csv(TB_JOURNAL_FIELDS, journal_rows)),
    ]

    if args.check:
        diffs = []
        for path, content in outputs:
            if not os.path.exists(path):
                diffs.append('%s: does not exist on disk' % os.path.relpath(path, ROOT))
                continue
            on_disk = open(path, newline='', encoding='utf-8').read()
            if on_disk != content:
                diffs.append('%s: on-disk content differs from a fresh rebuild'
                             % os.path.relpath(path, ROOT))
        if diffs:
            print('\n--check: %d output(s) stale:' % len(diffs))
            for d in diffs:
                print('  %s' % d)
            return 1
        print('\n--check: all %d outputs match a fresh rebuild; all ties pass' % len(outputs))
        return 0

    for path, content in outputs:
        with open(path, 'w', newline='', encoding='utf-8') as fh:
            fh.write(content)
        print('wrote %s (%d bytes)' % (os.path.relpath(path, ROOT), len(content)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
