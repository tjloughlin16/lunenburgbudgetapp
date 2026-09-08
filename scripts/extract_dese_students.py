#!/usr/bin/env python3
"""The children: how many, where, on an IEP or not, and where a placement leads.

    python3 scripts/extract_dese_students.py
    python3 scripts/extract_dese_students.py --check

Writes five files. FIVE, from SIX datasets, and the missing one is the point -- see below.

  sources/data/dese-enrollment.csv           t8td-gens   one row per organisation per year
  sources/data/dese-sped-indicator.csv       yamx-769q   ...per grade group, group, measure
  sources/data/dese-sped-program.csv         n62c-bx65   disability type and demographics
  sources/data/dese-sped-trajectory.csv      92x3-2qj9   where a placement starts and ends
  sources/data/dese-sped-movement.csv        8aww-sugs   entering and leaving services
  sources/data/dese-town-enrollment.csv      vxt3-k35x AND 8xyg-59b2 -- the same rows

TWO DATASET IDS, ONE TABLE, AND THE REASON IS A MEASUREMENT

`vxt3-k35x` is published as *Where Residents Go to School (Sending)* and `8xyg-59b2` as
*Reasons for Student Enrollment by Town (Receiving)*. They read as a matched pair giving
the two directions of school choice. They are not a pair. Compared tuple by tuple on
(school year, town of residence, reason, enrolling district, count), the two files hold
**the identical set of rows** -- the run prints the comparison -- and differ only in the
order of their columns. One table, published twice under two names.

So there is one table here, and *sending* and *receiving* are two ways of reading it:
filter on the town to see where Lunenburg's children go, filter on the district to see who
comes in. Loading it twice would have made a net position look like it rested on two
independent sources when it rests on one.

THE TRAP, AGAIN: ROLLUPS BESIDE DETAIL, IN MORE THAN ONE COLUMN AT ONCE

  * `ORG_TYPE` -- `State`, `District`, `School`, `Collaborative`, all in one column.
  * `STU_GRP` -- `All Students` beside `Students with Disabilities` and
    `Students without Disabilities`, which do partition it.
  * `IND_DESC` -- every indicator category carries its own total row.
  * `GRADES` -- `K-12` beside `Grades 3-8`, `Grade 10`, `Grades 9-12`, `Grades 11 and 12`.

**`GRADES` is the one that is not a rollup with detail beneath it: its members OVERLAP.**
Grade 10 is inside Grades 9-12 is inside K-12, and Grades 3-8 crosses both. There is no
sum of them that means anything, so the level column here says `all` or `subset` and never
implies that the subsets add up.

`8aww-sugs` looks like the exception -- `K-12` over thirteen named grades -- and is not.
That identity was asserted first and found to be FALSE: see `build_movement`, where the
sum of the grade rows is written onto the K-12 row as a figure rather than being claimed
as a breakdown of it.

SY2024 AND SY2025 ARE THE SAME FOUR NUMBERS IN `8aww-sugs`

Lunenburg's SY2024 and SY2025 rows are identical across enrolment, students on an IEP,
students moving in and students moving out. Four independently counted quantities landing
on the same values two years running is not plausible; a row carried forward is. This
extract does not decide which -- it MEASURES it, across every district in the file, and
writes `repeats_prior_year` on any row whose figures exactly equal the same district's
previous year. Nothing may sum two such years as though they were two years of movement.

WHAT A COUNT OF CHILDREN IS NOT

It is not money, and it does not say which fund paid. DESE counts students; the town's
budget lines are net appropriations (rule 11). A rise in out-of-district placements and a
rise in the tuition line are two measurements, and neither explains the other here.
"""
import argparse
import csv
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dese_xlsx import DATA, ROOT, STATE, fmt, num, peers, records  # noqa: E402

DOC_ENROL = 'sources/state-dese/dese-enrollment-by-grade.xlsx'
DOC_IND = 'sources/state-dese/dese-sped-indicators.xlsx'
DOC_PROG = 'sources/state-dese/dese-sped-program-characteristics.xlsx'
DOC_TRAJ = 'sources/state-dese/dese-sped-placement-trajectory.xlsx'
DOC_MOVE = 'sources/state-dese/dese-sped-movement.xlsx'
DOC_SEND = 'sources/state-dese/dese-residents-sending.xlsx'
DOC_RECV = 'sources/state-dese/dese-enrollment-receiving.xlsx'

OUT_ENROL = os.path.join(DATA, 'dese-enrollment.csv')
OUT_IND = os.path.join(DATA, 'dese-sped-indicator.csv')
OUT_PROG = os.path.join(DATA, 'dese-sped-program.csv')
OUT_TRAJ = os.path.join(DATA, 'dese-sped-trajectory.csv')
OUT_MOVE = os.path.join(DATA, 'dese-sped-movement.csv')
OUT_TOWN = os.path.join(DATA, 'dese-town-enrollment.csv')

ORG_LEVEL = {'State': 'state', 'District': 'district', 'School': 'school',
             'Collaborative': 'collaborative'}
GROUP_ALL = 'All Students'
GRADES_ALL = 'K-12'

# The total row inside each indicator category. Named per category rather than matched on
# the word `Total`, so a new category arrives as an error rather than as a silent member.
IND_TOTAL = {
    'Disability Type': 'Total Students with Disabilities',
    'Disability Type All': 'Total Students with Disabilities',
    'EL and Low Income/Economically Disadvantaged': 'Total Students with Disabilities',
    'Enrollment': 'Total In- and Out-of-District Students',
    'Gender': 'Total Students with Disabilities',
    'Grade Span': 'Total Students with Disabilities',
    'In District/Out of District': 'Total Students with Disabilities',
    'Placement': 'Total Students with Disabilities',
    'Race/Ethnicity': 'Total Students with Disabilities',
    'Special Education FTEs per 100 SWDs': 'Total Special Education FTEs',
}
# Two of those categories are two renderings of ONE breakdown: `Disability Type All` names
# eleven disabilities and `Disability Type` collapses several into `Other Disability`.
# They must never be added together, which is why the category stays on every row.

GRADE_COLS = ['PK_CNT', 'K_CNT', 'G1_CNT', 'G2_CNT', 'G3_CNT', 'G4_CNT', 'G5_CNT',
              'G6_CNT', 'G7_CNT', 'G8_CNT', 'G9_CNT', 'G10_CNT', 'G11_CNT', 'G12_CNT',
              'SP_CNT']

ENROL_COLS = ['SY', 'DIST_CODE', 'DIST_NAME', 'ORG_CODE', 'ORG_NAME', 'ORG_TYPE',
              'TOTAL_CNT'] + GRADE_COLS[:-1] + ['SP_CNT', 'AIAN_PCT', 'AS_PCT', 'BAA_PCT',
              'HL_PCT', 'MNHL_PCT', 'NHPI_PCT', 'WH_PCT', 'FE_PCT', 'MA_PCT', 'NB_PCT',
              'EL_CNT', 'EL_PCT', 'FLNE_CNT', 'FLNE_PCT', 'HN_CNT', 'HN_PCT', 'LI_CNT',
              'LI_PCT', 'ECD_CNT', 'ECD_PCT', 'SWD_CNT', 'SWD_PCT']
IND_COLS = ['SY', 'DIST_CODE', 'DIST_NAME', 'GRADES', 'STU_GRP', 'IND_CAT', 'IND_DESC',
            'TOT_CNT', 'IND_CNT', 'IND_PCT', 'VALUE_TYPE']
PROG_COLS = ['SY', 'DIST_CODE', 'DIST_NAME', 'IND_CAT', 'IND_DESC', 'TOT_CNT', 'IND_CNT',
             'IND_PCT', 'VALUE_TYPE']
TRAJ_COLS = ['SY', 'DIST_CODE', 'DIST_NAME', 'GRADESPAN', 'PLCMT_BGN', 'TOT_CNT',
             'NOIEP_CNT', 'NOIEP_PCT', 'INCL_CNT', 'INCL_PCT', 'SUBSEP_CNT', 'SUBSEP_PCT',
             'OOD_CNT', 'OOD_PCT']
MOVE_COLS = ['SY', 'DIST_CODE', 'DIST_NAME', 'GRADES', 'TOT', 'SPED_TOT', 'MOVEIN_CNT',
             'MOVEOUT_CNT']
SEND_COLS = ['SY', 'TOWN_NAME', 'ENR_REASON', 'DIST_CODE', 'DIST_NAME', 'ENR_CNT']
RECV_COLS = ['SY', 'DIST_CODE', 'DIST_NAME', 'ENR_REASON', 'TOWN_NAME', 'ENR_CNT']

ENROL_FIELDS = (['fy', 'lea', 'district', 'org_code', 'org_name', 'org_level', 'total_cnt',
                 'pk_cnt', 'k_cnt'] + ['grade_%d_cnt' % i for i in range(1, 13)]
                + ['sp_cnt', 'el_cnt', 'el_pct', 'first_lang_not_english_cnt',
                   'high_needs_cnt', 'high_needs_pct', 'low_income_cnt', 'low_income_pct',
                   'econ_disadvantaged_cnt', 'econ_disadvantaged_pct', 'swd_cnt',
                   'swd_pct', 'reconciles', 'doc_id'])
IND_FIELDS = ['fy', 'lea', 'district', 'geo_level', 'grades', 'grades_level',
              'student_group', 'student_group_level', 'indicator_category', 'indicator',
              'printing', 'denominator_cnt', 'measure_cnt', 'measure_pct', 'value_type',
              'doc_id']
PROG_FIELDS = ['fy', 'lea', 'district', 'geo_level', 'indicator_category', 'indicator',
               'indicator_level', 'printing', 'denominator_cnt', 'measure_cnt',
               'measure_pct', 'value_type', 'reconciles', 'doc_id']
TRAJ_FIELDS = ['fy', 'lea', 'district', 'geo_level', 'grade_span', 'placement_at_start',
               'cohort_cnt', 'no_iep_cnt', 'no_iep_pct', 'included_cnt', 'included_pct',
               'sub_separate_cnt', 'sub_separate_pct', 'out_of_district_cnt',
               'out_of_district_pct', 'unaccounted_cnt', 'reconciles', 'doc_id']
MOVE_FIELDS = ['fy', 'lea', 'district', 'geo_level', 'grades', 'grades_level',
               'enrolled_cnt', 'on_iep_cnt', 'moved_in_cnt', 'moved_out_cnt',
               'grade_rows_sum', 'repeats_prior_year', 'doc_id']
TOWN_FIELDS = ['fy', 'town', 'enrollment_reason', 'lea', 'district', 'students',
               'doc_id_sending', 'doc_id_receiving']


def number_printings(recs, keys, label):
    """`printing` = 1, 2, ... for rows sharing a natural key, and a count of how many.

    DESE PUBLISHES THE SAME KEY TWICE IN THREE OF THESE FILES, for three different
    reasons, and none of them may be dropped:

      * two rows identical in every column -- the row is simply published twice;
      * two rows identical but for the DISTRICT NAME, where one file carries both
        `Ayer Shirley` and `Ayer Shirley School District` for org code 06160000;
      * two rows with the same key and DIFFERENT FIGURES -- 0.0 FTE against 0.2 for one
        school, one subject, one year.

    The first load of these tables used the natural key as a primary key and lost 111 rows
    to `INSERT OR REPLACE` without a word. A load that drops rows looks exactly like data
    that was never published, which is the shape of defect this repository keeps finding.

    So `printing` numbers them instead -- the same word `enterprise_balance_sheet` uses for
    a balance sheet the annual report prints twice -- nothing is dropped, the duplicate is
    visible in the data, and anything aggregating must collapse on it first.
    """
    seen, dupes = {}, 0
    for r in recs:
        k = tuple(str(r[c]) for c in keys)
        seen[k] = seen.get(k, 0) + 1
        r['printing'] = seen[k]
        if seen[k] > 1:
            dupes += 1
    print('  %s: %d row(s) share a key already used and are numbered `printing` 2 or more'
          % (label, dupes))
    return dupes


def org_level(t, doc):
    if t not in ORG_LEVEL:
        raise SystemExit('%s carries ORG_TYPE %r, which this extract cannot place in the '
                         'hierarchy.\nNothing written.' % (doc, t))
    return ORG_LEVEL[t]


def geo(code):
    return 'state' if code == STATE else 'district'


def keep(code, want):
    return code in want or code == STATE


def write(fields, recs):
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=fields, lineterminator='\n')
    w.writeheader()
    for r in recs:
        w.writerow(r)
    return out.getvalue(), len(recs)


# --------------------------------------------------------------------------------------
def build_enrolment(want, report):
    """t8td-gens. One row per organisation per year, with the grade columns kept apart."""
    kept, checked, failed = [], 0, []
    for r in records(os.path.join(ROOT, DOC_ENROL), ENROL_COLS, DOC_ENROL):
        lvl = org_level(r['ORG_TYPE'], DOC_ENROL)
        grades = [num(r[c]) for c in GRADE_COLS]
        tot = num(r['TOTAL_CNT'])
        verdict = ''
        if tot is not None and all(g is not None for g in grades):
            checked += 1
            d = abs(sum(grades) - tot)
            verdict = 'yes' if d < 0.5 else 'no'
            if d >= 0.5:
                failed.append((r['SY'], r['DIST_NAME'], r['ORG_NAME'], sum(grades), tot))
        if not keep(r['DIST_CODE'], want):
            continue
        rec = dict(fy=int(r['SY']), lea=r['DIST_CODE'], district=r['DIST_NAME'],
                   org_code=r['ORG_CODE'], org_name=r['ORG_NAME'], org_level=lvl,
                   total_cnt=fmt(tot), pk_cnt=fmt(grades[0]), k_cnt=fmt(grades[1]),
                   sp_cnt=fmt(grades[14]),
                   el_cnt=fmt(num(r['EL_CNT'])), el_pct=r['EL_PCT'],
                   first_lang_not_english_cnt=fmt(num(r['FLNE_CNT'])),
                   high_needs_cnt=fmt(num(r['HN_CNT'])), high_needs_pct=r['HN_PCT'],
                   low_income_cnt=fmt(num(r['LI_CNT'])), low_income_pct=r['LI_PCT'],
                   econ_disadvantaged_cnt=fmt(num(r['ECD_CNT'])),
                   econ_disadvantaged_pct=r['ECD_PCT'],
                   swd_cnt=fmt(num(r['SWD_CNT'])), swd_pct=r['SWD_PCT'],
                   reconciles=verdict, doc_id=DOC_ENROL)
        for i in range(1, 13):
            rec['grade_%d_cnt' % i] = fmt(grades[1 + i])
        kept.append(rec)
    report('t8td-gens  PK..12 plus SP sum to TOTAL_CNT', checked, failed)
    return kept


def build_indicator(want, report):
    """yamx-769q. One row per district per grade group per student group per measure."""
    kept = []
    enrol = {}
    for r in records(os.path.join(ROOT, DOC_IND), IND_COLS, DOC_IND):
        if r['IND_CAT'] == 'CONTEXT' and r['IND_DESC'] == 'Student Enrollment':
            enrol[(r['SY'], r['DIST_CODE'], r['GRADES'], r['STU_GRP'])] = num(r['IND_CNT'])
        if not keep(r['DIST_CODE'], want):
            continue
        kept.append(dict(
            fy=int(r['SY']), lea=r['DIST_CODE'], district=r['DIST_NAME'],
            geo_level=geo(r['DIST_CODE']), grades=r['GRADES'],
            grades_level='all' if r['GRADES'] == GRADES_ALL else 'subset',
            student_group=r['STU_GRP'],
            student_group_level='all' if r['STU_GRP'] == GROUP_ALL else 'detail',
            indicator_category=r['IND_CAT'], indicator=r['IND_DESC'],
            denominator_cnt=fmt(num(r['TOT_CNT'])), measure_cnt=fmt(num(r['IND_CNT'])),
            measure_pct=r['IND_PCT'], value_type=r['VALUE_TYPE'], doc_id=DOC_IND))

    # The one identity this file states about itself: students with disabilities plus
    # students without them are all students, in the same grade group in the same year.
    checked, failed = 0, []
    for (sy, code, grades, grp), v in enrol.items():
        if grp != GROUP_ALL or v is None:
            continue
        a = enrol.get((sy, code, grades, 'Students with Disabilities'))
        b = enrol.get((sy, code, grades, 'Students without Disabilities'))
        if a is None or b is None:
            continue
        checked += 1
        if abs(a + b - v) >= 0.5:
            failed.append((sy, code, grades, a, b, v))
    report('yamx-769q  SWD + non-SWD == all students, same grade group', checked, failed)
    return kept, enrol


def build_program(want, report, problems_add):
    """n62c-bx65. Disability type, demographics and the special education FTE ratios."""
    kept = []
    total, parts = {}, {}
    for r in records(os.path.join(ROOT, DOC_PROG), PROG_COLS, DOC_PROG):
        cat, desc = r['IND_CAT'], r['IND_DESC']
        if cat not in IND_TOTAL:
            raise SystemExit(
                '%s carries indicator category %r, which this extract does not know the '
                'total row\nof. Nothing written -- a category whose total is unknown '
                'cannot be checked, and an\nunchecked breakdown is what a rollup summed '
                'with its detail looks like.' % (DOC_PROG, cat))
        lvl = 'total' if desc == IND_TOTAL[cat] else 'member'
        k = (r['SY'], r['DIST_CODE'], cat)
        v = num(r['IND_CNT'])
        if lvl == 'total':
            total[k] = v
        elif v is not None:
            parts[k] = parts.get(k, 0.0) + v
        if keep(r['DIST_CODE'], want):
            kept.append(dict(
                fy=int(r['SY']), lea=r['DIST_CODE'], district=r['DIST_NAME'],
                geo_level=geo(r['DIST_CODE']), indicator_category=cat, indicator=desc,
                indicator_level=lvl, denominator_cnt=fmt(num(r['TOT_CNT'])),
                measure_cnt=fmt(v), measure_pct=r['IND_PCT'],
                value_type=r['VALUE_TYPE'], reconciles='', doc_id=DOC_PROG))

    # NOT one identity. Ten categories sit in this column and they behave differently,
    # so the verdict is per category-district-year and the PATTERN is printed. Three of
    # them are worth knowing before anyone quotes a breakdown:
    #
    #   Placement       runs SHORT of the total in most district-years, because its four
    #                   members -- full inclusion, partial inclusion, separate school in
    #                   district, substantially separate -- are IN-DISTRICT placements.
    #                   Children placed out of district are in the total and in none of
    #                   the members.
    #   Disability Type is a COLLAPSED version of `Disability Type All`, with several
    #                   disabilities folded into `Other Disability`. Two renderings of one
    #                   breakdown; adding them together counts every child twice.
    #   Special Education FTEs per 100 SWDs is a RATIO, not a count, despite sitting in
    #                   the same `IND_CNT` column, and despite `VALUE_TYPE` saying
    #                   `Percent` on every row in this file including these.
    checked, verdict, pattern = 0, {}, {}
    for k, t in total.items():
        if t is None or k not in parts:
            continue
        checked += 1
        d = parts[k] - t
        tol = 0.35 if k[2] == 'Special Education FTEs per 100 SWDs' else 0.5
        verdict[k] = 'yes' if abs(d) < tol else 'no'
        p = pattern.setdefault(k[2], {'exact': 0, 'short': 0, 'long': 0})
        p['exact' if abs(d) < tol else ('short' if d < 0 else 'long')] += 1
    for rec in kept:
        rec['reconciles'] = verdict.get(
            (str(rec['fy']), rec['lea'], rec['indicator_category']), '')
    print('  n62c-bx65  do the members of a category add up to its own total? '
          '%s district-year(s)' % f'{checked:,}')
    for cat in sorted(pattern):
        p = pattern[cat]
        print('      %-44s exact %5d  short %5d  over %5d'
              % (cat, p['exact'], p['short'], p['long']))
    if not checked:
        problems_add('n62c-bx65 category totals matched NOTHING.')
    return kept


def build_trajectory(want, report):
    """92x3-2qj9. Where a cohort started, and where the same children are now."""
    kept, checked, failed = [], 0, []
    for r in records(os.path.join(ROOT, DOC_TRAJ), TRAJ_COLS, DOC_TRAJ):
        parts = [num(r[c]) for c in ('NOIEP_CNT', 'INCL_CNT', 'SUBSEP_CNT', 'OOD_CNT')]
        tot = num(r['TOT_CNT'])
        verdict, left = '', None
        if tot is not None and all(p is not None for p in parts):
            checked += 1
            left = tot - sum(parts)
            verdict = 'yes' if abs(left) < 0.5 else 'no'
            if abs(left) >= 0.5:
                failed.append((r['SY'], r['DIST_NAME'], r['GRADESPAN'], r['PLCMT_BGN'],
                               sum(parts), tot))
        if not keep(r['DIST_CODE'], want):
            continue
        kept.append(dict(
            fy=int(r['SY']), lea=r['DIST_CODE'], district=r['DIST_NAME'],
            geo_level=geo(r['DIST_CODE']), grade_span=r['GRADESPAN'],
            placement_at_start=r['PLCMT_BGN'], cohort_cnt=fmt(tot),
            no_iep_cnt=fmt(parts[0]), no_iep_pct=r['NOIEP_PCT'],
            included_cnt=fmt(parts[1]), included_pct=r['INCL_PCT'],
            sub_separate_cnt=fmt(parts[2]), sub_separate_pct=r['SUBSEP_PCT'],
            out_of_district_cnt=fmt(parts[3]), out_of_district_pct=r['OOD_PCT'],
            unaccounted_cnt=fmt(left), reconciles=verdict, doc_id=DOC_TRAJ))
    report('92x3-2qj9  the four destinations sum to the starting cohort', checked, failed,
           note='the four destinations describe children still enrolled here. Where they '
                'fall short\n       of the starting cohort the difference is in '
                '`unaccounted_cnt`, and what it IS -- moved\n       away, left for a '
                'private school, aged out, suppressed -- is not established by this file')
    return kept


def build_movement(want, report, problems_add):
    """8aww-sugs. Caseload in and out, and the repeated year, measured rather than assumed."""
    rows_ = list(records(os.path.join(ROOT, DOC_MOVE), MOVE_COLS, DOC_MOVE))
    figures = {}
    for r in rows_:
        figures[(r['SY'], r['DIST_CODE'], r['GRADES'])] = (
            r['TOT'], r['SPED_TOT'], r['MOVEIN_CNT'], r['MOVEOUT_CNT'])

    kept, repeats = [], 0
    for r in rows_:
        k = (r['SY'], r['DIST_CODE'], r['GRADES'])
        prior = figures.get((str(int(r['SY']) - 1), r['DIST_CODE'], r['GRADES']))
        same = 'yes' if prior is not None and prior == figures[k] else ''
        if same:
            repeats += 1
        if not keep(r['DIST_CODE'], want):
            continue
        kept.append(dict(
            fy=int(r['SY']), lea=r['DIST_CODE'], district=r['DIST_NAME'],
            geo_level=geo(r['DIST_CODE']), grades=r['GRADES'],
            grades_level='all' if r['GRADES'] == GRADES_ALL else 'grade',
            enrolled_cnt=fmt(num(r['TOT'])), on_iep_cnt=fmt(num(r['SPED_TOT'])),
            moved_in_cnt=fmt(num(r['MOVEIN_CNT'])),
            moved_out_cnt=fmt(num(r['MOVEOUT_CNT'])),
            grade_rows_sum='', repeats_prior_year=same, doc_id=DOC_MOVE))

    # THE GRADE ROWS ARE NOT THE K-12 ROW BROKEN DOWN, AND THIS WAS ASSERTED AS AN
    # IDENTITY FIRST AND FOUND TO BE FALSE. In SY2025 the state's thirteen grade rows come
    # to 789,946 against a K-12 row of 823,078, and Lunenburg's come to 1,393 against
    # 1,448. The give-away is `Grade 12`: 2,714 statewide, against about 70,000 in each of
    # the other secondary grades. A grade row here counts children who were in that grade
    # AND are still enrolled to be observed moving, so twelfth-graders are almost all
    # absent from it. **`K-12` is therefore a different population, not a sum.**
    #
    # So no identity is asserted. `grade_rows_sum` is written onto every K-12 row instead,
    # which puts the residual in the reader's hands as a figure rather than as a verdict
    # about a rollup that does not exist. WHAT THE DIFFERENCE IS is not established here.
    by_grade = {}
    for r in rows_:
        if r['GRADES'] == GRADES_ALL:
            continue
        v = num(r['TOT'])
        if v is not None:
            k = (r['SY'], r['DIST_CODE'])
            by_grade[k] = by_grade.get(k, 0.0) + v
    filled = 0
    for rec in kept:
        if rec['grades'] == GRADES_ALL:
            v = by_grade.get((str(rec['fy']), rec['lea']))
            rec['grade_rows_sum'] = fmt(v)
            filled += 1 if v is not None else 0
    print('  8aww-sugs  the grade rows are NOT the K-12 row broken down; their sum is '
          'written to\n      `grade_rows_sum` on %d K-12 row(s) so the residual is '
          'visible rather than implied' % filled)
    if not filled:
        problems_add('8aww-sugs grade_rows_sum was written to NO row, which looks '
                     'exactly like data\nthat is absent.')
    print('  8aww-sugs rows repeating the same district\'s previous year exactly, on all '
          'four\n    figures at once: %d. `repeats_prior_year` marks each one. Two such '
          'years are not\n    two years of movement and must never be summed as though '
          'they were.' % repeats)
    if not repeats:
        raise SystemExit(
            'the repeated-year test found NOTHING, and a duplicate SY2024/SY2025 row for '
            'Lunenburg\nis the reason this test exists. A check that no longer fires is '
            'not a check.\nNothing written.')
    return kept


def build_town(report, want):
    """vxt3-k35x and 8xyg-59b2, compared row by row and then loaded ONCE.

    SCOPED, and the reason is a limit rather than a judgement about what matters. The two
    files hold 74,878 rows covering every town and every district in Massachusetts, and
    the published database has to stay under Cloudflare's 25 MB per-asset limit -- the
    same trade `extract_dese_finance.py` and `extract_dese_radar.py` already record. So
    what is kept is every row about Lunenburg IN EITHER DIRECTION -- where its resident
    children go, and who arrives at its schools -- plus both directions for the six peer
    districts this project already compares against.

    The comparison between the two source files is made on ALL 74,878 rows before the
    scope is applied, so the statement that they are one dataset published twice covers
    the whole publication and not just our slice. The workbooks are in the archive with
    their sha256 and their addresses, so anyone wanting another town has the files we
    used.
    """
    def tuples(path, cols, doc):
        out = set()
        for r in records(os.path.join(ROOT, path), cols, doc):
            out.add((r['SY'], r['TOWN_NAME'], r['ENR_REASON'], r['DIST_CODE'],
                     r['DIST_NAME'], r['ENR_CNT']))
        return out

    send = tuples(DOC_SEND, SEND_COLS, DOC_SEND)
    recv = tuples(DOC_RECV, RECV_COLS, DOC_RECV)
    only_s, only_r = send - recv, recv - send
    print('  vxt3-k35x has %s rows, 8xyg-59b2 has %s; %s only in the first, %s only in '
          'the second'
          % (f'{len(send):,}', f'{len(recv):,}', f'{len(only_s):,}', f'{len(only_r):,}'))
    if not send or not recv:
        raise SystemExit('one of the two enrolment-reason files read as empty. '
                         'Nothing written.')
    if only_s or only_r:
        raise SystemExit(
            'The two enrolment-reason datasets are no longer the same rows. They were one '
            'table\npublished twice, and this extract loads them once on that basis. If '
            'they have\ndiverged that is a change in what they ARE, and the table has to '
            'be rebuilt as two.\nNothing written.')

    kept = []
    for sy, town, reason, code, name, cnt in sorted(send):
        if town != 'Lunenburg' and code not in want:
            continue
        kept.append(dict(fy=int(sy), town=town, enrollment_reason=reason, lea=code,
                         district=name, students=fmt(num(cnt)),
                         doc_id_sending=DOC_SEND, doc_id_receiving=DOC_RECV))
    print('  %s of %s rows kept: every row about Lunenburg in either direction, plus the '
          'six peers.\n    The two files were compared on all %s before scoping.'
          % (f'{len(kept):,}', f'{len(send):,}', f'{len(send):,}'))
    if not kept:
        raise SystemExit('scoping the enrolment-reason table left NO rows at all, which '
                         'looks exactly\nlike a filter that matched nothing. '
                         'Nothing written.')
    return kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    for doc in (DOC_ENROL, DOC_IND, DOC_PROG, DOC_TRAJ, DOC_MOVE, DOC_SEND, DOC_RECV):
        if not os.path.exists(os.path.join(ROOT, doc)):
            print('%s is catalogued but not on disk.\nrun: python3 '
                  'scripts/sync_archive.py --pull' % doc)
            return 1
    want = peers()
    problems = []

    def report(label, checked, failed, note=''):
        print('  %s: %s checked, %d disagree' % (label, f'{checked:,}', len(failed)))
        if not checked:
            problems.append('%s matched NOTHING. A check with no rows is not a check.'
                            % label)
            return
        for f in failed[:8]:
            print('      %s' % (f,))
        if failed and note:
            print('      (%s)' % note)

    print('Reading six DESE student datasets')
    enrol = build_enrolment(want, report)
    ind, _ = build_indicator(want, report)
    number_printings(ind, ['fy', 'lea', 'grades', 'student_group', 'indicator_category',
                           'indicator'], 'yamx-769q')
    prog = build_program(want, report, problems.append)
    number_printings(prog, ['fy', 'lea', 'indicator_category', 'indicator'], 'n62c-bx65')
    traj = build_trajectory(want, report)
    move = build_movement(want, report, problems.append)
    town = build_town(report, want)

    if problems:
        print('\n' + '\n'.join(problems) + '\nNothing written.')
        return 1

    outputs = [(OUT_ENROL, ENROL_FIELDS, enrol), (OUT_IND, IND_FIELDS, ind),
               (OUT_PROG, PROG_FIELDS, prog), (OUT_TRAJ, TRAJ_FIELDS, traj),
               (OUT_MOVE, MOVE_FIELDS, move), (OUT_TOWN, TOWN_FIELDS, town)]
    texts = []
    for path, fields, recs in outputs:
        if not recs:
            print('\n%s would be EMPTY. An empty extract passes every check downstream '
                  'and renders a\nblank page. Nothing written.'
                  % os.path.relpath(path, ROOT))
            return 1
        recs.sort(key=lambda r: tuple(str(r[f]) for f in fields[:7]))
        texts.append((path,) + write(fields, recs)[::1])

    if a.check:
        stale = [os.path.relpath(p, ROOT) for p, t, _ in texts
                 if (open(p, encoding='utf-8').read() if os.path.exists(p) else '') != t]
        if stale:
            print('\nstale: %s\nRe-run: python3 scripts/extract_dese_students.py'
                  % ', '.join(stale))
            return 1
        print('\nok: all six student extracts still reproduce')
        return 0

    print()
    for path, text, n in texts:
        open(path, 'w', encoding='utf-8', newline='').write(text)
        print('wrote %s  %s rows' % (os.path.relpath(path, ROOT), f'{n:,}'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
