#!/usr/bin/env python3
"""Publish the long documents in pieces, because nobody can read them whole.

    python3 scripts/split_large_text.py [--check]

An assistant asked to open the FY2022 annual town report found three routes to it and
could finish none: the PDF is 16.8MB and no longer in the repository, the extracted text
is 0.5MB, and the structured extract was 0.4MB. Its fetch tool truncates around 150KB.

So every published `.txt` over that gets a folder of parts beside it and an index naming
them, at a predictable address:

    /docs/<path>.txt              the whole thing, unchanged
    /docs/<path>.parts/index.json how many parts, how big, and what page each starts at
    /docs/<path>.parts/001.txt    the first ~140KB, split on a page boundary

**Split on page boundaries, never mid-sentence.** The extracted text carries `===PAGE n===`
markers, and a part that begins halfway through a paragraph is a part nobody can cite. The
index records the first and last page of each part so a reader can jump to the right one
rather than walking them all.

The whole file stays exactly where it was. Nothing is replaced -- this is an additional
address for a document that already had one.
"""
import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive_storage as A  # noqa: E402

PUB = os.path.join(ROOT, 'fy28', 'public', 'docs')
SITE = 'https://lunenburgbudgetproject.org'
LIMIT = 140 * 1024          # under the 150KB a fetcher holds, with room for the header
PAGE = re.compile(r'^===PAGE (\d+)===', re.M)


def parts_of(text):
    """Split on page boundaries, keeping each part under the limit."""
    marks = [(m.start(), int(m.group(1))) for m in PAGE.finditer(text)]
    if not marks:
        # No page markers: fall back to paragraph boundaries so a part still begins
        # somewhere a reader can make sense of.
        blocks = text.split('\n\n')
        chunks, cur = [], ''
        for b in blocks:
            if cur and len(cur) + len(b) + 2 > LIMIT:
                chunks.append((cur, None, None))
                cur = ''
            cur += (b + '\n\n')
        if cur.strip():
            chunks.append((cur, None, None))
        return chunks
    bounds = [m[0] for m in marks] + [len(text)]
    chunks, cur, first, last = [], '', marks[0][1], marks[0][1]
    for i, (start, page) in enumerate(marks):
        block = text[start:bounds[i + 1]]
        if cur and len(cur) + len(block) > LIMIT:
            chunks.append((cur, first, last))
            cur, first = '', page
        cur += block
        last = page
    if cur.strip():
        chunks.append((cur, first, last))
    return chunks


def original_of(rel, manifest):
    """The publisher's own file behind an extracted text, with its size and sha256.

    An assistant that cannot hold a 16.8MB scan can still hand a PERSON the link to it --
    citing a URL and fetching it are different acts, and the second is the only one it
    cannot do. But it has to learn the address without fetching the file, so the index
    beside the text names it: the URL, the bytes, and the sha256 to check a download
    against.
    """
    stem = os.path.basename(rel)[:-4]
    folder = rel.split('/')[0]
    for key, row in manifest.items():
        if not key.startswith(folder + '/'):
            continue
        if '/text/' in key or key.endswith('.txt'):
            continue
        if os.path.splitext(os.path.basename(key))[0] == stem:
            return dict(url=f'{SITE}/docs/{key}', bytes=int(row['bytes']),
                        sha256=row['sha256'],
                        note='The publisher\'s own file. You can give this address to a '
                             'person to download even if it is too large for you to '
                             'fetch; the sha256 lets them check what they got.')
    return None


# Documents that are published but not copied into the build, and are the RIGHT artefact
# for what they hold. The annual reports are tables, and a table does not survive being
# flattened into a line of prose: 47 of the FY2022 report's 194 pages are essentially
# blank in `text/`, and the OCR rendering has content for 33 of them -- 866k characters
# against 448k. The fixed-width version keeps the column positions, which is the whole
# meaning of a financial table, and it was reachable and advertised nowhere.
EXTRA = [os.path.join(ROOT, 'sources', 'town-budget', 'pages', '*.ocr.txt')]


def sources():
    """(path on disk, published path) for everything worth splitting."""
    out = []
    for path in sorted(glob.glob(os.path.join(PUB, '**', '*.txt'), recursive=True)):
        out.append((path, os.path.relpath(path, PUB).replace(os.sep, '/')))
    for pattern in EXTRA:
        for path in sorted(glob.glob(pattern)):
            rel = os.path.relpath(path, os.path.join(ROOT, 'sources')).replace(os.sep, '/')
            out.append((path, rel))
    return out


def build(write=True):
    manifest = A.read_manifest()
    made, skipped = [], 0
    for path, rel in sources():
        size = os.path.getsize(path)
        if size <= LIMIT:
            skipped += 1
            continue
        text = open(path, encoding='utf-8', errors='replace').read()
        chunks = parts_of(text)
        folder = os.path.join(PUB, rel[:-4] + '.parts')
        index = dict(
            resource='text-parts',
            document=f'{SITE}/docs/{rel}',
            bytes=size,
            note=f'{rel} is {size // 1024}KB, which is more than some callers can fetch. '
                 f'These parts are the same text, split on page boundaries. Read the one '
                 f'you need; the pages each covers are given below.',
            count=len(chunks),
            parts=[])
        original = original_of(rel, manifest)
        if original:
            index['original'] = original
        if write:
            import shutil
            shutil.rmtree(folder, ignore_errors=True)
            os.makedirs(folder, exist_ok=True)
        for i, (body, first, last) in enumerate(chunks, 1):
            name = f'{i:03d}.txt'
            if write:
                with open(os.path.join(folder, name), 'w', encoding='utf-8') as fh:
                    fh.write(body)
            entry = dict(url=f'{SITE}/docs/{rel[:-4]}.parts/{name}',
                         bytes=len(body.encode('utf-8')))
            if first is not None:
                entry.update(first_page=first, last_page=last)
            index['parts'].append(entry)
        if write:
            with open(os.path.join(folder, 'index.json'), 'w') as fh:
                json.dump(index, fh, indent=1)
        made.append((rel, size, len(chunks)))
    return made, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    if args.check:
        made, _ = build(write=False)
        missing = [rel for rel, _, _ in made
                   if not os.path.exists(os.path.join(PUB, rel[:-4] + '.parts',
                                                      'index.json'))]
        if missing:
            print(f'{len(missing)} long document(s) have no parts published:')
            for r in missing[:8]:
                print('  ' + r)
            print('\n  Run: python3 scripts/split_large_text.py')
            return 1
        print(f'ok: {len(made)} long documents all have parts')
        return 0

    made, skipped = build()
    total = sum(n for _, _, n in made)
    print(f'{len(made)} documents over {LIMIT // 1024}KB, split into {total} parts')
    print(f'  {skipped} published text files were already small enough')
    for rel, size, n in sorted(made, key=lambda m: -m[1])[:8]:
        print(f'  {size / 1024:6.0f} KB -> {n:>2} parts  {rel}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
