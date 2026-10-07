#!/usr/bin/env python3
"""EVERY BOARD'S MISSING RECORDS -- one page per board (`/boards/<slug>/records`), one
payload, and an email-ready markdown export in the format TJ approved for the Parks
Commission.

    python3 scripts/build_board_records.py                 # write fy28/public/data/board-records.json
    python3 scripts/build_board_records.py --check          # rebuild and compare; fail if stale
    python3 scripts/build_board_records.py --md --board parks-commission --since 2025-01-01
    python3 scripts/build_board_records.py --md --board parks-commission --since 2025-01-01 \\
        --out notes/outbound/drafts/PARKS-COMMISSION-MISSING-RECORDINGS.md

TJ, 7 October 2026, after approving that exact format for the Parks Commission and asking
for the same thing on every board: "every board should have a link that shows its missing
data. and list every meeting, and the table of which data is missing (youtube, official
minutes, etc)."

ONE DEFINITION, SHARED. Every status below -- posted, missing, or n/a -- comes from
`scripts/meeting_records.py`, the same module `build_backlog_depth.py`'s chart and
`build_boards.py`'s Recent-meetings table read. A missing record here is a missing record
there; nothing is recomputed a second way.

ONLY HELD MEETINGS. A meeting the town has noticed but not yet held owes nobody a record
yet, so both the payload and the markdown export drop anything dated after today --
exactly the split `fy28/src/lib/meetings.ts` already makes between "upcoming" and
"recent" on every board page.
"""
import argparse
import collections
import csv
import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import meeting_records as MR   # noqa: E402

PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', 'board-records.json')
RUNS = os.path.join(ROOT, 'sources', 'data', 'meeting-watch-runs.csv')
YT_CLASS = os.path.join(ROOT, 'sources', 'data', 'youtube-video-classification.csv')


def _read_csv(p):
    return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []


def agenda_as_of():
    """The last LIVE crawl of the town's AgendaCenter -- `meeting-watch-runs.csv`, not the
    file's own mtime, because a `seed` run reread the whole site and is not "today"."""
    live = [r['ran'] for r in _read_csv(RUNS) if r.get('source') == 'live' and r.get('ran')]
    return max(live) if live else None


def youtube_as_of():
    """The latest date any video was classified -- `youtube-video-classification.csv`'s
    own `classified_at`, which is when we last asked what the channel holds."""
    vals = [r.get('classified_at') for r in _read_csv(YT_CLASS) if r.get('classified_at')]
    return max(vals) if vals else None


def long_date(iso):
    return dt.date.fromisoformat(iso).strftime('%-d %B %Y') if iso else 'unknown'


def held_only(rows, as_of=None):
    return [r for r in rows if MR.is_held(r['date'], as_of)]


def board_names():
    """{board_slug: board name}, skipping the ~50 rows with no resolved slug at all --
    `Select Board` and others, from a join that could not place them, carried in the
    register as `board_slug=''`. Not a board a reader can be sent to; excluded here so it
    does not become a fiftieth "board" of its own. Rolled into `'all'` wherever the
    backlog-depth chart counts every meeting regardless of board, same as before."""
    names = {}
    for r in MR.records():
        if r['board_slug']:
            names.setdefault(r['board_slug'], r['board'])
    return names


def year_counts(rows):
    """`rows` (one board, newest first) rolled up by CALENDAR year -- the grain the
    approved Parks format uses, not the fiscal year the backlog chart uses. Newest year
    first, matching the rows they summarize."""
    by_year = collections.defaultdict(list)
    for r in rows:
        by_year[r['date'][:4]].append(r)
    out = []
    for y in sorted(by_year, reverse=True):
        yrows = by_year[y]
        missing = [r for r in yrows if MR.is_missing(r)]
        out.append(dict(year=y, meetings=len(yrows), missing=len(missing)))
    return out


def payload():
    as_of = dict(agendas_and_minutes=agenda_as_of(), youtube=youtube_as_of())
    today = dt.date.today().isoformat()
    names = board_names()
    boards = []
    for slug in sorted(names):
        rows = held_only(MR.records(slug), today)
        for r in rows:
            r['missing'] = MR.is_missing(r)   # for the page's gaps-only toggle; 'n/a' never counts
        missing = [r for r in rows if r['missing']]
        boards.append(dict(
            board_slug=slug, board=names[slug], meetings=len(rows), missing=len(missing),
            years=year_counts(rows), records=rows,
        ))
    return {
        'id': 'board-records',
        'title': 'Missing records, board by board',
        'grain': 'One row per meeting a board has HELD (noticed meetings still to come are '
                 'not counted here -- see each board’s own page for those). video, '
                 'minutes and transcript are each ‘posted’, ‘missing’, '
                 'or ‘n/a’ -- n/a for a board that has never recorded, or for a '
                 'date before its own first recording, and never a stand-in for missing.',
        'as_of': as_of,
        'boards': boards,
        'not_established': [
            'Whether a board that recorded once and then stopped did so by policy or by '
            'equipment failure. `video` only asks whether the date is on or after the '
            'board’s own first dated recording, never whether it still records today.',
            'Whether a missing set of minutes was ever approved and simply not posted, or '
            'never written at all -- both print the same way in the town’s own '
            'AgendaCenter.',
        ],
    }


def _cell(status):
    return '**MISSING**' if status == 'missing' else ('n/a' if status == 'n/a' else 'posted')


def _email_missing(r):
    """The approved Parks format has no transcript column (TJ: keep that format), so
    'missing something' there means video or minutes only -- never transcript, which the
    web records page shows as a fourth column instead."""
    return r['video']['status'] == 'missing' or r['minutes']['status'] == 'missing'


def _date_text(iso):
    return dt.date.fromisoformat(iso).strftime('%a %-d %b %Y')


def render_md(board_slug, since, pay=None):
    pay = pay or payload()
    b = next((x for x in pay['boards'] if x['board_slug'] == board_slug), None)
    if not b:
        raise SystemExit('no board %r in the register' % board_slug)
    rows = [r for r in b['records'] if r['date'] >= since]
    if not rows:
        raise SystemExit('no meetings for %r since %s' % (board_slug, since))
    years = sorted({r['date'][:4] for r in rows}, reverse=True)
    yr_range = years[0] if years[0] == years[-1] else '%s–%s' % (years[-1], years[0])
    L = []
    w = L.append
    w('# %s %s: meetings missing a recording or minutes' % (b['board'], yr_range))
    w('')
    w('As of %s. Each meeting below had an agenda posted; only meetings missing something '
      'are listed.' % long_date(dt.date.today().isoformat()))
    for y in years:
        yrows = sorted([r for r in rows if r['date'][:4] == y], key=lambda r: r['date'])
        missing = [r for r in yrows if _email_missing(r)]
        w('')
        w('## %s: %d of %d meetings missing something' % (y, len(missing), len(yrows)))
        w('')
        if not missing:
            w('Nothing missing.')
            continue
        w('| Meeting (agenda) | YouTube recording | Official minutes |')
        w('|---|---|---|')
        for r in missing:
            dtext = _date_text(r['date'])
            label = '[%s](%s)' % (dtext, r['agenda']['url']) if r['agenda']['url'] else dtext
            w('| %s | %s | %s |' % (label, _cell(r['video']['status']), _cell(r['minutes']['status'])))
    w('')
    w("Checked against the town's AgendaCenter (agendas and minutes, %s) and every upload "
      "on the Lunenburg Access YouTube channel (as of %s), matched by board and date and "
      "searched again by title." % (long_date(pay['as_of']['agendas_and_minutes']),
                                     long_date(pay['as_of']['youtube'])))
    w('')
    return '\n'.join(L)


def write_atomic(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    open(tmp, 'w', encoding='utf-8').write(content)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--md', action='store_true')
    ap.add_argument('--board')
    ap.add_argument('--since')
    ap.add_argument('--out')
    a = ap.parse_args()
    if a.md:
        if not a.board or not a.since:
            raise SystemExit('--md needs --board SLUG --since YYYY-MM-DD')
        doc = render_md(a.board, a.since)
        if a.out:
            write_atomic(os.path.join(ROOT, a.out) if not os.path.isabs(a.out) else a.out, doc)
            print('wrote %s' % a.out)
        else:
            print(doc)
        return 0
    pay = payload()
    js = json.dumps(pay, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
    if a.check:
        cur = open(PAYLOAD, encoding='utf-8').read() if os.path.exists(PAYLOAD) else ''
        if cur != js:
            print('STALE %s' % os.path.relpath(PAYLOAD, ROOT))
            return 1
        print('%s board(s), up to date' % len(pay['boards']))
        return 0
    write_atomic(PAYLOAD, js)
    print('wrote %s: %s board(s), %s meeting(s) held'
          % (os.path.relpath(PAYLOAD, ROOT), len(pay['boards']), sum(b['meetings'] for b in pay['boards'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
