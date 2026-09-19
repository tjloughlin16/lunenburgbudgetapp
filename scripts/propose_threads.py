#!/usr/bin/env python3
"""THREADS FORMING THAT NO THREAD NAMES -- proposed for a person, never created here.

    python3 scripts/propose_threads.py                    # the last 90 days
    python3 scripts/propose_threads.py --since 2026-01-01
    python3 scripts/propose_threads.py --check            # every registered thread still resolves

The gates are `notes/process/THREADS-MODEL.md` §2, and the reason this script only PROPOSES
is §4: the criteria do not have to decide, only to rank. Over-proposal costs one line in a
list; a miss is invisible, and has the shape of every silent zero in CLAUDE.md. So it is
tuned for recall and a person confirms by adding a row to sources/data/threads.csv.

GATE A -- PERSISTENCE, and it fires on any of three. The first two are LEADING indicators
and they are the point: recurrence can only fire after a matter has run for months, which
is no use to a resident who wanted to act on it.

  1. A NON-DECISION, at n=1. Passed over, tabled, deferred, referred, "comes back",
     "topics for future discussion". A board declining to decide is a board saying the
     question is open. The paraprofessional contract was exactly this and nothing else.
  2. A SCHEDULED NEXT STEP, at n=1 -- a warrant article, a posted hearing, a study due, a
     contract expiring.
  3. RECURRENCE -- >=3 meetings. Kept, but ranked below the other two.

GATE B -- CONSEQUENCE. One of seven kinds, `office` narrowed to a DECIDING post going
vacant or contested, never a routine appointment. Then the bar: REACH x CHANGE, the same
shape as CLAUDE.md rule 4, where a line is ranked by share times excess because neither
means anything alone.

THE BAR RANKS. IT DOES NOT CUT. A low score still prints; it prints lower.

TWO ROWS THAT ARE NEVER A MATTER, both already flagged in the data and both found by
running this forward:
  * a PROCEDURAL vote -- our minutes set `procedural: true`, 85 of 224 recent votes, and
    the first version of this script did not read it. "Close the public hearing" is the
    meeting operating itself.
  * a REPORT BUNDLE -- "Chair's report: ..." packs ten unrelated subjects into one row and
    scores high precisely because it is dense. It may SEED a candidate and may never be
    the evidence for one.
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
MINUTES = os.path.join(ROOT, 'sources', 'data', 'recording-minutes')
THREADS = os.path.join(ROOT, 'sources', 'data', 'threads.csv')
DECLINED = os.path.join(ROOT, 'sources', 'data', 'threads-declined.csv')

NONDECISION = re.compile(r'\b(pass(ed)? over|tabl(e|ed)|defer(red)?|continue[d]? to|refer(red)? to|'
                         r'future discussion|come back|bring back|held off|hold off|'
                         r'no vote (was )?(taken|tonight)|placeholder|not voted on)\b', re.I)
SCHEDULED = re.compile(r'\b(warrant article|public hearing|deadline|due back|statement of interest|'
                       r'\bRFP\b|request for proposal|feasibility study|expires?|renewal|reratif\w*|'
                       r'up for renewal|targeted for|submitted? by)\b', re.I)
WORMS = re.compile(r'\b(audit|forensic|investigat\w+|review of (the )?(financial )?practices|'
                   r'town counsel opinion|complaint|conflict of interest|discrepanc\w+|'
                   r'unaccounted|misstat\w+|overstat\w+|understat\w+|breach)\b', re.I)
BUNDLE = re.compile(r'^\s*((chair|chair\'s|superintendent|superintendent\'s|town manager|town manager\'s|'
                    r'director|treasurer|liaison)\s*\'?s?\s+report|committee reports|agenda run-through|'
                    r'announcements)\b|\breport:\s', re.I)

KIND = [
    ('rule',     r'\b(bylaw|by-law|zoning|regulation|ordinance|policy|code of lunenburg|charter)\w*\b'),
    ('money',    r'\b(fee|rate|tax|assessment|surcharge|tuition|user fee|enterprise fund|betterment|exemption)\w*\b'),
    ('contract', r'\b(contract|MOU|collective bargaining|union|agreement|lease|bid|procurement|award)\w*\b'),
    ('project',  r'\b(study|design|feasibilit\w+|construct\w+|renovat\w+|project)\w*\b'),
    ('asset',    r'\b(building|land|parcel|property|field|park|playground|sell|sale of|dispos\w+|demolit\w+)\w*\b'),
    ('service',  r'\b(hours|program|programme|staffing|position|FTE|route|eliminat\w+|reduc\w+|restor\w+)\w*\b'),
    # NARROWED: a deciding post going vacant or contested, never a routine appointment.
    ('office',   r'\b(superintendent search|town manager search|screening committee|'
                 r'vacancy on the|standing vacancy|interim (superintendent|town manager))\b'),
]
REACH = [(4, r'\b(every (resident|property|household|taxpayer)|townwide|town-wide|all residents|'
             r'tax rate|tax bill|ballot|bylaw|zoning|ratepayer)\w*\b'),
         (3, r'\b(school famil\w+|students|parents|district-wide|all schools|athletics|transportation|tuition)\b'),
         (2, r'\b(program|programme|team|club|league|participants)\w*\b')]
IRREVERSIBLE = re.compile(r'\b(sell|sale of|dispos\w+|demolit\w+|demolish|borrow|bond|multi-year|convey)\b', re.I)
FIGURE = re.compile(r'\$[\d,]+(?:\.\d+)?|\b\d+(?:\.\d+)?\s?FTE\b', re.I)


def read_csv(p):
    return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []


def registered():
    """Every thread already named, as compiled matchers. A thread's `exclude` fixes the
    SENSE of a word that carries more than one -- `surplus` is a budget surplus and also a
    1998 ambulance."""
    out = []
    for r in read_csv(THREADS):
        out.append(dict(r, rx=re.compile(r['match'], re.I) if r.get('match') else None,
                        ex=re.compile(r['exclude'], re.I) if r.get('exclude') else None))
    return out


def claimed(threads, text):
    for t in threads:
        if t['rx'] and t['rx'].search(text) and not (t['ex'] and t['ex'].search(text)):
            return t['id']
    return None


def meetings(since, until):
    """ONE ROW PER MEETING, not per recording. A meeting recorded in two parts is two files
    (the 2 May 2026 ATM is 6h56m and 4h55m), and a joint body's meeting counts for each of
    its constituents -- so items are keyed on (board_slug, date) and deduped."""
    by = collections.OrderedDict()
    for f in sorted(glob.glob(os.path.join(MINUTES, '*', '*.json'))):
        j = json.load(open(f, encoding='utf-8'))
        d = j.get('meeting_date') or ''
        if not (since <= d <= until):
            continue
        key = (j['board_slug'], d)
        m = j.get('minutes') or {}
        rec = by.setdefault(key, {'board': j.get('board') or j['board_slug'], 'items': [],
                                  'public_comment': [], 'seen': set()})
        for p in (m.get('public_comment') or []):
            rec['public_comment'].append(p.get('topic') or '')
        for x in (m.get('decisions') or []):
            rec['items'].append(('decision', x.get('decision') or ''))
        for v in (m.get('votes') or []):
            if v.get('procedural'):          # the meeting operating itself
                continue
            rec['items'].append(('vote', (v.get('motion') or '') + ' ' + (v.get('outcome') or '')))
        for t in (m.get('topics') or []):
            topic = t.get('topic') or ''
            if BUNDLE.search(topic):         # ten subjects in one row
                continue
            rec['items'].append(('topic', topic + ' ' + (t.get('summary') or '')))
    for rec in by.values():
        rec['items'] = [(s, t) for s, t in rec['items']
                        if t.strip() and not (t.strip().lower() in rec['seen'] or rec['seen'].add(t.strip().lower()))]
    return by


def score(text, pc):
    reach = max([w for w, rx in REACH if re.search(rx, text, re.I)] or [1])
    spoke = 0
    words = set(re.findall(r'\b[a-z]{6,}\b', text.lower()))
    if words and pc and len(words & set(re.findall(r'\b[a-z]{6,}\b', pc.lower()))) >= 2:
        spoke = 3                                    # residents turned up about this
    return (reach * 2 + (2 if FIGURE.search(text) else 0)
            + (2 if IRREVERSIBLE.search(text) else 0) + spoke), reach, spoke


def build(since, until):
    threads = registered()
    declined = {r['candidate'].lower() for r in read_csv(DECLINED)}
    hits = collections.defaultdict(list)
    for (slug, date), rec in meetings(since, until).items():
        pc = ' | '.join(rec['public_comment'])
        for src, text in rec['items']:
            if len(text) < 25:
                continue
            trig = []
            if NONDECISION.search(text):
                trig.append('non-decision')
            if SCHEDULED.search(text):
                trig.append('scheduled')
            if not trig:
                continue
            kinds = [k for k, rx in KIND if re.search(rx, text, re.I)]
            if not kinds:
                continue
            tid = claimed(threads, text)
            sc, reach, spoke = score(text, pc)
            worms = bool(WORMS.search(text))
            if worms:
                sc += 6
            hits[tid].append(dict(date=date, board=rec['board'], slug=slug, src=src, text=text,
                                  kinds=kinds, score=sc, reach=reach, spoke=spoke,
                                  worms=worms, trig=trig))
    return threads, declined, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--since')
    ap.add_argument('--until', default=dt.date.today().isoformat())
    ap.add_argument('--days', type=int, default=90)
    ap.add_argument('--top', type=int, default=20)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    if a.check:
        threads = registered()
        bad = [t['id'] for t in threads if not t.get('match')]
        # EVERY REGISTERED THREAD MUST STILL MATCH SOMETHING. A thread whose pattern has
        # stopped resolving looks exactly like a matter that stopped being discussed.
        _, _, hits = build('2000-01-01', a.until)
        allmin = meetings('2000-01-01', a.until)
        text = ' \n '.join(t for rec in allmin.values() for _, t in rec['items'])
        dead = [t['id'] for t in threads if t['rx'] and not t['rx'].search(text)]
        for t in threads:
            if t.get('closes', '').strip() == '':
                bad.append(t['id'] + ' (no closure criterion)')
        print('%d threads registered; %d declined' % (len(threads), len(read_csv(DECLINED))))
        if dead:
            print('MATCHES NOTHING IN THE RECORD: %s' % ', '.join(dead))
        if bad:
            print('INCOMPLETE: %s' % ', '.join(bad))
        raise SystemExit(1 if (dead or bad) else 0)

    since = a.since or (dt.date.fromisoformat(a.until) - dt.timedelta(days=a.days)).isoformat()
    threads, declined, hits = build(since, a.until)
    mts = meetings(since, a.until)
    print('%d meetings read, %s .. %s, across %d boards'
          % (len(mts), since, a.until, len({s for s, _ in mts})))
    known = sum(len(v) for k, v in hits.items() if k)
    print('%d triggered items — %d already claimed by a registered thread\n'
          % (sum(len(v) for v in hits.values()), known))

    # WHAT THE REGISTERED THREADS DID, so this run is also the "what moved" report.
    moved = sorted(((k, v) for k, v in hits.items() if k), key=lambda kv: -max(h['score'] for h in kv[1]))
    if moved:
        print('REGISTERED THREADS THAT MOVED')
        byid = {t['id']: t for t in threads}
        for tid, hs in moved:
            last = max(h['date'] for h in hs)
            print('  %-26s %s  %d item(s)   %s' % (tid, last, len(hs), byid[tid]['label']))
        print()
    print('PROPOSED — no thread names these. A person confirms by adding a row to threads.csv.')
    new = sorted(hits.get(None, []), key=lambda h: -h['score'])
    seen = set()
    shown = 0
    for h in new:
        key = re.sub(r'\W+', ' ', h['text'].lower())[:55]
        if key in seen or h['text'].lower()[:40] in declined:
            continue
        seen.add(key)
        shown += 1
        if shown > a.top:
            break
        print('  [%2d] %s %-22s %-18s %s%s%s'
              % (h['score'], h['date'], h['slug'][:22], '/'.join(h['kinds'][:2]),
                 'CAN-OF-WORMS ' if h['worms'] else '',
                 'residents-spoke ' if h['spoke'] else '', '+'.join(h['trig'])))
        print('       %s' % h['text'][:200].replace('\n', ' '))
    if not shown:
        print('  (none)')
    print('\nTHE BAR RANKS, IT DOES NOT CUT — a low score is printed lower, never dropped.')
    print('A candidate you reject goes in threads-declined.csv with a reason, so "we looked')
    print('and said no" stays distinguishable from "nobody looked".')


if __name__ == '__main__':
    main()
