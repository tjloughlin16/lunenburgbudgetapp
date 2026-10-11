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
    recorded    OUR minutes of a recording (write_recording_minutes.py): votes, transfers,
                topics. Derived twice over; cited to the video, styled as ours.
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
import glob
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
RECORDED = os.path.join(ROOT, 'sources', 'data', 'recording-minutes')
# The town's words for ours. Curated by hand in the CSV, published as JSON for the search
# page, which offers them when a search finds little. Constraint 3 of QUEUE item 18: a
# resident types "foreign language" and the archive says "French", and a null result on a
# public search reads as "the town never discussed it".
VOCAB_CSV = os.path.join(ROOT, 'sources', 'data', 'search-vocabulary.csv')
VOCAB_JSON = os.path.join(ROOT, 'fy28', 'public', 'data', 'search-vocabulary.json')
# EVERY BOARD THE SEARCH CAN ACTUALLY NARROW TO, generated from the index itself.
# `Search.tsx` carried a hardcoded list of SIX, so Parks Commission -- 186 meeting dates
# of minutes, agendas and recordings -- could not be selected at all, and neither could
# the other fifty. TJ: *"the search board drop-down doesn't have all..it's a limited set."*
# A hardcoded list of things the data already knows is this repo's most common defect
# (CLAUDE.md, `A LOCATION WAS HARDCODED where location is not identity`), and the
# remedy is the same every time: derive it, and let a check fail when it drifts.
BOARDS_JSON = os.path.join(ROOT, 'fy28', 'public', 'data', 'search-boards.json')
# AFFINITY -- what a page is ABOUT, as words, whether or not its text says them often.
# TJ, 11 September: "put 'affinity' so that certain words hit more with certain pages and
# reports or minutes even if the words don't show up as much." The search-engine term is
# BOOSTING: a curated keywords field weighted above the body. Here it is its own small
# FTS table, so it can change without re-pushing 97,000 rows, and a hit through it is
# labelled as matched by topic rather than by text -- curation is visible as curation.
AFFINITY_CSV = os.path.join(ROOT, 'sources', 'data', 'search-affinity.csv')
SITE = M.SITE

TOKENIZE = M.TOKENIZE
PAGE_MARKER = re.compile(r'^===PAGE (\d+)===$', re.M)

# Source folders whose documents are indexed by page. DISCOVERED, never listed.
#
# This was a hardcoded allowlist of five folders, and it is why TJ went looking for the
# landscaping contract on 2 October 2026 and found nothing: the document is in
# `town-ledgers`, which was not on the list, and neither were ten other trees. That is
# CLAUDE.md's own defect #1 -- *a location was hardcoded where location is not identity* --
# sitting in the one script whose output a resident reads. A list of eleven would be the
# same bug with a longer constant.
#
# So the gate is the CONTRACT rather than the name: a folder is indexed when it has an
# `index.csv` carrying `label`, `local` and `text`, which is what `source_files()` reads
# and what gives every row a citation. A tree gets searched the day it gets a conforming
# catalogue, and a tree with no catalogue -- or with a mirror's four-column one, as
# `state-dls` and `state-massgis` have -- stays out until somebody writes one.
#
# `meetings` is excluded by name and not by contract: it is the minutes corpus, it has its
# own reader and its own denominator, and its index is a different shape entirely.
SOURCE_INDEX_COLUMNS = {'label', 'local', 'text'}
SOURCE_FOLDERS_SKIP = {'meetings'}


def source_folders():
    out = []
    for idx in sorted(glob.glob(os.path.join(SRC, '*', 'index.csv'))):
        folder = os.path.basename(os.path.dirname(idx))
        if folder in SOURCE_FOLDERS_SKIP:
            continue
        with open(idx, encoding='utf-8', errors='replace') as fh:
            cols = set(next(csv.reader(fh), []))
        if SOURCE_INDEX_COLUMNS <= cols:
            out.append(folder)
    return out


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

# AN UNINDEXED FTS5 COLUMN HAS NO INDEX. `WHERE file_key=?` or `WHERE doc_key=?` on `search`
# is a scan of every row, body and all -- and the build ran one per affinity row (1,318) and
# one per changed file, so once ~2,900 Open Meeting Law letters joined the index the
# 10 October 2026 overnight run spent 5.5 hours in fts5NextMethod and never finished. This
# ordinary table maps each search rowid to its file and document, with real indexes, so
# every such lookup is an index seek and then a rowid fetch. It is local bookkeeping only:
# sync_search_d1.py names the tables it pushes, and this is not one of them.
KEY_SCHEMA = """
CREATE TABLE IF NOT EXISTS search_key (rid INTEGER PRIMARY KEY, file_key TEXT NOT NULL, doc_key TEXT);
CREATE INDEX IF NOT EXISTS search_key_file ON search_key(file_key);
CREATE INDEX IF NOT EXISTS search_key_doc ON search_key(doc_key);
"""
AFFINITY_DDL = ("CREATE VIRTUAL TABLE affinity USING fts5(tags, doc_key UNINDEXED, "
                "corpus UNINDEXED, title UNINDEXED, cite_url UNINDEXED, tokenize=%r)" % TOKENIZE)


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
    for folder in source_folders():
        idx = os.path.join(SRC, folder, 'index.csv')
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
    # TWO FILES, ONE KEY. A source row's doc_key is `<folder>/<file stem>`, so the FY26 and
    # FY27 copies of `warrant-article-tracking-copy.xlsx` -- and the three PROVENANCE notes
    # for one MUNIS delivery, in expenses/, revenue/ and fund-balances/ -- shared a key. The
    # search de-duplicates hits on doc_key, so one of each pair could never be found, and
    # sync_search_d1.py --check failed on "3 duplicated rows". Where a key would collide,
    # every file sharing it is keyed by its path within the folder instead. Keys that do not
    # collide are unchanged, so search-affinity.csv and every published citation still hold.
    seen = {}
    for e in out:
        seen.setdefault((e['folder'], _stem(e['file'])), []).append(e)
    for (folder, _), group in seen.items():
        # Distinct FILES, not distinct catalogue rows: a folder's index.csv may list one text
        # twice, and those already share a file_key, so wanted() keeps one and nothing collides.
        if len({e['file_key'] for e in group}) > 1:
            for e in group:
                d = os.path.relpath(os.path.dirname(e['file']), os.path.join(SRC, folder)).split(os.sep)
                if d and d[-1] == 'text':
                    d = d[:-1]
                e['key_stem'] = '/'.join([x for x in d if x not in ('', '.')] + [_stem(e['file'])])
    return out


def _stem(path):
    return os.path.splitext(os.path.basename(path))[0]


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
    stem = entry.get('key_stem') or _stem(entry['file'])
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
# The page's NAME is its <title>, minus the site's suffix -- set per page by the app
# since 15 September 2026 (fy28/src/lib/title.ts). Before that every page carried the
# site's title and the index fell back to the first <h1>, which on a report is the
# FINDING in a sentence ("Fewest paraprofessionals per pupil in the group, then the
# most.") rather than anything a reader could recognise as a page. The <h1> is still the
# fallback for a page whose title is the site's, so nothing goes untitled.
H1 = re.compile(r'<h1\b[^>]*>(.*?)</h1>', re.S | re.I)
SITE_NAME = 'Lunenburg Budget Project'
SITE_TITLE_SUFFIX = re.compile(r'\s+\u2014\s+' + re.escape(SITE_NAME) + r'\s*$')


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
    t = TITLE.search(raw)
    title = re.sub(r'\s+', ' ', html.unescape(TAG.sub('', t.group(1))).strip()) if t else ''
    if not SITE_TITLE_SUFFIX.search(title):
        # The site's own title, or none: this page did not name itself. Fall back to
        # the first heading, as before.
        m = H1.search(raw)
        title = html.unescape(TAG.sub('', m.group(1))).strip() if m else entry['route']
    title = re.sub(r'\s+', ' ', SITE_TITLE_SUFFIX.sub('', title))
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


# ------------------------------------------------------------ our minutes of recordings

def recorded_files():
    out = []
    for f in sorted(glob.glob(os.path.join(RECORDED, '*', '*.json'))):
        out.append({'file': f, 'file_key': rel(f), 'corpus': 'recorded'})
    return out


def recorded_rows(entry):
    m = json.load(open(entry['file'], encoding='utf-8'))
    mm = m['minutes']
    parts = [mm.get('summary', '')]
    parts += [t.replace('-', ' ') for t in mm.get('tags', [])]
    parts += [p['topic'] for p in mm.get('public_comment', [])]
    parts += [v['motion'] + ' — ' + v['outcome'] for v in mm.get('votes', [])]
    parts += [t['description'] for t in mm.get('transfers', [])]
    parts += [b['topic'] + '. ' + b['what_was_said'] for b in mm.get('budget_items', [])]
    parts += [d['decision'] for d in mm.get('decisions', [])]
    parts += [t['topic'] + ' — ' + t['resolution'] for t in mm.get('topics', [])]
    body = re.sub(r'\s+', ' ', ' '.join(p for p in parts if p)).strip()
    slug = '%s/%s-%s' % (m['board_slug'], m['meeting_date'], m['video_id'])
    return [({
        'corpus': 'recorded',
        'doc_key': 'recorded:' + slug,
        'file_key': entry['file_key'],
        'title': '%s, %s — our minutes of the recording' % (m['board'], m['meeting_date']),
        'board': m['board'], 'board_slug': m['board_slug'],
        'date': m['meeting_date'],
        'kind': 'our minutes',
        'cite_url': '%s/meeting-minutes/%s' % (SITE, slug),
        'source_url': m['video_url'],
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


# ------------------------------------------------ job postings: the town's and the district's
#
# TJ, 10 October 2026: *"I'm looking for a job posting for the school and can't find it."*
# The postings were already fetched daily and catalogued in `district-budget/index.csv`,
# which put them inside the `source` corpus's contract -- and out of its reach: they are
# JSON, their catalogue rows carry no `text`, and their labels say `SchoolSpring posting
# 5822484` rather than the job. So a search for `paraprofessional` found nothing.
#
# One row per POSTING, read from the history `extract_school_job_postings.py` already
# builds, with the description from the posting's latest snapshot. The date is the
# publisher's own `posted_date`, so newest-first means newest posted. A posting no longer
# listed stays findable and says so in its title: it left the listing, which is not a hire.

JOBS_CSV = os.path.join(ROOT, 'sources', 'data', 'school-job-postings.csv')
TOWN_JOBS_CSV = os.path.join(ROOT, 'sources', 'data', 'town-job-postings.csv')
# Since 10 October 2026 the town's postings are read too (fetch_town_job_postings.py), and
# both employers share one page, /jobs, which is where a posting no longer listed is cited.
JOBS_PAGE = SITE + '/jobs'


def job_files():
    return [{'file': f, 'file_key': rel(f), 'corpus': 'job'}
            for f in (JOBS_CSV, TOWN_JOBS_CSV) if os.path.exists(f)]


def _job(employer, employer_name, r, posting_id, title, posted, closes, last_seen, parts):
    listed = r['status'] != 'removed'
    body = re.sub(r'\s+', ' ', ' '.join(x for x in parts + [
        'job posting', 'job opening', 'vacancy', employer_name,
        'posted ' + posted, 'still listed' if listed else 'no longer listed'] if x)).strip()
    return ({
        'corpus': 'job',
        'doc_key': 'job:%s:%s' % (employer, posting_id),
        'file_key': rel(TOWN_JOBS_CSV if employer == 'town' else JOBS_CSV),
        'title': title if listed else 'No longer listed: ' + title,
        'board': employer_name,
        'board_slug': None,
        'date': posted,
        'kind': (closes or 'open') if listed else 'last seen %s' % last_seen,
        # An open posting cites the place to apply; one that has come down cites its line
        # in the history on /jobs, because the employer's page for it may not answer now.
        'cite_url': r['url'] if listed else '%s#job-%s-%s-down' % (JOBS_PAGE, employer, posting_id),
        'source_url': None,
        'start_s': None, 'seg_starts': None,
        'chars': len(body),
    }, body)


def job_rows(entry):
    import extract_school_job_postings as J
    out = []
    town = entry['file'] == TOWN_JOBS_CSV
    for r in csv.DictReader(open(entry['file'], encoding='utf-8')):
        if town:
            row, body = _job('town', 'Town of Lunenburg', r, r['posting_id'], r['title'],
                             r['posted_date'], r['closing_as_printed'].lower(), r['last_seen'],
                             [r['title'], r['department_as_printed'], r['category']])
            row['source_url'] = '%s/docs/%s' % (SITE, r['listing_file'][len('sources/'):])
        else:
            info = {}
            if r.get('detail_file'):
                p = os.path.join(ROOT, r['detail_file'])
                if os.path.exists(p):
                    info = json.load(open(p, encoding='utf-8'))['value'].get('jobInfo') or {}
            row, body = _job('schools', r['employer_as_printed'] or 'Lunenburg Public Schools', r,
                             r['posting_id'], r['title'], r['posted_date'],
                             'open until %s' % r['closing_date'] if r['closing_date'] else '', r['last_seen'],
                             [r['title'], r['locations'], r['category'], r['job_type'],
                              'positions: ' + r['positions'] if r['positions'] else '',
                              'closes ' + r['closing_date'] if r['closing_date'] else '',
                              J.text_of(info.get('jobDescription')), J.text_of(info.get('requirements'))])
            if r.get('detail_file'):
                row['source_url'] = '%s/docs/%s' % (SITE, r['detail_file'][len('sources/'):])
        out.append((row, body))
    return out


# -------------------------------------------------------------------------------- people
#
# Same request: *"We need to add a PEOPLE and JOBS lookup in search."* Everybody the org
# charts hold -- the annual reports' rosters, FY2011 onward, and both staff directories --
# is already public on /org-charts, one unit and one year at a time. Nothing let a reader
# start from a NAME.
#
# One row per name as printed (whitespace collapsed, case ignored), listing every role,
# body and year it appears under. The SAME NAME IS NOT PROVEN TO BE ONE PERSON -- two
# Jennifers in two decades are one row here -- and the card says so. The link goes to the
# most recent chart the name is on. No email, no extension: the search carries what the
# chart shows and nothing more.

ORG_JSON = os.path.join(ROOT, 'fy28', 'public', 'data', 'org-charts.json')


def person_files():
    if not os.path.exists(ORG_JSON):
        return []
    return [{'file': ORG_JSON, 'file_key': rel(ORG_JSON), 'corpus': 'person'}]


def _fy_span(fys):
    fys = sorted(set(fys))
    return ('FY%s' % fys[0]) if len(fys) == 1 else ('FY%s–FY%s' % (fys[0], fys[-1]))


def person_rows(entry):
    from urllib.parse import urlencode
    rows = json.load(open(entry['file'], encoding='utf-8'))['rows']
    people = {}
    for r in rows:
        name = ' '.join((r.get('person') or '').split())
        if r.get('status') != 'filled' or not name:
            continue
        people.setdefault(name.lower(), {'names': [], 'rows': []})
        people[name.lower()]['names'].append(name)
        people[name.lower()]['rows'].append(r)
    out = []
    for key, p in sorted(people.items()):
        name = max(set(p['names']), key=p['names'].count)
        held = {}
        for r in p['rows']:
            where = r['unit'] + (' — ' + r['subunit'] if r.get('subunit') else '')
            held.setdefault((r['role'] or 'listed', where), []).append(r['fy'])
        # Most recent first, so the snippet a reader sees is what they hold now.
        lines = sorted(held.items(), key=lambda kv: max(kv[1]), reverse=True)
        latest = max(p['rows'], key=lambda r: (r['fy'], -int(r.get('tier') or 0)))
        body = name + '. ' + ' '.join('%s, %s, %s.' % (role, where, _fy_span(fys))
                                      for (role, where), fys in lines)
        out.append(({
            'corpus': 'person',
            'doc_key': 'person:' + re.sub(r'[^a-z0-9]+', '-', key).strip('-'),
            'file_key': entry['file_key'],
            'title': name,
            'board': latest['unit'], 'board_slug': None,
            'date': '',
            'kind': '%s, FY%s' % (latest['role'] or 'listed', latest['fy']),
            'cite_url': '%s/org-charts?%s' % (SITE, urlencode({'unit': latest['unit'], 'fy': latest['fy']})),
            'source_url': None,
            'start_s': None, 'seg_starts': None,
            'chars': len(body),
        }, body))
    return out


# ------------------------------------------------------------------------------- the build

# EVERY CORPUS, IN ONE PLACE. sync_search_d1.py reads this rather than keeping its own
# list: a corpus added here and not there is indexed locally and never counted remotely.
CORPORA = ('post', 'page', 'job', 'person', 'recorded', 'source', 'minutes', 'transcript')

READERS = {
    'job': job_rows,
    'person': person_rows,
    'minutes': minutes_rows,
    'transcript': transcript_rows,
    'source': source_rows,
    'page': page_rows,
    'post': post_rows,
    'recorded': recorded_rows,
}


def wanted():
    out = {}
    for e in (minutes_files() + M.transcript_files() + source_files()
              + page_files() + post_files() + recorded_files() + job_files() + person_files()):
        e['sha256'] = M.sha256_of(e['file'])
        if e.get('key_stem'):
            # The KEY is part of what the indexer makes, so it is part of the fingerprint:
            # a file re-keyed with unchanged bytes must still be re-read here and re-sent
            # by sync_search_d1.py, which both decide on this field alone.
            e['sha256'] += ':key=' + e['key_stem']
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
    ensure_keys(db)
    return db


def ensure_keys(db):
    """Create search_key if this index predates it, and fill it from ONE scan of `search`.
    And if it disagrees with indexed_file's own row counts -- both ordinary tables, so the
    comparison is cheap -- refill it, so a key table that drifted can never send a lookup
    to the wrong row or miss one."""
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='search'").fetchone():
        return
    db.executescript(KEY_SCHEMA)
    keyed = db.execute('SELECT COUNT(*) FROM search_key').fetchone()[0]
    expect = db.execute('SELECT COALESCE(SUM(rows), 0) FROM indexed_file').fetchone()[0]
    if keyed != expect:
        db.execute('DELETE FROM search_key')
        db.execute('INSERT INTO search_key SELECT rowid, file_key, doc_key FROM search')
        db.commit()
        print('  search_key: filled %d row(s) from one scan (held %d, indexed_file says %d)'
              % (db.execute('SELECT COUNT(*) FROM search_key').fetchone()[0], keyed, expect),
              file=sys.stderr)


def rows_for_file(db, file_key, cols='*'):
    """Every search row of one file, in rowid order -- an index seek, never a scan."""
    rids = [r[0] for r in db.execute('SELECT rid FROM search_key WHERE file_key=? ORDER BY rid', (file_key,))]
    return [db.execute('SELECT %s FROM search WHERE rowid=?' % cols, (rid,)).fetchone() for rid in rids]


def row_for_doc(db, doc_key, cols):
    """The first search row carrying `doc_key`, or None -- an index seek, never a scan."""
    hit = db.execute('SELECT rid FROM search_key WHERE doc_key=? ORDER BY rid LIMIT 1', (doc_key,)).fetchone()
    return db.execute('SELECT %s FROM search WHERE rowid=?' % cols, (hit[0],)).fetchone() if hit else None


def have(db):
    return {r['file_key']: dict(r) for r in db.execute('SELECT * FROM indexed_file')}


def drift(db):
    w, h = wanted(), have(db)
    # No build on disk means nothing can be said about the pages, not that they are gone.
    # A clone that has never built the site must not report 78 removed files.
    if not os.path.isdir(DIST):
        h = {k: v for k, v in h.items() if v['corpus'] != 'page'}
    else:
        # `dist` EXISTING IS NOT `dist` BEING PRERENDERED, and the difference nearly
        # deleted the index. `vite build` alone -- or a `build:site` whose prerender step
        # died partway -- empties dist and leaves only the SPA shell plus whatever
        # `public/` copies verbatim: a dozen files, not one per route.
        #
        # On 20 September 2026 the refresh's own build:site died at EADDRINUSE after vite
        # had already emptied dist, so the next run walked 12 files and concluded that 70
        # real pages had been removed from the site. They had not; the build never
        # finished. The affinity check caught it and refused to publish, which is the only
        # reason a stripped index was not pushed to D1.
        #
        # Diagnosed by the triage agent this repository spawns on a failed refresh -- its
        # first run, and it found this rather than the thing it was pointed at.
        #
        # Same treatment as no dist at all: say nothing about pages rather than trust a
        # build that plainly did not run to completion. Anything actually present still
        # indexes normally; only the DELETIONS are withheld.
        found = sum(1 for k in w if w[k]['corpus'] == 'page')
        had = sum(1 for k in h if h[k]['corpus'] == 'page')
        if had >= 10 and found < had * 0.5:
            print('  NOTE: dist holds %d page(s) against %d in the index - this looks '
                  'like an unfinished build, so no page is treated as removed'
                  % (found, had), file=sys.stderr)
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


def _pieces(body):
    """Sentence and paragraph breaks first; a piece STILL over MAX_CHARS is cut at line
    breaks, then at spaces, then hard. Spreadsheet text has neither sentence ends nor blank
    lines, so a 246,000-character Finance Committee sheet came through as one "paragraph",
    was never split, and every search push from 8 October 2026 died on SQLITE_TOOBIG."""
    for para in re.split(r'(?<=[.!?])\s+|\n{2,}', body):
        if len(para) <= MAX_CHARS:
            yield para
            continue
        for line in re.split(r'\n', para):
            while len(line) > MAX_CHARS:
                cut = line.rfind(' ', 0, MAX_CHARS)
                cut = cut if cut > MAX_CHARS // 2 else MAX_CHARS
                yield line[:cut]
                line = line[cut:].lstrip()
            if line:
                yield line


def split_body(body):
    if len(body) <= MAX_CHARS:
        return [body]
    parts, buf = [], ''
    for para in _pieces(body):
        if buf and len(buf) + len(para) + 1 > MAX_CHARS:
            parts.append(buf)
            buf = ''
        buf = (buf + ' ' + para).strip() if buf else para
    if buf:
        parts.append(buf)
    return parts


CONTROL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


def readable(body):
    """Is this text, or the wreckage of a font encoding?

    167 Board of Assessors agendas extracted to `\\x00 \\x01 \\x02 ...` -- a PDF whose text
    layer maps glyphs to control characters. Indexing that matches nothing, and worse: a
    NUL inside a SQL string makes D1 drop the insert silently while the file's marker
    lands, so the sync reported them held for ever. A row nobody could search for is not
    a row."""
    if not body:
        return False
    # Control characters are the tell. A share-of-letters test was tried and dropped
    # seven budget spreadsheets, which are legitimately mostly digits.
    return not CONTROL.search(body)


def index_file(db, entry):
    rows = []
    for row, body in READERS[entry['corpus']](entry):
        if not readable(body):
            continue
        parts = split_body(body)
        for i, part in enumerate(parts):
            r = dict(row)
            if i:
                r['doc_key'] = '%s#part%d' % (row['doc_key'], i + 1)
            r['chars'] = len(part)
            rows.append((r, part))
    for row, body in rows:
        cur = db.execute('INSERT INTO search (%s) VALUES (%s)' % (','.join(COLS), ','.join('?' * len(COLS))),
                         [body] + [row.get(c) for c in META_COLS])
        db.execute('INSERT INTO search_key VALUES (?,?,?)', (cur.lastrowid, row.get('file_key'), row.get('doc_key')))
    db.execute('INSERT OR REPLACE INTO indexed_file VALUES (?,?,?,?,?)',
               (entry['file_key'], entry['corpus'], entry['sha256'],
                os.path.getsize(entry['file']), len(rows)))
    return len(rows)


def forget(db, file_key):
    for (rid,) in db.execute('SELECT rid FROM search_key WHERE file_key=?', (file_key,)).fetchall():
        db.execute('DELETE FROM search WHERE rowid=?', (rid,))
    db.execute('DELETE FROM search_key WHERE file_key=?', (file_key,))
    db.execute('DELETE FROM indexed_file WHERE file_key=?', (file_key,))


def build(rebuild=False, quiet=False):
    # A zero-byte file is what an interrupted first run leaves behind, and it is not an
    # index: the refresh tree's 17 September run died on `no such table: indexed_file`.
    fresh = rebuild or not os.path.exists(DB) or os.path.getsize(DB) == 0
    # ...and so is a file with bytes and no tables, which is what the 17 September run
    # actually met: `no such table: indexed_file` in the refresh tree, again.
    if not fresh:
        try:
            has = connect(DB, create=False).execute("SELECT 1 FROM sqlite_master WHERE name='indexed_file'").fetchone()
        except Exception:
            has = None
        fresh = not has
    if fresh and os.path.exists(DB):
        os.remove(DB)
    db = connect(DB, create=fresh)
    if fresh:
        w = wanted()
        added, changed, removed = list(w), [], []
    else:
        w, _, added, changed, removed = drift(db)
        # A SPLIT RULE APPLIES TO WHAT IS ALREADY INDEXED, NOT ONLY TO WHAT ARRIVES NEXT. The
        # index re-reads a file only when its text changes, so when long bodies began to be
        # split (890111ac) every document already in the index kept its one 246 KB row, and
        # the 10 October push still died on SQLITE_TOOBIG. Whenever the index was split to a
        # different limit than MAX_CHARS -- or never recorded one -- every file holding a row
        # over the limit is re-read. One scan, and only when the limit moves.
        split = db.execute("SELECT v FROM build_meta WHERE k='max_chars'").fetchone()
        if not split or split[0] != str(MAX_CHARS):
            long_files = {r[0] for r in db.execute('SELECT DISTINCT file_key FROM search WHERE length(body) > ?',
                                                   (MAX_CHARS,))}
            again = [k for k in long_files if k in w and k not in changed and k not in added]
            if again:
                print('  re-splitting %d file(s) indexed before the %d-character limit'
                      % (len(again), MAX_CHARS), file=sys.stderr)
            changed += again
    for k in removed + changed:
        forget(db, k)
    n = 0
    for i, k in enumerate(added + changed, 1):
        n += index_file(db, w[k])
        if not quiet and i % 500 == 0:
            print('  %d/%d files' % (i, len(added) + len(changed)), file=sys.stderr)
    build_affinity(db)
    db.execute('INSERT OR REPLACE INTO build_meta VALUES (?,?)', ('tokenize', TOKENIZE))
    db.execute('INSERT OR REPLACE INTO build_meta VALUES (?,?)', ('max_chars', str(MAX_CHARS)))
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


def affinity_rows():
    """Every curated row, joined to the indexed row it names. A tag for a page that does
    not exist is a typo, and a join that matches nothing must not read as data."""
    rows = list(csv.DictReader(open(AFFINITY_CSV, encoding='utf-8')))
    if len(rows) < 10:
        raise SystemExit('%s parsed to %d rows; refusing' % (rel(AFFINITY_CSV), len(rows)))
    return [(r['doc_key'].strip(), re.sub(r'\s*;\s*', ' ; ', r['tags'].strip())) for r in rows]


def build_affinity(db):
    db.execute('DROP TABLE IF EXISTS affinity')
    db.execute(AFFINITY_DDL)
    missing = []
    for doc_key, tags in affinity_rows():
        hit = row_for_doc(db, doc_key, 'corpus, title, cite_url')
        if not hit:
            missing.append(doc_key)
            continue
        title = re.sub(r', page \d+$', '', hit['title']) if hit['corpus'] == 'source' else hit['title']
        cite = re.sub(r'#page=\d+$', '', hit['cite_url']) if hit['corpus'] == 'source' else hit['cite_url']
        db.execute('INSERT INTO affinity (tags, doc_key, corpus, title, cite_url) VALUES (?,?,?,?,?)',
                   (tags, doc_key, hit['corpus'], title, cite))
    if missing:
        # AN AFFINITY ROW NAMES A PAGE BY ONE OF ITS ADDRESSES, AND PAGES HAVE SEVERAL.
        #
        # routes.ts keeps SLUG (tab -> the canonical slug) and ALIASES (an older or
        # shorter address -> tab). The index holds the canonical one; search-affinity.csv
        # was written by hand and names whichever address the writer had in mind. So a row
        # reading `page:what-it-all-adds-up-to` is not a row naming nothing -- it is the
        # alias of `page:one-big-report`, which is indexed and fine.
        #
        # Conflating those two killed the whole nightly refresh twice in three days:
        # 14 September 2026 on page:what-it-all-adds-up-to and 16 September on
        # page:the-paraprofessionals (the alias of page:paras). Both pages existed both
        # times. Nothing was wrong except the address the row used.
        #
        # So resolve through ALIASES before deciding, and keep the error for a row that
        # resolves to nothing at all -- which is the case actually worth failing on.
        alias_target = _page_aliases()
        def canonical(key):
            if not key.startswith('page:'):
                return None
            slug = key.split(':', 1)[1]
            return alias_target.get(slug, slug)

        still = []
        aliased = []
        for key in missing:
            canon = canonical(key)
            if canon is None or canon == key.split(':', 1)[1]:
                still.append(key)
                continue
            hit = row_for_doc(db, 'page:' + canon, 'corpus, title, cite_url')
            if not hit:
                still.append(key)
                continue
            tags = dict(affinity_rows())[key]
            db.execute('INSERT INTO affinity (tags, doc_key, corpus, title, cite_url) '
                       'VALUES (?,?,?,?,?)',
                       (tags, 'page:' + canon, hit['corpus'], hit['title'], hit['cite_url']))
            aliased.append('%s -> page:%s' % (key, canon))

        if aliased:
            print('  NOTE: %d affinity row(s) named an alias and were indexed under the '
                  'canonical address: %s' % (len(aliased), ', '.join(aliased[:6])),
                  file=sys.stderr)
        # A PAGE EXISTS BECAUSE routes.ts DECLARES IT, NOT BECAUSE dist HAPPENED TO
        # RENDER IT -- and this check had those two confused, which is a different fault
        # from the alias one above and was hiding behind it.
        #
        # The index is built FROM dist. `scripts/refresh.py` builds the search index at
        # step 8 and only runs `npm run build:site` inside its DEPLOY branch, later. So on
        # a normal night dist is whatever the last deploy left, every page added since is
        # absent from it, and their affinity rows look like rows naming nothing. On
        # 20 September 2026 that was 70 of them and it failed the whole run -- after the
        # ingestion, so new meetings were committed and the index was not.
        #
        # Existence and indexability are different questions:
        #   declared in routes.ts, not in the index -> real page, not rendered YET. Skip.
        #   not declared anywhere                   -> names nothing. That is the error.
        #
        # The second is the one worth failing on, and it still does.
        declared = _declared_slugs()
        unbuilt = [k for k in still
                   if k.startswith('page:')
                   and canonical(k) in declared]
        unknown = [k for k in still if k not in unbuilt]

        if unbuilt:
            print('  NOTE: %d affinity row(s) name pages routes.ts declares but this '
                  'dist has not rendered, so they are skipped rather than indexed '
                  '(build the site to pick them up): %s'
                  % (len(unbuilt), ', '.join(unbuilt[:6])), file=sys.stderr)
        if unknown:
            if os.path.isdir(DIST):
                raise SystemExit(
                    'search-affinity.csv names %d doc_key(s) that no page declares and '
                    'the index does not hold:\n  %s'
                    % (len(unknown), '\n  '.join(unknown[:20])))
            print('  NOTE: %d affinity rows name pages; fy28/dist is absent so they were '
                  'skipped' % len(unknown), file=sys.stderr)


def _declared_slugs():
    """Every slug the app routes on, listed or not, read from routes.ts.

    Not build_sitemap.routed(), which is SLUG minus UNLISTED -- an unlisted page is still
    a page, reachable by anybody given the address, and an affinity row naming one is not
    an error. The sitemap has a reason to exclude them; this check does not.
    """
    src = _routes_src()
    m = re.search(r'export const SLUG: Record<Tab, string> = \{(.*?)\n\}', src, re.S)
    if not m:
        raise SystemExit('routes.ts: could not find SLUG')
    slugs = {v for _, v in re.findall(r"^\s*'?([A-Za-z0-9_-]+)'?:\s*'([^']*)'",
                                      m.group(1), re.M) if v}
    # NESTED ROUTES EXIST TOO, and the SLUG table does not list them. `/analysis/<id>` is
    # one route per Markdown analysis on disk -- 20 September 2026 this check passed the
    # 53 top-level pages and then failed on seventeen of these, which are as real as any
    # of them. A page's existence is what the app routes on, and the app routes on the
    # file being there.
    slugs |= {'analysis/' + os.path.splitext(f)[0]
              for f in os.listdir(os.path.join(ROOT, 'sources', 'analyses'))
              if f.endswith('.md')}
    return slugs


def _routes_src():
    with open(os.path.join(ROOT, 'fy28', 'src', 'routes.ts'), encoding='utf-8') as fh:
        return fh.read()


def _page_aliases():
    """alias slug -> canonical slug, read from routes.ts.

    Read rather than duplicated, for the reason build_sitemap.routed() gives about the
    SLUG table: routes.ts is what decides a page's addresses, and a second copy of that
    mapping here would be a latent drift with a date on it."""
    src = _routes_src()
    m = re.search(r'export const SLUG: Record<Tab, string> = \{(.*?)\n\}', src, re.S)
    if not m:
        raise SystemExit('routes.ts: could not find SLUG')
    slug = dict(re.findall(r"^\s*'?([A-Za-z0-9_-]+)'?:\s*'([^']*)'", m.group(1), re.M))
    a = re.search(r'const ALIASES: Record<string, Tab> = \{(.*?)\n\}', src, re.S)
    if not a:
        return {}
    out = {}
    for alias, tab in re.findall(r"'?([A-Za-z0-9_-]+)'?:\s*'([A-Za-z0-9_]+)'", a.group(1)):
        if tab in slug and slug[tab] != alias:
            out[alias] = slug[tab]
    return out


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


def boards(db):
    """The board filter's options, as JSON, counted in MEETINGS.

    ONLY THE DATED CORPORA. The control is disabled unless the selected type carries a
    date -- minutes, agendas, our notes and machine captions -- so a board with nothing
    but `source` rows would be an option that can never match. That is also why the
    source TREES (`town-ledgers`, `contracts`, `peer-districts`, ...) do not appear: they
    share the `board_slug` column and are not boards.

    COUNTED IN MEETINGS, NOT ROWS. `doc_key` is one row per CHUNK in these corpora, so a
    count of them is a count of our own slicing -- rule 7's proxy trap, and it would have
    put `57,154` beside Select Board. Distinct DATE per board is a real quantity: one
    meeting, however many artifacts it left behind.

    THE LABEL IS THE TOWN'S OWN. `Nashoba Valley Reginal Dispatch Committee` keeps its
    spelling and `Tcp Building Design Committee` its capitalisation, because the name a
    resident needs is the one the AgendaCenter prints, not a tidier one of ours.
    """
    rows = db.execute(
        "SELECT board_slug slug, board label, COUNT(DISTINCT date) meetings, "
        "       MIN(date) first, MAX(date) last "
        '  FROM search '
        " WHERE corpus IN ('minutes','recorded','transcript') "
        "   AND board_slug IS NOT NULL AND board_slug != '' "
        "   AND date IS NOT NULL AND date != '' "
        ' GROUP BY board_slug ORDER BY meetings DESC, slug').fetchall()
    if len(rows) < 20:
        raise SystemExit('the index yielded %d board(s) for the search filter; refusing to '
                         'publish a list that short -- the hardcoded six is what this '
                         'replaces' % len(rows))
    out = [{'slug': r['slug'], 'label': r['label'] or r['slug'],
            'meetings': r['meetings'], 'first': r['first'], 'last': r['last']}
           for r in rows]
    return json.dumps(out, indent=1, ensure_ascii=False) + '\n'


def write_boards(db):
    with open(BOARDS_JSON, 'w', encoding='utf-8') as fh:
        fh.write(boards(db))


def check_boards(db):
    current = open(BOARDS_JSON, encoding='utf-8').read() if os.path.exists(BOARDS_JSON) else ''
    if current != boards(db):
        print('STALE: %s does not reproduce from the index' % rel(BOARDS_JSON))
        return 1
    return 0


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
    n = db.execute('SELECT COUNT(*) FROM affinity').fetchone()[0]
    print('  affinity     %8d rows of curated topic tags' % n)
    if not os.path.isdir(DIST):
        print('  NOTE: fy28/dist is absent, so the page corpus reflects the last build indexed')


def check(db):
    w, h, added, changed, removed = drift(db)
    # A transcript that arrived since the last build is not staleness: the backfill adds
    # one every minute for hours, and a check that fails for the whole of that is a check
    # nobody runs. Anything CHANGED or REMOVED underneath the index is, and fails.
    new_transcripts = [k for k in added if w[k]['corpus'] == 'transcript']
    added = [k for k in added if w[k]['corpus'] != 'transcript']
    if new_transcripts:
        print('  note: %d transcript(s) arrived since the index was built; rebuild before pushing'
              % len(new_transcripts))
    if added or changed or removed:
        print('STALE: %d added, %d changed, %d removed since the index was built'
              % (len(added), len(changed), len(removed)))
        for k in (added + changed + removed)[:12]:
            print('  ' + k)
        return 1
    if check_vocabulary() or check_boards(db):
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
    write_boards(db)
    status(db)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
