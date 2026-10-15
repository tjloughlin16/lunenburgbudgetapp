#!/usr/bin/env python3
"""WHAT IS ON THE NEXT AGENDAS, MATCHED TO THE THREADS IT BELONGS TO.

    python3 scripts/build_agenda_threads.py            # write fy28/public/data/agenda-threads.json
    python3 scripts/build_agenda_threads.py --check    # fail if it no longer reproduces
    python3 scripts/build_agenda_threads.py --report   # every item, matched or not, for review

TJ, 15 October 2026: *"for upcoming minutes and agendas, i want to try to take whats in the
agenda, match them to threads, show the threads, and make sure the threads have all the
relevant information, like what has been said so people can use the thread as a way to
catch up on the topic before the meeting."*

Reads  fy28/public/data/meeting-feed.json   `as_of`, the date of the last live crawl
       sources/meetings/index.csv           every agenda the town posted, with its address
       sources/meetings/text/               the agenda's own text, as extracted
       sources/data/meeting-notices-email.csv  agendas that arrived some other way
       sources/data/meeting-register.csv    what the agenda calls the body (body_as_printed)
       sources/data/threads.csv             the registry: each thread's own patterns
Writes fy28/public/data/agenda-threads.json

NO MODEL. The match is the thread's OWN `match`, `qualify` and `exclude` patterns -- the
same ones build_threads.py runs over the minutes -- applied to each agenda line. So an
agenda item reaches a thread by exactly the rule a minute does, and a thread whose patterns
are wrong is wrong in both places at once, which is where it will be noticed. Nothing here
is metered.

TWO WAYS AN ITEM REACHES A THREAD, and the payload says which (`by`):

  words   the item's own line carries the thread's words (and its qualifier, if it has one)
  board   the meeting is of a board the thread names as its own (`boards`), or the BOARD'S
          NAME carries the thread's words and the item carries the qualifier. The Trust Fund
          Commission's "By Law Warrant Article, Special Town Meeting" never says "trust fund",
          because the board is the trust funds -- THREADS-MODEL §17a, a board talking about
          its own subject does not repeat the subject's name.

NEVER A FORCED MATCH. An item no thread claims is listed as unmatched, and the count of
them is printed on every run. Procedural lines -- call to order, the pledge, minutes,
public comment, adjourn -- are recognised and set aside, so "unmatched" means a piece of
business no thread follows, not a pledge of allegiance.

AN AGENDA IS NOT A DECISION (rule 7). It lists what MAY be discussed; the town's own agendas
say so. A match here says "this thread's words are on this agenda", never "this will be
decided", and the page says the same.

NO WALL CLOCK. The window is `as_of` from the meeting feed -- the last live crawl -- minus
RECENT_DAYS to plus HORIZON_DAYS, so --check reproduces on any day the feed does.
"""
import argparse
import csv
import datetime as dt
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEED = os.path.join(ROOT, 'fy28', 'public', 'data', 'meeting-feed.json')
INDEX = os.path.join(ROOT, 'sources', 'meetings', 'index.csv')
TEXT = os.path.join(ROOT, 'sources', 'meetings', 'text')
EMAIL = os.path.join(ROOT, 'sources', 'data', 'meeting-notices-email.csv')
REGISTER = os.path.join(ROOT, 'sources', 'data', 'meeting-register.csv')
THREADS = os.path.join(ROOT, 'sources', 'data', 'threads.csv')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'agenda-threads.json')
SITE_DOCS = '/docs/meetings/'

RECENT_DAYS = 14     # an agenda just past is still how a resident finds the meeting
HORIZON_DAYS = 28    # the meeting feed's own horizon (UPCOMING_HORIZON_DAYS)

# A LINE THAT OPENS AN ITEM. Bullets as the town's word processors print them (•, o, ◼,
# the private-use glyph some PDFs extract a bullet as), numbers, letters, roman numerals,
# and a clock time ("7:00 PM CALL TO ORDER").
MARKER = re.compile(
    r'^\s*(?:'
    r'[•\-\*▪◦◼■●\uf0a7\uf0b7\u2022\u25aa\u25cf]\s*'
    r'|o\s+(?=[A-Z0-9])'
    r'|\(?\d{1,2}\s?[\.\)]\s+'
    r'|\(?[a-zA-Z][\.\)]\s+'
    r'|\(?(?:[IVX]{1,5}|[ivx]{1,5})[\.\)]\s+'
    r'|\d{1,2}\s?:\s?\d{2}\s*(?:[AaPp]\.?\s?[Mm]\.?)?\s+'
    r')')
# The depth of a marker, for carrying a parent's line to its children as context.
def depth(line):
    s = line.lstrip()
    if re.match(r'(?:[IVX]{1,5})[\.\)]\s', s):
        return 0
    if re.match(r'\(?\d{1,2}\s?[\.\)]\s', s) or re.match(r'\d{1,2}\s?:\s?\d{2}', s):
        return 1
    if re.match(r'[•▪◼■●\uf0b7\u2022]', s):
        return 1
    if re.match(r'\(?[A-Z][\.\)]\s', s):
        return 2
    if re.match(r'\(?[a-z][\.\)]\s', s) or re.match(r'o\s', s) or re.match(r'[\-\*◦\uf0a7]', s):
        return 3
    return 4

# BOILERPLATE: the Open Meeting Law notice, the Zoom paragraph, the recording notice. A line
# carrying any of these is never business, and never continues an item.
BOILER = re.compile(
    r'zoom|webinar|open meeting law|meeting id|passcode|participant|raise hand|press #|\*9|'
    r'toll.?free|telephone|dial |broadcast|facebook|youtube|ai companion|ai technology|'
    r'reasonably anticipated|votes may be taken|not all (?:the )?items|in-person|in -person|'
    r'https?://|www\.|@|members of the public|courtesy to the public|recorded|'
    r'virtual|terminated|interrupt|phone:|fax:|facsimile|tel:|\bper policy\b|'
    r'minutes known at time|town clerk received', re.I)

# PROCEDURE: on every agenda, about no matter. Set aside, never counted as unmatched.
PROCEDURAL = re.compile(
    r'^(?:call(?:ed)? to order|meeting called to order|pledge|roll call|open\b|public comment|'
    r'committee/public comment|announcements?|adjourn|motion to adjourn|adjournment|minutes|'
    r'approval of (?:the )?(?:regular |meeting )?minutes|meeting minutes|'
    r'upcoming (?:scheduled )?(?:meetings?|events)|upcoming meeting|next meeting|'
    r'future agenda|old business|new business|other business|unfinished business|'
    r'correspondence|other correspondence|introductions?|roles and responsibilities|'
    r'warrants?|committee reports?|liaison reports?|chair.?s? report|citizen.?s? (?:comment|input)|'
    r'if conducted remotely|discussion items|current business|beneficiary/comment|'
    r'appointments, ratifications|minutes\*?/warrants|public$|board$|commission$|'
    r'town manager$|town manager report|executive director report|financials|administration|'
    r'(?:amended|revised)\b|'
    r'(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d)',
    re.I)


def clean(s):
    s = s.replace('\u00a0', ' ').replace('**', '').replace('\t', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def strip_marker(s):
    return clean(MARKER.sub('', s, count=1))


def is_procedural(s):
    t = re.sub(r'^\d{1,2}\s?:\s?\d{2}\s*(?:[AaPp]\.?\s?[Mm]\.?)?\s*', '', s)   # "7:00 PM CALL TO ORDER"
    t = re.sub(r'\((?:\d+\s*min|vote may be taken|follow up|ongoing)\)', '', t, flags=re.I)
    t = re.sub(r'[\*\u2013\u2014\-:\s]+$', '', t).strip()
    t = re.sub(r'^(?:[IVX]{1,5}\.\s*)', '', t)
    return bool(PROCEDURAL.match(t) or MORE_PROCEDURE.search(t) or LETTERHEAD.search(t)) or len(t) < 4


# The same idea, phrased the many ways the town's boards phrase it: "Board & Public Comment",
# "CLOSING PUBLIC COMMENT", "Review & Approve Minutes (3 min)", "Superintendent's Report".
MORE_PROCEDURE = re.compile(
    r'^(?:[\w’\']+\s*(?:&|and|/)\s*)?(?:closing\s+)?(?:board\s+|public\s+)?comments?$|'
    r'^(?:review|approv|ratif|regular session)\w*\b.{0,40}\bminutes\b|\bminutes\b.{0,30}\bapprov|'
    r'^(?:superintendent|student representative|director|chair)\w*.?s?\s+report$|'
    r'^reports? (?:of|from) (?:sub-?committees?|other boards)|^topics for future|'
    r'^(?:agenda items|discussion points|other|other items not anticipated|matters that may legally)|'
    r'^meeting schedule|^upcoming scheduled', re.I)
# The page furniture an extract sometimes splits out as a line: an address, a telephone
# number, the agenda's own heading. Never business.
LETTERHEAD = re.compile(
    r'^\d{2,5}\s+[A-Z][\w\.]*(?:\s+[A-Z][\w\.]*)*\s+(?:avenue|ave|street|st|road|rd)\.?$|'
    r'^lunenburg,?\s+ma\b|^\(\d{3}\)|^agenda\b|^p\.?m\.?\s*[-–]|^[ap]\.m\.', re.I)


def columns(text):
    """THE PAGE IN READING ORDER. Some agendas are set in two columns and the extract keeps
    them side by side on one line -- `3. Public Comment ...      j. Discussion of Track &
    Field (Turf)` -- so the right-hand column is read after the left, as a person would.
    And some put every item on ONE line between inline bullets; those are split apart."""
    left, right = [], []
    for raw in text.splitlines():
        if raw.startswith('===PAGE'):
            continue
        line = raw.rstrip()
        if len(re.findall(r'\s[•·]\s', line)) >= 2:
            for part in re.split(r'\s+[•·]\s+', line):
                left.append('• ' + part.strip())
            continue
        segs = [(m.start(), m.group(0)) for m in re.finditer(r'\S(?:.*?\S)?(?=\s{5,}|$)', line)]
        if not segs:
            left.append('')
            continue
        for off, seg in segs:
            (right if off >= 50 and len(segs) > 1 or off >= 70 else left).append(seg)
    return '\n'.join(left + [''] + right)


def split_items(text):
    """Every business line on an agenda, with its parent's line as context.

    Returns [{'n', 'line', 'parent', 'procedural'}]. A line that opens with a marker starts
    an item; a short unmarked line straight after one continues it (PDF extraction wraps a
    long item over two lines). An unmarked line that is not a continuation is a heading or
    prose and is NOT an item -- the agenda's own structure decides, never a guess at prose.

    AN AGENDA WITH NO MARKED ITEM AT ALL is a notice -- a public hearing, typically -- and
    its non-boilerplate sentences are the one item it carries."""
    lines = columns(text).splitlines()
    items, stack, prev_item = [], [], False
    for raw in lines:
        s = clean(raw)
        if not s:
            prev_item = False
            continue
        # "NEW BUSINESS:  - 452 Northfield Rd demo request" -- a heading and its items on
        # one line, dash-separated (the Historical Commission sets its agenda this way).
        hm = re.match(r'^([A-Z][A-Z ]{2,30}):\s*(.*)$', s)
        if hm and not BOILER.search(s):
            parts = [clean(x) for x in re.split(r'(?:^|\s)-\s+', hm.group(2)) if clean(x)]
            parts = [x for x in parts if not re.fullmatch(r'update\W*', x, re.I)]
            if parts and re.search(r'\s-\s', ' ' + hm.group(2)):
                for x in parts:
                    items.append({'line': x, 'parent': hm.group(1).title()})
            else:
                items.append({'line': clean(hm.group(1) + (': ' + hm.group(2) if hm.group(2) else '')), 'parent': ''})
            stack, prev_item = [], False
            continue
        if MARKER.match(raw) and not BOILER.search(s):
            line = strip_marker(raw)
            if not line or re.fullmatch(r'[\W\d]+', line):
                prev_item = False
                continue
            d = depth(raw)
            while stack and stack[-1][0] >= d:
                stack.pop()
            parent = stack[-1][1]['line'] if stack else ''
            it = {'line': line, 'parent': parent}
            items.append(it)
            stack.append((d, it))
            prev_item = True
            continue
        if (prev_item and items and not BOILER.search(s) and len(s) <= 160
                and not (s.isupper() and len(s.split()) <= 6)):
            # a wrapped item: lowercase start, or the item it continues has no full stop yet
            last = items[-1]
            if s[:1].islower() or not re.search(r'[\.\?]$', last['line']) or s[:1] in '("“':
                last['line'] = clean(last['line'] + ' ' + s)
                continue
        prev_item = False
    if not items:
        body = ' '.join(clean(l) for l in lines if clean(l) and not BOILER.search(l))
        sents = [x.strip() for x in re.split(r'(?<=[\.\:])\s+(?=[A-Z])', body)
                 if re.search(r'hearing|will hold|consider|discuss|vote', x, re.I) and len(x) > 40]
        if sents:
            items = [{'line': clean(' '.join(sents))[:600], 'parent': ''}]
    for i, it in enumerate(items, 1):
        it['n'] = i
        it['procedural'] = is_procedural(it['line'])
    return items


def compile_threads():
    out = []
    for t in csv.DictReader(open(THREADS, encoding='utf-8')):
        c = lambda k: re.compile(t[k], re.I) if (t.get(k) or '').strip() else None
        out.append({'id': t['id'], 'label': t['label'], 'status': t['status'],
                    'match': c('match'), 'qualify': c('qualify'), 'exclude': c('exclude'),
                    'boards': {b.strip() for b in (t.get('boards') or '').split(';') if b.strip()}})
    return out


def match_item(it, meeting, threads):
    """[(thread id, by)] for one item. The patterns are the registry's own (see the header)."""
    own = it['line']
    ctx = (it['parent'] + ' ' + own).strip()
    names = ' '.join(x for x in (meeting['board'], meeting['body_as_printed']) if x)
    hits = []
    for t in threads:
        rx, qu, ex = t['match'], t['qualify'], t['exclude']
        if ex and ex.search(ctx):
            continue
        if rx and rx.search(own) and (not qu or qu.search(ctx)):
            hits.append((t['id'], 'words'))
        elif rx and rx.search(it['parent']) and qu and qu.search(own):
            hits.append((t['id'], 'words'))
        elif meeting['board_slug'] in t['boards']:
            hits.append((t['id'], 'board'))
        elif rx and qu and rx.search(names) and qu.search(ctx):
            hits.append((t['id'], 'board'))
    return hits


def agenda_rows(as_of):
    lo = (dt.date.fromisoformat(as_of) - dt.timedelta(days=RECENT_DAYS)).isoformat()
    hi = (dt.date.fromisoformat(as_of) + dt.timedelta(days=HORIZON_DAYS)).isoformat()
    rows = [r for r in csv.DictReader(open(INDEX, encoding='utf-8'))
            if r['kind'] == 'agenda' and lo <= r['date'] <= hi]
    seen = {(r['board_slug'] if 'board_slug' in r else '', r['date']) for r in rows}
    if os.path.exists(EMAIL):
        for e in csv.DictReader(open(EMAIL, encoding='utf-8')):
            if e['kind'] == 'agenda' and lo <= e['date'] <= hi:
                rows.append({'board': e['board'], 'board_slug': e['board_slug'], 'date': e['date'],
                             'file_id': e['file_id'], 'path': e['path'], 'via': 'email',
                             'url': SITE_DOCS + e['path']})
    return rows


def body_printed():
    out = {}
    if os.path.exists(REGISTER):
        for r in csv.DictReader(open(REGISTER, encoding='utf-8', errors='replace')):
            if r.get('body_as_printed'):
                out[(r['board_slug'], r['date'])] = r['body_as_printed']
    return out


def slug_of(path):
    return path.split('/')[0]


def build():
    feed = json.load(open(FEED, encoding='utf-8'))
    as_of = feed['as_of']
    threads = compile_threads()
    label = {t['id']: t['label'] for t in threads}
    printed = body_printed()
    meetings, missing = [], []
    crawled = set()
    for r in sorted(agenda_rows(as_of), key=lambda r: (r['date'], r['board'], r['file_id'])):
        slug = r.get('board_slug') or slug_of(r['path'])
        if r.get('via') == 'email' and (slug, r['date']) in crawled:
            continue            # a crawled agenda for the same board and date wins
        crawled.add((slug, r['date']))
        txt = os.path.join(TEXT, os.path.splitext(r['path'])[0] + '.txt')
        if not os.path.exists(txt):
            missing.append({'board': r['board'], 'date': r['date'], 'file_id': r['file_id'],
                            'why': 'no extracted text'})
            continue
        m = {'board': r['board'], 'board_slug': slug, 'date': r['date'], 'file_id': r['file_id'],
             'body_as_printed': printed.get((slug, r['date']), ''),
             'upcoming': r['date'] >= as_of,
             'agenda_url': r['url'], 'agenda_doc': SITE_DOCS + r['path'],
             **({'via': 'email'} if r.get('via') == 'email' else {})}
        items = split_items(open(txt, encoding='utf-8', errors='replace').read())
        if not items:
            missing.append({'board': r['board'], 'date': r['date'], 'file_id': r['file_id'],
                            'why': 'no item could be read off the agenda text'})
        for it in items:
            it['threads'] = [] if it['procedural'] else [
                {'id': tid, 'label': label[tid], 'by': by} for tid, by in match_item(it, m, threads)]
        m['items'] = items
        m['threads'] = sorted({x['id'] for it in items for x in it['threads']})
        meetings.append(m)

    by_thread = {}
    for m in meetings:
        for it in m['items']:
            for x in it['threads']:
                by_thread.setdefault(x['id'], []).append({
                    'board': m['board'], 'board_slug': m['board_slug'], 'date': m['date'],
                    'body_as_printed': m['body_as_printed'], 'upcoming': m['upcoming'],
                    'line': it['line'], 'parent': it['parent'], 'by': x['by'],
                    'agenda_url': m['agenda_url'], 'agenda_doc': m['agenda_doc']})
    business = [it for m in meetings for it in m['items'] if not it['procedural']]
    up = [m for m in meetings if m['upcoming']]
    up_business = [it for m in up for it in m['items'] if not it['procedural']]
    counts = {
        'agendas': len(meetings), 'agendas_upcoming': len(up),
        'agendas_unreadable': len(missing),
        'items': sum(len(m['items']) for m in meetings),
        'business_items': len(business),
        'matched_items': sum(1 for it in business if it['threads']),
        'upcoming_business_items': len(up_business),
        'upcoming_matched_items': sum(1 for it in up_business if it['threads']),
        'threads_on_an_upcoming_agenda': len({x['id'] for it in up_business for x in it['threads']}),
    }
    return {
        'about': 'Agenda items matched to threads by each thread\u2019s own patterns. An agenda '
                 'lists what MAY be discussed; a match says a thread\u2019s words are on the agenda, '
                 'never what will be decided.',
        'generated_by': 'scripts/build_agenda_threads.py',
        'method': 'deterministic: threads.csv `match` + `qualify` - `exclude` on each agenda line '
                  '(by: words), or the meeting is of a board the thread names (by: board). No model.',
        'as_of': as_of,
        'window': {'from': (dt.date.fromisoformat(as_of) - dt.timedelta(days=RECENT_DAYS)).isoformat(),
                   'to': (dt.date.fromisoformat(as_of) + dt.timedelta(days=HORIZON_DAYS)).isoformat()},
        'counts': counts,
        'unreadable': missing,
        'meetings': meetings,
        'by_thread': by_thread,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--report', action='store_true')
    a = ap.parse_args()
    d = build()
    body = json.dumps(d, indent=1, ensure_ascii=False) + '\n'
    if a.report:
        for m in d['meetings']:
            print('\n%s %s%s %s' % (m['date'], m['board'], (' -- ' + m['body_as_printed']) if m['body_as_printed'] else '',
                                     'UPCOMING' if m['upcoming'] else ''))
            for it in m['items']:
                tag = 'proc' if it['procedural'] else (','.join('%s(%s)' % (x['id'], x['by']) for x in it['threads']) or '-- unmatched')
                print('   %-3d %-70s  %s' % (it['n'], it['line'][:70], tag))
        return
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else None
        if have != body:
            raise SystemExit('STALE %s — run build_agenda_threads.py' % os.path.relpath(OUT, ROOT))
        print('ok — %(agendas)d agendas, %(matched_items)d of %(business_items)d business items matched' % d['counts'])
        return
    if not d['meetings']:
        raise SystemExit('not one agenda in the window could be read. Refusing to write an empty '
                         'file -- it would look exactly like a town with nothing on its agendas.')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(body)
    c = d['counts']
    print('wrote %s — as of %s: %d agendas (%d upcoming, %d unreadable); %d of %d business items '
          'matched a thread; upcoming: %d of %d, touching %d threads'
          % (os.path.relpath(OUT, ROOT), d['as_of'], c['agendas'], c['agendas_upcoming'],
             c['agendas_unreadable'], c['matched_items'], c['business_items'],
             c['upcoming_matched_items'], c['upcoming_business_items'],
             c['threads_on_an_upcoming_agenda']))


if __name__ == '__main__':
    main()
