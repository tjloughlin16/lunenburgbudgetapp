#!/usr/bin/env python3
"""What table is on which page of each annual town report, and can it be read.

Step 1 of `notes/process/WRITING-AN-ANALYSIS.md`, and the step
`notes/findings/TOWN-ARCHIVE.md` says nothing can be extracted before. A 2011 report and a
2025 report are not the same document: they carry different sections, in a different order,
under headings the town rewords between years. Writing an extractor against one year and
running it over fifteen produces figures for the years that happen to match and silence for
the rest, and silence is indistinguishable from a table that is not there.

So this finds the tables and says nothing about what they contain. For each page it records
the section it appears to belong to, which extraction mode reads it, how many columns the
rows agree on, and how many figures are on it. That is enough to decide where an extractor
should point and nowhere near enough to quote from.

**It prints its denominator.** Pages surveyed out of pages held, and every report that
could not be read at all -- because a survey that finds nothing prints nothing, and nothing
reads as absence. That is `search_minutes.py`'s rule and it applies with more force here,
where six of the sixteen reports have no text layer and will show up as empty unless
somebody is told why.

    python3 scripts/survey_annual_reports.py
    python3 scripts/survey_annual_reports.py --boxes <dir>   # include OCR'd scans
"""

import argparse
import csv
import glob
import os
import re
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings('ignore')

import pypdf
import pdf_tables as T

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'sources', 'town-budget', 'docs')
OUT = os.path.join(ROOT, 'sources', 'data', 'annual-report-survey.csv')

# The headings the town actually prints. Several are worded differently between years --
# `ACCOUNTS, SUMMARY` and `SUMMARY OF APPROPRIATIONS` are the same table -- which is the
# reason this file exists rather than a constant in an extractor.
SECTIONS = [
    ('receipts',        r'SUMMARY OF RECEIPTS|\bRECEIPTS\s*[-—]\s*JUNE'),
    ('appropriations',  r'ACCOUNTS,?\s+SUMMARY|SUMMARY OF APPROPRIATION|'
                        r'APPROPRIATION\s+SUMMARY|GENERAL FUND EXPENDITURES'),
    ('special_revenue', r'SPECIAL REVENUE FUND'),
    ('capital_project', r'CAPITAL PROJECT FUND'),
    ('trust_funds',     r'\bTRUST FUND'),
    ('enterprise',      r'ENTERPRISE FUND'),
    ('balance_sheet',   r'BALANCE SHEET'),
    ('debt',            r'BONDED INDEBTEDNESS|DEBT SERVICE|LONG.TERM DEBT'),
    ('payroll',         r'PAYROLL REPORT|WAGES PAID|EMPLOYEE EARNINGS|GROSS WAGES|'
                        r'SALARIES PAID'),
    ('staff_roster',    r'STAFF ROSTER'),
    ('valuation',       r'TOTAL VALUATION|ASSESSED VALUATION'),
    ('tax_rate',        r'TAX RATE|TAX RECAP'),
    ('town_meeting',    r'TOWN MEETING'),
    ('school_report',   r'SCHOOL COMMITTEE|SUPERINTENDENT|SCHOOL DEPARTMENT'),
]

# A line that prints a total AND a figure. The anchor a table can be reconciled against --
# rule 13 -- and the single most useful thing to know about a table before writing an
# extractor for it, because a table with no printed total can be extracted and never
# checked.
TOTAL_LINE = re.compile(
    r'((?:GRAND\s+)?TOTAL[A-Za-z0-9 ,&/\.\'\-]{0,44}?)\s*\$?\s?'
    r'([\d,]+\.\d\d)')


def fiscal_year(name):
    m = re.search(r'fy-?(\d{4})', name)
    return int(m.group(1)) if m else None


def sections_on(text):
    return [n for n, pat in SECTIONS if re.search(pat, text, re.I)]


def totals_on(lines):
    """Printed totals on the page, as `label=value`, most specific first.

    Recorded because it decides whether a table is extractable in the sense this project
    means: a table with a printed total can be checked against itself, and one without
    can only be transcribed and hoped over.
    """
    out = []
    for line in lines:
        for m in TOTAL_LINE.finditer(line):
            label = re.sub(r'\s+', ' ', m.group(1)).strip()
            out.append(f'{label}={m.group(2)}')
    seen, uniq = set(), []
    for t in out:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq[:6]


def survey_page(page):
    """One page, described by measurement. Never raises -- a page that cannot be read is a
    row saying so, not a crash that ends the survey twenty documents early."""
    try:
        mode, scores = T.instrument(page)
    except Exception as e:
        return {'mode': '', 'gutters': 0, 'money': 0, 'chars': 0, 'rows': 0,
                'sections': '', 'totals': '',
                'note': f'unreadable: {type(e).__name__}'}
    if mode is None:
        return {'mode': '', 'gutters': 0, 'money': 0, 'chars': 0, 'rows': 0,
                'sections': '', 'totals': '',
                'note': 'no text layer -- scan, needs OCR'}
    lines = T.page_lines(page, mode)
    figs = T.figure_rows(lines)
    ruler = T.column_ruler(figs)
    return {
        'mode': mode,
        'gutters': len(ruler),
        'money': T.money_tokens(lines),
        'chars': scores[mode]['chars'],
        'rows': len(figs),
        'sections': '|'.join(sections_on('\n'.join(lines))),
        'totals': ' ; '.join(totals_on(lines)),
        'note': '' if T.money_tokens(lines) else 'text, no figures',
    }


def survey_boxes(boxes_by_page, page_no):
    boxes = boxes_by_page.get(page_no, [])
    if not boxes:
        return None
    lines = T.layout_from_boxes(boxes)
    figs = T.figure_rows(lines)
    ruler = T.column_ruler(figs)
    return {
        'mode': 'ocr',
        'gutters': len(ruler),
        'money': T.money_tokens(lines),
        'chars': sum(len(b['text']) for b in boxes),
        'rows': len(figs),
        'sections': '|'.join(sections_on('\n'.join(lines))),
        'totals': ' ; '.join(totals_on(lines)),
        'note': f'{len(T.low_confidence(boxes))} low-confidence money line(s)',
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--boxes', default=os.path.join(ROOT, 'sources', 'town-budget', 'ocr'),
                    help="directory of ocr_pdf.swift --boxes TSVs")
    args = ap.parse_args()

    pdfs = sorted(glob.glob(os.path.join(DOCS, '*annual-town-report*.pdf')),
                  key=lambda p: (fiscal_year(os.path.basename(p)) or 0, p))
    rows, held, surveyed, unreadable = [], 0, 0, []

    for path in pdfs:
        name = os.path.basename(path)
        fy = fiscal_year(name)
        boxes_by_page = {}
        if args.boxes:
            tsv = os.path.join(args.boxes, name.replace('.pdf', '.tsv'))
            if os.path.exists(tsv):
                for b in T.read_boxes(tsv):
                    boxes_by_page.setdefault(b['page'], []).append(b)
        try:
            reader = pypdf.PdfReader(path)
            pages = len(reader.pages)
        except Exception as e:
            unreadable.append((name, f'{type(e).__name__}: {e}'))
            continue

        held += pages
        scanned_pages = 0
        for i, page in enumerate(reader.pages):
            r = survey_page(page)
            if r['mode'] == '':
                scanned_pages += 1
                ocr = survey_boxes(boxes_by_page, i + 1)
                if ocr:
                    r = ocr
            if r['mode']:
                surveyed += 1
            rows.append({'fy': fy, 'document': name, 'page': i + 1, **r})

        mine = [r for r in rows if r['document'] == name]
        got = sum(1 for r in mine if r['mode'])
        withfigs = sum(1 for r in mine if r['money'])
        flag = ''
        if scanned_pages and not boxes_by_page:
            flag = f'  <- {scanned_pages} scanned pages, no OCR boxes supplied'
        print(f'  FY{fy}  {pages:>4} pages  {got:>4} readable  '
              f'{withfigs:>4} carry figures{flag}')

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['fy', 'document', 'page', 'mode', 'gutters',
                                           'money', 'chars', 'rows', 'sections',
                                           'totals', 'note'])
        w.writeheader()
        w.writerows(rows)

    # The denominator. A survey that finds nothing must not read as absence.
    figs_pages = sum(1 for r in rows if r['money'])
    print(f'\n{surveyed} of {held} pages readable, across {len(pdfs)} reports'
          f' ({held - surveyed} have no text layer at all and no OCR)')
    print(f'{figs_pages} of those carry figures; the rest are prose, names or images.'
          f'\n  A page with no figures is not a page with no text -- the staff rosters'
          f' are lists of names and read perfectly.')
    if unreadable:
        print('reports that could not be opened at all:')
        for n, why in unreadable:
            print(f'  {n}: {why}')
    print(f'wrote {os.path.relpath(OUT, ROOT)}')

    found = {}
    for r in rows:
        for s in (r['sections'] or '').split('|'):
            if s:
                found.setdefault(s, set()).add(r['fy'])
    print('\nsection            years it appears in')
    for name, _ in SECTIONS:
        yrs = sorted(found.get(name, []))
        print(f'  {name:<18} {len(yrs):>2}  ' + (
            ' '.join(str(y)[2:] for y in yrs) if yrs else '(none found)'))


if __name__ == '__main__':
    main()
