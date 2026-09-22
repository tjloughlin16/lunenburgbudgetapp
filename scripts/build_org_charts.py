#!/usr/bin/env python3
"""Every department, board and school as an ORG CHART: who held which role, by year.

    python3 scripts/build_org_charts.py [--check]

Writes `sources/data/org-chart.csv` and `fy28/public/data/org-charts.json`.

TJ, 22 September 2026: *"I want to BUILD the org chart for every department, every board,
and the school, on one page 'Town Wide Org Charts'. Selectable by dropdown... and we can
do it for each FY... THEN we have the true mapping of personnel"*, and: *"this helps the
data model because the backend needs to map dept -> people in various roles."*

WHY THIS IS A TEST AND NOT JUST A PAGE. Every other reading in this project counts things:
how many staff, how many seats, how much money. A chart of WHO IS IN WHICH ROLE cannot be
counted into existence -- it either joins a department to named people with named roles or
it visibly does not, per year. That makes it the sharpest check the data model has, and it
found its first defect before a line of the page was written: 57 rows across ten years
hold a `person` like `Follow us on Facebook at...` under a `post` like
`TOTAL AREA- 26.63 MILES`, which is the town PROFILE page bleeding into the officials
listing. Those are rejected here and counted, never drawn.

AND IT IS THE FIRST ONE THAT EXISTS. TJ: *"not every department posts one publicly
(<cough> schools) so this is the first ever publicly available org chart for many
departments outside the annual report of hundreds of pages."* The material has always been
public; it has never been assembled.

FOUR SOURCES, ONE SHAPE. Each row is (fy, unit, section, role, person, status):

  town-personnel.csv       boards, committees and appointed officers, with the vacancies
                           the listing itself states
  department-rosters.csv   Police and Fire by name and rank, read off two- and
                           three-column pages
  staff-roster-entries.csv the four schools, by name and position
  department-staffing.csv  the departments that name their staff in prose -- the Council
                           on Aging, Building, IT -- and the two that state an
                           ESTABLISHMENT instead, the DPW and the Assessing office

STATUS IS NOT DECORATION. `filled` is a named person. `vacant` is a seat or post the town
itself prints as empty. `post` is an establishment position with no name attached, which
is the DPW's and the Assessing office's whole form -- and the distinction between a post
and a person is the one this project got wrong until 22 September.
"""
import argparse
import collections
import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
DATA = os.path.join(ROOT, 'sources', 'data')
OUT_CSV = os.path.join(DATA, 'org-chart.csv')
OUT_JSON = os.path.join(ROOT, 'fy28', 'public', 'data', 'org-charts.json')
FIELDS = ['fy', 'unit', 'unit_kind', 'subunit', 'section', 'role', 'person',
          'status', 'source']

# THE PROFILE PAGE IS NOT A BOARD. `TOTAL AREA- 26.63 MILES` and `Follow us on Facebook`
# come off the town's own statistics page, which sits inside the front matter the
# officials listing is read from.
JUNK = re.compile(r'https?://|facebook|instagram|follow us|@|^\W*$'
                  r'|\bMILES\b|\bTOTAL AREA\b|^\d+[\d,.]*$', re.I)
VACANT = re.compile(r'^\(?\s*(vacan\w*|open|unfilled|tbd)\s*\)?$', re.I)

# A LINE OF THE LISTING THAT IS NOT A POST. Found by building the chart and reading the
# unit list, which is the point of building it: `Terms Are For One Year Unless Otherwise
# Indicated.` is the listing's own footnote, and `Associate Members` is a SUB-HEADING
# inside a board -- the Planning Board and the Zoning Board of Appeals both print one --
# so promoting it to a unit invents a body the town does not have.
NOT_A_POST = re.compile(r'^terms are for|^associate members|^\W|^\d|^(lull|4vlv|got advisors)$'
                        r'|^senior citizen property tax work-off program', re.I)

# ONE POST, SEVERAL SPELLINGS. Every pair here was found by normalising the unit names and
# looking at what collided; each is the town's own typography or the scanner's, not a
# distinction the town draws.
ALIAS = {
    'town clock winders': 'Town Clockwinders',
    'town hall clockwinders': 'Town Clockwinders',
    'clock winders': 'Town Clockwinders',
    'fire chief/ emergency managementdirector/ forest warden':
        'Fire Chief / Emergency Management Director / Forest Warden',
    'fire chief/emergency managementdirector/forest warden':
        'Fire Chief / Emergency Management Director / Forest Warden',
    'fire chief/ emergency management director/ forest warden':
        'Fire Chief / Emergency Management Director / Forest Warden',
    'mericans with disabilities committee - - 3 yea':
        'Americans with Disabilities Committee',
}


# THE MEMBERSHIP IS NOT PART OF THE NAME. The listing prints `COUNCIL ON AGING- - (11
# MEMBERS)` in some years and `COUNCIL ON AGING` in others, so the same board arrived as
# two bodies with 78 and 35 rows. The stated size is already read into `stated_members`
# by extract_personnel.py; carrying it in the title as well splits the board in half.
SIZE_SUFFIX = re.compile(r'\s*[-—,]*\s*\(?\s*(?:no less than\s*)?\d+\s*'
                         r'(?:members?|member|yrs?|years?)[^)]*\)?\s*$', re.I)


def canon_unit(name, kind):
    """One name per body. Case is not a distinction; `kind` is.

    `Council on Aging` the department and `Council On Aging` the board are two real
    things -- paid staff and an appointed volunteer board -- and they must not be told
    apart by a capital O. The kind carries the difference and the name is normalised.
    """
    name = SIZE_SUFFIX.sub('', re.sub(r'\s+', ' ', name).strip()).strip(' -—,')
    key = name.lower()
    if key in ALIAS:
        return ALIAS[key]
    return name


def _rows_officials():
    p = os.path.join(DATA, 'town-personnel.csv')
    out, bad = [], 0
    if not os.path.exists(p):
        return out, bad
    for r in csv.DictReader(open(p, encoding='utf-8')):
        post, who = (r['post'] or '').strip(), (r['person'] or '').strip()
        if JUNK.search(post) or JUNK.search(who) or NOT_A_POST.match(post):
            bad += 1
            continue
        kind = ('board' if 'board seat' in r['kind'] else 'officer')
        if who:
            out.append(dict(fy=r['fy'], unit=canon_unit(post.title(), kind),
                            unit_kind=kind, subunit='', section='',
                            role=r['kind'], person=who,
                            status='vacant' if VACANT.match(who) else 'filled',
                            source='officials listing p%s' % r['page']))
        for _ in range(int(r['vacancies'] or 0)):
            out.append(dict(fy=r['fy'], unit=canon_unit(post.title(), kind),
                            unit_kind=kind, subunit='', section='',
                            role=r['kind'], person='', status='vacant',
                            source='officials listing p%s' % r['page']))
    return out, bad


def _rows_rosters():
    p = os.path.join(DATA, 'department-rosters.csv')
    out = []
    if not os.path.exists(p):
        return out
    for r in csv.DictReader(open(p, encoding='utf-8')):
        who = (r['name'] or '').strip()
        out.append(dict(fy=r['fy'], unit=r['department'], unit_kind='department',
                        subunit='',
                        section=(r['section'] or '').strip(), role=(r['rank'] or '').strip(),
                        person='' if VACANT.match(who) else who,
                        status='vacant' if VACANT.match(who) else 'filled',
                        source='department roster p%s' % r['page']))
    return out


SCHOOL = {'primary': 'Lunenburg Primary School', 'turkey-hill': 'Turkey Hill Elementary School',
          'middle': 'Lunenburg Middle School', 'high': 'Lunenburg High School',
          'central-office': 'School Central Office', 'passios': 'T.C. Passios Elementary School',
          'monty-tech': 'Montachusett Regional Vocational Technical School'}


def _rows_schools():
    """The district as ONE unit, each school a SUBUNIT inside it.

    TJ: *"the school org chart needs to be the FULL school, with sub-selections for each
    school. i want to see the whole thing in one place."* He is right about the shape:
    Lunenburg Public Schools is one organisation with four buildings, and splitting it
    into four units made the district the only body on this page you could not see whole.
    A principal belongs to a school; a superintendent belongs to none of them.

    Montachusett Regional is NOT folded in. It is a separate district that Lunenburg sends
    students to, and putting its staff inside Lunenburg's chart would be a claim about who
    employs whom.
    """
    p = os.path.join(DATA, 'staff-roster-entries.csv')
    out = []
    if not os.path.exists(p):
        return out
    for r in csv.DictReader(open(p, encoding='utf-8')):
        who = (r['name'] or '').strip()
        school = SCHOOL.get(r['school'], r['school'].title())
        # The key is `monty-tech`, not `montachusett` -- checking for the long
        # form silently folded a separate district into Lunenburg's chart.
        regional = re.search(r'monty|montachusett', r['school'], re.I) is not None
        out.append(dict(fy=r['fy'],
                        unit=school if regional else 'Lunenburg Public Schools',
                        unit_kind='school',
                        subunit='' if regional else school,
                        section=(r['grade_or_dept'] or '').strip(),
                        role=(r['position'] or r['role_raw'] or '').strip(),
                        person='' if VACANT.match(who) else who,
                        status='vacant' if VACANT.match(who) else 'filled',
                        source='school roster p%s' % r['page']))
    return out


def _rows_prose():
    """The departments that NAME their staff in prose, and the two that state posts."""
    p = os.path.join(DATA, 'department-staffing.csv')
    out = []
    if not os.path.exists(p):
        return out
    for r in csv.DictReader(open(p, encoding='utf-8')):
        if r['parsed'] != 'yes' or not r['positions']:
            continue
        parts = [x.strip() for x in r['positions'].split(';') if x.strip()]
        establishment = 'establishment' in r['measure']
        for part in parts:
            m = re.match(r'^(\d+)\s+(.*)$', part)
            n, label = (int(m.group(1)), m.group(2)) if m else (1, part)
            for _ in range(n):
                out.append(dict(
                    fy=r['fy'], unit=r['department'], unit_kind='department',
                    subunit='', section='',
                    role=label if establishment else '',
                    person='' if establishment else label,
                    # AN ESTABLISHMENT POST IS NOT A PERSON. The DPW and the Assessing
                    # office publish posts and never say who fills them, and the Assessing
                    # office's own FY2024 report -- "fully staffed for the first time in
                    # over a year" -- is why that distinction is kept rather than flattened.
                    status='post' if establishment else 'filled',
                    source='department report p%s' % r['page']))
    return out


KIND_SUFFIX = {'department': 'staff', 'board': 'board', 'officer': 'appointed post',
               'school': 'schools'}


def _disambiguate(rows):
    """A name that exists under two KINDS gets the kind in its title.

    TJ: *"im confused. council on aging... you said they were all paid positions?! They
    are showing as board spots."* Both are true and the page could not say so: `Council
    on Aging` the DEPARTMENT is eleven paid staff, every one of whom is on the town's
    2025 gross wages list, and `Council On Aging` the BOARD is eleven appointed
    volunteers. Two real bodies, one name, told apart by a capital O.
    """
    kinds = collections.defaultdict(set)
    for r in rows:
        kinds[r['unit'].lower()].add(r['unit_kind'])
    for r in rows:
        if len(kinds[r['unit'].lower()]) > 1:
            r['unit'] = '%s (%s)' % (r['unit'], KIND_SUFFIX.get(r['unit_kind'],
                                                                r['unit_kind']))
    return rows


def build():
    rows, bad = _rows_officials()
    rows += _rows_rosters() + _rows_schools() + _rows_prose()
    rows = _disambiguate(rows)
    seen, uniq = set(), []
    for r in rows:
        k = (r['fy'], r['unit'], r['subunit'], r['section'], r['role'], r['person'],
             r['status'])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    uniq.sort(key=lambda r: (r['unit'].lower(), r['fy'], r['subunit'].lower(),
                             r['section'].lower(), r['role'].lower(),
                             r['person'].lower()))
    return uniq, bad


def payload(rows):
    years = sorted({r['fy'] for r in rows})
    units = collections.defaultdict(lambda: dict(years=set(), kind='', n=0, subs=set()))
    for r in rows:
        u = units[r['unit']]
        u['years'].add(r['fy'])
        u['kind'] = u['kind'] or r['unit_kind']
        u['n'] += 1
        if r['subunit']:
            u['subs'].add(r['subunit'])
    return dict(
        generated_by='scripts/build_org_charts.py',
        years=years,
        units=[dict(unit=k, kind=v['kind'], rows=v['n'], years=sorted(v['years']),
                    subunits=sorted(v['subs']))
               for k, v in sorted(units.items(), key=lambda kv: (-kv[1]['n'], kv[0]))],
        rows=rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows, bad = build()
    pay = payload(rows)
    if a.check:
        old = list(csv.DictReader(open(OUT_CSV, encoding='utf-8'))) \
            if os.path.exists(OUT_CSV) else []
        if len(old) != len(rows) or any(
                any(str(r[k]) != o[k] for k in FIELDS) for r, o in zip(rows, old)):
            print('STALE %s' % OUT_CSV)
            return 1
        return 0
    with open(OUT_CSV, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    json.dump(pay, open(OUT_JSON, 'w', encoding='utf-8'), indent=1, sort_keys=True)
    st = collections.Counter(r['status'] for r in rows)
    print('%d rows across %d units and %d years' % (len(rows), len(pay['units']),
                                                    len(pay['years'])))
    print('  filled %d, vacant %d, establishment posts %d'
          % (st['filled'], st['vacant'], st['post']))
    print('  REJECTED %d rows: town-profile text, listing footnotes, sub-headings' % bad)
    thin = [u for u in pay['units'] if len(u['years']) == 1]
    print('  %d unit(s) appear in ONE year only — read them before trusting them'
          % len(thin))
    return 0


if __name__ == '__main__':
    sys.exit(main())
