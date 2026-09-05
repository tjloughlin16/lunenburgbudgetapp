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
SITE = 'https://lunenburgbudgetproject.org'


def index():
    """Every document the town published, whether or not we can read it."""
    rows = list(csv.DictReader(open(os.path.join(MIN, 'index.csv'))))
    for r in rows:
        stem = os.path.splitext(r['path'])[0] if r['path'].strip() else ''
        r['_stem'] = stem
        r['_txt'] = os.path.join(TEXT, stem + '.txt') if stem else ''
        r['_readable'] = bool(stem) and os.path.exists(r['_txt'])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('term', help='matched case-insensitively; a regex is allowed')
    ap.add_argument('--board', help='slug fragment, e.g. school-committee')
    ap.add_argument('--since', help='ISO date; only documents on or after it')
    ap.add_argument('--context', type=int, default=140, help='characters either side')
    a = ap.parse_args()

    rows = index()
    readable = [r for r in rows if r['_readable']]
    scope = readable
    if a.board:
        scope = [r for r in scope if a.board.lower() in r['_stem'].lower()]
    if a.since:
        scope = [r for r in scope if r['date'] >= a.since]

    pat = re.compile(a.term, re.I)
    hits = 0
    for r in sorted(scope, key=lambda r: (r['date'], r['board'])):
        body = open(r['_txt'], errors='replace').read()
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

    # Printed on EVERY run, hits or none. This is the whole reason the script exists.
    print(f'\n{"-" * 72}')
    print(f'{hits} document(s) matched {a.term!r}.')
    filters = [f'board~{a.board}' if a.board else '', f'since {a.since}' if a.since else '']
    where = ', '.join(f for f in filters if f)
    print(f'Searched {len(scope):,} of {len(rows):,} documents the town has published'
          + (f' (filtered: {where})' if where else '')
          + f'. {len(readable):,} of {len(rows):,} are readable at all.')
    unreadable = [r for r in rows if not r['_readable']]
    if unreadable:
        print(f'\n{len(unreadable)} document(s) CANNOT be searched. An empty result above')
        print('does not cover these, and "nobody said it" is not a conclusion available:')
        for r in unreadable[:20]:
            print(f'  {r["board"][:34]:<34} {r["date"]} {r["kind"]:<8} {r["url"]}')
        if len(unreadable) > 20:
            print(f'  ... and {len(unreadable) - 20} more')
    elif hits == 0:
        print('Every published document is readable, so an empty result here does mean')
        print('the term does not appear in the archive.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
