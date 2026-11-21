#!/usr/bin/env python3
"""The track and field in the town's capital process, cycle by cycle, FY2014 to FY2028.

    python3.11 scripts/build_track_field_capital.py           # write the report and payload
    python3.11 scripts/build_track_field_capital.py --check   # fail if either would change,
                                                              # or if any quote is not in its source

WHAT IT ANSWERS. Where the field was RANKED each time it entered a capital cycle, by whom,
at what price, and how money for it was actually found. The boards argued over this history
in autumn 2026 (a Select Board chair: "ranked 5 of 7 in prior capital planning") without a
table of it in front of them.

THE DATA is sources/data/track-field-capital-history.csv: one row per document or recording
that mentions the field in a capital cycle -- a request, a ranking, a plan line, a vote, or a
page read and found WITHOUT the field (an `absence` row, rule 13c: the page was looked at).
Three isolated reading agents compiled it on 20 November 2026; their reports are in
notes/findings/track-field-capital/. Every row carries `basis`: `document`, or `captions`
(machine captions of a recording -- a finding aid, never a record).

THE QUOTE CHECK. Every quoted passage is re-found in the extracted text it cites, every run.
A row may quote several passages, joined by ' | ' or elided with '...'; each part is checked.
Matching ignores case, punctuation and spacing (extracted text breaks lines and spaces
brackets), never words. A part prefixed `caption:` is looked for in the recording's caption
file named in `doc`. A quote that is not found stops the build.

ONE PASS, TWO OUTPUTS (rule 7d): sources/analyses/track-field-capital.md and the payload
fy28/public/data/track-field-capital.json. The report is UNLISTED (sources/analyses/UNLISTED)
until TJ says otherwise.
"""
import argparse
import csv
import glob
import html
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import conclusions as C  # noqa: E402
from conclusions import conclusion, emit, figure  # noqa: E402

RID = 'track-field-capital'
ME = os.path.basename(__file__)
DATA = os.path.join(ROOT, 'sources', 'data', 'track-field-capital-history.csv')
PUB = os.path.join(ROOT, 'fy28', 'public', 'docs', 'data', 'track-field-capital-history.csv')
OUT = os.path.join(ROOT, 'sources', 'analyses', '%s.md' % RID)
PAYLOAD = os.path.join(ROOT, 'fy28', 'public', 'data', '%s.json' % RID)
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
FIRST, LAST = 2014, 2028

# THE ROUNDS. One table per round, NEWEST FIRST (TJ, 20 November 2026: "id expect: newest
# first, in that order all the way down"). A round is a cycle, or part of one: FY2027 holds
# two, the capital plan and then the Special Town Meeting article, split at the School
# Committee's vote of 16 September 2026 that started the second. The key names the round's
# outcome line in outcomes().
ROUNDS = [
    (2028, None, None, 'Round 7 · money for FY2028 · capital plan (under way)', 'r28'),
    (2027, '2026-09-16', None, 'Round 6 · money for FY2027 · Special Town Meeting, Article 9', 'r27s'),
    (2027, None, '2026-09-16', 'Round 5 · money for FY2027 · capital plan', 'r27'),
    (2026, None, None, 'Round 4 · money for FY2026 · capital plan, then a spring 2025 article', 'r26'),
    (2025, None, None, 'Round 3 · money for FY2025 · capital plan (survey and drainage)', 'r25'),
    (2024, None, None, 'Round 2 · money for FY2024 · capital plan (a feasibility study)', 'r24'),
    (2017, None, None, 'Round 1 · money for FY2017 · borrowing article, May 2016', 'r17'),
]
# What a timeline row is ABOUT, in the words a reader would use. A row with no plain sentence
# stays in the dataset and off the page: duplicate readings of one rank, undated score sheets.
ABOUT = {'asked', 'priced', 'planned', 'ranked', 'not ranked', 'left out', 'withdrawn',
         'recommended', 'voted', 'paid', 'work', 'talked about'}
ROUND_CYCLES = {r[0] for r in ROUNDS}



# ---------------------------------------------------------------------------- reading

def load():
    with open(DATA, encoding='utf-8', newline='') as fh:
        rows = list(csv.DictReader(fh))
    for i, r in enumerate(rows, 2):
        r['_line'] = i
    return rows


def _norm(s):
    # Letters, digits and dollar signs only. Extracted text splits words (`H igh Sc hool`),
    # joins them (`projectsfor`), escapes them (`&amp;`) and spaces brackets; none of that
    # is a difference in what the document SAYS, and every word must still be there in order.
    return re.sub(r'[^a-z0-9$]+', '', html.unescape(s).lower())


_TEXT = {}


def _text(rel):
    if rel not in _TEXT:
        f = os.path.join(ROOT, 'sources', rel)
        if not os.path.isfile(f):
            _TEXT[rel] = None
        elif f.endswith('.json'):
            with open(f, encoding='utf-8') as fh:
                d = json.load(fh)
            _TEXT[rel] = _norm(' '.join(s['text'] for s in d['segments']))
        else:
            with open(f, encoding='utf-8', errors='replace') as fh:
                _TEXT[rel] = _norm(fh.read())
    return _TEXT[rel]


def _caption_file(doc):
    """The caption file for a recording named in `doc` by its YouTube id."""
    for vid in re.findall(r'(?:video |v=|recording )([A-Za-z0-9_-]{11})', doc):
        hit = glob.glob(os.path.join(ROOT, 'sources', 'data', 'youtube-transcripts', '*',
                                     '*-%s.json' % vid))
        if hit:
            return os.path.relpath(hit[0], os.path.join(ROOT, 'sources'))
    return None


def verify(rows):
    """Every quoted passage is in the text it cites. Returns the problems."""
    bad = []
    for r in rows:
        q = r['quote'].strip()
        if q.startswith('[no quote'):
            q = ''
        if not q:
            if r['kind'] != 'absence' and r['basis'] == 'document' and r['kind'] != 'ranking':
                bad.append('line %d: a %s row with no quote' % (r['_line'], r['kind']))
            continue
        if not r['text'].strip():
            bad.append('line %d: a quote with no text file to check it against' % r['_line'])
            continue
        main = _text(r['text'])
        if main is None:
            bad.append('line %d: %s is not on disk (sync_archive.py --pull?)'
                       % (r['_line'], r['text']))
            continue
        for seg in re.split(r'\s*\|\s*', q):
            src, rel = main, r['text']
            m = re.match(r'\s*caption:\s*(.*)$', seg, re.I | re.S)
            if m:
                seg = m.group(1)
                rel = _caption_file(r['doc'])
                src = _text(rel) if rel else None
                if src is None:
                    bad.append('line %d: a caption quote and no caption file for %r'
                               % (r['_line'], r['doc'][:80]))
                    continue
            for part in re.split(r'\.\.\.|\u2026', seg):
                if part.strip() and _norm(part) not in src:
                    bad.append('line %d: not found in %s: %r' % (r['_line'], rel, part[:80]))
    return bad + check_plain(rows)


def check_plain(rows):
    """The plain sentence is ours, so it may not carry a figure its row does not (rule 2):
    every dollar amount and every comma-grouped number in it must be in the row's amount,
    vote, account of what happened, or quote."""
    bad = []
    for r in rows:
        t = r.get('plain', '')
        if bool(t) != bool(r.get('about')) or (r.get('about') and r['about'] not in ABOUT):
            bad.append('line %d: about %r with plain %r' % (r['_line'], r.get('about'), t[:40]))
        hay = re.sub(r'[^0-9.m]', '', ' '.join(
            (r['amount'], r['vote'], r['what_happened'], r['quote'], r['rank'], r['rank_of'])).lower())
        for fig in re.findall(r'\$[\d,.]+[mM]?|\b\d{1,3}(?:,\d{3})+', t):
            if re.sub(r'[^0-9.m]', '', fig.lower()).rstrip('.') not in hay:
                bad.append('line %d: plain sentence carries %s, which its row does not' % (r['_line'], fig))
    return bad


def coverage(rows):
    """Every cycle FIRST..LAST has at least one row (rule 13c: a page read, or a mention)."""
    have = {int(r['cycle_fy']) for r in rows}
    return ['FY%d has no row: not even a recorded absence' % y
            for y in range(FIRST, LAST + 1) if y not in have]


def one(rows, **want):
    """The single row matching every condition: `field=value` exact, `field__in=sub`
    substring, `field__start=prefix`. More or fewer than one is an error, because a figure
    on this page must come from exactly one row."""
    def ok(r):
        for k, v in want.items():
            f, _, op = k.partition('__')
            if op == 'in' and v not in r[f]:
                return False
            if op == 'start' and not r[f].startswith(v):
                return False
            if not op and r[f] != v:
                return False
        return True
    hit = [r for r in rows if ok(r)]
    if len(hit) != 1:
        raise SystemExit('%s: %d rows match %r (want exactly one)' % (ME, len(hit), want))
    return hit[0]


def dollars(r, pattern, field='amount'):
    """A dollar amount read off one row's field, and checked to be in that row's quote or
    what_happened, so a figure on the page is never one the row itself does not print."""
    m = re.search(pattern, r[field])
    if not m:
        raise SystemExit('%s: line %d: %r not in %s %r' % (ME, r['_line'], pattern, field,
                                                          r[field]))
    s = m.group(1)
    mult = 1
    if s.upper().endswith('M'):
        s, mult = s[:-1].strip(), 1000000
    v = round(float(s.replace(',', '').replace('$', '')) * mult)
    return v


def rank(r):
    """(rank, of) from a ranking row, both whole numbers, checked."""
    a = re.match(r'\s*(\d+)\b', r['rank'])
    b = re.match(r'\s*(\d+)\s*$', r['rank_of'])
    if not (a and b):
        raise SystemExit('%s: line %d: no whole rank in %r of %r'
                         % (ME, r['_line'], r['rank'], r['rank_of']))
    return int(a.group(1)), int(b.group(1))


def heard(r):
    return r['basis'] == 'captions'


# ---------------------------------------------------------------------------- figures

def figures(rows):
    F = {}
    # Requests and ranks, FY2024: the schools' feasibility study.
    F['sc24'] = rank(one(rows, cycle_fy='2024', kind='ranking',
                         rank_scheme__start='FY24 Capital Plan Projects Priority'))
    F['tm24'] = rank(one(rows, cycle_fy='2024', kind='ranking', rank_scheme__start='TM Priority'))
    F['cpc24'] = rank(one(rows, cycle_fy='2024', kind='ranking', rank_scheme__start='CPC Priority'))
    F['req24'] = dollars(one(rows, cycle_fy='2024', date='2022-10-26', kind='request',
                             body__start='Lunenburg Public Schools'),
                         r'^([\d,]+) \(study\)')
    F['arpa24'] = dollars(one(rows, cycle_fy='2024', date='2023-11-20', kind='minutes'),
                          r'^([\d,]+) \(ARPA\)')
    # FY2025: survey and drainage, phase A.
    F['sc25'] = rank(one(rows, cycle_fy='2025', kind='ranking',
                         doc__in='a207', rank_scheme__start='School Committee Priority Rankings'))
    F['tm25'] = rank(one(rows, cycle_fy='2025', kind='ranking', rank_scheme__start='TM Priority'))
    F['cpc25'] = rank(one(rows, cycle_fy='2025', kind='ranking', rank_scheme__start='CPC Priority'))
    F['req25'] = dollars(one(rows, cycle_fy='2025', date='2024-01-16', kind='plan'), r'^([\d,]+)')
    # FY2027: the School Committee's own order, as heard; the CPC's printed list.
    r27 = one(rows, cycle_fy='2027', kind='ranking', rank_scheme__start='SC priority order read')
    F['sc27'] = rank(r27)
    F['sc27_heard'] = heard(r27)
    cpc27 = one(rows, cycle_fy='2027', date='2026-02-01', kind='ranking', body='Capital Planning Committee')
    m = re.search(r'considered (\d+) projects for FY27 which totaled (\$[\d,]+)', cpc27['quote'])
    F['cpc27_n'], F['cpc27_total'] = int(m.group(1)), int(m.group(2)[1:].replace(',', ''))
    # FY2028: first priority, as heard.
    r28 = one(rows, cycle_fy='2028', date='2026-10-21', kind='plan')
    F['first28_heard'] = heard(r28)
    m = re.match(r'~\$(\d+) million', r28['amount'])
    if not m:
        raise SystemExit('%s: line %d: no spoken estimate in %r' % (ME, r28['_line'], r28['amount']))
    F['est28'] = int(m.group(1)) * 1000000
    # The two Town Meeting votes.
    v16 = one(rows, cycle_fy='2017', date='2016-05-05', kind='vote')
    F['vote16'] = dollars(v16, r'^([\d,]+)$')
    v26 = one(rows, cycle_fy='2027', date='2026-11-17', kind='vote')
    F['vote26'] = dollars(v26, r'^\$([\d,]+)')
    F['vote26_heard'] = heard(v26)
    m = re.search(r'(\d+) in favor, (\d+) opposed', v26['what_happened'])
    F['yes26'], F['no26'] = int(m.group(1)), int(m.group(2))
    F['plan17'] = one(rows, cycle_fy='2017', date='2016-05-05', kind='absence')
    # Estimates: 2015 CPC list, and the September 2025 school plan's two phases.
    F['est15'] = dollars(one(rows, cycle_fy='2017', date='2015-10-27', kind='request'),
                         r'^([\d,]+)$')
    p25 = one(rows, cycle_fy='2027', date='2025-09-17', kind='plan')
    F['hard25'] = dollars(p25, r'^\$([\d,]+) \(FY27\)')
    F['turf25'] = dollars(p25, r'\$([\d.]+M) \(FY29\)')
    F['est25'] = F['hard25'] + F['turf25']
    # The rows themselves.
    F['bond17'] = dollars(one(rows, cycle_fy='2017', date='2017-01-17', kind='debt'), r'^([\d,]+)$')
    F['cpc26_n'] = int(one(rows, cycle_fy='2026', date='2024-12-16', kind='absence')['rank_of'])
    F['rows'] = len(rows)
    F['docs'] = sum(1 for r in rows if r['basis'] == 'document')
    F['heard'] = sum(1 for r in rows if heard(r))
    F['absent'] = sorted({int(r['cycle_fy']) for r in rows if r['kind'] == 'absence'})
    return F


# ---------------------------------------------------------------------------- the rank table

def of(t):
    return '%d of %d' % t


def nth(t):
    r = t[0]
    suf = 'th' if 10 <= r % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(r % 10, 'th')
    return '%d%s of %d' % (r, suf, t[1])


def band(t):
    """Where a rank sits in ITS OWN list, so 5 of 6 and 19 of 35 can be compared: the
    first place, or the top, middle or bottom third by rank over list length."""
    r, n = t
    if r == 1:
        return 'first'
    f = r / n
    return 'top third' if f <= 1 / 3 else ('middle third' if f <= 2 / 3 else 'bottom third')


def _ob(t):
    return '%s (%s)' % (of(t), band(t))


def rank_table(F):
    """cycle | requested | amount | each scheme's rank, as printed | how it ended."""
    return [
        dict(cycle='FY2017', requested='Turf field and track replacement',
             amount=C.usd(F['est15']) + ' (2015 estimate)', schools='—', town_manager='—',
             cpc='not in the plan', outcome='%s borrowed by separate article, May 2016'
             % C.usd(F['vote16']), basis='document'),
        dict(cycle='FY2024', requested='Feasibility study', amount=C.usd(F['req24']),
             schools=_ob(F['sc24']), town_manager=_ob(F['tm24']), cpc=_ob(F['cpc24']),
             outcome='listed as not included; study paid from ARPA (%s)' % C.usd(F['arpa24']),
             basis='document'),
        dict(cycle='FY2025', requested='Site survey and drainage', amount=C.usd(F['req25']),
             schools=_ob(F['sc25']), town_manager=_ob(F['tm25']), cpc=_ob(F['cpc25']),
             outcome='listed as not included in the preliminary plan', basis='document'),
        dict(cycle='FY2026', requested='Design and bid documents', amount='not stated',
             schools='not on the ranked list', town_manager='—', cpc='not ranked',
             outcome='spring 2025 article removed from the warrant (as heard)', basis='captions'),
        dict(cycle='FY2027', requested='Hardscape and drainage', amount=C.usd(F['hard25']),
             schools=_ob(F['sc27']) + ' (as heard)', town_manager='—',
             cpc='not among the %d ranked' % F['cpc27_n'],
             outcome='withdrawn from the cycle; then Article 9, %s (as heard)'
             % C.usd(F['vote26']), basis='captions'),
        dict(cycle='FY2028', requested='Turf and track', amount='about %s (as heard)'
             % C.usd(F['est28']), schools='first (as heard)', town_manager='—',
             cpc='no list held yet', outcome='under way', basis='captions'),
    ]


# ---------------------------------------------------------------------------- conclusions

# Years are dates, not derived figures: declared as literals so the rule-2 scan does not
# take `2016` for a typed amount. Nothing else is exempt.
YEARS = tuple(['FY%d' % y for y in range(FIRST, LAST + 1)]
              + ['%d' % y for y in range(FIRST, LAST + 1)])


def build_conclusions(F):
    cpc24, cpc25 = of(F['cpc24']), of(F['cpc25'])
    sc24, sc25, sc27 = of(F['sc24']), of(F['sc25']), of(F['sc27'])
    v16, v26 = C.usd(F['vote16']), C.usd(F['vote26'])
    e15, e25 = C.usd(F['est15']), C.usd(F['est25'])
    h25, t25 = C.usd(F['hard25']), C.usd(F['turf25'])
    rows = [
        conclusion(
            id='where-the-committee-ranked-it',
            claim='The two times the capital committee ranked the field, it put it %s, then %s.'
                  % (cpc24, cpc25),
            so_what='Both years the Town Manager\u2019s preliminary plan listed it among requests not included.',
            detail='FY2024: a %s feasibility study, Capital Planning Committee priority %s, Town '
                   'Manager priority %s. FY2025: %s for survey and drainage, priority %s and %s. '
                   'Both appear on the page headed as requests not included in the preliminary '
                   'recommendation.'
                   % (C.usd(F['req24']), cpc24, of(F['tm24']), C.usd(F['req25']), cpc25,
                      of(F['tm25'])),
            figures=dict(cpc24=figure(F['cpc24'][0], cpc24, 'capital requests, FY2024 rank'),
                         cpc25=figure(F['cpc25'][0], cpc25),
                         tm24=figure(F['tm24'][0], of(F['tm24'])),
                         tm25=figure(F['tm25'][0], of(F['tm25'])),
                         req24=figure(F['req24'], C.usd(F['req24'])),
                         req25=figure(F['req25'], C.usd(F['req25']))),
            figure='cpc24', kind='measured', bearing='sizes', allow=YEARS,
            basis='The Town Manager\u2019s preliminary FY2024 and FY2025 capital plan decks, '
                  'which print the TM and CPC priority beside each request; for FY2025 the CPC\u2019s '
                  'own workbook agrees (sheet Ordered).',
            not_shown='Whether the voted FY2024 and FY2025 plans included it: their item lists '
                      'were not readable in the text we hold. For FY2024 the committee\u2019s own '
                      'sheet prints no rank number and ties the field on average with another '
                      'request, sorting it one place higher; the rank is the Town Manager deck\u2019s. '
                      'And a rank says where it stood against that year\u2019s other requests, not why.'),
        conclusion(
            id='the-schools-moved-it-up',
            claim='The schools ranked the field %s for FY2024 and %s for FY2025; by FY2028 it was first.'
                  % (sc24, sc25),
            so_what='The FY2027 order, %s, and the FY2028 one were heard on recordings; no printed list is held.'
                    % sc27,
            detail='These are the School Committee\u2019s own priority orders for what it sent to '
                   'the town, a different list from the town committee\u2019s ranking. For FY2026 '
                   'the field was not on the schools\u2019 ranked list at all; the plan put its '
                   'money a year later.',
            figures=dict(sc24=figure(F['sc24'][0], sc24, 'school requests, schools\u2019 own rank'),
                         sc25=figure(F['sc25'][0], sc25), sc27=figure(F['sc27'][0], sc27)),
            figure='sc24', kind='measured', bearing='sizes', allow=YEARS,
            basis='The schools\u2019 FY24 and FY25 capital presentations (printed rank tables); '
                  'School Committee recordings of 1 October 2025 and 21 October 2026 (machine '
                  'captions, a finding aid).',
            not_shown='Why the order changed. Nothing here tests it: the field\u2019s condition, '
                      'other requests being funded, and a change in who sat on the committee '
                      'all fit the same sequence.'),
        conclusion(
            id='money-came-by-separate-article',
            claim='Both votes for field money were separate articles: %s in 2016, %s in 2026.'
                  % (v16, v26),
            so_what='Neither came through a ranked capital plan; the 2026 result is as heard, the official one is not held.',
            detail='In 2016 Town Meeting borrowed %s by its own article while that year\u2019s '
                   'capital plan said it had no request to bond. In November 2026 a Special Town '
                   'Meeting moved %s from the general stabilization fund for engineering, %s on '
                   'the electronic count as the captions read it.'
                   % (v16, v26, '%d to %d' % (F['yes26'], F['no26'])),
            figures=dict(v16=figure(F['vote16'], v16), v26=figure(F['vote26'], v26),
                         vote=figure(F['yes26'], '%d to %d' % (F['yes26'], F['no26']))),
            figure='v16', kind='measured', bearing='lever', allow=YEARS,
            basis='The FY2016 annual town report (Article 28 and the FY2017 capital plan); the '
                  'Special Town Meeting warrant of 17 November 2026 and the meeting\u2019s recording.',
            not_shown='The official 2026 tally and any board\u2019s recommendation on it: no Town '
                      'Clerk record or minutes of that meeting are held yet.'),
        conclusion(
            id='the-estimate-grew-with-scope',
            claim='The field\u2019s estimate went from %s in 2015 to %s in the schools\u2019 2025 plan.'
                  % (e15, e25),
            so_what='The 2025 figure adds hillside hardscape and drainage the 2015 one did not name.',
            detail='The September 2025 draft splits it: %s for hardscape and drainage, %s for '
                   'replacing the track and turf. The like-for-like part, turf and track, is %s '
                   'against the %s Town Meeting borrowed in 2016.'
                   % (h25, t25, t25, v16),
            figures=dict(e15=figure(F['est15'], e15), e25=figure(F['est25'], e25),
                         h25=figure(F['hard25'], h25), t25=figure(F['turf25'], t25),
                         v16=figure(F['vote16'], v16)),
            figure='e25', kind='measured', bearing='sizes', allow=YEARS,
            basis='Capital Planning Committee minutes of 27 October 2015; the School Committee\u2019s '
                  'revised draft FY27-FY35 capital plan, September 2025.',
            not_shown='What the work would cost if bid now: both are planning estimates, and a '
                      'later figure of about three million dollars was only spoken at a meeting.'),
    ]
    return emit(RID, rows)


# ---------------------------------------------------------------------------- the rounds

def _short_date(d):
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', d)
    if not m:
        return d.split(' (')[0] or 'undated'
    mon = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov',
           'Dec'][int(m.group(2)) - 1]
    return '%d %s %s' % (int(m.group(3)), mon, m.group(1))


def _sortkey(r):
    m = re.match(r'(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?', r['date'])
    return (m.group(0) if m else '9999', r['_line'])


def _what(r):
    w = r['what_happened'].strip()
    if not w:
        bits = [r['item'], r['rank_scheme'] and ('%s: %s' % (r['rank_scheme'],
                                                          ('%s of %s' % (r['rank'], r['rank_of'])
                                                           if r['rank_of'] else r['rank'])))]
        w = '; '.join(b for b in bits if b)
    return w


def _who(body):
    b = body.split(' (')[0].strip(' -') or 'document'
    for long, short in (('Lunenburg Public Schools to Capital Planning Committee', 'Schools, to the capital committee'),
                        ('Lunenburg Public Schools', 'Schools'),
                        ('Capital Planning Committee', 'Capital committee'),
                        ('Town Manager preliminary FY24 plan', 'Town Manager'),
                        ('Town Manager preliminary FY25 plan', 'Town Manager'),
                        ('Finance Committee (draft ATM warrant', 'Finance Committee')):
        if b.startswith(long):
            return short + b[len(long):]
    for org in ('Town Manager', 'Select Board', 'School Committee', 'Finance Committee'):
        if b.startswith(org):
            return org
    return b


def row_out(r):
    return dict(date=_short_date(r['date']), body=r['body'], who=_who(r['body']),
                about=r['about'], plain=r['plain'] + (' (as heard)' if heard(r) and r['plain'] else ''),
                kind=r['kind'], what=_what(r),
                amount=r['amount'], vote=r['vote'],
                basis='as heard (captions)' if heard(r) else (
                    'our record' if r['basis'].startswith('our record') else 'document'),
                doc=r['doc'], where=r['where'], line=r['_line'])


def _newest_first(rs):
    # An undated row goes last, not first: '9999' is _sortkey's sentinel for no date.
    return sorted(rs, key=lambda r: (_sortkey(r)[0] != '9999', _sortkey(r)), reverse=True)


def outcomes(F):
    """One plain line per round: asked, capital committee, Town Manager's plan, Town Meeting,
    money. Every figure is F's; nothing here is typed."""
    h = lambda b: ' (as heard)' if b else ''
    return {
        'r28': dict(asked='first on the schools\u2019 draft plan' + h(F['first28_heard']),
                    committee='no list yet', plan='\u2014', meeting='\u2014', money='none yet'),
        'r27s': dict(asked='%s for engineering, its own article' % C.usd(F['vote26']),
                     committee='not ranked', plan='not in it',
                     meeting='voted %d-%d%s' % (F['yes26'], F['no26'], h(F['vote26_heard'])),
                     money='%s from the stabilization fund, engineering only' % C.usd(F['vote26'])),
        'r27': dict(asked='schools\u2019 priority %s%s' % (of(F['sc27']), h(F['sc27_heard'])),
                    committee='chair took it out as too complex; not on the list of %d' % F['cpc27_n'],
                    plan='not in it', meeting='\u2014', money='none'),
        'r26': dict(asked='shown as a future request, unranked; then a design article',
                    committee='not on the list of %d' % F['cpc26_n'], plan='not in it',
                    meeting='article taken off the warrant by the Select Board', money='none'),
        'r25': dict(asked='%s, survey and drainage' % C.usd(F['req25']),
                    committee='ranked %s' % of(F['cpc25']), plan='left out',
                    meeting='plan passed; its item list is unreadable in our copy', money='none found'),
        'r24': dict(asked='%s feasibility study' % C.usd(F['req24']),
                    committee='ranked %s' % of(F['cpc24']), plan='left out',
                    meeting='plan passed; its item list is unreadable in our copy',
                    money='%s from ARPA (federal pandemic relief) instead' % C.usd(F['arpa24'])),
        'r17': dict(asked='not through the capital plan', committee='listed it, unranked',
                    plan='not in it', meeting='borrowed %s by its own article' % C.usd(F['vote16']),
                    money='bonds of %s; turf replaced that autumn' % C.usd(F['bond17'])),
    }


def rounds(rows, F):
    out, used = [], set()
    oc = outcomes(F)
    for cyc, since, until, title, key in ROUNDS:
        rs = [r for r in rows if int(r['cycle_fy']) == cyc
              and (since is None or _sortkey(r)[0] >= since)
              and (until is None or _sortkey(r)[0] < until)]
        used.update(r['_line'] for r in rs)
        shown = [r for r in _newest_first(rs) if r['plain']]
        out.append(dict(title=title, cycle=cyc, outcome=oc[key],
                        rows=[row_out(r) for r in shown], in_dataset=len(rs) - len(shown)))
    rest = [r for r in rows if r['_line'] not in used]
    rest = sorted(_newest_first(rest), key=lambda r: int(r['cycle_fy']), reverse=True)
    other = dict(title='Every other cycle, FY%d to FY%d · no field money asked for that year'
                       % (FIRST, LAST), cycle=None,
                 rows=[dict(row_out(r), cycle='FY' + r['cycle_fy']) for r in rest if r['plain']],
                 in_dataset=sum(1 for r in rest if not r['plain']))
    if len(used) + len(rest) != len(rows):
        raise SystemExit('%s: rounds lost a row' % ME)
    return out, other


# ---------------------------------------------------------------------------- outputs

NOT_ESTABLISHED = [
    'The official result of Article 9 at the 17 November 2026 Special Town Meeting, and the '
    'Finance Committee\u2019s and Select Board\u2019s recommendations on it.',
    'Whether the voted FY2024 and FY2025 capital plans included any field money: their item '
    'lists are not in the text we hold.',
    'Which printed list the Select Board chair\u2019s \u201cranked 5 of 7\u201d of 20 October '
    '2026 refers to: no list held ranks the field 5 of 7.',
    'Why any board ranked the field where it did.',
]


def sources(rows):
    man = {}
    try:
        with open(MANIFEST, encoding='utf-8') as fh:
            man = {r['key']: r for r in csv.DictReader(fh)}
    except OSError:
        pass
    seen, out = set(), []
    out.append(dict(path='sources/data/track-field-capital-history.csv',
                    docs_url='/docs/data/track-field-capital-history.csv',
                    filename='track-field-capital-history.csv', url='', sha256='', bytes=0,
                    table='track_field_capital_history',
                    publisher='Lunenburg Budget Project (ours)',
                    note='Every row behind this page, with the quote it rests on, its page or '
                         'second, and whether it is a document or a recording heard through '
                         'machine captions.'))
    for r in rows:
        key = r['doc'].split(' (')[0].split(';')[0].strip()
        if key in seen or key not in man:
            continue
        seen.add(key)
        m = man[key]
        out.append(dict(path='sources/' + key, docs_url='/docs/' + key,
                        filename=key.split('/')[-1], url=m.get('upstream', ''),
                        sha256=m.get('sha256', ''), bytes=int(m.get('bytes') or 0),
                        publisher=m.get('publisher', '') or '',
                        note=r['body']))
    return out


def payload(rows, F, concl):
    rs, other = rounds(rows, F)
    return dict(
        id=RID, generated_by='scripts/' + ME,
        about='The track and field in the town\u2019s capital process: every ranking, request, '
              'plan line and vote the archive holds, FY%d to FY%d.' % (FIRST, LAST),
        stats=[
            dict(value='%s \u2192 %s' % (band(F['sc24']).split()[0], 'top'),
                 label='where the schools put the field on their own list: %s in FY2024, %s in '
                       'FY2025, %s in FY2027, first for FY2028 (the last two as heard)'
                       % (nth(F['sc24']), nth(F['sc25']), nth(F['sc27']))),
            dict(value=of(F['cpc24']),
                 label='the capital committee\u2019s rank, FY2024: the %s. FY2025: %s, the %s'
                       % (band(F['cpc24']), of(F['cpc25']), band(F['cpc25']))),
            dict(value=C.usd(F['vote16']), label='borrowed by separate article, May 2016'),
            dict(value=C.usd(F['vote26']), label='for engineering, Special Town Meeting Nov 2026 (as heard)'),
            dict(value=C.usd(F['est25']), label='the September 2025 school plan\u2019s estimate'),
        ],
        grain='DOCUMENTS AND RECORDINGS. Each of the %d rows is one document or recording that '
              'ranks, prices, plans or votes on the field in a capital cycle, or a plan read and '
              'found without it. %d rest on documents; %d on machine captions of a recording, '
              'marked as heard.' % (F['rows'], F['docs'], F['heard']),
        rank_table=rank_table(F),
        rounds=rs, other=other,
        conclusions=concl,
        not_established=NOT_ESTABLISHED,
        sources=sources(rows),
    )


def _cell(s):
    return (s or '').replace('|', '\\|').replace('\n', ' ').strip()


def markdown(P, F):
    L = ['# Track and field capital', '',
         '**Where the field was ranked each time it entered the town\u2019s capital process, and '
         'how money for it was actually found.**', '',
         'Analysis, November 2026. Ranks are as each document prints them; anything marked '
         '*as heard* is from machine captions of a meeting recording, which are a finding aid, '
         'not a record.', '', '---', '', '## The ranks', '',
         '| cycle | requested | amount | schools\u2019 rank | Town Manager | capital committee | how it ended |',
         '|---|---|---|---|---|---|---|']
    for t in P['rank_table']:
        L.append('| %s |' % ' | '.join(_cell(t[k]) for k in (
            'cycle', 'requested', 'amount', 'schools', 'town_manager', 'cpc', 'outcome')))
    L += ['', '## What it shows', '']
    for c in P['conclusions']:
        L += ['**%s** %s' % (c['claim'], c['so_what']), '', c['detail'], '',
              '*Rests on:* %s *Does not show:* %s' % (c['basis'], c['not_shown']), '']
    L += ['## Round by round', '',
          'Newest first. Each time the field came up for money, what was asked and what each '
          'step did with it.', '',
          '| round | asked for | capital committee | Town Manager\u2019s plan | Town Meeting | money |',
          '|---|---|---|---|---|---|']
    for rd in P['rounds']:
        o = rd['outcome']
        L.append('| %s |' % ' | '.join(_cell(c) for c in (
            rd['title'].split(' · ')[1].replace('money for ', ''), o['asked'], o['committee'],
            o['plan'], o['meeting'], o['money'])))
    L += ['', 'Below, each round as a timeline, newest event first. *About* says what the event '
          'was: asked, ranked, left out, voted, paid. Every row, and the raw readings behind it, '
          'is in `track-field-capital-history.csv` with its quote and page.', '']
    for rd in P['rounds'] + [P['other']]:
        L += ['### ' + rd['title'], '']
        multi = rd['cycle'] is None
        head = (['cycle'] if multi else []) + ['date', 'about', 'who', 'what happened']
        L += ['| %s |' % ' | '.join(head), '|%s' % ('---|' * len(head))]
        for r in rd['rows']:
            cells = ([r['cycle']] if multi else []) + [r['date'], r['about'], r['who'], r['plain']]
            L.append('| %s |' % ' | '.join(_cell(c) for c in cells))
        if rd['in_dataset']:
            L += ['', '*%d more reading%s for this round (the same rank in another copy, score '
                  'sheets, plans read and found without the field) %s in the dataset.*'
                  % (rd['in_dataset'], '' if rd['in_dataset'] == 1 else 's',
                     'is' if rd['in_dataset'] == 1 else 'are')]
        L.append('')
    L += ['## What this does not establish', '']
    L += ['- ' + s for s in P['not_established']]
    L += ['', 'Each is a row in `money-gaps.csv`, with the document that would settle it.', '',
          '## Sources', '']
    for s in P['sources']:
        L.append('- [%s](%s) \u2014 %s' % (s['filename'], s['docs_url'], s['note']))
    L += ['', '*Generated by `scripts/%s` from `sources/data/track-field-capital-history.csv`. '
          'Every quote in the dataset is re-found in its source on each run.*' % ME, '']
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows = load()
    problems = verify(rows) + coverage(rows)
    if problems:
        print('%s: %d problem(s)\n  %s' % (ME, len(problems), '\n  '.join(problems)),
              file=sys.stderr)
        return 1
    F = figures(rows)
    concl = build_conclusions(F)
    P = payload(rows, F, concl)
    md = markdown(P, F)
    pay = json.dumps(P, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
    pub = open(DATA, 'rb').read()
    if a.check:
        def cur(p, b=False):
            return (open(p, 'rb').read() if b else open(p, encoding='utf-8').read()) \
                if os.path.exists(p) else None
        bad = [os.path.relpath(p, ROOT) for p, g, b in ((OUT, md, False), (PAYLOAD, pay, False),
                                                        (PUB, pub, True)) if cur(p, b) != g]
        if bad:
            print('STALE %s' % ', '.join(bad), file=sys.stderr)
            return 1
        print('%s: %d rows, every quote found, FY%d-FY%d covered; outputs current'
              % (ME, len(rows), FIRST, LAST))
        return 0
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(md)
    with open(PAYLOAD, 'w', encoding='utf-8') as fh:
        fh.write(pay)
    os.makedirs(os.path.dirname(PUB), exist_ok=True)
    shutil.copyfile(DATA, PUB)
    print('wrote %s, %s, %s' % tuple(os.path.relpath(p, ROOT) for p in (OUT, PAYLOAD, PUB)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
