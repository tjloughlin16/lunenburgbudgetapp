#!/usr/bin/env python3
"""What is on an upcoming agenda that a resident would want to know about, before the meeting.

    python3 scripts/write_agenda_preview.py school-committee 2026-09-09   # one agenda
    python3 scripts/write_agenda_preview.py --upcoming                    # every policy-board agenda dated today or later
    python3 scripts/write_agenda_preview.py --check
    python3 scripts/write_agenda_preview.py --status

THE UPCOMING HALF OF THE LOOP. TJ, 11 September 2026: *"meetings are posted 2 days
before. so we need the date the meetings will happen (agenda) to post on the site/facebook
to give them notice. THEN we post after once we have the transcript."* The retro half is
`write_recording_minutes.py`; this is the notice.

WHAT IT READS. The agenda the town published, as extracted to `sources/meetings/text/`.
That is a document, so unlike the minutes-from-captions this can QUOTE: every item it
lists carries the agenda's own line, and `--check` asserts that line is in the file. A
preview whose quote is not in the agenda fails the check rather than publishing.

WHAT IT PICKS OUT. Items touching money, votes, hearings, contracts, staffing, buildings,
fees, policy changes, and anything scheduled for a vote -- the things a resident who
cannot attend would want two days' notice of. It leaves out the pledge, the approval of
minutes, and standing reports unless the agenda says something specific under them.

WHAT IT DOES NOT DO (rule 7). It does not say what will be decided. An agenda lists what
MAY be discussed -- the town's own agendas say so in their footer -- and the preview says
so. Nothing here posts anywhere: it writes a file and composes a Facebook-ready text a
person pastes. Boards are limited by `recording-minutes-policy.csv`, the same approval
that governs the minutes.
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEETINGS_INDEX = os.path.join(ROOT, 'sources', 'meetings', 'index.csv')
TEXT = os.path.join(ROOT, 'sources', 'meetings', 'text')
POLICY = os.path.join(ROOT, 'sources', 'data', 'recording-minutes-policy.csv')
OUT = os.path.join(ROOT, 'sources', 'data', 'agenda-previews')
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
SITE = 'https://lunenburgbudgetproject.org'
MODEL = 'sonnet'

SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['when', 'time', 'where', 'attend', 'how_to_attend', 'items', 'hook', 'one_line', 'nothing_of_note'],
    'properties': {
        'when': {'type': 'string', 'description': 'date and time exactly as the agenda states them'},
        'time': {'type': 'string', 'description': 'the start time alone, e.g. "7:00 PM", or "not stated"'},
        'where': {'type': 'string', 'description': 'location as stated, SHORT (e.g. "Town Hall, Bilotta Room", "LMS Room D132"), or "not stated"'},
        'attend': {'type': 'string', 'enum': ['in person', 'zoom', 'hybrid', 'broadcast only', 'not stated'],
                   'description': 'how the public can take part'},
        'how_to_attend': {'type': 'string', 'description': 'in person / Zoom / hybrid / broadcast, as stated; include a Zoom link only if printed'},
        'hook': {'type': 'string', 'description': 'THE HOOK: the two or three things on this agenda a resident would most want to know about, as one phrase under 110 characters, no date, no board name, no outcome predicted. e.g. "Opioid-settlement money for AEDs, the Brooks House report, and a look at the town buildings"'},
        'items': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False,
            'required': ['agenda_line', 'why_it_matters', 'kind', 'important'],
            'properties': {
                'agenda_line': {'type': 'string', 'description': 'the item EXACTLY as printed on the agenda, verbatim, one line'},
                'why_it_matters': {'type': 'string', 'description': 'one sentence, plain English, no figures the agenda does not print, no prediction of the outcome'},
                'kind': {'type': 'string', 'enum': ['vote', 'hearing', 'budget', 'contract', 'staffing', 'facilities', 'fees', 'policy', 'grant', 'transfer', 'presentation', 'other']},
                'vote_expected': {'type': 'boolean', 'description': 'true only if the agenda says a vote is scheduled (e.g. "VOTE", "to approve", "action item")'},
                'important': {'type': 'boolean', 'description': 'true if this item touches the schools, the budget, taxes or fees, a contract or hiring decision, a building, or a service residents use -- something a resident would want to know was being decided. false for routine or administrative items.'},
            }}},
        'one_line': {'type': 'string', 'description': 'the meeting in one sentence for a notice, under 200 characters, naming the two or three items that matter most; no outcome predicted'},
        'nothing_of_note': {'type': 'boolean', 'description': 'true if the agenda holds only routine items'},
    },
}

SYSTEM = """You read a public meeting agenda and pick out what a resident who cannot attend would want notice of.

Rules:
1. agenda_line is VERBATIM from the agenda text you are given. Do not paraphrase it, do not merge two lines. It will be checked against the file.
2. Pick items touching money, votes, public hearings, contracts, hiring or cuts, buildings, fees, policy changes, grants, transfers, and anything marked for a vote. Skip the pledge, approval of prior minutes, adjournment, and standing reports with nothing specific under them.
3. why_it_matters is one plain sentence. Never predict what will be decided; an agenda lists what may be discussed.
4. Do not invent figures. If the agenda prints an amount you may repeat it inside agenda_line only.
5. important is true for an item that touches the schools, the budget, taxes or fees, a contract or hiring decision, a building, or a service residents use. Introductions, acknowledgements, correspondence, appointments to committees and housekeeping are not important.
6. hook is the headline a resident scans: the two or three items that matter, as a phrase, no date and no board name. one_line is for a notice: when, which board, and those items, under 200 characters.

Return only the JSON."""


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def policy_boards():
    if not os.path.exists(POLICY):
        return set()
    return {r['board_slug'] for r in csv.DictReader(open(POLICY, encoding='utf-8')) if r.get('board_slug')}


def agendas(board=None, date=None, upcoming_from=None):
    out = []
    for r in csv.DictReader(open(MEETINGS_INDEX, encoding='utf-8', errors='replace')):
        if r['kind'] != 'agenda':
            continue
        stem = os.path.splitext(r['path'])[0]
        slug = stem.split('/')[0]
        if board and slug != board:
            continue
        if date and r['date'] != date:
            continue
        if upcoming_from and r['date'] < upcoming_from:
            continue
        txt = os.path.join(TEXT, stem + '.txt')
        if not os.path.exists(txt):
            continue
        out.append({'board_slug': slug, 'board': r['board'], 'date': r['date'],
                    'file_id': r['file_id'], 'url': r['url'], 'text': txt,
                    'text_rel': os.path.relpath(txt, ROOT), 'stem': stem})
    return out


def out_path(a):
    return os.path.join(OUT, a['board_slug'], '%s-%s.json' % (a['date'], a['file_id']))


def normalise(s):
    return re.sub(r'\s+', ' ', s).strip().lower()


def write_one(a, force=False):
    path = out_path(a)
    sha = sha256_of(a['text'])
    if os.path.exists(path) and not force:
        have = json.load(open(path))
        if (have.get('source', {}).get('sha256') == sha and 'hook' in have.get('preview', {})
                and all('important' in it for it in have['preview'].get('items', []))):
            return 'current'
    raw = open(a['text'], encoding='utf-8', errors='replace').read()
    body = re.sub(r'^===PAGE \d+===$', '', raw, flags=re.M)
    if len(body.strip()) < 100:
        return 'too short to read'
    prompt = 'Board: %s. Agenda for %s.\n\n%s' % (a['board'], a['date'], body)
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    r = subprocess.run(['claude', '-p', '--tools', '', '--model', MODEL, '--system-prompt', SYSTEM,
                        '--json-schema', json.dumps(SCHEMA), '--output-format', 'json',
                        '--max-budget-usd', '1'],
                       input=prompt, capture_output=True, text=True, env=env, timeout=600)
    if r.returncode != 0:
        raise SystemExit('claude failed on %s:\n%s' % (a['text_rel'], (r.stdout + r.stderr)[-2000:]))
    res = json.loads(r.stdout)
    p = res.get('structured_output') or res.get('result')
    if isinstance(p, str):
        p = json.loads(p)
    if not isinstance(p, dict) or 'items' not in p:
        raise SystemExit('no structured output for %s' % a['text_rel'])
    # Every quoted line must be in the agenda. Drop any that is not, and say so.
    norm = normalise(body)
    kept, dropped = [], []
    for it in p['items']:
        (kept if normalise(it['agenda_line']) in norm else dropped).append(it)
    p['items'] = kept
    doc = {
        'what': 'A preview of a published agenda, for notice. An agenda lists what MAY be discussed; '
                'nothing here predicts an outcome. Every agenda_line is verbatim from the document.',
        'board_slug': a['board_slug'], 'board': a['board'], 'date': a['date'], 'file_id': a['file_id'],
        'agenda_url': a['url'],
        'agenda_text_url': '%s/docs/minutes/text/%s.txt' % (SITE, a['stem']),
        'source': {'text': a['text_rel'], 'sha256': sha},
        'written': {'by': 'scripts/write_agenda_preview.py', 'model': MODEL,
                    'at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'cost_usd': res.get('total_cost_usd'), 'lines_not_in_agenda_dropped': len(dropped)},
        'preview': p,
        'facebook': facebook_text(a, p),
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    return 'written ($%.3f, %d item(s), %d dropped)' % (res.get('total_cost_usd') or 0, len(kept), len(dropped))


def facebook_text(a, p):
    """Composed, not written: the notice a person pastes. Every line is the preview's own."""
    d = dt.date.fromisoformat(a['date'])
    head = '%s meets %s%s.' % (a['board'], d.strftime('%A %B %-d'),
                              (' at ' + p['time']) if p.get('time') and p['time'] != 'not stated' else '')
    lines = [head, (p.get('hook') or p['one_line']).rstrip('.') + '.']
    picks = [it for it in p['items'] if it.get('vote_expected')] or p['items']
    if picks:
        lines.append('On the agenda: ' + '; '.join(it['agenda_line'].strip().rstrip('.') for it in picks[:4]) + '.')
    if p.get('how_to_attend'):
        lines.append(p['how_to_attend'])
    lines.append('Agenda: ' + a['url'])
    return '\n\n'.join(lines)


def check():
    bad = n = 0
    for f in sorted(glob.glob(os.path.join(OUT, '*', '*.json'))):
        n += 1
        d = json.load(open(f, encoding='utf-8'))
        src = os.path.join(ROOT, d['source']['text'])
        if not os.path.exists(src):
            print('ORPHAN %s' % os.path.relpath(f, ROOT)); bad += 1; continue
        if sha256_of(src) != d['source']['sha256']:
            print('STALE %s: the agenda text changed' % os.path.relpath(f, ROOT)); bad += 1
        norm = normalise(re.sub(r'^===PAGE \d+===$', '', open(src, encoding='utf-8', errors='replace').read(), flags=re.M))
        for it in d['preview']['items']:
            if normalise(it['agenda_line']) not in norm:
                print('NOT IN AGENDA %s: %r' % (os.path.relpath(f, ROOT), it['agenda_line'][:60])); bad += 1
        if d.get('facebook') != facebook_text({'board': d['board'], 'date': d['date'], 'url': d['agenda_url']}, d['preview']):
            print('FACEBOOK TEXT DRIFTED %s' % os.path.relpath(f, ROOT)); bad += 1
    print('%d preview(s) checked, %d problem(s)' % (n, bad))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('board', nargs='?')
    ap.add_argument('date', nargs='?')
    ap.add_argument('--upcoming', action='store_true', help='every policy-board agenda dated today or later')
    ap.add_argument('--as-of', default=dt.date.today().isoformat())
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--status', action='store_true')
    a = ap.parse_args()
    if a.check:
        return check()
    if a.status:
        print('%d preview(s) held' % len(glob.glob(os.path.join(OUT, '*', '*.json'))))
        return 0
    if a.board and a.date:
        targets = agendas(a.board, a.date)
    elif a.upcoming:
        boards = policy_boards()
        targets = [x for x in agendas(upcoming_from=a.as_of) if x['board_slug'] in boards]
    else:
        ap.error('name a board and date, or --upcoming')
    if not targets:
        print('no agenda matches')
        return 0
    for t in targets:
        print('%s %s  %s' % (t['board_slug'], t['date'], write_one(t, force=a.force)), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
