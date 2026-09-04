"""The town's own year-to-date budget report, as filed by the Town Accountant.

Obtained by records request, not off a website: `sources/munis-ledgers/`, FY26 through
31 March 2026, printed 11 August 2026 from the town's accounting system.

Why it matters more than its size suggests. Every other budget figure in this project comes
from a budget document -- what somebody proposed or voted. This is the ledger: original
appropriation, transfers and adjustments, revised budget, year-to-date expended,
encumbrances. It is the only source held that shows money MOVING between lines during the
year, which analyses/budget-vs-actual.md had recorded as something we could not see.

It is one snapshot of one year, and department-level rather than line-level -- the whole
school department is a single row. So it cannot settle which school lines moved. It can
settle that the school department's appropriation was adjusted, and by how much.

    python3 scripts/extract_town_ledger.py
"""
import os, re, csv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources/munis-ledgers/expenses/glytdbud-expense-fy2026-p09-gf-all.txt')
OUT = os.path.join(ROOT, 'sources/data/town-ledger-fy26-q3.csv')

# "300 SCHOOL DEPARTMENT   26,247,474   76,394   26,323,868   15,736,640.86   1,668,043.22
#   8,919,184.21   66.1%"  -- six figures and a percentage after a numbered department.
# MUNIS prints a zero amount as ".00", with no leading digit, so the decimal groups
# must allow an empty integer part. Requiring [\d,]+ before the point dropped 16 of
# 67 departments here -- including a $2.4M assessment -- and dropped them silently.
ROW = re.compile(
    r'^(\d{3})\s+(.+?)\s{2,}'
    r'(-?[\d,]+)\s+(-?[\d,]+)\s+(-?[\d,]+)\s+'
    r'(-?[\d,]*\.\d{2})\s+(-?[\d,.]+)\s+(-?[\d,]*\.\d{2})\s+(-?[\d.]+)%\s*$')

# The report prints its own totals. Extracting rows without checking them against it is
# how a 24% shortfall goes unnoticed, so the totals are parsed and compared.
TOTAL = re.compile(
    r'GRAND TOTAL\s+(-?[\d,]+)\s+(-?[\d,]+)\s+(-?[\d,]+)\s+'
    r'(-?[\d,]*\.\d{2})\s+(-?[\d,.]+)\s+(-?[\d,]*\.\d{2})')


def num(s):
    s = s.replace(',', '')
    return float('0' + s) if s.startswith('.') else float(s)


def main():
    rows = []
    stated = None
    for ln in open(SRC, encoding='utf-8', errors='replace'):
        t = TOTAL.search(ln)
        if t:
            stated = dict(original=num(t.group(1)), transfers=num(t.group(2)),
                          revised=num(t.group(3)), expended=num(t.group(4)))
        m = ROW.match(ln.rstrip())
        if not m:
            continue
        rows.append(dict(
            dept=m.group(1), name=m.group(2).strip(),
            original=num(m.group(3)), transfers=num(m.group(4)),
            revised=num(m.group(5)), expended=num(m.group(6)),
            encumbered=num(m.group(7)), available=num(m.group(8)),
            pct_used=num(m.group(9))))
    if not rows:
        print('no ledger rows matched'); return 1
    if stated is None:
        print('GRAND TOTAL line not found -- cannot verify the extract'); return 1
    # The report prints appropriation, transfers and revised rounded to whole dollars, so
    # the sum of the rounded rows differs from the rounded total by a few dollars. That is
    # arithmetic, not a missing row. Expended carries cents and must tie exactly -- it is
    # the column that would move if a department were dropped.
    bad = []
    for k, tol in (('original', len(rows)), ('transfers', len(rows)),
                   ('revised', len(rows)), ('expended', 0.01)):
        got = sum(r[k] for r in rows)
        if abs(got - stated[k]) > tol:
            bad.append(f'  {k}: extracted {got:,.2f} vs report GRAND TOTAL {stated[k]:,.2f}'
                       f'  (short {stated[k] - got:,.2f})')
    if bad:
        print('EXTRACT DOES NOT RECONCILE TO THE REPORT:'); print('\n'.join(bad)); return 1
    print(f'reconciles to the report GRAND TOTAL '
          f'(expended {stated["expended"]:,.2f} exact; whole-dollar columns within rounding)')
    with open(OUT, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    moved = [r for r in rows if r['transfers']]
    print(f'{len(rows)} departments, FY26 through 31 March 2026\n')
    print(f"  total original appropriation  {sum(r['original'] for r in rows):>14,.0f}")
    print(f"  total transfers               {sum(r['transfers'] for r in rows):>+14,.0f}")
    print(f"  total revised                 {sum(r['revised'] for r in rows):>14,.0f}")
    print(f"  total expended                {sum(r['expended'] for r in rows):>14,.2f}")
    print(f"\n  {len(moved)} departments had money moved into or out of them:")
    for r in sorted(moved, key=lambda x: -abs(x['transfers']))[:8]:
        print(f"     {r['transfers']:>+11,.0f}  {r['name'][:44]}")
    sch = [r for r in rows if r['dept'].startswith('30')]
    print('\n  the school rows:')
    for r in sch:
        print(f"     {r['name'][:34]:<36} original {r['original']:>11,.0f}  "
              f"transfers {r['transfers']:>+9,.0f}  revised {r['revised']:>11,.0f}")
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()
