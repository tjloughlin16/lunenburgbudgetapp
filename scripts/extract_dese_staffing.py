#!/usr/bin/env python3
"""What DESE records the district employing: FTE by program area, by subject, by grade.

    python3 scripts/extract_dese_staffing.py
    python3 scripts/extract_dese_staffing.py --check

Writes four files, one per DESE dataset, and NEVER one joined across them:

  sources/data/dese-teacher-program-area.csv    vd2f-ib9q   one row per org per year
  sources/data/dese-teacher-subject.csv         4684-cw3t   ...per subject as well
  sources/data/dese-teacher-grade-subject.csv   77fu-a6h8   ...with the FTE split by grade
  sources/data/dese-educator-workforce.csv      fz9c-2g33   headcount by job class and race

THE TRAP: ROLLUP ROWS SIT IN THE SAME COLUMN SPACE AS DETAIL

Every one of these files carries summary rows beside the rows they summarise, and nothing
in the column NAMES says which is which:

  * `ORG_TYPE` is `State`, `District` or `School`, in one column, in one table.
  * `SUBJ` / `SUBJECT` carries `All` beside individual subjects -- and also carries
    `Core-All Subjects` and `Total Non-Core Academic Subjects`, which are groups of
    subjects, so the members do not even partition.
  * `RACE_ETH` carries `All Educators` beside the seven reported categories.

Summing a column across such a file counts the same people three or four times over. That
is not hypothetical here: it is exactly how the function-code expenditures once produced
$116M of spending for a $26.6M district. So every table below carries an explicit LEVEL
column per rollup dimension, derived per row, and **the extract refuses to write if a row
cannot be classified.**

HOW THE HIERARCHY WAS ESTABLISHED

Read off the data and then asserted, not taken from a data dictionary -- DESE publishes
none for these. The membership of each rollup is named in the constants below; anything
not named is detail, and any org type not named stops the run rather than being guessed.

TWO THINGS THAT ARE TRUE AND ARE NOT WHAT A READER EXPECTS

**1. A district row is NOT the sum of its school rows.** This is checked across every
district-year in `vd2f-ib9q` on every run, and the two disagree in a couple of hundred of
them, by as much as several hundred FTE in the largest districts. Staff not assigned to a
school -- district-wide coaches, itinerant specialists, central office instructional posts
-- have a district row and no school row. So a per-school table answers *what is in each
building*, never *what the district employs*, and the two must not be added or differenced
to make a third number.

**2. `TCHR_CNT` in `4684-cw3t` is an FTE, not a headcount.** The name says count. The
State row for SY2026 is 76718.6, which is `TCHR_FTE_CNT` in `vd2f-ib9q` to the tenth. A
tenth of a teacher is not a person, and a column called `_CNT` holding 76718.6 is exactly
the kind of rendered name rule 13 says never to quote: what it IS, is full-time
equivalents.

And the two do not always agree. `77fu-a6h8` at `SUBJ='All'` and `4684-cw3t` at
`SUBJECT='All Teachers'` are compared organisation by organisation on every run; almost
all agree, and a small number do not -- two charter schools where one file says 0.0 and
the other says a real staff, and a run of SY2015-SY2016 rows differing by tenths and
units. **Neither file corrects the other here.** The verdict is written onto the row as
`agrees_with_teacher_subject`, so a reader can see which figures two DESE publications
state twice and identically and which they do not. Rule 13a: publish the spread, do not
pick one.

WHAT THIS IS NOT

FTE here is EPIMS FTE, which the EPIMS Data Handbook defines as the share of an
individual's workday given to an ASSIGNMENT: *"the percent of workday staff are involved
in an assignment: 1.00 is a full-time employee; a half-time employee is a .50 FTE."* Per
assignment, not per person. A budget line pays a whole salary. The two have different
denominators and dividing one by the other does not give a cost per person -- see
`sources/data/money-gaps.csv`, which registers this, and note that Lunenburg's special
education teacher FTE falling from 18.5 to 2.0 while its total FTE holds flat is the
signature of recoding rather than of staff leaving. Neither is resolved here.
"""
import argparse
import csv
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dese_xlsx import DATA, ROOT, STATE, fmt, num, peers, records  # noqa: E402

# --- the four sources, by the path they live at -----------------------------------------
DOC_PROGRAM = 'sources/state-dese/dese-teachers-by-program-area.xlsx'
DOC_SUBJECT = 'sources/state-dese/dese-teacher-data.xlsx'
DOC_GRADE = 'sources/state-dese/dese-teachers-by-grade-subject.xlsx'
DOC_WORKFORCE = 'sources/state-dese/dese-educators-retention.xlsx'

OUT_PROGRAM = os.path.join(DATA, 'dese-teacher-program-area.csv')
OUT_SUBJECT = os.path.join(DATA, 'dese-teacher-subject.csv')
OUT_GRADE = os.path.join(DATA, 'dese-teacher-grade-subject.csv')
OUT_WORKFORCE = os.path.join(DATA, 'dese-educator-workforce.csv')

# --- the hierarchy, named ---------------------------------------------------------------
ORG_LEVEL = {'State': 'state', 'District': 'district', 'School': 'school',
             'Collaborative': 'collaborative'}

# `All` / `All Teachers` is every teacher. `Core-All Subjects` and `Total Non-Core
# Academic Subjects` are GROUPS of the subjects beside them -- so the members of this
# column do not partition, and three different rows are legitimately summaries.
SUBJECT_ALL = {'All', 'All Teachers'}
SUBJECT_GROUP = {'Core-All Subjects', 'Total Non-Core Academic Subjects'}

RACE_ALL = 'All Educators'

# Four FTE components, each printed to one decimal, so their sum can miss a total printed
# to one decimal by up to 0.2. 0.25 is that bound with nothing to spare.
TOL_FTE = 0.25
# Six grade-band components, same rounding: 0.3.
TOL_BAND = 0.35
# Two DESE datasets publishing the same FTE, each rounded to one decimal independently --
# 77fu-a6h8 states a total beside six rounded bands, 4684-cw3t states its own. Where they
# differ they differ by exactly 0.1, which is rounding and not disagreement. 0.15 is that
# bound; anything larger stops the run, and the run prints how many differed and by most.
TOL_CROSS = 0.15

PROGRAM_COLS = ['SY', 'DIST_CODE', 'DIST_NAME', 'ORG_CODE', 'ORG_NAME', 'ORG_TYPE',
                'GEN_ED_FTE_CNT', 'GEN_ED_FTE_PCT', 'SPED_FTE_CNT', 'SPED_FTE_PCT',
                'CAREER_TECH_FTE_CNT', 'CAREER_TECH_FTE_PCT', 'EL_FTE_CNT', 'EL_FTE_PCT',
                'TCHR_FTE_CNT', 'COMMENTS']
SUBJECT_COLS = ['SY', 'DIST_CODE', 'DIST_NAME', 'ORG_CODE', 'ORG_NAME', 'ORG_TYPE',
                'SUBJECT', 'TCHR_CNT', 'TCHR_LIC_PCT', 'STU_TCHR_RATIO', 'EXP_TCHR_PCT',
                'TCHR_WO_LIC', 'TCHR_INFLD_PCT', 'CORE_ACAD_CNT', 'CORE_ACAD_PCT']
GRADE_COLS = ['SY', 'DIST_CODE', 'DIST_NAME', 'ORG_CODE', 'ORG_NAME', 'ORG_TYPE', 'SUBJ',
              'PK2_CNT', 'PK2_PCT', 'GRD_3_5_CNT', 'GRD_3_5_PCT', 'GRD_6_8_CNT',
              'GRD_6_8_PCT', 'GRD_9_12_CNT', 'GRD_9_12_PCT', 'MULTI_GRD_CNT',
              'MULTI_GRD_PCT', 'ALL_GRD_CNT', 'ALL_GRD_PCT', 'FTE_CNT']
WORKFORCE_COLS = ['SY', 'DIST_CODE', 'DIST_NAME', 'RACE_ETH', 'JOB_CLASS_GRP',
                  'EDUCATORS_CNT', 'EDUCATORS_PCT', 'HIRES_CNT', 'HIRES_PCT',
                  'RETAINED_CNT', 'RETAINED_PCT']

PROGRAM_FIELDS = ['fy', 'lea', 'district', 'org_code', 'org_name', 'org_level',
                  'gen_ed_fte', 'gen_ed_pct', 'sped_fte', 'sped_pct', 'career_tech_fte',
                  'career_tech_pct', 'el_fte', 'el_pct', 'total_fte', 'comments',
                  'reconciles', 'doc_id']
SUBJECT_FIELDS = ['fy', 'lea', 'district', 'org_code', 'org_name', 'org_level', 'subject',
                  'subject_level', 'teacher_fte', 'licensed_pct', 'students_per_teacher',
                  'student_teacher_ratio_printed', 'experienced_pct',
                  'teachers_without_license', 'in_field_pct', 'core_academic_fte',
                  'core_academic_pct', 'doc_id']
GRADE_FIELDS = ['fy', 'lea', 'district', 'org_code', 'org_name', 'org_level', 'subject',
                'subject_level', 'pk_2_fte', 'grade_3_5_fte', 'grade_6_8_fte',
                'grade_9_12_fte', 'multi_grade_fte', 'all_grade_fte', 'total_fte',
                'printing', 'reconciles', 'agrees_with_teacher_subject', 'doc_id']
WORKFORCE_FIELDS = ['fy', 'lea', 'district', 'race_ethnicity', 'race_level', 'job_class',
                    'educators_headcount', 'educators_pct', 'hires_headcount', 'hires_pct',
                    'retained_headcount', 'retained_pct', 'reconciles', 'doc_id']


def org_level(r, doc):
    t = r['ORG_TYPE']
    if t not in ORG_LEVEL:
        raise SystemExit(
            '%s carries ORG_TYPE %r, which this extract does not know how to place in the '
            'hierarchy.\nNothing written -- a row whose level is unknown cannot be '
            'aggregated, and a silent\ndouble count is what the level column exists to '
            'prevent.' % (doc, t))
    return ORG_LEVEL[t]


def subject_level(s):
    if s in SUBJECT_ALL:
        return 'all'
    if s in SUBJECT_GROUP:
        return 'group'
    return 'subject'


def ratio(printed):
    """`11.7 to 1` as 11.7. DESE prints the ratio as a sentence; keep both."""
    p = (printed or '').strip()
    if not p or p.upper() in ('N/A', 'NA'):
        return None
    head = p.split(' to ')[0].strip()
    return num(head)


def keep_row(r, want):
    return r['DIST_CODE'] in want or r['DIST_CODE'] == STATE


def write(fields, records_):
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=fields, lineterminator='\n')
    w.writeheader()
    for rec in records_:
        w.writerow(rec)
    return out.getvalue(), len(records_)


# --------------------------------------------------------------------------------------
def build_program(want, report):
    """vd2f-ib9q. One row per organisation per year, FTE split four ways."""
    kept, checked, failed = [], 0, []
    dist_total, school_total = {}, {}
    for r in records(os.path.join(ROOT, DOC_PROGRAM), PROGRAM_COLS, DOC_PROGRAM):
        lvl = org_level(r, DOC_PROGRAM)
        parts = [num(r[c]) for c in ('GEN_ED_FTE_CNT', 'SPED_FTE_CNT',
                                     'CAREER_TECH_FTE_CNT', 'EL_FTE_CNT')]
        tot = num(r['TCHR_FTE_CNT'])
        verdict = ''
        if tot is not None and all(p is not None for p in parts):
            checked += 1
            d = abs(sum(parts) - tot)
            verdict = 'yes' if d <= TOL_FTE else 'no'
            if d > TOL_FTE:
                failed.append((r['SY'], r['DIST_NAME'], r['ORG_NAME'], lvl,
                               round(sum(parts), 1), tot))
        k = (r['SY'], r['DIST_CODE'])
        if lvl == 'school':
            school_total[k] = school_total.get(k, 0.0) + (tot or 0.0)
        elif lvl == 'district' and tot is not None:
            dist_total[k] = tot
        if keep_row(r, want):
            kept.append(dict(
                fy=int(r['SY']), lea=r['DIST_CODE'], district=r['DIST_NAME'],
                org_code=r['ORG_CODE'], org_name=r['ORG_NAME'], org_level=lvl,
                gen_ed_fte=fmt(num(r['GEN_ED_FTE_CNT'])), gen_ed_pct=r['GEN_ED_FTE_PCT'],
                sped_fte=fmt(num(r['SPED_FTE_CNT'])), sped_pct=r['SPED_FTE_PCT'],
                career_tech_fte=fmt(num(r['CAREER_TECH_FTE_CNT'])),
                career_tech_pct=r['CAREER_TECH_FTE_PCT'],
                el_fte=fmt(num(r['EL_FTE_CNT'])), el_pct=r['EL_FTE_PCT'],
                total_fte=fmt(tot), comments=r['COMMENTS'], reconciles=verdict,
                doc_id=DOC_PROGRAM))

    report('vd2f-ib9q  GEN_ED + SPED + CAREER_TECH + EL == TCHR_FTE_CNT',
           checked, failed, 'FTE')

    # The district-is-not-its-schools measurement. Not a failure -- a property, reported
    # so that nobody reconstructs a district by adding up its buildings.
    same, diff, worst = 0, 0, 0.0
    for k, v in dist_total.items():
        if k not in school_total:
            continue
        d = abs(school_total[k] - v)
        worst = max(worst, d)
        if d <= 0.5:
            same += 1
        else:
            diff += 1
    print('  a district row equals the sum of its school rows in %d district-year(s) and '
          'NOT in %d,\n    the largest gap being %.1f FTE. Staff with no school '
          'assignment are why. Do not\n    reconstruct a district from its buildings.'
          % (same, diff, worst))
    if same + diff == 0:
        raise SystemExit('the district-against-schools comparison matched NOTHING, which '
                         'looks exactly\nlike data that is absent. Nothing written.')
    return kept


def build_subject(want, report):
    """4684-cw3t. One row per organisation per subject per year."""
    kept = []
    seen_all = {}
    for r in records(os.path.join(ROOT, DOC_SUBJECT), SUBJECT_COLS, DOC_SUBJECT):
        lvl = org_level(r, DOC_SUBJECT)
        s = r['SUBJECT']
        if s == 'All Teachers':
            seen_all[(r['SY'], r['ORG_CODE'])] = num(r['TCHR_CNT'])
        # As in the grade-and-subject file: a row of zeros is DESE saying this
        # organisation had no teacher FTE in this subject that year, and they outnumber
        # the real rows. A subject ABSENT from this table for an organisation and year we
        # hold is a published zero and not a gap.
        if keep_row(r, want) and num(r['TCHR_CNT']):
            kept.append(dict(
                fy=int(r['SY']), lea=r['DIST_CODE'], district=r['DIST_NAME'],
                org_code=r['ORG_CODE'], org_name=r['ORG_NAME'], org_level=lvl,
                subject=s, subject_level=subject_level(s),
                teacher_fte=fmt(num(r['TCHR_CNT'])), licensed_pct=r['TCHR_LIC_PCT'],
                students_per_teacher=fmt(ratio(r['STU_TCHR_RATIO'])),
                student_teacher_ratio_printed=r['STU_TCHR_RATIO'],
                experienced_pct=r['EXP_TCHR_PCT'],
                teachers_without_license=fmt(num(r['TCHR_WO_LIC'])),
                in_field_pct=r['TCHR_INFLD_PCT'],
                core_academic_fte=fmt(num(r['CORE_ACAD_CNT'])),
                core_academic_pct=r['CORE_ACAD_PCT'], doc_id=DOC_SUBJECT))
    return kept, seen_all


def build_grade(want, report, all_teachers):
    """77fu-a6h8. The same grain as above with the FTE split across grade bands."""
    kept, checked, failed = [], 0, []
    cross_ok, cross_bad, cross_worst = 0, [], 0.0
    for r in records(os.path.join(ROOT, DOC_GRADE), GRADE_COLS, DOC_GRADE):
        lvl = org_level(r, DOC_GRADE)
        bands = [num(r[c]) for c in ('PK2_CNT', 'GRD_3_5_CNT', 'GRD_6_8_CNT',
                                     'GRD_9_12_CNT', 'MULTI_GRD_CNT', 'ALL_GRD_CNT')]
        tot = num(r['FTE_CNT'])
        verdict = ''
        if tot is not None and all(b is not None for b in bands):
            checked += 1
            d = abs(sum(bands) - tot)
            verdict = 'yes' if d <= TOL_BAND else 'no'
            if d > TOL_BAND:
                failed.append((r['SY'], r['DIST_NAME'], r['ORG_NAME'], r['SUBJ'],
                               round(sum(bands), 1), tot))
        # Two DESE datasets on the same quantity: `SUBJ='All'` here against
        # `SUBJECT='All Teachers'` in 4684-cw3t, organisation by organisation. The
        # verdict goes on the ROW rather than stopping the run, because where the two
        # disagree that is a fact about two DESE publications and the honest thing is to
        # publish the disagreement rather than to choose one (rule 13a).
        agrees = ''
        if r['SUBJ'] == 'All':
            other = all_teachers.get((r['SY'], r['ORG_CODE']))
            if other is not None and tot is not None:
                d = abs(other - tot)
                cross_worst = max(cross_worst, d)
                if d <= TOL_CROSS:
                    cross_ok += 1
                    agrees = 'yes'
                else:
                    cross_bad.append((r['SY'], r['ORG_NAME'], tot, other))
                    agrees = 'no'
        # A row of zeros is DESE saying this organisation had no teacher FTE in this
        # subject that year. There are more than twice as many of those as real rows, and
        # the published database has to stay under Cloudflare's 25 MB per-asset limit, so
        # they are not written. A subject ABSENT from this table for an organisation and
        # year we hold is a published zero and not a gap -- which is the opposite of the
        # usual rule here and is why it is said in the table's own caution as well.
        if keep_row(r, want) and any(b for b in bands + [tot]):
            kept.append(dict(
                fy=int(r['SY']), lea=r['DIST_CODE'], district=r['DIST_NAME'],
                org_code=r['ORG_CODE'], org_name=r['ORG_NAME'], org_level=lvl,
                subject=r['SUBJ'], subject_level=subject_level(r['SUBJ']),
                pk_2_fte=fmt(bands[0]), grade_3_5_fte=fmt(bands[1]),
                grade_6_8_fte=fmt(bands[2]), grade_9_12_fte=fmt(bands[3]),
                multi_grade_fte=fmt(bands[4]), all_grade_fte=fmt(bands[5]),
                total_fte=fmt(tot), reconciles=verdict,
                agrees_with_teacher_subject=agrees, doc_id=DOC_GRADE))

    report('77fu-a6h8  the six grade bands sum to FTE_CNT', checked, failed, 'FTE')
    print("  77fu-a6h8 SUBJ='All' against 4684-cw3t SUBJECT='All Teachers': %s agree, "
          '%d disagree; largest gap %.1f FTE'
          % (f'{cross_ok:,}', len(cross_bad), cross_worst))
    if not cross_ok:
        raise SystemExit(
            'the cross-check between two DESE teacher datasets matched NOTHING, which '
            'looks\nexactly like data that is absent. Nothing written.')
    for b in cross_bad[:6]:
        print('      %s' % (b,))
    if cross_bad:
        print('      the disagreement is recorded per row in '
              '`agrees_with_teacher_subject`; it is NOT\n      averaged away, and neither '
              'dataset is treated as correcting the other')
    return kept


def build_workforce(want, report):
    """fz9c-2g33. Headcount by job class and race, with hires and retention."""
    kept = []
    detail, total = {}, {}
    for r in records(os.path.join(ROOT, DOC_WORKFORCE), WORKFORCE_COLS, DOC_WORKFORCE):
        race, job = r['RACE_ETH'], r['JOB_CLASS_GRP']
        lvl = 'all' if race == RACE_ALL else 'detail'
        k = (r['SY'], r['DIST_CODE'], job)
        n = num(r['EDUCATORS_CNT'])
        if lvl == 'all':
            total[k] = n
        elif n is not None:
            detail[k] = detail.get(k, 0.0) + n
        if keep_row(r, want) or r['DIST_CODE'] in want:
            kept.append(dict(
                fy=int(r['SY']), lea=r['DIST_CODE'], district=r['DIST_NAME'],
                race_ethnicity=race, race_level=lvl, job_class=job,
                educators_headcount=fmt(n), educators_pct=r['EDUCATORS_PCT'],
                hires_headcount=fmt(num(r['HIRES_CNT'])), hires_pct=r['HIRES_PCT'],
                retained_headcount=fmt(num(r['RETAINED_CNT'])),
                retained_pct=r['RETAINED_PCT'], reconciles='', doc_id=DOC_WORKFORCE))

    # The identity: the seven reported races sum to `All Educators` -- EXCEPT where DESE
    # has suppressed a small cell, which is why an absent count is not read as zero and a
    # short sum is reported rather than being made to add up.
    checked, failed = 0, []
    verdict = {}
    for k, t in total.items():
        if t is None or k not in detail:
            continue
        checked += 1
        d = t - detail[k]
        verdict[k] = 'yes' if abs(d) < 0.5 else 'no'
        if abs(d) >= 0.5:
            failed.append((k[0], k[2], detail[k], t, 'suppressed cells' if d > 0 else ''))
    for rec in kept:
        rec['reconciles'] = verdict.get((str(rec['fy']), rec['lea'], rec['job_class']), '')
    report('fz9c-2g33  the reported races sum to All Educators', checked, failed,
           'educators', note='a short sum is DESE suppressing a small cell, not an error '
                             'in the total')
    return kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='fail if any of the four extracts no longer reproduces')
    a = ap.parse_args()

    for doc in (DOC_PROGRAM, DOC_SUBJECT, DOC_GRADE, DOC_WORKFORCE):
        if not os.path.exists(os.path.join(ROOT, doc)):
            print('%s is catalogued but not on disk.\nrun: python3 '
                  'scripts/sync_archive.py --pull' % doc)
            return 1
    want = peers()

    problems = []

    def report(label, checked, failed, unit, note=''):
        """Print an identity's verdict, and refuse if it had no power to fail."""
        print('  %s: %s checked, %d disagree' % (label, f'{checked:,}', len(failed)))
        if not checked:
            problems.append('%s matched NOTHING. A check with no rows is not a check.'
                            % label)
            return
        for f in failed[:8]:
            print('      %s' % (f,))
        if failed and note:
            print('      (%s)' % note)

    print('Reading four DESE staffing datasets')
    program = build_program(want, report)
    subject, all_teachers = build_subject(want, report)
    grade = build_grade(want, report, all_teachers)
    dup = 0
    seen = {}
    for r in grade:
        k = (r['fy'], r['org_code'], r['subject'])
        seen[k] = seen.get(k, 0) + 1
        r['printing'] = seen[k]
        dup += 1 if seen[k] > 1 else 0
    # 77fu-a6h8 publishes the same organisation, subject and year twice with DIFFERENT
    # figures -- 0.0 FTE against 0.2 for one school. Keying on the natural key would drop
    # one silently, and a dropped row looks exactly like data that was never published.
    # `printing` numbers them, the way `enterprise_balance_sheet` numbers a sheet the
    # annual report prints twice. Collapse on it before aggregating.
    print('  77fu-a6h8: %d row(s) share an organisation, subject and year already used '
          'and are\n    numbered `printing` 2 or more. They are NOT identical -- collapse '
          'on `printing`\n    before aggregating.' % dup)
    workforce = build_workforce(want, report)

    if problems:
        print('\n' + '\n'.join(problems))
        print('Nothing written.')
        return 1

    outputs = [(OUT_PROGRAM, PROGRAM_FIELDS, program),
               (OUT_SUBJECT, SUBJECT_FIELDS, subject),
               (OUT_GRADE, GRADE_FIELDS, grade),
               (OUT_WORKFORCE, WORKFORCE_FIELDS, workforce)]
    texts = []
    for path, fields, recs in outputs:
        if not recs:
            print('\n%s would be EMPTY. An empty extract passes every check downstream '
                  'and renders\na blank page. Nothing written.'
                  % os.path.relpath(path, ROOT))
            return 1
        recs.sort(key=lambda r: tuple(str(r[f]) for f in fields[:8]))
        text, n = write(fields, recs)
        texts.append((path, text, n))

    if a.check:
        stale = [os.path.relpath(p, ROOT) for p, t, _ in texts
                 if (open(p, encoding='utf-8').read() if os.path.exists(p) else '') != t]
        if stale:
            print('\nstale: %s\nRe-run: python3 scripts/extract_dese_staffing.py'
                  % ', '.join(stale))
            return 1
        print('\nok: all four staffing extracts still reproduce')
        return 0

    print()
    for path, text, n in texts:
        open(path, 'w', encoding='utf-8', newline='').write(text)
        print('wrote %s  %s rows' % (os.path.relpath(path, ROOT), f'{n:,}'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
