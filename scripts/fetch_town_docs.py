#!/usr/bin/env python3
"""Mirror the town's budget and finance documents, and make them readable.

The town runs CivicPlus, which serves documents from /DocumentCenter/View/<id>/<slug>.
The ids are sequential, but enumerating them would hammer a small town's web host for
thousands of files that have nothing to do with the budget. So this walks the pages that
actually matter -- the budget hub, town meetings and finances, the finance-adjacent
department pages -- and takes the documents they link to.

Same contract as the district crawler: download once, extract text, record where each file
came from so a reader can be sent to our copy and still see the town's original.

    python3 scripts/fetch_town_docs.py [--seeds-only] [--limit N]

Idempotent. Re-run it when the town posts something new.
"""
import argparse
import csv
import hashlib
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://www.lunenburgma.gov'
OUT = os.path.join(ROOT, 'sources', 'town-site')
DOCS = os.path.join(OUT, 'docs')
TEXT = os.path.join(OUT, 'text')
MANIFEST = os.path.join(OUT, 'index.csv')
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                    'AppleWebKit/537.36 Chrome/120 Safari/537.36'}

# Where the town keeps things that bear on a budget. Walked one level deep from each.
SEEDS = [
    '/835/2026-Annual-Town-Meeting-FY27-Budget-Hub',
    '/294/Town-Meetings-Town-Finances',
    '/163/Finance-Committee',
    '/171/Town-Accountant',
    '/175/Town-Manager',
    '/162/Board-of-Assessors',
    '/168/Treasurer-Collector',
    '/DocumentCenter',
]
# Budget words. A town site holds thousands of documents and most are dog licenses.
WANTED = re.compile(
    r'budget|financ|audit|appropriat|warrant|town.?meeting|capital|levy|tax|assess|'
    r'free.?cash|stabiliz|revenue|expenditure|override|omnibus|school|reserve|'
    r'classification|debt|acfr|balance.?sheet|forecast|five.?year|fy\d\d', re.I)


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read(), r.headers.get('Content-Type', '')
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def slug(s):
    s = re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
    return re.sub(r'-+', '-', s)[:80] or 'untitled'


def discover():
    """Every DocumentCenter item linked from a seed page, or from one page below it."""
    seen_pages, found = set(), {}
    queue = [(BASE + s, 0) for s in SEEDS]
    while queue:
        url, depth = queue.pop(0)
        if url in seen_pages or depth > 1:
            continue
        seen_pages.add(url)
        try:
            body, ctype = get(url)
        except Exception:
            continue
        if 'html' not in ctype:
            continue
        html = body.decode('utf8', 'ignore')
        for m in re.finditer(r'href="([^"]+)"[^>]*>(.*?)</a>', html, re.S | re.I):
            href, label = m.group(1), re.sub(r'<[^>]+>', '', m.group(2))
            label = re.sub(r'\s+', ' ', label).strip()
            full = urllib.parse.urljoin(url, href)
            if 'lunenburgma.gov' not in full:
                continue
            doc = re.search(r'/DocumentCenter/View/(\d+)(?:/([^/?#]+))?', full)
            if doc:
                did = doc.group(1)
                name = label or (doc.group(2) or '').replace('-', ' ')
                if did not in found and WANTED.search(name + ' ' + full):
                    found[did] = dict(id=did, label=name or f'document {did}',
                                      url=f'{BASE}/DocumentCenter/View/{did}')
            elif depth == 0 and re.search(r'/\d+/[A-Za-z]', full) and '#' not in full:
                queue.append((full.split('?')[0], depth + 1))
        time.sleep(0.3)
    return sorted(found.values(), key=lambda d: int(d['id']))


def sniff(body):
    if body[:4] == b'%PDF':
        return '.pdf'
    if body[:4] == b'PK\x03\x04':
        import io
        try:
            names = zipfile.ZipFile(io.BytesIO(body)).namelist()
        except Exception:
            return '.zip'
        for pre, ext in (('xl/', '.xlsx'), ('ppt/', '.pptx'), ('word/', '.docx')):
            if any(n.startswith(pre) for n in names):
                return ext
        return '.zip'
    if body[:5].lower() == b'<!doc' or b'<html' in body[:400].lower():
        return '.html'
    return '.bin'


def extract(path, out_txt):
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == '.pdf':
            import pypdf
            t = '\n'.join(f'===PAGE {i+1}===\n' + (p.extract_text() or '')
                          for i, p in enumerate(pypdf.PdfReader(path).pages))
            if len(re.sub(r'===PAGE \d+===|\s', '', t)) < 200:
                r = subprocess.run(['swift', os.path.join(ROOT, 'scripts', 'ocr_pdf.swift'),
                                    path, out_txt], capture_output=True, text=True)
                return 'ocr' if r.returncode == 0 else 'ocr failed'
            open(out_txt, 'w').write(t)
            return 'pdf text layer'
        if ext == '.xlsx':
            import openpyxl
            wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
            with open(out_txt, 'w') as fh:
                for ws in wb.worksheets:
                    fh.write(f'===SHEET {ws.title}===\n')
                    w = csv.writer(fh)
                    for row in ws.iter_rows(values_only=True):
                        if any(c is not None for c in row):
                            w.writerow(['' if c is None else c for c in row])
            return 'spreadsheet'
        if ext in ('.docx', '.pptx'):
            z = zipfile.ZipFile(path)
            if ext == '.pptx':
                parts = sorted((n for n in z.namelist()
                                if re.match(r'ppt/slides/slide\d+\.xml$', n)),
                               key=lambda s: int(re.findall(r'\d+', s)[0]))
                txt = '\n\n'.join('\n'.join(re.findall(r'<a:t>(.*?)</a:t>',
                                  z.read(n).decode('utf8', 'ignore'))) for n in parts)
            else:
                x = z.read('word/document.xml').decode('utf8', 'ignore')
                txt = re.sub(r'<[^>]+>', '', re.sub(r'</w:p>', '\n', x))
            open(out_txt, 'w').write(txt)
            return 'slides' if ext == '.pptx' else 'document'
    except Exception as e:
        return f'extract failed: {type(e).__name__}'
    return 'no extractor'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds-only', action='store_true')
    ap.add_argument('--limit', type=int)
    a = ap.parse_args()
    os.makedirs(DOCS, exist_ok=True)
    os.makedirs(TEXT, exist_ok=True)

    items = discover()
    print(f'{len(items)} budget-relevant documents linked from the town’s finance pages')
    if a.seeds_only:
        for i in items:
            print(f'  {i["id"]:>5}  {i["label"][:74]}')
        return
    if a.limit:
        items = items[:a.limit]

    rows = []
    for n, it in enumerate(items, 1):
        base = f'{it["id"]}-{slug(it["label"])}'
        have = [f for f in os.listdir(DOCS) if os.path.splitext(f)[0] == base]
        try:
            if have:
                path = os.path.join(DOCS, have[0])
                body = open(path, 'rb').read()
                note = 'had it'
            else:
                body, _ = get(it['url'])
                ext = sniff(body)
                if ext in ('.html', '.bin'):
                    print(f'  [{n:>3}] skipped (not a document)  {it["label"][:48]}')
                    continue
                path = os.path.join(DOCS, base + ext)
                open(path, 'wb').write(body)
                note = 'downloaded'
                time.sleep(0.4)
        except Exception as e:
            print(f'  [{n:>3}] FAILED {type(e).__name__}  {it["label"][:48]}')
            continue
        txt = os.path.join(TEXT, base + '.txt')
        how = 'had it' if os.path.exists(txt) and os.path.getsize(txt) > 0 \
            else extract(path, txt)
        rows.append(dict(label=it['label'], upstream=it['url'],
                         local=os.path.relpath(path, ROOT),
                         text=os.path.relpath(txt, ROOT) if os.path.exists(txt) else '',
                         bytes=len(body), sha256=hashlib.sha256(body).hexdigest(), read=how))
        print(f'  [{n:>3}] {note:<11}{os.path.splitext(path)[1]:<6}{len(body)/1000:>7.0f}KB '
              f'{how:<16}{it["label"][:42]}')

    with open(MANIFEST, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['label', 'upstream', 'local', 'text',
                                           'bytes', 'sha256', 'read'])
        w.writeheader()
        w.writerows(rows)
    print(f'\n{len(rows)} retrieved · manifest {os.path.relpath(MANIFEST, ROOT)}')


if __name__ == '__main__':
    main()
