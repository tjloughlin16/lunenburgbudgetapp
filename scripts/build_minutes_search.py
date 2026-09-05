"""Make the meeting archive searchable by something that can only fetch URLs.

WHY

`publish_minutes.py` publishes two things and its own docstring says they solve the two
halves an agent needs: every document individually, for citing, and one bundle per board,
for searching. The second half does not work, and the reason is a number in that docstring:

    "The whole School Committee, 118 documents, is 1.1MB -- comfortably one fetch."

It is not. An assistant asked to find a discussion in the School Committee minutes replied:
*"The bundle's 0.88MB -- too big to read in one go here. But the archive text is in your
repo, and I can reach GitHub from the container. Let me grep it directly."* It was right on
both counts, and it only recovered because it had a shell. Anything that can only fetch a
URL had no path at all: it could list 1,383 documents, or read one, or fail to read a board.
Nothing let it find WHICH document mentions a word.

Two boards are the whole problem -- select-board at 1.02MB and school-committee at 0.92MB,
the two most likely to be asked about. The other 39 bundles are fine.

WHAT THIS BUILDS

An inverted index: term -> the documents containing it. Sharded by the first two characters
of the term, so a lookup is one small fetch rather than a download of the whole index.

    /minutes/find/je.json     {"jersey": [412, 908], "jerseys": [412], ...}
    /minutes/find/documents.json   the array those numbers index into
    /minutes/find/README.txt       how to use it, for whatever arrives without context

The numbers are positions in `documents.json`, not file ids -- an integer costs a few bytes
where a path costs sixty, and the postings are almost all of the size.

Static files. No search server, nothing computed per request, which is what the rest of
this site promises and what a Pages deploy can actually hold.

WHAT IT DOES NOT DO

It finds documents containing a WORD. It does not rank them, does not do phrases, and does
not know that "jerseys" and "uniforms" are the same subject. An agent gets a short list of
candidate documents and reads them -- which is the right division of labour, because the
reading is the part it is good at and the scanning of 6.2MB is the part it cannot do.

    python3 scripts/build_minutes_search.py

Writes fy28/public/minutes/find/**.
"""
import json
import os
import re
import shutil
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT = os.path.join(ROOT, 'fy28', 'public', 'docs', 'minutes', 'text')
# PUBLISHED AT /minutes/find/, and that is not negotiable by a folder rename.
#
# `sources/minutes/` became `sources/meetings/` on 4 September 2026 and this output
# followed the source folder, so 476 files moved from /minutes/find/ to /meetings/find/.
# Nothing that advertises them moved: llms.txt, the /agents page, the release notes and
# this index's own README all still say /minutes/find/, and they are right -- a folder
# name is internal and a URL is a contract. The result was that `documents.json` and
# `coverage.json` 404'd while being cited as the way to use the shards, which makes the
# shards useless: they return document numbers with nothing to resolve them against.
#
# It was invisible for a day because the old files were still being served from a
# week-long edge cache. An agent found it, not a check.
OUT = os.path.join(ROOT, 'fy28', 'public', 'minutes', 'find')
SITE = 'https://lunenburgbudgetproject.org'

# A term in nearly every document tells you nothing about which one to read, and its
# postings list is the longest in the index -- the worst of both. Dropped, and the
# threshold is stated in README.txt rather than left as a silent behaviour.
TOO_COMMON = 0.40

# Three characters is where an index of this corpus stops being mostly noise: 'fy', 'mr'
# and every initial survive at two, and none of them narrows anything.
MIN_LEN = 3

TOKEN = re.compile(r"[a-z][a-z0-9'-]{%d,}" % (MIN_LEN - 1))
NAME = re.compile(r'^(\d{4}-\d{2}-\d{2})-([a-z]+)-(\d+)\.txt$')


def documents():
    """Every published document, in a stable order, read off what is actually on disk."""
    out = []
    for board in sorted(os.listdir(TEXT)):
        d = os.path.join(TEXT, board)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            m = NAME.match(fn)
            if not m:
                continue
            date, kind, file_id = m.groups()
            out.append(dict(board=board, date=date, kind=kind, id=int(file_id),
                            path=f'/docs/minutes/text/{board}/{fn}'))
    return out


def unsearchable():
    """Index rows with no readable text — what a search over this index CANNOT see.

    This is published rather than merely counted, and the reason is the audience. An agent
    with a shell finds a coverage gap by listing the text tree; the callers this index
    exists for can only fetch URLs, and have no way to discover what is missing by any
    means available to them. For them the index stating its own denominator is not a
    convenience -- it is the only route to the caveat.

    It went wrong exactly that way. 39 documents the town published as Word files were
    absent from the archive, the index reported "1,383 documents" without saying of how
    many, and a search returning nothing was indistinguishable from a subject nobody
    raised. The general name for that is coverage bias, and the fix is always to report
    the denominator.
    """
    idx = os.path.join(ROOT, 'sources', 'meetings', 'index.csv')
    if not os.path.exists(idx):
        return None, []
    import csv
    rows = list(csv.DictReader(open(idx)))
    missing = []
    for r in rows:
        stem = os.path.splitext(r['path'])[0] if r['path'].strip() else ''
        ok = stem and os.path.exists(
            os.path.join(ROOT, 'sources', 'meetings', 'text', stem + '.txt'))
        if not ok:
            missing.append(dict(board=r['board'], date=r['date'], kind=r['kind'],
                                url=r['url']))
    return len(rows), missing


def main():
    docs = documents()
    published_total, missing = unsearchable()
    if not docs:
        print(f'no documents under {TEXT} -- run publish_minutes.py first', file=sys.stderr)
        return 1

    postings = defaultdict(set)
    for i, d in enumerate(docs):
        with open(os.path.join(ROOT, 'fy28', 'public') + d['path'], errors='replace') as fh:
            for tok in set(TOKEN.findall(fh.read().lower())):
                postings[tok].add(i)

    cap = int(len(docs) * TOO_COMMON)
    kept = {t: sorted(v) for t, v in postings.items() if len(v) <= cap}
    dropped = len(postings) - len(kept)

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    shards = defaultdict(dict)
    for term, ids in kept.items():
        shards[term[:2]][term] = ids
    for prefix, terms in shards.items():
        with open(os.path.join(OUT, f'{prefix}.json'), 'w') as fh:
            json.dump(dict(sorted(terms.items())), fh, separators=(',', ':'))

    with open(os.path.join(OUT, 'documents.json'), 'w') as fh:
        json.dump(docs, fh, separators=(',', ':'))

    # The denominator, as data, beside the documents it is the denominator of.
    with open(os.path.join(OUT, 'coverage.json'), 'w') as fh:
        json.dump(dict(
            indexed=len(docs),
            published_by_the_town=published_total,
            note=('Documents in this index against documents the town has published. A '
                  'search here can only find something said in the indexed ones. If the '
                  'two numbers differ, `unsearchable` lists every document that cannot be '
                  'searched, and an empty result means "not in the indexed set" rather '
                  'than "never discussed".'),
            unsearchable=missing,
        ), fh, indent=1)

    sizes = {p: os.path.getsize(os.path.join(OUT, f'{p}.json')) for p in shards}
    biggest = max(sizes.items(), key=lambda kv: kv[1])
    with open(os.path.join(OUT, 'README.txt'), 'w') as fh:
        fh.write(f"""Which meeting documents contain a word.

The bundles at /minutes/<board>.txt are the whole text of a board, and the two largest --
select-board and school-committee -- are around 1MB, which is more than most callers can
read in one fetch. This index exists so you do not have to.

COVERAGE -- READ THIS BEFORE CONCLUDING ANYTHING FROM AN EMPTY RESULT

This index covers {len(docs):,} documents. The town has published {published_total or len(docs):,}.
{'Every published document is searchable.' if published_total == len(docs) else f'{published_total - len(docs)} are NOT searchable and are listed in coverage.json.'}

An empty result means the word is not in the {len(docs):,} documents indexed here. That is
not the same as nobody having said it, and the two are only distinguishable if you know the
denominator -- so it is published: {SITE}/minutes/find/coverage.json.

This is not hypothetical. 39 documents the town published as Word files were missing from
this archive while every count said otherwise, one of them School Committee minutes from the
middle of a fiscal year under analysis. They are here now. The count above is what makes the
next such gap visible instead of silent.

HOW TO USE IT

  1. Lowercase your word. Take its first two characters. Fetch that shard:
         {SITE}/minutes/find/je.json
     It is an object of term -> array of document numbers:
         {{"jersey":[412,908], "jerseys":[412], ...}}
     A term absent from the shard appears in no document. A missing shard file means no
     term starts with those two characters.

  2. Fetch the document table ONCE and keep it:
         {SITE}/minutes/find/documents.json
     An array. Position N is the document that the number N refers to:
         {{"board":"school-committee","date":"2025-09-17","kind":"minutes",
           "id":7408,"path":"/docs/minutes/text/school-committee/2025-09-17-minutes-7408.txt"}}

  3. Fetch the documents you want, at {SITE}<path>. They average 4.5KB.

Cite the individual document, never this index and never a bundle.

WHAT IT IS AND IS NOT

It reports which documents contain a word. It does not rank them, does not support phrases
or wildcards, and does not know that two words mean the same thing -- searching "jerseys"
will not find a document that only says "uniforms". Search both.

Terms shorter than {MIN_LEN} characters are not indexed. Terms appearing in more than
{int(TOO_COMMON * 100)}% of documents are not indexed either: they cannot narrow anything and their
postings would be most of the index. {dropped:,} terms were dropped on that rule.

Words are matched exactly as they appear in the text, so plurals and possessives are
separate terms. The text is extracted from scans, so it carries OCR errors.

BUILT FROM

{len(docs):,} of {published_total or len(docs):,} published documents, {len(kept):,} indexed terms, {len(shards)} shards.
Rebuild with scripts/build_minutes_search.py. The documents are the source; this is
derived and can be thrown away.
""")

    total = sum(sizes.values()) + os.path.getsize(os.path.join(OUT, 'documents.json'))
    print(f'wrote {os.path.relpath(OUT, ROOT)}/')
    print(f'  {len(docs):,} of {published_total} published documents '
          f'({100*len(docs)/(published_total or len(docs)):.1f}%), '
          f'{len(kept):,} terms, {dropped:,} dropped as too common')
    if missing:
        print(f'  {len(missing)} NOT searchable -- listed in coverage.json')
    print(f'  {len(shards)} shards, {total / 1e6:.2f}MB total, '
          f'largest shard {biggest[0]}.json at {biggest[1] / 1e3:.0f}KB')
    return 0


if __name__ == '__main__':
    sys.exit(main())
