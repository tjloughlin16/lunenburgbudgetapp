#!/usr/bin/env python3
"""A public records request for meetings the town announced and posted no minutes for.

    python3 scripts/build_minutes_request.py --board "School Committee"
    python3 scripts/build_minutes_request.py --board "School Committee" --since 2024

GENERATED, NOT WRITTEN. The list of dates comes out of sources/meetings/index.csv, which
is the town's own AgendaCenter listing. A request that names a date the town did not
announce is a request that gets refused on the first line, so nothing here is typed.

WHAT THE LIST MEANS, AND WHAT IT DOES NOT. Every row is a date carrying an AGENDA and no
MINUTES. That is not the same as a meeting held with no minutes taken: an agenda can be
posted for a meeting later cancelled, and minutes can exist without being posted online.
Those are different things, nothing published distinguishes them, and the letter says so.
It is a stronger request for saying so -- the recipient is the only party who can resolve
the ambiguity, which is the reason to ask.
"""
import argparse, collections, csv, datetime, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'sources', 'meetings', 'index.csv')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--board', required=True)
    ap.add_argument('--since', type=int, default=0)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()

    rows = [r for r in csv.DictReader(open(INDEX, encoding='utf-8', errors='replace'))
            if r['board'] == a.board]
    if not rows:
        sys.exit(f'no rows for board {a.board!r} in the index. A request naming a board '
                 'the listing does not carry would be refused on its first line.')

    kinds, url = collections.defaultdict(set), {}
    for r in rows:
        kinds[r['date']].add(r['kind'])
        if r['kind'] == 'agenda':
            url[r['date']] = r['url']
    missing = sorted(d for d, k in kinds.items()
                     if 'agenda' in k and 'minutes' not in k and int(d[:4]) >= a.since)
    if not missing:
        sys.exit('every announced meeting in that range has minutes posted. Nothing to ask for.')

    years = sorted({d[:4] for d in missing})
    fmt = lambda d: datetime.date(*map(int, d.split('-'))).strftime('%-d %B %Y')
    o = [f'# Public records request — {a.board} minutes',
         '',
         f'**To:** Records Access Officer, [Town of Lunenburg / Lunenburg Public Schools]  ',
         f'**Date:** {datetime.date.today():%-d %B %Y}  ',
         f'**Subject:** Minutes of {len(missing)} {a.board} meetings, {years[0]}–{years[-1]}',
         '',
         'Under the Massachusetts Public Records Law, M.G.L. c.66, §10, I request a copy of',
         f'the approved minutes of the {a.board} meetings listed below.',
         '',
         'Each of these meetings was announced by the Town on its AgendaCenter, which',
         'carries an agenda for the date. None of them has minutes posted there. Under the',
         'Open Meeting Law, M.G.L. c.30A, §22, minutes must be created for every meeting and',
         'made available upon request — the law does not require them to be posted online, so',
         'I expect that minutes exist for most or all of these dates and simply are not on the',
         'website.',
         '',
         '**Where a meeting on this list was cancelled and no minutes exist, please say so',
         'against that date rather than omitting it.** That answer is as useful to me as the',
         'minutes themselves, and it costs less to give.',
         '',
         '## Format and fees',
         '',
         'Electronic copies, in whatever format you already hold, sent to this email address',
         'are entirely acceptable and I would prefer them to paper. If any portion is',
         'withheld or redacted, please cite the specific exemption relied upon, as §10(b)',
         'requires.',
         '',
         '**Please contact me before incurring any cost.** If the request as written would',
         'attract a fee, tell me the estimate and I will narrow it — by year, or to the',
         'meetings where the budget was discussed — rather than have you absorb the work or',
         'me absorb a charge neither of us intended.',
         '',
         '## The meetings', '']
    for y in years:
        ds = [d for d in missing if d.startswith(y)]
        announced = len({d for d in kinds if d.startswith(y)})
        o += [f'### {y} — {len(ds)} of {announced} announced meetings have no minutes posted', '']
        o += [f'{i}. **{fmt(d)}** — {url.get(d, "agenda listed, address not recorded")}'
              for i, d in enumerate(ds, 1)]
        o += ['']
    o += ['---', '',
          'I am happy to take these in batches if that is easier, and to start with whichever',
          'year is least work. If another custodian holds these records, I would be grateful',
          'if you could forward this or tell me where to send it.',
          '',
          'Thank you for your time.',
          '',
          '[name] · [email] · [address]']

    out = a.out or os.path.join(
        ROOT, 'notes', 'outbound',
        'REQUEST-%s-minutes.md' % a.board.lower().replace(' ', '-'))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8').write('\n'.join(o) + '\n')
    print(f'wrote {os.path.relpath(out, ROOT)} — {len(missing)} meetings, '
          f'{years[0]}–{years[-1]}')


if __name__ == '__main__':
    main()
