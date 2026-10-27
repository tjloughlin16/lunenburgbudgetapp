#!/usr/bin/env python3
"""SCORE A READER AGAINST THE ANSWER KEY: Textract and Apple Vision, on pages already proven.

    python3 scripts/textract_score.py 2011        # one report: needs its pages read by textract_pages.py

THE ANSWER KEY. Every financial page of the FY2011-FY2025 annual reports is `proven` in
sources/data/annual-report-pages.csv -- it closed on totals the page prints itself -- and the
figures read off it sit in the datasets its `proved_by` column names. So the right value of each
figure on those pages is already known, and a new reader can be scored with nobody checking by hand.

WHAT IS MEASURED, AND WHAT IS NOT. For each proven figure: does the reader return that number on
that page? Three ways, so they can be told apart:

  vision, anywhere      the free macOS Vision OCR already held in sources/town-budget/ocr/
  textract, anywhere    Textract's LINE blocks: did it read the digits at all
  textract, in a cell   Textract's TABLE cells: did it read them AND put them in a grid

THIS IS A PROXY, and it says so in its output. A figure found in a cell is not a figure placed in
the RIGHT cell, and neither is a page that would close by itself -- that needs the prove step,
which is not built. What it does establish: a figure the reader never returned cannot be proven
by anything downstream, so a miss here is a real miss. A hit is necessary, not sufficient.

Figures under 100 are scored separately: an account count of 40 or a rate of 2.5 appears
somewhere on most pages by chance, so a hit on one says little.
"""
import collections
import csv
import glob
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'sources' / 'data'
OUT = ROOT / 'build' / 'textract'

# Columns that hold a position, an identifier or a year -- never a figure the page prints as money.
NOT_FIGURES = {'fy', 'report_fy', 'page', 'page_pdf', 'page_printed', 'line_no', 'issue_seq', 'code',
               'account', 'fund_number', 'table', 'edition', 'as_of_fy', 'due_fy', 'plan_fiscal_year',
               'table_fiscal_year', 'column_year', 'program_fy', 'cpc_ranking', 'levy_year', 'copy',
               'n_values', 'panel', 'line', 'issue', 'as_of', 'cells_printed', 'row_check'}
NUM = re.compile(r'\d[\d,]*(?:\.\d+)?')


def numbers(text):
    out = set()
    for m in NUM.findall(text or ''):
        try:
            out.add(round(abs(float(m.replace(',', ''))), 2))
        except ValueError:
            pass
    return out


def answer_key(fy):
    """{(page, value): {dataset}} for every proven page of the report."""
    pages = [r for r in csv.DictReader(open(DATA / 'annual-report-pages.csv'))
             if r['fy'] == str(fy) and r['state'] == 'proven']
    proven = {int(r['page']) for r in pages}
    datasets = {d.strip() for r in pages for d in r['proved_by'].split(',') if d.strip()}
    key = collections.defaultdict(set)
    for d in sorted(datasets):
        path = DATA / (d + '.csv')
        if not path.exists():
            continue
        for r in csv.DictReader(open(path, newline='')):
            if str(r.get('fy') if r.get('report_fy') in (None, '') else r.get('report_fy')) != str(fy):
                continue
            try:
                page = int(r.get('page_pdf') or r.get('page') or 0)
            except ValueError:
                continue
            if page not in proven:
                continue
            cols = ['value'] if d == 'pages-read' else [c for c in r if c not in NOT_FIGURES]
            for c in cols:
                v = (r.get(c) or '').strip().replace(',', '').replace('$', '')
                if re.fullmatch(r'-?\(?\d+(\.\d+)?\)?', v):
                    key[(page, round(abs(float(v.strip('()'))), 2))].add(d)
    return key, proven


def report_pdf(fy):
    hits = glob.glob(str(ROOT / ('sources/town-annual-reports/docs/*-fy-%d-annual-town-report.pdf' % fy)))
    if len(hits) != 1:
        raise SystemExit('expected one FY%d report, found %s' % (fy, hits))
    return Path(hits[0])


def by_page(path, page_col, text_col, delim='\t'):
    got = collections.defaultdict(set)
    if not path.exists():
        return None
    for r in csv.DictReader(open(path, newline=''), delimiter=delim):
        got[int(r[page_col])] |= numbers(r[text_col])
    return got


def main():
    fy = int(sys.argv[1])
    pdf = report_pdf(fy)
    stem = pdf.stem
    key, proven = answer_key(fy)
    readers = {
        'vision, anywhere': by_page(ROOT / 'sources/town-budget/ocr' / (stem + '.tsv'), 'page', 'text'),
        'textract, anywhere': by_page(OUT / 'out' / (stem + '.lines.tsv'), 'page', 'text'),
        'textract, in a cell': by_page(OUT / 'out' / (stem + '.cells.tsv'), 'page', 'text'),
    }
    if readers['textract, anywhere'] is None:
        raise SystemExit('no Textract output for %s: run textract_pages.py %s --mapped first' % (stem, pdf))
    read = set(readers['textract, anywhere'])
    pages = sorted(p for p in proven if p in read)
    unread = sorted(proven - read)

    lines = ['# FY%d: Textract and Vision against the answer key' % fy, '',
             'Report `%s`. %d proven pages; Textract has read %d of them%s.'
             % (pdf.name, len(proven), len(pages), (' (not yet: %s)' % unread) if unread else ''), '',
             '**A proxy, not a proof.** "Found" means the reader returned that number on that page. '
             'A miss is a real miss -- nothing downstream can prove a figure never read. A hit is '
             'necessary, not sufficient: it does not show the figure was placed in the right cell.', '']
    for band, test in (('figures of 100 or more', lambda v: v >= 100), ('figures under 100', lambda v: v < 100)):
        figs = [(p, v) for (p, v) in key if p in pages and test(v)]
        lines += ['## %s: %d proven' % (band.capitalize(), len(figs)), '',
                  '| reader | found | share |', '|---|---:|---:|']
        for name, got in readers.items():
            n = sum(1 for p, v in figs if got and v in got.get(p, ()))
            lines.append('| %s | %d | %.1f%% |' % (name, n, 100 * n / len(figs) if figs else 0))
        lines.append('')

    big = [(p, v) for (p, v) in key if p in pages and v >= 100]
    lines += ['## By page (figures of 100 or more)', '',
              '| page | proven | vision | textract | in a cell |', '|---:|---:|---:|---:|---:|']
    for p in pages:
        f = [v for q, v in big if q == p]
        cnt = [sum(v in (g.get(p, ()) if g else ()) for v in f) for g in readers.values()]
        lines.append('| %d | %d | %d | %d | %d |' % (p, len(f), *cnt))
    v, t = readers['vision, anywhere'] or {}, readers['textract, anywhere']
    only_v = sorted((p, x) for p, x in big if x in v.get(p, ()) and x not in t.get(p, ()))
    only_t = sorted((p, x) for p, x in big if x in t.get(p, ()) and x not in v.get(p, ()))
    neither = sorted((p, x) for p, x in big if x not in t.get(p, ()) and x not in v.get(p, ()))
    for title, rows in (('Vision read it, Textract did not', only_v), ('Textract read it, Vision did not', only_t),
                        ('Neither read it', neither)):
        lines += ['', '## %s: %d' % (title, len(rows)), '']
        lines += ['- p%d  %s  (%s)' % (p, '{:,.2f}'.format(x), ', '.join(sorted(key[(p, x)]))) for p, x in rows[:40]]
        if len(rows) > 40:
            lines.append('- ... and %d more' % (len(rows) - 40))
    out = OUT / ('score-fy%d.md' % fy)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines[:30]))
    print('... full report: %s' % out.relative_to(ROOT))


if __name__ == '__main__':
    main()
