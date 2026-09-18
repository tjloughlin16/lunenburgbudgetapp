#!/usr/bin/env python3
"""OCR for the town's scanned minutes, newest first, so a scan can be searched and its
votes read.

    python3 scripts/ocr_scanned_minutes.py --limit 40     # the next 40, newest first
    python3 scripts/ocr_scanned_minutes.py --status
    python3 scripts/ocr_scanned_minutes.py --check        # every OCR'd text still marked, its PDF unchanged

WHAT A SCAN IS. The town posts many sets of minutes as image-only PDFs -- a scan, or a
photo printed to PDF -- and 2,000-odd of them yield no text to pypdf. They are held,
they open for a person, and to a machine they are blank: unsearchable, and invisible to
extract_official_votes.py. macOS's Vision framework reads them locally
(scripts/ocr_pdf.swift, no network, nothing charged to the plan), about half a minute a
document.

WHAT AN OCR TEXT IS. A READING, and it says so: the first line of every file this writes
is `===OCR macOS Vision===`, which extract_minutes.py honours by never overwriting the
file, and which a reader of the text meets before anything else. Rule 13: a figure OCR
read is a place to look in the PDF, not a figure to quote. The PDF stays the document.

ORDER. Newest first across every board -- TJ, 17 September 2026: "Last 2 years is most
important across everything than deeper for more." The registry
`sources/data/ocr-minutes.csv` records each file done with the sha256 of the PDF it read.
"""
import argparse
import csv
import hashlib
import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN = os.path.join(ROOT, 'sources', 'meetings')
TEXT = os.path.join(MIN, 'text')
INDEX = os.path.join(MIN, 'index.csv')
REG = os.path.join(ROOT, 'sources', 'data', 'ocr-minutes.csv')
SWIFT = os.path.join(ROOT, 'scripts', 'ocr_pdf.swift')
MARKER = '===OCR macOS Vision==='
PAGE_MARKER = re.compile(r'^===PAGE \d+===$', re.M)
FIELDS = ['path', 'date', 'board_slug', 'pdf_sha256', 'chars', 'pages', 'ocr_at']


def sha256(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def registry():
    if not os.path.exists(REG):
        return {}
    return {r['path']: r for r in csv.DictReader(io.open(REG, encoding='utf-8', newline=''))}


def candidates(kinds=('minutes',)):
    """Minutes the archive holds as PDFs whose text file holds nothing a search could
    match, newest first."""
    done = registry()
    out = []
    for r in csv.DictReader(open(INDEX, encoding='utf-8')):
        p = (r.get('path') or '').strip()
        if not p or not p.lower().endswith('.pdf') or r.get('kind') not in kinds:
            continue
        src = os.path.join(MIN, p)
        if not os.path.exists(src) or p in done:
            continue
        txt = os.path.join(TEXT, os.path.splitext(p)[0] + '.txt')
        body = open(txt, encoding='utf-8', errors='replace').read() if os.path.exists(txt) else ''
        if body.startswith(MARKER) or PAGE_MARKER.sub('', body).strip():
            continue
        out.append(dict(path=p, date=r.get('date') or '', board_slug=p.split('/')[0], src=src, txt=txt))
    out.sort(key=lambda x: x['date'], reverse=True)
    return out


def ocr_one(c):
    tmp = c['txt'] + '.ocr'
    r = subprocess.run(['swift', SWIFT, c['src'], tmp, '2'], capture_output=True, text=True, timeout=1800)
    if r.returncode != 0 or not os.path.exists(tmp):
        return None
    body = open(tmp, encoding='utf-8', errors='replace').read()
    os.remove(tmp)
    os.makedirs(os.path.dirname(c['txt']), exist_ok=True)
    with open(c['txt'], 'w', encoding='utf-8') as fh:
        fh.write(MARKER + '\n' + body)
    return dict(path=c['path'], date=c['date'], board_slug=c['board_slug'], pdf_sha256=sha256(c['src']),
                chars=len(PAGE_MARKER.sub('', body).strip()), pages=len(PAGE_MARKER.findall(body)),
                ocr_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))


def append(rows):
    new = not os.path.exists(REG)
    with io.open(REG, 'a', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator='\n')
        if new:
            w.writeheader()
        w.writerows(rows)


def check():
    bad, n = [], 0
    for p, r in registry().items():
        n += 1
        txt = os.path.join(TEXT, os.path.splitext(p)[0] + '.txt')
        if not os.path.exists(txt) or not open(txt, encoding='utf-8', errors='replace').read().startswith(MARKER):
            bad.append('%s: OCR text missing or unmarked' % p)
        src = os.path.join(MIN, p)
        if os.path.exists(src) and sha256(src) != r['pdf_sha256']:
            bad.append('%s: the PDF changed since it was read' % p)
    if bad:
        sys.exit('ocr-minutes: %d problem(s)\n  ' % len(bad) + '\n  '.join(bad))
    print('ocr-minutes: %d scanned minutes read, every text marked and every PDF unchanged' % n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=40)
    ap.add_argument('--board')
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.check:
        return check()
    cs = candidates()
    if a.board:
        cs = [c for c in cs if c['board_slug'] == a.board]
    if a.status:
        import collections
        by = collections.Counter(c['board_slug'] for c in cs)
        print('%d scanned minutes still to read (%d done); newest first:' % (len(cs), len(registry())))
        for k, v in by.most_common():
            print('  %-50s %4d' % (k, v))
        return
    done = []
    for c in cs[:a.limit]:
        row = ocr_one(c)
        print('  %s %s  %s' % (c['board_slug'], c['date'], ('%d chars, %d pages' % (row['chars'], row['pages'])) if row else 'FAILED'))
        if row:
            done.append(row)
    if done:
        append(done)
    print('%d read; %d still to read' % (len(done), len(cs) - len(done)))


if __name__ == '__main__':
    main()
