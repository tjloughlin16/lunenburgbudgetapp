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
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oml_law as L  # noqa: E402

ROOT = os.path.dirname(HERE)
REGISTER = os.path.join(ROOT, 'sources', 'data', 'meeting-register.csv')
STAMPS = os.path.join(ROOT, 'sources', 'data', 'meeting-document-timestamps.csv')
MEET = os.path.join(ROOT, 'sources', 'meetings')
TEXT = os.path.join(MEET, 'text')
OUT = os.path.join(ROOT, 'sources', 'data', 'oml-reviews')
PUB = os.path.join(ROOT, 'fy28', 'public', 'data', 'oml')
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
MODEL = 'sonnet'
TIMEOUT = 900
SITE = 'https://lunenburgbudgetproject.org'

STATUSES = ['clear from the record', 'possible — needs checking', 'cannot tell from what is published']
CRITERIA = ['notice', 'agenda topics', 'votes', 'executive session', 'minutes',
            'remote participation', 'public access', 'other']
# The law handed to the model, and the only documents a rule may be quoted from. The guide
# (136 KB) is left out for size; its checklists carry its operative lines.
LAW_IN_PROMPT = ['c30a-18', 'c30a-20', 'c30a-21', 'c30a-22', 'c30a-23', '940-cmr-29',
                 'oml-notice-checklist', 'oml-minutes-checklist', 'oml-executive-session-checklist',
                 'oml-chair-checklist', 'remote-participation-guidance']

# WHAT NO RECORD CAN SHOW. Stated on every review, whatever the model returns.
CANNOT_SEE = [
    'Deliberation outside a meeting — emails, texts or conversations among a quorum of members — leaves no trace in an agenda, minutes or a recording.',
    'When the notice was actually posted, and where. We hold the agenda file and the moment that file was made; the clerk’s posting time is not in anything published here.',
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


def notice_facts(board, date, agenda_text):
    """What the script can establish about notice timing, and what it cannot."""
    s = stamp(board, date, 'agenda')
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
1. notice — was the notice posted 48 hours before the meeting excluding Saturdays, Sundays and legal holidays; does it carry date, time, place and topics; if it was revised, does it show when. The SCRIPT FACTS give the file arithmetic: the agenda FILE's creation time is the EARLIEST this version could have been posted, not the posting time. Under 48 counted hours, this version could not have been posted 48 hours ahead — an earlier version may have been; say so.
2. agenda topics — anything discussed or voted that is not on the posted agenda. The law requires topics the chair reasonably anticipates 48 hours ahead; a topic not anticipated may be discussed. Say whether the record shows why it came up.
3. votes — motion and outcome recorded; roll call where any member participates remotely (940 CMR 29.10); votes taken in open session.
4. executive session — a vote in open session to enter, by roll call; the purpose stated as one of the enumerated purposes of c.30A §21(a), with enough specificity; a statement whether the body will return to open session; no action taken that belongs in open session.
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
Prefer 4 to 10 findings, the most useful first. Do not invent problems; a meeting that appears regular should produce mostly "meets it" points and say so in `overall`.
`overall`: two sentences at most, no legal conclusions.'''


def schema():
    law_ids = LAW_IN_PROMPT
    return {
        'type': 'object', 'additionalProperties': False,
        'required': ['findings', 'overall'],
        'properties': {
            'overall': {'type': 'string'},
            'findings': {'type': 'array', 'items': {
                'type': 'object', 'additionalProperties': False,
                'required': ['criterion', 'title', 'status', 'bearing', 'summary', 'rule', 'evidence', 'settle'],
                'properties': {
                    'criterion': {'type': 'string', 'enum': CRITERIA},
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
                }}},
        }}


def build_prompt(ctx):
    law = L.documents()
    parts = ['MEETING: %s, %s.' % (ctx['board'], ctx['date'])]
    parts.append('SCRIPT FACTS (computed, not read):\n' + json.dumps(ctx['notice'], indent=1))
    parts.append('=== AGENDA (as posted; extracted text) ===\n' + (ctx['agenda_text'] or '(no agenda text held)'))
    parts.append('=== TOWN MINUTES (extracted text; the record) ===\n' + (ctx['minutes_text'] or '(no minutes held)'))
    if ctx.get('structured'):
        parts.append('=== STRUCTURED READ of the town minutes (DERIVED; an index, do not quote) ===\n'
                     + json.dumps(ctx['structured'], ensure_ascii=False)[:20000])
    if ctx.get('ours'):
        parts.append('=== OUR MINUTES of the recording (DERIVED; an index, do not quote) ===\n'
                     + json.dumps(ctx['ours'], ensure_ascii=False)[:15000])
    parts.append('=== CAPTIONS of the recording (machine speech recognition; [t] = second) ===\n'
                 + '\n'.join('[%d] %s' % (t, s) for t, s in ctx['lines']))
    for d in law:
        if d['id'] in LAW_IN_PROMPT:
            parts.append('=== LAW document id=%s: %s ===\n%s' % (d['id'], d['label'],
                                                               re.sub(r'===PAGE \d+===\n?', '', d['body'])))
    return '\n\n'.join(parts)


def gather(board, date):
    r = register_row(board, date)
    vid = (r['video_ids'] or '').split()[0] if r['video_ids'] else ''
    if not (r['minutes_path'] and r['transcript_paths'] and vid):
        raise SystemExit('%s %s lacks town minutes or a recording transcript; nothing to compare' % (board, date))
    ap, at = text_for(r['agenda_path'])
    mp, mt = text_for(r['minutes_path'])
    tp = os.path.join(ROOT, r['transcript_paths'].split()[0])
    tdoc, segs, lines = transcript_lines(tp)
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
    for name, p in (('agenda_text', ap), ('minutes_text', mp), ('transcript', tp), ('structured_read', sp), ('our_minutes', op)):
        if p and os.path.exists(p):
            inputs[name] = {'path': rel(p), 'sha256': sha256_of(p)}
    law = {d['id']: {'path': d['text'], 'sha256': sha256_of(os.path.join(ROOT, d['text'])),
                     'source_sha256': d['sha256'], 'upstream': d['upstream']}
           for d in L.documents() if d['id'] in LAW_IN_PROMPT}
    return {
        'board': r['board'], 'board_slug': board, 'date': date, 'video_id': vid,
        'video_url': 'https://www.youtube.com/watch?v=' + vid,
        'agenda_url': r['agenda_url'], 'minutes_url': r['minutes_url'],
        'agenda_text_url': SITE + '/docs/minutes/text/' + os.path.splitext(r['agenda_path'])[0] + '.txt' if r['agenda_path'] else '',
        'minutes_text_url': SITE + '/docs/minutes/text/' + os.path.splitext(r['minutes_path'])[0] + '.txt',
        'agenda_text': at, 'minutes_text': mt, 'segs': segs, 'lines': lines,
        'structured': structured, 'ours': ours, 'inputs': inputs, 'law_inputs': law,
        'notice': notice_facts(board, date, at),
        'minutes_file_created': (stamp(board, date, 'minutes') or {}).get('created', ''),
    }


# --------------------------------------------------------------------------- verification

BANNED = re.compile(r'\b(violat\w*|illegal\w*|unlawful\w*)\b', re.I)


def verify(finding, ctx, law_docs):
    """(finding, None) with quotes made canonical, or (None, reason)."""
    rule = finding['rule']
    hit = L.verbatim(rule['quote'], [rule['doc']], law_docs) or L.verbatim(rule['quote'], None, law_docs)
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
        else:
            src = ctx['agenda_text'] if e['source'] == 'agenda' else ctx['minutes_text']
            if not in_text(e['quote'], src):
                return None, '%s quote not verbatim in the %s text' % (e['source'], e['source'])
            e.pop('t', None)
            e['url'] = ctx['agenda_url'] if e['source'] == 'agenda' else ctx['minutes_url']
            e['text_url'] = ctx['agenda_text_url'] if e['source'] == 'agenda' else ctx['minutes_text_url']
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
    if under:
        summary = ('This agenda file was made %.1f counted hours before the meeting, so this version could '
                   'not have been posted 48 hours ahead.%s%s' % (hrs, rev, tz))
    else:
        summary = ('This agenda file was made %.1f counted hours before the meeting, so 48-hour posting was '
                   'possible; when it was actually posted is not in anything published here.%s' % (hrs, tz))
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
               'note': 'the PDF’s own creation time, read by scripts/extract_document_timestamps.py; '
                       'the earliest this file could have been posted'})
    return {
        'criterion': 'notice', 'by': 'script',
        'title': 'Agenda file made %.0f counted hours before the meeting' % hrs,
        'status': 'possible — needs checking' if under else 'cannot tell from what is published',
        'bearing': 'raises a question' if under else 'meets it, as recorded',
        'summary': summary,
        'rule': {'doc': 'c30a-20', 'section': 'G.L. c.30A, §20(b)', 'quote': rule_q, 'label': d['label'],
                 'upstream': d['upstream'], 'our_copy': d['our_copy']},
        'evidence': ev,
        'settle': 'The clerk’s posting record for this notice (the time it went up on the board and the website), and any earlier version.',
        'arithmetic': n,
    }


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
    r = subprocess.run(['claude', '-p', '--tools', '', '--model', MODEL, '--system-prompt', SYSTEM,
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
    overall = body.get('overall', '')
    if BANNED.search(overall):
        overall = ''
    counts = {s: sum(1 for f in kept if f['status'] == s) for s in STATUSES}
    doc = {
        'title': 'Open Meeting Law: points to check',
        'warning': ('EXPERIMENTAL AND UNLISTED. Read by a language model from the published record; every '
                    'quotation is checked verbatim against its source, and a point whose quotes are not '
                    'is dropped. ' + DISCLAIMER),
        'disclaimer': DISCLAIMER,
        'board': ctx['board'], 'board_slug': board, 'date': date, 'video_id': ctx['video_id'],
        'video_url': ctx['video_url'], 'agenda_url': ctx['agenda_url'], 'minutes_url': ctx['minutes_url'],
        'agenda_text_url': ctx['agenda_text_url'], 'minutes_text_url': ctx['minutes_text_url'],
        'our_minutes_page': '/meeting-minutes/%s/%s-%s' % (board, date, ctx['video_id']),
        'overall': overall,
        'counts': counts,
        'findings': kept,
        'dropped': dropped,
        'cannot_see': CANNOT_SEE,
        'statuses': {
            'clear from the record': 'the published record by itself settles this point',
            'possible — needs checking': 'the record suggests a question that something unpublished could answer',
            'cannot tell from what is published': 'the record is silent on something the law requires',
        },
        'notice_arithmetic': ctx['notice'],
        'minutes_file_created': ctx['minutes_file_created'],
        'inputs': ctx['inputs'], 'law_inputs': ctx['law_inputs'],
        'written': {'by': 'scripts/oml_review.py', 'model': MODEL,
                    'at': dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'), 'cost_usd': cost},
    }
    write_json(out_path(board, date, ctx['video_id']), doc)
    write_json(pub_path(board, date, ctx['video_id']), doc)
    print('wrote %s: %d finding(s) kept, %d dropped; %s' % (
        rel(out_path(board, date, ctx['video_id'])), len(kept), len(dropped),
        ', '.join('%d %s' % (v, k) for k, v in counts.items())))
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
                elif e['source'] in ('agenda', 'minutes'):
                    if not in_text(e['quote'], texts[e['source'] + '_text']):
                        bad.append('%s: %s quote not verbatim (%s)' % (rel(p), e['source'], f['title']))
            for k in ('title', 'summary', 'settle'):
                if BANNED.search(f.get(k, '')):
                    bad.append('%s: reserved word in %s (%s)' % (rel(p), k, f['title']))
            if f['status'] not in STATUSES:
                bad.append('%s: unknown status %r' % (rel(p), f['status']))
        pp = pub_path(doc['board_slug'], doc['date'], doc['video_id'])
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
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    if a.check:
        return check()
    if not (a.board and a.date):
        ap.error('board and date, or --check')
    return review(a.board, a.date, a.dry_run)


if __name__ == '__main__':
    sys.exit(main())
