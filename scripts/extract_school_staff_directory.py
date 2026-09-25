#!/usr/bin/env python3
"""THE DISTRICT'S PEOPLE, as each listing prints them -- and who is printed twice.

    python3 scripts/extract_school_staff_directory.py [--check]

Writes `sources/data/school-staff-directory.csv` and `sources/data/school-staff-shared.csv`.

THE GRAIN IS A PERSON AS ONE LISTING PRINTS THEM, not a person. Six sheets are read and
none is folded into another: the district's roll-up of every employee, and the five
listings the District Office and the four schools keep themselves. A person on two
schools' own listings therefore has TWO rows, which is the whole reason TJ gave the
per-school addresses -- *"to show 'shared' resources across school"*. Deduplicating here
would destroy the finding and leave a cleaner-looking file that could not answer the
question it was built for.

THE JOIN KEY IS THE EMAIL LOCAL PART, and it is the first stable person-identifier this
archive has held. Every other people-source here is a printed NAME -- `staff-roster-entries`
matches `Saranich, Carol` against `Carol Saranich` by whatever normalisation somebody
wrote, and the FY2022 roster hunt spent itself on exactly that. `csaranich` is issued by
the district, survives a name printed three ways, and is what makes these rows joinable
to each other at all.

    Two lists repeating a person is the MEASUREMENT.
    "A shared specialist" is a HYPOTHESIS, and rule 7 applies to it.

THE TWO ENCODINGS DISAGREE, AND BOTH ARE KEPT. The roll-up writes sharing into a free-text
school column (`Primary School & THES`); the per-school sheets write it by repetition. They
agree about five people and disagree about the rest, and the disagreement is structured
rather than random -- the roll-up has a COMBINED value, `Lunenburg Middle High School`, for
the building the middle and high schools share, so most of the repetition it appears to
contradict it is in fact recording another way. Neither encoding is authoritative and
neither is corrected against the other. `school-staff-shared.csv` carries what each says.

WHAT THIS IS NOT. It is a contact list, not an org chart and not a staffing level:

- **No FTE.** A 0.4 music teacher and a full-timer are one row each. The same limit the
  annual-report rosters have, and the reason `money_gaps` carries it.
- **No funding source**, which is the question rule 11 says actually matters -- whether a
  post is paid by the general fund, a grant or a revolving fund is not in any of this.
- **No reporting line.** A heading on a sheet groups people; it does not rank them.
- **No date beyond the fetch.** None of the six carries an `as of`. Turkey Hill's says
  `25-26 Updated 7/1` in its own title and is the only one that dates itself at all.

TWO SHAPES, DETECTED RATHER THAN ASSUMED. Five listings are tidy tables and announce
themselves with a `Name` header row. Turkey Hill's is a two-column-block office layout --
first-name-first, no emails, room numbers folded into the title, and the group headings
printed in the same column as the people. Rule 13c: the format is not standardised and a
reader who assumes it is loses a page. So the shape is read off the file, and a listing
matching neither is REFUSED by name rather than returned empty.

AND FOR A SOURCE THAT PRINTS NO TOTAL, THE CHECK ACCOUNTS FOR EVERY BOX. Rule 13 says
reconcile an extract to the total its source prints; none of these prints one. The
substitute is that every non-empty cell in a name column is classified as a person, a
heading or a note, and `--check` fails on one that is none of the three -- so a row lost to
a layout change is loud instead of silent.
"""
import argparse
import collections
import csv
import datetime
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
SNAPS = os.path.join(ROOT, 'sources', 'district-budget', 'docs', 'personnel',
                     'staff-directory')
INDEX = os.path.join(ROOT, 'sources', 'district-budget', 'index.csv')
OUT = os.path.join(DATA, 'school-staff-directory.csv')
OUT_SHARED = os.path.join(DATA, 'school-staff-shared.csv')

FIELDS = ['fy', 'fetched', 'listing', 'listing_kind', 'section', 'person',
          'person_as_printed', 'title', 'school', 'school_as_printed', 'email',
          'email_local', 'person_key', 'key_basis', 'room', 'extension', 'source']
SHARED = ['fy', 'person_key', 'key_basis', 'person', 'n_listings', 'listings',
          'rollup_school_as_printed', 'encodings_agree']

# HOW A ROW IS IDENTIFIED, WEAKEST LAST. `person_key` is whichever of these was available
# and `key_basis` always says which, because the three are not equally good and a join is
# only as strong as its weakest key:
#
#   1. AN ADDRESS THE SHEET PRINTS. Issued by the district, survives a name printed three
#      ways, and is the first stable person-identifier this archive has held.
#   2. AN ADDRESS DERIVED FROM THE RULE THE SHEET ITSELF STATES. Turkey Hill prints
#      *"All Emails are first initial, last name @lunenburgschools.net"* in its own last
#      row, which is what licenses deriving one -- and it is still derived.
#   3. A NAME, WHERE NOTHING ELSE IS PRINTED. Primary omits the address for every one of
#      its paraprofessionals, so 22 rows have only this, and a name is exactly the key
#      the FY2022 roster hunt proved cannot be trusted: the roll-up calls one of them
#      `Skye Abreu` and Primary's own sheet calls her `Skye Abrue`.
KEY_PRINTED = 'email printed'
KEY_DERIVED = "email derived from the sheet's own stated rule"
KEY_NAME = 'name only -- no address printed'

DOMAIN = 'lunenburgschools.net'

# THE SCHOOL NAMES ARE THE PUBLISHER'S, NORMALISED ONLY WHERE IT NAMES ONE PLACE TWO WAYS.
# `Lunenburg primary School` and `Lunenburg Primary School` are one school and a stray
# lowercase; `Primary School & THES` is two schools and must NOT be collapsed into either.
# So this maps only the forms that differ by case or abbreviation, `school_as_printed`
# keeps every one verbatim, and a value naming two places is left alone for
# `school-staff-shared.csv` to read.
SCHOOL = {
    'lunenburg primary school': 'Lunenburg Primary School',
    'primary school': 'Lunenburg Primary School',
    'primary': 'Lunenburg Primary School',
    'turkey hill elementary school': 'Turkey Hill Elementary School',
    'thes': 'Turkey Hill Elementary School',
    'lunenburg middle school': 'Lunenburg Middle School',
    'lms': 'Lunenburg Middle School',
    'lunenburg high school': 'Lunenburg High School',
    'lhs': 'Lunenburg High School',
    'lunenburg middle high school': 'Lunenburg Middle High School',
    'lmhs': 'Lunenburg Middle High School',
    'district': 'District',
    'district office': 'District Office',
}

# A NAME, AS EITHER SHEET SHAPE PRINTS IT. Every word capitalised, no digit, no `/` and
# no `&` -- because the headings that sit in the same column as the people are
# `Administration/Office`, `Grade 3`, `Nurse/Health & Behavioral Health`, `Achieve/TLC`.
NAME = re.compile(r"^[A-Z][A-Za-z'’.\-]*(?: [A-Z][A-Za-z'’.\-]*)+$")
# The words a sheet prints in a DATA column as a heading of its own.
COLHEAD = re.compile(r'^(room\s*#?|ext\.?/?voicemail|ext\.?|name|position|email)$', re.I)


def fetched_of(path):
    m = re.search(r'/(\d{4}-\d{2}-\d{2})/', path.replace(os.sep, '/'))
    return m.group(1) if m else ''


def fy_of(day):
    """The Massachusetts fiscal year a fetch date falls in -- 1 July to 30 June."""
    d = datetime.date.fromisoformat(day)
    return d.year + 1 if d.month >= 7 else d.year


def labels():
    """The district's own name for each listing, off the catalogue rather than a filename.

    `fetch_school_staff_directory.py` writes the anchor text from the landing page into
    the label, so the school a file belongs to is the publisher's word for it. Reading it
    back from the catalogue rather than un-slugging the filename keeps `&`, case and
    punctuation the district used.
    """
    out = {}
    if not os.path.exists(INDEX):
        return out
    for r in csv.DictReader(open(INDEX, encoding='utf-8')):
        if '/personnel/staff-directory/' not in r['local'] or not r['local'].endswith('.csv'):
            continue
        m = re.match(r'(.*?) \(school staff directory, rows\), fetched', r['label'])
        if m:
            out[r['local']] = (m.group(1), r['upstream'])
    return out


def split_name(s):
    """`Last, First` and `First Last` both become `First Last`; nothing else is touched."""
    s = re.sub(r'\s+', ' ', s).strip()
    if ',' in s:
        last, _, first = s.partition(',')
        return '%s %s' % (first.strip(), last.strip())
    return s


def local_part(email):
    m = re.search(r'([A-Za-z0-9._\-]+)@' + DOMAIN.replace('.', r'\.'),
                  (email or '').replace('mailto:', ''), re.I)
    return m.group(1).lower() if m else ''


def name_key(person):
    """A name reduced to letters, for the rows where nothing better is printed."""
    return 'name:' + re.sub(r'[^a-z]', '', person.lower())


def derived_local(person):
    """First initial + last name, which is the rule Turkey Hill's own sheet prints.

    Its last row reads *"All Emails are first initial, last name @lunenburgschools.net"*.
    That is the publisher stating the rule, which is what makes deriving it legitimate --
    but a derived key is still derived, so every row carrying one says so in `key_basis`
    and the report says how many of them the roll-up independently confirms.
    """
    parts = [p for p in re.split(r'\s+', person) if p]
    if len(parts) < 2:
        return ''
    return re.sub(r'[^a-z\-]', '', (parts[0][0] + parts[-1]).lower())


ROOM = re.compile(r'^([0-9]{1,3})(?:\s*/\s*([A-Za-z]+))?$')
EXTENSION = re.compile(r'^[0-9]{4}$')


def split_detail(cell):
    """The one cell Turkey Hill prints beside a name, which is not one kind of thing.

    Returns `(title, room, extension)`. THE SHEET IS INTERNALLY INCONSISTENT and that is a
    fact about it rather than a parsing problem: its left block heads the column `Room #`
    and fills it with JOB TITLES (`Norman Yvon | Principal`), while its right block heads
    the same column `Room #` and means it (`Quinn Cavaco | 210`). A hand-built sheet, in
    rule 13a's sense -- so the printed header cannot name the column and the value has to.

    WHAT SEPARATES A ROOM FROM AN EXTENSION IS READ OFF THE TWO COLUMNS THE SHEET DOES
    LABEL CORRECTLY, not off a rule of ours: every value under its `Ext./Voicemail`
    heading is four digits (`4002`, `4217`), every value under its `Room #` heading is one
    to three, sometimes with the team colour after it (`204/Blue`). A bare number is
    therefore attributed by width, and a cell that is neither is a title.

    A TITLE IS NEVER SYNTHESISED FROM THE SECTION. The five people under `Grade 3` have a
    room and no printed title; the grade is the GROUPING, kept in `section`, and writing
    `Grade 3 Teacher` into `title` would be us adding a claim the sheet does not make.
    """
    s = cell.strip()
    m = ROOM.match(s)
    if m:
        return '', s, ''
    if EXTENSION.match(s):
        return '', '', s
    # `Music, 216`, `Gr. 3 Teacher, 214`, `Teacher/110` -- the room appended to a title.
    m = re.match(r'^(.*?)[,/]\s*([0-9]{1,4}[A-Za-z]?)$', s)
    if m:
        return m.group(1).strip(), m.group(2), ''
    return s, '', ''


def read_tidy(rows, listing, kind, day, source):
    """A listing that announces its columns with a `Name` header row.

    The header is FOUND rather than assumed to be row 1: two of the five print a title
    line and a blank line above it. Columns are taken by their printed heading, so a
    listing that adds one (`Office Location`, `Extension`) needs nothing here.
    """
    hi = next((i for i, r in enumerate(rows)
               if any(c.strip().lower() == 'name' for c in r)), None)
    if hi is None:
        return None, []
    hdr = [c.strip().lower() for c in rows[hi]]

    def col(*names):
        for n in names:
            if n in hdr:
                return hdr.index(n)
        return None

    ci = {k: col(*v) for k, v in {
        'name': ('name',), 'title': ('position', 'title'), 'email': ('email',),
        'school': ('school/building', 'building', 'school'),
        'where': ('office location', 'location'), 'ext': ('extension', 'ext.', 'ext'),
    }.items()}
    out, unclassified = [], []
    for r in rows[hi + 1:]:
        if ci['name'] is None or len(r) <= ci['name']:
            continue
        raw = r[ci['name']].strip()
        if not raw:
            continue
        if not NAME.match(split_name(raw)):
            unclassified.append(raw)
            continue

        def cell(k):
            i = ci[k]
            return r[i].strip() if i is not None and len(r) > i else ''

        email = cell('email').replace('mailto:', '').strip()
        printed = cell('school') or cell('where')
        out.append(dict(
            fy=fy_of(day), fetched=day, listing=listing, listing_kind=kind, section='',
            person=split_name(raw), person_as_printed=raw, title=cell('title'),
            school=SCHOOL.get(printed.strip().lower(), printed.strip()),
            school_as_printed=printed, email=email, email_local=local_part(email),
            person_key=local_part(email) or name_key(split_name(raw)),
            key_basis=KEY_PRINTED if local_part(email) else KEY_NAME,
            room='', extension=cell('ext'), source=source))
    return 'tidy', (out, unclassified)


def read_blocks(rows, listing, kind, day, source):
    """Turkey Hill's two-column-block office layout.

    Each block is a `name | title | ext` triple standing side by side on the page, and the
    group headings sit in the SAME column as the people -- `Grade 3` above five teachers,
    `Custodians` above three. So a cell is read by what it looks like and by whether the
    cell beside it holds anything: a person carries a title, a heading does not.

    THE HEADING IS KEPT AS `section`, because it is the only grouping any of these six
    sheets publishes, and it is what `org-chart.csv` draws a body's bands from.
    """
    width = max((len(r) for r in rows), default=0)
    # A block starts at any column holding a plausible name; the two cells to its right
    # belong to it. Found from the data so a sheet laid out in three blocks still reads.
    starts = []
    for c in range(width):
        if sum(1 for r in rows if len(r) > c and NAME.match(r[c].strip())) >= 3:
            if not starts or c - starts[-1] >= 2:
                starts.append(c)
    out, unclassified = [], []
    for c in starts:
        section = ''
        for r in rows:
            if len(r) <= c:
                continue
            raw = r[c].strip()
            if not raw:
                continue
            nxt = r[c + 1].strip() if len(r) > c + 1 else ''
            if NAME.match(raw) and nxt and not COLHEAD.match(nxt):
                title, room, ext = split_detail(nxt)
                ext = ext or (r[c + 2].strip() if len(r) > c + 2 else '')
                person = split_name(raw)
                out.append(dict(
                    fy=fy_of(day), fetched=day, listing=listing, listing_kind=kind,
                    section=section, person=person, person_as_printed=raw, title=title,
                    school=SCHOOL.get(listing.strip().lower(), listing),
                    school_as_printed='', email='', email_local=derived_local(person),
                    person_key=derived_local(person) or name_key(person),
                    key_basis=KEY_DERIVED if derived_local(person) else KEY_NAME,
                    room=room, extension=ext, source=source))
            elif re.search(r'@|^All Emails', raw):
                continue                     # the sheet's note about how to build an address
            elif not NAME.match(raw) or not nxt or COLHEAD.match(nxt):
                section = raw.strip()
            else:
                unclassified.append(raw)
    return 'blocks', (out, unclassified)


def read_listing(path, listing, day, source):
    rows = list(csv.reader(io.StringIO(open(path, encoding='utf-8').read())))
    kind = 'roll-up' if re.search(r'all lunenburg', listing, re.I) else 'school'
    shape, got = read_tidy(rows, listing, kind, day, source)
    if shape:
        return shape, got
    return read_blocks(rows, listing, kind, day, source)


def build():
    lab = labels()
    rows, refused, unclassified = [], [], {}
    shapes = {}
    for local, (listing, upstream) in sorted(lab.items()):
        path = os.path.join(ROOT, local)
        if not os.path.exists(path):
            refused.append('%s -- catalogued, not on disk' % local)
            continue
        day = fetched_of(local)
        shape, (got, un) = read_listing(path, listing, day, upstream)
        if not got:
            refused.append('%s -- read as %s, no people' % (listing, shape))
            continue
        shapes[(day, listing)] = shape
        rows.extend(got)
        if un:
            unclassified[(day, listing)] = un
    return adopt_addresses(rows), refused, unclassified, shapes


def adopt_addresses(rows):
    """One person, one key -- where a sheet that omits her address is not the only sheet.

    WITHOUT THIS THE KEY SCHEME SPLITS PEOPLE IN HALF. Meredith Weiss is printed with an
    address by the high school and Turkey Hill and without one by the District Office and
    Primary, so she came out as `mweiss` on two listings and `name:meredithweiss` on two
    others -- counted as two people sharing two buildings each, when she is one person on
    four listings. A key that is missing on one sheet is not a different person.

    THE MATCH IS ON A NAME AND IS THEREFORE DERIVED, so the row keeps `key_basis` at its
    weakest value: a name did the work of joining, and everything downstream that cares
    about how strong this is can see that it was a name. What this cannot do is the
    reverse -- `Skye Abrue` and `Skye Abreu` stay two keys, because collapsing those needs
    a judgement that a typo is a typo, and that is exactly the judgement rule 13 says not
    to make silently. The seven of them are in `data-problems`, not fixed here.
    """
    by_name = {}
    for r in rows:
        if r['key_basis'] != KEY_NAME:
            by_name.setdefault((r['fy'], name_key(r['person'])), r['person_key'])
    for r in rows:
        if r['key_basis'] == KEY_NAME:
            r['person_key'] = by_name.get((r['fy'], name_key(r['person'])), r['person_key'])
    return rows


def shared_of(rows):
    """Who is printed on more than one listing, and what each encoding says about them.

    Only the per-school listings can repeat a person; the roll-up has one row each. So the
    repetition is counted across `listing_kind == 'school'` and the roll-up is then asked,
    separately, what IT says -- which is the disagreement, kept rather than resolved.

    THE ROLL-UP IS ASKED BY BOTH KEYS, because it prints an address for everybody and two
    of the five school listings do not. Matching it on the address alone left 15 people
    looking absent from a sheet that names them. Where the fallback is a NAME the row says
    so in `key_basis`, since that is the join this archive has already been burned by.
    """
    out = []
    for fy in sorted({r['fy'] for r in rows}):
        yr = [r for r in rows if r['fy'] == fy]
        rollup = {}
        for r in yr:
            if r['listing_kind'] != 'roll-up':
                continue
            rollup[r['person_key']] = r
            rollup.setdefault(name_key(r['person']), r)
        seen = collections.defaultdict(set)
        by_key = collections.defaultdict(list)
        for r in yr:
            if r['listing_kind'] != 'school':
                continue
            seen[r['person_key']].add(r['listing'])
            by_key[r['person_key']].append(r)
        for key, ls in sorted(seen.items()):
            if len(ls) < 2:
                continue
            mine = by_key[key]
            ru = rollup.get(key) or rollup.get(name_key(mine[0]['person']))
            printed = (ru or {}).get('school_as_printed', '')
            bases = {r['key_basis'] for r in mine}
            out.append(dict(
                fy=fy, person_key=key,
                key_basis=(KEY_NAME if KEY_NAME in bases
                           else KEY_DERIVED if KEY_DERIVED in bases else KEY_PRINTED),
                person=mine[0]['person'], n_listings=len(ls),
                listings=' | '.join(sorted(ls)),
                rollup_school_as_printed=printed or ('' if ru else 'not in the roll-up'),
                encodings_agree='yes' if '&' in printed else 'no'))
    return out


def write(path, fields, rows):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in fields})


def report(rows, refused, unclassified, shapes, shared):
    for r in refused:
        print('  !! refused %s' % r)
    for (day, listing), un in sorted(unclassified.items()):
        print('  ?? %s %s -- %d cell(s) in a name column classified as neither a person '
              'nor a heading: %s' % (day, listing[:28], len(un), '; '.join(un[:4])))
    by = collections.Counter((r['fetched'], r['listing']) for r in rows)
    for (day, listing), n in sorted(by.items()):
        print('  %s  %-46s %-6s %3d people' % (day, listing[:46],
                                               shapes.get((day, listing), '?'), n))
    basis = collections.Counter(r['key_basis'] for r in rows)
    print('%d rows, %d listings; keyed by %s'
          % (len(rows), len(by),
             ', '.join('%d %s' % (n, k) for k, n in basis.most_common())))
    # HOW MUCH OF THE WEAKEST KEY THE STRONGEST ONE CONFIRMS. A derived address that the
    # roll-up also prints is corroborated by a second document; one it does not is a
    # guess that happens to be ours, and the difference belongs in the report rather than
    # in a footnote nobody runs.
    printed = {r['person_key'] for r in rows if r['key_basis'] == KEY_PRINTED}
    der = [r for r in rows if r['key_basis'] == KEY_DERIVED]
    print('%d derived addresses, %d confirmed by an address another listing prints'
          % (len(der), sum(1 for r in der if r['person_key'] in printed)))
    print('%d people printed on more than one listing; the roll-up names two places for '
          '%d of them' % (len(shared), sum(1 for s in shared if s['encodings_agree'] == 'yes')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows, refused, unclassified, shapes = build()
    shared = shared_of(rows)
    if a.check:
        bad = list(refused)
        for (day, listing), un in sorted(unclassified.items()):
            bad.append('%s %s: %d unclassified cell(s) in a name column: %s'
                       % (day, listing, len(un), '; '.join(un[:3])))
        for p, fields, want in ((OUT, FIELDS, rows), (OUT_SHARED, SHARED, shared)):
            if not os.path.exists(p):
                bad.append('%s does not exist' % os.path.relpath(p, ROOT))
                continue
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=fields)
            w.writeheader()
            for r in want:
                w.writerow({k: r.get(k, '') for k in fields})
            if buf.getvalue() != open(p, encoding='utf-8', newline='').read():
                bad.append('%s is stale' % os.path.relpath(p, ROOT))
        report(rows, refused, unclassified, shapes, shared)
        for b in bad:
            print('  !! %s' % b)
        return 1 if bad else 0
    write(OUT, FIELDS, rows)
    write(OUT_SHARED, SHARED, shared)
    report(rows, refused, unclassified, shapes, shared)
    print('wrote %s and %s' % (os.path.relpath(OUT, ROOT), os.path.relpath(OUT_SHARED, ROOT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
