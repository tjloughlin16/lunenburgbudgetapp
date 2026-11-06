#!/usr/bin/env python3
"""NEW MATTERS OPEN THEIR OWN THREADS: one model call, and the build decides what publishes.

    python3 scripts/open_threads.py             # one call, only if its input changed
    python3 scripts/open_threads.py --dry-run   # the items and the prompt size; spends nothing

TJ, 5-6 November 2026: threads must update when new related information appears, and new ones
auto-publish at 3+ meetings on one question, with anything weaker in a review queue.

THE MODEL WRITES, THE BUILD DECIDES. propose_threads.py and the budget feed both find matters
no thread names, but as bare material: a word like `field` has no question and no way to close.
The model turns that material into matters, each with a question, a closing condition and a
pattern. It decides nothing about publishing: this script runs the pattern over the whole
record with the same chronology() every thread uses and counts the meetings.

    3+ meetings, pattern valid, not mostly another thread's   -> sources/data/threads-auto/opened.json
    anything else                                             -> sources/data/thread-review-queue.csv

An opened thread is never removed from here by a later run, so a thread cannot vanish because a
window moved. A person closes one by hand, or moves it to threads.csv to take it over. Refuse a
queued matter by adding it to threads-declined.csv: it is then not proposed again.

COST. One call per refresh, capped at MAX_USD, and none when the items are unchanged (the input's
sha256 is stored in opened.json). Appended to sources/data/agentic-spend.csv as `open-threads`.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sys

import build_threads as B
import claude_lean
import propose_threads as P

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPENED = os.path.join(ROOT, 'sources', 'data', 'threads-auto', 'opened.json')
QUEUE = os.path.join(ROOT, 'sources', 'data', 'thread-review-queue.csv')
FEED = os.path.join(ROOT, 'fy28', 'public', 'data', 'budget-feed.json')
SPEND = os.path.join(ROOT, 'sources', 'data', 'agentic-spend.csv')
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
MODEL = 'sonnet'
VERSION = 1            # bump to re-read the items after a prompt change
MAX_USD = 0.50
DAYS = 90
MAX_ITEMS = 80         # the proposer ranks; the rest of its list is the long tail
MAX_STORIES = 12
LINES_PER_STORY = 4
MIN_MEETINGS = 3
# PAST THIS A PATTERN IS A SUBJECT, NOT A MATTER. `#budget` was in 87 of 108 recent meetings.
MAX_MEETINGS = 40
MAX_OVERLAP = 0.5
QUEUE_FIELDS = ['id', 'label', 'question', 'closes', 'kind', 'groups', 'match', 'qualify', 'exclude',
                'started', 'meetings', 'why', 'first_seen']
CAVEAT = ('Opened automatically. A model wrote this question and its closing condition from the '
          'meeting record, and no person has read them yet.')

SYSTEM = """You read numbered items from the meetings of Lunenburg, Massachusetts boards and name
the MATTERS among them: open questions that recur and that the town has yet to decide.

Return a matter only if it is ONE question a resident could follow to an answer. A subject
("athletics"), a place, a recurring agenda item or routine housekeeping is not a matter.

For each matter write:
- label: 2 to 4 words, a noun phrase, no digits.
- question: one plain sentence a resident would ask, ending in a question mark, no digits. It is
  neutral: it asks, it does not accuse, and it does not say what should happen.
- closes: the event that ends it (a named vote or a signed contract), no digits.
- kind: one or more of rule, money, service, contract, project, asset, office, joined by ";".
- groups: one or more of what-i-pay, schools, buildings, water-sewer-roads, how-the-town-runs,
  joined by ";".
- match: a Python regular expression, case-insensitive, for the matter's distinctive words. It has
  to match the items you cite and should not match other business. Never a bare common word.
- qualify: a second pattern that must also match, when the distinctive word also means other
  things, or "".
- exclude: a pattern for senses to leave out, or "".
- items: the numbers of the items that show this matter. Cite only items you were given.

Skip anything about a named child, a family receiving services, or a personnel complaint.
Skip anything on the ALREADY CONSIDERED list. Returning no matters is a good answer."""

SCHEMA = {'type': 'object', 'required': ['matters'], 'properties': {'matters': {'type': 'array', 'items': {
    'type': 'object',
    'required': ['label', 'question', 'closes', 'kind', 'groups', 'match', 'qualify', 'exclude', 'items'],
    'properties': {k: {'type': 'string'} for k in
                   ('label', 'question', 'closes', 'kind', 'groups', 'match', 'qualify', 'exclude')}
    | {'items': {'type': 'array', 'items': {'type': 'integer'}}}}}}}


def read_opened():
    if not os.path.exists(OPENED):
        return {'about': 'Threads opened by scripts/open_threads.py. A later run never removes one.',
                'rule': 'A model wrote the question; the build counted the meetings.',
                'input_sha256': '', 'threads': []}
    return json.load(open(OPENED, encoding='utf-8'))


def compiled(row):
    return dict(row, rx=re.compile(row['match'], re.I) if row.get('match') else None,
                qu=re.compile(row['qualify'], re.I) if row.get('qualify') else None,
                ex=re.compile(row['exclude'], re.I) if row.get('exclude') else None)


def story_lines(threads, mts):
    """The budget feed's forming stories, as the unclaimed lines that carry each word."""
    if not os.path.exists(FEED):
        return []
    out = []
    feed = json.load(open(FEED, encoding='utf-8'))
    for story in (feed.get('proposed_threads') or [])[:MAX_STORIES]:
        rx = re.compile(story['suggested']['match'], re.I)
        found = []
        for (slug, date), rec in sorted(mts.items(), key=lambda kv: kv[0][1], reverse=True):
            for src, text in rec['items']:
                if len(found) < LINES_PER_STORY and rx.search(text) and not P.claimed(threads, text):
                    found.append(dict(date=date, slug=slug, text=text, why='budget story: ' + story['name']))
        out.extend(found)
    return out


def gather(until):
    """Every item the model may read, ranked, and what it has already considered."""
    since = (dt.date.fromisoformat(until) - dt.timedelta(days=DAYS)).isoformat()
    opened = read_opened()['threads']
    threads, declined, hits = P.build(since, until)
    threads = threads + [compiled(t) for t in opened]
    # A single-subject board's business is its thread's, whether or not a line names the subject.
    owned = {B.sole_subject_board(t) for t in threads} - {None}
    seen, items = set(), []
    for h in sorted(hits.get(None, []), key=lambda h: -h['score']):
        key = re.sub(r'\W+', ' ', h['text'].lower())[:55]
        if (key in seen or h['slug'] in owned or h['text'].lower()[:40] in declined
                or P.claimed(threads, h['text'])):
            continue
        seen.add(key)
        items.append(dict(date=h['date'], slug=h['slug'], text=h['text'], why='+'.join(h['trig'])))
        if len(items) >= MAX_ITEMS:
            break
    for h in story_lines(threads, P.meetings(since, until)):
        key = re.sub(r'\W+', ' ', h['text'].lower())[:55]
        if key not in seen:
            seen.add(key)
            items.append(h)
    queued = P.read_csv(QUEUE)
    # The question as well as the label: a label alone let "trust fund continuity" past "trust
    # fund administration during a vacancy".
    said = lambda r: '%s: %s' % (r['label'], r['question']) if r.get('question') else r['label']
    considered = sorted({said(t) for t in threads if t.get('label')} | {said(r) for r in queued}
                        | {r['candidate'] for r in P.read_csv(P.DECLINED)})
    return items, considered


def prompt_for(items, considered):
    body = ['%d. %s %s (%s): %s' % (i, it['date'], it['slug'], it['why'], ' '.join(it['text'].split())[:300])
            for i, it in enumerate(items, 1)]
    return 'ALREADY CONSIDERED:\n%s\n\nITEMS:\n%s\n' % ('\n'.join('- ' + c for c in considered), '\n'.join(body))


def sha_of(items, considered):
    return hashlib.sha256(('%d\n%s' % (VERSION, prompt_for(items, considered))).encode()).hexdigest()


def open_thread_meetings(rows, record, town):
    """(id, its meetings) for every open thread a new one could be a second copy of."""
    return [(t['id'], {(c['board_slug'], c['date']) for c in B.chronology(t, record, town)})
            for t in rows if t.get('status') == 'open' and t.get('match')]


def gate(m, items, record, town, others, open_meetings):
    """-> (row, why it may not publish or None). Everything measured here, nothing taken on trust."""
    row = {'id': B_slug(m['label']), 'label': m['label'].strip(), 'question': m['question'].strip(),
           'closes': m['closes'].strip(), 'kind': m['kind'].strip(), 'groups': m['groups'].strip(),
           'match': m['match'], 'qualify': m['qualify'], 'exclude': m['exclude'], 'tags': '', 'reports': '',
           'boards': '', 'status': 'open', 'resolved_on': '', 'caveat': CAVEAT, 'generated': 'opened-by-model',
           'note': '', 'pin': ''}
    cited = [items[n - 1] for n in m['items'] if 1 <= n <= len(items)]
    row['started'] = min([c['date'] for c in cited] or [''])
    row['registered_on'] = dt.date.today().isoformat()
    row['meetings'] = 0
    if not cited:
        return row, 'cites no item it was given'
    try:
        c = compiled(row)
    except re.error as e:
        return row, 'pattern does not compile: %s' % e
    if not c['rx']:
        return row, 'no pattern'
    # RULE 2: every digit on a page is a registered figure, and these three are shown as written.
    if any(re.search(r'\d', row[k]) for k in ('label', 'question', 'closes')):
        return row, 'a digit in its label, question or closing condition'
    hit = lambda t: c['rx'].search(t) and (not c['qu'] or c['qu'].search(t)) and not (c['ex'] and c['ex'].search(t))
    if sum(1 for x in cited if hit(x['text'])) * 2 < len(cited):
        return row, 'its pattern misses most of the items it cites'
    chron = B.chronology(row, record, town)
    row['meetings'] = len(chron)
    if len(chron) < MIN_MEETINGS:
        return row, 'on %d meeting(s), under the %d that publish' % (len(chron), MIN_MEETINGS)
    if len(chron) > MAX_MEETINGS:
        return row, 'on %d meetings: a subject, not one matter' % len(chron)
    texts = [i['text'] for x in chron for i in x['items']]
    taken = sum(1 for t in texts if P.claimed(others, t))
    if taken > MAX_OVERLAP * len(texts):
        return row, '%d of %d items already sit on another thread' % (taken, len(texts))
    # THE SAME MEETINGS AS AN OPEN THREAD MAY MEAN THE SAME MATTER UNDER NEW WORDS. Trust fund
    # continuity was the trust fund vacancy thread, in 3 of its 5 meetings, with no line in common.
    # Two matters at one busy meeting look alike here, so this can queue a real one. That is the
    # safe way round for a page nobody reads before it publishes.
    mine = {(x['board_slug'], x['date']) for x in chron}
    for oid, theirs in open_meetings:
        if oid != row['id'] and len(mine & theirs) >= MAX_OVERLAP * len(mine):
            return row, '%d of its %d meetings are also on %s' % (len(mine & theirs), len(mine), oid)
    return row, None


def B_slug(label):
    return re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')


def record_spend(cost, result):
    new = not os.path.exists(SPEND)
    with open(SPEND, 'a', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(['at', 'stream', 'board', 'date', 'cost_usd', 'result'])
        w.writerow([dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'open-threads', 'all',
                    dt.date.today().isoformat(), '%.4f' % cost if cost else '', result])


def write_json(path, obj):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    os.replace(tmp, path)


def add_to_queue(rows):
    have = P.read_csv(QUEUE)
    known = {r['id'] for r in have}
    fresh = [r for r in rows if r['id'] not in known]
    today = dt.date.today().isoformat()
    tmp = QUEUE + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=QUEUE_FIELDS, extrasaction='ignore')
        w.writeheader()
        w.writerows(have)
        w.writerows(dict(r, first_seen=today) for r in fresh)
    os.replace(tmp, QUEUE)
    return len(fresh)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    until = dt.date.today().isoformat()
    items, considered = gather(until)
    prompt = prompt_for(items, considered)
    sha = sha_of(items, considered)
    state = read_opened()
    print('%d item(s) no thread names, %d chars' % (len(items), len(prompt)))
    if a.dry_run:
        print(prompt[:6000])
        return
    if not items:
        print('nothing to read, so no call')
        return
    if state.get('input_sha256') == sha:
        print('unchanged since the last read, so no call')
        return
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    r = claude_lean.run(['claude', '-p', '--tools', '', '--model', MODEL, '--system-prompt', SYSTEM,
                         '--json-schema', json.dumps(SCHEMA), '--output-format', 'json',
                         '--max-budget-usd', '%.2f' % MAX_USD],
                        input=prompt, capture_output=True, text=True, env=env, timeout=900)
    if r.returncode != 0:
        print((r.stdout + r.stderr)[-1500:])
        record_spend(0, 'failed')
        raise SystemExit('claude failed')
    res = json.loads(r.stdout)
    body = res.get('structured_output') or res.get('result')
    if isinstance(body, str):
        body = json.loads(body)
    cost = res.get('total_cost_usd') or 0

    record, _ = B.the_record()
    town = B.town_record()
    others = P.registered() + [compiled(t) for t in state['threads']]
    taken = {t['id'] for t in state['threads']} | {t['id'] for t in B.read_csv(B.THREADS)} | {t['id'] for t in B.auto_rows()}
    open_meetings = open_thread_meetings(B.read_csv(B.THREADS) + state['threads'], record, town)
    opened, queued = [], []
    for m in body.get('matters') or []:
        row, why = gate(m, items, record, town, others, open_meetings)
        if not why and row['id'] in taken:
            why = 'its name is already used by a thread'
        print('  %-8s %-34s %d meeting(s)%s' % ('QUEUE' if why else 'OPEN', row['label'][:34], row['meetings'],
                                                ' -- ' + why if why else ''))
        if why:
            queued.append(dict(row, why=why))
        else:
            taken.add(row['id'])
            opened.append(row)
    state['threads'].extend(opened)
    os.makedirs(os.path.dirname(OPENED), exist_ok=True)
    write_json(OPENED, state)
    nq = add_to_queue(queued)
    # THE HASH IS OF THE ITEMS AS THEY STAND AFTER THIS READ. What was just opened or queued leaves
    # the items and joins the considered list, so hashing the input just read would make tomorrow
    # look changed and pay for a second call about nothing new.
    state['input_sha256'] = sha_of(*gather(until))
    write_json(OPENED, state)
    record_spend(cost, 'ok, %d opened, %d queued' % (len(opened), nq))
    print('opened %d, queued %d new, $%.4f' % (len(opened), nq, cost))


if __name__ == '__main__':
    sys.exit(main())
