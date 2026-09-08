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
    aid_response=0.0,         # share of the foundation reduction that reaches aid
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
    'aid_response': (
        'assumed',
        'Opens at zero because DESE’s own row shows Chapter 70 aid already above '
        'foundation minus required contribution, so the foundation subtraction is not '
        'what is currently setting the aid. Drag it to 100% for the scenario as it was '
        'originally modelled.'),
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
    'How many children leave the district each year, and for where',
    'How many children play sports',
    'How many children Chapter 70 is actually paid for',
    'What Lunenburg pays in school choice sending tuition, and for how many children',
    'What Chapter 70 aid would actually do if enrolment fell',
    'How much of a school budget stops being spent when a student leaves',
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


# ------------------------------------------------------------------------------ the model

def scenario(enr, prem, fml, ath_fee):
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
    foundation_reduction = round(leavers * fnd_pp, 2)
    tuition_out = round(leavers * DEFAULTS['tuition'], 2)
    aid_loss = round(DEFAULTS['aid_response'] * foundation_reduction, 2)
    max_avoidable = round(leavers * app_pp, 2)
    avoided = round(DEFAULTS['avoidable_share'] * max_avoidable, 2)

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

    return dict(
        defaults=DEFAULTS, basis=DIAL_BASIS,
        hs_resident=hs, athletes=athletes, leavers=leavers,
        per_grade=per_grade,
        biggest_grade_loss=max(g['leaving'] for g in per_grade),
        foundation_per_pupil=fnd_pp, appropriation_per_pupil=app_pp,
        foundation_reduction=foundation_reduction,
        tuition_out=tuition_out,
        aid_loss=aid_loss,
        aid_loss_upper=foundation_reduction,
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
    scn = scenario(enr, prem, fml, fee)
    quotes = said()

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
        source=f'{REPORT_TXT}; {CH70_XLSX}; {BOOKLET}; fy28/public/data/athletics.json; '
               'model/taxbase.py; sources/data/lunenburg.db — report_enrollment_mcas, '
               f'special_revenue_funds, money_gaps; {MINUTES}/',
        enrolment=enr,
        premise=prem,
        formula=fml,
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
    s, f = d['scenario'], d['formula']
    print(f'wrote {rel} — {s["leavers"]} students leaving of {s["hs_resident"]}; '
          f'aid sits {f["above_gap"]:,.0f} above foundation minus required contribution '
          f'({f["districts_above_gap"]} of {f["operating_districts"]} districts do); '
          f'break-even avoidable share {s["break_even_avoidable_share"] * 100:.0f}%')
    return 0


if __name__ == '__main__':
    sys.exit(main())
