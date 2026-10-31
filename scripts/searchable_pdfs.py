#!/usr/bin/env python3
"""A SEARCHABLE COPY OF EVERY PDF WHOSE PAGES ARE PICTURES: the scan as published, our words under it.

    python3 scripts/searchable_pdfs.py --status               # the register, counted
    python3 scripts/searchable_pdfs.py --new                  # the refresh step: survey, read, build, push
    python3 scripts/searchable_pdfs.py --new --no-textract    # the same, spending nothing
    python3 scripts/searchable_pdfs.py --key KEY [--force]    # one document
    python3 scripts/searchable_pdfs.py --quote                # what reading every waiting page would cost
    python3 scripts/searchable_pdfs.py --check                # every built copy still rebuilds byte for byte

TJ, 31 October 2026: *"id like this to become the standard process for all pdfs that have major
missing text portions ... it ingests and provides the raw, but aws textextracts it and creates the
searchable pdf too."* And where the site links a PDF: *"show the searchable PDF (with the 'raw pdf'
link also available)"*.

WHAT A SEARCHABLE COPY IS. A SANDWICH PDF: every object of the original kept byte for byte, the
scan included, and under each picture page a layer of invisible text (render mode 3) placed where
Textract found each word. Search, select and copy work; what a reader sees is the town's page.

WHICH PDFs. Those `pdf_kind` says have a page with no readable text -- `image`, `text, unreadable`
or `outlines` (rule 13d: never a character count). Only those pages get a layer; a page with a real
text layer is left alone, or a search would find every word on it twice.

THE ORIGINAL IS NEVER TOUCHED, AND THE COPY IS NOT THE ARCHIVE. The town's file stays in the
locked bucket at its own key, with its own sha256 (rule 12). The copy is OURS -- derived from that
file and from our Textract reads, rebuilt when either improves -- so it goes in the UNLOCKED
`lunenburg-derived` bucket beside our extracted text, at `searchable/<archive key>`, and is served
at `/docs/searchable/<archive key>`. Its metadata says what it is and names the original's sha256.

THE STEPS, per document, and each one is resumable:
  1. SURVEY   pdf_kind.classify. A PDF with nothing to add is recorded `not needed` and never
              opened again unless its sha256 changes.
  2. READ     the needed pages with no Textract read yet, through textract_pages.py -- the TEXT
              feature, a tenth of the tables price, and the meter, the caps and the latch
              (textract_spend.py) exactly as every other read. Any read already cached counts,
              tables or text: both carry every word's position.
  3. BUILD    only when EVERY needed page has a read. A half-searchable copy is a search that
              finds nothing on the unread pages and reads as "the town never said it" (rule 13c),
              so a document with unread pages waits as `waiting` and says how many.
  4. VERIFY   words sampled from the Textract reads are looked for in the built file, at their own
              position, by a different reader (pdfium) than the one that wrote it (pypdf).
  5. PUSH     to the derived bucket, and read back by listing: the etag must equal the file's MD5.
              Only then does the register say `built` -- so a key the register names is a key the
              bucket holds, and the site links nothing that would 404.

THE REGISTER is sources/data/searchable-pdfs.csv, one row per PDF in the archive manifest. The site
reads the `built` rows (fy28/public/data/searchable-pdfs.json, written here) to decide which links
get a searchable copy and a raw link beside it.
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import archive_storage as AS                                          # noqa: E402

ROOT = HERE.parent
REGISTER = ROOT / 'sources/data/searchable-pdfs.csv'
SITE_LIST = ROOT / 'fy28/public/data/searchable-pdfs.json'
TAKEDOWNS = ROOT / 'sources/data/takedowns.csv'
OUT = ROOT / 'build/searchable'
DERIVED_BUCKET = 'lunenburg-derived'
PREFIX = 'searchable/'
FIELDS = ['key', 'sha256', 'verdict', 'pages', 'need', 'read', 'state', 'words', 'bytes', 'md5', 'builder']
# BUMPED WHEN THE BUILD CHANGES WHAT IT WRITES, so --new rebuilds every copy made the old way.
BUILDER = 'sandwich-1'
FONT = '/FOCR'
HEADROOM_USD = 0.50                   # left under the monthly cap for anything else that reads
COURIER_ADVANCE = 0.6                 # every Courier glyph is 600/1000 em wide: no metrics table needed


# ------------------------------------------------------------------ the register

def read_register():
    if not REGISTER.exists():
        return {}
    with open(REGISTER, newline='') as f:
        return {r['key']: r for r in csv.DictReader(f)}


def write_register(rows):
    tmp = REGISTER.with_suffix('.tmp')
    with open(tmp, 'w', newline='') as f:
        w = csv.DictWriter(f, FIELDS, lineterminator='\n')
        w.writeheader()
        for k in sorted(rows):
            w.writerow({c: rows[k].get(c, '') for c in FIELDS})
    os.replace(tmp, REGISTER)
    built = sorted(k for k, r in rows.items() if r['state'] == 'built')
    SITE_LIST.parent.mkdir(parents=True, exist_ok=True)
    tmp = SITE_LIST.with_suffix('.tmp')
    tmp.write_text(json.dumps({'prefix': '/docs/' + PREFIX, 'keys': built}, separators=(',', ':')) + '\n')
    os.replace(tmp, SITE_LIST)


def ranges(pages):
    out, start, prev = [], None, None
    for p in sorted(pages):
        if start is None:
            start = prev = p
        elif p == prev + 1:
            prev = p
        else:
            out.append(str(start) if start == prev else f'{start}-{prev}')
            start = prev = p
    if start is not None:
        out.append(str(start) if start == prev else f'{start}-{prev}')
    return ','.join(out)


def unranges(s):
    pages = []
    for part in filter(None, (s or '').split(',')):
        a, _, b = part.partition('-')
        pages.extend(range(int(a), int(b or a) + 1))
    return pages


def taken_down():
    if not TAKEDOWNS.exists():
        return set()
    with open(TAKEDOWNS, newline='') as f:
        return {r.get('key', '') for r in csv.DictReader(f)}


def manifest_pdfs():
    return {k: r['sha256'] for k, r in AS.read_manifest().items() if k.lower().endswith('.pdf')}


# ------------------------------------------------------------------ 1. survey

def survey(key, sha):
    import pdf_kind
    k = pdf_kind.classify(str(AS.local_path(key)))
    need = [p['page'] for p in k['pages'] if p['kind'] in pdf_kind.OCR_KINDS]
    return {'key': key, 'sha256': sha, 'verdict': k['verdict'], 'pages': str(len(k['pages'])),
            'need': ranges(need), 'read': '', 'state': 'waiting' if need else 'not needed',
            'words': '', 'bytes': '', 'md5': ''}


# ------------------------------------------------------------------ 2. read

def cache_dir(sha):
    import textract_spend as M
    return M.CACHE / sha


def cached_read(sha, page):
    """The Textract response for a page, whichever feature read it. Text first: it is the read
    made for this purpose, and a tables read of the same page carries the same words."""
    for feature in ('text', 'tables', 'tables-reread'):
        f = cache_dir(sha) / ('p%03d-%s.json' % (page, feature))
        if f.exists():
            return f
    return None


def unread(row):
    return [p for p in unranges(row['need']) if not cached_read(row['sha256'], p)]


def read(row):
    """Send the unread pages through textract_pages.py. Returns a note, or '' if it read them all."""
    import textract_spend as M
    todo = unread(row)
    if not todo:
        return ''
    if M.latched():
        return 'Textract is latched (%s)' % ('STOP-METERED' if M.METERED_STOP.exists() else 'STOP-TEXTRACT')
    p = subprocess.run([sys.executable, str(HERE / 'textract_pages.py'), str(AS.local_path(row['key'])),
                        '--pages', ranges(todo), '--feature', 'text'],
                       capture_output=True, text=True)
    left = unread(row)
    if p.returncode or left:
        tail = (p.stderr or p.stdout).strip().splitlines()[-1:] or ['']
        return '%d of %d page(s) still unread: %s' % (len(left), len(todo), tail[0][:200])
    return ''


# ------------------------------------------------------------------ 3. build

def to_pdf(page):
    """displayed (fraction across, fraction down) -> PDF user space, for any /Rotate.

    Textract measures the page as displayed. The PDF draws in the unrotated box, so a page carrying
    /Rotate 90 has its displayed top edge along the box's left side. Derived per quarter turn:
    a displayed point (dx, dy), measured from the top-left, sits at box offset (u, v) from the
    bottom-left."""
    box = page.cropbox
    L, B = float(box.left), float(box.bottom)
    Wb, Hb = float(box.width), float(box.height)
    rot = (page.rotation or 0) % 360
    Wd, Hd = (Hb, Wb) if rot in (90, 270) else (Wb, Hb)

    def f(fx, fy):
        dx, dy = fx * Wd, fy * Hd
        u, v = {0: (dx, Hb - dy), 90: (dy, dx), 180: (Wb - dx, dy), 270: (Wb - dy, Hb - dx)}[rot]
        return L + u, B + v
    return f


def pdf_string(s):
    b = s.encode('cp1252', 'replace')
    return b'(' + b.replace(b'\\', b'\\\\').replace(b'(', b'\\(').replace(b')', b'\\)') + b')'


def layer(page, blocks):
    """The content stream of invisible words for one page, and how many it holds."""
    f = to_pdf(page)
    ops, n = [b'BT 3 Tr ' + FONT.encode() + b' 1 Tf'], 0
    for b in blocks:
        if b['BlockType'] != 'WORD' or not b.get('Text'):
            continue
        poly = b['Geometry']['Polygon']                         # TL, TR, BR, BL
        tl, tr, bl = (f(poly[i]['X'], poly[i]['Y']) for i in (0, 1, 3))
        advance = COURIER_ADVANCE * len(b['Text'])
        ax, ay = (tr[0] - tl[0]) / advance, (tr[1] - tl[1]) / advance   # x: stretched to the word
        bx, by = tl[0] - bl[0], tl[1] - bl[1]                           # y: one em is the word's height
        if (ax == 0 and ay == 0) or (bx == 0 and by == 0):
            continue
        ops.append(b'%.4f %.4f %.4f %.4f %.2f %.2f Tm %s Tj'
                   % (ax, ay, bx, by, bl[0], bl[1], pdf_string(b['Text'])))
        n += 1
    ops.append(b'ET')
    return b'\n'.join(ops), n


def build(row, out_path):
    """Write the sandwich. Returns the number of words placed."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import (ArrayObject, DecodedStreamObject, DictionaryObject, NameObject)
    src = AS.local_path(row['key'])
    reader = PdfReader(str(src))
    writer = PdfWriter(clone_from=reader)
    font = writer._add_object(DictionaryObject({
        NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'),
        NameObject('/BaseFont'): NameObject('/Courier'),
        NameObject('/Encoding'): NameObject('/WinAnsiEncoding')}))
    words = 0
    for pn in unranges(row['need']):
        page = writer.pages[pn - 1]
        blocks = json.loads(cached_read(row['sha256'], pn).read_text())['Blocks']
        data, n = layer(page, blocks)
        if not n:
            continue
        words += n

        def stream(b):
            s = DecodedStreamObject()
            s.set_data(b)
            return writer._add_object(s.flate_encode())
        old = page.get('/Contents')
        old = old.get_object() if old is not None else None
        olds = list(old) if isinstance(old, ArrayObject) else ([page.raw_get('/Contents')] if old is not None else [])
        # the page's own graphics state is closed off before our layer, so a transform it leaves
        # open cannot move our words
        page[NameObject('/Contents')] = ArrayObject([stream(b'q\n'), *olds, stream(b'\nQ\n'), stream(data)])
        res = page.get('/Resources')
        res = res.get_object() if res is not None else DictionaryObject()
        res = DictionaryObject(res)                              # this page's own copy: a shared one is left alone
        fonts = res.get('/Font')
        fonts = DictionaryObject(fonts.get_object()) if fonts is not None else DictionaryObject()
        fonts[NameObject(FONT)] = font
        res[NameObject('/Font')] = fonts
        page[NameObject('/Resources')] = res
    meta = dict(reader.metadata or {})
    meta.update({'/Producer': 'lunenburgbudgetproject.org (%s): Amazon Textract words, invisible, '
                              'under the original pages' % BUILDER,
                 '/Subject': 'UNOFFICIAL SEARCHABLE COPY. Original: /docs/%s, sha256 %s'
                             % (row['key'], row['sha256'])})
    writer.add_metadata(meta)
    # deterministic: the same original and the same reads write the same bytes, so --check can
    # rebuild and compare, and a re-run uploads nothing that has not changed
    writer._ID = None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix('.tmp')
    with open(tmp, 'wb') as fh:
        writer.write(fh)
    os.replace(tmp, out_path)
    return words


# ------------------------------------------------------------------ 4. verify

def verify(row, path, sample=24):
    """Look for sampled Textract words in the built file, at their own position, with pdfium.
    Returns a list of problems; empty means every sampled word was found where it belongs."""
    import pypdfium2 as pdfium
    from pypdf import PdfReader
    pdf = pdfium.PdfDocument(str(path))
    rd = PdfReader(str(path))
    if len(pdf) != int(row['pages']):
        return ['page count %d, the original has %s' % (len(pdf), row['pages'])]
    need = unranges(row['need'])
    picks = []
    for pn in need:
        blocks = json.loads(cached_read(row['sha256'], pn).read_text())['Blocks']
        ws = [b for b in blocks if b['BlockType'] == 'WORD' and len(b.get('Text', '')) >= 4
              and b['Text'].isascii() and b['Text'].isalnum()]
        if ws:
            picks.append((pn, ws[len(ws) // 2]))
    step = max(1, len(picks) // sample)
    problems = []
    for pn, w in picks[::step][:sample]:
        f = to_pdf(rd.pages[pn - 1])
        xs, ys = zip(*(f(p['X'], p['Y']) for p in w['Geometry']['Polygon']))
        pad = 0.25 * (max(ys) - min(ys) + max(xs) - min(xs)) / 2
        got = pdf[pn - 1].get_textpage().get_text_bounded(min(xs) - pad, min(ys) - pad,
                                                          max(xs) + pad, max(ys) + pad)
        if w['Text'] not in got.replace('\r', ' ').replace('\n', ' '):
            problems.append('p%d: %r not found at its position (got %r)' % (pn, w['Text'], got[:60]))
    return problems


# ------------------------------------------------------------------ 5. push

def push(key, path):
    body = path.read_bytes()
    AS._request('PUT', AS._object_url(PREFIX + key, DERIVED_BUCKET), data=body,
                headers={'Content-Type': 'application/pdf', 'Content-Length': str(len(body))},
                timeout=900)
    want = hashlib.md5(body).hexdigest()
    got = {o['key']: (o.get('etag') or '').strip('"')
           for o in AS.list_objects(PREFIX + key, bucket=DERIVED_BUCKET)}.get(PREFIX + key)
    if got != want:
        raise RuntimeError('read back %s: etag %s, the file is %s' % (key, got, want))
    return want, len(body)


# ------------------------------------------------------------------ the step

def process(row, textract=True, upload=True, force=False):
    """Advance one document as far as it will go. Returns a one-line note."""
    if row['state'] == 'not needed' or row['verdict'] == 'unreadable':
        return ''                      # nothing to add, or a file pdf_kind itself could not open
    if row['state'] == 'built' and not force and row.get('builder', BUILDER) == BUILDER:
        return ''
    if textract:
        why = read(row)
        if why:
            row['read'] = str(len(unranges(row['need'])) - len(unread(row)))
            row['state'] = 'waiting'
            return '%s: waiting -- %s' % (row['key'], why)
    left = unread(row)
    row['read'] = str(len(unranges(row['need'])) - len(left))
    if left:
        row['state'] = 'waiting'
        return '%s: waiting -- %d of %d needed page(s) unread' % (row['key'], len(left), len(unranges(row['need'])))
    path = OUT / row['key']
    words = build(row, path)
    problems = verify(row, path)
    if problems:
        row['state'] = 'refused'
        return '%s: REFUSED -- %s' % (row['key'], '; '.join(problems[:3]))
    row['words'] = str(words)
    if not upload:
        row['state'] = 'waiting'
        return '%s: built locally, %d words, not pushed' % (row['key'], words)
    row['md5'], n = push(row['key'], path)
    row['bytes'] = str(n)
    row['builder'] = BUILDER
    row['state'] = 'built'
    return '%s: built, %d words, %d page(s) layered' % (row['key'], words, len(unranges(row['need'])))


def quote(rows):
    import textract_spend as M
    waiting = [r for r in rows.values() if r['state'] in ('waiting', 'refused')]
    pages = sum(len(unread(r)) for r in waiting)
    usd = pages * M.PRICE_PER_PAGE['text']
    print('%d document(s) waiting; %d page(s) without a Textract read: $%.2f at the text price ($%.4f/page)'
          % (len(waiting), pages, usd, M.PRICE_PER_PAGE['text']))
    print('this month $%.2f of the $%.2f cap' % (M.spent(month=M.month_of()), M.MONTHLY_CAP_USD))
    return usd


def status(rows):
    from collections import Counter
    c = Counter(r['state'] for r in rows.values())
    print('%d PDF(s) in the register: %s' % (len(rows), ', '.join('%d %s' % (n, s) for s, n in c.most_common())))
    man = manifest_pdfs()
    print('%d PDF(s) in the manifest not yet surveyed' % len([k for k in man if k not in rows or rows[k]['sha256'] != man[k]]))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--status', action='store_true')
    g.add_argument('--new', action='store_true')
    g.add_argument('--key')
    g.add_argument('--quote', action='store_true')
    g.add_argument('--check', action='store_true')
    ap.add_argument('--no-textract', action='store_true', help='spend nothing: build only from reads already held')
    ap.add_argument('--no-push', action='store_true', help='build and verify locally, register nothing as built')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--limit', type=int, default=0, help='--new: at most this many documents surveyed this run')
    a = ap.parse_args()
    rows = read_register()

    if a.status:
        return status(rows)
    if a.quote:
        return quote(rows)
    if a.check:
        # two questions: does every built copy still rebuild to the same bytes, and does the
        # bucket hold exactly those bytes -- asked of the bucket's own listing, not of a state file
        built = {k: r for k, r in rows.items() if r['state'] == 'built'}
        held = {o['key'][len(PREFIX):]: (o.get('etag') or '').strip('"')
                for o in AS.list_objects(PREFIX, bucket=DERIVED_BUCKET)}
        bad = 0
        for k, r in sorted(built.items()):
            if held.get(k) != r['md5']:
                print('NOT IN THE BUCKET as registered: %s (bucket %s, register %s)' % (k, held.get(k), r['md5']))
                bad += 1
                continue
            tmp = OUT / '.check' / k
            build(r, tmp)
            if hashlib.md5(tmp.read_bytes()).hexdigest() != r['md5']:
                print('STALE: %s no longer rebuilds to what the bucket holds' % k)
                bad += 1
        extra = sorted(set(held) - set(built))
        for k in extra[:20]:
            print('  in the bucket, not registered (left alone, never linked): %s' % k)
        print('%d built cop(ies) checked, %d problem(s); %d unregistered object(s) in the bucket'
              % (len(built), bad, len(extra)))
        return 1 if bad else 0

    import textract_spend as M
    textract, why_not = not a.no_textract, '--no-textract'
    if textract and M.latched():
        # said once for the run, not once per document
        textract, why_not = False, 'latched: %s' % ('STOP-METERED' if M.METERED_STOP.exists() else 'STOP-TEXTRACT')
    man = manifest_pdfs()
    gone = taken_down()
    if a.key:
        if a.key not in man:
            sys.exit('%s is not a PDF in the archive manifest' % a.key)
        keys = [a.key]
    else:
        keys = [k for k in sorted(man) if k not in gone]
    surveyed = 0
    for key in keys:
        r = rows.get(key)
        if r is None or r['sha256'] != man[key]:
            if a.limit and surveyed >= a.limit:
                continue
            if not AS.local_path(key) or not os.path.exists(AS.local_path(key)):
                continue
            try:
                rows[key] = r = survey(key, man[key])
            except Exception as e:                               # noqa: BLE001 -- recorded, not fatal
                rows[key] = r = {'key': key, 'sha256': man[key], 'verdict': 'unreadable',
                                 'pages': '', 'need': '', 'read': '', 'state': 'refused',
                                 'words': '', 'bytes': '', 'md5': ''}
                print('%s: REFUSED -- pdf_kind could not read it: %s' % (key, str(e)[:160]))
            surveyed += 1
            if surveyed % 200 == 0:
                write_register(rows)
        if textract and r['state'] in ('waiting', 'refused'):
            # STOP SHORT OF THE CAP, NEVER AT IT. Reaching the monthly cap latches Textract until a
            # person clears it; this backlog is meant to pace itself across months instead (TJ, 31
            # October 2026: $8 a month, ~$20 of pages). So a document whose pages would cross the
            # cap is left for next month, and so is every one after it.
            cost = len(unread(r)) * M.PRICE_PER_PAGE['text']
            if cost and M.spent(month=M.month_of()) + cost > M.MONTHLY_CAP_USD - HEADROOM_USD:
                textract, why_not = False, 'this month is spent to within $%.2f of the $%.2f cap; resumes next month' % (
                    HEADROOM_USD, M.MONTHLY_CAP_USD)
        before = (r['state'], r['read'])
        try:
            note = process(r, textract=textract, upload=not a.no_push, force=a.force)
        except Exception as e:                                   # noqa: BLE001 -- one document, not the run
            note = '%s: FAILED -- %s' % (key, str(e)[:200])
        if textract and note and 'STOPPED' in note:
            # the meter refused (a cap, the latch): every later document would be refused too
            textract, why_not = False, 'the meter refused: ' + note.split('STOPPED:', 1)[-1].strip()[:160]
            print(note, flush=True)
        # A DOCUMENT THAT DID NOT MOVE SAYS NOTHING. Thousands wait on Textract at once, and a
        # line each every morning would bury the one that was refused.
        if note and ((r['state'], r['read']) != before or 'FAILED' in note or a.key):
            print(note, flush=True)
            write_register(rows)                                 # after every document that moved
    write_register(rows)
    status(rows)
    waiting = [r for r in rows.values() if r['state'] == 'waiting']
    if waiting:
        print('%d waiting on %d unread page(s)%s' % (
            len(waiting), sum(len(unread(r)) for r in waiting),
            '' if textract else ' -- Textract not called this run (%s)' % why_not))


if __name__ == '__main__':
    main()
