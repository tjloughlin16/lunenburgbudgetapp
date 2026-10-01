#!/usr/bin/env python3
"""WHICH ANNUAL REPORT YEARS ARE DONE, AND WHICH ONE IS NEXT. Start here.

    python3 scripts/annual_report_progress.py            # the board
    python3 scripts/annual_report_progress.py --next     # just the next year, for a script
    python3 scripts/annual_report_progress.py --check    # fail if the page map is stale

WHY THIS EXISTS, AND IT IS NOT CONVENIENCE. On 1 October 2026 TJ asked what years were
fully done and which to process next. Answering it took eleven tool calls and produced
TWO WRONG ANSWERS before the right one:

  * "FY2022 is the only year closed" -- from grepping COMMIT MESSAGE WORDING. An
    instrument's silence reported as a fact about the work. Rule 13c.
  * "no year is fully done, FY2024 is best at 22%" -- from ROW-level check status, which
    is not how this project defines a finished year. It defines it per PAGE: commit
    595148b1, "FY2025 is read: 23 of 23 pages, every one tied to arithmetic the page
    states". A year can be DONE with most of its rows still `check failed`, because the
    page state asks whether the page closed on an identity it prints about itself and
    `verify_report_tables.py` asks whether the table was exhausted. Two questions.

TJ: *"I don't understand. We already finished this year."* He was right both times, and
the cost was about an hour in which a year could have been processed instead.

The learning loop in `notes/PLAN-ANNUAL-REPORTS-TO-ZERO.md` entry 7 already names why
writing the fact down is not enough: *"the process doc had the fact and not the GATE. A
question with no consequence attached gets answered and walked past."* So this is the
gate. One command, one definition of done, and it refuses to answer off a stale map --
because every defect in that plan's own table was a stale instrument answering
confidently.

DONE, DEFINED ONCE, HERE. A year is done when every financial page the map holds for it
is `proven` OR `blocked`. `unproven` and `refused` are the two states that mean WORK IS
LEFT, and they are reported separately because they need different work: unproven needs
the ladder in `notes/process/INGESTING-A-TABLE-FAMILY.md`, refused needs a layout read off
the printed header.

WHY `blocked` COUNTS AS CLOSED AND IS STILL PRINTED ON EVERY ROW. The first version of
this script counted `blocked` as not done, which contradicted the register it reads from.
`map_annual_report_pages.blocked_pages()` says in its own docstring:

    HARD BLOCKED IS NOT UNFINISHED. TJ, 28 September 2026, on the FY2023 receipts page:
    "we need to mark it as TOO BLURRY and call it HARD BLOCKED. and move on."
    ... leaving both in one bucket means the backlog never stops containing the second
    kind -- every pass rediscovers it, re-renders it, and re-concludes it.

That is exactly what the old definition bought. FY2023 sat at 34 of 35 pages with page 25
hard blocked since 28 September, so the board named it NEXT; on 1 October an agent spent a
session re-extracting the embedded bitmap, re-measuring its grid, re-rendering it at 7x,
13x and 20x and re-reaching the conclusion already written in `page-blocked.csv` -- that
792x612 pixels across a landscape page of ~150 line items does not carry the digits. It
also re-checked the two publisher addresses: `DocumentCenter/View/4131` is now 404 and
`ArchiveCenter/ViewFile/Item/160` returns 18,274,143 bytes, byte-for-byte our copy. There
is no better scan to fetch. Nothing about the archive moved, which is the definition of
work the register existed to prevent.

**A blocked page is NEVER called proven.** Its own column stays on the board, a done year
carrying one is flagged `YES*` and not `YES`, and the pages are named under the board with
the reason and what would remove the block. The claim being made is *this year holds
nothing anybody can still do*, not *this year is fully read* -- rule 7's distinction
between a measurement and what it is taken to mean, pointed at our own progress.
"""

import argparse
import collections
import csv
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP = os.path.join(ROOT, 'sources', 'data', 'annual-report-pages.csv')
MAPPER = os.path.join(ROOT, 'scripts', 'map_annual_report_pages.py')

DONE_STATE = 'proven'
# A page in one of these needs nobody to do anything further: `proven` closed on the
# page's own arithmetic, `blocked` is a document a person looked at and could not read.
CLOSED = ['proven', 'blocked']
# Ordered worst-first: a year's next action is named by the most blocking state it has.
# `blocked` is NOT here -- it is not an action, which is the whole point of the state.
NOT_DONE = ['refused', 'unproven']
# What the board prints, in this order. `blocked` is shown on every row so a year that
# closed carrying one can never be mistaken for a year that was fully read.
COLUMNS = ['proven', 'blocked', 'refused', 'unproven']

BLOCKED_REGISTER = os.path.join(ROOT, 'sources', 'data', 'page-blocked.csv')

NEXT_ACTION = {
    'refused': 'read the printed column header off the page and write the layout down (rule 13b)',
    'unproven': 'run the extractor, read the REFUSALS, then the six-check ladder, cheapest first',
}


def load():
    if not os.path.exists(MAP):
        sys.exit('%s does not exist. Run: python3 scripts/map_annual_report_pages.py' % MAP)
    with open(MAP, newline='', encoding='utf-8-sig') as fh:
        return list(csv.DictReader(fh))


def map_is_stale():
    """None when fresh, else why. The map is derived; a stale one reads as absence."""
    r = subprocess.run([sys.executable, MAPPER, '--check'],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode == 0:
        return None
    return (r.stdout + r.stderr).strip() or 'map_annual_report_pages.py --check exited %d' % r.returncode


def tally(rows):
    by = collections.defaultdict(collections.Counter)
    for r in rows:
        fy = (r.get('fy') or '').strip()
        if not fy:
            continue
        by[fy][(r.get('state') or '').strip() or 'blank'] += 1
        by[fy]['pages'] += 1
    return by


def closed(c):
    """Pages nobody can still act on: proved, or hard blocked and registered as such."""
    return sum(c[s] for s in CLOSED)


def is_done(c):
    return c['pages'] > 0 and closed(c) == c['pages']


def worst(c):
    """The most blocking ACTIONABLE state a year has, or None if nothing is left."""
    return next((s for s in NOT_DONE if c[s]), None)


def blocked_rows():
    """The register itself, so a closed year's blocks are NAMED and not just counted.

    A count of hard-blocked pages with no reason beside it is the bare number rule 7b
    forbids: a reader cannot tell a page nobody could read from a page nobody tried.
    """
    out = collections.defaultdict(list)
    if not os.path.exists(BLOCKED_REGISTER):
        return out
    with open(BLOCKED_REGISTER, newline='', encoding='utf-8-sig') as fh:
        for r in csv.DictReader(fh):
            fy = (r.get('fy') or '').strip()
            if fy:
                out[fy].append(r)
    return out


def pick_next(by):
    """The year nearest to finishing. Fewest pages LEFT TO ACT ON, then newest -- so a
    year one page short is always next, and ties go to the year whose layout is freshest
    in mind. A hard-blocked page is not a page left: counting it here is what made the
    board name FY2023 as next for three days after the only thing left on it was a scan
    nobody can improve."""
    open_years = [(fy, c) for fy, c in by.items() if not is_done(c)]
    if not open_years:
        return None
    return sorted(open_years, key=lambda kv: (kv[1]['pages'] - closed(kv[1]), -int(kv[0])))[0][0]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--next', action='store_true', help='print only the next year to process')
    ap.add_argument('--check', action='store_true', help='exit non-zero if the page map is stale')
    a = ap.parse_args()

    stale = map_is_stale()
    if a.check:
        if stale:
            sys.exit('STALE: the page map no longer reproduces, so every figure below would\n'
                     'be about a map and not about the archive. Rebuild it first.\n  %s' % stale)
        print('ok -- the page map reproduces; the board below is current')
        return 0

    by = tally(load())
    nxt = pick_next(by)

    if a.next:
        if stale:
            sys.exit('STALE page map; refusing to name a year off it.\n  %s' % stale)
        print(nxt or '')
        return 0 if nxt else 1

    if stale:
        print('*** THE PAGE MAP IS STALE -- everything below describes the map, not the')
        print('*** archive. Check the instrument before you debug the data.')
        print('***   %s\n' % stale)

    print('A year is DONE when every financial page it holds is `proven` or `blocked`.')
    print('`blocked` is a page a PERSON read and could not -- it is closed, never proven.\n')
    print('fy     pages  %s  done' % '  '.join(s.ljust(8) for s in COLUMNS))
    done, with_blocks = [], []
    for fy in sorted(by):
        c = by[fy]
        cells = '  '.join(str(c[s]).ljust(8) for s in COLUMNS)
        if is_done(c):
            flag = 'YES*' if c['blocked'] else 'YES'
        else:
            flag = '<- next' if fy == nxt else ''
        print('%-6s %5d  %s  %s' % (fy, c['pages'], cells, flag))
        if is_done(c):
            done.append(fy)
            if c['blocked']:
                with_blocks.append(fy)

    print('\n%d of %d years done: %s' % (len(done), len(by), ', '.join(done) or 'none'))

    if with_blocks:
        reg = blocked_rows()
        print('\nYES* -- closed, but NOT fully read. These pages cannot be read at all:')
        for fy in with_blocks:
            for r in sorted(reg.get(fy, []), key=lambda r: int(r.get('page') or 0)):
                print('  FY%s p%-4s %s' % (fy, r.get('page', '?'), r.get('reason', 'blocked')))
                if r.get('closes'):
                    print('      closes: %s' % r['closes'])
            if not reg.get(fy):
                print('  FY%s -- %d blocked page(s), NOT in %s. Register them.'
                      % (fy, by[fy]['blocked'], BLOCKED_REGISTER))
    if nxt:
        c = by[nxt]
        left = c['pages'] - c[DONE_STATE]
        w = worst(c)
        print('\nNEXT: FY%s -- %d of %d pages left (%s).' % (nxt, left, c['pages'], w))
        print('  %s' % NEXT_ACTION.get(w, 'see notes/PLAN-ANNUAL-REPORTS-TO-ZERO.md'))
        print('  The plan: notes/PLAN-ANNUAL-REPORTS-TO-ZERO.md (phases, and the learning loop)')
        print('  The loop: notes/process/INGESTING-A-TABLE-FAMILY.md (score, map, refusals, ladder)')
    else:
        print('\nEvery year is done. Nothing to pick.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
