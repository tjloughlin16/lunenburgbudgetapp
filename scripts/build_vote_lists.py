#!/usr/bin/env python3
"""EVERY VOTE, ONE LIST PER BODY -- Town Meeting's articles, and every board's motions.

    python3 scripts/build_vote_lists.py            # write the payloads
    python3 scripts/build_vote_lists.py --check    # ...and fail if any is stale

Writes  fy28/public/data/town-meeting-votes.json   every article of every Town Meeting found
        fy28/public/data/votes/<board>.json        every vote of one board, by meeting

No model. Deterministic. Reads only what other generators already wrote:

  * TOWN MEETING. sources/data/town-meetings.csv and warrant-articles.csv (build_town_meetings.py
    -- the register and its articles, each result labelled by its record), plus the Town
    Clerk's rows in town-meeting-votes.csv that the register leaves UNPLACED because the annual
    report prints them under a heading with no date (build_town_meetings.py says why it will not
    guess the date). Those are listed here as their own meetings, "date not printed", so "every
    vote" does not quietly lose 38 of them.
  * BOARDS. fy28/public/data/boards.json, the join build_boards.py makes of the town's minutes
    (sources/data/official-votes/) and our minutes of the recordings. The join lives THERE and
    nowhere else; this only regroups it by meeting and fiscal year for a searchable page. The
    per-FY record counts read sources/data/meeting-register.csv (build_meeting_register.py).

TJ, 23 October 2026: "a single page that lists all town meeting votes, ever. and easily
searchable and findable by FY" -- then "a very simple 'All Votes' per board too, with the same
search mechanisms" -- and then: be explicit, per fiscal year, about whether we hold the record
needed to be accurate. So every fiscal year carries a coverage line computed from the data, and
every vote whose only record is our minutes of a recording carries a plain-words label saying so.

THE FISCAL YEAR. Massachusetts runs 1 July to 30 June, named for the year it ends. A vote's `fy`
is the fiscal year IN WHICH THE MEETING WAS HELD -- so the May 2025 Annual Town Meeting is FY2025
although it adopts the FY2026 budget. Where an article's own title names a fiscal year ("Set the
FY2014 general operating budget"), that is carried as `names_fy`, read off the words and nothing
else. For the Clerk's undated rows the meeting's fiscal year cannot be computed, so `fy` is the
fiscal year of the annual report that prints them and the row says so (`fy_basis`).

A QUOTE IS SHOWN AS VERBATIM ONLY WHERE IT IS. The Clerk's quotes were transcribed by a model
from the annual report's text layer; each is looked for in that document (case, whitespace, curly
quotes and a hyphen broken across a line forgiven -- the text layer splits "t o appropriate").
One that is not found is shown as the extractor's reading, never as the Clerk's words. A result
from our minutes is a motion AS HEARD on the recording, labelled so, and is never a quote.
"""
import argparse
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
OUT_TM = os.path.join(PUB, 'town-meeting-votes.json')
OUT_BOARDS = os.path.join(PUB, 'votes')
BOARDS_JSON = os.path.join(PUB, 'boards.json')
REGISTER = os.path.join(DATA, 'meeting-register.csv')

MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
          'October', 'November', 'December']

# The result words as the register spells them, and the Clerk's extract's own spellings mapped
# onto them. `not yet voted` and `no result held` are ours: a stage with no result held.
RESULT_ORDER = ['passed', 'amended and passed', 'failed', 'passed over', 'indefinitely postponed',
                'postponed', 'no action', 'kept off the warrant', 'not clear in the record',
                'not yet voted', 'no result held', 'not recorded']
CLERK_WORD = {'passed': 'passed', 'failed': 'failed', 'passed_over': 'passed over',
              'amended_and_passed': 'amended and passed', 'unclear': 'not clear in the record',
              'indefinitely_postponed': 'indefinitely postponed', 'no_action': 'no action'}
BASIS = {
    'clerk': "the Town Clerk's printed record in the annual town report -- the official record",
    'ours': 'our reading of the meeting video, from a machine transcript -- not an official record, and may be unreliable',
    'none': 'we have not found the result; each article says why',
    'minutes': "the board's own minutes, as the town posted them -- the official record",
    'both': "the board's own minutes, matched to the same vote in the video",
    'recording': 'our reading of the meeting video, from a machine transcript -- not an official record, and may be unreliable',
}

# THE SOURCE CHIPS (TJ, 23 October 2026). Every vote shows, in at most two chips of one to three
# words, the record it SHOULD rest on and whether we have it -- "Clerk's record ✓" or "Clerk's
# record — not yet" -- and a "Video" chip where the result shown comes from our reading of the
# meeting video. One sentence in the expansion says the same thing in full. verify_vote_lists.py
# recomputes both from the sources.
TICK = '\u2713'
WRONG = 'this result is from our reading of the meeting video and may be wrong'


def chip(text, tone, href=''):
    """tone: 'ok' (the record, held), 'caution' (expected and not available, or our reading of the
    video standing in for it), 'neutral' (the video, beside a record we do have)."""
    return {'text': text, 'tone': tone, 'href': href}


def first_href(links, prefix):
    return next((l['href'] for l in links if l['href'].startswith(prefix)), '')


def tm_source(v, y, held, upcoming):
    """(chips, sentence) for one Town Meeting article; y is the report that prints its Clerk's record."""
    clerk_href = first_href(v['links'], '/docs/town-annual-reports/')
    video = first_href(v['links'], 'https://www.youtube.com/')
    if v['basis'] == 'clerk':
        page = re.search(r'#page=(\d+)', clerk_href)
        return ([chip("Clerk's record " + TICK, 'ok', clerk_href)],
                "From the Town Clerk's record in the FY%d annual town report%s." % (
                    y, ', p.%s' % page.group(1) if page else ''))
    if upcoming:
        return ([chip('Not voted yet', 'caution')], v['reason'])
    have = y in held
    c1 = chip("Clerk's record \u2014 " + ('not found' if have else 'not yet'), 'caution',
              docs_href(held[y])[0] if have else '')
    why = ("The Town Clerk's record in the FY%d annual town report doesn't have this article as we read it" % y if have
           else "The Town Clerk's FY%d record isn't published yet" % y)
    if v['basis'] == 'ours':
        return [c1, chip('Video', 'caution', video)], '%s; %s.' % (why, WRONG)
    return [c1], v['reason']


def board_source(v, r):
    """(chips, sentence) for one board vote; r is the meeting's register row ({} if none)."""
    minutes = first_href(v['links'], '/docs/')
    video = first_href(v['links'], 'https://www.youtube.com/')
    if v['basis'] in ('minutes', 'both'):
        chips = [chip('Town minutes ' + TICK, 'ok', minutes)]
        if v['basis'] == 'both' and video:
            chips.append(chip('Video', 'neutral', video))
        return chips, ("From the town's minutes of this meeting" +
                       ('; matched to the same vote in the video.' if v['basis'] == 'both' else '.'))
    if not r:
        state, why = 'unknown', "We don't know whether the town posted minutes for this meeting"
    elif r.get('official_votes_path'):
        state, why = 'vote absent', "The town's minutes don't record this vote as we heard it"
    elif r.get('minutes') == '1':
        state, why = 'not read yet', "The town's minutes are posted but we haven't read them yet"
    else:
        state, why = 'not yet', "The town hasn't posted minutes for this meeting"
    return ([chip('Town minutes \u2014 ' + state, 'caution', r.get('minutes_url') or ''),
             chip('Video', 'caution', video)], '%s; %s.' % (why, WRONG))


def read_csv(p):
    return list(csv.DictReader(open(p, newline='', encoding='utf-8'))) if os.path.exists(p) else []


def plain_fy(date):
    y = int(date[:4])
    return y + 1 if date[5:7] >= '07' else y


def pretty(d):
    return '%d %s %s' % (int(d[8:10]), MONTHS[int(d[5:7]) - 1], d[:4])


def squash(s):
    return re.sub(r'\s+', ' ', s or '').strip()


def loose(s):
    """The comparison key for "is this quote in that document": case, ALL whitespace, curly
    quotes and dashes forgiven. Nothing else -- a different word is a different quote."""
    s = (s or '').lower()
    s = re.sub(r'[‘’‛′`´‟“”"\']', "'", s)
    s = re.sub(r'[–—‐]', '-', s)
    return re.sub(r'\s+', '', s)


_TEXT = {}


def doc_keys(path):
    """Both loose keys of one document: as extracted, and with line-broken hyphens rejoined."""
    if path not in _TEXT:
        full = os.path.join(ROOT, path)
        t = open(full, encoding='utf-8', errors='replace').read() if os.path.exists(full) else ''
        _TEXT[path] = (loose(t), loose(re.sub(r'-[ \t]*\n\s*', '', t)))
    return _TEXT[path]


def verbatim_in(quote, path):
    k = loose(quote)
    a, b = doc_keys(path)
    return bool(k) and (k in a or k in b)


# --- where a sources/ path is served, and the publisher's own address -------------------------

def catalogue():
    """{text or local path: (local document path, publisher's url)} from every sources/*/index.csv."""
    out = {}
    for idx in sorted(glob.glob(os.path.join(ROOT, 'sources', '*', 'index.csv'))):
        for r in read_csv(idx):
            local = r.get('local') or ''
            if not local:
                continue
            up = (r.get('upstream') or '').split()
            for k in (local, r.get('text') or ''):
                if k:
                    out.setdefault(k, (local, up[0] if up else ''))
    return out


CAT = None


def docs_href(path, page=None):
    """The /docs/ address of the DOCUMENT behind a sources/ path (a text file maps to the PDF it
    was read from), with #page=N; and the publisher's url. ('', '') if it is not catalogued."""
    local, town = CAT.get(path, ('', ''))
    if not local:
        return '', ''
    href = '/docs/' + local[len('sources/'):]
    return (href + ('#page=%s' % page if page else '')), town


def hms(t):
    t = int(t)
    return ('%d:%02d:%02d' % (t // 3600, t % 3600 // 60, t % 60)) if t >= 3600 else ('%d:%02d' % (t // 60, t % 60))


def video_label(url, t=None):
    """'Video at 1:23:45' off the &t=Ns the link itself carries, or the t given."""
    m = re.search(r'[?&]t=(\d+)s?', url or '')
    t = t if t is not None else (int(m.group(1)) if m else None)
    return 'Video at %s' % hms(t) if t is not None else 'Video (whole meeting)'


def split_ref(ref):
    """'sources/x.txt p.81' -> ('sources/x.txt', '81')."""
    m = re.match(r'(sources/\S+)(?: p\.(\d+))?$', ref or '')
    return (m.group(1), m.group(2)) if m else ('', None)


def doc_label(path):
    b = os.path.basename(path)
    m = re.search(r'fy-(\d{4})-annual-town-report', b)
    if m:
        return 'FY%s annual report' % m.group(1)
    if 'booklet' in b or 'warrant' in b:
        return 'the warrant'
    return b


FY_IN = re.compile(r'\bFY\s?(\d{4}|\d{2})\b|\bfiscal\s+year\s+(\d{4})\b', re.I)


def names_fy(text):
    out = []
    for m in FY_IN.finditer(text or ''):
        y = m.group(1) or m.group(2)
        y = int(y) if len(y) == 4 else 2000 + int(y)
        if 1990 < y < 2040 and y not in out:
            out.append(y)
    return out


def clean_amount(a, words):
    """The register's amount, with the trailing comma its pattern keeps ("$12,000,") dropped. A
    sum the text layer split ("$105, 975.36") is re-read from the warrant's own words."""
    a = (a or '').rstrip(',')
    if a and words:
        m = re.search(re.escape(a) + r',\s(\d{3}(?:\.\d{2})?)\b', words)
        if m:
            a = a + ',' + m.group(1)
    return a


# =========================================================================================
# TOWN MEETING
# =========================================================================================

def rec_chip(who, text, ref):
    if not text:
        return None
    path, page = split_ref(ref)
    if not path:
        return {'who': who, 'text': text, 'ref': ref, 'href': ''}
    return {'who': who, 'text': text, 'href': docs_href(path, page)[0],
            'ref': '%s p.%s' % (doc_label(path), page) if page else doc_label(path)}


def our_minutes_page(meeting_date, video_url):
    m = re.search(r'v=([\w-]+)', video_url or '')
    if not m:
        return ''
    p = os.path.join(DATA, 'recording-minutes', 'town-meeting', '%s-%s.json' % (meeting_date, m.group(1)))
    return '/meeting-minutes/town-meeting/%s-%s' % (meeting_date, m.group(1)) if os.path.exists(p) else ''


# WHICH REPORT PRINTS A MEETING'S CLERK'S RECORD. Observed, not assumed: every one of the 445 dated
# rows in town-meeting-votes.csv sits in the annual report labelled with the CALENDAR year of the
# meeting (a November Special is in that year's report, not the next). So a meeting with no Clerk's
# row is looked for in the report of its own calendar year.
def expected_report(date):
    return int(date[:4])


# What a reader sees for a result, in plain words (TJ, 23 October 2026: "i dont know what 'no
# result held' means"). The internal key stays; this is the label.
RESULT_LABEL = {'no result held': 'Result not found', 'not yet voted': 'Not voted yet',
                'not clear in the record': "The record doesn't say", 'not recorded': "The record doesn't say",
                'kept off the warrant': 'Kept off the warrant'}


def no_result_reason(m, a, held):
    """Why an article has no result, from the data, in a sentence a resident can read."""
    if m['status'] == 'upcoming':
        return 'Not voted yet -- the meeting is on %s.' % pretty(m['date'])
    if a['stage'] == 'kept off':
        return 'The Select Board kept this off the warrant, so Town Meeting did not vote on it.'
    y = expected_report(m['date'])
    if y not in held:
        return "Result not found -- we don't have the FY%d annual town report yet, where the Town Clerk prints it." % y
    return ("Result not found -- we haven't found this article in the Town Clerk's pages of the FY%d annual "
            "town report. It may be printed there; the report is linked above." % y)


def article_row(m, a, held):
    upcoming = m['status'] == 'upcoming'
    reason = ''
    if a['result']:
        result = CLERK_WORD.get(a['result'], a['result'])
        basis = 'clerk' if a['result_basis'] == 'official' else 'ours'
        if result == 'not clear in the record':
            reason = "The record doesn't say what was decided; the vote is linked so you can check it."
    else:
        result = 'kept off the warrant' if a['stage'] == 'kept off' else ('not yet voted' if upcoming else 'no result held')
        basis = 'none'
        reason = no_result_reason(m, a, held)
    links, quote, quote_kind, record_doc = [], '', '', ''
    if basis == 'clerk':
        path, page = split_ref(a['result_ref'])
        href, town = docs_href(path, page)
        links.append({'label': "Town Clerk's record, %s, p.%s" % (doc_label(path), page), 'href': href})
        if town:
            links.append({'label': "on the town's site", 'href': town})
        quote = a['result_quote']
        quote_kind = 'verbatim' if verbatim_in(quote, path) else 'not verbatim'
        record_doc = path
    elif basis == 'ours':
        links.append({'label': video_label(a['result_ref']), 'href': a['result_ref']})
        mp = our_minutes_page(m['date'], a['result_ref'])
        if mp:
            links.append({'label': 'Our minutes of the video', 'href': mp})
        quote, quote_kind = a['result_quote'], 'as heard'
    if a['details_doc']:
        href, _ = docs_href(a['details_doc'], a['details_page'])
        links.append({'label': 'Warrant, p.%s' % a['details_page'] if a['details_page'] else 'Warrant',
                      'href': href})
        if a['details_town_url']:
            links.append({'label': "warrant on the town's site", 'href': a['details_town_url']})
    if a['thread']:
        links.append({'label': 'its thread', 'href': '/threads/' + a['thread']})
    recs = [x for x in (rec_chip('Finance Committee', a['fincom_rec'], a['fincom_ref']),
                        rec_chip('Select Board', a['sb_rec'], a['sb_ref'])) if x]
    title = a['title'] or (a['warrant_words'][:140] if a['warrant_words'] else '')
    return {'id': '%s-a%s' % (m['id'], a['article'] or 'x'), 'n': ('Art. %s' % a['article']) if a['article'] else '',
            'title': title, 'title_from': a['title_from'],
            'amount': clean_amount(a['amount'], a['warrant_words']), 'result_amount': a['result_amount'],
            'sponsor': a['sponsor'], 'recs': recs, 'result': result, 'basis': basis,
            'quote': quote, 'quote_kind': quote_kind,
            'words': squash(re.sub(r'===PAGE \d+===(?:\s*\d+\b)?', ' ', a['warrant_words'] or '')),
            'names_fy': names_fy(title + ' ' + (a['warrant_words'] or '')[:300]),
            'flags': [f for f, on in (('amended', a['amended']), ('divided', a['divided']), ('put off', a['put_off'])) if on],
            'note': a['numbered_by'] or '', 'links': links,
            'record_doc': record_doc, 'result_label': RESULT_LABEL.get(result, result), 'reason': reason}


def kind_label(k):
    return {'annual': 'Annual Town Meeting', 'special': 'Special Town Meeting'}.get(k, 'Town Meeting')


def town_meeting():
    meetings = read_csv(os.path.join(DATA, 'town-meetings.csv'))
    arts = collections.defaultdict(list)
    for a in read_csv(os.path.join(DATA, 'warrant-articles.csv')):
        arts[a['meeting']].append(a)
    held = reports_held()
    groups = []
    for m in meetings:
        rows = sorted(arts[m['id']], key=lambda a: (a['article'] == '', int(a['article'] or 0), a['title']))
        links = []
        if m['warrant_doc']:
            links.append({'label': 'Warrant', 'href': docs_href(m['warrant_doc'])[0]})
        if m['warrant_town_url']:
            links.append({'label': "warrant on the town's site", 'href': m['warrant_town_url']})
        rep_doc = held.get(expected_report(m['date']))
        if rep_doc and m['status'] != 'upcoming':
            h, town = docs_href(rep_doc)
            links.append({'label': 'FY%d annual town report' % expected_report(m['date']), 'href': h})
        status = {'held': '', 'upcoming': 'Upcoming -- not voted yet',
                  'called; no later record': 'Called by the Select Board; we have no record that it was held'}.get(
                      m['status'], m['status'])
        note = m['date_conflict'] or ('We do not have the warrant for this meeting; the articles come from the '
                                      "Town Clerk's record or our minutes of the video." if not m['warrant_doc'] and rows else '')
        groups.append({'id': m['id'], 'kind': m['kind'], 'date': m['date'], 'date_printed': True,
                       'label': '%s, %s' % (kind_label(m['kind']), pretty(m['date'])),
                       'fy': plain_fy(m['date']), 'fy_basis': 'held in FY%d' % plain_fy(m['date']),
                       'status': status, 'note': note,
                       'links': links, 'votes': [article_row(m, a, held) for a in rows]})
    # THE CLERK'S UNDATED ROWS -- runs of one report, one kind, split where the numbering restarts.
    clerk = [r for r in read_csv(os.path.join(DATA, 'town-meeting-votes.csv')) if not r['meeting_date']]
    runs, prev = [], None
    for r in sorted(clerk, key=lambda r: (r['source_doc'], r['meeting'], int(r['page'] or 0), int(r['article'] or 0))):
        key = (r['source_doc'], r['meeting'])
        if not runs or prev[0] != key or int(r['article'] or 0) <= prev[1]:
            runs.append([])
        runs[-1].append(r)
        prev = (key, int(r['article'] or 0))
    for run in runs:
        r0 = run[0]
        pages = sorted({int(r['page']) for r in run})
        gid = 'undated-fy%s-%s-p%d' % (r0['fy'], r0['meeting'], pages[0])
        href, town = docs_href(r0['source_doc'], pages[0])
        votes = []
        for r in run:
            path = r['source_doc']
            h, _ = docs_href(path, r['page'])
            recs = [x for x in (rec_chip('Finance Committee', r['fincom'], '%s p.%s' % (path, r['page'])),
                                rec_chip('Select Board', r['select_board'], '%s p.%s' % (path, r['page']))) if x]
            links = [{'label': "Town Clerk's record, %s, p.%s" % (doc_label(path), r['page']), 'href': h}]
            if town:
                links.append({'label': "on the town's site", 'href': town})
            votes.append({'id': '%s-a%s' % (gid, r['article']), 'n': 'Art. %s' % r['article'], 'title': r['subject'],
                          'title_from': "the Town Clerk's record", 'amount': r['amount_as_printed'], 'result_amount': '',
                          'sponsor': '', 'recs': recs, 'result': CLERK_WORD.get(r['result'], r['result']),
                          'basis': 'clerk', 'quote': r['quote'],
                          'quote_kind': 'verbatim' if verbatim_in(r['quote'], path) else 'not verbatim',
                          'words': '', 'names_fy': names_fy(r['subject']), 'flags': [], 'note': '', 'links': links,
                          'record_doc': path,
                          'result_label': RESULT_LABEL.get(CLERK_WORD.get(r['result'], r['result']), CLERK_WORD.get(r['result'], r['result'])),
                          'reason': "The record doesn't say what was decided." if r['result'] == 'unclear' else ''})
        groups.append({'id': gid, 'kind': r0['meeting'], 'date': '', 'date_printed': False,
                       'label': '%s printed in the %s, p.%s -- date not printed' % (
                           kind_label(r0['meeting']), doc_label(r0['source_doc']),
                           '-'.join(str(p) for p in (pages[0], pages[-1])) if len(pages) > 1 else pages[0]),
                       'fy': int(r0['fy']),
                       'fy_basis': "the fiscal year of the annual report that prints it; the Clerk prints no date beside "
                                   "these votes, so the meeting may fall in a later year",
                       'status': '', 'note': 'The annual report prints these votes without a meeting date, so we do not guess one.',
                       'links': [{'label': doc_label(r0['source_doc']), 'href': href}] + (
                           [{'label': "the town's copy", 'href': town}] if town else []),
                       'votes': votes})
    for g in groups:
        up = g['status'].startswith('Upcoming')
        for v in g['votes']:
            got = {int(x) for x in re.findall(r'fy-(\d{4})-annual-town-report', v['record_doc'] or '')}
            y = got.pop() if got else (expected_report(g['date']) if g['date'] else g['fy'])
            v['chips'], v['basis_note'] = tm_source(v, y, held, up and v['result'] in ('not yet voted', 'kept off the warrant'))
    # newest first; an undated run sorts at the end of its fiscal year's dated meetings
    groups.sort(key=lambda g: (g['fy'], g['date'] or '%d-00' % g['fy']), reverse=True)
    return groups


def summarise(groups, basis_keys):
    votes = [v for g in groups for v in g['votes']]
    res = collections.Counter(v['result'] for v in votes)
    order = {k: i for i, k in enumerate(RESULT_ORDER)}
    return {
        'results': [{'key': k, 'n': n, 'label': RESULT_LABEL.get(k, k)} for k, n in sorted(res.items(), key=lambda kv: (order.get(kv[0], 99), kv[0]))],
        'fys': sorted({g['fy'] for g in groups}, reverse=True),
        'by_basis': {k: sum(1 for v in votes if v['basis'] == k) for k in basis_keys},
        'votes': len(votes),
        'meetings': len(groups),
    }


def reports_held():
    """{fy: annual town report document} for every FY the archive holds a report for."""
    out = {}
    for r in read_csv(os.path.join(ROOT, 'sources', 'town-annual-reports', 'index.csv')):
        m = re.match(r'FY\s?(\d{4}) Annual Town Report', squash(r['label']).strip('"'))
        if m and r['local']:
            out.setdefault(int(m.group(1)), r['local'])
    return out


def sentence(parts):
    s = '; '.join(p for p in parts if p)
    return (s[0].upper() + s[1:] + '.') if s else ''


def tm_fy_coverage(groups):
    """One line per fiscal year: is the Clerk's printed record -- the authoritative one -- what
    these results rest on? Computed from the rows and the archive's own catalogue, never typed.
    A meeting's Clerk record is looked for in the report(s) that print its rows, or, for a meeting
    with none, the report of the fiscal year it was held in."""
    held = reports_held()
    # A PAGE REGISTERED UNREADABLE COUNTS ONLY IF IT FALLS AMONG THE CLERK'S PAGES of that report --
    # page-blocked.csv is the financial pages' register, and a blurry receipts page says nothing
    # about whether the Town Meeting proceedings could be read.
    span = collections.defaultdict(list)
    for r in read_csv(os.path.join(DATA, 'town-meeting-votes.csv')):
        span[int(r['fy'])].append(int(r['page']))
    blocked = collections.Counter(int(r['fy']) for r in read_csv(os.path.join(DATA, 'page-blocked.csv'))
                                  if span[int(r['fy'])] and min(span[int(r['fy'])]) <= int(r['page']) <= max(span[int(r['fy'])]))
    def report_fy(path):
        m = re.search(r'fy-(\d{4})-annual-town-report', path)
        return int(m.group(1)) if m else None
    out = {}
    for fy in sorted({g['fy'] for g in groups}):
        gs = [g for g in groups if g['fy'] == fy]
        vs = [v for g in gs for v in g['votes'] if v['result'] not in ('not yet voted', 'kept off the warrant')]
        upcoming = sum(1 for g in gs for v in g['votes'] if v['result'] in ('not yet voted', 'kept off the warrant'))
        n, clerk = len(vs), sum(1 for v in vs if v['basis'] == 'clerk')
        ours = sum(1 for v in vs if v['basis'] == 'ours')
        none = n - clerk - ours
        # the report(s) that print this year's Clerk's record; a meeting with none looks to its own FY's
        reps = set()
        for g in gs:
            got = {report_fy(v['record_doc']) for v in g['votes'] if v['record_doc']} - {None}
            reps |= got or ({expected_report(g['date'])} if g['votes'] and g['date'] else set())
        reps = sorted(reps)
        reps_txt = ' and '.join('FY%d' % f for f in reps) + (' annual town reports' if len(reps) > 1 else ' annual town report')
        rest = [('%d from our reading of the meeting video, which may be unreliable' % ours) if ours else '',
                ('%d whose result we have not found' % none) if none else '',
                ('%d on a warrant not yet voted' % upcoming) if upcoming else '']
        if n and clerk == n:
            status = 'clerk'
            text = "Town Clerk's record: all %d articles voted, from the %s. %s" % (
                n, reps_txt, sentence(rest[2:]))
        else:
            status = 'part' if clerk else 'none'
            have = [f for f in reps if f in held]
            missing = [f for f in reps if f not in held]
            text = ("Town Clerk's record: %d of %d articles voted%s. " % (
                        clerk, n, (', from the %s' % ' and '.join('FY%d' % f for f in have) +
                                   (' annual town reports' if len(have) > 1 else ' annual town report')) if clerk else '')
                    + ("We don't have the %s annual town report%s yet, where the Clerk prints %s. "
                       % (' or '.join('FY%d' % f for f in missing), 's' if len(missing) > 1 else '',
                          'the rest' if clerk else 'them') if missing else '')
                    + sentence(rest))
            nb = sum(blocked[f] for f in have)
            if nb:
                text += ' %d of the Town Meeting pages could not be read (page-blocked.csv).' % nb
        missing = [f for f in reps if f not in held]
        if status == 'clerk':
            short = "Clerk's record %s for all %d articles" % (TICK, n)
        elif clerk:
            short = "Clerk's record for %d of %d articles" % (clerk, n)
        else:
            short = "Clerk's record not yet published" if missing else "Clerk's record not found"
        if clerk and missing:
            short += ' \u00b7 FY%d record not yet published' % missing[-1]
        out[str(fy)] = {'status': status, 'short': short, 'text': squash(text), 'articles': n, 'clerk': clerk, 'ours': ours,
                        'none': none, 'upcoming': upcoming, 'reports': reps,
                        'tag': {'clerk': '', 'part': "partly from the Clerk's record",
                                'none': "not from the Clerk's record"}[status]}
    return out


def tm_payload():
    groups = town_meeting()
    s = summarise(groups, ['clerk', 'ours', 'none'])
    held = [g for g in groups if g['date']]
    first = min(g['date'] for g in held)
    last = max(g['date'] for g in held)
    undated = [g for g in groups if not g['date']]
    clerk_fys = sorted({int(r['fy']) for r in read_csv(os.path.join(DATA, 'town-meeting-votes.csv'))})
    notverb = sum(1 for g in groups for v in g['votes'] if v['quote_kind'] == 'not verbatim')
    coverage = [
        'Every Town Meeting the archive finds, %s to %s: %d held, %d upcoming, %d called with no later record, and '
        '%d more whose votes the Clerk printed with no date (FY%s) -- %d articles in all.' % (
            pretty(first), pretty(last), sum(1 for g in held if not g['status']),
            sum(1 for g in held if g['status'].startswith('Upcoming')),
            sum(1 for g in held if g['status'] and not g['status'].startswith('Upcoming')), len(undated),
            ', FY'.join(sorted({str(g['fy']) for g in undated})), s['votes']),
        "Results: %d from the Town Clerk's printed record in the annual town reports FY%d-FY%d; %d from our reading "
        "of the meeting video (may be unreliable), where we do not have the Clerk's record of the article; %d whose "
        "result we have not found -- each says why." % (s['by_basis']['clerk'], clerk_fys[0], clerk_fys[-1], s['by_basis']['ours'],
                          s['by_basis']['none']),
        'Nothing before %s: the archive holds no annual town report before FY%d, so earlier votes are not here.' % (
            pretty(first), min(reports_held())),
    ]
    return {
        'generated_by': 'scripts/build_vote_lists.py -- never edit by hand',
        'title': 'Every Town Meeting vote',
        'standfirst': 'Every warrant article Town Meeting has voted since %s, with what was decided and where it is recorded.' % first[:4],
        'kind': 'town-meeting',
        'coverage': coverage,
        'grain': 'One row per warrant article per meeting. A row is an ARTICLE, not a motion: an amendment voted on '
                 'the floor is folded into the article it amended. Dollar amounts are as the warrant or the Clerk printed '
                 'them; an amount is what was asked or voted, never what was spent.',
        'fy_rule': 'Fiscal years run 1 July to 30 June. A meeting is filed under the fiscal year it was HELD in: the '
                   'May Annual Town Meeting falls in the year before the budget it adopts. Where an article names a '
                   'fiscal year, that is shown beside it.',
        'quote_rule': "Verbatim means found word for word in the cited page. %d of the Clerk's quotes were not, and are "
                      "shown as the extractor's reading. A result from our minutes is a motion as heard on the "
                      "recording, never a quote." % notverb,
        'basis': {k: BASIS[k] for k in ('clerk', 'ours', 'none')},
        'fy_coverage': tm_fy_coverage(groups),
        **s,
        'groups': groups,
    }


# =========================================================================================
# BOARDS
# =========================================================================================

def register():
    """{(slug, date): register row} -- every meeting the town noticed or we hold anything for."""
    return {(r['board_slug'], r['date']): r for r in read_csv(REGISTER) if r.get('board_slug') and r.get('date')}


def board_fy_coverage(slug, reg, horizon, groups):
    """Per fiscal year: of the meetings the register knows, how many have the town's minutes READ
    for votes, minutes posted but not read, only our minutes of a recording, or no record we can
    use. A meeting after `horizon` (the last date anything at all was recorded for any board) is
    not yet due a record and is not counted."""
    by = collections.defaultdict(collections.Counter)
    for (s, d), r in reg.items():
        if s != slug or d > horizon:
            continue
        c = by[plain_fy(d)]
        c['meetings'] += 1
        if r['official_votes_path']:
            c['town_read'] += 1
        elif r['minutes'] == '1':
            c['town_unread'] += 1
            if r['our_minutes_path']:
                c['town_unread_ours'] += 1
        elif r['our_minutes_path']:
            c['ours_only'] += 1
        else:
            c['nothing'] += 1
    for g in groups:                          # a voting date the register does not list
        by.setdefault(g['fy'], collections.Counter())
    out = {}
    for fy, c in sorted(by.items()):
        votes = [v for g in groups if g['fy'] == fy for v in g['votes']]
        rec_only = sum(1 for v in votes if v['basis'] == 'recording')
        parts = ['%d meeting%s on the town\'s calendar' % (c['meetings'], '' if c['meetings'] == 1 else 's'),
                 "%d with the town's minutes read" % c['town_read'],
                 ("%d with the town's minutes posted but not yet read (%d of them with our minutes of the video)"
                  % (c['town_unread'], c['town_unread_ours'])) if c['town_unread'] else '',
                 ('%d with only our minutes of the video' % c['ours_only']) if c['ours_only'] else '',
                 ('%d with no record we can use' % c['nothing']) if c['nothing'] else '']
        text = 'FY%d: %s.' % (fy, '; '.join(p for p in parts if p))
        if rec_only:
            text += ' %d vote%s below come only from our reading of the video, which may be unreliable.' % (
                rec_only, '' if rec_only == 1 else 's')
        status = 'clerk' if c['meetings'] and c['town_read'] == c['meetings'] else ('part' if c['town_read'] else 'none')
        short = ('Town minutes read for %d of %d meetings' % (c['town_read'], c['meetings'])) if c['meetings'] else \
            'No meetings on the town\'s calendar'
        out[str(fy)] = {'status': status, 'short': short, 'text': text, 'meetings': c['meetings'], 'town_read': c['town_read'],
                        'town_unread': c['town_unread'], 'town_unread_ours': c['town_unread_ours'],
                        'ours_only': c['ours_only'], 'nothing': c['nothing'], 'recording_only_votes': rec_only,
                        'tag': {'clerk': '', 'part': '', 'none': "no town minutes read"}[status]}
    return out


def board_payloads():
    import build_boards as BB
    d = json.load(open(BOARDS_JSON, encoding='utf-8'))
    reg = register()
    horizon = max(max(r['minutes_first_seen'] or '', r['video_uploaded'] or '', r['our_minutes_written'] or '')
                  for r in reg.values())
    out = {}
    for b in d['boards']:
        if not b['votes']:
            continue
        by_date = collections.defaultdict(list)
        for v in b['votes']:
            by_date[v['date']].append(v)
        groups = []
        for date in sorted(by_date, reverse=True):
            vs = by_date[date]
            r = reg.get((b['slug'], date)) or {}
            links, seen = [], set()
            for v in vs:
                for lab, h in (("Town's minutes", v.get('minutes_doc')), ("minutes on the town's site", v.get('minutes_url')),
                               ('Our minutes of the video', v.get('page')),
                               ('Video (whole meeting)', re.sub(r'&t=\d+s$', '', v.get('video_url') or ''))):
                    if h and h not in seen:
                        seen.add(h)
                        links.append({'label': lab, 'href': h})
            rows = []
            for i, v in enumerate(vs):
                k = BB.outcome_key(v.get('outcome'))[0]
                result = {'passed': 'passed', 'failed': 'failed'}.get(k, 'not recorded')
                vl = []
                if v.get('minutes_doc'):
                    vl.append({'label': "Town's minutes", 'href': v['minutes_doc']})
                if v.get('minutes_url'):
                    vl.append({'label': "on the town's site", 'href': v['minutes_url']})
                if v.get('video_url'):
                    vl.append({'label': video_label(v['video_url'], v.get('t')), 'href': v['video_url']})
                if v.get('page'):
                    vl.append({'label': 'Our minutes of the video', 'href': v['page']})
                rows.append({'id': '%s-%s-%d' % (b['slug'], date, i), 'n': '', 'title': v.get('motion') or '',
                             'result': result, 'result_text': v.get('outcome') or '',
                             'basis': v['source'], 'quote': v.get('quote') or '',
                             'quote_kind': 'verbatim' if v.get('quote') else '',
                             'moved_by': v.get('moved_by') or '', 'seconded_by': v.get('seconded_by') or '',
                             'conflict': v.get('conflict') or '', 'procedural': bool(v.get('procedural')),
                             'links': vl, 'result_label': RESULT_LABEL.get(result, result),
                             'reason': "The record doesn't say how the vote went." if result == 'not recorded' else ''})
                rows[-1]['chips'], rows[-1]['basis_note'] = board_source(rows[-1], r)
            groups.append({'id': '%s-%s' % (b['slug'], date), 'date': date, 'date_printed': True,
                           'label': pretty(date), 'fy': plain_fy(date), 'fy_basis': 'held in FY%d' % plain_fy(date),
                           'status': '', 'note': '', 'links': links, 'votes': rows})
        s = summarise(groups, ['minutes', 'both', 'recording'])
        c = b['counts']
        dates = sorted(by_date)
        coverage = [
            '%s votes at %s meetings, %s to %s (FY%d-FY%d).' % (
                f'{s["votes"]:,}', f'{s["meetings"]:,}', pretty(dates[0]), pretty(dates[-1]), plain_fy(dates[0]), plain_fy(dates[-1])),
            "%s from the board's own minutes (%s of the %s sets the town posted have been read), %s of them matched to "
            "the recording; %s from our minutes of a recording only." % (
                f'{s["by_basis"]["minutes"] + s["by_basis"]["both"]:,}', f'{c["official_votes_read"]:,}', f'{c["minutes"]:,}',
                f'{s["by_basis"]["both"]:,}', f'{s["by_basis"]["recording"]:,}'),
            'A meeting with neither minutes read nor a recording we have written up has no votes here, which is not '
            'the same as no votes taken. Each fiscal year says how many such meetings the register knows of.',
        ]
        out[b['slug']] = {
            'generated_by': "scripts/build_vote_lists.py, from build_boards.py's join -- never edit by hand",
            'title': 'Every %s vote' % b['name'], 'board': b['name'], 'slug': b['slug'], 'kind': 'board',
            'standfirst': 'Every motion the %s voted on that a record we hold shows, newest first.' % b['name'],
            'coverage': coverage,
            'grain': 'One row per motion voted. Procedural votes (minutes, adjournment) are hidden unless asked for.',
            'fy_rule': 'Fiscal years run 1 July to 30 June; a meeting is filed under the fiscal year it was held in.',
            'quote_rule': "A quote is the minutes' own words, checked verbatim when they were read. A vote from the "
                          'recording only is a motion as heard by a language model from captions, never a quote.',
            'basis': {k: BASIS[k] for k in ('minutes', 'both', 'recording')},
            'fy_coverage': board_fy_coverage(b['slug'], reg, horizon, groups),
            'conflicts': c.get('vote_conflicts', 0),
            **s,
            'groups': groups,
        }
    return out


def dashes(x):
    """A reader sees an em dash where these strings are written with ' -- '."""
    if isinstance(x, str):
        return x.replace(' -- ', ' \u2014 ')
    if isinstance(x, list):
        return [dashes(v) for v in x]
    if isinstance(x, dict):
        return {k: (v if k == 'generated_by' else dashes(v)) for k, v in x.items()}
    return x


def outputs():
    global CAT
    CAT = catalogue()
    outs = {OUT_TM: json.dumps(dashes(tm_payload()), indent=1, ensure_ascii=False, sort_keys=True) + '\n'}
    for slug, p in board_payloads().items():
        p = dashes(p)
        outs[os.path.join(OUT_BOARDS, slug + '.json')] = json.dumps(p, ensure_ascii=False, sort_keys=True,
                                                                     separators=(',', ':')) + '\n'
    return outs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    outs = outputs()
    extra = [p for p in glob.glob(os.path.join(OUT_BOARDS, '*.json')) if p not in outs]
    if a.check:
        stale = [p for p, body in outs.items() if not os.path.exists(p) or open(p, encoding='utf-8').read() != body]
        if stale or extra:
            raise SystemExit('STALE: %s%s -- run build_vote_lists.py' % (
                ', '.join(os.path.relpath(p, ROOT) for p in stale[:5]) + (' and %d more' % (len(stale) - 5) if len(stale) > 5 else ''),
                (' ; no longer produced: ' + ', '.join(os.path.relpath(p, ROOT) for p in extra)) if extra else ''))
        print('ok -- %d payloads reproduce' % len(outs))
        return
    os.makedirs(OUT_BOARDS, exist_ok=True)
    for p, body in outs.items():
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            fh.write(body)
        os.replace(tmp, p)
    for p in extra:
        os.remove(p)
    tm = json.loads(outs[OUT_TM])
    print('town meeting: %d meetings, %d articles, FY%d-FY%d; by basis %s' % (
        tm['meetings'], tm['votes'], tm['fys'][-1], tm['fys'][0], tm['by_basis']))
    for line in tm['coverage']:
        print('  ' + line)
    for fy, c in sorted(tm['fy_coverage'].items()):
        print('  FY%s %-6s %s' % (fy, c['status'], c['text']))
    print('boards: %d payloads, %d votes' % (len(outs) - 1, sum(json.loads(b)['votes'] for p, b in outs.items() if p != OUT_TM)))


if __name__ == '__main__':
    main()
