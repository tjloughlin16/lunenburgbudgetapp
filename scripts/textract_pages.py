#!/usr/bin/env python3
"""READ A PDF'S PAGES WITH AMAZON TEXTRACT: the cells of every table, with their row and column.

    python3 scripts/textract_pages.py FILE --pages 12-30 --dry-run   # what it would send, and the cost
    python3 scripts/textract_pages.py FILE --pages 12-30             # send it, through the meter
    python3 scripts/textract_pages.py FILE --mapped                  # the pages annual-report-pages.csv maps
    python3 scripts/textract_pages.py FILE --all --feature text      # plain lines, a tenth of the price

WHY TEXTRACT, when macOS Vision is free and local. Not for the text: for the GRID. Vision returns
words and boxes, and every annual-report table was turned into rows by measuring the page
(CLAUDE.md 13b: the rotation, the row band, the column centres, a layout written down per year).
Textract's TABLES feature returns CELLs with RowIndex and ColumnIndex already assigned. Whether it
assigns them RIGHT is the open question, and the pilot measures it against the 511 pages already
proven; until then a Textract cell is a candidate, exactly as a Vision box was.

WHAT IT WRITES
  build/textract/cache/<sha256>/p<NNN>-<feature>.json   the raw response. PAID FOR: never deleted
                                                        by this script, and re-reading is free
  build/textract/out/<stem>.cells.tsv                   page, table, row, col, spans, confidence, text
  build/textract/out/<stem>.lines.tsv                   page, line, confidence, box, text

Both TSVs are rebuilt from the cache on every run, so they cannot drift from what AWS returned.

WHAT IT REFUSES
  * a file whose sha256 is in neither archive-manifest.csv nor redactions.csv nor
    ingest-pending.csv. A document is read after it is LANDED (ingest.py), never before: an
    unlanded file is one whose bytes nobody has backed up, and whose provenance nobody wrote down.
  * anything the meter refuses -- see textract_spend.py. A refusal stops the run where it is;
    everything already returned stays cached and is written out.

Pages go one at a time through the synchronous AnalyzeDocument call, as single-page PDFs (or a
JPEG where the page alone is over the 5 MB synchronous limit). No S3 bucket is involved,
and only the pages asked for are paid for.
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import textract_spend as M                                           # noqa: E402

ROOT = M.ROOT
OUT = M.STATE / 'out'
# The quotas page says 10 MB for a synchronous call; the API and boto3 references say 5 MB for a
# document sent as BYTES, which is what this does. The two are not reconciled, so the lower one.
# https://docs.aws.amazon.com/textract/latest/dg/limits-document.html, read 27 October 2026.
SYNC_LIMIT = 5 * 1024 * 1024
MAX_PIXELS = 10000                    # on any side, same page
REGISTERS = [ROOT / 'sources/data/archive-manifest.csv', ROOT / 'sources/data/redactions.csv',
             ROOT / 'sources/data/ingest-pending.csv']
PAGE_MAP = ROOT / 'sources/data/annual-report-pages.csv'


def shown(p):
    p = Path(p).resolve()
    return str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def landed(sha):
    for reg in REGISTERS:
        if not reg.exists():
            continue
        with open(reg, newline='') as f:
            for r in csv.DictReader(f):
                if sha in (r.get('sha256'), r.get('raw_sha256'), r.get('public_sha256')):
                    return reg.name
    return None


def page_count(path):
    from pypdf import PdfReader
    return len(PdfReader(str(path)).pages)


def parse_pages(spec, n):
    out = set()
    for part in spec.split(','):
        a, _, b = part.strip().partition('-')
        lo, hi = int(a), int(b or a)
        if lo < 1 or hi > n or lo > hi:
            raise SystemExit('page range %s is outside 1-%d' % (part, n))
        out.update(range(lo, hi + 1))
    return sorted(out)


def mapped_pages(path):
    rel = str(Path(path).resolve().relative_to(ROOT)) if Path(path).resolve().is_relative_to(ROOT) else ''
    stem = Path(path).stem
    with open(PAGE_MAP, newline='') as f:
        pages = sorted({int(r['page']) for r in csv.DictReader(f)
                        if r['document'] and (Path(r['document']).stem == stem or r['document'] == rel)})
    if not pages:
        raise SystemExit('%s has no pages in %s' % (stem, PAGE_MAP.relative_to(ROOT)))
    return pages


def page_bytes(path, page):
    """One page as something the synchronous API takes: a one-page PDF, or a JPEG if that is too big."""
    from pypdf import PdfReader, PdfWriter
    w = PdfWriter()
    w.add_page(PdfReader(str(path)).pages[page - 1])
    buf = io.BytesIO()
    w.write(buf)
    if buf.tell() < SYNC_LIMIT:
        return buf.getvalue(), 'pdf'
    # Too big as a PDF: almost always a high-resolution scan. Rasterise at 300 dpi first, so a
    # scan is not quietly downsampled below what it was captured at, and give up resolution only
    # as far as the limit forces -- and say so in the label, because a 150 dpi read is a weaker read.
    import pypdfium2 as pdfium
    pg = pdfium.PdfDocument(str(path))[page - 1]
    w_pt, h_pt = pg.get_size()
    for dpi in (300, 200, 150):
        scale = min(dpi / 72, MAX_PIXELS / max(w_pt, h_pt))
        img = pg.render(scale=scale).to_pil().convert('RGB')
        for q in (90, 80):
            buf = io.BytesIO()
            img.save(buf, 'JPEG', quality=q)
            if buf.tell() < SYNC_LIMIT:
                return buf.getvalue(), 'jpeg %d dpi q%d' % (round(scale * 72), q)
    raise ValueError('page %d is over the synchronous limit even as a 150 dpi JPEG' % page)


def cache_path(sha, page, feature):
    return M.CACHE / sha / ('p%03d-%s.json' % (page, feature))


class FakeTextract:
    """TEXTRACT_FAKE=1: a canned one-cell table, so the meter and the cache can be tested for $0."""

    def analyze_document(self, Document, FeatureTypes):
        return {'Blocks': [
            {'Id': 't', 'BlockType': 'TABLE', 'Relationships': [{'Type': 'CHILD', 'Ids': ['c']}]},
            {'Id': 'c', 'BlockType': 'CELL', 'RowIndex': 1, 'ColumnIndex': 1, 'RowSpan': 1,
             'ColumnSpan': 1, 'Confidence': 99.0, 'Relationships': [{'Type': 'CHILD', 'Ids': ['w']}]},
            {'Id': 'w', 'BlockType': 'WORD', 'Text': '$1,234.56', 'Confidence': 99.0},
            {'Id': 'l', 'BlockType': 'LINE', 'Text': 'FAKE $1,234.56', 'Confidence': 99.0,
             'Geometry': {'BoundingBox': {'Left': 0.1, 'Top': 0.1, 'Width': 0.2, 'Height': 0.01}}}],
            'DocumentMetadata': {'Pages': 1}, 'fake': True}

    def detect_document_text(self, Document):
        return self.analyze_document(Document, [])


def client():
    if os.environ.get('TEXTRACT_FAKE'):
        return FakeTextract()
    import boto3
    from botocore.config import Config
    return boto3.Session(profile_name=M.PROFILE).client(
        'textract', region_name='us-east-1',
        # Throttling is retried by the SDK; every retry is the SAME reserved page, not a new charge.
        config=Config(retries={'max_attempts': 6, 'mode': 'adaptive'}))


def call(tx, data, feature):
    if feature == 'tables':
        return tx.analyze_document(Document={'Bytes': data}, FeatureTypes=['TABLES', 'LAYOUT'])
    return tx.detect_document_text(Document={'Bytes': data})


def write_out(path, sha, feature):
    """The TSVs, from EVERY cached page of this document -- not just this run's, or a one-page
    run would overwrite the other pages' cells. A page never returned is simply absent."""
    OUT.mkdir(parents=True, exist_ok=True)
    stem = Path(path).stem
    cells, lines = [], []
    for cp in sorted((M.CACHE / sha).glob('p*-%s.json' % feature)):
        page = int(cp.stem.split('-')[0][1:])
        blocks = json.loads(cp.read_text())['Blocks']
        by_id = {b['Id']: b for b in blocks}

        def kids(b, kind='CHILD'):
            return [by_id[i] for rel in b.get('Relationships', []) if rel['Type'] == kind
                    for i in rel['Ids'] if i in by_id]

        n = 0
        for b in blocks:
            if b['BlockType'] == 'LINE':
                n += 1
                bb = b.get('Geometry', {}).get('BoundingBox', {})
                lines.append([page, n, '%.1f' % b.get('Confidence', 0),
                              '%.4f' % bb.get('Left', 0), '%.4f' % bb.get('Top', 0),
                              '%.4f' % bb.get('Width', 0), '%.4f' % bb.get('Height', 0), b['Text']])
        t = 0
        for b in blocks:
            if b['BlockType'] != 'TABLE':
                continue
            t += 1
            for c in kids(b):
                if c['BlockType'] != 'CELL':
                    continue
                text = ' '.join(w['Text'] for w in kids(c) if w['BlockType'] == 'WORD')
                cells.append([page, t, c['RowIndex'], c['ColumnIndex'], c.get('RowSpan', 1),
                              c.get('ColumnSpan', 1), '%.1f' % c.get('Confidence', 0), text])
    for name, head, data in (('cells', ['page', 'table', 'row', 'col', 'rowspan', 'colspan',
                                        'confidence', 'text'], cells),
                             ('lines', ['page', 'line', 'confidence', 'left', 'top', 'width',
                                        'height', 'text'], lines)):
        p = OUT / ('%s.%s.tsv' % (stem, name))
        tmp = p.with_suffix('.tmp')
        with open(tmp, 'w', newline='') as f:
            w = csv.writer(f, delimiter='\t', lineterminator='\n')
            w.writerow(head)
            w.writerows(data)
        os.replace(tmp, p)
    return len(cells), len(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('file')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--pages', help='e.g. 12-30,41')
    g.add_argument('--mapped', action='store_true', help='the pages annual-report-pages.csv holds for it')
    g.add_argument('--all', action='store_true')
    ap.add_argument('--feature', choices=sorted(M.PRICE_PER_PAGE), default='tables')
    ap.add_argument('--max-usd', type=float, help='run ceiling; default twice the estimate, at least $0.10')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-aws-check', action='store_true', help='skip reading the AWS budget (tests)')
    a = ap.parse_args()

    path = Path(a.file)
    sha = sha256_of(path)
    where = landed(sha)
    if not where:
        sys.exit('REFUSED: %s (sha256 %s...) is not landed -- not in the manifest, the redaction '
                 'register or ingest-pending. Run it through scripts/ingest.py first.' % (path, sha[:12]))
    n = page_count(path)
    pages = (parse_pages(a.pages, n) if a.pages else mapped_pages(path) if a.mapped
             else list(range(1, n + 1)))
    todo = [p for p in pages if not cache_path(sha, p, a.feature).exists()]
    price = M.PRICE_PER_PAGE[a.feature]
    est = round(len(todo) * price, 4)
    ceiling = a.max_usd if a.max_usd is not None else max(0.10, round(2 * est, 2))
    month = M.spent(month=M.month_of())
    print('%s  (%s, %d pages, landed in %s)' % (path.name, sha[:12], n, where))
    print('%d page(s) asked for, %d cached already (free), %d to send at $%.4f: $%.4f; ceiling $%.2f; '
          'this month $%.2f of the $%.2f cap'
          % (len(pages), len(pages) - len(todo), len(todo), price, est, ceiling, month, M.MONTHLY_CAP_USD))
    if a.dry_run or not todo:
        if not a.dry_run:
            print('cells %d, lines %d -> %s' % (*write_out(path, sha, a.feature), shown(OUT)))
        return

    run = '%s-%s-%d' % (dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ'), sha[:8], os.getpid())
    tx = client()
    stopped = None
    done = 0
    try:
        with M.Meter(run, ceiling, aws=not a.no_aws_check) as meter:
            meter.progress(path.name, len(todo), 0)
            for page in todo:
                try:
                    data, form = page_bytes(path, page)
                except Exception as e:                       # noqa: BLE001 -- nothing sent, nothing spent
                    print('  p%d  NOT SENT: %s' % (page, e))
                    continue
                meter.reserve(sha, page, a.feature)
                t0 = time.time()
                try:
                    resp = call(tx, data, a.feature)
                except Exception as e:                       # noqa: BLE001 -- counted as spent, reported
                    meter.outcome(sha, page, a.feature, 'failed:%s' % type(e).__name__)
                    print('  p%d  FAILED (counted as spent): %s' % (page, str(e).splitlines()[0][:160]))
                    continue
                resp.pop('ResponseMetadata', None)
                cp = cache_path(sha, page, a.feature)
                cp.parent.mkdir(parents=True, exist_ok=True)
                tmp = cp.with_suffix('.tmp')
                tmp.write_text(json.dumps(resp))
                os.replace(tmp, cp)
                meter.outcome(sha, page, a.feature, 'ok')
                done += 1
                meter.progress(path.name, len(todo), done)
                blocks = resp.get('Blocks', [])
                print('  p%d  %s, %.1fs, %d table(s), %d line(s)'
                      % (page, form, time.time() - t0, sum(b['BlockType'] == 'TABLE' for b in blocks),
                         sum(b['BlockType'] == 'LINE' for b in blocks)), flush=True)
    except M.Refused as e:
        stopped = str(e)
    print('sent %d page(s); this run $%.4f; this month $%.2f of $%.2f'
          % (done, M.spent(run=run), M.spent(month=M.month_of()), M.MONTHLY_CAP_USD))
    print('cells %d, lines %d -> %s' % (*write_out(path, sha, a.feature), shown(OUT)))
    if stopped:
        sys.exit('STOPPED: %s' % stopped)


if __name__ == '__main__':
    main()
