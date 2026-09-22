#!/usr/bin/env python3
"""Open seats: the boards a resident could join, as a list.

    python3 scripts/build_open_seats.py
    python3 scripts/build_open_seats.py --check

Writes `sources/analyses/open-seats.md` and `fy28/public/data/open-seats.json`.

TJ, 22 September 2026: *"keep Open seats as a separate report too. A more dynamic one ...
And we can point people to that actually, so make that one a simple one pager ... Less of
a report, more of a list."*

SO IT IS A LIST, AND THE RESTRAINT IS THE POINT. This is the one page here with a job
outside understanding: somebody reads it and then does something. Every sentence that is
not a seat, a board or a date is in its way. There are no conclusion cards, no charts and
no analysis -- those live on `board-composition`, which is about how the boards behave;
this is about whether there is a chair free.

TWO KINDS OF OPENING, and they are different in a way that matters to whoever is reading:

  A SEAT PRINTED EMPTY. The town states a vacancy where a name would go. Available now,
  as far as the last annual report knows.
  A TERM RUNNING OUT. The seat is filled, and the year it comes up is printed beside the
  holder's name. Not available today; available on a date.

The second is the larger number and the more useful one, because a resident who wants a
seat on a particular board can see when to ask rather than only whether to.

WHAT THIS PAGE CANNOT DO, and it says so in one line rather than a section: the annual
report is a snapshot taken once a year, so a seat filled last month still reads as empty
and a seat vacated last month does not read as empty at all. It tells you where to ask.
It cannot tell you what is true today.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

import town_personnel_data as T                                  # noqa: E402
from conclusions import num                                      # noqa: E402

OUT = os.path.join(ROOT, 'sources', 'analyses', 'open-seats.md')
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'open-seats.json')

TOWN = 'https://www.lunenburgma.gov'


def render(d):
    last = d['last']
    vac = sum(d['vacancies'].values())
    soon = d['ahead'][:2]
    t = ['# Open seats\n',
         '\nBoards and committees with a seat going spare, and when the filled ones come '
         'up. From the FY%s annual town report — the town’s own listing, not ours.\n'
         % last]

    t.append('\n## Empty now\n\nThe town printed a vacancy where a name would go.\n\n'
             '| board or committee | seats open |\n|---|---:|\n')
    for post, n in sorted(d['vacancies'].items(), key=lambda a: (-a[1], a[0])):
        t.append('| %s | %s |\n' % (post, n))
    t.append('| **total** | **%s** |\n' % num(vac))

    t.append('\n## Coming up\n\nFilled seats, by the year the term runs out. A seat with a '
             'term ending is a seat to ask about before it does.\n')
    by_year = {}
    for r in d['named']:
        if r['term_expires']:
            by_year.setdefault(r['term_expires'], []).append(r)
    for y in sorted(by_year):
        if not y.isdigit() or int(y) < int(last):
            continue
        rows = sorted(by_year[y], key=lambda r: r['post'])
        t.append('\n### %s — %s seats\n\n| board or committee | seat held by |\n|---|---|\n'
                 % (y, num(len(rows))))
        for r in rows:
            t.append('| %s | %s |\n' % (r['post'], r['person']))

    t.append('\n## How to ask\n\nAppointed seats are filled by the Select Board; elected '
             'seats are filled at the annual town election, third Saturday in May. The '
             'town’s boards and committees are listed at %s.\n' % TOWN)
    t.append('\nThis is a snapshot taken once a year. A seat filled last month still reads '
             'as empty here, and one vacated last month does not read as empty at all — so '
             'it tells you where to ask, not what is true today.\n')
    return ''.join(t)


def payload(d):
    last = d['last']
    vac = sum(d['vacancies'].values())
    soon = d['ahead'][0] if d['ahead'] else None
    by_year = {}
    for r in d['named']:
        y = r['term_expires']
        if y.isdigit() and int(y) >= int(last):
            by_year.setdefault(y, []).append(dict(post=r['post'], person=r['person']))
    return dict(
        generated_by='scripts/build_open_seats.py',
        about='Boards and committees with a seat going spare, and when the filled ones '
              'come up — a list, from the town’s own annual-report listing.',
        grain='SEATS, not people. One row is one seat on one body: either printed empty '
              'by the town, or filled with the year its term runs out printed beside it.',
        stats=[
            dict(value=num(vac), tone='var(--series-cost)',
                 label='seats printed EMPTY across %s boards' % num(len(d['vacancies']))),
            dict(value=num(d['terms'][soon]) if soon else '—',
                 label='seats whose term runs out in %s' % (soon or '')),
            dict(value=num(len(d['sizes'])),
                 label='boards, committees and posts in the town’s listing'),
        ],
        fy=last,
        vacancies=[dict(post=p, seats=n)
                   for p, n in sorted(d['vacancies'].items(), key=lambda a: (-a[1], a[0]))],
        expiring=[dict(year=y, seats=v) for y, v in sorted(by_year.items())],
        sources=[dict(what='Every board, committee and post, with its holders and their '
                           'term-expiry years',
                      where='the ELECTED OFFICIALS and APPOINTED OFFICIALS listing in the '
                            'FY%s annual town report' % last,
                      basis='published',
                      note='Read by scripts/extract_personnel.py. A vacancy is printed in '
                           'place of a name, in eight different spellings.')],
        not_established=[
            'What is open TODAY. The annual report is a snapshot taken once a year.',
            'Whether anybody has already been appointed to a seat printed as empty.',
            'What a seat asks of the person in it — hours, meetings, or term length '
            'beyond the year it ends.',
        ],
        conclusions=[],
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    d = T.load()
    files = {OUT: render(d),
             PAYLOAD: json.dumps(payload(d), indent=1, ensure_ascii=False,
                                 sort_keys=True) + '\n'}
    if a.check:
        stale = [os.path.basename(p) for p, want in files.items()
                 if (open(p, encoding='utf-8').read() if os.path.exists(p) else '') != want]
        if stale:
            print('STALE %s' % ', '.join(sorted(stale)), file=sys.stderr)
            return 1
        print('open-seats is current')
        return 0
    for p, want in files.items():
        open(p, 'w', encoding='utf-8').write(want)
    print('wrote %s and %s' % (os.path.relpath(OUT, ROOT), os.path.relpath(PAYLOAD, ROOT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
