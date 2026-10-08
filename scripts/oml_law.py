#!/usr/bin/env python3
"""THE OPEN MEETING LAW CORPUS: what `fetch_open_meeting_law.py` holds, read back as text.

One place for three things two tools need -- `search_minutes.py --corpus law` and
`oml_review.py` -- so they cannot disagree about what the law corpus is:

  * `documents()`  every held document: id, label, publisher URL, our copy, its text;
  * `passages()`   the text cut into paragraphs, each tagged with WHERE it sits -- the
                   statute's section, the regulation's 29.xx heading, the guide's page --
                   because a quotation of a law with no section is not a citation;
  * `verbatim()`   is a quotation really in a document, compared the way this repo compares
                   quotes (whitespace-insensitive, curly quotes straightened, case-folded).

The text is OUR extraction of the publisher's file. The file, at its publisher URL, is the
source; a passage here locates it.
"""
import csv
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'sources', 'state-law', 'index.csv')
SITE = 'https://lunenburgbudgetproject.org'
PAGE = re.compile(r'^===PAGE (\d+)===$')
STRAIGHT = str.maketrans({'’': "'", '‘': "'", '“': '"', '”': '"',
                          '–': '-', '—': '-', ' ': ' ', '­': ''})


def documents():
    if not os.path.exists(INDEX):
        return []
    out = []
    with open(INDEX, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            p = os.path.join(ROOT, r['text'])
            r['body'] = open(p, encoding='utf-8').read() if os.path.exists(p) else ''
            r['our_copy'] = SITE + '/docs/' + r['local'][len('sources/'):]
            out.append(r)
    return out


def _where(doc_id, line, cur):
    """The citation a passage inherits from the nearest heading above it."""
    s = line.strip()
    m = re.match(r'^Section (\d+)\.', s) or re.match(r'^Section (\d+):', s)
    if m and doc_id.startswith('c30a'):
        return 'G.L. c.30A, §%s' % m.group(1)
    m = re.match(r'^(29\.\d\d):\s*\S', s)
    if m and doc_id == '940-cmr-29':
        return '940 CMR %s' % m.group(1)
    return cur


def passages(docs=None):
    """[{doc, where, page, text}] -- paragraphs, blank-line separated, page-tagged."""
    out = []
    for d in docs if docs is not None else documents():
        where, page, buf = '', None, []

        def flush():
            t = ' '.join(' '.join(buf).split())
            if len(t) >= 20:
                out.append({'doc': d, 'where': where, 'page': page, 'text': t})
            buf.clear()
        default = {'c30a-18': 'G.L. c.30A, §18', 'c30a-19': 'G.L. c.30A, §19',
                   'c30a-20': 'G.L. c.30A, §20', 'c30a-21': 'G.L. c.30A, §21',
                   'c30a-22': 'G.L. c.30A, §22', 'c30a-23': 'G.L. c.30A, §23',
                   'c30a-24': 'G.L. c.30A, §24', 'c30a-25': 'G.L. c.30A, §25'}.get(d['id'], '')
        where = default
        for line in d['body'].splitlines():
            m = PAGE.match(line)
            if m:
                flush()
                page = int(m.group(1))
                continue
            if not line.strip():
                flush()
                continue
            nw = _where(d['id'], line, where)
            if nw != where:
                flush()
                where = nw
            buf.append(line.strip())
        flush()
    return out


def squash(s):
    return re.sub(r'\s+', '', (s or '').translate(STRAIGHT)).lower()


_SQ = {}


def verbatim(quote, doc_ids=None, docs=None):
    """The first document (id) whose text holds `quote` verbatim, or None.

    Whitespace is ignored because a PDF breaks lines mid-sentence and a model quoting it
    does not; that is the only liberty. A quotation of fewer than 20 characters proves
    nothing and is refused."""
    q = squash(quote)
    if len(q) < 20:
        return None
    for d in docs if docs is not None else documents():
        if doc_ids and d['id'] not in doc_ids:
            continue
        if d['id'] not in _SQ:
            _SQ[d['id']] = squash(d['body'].replace('-\n', '-\n'))
            _SQ[d['id']] = re.sub(r'===page\d+===', '', _SQ[d['id']])
        if q in _SQ[d['id']]:
            return d['id']
    return None


def search(term, limit=25):
    """FTS5 over the passages, in memory: porter-stemmed, phrases and NEAR, BM25-ranked.

    In memory because the corpus is ~20 documents and ~330 KB: an index FILE would be one
    more derived thing that can go stale, for no speed anybody would notice."""
    import sqlite3
    ps = passages()
    db = sqlite3.connect(':memory:')
    db.execute("CREATE VIRTUAL TABLE p USING fts5(text, tokenize='porter unicode61')")
    db.executemany('INSERT INTO p(rowid, text) VALUES (?, ?)', [(i, p['text']) for i, p in enumerate(ps)])
    rows = db.execute("SELECT rowid, highlight(p, 0, '\x02', '\x03') FROM p WHERE p MATCH ? "
                      "ORDER BY bm25(p) LIMIT ?", (term, limit)).fetchall()
    return ps, [(ps[i], marked) for i, marked in rows]
