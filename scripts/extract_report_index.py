#!/usr/bin/env python3
"""The town's OWN list of departments, from the contents page of each annual report.

    python3 scripts/extract_report_index.py [--check]

Writes `sources/data/report-index.csv`: one row per department per year, with the pages
its report occupies -- or the town's own words when there is none.

TJ, 22 September 2026: *"we have a dept list right? I assume EVERY department shows up
here... i see big gaps in your table but i still dont know why. just capture it all."*

WE DID NOT HAVE A DEPARTMENT LIST. Every list in this project so far was one I typed,
which is why Facilities was absent from the coverage grid -- not because the town omits
it but because I had not thought of it. The town publishes the list itself, on the
contents page of every annual report, with the page range of each report beside it:

    Building Department            Pages 39-40
    Cultural Council               No Report Submitted
    Department of Public Works     Pages 44-48

That second line is the answer to `why is this cell empty` for a whole class of gaps: the
department did not submit a report that year and the town SAYS SO. A gap we can explain
in the town's own words is not the same kind of thing as a gap we cannot, and until now
this project could not tell them apart.

THE PAGE NUMBERS ARE PRINTED PAGE NUMBERS, not positions in the PDF. The offset differs
per year -- covers, blank pages and unnumbered front matter -- so it is measured per year
from the page numbers the book prints at its own feet, never assumed.
"""
import argparse
import collections
import csv
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(ROOT, 'sources', 'town-budget', 'pages')
OUT = os.path.join(ROOT, 'sources', 'data', 'report-index.csv')
FIELDS = ['fy', 'section', 'department', 'printed_from', 'printed_to',
          'pdf_from', 'pdf_to', 'state', 'as_printed']

CONTENTS = re.compile(r'\bcontents\b|\btable of contents\b', re.I)
# `Pages 39-40`, `Page 21`, `Pages 44-48`
RANGE = re.compile(r'\bPages?\s+(\d{1,3})\s*[-–—]\s*(\d{1,3})\b', re.I)
SINGLE = re.compile(r'\bPages?\s+(\d{1,3})\b', re.I)
NONE = re.compile(r'no\s+report', re.I)
# BEFORE FY2024 THE WORD `Pages` IS NOT THERE. `Board of Assessors 37-38`, `Planning
# Board 97`, `Fire Department aaaaaaaaaaaado, 86-88` -- a name, then leader dots the
# scanner turns into letters, then the page numbers at the end of the line. Anchored to
# the END so a figure inside a department's name cannot be read as its page.
TAIL = re.compile(r'(\d{1,3})\s*[-\u2013\u2014]\s*(\d{1,3})\s*$')
TAIL_ONE = re.compile(r'(\d{1,3})\s*$')
WORDS2 = re.compile(r'[A-Za-z]{3,}')
# The all-capitals group headings inside the contents, which are not departments.
GROUP = re.compile(r'^[A-Z][A-Z &\'.,/-]{4,}$')


def book(fy):
    lines, page = [], None
    path = os.path.join(PAGES, 'FY%s.ocr.txt' % fy)
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'^===PAGE (\d+)===', line)
        if m:
            page = int(m.group(1))
            continue
        if page:
            lines.append((page, re.sub(r'\s+', ' ',
                                       re.sub(r'^\s*\d+\|', '', line)).strip()))
    return lines


def offset(lines):
    """PDF page minus printed page, measured from the numbers the book prints itself.

    Every page of these reports ends with its own printed number on its last line or two.
    Taking the MEDIAN difference across the whole book survives the pages where the
    number is missing or misread, which a single sample would not.
    """
    by_page = collections.defaultdict(list)
    for p, t in lines:
        by_page[p].append(t)
    diffs = []
    for p, ls in by_page.items():
        for t in [x for x in ls[-3:] if x]:
            if re.fullmatch(r'\d{1,3}', t):
                diffs.append(p - int(t))
                break
    if not diffs:
        return 0
    diffs.sort()
    return diffs[len(diffs) // 2]


def _ref(t):
    """(from, to) if this contents line points at pages, 'none' if it says so, else None."""
    if not t or len(WORDS2.findall(t)) < 2:
        return None
    if NONE.search(t):
        return 'none'
    for pat in (RANGE, TAIL):
        m = pat.search(t)
        if m:
            return (int(m.group(1)), int(m.group(2)), m.start())
    for pat in (SINGLE, TAIL_ONE):
        m = pat.search(t)
        if m:
            return (int(m.group(1)), int(m.group(1)), m.start())
    return None


def contents_pages(lines):
    """The pages of the contents listing: where `Pages N-M` entries cluster."""
    hits = collections.Counter(p for p, t in lines if _ref(t))
    if not hits:
        return []
    # A CONTENTS PAGE IS DENSE AND NEAR THE FRONT, and it carries no money. Without the
    # last two tests every budget table in the book qualified -- a column of figures ends
    # in a number as surely as a contents entry does -- and FY2016 came back with 161
    # `departments`.
    money = collections.Counter()
    for p, t in lines:
        money[p] += t.count('$')
    dense = sorted(p for p, n in hits.items()
                   if n >= 8 and p <= 14 and money[p] <= 2)
    if not dense:
        return []
    # CONTIGUOUS FROM THE FIRST DENSE PAGE. The APPOINTED OFFICIALS listing a few pages
    # later is just as dense in trailing numbers -- every post is followed by its
    # holders and their term-expiry years -- so `Faye Silva 2013` reads exactly like a
    # contents entry. The contents is the run at the front; it does not resume.
    run = [dense[0]]
    for p in dense[1:]:
        if p == run[-1] + 1:
            run.append(p)
        else:
            break
    return run


def entries(fy):
    lines = book(fy)
    off = offset(lines)
    pgs = set(contents_pages(lines))
    if not pgs:
        return []
    out, section, carry = [], '', ''
    for p, t in lines:
        if p not in pgs or not t:
            continue
        if GROUP.match(t) and not RANGE.search(t):
            section = t.title()
            carry = ''
            continue
        # A NAME CAN WRAP. `Nashoba Associated Boards of` / `Health Pages 67-71`, and
        # `Housing Authority` / `Submitted` -- so a line with no page reference is held
        # and glued to the next one rather than dropped.
        whole = (carry + ' ' + t).strip() if carry else t
        ref = _ref(whole)
        if ref is None:
            carry = whole if len(whole) < 60 else ''
            continue
        carry = ''
        if ref == 'none':
            name = re.sub(r'\s+', ' ', NONE.split(whole)[0]).strip(' .-\u2013')
            name = re.sub(r'^(?:No\s+Report\s+)?Submitted\s+', '', name).strip()
            if len(name) >= 3 and not GROUP.match(name):
                out.append(dict(fy=fy, section=section, department=name,
                                printed_from='', printed_to='', pdf_from='', pdf_to='',
                                state='no report submitted', as_printed=whole[:160]))
            continue
        a, b, at = ref
        name = re.sub(r'\s+', ' ', whole[:at]).strip(' .-\u2013')
        # The scanner turns leader dots into letters: `Fire Department aaaaaaaaaaaado,`.
        name = re.sub(r'\s+[a-z]{4,}[.,]?$', '', name).strip(' .-\u2013')
        # `No Report` and `Submitted` are set on two lines, so the orphaned `Submitted`
        # lands at the FRONT of the next department's name: `Submitted Department of
        # Public Works`. Same for a whole entry swallowed mid-line.
        name = re.sub(r'^(?:No\s+Report\s+)?Submitted\s+', '', name).strip()
        name = re.sub(r'\s+(?:No\s+Report\s+)?Submitted$', '', name).strip()
        if not name or len(name) < 3 or GROUP.match(name):
            continue
        if b < a:                       # `Pages 44-43` -- the town's own transposition
            a, b = b, a
        out.append(dict(fy=fy, section=section, department=name,
                        printed_from=a, printed_to=b,
                        pdf_from=a + off, pdf_to=b + off,
                        state='report', as_printed=whole[:160]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows = []
    for f in sorted(glob.glob(os.path.join(PAGES, 'FY*.ocr.txt'))):
        m = re.search(r'FY(\d{4})\.ocr', f)
        if m:
            rows += entries(m.group(1))
    if a.check:
        old = list(csv.DictReader(open(OUT, encoding='utf-8'))) if os.path.exists(OUT) else []
        same = len(old) == len(rows) and all(
            all(str(r[k]) == o[k] for k in FIELDS) for r, o in zip(rows, old))
        if not same:
            print('STALE %s' % OUT)
            return 1
        return 0
    with open(OUT, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    per = collections.Counter(r['fy'] for r in rows)
    none = collections.Counter(r['fy'] for r in rows if r['state'] == 'no report submitted')
    print('%d contents entries across %d years' % (len(rows), len(per)))
    for fy in sorted(per):
        print('  FY%s  %3d departments, %d saying no report submitted'
              % (fy, per[fy], none[fy]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
