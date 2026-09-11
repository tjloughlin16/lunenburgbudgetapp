#!/usr/bin/env python3
"""One full-text index over everything this project holds, corpus by corpus.

    python3 scripts/build_search_index.py            # add or refresh what has changed
    python3 scripts/build_search_index.py --rebuild  # from scratch
    python3 scripts/build_search_index.py --check    # fail if it has drifted from its inputs
    python3 scripts/build_search_index.py --status   # what is in it; writes nothing
    python3 scripts/build_search_index.py --export DIR   # the rows, as SQL, for the D1 push

WHY THIS EXISTS, AND WHY NOW

TJ, 11 September 2026: *"People need to be able to find things once we start pushing
people here."* The blog exists to bring strangers in from Facebook, and a stranger who
searches for the one thing they care about and finds nothing concludes the site does not
have it. So the search has to cover EVERYTHING a reader might land on -- the pages, the
posts, the documents, the minutes, the recordings -- and it has to be built to take blog
posts that do not exist yet, because the next post is the thing most likely to be searched
for the day after it goes out.

`build_minutes_fts.py` already indexes two of those corpora and this reuses its readers
rather than re-describing them. What it adds is the other three, and a shape that can be
pushed to D1 as one table.

FIVE CORPORA, AND EACH KEEPS ITS OWN DENOMINATOR

    minutes     text the extractor pulled out of a file THE TOWN PUBLISHED. A record.
    transcript  machine captions of a recording. OURS, derived, a FINDING AID. Cited as
                the video at a timestamp, never as a document.
    source      the archive's documents -- budgets, annual reports, DESE files -- one row
                per PAGE, so a hit cites a page of a PDF rather than a 200-page file.
    page        the site's own pages, from the prerendered build. One row per page.
    post        blog posts, and ONLY the ones in PUBLISHED. The drafts are not on the
                site and must not be findable through it either -- `build_blog.py --check`
                walks the built site for exactly that, and an index that leaked a draft
                would be the hole it is looking for.

The line between them is a column, `corpus`, and every count is reported against its own
corpus. Rule 13: a transcript hit locates a MOMENT; a caption model hears *fifteen
hundred*, *$1,500* and *$50* alike, and a figure read off one is never the record.

ONE TABLE, BECAUSE D1 IS WHERE IT IS GOING

The local index has a `doc` table beside its `fts` table. Here the metadata rides in the
FTS5 table itself as UNINDEXED columns, which FTS5 supports for exactly this: the row is
one row, an insert is one statement, and the push to D1 -- which bills in ROWS WRITTEN --
costs one row per chunk rather than two. Measured, 11 September: 1,002 rows written for
1,000 chunks, ~3MB per thousand.

STALENESS IS MEASURED, NOT TRUSTED

Every indexed file's sha256 is stored beside it; `--check` recomputes them all and fails
on drift; `--status` prints the build date and the count per corpus, which is what the
search page shows the reader. An index quietly older than its inputs is the shape of
nearly every defect in this repository.

It is DERIVED and gitignored, like `minutes-fts.db` and `lunenburg.db`. The text files,
the build and `blog.json` are the sources of truth; this can be rebuilt from them at any
time.
"""
import argparse
import csv
import datetime as dt
import html
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import build_minutes_fts as M  # noqa: E402  -- the two readers it already has

DB = os.path.join(ROOT, 'sources', 'data', 'search-fts.db')
SRC = os.path.join(ROOT, 'sources')
DIST = os.path.join(ROOT, 'fy28', 'dist')
BLOG_JSON = os.path.join(ROOT, 'fy28', 'public', 'data', 'blog.json')
# The town's words for ours. Curated by hand in the CSV, published as JSON for the search
# page, which offers them when a search finds little. Constraint 3 of QUEUE item 18: a
# resident types "foreign language" and the archive says "French", and a null result on a
# public search reads as "the town never discussed it".
VOCAB_CSV = os.path.join(ROOT, 'sources', 'data', 'search-vocabulary.csv')
VOCAB_JSON = os.path.join(ROOT, 'fy28', 'public', 'data', 'search-vocabulary.json')
SITE = M.SITE

TOKENIZE = M.TOKENIZE
PAGE_MARKER = re.compile(r'^===PAGE (\d+)===$', re.M)

# Source folders whose documents are indexed by page. `meetings` is the minutes corpus and
# has its own reader; `data`, `analyses` and `views` are ours or are symlinks.
SOURCE_FOLDERS = ('district-budget', 'state-dese', 'town-annual-reports', 'town-budget',
                  'town-supplementary')

# Site pages that are not content: forms, the machine-facing pages, the drafts page.
PAGE_SKIP = {'ask', 'ask-a-question', 'agents', 'blog-drafts', '404', 'not-found', 'search'}

META_COLS = ['corpus', 'doc_key', 'file_key', 'title', 'board', 'board_slug', 'date',
             'kind', 'cite_url', 'source_url', 'start_s', 'seg_starts', 'chars']
COLS = ['body'] + META_COLS

SCHEMA = """
CREATE TABLE indexed_file (
    file_key    TEXT PRIMARY KEY,
    corpus      TEXT NOT NULL,
    sha256      TEXT NOT NULL,
    bytes       INTEGER,
    rows        INTEGER
);
CREATE TABLE build_meta (k TEXT PRIMARY KEY, v TEXT);
"""


def fts_ddl(name='search'):
    return ('CREATE VIRTUAL TABLE %s USING fts5(body, %s, tokenize=%r)'
            % (name, ', '.join(c + ' UNINDEXED' for c in META_COLS), TOKENIZE))


def rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, '/')


# ---------------------------------------------------------------------- minutes, captions

def minutes_files():
    out = M.document_files()
    for e in out:
        e['corpus'] = 'minutes'
    return out


def minutes_rows(entry):
    rows = M.document_rows(entry)
    for row, body in rows:
        row['corpus'] = 'minutes'
        row['title'] = '%s, %s' % (row.get('board') or row['board_slug'], row.get('date') or '')
        row['title'] = ('%s — %s' % (row['title'], row['kind'])) if row.get('kind') else row['title']
    return rows


def transcript_rows(entry):
    rows = M.transcript_rows(entry)
    for row, body in rows:
        row['title'] = '%s, %s — recording' % (row['board'], row['date'])
    return rows


# ---------------------------------------------------------------- the archive's documents

def source_files():
    """Every archive document with an extracted text, off its folder's index.csv.

    The index is read rather than the folder walked, for the same reason as the minutes:
    a stray text file with no label and no upstream must not enter with no citation.
    """
    out = []
    for folder in SOURCE_FOLDERS:
        idx = os.path.join(SRC, folder, 'index.csv')
        if not os.path.exists(idx):
            continue
        for r in csv.DictReader(open(idx, encoding='utf-8', errors='replace')):
            text = (r.get('text') or '').strip()
            if not text:
                continue
            path = os.path.join(ROOT, text)
            if not os.path.exists(path):
                continue
            local = (r.get('local') or '').strip()
            out.append({
                'file': path,
                'file_key': rel(path),
                'corpus': 'source',
                'folder': folder,
                'label': (r.get('label') or '').strip() or os.path.basename(local),
                'local': local,
                'upstream': (r.get('upstream') or '').strip(),
            })
    return out


def source_rows(entry):
    """One row per PAGE, so the citation is a page of the document and not the document.

    A 200-page annual report as one row would match everything and cite nothing. The
    `===PAGE n===` markers are the extractor's own and are stripped from the body.
    """
    raw = open(entry['file'], encoding='utf-8', errors='replace').read()
    parts = PAGE_MARKER.split(raw)
    # split() yields [preamble, n1, text1, n2, text2, ...]
    pages = []
    if parts[0].strip():
        pages.append((None, parts[0]))
    for i in range(1, len(parts) - 1, 2):
        pages.append((int(parts[i]), parts[i + 1]))
    stem = os.path.splitext(os.path.basename(entry['file']))[0]
    doc_url = '%s/docs/%s' % (SITE, entry['local'][len('sources/'):]) if entry['local'] else ''
    text_url = '%s/docs/%s' % (SITE, entry['file_key'][len('sources/'):])
    out = []
    for n, text in pages:
        body = re.sub(r'[ \t]+', ' ', text).strip()
        if len(body) < 40:
            continue
        cite = ('%s#page=%d' % (doc_url, n)) if (doc_url and n) else (doc_url or text_url)
        out.append(({
            'corpus': 'source',
            'doc_key': '%s/%s#p%s' % (entry['folder'], stem, n if n else '0'),
            'file_key': entry['file_key'],
            'title': entry['label'] + ((', page %d' % n) if n else ''),
            'board': entry['folder'],
            'board_slug': entry['folder'],
            'date': '',
            'kind': 'document page',
            'cite_url': cite,
            'source_url': entry['upstream'],
            'start_s': n,
            'seg_starts': None,
            'chars': len(body),
        }, body))
    return out


# ----------------------------------------------------------------------- the site's pages

TAG = re.compile(r'<[^>]+>')
DROP = re.compile(r'<(script|style|nav|header|footer|noscript)\b.*?</\1>', re.S | re.I)
TITLE = re.compile(r'<title>(.*?)</title>', re.S | re.I)
# The <title> is the site's, on every page. The page's own name is its first <h1>.
H1 = re.compile(r'<h1\b[^>]*>(.*?)</h1>', re.S | re.I)


def page_files():
    """Every prerendered page in the build. Empty, and said so, when there is no build."""
    if not os.path.isdir(DIST):
        return []
    out = []
    for dirpath, _, names in os.walk(DIST):
        for name in names:
            if not name.endswith('.html'):
                continue
            path = os.path.join(dirpath, name)
            route = rel(path)[len('fy28/dist/'):-len('.html')]
            if route == 'index':
                route = ''
            if route.split('/')[0] in PAGE_SKIP or route.startswith('share/'):
                continue
            out.append({'file': path, 'file_key': rel(path), 'corpus': 'page',
                        'route': route})
    return out


def page_rows(entry):
    raw = open(entry['file'], encoding='utf-8', errors='replace').read()
    m = H1.search(raw) or TITLE.search(raw)
    title = html.unescape(TAG.sub('', m.group(1))).strip() if m else entry['route']
    title = re.sub(r'\s+', ' ', title)
    body_html = DROP.sub(' ', raw)
    body = html.unescape(TAG.sub(' ', body_html))
    body = re.sub(r'\s+', ' ', body).strip()
    if len(body) < 80:
        return []
    return [({
        'corpus': 'page',
        'doc_key': 'page:' + (entry['route'] or 'home'),
        'file_key': entry['file_key'],
        'title': title,
        'board': None, 'board_slug': None, 'date': '',
        'kind': 'page',
        'cite_url': '%s/%s' % (SITE, entry['route']),
        'source_url': None,
        'start_s': None, 'seg_starts': None,
        'chars': len(body),
    }, body)]


# ---------------------------------------------------------------------- published posts

def post_files():
    """The published posts, and only those, out of the payload the site itself serves.

    `blog.json` carries `posts: []` until something is in PUBLISHED, so with nothing
    published this corpus is empty. That is correct, and it is the whole design: a draft
    reaches the index by the same single act that puts it on the site.
    """
    if not os.path.exists(BLOG_JSON):
        return []
    return [{'file': BLOG_JSON, 'file_key': rel(BLOG_JSON), 'corpus': 'post'}]


def post_rows(entry):
    d = json.load(open(entry['file'], encoding='utf-8'))
    out = []
    for p in d.get('posts', []):
        if not p.get('published'):
            continue
        parts = [p.get('headline', ''), p.get('support', ''), p.get('takeaway', '')]
        parts += [i.get('text', '') for i in p.get('impacts', [])]
        body = re.sub(r'\s+', ' ', ' '.join(x for x in parts if x)).strip()
        body = body.replace('**', '')
        out.append(({
            'corpus': 'post',
            'doc_key': 'post:' + p['slug'],
            'file_key': entry['file_key'],
            'title': p.get('title') or p['slug'],
            'board': None, 'board_slug': None,
            'date': p.get('published') or '',
            'kind': p.get('format') or 'post',
            'cite_url': '%s/blog/%s' % (SITE, p['slug']),
            'source_url': None,
            'start_s': None, 'seg_starts': None,
            'chars': len(body),
        }, body))
    return out


# ------------------------------------------------------------------------------- the build

READERS = {
    'minutes': minutes_rows,
    'transcript': transcript_rows,
    'source': source_rows,
    'page': page_rows,
    'post': post_rows,
}


def wanted():
    out = {}
    for e in (minutes_files() + M.transcript_files() + source_files()
              + page_files() + post_files()):
        e['sha256'] = M.sha256_of(e['file'])
        out[e['file_key']] = e
    if not out:
        raise SystemExit('no inputs found at all; refusing to write an empty index')
    return out


def connect(path, create):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    if create:
        db.executescript(SCHEMA)
        db.execute(fts_ddl())
    return db


def have(db):
    return {r['file_key']: dict(r) for r in db.execute('SELECT * FROM indexed_file')}


def drift(db):
    w, h = wanted(), have(db)
    # No build on disk means nothing can be said about the pages, not that they are gone.
    # A clone that has never built the site must not report 78 removed files.
    if not os.path.isdir(DIST):
        h = {k: v for k, v in h.items() if v['corpus'] != 'page'}
    added = [k for k in w if k not in h]
    changed = [k for k in w if k in h and w[k]['sha256'] != h[k]['sha256']]
    removed = [k for k in h if k not in w]
    return w, h, added, changed, removed


# D1 refuses a statement past about 100KB, and one row is one statement's worth at
# minimum -- the site's database page is 409KB of text and four minutes documents pass
# 100KB. A body over this is split into parts at a paragraph break; every part keeps the
# document's citation and the search de-duplicates hits on it.
MAX_CHARS = 40_000


def split_body(body):
    if len(body) <= MAX_CHARS:
        return [body]
    parts, buf = [], ''
    for para in re.split(r'(?<=[.!?])\s+|\n{2,}', body):
        if buf and len(buf) + len(para) + 1 > MAX_CHARS:
            parts.append(buf)
            buf = ''
        buf = (buf + ' ' + para).strip() if buf else para
    if buf:
        parts.append(buf)
    return parts


def index_file(db, entry):
    rows = []
    for row, body in READERS[entry['corpus']](entry):
        parts = split_body(body)
        for i, part in enumerate(parts):
            r = dict(row)
            if i:
                r['doc_key'] = '%s#part%d' % (row['doc_key'], i + 1)
            r['chars'] = len(part)
            rows.append((r, part))
    for row, body in rows:
        db.execute('INSERT INTO search (%s) VALUES (%s)' % (','.join(COLS), ','.join('?' * len(COLS))),
                   [body] + [row.get(c) for c in META_COLS])
    db.execute('INSERT OR REPLACE INTO indexed_file VALUES (?,?,?,?,?)',
               (entry['file_key'], entry['corpus'], entry['sha256'],
                os.path.getsize(entry['file']), len(rows)))
    return len(rows)


def forget(db, file_key):
    db.execute('DELETE FROM search WHERE file_key=?', (file_key,))
    db.execute('DELETE FROM indexed_file WHERE file_key=?', (file_key,))


def build(rebuild=False, quiet=False):
    fresh = rebuild or not os.path.exists(DB)
    if rebuild and os.path.exists(DB):
        os.remove(DB)
    db = connect(DB, create=fresh)
    if fresh:
        w = wanted()
        added, changed, removed = list(w), [], []
    else:
        w, _, added, changed, removed = drift(db)
    for k in removed + changed:
        forget(db, k)
    n = 0
    for i, k in enumerate(added + changed, 1):
        n += index_file(db, w[k])
        if not quiet and i % 500 == 0:
            print('  %d/%d files' % (i, len(added) + len(changed)), file=sys.stderr)
    db.execute('INSERT OR REPLACE INTO build_meta VALUES (?,?)', ('tokenize', TOKENIZE))
    if added or changed or removed or fresh:
        db.execute('INSERT OR REPLACE INTO build_meta VALUES (?,?)',
                   ('built', dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')))
    db.commit()
    if added or changed or removed:
        db.execute("INSERT INTO search(search) VALUES('optimize')")
        db.commit()
    if not quiet:
        print('%s %s: +%d file(s), %d changed, %d removed, %d row(s) written'
              % ('rebuilt' if fresh else 'refreshed', rel(DB), len(added), len(changed),
                 len(removed), n))
    return db


def vocabulary():
    rows = list(csv.DictReader(open(VOCAB_CSV, encoding='utf-8')))
    if len(rows) < 10:
        raise SystemExit('%s parsed to %d rows; refusing to publish an empty vocabulary'
                         % (rel(VOCAB_CSV), len(rows)))
    out = {}
    for r in rows:
        key = r['you_might_type'].strip().lower()
        out[key] = {'try': [t.strip() for t in r['the_archive_says'].split(';') if t.strip()],
                    'note': (r.get('note') or '').strip()}
    return json.dumps(out, indent=1, ensure_ascii=False) + '\n'


def write_vocabulary():
    with open(VOCAB_JSON, 'w', encoding='utf-8') as fh:
        fh.write(vocabulary())


def check_vocabulary():
    current = open(VOCAB_JSON, encoding='utf-8').read() if os.path.exists(VOCAB_JSON) else ''
    if current != vocabulary():
        print('STALE: %s does not reproduce from %s' % (rel(VOCAB_JSON), rel(VOCAB_CSV)))
        return 1
    return 0


def status(db):
    built = db.execute("SELECT v FROM build_meta WHERE k='built'").fetchone()
    print('built %s' % (built['v'] if built else 'never'))
    print('  %-12s %8s %10s' % ('corpus', 'files', 'rows'))
    for r in db.execute('SELECT f.corpus, COUNT(*) files, SUM(rows) rows FROM indexed_file f '
                        'GROUP BY f.corpus ORDER BY f.corpus'):
        print('  %-12s %8d %10d' % (r['corpus'], r['files'], r['rows'] or 0))
    if not os.path.isdir(DIST):
        print('  NOTE: fy28/dist is absent, so the page corpus reflects the last build indexed')


def check(db):
    w, h, added, changed, removed = drift(db)
    if added or changed or removed:
        print('STALE: %d added, %d changed, %d removed since the index was built'
              % (len(added), len(changed), len(removed)))
        for k in (added + changed + removed)[:12]:
            print('  ' + k)
        return 1
    if check_vocabulary():
        return 1
    print('ok: %s matches its %d input files; the vocabulary reproduces' % (rel(DB), len(w)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rebuild', action='store_true')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    if a.status or a.check:
        if not os.path.exists(DB):
            print('no index at %s; run without --status/--check to build it' % rel(DB))
            return 1
        db = connect(DB, create=False)
        return check(db) if a.check else (status(db) or 0)
    db = build(rebuild=a.rebuild, quiet=a.quiet)
    write_vocabulary()
    status(db)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
