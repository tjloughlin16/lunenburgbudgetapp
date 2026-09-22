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
FIELDS = ['fy', 'unit', 'unit_kind', 'subunit', 'section', 'tier', 'role', 'person',
          'status', 'source']

# ---------------------------------------------------------------------------
# THE LADDER. A flat list of forty names is not an org chart, and the town prints the
# hierarchy on every roster it publishes: Chief, Deputy Chief, Captain, Lieutenant,
# Sergeant, Officer. TJ, 22 September 2026: *"i think the org chart needs some hierarchy.
# flat lists are hard to read, and i know there's hierarchy in here. ESP for the schools.
# but other depts have chiefs, captains, etc so it exists there too."*
#
# RULE 7 APPLIES TO THIS TABLE. The RANK is a fact -- the town printed it beside the name.
# The ORDER of the ranks is our reading of them, and two of these are genuinely arguable:
# a Business Manager and a Director of Facilities do not report to a Principal, and a
# board Chair is first among equals rather than anybody's superior. So the page calls
# these BANDS and not a reporting line, because nothing published says who reports to
# whom.
#
# ORDER MATTERS AND IS THE WHOLE TRICK: `Deputy Chief` must be tested before `Chief` and
# `Assistant Principal` before `Principal`, or every deputy in the town becomes a head.
TIERS = [
    (1, re.compile(r'\bdeputy|\bassistant\b|\basst\.?\b|\bvice[- ]?chair|\bcapt\.?\b'
                   r'|\bcaptain\b|\binterim\b|\bassoc(?:iate)?\b', re.I)),
    (0, re.compile(r'\bsuperintendent\b|\btown manager\b|\bchief\b|\bprincipal\b'
                   r'|\bdirector\b|\bchair(?:man|person|woman)?\b|\blibrarian\b'
                   r'|\btown clerk\b|\btreasurer\b|\bcollector\b|\bcommissioner\b'
                   r'|\badministrator\b', re.I)),
    (2, re.compile(r'\blieutenant\b|\blt\.?\b|\bsergeant\b|\bsgt\.?\b'
                   r'|\bdepartment head\b|\bdept\.? head\b|\bsupervisor\b'
                   r'|\bmanager\b|\bcoordinator\b|\bforeman\b|\bhead\b', re.I)),
]
TIER_STAFF = 3


def tier_of(role, kind):
    """Which band a printed role sits in. 0 head, 1 deputy, 2 supervisor, 3 everyone else.

    A BOARD SEAT IS NOT THE BOTTOM OF ANYTHING, but it has to sort somewhere, and putting
    members below the chair is the way every set of minutes in this town reads.
    """
    t = (role or '').strip()
    if not t:
        return TIER_STAFF
    for band, pat in TIERS:
        if pat.search(t):
            return band
    return TIER_STAFF

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


MONTY = 'Montachusett Regional Vocational Technical School'
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


# ---------------------------------------------------------------------------
# THE FIFTH SOURCE: WHO SIGNED THE REPORT.
#
# Most bodies in this town publish no roster at all. The Library, the Town Clerk, the
# Sewer Commission, Conservation, Veterans' Services -- fifteen years of reports and not
# one list of staff between them. What every one of them DOES print is the block that
# ends the report:
#
#     Respectfully submitted,
#     Muir Haman, Director, Lunenburg Public Library
#
# That is the head of the body, named, dated to the year, in the town's own words. It is
# the top layer of the chart for about thirty bodies that otherwise have nobody in it at
# all, and `extract_report_signatures.py` has 182 of them across thirteen years.
#
# THE NAMES NEED NORMALISING AND THAT IS OCR WORK, NOT INTERPRETATION. Every key below
# is a spelling of a body the contents page already names somewhere else in the same
# archive -- `LUNENBURG PUBLIC SCHOOLS` in capitals, `Lunenburg Public Library` with the
# town in front, `Veteran's Agent` where a later year says `Veterans' Services`.
SIG_SCHOOL = {
    'primary school': 'Lunenburg Primary School',
    'lunenburg primary school': 'Lunenburg Primary School',
    'turkey hill elementary': 'Turkey Hill Elementary School',
    'turkey hill elementary school': 'Turkey Hill Elementary School',
    'turkey hill middle school': 'Turkey Hill Elementary School',
    'middle school': 'Lunenburg Middle School',
    'lunenburg middle school': 'Lunenburg Middle School',
    'high school': 'Lunenburg High School',
    'lunenburg high school': 'Lunenburg High School',
}
# The district's own offices. They are not buildings, and the annual report files each
# under its own heading -- so they become SECTIONS of the central office rather than
# schools, which is what they are.
SIG_CENTRAL = {
    'superintendent message': 'Superintendent',
    "superintendent's message": 'Superintendent',
    'school facilities': 'Facilities and Grounds',
    'special services': 'Special Services',
    'special services department': 'Special Services',
    'review special services department': 'Special Services',
    'school lunch program': 'Food Service',
    'lunenburg school food service': 'Food Service',
    'pd update lunenburg school food service': 'Food Service',
    'teaching & learning models and pd update': 'Teaching and Learning',
    'teaching & learning models and': 'Teaching and Learning',
}
SIG_ALIAS = {
    'lunenburg public schools': 'Lunenburg Public Schools',
    'town manager': 'Town Manager', 'town manager report': 'Town Manager',
    'report of the town manager': 'Town Manager',
    'town manager report-heather r. lemieux': 'Town Manager',
    'public library': 'Public Library', 'lunenburg public library': 'Public Library',
    'public library 67,': 'Public Library',
    'housing authority submitted lunenburg public library': 'Public Library',
    "veteran's agent": "Veterans' Services", 'veterans services': "Veterans' Services",
    "veterans' services": "Veterans' Services",
    'police department **•': 'Police Department',
    'committee submitted zoning board of appeals': 'Zoning Board of Appeals',
    'ad hoc open space advisory committee to the planning board':
        'Ad Hoc Open Space Advisory Committee',
    'montachusett regional vocational': MONTY,
    'montachusett regional vocational technical school': MONTY,
    'montachusett regional vocational technical school district': MONTY,
    'montachusett regional vocational technical school ooooooooooo a o': MONTY,
    'technical school': MONTY,
}
# A TOWN MEETING IS NOT A DEPARTMENT. These are contents entries the signature extractor
# attributes a signing block to because the block sits on their pages -- the moderator's
# name at the end of a warrant, a line of an election return. Dropped rather than drawn.
SIG_DROP = re.compile(r'town meeting|town election|collection of taxes|omnibus|'
                      r'revenue funds|capital projects|vital records|excerpts', re.I)

def _rows_signatures():
    """The head of every body that signs its own report."""
    p = os.path.join(DATA, 'report-signatures.csv')
    out = []
    if not os.path.exists(p):
        return out
    for r in csv.DictReader(open(p, encoding='utf-8')):
        raw = re.sub(r'\s+', ' ', (r['department'] or '')).strip()
        # The orphaned `Submitted` of the PREVIOUS contents entry lands at the front of
        # the next name often enough to be worth cutting here as well as there.
        raw = re.sub(r'^.*\bSubmitted\b\s*', '', raw).strip() or raw
        if not raw or SIG_DROP.search(raw):
            continue
        key = raw.lower()
        if key in SIG_SCHOOL:
            unit, kind, sub, sect = ('Lunenburg Public Schools', 'school',
                                     SIG_SCHOOL[key], '')
        elif key in SIG_CENTRAL:
            unit, kind, sub, sect = ('Lunenburg Public Schools', 'school',
                                     'School Central Office', SIG_CENTRAL[key])
        else:
            unit = SIG_ALIAS.get(key, raw.title() if raw.isupper() else raw)
            if unit == 'Lunenburg Public Schools':
                kind, sub, sect = 'school', '', ''
            elif unit == MONTY:
                kind, sub, sect = 'school', '', ''
            elif re.search(r'commission|committee|board|authority|council', unit, re.I):
                kind, sub, sect = 'board', '', ''
            else:
                kind, sub, sect = 'department', '', ''
        out.append(dict(fy=r['fy'], unit=canon_unit(unit, kind), unit_kind=kind,
                        subunit=sub, section=sect,
                        # THE TITLE IS THE TOWN'S, NOT OURS. Where the block prints no
                        # title the person still signed the report, and `signed the
                        # report` is the only thing we can say about them.
                        # `nham, Superintendent` -- the scanner cuts the name in half
                        # and the tail of it lands in front of the title.
                        role=re.sub(r'^[a-z]{2,12},\s*', '',
                                    (r['title'] or 'signed the report').strip()),
                        person=r['person'].strip(), status='filled',
                        source='report signature p%s' % r['page']))
    return out


KIND_SUFFIX = {'department': 'staff', 'board': 'board', 'officer': 'appointed post',
               'school': 'schools'}


def _one_spelling(rows):
    """One spelling per body, chosen by weight of rows rather than by a table.

    Four sources name the same bodies and none of them agrees on capitals: the officials
    listing is read through `.title()` so it says `Board Of Assessors`, the contents page
    says `Board of Assessors`, and the two arrived as two bodies sitting next to each
    other in the dropdown. Case is not a distinction the town draws, so the most-used
    spelling wins and every row takes it. `_disambiguate` still splits on KIND afterwards,
    which is a real distinction and survives this.
    """
    weight = collections.defaultdict(collections.Counter)
    for r in rows:
        weight[r['unit'].lower()][r['unit']] += 1
    best = {k: c.most_common(1)[0][0] for k, c in weight.items()}
    for r in rows:
        r['unit'] = best[r['unit'].lower()]
    return rows


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
    rows += _rows_rosters() + _rows_schools() + _rows_prose() + _rows_signatures()
    for r in rows:
        # AN APPOINTED POST IS ITS OWN HEAD. A one-post unit like the Dam Keeper has
        # nobody under it, and banding it with the staff of a forty-person department
        # would read as a rank it does not have.
        r['tier'] = 0 if r['unit_kind'] == 'officer' else tier_of(r['role'],
                                                                 r['unit_kind'])
    rows = _disambiguate(_one_spelling(rows))
    seen, uniq = set(), []
    for r in rows:
        k = (r['fy'], r['unit'], r['subunit'], r['section'], r['role'], r['person'],
             r['status'])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    uniq.sort(key=lambda r: (r['unit'].lower(), r['fy'], r['subunit'].lower(),
                             r['tier'], r['section'].lower(), r['role'].lower(),
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
