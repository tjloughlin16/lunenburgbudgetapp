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
    by, future = {}, []
    today = dt.date.today().isoformat()
    for f in sorted(glob.glob(os.path.join(MINUTES, '*', '*.json'))):
        j = json.load(open(f, encoding='utf-8'))
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
                                 'video_url': j.get('video_url') or ''})
        for x in (m.get('decisions') or []):
            rec['items'].append({'kind': 'decision', 'text': x.get('decision') or '', 't': x.get('t')})
        for t in (m.get('topics') or []):
            rec['items'].append({'kind': 'topic', 'text': t.get('topic') or '', 't': t.get('t_start')})
    for r in by.values():
        r.pop('seen', None)
    return by, future


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


def chronology(t, record):
    rx = re.compile(t['match'], re.I) if t.get('match') else None
    # ENTITY **AND** QUALIFIER (§2). "Turkey Hill" is a PLACE hosting two matters and a lot
    # of traffic -- paraprofessionals, DIBELS scores, solar offsets, intercoms. Both Turkey
    # Hill threads first shipped matching the bare entity, and the ADA thread's items were
    # 46 of 46 shared with the rebuild thread: one thread rendered twice. `qualify` is the
    # second pattern that must ALSO match, and it is what separates a matter from a place.
    qu = re.compile(t['qualify'], re.I) if t.get('qualify') else None
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
            if (rx and rx.search(v['motion']) and (not qu or qu.search(v['motion']))
                    and not (ex and ex.search(v['motion']))):
                hits.append({'kind': 'vote', 'text': v['motion'], 'outcome': v['outcome'],
                             't': v['t'], 'video_url': v['video_url']})
        for it in rec['items']:
            if (rx and rx.search(it['text']) and (not qu or qu.search(it['text']))
                    and not (ex and ex.search(it['text']))):
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


SCHEDULED = re.compile(r'\b(warrant article|public hearing|statement of interest|\bRFP\b|'
                       r'request for proposal|ballot|town meeting|deadline|due back|'
                       r'placeholder|feasibility study)\b', re.I)
PLANS = re.compile(r'\b(study|design|schematic|estimate|proposal|draft|plan|report|'
                   r'recommendation|options|scope)\w*\b', re.I)


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
    votes = sum(1 for c in chron for i in c['items'] if i['kind'] == 'vote')
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
        'heat': heat, 'stage': stage, 'tangled': tangled,
        'basis': {
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
    threads, problems = [], []
    for t in read_csv(THREADS):
        chron = chronology(t, record)
        temp = temperature(t, chron, dt.date.today().isoformat(), record)
        stands = where_it_stands(chron)
        closure = resolve_closure(t, record, official)
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
            chronology=chron,
            meetings=len(chron),
            boards_touched=len({c['board_slug'] for c in chron}),
            first_seen=mts[0] if mts else '',
            last_moved=mts[-1] if mts else '',
            claims_before_started=looseness(t, record),
            stands=stands,
            # NEW MEANS NEWLY OPENED BY US, NOT NEWLY STARTED BY THE TOWN. A matter can
            # have run for a year before anybody names it a thread; what is new to a
            # returning reader is the THREAD. Fourteen days, because that is about two
            # meeting cycles -- long enough that somebody checking fortnightly still sees
            # it, short enough that "new" keeps meaning something.
            is_new=bool(t.get('registered_on')
                        and (dt.date.today() - dt.date.fromisoformat(t['registered_on'])).days <= 14),
            heat=temp['heat'], stage=temp['stage'], tangled=temp['tangled'],
            momentum=temp['basis'],
            weight=(len({c['board_slug'] for c in chron}) * 100
                    + int((mts[-1] if mts else '0000-00-00').replace('-', '')[2:6] or 0) // 100
                    + min(len(chron), 40)),
        ))
    # THE DENOMINATOR, ON EVERY RUN (THREADS-MODEL §7 and search_minutes.py). A thread that
    # went quiet because the RECORD went quiet is not a thread where nothing happened, and
    # the boards with the thinnest minutes are not the boards with the least happening.
    threads.sort(key=lambda t: (t['last_moved'] or '', t['weight']), reverse=True)
    cov = {'rank_note': 'newest first — by the date each thread last came up',
           'dated_in_the_future_and_excluded': [{'board': b, 'date': d, 'file': f} for b, d, f in future],
           'rank_basis': 'when each last came up, newest first',
           'meetings_readable': len(record),
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
