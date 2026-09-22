#!/usr/bin/env python3
"""Where every figure about a town department or board comes from, department by department.

    python3 scripts/build_town_data_provenance.py
    python3 scripts/build_town_data_provenance.py --check

Writes `notes/reference/TOWN-DATA-PROVENANCE.md`.

TJ, 21 September 2026: *"did you describe how each board's/dept's data is fetched so we
remember in the future? provenance and all that"*. Partly, and in the wrong places. Every
generator documents itself in its own docstring and every dataset has a line in the source
catalogue -- but a person asking *what do we know about the Fire Department and how do we
know it* had to read five files and join them in their head.

GENERATED, NEVER MAINTAINED, for the reason rule 2 gives: a hand-written inventory of
one's own datasets is the thing most certain to be wrong within a month, and this one
would be wrong in the direction that matters -- claiming coverage that has gone.

WHAT IT RECORDS FOR EACH DEPARTMENT AND BOARD

  * WHICH DATASET holds each kind of figure -- money, posts, staffing, named roster.
  * WHICH YEARS are actually in it, counted from the rows rather than from the plan.
  * WHAT PROVES IT. Every one of these datasets carries a check the DOCUMENT offers about
    itself: group totals against the printed grand total, a heading stating a membership
    against the names beneath it, a stated strength against a named roster. The state of
    that check per year is the honest answer to "can I quote this", and it is repeated
    here so nobody has to go and find it.
  * WHAT IS MISSING, and whether it is missing from the town or from us. Those are
    different facts and this project has confused them repeatedly -- most of today, in
    fact: `the town does not print who works there` was our silence, not theirs.
"""
import argparse
import collections
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

import town_budget_data as D                                    # noqa: E402

DATA = os.path.join(ROOT, 'sources', 'data')
OUT = os.path.join(ROOT, 'notes', 'reference', 'TOWN-DATA-PROVENANCE.md')

SOURCES = [
    ('money — what Town Meeting voted', 'report-appropriations.csv',
     'scripts/extract_tables.py appropriations',
     'the omnibus budget in each annual town report — THE YEAR AHEAD, so the FY2024 book '
     'carries the FY2025 budget',
     'the twelve group totals against the grand total the same page prints'),
    ('posts — every elected seat, appointed seat and officer', 'town-personnel.csv',
     'scripts/extract_personnel.py',
     'the ELECTED OFFICIALS and APPOINTED OFFICIALS listing, nine pages a year',
     'a heading stating a membership against the names printed beneath it'),
    ('staffing — what a department says it employs', 'department-staffing.csv',
     'scripts/extract_department_staffing.py',
     'the prose of each department’s own report; no heading names it in any year',
     'none available except where a roster exists to compare against'),
    ('roster — staff by name', 'department-rosters.csv',
     'scripts/extract_department_rosters.py',
     'the Police `Department Personnel` and Fire `Roster of the Lunenburg Fire '
     'Department` pages, both set in two columns',
     'the named roster against the strength the department states in prose'),
]


# HOW EACH ONE IS PRINTED, AND WHAT MAKES IT HARD. TJ: *"for provenance, did you capture
# the complexities of getting the satffing per board? Some have tables. some in prose.
# keeping track of all that can help us in the future"*. This is that -- and it is the part
# that cannot be derived, because it is what was learned by getting each one wrong. The
# counts elsewhere in this file come off the data; these came off the pages.
FORMS = [
    ('Fire Department', 'BOTH — prose and a named table',
     'A sentence states strength as a count plus a RANGE (`10 Career and 30-35 On Call/Per '
     'Diem`), and a `Roster of the Lunenburg Fire Department` names everyone a few pages '
     'later, in two columns split A Shift / B Shift, then Call Firefighters.',
     'The two disagree by seven to twelve in most years and are NOT reconciled — rule 13a. '
     'The roster is two-column, so it needs the word geometry; read as flat lines the A '
     'and B shift names merge into one person. Rank comes before the name here (`Scott '
     'Dillon, Lieutenant/EMT` puts it after) so both forms are parsed.'),
    ('Police Department', 'a named table only',
     'A `Department Personnel:` heading, then Administration, the Patrol Bureau split into '
     'Day / Evening / Split shifts, the Investigative Bureau and the Community Policing '
     'Bureau, every officer by rank.',
     'Two columns, same as Fire. States no total anywhere, so there is NOTHING to check the '
     'roster against — where Fire has a stated strength to disagree with, Police has only '
     'the names. A short year therefore looks identical to a small year: FY2024 reads 7 '
     'officers against 25 the year before, and that is a page this reader did not find.'),
    ('Department of Public Works', 'prose only, an establishment post by post',
     '`The staff consists of one Director, one Executive Assistant (shared with the '
     'Facilities Department), one Highway Superintendent, 5 Heavy Equipment Operators...` '
     '— counts as words AND numerals in the same sentence, wrapping across three lines.',
     'NOT a headcount and not comparable to Fire\u2019s. FY2023 says `5 Heavy Equipment '
     'Operators`; FY2024 says `3 Heavy Equipment Operators, 2 Driver/Laborers`. Read as '
     'counts that is two operators lost; read as printed it is the same five people with '
     'two titles reclassified. The sentence is stored verbatim for exactly this reason.'),
    ('Building Department', 'prose, a list of names inline',
     '`The Building Department consists of the following personnel:` followed by names.',
     'Neither a count nor a table. Captured as a statement with `parsed=no` — evidence the '
     'town said something, which is not a number.'),
    ('Boards and committees', 'a listing, nine pages a year',
     'ELECTED OFFICIALS and APPOINTED OFFICIALS, each post with its holders and their '
     'term-expiry years, and its own membership stated in the heading.',
     'The heading is the CHECK: `COUNCIL ON AGING-(11 members)` should be followed by '
     'eleven names. But the heading is stated four different ways — `(5 members)`, `3 year '
     'terms` PLURAL, `(5 members as of Nov. 2021)` with text before the bracket, and `(no '
     'less than 5 and no more than 22 members)` which is a RANGE and not a size. Each of '
     'those four, missed, turned a heading into a person and gave the post above it '
     'somebody else\u2019s members.'),
    ('every other department', 'nothing published',
     'No roster, no establishment sentence, no count.',
     'The gross-wages list tagged each name with a department through FY2016 and stopped. '
     'So a DPW labourer, a library assistant and a town hall clerk appear in no published '
     'headcount at all after that year.'),
]


# THE SAME THING FOR THE MONEY, because the budget tables were read wrong in more ways than
# the staffing was. TJ: *"same with stabilization problems"*, *"and town budget info"*.
MONEY_TRAPS = [
    ('the omnibus budget', 'THE BOOK IS NOT THE YEAR',
     'The omnibus printed in an annual report is the year AHEAD: the FY2024 book carries '
     '`FY 2025 Omnibus Budget`, voted that spring. Reading a book\u2019s omnibus as its own '
     'year puts every figure one year out, and FY2024\u2019s own budget is in the FY2023 '
     'book, which is why it read as absent for months.'),
    ('the omnibus budget', 'THE TOTALS NEST',
     '`Total Protection` sums no line at all — it sums Police, Fire, Radio Watch and Other '
     'Protection, each of which sums its own lines. A flat walk hands it an empty run and '
     'reports a $4.6M failure at the one place the table is perfectly readable.'),
    ('the omnibus budget', 'A NUMBERED ROW IS A LINE, NOT A TOTAL',
     'Across every omnibus year, 254 of 255 recognised subtotals carry no line number. The '
     'one that did was two consecutive $4,000.00 items where the first was read as the '
     'second\u2019s total.'),
    ('the omnibus budget', 'A GAP IN THE NUMBERING IS NOT A MISSING ROW',
     'FY2024 reads all 109 lines and ties all nineteen printed totals while failing to read '
     'twenty of the line NUMBERS beside them — they sit in their own narrow column and '
     'Vision drops them. Only fail on numbering when the arithmetic does not already prove '
     'completeness.'),
    ('the omnibus budget', 'EVERYTHING ABOVE THE HEADING IS A DIFFERENT TABLE',
     'FY2023\u2019s omnibus starts halfway down page 164; above it sits the capital plan '
     'with its own `TOTAL: $1,360,500.00`. Ten of its rows summed as omnibus lines produced '
     'a $5.6M failure against a table nobody was extracting.'),
    ('any scanned money column', 'A FIGURE MUST BE TAKEN WHOLE',
     '`$497,155.24` scans as `$497.155.24` and an unanchored pattern returns `$497.15` AND '
     '`5.24` — two well-formed figures, both wrong, both summed. 1,098 lines across the '
     'sixteen reports, 1,945 sub-$10 fragments all counted as money.'),
    ('any scanned money column', 'A LOST SEPARATOR LEAVES FIVE DIGITS',
     '`$161,942.40` scans as `161.94240`. Groups run in threes and cents in twos, so the '
     'mark is the lost thousands separator — read flat it is $16,194,240 in a town whose '
     'whole budget is $42M.'),
    ('any scanned money column', 'THE LAST SEPARATOR IS NOT THE DECIMAL POINT',
     '`$50,000` read that way is fifty dollars — a thousandfold error, silent, in a figure '
     'the town prints all through its warrant. What follows the mark decides: two digits is '
     'a decimal, three is a group separator.'),
    ('any scanned money column', 'NOTHING HERE IS A HUNDRED BILLION DOLLARS',
     'Merged cells produced $2,254,933,999,368,739,225,600 in FY2025\u2019s debt schedule, '
     'which then matched a grand total read the same broken way, so the year PASSED its '
     'check. Two pieces of nonsense agreeing is a check with no power to fail.'),
    ('the omnibus budget', 'SOME OF THE ERROR IS THE TOWN\u2019S',
     'FY2022 and FY2023 both print `Total General Government` 80 cents under their own '
     'lines, and in both the odd amount is on `Town Clerk Salary`. FY2022 prints `Total '
     'Health & Sanitation` 30 cents under its five lines and foots its GRAND total on the '
     'correct figure. Recorded as `attested` rows in `table-corrections.csv` so nobody '
     're-reads those pages hunting an OCR fault that was never there.'),
    ('the stabilization funds', 'A BARE `STABILIZATION` IS NOT THE GENERAL FUND',
     'FY2011\u2013FY2013 print `TD BankNorth Stabilization`, which is ZONING: $226,821.90, '
     'Zoning\u2019s own opening balance. Publishing it as the general Stabilization Fund '
     'was caught one step before shipping.'),
    ('the stabilization funds', 'THE LETTERS ARE NOT ALWAYS LATIN',
     'FY2023 prints `Bartholomew - \u041e\u0420\u0415\u0412` where all four characters '
     'are CYRILLIC. It looks identical to OPEB, compares equal to nothing, and cost that '
     'fund a year. Only the codepoints show it.'),
    ('the stabilization funds', 'THE LAYOUT IS A HYPOTHESIS THE DOCUMENT TESTS',
     'Nine columns read off FY2014 were proposed for four other years; FY2015 and FY2016 '
     'accepted them, FY2017 and FY2022 refused. And ONE REPORT CAN HOLD TWO LAYOUTS: FY2023 '
     'prints a fourteen-column trust summary and an eight-column `held by other banks` '
     'table, so a layout keyed by year alone is always wrong about one of them.'),
    ('any scanned table', 'MEASURE THE PAGE, DO NOT TUNE A CONSTANT',
     'A scan is slightly turned, so a row\u2019s observations do not share a `y`. The '
     'rotation is recoverable from the page — the median slope between each figure and its '
     'nearest neighbour, \u22120.01033 from 158 pairs on FY2020 page 41 — and the row band '
     'is half the page\u2019s own row pitch. No tolerance works: at 0.004 two funds merge, '
     'at 0.003 one splits from its own account number.'),
    ('any scanned page', 'THE RENDERER CAN CLIP A FIFTH OF THE PAGE',
     '`PDFPage.bounds(for:)` applies `/Rotate` and `PDFPage.draw(with:to:)` does not, so a '
     'canvas sized for one and filled from the other lost about 20% of every landscape '
     'document — identically at 2x and 4x, which is why resolution never fixed it.'),
    ('any OCR box', 'A LINE BOX CANNOT SEE A COLUMN',
     'Vision returns one observation per LINE, so on a two-column page its box spans both: '
     '27 observations for 27 lines, every x-centre between 0.495 and 0.500. '
     '`ocr_words.swift` asks for a box per WORD, and the column break is then measurable — '
     'median word gap 0.0028 of the page, a break over 0.05.'),
]


def read(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return []
    with open(p, encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def span(years):
    ys = sorted({int(y) for y in years if str(y).isdigit()})
    if not ys:
        return '—', 0
    runs, start, prev = [], ys[0], ys[0]
    for y in ys[1:]:
        if y != prev + 1:
            runs.append((start, prev))
            start = y
        prev = y
    runs.append((start, prev))
    return ', '.join('FY%d' % a if a == b else 'FY%d–FY%d' % (a, b)
                     for a, b in runs), len(ys)


def build():
    budget = D.load()
    personnel = read('town-personnel.csv')
    staffing = read('department-staffing.csv')
    rosters = read('department-rosters.csv')

    t = ['# Where every figure about a town department comes from\n',
         '\nGenerated by `scripts/build_town_data_provenance.py`. Do not edit — the '
         'counts are read off the datasets, so a coverage claim here cannot outlive the '
         'data behind it.\n']

    t.append('\n## The four sources, and what each one proves\n\n'
             '| what | dataset | written by | read from | what checks it |\n'
             '|---|---|---|---|---|\n')
    for what, ds, gen, frm, chk in SOURCES:
        t.append('| %s | `%s` | `%s` | %s | %s |\n' % (what, ds, gen, frm, chk))

    t.append('\n## How each one is printed, and what makes it hard\n\n'
             'The counts in this file are derived from the data. This table is not — it is '
             'what was learned by getting each of these wrong, and it is the part that '
             'saves the next reader a day.\n\n'
             '| department | form | how it is printed | what to watch |\n|---|---|---|---|\n')
    for dept, form, printed, watch in FORMS:
        t.append('| %s | %s | %s | %s |\n' % (dept, form, printed, watch))

    t.append('\n## Reading the money, and what goes wrong\n\n'
             'Same kind of table, for the budget and the funds. Every line here is a defect '
             'that reached a figure before it was caught.\n\n'
             '| where | the trap | what happened |\n|---|---|---|\n')
    for where, trap, what in MONEY_TRAPS:
        t.append('| %s | %s | %s |\n' % (where, trap, what))

    # ---- money, by department -------------------------------------------------------
    t.append('\n## Money, department by department\n\n'
             'The omnibus budget in an annual report is the year AHEAD. Detail reconciles '
             'for the three years below; every other year has a printed grand total and '
             'no department breakdown read yet.\n\n'
             '| department | years with a figure | FY%d | check |\n|---|---|---:|---|\n'
             % budget['detail_years'][-1])
    for slug, name, _p in D.GROUPS:
        years = [y for y in budget['detail_years'] if budget['groups'][y].get(slug)]
        sp, _n = span(years)
        last = budget['groups'][budget['detail_years'][-1]].get(slug)
        rc = budget['reconcile'][budget['detail_years'][-1]]
        t.append('| %s | %s | $%s | %s |\n'
                 % (name, sp, format(int(last or 0), ','),
                    'group totals tie to the printed grand total'
                    if abs(rc['difference']) < 0.01 else
                    'ties to %+.2f — the town’s own arithmetic' % rc['difference']))
    t.append('\nThe voted TOTAL is held for %s. FY2026 is a total and nothing else: the '
             'FY2025 report prints Article 10 as prose and no department table exists for '
             'it in any form.\n' % span(budget['totals'])[0])

    # ---- posts ----------------------------------------------------------------------
    by_post = collections.defaultdict(list)
    for r in personnel:
        by_post[r['post']].append(r)
    checks = collections.Counter(r['size_check'] for r in personnel)
    t.append('\n## Posts and boards\n\n`town-personnel.csv`, %s, %s rows across %s '
             'distinct posts. Checks: %s checked, %s check failed, %s no check — and '
             'nothing may be counted without splitting on that column.\n'
             % (span([r['fy'] for r in personnel])[0], format(len(personnel), ','),
                len(by_post), checks['checked'], checks['check failed'],
                checks['no check']))
    t.append('\n| board, committee or post | years listed | how it is filled | states its size |\n'
             '|---|---|---|---|\n')
    for post in sorted(by_post):
        rs = by_post[post]
        sp, _n = span([r['fy'] for r in rs])
        kind = collections.Counter('%s %s' % (r['section'], r['kind']) for r in rs)
        stated = next((r['stated_members'] for r in rs if r['stated_members']), '')
        t.append('| %s | %s | %s | %s |\n'
                 % (post, sp, kind.most_common(1)[0][0], stated or 'no'))

    # ---- staffing and rosters -------------------------------------------------------
    t.append('\n## Staffing, where a department states it\n\n'
             '| department | years | how it states it |\n|---|---|---|\n')
    by_dept = collections.defaultdict(list)
    for r in staffing:
        by_dept[r['department']].append(r)
    for dept in sorted(by_dept):
        rs = by_dept[dept]
        sp, _n = span([r['fy'] for r in rs])
        kinds = sorted({r['measure'] for r in rs if r['measure']}) or ['prose, not counted']
        t.append('| %s | %s | %s |\n' % (dept, sp, '; '.join(kinds)))

    t.append('\n## Named rosters\n\n'
             '| department | years | names | agrees with the stated strength |\n'
             '|---|---|---:|---|\n')
    rc = collections.Counter((r['fy'], r['department']) for r in rosters)
    agree = {(r['fy'], r['department']): r['roster_check'] for r in rosters}
    for dept in sorted({d for _f, d in rc}):
        years = [f for f, d in rc if d == dept]
        sp, _n = span(years)
        ok = sum(1 for f in years if agree.get((f, dept)) == 'checked')
        t.append('| %s | %s | %s | %s of %s years |\n'
                 % (dept, sp, sum(n for (f, d), n in rc.items() if d == dept), ok,
                    len(years)))

    t.append('\n## What is missing, and from whom\n\n'
             '- **FY2011–FY2015 posts.** Ours. Those reports print the listing in a layout '
             'that states no membership anywhere, so the check that makes it readable does '
             'not exist in them and the reader refuses rather than guesses.\n'
             '- **Department detail for FY2026.** The town’s. Article 10 is printed as '
             'prose and no department figures appear in any form.\n'
             '- **Headcount for every department except Police, Fire and the schools.** '
             'The town’s, but only partly: departments describe their staffing in prose, '
             'in whichever form that year’s department head chose — a count, a range, an '
             'establishment post by post, a list of names. Those are different quantities '
             'and none of them is FTE.\n'
             '- **Which fund pays which post.** The town’s, and nothing published closes '
             'it. See `sources/data/money-gaps.csv`.\n')
    return ''.join(t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    want = build()
    if a.check:
        cur = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if cur != want:
            print('STALE %s' % os.path.relpath(OUT, ROOT), file=sys.stderr)
            return 1
        print('%s is current' % os.path.relpath(OUT, ROOT))
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(want)
    print('wrote %s (%d lines)' % (os.path.relpath(OUT, ROOT), want.count('\n')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
