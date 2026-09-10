#!/usr/bin/env python3
"""Student attrition by GRADE, Lunenburg only — the dimension the outflow work lacked.

WHY AN EXTRACTOR AND NOT A LOAD. The two workbooks are 85MB and 89MB -- every district,
every year, every subject, every student group. The published database is served to
residents and is already 31MB; adding 174MB of other towns' AP results so that 420
districts nobody here analyses can be queried is the trade `extract_dese_radar.py` already
refused. The full workbooks are in the archive with their sha256 and their address, which
is rule 12 doing its job: we do not have to republish everything, we have to make the
source reachable.

TWO TRAPS, BOTH VISIBLE IN THE FIRST THREE ROWS, and both have already cost this project.

  ROLLUPS SIT BESIDE DETAIL. Row 2 is DIST_CODE 00000000 / State / ORG_TYPE State. Summing
  those with district rows is what produced $116M of spending for a $26.6M district.

  STUDENT GROUPS OVERLAP. `STU_GRP` carries 'All Students' AND the race categories AND
  low-income AND disability status, all describing the SAME students. Summing them
  double-counts -- the error that reported Lunenburg's administrators doubling when the
  truth was 14 to 19.

So this keeps Lunenburg's own rows, keeps every student group as its own row rather than
adding them, and records which is the total. Nothing here may be summed without splitting
on `stu_grp` first.

    python3 scripts/extract_dese_attrition.py
    python3 scripts/extract_dese_attrition.py --check
"""
import argparse
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources', 'state-dese')
LEA = '01620000'
FILES = [('attrition', 'dese-student-attrition.xlsx')]
OUT = os.path.join(ROOT, 'sources', 'data', 'dese-attrition.csv')


def rows_for(path, kind):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    it = ws.iter_rows(values_only=True)
    hdr = [str(c).strip() if c is not None else '' for c in next(it)]
    ix = {h: i for i, h in enumerate(hdr)}
    need = ('SY', 'DIST_CODE', 'ORG_CODE', 'ORG_NAME', 'ORG_TYPE', 'STU_GRP')
    missing = [n for n in need if n not in ix]
    if missing:
        raise SystemExit('%s is missing columns %s. Its shape changed; nothing written.'
                         % (os.path.basename(path), missing))
    out = []
    for r in it:
        if str(r[ix['DIST_CODE']]).strip() != LEA:
            continue
        rec = {'kind': kind, 'sy': r[ix['SY']], 'org_code': r[ix['ORG_CODE']],
               'org_name': r[ix['ORG_NAME']], 'org_type': r[ix['ORG_TYPE']],
               'stu_grp': r[ix['STU_GRP']]}
        # Everything else in the row is the measure block, kept under its own name.
        # ROWS CAN BE SHORTER THAN THE HEADER -- openpyxl stops at the last populated
        # cell, so a row whose trailing measures are blank comes back short and indexing
        # it by header position raises IndexError. Guard the length rather than trusting
        # the header, and record the absence as None instead of skipping the row.
        for h, i in ix.items():
            if h in ('SY', 'DIST_CODE', 'DIST_NAME', 'ORG_CODE', 'ORG_NAME',
                     'ORG_TYPE', 'STU_GRP'):
                continue
            rec[h.lower()] = r[i] if i < len(r) else None
        out.append(rec)
    return out


def build():
    rows = []
    for kind, name in FILES:
        p = os.path.join(SRC, name)
        if not os.path.exists(p):
            raise SystemExit('%s is not in the archive. Ingest it first.' % name)
        got = rows_for(p, kind)
        if not got:
            raise SystemExit('%s yielded no Lunenburg rows. A filter that matches nothing '
                             'looks exactly like a district with no AP programme. '
                             'Nothing written.' % name)
        print('  %-14s %6d Lunenburg rows' % (kind, len(got)))
        rows += got
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows = build()
    cols = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    if a.check:
        if not os.path.exists(OUT):
            print('MISSING %s' % os.path.relpath(OUT, ROOT)); return 1
        have = list(csv.DictReader(open(OUT, newline='', encoding='utf-8')))
        if len(have) != len(rows):
            print('STALE %s — %d rows on disk, %d from the workbooks'
                  % (os.path.relpath(OUT, ROOT), len(have), len(rows))); return 1
        print('ok — %d rows' % len(rows)); return 0
    with open(OUT, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print('%s: %d rows, SY %s-%s'
          % (os.path.relpath(OUT, ROOT), len(rows),
             min(r['sy'] for r in rows), max(r['sy'] for r in rows)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
