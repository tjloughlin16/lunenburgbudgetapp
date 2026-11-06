#!/usr/bin/env python3
"""Year-by-year series read out of the annual town reports, one family at a time.

Most of what the reports print over time is prose or a short list, in a layout that changes
every few years, so no table reader gets it. A family is therefore READ, by a person or an
agent, into `sources/data/report-series/<family>.csv`, and this script is what stops a read
being taken on trust (CLAUDE.md rules 13, 13c):

  * every row quotes the page, and the quote must be on the cited page of the edition's text;
  * every figure in `value` must be in its quote, unless the row says it was spelled out;
  * where the page prints a total, the parts are summed and compared. A year that does not
    tie is LABELLED with the residual, never dropped and never adjusted;
  * `<family>.coverage.csv` holds one row per edition: `held`, or `not printed` with the
    pages looked at. An edition with neither is a hole, and the build refuses (rule 13c:
    a pattern that found nothing is not an absence).

It writes `sources/data/series-<family>.csv`, which build_db.py loads by glob, and
`sources/data/series-coverage.csv`, one row per family per edition.

    python3 scripts/report_series.py            # rebuild every family
    python3 scripts/report_series.py --check    # fail if a read fails or an output is stale

`our_grouping` is ours and says so in its name: the town's category names change by era, and
a grouping across them is a judgement, not something the reports print.
"""
import csv
import glob
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
READS = os.path.join(ROOT, 'sources', 'data', 'report-series')
DATA = os.path.join(ROOT, 'sources', 'data')
TEXT = os.path.join(ROOT, 'sources', 'town-annual-reports', 'text')
BUDGET_PAGES = os.path.join(ROOT, 'sources', 'town-budget', 'pages')

READ_COLS = ['year', 'year_basis', 'edition', 'pdf_page', 'row_group', 'row_role', 'measure', 'value',
             'unit', 'our_grouping', 'quote', 'note']
OUT_COLS = READ_COLS + ['group_parts_sum', 'group_total_printed', 'group_ties', 'quote_found']
COVERAGE_COLS = ['family', 'edition', 'status', 'pages_looked', 'note']
ROLES = {'total', 'part', 'single'}
TIES_TOLERANCE = 0.005  # below a cent; a count either ties or it does not

# Every family says what it is, for the source catalogue (build_source_index.py).
FAMILIES = {
    'fire-calls': ('Fire Department calls by year and category, 1959-FY2025',
                   'What the Fire Department printed about its calls in every annual report: the '
                   'total and each category as printed, with the quote and the PDF page. Parts '
                   'are tied to the printed total, and a year that does not tie says so.'),
}


def catalogue_items():
    """(path, title, stars, description) for build_source_index.py, one family at a time."""
    items = [('data/series-coverage.csv', 'Which annual reports were checked for each series', 1,
              'One row per series per edition: whether the series is printed there and, if not, '
              'which pages were looked at.')]
    for family, (title, what) in sorted(FAMILIES.items()):
        items += [('data/series-%s.csv' % family, title, 2, what),
                  ('data/report-series/%s.csv' % family, title + ': the read', 1,
                   'Written by us. The read itself, before the checks in report_series.py add '
                   'their columns.'),
                  ('data/report-series/%s.coverage.csv' % family, title + ': editions looked at', 1,
                   'Written by us. Every edition, and whether the series is printed there.')]
    return items


def normalise(s):
    """Letters and digits only, so line wraps, column gaps and OCR punctuation do not matter."""
    s = re.sub(r'(?m)^\s*\d+\|', ' ', s)     # the budget page files number their lines
    s = re.sub(r'([A-Za-z])-\s*\n\s*([a-z])', r'\1\2', s)  # a word hyphenated across a line
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()


def editions():
    """edition label -> every text layer we hold for it."""
    out = {}
    for path in sorted(glob.glob(os.path.join(TEXT, '*.txt'))):
        m = re.search(r'-fy-(\d{4})-annual', path)
        if m:
            out.setdefault('FY' + m.group(1), []).append(path)
            continue
        m = re.search(r'-(\d{4})-annual', path) or re.search(r'(\d{4}) Annual', path)
        if m:
            out.setdefault(m.group(1), []).append(path)
    for path in sorted(glob.glob(os.path.join(BUDGET_PAGES, 'FY*.txt'))):
        out.setdefault(os.path.basename(path)[:6], []).append(path)
    return out


_cache = {}


def pages_of(path):
    if path not in _cache:
        with open(path, errors='replace') as f:
            parts = re.split(r'===PAGE (\d+)===[^\n]*\n?', f.read())
        _cache[path] = {int(parts[i]): normalise(parts[i + 1]) for i in range(1, len(parts), 2)}
    return _cache[path]


def quote_on_page(quote, edition, page_field, eds):
    """Is the quote on this page? A row may cite a span, `14-15`, when a list crosses a page."""
    n = normalise(quote)
    pages = [int(p) for p in re.findall(r'\d+', page_field)]
    if len(pages) == 2:
        pages = list(range(pages[0], pages[1] + 1))
    joined = ''
    for path in eds.get(edition, []):
        got = pages_of(path)
        text = ' '.join(got.get(p, '') for p in pages)
        if n and n in text:
            return True
        joined += ' ' + text
    # A two-column page reads label and figure apart: both must still be on the page.
    words = n.split()
    return bool(words) and all(re.search(r'\b%s\b' % re.escape(w), joined) for w in words) and 'apart'


def read_family(path, eds, problems):
    family = os.path.basename(path)[:-4]
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != READ_COLS:
            problems.append('%s: columns are %s' % (family, reader.fieldnames))
            return family, []
        rows = list(reader)
    groups = {}
    for i, r in enumerate(rows, 2):
        where = '%s line %d (%s p%s)' % (family, i, r['edition'], r['pdf_page'])
        if r['row_role'] not in ROLES:
            problems.append('%s: role %r' % (where, r['row_role']))
        if r['edition'] not in eds:
            problems.append('%s: no such edition' % where)
        found = quote_on_page(r['quote'], r['edition'], r['pdf_page'], eds)
        r['quote_found'] = 'apart' if found == 'apart' else 'yes' if found else 'no'
        if r['quote_found'] == 'no':
            problems.append('%s: quote not on the page: %r' % (where, r['quote'][:70]))
        digits = r['value'].replace(',', '')
        if digits and 'spelled' not in r['note'] and 'misread' not in r['note'] \
                and not re.search(r'(?<![\d.])%s(?![\d])' % re.escape(digits),
                                  r['quote'].replace(',', '')):
            problems.append('%s: value %s is not in its quote' % (where, r['value']))
        groups.setdefault((r['year'], r['edition'], r['row_group']), []).append(r)
    for rs in groups.values():
        total = [r for r in rs if r['row_role'] == 'total']
        parts = [float(r['value'].replace(',', '')) for r in rs if r['row_role'] == 'part' and r['value']]
        printed = float(total[0]['value'].replace(',', '')) if total else None
        psum = sum(parts) if parts else None
        ties = 'no total printed' if printed is None else 'no parts printed' if psum is None else \
            'yes' if abs(printed - psum) < TIES_TOLERANCE else 'no, parts %+g against the total' % (psum - printed)
        for r in rs:
            r['group_parts_sum'] = '' if psum is None else '%g' % psum
            r['group_total_printed'] = '' if printed is None else '%g' % printed
            r['group_ties'] = ties
    return family, rows


def csv_text(cols, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, cols, lineterminator='\n', extrasaction='ignore')
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def build(eds, problems):
    outputs, coverage = {}, []
    for path in sorted(glob.glob(os.path.join(READS, '*.csv'))):
        if path.endswith('.coverage.csv'):
            continue
        family, rows = read_family(path, eds, problems)
        if family not in FAMILIES:
            problems.append('%s: add it to FAMILIES, or the catalogue cannot describe it' % family)
        outputs[os.path.join(DATA, 'series-%s.csv' % family)] = csv_text(OUT_COLS, rows)
        cov_path = path[:-4] + '.coverage.csv'
        if not os.path.exists(cov_path):
            problems.append('%s: no coverage file; every edition must be accounted for' % family)
            continue
        with open(cov_path, newline='') as f:
            cov = {c['edition']: c for c in csv.DictReader(f)}
        held = {r['edition'] for r in rows}
        for ed in sorted(eds):
            c = cov.get(ed)
            if c is None:
                problems.append('%s: edition %s was not looked at' % (family, ed))
                continue
            if (c['status'] == 'held') != (ed in held):
                problems.append('%s: edition %s says %r, and holds %s rows'
                                % (family, ed, c['status'], 'some' if ed in held else 'no'))
            if c['status'] != 'held' and not c['pages_looked'].strip():
                problems.append('%s: edition %s says %r but names no page looked at'
                                % (family, ed, c['status']))
            coverage.append(dict(c, family=family))
    outputs[os.path.join(DATA, 'series-coverage.csv')] = csv_text(COVERAGE_COLS, coverage)
    return outputs


def main():
    check = '--check' in sys.argv
    eds, problems = editions(), []
    outputs = build(eds, problems)
    if check:
        for path, text in outputs.items():
            old = open(path).read() if os.path.exists(path) else None
            if old != text:
                problems.append('%s is stale' % os.path.relpath(path, ROOT))
    for p in problems:
        print('FAIL', p)
    if problems:
        return 1
    if not check:
        for path, text in outputs.items():
            with open(path + '.tmp', 'w') as f:
                f.write(text)
            os.replace(path + '.tmp', path)
    for path, text in sorted(outputs.items()):
        print('%s %s: %d rows' % ('ok' if check else 'wrote', os.path.relpath(path, ROOT), text.count('\n') - 1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
