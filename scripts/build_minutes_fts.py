#!/usr/bin/env python3
"""A full-text index over BOTH meeting corpora, kept honestly apart.

    python3 scripts/build_minutes_fts.py            # add or refresh what has changed
    python3 scripts/build_minutes_fts.py --rebuild  # from scratch, dropping everything
    python3 scripts/build_minutes_fts.py --check    # fail if it has drifted from the text
    python3 scripts/build_minutes_fts.py --status   # what is in it, written nothing

WHY A GREP IS NO LONGER ENOUGH

`search_minutes.py` greps `sources/meetings/text/`. That is 61MB and takes a second and a
half, which is fine. Adding the meeting CAPTIONS takes it toward 280MB, at which point a
search costs twenty seconds -- and a tool that costs twenty seconds stops being run, which
is the real price. Rule 15a asks everybody here to search the archive before concluding a
thing was never discussed; the cost of that search is therefore load-bearing.

But speed is the smaller half. A grep has no idea what a word is:

    ELL    matched 3,049 documents, through *well*, *shell*, *sell*.   The truth is 2.
    ESSER  matched 125, through *lesser* and *assessor*.               The truth is 34.
    Latin  matched 140, through *relating*.                            The truth is 5.

Every one of those is a rule 13 failure waiting to be made -- a reader who searches `ELL`
and is handed 3,049 documents does not conclude the tool is wrong, they conclude the
district discusses English learners constantly. A real tokenizer ends that class of error
outright, and brings phrases, NEAR and BM25 ranking with it. Today's 28 hits for
`paraprofessional` come back in filename order, which is no order at all.

TWO CORPORA, ONE INDEX, AND THE LINE BETWEEN THEM IS A COLUMN

  ``document``    text the extractor pulled out of a file THE TOWN PUBLISHED. A record.
  ``transcript``  machine captions of a recording. OURS, derived, and a FINDING AID.

`fetch_youtube_transcripts.py` deliberately keeps the caption files out of
`sources/meetings/text/` so that a grep cannot return the two interchangeably. Putting
both in one index does not undo that: every row carries its `corpus`, every count is
reported against its own denominator, and every transcript hit is cited as a VIDEO AT A
TIMESTAMP rather than as a document. A caption model hears *fifteen hundred*, *$1,500* and
*$50* alike. A transcript hit locates the moment; it never settles what was said.

THE GRAIN IS DIFFERENT ON THE TWO SIDES, ON PURPOSE

A published document is one row: it has one address and that address is the whole file.

A transcript is one row per ~60 SECONDS of the recording, because the citable address of a
caption is `watch?v=...&t=<seconds>` and a whole-meeting row could not produce one. Each
chunk keeps the character offset of every segment inside it, so a hit resolves to the
segment's own start rather than to the top of the chunk. Chunks overlap by one segment so
a phrase spoken across a boundary is still found; the same segment therefore appears in two
rows, and the search de-duplicates on the segment start.

STEMMING: `porter`, AND THE COST IS STATED IN THE OUTPUT

`porter` folds *budget*, *budgets* and *budgeting* together, which is what somebody
searching a meeting archive almost always wants and what a grep for `budget` gives them
anyway. What it costs is exactness: a search for `assess` now also matches *assessed*, and
a reader who is not told cannot tell. So the stem is not hidden -- `search_minutes.py` uses
FTS5's own `highlight()` to recover the SURFACE FORMS that actually matched in each
document and prints them, marking a hit `exact` when the reader's own word is among them
and naming the variant when it is not. The behaviour is visible rather than argued about.

WHERE IT LIVES, AND WHY NOT IN `lunenburg.db`

Its own file, `sources/data/minutes-fts.db`. Three reasons, in order of weight:

  1. **D1.** Everything in `lunenburg.db` is pushed to D1 by `sync_d1.py`, which is already
     at the free tier's write budget -- a full replace is ~51,000 rows against a limit of
     100,000 a day. This index is an order of magnitude more rows than that and would take
     the endpoint dark. Row counts, not bytes, are the thing that bills there.
  2. **Weight.** `lunenburg.db` is 31MB and is downloaded whole from R2 by anybody who
     wants to query the budget. The text of every meeting since 2013 is not budget data and
     must not become the price of asking a budget question.
  3. **Cadence.** `lunenburg.db` is rebuilt wholesale from the CSVs. This is rebuilt
     incrementally as captions arrive -- there is a backfill running as this is written,
     adding a meeting every 45 seconds -- and the two do not want the same run.

It is DERIVED and gitignored, exactly like `lunenburg.db`: it can be rebuilt from the text
files at any time and it is never a source of truth. The text files are.

STALENESS IS THE REAL RISK AND IT IS NOT LEFT TO TRUST

An index quietly older than the text it indexes is the shape of nearly every defect in this
repo: something derived was written down, the thing it derived from moved, and nothing
connected the two. So every indexed file's sha256 is stored beside it, `--check` recomputes
all of them, and `search_minutes.py` re-reads the manifest on EVERY run and says on every
run whether the index is current -- and greps the difference directly rather than reporting
a smaller archive than it holds.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN = os.path.join(ROOT, 'sources', 'meetings')
TEXT = os.path.join(MIN, 'text')
INDEX_CSV = os.path.join(MIN, 'index.csv')
TRANSCRIPTS = os.path.join(ROOT, 'sources', 'data', 'youtube-transcripts')
TRANSCRIPT_INDEX = os.path.join(ROOT, 'sources', 'data', 'youtube-transcript-index.csv')
SEARCHABLE = os.path.join(ROOT, 'sources', 'data', 'minutes-searchable.csv')
DB = os.path.join(ROOT, 'sources', 'data', 'minutes-fts.db')
SITE = 'https://lunenburgbudgetproject.org'

# Ours, written by scripts/extract_minutes.py. Indexing them would make `PAGE` a term in
# every document in the archive.
PAGE_MARKER = re.compile(r'^===PAGE \d+===$', re.M)

# Seconds of recording per indexed row. A citable caption address is a timestamp, so the
# row has to be small enough that its own start time IS the answer to "where in the
# meeting". Sixty seconds is about 160 words here.
CHUNK_SECONDS = 60

TOKENIZE = 'porter unicode61 remove_diacritics 2'

SCHEMA = """
CREATE TABLE doc (
    rowid       INTEGER PRIMARY KEY,
    corpus      TEXT NOT NULL,      -- 'document' (the town published it) | 'transcript'
    doc_key     TEXT NOT NULL,      -- stem, or <video_id>#<chunk ordinal>
    file_key    TEXT NOT NULL,      -- the file on disk this row came out of
    board       TEXT,
    board_slug  TEXT,
    date        TEXT,
    kind        TEXT,               -- minutes / agenda / ... ; 'recording' for captions
    cite_url    TEXT NOT NULL,      -- WHERE TO CITE. A document, or a video AT A TIME.
    source_url  TEXT,               -- the town's own page, or the video
    start_s     INTEGER,            -- transcript chunk start; NULL for a document
    end_s       INTEGER,
    seg_starts  TEXT,               -- JSON [[char_offset, seconds], ...] within the chunk
    chars       INTEGER
);
CREATE INDEX doc_file ON doc(file_key);
CREATE INDEX doc_corpus ON doc(corpus, date);

-- What was indexed, so staleness is a measurement rather than a hope.
CREATE TABLE indexed_file (
    file_key    TEXT PRIMARY KEY,   -- repo-relative path
    corpus      TEXT NOT NULL,
    sha256      TEXT NOT NULL,
    bytes       INTEGER,
    rows        INTEGER
);

CREATE TABLE build_meta (k TEXT PRIMARY KEY, v TEXT);
"""


def rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, '/')


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


# ------------------------------------------------------------------ the town's documents

def document_files():
    """One entry per extracted text file the town's own index points at.

    Read off `sources/meetings/index.csv` rather than by walking the text folder, so a
    stray file cannot enter the index with no board, no date and no citable address.
    """
    rows = list(csv.DictReader(open(INDEX_CSV, encoding='utf-8', errors='replace')))
    if not rows:
        raise SystemExit('sources/meetings/index.csv parsed to zero rows. Refusing to '
                         'build an index over an archive that reads as empty.')
    out = []
    for r in rows:
        path = (r.get('path') or '').strip()
        if not path:
            continue
        stem = os.path.splitext(path)[0]
        txt = os.path.join(TEXT, stem + '.txt')
        if not os.path.exists(txt):
            continue
        out.append({
            'file': txt,
            'file_key': rel(txt),
            'corpus': 'document',
            'doc_key': stem,
            'board': r.get('board', ''),
            'board_slug': stem.split('/')[0],
            'date': r.get('date', ''),
            'kind': r.get('kind', ''),
            'cite_url': '%s/docs/minutes/text/%s.txt' % (SITE, stem),
            'source_url': r.get('url', ''),
        })
    return out


def document_rows(entry):
    """A published document is ONE row: it has one address, and it is the whole file."""
    raw = open(entry['file'], encoding='utf-8', errors='replace').read()
    body = PAGE_MARKER.sub('', raw)
    if not body.strip():
        # Held, extracted, and holding nothing a search could match. That is
        # `build_minutes_searchable.py`'s finding and it stays that script's to report;
        # here it simply means there is nothing to index.
        return []
    row = dict(entry)
    row.pop('file')
    row['start_s'] = None
    row['end_s'] = None
    row['seg_starts'] = None
    row['chars'] = len(body)
    return [(row, body)]


# --------------------------------------------------------------------- our own captions

def transcript_files():
    """Every transcript the index lists, RE-READ ON EVERY RUN.

    The index is growing while this is being written -- a backfill adds a meeting every
    45 seconds -- so nothing here may cache a count or assume one.
    """
    if not os.path.exists(TRANSCRIPT_INDEX):
        return []
    out = []
    for r in csv.DictReader(open(TRANSCRIPT_INDEX, encoding='utf-8', errors='replace')):
        path = os.path.join(ROOT, r['path'])
        if not os.path.exists(path):
            continue
        out.append({
            'file': path,
            'file_key': r['path'],
            'corpus': 'transcript',
            'video_id': r['video_id'],
            'board_slug': r['board_slug'],
            'date': r['meeting_date'],
        })
    return out


def transcript_rows(entry):
    """One row per ~60 seconds, because the citable address of a caption is a timestamp.

    Chunks overlap by one segment so a phrase spoken across a boundary is still found. The
    duplicate that creates is de-duplicated at search time on the segment's start, which is
    the only identifier that survives the overlap.
    """
    doc = json.load(open(entry['file'], encoding='utf-8'))
    segs = doc.get('segments') or []
    if not segs:
        return []
    board_slug = doc.get('board_slug') or entry['board_slug']
    date = doc.get('meeting_date') or entry['date']
    vid = doc.get('video_id') or entry['video_id']
    video_url = doc.get('video_url') or 'https://www.youtube.com/watch?v=%s' % vid
    board = board_slug.replace('-', ' ').title()

    out = []
    i, n, ordinal = 0, len(segs), 0
    while i < n:
        start = float(segs[i].get('start') or 0.0)
        parts, offsets, j = [], [], i
        pos = 0
        while j < n and float(segs[j].get('start') or 0.0) < start + CHUNK_SECONDS:
            text = (segs[j].get('text') or '').replace('\n', ' ')
            offsets.append([pos, int(float(segs[j].get('start') or 0.0))])
            parts.append(text)
            pos += len(text) + 1
            j += 1
        if j == i:                      # a single segment longer than the window
            j = i + 1
        body = ' '.join(parts)
        if body.strip():
            out.append(({
                'corpus': 'transcript',
                'doc_key': '%s#%d' % (vid, ordinal),
                'file_key': entry['file_key'],
                'board': board,
                'board_slug': board_slug,
                'date': date,
                'kind': 'recording',
                'cite_url': '%s&t=%ds' % (video_url, int(start)),
                'source_url': video_url,
                'start_s': int(start),
                'end_s': int(float(segs[j - 1].get('start') or 0.0)
                              + float(segs[j - 1].get('duration') or 0.0)),
                'seg_starts': json.dumps(offsets, separators=(',', ':')),
                'chars': len(body),
            }, body))
            ordinal += 1
        # ONE SEGMENT OF OVERLAP. Without it, `"class size"` spoken across the boundary
        # is in neither row, which is a silent miss and the worst kind.
        i = max(j - 1, i + 1)
    return out


# ------------------------------------------------------------------------------- the build

DOC_COLS = ['corpus', 'doc_key', 'file_key', 'board', 'board_slug', 'date', 'kind',
            'cite_url', 'source_url', 'start_s', 'end_s', 'seg_starts', 'chars']


def connect(path, create):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    if create:
        db.executescript(SCHEMA)
        db.execute('CREATE VIRTUAL TABLE fts USING fts5(body, tokenize=%r)' % TOKENIZE)
    return db


def wanted():
    """Every file that belongs in the index, with its hash. Both corpora."""
    out = {}
    for e in document_files() + transcript_files():
        e['sha256'] = sha256_of(e['file'])
        out[e['file_key']] = e
    if not out:
        raise SystemExit('no text files found at all. Refusing to write an empty index: '
                         'an empty index and an unsearchable archive read alike.')
    return out


def have(db):
    return {r['file_key']: dict(r) for r in db.execute('SELECT * FROM indexed_file')}


def drift(db):
    """(added, changed, removed) between what is on disk and what is in the index."""
    w, h = wanted(), have(db)
    added = [k for k in w if k not in h]
    changed = [k for k in w if k in h and w[k]['sha256'] != h[k]['sha256']]
    removed = [k for k in h if k not in w]
    return w, h, added, changed, removed


def index_file(db, entry):
    rows = (transcript_rows if entry['corpus'] == 'transcript' else document_rows)(entry)
    for row, body in rows:
        cur = db.execute('INSERT INTO doc (%s) VALUES (%s)'
                         % (','.join(DOC_COLS), ','.join('?' * len(DOC_COLS))),
                         [row.get(c) for c in DOC_COLS])
        db.execute('INSERT INTO fts (rowid, body) VALUES (?,?)', (cur.lastrowid, body))
    db.execute('INSERT OR REPLACE INTO indexed_file VALUES (?,?,?,?,?)',
               (entry['file_key'], entry['corpus'], entry['sha256'],
                os.path.getsize(entry['file']), len(rows)))
    return len(rows)


def forget(db, file_key):
    for r in db.execute('SELECT rowid FROM doc WHERE file_key=?', (file_key,)).fetchall():
        db.execute('DELETE FROM fts WHERE rowid=?', (r['rowid'],))
    db.execute('DELETE FROM doc WHERE file_key=?', (file_key,))
    db.execute('DELETE FROM indexed_file WHERE file_key=?', (file_key,))


def build(rebuild=False, quiet=False):
    fresh = rebuild or not os.path.exists(DB)
    if rebuild and os.path.exists(DB):
        os.remove(DB)
    db = connect(DB, create=fresh)
    if fresh:
        w = wanted()
        added, changed, removed, h = list(w), [], [], {}
    else:
        w, h, added, changed, removed = drift(db)

    for k in removed:
        forget(db, k)
    for k in changed:
        forget(db, k)
    n = 0
    for k in added + changed:
        n += index_file(db, w[k])
    db.execute('INSERT OR REPLACE INTO build_meta VALUES (?,?)', ('tokenize', TOKENIZE))
    db.execute('INSERT OR REPLACE INTO build_meta VALUES (?,?)',
               ('chunk_seconds', str(CHUNK_SECONDS)))
    db.commit()
    if added or changed or removed:
        db.execute("INSERT INTO fts(fts) VALUES('optimize')")
        db.commit()
    if not quiet:
        print('%s %s: +%d file(s), %d changed, %d removed, %d row(s) written'
              % ('rebuilt' if fresh else 'refreshed', rel(DB),
                 len(added), len(changed), len(removed), n))
    return db


# ------------------------------------------------------------------------------ reporting

def counts(db):
    out = {}
    for r in db.execute('SELECT corpus, COUNT(*) n FROM indexed_file GROUP BY corpus'):
        out[r['corpus'] + '_files'] = r['n']
    for r in db.execute('SELECT corpus, COUNT(*) n FROM doc GROUP BY corpus'):
        out[r['corpus'] + '_rows'] = r['n']
    for k in ('document_files', 'transcript_files', 'document_rows', 'transcript_rows'):
        out.setdefault(k, 0)
    return out


def reconcile(db):
    """The index's own counts, against the two registries that state them independently.

    A join that matches nothing looks exactly like data that is absent, so this asserts
    the numbers rather than reporting them. Both sides are read fresh: the transcript
    index is being appended to while this runs.
    """
    problems = []
    c = counts(db)

    # A published document is one indexed ROW, so the row count is the count of documents
    # that hold something a search can match -- which is exactly what
    # `minutes-searchable.csv` measures, by a route that shares no code with this one.
    # The FILE count is larger and is meant to be: the extractor opens every scan too.
    if os.path.exists(SEARCHABLE):
        rows = list(csv.DictReader(open(SEARCHABLE, encoding='utf-8')))
        searchable = sum(int(r['searchable']) for r in rows)
        if c['document_rows'] != searchable:
            problems.append(
                'the index holds %d searchable town document(s); minutes-searchable.csv '
                'counts %d. A document that can be grepped and is not in the index is a '
                'silently smaller archive.' % (c['document_rows'], searchable))
    else:
        problems.append('sources/data/minutes-searchable.csv is absent, so the document '
                        'count reconciles against nothing. Run '
                        'scripts/build_minutes_searchable.py.')

    listed = 0
    if os.path.exists(TRANSCRIPT_INDEX):
        for r in csv.DictReader(open(TRANSCRIPT_INDEX, encoding='utf-8')):
            if os.path.exists(os.path.join(ROOT, r['path'])):
                listed += 1
    if c['transcript_files'] != listed:
        problems.append(
            'the index holds captions for %d meeting(s); '
            'youtube-transcript-index.csv lists %d whose file is on disk.'
            % (c['transcript_files'], listed))
    return c, problems


def status(db):
    c, problems = reconcile(db)
    w, h, added, changed, removed = drift(db)
    print('%s' % rel(DB))
    print('  tokenizer               %s' % TOKENIZE)
    print('  town documents          %6d file(s) opened, %6d searchable and indexed'
          % (c['document_files'], c['document_rows']))
    print('  our transcripts         %6d meeting(s), %6d indexed row(s) of ~%ds each'
          % (c['transcript_files'], c['transcript_rows'], CHUNK_SECONDS))
    print('  on disk, not indexed    %6d' % len(added))
    print('  indexed, since changed  %6d' % len(changed))
    print('  indexed, now gone       %6d' % len(removed))
    for p in problems:
        print('  RECONCILIATION: %s' % p)
    return 0 if not problems and not (added or changed or removed) else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--rebuild', action='store_true', help='from scratch')
    ap.add_argument('--check', action='store_true',
                    help='fail if the index has drifted from the text, or does not '
                         'reconcile against the two registries')
    ap.add_argument('--status', action='store_true')
    a = ap.parse_args()

    if a.check:
        if not os.path.exists(DB):
            print('STALE — %s has never been built. '
                  'Run scripts/build_minutes_fts.py' % rel(DB))
            return 1
        db = connect(DB, create=False)
        w, h, added, changed, removed = drift(db)
        c, problems = reconcile(db)
        if added or changed or removed:
            print('STALE — the index no longer matches the text on disk: '
                  '%d file(s) not indexed, %d changed since indexing, %d indexed and now '
                  'gone. Run scripts/build_minutes_fts.py'
                  % (len(added), len(changed), len(removed)))
            for k in (added + changed + removed)[:6]:
                print('    %s' % k)
            return 1
        if problems:
            print('FAILED — the index does not reconcile against the registries:')
            for p in problems:
                print('  %s' % p)
            return 1
        print('ok — %d searchable town document(s) and %d transcript(s) indexed as %d '
              'row(s); every sha256 matches'
              % (c['document_rows'], c['transcript_files'],
                 c['document_rows'] + c['transcript_rows']))
        return 0

    if a.status:
        if not os.path.exists(DB):
            print('%s has never been built.' % rel(DB))
            return 1
        return status(connect(DB, create=False))

    db = build(rebuild=a.rebuild)
    return status(db) and 0        # report, but a growing corpus is not a build failure


if __name__ == '__main__':
    sys.exit(main())
