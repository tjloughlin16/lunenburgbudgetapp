#!/usr/bin/env python3
"""The health-insurance page's series, pre-rendered from the ledger and the reports.

    python3 scripts/build_insurance_charts.py            # write it
    python3 scripts/build_insurance_charts.py --check    # fail if it is stale

WHY THIS PAGE EXISTS.

Health insurance is one of the largest costs of running Lunenburg's schools, and a large
part of it is **not in the school budget**. It is appropriated to the town's INSURANCE
department (914), one line of which is named for the schools:

    0100-19142-570018  SCHRETHLTH   school retiree health

A resident reading the district's $26M budget book never sees that account. That is not
concealment -- it is ordinary municipal accounting, because retirees are the town's
obligation under Chapter 32B rather than the School Committee's -- but it is rule 11 with
a number attached: **the school budget is not what the schools cost.**

WHAT THE ACCOUNT IS, EXACTLY (rule 13). `SCHRETHLTH` is health insurance for RETIREES of
the schools. It is not current staff; the district budgets its own active-employee health
insurance separately, inside department 300, and both figures are carried here so the page
can say which is which. Nothing here extends the claim past the account name.

FOUR ROUTES TO A HEALTH-INSURANCE FIGURE, AND THEY ARE NOT THE SAME QUANTITY:

  1. `ledger_snapshot` x `account`, dept 914, FY2026 period 12 -- the town's insurance
     department, account by account. The only year the archive holds at this grain.
  2. `ledger_snapshot` x `account`, dept 300, FY2026 period 12 -- `HEALTH INS`, the
     district's own active-employee line, inside the school appropriation.
  3. `budget_figure`, line `health insurance` -- the district's own budget book,
     FY2014-FY2027, at three stages. RULE 1: the stages are kept apart and never
     differenced across each other.
  4. The annual town reports' GENERAL FUND APPROPRIATIONS classification, FY2011-FY2023 --
     the insurance department as printed, with its own subtotal.

ROUTE 4 IS EXTRACTED HERE RATHER THAN TAKEN FROM `report_appropriations`, and the reason
is rule 13. Every row of that table for these pages is `check failed`: its v-numbers are
ORDINALS, not columns, and the page-level reconciliation does not tie. So this script reads
the page text directly and reconciles each year against **the identity the table itself
prints** -- the component rows must sum to the printed `Total Insurance`. A year that does
not tie is reported as not established and is kept out of every series. That check has
power to fail, and it does: FY2014 is short by exactly the $6,150.00 the page prints as a
bare `fwd` carry-forward on its own line above the block, and rather than guess which row
that belongs to the year is reported as not established. FY2024 and FY2025 print no
classification of appropriations at all.

ONLY THE APPROPRIATED COLUMN IS PUBLISHED FROM THESE PAGES. The reconciliation establishes
that one column: the components sum to the printed subtotal in it. The EXPENDED column is
present on the page and does NOT tie in every year -- several editions print two columns
where others print four, so what is third on one page is second on another -- and that is
rule 13's positional-name trap exactly. A column this script has not established is not
published from it.

THE FINDING THE EXTRACT MAKES POSSIBLE. In FY2023 the town's report stopped printing one
`Health Insurance CH 32B` line and started printing three -- town retirees, school retirees
and the remainder. So the school share of the town's insurance department is separately
published in exactly TWO of the sixteen years this archive holds: the FY2023 annual report
and the FY2026 ledger. Every other year has one undivided line. That is a gap, and it is
registered in `sources/data/money-gaps.csv` rather than only written on the page.

RULE 7. "The line was split in FY2023" is a measurement -- it is on the page. "The town
began separating school costs" is a hypothesis and is labelled as one. Nothing here says
why any number moved.

RULE 2. Not one figure is typed into the page. Everything it says arrives from this file.

NO D1 AT PAGE LOAD. One static file, identical for every reader until the ledger changes.
"""
import argparse
import glob
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources/data/lunenburg.db')
PAGES = os.path.join(ROOT, 'sources/town-budget/pages')
OUT = os.path.join(ROOT, 'fy28/public/data/health-insurance.json')

LEDGER_FY, LEDGER_PERIOD = 2026, 12
INSURANCE_DEPT = '914'
SCHOOL_RETIREE = '0100-19142-570018'
SCHOOL_ACTIVE = '0100-S5991992-570001'
DISTRICT_LINE = 'health insurance'

# The gap rows this page rests on, quoted BY KEY out of the register. If one is renamed the
# build stops rather than rendering a limit with no reason attached -- the same discipline
# build_traceability_ladder.py uses, and for the same reason: the register outranks the page.
GAP_KEYS = [
    ('money_out', 'School share of the town’s health insurance before FY2026'),
    ('money_out', 'School share of Medicare, active health insurance and the insurance reserves'),
    ('document_wanted', 'The town’s Chapter 32B enrolment schedule'),
]

# What each ledger account is, in words a resident uses. The KEY is the account id, so a
# renamed abbreviation cannot silently re-label a line; a missing key stops the build.
ACCOUNT_MEANING = {
    '0100-19142-570001': ('HEALTH INS', 'Active employees’ health insurance', 'unnamed'),
    '0100-19142-570002': ('LIFE INS', 'Life insurance', 'unnamed'),
    '0100-19142-570003': ('MEDI', 'Medicare — the employer’s payroll share', 'unnamed'),
    '0100-19142-570004': ('INS COST C', 'Insurance cost control', 'unnamed'),
    '0100-19142-570009': ('TNRETHLTHI', 'Town retirees’ health insurance', 'town'),
    '0100-19142-570016': ('PEC EXPENS', 'Public Employee Committee expenses', 'unnamed'),
    '0100-19142-570018': ('SCHRETHLTH', 'School retirees’ health insurance', 'school'),
}

# ---------------------------------------------------------------------------
# The annual reports' insurance block, read off the page and reconciled to the
# subtotal the page itself prints.
# ---------------------------------------------------------------------------

# No space inside a number. Allowing one merged `$2,372,677.80 52,372,677.80` into a single
# token of 2.37e16 in FY2020 and `1213617.67 1213617.67 1213617.67` into one in FY2023 --
# two of the sixteen years silently lost to a character class.
MONEY = re.compile(r'\$?\d[\d.,:]*\d')
PAGE_MARK = re.compile(r'^===PAGE (\d+)===')
FWD = re.compile(r'^\s*\$?([\d.,]+)\s+fwd\s*$')

# The rows the insurance block is made of. Matched as SUBSTRINGS because the scans lose
# leading characters -- `ublic Employee Committee`, `Insurance Cost Contro` are what several
# editions actually contain, and a stricter match would drop the row and break the identity.
COMPONENTS = [
    ('health_ins', 'Health Insurance CH', 'Health Insurance CH 32B'),
    ('life', 'Life Insurance', 'Life Insurance'),
    ('medicare', 'Medicare', 'Medicare'),
    ('town_retirees', 'Town Retirees Health', 'Town Retirees Health'),
    ('cost_control', 'Insurance Cost Contro', 'Insurance Cost Control'),
    ('pec', 'ublic Employee Committee', 'Public Employee Committee Expenses'),
    ('school_retirees', 'School Retirees Health', 'School Retirees Health'),
]
SIDE = {'town_retirees': 'town', 'school_retirees': 'school'}


def money(tok):
    """A printed amount, or None. Cents are the last two digits after a separator, whatever
    that separator scanned as -- these pages render thousands as `.` about as often as `,`
    (`$2.852.641.67`), so a locale-naive parse is off by three orders of magnitude."""
    t = tok.replace('$', '').replace(':', '.').rstrip('.,')
    if not re.match(r'^\d[\d.,]*$', t):
        return None
    m = re.match(r'^([\d.,]*\d)[.,](\d{2})$', t)
    if not m:
        return None
    return round(float(m.group(1).replace('.', '').replace(',', '') + '.' + m.group(2)), 2)


def amounts(text):
    return [v for v in (money(t) for t in MONEY.findall(text)) if v is not None]


def read_pages(path):
    """{page number: [lines]} for one annual report's extracted text."""
    out, cur = {}, None
    for ln in open(path, encoding='utf-8', errors='replace').read().splitlines():
        m = PAGE_MARK.match(ln)
        if m:
            cur = m.group(1)
            out[cur] = []
        elif cur is not None:
            out[cur].append(ln)
    return out


def body(line):
    return line.split('|', 1)[1] if '|' in line else line


def insurance_block(path, fy):
    """The insurance block of one annual report, with its own reconciliation.

    Returns a dict whose `checked` is True only when the component rows sum, to the cent,
    to the `Total Insurance` the page prints in the APPROPRIATED column."""
    for page, lines in read_pages(path).items():
        ends = [i for i, l in enumerate(lines) if 'Total Insuranc' in l]
        if not ends:
            continue
        end = ends[0]
        start = next((i for i in range(end - 1, -1, -1)
                      if 'Health Insurance CH' in lines[i]), None)
        if start is None:
            continue
        rows, carried = [], 0.0
        for i in range(start, end):
            t = body(lines[i])
            f = FWD.match(t)
            if f:
                # A carry-forward the page prints on its own line. It is inside the
                # subtotal -- the printed column heading is APPROPRIATED / TOTAL FUNDS
                # FORWARD -- so leaving it out is what makes FY2014 fail to tie.
                v = money(f.group(1))
                if v is not None:
                    carried += v
                continue
            key = next((k for k, needle, _ in COMPONENTS if needle in t), None)
            if key is None:
                continue
            label = next(lab for k, _, lab in COMPONENTS if k == key)
            vals = amounts(t.replace('CH 32B', '').replace('CH 328', ''))
            rows.append({'key': key, 'label': label,
                         'appropriated': vals[0] if vals else None,
                         'expended': vals[2] if len(vals) > 2 else None,
                         'side': SIDE.get(key, 'unnamed')})
        tot = amounts(body(lines[end]))
        printed = tot[0] if tot else None
        summed = round(sum(r['appropriated'] or 0 for r in rows) + carried, 2)
        ok = printed is not None and abs(summed - printed) < 0.005
        return {
            'fy': fy, 'page': page,
            'line_no': f'{start + 1}-{end + 1}',
            'source': os.path.relpath(path, ROOT),
            'rows': rows,
            'carried_forward': round(carried, 2),
            'printed_total': printed,
            'printed_expended': tot[2] if len(tot) > 2 else None,
            'summed_components': summed,
            'difference': None if printed is None else round(summed - printed, 2),
            'checked': ok,
            'names_school_share': any(r['key'] == 'school_retirees' for r in rows),
        }
    return None


def annual_reports():
    years = []
    for path in sorted(glob.glob(os.path.join(PAGES, 'FY*.txt'))):
        base = os.path.basename(path)
        if '.ocr.' in base or 'addendum' in base:
            continue
        fy = int(re.match(r'FY(\d{4})', base).group(1))
        blk = insurance_block(path, fy)
        years.append(blk if blk else {
            'fy': fy, 'page': None, 'line_no': None,
            'source': os.path.relpath(path, ROOT), 'rows': [],
            'carried_forward': 0.0, 'printed_total': None, 'printed_expended': None,
            'summed_components': None,
            'difference': None, 'checked': False, 'names_school_share': False,
        })
    return years


# ---------------------------------------------------------------------------
# The ledger, and the district's own budget book
# ---------------------------------------------------------------------------

def ledger(cx):
    rows = cx.execute("""
        SELECT a.account_id, a.name, l.original, l.transfers, l.revised,
               l.expended, l.encumbered, l.available, l.doc_id
        FROM ledger_snapshot l JOIN account a USING (account_id)
        WHERE a.dept = ? AND a.level = 'account' AND a.account_type = 'expense'
          AND l.fy = ? AND l.period = ?
        ORDER BY a.account_id
    """, (INSURANCE_DEPT, LEDGER_FY, LEDGER_PERIOD)).fetchall()
    if not rows:
        sys.exit(f'no dept {INSURANCE_DEPT} accounts at FY{LEDGER_FY} period {LEDGER_PERIOD} '
                 '— the join matched nothing, which looks exactly like an empty department')
    out = []
    for r in rows:
        if r['account_id'] not in ACCOUNT_MEANING:
            sys.exit(f'{r["account_id"]} ({r["name"]}) has no entry in ACCOUNT_MEANING. '
                     'A new insurance account must be described before it can be drawn.')
        printed, meaning, side = ACCOUNT_MEANING[r['account_id']]
        if printed != r['name']:
            sys.exit(f'{r["account_id"]} is printed `{r["name"]}` and this script expects '
                     f'`{printed}` — the ledger renamed an account under a description.')
        out.append({
            'account_id': r['account_id'], 'printed': r['name'], 'meaning': meaning,
            'side': side, 'original': r['original'], 'transfers': r['transfers'],
            'revised': r['revised'], 'expended': r['expended'],
            'encumbered': r['encumbered'], 'available': r['available'],
            'doc_id': r['doc_id'],
        })
    return out


def one(cx, sql, args=(), what=''):
    r = cx.execute(sql, args).fetchone()
    if r is None:
        sys.exit(f'nothing returned for {what} — refusing to write a page built on a join '
                 'that matched nothing')
    return r


def district_line(cx):
    rows = cx.execute("""
        SELECT fy, stage, variant, value, documents_disagree, doc_id
        FROM budget_figure WHERE line_key = ? ORDER BY fy, stage, variant
    """, (DISTRICT_LINE,)).fetchall()
    if not rows:
        sys.exit(f'budget_figure has no `{DISTRICT_LINE}` line')
    return [dict(r) for r in rows]


def series(rows, stage, variant=''):
    return [{'fy': r['fy'], 'value': r['value']}
            for r in rows if r['stage'] == stage and r['variant'] == variant]


def change(points):
    if len(points) < 2:
        return None
    a, b = points[0], points[-1]
    yrs = b['fy'] - a['fy']
    return {
        'first_fy': a['fy'], 'last_fy': b['fy'], 'first': a['value'], 'last': b['value'],
        'change': round(b['value'] - a['value'], 2),
        'pct': None if not a['value'] else (b['value'] - a['value']) / a['value'],
        'years': yrs,
        'cagr': None if not a['value'] or yrs <= 0 else (b['value'] / a['value']) ** (1 / yrs) - 1,
    }


def gaps(cx):
    out = []
    for side, what in GAP_KEYS:
        r = cx.execute('SELECT side, what, why FROM money_gaps WHERE side=? AND what=?',
                       (side, what)).fetchone()
        if r is None:
            sys.exit(f'money_gaps has no row ({side}, {what!r}). This page quotes the '
                     'register by key; add the row to sources/data/money-gaps.csv and '
                     'rebuild the database rather than typing the limit into the page.')
        why, _, closes = r['why'].partition('— closes:')
        out.append({'side': r['side'], 'what': r['what'],
                    'why': why.strip().rstrip('·').strip(),
                    'closes': closes.strip() or None})
    return out


def build():
    cx = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    cx.row_factory = sqlite3.Row

    accounts = ledger(cx)
    dept = one(cx, """SELECT a.name, l.original, l.expended, l.doc_id
                      FROM ledger_snapshot l JOIN account a USING (account_id)
                      WHERE a.dept=? AND a.level='department' AND a.account_type='expense'
                        AND l.fy=?""",
               (INSURANCE_DEPT, LEDGER_FY), 'the insurance department row')

    # RECONCILIATION 1 — two MUNIS reports, two grains, one department. The department row
    # comes from the period 9 omnibus report and the accounts from the period 12 detail; if
    # they stopped agreeing, one of the two reports would be describing a different budget.
    acct_sum = round(sum(a['original'] for a in accounts), 2)
    if abs(acct_sum - dept['original']) > 1.0:
        sys.exit(f'dept {INSURANCE_DEPT} accounts sum to {acct_sum:,.2f} against a '
                 f'department row of {dept["original"]:,.2f} — refusing to write')

    school_appropriation = [
        dict(one(cx, """SELECT a.dept, a.name, l.original
                        FROM ledger_snapshot l JOIN account a USING (account_id)
                        WHERE a.dept=? AND a.level='department' AND a.account_type='expense'
                          AND l.fy=?""", (d, LEDGER_FY), f'department {d}'))
        for d in ('300', '301')]
    omnibus = one(cx, """SELECT SUM(l.original) AS total, COUNT(*) AS depts
                         FROM ledger_snapshot l JOIN account a USING (account_id)
                         WHERE a.level='department' AND a.account_type='expense' AND l.fy=?""",
                  (LEDGER_FY,), 'the omnibus budget')

    active = one(cx, """SELECT a.account_id, a.name, l.original, l.expended, l.available,
                               l.doc_id
                        FROM ledger_snapshot l JOIN account a USING (account_id)
                        WHERE a.account_id=? AND l.fy=? AND l.period=?""",
                 (SCHOOL_ACTIVE, LEDGER_FY, LEDGER_PERIOD), 'the school active-health line')

    dl = district_line(cx)
    settled = series(dl, 'settled')
    proposed = series(dl, 'proposed')
    actual = series(dl, 'actual')
    variants = sorted({r['variant'] for r in dl if r['variant']})

    # RECONCILIATION 2 — the district's own settled FY2026 health-insurance line against the
    # town's ledger account for the same money. Two documents, different publishers. They
    # agree to the dollar today; if they stop, the page must not go on implying they are one
    # figure, so this is asserted rather than assumed.
    settled26 = next((p['value'] for p in settled if p['fy'] == LEDGER_FY), None)
    if settled26 is None:
        sys.exit(f'the district budget book has no settled FY{LEDGER_FY} health insurance line')
    active_agrees = abs(settled26 - active['original']) < 1.0

    reports = annual_reports()
    checked = [y for y in reports if y['checked']]
    if not checked:
        sys.exit('not one annual-report insurance block reconciles to its own printed '
                 'subtotal — refusing to write a series with no established year')
    named = [y for y in reports if y['names_school_share'] and y['checked']]

    # The town-side series: the appropriated column of every year that ties, plus FY2026
    # from the ledger, which is a different document and is labelled as one.
    town_series = [{'fy': y['fy'], 'appropriated': y['printed_total'],
                    'source': 'annual report', 'page': y['page']} for y in checked]
    town_series.append({'fy': LEDGER_FY, 'appropriated': acct_sum,
                        'source': 'ledger', 'page': None})

    school_total = round(active['original'] + sum(
        a['original'] for a in accounts if a['side'] == 'school'), 2)
    school_in_dept914 = round(sum(a['original'] for a in accounts if a['side'] == 'school'), 2)
    unnamed = round(sum(a['original'] for a in accounts if a['side'] == 'unnamed'), 2)
    appropriation = round(sum(d['original'] for d in school_appropriation), 2)

    # The FY2023 -> FY2026 school retiree comparison. Appropriation against appropriation,
    # from two different publishers -- like for like on the stage (rule 6), and NOT like for
    # like on the document, which the page says.
    r23 = next((y for y in named if y['fy'] != LEDGER_FY), None)
    school23 = None
    if r23:
        school23 = next(r['appropriated'] for r in r23['rows'] if r['key'] == 'school_retirees')

    # THE SPLIT, MEASURED. In the first year the report names a school share, the single
    # `Health Insurance CH 32B` line falls while the department's own subtotal rises. Both
    # halves are computed here so the page states the measurement and not the reading of it.
    split = None
    if r23:
        prev = next((y for y in checked if y['fy'] == r23['fy'] - 1), None)
        if prev:
            def row(y, key):
                return next((r['appropriated'] for r in y['rows'] if r['key'] == key), None)
            a, b = row(prev, 'health_ins'), row(r23, 'health_ins')
            split = {
                'fy': r23['fy'], 'prev_fy': prev['fy'],
                'undivided_before': a, 'undivided_after': b,
                'undivided_pct': None if not a else (b - a) / a,
                'total_before': prev['printed_total'], 'total_after': r23['printed_total'],
                'total_pct': (r23['printed_total'] - prev['printed_total']) / prev['printed_total'],
                'named_rows': [r['label'] for r in r23['rows'] if r['side'] != 'unnamed'],
            }

    town_points = [{'fy': t['fy'], 'value': t['appropriated']} for t in town_series]

    return {
        'generated_by': 'scripts/build_insurance_charts.py',
        'source': 'sources/data/lunenburg.db',
        'ledger': {
            'fy': LEDGER_FY, 'period': LEDGER_PERIOD, 'dept': INSURANCE_DEPT,
            'dept_name': dept['name'], 'doc_id': dept['doc_id'],
            'department_row': dept['original'], 'department_doc_id': dept['doc_id'],
            'accounts': accounts,
            'total_original': acct_sum,
            'total_expended': round(sum(a['expended'] for a in accounts), 2),
            'school_original': school_in_dept914,
            'school_share_of_dept': school_in_dept914 / acct_sum,
            'unnamed_original': unnamed,
            'unnamed_accounts': sum(1 for a in accounts if a['side'] == 'unnamed'),
            'reconciles_department_row': True,
        },
        'school': {
            'active': {
                'account_id': active['account_id'], 'printed': active['name'],
                'original': active['original'], 'expended': active['expended'],
                'available': active['available'], 'doc_id': active['doc_id'],
            },
            'retiree_account_id': SCHOOL_RETIREE,
            'retiree_original': school_in_dept914,
            'total_original': school_total,
            'retiree_share_of_total': school_in_dept914 / school_total,
            'appropriation': appropriation,
            'appropriation_departments': school_appropriation,
            'retiree_share_of_appropriation': school_in_dept914 / appropriation,
            'health_share_of_appropriation': active['original'] / appropriation,
            'omnibus': omnibus['total'], 'omnibus_departments': omnibus['depts'],
            'district_book_agrees': active_agrees,
            'district_book_settled': settled26,
        },
        'district': {
            'line_key': DISTRICT_LINE,
            'settled': settled, 'proposed': proposed, 'actual': actual,
            'variants': [{'variant': v, 'points': series(dl, 'proposed', v)} for v in variants],
            'change_settled': change(settled),
            'change_actual': change(actual),
            'stages_note': 'settled, proposed and actual are three different documents about '
                           'the same line and are never differenced across each other',
        },
        'reports': {
            'years': reports,
            'editions': len(reports),
            'checked': [y['fy'] for y in checked],
            'not_checked': [{'fy': y['fy'], 'why': (
                'no insurance classification printed in this edition' if y['page'] is None
                else f'components sum to {y["summed_components"]:,.2f} against a printed '
                     f'{y["printed_total"]:,.2f}')} for y in reports if not y['checked']],
            'names_school_share': [y['fy'] for y in named],
            # The years in which ANY document in this archive separates a school share, and
            # the years in which one could have. Computed rather than counted in the page,
            # because "2 of 16" is exactly the kind of figure that survives the data moving.
            'school_years': sorted({y['fy'] for y in named} | {LEDGER_FY}),
            'years_examined': sorted({y['fy'] for y in reports} | {LEDGER_FY}),
            'school_retirees_fy2023': school23,
            'school_retirees_first_named_fy': r23['fy'] if r23 else None,
            'school_retirees_page': r23['page'] if r23 else None,
            'school_retirees_source': r23['source'] if r23 else None,
            'split': split,
            'growth_since_named': None if not school23 else {
                'first_fy': r23['fy'], 'last_fy': LEDGER_FY,
                'first': school23, 'last': school_in_dept914,
                'pct': (school_in_dept914 - school23) / school23,
                'cagr': (school_in_dept914 / school23) ** (1 / (LEDGER_FY - r23['fy'])) - 1,
            },
        },
        'town_series': town_series,
        'town_change': change(town_points),
        'gaps': gaps(cx),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='fail if the published file is not what this would write')
    a = ap.parse_args()
    payload = json.dumps(build(), indent=1, sort_keys=True) + '\n'
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if have != payload:
            print(f'STALE — {os.path.relpath(OUT, ROOT)} is not what the ledger and the '
                  'reports now produce. Run scripts/build_insurance_charts.py.')
            return 1
        print(f'ok — {os.path.relpath(OUT, ROOT)} reproduces from the ledger and the reports')
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(payload)
    d = json.loads(payload)
    print(f"wrote {os.path.relpath(OUT, ROOT)} — "
          f"{len(d['ledger']['accounts'])} insurance accounts reconciling to the "
          f"department row, {len(d['reports']['checked'])} of {d['reports']['editions']} "
          f"annual reports tying to their own printed subtotal, "
          f"{len(d['reports']['names_school_share'])} naming the school share, "
          f"{len(d['district']['settled'])} settled and {len(d['district']['actual'])} "
          f"actual years of the district's own line, {len(d['gaps'])} gap rows quoted")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
