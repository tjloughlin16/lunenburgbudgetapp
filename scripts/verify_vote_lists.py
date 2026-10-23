#!/usr/bin/env python3
"""VERIFY THE VOTE LISTS, BY A SECOND ROUTE.

    python3 scripts/verify_vote_lists.py

build_vote_lists.py regroups the Town Meeting register and build_boards.py's join into
fy28/public/data/town-meeting-votes.json and fy28/public/data/votes/<board>.json. This reads the
payloads and checks each against the SOURCES, not against the generator's own arithmetic:

  1. COUNTS. Articles per Town Meeting equal the register's `articles` (town-meetings.csv), and
     the undated groups hold every Clerk row with no meeting date. Votes per board per fiscal year
     equal boards.json's, counted afresh.
  2. QUOTES. A quote shown as verbatim is found in its document by a different comparison than the
     generator's -- the words only, every non-alphanumeric dropped. A Town Meeting result "as heard"
     is a motion in our minutes of that meeting's video, word for word.
  3. LABELS. Every vote's plain-words caveat is the one its record calls for, recomputed from the
     register; no vote resting on a record carries one, and none resting on a video lacks one.
  4. PER-YEAR COVERAGE. Each fiscal year's counts recompute from warrant-articles.csv and
     town-meeting-votes.csv (Town Meeting) or meeting-register.csv (boards).
  5. LINKS. Every /docs/ link is a document in the archive manifest; every video link is a video id
     on record, and a link labelled "Video at" carries &t=; every /meeting-minutes/ link is a file
     of ours; every town URL is one a catalogue or the register records.

Exit status 1 on any failure.
"""
import collections
import csv
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
DATA = os.path.join(ROOT, 'sources', 'data')
PUB = os.path.join(ROOT, 'fy28', 'public', 'data')

FAIL = []


def fail(msg):
    FAIL.append(msg)


def read_csv(p):
    return list(csv.DictReader(open(p, newline='', encoding='utf-8')))


def words(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


_DOC = {}


def doc_words(path):
    if path not in _DOC:
        p = os.path.join(ROOT, path)
        t = open(p, encoding='utf-8', errors='replace').read() if os.path.exists(p) else ''
        _DOC[path] = words(t)
    return _DOC[path]


def fy_of(d):
    return int(d[:4]) + 1 if d[5:7] >= '07' else int(d[:4])


# ---------------------------------------------------------------------------------- links
MANIFEST = {r['key'] for r in read_csv(os.path.join(DATA, 'archive-manifest.csv'))}
VIDEOS = {r['video_id'] for r in read_csv(os.path.join(DATA, 'youtube-video-boards.csv'))}
TOWN = set()
for idx in glob.glob(os.path.join(ROOT, 'sources', '*', 'index.csv')):
    for r in read_csv(idx):
        for k in ('upstream', 'url'):
            TOWN.update((r.get(k) or '').split())
REG = {(r['board_slug'], r['date']): r for r in read_csv(os.path.join(DATA, 'meeting-register.csv'))
       if r.get('board_slug') and r.get('date')}
for r in REG.values():
    TOWN.update((r.get('minutes_url') or '', r.get('agenda_url') or ''))
THREADS = {t['id'] for t in json.load(open(os.path.join(PUB, 'threads.json'), encoding='utf-8'))['threads']}
checked_links = collections.Counter()


def check_link(where, l):
    h = l['href']
    if not h:
        fail('%s: empty link %r' % (where, l['label']))
    elif h.startswith('/docs/'):
        key = h[len('/docs/'):].split('#')[0]
        if key not in MANIFEST:
            fail('%s: %s is not a document in the archive manifest' % (where, h))
        checked_links['docs'] += 1
    elif h.startswith('https://www.youtube.com/watch?v='):
        vid = re.search(r'v=([\w-]+)', h).group(1)
        if vid not in VIDEOS:
            fail('%s: video %s is not on record' % (where, vid))
        if l['label'].startswith('Video at') and not re.search(r'[?&]t=\d+s?\b', h):
            fail('%s: %r has no timestamp' % (where, l['label']))
        checked_links['video'] += 1
    elif h.startswith('/meeting-minutes/'):
        slug, rest = h[len('/meeting-minutes/'):].split('/', 1)
        if not os.path.exists(os.path.join(DATA, 'recording-minutes', slug, rest + '.json')):
            fail('%s: %s is not a file of our minutes' % (where, h))
        checked_links['ours'] += 1
    elif h.startswith('/threads/'):
        if h[len('/threads/'):] not in THREADS:
            fail('%s: thread %s does not exist' % (where, h))
        checked_links['thread'] += 1
    elif h.startswith('https://www.lunenburgma.gov/'):
        if h not in TOWN:
            fail('%s: town URL %s is recorded nowhere' % (where, h))
        checked_links['town'] += 1
    else:
        fail('%s: unrecognised link %s' % (where, h))


# ---------------------------------------------------------------------------------- town meeting
HELD = {int(m.group(1)) for r in read_csv(os.path.join(ROOT, 'sources', 'town-annual-reports', 'index.csv'))
        for m in [re.search(r'FY\s?(\d{4}) Annual Town Report', r['label'])] if m and r['local']}


def report_for(g, v):
    """The annual report that prints (or would print) this article's Clerk's record: the one its
    record cites, else the meeting's calendar year (every dated Clerk row obeys that), else the
    undated group's own year."""
    m = re.search(r'fy-(\d{4})-annual-town-report', v.get('record_doc') or '')
    return int(m.group(1)) if m else (int(g['date'][:4]) if g['date'] else g['fy'])


def town_meeting():
    p = json.load(open(os.path.join(PUB, 'town-meeting-votes.json'), encoding='utf-8'))
    reg = {m['id']: m for m in read_csv(os.path.join(DATA, 'town-meetings.csv'))}
    arts = read_csv(os.path.join(DATA, 'warrant-articles.csv'))
    clerk = read_csv(os.path.join(DATA, 'town-meeting-votes.csv'))
    groups = {g['id']: g for g in p['groups']}
    for mid, m in reg.items():
        g = groups.get(mid)
        if g is None:
            fail('town meeting %s is in the register and not on the page' % mid)
        elif len(g['votes']) != int(m['articles'] or 0):
            fail('%s: %d articles on the page, %s in the register' % (mid, len(g['votes']), m['articles']))
    undated = [g for g in p['groups'] if not g['date_printed']]
    n_und = sum(len(g['votes']) for g in undated)
    n_clerk_und = sum(1 for r in clerk if not r['meeting_date'])
    if n_und != n_clerk_und:
        fail('undated groups hold %d votes; the Clerk prints %d with no date' % (n_und, n_clerk_und))
    if sum(len(g['votes']) for g in p['groups']) != len(arts) + n_clerk_und:
        fail('town meeting: %d rows on the page, %d articles + %d undated in the sources'
             % (sum(len(g['votes']) for g in p['groups']), len(arts), n_clerk_und))

    verb = heard = 0
    for g in p['groups']:
        for v in g['votes']:
            w = '%s %s' % (g['id'], v['n'])
            for l in v['links']:
                check_link(w, l)
            for r in v.get('recs') or []:
                if r['href']:
                    check_link(w, {'label': r['who'], 'href': r['href']})
            # the chips match the basis, recomputed: the Clerk's record held -> its tick; otherwise a
            # a "From video" chip iff the result is ours, then a missing-record chip naming whether the report is held
            texts = [c['text'] for c in v['chips']]
            y = report_for(g, v)
            if not 1 <= len(texts) <= 2:
                fail('%s: %d chips' % (w, len(texts)))
            if v['basis'] == 'clerk':
                want = ["Clerk's record ✓"]
            elif g['status'].startswith('Upcoming') and v['result'] in ('not yet voted', 'kept off the warrant'):
                want = ['Not voted yet']
            else:
                want = (['From video'] if v['basis'] == 'ours' else []) + ["Clerk's record not found" if y in HELD else "No Clerk's record yet"]
            if texts != want:
                fail('%s: chips %s, the record calls for %s' % (w, texts, want))
            if v['basis'] == 'ours' and 'may be wrong' not in v['basis_note']:
                fail('%s: a result from the video does not say it may be wrong' % w)
            if not v['basis_note']:
                fail('%s: no sentence saying where the result comes from' % w)
            for c in v['chips']:
                if c['href']:
                    check_link(w, {'label': c['text'], 'href': c['href']})
            if v['quote_kind'] == 'verbatim':
                verb += 1
                if not v['record_doc'] or words(v['quote']) not in doc_words(v['record_doc']):
                    fail('%s: quote shown as verbatim is not in %s' % (w, v['record_doc']))
            elif v['quote_kind'] == 'as heard':
                heard += 1
                vid = re.search(r'v=([\w-]+)', v['links'][0]['href']).group(1)
                f = glob.glob(os.path.join(DATA, 'recording-minutes', 'town-meeting', '%s-%s.json' % (g['date'], vid)))
                motions = [x['motion'] for x in json.load(open(f[0], encoding='utf-8'))['minutes']['votes']] if f else []
                if v['quote'] not in motions:
                    fail('%s: "as heard" %r is not a motion in our minutes of %s' % (w, v['quote'][:60], vid))
    # per-FY coverage, recomputed from the sources: a register article's FY is its meeting's; an
    # undated Clerk row's is its report's
    fy_m = {mid: fy_of(m['date']) for mid, m in reg.items()}
    want = collections.defaultdict(collections.Counter)
    for a in arts:
        m = reg[a['meeting']]
        c = want[fy_m[a['meeting']]]
        if m['status'] == 'upcoming' or a['stage'] == 'kept off':
            c['upcoming'] += 1
            continue
        c['articles'] += 1
        c['clerk' if a['result_basis'] == 'official' else 'ours' if a['result_basis'] == 'ours' else 'none'] += 1
    for r in clerk:
        if not r['meeting_date']:
            want[int(r['fy'])]['articles'] += 1
            want[int(r['fy'])]['clerk'] += 1
    for fy, c in want.items():
        got = p['fy_coverage'].get(str(fy))
        if not got:
            fail('town meeting FY%d has no coverage line' % fy)
            continue
        for k in ('articles', 'clerk', 'ours', 'none', 'upcoming'):
            if got[k] != c[k]:
                fail('town meeting FY%d coverage %s = %d, the sources give %d' % (fy, k, got[k], c[k]))
            if k != 'articles' and c[k] and str(c[k]) not in got['text']:
                fail('town meeting FY%d coverage line does not state %s = %d' % (fy, k, c[k]))
    print('town meeting: %d meetings, %d articles; %d verbatim quotes and %d "as heard" checked; %d FY lines'
          % (len(p['groups']), sum(len(g['votes']) for g in p['groups']), verb, heard, len(want)))


# ---------------------------------------------------------------------------------- boards
def boards():
    b = json.load(open(os.path.join(PUB, 'boards.json'), encoding='utf-8'))
    files = {os.path.basename(f)[:-5]: f for f in glob.glob(os.path.join(PUB, 'votes', '*.json'))}
    want_boards = {x['slug'] for x in b['boards'] if x['votes']}
    if set(files) != want_boards:
        fail('vote files %s differ from boards with votes %s' % (sorted(set(files) ^ want_boards)[:5], ''))
    reg = REG
    horizon = max(max(r['minutes_first_seen'] or '', r['video_uploaded'] or '', r['our_minutes_written'] or '')
                  for r in reg.values())
    n_votes = n_quotes = n_cav = 0
    for x in b['boards']:
        if x['slug'] not in files:
            continue
        p = json.load(open(files[x['slug']], encoding='utf-8'))
        src = collections.Counter(fy_of(v['date']) for v in x['votes'])
        got = collections.Counter()
        for g in p['groups']:
            if g['fy'] != fy_of(g['date']):
                fail('%s %s: filed under FY%d' % (x['slug'], g['date'], g['fy']))
            r = reg.get((x['slug'], g['date']))
            for v in g['votes']:
                got[g['fy']] += 1
                n_votes += 1
                w = '%s %s' % (x['slug'], g['date'])
                for l in v['links']:
                    check_link(w, l)
                texts = [c['text'] for c in v['chips']]
                if v['basis'] == 'recording':
                    n_cav += 1
                    state = ('Town minutes unknown' if not r else 'Not in town minutes' if r['official_votes_path']
                             else 'Town minutes unread' if r['minutes'] == '1' else 'No town minutes yet')
                    want = ['From video', state]
                    if 'may be wrong' not in v['basis_note']:
                        fail('%s: a vote from the video does not say it may be wrong' % w)
                else:
                    want = ['Town minutes ✓'] + (['Also on video'] if v['basis'] == 'both' and any(
                        l['href'].startswith('https://www.youtube.com/') for l in v['links']) else [])
                if texts != want:
                    fail('%s: chips %s, the record calls for %s' % (w, texts, want))
                for c in v['chips']:
                    if c['href']:
                        check_link(w, {'label': c['text'], 'href': c['href']})
                if v['quote']:
                    n_quotes += 1
                    doc = next((l['href'] for l in v['links'] if l['href'].startswith('/docs/meetings/')), '')
                    txt = re.sub(r'\.\w+$', '.txt', doc.replace('/docs/meetings/', 'sources/meetings/text/'))
                    if not doc or words(v['quote']) not in doc_words(txt):
                        fail('%s: quote not verbatim in %s' % (w, txt or 'any linked minutes'))
        if got != src:
            fail('%s: votes per FY %s, boards.json gives %s' % (x['slug'], dict(got), dict(src)))
        # per-FY coverage, from the register
        want = collections.defaultdict(collections.Counter)
        for (s, d), r in reg.items():
            if s != x['slug'] or d > horizon:
                continue
            c = want[fy_of(d)]
            c['meetings'] += 1
            c['town_read' if r['official_votes_path'] else 'town_unread' if r['minutes'] == '1'
              else 'ours_only' if r['our_minutes_path'] else 'nothing'] += 1
        for fy, c in want.items():
            line = p['fy_coverage'].get(str(fy))
            if not line:
                fail('%s FY%d: no coverage line' % (x['slug'], fy))
                continue
            for k in ('meetings', 'town_read', 'town_unread', 'ours_only', 'nothing'):
                if line[k] != c[k]:
                    fail('%s FY%d: %s = %d, the register gives %d' % (x['slug'], fy, k, line[k], c[k]))
        for g in p['groups']:
            if str(g['fy']) not in p['fy_coverage']:
                fail('%s FY%d: votes with no coverage line' % (x['slug'], g['fy']))
    print('boards: %d files, %d votes; %d quotes checked verbatim; %d video-only chips recomputed'
          % (len(files), n_votes, n_quotes, n_cav))


def main():
    town_meeting()
    boards()
    print('links checked: %s' % dict(checked_links))
    if FAIL:
        print('FAILED -- %d:' % len(FAIL))
        for f in FAIL[:40]:
            print('  ' + f)
        if len(FAIL) > 40:
            print('  ... and %d more' % (len(FAIL) - 40))
        sys.exit(1)
    print('ok')


if __name__ == '__main__':
    main()
