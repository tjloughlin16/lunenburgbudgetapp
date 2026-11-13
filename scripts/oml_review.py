#!/usr/bin/env python3
"""OPEN MEETING LAW: POINTS TO CHECK, for one meeting. Experimental, one-off, unlisted.

    python3 scripts/oml_review.py school-committee 2026-07-29            # one meeting (one paid call)
    python3 scripts/oml_review.py school-committee 2026-07-29 --dry-run  # inputs and size, no call
    python3 scripts/oml_review.py --check                                # every review still holds

TJ, 8 October 2026: compare the town's minutes AND the recording against the Open Meeting
Law -- notice, what was on the agenda, how votes were taken, how discussion was had -- one
meeting at a time, on a page nobody is sent to.

WHAT IT READS, all of it already in this repository:

  * the meeting register row, and the agenda PDF's own creation time
    (meeting-document-timestamps.csv) -- the earliest moment THIS FILE could have been
    posted. Not the posting time: nothing we hold records that;
  * the posted agenda's text, and the town's minutes' text -- the record;
  * the town's minutes read structured (official-votes) and our minutes of the recording
    (recording-minutes) -- both DERIVED, given to the model as an index and never quotable;
  * the machine captions of the recording -- a FINDING AID: quotable only as the video at
    its second, and labelled so;
  * the law: G.L. c.30A §§18-24 as the Legislature publishes them, 940 CMR 29.00, and the
    Attorney General's checklists and remote-participation guidance
    (fetch_open_meeting_law.py).

WHAT THE SCRIPT DECIDES, AND WHAT THE MODEL DOES. The notice arithmetic -- hours between
the agenda file's creation and the meeting, excluding Saturdays, Sundays and legal holidays
-- is computed here, not by the model, and handed to it as a fact with its limits. The
model (sonnet, `claude -p --json-schema`, no tools) reads the rest and returns findings.

EVERY FINDING CARRIES, AND IS DROPPED WITHOUT:

  * the rule, quoted from the law text, with its section -- checked VERBATIM against the
    held law (oml_law.verbatim);
  * the evidence, quoted from the agenda, the minutes or the captions -- each checked
    VERBATIM against its source text, the caption quote re-anchored to the second its words
    actually start at;
  * a status, exactly one of `clear from the record`, `possible — needs checking`,
    `cannot tell from what is published`.

A finding with ANY quote that is not verbatim is dropped and counted, as
extract_official_votes.py drops an unquoted vote. The word the law uses for a breach does
not appear in our output except inside a quotation of the law: only the Attorney General's
office determines that, and the page says so.
"""
import argparse
import csv
import datetime as dt
import glob
import hashlib
import json
import math
import os
import re
import subprocess
import claude_lean
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oml_law as L  # noqa: E402

ROOT = os.path.dirname(HERE)
REGISTER = os.path.join(ROOT, 'sources', 'data', 'meeting-register.csv')
STAMPS = os.path.join(ROOT, 'sources', 'data', 'meeting-document-timestamps.csv')
MEET = os.path.join(ROOT, 'sources', 'meetings')
TEXT = os.path.join(MEET, 'text')
OUT = os.environ.get('OML_OUT') or os.path.join(ROOT, 'sources', 'data', 'oml-reviews')
PUB = os.path.join(ROOT, 'fy28', 'public', 'data', 'oml')
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
# OML_MODEL / OML_OUT: a pilot on another model writes beside, never over, the held reviews,
# and publishes nothing (12 November 2026, the Haiku pilot).
MODEL = os.environ.get('OML_MODEL', 'sonnet')
TIMEOUT = 900
SITE = 'https://lunenburgbudgetproject.org'

# ESCALATION (13 November 2026). TJ: the one call "needs to flag if an agentic review should be
# kicked off for it" -- and "if that's a high percentage... then it means we need an agentic loop
# to begin". So every point says whether it needs one, and every review records the rate.
ESCALATE_REASONS = ['none', 'no fitting precedent', 'record conflicts', 'needs another document',
                    'judgement on the facts']
ESCALATION_RATE_LINE = 0.33   # above this across a batch, the review itself should start agentic
STATUSES = ['clear from the record', 'possible — needs checking', 'cannot tell from what is published']
CRITERIA = ['notice', 'agenda topics', 'votes', 'executive session', 'minutes',
            'remote participation', 'public access', 'other']
# The law handed to the model, and the only documents a rule may be quoted from. The guide
# (136 KB) is left out for size; its checklists carry its operative lines.
LAW_IN_PROMPT = ['c30a-18', 'c30a-20', 'c30a-21', 'c30a-22', 'c30a-23', '940-cmr-29',
                 'oml-notice-checklist', 'oml-minutes-checklist', 'oml-executive-session-checklist',
                 'oml-chair-checklist', 'remote-participation-guidance',
                 # AG DETERMINATIONS on how specific a topic must be, and on acronyms (8 Oct 2026,
                 # TJ: "Are the acronyms used a violation?" -- "Or you can find the AG
                 # determinations"). See sources/state-law/notes/acronyms-in-agendas.md.
                 'oml-det-2026-99', 'oml-det-2018-56', 'oml-det-2024-218', 'oml-det-2015-148',
                 'oml-det-2015-127', 'oml-det-2014-125']

# THE PRECEDENT PACK (13 November 2026): the leading AG determinations per issue, built
# model-free by build_oml_leading_rulings.py from the 2,909 digests. Handed to the model with
# each ruling's key passage; a finding may cite up to two, each quote checked verbatim against
# the letter. A ruling is how the AG read the law for ANOTHER body on other facts.
LEADING = os.path.join(ROOT, 'sources', 'data', 'oml-leading-rulings.json')


def leading_rulings():
    return json.load(open(LEADING, encoding='utf-8')) if os.path.exists(LEADING) else {'issues': {}}


def precedent_ids():
    ids = {r['id'] for v in leading_rulings()['issues'].values() for r in v['rulings']}
    return sorted(ids | {i for i in LAW_IN_PROMPT if i.startswith('oml-det-')})


def precedent_holding(det_id, quote):
    """WHICH holding a quoted passage belongs to. One letter decides many allegations -- OML
    2013-195 holds 26 times, both ways -- so a letter has no single holding. Taken from the
    digest allegation whose key passage overlaps the quote; when none does, the holding is left
    blank and the page says to read the letter, rather than borrowing another allegation's
    (the first pilot did that, 13 Nov 2026, and labelled a violation `no violation`)."""
    m = re.match(r'oml-det-(\d{4})-', det_id)
    p = os.path.join(ROOT, 'sources', 'data', 'oml-determinations', m.group(1) if m else '', det_id + '.json')
    if not os.path.exists(p):
        return {'number': '', 'public_body': '', 'holding': '', 'issue': ''}
    d = json.load(open(p, encoding='utf-8'))
    q = L.squash(quote)
    for a in d.get('allegations') or []:
        k = L.squash(a.get('key_passage') or '')
        if len(k) >= 20 and (k in q or q in k):
            return {'number': d['number'], 'public_body': d['public_body'], 'holding': a['holding'],
                    'issue': a['issue']}
    return {'number': d['number'], 'public_body': d['public_body'], 'holding': '', 'issue': '',
            'holding_note': 'the quoted words are not one of the digest\'s key passages; read the letter for the holding'}


# WHAT STANDS OUT (13 November 2026). TJ: the top one or two points "should POP", ranked by
# how much precedent stands behind them -- by a score that is NOT shown on the page. The
# score is ours and model-free; the page shows only the facts it rests on (how often the AG
# has ruled against a board on that issue, and where the rule is written), never the word
# the law uses for a breach.
ISSUES = ['notice timing', 'notice content / topic specificity', 'acronyms and jargon',
          'discussion beyond the notice', 'votes and roll calls', 'executive session: purpose',
          'executive session: procedure', 'executive session minutes', 'open session minutes',
          'release of minutes', 'remote participation', 'public access and recording', 'public comment',
          'other']
STATUS_W = {'clear from the record': 1.0, 'possible — needs checking': 0.6,
            'cannot tell from what is published': 0.25}
# SERIOUSNESS, per issue -- OURS, a judgement, and never shown. TJ, 13 November 2026, wanted
# what is "huge and important" to lead, and precedent alone puts minutes first on nearly every
# page (boards lose ~56% of 694 minutes letters). So business done out of public view -- an
# executive session, a vote, the notice the public relies on -- outranks record-keeping.
SERIOUSNESS = {
    'executive session: purpose': 1.0, 'executive session: procedure': 1.0,
    'votes and roll calls': 0.95, 'notice timing': 0.9, 'notice content / topic specificity': 0.85,
    'public access and recording': 0.85, 'discussion beyond the notice': 0.8,
    'executive session minutes': 0.75, 'release of minutes': 0.7, 'remote participation': 0.7,
    'open session minutes': 0.6, 'acronyms and jargon': 0.6, 'public comment': 0.5, 'other': 0.5,
}
STANDOUT_MIN = 0.18   # below this a point does not lead the page, however it ranks
STANDOUT_MAX = 2


def finding_issue(f):
    """The issue a point is about: the model's tag when it gave one, else read off the criterion
    and title (reviews written before the tag), else the issue of the AG passage it quoted."""
    if f.get('issue') in ISSUES:
        return f['issue']
    # The TITLE only: a summary mentions everything nearby ("the minutes record a vote to enter
    # executive session"), and reading it labelled an entry-purpose point as minutes.
    t = f['title'].lower()
    c = f['criterion']
    if c == 'notice':
        return 'notice timing' if ('hour' in t or f.get('by') == 'script') else 'notice content / topic specificity'
    if c == 'agenda topics':
        if 'acronym' in t or 'abbreviat' in t or 'jargon' in t:
            return 'acronyms and jargon'
        if 'public comment' in t:
            return 'public comment'
        return 'discussion beyond the notice'
    if c == 'executive session':
        if 'minutes' in t and 'purpose' not in t:
            return 'executive session minutes'
        if 'purpose' in t:
            return 'executive session: purpose'
        return 'executive session: procedure'
    if c == 'minutes' and 'executive session minutes' in t:
        return 'executive session minutes'
    got = {'votes': 'votes and roll calls', 'minutes': 'open session minutes',
           'remote participation': 'remote participation',
           'public access': 'public access and recording'}.get(c)
    if got:
        return got
    # Last, the issue of the AG passage it quoted: a cited ruling can be about something else
    # (the first try ranked "discussion went beyond the listed items" as notice timing).
    for pr in f.get('precedent') or []:
        if pr.get('issue') in ISSUES:
            return pr['issue']
    return 'other'


def rule_weight(doc):
    if doc.startswith('c30a-'):
        return 1.0, 'the statute, ' 
    if doc == '940-cmr-29':
        return 0.9, 'the regulations, '
    return 0.7, 'the AG’s guidance, '


def standout(findings):
    """The top points by precedent, with the facts behind each. Returns (items, scores)."""
    lead = leading_rulings()['issues']
    scored = []
    for i, f in enumerate(findings):
        issue = finding_issue(f)
        rec = (lead.get(issue) or {}).get('record')
        if f['bearing'] != 'raises a question' or not rec:
            continue
        against, for_ = rec['ruled_against'], rec['ruled_for']
        rate = against / max(1, against + for_)
        volume = min(1.0, math.log1p(against) / math.log1p(300))
        rw, where = rule_weight(f['rule']['doc'])
        held = [pr.get('holding') for pr in f.get('precedent') or []]
        bonus = 1.15 if 'violation' in held else (0.85 if held and all(h == 'no violation' for h in held) else 1.0)
        score = (STATUS_W[f['status']] * rw * rate * (0.5 + 0.5 * volume) * bonus
                 * SERIOUSNESS.get(issue, 0.5))
        strength = ('well settled' if against >= 100 and rate >= 0.45 else
                    'often ruled on' if against >= 40 and rate >= 0.35 else
                    'some precedent' if against >= 10 else 'little precedent')
        scored.append({'finding': i, 'title': f['title'], 'issue': issue, 'score': round(score, 3),
                       'strength': strength, 'status': f['status'],
                       'record': dict(rec), 'rule_written_in': where.rstrip(', ') + ' ' + f['rule']['section'],
                       'cited_against': [pr.get('number') for pr in f.get('precedent') or []
                                         if pr.get('holding') == 'violation']})
    scored.sort(key=lambda x: -x['score'])
    items = [x for x in scored if x['score'] >= STANDOUT_MIN][:STANDOUT_MAX]
    return items, scored


# WHAT NO RECORD CAN SHOW. Stated on every review, whatever the model returns.
CANNOT_SEE = [
    'Deliberation outside a meeting — emails, texts or conversations among a quorum of members — leaves no trace in an agenda, minutes or a recording.',
    'When the official notice was posted. We hold the ONLINE copy and the moment that file was made; the official notice may be the paper posted at Town Hall, and its posting time is not in anything published here.',
    'Anything in documents used at the meeting but not posted (handouts, slides, the executive session minutes themselves).',
    'Whether executive session minutes exist, and whether they were reviewed for release as the law requires.',
    'Anything said off-microphone, or before the recording started and after it stopped.',
]
DISCLAIMER = ('Only the Attorney General’s Division of Open Government determines whether the Open '
              'Meeting Law was broken, on a complaint filed first with the public body. These are '
              'points a reader could check, read by a language model from the published record; '
              'none is a finding of fact about what a board did.')

# MASSACHUSETTS LEGAL HOLIDAYS, G.L. c.4 §7 cl.18, typed by us for the years this covers --
# OURS, and named as ours on every review. A holiday on a Sunday is observed the Monday;
# one on a Saturday is not moved.
HOLIDAYS = {
    '2025-01-01', '2025-01-20', '2025-02-17', '2025-04-21', '2025-05-26', '2025-06-19',
    '2025-07-04', '2025-09-01', '2025-10-13', '2025-11-11', '2025-11-27', '2025-12-25',
    '2026-01-01', '2026-01-19', '2026-02-16', '2026-04-20', '2026-05-25', '2026-06-19',
    '2026-07-04', '2026-09-07', '2026-10-12', '2026-11-11', '2026-11-26', '2026-12-25',
    '2027-01-01', '2027-01-18', '2027-02-15', '2027-04-19', '2027-05-31', '2027-06-21',
    '2027-07-05', '2027-09-06', '2027-10-11', '2027-11-11', '2027-11-25', '2027-12-25',
}


def sha256_of(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def rel(p):
    return os.path.relpath(p, ROOT)


# ------------------------------------------------------------------------------ the inputs

def register_row(board, date):
    for r in csv.DictReader(open(REGISTER, encoding='utf-8')):
        if r['board_slug'] == board and r['date'] == date:
            return r
    raise SystemExit('no register row for %s %s' % (board, date))


def stamp(board, date, kind):
    for r in csv.DictReader(open(STAMPS, encoding='utf-8')):
        if r['board_slug'] == board and r['meeting_date'] == date and r['kind'] == kind:
            return r
    return None


def text_for(path_in_meetings):
    """The extracted text of a town document, by its path under sources/meetings/."""
    if not path_in_meetings:
        return None, None
    stem = os.path.splitext(path_in_meetings)[0]
    p = os.path.join(TEXT, stem + '.txt')
    if not os.path.exists(p):
        return None, None
    return p, open(p, encoding='utf-8', errors='replace').read()


def meeting_start(agenda_text, date):
    """The meeting's start, read off the agenda: the first clock time printed on it."""
    m = re.search(r'(\d{1,2})\s*:\s*(\d{2})\s*([ap])\.?\s*m', agenda_text or '', re.I)
    if not m:
        return None, ''
    h, mi = int(m.group(1)) % 12, int(m.group(2))
    if m.group(3).lower() == 'p':
        h += 12
    d = dt.date.fromisoformat(date)
    return dt.datetime(d.year, d.month, d.day, h, mi), m.group(0)


def counted_hours(start, end):
    """Hours from start to end, leaving out every hour on a Saturday, Sunday or legal holiday."""
    if end <= start:
        return 0.0
    total, t = 0.0, start
    while t < end:
        nxt = min(end, dt.datetime.combine(t.date() + dt.timedelta(days=1), dt.time()))
        if t.weekday() < 5 and t.date().isoformat() not in HOLIDAYS:
            total += (nxt - t).total_seconds() / 3600.0
        t = nxt
    return total


def notice_facts(board, date, agenda_text, s=None):
    """What the script can establish about notice timing, and what it cannot. `s` is the
    timestamp row of the agenda VERSION being measured (see agenda_versions)."""
    s = s or stamp(board, date, 'agenda')
    start, as_printed = meeting_start(agenda_text, date)
    f = {'agenda_file_created': s['created'] if s else '', 'agenda_file_modified': s['modified'] if s else '',
         'agenda_file_producer': s['producer'] if s else '',
         'meeting_start_as_printed': as_printed, 'meeting_start': start.isoformat() if start else '',
         'excluded_days': [], 'counted_hours_file_to_meeting': None, 'timezone_assumed': False,
         'revised_notice': bool(re.search(r'\bREVISED\b|\bAMENDED\b', agenda_text or '')),
         'holidays_source': 'G.L. c.4 §7 cl.18; the list of dates is typed by this project'}
    if not (s and s['created'] and start):
        return f
    c = s['created']
    made = dt.datetime.fromisoformat(c[:19])
    if len(c) > 19:
        # The meeting time is local (Eastern). Convert the file's clock to it.
        aware = dt.datetime.fromisoformat(c)
        made = aware.astimezone(dt.timezone(dt.timedelta(hours=-4 if 3 <= aware.month <= 10 else -5))).replace(tzinfo=None)
    else:
        f['timezone_assumed'] = True
    f['counted_hours_file_to_meeting'] = round(counted_hours(made, start), 1)
    f['clock_hours_file_to_meeting'] = round((start - made).total_seconds() / 3600.0, 1)
    d = made.date()
    while d <= start.date():
        if d.weekday() >= 5 or d.isoformat() in HOLIDAYS:
            f['excluded_days'].append(d.isoformat())
        d += dt.timedelta(days=1)
    return f


# AGENDA VERSIONS (13 November 2026). TJ: "if a committee reposts its agenda for the same date,
# we use the most relevant one ... we should make that clear when that happens" -- "one meeting
# didnt mention executive session, but did they add that later as an amended agenda". Until
# now the review read whichever agenda the index listed first: for 4 March 2026 that was the
# ORIGINAL, and the REVISED one posted at 2:42 pm the day of the meeting was never read.
MEETINGS_INDEX = os.path.join(MEET, 'index.csv')


def _lines(text):
    out = []
    for ln in (text or '').splitlines():
        ln = ' '.join(ln.split())
        if ln and not ln.startswith('===PAGE'):
            out.append(ln)
    return out


def version_diff(old, new):
    """Lines in one version and not the other. A line counts as added only if its words appear
    NOWHERE in the other version, compared as letters and digits alone: the same agenda read
    twice differs in spacing ('Tim Sa ntry'), punctuation ('(3 min' against '(3 min)'), item
    letters (removing one item re-letters the rest) and where lines break (two items run onto
    one line). None of those is a change in what the public was told (13 Nov 2026: each produced
    a false "late addition")."""
    def items(text):
        out = []
        for ln in _lines(text):
            out += [x for x in re.split(r'\s+(?=(?:\d{1,2}|[a-z])[.)]\s+[A-Z])', ln) if x.strip()]
        return out

    def norm(x):
        x = re.sub(r'^\s*(?:[a-z]|\d{1,2}|[ivx]+)[.)]\s+', '', x, flags=re.I)
        return re.sub(r'[^a-z0-9]', '', x.lower())
    a, b = items(old), items(new)
    wa, wb = norm(' '.join(a)), norm(' '.join(b))
    return ([x for x in a if len(norm(x)) >= 8 and norm(x) not in wb],
            [x for x in b if len(norm(x)) >= 8 and norm(x) not in wa])


def agenda_versions(board, date):
    """Every agenda the town posted online for this board and date, oldest first, each with its
    text, file creation time, printed start and notice arithmetic. Versions that print a
    DIFFERENT start time are a different meeting that day, not a revision; the caller keeps the
    group it is reviewing."""
    stamps = {r['path']: r for r in csv.DictReader(open(STAMPS, encoding='utf-8'))
              if r['board_slug'] == board and r['meeting_date'] == date and r['kind'] == 'agenda'}
    out = []
    for r in csv.DictReader(open(MEETINGS_INDEX, encoding='utf-8')):
        if r['kind'] != 'agenda' or r['date'] != date or r['path'].split('/')[0] != board:
            continue
        tp, txt = text_for(r['path'])
        if not txt:
            continue
        st = stamps.get(r['path'])
        start, printed = meeting_start(txt, date)
        nf = notice_facts(board, date, txt, st)
        # A copy made AFTER the meeting began cannot be its notice -- 4 Feb 2026 holds the March
        # agenda, made after the February meeting. Set aside, never read as a revision.
        if (nf.get('clock_hours_file_to_meeting') or 0) < 0:
            continue
        out.append({'file_id': r['file_id'], 'path': r['path'], 'url': r['url'], 'title': r.get('title', ''),
                    'text_path': tp, 'text': txt, 'created': (st or {}).get('created', ''),
                    'start_as_printed': printed, 'start': start.isoformat() if start else '',
                    'text_url': SITE + '/docs/minutes/text/' + os.path.splitext(r['path'])[0] + '.txt',
                    'notice': nf})
    out.sort(key=lambda v: (v['created'] or '9', v['file_id']))
    return out


def transcript_lines(path):
    """[(t, text)] in ~20-second lines, and the segment list for re-anchoring quotes."""
    d = json.load(open(path))
    segs = d['segments']
    lines, cur, t0 = [], [], None
    for s in segs:
        if t0 is None:
            t0 = int(s['start'])
        cur.append(s['text'])
        if s['start'] - t0 >= 20:
            lines.append((t0, ' '.join(cur)))
            cur, t0 = [], None
    if cur:
        lines.append((t0, ' '.join(cur)))
    return d, segs, lines


def anchor(quote, segs):
    """The second at which the caption words of `quote` begin, or None if they are not there."""
    if not hasattr(anchor, 'cache') or anchor.cache[0] is not segs:
        chars, owner = [], []
        for i, s in enumerate(segs):
            for ch in L.squash(s['text']):
                chars.append(ch)
                owner.append(i)
        anchor.cache = (segs, ''.join(chars), owner)
    _, flat, owner = anchor.cache
    q = L.squash(quote)
    if len(q) < 20:
        return None
    j = flat.find(q)
    if j < 0:
        return None
    return int(segs[owner[j]]['start'])


def in_text(quote, text):
    q = L.squash(quote)
    return len(q) >= 20 and q in re.sub(r'===page\d+===', '', L.squash(text or ''))


# ------------------------------------------------------------------------------ the prompt

SYSTEM = '''You check ONE public meeting of a Massachusetts town board against the Open Meeting Law (G.L. c.30A §§18-25 and 940 CMR 29.00), using only the published record you are given. You are not a lawyer and you decide nothing: you list POINTS A READER COULD CHECK.

Look at, in this order:
1. notice — was the notice posted 48 hours before the meeting excluding Saturdays, Sundays and legal holidays; does it carry date, time, place and topics; if it was revised, does it show when. The SCRIPT FACTS give the file arithmetic for the ONLINE COPY: the agenda FILE's creation time is the EARLIEST this online copy could have been posted, not the posting time. The town's official notice may be the paper posted at Town Hall, which we cannot see; every timing statement is about the online copy and says so. Under 48 counted hours, this version could not have been posted 48 hours ahead — an earlier version may have been; say so.
2. agenda topics — anything discussed or voted that is not on the posted agenda. The law requires topics the chair reasonably anticipates 48 hours ahead; a topic not anticipated may be discussed. Say whether the record shows why it came up.
   ALSO, both of which the first version of this review missed (8 Oct 2026):
   (a) ACRONYMS AND JARGON in a listed topic: the AG holds a topic insufficiently specific when it rests on an acronym or abbreviation not widely understood by the public, and a body's own familiarity does not count (determinations OML 2026-99, 2018-56, 2024-218 -- the last is Lunenburg's own Historical Commission; contrast 2015-148, AFSCME widely understood). Flag each listed topic that depends on one; quote the topic and the determination.
   (b) DISCUSSION THAT STRAYS BEYOND A LISTED TOPIC: substantial discussion of a subject the notice does not reasonably cover (e.g. the budget or staffing generally during a data presentation), as distinct from context that serves the listed topic. This is a judgement -- at most "possible -- needs checking"; quote the topic as listed and the discussion with its timestamp, and say plainly which reading favours each side. Agenda time estimates ("(3 min)") are not a legal requirement; never flag a topic for running long.
3. votes — motion and outcome recorded; roll call where any member participates remotely (940 CMR 29.10); votes taken in open session.
4. executive session — a vote in open session to enter, by roll call; the purpose stated as one of the enumerated purposes of c.30A §21(a), with enough specificity; a statement whether the body will return to open session; no action taken that belongs in open session. For purpose 1 (an individual's reputation, character or health, or discipline, dismissal, or complaints or charges brought AGAINST them), the 48-hour written notice is owed to 'the individual to be discussed' -- the subject of the discussion, NOT the person who filed a complaint -- and it may be waived by written agreement; that individual may also ask for open session and has rights to attend with counsel. Name the notice's recipient that way.
5. minutes — date, time, place, members present or absent, summary of discussions on each subject, list of documents used, decisions and actions including the record of all votes (c.30A §22(a)); timely creation and approval.
6. remote participation and public access — remote members identified, votes by roll call, the public able to follow live.

RULES FOR EVERY FINDING:
- rule.quote: copy CONTIGUOUS words, character for character, from ONE of the LAW documents below, 30 to 400 characters, and name the document id and the section (e.g. "G.L. c.30A, §21(a)" or "940 CMR 29.03(1)(b)"). If it is not verbatim the finding is discarded.
- evidence: one to three quotes, each CONTIGUOUS and verbatim from the AGENDA, the TOWN MINUTES or the CAPTIONS, 20 to 300 characters. For captions give the [t] second of the line you copied from; caption text is lower-case machine speech recognition — copy it as printed, never tidy it. Never quote OUR MINUTES or the STRUCTURED READ: they are derived indexes, given to help you find things.
- status, exactly one of:
  "clear from the record" — the published record by itself settles this point (say which way in `summary`);
  "possible — needs checking" — the record suggests a question but something not published could answer it;
  "cannot tell from what is published" — the record is silent on something the law requires.
- bearing: "raises a question" or "meets it, as recorded". Report a "meets it" point only for the main procedural checks (notice, executive session entry, remote roll calls, minutes contents), not for every routine vote.
- summary: at most two short sentences, plain English, no legal conclusions. NEVER use the word "violation" or "violated" or "illegal" or "unlawful"; say "the record does not show X" or "X happened before Y".
- settle: the one document, record or question that would settle it.
- precedent (optional, at most two): where one of the PRECEDENT rulings below bears on the point, give its id and a CONTIGUOUS verbatim quote (30 to 400 characters) from its key passage or the determination text. A ruling is how the Attorney General read the law for ANOTHER body on other facts: cite it as how the AG has read the rule, never as a finding about this board, and say in `summary` only what this meeting's record shows. Cite a ruling against the point as readily as one for it. Do not cite a ruling whose facts are unlike this meeting's.
- issue: the closest one from the list, the same list the PRECEDENT is grouped by.
- escalate: whether a researcher with search over all 2,909 AG determinations, every posted agenda and minutes of this and other meetings, and the full captions could change this point's status. needed=true ONLY when that research could actually move it: no PRECEDENT ruling fits the facts ("no fitting precedent"); the minutes, agenda and captions contradict each other in a way more of the record could resolve ("record conflicts"); another meeting's documents would settle it, e.g. an earlier notice or the minutes that approve these ("needs another document"); or the point turns on a reading of the facts the AG has addressed in comparable cases ("judgement on the facts"). Otherwise needed=false, reason "none", question "". `question`: one sentence the researcher must answer.
Prefer 4 to 10 findings, the most useful first. Do not invent problems; a meeting that appears regular should produce mostly "meets it" points and say so in `overall`.
`overall`: two sentences at most, no legal conclusions.'''


def schema():
    law_ids = LAW_IN_PROMPT
    prec_ids = precedent_ids()
    return {
        'type': 'object', 'additionalProperties': False,
        'required': ['findings', 'overall'],
        'properties': {
            'overall': {'type': 'string'},
            'findings': {'type': 'array', 'items': {
                'type': 'object', 'additionalProperties': False,
                'required': ['criterion', 'issue', 'escalate', 'title', 'status', 'bearing', 'summary', 'rule', 'evidence', 'settle'],
                'properties': {
                    'criterion': {'type': 'string', 'enum': CRITERIA},
                    'issue': {'type': 'string', 'enum': ISSUES},
                    'escalate': {'type': 'object', 'additionalProperties': False,
                                 'required': ['needed', 'reason', 'question'],
                                 'properties': {'needed': {'type': 'boolean'},
                                                'reason': {'type': 'string', 'enum': ESCALATE_REASONS},
                                                'question': {'type': 'string'}}},
                    'title': {'type': 'string', 'description': 'under 90 characters'},
                    'status': {'type': 'string', 'enum': STATUSES},
                    'bearing': {'type': 'string', 'enum': ['raises a question', 'meets it, as recorded']},
                    'summary': {'type': 'string'},
                    'rule': {'type': 'object', 'additionalProperties': False,
                             'required': ['doc', 'section', 'quote'],
                             'properties': {'doc': {'type': 'string', 'enum': law_ids},
                                            'section': {'type': 'string'},
                                            'quote': {'type': 'string'}}},
                    'evidence': {'type': 'array', 'minItems': 1, 'maxItems': 3, 'items': {
                        'type': 'object', 'additionalProperties': False,
                        'required': ['source', 'quote'],
                        'properties': {'source': {'type': 'string', 'enum': ['agenda', 'minutes', 'captions']},
                                       'quote': {'type': 'string'},
                                       't': {'type': 'integer'}}}},
                    'settle': {'type': 'string'},
                    'precedent': {'type': 'array', 'maxItems': 2, 'items': {
                        'type': 'object', 'additionalProperties': False,
                        'required': ['id', 'quote'],
                        'properties': {'id': {'type': 'string', 'enum': prec_ids},
                                       'quote': {'type': 'string'}}}},
                }}},
        }}


def build_prompt(ctx):
    law = L.documents()
    parts = ['MEETING: %s, %s.' % (ctx['board'], ctx['date'])]
    if ctx['waiting_for']:
        parts.append('WHAT IS HELD: %s. NOT YET HELD: %s. Review what is held. Do not raise a point only '
                     'because something is not yet held -- the page says what it is waiting for. Where a '
                     'question can only be answered by what is missing, a single point with status "cannot '
                     'tell from what is published" is enough.' % (ctx['stage'], ' and '.join(ctx['waiting_for'])))
    parts.append('SCRIPT FACTS (computed, not read):\n' + json.dumps(ctx['notice'], indent=1))
    vs = ctx.get('agenda_versions') or []
    if vs:
        parts.append('THE TOWN POSTED %d AGENDAS ONLINE FOR THIS MEETING (computed, not read). The LAST one posted '
                     'is the operative notice; earlier ones show what the public was told before it. Notice timing '
                     'is per version: a topic first added in a later version had only that version\'s posting time. '
                     'Quote from whichever version shows the point, and say which version in the summary.' % len(vs))
        for v in vs:
            facts = {'file_id': v['file_id'], 'title': v['title'], 'file_created': v['created'],
                     'counted_hours_file_to_meeting': v['notice']['counted_hours_file_to_meeting'],
                     'operative': v['operative']}
            if not v['operative']:
                facts['lines_removed_in_the_last_version'] = v['removed_in_next']
                facts['lines_added_in_the_last_version'] = v['added_in_next']
            parts.append('=== AGENDA VERSION %d of %d (%s) ===\nSCRIPT FACTS: %s\n%s'
                         % (v['version'], len(vs), 'operative, last posted' if v['operative'] else 'superseded',
                            json.dumps(facts, ensure_ascii=False), v['text']))
    else:
        parts.append('=== AGENDA (as posted; extracted text) ===\n' + (ctx['agenda_text'] or '(no agenda text held)'))
    parts.append('=== TOWN MINUTES (extracted text; the record) ===\n' + (ctx['minutes_text'] or
                 '(NOT YET POSTED. The board has not approved and published minutes for this meeting. '
                 'Any point that only the official minutes could establish -- what they record, '
                 'whether they meet the content requirements -- is "cannot tell from what is '
                 'published". Do not treat their absence as a finding.)'))
    if ctx.get('structured'):
        parts.append('=== STRUCTURED READ of the town minutes (DERIVED; an index, do not quote) ===\n'
                     + json.dumps(ctx['structured'], ensure_ascii=False)[:20000])
    if ctx.get('ours'):
        parts.append('=== OUR MINUTES of the recording (DERIVED; an index, do not quote) ===\n'
                     + json.dumps(ctx['ours'], ensure_ascii=False)[:15000])
    parts.append('=== CAPTIONS of the recording (machine speech recognition; [t] = second) ===\n'
                 + ('\n'.join('[%d] %s' % (t, s) for t, s in ctx['lines']) if ctx['lines'] else
                    '(NO RECORDING HELD YET. Never quote captions.)'))
    pack = ['=== PRECEDENT: the leading AG determinations per issue (most cited by later letters, '
            'the most cited against a school committee, and the newest). Each holding is against the '
            'body named, on its own facts. Quote only verbatim. ===']
    for issue, v in leading_rulings()['issues'].items():
        pack.append('-- %s --' % issue)
        for r in v['rulings']:
            pack.append('id=%s | %s, %s | %s (%s) | holding: %s | cited by %d later letters\n  %s'
                        % (r['id'], r['number'], r['date'], r['public_body'], r['body_type'],
                           r['holding'], r['cited_by'], r['key_passage']))
    parts.append('\n'.join(pack))
    for d in law:
        if d['id'] in LAW_IN_PROMPT:
            parts.append('=== LAW document id=%s: %s ===\n%s' % (d['id'], d['label'],
                                                               re.sub(r'===PAGE \d+===\n?', '', d['body'])))
    return '\n\n'.join(parts)


WITHOUT_MINUTES = False


def gather(board, date):
    r = register_row(board, date)
    vid = (r['video_ids'] or '').split()[0] if r['video_ids'] else ''
    # THE TOWN'S MINUTES ARE OPTIONAL WHEN ASKED: TJ, 8 October 2026, for the previous night's
    # School Committee: "Yes do yesterdays" -- minutes are not posted until the board approves
    # them, weeks later. Without them, anything only the minutes would show is CANNOT TELL, and
    # the page says the official minutes were not yet available.
    # ONE REVIEW PER MEETING, OF WHATEVER IS HELD (13 November 2026). TJ: "Do the OML review"
    # should process the info available, but flag that it can only go so far until more is
    # added" -- agenda only, then the recording, then the minutes. Each pass replaces the last.
    if not r['agenda_path']:
        raise SystemExit('%s %s: no agenda held; nothing to review' % (board, date))
    has_tr = bool(r['transcript_paths'] and vid)
    has_min = bool(r['minutes_path'])
    stage = ('full record' if has_tr and has_min else 'agenda and recording' if has_tr
             else 'agenda and minutes' if has_min else 'agenda only')
    waiting = ([] if has_tr else ['the recording']) + ([] if has_min else ['the official minutes'])
    ap, at = text_for(r['agenda_path'])
    versions = agenda_versions(board, date)
    chosen = next((v for v in versions if v['path'] == r['agenda_path']), None)
    same = [v for v in versions if not chosen or not v['start'] or not chosen['start'] or v['start'] == chosen['start']]
    other_meetings = [v for v in versions if v not in same]
    for i, v in enumerate(same, 1):
        v['version'] = i
        v['operative'] = v is same[-1]
    if len(same) > 1:
        # THE OPERATIVE NOTICE IS THE LAST ONE POSTED. The review reads every version; the
        # agenda it quotes by default, and the notice point it states, are the last one's.
        op = same[-1]
        ap, at = op['text_path'], op['text']
        r = dict(r, agenda_path=op['path'], agenda_url=op['url'])
        for v in same[:-1]:
            v['removed_in_next'], v['added_in_next'] = version_diff(v['text'], op['text'])
    mp, mt = text_for(r['minutes_path'])
    tp = os.path.join(ROOT, r['transcript_paths'].split()[0]) if has_tr else ''
    tdoc, segs, lines = transcript_lines(tp) if has_tr else (None, [], [])
    structured = ours = None
    sp = os.path.join(ROOT, r['official_votes_path']) if r['official_votes_path'] else ''
    if sp and os.path.exists(sp):
        j = json.load(open(sp))
        structured = {k: j.get(k) for k in ('attendees', 'votes', 'decisions', 'topics') if j.get(k)}
    op = os.path.join(ROOT, r['our_minutes_path']) if r['our_minutes_path'] else ''
    if op and os.path.exists(op):
        j = json.load(open(op))['minutes']
        ours = {k: j.get(k) for k in ('attendees', 'votes', 'decisions', 'topics') if j.get(k)}
    inputs = {}
    for name, p in (('agenda_text', ap), ('minutes_text', mp), ('transcript', tp), ('structured_read', sp),
                    ('our_minutes', op), ('leading_rulings', LEADING)) + tuple(
                        ('agenda_text_v%d' % v['version'], v['text_path']) for v in same if len(same) > 1):
        if p and os.path.exists(p):
            inputs[name] = {'path': rel(p), 'sha256': sha256_of(p)}
    law = {d['id']: {'path': d['text'], 'sha256': sha256_of(os.path.join(ROOT, d['text'])),
                     'source_sha256': d['sha256'], 'upstream': d['upstream']}
           for d in L.documents() if d['id'] in LAW_IN_PROMPT}
    return {
        'board': r['board'], 'board_slug': board, 'date': date,
        # The file key: the video id once there is a recording, `agenda` before. The page
        # address follows it, and the earlier pass's file is removed when the key changes.
        'video_id': vid if has_tr else 'agenda', 'has_video': has_tr,
        'stage': stage, 'waiting_for': waiting,
        'video_url': ('https://www.youtube.com/watch?v=' + vid) if has_tr else '',
        'agenda_url': r['agenda_url'], 'minutes_url': r['minutes_url'],
        'agenda_text_url': SITE + '/docs/minutes/text/' + os.path.splitext(r['agenda_path'])[0] + '.txt' if r['agenda_path'] else '',
        'minutes_text_url': (SITE + '/docs/minutes/text/' + os.path.splitext(r['minutes_path'])[0] + '.txt')
                            if r['minutes_path'] else '',
        'agenda_text': at, 'minutes_text': mt, 'segs': segs, 'lines': lines,
        'structured': structured, 'ours': ours, 'inputs': inputs, 'law_inputs': law,
        'notice': next((v['notice'] for v in same if v.get('operative')), None) or notice_facts(board, date, at),
        'agenda_versions': same if len(same) > 1 else [],
        'other_meetings_same_date': other_meetings,
        'minutes_file_created': (stamp(board, date, 'minutes') or {}).get('created', ''),
    }


# --------------------------------------------------------------------------- verification

BANNED = re.compile(r'\b(violat\w*|illegal\w*|unlawful\w*)\b', re.I)


def verify(finding, ctx, law_docs):
    """(finding, None) with quotes made canonical, or (None, reason)."""
    rule = finding['rule']
    # The fallback searches only what the model was given: the law index now holds 2,909 AG
    # letters, and a rule quote must not resolve to one that was never in the prompt.
    hit = L.verbatim(rule['quote'], [rule['doc']], law_docs) or L.verbatim(rule['quote'], LAW_IN_PROMPT, law_docs)
    if not hit:
        return None, 'rule quote not verbatim in the law'
    rule['doc'] = hit
    d = next(x for x in law_docs if x['id'] == hit)
    rule['label'] = d['label']
    rule['upstream'] = d['upstream']
    rule['our_copy'] = d['our_copy']
    for e in finding['evidence']:
        if e['source'] == 'captions':
            t = anchor(e['quote'], ctx['segs'])
            if t is None:
                return None, 'caption quote not verbatim in the captions'
            e['t'] = t
            e['url'] = '%s&t=%ds' % (ctx['video_url'], t)
            e['note'] = 'machine captions — a finding aid; watch the moment to check it'
        elif e['source'] == 'agenda' and ctx.get('agenda_versions'):
            # Checked against the LAST version first, then earlier ones; the evidence names the
            # version it came from, so the page can say "the original agenda".
            v = next((v for v in reversed(ctx['agenda_versions']) if in_text(e['quote'], v['text'])), None)
            if not v:
                return None, 'agenda quote not verbatim in any posted version'
            e.pop('t', None)
            e.update({'url': v['url'], 'text_url': v['text_url'], 'agenda_version': v['version'],
                      'agenda_file_id': v['file_id'], 'operative': v['operative']})
        else:
            src = ctx['agenda_text'] if e['source'] == 'agenda' else ctx['minutes_text']
            if not in_text(e['quote'], src):
                return None, '%s quote not verbatim in the %s text' % (e['source'], e['source'])
            e.pop('t', None)
            e['url'] = ctx['agenda_url'] if e['source'] == 'agenda' else ctx['minutes_url']
            e['text_url'] = ctx['agenda_text_url'] if e['source'] == 'agenda' else ctx['minutes_text_url']
    for pr in finding.get('precedent') or []:
        if not L.verbatim(pr['quote'], [pr['id']], law_docs):
            return None, 'precedent quote not verbatim in %s' % pr['id']
        d = next(x for x in law_docs if x['id'] == pr['id'])
        pr.update({'label': d['label'], 'upstream': d['upstream'], 'our_copy': d['our_copy']})
        pr.update(precedent_holding(pr['id'], pr['quote']))
        pr['note'] = 'how the Attorney General read the law for that body, on its facts; not a finding about this board'
    for k in ('title', 'summary', 'settle'):
        if BANNED.search(finding.get(k, '')):
            return None, 'used a word reserved for the Attorney General (%s)' % k
    return finding, None


def notice_finding(ctx, law_docs):
    """The notice-timing point, decided by arithmetic rather than by the model."""
    n = ctx['notice']
    if n['counted_hours_file_to_meeting'] is None:
        return None
    rule_q = ('a public body shall post notice of every meeting at least 48 hours prior to the meeting, '
              'excluding Saturdays, Sundays and legal holidays')
    if not L.verbatim(rule_q, ['c30a-20'], law_docs):
        return None
    d = next(x for x in law_docs if x['id'] == 'c30a-20')
    hrs = n['counted_hours_file_to_meeting']
    under = hrs < 48
    tz = (' The file’s clock carries no timezone; Eastern time is assumed. Read as UTC it would be '
          'four hours earlier.' if n['timezone_assumed'] else '')
    rev = ' The agenda is headed REVISED, so an earlier version may have been posted sooner.' if n['revised_notice'] else ''
    # THE ONLINE COPY ONLY (TJ, 13 November 2026): "we can only make claims about the online copy,
    # which isnt official, technically." The town's official notice is, as far as anyone has
    # told us, the paper posted at Town Hall, and its posting time is published nowhere.
    if under:
        summary = ('The online copy of this agenda was made %.1f counted hours before the meeting, so that '
                   'copy could not have gone up online 48 hours ahead. The official notice may be the copy '
                   'posted at Town Hall; its posting time is not published.%s%s' % (hrs, rev, tz))
    else:
        summary = ('The online copy of this agenda was made %.1f counted hours before the meeting, so it could '
                   'have gone up online 48 hours ahead. When the official notice was posted is not in anything '
                   'published here.%s' % (hrs, tz))
    ev = []
    # The line the time is printed on -- with the line above it when that alone is too short
    # to be a quotation (a Parks agenda prints `7:00pm` on a line of its own).
    lines = [ln.strip() for ln in (ctx['agenda_text'] or '').splitlines() if ln.strip()]
    for i, ln in enumerate(lines):
        if n['meeting_start_as_printed'] and n['meeting_start_as_printed'] in ln:
            q = ln if len(ln) >= 20 or i == 0 else lines[i - 1] + ' ' + ln
            if in_text(q, ctx['agenda_text']):
                ev.append({'source': 'agenda', 'quote': ' '.join(q.split()), 'url': ctx['agenda_url'],
                           'text_url': ctx['agenda_text_url']})
            break
    m = re.search(r'REVISED[^\n]{0,60}', ctx['agenda_text'] or '')
    if m and in_text(m.group(0).strip(), ctx['agenda_text']):
        ev.append({'source': 'agenda', 'quote': m.group(0).strip(), 'url': ctx['agenda_url'],
                   'text_url': ctx['agenda_text_url']})
    ev.append({'source': 'file metadata', 'quote': 'CreationDate %s' % n['agenda_file_created'],
               'url': ctx['agenda_url'],
               'note': 'the online PDF’s own creation time, read by scripts/extract_document_timestamps.py; '
                       'the earliest this online copy could have been posted'})
    return {
        'criterion': 'notice', 'issue': 'notice timing', 'by': 'script',
        'title': 'Online copy of the agenda made %.0f counted hours before the meeting' % hrs,
        'status': 'possible — needs checking' if under else 'cannot tell from what is published',
        'bearing': 'raises a question' if under else 'meets it, as recorded',
        'summary': summary,
        'rule': {'doc': 'c30a-20', 'section': 'G.L. c.30A, §20(b)', 'quote': rule_q, 'label': d['label'],
                 'upstream': d['upstream'], 'our_copy': d['our_copy']},
        'evidence': ev,
        'settle': 'The clerk’s posting record for this notice (the time it went up on the board and the website), and any earlier version.',
        'arithmetic': n,
    }


def added_topic_findings(versions, law_docs):
    """A TOPIC FIRST POSTED IN A REVISED ONLINE AGENDA had only that copy's posting time. Decided
    by the script, from the computed diff and the file arithmetic, like the notice point -- the
    model missed it on 6 Aug 2025, where the revision added the contract the board then voted.
    Only lines that read as topics (lettered or numbered items), and only under 48 hours."""
    out = []
    op = next((v for v in versions if v.get('operative')), None)
    hrs = op and op.get('counted_hours_file_to_meeting')
    if not op or hrs is None or hrs >= 48:
        return out
    rule_q = ('a public body shall post notice of every meeting at least 48 hours prior to the meeting, '
              'excluding Saturdays, Sundays and legal holidays')
    d = next((x for x in law_docs if x['id'] == 'c30a-20'), None)
    if not d or not L.verbatim(rule_q, ['c30a-20'], law_docs):
        return out
    seen = set()
    for v in versions:
        for line in v.get('added_in_next') or []:
            if not re.match(r'^\s*(?:[a-z]|\d{1,2}|[ivx]+)[.)]\s+\S', line, re.I) or L.squash(line) in seen:
                continue
            if len(L.squash(line)) < 20:
                continue
            seen.add(L.squash(line))
            topic = re.sub(r'^\s*(?:[a-z]|\d{1,2}|[ivx]+)[.)]\s+', '', line, flags=re.I)
            out.append({
                'criterion': 'notice', 'issue': 'notice timing', 'by': 'script',
                'escalate': {'needed': False, 'reason': 'none', 'question': ''},
                'title': '“%s” first appears on an online agenda made %.0f counted hours before' % (topic[:56], hrs),
                'status': 'possible — needs checking', 'bearing': 'raises a question',
                'summary': ('This topic is not on the earlier online agenda; it was added in the online copy made '
                            '%.1f counted hours before the meeting, so that copy could not have gone up online 48 '
                            'hours ahead. When the official notice was amended is not published.' % hrs),
                'rule': {'doc': 'c30a-20', 'section': 'G.L. c.30A, §20(b)', 'quote': rule_q, 'label': d['label'],
                         'upstream': d['upstream'], 'our_copy': d['our_copy']},
                'evidence': [{'source': 'agenda', 'quote': line, 'url': op['url'], 'text_url': op['text_url'],
                              'agenda_version': op['version'], 'agenda_file_id': op['file_id'], 'operative': True},
                             {'source': 'file metadata', 'quote': 'CreationDate %s' % op['created'], 'url': op['url'],
                              'note': 'the revised online agenda’s own creation time; the earliest that copy could have been posted'}],
                'settle': 'The clerk’s posting record for the revised notice, and whether the topic was posted anywhere earlier.',
            })
    return out


# --------------------------------------------------------------------------------- running

def out_path(board, date, vid):
    return os.path.join(OUT, board, '%s-%s.json' % (date, vid))


def pub_path(board, date, vid):
    return os.path.join(PUB, board, '%s-%s.json' % (date, vid))


def write_json(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.part'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    os.replace(tmp, path)


def log_spend(board, date, cost, result):
    import sweep_backlog
    sweep_backlog.log({'at': dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'), 'stream': 'oml',
                       'board': board, 'date': date, 'cost_usd': '%.4f' % (cost or 0), 'result': result})


def review(board, date, dry=False):
    ctx = gather(board, date)
    prompt = build_prompt(ctx)
    print('%s %s: prompt %d chars (~%dk tokens); notice: %s counted hours'
          % (board, date, len(prompt), len(prompt) // 4000, ctx['notice']['counted_hours_file_to_meeting']))
    if dry:
        return 0
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    r = claude_lean.run(['claude', '-p', '--tools', '', '--model', MODEL, '--system-prompt', SYSTEM,
                        '--json-schema', json.dumps(schema()), '--output-format', 'json',
                        '--max-budget-usd', '2'],
                       input=prompt, capture_output=True, text=True, env=env, timeout=TIMEOUT)
    if r.returncode != 0:
        log_spend(board, date, 0, 'failed')
        raise SystemExit('claude failed on %s %s:\n%s' % (board, date, (r.stdout + r.stderr)[-2000:]))
    res = json.loads(r.stdout)
    cost = res.get('total_cost_usd')
    body = res.get('structured_output') or res.get('result')
    if isinstance(body, str):
        body = json.loads(body)
    if not isinstance(body, dict) or 'findings' not in body:
        log_spend(board, date, cost, 'no structured output')
        raise SystemExit('no structured output for %s %s' % (board, date))
    log_spend(board, date, cost, 'ok')
    print('cost $%.4f' % (cost or 0))
    law_docs = L.documents()
    kept, dropped = [], []
    for f in body['findings']:
        f['by'] = 'model'
        g, why = verify(f, ctx, law_docs)
        if g:
            kept.append(g)
        else:
            dropped.append({'title': f.get('title', ''), 'why': why})
    nf = notice_finding(ctx, law_docs)
    if nf:
        kept = [nf] + [f for f in kept if not (f['criterion'] == 'notice' and 'hour' in (f['title'] + f['summary']).lower())]
    vs_saved = [dict(v, counted_hours_file_to_meeting=v['notice']['counted_hours_file_to_meeting'])
                for v in ctx.get('agenda_versions') or []]
    kept = added_topic_findings(vs_saved, law_docs) + kept
    overall = body.get('overall', '')
    if BANNED.search(overall):
        overall = ''
    counts = {s: sum(1 for f in kept if f['status'] == s) for s in STATUSES}
    items, scored = standout(kept)
    flagged = sum(1 for f in kept if (f.get('escalate') or {}).get('needed'))
    doc = {
        'title': 'Open Meeting Law review',
        'warning': ('EXPERIMENTAL AND UNLISTED. Read by a language model from the published record; every '
                    'quotation is checked verbatim against its source, and a point whose quotes are not '
                    'is dropped. ' + DISCLAIMER),
        'disclaimer': DISCLAIMER,
        'board': ctx['board'], 'board_slug': board, 'date': date, 'video_id': ctx['video_id'],
        'video_url': ctx['video_url'], 'agenda_url': ctx['agenda_url'], 'minutes_url': ctx['minutes_url'],
        'agenda_text_url': ctx['agenda_text_url'], 'minutes_text_url': ctx['minutes_text_url'],
        'our_minutes_page': ('/meeting-minutes/%s/%s-%s' % (board, date, ctx['video_id'])) if ctx['has_video'] else '',
        'stage': ctx['stage'], 'waiting_for': ctx['waiting_for'],
        'overall': overall,
        'counts': counts,
        'findings': kept,
        'standout': items,
        'standout_scores': scored,
        'escalation': {'flagged': flagged, 'of': len(kept),
                       'rate': round(flagged / len(kept), 3) if kept else 0.0},
        'dropped': dropped,
        'cannot_see': CANNOT_SEE + ([] if ctx['has_video'] else
                       ['There was no recording of this meeting held when this was written, so nothing '
                        'said at the meeting is checked.']) + ([] if ctx['minutes_text'] else
                       ['The official minutes of this meeting were not yet posted when this was '
                        'written, so nothing here is checked against them.']),
        'statuses': {
            'clear from the record': 'the published record by itself settles this point',
            'possible — needs checking': 'the record suggests a question that something unpublished could answer',
            'cannot tell from what is published': 'the record is silent on something the law requires',
        },
        'notice_arithmetic': ctx['notice'],
        # Every agenda posted online for this meeting, oldest first, without its text: what the
        # page shows as "this meeting had N posted agendas", with what changed between them.
        'agenda_versions': [{k: v.get(k) for k in ('version', 'file_id', 'title', 'url', 'text_url', 'created',
                                                    'operative', 'removed_in_next', 'added_in_next')}
                            | {'counted_hours_file_to_meeting': v['notice']['counted_hours_file_to_meeting']}
                            for v in ctx.get('agenda_versions') or []],
        'other_meetings_same_date': [{k: v.get(k) for k in ('file_id', 'title', 'url', 'start_as_printed')}
                                     for v in ctx.get('other_meetings_same_date') or []],
        'minutes_file_created': ctx['minutes_file_created'],
        'inputs': ctx['inputs'], 'law_inputs': ctx['law_inputs'],
        'written': {'by': 'scripts/oml_review.py', 'model': MODEL,
                    'at': dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'), 'cost_usd': cost},
    }
    # ONE REPORT PER MEETING: an earlier pass (another key, e.g. `agenda` before the recording)
    # is replaced, and remembered in one line.
    history = []
    dirs = [OUT] + ([] if os.environ.get('OML_OUT') else [PUB])
    for base in dirs:
        for old in glob.glob(os.path.join(base, board, '%s-*.json' % date)):
            try:
                o = json.load(open(old, encoding='utf-8'))
            except ValueError:
                o = {}
            if base == OUT and o:
                history = (o.get('history') or []) + [{'stage': o.get('stage', 'full record'),
                           'at': (o.get('written') or {}).get('at', ''), 'counts': o.get('counts', {}),
                           'points': len(o.get('findings', []))}]
            if os.path.basename(old) != os.path.basename(out_path(board, date, ctx['video_id'])):
                os.remove(old)
    doc['history'] = history
    write_json(out_path(board, date, ctx['video_id']), doc)
    if not os.environ.get('OML_OUT'):
        write_json(pub_path(board, date, ctx['video_id']), doc)
    print('wrote %s: %d finding(s) kept, %d dropped; %s' % (
        rel(out_path(board, date, ctx['video_id'])), len(kept), len(dropped),
        ', '.join('%d %s' % (v, k) for k, v in counts.items())))
    return 0


def rescore():
    """Recompute what is model-free on every held review -- each precedent's holding and the
    `standout` block -- with no paid call. Run after the leading-rulings index or the score
    changes. Writes the published copy too, unless OML_OUT points at a pilot."""
    n = 0
    for p in sorted(glob.glob(os.path.join(OUT, '*', '*.json'))):
        doc = json.load(open(p, encoding='utf-8'))
        for f in doc['findings']:
            for pr in f.get('precedent') or []:
                pr.pop('holding_note', None)
                pr.update(precedent_holding(pr['id'], pr['quote']))
        # SCRIPT POINTS ARE RE-DERIVED, never carried: their wording and arithmetic belong to
        # this script, so a change here (the online-copy wording, 13 Nov 2026) reaches every review.
        law_docs = L.documents()
        try:
            ctx = gather(doc['board_slug'], doc['date'])
        except SystemExit:
            ctx = None
        if ctx:
            model_pts = [f for f in doc['findings'] if f.get('by') != 'script']
            nf = notice_finding(ctx, law_docs)
            vs = [dict(v, counted_hours_file_to_meeting=v['notice']['counted_hours_file_to_meeting'])
                  for v in ctx.get('agenda_versions') or []]
            doc['findings'] = added_topic_findings(vs, law_docs) + ([nf] if nf else []) + model_pts
            doc['agenda_versions'] = [{k: v.get(k) for k in ('version', 'file_id', 'title', 'url', 'text_url',
                                                             'created', 'operative', 'removed_in_next', 'added_in_next')}
                                      | {'counted_hours_file_to_meeting': v['counted_hours_file_to_meeting']} for v in vs]
            doc['counts'] = {s: sum(1 for f in doc['findings'] if f['status'] == s) for s in STATUSES}
        doc['standout'], doc['standout_scores'] = standout(doc['findings'])
        write_json(p, doc)
        if not os.environ.get('OML_OUT'):
            write_json(pub_path(doc['board_slug'], doc['date'], doc['video_id']), doc)
        n += 1
        print('%s: %s' % (doc['date'], '; '.join('%s (%.2f, %s)' % (x['title'], x['score'], x['strength'])
                                                 for x in doc['standout']) or 'nothing stands out'))
    print('rescored %d review(s)' % n)
    return 0


def check():
    """Every review: parses; every quote still verbatim; inputs unchanged; published copy identical."""
    files = sorted(glob.glob(os.path.join(OUT, '*', '*.json')))
    law_docs = L.documents()
    bad, stale, n = [], [], 0
    for p in files:
        doc = json.load(open(p))
        n += len(doc['findings'])
        texts = {}
        for k in ('agenda_text', 'minutes_text'):
            ip = doc['inputs'].get(k, {}).get('path')
            texts[k] = open(os.path.join(ROOT, ip), encoding='utf-8', errors='replace').read() if ip else ''
        tp = doc['inputs'].get('transcript', {}).get('path')
        segs = json.load(open(os.path.join(ROOT, tp)))['segments'] if tp else []
        for name, meta in list(doc['inputs'].items()) + list(doc['law_inputs'].items()):
            fp = os.path.join(ROOT, meta['path'])
            if not os.path.exists(fp) or sha256_of(fp) != meta['sha256']:
                stale.append('%s: input %s has changed since the review' % (rel(p), meta['path']))
        for f in doc['findings']:
            if not L.verbatim(f['rule']['quote'], [f['rule']['doc']], law_docs):
                bad.append('%s: rule quote no longer verbatim (%s)' % (rel(p), f['title']))
            for e in f['evidence']:
                if e['source'] == 'captions':
                    if anchor(e['quote'], segs) != e['t']:
                        bad.append('%s: caption quote not at t=%s (%s)' % (rel(p), e['t'], f['title']))
                elif e['source'] == 'agenda' and e.get('agenda_version'):
                    vp = doc['inputs'].get('agenda_text_v%d' % e['agenda_version'], {}).get('path')
                    vt = open(os.path.join(ROOT, vp), encoding='utf-8', errors='replace').read() if vp else ''
                    if not in_text(e['quote'], vt):
                        bad.append('%s: agenda v%s quote not verbatim (%s)' % (rel(p), e['agenda_version'], f['title']))
                elif e['source'] in ('agenda', 'minutes'):
                    if not in_text(e['quote'], texts[e['source'] + '_text']):
                        bad.append('%s: %s quote not verbatim (%s)' % (rel(p), e['source'], f['title']))
            for pr in f.get('precedent') or []:
                if not L.verbatim(pr['quote'], [pr['id']], law_docs):
                    bad.append('%s: precedent quote not verbatim in %s (%s)' % (rel(p), pr['id'], f['title']))
            for k in ('title', 'summary', 'settle'):
                if BANNED.search(f.get(k, '')):
                    bad.append('%s: reserved word in %s (%s)' % (rel(p), k, f['title']))
            if f['status'] not in STATUSES:
                bad.append('%s: unknown status %r' % (rel(p), f['status']))
        pp = pub_path(doc['board_slug'], doc['date'], doc['video_id'])
        if os.environ.get('OML_OUT'):
            continue  # a pilot publishes nothing, by design
        if not os.path.exists(pp) or open(pp, 'rb').read() != open(p, 'rb').read():
            bad.append('%s: published copy %s missing or different' % (rel(p), rel(pp)))
    for s in stale:
        print('  stale:', s)
    for b in bad:
        print('  !!', b)
    print('oml reviews: %d file(s), %d finding(s); %d quote problem(s), %d stale input(s)'
          % (len(files), n, len(bad), len(stale)))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('board', nargs='?')
    ap.add_argument('date', nargs='?')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--rescore', action='store_true', help='recompute precedent holdings and the standout block; no paid call')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--without-minutes', action='store_true',
                    help='review from the agenda and the recording when the town has not posted minutes yet')
    a = ap.parse_args()
    global WITHOUT_MINUTES
    WITHOUT_MINUTES = a.without_minutes
    if a.check:
        return check()
    if a.rescore:
        return rescore()
    if not (a.board and a.date):
        ap.error('board and date, or --check')
    return review(a.board, a.date, a.dry_run)


if __name__ == '__main__':
    sys.exit(main())
