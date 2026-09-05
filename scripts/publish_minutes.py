"""Publish the meeting archive as text an agent can actually read and search.

The archive holds 1,383 agendas and sets of minutes, and until now published none of their
text. `llms.txt` said so in as many words — *"Extracted text of all of them is in the
repository"* — which is true and useless to anybody who is not holding the repository.
What the site served was an index of 1,422 dates pointing at the town's own scanned PDFs.

The cost of that was measured rather than guessed. An assistant asked to find the School
Committee's most recent discussion of the paraprofessional contract read the site and
concluded it mirrors *"budget documents, not School Committee minutes"*, and that contract
discussions "would more likely be in minutes… which are a different set of documents". It
was wrong, and it was wrong for a good reason: nothing it could reach showed otherwise.

Two things are published here, because an agent needs both and they solve different halves:

**1. Every document, individually**, at `/docs/minutes/text/<board>/<file>.txt`. This is
what a citation needs — a stable address for the one document a figure rests on.

**2. One bundle per board**, at `/minutes/<board>.txt`. Each document inside carries a
header with its date, kind, our own path and the town's URL, so anything found in a bundle
can be cited to a single document rather than to the bundle.

*"The whole School Committee, 118 documents, is 1.1MB — comfortably one fetch"* is what
this docstring said, and it was wrong for the two boards it matters for. An assistant:
*"The bundle's 0.88MB — too big to read in one go here."* It recovered by grepping the repo
from its container; anything holding only a URL could not. **select-board is 1.02MB and
school-committee 0.92MB — the two most likely to be asked about, and the only two over
0.5MB.** The bundles remain the right thing for a caller that can hold them, and
`build_minutes_search.py` publishes an inverted index for every caller that cannot.

The bundles are a convenience layer over the individual files and are byte-derivable from
them. They are not a source; the individual files are.

    python3 scripts/publish_minutes.py

Writes fy28/public/docs/minutes/text/**, fy28/public/minutes/*.txt and a manifest.
"""
import csv
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources', 'meetings')
TEXT = os.path.join(SRC, 'text')
PUB = os.path.join(ROOT, 'fy28', 'public')
# The SOURCE folder is sources/meetings/; the PUBLISHED path stays /docs/minutes/.
# A folder name is internal and a URL is a contract: llms.txt tells agents to cite
# /docs/minutes/text/<board>/..., documents.json embeds 1,422 of those paths, and
# functions/minutes/[[path]].js serves the bundles. Renaming the folder should cost
# nobody a link.
DOCS_OUT = os.path.join(PUB, 'docs', 'minutes', 'text')
BUNDLE_OUT = os.path.join(PUB, 'minutes')
SITE = 'https://lunenburgbudgetproject.org'

# A bundle nobody can fetch is no better than no bundle. Cloudflare Pages caps a single
# asset at 25MB; well below that, an agent's own fetch limit bites first. Boards over this
# are split by year.
MAX_BUNDLE = 4 * 1024 * 1024


def town_urls():
    """file stem -> the town's own URL, from the index the fetcher wrote."""
    idx = os.path.join(SRC, 'index.csv')
    out = {}
    if os.path.exists(idx):
        for r in csv.DictReader(open(idx)):
            stem = os.path.splitext(os.path.basename(r.get('path', '')))[0]
            if stem:
                out[stem] = r.get('url', '')
    return out


def main():
    if not os.path.isdir(TEXT):
        sys.exit(f'no extracted text at {TEXT} — run scripts/extract_minutes.py')

    urls = town_urls()
    shutil.rmtree(DOCS_OUT, ignore_errors=True)
    # Delete THIS script's own output, not the folder it sits in. `fy28/public/minutes/`
    # also holds `find/` -- the word index, 476 files, published at the URL llms.txt tells
    # agents to use -- and an `rmtree` of the parent takes it with the bundles. That is a
    # loaded gun for the next person who runs this after a fresh checkout, and it does not
    # announce itself: the site keeps working until the next deploy.
    for name in os.listdir(BUNDLE_OUT) if os.path.isdir(BUNDLE_OUT) else []:
        if name.endswith(('.txt', '.csv')):
            os.remove(os.path.join(BUNDLE_OUT, name))
    os.makedirs(DOCS_OUT, exist_ok=True)
    os.makedirs(BUNDLE_OUT, exist_ok=True)

    boards, copied, total_bytes = {}, 0, 0
    for board in sorted(os.listdir(TEXT)):
        bdir = os.path.join(TEXT, board)
        if not os.path.isdir(bdir):
            continue
        files = sorted(f for f in os.listdir(bdir) if f.endswith('.txt'))
        if not files:
            continue
        os.makedirs(os.path.join(DOCS_OUT, board), exist_ok=True)
        docs = []
        for fn in files:
            src = os.path.join(bdir, fn)
            shutil.copy2(src, os.path.join(DOCS_OUT, board, fn))
            copied += 1
            body = open(src, encoding='utf-8', errors='ignore').read()
            total_bytes += len(body)
            stem = os.path.splitext(fn)[0]
            # Date and kind are in the filename the fetcher wrote: YYYY-MM-DD-kind-id
            bits = stem.split('-')
            date = '-'.join(bits[:3]) if len(bits) >= 3 else ''
            kind = bits[3] if len(bits) >= 4 else ''
            docs.append(dict(fn=fn, stem=stem, date=date, kind=kind, body=body,
                             path=f'/docs/minutes/text/{board}/{fn}',
                             url=urls.get(stem, '')))
        boards[board] = docs

    # Bundles, split by year where a board is too large to be one fetch.
    manifest = []
    for board, docs in boards.items():
        size = sum(len(d['body']) for d in docs)
        groups = {'': docs}
        if size > MAX_BUNDLE:
            groups = {}
            for d in docs:
                y = d['date'][:4] or 'undated'
                groups.setdefault(y, []).append(d)

        for suffix, group in sorted(groups.items()):
            name = f'{board}.txt' if not suffix else f'{board}-{suffix}.txt'
            out = os.path.join(BUNDLE_OUT, name)
            with open(out, 'w', encoding='utf-8') as fh:
                fh.write(
                    f'# {board} — {len(group)} documents, concatenated for reading and search\n'
                    f'#\n'
                    f'# This is a CONVENIENCE BUNDLE, not a source. Every document below is\n'
                    f'# published separately and byte-identically; cite the individual file,\n'
                    f'# whose path is given in each header, rather than this bundle.\n'
                    f'# Index of all boards: {SITE}/minutes/INDEX.txt\n'
                    f'# The town\'s own scanned original is linked per document.\n\n')
                for d in group:
                    fh.write('=' * 88 + '\n')
                    fh.write(f'DOCUMENT : {d["fn"]}\n')
                    fh.write(f'BOARD    : {board}\n')
                    fh.write(f'DATE     : {d["date"]}\n')
                    fh.write(f'KIND     : {d["kind"]}\n')
                    fh.write(f'OUR COPY : {SITE}{d["path"]}\n')
                    if d['url']:
                        fh.write(f'TOWN PDF : {d["url"]}\n')
                    fh.write('=' * 88 + '\n\n')
                    fh.write(d['body'].rstrip() + '\n\n')
            manifest.append(dict(board=board, file=name, docs=len(group),
                                 bytes=os.path.getsize(out)))

    # ONE INDEX PER BOARD, because the combined one cannot be read by the callers it is
    # for. `/data/minutes-index.csv` is 242KB sorted alphabetically by board, and an
    # agent reported its fetch truncating around 60-70% -- which cuts off at "Lunenburg
    # Municipal Building", so School Committee, Select Board, Sewer Commission, Planning
    # Board and everything else late in the alphabet is unreachable. It resorted to
    # cloning the repository. A file a reader has to leave the site to read is not
    # published; and sorting differently would only move which boards are unreachable.
    #
    # So: one small CSV per board, beside that board's text bundle, in date order with
    # the newest first -- because a truncated read of a dated file should lose the oldest
    # rows, not the newest.
    csv_manifest = []
    for board, docs in boards.items():
        out = os.path.join(BUNDLE_OUT, f'{board}.csv')
        with open(out, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['date', 'kind', 'board', 'our_copy', 'town_pdf', 'bytes'])
            for d in sorted(docs, key=lambda d: d['date'], reverse=True):
                w.writerow([d['date'], d['kind'], board, SITE + d['path'],
                            d['url'], len(d['body'])])
        csv_manifest.append(dict(board=board, docs=len(docs),
                                 bytes=os.path.getsize(out)))

    with open(os.path.join(BUNDLE_OUT, 'INDEX.txt'), 'w', encoding='utf-8') as fh:
        fh.write('Lunenburg meeting archive — full text, by board\n')
        fh.write('=' * 88 + '\n\n')
        fh.write(f'{copied} agendas and sets of minutes across {len(boards)} town boards.\n'
                 'Each bundle below is every document for one board, concatenated, with a\n'
                 'header per document giving its date, our own permanent address for it, and\n'
                 "the town's scanned original.\n\n"
                 'Cite the individual document, never a bundle.\n\n'
                 'TO SEARCH: do not start with a bundle. The two largest are around 1MB,\n'
                 'which is more than many callers can read at once. Look the word up and\n'
                 'fetch only the documents it names -- three small requests:\n'
                 f'  {SITE}/minutes/find/README.txt      how, in twenty lines\n'
                 f'  {SITE}/minutes/find/<first two letters of the word>.json\n\n'
                 'The bundles below are still the fastest way to read a board whole, if\n'
                 'you can hold one. Check the size in this list before fetching.\n\n'
                 f'Individual documents: {SITE}/docs/minutes/text/<board>/<file>.txt\n\n'
                 'TO ANSWER A DATE OR BOARD QUESTION without reading any text, fetch that\n'
                 "board's index instead of its bundle. Same name, .csv rather than .txt --\n"
                 f'  {SITE}/minutes/school-committee.csv    (a few KB)\n'
                 'date, kind, board, our permanent address for the document, the town\'s\n'
                 'own PDF, and its size. Newest first. Every board has one.\n\n'
                 f'All of them in one file: {SITE}/data/minutes-index.csv '
                 f'({os.path.getsize(os.path.join(SRC, "index.csv"))/1024:.0f}KB, sorted\n'
                 'by board, and too large for some callers to read whole -- which is why\n'
                 'the per-board files above exist).\n\n'
                 '  docs      text        index\n')
        by_board = {m['board']: m for m in csv_manifest}
        for m in sorted(manifest, key=lambda m: -m['docs']):
            c = by_board.get(m['board'], {})
            fh.write(f'{m["docs"]:>5} docs  {m["bytes"]/1024/1024:>6.2f}MB  '
                     f'{c.get("bytes", 0)/1024:>6.1f}KB  '
                     f'{SITE}/minutes/{m["file"]}\n')

    print(f'published {copied} documents ({total_bytes/1024/1024:.1f}MB of text) '
          f'across {len(boards)} boards')
    print(f'  individual : {os.path.relpath(DOCS_OUT, ROOT)}/<board>/<file>.txt')
    print(f'  bundles    : {os.path.relpath(BUNDLE_OUT, ROOT)}/  ({len(manifest)} files)\n')
    for m in sorted(manifest, key=lambda m: -m['docs'])[:8]:
        print(f'  {m["docs"]:>5} docs  {m["bytes"]/1024/1024:>6.2f}MB  /minutes/{m["file"]}')
    big = [m for m in manifest if m['bytes'] > 25 * 1024 * 1024]
    if big:
        print(f'\n  WARNING: {len(big)} bundle(s) exceed the 25MB per-file host limit')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
