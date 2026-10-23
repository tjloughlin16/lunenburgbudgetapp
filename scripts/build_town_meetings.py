#!/usr/bin/env python3
"""TOWN MEETINGS, FOUND IN THE RECORD -- and every warrant article, stage by stage.

    python3 scripts/build_town_meetings.py            # write the register, the articles, the threads
    python3 scripts/build_town_meetings.py --check    # ...and fail if any of them is stale

Writes  sources/data/town-meetings.csv               one row per Town Meeting
        sources/data/warrant-articles.csv            one row per meeting x article
        sources/data/threads-auto/town-meetings.json the generated threads build_threads.py merges

No model. Deterministic. Reads only what is already held.

WHY A MEETING IS FOUND AND NEVER TYPED. TJ, 20-21 October 2026: Lunenburg holds an Annual
Town Meeting in May, a Special in November, and sometimes another -- one was held on
3 September 2026 after a citizens' petition. Each needs its thread "as soon as there is a
signal", with nobody remembering to add a row. So a meeting enters the register from any
ONE of these, and each row says which it came from (`signals`):

  notice      a legal notice: "voted to call a Special Town Meeting for <date>"
  warrant     a warrant or booklet the town published, read for its date
  sb-vote     a Select Board vote to call the meeting, in either record of the board
  agenda      a Select Board agenda the AgendaCenter titles "Special Town Meeting"
  clerk       the Town Clerk's printed record in the annual report (town-meeting-votes.csv)
  ours        our minutes of the meeting's recording
  video       a recording on the town's channel filed as Town Meeting

The 3 September 2026 meeting reaches the register from the Select Board's vote of
27 July 2026 to call it -- its first signal -- and then from the notice, the warrant, the
agenda and the recording.

AN ARTICLE IS A NUMBER ON A WARRANT, AND EVERY STAGE CITES A RECORD. Proposed (a draft),
on the warrant (the posted warrant), recommended (the Finance Committee or Select Board,
as printed or voted), voted (Town Meeting), recorded (the Town Clerk). A stage with no
record is BLANK. Results come from the Clerk's printed record where it exists and from our
minutes of the recording otherwise, labelled ours -- and upgrade by themselves when the
Clerk's year is extracted (THREADS-MODEL §18).

WHICH ARTICLES GET A THREAD OF THEIR OWN. TJ, 21 October 2026: "the articles that have
been discussed a lot get [their own thread]. every other article will likely be discussed
twice (to get it on the warrant, the vote to recommend), so all details can be summed up
without a full thread, as long as there is a link to the details of the article". The rule
is mechanical, the thresholds are OURS (named below), and the page prints them.
"""
import argparse
import collections
import csv
import datetime as dt
import glob
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
DATA = os.path.join(ROOT, 'sources', 'data')
OUT_MEETINGS = os.path.join(DATA, 'town-meetings.csv')
OUT_ARTICLES = os.path.join(DATA, 'warrant-articles.csv')
OUT_THREADS = os.path.join(DATA, 'threads-auto', 'town-meetings.json')
TMVOTES = os.path.join(DATA, 'town-meeting-votes.csv')
DRAFTS = os.path.join(DATA, 'warrant-articles-fincom.csv')
VIDEOS = os.path.join(DATA, 'youtube-video-boards.csv')

# ---------------------------------------------------------------------------------------
# THE PROMOTION RULE -- OUR CHOICE, PRINTED ON THE PAGE (CLAUDE.md rule 3).
#
# An article gets a thread of its own when ANY of these holds:
#   1. it came up at PROMOTE_MEETINGS or more distinct meetings BEYOND the routine stops --
#      a vote to place it on the warrant, a vote to recommend it, and Town Meeting itself
#      do not count, because every article has those;
#   2. a member of the public spoke about it at a board meeting, or a dispute about it was
#      recorded (our minutes' `contention`), at any meeting before the vote;
#   3. Town Meeting amended it, divided on it (a counted vote), or put it off (passed over,
#      postponed, referred).
PROMOTE_MEETINGS = 3
# HOW FAR BACK an article's discussion is looked for: the warrant window, or this many days
# before the meeting, whichever starts first. Spring articles are argued through the whole
# budget season; 180 days reaches back to November for a May meeting.
LOOKBACK_DAYS = 180
# DIVIDED means the losing side was at least this share of the votes counted. A count alone is
# not division: the 2026 Annual voted by handset and every article has a count, most 250-20.
DIVIDED_SHARE = 0.15
# ...and the meetings must span this many boards. One board raising its own subject at its
# own meetings is that board's agenda, not a matter (THREADS-MODEL §2: "the second board
# beats the third mention"). The Cemetery Commission discusses selling lots every month.
PROMOTE_BOARDS = 2
# EVERY ARTICLE GETS ITS ROUTINE STOPS: the Select Board places it and recommends it, the
# Finance Committee reviews it and recommends it. Up to this many meetings of each of those
# two boards are routine, and are not counted toward PROMOTE_MEETINGS.
ROUTINE_PER_BOARD = 2
ROUTINE_BOARDS = ('select-board', 'finance-committee')
# A subject word used in more than this many items across every board is too common to
# follow an article by ("budget", "school").
KW_MAX_DF = 250
# A BOARD VOTE BELONGS TO THE NEXT TOWN MEETING within this many days, unless it names the
# meeting's date -- then it belongs to that one.
ASSIGN_DAYS = 210

MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
          'september', 'october', 'november', 'december']
DATE = re.compile(r'\b(%s)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b' % '|'.join(MONTHS), re.I)
KIND = re.compile(r'\b(annual|special)\s+town\s+meeting\b', re.I)
WORDNUM = {w: i for i, w in enumerate(
    'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen '
    'fifteen sixteen seventeen eighteen nineteen twenty'.split())}
WORDNUM.update({'twenty-one': 21, 'twenty-two': 22, 'twenty-three': 23, 'twenty-four': 24,
                'twenty-five': 25, 'thirty': 30})

# A BILL WARRANT IS NOT A TOWN MEETING WARRANT. The Select Board signs payroll and vendor
# warrants weekly and the town clerk's election warrant every year; none is a Town Meeting.
# build_agenda_threads.py treats a bare "warrants" as procedural for exactly this reason, so
# the test here is narrower than "the word warrant": a Town Meeting word, or an article.
NOT_TM = re.compile(r'\belection\b|\bprimary\b|\bpayroll\b|\bbills?\b|\bvendor|\btreasur|'
                    r'accounts payable|expenditure|\bballot\b|\bweekly\b', re.I)
NUMWORDS = 'one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty'
# Case matters for one alternative only: a DRAFT article is lettered ("Article L"), and a
# capital letter is what tells it from "article about".
TM_WORDS = re.compile(r'(?i:\btown\s+meeting\b|\bwarrant\s+articles?\b'
                      r'|\b(?:open|close|closing|opening)\s+(?:of\s+)?the\s+warrant\b'
                      r'|\b(?:on|in|to|from)\s+the\s+(?:special\s+|annual\s+)?warrant\b'
                      r'|\barticles?\s+(?:\d{1,2}|' + NUMWORDS + r')\b'
                      r'|\bwarrant\b.{0,80}\barticles\b)'
                      r'|\b[Aa]rticles?\s+[A-Z]{1,2}\b')
_D = r'(?:%s)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}' % '|'.join(MONTHS)
# A MEETING'S DATE IS THE ONE BESIDE ITS NAME: "the Special Town Meeting on August 8, 2016",
# "the November 17, 2026 special town meeting", "Town Meeting (May 7, 2016)", "Town Meeting
# date to August 22, 2016". A date elsewhere in the motion is something else -- "Open the
# Annual Town Meeting warrant on January 12, 2022" is the day the warrant opened.
MEET_DATE = re.compile(r'(?i:\b(?:annual|special)\s+town\s+meeting\s*(?:\(|,)?\s*(?:date\s+to\s+|scheduled\s+for\s+|for\s+|on\s+)?'
                       r'(?:\w+day,?\s+)?' + _D + r'|' + _D + r'\s+(?:annual|special)\s+town\s+meeting\b)')
ART_REF = re.compile(r'\barticles?\s+(?!97\b)(\d{1,2}|%s)\b' % '|'.join(sorted(WORDNUM, key=len, reverse=True)), re.I)

EVENTS = [  # (event, pattern) -- the first that matches names what a board did
    ('called', re.compile(r'\bcall(?:ed|ing)?\s+(?:a|the)\s+(?:special|annual)\s+town\s+meeting', re.I)),
    ('warrant opened', re.compile(r'\bopen(?:ed|ing)?\s+(?:of\s+)?the\s+warrant', re.I)),
    ('warrant closed', re.compile(r'\bclos(?:e|ed|ing)\s+(?:of\s+)?the\s+warrant', re.I)),
    ('warrant approved', re.compile(r'\b(?:approve|sign|execute|accept)\w*\s+(?:the\s+)?(?:\w+\s+){0,6}?(?:town\s+meeting\s+)?warrant\b(?!\s+article)', re.I)),
    ('placed', re.compile(r'\b(?:include|place|add|insert|put)\w*\b.{0,120}?\b(?:on|in|to)\s+the\s+(?:\w+\s+){0,4}?warrant\b'
                          r'|for\s+inclusion\s+(?:in|on)\s+the|^\s*(?:to\s+)?(?:include|place|insert)\s+article\b', re.I)),
    ('recommended', re.compile(r'\brecommend|\bsupport\b|\bfavorabl|\bdisapprov|\bnot\s+recommend', re.I)),
    ('hearing', re.compile(r'\bpublic\s+hearing\b', re.I)),
    ('deferred', re.compile(r'\bdefer', re.I)),
    ('referred', re.compile(r'\brefer\w*\b', re.I)),
]


def read_csv(p):
    return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []


def iso(m):
    """A DATE match -> YYYY-MM-DD, or '' if it is not a real day."""
    try:
        return dt.date(int(m.group(3)), MONTHS.index(m.group(1).lower()) + 1, int(m.group(2))).isoformat()
    except ValueError:
        return ''


def squash(s):
    return re.sub(r'\s+', ' ', s or '').strip()


def pages_of(text):
    """[(pdf page number, offset)] from the ===PAGE N=== markers every extracted text carries."""
    return [(int(m.group(1)), m.start()) for m in re.finditer(r'===PAGE (\d+)===', text)]


def page_at(marks, pos):
    p = 1
    for n, off in marks:
        if off > pos:
            break
        p = n
    return p


def year_words(s):
    """"Two Thousand and Twenty-Six" -> 2026, "two thousand and nineteen" -> 2019."""
    s = s.lower().replace('-', ' ')
    m = re.search(r'two thousand(?: and)? ([a-z ]+)', s)
    if not m:
        return None
    n = 0
    for w in m.group(1).split():
        if w in WORDNUM:
            n += WORDNUM[w]
        elif w == 'twenty':
            n += 20
        else:
            break
    return 2000 + n if n else None


# =========================================================================================
# 1. DOCUMENTS. Every index in sources/, never one folder (CLAUDE.md: a hardcoded folder is a
#    latent break). A document is a candidate when its catalogue label names a Town Meeting
#    or a warrant; it is then READ, and its role and date come from its own words.
# =========================================================================================

def catalogue():
    """[{label, local, text, town_url}] for every catalogued document that might be about a
    Town Meeting, from every sources/*/index.csv."""
    out = []
    for idx in sorted(glob.glob(os.path.join(ROOT, 'sources', '*', 'index.csv'))):
        folder = os.path.basename(os.path.dirname(idx))
        for r in read_csv(idx):
            if folder == 'meetings':
                label = r.get('title') or ''
                if not KIND.search(label):
                    continue
                txt = os.path.join('sources', 'meetings', 'text', re.sub(r'\.\w+$', '.txt', r['path']))
                out.append({'label': label, 'local': 'sources/meetings/' + r['path'], 'text': txt,
                            'town_url': r['url'], 'via': 'agenda', 'board_date': r['date']})
                continue
            label = r.get('label') or r.get('title') or ''
            if not re.search(r'town\s+meeting|warrant', label, re.I) or re.search(r'election', label, re.I):
                continue
            out.append({'label': label, 'local': r.get('local') or '', 'text': r.get('text') or '',
                        'town_url': (r.get('upstream') or r.get('url') or '').split()[0] if (r.get('upstream') or r.get('url')) else '',
                        'via': folder, 'board_date': ''})
    return out


def read_text(rel):
    p = os.path.join(ROOT, rel) if rel else ''
    return open(p, encoding='utf-8', errors='replace').read() if p and os.path.exists(p) else ''


def doc_meeting(text):
    """(kind, date) the document is FOR, from its own words; ('', '') if it does not say.

    The legal notice says it outright -- "voted to call a Special Town Meeting for Tuesday,
    November 17, 2026" -- and a warrant prints the meeting in its heading. The first kind
    with a date within 200 characters after it, in the first pages, is the one."""
    m = re.search(r'(?:call|for)\s+an?\s+(annual|special)\s+town\s+meeting\s+(?:scheduled\s+)?for\s+'
                  r'(?:\w+day,?\s+)?((?:%s)\s+\d{1,2},?\s+\d{4})' % '|'.join(MONTHS), text, re.I)
    if m:
        d = DATE.search(m.group(2))
        return m.group(1).lower(), iso(d)
    head = text[:9000]
    for k in KIND.finditer(head):
        d = DATE.search(head, k.end(), k.end() + 220)
        if d and iso(d):
            return k.group(1).lower(), iso(d)
    # "SPECIAL TOWN MEETING WARRANT \n September 3, 2026" puts the date after; "INDEX OF MAY 7,
    # 2016 ANNUAL TOWN MEETING ARTICLES" puts it before.
    for k in KIND.finditer(head):
        ds = [d for d in DATE.finditer(head, max(0, k.start() - 60), k.start()) if iso(d)]
        if ds:
            return k.group(1).lower(), iso(ds[-1])
    return '', ''


def notice_facts(text):
    """What a legal notice states: when the board voted to call it, when the warrant opens
    and closes, and the date the notice is dated."""
    f = {}
    m = re.search(r'at the meeting of\s+((?:%s)\s+\d{1,2},?\s+\d{4})' % '|'.join(MONTHS), text, re.I)
    if m:
        f['called_on'] = iso(DATE.search(m.group(1)))
    m = re.search(r'open(?:ed)?\s+the\s+warrant\s+for\s+submission\s+of\s+articles\s+on\s+'
                  r'(?:\w+day,?\s+)?((?:%s)\s+\d{1,2},?\s+\d{4})' % '|'.join(MONTHS), text, re.I)
    if m:
        f['warrant_opens'] = iso(DATE.search(m.group(1)))
    m = re.search(r'close\s+the\s+warrant\s+on\s+(?:\w+day,?\s+)?((?:%s)\s+\d{1,2},?\s+\d{4})' % '|'.join(MONTHS), text, re.I) \
        or re.search(r'by\s+5:00\s*PM\s+on\s+(?:\w+day,?\s+)?((?:%s)\s+\d{1,2},?\s+\d{4})' % '|'.join(MONTHS), text, re.I)
    if m:
        f['warrant_closes'] = iso(DATE.search(m.group(1)))
    m = re.search(r'Dated:\s*((?:%s)\s+\d{1,2},?\s+\d{4})' % '|'.join(MONTHS), text, re.I)
    if m:
        f['notice_dated'] = iso(DATE.search(m.group(1)))
    return f


# -----------------------------------------------------------------------------------------
# THE WARRANT, ARTICLE BY ARTICLE. Three layouts across 2015-2026, all real:
#   "ARTICLE 8.  FISCAL YEAR 2026 BUDGET ADJUSTMENTS" -- a printed title (2026)
#   "ARTICLE 4.  To see if the Town will vote ..."    -- no title at all (2017-2024)
#   an index "ARTICLE 1.  CC  Reauthorize Revolving Fund" and then the body (2015, 2016)
# A run of headings restarting at 1 is one list; a list whose entries hold "To see if" is
# the warrant, one whose entries do not is an index of titles.
# -----------------------------------------------------------------------------------------
HEAD = re.compile(r'^[ \t]*ARTICLE[ \t]+(\d{1,2})(?:[ \t]+(\d))?[ \t]*[.:]?[ \t]*(.*)$', re.M)
END = re.compile(r'And you are directed to serve this Warrant|Hereof,?\s+fail not|'
                 r'^\s*INDEX OF\b|^\s*FINANCE COMMITTEE REPORT\s*$', re.I | re.M)
AMOUNT = re.compile(r'\$\s?\d[\d,]*(?:\.\d{2})?')
SPONSOR = re.compile(r'\((?:Submitted|Sponsored|Requested|Inserted)\s+by\s+(?:the\s+)?([^)]{3,90})\)', re.I)
PETITION = re.compile(r'citizens?\W{0,3}\s*petition', re.I)
FINCOM_REC = re.compile(r'FINANCE\s+COMMITTEE\s+RECOMMENDATION\s*:?[ \t]*([^\n]*)', re.I)
SB_REC = re.compile(r'(?:SELECT\s+BOARD|BOARD\s+OF\s+SELECTMEN)\s+RECOMMENDATION\s*:?[ \t]*([^\n]*)', re.I)


def first_sentence(words):
    """The warrant's own sentence: "To see if the Town will vote to ... ; or take any other
    action relative thereto". Up to the first semicolon or "relative thereto", at most 600
    characters. A colon ends it too: what follows "as presented below:" is a table or a bylaw
    -- a revolving fund's spending cap, a fine -- not the sum the article asks for."""
    m = re.search(r'relative\s+thereto|[;:]', words)
    return words[:m.end()] if m else words[:600]


def headings(text):
    """Every article heading, with the OCR's split numbers rejoined: "ARTICLE 2 6." in the
    2016 booklet is article 26, which the sequence around it proves."""
    hs = []
    for m in HEAD.finditer(text):
        n = int(m.group(1))
        if m.group(2) and hs and int(m.group(1) + m.group(2)) == hs[-1]['n'] + 1:
            n = int(m.group(1) + m.group(2))
        hs.append({'n': n, 'start': m.start(), 'end': m.end(), 'rest': m.group(3).strip()})
    return hs


def runs_of(hs):
    runs = []
    for h in hs:
        if h['n'] == 1:
            runs.append([])
        if runs:
            if runs[-1] and h['n'] <= runs[-1][-1]['n']:
                continue          # a number out of sequence is an OCR artefact; the gap shows it
            runs[-1].append(h)
    return runs


_SEP = r'[ \t]*(?:\n[ \t]*)?'
SPLIT_HEAD = re.compile(r'(?m)^[ \t]*' + _SEP.join('ARTICLE') + r'[ \t]*(?:\n[ \t]*)?(\d{1,2})[ \t]*([.:])')


def normalise(text):
    """THE TEXT LAYER BREAKS WORDS ACROSS LINES: "AR / TICLE 11:", "ARTIC / LE 7:" and
    "ARTICLE / 9:" in the November 2024 booklet. Rejoined here, and only here, where a whole
    heading -- the word, a number, a full stop or colon -- survives being put back together."""
    return SPLIT_HEAD.sub(lambda m: 'ARTICLE %s%s' % (m.group(1), m.group(2)), text)


def parse_warrant(text):
    """{'articles': [...], 'index_titles': {n: title}, 'numbered_to': N, 'notes': [...]}."""
    text = normalise(text)
    marks = pages_of(text)
    hs = headings(text)
    runs = runs_of(hs)
    index, body, notes = {}, None, []
    for r in runs:
        is_body = sum(1 for i, h in enumerate(r)
                      if re.search(r'to\s+see\s+if', text[h['start']:h['start'] + 500], re.I)) > len(r) / 2
        if is_body and body is None:
            body = r
        elif not is_body:
            for h in r:
                t = re.sub(r'^CC\s+', '', h['rest']).strip()
                if t and not re.match(r'to\s+see\s+if', t, re.I):
                    index.setdefault(h['n'], squash(t))
    arts = []
    if body:
        for i, h in enumerate(body):
            stop = body[i + 1]['start'] if i + 1 < len(body) else len(text)
            e = END.search(text, h['end'], stop)
            span = text[h['start']:e.start() if e else min(stop, h['start'] + 12000)]
            rest = re.sub(r'^CC\s+', '', h['rest']).strip()
            title = ''
            if rest and not re.match(r'to\s+see\s+if', rest, re.I) and sum(c.isupper() for c in rest) > len(rest) * .5:
                title = squash(rest)
                # a printed title wraps: the next line, while it is still capitals and before
                # the "(Submitted by" line, is the rest of it
                nxt = text[h['end']:h['end'] + 200].split('\n')[1:2]
                if nxt and nxt[0].strip() and nxt[0].strip().isupper() and not nxt[0].strip().startswith('('):
                    title = squash(title + ' ' + nxt[0])
            body_text = squash(span)
            w = re.search(r'to\s+see\s+(?:if|whether)\b.*?(?:relative\s+thereto|$)', body_text, re.I)
            words = w.group(0) if w else ''
            # THE ARTICLE'S SUM IS IN ITS FIRST SENTENCE. A bylaw article prints the whole bylaw
            # after it, and "$300 fine" in section 6 is not what the article appropriates.
            a = AMOUNT.search(first_sentence(words))
            sp = SPONSOR.search(body_text)
            sponsor = squash(sp.group(1)) if sp else ('citizen petition' if PETITION.search(body_text[:1500]) else '')
            fc = FINCOM_REC.search(span)
            sb = SB_REC.search(span)
            arts.append({'n': h['n'], 'title': title, 'index_title': index.get(h['n'], ''),
                         'warrant_words': words[:600], 'amount': a.group(0).replace(' ', '') if a else '',
                         'sponsor': sponsor,
                         'fincom_printed': squash(fc.group(1)).strip(' .') if fc else '',
                         'sb_printed': squash(sb.group(1)).strip(' .') if sb else '',
                         'page': page_at(marks, h['start'])})
        nums = [a['n'] for a in arts]
        gaps = sorted(set(range(1, max(nums) + 1)) - set(nums))
        if gaps:
            notes.append('the text holds no heading for article(s) %s' % ', '.join(map(str, gaps)))
    numbered_to = max([a['n'] for a in arts] + list(index) + [0])
    # THE SIGNATURE THAT IS THIS WARRANT'S. A booklet prints the election warrant too, and the
    # 2022 booklet's copy of it is dated "two thousand and twenty one" -- a year early. So the
    # signature after the articles wins, then the last one before them outside an election
    # warrant; the date is kept only if it falls in the months before the meeting.
    sigs = []
    for g in re.finditer(r'Given under our hands,?\s+this\s+(\d{1,2})\s*(?:st|nd|rd|th)?\s+day\s+of\s+(%s)\s+in\s+the\s+year\s+([A-Za-z \-]+)'
                         % '|'.join(MONTHS), text, re.I):
        y = year_words(g.group(3))
        if not y or re.search(r'TOWN\s+ELECTION', text[max(0, g.start() - 3500):g.start()], re.I):
            continue
        try:
            sigs.append((g.start(), dt.date(y, MONTHS.index(g.group(2).lower()) + 1, int(g.group(1))).isoformat()))
        except ValueError:
            pass
    first = body[0]['start'] if body else 0
    after = [d for off, d in sigs if off > first]
    before = [d for off, d in sigs if off <= first]
    signed = (after or before[-1:] or [''])[0]
    return {'articles': arts, 'index_titles': index, 'numbered_to': numbered_to, 'notes': notes,
            'signed': signed, 'signatures': [d for _, d in sigs]}


# =========================================================================================
# 2. THE BOARDS' OWN RECORDS: votes about a Town Meeting, in both records of each board.
# =========================================================================================

def board_items():
    """[{board_slug, date, source, kind, text, outcome, quote, cite...}] -- every vote,
    decision and topic in the town's minutes and ours that is about a Town Meeting."""
    import build_threads as BT
    record, _ = BT.the_record()
    town = BT.town_record()
    out = []
    for (slug, date), rec in record.items():
        if slug == 'town-meeting':
            continue
        for v in rec['votes']:
            if not v['procedural']:
                out.append({'board_slug': slug, 'board': rec['board'], 'date': date, 'source': 'ours',
                            'kind': 'vote', 'text': v['motion'], 'outcome': v['outcome'], 't': v['t'],
                            'video_url': v['video_url'], 'quote': '', 'recording_note': v.get('recording_note') or ''})
        for it in rec['items']:
            if it['kind'] in ('decision', 'topic', 'comment', 'contention', 'budget'):
                out.append({'board_slug': slug, 'board': rec['board'], 'date': date, 'source': 'ours',
                            'kind': it['kind'], 'text': it['text'], 'outcome': '', 't': it.get('t'),
                            'video_url': it.get('video_url') or (rec['recordings'][0] if rec['recordings'] else ''),
                            'quote': '', 'recording_note': it.get('recording_note') or ''})
    for (slug, date), rec in town.items():
        if slug == 'town-meeting':
            continue
        for it in rec['items']:
            out.append(dict(it, board_slug=slug, date=date, board=''))
    return out, record, town


def about_town_meeting(text):
    """Is this about a Town Meeting? Named outright ("town meeting", an article by number),
    yes -- an article may well be about bills. Otherwise only a warrant that is not a bill,
    payroll or election warrant."""
    if re.search(r'\btown\s+meeting\b|\bwarrant\s+articles?\b', text, re.I) or ART_REF.search(text):
        return True
    return bool(TM_WORDS.search(text)) and not NOT_TM.search(text)


def plain_date(d):
    """2026-08-27 -> 27 August 2026: dates a resident reads, not ISO."""
    import datetime as _dt
    try:
        x = _dt.date.fromisoformat(d)
    except (TypeError, ValueError):
        return d
    return '%d %s %d' % (x.day, x.strftime('%B'), x.year)


def event_of(text):
    for name, rx in EVENTS:
        if rx.search(text):
            return name
    return 'discussed'


def art_numbers(text):
    out = []
    for m in ART_REF.finditer(text):
        g = m.group(1).lower()
        out.append(int(g) if g.isdigit() else WORDNUM.get(g))
    return [n for n in out if n]


# A LIST OF ARTICLES: "articles 2,3,6,16,17,18,19", "articles 16 through 19", "articles 4 and 5".
# ART_REF takes the first number after the word and nothing else, so a consent calendar naming
# seven articles was filed under one of them and the other six read as "result not found"
# (23 October 2026, the May 2026 Annual Town Meeting).
ART_LIST = re.compile(r'\barticles?\s+(\d{1,2}(?:\s*(?:,|;?\s*and|&|through|thru|to|-|\u2013)\s*\d{1,2})*)', re.I)


def art_list(text):
    """The articles of the FIRST list in a motion, ranges expanded -- for a consent calendar,
    whose first list is what it decides ("...; article 7 removed on a hold" is not)."""
    m = ART_LIST.search(text)
    if not m:
        return []
    out, parts = [], re.split(r'\s*(,|;?\s*and|&)\s*', m.group(1))
    for p in parts:
        r = re.match(r'(\d{1,2})\s*(?:through|thru|to|-|\u2013)\s*(\d{1,2})$', p.strip())
        if r and int(r.group(1)) < int(r.group(2)):
            out.extend(range(int(r.group(1)), int(r.group(2)) + 1))
        elif p.strip().isdigit():
            out.append(int(p.strip()))
    return out


# A VOTE MARKED PROCEDURAL THAT STILL DECIDES AN ARTICLE. Our minutes mark "accept the reports of
# town officers (article 1)" procedural, so it was skipped and Article 1 read as not found. Real
# procedure -- moving the question, recess, adjournment, reconsideration -- stays out.
PROCEDURE = re.compile(r'move\s+the\s+question|previous\s+question|recess|adjourn|reconsider|'
                       r'waive\s+the\s+reading|admit|non-?voters?|dissolve|quorum|moderator|'
                       r'order\s+of\s+(?:the\s+)?articles|take\s+.*out\s+of\s+order', re.I)


# =========================================================================================
# 3. THE REGISTER.
# =========================================================================================

def build():
    today = dt.date.today().isoformat()
    signals = collections.defaultdict(lambda: {'kinds': set(), 'signals': collections.OrderedDict(),
                                               'docs': [], 'facts': {}, 'first': None})

    def sig(date, kind, name, ref, when=''):
        if not date:
            return
        m = signals[date]
        if kind:
            m['kinds'].add(kind)
        m['signals'].setdefault(name, ref)
        when = when or date
        if not m['first'] or when < m['first'][0]:
            m['first'] = (when, name, ref)

    # documents
    warrants = {}
    for d in catalogue():
        text = read_text(d['text'])
        if not text:
            continue
        kind, date = doc_meeting(text)
        if not date:
            continue
        is_notice = bool(re.search(r'voted\s+to\s+call|opened\s+the\s+warrant\s+for\s+submission|open\s+the\s+warrant\s+for\s+submission', text, re.I))
        is_warrant = bool(re.search(r'notify\s+and\s+warn', text, re.I)) and not re.search(r'draft', d['local'], re.I)
        # A DRAFT is a draft WARRANT: "draft" in the name is not enough. The Brooks House
        # presentation (a deck "to Town Meeting", marked draft) entered the register as a
        # Special Town Meeting on 17 November 2024 that never happened (23 October 2026).
        is_draft = bool(re.search(r'draft', d['local'], re.I)) and bool(
            re.search(r'warrant', d['local'], re.I) or len(re.findall(r'\bARTICLE\s+[0-9A-Z]{1,2}\b', text)) >= 3)
        role = 'notice' if is_notice and not is_warrant else 'warrant' if is_warrant else 'draft' if is_draft else 'other'
        if role == 'other':
            continue
        facts = notice_facts(text) if role == 'notice' else {}
        doc = dict(d, role=role, kind=kind, facts=facts)
        if role == 'warrant':
            w = parse_warrant(text)
            if not w['articles']:
                doc['role'] = role = 'warrant (no articles in its text)'
            doc['parsed'] = w
        signals[date]['docs'].append(doc)
        sig(date, kind, 'notice' if role == 'notice' else 'warrant' if role.startswith('warrant') else 'draft',
            d['local'], facts.get('notice_dated') or facts.get('called_on') or facts.get('warrant_opens')
            or ok_signed(doc, date) or (dated_in_name(d['local']) if role == 'draft' else ''))
        if role == 'notice' and d['via'] == 'agenda':
            sig(date, kind, 'agenda', d['local'], d['board_date'] if d['board_date'] < date else '')
        for k, v in facts.items():
            signals[date]['facts'].setdefault(k, (v, d['local']))

    # the Select Board's vote to call it, in either record
    items, record, town = board_items()
    # A SELECT BOARD VOTE THAT NAMES A TOWN MEETING STILL TO COME -- to call it, or to set its
    # schedule ("Approve the draft schedule for the November 17, 2026 special town meeting").
    # The date must sit beside the meeting's name, so a date elsewhere in the motion cannot
    # summon a meeting that does not exist.
    for it in items:
        if it['kind'] != 'vote' or it['board_slug'] != 'select-board':
            continue
        for k in MEET_DATE.finditer(it['text']):
            when = iso(DATE.search(k.group(0)))
            if not when or when <= it['date']:
                continue
            ref = ('the town\'s minutes' if it['source'] == 'town' else 'our minutes') + ', Select Board, ' + it['date']
            sig(when, re.search(r'annual|special', k.group(0), re.I).group(0).lower(), 'sb-vote', ref, it['date'])
            if EVENTS[0][1].search(it['text']):
                signals[when]['facts'].setdefault('called_on', (it['date'], ref))
            break

    # the Clerk's printed record
    clerk = read_csv(TMVOTES)
    undated = [r for r in clerk if not r['meeting_date']]
    # A CLERK ROW WITH NO MEETING DATE STAYS UNPLACED. Reading the date off a nearby page
    # heading was tried and put two different Special Town Meetings' "Article 1" into one
    # meeting: the FY2011 report prints a July 18, 2011 heading, and the undated rows after it
    # belong to a later Special whose heading carries no date. Unplaced, and counted.
    for r in clerk:
        sig(r['meeting_date'], r['meeting'], 'clerk', r['source_doc'])
    # ours, and the recordings
    for (slug, date), rec in record.items():
        if slug == 'town-meeting':
            sig(date, '', 'ours', 'sources/data/recording-minutes/town-meeting/%s-*.json' % date)
    for r in read_csv(VIDEOS):
        if r['board_slug'] == 'town-meeting' and r['role'] == 'owner' and r['meeting_date']:
            k = re.search(r'annual|special', r['title_stem'], re.I)
            sig(r['meeting_date'], k.group(0).lower() if k else '', 'video', 'https://www.youtube.com/watch?v=' + r['video_id'])

    # THE CLERK'S DATE CAN DISAGREE WITH THE WARRANT'S. The FY2016 annual report prints the
    # 2016 Annual Town Meeting as "May 5, 2016" on every page of its proceedings; the warrant
    # calls it for May 7, 2016, a Saturday, and the recording is filed under May 7. One
    # meeting, two printed dates. A date only the Clerk's record holds, within a week of a
    # meeting of the same kind that other records hold, is that meeting -- and the row says
    # both dates rather than choosing silently.
    conflicts = {}
    for date in sorted(signals):
        if set(signals[date]['signals']) != {'clerk'}:
            continue
        kinds = {r['meeting'] for r in clerk if r['meeting_date'] == date}
        near = [d for d in signals if d != date and set(signals[d]['signals']) - {'clerk'}
                and abs((dt.date.fromisoformat(d) - dt.date.fromisoformat(date)).days) <= 7
                and (signals[d]['kinds'] & kinds or not signals[d]['kinds'])]
        if len(near) == 1:
            to = near[0]
            for r in clerk:
                if r['meeting_date'] == date:
                    r['meeting_date'], r['_printed_date'] = to, date
            signals[to]['signals'].setdefault('clerk', signals[date]['signals']['clerk'])
            signals[to]['kinds'] |= kinds
            conflicts[to] = date
            del signals[date]
    # A DOCUMENT ABOUT A MEETING DOES NOT CREATE ONE (TJ, 23 October 2026: "decks shouldnt be
    # creating meetings"). Only a record that a meeting was CALLED or HELD can put a date in the
    # register: the legal notice, the posted warrant, the Select Board's vote, its agenda, the
    # Clerk's record, our minutes or the town's recording. A draft attaches to a meeting those
    # records already hold and never stands alone -- a presentation that misprinted a past
    # meeting's date (the Brooks House deck: "November 17, 2024" for 12 November) made one.
    CREATES = {'notice', 'warrant', 'sb-vote', 'agenda', 'clerk', 'ours', 'video'}
    for date in [d for d in signals if not set(signals[d]['signals']) & CREATES]:
        print('  not a meeting: %s, only %s' % (date, ', '.join(signals[date]['signals'])), file=sys.stderr)
        del signals[date]
    # ONE DATE CAN HOLD TWO MEETINGS: a Special Town Meeting held inside the Annual. The
    # Clerk prints them apart (2011-05-07), and that is the only record that separates them.
    meetings = []
    for date in sorted(signals):
        s = signals[date]
        kinds = sorted(s['kinds']) or ['']
        clerk_kinds = {r['meeting'] for r in clerk if r['meeting_date'] == date}
        for kind in (sorted(clerk_kinds) if len(clerk_kinds) > 1 else [None]):
            meetings.append(meeting_row(date, kind, s, kinds, clerk, today))
            if date in conflicts:
                meetings[-1]['date_conflict'] = ('the Town Clerk\'s record prints %s; the warrant and the recording say %s'
                                                 % (pretty(conflicts[date]), pretty(date)))
    return meetings, items, record, town, clerk, undated


def dated_in_name(path):
    """A draft's own date, from the name the Finance Committee gave it: "draft-warrant-4.5.26"
    is 5 April 2026, "draft-atm-warrant-articles-2-28-23" 28 February 2023."""
    m = re.search(r'(\d{1,2})[.-](\d{1,2})[.-](\d{2,4})(?!\d)', os.path.basename(path))
    if not m:
        return ''
    y = int(m.group(3))
    try:
        return dt.date(y + 2000 if y < 100 else y, int(m.group(1)), int(m.group(2))).isoformat()
    except ValueError:
        return ''


def ok_signed(doc, date):
    sg = (doc.get('parsed') or {}).get('signed') or ''
    return sg if sg and 0 <= (dt.date.fromisoformat(date) - dt.date.fromisoformat(sg)).days <= 150 else ''


def meeting_row(date, kind_override, s, kinds, clerk, today):
    kind = kind_override or next((k for k in kinds if k), '')
    kind_basis = 'stated' if kind else ''
    if not kind:
        # NOT STATED ANYWHERE WE READ. May is the Annual by the town's bylaw; anything else is
        # a Special. Ours, labelled.
        kind = 'annual' if date[5:7] in ('05', '06') else 'special'
        kind_basis = 'by the month (May or June is the Annual) -- not printed in what we hold'
    mid = '%s-%s' % ('atm' if kind == 'annual' else 'stm', date)
    docs = [d for d in s['docs'] if not kind_override or d['kind'] in ('', kind_override)]
    warrant = next((d for d in docs if d['role'] == 'warrant'), None)
    if warrant and warrant['kind'] and warrant['kind'] != kind:
        warrant = None
    notice = next((d for d in docs if d['role'] == 'notice'), None)
    facts = {k: v for k, v in s['facts'].items()}
    signed = (warrant.get('parsed') or {}).get('signed', '') if warrant else ''
    if signed and not (0 <= (dt.date.fromisoformat(date) - dt.date.fromisoformat(signed)).days <= 150):
        signed = ''          # a signature dated after the meeting, or a year before it, is a misprint
    return {
        'id': mid, 'date': date, 'kind': kind, 'kind_basis': kind_basis,
        'status': 'upcoming' if date > today else 'held',
        'signals': ';'.join(s['signals']),
        'first_signal': s['first'][0] if s['first'] else '',
        'first_signal_kind': s['first'][1] if s['first'] else '',
        'first_signal_ref': s['first'][2] if s['first'] else '',
        'called_on': (facts.get('called_on') or ('', ''))[0],
        'called_ref': (facts.get('called_on') or ('', ''))[1],
        'warrant_opens': (facts.get('warrant_opens') or ('', ''))[0],
        'warrant_opens_ref': (facts.get('warrant_opens') or ('', ''))[1],
        'warrant_closes': (facts.get('warrant_closes') or ('', ''))[0],
        'warrant_closes_ref': (facts.get('warrant_closes') or ('', ''))[1],
        'notice_doc': notice['local'] if notice else '',
        'notice_town_url': notice['town_url'] if notice else '',
        'warrant_doc': warrant['local'] if warrant else '',
        'warrant_town_url': warrant['town_url'] if warrant else '',
        'warrant_signed': signed, 'date_conflict': '',
        '_warrant': warrant, '_signals': s,
    }


# =========================================================================================
# 4. ARTICLES.
# =========================================================================================

def norm_words(s):
    stop = set('the a an of to and or for in on by be any other action relative thereto town vote will see if '
               'sum sums money raise appropriate transfer from available funds fund fy fiscal year article '
               'thereof such as said with under its this that which all amount amounts take may necessary '
               'lunenburg authorize authorization'.split())
    return {w for w in re.findall(r'[a-z]{3,}', (s or '').lower()) if w not in stop}


def amounts_in(s):
    return {re.sub(r'[^\d.]', '', a).rstrip('0').rstrip('.') for a in AMOUNT.findall(s or '')}


def tally(s):
    """(for, against) from a printed or heard count -- "passed 340-68", "(Yes-164, No-7)",
    "(98 YES, 12NO)", "74 no to 37 yes" -- or None. A year or a fraction is not a count."""
    s = (s or '').replace('\u2013', '-')
    m = re.search(r'yes\W{0,3}(\d{1,4})\D{1,12}no\W{0,3}(\d{1,4})', s, re.I) or \
        re.search(r'(\d{1,4})\s*yes\D{1,8}(\d{1,4})\s*no', s, re.I)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r'(\d{1,4})\s*no\s+to\s+(\d{1,4})\s*yes', s, re.I)
    if m:
        return int(m.group(2)), int(m.group(1))
    m = re.search(r'(\d{1,4})\s+(?:against|opposed)\s+to\s+(\d{1,4})\s+in\s+favou?r', s, re.I)
    if m:
        return int(m.group(2)), int(m.group(1))
    for m in re.finditer(r'(?<![\d$/.,])(\d{1,4})\s*(?:-|to)\s*(\d{1,4})(?![\d/.,])', s):
        a, b = int(m.group(1)), int(m.group(2))
        if 1900 < a < 2100 or 1900 < b < 2100:
            continue
        return a, b
    return None


def divided(s):
    t = tally(s)
    return bool(t and sum(t) and min(t) / sum(t) >= DIVIDED_SHARE)


def clerk_divided(r):
    return divided(r['quote'])


def our_article_votes(rec):
    """{article: {'main': vote|None, 'votes': [...], 'amended', 'divided', 'put_off'}} from our
    minutes of one Town Meeting -- the article's main motion, told apart from amendments,
    boards stating positions, and procedure."""
    out = collections.defaultdict(lambda: {'main': None, 'votes': []})
    for v in rec['votes']:
        ns = art_numbers(v['motion'])
        if not ns:
            continue
        if v['procedural'] and PROCEDURE.search(v['motion']):
            continue
        # SEVERAL ARTICLES, ONE VOTE. Town Meeting often takes a group together -- a consent
        # calendar, or "articles 9, 10 and 11" moved at once (TJ, 23 October 2026: "we
        # frequently group many articles into 1 vote"). A motion whose FIRST reference is a
        # plural list decides every article in it; one that names a single article and
        # mentions another ("amend article 24 to fund ...") stays with the first.
        group = art_list(v['motion'])
        joint = len(group) > 1 or re.search(r'consent', v['motion'], re.I)
        for n in ((group or ns[:1]) if joint else ns[:1]):
            out[n]['votes'].append(v)
    for n, a in out.items():
        role = []
        for v in a['votes']:
            m = v['motion']
            if re.match(r'\s*(?:to\s+)?amend', m, re.I) or re.search(r'\bamendment\b', m, re.I):
                role.append('amend')
            elif re.search(r'recommendation|\bto support\b|convened|committee.{0,40}(?:support|position)', m, re.I):
                role.append('board')
            else:
                role.append('main')
        mains = [v for v, r in zip(a['votes'], role) if r == 'main']
        a['main'] = mains[-1] if mains else None
        a['amended'] = 'amend' in role and any(re.search(r'pass|carri|adopt', v['outcome'] or '', re.I)
                                              for v, r in zip(a['votes'], role) if r == 'amend')
        a['amend_tried'] = 'amend' in role
        oc = ' '.join((v['outcome'] or '') for v in a['votes'] if v in mains)
        a['divided'] = any(divided(v['outcome']) for v in mains)
        txt = ' '.join(v['motion'] + ' ' + (v['outcome'] or '') for v in a['votes'])
        a['put_off'] = bool(re.search(r'postpone|\btabled?\b|refer(?:red)?\s+(?:back|to)|indefinite', txt, re.I))
    return out


def our_result(v):
    """What our minutes say happened to an article: the main motion's outcome -- and a
    motion TO PASS OVER that passed means the article was passed over, not passed."""
    w = outcome_word(v['outcome'])
    if w == 'passed' and re.search(r'\bpass(?:ed)?\s+over\b', v['motion'], re.I) and not re.search(r'consent', v['motion'], re.I):
        return 'passed over'
    return w


def outcome_word(s):
    s = (s or '').lower()
    if re.search(r'pass(?:ed)?\s*over|passed_over', s):
        return 'passed over'
    if re.search(r'indefinit|postpone', s):
        return 'postponed'
    if re.search(r'fail|defeat|not\s+carr|rejected', s):
        return 'failed'
    if re.search(r'amended', s):
        return 'amended and passed'
    if re.search(r'pass|carri|adopt|approved|unanim', s):
        return 'passed'
    if re.search(r'not audible|unclear', s):
        return 'not clear in the record'
    return s[:40]


def build_articles(meetings, items, record, clerk):
    by_clerk = collections.defaultdict(list)
    for r in clerk:
        if r['meeting_date']:
            by_clerk[(r['meeting_date'], r['meeting'])].append(r)
    real = {'atm-%s-05' % m['date'][:4]: m['id'] for m in meetings if m['kind'] == 'annual'}
    drafts = {real.get(k, k): v for k, v in latest_drafts().items()}
    rows, unmatched_drafts, report = [], [], {}
    for m in meetings:
        arts = collections.OrderedDict()
        w = (m['_warrant'] or {}).get('parsed') or {}
        wdoc = m['_warrant']
        for a in w.get('articles', []):
            arts[a['n']] = {
                'title': a['title'] or a['index_title'],
                'title_from': 'the warrant' if a['title'] else 'the warrant\'s index' if a['index_title'] else '',
                'warrant_words': a['warrant_words'], 'amount': a['amount'], 'sponsor': a['sponsor'],
                'details_doc': wdoc['local'], 'details_town_url': wdoc['town_url'], 'details_page': a['page'],
                'fincom_printed': a['fincom_printed'], 'sb_printed': a['sb_printed'], 'evidence': {}}
        crows = by_clerk.get((m['date'], m['kind']), [])
        for r in crows:
            n = int(r['article'])
            a = arts.setdefault(n, {'title': '', 'title_from': '', 'warrant_words': '', 'amount': '',
                                    'sponsor': '', 'details_doc': '', 'details_town_url': '', 'details_page': '',
                                    'fincom_printed': '', 'sb_printed': '', 'evidence': {}})
            a['clerk'] = r
        rec = record.get(('town-meeting', m['date']))
        ours = our_article_votes(rec) if rec else {}
        for n, v in ours.items():
            if n not in arts and m['_warrant']:
                continue      # a number our minutes heard that the warrant does not have
            a = arts.setdefault(n, {'title': '', 'title_from': '', 'warrant_words': '', 'amount': '',
                                    'sponsor': '', 'details_doc': '', 'details_town_url': '', 'details_page': '',
                                    'fincom_printed': '', 'sb_printed': '', 'evidence': {}})
            a['ours'] = v
        # the boards' votes naming an article, for this meeting
        for it in items:
            if it.get('_meeting') != m['id'] or it['kind'] != 'vote':
                continue
            ns = art_numbers(it['text'])
            # BEFORE A WARRANT IS POSTED the Select Board places articles by subject, often with
            # no number ("Include the stormwater management bylaw fee structure in the warrant").
            # Each is a row of its own, keyed by its words, until the warrant numbers it.
            upcoming = m['status'] == 'upcoming' and not m['_warrant']
            if not ns and it['board_slug'] == 'select-board' and event_of(it['text']) == 'placed':
                subj = vote_subject(it['text'])
                same = next((k for k, a in arts.items() if not isinstance(k, str)
                             and contained(subj, a['title'] + ' ' + (a.get('clerk') or {}).get('subject', '') + ' '
                                           + ' '.join(vote_subject(v['text']) for v in a.get('board_votes') or []))), None)
                ns = [same] if same is not None else ['u:' + subj.lower()] if upcoming else []
            # A NUMBER USED BEFORE THE WARRANT WAS SIGNED may be a draft's number: the final
            # warrant renumbers. It attaches only to a meeting still being assembled, or after
            # the signature.
            if m['_warrant'] and m['warrant_signed'] and it['date'] < m['warrant_signed']:
                ns = [n for n in ns if isinstance(n, str)]
            for n in ns:
                if n in arts or upcoming:
                    if n not in arts:
                        arts[n] = {'title': '', 'title_from': '', 'warrant_words': '', 'amount': '', 'sponsor': '',
                                   'details_doc': '', 'details_town_url': '', 'details_page': '',
                                   'fincom_printed': '', 'sb_printed': '', 'evidence': {}, 'provisional': True}
                    arts[n].setdefault('board_votes', []).append(it)
        # drafts, matched by subject and amount -- never by letter, which renumbers
        dr = drafts.get(m['id'], [])
        matched = match_drafts(dr, arts)
        for d in dr:
            if d['letter'] not in matched:
                unmatched_drafts.append((m['id'], d))
        for n, a in sorted(arts.items(), key=lambda kv: (isinstance(kv[0], str), kv[0] if not isinstance(kv[0], str) else 0, str(kv[0]))):
            rows.append(article_row(m, n, a, matched_for(n, matched, dr)))
        report[m['id']] = {'parsed': len(w.get('articles', [])), 'numbered_to': w.get('numbered_to', 0),
                           'notes': w.get('notes', []), 'clerk': len(crows), 'ours': len(ours), 'drafts': len(dr)}
    return rows, unmatched_drafts, report


def latest_drafts():
    """{meeting id: [draft article]} -- the LAST draft the Finance Committee held for each
    Annual Town Meeting, one row per letter. `fy` is the budget's fiscal year, so the FY2027
    drafts are for the May 2026 meeting."""
    rows = read_csv(DRAFTS)
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        by[r['fy']][r['draft_label']].append(r)
    out = {}
    for fy, labels in by.items():
        def when(lbl):
            p = re.findall(r'\d+', lbl)
            m, d, y = (int(x) for x in p[:3])
            return (y + 2000 if y < 100 else y, m, d)
        last = max(labels, key=when)
        seen = collections.OrderedDict()
        for r in labels[last]:
            x = seen.setdefault(r['article_letter'], {'letter': r['article_letter'], 'title': squash(r['title']),
                                                      'amounts': set(), 'draft': last, 'file': r['source_file'],
                                                      'context': r['context']})
            if r['amount']:
                x['amounts'].add(re.sub(r'[^\d.]', '', r['amount']).rstrip('0').rstrip('.'))
        out['atm-%d-05' % (int(fy) - 1)] = list(seen.values())
    # keyed by month; resolve to the real meeting id later
    return {k: v for k, v in out.items()}


def match_drafts(drafts, arts):
    return _match_drafts(drafts, arts)


def _match_drafts(drafts, arts):
    """{letter: article number}. A draft matches the final article whose words CONTAIN most
    of the draft's title -- the draft is the shorter text -- and an amount in common decides a
    near tie. A draft whose title says nothing ("To see if the Town will vote to raise and
    appropriate...") is read with its first lines of context. Anything unclear is left
    unmatched and reported: a letter renumbers, so a wrong match is worse than none."""
    out, taken = {}, set()
    for d in drafts:
        dw = norm_words(d['title']) - GENERIC_DRAFT
        if len(dw) < 3:
            dw = norm_words(d['title'] + ' ' + d['context'][:240]) - GENERIC_DRAFT
        if len(dw) < 2:
            continue
        scores = []
        for n, a in arts.items():
            aw = norm_words(a['title'] + ' ' + a['warrant_words'][:400] + ' ' + (a.get('clerk') or {}).get('subject', ''))
            sc = len(dw & aw) / len(dw)
            if d['amounts'] & amounts_in(a['amount'] + ' ' + a['warrant_words'] + ' ' + (a.get('clerk') or {}).get('amount_as_printed', '')):
                sc += .25
            scores.append((sc, n))
        scores.sort(key=lambda x: (-x[0], str(x[1])))
        if not scores:
            continue
        best, bn = scores[0]
        second = scores[1][0] if len(scores) > 1 else 0
        if best >= .6 and best - second >= .2 and bn not in taken:
            out[d['letter']] = bn
            taken.add(bn)
    return out


GENERIC_DRAFT = set('placeholder submitted manager select board finance committee recommendation'.split())


def vote_subject(text):
    """What a placement vote is ABOUT, without the verb and the warrant around it:
    "Include Article 1 (reports of officers and committees) in the warrant" -> "reports of
    officers and committees"; "Place Article 5, middle high school track and field
    engineering, on the warrant" -> "middle high school track and field engineering"."""
    t = squash(text)
    m = re.search(r'\barticle\s+\w+\s*\(([^)]+)\)', t, re.I)
    if m:
        return m.group(1).strip()
    t = re.sub(r'^(?:to\s+)?(?:approve|place|include|add|insert|put|recommend(?:\s+approval\s+of)?)\s+(?:the\s+)?', '', t, flags=re.I)
    t = re.sub(r'^article\s+\w+\s*[,:]?\s*', '', t, flags=re.I)
    t = re.sub(r'\s*\((?:to\s+vote\s+it\s+down|[^)]*\bvote\b[^)]*)\)', '', t, flags=re.I)
    t = re.sub(r',?\s*(?:on|in|to|for\s+inclusion\s+(?:in|on))\s+the\s+(?:special\s+town\s+meeting\s+|annual\s+town\s+meeting\s+)?warrant\b.*$', '', t, flags=re.I)
    return t.strip(' ,.;:') or squash(text)


def contained(a, b):
    wa, wb = norm_words(a), norm_words(b)
    return bool(wa) and len(wa & wb) / len(wa) >= .6


def matched_for(n, matched, drafts):
    for letter, num in matched.items():
        if num == n:
            return next(d for d in drafts if d['letter'] == letter)
    return None


def article_row(m, n, a, draft):
    c, o = a.get('clerk'), a.get('ours')
    rec = lambda x: x and not re.match(r'^\s*$|^(?:deferred|to be made at town meeting|recommendation at town meeting)', x, re.I)
    bv = a.get('board_votes') or []
    # THE LAST POSITION EACH BOARD VOTED: to recommend, or to defer its recommendation to
    # Town Meeting -- both are a position, and the second is common.
    # The latest meeting at which the board took a position; at that meeting the TOWN'S
    # minutes outrank our notes, so a line upgrades by itself the day official minutes are
    # read (THREADS-MODEL §18), whatever order the two records arrive in.
    def position(slug):
        vs = [v for v in bv if v['board_slug'] == slug and event_of(v['text']) in ('recommended', 'deferred')]
        return max(vs, key=lambda v: (v['date'], v['source'] == 'town'), default=None)
    fc_vote, sb_vote = position('finance-committee'), position('select-board')

    # A POSITION IS WRITTEN IN PLAIN WORDS, never as the note text: our notes are machine
    # captions and mishear figures ("$418,0056"; TJ, 21 October 2026, and rule 13). An amount
    # is shown only when the TOWN'S minutes print it; ours say where to hear it instead.
    MONEY = re.compile(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?(?![\d,])')

    def said(v):
        unan = re.search(r'unanim', v.get('outcome') or '', re.I)
        if event_of(v['text']) == 'recommended':
            word = 'Recommended' + (' unanimously' if unan else '')
            if re.search(r'\b(?:not|against|disapprov)', v['text'], re.I):
                word = 'Voted on a recommendation (see the record)'
        else:
            word = 'Voted%s to leave its recommendation to Town Meeting' % (' unanimously' if unan else '')
        amt = MONEY.search(v['text']) if v['source'] == 'town' else None
        when = plain_date(v['date'])
        return '%s%s (%s)' % (word, ', at %s' % amt.group(0) if amt else '',
                              'the town\'s minutes, %s' % when if v['source'] == 'town'
                              else 'our notes of the %s recording' % when)
    placed_vote = next((v for v in bv if v['board_slug'] == 'select-board' and event_of(v['text']) == 'placed'
                        and not re.search(r'\bfail', v.get('outcome') or '', re.I)), None)
    cite = lambda v: '%s, %s, %s' % ('the town\'s minutes' if v['source'] == 'town' else 'our minutes', v['board_slug'], v['date'])
    stage = ''
    if draft:
        stage = 'proposed'
    if placed_vote:
        stage = 'placed'
    if a['details_doc']:
        stage = 'on the warrant'
    if rec(a['fincom_printed']) or rec(a['sb_printed']) or fc_vote or sb_vote or (c and (c['fincom'] or c['select_board'])):
        stage = 'recommended' if stage or a['details_doc'] else 'recommended'
    result, result_basis, result_ref, result_quote, result_amount = '', '', '', '', ''
    if c:
        result, result_basis = outcome_word(c['result']), 'official'
        result_ref = '%s p.%s' % (c['source_doc'], c['page'])
        result_quote, result_amount = c['quote'], c['amount_as_printed']
    elif o and o['main']:
        result, result_basis = our_result(o['main']), 'ours'
        result_ref = o['main']['video_url'] + ('&t=%ss' % o['main']['t'] if o['main'].get('t') is not None else '')
        result_quote = o['main']['motion']
    if result:
        stage = 'voted'
    if c:
        stage = 'recorded'
    title = a['title'] or (c['subject'] if c else '')
    title_from = a['title_from'] or ('the Town Clerk\'s record' if c and c['subject'] else '')
    if not title and a['warrant_words']:
        t = re.sub(r'^to\s+see\s+if\s+the\s+town\s+(?:will|would)\s+vote\s+(?:to\s+)?', '', a['warrant_words'], flags=re.I)
        title = t.split(';')[0][:110]
        title_from = 'the warrant\'s words'
    if not title and o and o['main']:
        title, title_from = o['main']['motion'][:110], 'our minutes, as heard'
    if not title and bv:
        title, title_from = vote_subject(bv[0]['text'])[:110], 'the Select Board\'s vote, as recorded'
    # KEPT OFF: the board voted on putting it on the warrant, and the vote failed. "Include
    # Article 6 ... (to vote it down)" -- failed 0-5 -- is an article the board declined.
    kept_off = [v for v in bv if v['board_slug'] == 'select-board' and event_of(v['text']) == 'placed'
                and re.search(r'\bfail', v.get('outcome') or '', re.I)]
    if kept_off and not a['details_doc'] and not result:
        stage = 'kept off'
    amended = (c and c['result'] == 'amended_and_passed') or (o and (o.get('amended') or o.get('amend_tried')))
    divided = (c and clerk_divided(c)) or (o and o.get('divided'))
    # PASSED OVER IS NOT PUT OFF. An article passed over is usually one with nothing to do --
    # a budget adjustment nobody needed. Postponed, tabled or referred is a decision deferred.
    put_off = (c and c['result'] == 'indefinitely_postponed') or (o and o.get('put_off'))
    return {
        'meeting': m['id'], 'article': '' if isinstance(n, str) else n, 'title': squash(title), 'title_from': title_from,
        'warrant_words': a['warrant_words'], 'amount': a['amount'], 'sponsor': a['sponsor'],
        'details_doc': a['details_doc'], 'details_town_url': a['details_town_url'],
        'details_page': a['details_page'],
        'stage': stage,
        'proposed_ref': ('%s, %s as article %s' % (draft['file'], draft['draft'], draft['letter'])) if draft else
                        (cite(placed_vote) if placed_vote else ''),
        'placed_ref': ('%s p.%s' % (a['details_doc'], a['details_page'])) if a['details_doc'] else
                      (cite(placed_vote) if placed_vote else ''),
        'fincom_rec': a['fincom_printed'] or (c['fincom'] if c else '') or (said(fc_vote) if fc_vote else ''),
        'fincom_ref': ('%s p.%s' % (a['details_doc'], a['details_page'])) if a['fincom_printed'] else
                      ('%s p.%s' % (c['source_doc'], c['page'])) if c and c['fincom'] else cite(fc_vote) if fc_vote else '',
        'sb_rec': a['sb_printed'] or (c['select_board'] if c else '') or (said(sb_vote) if sb_vote else ''),
        'sb_ref': ('%s p.%s' % (a['details_doc'], a['details_page'])) if a['sb_printed'] else
                  ('%s p.%s' % (c['source_doc'], c['page'])) if c and c['select_board'] else cite(sb_vote) if sb_vote else '',
        'result': result, 'result_basis': result_basis, 'result_ref': result_ref,
        'result_amount': result_amount, 'result_quote': squash(result_quote)[:400],
        'recorded_ref': ('%s p.%s' % (c['source_doc'], c['page'])) if c else '',
        'amended': 'yes' if amended else '', 'divided': 'yes' if divided else '',
        'put_off': 'yes' if put_off else '',
        'numbered_by': 'a board vote before the warrant was posted; the warrant may renumber it' if a.get('provisional') else '',
        'promoted': '', 'promoted_why': '', 'thread': '',
    }


# =========================================================================================
# 5. ASSIGN THE BOARDS' ITEMS TO A MEETING, and build the timeline each thread shows.
# =========================================================================================

def assign(items, meetings, strict=False):
    """Each board item about a Town Meeting, to the meeting it is about: the one whose date
    it names, else the next one within ASSIGN_DAYS. STRICT, on the second pass: not before
    the meeting's own beginning -- two weeks before it was called or its warrant opened, where
    either is known -- so May's talk after the Annual is not filed under September's Special."""
    dates = sorted({m['date'] for m in meetings})
    by_date = collections.defaultdict(list)
    for m in meetings:
        by_date[m['date']].append(m)
    for it in items:
        if not about_town_meeting(it['text'] + ' ' + (it.get('quote') or '')):
            continue
        named = [iso(d) for d in DATE.finditer(it['text']) if iso(d) in by_date and iso(d) >= it['date']]
        target = named[0] if named else next((d for d in dates if d >= it['date']
                                              and (dt.date.fromisoformat(d) - dt.date.fromisoformat(it['date'])).days <= ASSIGN_DAYS), None)
        if not target:
            continue
        ms = by_date[target]
        k = KIND.search(it['text'])
        pick = next((m for m in ms if k and m['kind'] == k.group(1).lower()), ms[0])
        if strict and not named:
            began = min([x for x in (pick['called_on'], pick['warrant_opens']) if x] or [''])
            if began and it['date'] < (dt.date.fromisoformat(began) - dt.timedelta(days=14)).isoformat():
                it.pop('_meeting', None)
                continue
        it['_meeting'] = pick['id']
        it['_event'] = event_of(it['text'])


def warrant_dates_from_votes(meetings, items):
    """When the warrant opened and closed, from the Select Board's own votes, where no notice
    said so: "Open the Annual Town Meeting warrant on January 12, 2022 and close it on March
    21, 2022 at 4:00 PM". A date after "close" is the close; one after "open", the opening;
    "open the warrant tonight" opens it on the day of the vote."""
    by = {m['id']: m for m in meetings}
    for it in sorted(items, key=lambda i: i['date']):
        m = by.get(it.get('_meeting'))
        if not m or it['kind'] != 'vote' or it['board_slug'] != 'select-board':
            continue
        if re.search(r'\bfail', it.get('outcome') or '', re.I):
            continue
        ref = ('the town\'s minutes' if it['source'] == 'town' else 'our minutes') + ', Select Board, ' + it['date']
        t = it['text']
        if not re.search(r'\bwarrant\b', t, re.I):
            continue
        for d in DATE.finditer(t):
            before = t[max(0, d.start() - 45):d.start()].lower()
            if 'clos' in before and not m['warrant_closes']:
                m['warrant_closes'], m['warrant_closes_ref'] = iso(d), ref
            elif 'open' in before and 'clos' not in before and not m['warrant_opens']:
                m['warrant_opens'], m['warrant_opens_ref'] = iso(d), ref
        if re.search(r'\bopen\w*\s+the\s+warrant\s+tonight', t, re.I) and not m['warrant_opens']:
            m['warrant_opens'], m['warrant_opens_ref'] = it['date'], ref
        if EVENTS[0][1].search(t) and not m['called_on']:
            m['called_on'], m['called_ref'] = it['date'], ref


def timeline(m, items, record):
    """The meeting's life as a list of meetings, in the shape every thread page reads."""
    stops = collections.OrderedDict()
    for it in sorted((i for i in items if i.get('_meeting') == m['id'] and i['kind'] in ('vote', 'decision', 'topic')),
                     key=lambda i: (i['date'], i['board_slug'])):
        # A TOPIC IS ONLY THE WARRANT'S OWN BOARDS' -- the Select Board and the Finance Committee
        # discussing the warrant. Another board's topic that mentions Town Meeting in passing
        # ("will report to Town Meeting") is not a step in this meeting's life; its votes are.
        if it['kind'] == 'topic' and (it['board_slug'] not in ('select-board', 'finance-committee')
                                      or not re.search(r'warrant|town meeting', it['text'], re.I)):
            continue
        # ANOTHER BOARD'S LINE belongs here when it is about this warrant -- an article, the
        # warrant -- not when it mentions what some Town Meeting once did.
        if it['board_slug'] not in ('select-board', 'finance-committee') and not re.search(r'\barticle|\bwarrant', it['text'], re.I):
            continue
        key = (it['board_slug'], it['date'])
        s = stops.setdefault(key, {'board': it.get('board') or '', 'board_slug': it['board_slug'], 'date': it['date'], 'items': []})
        s['items'].append({k: it.get(k) for k in ('kind', 'text', 'outcome', 't', 'video_url', 'source', 'quote',
                                                   'recording_note', 'doc_url', 'town_url') if it.get(k) not in (None, '')} |
                          {'kind': it['kind'], 'text': it['text'], 'outcome': it.get('outcome') or '',
                           't': it.get('t'), 'video_url': it.get('video_url') or '', 'source': it.get('source') or 'ours'})
    rec = record.get(('town-meeting', m['date']))
    if rec:
        stops[('town-meeting', m['date'])] = {
            'board': 'Town Meeting', 'board_slug': 'town-meeting', 'date': m['date'],
            'items': [{'kind': 'vote', 'text': v['motion'], 'outcome': v['outcome'], 't': v['t'],
                       'video_url': v['video_url'], 'source': 'ours', 'recording_note': v.get('recording_note') or ''}
                      for v in rec['votes'] if not v['procedural']]}
    out = list(stops.values())
    for s in out:
        s['records'] = sorted({i['source'] for i in s['items']})
    out.sort(key=lambda c: (c['date'], c['board_slug']))
    return out


# =========================================================================================
# 6. PROMOTION, and the child threads.
# =========================================================================================

ROUTINE = re.compile(r'\b(?:recommend|support|place|include|insert|on the warrant|in the warrant|'
                     r'approve the warrant|defer|refer|hearing)\w*', re.I)
GENERIC = set('budget school schools town select board committee meeting special annual capital plan '
              'department public general bylaw bylaws code chapter section amend amendment amending '
              'expenses expense prior pay payment reports officers committees revolving spending limits '
              'limit borrow anticipation revenue reimbursement state highway assistance omnibus '
              'adjustments closeouts operating program funding new existing establish accept provisions '
              'massachusetts general laws section purpose purposes cost costs services service '
              'lunenburg main street road building buildings water sewer enterprise free cash '
              'stabilization override proposition contingent upon approval question place include '
              'warrant article articles inclusion insert motion move'.split())


def keywords(row, df, n_docs):
    """THE ARTICLE'S SUBJECT, as two words that must both appear: the two rarest words of its
    TITLE that every board's record uses at least three times. Never the warrant's legal words
    -- "subsection", "entitled", "operate" are rare and say nothing about the subject -- and
    never one word alone: "OPEB" alone matched every board that mentioned retiree benefits.
    Two words, or none, and an article with none is followed by its number instead."""
    words = norm_words(row['title']) - GENERIC
    cand = sorted((df.get(w, 0), w) for w in words if 3 <= df.get(w, 0) <= KW_MAX_DF and len(w) >= 4)
    return [w for _, w in cand[:2]] if len(cand) >= 2 else []


def promote(articles, meetings, record, town, hand, items):
    import build_threads as BT
    texts = [v['motion'] for r in record.values() for v in r['votes']] + \
            [i['text'] for r in record.values() for i in r['items']] + \
            [i['text'] + ' ' + i['quote'] for r in town.values() for i in r['items']]
    df = collections.Counter()
    for t in texts:
        for w in set(re.findall(r'[a-z]{4,}', t.lower())):
            df[w] += 1
    by_id = {m['id']: m for m in meetings}
    # every board item that names an article of a meeting by its number, after assign()
    named = collections.defaultdict(list)
    for it in items:
        if it.get('_meeting'):
            for n in set(art_numbers(it['text'])):
                named[(it['_meeting'], n)].append(it)
    children = []
    for a in articles:
        m = by_id[a['meeting']]
        start = m['_start']
        kw = keywords(a, df, len(texts))
        a['_kw'], a['_start'] = kw, start
        why = []
        # WHERE IT CAME UP: the meetings its own words reach, and the meetings that named it
        # by number while it was on this warrant. A board's routine vote does not count.
        stops = {}
        if kw:
            t = {'id': '', 'match': r'\b%s' % re.escape(kw[0]), 'qualify': (r'\b%s' % re.escape(kw[1])) if len(kw) > 1 else '',
                 'exclude': '', 'boards': '', 'started': start}
            # only the window: the matcher reads every meeting it is handed
            rw = {k: v for k, v in record.items() if start <= k[1] <= m['date']}
            tw = {k: v for k, v in town.items() if start <= k[1] <= m['date']}
            for c in BT.chronology(t, rw, tw):
                if c['board_slug'] != 'town-meeting':
                    stops.setdefault((c['board_slug'], c['date']), []).extend(c['items'])
        if a['article'] != '':
            for it in named.get((m['id'], a['article']), []):
                stops.setdefault((it['board_slug'], it['date']), []).append(it)
        # THE ROUTINE STOPS COME OFF FIRST: the first ROUTINE_PER_BOARD meetings of the Select
        # Board and of the Finance Committee, and any meeting where the only mention was a
        # routine vote (to place it, recommend it, defer it).
        real = sorted(k for k, its in stops.items() if any(not (i['kind'] == 'vote' and ROUTINE.search(i['text'])) for i in its))
        seen = collections.Counter()
        beyond = []
        for k in real:
            if k[0] in ROUTINE_BOARDS and seen[k[0]] < ROUTINE_PER_BOARD:
                seen[k[0]] += 1
                continue
            beyond.append(k)
        boards = {k[0] for k in stops}
        if len(beyond) >= PROMOTE_MEETINGS and len(boards) >= PROMOTE_BOARDS:
            why.append('came up at %d meetings of %d boards beyond the routine stops' % (len(beyond), len(boards)))
        heard = {k for k, its in stops.items() if any(i['kind'] in ('comment', 'contention') for i in its)}
        if heard:
            why.append('residents spoke about it, or a dispute was recorded, at %d meeting%s' % (len(heard), '' if len(heard) == 1 else 's'))
        if a['amended']:
            why.append('Town Meeting took up an amendment')
        if a['divided']:
            why.append('Town Meeting divided on it')
        if a['put_off']:
            why.append('Town Meeting postponed or referred it')
        a['_stops'] = len(stops)
        # AN EXISTING THREAD THAT ALREADY FOLLOWS IT is linked, never duplicated -- promoted or
        # not: one whose closure names this article, or, for a meeting still to come, an open
        # thread whose own words match the article's.
        words = a['title'] + ' ' + a['warrant_words']
        own = next((h for h in hand if h.get('closed_board') == 'town-meeting' and h.get('closed_date') == m['date']
                    and re.sub(r'\D', '', h.get('closed_article') or '') == str(a['article'])), None) or \
            next((h for h in hand if h['status'] == 'open' and m['status'] == 'upcoming' and h.get('match')
                  and re.search(h['match'], words, re.I)
                  and (not h.get('qualify') or re.search(h['qualify'], words, re.I))
                  and not (h.get('exclude') and re.search(h['exclude'], words, re.I))), None)
        if own:
            a['thread'] = own['id']
        if not why:
            continue
        a['promoted'], a['promoted_why'] = 'yes', '; '.join(why)
        if own:
            continue
        if not kw:
            a['promoted_why'] += '; its title is too general to follow by its words, so its record is in this meeting\'s timeline'
            continue
        cid = '%s-article-%s' % (m['id'], a['article'] if a['article'] != '' else
                                 re.sub(r'[^a-z0-9]+', '-', a['title'].lower()).strip('-')[:40])
        a['thread'] = cid
        children.append({'id': cid, 'parent': m['id'], 'article': a['article'], 'kw': kw, 'start': start, 'row': a})
    return children


# =========================================================================================
# 7. THE THREAD ROWS, in the registry's own columns, and the status board.
# =========================================================================================

STAGE_WORD = {'proposed': 'Proposed', 'placed': 'Placed on the warrant', 'kept off': 'Kept off the warrant',
              'on the warrant': 'On the warrant', 'recommended': 'Recommended',
              'voted': 'Voted', 'recorded': 'Voted'}


def pretty(d):
    x = dt.date.fromisoformat(d)
    return '%s %d, %d' % (x.strftime('%B'), x.day, x.year)


def thread_rows(meetings, articles, children, items, record):
    by_m = collections.defaultdict(list)
    for a in articles:
        by_m[a['meeting']].append(a)
    out = []
    for m in meetings:
        if m['status'] == 'called; no later record':
            continue
        arts = by_m[m['id']]
        name = '%s Town Meeting, %s' % (m['kind'].title(), pretty(m['date']))
        voted = [a for a in arts if a['result']]
        top = max((a['article'] for a in arts if a['article'] != ''), default=None)
        # THE MEETING IS OVER WHEN IT HAS MET. Its closure cites the last article we hold a vote
        # for; where that is not the warrant's last, the caveat says so rather than the thread
        # waiting forever on a vote the Clerk's extract did not carry.
        last = max((a for a in arts if a['article'] != '' and a['result']), key=lambda a: a['article'], default=None)
        closed = m['status'] == 'held' and last is not None
        closure = closure_of(last, m) if closed else None
        status = 'resolved' if closed else 'open' if m['status'] == 'upcoming' or arts else 'open'
        if m['status'] == 'held' and not closed:
            status = 'held'
        thin = []
        if not m['warrant_doc']:
            thin.append('we do not hold the warrant for this meeting' if m['status'] == 'held'
                        else 'the warrant has not been posted yet; the articles listed are the ones the Select Board has numbered at its meetings, and the final warrant may renumber them')
        if m['status'] == 'held' and not voted:
            thin.append('we hold no record of how Town Meeting voted')
        if closed and top is not None and last['article'] != top:
            thin.append('the last article we hold a vote for is article %s; the warrant runs to article %s'
                        % (last['article'], top))
        if m['kind_basis'].startswith('by the month'):
            thin.append('nothing we hold says whether this was the Annual or a Special Town Meeting; we filed it by its month')
        out.append({
            'id': m['id'], 'label': name,
            'question': 'Every article on the warrant, and where each one stands.',
            'kind': 'town-meeting', 'groups': 'how-the-town-runs', 'tags': '',
            'boards': 'town-meeting', 'registered_on': m['first_signal'], 'started': m['_start'],
            'closes': 'Town Meeting votes the last article on the warrant',
            'status': status, 'resolved_on': m['date'] if closed else '',
            'caveat': ('. '.join(t[0].upper() + t[1:] for t in thin) + '.') if thin else '',
            'generated': 'town-meetings', 'closure': closure,
            'chronology': timeline(m, items, record),
            'warrant': warrant_payload(m, arts, children, items),
        })
    for c in children:
        a = c['row']
        out.append({
            'id': c['id'], 'label': ('Article %s: %s' % (a['article'], plain_title(a['title'])[:80])) if a['article'] != '' else plain_title(a['title'])[:90],
            'question': 'What happened to %s before and at the %s?' % (('article %s' % a['article']) if a['article'] != '' else 'this article',
                                                                       name_of(c['parent'], meetings)),
            'kind': 'town-meeting', 'groups': 'how-the-town-runs', 'tags': '', 'boards': '',
            'registered_on': c['start'], 'started': c['start'],
            'match': r'\b%s' % re.escape(c['kw'][0]), 'qualify': (r'\b%s' % re.escape(c['kw'][1])) if len(c['kw']) > 1 else '',
            'exclude': '', 'until': c['parent'].split('-', 1)[1],
            'closed_board': 'town-meeting', 'closed_date': c['parent'].split('-', 1)[1],
            'closed_article': str(a['article']), 'closed_match': '',
            'closes': 'Town Meeting votes %s' % (('article %s' % a['article']) if a['article'] != '' else 'the article'),
            # AN ARTICLE OF A MEETING THAT HAS MET IS NOT OPEN. With no vote in what we hold it is
            # `held`: the meeting happened, and the record we can read does not say what it did.
            'status': 'resolved' if a['result'] else 'open' if next(x for x in meetings if x['id'] == c['parent'])['status'] == 'upcoming' else 'held',
            'resolved_on': c['parent'].split('-', 1)[1] if a['result'] else '',
            'caveat': 'Followed by the words "%s" -- a meeting that discussed it in other words is missing.'
                      % '" and "'.join(c['kw']),
            'generated': 'town-meetings', 'parent': c['parent'],
            'promoted_why': a['promoted_why'],
            'closure': closure_of(a, next(x for x in meetings if x['id'] == c['parent'])) if a['result'] else None,
        })
    return out


def closure_of(a, m):
    """A closure in the shape build_threads.resolve_closure() returns: the Clerk's record when
    it exists, our minutes otherwise -- and it upgrades the day the Clerk's year is read, because
    warrant-articles.csv takes the Clerk first on every run."""
    doc, _, page = a['result_ref'].partition(' p.')
    return {'basis': a['result_basis'],
            'source': 'the Town Clerk, printed in the annual town report' if a['result_basis'] == 'official'
            else 'our minutes of the recording, from machine captions',
            'meeting': 'Town Meeting', 'date': m['date'], 'article': str(a['article']),
            'result': a['result'], 'amount_as_printed': a['result_amount'],
            'quote': a['result_quote'], 'fincom': a['fincom_rec'] if a['result_basis'] == 'official' else '',
            'select_board': a['sb_rec'] if a['result_basis'] == 'official' else '',
            'document': doc, 'page': page,
            'caveat': '' if a['result_basis'] == 'official' else
            'AS HEARD from machine captions. A caption model hears "fifteen hundred", "$1,500" and "$50" alike; '
            'check the recording at the second cited. This upgrades to the Town Clerk\'s printed record when '
            'that year\'s annual report is extracted.'}


ACRONYMS = set('FY PEG OPEB SAP ADA MBTA DPW CPA EDC COA MGL II III LMHS TC PACC MART IBPO AFSCME STM ATM BTFC APDC US MSBA LED'.split())


PROPER = {'lunenburg', 'massachusetts', 'whalom', 'passios', 'ritter', 'brooks', 'marshall', 'fitchburg', 'montachusett', 'chapter'}


def plain_title(s):
    """A warrant's capitals in sentence case, keeping acronyms and anything with a figure --
    the same rule as plainTitle() in fy28/src/components/TownMeetingBoard.tsx."""
    letters = re.sub(r'[^A-Za-z]', '', s)
    if not letters or sum(c.isupper() for c in letters) < len(letters) * .7:
        return s
    out = re.sub(r"[a-z0-9\u2019'.]+", lambda m: m.group(0).upper()
                 if re.sub(r"[\u2019'.]", '', m.group(0).upper()) in ACRONYMS or re.search(r'\d', m.group(0))
                 else m.group(0).capitalize() if m.group(0) in PROPER else m.group(0), s.lower())
    return out[:1].upper() + out[1:]


def name_of(mid, meetings):
    m = next(x for x in meetings if x['id'] == mid)
    return '%s Town Meeting of %s' % (m['kind'].title(), pretty(m['date']))


def notice_when_where(m):
    """The time and place the legal notice prints -- "Tuesday, November 17, 2026 at 7:00 PM at
    the Lunenburg Middle/High School Auditorium" -- read off the notice, never typed (rule 2).
    Empty when the notice does not say it in that shape."""
    if not m.get('notice_doc'):
        return '', ''
    t = os.path.join(ROOT, 'sources', 'meetings', 'text',
                     re.sub(r'^sources/meetings/', '', m['notice_doc'])[:-4] + '.txt')
    if not os.path.exists(t):
        return '', ''
    x = squash(open(t, encoding='utf-8', errors='replace').read())
    k = re.search(r'\bat\s+(\d{1,2}:\d{2}\s*[AP]\.?\s*M\.?)\s+(?:in|at)\s+the\s+([^.]{4,90}?)\s*\.', x, re.I)
    return (re.sub(r'\s+', ' ', k.group(1)).upper().replace('.', ''), k.group(2).strip()) if k else ('', '')


def next_steps(m, items=()):
    """WHAT HAPPENS NEXT, for a meeting still to come: every POSTED agenda, any board, dated
    from today until the meeting, whose text is about a Town Meeting (about_town_meeting, so
    a bill warrant is not one). Read off the agendas the town has posted; nothing predicted.
    TJ, 21 October 2026: the dates a resident can act on were buried in the timeline."""
    if m['status'] != 'upcoming':
        return []
    today = dt.date.today().isoformat()
    out = []
    for r in csv.DictReader(open(os.path.join(ROOT, 'sources', 'meetings', 'index.csv'), encoding='utf-8')):
        if r['kind'] != 'agenda' or not (today <= r['date'] < m['date']):
            continue
        t = os.path.join(ROOT, 'sources', 'meetings', 'text', r['path'][:-4] + '.txt')
        if not os.path.exists(t):
            continue
        x = open(t, encoding='utf-8', errors='replace').read()
        lines = [squash(l) for l in x.splitlines() if about_town_meeting(l) and len(squash(l)) > 6]
        if not lines:
            continue
        when = re.search(r'\b(\d{1,2}:\d{2}\s*[AP]\.?\s*M)', x, re.I)
        out.append({'date': r['date'], 'board': r['board'],
                    'time': re.sub(r'\s+', ' ', when.group(1)).upper().replace('.', '') if when else '',
                    'hearing': bool(re.search(r'public\s+hearing', x, re.I)),
                    'item': re.sub(r'^[a-z0-9]{1,3}[.)]\s*', '', lines[0], flags=re.I)[:120],
                    'doc': '/docs/meetings/' + r['path'], 'town_url': r['url']})
    # ANNOUNCED, NOT YET POSTED: a decision at a board's recent meeting that names a coming
    # date for this warrant ("Board will make recommendations on all warrant articles at the
    # October 27 meeting"). Ours, from the recording, and labelled so; dropped once an agenda
    # for that board and date is posted, since the agenda then says it.
    posted = {(o['board'], o['date']) for o in out}
    year = m['date'][:4]
    for it in items:
        if it['kind'] != 'decision' or it['date'] < (dt.date.today() - dt.timedelta(days=45)).isoformat():
            continue
        if not (about_town_meeting(it['text']) or re.search(r'\bwarrant\b', it['text'], re.I)):
            continue
        for k in re.finditer(r'\b(%s)\s+(\d{1,2})\b' % '|'.join(MONTHS), it['text'], re.I):
            d = iso(DATE.search('%s %s, %s' % (k.group(1), k.group(2), year)))
            if d and today <= d < m['date'] and (it['board'], d) not in posted:
                out.append({'date': d, 'board': it['board'], 'time': '', 'hearing': False,
                            'item': it['text'][:160], 'announced': it['date'], 'source': it['source'],
                            'video_url': it.get('video_url') or '', 't': it.get('t')})
    return sorted(out, key=lambda o: (o['date'], o['time']))


HEARD = os.path.join(DATA, 'heard-figures.csv')


def heard_figures():
    """FIGURES A PERSON CHECKED IN THE RECORDING (sources/data/heard-figures.csv): our notes
    come from machine captions and mishear numbers, so a figure from a recording reaches an
    article row only after somebody listened at the second cited and wrote it down here, with
    who and when (TJ, 21 October 2026; rule 13). Matched to an article by its meeting and a
    pattern on the article's title -- a pattern that matches nothing is REFUSED, not ignored."""
    if not os.path.exists(HEARD):
        return []
    return list(csv.DictReader(open(HEARD, encoding='utf-8')))


SUMMARIES = os.path.join(DATA, 'article-summaries.json')


def summaries():
    """A sentence or two per article, written by scripts/write_article_summaries.py from the
    article's own record and checked there (no figure the warrant or a checked figure lacks).
    Keyed meeting|article|title, so a renumbered or reworded article simply has none until the
    next run writes it."""
    return json.load(open(SUMMARIES, encoding='utf-8')) if os.path.exists(SUMMARIES) else {}


def warrant_payload(m, arts, children, items=()):
    def money(a):
        vals = [float(re.sub(r'[^\d.]', '', x) or 0) for x in AMOUNT.findall(a['amount'] + ' ' + a['result_amount'])]
        return max(vals) if vals else 0
    rows = []
    summ = summaries()
    for a in arts:
        sm = summ.get('%s|%s|%s' % (m['id'], a['article'] if a['article'] != '' else '', a['title'].lower().strip()), {})
        rows.append({
            'summary': sm.get('summary', ''), 'summary_from': sm.get('from', '') if sm.get('summary') else '',
            'article': a['article'], 'title': a['title'], 'title_from': a['title_from'],
            'amount': a['amount'], 'sponsor': a['sponsor'],
            'stage': STAGE_WORD.get(a['stage'], ''),
            'fincom': a['fincom_rec'], 'select_board': a['sb_rec'],
            'result': a['result'], 'result_basis': a['result_basis'], 'result_amount': a['result_amount'],
            'result_ref': a['result_ref'],
            'details': ('/docs/' + a['details_doc'].replace('sources/', '', 1)) if a['details_doc'] else '',
            'details_town': a['details_town_url'], 'details_page': a['details_page'],
            'clerk_doc': ('/docs/' + a['recorded_ref'].split(' p.')[0].replace('sources/', '', 1).replace('/text/', '/docs/').replace('.txt', '.pdf')) if a['recorded_ref'] else '',
            'clerk_page': a['recorded_ref'].split(' p.')[1] if a['recorded_ref'] else '',
            'amended': bool(a['amended']), 'divided': bool(a['divided']), 'put_off': bool(a['put_off']),
            'promoted': bool(a['promoted']), 'promoted_why': a['promoted_why'], 'thread': a['thread'],
            'numbered_by': a['numbered_by'],
            'money': money(a),
            'heard': [{'figure': h['figure'], 'value': float(h['value']), 'what': h['what'], 'board': h['board'],
                       'date': h['date'], 'listen': '%s&t=%ss' % (h['video_url'], h['t']),
                       'verified_by': h['verified_by'], 'verified_on': h['verified_on'], 'note': h['note'],
                       'how': h.get('how') or 'heard'}
                      for h in heard_figures() if h['meeting'] == m['id']
                      and re.search(h['article_match'], a['title'], re.I)],
        })
    for h in heard_figures():
        if h['meeting'] == m['id'] and not any(re.search(h['article_match'], a['title'], re.I) for a in arts):
            raise SystemExit('REFUSING: heard figure %s (%r) matches no article of %s'
                             % (h['figure'], h['article_match'], m['id']))
    # MONEY OR DEBATE LEADS. A promoted article first, then the largest sum, then the number.
    # A HEARD FIGURE COUNTS AS MONEY FOR THE ORDER: the largest commitment leads.
    for r in rows:
        r['money'] = max([r['money']] + [h['value'] for h in r['heard']])
    rows.sort(key=lambda r: (not r['promoted'], -r['money'], r['article'] == '', r['article'] or 0))
    return {
        'meeting': m['id'], 'date': m['date'], 'kind': m['kind'], 'status': m['status'],
        'called_on': m['called_on'], 'warrant_opens': m['warrant_opens'], 'warrant_closes': m['warrant_closes'],
        'warrant_signed': m['warrant_signed'],
        'warrant_doc': ('/docs/' + m['warrant_doc'].replace('sources/', '', 1)) if m['warrant_doc'] else '',
        'warrant_town_url': m['warrant_town_url'],
        'notice_doc': ('/docs/' + m['notice_doc'].replace('sources/', '', 1)) if m['notice_doc'] else '',
        'notice_town_url': m['notice_town_url'],
        'time': notice_when_where(m)[0], 'place': notice_when_where(m)[1],
        'next': next_steps(m, items),
        # COUNTED HERE, so a post or a page quotes the board's own figure rather than typing one.
        'counts': {'on_warrant': sum(1 for r in rows if r['stage'] != 'Kept off the warrant'),
                   'kept_off': sum(1 for r in rows if r['stage'] == 'Kept off the warrant'),
                   'not_numbered': sum(1 for r in rows if r['article'] == '' and r['stage'] != 'Kept off the warrant')},
        'signals': m['signals'].split(';'),
        'rule': {'meetings': PROMOTE_MEETINGS, 'boards': PROMOTE_BOARDS, 'routine_per_board': ROUTINE_PER_BOARD,
                 'divided_share': DIVIDED_SHARE,
                 'text': 'An article gets its own thread when it came up at %d or more meetings, across at least %d '
                         'boards, beyond the routine stops every article gets (the Select Board and the Finance '
                         'Committee each take it up about %d times to place it and recommend it); when residents '
                         'spoke about it or a dispute about it was recorded; or when Town Meeting took up an '
                         'amendment, postponed it, or divided on it, with at least %d in 100 on the losing side. '
                         'Those thresholds are our choice, not the town\'s.'
                         % (PROMOTE_MEETINGS, PROMOTE_BOARDS, ROUTINE_PER_BOARD, round(DIVIDED_SHARE * 100))},
        'articles': rows,
    }


# =========================================================================================

MEETING_COLS = ['id', 'date', 'date_conflict', 'kind', 'kind_basis', 'status', 'signals', 'first_signal', 'first_signal_kind',
                'first_signal_ref', 'called_on', 'called_ref', 'warrant_opens', 'warrant_opens_ref', 'warrant_closes',
                'warrant_closes_ref', 'warrant_signed',
                'notice_doc', 'notice_town_url', 'warrant_doc', 'warrant_town_url', 'articles', 'articles_voted',
                'articles_clerk', 'thin']
ARTICLE_COLS = ['meeting', 'article', 'title', 'title_from', 'amount', 'sponsor', 'stage',
                'details_doc', 'details_page', 'details_town_url',
                'proposed_ref', 'placed_ref', 'fincom_rec', 'fincom_ref', 'sb_rec', 'sb_ref',
                'result', 'result_basis', 'result_amount', 'result_ref', 'result_quote', 'recorded_ref',
                'amended', 'divided', 'put_off', 'numbered_by', 'promoted', 'promoted_why', 'thread',
                'warrant_words']


def to_csv(rows, cols):
    b = io.StringIO()
    w = csv.DictWriter(b, fieldnames=cols, extrasaction='ignore', lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return b.getvalue()


def run():
    meetings, items, record, town, clerk, undated = build()
    # the drafts are keyed atm-YYYY-05; point each at the real May meeting
    assign(items, meetings)
    warrant_dates_from_votes(meetings, items)
    assign(items, meetings, strict=True)
    for m in meetings:
        # CALLED, AND NOTHING SINCE. A date only a Select Board vote ever named, now past, with no
        # notice, warrant, Clerk's record or recording: the 2016 Special was set for 8 August and
        # moved to 22 August. Registered, so the vote is not lost; given no thread.
        if m['status'] == 'held' and set(m['signals'].split(';')) <= {'sb-vote'}:
            m['status'] = 'called; no later record'
    for m in meetings:
        m['_start'] = min(x for x in (m['warrant_opens'], m['called_on'],
                                      (dt.date.fromisoformat(m['date']) - dt.timedelta(days=LOOKBACK_DAYS)).isoformat()) if x)
    articles, unmatched, report = build_articles(meetings, items, record, clerk)
    hand = read_csv(os.path.join(DATA, 'threads.csv'))
    children = promote(articles, meetings, record, town, hand, items)
    by_m = collections.Counter(a['meeting'] for a in articles)
    voted = collections.Counter(a['meeting'] for a in articles if a['result'])
    ck = collections.Counter(a['meeting'] for a in articles if a['recorded_ref'])
    for m in meetings:
        m['articles'], m['articles_voted'], m['articles_clerk'] = by_m[m['id']], voted[m['id']], ck[m['id']]
        m['thin'] = '; '.join(x for x in (
            '' if m['warrant_doc'] else 'no warrant held',
            '' if voted[m['id']] or m['status'] == 'upcoming' else 'no votes held') if x)
    threads = thread_rows(meetings, articles, children, items, record)
    payload = {'about': 'Generated by scripts/build_town_meetings.py -- never edit by hand. build_threads.py '
                        'merges these into threads.json beside the hand registry, sources/data/threads.csv.',
               'rule': {'promote_meetings': PROMOTE_MEETINGS, 'lookback_days': LOOKBACK_DAYS, 'assign_days': ASSIGN_DAYS},
               'threads': threads}
    return meetings, articles, unmatched, report, payload, undated


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    meetings, articles, unmatched, report, payload, undated = run()
    outs = {OUT_MEETINGS: to_csv(meetings, MEETING_COLS),
            OUT_ARTICLES: to_csv(sorted(articles, key=lambda r: (r['meeting'][4:], r['meeting'], r['article'] == '',
                                                                 r['article'] or 0, r['title'])), ARTICLE_COLS),
            OUT_THREADS: json.dumps(payload, indent=1, ensure_ascii=False) + '\n'}
    if a.check:
        stale = [p for p, body in outs.items()
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != body]
        if stale:
            raise SystemExit('STALE: %s -- run build_town_meetings.py' % ', '.join(os.path.relpath(p, ROOT) for p in stale))
        print('ok -- %d meetings, %d articles, %d threads' % (len(meetings), len(articles), len(payload['threads'])))
        return
    for p, body in outs.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + '.tmp'
        open(tmp, 'w', encoding='utf-8').write(body)
        os.replace(tmp, p)
    print('wrote %d meetings, %d articles, %d threads (%d articles promoted)'
          % (len(meetings), len(articles), len(payload['threads']), sum(1 for x in articles if x['promoted'])))
    for m in meetings:
        r = report.get(m['id'], {})
        print('  %-16s %-8s signals=%-40s warrant=%-3s parsed=%-3s numbered=%-3s clerk=%-3s ours=%-3s first=%s %s %s'
              % (m['id'], m['status'], m['signals'], 'yes' if m['warrant_doc'] else '-', r.get('parsed'),
                 r.get('numbered_to'), r.get('clerk'), r.get('ours'), m['first_signal'], m['first_signal_kind'],
                 '; '.join(r.get('notes', []))))
    if unmatched:
        print('DRAFTS NOT MATCHED to a final article (%d):' % len(unmatched))
        for mid, d in unmatched:
            print('  %s  draft %s %s: %s' % (mid, d['draft'], d['letter'], d['title'][:80]))


if __name__ == '__main__':
    main()
