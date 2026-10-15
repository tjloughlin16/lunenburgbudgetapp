#!/usr/bin/env python3
"""GENERATE A SUGGESTED REPORT WITH AN AGENT, and keep a record of how it went.

    python3 scripts/generate_report.py <slug>                 # start a generation
    python3 scripts/generate_report.py <slug> --answer "..."  # answer its open questions; it resumes
    python3 scripts/generate_report.py <slug> --dry-run       # print the prompt and the command, spend nothing
    python3 scripts/generate_report.py --status               # every generation, one line each

Started by the button on the ingestion dashboard's Suggested reports tab (dashboard_server.py).

WHY IT EXISTS, AND WHAT IT IS REALLY FOR. TJ, 15 October 2026: *"i want to test
auto-generation ... a generate button, that kicks off an agent, and the agent feeds information
back into a 'generation report' ... it can have open questions, status, etc"* and then: *"the
goal is that suggested reports may be auto-generated in 3 months from now. so we need this
process crisp, and it means we need to identify only reports that make sense to auto-generate
all the time."*

So each run is a TRIAL, and its record is the evidence. Three things make it crisp:

  1. THE OUTPUT IS CHECKED BY MACHINE, NOT READ FOR TONE. The agent must write `build.py`, a
     generator that emits a topic payload through scripts/topic.py (`TP.page(..., draft=...)`)
     -- the same rule-2, length, chart and source checks every published page passes. This
     script runs that generator ITSELF after the agent stops and records pass or fail. The
     agent's own word that it worked is not the check.
  2. EVERY RUN ENDS WITH A VERDICT ON AUTO-GENERATION -- `yes`, `with-a-person`, `no` -- and
     the reasons, the datasets it used and every question it had to ask. Over months, these
     records answer which KINDS of report can be generated without anybody.
  3. IT IS FENCED. The agent can read the repository, query the analysis database read-only,
     search the minutes, and write ONLY inside notes/report-generations/<slug>/. It cannot
     commit, build, deploy, fetch, or start another model. Each run is capped in dollars.

WHERE THE RECORD LIVES. notes/report-generations/<slug>/generation.json -- tracked, so the
trial history survives this machine -- beside the agent's DRAFT.md, build.py and payload.json,
and a gitignored stream log in build/report-generations/<slug>.jsonl.

STATES. queued -> running -> one of: draft-ready (the generator validates), needs-input (open
questions block it), blocked (the data does not exist), failed (the run itself broke), and
invalid (the agent said draft-ready but its generator does not pass), and stopped-at-cap (it
spent the per-run cap with its work on disk; Continue resumes it). Answering resumes the
SAME agent session (`claude -p --resume`), so it keeps what it read.
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import build_suggested_reports as SR  # noqa: E402

# REPORT_GEN_DIR / REPORT_GEN_MODEL / REPORT_GEN_BUDGET exist for testing the plumbing
# somewhere that is not the trial record -- a smoke run must not count as a trial.
GEN = os.environ.get('REPORT_GEN_DIR') or os.path.join(ROOT, 'notes', 'report-generations')
LOGS = os.path.join(ROOT, 'build', 'report-generations')
LOCK = os.path.join(LOGS, 'RUNNING')
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
MODEL = os.environ.get('REPORT_GEN_MODEL') or 'sonnet'
# THE CAP PER RUN. ~0.6% of the week at the account's measured $5 a percent. An answer is a
# new run with its own cap. Raise it only on evidence that good drafts need more.
BUDGET_USD = float(os.environ.get('REPORT_GEN_BUDGET') or 3.00)
TIMEOUT_S = 45 * 60


# THE AGENT'S GENERATOR IS ARBITRARY PYTHON, so it never runs bare. Writing build.py is fenced
# by the tool permissions; RUNNING it is fenced by a macOS sandbox profile: no network, and no
# file writes anywhere except the report's own folder and the temp directories. Both the agent
# (the only python3 command it is allowed) and validate() below run it this way.
def sandbox_profile(slug):
    p = os.path.join(LOGS, '%s.sb' % slug)
    os.makedirs(LOGS, exist_ok=True)
    open(p, 'w').write('''(version 1)
(allow default)
(deny network*)
(deny file-write*)
(allow file-write* (subpath "%s") (subpath "/private/tmp") (subpath "/private/var/folders") (literal "/dev/null"))
''' % os.path.realpath(gdir(slug)))
    return p


def build_cmd(slug):
    return 'sandbox-exec -f %s python3 -B %s/build.py' % (rel(sandbox_profile(slug)), rel(gdir(slug)))


def outside_changes(slug, before):
    """Paths git sees as changed now that it did not before the run, outside the report's
    folder. Recorded as a breach, NEVER reverted: another agent may own them."""
    after = git_dirty()
    mine = rel(gdir(slug)) + '/'
    return sorted(p for p in after - before if not p.startswith(mine))


def git_dirty():
    r = subprocess.run(['git', 'status', '--porcelain', '-uall'], cwd=ROOT, capture_output=True, text=True)
    return {ln[3:] for ln in r.stdout.splitlines()}

RESULT = {
    'type': 'object', 'additionalProperties': False,
    'required': ['status', 'summary', 'autogen', 'datasets_used', 'figures', 'open_questions',
                 'gaps', 'proposed', 'next_steps'],
    'properties': {
        'status': {'type': 'string', 'enum': ['draft-ready', 'needs-input', 'blocked']},
        'summary': {'type': 'string', 'description': 'two or three sentences: what the draft establishes, or why it stopped'},
        'autogen': {'type': 'object', 'additionalProperties': False, 'required': ['verdict', 'reasons'],
                    'properties': {
                        'verdict': {'type': 'string', 'enum': ['yes', 'with-a-person', 'no']},
                        'reasons': {'type': 'array', 'items': {'type': 'string'},
                                    'description': 'why a report of THIS KIND could or could not be regenerated by a script with nobody watching, whenever its data updates'}}},
        'datasets_used': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                          'required': ['source', 'what'], 'properties': {
                              'source': {'type': 'string', 'description': 'a path in sources/data, a database table, or a document'},
                              'what': {'type': 'string'}}}},
        'figures': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                    'required': ['value', 'what', 'kind', 'source'], 'properties': {
                        'value': {'type': 'string'}, 'what': {'type': 'string'},
                        'kind': {'type': 'string', 'enum': ['published', 'stated', 'estimate']},
                        'source': {'type': 'string', 'description': 'the query, the cell or the line that produced it'}}}},
        'open_questions': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                           'required': ['question', 'why', 'blocking'], 'properties': {
                               'question': {'type': 'string'}, 'why': {'type': 'string'},
                               'blocking': {'type': 'boolean'}}}},
        'gaps': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                 'required': ['what', 'closes'], 'properties': {
                     'what': {'type': 'string'}, 'closes': {'type': 'string'}}}},
        'proposed': {'type': 'object', 'additionalProperties': False, 'required': ['home', 'title'],
                     'properties': {'home': {'type': 'string'}, 'title': {'type': 'string'}}},
        'next_steps': {'type': 'array', 'items': {'type': 'string'}},
    }}


def now():
    return dt.datetime.now().astimezone().isoformat(timespec='seconds')


def gdir(slug):
    return os.path.join(GEN, slug)


def rel(p):
    r = os.path.relpath(p, ROOT)
    return p if r.startswith('..') else r


def load(slug):
    p = os.path.join(gdir(slug), 'generation.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None


def save(g):
    d = gdir(g['slug'])
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, 'generation.json')
    with open(p + '.tmp', 'w', encoding='utf-8') as fh:
        json.dump(g, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    os.replace(p + '.tmp', p)


def suggestion(slug):
    for r in SR.ranked(dt.date.today().isoformat()):
        if r['slug'] == slug:
            return r
    raise SystemExit('generate_report: no suggestion with slug %r in %s' % (slug, rel(SR.OUT)))


def categories():
    import topics as T
    return [(c['id'], c['shelf']) for c in T.CATEGORIES]


def prompt(s, slug):
    d = rel(gdir(slug))
    meets = '\n'.join('- %s, %s (%s): %s -- heard: "%s" (%s)' % (
        o['date'], o['board'], o['fiscal_year'], o['question_then'], o['words_as_heard'], o['watch_at'])
        for o in s['occurrences'])
    cats = ', '.join('%s (%s)' % c for c in categories())
    return f"""You are drafting ONE report for the Lunenburg budget website, from a suggestion the town's meetings raised. You run unattended; nobody is watching. Your record is evidence for whether reports like this one can be generated with nobody at all.

THE SUGGESTION
title: {s['title']}   slug: {slug}
question: {s['question']}
threads it would serve: {s.get('threads') or 'none'}
numbers in play, as heard in the captions (a finding aid, not a source): {s.get('data_in_play_as_heard') or 'none'}
file names that share a word with it (a place to start, not a finding): {s.get('data_leads')}
the meetings that raised it:
{meets}

THE RULES are in CLAUDE.md, which you have. The ones that decide this draft: rule 1 (never mix budgets and actuals), 2 (every figure computed, never typed), 3 (say whose number it is), 7 (a figure is a fact, an explanation is a hypothesis -- label it), 7b (a conclusion is a metric and two lines), 7c (what cannot be answered is a gap with the document that would close it), 11 (a budget line is net), 13 (cite the coordinate and the raw value), 13c (a pattern that finds nothing is not an absence -- look at the document). The process is notes/process/WRITING-AN-ANALYSIS.md; read it.

WHAT YOU MAY DO
- Read anything in the repository. Query `sqlite3 -readonly sources/data/lunenburg.db` (notes/reference/SCHEMA.md documents it). Search what was said with `python3 scripts/search_minutes.py "<words>"`.
- Write ONLY inside {d}/. Nothing else in the repository changes. You cannot commit, build, deploy, fetch from the web, or start another model.

WHAT YOU MUST PRODUCE, in {d}/
1. DRAFT.md -- what the data shows, what it does not show, and any hypothesis labelled as one. Every figure with the query or the cell it came from.
2. build.py -- a generator that writes {d}/payload.json by calling scripts/topic.py:
     import sys, os; sys.path.insert(0, os.path.join(<repo root>, 'scripts'))
     import topic as TP, ladder as LD, conclusions as C; from conclusions import figure
     payload = TP.page('{slug}', finding, facts, conclusions, chart=..., sources=[...], draft={{'title': ..., 'home': ...}})
     ...then write payload to {d}/payload.json (json.dump, indent=1).
   Read scripts/topic.py's docstring and copy the idiom of an existing generator (scripts/build_monty_tech_topics.py is short). Every figure must be READ from data in build.py -- a query or a CSV read -- never typed. `home` is one of these shelves: {cats}. A title is two to four words, a noun phrase.
   Run it with EXACTLY `{build_cmd(slug)}` -- the only way you are allowed to run it -- until it passes. It runs in a sandbox: it can read anything, and write only inside {d}/. If the data cannot carry a page, do not fake one: say so.
3. Your final answer, in the structured form requested: status, summary, the auto-generation verdict with reasons, datasets used, figures, open questions (only ones a person must answer -- things the files cannot), gaps, proposed shelf and title, next steps.

THE AUTO-GENERATION VERDICT is the most important thing you return. `yes` only if a script could regenerate this report whenever its data updates, with no judgement call, no document only a person can obtain, and no question for anybody. `with-a-person` if it works but a person must decide or check something -- say exactly what. `no` if the data does not exist or the subject is not numbers. Be strict: a wrong `yes` is worse than a cautious `with-a-person`.

If a question blocks you, stop and return status needs-input with the question. Do not guess past it."""


def allowed(slug):
    d = rel(gdir(slug))
    a = os.path.join(ROOT, d)
    return ['Read', 'Grep', 'Glob',
            'Bash(sqlite3 -readonly:*)', 'Bash(python3 scripts/search_minutes.py:*)',
            'Bash(%s)' % build_cmd(slug),
            'Write(%s/**)' % d, 'Edit(%s/**)' % d, 'Write(/%s/**)' % a, 'Edit(/%s/**)' % a]


def validate(slug):
    """Run the agent's generator OURSELVES. Pass means topic.py accepted the page."""
    b = os.path.join(gdir(slug), 'build.py')
    if not os.path.exists(b):
        return dict(ran=False, passed=False, error='no build.py was written')
    r = subprocess.run(build_cmd(slug).split(), cwd=ROOT, capture_output=True, text=True, timeout=600)
    p = os.path.join(gdir(slug), 'payload.json')
    ok = r.returncode == 0 and os.path.exists(p)
    return dict(ran=True, passed=ok, at=now(),
                error='' if ok else (r.stderr or r.stdout or 'no payload.json')[-1500:])


def run(slug, answer=None, dry=False):
    s = suggestion(slug)
    g = load(slug)
    if answer is None and g and g['status'] in ('queued', 'running'):
        raise SystemExit('generate_report: %s is already %s' % (slug, g['status']))
    if answer is not None and not (g and g.get('session_id')):
        raise SystemExit('generate_report: %s has no session to answer' % slug)
    if answer is None and not g:
        g = dict(slug=slug, id=s['id'], title=s['title'], question=s['question'],
                 threads=s.get('threads', ''), score=s['score'], requested_at=now(),
                 status='queued', runs=[], answers=[], result=None, validation=None,
                 session_id=None, cost_usd=0.0)
    if answer is not None:
        g['answers'].append(dict(at=now(), text=answer))
        text = ('Answers to your open questions, from the person running this project:\n\n%s\n\n'
                'Continue the draft under the same rules and return the same structured result.' % answer)
    else:
        text = prompt(s, slug)
    argv = ['claude', '-p', '--model', MODEL, '--output-format', 'stream-json', '--verbose',
            '--max-budget-usd', '%.2f' % BUDGET_USD, '--json-schema', json.dumps(RESULT),
            '--allowedTools', *allowed(slug)]
    if answer is not None:
        argv += ['--resume', g['session_id']]
    if dry:
        print(' '.join(a if ' ' not in a else repr(a) for a in argv[:8]), '...')
        print('\n'.join(allowed(slug)))
        print('\n' + text)
        return 0
    os.makedirs(LOGS, exist_ok=True)
    if os.path.exists(LOCK):
        raise SystemExit('generate_report: another generation is running (%s)' % open(LOCK).read().strip())
    open(LOCK, 'w').write('%s %s' % (slug, now()))
    before = git_dirty()
    run_rec = dict(n=len(g['runs']) + 1, kind='answer' if answer is not None else 'generate',
                   started=now(), model=MODEL, budget_usd=BUDGET_USD, tool_calls=0, last_action='',
                   finished=None, cost_usd=None, exit=None, error='')
    g['runs'].append(run_rec)
    g['status'] = 'running'
    save(g)
    os.makedirs(gdir(slug), exist_ok=True)
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    res = None
    try:
        with open(os.path.join(LOGS, '%s.jsonl' % slug), 'a', encoding='utf-8') as log:
            p = subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True, env=env)
            p.stdin.write(text)
            p.stdin.close()
            t0, last_save = time.time(), 0
            for line in p.stdout:
                log.write(line)
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                if ev.get('type') == 'system' and ev.get('session_id'):
                    g['session_id'] = ev['session_id']
                elif ev.get('type') == 'assistant':
                    for c in (ev.get('message') or {}).get('content') or []:
                        if c.get('type') == 'tool_use':
                            run_rec['tool_calls'] += 1
                            inp = c.get('input') or {}
                            what = inp.get('command') or inp.get('file_path') or inp.get('pattern') or ''
                            run_rec['last_action'] = ('%s %s' % (c.get('name'), what))[:160]
                elif ev.get('type') == 'result':
                    res = ev
                if time.time() - last_save > 5:
                    save(g)
                    last_save = time.time()
                if time.time() - t0 > TIMEOUT_S:
                    p.kill()
                    run_rec['error'] = 'timed out after %d minutes' % (TIMEOUT_S // 60)
                    break
            p.wait()
            run_rec['exit'] = p.returncode
            if p.returncode and not run_rec['error']:
                run_rec['error'] = (p.stderr.read() or '')[-1500:]
    finally:
        if os.path.exists(LOCK):
            os.remove(LOCK)
    run_rec['finished'] = now()
    if res:
        run_rec['cost_usd'] = res.get('total_cost_usd')
        g['session_id'] = res.get('session_id') or g['session_id']
        body = res.get('structured_output')
        if body is None and isinstance(res.get('result'), str):
            try:
                body = json.loads(res['result'])
            except ValueError:
                body = None
        if res.get('is_error') or not body:
            run_rec['error'] = run_rec['error'] or ('%s: %s' % (res.get('subtype'), str(res.get('result'))[:500]))
        else:
            g['result'] = body
    g['cost_usd'] = round(sum(r.get('cost_usd') or 0 for r in g['runs']), 4)
    g['validation'] = validate(slug)
    breach = outside_changes(slug, before)
    run_rec['changed_outside_its_folder'] = breach   # other agents' work can land here too
    if res and res.get('subtype') == 'error_max_budget_usd':
        # NOT A FAILURE: it ran out of the per-run cap with its work on disk. Continue resumes
        # the same session with a fresh cap.
        g['status'] = 'stopped-at-cap'
    elif not g['result']:
        g['status'] = 'failed'
    elif g['result']['status'] == 'draft-ready' and not g['validation']['passed']:
        g['status'] = 'invalid'
    else:
        g['status'] = g['result']['status']
    save(g)
    print('%s: %s, $%.2f this run, $%.2f in all; generator %s'
          % (slug, g['status'], run_rec['cost_usd'] or 0, g['cost_usd'],
             'passes' if g['validation']['passed'] else 'does not pass'))
    return 0


def status():
    if not os.path.isdir(GEN):
        print('no generations yet')
        return 0
    for slug in sorted(os.listdir(GEN)):
        g = load(slug)
        if g:
            v = (g.get('result') or {}).get('autogen', {}).get('verdict', '-')
            print('%-32s %-12s runs %d  $%.2f  autogen %s' % (slug, g['status'], len(g['runs']), g['cost_usd'], v))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('slug', nargs='?')
    ap.add_argument('--answer')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--status', action='store_true')
    a = ap.parse_args()
    if a.status or not a.slug:
        return status()
    return run(a.slug, a.answer, a.dry_run)


if __name__ == '__main__':
    sys.exit(main())
