#!/usr/bin/env python3
"""Where a department's report exists and we still have no headcount from it.

    python3 scripts/build_staffing_coverage.py [--check]

Writes `sources/data/staffing-coverage.csv` and `notes/generated/STAFFING-COVERAGE.md`.

TJ, 22 September 2026, after finding the Police roster in FY2016 and the Building
Department's staff in FY2022 by opening the book:

    *"we HAVE to assume every department and every annual report contains the same
    information. That's the baseline. no more assuming the data isnt there. it IS there.
    it has been every single time. we just haven't found it."*

He has been right every time, and the reason is always the same: the town says the same
thing in a different SHAPE, and a reader keyed to last year's shape reports an absence.
The Building Department alone writes its four staff three ways in three consecutive years
-- a colon-list, `X serves as the Y` prose, and `The department consists of X who is the
Y` -- and each new shape looked like a year the department published nothing.

So this file exists to stop that being invisible. For every department we have EVER got a
count from, it marks each year:

    a number       the department's own pages give one
    talks          its report mentions staff and states no number
    quiet          its report never mentions staff at all
    NONE           THE TOWN SAYS the department filed no report that year
    -              the department is not in that year's contents at all

TJ, 22 September 2026: *"we have a dept list right? I assume EVERY department shows up
here... I dont see Facilities in your list for example. Also, i see big gaps in your table
but i still dont know why."*

BOTH COMPLAINTS HAD THE SAME CAUSE: the department list was one I had typed. Facilities
was missing because I did not think of it, and a gap had no reason beside it because
nothing knew what the gap was. The town publishes its own list on the contents page of
every annual report, with each report's page range and the words `No Report Submitted`
where there is none -- so the list is now theirs, every department is visited, and each
empty cell says which kind of empty it is.
"""
import argparse
import collections
import csv
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
PAGES = os.path.join(ROOT, 'sources', 'town-budget', 'pages')
OUT_CSV = os.path.join(ROOT, 'sources', 'data', 'staffing-coverage.csv')
OUT_MD = os.path.join(ROOT, 'notes', 'generated', 'STAFFING-COVERAGE.md')

# How each department's own report announces itself. Several spellings each, because the
# heading is not stable either -- `DEPARTMENT OF PUBLIC WORKS` and `DPW` and `HIGHWAY
# DIVISION` are the same department in different books.
INDEX = os.path.join(ROOT, 'sources', 'data', 'report-index.csv')
SECTION = os.path.join(ROOT, 'sources', 'data', 'staffing-by-section.csv')
STAFFING = os.path.join(ROOT, 'sources', 'data', 'department-staffing.csv')

# Contents entries that are TABLES an office prints, not a department that employs people.
NOT_A_DEPT = re.compile(
    r'balance sheet|fund balance|revenue chart|appropriations|receivable|outstanding debt'
    r'|repayment schedule|gross wages|town meeting|election|vital|profile|in memoriam'
    r'|officials|office hours|trust fund|capital project|special revenue|collection of'
    r'|classification|indebtedness|cash as of|summary|report of the|excerpt|chart'
    r'|statistics|index|warrant|dedication|memoriam', re.I)

# One department, many spellings -- the scanner and fifteen different editors. Keyed on
# the first pattern that matches, so the order matters only where two could both hit.
CANON = [
    # SCHOOL FACILITIES IS NOT THE TOWN'S FACILITIES DEPARTMENT, and a rule matching
    # `facilit` folded them into one row. The Town Charter draws the line itself: the
    # Town Manager's jurisdiction covers all town property `except property under the
    # control of the school committee and the conservation commission`. FY2012's `John
    # Londa, Facilities Director` sits under a SCHOOL FACILITIES heading and is the
    # district's, not the town's.
    (r'school facilit', 'School Facilities'),
    (r'public library|library', 'Library'),
    (r'public works|^dpw', 'Department of Public Works'),
    (r'council on aging|senior center', 'Council on Aging'),
    (r'fire department|fire rescue', 'Fire Department'),
    (r'police department', 'Police Department'),
    (r'building department|building commissioner|inspectional', 'Building Department'),
    (r'information technology', 'Information Technology'),
    (r'assessor', 'Board of Assessors'),
    (r'board of health', 'Board of Health'),
    (r'nashoba', 'Nashoba Associated Boards of Health'),
    (r'cemetery', 'Cemetery Commission'),
    (r'conservation', 'Conservation Commission'),
    (r'planning board', 'Planning Board'),
    (r'zoning board', 'Zoning Board of Appeals'),
    (r'sewer', 'Sewer Commission'),
    (r'veteran', "Veterans' Services"),
    (r'historical', 'Historical Commission'),
    (r'cultural council', 'Cultural Council'),
    (r'finance committee', 'Finance Committee'),
    (r'town manager|selectmen|select board', 'Town Manager'),
    (r'town clerk', 'Town Clerk'),
    (r'treasurer|tax collector', 'Treasurer / Collector'),
    (r'public access', 'Lunenburg Public Access'),
    (r'facilit', 'Facilities'),
    (r'park|recreation', 'Parks & Recreation'),
    (r'housing authority', 'Housing Authority'),
    (r'capital planning', 'Capital Planning Committee'),
    (r'montachusett|monty tech', 'Montachusett Regional Vocational'),
    (r'lunenburg public schools|superintendent', 'Schools'),
    (r'primary school', 'Lunenburg Primary School'),
    (r'turkey hill', 'Turkey Hill Elementary School'),
    (r'middle school', 'Lunenburg Middle School'),
    (r'high school', 'Lunenburg High School'),
    (r'senior property tax', 'Senior Property Tax Work-Off'),
    (r'special services|student support', 'Special Services'),
    (r'architectural preservation', 'Architectural Preservation District'),
    (r'green communit', 'Green Communities Committee'),
    (r'agricultural', 'Agricultural Commission'),
    (r'open space', 'Open Space Advisory Committee'),
    (r'trust fund commission', 'Trust Fund Commission'),
    (r'personnel (?:board|committee)', 'Personnel Board'),
]


def canon(name):
    for pat, out in CANON:
        if re.search(pat, name, re.I):
            return out
    return None


def years():
    out = []
    for f in sorted(glob.glob(os.path.join(PAGES, 'FY*.ocr.txt'))):
        m = re.search(r'FY(\d{4})\.ocr', f)
        if m:
            out.append(m.group(1))
    return out


def counts(with_form=False):
    """{(department, fy): people} from every reader that produces one.

    THE ONE PLACE THE READERS ARE MERGED. The personnel page used to do its own merging
    and drifted from this grid within an hour -- the page said Fire had nine years and
    the grid said fifteen, and both were reading the same archive. `town_personnel_data`
    now calls this, so a department cannot be counted one way on the page and another way
    on the page that audits the page.
    """
    out, form = {}, {}
    # ORDER IS PRECEDENCE, and one source had to be narrowed. `department-staffing.csv`
    # stores the Fire Department's CAREER count in its own column beside the on-call
    # range, so taking that column alone put 7 in FY2019 next to 40 in FY2022 -- two
    # different quantities in one row of the same table, which is the error this whole
    # project is built to avoid. The section reader adds the low end of the range and is
    # the one that produces a comparable figure, so the career-only rows are skipped.
    for path, dep, ppl, ok in ((SECTION, 'department', 'people', lambda r: r['people']),
                               (STAFFING, 'department', 'career',
                                lambda r: r['parsed'] == 'yes' and r['career']
                                and 'on-call' not in r['measure'])):
        if not os.path.exists(path):
            continue
        for r in csv.DictReader(open(path, encoding='utf-8')):
            if not ok(r):
                continue
            d = canon(r[dep])
            if d and (d, r['fy']) not in out:
                out[(d, r['fy'])] = int(r[ppl])
                form[(d, r['fy'])] = r.get('form') or r.get('measure') or ''
    # The rosters are a reader of their own: Police and Fire, counted by name.
    rost = os.path.join(ROOT, 'sources', 'data', 'department-rosters.csv')
    if os.path.exists(rost):
        n = collections.Counter()
        for r in csv.DictReader(open(rost, encoding='utf-8')):
            n[(canon(r['department']), r['fy'])] += 1
        for k, v in n.items():
            if k[0] and k not in out:
                out[k] = v
                form[k] = 'every member of staff, named on its roster'
    return (out, form) if with_form else out


def build():
    fys = years()
    have = counts()
    filed, reason = {}, {}
    for r in csv.DictReader(open(INDEX, encoding='utf-8')):
        if NOT_A_DEPT.search(r['department']):
            continue
        d = canon(r['department'])
        if not d:
            continue
        filed[(d, r['fy'])] = r['state']
    for r in csv.DictReader(open(SECTION, encoding='utf-8')):
        d = canon(r['department'])
        if d and r['reason']:
            reason.setdefault((d, r['fy']), r['reason'])
    depts = sorted({d for d, _ in filed} | {d for d, _ in have})
    rows = []
    for d in depts:
        for fy in fys:
            n = have.get((d, fy))
            st = filed.get((d, fy))
            if n is not None:
                state = 'count'
            elif st == 'no report submitted':
                state = 'town says no report submitted'
            elif st == 'report':
                state = reason.get((d, fy), 'report filed, nothing read from it')
            else:
                state = 'not in that year’s contents'
            rows.append(dict(department=d, fy=fy, people='' if n is None else n,
                             state=state, report_pages=''))
    return fys, depts, rows


def render(fys, depts, rows):
    by = {(r['department'], r['fy']): r for r in rows}
    MARK = {'count': None,
            'town says no report submitted': 'NONE',
            'mentions staff, states no number': 'talks',
            'no mention of staff on its own pages': 'quiet',
            'report filed, nothing read from it': '?',
            'pages not in our text of the book': '??',
            'not in that year’s contents': '-'}
    t = ['# Every department the town lists, and what we have for each\n\n']
    t.append('Generated by `scripts/build_staffing_coverage.py` from the town’s OWN '
             'contents page (`report-index.csv`), so the department list is theirs and '
             'not ours.\n\n')
    t.append('- a **number** — its own pages give one\n'
             '- **talks** — its report mentions staff and states no number\n'
             '- **quiet** — its report never mentions staff\n'
             '- **NONE** — the town says the department filed no report that year\n'
             '- **-** — not in that year’s contents at all\n\n')
    t.append('| department | ' + ' | '.join(f[-2:] for f in fys) + ' |\n')
    t.append('|---|' + '---|' * len(fys) + '\n')
    for d in depts:
        cells = []
        for fy in fys:
            r = by[(d, fy)]
            cells.append(str(r['people']) if r['state'] == 'count'
                         else (MARK.get(r['state']) or '?'))
        t.append('| %s | %s |\n' % (d, ' | '.join(cells)))
    n = collections.Counter(r['state'] for r in rows)
    t.append('\n')
    for k, v in n.most_common():
        t.append('- **%d** %s\n' % (v, k))
    t.append('\nEvery cell that is not a number is a TO-DO or an explanation, never a '
             'finding. `talks` is the richest seam: the report is about the department’s '
             'own staff and we have not got a number out of it yet.\n')
    return ''.join(t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    fys, depts, rows = build()
    md = render(fys, depts, rows)
    if a.check:
        old = open(OUT_MD, encoding='utf-8').read() if os.path.exists(OUT_MD) else ''
        if old != md:
            print('STALE %s' % OUT_MD)
            return 1
        return 0
    with open(OUT_CSV, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['department', 'fy', 'people', 'state',
                                           'report_pages'])
        w.writeheader()
        w.writerows(rows)
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    open(OUT_MD, 'w', encoding='utf-8').write(md)
    print(md)
    return 0


if __name__ == '__main__':
    sys.exit(main())
