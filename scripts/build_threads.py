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
import datetime as dt
import functools
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREADS = os.path.join(ROOT, 'sources', 'data', 'threads.csv')
REPORTS = os.path.join(ROOT, 'fy28', 'public', 'data', 'reports.json')
TOPICS = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics.json')


def report_links(t, catalogue):
    """THE REPORTS FOR FURTHER READING, from the registry's curated `reports` column.

    TJ, 11 October 2026: *"threads need to automatically pull in any related full reports,
    as links for more detailed reading."* Curated, not matched: each thread's own `match`
    pattern run against report titles found a report for four threads of twenty-one, and
    one of those was a budget line that happened to mention veterans. Empty is allowed --
    six threads have no report and saying so is better than linking a near miss. An id
    that does not resolve REFUSES, because a join that matches nothing looks like a thread
    with no reading."""
    out = []
    for rid in [x.strip() for x in (t.get('reports') or '').split(';') if x.strip()]:
        rid = catalogue['superseded'].get(rid, rid)
        # A HUB OR TOPIC PAGE, by its address (`/athletics`, `/parks/artificial-turf-fund`),
        # resolved against topics.json -- the long reports those pages absorbed are UNLISTED
        # and are not in reports.json, so a thread reads on from the page that answers now.
        r = catalogue['by_path'].get(rid) if rid.startswith('/') else catalogue['by_id'].get(rid)
        if not r:
            raise SystemExit('threads.csv: %s lists report %r, which is not in reports.json '
                             '(unlisted, renamed, or a typo)' % (t['id'], rid))
        out.append({'title': r['title'], 'url': r['url']})
    return out
DECLINED = os.path.join(ROOT, 'sources', 'data', 'threads-declined.csv')
# GENERATED THREADS, never hand-edited: one JSON per generator, each {'threads': [row, ...]} in
# the registry's own columns plus the generator's fields. build_town_meetings.py writes one
# thread per Town Meeting -- its status board in `warrant`, its life in `chronology` -- and one
# per article promoted by its rule, with `parent`. threads.csv stays the hand registry.
AUTO = os.path.join(ROOT, 'sources', 'data', 'threads-auto')
# Fields a generated thread may carry that a registry thread never does. Written only when set,
# so a thread from threads.csv builds exactly as it did before.
AUTO_FIELDS = ('generated', 'parent', 'children', 'warrant', 'promoted_why')


def auto_rows():
    out = []
    for f in sorted(glob.glob(os.path.join(AUTO, '*.json'))):
        out.extend(json.load(open(f, encoding='utf-8'))['threads'])
    return out
MINUTES = os.path.join(ROOT, 'sources', 'data', 'recording-minutes')
# MOMENTS A PERSON PICKED OUT OF A RECORDING, for a thread, where our minutes dropped them.
# TJ, 17 October 2026, on the School Committee calling the track walls a danger: *"can you put
# those safety notes into the turf field thread?"* -- our minutes of 7 October kept the cost
# and the next step and lost every remark about safety. Each row's quote must appear
# VERBATIM in the machine captions within a minute and a half of its `t`, or the build stops:
# the quote is the evidence, and a misremembered one is worse than none.
MOMENTS = os.path.join(ROOT, 'sources', 'data', 'thread-moments.csv')
TRANSCRIPTS = os.path.join(ROOT, 'sources', 'data', 'youtube-transcripts')
CALLOUTS = os.path.join(ROOT, 'sources', 'data', 'thread-callouts.csv')
CALLOUTS_AUTO = os.path.join(ROOT, 'sources', 'data', 'thread-callouts-auto')


def moments(tid):
    """{(board_slug, date): [item, ...]} for one thread, every quote checked against the captions."""
    out = {}
    if not os.path.exists(MOMENTS):
        return out
    for r in read_csv(MOMENTS):
        if r['thread'] != tid:
            continue
        f = os.path.join(TRANSCRIPTS, r['board_slug'], '%s-%s.json' % (r['date'], r['video_id']))
        if not os.path.exists(f):
            raise SystemExit('thread-moments.csv: no captions at %s' % os.path.relpath(f, ROOT))
        t = int(r['t'])
        segs = json.load(open(f, encoding='utf-8'))['segments']
        # A GAP IN THE CAPTIONS is a moment too: `kind` unreadable, `quote` empty, `t` and
        # `t_end` the stretch. TJ, 18 October 2026, on the School Committee's 7 October
        # meeting: the superintendent called the fields unsafe *"but unfortunately in the
        # audio, that's all garbled"*. Nobody can quote her from this record, so the thread
        # says where the record goes silent -- checked: the captions there must hold almost
        # nothing, or the build stops.
        if r['kind'] == 'unreadable':
            end = int(r['t_end'])
            n = sum(len(x['text'].split()) for x in segs if t <= x['start'] < end)
            if n > (end - t) // 2:     # under one word in two seconds; speech runs ~2.5 a second
                raise SystemExit('thread-moments.csv: %s %s %d-%d holds %d caption words; not a gap'
                                 % (r['board_slug'], r['date'], t, end, n))
            out.setdefault((r['board_slug'], r['date']), []).append(
                {'kind': 'unreadable', 'text': r['text'], 'outcome': '', 't': t, 'quote': '',
                 'video_url': 'https://www.youtube.com/watch?v=' + r['video_id'], 'source': 'caption'})
            continue
        heard = ' '.join(x['text'] for x in segs if t - 30 <= x['start'] <= t + 90)
        if ' '.join(r['quote'].split()) not in ' '.join(heard.split()):
            raise SystemExit('thread-moments.csv: %s %s t=%d -- %r is not in the captions there'
                             % (r['board_slug'], r['date'], t, r['quote']))
        out.setdefault((r['board_slug'], r['date']), []).append(
            {'kind': r['kind'], 'text': r['text'], 'outcome': '', 't': t, 'quote': r['quote'],
             'video_url': 'https://www.youtube.com/watch?v=' + r['video_id'], 'source': 'caption'})
    return out
TMVOTES = os.path.join(ROOT, 'sources', 'data', 'town-meeting-votes.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'threads.json')
# THE TOWN'S OWN MINUTES, read structured by extract_official_votes.py -- every item carries
# its quote from the minutes, checked verbatim. Until 15 October 2026 a thread read only OUR
# minutes of the recordings, so a meeting whose only record is the town's minutes (most
# boards, most years) could never reach a thread, and nothing on a thread page could be
# quoted from a document.
TOWN = os.path.join(ROOT, 'sources', 'data', 'official-votes')
# WHAT IS ON THE NEXT AGENDAS, matched by build_agenda_threads.py with each thread's own
# patterns. TJ, 15 October 2026: a thread is how a resident catches up before the meeting,
# so it has to say which meeting is next.
AGENDAS = os.path.join(ROOT, 'fy28', 'public', 'data', 'agenda-threads.json')
# THE REPORTS A THREAD NEEDS, from the meetings themselves (build_suggested_reports.py). TJ,
# 15 October 2026: "reports should assist threads." A thread follows a matter; a report lays
# out its numbers. A suggestion lands here when the model named this thread or the thread's
# own patterns found its words -- never by board alone.
SUGGESTED = os.path.join(ROOT, 'sources', 'data', 'suggested-reports.csv')
SUGGESTED_MEETINGS = os.path.join(ROOT, 'sources', 'data', 'suggested-reports-meetings.csv')


# THE CALLOUTS: what someone says NEXT. TJ, 19 October 2026: *"if someone walked up to me and
# said 'did you hear about TC Passios?!' what will they say next? 'Theres an article to vote
# for its demolition, that'll cost 1-4 million!'"* -- and the kinds: *"money, warrant articles
# at town meeting, increase in fees and amount, change to town or school services, or
# something 'impactful'"*. A count of meetings never passes that test; a stake or an event does.
#
# PICKED BY A PERSON, CHECKED BY THE BUILD. Which figure is the stake is judgement -- the
# latest figure on the town offices thread is a basement slab, the stake is the $21M plan --
# so scripts/propose_callouts.py ranks candidates and a person writes the row. The build then
# refuses any row whose evidence does not hold:
#   * every quote must be IN its source, whitespace ignored (an extract prints "T otal").
#     PRINTED: the document's text. HEARD: the machine captions near `t`, or -- where the
#     captions are not held -- our notes of that recording, and the page says which.
#   * a PRINTED value's every number must be in its quote, at the precision shown: "$21.4M"
#     against "$21,409,100". A HEARD quote is words ("one and four million"), so the value is
#     our rendering of it and the card says "as heard".
#   * `hook` is the few words that ride beside the value on the front page, and it may not
#     hold a digit: a figure in it would be a figure typed into prose (CLAUDE.md rule 2).
CALLOUT_KINDS = ('money', 'warrant', 'fee', 'service', 'impact')
_NUM = re.compile(r'(\d[\d,]*(?:\.\d+)?)\s*(M\b|K\b|million\b|thousand\b)?', re.I)


_WORDNUM = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8,
            'nine': 9, 'ten': 10, 'twenty': 20, 'thirty': 30, 'fifty': 50, 'hundred': 100, 'a': 1, 'half': .5}
_SCALE = {'million': 1e6, 'm': 1e6, 'thousand': 1e3, 'k': 1e3, 'billion': 1e9}


def _amounts(text):
    """Every amount a passage names, scaled: "$21,409,100" -> 21409100; "between one and four
    million" -> 1e6 and 4e6, because a unit three words on scales the numbers before it."""
    toks = re.findall(r'\d[\d,]*(?:\.\d+)?|[a-z]+', (text or '').lower().replace('$', ' '))
    out = []
    for i, tk in enumerate(toks):
        if tk[0].isdigit():
            v = float(tk.replace(',', ''))
        elif tk in _WORDNUM and tk != 'a' or (tk == 'a' and i + 1 < len(toks) and toks[i + 1] in _SCALE):
            v = _WORDNUM[tk]
        else:
            continue
        scale = next((_SCALE[x] for x in toks[i + 1:i + 4] if x in _SCALE), 1)
        out += [v, v * scale]
    return out


def _value_holds(value, evidence):
    """Is every number in a callout's value in its evidence, at the precision shown?
    "$21.4M" against 21,409,100; "Nov 17" against "November 17, 2026"."""
    have = _amounts(evidence)
    for num, unit in _NUM.findall(value):
        v = float(num.replace(',', ''))
        scale = {'m': 1e6, 'million': 1e6, 'k': 1e3, 'thousand': 1e3}.get(unit.lower(), 1)
        places = len(num.split('.')[1]) if '.' in num else 0
        if not any(round(q / scale, places) == v for q in have):
            return num + unit
    return None


def _squash(s):
    return ''.join((s or '').replace('\u2019', "'").replace('\u2018', "'").split()).lower()


def _callout_source(r, n, problems):
    """One source of one callout -> {basis, href, where, checked_against}, or None with a problem."""
    sfx = '' if n == 1 else str(n)
    basis, quote = r['basis' + sfx], r['quote' + sfx]
    if not basis:
        return None
    tag = '%s callout %s' % (r['thread'], r['order'])
    if basis == 'printed':
        txt = os.path.join(ROOT, 'sources', r['text' + sfx])
        if not os.path.exists(txt):
            problems.append('%s: no text at sources/%s' % (tag, r['text' + sfx]))
            return None
        if _squash(quote) not in _squash(open(txt, encoding='utf-8', errors='replace').read()):
            problems.append('%s: quote not in sources/%s' % (tag, r['text' + sfx]))
            return None
        if n == 1:
            # THE LABEL'S NUMBERS TOO. Monty Tech's first machine pick said "about $117,438 more"
            # beside a value of 8.8% -- a figure typed into the sentence, unchecked.
            miss = _value_holds(r['value'] + ' ' + r['label'], quote)
            if miss:
                problems.append('%s: %s in the value is not in its quote' % (tag, miss))
                return None
        return {'basis': 'printed', 'href': '/docs/' + r['doc' + sfx], 'where': r['where' + sfx],
                'checked_against': 'the document'}
    if basis == 'heard':
        b, d, vid, t = r['board' + sfx], r['date' + sfx], r['video_id' + sfx], int(r['t' + sfx])
        cap = os.path.join(TRANSCRIPTS, b, '%s-%s.json' % (d, vid))
        if os.path.exists(cap):
            segs = json.load(open(cap, encoding='utf-8'))['segments']
            heard, against = ' '.join(x['text'] for x in segs if t - 120 <= x['start'] <= t + 120), 'the captions'
        else:
            notes = os.path.join(MINUTES, b, '%s-%s.json' % (d, vid))
            if not os.path.exists(notes):
                problems.append('%s: neither captions nor our notes for %s %s' % (tag, b, d))
                return None
            heard, against = json.dumps(json.load(open(notes, encoding='utf-8'))['minutes'], ensure_ascii=False), 'our notes of the recording'
        if _squash(quote) not in _squash(heard):
            problems.append('%s: quote not in %s of %s %s' % (tag, against, b, d))
            return None
        # A HEARD VALUE IS OUR RENDERING OF WORDS, so its numbers must be in those words or in
        # what our notes heard at that moment -- "$1M-$4M" from "one and four million". A
        # number found in neither was computed, and a computed figure is not a callout.
        if n == 1:
            miss = _value_holds(r['value'] + ' ' + r['label'], quote + ' ' + ' '.join(r.get('heard') or []))
            if miss:
                problems.append('%s: %s in the value is neither in its quote nor heard' % (tag, miss))
                return None
        return {'basis': 'heard', 'href': 'https://www.youtube.com/watch?v=%s&t=%ds' % (vid, t),
                'where': r['where' + sfx], 'checked_against': against}
    problems.append('%s: basis is printed or heard, not %r' % (tag, basis))
    return None


def callouts(known, problems):
    """{thread id: [callout, ...]} in order, every row's evidence checked."""
    out = {}
    if not os.path.exists(CALLOUTS):
        return out
    for r in read_csv(CALLOUTS):
        tag = '%s callout %s' % (r['thread'], r['order'])
        if r['thread'] not in known:
            problems.append('%s: no such thread' % tag)
            continue
        if r['kind'] not in CALLOUT_KINDS:
            problems.append('%s: kind %r is not one of %s' % (tag, r['kind'], ', '.join(CALLOUT_KINDS)))
        if re.search(r'\d', r['hook']):
            problems.append('%s: the hook holds a digit; a figure goes in `value`' % tag)
        if len(r['value']) > 24 or len(r['label']) > 110 or len(r['hook']) > 40:
            problems.append('%s: value <= 24, label <= 110, hook <= 40 characters' % tag)
        srcs = [x for x in (_callout_source(r, 1, problems), _callout_source(r, 2, problems)) if x]
        if not srcs:
            continue
        out.setdefault(r['thread'], []).append({'order': int(r['order']), 'kind': r['kind'], 'value': r['value'],
                                                'label': r['label'], 'hook': r['hook'], 'sources': srcs})
    # THE MACHINE'S PICKS (scripts/write_thread_callouts.py), for every thread a person has
    # not picked. Checked by the same code as a person's row; a failure is DROPPED and named
    # here rather than stopping the build -- the refresh must not fail on a model's mistake,
    # and a dropped callout is a thread showing less, never a thread showing something wrong.
    if os.path.isdir(CALLOUTS_AUTO):
        for f in sorted(os.listdir(CALLOUTS_AUTO)):
            if not f.endswith('.json'):
                continue
            j = json.load(open(os.path.join(CALLOUTS_AUTO, f), encoding='utf-8'))
            tid = j['thread']
            if tid in out or tid not in known:
                continue
            for k, c in enumerate(j['callouts'], 1):
                # THE SECOND READER'S VERDICT (write_thread_callouts.judge). Unjudged is not kept.
                v = c.get('verdict') or {}
                if not v.get('keep'):
                    print('  DROPPED (machine pick): %s callout %d: %s' % (tid, k, v.get('why') or 'not judged'))
                    continue
                r = dict({x: '' for x in ('doc', 'text', 'board', 'date', 'video_id', 't', 'basis2')},
                         **{x: v for x, v in c.items() if x not in ('item_date', 'item_board', 'verdict')},
                         thread=tid, order=str(k))
                r['t'] = str(r['t'])
                mine = []
                if re.search(r'\d', r['hook']) or len(r['value']) > 24 or len(r['label']) > 110 or len(r['hook']) > 40 \
                        or r['kind'] not in CALLOUT_KINDS:
                    mine.append('%s callout %d: breaks a length, hook or kind rule' % (tid, k))
                src = None if mine else _callout_source(r, 1, mine)
                if not src or mine:
                    print('  DROPPED (machine pick): ' + '; '.join(mine))
                    continue
                out.setdefault(tid, []).append({'order': k, 'kind': r['kind'], 'value': r['value'],
                                                'label': r['label'], 'hook': r['hook'], 'sources': [src],
                                                'auto': True})
    for tid, cs in out.items():
        cs.sort(key=lambda c: c['order'])
        if len(cs) > 3:
            problems.append('%s: %d callouts; three at most, or none of them is the hook' % (tid, len(cs)))
    return out


def reports_needed(tid):
    """[{title, slug, status, url, question, meetings: [{date, board, question_then, watch_at,
    at, our_minutes}]}] for the suggestions this thread is linked to, newest raising first."""
    if not os.path.exists(SUGGESTED):
        return []
    occ = read_csv(SUGGESTED_MEETINGS) if os.path.exists(SUGGESTED_MEETINGS) else []
    out = []
    for r in read_csv(SUGGESTED):
        ids = [x.split(' (')[0] for x in (r.get('threads') or '').split(';') if x.strip()]
        if tid not in ids:
            continue
        ms = sorted((o for o in occ if o['id'] == r['id']), key=lambda o: o['date'], reverse=True)
        out.append({'title': r['title'], 'slug': r['slug'], 'status': r['status'],
                    'url': r['exists_at'] or '', 'question': r['question'],
                    'how': [x.split(' (')[1].rstrip(')') for x in r['threads'].split(';')
                            if x.split(' (')[0] == tid][0],
                    'meetings': [{k: o[k] for k in ('date', 'board', 'fiscal_year', 'question_then',
                                                     'watch_at', 'at', 'our_minutes')} for o in ms]})
    out.sort(key=lambda x: (x['status'] != 'new', -len(x['meetings']),
                            [-ord(c) for c in (x['meetings'][0]['date'] if x['meetings'] else '')]))
    return out


def read_csv(p):
    return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []


def norm_motion(s):
    return re.sub(r'\W+', ' ', (s or '').lower()).strip()


def src(o):
    """Where an item came from, when the meeting was posted twice: the recording that heard it,
    and a note if the other recording lacks that moment. Empty for an ordinary meeting."""
    return {'video_url': o.get('video_url') or '', 'recording_note': o.get('recording_note') or ''}


def the_record():
    """Every meeting we can read, one row per (board, date), votes deduped across parts."""
    by, future = {}, []
    today = dt.date.today().isoformat()
    # A MEETING POSTED TWICE IS READ ONCE, FROM THE MERGED ACCOUNT. Both recordings are
    # valid; merge_recording_minutes.py lines their minutes up and keeps the union, each item
    # citing the recording it came from and saying when the other recording lacks that moment.
    # Reading both files instead would put every remark on a thread twice.
    import merge_recording_minutes as MRG
    merged, skip = {}, set()
    for (b, d), gs in MRG.groups().items():
        for g in gs:
            mg = MRG.merged(b, d, g)
            if mg:
                lead = mg['videos'][0]
                merged[lead], role = mg, MRG.roles(mg['videos'])
                mg['_role'] = role
                skip.update(v for v in mg['videos'] if v != lead)
    for f in sorted(glob.glob(os.path.join(MINUTES, '*', '*.json'))):
        vid = os.path.basename(f)[:-5].split('-', 3)[-1]
        if vid in skip:
            continue
        j = json.load(open(f, encoding='utf-8'))
        if vid in merged:
            mg = merged[vid]
            j = dict(j, minutes=dict(j.get('minutes') or {}, **{k: [
                dict(it, video_url='https://www.youtube.com/watch?v=' + it['video_id'],
                     recording_note=MRG.label(it, mg['_role']) if it.get('absent_from') else '')
                for it in mg[k]] for k in MRG.LISTS}))
        # A MEETING CANNOT HAVE HAPPENED TOMORROW. Three minutes files carry dates a model
        # read wrong (2027-11-06, 2027-01-16, and a 2021 Parks meeting). Left in, the worst
        # of them made a thread report `last moved 2027-01-16` and sort to the top of the
        # page -- a date defect arriving as a ranking, which is the hardest kind to notice.
        if (j.get('meeting_date') or '') > today:
            future.append((j['board_slug'], j.get('meeting_date'), os.path.relpath(f, ROOT)))
            continue
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
                                 'video_url': v.get('video_url') or j.get('video_url') or '',
                                 'recording_note': v.get('recording_note') or ''})
        for x in (m.get('decisions') or []):
            rec['items'].append({'kind': 'decision', 'text': x.get('decision') or '', 't': x.get('t'), **src(x)})
        for t in (m.get('topics') or []):
            rec['items'].append({'kind': 'topic', 'text': t.get('topic') or '', 't': t.get('t_start'),
                                 't_end': t.get('t_end'), **src(t)})
        # THE BUDGET DISCUSSION AND THE PUBLIC'S COMMENTS, READ TOO. Until 10 October 2026 a
        # thread saw only votes, decisions and topic headings, so the Finance Committee's
        # 24 September discussion of the track and turf engineering request -- recorded under
        # budget items -- never reached the turf thread, and nothing a resident said at the
        # microphone could reach any thread at all. TJ: *"The turf field one has now been
        # discussed at 3 different meetings with inflammatory phrasing, and I dont think we
        # detected that. we need to figure out why"*.
        for b in (m.get('budget_items') or []):
            txt = (b.get('topic') or '') + ('. ' + b['what_was_said'] if b.get('what_was_said') else '')
            rec['items'].append({'kind': 'budget', 'text': txt, 't': b.get('t'), **src(b)})
        # CONTENTION, where our minutes were read for it (10 October 2026 onward; an older
        # file has no key and contributes nothing -- not "calm", just not read).
        for c in (m.get('contention') or []):
            rec['items'].append({'kind': 'contention',
                                 'text': '%s (%s): "%s"' % (c.get('about') or '', c.get('sides') or '',
                                                            c.get('words_as_heard') or ''),
                                 't': c.get('t'), **src(c)})
        # CONCERNS AND CONDITIONS (17 October 2026 onward; same three states as contention).
        for c in (m.get('concerns_and_conditions') or []):
            rec['items'].append({'kind': {'condition': 'condition', 'liability or legal': 'liability'}.get(c.get('kind'), 'safety'),
                                 'text': '%s (%s): "%s"' % (c.get('about') or '', c.get('who') or '',
                                                            c.get('words_as_heard') or ''),
                                 't': c.get('t'), **src(c)})
        for c in (m.get('public_comment') or []):
            if not re.match(r'\s*no public comment', c.get('topic') or '', re.I):
                rec['items'].append({'kind': 'comment', 'text': c.get('topic') or '', 't': c.get('t'), **src(c)})
    for r in by.values():
        r.pop('seen', None)
    return by, future


def town_record():
    """The town's minutes, one row per (board, date), every item with its verbatim quote.

    Kept apart from `the_record()` on purpose: a closure resolves only against a vote whose
    second in a recording can be cited, and the two records of one meeting are shown side by
    side, each labelled, rather than merged into one list that would count a vote twice."""
    by, today = {}, dt.date.today().isoformat()
    for f in sorted(glob.glob(os.path.join(TOWN, '*', '*.json'))):
        try:
            j = json.load(open(f, encoding='utf-8'))
        except (OSError, ValueError):
            continue
        date = j.get('meeting_date') or ''
        if not date or date > today or not j.get('board_slug'):
            continue
        src = j.get('source') or {}
        cite = {'source': 'town', 'doc_url': src.get('doc_url') or '', 'town_url': src.get('minutes_url') or ''}
        rec = by.setdefault((j['board_slug'], date), {'items': [], 'seen': set()})
        def add(kind, text, quote, outcome=''):
            k = (kind, norm_motion(text))
            if not text or k in rec['seen']:
                return
            rec['seen'].add(k)
            rec['items'].append(dict(cite, kind=kind, text=text, outcome=outcome, quote=quote or '',
                                     t=None, video_url=''))
        for v in j.get('votes') or []:
            if not v.get('procedural'):
                add('vote', v.get('motion') or '', v.get('quote'), v.get('outcome') or '')
        for x in j.get('decisions') or []:
            add('decision', x.get('decision') or '', x.get('quote'))
        for b in j.get('budget_items') or []:
            add('budget', (b.get('topic') or '') + ('. ' + b['what_was_recorded'] if b.get('what_was_recorded') else ''),
                b.get('quote'))
        for x in j.get('topics') or []:
            add('topic', (x.get('topic') or '') + ('. ' + x['resolution'] if x.get('resolution') else ''), x.get('quote'))
        # A SPEAKER'S NAME IS NOT CARRIED. The town's minutes print it and the quote may too;
        # the thread needs what was raised, not who stood up.
        for c in j.get('public_comment') or []:
            if not re.match(r'\s*no public comment', c.get('topic') or '', re.I):
                add('comment', c.get('topic') or '', c.get('quote'))
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


def looseness(t, record):
    """HOW MUCH THIS THREAD'S PATTERN WOULD CLAIM OUTSIDE ITS OWN WINDOW.

    `started` and `match` compensate for each other, and the compensation is invisible
    until it is counted. `sap-rewrite` matches a salary-schedule article at the 2022 Town
    Meeting; `middle-school-sports` matches a citizen petition about the SEWER SERVICE AREA
    MAP; `solid-waste-enterprise` matches solid waste removal at Woodruff. None is the
    matter, and all three are hidden by a date rather than excluded by a pattern -- two
    mechanisms each covering the other's weakness, which is the shape every compensating
    error in this repository has had.

    A pattern general enough to be useful ("surplus", "salary schedule") cannot be made
    precise, so this does not fail. It COUNTS, so a thread leaning hard on its start date
    is legible as one, and so a `started` moved earlier cannot quietly drag in years of a
    different matter."""
    rx = re.compile(t['match'], re.I) if t.get('match') else None
    qu = re.compile(t['qualify'], re.I) if t.get('qualify') else None
    ex = re.compile(t['exclude'], re.I) if t.get('exclude') else None
    n = 0
    for (slug, date), rec in record.items():
        if not t.get('started') or date >= t['started']:
            continue
        for x in [v['motion'] for v in rec['votes']] + [i['text'] for i in rec['items']]:
            if rx and rx.search(x) and (not qu or qu.search(x)) and not (ex and ex.search(x)):
                n += 1
    return n


def chronology(t, record, town=None):
    """Every meeting the thread came up at, oldest first, from BOTH records of it.

    `source` on every item says which: `ours` is our minutes of the recording, written by a
    model from machine captions, cited to the second; `town` is the town's own minutes,
    cited to the document with the sentence quoted from it. A meeting can carry both, and
    they are kept apart rather than merged -- two records of one vote are not two votes."""
    rx = re.compile(t['match'], re.I) if t.get('match') else None
    # ENTITY **AND** QUALIFIER (§2). "Turkey Hill" is a PLACE hosting two matters and a lot
    # of traffic -- paraprofessionals, DIBELS scores, solar offsets, intercoms. Both Turkey
    # Hill threads first shipped matching the bare entity, and the ADA thread's items were
    # 46 of 46 shared with the rebuild thread: one thread rendered twice. `qualify` is the
    # second pattern that must ALSO match, and it is what separates a matter from a place.
    qu = re.compile(t['qualify'], re.I) if t.get('qualify') else None
    ex = re.compile(t['exclude'], re.I) if t.get('exclude') else None
    board = (t.get('boards') or '').strip()
    town = town or {}

    def hit(text):
        return bool(rx and rx.search(text) and (not qu or qu.search(text)) and not (ex and ex.search(text)))

    out = []
    names = dict(board_names(), **{k[0]: v['board'] for k, v in record.items()})
    for key in sorted(set(record) | set(town), key=lambda k: (k[1], k[0])):
        slug, date = key
        if t.get('started') and date < t['started']:
            continue
        # `until`: a generated article thread ends at its Town Meeting (build_town_meetings.py).
        # The hand registry has no such column, so its threads are unchanged.
        if t.get('until') and date > t['until']:
            continue
        rec = record.get(key)
        hits = []
        if rec:
            for v in rec['votes']:
                if not v['procedural'] and hit(v['motion']):
                    hits.append({'kind': 'vote', 'text': v['motion'], 'outcome': v['outcome'],
                                 't': v['t'], 'video_url': v['video_url'], 'source': 'ours', 'recording_note': v.get('recording_note') or ''})
            # A REMARK MADE IN PASSING DOES NOT REPEAT ITS SUBJECT. "That wall is going to collapse
            # on someone" was said inside the School Committee's track and turf discussion and
            # names neither. So a concern, condition or dispute also belongs to the thread when it
            # falls inside a matching topic's span, or names the thread's subject within ten
            # minutes of a full match in the same meeting (the Select Board's "kids are actively
            # getting injured because of the condition of the field", 6 Oct, inside a three-hour
            # warrant topic that a span cannot narrow).
            full = [it for it in rec['items'] if it.get('t') is not None and hit(it['text'])] + \
                   [v for v in rec['votes'] if v.get('t') is not None and not v['procedural'] and hit(v['motion'])]
            spans = [(it['t'], it['t_end']) for it in full if it.get('kind') == 'topic' and it.get('t_end')]

            def near(it):
                if it['kind'] not in ('safety', 'liability', 'condition', 'contention') or it.get('t') is None:
                    return False
                # `exclude` HOLDS HERE TOO. A remark inside a matching topic's span skipped it,
                # so the pantry's modular hearing at the ZBA reached TC Passios through one
                # line that mentioned where the pantry is now (TJ, 19 October 2026).
                if ex and ex.search(it['text']):
                    return False
                if any(a <= it['t'] <= b for a, b in spans):
                    return True
                return bool(rx and rx.search(it['text']) and not (ex and ex.search(it['text']))
                            and any(abs(f['t'] - it['t']) <= 600 for f in full))
            for it in rec['items']:
                if hit(it['text']) or near(it):
                    hits.append({'kind': it['kind'], 'text': it['text'], 'outcome': '', 't': it['t'],
                                 'video_url': it.get('video_url') or (rec['recordings'][0] if rec['recordings'] else ''),
                                 'source': 'ours', 'recording_note': it.get('recording_note') or ''})
        for it in (town.get(key) or {}).get('items', []):
            # The town's quote is matched too: a minute summarised as "Capital requests" whose
            # sentence names the turf field is about the turf field.
            if hit(it['text'] + ' ' + it['quote']):
                hits.append(dict(it))
        # §17a: a board talking about its own subject does not repeat the subject's name.
        if not hits and board and slug == board:
            for v in (rec['votes'] if rec else []):
                if not v['procedural'] and re.search(r'warrant|article|bylaw|fee|rate', v['motion'], re.I):
                    hits.append({'kind': 'vote', 'text': v['motion'], 'outcome': v['outcome'],
                                 't': v['t'], 'video_url': v['video_url'], 'source': 'ours', 'recording_note': v.get('recording_note') or ''})
            for it in (town.get(key) or {}).get('items', []):
                if it['kind'] == 'vote' and re.search(r'warrant|article|bylaw|fee|rate', it['text'], re.I):
                    hits.append(dict(it))
        if hits:
            out.append({'board': (rec or {}).get('board') or names.get(slug) or slug.replace('-', ' ').title(),
                        'board_slug': slug, 'date': date, 'items': hits,
                        'records': sorted({h['source'] for h in hits})})
    # The picked moments, into the meeting they belong to -- or as a meeting of their own.
    picked = moments(t['id'])
    for c in out:
        c['items'].extend(picked.pop((c['board_slug'], c['date']), []))
    for (slug, date), items in picked.items():
        out.append({'board': names.get(slug) or slug.replace('-', ' ').title(),
                    'board_slug': slug, 'date': date, 'items': items, 'records': []})
    for c in out:
        c['records'] = sorted({h['source'] for h in c['items']})
    out.sort(key=lambda c: (c['date'], c['board_slug']))
    return out


@functools.lru_cache(maxsize=None)
def board_names():
    """slug -> the board's name as the town's AgendaCenter files it. Read once: chronology()
    calls it per thread, and the index is twelve thousand rows. Callers copy it (dict(...))."""
    out = {}
    for r in read_csv(os.path.join(ROOT, 'sources', 'meetings', 'index.csv')):
        out.setdefault((r.get('path') or '').split('/')[0], r.get('board') or '')
    return out


def votes_in(stop):
    """VOTES AT ONE MEETING, NEVER TWICE. Where both records carry the meeting, the larger
    count of the two stands for it -- the same vote heard in the recording and printed in the
    minutes is one vote (THREADS-MODEL §14d-i)."""
    ours = sum(1 for i in stop['items'] if i['kind'] == 'vote' and i.get('source') != 'town')
    town = sum(1 for i in stop['items'] if i['kind'] == 'vote' and i.get('source') == 'town')
    return max(ours, town)


SCHEDULED = re.compile(r'\b(warrant article|public hearing|statement of interest|\bRFP\b|'
                       r'request for proposal|ballot|town meeting|deadline|due back|'
                       r'placeholder|feasibility study)\b', re.I)
PLANS = re.compile(r'\b(study|design|schematic|estimate|proposal|draft|plan|report|'
                   r'recommendation|options|scope)\w*\b', re.I)


HOT_MEETINGS, HOT_BOARDS, HOT_WINDOW, HOT_LATEST = 3, 2, 30, 14


def temperature(t, chron, today, record):
    """HOW ALIVE A MATTER IS — derived, never typed.

    TJ, 19 September 2026: "I want to see if something is HOT, COLD, just getting started,
    [a can of worms] ... Did it recently come up and it looks to have impact? Have MANY
    boards discussed it with no resolution? Are there plans behind it yet? Just an idea or
    is there movement and votes yet?"

    Two different questions, so two answers rather than one blended score:

      HEAT  -- how recently and how fast it is moving. A count of meetings and the gaps
               between them; nothing about importance.
      STAGE -- how far along it is. Whether anyone has voted, whether anything is
               scheduled, whether a document exists yet.

    THE LABEL IS A READING OF THE COUNTS AND THE COUNTS TRAVEL WITH IT. `basis` carries
    the arithmetic to the page, so a reader is never asked to take "picking up" on trust --
    rule 7: the meetings and the dates are the facts, and the word is our summary of them.

    `tangled` is TJ's "many boards discussed it with no resolution" -- deliberately not
    called anything more lurid, because the state is ordinary: a matter that has spread
    across the town's boards and been settled by none of them."""
    dates = sorted({c['date'] for c in chron})
    n, boards = len(dates), len({c['board_slug'] for c in chron})
    votes = sum(votes_in(c) for c in chron)
    text = ' '.join(i['text'] for c in chron for i in c['items'])
    days = (dt.date.fromisoformat(today) - dt.date.fromisoformat(dates[-1])).days if dates else 9999
    span = (dt.date.fromisoformat(dates[-1]) - dt.date.fromisoformat(dates[0])).days if n > 1 else 0

    # meetings in the last 90 days against the rate over the whole life
    recent = sum(1 for d in dates if (dt.date.fromisoformat(today) - dt.date.fromisoformat(d)).days <= 90)
    rate = (n / max(span, 1)) * 90 if span else 0

    # HOW MANY TIMES ITS OWN BOARDS HAVE MET SINCE, WITHOUT RAISING IT.
    #
    # A day count is the wrong instrument. "Six months" means one thing for a board that
    # sits twice a month and another for one that sits quarterly, and the Monty Tech
    # assessment is set every January -- six quiet months there is the calendar, not
    # neglect. What a resident actually wants to know is whether the matter is being
    # passed over: the Finance Committee has met eleven times and not returned to it.
    #
    # It is a LOWER BOUND, because it counts only meetings we can read. The page prints
    # the denominator for the same reason search_minutes.py does.
    mine = {c['board_slug'] for c in chron}
    last = dates[-1] if dates else '9999-99-99'
    passed_over = sum(1 for (slug, d) in record if slug in mine and d > last)

    # ORDER MATTERS, AND THE FIRST VERSION GOT IT WRONG. `n == 1` was tested before the
    # recency tests, so the extended day fee -- ONE meeting, FIVE MONTHS ago -- was
    # labelled "just started" beside a standing line reading "last moved 5 months ago".
    # TJ: "this feels conflicting". It was.
    #
    # The fix is not a reorder but a distinction: ONE MEETING RECENTLY is a matter getting
    # under way; ONE MEETING LONG AGO is a matter that was raised and then dropped. Those
    # are different things and a reader wants to tell them apart -- the second is arguably
    # the more interesting, because somebody put it on a future agenda and it never came
    # back.
    if t['status'] == 'resolved':
        heat = 'settled'
    elif n == 1:
        heat = 'just started' if days <= 90 else 'raised once'
    # STALE, NOT "GONE QUIET". TJ: "discussed 6 months ago seems 'stale' to me. A BIG open
    # question with no movement (its not moving) is stale." The two words say different
    # things: gone quiet reports that discussion stopped, which is neutral; STALE reports
    # that an open question is not being answered, which is the fact a resident wants.
    #
    # BOTH SIGNALS ARE REQUIRED, because either alone lies. A day count alone ignores how
    # often the board actually sits; a count of meetings passed over alone called the DPW
    # contract "gone quiet" at FIFTY-FOUR DAYS, because the Select Board happens to meet
    # weekly. Stale means real time has passed AND the boards have sat repeatedly without
    # returning to it.
    elif days > 365:
        heat = 'gone quiet'
    elif passed_over >= 4 and days >= 120:
        heat = 'stale'
    elif passed_over >= 2 or days >= 60:
        heat = 'slowing'
    elif recent >= 2 and recent > rate:
        heat = 'picking up'
    else:
        heat = 'moving'

    tangled = (t['status'] != 'resolved' and boards >= 3 and span >= 180 and n >= 6)

    # HOT -- TJ, 10 October 2026: *"a HOT indicator for threads with a fire emoji when it shows
    # up in many meetings in a short and RECENT period of time"*, *"esp across different
    # committees/boards"*. All four, because each alone lies: a busy board raising one item
    # at three of its own meetings is not the town catching fire, and a burst last spring is
    # not hot now. OPEN; at least HOT_MEETINGS meetings in the last HOT_WINDOW days; those
    # spanning at least HOT_BOARDS boards; the latest within HOT_LATEST days. The counts go
    # to the page with the badge, so the emoji is a reading of the numbers, never instead
    # of them.
    win = [c for c in chron
           if (dt.date.fromisoformat(today) - dt.date.fromisoformat(c['date'])).days <= HOT_WINDOW]
    hot_meetings = len({(c['date'], c['board_slug']) for c in win})
    hot_boards = len({c['board_slug'] for c in win})
    hot = (t['status'] == 'open' and hot_meetings >= HOT_MEETINGS and hot_boards >= HOT_BOARDS
           and days <= HOT_LATEST)

    if t['status'] == 'resolved':
        stage = 'decided'
    elif votes:
        stage = 'voted on, not decided'
    elif SCHEDULED.search(text):
        stage = 'a date is set'
    elif PLANS.search(text):
        stage = 'plans being drawn'
    else:
        stage = 'talked about only'

    return {
        'heat': heat, 'stage': stage, 'tangled': tangled, 'hot': hot,
        'basis': {
            'meetings_last_30': hot_meetings, 'boards_last_30': hot_boards,
            'meetings': n, 'boards': boards, 'votes': votes,
            'days_since_last': days, 'span_days': span, 'meetings_last_90': recent,
            'board_meetings_since': passed_over,
        },
    }


def where_it_stands(chron):
    """WHAT WAS LAST DECIDED, VOTED, OR LEFT OPEN — not when it was last mentioned.

    TJ, on /threads/turf-field-study: "'Where it stands' on the thread pages need to be
    what was last decided, voted, left open. 'Open — last discussed at the School
    Committee, Sep 16, 3 days ago' is not good enough."

    He is right, and the reason is worth keeping: a date answers *is this current*, which
    is a question about the PAGE. A resident's question is about the MATTER — what happened
    at that meeting, and what is now true. Those are different questions and the date was
    answering the easier one.

    So this returns the most recent thing that actually moved: a VOTE if one was taken,
    else a DECISION the board recorded, else the topic it was last discussed under. Each
    carries its board, its date and the second in the recording, so the claim is checkable
    rather than summarised."""
    def pick(kinds):
        for stop in reversed(chron):
            best = [i for i in stop['items'] if i['kind'] in kinds]
            if best:
                return dict(best[-1], board=stop['board'], board_slug=stop['board_slug'], date=stop['date'])
        return None
    return {'vote': pick(('vote',)), 'decision': pick(('decision',)), 'any': pick(('vote', 'decision', 'topic'))}


def build():
    (record, future), official = the_record(), official_votes()
    town = town_record()
    every = dict.fromkeys(set(record) | set(town))      # every meeting either record can read
    agendas = json.load(open(AGENDAS, encoding='utf-8')) if os.path.exists(AGENDAS) else {}
    threads, problems = [], []
    rj = json.load(open(REPORTS, encoding='utf-8'))
    tj = json.load(open(TOPICS, encoding='utf-8'))
    catalogue = {'superseded': rj.get('superseded', {}),
                 'by_id': {r['id']: r for r in rj['reports'] + rj['pages']},
                 'by_path': {x['path']: {'title': x['title'], 'url': x['path']}
                             for x in tj['categories'] + list(tj['topics'].values())
                             if x.get('ready')}}
    rows = read_csv(THREADS)
    calls = callouts({t['id'] for t in rows}, problems)
    auto = auto_rows()
    hand_ids = {t['id'] for t in rows}
    for t in auto:
        if t['id'] in hand_ids:
            problems.append('%s is both in threads.csv and generated' % t['id'])
    kids = collections.defaultdict(list)
    for t in auto:
        if t.get('parent'):
            kids[t['parent']].append(t['id'])
    # A HAND THREAD THAT CLOSES AT A TOWN MEETING belongs under that meeting too: its closure
    # names the meeting's date. Computed from the registry's own closure columns, never typed.
    tm_ids = {t['warrant']['date']: t['id'] for t in auto if t.get('warrant')}
    for t in rows:
        if t.get('closed_board') == 'town-meeting' and t.get('closed_date') in tm_ids:
            kids[tm_ids[t['closed_date']]].append(t['id'])
    for t in rows + auto:
        gen = t in auto
        # A GENERATED MEETING THREAD BRINGS ITS OWN CHRONOLOGY AND CLOSURE: its life is the
        # warrant's, assembled by build_town_meetings.py; a generated ARTICLE thread is
        # followed by the same matcher as every registry thread.
        chron = t['chronology'] if gen and 'chronology' in t else chronology(t, record, town)
        temp = temperature(t, chron, dt.date.today().isoformat(), every)
        stands = where_it_stands(chron)
        closure = t['closure'] if gen and 'closure' in t else resolve_closure(t, record, official)
        if t['status'] == 'resolved' and not closure:
            problems.append('%s says resolved and its closure does not resolve to a vote' % t['id'])
        if not (t.get('closes') or '').strip():
            problems.append('%s has no closure criterion' % t['id'])
        mts = [c['date'] for c in chron]
        # THE ORDER OF THE TOP BAND, AND IT IS NOT THE §2 BAR. The bar scores a CANDIDATE
        # from the words of one item; a registered thread has a history, and the history is
        # better evidence than the sentence that started it. Cross-board spread was the
        # strongest single predictor in the manual pass -- every confirmed thread reached a
        # second board early and every false positive stayed put -- so it leads, then how
        # recently the thread moved, then how much of the record it touches.
        # It is named `weight` and not `importance`: the page says what it ordered on.
        threads.append(dict(
            # `note` IS NOT PUBLISHED. It is the registry's own margin -- "ENTITY vs
            # MATTER", "CAN OF WORMS trigger, at n=1", "POLYSEMY" -- written for whoever
            # maintains the patterns, and every word of it is ours. It was rendering to
            # residents under "What this does not show", which is rule 7b's second named
            # failure: precision and jargon are not the same thing, and the second is
            # usually an unfinished sentence. `caveat` is the reader's half, in English.
            {k: t[k] for k in ('id', 'label', 'question', 'kind', 'groups', 'tags', 'boards',
                               'registered_on', 'started', 'closes', 'status', 'resolved_on', 'caveat')},
            closure=closure,
            callouts=calls.get(t['id'], []),
            reports=report_links(t, catalogue) if not gen else [],
            reports_needed=reports_needed(t['id']),
            # WHERE IT IS ON AN AGENDA: every posted agenda in the window whose item carries
            # this thread's words, upcoming and just past. The page filters by the reader's
            # clock. An agenda says what MAY be discussed, never what will be decided.
            on_agenda=(agendas.get('by_thread') or {}).get(t['id'], []),
            chronology=chron,
            meetings=len(chron),
            boards_touched=len({c['board_slug'] for c in chron}),
            first_seen=mts[0] if mts else '',
            last_moved=mts[-1] if mts else '',
            claims_before_started=looseness(t, record),
            stands=stands,
            # NEW MEANS THE MATTER IS NEW, not that we only just noticed it. TJ:
            # "'new' threads means new in existence. not new to us ;) Some of the 'new'
            # things have LOTS of meetings."
            #
            # The first version keyed on `registered_on` -- the day we opened the thread --
            # which made every thread new on the day the registry was seeded, including
            # Turkey Hill with fourteen meetings behind it. That is our filing date and it
            # is not news about the town. A resident wants to know what has just been
            # RAISED, and the record says that: the first meeting that discussed it.
            #
            # 60 days, roughly four meetings of a board that sits fortnightly -- long
            # enough to survive somebody checking monthly, short enough that a matter with
            # a year of history can never qualify.
            # ...and a SETTLED matter is never new, however recently it arose. The
            # citizens' petition ran from July to Town Meeting in nine meetings and was
            # decided; putting it under "newly raised" would send a reader to something
            # already over.
            is_new=bool(t['status'] != 'resolved' and mts
                        and (dt.date.today() - dt.date.fromisoformat(mts[0])).days <= 60),
            # PINNED: a person's call that this matter leads the page, in this order. TJ, 10
            # October 2026: *"need to have a way to make them important and ordered"*. The
            # registry's `pin` column; blank is unpinned, and unpinned threads keep the
            # newest-first order below the pinned ones.
            pin=int((t.get('pin') or '').strip()) if (t.get('pin') or '').strip().isdigit() else None,
            heat=temp['heat'], stage=temp['stage'], tangled=temp['tangled'], hot=temp['hot'],
            momentum=temp['basis'],
            weight=(len({c['board_slug'] for c in chron}) * 100
                    + int((mts[-1] if mts else '0000-00-00').replace('-', '')[2:6] or 0) // 100
                    + min(len(chron), 40)),
        ))
        extra = dict((k, t[k]) for k in AUTO_FIELDS if gen and t.get(k))
        if kids.get(t['id']):
            extra['children'] = kids[t['id']]
        if t.get('closed_board') == 'town-meeting' and t.get('closed_date') in tm_ids and not gen:
            extra['parent'] = tm_ids[t['closed_date']]
        threads[-1].update(extra)
    # THE DENOMINATOR, ON EVERY RUN (THREADS-MODEL §7 and search_minutes.py). A thread that
    # went quiet because the RECORD went quiet is not a thread where nothing happened, and
    # the boards with the thinnest minutes are not the boards with the least happening.
    threads.sort(key=lambda t: (t['last_moved'] or '', t['weight']), reverse=True)
    threads.sort(key=lambda t: (t['pin'] is None, t['pin'] or 0))     # stable: pinned lead
    cov = {'rank_note': 'newest first — by the date each thread last came up',
           'dated_in_the_future_and_excluded': [{'board': b, 'date': d, 'file': f} for b, d, f in future],
           'rank_basis': 'when each last came up, newest first',
           'meetings_readable': len(every),
           'meetings_with_our_minutes': len(record),
           'meetings_with_town_minutes_read': len(town),
           'boards_readable': len({s for s, _ in every}),
           'agendas_as_of': agendas.get('as_of', ''),
           'agendas_matched': agendas.get('counts', {}),
           'town_meeting_readable': len([1 for s, _ in record if s == 'town-meeting']),
           'official_town_meeting_years': sorted({r['fy'] for r in read_csv(TMVOTES)})}
    return threads, cov, problems


def hottest(threads):
    """WHAT THE TOWN IS TALKING ABOUT RIGHT NOW -- the strip at the top of the front page.

    TJ, 19 October 2026: *"a sort of thin headline to dynamically call out the HOTTEST topic
    in town"*, *"it has to be automated ... populated and removed when there is no hot
    topic"*, and *"if there are multiple equally hot topics, we can list them"*.

    NO NEW RULE. The set is exactly the threads `temperature()` already calls hot, so the
    front page and the 🔥 badge on /threads can never disagree. Ordered by meetings in the
    window, then boards, then the most recent. EMPTY IS AN ANSWER: the page draws nothing.

    `as_of` travels with it because `hot` is relative to the day this ran. A refresh that
    stops would otherwise leave last month's fire on the front page; the page checks it."""
    # A generated Town Meeting thread is not put on the front page by this rule; whether it
    # should be is a decision for later (THREADS-MODEL §20).
    rows = [t for t in threads if t['hot'] and not t.get('generated')]
    rows.sort(key=lambda t: (-t['momentum']['meetings_last_30'], -t['momentum']['boards_last_30'],
                             t['momentum']['days_since_last']))
    return {'as_of': dt.date.today().isoformat(), 'window_days': HOT_WINDOW,
            'threads': [{'id': t['id'], 'label': t['label'],
                         # "TC Passios: the site's future" -> "TC Passios". A label without a
                         # colon is already short.
                         'short': t['label'].split(':')[0].strip(),
                         # The front page's hook: the first callout that carries one, value
                         # first -- "$1M–$4M to demolish". Checked where the callout is.
                         'hook': next(('%s %s' % (c['value'], c['hook']) for c in t['callouts'] if c['hook']), ''),
                         'meetings': t['momentum']['meetings_last_30'],
                         'boards': t['momentum']['boards_last_30'],
                         'days_since_last': t['momentum']['days_since_last']} for t in rows]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    threads, cov, problems = build()
    payload = {'about': 'Threads: a matter tracked across meetings and boards to a decision. '
                        'notes/process/THREADS-MODEL.md',
               'generated_by': 'scripts/build_threads.py',
               'coverage': cov,
               'hottest': hottest(threads),
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
    loose = sorted((t for t in threads if t['claims_before_started'] >= 5),
                   key=lambda t: -t['claims_before_started'])
    if loose:
        print('LEANING ON `started` — the pattern claims this much before the thread began:')
        for t in loose[:8]:
            print('  %4d  %s' % (t['claims_before_started'], t['id']))
    print('wrote %s — %d threads (%s); closures: %s'
          % (os.path.relpath(OUT, ROOT), len(threads), dict(st), dict(bas) or 'none'))
    print('readable record: %d meetings across %d boards; %d Town Meetings; official votes for FY%s'
          % (cov['meetings_readable'], cov['boards_readable'], cov['town_meeting_readable'],
             ', FY'.join(cov['official_town_meeting_years'])))


if __name__ == '__main__':
    main()
