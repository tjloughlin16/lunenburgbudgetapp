#!/usr/bin/env python3
"""What has APPEARED on the town's YouTube channel since we last looked.

    python3 scripts/watch_youtube.py            # read the channel feed; record what is NEW
    python3 scripts/watch_youtube.py --check    # no network; the state holds together
    python3 scripts/watch_youtube.py --dry-run  # say what is new, write nothing

THE FEED, NOT THE API. `youtube.com/feeds/videos.xml?channel_id=…` is a published
interface: the channel's newest fifteen uploads, no key, no quota, no billing. Fifteen is
enough for a channel that posts a few videos a week and is checked daily; a gap longer
than that is what `fetch_youtube_index.py` (the full enumeration) is for, and this says
so when the oldest entry in the feed is one it has never seen.

DETERMINISM, the same requirement as watch_meetings.py. The video index
`sources/data/youtube-videos.csv` is the memory: a video is new if its id is not in it.
A new one is appended there (so every downstream script sees it) and an event is written
to `youtube-watch-events.csv` with the day OUR watcher first saw it -- which is not the
day it was uploaded; the feed carries that separately. Run twice on one day and the
second run finds nothing, writes nothing, and the files are byte-identical.

WHAT THIS IS NOT (rule 7). An observation log, an announcement, not a measurement. A
video appearing here says the channel posted it; it does not say the meeting happened,
or that captions exist yet -- YouTube's auto-captions arrive hours to days later, which
is why the refresh fetches transcripts on every run rather than once.
"""
import argparse
import csv
import datetime as dt
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import fetch_youtube_index as FYI  # noqa: E402  -- the channel id and the index columns

FEED = 'https://www.youtube.com/feeds/videos.xml?channel_id=' + FYI.CHANNEL_ID
INDEX = FYI.OUT
EVENTS = os.path.join(ROOT, 'sources', 'data', 'youtube-watch-events.csv')
EVENT_COLS = ['first_seen', 'video_id', 'title', 'url', 'uploaded', 'basis']
NS = {'a': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}


def read_csv(path, cols):
    if not os.path.exists(path):
        return []
    with open(path, newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows, cols):
    tmp = path + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, '') for c in cols})
    os.replace(tmp, path)


def feed_entries(xml_bytes):
    root = ET.fromstring(xml_bytes)
    out = []
    for e in root.findall('a:entry', NS):
        out.append({
            'video_id': e.find('yt:videoId', NS).text,
            'title': (e.find('a:title', NS).text or '').strip(),
            'url': 'https://www.youtube.com/watch?v=' + e.find('yt:videoId', NS).text,
            'uploaded': (e.find('a:published', NS).text or '')[:10],
        })
    return out


def check():
    idx = {r['video_id'] for r in read_csv(INDEX, FYI.COLS)}
    events = read_csv(EVENTS, EVENT_COLS)
    bad = [e['video_id'] for e in events if e['video_id'] not in idx]
    dup = len(events) - len({e['video_id'] for e in events})
    if bad or dup:
        print('FAIL: %d event(s) name a video not in the index; %d duplicated event(s)' % (len(bad), dup))
        return 1
    print('ok: %d youtube watch event(s), every one in the index, none twice' % len(events))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--as-of', default=dt.date.today().isoformat())
    a = ap.parse_args()
    if a.check:
        return check()

    index = read_csv(INDEX, FYI.COLS)
    if len(index) < FYI.MIN_EXPECTED:
        raise SystemExit('the video index holds %d rows, under the %d a real one has; refusing to '
                         'treat everything as new' % (len(index), FYI.MIN_EXPECTED))
    known = {r['video_id'] for r in index}
    req = urllib.request.Request(FEED, headers={'User-Agent': 'lunenburgbudgetproject.org watcher'})
    with urllib.request.urlopen(req, timeout=60) as r:
        entries = feed_entries(r.read())
    if not entries:
        raise SystemExit('the channel feed returned no entries; not writing anything')

    fresh = [e for e in entries if e['video_id'] not in known]
    if entries and entries[-1]['video_id'] not in known:
        print('WARNING: the OLDEST video in the feed is unknown too, so more than fifteen may '
              'have been posted since the last look. Run fetch_youtube_index.py for the rest.')
    now = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    for e in fresh:
        print('NEW  %s  %s  %s' % (e['uploaded'], e['video_id'], e['title']))
    if not fresh:
        print('nothing new on the channel (%d in the feed, all known)' % len(entries))
        return 0
    if a.dry_run:
        return 0

    # Newest first in the index, as fetch_youtube_index writes it: rank 0 is the newest.
    # New rows take rank 0..n-1 and every existing rank shifts, which is what the column
    # means (a position in the channel listing) rather than an identity.
    new_rows = [{'channel_rank': i, 'video_id': e['video_id'], 'title': e['title'],
                 'url': e['url'], 'uploaded': e['uploaded'], 'duration_s': '',
                 'view_count': '', 'indexed_at': now} for i, e in enumerate(fresh)]
    for r in index:
        try:
            r['channel_rank'] = str(int(r['channel_rank']) + len(fresh))
        except ValueError:
            pass
    write_csv(INDEX, new_rows + index, FYI.COLS)
    events = read_csv(EVENTS, EVENT_COLS)
    events += [{'first_seen': a.as_of, 'video_id': e['video_id'], 'title': e['title'],
                'url': e['url'], 'uploaded': e['uploaded'], 'basis': 'feed'} for e in fresh]
    write_csv(EVENTS, events, EVENT_COLS)
    print('%d new video(s) recorded' % len(fresh))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
