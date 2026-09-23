#!/usr/bin/env python3
"""THE ORG CHART, CHECKED AS A MODEL rather than looked at as a page.

    python3 scripts/check_org_charts.py [--unit NAME] [--fy YYYY] [--quiet]

TJ, 22 September 2026: *"I assume you can model this in the DB and show the linking and
hierarchy, to confirm its all right, vs visualizaing on the page."* -- after: *"i think
you are being too narrow sighted... Any human that looks at these org charts will tell you
where the natural hierarchy plays into this. i shouldnt have had to tell you to organize
schools by grades."*

He is right about the method. Every defect found in this dataset so far was found by a
PERSON reading the rendered page and saying `that is wrong`, which does not scale to 104
units across fifteen years and does not catch the next one. So the shape gets asserted.

EACH CHECK IS A STRUCTURAL CLAIM ABOUT A BODY, not about a figure:

    HEADLESS      a body with members and nobody at the top. A police department
                  without a chief is not a police chart, and this is the check that
                  would have caught seven years of the Fire Department
    MANY-HEADS    more than three people in the top band of one body in one year --
                  usually a committee filed under `officer`, where every row read as a
                  head, or a name matched by two rank patterns
    DOUBLED       one person twice in one body, one year -- an OCR variant of a name, or
                  the same post read off the roster and the signature block
    NOT-A-PERSON  a section heading or a sentence sitting in the `person` column
    DEAD-GROUP    a grouping with ONE value for the whole unit-year. `Elected` over every
                  member of an elected board is a heading that tells a reader nothing
    NO-ROLE       rows where the town printed no title at all. Not a defect -- several
                  departments publish bare name lists -- but it bounds what the chart can
                  ever show, so it is counted and never silently tolerated
    TWIN-UNIT     two units whose names differ only by punctuation, case or a word like
                  `Department`. One body in two dropdown entries

Exit 1 if any check finds something. The counts are the report.
"""
import argparse
import collections
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources', 'data', 'org-chart.csv')

HEADISH = re.compile(r'\b(bureau|shift|division|officers|firefighters|patrol|reserve|'
                     r'arrivals|supervisors|members|trustees|personnel|staff|program|'
                     r'committee|commission|department|council|board)\b', re.I)
# INTERIM AND ACTING ARE NOT SECOND. An Interim Chief runs the department; the word says
# how long, not how far down.
SECOND = re.compile(r'\bdeputy\b|\bassistant\b|\basst\b|\bvice[- ]?chair|'
                    r'\blieutenant\b|\blt\b|\bsergeant\b|\bsgt\b', re.I)
SENTENCE = re.compile(r'\b(?:retired|resigned|graduated|began|served|hired|appointed|'
                      r'until|denotes|vacan\w*)\b', re.I)


def norm_unit(u):
    u = re.sub(r'\s*\((staff|board|schools|appointed post)\)$', '', u, flags=re.I)
    return re.sub(r'[^a-z]', '', re.sub(r'\b(the|of|and|lunenburg|department|town)\b',
                                        '', u.lower()))


def load():
    return list(csv.DictReader(open(SRC, encoding='utf-8')))


def check(rows, want_unit=None, want_fy=None):
    by = collections.defaultdict(list)
    for r in rows:
        if want_unit and r['unit'] != want_unit:
            continue
        if want_fy and r['fy'] != want_fy:
            continue
        by[(r['unit'], r['fy'], r['subunit'])].append(r)

    out = collections.defaultdict(list)
    for (unit, fy, sub), rs in sorted(by.items()):
        people = [r for r in rs if r['person'].strip()]
        heads = [r for r in rs if r['tier'] == '0']
        where = '%s%s FY%s' % (unit, ' / ' + sub if sub else '', fy)

        if len(people) >= 3 and not heads:
            out['HEADLESS'].append('%-58s %d people, nobody at the top' % (where, len(people)))
        # A BODY HAS ONE CHAIR. Two means a mid-year change the reports print both
        # sides of -- or a chair read off a page the contents page attributed to the
        # wrong body, which is the likelier of the two and the reason this is checked.
        # TWO CHAIRS WHO BOTH SIT ON THE BODY IS A SUCCESSION, and the reports print
        # both sides of one: a board that changes chair mid-year names the old one in the
        # narrative and the new one in the signature. What is wrong is a chair who is not
        # a member, and those are removed upstream — so this now flags only what is left.
        seated = {r['person'] for r in rs
                  if r['role'] in ('board seat', 'officer')
                  or not re.search(r'chair', r['role'], re.I)}
        chairs = {h['person'] for h in rs if re.search(r'^chair', h['role'], re.I)}
        if len(chairs) > 1 and not chairs <= seated:
            out['TWO-CHAIRS'].append('%-58s %s' % (where, ', '.join(sorted(chairs))[:70]))
        # A DEPUTY AT THE TOP OF A BODY. TJ caught this twice by eye -- a Deputy Chief
        # above the Chief, an Assistant Principal above the Principal -- and both times
        # the head had been thrown away by a matcher rather than demoted. If the highest
        # band a body has is occupied by a rank whose own name says it is second, the
        # first is missing.
        # ONLY IN THE HEAD BAND. A vice-chair in the DEPUTY band with nothing above is
        # the record -- several bodies name a vice-chair in their report and never a
        # chair -- and a flat body whose members happen to be assistants elsewhere is not
        # inverted at all. What is wrong is a second-in-command standing at the TOP.
        if len(people) > 1:
            inv = [r for r in rs if r['tier'] == '0' and SECOND.search(r['role'])]
            if inv:
                out['INVERTED'].append('%-58s top band is %s'
                                       % (where, ', '.join(sorted({r['role'][:26]
                                                                   for r in inv}))[:56]))
        if len(heads) > 3:
            out['MANY-HEADS'].append('%-58s %d in the top band: %s'
                                     % (where, len(heads),
                                        ', '.join(sorted({h['person'][:22] for h in heads}))[:90]))
        seen = collections.Counter(r['person'].strip().lower() for r in people)
        for who, n in seen.items():
            if n > 1:
                out['DOUBLED'].append('%-58s %s x%d' % (where, who[:30], n))
        for r in people:
            p = r['person'].strip()
            if (HEADISH.search(p) or SENTENCE.search(p)) and len(p.split()) <= 5:
                out['NOT-A-PERSON'].append('%-58s %-28s role=%s' % (where, p[:28], r['role'][:24]))
        # A BAND IS GROUPED ONLY IF THE GROUPING DIVIDES IT. One heading over a whole
        # band is a line of type between the reader and the names, and the page applies
        # the same rule -- so the check has to be per BAND, not per unit-year.
        for t in {r['tier'] for r in rs}:
            band = [r for r in rs if r['tier'] == t]
            groups = {r['section_group'] for r in band}
            if len(band) >= 4 and len(groups) == 1 and groups != {''}:
                out['DEAD-GROUP'].append('%-58s band %s: every one of %d under %r'
                                         % (where, t, len(band), list(groups)[0]))
        n0 = sum(1 for r in rs if not r['role'].strip() or r['role'] in ('board seat',
                                                                        'officer'))
        if n0 and n0 == len(rs) and len(rs) >= 3:
            out['NO-ROLE'].append('%-58s %d rows, the town printed no title on any'
                                  % (where, n0))

    twins = collections.defaultdict(set)
    for r in rows:
        twins[norm_unit(r['unit'])].add(r['unit'])
    for k, v in sorted(twins.items()):
        # A DEPARTMENT AND A BOARD OF THE SAME NAME ARE TWO BODIES, on purpose. The
        # Council on Aging is eleven paid staff AND eleven appointed volunteers, and the
        # suffix is how the page says so. Only an UNMARKED pair is a defect.
        if len(v) > 1 and not all(re.search(r'\((staff|board|schools|appointed post)\)$',
                                            x) for x in v):
            out['TWIN-UNIT'].append('%s' % ' | '.join(sorted(v)))
    return out


ORDER = ['PAYLOAD', 'NOT-A-PERSON', 'INVERTED', 'TWIN-UNIT', 'TWO-CHAIRS', 'HEADLESS', 'MANY-HEADS', 'DOUBLED',
         'DEAD-GROUP', 'NO-ROLE']


def payload_shape():
    """The PUBLISHED payload, checked for the things a page can trip over.

    Every check above reads the CSV, and the CSV was right the whole time a reader was
    looking at a Fire Chief filed under `Members, seats and staff` below his own deputy.
    The defect was that the JSON carried `tier` as a NUMBER while the page compared
    against `'0'` -- and in JavaScript the integer 0 is falsy, so `r.tier || '3'` read
    every head in the archive as missing. No check on the data could have caught it, so
    the check is on the payload's SHAPE.
    """
    path = os.path.join(ROOT, 'fy28', 'public', 'data', 'org-charts.json')
    if not os.path.exists(path):
        return []
    import json
    rows = json.load(open(path, encoding='utf-8'))['rows']
    bad = []
    kinds = {type(r.get('tier')).__name__ for r in rows}
    if kinds != {'str'}:
        bad.append('tier is published as %s; the page compares it against strings, and '
                   'a numeric 0 is FALSY in JavaScript' % ' and '.join(sorted(kinds)))
    if any(str(r.get('tier')) not in ('0', '1', '2', '3', '4') for r in rows):
        bad.append('a tier outside 0-4 is published; the page has no band for it')
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--unit')
    ap.add_argument('--fy')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--limit', type=int, default=12)
    a = ap.parse_args()
    rows = load()
    out = check(rows, a.unit, a.fy)
    for msg in payload_shape():
        out['PAYLOAD'].append(msg)
    total = sum(len(v) for v in out.values())
    print('%d rows, %d units, %d years'
          % (len(rows), len({r['unit'] for r in rows}), len({r['fy'] for r in rows})))
    for k in ORDER:
        v = out.get(k, [])
        print('  %-13s %4d' % (k, len(v)))
        if not a.quiet:
            for line in v[:a.limit]:
                print('      %s' % line)
            if len(v) > a.limit:
                print('      ... and %d more' % (len(v) - a.limit))
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main())
