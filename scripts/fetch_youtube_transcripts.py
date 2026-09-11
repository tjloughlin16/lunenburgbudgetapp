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
NO_CAPTIONS = os.path.join(ROOT, 'sources', 'data', 'youtube-no-captions.csv')

# TWO FAILURES THAT LOOK IDENTICAL AND ARE NOT. `TranscriptsDisabled` and
# `NoTranscriptFound` are PERMANENT FACTS ABOUT ONE RECORDING -- the town posted it with
# captions off, and no amount of waiting changes that. Everything else (a refusal, a
# timeout, a reset) is about the ENDPOINT and is worth backing away from.
#
# Conflating them cost fifteen hours on 10 September 2026. Six consecutive 2017 meetings
# had captions disabled, the run read three-in-a-row as a throttle, and the backfill sat
# in escalating cooldowns up to the six-hour cap while nothing at all was wrong with our
# access. A permanent condition must never drive a backoff.
PERMANENT = ('TranscriptsDisabled', 'NoTranscriptFound', 'VideoUnavailable',
             'VideoUnplayable', 'AgeRestricted')

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


def load_targets(board, since, until, video_only=False):
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
    if video_only:
        rows = [r for r in rows if r['video_id'] in _video_only_ids()]
        # TWO TIERS, NEWEST FIRST INSIDE EACH. TJ: "i would rather get all the 3 boards,
        # in newest first order, THEN the other boards in newest first order."
        #
        # The three tables where the town's money is argued come first, INTERLEAVED with
        # each other by date rather than one board exhausted before the next -- so a run
        # that stops early leaves the most recent months across all three, which is what
        # somebody asking about a current argument needs. Everything else follows, also
        # newest first. It matters because the caption endpoint can stop a run at any
        # point: the order decides what we have when it does, not merely what we get to
        # last.
        TIER_1 = ('school-committee', 'select-board', 'finance-committee')
        rows.sort(key=lambda r: (0 if r['board_slug'] in TIER_1 else 1,
                                 [-ord(c) for c in r['meeting_date']]))
        if not rows:
            raise SystemExit(
                'no meeting in `meeting-register.csv` has evidence "video only". '
                'Either the register has not been rebuilt or every such meeting now '
                'has a document.')
    return rows


def _video_only_ids():
    """Recordings of meetings for which NO document survives.

    THIS IS THE POINT OF THE WHOLE EXERCISE and newest-first misses it entirely. 231
    meetings in `meeting-register.csv` carry evidence `video only` -- 162 of them School
    Committee -- and for those a rough machine caption is the difference between a
    searchable account and none at all. Every meeting the backfill had reached working
    backwards from today ALSO had minutes, so after fifty fetches the count of
    document-less meetings made searchable was nought.

    Read from the register on every call rather than cached: the register is rebuilt when
    the town publishes, and a meeting stops being video-only the day its minutes appear.
    """
    import csv as _csv
    path = os.path.join(ROOT, 'sources', 'data', 'meeting-register.csv')
    if not os.path.exists(path):
        raise SystemExit('--video-only needs sources/data/meeting-register.csv. '
                         'Run: python3 scripts/build_meeting_register.py')
    ids = set()
    with open(path, newline='', encoding='utf-8') as fh:
        for r in _csv.DictReader(fh):
            if r.get('evidence') == 'video only':
                # One meeting can list several recordings.
                ids.update(v for v in (r.get('video_ids') or '').split('|') if v)
    if not ids:
        raise SystemExit('meeting-register.csv parsed to zero video-only recordings -- '
                         'refusing to report that as "nothing to do".')
    return ids


def note_no_captions(row, reason):
    """Flag a recording that will never yield a caption, for a person to look at.

    TJ: "if you hit that (transcripts disabled, can you flag it??? I want to review those
    manually)" -- and then "but then skip, normally". So it is written down rather than
    swallowed: a meeting we cannot read is a hole in the archive whatever the cause, and
    some of these may have captions that YouTube simply will not serve to this library.
    """
    cols = ['video_id', 'board_slug', 'meeting_date', 'reason', 'url', 'seen_at']
    have = {}
    if os.path.exists(NO_CAPTIONS):
        with open(NO_CAPTIONS, newline='', encoding='utf-8') as fh:
            have = {r['video_id']: r for r in csv.DictReader(fh)}
    have[row['video_id']] = dict(
        video_id=row['video_id'], board_slug=row['board_slug'],
        meeting_date=row['meeting_date'], reason=reason,
        url='https://www.youtube.com/watch?v=' + row['video_id'],
        seen_at=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
    tmp = NO_CAPTIONS + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator='\n')
        w.writeheader()
        for k in sorted(have, key=lambda k: (have[k]['meeting_date'], k), reverse=True):
            w.writerow({c: have[k].get(c, '') for c in cols})
    os.replace(tmp, NO_CAPTIONS)
    return len(have)


def read_no_captions():
    if not os.path.exists(NO_CAPTIONS):
        return set()
    with open(NO_CAPTIONS, newline='', encoding='utf-8') as fh:
        return {r['video_id'] for r in csv.DictReader(fh)}


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
    ap.add_argument('--retry-no-captions', action='store_true',
                    help='try recordings previously found to have no captions '
                         'at all — the town can turn them on later')
    ap.add_argument('--video-only', action='store_true',
                    help='only meetings with NO surviving document -- the 231 for '
                         'which a caption is the only possible record')
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
    targets = load_targets(args.board, args.since, args.until, args.video_only)

    if args.status:
        # COUNT VIDEOS, NOT BOARD-VIDEO PAIRS. A joint meeting is listed under every
        # board that sat in it -- eight recordings here are select-board AND
        # finance-committee AND school-committee -- so summing the per-board rows counts
        # one recording three times. It reported 35 held when 25 files existed, and told
        # us select-board had 5 transcripts when it had none: those five were tri-board
        # meetings already fetched under school-committee. The per-board rows below are
        # RIGHT to count a joint meeting under each board; only the total was wrong.
        scope = {r['video_id'] for r in targets}
        done = scope & set(idx)
        joint = len(targets) - len(scope)
        print('%d video(s) in scope; %d fetched, %d not%s'
              % (len(scope), len(done), len(scope) - len(done),
                 ('  (%d joint listing(s) across boards, counted once here '
                  'and under each board below)' % joint) if joint else ''))
        by = {}
        for r in targets:
            b = by.setdefault(r['board_slug'], [0, 0])
            b[0] += 1
            b[1] += 1 if r['video_id'] in idx else 0
        for b in sorted(by, key=lambda b: -by[b][0])[:12]:
            print('  %-38s %5d fetched of %5d' % (b, by[b][1], by[b][0]))
        return 0

    # A RECORDING ALREADY KNOWN TO HAVE NO CAPTIONS IS NOT WORK. Retrying it every run
    # spends a request and a 45-second pause to be told the same permanent thing, and --
    # before the two cases were separated -- three of them in a row halted the backfill.
    # `--retry-no-captions` exists because the town CAN turn captions on later, so this
    # must be a skip somebody can undo rather than a decision made once.
    skip = set() if args.retry_no_captions else read_no_captions()
    todo = [r for r in targets
            if r['video_id'] not in idx and r['video_id'] not in skip][:args.limit]
    if skip:
        held_back = sum(1 for r in targets
                        if r['video_id'] not in idx and r['video_id'] in skip)
        if held_back:
            print('%d recording(s) in scope carry no captions and are skipped; '
                  'see %s (--retry-no-captions to try them again)'
                  % (held_back, os.path.relpath(NO_CAPTIONS, ROOT)))
    if not todo:
        print('nothing to fetch — every video in scope already has a transcript')
        return 0

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        raise SystemExit('pip3 install --user youtube-transcript-api')
    api = YouTubeTranscriptApi()

    ok = fail = streak = nocap = 0
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
            kind = type(e).__name__
            if kind in PERMANENT:
                # A FACT ABOUT THE RECORDING, NOT ABOUT OUR ACCESS. Flag it, skip it, and
                # do NOT touch the streak -- see PERMANENT above.
                nocap += 1
                total_flagged = note_no_captions(row, kind)
                print('  %2d/%d  %s  %-22s  NO CAPTIONS (%s) — flagged for review'
                      % (i, len(todo), row['meeting_date'], row['board_slug'][:22], kind))
                if i < len(todo):
                    time.sleep(args.sleep)
                continue
            fail += 1
            streak += 1
            print('  %2d/%d  %s  %s  FAILED %s: %s'
                  % (i, len(todo), row['meeting_date'], row['video_id'],
                     kind, str(e).splitlines()[0][:110]))
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

    print('\n%d fetched, %d failed, %d with no captions. %d transcript(s) held in total.'
          % (ok, fail, nocap, len(idx)))
    if nocap:
        print('  %d recording(s) carry no captions at all — flagged in %s for review.'
              % (len(read_no_captions()), os.path.relpath(NO_CAPTIONS, ROOT)))
    remaining = len([r for r in targets if r['video_id'] not in idx])
    print('%d still to fetch in this scope.' % remaining)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
