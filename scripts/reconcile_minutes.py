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


def structured_official(off_path, sha):
    """The town's minutes as a SCHEMA-2 read, if one exists for exactly this text, else None.

    TWO STATES, BOTH VALID, FOR A WHILE. TJ, 6 October 2026: the official minutes are being
    moved to a structured read that mirrors ours, so reconcile compares like with like -- and
    the 4,574 sets already read for votes only stay as they are until somebody asks for them
    to be re-read. So this prefers the structured file and falls back to the raw text, and
    every reconciliation records which one it compared against."""
    import extract_official_votes as E
    m = re.search(r'(\d{4}-\d{2}-\d{2})-minutes-(\w+)\.txt$', off_path)
    if not m:
        return None
    board = os.path.basename(os.path.dirname(off_path))
    p = os.path.join(E.OUT, board, '%s-%s.json' % (m.group(1), m.group(2)))
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding='utf-8'))
    if E.schema_of(d) < 2 or d.get('source', {}).get('sha256') != sha:
        return None
    return d


def official_for_prompt(d):
    """A schema-2 read, rendered in the same sections as ours_for_prompt, each item with
    the verbatim quote the extractor already checked against the minutes."""
    def sec(title, items, fmt):
        return ['', title] + (['- %s\n  QUOTE: "%s"' % (fmt(x), x['quote']) for x in items] or ['- none'])
    out = ['(Structured from the official minutes. Every QUOTE is verbatim from them -- copy a QUOTE as the `official` text.)']
    out += sec('VOTES (non-procedural):', [v for v in d['votes'] if not v.get('procedural')],
               lambda v: '%s — %s' % (v['motion'], v['outcome']))
    out += sec('TRANSFERS:', d.get('transfers', []),
               lambda t: '%s — %s (%s)' % (t['description'], t.get('amount_as_printed', ''), t['outcome']))
    out += sec('BUDGET ITEMS (figures as printed):', d.get('budget_items', []),
               lambda b: '%s: %s [%s]' % (b['topic'], b['what_was_recorded'], ', '.join(b.get('figures_as_printed') or [])))
    out += sec('DECISIONS:', d.get('decisions', []), lambda x: x['decision'])
    out += sec('ATTENDEES:', d.get('attendees', []),
               lambda a: '%s (%s) %s' % (a['name'], a.get('role', ''), a['status']))
    out += sec('PUBLIC COMMENT:', d.get('public_comment', []),
               lambda c: '%s%s' % (c['topic'], ' -- ' + c['speaker'] if c.get('speaker') else ''))
    return '\n'.join(out)


def atomic_json(path, obj, indent=1):
    """Write JSON so a crash leaves the old file or the new one, never half of either."""
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, indent=indent, ensure_ascii=False)
        fh.write('\n')
    os.replace(tmp, path)


def finish(path, m, off, sha, official_text, body, against, model, by, cost):
    """Check a comparison's quotes against the town's text and write it into our minutes.
    ONE PLACE, so a reconcile done here and one folded into the structured read of the
    town's minutes (extract_official_votes.py) are the same object, checked the same way."""
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
        # WHICH FORM OF THE TOWN'S MINUTES THIS COMPARED AGAINST. `structured` = the
        # schema-2 read; `text` = the raw minutes, which is every reconciliation written
        # before 6 October 2026 (they carry no key; read a missing one as `text`).
        'against': against,
        'coverage': body['coverage'],
        'summary': body['summary'],
        'counts': counts,
        'findings': kept,
        'quotes_not_in_official_dropped': dropped,
        'written': {'by': by, 'model': model,
                    'at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'cost_usd': cost},
    }
    if path:
        atomic_json(path, m)
    return counts


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
    structured = structured_official(off_path, sha)
    against = 'structured' if structured else 'text'
    prompt = ('Meeting: %s, %s.\n\n=== OUR MINUTES (from the recording) ===\n%s\n\n=== OFFICIAL MINUTES (the town\'s) ===\n%s'
              % (m['board'], m['meeting_date'], ours_for_prompt(m['minutes']),
                 official_for_prompt(structured) if structured else official_text))
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
    counts = finish(path, m, off, sha, official_text, body, against, MODEL,
                    'scripts/reconcile_minutes.py', res.get('total_cost_usd'))
    return 'reconciled against %s ($%.3f): %s' % (against, res.get('total_cost_usd') or 0,
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
    # A CAP, BECAUSE THIS ONE NEVER HAD ONE. Every other model step in refresh.py is
    # bounded -- MAX_MINUTES_PER_RUN, MAX_OFFICIAL_VOTES_PER_RUN, MAX_OCR_PER_RUN -- and
    # this was added without one and called bare, so it walked the whole backlog every
    # day. On 28 September 2026 it ran two hours, made 89 model calls and spent $22.73
    # API-equivalent before it was killed, with about 157 pairs still to go: another four
    # and a half hours and roughly a tenth of the week's allowance, in one step of one run.
    ap.add_argument('--limit', type=int, default=0,
                    help='at most this many reconciliations; 0 means no cap')
    # `--since` FILTERS ON THE MEETING DATE, WHICH IS NOT WHEN THE WORK ARRIVED, and that
    # is why the daily run does not use it.
    #
    # TJ, 28 September 2026: *"there may be a meeting from a year ago, that only recently
    # had its transcript filled in, or its minutes added. So the NEW is relevant to new
    # files/info created/pushed out by the boards/depts, not based on the meeting dates...
    # otherwise we'll miss things."*
    #
    # He is right and this flag was briefly wired into refresh.py, where it would have
    # pruned exactly that case out of the daily run -- and since sweep_backlog.py has no
    # reconcile stream, out of every run. A pair becomes eligible when the town publishes
    # its minutes, which can be a year after the meeting, and `sources/meetings/index.csv`
    # records no fetch date to filter on. So the daily run EXCLUDES NOTHING and is bounded
    # by `--limit` alone, newest first: a meeting that becomes eligible today is reached
    # within a day or two whatever its date, and nothing is ever permanently skipped.
    # The flag stays for working one span by hand.
    ap.add_argument('--since', default='',
                    help='only meetings on or after this date -- for working a span by '
                         'hand; the daily run does not use it, see the note in the code')
    a = ap.parse_args()
    if a.check:
        return check()
    # NEWEST MEETING FIRST, so a bounded run spends its budget on what a reader is most
    # likely to be looking at, and an old pair that only just became eligible is still
    # reached within a day or two rather than never.
    files = sorted(glob.glob(os.path.join(W.OUT, '*', '*.json')),
                   key=lambda f: (os.path.basename(f)[:10], f), reverse=True)
    if a.board and a.date:
        files = [f for f in files if a.board in f and os.path.basename(f).startswith(a.date)]
    if a.status:
        both = sum(1 for f in files if official_for(json.load(open(f)))[0])
        done = sum(1 for f in files if json.load(open(f)).get('reconciliation'))
        print('%d minutes file(s); %d have official minutes; %d reconciled' % (len(files), both, done))
        return 0
    # COUNT WHAT IS SPENT, NOT WHAT IS LOOKED AT. `files` is every minutes file; most are
    # already reconciled or have no official minutes to compare against, and skipping one
    # costs nothing. The limit therefore counts the ones that actually CALLED the model.
    spent, pending = 0, 0
    if a.since:
        files = [f for f in files
                 if (json.load(open(f)).get('meeting_date') or '') >= a.since]
    for f in files:
        if a.limit and spent >= a.limit:
            pending += 1
            continue
        before = json.load(open(f)).get('reconciliation')
        out = reconcile(f, force=a.force)
        after = json.load(open(f)).get('reconciliation')
        if after and after is not before:
            spent += 1
        print('%s  %s' % (os.path.relpath(f, W.OUT), out), flush=True)
    if pending:
        print('%d reconciliation(s) done this run (--limit %d); %d file(s) not looked at '
              '-- they wait for tomorrow' % (spent, a.limit, pending), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
