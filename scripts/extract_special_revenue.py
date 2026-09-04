"""The school department's funds outside the general fund appropriation.

`sources/munis-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx`, obtained from the Town by records
request, FY26 through 31 March 2026. Sixty-two school fund rows: every grant and revolving
account the district holds, by fund number and by the town's own name for it, with revenue,
salaries paid, other expenditure, encumbrances and balance.

Rule 11 says the budget shows one funding stream and the others are invisible. This is the
others, priced -- and it is the only source held that shows **grant money paying salaries**,
which is the exact question the special education work could not answer from budget columns.

Sign convention: the town's balance sheet shows revenue and fund balances as credits, i.e.
negative. They are flipped here to read as money.

    python3 scripts/extract_special_revenue.py
"""
import os, csv, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources/munis-ledgers/fund-balances/special-revenue-fy2026-p09.xlsx')
OUT = os.path.join(ROOT, 'sources/data/school-special-revenue-fy26-q3.csv')
SCHOOL_ORG = 300

# Column positions, read from the header row and confirmed against the sheet's own totals.
FUND, NAME, ORG, REVENUE, SALARIES, EXPEND, ENCUMB, BALANCE = 0, 1, 2, 10, 12, 13, 14, 15


def main():
    import openpyxl
    ws = openpyxl.load_workbook(SRC, data_only=True)['FY26 SPECIAL REVENUE']
    num = lambda v: float(v) if isinstance(v, (int, float)) else 0.0
    rows = []
    for r in ws.iter_rows(min_row=8, values_only=True):
        if len(r) <= BALANCE or r[ORG] not in (SCHOOL_ORG, str(SCHOOL_ORG)):
            continue
        name = str(r[NAME] or '').lstrip("'").strip()
        if not name:
            continue
        rows.append(dict(
            fund=r[FUND], name=name,
            revenue=-num(r[REVENUE]),          # credits, flipped to read as money
            salaries=num(r[SALARIES]),
            expenditure=num(r[EXPEND]),
            encumbered=num(r[ENCUMB]),
            balance=-num(r[BALANCE])))
    with open(OUT, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(sorted(rows, key=lambda x: -x['salaries']))
    t = lambda k: sum(r[k] for r in rows)
    print(f'{len(rows)} school fund rows, FY26 through 31 March 2026\n')
    print(f"  revenue received       {t('revenue'):>14,.2f}")
    print(f"  SALARIES paid          {t('salaries'):>14,.2f}")
    print(f"  other expenditure      {t('expenditure'):>14,.2f}")
    print(f"  encumbered             {t('encumbered'):>14,.2f}")
    print(f"  balance held           {t('balance'):>14,.2f}")
    pay = [r for r in rows if r['salaries']]
    print(f"\n  {len(pay)} of these funds paid salaries in the nine months:")
    for r in sorted(pay, key=lambda x: -x['salaries']):
        print(f"     {r['salaries']:>12,.2f}   {r['name'][:52]}")
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()
