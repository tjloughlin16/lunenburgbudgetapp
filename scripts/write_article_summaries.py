#!/usr/bin/env python3
"""A SENTENCE OR TWO PER WARRANT ARTICLE: what it would do, in plain words.

TJ, 21 October 2026, on the November 17 board: "each article needs a BIT more of the detail
for each. a sentence or two." A title like "Transfer of funds to the special education
reserve fund" says what it is called, not what it does or why it is there.

    python3 scripts/write_article_summaries.py                 # meetings coming up or held in the last 60 days
    python3 scripts/write_article_summaries.py --meeting stm-2026-11-17
    python3 scripts/write_article_summaries.py --dry-run       # what would be sent, and to whom
    python3 scripts/write_article_summaries.py --check         # every stored summary still passes its checks

WHAT THE MODEL READS -- AND ONLY THAT. Per article: its title, the warrant's own words where we
hold the warrant, the figures a person checked in the recordings (heard-figures.csv), and the
board discussion attached to it on the meeting's thread (our notes, from machine captions).
`claude -p` writes one or two plain sentences from those; it reads nothing else.

WHAT IS REFUSED. A summary may carry a figure only if the WARRANT or a CHECKED FIGURE carries
it: our notes mishear numbers (rule 13), so a figure that came only from them is not allowed
through, and a summary that types one is dropped rather than shown. No cause words of our own
(rule 7). Two sentences at most. Each summary says what it was written from.

CACHED BY ITS INPUT. A summary is rewritten only when the record behind it changes, so the
daily refresh pays only for articles that moved. Every call is logged to agentic-spend.csv
under the stream `article-summaries`.
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
DATA = os.path.join(ROOT, 'sources', 'data')
AUTO = os.path.join(DATA, 'threads-auto', 'town-meetings.json')
ARTS = os.path.join(DATA, 'warrant-articles.csv')
OUT = os.path.join(DATA, 'article-summaries.json')
SPEND = os.path.join(DATA, 'agentic-spend.csv')
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
MODEL = 'sonnet'
VERSION = 3            # bump to rewrite every summary after a prompt change
RECENT_DAYS = 60
MAX_SENTENCES = 3        # "a sentence or two"; three short ones when an article carries several figures
MAX_CHARS = 450
CAUSE = re.compile(r'\b(?:because|due to|led to|caused|in order to|so that|as a result)\b', re.I)
STOP = set('the a an of to and for in on at by with from town lunenburg article warrant vote '
           'fiscal year fund funds special annual meeting non binding question'.split())

SYSTEM = """You write one or two plain sentences per Town Meeting warrant article, for residents
of Lunenburg, Massachusetts, who are not finance people. Say what the article would do if
voted, and anything in the material that a resident would want to know first (who brought it,
what it pays for, whether it is binding). Write the way you would explain it to a neighbour.

Rules, all of them strict:
- Use ONLY the material given for that article. Do not add anything you know from elsewhere.
- A figure (any number, amount or date) may appear ONLY if it is in WARRANT or CHECKED FIGURES.
  Figures in BOARD DISCUSSION are machine captions and may be misheard: never copy them.
- Do not explain causes or motives ("because", "in order to", "due to") unless WARRANT says so.
- No finance jargon: not "appropriate", "raise and appropriate", "free cash certification",
  "enterprise fund", "levy". Say "pay for", "spend", "set aside" and so on.
- Two sentences, three at most when there are several figures; under 450 characters. No opinions, no adjectives about merit.
- A NON-BINDING (advisory) question decides nothing: say what it asks voters, and that it is
  non-binding.
- When the warrant is not posted yet, describe the article as the boards described it. Do NOT
  say the wording is not posted: the page says that once, above every article.
- Spell names as TITLE spells them (the captions misspell names: "TC Pacios" is TC Passios).
- Return an empty summary ONLY if the material says nothing at all about what the article is
  about beyond its title."""

SCHEMA = {'type': 'object', 'properties': {'articles': {'type': 'array', 'items': {
    'type': 'object', 'properties': {'key': {'type': 'string'}, 'summary': {'type': 'string'}},
    'required': ['key', 'summary']}}}, 'required': ['articles']}


# The captions spell names as they hear them; one spelling per name, so a match is not lost.
SPELL = {'pacios': 'passios', 'passos': 'passios', 'passeos': 'passios', 'tcp': 'passios'}


def words(s):
    return {SPELL.get(w, w) for w in re.findall(r'[a-z]{3,}', s.lower()) if w not in STOP}


def key_of(meeting, a):
    return '%s|%s|%s' % (meeting, a.get('article') if a.get('article') != '' else '', a['title'].lower().strip())


def material(m, a, csvrow, linked=None):
    """Everything the model may read about one article, and the figures it may use. An article
    followed in a thread of its own (TC Passios, the turf field, stormwater) also brings that
    thread's record: most of the discussion of a matter is filed there, not under the meeting."""
    tw = words(a['title'])
    num = a.get('article')
    disc = []
    if linked:
        for stop in linked.get('chronology') or []:
            for it in stop.get('items') or []:
                disc.append('%s, %s: %s' % (stop.get('board') or '', stop.get('date') or '', it.get('text') or ''))
    for stop in m.get('chronology') or []:
        for it in stop.get('items') or []:
            t = it.get('text') or ''
            by_num = num != '' and re.search(r'\barticle\s+%s\b' % num, t, re.I)
            by_words = len(tw & words(t)) >= min(2, len(tw))
            if by_num or by_words:
                disc.append('%s, %s: %s' % (stop.get('board') or it.get('board') or '', stop.get('date') or it.get('date') or '', t))
    disc = list(dict.fromkeys(disc))
    warrant = (csvrow or {}).get('warrant_words', '')
    heard = ['%s -- %s' % (h['figure'], h['what']) for h in a.get('heard') or []]
    allowed = ' '.join([warrant, a['title'], a.get('amount') or '', a.get('result_amount') or ''] + heard)
    text = ('TITLE: %s\nWARRANT: %s\nCHECKED FIGURES: %s\nBOARD DISCUSSION (machine captions, figures unreliable):\n%s'
            % (a['title'], warrant or '(the warrant is not posted yet)', '; '.join(heard) or '(none)',
               '\n'.join('- ' + d for d in disc[-40:]) or '(none)'))
    return text, allowed, ('the warrant' if warrant else "the boards' discussion, from our notes of the recordings")


def figures(s):
    """The figures in a text, as bare digits. A four-digit year also stands for its two-digit
    form, so "FY27" in a summary matches "fiscal year 2027" in the warrant."""
    out = {re.sub(r'[,$]', '', x) for x in re.findall(r'\$?\d[\d,]*(?:\.\d+)?', s)}
    return out | {x[2:] for x in out if re.fullmatch(r'(?:19|20)\d\d', x)}


def check(summary, allowed):
    """The reasons a summary may not be shown; empty if it passes."""
    bad = []
    if len(summary) > MAX_CHARS:
        bad.append('%d characters' % len(summary))
    if len([x for x in re.split(r'(?<=[.!?])\s+', summary.strip()) if x]) > MAX_SENTENCES:
        bad.append('more than %d sentences' % MAX_SENTENCES)
    if CAUSE.search(summary) and not CAUSE.search(allowed):
        bad.append('a cause word not in the warrant')
    extra = figures(summary) - figures(allowed) - {w for w in figures(allowed)}
    # number words for figures written out in the warrant are fine; a digit not in the inputs is not
    if extra:
        bad.append('figure(s) not in the warrant or checked figures: %s' % ', '.join(sorted(extra)))
    return bad


def ask(body, n, meeting):
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    r = claude_lean.run(['claude', '-p', '--tools', '', '--model', MODEL, '--system-prompt', SYSTEM,
                        '--json-schema', json.dumps(SCHEMA), '--output-format', 'json',
                        '--max-budget-usd', '%.2f' % max(0.5, 0.05 * n)],
                       input=body, capture_output=True, text=True, env=env, timeout=1500)
    if r.returncode != 0:
        print((r.stdout + r.stderr)[-1200:])
        record(meeting, 0, 'failed')
        raise SystemExit('claude failed on %s' % meeting)
    res = json.loads(r.stdout)
    out = res.get('structured_output') or res.get('result')
    out = json.loads(out) if isinstance(out, str) else out
    # Keys compared NORMALISED: the model may echo a key with a curly quote or changed spacing,
    # and a key that does not match exactly must not silently become "no summary".
    return {norm(x['key']): x['summary'].strip() for x in out.get('articles') or []}, res.get('total_cost_usd') or 0


def norm(k):
    return re.sub(r'[^a-z0-9|]+', '', k.lower().replace('’', "'"))


def record(meeting, cost, result):
    new = not os.path.exists(SPEND)
    with open(SPEND, 'a', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(['at', 'stream', 'board', 'date', 'cost_usd', 'result'])
        w.writerow([dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'article-summaries',
                    meeting, dt.date.today().isoformat(), '%.4f' % cost if cost else '', result])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--meeting', action='append')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    store = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    if a.check:
        bad = [(k, check(v['summary'], v['allowed'])) for k, v in store.items() if v.get('summary')]
        bad = [(k, b) for k, b in bad if b]
        for k, b in bad:
            print('  FAIL %s: %s' % (k, '; '.join(b)))
        print('%s -- %d summaries' % ('FAILED' if bad else 'ok', len(store)))
        sys.exit(1 if bad else 0)

    auto = json.load(open(AUTO, encoding='utf-8'))
    auto = auto if isinstance(auto, list) else auto.get('threads', auto)
    pub = json.load(open(os.path.join(ROOT, 'fy28', 'public', 'data', 'threads.json'), encoding='utf-8'))
    by_id = {t['id']: t for t in pub['threads']}
    rows = {}
    for r in csv.DictReader(open(ARTS, encoding='utf-8')):
        rows[(r['meeting'], r['title'].lower().strip())] = r
    today = dt.date.today()
    meetings = [t for t in auto if t.get('kind') == 'town-meeting' and t.get('warrant')]
    if a.meeting:
        meetings = [t for t in meetings if t['id'] in a.meeting]
    else:
        meetings = [t for t in meetings if t['warrant']['status'] == 'upcoming'
                    or (today - dt.date.fromisoformat(t['warrant']['date'])).days <= RECENT_DAYS]
    spent, wrote = 0.0, 0
    for m in meetings:
        todo, prompts = [], []
        for art in m['warrant']['articles']:
            k = key_of(m['id'], art)
            text, allowed, basis = material(m, art, rows.get((m['id'], art['title'].lower().strip())),
                                            by_id.get(art.get('thread')) if art.get('thread') else None)
            sha = hashlib.sha256(('v%d\n%s' % (VERSION, text)).encode()).hexdigest()
            prev = store.get(k, {})
            # Current if the record has not moved -- unless the last attempt was REFUSED, which a
            # fix to the checks (or a second try) may now pass.
            if prev.get('input_sha256') == sha and not prev.get('refused'):
                continue
            todo.append((k, allowed, basis, sha))
            prompts.append('### ARTICLE key=%s\n%s' % (k, text))
        if not todo:
            print('  %-18s current' % m['id'])
            continue
        body = '\n\n'.join(prompts)
        if a.dry_run:
            print('  %-18s would write %d summaries (%d chars)' % (m['id'], len(todo), len(body)))
            continue
        got, cost = ask(body, len(todo), m['id'])
        # A BATCH THAT DROPS AN ARTICLE: ask for each missing one on its own. Seen 21 October
        # 2026 -- three of eleven came back absent from a batch and fine when asked singly.
        for (k, _, _, _), pr in zip(todo, prompts):
            if norm(k) not in got:
                one, c1 = ask(pr, 1, m['id'])
                got.update(one)
                cost += c1
        # ONE SECOND TRY for a summary the checks refused, told exactly why. A figure from the
        # captions stays refused if it comes back: the check, not the model, decides.
        again = [(k, check(got.get(norm(k), ''), allowed)) for k, allowed, _, _ in todo if got.get(norm(k))]
        again = [(k, b) for k, b in again if b]
        if again:
            redo = '\n\n'.join('%s\nYOUR FIRST SUMMARY WAS REFUSED: %s. Rewrite it within the rules.'
                                % (pr, '; '.join(b)) for pr in prompts for k, b in again if ('key=%s\n' % k) in pr)
            got2, cost2 = ask(redo, len(again), m['id'])
            got.update({k: v for k, v in got2.items() if v})
            cost += cost2
        spent += cost
        kept = 0
        for k, allowed, basis, sha in todo:
            s = got.get(norm(k), '')
            bad = check(s, allowed) if s else ['empty']
            if not s:
                print('    no summary returned for %s' % k)
            store[k] = {'summary': '' if bad else s, 'from': basis, 'refused': bad,
                        'refused_text': s if bad and s else '',
                        'allowed': allowed, 'input_sha256': sha, 'model': MODEL, 'version': VERSION,
                        'written_at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}
            kept += not bad
            if bad and s:
                print('    refused %s: %s' % (k, '; '.join(bad)))
        record(m['id'], cost, 'ok, %d of %d kept' % (kept, len(todo)))
        wrote += kept
        print('  %-18s %d of %d summaries kept ($%.3f)' % (m['id'], kept, len(todo), cost))
        tmp = OUT + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(store, fh, indent=1, ensure_ascii=False, sort_keys=True)
            fh.write('\n')
        os.replace(tmp, OUT)
    print('%d summaries written, $%.3f' % (wrote, spent))


if __name__ == '__main__':
    main()
