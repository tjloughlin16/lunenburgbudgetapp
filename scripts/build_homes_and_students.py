#!/usr/bin/env python3
"""Homes and students: the town keeps adding single-family homes, and the schools do not
get more children. Two series that already sit in this archive, set beside each other.

    python3 scripts/build_homes_and_students.py           # write fy28/public/data/homes-and-students.json
    python3 scripts/build_homes_and_students.py --check   # fail if it no longer reproduces

TJ, 16 September 2026: "residential development, and comparing that to the enrollment in
the school. we can probably relate residential development to school enrollment right?!
Im curious how we are building residential but the enrollment isnt increasing."

THE TWO SERIES, AND WHY THESE TWO.
  Homes     the count of single-family PARCELS the Division of Local Services reports for
            Lunenburg every fiscal year (`dls-avg-tax-bill.csv`, from the DLS Gateway by
            script). A parcel count, not a value: a revaluation cannot move it, so a rise
            is homes that exist and did not before. It counts single-family only -- no
            condominiums, no apartments -- and that is said on the page.
  Students  DESE's 1 October headcount of the district (`dese_enrollment`), the same
            series /who-is-in-the-schools draws.

RULE 7, HARD. The two lines going opposite ways is a measurement. Why they do is not:
fewer children per home, older households, more children choicing out, households
without children buying the new homes -- the data separates none of those, and the page
says so in the card, not only in the caveats. The one number that would settle most of
it -- school-age children per household by year -- the Census publishes only as a
five-year sample, and it is named in `not_established` as what would.

FISCAL YEARS. DLS's FY is the tax year (FY2026 = the tax bills of July 2025-June 2026,
on the assessment of 1 January 2025). DESE's FY is the school year (FY2026 = 1 October
2025). Both are labelled FY2026 and both describe the town in the second half of 2025;
they are set side by side on that basis and the page states it.
"""
import argparse
import csv
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import conclusions as C                                           # noqa: E402
from conclusions import conclusion, emit, figure                  # noqa: E402

DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
DLS = os.path.join(ROOT, 'sources', 'data', 'dls-avg-tax-bill.csv')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'homes-and-students.json')
DLS_KEY = 'state-dls/AvgSingleFamTaxBill.xlsx'
DESE_KEY = 'state-dese/dese-enrollment-by-grade.xlsx'
DISTRICT = 'Lunenburg'


def fail(msg):
    raise SystemExit('build_homes_and_students: ' + msg)


def homes():
    rows = [r for r in csv.DictReader(open(DLS, encoding='utf-8'))
            if r['municipality'] == DISTRICT and r['sf_parcels'] not in ('', None)]
    out = [dict(fy=int(r['fy']), homes=int(float(r['sf_parcels']))) for r in rows]
    out.sort(key=lambda r: r['fy'])
    if not out:
        fail('no Lunenburg rows with parcels in %s' % os.path.relpath(DLS, ROOT))
    return out


def students():
    db = sqlite3.connect('file:%s?mode=ro' % DB, uri=True)
    try:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT fy, total_cnt AS total FROM dese_enrollment WHERE org_level='district' AND org_name=? "
                          "AND total_cnt IS NOT NULL ORDER BY fy", (DISTRICT,)).fetchall()
        return [dict(fy=int(r['fy']), students=int(r['total'])) for r in rows]
    finally:
        db.close()


def sources():
    man = {r['key']: r for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}
    out = []
    for key, table, publisher, note in (
        (DLS_KEY, 'Average Single-Family Tax Bill, FY1988–FY2026', 'Massachusetts DOR, Division of Local Services',
         'Every town’s single-family parcels by fiscal year, exported from the DLS Gateway by script. The parcel count is the homes series here.'),
        (DESE_KEY, 'Enrollment by grade, FY1994–FY2026', 'Massachusetts Department of Elementary and Secondary Education',
         'A headcount on 1 October of the school year. The students series here.'),
    ):
        r = man.get(key) or fail('%s is not in the manifest (rule 12)' % key)
        if not r['upstream']:
            fail('%s carries no upstream address (rule 12)' % key)
        out.append(dict(path='sources/' + key, sha256=r['sha256'], bytes=int(r['bytes']), url=r['upstream'],
                        docs_url='/docs/' + key, table=table, publisher=publisher, note=note))
    return out


def build():
    h = {r['fy']: r['homes'] for r in homes()}
    s = {r['fy']: r['students'] for r in students()}
    years = sorted(set(h) & set(s))
    if len(years) < 10:
        fail('only %d overlapping years' % len(years))
    series = [dict(fy=fy, homes=h[fy], students=s[fy], students_per_100_homes=round(100 * s[fy] / h[fy], 1)) for fy in years]
    first, last = series[0], series[-1]
    # The homes series is monotone or nearly so; say exactly how many years it fell.
    fell = sum(1 for a, b in zip(series, series[1:]) if b['homes'] < a['homes'])
    peak_students = max(series, key=lambda r: r['students'])
    added = last['homes'] - first['homes']
    lost = peak_students['students'] - last['students']
    ratio_first, ratio_last = first['students_per_100_homes'], last['students_per_100_homes']
    # A five-year window, the one TJ asked about, from the latest year back.
    w5 = [r for r in series if r['fy'] >= last['fy'] - 5]
    homes5 = w5[-1]['homes'] - w5[0]['homes']
    students5 = w5[-1]['students'] - w5[0]['students']

    rows = [
        conclusion(
            id='more-homes-fewer-students',
            claim='%s more single-family homes since FY%d, and %s fewer students than the FY%d peak.'
                  % (C.num(added), first['fy'], C.num(lost), peak_students['fy']),
            so_what=('Homes rose in every one of the %d steps in the record. Enrolment has not followed them.' % (len(series) - 1)) if fell == 0
                    else ('Homes fell in only %d of %d steps in the record. Enrolment has not followed them.' % (fell, len(series) - 1)),
            figures={'added': figure(added, C.num(added), 'more single-family homes, FY%d to FY%d' % (first['fy'], last['fy'])),
                     'homes_first': figure(first['homes'], C.num(first['homes'])), 'homes_last': figure(last['homes'], C.num(last['homes'])),
                     'homes_pct': figure(added / first['homes'], C.pct(100 * added / first['homes'])),
                     'lost': figure(lost, C.num(lost)), 'peak': figure(peak_students['students'], C.num(peak_students['students'])),
                     'students_last': figure(last['students'], C.num(last['students'])),
                     'lost_pct': figure(lost / peak_students['students'], C.pct(100 * lost / peak_students['students'])),
                     'fy_first': figure(first['fy'], 'FY%d' % first['fy']), 'fy_last': figure(last['fy'], 'FY%d' % last['fy']),
                     'fy_peak': figure(peak_students['fy'], 'FY%d' % peak_students['fy']),
                     'fell': figure(fell, C.num(fell)), 'steps': figure(len(series) - 1, C.num(len(series) - 1))},
            figure='added', kind='measured', bearing='sizes',
            lede='The town has been building. The schools have been shrinking. Both are true in the same years, from two state files that count two different things.',
            detail='Single-family parcels went from %s in FY%d to %s in FY%d, up %s, and fell in %d of the %d year-to-year steps the record holds. '
                   'Enrolment peaked at %s in FY%d and stands at %s, down %s. The two lines cross the page in opposite directions.'
                   % (C.num(first['homes']), first['fy'], C.num(last['homes']), last['fy'], C.pct(100 * added / first['homes']), fell, len(series) - 1,
                      C.num(peak_students['students']), peak_students['fy'], C.num(last['students']), C.pct(100 * lost / peak_students['students'])),
            basis='Single-family parcels from the DLS average tax bill file, Lunenburg rows, FY%d–FY%d; enrolment from `dese_enrollment`, district rows, total_cnt. '
                  'DLS’s fiscal year is the tax year and DESE’s is the school year; both FY-labels describe the same autumn and are set side by side on that basis.'
                  % (first['fy'], last['fy']),
            not_shown='WHY. Fewer children per home, older households, children choicing out, new homes bought by households without children — '
                      'this pair of series separates none of them. Nor does the homes count include condominiums or apartments; it is single-family parcels only.',
            see=[('/who-is-in-the-schools', 'Who is in the schools, FY1994 to today'), ('/lunenburg-by-the-numbers', 'Who lives here')],
        ),
        conclusion(
            id='students-per-hundred-homes',
            claim='%s students for every hundred single-family homes in FY%d, against %s in FY%d.'
                  % ('%.1f' % ratio_last, last['fy'], '%.1f' % ratio_first, first['fy']),
            so_what='Fewer school-age children for each home than the town had. The fact under every “growth” argument.',
            figures={'ratio_last': figure(ratio_last, '%.1f' % ratio_last, 'students per 100 single-family homes, FY%d' % last['fy']),
                     'ratio_first': figure(ratio_first, '%.1f' % ratio_first),
                     'fy_first': figure(first['fy'], 'FY%d' % first['fy']), 'fy_last': figure(last['fy'], 'FY%d' % last['fy']),
                     'ratio_drop': figure((ratio_first - ratio_last) / ratio_first, C.pct(100 * (ratio_first - ratio_last) / ratio_first))},
            figure='ratio_last', kind='measured', bearing='sizes',
            detail='Dividing one series by the other gives students per hundred homes: %s in FY%d, %s in FY%d, a fall of %s. '
                   'It is a ratio of two counts and not a household survey: it does not say which homes hold children.'
                   % ('%.1f' % ratio_first, first['fy'], '%.1f' % ratio_last, last['fy'], C.pct(100 * (ratio_first - ratio_last) / ratio_first)),
            basis='The two series above, divided, year by year.',
            not_shown='Children per household. The Census publishes households with a child under 18 only as a five-year sample (on /lunenburg-by-the-numbers), '
                      'so the ratio here is homes to students, not families to children.',
            see=[('/lunenburg-by-the-numbers', 'A third of homes have a child under 18 — the five-year sample')],
        ),
        conclusion(
            id='the-last-five-years',
            claim='In the last five years: %s%s single-family homes, %s%s students.'
                  % ('+' if homes5 >= 0 else '−', C.num(abs(homes5)), '+' if students5 >= 0 else '−', C.num(abs(students5))),
            so_what='Building does not read through to enrolment on any horizon this record shows — five years or twenty.',
            figures={'homes5': figure(homes5, ('+' if homes5 >= 0 else '−') + C.num(abs(homes5)), 'single-family homes, FY%d to FY%d' % (w5[0]['fy'], w5[-1]['fy'])),
                     'students5': figure(students5, ('+' if students5 >= 0 else '−') + C.num(abs(students5))),
                     'fy_w0': figure(w5[0]['fy'], 'FY%d' % w5[0]['fy']), 'fy_w1': figure(w5[-1]['fy'], 'FY%d' % w5[-1]['fy']),
                     'h0': figure(w5[0]['homes'], C.num(w5[0]['homes'])), 'h1': figure(w5[-1]['homes'], C.num(w5[-1]['homes'])),
                     's0': figure(w5[0]['students'], C.num(w5[0]['students'])), 's1': figure(w5[-1]['students'], C.num(w5[-1]['students']))},
            figure='homes5', kind='measured', bearing='sizes',
            detail='FY%d to FY%d: single-family parcels %s to %s, enrolment %s to %s. A new home in Lunenburg has not, on this record, meant a new pupil.'
                   % (w5[0]['fy'], w5[-1]['fy'], C.num(w5[0]['homes']), C.num(w5[-1]['homes']), C.num(w5[0]['students']), C.num(w5[-1]['students'])),
            basis='The same two series, the latest six fiscal years.',
            not_shown='Whether the homes added were bought by families with children who then enrolled elsewhere — Monty Tech, school choice, private school — which would leave enrolment flat with more children in town. '
                      '/where-students-go-instead counts residents educated elsewhere and is the place to look.',
            see=[('/where-students-go-instead', 'Where Lunenburg’s children go instead'), ('/growth', 'What commercial growth would have to look like')],
        ),
    ]
    return dict(
        generated_by='scripts/build_homes_and_students.py',
        about='Homes and students: the town’s single-family parcel count and the schools’ headcount, FY%d to FY%d, side by side — '
              'the town has added homes every year and the schools have not gained children.' % (first['fy'], last['fy']),
        grain='Two COUNTS on two state files: single-family parcels as DLS reports them each fiscal year, and children enrolled in the district on 1 October. '
              'Neither is a dollar figure; neither says who lives in a home.',
        first_fy=first['fy'], last_fy=last['fy'],
        series=series,
        window5=dict(first_fy=w5[0]['fy'], last_fy=w5[-1]['fy'], homes=homes5, students=students5),
        sources=sources(),
        not_established=[
            'Why enrolment does not follow homes: children per household, the age of households moving in, and children educated outside the district are three explanations this pair of counts cannot separate.',
            'How many homes of other kinds — condominiums, apartments, two-family — were added; the DLS series is single-family parcels only.',
            'School-age children per household by year. The Census gives it as a five-year sample; the assessors’ records carry no ages.',
        ],
        conclusions=emit('homestudents', rows),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    data = build()
    if a.check:
        have = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else None
        if have != data:
            print('STALE %s — run build_homes_and_students.py' % os.path.relpath(OUT, ROOT))
            return 1
        print('ok — %s reproduces from the CSV and the database' % os.path.relpath(OUT, ROOT))
        return 0
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write('\n')
    print('%s: FY%d–FY%d, %d years, %d conclusions' % (os.path.relpath(OUT, ROOT), data['first_fy'], data['last_fy'], len(data['series']), len(data['conclusions'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
