"""Every financial page in every annual town report, and whether anything has read it.

    python3 scripts/map_annual_report_pages.py
    python3 scripts/map_annual_report_pages.py --check

Writes `sources/data/annual-report-pages.csv`, newest report first.

WHY, IN TJ'S WORDS: *"i think we probalby need to amke sure we capture everything that
needs to be ingested from those reports then, directly in the backlog."*

The stabilization work showed the shape of the problem. A table family was worked for
weeks and a better one sat unread in the same reports -- not because anybody decided to
skip it, but because nothing anywhere said it existed. The backlog counted ROWS in
datasets that had already been built, so a table with no extractor contributed nothing to
it and was invisible by construction. A backlog that can only see work already started is
not a backlog.

This maps the other direction: from the PAGES, to what is on them, to whether any dataset
has taken anything from that page. What comes out is the real queue.

HOW A PAGE IS JUDGED READ. Most `report_*` tables carry the `page` they came from, so a
page is `read` when some dataset holds a row citing it. That is a coarse test and it is
honest about being coarse -- one row from a page marks the page read, and a table whose
bottom half was dropped still counts. It measures whether a page has been LOOKED at, not
whether it was exhausted; `verify_report_tables.py` is what measures the second thing.

WHAT `subject` IS. A guess, from the headings the page prints, and it says so. It exists
to group the queue -- twenty pages of `special-revenue` are one job, not twenty -- and
never to assert what a figure means. Where no heading survives the scan the subject is
`unknown`, which is a statement about our scan rather than about the page.

`reversed` is a page whose OCR came out upside down: its text is mirrored and no extractor
can see a figure on it at all. Those are not a reading job, they are a re-OCR job, and
mixing the two makes the queue lie about its own size.
"""
import argparse
import collections
import csv
import glob
import io
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_tables as T  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
OUT = os.path.join(ROOT, 'sources', 'data', 'annual-report-pages.csv')

MONEY = re.compile(r'^\(?-?[$S]?-?[\d,]{1,15}[.,]\d{2}\)?$')
MIN_FIGURES = 15

# Ordered: the first that matches wins, so the specific sits above the general.
SUBJECTS = [
    ('trust-and-stabilization',
     r'stabilization|trust\s+fund|held\s+by\s+other\s+banks|bartholomew'),
    ('treasurers-cash', r"treasurer.{0,3}s\s+cash"),
    ('special-revenue', r'special\s+revenue'),
    ('receivables', r'receivable'),
    ('balance-sheet', r'combined\s+balance\s+sheet|all\s+fund\s+types'),
    ('tax-collection', r'collection\s+of\s+taxes|taxes\s*&\s*excise|tax\s+liens'),
    ('debt', r'debt\s+(repayment|schedule|limit)|outstanding\s+debt|bonds?\s+payable'),
    ('appropriations', r'appropriat|budget\s+report|expenditures?\b'),
    ('payroll', r'gross\s+wages|payroll|salar(y|ies)'),
    ('valuation', r'valuation|assessed\s+value|new\s+growth'),
    ('elections', r'election|ballot|precinct'),
    ('vital-records', r'births?\b|deaths?\b|marriages?'),
    ('officials', r'town\s+officials|appointed|elected\s+officials'),
    ('capital', r'capital\s+(project|plan|outlay)'),
    ('enrollment', r'enrollment|mcas'),
]
SUBJECTS = [(k, re.compile(v, re.I)) for k, v in SUBJECTS]

FIELDS = ['fy', 'page', 'subject', 'state', 'figures', 'figures_reversed',
          'read_by', 'heading', 'document']


def unreversed(t):
    r = t[::-1]
    for a, b in (('S', '$'), ('E', '3'), ('Z', '2'), ('B', '8'), ("'", ',')):
        r = r.replace(a, b)
    return r


def read_pages():
    """{(fy, page): 'dataset, dataset'} for every page some dataset cites."""
    out = collections.defaultdict(set)
    if not os.path.exists(DB):
        return out
    db = sqlite3.connect('file:%s?mode=ro' % DB, uri=True)
    try:
        for (t,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' "
                               "AND name LIKE 'report_%'"):
            cols = {r[1] for r in db.execute('PRAGMA table_info("%s")' % t)}
            if not {'fy', 'page'} <= cols:
                continue
            for fy, pg in db.execute('SELECT DISTINCT fy, page FROM "%s"' % t):
                try:
                    out[(int(fy), int(pg))].add(t[len('report_'):])
                except (TypeError, ValueError):
                    continue
    finally:
        db.close()
    return out


def subject_of(texts):
    joined = ' | '.join(texts)
    for name, pat in SUBJECTS:
        if pat.search(joined):
            return name
    return 'unknown'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    done = read_pages()
    rows = []
    for f in sorted(glob.glob(os.path.join(OCR, '*annual-town-report.tsv'))):
        m = re.search(r'fy-(\d{4})-', f)
        if not m:
            continue
        fy = int(m.group(1))
        doc = os.path.relpath(f, ROOT)
        by_page = collections.defaultdict(list)
        for b in T.read_boxes(f):
            by_page[b['page']].append(b)
        for page, boxes in sorted(by_page.items()):
            figs = rev = 0
            for b in boxes:
                t = (b['text'] or '').strip()
                if not t:
                    continue
                if MONEY.match(t):
                    figs += 1
                elif MONEY.match(unreversed(t)):
                    rev += 1
            if figs + rev < MIN_FIGURES:
                continue
            top = [' '.join((b['text'] or '').split())
                   for b in sorted(boxes, key=lambda b: -b['y'])[:10]]
            top = [t for t in top if len(t) > 6 and not MONEY.match(t)]
            if rev > figs:
                # Nothing on a mirrored page can be classified; its headings are as
                # mangled as its figures. Try the unreversed reading before giving up.
                top = [unreversed(t) for t in top]
            hits = done.get((fy, page), set())
            state = 'read' if hits else ('reversed' if rev > figs else 'unread')
            rows.append(dict(
                fy=fy, page=page, subject=subject_of(top), state=state,
                figures=figs, figures_reversed=rev,
                read_by=', '.join(sorted(hits)),
                heading=(top[0] if top else '')[:60], document=doc))

    rows.sort(key=lambda r: (-r['fy'], r['page']))
    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    wr.writeheader()
    wr.writerows(rows)
    text = buf.getvalue()

    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if cur != text:
            print('STALE %s -- run: python3 scripts/map_annual_report_pages.py'
                  % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('ok -- %d financial pages mapped across %d reports'
              % (len(rows), len({r['fy'] for r in rows})))
        return 0

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(text)
    st = collections.Counter(r['state'] for r in rows)
    print('wrote %s -- %d financial pages across %d reports'
          % (os.path.relpath(OUT, ROOT), len(rows), len({r['fy'] for r in rows})))
    print('  read %d, unread %d, reversed %d'
          % (st['read'], st['unread'], st['reversed']))
    print()
    print('  what is NOT yet ingested, by subject:')
    todo = collections.Counter(r['subject'] for r in rows if r['state'] != 'read')
    for s, n in todo.most_common():
        yrs = sorted({r['fy'] for r in rows
                      if r['subject'] == s and r['state'] != 'read'})
        print('    %-24s %3d pages  FY%d-FY%d' % (s, n, yrs[0], yrs[-1]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
