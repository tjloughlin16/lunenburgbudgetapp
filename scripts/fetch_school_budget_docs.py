#!/usr/bin/env python3
"""Mirror every document on the district's budget page, and make each one readable.

The page is a wall of Google Drive links going back to FY18 — roughly ninety documents,
none of them hosted by the district itself. Drive links rot, get re-shared, or quietly
change permissions, and analyzing from them means an HTTP call every time somebody asks a
question. So this pulls the lot down once.

Two things it does beyond downloading:

  * records where each file came from, so a reader can be sent to our copy and still see
    the district's original URL
  * extracts text from every one of them. Scans with no text layer go through
    scripts/ocr_pdf.swift, spreadsheets are flattened to text, and slide decks and Word
    files are unzipped for their XML. A document nobody can grep is a document nobody
    will read.

    python3 scripts/fetch_school_budget_docs.py [--limit N] [--list]

Idempotent: a file already on disk with a non-zero size is skipped, so it is safe to
re-run when the district posts something new.
"""
import argparse
import csv
import hashlib
import os
import re
import subprocess
import sys
import time
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = ('https://www.lunenburgschools.net/department-directory/'
        'superintendent-of-schools/school-budget-information')
OUT = os.path.join(ROOT, 'sources', 'district-budget')
DOCS = os.path.join(OUT, 'docs')
TEXT = os.path.join(OUT, 'text')
MANIFEST = os.path.join(OUT, 'index.csv')
# Who this is, in a form somebody can look up.
#
# A crawler that will not say what it is gives an administrator seeing a burst of requests
# nothing to do but block it. Naming the site means the request is attributable, the
# +URL leads to a page explaining what the project is, and anybody who wants it to stop
# has an obvious way to ask.
#
# It is also the honest form. This is not a browser and should not claim to be one; the
# "Mozilla/5.0 (compatible; ...)" prefix is the convention every well-behaved crawler
# uses, and the rest of it is true.
UA = {'User-Agent': ('Mozilla/5.0 (compatible; LunenburgBudgetProject/1.0; +https://lunenburgbudgetproject.org)')}

EXT = {b'%PDF': '.pdf', b'PK\x03\x04': '.zip'}   # zip refined later by its own contents


def get(url, tries=3, data=None):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA, data=data)
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read(), r.geturl()
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))
    raise RuntimeError(url)


def slug(s):
    s = re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
    return re.sub(r'-+', '-', s)[:70] or 'untitled'


def links():
    """Every Drive/Docs link on the page, with the text that labels it."""
    html = get(PAGE)[0].decode('utf8', 'ignore')
    out, seen = [], set()
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S | re.I):
        href, label = m.group(1), re.sub(r'<[^>]+>', '', m.group(2))
        label = re.sub(r'\s+', ' ', label).strip()
        fid = re.search(r'/d/([A-Za-z0-9_-]{20,})|[?&]id=([A-Za-z0-9_-]{20,})', href)
        if not fid or not label:
            continue
        gid = fid.group(1) or fid.group(2)
        if gid in seen:
            continue
        seen.add(gid)
        kind = ('sheet' if '/spreadsheets/' in href else
                'doc' if '/document/' in href else 'file')
        out.append(dict(id=gid, label=label, url=href, kind=kind))
    return out


def download(item):
    """Drive's direct-download endpoint, with the virus-scan interstitial handled."""
    gid = item['id']
    if item['kind'] == 'sheet':
        url = f'https://docs.google.com/spreadsheets/d/{gid}/export?format=xlsx'
    elif item['kind'] == 'doc':
        url = f'https://docs.google.com/document/d/{gid}/export?format=docx'
    else:
        url = f'https://drive.google.com/uc?export=download&id={gid}'
    body, final = get(url)
    if body[:15].lower().startswith(b'<!doctype html') or b'<html' in body[:200].lower():
        # Large files get an interstitial carrying a confirm token.
        tok = re.search(rb'confirm=([0-9A-Za-z_-]+)', body)
        uuid = re.search(rb'name="uuid" value="([^"]+)"', body)
        if tok or uuid:
            u = f'https://drive.usercontent.google.com/download?id={gid}&export=download&confirm=t'
            if uuid:
                u += '&uuid=' + uuid.group(1).decode()
            body, final = get(u)
    return body


def sniff(body):
    if body[:4] == b'%PDF':
        return '.pdf'
    if body[:4] == b'PK\x03\x04':
        try:
            names = zipfile.ZipFile(__import__('io').BytesIO(body)).namelist()
        except Exception:
            return '.zip'
        if any(n.startswith('xl/') for n in names):
            return '.xlsx'
        if any(n.startswith('ppt/') for n in names):
            return '.pptx'
        if any(n.startswith('word/') for n in names):
            return '.docx'
        return '.zip'
    return '.bin'


def extract(path, out_txt):
    """Text from anything. Returns a short note about how it was read."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == '.pdf':
            import pypdf
            t = '\n'.join(f'===PAGE {i+1}===\n' + (p.extract_text() or '')
                          for i, p in enumerate(pypdf.PdfReader(path).pages))
            if len(re.sub(r'===PAGE \d+===|\s', '', t)) < 200:
                # No text layer. macOS Vision reads the scan; nothing to install.
                r = subprocess.run(['swift', os.path.join(ROOT, 'scripts', 'ocr_pdf.swift'),
                                    path, out_txt], capture_output=True, text=True)
                return 'ocr' if r.returncode == 0 else f'ocr failed: {r.returncode}'
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
        if ext in ('.pptx', '.docx'):
            z = zipfile.ZipFile(path)
            if ext == '.pptx':
                parts = sorted((n for n in z.namelist()
                                if re.match(r'ppt/slides/slide\d+\.xml$', n)),
                               key=lambda s: int(re.findall(r'\d+', s)[0]))
                txt = '\n\n'.join(f'===SLIDE {i+1}===\n' +
                                  '\n'.join(re.findall(r'<a:t>(.*?)</a:t>',
                                                       z.read(n).decode('utf8', 'ignore')))
                                  for i, n in enumerate(parts))
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
    ap.add_argument('--limit', type=int)
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()

    os.makedirs(DOCS, exist_ok=True)
    os.makedirs(TEXT, exist_ok=True)
    items = links()
    print(f'{len(items)} documents linked from the district budget page')
    if a.list:
        for i in items:
            print(f"  {i['kind']:<6} {i['label'][:70]}")
        return
    if a.limit:
        items = items[:a.limit]

    # What the previous run recorded about HOW each document was read -- a PDF text layer,
    # OCR, unzipped XML. Re-running skips extraction for anything already extracted, and
    # used to write the string "already had it" into the column that was supposed to say
    # "ocr", destroying the only record of which documents have no text layer at all. A
    # crawler advertised as idempotent must not lose information by being re-run, so the
    # earlier answer is carried forward whenever nothing was re-extracted.
    was_read = {}
    if os.path.exists(MANIFEST):
        with open(MANIFEST, newline='') as fh:
            was_read = {r['label']: r['read'] for r in csv.DictReader(fh)
                        if r.get('read') and r['read'] != 'already had it'}

    rows = []
    for n, it in enumerate(items, 1):
        base = slug(it['label'])
        existing = [f for f in os.listdir(DOCS) if os.path.splitext(f)[0] == base]
        try:
            if existing:
                path = os.path.join(DOCS, existing[0])
                body = open(path, 'rb').read()
                note = 'already had it'
            else:
                body = download(it)
                path = os.path.join(DOCS, base + sniff(body))
                open(path, 'wb').write(body)
                note = 'downloaded'
                time.sleep(0.6)
        except Exception as e:
            print(f'  [{n:>2}] FAILED  {it["label"][:56]}  {type(e).__name__}')
            rows.append(dict(label=it['label'], upstream=it['url'], local='', text='',
                             bytes=0, sha256='', read='download failed'))
            continue

        txt = os.path.join(TEXT, base + '.txt')
        if os.path.exists(txt) and os.path.getsize(txt) > 0:
            how = was_read.get(it['label'], 'already had it')
        else:
            how = extract(path, txt)
        rows.append(dict(
            label=it['label'], upstream=it['url'],
            local=os.path.relpath(path, ROOT), text=os.path.relpath(txt, ROOT)
            if os.path.exists(txt) else '',
            bytes=len(body), sha256=hashlib.sha256(body).hexdigest(), read=how))
        print(f'  [{n:>2}] {note:<14} {os.path.splitext(path)[1]:<6} {len(body)/1000:>7.0f}KB '
              f'{how:<16} {it["label"][:44]}')

    with open(MANIFEST, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['label', 'upstream', 'local', 'text',
                                           'bytes', 'sha256', 'read'])
        w.writeheader()
        w.writerows(rows)
    ok = sum(1 for r in rows if r['local'])
    print(f'\n{ok}/{len(rows)} retrieved · manifest {os.path.relpath(MANIFEST, ROOT)}')


if __name__ == '__main__':
    main()
