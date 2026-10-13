#!/usr/bin/env python3
"""The recording-minutes payloads the site serves, generated from the minutes files.

    python3 scripts/build_recording_minutes.py           # write the index and every shard
    python3 scripts/build_recording_minutes.py --check   # fail if any no longer reproduces

Every meeting for which `write_recording_minutes.py` has produced minutes, newest first,
with the town's own documents for that meeting linked beside ours. The page
/meeting-minutes renders it: an index by board, and one page per recording.

TWO KINDS OF FILE, NOT ONE. Until 13 October 2026 this was a single file holding every
meeting in full; it reached 25.4 MiB indented, past the 25 MiB a Cloudflare Pages file may
be, and a page showing ONE meeting downloaded all of them. So:

    fy28/public/data/recording-minutes.json                     THE INDEX: every meeting's
        metadata (board, date, headline, tags, counts, where its full minutes are), the
        per-board time-by-subject and the counts. What the list pages, the sitemap and the
        prerender read. Same address as the old combined file, so a link to it still
        answers -- with the index rather than the minutes.
    fy28/public/data/recording-minutes/<board>/<year>.json      ONE SHARD PER BOARD AND
        CALENDAR YEAR: the same meeting entries, in full -- the minutes, the reconciliation
        against the town's minutes, the digest. A meeting page fetches only its own shard,
        whose address it derives from its own slug.

Per board-year rather than per meeting because Cloudflare Pages also caps a deploy at
20,000 files and the build already holds most of that; a shard per meeting would add one
file per meeting, forever. Not served from R2 because the bucket is write-once: an object
under a fixed key can never be replaced, and these change every day.

AND NO FILE THIS WRITES MAY PASS MAX_BYTES. The generator refuses to write anything if one
would -- all or nothing -- so the Pages limit can never again be found by a failed deploy.

Counts here are derived from the files and never typed. The `warning` travels in the index
and in every shard because the payloads are fetched by things other than the page.
Python consumers call `payload()` and get the full combined shape, from the sources.
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
SHARDS = os.path.join(ROOT, 'fy28', 'public', 'data', 'recording-minutes')
# Cloudflare Pages refuses a file over 25 MiB. Refuse well before it, so the warning comes
# from this script and not from a deploy.
MAX_BYTES = 15_000_000
# What the index carries per meeting. Everything else -- the minutes themselves, the
# reconciliation, the digest, the per-meeting time by subject, the transcript provenance --
# is in the meeting's shard.
INDEX_FIELDS = ('slug', 'board_slug', 'board', 'date', 'video_id', 'video_url', 'headline',
                'confidence', 'tags', 'recording', 'counts', 'town_published',
                'has_official_minutes', 'discrepancies', 'caption_errors', 'written')
PAGES = os.path.join(ROOT, 'sources', 'data', 'board-pages.csv')

# ----------------------------------------------------------------- names, as posted
#
# THE CAPTION MODEL HEARS "MANNY GILMAN'S" AND THE PAGE PRINTED IT. Every meeting's
# attendee list is the caption model's hearing of real elected officials' names --
# "Manny Gilman's", "Chris Manard", "Jean", "Laura" -- and it was rendered on a public
# page with a small caveat after it. A member reading their own name mangled is the
# person most likely to write in about this site, and the town publishes the roster the
# hearing can be checked against: `board-pages.csv`, every board's members as posted.
#
# So each heard attendee is matched to the posted roster of the board that met -- or of
# the board their stated role names -- and the page shows the POSTED name where the match
# is unambiguous, with the heard form kept in the data. The match is an inference (rule
# 7) and the payload says how it was made: `exact`, `surname`, `first-name` (unique on
# that roster) or `fuzzy` (both name parts within a letter or two). Anything ambiguous,
# anything whose role does not sound like a seat on the board, and every placeholder
# ("the chair (name not stated)") is left as heard.
#
# AND THE ROSTER IS EVIDENCE OF A SEAT ONLY FOR THE CURRENT TERM. A page fetched in
# September 2026 says who sits now; it does not say who sat in April 2024, and "Laura
# (member)" at a 2024 meeting may be somebody else entirely. A term that expires in year
# Y on a three-year seat began in May of Y-3 at the latest, so a member is matched only
# for meetings on or after that date. A roster line with no term (an appointed committee)
# is trusted for the year before it was fetched and no further. Under-matching is the
# safe direction: a name left as heard is an unresolved caption; a name resolved to the
# wrong person is a published error about a real one.

import csv
import re

SEAT = re.compile(r'\b(chair|vice|clerk|secretary|member|presiding)\b', re.I)
PLACEHOLDER = re.compile(r'not stated|unnamed|\bthe chair\b|chairman|madam|\bthe (chief|superintendent|town manager)\b', re.I)
HONORIFIC = re.compile(r'^(dr|mr|mrs|ms|miss)\.?\s+', re.I)
# The roster uses whichever form the member chose; the captions use whichever the room
# used. Both directions, small, and only for names that occur on a Lunenburg roster.
NICK = {'tony': 'anthony', 'mike': 'michael', 'chris': 'christopher', 'dave': 'david',
        'jen': 'jennifer', 'jenny': 'jennifer', 'tom': 'thomas', 'matt': 'matthew',
        'dan': 'daniel', 'mandy': 'amanda', 'deb': 'deborah', 'jay': 'jason',
        'tim': 'timothy', 'steve': 'steven', 'bill': 'william', 'kim': 'kimberly',
        'pat': 'patrick', 'rich': 'richard', 'kathy': 'katherine', 'liz': 'elizabeth'}


def canon_first(t):
    t = t.lower()
    return NICK.get(t, t)


def first_dist(a, b):
    """How far apart two first names are, as spoken or as given: "Manny" is one letter
    from "Mandy", and "Tony" is "Anthony" -- either route counts."""
    return min(edit(a, b), edit(canon_first(a), canon_first(b)))


def edit(a, b):
    """Levenshtein, small strings only."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


TERM = re.compile(r'term[^0-9]*(20\d\d)', re.I)
TERM_YEARS = 3


def rosters():
    """{board slug: [(posted name, posted role, seated-since ISO date)]} from the
    town's board pages."""
    out = {}
    if not os.path.exists(PAGES):
        return out
    for row in csv.DictReader(open(PAGES, encoding='utf-8')):
        seats = []
        fetched = (row.get('fetched_at') or '')[:10]
        for line in row['members'].split('\n'):
            line = line.strip()
            if not line or line.lower().startswith(('the ', 'please', 'email', 'vacancy')):
                continue
            head = re.split(r'\s+[\u2014\u2013-]\s+|\s*\(', line, 1)[0]
            parts = [p.strip() for p in head.split(',')]
            name = parts[0]
            toks = name.split()
            if not 2 <= len(toks) <= 4 or not all(t[0].isupper() for t in toks):
                continue
            t = TERM.search(line)
            if t:
                since = '%d-05-01' % (int(t.group(1)) - TERM_YEARS)
            elif fetched:
                since = '%d%s' % (int(fetched[:4]) - 1, fetched[4:])
            else:
                continue
            seats.append((name, parts[1] if len(parts) > 1 else '', since))
        if seats:
            out[row['slug']] = seats
    return out


def match_seat(heard, role, roster, date):
    if not roster or PLACEHOLDER.search(heard) or not SEAT.search(role or ''):
        return None
    roster = [r for r in roster if r[2] <= date]
    h = re.split(r'\s*[/(]', heard, 1)[0]
    h = HONORIFIC.sub('', h.strip())
    ht = [t.lower().replace("'s", '') for t in re.findall(r"[A-Za-z][A-Za-z'\-]*", h)]
    if not ht:
        return None
    found = []
    for name, prole, _since in roster:
        nt = name.lower().split()
        first, last = nt[0], nt[-1]
        if ' '.join(ht) == ' '.join(nt):
            found.append((name, prole, 'exact'))
        elif last in ht and (len(ht) == 1 or first_dist(ht[0], first) <= 2):
            found.append((name, prole, 'surname'))
        elif len(ht) == 1 and canon_first(ht[0]) == canon_first(first):
            found.append((name, prole, 'first-name'))
        elif len(ht) >= 2 and first_dist(ht[0], first) <= 1 and edit(ht[-1], last) <= 2:
            found.append((name, prole, 'fuzzy'))
    # One seat, or none. Two members who share a first name are a list of two, and the
    # page must not pick.
    return found[0] if len(found) == 1 else None


def roster_for(board_slug, role, all_rosters):
    """The board that met, unless the stated role names another board -- "school
    committee member" at a Finance Committee meeting is matched against the School
    Committee's roster."""
    r = (role or '').lower()
    for slug in all_rosters:
        words = slug.replace('-', ' ')
        if slug != board_slug and words in r:
            return all_rosters[slug]
    return all_rosters.get(board_slug)


def with_posted_names(attendees, board_slug, date, all_rosters):
    out = []
    for a in attendees:
        a = dict(a)
        m = match_seat(a.get('name_as_heard', ''), a.get('role', ''),
                       roster_for(board_slug, a.get('role', ''), all_rosters), date)
        if m:
            a['posted_name'], a['posted_role'], a['matched_by'] = m
        out.append(a)
    return out


def payload():
    items = []
    all_rosters = rosters()
    for f in sorted(glob.glob(os.path.join(W.OUT, '*', '*.json'))):
        m = json.load(open(f, encoding='utf-8'))
        mm = dict(m['minutes'])
        mm['attendees'] = with_posted_names(mm.get('attendees', []), m['board_slug'], m['meeting_date'], all_rosters)
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
            'headline': mm.get('headline', ''),
            'summary': mm['summary'],
            'confidence': mm['confidence'],
            'tags': mm.get('tags', []),
            'recording': m.get('recording'),
            'counts': {'votes': len(votes), 'procedural_votes': len(mm['votes']) - len(votes),
                       'transfers': len(mm['transfers']), 'budget_items': len(mm['budget_items']),
                       'decisions': len(mm['decisions']), 'topics': len(mm['topics']),
                       'public_comment': len(mm.get('public_comment', [])),
                       'attendees': len(mm.get('attendees', [])),
                       'attendees_matched': sum(1 for a in mm['attendees'] if a.get('posted_name')),
                       'not_audible': len(mm['not_audible'])},
            'town_published': m['town_published'],
            'has_official_minutes': any(d['kind'] == 'minutes' for d in m['town_published']),
            'discrepancies': (m.get('reconciliation') or {}).get('counts', {}).get('discrepancy', 0),
            'caption_errors': (m.get('reconciliation') or {}).get('counts', {}).get('caption_error', 0),
            'source': m['source'],
            'written': m['written'],
            'minutes': mm,
            'reconciliation': m.get('reconciliation'),
            'digest': m.get('digest'),
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


def shard_path(board_slug, date):
    """Where a meeting's full entry is published, relative to /data/. The page derives the
    same address from the meeting's slug (WhatWasSaid.tsx, shardFile)."""
    return 'recording-minutes/%s/%s.json' % (board_slug, date[:4])


def dump(obj):
    return json.dumps(obj, separators=(',', ':'), ensure_ascii=False) + '\n'


def render():
    """{absolute path: text} for every file this generator owns."""
    p = payload()
    shards = {}
    for m in p['meetings']:
        shards.setdefault(shard_path(m['board_slug'], m['date']), []).append(m)
    out = {}
    for rel, items in sorted(shards.items()):
        out[os.path.join(ROOT, 'fy28', 'public', 'data', rel)] = dump({
            'warning': p['warning'],
            'what': p['what'],
            'board_slug': items[0]['board_slug'],
            'board': items[0]['board'],
            'year': items[0]['date'][:4],
            'index': '/data/recording-minutes.json',
            'counts': {'meetings': len(items)},
            'meetings': items,
        })
    index = {k: v for k, v in p.items() if k != 'meetings'}
    index['shards'] = ('The full minutes of each meeting -- votes, topics, the reconciliation '
                       'against the town\'s minutes, the digest -- are in one file per board '
                       'and calendar year, at the `data` address beside each meeting.')
    index['meetings'] = []
    for m in p['meetings']:
        e = {k: m[k] for k in INDEX_FIELDS}
        # The list shows the headline, or the summary where the model wrote no headline;
        # the index carries whichever the list would show, not both.
        e['headline'] = m['headline'] or m['summary']
        e['reconciled'] = bool(m.get('reconciliation'))
        e['data'] = '/data/' + shard_path(m['board_slug'], m['date'])
        index['meetings'].append(e)
    out[OUT] = dump(index)
    return out


def existing():
    """Every file this generator owns that is on disk now."""
    have = glob.glob(os.path.join(SHARDS, '*', '*.json'))
    return set(have + ([OUT] if os.path.exists(OUT) else []))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    files = render()
    big = [(f, len(t.encode('utf-8'))) for f, t in files.items() if len(t.encode('utf-8')) > MAX_BYTES]
    if big:
        for f, n in big:
            print('REFUSED: %s would be %s bytes, past MAX_BYTES %s (Cloudflare Pages refuses a '
                  'file over 25 MiB). Shard it finer.' % (os.path.relpath(f, ROOT), format(n, ','),
                                                         format(MAX_BYTES, ',')))
        return 2
    stray = existing() - set(files)
    if a.check:
        bad = 0
        for f, text in sorted(files.items()):
            have = open(f, encoding='utf-8').read() if os.path.exists(f) else ''
            if have != text:
                print('STALE: %s — run build_recording_minutes.py' % os.path.relpath(f, ROOT))
                bad += 1
        for f in sorted(stray):
            print('STRAY: %s is no longer generated — run build_recording_minutes.py' % os.path.relpath(f, ROOT))
            bad += 1
        if bad:
            return 1
        print('ok: %s and %d shard(s) reproduce' % (os.path.relpath(OUT, ROOT), len(files) - 1))
        return 0
    # Shards first, the index last: a reader that sees the new index finds every shard it
    # names. Each file atomically, so a crash never leaves a truncated one.
    for f in sorted(files, key=lambda f: f == OUT):
        os.makedirs(os.path.dirname(f), exist_ok=True)
        have = open(f, encoding='utf-8').read() if os.path.exists(f) else None
        if have == files[f]:
            continue
        tmp = f + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            fh.write(files[f])
        os.replace(tmp, f)
    for f in stray:
        os.remove(f)
    for d in glob.glob(os.path.join(SHARDS, '*')):
        if os.path.isdir(d) and not os.listdir(d):
            os.rmdir(d)
    p = json.loads(files[OUT])
    largest = max(files.items(), key=lambda kv: len(kv[1].encode('utf-8')))
    print('wrote %s and %d shard(s) — %d meeting(s), %d board(s), %d with no official minutes; '
          'largest file %s, %s bytes'
          % (os.path.relpath(OUT, ROOT), len(files) - 1, p['counts']['meetings'], p['counts']['boards'],
             p['counts']['without_official_minutes'], os.path.relpath(largest[0], ROOT),
             format(len(largest[1].encode('utf-8')), ',')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
