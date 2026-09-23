"""Every financial page in every annual town report, and whether anything has read it.

    python3 scripts/map_annual_report_pages.py
    python3 scripts/map_annual_report_pages.py --check

Writes `sources/data/annual-report-pages.csv`, newest report first.

WHY, IN TJ'S WORDS: *"i think we probalby need to amke sure we capture everything that
needs to be ingested from those reports then, directly in the backlog."*

The stabilization work showed the shape of the problem. A table family was worked for
weeks and a better one sat unread in the same reports -- not because anybody decided to
skip it, but because nothing anywhere said it existed. The backlog counted ROWS in
datasets that had already been built, so a table with no extractor contributed nothing to
it and was invisible by construction. A backlog that can only see work already started is
not a backlog.

This maps the other direction: from the PAGES, to what is on them, to whether any dataset
has taken anything from that page. What comes out is the real queue.

HOW A PAGE IS JUDGED READ. Most `report_*` tables carry the `page` they came from, so a
page is `read` when some dataset holds a row citing it. That is a coarse test and it is
honest about being coarse -- one row from a page marks the page read, and a table whose
bottom half was dropped still counts. It measures whether a page has been LOOKED at, not
whether it was exhausted; `verify_report_tables.py` is what measures the second thing.

WHAT `subject` IS. A guess, from the headings the page prints, and it says so. It exists
to group the queue -- twenty pages of `special-revenue` are one job, not twenty -- and
never to assert what a figure means. Where no heading survives the scan the subject is
`unknown`, which is a statement about our scan rather than about the page.

`reversed` is a page whose OCR came out upside down: its text is mirrored and no extractor
can see a figure on it at all. Those are not a reading job, they are a re-OCR job, and
mixing the two makes the queue lie about its own size.
"""
import argparse
import collections
import csv
import glob
import io
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_tables as T  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
DB = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
OUT = os.path.join(ROOT, 'sources', 'data', 'annual-report-pages.csv')

# THE SHARED PATTERN, not a local one. This file had its own, and it required cents --
# so every page of FY2025's Town Meeting warrant, which is nothing but `$50,000` and
# `$75,000`, counted as having no figures at all and was never classified as financial.
# The town writes round sums in the warrant and cents in the ledger tables, and a script
# that knows only one habit is blind to the other.
#
# Every money pattern in this repository should be this one. See pdf_tables.py.
MONEY = T.SCANNED_MONEY
MIN_FIGURES = 15

# Ordered: the first that matches wins, so the specific sits above the general.
SUBJECTS = [
    # TREASURER'S CASH FIRST, and the order is the whole point of this list.
    #
    # Every Treasurer's Cash page lists the stabilization funds by name -- `Bartholomew
    # Stabilization Fund`, `TD BankNorth Zoning Stabilization` -- so with
    # `trust-and-stabilization` above it, every one of them matched that instead and the
    # queue said the town published four cash pages in fifteen years. It publishes one
    # almost every year: FY2011, FY2013-FY2025, found by searching the OCR for the
    # heading directly.
    #
    # The rule the ordering encodes: the more SPECIFIC heading wins. "Treasurer's Cash
    # as of 6/30/2024" names one table; "stabilization" is a word that appears on any
    # page listing a fund, including this one.
    ('treasurers-cash', r"treasurer.{0,3}s\s+cash"),
    ('trust-and-stabilization',
     r'stabilization|trust\s+fund|held\s+by\s+other\s+banks|bartholomew'),
    ('special-revenue', r'special\s+revenue'),
    ('receivables', r'receivable'),
    # FY2025 p25 is headed exactly `BALANCE SHEET` and was landing in `unknown`,
    # because the pattern wanted the FY2011-FY2023 wording. The bare heading is
    # the newer one.
    ('balance-sheet',
     r'combined\\s+balance\\s+sheet|all\\s+fund\\s+types|^\\s*balance\\s+sheet\\s*$'),
    ('tax-collection', r'collection\s+of\s+taxes|taxes\s*&\s*excise|tax\s+liens'),
    ('debt', r'debt\s+(repayment|schedule|limit)|outstanding\s+debt|bonds?\s+payable'),
    # THE TOWN CHANGED THE TABLE AFTER FY2023, which is why the newest two years
    # looked like they had no budget in them at all. Through FY2023 the department
    # figures are a summary section headed `GENERAL FUND APPROPRIATIONS / SUMMARY &
    # CLASSIFICATION OF ACCOUNTS`; from FY2024 they are the warrant's `FY 2025 Omnibus
    # Budget` table -- Line No. | Account | VOTED -- and the old heading appears nowhere.
    #
    # Same data, different table, different section of the report. `omnibus` is the word
    # that finds the new one, and it has to sit HERE rather than in a new subject,
    # because a reader asking what the town appropriated does not care which layout the
    # year happened to use.
    ('appropriations',
     r'appropriat|budget\s+report|expenditures?\b|omnibus\s+budget'),
    ('payroll', r'gross\s+wages|payroll|salar(y|ies)'),
    ('valuation', r'valuation|assessed\s+value|new\s+growth'),
    ('elections', r'election|ballot|precinct'),
    ('vital-records', r'births?\b|deaths?\b|marriages?'),
    ('officials', r'town\s+officials|appointed|elected\s+officials'),
    ('capital', r'capital\s+(project|plan|outlay)'),
    ('enrollment', r'enrollment|mcas'),
]
SUBJECTS = [(k, re.compile(v, re.I)) for k, v in SUBJECTS]

# WHAT EACH SUBJECT WOULD BE WORTH, and WHY -- keyed to questions this project has
# already registered as unanswerable in `money-gaps.csv`, or to a page it already
# publishes. TJ: "can you classify the annual report info left to bee extract by
# importance you see? IS there anything that answers any open questions we have, or
# support anything we already report on?"
#
# The ranking is a JUDGEMENT and is written down here so it can be argued with rather
# than inferred from what somebody happened to work on next. `answers` names a registered
# gap wherever one exists, because a gap with a named remedy is a plan and one without is
# a grievance.
PRIORITY = {
    'special-revenue': (1,
        'The load-bearing one. CLAUDE.md rule 11: grants, circuit breaker, school choice, '
        'revolving funds and gifts pay for real staff and appear NOWHERE in the budget, so '
        'a line that rises because a grant ended looks identical to one that rises because '
        'the district grew. Closes the registered gaps "What any special revenue fund '
        'bought" and "Grants received in earlier years", and bears on "Which fund pays '
        'which post".'),
    'balance-sheet': (2,
        'The whole town in one statement, which this project does not have at all. Closes '
        '"What the town held town-wide at 30 June 2024 and 30 June 2025" and bears '
        'directly on "Why the Town\u2019s undesignated fund balance and DLS\u2019s free cash '
        'differ" \u2014 a discrepancy /free-cash currently records and cannot explain.'),
    'receivables': (3,
        'What is owed to the town and has not been collected. Thirty pages over twelve '
        'years, and nothing here measures it; it is the other half of the tax-collection '
        'picture the property-owners and tax-bill pages tell from the levy side.'),
    'trust-and-stabilization': (4,
        'The thread already being worked. Sixteen pages remain, and they are the years '
        'where the general Stabilization Fund is still missing from the series on '
        '/analysis/stabilization-funds.'),
    'tax-collection': (5,
        'Collections and liens by year. Supports the same reports as receivables and is '
        'the series behind "what the town actually took in" as against what it committed.'),
    'payroll': (6,
        'Gross wages by name already exist for fifteen years; these are the pages that '
        'extract did not reach. It bounds "Whether a budgeted position was filled" '
        'without settling it \u2014 a roster carries no FTE and no funding source.'),
    'valuation': (7,
        'Assessed value by class. /commercial-base and /property-owners are built on the '
        'state\u2019s certification of this; the town\u2019s own printing is the check on it.'),
    'capital': (8, 'Capital projects and what they cost. Bears on "Debt service by project".'),
    'appropriations': (9, 'Already the largest dataset here at 4,665 rows; these are stragglers.'),
    'enrollment': (10, 'DESE publishes this directly and is the better source.'),
    'elections': (11, 'Complete at 2,012 rows; not a money question.'),
    'vital-records': (12, 'Complete; not a money question.'),
    'treasurers-cash': (13, 'Now extracted by scripts/extract_treasurers_cash.py.'),
    'unknown': (14,
        'A statement about our SCAN, not about the page: the heading is what the scanner '
        'lost. These have to be looked at before they can be ranked.'),
}

FIELDS = ['fy', 'page', 'subject', 'priority', 'state', 'figures', 'figures_reversed',
          'read_by', 'heading', 'answers', 'document']


def unreversed(t):
    r = t[::-1]
    for a, b in (('S', '$'), ('E', '3'), ('Z', '2'), ('B', '8'), ("'", ',')):
        r = r.replace(a, b)
    return r


# WORDS DECIDE WHETHER A PAGE IS MIRRORED. NUMBERS CANNOT.
#
# The test used to be "more tokens look like money when reversed than look like money
# upright", and it is worthless, for a reason that is arithmetic rather than a tuning
# problem: `28,915,000` does not match the money pattern upright, because that pattern
# wants exactly two digits after the last separator — and REVERSED it is `000,519,82`,
# which does. So every figure printed in round thousands counts as evidence of
# reversal, and none of them counts as evidence against it.
#
# A debt schedule is nothing but round thousands. That is how "FIVE YEARS OUTSTANDING
# DEBT" came to be listed as mirrored in six different years while reading perfectly
# upright in the OCR — `28,915,000`, `15,000`, `31,763,200`. The queue then printed its
# heading through unreversed(), so it appeared in the backlog as `T83D GNIDNAT$TUO
# $RA3Y 3VIF` and looked exactly like the thing it was not. A derived classification
# quoted back as an observation, which is rule 13 in one line, and it sent two hours of
# re-OCR at seven reports that had nothing wrong with them.
#
# Mirrored TEXT is unambiguous in a way mirrored numbers never are: `Town` reverses to
# `nwoT`, and no page of English contains that. So look for common words, in both
# directions, and let the count decide. These nine appear on essentially every financial
# page the town prints, and a page carrying none of them either way is left `unread`
# rather than guessed at.
WORDS = ('the', 'and', 'total', 'town', 'fund', 'school', 'year', 'department', 'debt')
REVERSED_WORDS = tuple(w[::-1] for w in WORDS)


def reading_direction(texts):
    """`upright`, `reversed`, or None when the page says neither.

    Counts whole words rather than substrings: `eht` is inside nothing, but `dna` sits
    inside plenty of real tokens, and a substring test on short words finds itself.
    """
    toks = re.findall(r'[a-z]{3,}', ' '.join(texts).lower())
    fwd = sum(t in WORDS for t in toks)
    rev = sum(t in REVERSED_WORDS for t in toks)
    if fwd == rev:
        return None
    return 'reversed' if rev > fwd else 'upright'


# A PAGE IS READ WHEN SOMETHING EXTRACTED FIGURES FROM IT, and `report_` is a naming
# convention rather than a fact about a table. Ten tables carry `fy` and `page` and do not
# start with it -- `special_revenue_read`, `staff_roster_entries`, `stated_cuts`,
# `placement_counts` -- so 353 pages that had been read were counted as backlog, 50 of
# them in the one subject that looked like the largest thing left to do.
#
# THE EXCEPTION IS A CATALOGUE. `annual_report_survey` holds a row per page saying what is
# printed on it, which is how this map knows the pages exist at all. Counting it as a
# reading would mark every page in the archive read and leave a backlog of nothing --
# the same error in the other direction, and a far worse one, because an empty queue
# looks like success.
CATALOGUES = {'annual_report_survey'}


def read_pages():
    """{(fy, page): 'dataset, dataset'} for every page some dataset cites."""
    out = collections.defaultdict(set)
    if not os.path.exists(DB):
        return out
    db = sqlite3.connect('file:%s?mode=ro' % DB, uri=True)
    try:
        for (t,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            if t in CATALOGUES:
                continue
            cols = {r[1] for r in db.execute('PRAGMA table_info("%s")' % t)}
            if not {'fy', 'page'} <= cols:
                continue
            for fy, pg in db.execute('SELECT DISTINCT fy, page FROM "%s"' % t):
                try:
                    out[(int(fy), int(pg))].add(
                        t[len('report_'):] if t.startswith('report_') else t)
                except (TypeError, ValueError):
                    continue
    finally:
        db.close()
    return out


def subject_of(texts):
    joined = ' | '.join(texts)
    for name, pat in SUBJECTS:
        if pat.search(joined):
            return name
    return 'unknown'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    done = read_pages()
    rows = []
    for f in sorted(glob.glob(os.path.join(OCR, '*annual-town-report.tsv'))):
        m = re.search(r'fy-(\d{4})-', f)
        if not m:
            continue
        fy = int(m.group(1))
        doc = os.path.relpath(f, ROOT)
        by_page = collections.defaultdict(list)
        for b in T.read_boxes(f):
            by_page[b['page']].append(b)
        for page, boxes in sorted(by_page.items()):
            figs = rev = 0
            for b in boxes:
                t = (b['text'] or '').strip()
                if not t:
                    continue
                if MONEY.match(t):
                    figs += 1
                elif MONEY.match(unreversed(t)):
                    rev += 1
            if figs + rev < MIN_FIGURES:
                continue
            top = [' '.join((b['text'] or '').split())
                   for b in sorted(boxes, key=lambda b: -b['y'])[:10]]
            top = [t for t in top if len(t) > 6 and not MONEY.match(t)]
            # THE WORDS DECIDE, and only where they actually speak. `figures_reversed`
            # is still recorded because it is a real count, but it no longer classifies
            # anything: see reading_direction() for why a round-thousands table made it
            # say `reversed` about six perfectly upright debt schedules.
            direction = reading_direction(
                [' '.join((b['text'] or '').split()) for b in boxes])
            if direction == 'reversed':
                # Nothing on a mirrored page can be classified; its headings are as
                # mangled as its figures. Read them the other way round.
                top = [unreversed(t) for t in top]
            hits = done.get((fy, page), set())
            state = 'read' if hits else ('reversed' if direction == 'reversed' else 'unread')
            subj = subject_of(top)
            pri, why = PRIORITY.get(subj, (99, ''))
            rows.append(dict(
                fy=fy, page=page, subject=subj, priority=pri, answers=why, state=state,
                figures=figs, figures_reversed=rev,
                read_by=', '.join(sorted(hits)),
                heading=(top[0] if top else '')[:60], document=doc))

    # PRIORITY FIRST, then newest. The queue is meant to be read top-down.
    rows.sort(key=lambda r: (r['priority'], -r['fy'], r['page']))
    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    wr.writeheader()
    wr.writerows(rows)
    text = buf.getvalue()

    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if cur != text:
            print('STALE %s -- run: python3 scripts/map_annual_report_pages.py'
                  % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('ok -- %d financial pages mapped across %d reports'
              % (len(rows), len({r['fy'] for r in rows})))
        return 0

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(text)
    st = collections.Counter(r['state'] for r in rows)
    print('wrote %s -- %d financial pages across %d reports'
          % (os.path.relpath(OUT, ROOT), len(rows), len({r['fy'] for r in rows})))
    print('  read %d, unread %d, reversed %d'
          % (st['read'], st['unread'], st['reversed']))
    print()
    print('  what is NOT yet ingested, by subject:')
    todo = collections.Counter(r['subject'] for r in rows if r['state'] != 'read')
    for s, n in sorted(todo.items(), key=lambda kv: PRIORITY.get(kv[0], (99,))[0]):
        yrs = sorted({r['fy'] for r in rows
                      if r['subject'] == s and r['state'] != 'read'})
        print('    %2d. %-24s %3d pages  FY%d-FY%d'
              % (PRIORITY.get(s, (99,))[0], s, n, yrs[0], yrs[-1]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
