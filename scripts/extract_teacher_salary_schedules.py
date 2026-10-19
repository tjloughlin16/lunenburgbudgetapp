#!/usr/bin/env python3
"""Every TEACHER SALARY SCHEDULE in the comparison districts' contracts, read off the page.

    python3 scripts/extract_teacher_salary_schedules.py            # write the two CSVs
    python3 scripts/extract_teacher_salary_schedules.py --check    # ...and fail if they would change
    python3 scripts/extract_teacher_salary_schedules.py --ocr      # (re)make the word-box cache for
                                                                   #   the scanned pages, via Vision
    python3 scripts/extract_teacher_salary_schedules.py --dump DOC PAGE   # the page's words, for
                                                                   #   writing a layout

WHY. A local union leader told this project that Lunenburg pays teachers less than any
comparison district. DESE's AVERAGE teacher salary does not settle that: an average is the
scale times the seniority and education of whoever is employed. The claim is about the PAY
SCALE, and the scale is printed in each district's teachers' contract, by step and lane.

OUTPUT.
  sources/data/teacher-salary-schedules.csv      one row per printed cell
  sources/data/teacher-salary-schedule-docs.csv  one row per contract: what it covers, which
                                                 schedules were read, and what was not

THE METHOD IS CLAUDE.md 13b, because half these contracts are scans.
  1. WORDS WITH POSITIONS. A page with a readable text layer is read by pdfplumber; a scanned
     page by `ocr_words.swift` (Vision, a box per word), cached as a TSV under
     sources/contracts/txt/words/ so that --check does not depend on re-running Vision.
     `pdf_kind.py` decided which pages are scans (rule 13d); a layout names its source.
  2. THE COLUMNS ARE NAMED FROM A HEADER SOMEBODY READ AND WROTE DOWN. Every LAYOUT below
     carries the lanes exactly as the page prints them, and the steps as printed. Nothing is
     inferred from heading words: on two of these pages the lane headers are white text on a
     shaded band and are not in any text layer at all.
  3. ROWS BY POSITION, after measuring the page's own rotation (the median slope between
     neighbouring figures); the band is half the page's own row pitch.
  4. FIGURES PLACED BY COLUMN POSITION, NEVER BY ORDER. The figures' x-centres are split into
     exactly as many columns as the header has lanes, at the widest gaps; each figure goes to
     the nearest column. A lane with no figure in a row (A-W's closed step 16, North
     Middlesex's B lanes above step 10, Monty Tech's staircase) stays absent.
  5. A GRID IS REFUSED, NOT GUESSED, when its rows do not number its printed steps, when two
     figures land in one cell, or when a printed step label disagrees with the row it sits on.
     A refused grid is recorded in the docs register with the reason.
  6. CORRECTIONS ARE NAMED. Where OCR misread a figure and the arithmetic check caught it, the
     cell was read by eye off the rendered page and is listed in CORRECTIONS with what OCR
     returned. A correction applies only if OCR still returns exactly that misreading, so a
     changed OCR cache cannot silently keep an old fix.

THE CHECK. Within one schedule, salary must rise with every step in a lane and with every lane
in a step. A cell that does not is FLAGGED in the CSV (`flag`), never dropped or adjusted: some
contracts genuinely print equal cells (Leominster's steps 13 and 14 in the B lanes), and the
reader should see them.

WHAT THIS DOES NOT DO. It reads the BASE schedule only. Longevity payments, stipends, the
doctorate/CAGS add-ons and National Board increments that some contracts pay outside the grid
are not in it; the docs register notes where a contract prints them.
"""
import argparse
import csv
import io
import os
import re
import statistics
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources')
WORDS = os.path.join(SRC, 'contracts', 'txt', 'words')
OUT = os.path.join(SRC, 'data', 'teacher-salary-schedules.csv')
DOCS_OUT = os.path.join(SRC, 'data', 'teacher-salary-schedule-docs.csv')

FIELDS = ['district', 'org_code', 'contract_period', 'fy', 'schedule', 'step', 'lane', 'salary',
          'doc', 'page', 'read', 'flag']
DOC_FIELDS = ['district', 'org_code', 'doc', 'publisher', 'upstream', 'publisher_filename',
              'contract_period', 'pdf_kind', 'fiscal_years_read', 'cells', 'status', 'note']


def fail(msg):
    raise SystemExit('extract_teacher_salary_schedules: ' + msg)


# ----------------------------------------------------------------------------- the contracts
# One row per document. `kind` is what scripts/pdf_kind.py printed for it on 19 October 2026.
CONTRACTS = {
    'contracts/pdf/dese-teacher-contract.pdf': dict(
        district='Lunenburg', org='01620000', period='2024-07-01 to 2027-06-30',
        publisher='DESE educator contracts', filename='Teacher_Contract.pdf',
        upstream='https://profiles.doe.mass.edu/statereport/educatorcontractsdownload.aspx?orgcode=01620000&type=T',
        kind='scan: 72 image',
        note='Appendix B, pdf pages 36-37 (printed 33-34). The FY27 grid runs onto page 37.'),
    'contracts/pdf/dese-teacher-contract-harvard.pdf': dict(
        district='Harvard', org='01250000', period='2017-09-01 to 2020-08-31',
        publisher='DESE educator contracts', filename='Teacher_Contract.pdf',
        upstream='https://profiles.doe.mass.edu/statereport/educatorcontractsdownload.aspx?orgcode=01250000&type=T',
        kind='digital: 44 text',
        note='DESE publishes the latest contract a district SUBMITTED; this one expired in 2020. '
             'FY20 is printed twice: a first-half schedule and a mid-year (+1.25%) schedule.'),
    'contracts/pdf/harvard-teachers-2023-2026.pdf': dict(
        district='Harvard', org='01250000', period='2023-08-24 to 2026-08-23',
        publisher='Town of Harvard, DocumentCenter',
        filename='Teachers Contract Aug 24, 2023-Aug 23, 2026.pdf',
        upstream='https://www.harvard-ma.gov/DocumentCenter/View/2216/Teachers-Contract-Aug-24-2023-Aug-23-2026-PDF',
        kind='mixed: 4 image, 41 text, 1 text+image',
        note='The current Harvard Educators Association contract, from the town site, because '
             "DESE's filing is the 2017-2020 one."),
    'contracts/pdf/dese-teacher-contract-groton-dunstable.pdf': dict(
        district='Groton-Dunstable', org='06730000',
        period='base agreement from 2014-09-01 (signed 2015-08-31); Schedule A for 2017-18 to 2019-20',
        publisher='DESE educator contracts', filename='Teacher_Contract.pdf',
        upstream='https://profiles.doe.mass.edu/statereport/educatorcontractsdownload.aspx?orgcode=06730000&type=T',
        kind='scan: 30 image',
        note='Pages are out of order in the filing: the schedules are pdf pages 3 (2017-18, '
             '2018-19) and 2 (2019-20). Figures printed to the cent. A 2024-2027 agreement was '
             'ratified (Groton Herald, 30 October 2024) and is not filed with DESE or found '
             'published.'),
    'contracts/pdf/dese-teacher-contract-leominster.pdf': dict(
        district='Leominster', org='01530000', period='2015-07-01 to 2018-06-30',
        publisher='DESE educator contracts', filename='Teacher_Contract.pdf',
        upstream='https://profiles.doe.mass.edu/statereport/educatorcontractsdownload.aspx?orgcode=01530000&type=T',
        kind='scan: 71 image',
        note='Expired 2018; no later Leominster contract was found published. Steps 0-14; each '
             'lane carries two names (B / VC, ...), the second for vocational teachers.'),
    'contracts/pdf/dese-teacher-contract-north-middlesex.pdf': dict(
        district='North Middlesex', org='07350000', period='2018-09-01 to 2021-06-30',
        publisher='DESE educator contracts', filename='Teacher_Contract.pdf',
        upstream='https://profiles.doe.mass.edu/statereport/educatorcontractsdownload.aspx?orgcode=07350000&type=T',
        kind='scan: 98 image',
        note='Expired 2021; superseded by the 2024-2027 agreement below. A poor scan: the cells '
             'read by eye off a 2.6x render say so in `read`. The BA lanes print $0 at steps '
             '11-13; those cells are not rows here.'),
    'contracts/pdf/north-middlesex-teachers-2024-2027.pdf': dict(
        district='North Middlesex', org='07350000', period='2024-07-01 to 2027-06-30',
        publisher='North Middlesex Teachers Association (massteacher.org)',
        filename='Final-Teachers-CBA-2024-2027-NMRSD.pdf',
        upstream='https://nmta.massteacher.org/wp-content/uploads/sites/23/2025/03/Final-Teachers-CBA-2024-2027-NMRSD.pdf',
        kind='digital: 67 text, 1 text+image',
        note='The union’s posted copy of the current agreement. The B+15 lane is closed to new '
             'entrants since 1 July 2019 (p23). BA and BA+15 stop at step 10.'),
    'contracts/pdf/dese-teacher-contract-ayer-shirley.pdf': dict(
        district='Ayer Shirley', org='06160000', period='2019-09-01 to 2022-08-31',
        publisher='DESE educator contracts', filename='Teacher_Contract.pdf',
        upstream='https://profiles.doe.mass.edu/statereport/educatorcontractsdownload.aspx?orgcode=06160000&type=T',
        kind='mixed: 1 image, 43 text, 2 text+image',
        note='Expired 2022. The 2022-2025 agreement the district posted '
             '(asrsd.org/.../ASREA%202022-2025.pdf) returned 404 on 19 October 2026. The B lanes '
             'print $0 at steps 13-14 (no such step); those cells are not rows here. "Above top '
             'step" salaries for a closed group are outside the grid (p41).'),
    'contracts/pdf/dese-teacher-contract-fitchburg.pdf': dict(
        district='Fitchburg', org='00970000', period='2015-07-01 to 2018-06-30',
        publisher='DESE educator contracts', filename='Teacher_Contract.pdf',
        upstream='https://profiles.doe.mass.edu/statereport/educatorcontractsdownload.aspx?orgcode=00970000&type=T',
        kind='mixed: 2 image, 42 text+image',
        note='Expired 2018; superseded by the 2024-2027 agreement below. Step 7 is $1,000 above '
             'step 6 in 2016-17; in 2017-18 every lane\u2019s step 7 is about $1,000 more than '
             '1.25% over 2016-17, which the stated-increase check flags. A further step-7 row '
             'is dated 6/30/2018.'),
    'contracts/pdf/fitchburg-teachers-2024-2027.pdf': dict(
        district='Fitchburg', org='00970000', period='2024-07-01 to 2027-06-30',
        publisher='Fitchburg Education Association (massteacher.org)',
        filename='FEA-Teachers-24-27.pdf',
        upstream='https://fitchburg.massteacher.org/wp-content/uploads/sites/49/2026/05/FEA-Teachers-24-27.pdf',
        kind='mixed: 1 image, 71 text+image',
        note='The union’s posted copy. Lane headers are printed on a shaded band and are not '
             'in the text layer; they were read off the page. Longevity is paid OUTSIDE the '
             'schedule: $1,000 a year after 7 years, plus $500-$2,000 after 15 (p66).'),
    'contracts/pdf/dese-teacher-contract-ashburnham-westminster.pdf': dict(
        district='Ashburnham-Westminster', org='06100000', period='2016-07-01 to 2019-06-30',
        publisher='DESE educator contracts', filename='Teacher_Contract.pdf',
        upstream='https://profiles.doe.mass.edu/statereport/educatorcontractsdownload.aspx?orgcode=06100000&type=T',
        kind='digital: 39 text, 1 text+image',
        note='Expired 2019; no later contract was found published. Step 15 is the top step; '
             'step 16 is printed for four lanes and attainable only by those placed there by '
             '1 July 2016 (p32).'),
    'contracts/pdf/dese-teacher-contract-montachusett.pdf': dict(
        district='Montachusett Regional Vocational Technical', org='08320000',
        period='2023-09-01 to 2026-08-31',
        publisher='DESE educator contracts', filename='Teacher_Contract.pdf',
        upstream='https://profiles.doe.mass.edu/statereport/educatorcontractsdownload.aspx?orgcode=08320000&type=T',
        kind='mixed: 44 image, 3 text',
        note='A vocational school: the columns are defined twice, for vocational teachers by '
             'licensure plus credits and for academic teachers by degree (p39). Lanes here use '
             'the academic name first. Columns I-IV run to step 15 and V-VIII to step 16 (step 16 is '
             'shaded in I-IV). The step 3 to 4 increase is larger than any other. '
             'Printed sideways. Adds $1,000 per further advanced degree in column VIII and '
             '$1,500 for National Board certification, outside the grid.'),
}

# ----------------------------------------------------------------------------- the layouts
# One per printed grid. `region` = (row0, row1, col0, col1) as fractions of the page in the
# READING frame (rows top-down). `frame`: 'normal', or 'sideways' for a table printed across
# the page (Monty Tech's, whose pages carry /Rotate 90 and 270 -- ocr_words.swift folds both
# into one frame). Not assumed: the printed step labels must sit on the rows the layout gives
# them, or the grid is refused. `src`: 'text' (the PDF's text layer) or 'ocr' (the cached Vision words).
# `fy` is the fiscal year the schedule is paid in: a 2025-2026 school year is FY2026.
L = []


def grid(doc, page, fy, schedule, lanes, steps, region, src, frame='normal', vs=None):
    """`vs` = (an earlier schedule's printed title in the same document, the factor the
    contract states between them). Where given, every cell present in both must equal the
    earlier cell times the factor to within $2 -- a second instrument, independent of OCR,
    that catches a misread digit the rising-steps check cannot (73,285 for 73,286)."""
    L.append(dict(doc=doc, page=page, fy=fy, schedule=schedule, lanes=lanes, steps=steps,
                  region=region, src=src, frame=frame, vs=vs))


def S(a, b):
    return [str(i) for i in range(a, b + 1)]


# Each block below was written after looking at the rendered page.

# LUNENBURG. Appendix B, three grids headed "FY 25 Salary 2.5 % COLA", "FY 26 Salary 4.0%
# COLA", "FY 27 Salary 3.5% COLA"; FY27 steps 6-13 continue on the next page.
D = 'contracts/pdf/dese-teacher-contract.pdf'
LUN = ['Bach', 'B+15', 'B+30', 'Masters', 'M+15', 'M+30', 'M+45', 'M+60', 'M+75', 'Doctorate']
grid(D, 36, '2025', 'FY 25 Salary 2.5 % COLA', LUN, S(1, 13), (0.19, 0.46, 0, 1), 'ocr')
grid(D, 36, '2026', 'FY 26 Salary 4.0% COLA', LUN, S(1, 13), (0.50, 0.77, 0, 1), 'ocr',
     vs=('FY 25 Salary 2.5 % COLA', 1.04))
grid(D, 36, '2027', 'FY 27 Salary 3.5% COLA', LUN, S(1, 5), (0.81, 0.92, 0, 1), 'ocr',
     vs=('FY 26 Salary 4.0% COLA', 1.035))
grid(D, 37, '2027', 'FY 27 Salary 3.5% COLA', LUN, S(6, 13), (0.06, 0.24, 0, 1), 'ocr',
     vs=('FY 26 Salary 4.0% COLA', 1.035))

# NORTH MIDDLESEX, DESE's filing (2018-2021). Three grids, "2% COLA + STEPS", headed FY2019,
# FY2020, FY2021. The BA and BA+15 lanes print $0 at steps 11-13.
D = 'contracts/pdf/dese-teacher-contract-north-middlesex.pdf'
NM = ['BA', 'BA+15', 'MA', 'MA+15', 'MA+30', 'MA+45', 'MA+60', 'MA+75']
grid(D, 24, '2019', 'FY2019 2% COLA + STEPS', NM, S(1, 13), (0.145, 0.33, 0, 1), 'ocr')
grid(D, 24, '2020', 'FY2020 2% COLA + STEPS', NM, S(1, 13), (0.40, 0.59, 0, 1), 'ocr',
     vs=('FY2019 2% COLA + STEPS', 1.02))
grid(D, 24, '2021', 'FY2021 2% COLA + STEPS', NM, S(1, 13), (0.66, 0.86, 0, 1), 'ocr',
     vs=('FY2020 2% COLA + STEPS', 1.02))

# NORTH MIDDLESEX, 2024-2027 (the union's copy). "FY25 3.00% COLA", "FY26 3.50% COLA" (steps
# 7-13 on page 25), "FY27 3.50% COLA". Same lanes; the last prints "MA+75/Ph.D".
D = 'contracts/pdf/north-middlesex-teachers-2024-2027.pdf'
NM2 = NM[:-1] + ['MA+75/Ph.D.']
grid(D, 24, '2025', 'FY25 3.00% COLA', NM2, S(1, 13), (0.152, 0.61, 0, 1), 'text')
grid(D, 24, '2026', 'FY26 3.50% COLA', NM2, S(1, 6), (0.685, 0.89, 0, 1), 'text',
     vs=('FY25 3.00% COLA', 1.035))
grid(D, 25, '2026', 'FY26 3.50% COLA', NM2, S(7, 13), (0.09, 0.33, 0, 1), 'text',
     vs=('FY25 3.00% COLA', 1.035))
grid(D, 25, '2027', 'FY27 3.50% COLA', NM2, S(1, 13), (0.40, 0.86, 0, 1), 'text',
     vs=('FY26 3.50% COLA', 1.035))

# HARVARD, 2023-2026 (the town's copy). "FY24 HEA Scale", "FY25 HEA Scale", "FY26 HEA Scale";
# the text above each states the increase (2.5%, 3%, 2.5%).
D = 'contracts/pdf/harvard-teachers-2023-2026.pdf'
HV = ['B', 'B15', 'M', 'M15', 'M30', 'M45', 'M60', 'PhD']
grid(D, 32, '2024', 'FY24 HEA Scale', HV, S(1, 13), (0.26, 0.61, 0, 1), 'text')
grid(D, 33, '2025', 'FY25 HEA Scale', HV, S(1, 13), (0.23, 0.58, 0, 1), 'text',
     vs=('FY24 HEA Scale', 1.03))
grid(D, 34, '2026', 'FY26 HEA Scale', HV, S(1, 13), (0.23, 0.58, 0, 1), 'text',
     vs=('FY25 HEA Scale', 1.025))

# HARVARD, DESE's filing (2017-2020). FY18 (+1.5%), FY19 (+2.75%), FY20 first half (+2%),
# FY20 mid-year (+1.25%). Printed under the heading "Harvard Public Schools Contract
# Proposal - HPS to HTA".
D = 'contracts/pdf/dese-teacher-contract-harvard.pdf'
grid(D, 31, '2018', 'FY18', HV, S(1, 13), (0.165, 0.61, 0, 1), 'text')
grid(D, 32, '2019', 'FY19', HV, S(1, 13), (0.225, 0.67, 0, 1), 'text', vs=('FY18', 1.0275))
grid(D, 33, '2020', 'FY20 - First Half Year', HV, S(1, 13), (0.228, 0.67, 0, 1), 'text',
     vs=('FY19', 1.02))
grid(D, 34, '2020', 'FY20 - Mid-Year', HV, S(1, 13), (0.188, 0.63, 0, 1), 'text',
     vs=('FY20 - First Half Year', 1.0125))

# ASHBURNHAM-WESTMINSTER, DESE's filing (2016-2019). Appendix C, one schedule a page. The two
# right-hand headers are printed on two lines each: "CAGS / MA/MA" and "DOC / MA75". No
# increase is stated in the contract text, so there is no stated-increase check.
D = 'contracts/pdf/dese-teacher-contract-ashburnham-westminster.pdf'
AW = ['BA', 'BA30', 'MA', 'MA30', 'MA60', 'CAGS MA/MA', 'DOC MA75']
grid(D, 32, '2017', 'TEACHER\'S SALARY SCHEDULE 2016-2017', AW, S(1, 16), (0.205, 0.52, 0, 1), 'text')
grid(D, 33, '2018', 'TEACHER\'S SALARY SCHEDULE 2017-2018', AW, S(1, 16), (0.202, 0.52, 0, 1), 'text')
grid(D, 34, '2019', 'TEACHER\'S SALARY SCHEDULE 2018-2019', AW, S(1, 16), (0.199, 0.515, 0, 1), 'text')

# AYER SHIRLEY, DESE's filing (2019-2022). Schedule A, "2019-2020 Teacher Salary Scale 3.0%
# FY20" and so on; three lanes are added in FY21. Each year is the prior x 1.03 (Art. XXXV).
D = 'contracts/pdf/dese-teacher-contract-ayer-shirley.pdf'
AS1 = ['[BA]', '[BA+15]', 'MA', 'MA15', 'MA30']
AS2 = AS1 + ['MA45', 'MA60', 'MA75']
grid(D, 38, '2020', '2019-2020 Teacher Salary Scale 3.0% FY20', AS1, S(1, 14), (0.28, 0.62, 0, 1), 'text')
grid(D, 39, '2021', '2020-2021 Teacher Salary Scale 3.0% FY21', AS2, S(1, 14), (0.16, 0.45, 0, 1), 'text',
     vs=('2019-2020 Teacher Salary Scale 3.0% FY20', 1.03))
grid(D, 40, '2022', '2021-2022 Teacher Salary Scale 3.0% FY22', AS2, S(1, 14), (0.16, 0.44, 0, 1), 'text',
     vs=('2020-2021 Teacher Salary Scale 3.0% FY21', 1.03))

# FITCHBURG, 2024-2027 (the union's copy). Appendix II, "2024-2025 - 3% COLA and Step 9",
# "2025-2026 - 3% COLA and Step 10", "2026-2027 - 2.5% COLA and Step 11". The page is a scan
# carrying somebody's text layer, and that layer is INCOMPLETE -- it holds five of the eleven
# MA+60 figures on page 66 -- so these pages are read by Vision like any other scan. The lane
# headers are white on a shaded band and were read off the page.
D = 'contracts/pdf/fitchburg-teachers-2024-2027.pdf'
FT = ['BA', 'BA+15', 'BA+30', 'MA', 'MA+15', 'MA+30', 'MA+45', 'MA+60']
grid(D, 65, '2025', '2024-2025 - 3% COLA and Step 9', FT, S(1, 9), (0.29, 0.47, 0, 1), 'ocr')
grid(D, 65, '2026', '2025-2026 - 3% COLA and Step 10', FT, S(1, 10), (0.545, 0.73, 0, 1), 'ocr',
     vs=('2024-2025 - 3% COLA and Step 9', 1.03))
grid(D, 66, '2027', '2026-2027 - 2.5% COLA and Step 11', FT, S(1, 11), (0.14, 0.36, 0, 1), 'ocr',
     vs=('2025-2026 - 3% COLA and Step 10', 1.025))

# GROTON-DUNSTABLE, DESE's filing. "Unit A Salary Schedule / Schedule A / 2017-2018", then
# 2018-2019 below it on pdf page 3, and 2019-2020 alone on pdf page 2. Printed to the cent.
# The B lanes stop at step 9, M at 10, M15 at 11. Increases stated in Art. (p20): 1.50%,
# 2.25%, 2.25%.
D = 'contracts/pdf/dese-teacher-contract-groton-dunstable.pdf'
GD = ['B', 'B15', 'M', 'M15', 'M30', 'M45', 'M60']
grid(D, 3, '2018', 'Unit A Salary Schedule, Schedule A, 2017-2018', GD, S(1, 12), (0.21, 0.44, 0, 1), 'ocr')
grid(D, 3, '2019', 'Unit A Salary Schedule, Schedule A, 2018-2019', GD, S(1, 12), (0.565, 0.795, 0, 1), 'ocr',
     vs=('Unit A Salary Schedule, Schedule A, 2017-2018', 1.0225))
grid(D, 2, '2020', 'Unit A Salary Schedule, Schedule A, 2019-2020', GD, S(1, 12), (0.268, 0.50, 0, 1), 'ocr',
     vs=('Unit A Salary Schedule, Schedule A, 2018-2019', 1.0225))

# LEOMINSTER, DESE's filing (2015-2018). Appendix 2, "Teacher Salaries 2015-2018": four grids
# headed '15-'16 (+1%), '16-'17 (+2%), '17-'18 (+2%) and 6/30/2018 (+1%) -- the last a 1%
# increase on the final day of FY2018, so it is recorded under FY2018 with its own title.
# Each lane has two printed names, the second for vocational teachers. Steps 0-14.
D = 'contracts/pdf/dese-teacher-contract-leominster.pdf'
LE = ['B / VC', 'B+15 / VC+15', 'M / VC+30', 'M+15 / VC+45', 'M+30 / VC+60', 'M+45 / VC+75',
      'M+60 / VC+90']
grid(D, 52, '2016', "'15-'16 (+1%)", LE, S(0, 14), (0.195, 0.515, 0, 1), 'ocr')
grid(D, 52, '2017', "'16-'17 (+2%)", LE, S(0, 14), (0.58, 0.90, 0, 1), 'ocr',
     vs=("'15-'16 (+1%)", 1.02))
grid(D, 53, '2018', "'17-'18 (+2%)", LE, S(0, 14), (0.138, 0.46, 0, 1), 'ocr',
     vs=("'16-'17 (+2%)", 1.02))
grid(D, 53, '2018', '6/30/2018 (+1%)', LE, S(0, 14), (0.522, 0.845, 0, 1), 'ocr',
     vs=("'17-'18 (+2%)", 1.01))

# FITCHBURG, DESE's filing (2015-2018). Appendix II, one page: 2015-16 (2.0%, steps 0-6),
# 2016-17 (1.25%, steps 0-7 -- step 7 is step 6 plus $1,000), 2017-18 (1.25%), and a single
# row headed 6/30/2018 for step 7, again $1,000 higher. A scan with a poor text layer of
# somebody else's making (63.991 for 63,991), so read by Vision.
D = 'contracts/pdf/dese-teacher-contract-fitchburg.pdf'
grid(D, 35, '2016', '2015-16 2.0%', FT, S(0, 6), (0.18, 0.33, 0, 1), 'ocr')
grid(D, 35, '2017', '2016-17 1.25%', FT, S(0, 7), (0.385, 0.545, 0, 1), 'ocr',
     vs=('2015-16 2.0%', 1.0125))
grid(D, 35, '2018', '2017-18 1.25%', FT, S(0, 7), (0.60, 0.76, 0, 1), 'ocr',
     vs=('2016-17 1.25%', 1.0125))
grid(D, 35, '2018', '6/30/2018', FT, ['7'], (0.805, 0.825, 0, 1), 'ocr')

# MONTY TECH, DESE's filing (2023-2026). "PROFESSIONAL SALARY SCHEDULE 2023-2024" and the two
# years after, one page each, printed sideways. Increases 4.00%, 3.00%, 3.00% (printed above
# each schedule). Columns I-VIII carry two names (p39): the
# academic definition first, then the vocational one. Columns V-VIII run to step 16.
D = 'contracts/pdf/dese-teacher-contract-montachusett.pdf'
MT = ['I: BS / Licensure', 'II: BS+15 / Licensure+15', 'III: BS+30 / Licensure+30',
      'IV: Masters or BS+45 / Licensure+45', 'V: M+15 / Licensure+60',
      'VI: M+30 / Licensure+90', 'VII: M+45 / BS', 'VIII: CAGS / Masters']
grid(D, 40, '2024', 'PROFESSIONAL SALARY SCHEDULE 2023-2024', MT, S(1, 16), (0.24, 0.66, 0.15, 0.95), 'ocr', 'sideways')
grid(D, 41, '2025', 'PROFESSIONAL SALARY SCHEDULE 2024-2025', MT, S(1, 16), (0.25, 0.67, 0.15, 0.95), 'ocr', 'sideways',
     vs=('PROFESSIONAL SALARY SCHEDULE 2023-2024', 1.03))
grid(D, 42, '2026', 'PROFESSIONAL SALARY SCHEDULE 2025-2026', MT, S(1, 16), (0.25, 0.67, 0.15, 0.95), 'ocr', 'sideways',
     vs=('PROFESSIONAL SALARY SCHEDULE 2024-2025', 1.03))

# (doc, page, fy or printed title, step, lane): (what word OCR returned, or None if it gave no figure for the
# cell, and what the page prints, read by eye off the rendered page). Every entry is a cell
# the arithmetic check flagged, the second reading did not confirm, or the grid left empty.
CORRECTIONS = {}
LUNF = 'contracts/pdf/dese-teacher-contract.pdf'
CORRECTIONS.update({
    (LUNF, 36, '2026', '2', 'Bach'): (None, '55080'),          # OCR: '5,080' (step 2 ran in)
})
# North Middlesex's filing is a poor scan; every cell below was read off a 2.6x render.
NMF = 'contracts/pdf/dese-teacher-contract-north-middlesex.pdf'
CORRECTIONS.update({
    (NMF, 24, '2019', '5', 'MA+60'): ('56402', '66402'),
    (NMF, 24, '2019', '9', 'MA+75'): ('29233', '79233'),
    (NMF, 24, '2019', '10', 'MA+30'): ('77022', '77622'),
    (NMF, 24, '2019', '2', 'MA+15'): (None, '55238'),
    (NMF, 24, '2019', '3', 'MA+30'): (None, '58590'),
    (NMF, 24, '2019', '12', 'MA+15'): (None, '81717'),
    (NMF, 24, '2019', '12', 'MA+30'): (None, '82945'),
    (NMF, 24, '2019', '13', 'MA+30'): (None, '85426'),
    (NMF, 24, '2020', '3', 'MA+75'): ('63371', '63871'),
    (NMF, 24, '2020', '4', 'MA'): ('50060', '60060'),
    (NMF, 24, '2020', '8', 'MA+60'): ('76167', '76187'),
    (NMF, 24, '2020', '12', 'MA+60'): ('85011', '88011'),
    (NMF, 24, '2020', '5', 'MA'): (None, '62461'),
    (NMF, 24, '2020', '8', 'BA+15'): (None, '68254'),
    (NMF, 24, '2020', '8', 'MA+45'): (None, '74790'),
    (NMF, 24, '2020', '9', 'MA+45'): (None, '77785'),
    (NMF, 24, '2020', '9', 'MA+75'): (None, '80818'),
    (NMF, 24, '2020', '13', 'MA+30'): (None, '87135'),
    (NMF, 24, '2021', '4', 'MA+60'): ('56426', '66426'),
    (NMF, 24, '2021', '6', 'MA+15'): ('67292', '67232'),
    (NMF, 24, '2021', '6', 'MA+75'): ('73285', '73286'),
    (NMF, 24, '2021', '7', 'MA+60'): ('24720', '74720'),
    (NMF, 24, '2021', '9', 'MA'): ('74523', '74533'),
    (NMF, 24, '2021', '9', 'MA+45'): ('79741', '79341'),
    (NMF, 24, '2021', '13', 'MA+30'): ('86878', '88878'),
    (NMF, 24, '2021', '3', 'MA+30'): (None, '60957'),
    (NMF, 24, '2021', '12', 'MA+30'): (None, '86296'),
})
FTD = 'contracts/pdf/dese-teacher-contract-fitchburg.pdf'
CORRECTIONS.update({
    (FTD, 35, '2017', '7', 'MA'): ('61862', '67862'),
})
MTF = 'contracts/pdf/dese-teacher-contract-montachusett.pdf'
CORRECTIONS.update({
    (MTF, 40, '2024', '9', 'VII: M+45 / BS'): (None, '82814'),
    (MTF, 40, '2024', '12', 'II: BS+15 / Licensure+15'): (None, '84059'),
    (MTF, 40, '2024', '12', 'VI: M+30 / Licensure+90'): (None, '88737'),
    (MTF, 41, '2025', '2', 'V: M+15 / Licensure+60'): (None, '63040'),
    (MTF, 41, '2025', '3', 'II: BS+15 / Licensure+15'): (None, '61550'),
    (MTF, 41, '2025', '3', 'VII: M+45 / BS'): (None, '67483'),
    (MTF, 41, '2025', '15', 'VII: M+45 / BS'): (None, '102729'),
    (MTF, 42, '2026', '9', 'VI: M+30 / Licensure+90'): ('36712', '86712'),
    (MTF, 42, '2026', '11', 'II: BS+15 / Licensure+15'): ('36902', '86902'),
})

# Cells word OCR read correctly that the second reading did not contain, each looked at on the
# rendered page: (doc, page, fy, step, lane) -> the figure printed. Labelled 'checked by eye'.
EYE_CHECKED = {
    (NMF, 24, '2019', '6', 'MA+45'): '67792',
    (NMF, 24, '2020', '7', 'MA+15'): '68553',
    (NMF, 24, '2021', '6', 'BA+15'): '64678',
    (FTD, 35, '6/30/2018', '7', 'MA+60'): '78729',   # the second reading ran it into the page number
    (MTF, 40, '2024', '6', 'VIII: CAGS / Masters'): '77411',
    (MTF, 40, '2024', '8', 'I: BS / Licensure'): '72906',
    (MTF, 41, '2025', '10', 'VI: M+30 / Licensure+90'): '86400',
    (MTF, 42, '2026', '5', 'I: BS / Licensure'): '69904',
    (MTF, 42, '2026', '15', 'VII: M+45 / BS'): '105811',
}

# ----------------------------------------------------------------------------- words
MONEY = re.compile(r'^\$?(\d{1,3}(?:[,.]\d{3})+)(?:[.,](\d{2}))?$')


def words_path(doc, page):
    stem = os.path.splitext(os.path.basename(doc))[0]
    return os.path.join(WORDS, '%s-p%02d.tsv' % (stem, page))


def make_ocr(doc, page):
    os.makedirs(WORDS, exist_ok=True)
    out = words_path(doc, page)
    r = subprocess.run(['swift', os.path.join(ROOT, 'scripts', 'ocr_words.swift'),
                        os.path.join(SRC, doc), out, str(page), str(page), '3'],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out):
        fail('Vision OCR failed on %s p%d: %s' % (doc, page, r.stderr[-300:]))


def load_words(doc, page, src):
    """[(text, x, y, w, h)] in page fractions, origin TOP-left, unrotated page frame."""
    out = []
    if src == 'ocr':
        p = words_path(doc, page)
        if not os.path.exists(p):
            fail('no word cache for %s p%d; run with --ocr' % (doc, page))
        with open(p, encoding='utf-8') as fh:
            for r in csv.DictReader(fh, delimiter='\t'):
                if int(r['page']) != page:
                    continue
                x, y, w, h = (float(r[k]) for k in ('x', 'y', 'w', 'h'))
                # Vision's origin is bottom-left; the box's y is its bottom edge.
                out.append((r['text'], x, 1 - y - h, w, h))
    else:
        import pdfplumber
        with pdfplumber.open(os.path.join(SRC, doc)) as pdf:
            pg = pdf.pages[page - 1]
            W, H = float(pg.width), float(pg.height)
            for wd in pg.extract_words(keep_blank_chars=False, use_text_flow=False):
                out.append((wd['text'], wd['x0'] / W, wd['top'] / H,
                            (wd['x1'] - wd['x0']) / W, (wd['bottom'] - wd['top']) / H))
    return out


def split_tokens(words):
    """Split a box that OCR ran together ('57,793|60,502') proportionally by characters."""
    out = []
    for text, x, y, w, h in words:
        parts = [p for p in re.split(r'[|]', text)]
        if len(parts) == 1:
            out.append((text, x, y, w, h))
            continue
        n = max(1, len(text))
        pos = 0
        for p in parts:
            if p:
                out.append((p, x + w * pos / n, y, w * len(p) / n, h))
            pos += len(p) + 1
    return out


def merge_split(toks):
    """Join a figure a reader split in two ('$67,1' + '45', pdfplumber on North Middlesex):
    two boxes on one line, nearly touching, that are a figure together and not apart."""
    toks = sorted(toks, key=lambda t: (round(t[2] + t[4] / 2, 3), t[1]))
    out = []
    for t in toks:
        if out:
            p = out[-1]
            same_line = abs((p[2] + p[4] / 2) - (t[2] + t[4] / 2)) < max(p[4], t[4]) / 2
            gap = t[1] - (p[1] + p[3])
            if (same_line and -0.002 < gap < 0.006 and not money(p[0]) and not money(t[0])
                    and money(p[0] + t[0])):
                out[-1] = (p[0] + t[0], p[1], p[2], t[1] + t[3] - p[1], max(p[4], t[4]))
                continue
        out.append(t)
    return out


def money(text):
    t = text.strip().rstrip('L|lI.').replace('S', '$') if text else text
    m = MONEY.match(t)
    if not m:
        return None
    whole = re.sub(r'[,.]', '', m.group(1))
    # A DOLLAR SIGN READ AS A DIGIT. Vision reads "$52,124" as "552,124" on the North
    # Middlesex scan. No teacher scale here reaches $200,000, so a six-figure reading above
    # that whose first digit is a look-alike (5, 8, 3) has its first digit dropped. Named here
    # because it is a rule about the instrument, not about any one cell.
    if len(whole) == 6 and int(whole) >= 200000 and whole[0] in '583':
        whole = whole[1:]
    if len(whole) < 5 or len(whole) > 6:
        return None
    return whole + ('.' + m.group(2) if m.group(2) else '')


def to_frame(tok, frame):
    """(text, row coordinate, column coordinate, column extent) in the reading frame."""
    text, x, y, w, h = tok
    cx, cy = x + w / 2, y + h / 2
    if frame == 'normal':
        return text, cy, cx
    if frame == 'sideways':     # a table printed sideways: its steps run along the page's x
        return text, cx, 1 - cy
    fail('unknown frame ' + frame)


# ----------------------------------------------------------------------------- one grid
def read_grid(g):
    """(cells, problem). cells = {(step, lane): value}."""
    toks = [to_frame(t, g['frame']) for t in merge_split(split_tokens(load_words(g['doc'], g['page'], g['src'])))]
    r0, r1, c0, c1 = g['region']
    toks = [t for t in toks if r0 <= t[1] <= r1 and c0 <= t[2] <= c1]
    figs = [(money(t[0]), t[1], t[2]) for t in toks]
    figs = [f for f in figs if f[0]]
    if len(figs) < len(g['lanes']):
        return None, 'only %d figures found in the region' % len(figs)
    lanes, steps = g['lanes'], g['steps']

    # COLUMNS: split the figures' column coordinates at the widest gaps.
    cs = sorted(f[2] for f in figs)
    gaps = sorted(range(1, len(cs)), key=lambda i: cs[i] - cs[i - 1], reverse=True)[:len(lanes) - 1]
    bounds = sorted(gaps)
    groups, start = [], 0
    for b in bounds + [len(cs)]:
        groups.append(cs[start:b])
        start = b
    centres = [statistics.median(gp) for gp in groups]
    if len(centres) != len(lanes):
        return None, 'figures fall into %d columns, the header has %d lanes' % (len(centres), len(lanes))
    width = min((centres[i] - centres[i - 1]) for i in range(1, len(centres))) if len(centres) > 1 else 1
    # A column split at a gap no wider than the spacing within a column is not a column.
    within = max((gp[-1] - gp[0]) for gp in groups)
    if len(centres) > 1 and within > width * 0.75:
        return None, 'columns are not separable (spread %.3f against spacing %.3f)' % (within, width)

    # ROWS: measure the slope between each figure and its right-hand neighbour, then band.
    # A rough pitch from the layout's own step count bounds what counts as the same row, so
    # a neighbour on the next row down cannot pollute the slope.
    rough = (max(f[1] for f in figs) - min(f[1] for f in figs)) / max(1, len(steps) - 1)
    slopes = []
    for f in figs:
        right = [o for o in figs if 0 < o[2] - f[2] < width * 1.5 and abs(o[1] - f[1]) < rough * 0.35]
        if right:
            o = min(right, key=lambda o: o[2] - f[2])
            slopes.append((o[1] - f[1]) / (o[2] - f[2]))
    slope = statistics.median(slopes) if slopes else 0.0
    adj = sorted(((f[1] - slope * f[2]), f) for f in figs)
    ys = [a for a, _ in adj]
    diffs = [ys[i] - ys[i - 1] for i in range(1, len(ys))]
    big = [d for d in diffs if d > rough * 0.5]
    pitch = statistics.median(big) if big else rough
    band = pitch / 2
    rows, cur = [], [adj[0]]
    for a in adj[1:]:
        if a[0] - cur[-1][0] > band:
            rows.append(cur)
            cur = [a]
        else:
            cur.append(a)
    rows.append(cur)
    if len(rows) != len(steps):
        return None, '%d rows of figures, the page prints %d steps' % (len(rows), len(steps))

    # STEP LABELS, where the page prints them as separate words, must match their rows.
    labels = [(t[0].strip(), t[1] - slope * t[2]) for t in toks
              if re.fullmatch(r'\d{1,2}', t[0].strip()) and t[2] < centres[0] - width * 0.4]
    # One misread label (Vision reads "Step 9" as "3" on North Middlesex's scan) is tolerated
    # when every other labelled row agrees, because the others then fix the row order; two
    # are not.
    cells, wrong, agree = {}, [], 0
    for i, row in enumerate(rows):
        yrow = statistics.median(a for a, _ in row)
        near = [lab for lab, yy in labels if abs(yy - yrow) < band]
        if near and steps[i] not in near:
            wrong.append('row %d carries step label %s, the layout says step %s' % (i + 1, near, steps[i]))
        elif near:
            agree += 1
    if len(wrong) > 1 or (wrong and agree < len(steps) - 2):
        return None, '; '.join(wrong)
    for i, row in enumerate(rows):
        for _, f in row:
            j = min(range(len(centres)), key=lambda k: abs(centres[k] - f[2]))
            key = (steps[i], lanes[j])
            if key in cells:
                return None, 'two figures in step %s, lane %s' % key
            cells[key] = f[0]
    return cells, None


def second_reading(doc, page):
    """Every figure in the LINE-level OCR of the page (sources/contracts/txt/<doc>.txt, made by
    pdf_kind.extract_text at a different scale and grouping). A cell the word-level OCR read
    that this independent pass also contains is 'confirmed'; one it does not contain is shown
    as unconfirmed, and every one of those was looked at on the rendered page."""
    stem = os.path.splitext(os.path.basename(doc))[0]
    txt = os.path.join(SRC, 'contracts', 'txt', stem + '.txt')
    text, cur, keep = open(txt, encoding='utf-8').read(), None, []
    for line in text.splitlines():
        m = re.match(r'===PAGE (\d+)===$', line)
        if m:
            cur = int(m.group(1))
        elif cur == page:
            keep.append(line)
    out = set()
    for tok in re.split(r'[\s|]+', '\n'.join(keep)):
        v = money(tok)
        if v:
            out.add(v)
    return out


def num(v):
    return float(v)


def check(g, cells):
    """{(step, lane): flag} for cells that do not rise along steps or across lanes."""
    flags = {}
    for lane in g['lanes']:
        seq = [(s, cells[(s, lane)]) for s in g['steps'] if (s, lane) in cells]
        for (s0, v0), (s1, v1) in zip(seq, seq[1:]):
            if num(v1) <= num(v0):
                flags[(s1, lane)] = 'not above step %s in its lane (%s)' % (s0, v0)
    for s in g['steps']:
        seq = [(lane, cells[(s, lane)]) for lane in g['lanes'] if (s, lane) in cells]
        for (l0, v0), (l1, v1) in zip(seq, seq[1:]):
            if num(v1) <= num(v0):
                f = 'not above lane %s at its step (%s)' % (l0, v0)
                flags[(s, l1)] = (flags[(s, l1)] + '; ' + f) if (s, l1) in flags else f
    return flags


# ----------------------------------------------------------------------------- build
def hits(which, g):
    """Does a correction's year-or-title field name this grid? A fiscal year is enough only
    when no other grid on the same page shares it; otherwise the printed title is required."""
    if which == g['schedule']:
        return True
    if which != g['fy']:
        return False
    twins = [o for o in L if o['doc'] == g['doc'] and o['page'] == g['page'] and o['fy'] == g['fy']
             and o['schedule'] != g['schedule']]
    if twins:
        fail('a correction names FY%s on %s p%d, which prints two schedules for that year; '
             'name it by title' % (which, g['doc'], g['page']))
    return True


def build():
    rows, used, refused = [], set(), {}
    for g in L:
        c = CONTRACTS[g['doc']]
        cells, problem = read_grid(g)
        if problem:
            refused.setdefault(g['doc'], []).append('%s (p%d): %s' % (g['schedule'], g['page'], problem))
            continue
        how = {k: 'text layer' for k in cells}
        if g['src'] == 'ocr':
            second = second_reading(g['doc'], g['page'])
            for k, v in cells.items():
                how[k] = ('ocr, confirmed by a second reading' if v in second
                          else 'ocr, NOT confirmed by a second reading')
        for key, want in EYE_CHECKED.items():
            d, p, fy, step, lane = key
            if d == g['doc'] and p == g['page'] and hits(fy, g) and (step, lane) in cells:
                if cells[(step, lane)] != want:
                    fail('eye check %r expects %s, OCR now gives %s' % (key, want, cells[(step, lane)]))
                how[(step, lane)] = 'ocr, not in the second reading, checked by eye'
                used.add(key)
        for key, (was, now) in CORRECTIONS.items():
            d, p, fy, step, lane = key
            if d == g['doc'] and p == g['page'] and hits(fy, g) and step in g['steps'] \
                    and lane in g['lanes']:
                if cells.get((step, lane)) != was:
                    fail('correction %r expects OCR %s, got %s' % (key, was, cells[(step, lane)]))
                cells[(step, lane)] = now
                how[(step, lane)] = ('by eye off the page (word OCR read %s)' % was if was else
                                     'by eye off the page (word OCR gave no figure)')
                used.add(key)
        flags = check(g, cells)
        for s in g['steps']:
            for lane in g['lanes']:
                if (s, lane) in cells:
                    rows.append(dict(district=c['district'], org_code=c['org'],
                                     contract_period=c['period'], fy=g['fy'],
                                     schedule=g['schedule'], step=s, lane=lane,
                                     salary=cells[(s, lane)], doc=g['doc'], page=g['page'],
                                     read=how[(s, lane)], flag=flags.get((s, lane), '')))
    # THE STATED-INCREASE CHECK, across schedules of one document.
    by = {}
    for r in rows:
        by.setdefault((r['doc'], r['schedule']), {})[(r['step'], r['lane'])] = r
    for g in L:
        if not g['vs']:
            continue
        prior, factor = g['vs']
        before = by.get((g['doc'], prior))
        if before is None:
            fail('%s: no schedule titled %r to compare with' % (g['schedule'], prior))
        for key, r in by.get((g['doc'], g['schedule']), {}).items():
            if key[0] not in g['steps'] or key not in before:
                continue
            want = float(before[key]['salary']) * factor
            if abs(float(r['salary']) - want) > 2:
                f = 'not %s x %s (%.0f)' % (prior, factor, want)
                r['flag'] = (r['flag'] + '; ' + f) if r['flag'] else f
    unused = (set(CORRECTIONS) | set(EYE_CHECKED)) - used
    if unused:
        fail('corrections that matched no cell: %r' % sorted(unused))
    docs = []
    for doc, c in CONTRACTS.items():
        mine = [r for r in rows if r['doc'] == doc]
        fys = sorted({r['fy'] for r in mine})
        layouts = [g for g in L if g['doc'] == doc]
        if refused.get(doc):
            status = 'partly read' if mine else 'not read'
        elif not layouts:
            status = 'not read'
        else:
            status = 'read'
        note = c['note']
        if refused.get(doc):
            note = (note + ' REFUSED: ' + ' | '.join(refused[doc])).strip()
        docs.append(dict(district=c['district'], org_code=c['org'], doc=doc,
                         publisher=c['publisher'], upstream=c['upstream'],
                         publisher_filename=c['filename'], contract_period=c['period'],
                         pdf_kind=c['kind'], fiscal_years_read=' '.join(fys),
                         cells=len(mine), status=status, note=note))
    return rows, docs


def render(rows, fields):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--ocr', action='store_true')
    ap.add_argument('--dump', nargs=2, metavar=('DOC', 'PAGE'))
    ap.add_argument('--frame', default='normal')
    ap.add_argument('--src', default='text')
    a = ap.parse_args()
    if a.dump:
        doc, page = a.dump[0], int(a.dump[1])
        for t in sorted((to_frame(t, a.frame) for t in split_tokens(load_words(doc, page, a.src))),
                        key=lambda t: (round(t[1], 2), t[2])):
            print('%.3f %.3f %s' % (t[1], t[2], t[0]))
        return
    if a.ocr:
        for doc, page in sorted({(g['doc'], g['page']) for g in L if g['src'] == 'ocr'}):
            make_ocr(doc, page)
            print('ocr', doc, page)
    rows, docs = build()
    out, dout = render(rows, FIELDS), render(docs, DOC_FIELDS)
    if a.check:
        bad = [p for p, s in ((OUT, out), (DOCS_OUT, dout))
               if not os.path.exists(p) or open(p, encoding='utf-8').read() != s]
        if bad:
            fail('stale: %s' % ', '.join(os.path.relpath(p, ROOT) for p in bad))
        print('ok: %d cells, %d contracts, both files reproduce' % (len(rows), len(docs)))
        return
    for p, s in ((OUT, out), (DOCS_OUT, dout)):
        with open(p + '.tmp', 'w', encoding='utf-8', newline='') as fh:
            fh.write(s)
        os.replace(p + '.tmp', p)
    flagged = [r for r in rows if r['flag']]
    print('wrote %d cells from %d contracts; %d flagged' % (len(rows), len(docs), len(flagged)))
    for d in docs:
        print('  %-28s %-12s %-40s %s' % (d['district'][:28], d['status'], d['fiscal_years_read'],
                                          d['doc'].split('/')[-1]))
    for r in flagged:
        print('  FLAG %s %s %s step %s %s = %s: %s' % (r['district'], r['fy'], r['schedule'],
                                                     r['step'], r['lane'], r['salary'], r['flag']))


if __name__ == '__main__':
    main()
