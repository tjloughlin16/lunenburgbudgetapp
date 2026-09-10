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
    dict(key='studyhalls', board='school-committee', date='2025-02-26', kind='minutes',
         section='misc',
         doc='7076', who='the district, answering a resident in public comment',
         quote='No we expect that there will be an increased number of kids in study '
               'halls, all classes will be larger.',
         why='The persona review’s omission step found this, and it is the sharpest '
             'thing in the archive on the question this page was asked. A resident asked '
             'about “extra-large study halls” in the FY26 budget and the district '
             'said it expects more children in them. IT DOES NOT SAY THE MISCELLANEOUS '
             'ROWS ARE STUDY HALLS — nothing published says what those groups are, and '
             'the ones measured here average under five students, which is not what a '
             'large study hall looks like. It also describes the school year AFTER the '
             'last one this file covers, so it is a statement of what the district '
             'expected rather than a measurement of what happened.'),
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
            'computer science', 'class size', 'course selection',
            # ADDED BY THE SECOND PERSONA RUN, for the categories this page newly names
            # as movers -- Miscellaneous, History and mathematics at the middle school.
            # `study hall` is the term a resident used at the School Committee for the
            # thing this page measures as Miscellaneous, and searching for our own word
            # for it would never have found her.
            'study hall', 'work credit', 'history', 'social studies', 'Algebra',
            'course request']

# The rows in money-gaps.csv this page cites. The registry outranks the page (rule 7c):
# if one of these is missing, nothing is written.
CITES_GAPS = [
    'Which courses a Lunenburg High student could actually choose from, in any year',
    'Why fewer Lunenburg High students take a history or a language course than before SY2020',
    'How many classes ran in each subject at Lunenburg Middle School and Lunenburg High before SY2017',
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
    # THE NAME MOVES AND THE CODE DOES NOT. `Thomas C Passios Elem` in SY2011 is
    # `Thomas C Passios Elementary` in SY2012 -- one school, two strings, and anything
    # grouped on the string reads it as two schools that each lasted a year. That is the
    # same defect as reading `Turkey Hill Middle` and `Turkey Hill Elementary School` as
    # ONE school, pointed the other way, and both are why every grouping here is on
    # `org_code`. The name shown is the last one the state used.
    latest = {}
    for r in rows:
        latest[r['org_code']] = r['org_name']
    out = []
    for r in rows:
        held = [label for col, label in GRADES if (r[col] or 0) > 0]
        out.append(dict(sy=int(r['fy']), org_code=r['org_code'],
                        org_name=latest[r['org_code']],
                        filed_as=r['org_name'],
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
    return _runs(hs), nine


def _runs(by_year):
    """Contiguous runs of ONE grade span. `by_year` is {sy: row-with-a-span}.

    A run breaks on a change of span AND on a missing year, because a school that stops
    reporting and starts again four years later is not one series either."""
    runs, cur = [], None
    for sy in sorted(by_year):
        s = by_year[sy]['span']
        if cur and cur['span'] == s and cur['last_sy'] == sy - 1:
            cur['last_sy'] = sy
        else:
            cur = dict(span=s, first_sy=sy, last_sy=sy)
            runs.append(cur)
    return runs


def school_eras(span_rows, org):
    """EVERY school's configuration history, on the same mechanism as the high school's.

    THE REORGANISATION WAS NOT A RENAME AND IT WAS NOT ONLY THE HIGH SCHOOL'S. Thomas C
    Passios closed after SY2012; for the four years until the new middle-school/high-school
    building opened, every remaining school shifted up one grade band -- Lunenburg Primary
    to PK-3, Turkey Hill Middle to 4-7, Lunenburg High to 8-12. SY2017 resets the whole
    structure, and DESE issues NEW org codes for the two schools in the new building.

    So `Turkey Hill Middle` (4-7, ending SY2016) and `Turkey Hill Elementary School` (3-5,
    beginning SY2017) share a name stem and are different schools in different buildings
    holding different children, and joining them into one series would draw a building
    programme as a trend. Every span here is read off DESE's own enrolment-by-grade
    counts, never off a name, and nothing in this file is hardcoded to the table above:
    if the state restates a year, the runs move and the assertions below fail."""
    rows = {r['sy']: r for r in span_rows if r['org_name'] == org}
    if not rows:
        fail('DESE’s enrolment file carries no rows for %s, and this page draws a '
             'per-school series for it.' % org)
    return _runs(rows)


def latest_era(runs, org, class_years, fte_years):
    """The window a school's own comparison may run over: its most recent unbroken run at
    one grade span, narrowed to the years BOTH instruments cover.

    Narrowed rather than assumed, because the two files do not span the same years -- the
    teacher file runs one year further than the class-size file -- and a comparison is
    only as long as its shorter instrument."""
    era = runs[-1]
    yrs = sorted(set(range(era['first_sy'], era['last_sy'] + 1))
                 & set(class_years) & set(fte_years))
    if len(yrs) < 3:
        fail('%s has only %d year(s) inside its most recent grade span that both DESE '
             'files cover. Three years is a trend to a board that will not project two, '
             'and two is not.' % (org, len(yrs)))
    if yrs != list(range(yrs[0], yrs[-1] + 1)):
        fail('%s’s comparable years %s have a hole in them. A hole and a zero are '
             'different facts.' % (org, yrs))
    return dict(span=era['span'], first_sy=yrs[0], last_sy=yrs[-1], years=len(yrs),
                era_first_sy=era['first_sy'], era_last_sy=era['last_sy'])


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


# ---- the two instruments, per school ----------------------------------------------
#
# WHAT THIS SECTION IS FOR. The page states in prose that sections and teacher FTE move
# the same way in eight of ten subjects district-wide and that Mathematics does not. That
# sentence is the most decision-relevant thing on the page and it is district-wide, which
# is the level at which two schools moving in opposite directions look like one school
# doing nothing. The quadrant below is the same comparison drawn, and drawn per school.
#
# THE THIRD INSTRUMENT IS A TEST AND NOT A DECORATION. A subject with fewer teachers and
# MORE sections has two readings: the school found the staff elsewhere, or it spread the
# same people thinner. Average class size separates them -- thinner means FULLER classes.
# So every row here carries the change in average class size, and the chart encodes it as
# a filled or hollow dot rather than as a colour, so the test survives any kind of vision.
# Where the three instruments disagree, the row says so and nothing here picks a winner.

# A published FTE is one decimal, so a change smaller than half of that is not a change.
FTE_ZERO = 0.05

# The district's FTE against the sum of its own schools'. Every school in the file is a
# tenth or better, and four or five of them rounding the same way is 0.2 -- so a
# disagreement past this is a rollup that no longer holds, not rounding.
FTE_ROLLUP_TOL = 0.25

# HOW MUCH A SCHOOL'S TOTAL SECTION COUNT MAY MOVE IN ONE YEAR before its series stops
# being trendable. Not a taste: the four schools in the current configuration separate
# cleanly and the constant sits in the gap between them. Lunenburg High's worst single
# year is 9.1% and the middle school's is 20.7%; the two elementary schools' are 80.1%
# and 111.4%, in years their enrolment moved by 1.4% and 1.0%. `assert_stability()`
# refuses to write if that separation stops holding, so the line cannot quietly move.
TRENDABLE_SWING = 0.35

# The chart labels. A dot needs a word a reader knows at 390px, and `Social
# Studies/Social Sciences` is not one. These are NAMES rather than figures -- rule 2 does
# not reach them -- but they are declared here rather than typed into the page so the
# chart and its table twin cannot disagree, and `_short()` fails on a subject it has never
# seen rather than inventing an abbreviation for it.
SHORT = {
    'Agriculture, Food and Natural Resources': 'Agriculture',
    'Architecture and Construction': 'Construction',
    'Arts': 'Arts',
    'Business and Marketing': 'Business',
    'Civics/Government': 'Civics',
    'Communications and Audio/Visual Technology': 'Media',
    'Computer and Information Sciences': 'Computing',
    'Core-All Subjects': 'Core, all subjects',
    'Economics': 'Economics',
    'Engineering and Technology': 'Engineering',
    'English/Language Arts': 'English',
    'Foreign Language': 'Language',
    'Geography': 'Geography',
    'Health Care Sciences': 'Health care',
    'History': 'History',
    'Hospitality and Tourism': 'Hospitality',
    'Human Services': 'Human services',
    'Manufacturing': 'Manufacturing',
    'Mathematics': 'Mathematics',
    'Military Science': 'Military science',
    'Miscellaneous': 'Miscellaneous',
    'Physical, Health, and Safety Education': 'PE and health',
    'Public, Protective, and Government Service': 'Public service',
    'Reading': 'Reading',
    'Religious Education and Theology': 'Religious education',
    'Science': 'Science',
    'Social Studies/Social Sciences': 'Social studies',
    'Transportation, Distribution and Logistics': 'Transport',
}

# What each corner of the quadrant MEANS, in the words the chart prints. Held here rather
# than in the page because the classifier and the label must be the same statement.
QUADRANTS = {
    ('-', '+'): 'fewer teachers, more classes',
    ('-', '-'): 'fewer teachers, fewer classes',
    ('+', '+'): 'more teachers, more classes',
    ('+', '-'): 'more teachers, fewer classes',
}


def _short(subj):
    if subj not in SHORT:
        fail('%r has no short label, and the quadrant chart prints one against every '
             'dot. Add it to SHORT rather than letting the page fall back to a name no '
             'reader can fit on a phone.' % subj)
    return SHORT[subj]


def assert_fte_rollup(db, first, last):
    """The district's teacher FTE against the sum of its own schools', every subject,
    every year.

    THE ROLLUP TRAP AGAIN, ON THE OTHER INSTRUMENT. `dese_teacher_subject` carries the
    district beside its schools exactly as the class-size file does, and this page is
    about to decompose a district figure into four school figures. If those four do not
    add up to the one, the decomposition is arithmetic on unrelated numbers."""
    got = q(db, 'SELECT fy, org_name, org_level, subject, teacher_fte '
                'FROM dese_teacher_subject '
                "WHERE lea=? AND subject_level='subject'", LEA)
    if not got:
        fail('dese_teacher_subject holds no Lunenburg rows at all.')
    dist = collections.defaultdict(float)
    schools = collections.defaultdict(float)
    for r in got:
        key = (int(r['fy']), r['subject'])
        if r['org_name'] == DISTRICT:
            dist[key] += r['teacher_fte'] or 0
        elif r['org_level'] == 'school':
            schools[key] += r['teacher_fte'] or 0
    worst, where = 0.0, None
    for key in set(dist) | set(schools):
        gap = abs(dist.get(key, 0.0) - schools.get(key, 0.0))
        if gap > worst:
            worst, where = gap, key
    if worst > FTE_ROLLUP_TOL:
        fail('district teacher FTE and the sum of its schools’ differ by %.2f at '
             '%s, past the %.2f this page allows for one-decimal rounding. The district '
             'figure cannot be decomposed into school figures that do not add up to it.'
             % (worst, where, FTE_ROLLUP_TOL))
    return dict(worst=round(worst, 3), at=list(where) if where else None,
                tolerance=FTE_ROLLUP_TOL,
                subject_years=len(set(dist) | set(schools)))


def stability(rows, org, first, last):
    """The largest one-year move in a school's TOTAL section count, with the move in its
    own enrolment beside it.

    A school whose section count halves and doubles between adjacent years while the same
    number of children walk through the door is not recording sections the way the schools
    either side of it are. This measures that rather than asserting it, and prints the
    figure whichever side of the line it falls."""
    pts = sorted((r for r in rows if r['org_name'] == org and r['subj'] == ROLLUP_SUBJ
                  and first <= r['sy'] <= last), key=lambda r: r['sy'])
    if len(pts) < 2:
        fail('%s has fewer than two comparable years and a swing needs two.' % org)
    worst = None
    for a, b in zip(pts, pts[1:]):
        if not a['tot_clss_cnt'] or not a['tot_stu_cnt']:
            continue
        swing = abs(b['tot_clss_cnt'] - a['tot_clss_cnt']) / a['tot_clss_cnt']
        if worst is None or swing > worst['swing']:
            worst = dict(swing=round(swing, 4), from_sy=a['sy'], to_sy=b['sy'],
                         from_sections=round(a['tot_clss_cnt']),
                         to_sections=round(b['tot_clss_cnt']),
                         students_swing=round(abs(b['tot_stu_cnt'] - a['tot_stu_cnt'])
                                              / a['tot_stu_cnt'], 4))
    if worst is None:
        fail('%s has no year with any sections in it, so no swing can be measured.' % org)
    worst['trendable'] = worst['swing'] <= TRENDABLE_SWING
    worst['bound'] = TRENDABLE_SWING
    worst['sections'] = [dict(sy=p['sy'], sections=round(p['tot_clss_cnt']),
                              students=round(p['tot_stu_cnt']),
                              avg=round(p['avg_clss_cnt'], 1)) for p in pts]
    return worst


def assert_stability(schools):
    """That the four schools still fall either side of the line the constant sits in.

    A threshold with nothing asserting it is a taste. This one is a gap in the data --
    the trendable schools are at 9% and 21% and the others at 80% and 111% -- and if that
    gap closes, the constant stops being a reading of the data and the page has to be
    rewritten rather than kept."""
    inside = [s for s in schools if s['stability']['trendable']]
    outside = [s for s in schools if not s['stability']['trendable']]
    if not inside or not outside:
        fail('every school now falls on the same side of the %.0f%% one-year swing '
             'bound, and this page is written around two schools whose section counts '
             'can be trended and two whose cannot. Re-read the series before publishing.'
             % (TRENDABLE_SWING * 100))
    hi = max(s['stability']['swing'] for s in inside)
    lo = min(s['stability']['swing'] for s in outside)
    if lo - hi < 0.2:
        fail('the worst trendable school swings %.1f%% and the best untrendable one '
             '%.1f%%. The bound at %.0f%% was set in a gap between two clusters and there '
             'is no longer a gap, so it is now a judgement rather than a reading.'
             % (hi * 100, lo * 100, TRENDABLE_SWING * 100))
    return dict(worst_trendable=hi, best_untrendable=lo, bound=TRENDABLE_SWING)


def instruments(db, rows, org, first, last, steps_readable):
    """Sections, teacher FTE and average class size for one org, at both ends of its own
    window -- and where each subject lands in the quadrant.

    AND THE STEP CHECK IS ONLY PUBLISHED WHERE THE YEARS BETWEEN THE ENDS CAN BE READ.
    The DISTRICT total is the sum of five schools including the two whose section counts
    double and halve between adjacent years, so its year-by-year series says SY2021
    Science ran 116 sections against 78 the year before and 76 the year after. Its two
    ENDS are clean -- both elementary schools report ordinary counts in SY2017 and SY2025
    -- so the endpoint comparison stands and the steps between them do not. `steps_readable`
    carries that distinction into the payload rather than leaving the page to remember it,
    because a column of largest-single-year moves that is really a column of coding
    artefacts is exactly the kind of figure a reader would quote.

    THE STEP CHECK IS RULE 6 AND IT IS NOT OPTIONAL. A change measured between two
    endpoints nine years apart says nothing about whether it happened gradually or in one
    year. The middle school's English sections read as −11 across the window and ten of
    those eleven go in a single step between the first two years; a reader told 'English
    lost eleven sections over nine years' has been given a trend where there is a step.
    So every row carries its largest single-year move, that move's year, and its size
    against the net -- and a row where one year is the whole of the net change says so."""
    got = q(db, 'SELECT fy, subject, teacher_fte FROM dese_teacher_subject '
                "WHERE org_name=? AND subject_level='subject'", org)
    if not got:
        fail('dese_teacher_subject returned nothing for %s. A join that matches nothing '
             'looks exactly like a school that employs nobody.' % org)
    fte = {(int(r['fy']), r['subject']): r['teacher_fte'] for r in got}
    subs = sorted({s for (_y, s) in fte if (first, s) in fte and (last, s) in fte})
    if not subs:
        fail('not one subject at %s carries teacher FTE at both ends of its window.' % org)

    out = []
    for s in subs:
        cell = {r['sy']: r for r in rows if r['org_name'] == org and r['subj'] == s
                and first <= r['sy'] <= last}
        missing = [y for y in range(first, last + 1) if y not in cell]
        if missing:
            fail('%r carries teacher FTE at %s but no class-size row in %s. DESE uses one '
                 'subject vocabulary for both files, and a name present in one and not '
                 'the other means the vocabulary moved.' % (s, org, missing))
        pts = [dict(sy=y, sections=round(cell[y]['tot_clss_cnt']),
                    avg=round(cell[y]['avg_clss_cnt'], 1),
                    students=round(cell[y]['tot_stu_cnt']))
               for y in range(first, last + 1)]
        if not any(p['sections'] for p in pts):
            continue
        dfte = round(fte[(last, s)] - fte[(first, s)], 1)
        dsec = pts[-1]['sections'] - pts[0]['sections']
        davg = round(pts[-1]['avg'] - pts[0]['avg'], 1)
        sx = '+' if dfte > FTE_ZERO else ('-' if dfte < -FTE_ZERO else '0')
        sy_ = '+' if dsec > 0 else ('-' if dsec < 0 else '0')
        quad = QUADRANTS.get((sx, sy_))
        step = max(zip(pts, pts[1:]),
                   key=lambda ab: abs(ab[1]['sections'] - ab[0]['sections']))
        step_size = step[1]['sections'] - step[0]['sections']
        out.append(dict(
            subj=s, short=_short(s),
            fte_first=fte[(first, s)], fte_last=fte[(last, s)], fte_change=dfte,
            sections_first=pts[0]['sections'], sections_last=pts[-1]['sections'],
            sections_change=dsec,
            avg_first=pts[0]['avg'], avg_last=pts[-1]['avg'], avg_change=davg,
            students_first=pts[0]['students'], students_last=pts[-1]['students'],
            fuller=davg > 0,
            agrees=(sx == sy_) or sx == '0' or sy_ == '0',
            same_direction=(sx == sy_ and sx != '0'),
            quadrant=quad,
            on_the_line=(quad is None),
            axis=('neither instrument moved' if sx == '0' and sy_ == '0'
                  else 'teacher FTE did not move' if sx == '0'
                  else 'the section count did not move' if sy_ == '0' else None),
            points=pts,
            step_from_sy=step[0]['sy'], step_to_sy=step[1]['sy'], step=step_size,
            step_share=(round(abs(step_size) / abs(dsec), 2) if dsec else None),
            # A net move of one or two sections is inside the noise of any single year,
            # so flagging it as "one step" says nothing. The flag is for a move big
            # enough to be called a change that turns out to have happened in one year.
            one_step=abs(dsec) >= 3 and abs(step_size) >= abs(dsec),
        ))
    if not out:
        fail('%s has no subject with both instruments and any section in its window.' % org)
    out.sort(key=lambda r: (-abs(r['sections_change']), r['subj']))

    inq = [r for r in out if r['quadrant']]
    tally = collections.Counter(r['quadrant'] for r in inq)
    thinner = [r for r in inq
               if r['quadrant'] == QUADRANTS[('-', '+')] and r['fuller']]
    return dict(
        org=org, first_sy=first, last_sy=last, years=last - first + 1,
        subjects=out, compared=len(out), steps_readable=steps_readable,
        quadrants=[dict(quadrant=name, subjects=[r['short'] for r in inq
                                                 if r['quadrant'] == name],
                        count=tally.get(name, 0))
                   for name in QUADRANTS.values()],
        on_the_line=[r['short'] for r in out if r['on_the_line']],
        # THE TEST, RUN. `fewer teachers, more classes` is consistent with the same staff
        # spread thinner ONLY if the classes got fuller. Where they got emptier, that
        # reading is refuted by the school's own third instrument, and the count of each
        # is published rather than described.
        spread_thinner=[r['short'] for r in thinner],
        fewer_teachers_more_classes=[r['short'] for r in inq
                                     if r['quadrant'] == QUADRANTS[('-', '+')]],
        fuller=[r['short'] for r in out if r['fuller']],
        emptier=[r['short'] for r in out if not r['fuller'] and r['avg_change'] < 0],
        one_step=[r['short'] for r in out if r['one_step']] if steps_readable else [],
    )


def decompose(db, rows, district, schools, subj, first, last):
    """One district subject, split across the buildings that make it up.

    THE DISTRICT FIGURE IS THE ONE ON THE PAGE AND IT IS THE ONE THAT HIDES THIS. Teacher
    FTE for a subject is a district total, and a total is what two schools moving in
    opposite directions looks like when nobody splits it.

    EVERY SCHOOL IS IN THE SPLIT, INCLUDING THE TWO WHOSE SECTION SERIES THIS PAGE WILL
    NOT TREND. Two identities are the whole value of a decomposition -- the parts make the
    whole on both instruments -- and dropping the schools that are awkward would break
    both and hide the break. What the awkward schools get instead is a FLAG on the row:
    their figures are two endpoints out of a series that swings 80% in a year, they are
    printed so the identity can be seen to close, and no trend is drawn through them."""
    d = [r for r in district['subjects'] if r['subj'] == subj]
    if not d:
        fail('%r is not among the district’s compared subjects, and this page '
             'decomposes it.' % subj)
    parts = []
    for s in schools:
        got = q(db, 'SELECT fy, teacher_fte FROM dese_teacher_subject '
                    "WHERE org_name=? AND subject_level='subject' AND subject=? "
                    'AND fy IN (?,?)', s['name'], subj, first, last)
        fte = {int(r['fy']): r['teacher_fte'] for r in got}
        if first not in fte or last not in fte:
            continue
        sa, sb = _sections(rows, s['name'], first, subj), _sections(rows, s['name'], last, subj)
        aa = [r for r in rows if r['org_name'] == s['name'] and r['sy'] == first
              and r['subj'] == subj]
        ab = [r for r in rows if r['org_name'] == s['name'] and r['sy'] == last
              and r['subj'] == subj]
        if sa is None or sb is None or not aa or not ab:
            fail('%s carries teacher FTE for %r and no class-size row at one end of the '
                 'window, so it cannot appear in a decomposition that has to add up.'
                 % (s['name'], subj))
        parts.append(dict(
            org=s['name'], trendable=bool(s['stability'] and s['stability']['trendable']),
            fte_first=fte[first], fte_last=fte[last],
            fte_change=round(fte[last] - fte[first], 1),
            sections_first=sa, sections_last=sb, sections_change=sb - sa,
            avg_first=round(aa[0]['avg_clss_cnt'], 1),
            avg_last=round(ab[0]['avg_clss_cnt'], 1),
            avg_change=round(ab[0]['avg_clss_cnt'] - aa[0]['avg_clss_cnt'], 1)))
    if len(parts) < 2:
        fail('%r is carried by fewer than two schools, so there is nothing to '
             'decompose.' % subj)
    fte_sum = round(sum(p['fte_change'] for p in parts), 1)
    sec_sum = sum(p['sections_change'] for p in parts)
    if abs(fte_sum - d[0]['fte_change']) > FTE_ROLLUP_TOL:
        fail('the schools’ %s FTE changes sum to %+.1f and the district’s is '
             '%+.1f. A decomposition whose parts do not make the whole is two unrelated '
             'numbers printed together.' % (subj, fte_sum, d[0]['fte_change']))
    if sec_sum != d[0]['sections_change']:
        fail('the schools’ %s section changes sum to %+d and the district’s is '
             '%+d. DESE suppresses small cells, so this can happen honestly — but it '
             'may not happen silently under a decomposition this page prints as an '
             'identity.' % (subj, sec_sum, d[0]['sections_change']))
    up = [p for p in parts if p['fte_change'] > FTE_ZERO]
    down = [p for p in parts if p['fte_change'] < -FTE_ZERO]
    if not up or not down:
        fail('%r no longer moves in both directions across the schools, and the '
             'conclusion this page draws from it is that the district figure hides two '
             'opposite moves.' % subj)
    return dict(subj=subj, short=_short(subj), district=d[0], parts=parts,
                fte_sum=fte_sum, sections_sum=sec_sum,
                gained=max(up, key=lambda p: p['fte_change']),
                lost=min(down, key=lambda p: p['fte_change']))


def reorganisation(span_rows, rows, schools):
    """What the two building changes were, and whether the unreadable years are them.

    THE TIDY EXPLANATION IS AVAILABLE AND IT IS WRONG. Two school-years in this file
    report an average class size no school can have, and both elementary schools' section
    counts swing by 80% and 111% in a year. The reorganisation is right there, and it
    would explain all of it neatly. It does not: the flagged years are checked against
    the boundary years here and MOSTLY MISS THEM. Rule 7 -- that the broken years line up
    with the reorganisation would be a measurement; that the reorganisation caused them
    would be a hypothesis; and here there is not even the correlation."""
    by_school = {}
    for org in sorted({r['org_name'] for r in span_rows}):
        by_school[org] = school_eras(span_rows, org)
    # A boundary is a year in which ANY school changed grade span or stopped or started
    # reporting -- read off the runs rather than typed.
    bounds = set()
    for org, runs in by_school.items():
        for i, r in enumerate(runs):
            if i:
                bounds.add(r['first_sy'])
        if runs[-1]['last_sy'] < max(x['sy'] for x in span_rows):
            bounds.add(runs[-1]['last_sy'] + 1)
        if runs[0]['first_sy'] > min(x['sy'] for x in span_rows):
            bounds.add(runs[0]['first_sy'])
    flagged = []
    for org in sorted({r['org_name'] for r in rows if r['org_type'] == 'School'}):
        pts = sorted((r for r in rows if r['org_name'] == org
                      and r['subj'] == ROLLUP_SUBJ), key=lambda r: r['sy'])
        for a, b in zip(pts, pts[1:]):
            if a['tot_clss_cnt'] and (abs(b['tot_clss_cnt'] - a['tot_clss_cnt'])
                                      / a['tot_clss_cnt']) > TRENDABLE_SWING:
                flagged.append(dict(org=org, from_sy=a['sy'], to_sy=b['sy'],
                                    from_sections=round(a['tot_clss_cnt']),
                                    to_sections=round(b['tot_clss_cnt']),
                                    at_boundary=b['sy'] in bounds))
    for r in implausible(rows):
        flagged.append(dict(org=r['org'], from_sy=r['sy'], to_sy=r['sy'],
                            from_sections=r['sections'], to_sections=r['sections'],
                            avg=r['avg'], at_boundary=r['sy'] in bounds))
    if not flagged:
        fail('no school-year is flagged as unreadable any more, and this page is built '
             'around two schools whose records cannot be trended.')
    at = sum(1 for f in flagged if f['at_boundary'])
    return dict(
        boundaries=sorted(bounds),
        eras=[dict(org=o, runs=r) for o, r in sorted(by_school.items())],
        flagged=flagged, flagged_count=len(flagged), at_boundary=at,
        away_from_boundary=len(flagged) - at,
        # Stated as the count rather than as a conclusion, because the count IS the
        # finding and the sentence around it would be the hypothesis.
        clusters_on_reorganisation=at > len(flagged) - at)


# ---- the eras, and why every trend on this page is built on them -------------------
#
# THE SPINE. Three of this page's boundaries are EVENTS and one is a judgement, and the
# difference is printed rather than blurred.
#
#   * SY2013 -- Thomas C Passios closes and every remaining school shifts up one grade
#     band. Read off DESE's enrolment-by-grade counts.
#   * SY2017 -- the new middle-school/high-school building opens and the structure resets
#     to what it was. Read off the same counts.
#   * SY2020 and SY2023 -- the pandemic. NOT in the data. We asserted it, it is labelled
#     as asserted everywhere it appears, and a reader can disagree with it in a way they
#     cannot disagree with a grade span.
#
# WHY THIS IS NOT A PRESENTATION CHOICE. Two findings drafted for this page from
# endpoint-to-endpoint comparisons did not survive contact with the eras, and both were
# wrong in the same direction:
#
#   * History at Lunenburg High reads as a 23-point fall in participation between SY2011
#     and SY2025. Averaged within eras it is 80, 59, 76, 65, 60 -- it fell only in the
#     four years the high school held grade 8, and RECOVERED when grade 8 left. The
#     endpoint comparison was measuring an eighth grade arriving and leaving.
#   * Arts reads as nearly doubling, 36 to 64. By era it is 41, 69, 57, 50, 61 -- the
#     same four grade-8 years, the same artefact, pointed the other way.
#
# Both are computed here rather than described, in `overturned()`, and both are ON the
# page, because the most convincing possible argument for why a two-point comparison
# misleads in this town is two of them that did.
#
# AND THE DISTINCTION THE ERAS BUY, which endpoints cannot express: a fall that recovered
# and a fall that did not are different problems, and only one of them is a decision
# anybody still has in front of them.

# The pandemic. A JUDGEMENT, not a reading -- the class-size file contains nothing that
# marks these years, and this constant is the whole of the assertion. It is separated from
# the structural boundaries everywhere it is used so that a reader can take it or leave it.
COVID = (2020, 2022)


def era_bands(runs, first, last):
    """The five eras, built from the high school's own grade spans plus the one boundary
    we assert. Nothing below is a typed year: change what DESE files and the bands move."""
    bounds = {first}
    for r in runs:
        if first <= r['first_sy'] <= last:
            bounds.add(r['first_sy'])
    asserted = {COVID[0], COVID[1] + 1}
    bounds |= {b for b in asserted if first < b <= last}
    edges = sorted(bounds) + [last + 1]
    out = []
    for a, b in zip(edges, edges[1:]):
        yrs = list(range(a, b))
        if not yrs:
            continue
        span = {r['span'] for r in runs
                for y in yrs if r['first_sy'] <= y <= r['last_sy']}
        if len(span) != 1:
            fail('SY%d–SY%d spans more than one high-school grade configuration '
                 '(%s). An era that straddles a reorganisation is the thing the eras '
                 'exist to stop.' % (a, b - 1, sorted(span)))
        # WHICH END OF THIS ERA IS A READING AND WHICH IS A JUDGEMENT, separately, so
        # the page can mark the pandemic boundary as ours without marking the
        # reorganisation as ours too.
        out.append(dict(first_sy=a, last_sy=b - 1, years=len(yrs), span=span.pop(),
                        first_asserted=a in asserted, last_asserted=b in asserted,
                        covid=a >= COVID[0] and b - 1 <= COVID[1]))
    if len(out) < 4:
        fail('only %d eras came out of the grade spans and the asserted pandemic '
             'boundary, and this page is written around a segmentation with a '
             'structural break, a reset and a shock in it.' % len(out))
    return out


# A grade band whose FTE is under this is nobody's teaching assignment. One year files
# 0.3 against the high school's 6-8 band while grade 8 is in a different building, which
# is a rounding artefact of an assignment filed against a band rather than a cohort.
GRADE_BAND_NOISE = 0.5


def assert_grade8_staffing(db, bands, g8):
    """THE ERA BOUNDARY, CHECKED AGAINST A SECOND INSTRUMENT THAT DOES NOT KNOW ABOUT IT.

    The grade spans on this page are read off DESE's enrolment-by-grade counts. DESE also
    publishes teaching FTE by GRADE BAND per school, in a different file collected for a
    different purpose -- and Lunenburg High's grades 6-8 band is nonzero in exactly the
    four years the enrolment file says grade 8 was in that building, and zero in every
    other year of nineteen.

    Two files that must agree is worth more than one file checked carefully, so this is an
    assertion rather than a reassurance: if enrolment and teacher assignment stop saying
    the same thing about which years the high school held grade 8, the build stops.

    `subject='All'` IS A ROLLUP ROW HERE TOO, exactly as in the class-size file, so this
    reads that row rather than summing the detail. And `multi_grade_fte` is not read at
    all: it moves 21.1 to 5.9 between two consecutive years while the school's total FTE
    barely moves, which is coding rather than staffing."""
    got = q(db, 'SELECT fy, grade_6_8_fte, grade_9_12_fte, total_fte '
                'FROM dese_teacher_grade_subject '
                "WHERE org_name=? AND subject='All' ORDER BY fy", HIGH)
    if not got:
        fail('dese_teacher_grade_subject carries no %s rows. A join that matches nothing '
             'looks exactly like a school that staffs nobody.' % HIGH)
    staffed = {int(r['fy']) for r in got
               if (r['grade_6_8_fte'] or 0) >= GRADE_BAND_NOISE}
    want = set(range(bands[g8]['first_sy'], bands[g8]['last_sy'] + 1))
    if staffed != want:
        fail('DESE’s enrolment counts put grade 8 in %s in %s, and its teacher '
             'assignment file staffs the 6-8 band in %s. Two state files disagree about '
             'when this school held a middle grade, and every era on this page rests on '
             'them agreeing.'
             % (HIGH, sorted(want), sorted(staffed)))
    fte = {int(r['fy']): r for r in got}
    return dict(
        years=sorted(want),
        grade_6_8=[dict(fy=y, fte=fte[y]['grade_6_8_fte'],
                        total=fte[y]['total_fte']) for y in sorted(want)],
        first=min(fte[y]['grade_6_8_fte'] for y in want),
        last=max(fte[y]['grade_6_8_fte'] for y in want),
        zero_years=sorted(set(fte) - want),
        noise_bound=GRADE_BAND_NOISE,
        # What the school's own total did across the same boundary -- the size of the
        # arrival, in the instrument that counts posts rather than children.
        total_before=fte[bands[g8]['first_sy'] - 1]['total_fte']
        if bands[g8]['first_sy'] - 1 in fte else None,
        total_during=round(sum(fte[y]['total_fte'] for y in want) / len(want), 1),
        total_after=fte[bands[g8]['last_sy'] + 1]['total_fte']
        if bands[g8]['last_sy'] + 1 in fte else None)


def era_schools(span_rows, bands):
    """Which schools reported in each era, from the state's own enrolment file. The
    era table's context line is derived from this rather than written."""
    out = []
    for e in bands:
        names = sorted({r['org_name'] for r in span_rows
                        if e['first_sy'] <= r['sy'] <= e['last_sy']})
        out.append(dict(e, schools=names, school_count=len(names)))
    return out


def era_series(rows, db, org, org_code, bands, first, last):
    """THE TRIPLE: what was staffed, how much room existed, and how many students got in
    — averaged within each era, per subject, on one time axis.

    Three instruments and three units, and they are never combined into one number. A
    reader matching a cut to what happened to students needs all three, because each pair
    of them can move apart:

      * teacher FTE -- posts. `dese_teacher_subject`, filed by fiscal year.
      * seats -- `tot_clss_cnt` x `avg_clss_cnt`, how many student-places ran. NOT the
        number of children: one child fills several.
      * participation -- distinct students in the subject over the school's own `All`
        row, the share of the school that took anything in it.

    THE ERA MEAN IS THE POINT AND THE YEARS ARE STILL PUBLISHED. A mean over four years
    is what survives one bad year in a file that has several; the yearly points are
    carried beside it so a reader can see what the mean is a mean of.

    THE FTE FILE RUNS A YEAR FURTHER THAN THE CLASS-SIZE FILE and that year is not in
    here. All three instruments are cut to the years the class-size collection covers, so
    the last era is the same length on all three."""
    got = q(db, 'SELECT fy, subject, teacher_fte FROM dese_teacher_subject '
                "WHERE org_name=? AND subject_level='subject'", org)
    fte = {(int(r['fy']), r['subject']): r['teacher_fte'] for r in got}
    den = {y['sy']: y['all_students']
           for y in participation_denominator(rows, db, org, org_code, first, last)['years']}
    cell = [r for r in rows if r['org_name'] == org and r['subj'] != ROLLUP_SUBJ
            and not r['subj'].startswith(CH74) and first <= r['sy'] <= last]
    out = []
    for s in sorted({r['subj'] for r in cell}):
        pts = {}
        for r in cell:
            if r['subj'] == s:
                pts[r['sy']] = r
        if not any(p['tot_stu_cnt'] for p in pts.values()):
            continue
        years, eras_ = [], []
        for e in bands:
            ys = [y for y in range(e['first_sy'], e['last_sy'] + 1) if y in pts]
            if not ys:
                continue
            have_fte = [fte[(y, s)] for y in ys if (y, s) in fte]
            eras_.append(dict(
                first_sy=e['first_sy'], last_sy=e['last_sy'], covid=e['covid'],
                participation=round(sum(pts[y]['tot_stu_cnt'] / den[y] for y in ys)
                                    / len(ys), 4),
                sections=round(sum(pts[y]['tot_clss_cnt'] for y in ys) / len(ys), 1),
                seats=round(sum(pts[y]['tot_clss_cnt'] * pts[y]['avg_clss_cnt']
                                for y in ys) / len(ys)),
                avg=round(sum(pts[y]['avg_clss_cnt'] for y in ys) / len(ys), 1),
                fte=(round(sum(have_fte) / len(have_fte), 2) if have_fte else None),
                fte_years=len(have_fte), years=len(ys)))
        for y in sorted(pts):
            r = pts[y]
            out_fte = fte.get((y, s))
            years.append(dict(sy=y, participation=round(r['tot_stu_cnt'] / den[y], 4),
                              sections=round(r['tot_clss_cnt']),
                              seats=round(r['tot_clss_cnt'] * r['avg_clss_cnt']),
                              avg=round(r['avg_clss_cnt'], 1),
                              fte=out_fte, students=round(r['tot_stu_cnt'])))
        if len(eras_) < 2:
            continue
        out.append(dict(subj=s, short=_short(s), eras=eras_, years=years,
                        has_fte=any(e['fte'] is not None for e in eras_),
                        # The whole point of the era view, as a field rather than a
                        # sentence: did it fall and come back, or fall and stay?
                        peak_era=max(range(len(eras_)),
                                     key=lambda i: eras_[i]['participation']),
                        low_era=min(range(len(eras_)),
                                    key=lambda i: eras_[i]['participation'])))
    if not out:
        fail('%s produced no era series at all.' % org)
    out.sort(key=lambda r: -r['eras'][-1]['participation'])
    return dict(org=org, bands=bands, subjects=out,
                first_sy=first, last_sy=last,
                units=dict(fte='full-time-equivalent teaching posts',
                           seats='student places — sections times the average class, '
                                 'not a count of children',
                           participation='the share of the school taking anything in '
                                         'the subject area'))


def grade8_shift(era, bands):
    """The subjects whose share of the high school moved when grade 8 moved.

    A FACT ABOUT THE SCHOOL, and the reason every trend on this page is read inside an
    era rather than across the file. For four years the high school held grade 8, and a
    subject an eighth grade all takes -- or none of it takes -- moves the school's share
    by twenty points in the year they arrive and back again in the year they leave,
    without one thing changing about what a ninth to twelfth grader was offered.

    So this finds them: every subject whose participation moves at least ten points INTO
    those four years and at least ten points back OUT of them, in opposite directions.
    Nothing here is a list chosen in advance; the threshold is the whole of the choice
    and the subjects come out of the file. Beside each one the page prints the years grade
    8 was in the building, which is what a reader needs to see the shape for what it is.
    """
    now = bands[-1]['span']
    odd = [i for i, b in enumerate(bands) if b['span'] != now]
    if len(odd) != 1:
        fail('the high school no longer holds exactly one era at a grade span other '
             'than its current one, and this section rests on there being one.')
    g8 = odd[0]
    if g8 == 0 or g8 == len(bands) - 1:
        fail('the era at a different grade span is at one end of the series, so there '
             'is no step into it and out of it to measure.')
    out = []
    for r in era['subjects']:
        band = [e['participation'] for e in r['eras']]
        if len(band) != len(bands):
            continue
        into = round(band[g8] - band[g8 - 1], 4)
        out_of = round(band[g8 + 1] - band[g8], 4)
        if min(abs(into), abs(out_of)) < 0.10 or (into > 0) == (out_of > 0):
            continue
        ys = r['years']
        out.append(dict(
            subj=r['subj'], short=r['short'],
            first_sy=ys[0]['sy'], last_sy=ys[-1]['sy'],
            end_to_end=round(ys[-1]['participation'] - ys[0]['participation'], 4),
            era_values=band, into=into, out_of=out_of,
            grade8_era=g8, grade8_span=bands[g8]['span'], current_span=now,
            grade8_first_sy=bands[g8]['first_sy'],
            grade8_last_sy=bands[g8]['last_sy'],
            # WHAT THE SUBJECT DID ONCE GRADE 8 WAS GONE, which is the comparison a
            # reader of this page actually wants and the one the whole-file endpoints
            # cannot make: the eras at the current configuration, on their own.
            since=[dict(first_sy=e['first_sy'], last_sy=e['last_sy'],
                        participation=e['participation'], covid=e['covid'])
                   for e in r['eras'][g8 + 1:]],
            since_change=round(band[-1] - band[g8 + 1], 4)))
    if not out:
        fail('no subject at the high school now moves ten points into the grade-8 years '
             'and ten points back out, and this page explains its eras with the ones '
             'that do.')
    out.sort(key=lambda r: -abs(r['into']))
    return dict(grade8_era=g8, grade8_first_sy=bands[g8]['first_sy'],
                grade8_last_sy=bands[g8]['last_sy'],
                grade8_span=bands[g8]['span'], current_span=now,
                subjects=out, count=len(out))


# ---- the third instrument: how many children got in -------------------------------
#
# THE QUESTION THIS ANSWERS, AND IT IS NOT THE ONE THE SECTION COUNTS ANSWER. A resident
# asked whether Lunenburg students are being offered less substantive work AND TAKING IT:
# a Miscellaneous bucket rising while music, mathematics and the rest fall would be
# children filling slots because nothing else fits their timetable. Sections cannot see
# that. A subject can gain sections and lose students, and Miscellaneous at Lunenburg High
# does exactly that.
#
# `tot_stu_cnt` IS DISTINCT STUDENTS IN A SUBJECT AREA AND IT IS NOT SEATS. The two are
# routinely confused and the file settles it twice over: at Lunenburg High in SY2025
# Mathematics runs 32 sections averaging 14.5 -- 464 seats -- against a `tot_stu_cnt` of
# 434; and the 22 subject rows sum to 2,726 against an `All` row of 438, because a student
# takes several subjects. What the `All` row DOES track is the school: within 3.4% of
# DESE's own enrolment count in all fifteen years, which is what makes
# `subject students / All students` a PARTICIPATION RATE -- the share of the school taking
# anything in that subject area.
#
# THE DENOMINATOR IS THE `All` ROW AND NEVER A SUM OF THE DETAIL. `assert_rollups()`
# already refuses to write unless the detail sections sum to the `All` sections, and the
# participation rate here divides by the `All` row's own student count. The two are checked
# against each other in `participation_denominator()` below, and against DESE's separate
# enrolment file, so a share on this page has a denominator that three sources agree about.
#
# RULE 7 GOVERNS THE READING AND THE READING IS NOT WHAT THE QUESTION EXPECTED. Within the
# comparable window Miscellaneous participation at Lunenburg High is flat while its
# sections rise by half -- more groups, smaller ones, the same share of the school. Two
# subjects DID lose participation heavily, and both of their falls happen in a single year.
# Every one of those is a measurement; every explanation for one is a hypothesis; and the
# page carries the measurements and both readings.

def participation_denominator(rows, db, org, org_code, first, last):
    """That the `All` row's student count is the school, checked against a second file.

    A share is only as good as what it is over, and this one is over a column whose
    meaning is not printed anywhere. So it is established rather than assumed: the `All`
    row against DESE's enrolment-by-grade count for the same school in the same year, and
    the worst disagreement published beside the series it underwrites."""
    enr = {int(r['fy']): r['total_cnt']
           for r in q(db, 'SELECT fy, total_cnt FROM dese_enrollment '
                          "WHERE org_code=? AND org_level='school'", org_code)}
    out, worst = [], 0.0
    for sy in range(first, last + 1):
        m = [r for r in rows if r['org_name'] == org and r['sy'] == sy
             and r['subj'] == ROLLUP_SUBJ]
        if not m or not m[0]['tot_stu_cnt']:
            fail('%s has no usable All row in SY%d, and every participation share on '
                 'this page is over it.' % (org, sy))
        e = enr.get(sy)
        if not e:
            fail('DESE’s enrolment file carries no SY%d row for %s, and the '
                 'denominator of every share on this page is checked against it.'
                 % (sy, org))
        gap = abs(m[0]['tot_stu_cnt'] - e) / e
        worst = max(worst, gap)
        out.append(dict(sy=sy, all_students=round(m[0]['tot_stu_cnt']),
                        enrolled=round(e), gap=round(gap, 4)))
    if worst > 0.05:
        fail('the All row and DESE’s enrolment count for %s differ by up to %.1f%%. '
             'A participation rate over a denominator that is not the school is not a '
             'participation rate.' % (org, worst * 100))
    return dict(years=out, worst_gap=round(worst, 4),
                bound=0.05,
                what='distinct students on the file’s own `All` row, checked against '
                     'DESE’s separate enrolment-by-grade count for the same school '
                     'and year')


# How far a year has to stand off BOTH its neighbours, in share-of-the-school points,
# before it is a spike rather than a movement. One year in this file clears it -- and it
# clears it by 33 points.
SPIKE = 0.15


def _spike(before, here, after):
    return ((here - before > SPIKE and here - after > SPIKE)
            or (before - here > SPIKE and after - here > SPIKE))


def participation(rows, db, org, org_code, first, last):
    """Every subject's share of the school, year by year, with what moved and WHEN."""
    den = participation_denominator(rows, db, org, org_code, first, last)
    total = {y['sy']: y['all_students'] for y in den['years']}
    cell = [r for r in rows if r['org_name'] == org and r['subj'] != ROLLUP_SUBJ
            and not r['subj'].startswith(CH74) and first <= r['sy'] <= last]
    out = []
    for s in sorted({r['subj'] for r in cell}):
        pts = []
        for sy in range(first, last + 1):
            m = [r for r in cell if r['subj'] == s and r['sy'] == sy]
            if not m:
                fail('%s has no %r row in SY%d. A missing row and a zero are different '
                     'facts.' % (org, s, sy))
            pts.append(dict(sy=sy, students=round(m[0]['tot_stu_cnt']),
                            share=round(m[0]['tot_stu_cnt'] / total[sy], 4),
                            sections=round(m[0]['tot_clss_cnt']),
                            avg=round(m[0]['avg_clss_cnt'], 1)))
        if not any(p['students'] for p in pts):
            continue
        a, b = pts[0], pts[-1]
        step = max(zip(pts, pts[1:]),
                   key=lambda ab: abs(ab[1]['share'] - ab[0]['share']))
        d = round(b['share'] - a['share'], 4)
        ds = round(step[1]['share'] - step[0]['share'], 4)
        out.append(dict(
            subj=s, short=_short(s), points=pts,
            first_share=a['share'], last_share=b['share'], share_change=d,
            first_students=a['students'], last_students=b['students'],
            sections_first=a['sections'], sections_last=b['sections'],
            sections_change=b['sections'] - a['sections'],
            avg_first=a['avg'], avg_last=b['avg'],
            # WHEN, not just how much. Two of the three largest falls at the high school
            # happen entirely between SY2020 and SY2021, and a reader shown only the two
            # endpoints would read a step in one year as a drift across nine.
            step=ds, step_from_sy=step[0]['sy'], step_to_sy=step[1]['sy'],
            one_step=abs(d) >= 0.05 and abs(ds) >= abs(d),
            # A year that disagrees with BOTH its neighbours by more than 15 points IN
            # THE SAME DIRECTION -- up from one and up from the other, or down from
            # both. That is a spike; a year that is 15 points below the one before it
            # and stays there is a STEP, and the two must not be confused. Comparing
            # against the MEAN of the neighbours does confuse them, and it also flags
            # the years either side of a real spike as spikes themselves.
            spikes=[pts[i]['sy'] for i in range(1, len(pts) - 1)
                    if _spike(pts[i - 1]['share'], pts[i]['share'],
                              pts[i + 1]['share'])],
        ))
    if not out:
        fail('%s has no subject with any student in it.' % org)
    movers = sorted(out, key=lambda r: -abs(r['share_change']))
    return dict(
        org=org, first_sy=first, last_sy=last, years=last - first + 1,
        denominator=den, subjects=out,
        movers=[r['short'] for r in movers[:6]],
        fell=[r['short'] for r in out if r['share_change'] <= -0.05],
        rose=[r['short'] for r in out if r['share_change'] >= 0.05],
        held=[r['short'] for r in out if abs(r['share_change']) < 0.05],
        one_step=[dict(short=r['short'], from_sy=r['step_from_sy'],
                       to_sy=r['step_to_sy'], step=r['step'])
                  for r in out if r['one_step']],
        spiked=[dict(short=r['short'], years=r['spikes']) for r in out if r['spikes']],
    )


def more_groups_same_share(part, subj):
    """The worked case, and the one that answers the question it was asked to answer.

    THE HYPOTHESIS WAS THAT MISCELLANEOUS IS A STUDY HALL absorbing students who cannot
    schedule anything else -- which would show as its share of the school RISING while
    academic subjects fell. What the file shows is its sections rising by half and its
    share of the school not moving, in groups averaging under five. Both are measurements.
    Neither settles what a Miscellaneous group IS, and DESE publishes no course name for
    any of them, so this function produces the numbers and the page carries both readings.
    """
    m = [r for r in part['subjects'] if r['subj'] == subj]
    if not m:
        fail('%r is not among %s’s subjects and this page works it as an example.'
             % (subj, part['org']))
    r = m[0]
    if r['sections_change'] <= 0:
        fail('%s at %s no longer gains sections across the window, and the worked case '
             'on this page is a subject gaining sections while its share of the school '
             'does not move.' % (subj, part['org']))
    seats_first = round(r['sections_first'] * r['avg_first'])
    seats_last = round(r['sections_last'] * r['avg_last'])
    return dict(
        subj=subj, short=_short(subj),
        first_sy=part['first_sy'], last_sy=part['last_sy'],
        sections_first=r['sections_first'], sections_last=r['sections_last'],
        sections_change=r['sections_change'],
        share_first=r['first_share'], share_last=r['last_share'],
        share_change=r['share_change'],
        avg_first=r['avg_first'], avg_last=r['avg_last'],
        students_first=r['first_students'], students_last=r['last_students'],
        # SEATS, SAID TO BE SEATS. Sections times the average is how many student-places
        # ran; the student count is how many DIFFERENT children were in them. The ratio
        # is how many Miscellaneous things a child in one takes, and it is the figure
        # that makes the size of these groups legible.
        seats_first=seats_first, seats_last=seats_last,
        per_student_first=round(seats_first / r['first_students'], 1)
        if r['first_students'] else None,
        per_student_last=round(seats_last / r['last_students'], 1)
        if r['last_students'] else None,
        spikes=r['spikes'])


def per_school(db, rows, span_rows, class_years, fte_years):
    """Every school in the current configuration, on its OWN window.

    Not on a common one. Forcing four schools onto one span would either throw away years
    or straddle a reorganisation, and both are worse than four charts with four spans
    printed on them. As it happens all four windows come out the same here -- the SY2017
    reset is what starts every one of them -- and that is a derived fact rather than a
    convenience, so it is asserted below instead of assumed."""
    out = []
    for org in sorted({r['org_name'] for r in rows if r['org_type'] == 'School'
                       and r['sy'] == max(r2['sy'] for r2 in rows)}):
        runs = school_eras(span_rows, org)
        has_fte = any(y in fte_years.get(org, ()) for y in class_years)
        if not has_fte:
            # The Advanced Community Experience Program: one section a year, four to nine
            # children, and no teacher FTE filed against it at all. Named rather than
            # dropped, because a school missing from a list of schools is a hole.
            pts = [r for r in rows if r['org_name'] == org and r['subj'] == ROLLUP_SUBJ]
            out.append(dict(name=org, org_code=pts[0]['org_code'], eras=runs,
                            window=None, stability=None, subjects=None,
                            instruments=None, participation=None,
                            excluded='ran %s section a year for %s children and files no '
                                     'teacher FTE of its own — there is nothing to '
                                     'trend and nothing to set beside it'
                                     % (C.num(max(round(p['tot_clss_cnt']) for p in pts)),
                                        C.num(max(round(p['tot_stu_cnt']) for p in pts)))))
            continue
        w = latest_era(runs, org, class_years, fte_years[org])
        st = stability(rows, org, w['first_sy'], w['last_sy'])
        entry = dict(name=org, org_code=[r for r in rows if r['org_name'] == org][0]['org_code'],
                     eras=runs, window=w, stability=st, excluded=None)
        if st['trendable']:
            entry['subjects'] = by_subject(rows, org, w['first_sy'], w['last_sy'])
            entry['instruments'] = instruments(db, rows, org, w['first_sy'], w['last_sy'],
                                               steps_readable=True)
            entry['participation'] = participation(rows, db, org, entry['org_code'],
                                                   w['first_sy'], w['last_sy'])
        else:
            entry['subjects'] = None
            entry['instruments'] = None
            entry['participation'] = None
            entry['excluded'] = (
                'its total section count moved %s in one year — %s to %s between '
                '%s and %s — while its own enrolment moved %s. A subject series '
                'inside a school total that does that is not a series'
                % (C.pct(st['swing'] * 100), C.num(st['from_sections']),
                   C.num(st['to_sections']), 'SY%d' % st['from_sy'],
                   'SY%d' % st['to_sy'], C.pct(st['students_swing'] * 100)))
        out.append(entry)
    if not out:
        fail('no school is in the most recent year of the class-size file.')
    return out


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


def _era_history(era):
    """History at the high school across the eras, and the assertion the card rests on:
    that all THREE instruments moved the same way.

    The comparison is the era before the pandemic against the era now -- both at the same
    grade span, both after the new building opened -- and NOT the two ends of the file,
    which straddle a reorganisation this page has already shown is worth sixteen points
    on its own."""
    m = [r for r in era['subjects'] if r['subj'] == 'History']
    if not m:
        fail('History is not in the era series and a conclusion on this page rests on '
             'it.')
    bands = m[0]['eras']
    now = bands[-1]
    before = [b for b in bands if b['last_sy'] < now['first_sy'] and not b['covid']]
    if not before:
        fail('there is no pre-pandemic era at the current configuration to compare the '
             'present one with.')
    was = before[-1]
    for k in ('participation', 'seats', 'fte'):
        if was[k] is None or now[k] is None:
            fail('History has no %s in one of the two eras this page compares.' % k)
        if now[k] >= was[k]:
            fail('History’s %s is no longer lower now than before the pandemic '
                 '(%s then, %s now), and the conclusion on this page is that all three '
                 'instruments moved down together. Rewrite it rather than shipping a '
                 'claim the data no longer makes.' % (k, was[k], now[k]))
    return dict(before=was['participation'], now=now['participation'],
                fte_before=was['fte'], fte_now=now['fte'],
                seats_before=was['seats'], seats_now=now['seats'],
                era_first_sy=was['first_sy'], era_last_sy=now['last_sy'],
                era_last_first_sy=now['first_sy'],
                from_sy=was['last_sy'] + 1)


def build_conclusions(hs, hs_subj, fj, cs, first, last, lang, mc, split, era):
    """What this page establishes, as DATA rather than as sentences in a page.

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

    era_h = _era_history(era)
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
            id='history-lost-staff-seats-and-takers-together',
            claim='%s of Lunenburg High takes a history course, against %s before %s.'
                  % (C.pct(era_h['now'] * 100), C.pct(era_h['before'] * 100),
                     'SY%d' % era_h['from_sy']),
            so_what='Teacher FTE went %s to %s and seats %s to %s — the one subject '
                    'where all three fell.'
                    % (era_h['fte_before'], era_h['fte_now'],
                       C.num(era_h['seats_before']), C.num(era_h['seats_now'])),
            figures={
                'now': figure(era_h['now'], C.pct(era_h['now'] * 100)),
                'before': figure(era_h['before'], C.pct(era_h['before'] * 100)),
                'from_sy': sy(era_h['from_sy']),
                'fte_before': figure(era_h['fte_before'], str(era_h['fte_before'])),
                'fte_now': figure(era_h['fte_now'], str(era_h['fte_now'])),
                'seats_before': figure(era_h['seats_before'],
                                       C.num(era_h['seats_before'])),
                'seats_now': figure(era_h['seats_now'], C.num(era_h['seats_now'])),
                'era_first': sy(era_h['era_first_sy']),
                'era_last': sy(era_h['era_last_sy']),
                'era_last_first': sy(era_h['era_last_first_sy']),
            },
            figure='now',
            kind='measured',
            bearing='lever',
            lede='Three instruments measure this page’s question — what was '
                 'staffed, how much room ran, and how many children got in — and '
                 'this is the only subject at the high school where all three moved down '
                 'together.',
            detail='Averaged over %s to %s the school staffed %s posts of history and '
                   '%s student places ran; over %s to %s it is %s posts and %s places, '
                   'and the share of the school taking a history course went from %s to '
                   '%s. The averages are over eras rather than single years on purpose: '
                   'the same subject read end to end across the whole file appears to '
                   'fall by a third more than this, and most of that is a reorganisation '
                   'rather than a change in provision.'
                   % ('SY%d' % era_h['era_first_sy'], 'SY%d' % era_h['from_sy'],
                      era_h['fte_before'], C.num(era_h['seats_before']),
                      'SY%d' % era_h['era_last_first_sy'],
                      'SY%d' % era_h['era_last_sy'], era_h['fte_now'],
                      C.num(era_h['seats_now']), C.pct(era_h['before'] * 100),
                      C.pct(era_h['now'] * 100)),
            basis='Teacher FTE, sections times average class size, and distinct students '
                  'over the school’s own `All` row — three DESE series for the '
                  'same subject at the same school, averaged inside eras whose '
                  'boundaries are the school’s own grade spans plus one we assert '
                  'for the pandemic.',
            not_shown='That a staffing decision caused it. The fall begins in the years '
                      'the pandemic closed and reopened this school, students choose '
                      'their own courses at this level, and history teaching recovered '
                      'part of a post since without the share recovering with it. Those '
                      'are three readings of one set of numbers and this page does not '
                      'choose between them.',
            see=[('/school-staffing', 'Teacher FTE by subject')],
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
        ),

        # ---- what the eras and the third instrument added -----------------------
        #
        # THREE CARDS, AND THE REASON EACH IS A CARD RATHER THAN A PARAGRAPH.
        #
        # The first answers the question a resident actually asked -- whether children
        # are being parked in filler classes because nothing else fits -- and it answers
        # it against the expectation. The second makes a district figure this page
        # already published legible, by saying which building it happened in. The third
        # is the one place in the file where all three instruments move together.
        #
        # WHAT IS NOT A CARD, deliberately: that two of our own drafted findings were
        # artefacts of a reorganisation. That is true, it is on the page, and it is about
        # a METHOD rather than about the world -- conclusions.py's fourth test.
        conclusion(
            id='miscellaneous-is-more-groups-not-more-students',
            claim='Miscellaneous went from %s sections to %s at Lunenburg High, taking '
                  'the same share of students.'
                  % (C.num(mc['sections_first']), C.num(mc['sections_last'])),
            so_what='More groups, smaller — %s students each. %s of the school took '
                    'one in %s and %s now.'
                    % (mc['avg_last'], C.pct(mc['share_first'] * 100),
                       'SY%d' % mc['first_sy'], C.pct(mc['share_last'] * 100)),
            figures={
                'sections_last': figure(mc['sections_last'],
                                        C.num(mc['sections_last']), 'course sections'),
                'sections_first': figure(mc['sections_first'],
                                         C.num(mc['sections_first'])),
                'avg_last': figure(mc['avg_last'], str(mc['avg_last'])),
                'avg_first': figure(mc['avg_first'], str(mc['avg_first'])),
                'share_first': figure(mc['share_first'],
                                      C.pct(mc['share_first'] * 100)),
                'share_last': figure(mc['share_last'],
                                     C.pct(mc['share_last'] * 100)),
                'students_last': figure(mc['students_last'],
                                        C.num(mc['students_last'])),
                'seats_last': figure(mc['seats_last'], C.num(mc['seats_last'])),
                'per_student': figure(mc['per_student_last'],
                                      str(mc['per_student_last'])),
                'sy_first': sy(mc['first_sy']), 'sy_last': sy(mc['last_sy']),
                'spike': sy(mc['spikes'][0]),
            },
            figure='sections_last',
            kind='measured',
            bearing='sizes',
            lede='A resident asked whether children are being offered thinner work and '
                 'taking it — a filler bucket swelling while the subjects around it '
                 'shrink. This is the bucket, and the count of children in it did not '
                 'move.',
            detail='%s student places ran in Miscellaneous at Lunenburg High in %s '
                   'among %s different children, so a child in one is in about %s of '
                   'them; the groups averaged %s students at the start of the window. '
                   'Groups of under five are the shape of small-group support, not '
                   'of a room somebody is parked in — and that is a reading, not a '
                   'finding, because DESE files no course name against any of them. One '
                   'year stands off its neighbours by more than thirty points, %s, and '
                   'the page marks it rather than averaging it in.'
                   % (C.num(mc['seats_last']), 'SY%d' % mc['last_sy'],
                      C.num(mc['students_last']), str(mc['per_student_last']),
                      str(mc['avg_first']), 'SY%d' % mc['spikes'][0]),
            basis='`tot_clss_cnt`, `avg_clss_cnt` and `tot_stu_cnt` for the '
                  'Miscellaneous subject area at Lunenburg High, over the school’s '
                  'own `All` row — which DESE’s separate enrolment file agrees '
                  'with to within a few per cent in every year.',
            not_shown='What any of these groups is. Academic support, an elective, '
                      'directed study and a study hall all fit these numbers, and '
                      'nothing published separates them. What would: the district’s '
                      'own Program of Studies, which exists and is not published.',
            see=[('/what-we-cannot-answer', 'The gap this leaves')],
        ),
        conclusion(
            id='mathematics-moved-between-two-buildings',
            claim='Mathematics teacher FTE fell %s at the middle school and rose %s at '
                  'the high school.' % (abs(split['lost']['fte_change']),
                                        split['gained']['fte_change']),
            so_what='The district figure is %s and shows neither. Middle school classes '
                    'went from %s to %s.'
                    % (split['district']['fte_change'], split['lost']['avg_first'],
                       split['lost']['avg_last']),
            figures={
                'lost': figure(split['lost']['fte_change'],
                               str(abs(split['lost']['fte_change'])),
                               'full-time teaching posts'),
                'gained': figure(split['gained']['fte_change'],
                                 str(split['gained']['fte_change'])),
                'district': figure(split['district']['fte_change'],
                                   str(split['district']['fte_change'])),
                'avg_first': figure(split['lost']['avg_first'],
                                    str(split['lost']['avg_first'])),
                'avg_last': figure(split['lost']['avg_last'],
                                   str(split['lost']['avg_last'])),
                'sec_lost': figure(split['lost']['sections_change'],
                                   C.num(abs(split['lost']['sections_change']))),
                'sec_gained': figure(split['gained']['sections_change'],
                                     C.num(split['gained']['sections_change'])),
                'hs_avg_last': figure(split['gained']['avg_last'],
                                      str(split['gained']['avg_last'])),
                'sy_first': sy(first), 'sy_last': sy(last),
            },
            figure='lost',
            kind='measured',
            bearing='lever',
            lede='This page already published the district figure for mathematics and '
                 'called it the one subject where the two instruments disagree. Split by '
                 'building, it is not one subject disagreeing with itself — it is '
                 'two schools going opposite ways.',
            detail='Between %s and %s the middle school ran %s fewer mathematics '
                   'sections and its classes went from %s students to %s. The high '
                   'school ran %s more and its classes fell to %s. Both are inside one '
                   'district figure, and the '
                   'four schools’ FTE adds up to it exactly. Which building a post '
                   'sits in is a thing this town decides, so this is a dial rather than '
                   'a condition — and nothing here says what it should be set to.'
                   % ('SY%d' % first, 'SY%d' % last,
                      C.num(abs(split['lost']['sections_change'])),
                      split['lost']['avg_first'], split['lost']['avg_last'],
                      C.num(split['gained']['sections_change']),
                      split['gained']['avg_last']),
            basis='`dese_teacher_subject` teacher FTE per school against '
                  '`dese_class_size` sections and average class size for the same '
                  'subject, over the years both files cover. The generator refuses to '
                  'write unless the schools’ FTE sums to the district’s and '
                  'their sections sum to the district’s.',
            not_shown='Why. A post can move because a timetable changed, because a '
                      'retirement was not replaced, because a grant ended, or because '
                      'the two schools were staffed to different targets. Nothing in '
                      'either state file distinguishes them.',
            see=[('/school-staffing', 'The FTE series in full')],
        ),
    ]
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

        # ---- the two instruments, per school ------------------------------------
        # The district figure this page already publishes, DRAWN and then SPLIT. Every
        # assertion below is fail-closed: the FTE rollup, the schools' windows being
        # their own most recent grade span, the stability separation the exclusion
        # rests on, and the decomposition summing to the district figure it decomposes.
        fte_rollup = assert_fte_rollup(db, first, last)
        class_years = sorted({r['sy'] for r in rows})
        fte_years = collections.defaultdict(set)
        for r in q(db, 'SELECT DISTINCT fy, org_name FROM dese_teacher_subject '
                       "WHERE lea=? AND subject_level='subject'", LEA):
            fte_years[r['org_name']].add(int(r['fy']))
        schools = per_school(db, rows, span_rows, class_years, fte_years)
        assert_stability([s for s in schools if s['stability']])
        # THE DISTRICT'S OWN STEPS ARE NOT READABLE and the payload says so rather than
        # the page remembering it: the total is the sum of five schools, two of whose
        # counts this page refuses to trend, and its intermediate years carry their
        # swings. Both ENDS are ordinary years at all five, so the endpoints stand.
        district_inst = instruments(db, rows, DISTRICT, first, last,
                                    steps_readable=False)
        hs_part = [s for s in schools if s['name'] == HIGH][0]['participation']
        misc_case = more_groups_same_share(hs_part, 'Miscellaneous')

        # ---- the eras, and the three instruments on them --------------------------
        file_first = min(r['sy'] for r in rows)
        file_last = max(r['sy'] for r in rows)
        bands = era_schools(span_rows, era_bands(era_runs, file_first, file_last))
        hs_code = [r for r in rows if r['org_name'] == HIGH][0]['org_code']
        hs_era = era_series(rows, db, HIGH, hs_code, bands, file_first, file_last)
        g8_shift = grade8_shift(hs_era, bands)
        g8_staffing = assert_grade8_staffing(db, bands, g8_shift['grade8_era'])
        split_subj = decompose(db, rows, district_inst, schools,
                               fj["biggest_disagreement"]["subj"], first, last)
        reorg = reorganisation(span_rows, rows, schools)

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
            schools=schools,
            instruments=district_inst,
            fte_rollup=fte_rollup,
            decomposition=split_subj,
            miscellaneous=misc_case,
            bands=bands,
            era_series=hs_era,
            grade8_shift=g8_shift,
            grade8_staffing=g8_staffing,
            reorganisation=reorg,
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
            conclusions=build_conclusions(
                hs, hs_subj, fj, cs, first, last,
                language(rows, hs_subj, ms_subj, hs, middle),
                misc_case, split_subj, hs_era),
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
