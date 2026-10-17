#!/usr/bin/env python3
"""Every meeting the channel posted MORE THAN ONE video of: which videos are the SAME recording.

    python3 scripts/reconcile_meeting_videos.py           # write the register and the report
    python3 scripts/reconcile_meeting_videos.py --check   # fail if either is stale

WHY. TJ, 17 October 2026. The School Committee's 7 October recording was taken down and
re-posted two days later as "School Committee Meeting 10.07.26 - Audio Fix". Nothing here
handled that: the re-upload's title was a stem nobody had decided, so it joined no meeting,
and every link we published went to a video that no longer exists.

BOTH ARE VALID. NOTHING IS SUPERSEDED. TJ, the same afternoon, after a first version picked
a winner: *"we shouldnt supercede the old one entirely though. the idea is, we should
reconcile both processed minutes to find the best outcome"* -- *"treat them both as valid"*.
The case that proved it: Town Meeting 2 May 2026's "(audio edited)" re-upload is two hours
shorter, and the minutes written from it hold 18 votes to the original's 33. Each recording
has things the other lacks. So this file only says which videos are the same recording and
how their clocks line up; merge_recording_minutes.py reconciles their minutes into one.

WHAT MAKES TWO VIDEOS THE SAME RECORDING:
  1. THEIR CAPTIONS OVERLAP -- the share of six-word runs one transcript shares with the
     other, measured over EACH of them. High over both: the same recording (`same
     recording`). High over the shorter only: the shorter is an `excerpt` of the longer, a
     presentation clipped out of the meeting -- also kept, also valid. Low: a `separate
     recording` (a 4pm and a 6pm meeting, Part 1 and Part 2, a hearing the same night).
  2. A REVISION MARKER IN THE TITLE ("Audio Fix" ...), where there are no captions to compare.
  3. A PERSON, in meeting-video-decisions.csv (`same` or `separate`), which outranks both.
Where nothing can be measured or marked: `unmeasured`.

THE CLOCK. A re-cut moves every moment: a remark at 1:54:03 in one upload may be at 1:31:40
in the other. `offset_s` is the median, over the six-word runs both share, of how far this
video's clock sits from the group's newest upload -- add it to a time here to find the same
moment there. It is measured, and blank where there is nothing to measure it from.

`newest` names the group's most recent upload: what a page links when it shows ONE video,
because an older upload is the one most likely to have been taken down.

Writes:
  sources/data/meeting-videos.csv         one row per video in a multi-video meeting
  notes/generated/MEETING-VIDEOS.md       the same, for reading
"""
import argparse
import collections
import csv
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
CLASS = os.path.join(DATA, 'youtube-video-classification.csv')
BOARDS = os.path.join(DATA, 'youtube-video-boards.csv')
VIDEOS = os.path.join(DATA, 'youtube-videos.csv')
TRANSCRIPTS = os.path.join(DATA, 'youtube-transcript-index.csv')
MINUTES = os.path.join(DATA, 'recording-minutes')
OUT = os.path.join(DATA, 'meeting-videos.csv')
# A PERSON'S CALL OUTRANKS THE MEASUREMENT. Read, never written: video_id, status (same |
# separate), with_video, why, decided_by, decided_on. `same` puts the two in one group;
# `separate` takes the video out of any. For what the captions cannot see.
DECISIONS = os.path.join(DATA, 'meeting-video-decisions.csv')
REPORT = os.path.join(ROOT, 'notes', 'generated', 'MEETING-VIDEOS.md')
SAME = 0.5
N = 6
COLS = ['board_slug', 'date', 'video_id', 'title', 'channel_rank', 'part', 'revision',
        'transcript_seconds', 'relation', 'group', 'newest', 'offset_s', 'basis', 'best_overlap',
        'overlap_with', 'our_minutes']


def read_csv(p):
    with open(p, encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


def shingles(path):
    """{six-word run: the second it first starts} -- a set for overlap, a clock for offsets."""
    if not path or not os.path.exists(path):
        return None
    out = []
    for seg in json.load(open(path, encoding='utf-8')).get('segments') or []:
        for w in re.findall(r"[a-z0-9']+", seg.get('text', '').lower()):
            out.append((w, seg.get('start', 0)))
    runs = {}
    for i in range(max(0, len(out) - N + 1)):
        runs.setdefault(' '.join(w for w, _ in out[i:i + N]), out[i][1])
    return runs


def offset(a, b):
    """Median of (b's time - a's time) over the runs both share: add to a time in `a` to find
    the same moment in `b`. Runs said more than once (a roll call) are dropped -- their
    first-occurrence times need not correspond."""
    shared = [b[k] - a[k] for k in set(a) & set(b)]
    if len(shared) < 20:
        return None
    shared.sort()
    return round(shared[len(shared) // 2])


def overlap(a, b):
    """(over the smaller, over the larger) -- both, because ONE IS NOT ENOUGH. Over the smaller
    alone, a 24-minute clip cut from a 90-minute meeting scores 0.91 and reads as a re-upload:
    the first run made "4.2.14 - School Comm. Meeting ALICE Training Presentation" current
    over the whole meeting it was cut from. High over both is the same recording; high over
    the smaller only is an EXCERPT, and the full recording stays in use."""
    if not a or not b:
        return None
    n = len(set(a) & set(b))
    return n / min(len(a), len(b)), n / max(len(a), len(b))


def decisions():
    out = {}
    for r in (read_csv(DECISIONS) if os.path.exists(DECISIONS) else []):
        if r['status'] not in ('same', 'separate'):
            raise SystemExit('%s: %s has status %r; same or separate'
                             % (os.path.relpath(DECISIONS, ROOT), r['video_id'], r['status']))
        if not r.get('why', '').strip():
            raise SystemExit('%s: %s has no why' % (os.path.relpath(DECISIONS, ROOT), r['video_id']))
        out[r['video_id']] = r
    return out


def build():
    decide = decisions()
    cls = {r['video_id']: r for r in read_csv(CLASS)}
    rank = {r['video_id']: int(r['channel_rank']) for r in read_csv(VIDEOS) if r['channel_rank'].isdigit()}
    tr = {r['video_id']: r for r in read_csv(TRANSCRIPTS)}
    groups = collections.defaultdict(set)
    for r in read_csv(BOARDS):
        if cls.get(r['video_id'], {}).get('kind') == 'meeting' and r['meeting_date']:
            groups[(r['board_slug'], r['meeting_date'])].add(r['video_id'])
    minutes = collections.defaultdict(set)
    for board in os.listdir(MINUTES) if os.path.isdir(MINUTES) else []:
        for f in os.listdir(os.path.join(MINUTES, board)):
            m = re.match(r'(\d{4}-\d{2}-\d{2})-(.+)\.json$', f)
            if m:
                minutes[(board, m.group(1))].add(m.group(2))

    rows, cache = [], {}
    if not groups:
        raise SystemExit('REFUSING: no meeting videos joined to any board')
    for key in sorted(groups):
        ids = sorted(groups[key], key=lambda v: rank.get(v, 10 ** 9))
        if len(ids) < 2:
            continue
        for v in ids:
            if v not in cache:
                t = tr.get(v)
                cache[v] = shingles(os.path.join(ROOT, t['path'])) if t else None
        ov = {(a, b): overlap(cache[a], cache[b]) for a in ids for b in ids if a < b}
        o = lambda a, b: ov.get((min(a, b), max(a, b)))
        # Union the same recording: measured overlap first; a title marker where unmeasured.
        parent = {v: v for v in ids}

        def find(v):
            while parent[v] != v:
                v = parent[v]
            return v
        basis, excerpt = {}, {}
        decided = {v: d for v, d in decide.items() if v in ids}
        sep = {v for v, d in decided.items() if d['status'] == 'separate'}
        for a in ids:
            for b in ids:
                if a >= b or a in sep or b in sep:
                    continue
                x = o(a, b)
                marked = cls[a].get('revision') or cls[b].get('revision')
                if x is not None and x[0] >= SAME and x[1] >= SAME:
                    parent[find(a)] = find(b)
                    basis[a] = basis[b] = 'captions overlap'
                elif x is not None and x[0] >= SAME:
                    short, full = sorted((a, b), key=lambda v: len(cache[v]))
                    excerpt[short] = full
                elif x is None and cls[a].get('part', '') == cls[b].get('part', '') and marked:
                    parent[find(a)] = find(b)
                    basis.setdefault(a, 'title says revision')
                    basis.setdefault(b, 'title says revision')
        for v, d in decided.items():
            w = d.get('with_video', '')
            if d['status'] == 'same' and w in ids:
                parent[find(v)] = find(w)
                basis[v] = basis[w] = 'person decided: ' + d['why']
        members = collections.defaultdict(list)
        for v in ids:
            members[find(v)].append(v)
        for v in ids:
            grp = members[find(v)]
            best = max(((o(v, w)[0], w) for w in ids if w != v and o(v, w) is not None), default=(None, ''))
            newest = min(grp, key=lambda w: rank.get(w, 10 ** 9))
            if v in sep:
                rel, b, newest = 'separate recording', 'person decided: ' + decided[v]['why'], v
            elif len(grp) > 1:
                rel, b = 'same recording', basis[v]
            elif v in excerpt:
                rel, b = 'excerpt', 'most of it is inside a longer recording, ' + excerpt[v]
                newest = v
            else:
                measured = all(o(v, w) is not None for w in ids if w != v)
                rel = 'separate recording' if measured else 'unmeasured'
                b = 'captions overlap' if measured else 'no captions to compare'
            off = '' if v == newest else offset(cache[v], cache[newest]) if cache.get(v) and cache.get(newest) else None
            t = tr.get(v)
            rows.append({
                'board_slug': key[0], 'date': key[1], 'video_id': v, 'title': cls[v]['title'],
                'channel_rank': rank.get(v, ''), 'part': cls[v].get('part', ''),
                'revision': cls[v].get('revision', ''),
                'transcript_seconds': t['seconds'] if t else '',
                'relation': rel, 'group': newest if rel == 'same recording' else '',
                'newest': newest, 'offset_s': '0' if v == newest else ('' if off is None else str(off)),
                'basis': b,
                'best_overlap': '' if best[0] is None else '%.2f' % best[0],
                'overlap_with': best[1],
                'our_minutes': 'yes' if v in minutes[key] else '',
            })
    return rows


def render(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def report(rows):
    meetings = sorted({(r['board_slug'], r['date']) for r in rows})
    c = collections.Counter(r['relation'] for r in rows)
    out = ['# Meetings with more than one video', '',
           'Generated by `scripts/reconcile_meeting_videos.py`; do not edit. Every video is valid and '
           'kept. Videos of the SAME recording have their minutes reconciled into one by '
           '`merge_recording_minutes.py`.', '',
           '**%d meetings, %d videos:** %s.' % (len(meetings), len(rows),
                                                 ', '.join('%d %s' % (n, s) for s, n in c.most_common())), '',
           'Same recording: at least %d%% of each transcript\'s six-word runs occur in the other. '
           'Excerpt: that holds for the shorter only. `offset` is how far that video\'s clock sits from '
           'the newest upload\'s, measured from the runs both share.' % (SAME * 100), '',
           '| date | board | video | relation | overlap | offset | our minutes |', '|---|---|---|---|---:|---:|---|']
    for r in sorted(rows, key=lambda r: (r['date'], r['board_slug'], str(r['channel_rank'])), reverse=True):
        out.append('| %s | %s | [%s](https://www.youtube.com/watch?v=%s) | %s | %s | %s | %s |' % (
            r['date'], r['board_slug'], r['title'].replace('|', '/'), r['video_id'],
            r['relation'], r['best_overlap'], r['offset_s'], r['our_minutes']))
    return '\n'.join(out) + '\n'


def same_recording():
    """{video_id: [every video id of the same recording, newest first]} -- only videos in a group."""
    if not os.path.exists(OUT):
        return {}
    rows = [r for r in read_csv(OUT) if r.get('relation') == 'same recording']
    by = collections.defaultdict(list)
    for r in sorted(rows, key=lambda r: int(r['channel_rank'] or 10 ** 9)):
        by[(r['board_slug'], r['date'], r['group'])].append(r['video_id'])
    return {v: g for g in by.values() for v in g}


def offsets():
    """{video_id: seconds to add to land on its group's newest upload}; absent where unmeasured."""
    if not os.path.exists(OUT):
        return {}
    return {r['video_id']: int(r['offset_s']) for r in read_csv(OUT)
            if r.get('relation') == 'same recording' and r.get('offset_s') not in ('', None)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows = build()
    want = {OUT: render(rows), REPORT: report(rows)}
    if a.check:
        bad = [p for p, s in want.items() if not os.path.exists(p) or open(p, encoding='utf-8').read() != s]
        if bad:
            raise SystemExit('stale: %s -- run scripts/reconcile_meeting_videos.py'
                             % ', '.join(os.path.relpath(p, ROOT) for p in bad))
        print('ok -- %d videos in multi-video meetings' % len(rows))
        return
    # WHAT CHANGED, so the daily run can say so: a meeting newly recorded twice is news --
    # usually the town re-posting it -- and its minutes now have two sources to reconcile.
    before = same_recording()
    for r in rows:
        if r['relation'] == 'same recording' and r['video_id'] not in before and r['video_id'] == r['newest']:
            print('NEWLY RE-POSTED: %s %s -- %s joins %s (%s)' % (
                r['date'], r['board_slug'], r['video_id'],
                ', '.join(x['video_id'] for x in rows if x['group'] == r['group'] and x is not r), r['basis']))
    for p, s in want.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p + '.tmp', 'w', encoding='utf-8') as fh:
            fh.write(s)
        os.replace(p + '.tmp', p)
    c = collections.Counter(r['relation'] for r in rows)
    print('wrote %s -- %d videos: %s' % (os.path.relpath(OUT, ROOT), len(rows), dict(c)))


if __name__ == '__main__':
    main()
