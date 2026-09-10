#!/usr/bin/env python3
"""What Lunenburg's schools actually TAUGHT -- how many classes ran, in what, year by year.

    python3 scripts/build_course_offerings.py
    python3 scripts/build_course_offerings.py --check

Writes `fy28/public/data/course-offerings.json`, which /what-courses-actually-ran renders.

WHY THIS MEASURE AND NOT THE ONE EVERY EARLIER PAGE HERE USED. `tot_clss_cnt` is how many
classes RAN in a subject, so a subject with none is a subject nobody ran that year. Every
previous approach to "did the cuts change what children can take" reached for teacher FTE
-- a real quantity, and one that cannot tell four Spanish sections from two. This counts
the sections. /school-staffing registers the gap this closes in its own words: *the
district's master schedule by year, which would say whether a subject losing FTE lost a
course.*

`avg_clss_cnt` ANSWERS A DIFFERENT QUESTION and is never blurred with it: not what ran but
how full it was. A district can keep a subject while halving its sections, or keep its
sections while packing them, and only holding the two apart can tell those apart.

FOUR TRAPS, EACH ASSERTED HERE RATHER THAN AVOIDED BY CARE.

1.  THE ROLLUP TRAP, TWICE OVER. `org_name` carries the DISTRICT beside its own schools,
    and `subj` carries `All` beside the subjects it totals. Summing across either is the
    error that once produced $116M of spending for a $26.6M district. `assert_rollups()`
    checks both identities on every org-year -- All == the sum of the 25 non-CH74
    subjects, and the district == the sum of its schools -- and REPORTS the years where
    the second does not hold rather than smoothing them.

2.  THE CH74 ROWS ARE A SECOND, PARALLEL CLASSIFICATION. Fifteen `CH74 - ` rows describe
    Chapter 74 vocational programme areas and are NOT part of the subject total. Every one
    of Lunenburg's 869 of them is zero -- Lunenburg runs no Chapter 74 programme; its
    vocational students go to Monty Tech, which is a different page. Asserted, because the
    day one stops being zero, summing them in would double-count.

3.  THE SCHOOLS ARE NOT THE SAME SCHOOLS. Lunenburg reorganised its buildings twice in
    this period, and `Lunenburg High` means grades 8-12 for four of the fifteen years and
    grades 9-12 for the other eleven. That is not read off the school's NAME -- it is read
    off DESE's own enrolment-by-grade file, which prints a count per grade per school, so
    the grade span of every school-year here is a published measurement. `eras()` refuses
    to write unless the analysis window is one span throughout.

4.  TWO SCHOOL-YEARS REPORT AN AVERAGE CLASS SIZE NO PRIMARY SCHOOL CAN HAVE -- 87.1 at
    Lunenburg Primary in SY2011 and 36.5 in SY2022, against a maximum of 24.1 in every
    other year at every other school. So the elementary series is not trendable and this
    page says so instead of drawing it. The high school's own series is intact in all
    fifteen years and carries the page.

RULE 7 GOVERNS THE WHOLE THING. A section that stopped running is a measurement. That a
child lost an opportunity is a claim needing separate evidence, and the district's own
principal supplied the alternative reading in public: *"Our strategy moving forward is
allowing the students choices to dictate our courses and electives. We will whittle away
at courses once we have recommendations and students choices entered."* Fewer sections can
be fewer children choosing. Nothing in this file separates the two, and it says so.

RULE 8. Not an audit. The town has argued about whether the cuts narrowed what children
can take for three budget cycles with no measurement in the room. This is the measurement.
And the district gets its credit at the same weight: in the same paragraph as the
whittling, the High School Principal is choosing what to ADD.

RULE 11 DOES NOT APPLY AND THAT IS WORTH SAYING. Nothing on this page is a dollar.

TWO CORRECTIONS, KEPT RATHER THAN EDITED OUT, because both are the same defect shape.

  * The comparison against teacher FTE was written as *the subjects that disagree are the
    smallest lines, both moving by a fraction of a post*. That was true of an earlier
    window and false of the one this page settled on, where the larger disagreement is
    MATHEMATICS -- the largest line in the comparison, its FTE down 1.5 while its sections
    rose. Every figure around the sentence was still right. The disagreement is now
    DERIVED and named by the data, and verify_course_offerings.py asserts the structure
    the paragraph rests on rather than only its numbers.
  * The caveat about the elementary schools compared the two impossible averages against
    *the maximum everywhere else* and computed that maximum over the HIGH SCHOOL, which is
    four points lower than the real one. It was found the moment the caveats stopped being
    typed and started being interpolated -- which is rule 2's whole case, arriving on a
    surface rule 2 had never been applied to.
"""
import argparse
import collections
import csv
import json
import os
import re
import sqlite3
import sys

import conclusions as C
from conclusions import conclusion, emit, figure

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
GAPS = os.path.join(ROOT, 'sources', 'data', 'money-gaps.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'course-offerings.json')
CURRICULUM = os.path.join(ROOT, 'sources', 'state-dese', 'dese-curriculum-lunenburg.xlsx')

LEA = '01620000'
MINUTES = 'sources/meetings/text'

HIGH = 'Lunenburg High'
MIDDLE = 'Lunenburg Middle School'
DISTRICT = 'Lunenburg'

# The window every finding on this page rests on: the years the high school held one
# grade span, in one building configuration, with the same five schools reporting. Nine
# years. TJ's rule about this town -- three years is more forward visibility than its
# boards currently use -- cuts the other way here, and the span is stated on every chart.
WINDOW = (2017, 2025)

# The years `Lunenburg High` was grades 9-12. Derived below from DESE's enrolment-by-grade
# file and CHECKED against this, rather than typed: if the state's own grade counts stop
# saying what this says, the build fails instead of publishing a comparison across a
# reorganisation.
NINE_TO_TWELVE = (2011, 2012, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025)

# An average class size above this is not a class. Both offenders are Lunenburg Primary,
# and the point of the constant is that the page refuses to trend a series containing one
# rather than quietly averaging it in.
IMPLAUSIBLE_AVG = 30.0

ROLLUP_SUBJ = 'All'
CH74 = 'CH74 - '

# The workbooks, by manifest key. Read out of the manifest so a citation cannot lose its
# hash silently (rules 2 and 12).
DOCS = [
    dict(key='state-dese/dese-class-size.xlsx',
         what='Every Massachusetts district’s class counts and average class sizes '
              'by school and subject, SY2011–SY2025. The source of every section '
              'count and every class size on this page.',
         publisher='Massachusetts Department of Elementary and Secondary Education',
         stage='reported for the school year, from the district’s own course '
               'records. Not a budget, and not a plan — a count of what ran.',
         table='dese_class_size'),
    dict(key='state-dese/dese-enrollment-by-grade.xlsx',
         what='Enrolment by grade, by school, for every district. The source of the '
              'grade span of each Lunenburg school in each year — which is what '
              'makes a comparison across the two building reorganisations either '
              'legitimate or meaningless.',
         publisher='Massachusetts Department of Elementary and Secondary Education',
         stage='reported as at 1 October of the school year.',
         table='dese_enrollment'),
    dict(key='state-dese/dese-teacher-data.xlsx',
         what='Teacher FTE by subject, by school. The second instrument on this page, '
              'and the one every earlier attempt at this question used on its own.',
         publisher='Massachusetts Department of Elementary and Secondary Education',
         stage='reported for the school year. Per ASSIGNMENT, not per person.',
         table='dese_teacher_subject'),
    dict(key='state-dese/dese-curriculum-lunenburg.xlsx',
         what='Lunenburg’s own curriculum return to DESE — 119 rows, eight '
              'subjects by grade, with the published curriculum product named against '
              'each. Reporting is voluntary and 104 rows name none, so this bounds what '
              'a parent can LOOK UP and says nothing about what is taught.',
         publisher='Massachusetts Department of Elementary and Secondary Education',
         stage='as the district reported it. Undated within the workbook.',
         table='not loaded — read from the workbook'),
]

# What was said in public about courses, electives and the schedule. Every quote is
# re-read out of the extracted minutes on every run: a quote is a claim about a document,
# and an extractor can change what a document renders to (rule 13).
#
# FOUR OF THESE ARE HERE BECAUSE OF THE PERSONA REVIEW AND NOT BECAUSE OF THE DATA.
# `notes/process/PERSONAS.md` step 3: for every category a report says moved, search the
# archive for what people said about that thing in the same year. Searching the record for
# `foreign language`, `world language`, `French` and `Latin` -- rather than for the words
# this page had already chosen -- produced the High School Principal saying in his own
# opening report that the school's largest class was 31 BECAUSE OF a reduction in foreign
# language, a parent describing a child who had practised French for three years, and the
# middle school's grade 8 world language in the override conversation. The data had the
# subject; the archive had the mechanism and the people. `section` splits them on the page.
QUOTES = [
    dict(key='whittle', board='school-committee', date='2024-03-06', kind='minutes',
         section='mechanism',
         doc='6449', who='the High School Principal, to the School Committee',
         quote='Our strategy moving forward is allowing the students choices to dictate '
               'our courses and electives. We will whittle away at courses once we have '
               'recommendations and students choices entered.',
         why='The single most important sentence on this page, and it is the district’s '
             'own. It says the mechanism: a section that does not run may be a section '
             'nobody chose rather than a section anybody cut. Everything measured here is '
             'the OUTCOME of that process, and nothing here separates the two halves of '
             'it.'),
    dict(key='musictech', board='school-committee', date='2024-02-07', kind='minutes',
         section='mechanism',
         doc='6395', who='a student, in public comment',
         quote='I have seen that there are supposed to be cuts to the current High School '
               'band teacher, where the electives he teaches such as Music Tech will be '
               'non-existent.',
         why='And the high school’s Arts sections went UP that year. Both are true, '
             'and the reason they can both be true is the limit this page keeps running '
             'into: DESE files sections by SUBJECT AREA and never by course, so one '
             'named elective ending is invisible inside a subject total that rose. That '
             'is a gap in the register, not a contradiction.'),
    dict(key='newelective', board='school-committee', date='2024-01-24', kind='minutes',
         section='mechanism',
         doc='6375', who='a student, in public comment',
         quote='I was put into a new elective that was just implemented this semester '
               'titled Music in Modern Media and it goes into Music Technology and the '
               'History of Music Film Literacy and all those things we had four people '
               'when that elective was implemented on the first day eight people showed '
               'up, there is more interests and it was not advertised in a great way but '
               'there is more interest.',
         why='A course being ADDED, in the same budget cycle as the cut list — and '
             'at a size this file would record as a section of four to eight. It is the '
             'clearest account anybody has given in public of what the small sections in '
             'the high school actually are.'),
    dict(key='schedule', board='school-committee', date='2024-12-04', kind='minutes',
         section='mechanism',
         doc='6907', who='the School Committee’s own agenda and minutes',
         quote='LHS Master Schedule Development Mr. Santry gives a detailed summary of '
               'the scheduling process at the High School via Slide Presentation',
         why='The document that would close almost every limit on this page exists and '
             'was presented in public. It is not in this archive and is not published on '
             'the district’s site, which is why it is named on the records request '
             'rather than argued about.'),
    dict(key='options', board='school-committee', date='2023-12-20', kind='minutes',
         section='mechanism',
         doc='6145', who='a School Committee member, on the FY25 budget',
         quote='we need to make sure we are continuing to challenge our students and '
               'options specifically for students that are on an AP track and getting the '
               'kids the classes they want/need to take',
         why='The question this page was built to answer, asked at the table a year '
             'before the budget it concerned. Nothing in front of that meeting counted '
             'what ran.'),
    dict(key='apstats', board='school-committee', date='2024-03-06', kind='minutes',
         section='mechanism',
         doc='6449', who='the High School Principal, in the same report',
         quote='We would like to offer AP Statis tics if possible as many academic '
               'programs at college levels include statistics as a requirement.',
         why='The other direction, in the same paragraph as the whittling, and rule 8 '
             'says it goes on the page at the same weight: a school choosing what to ADD '
             'in the middle of a budget it does not yet know the size of. Mathematics is '
             'among the subjects that gained sections here. The transcription reads '
             '“Statis tics”; it is quoted as the archive holds it rather than '
             'tidied, because a quote is a claim about a document.'),
    dict(key='largest31', board='school-committee', date='2025-09-03', kind='minutes',
         section='language',
         doc='7385', who='the High School Principal, in his opening report',
         quote='Our largest class is 31 which is because of a reduction in foreign '
               'language.',
         why='The other half of the measurement, said out loud by the person who builds '
             'the schedule: fewer sections and fuller ones are one decision seen twice. '
             'It describes the SEPTEMBER AFTER the last school year this file covers, so '
             'it is corroboration from beyond the measurement rather than part of it — '
             'and it is the only place in the readable archive where anybody in the '
             'district connects the two quantities this page keeps apart.'),
    dict(key='french', board='school-committee', date='2024-01-24', kind='minutes',
         section='language',
         doc='6375', who='a parent, in public comment',
         quote='In addition to the special education with my daughter being in 7th grade '
               'she is concerned about the cuts to foreign language and the middle school '
               'sports.',
         why='The middle school half, from the year it moved. This page found the '
             'subject in the data; the archive is where the child is. What the parent '
             'describes and what the file records are the same event seen from two '
             'sides, and neither establishes the other.'),
    dict(key='restoration', board='school-committee', date='2026-04-01', kind='minutes',
         section='language',
         doc='7748', who='a School Committee member, reporting from the middle '
                         'school’s advisory council',
         quote='the school advisory committee for the middle school met and talked about '
               'the grade 8 world language and the override, middle school sports being '
               'in the restoration budget',
         why='Still live, two years on, and in the same sentence as the override. Read '
             'it carefully: the minute puts MIDDLE SCHOOL SPORTS in the restoration '
             'budget and says only that grade 8 world language was discussed. This page '
             'does not read it as saying more than that.'),
    dict(key='request', board='school-committee', date='2026-03-10', kind='minutes',
         section='language',
         doc='7706', who='a resident, in public comment',
         quote="the school's requests for an interventionist, a kindergarten "
               'paraprofessional, a world language teacher, a teacher and '
               'paraprofessional for the bridge program, an English teacher, a part-time '
               'music teacher, an assistant principal, a literacy coach, and an '
               'assistant business manager entirely reasonable and defensible',
         why='A world language teacher is on the district’s own ask, first in the '
             'list after the interventionist and the kindergarten paraprofessional. That '
             'is a document stating intent, which is evidence of intent and not of '
             'outcome — but it is the point at which a measurement in this file '
             'becomes something a body in this town is actually voting on.'),
]

# Rule 15a. The denominator prints beside every one of these: a grep that finds nothing
# prints nothing, and nothing reads as "nobody said it".
# The terms the persona review searched, INCLUDING the ones that found nothing. A term
# with no matches is a statement about the readable archive and never about what anybody
# said, and the denominator prints beside all of them.
#
# `French` and `Latin` are here because searching for the words this page had already
# chosen -- `foreign language`, `world language` -- missed the parent and the student who
# named the actual languages. That is the omission step of PERSONAS.md working: a report
# searches for its own vocabulary and residents use theirs.
SEARCHED = ['electives', 'course offerings', 'master schedule', 'program of studies',
            'world language', 'foreign language', 'French', 'Latin',
            'computer science', 'class size', 'course selection']

# The rows in money-gaps.csv this page cites. The registry outranks the page (rule 7c):
# if one of these is missing, nothing is written.
CITES_GAPS = [
    'Which courses a Lunenburg High student could actually choose from, in any year',
    'What is taught in the fifth of Lunenburg High sections DESE files as Miscellaneous',
    'How many classes ran in each subject at the two elementary schools',
]

# WHAT THIS PAGE CANNOT SAY -- and it is a FUNCTION rather than a list of sentences.
#
# Rule 2 covers every generated surface and not only the projection: three figures once
# shipped here stating amounts the model no longer produced, one off by $313,000. These
# paragraphs carry a grade cohort, a seat count, two impossible class sizes and a
# curriculum count, and every one of them is interpolated from what the run just computed.
# A caveat that quotes a stale figure is worse than one that quotes none: it is the
# defect it exists to warn about.
def not_established(rows, cur, hs, eras, impl, years):
    other = [e for e in eras if e['span'] != '9–12']
    if len(other) != 1:
        fail('the high school no longer has exactly one era at a different grade span, '
             'and this page’s caveats are written against one.')
    o = other[0]
    # The break itself, measured: the year grade 8 arrived, the children it brought, and
    # the seats the file recorded arriving with them.
    before = [p for p in hs if p['sy'] == o['first_sy'] - 1]
    after = [p for p in hs if p['sy'] == o['first_sy']]
    if not before or not after:
        fail('the year on either side of the grade-span break is missing from the high '
             'school series, and the caveat about it cannot be written.')
    seats = after[0]['seats'] - before[0]['seats']
    kids = after[0]['students'] - before[0]['students']
    return [
        'Whether a subject running fewer sections means a child could not take it. A '
        'section is what RAN, and what ran is the product of two things at once — '
        'what the schedule offered and what students chose. The district’s own '
        'principal told the School Committee that courses are whittled away after '
        'student choices are entered. Nothing here separates the two, and the honest '
        'reading of a fall is that one of them moved.',

        'What any of these sections is CALLED. DESE files by subject area and never by '
        'course, so a named elective ending inside a subject whose total rose is '
        'invisible to this file — which is exactly what a student described to the '
        'School Committee in February 2024.',

        # THE INTERPOLATION CAUGHT A TYPED FIGURE THE MOMENT IT WAS TURNED ON: the
        # comparison here was written as the high school's own maximum, which is a
        # different quantity from the highest average class size anywhere else in the
        # district and is four points lower. Rule 2's whole case in one line.
        'Anything about the two elementary schools. %s school-years report an average '
        'class size no primary school can have — %s and %s, both at %s — against '
        'a maximum of %s in every other school-year in the file, and adjacent years '
        'swing by a factor of two with no matching change in enrolment. The subject '
        'coding of a self-contained classroom is not stable enough to trend, so this '
        'page does not trend it.'
        % (C.num(len(impl)), impl[0]['avg'], impl[-1]['avg'], impl[0]['org'],
           max(r['avg_clss_cnt'] for r in rows
               if r['subj'] == ROLLUP_SUBJ and r['org_type'] == 'School'
               and r['avg_clss_cnt'] <= IMPLAUSIBLE_AVG)),

        'Why the high school’s record breaks at SY%d. Grade 8 moved into the '
        'building that year: the school’s student count rose by %s and its '
        'recorded seats by %s — more than twenty course seats for every additional '
        'child. The arithmetic does not work, nothing in this archive explains it, and '
        'no finding here crosses that year.'
        % (o['first_sy'], C.num(kids), C.num(seats)),

        'Whether any of this was caused by the budget. The town cut, enrolment fell and '
        'the buildings were reorganised twice inside the same %s years. Those are '
        'three causes and this file records one outcome.' % C.num(years),

        'What Lunenburg teaches. The district’s curriculum return to DESE names a '
        'published product against %s of its %s rows, and DESE’s curriculum '
        'reporting is VOLUNTARY — so a blank is a row nobody filled in, never a '
        'subject nobody teaches. Lunenburg plainly teaches science. The count on this '
        'page is about what a parent can look up.'
        % (C.num(cur['with_product']), C.num(cur['rows'])),

        'Anything about quality, results or what a section is worth. This page counts '
        'classes.',

        'Anything about the town side. Massachusetts collects a class count from school '
        'districts and from nothing else, so there is no equivalent series for the fire '
        'department, the library or public works, and no comparison between the two '
        'halves of the town budget can be drawn from this page in either direction.',

        'Anything about a person. Every figure here is a count of classes at a school. '
        'Where a quote on this page names somebody it is a role in a public meeting '
        'record, quoted for the mechanism it describes.',
    ]


def closes(said):
    """The two documents that would close almost everything above, with the dates they
    were in front of the School Committee -- read off the quotes rather than typed, so a
    date cannot drift from the minute it came out of."""
    by = {q['key']: q for q in said}
    for k in ('whittle', 'schedule'):
        if k not in by:
            fail('the quote %r is gone and the `closes` sentence is built from its '
                 'date.' % k)
    return ('The district’s own Program of Studies for each year — the High '
            'School Principal handed the School Committee an edition of it on %s — '
            'and the LHS master schedule, presented to the School Committee on %s. Both '
            'exist, both were discussed in public, and neither is published. Between '
            'them they would turn every section count on this page into a list of '
            'courses, which is the thing a parent actually wants.'
            % (_longdate(by['whittle']['date']), _longdate(by['schedule']['date'])))


def differently(said):
    """The Finance Committee's test in notes/process/PERSONAS.md, and the one persona test
    this page failed on its first pass. Deliberately the cheapest possible ask: not a new
    document, not a records request, and nothing anybody has to compile."""
    by = {q['key']: q for q in said}
    return ('Publish the Program of Studies each year, with the previous year’s '
            'beside it. The High School Principal handed the School Committee an edition '
            'of it on %s and presented the LHS master schedule on %s, so both documents '
            'exist, both have been in front of the board, and neither is on the '
            'district’s website. Two PDFs a year would turn every section count on '
            'this page into a list of courses — which is what a parent asking '
            'whether their child can still take a language actually wants, and what no '
            'state file will ever hold.'
            % (_longdate(by['whittle']['date']), _longdate(by['schedule']['date'])))


MONTHS = ('January February March April May June July August September October November '
          'December').split()


def _longdate(iso):
    y, m, d = iso.split('-')
    return '%d %s %s' % (int(d), MONTHS[int(m) - 1], y)


def fail(msg):
    raise SystemExit('%s\nNothing written.' % msg)


def q(db, sql, *args):
    cur = db.execute(sql, args)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


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
    return out


# ---- the class-size rows, and the two rollups that must hold ----------------------

def class_rows(db):
    rows = q(db, 'SELECT sy, org_code, org_name, org_type, subj, tot_clss_cnt, '
                 'avg_clss_cnt, tot_stu_cnt FROM dese_class_size ORDER BY sy, org_code, subj')
    if not rows:
        fail('dese_class_size is empty. An empty table passes every check downstream and '
             'renders a blank page. Run scripts/build_db.py.')
    for r in rows:
        r['sy'] = int(r['sy'])
        for k in ('tot_clss_cnt', 'avg_clss_cnt', 'tot_stu_cnt'):
            r[k] = float(r[k] or 0)
    return rows


def assert_rollups(rows):
    """Both rollups, on every cell, and the CH74 parallel classification.

    A rollup summed with its own detail is the defect shape this archive has the most
    expensive history with. Neither identity is assumed here; both are recomputed."""
    ch74 = [r for r in rows if r['subj'].startswith(CH74)]
    if not ch74:
        fail('no CH74 rows at all. They are a SECOND classification sitting in the same '
             'column as the subjects, and a load that dropped them has changed the shape '
             'of the file underneath this page.')
    hot = [r for r in ch74 if r['tot_clss_cnt'] or r['tot_stu_cnt']]
    if hot:
        fail('%d Chapter 74 rows are no longer zero (first: SY%d %s %s). They are a '
             'PARALLEL classification, not part of the subject total, and every sum on '
             'this page excludes them on the strength of their being empty. If Lunenburg '
             'has begun running a Chapter 74 programme that is a finding, and this page '
             'has to be rewritten rather than quietly kept.'
             % (len(hot), hot[0]['sy'], hot[0]['org_name'], hot[0]['subj']))

    cells = collections.defaultdict(dict)
    for r in rows:
        cells[(r['sy'], r['org_code'])][r['subj']] = r
    bad = []
    for key, by_subj in sorted(cells.items()):
        total = by_subj.get(ROLLUP_SUBJ)
        if total is None:
            bad.append('SY%d %s has no %r row' % (key[0], key[1], ROLLUP_SUBJ))
            continue
        parts = sum(v['tot_clss_cnt'] for s, v in by_subj.items()
                    if s != ROLLUP_SUBJ and not s.startswith(CH74))
        if abs(parts - total['tot_clss_cnt']) > 0.001:
            bad.append('SY%d %s: All=%g, subjects sum to %g'
                       % (key[0], total['org_name'], total['tot_clss_cnt'], parts))
    if bad:
        fail('the subject rollup does not hold on %d cell(s):\n  %s\n'
             'Nothing on this page may be summed until it does.'
             % (len(bad), '\n  '.join(bad[:8])))

    # The district against its own schools. This one is allowed to differ -- DESE
    # suppresses small cells -- but the years it differs in are PUBLISHED rather than
    # smoothed, because a district total larger than its schools is a real fact about
    # what can be attributed.
    residual = []
    for sy in sorted({r['sy'] for r in rows}):
        d = [r for r in rows if r['sy'] == sy and r['org_type'] == 'District'
             and r['subj'] == ROLLUP_SUBJ]
        s = [r for r in rows if r['sy'] == sy and r['org_type'] == 'School'
             and r['subj'] == ROLLUP_SUBJ]
        if len(d) != 1 or not s:
            fail('SY%d does not carry exactly one district row and at least one school '
                 'row. Splitting the district from its schools is what stops this page '
                 'double-counting everything on it.' % sy)
        gap = d[0]['tot_clss_cnt'] - sum(x['tot_clss_cnt'] for x in s)
        if gap:
            residual.append(dict(sy=sy, sections=round(gap),
                                 students=round(d[0]['tot_stu_cnt']
                                                - sum(x['tot_stu_cnt'] for x in s)),
                                 schools=len(s)))
        if gap < 0:
            fail('SY%d: the schools report MORE sections than the district (%g). That '
                 'cannot happen if the district row is a rollup, so the file no longer '
                 'means what this page reads it to mean.' % (sy, gap))
    return dict(ch74_rows=len(ch74), cells=len(cells), district_residual=residual)


def implausible_subject(rows):
    """The single clearest cell, for the page to print rather than describe.

    The school-level averages say the elementary series cannot be trended. ONE SUBJECT ROW
    says why in a way nobody has to take on trust: Lunenburg Primary's Arts, recorded as
    two classes averaging the entire school. That is a coding artefact of a self-contained
    classroom, not a class of 341 children, and printing it is more honest than any
    sentence about instability."""
    cells = [r for r in rows
             if r['subj'] != ROLLUP_SUBJ and not r['subj'].startswith(CH74)
             and r['tot_clss_cnt'] and r['avg_clss_cnt'] > IMPLAUSIBLE_AVG]
    if not cells:
        fail('no subject cell now reports an impossible average class size, so the '
             'worked example on this page no longer exists. Rewrite the elementary '
             'section rather than shipping a caveat that is no longer true.')
    w = max(cells, key=lambda r: r['avg_clss_cnt'])
    return dict(sy=w['sy'], org=w['org_name'], subj=w['subj'],
                sections=round(w['tot_clss_cnt']), avg=w['avg_clss_cnt'],
                students=round(w['tot_stu_cnt']),
                school_students=round(_students(rows, w['org_name'], w['sy'])))


def implausible(rows):
    """The school-years whose average class size no school can have. Named, not dropped
    quietly: the reason the elementary series is not trended is a finding."""
    out = [dict(sy=r['sy'], org=r['org_name'], avg=r['avg_clss_cnt'],
                sections=round(r['tot_clss_cnt']), students=round(r['tot_stu_cnt']))
           for r in rows
           if r['subj'] == ROLLUP_SUBJ and r['avg_clss_cnt'] > IMPLAUSIBLE_AVG]
    if not out:
        fail('no school-year now reports an implausible average class size. That is good '
             'news about the source and it means this page’s reason for refusing to '
             'trend the elementary series no longer holds -- rewrite it rather than '
             'shipping a caveat that is no longer true.')
    return sorted(out, key=lambda r: -r['avg'])


# ---- the grade spans, from the state's own counts ---------------------------------

GRADES = ([('pk_cnt', 'PK'), ('k_cnt', 'K')]
          + [('grade_%d_cnt' % i, str(i)) for i in range(1, 13)])


def spans(db, first_sy, last_sy):
    """The grade span of every Lunenburg school in every year, READ OFF DESE'S OWN COUNTS.

    Not off the school's name, and not off anything anybody wrote down. `Lunenburg High`
    is grades 8-12 for four of these fifteen years, and the only reason this page knows
    that is that the state prints a count per grade per school."""
    cols = ','.join(c for c, _ in GRADES)
    rows = q(db, 'SELECT fy, org_code, org_name, total_cnt, %s FROM dese_enrollment '
                 "WHERE lea=? AND org_level='school' AND fy BETWEEN ? AND ? "
                 'ORDER BY fy, org_name' % cols, LEA, first_sy, last_sy)
    if not rows:
        fail('dese_enrollment holds no Lunenburg school rows. Without the grade spans '
             'this page cannot say whether any two years are comparable, and a comparison '
             'across a reorganisation is worse than no comparison.')
    out = []
    for r in rows:
        held = [label for col, label in GRADES if (r[col] or 0) > 0]
        out.append(dict(sy=int(r['fy']), org_code=r['org_code'], org_name=r['org_name'],
                        students=int(r['total_cnt'] or 0),
                        grades=held,
                        span=('%s–%s' % (held[0], held[-1])) if held else 'not stated'))
    return out


def eras(span_rows):
    """The high school's own configuration history, and the assertion the window rests on."""
    hs = {r['sy']: r for r in span_rows if r['org_name'] == HIGH}
    if not hs:
        fail('DESE’s enrolment file carries no rows for %s.' % HIGH)
    nine = tuple(sorted(sy for sy, r in hs.items() if r['span'] == '9–12'))
    if nine != NINE_TO_TWELVE:
        fail('the years %s held only grades 9-12 are now %s, and this page is written '
             'against %s. A section count compared across a change of grade span is not a '
             'comparison. Re-derive the window before publishing anything.'
             % (HIGH, nine, NINE_TO_TWELVE))
    first, last = WINDOW
    off = [sy for sy in range(first, last + 1) if hs.get(sy, {}).get('span') != '9–12']
    if off:
        fail('%s was not grades 9-12 in %s, which is inside the analysis window %s.'
             % (HIGH, off, WINDOW))
    runs, cur = [], None
    for sy in sorted(hs):
        s = hs[sy]['span']
        if cur and cur['span'] == s and cur['last_sy'] == sy - 1:
            cur['last_sy'] = sy
        else:
            cur = dict(span=s, first_sy=sy, last_sy=sy)
            runs.append(cur)
    return runs, nine


def configurations(span_rows):
    """Every school, every year, as the state counted it -- the raw table under the eras."""
    by_year = collections.defaultdict(list)
    for r in span_rows:
        by_year[r['sy']].append(r)
    out = []
    for sy in sorted(by_year):
        schools = sorted(by_year[sy], key=lambda r: r['org_code'])
        out.append(dict(sy=sy, schools=[dict(name=s['org_name'], span=s['span'],
                                             students=s['students']) for s in schools]))
    return out


# ---- the series ------------------------------------------------------------------

def series(rows, org):
    got = [r for r in rows if r['org_name'] == org and r['subj'] == ROLLUP_SUBJ]
    if not got:
        fail('no rows at all for %s. A join that matches nothing looks exactly like a '
             'school that ran no classes.' % org)
    return [dict(sy=r['sy'], sections=round(r['tot_clss_cnt']),
                 avg=round(r['avg_clss_cnt'], 1),
                 students=round(r['tot_stu_cnt']),
                 seats=round(r['tot_clss_cnt'] * r['avg_clss_cnt']),
                 seats_per_student=(round(r['tot_clss_cnt'] * r['avg_clss_cnt']
                                          / r['tot_stu_cnt'], 2)
                                    if r['tot_stu_cnt'] else None))
            for r in sorted(got, key=lambda r: r['sy'])]


def assert_seats(rows, org):
    """The identity the page's `seats` figure rests on: the All row's sections times its
    average equals the sum of the subjects' own. Rounding in the published averages makes
    this approximate, so the tolerance is stated rather than assumed."""
    worst = 0.0
    for sy in sorted({r['sy'] for r in rows}):
        cell = [r for r in rows if r['org_name'] == org and r['sy'] == sy]
        tot = [r for r in cell if r['subj'] == ROLLUP_SUBJ]
        if not tot:
            continue
        a = tot[0]['tot_clss_cnt'] * tot[0]['avg_clss_cnt']
        b = sum(r['tot_clss_cnt'] * r['avg_clss_cnt'] for r in cell
                if r['subj'] != ROLLUP_SUBJ and not r['subj'].startswith(CH74))
        if a:
            worst = max(worst, abs(a - b) / a)
    if worst > 0.01:
        fail('at %s the total row’s seats and the sum of its subjects’ differ '
             'by up to %.2f%%. The two are meant to be the same quantity, so the file no '
             'longer holds together and no seats figure may be published from it.'
             % (org, worst * 100))
    return round(worst, 6)


def by_subject(rows, org, first, last):
    """Every subject at one school across the window, with what moved."""
    cell = [r for r in rows if r['org_name'] == org
            and not r['subj'].startswith(CH74) and r['subj'] != ROLLUP_SUBJ]
    subs = sorted({r['subj'] for r in cell})
    years = sorted({r['sy'] for r in cell if first <= r['sy'] <= last})
    if not years:
        fail('no years in the window %s-%s at %s.' % (first, last, org))
    out = []
    for s in subs:
        pts = []
        for sy in years:
            m = [r for r in cell if r['subj'] == s and r['sy'] == sy]
            if not m:
                fail('%s has no %r row in SY%d. A missing row and a zero are different '
                     'facts and this file publishes zeros, so a hole means the load lost '
                     'something.' % (org, s, sy))
            pts.append(dict(sy=sy, sections=round(m[0]['tot_clss_cnt']),
                            avg=round(m[0]['avg_clss_cnt'], 1),
                            students=round(m[0]['tot_stu_cnt'])))
        a, b = pts[0], pts[-1]
        if a['sections'] == 0 and b['sections'] == 0 and not any(p['sections'] for p in pts):
            continue
        out.append(dict(subj=s, points=pts,
                        first_sy=a['sy'], last_sy=b['sy'],
                        first=a['sections'], last=b['sections'],
                        change=b['sections'] - a['sections'],
                        first_avg=a['avg'], last_avg=b['avg'],
                        first_students=a['students'], last_students=b['students'],
                        share_of_students=(round(b['students'] / bstu, 4)
                                           if (bstu := _students(rows, org, b['sy'])) else None)))
    out.sort(key=lambda r: (-abs(r['change']), r['subj']))
    return out


def _students(rows, org, sy):
    m = [r for r in rows if r['org_name'] == org and r['sy'] == sy
         and r['subj'] == ROLLUP_SUBJ]
    return m[0]['tot_stu_cnt'] if m else 0


# ---- the second instrument: teacher FTE -------------------------------------------

def retired(rows, first_reliable):
    """Subjects that ran district-wide and have run nothing since -- with the LAST YEAR.

    The question the town asks is whether anything stopped altogether, and the CTE areas
    are where it is most likely. This finds them from the whole file rather than from the
    analysis window, because a subject that ended in SY2012 is invisible to a window that
    starts in SY2017 -- and then says, per subject, whether the last year it ran is one of
    the years this file can be trusted. Two of the three ended in SY2011, which is the
    year Lunenburg Primary reports an average class size of 87.1, so "it ended" and "the
    year was mis-reported" fit those equally well and the page says so.
    """
    out = []
    for subj in sorted({r['subj'] for r in rows
                        if not r['subj'].startswith(CH74) and r['subj'] != ROLLUP_SUBJ}):
        pts = sorted((r for r in rows if r['org_type'] == 'District'
                      and r['subj'] == subj), key=lambda r: r['sy'])
        ran = [p for p in pts if p['tot_clss_cnt']]
        if not ran or ran[-1]['sy'] == pts[-1]['sy']:
            continue
        out.append(dict(subj=subj, last_sy=ran[-1]['sy'],
                        last_sections=round(ran[-1]['tot_clss_cnt']),
                        last_students=round(ran[-1]['tot_stu_cnt']),
                        years_since=pts[-1]['sy'] - ran[-1]['sy'],
                        ran_years=[p['sy'] for p in ran],
                        in_reliable_years=ran[-1]['sy'] >= first_reliable))
    out.sort(key=lambda r: (-r['years_since'], r['subj']))
    return out


def fte_join(db, rows, org, first, last, fte_extra):
    """Sections against teacher FTE, subject by subject, on the years BOTH instruments
    cover -- which is not the same as the years either covers.

    THE WINDOW IS THE FINDING'S FOUNDATION AND IT IS NARROWER THAN EITHER SOURCE.
    `dese_teacher_subject` runs one year further than the class-size file. So the four
    subject moves /school-staffing reports for FY2015-FY2026 are NOT what this compares:
    three of them happen partly in a year sections cannot see, and that year's FTE is
    carried here separately rather than differenced against anything (rule 1's cousin --
    two instruments, two spans, and no line drawn through both)."""
    got = q(db, 'SELECT fy, subject, teacher_fte FROM dese_teacher_subject '
                "WHERE org_name=? AND subject_level='subject'", org)
    if not got:
        fail('dese_teacher_subject returned nothing for %s. A join that matches nothing '
             'looks exactly like a district that employs nobody.' % org)
    fte = {(int(r['fy']), r['subject']): r['teacher_fte'] for r in got}
    subs = sorted({s for (_y, s) in fte if (first, s) in fte and (last, s) in fte})
    if not subs:
        fail('not one subject carries teacher FTE in both SY%d and SY%d. The two '
             'instruments no longer overlap.' % (first, last))
    out, agree = [], 0
    for s in subs:
        fa, fb = fte[(first, s)], fte[(last, s)]
        sa = _sections(rows, org, first, s)
        sb = _sections(rows, org, last, s)
        if sa is None or sb is None:
            fail('%r carries teacher FTE at %s but no class-size row. DESE uses one '
                 'subject vocabulary for both files and a name that matches in one and '
                 'not the other means the vocabulary moved.' % (s, org))
        dfte, dsec = round(fb - fa, 1), sb - sa
        same = _sign(dfte) == _sign(dsec)
        agree += 1 if same else 0
        out.append(dict(subj=s, fte_first=fa, fte_last=fb, fte_change=dfte,
                        sections_first=sa, sections_last=sb, sections_change=dsec,
                        agrees=same,
                        fte_beyond=fte_extra.get(s),
                        fte_beyond_change=(None if fte_extra.get(s) is None
                                           else round(fte_extra[s] - fb, 1))))
    out.sort(key=lambda r: (r['agrees'], -abs(r['sections_change']), r['subj']))
    off = [r for r in out if not r['agrees']]
    if not off:
        fail('every subject now agrees, and this page is written around the ones that do '
             'not. Rewrite the section rather than shipping prose about an exception '
             'that no longer exists.')
    # THE BIGGEST DISAGREEMENT, BY THE SIZE OF THE LINE. Written out here rather than
    # described in prose, because the first draft of this page said the disagreeing
    # subjects were "the smallest lines in the comparison, both moving by a fraction of a
    # full-time post" -- which was true of an earlier window and false of this one, where
    # the largest disagreement is the LARGEST line in the comparison. That is rule 2's
    # exact failure mode: a sentence that outlived the number it rested on.
    biggest = max(off, key=lambda r: r['fte_first'])
    return dict(first_sy=first, last_sy=last, subjects=out,
                agree=agree, compared=len(out), disagree=len(off),
                disagreeing=[r['subj'] for r in off],
                biggest_disagreement=biggest,
                biggest_line=max(out, key=lambda r: r['fte_first'])['subj'])


def _sections(rows, org, sy, subj):
    m = [r for r in rows if r['org_name'] == org and r['sy'] == sy and r['subj'] == subj]
    return round(m[0]['tot_clss_cnt']) if m else None


def _sign(x):
    return 0 if abs(x) < 1e-9 else (1 if x > 0 else -1)


def beyond(db, org, sy):
    """The FTE year the section file cannot see. Carried, labelled, never differenced
    against a section count."""
    got = q(db, 'SELECT subject, teacher_fte FROM dese_teacher_subject '
                "WHERE org_name=? AND subject_level='subject' AND fy=?", org, sy)
    if not got:
        return {}
    return {r['subject']: r['teacher_fte'] for r in got}


# ---- the curriculum return --------------------------------------------------------

def curriculum():
    """What a parent can LOOK UP, which is a different quantity from what is taught.

    DESE's curriculum reporting is VOLUNTARY. A blank Product is a row nobody filled in,
    and this function is careful to produce a count of REPORTING and never a count of
    provision -- which is the only honest thing that can be made of this workbook, and is
    why it appears on this page as a note beside a finding rather than as a finding."""
    if not os.path.exists(CURRICULUM):
        fail('%s is not here. Run scripts/sync_archive.py --pull.'
             % os.path.relpath(CURRICULUM, ROOT))
    import openpyxl
    wb = openpyxl.load_workbook(CURRICULUM, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    it = ws.iter_rows(values_only=True)
    next(it)
    hdr = [str(c).strip() if c is not None else '' for c in next(it)]
    need = ('Subject', 'Grade', 'Course', 'Product')
    missing = [n for n in need if n not in hdr]
    if missing:
        fail('the curriculum workbook is missing columns %s. Its shape changed.' % missing)
    ix = {h: i for i, h in enumerate(hdr)}
    rows = [r for r in it if r and (r[ix['Subject']] or '').strip()]
    if not rows:
        fail('the curriculum workbook holds no rows.')
    tally = collections.Counter()
    named = collections.Counter()
    products = set()
    for r in rows:
        s = (r[ix['Subject']] or '').strip()
        p = (r[ix['Product']] or '').strip()
        tally[s] += 1
        if p:
            named[s] += 1
            products.add(p)
    total = sum(tally.values())
    with_product = sum(named.values())
    if with_product >= total:
        fail('every curriculum row now names a product. That is a real change and the '
             'note on this page about what a parent can look up is no longer true.')
    return dict(
        rows=total, with_product=with_product, blank=total - with_product,
        subjects=[dict(subject=s, rows=tally[s], with_product=named[s])
                  for s in sorted(tally)],
        products=sorted(products),
        reported_subjects=sorted(s for s in tally if named[s]))


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
        if re.sub(r'\s+', ' ', spec['quote']) not in text:
            fail('the quote attributed to %s %s is no longer in %s — quote the '
                 'source, never your rendering of it (rule 13)'
                 % (spec['board'], spec['date'], rel))
        kind = 'Minutes' if spec['kind'] == 'minutes' else 'Agenda'
        out.append(dict(
            key=spec['key'], board=spec['board'].replace('-', ' ').title(),
            date=spec['date'], quote=spec['quote'], why=spec['why'], who=spec['who'],
            section=spec['section'],
            kind=kind, cite='/docs/' + rel.replace('sources/', ''),
            town='https://www.lunenburgma.gov/AgendaCenter/ViewFile/%s/_%s%s%s-%s'
                 % (kind, spec['date'][5:7], spec['date'][8:10], spec['date'][:4],
                    spec['doc'])))
    return out


def searched():
    idx = os.path.join(ROOT, 'sources/meetings/index.csv')
    if not os.path.exists(idx):
        fail('sources/meetings/index.csv is not here — a search of nothing is not a '
             'search')
    rows = list(csv.DictReader(open(idx, encoding='utf-8')))
    readable = []
    for r in rows:
        stem = os.path.splitext(r['path'])[0] if r['path'].strip() else ''
        txt = os.path.join(ROOT, MINUTES, stem + '.txt') if stem else ''
        if stem and os.path.exists(txt):
            readable.append(txt)
    if not readable:
        fail('no meeting document is readable — refusing to publish a count of what '
             'nobody said')
    bodies = [open(t, encoding='utf-8', errors='replace').read() for t in readable]
    # ON A LEADING WORD BOUNDARY, and this page is where that stopped being optional.
    # A bare substring search for `Latin` matched 140 documents in this archive and almost
    # none of them were about a language -- `relating` contains it, and so does most of
    # what a board says. The count that reached the first draft of this page was 140 and
    # the true one is 4. It is CLAUDE.md's own verifier lesson -- a substring check on
    # `61` passing on the digits inside $25,613,679.23 -- arriving on the search side,
    # where it matters more, because this number is PRINTED beside a claim about what
    # nobody said.
    #
    # LEADING ONLY, NOT BOTH. A trailing boundary is a different and quieter error: it
    # drops `class sizes` from a search for `class size` and takes the count from 10 to
    # 4 without anything looking wrong. Residents write plurals.
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


def split(gap):
    why = gap['why']
    closes = None
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
    return [split(by_what[w]) for w in CITES_GAPS]


# ---- what this page establishes ---------------------------------------------------

def language(rows, hs_subj, ms_subj, hs, middle):
    """The one subject where the data and the meeting record found each other.

    SEPARATED FROM THE OTHER SUBJECTS BECAUSE THE PERSONA REVIEW SEPARATED IT. Nothing in
    the section counts says foreign language matters more than mathematics; what says so
    is that this is the subject residents came to a meeting about, twice, and the subject
    the High School Principal named in his own opening report. The measurement is the same
    measurement it would be under any other heading.

    THE SHARE IS DISTINCT STUDENTS OVER THE SCHOOL'S OWN DISTINCT STUDENTS, both out of
    the same file and the same row family, so it is not a ratio across two instruments.
    It is NOT a share of children who COULD take a language: the file carries no grades
    inside a school, and a language may not be offered in every grade of one."""
    def share(pts, school):
        by = {p['sy']: p for p in school}
        out = []
        for p in pts:
            s0 = by.get(p['sy'])
            out.append(dict(sy=p['sy'], sections=p['sections'], avg=p['avg'],
                            students=p['students'],
                            school_students=s0['students'] if s0 else None,
                            share=(round(p['students'] / s0['students'], 4)
                                   if s0 and s0['students'] else None)))
        return out

    h = [r for r in hs_subj if r['subj'] == 'Foreign Language']
    m = [r for r in ms_subj if r['subj'] == 'Foreign Language']
    if not h or not m:
        fail('Foreign Language is missing from one of the two schools, and this page '
             'rests on both.')
    hp, mp = share(h[0]['points'], hs), share(m[0]['points'], middle)
    if any(p['share'] is None for p in hp + mp):
        fail('a year of the language share has no denominator. A share over nothing is '
             'not a share.')
    low = min(mp, key=lambda p: p['share'])
    # The middle school has been here before and came back, and saying so is rule 6:
    # a series that dips and recovers is not the same finding as one that fell and stayed.
    prior = [p for p in mp if p['sections'] == mp[-1]['sections'] and p['sy'] < mp[-1]['sy']]
    peak = max(mp, key=lambda p: p['share'])
    return dict(
        high=hp, middle=mp,
        high_first=hp[0], high_last=hp[-1],
        middle_first=mp[0], middle_last=mp[-1],
        middle_low=low, middle_peak=peak,
        middle_prior_at_this_level=[p['sy'] for p in prior],
        middle_recovered=bool(prior),
        # THE COMPARISON IS THE CURRENT RUN AGAINST THE YEAR BEFORE IT, and not against
        # the highest year on record. The largest single fall in this series is
        # SY2019-SY2020, and the school RECOVERED from it -- so quoting that step as the
        # change would be drawing a line across a dip the data itself closes, which is
        # rule 6 in its plainest form. What is happening now is a RUN: the same section
        # count in consecutive years, and the honest baseline is the last year above it.
        # Both are found from the series rather than typed, so the comparison moves when
        # the data does.
        middle_run=_run(mp),
        middle_step=_before_run(mp))


def _run(points):
    """The trailing consecutive years at the current section count."""
    last = points[-1]['sections']
    out = []
    for p in reversed(points):
        if p['sections'] != last:
            break
        out.append(p['sy'])
    return sorted(out)


def _before_run(points):
    """The year immediately before that run -- the baseline the conclusion compares to."""
    run = set(_run(points))
    prior = [p for p in points if p['sy'] not in run]
    if not prior:
        fail('the middle school has been at its current level for its whole history, so '
             'there is no year to compare it with and the conclusion on this page cannot '
             'be drawn.')
    a, b = prior[-1], points[-1]
    return dict(sy=b['sy'], from_sy=a['sy'], from_sections=a['sections'],
                to_sections=b['sections'], from_share=a['share'], to_share=b['share'],
                from_students=a['students'], to_students=b['students'],
                years_at_this_level=len(run))


def build_conclusions(hs, hs_subj, fj, cs, first, last, lang):
    """The five things this page establishes, as DATA rather than as sentences in a page.

    RULE 2 IS ENFORCED HERE, NOT ASKED FOR. Every figure these sentences state -- the
    section counts, the shares, and the SCHOOL YEARS themselves -- is registered beside
    the value it was computed from, and `conclusions.check()` fails the build if any digit
    is left standing that nothing computed. `9-12` and `grade 8` are declared exceptions:
    a grade span is a name, not a derived figure."""
    def sub(name):
        m = [r for r in hs_subj if r['subj'] == name]
        if not m:
            fail('%r is not among the high school’s subjects. This page names it in '
                 'a conclusion.' % name)
        return m[0]

    a = [r for r in hs if r['sy'] == first][0]
    b = [r for r in hs if r['sy'] == last][0]
    fl = sub('Foreign Language')
    misc = sub('Miscellaneous')
    ml = lang['middle_last']
    mstep = lang['middle_step']
    bd = fj['biggest_disagreement']

    fl_share_first = fl['first_students'] / a['students']
    fl_share_last = fl['last_students'] / b['students']
    misc_share = misc['last'] / b['sections']

    # The window's two ends, registered as figures like anything else. They are derived
    # -- WINDOW is asserted against DESE's own grade counts before anything is written --
    # and a year typed into a claim is exactly the defect rule 2 exists for.
    def sy(v):
        return figure(v, 'SY%d' % v)

    rows = [
        conclusion(
            id='the-high-school-runs-more-sections-not-fewer',
            claim='Lunenburg High ran %s sections in %s against %s in %s, on flat '
                  'enrolment.' % (C.num(b['sections']), 'SY%d' % last,
                                  C.num(a['sections']), 'SY%d' % first),
            so_what='More classes ran, not fewer — and the average class fell from '
                    '%s students to %s.' % (a['avg'], b['avg']),
            figures={
                'last': figure(b['sections'], C.num(b['sections']), 'course sections'),
                'first': figure(a['sections'], C.num(a['sections'])),
                'avg_first': figure(a['avg'], str(a['avg'])),
                'avg_last': figure(b['avg'], str(b['avg'])),
                'stu_first': figure(a['students'], C.num(a['students'])),
                'stu_last': figure(b['students'], C.num(b['students'])),
                'sy_first': sy(first), 'sy_last': sy(last),
                'years': figure(last - first + 1, C.num(last - first + 1)),
            },
            figure='last',
            kind='measured',
            bearing='sizes',
            allow=('9-12',),
            lede='The argument in this town has been about whether the cuts narrowed what '
                 'children can take, and at the high school the count of classes that ran '
                 'went the other way.',
            detail='%s students in %s and %s in %s — within a handful of each other '
                   '— across the %s years the high school held only grades 9-12 in '
                   'one building configuration. A section is what RAN, so this is not a '
                   'catalogue and not a plan. What it cannot say is whether the same '
                   'COURSES ran: DESE files sections by subject area and never by course.'
                   % (C.num(a['students']), 'SY%d' % first, C.num(b['students']),
                      'SY%d' % last, C.num(last - first + 1)),
            basis='DESE’s class-size collection — `tot_clss_cnt` and '
                  '`avg_clss_cnt` for Lunenburg High — with the grade span of the '
                  'school in every one of those years read off DESE’s own '
                  'enrolment-by-grade counts, so the two ends of the comparison are the '
                  'same school.',
            not_shown='That more sections is more choice. A fifth of them are groups '
                      'averaging under five students and nothing published says what '
                      'those teach. Nor does it show a cause: the town cut, enrolment '
                      'fell and the buildings were reorganised inside the same period.',
            see=[('/school-staffing', 'The staffing behind it'),
                 ('/cut-register', 'What the district said it was cutting')],
        ),
        conclusion(
            id='foreign-language-narrowed-on-every-instrument',
            claim='%s of Lunenburg High students took a foreign language in %s, against '
                  '%s in %s.' % (C.pct(fl_share_last * 100), 'SY%d' % last,
                                 C.pct(fl_share_first * 100), 'SY%d' % first),
            so_what='Sections fell from %s to %s over the same years — the one '
                    'subject narrowing on every measure here.'
                    % (C.num(fl['first']), C.num(fl['last'])),
            figures={
                'share_last': figure(fl_share_last, C.pct(fl_share_last * 100)),
                'share_first': figure(fl_share_first, C.pct(fl_share_first * 100)),
                'sec_first': figure(fl['first'], C.num(fl['first'])),
                'sec_last': figure(fl['last'], C.num(fl['last'])),
                'stu_first': figure(fl['first_students'], C.num(fl['first_students'])),
                'stu_last': figure(fl['last_students'], C.num(fl['last_students'])),
                'sy_first': sy(first), 'sy_last': sy(last),
            },
            figure='share_last',
            kind='measured',
            bearing='lever',
            lede='Three instruments point the same way for one subject and only one, '
                 'which is what makes it worth separating from everything else here.',
            detail='%s students took a language in %s and %s in %s, in %s sections '
                   'rather than %s. District teacher FTE for the subject moved with '
                   'them. A language schedule is set by people in this town, in a '
                   'document the School Committee sees, so this is a decision somebody '
                   'can look at rather than a condition.'
                   % (C.num(fl['first_students']), 'SY%d' % first,
                      C.num(fl['last_students']), 'SY%d' % last,
                      C.num(fl['last']), C.num(fl['first'])),
            basis='Sections, distinct students and average class size for Foreign '
                  'Language at Lunenburg High, beside district teacher FTE for the same '
                  'subject name from DESE’s teacher file.',
            not_shown='Whether a child who wanted a language could not get one. The '
                      'district’s own principal told the School Committee that '
                      'courses are whittled away after student choices are entered, so a '
                      'fall in sections and a fall in students choosing can be the same '
                      'measurement seen twice.',
            see=[('/school-staffing', 'Teacher FTE by subject')],
        ),
        conclusion(
            id='the-middle-school-world-language',
            claim='%s of Lunenburg Middle School took a world language in %s, against %s '
                  'in %s.' % (C.pct(ml['share'] * 100), 'SY%d' % ml['sy'],
                              C.pct(mstep['from_share'] * 100), 'SY%d' % mstep['from_sy']),
            so_what='Sections went from %s to %s — the lowest share in the %s years '
                    'the school has existed.'
                    % (C.num(mstep['from_sections']), C.num(ml['sections']),
                       C.num(len(lang['middle']))),
            figures={
                'share_last': figure(ml['share'], C.pct(ml['share'] * 100)),
                'share_first': figure(mstep['from_share'],
                                      C.pct(mstep['from_share'] * 100)),
                'sy_last': sy(ml['sy']), 'sy_first': sy(mstep['from_sy']),
                'sec_first': figure(mstep['from_sections'],
                                    C.num(mstep['from_sections'])),
                'sec_last': figure(ml['sections'], C.num(ml['sections'])),
                'years': figure(len(lang['middle']), C.num(len(lang['middle']))),
                'stu_first': figure(mstep['from_students'],
                                    C.num(mstep['from_students'])),
                'stu_last': figure(ml['students'], C.num(ml['students'])),
                'dip': sy(lang['middle_prior_at_this_level'][0]),
                'run': figure(mstep['years_at_this_level'],
                              C.num(mstep['years_at_this_level'])),
            },
            figure='share_last',
            kind='measured',
            bearing='lever',
            allow=('8',),
            lede='This is the subject residents actually came to a meeting about: a '
                 'parent told the School Committee that her seventh grader had practised '
                 'French for three years and had just heard she might not be able to '
                 'take it.',
            detail='%s children took a language at the middle school in %s and %s in %s. '
                   'READ THE SERIES BEFORE CONCLUDING, because it has been here before: '
                   'the school fell to the same %s sections in %s and was back above it '
                   'the next year, so one low year is not a subject ending. What is '
                   'different now is that it has stayed for %s, and that grade 8 world '
                   'language was still being discussed alongside the override two years '
                   'after a parent raised it.'
                   % (C.num(mstep['from_students']), 'SY%d' % mstep['from_sy'],
                      C.num(ml['students']), 'SY%d' % ml['sy'],
                      C.num(ml['sections']), 'SY%d' % lang['middle_prior_at_this_level'][0],
                      ('%s years' % C.num(mstep['years_at_this_level']))),
            basis='Sections and distinct students for Foreign Language at Lunenburg '
                  'Middle School over the share of the school’s own distinct '
                  'students — both out of the same DESE file and the same row '
                  'family, so this is not a ratio across two instruments.',
            not_shown='Whether a language was offered and not chosen, or not offered. It '
                      'also does not show what share of children COULD take one: the '
                      'file carries no grades inside a school, and a language need not '
                      'be offered in every grade.',
        ),

        conclusion(
            id='computer-science-at-the-high-school',
            claim='In the %s years Lunenburg High held only grades 9-12 it ran %s '
                  'computer science section.'
                  % (C.num(len(cs['nine_to_twelve_years'])), C.num(cs['hs_sections'])),
            so_what='%s students, in %s. The subject runs at the middle school in every '
                    'one of its %s years.'
                    % (C.num(cs['hs_students']), 'SY%d' % cs['hs_year'],
                       C.num(cs['middle_years'])),
            figures={
                'sections': figure(cs['hs_sections'], C.num(cs['hs_sections']),
                                   'section in %d years'
                                   % len(cs['nine_to_twelve_years'])),
                'years': figure(len(cs['nine_to_twelve_years']),
                                C.num(len(cs['nine_to_twelve_years']))),
                'students': figure(cs['hs_students'], C.num(cs['hs_students'])),
                'year': sy(cs['hs_year']),
                'middle_years': figure(cs['middle_years'], C.num(cs['middle_years'])),
                'ran_first': figure(cs['ran_first'], C.num(cs['ran_first'])),
                'ran_last': figure(cs['ran_last'], C.num(cs['ran_last'])),
            },
            figure='sections',
            kind='measured',
            bearing='lever',
            allow=('9-12', 'grade 8', 'grade-8'),
            lede='The years the high school DID run computer science — %s to %s '
                 'sections a year — are the years grade 8 was housed in the '
                 'building, and the students in those sections numbered close to the '
                 'grade-8 cohort each year.'
                 % (C.num(cs['ran_first']), C.num(cs['ran_last'])),
            detail='This is the clearest thing on the page a body in this town could '
                   'decide to change, and establishing it costs nothing: the subject '
                   'already runs at the middle school every year, so the question is a '
                   'schedule rather than a programme. What the count cannot say is '
                   'whether high school students take computing under another heading '
                   '— DESE’s subject areas are broad, and this district files a '
                   'fifth of its high school sections under Miscellaneous.',
            basis='`tot_clss_cnt` for Computer and Information Sciences at Lunenburg '
                  'High and at Lunenburg Middle School in every year DESE publishes, '
                  'with the high school’s grade span in each of those years taken '
                  'from DESE’s enrolment-by-grade counts.',
            not_shown='That nobody in Lunenburg teaches computing to a ninth-grader. It '
                      'shows what DESE recorded under one subject heading. The '
                      'district’s curriculum return to DESE names no product '
                      'against any of its digital-literacy rows either, and that is a '
                      'fact about voluntary reporting rather than about provision.',
        ),
        conclusion(
            id='a-fifth-of-high-school-sections-have-no-named-subject',
            claim='%s of Lunenburg High’s sections are in a class averaging %s '
                  'students.' % (C.pct(misc_share * 100), misc['last_avg']),
            so_what='DESE calls the category Miscellaneous and nothing published says '
                    'what those %s groups teach.' % C.num(misc['last']),
            figures={
                'share': figure(misc_share, C.pct(misc_share * 100)),
                'avg': figure(misc['last_avg'], str(misc['last_avg'])),
                'sections': figure(misc['last'], C.num(misc['last'])),
                'first': figure(misc['first'], C.num(misc['first'])),
                'sy_first': sy(first),
            },
            figure='share',
            kind='measured',
            bearing='sizes',
            lede='It is also the single largest mover in the high school’s section '
                 'count, up from %s sections in %s.'
                 % (C.num(misc['first']), 'SY%d' % first),
            detail='A student described one of these to the School Committee in public '
                   'comment — a new elective, four students on the register, eight '
                   'on the first day. That is what a section this size looks like from '
                   'the inside, and it is the only account of one anybody has given in '
                   'public. Whether the rest are electives, academic support, directed '
                   'study or something else is not published anywhere.',
            basis='Sections and average class size for the Miscellaneous subject area at '
                  'Lunenburg High against the school’s own total, at both ends of '
                  'the window.',
            not_shown='What any of them is. The category carries no course names, and '
                      'reading small groups as enrichment or as remediation fits the '
                      'same number equally well. Registered in the gaps below.',
        ),
        conclusion(
            id='sections-and-teacher-fte-agree',
            claim='Sections and teacher FTE moved the same way in %s of the %s subjects '
                  'with both published.'
                  % (C.num(fj['agree']), C.num(fj['compared'])),
            so_what='The staffing proxy was not misleading — but only a section '
                    'count can say whether a class stopped running.',
            figures={
                'agree': figure(fj['agree'], C.num(fj['agree']),
                                'of %d subjects' % fj['compared']),
                'compared': figure(fj['compared'], C.num(fj['compared'])),
                'sy_first': sy(fj['first_sy']), 'sy_last': sy(fj['last_sy']),
                'disagree': figure(fj['disagree'], C.num(fj['disagree'])),
                'off_fte': figure(bd['fte_change'], str(abs(bd['fte_change']))),
                'off_sections': figure(bd['sections_change'],
                                       C.num(bd['sections_change'])),
                'off_avg_first': figure(bd['first_avg'], str(bd['first_avg'])),
                'off_avg_last': figure(bd['last_avg'], str(bd['last_avg'])),
            },
            figure='agree',
            kind='measured',
            bearing='sizes',
            lede='Two independent state files, one counting people and one counting '
                 'classes, over the years both cover — %s to %s, district-wide.'
                 % ('SY%d' % fj['first_sy'], 'SY%d' % fj['last_sy']),
            detail='THE %s THAT DIFFER ARE WHY BOTH FILES ARE PUBLISHED HERE, and the '
                   'larger of them is %s Its '
                   'teacher FTE fell by %s while its sections ROSE by %s and its average '
                   'class went from %s students to %s. Both readings are true and they '
                   'answer different questions — fewer teachers, more classes, '
                   'smaller ones — and a page carrying only the FTE would have '
                   'reported a subject contracting. That is the whole case for counting '
                   'sections: the staffing series was pointing the right way in eight '
                   'subjects and could not, on its own, tell four sections of a subject '
                   'from two.'
                   % (C.num(fj['disagree']),
                      (bd['subj'] + ' — the largest line in the comparison.')
                      if bd['is_largest_line'] else (bd['subj'] + '.'),
                      abs(bd['fte_change']),
                      C.num(bd['sections_change']), bd['first_avg'], bd['last_avg']),
            basis='`dese_teacher_subject` teacher FTE at district level against '
                  '`dese_class_size` section counts for the same subject names, at both '
                  'ends of the overlapping window. DESE uses one subject vocabulary for '
                  'both files, and the join refuses to write unless every compared '
                  'subject is present in both.',
            not_shown='The most recent year. The teacher file runs one year further '
                      'than the class-size file, and its largest moves in that year are '
                      'in %s — none of which has a section count to sit beside it. '
                      'They are carried on this page, labelled, and never differenced '
                      'against one.'
                      % ' and '.join(r['subj'] for r in sorted(
                          (x for x in fj['subjects'] if x['fte_beyond_change']),
                          key=lambda x: -abs(x['fte_beyond_change']))[:2]),
            see=[('/school-staffing', 'The FTE series in full')],
        ),    ]
    return emit('courses', rows)


def computer_science(rows, nine):
    hs = [dict(sy=sy, sections=_sections(rows, HIGH, sy,
                                         'Computer and Information Sciences'))
          for sy in sorted(nine)]
    if any(r['sections'] is None for r in hs):
        fail('a year of the high school’s computer science series is missing.')
    ran = [r for r in hs if r['sections']]
    if len(ran) != 1:
        fail('the high school now ran computer science in %d of its grades-9-12 years, '
             'and this page states one. Re-read the series before publishing.' % len(ran))
    year = ran[0]['sy']
    stu = [r for r in rows if r['org_name'] == HIGH and r['sy'] == year
           and r['subj'] == 'Computer and Information Sciences'][0]['tot_stu_cnt']
    mid = [dict(sy=r['sy'], sections=round(r['tot_clss_cnt']))
           for r in sorted((r for r in rows if r['org_name'] == MIDDLE
                            and r['subj'] == 'Computer and Information Sciences'),
                           key=lambda r: r['sy'])]
    if not mid or any(not m['sections'] for m in mid):
        fail('Lunenburg Middle School no longer runs computer science in every one of its '
             'years, and this page says it does.')
    # The years the subject DID run at the high school, which are the grades-8-12 years.
    # Read off the file rather than typed, so the conclusion's range moves with the data.
    ran_all = sorted(round(r['tot_clss_cnt']) for r in rows
                     if r['org_name'] == HIGH
                     and r['subj'] == 'Computer and Information Sciences'
                     and r['sy'] not in set(nine) and r['tot_clss_cnt'])
    if not ran_all:
        fail('the high school ran no computer science in any of the years it held grade '
             '8, and the conclusion on this page rests on it having done so.')
    # EVERY year at the high school, not only the grades-9-12 ones. The table on the page
    # prints the whole series with the grade span beside each row, because the four years
    # the subject DID run are the interesting ones and a hole where they belong reads as
    # a subject that never ran at all.
    all_hs = [dict(sy=r['sy'], sections=round(r['tot_clss_cnt']),
                   students=round(r['tot_stu_cnt']))
              for r in sorted((r for r in rows if r['org_name'] == HIGH
                               and r['subj'] == 'Computer and Information Sciences'),
                              key=lambda r: r['sy'])]
    return dict(nine_to_twelve_years=list(nine), high=hs, high_all=all_hs, middle=mid,
                hs_sections=sum(r['sections'] for r in hs), hs_year=year,
                hs_students=round(stu), middle_years=len(mid),
                ran_first=ran_all[0], ran_last=ran_all[-1],
                ran_years=sorted(r['sy'] for r in rows if r['org_name'] == HIGH
                                 and r['subj'] == 'Computer and Information Sciences'
                                 and r['sy'] not in set(nine) and r['tot_clss_cnt']))


def build():
    if not os.path.exists(DB):
        fail('%s is not here. Run scripts/build_db.py.' % os.path.relpath(DB, ROOT))
    db = sqlite3.connect('file:%s?mode=ro' % DB, uri=True)
    try:
        rows = class_rows(db)
        roll = assert_rollups(rows)
        span_rows = spans(db, min(r['sy'] for r in rows), max(r['sy'] for r in rows))
        era_runs, nine = eras(span_rows)
        first, last = WINDOW

        hs = series(rows, HIGH)
        district = series(rows, DISTRICT)
        middle = series(rows, MIDDLE)
        seats_tol = assert_seats(rows, HIGH)

        hs_subj = by_subject(rows, HIGH, first, last)
        ms_subj = by_subject(rows, MIDDLE, first, last)
        district_subj = by_subject(rows, DISTRICT, first, last)
        fte_extra = beyond(db, DISTRICT, last + 1)
        fj = fte_join(db, rows, DISTRICT, first, last, fte_extra)
        # The disagreement's own class sizes, joined from the district subject series so
        # the sentence about it cannot state a size nothing computed.
        bd = fj['biggest_disagreement']
        ds = [r for r in district_subj if r['subj'] == bd['subj']]
        if not ds:
            fail('%r disagrees between the two instruments and has no district subject '
                 'row, so its class sizes cannot be stated.' % bd['subj'])
        bd.update(first_avg=ds[0]['first_avg'], last_avg=ds[0]['last_avg'],
                  first_students=ds[0]['first_students'],
                  last_students=ds[0]['last_students'],
                  is_largest_line=(bd['subj'] == fj['biggest_line']))
        cs = computer_science(rows, nine)
        cur = curriculum()
        said = said_in_meetings()
        terms, minutes = searched()

        a = [r for r in hs if r['sy'] == first][0]
        b = [r for r in hs if r['sy'] == last][0]
        gainers = [r for r in hs_subj if r['change'] > 0]
        losers = [r for r in hs_subj if r['change'] < 0]
        zeroed = [r for r in hs_subj if r['last'] == 0 and any(p['sections']
                                                              for p in r['points'])]
        return dict(
            generated_by='scripts/build_course_offerings.py',
            about='How many classes ran in each subject in Lunenburg’s schools, year '
                  'by year — the one measurement in this archive that counts what '
                  'was taught rather than who was employed to teach it.',
            grain='COURSE SECTIONS: how many classes ran in a subject area at a school in '
                  'a school year, as DESE records them. Not courses — the file '
                  'carries no course names. Not dollars, not teachers, not children. A '
                  'section is what RAN, which is what a schedule offered and what '
                  'students chose, together.',
            window=dict(first_sy=first, last_sy=last, years=last - first + 1,
                        why='the years Lunenburg High held one grade span, in one '
                            'building configuration, with the same five schools '
                            'reporting'),
            first_sy=min(r['sy'] for r in district),
            last_sy=max(r['sy'] for r in district),
            eras=era_runs,
            configurations=configurations(span_rows),
            rollups=roll,
            implausible=implausible(rows),
            implausible_cell=implausible_subject(rows),
            seats_tolerance=seats_tol,
            high_school=hs, district=district, middle=middle,
            high_school_subjects=hs_subj,
            middle_subjects=ms_subj,
            district_subjects=district_subj,
            language=language(rows, hs_subj, ms_subj, hs, middle),
            headline=dict(
                first=a, last=b,
                sections_change=b['sections'] - a['sections'],
                students_change=b['students'] - a['students'],
                gainers=len(gainers), losers=len(losers),
                zeroed=[r['subj'] for r in zeroed],
                biggest_gain=gainers[0]['subj'] if gainers else None,
                biggest_loss=(sorted(losers, key=lambda r: r['change'])[0]['subj']
                              if losers else None),
            ),
            fte=fj,
            fte_beyond=dict(sy=last + 1, subjects=[
                dict(subj=s, fte=v) for s, v in sorted(fte_extra.items())]),
            computer_science=cs,
            # SY2011 is the first year of the collection and the year Lunenburg Primary
            # reports 23 sections at an average of 87.1 students. A subject whose last
            # year is SY2011 may have ended or may never have been recorded properly, and
            # the payload marks which rather than choosing.
            retired=retired(rows, first_reliable=min(r['sy'] for r in rows) + 1),
            curriculum=cur,
            sources=documents(),
            said=said, searched=terms, minutes=minutes,
            gaps=gaps(),
            not_established=not_established(
                rows, cur, hs, era_runs, implausible(rows),
                max(r['sy'] for r in rows) - min(r['sy'] for r in rows) + 1),
            closes=closes(said), differently=differently(said),
            conclusions=build_conclusions(hs, hs_subj, fj, cs, first, last,
                                          language(rows, hs_subj, ms_subj, hs, middle)),
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
            print('STALE %s — run: python3 scripts/build_course_offerings.py'
                  % os.path.relpath(OUT, ROOT))
            return 1
        print('ok — %s reproduces from the database'
              % os.path.relpath(OUT, ROOT))
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, sort_keys=True)
        fh.write('\n')
    h = data['headline']
    print('%s: SY%d–SY%d, %d org-years, both rollups hold'
          % (os.path.relpath(OUT, ROOT), data['first_sy'], data['last_sy'],
             data['rollups']['cells']))
    print('  Lunenburg High SY%d→SY%d: %d→%d sections (%+d), %d→%d '
          'students, average class %s→%s'
          % (h['first']['sy'], h['last']['sy'], h['first']['sections'],
             h['last']['sections'], h['sections_change'], h['first']['students'],
             h['last']['students'], h['first']['avg'], h['last']['avg']))
    print('  %d subjects gained sections, %d lost; biggest gain %s, biggest loss %s'
          % (h['gainers'], h['losers'], h['biggest_gain'], h['biggest_loss']))
    print('  sections vs teacher FTE: agree on %d of %d subjects'
          % (data['fte']['agree'], data['fte']['compared']))
    print('  curriculum return: %d of %d rows name a product'
          % (data['curriculum']['with_product'], data['curriculum']['rows']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
