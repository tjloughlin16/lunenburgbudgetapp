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

DONE, DEFINED ONCE, HERE. A year is done when EVERY financial page the map holds for it
is `proven`. `unproven`, `refused` and `blocked` all mean not done, and are reported
separately because they need different work: unproven needs the ladder in
`notes/process/INGESTING-A-TABLE-FAMILY.md`, refused needs a layout read off the printed
header, blocked needs whatever the block says.
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
# Ordered worst-first: a year's next action is named by the most blocking state it has.
NOT_DONE = ['blocked', 'refused', 'unproven']

NEXT_ACTION = {
    'blocked': 'read what the block says, then the ladder (INGESTING-A-TABLE-FAMILY.md step 3)',
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


def is_done(c):
    return c['pages'] > 0 and c[DONE_STATE] == c['pages']


def worst(c):
    """The most blocking not-done state a year has, or None if done."""
    return next((s for s in NOT_DONE if c[s]), None)


def pick_next(by):
    """The year nearest to finishing. Fewest pages left, then newest -- so a year one
    page short is always next, and ties go to the year whose layout is freshest in mind."""
    open_years = [(fy, c) for fy, c in by.items() if not is_done(c)]
    if not open_years:
        return None
    return sorted(open_years, key=lambda kv: (kv[1]['pages'] - kv[1][DONE_STATE], -int(kv[0])))[0][0]


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

    states = NOT_DONE
    print('A year is DONE when every financial page it holds is `%s`.\n' % DONE_STATE)
    print('fy     pages  %s  %s  done' % (DONE_STATE.ljust(8), '  '.join(s.ljust(8) for s in states)))
    done = []
    for fy in sorted(by):
        c = by[fy]
        cells = '  '.join(str(c[s]).ljust(8) for s in states)
        flag = 'YES' if is_done(c) else ('<- next' if fy == nxt else '')
        print('%-6s %5d  %s  %s  %s' % (fy, c['pages'], str(c[DONE_STATE]).ljust(8), cells, flag))
        if is_done(c):
            done.append(fy)

    print('\n%d of %d years done: %s' % (len(done), len(by), ', '.join(done) or 'none'))
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
