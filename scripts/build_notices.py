#!/usr/bin/env python3
"""The notices: what to tell people before a meeting, and what to tell them after.

    python3 scripts/build_notices.py           # write fy28/public/data/notices.json
    python3 scripts/build_notices.py --check   # fail if it no longer reproduces

TJ, 11 September 2026: *"we need to check for upcoming, and then for the retro."* Two
kinds of notice, one payload, both COMPOSED from files that already exist rather than
written here:

  upcoming   an agenda preview (`write_agenda_preview.py`) for a policy-board meeting
             dated today or later -- the notice goes out about two days before
  retro      our minutes of the recording (`write_recording_minutes.py`) -- what happened,
             once the video and its captions exist

Each notice carries a `facebook` text a person pastes. NOTHING HERE POSTS. Rule 7 shapes
every line: an upcoming notice says what is ON the agenda and never what will be decided;
a retro notice says what the recording carries and links to the minutes page where every
item is cited to the second. A retro text quotes no figure -- those are as heard.

The site renders both on /this-week; the payload is also what a person copies from.
"""
import argparse
import datetime as dt
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREVIEWS = os.path.join(ROOT, 'sources', 'data', 'agenda-previews')
RECORDED = os.path.join(ROOT, 'sources', 'data', 'recording-minutes')
RUNS = os.path.join(ROOT, 'sources', 'data', 'refresh-runs.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'notices.json')
SITE = 'https://lunenburgbudgetproject.org'
RETRO_DAYS = 21     # a retro notice is offered for this long after the meeting
UPCOMING_DAYS = 14  # a notice two months out is a calendar entry, not a notice


def as_of():
    """The date of the last refresh run, not today -- so the file reproduces (see
    build_meeting_feed.py for why)."""
    import csv
    if not os.path.exists(RUNS):
        return dt.date.today().isoformat()
    rows = list(csv.DictReader(open(RUNS, encoding='utf-8')))
    return max(r['as_of'] for r in rows) if rows else dt.date.today().isoformat()


def long_date(iso):
    return dt.date.fromisoformat(iso).strftime('%A %B %-d')


def retro_text(m):
    mm = m['minutes']
    votes = [v for v in mm['votes'] if not v.get('procedural')]
    url = '%s/what-was-said/%s/%s-%s' % (SITE, m['board_slug'], m['meeting_date'], m['video_id'])
    lines = ['%s, %s: %s' % (m['board'], long_date(m['meeting_date']), mm.get('headline') or 'here is what the recording carries.')]
    lines.append(mm['summary'])
    if votes:
        lines.append('Votes taken (%d): ' % len(votes)
                     + '; '.join('%s — %s' % (v['motion'].rstrip('.'), v['outcome']) for v in votes[:5])
                     + ('; and more.' if len(votes) > 5 else '.'))
    if mm['transfers']:
        lines.append('%d budget transfer%s were voted; the amounts are on the page, as heard.'
                     % (len(mm['transfers']), '' if len(mm['transfers']) == 1 else 's'))
    lines.append('Every item links to the video at that moment: ' + url)
    lines.append('These are our minutes from the recording, not the town’s. Figures are as heard and may be wrong; the recording is the record.')
    return '\n\n'.join(lines)


def payload():
    today = as_of()
    upcoming = []
    for f in sorted(glob.glob(os.path.join(PREVIEWS, '*', '*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        days = (dt.date.fromisoformat(d['date']) - dt.date.fromisoformat(today)).days
        if days < 0 or days > UPCOMING_DAYS:
            continue
        upcoming.append({
            'board': d['board'], 'board_slug': d['board_slug'], 'date': d['date'],
            'days_away': (dt.date.fromisoformat(d['date']) - dt.date.fromisoformat(today)).days,
            'when': d['preview']['when'], 'where': d['preview']['where'],
            'time': d['preview'].get('time', ''), 'attend': d['preview'].get('attend', ''),
            'hook': d['preview'].get('hook', ''),
            'how_to_attend': d['preview']['how_to_attend'],
            'one_line': d['preview']['one_line'],
            'items': d['preview']['items'],
            'important': sum(1 for it in d['preview']['items'] if it.get('important')),
            'nothing_of_note': d['preview']['nothing_of_note'],
            'agenda_url': d['agenda_url'],
            'facebook': d['facebook'],
            'written': d['written']['at'][:10],
        })
    upcoming.sort(key=lambda x: (x['date'], x['board']))

    retro = []
    since = (dt.date.fromisoformat(today) - dt.timedelta(days=RETRO_DAYS)).isoformat()
    for f in sorted(glob.glob(os.path.join(RECORDED, '*', '*.json'))):
        m = json.load(open(f, encoding='utf-8'))
        if m['meeting_date'] < since:
            continue
        mm = m['minutes']
        retro.append({
            'board': m['board'], 'board_slug': m['board_slug'], 'date': m['meeting_date'],
            'url': '/what-was-said/%s/%s-%s' % (m['board_slug'], m['meeting_date'], m['video_id']),
            'headline': mm.get('headline', ''),
            'summary': mm['summary'],
            'votes': sum(1 for v in mm['votes'] if not v.get('procedural')),
            'transfers': len(mm['transfers']),
            'tags': mm.get('tags', []),
            'has_official_minutes': any(x['kind'] == 'minutes' for x in m['town_published']),
            'facebook': retro_text(m),
            'written': m['written']['at'][:10],
        })
    retro.sort(key=lambda x: (x['date'], x['board']), reverse=True)
    return {
        'category': 'announcement',
        'what': 'Notices composed from published agendas (upcoming) and our minutes of recordings (retro). '
                'Nothing here predicts a decision or quotes a caption figure. The facebook field is text a person pastes.',
        'as_of': today,
        'upcoming': upcoming,
        'retro': retro,
        'counts': {'upcoming': len(upcoming), 'retro': len(retro)},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text = json.dumps(payload(), indent=1, ensure_ascii=False) + '\n'
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        print('ok: notices.json reproduces' if have == text else 'STALE: run build_notices.py')
        return 0 if have == text else 1
    open(OUT, 'w', encoding='utf-8').write(text)
    p = json.loads(text)
    print('wrote %s — %d upcoming, %d retro, as of %s' % (os.path.relpath(OUT, ROOT), p['counts']['upcoming'], p['counts']['retro'], p['as_of']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
