#!/usr/bin/env python3
"""The recording-minutes payload the site serves, generated from the minutes files.

    python3 scripts/build_recording_minutes.py           # write fy28/public/data/recording-minutes.json
    python3 scripts/build_recording_minutes.py --check   # fail if it no longer reproduces

One file, every meeting for which `write_recording_minutes.py` has produced minutes,
newest first, with the town's own documents for that meeting linked beside ours. The
page /what-was-said renders it: an index by board, and one page per recording.

Counts here are derived from the files and never typed. The `warning` travels with every
item because the payload is fetched by things other than the page.
"""
import argparse
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import write_recording_minutes as W  # noqa: E402

OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'recording-minutes.json')


def payload():
    items = []
    for f in sorted(glob.glob(os.path.join(W.OUT, '*', '*.json'))):
        m = json.load(open(f, encoding='utf-8'))
        mm = m['minutes']
        votes = [v for v in mm['votes'] if not v.get('procedural')]
        # TIME BY SUBJECT. Each topic's span, credited in full to each of its tags (a
        # topic tagged budget AND athletics counts its minutes toward both), so the
        # figure answers "how long did they talk about X" and the tags do not sum to the
        # meeting. Seconds, from the captions' own timestamps.
        by_tag = {}
        spoken = 0
        for t in mm.get('topics', []):
            span = max(0, int(t.get('t_end', 0)) - int(t.get('t_start', 0)))
            spoken += span
            for tag in t.get('tags', []):
                by_tag[tag] = by_tag.get(tag, 0) + span
        items.append({
            'time_by_tag_s': dict(sorted(by_tag.items(), key=lambda kv: -kv[1])),
            'topics_span_s': spoken,
            'slug': '%s/%s-%s' % (m['board_slug'], m['meeting_date'], m['video_id']),
            'board_slug': m['board_slug'],
            'board': m['board'],
            'date': m['meeting_date'],
            'video_id': m['video_id'],
            'video_url': m['video_url'],
            'summary': mm['summary'],
            'confidence': mm['confidence'],
            'tags': mm.get('tags', []),
            'recording': m.get('recording'),
            'counts': {'votes': len(votes), 'procedural_votes': len(mm['votes']) - len(votes),
                       'transfers': len(mm['transfers']), 'budget_items': len(mm['budget_items']),
                       'decisions': len(mm['decisions']), 'topics': len(mm['topics']),
                       'public_comment': len(mm.get('public_comment', [])),
                       'attendees': len(mm.get('attendees', [])),
                       'not_audible': len(mm['not_audible'])},
            'town_published': m['town_published'],
            'has_official_minutes': any(d['kind'] == 'minutes' for d in m['town_published']),
            'source': m['source'],
            'written': m['written'],
            'minutes': mm,
        })
    items.sort(key=lambda i: (i['date'], i['video_id']), reverse=True)
    boards = {}
    for i in items:
        b = boards.setdefault(i['board_slug'], {'board': i['board'], 'meetings': 0, 'without_official_minutes': 0})
        b['meetings'] += 1
        b['without_official_minutes'] += 0 if i['has_official_minutes'] else 1
    tags = {}
    for i in items:
        for t in i['tags']:
            tags[t] = tags.get(t, 0) + 1
    # Per board: seconds by tag across every meeting held, and the meeting count, so a
    # page can say "the School Committee spent 4h12m of 21h on athletics across 9 meetings".
    time_by_board = {}
    for i in items:
        b = time_by_board.setdefault(i['board_slug'], {'board': i['board'], 'meetings': 0, 'topics_span_s': 0, 'by_tag_s': {}})
        b['meetings'] += 1
        b['topics_span_s'] += i['topics_span_s']
        for tag, sec in i['time_by_tag_s'].items():
            b['by_tag_s'][tag] = b['by_tag_s'].get(tag, 0) + sec
    for b in time_by_board.values():
        b['by_tag_s'] = dict(sorted(b['by_tag_s'].items(), key=lambda kv: -kv[1]))
    return {
        'warning': W.WARNING,
        'tags': dict(sorted(tags.items(), key=lambda kv: (-kv[1], kv[0]))),
        'time_by_board': time_by_board,
        'time_note': 'Seconds of recording per subject, from our topic spans; a topic with two tags is credited to both, so tags do not sum to the meeting.',
        'what': 'Our minutes of recorded meetings, written by a language model from our machine '
                'captions. A finding aid to the recording, cited by the second.',
        'counts': {'meetings': len(items), 'boards': len(boards),
                   'without_official_minutes': sum(1 for i in items if not i['has_official_minutes'])},
        'boards': boards,
        'meetings': items,
    }


def render():
    return json.dumps(payload(), indent=1, ensure_ascii=False) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text = render()
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if have != text:
            print('STALE: %s — run build_recording_minutes.py' % os.path.relpath(OUT, ROOT))
            return 1
        print('ok: %s reproduces' % os.path.relpath(OUT, ROOT))
        return 0
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(text)
    p = json.loads(text)
    print('wrote %s — %d meeting(s), %d board(s), %d with no official minutes'
          % (os.path.relpath(OUT, ROOT), p['counts']['meetings'], p['counts']['boards'],
             p['counts']['without_official_minutes']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
