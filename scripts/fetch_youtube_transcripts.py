#!/usr/bin/env python3
"""Captions for the meeting recordings, newest first.

A TRANSCRIPT IS A FINDING AID AND NEVER A SOURCE. This is the whole design constraint and
it is not a disclaimer bolted on afterwards. An auto-generated caption is a machine's
rendering of audio, and it mangles exactly what this project cares about: *fifteen
hundred*, *$1,500* and *$50* are the same sound to a caption model. Quoting a figure from
a caption as though it were the record is CLAUDE.md rule 13 with a microphone.

So a transcript locates the MOMENT. The citation is the video at that timestamp, or the
document the transcript tells you to go and ask for. Every file written here says so in
its own header, because the file will outlive this docstring and will be read by somebody
who did not run the script.

WHY IT IS WORTH HAVING ANYWAY. sources/data/meeting-register.csv shows 231 meetings whose
only surviving record is a recording -- no agenda, no minutes, nothing filed -- and 162 of
those are School Committee. For those meetings a rough machine transcript is the
difference between a searchable account and none at all.

WE DO NOT DOWNLOAD THE VIDEOS. TJ: "we dont need to download the videos." This script
cannot: it uses the caption API only, never yt-dlp's media path, and there is no option
that would write a media file.

WHERE THE FILES GO, AND WHY NOT BESIDE THE MINUTES. `sources/meetings/text/` holds text
extracted from documents the TOWN published. A caption is ours and machine-made, and
putting the two in one tree would let a grep return them interchangeably -- which is the
proxy-as-fact failure rule 7 keeps warning about. They live under `sources/data/`, the
folder the archive layout defines as "computed here", in their own subtree.

    python3 scripts/fetch_youtube_transcripts.py --board school-committee --limit 10
    python3 scripts/fetch_youtube_transcripts.py --board school-committee --since 2024-07-01
    python3 scripts/fetch_youtube_transcripts.py --status
"""
import argparse
import csv
import datetime as dt
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARDS = os.path.join(ROOT, 'sources', 'data', 'youtube-video-boards.csv')
VIDEOS = os.path.join(ROOT, 'sources', 'data', 'youtube-videos.csv')
DEST = os.path.join(ROOT, 'sources', 'data', 'youtube-transcripts')
INDEX = os.path.join(ROOT, 'sources', 'data', 'youtube-transcript-index.csv')

COLS = ['video_id', 'board_slug', 'meeting_date', 'path', 'segments', 'seconds',
        'language', 'generated', 'chars', 'fetched_at']

# THE WARNING TRAVELS WITH THE FILE. It will outlive this script and be read by somebody
# who never ran it, quite possibly by a program rather than a person -- so it is a field in
# the document, not a comment in the code.
WARNING = (
    'MACHINE-GENERATED CAPTIONS. NOT A RECORD OF THE MEETING. These were produced by a '
    'speech model, not by a person. They are OURS, they are derived, and they are wrong '
    'in specific ways that matter here: a caption model hears "fifteen hundred", "$1,500" '
    'and "$50" alike, and it mangles names. USE THIS TO FIND THE MOMENT, THEN CITE THE '
    'MOMENT -- the citation is the video at that timestamp, or the document this points '
    'you to. Never this file. No figure, name or vote may be quoted from these lines as '
    'though the meeting said it.')


def load_targets(board, since, until):
    if not os.path.exists(BOARDS):
        raise SystemExit('%s is missing. Run scripts/build_youtube_classification.py.'
                         % os.path.relpath(BOARDS, ROOT))
    with open(BOARDS, newline='', encoding='utf-8') as fh:
        rows = [r for r in csv.DictReader(fh) if r.get('meeting_date')]
    if not rows:
        raise SystemExit('no classified video carries a meeting date. Nothing to fetch.')
    if board:
        rows = [r for r in rows if r['board_slug'] == board]
        if not rows:
            raise SystemExit('no videos for board %r. Check sources/data/youtube-boards.csv'
                             % board)
    if since:
        rows = [r for r in rows if r['meeting_date'] >= since]
    if until:
        rows = [r for r in rows if r['meeting_date'] <= until]
    # NEWEST FIRST. The refresh case and the backfill case are then the same loop, and an
    # interrupted backfill has still delivered the half people ask about.
    rows.sort(key=lambda r: (r['meeting_date'], r['video_id']), reverse=True)
    return rows


def read_index():
    if not os.path.exists(INDEX):
        return {}
    with open(INDEX, newline='', encoding='utf-8') as fh:
        return {r['video_id']: r for r in csv.DictReader(fh)}


def write_index(idx):
    os.makedirs(os.path.dirname(INDEX), exist_ok=True)
    tmp = INDEX + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for k in sorted(idx, key=lambda k: (idx[k]['meeting_date'], k), reverse=True):
            w.writerow({c: idx[k].get(c, '') for c in COLS})
    os.replace(tmp, INDEX)


def fetch_one(api, row):
    from youtube_transcript_api import YouTubeTranscriptApi  # noqa: F401
    vid = row['video_id']
    tr = api.fetch(vid)
    segs = list(tr)
    lang = getattr(tr, 'language_code', '') or ''
    auto = getattr(tr, 'is_generated', True)

    # AS RAW AS YOUTUBE GIVES IT. TJ: "keep it as raw as we get from youtube, put into
    # individual, single-doc transcript files per meeting."
    #
    # The first version of this rendered each segment as "[0:01:23] text", which rounded
    # `start` to whole seconds and DROPPED `duration` outright -- a prettier file that had
    # thrown away part of the source. That is rule 13 committed by a fetcher: the stored
    # thing must be the observed thing, and anything easier to read is built FROM it later
    # and kept beside it.
    #
    # So: one JSON document per meeting. `segments` holds exactly the three fields the API
    # returns, floats unrounded, text unmodified -- no stripping, no joining of fragments,
    # no de-duplicating the stutters the model transcribed. `meta` carries the provenance
    # and the warning that must travel with the file.
    rel = os.path.join(row['board_slug'], '%s-%s.json' % (row['meeting_date'], vid))
    path = os.path.join(DEST, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc = {
        'warning': WARNING,
        'video_id': vid,
        'video_url': 'https://www.youtube.com/watch?v=%s' % vid,
        'board_slug': row['board_slug'],
        'meeting_date': row['meeting_date'],
        'title': row.get('title_stem', ''),
        'language': lang,
        'generated': 'auto' if auto else 'uploaded',
        'fetched_at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'fetched_by': 'scripts/fetch_youtube_transcripts.py',
        'segment_fields': ['start', 'duration', 'text'],
        'segments': [{'start': s.start,
                      'duration': getattr(s, 'duration', None),
                      'text': s.text} for s in segs],
    }
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    text = ''  # size is read off the file below
    return {
        'video_id': vid, 'board_slug': row['board_slug'],
        'meeting_date': row['meeting_date'],
        'path': os.path.relpath(path, ROOT).replace(os.sep, '/'),
        'segments': len(segs),
        'seconds': int(segs[-1].start + getattr(segs[-1], 'duration', 0)) if segs else 0,
        'language': lang, 'generated': 'auto' if auto else 'uploaded',
        'chars': os.path.getsize(path),
        'fetched_at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--board')
    ap.add_argument('--since')
    ap.add_argument('--until')
    ap.add_argument('--limit', type=int, default=10,
                    help='how many to fetch this run (default 10)')
    # PACING IS THE WHOLE PROBLEM, and 1.5s was wrong by an order of magnitude.
    #
    # Ten fetches in about 35 seconds got this IP a 429 on the caption endpoint -- from
    # BOTH youtube-transcript-api and yt-dlp, which is how we know the throttle is on the
    # endpoint and not on a library. yt-dlp still downloaded the video's player metadata
    # fine, so it is captions specifically.
    #
    # Nothing here is urgent. The whole channel is 2,857 meetings and this costs no money
    # and no attention -- it runs unattended and resumes. So the default is slow enough to
    # be invisible to YouTube rather than fast enough to finish in one sitting.
    ap.add_argument('--sleep', type=float, default=45.0,
                    help='seconds between requests (default 45; 1.5 got us 429ed)')
    ap.add_argument('--stop-after-failures', type=int, default=3,
                    help='give up the run after this many consecutive failures')
    ap.add_argument('--status', action='store_true',
                    help='what is fetched and what is not, then stop')
    args = ap.parse_args()

    idx = read_index()
    targets = load_targets(args.board, args.since, args.until)

    if args.status:
        done = [r for r in targets if r['video_id'] in idx]
        print('%d video(s) in scope; %d fetched, %d not'
              % (len(targets), len(done), len(targets) - len(done)))
        by = {}
        for r in targets:
            b = by.setdefault(r['board_slug'], [0, 0])
            b[0] += 1
            b[1] += 1 if r['video_id'] in idx else 0
        for b in sorted(by, key=lambda b: -by[b][0])[:12]:
            print('  %-38s %5d fetched of %5d' % (b, by[b][1], by[b][0]))
        return 0

    todo = [r for r in targets if r['video_id'] not in idx][:args.limit]
    if not todo:
        print('nothing to fetch — every video in scope already has a transcript')
        return 0

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        raise SystemExit('pip3 install --user youtube-transcript-api')
    api = YouTubeTranscriptApi()

    ok = fail = streak = 0
    for i, row in enumerate(todo, 1):
        try:
            rec = fetch_one(api, row)
            idx[rec['video_id']] = rec
            ok += 1
            streak = 0
            print('  %2d/%d  %s  %-22s %6d segs  %5.1f min  %s'
                  % (i, len(todo), rec['meeting_date'], rec['board_slug'][:22],
                     rec['segments'], rec['seconds'] / 60.0, rec['generated']))
        except Exception as e:
            fail += 1
            streak += 1
            print('  %2d/%d  %s  %s  FAILED %s: %s'
                  % (i, len(todo), row['meeting_date'], row['video_id'],
                     type(e).__name__, str(e).splitlines()[0][:110]))
            # STOP ON A STREAK RATHER THAN GRINDING THROUGH IT. Once the endpoint is
            # throttling, every further request is both useless and more evidence to
            # whatever is counting. A run that stops early has cost nothing; a run that
            # hammers 300 refusals may cost the next run too.
            if streak >= args.stop_after_failures:
                print('\n  %d failures in a row — stopping. The caption endpoint '
                      'throttles by IP and continuing makes it worse. The index is '
                      'written, so re-running later resumes where this left off.'
                      % streak)
                break
            time.sleep(args.sleep * 4)
        # WRITE THE INDEX AS WE GO. A run that dies at 40 of 50 must not lose 40.
        write_index(idx)
        if i < len(todo):
            time.sleep(args.sleep)

    print('\n%d fetched, %d failed. %d transcript(s) held in total.'
          % (ok, fail, len(idx)))
    remaining = len([r for r in targets if r['video_id'] not in idx])
    print('%d still to fetch in this scope.' % remaining)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
