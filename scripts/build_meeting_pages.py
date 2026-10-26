#!/usr/bin/env python3
"""ONE PAGE PER MEETING, every meeting the register holds -- not only the recorded ones.

TJ, 26 October 2026: *"when i search and select 'meetings', there's no MEETINGS filter. i
can select minutes but its just blank text docs. i cant find the combined meeting page
based on a search."* A meeting page existed only where we had written minutes from a
recording: 1,617 of the 7,100 meetings in `meeting-register.csv`. A search hit in the
town's own minutes opened the extracted `.txt` and nothing else.

Writes `fy28/public/data/meetings/<board>/<year>.json`, one file per board and calendar
year, read by the meeting page at `/meeting-minutes/<board>/<date>` when no recording page
answers that address. Each meeting carries what the register knows and where it is:

- the agenda and the minutes: our copy, the extracted text, the publisher's address;
- the recording(s), and our minutes of them where written;
- the votes the TOWN'S minutes record, each with its verbatim quote
  (`official-votes/`, read by a model and checked verbatim against the minutes).

Nothing here is new data. It is the register and the votes, grouped by meeting so a
reader can arrive at one.

    python3 scripts/build_meeting_pages.py
    python3 scripts/build_meeting_pages.py --check
"""
import argparse
import collections
import csv
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(ROOT, 'sources', 'data', 'meeting-register.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'meetings')
TEXT = os.path.join(ROOT, 'sources', 'meetings', 'text')


def doc(path, url, created=None):
    """A town document: our copy, its extracted text, the publisher's address."""
    if not path and not url:
        return None
    stem = os.path.splitext(path)[0] if path else ''
    # Only text that exists: a scan nobody has read has a copy and no text.
    has_text = bool(stem) and os.path.exists(os.path.join(TEXT, stem + '.txt'))
    return {'copy': '/docs/meetings/%s' % path if path else None,
            'text': '/docs/minutes/text/%s.txt' % stem if has_text else None,
            'url': url or None, 'created': created or None}


def votes(path):
    if not path:
        return []
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        sys.exit('build_meeting_pages: the register names %s and it is not on disk' % path)
    return [{'motion': v.get('motion') or '', 'moved_by': v.get('moved_by') or '',
             'seconded_by': v.get('seconded_by') or '', 'outcome': v.get('outcome') or '',
             'procedural': bool(v.get('procedural')), 'quote': v.get('quote') or ''}
            for v in json.load(open(full, encoding='utf-8')).get('votes', [])]


def build():
    rows = list(csv.DictReader(open(REGISTER, encoding='utf-8')))
    if len(rows) < 1000:
        sys.exit('build_meeting_pages: %s parsed to %d rows; refusing' % (REGISTER, len(rows)))
    shards = collections.defaultdict(list)
    for r in rows:
        videos = r['video_urls'].split() if r['video_urls'] else []
        m = {
            'board': r['board'], 'board_slug': r['board_slug'], 'date': r['date'],
            'as_printed': r['body_as_printed'] or None,
            'part_of': r['part_of'] or None,
            'agenda': doc(r['agenda_path'], r['agenda_url'], r['agenda_created']),
            'minutes': doc(r['minutes_path'], r['minutes_url'], r['minutes_created']),
            'minutes_ocr': r['minutes_ocr'] == '1',
            'videos': videos,
            'captions_disabled': r['captions_disabled'] == '1',
            'ours': r['our_minutes_url'] or None,
            'ours_headline': r['our_minutes_headline'] or None,
            'votes': votes(r['official_votes_path']),
            'missing': r['missing'].split() if r['missing'] else [],
        }
        shards[(r['board_slug'], r['date'][:4])].append(m)
    out = {}
    for (board, year), ms in shards.items():
        ms.sort(key=lambda m: m['date'])
        out[os.path.join(OUT, board, year + '.json')] = json.dumps(
            {'generated_by': 'scripts/build_meeting_pages.py', 'board_slug': board, 'year': year,
             'meetings': ms}, ensure_ascii=False, separators=(',', ':')) + '\n'
    return out, len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    want, n = build()
    have = set(glob.glob(os.path.join(OUT, '*', '*.json')))
    if a.check:
        stale = [k for k, v in want.items()
                 if not os.path.exists(k) or open(k, encoding='utf-8').read() != v]
        extra = have - set(want)
        if stale or extra:
            print('build_meeting_pages: %d stale, %d not in the register. Run it.' % (len(stale), len(extra)))
            sys.exit(1)
        print('build_meeting_pages: %d meetings in %d files reproduce.' % (n, len(want)))
        return
    for k, v in want.items():
        os.makedirs(os.path.dirname(k), exist_ok=True)
        with open(k + '.tmp', 'w', encoding='utf-8') as fh:
            fh.write(v)
        os.replace(k + '.tmp', k)
    for k in have - set(want):
        os.remove(k)
    print('build_meeting_pages: %d meetings, %d board-year files.' % (n, len(want)))


if __name__ == '__main__':
    main()
