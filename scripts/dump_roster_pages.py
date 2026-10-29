#!/usr/bin/env python3
"""Write every school staff roster page to text, located from the catalogue.

**The pages come from `sources/data/annual-report-catalogue.csv`**, which was built by
reading all sixteen reports end to end. They are not found by matching a heading, and the
reason is the whole finding of this work: the rosters are called
`PRIMARY SCHOOL FACULTY / STAFF ROSTER` in FY2011, `THMS STAFF ROSTER` in FY2012,
`FACULTY/STAFF ROSTER` in FY2013, nothing at all in FY2019 and FY2021, and
`FY 21 PRIMARY SCHOOL ROSTER` in FY2020. Several continue onto a second page with no
heading repeated.

A search for `STAFF ROSTER` found 29 pages across 10 years. The catalogue has 51 blocks
across all 15 years, and the difference is not small: FY2025 alone went from 4 pages to 8,
which is why its roster count read as a district that had shrunk by a third.

The schools change too, and a series that assumes four fixed schools will be wrong.
FY2011 has a `THOMAS C. PASSIOS ELEMENTARY SCHOOL`, and `TURKEY HILL MIDDLE SCHOOL` in
FY2011-2013 becomes `TURKEY HILL ELEMENTARY SCHOOL (THES)` later.

Output is one file per page, every non-blank line numbered, because line accounting is the
only check this data has -- a roster prints no total.

    python3 scripts/dump_roster_pages.py [--out <dir>]
"""

import argparse
import csv
import os
import re
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings('ignore')

import pdf_tables as T
import report_pages as RP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The sixteen annual town reports moved out of town-budget/ on 5 September 2026.
# Every script here globs '*annual-town-report*.pdf' under this path, and a glob
# that matches nothing raises nothing -- so pointing at the folder they left made
# each of these a silent no-op rather than an error.
DOCS = os.path.join(ROOT, 'sources', 'town-annual-reports', 'docs')
CATALOGUE = os.path.join(ROOT, 'sources', 'data', 'annual-report-catalogue.csv')

IS_SCHOOL_ROSTER = re.compile(
    r'(roster|faculty|staff|personnel)', re.I)
IS_SCHOOL = re.compile(
    r'(school|primary|turkey|middle|high|thes|passios|district|teacher|central office)',
    re.I)
# Department rosters are real data and belong in the archive, but they are a different
# dataset with a different grain -- a firefighter is not a teacher -- and mixing them here
# would put them in the school series.
NOT_SCHOOL = re.compile(r'\b(fire|police|dpw|highway|library trustee)\b', re.I)


def page_numbers(field):
    """Every page number mentioned, from a free-text page field.

    The catalogue records what the reader saw, and for a roster spread over four buildings
    that is `107-108 (Primary), 110-111 (THMS), 114-115 (LHS)`. Parsing it loosely is
    right: over-including a page costs one file, and the reading step drops it.
    """
    pages = set()
    for a, b in re.findall(r'(\d+)\s*[-–]\s*(\d+)', field or ''):
        if int(b) >= int(a) and int(b) - int(a) < 30:
            pages.update(range(int(a), int(b) + 1))
    for n in re.findall(r'(?<![\d-])(\d{1,3})(?![\d-])', field or ''):
        pages.add(int(n))
    return sorted(pages)


def school_of(text):
    t = text.upper()
    for name, pat in [('passios', r'PASSIOS'),
                      ('turkey-hill', r'\bTHES\b|TURKEY HILL'),
                      ('primary', r'PRIMARY'),
                      ('middle', r'MIDDLE SCHOOL|\bLMS\b'),
                      ('high', r'HIGH SCHOOL|\bLHS\b'),
                      ('central-office', r'CENTRAL OFFICE|SUPERINTENDENT')]:
        if re.search(pat, t):
            return name
    return 'unknown'


# THE REPORTS READ ON AWS. TJ, 28 October 2026: the 1959-2010 reports were read by Textract,
# not Vision, and this reader took its lines only from report_pages -- Vision's box files --
# so their rosters could not be dumped at all. Textract's lines are one per text run, each
# with its position; a roster is a column layout (`Name    Position`), so the runs that share
# a row are put back together left to right with a gap, which is what the Vision rendering
# preserves and what the reading step expects. Everything after this file is engine-blind.
TEXTRACT_OUT = os.path.join(ROOT, 'build', 'textract', 'out')
GAP = '    '


def textract_lines(doc):
    """{page: [line, ...]} rebuilt into rows from Textract's lines.tsv, or {} if none."""
    path = os.path.join(TEXTRACT_OUT, os.path.splitext(doc)[0] + '.lines.tsv')
    if not os.path.exists(path):
        return {}
    by_page = {}
    for r in csv.DictReader(open(path, newline=''), delimiter='\t'):
        by_page.setdefault(int(r['page']), []).append(
            (float(r['top']), float(r['height']), float(r['left']), r['text']))
    out = {}
    for page, runs in by_page.items():
        heights = sorted(h for _, h, _, _ in runs if h > 0)
        band = (heights[len(heights) // 2] if heights else 0.01) * 0.5
        rows = []
        for top, h, left, text in sorted(runs, key=lambda t: t[0] + t[1] / 2):
            mid = top + h / 2
            if rows and abs(mid - rows[-1][0]) <= band:
                rows[-1][1].append((left, text))
            else:
                rows.append([mid, [(left, text)]])
        out[page] = [GAP.join(t for _, t in sorted(cells)) for _, cells in rows]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--boxes', default=os.path.join(ROOT, 'sources', 'town-budget', 'ocr'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'sources', 'data', 'rosters'))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    wanted = {}
    for r in csv.DictReader(open(CATALOGUE)):
        blob = f"{r['name']} {r['printed_heading']} {r['what_it_is']}"
        if not (IS_SCHOOL_ROSTER.search(blob) and IS_SCHOOL.search(blob)):
            continue
        if NOT_SCHOOL.search(blob):
            continue
        for p in page_numbers(r['pages']):
            wanted.setdefault((r['edition'], r['document']), set()).add(p)

    written, per_year, sparse = [], [], []
    for (edition, doc), pages in sorted(wanted.items()):
        fy = re.search(r'(\d{4})', edition).group(1)
        # A calendar edition (1959-2010) is labelled by its year alone, never as FY.
        label = edition if not edition.startswith('FY') else f'FY{fy}'
        # Rosters are column layouts, so the rendering that preserves column POSITION is
        # the one to read. The text layer collapses `Name    Role` to single spaces.
        # Calendar editions only: FY2011 has a 29-page Textract pilot, and its rosters stay
        # on the Vision reading they were proven on.
        tx = textract_lines(doc) if not edition.startswith('FY') else {}
        if tx:
            text, ocr = {}, tx
        else:
            text = RP.load(edition)
            ocr = RP.load(edition, ocr=True)
        got = []
        for page in sorted(pages):
            lines = ocr.get(page) or text.get(page) or []
            keep = [l.rstrip() for l in lines if l.strip()]
            if not keep:
                sparse.append((fy, page, 0))
                continue
            if len(keep) < 8:
                sparse.append((fy, page, len(keep)))
            school = school_of('\n'.join(keep[:12]))
            name = f'{label}-p{page:03d}-{school}.txt'
            with open(os.path.join(args.out, name), 'w') as fh:
                fh.write(f'# {doc} page {page} -- {label} -- school: {school}'
                         f'{" -- read by Textract" if tx else ""}\n')
                fh.write(f'# {len(keep)} non-blank lines. '
                         f'Every one must be accounted for.\n\n')
                for i, l in enumerate(keep, 1):
                    fh.write(f'{i:4d}| {l}\n')
            written.append((name, len(keep)))
            got.append(page)
        per_year.append((fy, len(got), ','.join(str(p) for p in got)))

    # The denominator, per year.
    print(f'{"FY":<8}{"pages":>6}  pages')
    for fy, n, pages in sorted(per_year):
        print(f'{fy:<8}{n:>6}  {pages}')
    print(f'\n{len(written)} roster pages -> {os.path.relpath(args.out, ROOT)}, '
          f'{sum(c for _, c in written)} lines to account for')
    if sparse:
        print(f'\n{len(sparse)} pages the catalogue lists but the text layer barely '
              f'renders -- written anyway, and NOT to be read as thin rosters:')
        for fy, page, n in sparse:
            print(f'  FY{fy} p{page}: {n} lines')


if __name__ == '__main__':
    main()
