#!/usr/bin/env python3
"""WHICH GRADES LUNENBURG STUDENTS LEAVE IN -- DESE's attrition rate, grade by grade.

    python3 scripts/build_attrition.py
    python3 scripts/build_attrition.py --check

Writes `fy28/public/data/attrition.json`, which /which-grades-students-leave renders.

WHY THIS PAGE EXISTS. Residents keep asking which grades children leave in, and every
answer this project could give was about DESTINATIONS -- how many go to Monty Tech, how
many under school choice -- because `dese_town_enrollment` is what the archive held. That
file has no grade in it. This one is a rate PER GRADE, seventeen years of it, and it is
the only thing published that can answer the question that was actually asked.

EVERY FIGURE IN THE SOURCE IS A PERCENTAGE. Nothing here sums a rate across grades, and
nothing averages one across grades without weighting by the enrolment in each. Where a
count of children appears on this page it is IMPLIED -- DESE's own rate applied to DESE's
own enrolment count -- and it says so every time.

FIVE TRAPS, EACH ASSERTED HERE RATHER THAN AVOIDED BY CARE.

1.  THE YEAR ON THE ROW IS THE YEAR THEY WERE GONE, NOT THE YEAR THEY WERE COUNTED. A row
    labelled SY2026 measures children who were enrolled in SY2025 and were not enrolled in
    SY2026. Get this backwards and every grade shifts by one, which puts the finding in
    grade 7. It is established here THREE independent ways, and the build stops if any of
    them stops holding:

      * the enrolment-weighted mean of the twelve grade rates reproduces DESE's own
        `grd_all` to within 0.09 points when weighted by the PRIOR year's enrolment, and
        only to within 0.38 points when weighted by the same year's;
      * `Lunenburg High` carries a grade-8 attrition figure in exactly the four school
        years that follow the four years DESE's enrolment file says grade 8 was in that
        building -- SY2014-SY2017 against FY2013-FY2016;
      * DESE's own published year ranges for the Low Income and Economically Disadvantaged
        student groups line up with the rows in this file shifted by one year, and not
        with the rows as labelled.

    And DESE says it in prose on the dataset page: *"the percentage of attrition by grade
    from the end of one school year to the beginning of the next"*.

2.  `org_type` PUTS THE DISTRICT BESIDE ITS OWN SCHOOLS. A district row is not the sum of
    its school rows and could not be -- they are rates. `assert_levels()` splits them and
    nothing on this page adds across the split.

3.  `stu_grp` OVERLAPS. `All Students` sits beside race, sex and selected-population
    groups describing the SAME children. Never added; each group is its own series.

4.  A SCHOOL NEVER REPORTS ITS OWN TOP GRADE, and this is the trap that decides the whole
    page. DESE blanks a grade where the school has "no grade in the given year for
    students from the previous year to advance" -- so Lunenburg Middle School, which ends
    at grade 8, publishes no grade-8 rate at all. The finding on this page is invisible in
    every school row and exists only at district level. `assert_terminal_grade()` checks
    the rule on every school-year against DESE's own enrolment-by-grade spans.

5.  THE SCHOOLS ARE NOT THE SAME SCHOOLS. Lunenburg reorganised its buildings twice. The
    DISTRICT's grade series is immune to that -- a grade is a grade wherever it is housed
    -- and the SCHOOL series is not: Lunenburg High's own attrition rate averages 8.8% in
    the four years it held grade 8 and 5.2% in the other thirteen, and not one child's
    behaviour changed. The eras are derived by importing the same functions
    /what-courses-actually-ran uses, so the two pages cannot segment the same reorganisation
    differently.

RULE 7 IS THE WHOLE PAGE. That one in five eighth graders does not return is a
measurement. WHY is not, and every reader will supply an answer for themselves. Monty Tech
admits at grade 9 and Lunenburg is a member town there; so does a private school, a
charter, a school choice transfer, an out-of-district placement, and a family moving for
work. This file cannot separate any of them and says so, in the conclusions, in the
caveats and in the gap register.

RULE 8. Not an audit. Nothing here is evidence that anybody failed, and the biggest single
number on the page -- the churn against the net -- is the one that most argues AGAINST the
reading a resident arrives with.

RULE 11 DOES NOT APPLY AND IT IS WORTH SAYING: nothing on this page is a dollar.
"""
import argparse
import collections
import csv
import json
import os
import re
import sqlite3
import statistics
import sys

import build_course_offerings as CO
import conclusions as C
from conclusions import conclusion, emit, figure

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'attrition.json')

LEA = '01620000'
MINUTES = 'sources/meetings/text'
DISTRICT = 'Lunenburg'
HIGH = 'Lunenburg High'
ALL = 'All Students'

# The twelve grade columns, in order, with the label a reader uses. There is no grade 12
# column: a twelfth grader who does not come back has graduated, and DESE does not call
# that attrition.
GRADES = ([('gk_pct', 'K', 'k_cnt')]
          + [('g%02d_pct' % i, str(i), 'grade_%d_cnt' % i) for i in range(1, 12)])

# How close the enrolment-weighted mean of the twelve grade rates has to come to DESE's
# own all-grades rate before this page will believe it has the right denominator. Both
# joins are computed; the prior-year one has to be inside this and it has to beat the
# same-year one by a clear margin, because two joins that are both plausible establish
# nothing.
# The grade that follows each grade, for DESE's own blank rule below. `12` is absent on
# purpose: nothing follows it, which is why no twelfth grader is ever counted as leaving.
_SEQ = ['PK', 'K'] + [str(i) for i in range(1, 13)]
ORDER = {a: b for a, b in zip(_SEQ, _SEQ[1:])}

OFFSET_TOL = 0.002
OFFSET_MARGIN = 2.0

# DESE's own description of what the number means, from the dataset page whose address is
# in DOCS below. Held here rather than paraphrased: the whole of trap 1 is that the year
# on the row is not the year the children were counted, and this is the publisher saying
# so. The verifier asserts both clauses are still in the payload the page renders.
DESE_DEFINITION = (
    'This dataset provides the percentage of attrition by grade from the end of one '
    'school year to the beginning of the next for students in Massachusetts public '
    'schools since 2010. The information is as of October 1 of the given school year.')
DESE_BLANKS = (
    'A blank value indicates that either: The school or district is new in the year '
    'selected; The school or district has no students enrolled in that grade level in '
    'the year selected; The school or district has no grade in the given year for '
    'students from the previous year to advance; The data is suppressed because the '
    'enrollment total is less than 6.')
DESE_GROUPS = (
    'Economically Disadvantaged was used 2015-2021. Low Income was used prior to 2015, '
    'and a different version of Low Income has been used since 2022.')
DESE_URL = ('https://educationtocareer.data.mass.gov/Students-and-Teachers/'
            'Student-Attrition/4as3-w39x/about_data')

# The selected populations this page draws, in the order it draws them. Race and ethnicity
# groups are in the file and are NOT drawn: Lunenburg's non-white cohorts are small enough
# that most grade-8 cells are suppressed, and a chart of four published points beside
# seventeen is a chart that invites a conclusion the data refuses. They are in the raw
# table, which is where a reader can see the suppression for themselves.
SELECTED = ['All Students', 'Students with Disabilities', 'High Needs', 'Low Income',
            'Economically Disadvantaged', 'English Learners', 'Male', 'Female']

# The groups whose definition CHANGED inside the series. DESE says so itself, quoted
# above, and the page never draws them as one line.
BROKEN = ('Low Income', 'Economically Disadvantaged')

DOCS = [
    dict(key='state-dese/dese-student-attrition.xlsx',
         what='Every Massachusetts district and school, the share of students in each '
              'grade who did not return the following year, SY2010-SY2026, split by '
              'student group. Every figure in it is a PERCENTAGE. The source of every '
              'rate on this page.',
         publisher='Massachusetts Department of Elementary and Secondary Education',
         stage='measured from the end of one school year to the beginning of the next, '
               'as at 1 October of the year named on the row. So the row says the year '
               'the children were GONE, not the year they were counted.',
         table='dese_attrition'),
    dict(key='state-dese/dese-enrollment-by-grade.xlsx',
         what='Enrolment by grade, by school, for every district. Two jobs here: it is '
              'the denominator that turns a rate into a number of children, and it is '
              'what establishes the grade span of each Lunenburg school in each year -- '
              'which is how this page knows a school-level series crosses a '
              'reorganisation.',
         publisher='Massachusetts Department of Elementary and Secondary Education',
         stage='reported as at 1 October of the school year.',
         table='dese_enrollment'),
    dict(key='state-dese/dese-residents-sending.xlsx',
         what='Where the town’s resident children are educated, by receiving '
              'district and by reason -- Monty Tech, school choice, charter. It has NO '
              'GRADE in it, which is precisely why it cannot say where a departing '
              'eighth grader went.',
         publisher='Massachusetts Department of Elementary and Secondary Education',
         stage='a headcount as at 1 October, by receiving district.',
         table='dese_town_enrollment'),
]

# WHAT WAS SAID IN PUBLIC. Every quote is re-read out of the extracted minutes on every
# run -- a quote is a claim about a document and an extractor can change what a document
# renders to (rule 13).
#
# ALL THREE ARE HERE BECAUSE OF THE PERSONA REVIEW AND NOT BECAUSE OF THE DATA. Searching
# this archive for the words this project would use -- `attrition`, `declining
# enrollment`, `enrollment decline`, `families leaving`, `losing students` -- finds
# nothing about children at all. `attrition` in Lunenburg means STAFF attrition, twice.
# The town argues about this in `choicing out`, `private school` and `8th grade`, and
# those found the High School Principal describing the exact decision this page measures.
QUOTES = [
    dict(key='choicing-out', board='school-committee', date='2025-03-12', kind='minutes',
         doc='7098', who='the Lunenburg Middle High School Principal, to the School '
                         'Committee',
         quote='She said to me that she was looking at choicing out if her private '
               "school choices didn't come through.",
         why='The decision this whole page measures, described by the person who watches '
             'it happen, in the town’s own words rather than ours. It also names '
             'two of the destinations at once -- a private school and a school choice '
             'transfer -- which is the reason no rate here can be read as one thing. '
             'What it establishes is that the choice is discussed in public. It '
             'establishes nothing about how many children make it.'),
    dict(key='hemorrhage', board='school-committee', date='2025-03-12', kind='minutes',
         doc='7098', who='the same principal, in the same comment',
         quote="I think that's going to be the reality that we have if we're not able "
               'to offer our student choices they are going to hemorrhage out of the '
               'high school',
         why='A prediction, made in public, about the quantity on this page. It is '
             'evidence of what somebody in the district expected; it is not evidence '
             'about what happened, and the series that would test it does not yet reach '
             'the years after it was said.'),
    dict(key='band-transition', board='school-committee', date='2024-02-07',
         kind='minutes', doc='6395',
         who='a student representative, to the School Committee',
         quote='When transitioning from 8th grade to 9th grade the numbers are reduced '
               'in the high school band.',
         why='The town does talk about the grade 8 to grade 9 step -- just about a '
             'different quantity. This is a student naming the transition where this '
             'page finds every year’s largest departure, and she attributes the '
             'drop she is describing to scheduling rather than to anybody leaving.'),
    dict(key='sizer-parker', board='school-committee', date='2024-12-04', kind='minutes',
         doc='6907', who='the School Committee’s own minutes',
         quote='b. Sizer & Parker Annual Reports Haven’t received the updated data',
         why='Rule 8, and the credit that goes with it: the committee had put the two '
             'charter schools’ annual reports on its own agenda and said in public '
             'that the data had not arrived. The board is asking the question this page '
             'cannot answer, and was told the same thing this page reports.'),
]

# The terms the persona review searched, INCLUDING every one that found nothing. A term
# with no matches is a statement about the readable archive and never about what anybody
# said, and the denominator prints beside all of them.
SEARCHED = ['attrition', 'declining enrollment', 'enrollment decline', 'families leaving',
            'losing students', 'leave the district',
            'choicing out', 'school choice', 'private school', 'Monty Tech',
            '8th grade', 'eighth grade', 'enrollment projection', 'Sizer']

CITES_GAPS = [
    'Which school a Lunenburg student who left went to, by grade',
    'Why one in five Lunenburg eighth graders does not return for grade 9',
    'How many of the children counted as leaving a Lunenburg school moved out of town',
]


def fail(msg):
    raise SystemExit('%s\nNothing written.' % msg)


def q(db, sql, *args):
    cur = db.execute(sql, args)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


MONTHS = ('January February March April May June July August September October November '
          'December').split()


def _longdate(iso):
    y, m, d = iso.split('-')
    return '%d %s %s' % (int(d), MONTHS[int(m) - 1], y)


def documents():
    have = {}
    with open(MANIFEST, encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            have[row['key']] = row
    out = []
    for d in DOCS:
        row = have.get(d['key'])
        if not row:
            fail('%s is not in the archive manifest. A figure without its document is '
                 'not publishable (rule 12).' % d['key'])
        out.append(dict(d, path='sources/' + d['key'], sha256=row['sha256'],
                        bytes=int(row['bytes']), url=row['upstream'],
                        docs_url='/docs/' + d['key'],
                        filename=d['key'].split('/')[-1],
                        note=d['what'] + ' Stage: ' + d['stage']))
    if not out[0]['url']:
        fail('the attrition workbook carries no upstream address in the manifest. Rule '
             '12: a figure is only checkable if somebody can get back to the document, '
             'and "public" is not an address.')
    return out


# ---- the rows, and the two levels that must not be mixed --------------------------

def attrition_rows(db):
    rows = q(db, 'SELECT sy, org_code, org_name, org_type, stu_grp, %s, grd_all '
                 'FROM dese_attrition ORDER BY sy, org_code, stu_grp'
                 % ','.join(c for c, _l, _e in GRADES))
    if not rows:
        fail('dese_attrition is empty. An empty table passes every check downstream and '
             'renders a blank page. Run scripts/build_db.py.')
    for r in rows:
        r['sy'] = int(r['sy'])
        for c, _l, _e in GRADES:
            r[c] = None if r[c] is None else float(r[c])
        r['grd_all'] = None if r['grd_all'] is None else float(r['grd_all'])
    return rows


def assert_levels(rows):
    """`org_type` is the rollup guard, and this page never crosses it.

    A district row is not the sum of its school rows and could not be: they are rates over
    different denominators. So the guard here is not an arithmetic identity -- there is
    none to check -- it is that BOTH levels are present and distinguishable, and that the
    level a series is drawn from is stated. If the column ever went single-valued, every
    chart on this page would silently become a mixture."""
    by = collections.Counter(r['org_type'] for r in rows)
    if set(by) != {'District', 'School'}:
        fail('dese_attrition no longer carries exactly the two org levels this page '
             'splits on; it carries %s. Nothing may be drawn until the split is '
             'restated.' % sorted(by))
    grps = sorted({r['stu_grp'] for r in rows})
    if ALL not in grps:
        fail('there is no %r row, and every comparison on this page is against it.' % ALL)
    if len(grps) < 5:
        fail('only %d student groups are in the file and this page rests on the '
             'OVERLAP between them being visible.' % len(grps))
    return dict(district_rows=by['District'], school_rows=by['School'],
                groups=grps, rows=len(rows))


# ---- trap 1: the year on the row is the year they were GONE -----------------------

def enrolment(db):
    cols = ','.join(e for _c, _l, e in GRADES)
    rows = q(db, 'SELECT fy, total_cnt, grade_8_cnt, grade_9_cnt, swd_pct, %s '
                 "FROM dese_enrollment WHERE lea=? AND org_level='district' "
                 'ORDER BY fy' % cols, LEA)
    out = {}
    for r in rows:
        if r['k_cnt'] is None:
            continue
        out[int(r['fy'])] = r
    if not out:
        fail('dese_enrollment carries no Lunenburg district rows with a grade breakdown, '
             'and every count of children on this page is a rate times one of them.')
    return out


def _weighted(a, e):
    """The enrolment-weighted mean of the twelve grade rates. NEVER the plain mean: a
    rate off a grade of 40 and a rate off a grade of 140 do not average."""
    num = den = 0.0
    for c, _l, ecol in GRADES:
        if a[c] is None or e[ecol] is None:
            return None
        num += a[c] * float(e[ecol])
        den += float(e[ecol])
    return (num / den) if den else None


def assert_offset(raw, en):
    """WHICH YEAR'S ENROLMENT IS THE DENOMINATOR -- established, not assumed.

    DESE's own `grd_all` is an all-grades rate the file publishes beside the twelve grade
    rates, and it is NOT their plain mean. Weighted by enrolment it has to be one of them.
    Computing it both ways -- against the same year's enrolment and against the previous
    year's -- is a test with a right answer, and the previous year's wins by a factor of
    five. Everything on this page is joined that way.

    THE MARGIN IS THE POINT, not the tolerance. Two joins that are both inside a loose
    tolerance would establish nothing; one that is five times closer than the other is a
    measurement."""
    err = {0: [], -1: []}
    for a in raw:
        for off in err:
            e = en.get(a['sy'] + off)
            if not e:
                continue
            w = _weighted(a, e)
            if w is None or a['grd_all'] is None:
                continue
            err[off].append(abs(w - a['grd_all']))
    for off, v in err.items():
        if len(v) < 10:
            fail('only %d year(s) could be tested for the offset, and the grade join '
                 'this whole page rests on cannot be established from that.' % len(v))
    prior, same = max(err[-1]), max(err[0])
    if prior > OFFSET_TOL:
        fail('joining each attrition row to the PREVIOUS year’s enrolment '
             'reproduces DESE’s own all-grades rate only to %.4f, and this page '
             'requires %.4f. The denominator is not what it was. Nothing written.'
             % (prior, OFFSET_TOL))
    if same <= prior * OFFSET_MARGIN:
        fail('the two candidate joins now agree to within a factor of %.2f (prior '
             '%.4f, same-year %.4f), so the file no longer establishes which year’s '
             'enrolment is the denominator. Every grade on this page would shift by one '
             'if the answer changed.' % (same / prior if prior else 0, prior, same))
    return dict(prior_year_max_error=round(prior, 5),
                same_year_max_error=round(same, 5),
                ratio=round(same / prior, 2), tolerance=OFFSET_TOL,
                years_tested=len(err[-1]))


def assert_grade8_lag(rows, span_rows):
    """THE OFFSET, CHECKED AGAINST A SECOND FILE THAT DOES NOT KNOW ABOUT IT.

    DESE's enrolment file says `Lunenburg High` held grade 8 in FY2013-FY2016. The
    attrition file -- a different collection, published separately -- carries a grade-8
    figure for that school in exactly SY2014-SY2017 and in no other year of eighteen.
    Every year is displaced by exactly one, in both directions, with no exceptions. Two
    files that must agree is worth more than one file read carefully."""
    held = sorted(r['sy'] for r in span_rows
                  if r['org_name'] == HIGH and '8' in r['grades'])
    reported = sorted(r['sy'] for r in rows
                      if r['org_name'] == HIGH and r['stu_grp'] == ALL
                      and r['g08_pct'] is not None)
    if not held or not reported:
        fail('one of the two files no longer says anything about grade 8 at %s, and the '
             'offset check on this page is the two of them agreeing.' % HIGH)
    if [y + 1 for y in held] != reported:
        fail('DESE’s enrolment file says %s held grade 8 in %s, so the attrition '
             'file should carry a grade-8 figure for it in %s. It carries one in %s. The '
             'one-year offset every series on this page is joined on is no longer '
             'established.' % (HIGH, held, [y + 1 for y in held], reported))
    return dict(school=HIGH, enrolment_years=held, attrition_years=reported,
                lag=1, years=len(held))


def assert_group_definition_lag(rows):
    """A THIRD, INDEPENDENT ROUTE TO THE SAME OFFSET, and it comes from DESE's own prose.

    The dataset page says Economically Disadvantaged was used 2015-2021 and Low Income
    before 2015 and again since 2022. Those are ENROLMENT years. If the row labels were
    enrolment years the two groups would appear on rows 2015-2021 and 2010-2014/2022-;
    they appear on rows 2016-2022 and 2010-2015/2023-, which is the same thing displaced
    by one. Nothing about this check touches the grade columns, so it cannot be a
    restatement of either of the other two."""
    out = {}
    for grp in BROKEN:
        yrs = sorted(r['sy'] for r in rows if r['org_type'] == 'District'
                     and r['stu_grp'] == grp and r['grd_all'] is not None)
        if not yrs:
            fail('the %r group has no published district years, and DESE’s own '
                 'statement about when it was used is one of the three routes to the '
                 'offset on this page.' % grp)
        out[grp] = yrs
    ed = out['Economically Disadvantaged']
    if (ed[0], ed[-1]) != (2016, 2022):
        fail('DESE says Economically Disadvantaged was used for enrolment years '
             '2015-2021. Displaced by the one-year offset that is rows SY2016-SY2022, '
             'and this file now carries SY%d-SY%d. Either the offset or the file '
             'changed.' % (ed[0], ed[-1]))
    li = out['Low Income']
    if 2016 in li or 2022 in li:
        fail('Low Income now appears on a row DESE says Economically Disadvantaged '
             'covered. The two definitions are overlapping, and this page draws them as '
             'separate series on that basis.')
    return dict(economically_disadvantaged=ed, low_income=li,
                dese_says=DESE_GROUPS)


# ---- trap 4: a school never reports its own top grade -----------------------------

def assert_terminal_grade(rows, span_rows):
    """THE RULE THAT DECIDES THE WHOLE PAGE, checked on every school-year.

    DESE blanks a grade where the school has "no grade in the given year for students
    from the previous year to advance". A school's TOP grade is exactly that: everyone in
    it advances out of the building, so the school cannot report attrition for it. Which
    means Lunenburg Middle School, grades 6-8, publishes no grade-8 rate -- the largest
    departure in this town is structurally invisible in every school row, and the
    district row is the only place it exists.

    Checked against DESE's own enrolment-by-grade spans, on the one-year offset, for every
    school-year both files cover. Reported as a count rather than asserted to zero
    exceptions, because a school in its first or last year of operation legitimately files
    nothing -- those are named."""
    spans = {(r['sy'], r['org_code']): r for r in span_rows}
    labels = {lab for _c, lab, _e in GRADES}
    checked = exceptions = 0
    bad = []
    for r in rows:
        if r['org_type'] != 'School' or r['stu_grp'] != ALL:
            continue
        sp = spans.get((r['sy'] - 1, r['org_code']))
        if not sp:
            exceptions += 1
            continue
        now = spans.get((r['sy'], r['org_code']))
        if not now or not sp['grades'] or not now['grades']:
            exceptions += 1
            continue
        # DESE'S OWN RULE, APPLIED LITERALLY, and it is not "drop the top grade".
        # A grade is blank where the school has "no grade in the given year for students
        # from the previous year to advance" -- so grade g is reportable in SY only if
        # the school holds grade g+1 THAT YEAR. Usually that is the top grade and nothing
        # else, which is why the shortcut looks right; it is wrong in exactly the years
        # the town reorganised, when Lunenburg Primary gained grade 3 and its second
        # grade became reportable for the first time. Written as the rule rather than as
        # its usual consequence, the reorganisation years pass instead of being excused.
        nxt = set(now['grades'])
        expect = {g for g in sp['grades']
                  if g in labels and ORDER.get(g) in nxt}
        if not expect:
            exceptions += 1
            continue
        got = {lab for c, lab, _e in GRADES if r[c] is not None}
        checked += 1
        if got != expect:
            bad.append(dict(sy=r['sy'], org=r['org_name'], span=sp['span'],
                            expected=sorted(expect), got=sorted(got)))
    if not checked:
        fail('no school-year could be checked against the terminal-grade rule. A join '
             'that matches nothing looks exactly like a rule that holds.')
    if bad:
        fail('%d school-year(s) publish a set of grades that is not "every grade the '
             'school held the year before, except its top one" -- e.g. %s. That rule is '
             'why the grade-8 finding on this page is drawn at district level, and it no '
             'longer holds.' % (len(bad), bad[0]))
    return dict(school_years_checked=checked, exceptions=exceptions,
                dese_says=DESE_BLANKS)


# ---- the district series ----------------------------------------------------------

def district_series(rows, en):
    got = [r for r in rows if r['org_type'] == 'District' and r['stu_grp'] == ALL]
    if not got:
        fail('there is no Lunenburg district row for %s. A join that matches nothing '
             'looks exactly like a town nobody leaves.' % ALL)
    out = []
    for r in sorted(got, key=lambda r: r['sy']):
        if r['grd_all'] is None:
            fail('SY%d has no all-grades rate, and this page differences against it.'
                 % r['sy'])
        e = en.get(r['sy'] - 1)
        row = dict(sy=r['sy'], cohort_fy=r['sy'] - 1, all=r['grd_all'],
                   grades=[dict(grade=lab, rate=r[c]) for c, lab, _e in GRADES])
        if e:
            row['cohort'] = int(sum(e[ecol] for _c, _l, ecol in GRADES))
            row['implied'] = round(r['grd_all'] * row['cohort'], 1)
            row['grade8_cohort'] = int(e['grade_8_cnt'] or 0)
            row['grade8_implied'] = round((r['g08_pct'] or 0) * row['grade8_cohort'], 1)
        out.append(row)
    if len(out) < 10:
        fail('only %d district years are in the file and this page draws a series across '
             'a reorganisation and a pandemic.' % len(out))
    return out


def grade_profile(dist):
    """Every grade, over every year: what it averages and how often it is the worst.

    `times_highest` is COUNTED, never asserted. The finding on this page is that one grade
    is the highest in every year measured, and a page that hardcodes that is a page that
    goes on saying it after it stops being true."""
    prof = []
    highest = collections.Counter()
    for row in dist:
        best = max(row['grades'], key=lambda g: (g['rate'] is not None, g['rate'] or -1))
        highest[best['grade']] += 1
    for _c, lab, _e in GRADES:
        v = [g['rate'] for row in dist for g in row['grades']
             if g['grade'] == lab and g['rate'] is not None]
        if not v:
            fail('grade %s has no published rate in any year, which has never been true '
                 'of a Lunenburg district row.' % lab)
        yrs = {g['rate']: row['sy'] for row in dist for g in row['grades']
               if g['grade'] == lab and g['rate'] is not None}
        prof.append(dict(grade=lab, mean=round(statistics.mean(v), 4),
                         median=round(statistics.median(v), 4),
                         min=min(v), min_sy=yrs[min(v)],
                         max=max(v), max_sy=yrs[max(v)],
                         years=len(v), times_highest=highest[lab]))
    return prof


def the_outlier(prof, dist):
    """The one grade that stands off the other eleven, DERIVED.

    Nothing in this function knows which grade it is. If the profile ever stops having a
    single grade that is highest in every measured year, the page stops claiming one."""
    top = max(prof, key=lambda p: p['mean'])
    rest = [p for p in prof if p['grade'] != top['grade']]
    runner = max(rest, key=lambda p: p['mean'])
    if top['times_highest'] != len(dist):
        fail('grade %s is the highest in %d of %d years rather than in all of them, and '
             'the first conclusion on this page is written as "every year". Re-derive it '
             'before publishing.' % (top['grade'], top['times_highest'], len(dist)))
    series = [dict(sy=r['sy'], cohort_fy=r['cohort_fy'],
                   rate=[g['rate'] for g in r['grades'] if g['grade'] == top['grade']][0],
                   cohort=r.get('grade8_cohort'), implied=r.get('grade8_implied'))
              for r in dist]
    if any(s['rate'] is None for s in series):
        fail('a year of the grade %s series has no rate. A hole and a zero are different '
             'facts and this page draws a line.' % top['grade'])
    latest = series[-1]
    ranked = sorted(series, key=lambda s: -s['rate'])
    rank = 1 + [s['sy'] for s in ranked].index(latest['sy'])
    # A RUN OF RISES, counted rather than eyeballed -- and the longest run BEFORE this
    # one, because "three years of increases" is only a finding if the series has not
    # done it before.
    runs, cur = [], 1
    for a, b in zip(series, series[1:]):
        cur = cur + 1 if b['rate'] > a['rate'] else 1
        runs.append(dict(end_sy=b['sy'], length=cur))
    now = runs[-1]['length']
    prior = max([r['length'] for r in runs[:-1]] or [0])
    return dict(
        grade=top['grade'], mean=top['mean'], median=top['median'],
        min=top['min'], min_sy=top['min_sy'], max=top['max'], max_sy=top['max_sy'],
        runner_up=runner['grade'], runner_up_mean=runner['mean'],
        multiple=round(top['mean'] / runner['mean'], 1),
        others_low=min(p['mean'] for p in rest), others_high=runner['mean'],
        series=series, latest=latest, rank_of_latest=rank, years=len(series),
        rising_run=now, longest_prior_rising_run=prior,
        implied_total=round(sum(s['implied'] for s in series if s['implied']), 0),
        implied_years=len([s for s in series if s['implied'] is not None]),
    )


def churn(dist, en):
    """The size of the leaving against the size of the change, which is the question a
    resident actually arrives with -- is attrition why the schools are emptying?

    THE COUNT IS IMPLIED AND SAYS SO. DESE publishes a rate and an enrolment; this
    multiplies them. It is not a headcount anybody published, and it is not a count of
    distinct children: a child who leaves and returns is two events here and one child."""
    have = [r for r in dist if r.get('implied') is not None]
    if len(have) < 10:
        fail('only %d years can be turned into a number of children, and the comparison '
             'against the enrolment change needs the whole span.' % len(have))
    first_fy, last_fy = have[0]['cohort_fy'], have[-1]['sy']
    if first_fy not in en or last_fy not in en:
        fail('the enrolment file does not cover both ends of the implied-departure span.')
    a, b = int(en[first_fy]['total_cnt']), int(en[last_fy]['total_cnt'])
    total = sum(r['implied'] for r in have)
    return dict(first_fy=first_fy, last_fy=last_fy, transitions=len(have),
                implied_total=round(total),
                per_year=round(total / len(have), 1),
                enrol_first=a, enrol_last=b, enrol_change=b - a,
                ratio=round(total / abs(b - a), 1) if b != a else None,
                years=[dict(sy=r['sy'], cohort_fy=r['cohort_fy'], cohort=r['cohort'],
                            rate=r['all'], implied=r['implied']) for r in have])


def grade9_intake(outlier, en):
    """The other half, and the one the net hides.

    Of every eighth grade, DESE's rate says how many did not come back. What the enrolment
    file then shows is how large grade 9 actually was -- and the difference is children in
    grade 9 who were not in Lunenburg's own grade 8. That is a RESIDUAL across two files
    and it is labelled as one: arrivals from anywhere, and anybody repeating the year, are
    the same number here."""
    out = []
    for s in outlier['series']:
        e, nxt = en.get(s['cohort_fy']), en.get(s['sy'])
        if not e or not nxt or not nxt['grade_9_cnt']:
            continue
        g8 = int(e['grade_8_cnt'] or 0)
        stayed = g8 * (1 - s['rate'])
        g9 = int(nxt['grade_9_cnt'])
        out.append(dict(cohort_fy=s['cohort_fy'], sy=s['sy'], grade8=g8,
                        rate=s['rate'], stayed=round(stayed, 1), grade9=g9,
                        residual=round(g9 - stayed, 1)))
    if len(out) < 10:
        fail('only %d grade 8 to grade 9 steps could be built, and the page draws a '
             'series.' % len(out))
    up = [r for r in out if r['residual'] > 0]
    return dict(years=out, steps=len(out), larger=len(up),
                mean_residual=round(statistics.mean(r['residual'] for r in out), 1),
                mean_leaving=round(statistics.mean(
                    r['grade8'] * r['rate'] for r in out), 1))


# ---- the eras, on the same mechanism /what-courses-actually-ran uses ---------------

def era_series(dist, bands, outlier):
    """The five eras, and the grade series averaged inside each.

    WHY THIS IS NOT DECORATION. Two findings on /what-courses-actually-ran did not survive
    era segmentation -- both were an eighth grade arriving in a building and leaving
    again. A grade-level series is MORE exposed to that than a subject one, so it is
    checked the same way. What the check finds here is the opposite of what it found
    there: the district's grade series is flat across every boundary, because a grade is a
    grade wherever the town houses it."""
    out = []
    for b in bands:
        yrs = [r for r in dist if b['first_sy'] <= r['sy'] <= b['last_sy']]
        if not yrs:
            continue
        g = [x['rate'] for r in yrs for x in r['grades']
             if x['grade'] == outlier['grade'] and x['rate'] is not None]
        out.append(dict(b, years_in_file=len(yrs),
                        outlier_mean=round(statistics.mean(g), 4),
                        all_mean=round(statistics.mean(r['all'] for r in yrs), 4)))
    if len(out) < 4:
        fail('only %d eras carry attrition years, and this page is written around a '
             'segmentation with a structural break, a reset and a shock in it.' % len(out))
    lo = min(out, key=lambda e: e['outlier_mean'])
    hi = max(out, key=lambda e: e['outlier_mean'])
    return dict(bands=out, low=lo, high=hi,
                spread=round(hi['outlier_mean'] - lo['outlier_mean'], 4))


def school_artefact(rows, span_rows, outlier):
    """THE SAME NUMBER, DRAWN TWO WAYS, AND ONE OF THEM IS A BUILDING PROGRAMME.

    `Lunenburg High` is one school with one name and its own published attrition rate for
    eighteen years. In four of them it held grade 8 -- the grade this page finds is the
    largest departure in the town -- and its rate is a third higher in exactly those four
    years. Nothing about any child changed. This is why the district series carries the
    page and the school series is shown only to make the trap visible."""
    got = [r for r in rows if r['org_name'] == HIGH and r['stu_grp'] == ALL
           and r['grd_all'] is not None]
    spans = {r['sy']: r for r in span_rows if r['org_name'] == HIGH}
    col = [c for c, lab, _e in GRADES if lab == outlier['grade']]
    if not col:
        fail('the outlier grade has no column, which cannot happen.')
    col = col[0]
    with_g, without = [], []
    series = []
    for r in sorted(got, key=lambda r: r['sy']):
        sp = spans.get(r['sy'] - 1)
        has = r[col] is not None
        (with_g if has else without).append(r['grd_all'])
        series.append(dict(sy=r['sy'], cohort_fy=r['sy'] - 1, all=r['grd_all'],
                           held_outlier_grade=has,
                           span=sp['span'] if sp else 'not stated'))
    if not with_g or not without:
        fail('%s no longer has years both with and without grade %s, and the artefact '
             'this section exists to show is not visible in the file.'
             % (HIGH, outlier['grade']))
    a, b = statistics.mean(with_g), statistics.mean(without)
    return dict(school=HIGH, grade=outlier['grade'], series=series,
                with_mean=round(a, 4), with_years=len(with_g),
                without_mean=round(b, 4), without_years=len(without),
                points=round((a - b) * 100, 1),
                ratio=round(a / b, 2))


# ---- the selected populations -----------------------------------------------------

def groups(rows, en, outlier):
    """Every student group, at the outlier grade and across all grades.

    THE COHORT BOUND IS THE POINT AND IT IS PUBLISHED BESIDE EVERY RATE. A Lunenburg grade
    is about a hundred and twenty children; the group inside it can be a dozen. One family
    moving is several percentage points, and a page that draws these without saying so is
    inviting a conclusion the arithmetic will not carry. The bound is an ESTIMATE -- DESE
    publishes no group count by grade -- built from the district's own published share of
    that group applied to the grade's own enrolment, and it is labelled as one everywhere
    it appears."""
    col = [c for c, lab, _e in GRADES if lab == outlier['grade']][0]
    base = [g for g in groups_present(rows) if g in SELECTED]
    out = []
    for grp in SELECTED:
        if grp not in base:
            fail('the %r group is no longer in the file and this page draws it.' % grp)
        got = sorted((r for r in rows if r['org_type'] == 'District'
                      and r['stu_grp'] == grp), key=lambda r: r['sy'])
        series = [dict(sy=r['sy'], cohort_fy=r['sy'] - 1, rate=r[col], all=r['grd_all'])
                  for r in got]
        pub = [s for s in series if s['rate'] is not None]
        alls = [s for s in series if s['all'] is not None]
        row = dict(grp=grp, series=series, published_years=len(pub),
                   years=len(series), broken=grp in BROKEN,
                   all_mean=round(statistics.mean(s['all'] for s in alls), 4)
                   if alls else None)
        if pub:
            row.update(mean=round(statistics.mean(s['rate'] for s in pub), 4),
                       min=min(s['rate'] for s in pub),
                       max=max(s['rate'] for s in pub),
                       first_sy=pub[0]['sy'], last_sy=pub[-1]['sy'])
        out.append(row)
    ref = [r for r in out if r['grp'] == ALL][0]
    if 'mean' not in ref:
        fail('%r has no published rate at grade %s, which is the comparison every other '
             'group on this page is drawn against.' % (ALL, outlier['grade']))
    for r in out:
        if 'mean' in r:
            r['gap_points'] = round((r['mean'] - ref['mean']) * 100, 1)
    return out, ref


def groups_present(rows):
    return sorted({r['stu_grp'] for r in rows})


def group_gap_by_grade(rows, grp, dist):
    """WHERE a group's gap actually sits, grade by grade -- because a group that leaves
    more everywhere is a different fact from one that leaves more at one step.

    Both series are enrolment-unweighted means over the same years, which is legitimate
    HERE and nowhere else on this page: it is one grade compared with itself across two
    student groups, never one grade averaged against another."""
    got = [r for r in rows if r['org_type'] == 'District' and r['stu_grp'] == grp]
    if not got:
        fail('the %r group has no district rows.' % grp)
    out = []
    for c, lab, _e in GRADES:
        theirs = [r[c] for r in got if r[c] is not None]
        ours = [g['rate'] for row in dist for g in row['grades']
                if g['grade'] == lab and g['rate'] is not None]
        if not theirs or not ours:
            continue
        out.append(dict(grade=lab, group_mean=round(statistics.mean(theirs), 4),
                        all_mean=round(statistics.mean(ours), 4),
                        gap_points=round((statistics.mean(theirs)
                                          - statistics.mean(ours)) * 100, 1),
                        years=len(theirs)))
    if not out:
        fail('no grade could be compared between %r and %r.' % (grp, ALL))
    top = max(out, key=lambda r: r['gap_points'])
    rest = [r for r in out if r['grade'] != top['grade']]
    return dict(grp=grp, grades=out, widest=top,
                next_widest=max(rest, key=lambda r: r['gap_points']))


# ---- where they went, which nobody publishes --------------------------------------

def destinations(db, outlier):
    """The one file that says where the town's children are, and the column it has not
    got. `dese_town_enrollment` names a receiving district and a reason and carries NO
    GRADE, so it can size the candidates and can never attribute one departure."""
    rows = q(db, 'SELECT fy, enrollment_reason, district, students '
                 "FROM dese_town_enrollment WHERE town='Lunenburg' ORDER BY fy",
             )
    if not rows:
        fail('dese_town_enrollment holds no Lunenburg rows, and the section naming what '
             'this page cannot attribute rests on it.')
    cols = [d[0] for d in db.execute(
        'SELECT * FROM dese_town_enrollment LIMIT 1').description]
    if any('grade' in c for c in cols):
        fail('dese_town_enrollment now has a grade column. That is the document that '
             'would close the biggest gap on this page, and the page says it does not '
             'exist. Rewrite the section before publishing.')
    last = max(int(r['fy']) for r in rows)
    here = [r for r in rows if int(r['fy']) == last]
    away = [r for r in here if not (r['enrollment_reason'] == 'Resident/Member'
                                    and r['district'] == 'Lunenburg')]
    by_reason = collections.Counter()
    for r in away:
        by_reason[r['enrollment_reason']] += int(r['students'])
    monty = [r for r in away if 'Montachusett' in r['district']]
    if not monty:
        fail('Monty Tech is not in the town file for FY%d, and it is the largest '
             'candidate destination this page names.' % last)
    return dict(
        fy=last, columns=cols,
        elsewhere=sum(int(r['students']) for r in away),
        by_reason=[dict(reason=k, students=v) for k, v in by_reason.most_common()],
        monty_tech=int(monty[0]['students']),
        monty_grades=4,
        monty_per_grade=round(int(monty[0]['students']) / 4, 1),
        outlier_grade=outlier['grade'],
        series=[dict(fy=int(r['fy']), students=int(r['students'])) for r in rows
                if 'Montachusett' in r['district']],
    )


# ---- the meeting record -----------------------------------------------------------

def said_in_meetings():
    out = []
    for spec in QUOTES:
        rel = '%s/%s/%s-%s-%s.txt' % (MINUTES, spec['board'], spec['date'],
                                      spec['kind'], spec['doc'])
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            fail('%s is not here — a quote on this page is attributed to a document '
                 'that is not in the archive' % rel)
        text = re.sub(r'\s+', ' ', open(path, encoding='utf-8', errors='replace').read())
        want = re.sub(r'\s+', ' ', spec['quote'])
        if want not in text:
            fail('the quote attributed to %s %s is no longer in %s — quote the '
                 'source, never your rendering of it (rule 13)'
                 % (spec['board'], spec['date'], rel))
        kind = 'Minutes' if spec['kind'] == 'minutes' else 'Agenda'
        out.append(dict(
            key=spec['key'], board=spec['board'].replace('-', ' ').title(),
            date=spec['date'], quote=spec['quote'], why=spec['why'], who=spec['who'],
            kind=kind, cite='/docs/' + rel.replace('sources/', ''),
            town='https://www.lunenburgma.gov/AgendaCenter/ViewFile/%s/_%s%s%s-%s'
                 % (kind, spec['date'][5:7], spec['date'][8:10], spec['date'][:4],
                    spec['doc'])))
    return out


def searched():
    idx = os.path.join(ROOT, 'sources/meetings/index.csv')
    if not os.path.exists(idx):
        fail('sources/meetings/index.csv is not here — a search of nothing is not '
             'a search')
    rows = list(csv.DictReader(open(idx, encoding='utf-8')))
    readable = []
    for r in rows:
        stem = os.path.splitext(r['path'])[0] if r['path'].strip() else ''
        txt = os.path.join(ROOT, MINUTES, stem + '.txt') if stem else ''
        if stem and os.path.exists(txt):
            readable.append(txt)
    if not readable:
        fail('no meeting document is readable — refusing to publish a count of '
             'what nobody said')
    bodies = [re.sub(r'\s+', ' ', open(t, encoding='utf-8', errors='replace').read())
              for t in readable]
    terms = [dict(term=t,
                  documents=sum(1 for b in bodies
                                if re.search(r'\b%s' % re.escape(t), b, re.I)))
             for t in SEARCHED]
    if not any(t['documents'] for t in terms):
        fail('not one search term matched any document. The archive did not go quiet; '
             'something is wrong with the read.')
    cov = os.path.join(ROOT, 'sources/data/minutes-searchable.csv')
    if not os.path.exists(cov):
        fail('sources/data/minutes-searchable.csv is not here — the searchable '
             'share cannot be typed')
    tally = collections.Counter()
    for r in csv.DictReader(open(cov, encoding='utf-8')):
        for k in ('held', 'searchable', 'unsearchable', 'image_scan'):
            tally[k] += int(r[k] or 0)
    if not tally['searchable'] or tally['held'] != tally['searchable'] + tally['unsearchable']:
        fail('minutes-searchable.csv does not reconcile — refusing to publish a '
             'coverage figure that does not add up')
    return terms, dict(held=tally['held'], searchable=tally['searchable'],
                       unsearchable=tally['unsearchable'],
                       image_scan=tally['image_scan'],
                       searchable_share=round(tally['searchable'] / tally['held'], 4))


def split_gap(gap):
    why, closes = gap['why'], None
    marker = '— closes:'
    if marker in why:
        why, closes = why.split(marker, 1)
        why, closes = why.strip(), closes.strip()
    return dict(side=gap['side'], what=gap['what'], why=why, closes=closes)


def gaps():
    rows = list(csv.DictReader(open(GAPS, encoding='utf-8')))
    if not rows:
        fail('money-gaps.csv is empty.')
    by_what = {r['what']: r for r in rows}
    missing = [w for w in CITES_GAPS if w not in by_what]
    if missing:
        fail('this page cites money_gaps rows that are not in the register: %s\n'
             'Rule 7c: the registry outranks the page.' % missing)
    return [split_gap(by_what[w]) for w in CITES_GAPS]


# ---- what this page cannot say ----------------------------------------------------

def not_established(outlier, art, dest, grp_gap, era, terminal, groups_rows):
    ell = [g for g in groups_rows if g['grp'] == 'English Learners'][0]
    return [
        'WHY anybody left. Attrition is leaving for any reason. A vocational admission, a '
        'private school, a charter, a school choice transfer, an out-of-district '
        'placement and a family moving for work are one number in this file, and nothing '
        'in it separates them.',

        'Where they went. DESE’s own file of where the town’s resident children '
        'are educated carries a receiving district and a reason and NO GRADE, so the '
        '%s children educated somewhere else in FY%d cannot be attributed to the grade '
        'they left in. Monty Tech holds %s of them across %s grade years — about '
        '%s a year, which is the same order of magnitude as this page’s implied '
        'grade %s departures and is not evidence that they are the same children.'
        % (C.num(dest['elsewhere']), dest['fy'], C.num(dest['monty_tech']),
           C.num(dest['monty_grades']), dest['monty_per_grade'], outlier['grade']),

        'Anything about a school, at the grade that matters. DESE blanks the top grade of '
        'every school, because everybody in it advances out of the building — so '
        'Lunenburg Middle School, which ends at grade %s, publishes no grade %s rate at '
        'all. The rule was checked on %s school-years here. Every finding about grade %s '
        'on this page is a DISTRICT figure, and there is no school-level version of it '
        'to be had.'
        % (outlier['grade'], outlier['grade'], C.num(terminal['school_years_checked']),
           outlier['grade']),

        '%s’s own rate over time. It averages %s in the %s years the school held '
        'grade %s and %s in the other %s, a difference of %s points that is a building '
        'programme rather than a change in anybody’s behaviour. It is on this page '
        'only to make that visible.'
        % (art['school'], C.pct(art['with_mean'] * 100), C.num(art['with_years']),
           art['grade'], C.pct(art['without_mean'] * 100), C.num(art['without_years']),
           art['points']),

        'A trend in the selected populations. English Learners have a published '
        'all-grades rate in %s of %s years and no published grade %s rate in any year, '
        'because DESE suppresses a cell whose enrolment is under six. A group of a dozen '
        'children moves several points when one family does, and nothing on this page '
        'divides a group rate by anything.'
        % (C.num(sum(1 for s in ell['series'] if s['all'] is not None)),
           C.num(ell['years']), outlier['grade']),

        'A count of children who left. Every number of children on this page is DESE’s '
        'rate multiplied by DESE’s enrolment, and it is an implied figure rather '
        'than a headcount anybody published. It is also not a count of distinct '
        'children: a child who leaves and comes back is two events here.',

        'Whether the town side has anything like this. Massachusetts collects an '
        'attrition rate from school districts and from nothing else, so no comparison '
        'between the two halves of the town budget can be drawn from this page in either '
        'direction.',

        'Anything about a person. Every figure here is a rate over a grade cohort. Where '
        'a quote names somebody it is a role in a public meeting record, quoted for what '
        'it describes.',
    ]


def closes(dest, outlier):
    return ('DESE already publishes where every Lunenburg resident child is educated '
            '— %s of them somewhere other than a Lunenburg school in FY%d — '
            'and publishes an attrition rate per grade. The two files never meet: one '
            'has no grade and the other has no destination. One column added to the '
            'first would say which grade each of those children left in, and would turn '
            'the largest measurement on this page from a rate into an answer.'
            % (C.num(dest['elsewhere']), dest['fy']))


def differently(outlier, dest):
    """The Finance Committee's test in notes/process/PERSONAS.md: one thing that could be
    done differently next year. Deliberately the cheapest possible ask -- the district
    already files the data that answers this to the state every October."""
    return ('Report the grade %s exit count to the School Committee each autumn, beside '
            'the October enrolment. The district files the submission that produces this '
            'rate to the state every 1 October, so the number exists inside the district '
            'before DESE publishes it — and it is the one figure that would let a '
            'board tell a year when %s of an eighth grade left from a year when a third '
            'did, while there is still a budget cycle to do anything about it.'
            % (outlier['grade'], C.pct(outlier['min'] * 100)))


# ---- what this page establishes ---------------------------------------------------

def sy(y):
    return figure(y, 'SY%d' % int(y))


def build_conclusions(outlier, prof, ch, grp_gap, era, dest, groups_rows, g9):
    swd = [g for g in groups_rows if g['grp'] == 'Students with Disabilities'][0]
    ref = [g for g in groups_rows if g['grp'] == ALL][0]
    others = sorted(p for p in
                    [x['mean'] for x in prof if x['grade'] != outlier['grade']])
    rows = [
        conclusion(
            id='one-grade-does-all-the-leaving',
            claim='One in five eighth graders does not come back to a Lunenburg school '
                  'for grade 9.',
            so_what='The highest grade in all %s years measured. The other eleven sit '
                    'between %s and %s.'
                    % (C.num(outlier['years']), C.pct(others[0] * 100),
                       C.pct(others[-1] * 100)),
            figures={
                'mean': figure(outlier['mean'], C.pct(outlier['mean'] * 100),
                               'of each eighth grade'),
                'years': figure(outlier['years'], C.num(outlier['years'])),
                'low': figure(others[0], C.pct(others[0] * 100)),
                'high': figure(others[-1], C.pct(others[-1] * 100)),
                'multiple': figure(outlier['multiple'], str(outlier['multiple'])),
                'per_year': figure(round(outlier['implied_total']
                                         / outlier['implied_years']),
                                   C.num(outlier['implied_total']
                                         / outlier['implied_years'])),
                'total': figure(outlier['implied_total'],
                                C.num(outlier['implied_total'])),
            },
            figure='mean',
            kind='measured',
            bearing='sizes',
            lede='Residents keep asking which grades children leave in. It is one '
                 'grade, it is the same grade every year, and the step it sits at is '
                 'the move from the middle school to the high school.',
            detail='Averaged over the whole file the grade 8 rate is %s times the next '
                   'highest grade, and it is the highest grade in every single year '
                   'measured — through a school closing, a new building opening '
                   'and a pandemic. Applied to the town’s own eighth grades that is '
                   'about %s children a year and roughly %s in total. Those counts are '
                   'IMPLIED — DESE publishes the rate and the enrolment, and this '
                   'page multiplies them.'
                   % (str(outlier['multiple']),
                      C.num(outlier['implied_total'] / outlier['implied_years']),
                      C.num(outlier['implied_total'])),
            basis='`dese_attrition`, Lunenburg’s district rows for All Students, '
                  'joined to `dese_enrollment` on the PREVIOUS year’s grade counts '
                  '— which is the join DESE’s own all-grades rate reproduces '
                  'five times more closely than the same-year one, and which two other '
                  'independent checks in the generator confirm.',
            not_shown='Why, and where to. Attrition is leaving for any reason: a '
                      'vocational admission at grade 9, a private or charter school, a '
                      'school choice transfer, an out-of-district placement and a family '
                      'moving are one number here. Nothing in this file separates them, '
                      'and the file that names destinations carries no grade.',
            see=[('/where-students-go-instead', 'Where the town’s children are'),
                 ('/monty-tech', 'What Monty Tech costs the town')],
        ),
        conclusion(
            id='a-high-year-not-a-new-level',
            claim='The eighth grade measured this year lost %s — the '
                  '%s-highest of seventeen years.'
                  % (C.pct(outlier['latest']['rate'] * 100),
                     'second' if outlier['rank_of_latest'] == 2
                     else C.num(outlier['rank_of_latest'])),
            so_what='Averaged inside five eras the rate stays between %s and %s. '
                    'A high year, not a new level.'
                    % (C.pct(era['low']['outlier_mean'] * 100),
                       C.pct(era['high']['outlier_mean'] * 100)),
            figures={
                'latest': figure(outlier['latest']['rate'],
                                 C.pct(outlier['latest']['rate'] * 100),
                                 'of the last eighth grade'),
                'era_low': figure(era['low']['outlier_mean'],
                                  C.pct(era['low']['outlier_mean'] * 100)),
                'era_high': figure(era['high']['outlier_mean'],
                                   C.pct(era['high']['outlier_mean'] * 100)),
                'max': figure(outlier['max'], C.pct(outlier['max'] * 100)),
                'max_sy': sy(outlier['max_sy']),
                'min': figure(outlier['min'], C.pct(outlier['min'] * 100)),
                'min_sy': sy(outlier['min_sy']),
                'run': figure(outlier['rising_run'], C.num(outlier['rising_run'])),
                'prior_run': figure(outlier['longest_prior_rising_run'],
                                    C.num(outlier['longest_prior_rising_run'])),
                'spread': figure(era['spread'], C.points(era['spread'] * 100)),
            },
            figure='latest',
            kind='measured',
            bearing='sizes',
            lede='The rate has risen for the last stretch of the series, which is what a '
                 'reader will notice first. Set against seventeen years it is inside a '
                 'range the town has been in the whole time.',
            detail='The series runs from %s in %s to %s in %s and the five eras — '
                   'built from DESE’s own grade spans, so a school closing and a new '
                   'building are boundaries rather than noise — average within %s '
                   'of each other. The current run of rises is %s years long and the '
                   'longest earlier one was %s, so a run of this length is not new '
                   'either. A single Lunenburg grade is around a hundred and twenty '
                   'children, so one family is close to a point.'
                   % (C.pct(outlier['min'] * 100), 'SY%d' % outlier['min_sy'],
                      C.pct(outlier['max'] * 100), 'SY%d' % outlier['max_sy'],
                      C.points(era['spread'] * 100), C.num(outlier['rising_run']),
                      C.num(outlier['longest_prior_rising_run'])),
            basis='The same district rows, averaged inside eras derived in code from '
                  '`dese_enrollment` grade spans by the functions '
                  '/what-courses-actually-ran uses, so the two pages cannot segment the '
                  'same reorganisation differently. The pandemic boundary is OURS and is '
                  'marked as ours wherever it appears.',
            not_shown='Whether the rise continues. Three points are three points, and '
                      'this town’s boards are being asked to read them as a '
                      'direction because they have nothing longer. The eras are on the '
                      'page precisely so a reader can see what the same three points '
                      'looked like the last four times.',
        ),
        conclusion(
            id='the-leaving-is-nine-times-the-fall',
            claim='DESE’s rates imply %s children left in seventeen years. '
                  'Enrolment fell %s.'
                  % (C.num(ch['implied_total']), C.num(abs(ch['enrol_change']))),
            so_what='Churn is %s times the net change, so arrivals rather than leavers '
                    'set the size of the schools.' % str(ch['ratio']),
            figures={
                'implied': figure(ch['implied_total'], C.num(ch['implied_total']),
                                  'children, implied'),
                'fall': figure(abs(ch['enrol_change']), C.num(abs(ch['enrol_change']))),
                'ratio': figure(ch['ratio'], str(ch['ratio'])),
                'per_year': figure(ch['per_year'], C.num(ch['per_year'])),
                'first': figure(ch['enrol_first'], C.num(ch['enrol_first'])),
                'last': figure(ch['enrol_last'], C.num(ch['enrol_last'])),
                'first_fy': figure(ch['first_fy'], 'FY%d' % ch['first_fy']),
                'last_fy': figure(ch['last_fy'], 'FY%d' % ch['last_fy']),
            },
            figure='implied',
            kind='measured',
            bearing='sizes',
            lede='The question a resident arrives with is whether children leaving is '
                 'why the schools are emptying. On these two files it is not: the '
                 'leaving is an order of magnitude larger than the change, and almost '
                 'all of it is replaced.',
            detail='About %s children a year leave, every year, and district enrolment '
                   'went from %s in %s to %s in %s. A town losing %s children a year net '
                   'and a town losing %s and gaining most of them back are the same '
                   'line on an enrolment chart and are not the same town. This is the '
                   'same shape /if-students-leave found on the other side of the '
                   'ledger, where inbound school choice collapsed while outbound stayed '
                   'flat and the net barely moved.'
                   % (C.num(ch['per_year']), C.num(ch['enrol_first']),
                      'FY%d' % ch['first_fy'], C.num(ch['enrol_last']),
                      'FY%d' % ch['last_fy'],
                      C.num(abs(ch['enrol_change']) / ch['transitions']),
                      C.num(ch['per_year'])),
            basis='DESE’s all-grades attrition rate for each year applied to the '
                  'previous year’s Lunenburg enrolment in grades K to 11, against '
                  'DESE’s own district totals at both ends. Grade 12 is excluded '
                  'from the rate by DESE: a twelfth grader who does not come back has '
                  'graduated.',
            not_shown='Who arrives. This page measures one direction only and the '
                      'balancing figure is a RESIDUAL rather than a measurement — '
                      'births, families moving in, children returning from a private '
                      'school and anybody repeating a year are one number here. Nor is '
                      'the implied total a count of distinct children.',
            see=[('/if-students-leave', 'The other direction, priced')],
        ),
        conclusion(
            id='the-gap-is-at-one-step-not-everywhere',
            claim='Eighth graders on an IEP leave at %s, against %s for all students.'
                  % (C.pct(swd['mean'] * 100), C.pct(ref['mean'] * 100)),
            so_what='The gap is %s at grade 8 and never above %s at any other grade.'
                    % (C.points(grp_gap['widest']['gap_points']),
                       C.points(grp_gap['next_widest']['gap_points'])),
            figures={
                'swd': figure(swd['mean'], C.pct(swd['mean'] * 100),
                              'of eighth graders on an IEP'),
                'all': figure(ref['mean'], C.pct(ref['mean'] * 100)),
                'widest': figure(grp_gap['widest']['gap_points'],
                                 C.points(grp_gap['widest']['gap_points'])),
                'next': figure(grp_gap['next_widest']['gap_points'],
                               C.points(grp_gap['next_widest']['gap_points'])),
                'lo': figure(swd['min'], C.pct(swd['min'] * 100)),
                'hi': figure(swd['max'], C.pct(swd['max'] * 100)),
                'years': figure(swd['published_years'],
                                C.num(swd['published_years'])),
            },
            figure='swd',
            kind='measured',
            bearing='sizes',
            lede='A group that leaves more everywhere is a different fact from one that '
                 'leaves more at a single step. This is the second: across the other '
                 'eleven grades the two series are close together.',
            detail='Published in all %s years, and it swings from %s to %s between them '
                   '— because the group inside one Lunenburg grade is on the order '
                   'of twenty children, so one family is several points. That is the '
                   'reason the year-by-year sits under this card rather than a headline '
                   'off any single year. The same shape appears for High Needs and for '
                   'Low Income, which OVERLAP this group and each other and are never '
                   'added.'
                   % (C.num(swd['published_years']), C.pct(swd['min'] * 100),
                      C.pct(swd['max'] * 100)),
            basis='`dese_attrition` district rows for Students with Disabilities against '
                  'All Students, grade by grade, over the same years. The cohort sizes '
                  'beside them are ESTIMATES: DESE publishes no count of a student group '
                  'within a grade, so they are the district’s own published share '
                  'of that group applied to the grade’s enrolment.',
            not_shown='Anything about placement, service or cause. An out-of-district '
                      'placement made at the high school transition, a vocational '
                      'admission, a family moving for services and a private school all '
                      'fit this number equally well. A special education placement is '
                      'not attrition and this file cannot tell you which of these it '
                      'counted.',
            see=[('/who-ends-up-out-of-district', 'The route out of district'),
                 ('/how-many-students-are-on-an-iep', 'How many children are on an IEP')],
        ),
        conclusion(
            id='nothing-published-says-where-they-went',
            claim='No published record says which school a departing Lunenburg eighth '
                  'grader went to.',
            so_what='Monty Tech, a private school, a charter and a family moving are one '
                    'number here.',
            figures={
                'elsewhere': figure(dest['elsewhere'], C.num(dest['elsewhere'])),
                'fy': figure(dest['fy'], 'FY%d' % dest['fy']),
                'monty': figure(dest['monty_tech'], C.num(dest['monty_tech'])),
                'per_grade': figure(dest['monty_per_grade'],
                                    str(dest['monty_per_grade'])),
                'implied': figure(round(outlier['implied_total']
                                        / outlier['implied_years']),
                                  C.num(outlier['implied_total']
                                        / outlier['implied_years'])),
            },
            no_figure='There is no figure here because nobody publishes one. DESE '
                      'publishes the rate without a destination and the destination '
                      'without a grade, and the two files are never joined.',
            kind='measured',
            bearing='lever',
            lede='This is the question every reader of the card above will ask next, and '
                 'it is the one the record refuses. Two DESE files each hold half of the '
                 'answer and neither holds the join.',
            detail='%s Lunenburg children were educated somewhere other than a Lunenburg '
                   'school in %s. Monty Tech holds %s of them across four grade years, '
                   'about %s a year, which is the same order of magnitude as the %s '
                   'eighth graders a year this page implies are leaving — and being '
                   'the same size is not being the same children. Lunenburg is a MEMBER '
                   'town of Monty Tech, so a child going there is not choosing out of '
                   'the town’s system in the way the phrase usually means. The '
                   'district files the submission that produces this rate every 1 '
                   'October, so the grade breakdown exists inside the district before '
                   'the state publishes anything.'
                   % (C.num(dest['elsewhere']), 'FY%d' % dest['fy'],
                      C.num(dest['monty_tech']), str(dest['monty_per_grade']),
                      C.num(outlier['implied_total'] / outlier['implied_years'])),
            basis='`dese_town_enrollment`, read whole: its columns are checked on every '
                  'run and the generator refuses to publish this claim if a grade column '
                  'ever appears in it.',
            not_shown='Any attribution at all. Nothing here says a single departing '
                      'eighth grader went to any of these places. The sizes are '
                      'comparable and that is the whole of what is established.',
            see=[('/monty-tech', 'What Monty Tech costs the town'),
                 ('/what-we-cannot-answer', 'The gap this leaves')],
        ),
    ]
    return emit('attrition', rows)


def build():
    if not os.path.exists(DB):
        fail('%s is not here. Run scripts/build_db.py.' % os.path.relpath(DB, ROOT))
    db = sqlite3.connect('file:%s?mode=ro' % DB, uri=True)
    try:
        rows = attrition_rows(db)
        levels = assert_levels(rows)
        en = enrolment(db)
        first_sy, last_sy = min(r['sy'] for r in rows), max(r['sy'] for r in rows)
        span_rows = CO.spans(db, min(en), max(en))

        raw_dist = [r for r in rows if r['org_type'] == 'District'
                    and r['stu_grp'] == ALL]
        offset = assert_offset(raw_dist, en)
        dist = district_series(rows, en)
        lag = assert_grade8_lag(rows, span_rows)
        deflag = assert_group_definition_lag(rows)
        terminal = assert_terminal_grade(rows, span_rows)

        prof = grade_profile(dist)
        outlier = the_outlier(prof, dist)
        ch = churn(dist, en)
        g9 = grade9_intake(outlier, en)

        # THE ERAS, on the same mechanism /what-courses-actually-ran uses — imported
        # rather than reimplemented, so the two pages cannot disagree about when this
        # town reorganised its buildings.
        runs = CO.school_eras(span_rows, HIGH)
        bands = CO.era_bands(runs, first_sy, last_sy)
        era = era_series(dist, bands, outlier)
        art = school_artefact(rows, span_rows, outlier)

        groups_rows, ref = groups(rows, en, outlier)
        grp_gap = group_gap_by_grade(rows, 'Students with Disabilities', dist)
        dest = destinations(db, outlier)

        said = said_in_meetings()
        terms, minutes = searched()

        return dict(
            generated_by='scripts/build_attrition.py',
            about='Which grades Lunenburg children leave in, year by year — '
                  'DESE’s attrition rate for the district and its schools, '
                  'SY%d to SY%d, with every figure kept as the rate it is.'
                  % (first_sy, last_sy),
            grain='A RATE, NEVER A COUNT. Of the children in one grade in one year, the '
                  'share who were not enrolled in a Lunenburg school the following '
                  'October. It cannot be summed across grades and cannot be averaged '
                  'across them without weighting by the enrolment in each. It counts '
                  'leaving for ANY reason and names no destination. Where a number of '
                  'children appears on this page it is the rate multiplied by '
                  'DESE’s own enrolment, and it says so.',
            first_sy=first_sy, last_sy=last_sy, years=last_sy - first_sy + 1,
            levels=levels,
            offset=offset, grade8_lag=lag, group_definition_lag=deflag,
            terminal_grade=terminal,
            dese=dict(definition=DESE_DEFINITION, blanks=DESE_BLANKS,
                      groups=DESE_GROUPS, url=DESE_URL),
            district=dist,
            grade_profile=prof,
            outlier=outlier,
            churn=ch,
            grade9=g9,
            eras=era,
            school_artefact=art,
            groups=groups_rows,
            group_gap=grp_gap,
            destinations=dest,
            sources=documents(),
            said=said, searched=terms, minutes=minutes,
            gaps=gaps(),
            not_established=not_established(outlier, art, dest, grp_gap, era, terminal,
                                            groups_rows),
            closes=closes(dest, outlier),
            differently=differently(outlier, dest),
            conclusions=build_conclusions(outlier, prof, ch, grp_gap, era, dest,
                                          groups_rows, g9),
        )
    finally:
        db.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    data = build()

    if args.check:
        if not os.path.exists(OUT):
            print('MISSING %s' % os.path.relpath(OUT, ROOT))
            return 1
        with open(OUT, encoding='utf-8') as fh:
            have = json.load(fh)
        if have != data:
            print('STALE %s — run: python3 scripts/build_attrition.py'
                  % os.path.relpath(OUT, ROOT))
            return 1
        print('ok — %s reproduces from the database' % os.path.relpath(OUT, ROOT))
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write('\n')
    o, ch = data['outlier'], data['churn']
    print('%s: SY%d–SY%d, %d rows, %d district + %d school'
          % (os.path.relpath(OUT, ROOT), data['first_sy'], data['last_sy'],
             data['levels']['rows'], data['levels']['district_rows'],
             data['levels']['school_rows']))
    print('  the denominator is the PREVIOUS year: max error %.4f against %.4f '
          'same-year (%.1fx)' % (data['offset']['prior_year_max_error'],
                                 data['offset']['same_year_max_error'],
                                 data['offset']['ratio']))
    print('  grade %s is highest in %d of %d years: mean %.1f%%, next is grade %s at '
          '%.1f%%' % (o['grade'], o['years'], o['years'], o['mean'] * 100,
                      o['runner_up'], o['runner_up_mean'] * 100))
    print('  implied departures %s against an enrolment change of %d (%.1fx)'
          % (format(int(ch['implied_total']), ',d'), ch['enrol_change'], ch['ratio']))
    print('  %s: %.1f%% in the %d years it held grade %s, %.1f%% in the other %d'
          % (data['school_artefact']['school'],
             data['school_artefact']['with_mean'] * 100,
             data['school_artefact']['with_years'], data['school_artefact']['grade'],
             data['school_artefact']['without_mean'] * 100,
             data['school_artefact']['without_years']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
