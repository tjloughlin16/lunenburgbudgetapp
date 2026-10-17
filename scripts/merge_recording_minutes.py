#!/usr/bin/env python3
"""One meeting recorded twice: both sets of our minutes, reconciled into the best account.

    python3 scripts/merge_recording_minutes.py            # write the report
    python3 scripts/merge_recording_minutes.py --check    # fail if it is stale

WHY. TJ, 17 October 2026: *"we should reconcile both processed minutes to find the best
outcome"* and *"treat them both as valid"*. reconcile_meeting_videos.py says which videos are
the same recording; this lines their minutes up and keeps the union.

HOW TWO ITEMS ARE ONE. Each set of minutes cites the second it heard a thing, on its own
video's clock. A re-upload need not share that clock -- Town Meeting 2 May 2026's edit cut two
hours from the middle -- so no single offset maps one onto the other. Each moment is mapped
LOCALLY instead: the six-word caption runs both transcripts share within 90 seconds of it give
the shift there, and a moment with no shared run near it was not in the other recording at
all. Two items are the same when they sit in the same list, land within 90 seconds of each
other once mapped, and share enough words (votes 0.3, the rest 0.2, by token overlap).

WHICH WORDING WINS, item by item, never recording by recording:
  - a vote whose outcome was heard beats one marked "not audible";
  - otherwise the newest upload's wording (the town re-posts to fix something).
An item found in only one recording is kept, and says which. Nothing is dropped.

THE HEADLINE AND SUMMARY come from the newest upload unless it heard fewer votes than another
recording of the meeting, in which case from the one that heard the most -- the 2026 Town
Meeting edit lost fifteen of thirty-three votes, and a headline written from it would lead
with less than the meeting did.

Read by build_threads.py and build_boards.py, through `merged()`.
"""
import argparse
import collections
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import reconcile_meeting_videos as MV  # noqa: E402

MINUTES = os.path.join(ROOT, 'sources', 'data', 'recording-minutes')
TRANSCRIPTS = os.path.join(ROOT, 'sources', 'data', 'youtube-transcripts')
REPORT = os.path.join(ROOT, 'notes', 'generated', 'MERGED-MINUTES.md')
NEAR = 90
LISTS = {'votes': 'motion', 'decisions': 'decision', 'budget_items': 'topic', 'transfers': 'description',
         'contention': 'about', 'concerns_and_conditions': 'about', 'public_comment': 'topic', 'topics': 'topic'}
TIME = {'topics': 't_start'}


def words(s):
    return set(re.findall(r'[a-z0-9]{3,}', (s or '').lower()))


def jaccard(a, b):
    a, b = words(a), words(b)
    return len(a & b) / len(a | b) if a and b else 0.0


def runs(board, date, vid):
    p = os.path.join(TRANSCRIPTS, board, '%s-%s.json' % (date, vid))
    if not os.path.exists(p):
        return None
    return MV.shingles(p)


def mapper(a, b):
    """t on a's clock -> t on b's clock, or None where b has nothing near that moment."""
    if not a or not b:
        return lambda t: None
    pairs = sorted((a[k], b[k]) for k in set(a) & set(b))
    ta = [p[0] for p in pairs]
    import bisect

    def f(t):
        if t is None:
            return None
        lo, hi = bisect.bisect_left(ta, t - NEAR), bisect.bisect_right(ta, t + NEAR)
        d = sorted(pairs[i][1] - pairs[i][0] for i in range(lo, hi))
        return None if len(d) < 3 else t + d[len(d) // 2]
    return f


def files(board, date):
    out = {}
    for p in glob.glob(os.path.join(MINUTES, board, date + '-*.json')):
        out[os.path.basename(p)[len(date) + 1:-5]] = p
    return out


def merged(board, date, group):
    """The reconciled minutes of one recording group, or None if fewer than two have minutes.

    `group` is the video ids, newest first. Returns {'videos': [...], 'headline', 'summary',
    'headline_from', <list>: [item + {'video_id', 't', 'heard_in'}], 'counts': {...}}."""
    have = files(board, date)
    vids = [v for v in group if v in have]
    if len(vids) < 2:
        return None
    mins = {v: json.load(open(have[v], encoding='utf-8')) for v in vids}
    clock = {v: runs(board, date, v) for v in vids}
    maps = {(a, b): mapper(clock[a], clock[b]) for a in vids for b in vids if a != b}
    out = {'videos': vids, 'counts': {}}
    for name, field in LISTS.items():
        tk = TIME.get(name, 't')
        acc = []                                   # merged items so far, each with its own clock
        for v in vids:                             # newest first, so its wording is met first
            for idx, it in enumerate(mins[v]['minutes'].get(name) or []):
                t = it.get(tk)
                best, score = None, 0.0
                for m in acc:
                    if m['video_id'] == v or v in m['heard_in']:
                        continue
                    mt = maps[(v, m['video_id'])](t)
                    if mt is None or m.get(tk) is None or abs(mt - m[tk]) > NEAR:
                        continue
                    s = jaccard(it.get(field), m.get(field))
                    # Within half a minute the clock is the stronger evidence: "Motion to
                    # adjourn" and "Adjourn the meeting" share one word and are one vote.
                    need = 0.15 if abs(mt - m[tk]) <= 30 else (0.3 if name == 'votes' else 0.2)
                    if s >= need and s > score:
                        best, score = m, s
                if best is None:
                    acc.append(dict(it, video_id=v, heard_in=[v], members=[[v, idx]]))
                    continue
                best['heard_in'].append(v)
                best['members'].append([v, idx])
                if name == 'votes' and best.get('outcome') == 'not audible' and it.get('outcome') not in (None, '', 'not audible'):
                    keep, mem = best['heard_in'], best['members']
                    best.clear()
                    best.update(dict(it, video_id=v, heard_in=keep, members=mem))
        # WAS IT CUT, OR DID WE NOT WRITE IT DOWN? An item one recording's minutes lack is one
        # of two things, and TJ wants them told apart (*"so we can see when content was lost
        # specifically"*): the moment is not in the other recording at all -- no caption runs
        # they share sit near it -- or it is there and that set of minutes simply did not
        # note it. The first is `absent_from`: content lost. The second is `unnoted_in`.
        for m in acc:
            m['absent_from'], m['unnoted_in'] = [], []
            for w in vids:
                if w in m['heard_in']:
                    continue
                (m['unnoted_in'] if maps[(m['video_id'], w)](m.get(tk)) is not None else m['absent_from']).append(w)
        out[name] = acc
        out['counts'][name] = {'both': sum(1 for m in acc if len(m['heard_in']) > 1),
                               'only': {v: sum(1 for m in acc if m['heard_in'] == [v]) for v in vids},
                               'cut_from': {v: sum(1 for m in acc if v in m['absent_from']) for v in vids}}
    nv = {v: len(mins[v]['minutes'].get('votes') or []) for v in vids}
    lead = vids[0] if nv[vids[0]] >= max(nv.values()) else max(vids, key=lambda v: nv[v])
    out['headline'] = mins[lead]['minutes'].get('headline', '')
    out['summary'] = mins[lead]['minutes'].get('summary', '')
    out['headline_from'] = lead
    return out


def roles(group):
    """{video_id: 'the original' | 'the edited video' | 'the re-upload'} -- the words a label uses.
    Oldest upload is the original; a newer one is 'the edited video' when its title says its
    AUDIO was revised (Audio Fix, audio edited, Audio Revision), otherwise 'the re-upload' -- a
    corrected date is not an edit of the recording."""
    import csv
    rows = {r['video_id']: r for r in csv.DictReader(open(MV.OUT, encoding='utf-8')) if r['video_id'] in group}
    order = sorted(group, key=lambda v: -int(rows.get(v, {}).get('channel_rank') or 0))
    out = {}
    for i, v in enumerate(order):
        edited = 'audio' in (rows.get(v, {}).get('revision') or '').lower()
        out[v] = 'the original' if i == 0 else ('the edited video' if edited else 'the re-upload')
    return out


def label(item, role):
    """The words beside an item: lost content first, then a note-taking difference, else none."""
    if item.get('absent_from'):
        return 'missing from ' + ' and '.join(role[w] for w in item['absent_from'])
    if item.get('unnoted_in'):
        return 'noted only from ' + role[item['video_id']]
    return ''


def annotations(board, date, group):
    """What each recording's own minutes page needs: {video_id: {'role', 'others': [{video_id,
    role}], 'labels': {list: {index: label}}, 'missing_here': [{list, text, t, video_id, role}],
    'counts': {...}}}. `labels` carries only LOST CONTENT -- an item whose moment is not in
    another recording; `missing_here` is the items heard only in another recording because
    this one does not have that moment at all."""
    m = merged(board, date, group)
    if not m:
        return {}
    role = roles(m['videos'])
    out = {v: {'role': role[v], 'others': [{'video_id': w, 'role': role[w]} for w in m['videos'] if w != v],
               'labels': {}, 'missing_here': []} for v in m['videos']}
    for name, field in LISTS.items():
        tk = TIME.get(name, 't')
        for it in m[name]:
            if it['absent_from']:
                lab = 'missing from ' + ' and '.join(role[w] for w in it['absent_from'])
                for v, idx in it['members']:
                    out[v]['labels'].setdefault(name, {})[str(idx)] = lab
                for w in it['absent_from']:
                    out[w]['missing_here'].append({'list': name, 'text': it.get(field) or '',
                                                   'outcome': it.get('outcome') or '',
                                                   't': it.get(tk), 'video_id': it['video_id'],
                                                   'role': role[it['video_id']]})
    return out


def groups():
    """{(board, date): [video ids, newest first]} for every recording group with 2+ minutes."""
    out = {}
    import csv
    if not os.path.exists(MV.OUT):
        return out
    for r in csv.DictReader(open(MV.OUT, encoding='utf-8')):
        if r.get('relation') == 'same recording':
            out.setdefault((r['board_slug'], r['date'], r['group']), []).append((int(r['channel_rank'] or 10 ** 9), r['video_id']))
    res = {}
    for (b, d, g), vs in out.items():
        ids = [v for _, v in sorted(vs)]
        if len([v for v in ids if v in files(b, d)]) >= 2:
            res.setdefault((b, d), []).append(ids)
    return res


def report():
    lines = ['# Meetings recorded twice: both sets of minutes, reconciled', '',
             'Generated by `scripts/merge_recording_minutes.py`; do not edit. Both recordings are valid. '
             'Each item is matched across them by the moment it was said (mapped locally through the '
             'captions both share) and its words; an item heard in only one is kept.', '',
             '**Cut** counts items whose moment is not in that recording at all -- content lost from it. '
             'The rest of "only in one" is a difference in what our two sets of minutes noted.', '',
             '| date | board | recordings | votes in both | votes only in one | votes cut from | other items in both | other items cut from | headline from |',
             '|---|---|---:|---:|---|---|---:|---|---|']
    for (b, d), gs in sorted(groups().items(), reverse=True):
        for g in gs:
            m = merged(b, d, g)
            if not m:
                continue
            c = m['counts']
            vo = ', '.join('%s %d' % (v, n) for v, n in c['votes']['only'].items())
            both = sum(x['both'] for k, x in c.items() if k != 'votes')
            only = collections.Counter()
            for k, x in c.items():
                if k != 'votes':
                    only.update(x['only'])
            role = roles(g)
            cut = collections.Counter()
            for k, x in c.items():
                if k != 'votes':
                    cut.update(x['cut_from'])
            name = lambda v: '%s (%s)' % (role[v], v)
            lines.append('| %s | %s | %d | %d | %s | %s | %d | %s | %s |' % (
                d, b, len(m['videos']), c['votes']['both'],
                ', '.join('%s %d' % (name(v), n) for v, n in c['votes']['only'].items()),
                ', '.join('%s %d' % (name(v), n) for v, n in c['votes']['cut_from'].items() if n) or 'none',
                both, ', '.join('%s %d' % (name(v), n) for v, n in cut.items() if n) or 'none',
                name(m['headline_from'])))
    return '\n'.join(lines) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    want = report()
    if a.check:
        if not os.path.exists(REPORT) or open(REPORT, encoding='utf-8').read() != want:
            raise SystemExit('stale: %s -- run scripts/merge_recording_minutes.py' % os.path.relpath(REPORT, ROOT))
        print('ok')
        return
    with open(REPORT + '.tmp', 'w', encoding='utf-8') as fh:
        fh.write(want)
    os.replace(REPORT + '.tmp', REPORT)
    print(want)


if __name__ == '__main__':
    main()
