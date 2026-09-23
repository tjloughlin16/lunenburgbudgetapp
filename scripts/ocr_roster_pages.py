#!/usr/bin/env python3
"""Word geometry for every page that carries a department roster, found not chosen.

    python3 scripts/ocr_roster_pages.py [--fy 2016] [--dry-run]

TJ, 22 September 2026, after finding the Police roster in FY2016 and FY2025 by opening the
book while this project reported both years as unpublished:

    *"we HAVE to assume every department and every annual report contains the same
    information. That's the baseline. no more assuming the data isnt there. it IS there.
    it has been every single time. we just haven't found it."*

THE PAGE RANGES WERE TYPED BY HAND, and that is the whole defect. `fy2025.rosters.tsv`
covers pages 54-70; the Police roster is on page 79. Nothing was wrong with the reader,
the scan or the town -- the geometry for that page was never captured, so no amount of
fixing the parser could ever have found it. `fy2016.rosters.tsv` has the right page and
failed for the other reason: that year's roster carries no `Department Personnel:`
heading, so the trigger never fired.

So the pages are DERIVED from the text of the book: anything that looks like the start of
a roster, plus the pages that follow it while names keep coming. A year whose format
changes is then a year with different markers, not a year with no data.
"""
import argparse
import collections
import csv
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(ROOT, 'sources', 'town-budget', 'pages')
WORDS = os.path.join(ROOT, 'sources', 'town-budget', 'ocr', 'words')
PDFS = os.path.join(ROOT, 'sources', 'town-annual-reports', 'docs')
SWIFT = os.path.join(ROOT, 'scripts', 'ocr_words.swift')

# EVERY WAY A ROSTER HAS BEEN ANNOUNCED so far, across fifteen books. A new year that
# invents another one belongs here; it does not belong in a sentence saying the town
# stopped publishing.
START = re.compile(
    r'department personnel'
    r'|roster of the lunenburg fire'
    r'|patrol supervisors?\b'
    r'|patrol bureau'
    r'|patrol officers?\b'
    r'|reserve (?:intermittent|police) officers?'
    r'|call firefighters?\b'
    r'|^\s*administrative\s*$'
    r'|the technology team'
    r'|overview of our current', re.I)
# Pages that merely MENTION a roster word in prose are not roster pages. A roster page is
# dense with ranks and names; require several on the page.
RANK = re.compile(r'\b(?:Chief|Deputy|Lt\.?|Lieutenant|Sgt\.?|Sergeant|Det\.?|Detective'
                  r'|Ofc\.?|Off\.?|Officer|Captain|Capt\.?|Firefighter|FF|EMT|Paramedic'
                  r'|Director|Administrator|Coordinator)\b')
MIN_RANKS = 4

# THE OFFICIALS LISTING, TOLD APART BY WHAT IS ON IT rather than by where it sits. A page
# of the front-of-book listing states how each post is CONSTITUTED -- `(5 members)`,
# `3 year term` -- and a department's own roster never does. FY2011 has no word geometry
# at all, so `listing_pages` returns nothing for it and its page 8, `RESERVE POLICE
# OFFICERS`, would otherwise read as the Police Department's roster and be counted twice.
#
# A page cutoff was the first fix and it was wrong: FY2012 prints `Roster of the Lunenburg
# Fire Department` on page 23 and FY2013 its call list on page 24, well inside any front
# matter, so excluding by page number threw away three years of real rosters. Content, not
# position -- which is the same mistake as reading a heading's absence as a section's.
# `3 year term`, `(5 members)` -- and FY2011 writes it `REGISTRAR OF VOTERS-3 YRS`, which
# the first two patterns miss, so that page read as a Police roster.
CONSTITUTED = re.compile(r'\(\s*\d+\s+members?\b|\b\d\s*year\s+terms?\b'
                         r'|[-\s]\d+\s*YRS?\b', re.I)
MIN_CONSTITUTED = 2
DENSE_RANKS = 8


MAX_ROSTER_LINE = 70

# A ROSTER LINE NAMES A PERSON. FY2011 page 89 is the pay-grade schedule -- `Assistant
# Assessor`, `Council on Aging Director`, `Firefighter/EMT/Capt - Call/FT` -- forty lines
# of JOB TITLES with grades beside them and not one human being on the page. It is as
# rank-dense as any roster and it is a salary table, so it read as the FY2011 Police
# roster and put one officer in the series.
TITLE_WORD = set('''administrative administration assistant assessing assessor clerk
director outreach dispatcher coordinator inspector firefighter emt emt-i paramedic
call chief deputy capt captain lt lieutenant sgt sergeant det detective ofc off officer
head junior senior library treasurer collector tax town building dpw council aging
services emergency account principal custodian mechanic laborer operator secretary
supervisor superintendent technician manager agent nurse aide part time full shift
patrol bureau reserve intermittent police fire department personnel vacant vacancy
day evening night split community policing traffic k9 sro animal control'''.split())
WORDISH = re.compile(r"[A-Za-z][A-Za-z'\-.]*")


def _has_name(line):
    """Does this line name a person, as opposed to naming a job?

    SCANNED AS TOKENS, because a regex over PAIRS gets this wrong in a way that is easy to
    miss: `re.findall` does not overlap, so on `Chief James P. Marino` it matches
    `Chief James`, rejects it because `Chief` is a title, and never tries `James Marino`.
    Every Police roster in the archive is written rank-first, so that one detail hid all
    of them at once.

    Middle initials are dropped before pairing, so `James P. Marino` is `James` beside
    `Marino` rather than two failed pairs.
    """
    toks = [t for t in WORDISH.findall(line) if len(t.strip('.')) > 1]
    for a, b in zip(toks, toks[1:]):
        if not (a[:1].isupper() and b[:1].isupper()):
            continue
        if a.lower().strip('.') in TITLE_WORD or b.lower().strip('.') in TITLE_WORD:
            continue
        return True
    return False


def _rank_lines(lines):
    """How many lines are short enough to be a roster entry AND carry a rank."""
    # MEASURED AFTER COLLAPSING THE GUTTERS. FY2025 sets its patrol roster in three
    # columns, so `Sgt. John Morreale` and `Sgt. Vacant` and `Sgt. Paul Theodoulou` arrive
    # as one 132-character line that is thirty characters of text and a hundred of column
    # gap. Measuring it raw called the Police roster prose and dropped the page.
    return sum(1 for ln in lines
               if len(re.sub(r'\s+', ' ', ln).strip()) <= MAX_ROSTER_LINE
               and RANK.search(ln) and _has_name(ln))


def officials_pages(fy):
    """The ELECTED/APPOINTED OFFICIALS listing pages, which are NOT department rosters.

    They name reserve police officers, constables and inspectors as appointed POSTS, and
    `extract_personnel.py` already reads them. Counting them here as well put the FY2014
    Police roster at 62 and FY2023's at 53 -- the department's own roster plus the front
    of the book, added together.
    """
    sys.path.insert(0, os.path.join(ROOT, 'scripts'))
    import extract_personnel as P
    try:
        pages = set(P.listing_pages(fy))          # takes the YEAR, not a path
    except Exception:
        pages = set()
    return pages


def pages_with_rosters(fy):
    """{page: why} for every page of FY<fy> that carries roster-shaped content."""
    path = os.path.join(PAGES, 'FY%s.ocr.txt' % fy)
    if not os.path.exists(path):
        return {}
    by_page, page = collections.defaultdict(list), None
    for line in open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'^===PAGE (\d+)===', line)
        if m:
            page = int(m.group(1))
            continue
        if page:
            by_page[page].append(re.sub(r'^\s*\d+\|', '', line).rstrip())
    skip = officials_pages(fy)
    out = {}
    for p, lines in by_page.items():
        if p in skip or len(CONSTITUTED.findall('\n'.join(lines))) >= MIN_CONSTITUTED:
            continue
        text = '\n'.join(lines)
        # A ROSTER PAGE NEED NOT ANNOUNCE ITSELF. FY2013 prints its whole Fire roster on
        # page 26 as two columns of `J. Gregory Massak, Lieutenant/EMT` with NO heading
        # anywhere on the page -- the heading was on page 25 and the list simply runs on.
        # Requiring an opener on every page lost forty-odd firefighters in a year this
        # project then described as unpublished. So: an opener, OR enough rank-bearing
        # short lines that the page can be nothing else.
        dense = _rank_lines(lines) >= DENSE_RANKS
        if not START.search(text) and not dense:
            continue
        # A ROSTER IS SHORT LINES. FY2023 page 19 is the Town Manager's PROSE, listing
        # every position filled that year -- `Police Officers (3), Reserve Police Officer,
        # Facilities Director (2), Conservation Administrator...` -- and it matched four
        # rank words inside one paragraph. Counting ranks only on lines a roster could
        # actually be set in separates the two without naming either page.
        # A PAGE THAT ANNOUNCES A ROSTER IS A ROSTER PAGE, however short the list on it.
        # FY2022 prints `Roster of the Lunenburg Fire Department- 2022` at the foot of
        # page 85 with the Chief, the Deputy and nine career firefighters under it, and
        # then the book moves to the Police Department -- the call firefighters are not
        # in that year's report at all. Two rank-bearing lines is under the threshold, so
        # the page was skipped and the department published with ONE name against a
        # stated forty. The density test exists to reject PROSE that happens to contain
        # rank words, and prose does not carry the heading: FY2023 page 19, the one it
        # was written for, has the opener and ZERO rank lines.
        floor = 1 if START.search(text) else MIN_RANKS
        if _rank_lines(lines) < floor:
            continue
        m = START.search(text)
        out[p] = m.group(0).strip()[:40] if m else 'rank-dense, no heading'
    # A roster runs on. Take the page after any hit when it is also rank-dense, which is
    # how the Fire call list and the Police reserve list continue onto a second page.
    for p in sorted(out):
        nxt = p + 1
        if nxt in out or nxt not in by_page:
            continue
        if _rank_lines(by_page[nxt]) >= MIN_RANKS:
            out[nxt] = 'continuation'
    return out


def have(fy):
    """Pages already present in this year's word-geometry file."""
    path = os.path.join(WORDS, 'fy%s.rosters.tsv' % fy)
    if not os.path.exists(path):
        return set()
    with open(path, encoding='utf-8') as fh:
        return {int(r['page']) for r in csv.DictReader(fh, delimiter='\t')}


def pdf_for(fy):
    for name in sorted(os.listdir(PDFS)):
        if 'fy-%s-' % fy in name and 'addendum' not in name:
            return os.path.join(PDFS, name)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fy', action='append')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    fys = a.fy or [str(y) for y in range(2011, 2026)]
    total_missing = 0
    for fy in fys:
        want = pages_with_rosters(fy)
        if not want:
            print('FY%s  no roster-shaped page found -- LOOK AT THE BOOK' % fy)
            continue
        got = have(fy)
        missing = sorted(set(want) - got)
        total_missing += len(missing)
        print('FY%s  %d roster page(s); %d already read; MISSING %s'
              % (fy, len(want), len(set(want) & got), missing or 'none'))
        for p in missing:
            print('      p%-4d %s' % (p, want[p]))
        if missing and not a.dry_run:
            pdf = pdf_for(fy)
            if not pdf:
                print('      no PDF for FY%s' % fy)
                continue
            # CONTIGUOUS RUNS, not one span. FY2016 needs pages 67 and 90, and asking
            # for 67-90 reads twenty-four pages to get two.
            runs, run = [], [missing[0]]
            for a_, b_ in zip(missing, missing[1:]):
                if b_ == a_ + 1:
                    run.append(b_)
                else:
                    runs.append(run)
                    run = [b_]
            runs.append(run)
            for i, r in enumerate(runs):
                out = os.path.join(WORDS, 'fy%s.extra%d.tsv' % (fy, i))
                subprocess.run(['swift', SWIFT, pdf, out, str(r[0]), str(r[-1])],
                               check=False)
    if a.dry_run:
        print('\n%d page(s) of roster geometry have never been read.' % total_missing)
    return 0


if __name__ == '__main__':
    sys.exit(main())
