#!/usr/bin/env python3
"""WHICH PAGES OF AN ANNUAL REPORT ARE FINANCIAL -- so Textract's Tables, at ten times the price of
text, is paid for only where a money table can be.

    python3 scripts/find_financial_pages.py --score        # against the ten answer-key reports; exit 1 on a miss
    python3 scripts/find_financial_pages.py --list         # how many pages it picks in each unread report
    python3 scripts/find_financial_pages.py --list 1987    # which pages, with each page's first line

TJ, 28 October 2026: text on every page, then Tables only on financial pages. The 42 reports of
1959-2000 are 5,170 pages; Tables on all of them is ~$78 against a $50 month.

THE RULE: a page is financial if its Textract TEXT read (already paid for, every page) holds at
least MIN_MONEY money figures -- `1,234`, `1,234.56`, `12.50`, `$7940` -- counted as words, with
the punctuation a sentence leaves on them stripped. Nothing else: no headings, no keywords.

THE ANSWER KEY is 2001-2010, read for Tables on every page on purpose. Each worker marked every
table `financial` yes or no in sources/data/report-tables/<ed>/map.csv; a page is financial there
if any table on it is. Measured 28 October 2026 (re-run --score, never quote this line):
334 of 334 financial pages found, 466 of 1,076 picked. A miss loses data and an extra page costs
1.5 cents, so the threshold is set for recall.

WHAT IT DOES NOT PICK, by design: count tables with no money in them -- elections, enrollment,
vital records, officials, department activity. Workers built datasets from those in 2001-2010
(`financial` = no); for 1959-2000 their text is read and searchable and their tables are not.

Checked against older printing (1959-1979) by listing rejected pages with many numbers: they are
enrollment, elections and deaths. Two misses that check found are fixed in MONEY: a figure ending
a sentence (`$700,000.00.`) and whole dollars with no comma (`$7940`). 1978 p35 (revenue sources
as percentages) is rejected and is a graph, not a table -- p36: "The graphs on the preceding page".
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import textract_pages as T                                            # noqa: E402
import read_annual_reports as R                                       # noqa: E402

MIN_MONEY = 3
MONEY = re.compile(r'(?<![\w.])\$?\(?\d{1,3}(?:[,.]\d{3})+(?:\.\d{2})?\)?(?!\d)'
                   r'|(?<![\w.])\$?\d+\.\d{2}(?!\d)'
                   r'|\$\d+(?!\d)')
KEYS = T.M.ROOT / 'sources' / 'data' / 'report-tables'


def page_words(sha, page):
    """The WORDs and LINEs of a page's text read, or None if it was never read."""
    cp = T.cache_path(sha, page, 'text')
    if not cp.exists():
        return None
    blocks = json.loads(cp.read_text())['Blocks']
    return ([b['Text'] for b in blocks if b['BlockType'] == 'WORD'],
            [b['Text'] for b in blocks if b['BlockType'] == 'LINE'])


def money_count(words):
    return sum(1 for w in words if MONEY.fullmatch(w.strip(',;:.')))


def financial_pages(path):
    """The financial pages of a report, from its text read. Refuses a report whose text read is
    incomplete: an unread page is not a non-financial one."""
    sha, n = T.sha256_of(path), T.page_count(path)
    out = []
    for p in range(1, n + 1):
        got = page_words(sha, p)
        if got is None:
            raise SystemExit('%s p%d has no text read; read the text first '
                             '(read_annual_reports.py --feature text)' % (Path(path).name, p))
        if money_count(got[0]) >= MIN_MONEY:
            out.append(p)
    return out


def score():
    tp = picked = total = key = 0
    misses = []
    for mp in sorted(KEYS.glob('*/map.csv')):
        ed = json.loads((mp.parent / 'edition.json').read_text())
        pdf = T.M.ROOT / ed['pdf']
        fin = {int(r['page']) for r in csv.DictReader(open(mp, newline='')) if r['financial'] == 'yes'}
        got = set(financial_pages(pdf))
        n = T.page_count(pdf)
        tp += len(got & fin)
        picked += len(got)
        total += n
        key += len(fin)
        misses += [(ed['edition'], p) for p in sorted(fin - got)]
        print('  %s  %3d pages  %3d financial  %3d picked  %d missed'
              % (ed['edition'], n, len(fin), len(got), len(fin - got)))
    print('found %d of %d financial pages; picked %d of %d (%.0f%% of what it picks is financial)'
          % (tp, key, picked, total, 100 * tp / max(picked, 1)))
    for ed, p in misses:
        words, lines = page_words(T.sha256_of(T.M.ROOT / json.loads(
            (KEYS / ed / 'edition.json').read_text())['pdf']), p)
        print('  MISSED %s p%d: %d money figure(s); %s' % (ed, p, money_count(words), ' | '.join(lines[:2])[:90]))
    return 1 if misses else 0


def listing(year=None):
    total = 0
    for y, path in R.reports():
        if year and y != year:
            continue
        sha, n, todo = R.todo_of(path, 'tables')
        if not todo and not year:
            continue
        pages = financial_pages(path)
        total += len(set(pages) & set(todo))
        print('  %d  %-40s %4d pages  %4d financial  %4d of them unread for tables'
              % (y, path.name, n, len(pages), len(set(pages) & set(todo))))
        if year:
            for p in pages:
                print('    p%-4d %s' % (p, ' | '.join(page_words(sha, p)[1][:2])[:100]))
    print('%d financial page(s) unread for tables: $%.2f at $%.4f'
          % (total, total * T.M.PRICE_PER_PAGE['tables'], T.M.PRICE_PER_PAGE['tables']))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--score', action='store_true')
    g.add_argument('--list', nargs='?', type=int, const=0, metavar='YEAR')
    a = ap.parse_args()
    if a.score:
        sys.exit(score())
    listing(a.list or None)


if __name__ == '__main__':
    main()
