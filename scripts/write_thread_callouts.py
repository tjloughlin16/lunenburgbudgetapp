#!/usr/bin/env python3
"""WHAT SOMEONE SAYS NEXT, picked by a model for every thread -- and checked before it shows.

    python3 scripts/write_thread_callouts.py                 # open threads whose record changed
    python3 scripts/write_thread_callouts.py --all           # every open thread, changed or not
    python3 scripts/write_thread_callouts.py tc-passios-site # one thread
    python3 scripts/write_thread_callouts.py --dry-run       # which would run, and the prompt; spends nothing

TJ, 19 October 2026: *"if someone walked up to me and said 'did you hear about TC Passios?!'
what will they say next? 'Theres an article to vote for its demolition, that'll cost 1-4
million!'"*, then *"I was hoping this was a mechanism automatically applied to threads"*, and
*"we need this accurate always"*.

SO THE MODEL PICKS AND THE BUILD DECIDES. Which figure is a thread's stake is judgement -- a
rule picks the basement slab over the $21M plan -- so `claude -p` reads the thread's record and
answers the hallway question. It is given the record as numbered items and may only quote
them. What it returns is written to sources/data/thread-callouts-auto/<thread>.json and is
nothing yet: build_threads.py checks every callout exactly as it checks a person's row --
the quote must be in its source (the town's minutes for a printed one, the captions or our
notes for a heard one), and every number in the value must be in the quote or in what that
meeting was heard to say -- and DROPS any that fails. A wrong callout never shows; a thread
with none shows none.

A PERSON'S ROW WINS. A thread with any row in sources/data/thread-callouts.csv is skipped here.

COST. Sonnet, several threads to a call (CHUNK_CHARS), capped at $0.50 a thread. It runs only when the record a thread is
given has changed since its last pick (the input's sha256 is stored), so the daily refresh
spends on the threads that moved and nothing else. Every call is appended to
sources/data/agentic-spend.csv under the stream `callouts`.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import claude_lean
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREADS = os.path.join(ROOT, 'fy28', 'public', 'data', 'threads.json')
CURATED = os.path.join(ROOT, 'sources', 'data', 'thread-callouts.csv')
OUT = os.path.join(ROOT, 'sources', 'data', 'thread-callouts-auto')
MINUTES = os.path.join(ROOT, 'sources', 'data', 'recording-minutes')
TRANSCRIPTS = os.path.join(ROOT, 'sources', 'data', 'youtube-transcripts')
SPEND = os.path.join(ROOT, 'sources', 'data', 'agentic-spend.csv')
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
MODEL = 'sonnet'
VERSION = 2            # bump to re-pick every thread after a prompt change
# THREADS PER CALL. The first pass made one call a thread and each cost ~$0.23 however small
# the thread -- a fixed overhead per call. So threads are batched up to this many characters
# of record; the first pass would have been three calls instead of seventeen.
CHUNK_CHARS = 150_000

SYSTEM = """You pick the CALLOUTS for one matter the town of Lunenburg, Massachusetts is deciding.

The test is the hallway: if a resident said "did you hear about <this>?!", what would they say
NEXT? A callout is that next sentence, split into a VALUE and a LABEL -- for example value
"$1M-$4M", label "estimated cost to demolish the building"; or value "Nov 17", label "Town
Meeting votes a non-binding question on demolishing it". A count of meetings is never a
callout. A procedural step is never a callout.

KINDS, in roughly this order of interest:
  money    -- what it costs, or what is at stake in dollars
  warrant  -- it goes to Town Meeting or the ballot, or did and what happened
  fee      -- a fee or rate a resident pays, and the amount or the increase
  service  -- a town or school service started, cut, restored or changed
  impact   -- anything else a resident would repeat: a size, a deadline, a building closing

RULES -- break one and the callout is thrown away:
  1. Use ONLY the numbered items given. `item` is the id of the one item the callout rests on.
  2. `quote` is copied EXACTLY, character for character. Where an item has CAPTIONS, quote the
     CAPTIONS -- the words actually spoken -- never the TEXT, which is our paraphrase. A town
     minutes item: quote its QUOTE. Otherwise its TEXT. A short span is best: the words that
     carry the value. Captions mishear; quote them as they are, misspellings included.
  3. Every number in `value` AND in `label` must appear in your quote or in that item's HEARD
     figures -- a year or a date too. Do not
     compute, add, convert or round to a new number. "$1M-$4M" from "between one and four
     million" is fine; a total you added up is not.
  4. value: at most 24 characters. label: at most 100, plain English a resident would say,
     no jargon, no board-internal shorthand. hook: at most 32 characters, NO DIGITS, the words
     that follow the value on the front page ("to demolish", "plan voters rejected"); leave it
     empty unless the callout is the thread's best single hook.
  5. Prefer what is DECIDED or SCHEDULED over what was floated; the TOWN'S MINUTES over our
     notes of a recording; recent over old, unless the old figure is still the stake.
  5b. A HOOK STANDS ALONE on the front page, without its label, so it must carry the status
     itself: a figure not decided says so -- "floated", "proposed", "requested", "estimated".
     "~$80 per household stormwater fee" reads as a fee that exists; "household fee floated"
     does not. The same goes for the label: never let it read as decided when it is not.
  6. Several matters may be given; answer each, by its `thread` id. At most three per matter, best first. The first is the hook. If nothing passes the hallway test,
     return none: an empty list is better than a weak callout.
  7. Never a person's name. Never an individual's private matter."""

ONE = {'type': 'array', 'maxItems': 3, 'items': {
        'type': 'object', 'additionalProperties': False,
        'required': ['item', 'kind', 'value', 'label', 'hook', 'quote'],
        'properties': {
            'item': {'type': 'string'},
            'kind': {'type': 'string', 'enum': ['money', 'warrant', 'fee', 'service', 'impact']},
            'value': {'type': 'string'}, 'label': {'type': 'string'},
            'hook': {'type': 'string'}, 'quote': {'type': 'string'}}}}
SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['matters'],
          'properties': {'matters': {'type': 'array', 'items': {
              'type': 'object', 'additionalProperties': False, 'required': ['thread', 'callouts'],
              'properties': {'thread': {'type': 'string'}, 'callouts': ONE}}}}}


# THE SECOND READER. The checks in build_threads.py prove a callout's NUMBERS are in its
# source; they cannot prove its SENTENCE. The first machine pass labelled the turf field's
# $195,830 "on the warrant" from a meeting that held it OFF the warrant -- the number was in
# the captions, the claim was not. So every pick is read again, by a separate call that sees
# the evidence and everything recorded AFTER it, and is kept only if every claim is supported
# and nothing later has overtaken it. LLM-as-judge: one model proposes, another disposes.
JUDGE = """You check CALLOUTS -- short claims shown to residents about a matter their town is
deciding -- against the evidence. You did not write them. Be strict: a resident will repeat
these at a meeting.

For each callout you get its VALUE, LABEL and HOOK, the EVIDENCE it rests on (our notes of a
recording, the machine captions of what was said, or the town's minutes), and LATER: what the
record says about the matter after that evidence.

keep = true only if BOTH:
  supported -- every claim in the value, label and hook is stated in, or directly follows
               from, the evidence. Status words count as claims: "on the warrant", "approved",
               "set", "voted" must be in the evidence. A figure that was floated must not
               read as decided, in the label OR in the hook (the hook is shown alone).
  current   -- nothing in LATER contradicts or overtakes it. If it was true then and is not
               now, it is not current.
Otherwise keep = false, and say which claim fails in `why`, in a few words."""

JUDGE_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['verdicts'],
                'properties': {'verdicts': {'type': 'array', 'items': {
                    'type': 'object', 'additionalProperties': False,
                    'required': ['id', 'keep', 'why'],
                    'properties': {'id': {'type': 'string'}, 'keep': {'type': 'boolean'},
                                   'why': {'type': 'string'}}}}}}


def judge(threads_by_id, figs, today, env, every=False):
    """Read the machine picks again; write `verdict` onto each. -> cost.

    Only picks with no verdict, unless `every`: a thread whose record moved is re-picked (its
    input hash changed), so its new picks arrive unjudged and are judged here. A thread that did
    not move has nothing later to overtake its picks."""
    blocks, refs = [], {}
    for f in sorted(os.listdir(OUT)):
        if not f.endswith('.json'):
            continue
        j = json.load(open(os.path.join(OUT, f), encoding='utf-8'))
        t = threads_by_id.get(j['thread'])
        if not t:
            continue
        items = items_for(t, figs, today)
        for k, c in enumerate(j['callouts']):
            if 'verdict' in c and not every:
                continue
            cid = '%s#%d' % (j['thread'], k)
            refs[cid] = (f, k)
            ev = next((x for x in items if x['date'] == c['item_date'] and x['board_slug'] == c['item_board']
                       and (c['quote'] in x['text'] + x['quote'] + x['captions'])), None)
            later = [x for x in items if x['date'] > c['item_date']][:20]
            b = ['--- CALLOUT %s  (matter: %s)' % (cid, t['label']),
                 'VALUE: %s' % c['value'], 'LABEL: %s' % c['label'], 'HOOK: %s' % (c['hook'] or '(none)'),
                 'EVIDENCE (%s, %s): %s' % (c['where'], c['basis'], (ev or {}).get('text', '') if ev else '(item not found)')]
            if ev and ev['quote']:
                b.append('  TOWN MINUTES: %s' % ev['quote'][:700])
            if ev and ev['captions']:
                b.append('  CAPTIONS: %s' % ev['captions'])
            b.append('  QUOTED: %s' % c['quote'])
            b.append('LATER:' + (''.join('\n  %s %s %s: %s' % (x['date'], x['board'], x['kind'], x['text'][:220])
                                        for x in later) or ' (nothing later)'))
            blocks.append('\n'.join(b))
    if not blocks:
        return 0
    r = claude_lean.run(['claude', '-p', '--tools', '', '--model', MODEL, '--system-prompt', JUDGE,
                        '--json-schema', json.dumps(JUDGE_SCHEMA), '--output-format', 'json',
                        '--max-budget-usd', '2'],
                       input='\n\n'.join(blocks), capture_output=True, text=True, env=env, timeout=1500)
    if r.returncode != 0:
        print((r.stdout + r.stderr)[-1500:])
        raise SystemExit('the judge call failed; no pick is marked kept')
    res = json.loads(r.stdout)
    body = res.get('structured_output') or res.get('result')
    if isinstance(body, str):
        body = json.loads(body)
    got = {v['id']: v for v in body.get('verdicts') or []}
    files = {}
    for cid, (f, k) in refs.items():
        j = files.setdefault(f, json.load(open(os.path.join(OUT, f), encoding='utf-8')))
        v = got.get(cid)
        # NO VERDICT IS A DROP. A pick the judge did not answer for has not been checked.
        j['callouts'][k]['verdict'] = {'keep': bool(v and v['keep']), 'why': (v or {}).get('why', 'no verdict returned')}
    for f, j in files.items():
        tmp = os.path.join(OUT, f + '.tmp')
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(j, fh, indent=1, ensure_ascii=False)
            fh.write('\n')
        os.replace(tmp, os.path.join(OUT, f))
    cost = res.get('total_cost_usd') or 0
    record('judge', cost, 'ok, %d kept of %d' % (sum(1 for v in got.values() if v['keep']), len(refs)))
    for cid, (f, k) in refs.items():
        v = files[f]['callouts'][k]['verdict']
        print('  %s %-30s %s' % ('KEEP' if v['keep'] else 'DROP', cid, '' if v['keep'] else v['why'][:120]))
    return cost


def heard_figures():
    out = {}
    for b in os.listdir(MINUTES):
        for f in os.listdir(os.path.join(MINUTES, b)):
            if not f.endswith('.json'):
                continue
            j = json.load(open(os.path.join(MINUTES, b, f), encoding='utf-8'))
            for x in (j.get('minutes') or {}).get('budget_items') or []:
                out[(j['board_slug'], j['meeting_date'][:10], x.get('t'))] = x.get('figures_as_heard') or []
    return out


_CAPS = {}


def captions_at(board, date, video_url, t):
    """What was actually said around `t`, from the machine captions, or '' if not held."""
    m = re.search(r'v=([\w-]{11})', video_url or '')
    if not m or t is None:
        return ''
    f = os.path.join(TRANSCRIPTS, board, '%s-%s.json' % (date, m.group(1)))
    if f not in _CAPS:
        _CAPS[f] = json.load(open(f, encoding='utf-8'))['segments'] if os.path.exists(f) else []
    # inside the checker's window (t +/- 120), so anything quoted from here can be found there
    return ' '.join(x['text'] for x in _CAPS[f] if t - 25 <= x['start'] <= t + 80)[:900]


def pretty(d):
    y, m, dd = d.split('-')
    return '%d %s %s' % (int(dd), ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][int(m) - 1], y)


def items_for(t, figs, today):
    """The record the model may quote: numbered, newest first. Everything in the last 180 days,
    then the money items before that, so an old figure that is still the stake can be found."""
    rows = []
    for c in t['chronology']:
        for i in c['items']:
            if i.get('kind') == 'unreadable':
                continue
            rows.append((c, i))
    recent = [(c, i) for c, i in rows if (today - dt.date.fromisoformat(c['date'])).days <= 180]
    older = [(c, i) for c, i in rows if (c, i) not in recent and i['kind'] in ('budget', 'vote', 'decision')]
    pick = sorted(recent, key=lambda x: x[0]['date'], reverse=True)[:90] + \
        sorted(older, key=lambda x: x[0]['date'], reverse=True)[:30]
    out = []
    for n, (c, i) in enumerate(pick, 1):
        f = figs.get((c['board_slug'], c['date'], i.get('t')), []) if i['source'] != 'town' else []
        out.append(dict(id='I%d' % n, board=c['board'], board_slug=c['board_slug'], date=c['date'],
                        kind=i['kind'], source=i['source'], text=i['text'], quote=i.get('quote') or '',
                        heard=f, t=i.get('t'), video_url=i.get('video_url') or '', doc_url=i.get('doc_url') or '',
                        outcome=i.get('outcome') or '',
                        captions=captions_at(c['board_slug'], c['date'], i.get('video_url'), i.get('t'))
                        if i['source'] != 'town' and i['kind'] != 'topic' else ''))
    return out


def prompt_for(t, items):
    lines = ['=== MATTER thread=%s' % t['id'], 'TITLE: %s' % t['label'], 'QUESTION: %s' % t['question'],
             'STATUS: %s' % t['status'], 'CAVEAT: %s' % (t.get('caveat') or ''), '',
             'ITEMS (id | date | board | kind | record):']
    for x in items:
        rec = "the town's minutes" if x['source'] == 'town' else 'our notes of the recording'
        s = '%s | %s | %s | %s%s | %s\n   TEXT: %s' % (x['id'], x['date'], x['board'], x['kind'],
                                                       (' (%s)' % x['outcome']) if x['outcome'] else '', rec, x['text'])
        if x['quote']:
            s += '\n   QUOTE: %s' % x['quote'][:600]
        if x['heard']:
            s += '\n   HEARD: %s' % ' | '.join(x['heard'])
        if x['captions']:
            s += '\n   CAPTIONS: %s' % x['captions']
        lines.append(s)
    return '\n'.join(lines)


def resolve(c, items):
    """A model callout -> a registry-shaped row, with its source spelled out for the checker."""
    x = next((i for i in items if i['id'] == c['item']), None)
    if not x:
        return None
    row = dict(kind=c['kind'], value=c['value'].strip(), label=c['label'].strip(), hook=c['hook'].strip(),
               quote=c['quote'], heard=x['heard'], item_date=x['date'], item_board=x['board_slug'])
    if x['source'] == 'town':
        if not x['doc_url'].startswith('/docs/meetings/'):
            return None
        rel = x['doc_url'][len('/docs/'):]
        b, f = rel.split('/')[1], rel.split('/')[2]
        row.update(basis='printed', doc=rel, text='meetings/text/%s/%s' % (b, f),
                   where='%s minutes, %s' % (x['board'], pretty(x['date'])))
    else:
        m = re.search(r'v=([\w-]{11})', x['video_url'])
        if not m or x['t'] is None:
            return None
        row.update(basis='heard', board=x['board_slug'], date=x['date'], video_id=m.group(1), t=int(x['t']),
                   where='%s, %s' % (x['board'], pretty(x['date'])))
    return row


def record(tid, cost, result):
    new = not os.path.exists(SPEND)
    with open(SPEND, 'a', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(['at', 'stream', 'board', 'date', 'cost_usd', 'result'])
        w.writerow([dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'callouts', tid,
                    dt.date.today().isoformat(), '%.4f' % cost if cost else '', result])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('thread', nargs='*')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--judge-only', action='store_true', help='read the existing picks again; pick nothing')
    a = ap.parse_args()
    d = json.load(open(THREADS, encoding='utf-8'))
    curated = {r['thread'] for r in csv.DictReader(open(CURATED, encoding='utf-8'))} if os.path.exists(CURATED) else set()
    figs, today = heard_figures(), dt.date.today()
    # GENERATED THREADS (build_town_meetings.py) are not picked for unless named: their
    # callouts have not been agreed, and each pick is a metered model call.
    todo = [t for t in d['threads'] if (t['id'] in a.thread if a.thread else t['status'] == 'open' and not t.get('generated'))]
    if a.thread and len(todo) != len(set(a.thread)):
        raise SystemExit('no such thread among %s' % a.thread)
    os.makedirs(OUT, exist_ok=True)
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    if a.judge_only:
        print('judged, $%.2f' % judge({t['id']: t for t in d['threads']}, figs, today, env, every=True))
        return
    pending = []
    for t in todo:
        if t['id'] in curated:
            print('  %-28s a person picked these (thread-callouts.csv); skipped' % t['id'])
            continue
        items = items_for(t, figs, today)
        if not items:
            print('  %-28s no record to read' % t['id'])
            continue
        prompt = prompt_for(t, items)
        sha = hashlib.sha256(('%d\n%s' % (VERSION, prompt)).encode()).hexdigest()
        path = os.path.join(OUT, t['id'] + '.json')
        if not a.all and not a.thread and os.path.exists(path) and json.load(open(path))['input_sha256'] == sha:
            print('  %-28s current' % t['id'])
            continue
        pending.append((t, items, prompt, sha, path))
    chunks, cur = [], []
    for p in pending:
        if cur and sum(len(x[2]) for x in cur) + len(p[2]) > CHUNK_CHARS:
            chunks.append(cur)
            cur = []
        cur.append(p)
    if cur:
        chunks.append(cur)
    print('%d thread(s) to pick, in %d call(s)' % (len(pending), len(chunks)))
    spent, n = 0.0, 0
    for chunk in chunks:
        text = '\n\n'.join(p[2] for p in chunk)
        if a.dry_run:
            print('  call: %s (%d chars)' % (', '.join(p[0]['id'] for p in chunk), len(text)))
            if a.thread:
                print(text)
            continue
        env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
        r = claude_lean.run(['claude', '-p', '--tools', '', '--model', MODEL, '--system-prompt', SYSTEM,
                            '--json-schema', json.dumps(SCHEMA), '--output-format', 'json',
                            '--max-budget-usd', '%.2f' % (0.5 * len(chunk))],
                           input=text, capture_output=True, text=True, env=env, timeout=1500)
        if r.returncode != 0:
            print((r.stdout + r.stderr)[-1500:])
            record(','.join(p[0]['id'] for p in chunk), 0, 'failed')
            raise SystemExit('claude failed on %s' % ', '.join(p[0]['id'] for p in chunk))
        res = json.loads(r.stdout)
        body = res.get('structured_output') or res.get('result')
        if isinstance(body, str):
            body = json.loads(body)
        cost = res.get('total_cost_usd') or 0
        spent += cost
        got = {m['thread']: m['callouts'] for m in body.get('matters') or []}
        for t, items, prompt, sha, path in chunk:
            share = cost * len(prompt) / max(len(text), 1)      # a call's cost, split by the record each thread brought
            rows = [x for x in (resolve(c, items) for c in got.get(t['id'], [])) if x]
            tmp = path + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as fh:
                json.dump(dict(warning='PICKED BY A LANGUAGE MODEL. Nothing here shows until build_threads.py '
                                       'has checked each callout against its source; a failing one is dropped.',
                               thread=t['id'], picked_at=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                               model=MODEL, version=VERSION, cost_usd=round(share, 4), input_sha256=sha,
                               callouts=rows), fh, indent=1, ensure_ascii=False)
                fh.write('\n')
            os.replace(tmp, path)
            record(t['id'], share, 'ok, %d callout(s)' % len(rows))
            n += 1
            print('  %-28s %d callout(s): %s' % (t['id'], len(rows),
                                                '; '.join('%s %s' % (x['value'], x['label']) for x in rows)[:150]))
    if n:
        spent += judge({t['id']: t for t in d['threads']}, figs, today, env)
    print('%d thread(s) picked and every pick judged, $%.2f' % (n, spent))


if __name__ == '__main__':
    main()
