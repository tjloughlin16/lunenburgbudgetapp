#!/usr/bin/env python3
"""What it would cost Lunenburg if students transferred out under school choice.

    python3 scripts/build_if_students_leave.py            # write it
    python3 scripts/build_if_students_leave.py --check    # fail if it is stale

WHERE THIS CAME FROM. A member of the Select Board put a scenario to an AI assistant and
sent the result to this site: model a 40% school choice transfer rate of athletes, who are
45% of the high school population, and model the impact on Chapter 70 funding and on
school choice funds. The reasoning was sound on the documents that are easy to find. This
page runs the same scenario against everything the archive holds, and the two places it
lands differently are the interesting part -- neither of them is an error in the scenario.

RULE 8. This is not a correction of anybody. It is the same question with more of the
data, and the page says so. The scenario's central claim -- that students leaving costs
the town money -- is not disputed here and is not weakened by anything below.

WHAT IS MEASURED, WHAT IS ASSUMED, AND THE LINE BETWEEN THEM (rules 3, 7 and 13):

  MEASURED, each from one document, quoted by coordinate:
    * High school enrolment, 433, and the four grade counts that sum to it -- the FY2025
      annual town report, printed page 89. The table's own column headings are read off
      the page rather than inferred, which matters because `column_meaning` in
      `report_enrollment_mcas` is EMPTY for this dataset and `v1` is an ordinal. The
      report calls the column `Lunenburg Resident Students`.
    * High school athletic participations, 533 in FY2026 -- the district's athletics
      workbook, via /data/athletics.json.
    * The Chapter 70 calculation -- DESE's FY27 district summary, row 168, five cells.
    * School choice money COMING IN -- the town's own special revenue schedule, thirteen
      annual town reports, and the FY2027 Town Meeting booklet's cherry sheet line.

  ASSUMED, and every one of them is a dial the reader moves:
    * that 45% of high school students are athletes;
    * that 40% of them would transfer;
    * that sending tuition is $5,000 a student. This is the statutory base rate under
      M.G.L. c.76 s.12B and it is HIGHER for special education. THIS ARCHIVE HOLDS NO
      DOCUMENT STATING IT. It is published here as an assumption, not a measurement.
    * how much Chapter 70 aid actually falls;
    * how much cost the district could actually avoid.

THE ONE CORRECTION THE FULL DATA OFFERS, and it is arithmetic rather than judgement.
DESE's own row for Lunenburg says Chapter 70 aid is $395,366 MORE than foundation budget
minus required local contribution. Aid is therefore not currently being set by that
subtraction, so multiplying foundation dollars per pupil by students lost gives an upper
bound on the FOUNDATION effect and not a prediction of the AID loss. 292 of the 319
operating districts in the same sheet are in the same position. The mechanism that
produces it -- minimum aid and hold-harmless under c.70 -- is named on the page as the
statutory provision it is, and this archive holds no document applying it to Lunenburg.
That is registered as a gap.

THE FINDING THE PAGE LEADS WITH is neither of those. It is the asymmetry: the money
leaves at once and in full, and the cost does not, because 78 students spread over four
grades is about twenty a grade. It holds at every setting of every dial, which is why it
is the headline and the dollar figures are not.

WHAT IT REFUSES TO WRITE ON. Eleven joins or assertions that could silently match nothing:
  1. the FY2025 annual report's enrolment table not being on the page, or its column
     headings not reading as the report prints them;
  2. the four high school grade counts not summing to the printed High School Total;
  3. the school totals not summing to the printed All Schools Total;
  4. `report_enrollment_mcas` disagreeing with the page -- two routes to one figure;
  5. no FY2026 high school participation figure in athletics.json;
  6. the DESE workbook's headings, or its Lunenburg row, disagreeing with model/taxbase;
  7. F+G != H in the DESE row -- the identity the sheet states about itself;
  8. the school choice fund series failing its own row arithmetic, or failing to chain
     from one annual report to the next;
  9. the FY2027 Town Meeting booklet's School Choice Receiving line not being on the line
     this script reads it from;
 10. a minutes quote no longer present verbatim in the file it is attributed to;
 11. a `money_gaps` row quoted by key having been renamed out from under the page.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'model'))

DB = os.path.join(ROOT, 'sources/data/lunenburg.db')
OUT = os.path.join(ROOT, 'fy28/public/data/if-students-leave.json')
REPORTS = os.path.join(ROOT, 'fy28/public/data/reports.json')
ATHLETICS = os.path.join(ROOT, 'fy28/public/data/athletics.json')

CH70_XLSX = 'sources/budget-workbooks/ch70-fy27-summary.xlsx'

# THE FOUR DESE WORKBOOKS, BY FILENAME AND NEVER BY FOLDER.
#
# `sources/` is keyed on how a document REACHED us and documents get re-filed on purpose,
# so a literal folder in a script is a latent break with a date on it — it has already
# broken eight scripts in this repository. These are located by basename across every
# `sources/` subtree, and the resolved path plus a sha256 goes into the payload, so a page
# citing one of them names the bytes rather than the shelf.
#
# All four are DESE's own published district files. `.xlsx` under sources/ is gitignored
# and lives in the R2 archive, exactly like the FY27 Chapter 70 summary beside them.
DESE = {
    'sending': dict(
        file='dese-residents-sending.xlsx', sheet='Data', dataset='vxt3-k35x',
        title='Enrollment of town residents by district — where the children of a town '
              'actually go to school'),
    'receiving': dict(
        file='dese-enrollment-receiving.xlsx', sheet='Data', dataset='8xyg-59b2',
        title='Enrollment of a district by town of residence — where a district’s '
              'children come from'),
    'profile': dict(
        file='dese-ch70-district-profile.xlsx', sheet='DataC70', dataset=None,
        title='Chapter 70 District Profile — foundation enrolment, foundation budget, '
              'required local contribution and aid, every district, FY1993 onward'),
    'factors': dict(
        file='dese-ch70-key-factors.xlsx', sheet='dataAid', dataset=None,
        title='Chapter 70 Trends in Aid and Local Contribution — the AID CALCULATION '
              'broken into its named components'),
}

LEA_CODE = '01620000'      # Lunenburg, in DESE's district files
LEA_NUM = 162              # Lunenburg, in the Chapter 70 workbooks' own LEA numbering
PROFILE_ORG4 = '0162'
CHOICE_REASON = 'School Choice Program'
CHARTER_REASON = 'Charter School'
MEMBER_REASON = 'Resident/Member'
LATEST_SY = 2026           # asserted to be present rather than assumed
REPORT_TXT = 'sources/town-annual-reports/text/4130-fy-2025-annual-town-report.txt'
REPORT_PDF = '4130-fy-2025-annual-town-report.pdf'
BOOKLET = 'sources/town-budget/text/3765-town-meeting-booklet-including-warrant.txt'
MINUTES = 'sources/meetings/text'

TOWN = 'Lunenburg'
ENROL_FY = 2025            # the annual town report edition the enrolment comes from
ENROL_PAGE = '89'          # the printed page number, as the dataset records it
ATH_FY = 2026              # the athletics workbook year

# THE COLUMN HEADINGS, AS THE REPORT PRINTS THEM. `report_enrollment_mcas` stores this
# table as v1/v2/v3 with `column_meaning` EMPTY, and v1 is an ordinal rather than a column
# name (rule 13). The page itself names the columns, so they are read off the page and
# asserted before any figure is attributed to one of them. Get this wrong and the page
# says 433 resident students when the number is something else.
HEADINGS = ('Grade Level', 'Lunenburg Resident', 'Students', 'School Choice',
            'Students', 'Total')
HEADING_RE = re.compile(r'\s+'.join(re.escape(h) for h in HEADINGS))
HS_GRADES = ('9', '10', '11', '12')
SCHOOL_TOTALS = ('Primary Total', 'Elementary Total', 'Middle School Total',
                 'High School Total', 'Advanced Community')
# The label as it is PRINTED, where that differs from the label the dataset stores. The
# ACE row's name wraps over three lines on the page and the extract kept the first two
# words. Two labels for one row is exactly the sort of thing that makes a join match
# nothing, so both are written down rather than one being assumed to work for both.
PAGE_LABEL = {'Advanced Community': r'Advanced Community\s+Experience\s+Program\(ACE\)'}
HS_LABEL = 'High School Total'
ALL_LABEL = 'All Schools Total'

# THE SCENARIO AS IT WAS PUT TO THIS SITE. These are the DEFAULTS of the dials, not
# findings, and the page labels every one of them as an assumption.
DEFAULTS = dict(
    athlete_share=0.45,       # of the high school population
    transfer_rate=0.40,       # of those athletes
    tuition=5000.0,           # per student, per year
    # aid_per_pupil is NOT typed here. It is DERIVED from DESE's own aid components --
    # the minimum aid increment of the latest year divided by that year's foundation
    # enrolment -- and filled in by scenario(). Typing it would be rule 2's exact error on
    # the single most consequential number this page carries.
    avoidable_share=0.0,      # share of the per-pupil appropriation the district avoids
)

# WHY EACH DIAL OPENS WHERE IT DOES, and what would move it. Rendered on the page beside
# the control, because a default nobody explains is a finding nobody can argue with.
DIAL_BASIS = {
    'athlete_share': (
        'assumed',
        'The scenario as it was put to this site. Nothing published counts Lunenburg '
        'athletes as people rather than as participations, so this cannot be measured — '
        'but it can be bounded, and the bound is below.'),
    'transfer_rate': (
        'assumed',
        'The scenario as it was put to this site. Nobody has measured how many Lunenburg '
        'students choice out in any year, in either direction.'),
    'tuition': (
        'statute',
        'The base school choice tuition set by M.G.L. c.76 §12B. It is higher for special '
        'education placements, and THIS ARCHIVE HOLDS NO DOCUMENT STATING EITHER RATE. '
        'Treat it as a dial, not as a measurement.'),
    'aid_per_pupil': (
        'derived',
        'Opens on the minimum aid increment DESE’s own aid-component columns give for the '
        'latest year, divided by that year’s foundation enrolment — because in that year '
        'the minimum aid increment IS the whole of Lunenburg’s increase and the '
        'foundation aid increment is zero. Drag it to the foundation budget per pupil for '
        'the scenario as it was originally modelled; the distance between the two ends is '
        'the correction the full data offers.'),
    'avoidable_share': (
        'assumed',
        'Opens at zero because the students leave from across four grades, so no '
        'classroom closes on the arithmetic alone. Nothing published says at what '
        'enrolment a section is removed.'),
}

# WHAT THE TOWN SAID. Rule 15a: every one found with scripts/search_minutes.py, and every
# one asserted below to still be present in the document it is attributed to.
QUOTES = [
    dict(key='hemorrhage',
         board='school-committee', date='2025-03-12', doc='7098', kind='minutes',
         quote='She said to me that she was looking at choicing out if her private school '
               'choices didn’t come through. I think that\'s going to be the reality that '
               'we have if we\'re not able to offer our student choices they are going to '
               'hemorrhage out of the high school',
         who='Tim Santry, LMHS Principal',
         why='The mechanism the scenario models is not hypothetical to the people running '
             'the high school. The principal named it at a public meeting, in the same '
             'remarks that record 27 class offerings cut over two years. What the minutes '
             'establish is that this was SAID; they do not establish that any student '
             'left, and nothing published counts departures.'),
    dict(key='seats',
         board='finance-committee', date='2026-02-26', doc='7673', kind='minutes',
         quote='Dr. Jodi Fortuna stated that the School Committee did open 24 seats this '
               'year for school choice. She further states that only 5 students applied.',
         who='Superintendent Dr. Jodi Fortuna, to the Finance Committee',
         why='School choice runs both ways and Lunenburg is on the receiving side too. '
             'Seats offered are a decision; students arriving are not, and the two '
             'numbers here are five times apart.'),
    dict(key='uneven',
         board='finance-committee', date='2026-01-27', doc='7619', kind='minutes',
         quote='School Committee Chair Sculimbrene addressed the school choice revenue '
               'issue, noting that school choice demand is uneven across grade levels and '
               'that demand cannot simply be switched on.',
         who='School Committee Chair Sculimbrene',
         why='Choice traffic is not smooth across grades in either direction, which is '
             'the same reason a scenario spread evenly over four grades is a model rather '
             'than a forecast.'),
    dict(key='declined',
         board='finance-committee', date='2026-01-27', doc='7619', kind='minutes',
         quote='school choice enrollment revenue, which has declined from approximately '
               '$500,000 to $112,000 on the cherry sheet',
         who='a Finance Committee member',
         why='The only figure anybody in Lunenburg has publicly attached to school choice '
             'money, and it is about money coming IN. This archive holds no Cherry Sheet '
             'for any year, so this can be reported as SAID and cannot be checked against '
             'the document it names — which is a gap somebody in the room reached before '
             'we did.'),
    dict(key='highschoolonly',
         board='school-committee', date='2026-02-04', doc='7634', kind='minutes',
         quote='We are looking to only add school choice options to the high school.',
         who='School Committee',
         why='The high school is where the choice seats are, in both directions. The '
             'FY2025 annual town report counts 17 school choice students in the district '
             'and every one of them is in grades 9 to 12.'),
]

# The gap-register rows this page rests on, quoted BY KEY. A limit whose reason has been
# renamed out from under it renders as an empty box, so a missing key stops the build.
GAP_KEYS = [
    'What the children who leave the district cost, as against how many there are',
    'What Lunenburg pays in school choice sending tuition, and for how many children',
    'What Chapter 70 aid would actually do if enrolment fell',
    'What the foundation budget pays per pupil for each kind of child',
    'How much of a school budget stops being spent when a student leaves',
    'How many children play sports',
    'How many children Chapter 70 is actually paid for',
    'The Cherry Sheet itself — what the state told Lunenburg to expect, receipt by receipt',
]

RELATED = [
    ('fy27-and-the-override',
     'Where the FY27 revenue figures come from, including the state aid arithmetic this '
     'scenario runs against'),
    ('athletics',
     'The participation counts this scenario’s 45% is tested against, and why a '
     'participation is not a child'),
    ('connecting-the-budget',
     'Why no state aid dollar can be followed to anything it paid for — 0 of 222 accounts '
     'share an organisation code'),
    ('peer-districts',
     'What comparable districts actually cut, and in what order, when they had to'),
]

CENT = 0.005


def fail(msg):
    sys.exit(f'build_if_students_leave: {msg}')


def q(c, sql, *a):
    return [dict(r) for r in c.execute(sql, a)]


def norm(s):
    return re.sub(r'\s+', ' ', s).replace('’', "'").replace('‘', "'") \
             .replace('“', '"').replace('”', '"')


# ------------------------------------------------------------------ the children, counted

def enrolment(c):
    """The FY2025 annual town report's enrolment table, read TWO ways and reconciled.

    Route one is the printed page itself, where the columns are named. Route two is
    `report_enrollment_mcas`, where they are not -- `column_meaning` is empty for this
    dataset and `v1` means only *the first figure column of this page*. The dataset is
    `status='no check'`, because the page prints no total the extract can be tied to.
    So this function supplies the check the extract could not: the four high school
    grades sum to the printed High School Total, the five school totals sum to the
    printed All Schools Total, and residents plus school choice equals total on every
    row. Three identities the table states about itself.
    """
    path = os.path.join(ROOT, REPORT_TXT)
    if not os.path.exists(path):
        fail(f'{REPORT_TXT} is not on disk — run scripts/sync_archive.py --pull')
    text = open(path, encoding='utf-8', errors='replace').read()

    m = HEADING_RE.search(text)
    if not m:
        fail('the FY2025 annual town report no longer prints the enrolment table headings '
             'this page quotes — without them `v1` is an ordinal and nothing here may be '
             'called a count of resident students')
    # Captured BEFORE the row loop below, which rebinds `m`. It did, and this field
    # shipped a slice of the balance sheet two pages earlier.
    headings_printed = re.sub(r'\s+', ' ', text[m.start():m.end()]).strip()
    block = text[m.end():]
    block = block[:block.index('===PAGE')] if '===PAGE' in block else block[:2000]

    rows = {}
    for label in HS_GRADES + SCHOOL_TOTALS + (ALL_LABEL,):
        # ANCHORED AT A LINE START. Unanchored, the grade label `9` matched inside the
        # figures of the row above it — `389 0 389` — and produced a row that failed the
        # table's own identity. A label is a label only where the printed row begins.
        pat = (r'(?:^|\n)[ \t]*' + (PAGE_LABEL.get(label) or re.escape(label))
               + r'\s+(\d[\d,]*)\s+(\d[\d,]*)\s+(\d[\d,]*)')
        m = re.search(pat, block)
        if not m:
            fail(f'the row {label!r} is not on printed page {ENROL_PAGE} of the FY'
                 f'{ENROL_FY} annual town report in the shape this page reads it')
        rows[label] = tuple(int(x.replace(',', '')) for x in m.groups())

    # IDENTITY 1: residents + school choice = total, on every row the page prints.
    for label, (res, choice, total) in rows.items():
        if res + choice != total:
            fail(f'{label}: {res} + {choice} != {total} on the page — the column meanings '
                 'this page attributes are not the ones the table is using')
    # IDENTITY 2: the four high school grades sum to the printed High School Total.
    hs = rows[HS_LABEL]
    grades = [rows[g] for g in HS_GRADES]
    if sum(g[0] for g in grades) != hs[0]:
        fail(f'grades {HS_GRADES} sum to {sum(g[0] for g in grades)} residents against a '
             f'printed High School Total of {hs[0]} — the scenario’s denominator does not '
             'reconcile to its own page')
    # IDENTITY 3: the five school totals sum to the printed All Schools Total.
    allrow = rows[ALL_LABEL]
    parts = [rows[s] for s in SCHOOL_TOTALS]
    if sum(p[0] for p in parts) != allrow[0]:
        fail(f'the school totals sum to {sum(p[0] for p in parts)} residents against a '
             f'printed All Schools Total of {allrow[0]}')

    # ROUTE TWO: the dataset, which must agree with the page it was extracted from.
    ds = q(c, """SELECT label, v1, v2, v3, status, page FROM report_enrollment_mcas
                 WHERE fy = ? AND page = ? AND label IN (%s)"""
           % ','.join('?' * (len(SCHOOL_TOTALS) + 1)),
           ENROL_FY, ENROL_PAGE, *(SCHOOL_TOTALS + (ALL_LABEL,)))
    if not ds:
        fail('report_enrollment_mcas returned no rows for the FY2025 enrolment page — a '
             'join that matches nothing looks exactly like data that is absent')
    by_label = {r['label']: r for r in ds}
    for label in SCHOOL_TOTALS + (ALL_LABEL,):
        r = by_label.get(label)
        if r is None:
            fail(f'report_enrollment_mcas has no {label!r} row for FY{ENROL_FY} page '
                 f'{ENROL_PAGE} — the two routes to this table do not cover the same rows')
        got = (int(r['v1']), int(r['v2']), int(r['v3']))
        if got != rows[label]:
            fail(f'{label}: the page prints {rows[label]} and the dataset holds {got} — '
                 'two routes to the same printed row disagree')
    statuses = sorted({r['status'] for r in ds})
    if statuses != ['no check']:
        fail(f'the enrolment rows now carry statuses {statuses}; this page states '
             '"no check" in prose and that sentence is derived from here')

    return dict(
        fy=ENROL_FY, page=ENROL_PAGE, document=REPORT_PDF,
        headings=['Grade Level', 'Lunenburg Resident Students',
                  'School Choice Students', 'Total'],
        headings_raw=headings_printed,
        status=statuses[0],
        status_means='The extract carries no reconciliation because the page prints no '
                     'total it could be tied to. Nothing here may be aggregated with a '
                     '`checked` row without saying so.',
        checks=[
            'residents + school choice students = total, on every row the page prints',
            f'grades {", ".join(HS_GRADES)} sum to the printed {HS_LABEL}',
            f'the five school totals sum to the printed {ALL_LABEL}',
            'the printed page and `report_enrollment_mcas` agree on every row',
        ],
        hs_resident=hs[0], hs_choice_in=hs[1], hs_total=hs[2],
        district_resident=allrow[0], district_choice_in=allrow[1],
        district_total=allrow[2],
        grades=[dict(grade=g, resident=rows[g][0], choice_in=rows[g][1],
                     total=rows[g][2]) for g in HS_GRADES],
        schools=[dict(school=s, resident=rows[s][0], choice_in=rows[s][1],
                      total=rows[s][2]) for s in SCHOOL_TOTALS],
        choice_in_outside_hs=allrow[1] - hs[1],
    )


# --------------------------------------------------------- the premise, tested not assumed

def premise(enr):
    """Is 45% of the high school a plausible number of athletes? Two independent tests.

    Neither is a count of children. Rule 7 and the standing gap: a participation is not a
    student, and this project holds no unduplicated athlete roster. What the workbook CAN
    do is bound the claim from both sides, and it does -- the year total is above the
    entire student body, and the largest single season alone is about half of it.
    """
    with open(ATHLETICS, encoding='utf-8') as fh:
        ath = json.load(fh)
    totals = [t for t in ath['participation_totals'] if t['fy'] == ATH_FY]
    if len(totals) != 1:
        fail(f'{len(totals)} FY{ATH_FY} rows in athletics.json participation_totals — '
             'expected exactly one, so the join that reads it matched nothing or too much')
    hs_participations = float(totals[0]['hs'])
    if hs_participations <= 0:
        fail(f'FY{ATH_FY} high school participations came back at {hs_participations} — '
             'the premise cannot be tested against nothing')

    seasons = [p for p in ath['participation'] if p['fy'] == ATH_FY and p['level'] == 'HS']
    if not seasons:
        fail(f'no FY{ATH_FY} high school season rows in athletics.json — the single-season '
             'bound this page states has nothing behind it')
    if abs(sum(p['athletes'] for p in seasons) - hs_participations) > CENT:
        fail(f'the FY{ATH_FY} high school seasons sum to '
             f'{sum(p["athletes"] for p in seasons):,.0f} against a stated total of '
             f'{hs_participations:,.0f} — athletics.json disagrees with itself')
    biggest = max(seasons, key=lambda p: p['athletes'])

    hs = enr['hs_resident']
    implied = DEFAULTS['athlete_share'] * hs
    return dict(
        fy=ATH_FY,
        hs_participations=hs_participations,
        seasons=[dict(season=p['season'], participations=float(p['athletes']))
                 for p in seasons],
        biggest_season=biggest['season'],
        biggest_season_participations=float(biggest['athletes']),
        # TEST ONE, the one the scenario itself implies. If 45% of 433 play, each of them
        # plays 533/195 sports. That is a number a reader can judge, and it is ordinary.
        implied_athletes=round(implied),
        implied_athletes_exact=round(implied, 2),
        per_athlete=round(hs_participations / implied, 2),
        # TEST TWO, and the stronger one. A student plays at most one sport in a season
        # in almost every case, so the largest season is close to a floor under the
        # number of children who play at all -- and it is already about half the school.
        biggest_season_share=round(biggest['athletes'] / hs, 4),
        # AND THE PROOF THAT PARTICIPATIONS ARE NOT STUDENTS: the year's total exceeds
        # the entire student body. Nothing else needs saying about that column.
        participation_share=round(hs_participations / hs, 4),
        verdict='consistent',
        verdict_note=(
            f'At {DEFAULTS["athlete_share"] * 100:.0f}% of {hs} the scenario implies '
            f'{round(implied)} athletes playing {hs_participations / implied:.2f} sports '
            f'each, which is an ordinary number. The largest single season on its own is '
            f'{biggest["athletes"] / hs * 100:.0f}% of the student body, so if anything '
            f'{DEFAULTS["athlete_share"] * 100:.0f}% is low. Neither of these is a count '
            'of children and neither should be quoted as one.'),
    )


# ------------------------------------------------------------------- DESE's own arithmetic

def formula():
    try:
        import openpyxl
    except ImportError:                                     # pragma: no cover
        fail('openpyxl is not installed, and the DESE Chapter 70 summary is a workbook')
    from taxbase import CH70, LPS_APPROPRIATION

    path = os.path.join(ROOT, CH70_XLSX)
    if not os.path.exists(path):
        fail(f'{CH70_XLSX} is not on disk — run scripts/sync_archive.py --pull')
    ws = openpyxl.load_workbook(path, data_only=True)['alldistricts']

    title = (ws['A4'].value or '').strip()
    m = re.match(r'FY(\d\d) Chapter 70 district summary$', title)
    if not m:
        fail(f'A4 reads {title!r}, not the FY?? Chapter 70 district summary — this is not '
             'the sheet whose column meanings this page quotes')
    sheet_fy = 2000 + int(m.group(1))
    heads = {'D6': 'Foundation enrollment', 'E6': 'Foundation budget',
             'F6': 'Required contribution', 'G6': 'Chapter 70 \naid',
             'H6': 'Required \nnet school spending'}
    for cell, want in heads.items():
        if ws[cell].value != want:
            fail(f'{cell} reads {ws[cell].value!r}, expected {want!r} — the column '
                 'meanings this page quotes are no longer the ones the sheet prints')

    rows, lun = [], None
    for r in range(7, ws.max_row + 1):
        name = ws.cell(r, 2).value
        if not name or ws.cell(r, 3).value != 1:
            continue
        fnd = float(ws.cell(r, 5).value or 0)
        if fnd <= 0:
            continue
        rec = dict(row=r, district=name.strip(), enrollment=ws.cell(r, 4).value or 0,
                   foundation=fnd, required=float(ws.cell(r, 6).value or 0),
                   aid=float(ws.cell(r, 7).value or 0),
                   nss=float(ws.cell(r, 8).value or 0))
        rec['gap'] = rec['foundation'] - rec['required']
        rec['above_gap'] = rec['aid'] - rec['gap']
        rows.append(rec)
        if rec['district'] == TOWN:
            lun = rec
    if lun is None:
        fail(f'no {TOWN} row in {CH70_XLSX} — the district lookup matched nothing')
    if len(rows) < 100:
        fail(f'only {len(rows)} operating districts read out of the workbook — the '
             'statewide comparison this page makes matched almost nothing')

    # TWO ROUTES TO FIVE NUMBERS. model/taxbase.CH70 was typed from this sheet by hand.
    want = dict(foundationEnrollment=lun['enrollment'],
                foundationBudget=round(lun['foundation']),
                requiredContribution=round(lun['required']),
                aid=round(lun['aid']), requiredNSS=round(lun['nss']))
    for k, v in want.items():
        if abs(CH70[k] - v) > 1:
            fail(f'model/taxbase.CH70[{k!r}] is {CH70[k]:,} and row {lun["row"]} of '
                 f'{CH70_XLSX} says {v:,} — two routes to the same DESE figure disagree')

    # THE IDENTITY THE SHEET STATES ABOUT ITSELF: F + G = H, exactly.
    if abs(lun['required'] + lun['aid'] - lun['nss']) > 1:
        fail(f'row {lun["row"]}: F+G is {lun["required"] + lun["aid"]:,.0f} against H of '
             f'{lun["nss"]:,.0f} — the identity this page rests on no longer holds')

    above = [r for r in rows if r['above_gap'] > 0]
    if lun['above_gap'] <= 0:
        fail('Lunenburg’s Chapter 70 aid is no longer above foundation minus required '
             'contribution. That is the central measurement on this page and every '
             'sentence about it is derived from here — rebuild rather than reword.')

    return dict(
        source=CH70_XLSX, sheet='alldistricts', row=lun['row'], fy=sheet_fy,
        as_of=str(ws['I1'].value)[:10] if ws['I1'].value else None,
        cells={'enrollment': f'D{lun["row"]}', 'foundation': f'E{lun["row"]}',
               'required': f'F{lun["row"]}', 'aid': f'G{lun["row"]}',
               'nss': f'H{lun["row"]}'},
        headings={k: v.replace('\n', ' ').strip() for k, v in heads.items()},
        enrollment=lun['enrollment'], foundation=round(lun['foundation'], 2),
        required=lun['required'], aid=lun['aid'], nss=lun['nss'],
        gap=round(lun['gap'], 2), above_gap=round(lun['above_gap'], 2),
        above_gap_share_of_aid=round(lun['above_gap'] / lun['aid'], 6),
        foundation_per_pupil=round(lun['foundation'] / lun['enrollment'], 2),
        aid_per_pupil=round(lun['aid'] / lun['enrollment'], 2),
        operating_districts=len(rows), districts_above_gap=len(above),
        districts_above_gap_share=round(len(above) / len(rows), 4),
        appropriation=LPS_APPROPRIATION,
        appropriation_per_pupil=round(LPS_APPROPRIATION / lun['enrollment'], 2),
        appropriation_denominator=(
            f'the FY{sheet_fy} appropriation to the schools divided by DESE’s FY{sheet_fy} '
            f'foundation enrolment of {lun["enrollment"]:,}. Both figures are FY{sheet_fy}; '
            'the denominator is the count the aid is calculated on and it is not the same '
            'as any of the three headcounts DESE publishes for the same district.'),
    )


# --------------------------------------------------- school choice money, the way it comes IN

def choice_in(c):
    """Thirteen years of the town's own School Choice revolving fund, plus the cherry sheet.

    THE STATUS PROBLEM, AND WHAT IS DONE ABOUT IT. Every one of these rows is
    `status='check failed'` in `special_revenue_funds`, and that status is about the
    PAGE: the schedule's column totals do not foot to the totals the report prints. It
    is not about this row. So no figure here is `checked` and the page says so — and
    the row's own arithmetic is asserted instead, which is a real check and a different
    one: forward + receipts − disbursements = carried, in every year that prints four
    columns, and the carried balance equals the NEXT annual report's opening balance,
    across two separately published documents.
    """
    rows = q(c, """SELECT fy, edition, fund, page, v1, v2, v3, v4, n_values, status
                   FROM   special_revenue_funds
                   WHERE  lower(fund) LIKE '%school choice%'
                   ORDER  BY fy""")
    if not rows:
        fail('no School Choice rows in special_revenue_funds — the fund join matched '
             'nothing, which looks exactly like a town that has no such fund')

    def num(s):
        s = (s or '').strip()
        return float(s.replace(',', '')) if s else None

    series, chain_checks, arith_checks = [], 0, 0
    prev = None
    for r in rows:
        fwd, rec, dis, car = (num(r['v1']), num(r['v2']), num(r['v3']), num(r['v4']))
        derived = None
        if fwd is not None and rec is not None and dis is not None:
            computed = round(fwd + rec - dis, 2)
            if car is None:
                car, derived = computed, 'carried balance, from this row’s own three others'
            elif abs(computed - car) > CENT:
                fail(f'FY{r["fy"]} School Choice: {fwd:,.2f} + {rec:,.2f} − {dis:,.2f} = '
                     f'{computed:,.2f} against a printed carried balance of {car:,.2f} — '
                     'the row does not state its own arithmetic')
            else:
                arith_checks += 1
        usable = fwd is not None and rec is not None and dis is not None
        if prev is not None and usable and prev['carried'] is not None:
            if abs(prev['carried'] - fwd) > CENT:
                fail(f'FY{r["fy"]} opens at {fwd:,.2f} against FY{prev["fy"]}’s carried '
                     f'balance of {prev["carried"]:,.2f} — two annual town reports '
                     'disagree about the same balance')
            chain_checks += 1
        row = dict(fy=int(r['fy']), edition=r['edition'], page=r['page'],
                   fund=r['fund'], status=r['status'],
                   forward=fwd, receipts=rec, disbursements=dis, carried=car,
                   derived=derived, usable=usable,
                   why=None if usable else
                       'the extract captured fewer than the four columns the schedule '
                       'prints, so this year states no receipts figure')
        series.append(row)
        if usable:
            prev = row

    usable = [r for r in series if r['usable']]
    if len(usable) < 5:
        fail(f'only {len(usable)} School Choice fund years survive their own arithmetic — '
             'a series this short is not a series')
    if chain_checks < 5:
        fail(f'only {chain_checks} year-to-year balance chains could be checked across the '
             'annual reports — the cross-document check this series rests on is missing')

    first, last = usable[0], usable[-1]

    # THE CHERRY SHEET LINE, from the FY2027 Town Meeting booklet. Read from the file by
    # the line it is printed on rather than typed (rule 2), and asserted to be there.
    bpath = os.path.join(ROOT, BOOKLET)
    if not os.path.exists(bpath):
        fail(f'{BOOKLET} is not on disk — run scripts/sync_archive.py --pull')
    blines = open(bpath, encoding='utf-8', errors='replace').read().splitlines()
    hit = [(i + 1, l) for i, l in enumerate(blines) if 'chool Choice Receiving' in l
           and '$' in l and 'Tuition' not in l]
    if not hit:
        fail('the FY2027 Town Meeting booklet no longer prints a School Choice Receiving '
             'cherry sheet line this page can read')
    lineno, line = hit[0]
    amounts = [float(x.replace(',', '')) for x in
               re.findall(r'([\d,]+\.\d\d)\$', line.replace(' $', '$'))]
    if len(amounts) < 3:
        fail(f'line {lineno} of the FY2027 Town Meeting booklet reads {line.strip()!r} and '
             f'{len(amounts)} amounts can be read out of it — this page states three')
    cherry = [dict(fy=fy, amount=a) for fy, a in zip((2025, 2026, 2027), amounts[:3])]

    return dict(
        fund_series=series, usable_years=[r['fy'] for r in usable],
        status=sorted({r['status'] for r in series}),
        status_means=('Every one of these rows is `check failed`, and that status is about '
                      'the PAGE: the schedule’s columns do not foot to the totals the '
                      'report prints. It is not a statement about this row. What IS '
                      'established here is the row’s own arithmetic and the chain between '
                      'documents — both asserted by the generator, neither by the extract.'),
        arithmetic_checks=arith_checks, chain_checks=chain_checks,
        first=first, last=last,
        receipts_change=round(last['receipts'] - first['receipts'], 2),
        receipts_pct=round(last['receipts'] / first['receipts'] - 1.0, 4),
        peak=max(usable, key=lambda r: r['receipts']),
        cherry_sheet=cherry,
        cherry_line=lineno, cherry_source=BOOKLET,
        # AN IMPLIED HEADCOUNT, and it is implied rather than counted. Dividing a cherry
        # sheet estimate by an assumed tuition rate is two assumptions stacked, and it is
        # published here only because it lands close to a count the town itself printed.
        implied_from_cherry=[dict(fy=r['fy'], amount=r['amount'],
                                  students=round(r['amount'] / DEFAULTS['tuition'], 1))
                             for r in cherry],
    )


# ---------------------------------------------------------------- finding a DESE workbook

def find_source(basename):
    """Locate a source file by NAME, never by folder.

    Rule: this archive re-files documents on purpose, so a literal `sources/<folder>/` in
    a script is a latent break with a date on it. Globbed, and the resolved path is
    returned so the caller can record where it actually was.
    """
    hits = sorted(glob.glob(os.path.join(ROOT, 'sources', '**', basename), recursive=True))
    if not hits:
        fail(f'{basename} is not anywhere under sources/ — it is a DESE workbook, it is '
             'gitignored like every other .xlsx here, and a fresh clone needs '
             'scripts/sync_archive.py --pull before this page can be built')
    if len(hits) > 1:
        fail(f'{basename} is under sources/ {len(hits)} times: '
             f'{[os.path.relpath(h, ROOT) for h in hits]} — two copies of a document are '
             'two documents until something says they are the same bytes')
    return hits[0]


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def dese_sheet(key):
    """Open one DESE workbook and return its rows, with the provenance to cite it by."""
    try:
        import openpyxl
    except ImportError:                                     # pragma: no cover
        fail('openpyxl is not installed, and every DESE source here is a workbook')
    spec = DESE[key]
    path = find_source(spec['file'])
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    if spec['sheet'] not in wb.sheetnames:
        fail(f'{spec["file"]} has no sheet {spec["sheet"]!r} — it holds '
             f'{wb.sheetnames}. The sheet is the coordinate this page cites.')
    rows = list(wb[spec['sheet']].iter_rows(values_only=True))
    wb.close()
    if not rows:
        fail(f'{spec["file"]} sheet {spec["sheet"]!r} is empty')
    prov = dict(key=key, file=spec['file'], sheet=spec['sheet'], dataset=spec['dataset'],
                title=spec['title'], path=os.path.relpath(path, ROOT),
                sha256=sha256(path), rows=len(rows))
    return rows, prov


# ------------------------------------------------- where Lunenburg's children actually go

def choice_flows():
    """DESE's own count of children leaving and arriving, thirteen school years.

    THIS IS THE BASELINE THE SCENARIO DEPARTS FROM, and until this workbook arrived
    nothing in this project held it. `money_gaps` said flatly that nobody publishes how
    many children leave the district. Somebody does.

    BOTH DIRECTIONS, ALWAYS. School choice runs two ways and Lunenburg is on both sides of
    it. A page that models children leaving without counting the ones arriving overstates
    the effect, and the net is the quantity a budget actually feels.
    """
    srows, sprov = dese_sheet('sending')
    shead = srows[0]
    want = ('SY', 'TOWN_NAME', 'ENR_REASON', 'DIST_CODE', 'DIST_NAME', 'ENR_CNT')
    if tuple(shead[:6]) != want:
        fail(f'{sprov["file"]} row 1 reads {tuple(shead[:6])!r}, expected {want!r} — the '
             'column meanings this page reads are no longer the ones the file prints')
    sending = [r for r in srows[1:] if r[1] == TOWN]
    if not sending:
        fail(f'no {TOWN} rows in {sprov["file"]} — the town filter matched nothing, which '
             'looks exactly like a town whose children never leave')

    rrows, rprov = dese_sheet('receiving')
    rhead = rrows[0]
    rwant = ('SY', 'DIST_CODE', 'DIST_NAME', 'ENR_REASON', 'TOWN_NAME', 'ENR_CNT')
    if tuple(rhead[:6]) != rwant:
        fail(f'{rprov["file"]} row 1 reads {tuple(rhead[:6])!r}, expected {rwant!r}')
    receiving = [r for r in rrows[1:] if r[1] == LEA_CODE]
    if not receiving:
        fail(f'no rows for LEA {LEA_CODE} in {rprov["file"]} — the district filter matched '
             'nothing, so the arriving half of this page would silently read as zero')

    years = sorted({int(r[0]) for r in sending} & {int(r[0]) for r in receiving})
    if len(years) < 5:
        fail(f'only {len(years)} school years appear in BOTH DESE files — a net series '
             'needs both directions in the same year')
    if LATEST_SY not in years:
        fail(f'SY{LATEST_SY} is not in both DESE files; they cover {years}. The page '
             'names the latest year in prose and that sentence is derived from here.')

    def tally(rows, sy, reason_ix, count_ix):
        out = {}
        for r in rows:
            if int(r[0]) != sy:
                continue
            out[r[reason_ix]] = out.get(r[reason_ix], 0) + int(r[count_ix] or 0)
        return out

    series = []
    for sy in years:
        s = tally(sending, sy, 2, 5)
        rcv = tally(receiving, sy, 3, 5)
        out_choice = s.get(CHOICE_REASON, 0)
        in_choice = rcv.get(CHOICE_REASON, 0)
        series.append(dict(
            sy=sy,
            out_choice=out_choice, out_charter=s.get(CHARTER_REASON, 0),
            in_choice=in_choice,
            net_choice=out_choice - in_choice,
            resident_total=sum(s.values()),
            attending_lunenburg=rcv.get(MEMBER_REASON, 0),
            out_reasons={k: v for k, v in sorted(s.items())},
            in_reasons={k: v for k, v in sorted(rcv.items())}))

    latest = next(r for r in series if r['sy'] == LATEST_SY)
    if latest['out_choice'] <= 0:
        fail(f'SY{LATEST_SY} shows {latest["out_choice"]} children leaving under school '
             'choice — the baseline this whole page is measured against came back at zero, '
             'which is what a broken filter looks like')

    # WHERE THEY GO, latest year, largest first. A count with no destination is a number;
    # a count with destinations is something a reader can act on.
    dest = sorted(
        (dict(district=r[4].strip(), reason=r[2], students=int(r[5] or 0))
         for r in sending if int(r[0]) == LATEST_SY and r[2] in (CHOICE_REASON, CHARTER_REASON)),
        key=lambda d: (-d['students'], d['district']))
    origin = sorted(
        (dict(town=r[4].strip(), reason=r[3], students=int(r[5] or 0))
         for r in receiving if int(r[0]) == LATEST_SY and r[3] == CHOICE_REASON),
        key=lambda d: (-d['students'], d['town']))
    if sum(d['students'] for d in dest if d['reason'] == CHOICE_REASON) != latest['out_choice']:
        fail('the SY destination detail does not sum back to the year total — the two '
             'reads of the same rows disagree')

    # The vocational district is MEMBERSHIP, not choice, and it is the largest single
    # destination outside Lunenburg. Naming it stops a reader adding it to the choice
    # count, which is the obvious misreading of this table.
    member_elsewhere = sorted(
        (dict(district=r[4].strip(), students=int(r[5] or 0))
         for r in sending if int(r[0]) == LATEST_SY and r[2] == MEMBER_REASON
         and r[3] != LEA_CODE), key=lambda d: -d['students'])

    outs = [r['out_choice'] for r in series]
    return dict(
        sources=[sprov, rprov],
        years=years, latest_sy=LATEST_SY, series=series, latest=latest,
        destinations=dest, origins=origin, member_elsewhere=member_elsewhere,
        peak=max(series, key=lambda r: r['out_choice']),
        low=min(series, key=lambda r: r['out_choice']),
        mean_out=round(sum(outs) / len(outs), 1),
        first=series[0], last=series[-1],
        reasons_seen=sorted({k for r in series for k in r['out_reasons']}))


# ------------------------------------------- thirty-four years of the Chapter 70 formula

def formula_history(c, fy27_aid):
    """What Chapter 70 aid has ACTUALLY done, and what its own components say drives it.

    THE POINT OF THIS BLOCK. The brief this page answers assumed aid falls with enrolment.
    Rather than assert the caveat, this measures it: DESE publishes Lunenburg's foundation
    enrolment and aid for thirty-four years, so the years enrolment fell can simply be
    counted, and what aid did in those years read off.

    AND THEN THE MECHANISM, from DESE's own aid-component columns. Aid is built on the
    PRIOR YEAR plus named increments -- foundation aid, down payment, growth, target
    phase-in and minimum aid -- and that identity is asserted here rather than described.
    In FY2026 the whole of Lunenburg's increase is the minimum aid increment, which is a
    flat amount per foundation pupil. That is the number a scenario about students leaving
    actually needs.
    """
    prows, pprov = dese_sheet('profile')
    head = None
    for i, r in enumerate(prows[:8]):
        if r and r[3] == 'fy' and r[4] == 'distfoundenro':
            head = i
            break
    if head is None:
        fail(f'{pprov["file"]} sheet {pprov["sheet"]!r} has no header row naming `fy` and '
             '`distfoundenro` in the first eight rows — the column positions this page '
             'reads are established from that row and nothing else')
    cols = tuple(prows[head][:11])
    want = ('Org4Codefy', 'Org4Code', 'LEANumCode', 'fy', 'distfoundenro',
            'distfoundbudget', 'distrlc', 'c70aid', 'rqdnss', 'rqdnss', 'actualNSS')
    if cols != want:
        fail(f'{pprov["file"]} row {head + 1} reads {cols!r}, expected {want!r}')
    hist = []
    for r in prows[head + 1:]:
        if not r or not r[1] or str(r[1]).strip() != PROFILE_ORG4:
            continue
        hist.append(dict(fy=int(r[3]), enrollment=int(r[4] or 0),
                         foundation=round(float(r[5] or 0), 2),
                         required=round(float(r[6] or 0), 2),
                         aid=round(float(r[7] or 0), 2)))
    hist.sort(key=lambda x: x['fy'])
    if len(hist) < 25:
        fail(f'only {len(hist)} years of the Chapter 70 profile for {TOWN} — the whole '
             'value of this source is its length, and a short series is not it')

    # RECONCILIATION ONE, against a completely independent document: the town's own FY2026
    # revenue ledger. If DESE's FY2026 aid and the town's budgeted Chapter 70 are not the
    # same figure, these are not the same quantity and nothing below may be published.
    ledger = q(c, """SELECT budgeted FROM v_revenue
                     WHERE object = '450600' AND fy = 2026""")
    if len(ledger) != 1:
        fail(f'{len(ledger)} Chapter 70 rows in the FY2026 revenue ledger — the check that '
             'ties DESE\'s series to the town\'s own books matched nothing usable')
    town_ch70 = round(float(ledger[0]['budgeted']), 2)
    latest = hist[-1]
    if abs(latest['aid'] - town_ch70) > 1:
        fail(f'DESE gives FY{latest["fy"]} Chapter 70 aid of {latest["aid"]:,.0f} and the '
             f'town\'s own FY2026 revenue ledger budgets {town_ch70:,.0f} — two '
             'independent documents disagree about the same year, so this series cannot '
             'be presented as the same quantity the rest of this site measures')

    # RECONCILIATION TWO: the FY27 summary workbook picks up where this series stops.
    if not (fy27_aid > latest['aid']):
        fail(f'the FY27 workbook gives aid of {fy27_aid:,.0f} against DESE\'s '
             f'FY{latest["fy"]} figure of {latest["aid"]:,.0f} — the two sources no longer '
             'continue each other and the page draws them as one line')

    # WHAT AID DID IN THE YEARS ENROLMENT FELL. Counted, not asserted.
    fell = []
    for a, b in zip(hist, hist[1:]):
        if b['enrollment'] < a['enrollment']:
            fell.append(dict(fy=b['fy'], pupils=b['enrollment'] - a['enrollment'],
                             aid_change=round(b['aid'] - a['aid'], 2),
                             aid_fell=b['aid'] < a['aid'] - 0.5))
    if not fell:
        fail('no year in thirty-four in which foundation enrolment fell — that is not a '
             'district, that is a broken read')
    aid_fell = [f for f in fell if f['aid_fell']]

    # ---- the components, and the identity they state --------------------------------
    frows, fprov = dese_sheet('factors')
    fhead = None
    for i, r in enumerate(frows[:8]):
        if r and r[3] == 'DistName' and r[4] == 'fy':
            fhead = i
            break
    if fhead is None:
        fail(f'{fprov["file"]} sheet {fprov["sheet"]!r} has no header row naming '
             '`DistName` and `fy` — the component columns are named from that row')
    fcols = list(frows[fhead])
    need = ['distfoundenro', 'foundaidinc', 'downpymtaidinc', 'growthaidinc',
            'targaidphaseinaid', 'minaidinc', 'c70aid']
    ix = {}
    for n in need:
        if n not in fcols:
            fail(f'{fprov["file"]} sheet {fprov["sheet"]!r} no longer has a column named '
                 f'{n!r} — it holds {[x for x in fcols if x]}')
        ix[n] = fcols.index(n)

    comps = []
    for r in frows[fhead + 1:]:
        if not r or r[3] != TOWN:
            continue
        rec = dict(fy=int(r[4]), enrollment=int(r[ix['distfoundenro']] or 0),
                   aid=round(float(r[ix['c70aid']] or 0), 2))
        for n in ('foundaidinc', 'downpymtaidinc', 'growthaidinc', 'targaidphaseinaid',
                  'minaidinc'):
            rec[n] = round(float(r[ix[n]] or 0), 2)
        rec['increments'] = round(sum(rec[n] for n in (
            'foundaidinc', 'downpymtaidinc', 'growthaidinc', 'targaidphaseinaid',
            'minaidinc')), 2)
        comps.append(rec)
    comps.sort(key=lambda x: x['fy'])
    if len(comps) < 10:
        fail(f'only {len(comps)} years of Chapter 70 aid components for {TOWN}')

    # THE IDENTITY: this year's aid is last year's plus the named increments. It is
    # asserted rather than described, and where it does NOT hold the residual is published
    # rather than smoothed -- those are the years the state applied a reduction, and a
    # reader is owed the fact that the identity has exceptions.
    ties, breaks = [], []
    for a, b in zip(comps, comps[1:]):
        resid = round(b['aid'] - (a['aid'] + b['increments']), 2)
        (ties if abs(resid) <= 1 else breaks).append(
            dict(fy=b['fy'], residual=resid))
    recent = [t for t in ties if t['fy'] >= comps[-1]['fy'] - 6]
    if len(recent) < 5:
        fail(f'the aid identity — last year’s aid plus the named increments — holds in '
             f'only {len(recent)} of the last seven years. The page states it as the way '
             'the calculation works and that sentence is derived from here.')

    last = comps[-1]
    if last['minaidinc'] <= 0:
        fail(f'FY{last["fy"]} carries no minimum aid increment. The marginal aid figure '
             'this page’s model opens on is derived from it, and with it at zero the '
             'model needs rebuilding rather than rewording.')
    if last['enrollment'] <= 0:
        fail(f'FY{last["fy"]} foundation enrolment came back at {last["enrollment"]}')
    min_aid_pp = round(last['minaidinc'] / last['enrollment'], 2)

    return dict(
        sources=[pprov, fprov],
        series=hist, span=[hist[0]['fy'], hist[-1]['fy']],
        latest=latest, town_ledger_ch70=town_ch70, fy27_aid=fy27_aid,
        enrolment_fell_years=fell,
        enrolment_fell=len(fell), aid_fell_too=len(aid_fell),
        aid_fell_in=[f['fy'] for f in aid_fell],
        # WHY AID FELL, only where a document says so. The component columns start at
        # FY2007, so a year before that carries no explanation in this archive and the
        # page must not borrow one from the years that do. Rule 7, in its exact shape:
        # a measurement with a plausible cause attached to the wrong rows.
        aid_fell_with_reduction=[f['fy'] for f in aid_fell
                                 if f['fy'] in {b['fy'] for b in breaks}],
        aid_fell_unexplained=[f['fy'] for f in aid_fell
                              if f['fy'] < comps[0]['fy']],
        components_from=comps[0]['fy'],
        # The recent record on its own. Rule 6: read the year-by-year rather than one
        # ratio, and the last dozen years are a different regime from the 2009 cuts.
        recent_from=comps[0]['fy'],
        recent_fell=[f for f in fell if f['fy'] >= comps[0]['fy']],
        components=comps, identity_ties=ties, identity_breaks=breaks,
        latest_components=last,
        min_aid_per_pupil=min_aid_pp,
        min_aid_total=last['minaidinc'],
        foundation_aid_inc=last['foundaidinc'],
        # Every component of the latest year, named, so the page can say which of them is
        # doing the work rather than asserting it.
        latest_named=[(n, last[n]) for n in (
            'foundaidinc', 'downpymtaidinc', 'growthaidinc', 'targaidphaseinaid',
            'minaidinc')],
    )


# ------------------------------------------- which children, not just how many

def key_factors():
    """The foundation budget is built from per-pupil rates that DIFFER BY CATEGORY.

    So which children leave changes the foundation effect, not only how many. This block
    publishes the composition DESE calculates the budget on. It does NOT publish a rate per
    category, because these sheets do not carry one -- which is registered as a gap rather
    than estimated.
    """
    try:
        import openpyxl
    except ImportError:                                     # pragma: no cover
        fail('openpyxl is not installed')
    path = find_source(DESE['factors']['file'])
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    if 'Summary' not in wb.sheetnames:
        fail(f'{DESE["factors"]["file"]} has no Summary sheet')
    rows = list(wb['Summary'].iter_rows(values_only=True))
    wb.close()
    head = None
    for i, r in enumerate(rows[:12]):
        if r and r[0] == 'LEA' and r[2] == 'Foundation Enrollment':
            head = i
            break
    if head is None:
        fail(f'{DESE["factors"]["file"]} Summary has no header row naming `LEA` and '
             '`Foundation Enrollment` — the columns this page reads are named there')
    cols = list(rows[head])
    want = ['LEA', 'Operating District', 'Foundation Enrollment', 'EL enro', 'EL %',
            'Voc enro', 'Vocational %', 'Lowinc enro', 'Lowinc %', 'Lowinc Group',
            'Labor Market Area', 'Wage Adjustment Factor', 'Foundation Budget',
            'Foundation Budget per Pupil']
    if cols[:len(want)] != want:
        fail(f'{DESE["factors"]["file"]} Summary row {head + 1} reads {cols[:len(want)]!r}, '
             f'expected {want!r}')
    lun = None
    for i, r in enumerate(rows[head + 1:], head + 2):
        if r and isinstance(r[1], str) and r[1].strip() == TOWN:
            lun = (i, r)
            break
    if lun is None:
        fail(f'no {TOWN} row on the Summary sheet of {DESE["factors"]["file"]}')
    rowno, r = lun
    title = rows[0][9] if rows and len(rows[0]) > 9 else None
    return dict(
        file=DESE['factors']['file'], sheet='Summary', row=rowno,
        title=str(title).strip() if title else None,
        enrollment=int(r[2]), el=int(r[3]), el_share=round(float(r[4]), 4),
        voc=int(r[5]), voc_share=round(float(r[6]), 4),
        lowinc=int(r[7]), lowinc_share=round(float(r[8]), 4),
        lowinc_group=r[9], labor_market=str(r[10]).strip(),
        wage_factor=float(r[11]),
        foundation=round(float(r[12]), 2),
        foundation_per_pupil=round(float(r[13]), 2))


# ------------------------------------------------------------------------------ the model

def scenario(enr, prem, fml, ath_fee, hist, flows):
    """The scenario, evaluated at its defaults. The page recomputes it as dials move.

    Everything the page draws is this function's arithmetic, so a reader who moves nothing
    sees the scenario exactly as it was put to this site, and a reader who disagrees with
    an input can say so on the page rather than in an email.
    """
    hs = enr['hs_resident']
    athletes = round(DEFAULTS['athlete_share'] * hs)
    leavers = round(DEFAULTS['transfer_rate'] * athletes)
    if leavers <= 0:
        fail('the scenario evaluates to zero students leaving — the defaults are wrong '
             'and every figure below would be zero')

    fnd_pp = fml['foundation_per_pupil']
    app_pp = fml['appropriation_per_pupil']
    # THE MARGINAL AID FIGURE, DERIVED RATHER THAN CHOSEN. See formula_history(): DESE's
    # own components make this year's aid last year's aid plus named increments, and in
    # the latest year every dollar of Lunenburg's increase is the minimum aid increment,
    # which is a flat amount per foundation pupil. So one pupil fewer is one of those
    # amounts, not one foundation budget per pupil -- and the two differ by a factor of
    # nearly a hundred. The dial spans both.
    aid_pp = hist['min_aid_per_pupil']
    defaults = dict(DEFAULTS, aid_per_pupil=aid_pp)
    foundation_reduction = round(leavers * fnd_pp, 2)
    tuition_out = round(leavers * defaults['tuition'], 2)
    aid_loss = round(leavers * aid_pp, 2)
    max_avoidable = round(leavers * app_pp, 2)
    avoided = round(defaults['avoidable_share'] * max_avoidable, 2)

    # PER GRADE, because this is the whole finding. The leavers are spread across the four
    # high school grades in proportion to the size each grade actually is, printed on the
    # same page as the total -- not divided by four, which would put more in grade 9 than
    # grade 9 has athletes to lose.
    per_grade = []
    for g in enr['grades']:
        n = leavers * g['resident'] / hs
        per_grade.append(dict(grade=g['grade'], resident=g['resident'],
                              leaving=round(n, 1),
                              remaining=round(g['resident'] - n, 1),
                              share=round(n / g['resident'], 4)))
    if abs(sum(g['leaving'] for g in per_grade) - leavers) > 0.5:
        fail('the per-grade split does not sum back to the number of students leaving')

    net = round(tuition_out + aid_loss - avoided, 2)
    break_even = round((tuition_out + aid_loss) / max_avoidable, 4)

    baseline = flows['latest']
    return dict(
        defaults=defaults, basis=DIAL_BASIS,
        aid_per_pupil=aid_pp, aid_per_pupil_max=fnd_pp,
        aid_ratio=round(fnd_pp / aid_pp, 1) if aid_pp else None,
        # THE BASELINE THIS DEPARTS FROM, which is the thing a scenario most needs and the
        # thing a public search will not surface. DESE counts the children already
        # leaving; the scenario adds to them rather than starting from nothing.
        baseline_sy=baseline['sy'],
        baseline_out=baseline['out_choice'], baseline_in=baseline['in_choice'],
        baseline_net=baseline['net_choice'],
        after_out=baseline['out_choice'] + leavers,
        after_multiple=round((baseline['out_choice'] + leavers)
                             / baseline['out_choice'], 2) if baseline['out_choice'] else None,
        hs_resident=hs, athletes=athletes, leavers=leavers,
        per_grade=per_grade,
        biggest_grade_loss=max(g['leaving'] for g in per_grade),
        foundation_per_pupil=fnd_pp, appropriation_per_pupil=app_pp,
        foundation_reduction=foundation_reduction,
        tuition_out=tuition_out,
        aid_loss=aid_loss,
        aid_loss_upper=foundation_reduction,
        aid_loss_ratio=round(foundation_reduction / aid_loss, 1) if aid_loss else None,
        max_avoidable=max_avoidable, avoided=avoided,
        net_cost=net,
        net_cost_upper=round(tuition_out + foundation_reduction, 2),
        break_even_avoidable_share=break_even,
        break_even_upper=round((tuition_out + foundation_reduction) / max_avoidable, 4),
        # The athletics revolving fund loses the fees these students were paying. It is a
        # small number and it is on the page because the scenario is about athletes -- and
        # because a fund losing revenue is not the same event as the town losing revenue.
        fee=ath_fee,
        participations_lost=round(leavers * prem['per_athlete'], 1),
        fees_lost=round(leavers * prem['per_athlete'] * ath_fee['amount'], 2)
        if ath_fee else None,
    )


def athletics_fee():
    with open(ATHLETICS, encoding='utf-8') as fh:
        ath = json.load(fh)
    hs = [f for f in ath['fee_headline'] if f['level'] == 'HS']
    if not hs:
        fail('no high school athletic fee in athletics.json — the fee side of this '
             'scenario has nothing behind it')
    latest = max(hs, key=lambda f: f['fy'])
    return dict(fy=latest['fy'], amount=float(latest['amount']),
                school_year=latest.get('school_year'), source=latest.get('source'),
                set_on=latest.get('set_on') or None)


# ----------------------------------------------------------------- what the town said

def said():
    out = []
    for spec in QUOTES:
        rel = f'{MINUTES}/{spec["board"]}/{spec["date"]}-{spec["kind"]}-{spec["doc"]}.txt'
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            fail(f'{rel} is not here — a quote on this page is attributed to a document '
                 'that is not in the archive')
        text = norm(open(path, encoding='utf-8', errors='replace').read())
        if norm(spec['quote']) not in text:
            fail(f'the quote attributed to {spec["board"]} {spec["date"]} is no longer in '
                 f'{rel} — quote the source, never your rendering of it')
        out.append(dict(
            key=spec['key'], board=spec['board'].replace('-', ' ').title(),
            date=spec['date'], quote=spec['quote'], who=spec['who'], why=spec['why'],
            cite=f'/docs/{rel.replace("sources/", "")}',
            town=f'https://www.lunenburgma.gov/AgendaCenter/ViewFile/'
                 f'{"Minutes" if spec["kind"] == "minutes" else "Agenda"}/'
                 f'_{spec["date"][5:7]}{spec["date"][8:10]}{spec["date"][:4]}-{spec["doc"]}'))
    return out


# --------------------------------------------------------------------------- the build

def build():
    if not os.path.exists(DB):
        fail(f'{os.path.relpath(DB, ROOT)} is not here — run scripts/build_db.py')
    c = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    c.row_factory = sqlite3.Row

    enr = enrolment(c)
    prem = premise(enr)
    fml = formula()
    fee = athletics_fee()
    inbound = choice_in(c)
    flows = choice_flows()
    hist = formula_history(c, fml['aid'])
    factors = key_factors()
    scn = scenario(enr, prem, fml, fee, hist, flows)
    quotes = said()

    # TWO ROUTES TO THE FY26 FOUNDATION BUDGET, from two different DESE workbooks. The
    # Chapter 70 profile and the key-factors summary are separate files with separate
    # calculations behind them, and if they disagree neither may be published.
    if abs(factors['foundation'] - hist['latest']['foundation']) > 1:
        fail(f'the key-factors summary gives a FY{hist["latest"]["fy"]} foundation budget '
             f'of {factors["foundation"]:,.0f} and the Chapter 70 profile gives '
             f'{hist["latest"]["foundation"]:,.0f} — two DESE workbooks disagree')
    if factors['enrollment'] != hist['latest']['enrollment']:
        fail(f'the two DESE workbooks disagree about FY{hist["latest"]["fy"]} foundation '
             f'enrolment: {factors["enrollment"]} and {hist["latest"]["enrollment"]}')

    gaps = {g['what']: g for g in q(c, 'SELECT side, what, why FROM money_gaps')}
    missing = [k for k in GAP_KEYS if k not in gaps]
    if missing:
        fail('money_gaps no longer carries: ' + '; '.join(missing) +
             ' — rule 7c says a limit this page hits is registered there, and a gap '
             'quoted by key that has been renamed renders as an empty box')

    def split(g):
        w = g['why']
        i = w.find('— closes:')
        return dict(side=g['side'], what=g['what'],
                    why=(w[:i].strip() if i >= 0 else w.strip()),
                    closes=(w[i + len('— closes:'):].strip() if i >= 0 else None))

    with open(REPORTS, encoding='utf-8') as fh:
        by_id = {r['id']: r for r in json.load(fh)['reports']}
    related = []
    for rid, why in RELATED:
        r = by_id.get(rid)
        if r is None:
            fail(f'reports.json no longer carries {rid}, which this page cites')
        related.append(dict(id=rid, title=r['title'], why=why, words=r['words'],
                            updated=r['updated'], url=r['markdown']['url'],
                            pdf=(r.get('pdf') or {}).get('url')))

    return dict(
        generated_by='scripts/build_if_students_leave.py',
        source=f'{REPORT_TXT}; {CH70_XLSX}; {BOOKLET}; '
               + '; '.join(sorted(v['file'] for v in DESE.values()))
               + '; fy28/public/data/athletics.json; model/taxbase.py; '
               'sources/data/lunenburg.db — report_enrollment_mcas, v_revenue, '
               f'special_revenue_funds, money_gaps; {MINUTES}/',
        enrolment=enr,
        premise=prem,
        formula=fml,
        formula_history=hist,
        key_factors=factors,
        flows=flows,
        choice_in=inbound,
        scenario=scn,
        said=quotes,
        gaps=[split(gaps[k]) for k in GAP_KEYS],
        related=related,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='fail if the published file is not what this would write')
    a = ap.parse_args()
    payload = json.dumps(build(), indent=1, sort_keys=True) + '\n'
    rel = os.path.relpath(OUT, ROOT)
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if have != payload:
            print(f'STALE — {rel} is not what the archive now produces. '
                  'Run scripts/build_if_students_leave.py.')
            return 1
        print(f'ok — {rel} reproduces from the archive')
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(payload)
    d = json.loads(payload)
    s, f, h = d['scenario'], d['formula'], d['formula_history']
    print(f'wrote {rel} — {s["baseline_out"]} children already leave under school choice '
          f'in SY{s["baseline_sy"]} ({s["baseline_in"]} arrive); the scenario adds '
          f'{s["leavers"]} more, {s["after_multiple"]}x the present flow. '
          f'Chapter 70 moves {h["min_aid_per_pupil"]:,.2f} a pupil at the margin against a '
          f'foundation budget of {f["foundation_per_pupil"]:,.2f}; enrolment fell in '
          f'{h["enrolment_fell"]} of {h["span"][1] - h["span"][0]} years and aid fell in '
          f'{h["aid_fell_too"]}. Break-even avoidable share '
          f'{s["break_even_avoidable_share"] * 100:.0f}%')
    return 0


if __name__ == '__main__':
    sys.exit(main())
