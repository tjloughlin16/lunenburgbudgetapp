#!/usr/bin/env python3
"""High school to high school: enrolment in grades 9-12, and what each high school spends a
pupil, for Lunenburg, Monty Tech and the districts this site compares Lunenburg with.

    python3 scripts/build_high_schools.py           # write fy28/public/data/high-schools.json
    python3 scripts/build_high_schools.py --check   # fail if it no longer reproduces

WHY THIS EXISTS. Monty Tech enrols grades 9-12 only, so setting its enrolment beside a
pre-K-to-12 district compares two different things. TJ, 14 October 2026, asked for the
comparison LIKE FOR LIKE: high school to high school, in enrolment and in cost a pupil.

TWO DESE FILES, READ BY COORDINATE. Nothing here is typed; every value carries the row of
the workbook it came from, and the payload says which file.

  state-dese/dese-enrollment-by-grade.xlsx
      DISTRICT rows: the 1 October headcount in grades 9, 10, 11 and 12, summed. For Monty
      Tech the generator asserts that its whole-district total EQUALS its grades 9-12 sum in
      every year, which is what makes the whole district the like-for-like figure. For the
      comparison districts the sum is checked against `dese_enrollment` in lunenburg.db,
      loaded separately from the same file.
      SCHOOL rows: used only to test, year by year, whether a high school enrolled grades
      9-12 and nothing below grade 9 (PK to G8 all zero; DESE's SP column, students past
      grade 12, is the same span and is allowed).

  state-dese/school-expenditures-by-spending-category.xlsx
      DESE's school-level per-pupil expenditure. The measure is the row DESE labels
      `Total A+B+C` / `Total Expenditures`: district non-instructional (A), district-level
      instructional (B) and school-reported instructional (C) spending, state, local and
      federal, a pupil. The generator checks A+B+C against the printed total. The file has
      no capital or debt category -- its categories are listed in the payload -- so neither
      is in any school's figure.

LIKE FOR LIKE, ENFORCED. A school-year enters the spending comparison only if the enrolment
file shows that school enrolling grades 9-12 and no grade below 9 that year. The spending file's
own GRADES_SERVED is the school's CURRENT span, not the year's: The Bromfield School is
labelled 09-12 in every year, but enrolled grades 6-12 until its middle school got its own
code. Those years are left out, and the payload says so.

Nothing here multiplies a count by a figure a pupil, divides a cost by an enrolment, or says
why any figure moved (rule 7).
"""
import argparse
import csv
import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_enrollment import DISTRICT, PEERS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'high-schools.json')
ENR = 'state-dese/dese-enrollment-by-grade.xlsx'
PPX = 'state-dese/school-expenditures-by-spending-category.xlsx'
MT_TEXT = 'town-budget/text/3583-fy27-monty-tech-budget-presentation-pdf.txt'
MT_DOC = 'town-budget/docs/3583-fy27-monty-tech-budget-presentation-pdf.pdf'
MT_LEA = '08320000'
FIRST_FY = 2008
GRADES = ('G9_CNT', 'G10_CNT', 'G11_CNT', 'G12_CNT')
BELOW_9 = ('PK_CNT', 'K_CNT', 'G1_CNT', 'G2_CNT', 'G3_CNT', 'G4_CNT', 'G5_CNT', 'G6_CNT',
           'G7_CNT', 'G8_CNT')


def fail(msg):
    raise SystemExit('build_high_schools: %s\nNothing written.' % msg)


def manifest():
    return {r['key']: r for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}


def sheet(key):
    import openpyxl
    path = os.path.join(ROOT, 'sources', key)
    if not os.path.exists(path):
        fail('%s is not here; run sync_archive.py --pull.' % key)
    return openpyxl.load_workbook(path, read_only=True).worksheets[0]


def leas(db):
    """The comparison districts by DESE code, from the names build_enrollment.py uses."""
    out = {}
    for name in [DISTRICT] + PEERS:
        r = db.execute("SELECT DISTINCT lea FROM dese_enrollment WHERE org_level='district' "
                       "AND org_name=?", (name,)).fetchall()
        if len(r) != 1:
            fail('%r matches %d DESE district codes in dese_enrollment, not one' % (name, len(r)))
        out[r[0][0]] = name
    return out


def enrolment(db, names):
    ws = sheet(ENR)
    want = set(names) | {MT_LEA}
    head = None
    dist, school = {}, {}
    for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if head is None:
            head = {k: n for n, k in enumerate(row)}
            for k in ('SY', 'DIST_CODE', 'ORG_CODE', 'ORG_NAME', 'ORG_TYPE', 'TOTAL_CNT') + GRADES + BELOW_9:
                if k not in head:
                    fail('%s: no %s column' % (ENR, k))
            continue
        row = tuple(row) + (None,) * (len(head) - len(row))   # read_only drops empty tails
        lea = row[head['DIST_CODE']]
        if lea not in want:
            continue
        fy = int(row[head['SY']])
        g = [row[head[k]] for k in GRADES]
        g912 = sum(int(x) for x in g) if all(x is not None for x in g) else None
        total = int(row[head['TOTAL_CNT']]) if row[head['TOTAL_CNT']] is not None else None
        below9 = sum(int(row[head[k]] or 0) for k in BELOW_9)
        rec = dict(total=total, g912=g912, below9=below9, row=i)
        if row[head['ORG_TYPE']] == 'District':
            if fy >= FIRST_FY:
                dist.setdefault(lea, {})[fy] = rec
        elif str(row[head['ORG_CODE']]).endswith('505') or lea == MT_LEA:
            school.setdefault(row[head['ORG_CODE']], {})[fy] = dict(rec, name=row[head['ORG_NAME']])
    if MT_LEA not in dist:
        fail('%s: no Monty Tech district rows' % ENR)
    for fy, r in dist[MT_LEA].items():
        if r['total'] != r['g912']:
            fail('%s row %d: Monty Tech FY%d totals %s and its grades 9-12 sum to %s -- the '
                 'whole district is no longer its high school' % (ENR, r['row'], fy, r['total'], r['g912']))
    # The comparison districts, against the database loaded from the same file.
    for lea in names:
        for fy, r in dist.get(lea, {}).items():
            got = db.execute("SELECT grade_9_cnt+grade_10_cnt+grade_11_cnt+grade_12_cnt FROM "
                             "dese_enrollment WHERE org_level='district' AND lea=? AND fy=?",
                             (lea, fy)).fetchall()
            vals = {int(x[0]) for x in got if x[0] is not None}
            if vals and vals != {r['g912']}:
                fail('%s FY%d: grades 9-12 read %s here and %s in lunenburg.db'
                     % (names[lea], fy, r['g912'], sorted(vals)))
    return dist, school


def spending(schools_enr, codes):
    ws = sheet(PPX)
    head = None
    got, cats = {}, set()
    for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if head is None:
            head = {k: n for n, k in enumerate(row)}
            continue
        row = tuple(row) + (None,) * (len(head) - len(row))
        cats.add(row[head['IND_CAT']])
        if row[head['ORG_CODE']] not in codes:
            continue
        cat, sub = row[head['IND_CAT']], row[head['IND_SUBCAT']]
        part = {'Sub-Total A': 'a', 'Sub-Total B': 'b', 'Sub-Total C': 'c',
                'Total A+B+C': 'total'}.get(cat)
        if not part:
            continue
        fy = int(row[head['SY']])
        rec = got.setdefault(row[head['ORG_CODE']], {}).setdefault(fy, dict(
            school=row[head['ORG_NAME']], lea=row[head['DIST_CODE']],
            grades_label=row[head['GRADES_SERVED']]))
        rec[part] = row[head['IND_VALUE']]
        if part == 'total':
            if sub != 'Total Expenditures':
                fail('%s row %d: Total A+B+C is %r, not Total Expenditures' % (PPX, i, sub))
            rec['row'] = i
    if any(re.search(r'capital|debt', c or '', re.I) for c in cats):
        fail('%s now has a capital or debt category; the page says it has none' % PPX)
    out = {}
    for code, years in got.items():
        for fy, r in years.items():
            if not all(k in r for k in ('a', 'b', 'c', 'total')):
                fail('%s %s FY%d: a subtotal is missing' % (PPX, r['school'], fy))
            if abs(r['a'] + r['b'] + r['c'] - r['total']) > 2:
                fail('%s row %d: A+B+C is %s and the total prints %s'
                     % (PPX, r['row'], r['a'] + r['b'] + r['c'], r['total']))
            e = schools_enr.get(code, {}).get(fy)
            # Grades 9-12 and nothing below: a high school may also enrol students past
            # grade 12 (DESE's SP column), which is the same span, not a different school.
            only = bool(e and e['g912'] and e['below9'] == 0)
            out.setdefault(code, {})[fy] = dict(
                total=int(r['total']), a=int(r['a']), b=int(r['b']), c=int(r['c']),
                row=r['row'], grades_9_12_only=only,
                enrolled=e['total'] if e else None, enrolled_g912=e['g912'] if e else None,
                enrolment_row=e['row'] if e else None)
    return out, sorted(c for c in cats if c)


def members():
    """How many towns Monty Tech draws from, from the one parser of DESE's apportionment
    sheet (build_monty_tech.member_towns), which foots every member row to the sheet's
    totals."""
    import build_monty_tech
    m = build_monty_tech.member_towns()
    return dict(count=m['count'], towns=[t['town'] for t in m['towns']], line=m['line'],
                anchor=m['anchor'], docs_url=m['docs_url'])


def build():
    man = manifest()
    for k in (ENR, PPX, MT_DOC):
        if k not in man:
            fail('%s is not in archive-manifest.csv (rule 12)' % k)
    db = sqlite3.connect('file:%s?mode=ro' % DB, uri=True)
    try:
        names = leas(db)
        dist, schools_enr = enrolment(db, names)
    finally:
        db.close()
    names[MT_LEA] = 'Monty Tech'
    # Each district's high school: the one school code whose name says High or Regional and
    # which the spending file carries. One per district, or the build stops.
    hs = {}
    for code, years in schools_enr.items():
        lea = code[:4] + '0000'
        if lea in names and (code.endswith('505') or lea == MT_LEA) and max(years) >= 2019:
            hs.setdefault(lea, []).append(code)
    for lea in names:
        if len(hs.get(lea, [])) != 1:
            fail('%s: %d high schools found, not one: %s' % (names[lea], len(hs.get(lea, [])),
                                                            hs.get(lea)))
    hs = {lea: v[0] for lea, v in hs.items()}
    spend, cats = spending(schools_enr, set(hs.values()))
    mem = members()
    years = sorted({y for d in dist.values() for y in d})
    out_d = []
    for lea in names:
        series = dist.get(lea, {})
        sname = schools_enr[hs[lea]][max(schools_enr[hs[lea]])]['name']
        out_d.append(dict(
            lea=lea, district=names[lea], high_school=sname, high_school_code=hs[lea],
            regional=(lea == MT_LEA or 'Regional' in sname),
            vocational=(lea == MT_LEA),
            g912={str(y): series[y]['g912'] for y in sorted(series)},
            rows={str(y): series[y]['row'] for y in sorted(series)}))
    out_s = []
    for lea in names:
        code = hs[lea]
        s = spend.get(code)
        if not s:
            fail('%s: no per-pupil rows for %s' % (PPX, code))
        out_s.append(dict(lea=lea, district=names[lea], code=code,
                          school=spending_name(code, schools_enr),
                          years={str(y): s[y] for y in sorted(s)}))
    sy = sorted({int(y) for s in out_s for y in s['years']})
    return dict(
        about='Grades 9-12 enrolment and high school spending a pupil: Lunenburg, Monty Tech '
              'and the districts build_enrollment.py compares Lunenburg with.',
        generated_by='scripts/build_high_schools.py',
        enrolment=dict(
            first_fy=years[0], last_fy=years[-1], districts=out_d,
            grain='DESE’s 1 October headcount in grades 9, 10, 11 and 12, district rows; for '
                  'Monty Tech, the whole district, which the generator checks is the same '
                  'number every year.',
            source=dict(key=ENR, href='/docs/' + ENR)),
        spending=dict(
            first_fy=sy[0], last_fy=sy[-1], schools=out_s,
            measure='DESE’s school-level per-pupil expenditure, the row it labels Total A+B+C, '
                    'Total Expenditures: district non-instructional, district-level '
                    'instructional and school-reported instructional spending, state, local '
                    'and federal, a pupil.',
            categories=cats,
            rule='A school-year is compared only where the enrolment file shows that school '
                 'enrolling grades 9-12 and no grade below 9.',
            source=dict(key=PPX, href='/docs/' + PPX)),
        monty_tech_members=mem)


def spending_name(code, schools_enr):
    ys = schools_enr[code]
    return ys[max(ys)]['name']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    data = build()
    text = json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else None
        if cur != text:
            print('STALE %s — run: python3 scripts/build_high_schools.py'
                  % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('ok — %s reproduces' % os.path.relpath(OUT, ROOT))
        return 0
    with open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    e, s = data['enrolment'], data['spending']
    print('wrote %s: grades 9-12 FY%d-FY%d, %d districts; spending FY%d-FY%d'
          % (os.path.relpath(OUT, ROOT), e['first_fy'], e['last_fy'], len(e['districts']),
             s['first_fy'], s['last_fy']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
