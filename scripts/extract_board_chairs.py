#!/usr/bin/env python3
"""WHO CHAIRED EACH BOARD, from the body's own report.

    python3 scripts/extract_board_chairs.py [--check]

Writes `sources/data/board-chairs.csv`.

TJ, 22 September 2026, after a QA pass showed 274 bodies with members and nobody at the
top: *"Any human that looks at these org charts will tell you where the natural hierarchy
plays into this."* A board's hierarchy is its CHAIR, and the officials listing prints the
chair only in the early years -- `David W. Reif** 2014`, under a footnote reading
`** denotes chairperson`. After about FY2015 the asterisks stop.

THE CHAIR DID NOT STOP BEING PUBLISHED. Every year of every book names chairs, in the
bodies' own reports, in four forms:

    Richard Letarte, Chairman        Louis Franco, Member      Rena Swezey, Member
    Terri Burchfield, Chairman
    Chairman Richard McGrath. The Commissioners would like to thank...
    FY23 Council on Aging Board members were Chairperson Deb Lincoln,
    Vice-Chairperson Jane Rabbitt, Barbara Brown, ...

THE PAGE RANGE COMES FROM THE TOWN'S OWN CONTENTS PAGE, so a chair is attributed to the
body whose report names them rather than to whichever heading happened to be above. That
is the same discipline `extract_report_signatures.py` uses and the same reason it works.

WHAT THIS IS NOT. A chair named in a report is a chair the report names. It is not a term
of office, it is not dated within the year, and a body that changed chairs mid-year may
print either or both -- so a year with two chairs is recorded with two rows rather than
resolved.
"""
import argparse
import collections
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
DATA = os.path.join(ROOT, 'sources', 'data')
INDEX = os.path.join(DATA, 'report-index.csv')
OUT = os.path.join(DATA, 'board-chairs.csv')
FIELDS = ['fy', 'department', 'person', 'title', 'page', 'as_printed']

NAME = r"[A-Z][A-Za-z'\-]+(?:\s+(?:[A-Z]\.|[A-Z][A-Za-z'\-]+)){1,2}"
TITLE = r"(Vice[- ]?Chair(?:man|person|woman)?|Co[- ]?Chair(?:man|person|woman)?" \
        r"|Chair(?:man|person|woman)?)"
# `Richard Letarte, Chairman` and `Terri Burchfield, Chairman`
TRAILING = re.compile(r'\b(%s)\s*,\s*%s\b' % (NAME, TITLE))
# `Chairman Richard McGrath` and `Chairperson Deb Lincoln`
LEADING = re.compile(r'\b%s\s+(%s)' % (TITLE, NAME))

# A TITLE IS NOT A NAME, and the leading form will happily take one. `Chairman of the
# Board`, `Chairperson and the Town`, `Vice Chairman Report`.
NOT_NAME = re.compile(r'\b(board|committee|commission|report|town|department|the|of|and|'
                      r'school|select|finance|meeting|member|members|said|will|has|'
                      r'commissioners|trustees|officials|association|authority)\b',
                      re.I)
# The sentence the listing's own footnote prints; not a person.
FOOTNOTE = re.compile(r'denotes\s+chair', re.I)
# A TABLE IS NOT A BODY. The contents page lists `Bonded Indebtedness`, `Collection of
# Taxes` and `Special Revenue Funds` beside the departments, and a chair named anywhere
# in those pages would be attributed to a table.
NOT_A_BODY = re.compile(r'balance|receipt|indebted|collection of taxes|revenue fund|'
                        r'capital project|debt|wages|officials|profile|summary|'
                        r'classification|vital|meeting|election|omnibus|hours', re.I)
# A REPORT DOES NOT RUN SIXTY PAGES. FY2011 and FY2012 print an ALPHABETICAL index, so a
# `12-74` there is the distance between two unrelated entries rather than one report --
# and a chair found anywhere inside it would be filed under whatever came first.
MAX_SPAN = 40


def _pages(fy):
    import extract_staffing_by_section as X
    return X.page_text(fy)


def read_year(fy, rows_idx, pages):
    owner = {}
    for r in rows_idx:
        if r['fy'] != fy or r['state'] != 'report' or not r['pdf_from']:
            continue
        if NOT_A_BODY.search(r['department']):
            continue
        if int(r['pdf_to']) - int(r['pdf_from']) > MAX_SPAN:
            continue
        for p in range(int(r['pdf_from']), int(r['pdf_to']) + 1):
            owner.setdefault(p, r['department'])
    out = []
    for p in sorted(pages):
        dept = owner.get(p)
        if not dept:
            continue
        for ln in pages.get(p, []):
            t = re.sub(r'\s+', ' ', ln).strip()
            if not t or FOOTNOTE.search(t):
                continue
            for pat, ni, ti in ((TRAILING, 1, 2), (LEADING, 2, 1)):
                for m in pat.finditer(t):
                    who, title = m.group(ni).strip(), m.group(ti).strip()
                    # A TITLE IS NOT A NAME, AND THE LINE OFTEN HOLDS BOTH. `...were
                    # Chairperson Deb Lincoln, Vice-Chairperson Jane Rabbitt` gave a
                    # vice-chair called `Chairperson Deb Lincoln`, because the pattern
                    # takes whatever follows the title and the previous person's title
                    # was sitting there.
                    if NOT_NAME.search(who) or re.search(TITLE, who, re.I):
                        continue
                    out.append(dict(fy=fy, department=dept, person=who,
                                    title=title.title(), page=p, as_printed=t[:120]))
    return out


def build():
    idx = list(csv.DictReader(open(INDEX, encoding='utf-8')))
    out = []
    for fy in sorted({r['fy'] for r in idx}):
        out += read_year(fy, idx, _pages(fy))
    seen, uniq = set(), []
    for r in out:
        k = (r['fy'], r['department'], r['person'], r['title'])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    uniq.sort(key=lambda r: (r['fy'], r['department'].lower(), r['title'], r['person']))
    return uniq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows = build()
    if a.check:
        old = list(csv.DictReader(open(OUT, encoding='utf-8'))) if os.path.exists(OUT) else []
        if len(old) != len(rows) or any(
                any(str(r[k]) != o[k] for k in FIELDS) for r, o in zip(rows, old)):
            print('STALE %s' % OUT)
            return 1
        return 0
    with open(OUT, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    per = collections.Counter(r['fy'] for r in rows)
    print('%d chair mentions across %d years and %d bodies'
          % (len(rows), len(per), len({r['department'] for r in rows})))
    for fy in sorted(per):
        print('  FY%s  %3d' % (fy, per[fy]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
