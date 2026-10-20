#!/usr/bin/env python3
"""DESE's AVERAGE TEACHER SALARY and teacher FTE, for every district, SY2009-SY2025.

    python3 scripts/extract_dese_teacher_salaries.py           # write the CSV
    python3 scripts/extract_dese_teacher_salaries.py --check   # ...and fail if it would change

WHY. `dese_radar` holds these figures for the fourteen districts somebody selected in RADAR.
Comparing Lunenburg with the districts the DISTRICT ITSELF named as comparable
(sources/data/comparison-sets.csv) needs every district, so this reads the statewide table.

THE SOURCE IS ALREADY HELD. `sources/state-dese/district-expenditures-by-spending-category.xlsx`
is DESE's "District Expenditures by Spending Category" (education-to-career dataset er3w-dyti),
catalogued in sources/state-dese/index.csv with its sha256. Its `Teacher Salaries` category
carries, per district and school year (`SY` = the fiscal year: SY2025 is 2024-25):
    Average Teacher Salary          from SY2018 only -- earlier years print FTE but no average
    Teacher FTE
    Teachers per 100 FTE students
Nothing is computed here; each figure is the value the table prints.

THE CHECK. Every (district, year) that `dese-radar.csv` also holds -- read from a DIFFERENT
DESE file, RADAR's district comparison workbook -- must carry the same average salary to the
dollar and the same FTE to 0.05, or this refuses to write. Lunenburg FY2018-FY2025 is named
explicitly (74,236 / 77,908 / 83,054 / 85,067 / 85,426 / 88,019 / 98,894 / 97,233), because
that is the series the rest of the site already quotes.

WHAT IT IS NOT. An average is the scale times the seniority and education of whoever is
employed that year, divided by FTE. It is not a pay scale (sources/data/teacher-salary-
schedules.csv is) and it is not what any teacher is paid. DESE's profiles report
(statereport/teachersalaries.aspx) prints the same average plus a salary TOTAL, but only to
2023-24 on 19 October 2026; this table runs a year later.
"""
import argparse
import csv
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources', 'state-dese', 'district-expenditures-by-spending-category.xlsx')
DOC = 'sources/state-dese/district-expenditures-by-spending-category.xlsx'
RADAR = os.path.join(ROOT, 'sources', 'data', 'dese-radar.csv')
OUT = os.path.join(ROOT, 'sources', 'data', 'dese-teacher-salaries.csv')
FIELDS = ['fy', 'org_code', 'district', 'avg_teacher_salary', 'teacher_fte',
          'teachers_per_100_students', 'doc_id']
MEASURE = {'Average Teacher Salary': 'avg_teacher_salary', 'Teacher FTE': 'teacher_fte',
           'Teachers per 100 FTE students': 'teachers_per_100_students'}
LUNENBURG = {2018: 74236, 2019: 77908, 2020: 83054, 2021: 85067, 2022: 85426, 2023: 88019,
             2024: 98894, 2025: 97233}


def fail(msg):
    raise SystemExit('extract_dese_teacher_salaries: ' + msg)


def fmt(v, kind):
    if v is None or v == '':
        return ''
    v = float(v)
    if kind == 'avg_teacher_salary':
        if v != int(v):
            fail('an average salary with cents: %r' % v)
        return str(int(v))
    return ('%.1f' % v)


def build():
    import openpyxl
    if not os.path.exists(SRC):
        fail('%s is not on disk; run sync_archive.py --pull' % DOC)
    ws = openpyxl.load_workbook(SRC, read_only=True)['Data']
    it = ws.iter_rows(values_only=True)
    head = next(it)
    if tuple(head[:7]) != ('SY', 'DIST_CODE', 'DIST_NAME', 'IND_CAT', 'IND_SUBCAT', 'IND_VALUE',
                           'IND_VALUE_TYPE'):
        fail('unexpected header %r' % (head,))
    rows = {}
    for sy, code, name, cat, sub, val, _typ in it:
        if cat != 'Teacher Salaries':
            continue
        if sub not in MEASURE:
            fail('an unknown Teacher Salaries measure %r' % sub)
        key = (int(sy), code)
        r = rows.setdefault(key, {'fy': str(int(sy)), 'org_code': code, 'district': name,
                                  'doc_id': DOC})
        if r['district'] != name:
            fail('%s %s carries two names' % key)
        col = MEASURE[sub]
        if r.get(col):
            fail('%s %s %s printed twice' % (key[0], key[1], sub))
        r[col] = fmt(val, col)
    out = [rows[k] for k in sorted(rows)]
    for r in out:
        for c in MEASURE.values():
            r.setdefault(c, '')
    return out


def reconcile(out):
    by = {(int(r['fy']), r['org_code']): r for r in out}
    for fy, want in LUNENBURG.items():
        got = by.get((fy, '01620000'), {}).get('avg_teacher_salary')
        if got != str(want):
            fail('Lunenburg FY%d average salary is %s; RADAR and the site say %d' % (fy, got, want))
    n = 0
    with open(RADAR, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['group'] != 'Teacher Salaries':
                continue
            mine = by.get((int(r['fy']), r['lea']))
            if mine is None:
                fail('RADAR holds %s FY%s and the statewide table does not' % (r['district'], r['fy']))
            if r['measure'] == 'Average Teacher Salary':
                if mine['avg_teacher_salary'] != str(int(float(r['value']))):
                    fail('%s FY%s average: RADAR %s, statewide %s' % (
                        r['district'], r['fy'], r['value'], mine['avg_teacher_salary']))
                n += 1
            elif r['measure'] == 'Teacher FTE':
                if abs(float(mine['teacher_fte']) - float(r['value'])) > 0.05:
                    fail('%s FY%s FTE: RADAR %s, statewide %s' % (
                        r['district'], r['fy'], r['value'], mine['teacher_fte']))
                n += 1
    return n


def render(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, '') for k in FIELDS})
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    out = build()
    n = reconcile(out)
    s = render(out)
    with_avg = sum(1 for r in out if r['avg_teacher_salary'])
    if a.check:
        if not os.path.exists(OUT) or open(OUT, encoding='utf-8').read() != s:
            fail('stale: %s' % os.path.relpath(OUT, ROOT))
        print('ok: %d district-years (%d with an average), %d figures tie to dese-radar.csv'
              % (len(out), with_avg, n))
        return
    with open(OUT + '.tmp', 'w', encoding='utf-8', newline='') as fh:
        fh.write(s)
    os.replace(OUT + '.tmp', OUT)
    print('wrote %d district-years (%d with an average); %d figures tie to dese-radar.csv'
          % (len(out), with_avg, n))


if __name__ == '__main__':
    main()
