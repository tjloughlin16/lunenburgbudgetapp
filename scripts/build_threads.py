#!/usr/bin/env python3
"""THREADS, RESOLVED AGAINST THE RECORD -- the payload the pages read.

    python3 scripts/build_threads.py
    python3 scripts/build_threads.py --check

Reads  sources/data/threads.csv            the registry; a person writes it
       sources/data/threads-declined.csv   what we looked at and said no to
       sources/data/recording-minutes/     our minutes of the recordings
       sources/data/town-meeting-votes.csv the Town Clerk's printed record
Writes fy28/public/data/threads.json

WHY A THREAD'S CLOSURE IS A REFERENCE AND NOT A SENTENCE. The registry was first seeded
with closures typed as prose -- "Article 33 ... PASSED 100-9". That is a figure typed into
a sentence, the one thing in this repository that can be silently wrong (rule 2), and it
was wrong within the hour: `solid-waste-enterprise` was filed as carried at the 2 May 2026
Annual Town Meeting, and that meeting's record contains no such vote. So the registry now
carries `closed_board`, `closed_date`, `closed_article` and `closed_match`, and the tally,
the motion and the outcome are RESOLVED FROM THE RECORD here. Nothing about a vote is
typed by a person.

TWO RECORDS OF ONE VOTE, AND THE MERGE IS AUTOMATIC. TJ, 19 September 2026: "the votes
follow the same pattern for town meeting. We accept the transcript version, then when we
get the official version we merge."

  official  -- the Town Clerk's printed proceedings in the annual town report. A record
               of what happened. Preferred always.
  ours      -- our minutes of the recording, written by a model from machine captions,
               which mishear numbers. A finding aid. Used only while the first does not
               exist.

The annual report runs about a year behind, so a thread closing today resolves to OURS and
upgrades to OFFICIAL when that year's report is extracted -- with no edit to the registry.
Every closure states which it used, in `basis`, and a page that renders a caption-derived
tally without saying so is misreporting it.

THE UNIT IS THE MEETING, NEVER THE RECORDING (THREADS-MODEL §14d-i). The 2 May 2026 ATM is
two videos, 6h56m and 4h55m, sharing 3 of 45 motions; a joint body's meeting counts for
three boards. Votes are keyed on (board, date, motion) and deduped.
"""
import argparse
import collections
import csv
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREADS = os.path.join(ROOT, 'sources', 'data', 'threads.csv')
DECLINED = os.path.join(ROOT, 'sources', 'data', 'threads-declined.csv')
MINUTES = os.path.join(ROOT, 'sources', 'data', 'recording-minutes')
TMVOTES = os.path.join(ROOT, 'sources', 'data', 'town-meeting-votes.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'threads.json')


def read_csv(p):
    return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []


def norm_motion(s):
    return re.sub(r'\W+', ' ', (s or '').lower()).strip()


def the_record():
    """Every meeting we can read, one row per (board, date), votes deduped across parts."""
    by = {}
    for f in sorted(glob.glob(os.path.join(MINUTES, '*', '*.json'))):
        j = json.load(open(f, encoding='utf-8'))
        key = (j['board_slug'], j.get('meeting_date') or '')
        m = j.get('minutes') or {}
        rec = by.setdefault(key, {'board_slug': key[0], 'board': j.get('board') or key[0],
                                  'date': key[1], 'votes': [], 'items': [], 'seen': set(),
                                  'recordings': []})
        rec['recordings'].append(j.get('video_url') or '')
        for v in (m.get('votes') or []):
            k = norm_motion(v.get('motion'))
            if not k or k in rec['seen']:
                continue
            rec['seen'].add(k)
            rec['votes'].append({'motion': v.get('motion') or '', 'outcome': v.get('outcome') or '',
                                 'procedural': bool(v.get('procedural')), 't': v.get('t'),
                                 'video_url': j.get('video_url') or ''})
        for x in (m.get('decisions') or []):
            rec['items'].append({'kind': 'decision', 'text': x.get('decision') or '', 't': x.get('t')})
        for t in (m.get('topics') or []):
            rec['items'].append({'kind': 'topic', 'text': t.get('topic') or '', 't': t.get('t_start')})
    for r in by.values():
        r.pop('seen', None)
    return by


def official_votes():
    out = collections.defaultdict(list)
    for r in read_csv(TMVOTES):
        out[(r['meeting_date'] or '', re.sub(r'\D', '', r['article']))].append(r)
    return out


def resolve_closure(t, record, official):
    """The closing act, from the record. OFFICIAL first, ours only while it does not exist."""
    date, art = t.get('closed_date') or '', re.sub(r'\D', '', t.get('closed_article') or '')
    if not date:
        return None
    for r in official.get((date, art), []):
        return {'basis': 'official', 'source': 'the Town Clerk, printed in the annual town report',
                'meeting': 'Town Meeting', 'date': date, 'article': r['article'],
                'result': r['result'], 'amount_as_printed': r['amount_as_printed'],
                'quote': r['quote'], 'fincom': r['fincom'], 'select_board': r['select_board'],
                'document': r['source_doc'], 'page': r['page'],
                'caveat': ''}
    rec = record.get((t.get('closed_board') or 'town-meeting', date))
    if not rec:
        return None
    rx = re.compile(t['closed_match'], re.I) if t.get('closed_match') else None
    arx = re.compile(r'\barticle\s+%s\b' % art, re.I) if art else None
    # PRECEDENCE, AND IT IS NOT COSMETIC. Several motions can name one article: at the
    # 3 Sep 2026 Special Town Meeting the School Committee moved to SUPPORT article 3
    # before Town Meeting moved the transfer itself, and matching on the number alone
    # picked the supporting motion and called it the closure. So: the number AND the
    # subject first, then the subject, then the number.
    def rank(v):
        a = bool(arx and arx.search(v['motion']))
        b = bool(rx and rx.search(v['motion']))
        return 0 if (a and b) else 1 if b else 2 if a else 9
    for v in sorted((v for v in rec['votes'] if not v['procedural']), key=rank):
        if rank(v) < 9:
            return {'basis': 'ours', 'source': 'our minutes of the recording, from machine captions',
                    'meeting': rec['board'], 'date': date, 'article': t.get('closed_article') or '',
                    'result': v['outcome'], 'amount_as_printed': '', 'quote': v['motion'],
                    'fincom': '', 'select_board': '',
                    'document': v['video_url'], 'page': '',
                    'caveat': 'AS HEARD from machine captions. A caption model hears "fifteen hundred", '
                              '"$1,500" and "$50" alike; check the recording at the second cited. '
                              'This upgrades to the Town Clerk\'s printed record when that year\'s '
                              'annual report is extracted.'}
    return None


def chronology(t, record):
    rx = re.compile(t['match'], re.I) if t.get('match') else None
    ex = re.compile(t['exclude'], re.I) if t.get('exclude') else None
    board = (t.get('boards') or '').strip()
    out = []
    for (slug, date), rec in sorted(record.items(), key=lambda kv: kv[0][1]):
        if t.get('started') and date < t['started']:
            continue
        hits = []
        for v in rec['votes']:
            if v['procedural']:
                continue
            if rx and rx.search(v['motion']) and not (ex and ex.search(v['motion'])):
                hits.append({'kind': 'vote', 'text': v['motion'], 'outcome': v['outcome'],
                             't': v['t'], 'video_url': v['video_url']})
        for it in rec['items']:
            if rx and rx.search(it['text']) and not (ex and ex.search(it['text'])):
                hits.append({'kind': it['kind'], 'text': it['text'], 'outcome': '', 't': it['t'],
                             'video_url': rec['recordings'][0] if rec['recordings'] else ''})
        # §17a: a board talking about its own subject does not repeat the subject's name.
        if not hits and board and slug == board:
            for v in rec['votes']:
                if not v['procedural'] and re.search(r'warrant|article|bylaw|fee|rate', v['motion'], re.I):
                    hits.append({'kind': 'vote', 'text': v['motion'], 'outcome': v['outcome'],
                                 't': v['t'], 'video_url': v['video_url']})
        if hits:
            out.append({'board': rec['board'], 'board_slug': slug, 'date': date, 'items': hits})
    return out


def build():
    record, official = the_record(), official_votes()
    threads, problems = [], []
    for t in read_csv(THREADS):
        chron = chronology(t, record)
        closure = resolve_closure(t, record, official)
        if t['status'] == 'resolved' and not closure:
            problems.append('%s says resolved and its closure does not resolve to a vote' % t['id'])
        if not (t.get('closes') or '').strip():
            problems.append('%s has no closure criterion' % t['id'])
        mts = [c['date'] for c in chron]
        threads.append(dict(
            {k: t[k] for k in ('id', 'label', 'question', 'kind', 'groups', 'tags', 'boards',
                               'started', 'closes', 'status', 'resolved_on', 'note')},
            closure=closure,
            chronology=chron,
            meetings=len(chron),
            boards_touched=len({c['board_slug'] for c in chron}),
            first_seen=mts[0] if mts else '',
            last_moved=mts[-1] if mts else '',
        ))
    # THE DENOMINATOR, ON EVERY RUN (THREADS-MODEL §7 and search_minutes.py). A thread that
    # went quiet because the RECORD went quiet is not a thread where nothing happened, and
    # the boards with the thinnest minutes are not the boards with the least happening.
    cov = {'meetings_readable': len(record),
           'boards_readable': len({s for s, _ in record}),
           'town_meeting_readable': len([1 for s, _ in record if s == 'town-meeting']),
           'official_town_meeting_years': sorted({r['fy'] for r in read_csv(TMVOTES)})}
    return threads, cov, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    threads, cov, problems = build()
    payload = {'about': 'Threads: a matter tracked across meetings and boards to a decision. '
                        'notes/process/THREADS-MODEL.md',
               'generated_by': 'scripts/build_threads.py',
               'coverage': cov,
               'threads': threads,
               'declined': read_csv(DECLINED)}
    body = json.dumps(payload, indent=1, ensure_ascii=False) + '\n'
    if a.check:
        if problems:
            for p in problems:
                print('  %s' % p)
            raise SystemExit('REFUSING: %d thread(s) do not hold together' % len(problems))
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else None
        if have != body:
            raise SystemExit('STALE %s — run build_threads.py' % os.path.relpath(OUT, ROOT))
        print('ok — %d threads resolve against the record' % len(threads))
        return
    if problems:
        for p in problems:
            print('  %s' % p)
        raise SystemExit('REFUSING to write: %d thread(s) do not hold together' % len(problems))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(body)
    st = collections.Counter(t['status'] for t in threads)
    bas = collections.Counter(t['closure']['basis'] for t in threads if t['closure'])
    print('wrote %s — %d threads (%s); closures: %s'
          % (os.path.relpath(OUT, ROOT), len(threads), dict(st), dict(bas) or 'none'))
    print('readable record: %d meetings across %d boards; %d Town Meetings; official votes for FY%s'
          % (cov['meetings_readable'], cov['boards_readable'], cov['town_meeting_readable'],
             ', FY'.join(cov['official_town_meeting_years'])))


if __name__ == '__main__':
    main()
