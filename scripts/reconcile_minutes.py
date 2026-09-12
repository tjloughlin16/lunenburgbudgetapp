#!/usr/bin/env python3
"""Our minutes of a recording, against the minutes the town published for the same meeting.

    python3 scripts/reconcile_minutes.py                 # every meeting with both, not yet reconciled
    python3 scripts/reconcile_minutes.py school-committee 2026-06-24
    python3 scripts/reconcile_minutes.py --force ...     # redo one
    python3 scripts/reconcile_minutes.py --check         # every reconciliation names the official text it read
    python3 scripts/reconcile_minutes.py --status

TWO RECORDS, AND NEITHER IS THE REFEREE. TJ, 12 September 2026: *"I dont want to just
unilaterally accept their minutes as truth. If there truly is a difference in what was
documented vs what we think, that's a flag. but if its just our recording reading being
wrong or mistranslated, thats what this is intending to fix."*

So every difference is sorted into one of two kinds, and they are treated oppositely:

  caption_error   the same fact, rendered badly by the caption model: a figure's digits,
                  a mangled name, a misheard count. The town's minutes RESOLVE these. We
                  record the official reading BESIDE the as-heard one -- never over it --
                  and the page shows both, with the second of video, so a reader can
                  check which is right.

  discrepancy     a substantive difference: a vote the recording carries and the minutes
                  do not, or the reverse; outcomes that differ; an amount that differs by
                  more than digits could explain; a decision recorded one way and heard
                  another. These are FLAGGED, on the meeting page and on the index, with
                  both readings and the timestamp. Nothing is corrected. Which record is
                  right is exactly the question, and it is a question for a person.

Plus `agree` (the same in both) and `only_in_ours` / `only_in_official`, each counted so
the page can say how much of the meeting the two records share.

WHAT IT READS. Our minutes file (votes, transfers, budget items with figures as heard,
decisions) and the town's extracted minutes text. The town's text is a DOCUMENT, so the
model may quote it and `--check` asserts every quote is in the file. The official
minutes' sha256 is stored, and a re-fetched official document invalidates the
reconciliation rather than silently outliving it.

Run by `refresh.py` after the minutes step: official minutes appear weeks after a
meeting, so this is re-tried daily until they exist.
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
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import write_recording_minutes as W  # noqa: E402

NODE22 = W.NODE22
MODEL = W.MODEL
TEXT = os.path.join(ROOT, 'sources', 'meetings', 'text')

KINDS = ['agree', 'caption_error', 'discrepancy', 'only_in_ours', 'only_in_official']

SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['findings', 'coverage', 'summary'],
    'properties': {
        'findings': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False,
            'required': ['kind', 'about', 'ours', 'official', 'note'],
            'properties': {
                'kind': {'type': 'string', 'enum': KINDS},
                'about': {'type': 'string', 'description': 'what is being compared: a vote, a transfer, a figure, a decision, an attendee -- one short phrase'},
                't': {'type': 'integer', 'description': 'the second in the recording from our minutes, where one applies'},
                'ours': {'type': 'string', 'description': 'exactly what our minutes say, or "" if only the official minutes have it'},
                'official': {'type': 'string', 'description': 'the official minutes text, QUOTED VERBATIM, or "" if only ours has it'},
                'official_reading': {'type': 'string', 'description': 'for caption_error only: the figure or name as the official minutes give it, alone'},
                'note': {'type': 'string', 'description': 'one sentence: why this kind, and for a discrepancy what a person should check'},
            }}},
        'coverage': {'type': 'string', 'enum': ['full', 'partial', 'official minutes are a summary only'],
                     'description': 'how much of the meeting the official minutes record'},
        'summary': {'type': 'string', 'description': 'two sentences: how closely the two records agree, and the one thing a reader should know about where they differ'},
    },
}

SYSTEM = """You compare two records of the same public meeting: OUR minutes (written by a model from machine captions of the video, so figures and names may be misheard) and the OFFICIAL minutes the town published (written by a person; may be a summary; may omit things).

Sort every difference into exactly one kind:
- caption_error: the same fact, rendered badly by the captions. Digit grouping ("$81,75.96" vs "$8,175.96"), a misheard name, a misheard count where the words are otherwise the same item. Give official_reading.
- discrepancy: a SUBSTANTIVE difference. A vote in one record and not the other; outcomes that differ; an amount that differs beyond what misheard digits explain; a decision described one way and the other way. Do not resolve it. Say what a person should check.
- agree: the same in both.
- only_in_ours / only_in_official: an item one record has and the other does not, where it is not a vote or a decision (those are discrepancies).

Rules:
1. official is QUOTED VERBATIM from the official text. It will be checked against the file.
2. Never treat the official minutes as automatically right. A discrepancy stays a discrepancy.
3. Compare every non-procedural vote, every transfer, every figure in figures_as_heard, every decision, and the attendees. Skip the pledge and adjournment.
4. Be concrete. "The minutes do not record this vote" is a finding; "minutes are shorter" is not.

Return only the JSON."""


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def normalise(s):
    return re.sub(r'[^a-z0-9$%.]+', ' ', s.lower()).strip()


def official_for(m):
    """The town's minutes text for this meeting, from the links our minutes already carry."""
    for d in m.get('town_published', []):
        if d['kind'] == 'minutes':
            stem = os.path.splitext(d['path'].replace('sources/meetings/', ''))[0]
            p = os.path.join(TEXT, stem + '.txt')
            if os.path.exists(p):
                return p, d
    return None, None


def ours_for_prompt(mm):
    out = ['VOTES (non-procedural):']
    out += ['- [t=%d] %s — %s' % (v['t'], v['motion'], v['outcome']) for v in mm['votes'] if not v.get('procedural')] or ['- none']
    out += ['', 'TRANSFERS:'] + ['- [t=%d] %s — %s (%s)' % (t['t'], t['description'], t.get('amount_as_heard', ''), t['outcome']) for t in mm['transfers']] or ['- none']
    out += ['', 'FIGURES AS HEARD (budget items):']
    out += ['- [t=%d] %s: %s' % (b['t'], b['topic'], ', '.join(b.get('figures_as_heard') or [])) for b in mm['budget_items'] if b.get('figures_as_heard')] or ['- none']
    out += ['', 'DECISIONS:'] + ['- [t=%d] %s' % (d['t'], d['decision']) for d in mm['decisions']] or ['- none']
    out += ['', 'ATTENDEES (as heard):'] + ['- %s (%s)' % (a['name_as_heard'], a['role']) for a in mm.get('attendees', [])] or ['- none']
    return '\n'.join(out)


def reconcile(path, force=False):
    m = json.load(open(path, encoding='utf-8'))
    off_path, off = official_for(m)
    if not off_path:
        return 'no official minutes yet'
    sha = sha256_of(off_path)
    have = m.get('reconciliation')
    if have and have.get('official_sha256') == sha and not force:
        return 'current'
    raw = open(off_path, encoding='utf-8', errors='replace').read()
    official_text = re.sub(r'^===PAGE \d+===$', '', raw, flags=re.M)
    prompt = ('Meeting: %s, %s.\n\n=== OUR MINUTES (from the recording) ===\n%s\n\n=== OFFICIAL MINUTES (the town\'s) ===\n%s'
              % (m['board'], m['meeting_date'], ours_for_prompt(m['minutes']), official_text))
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    r = subprocess.run(['claude', '-p', '--tools', '', '--model', MODEL, '--system-prompt', SYSTEM,
                        '--json-schema', json.dumps(SCHEMA), '--output-format', 'json',
                        '--max-budget-usd', '1.5'],
                       input=prompt, capture_output=True, text=True, env=env, timeout=900)
    if r.returncode != 0:
        raise SystemExit('claude failed reconciling %s:\n%s' % (path, (r.stdout + r.stderr)[-2000:]))
    res = json.loads(r.stdout)
    body = res.get('structured_output') or res.get('result')
    if isinstance(body, str):
        body = json.loads(body)
    # Every official quote must be in the official text; a finding whose quote is not is
    # dropped and counted, never published.
    norm = normalise(official_text)
    kept, dropped = [], 0
    for f in body['findings']:
        if f.get('official') and normalise(f['official']) not in norm:
            dropped += 1
            continue
        kept.append(f)
    counts = {k: sum(1 for f in kept if f['kind'] == k) for k in KINDS}
    m['reconciliation'] = {
        'what': 'Our minutes against the minutes the town published. caption_error = the same fact the captions '
                'rendered badly, resolved by the official reading shown beside the as-heard one; discrepancy = a '
                'substantive difference, flagged and not resolved. Neither record is treated as the referee.',
        'official': {'url': off['url'], 'text_url': off['text_url'], 'path': off['path']},
        'official_sha256': sha,
        'coverage': body['coverage'],
        'summary': body['summary'],
        'counts': counts,
        'findings': kept,
        'quotes_not_in_official_dropped': dropped,
        'written': {'by': 'scripts/reconcile_minutes.py', 'model': MODEL,
                    'at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'cost_usd': res.get('total_cost_usd')},
    }
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(m, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    return 'reconciled ($%.3f): %s' % (res.get('total_cost_usd') or 0,
                                      ', '.join('%s %d' % (k, n) for k, n in counts.items() if n))


def check():
    bad = n = 0
    for f in sorted(glob.glob(os.path.join(W.OUT, '*', '*.json'))):
        m = json.load(open(f, encoding='utf-8'))
        rc = m.get('reconciliation')
        if not rc:
            continue
        n += 1
        p = os.path.join(ROOT, rc['official']['path'])
        stem = os.path.splitext(rc['official']['path'].replace('sources/meetings/', ''))[0]
        t = os.path.join(TEXT, stem + '.txt')
        if not os.path.exists(t):
            print('ORPHAN %s: official text gone' % os.path.relpath(f, ROOT)); bad += 1; continue
        if sha256_of(t) != rc['official_sha256']:
            print('STALE %s: the official minutes changed since reconciliation' % os.path.relpath(f, ROOT)); bad += 1
        norm = normalise(re.sub(r'^===PAGE \d+===$', '', open(t, encoding='utf-8', errors='replace').read(), flags=re.M))
        for x in rc['findings']:
            if x.get('official') and normalise(x['official']) not in norm:
                print('QUOTE NOT IN OFFICIAL %s: %r' % (os.path.relpath(f, ROOT), x['official'][:60])); bad += 1
    print('%d reconciliation(s) checked, %d problem(s)' % (n, bad))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('board', nargs='?')
    ap.add_argument('date', nargs='?')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--status', action='store_true')
    a = ap.parse_args()
    if a.check:
        return check()
    files = sorted(glob.glob(os.path.join(W.OUT, '*', '*.json')))
    if a.board and a.date:
        files = [f for f in files if a.board in f and os.path.basename(f).startswith(a.date)]
    if a.status:
        both = sum(1 for f in files if official_for(json.load(open(f)))[0])
        done = sum(1 for f in files if json.load(open(f)).get('reconciliation'))
        print('%d minutes file(s); %d have official minutes; %d reconciled' % (len(files), both, done))
        return 0
    for f in files:
        print('%s  %s' % (os.path.relpath(f, W.OUT), reconcile(f, force=a.force)), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
