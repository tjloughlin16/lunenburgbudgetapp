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


# SCHEMA 2: THE WHOLE OF THE MINUTES, NOT ONLY THE VOTES. TJ, 6 October 2026: process the
# official minutes "into a structured output that's read by Reconcile for sure." The
# fields MIRROR our minutes of a recording (write_recording_minutes.SCHEMA) so the two
# records of one meeting can be compared field by field -- where ours carries a video
# second `t`, these carry a verbatim `quote`, and every quote in every field is checked
# against the text exactly as votes always were. No headline and no summary: those are
# our prose, and nothing in this file is allowed to be anything but the town's record.
#
# A SUPERSET. `votes` is unchanged in name and shape, so everything that reads a version-1
# file reads a version-2 file the same way. A v1 file has no `schema` key.
SCHEMA_VERSION = 2

SYSTEM_V2 = SYSTEM.replace(
    'and listing every VOTE the minutes record.',
    'and recording what the minutes say happened: who attended, every vote, decisions taken '
    'without a vote, budget items and the figures printed for them, transfers, public comment, '
    'and the topics taken up.') + """

Beyond votes, also record -- each item with its own VERBATIM `quote` (20 to 300 characters) from the minutes, under the same rule as a vote's quote:
- `attendees`: every person the minutes name as taking part -- members, officials, staff, AND anyone who appeared before the board: presenters, applicants, their engineers or attorneys, consultants. `name` exactly as printed, `role` as printed ("Chair", "Town Manager", "representing the applicant"), `status` one of "present", "absent", "remote", "not stated" (a presenter who appeared is "present"). One attendance line may serve as the quote for several people.
- `decisions`: something the board decided or directed WITHOUT a recorded vote -- "the board agreed to...", "the chair directed staff to...", "tabled to the next meeting". Not a vote, and not mere discussion.
- `budget_items`: any matter where the minutes print a dollar figure or discuss money -- whether or not anything was decided: a cost reported, a price quoted, a cut described, a grant mentioned. `what_was_recorded` in one plain sentence, `figures_as_printed` every dollar figure exactly as the minutes print it.
- `transfers`: a reserve fund or line-item transfer, `amount_as_printed`, `outcome`.
- `public_comment`: each speaker in public comment, `speaker` and `stated_role` only as printed, `topic` in a few words.
- `topics`: each agenda item taken up, in order, with its `resolution` in a few words ("approved", "continued", "no action") and short `tags`.
- `tags`: a few short subject tags for the whole meeting, in plain words.
Record only what the minutes print. A field with nothing in it is an empty list."""

_Q = {'type': 'string', 'description': 'VERBATIM and contiguous from the minutes text'}


def _item(required, **props):
    props['quote'] = _Q
    return {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                                       'required': list(required) + ['quote'], 'properties': props}}


_S = {'type': 'string'}
SCHEMA_V2 = {
    'type': 'object', 'additionalProperties': False,
    'required': ['attendees', 'votes', 'decisions', 'budget_items', 'transfers',
                 'public_comment', 'topics', 'tags', 'note'],
    'properties': {
        'attendees': _item(['name', 'status'], name=_S, role=_S,
                           status={'type': 'string', 'enum': ['present', 'absent', 'remote', 'not stated']}),
        'votes': SCHEMA['properties']['votes'],
        'decisions': _item(['decision'], decision=_S),
        'budget_items': _item(['topic', 'what_was_recorded'], topic=_S, what_was_recorded=_S,
                              figures_as_printed={'type': 'array', 'items': _S}),
        'transfers': _item(['description', 'outcome'], description=_S, amount_as_printed=_S, outcome=_S),
        'public_comment': _item(['topic'], speaker=_S, stated_role=_S, topic=_S),
        'topics': _item(['topic', 'resolution'], topic=_S, resolution=_S,
                        tags={'type': 'array', 'items': _S}),
        'tags': {'type': 'array', 'items': _S},
        'note': SCHEMA['properties']['note'],
    },
}
# Every list whose items carry a quote. `check()` and the verifier walk exactly these.
QUOTED = ('attendees', 'votes', 'decisions', 'budget_items', 'transfers', 'public_comment', 'topics')


def schema_of(doc):
    """1 for a file written before schema 2, which carries no `schema` key."""
    return int(doc.get('schema') or 1)


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


def is_limit(text):
    """Is this the plan refusing, rather than one meeting failing? The sweep's own word
    list, imported rather than restated, so the two cannot disagree about what a limit is."""
    from sweep_backlog import HARD_LIMIT_WORDS
    low = text.lower()
    return any(w in low for w in HARD_LIMIT_WORDS)


def verify_quotes(items, flat):
    """(kept, dropped): the items whose quote is verbatim in `flat`, with the quote stored
    in its canonical form."""
    kept, dropped = [], 0
    for v in items:
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
    return kept, dropped


def ours_for(e):
    """(path, our minutes) for the meeting whose official minutes are `e`, or (None, None).
    Matched the way reconcile_minutes.py matches: our file names this very text as the
    town's minutes for its meeting."""
    import reconcile_minutes as R
    import write_recording_minutes as W
    for p in sorted(glob.glob(os.path.join(W.OUT, e['board_slug'], e['date'] + '-*.json'))):
        m = json.load(open(p, encoding='utf-8'))
        off_path, _ = R.official_for(m)
        if off_path and os.path.abspath(off_path) == os.path.abspath(e['path']):
            return p, m
    return None, None


# THE RECONCILE, FOLDED INTO THIS READ (TJ, 6 October 2026: "why do two model reads if we
# have everything we need from one?"). When our minutes of the recording already exist --
# the usual case, since the town's arrive weeks later -- the model has the town's full text
# in front of it anyway, so it compares the two in the same call. Same kinds, same schema
# and the same quote check as reconcile_minutes.py, imported from there, and written into
# our minutes file by the same function. Our minutes are an INPUT here and never rewritten
# apart from the reconciliation; they were written from the recording alone.
# OFF. Piloted 6 October 2026 on five meetings that already had a sonnet reconciliation:
# folded into a haiku read, the comparison matched 47 of sonnet's 114 findings and gave the
# same verdict on 28 -- on one meeting it called nothing `agree` where sonnet found eleven.
# The extraction in the same calls was BETTER than alone (83 of 114 items captured, from 74),
# so it is the comparison that suffers. Reconcile stays its own sonnet call, run right after
# this one by process_meeting.py. Turn this on only after a pilot proves a version of it.
FOLD_RECONCILE = os.environ.get('FOLD_RECONCILE') == '1'


def with_reconcile(system, schema):
    import reconcile_minutes as R
    sch = json.loads(json.dumps(schema))
    sch['required'] = sch['required'] + ['reconciliation']
    sch['properties']['reconciliation'] = R.SCHEMA
    return (system + "\n\nSECOND TASK, IN THE SAME ANSWER: `reconciliation`. OUR MINUTES of the same meeting, "
            "written by a model from the recording, are given after the official text. Compare them, under "
            "these instructions:\n\n" + R.SYSTEM.replace('Return only the JSON.', '').strip()), sch


def extract_one(e, force=False, schema=1, model=None, out_dir=None):
    path = out_path(e) if out_dir is None else os.path.join(out_dir, e['board_slug'], os.path.basename(out_path(e)))
    sha = sha256_of(e['path'])
    if os.path.exists(path) and not force:
        held = json.load(open(path))
        # CURRENT means the same text, read at least as deeply as asked. A v1 file is
        # current for a votes-only read and is NOT current when schema 2 is asked for --
        # that is the upgrade, one meeting at a time, and nothing else re-reads it.
        if held.get('source', {}).get('sha256') == sha and schema_of(held) >= schema:
            return 'current'
    text = open(e['path'], encoding='utf-8', errors='replace').read()
    if len(norm(text)) < MIN_CHARS:
        return 'no text'
    prompt = 'Board: %s. Meeting date: %s.\n\nMINUTES TEXT:\n\n%s' % (e['board_slug'].replace('-', ' ').title(), e['date'], text[:120_000])
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    system, sch = (SYSTEM_V2, SCHEMA_V2) if schema >= 2 else (SYSTEM, SCHEMA)
    ours_path, ours = ours_for(e) if (schema >= 2 and FOLD_RECONCILE) else (None, None)
    if ours:
        import reconcile_minutes as R
        system, sch = with_reconcile(system, sch)
        prompt += '\n\n=== OUR MINUTES (from the recording) ===\n' + R.ours_for_prompt(ours['minutes'])
    r = subprocess.run(['claude', '-p', '--tools', '', '--model', model or MODEL, '--system-prompt', system,
                        '--json-schema', json.dumps(sch), '--output-format', 'json', '--max-budget-usd', '1'],
                       input=prompt, capture_output=True, text=True, env=env, timeout=TIMEOUT)
    if r.returncode != 0:
        raise SystemExit('claude failed on %s:\n%s' % (e['rel'], (r.stdout + r.stderr)[-2000:]))
    res = json.loads(r.stdout)
    body = res.get('structured_output') or res.get('result')
    if isinstance(body, str):
        body = json.loads(body)
    if not isinstance(body, dict) or 'votes' not in body:
        raise SystemExit('no structured output for %s' % e['rel'])
    # THE QUOTE IS THE PROOF. An item whose quote is not in the minutes is dropped and
    # counted -- in every quoted field, by the same test votes always had.
    flat = canon(text)
    checked, dropped_by = {}, {}
    for field in (QUOTED if schema >= 2 else ('votes',)):
        checked[field], dropped_by[field] = verify_quotes(body.get(field) or [], flat)
    kept = checked['votes']
    dropped = sum(dropped_by.values())
    doc = {
        'warning': 'VOTES AS THE TOWN’S MINUTES STATE THEM, read by a language model from the extracted text. The minutes are the record; each row carries its quote from them, checked verbatim.',
        'board_slug': e['board_slug'], 'meeting_date': e['date'], 'docid': e['docid'],
        'source': {'text': e['rel'], 'sha256': sha, 'chars': len(text), 'minutes_url': upstream(e),
                   'doc_url': '/docs/meetings/' + e['board_slug'] + '/' + os.path.basename(e['path'])},
        'votes': kept, 'dropped_unquoted': dropped, 'note': body.get('note', ''),
        'cost_usd': res.get('total_cost_usd'),
    }
    rec = ''
    if ours and isinstance(body.get('reconciliation'), dict) and 'findings' in body['reconciliation']:
        import reconcile_minutes as R
        _, off = R.official_for(ours)
        official_text = re.sub(r'^===PAGE \d+===$', '', text, flags=re.M)
        # Pilot runs write NOTHING into our minutes: the comparison goes into the pilot
        # file instead, so a trial never changes a record the site reads.
        target = ours_path if out_dir is None else None
        counts = R.finish(target, ours, off, sha, official_text, body['reconciliation'], 'text',
                          model or MODEL, 'scripts/extract_official_votes.py (with the structured read)', None)
        if out_dir is not None:
            doc['reconciliation_pilot'] = ours['reconciliation']
        rec = '; reconciled: ' + ', '.join('%s %d' % (k, v) for k, v in counts.items() if v)
    if schema >= 2:
        doc['schema'] = SCHEMA_VERSION
        doc['model'] = model or MODEL
        doc['warning'] = ('THE TOWN’S MINUTES, STRUCTURED: who attended, votes, decisions, budget items, '
                          'transfers, public comment and topics, read by a language model from the '
                          'extracted text. The minutes are the record; every item carries its quote '
                          'from them, checked verbatim.')
        for field in QUOTED:
            doc[field] = checked[field]
        doc['tags'] = body.get('tags') or []
        doc['dropped_unquoted_by_field'] = {k: v for k, v in dropped_by.items() if v}
    # THE COST, PRINTED WHERE THE SWEEP CAN READ IT. It was already captured from
    # `claude -p --output-format json` and written into this file, and nowhere else --
    # so `sweep_backlog.py`, which scrapes stdout for a `$`, logged an EMPTY cost for
    # every run it has ever made. Its own docstring promises the week's scripted spend
    # is `a number and not a feeling`; it was a feeling. One line fixes it.
    if res.get('total_cost_usd') is not None:
        print('cost $%.4f' % res['total_cost_usd'])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    import reconcile_minutes as R
    R.atomic_json(path, doc)
    if schema >= 2:
        return 'wrote v2: %s%s%s ($%.3f)' % (', '.join('%d %s' % (len(checked[f]), f) for f in QUOTED),
                                             ', dropped %d unquoted' % dropped if dropped else '', rec,
                                             doc['cost_usd'] or 0)
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
        for field in QUOTED:
            for v in d.get(field) or []:
                votes += field == 'votes'
                if canon(v['quote']) not in flat:
                    bad.append('%s: %s quote not in the minutes: %r' % (p, field, v['quote'][:80]))
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
    ap.add_argument('--schema', type=int, default=1, choices=(1, 2),
                    help='2 = the whole minutes, structured (re-reads a v1 file); 1 = votes only')
    ap.add_argument('--model', default=None, help='override VOTES_MODEL for this run')
    ap.add_argument('--out', default=None, help='write here instead of sources/data/official-votes (a pilot)')
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
            r = extract_one(e, force=a.force, schema=a.schema, model=a.model, out_dir=a.out)
        except subprocess.TimeoutExpired:
            r = 'TIMED OUT after %ds -- skipped, will be retried next run' % TIMEOUT
            failed.append((e['board_slug'], e['date'], 'timeout'))
        except SystemExit as exc:
            # A LIMIT IS NOT A BAD MEETING. The guard above exists for one meeting the model
            # cannot digest; a usage or session limit refuses EVERY meeting, so swallowing it
            # turns the loop into a spin. On 6 October 2026 it did exactly that: this script
            # printed FAILED and exited 0, the sweep logged `ok`, saw no limit, and re-queued
            # the same 169 meetings for three and a half hours -- 5,145 refused calls, each
            # one taking the window the moment it reopened. Stop, and exit non-zero with the
            # CLI's own words, so the caller's limit check can see them.
            said = str(exc)
            if is_limit(said):
                print('  %s %s  REFUSED -- a limit; stopping the run' % (e['board_slug'], e['date']), flush=True)
                sys.exit('official votes: stopped at a limit after %d written. The CLI said:\n%s'
                         % (done, said[-600:]))
            r = 'FAILED -- skipped, will be retried next run: %s' % said[:160]
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
        # NON-ZERO, so a caller can tell a run that wrote nothing from one that worked.
        # Exiting 0 here is what let the sweep log 5,145 failures as `ok`.
        sys.exit(1)


if __name__ == '__main__':
    main()
