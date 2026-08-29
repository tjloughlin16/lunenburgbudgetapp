"""The town's own year-to-date budget report, as filed by the Town Accountant.

Obtained by records request, not off a website: `sources/q3-fy26/`, FY26 through
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
SRC = os.path.join(ROOT, 'sources/q3-fy26/town-general-fund-expenditures-fy26-q3.txt')
OUT = os.path.join(ROOT, 'sources/data/town-ledger-fy26-q3.csv')

# "300 SCHOOL DEPARTMENT   26,247,474   76,394   26,323,868   15,736,640.86   1,668,043.22
#   8,919,184.21   66.1%"  -- six figures and a percentage after a numbered department.
ROW = re.compile(
    r'^(\d{3})\s+(.+?)\s{2,}'
    r'(-?[\d,]+)\s+(-?[\d,]+)\s+(-?[\d,]+)\s+'
    r'(-?[\d,]+\.\d{2})\s+(-?[\d,.]+)\s+(-?[\d,]+\.\d{2})\s+(-?[\d.]+)%\s*$')


def num(s):
    return float(s.replace(',', ''))


def main():
    rows = []
    for ln in open(SRC, encoding='utf-8', errors='replace'):
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
        print('no ledger rows matched'); return
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
