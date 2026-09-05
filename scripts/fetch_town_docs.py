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
import sys
import time
import urllib.parse
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://www.lunenburgma.gov'
# The town's document store is mirrored into THREE folders, not one, and which folder a
# document belongs in is decided by scripts/town_document_home.py -- one copy of the rule,
# imported here and by anything that repairs the split.
#
# This used to write everything to town-budget/ and test "have I got this already?" against
# that one folder. So every document that had been filed as supplementary or as an annual
# report looked missing, was downloaded again, and landed back in town-budget/ -- undoing
# the split on every run, four times, manifest as well as files.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from town_document_home import FOLDERS, home  # noqa: E402

def folder(name):
    return os.path.join(ROOT, 'sources', name)

def docs_dir(name):
    return os.path.join(folder(name), 'docs')

def text_dir(name):
    return os.path.join(folder(name), 'text')

def manifest_of(name):
    return os.path.join(folder(name), 'index.csv')
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

# Where the town keeps things that bear on a budget. Walked one level deep from each.
SEEDS = [
    '/835/2026-Annual-Town-Meeting-FY27-Budget-Hub',
    '/294/Town-Meetings-Town-Finances',
    '/163/Finance-Committee',
    '/171/Town-Accountant',
    '/175/Town-Manager',
    '/162/Board-of-Assessors',
    '/168/Treasurer-Collector',
    '/287/Town-Manager-Reports',
    # The annual town reports, FY2011-FY2025. Sixteen of them, and the archive held none
    # until 4 September 2026 -- they were never discovered because no seed page linked
    # them. They carry the Town Accountant's year-end statements, which is the only place
    # revenue by source and appropriation by department are published side by side.
    '/838/Annual-Town-Reports',
    '/DocumentCenter',
    '/Archive.aspx',
]
# Budget words. A town site holds thousands of documents and most are dog licenses.
WANTED = re.compile(
    r'budget|financ|audit|appropriat|warrant|town.?meeting|capital|levy|tax|assess|'
    r'free.?cash|stabiliz|revenue|expenditure|override|omnibus|school|reserve|'
    r'classification|debt|acfr|balance.?sheet|forecast|five.?year|fy\d\d|'
    # `fy\d\d` does not match `FY 2025` or `FY-2025`, which is how the annual town
    # reports are titled -- so all sixteen were filtered out by a pattern meant to
    # catch them. The archive held none of them until this was noticed.
    r'annual.?town.?report|fy.\d{4}', re.I)


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


def dedupe_key(label):
    """A key that matches the SAME document titled two different ways.

    The town publishes the annual town reports in both stores and does not title them
    alike: DocumentCenter says `FY 2025 Annual Town Report`, the ArchiveCenter says
    `FY25 Annual Town Report (PDF)`. Slugging alone leaves those as two documents, and the
    archive ends up with 487MB of duplicate PDFs under two ids.

    So the year is normalised to four digits and the format suffix dropped, which is all
    that separates them.
    """
    k = label.lower()
    k = re.sub(r'\((?:pdf|xlsx?|docx?|pptx?)\)', ' ', k)
    k = re.sub(r'\bfy\s*(\d{4})\b', r'fy\1', k)
    k = re.sub(r'\bfy\s*(\d{2})\b(?!\d)', lambda m: 'fy20' + m.group(1), k)
    return re.sub(r'[^a-z0-9]', '', k)


def slug(s):
    s = re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
    return re.sub(r'-+', '-', s)[:80] or 'untitled'


def discover_archive():
    """The town's OTHER document store, which link-walking cannot reach.

    `/Archive.aspx` renders its categories and items in javascript, so the HTML a fetcher
    receives contains no archive links at all -- one stylesheet reference and nothing else.
    That is why this project walked `/DocumentCenter/` for a year and never saw a second
    store sitting beside it holding fifteen years of annual town reports and a category of
    town meeting and budget documents for every year from FY12 to FY25.

    The ids are in the markup even though the links are not:

        <label for="amidDDN52">Annual Town Reports:</label>     -> AMID 52, the category
        <a href="Archive.aspx?ADID=201"><span>FY24-FY33: ...</span></a>  -> ADID 201, an item

    So: read the categories off the index, ask each category page for its items, and take
    the file from `/ArchiveCenter/ViewFile/Item/<ADID>`, which is the address a resident
    would use.
    """
    out = {}
    try:
        body, _ = get(BASE + '/Archive.aspx')
    except Exception as e:
        print(f'  archive index unreachable: {e}')
        return out
    index = body.decode('utf8', 'ignore')
    cats = re.findall(r'<label for="amidDDN(\d+)">([^<]+)</label>', index)
    print(f'  {len(cats)} archive categories')
    for amid, cat in cats:
        cat = cat.strip().rstrip(':')
        try:
            page, _ = get(f'{BASE}/Archive.aspx?AMID={amid}')
        except Exception:
            continue
        html = page.decode('utf8', 'ignore')
        items = re.findall(
            r'<a href="Archive\.aspx\?ADID=(\d+)"[^>]*>\s*<span>([^<]*)</span>', html, re.S)
        for adid, title in items:
            title = re.sub(r'\s+', ' ', title).strip()
            aid = 'a' + adid
            if aid in out:
                continue
            out[aid] = dict(id=aid, label=title or f'{cat} item {adid}',
                            url=f'{BASE}/ArchiveCenter/ViewFile/Item/{adid}',
                            category=cat)
        print(f'    AMID {amid:>3}  {len(items):>3} items  {cat}')
        time.sleep(0.3)
    return out


def discover():
    """Every DocumentCenter or ArchiveCenter item linked from a seed, or one page below.

    The town runs TWO document stores and this only ever walked one of them.
    `/DocumentCenter/View/<id>` holds what is current; `/ArchiveCenter/ViewFile/Item/<id>`
    holds what has been retired -- twelve categories of it, including the town meeting and
    budget documents for FY12 through FY25 and the town meeting booklets back to 2015.
    None of it was in this archive, because no seed linked a DocumentCenter URL to any of
    it and the pattern below did not match the other kind.
    """
    seen_pages, found = set(), {}
    rejected, seen_links = {}, 0
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
                seen_links += 1
                if did not in found and WANTED.search(name + ' ' + full):
                    found[did] = dict(id=did, label=name or f'document {did}',
                                      url=f'{BASE}/DocumentCenter/View/{did}')
                elif did not in found:
                    rejected.setdefault(did, name or full)
            if doc:
                continue
            if depth == 0 and re.search(r'/\d+/[A-Za-z]', full) and '#' not in full:
                queue.append((full.split('?')[0], depth + 1))
        time.sleep(0.3)
    # Archive items are keyed `a<id>` so they cannot collide with a DocumentCenter id of
    # the same number, which means the key is not always an integer.
    def order(d):
        i = d['id']
        return (i[0] == 'a', int(i.lstrip('a')))

    # PRINT THE DENOMINATOR. This is the whole reason sixteen annual town reports sat
    # unnoticed on the town's website for as long as this project has existed: the filter
    # rejected them, the fetcher printed only what it kept, and a list of what you have
    # cannot tell you what you are missing. `search_minutes.py` prints coverage on every
    # run for exactly this reason and this did not.
    arch = discover_archive()
    for k, v in arch.items():
        if k not in found and WANTED.search(v['label'] + ' ' + v.get('category', '')):
            found[k] = v
        elif k not in found:
            rejected.setdefault(k, f"{v['category']}: {v['label']}")
    seen_links += len(arch)

    kept = len(found)
    print(f'\n{seen_links:,} document links seen · {kept} kept · '
          f'{len(rejected):,} rejected by the WANTED filter')
    if rejected:
        show = sorted(rejected.values())[:12]
        print('  a sample of what was rejected — read it, that is the point:')
        for r in show:
            print(f'    {r[:96]}')
        if len(rejected) > len(show):
            print(f'    ... and {len(rejected) - len(show):,} more')
    return sorted(found.values(), key=order)


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
    for _f in FOLDERS:
        os.makedirs(docs_dir(_f), exist_ok=True)
        os.makedirs(text_dir(_f), exist_ok=True)

    items = discover()
    print(f'{len(items)} budget-relevant documents linked from the town’s finance pages')

    # THE SAME DOCUMENT LIVES AT TWO ADDRESSES -- see dedupe_key(). A document with two
    # addresses is one document, and rule 12 wants both kept: when one link dies the other
    # may not have. So the duplicate is recorded as a second `upstream` against the copy we
    # keep, never fetched again and never stored twice.
    by_key, aliases = {}, {}
    for it in items:
        k = dedupe_key(it['label'])
        if k in by_key:
            aliases.setdefault(by_key[k], []).append(it['url'])
        else:
            by_key[k] = it['id']
    dupes = sum(len(v) for v in aliases.values())
    if dupes:
        print(f'{dupes} item(s) are the same document at a second address — '
              f'fetched once, both addresses recorded')
    items = [it for it in items if by_key.get(dedupe_key(it['label'])) == it['id']]

    if a.seeds_only:
        for i in items:
            print(f'  {i["id"]:>5}  {i["label"][:74]}')
        return
    if a.limit:
        items = items[:a.limit]

    rows = []
    for n, it in enumerate(items, 1):
        base = f'{it["id"]}-{slug(it["label"])}'
        want = home(it['label'])
        # Look in ALL THREE mirrors before deciding we do not have it. A document already
        # filed as supplementary is not missing just because it is not in town-budget/.
        have = None
        for f in FOLDERS:
            d = docs_dir(f)
            if not os.path.isdir(d):
                continue
            hit = [x for x in os.listdir(d) if os.path.splitext(x)[0] == base]
            if hit:
                have = (f, os.path.join(d, hit[0]))
                break
        try:
            if have:
                found_in, path = have
                body = open(path, 'rb').read()
                note = 'had it' if found_in == want else f'had it ({found_in})'
            else:
                body, _ = get(it['url'])
                ext = sniff(body)
                if ext in ('.html', '.bin'):
                    print(f'  [{n:>3}] skipped (not a document)  {it["label"][:48]}')
                    continue
                os.makedirs(docs_dir(want), exist_ok=True)
                path = os.path.join(docs_dir(want), base + ext)
                open(path, 'wb').write(body)
                note = 'downloaded'
                time.sleep(0.4)
        except Exception as e:
            print(f'  [{n:>3}] FAILED {type(e).__name__}  {it["label"][:48]}')
            continue
        # The text sits beside whichever copy we actually have, not beside where a new
        # one would have gone.
        here = have[0] if have else want
        os.makedirs(text_dir(here), exist_ok=True)
        txt = os.path.join(text_dir(here), base + '.txt')
        how = 'had it' if os.path.exists(txt) and os.path.getsize(txt) > 0 \
            else extract(path, txt)
        also = aliases.get(it['id'], [])
        rows.append(dict(_home=here, label=it['label'],
                         upstream=' '.join([it['url']] + also),
                         local=os.path.relpath(path, ROOT),
                         text=os.path.relpath(txt, ROOT) if os.path.exists(txt) else '',
                         bytes=len(body), sha256=hashlib.sha256(body).hexdigest(), read=how))
        print(f'  [{n:>3}] {note:<11}{os.path.splitext(path)[1]:<6}{len(body)/1000:>7.0f}KB '
              f'{how:<16}{it["label"][:42]}')

    # A PARTIAL RUN MUST NOT WRITE A MANIFEST. Each write replaces the whole file, so
    # `--limit 40` would leave three index.csv files describing forty documents and
    # silently drop the rest -- and every one of those rows is a document's only recorded
    # address. Discovered by doing exactly that.
    if a.limit:
        print(f'\n{len(rows)} retrieved. Manifests NOT written: --limit makes this a '
              f'partial run,\nand a manifest write replaces the whole file.')
        return

    # Each mirror's manifest gets ONLY its own rows. Writing them all to town-budget's
    # index.csv is how the split came undone in the manifest as well as on disk.
    fields = ['label', 'upstream', 'local', 'text', 'bytes', 'sha256', 'read']
    for name in FOLDERS:
        mine = [r for r in rows if r['_home'] == name]
        if not mine and not os.path.exists(manifest_of(name)):
            continue
        os.makedirs(folder(name), exist_ok=True)
        with open(manifest_of(name), 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction='ignore')
            w.writeheader()
            w.writerows(mine)
        print(f'  {len(mine):>4} rows · {os.path.relpath(manifest_of(name), ROOT)}')
    print(f'\n{len(rows)} retrieved across {len(FOLDERS)} mirrors')
    if aliases:
        print(f'{len(aliases)} of them carry a second published address in `upstream`')


if __name__ == '__main__':
    main()
