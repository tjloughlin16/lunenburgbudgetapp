#!/usr/bin/env python3
"""Search the meeting archive, and always say how much of it was searched.

    python3 scripts/search_minutes.py "jersey"
    python3 scripts/search_minutes.py "para" --board school-committee --since 2025-07-01

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
"""
import argparse
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN = os.path.join(ROOT, 'sources', 'meetings')
TEXT = os.path.join(MIN, 'text')
DATASET = os.path.join(ROOT, 'sources', 'data', 'minutes-searchable.csv')
SITE = 'https://lunenburgbudgetproject.org'

# Written by scripts/extract_minutes.py, so they are OURS and not the document's. Counting
# them as text is the defect this file's docstring describes.
PAGE_MARKER = re.compile(r'^===PAGE \d+===$', re.M)


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('term', help='matched case-insensitively; a regex is allowed')
    ap.add_argument('--board', help='slug fragment, e.g. school-committee')
    ap.add_argument('--since', help='ISO date; only documents on or after it')
    ap.add_argument('--until', help='ISO date; only documents on or before it')
    ap.add_argument('--context', type=int, default=140, help='characters either side')
    ap.add_argument('--list-unsearchable', action='store_true',
                    help='print every in-scope document that cannot be searched')
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

    pat = re.compile(a.term, re.I)
    hits = 0
    for r in sorted([r for r in scope if r['_has_text']],
                    key=lambda r: (r['date'], r['board'])):
        body = body_of(r)
        found = list(pat.finditer(body))
        if not found:
            continue
        hits += 1
        print(f'\n{r["board"]} — {r["date"]} {r["kind"]}  ({len(found)} hit'
              f'{"s" if len(found) > 1 else ""})')
        print(f'  cite: {SITE}/docs/minutes/text/{r["_stem"]}.txt')
        print(f'  town: {r["url"]}')
        for m in found[:3]:
            lo = max(0, m.start() - a.context)
            print('   ... ' + ' '.join(body[lo:m.end() + a.context].split()))

    # Every in-scope document is settled into exactly one state before anything is printed,
    # so the numbers below cannot fail to add up to the scope.
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
    print(f'{hits} document(s) matched {a.term!r}'
          + (f'  [{where}]' if where else '  [whole archive]') + '.')

    n = len(scope)
    pct = (100.0 * len(searched) / n) if n else 0.0
    print(f'\nSEARCHED {len(searched):,} of the {n:,} document(s) in scope ({pct:.0f}%).')
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
