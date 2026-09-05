"""Extract Lunenburg Public Schools budget lines from the district workbook
(public/data/proposals.xlsx == sources/budget-workbooks/fy27-proposals.xlsx) into tidy CSV.

Columns in the source sheet 'FY27 Budget Projection':
  A code (function group)   B description (line item)
  C FY23 actual  D FY24 actual  E FY25 actual  F FY25 budget
  G FY26 final budget  H FY26 actuals-to-date  I FY26 encumbrances-to-date
  J FY27 Restoration  K FY27 Core  L FY27 Level Service  M FY27 Balanced
  O forecast (sheet labels it FY29; it is the out-year forecast column)
  P Restoration budget as of 2/24/26   S comments
"""
import openpyxl, csv, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else 'sources/budget-workbooks/fy27-proposals.xlsx'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'sources/data/lps-budget-lines.csv'

COLS = [
    ('fy23_actual', 2), ('fy24_actual', 3), ('fy25_actual', 4), ('fy25_budget', 5),
    ('fy26_final', 6), ('fy26_actual_td', 7), ('fy26_encumb_td', 8),
    ('fy27_restoration', 9), ('fy27_core', 10), ('fy27_level_service', 11),
    ('fy27_balanced', 12), ('forecast_outyear', 14), ('restoration_2_24_26', 15),
]

rows = list(openpyxl.load_workbook(SRC, data_only=True).active.iter_rows(values_only=True))

def s(v):
    return v.strip() if isinstance(v, str) else None

def n(v):
    return float(v) if isinstance(v, (int, float)) else None

records, section, group = [], 'EXPENSES', None
for i, r in enumerate(rows[5:], start=6):
    code, desc = s(r[0]), s(r[1])
    if code and code.upper().startswith('DISTRICT SALARIES'):
        section = 'SALARIES'
        continue
    if code and code.upper().startswith('DISTRICT EXPENSES'):
        section = 'EXPENSES'
        continue
    vals = {k: n(r[j]) for k, j in COLS}
    if code and not desc:
        group = code
        if not any(v is not None for v in vals.values()):
            continue          # pure section header
        desc = code           # group row that also carries figures
    if not desc:
        continue
    kind = 'total' if 'TOTAL' in desc.upper() else 'line'
    records.append(dict(row=i, section=section, function_group=group,
                        line_item=desc, kind=kind, **vals,
                        comments=s(r[18])))

with open(OUT, 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(records[0].keys()))
    w.writeheader()
    w.writerows(records)

lines = [r for r in records if r['kind'] == 'line']
print(f'{OUT}: {len(records)} rows ({len(lines)} line items, '
      f'{len(records)-len(lines)} totals)')
for k, _ in COLS:
    print(f"  {k:<22} {sum(r[k] or 0 for r in lines):>15,.0f}")
