#!/usr/bin/env python3
"""What each town department says about its own staffing, in its own words.

    python3 scripts/extract_department_staffing.py
    python3 scripts/extract_department_staffing.py --check

Writes `sources/data/department-staffing.csv`.

WHY THIS EXISTS. TJ, on being told a budget line falling is not a cut: *"'cuts' are
service reductions, which we have to find in ways other than budget information. The
immediate one is staffing."* The wage list stopped naming departments after FY2016 and
there is no roster for most departments -- so I told him the town does not print who works
there. He asked *"and you are SURE..."* and he was right to: I had searched our own
extraction plan, found no roster rows, and reported OUR silence as the town's. Rule 13c,
for the second time in one day.

DEPARTMENTS DESCRIBE THEIR OWN STAFFING IN THE PROSE OF THEIR REPORTS, every year. No
heading names it, which is exactly why it went unread -- the same reason fifteen years of
out-of-district placement counts sat unread in the same documents until somebody looked.

WHAT IS CAPTURED AND WHAT IS PARSED ARE DIFFERENT THINGS, deliberately. The sentence is
stored VERBATIM, because that is the source and a reader must be able to check it. Counts
are parsed only where the form is unambiguous, into their own columns, and where it is not
the row still exists with `parsed=no`. A statement that cannot be counted is evidence that
the town said something; it is not a number.

AND THE FORMS DO NOT AGREE WITH EACH OTHER. The Fire Department gives a count and a RANGE
(`10 Career and 30-35 On Call/Per Diem`). The DPW gives an establishment, post by post
(`one Director, one Executive Assistant (shared with the Facilities Department), one
Highway Superintendent, 5 Heavy Equipment Operators...`). The Building Department gives a
list of names. Those are three different quantities and they may not be summed into a town
total -- which is why `measure` says which kind each row is, and nothing aggregates across
kinds.
"""
import argparse
import collections
import csv
import glob
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(ROOT, 'sources', 'town-budget', 'pages')
OUT = os.path.join(ROOT, 'sources', 'data', 'department-staffing.csv')

FIELDS = ['fy', 'page', 'department', 'measure', 'career', 'on_call_low', 'on_call_high',
          'positions', 'parsed', 'statement']

# The regional school district reprints the same paragraphs about itself in every town's
# annual report -- leadership "comprised of", students "comprised of", career and technical
# education. It is not Lunenburg's staffing and it matched every pattern here.
NOT_OURS = re.compile(r'montachusett|monty\s*tech|regional\s+vocational|sending\s+communit'
                      r'|easement|fringe benefits', re.I)

TRIGGER = re.compile(
    r'staff consists of|staff is comprised of|department consists of'
    r'|consists of the following personnel|department is staffed'
    r'|staffing (?:as of|is now|is currently)'
    r'|\bcareer\s+(?:and|firefighters)', re.I)

HEADING = re.compile(r"^[A-Z][A-Z &/'.\-]{6,}$")

WORDS = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7,
         'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12}

# `10 Career and 30-35 On Call/Per Diem Firefighters`, and `eight Career and 40-45 On Call`
# -- the count is sometimes a numeral and sometimes a word, in the same sentence shape.
FIRE = re.compile(r'(\d+|%s)\s+career\s+and\s+(\d+)\s*[-–]\s*(\d+)\s+on[\s-]?call'
                  % '|'.join(WORDS), re.I)

# `one Director`, `5 Heavy Equipment Operators`, `two Seasonal Cemetery Laborers`.
POST = re.compile(r'\b(\d+|%s)\s+([A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*){0,3})'
                  % '|'.join(WORDS))


# THE HEADING ABOVE A SENTENCE IS NOT ALWAYS ITS DEPARTMENT. The tracker takes the last
# all-capitals line, and on a page whose running header is `PROPERTY` or a mid-page label
# reads `FIRE RESCUE`, the Fire Department's own staffing sentence gets filed under it. The
# sentence names itself, so where it does, it wins.
SELF_NAMED = [(re.compile(r'\bfire department\b', re.I), 'Fire Department'),
              (re.compile(r'\bpolice department\b', re.I), 'Police Department'),
              (re.compile(r'\bbuilding department\b', re.I), 'Building Department'),
              (re.compile(r'department of public works|\bDPW\b', re.I),
               'Department of Public Works'),
              (re.compile(r'council on aging', re.I), 'Council on Aging')]


def name_of(head, statement):
    for pat, name in SELF_NAMED:
        if pat.search(statement):
            return name
    return head.title() or '(unheaded)'


def count(tok):
    return int(tok) if tok.isdigit() else WORDS.get(tok.lower(), 0)


def statements(path):
    """Every staffing sentence on the town's own pages, with the heading above it."""
    page, head = None, ''
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'^===PAGE (\d+)===', line)
        if m:
            page = int(m.group(1))
            continue
        t = re.sub(r'^\s*\d+\|', '', line).rstrip()
        s = t.strip()
        if HEADING.match(s):
            head = s
        if not s or NOT_OURS.search(s) or not TRIGGER.search(s):
            continue
        yield page, head, s


def join_wrapped(path):
    """The sentence and the line after it, because these paragraphs wrap mid-clause.

    `The staff consists of one Director, one Executive Assistant (shared with the Facili`
    ends there and continues `ties Department), one Highway Superintendent, 5 Heavy
    Equipment Operators...` on the next line. Reading only the matched line gets the first
    two posts and loses the department.
    """
    lines, page = [], None
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'^===PAGE (\d+)===', line)
        if m:
            page = int(m.group(1))
            continue
        lines.append((page, re.sub(r'^\s*\d+\|', '', line).strip()))
    return lines


def read_year(fy):
    path = os.path.join(PAGES, 'FY%s.ocr.txt' % fy)
    if not os.path.exists(path):
        return []
    lines = join_wrapped(path)
    idx = {(p, t): i for i, (p, t) in enumerate(lines)}
    out = []
    for page, head, s in statements(path):
        i = idx.get((page, s))
        # Take up to four following lines, stopping at a blank or a new heading: the
        # establishment sentences run to three lines in some years.
        whole = s
        if i is not None:
            for j in range(i + 1, min(i + 5, len(lines))):
                nxt = lines[j][1]
                if not nxt or HEADING.match(nxt):
                    break
                whole += ' ' + nxt
                if nxt.endswith('.'):
                    break
        whole = re.sub(r'(\w)-\s+(\w)', r'\1\2', whole)   # rejoin words split at the margin
        whole = re.sub(r'\s+', ' ', whole).strip()

        f = FIRE.search(whole)
        row = dict(fy=fy, page=page, department=name_of(head, whole),
                   measure='', career='', on_call_low='', on_call_high='',
                   positions='', parsed='no', statement=whole[:600])
        if f:
            row.update(measure='career and on-call firefighters', parsed='yes',
                       career=count(f.group(1)), on_call_low=int(f.group(2)),
                       on_call_high=int(f.group(3)))
        elif re.search(r'staff consists of|department consists of', whole, re.I):
            posts = [(count(a), b.strip()) for a, b in POST.findall(whole)]
            posts = [(n, w) for n, w in posts if n and len(w) > 3]
            if posts:
                row.update(measure='establishment, post by post', parsed='yes',
                           positions='; '.join('%d %s' % (n, w) for n, w in posts))
        out.append(row)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows = []
    for f in sorted(glob.glob(os.path.join(PAGES, 'FY*.ocr.txt'))):
        rows += read_year(re.search(r'FY(\d{4})', f).group(1))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(rows)
    by = collections.Counter(r['department'] for r in rows)
    print('%d staffing statements across %d years; %d parsed'
          % (len(rows), len({r['fy'] for r in rows}),
             sum(1 for r in rows if r['parsed'] == 'yes')))
    for d, n in by.most_common(10):
        print('  %-34s %d' % (d[:34], n))
    if a.check:
        cur = open(OUT, encoding='utf-8', newline='').read() if os.path.exists(OUT) else ''
        if cur != buf.getvalue():
            print('  STALE — run: python3 scripts/extract_department_staffing.py')
            return 1
        print('  department-staffing.csv is current')
        return 0
    open(OUT, 'w', encoding='utf-8', newline='').write(buf.getvalue())
    print('wrote %s' % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
