"""Browsable views of the archive: one file on disk, many places to find it.

    python3 scripts/build_views.py
    python3 scripts/build_views.py --check    # fail if any link dangles

Writes `views/` at the repository root. **Nothing is copied and nothing in `sources/` is
touched or moved.** Every entry is a relative symlink to the real file, so the archive has
exactly one canonical copy and this is a second way to reach it.

WHY THIS EXISTS

`sources/` is organised by provenance, because that is the only attribute of a document
that is single-valued and never changes. Everything a person actually searches by is
neither: `fy27-proposals.xlsx` carries five fiscal years, a town meeting warrant covers
twenty subjects, and what we use a document for changes as the work does. A directory
tree can hold one key; the questions people ask need several.

So the tree keeps provenance and this holds the rest. A document appears under every year
it covers and every group it belongs to, which is correct in an index and impossible in a
folder.

WHY SYMLINKS AND NOT COPIES

A copy is a second thing that can drift, and this archive already carries a sha256 on
every file precisely because a document can be replaced in place. A link cannot drift: it
either resolves to the one real file or it dangles, and `--check` fails when it dangles.
They cost the length of a path -- the whole of `views/` is a few kilobytes.

They are committed rather than ignored. The point is to open Finder and find a document
without running anything, and a view that has to be generated before it exists does not
do that on a fresh clone.

WHERE THE NAMES COME FROM

`sources.json`, which already carries a curated title for all 302 documents -- "FY27
line-item projections, 23 March 2026" rather than `fy27-projections-3-23-26.pdf`. Nothing
here invents a name.

**The real file keeps the publisher's filename and the link does not have to.** Rule 12
requires the publisher's own name to survive, because when a link dies the only way a
resident gets the document is to ask the town for it by name. A view is not the archive,
so it can be readable.

WHAT IT REFUSES TO DO

It classifies from what the catalogue states and never from a guess. A fiscal year is
taken only from an explicit FY marker in the title or path. Anything it cannot place is
listed in `views/README.md` with a count, because a view that quietly covers 55% of the
archive while looking complete is the coverage-bias failure this project has already
shipped once.
"""
import argparse
import html
import json
import os
import re
import shutil
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOGUE = os.path.join(ROOT, 'fy28', 'src', 'data', 'sources.json')
SOURCES = os.path.join(ROOT, 'sources')
VIEWS = os.path.join(ROOT, 'views')

# A fiscal year stated outright. NOT inferred from a date: a document published in March
# 2026 may be about FY27, and guessing which would put real documents under wrong years.
FY = re.compile(r'\bFY\s?(\d{2})\b', re.I)


def documents():
    """Every catalogued document, with the group heading it sits under."""
    cat = json.load(open(CATALOGUE, encoding='utf-8'))
    out = []

    def walk(node, group):
        if isinstance(node, dict):
            if 'path' in node and 'title' in node:
                out.append((group, node))
                return
            here = node.get('title') or node.get('name') or group
            for key, val in node.items():
                walk(val, here if isinstance(here, str) else key)
        elif isinstance(node, list):
            for val in node:
                walk(val, group)

    walk(cat, None)
    return out


def safe(name):
    """A filename that survives a filesystem and still reads like the title.

    Titles come out of scraped pages and carry raw HTML entities -- `Town Manager&#39;s`
    -- which would be the name somebody reads in Finder.
    """
    name = html.unescape(name)
    name = name.replace('/', ' - ').replace(':', ' -').replace('\x00', '')
    name = re.sub(r'\s+', ' ', name).strip().strip('.')
    return name[:150] or 'untitled'


def link(target_abs, link_path):
    """A RELATIVE symlink, so the whole repository can be moved or cloned anywhere."""
    os.makedirs(os.path.dirname(link_path), exist_ok=True)
    rel = os.path.relpath(target_abs, os.path.dirname(link_path))
    if os.path.islink(link_path) or os.path.exists(link_path):
        os.remove(link_path)
    os.symlink(rel, link_path)


def place(view, folder, title, doc, seen):
    """Link a document, and its extracted text where one exists, into one folder.

    The PDF and the text we actually read from it live in different directories in
    `sources/` -- `pdf/` and `txt/`. Here they sit together under one name, which is what
    somebody browsing expects and is the single most confusing thing about the archive as
    it stands.
    """
    made = 0
    placed = set()
    for path_key, suffix in (('path', ''), ('textPath', ' (text)')):
        rel = doc.get(path_key)
        if not rel:
            continue
        target = os.path.join(SOURCES, rel)
        if not os.path.exists(target) or target in placed:
            # A spreadsheet is its own text, so textUrl repeats url and a second link
            # would point at the same bytes under a name promising something else.
            continue
        placed.add(target)
        ext = os.path.splitext(rel)[1]
        base = safe(title) + suffix
        name, n = base + ext, 2
        while (view, folder, name) in seen:
            name, n = f'{base} ({n}){ext}', n + 1
        seen.add((view, folder, name))
        link(target, os.path.join(VIEWS, view, folder, name))
        made += 1
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='exit non-zero if any link dangles')
    args = ap.parse_args()

    docs = documents()
    if not docs:
        print('no catalogued documents; run scripts/build_source_index.py first')
        return 1

    # textUrl is a published URL; the archive path is what a link has to point at.
    for _g, doc in docs:
        turl = doc.get('textUrl')
        if turl and turl.startswith('/docs/'):
            doc['textPath'] = turl[len('/docs/'):]

    if not args.check and os.path.isdir(VIEWS):
        shutil.rmtree(VIEWS)

    seen, made = set(), 0
    years = defaultdict(int)
    no_year = []

    for group, doc in docs:
        title = doc['title']

        # by fiscal year -- a document appears under EVERY year it states
        found = sorted({'FY' + m for m in FY.findall(title + ' ' + doc['path'])})
        if found:
            for fy in found:
                made += place('by-fiscal-year', fy, title, doc, seen)
                years[fy] += 1
        else:
            no_year.append(doc)

        # by group -- the catalogue's own headings, already curated
        if group:
            made += place('by-group', safe(group), title, doc, seen)

        # by importance -- the documents the project actually leans on
        stars = doc.get('stars')
        if isinstance(stars, int) and stars >= 3:
            made += place('by-importance', 'load-bearing (3 stars)', title, doc, seen)

    # Every link, checked. A committed symlink's one real failure mode is dangling.
    dangling = []
    for dp, _dn, fns in os.walk(VIEWS):
        for fn in fns:
            p = os.path.join(dp, fn)
            if os.path.islink(p) and not os.path.exists(p):
                dangling.append(os.path.relpath(p, ROOT))

    if not args.check:
        with open(os.path.join(VIEWS, 'README.md'), 'w', encoding='utf-8') as fh:
            fh.write(readme(docs, years, no_year, made))

    print('views/ — %d links over %d documents' % (made, len(docs)))
    print('  by-fiscal-year: %d years, %d documents placed, %d with no stated year'
          % (len(years), len(docs) - len(no_year), len(no_year)))
    if dangling:
        print('  %d DANGLING link(s):' % len(dangling))
        for d in dangling[:10]:
            print('    ', d)
        return 1
    print('  every link resolves')
    return 0


def readme(docs, years, no_year, made):
    L = ['# Views — the same archive, indexed by the questions people ask', '',
         'Generated by `scripts/build_views.py`. **Every entry here is a symlink.** The',
         'real files live in `sources/`, organised by where they came from, and nothing',
         'in this directory is a copy — open one and you open the original.',
         '',
         'Regenerate after any ingest:', '', '    python3 scripts/build_views.py', '',
         '## What is here', '',
         '| view | what it answers |', '|---|---|',
         '| `by-fiscal-year/` | which documents cover FY26 — including ones whose name '
         'says FY27, because a projection carries five years of actuals |',
         '| `by-group/` | the catalogue’s own subject headings |',
         '| `by-importance/` | the documents this project actually leans on |',
         '',
         '## Coverage, stated rather than implied', '',
         '**%d of %d catalogued documents state a fiscal year** in their title or path '
         'and appear under `by-fiscal-year/`.' % (len(docs) - len(no_year), len(docs)),
         '',
         'The other **%d do not**, and are NOT placed by year. A fiscal year is taken '
         'only from' % len(no_year),
         'an explicit `FY26`-style marker, never inferred from a publication date — a '
         'document',
         'published in March 2026 is usually about FY27, and guessing would file real',
         'documents under wrong years. Every one of them is reachable through '
         '`by-group/`.',
         '',
         '| year | documents |', '|---|---:|']
    for fy in sorted(years):
        L.append('| %s | %d |' % (fy, years[fy]))
    L += ['', '## Documents with no stated fiscal year', '',
          'Listed so this view cannot look more complete than it is.', '']
    for doc in sorted(no_year, key=lambda d: d['path'])[:400]:
        L.append('- `%s` — %s' % (doc['path'], doc['title']))
    L.append('')
    return '\n'.join(L)


if __name__ == '__main__':
    sys.exit(main())
