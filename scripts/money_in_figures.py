#!/usr/bin/env python3
"""Every figure the money-in page states, computed — with its definition attached.

WHY THIS IS A SEPARATE MODULE

`notes/reference/data-model/money-in.html` carries 140 typed figures, 107 of them
distinct, and nothing generated any of them. Two of its aggregates could not be
adjudicated against the database at all — property tax was $195,000 apart and the town
revenue total $27,500 apart — and the reason neither could be settled is the same reason
the page was worth fixing: **an aggregate with no stated definition cannot be checked, only
believed.** A figure that matches is then indistinguishable from a figure that happens to
be close.

So every quantity here is a `Fig`: a value, the words for it, and the SQL that produced it.
The SQL is not decoration. It is the definition, it ships beside the number in the
generated page, and it is what a reader disagreeing with a figure argues with.

WHAT IS DELIBERATELY NOT HERE

Any figure that would need `report_appropriations` or `special_revenue_funds`. Both have
**zero rows with `status = 'checked'`** — 4,530 and 2,058 rows respectively are
`check failed` — and `CLAUDE.md` forbids aggregating those without splitting on status.
The annual reports hold fifteen years of both and they are not usable yet;
`notes/HANDOFF-ANNUAL-REPORTS.md` says what would make them so.

`annual_report_receipts` IS usable, but only in part, and the part is not a row filter —
it is five WHOLE years. FY2014, FY2015, FY2017, FY2018 and FY2022 have every row checked
against the report's own printed GRAND TOTAL. The other eight years have none checked at
all. A trend drawn through the five while the eight are silently absent is the standard way
to publish a wrong shape, so `receipts_years()` returns the gap alongside the data and the
page is required to show it.

    python3 scripts/money_in_figures.py          # every figure, with its definition
    python3 scripts/money_in_figures.py --sql    # ...and the statement behind each
"""

import os
import sqlite3
import sys
from dataclasses import dataclass, field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')

# The ledger we hold for FY26 stops at period 9 — 31 March. Every FY26 figure here is a
# nine-month view of a twelve-month year and must say so wherever it appears.
FY, PERIOD = 2026, 9

# The school's two appropriation lines. `301` is non-recurring and is a separate Town
# Meeting article, so it is carried separately rather than folded in: an article that did
# not pass in some other year would otherwise silently change the base.
SCHOOL_ORGS = ('300', '301')


@dataclass
class Fig:
    """One number, what it means, and the statement that produced it."""
    key: str
    label: str
    value: float
    sql: str
    note: str = ''
    unit: str = '$'
    # Where the number came from, for the reader who wants the document rather than the
    # query. Filled where a single document backs it.
    docs: list = field(default_factory=list)

    def fmt(self):
        if self.unit == '%':
            return f'{self.value:.1f}%'
        return f'${self.value:,.0f}'


def db():
    if not os.path.exists(DB):
        raise SystemExit(f'{DB} does not exist. Run: python3 scripts/build_db.py')
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def one(c, sql, params=()):
    r = c.execute(sql, params).fetchone()
    return (r[0] if r and r[0] is not None else 0.0)


def revenue_figures(c):
    """The money-in side of the general fund, FY26, as the ledger records it.

    Every one of these is `budgeted`, not `received`. The page's own subject is what the
    town EXPECTS to take in against what it appropriated, and mixing a budgeted revenue
    with a received one is rule 1 in the revenue direction.
    """
    figs = []

    def add(key, label, where, note='', params=()):
        sql = (f"SELECT SUM(budgeted) FROM v_revenue "
               f"WHERE fy={FY} AND fund='0100' AND ({where})")
        figs.append(Fig(key, label, one(c, sql, params), sql, note))

    add('rev_total', 'Every general-fund revenue line the town budgeted', '1=1',
        'The pot. 67 departments draw from it and nothing ties a source to a department.')
    add('rev_re_tax', 'Real estate taxes', "name = 'RE TAXES'")
    add('rev_pp_tax', 'Personal property taxes', "name = 'PP TAXES'")
    add('rev_tax', 'Property tax, real and personal',
        "name IN ('RE TAXES','PP TAXES')",
        'The page previously stated $35,276,996 for this, which is $195,000 more than '
        'these two lines. No third line accounts for the difference, and the page did not '
        'record which lines it was adding.')
    add('rev_ch70', 'Chapter 70 school aid', "name = 'CH 70 AID'",
        'Set in the Governor’s budget, not by anything Lunenburg does.')
    add('rev_circuit', 'Circuit breaker — special education cost reimbursement',
        "name = 'SCHCOSTREI'")
    add('rev_ugga', 'Unrestricted general government aid', "name = 'UGGA'")
    add('rev_mve', 'Motor vehicle excise', "name = 'MVE'")
    add('rev_transfers', 'Free cash and transfers in', "name = 'FBCYBUDGET'")
    return figs


def appropriation_figures(c):
    """What Town Meeting voted, what it became after transfers, and the school's share.

    TWO JOINS THAT ARE NOT OPTIONAL, both learned by getting this wrong here first.

    `ledger_snapshot` holds two KINDS of row in one table: 67 department-level rows and
    192 detail-level revenue accounts, the second carrying revenue as NEGATIVE. Summing on
    `account_id LIKE '0100-%'` adds them together and returns **minus $997,871** for the
    town's budget. So every figure joins `account` and splits on `level` and
    `account_type`. It is the `status` rule and the `v1` rule wearing a third costume:
    a column that says what a row IS cannot be skipped because the rows look alike.

    ORIGINAL IS WHAT WAS VOTED. REVISED IS WHAT IT BECAME.

    The hand-written page stated $26,323,868 and $35,777 under the words "Town Meeting
    appropriation". Those are the **revised** figures — after $76,394 of transfers into
    dept 300 and $4,223 out of dept 301. What Town Meeting actually voted was $26,247,474
    and $40,000. The page's arithmetic was right and consistent; its LABEL named a
    different quantity from its number, which is the failure `CLAUDE.md` rule 13 is about.
    Both are computed here and neither is called the other.
    """
    figs = []
    dept = ("FROM ledger_snapshot l JOIN account a USING (account_id) "
            f"WHERE l.fy={FY} AND l.period={PERIOD} AND a.level='department'")

    for col, word in (('original', 'voted by Town Meeting'),
                      ('revised', 'after transfers since the vote')):
        sql_s = f"SELECT SUM(l.{col}) {dept} AND a.dept IN ('300','301')"
        sql_t = f"SELECT SUM(l.{col}) {dept} AND a.account_type='expense'"
        school, town = one(c, sql_s), one(c, sql_t)
        figs.append(Fig(f'appr_school_{col}', f'To the schools — depts 300 and 301, {word}',
                        school, sql_s))
        figs.append(Fig(f'appr_town_{col}', f'The whole omnibus budget, 67 departments, {word}',
                        town, sql_t))
        figs.append(Fig(f'appr_share_{col}', f'The schools’ share, {word}',
                        (school / town * 100) if town else 0.0,
                        f'appr_school_{col} / appr_town_{col}',
                        note='A share of the APPROPRIATION, not of any revenue source. '
                             'No record ties a source to a department.' if col == 'original'
                             else '',
                        unit='%'))

    sql_gap = (f"SELECT SUM(l.original) {dept} AND a.account_type='expense'")
    figs.append(Fig('rev_over_appr',
                    'Revenue budgeted, less everything appropriated to departments',
                    one(c, "SELECT SUM(budgeted) FROM v_revenue "
                           f"WHERE fy={FY} AND fund='0100'") - one(c, sql_gap),
                    'rev_total − appr_town_original',
                    note='The town budgets more revenue than the omnibus spends. This is '
                         'not a surplus: it is what the other warrant articles, the '
                         'transfers and the reserves are funded from. Named here so it '
                         'cannot be mistaken for one.'))
    return figs


def fund_figures(c):
    """The school's own funds — the money that pays for schools and is not appropriated.

    This is `CLAUDE.md` rule 11 made visible: grants, revolving funds, fees and gifts pay
    for real staff and real programs and appear nowhere in the school budget line.
    """
    figs = []
    # Funds whose name says school, plus the ones the district plainly runs. Named rather
    # than pattern-matched where the name does not carry it, so the list is auditable.
    where = ("(upper(name) LIKE '%SCHOOL%' OR upper(name) LIKE '%EXTENDED DAY%' "
             "OR upper(name) LIKE '%ATHLETIC%' OR upper(name) LIKE '%LUNCH%' "
             "OR upper(name) LIKE '%CIRCUIT BREAKER%')")
    for key, col, label in [
        ('fund_rev', 'revenue', 'Into the school’s own funds'),
        ('fund_spent', 'spent', 'Out of the school’s own funds'),
        ('fund_held', 'closing_balance', 'Held in those funds at period 9'),
    ]:
        sql = (f"SELECT SUM({col}) FROM v_fund_year "
               f"WHERE fy={FY} AND period={PERIOD} AND {where}")
        figs.append(Fig(key, label, one(c, sql), sql,
                        'Actual, not budget. These cannot be added to an appropriation.'))
    return figs


def receipts_years(c):
    """The annual-report receipts, and — as loudly — the years that cannot be used.

    Returns (usable, unusable). A caller that renders the first without the second is
    publishing a trend with eight silent holes in it.
    """
    rows = c.execute("""
        SELECT fy,
               SUM(status='checked')  AS checked,
               COUNT(*)               AS total
        FROM annual_report_receipts GROUP BY fy ORDER BY fy""").fetchall()
    usable = [r['fy'] for r in rows if r['checked'] == r['total'] and r['total']]
    unusable = [(r['fy'], r['total']) for r in rows if r['checked'] != r['total']]
    return usable, unusable


def education_receipts(c, years):
    """Money the town received FOR schools, by year, from the checked receipt rows.

    Normalises the source name before grouping. OCR on some editions spaces letters out --
    FY2018 prints `PRE-SCHOOL T UIT ION` and `SCHOOL T RANSPORT AT ION` -- so a GROUP BY on
    the raw name drops those years out of their own category and the series shows a hole
    where the money did not stop.
    """
    if not years:
        return []
    qs = ','.join('?' for _ in years)
    rows = c.execute(f"""
        SELECT fy, source, CAST(amount AS REAL) AS amount
        FROM annual_report_receipts
        WHERE status='checked' AND fy IN ({qs})""", years).fetchall()

    def bucket(name):
        n = name.upper().replace(' ', '')
        if 'CH70' in n:
            return 'Chapter 70 school aid'
        if 'MSBA' in n:
            return 'MSBA — school building reimbursement'
        if 'MEDICARE' in n or 'MEDICAID' in n:
            return 'School-based Medicaid reimbursement'
        if 'SMARTGROWTH' in n and 'SCHOOL' in n:
            return 'Smart-growth school cost reimbursement'
        if 'PRESCHOOL' in n and 'TUITION' in n:
            return 'Pre-school tuition'
        if 'SCHOOLTRANSPORT' in n:
            return 'School transportation fees'
        return None

    out = {}
    for r in rows:
        b = bucket(r['source'])
        if b:
            out.setdefault(b, {})[r['fy']] = out.setdefault(b, {}).get(r['fy'], 0) + r['amount']
    return sorted(out.items(), key=lambda kv: -max(kv[1].values()))


def all_figures(c):
    return revenue_figures(c) + appropriation_figures(c) + fund_figures(c)


def main():
    c = db()
    show_sql = '--sql' in sys.argv
    print(f'\nFY{FY}, period {PERIOD} — nine months of a twelve-month year\n')
    for f in all_figures(c):
        print(f'  {f.fmt():>16}  {f.label}')
        if f.note:
            print(f'                    {f.note}')
        if show_sql:
            print(f'                    {" ".join(f.sql.split())}')
    usable, unusable = receipts_years(c)
    print(f'\nannual-report receipts — usable years: {", ".join("FY"+y for y in usable)}')
    print('  NOT usable, and they are not gaps in the town\'s record but in ours:')
    print('    ' + ', '.join(f'FY{y} ({n} rows, none checked)' for y, n in unusable))
    print('\nmoney the town received FOR schools, checked years only:')
    for label, by_year in education_receipts(c, usable):
        series = '  '.join(f'FY{y[2:]} {v:>10,.0f}' for y, v in sorted(by_year.items()))
        print(f'  {label}\n    {series}')


if __name__ == '__main__':
    main()
