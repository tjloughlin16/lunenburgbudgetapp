#!/usr/bin/env python3
"""The cut register — what the schools said they were cutting, and whether it shows.

    python3 scripts/build_cut_register.py            # write it
    python3 scripts/build_cut_register.py --check    # fail if it is stale

TWO LAYERS, AND THE WHOLE POINT IS THAT THEY ARE NOT ADDED TOGETHER.

LAYER ONE is what the district PUT IN WRITING: `stated_cuts`, extracted by
scripts/extract_stated_cuts.py out of nine of its own budget documents, every row quoted
at a page. Rule 13a governs it absolutely. A reduction list is a document somebody
ASSEMBLED to argue for a budget; the slide numbers and the letterhead are not provenance.
It is strong evidence of INTENT, published by the people who held the intent, and it is
not evidence that anything happened.

LAYER TWO is what an INSTRUMENT recorded afterwards, collected by somebody who was not in
the argument: DESE's teacher FTE by school and subject, submitted through EPIMS on the
first of October each year, FY2008 to FY2026. Nothing about it is produced by the district
to make a case.

The two are reported side by side and never summed. A count of cuts announced and a count
of cuts an instrument can see are different quantities about different things, and one
blended figure would be a claim neither layer supports.

WHY THIS IS NOT AN AUDIT, WHICH IS RULE 8 AND IS LOAD-BEARING HERE. A cut announced and
not visible afterwards has many innocent readings and the page names them every time: a
grant appeared; a retirement changed the arithmetic (the district's own FY25 slides say
twice that a cut "will be absorbed by a retirement"); enrolment moved; the position was
restored in public by a later vote, which is exactly what the FY2020 record shows
happening. The finding is what the record shows. It is never that anybody lied.

THREE THINGS THE INSTRUMENT STRUCTURALLY CANNOT DO, and they are on the page and in
money_gaps rather than in a footnote:

  1. IT COUNTS TEACHERS. Paraprofessionals, secretaries, custodians, guidance staff,
     social workers, maintenance and BCBAs are most of every list here and appear in no
     published per-school series at all.
  2. IT IS ONE DAY A YEAR. A post cut in June and filled again in November is invisible to
     an October snapshot, and that is precisely the reversal residents describe.
  3. IT APPORTIONS BY ASSIGNMENT, NOT BY PERSON. DESE's subject FTE moves when a teacher's
     timetable changes, so a subject can rise while a post in it is removed.

WHAT REFUSES TO WRITE. Every one of these has the shape of a defect this project has
already shipped -- a join that matches nothing looking exactly like data that is absent:

  * `stated_cuts` missing, empty, or missing any of the five budget cycles;
  * the DESE teacher series missing, or missing Lunenburg at school level;
  * the OPERATIVE list of any cycle being empty -- the register's spine is one list per
    cycle that was actually adopted, and a cycle with none would silently drop out;
  * the FY2020 withdrawal case, the FY2025 override case and the FY2026 world language
    case not reproducing from the data, since each is a named claim in a conclusion;
  * any of the three money_gaps rows this page cites by key having been renamed;
  * any meeting quote no longer being present verbatim in the file it is attributed to.
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
DB = os.path.join(ROOT, 'sources/data/lunenburg.db')
OUT = os.path.join(ROOT, 'fy28/public/data/cut-register.json')
MINUTES = 'sources/meetings/text'

# ---- the instrument -----------------------------------------------------------------
#
# DESE's teacher FTE, per school, per subject. The org names are the STATE'S, and the
# mapping from the district's own school shorthand to them is ours because nothing
# published joins the two. `mid-high` is the district's own word for a post shared across
# the middle and high schools, and it is tested against the two schools SUMMED rather than
# against either one -- a world language teacher covering both buildings is one FTE split
# over two org codes in EPIMS, and testing either half alone would find half a cut.
ORG = {
    'primary': ['Lunenburg Primary School'],
    'turkey-hill': ['Turkey Hill Elementary School'],
    'middle': ['Lunenburg Middle School'],
    'high': ['Lunenburg High'],
    'ace': ['Advanced Community Experience Program'],
    'mid-high': ['Lunenburg Middle School', 'Lunenburg High'],
    'primary-and-turkey-hill': ['Lunenburg Primary School',
                                'Turkey Hill Elementary School'],
    'high-and-primary': ['Lunenburg High', 'Lunenburg Primary School'],
    'middle-and-high': ['Lunenburg Middle School', 'Lunenburg High'],
    'district': None,          # the district row, which DESE publishes separately
}
DISTRICT_ORG = 'Lunenburg'

# WHICH DESE SUBJECT A JOB TITLE IS. OURS, declared here, published in the payload, and
# matched on WORD BOUNDARIES -- an early draft matched `art` inside `Part-Time Secretary`
# and filed a secretary as an arts teacher in three years running.
#
# The list is deliberately short. A title that is not obviously one of these subjects gets
# no subject rather than a guess, because a wrong subject produces a confident verdict and
# no subject produces an honest `cannot see`.
SUBJECT = [
    ('Arts', r'\b(music|band|art|arts)\b'),
    ('Foreign Language', r'\b(world language|foreign language|fl)\b'),
    ('Mathematics', r'\bmath\b'),
    ('Science', r'\bscience\b'),
    ('English/Language Arts', r'\b(english|humanities|ela)\b'),
    ('History', r'\b(history|social studies)\b'),
    ('Reading', r'\b(reading|literacy)\b'),
]

# A CLASSROOM TEACHER has no subject in DESE's file below the high school, because an
# elementary teacher teaches all of them. These titles are tested against the school's
# whole teacher count instead.
CLASSROOM = r'\b(classroom teacher|grade \d teacher|grade \d+ teacher|bubble teacher)\b'

# JOBS THE PUBLISHED SERIES DO NOT MEASURE AT ALL, per school or otherwise, in the years
# this register covers. This is not a shortcoming of the extract: DESE publishes teacher
# FTE by school, and its educator workforce headcount -- which does carry
# paraprofessionals and administrators -- exists for Lunenburg in FY2021 to FY2023 only,
# which is none of the years a list here would be tested in.
UNMEASURED = r'\b(paraprofessional|para|secretary|secretaries|clerk|custodian|custodial|' \
             r'maintenance|guidance|counselor|counsellor|social worker|adjustment|' \
             r'bcba|psychologist|nurse|principal|superintendent|director|coach|tutor|' \
             r'librarian|library|occupational therapy|cota|trainer|it tech|' \
             r'business manager|instructional coach|specialist)\b'

# HOW BIG A MOVEMENT HAS TO BE. Ours, and the payload states both numbers so the page can
# print them rather than describe them.
#
# DESE publishes FTE to one decimal place, so 0.1 is the resolution of the instrument
# itself. The tolerance is set at 0.15 -- above the rounding, below the smallest cut any
# document here states (0.2). A movement inside it is reported as the instrument not
# resolving the question, never as the cut not happening.
TOL = 0.15
# Where a document names a position but prints no FTE -- which is most of the FY2026
# approved list -- there is no stated magnitude to test against, so the test is whether
# the instrument moved at all, by at least this much.
UNSTATED_MOVE = 0.5

# THE OPERATIVE LIST FOR EACH CYCLE: the one that was actually adopted or voted, as
# against the drafts that preceded it. The register publishes every list; the OUTCOME
# section tests only these, because testing a withdrawn draft against the following year
# would report as a failed cut something the district itself withdrew.
#
# FY2025 is the case that makes this necessary. The School Committee published two lists
# before the May 2024 ballot -- cuts without an override and cuts with one -- and the
# override PASSED, so the operative list is the shorter one.
OPERATIVE = {
    2020: ('2019-04-03', None),
    2021: ('2020-01-22', None),
    2025: ('2024-04', 'the override passing'),
    2026: ('2025-03-12', None),
    2027: ('2026-03-23', None),
}

# THE THREE CASES THE CONCLUSIONS NAME. Each is re-derived from the register on every run
# and this refuses to write if one stops reproducing, because a conclusion naming a case
# that the data no longer contains is prose that ships.
FY20_WITHDRAWN = [
    # (school, a fragment of the position as the March list printed it)
    ('primary', '0.5 FTE Librarian'),
    ('high', 'Foreign Language Teacher'),
    ('high', 'Proposed Athletic Trainer'),
]
# The FY25 pairing between the two lists. OURS -- the two documents use different words
# for the same posts -- and published in the payload as ours, with both strings quoted so
# a reader can check the pairing rather than take it.
FY25_PAIRS = [
    ('Instructional Coach (district)', 'Instructional Coach Districtwide'),
    ('Intervention Teacher (LHS)', 'Intervention Teacher LHS'),
    ('Classroom Teacher (LMS-grade 8)', 'Classroom Teacher LMS'),
    ('Classroom Teacher (LHS-history)', 'Humanities Teacher LHS'),
    ('Guidance Counselor (LMS)', 'Counselor LMS'),
    ('Classroom Teacher (THES-grade 5)', 'Classroom Teacher THES'),
    ('Wilson Reading Teacher (THES)', 'Wilson Reading Teacher THES'),
    ('Social Worker (PS-second SW position)', 'Social Worker PS'),
    ('PE Teacher (PS/THES)', 'PE Teacher PS/THES'),
]
FY25_UNPAIRED = 'Guidance Counselor (LMS/LHS)'

QUOTES = [
    dict(key='layoffs', board='school-committee', date='2025-05-07', kind='minutes',
         doc='7207',
         quote='June 30th we have a significant number of staff being laid off, we are '
               'going to pay out unemployment, and they are going to hopefully and very '
               'likely end up finding employment in other districts.',
         why='Said seven weeks after the School Committee approved the 39-position FY26 '
             'list. It is the clearest statement in the meeting record that the FY26 list '
             'was carried out; it names no post and no number, so it corroborates the '
             'direction and not any row.'),
    dict(key='restore-ms-sports', board='school-committee', date='2026-06-24',
         kind='minutes', doc='7869',
         quote='commitment to work with the athletic directors, coaches, and schedulers '
               'to restore middle school athletics for the upcoming year',
         why='Middle school sports were cut in the FY27 Core scenario at $14,415. Three '
             'months after the budget was voted, restoring them is being asked for in '
             'public. This is what the gap between a list and an outcome sounds like from '
             'inside the room.'),
    dict(key='restore-jazz-band', board='school-committee', date='2026-06-24',
         kind='minutes', doc='7869',
         quote='If there is anything we can do to help restore the 6th grade Jazz band, '
               'please let us know.',
         why='The FY27 balanced budget removed 0.2 of a music teacher at Turkey Hill and '
             'the district’s own slide says Grade 5 band instruction will be eliminated. '
             'A resident is asking for a band back in the same cycle.'),
    dict(key='retirement', board='school-committee', date='2025-06-04', kind='minutes',
         doc='7251',
         quote='Ms. Peggy Proctor is a World Language teacher working with grades 8 '
               'through 12, we thank her for her 26 years of service.',
         why='The FY26 approved list cut an LMHS World Language Teacher, and the state’s '
             'foreign language FTE falls by exactly 1.0 the following October. A '
             'retirement announced in the same month fits that fall as well as a layoff '
             'does, and nothing in the record separates them. Rule 7.'),
    dict(key='staffing-dispute', board='finance-committee', date='2026-01-27',
         kind='minutes', doc='7619',
         quote='really irritates me when we say things like we\'re cutting staff when '
               'the data shows that staffing has gone up almost every year in the last 10 '
               'years.',
         why='The Finance Committee chair, on the contested fact this whole register '
             'sits inside. The reply in the same paragraph is that FY26 included '
             'significant layoffs and the chart did not show them. Both are claims about '
             'measurement, which is what this page is for.'),
]

SEARCHED = ['laid off', 'layoff', 'restore', 'attrition', 'rehire',
            'reduction in force', 'middle school athletics', 'world language']

GAP_KEYS = [
    ('people', 'Whether a position the district announced it would cut was removed'),
    ('people', 'Whether an announced cut was reversed by a hire during the school year'),
    ('money_out', 'What each announced school position cut was worth'),
]


def fail(msg):
    sys.exit('REFUSING TO WRITE — %s' % msg)


def subject_of(position):
    low = position.lower()
    for name, pat in SUBJECT:
        if re.search(pat, low):
            return name
    return None


def build():
    if not os.path.exists(DB):
        fail('sources/data/lunenburg.db is not here — run scripts/build_db.py')
    cx = sqlite3.connect('file:%s?mode=ro' % DB, uri=True)
    cx.row_factory = sqlite3.Row

    have = cx.execute("SELECT name FROM sqlite_master WHERE type='table' "
                      "AND name='stated_cuts'").fetchone()
    if have is None:
        fail('`stated_cuts` is not in the database. Run '
             'scripts/extract_stated_cuts.py and then scripts/build_db.py — this page is '
             'the register and without it there is nothing to render.')
    rows = [dict(r) for r in cx.execute('SELECT * FROM stated_cuts')]
    if not rows:
        fail('`stated_cuts` is empty')
    for r in rows:
        r['fy'] = int(r['fy'])
        r['page'] = int(r['page'])
        r['fte'] = float(r['fte']) if r['fte'] else None
        r['amount'] = float(r['amount']) if r['amount'] else None

    cycles_fy = sorted({r['fy'] for r in rows})
    missing = [fy for fy in OPERATIVE if fy not in cycles_fy]
    if missing:
        fail('the register carries no rows for FY%s, and the operative list for that '
             'cycle is what the outcome section is computed from'
             % ', FY'.join(str(m) for m in missing))

    # ---------------------------------------------------------------- the instrument
    tbl = cx.execute("SELECT name FROM sqlite_master WHERE type='table' "
                     "AND name='dese_teacher_subject'").fetchone()
    if tbl is None:
        fail('dese_teacher_subject is not in the database — layer two of this page is the '
             "state's own teacher counts and without them the page is one layer")
    series = collections.defaultdict(dict)
    for r in cx.execute(
            "SELECT fy, org_name, org_level, subject, teacher_fte FROM dese_teacher_subject "
            "WHERE district LIKE 'Lunenburg%'"):
        series[(r['org_name'], r['subject'])][r['fy']] = r['teacher_fte']
    schools = {o for (o, _s) in series} & {n for v in ORG.values() if v for n in v}
    if len(schools) < 4:
        fail('DESE publishes school-level teacher FTE for only %d of the Lunenburg '
             'schools this register names — the join matched almost nothing, which looks '
             'exactly like the state publishing nothing' % len(schools))
    dese_years = sorted({fy for v in series.values() for fy in v})
    dese_last = dese_years[-1]

    def fte_at(orgs, subject, fy):
        """The instrument's reading, or None where the state has not published the year.

        Summed across orgs where the district named a post shared between two buildings.
        A missing org in a published year is a real zero for that org -- DESE prints a row
        only where there is FTE to print -- and is treated as such; a missing YEAR is not,
        and returns None so the row is reported as not yet measurable."""
        if fy not in dese_years:
            return None
        tot, seen = 0.0, False
        for o in orgs:
            v = series.get((o, subject), {})
            if fy in v:
                tot += v[fy]
                seen = True
            elif (o, subject) in series:
                seen = True           # the pair exists, this year prints nothing: a zero
        return round(tot, 4) if seen else None

    # ---------------------------------------------------------------- test one row
    def test(r):
        """What an instrument shows for one stated reduction, and the reason where none can.

        Returns the verdict, the instrument, its two readings and the change. The verdict
        vocabulary is deliberately three-valued and the third one is the honest majority
        answer, not a failure."""
        pos = r['position']
        low = pos.lower()
        orgs = ORG.get(r['school'])
        if r['direction'] != 'reduction':
            return dict(verdict='not a reduction', instrument='', reason='')
        if r['fy'] > dese_last:
            return dict(verdict='not yet measurable', instrument='',
                        reason='the state has not published a teacher count for FY%d yet; '
                               'the school year this budget pays for is the one now '
                               'running' % r['fy'])
        if re.search(UNMEASURED, low):
            return dict(verdict='cannot see at this grain', instrument='',
                        reason='no published series counts this job by school. DESE '
                               'publishes teacher FTE; its educator headcount, which does '
                               'carry paraprofessionals and administrators, exists for '
                               'Lunenburg in FY2021–FY2023 only')
        subject = subject_of(pos)
        if subject is None and re.search(CLASSROOM, low):
            subject = 'All Teachers'
        if subject is None:
            return dict(verdict='cannot see at this grain', instrument='',
                        reason='the position does not name a subject the state reports, '
                               'and this register assigns no subject it cannot read off '
                               'the title')
        if orgs is None:
            orgs = [DISTRICT_ORG]
            label = 'the district'
        elif not orgs:
            return dict(verdict='cannot see at this grain', instrument='',
                        reason='the document names no school, and the state publishes '
                               'this series per school')
        else:
            label = ' + '.join(orgs)
        before = fte_at(orgs, subject, r['fy'] - 1)
        after = fte_at(orgs, subject, r['fy'])
        inst = 'DESE teacher FTE, %s, %s' % (subject, label)
        if before is None or after is None:
            return dict(verdict='cannot see at this grain', instrument=inst,
                        reason='the state publishes no %s row for %s in one of the two '
                               'years' % (subject, label))
        change = round(after - before, 4)
        stated = r['fte']
        # HOW FAR THE INSTRUMENT HAS TO FALL. Where the document states an FTE, the fall
        # must reach that figure less the tolerance -- AND must clear the tolerance in its
        # own right, because DESE prints FTE to one decimal and a movement of 0.1 is the
        # resolution of the instrument rather than a reading from it. Without the second
        # half a stated cut of 0.2 would be confirmed by a fall of 0.05, which is nothing.
        floor = -max(stated - TOL, TOL) if stated else -UNSTATED_MOVE
        if change <= floor:
            verdict = 'the instrument moved with it'
        elif change >= TOL:
            verdict = 'the instrument moved the other way'
        else:
            verdict = 'the instrument does not resolve it'
        return dict(verdict=verdict, instrument=inst, subject=subject,
                    before=before, after=after, change=change,
                    before_fy=r['fy'] - 1, after_fy=r['fy'],
                    reason='')

    for r in rows:
        r.update(test(r))

    # ---------------------------------------------------------------- the cycles
    cycles = []
    for fy in cycles_fy:
        f = [r for r in rows if r['fy'] == fy]
        docs = []
        for date in sorted({r['doc_date'] for r in f}):
            d = [r for r in f if r['doc_date'] == date]
            docs.append(dict(
                doc_date=date, doc_title=d[0]['doc_title'], stage=d[0]['stage'],
                doc_text=d[0]['doc_text'], doc_pdf=d[0]['doc_pdf'],
                sha256=d[0]['sha256'],
                rows=len(d),
                reductions=sum(1 for x in d if x['direction'] == 'reduction'),
                restorations=sum(1 for x in d if x['direction'] in
                                 ('restoration', 'addition')),
                with_amount=sum(1 for x in d if x['amount'] is not None),
                with_fte=sum(1 for x in d if x['fte'] is not None),
                with_consequence=sum(1 for x in d if x['consequence'])))
        op_date, op_cond = OPERATIVE[fy]
        cycles.append(dict(fy=fy, documents=docs, n_documents=len(docs),
                           rows=len(f), operative_date=op_date,
                           operative_conditional=op_cond or ''))

    # ---------------------------------------------------------------- the operative set
    for r in rows:
        op_date, op_cond = OPERATIVE[r['fy']]
        r['operative'] = bool(
            r['doc_date'] == op_date
            and (op_cond is None or r['conditional_on'] == op_cond))
    operative = [r for r in rows if r['operative'] and r['direction'] == 'reduction']
    for fy in OPERATIVE:
        if not [r for r in operative if r['fy'] == fy]:
            fail('the operative list for FY%d is empty. OPERATIVE names the document '
                 'that was adopted for each cycle and one of them no longer matches any '
                 'row, so that whole cycle would vanish from the outcome counts.' % fy)

    verdicts = collections.Counter(r['verdict'] for r in operative)
    measurable = [r for r in operative if r['verdict'] != 'not yet measurable']
    seen_by = [r for r in measurable if r['verdict'] == 'the instrument moved with it']
    other_way = [r for r in measurable
                 if r['verdict'] == 'the instrument moved the other way']
    unresolved = [r for r in measurable
                  if r['verdict'] == 'the instrument does not resolve it']
    blind = [r for r in measurable if r['verdict'] == 'cannot see at this grain']
    if not seen_by or not blind:
        fail('the outcome pass produced no row in one of its two largest categories — '
             '%d confirmed, %d unmeasurable. A classifier that puts everything in one '
             'bucket is broken, not clean.' % (len(seen_by), len(blind)))
    tested = seen_by + other_way + unresolved

    # ---------------------------------------------------------------- case 1: FY2020
    march = [r for r in rows if r['doc_date'] == '2019-03-06'
             and r['direction'] == 'reduction' and r['school'] != 'district']
    april = [r for r in rows if r['doc_date'] == '2019-04-03'
             and r['direction'] == 'reduction']
    memo_restored = [r for r in rows if r['doc_date'] == '2019-03-29'
                     and r['direction'] == 'restoration']
    if len(memo_restored) != 2:
        fail('the 29 March 2019 memo no longer carries two restorations — a conclusion on '
             'this page says the district named two positions for restoration three weeks '
             'after listing them as cuts')
    withdrawn = []
    for school, frag in FY20_WITHDRAWN:
        src = [r for r in march if r['school'] == school and frag in r['position']]
        if len(src) != 1:
            fail('the FY2020 March list no longer carries exactly one %r at %s — the '
                 'withdrawal case names it' % (frag, school))
        # It counts as withdrawn only if nothing on the April list is the same post.
        still = [r for r in april
                 if r['school'] == school
                 and any(w in r['position'].lower() for w in _keywords(frag))]
        if still:
            fail('%r at %s is on the April list after all (%r) — the withdrawal case is '
                 'no longer what the documents say'
                 % (frag, school, [r['position'] for r in still]))
        withdrawn.append(dict(school=school, printed=src[0]['printed'],
                              position=src[0]['position'],
                              consequence=src[0]['consequence'], fte=src[0]['fte'],
                              page=src[0]['page'], doc_text=src[0]['doc_text']))
    if len(march) != 8:
        fail('the FY2020 March list names %d positions at a school, not 8 — the '
             'withdrawal case is stated as three of eight' % len(march))

    # What the instruments show for the two the March list named and the April list did
    # not, plus the one it did.
    # THE THREE DATES, AND THE COUNT OF SCHOOLS, DERIVED. The page names them in prose and
    # rule 2 covers a date in a sentence exactly as it covers a figure: an extract that
    # re-dated a document would leave the page confidently wrong.
    fy20 = dict(
        march_date='2019-03-06', memo_date='2019-03-29', final_date='2019-04-03',
        march_schools=len({r['school'] for r in march}),
        weeks_between=round((__import__('datetime').date(2019, 4, 3)
                             - __import__('datetime').date(2019, 3, 6)).days / 7),
        named_march=len(march), named_april=len(april), withdrawn=withdrawn,
        restored_by_memo=[dict(printed=r['printed'], school=r['school'],
                               page=r['page'], doc_text=r['doc_text'],
                               consequence=r['consequence']) for r in memo_restored],
        lhs_foreign=dict(
            subject='Foreign Language', org='Lunenburg High',
            before_fy=2019, after_fy=2020,
            before=fte_at(['Lunenburg High'], 'Foreign Language', 2019),
            after=fte_at(['Lunenburg High'], 'Foreign Language', 2020)),
        lms_foreign=dict(
            subject='Foreign Language', org='Lunenburg Middle School',
            before_fy=2019, after_fy=2020,
            before=fte_at(['Lunenburg Middle School'], 'Foreign Language', 2019),
            after=fte_at(['Lunenburg Middle School'], 'Foreign Language', 2020)),
    )
    for key in ('march_date', 'memo_date', 'final_date'):
        if not [r for r in rows if r['doc_date'] == fy20[key]]:
            fail('the FY2020 case names a document dated %s and the register has no rows '
                 'from it' % fy20[key])
    for half in ('lhs_foreign', 'lms_foreign'):
        v = fy20[half]
        if v['before'] is None or v['after'] is None:
            fail('DESE publishes no foreign language FTE for %s in FY2019 or FY2020, and '
                 'the FY2020 case rests on that pair' % v['org'])
        v['change'] = round(v['after'] - v['before'], 4)
    if fy20['lms_foreign']['change'] >= -0.5:
        fail('the middle school foreign language FTE no longer falls between FY2019 and '
             'FY2020 — the FY2020 case says the cut that survived is visible and the one '
             'withdrawn is not')
    if fy20['lhs_foreign']['change'] <= -0.5:
        fail('the high school foreign language FTE now falls between FY2019 and FY2020 — '
             'the FY2020 case says the withdrawn cut does not show')

    # The Primary librarian, in the district's own budget book. A second instrument, and
    # a weaker one: this is the district restating its own figures rather than a third
    # party counting.
    lib = {r['fy']: r['value'] for r in cx.execute(
        "SELECT fy, value FROM budget_figure WHERE label='P.S. Librarian' "
        "AND stage='restated' ORDER BY fy")}
    if not lib:
        fail("budget_figure carries no restated `P.S. Librarian` line — the FY2020 case "
             'sets the district’s own book beside the state’s teacher count')
    fy20['primary_librarian'] = dict(
        label='P.S. Librarian', stage='restated',
        points=[dict(fy=fy, value=round(v, 2)) for fy, v in sorted(lib.items())],
        first_funded_fy=min((fy for fy, v in lib.items() if v > 0), default=None))
    if fy20['primary_librarian']['first_funded_fy'] != 2020:
        fail('the district’s restated `P.S. Librarian` line is no longer first funded in '
             'FY2020 — the FY2020 case says the line the withdrawn cut named appears in '
             'the book in the year it was withdrawn')

    # ---------------------------------------------------------------- case 2: FY2025
    esser = [r for r in rows if r['block'].startswith('Positions CUT in the FY25')]
    with_ovr = [r for r in rows if r['conditional_on'] == 'the override passing']
    without = [r for r in rows if r['conditional_on'] == 'the override failing']
    # The last row of the longer list is not a position -- `Expense lines including
    # supplies, instructional tools etc` -- and counting it as one would put a
    # thirteen-position difference at fourteen.
    not_a_post = [r for r in without if r['position'].startswith('Expense lines')]
    if len(not_a_post) != 1:
        fail('the cuts-without-override list no longer carries exactly one non-position '
             'row; the count of positions on it depends on excluding it')
    without = [r for r in without if r not in not_a_post]
    if not esser or not with_ovr or not without:
        fail('one of the three FY2025 lists is empty — the override case compares all '
             'three')
    esser_pos = {r['position']: r for r in esser}
    with_pos = {r['position']: r for r in with_ovr}
    pairs = []
    for a, b in FY25_PAIRS:
        if a not in esser_pos:
            fail('the FY25 ESSER cut list no longer prints %r' % a)
        if b not in with_pos:
            fail('the FY25 cuts-with-override list no longer prints %r' % b)
        pairs.append(dict(esser=a, with_override=b,
                          esser_page=esser_pos[a]['page'],
                          override_page=with_pos[b]['page']))
    if FY25_UNPAIRED not in esser_pos:
        fail('the FY25 ESSER cut list no longer prints %r, which is the one position on '
             'it that the override statement does not carry over' % FY25_UNPAIRED)
    if len(pairs) != len(with_ovr):
        fail('the cuts-with-override list has %d rows and %d of them pair to the ESSER '
             'list — the conclusion says every one of them does'
             % (len(with_ovr), len(pairs)))
    # RECONCILED TO THE DOCUMENT'S OWN PROSE, which is rule 13's requirement of any
    # extract: the override statement states in a sentence how many posts each budget cuts
    # and how many the override buys back, and 19 minus 10 has to equal the shorter list.
    stmt = re.sub(r'\s+', ' ', open(os.path.join(
        ROOT, 'sources', with_ovr[0]['doc_text']), encoding='utf-8',
        errors='replace').read())
    for phrase in ('includes cutting 19 full time positions and 7 part time positions',
                   'We would retain 10 of the full time positions eliminated in the '
                   '4.47% budget and all of the part time positions'):
        if phrase not in stmt:
            fail('the override statement no longer says %r — the two lists are '
                 'reconciled to that sentence rather than merely counted' % phrase[:60])
    if 19 - 10 != len(with_ovr):
        fail('the override statement says 19 full-time posts cut and 10 retained, which '
             'is %d, and the cuts-with-override list has %d rows. The document no longer '
             'agrees with itself and this register will not publish either figure.'
             % (19 - 10, len(with_ovr)))

    ballot = cx.execute(
        "SELECT date, yes, no, result, purpose FROM ballot_questions "
        "WHERE date='2024-05-18'").fetchone()
    if ballot is None or ballot['result'] != 'PASSED':
        fail('the May 2024 override is not in `ballot_questions` as PASSED — the FY2025 '
             'case turns on which of the two published lists became operative')
    fy25 = dict(
        without=len(without), with_override=len(with_ovr),
        stated_full_time_cut=19, stated_full_time_retained=10,
        reconciles='the statement’s own sentence — 19 full-time posts cut, 10 retained — '
                   'leaves 9, which is the length of the shorter list',
        excluded_not_a_post=not_a_post[0]['printed'],
        saved=len(without) - len(with_ovr),
        esser=len(esser), paired=len(pairs), pairs=pairs, unpaired=FY25_UNPAIRED,
        ballot=dict(date=ballot['date'], yes=int(ballot['yes']), no=int(ballot['no']),
                    result=ballot['result'], purpose=ballot['purpose']),
        without_rows=[dict(printed=r['printed'], school=r['school'], page=r['page'])
                      for r in without],
        with_rows=[dict(printed=r['printed'], school=r['school'], page=r['page'],
                        verdict=r['verdict'], instrument=r.get('instrument', ''),
                        reason=r.get('reason', '')) for r in with_ovr],
    )

    # ---------------------------------------------------------------- case 3: FY2026
    wl = [r for r in rows if r['fy'] == 2026 and 'World Language' in r['position']]
    if len(wl) != 1:
        fail('the FY2026 approved list no longer carries exactly one World Language '
             'Teacher row — a conclusion names it')
    fy26 = dict(
        row=dict(printed=wl[0]['printed'], school=wl[0]['school'],
                 page=wl[0]['page'], doc_text=wl[0]['doc_text'],
                 verdict=wl[0]['verdict'], instrument=wl[0].get('instrument', ''),
                 before=wl[0].get('before'), after=wl[0].get('after'),
                 change=wl[0].get('change')),
        approved=len([r for r in rows if r['fy'] == 2026]),
        # The district's whole teacher count, either side, so the reader can see that the
        # subject fell inside a year the total also fell.
        district=dict(
            before_fy=2025, after_fy=2026,
            before=fte_at([DISTRICT_ORG], 'All Teachers', 2025),
            after=fte_at([DISTRICT_ORG], 'All Teachers', 2026)),
        # And the one that went the other way, because publishing only the agreeing case
        # would be choosing the evidence.
        other_way=[dict(printed=r['printed'], school=r['school'],
                        instrument=r.get('instrument', ''), before=r.get('before'),
                        after=r.get('after'), change=r.get('change'))
                   for r in operative if r['fy'] == 2026
                   and r['verdict'] == 'the instrument moved the other way'],
    )
    if fy26['row']['verdict'] != 'the instrument moved with it':
        fail('the FY2026 world language cut is no longer visible in the state’s foreign '
             'language FTE — a conclusion says it is the clearest case on the page')
    if not fy26['other_way']:
        fail('no FY2026 row now goes the other way — the page publishes that case beside '
             'the agreeing one on purpose, and a section that renders empty is worse than '
             'no section')
    d = fy26['district']
    if d['before'] is None or d['after'] is None:
        fail('DESE publishes no district teacher total for FY2025 or FY2026')
    d['change'] = round(d['after'] - d['before'], 4)

    # ---------------------------------------------------------------- categories
    def group(items, key):
        agg = collections.Counter()
        for it in items:
            agg[it[key]] += 1
        return [dict(name=k, n=v) for k, v in sorted(agg.items(), key=lambda kv: -kv[1])]

    categories = dict(
        by_school=group([r for r in rows if r['direction'] == 'reduction'], 'school'),
        by_verdict=[dict(name=k, n=v) for k, v in verdicts.most_common()],
        operative_by_school=group(operative, 'school'),
        by_direction=group(rows, 'direction'),
    )
    per_year = []
    for fy in cycles_fy:
        f = [r for r in rows if r['fy'] == fy]
        op = [r for r in operative if r['fy'] == fy]
        per_year.append(dict(
            fy=fy, rows=len(f), documents=len({r['doc_date'] for r in f}),
            reductions=sum(1 for r in f if r['direction'] == 'reduction'),
            restorations=sum(1 for r in f if r['direction'] in
                             ('restoration', 'addition')),
            operative=len(op),
            operative_fte=round(sum(r['fte'] for r in op if r['fte']), 2),
            operative_amount=round(sum(r['amount'] for r in op if r['amount']), 2),
            moved_with=sum(1 for r in op
                           if r['verdict'] == 'the instrument moved with it'),
            moved_other=sum(1 for r in op
                            if r['verdict'] == 'the instrument moved the other way'),
            unresolved=sum(1 for r in op
                           if r['verdict'] == 'the instrument does not resolve it'),
            blind=sum(1 for r in op if r['verdict'] == 'cannot see at this grain'),
            not_yet=sum(1 for r in op if r['verdict'] == 'not yet measurable')))

    said = read_quotes()
    hits = search_minutes()
    gaps = read_gaps(cx)

    documents = []
    for date in sorted({r['doc_date'] for r in rows}):
        d = [r for r in rows if r['doc_date'] == date][0]
        documents.append(dict(
            doc_date=date, fy=d['fy'], title=d['doc_title'], stage=d['stage'],
            path=d['doc_pdf'], text=d['doc_text'], sha256=d['sha256'],
            docs_url='/docs/' + d['doc_pdf'],
            rows=sum(1 for r in rows if r['doc_date'] == date)))

    # ---- the quantities the conclusions rest on ------------------------------------
    n_rows = len(rows)
    n_red = sum(1 for r in rows if r['direction'] == 'reduction')
    n_docs = len(documents)
    n_cycles = len(cycles_fy)
    blind_share = 100.0 * len(blind) / len(measurable)
    agree_share = 100.0 * len(seen_by) / len(tested) if tested else 0.0
    fy26_wl = fy26['row']

    payload = dict(
        generated_by='scripts/build_cut_register.py',
        source='sources/data/lunenburg.db — stated_cuts, dese_teacher_subject, '
               'budget_figure (stage=restated), ballot_questions',
        about='What Lunenburg’s schools said in writing they were cutting, cycle by '
              'cycle, and what an instrument nobody in the argument produced shows '
              'afterwards.',
        grain='One row per reduction, restoration or addition NAMED in a district budget '
              'document, quoted at a page. A row is a CLAIM the district published, not '
              'an event. Layer two is DESE teacher FTE, one October snapshot a year, and '
              'the two are never added together.',
        span=dict(first_fy=cycles_fy[0], last_fy=cycles_fy[-1], cycles=n_cycles,
                  documents=n_docs, rows=n_rows,
                  instrument_first_fy=dese_years[0], instrument_last_fy=dese_last),
        definitions=dict(
            stated='a reduction or restoration NAMED in a district budget document. Rule '
                   '13a: a document somebody assembled to argue for a budget, however '
                   'official it looks, is `stated` and not evidence of an outcome',
            operative='the list from each cycle that was actually adopted or voted, as '
                      'against the drafts before it. FY2025’s is the shorter of the two '
                      'lists the School Committee published, because the override passed',
            instrument='DESE teacher FTE by school and subject, submitted through EPIMS '
                       'on 1 October and published by the state',
            moved_with='the instrument fell by at least the FTE the document stated, less '
                       'the tolerance; or, where the document stated no FTE, by at least '
                       '%.1f' % UNSTATED_MOVE,
            other_way='the instrument rose by more than the tolerance',
            unresolved='the instrument moved by less than the document stated — which is '
                       'not the same as the cut not happening',
            blind='no published series counts this job, by school, in these years',
            tolerance=TOL, unstated_move=UNSTATED_MOVE,
            subject_map=[dict(subject=s, pattern=p) for s, p in SUBJECT],
            unmeasured_pattern=UNMEASURED),
        documents=documents,
        cycles=cycles,
        per_year=per_year,
        categories=categories,
        rows=[{k: r[k] for k in (
            'fy', 'doc_date', 'doc_title', 'stage', 'block', 'direction',
            'conditional_on', 'printed', 'position', 'school', 'school_printed',
            'fte', 'amount', 'consequence', 'page', 'doc_text', 'doc_pdf', 'sha256',
            'basis', 'operative', 'verdict', 'instrument')
            } | {k: r.get(k) for k in ('subject', 'before', 'after', 'change',
                                       'before_fy', 'after_fy', 'reason')}
            for r in rows],
        totals=dict(
            rows=n_rows, reductions=n_red,
            restorations=sum(1 for r in rows if r['direction'] in
                             ('restoration', 'addition')),
            documents=n_docs, cycles=n_cycles,
            with_amount=sum(1 for r in rows if r['amount'] is not None),
            with_fte=sum(1 for r in rows if r['fte'] is not None),
            with_consequence=sum(1 for r in rows if r['consequence']),
            operative=len(operative),
            measurable=len(measurable),
            moved_with=len(seen_by), moved_other=len(other_way),
            unresolved=len(unresolved), blind=len(blind),
            not_yet=verdicts['not yet measurable'],
            blind_share=round(blind_share, 2),
            agree_share=round(agree_share, 2)),
        fy2020=fy20,
        fy2025=fy25,
        fy2026=fy26,
        said=said,
        searched=hits['terms'],
        minutes=hits['minutes'],
        gaps=gaps,
        not_established=[
            'That any position on any of these lists was or was not removed. The lists '
            'are what the district published; the state’s teacher counts are a separate '
            'measurement on a different definition, and where the two agree that is '
            'consistency rather than proof.',
            'That a cut which does not show was not made. A grant can pay for a post, a '
            'retirement can absorb a reduction — the district’s own FY25 slides say so '
            'twice — enrolment can move, and a later vote can restore a position in '
            'public, which is what the FY2020 record shows happening.',
            'That a cut which does show was made for the reason the list gives. Two '
            'things moving together is not one causing the other.',
            'Anything about a post cut in June and filled again in the autumn. The '
            'instrument is one day a year.',
            'What any of this cost. Only the FY2027 documents print a dollar figure '
            'beside a position, and a budget-line saving is net (rule 11) rather than '
            'what the post costs.',
        ],
        closes='The district’s own year-end position control report — filled posts by '
               'FTE, school and funding source, for each year — which the Business Office '
               'produces for payroll and does not publish.',
        conclusions=emit('cut-register', [
            conclusion(
                id='a-cut-list-is-a-draft',
                bearing='lever',
                claim='Positions on the FY2020 cut list that were gone from it four weeks later',
                so_what='A published cut list is a stage in an argument, not a decision the town has taken.',
                lede='In FY2020 the district published a list of %s positions it '
                     'recommended cutting and a final list, four weeks later, that did '
                     'not carry %s of them.'
                     % (C.num(fy20['named_march']), C.num(len(withdrawn))),
                detail='On %s the Superintendent recommended reductions at %s schools. '
                       'On %s, after the Town Manager raised the target, a memo '
                       'recommended that the extra money “be used to restore one foreign '
                       'language teacher position to LHS and a 0.5 librarian position to '
                       'the Primary School”. Both are absent from the budget presented '
                       'for adoption on %s, and the athletic trainer moved from the '
                       'reduced column to the new-positions column. The state’s teacher '
                       'counts agree with the withdrawal rather than the announcement: '
                       'high school foreign language FTE goes from %s to %s across that '
                       'year, while the middle school post — the one that stayed cut — '
                       'goes from %s to %s.'
                       % ('6 March 2019', C.num(fy20['march_schools']),
                          '29 March 2019', '3 April 2019',
                          '%g' % fy20['lhs_foreign']['before'],
                          '%g' % fy20['lhs_foreign']['after'],
                          '%g' % fy20['lms_foreign']['before'],
                          '%g' % fy20['lms_foreign']['after']),
                figures={
                    'withdrawn': figure(len(withdrawn), C.num(len(withdrawn)),
                                        'of %s named positions' % C.num(fy20['named_march'])),
                    'named': figure(fy20['named_march'], C.num(fy20['named_march'])),
                    'lhs_before': figure(fy20['lhs_foreign']['before'],
                                         '%g' % fy20['lhs_foreign']['before']),
                    'lhs_after': figure(fy20['lhs_foreign']['after'],
                                        '%g' % fy20['lhs_foreign']['after']),
                    'lms_before': figure(fy20['lms_foreign']['before'],
                                         '%g' % fy20['lms_foreign']['before']),
                    'lms_after': figure(fy20['lms_foreign']['after'],
                                        '%g' % fy20['lms_foreign']['after']),
                    'schools': figure(fy20['march_schools'],
                                      C.num(fy20['march_schools'])),
                },
                figure='withdrawn',
                kind='measured',
                basis='Three district documents from one budget cycle — the 6 March 2019 '
                      'reduction list, the 29 March 2019 Superintendent’s memo and the '
                      '3 April 2019 budget hearing deck — every row quoted at its page, '
                      'set beside DESE’s teacher FTE by school and subject.',
                not_shown='That the other five were carried out. This compares two lists '
                          'the district published; it does not observe a single post. The '
                          'foreign language figures are DESE’s apportionment of teaching '
                          'time by subject, which moves when a timetable moves.',
                see=[('/school-staffing', 'the people the budget buys'),
                     ('/what-stopped-being-funded', 'lines that went to zero, and came back')],
                # DECLARED EXCEPTIONS, and each is a name rather than a derived figure:
                # three document dates, the FTE the district itself printed inside a
                # sentence it wrote, and a fiscal year. The generator refuses to write if
                # the register holds no rows from any of the three dates.
                allow=('6 March 2019', '29 March 2019', '3 April 2019', '0.5',
                       'FY2020'),
            ),
            conclusion(
                id='the-override-changed-which-cuts-happened',
                bearing='lever',
                claim='School positions the May 2024 override took off the cut list',
                so_what='The nine it did not save are the nine a federal grant had been paying for.',
                lede='Before the May 2024 ballot the School Committee published two cut '
                     'lists — %s positions without an override and %s with one — and the '
                     'override passed %s to %s.'
                     % (C.num(fy25['without']), C.num(fy25['with_override']),
                        C.num(fy25['ballot']['yes']), C.num(fy25['ballot']['no'])),
                detail='So the shorter list is the one that became operative, and %s '
                       'positions came off. Every one of the %s that stayed on it pairs '
                       'to a post the district’s own budget update lists as cut “due to '
                       'loss of ESSER” — the federal pandemic grant — and only one ESSER '
                       'post, a second guidance counsellor, was among those the override '
                       'saved. The pairing between the two documents’ wordings is ours '
                       'and both strings are published beside each other. What the town '
                       'voted for bought back the posts it was paying for itself; the '
                       'grant-funded ones ended either way.'
                       % (C.num(fy25['saved']), C.num(fy25['with_override'])),
                figures={
                    'saved': figure(fy25['saved'], C.num(fy25['saved']), 'positions'),
                    'without': figure(fy25['without'], C.num(fy25['without'])),
                    'with': figure(fy25['with_override'], C.num(fy25['with_override'])),
                    'yes': figure(fy25['ballot']['yes'], C.num(fy25['ballot']['yes'])),
                    'no': figure(fy25['ballot']['no'], C.num(fy25['ballot']['no'])),
                },
                figure='saved',
                kind='measured',
                basis='The School Committee’s own override statement, which prints both '
                      'lists on one page; the FY25 Superintendent’s Budget Update, page '
                      '43, which prints the positions cut for loss of ESSER; and the '
                      'election result as the FY2024 annual town report records it.',
                not_shown='That the thirteen were kept or that the nine went. Two '
                          'published lists and a ballot result establish which list was '
                          'operative and nothing about any individual post. The pairing '
                          'between the two documents is our reading of two different '
                          'wordings, printed here so it can be disagreed with.',
                see=[('/overrides', 'what this town does with an override'),
                     ('/when-grants-end', 'what happened when the federal money stopped')],
                allow=('May 2024', 'FY25', '43',),
            ),
            conclusion(
                id='most-announced-cuts-cannot-be-checked',
                bearing='sizes',
                claim='Adopted school cuts that no published series can see at all',
                so_what='The jobs the state counts are teachers. Most cut posts are not teachers.',
                lede='Of the %s reductions on the lists this town actually adopted and '
                     'that are old enough to check, %s name a job no published series '
                     'measures by school.'
                     % (C.num(len(measurable)), C.num(len(blind))),
                detail='Paraprofessionals, secretaries, custodians, guidance counsellors, '
                       'social workers, maintenance staff, tutors and BCBAs are most of '
                       'every list here, and the state publishes teacher FTE. Its '
                       'educator headcount does carry paraprofessionals and '
                       'administrators, and for Lunenburg it exists in FY2021, FY2022 and '
                       'FY2023 only — none of the years any list here would be tested in. '
                       'So the question a resident asks first, whether the cut happened, '
                       'is unanswerable for %s of the posts by anything anybody publishes.'
                       % C.pct(blind_share),
                figures={
                    'blind': figure(len(blind), C.num(len(blind)),
                                    'of %s adopted cuts' % C.num(len(measurable))),
                    'measurable': figure(len(measurable), C.num(len(measurable))),
                    'share': figure(blind_share, C.pct(blind_share)),
                },
                figure='blind',
                kind='measured',
                basis='The adopted list from each of the five cycles, tested against '
                      'DESE’s teacher FTE by school and subject; the jobs no series '
                      'counts are identified from the district’s own printed job title '
                      'and the rule is published in the payload.',
                not_shown='That those cuts did not happen. This is a statement about what '
                          'is published, not about what occurred, and it is the reason '
                          'three rows sit in the gap register with the document that '
                          'would close each.',
                see=[('/what-we-cannot-answer', 'the gaps, and what would close them'),
                     ('/school-staffing', 'the three quantities the archive does hold')],
                allow=('FY2021', 'FY2022', 'FY2023'),
            ),
            conclusion(
                id='half-of-what-can-be-checked-checks-out',
                bearing='sizes',
                claim='Adopted cuts the state’s teacher counts move with, of the ones it can see',
                so_what='Half. Two moved the other way and four by less than the document stated.',
                lede='Where a published series can see an adopted cut at all — %s of '
                     'them — the state’s teacher FTE moves with it in %s cases.'
                     % (C.num(len(tested)), C.num(len(seen_by))),
                detail='The clearest is the FY2026 world language teacher: the School '
                       'Committee approved cutting one, and the foreign language FTE '
                       'across the middle and high schools falls from %s to %s the '
                       'following October. %s went the other way, %s moved by less than '
                       'the document stated. A movement that agrees is consistency and '
                       'not proof — a retirement was announced in the same month as the '
                       'world language cut, and the record does not separate the two.'
                       % ('%g' % fy26_wl['before'], '%g' % fy26_wl['after'],
                          C.num(len(other_way)), C.num(len(unresolved))),
                figures={
                    'agree': figure(len(seen_by), C.num(len(seen_by)),
                                    'of %s the state can see' % C.num(len(tested))),
                    'tested': figure(len(tested), C.num(len(tested))),
                    'other': figure(len(other_way), C.num(len(other_way))),
                    'unresolved': figure(len(unresolved), C.num(len(unresolved))),
                    'wl_before': figure(fy26_wl['before'], '%g' % fy26_wl['before']),
                    'wl_after': figure(fy26_wl['after'], '%g' % fy26_wl['after']),
                },
                figure='agree',
                kind='measured',
                basis='The adopted list from each cycle, against DESE teacher FTE by '
                      'school and subject for the October after the budget took effect. '
                      'The tolerance, the subject mapping and the list of jobs no series '
                      'counts are all ours and all published in the payload.',
                not_shown='That the instrument saw the cut. DESE apportions FTE by '
                          'teaching assignment rather than by post, so a subject can fall '
                          'because one timetable changed and rise while a post in it is '
                          'removed — which is what the FY2026 high school mathematics '
                          'row does. And the count is one day a year, so a post filled '
                          'again in November is invisible.',
                see=[('/school-staffing', 'the FTE series this is read from'),
                     ('/what-we-cannot-answer', 'what this record cannot settle')],
                allow=('FY2026',),
            ),
        ]),
    )
    return payload


def _keywords(frag):
    """The distinguishing words of a printed position, lower-cased.

    Used only to ask whether a LATER list still names the same post. Stop words are
    dropped so `Proposed Athletic Trainer` still matches `Athletic Trainer`."""
    stop = {'the', 'a', 'of', 'and', 'proposed', 'fte', 'part', 'time', 'part-time'}
    return [w for w in re.findall(r'[a-z]+', frag.lower())
            if w not in stop and len(w) > 3]


def read_quotes():
    said = []
    for spec in QUOTES:
        rel = '%s/%s/%s-%s-%s.txt' % (MINUTES, spec['board'], spec['date'],
                                      spec['kind'], spec['doc'])
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            fail('%s is not here — a quote on this page is attributed to a document that '
                 'is not in the archive' % rel)
        text = re.sub(r'\s+', ' ',
                      open(path, encoding='utf-8', errors='replace').read())
        want = re.sub(r'\s+', ' ', spec['quote'])
        if want not in text:
            fail('the quote attributed to %s %s is no longer in %s — quote the source, '
                 'never your rendering of it' % (spec['board'], spec['date'], rel))
        said.append(dict(
            key=spec['key'], board=spec['board'].replace('-', ' ').title(),
            date=spec['date'], kind=spec['kind'], quote=spec['quote'], why=spec['why'],
            cite='/docs/' + rel.replace('sources/', ''),
            town='https://www.lunenburgma.gov/AgendaCenter/ViewFile/Minutes/_%s%s%s-%s'
                 % (spec['date'][5:7], spec['date'][8:10], spec['date'][:4],
                    spec['doc'])))
    return said


def search_minutes():
    idx = os.path.join(ROOT, 'sources/meetings/index.csv')
    if not os.path.exists(idx):
        fail('sources/meetings/index.csv is not here — this page states how many meeting '
             'documents were searched, and a search of nothing is not a search')
    rows = list(csv.DictReader(open(idx, encoding='utf-8')))
    readable, dates = [], []
    for r in rows:
        stem = os.path.splitext(r['path'])[0] if r['path'].strip() else ''
        txt = os.path.join(ROOT, MINUTES, stem + '.txt') if stem else ''
        if stem and os.path.exists(txt):
            readable.append(txt)
            if r.get('date'):
                dates.append(r['date'])
    if not readable:
        fail('no meeting document is readable — refusing to publish a count of what '
             'nobody said')
    bodies = [open(t, encoding='utf-8', errors='replace').read() for t in readable]
    terms = []
    for term in SEARCHED:
        pat = re.compile(re.escape(term), re.I)
        terms.append(dict(term=term, documents=sum(1 for b in bodies if pat.search(b))))
    return dict(terms=terms,
                minutes=dict(published=len(rows), held=len(rows),
                             searchable=len(readable),
                             unsearchable=len(rows) - len(readable),
                             image_scan=0,
                             searchable_share=round(len(readable) / len(rows), 4),
                             text_files_present=len(readable),
                             first_date=min(dates), last_date=max(dates)))


def read_gaps(cx):
    out = []
    for side, what in GAP_KEYS:
        r = cx.execute('SELECT side, what, why FROM money_gaps WHERE side=? AND what=?',
                       (side, what)).fetchone()
        if r is None:
            fail('money_gaps has no row (%s, %r). This page quotes the register by key; '
                 'add the row to sources/data/money-gaps.csv and rebuild the database '
                 'rather than typing the limit into the page.' % (side, what))
        why, _, closes = r['why'].partition('— closes:')
        out.append(dict(side=r['side'], what=r['what'],
                        why=why.strip().rstrip('·').strip(),
                        closes=closes.strip() or None))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    payload = json.dumps(build(), indent=1, sort_keys=True) + '\n'
    rel = os.path.relpath(OUT, ROOT)
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if have != payload:
            print('STALE — %s is not what the database now produces. '
                  'Run scripts/build_cut_register.py.' % rel)
            return 1
        print('ok — %s reproduces from the database' % rel)
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(payload)
    d = json.loads(payload)
    t = d['totals']
    print('wrote %s — %d stated changes in %d documents across %d cycles; %d adopted '
          'reductions, of which %d the state can see (%d move with it, %d the other way, '
          '%d unresolved), %d it cannot see at all and %d not yet measurable'
          % (rel, t['rows'], t['documents'], t['cycles'], t['operative'],
             t['moved_with'] + t['moved_other'] + t['unresolved'],
             t['moved_with'], t['moved_other'], t['unresolved'], t['blind'],
             t['not_yet']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
