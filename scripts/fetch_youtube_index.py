#!/usr/bin/env python3
"""The PEG channel's video index -- one row per recording, and NOT the recordings.

WHY THIS EXISTS. The town posts minutes for a fraction of the meetings it holds -- School
Committee minutes are 162 of 402 listed meetings, none at all in 2021 or 2022 -- and
`scripts/search_minutes.py` can only search what was published. A recording of a meeting
whose minutes were never posted is the only account of that meeting that exists.

WHAT IT STORES, AND WHAT IT REFUSES TO.

  * The video id, the title EXACTLY as posted, the URL, the upload date, the duration.
  * Never the media file. TJ, 8 September 2026: "we dont need to download the videos."
    The archive is 4.26 GB after taking in 21,000 documents and a single two-hour meeting
    recording is a meaningful slice of that; the bucket is write-once for ten years, so a
    mistake at that scale is permanent and large. `--download` is not an option this
    script has, deliberately, and `format` is never set.
  * Never a classification. What board a video is for is a JUDGMENT about a string and it
    is made elsewhere, by an agent, into its own file. This script's output is as close to
    what the channel published as we can get, so that improving the classifier never means
    re-fetching anything.

THE TITLE IS THE OBSERVED THING AND EVERYTHING ELSE IS OURS. TJ: "Their titles are not
consistently labeled. No standard formatting." So this file stores the title verbatim,
including its stray spaces and its typos, and does not normalise, strip or title-case it.
Rule 13: a rendered version is for reading, never for quoting.

THE INDEX IS ALSO THE REFRESH DETECTOR. Re-running this and diffing on video id IS "what
is new since last time" -- there is no second watcher to build for the site's refresh
mechanism. That is why it is cheap, why the id is stable, and why it is written even when
no transcript will ever be fetched: the index establishes THAT a meeting was recorded,
which is a fact the written record does not always carry.

    python3 scripts/fetch_youtube_index.py            # refresh the index
    python3 scripts/fetch_youtube_index.py --check    # fail if it is stale
"""
import argparse
import csv
import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'sources', 'data', 'youtube-videos.csv')

# The town's PEG access channel. The archive already held this address -- the minutes
# carry a standing notice that each meeting is recorded and uploaded to it, and this
# project extracted the channel's own finances the same week.
CHANNEL_URL = 'https://www.youtube.com/user/LunenburgAccess/videos'
CHANNEL_ID = 'UCSs_mXucaangBG9xlgmlxZA'

COLS = ['channel_rank', 'video_id', 'title', 'url', 'uploaded', 'duration_s',
        'view_count', 'indexed_at']

# A channel this size does not lose 90% of its videos overnight. If an enumeration comes
# back with almost nothing -- a rate limit, a signed-out page, a changed URL -- writing it
# would silently delete the index and, because the index IS the refresh detector, would
# then report every remaining video as new. Refuse instead.
MIN_EXPECTED = 500


def enumerate_channel(limit=None):
    try:
        import yt_dlp
    except ImportError:
        raise SystemExit(
            'yt-dlp is not installed.\n\n    pip3 install --user yt-dlp\n\n'
            'It is used ONLY to list the channel and, elsewhere, to pull captions. This '
            'script never downloads media.')

    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,       # belt
        'simulate': True,            # and braces. Nothing may write a media file.
        'extract_flat': 'in_playlist',
        'ignoreerrors': True,
    }
    if limit:
        opts['playlistend'] = limit
    with yt_dlp.YoutubeDL(opts) as y:
        info = y.extract_info(CHANNEL_URL, download=False)
    return [e for e in (info.get('entries') or []) if e]


def to_rows(entries, indexed_at):
    # CHANNEL ORDER IS THE ONLY CHRONOLOGY A FLAT EXTRACTION GIVES.
    #
    # It returns NO upload date for any entry -- 100% empty on the first probe -- so
    # sorting the file by `uploaded` sorted by nothing and threw away the one ordering
    # YouTube did supply. `channel_rank` is that ordering, 0 = newest, and it is what the
    # file is written in.
    #
    # The dates ARE in the titles ("Select Board 09.01.26") and that is the better date
    # anyway: it is the day the meeting was held rather than the day somebody uploaded the
    # recording. But reading it out of a title is a judgment about a string, so it belongs
    # with the classifier and not here. This file holds what the channel returned.
    rows, seen = [], set()
    for rank, e in enumerate(entries):
        vid = e.get('id')
        if not vid or vid in seen:
            continue
        seen.add(vid)
        # `upload_date` is absent from a flat extraction for most entries; `timestamp` is
        # present for some. Whichever is available is recorded AS the upload date and the
        # column is named `uploaded` rather than `meeting_date`, because they are not the
        # same thing -- a recording posted days after the meeting carries the posting day.
        # Deriving the meeting date belongs with the classifier, which can read the title.
        up = e.get('upload_date') or ''
        if not up and e.get('timestamp'):
            up = dt.datetime.utcfromtimestamp(e['timestamp']).strftime('%Y%m%d')
        if len(up) == 8 and up.isdigit():
            up = '%s-%s-%s' % (up[:4], up[4:6], up[6:])
        rows.append({
            'channel_rank': rank,
            'video_id': vid,
            'title': e.get('title') or '',      # VERBATIM. Not stripped, not normalised.
            'url': 'https://www.youtube.com/watch?v=%s' % vid,
            'uploaded': up,
            'duration_s': int(e['duration']) if e.get('duration') else '',
            'view_count': e.get('view_count') or '',
            'indexed_at': indexed_at,
        })
    return rows


def read_existing():
    if not os.path.exists(OUT):
        return {}
    with open(OUT, newline='', encoding='utf-8') as fh:
        return {r['video_id']: r for r in csv.DictReader(fh)}


def write(rows):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        # Newest first, which is the order transcripts are fetched in and the order a
        # person reading the file wants. Ties broken on id so the file is stable.
        for r in sorted(rows, key=lambda r: int(r['channel_rank'])):
            w.writerow(r)
    os.replace(tmp, OUT)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true',
                    help='fail if the channel holds videos the index does not')
    ap.add_argument('--limit', type=int, help='only the newest N (for a quick probe)')
    args = ap.parse_args()

    before = read_existing()
    entries = enumerate_channel(args.limit)
    if not args.limit and len(entries) < MIN_EXPECTED:
        raise SystemExit(
            'the channel returned only %d videos, below the floor of %d. That is far more '
            'likely to be a rate limit or a changed URL than a channel that lost its '
            'archive, and writing it would both destroy the index and report every '
            'surviving video as new. Nothing written.' % (len(entries), MIN_EXPECTED))

    indexed_at = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    rows = to_rows(entries, indexed_at)

    # KEEP THE FIRST-SEEN STAMP. `indexed_at` on a row that already existed answers "when
    # did this first appear", which is what the refresh diff reports on; overwriting it
    # every run would make every row look new every time.
    for r in rows:
        if r['video_id'] in before:
            r['indexed_at'] = before[r['video_id']].get('indexed_at') or indexed_at

    new = [r for r in rows if r['video_id'] not in before]
    gone = [v for v in before if v not in {r['video_id'] for r in rows}]

    if args.check:
        if new or gone:
            print('STALE — %d video(s) on the channel are not in the index, %d indexed '
                  'video(s) are no longer listed.' % (len(new), len(gone)))
            for r in new[:10]:
                print('  new   %s  %s' % (r['video_id'], r['title'][:70]))
            for v in gone[:10]:
                print('  gone  %s  %s' % (v, (before[v].get('title') or '')[:70]))
            print('\n  Run: python3 scripts/fetch_youtube_index.py')
            return 1
        print('ok — %d videos, index matches the channel' % len(rows))
        return 0

    write(rows)
    undated = sum(1 for r in rows if not r['uploaded'])
    print('%s: %d videos (%d new, %d no longer listed)'
          % (os.path.relpath(OUT, ROOT), len(rows), len(new), len(gone)))
    # THE DENOMINATOR, printed every run for the same reason search_minutes prints one:
    # a field that is empty for a third of the rows is invisible unless it is counted.
    print('  %d of %d have no upload date from a flat extraction (%.0f%%). The meeting '
          'date is in the title for most and the classifier derives it there; this column '
          'is the channel\'s, not the meeting\'s.'
          % (undated, len(rows), 100.0 * undated / len(rows) if rows else 0))
    if new:
        print('\n  newest additions:')
        for r in sorted(new, key=lambda r: int(r['channel_rank']))[:8]:
            print('    #%-5s %s  %s' % (r['channel_rank'], r['video_id'], r['title'][:64]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
