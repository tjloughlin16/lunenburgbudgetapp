#!/usr/bin/env python3
"""Search the meeting archive, and always say how much of it was searched.

    python3 scripts/search_minutes.py "jersey"
    python3 scripts/search_minutes.py "para" --board school-committee --since 2025-07-01
    python3 scripts/search_minutes.py '"class size"'      # a phrase
    python3 scripts/search_minutes.py 'NEAR(budget cut)'  # words near each other

WHY THIS EXISTS RATHER THAN A GREP

Two reasons, and the second is the point.

**It collapses the work.** Finding what a board said takes a grep, then a mapping from
filename to board and date, then a lookup of each document's citable URL. That is eight or
so steps, done slightly differently every time, and the URL step is the one that gets
skipped -- which is how a quotation ends up in an analysis with no address.

**It makes the caveat impossible to omit.** A grep that finds nothing prints nothing, and
"nothing" reads as "nobody said it". It is not: it means nobody said it *in the documents
that can be read*. Those were different numbers for a long time -- 39 documents the town
published as Word files were absent from the archive entirely, including School Committee
minutes from the middle of a fiscal year under analysis, and nothing anywhere said so. An
agent that grepped and found nothing would have written "no vote in the archive names this
account" when the honest sentence was "no vote in the 1,383 documents that can be read".

The general name for that is **coverage bias**, and the only fix is to report the
denominator every time, whether or not it is convenient. So this prints coverage on every
run, including runs with no hits -- especially those, since that is when it matters.

**AND THE DENOMINATOR HAS BEEN WRONG TWICE.** The first time it compared what we hold
against what we hold and called the result what the town published; `minutes-coverage.csv`
fixed that. The second time it counted a document as searched because a `.txt` file
existed beside it -- and a `.txt` file exists for every scan the extractor opened, holding
nothing but the `===PAGE n===` markers the extractor itself wrote. A quarter of the archive
was being reported as searched while contributing not one character a grep could match.

So the line now counts a document as searched only if its extract holds a non-whitespace
character once our own page markers are removed. The threshold is zero rather than a
number somebody chose; `build_minutes_searchable.py` documents why, and diagnoses each
unsearchable document from the file's own structure.

**The caveat is scoped to the search you ran.** An archive-wide figure printed under a
board-level search understates that board: the Board of Assessors is far worse than the
archive, and a reader who filtered to it deserves ITS number, not the average.

This is the same discipline as `extract_munis_report.py`, which refuses to write when its
extract does not tie to the report's own printed total. A number without its denominator is
not a smaller answer; it is a different and wrong one.

--------------------------------------------------------------------------------------
AND A THIRD TIME, IN A NEW WAY: THE MEETINGS WITH NO DOCUMENT AT ALL
--------------------------------------------------------------------------------------

`sources/data/meeting-register.csv` counts **231 meetings whose only surviving record is a
recording** -- no agenda, no minutes, nothing filed -- and **162 of those are School
Committee**. This tool could not see one of them. Every search over that period reported
"nobody said it" about meetings it had never had any way to read, and the coverage line
above did not mention them, because it counted DOCUMENTS out of DOCUMENTS.

Machine captions now exist for some of those meetings and this searches them. But a
caption is not minutes and the two must never be handed back interchangeably, so:

  * a transcript hit is **labelled a transcript** in every line it appears on;
  * it is **cited as the video at its timestamp**, never as a document, because that is
    the only address at which anybody can check it;
  * transcripts get **their own denominator**. Merging them into the document coverage
    line would silently change what that sentence means, which is precisely the defect
    that has already happened twice above.

A caption model hears *fifteen hundred*, *$1,500* and *$50* alike, and it mangles names. A
transcript search locates a MOMENT. It cannot settle what was said, what a figure was, or
who said it -- for that, watch the moment, or ask the town for the record of it.

--------------------------------------------------------------------------------------
HOW IT SEARCHES, AND WHAT THE INDEX COSTS
--------------------------------------------------------------------------------------

`scripts/build_minutes_fts.py` keeps an FTS5 index over both corpora and this uses it when
it is there. That is not only speed. A grep does not know what a word is:

    ELL    matched 3,049 documents through *well*, *shell*, *sell*.   The truth is 2.
    ESSER  matched 125 through *lesser* and *assessor*.               The truth is 34.
    Latin  matched 140 through *relating*.                            The truth is 5.

The index is stemmed with `porter`, so `budget` also finds *budgets* and *budgeting*. That
is usually wanted and it is never hidden: each hit prints the SURFACE FORMS that actually
matched and says whether your own word was among them.

**Staleness is the risk an index adds**, and it is the shape of nearly every defect in this
repo. So the manifest is re-read on every run, the state of the index is printed on every
run, and any in-scope file that is missing from the index or has changed since it was
indexed is **grepped directly** and reported as such -- an index that has fallen behind
makes this slower, never quieter.
"""
import argparse
import csv
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN = os.path.join(ROOT, 'sources', 'meetings')
TEXT = os.path.join(MIN, 'text')
DATASET = os.path.join(ROOT, 'sources', 'data', 'minutes-searchable.csv')
REGISTER = os.path.join(ROOT, 'sources', 'data', 'meeting-register.csv')
TRANSCRIPT_INDEX = os.path.join(ROOT, 'sources', 'data', 'youtube-transcript-index.csv')
FTS_DB = os.path.join(ROOT, 'sources', 'data', 'minutes-fts.db')
SITE = 'https://lunenburgbudgetproject.org'

# Written by scripts/extract_minutes.py, so they are OURS and not the document's. Counting
# them as text is the defect this file's docstring describes.
PAGE_MARKER = re.compile(r'^===PAGE \d+===$', re.M)

# FTS5's highlight() wraps matched tokens. Control characters, so nothing in a document
# can be mistaken for one.
MARK_A, MARK_B = '\x02', '\x03'
MARKED = re.compile(MARK_A + '(.*?)' + MARK_B, re.S)

# Two caption matches closer together than this are one passage, not two moments. Segments
# run about three seconds, so a phrase repeated across a sentence otherwise reports three
# times.
MOMENT_GAP = 25

# What makes a term a REGEX rather than a word. If any of these is present the FTS route
# cannot honour the query and this says so and greps instead, rather than quietly
# answering a different question.
REGEXY = re.compile(r'[\\\[\]^$|+?{}]|\.\*|\.\+')

# FTS5's own query syntax. If the caller used it, pass it through untouched.
FTS_SYNTAX = re.compile(r'["():*]|\b(?:AND|OR|NOT|NEAR)\b')

# THE WARNING, in one place, because it is printed wherever a caption is.
CAPTION_CAVEAT = (
    'MACHINE CAPTIONS, NOT A RECORD. A caption model hears "fifteen hundred", "$1,500"\n'
    '  and "$50" alike, and it mangles names. A hit LOCATES A MOMENT: open the video at\n'
    '  the timestamp and check it there. No figure, name or vote may be quoted from these\n'
    '  lines as though the meeting said it.')


# --------------------------------------------------------------------- the town's documents

def index():
    """Every document the town published, with what we can actually do with each.

    Three states, not two:
      `_held`       we have the file at all
      `_has_text`   the extractor produced a .txt for it
      `_searchable` that .txt holds something a grep could match
    """
    rows = list(csv.DictReader(open(os.path.join(MIN, 'index.csv'))))
    if not rows:
        raise SystemExit('sources/meetings/index.csv parsed to zero rows.')
    for r in rows:
        path = (r.get('path') or '').strip()
        stem = os.path.splitext(path)[0] if path else ''
        r['_stem'] = stem
        r['_src'] = os.path.join(MIN, path) if path else ''
        r['_txt'] = os.path.join(TEXT, stem + '.txt') if stem else ''
        r['_key'] = os.path.relpath(r['_txt'], ROOT).replace(os.sep, '/') if stem else ''
        r['_held'] = bool(r['_src']) and os.path.exists(r['_src'])
        r['_has_text'] = bool(r['_txt']) and os.path.exists(r['_txt'])
        r['_body'] = None
        r['_searchable'] = False
    return rows


def body_of(r):
    """The searchable body, read once and cached on the row."""
    if r['_body'] is None:
        raw = open(r['_txt'], errors='replace').read()
        r['_body'] = PAGE_MARKER.sub('', raw)
        r['_searchable'] = bool(r['_body'].strip())
    return r['_body']


def archive_wide():
    """The whole-archive picture, read from the generated dataset rather than recomputed.

    Rule 2: nothing here is typed. If the dataset is absent the line says so rather than
    quoting a number nobody can check.
    """
    if not os.path.exists(DATASET):
        return None
    rows = list(csv.DictReader(open(DATASET, encoding='utf-8')))
    if not rows:
        return None
    keys = ['listed', 'held', 'searchable', 'unsearchable', 'image_scan',
            'vector_outlines', 'blank', 'extract_failed', 'unreadable', 'not_fetched']
    return {k: sum(int(r[k]) for r in rows) for k in keys}


# ------------------------------------------------------------------------- the transcripts

def transcript_scope(board, since, until):
    """What a caption search could POSSIBLY cover, and what it does -- scoped to the run.

    Read fresh from the register and from the transcript index on every call. The index is
    being appended to by a backfill as this is written; a count cached anywhere would be
    wrong within the minute.
    """
    if not os.path.exists(REGISTER):
        return None
    rows = list(csv.DictReader(open(REGISTER, encoding='utf-8')))
    if not rows:
        return None
    if board:
        frag = board.lower()
        rows = [r for r in rows if frag in (r['board_slug'] or '').lower()]
    if since:
        rows = [r for r in rows if r['date'] >= since]
    if until:
        rows = [r for r in rows if r['date'] <= until]

    fetched = set()
    if os.path.exists(TRANSCRIPT_INDEX):
        for t in csv.DictReader(open(TRANSCRIPT_INDEX, encoding='utf-8')):
            if os.path.exists(os.path.join(ROOT, t['path'])):
                fetched.add(t['video_id'])

    recorded = [r for r in rows if r.get('video') == '1']
    have = [r for r in recorded if set((r.get('video_ids') or '').split()) & fetched]
    only = [r for r in recorded if r.get('evidence') == 'video only']
    only_have = [r for r in only if set((r.get('video_ids') or '').split()) & fetched]

    # A MEETING OCCASION AND A RECORDING ARE NOT THE SAME COUNT, and conflating them is a
    # mistake this project has already made and fixed once: a joint meeting is a row under
    # every board that sat in it, so summing the rows counts one recording three times.
    # The meeting counts above are the right grain for "what could this search have
    # covered"; these are the right grain for "how many files are there". Both are
    # printed, and neither is used as the other.
    ids = set()
    for r in recorded:
        ids |= set((r.get('video_ids') or '').split())
    return {'meetings': len(rows), 'recorded': len(recorded), 'transcribed': len(have),
            'video_only': len(only), 'video_only_transcribed': len(only_have),
            'recordings': len(ids), 'recordings_transcribed': len(ids & fetched)}


# ------------------------------------------------------------------------------- the index

def open_index():
    """(connection, note). `note` is why there is no connection, if there is not."""
    if not os.path.exists(FTS_DB):
        return None, ('sources/data/minutes-fts.db has never been built '
                      '(scripts/build_minutes_fts.py)')
    try:
        db = sqlite3.connect('file:%s?mode=ro' % FTS_DB, uri=True)
        db.row_factory = sqlite3.Row
        db.execute('SELECT 1 FROM doc LIMIT 1').fetchone()
        return db, None
    except sqlite3.Error as e:
        return None, 'sources/data/minutes-fts.db will not open (%s)' % e


def fts_query(term):
    """The caller's term as an FTS5 MATCH expression, without changing what they asked.

    A bare word or two is quoted term by term, which is what stops an apostrophe or a
    hyphen being read as syntax. Anything that already uses FTS5's own operators -- a
    quoted phrase, NEAR, AND/OR/NOT, a `*` prefix -- is passed through untouched.
    """
    if FTS_SYNTAX.search(term):
        return term
    words = [w for w in re.split(r'\s+', term.strip()) if w]
    return ' AND '.join('"%s"' % w.replace('"', '""') for w in words)


def query_words(term):
    """The caller's own words, for deciding whether a hit is exact or a stemmed variant."""
    return {w.lower() for w in re.findall(r"[\w']+", term)
            if w.upper() not in ('AND', 'OR', 'NOT', 'NEAR')}


def marks(marked):
    """[(original offset, surface form)] for every token FTS5 says matched."""
    out, shrink = [], 0
    for m in MARKED.finditer(marked):
        out.append((m.start() - shrink, m.group(1)))
        shrink += 2
    return out


def unmark(s):
    return s.replace(MARK_A, '').replace(MARK_B, '')


def context_at(body, offset, width, length):
    lo = max(0, offset - width)
    return ' '.join(body[lo:offset + length + width].split())


def seconds_at(seg_starts, offset):
    """Which segment of the chunk this offset falls in -- so the citation is the moment."""
    best = None
    for char_off, secs in seg_starts:
        if char_off <= offset:
            best = secs
        else:
            break
    return best


def hhmmss(s):
    return '%d:%02d:%02d' % (s // 3600, (s % 3600) // 60, s % 60)


# -------------------------------------------------------------------------------- printing

def label_forms(forms, words):
    """`exact`, or the variants the stemmer reached. Never silent about the difference.

    Compared WORD BY WORD, because FTS5's highlight() merges adjacent matched tokens into
    one span: a phrase search for `"study hall"` comes back as the single surface form
    `study hall`, which is not in the caller's word set and would be reported as a stemmed
    variant of itself.
    """
    lower = {f.lower() for f in forms}
    exact = sorted(f for f in lower
                   if set(re.findall(r"[\w']+", f)) <= words)
    variant = sorted(lower - set(exact))
    if exact and not variant:
        return 'exact: ' + ', '.join(exact)
    if exact:
        return 'exact: %s; also stemmed to %s' % (', '.join(exact), ', '.join(variant))
    return 'STEMMED VARIANTS ONLY: ' + ', '.join(variant)


def print_document_hit(r, n, forms, contexts, words):
    print('\n[town document] %s — %s %s  (%d hit%s)'
          % (r['board'], r['date'], r['kind'], n, 's' if n > 1 else ''))
    print('  matched: %s' % label_forms(forms, words))
    print('  cite: %s/docs/minutes/text/%s.txt' % (SITE, r['doc_key']))
    if r['source_url']:
        print('  town: %s' % r['source_url'])
    for c in contexts:
        print('   ... ' + c)


def print_transcript_hit(meta, moments, forms, words, first):
    # The full caveat once per run, at the top of the captions; the LABEL on every hit.
    # A warning repeated after every result is a warning people learn to skip, and the
    # thing that must never be skipped is which corpus a line came out of.
    if first:
        print('\n  ' + CAPTION_CAVEAT)
    print('\n[TRANSCRIPT — our machine captions, NOT a record] %s — %s  (%d moment%s)'
          % (meta['board'], meta['date'], len(moments), 's' if len(moments) > 1 else ''))
    print('  matched: %s' % label_forms(forms, words))
    for secs, cite, ctx in moments:
        print('  cite: %s   [%s into the recording]' % (cite, hhmmss(secs)))
        print('   ... ' + ctx)


# --------------------------------------------------------------------------- the two routes

def search_fts(db, expr, corpus, scope_keys, board, since, until, context, limit):
    """Everything matching, ranked by BM25. Filtered in SQL, so nothing large is read."""
    sql = ["SELECT d.rowid, d.corpus, d.doc_key, d.file_key, d.board, d.date, d.kind,",
           "       d.cite_url, d.source_url, d.start_s, d.seg_starts,",
           "       highlight(fts, 0, ?, ?) AS marked, bm25(fts) AS rank",
           "  FROM fts JOIN doc d ON d.rowid = fts.rowid",
           " WHERE fts MATCH ? AND d.corpus = ?"]
    args = [MARK_A, MARK_B, expr, corpus]
    if board:
        sql.append(' AND lower(d.board_slug) LIKE ?')
        args.append('%' + board.lower() + '%')
    if since:
        sql.append(' AND d.date >= ?')
        args.append(since)
    if until:
        sql.append(' AND d.date <= ?')
        args.append(until)
    sql.append(' ORDER BY rank')
    rows = db.execute('\n'.join(sql), args).fetchall()
    if scope_keys is not None:
        rows = [r for r in rows if r['file_key'] in scope_keys]
    return rows


def grep_transcripts(board, since, until, pat, context):
    """The captions, grepped. Slower and dumber than the index, and NOT optional.

    A regex term cannot go to FTS5, and the first version of this simply reported the
    captions as unsearched when one arrived. That is the defect this whole file is about,
    wearing a new hat: a search that silently covers less than the reader thinks. So the
    fallback covers both corpora or neither.
    """
    if not os.path.exists(TRANSCRIPT_INDEX):
        return []
    out = []
    for t in csv.DictReader(open(TRANSCRIPT_INDEX, encoding='utf-8')):
        if board and board.lower() not in (t['board_slug'] or '').lower():
            continue
        if since and t['meeting_date'] < since:
            continue
        if until and t['meeting_date'] > until:
            continue
        path = os.path.join(ROOT, t['path'])
        if not os.path.exists(path):
            continue
        doc = json.load(open(path, encoding='utf-8'))
        segs = doc.get('segments') or []
        body, offsets = [], []
        pos = 0
        for sg in segs:
            text = (sg.get('text') or '').replace('\n', ' ')
            offsets.append([pos, int(float(sg.get('start') or 0))])
            body.append(text)
            pos += len(text) + 1
        body = ' '.join(body)
        found = list(pat.finditer(body))
        if not found:
            continue
        video = doc.get('video_url') or ('https://www.youtube.com/watch?v=%s'
                                         % t['video_id'])
        moments, forms, last = {}, set(), None
        for m in found:
            secs = seconds_at(offsets, m.start()) or 0
            forms.add(m.group(0))
            if secs in moments:
                continue
            moments[secs] = ('%s&t=%ds' % (video, secs),
                             context_at(body, m.start(), context, len(m.group(0))))
        out.append({'board': (t['board_slug'] or '').replace('-', ' ').title(),
                    'date': t['meeting_date'], 'moments': moments, 'forms': forms})
    return sorted(out, key=lambda m: m['date'], reverse=True)


def grep_rows(rows, pat, context, limit):
    """The route this tool has always had. Used when the index cannot answer."""
    out = []
    for r in rows:
        if not r['_has_text']:
            continue
        body = body_of(r)
        found = list(pat.finditer(body))
        if not found:
            continue
        out.append((r, [(m.group(0), context_at(body, m.start(), context,
                                                len(m.group(0)))) for m in found[:limit]],
                    len(found)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('term', help='a word, a "quoted phrase", NEAR(a b); a regex forces '
                                 'the grep route')
    ap.add_argument('--board', help='slug fragment, e.g. school-committee')
    ap.add_argument('--since', help='ISO date; only documents on or after it')
    ap.add_argument('--until', help='ISO date; only documents on or before it')
    ap.add_argument('--context', type=int, default=140, help='characters either side')
    ap.add_argument('--list-unsearchable', action='store_true',
                    help='print every in-scope document that cannot be searched')
    # The default INCLUDES transcripts. Excluding them silently is the bug this tool had:
    # a search over a meeting with no minutes reported "nobody said it" while 131 minutes
    # of caption for that same meeting sat unread. They are labelled everywhere they
    # appear, so including them cannot be mistaken for quoting them.
    ap.add_argument('--transcripts', dest='transcripts', action='store_true',
                    default=True, help='search our machine captions too (the default)')
    ap.add_argument('--no-transcripts', dest='transcripts', action='store_false',
                    help='town-published documents only')
    ap.add_argument('--grep', action='store_true',
                    help='force the grep route even if the index is available')
    ap.add_argument('--order', choices=('rank', 'date'), default='rank',
                    help='BM25 relevance (default) or chronological')
    a = ap.parse_args()

    rows = index()

    # The SCOPE is every document the filters select, whether or not we can read it. That
    # is the only denominator a reader of these results cares about: a board-level search
    # is compromised by that board's scans, not by the archive's average.
    scope = rows
    if a.board:
        scope = [r for r in scope
                 if a.board.lower() in (r['_stem'] or r['board']).lower().replace(' ', '-')]
    if a.since:
        scope = [r for r in scope if r['date'] >= a.since]
    if a.until:
        scope = [r for r in scope if r['date'] <= a.until]
    by_key = {r['_key']: r for r in scope if r['_key']}

    words = query_words(a.term)
    db, why_no_index = open_index()

    # WHY THE ROUTE WAS CHOSEN, always stated. A tool that silently falls back to a
    # different algorithm is answering a different question without saying so.
    route, route_note = 'fts', ''
    if a.grep:
        route, route_note = 'grep', 'you asked for it (--grep)'
    elif db is None:
        route, route_note = 'grep', why_no_index
    elif REGEXY.search(a.term):
        route, route_note = 'grep', ('the term is a regular expression, which the index '
                                     'cannot honour')

    # Which in-scope files the index actually holds, and which have moved underneath it.
    indexed, stale = set(), []
    if db is not None:
        # SEARCHABLE means the index holds a ROW for it. A file the extractor opened and
        # got nothing out of has an `indexed_file` entry and no `doc` row, and it must not
        # be counted as searched -- that is the defect this tool's docstring describes,
        # arriving by a new route.
        indexed = {r[0] for r in db.execute(
            "SELECT DISTINCT file_key FROM doc WHERE corpus='document'")}
        # Cheap staleness: a file whose size has changed, or that the index has never
        # seen. A full re-hash belongs in `build_minutes_fts.py --check`; here the point
        # is to notice and GREP the difference, not to certify the whole index.
        sizes = {r[0]: r[1] for r in db.execute(
            "SELECT file_key, bytes FROM indexed_file WHERE corpus='document'")}
        for k, r in by_key.items():
            if not r['_has_text']:
                continue
            if k not in sizes or os.path.getsize(r['_txt']) != sizes[k]:
                stale.append(k)

    hit_docs = 0
    doc_forms_seen = set()

    if route == 'fts':
        expr = fts_query(a.term)
        try:
            found = search_fts(db, expr, 'document', set(by_key), a.board, a.since,
                               a.until, a.context, 3)
        except sqlite3.OperationalError as e:
            print('the index refused that query (%s). Falling back to the grep route.' % e)
            route, route_note, found = 'grep', 'the index refused the query: %s' % e, []
    if route == 'fts':
        if a.order == 'date':
            found = sorted(found, key=lambda r: (r['date'], r['board']))
        for r in found:
            body = unmark(r['marked'])
            ms = marks(r['marked'])
            forms = {f for _, f in ms}
            doc_forms_seen |= {f.lower() for f in forms}
            src = by_key.get(r['file_key'])
            hit_docs += 1
            print_document_hit(
                {'board': (src or r)['board'], 'date': r['date'], 'kind': r['kind'],
                 'doc_key': r['doc_key'], 'source_url': r['source_url']},
                len(ms), forms,
                [context_at(body, off, a.context, len(f)) for off, f in ms[:3]], words)
        # ...and anything the index has not caught up with, grepped directly rather than
        # dropped. An index that has fallen behind makes this slower, never quieter.
        if stale:
            pat = re.compile(re.escape(a.term), re.I)
            for r, cs, n in grep_rows([by_key[k] for k in stale], pat, a.context, 3):
                hit_docs += 1
                print_document_hit(
                    {'board': r['board'], 'date': r['date'], 'kind': r['kind'],
                     'doc_key': r['_stem'], 'source_url': r['url']},
                    n, {c[0] for c in cs}, [c[1] for c in cs], words)
                print('  (grepped directly: this file is not in the index, or has changed '
                      'since it was)')
    else:
        pat = re.compile(a.term, re.I)
        got = grep_rows(sorted(scope, key=lambda r: (r['date'], r['board'])),
                        pat, a.context, 3)
        for r, cs, n in got:
            hit_docs += 1
            doc_forms_seen |= {c[0].lower() for c in cs}
            print_document_hit(
                {'board': r['board'], 'date': r['date'], 'kind': r['kind'],
                 'doc_key': r['_stem'], 'source_url': r['url']},
                n, {c[0] for c in cs}, [c[1] for c in cs], words)

    # ------------------------------------------------------------------ the captions
    hit_meetings = 0
    tr_note = ''
    if a.transcripts:
        if route == 'grep':
            # Same term, same corpus discipline, slower route.
            pat = re.compile(a.term, re.I)
            per = {m['date'] + m['board']: m for m in
                   grep_transcripts(a.board, a.since, a.until, pat, a.context)}
            for meta in sorted(per.values(), key=lambda m: m['date'], reverse=True):
                hit_meetings += 1
                moments, last = [], None
                for secs, (cite, ctx) in sorted(meta['moments'].items()):
                    if last is not None and secs - last < MOMENT_GAP:
                        continue
                    last = secs
                    moments.append((secs, cite, ctx))
                print_transcript_hit(meta, moments[:3], meta['forms'], words,
                                     hit_meetings == 1)
            tr_note = ('grepped, not indexed — a substring match, because %s'
                       % (route_note or 'the index was not used'))
        elif db is not None:
            expr = fts_query(a.term)
            try:
                trows = search_fts(db, expr, 'transcript', None, a.board, a.since,
                                   a.until, a.context, 3)
            except sqlite3.OperationalError as e:
                trows, tr_note = [], 'not searched: the index refused that query (%s)' % e
            per = {}
            for r in trows:
                meta = per.setdefault(r['file_key'], {
                    'board': r['board'], 'date': r['date'], 'rank': r['rank'],
                    'moments': {}, 'forms': set()})
                meta['rank'] = min(meta['rank'], r['rank'])
                body = unmark(r['marked'])
                segs = json.loads(r['seg_starts'] or '[]')
                for off, form in marks(r['marked']):
                    meta['forms'].add(form)
                    secs = seconds_at(segs, off)
                    if secs is None:
                        secs = r['start_s']
                    # The chunks overlap by one segment, so the same moment can arrive
                    # twice. The segment's own start is what identifies it.
                    if secs in meta['moments']:
                        continue
                    meta['moments'][secs] = (
                        re.sub(r'&t=\d+s$', '', r['cite_url']) + '&t=%ds' % secs,
                        context_at(body, off, a.context, len(form)))
            order = (sorted(per.values(), key=lambda m: (m['date'],))
                     if a.order == 'date'
                     else sorted(per.values(), key=lambda m: m['rank']))
            for meta in order:
                hit_meetings += 1
                # One PASSAGE, not one segment. The chunks overlap and a phrase said twice
                # in a sentence lands in consecutive three-second segments, so three
                # "moments" ten seconds apart are one thing said once. Collapse them and
                # keep the earliest, which is the timestamp somebody would scrub to.
                moments, last = [], None
                for secs, (cite, ctx) in sorted(meta['moments'].items()):
                    if last is not None and secs - last < MOMENT_GAP:
                        continue
                    last = secs
                    moments.append((secs, cite, ctx))
                print_transcript_hit(meta, moments[:3], meta['forms'], words,
                                     hit_meetings == 1)

    # Every in-scope document is settled into exactly one state before anything is printed,
    # so the numbers below cannot fail to add up to the scope. In the index route the
    # searchability of a document is READ OFF THE INDEX rather than by opening 12,000
    # files -- the index holds one row per document that has something to match, which is
    # the same definition `build_minutes_searchable.py` uses and is reconciled against it
    # by `build_minutes_fts.py --check`.
    if route == 'fts':
        for r in scope:
            r['_searchable'] = r['_key'] in indexed or r['_key'] in stale
    else:
        for r in scope:
            if r['_has_text']:
                body_of(r)
    searched = [r for r in scope if r['_searchable']]
    unsearchable = [r for r in scope if r['_held'] and not r['_searchable']]
    not_held = [r for r in scope if not r['_held']]
    if len(searched) + len(unsearchable) + len(not_held) != len(scope):
        raise SystemExit('the three states do not account for every document in scope. '
                         'Refusing to print a coverage line that does not foot.')

    # Printed on EVERY run, hits or none. This is the whole reason the script exists.
    print(f'\n{"-" * 72}')
    filters = [f'board~{a.board}' if a.board else '',
               f'since {a.since}' if a.since else '',
               f'until {a.until}' if a.until else '']
    where = ', '.join(f for f in filters if f)
    print(f'{hit_docs} town document(s) matched {a.term!r}'
          + (f'  [{where}]' if where else '  [whole archive]') + '.')
    if a.transcripts:
        print(f'{hit_meetings} meeting(s) matched it in OUR MACHINE CAPTIONS, which are '
              'a finding aid and not a record.')

    print(f'\nROUTE: {"FTS5 index" if route == "fts" else "grep"}'
          + (f' — {route_note}' if route_note else '')
          + (f'; tokenised and stemmed (porter), so a hit may be a variant of your word '
             f'— each result says which' if route == 'fts' else
             '; a substring match, so `ELL` also matches `well` and `shell`'))
    if route == 'fts' and stale:
        print(f'  {len(stale):,} in-scope file(s) are NOT in the index or have changed '
              'since indexing.')
        print('  They were grepped directly and are marked as such above. Run '
              'scripts/build_minutes_fts.py')
    elif route == 'fts':
        print('  The index is current for every file in scope.')

    n = len(scope)
    pct = (100.0 * len(searched) / n) if n else 0.0
    print(f'\nTOWN-PUBLISHED DOCUMENTS')
    print(f'  SEARCHED {len(searched):,} of the {n:,} document(s) in scope ({pct:.0f}%).')
    if unsearchable:
        print(f'  {len(unsearchable):,} {"is" if len(unsearchable) == 1 else "are"} held '
              'but carr' + ('ies' if len(unsearchable) == 1 else 'y')
              + ' no searchable text at all.')
    if not_held:
        print(f'  {len(not_held):,} {"is" if len(not_held) == 1 else "are"} listed by the '
              'town and not held here.')
    if unsearchable or not_held:
        print('  An empty result above does NOT cover those, so "nobody said it" is not')
        print('  a conclusion this run can support.')
        if a.board or a.since or a.until:
            print('  These are YOUR filter\'s figures. The archive average is better than')
            print('  some boards and worse than others; do not substitute it for this.')
    else:
        print('  Every document in scope is searchable, so an empty result here does mean')
        print('  the term does not appear in it.')

    # A SECOND DENOMINATOR, DELIBERATELY NOT ADDED TO THE FIRST. The one above counts what
    # the TOWN published. This counts what WE made from recordings. Summing them would
    # report a machine's rendering of audio as archive coverage.
    tr = transcript_scope(a.board, a.since, a.until)
    print('\nOUR TRANSCRIPTS (machine captions — a separate corpus, a separate '
          'denominator)')
    if tr is None:
        print('  sources/data/meeting-register.csv is absent, so how many meetings COULD')
        print('  be covered is unstated. Run scripts/build_meeting_register.py.')
    elif not a.transcripts:
        print('  NOT SEARCHED — you passed --no-transcripts. %d meeting(s) in scope have a'
              % tr['recorded'])
        print('  recording and %d of those have a transcript here; none of it was read.'
              % tr['transcribed'])
    elif tr_note:
        print('  %s' % tr_note)
    else:
        rpct = (100.0 * tr['transcribed'] / tr['recorded']) if tr['recorded'] else 0.0
        print('  SEARCHED %d of the %d meeting(s) in scope that have a recording (%.0f%%).'
              % (tr['transcribed'], tr['recorded'], rpct))
        print('  That is %d of %d distinct recordings; a joint meeting is one recording '
              'and is' % (tr['recordings_transcribed'], tr['recordings']))
        print('  counted once under each board that sat in it.')
        print('  %d meeting(s) in scope have a recording and NO document at all — no '
              'agenda,' % tr['video_only'])
        print('  no minutes, nothing filed. %d of those can now be searched here; the '
              'other %d' % (tr['video_only_transcribed'],
                            tr['video_only'] - tr['video_only_transcribed']))
        print('  cannot be searched by anything, and the document coverage above does not')
        print('  count them at all.')
        print('  ' + CAPTION_CAVEAT)
        print('  Captions are fetched a meeting at a time; this figure grows. '
              'scripts/fetch_youtube_transcripts.py --status')

    whole = archive_wide()
    if whole is None:
        print('\n  (sources/data/minutes-searchable.csv is absent, so why those documents')
        print('   cannot be read is unstated. Run scripts/build_minutes_searchable.py.)')
    else:
        wpct = 100.0 * whole['searchable'] / whole['held'] if whole['held'] else 0.0
        lead = ('Archive-wide' if n != whole['listed'] else 'Why they cannot be read')
        print(f'\n  {lead}: {whole["searchable"]:,} of {whole["held"]:,} held documents '
              f'are searchable ({wpct:.0f}%).')
        print(f'  Of the {whole["unsearchable"]:,} that are not — '
              f'{whole["image_scan"]:,} image scans awaiting OCR, '
              f'{whole["vector_outlines"]:,} whose text is drawn')
        print(f'  as vector outlines, {whole["blank"]:,} blank, '
              f'{whole["extract_failed"]:,} with a text layer our extractor could not '
              f'read, {whole["unreadable"]:,} that')
        print(f'  will not parse; and {whole["not_fetched"]:,} the town lists that we do '
              'not hold.')
        print('  Per board and year: sources/data/minutes-searchable.csv')

    if unsearchable:
        show = unsearchable if a.list_unsearchable else unsearchable[:12]
        print(f'\nThe {len(unsearchable)} in-scope document(s) that cannot be searched'
              + ('' if a.list_unsearchable else f' (first {len(show)})') + ':')
        for r in sorted(show, key=lambda r: (r['date'], r['board'])):
            print(f'  {r["board"][:34]:<34} {r["date"]} {r["kind"]:<8} {r["url"]}')
        if len(show) < len(unsearchable):
            print(f'  ... and {len(unsearchable) - len(show)} more '
                  '(--list-unsearchable prints them all)')

    if not_held:
        show = not_held if a.list_unsearchable else not_held[:12]
        print(f'\nThe {len(not_held)} in-scope document(s) the town lists and we do not '
              'hold:')
        for r in sorted(show, key=lambda r: (r['date'], r['board'])):
            print(f'  {r["board"][:34]:<34} {r["date"]} {r["kind"]:<8} {r["url"]}')
        if len(show) < len(not_held):
            print(f'  ... and {len(not_held) - len(show)} more')
    return 0


if __name__ == '__main__':
    sys.exit(main())
