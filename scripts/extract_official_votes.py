#!/usr/bin/env python3
"""The votes in the TOWN'S minutes, one file per set of minutes, each vote with the words
the minutes used for it.

    python3 scripts/extract_official_votes.py --board parks-commission          # every set of minutes, newest first
    python3 scripts/extract_official_votes.py --board parks-commission --limit 5
    python3 scripts/extract_official_votes.py parks-commission 2026-06-24       # one meeting
    python3 scripts/extract_official_votes.py --check                          # every file: quotes verbatim, source unchanged
    python3 scripts/extract_official_votes.py --status

WHY. TJ, 17 September 2026: "i noticed parks doesnt have any 'votes' listed ... I assumed
votes would be a combination of the transcript processing as well as the official
minutes, joined and deduped." Until now a board's votes came only from OUR minutes of
its recordings; a board with no transcript showed none, however many minutes the town
had posted. The town's minutes are the record, and they are read here for the votes
they state.

WHAT A ROW IS. A vote AS THE MINUTES STATE IT: the motion, the outcome, who moved it
where the minutes say, and -- the part that makes it checkable -- a short VERBATIM quote
from the minutes that records the vote. `--check` fails if any quote is not in the text
it claims to come from, which is rule 13 applied to an extraction: the model may
paraphrase the motion, but the quote is the town's own words or the row is refused.

WHERE THEY LIVE. `sources/data/official-votes/<board>/<date>-<docid>.json`, in git,
each with the sha256 of the minutes text it was read from. scripts/build_boards.py joins
them with our recording minutes' votes, deduplicated per meeting.
"""
import argparse
import csv
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT = os.path.join(ROOT, 'sources', 'meetings', 'text')
OUT = os.path.join(ROOT, 'sources', 'data', 'official-votes')
INDEX = os.path.join(ROOT, 'sources', 'meetings', 'index.csv')
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
# How long one meeting may take before it is skipped and left for the next run.
TIMEOUT = 600
MODEL = os.environ.get('VOTES_MODEL', 'haiku')
MIN_CHARS = 400          # a minutes file shorter than this is a stub or a scan with no text

SYSTEM = """You are reading the OFFICIAL MINUTES of a meeting of a town board in Lunenburg, Massachusetts, as extracted text, and listing every VOTE the minutes record.

Rules:
- A vote is a motion the minutes say was voted on: "motion by X, seconded by Y, to ...; vote 5-0", "unanimously approved", "so voted", "the motion carried/failed". Include votes to approve prior minutes, adjourn, enter executive session -- and mark those `procedural: true`.
- `motion`: what was moved, in one plain sentence, paraphrased from the minutes. Keep dollar amounts and names exactly as the minutes print them.
- `outcome`: "passed", "failed", a count exactly as printed like "passed 4-0" or "passed 3-1-1", or "not stated" if the minutes record a motion but no result.
- `moved_by` and `seconded_by`: names exactly as printed, only if printed.
- `quote`: a VERBATIM excerpt of the minutes, 20 to 200 characters, copied character for character (including odd spacing or line breaks collapsed to single spaces), that records this vote. It will be checked against the text; if it is not verbatim the vote is discarded.
- Do not invent a vote from a discussion. If the minutes describe a discussion with no motion, it is not a vote.
- If the text is a scan with no readable votes, return an empty list and say so in `note`."""

SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['votes', 'note'],
    'properties': {
        'votes': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False,
            'required': ['motion', 'outcome', 'procedural', 'quote'],
            'properties': {
                'motion': {'type': 'string'},
                'outcome': {'type': 'string'},
                'procedural': {'type': 'boolean'},
                'moved_by': {'type': 'string'},
                'seconded_by': {'type': 'string'},
                'quote': {'type': 'string', 'description': 'CONTIGUOUS and verbatim: start at the words that make the motion ("X moved to ...") and copy forward without skipping anything'},
            }}},
        'note': {'type': 'string', 'description': 'anything about the text that limits the reading: a scan, pages missing, no votes recorded. Empty string if nothing.'},
    },
}


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


STRAIGHT = str.maketrans({'\u2019': "'", '\u2018': "'", '\u201c': '"', '\u201d': '"', '\u2013': '-', '\u2014': '-', '\u00a0': ' '})


def canon(s):
    """Single-spaced, quotes straightened, lower-cased: the form both the minutes and a
    quote are compared in, and the form a quote is stored in."""
    return re.sub(r'\s+', ' ', s.translate(STRAIGHT)).strip().lower()


def squash(s):
    """For the verbatim test: whitespace-free and with curly quotes straightened, because
    the extracted text breaks lines mid-word ("D. Burns-\naye") and prints O’Dall with a
    curly apostrophe the model renders straight -- both are still the town's words."""
    return re.sub(r'\s+', '', s).translate(str.maketrans({'\u2019': "'", '\u2018': "'", '\u201c': '"', '\u201d': '"', '\u2013': '-', '\u2014': '-'})).lower()


def sha256_of(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def minutes_files(board=None):
    pat = os.path.join(TEXT, board or '*', '*-minutes-*.txt')
    out = []
    for p in sorted(glob.glob(pat), reverse=True):
        m = re.match(r'(\d{4}-\d{2}-\d{2})-minutes-(\w+)\.txt$', os.path.basename(p))
        if not m:
            continue
        out.append(dict(path=p, rel=os.path.relpath(p, ROOT), board_slug=os.path.basename(os.path.dirname(p)),
                        date=m.group(1), docid=m.group(2)))
    # NEWEST FIRST ACROSS EVERY BOARD, not board by board: the last two years matter more
    # than any one board's depth (TJ, 17 September 2026).
    out.sort(key=lambda e: e['date'], reverse=True)
    return out


def out_path(e):
    return os.path.join(OUT, e['board_slug'], '%s-%s.json' % (e['date'], e['docid']))


def upstream(e):
    """The town's own URL for these minutes, from the meetings index."""
    for r in csv.DictReader(open(INDEX, encoding='utf-8')):
        if r.get('path', '').endswith('/%s-minutes-%s.pdf' % (e['date'], e['docid'])) or r.get('path', '').endswith('/%s-minutes-%s.docx' % (e['date'], e['docid'])):
            return r.get('url') or ''
    return ''


def extract_one(e, force=False):
    path = out_path(e)
    sha = sha256_of(e['path'])
    if os.path.exists(path) and not force:
        if json.load(open(path)).get('source', {}).get('sha256') == sha:
            return 'current'
    text = open(e['path'], encoding='utf-8', errors='replace').read()
    if len(norm(text)) < MIN_CHARS:
        return 'no text'
    prompt = 'Board: %s. Meeting date: %s.\n\nMINUTES TEXT:\n\n%s' % (e['board_slug'].replace('-', ' ').title(), e['date'], text[:120_000])
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    r = subprocess.run(['claude', '-p', '--tools', '', '--model', MODEL, '--system-prompt', SYSTEM,
                        '--json-schema', json.dumps(SCHEMA), '--output-format', 'json', '--max-budget-usd', '1'],
                       input=prompt, capture_output=True, text=True, env=env, timeout=TIMEOUT)
    if r.returncode != 0:
        raise SystemExit('claude failed on %s:\n%s' % (e['rel'], (r.stdout + r.stderr)[-2000:]))
    res = json.loads(r.stdout)
    body = res.get('structured_output') or res.get('result')
    if isinstance(body, str):
        body = json.loads(body)
    if not isinstance(body, dict) or 'votes' not in body:
        raise SystemExit('no structured output for %s' % e['rel'])
    # THE QUOTE IS THE PROOF. A vote whose quote is not in the minutes is dropped and counted.
    flat = canon(text)
    kept, dropped = [], 0
    for v in body['votes']:
        q = canon(v.get('quote', ''))
        if len(q) < 20:
            dropped += 1
            continue
        if q in flat:
            v['quote'] = q
            kept.append(v)
            continue
        # THE MODEL ABRIDGED IT ("... The motion pass" with the roll call skipped). If the
        # quote's opening is verbatim, take the town's own words from that point for the
        # same length instead -- the stored quote is then the minutes, not the model.
        head = q[:40]
        i = flat.find(head) if len(head) >= 40 else -1
        if i >= 0:
            v['quote'] = flat[i:i + len(q)]
            v['quote_taken_from_text'] = True
            kept.append(v)
        else:
            dropped += 1
    doc = {
        'warning': 'VOTES AS THE TOWN’S MINUTES STATE THEM, read by a language model from the extracted text. The minutes are the record; each row carries its quote from them, checked verbatim.',
        'board_slug': e['board_slug'], 'meeting_date': e['date'], 'docid': e['docid'],
        'source': {'text': e['rel'], 'sha256': sha, 'chars': len(text), 'minutes_url': upstream(e),
                   'doc_url': '/docs/meetings/' + e['board_slug'] + '/' + os.path.basename(e['path'])},
        'votes': kept, 'dropped_unquoted': dropped, 'note': body.get('note', ''),
        'cost_usd': res.get('total_cost_usd'),
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    return 'wrote %d vote(s)%s ($%.3f)' % (len(kept), ', dropped %d unquoted' % dropped if dropped else '', doc['cost_usd'] or 0)


def check():
    bad, n, votes = [], 0, 0
    for p in sorted(glob.glob(os.path.join(OUT, '*', '*.json'))):
        d = json.load(open(p))
        n += 1
        src = os.path.join(ROOT, d['source']['text'])
        if not os.path.exists(src):
            bad.append('%s: source text gone' % p); continue
        if sha256_of(src) != d['source']['sha256']:
            bad.append('%s: source text changed since it was read' % p); continue
        flat = canon(open(src, encoding='utf-8', errors='replace').read())
        for v in d['votes']:
            votes += 1
            if canon(v['quote']) not in flat:
                bad.append('%s: quote not in the minutes: %r' % (p, v['quote'][:80]))
    if bad:
        sys.exit('official votes: %d problem(s)\n  ' % len(bad) + '\n  '.join(bad))
    print('official votes: %d files, %d votes, every quote verbatim in its minutes' % (n, votes))


def status():
    files = minutes_files()
    have = {os.path.relpath(p, OUT)[:-5] for p in glob.glob(os.path.join(OUT, '*', '*.json'))}
    by = {}
    for e in files:
        b = by.setdefault(e['board_slug'], [0, 0])
        b[0] += 1
        if '%s/%s-%s' % (e['board_slug'], e['date'], e['docid']) in have:
            b[1] += 1
    for k, (t, h) in sorted(by.items(), key=lambda x: -x[1][0]):
        print('  %-50s %3d of %3d read' % (k, h, t))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('board', nargs='?')
    ap.add_argument('date', nargs='?')
    ap.add_argument('--board', dest='board_opt')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--status', action='store_true')
    a = ap.parse_args()
    if a.check:
        return check()
    if a.status:
        return status()
    board = a.board_opt or a.board
    files = minutes_files(board)
    if a.date:
        files = [e for e in files if e['date'] == a.date]
    done, failed = 0, []
    for e in files:
        # ONE BAD MEETING MUST NOT END THE RUN. `extract_one` raises SystemExit on a
        # non-zero exit or missing structured output, and `subprocess.run(timeout=600)`
        # raises TimeoutExpired -- none of which was caught, so the first meeting the
        # model chewed on for ten minutes killed the loop and everything behind it.
        #
        # On 23 September 2026 that cost 19 of the run's 40 meetings: 21 written, one
        # slow minute set, and the process gone. The queue is capped precisely BECAUSE
        # this stream is metered, so there is no slack to absorb a whole run.
        #
        # The term for what was missing is a POISON PILL guard: one item a consumer
        # cannot digest must not be able to stop the consumer. The failure is recorded
        # against the meeting and the loop moves on -- and because a meeting is only
        # written when it succeeds, a skipped one is simply first in line next time.
        try:
            r = extract_one(e, force=a.force)
        except subprocess.TimeoutExpired:
            r = 'TIMED OUT after %ds -- skipped, will be retried next run' % TIMEOUT
            failed.append((e['board_slug'], e['date'], 'timeout'))
        except SystemExit as exc:
            r = 'FAILED -- skipped, will be retried next run: %s' % str(exc)[:160]
            failed.append((e['board_slug'], e['date'], 'failed'))
        print('  %s %s  %s' % (e['board_slug'], e['date'], r))
        if r.startswith('wrote'):
            done += 1
            if a.limit and done >= a.limit:
                break
    if failed:
        print('\n%d meeting(s) skipped and still queued:' % len(failed))
        for b, d, why in failed:
            print('  %-44s %s  %s' % (b, d, why))


if __name__ == '__main__':
    main()
