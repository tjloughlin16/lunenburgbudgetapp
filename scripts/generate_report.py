#!/usr/bin/env python3
"""GENERATE A SUGGESTED REPORT WITH AN AGENT, in its own copy of the repository.

    python3 scripts/generate_report.py <slug>                 # start (or continue) a generation
    python3 scripts/generate_report.py <slug> --answer "..."  # answer its open questions; it resumes
    python3 scripts/generate_report.py <slug> --dry-run       # print the prompt and the fence; spend nothing
    python3 scripts/generate_report.py --status               # every generation, one line each

Started by the Generate button on the ingestion dashboard (dashboard_server.py). Published by
the Publish button (publish_generation.py) -- never by this script.

WHY. TJ, 15 October 2026: a Generate button whose agent "feeds information back into a
'generation report'"; then *"the goal is that suggested reports may be auto-generated in 3
months from now. so we need this process crisp"*; then *"make sure its flexible. it should be
able to do anything YOU could do if i asked you to generate a report, such as creating a hub in
case its a big report"*; and *"if you are cloning, make sure we dont hit the same issues as
refresh, which means losing work, stepping on commits"*.

THE SHAPE THAT FOLLOWS FROM ALL FOUR.

  ITS OWN COPY. Each generation gets a git worktree, ~/lunenburgbudgets-gen/<slug>, on its own
  branch gen/<slug>, cut from the local main when it is first asked for. Inside it the agent
  has every tool a session has -- it can register a hub and several topics, write generators
  and extractors, edit components, run any check. Nothing it does reaches the person's tree
  until somebody presses Publish.

  A FENCE THE AGENT CANNOT TALK ITS WAY THROUGH. The whole `claude -p` process runs under a
  macOS sandbox profile: it can WRITE only inside its worktree (plus its own session files and
  temp), and it cannot READ the Cloudflare credential, ssh keys or the GitHub token. So it
  cannot push to the archive bucket (write-once for ten years), deploy, write D1, or push git,
  whatever it tries. It reads the person's tree, read-only, for the documents git does not hold.

  NOTHING IS LOST, NOTHING IS STEPPED ON -- the refresh's three failures, each closed:
    * it reset its tree each morning                -> a worktree is never reset, cleaned,
                                                       stashed or removed by any script here
    * it swept another session's edit into a commit -> this worktree belongs to ONE agent; the
                                                       runner commits it after every run, so
                                                       work is in git within seconds of the
                                                       agent stopping, on gen/<slug> only
    * it pushed to side branches when main moved    -> publish replays onto main the way
                                                       refresh_git does, and REFUSES rather
                                                       than overwrites uncommitted work
  check_refresh_safe.py scans this file and publish_generation.py for every destructive git
  form and fails the build if one appears.

  SHARED INDEX FILES ARE NOT COMMITTED HERE. topics.json, the sitemap, the source catalogue
  and the like are rebuilt from everything on main at publish time; committing a worktree's
  copy of them would only conflict with every other change made meanwhile (DERIVED below).

  CHECKED BY MACHINE. The agent declares the pages it built and the commands that check them;
  the runner runs those checks itself, in the sandbox, and records each result. The agent's
  word that it worked is not the check.

WHERE THE RECORD LIVES. notes/report-generations/<slug>/generation.json in the PERSON's tree
(tracked; the dashboard reads it): status, every run, cost, the agent's structured report,
the checks, the branch and its commits. The agent's own notes go in the worktree and arrive on
main with the branch.
"""
import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import build_suggested_reports as SR  # noqa: E402

# REPORT_GEN_* exist for testing the plumbing somewhere that is not the trial record.
GEN = os.environ.get('REPORT_GEN_DIR') or os.path.join(ROOT, 'notes', 'report-generations')
TREES = os.environ.get('REPORT_GEN_TREES') or os.path.expanduser('~/lunenburgbudgets-gen')
LOGS = os.path.join(ROOT, 'build', 'report-generations')
LOCK = os.path.join(LOGS, 'RUNNING')
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
MODEL = os.environ.get('REPORT_GEN_MODEL') or 'sonnet'
# PER RUN. A hub with several topics is real work; $5 is about 1% of the week at the measured
# $5 a percent. Continue resumes with a fresh cap. Raise only on evidence.
BUDGET_USD = float(os.environ.get('REPORT_GEN_BUDGET') or 5.00)
TIMEOUT_S = 60 * 60
HOME = os.path.expanduser('~')

# Rebuilt on main at publish (publish_generation.py), never carried on a generation branch.
DERIVED = ['fy28/src/data/topic-categories.json', 'fy28/public/data/topics.json',
           'fy28/public/sitemap.xml', 'fy28/public/data/reports.json',
           'fy28/public/data/site-changes.json', 'fy28/public/data/sources.json',
           'fy28/src/data/sources.json', 'fy28/public/docs', 'notes/generated', 'README.md']

RESULT = {
    'type': 'object', 'additionalProperties': False,
    'required': ['status', 'summary', 'autogen', 'pages', 'checks', 'datasets_used', 'figures',
                 'open_questions', 'gaps', 'next_steps'],
    'properties': {
        'status': {'type': 'string', 'enum': ['draft-ready', 'needs-input', 'blocked']},
        'summary': {'type': 'string', 'description': 'two or three sentences: what was built and what it establishes, or why it stopped'},
        'autogen': {'type': 'object', 'additionalProperties': False, 'required': ['verdict', 'reasons'],
                    'properties': {
                        'verdict': {'type': 'string', 'enum': ['yes', 'with-a-person', 'no']},
                        'reasons': {'type': 'array', 'items': {'type': 'string'},
                                    'description': 'why a report of THIS KIND could or could not be regenerated by a script with nobody watching, whenever its data updates'}}},
        'pages': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                  'required': ['path', 'kind', 'title'], 'properties': {
                      'path': {'type': 'string', 'description': 'the site address, e.g. /sewer/sewer-connection-fees'},
                      'kind': {'type': 'string', 'enum': ['hub', 'topic', 'analysis', 'other']},
                      'title': {'type': 'string'}}},
                  'description': 'every page built or changed, for review'},
        'checks': {'type': 'array', 'items': {'type': 'string'},
                   'description': 'shell commands, run from the repository root, that must exit 0 for this work to be right -- each generator --check you wrote, scripts/topics.py, and anything else that proves it'},
        'datasets_used': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                          'required': ['source', 'what'], 'properties': {
                              'source': {'type': 'string'}, 'what': {'type': 'string'}}}},
        'figures': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                    'required': ['value', 'what', 'kind', 'source'], 'properties': {
                        'value': {'type': 'string'}, 'what': {'type': 'string'},
                        'kind': {'type': 'string', 'enum': ['published', 'stated', 'estimate']},
                        'source': {'type': 'string'}}}},
        'open_questions': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                           'required': ['question', 'why', 'blocking'], 'properties': {
                               'question': {'type': 'string'}, 'why': {'type': 'string'},
                               'blocking': {'type': 'boolean'}}}},
        'gaps': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                 'required': ['what', 'closes'], 'properties': {
                     'what': {'type': 'string'}, 'closes': {'type': 'string'}}}},
        'next_steps': {'type': 'array', 'items': {'type': 'string'}},
    }}


def now():
    return dt.datetime.now().astimezone().isoformat(timespec='seconds')


def gdir(slug):
    return os.path.join(GEN, slug)


def tree(slug):
    return os.path.join(TREES, slug)


def branch(slug):
    return (os.environ.get('REPORT_GEN_BRANCH_PREFIX') or 'gen/') + slug


def git(cwd, *args, check=True):
    r = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True,
                       env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'))
    if check and r.returncode:
        raise SystemExit('generate_report: git %s failed: %s' % (' '.join(args[:3]), (r.stderr or r.stdout)[:400]))
    return r


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
    raise SystemExit('generate_report: no suggestion with slug %r' % slug)


# ------------------------------------------------------------------ the worktree

def make_tree(slug):
    """Create the worktree once; reuse it for every later run of the same generation. Never
    reset, never recreated over existing work."""
    t = tree(slug)
    if os.path.isdir(t):
        return t
    os.makedirs(TREES, exist_ok=True)
    if git(ROOT, 'rev-parse', '--verify', '-q', 'refs/heads/' + branch(slug), check=False).returncode == 0:
        git(ROOT, 'worktree', 'add', t, branch(slug))          # the branch exists: attach, keep its work
    else:
        git(ROOT, 'worktree', 'add', '-b', branch(slug), t, 'main')
    # NO PUSH FROM HERE, EVEN BY MISTAKE: a per-worktree push URL that goes nowhere.
    git(ROOT, 'config', 'extensions.worktreeConfig', 'true')
    git(t, 'config', '--worktree', 'remote.origin.pushurl', 'no-push-from-a-generation-worktree')
    # WHAT GIT DOES NOT HOLD. The analysis database is copied (a generator may rebuild it);
    # the minutes index and node_modules are linked, read-only in effect because the sandbox
    # forbids writing outside this tree. Documents are read from the person's tree.
    db = os.path.join(ROOT, 'sources', 'data', 'lunenburg.db')
    if os.path.exists(db):
        shutil.copy2(db, os.path.join(t, 'sources', 'data', 'lunenburg.db'))
    for rel in ('sources/data/minutes-fts.db', 'fy28/node_modules', 'node_modules'):
        src, dst = os.path.join(ROOT, rel), os.path.join(t, rel)
        if os.path.exists(src) and not os.path.lexists(dst):
            os.symlink(src, dst)
    return t


def sandbox(slug):
    """The fence for the whole agent process, and for every check run here."""
    t = os.path.realpath(tree(slug))
    p = os.path.join(LOGS, '%s.sb' % slug)
    os.makedirs(LOGS, exist_ok=True)
    nm_tmp = os.path.realpath(os.path.join(ROOT, 'fy28', 'node_modules', '.tmp'))
    with open(p, 'w') as fh:
        fh.write('''(version 1)
(allow default)
(deny file-write*)
(allow file-write* (subpath "%(t)s") (subpath "/private/tmp") (subpath "/private/var/folders")
  (subpath "%(h)s/.claude") (regex #"^%(h)s/\\.claude\\.json") (subpath "%(h)s/Library/Caches")
  (subpath "%(h)s/.npm") (subpath "%(nm)s") (literal "/dev/null") (literal "/dev/tty") (regex #"^/dev/ttys"))
(deny file-read* (subpath "%(h)s/Library/Preferences/.wrangler") (subpath "%(h)s/.wrangler")
  (subpath "%(h)s/.ssh") (subpath "%(h)s/.config/gh") (subpath "%(h)s/.aws"))
''' % dict(t=t, h=HOME, nm=nm_tmp))
    return p


def commit_tree(slug, message):
    """Everything the agent changed in ITS tree, minus the shared index files. -> sha or None.
    Its tree holds nobody else's work, which is what makes `add -A` safe HERE and nowhere else."""
    t = tree(slug)
    spec = ['.'] + [':(exclude)%s' % d for d in DERIVED]
    git(t, 'add', '-A', '--', *spec)
    if not git(t, 'diff', '--cached', '--quiet', check=False).returncode:
        return None
    git(t, 'commit', '-q', '-m', message)
    return git(t, 'rev-parse', 'HEAD').stdout.strip()


def branch_summary(slug):
    t = tree(slug)
    base = git(t, 'merge-base', 'main', 'HEAD').stdout.strip()
    stat = git(t, 'diff', '--stat', '%s..HEAD' % base).stdout.strip().splitlines()
    files = git(t, 'diff', '--name-status', '%s..HEAD' % base).stdout.strip().splitlines()
    commits = git(t, 'rev-list', '%s..HEAD' % base).stdout.split()
    return dict(branch=branch(slug), worktree=t, base=base, head=git(t, 'rev-parse', 'HEAD').stdout.strip(),
                commits=len(commits), files=files[:200], stat=stat[-1] if stat else '')


def run_checks(slug, commands):
    """Each declared check, run by US, in the sandbox, in the worktree. Plus the registry."""
    t = tree(slug)
    sb = sandbox(slug)
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''), PYTHONDONTWRITEBYTECODE='1')
    out = []
    # THE SHARED INDEXES FIRST, in the worktree: they are not carried on the branch (DERIVED),
    # so a check that compares against one would fail for a reason that is ours, not the
    # agent's. Rebuilt here for checking and preview; rebuilt again on main at publish.
    for gen in ('build_topics_index.py', 'build_reports_index.py'):
        subprocess.run(['sandbox-exec', '-f', sb, sys.executable, 'scripts/' + gen], cwd=t,
                       capture_output=True, text=True, env=env, timeout=900)
    for cmd in ['python3 scripts/topics.py'] + [c for c in commands if c.strip()][:12]:
        r = subprocess.run(['sandbox-exec', '-f', sb, '/bin/bash', '-c', cmd], cwd=t,
                           capture_output=True, text=True, env=env, timeout=900)
        out.append(dict(cmd=cmd, exit=r.returncode, tail=(r.stdout + r.stderr)[-600:]))
    return out


# ------------------------------------------------------------------ the agent

def prompt(s, slug):
    t = tree(slug)
    meets = '\n'.join('- %s, %s (%s): %s -- heard: "%s" (%s)' % (
        o['date'], o['board'], o['fiscal_year'], o['question_then'], o['words_as_heard'], o['watch_at'])
        for o in s['occurrences'])
    return f"""You are building a report for the Lunenburg budget website from a suggestion the town's meetings raised. You run unattended; nobody is watching. Do it the way an experienced session in this repository would if TJ said "generate this report": whatever it needs -- one topic page, several, or a hub with topics, a new generator, an extractor, a component.

THE SUGGESTION
title: {s['title']}   slug: {slug}
question: {s['question']}
threads it would serve: {s.get('threads') or 'none'}
numbers in play, as heard in the captions (a finding aid, not a source): {s.get('data_in_play_as_heard') or 'none'}
the meetings that raised it:
{meets}

WHERE YOU ARE. Your working directory, {t}, is your own git worktree of the repository on branch {branch(slug)}. Change anything in it. It is yours alone: nobody else edits it. CLAUDE.md is the rulebook; follow it, especially rules 1, 2, 3, 7, 7a-7d, 11, 12, 13, 13c. notes/process/WRITING-AN-ANALYSIS.md and notes/process/HUB-AND-SPOKE.md are the process. scripts/topics.py and scripts/topic_registry/ are how pages exist; copy an existing category and generator (scripts/build_monty_tech_topics.py is short).

WHAT YOU CANNOT DO, by design -- do not try, and do not treat a refusal as an error to work around:
- Write outside this worktree. The documents git does not hold (PDFs, spreadsheets) are readable, read-only, at {ROOT}/sources/...
- Push git, commit (the runner commits your tree after you stop), push to the archive bucket, run ingest.py --secure or sync_archive.py, deploy, write D1, start `claude`, run process_meeting.py or any metered stream, or run `npm run build:site` / `vite build`. Fetching a NEW document cannot be finished here: name it in open_questions or gaps with its address.
- Contact any outside service except reading public web pages.

WHAT TO RETURN, in the structured form requested:
- pages: every page you built or changed, with its site address, for review.
- checks: the commands that prove it, run from the repository root -- each generator's --check, `python3 scripts/build_topics_index.py`, `cd fy28 && npx tsc -b` if you touched TypeScript. The runner runs them itself.
- autogen: THE MOST IMPORTANT FIELD. `yes` only if a script could regenerate this report whenever its data updates, with no judgement call, no document only a person can obtain, no question for anybody. `with-a-person` if a person must decide or check something -- say exactly what. `no` if the data does not exist or the subject is not numbers. A wrong `yes` is worse than a cautious `with-a-person`.
- open_questions: only what a person must answer -- not what the files can. If one blocks you, stop and return needs-input.
- datasets_used, figures (each with the query or cell), gaps (each with the document that would close it), next_steps."""


def run(slug, answer=None, dry=False):
    s = suggestion(slug)
    g = load(slug)
    if g and g['status'] in ('queued', 'running', 'publishing'):
        raise SystemExit('generate_report: %s is %s' % (slug, g['status']))
    if g and g['status'] == 'published':
        raise SystemExit('generate_report: %s is already published' % slug)
    resume = bool(answer is not None or (g and g.get('session_id')))
    if not g:
        g = dict(slug=slug, id=s['id'], title=s['title'], question=s['question'],
                 threads=s.get('threads', ''), score=s['score'], requested_at=now(),
                 status='queued', runs=[], answers=[], reviews=[], result=None, checks=[],
                 session_id=None, cost_usd=0.0, branch=branch(slug), worktree=tree(slug))
    text = prompt(s, slug)
    if answer is not None:
        g['answers'].append(dict(at=now(), text=answer))
        text = ('From the person running this project:\n\n%s\n\nContinue under the same rules and '
                'return the same structured result.' % answer)
    elif resume:
        text = 'Continue where you stopped, under the same rules, and return the same structured result.'
    allowed = ['Read', 'Write', 'Edit', 'MultiEdit', 'Glob', 'Grep', 'Bash', 'WebFetch', 'WebSearch', 'TodoWrite']
    denied = ['Task', 'Agent', 'Bash(git push:*)', 'Bash(git commit:*)', 'Bash(claude:*)',
              'Bash(npx wrangler:*)', 'Bash(wrangler:*)', 'Bash(npm run build:*)', 'Bash(npx vite build:*)',
              'Bash(python3 scripts/ingest.py --secure:*)', 'Bash(python3 scripts/sync_archive.py:*)',
              'Bash(python3 scripts/process_meeting.py:*)', 'Bash(python3 scripts/sync_d1.py:*)']
    argv = ['sandbox-exec', '-f', '<profile>', 'claude', '-p', '--model', MODEL,
            '--output-format', 'stream-json', '--verbose', '--max-budget-usd', '%.2f' % BUDGET_USD,
            '--json-schema', json.dumps(RESULT), '--add-dir', ROOT,
            '--allowedTools', *allowed, '--disallowedTools', *denied]
    if resume:
        argv += ['--resume', g['session_id']]
    if dry:
        print('worktree %s on %s; sandbox writes only there' % (tree(slug), branch(slug)))
        print('allowed: %s\ndenied: %s\n' % (allowed, denied))
        print(text)
        return 0
    os.makedirs(LOGS, exist_ok=True)
    if os.path.exists(LOCK):
        raise SystemExit('generate_report: another generation is running (%s)' % open(LOCK).read().strip())
    open(LOCK, 'w').write('%s %s' % (slug, now()))
    try:
        t = make_tree(slug)
        argv[2] = sandbox(slug)
        rec = dict(n=len(g['runs']) + 1, kind='answer' if answer is not None else ('continue' if resume else 'generate'),
                   started=now(), model=MODEL, budget_usd=BUDGET_USD, tool_calls=0, last_action='',
                   finished=None, cost_usd=None, exit=None, error='', commit=None)
        g['runs'].append(rec)
        g['status'] = 'running'
        save(g)
        env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''), GIT_OPTIONAL_LOCKS='0')
        res = None
        with open(os.path.join(LOGS, '%s.jsonl' % slug), 'a', encoding='utf-8') as log:
            p = subprocess.Popen(argv, cwd=t, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
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
                            rec['tool_calls'] += 1
                            inp = c.get('input') or {}
                            what = inp.get('command') or inp.get('file_path') or inp.get('pattern') or inp.get('url') or ''
                            rec['last_action'] = ('%s %s' % (c.get('name'), what))[:160]
                elif ev.get('type') == 'result':
                    res = ev
                if time.time() - last_save > 5:
                    save(g)
                    last_save = time.time()
                if time.time() - t0 > TIMEOUT_S:
                    p.kill()
                    rec['error'] = 'timed out after %d minutes' % (TIMEOUT_S // 60)
                    break
            p.wait()
            rec['exit'] = p.returncode
            if p.returncode and not rec['error'] and not res:
                rec['error'] = (p.stderr.read() or '')[-1500:]
        rec['finished'] = now()
        # WORK IS IN GIT BEFORE ANYTHING ELSE IS JUDGED: whatever happens next, it is on the branch.
        rec['commit'] = commit_tree(slug, 'Generation of %s, run %d (%s)\n\nWritten by an agent in its own '
                                    'worktree (scripts/generate_report.py). Not reviewed until published.'
                                    % (slug, rec['n'], rec['kind']))
        if res:
            rec['cost_usd'] = res.get('total_cost_usd')
            g['session_id'] = res.get('session_id') or g['session_id']
            body = res.get('structured_output')
            if body is None and isinstance(res.get('result'), str):
                try:
                    body = json.loads(res['result'])
                except ValueError:
                    body = None
            if body:
                g['result'] = body
            elif res.get('subtype') != 'error_max_budget_usd':
                rec['error'] = rec['error'] or ('%s: %s' % (res.get('subtype'), str(res.get('result'))[:500]))
        g['cost_usd'] = round(sum(r.get('cost_usd') or 0 for r in g['runs']), 4)
        g['branch_summary'] = branch_summary(slug)
        g['checks'] = run_checks(slug, (g.get('result') or {}).get('checks') or [])
        checks_ok = all(c['exit'] == 0 for c in g['checks'])
        if res and res.get('subtype') == 'error_max_budget_usd':
            g['status'] = 'stopped-at-cap'
        elif not g.get('result'):
            g['status'] = 'failed'
        elif g['result']['status'] == 'draft-ready' and not checks_ok:
            g['status'] = 'invalid'
        else:
            g['status'] = g['result']['status']
        save(g)
    finally:
        if os.path.exists(LOCK):
            os.remove(LOCK)
    print('%s: %s, $%.2f this run, $%.2f in all; checks %s; branch %s, %d commit(s)'
          % (slug, g['status'], rec['cost_usd'] or 0, g['cost_usd'],
             'pass' if checks_ok else 'FAIL', branch(slug), g['branch_summary']['commits']))
    return 0


def status():
    if not os.path.isdir(GEN):
        print('no generations yet')
        return 0
    for slug in sorted(os.listdir(GEN)):
        g = load(slug)
        if g:
            v = (g.get('result') or {}).get('autogen', {}).get('verdict', '-')
            print('%-32s %-14s runs %d  $%.2f  autogen %-14s %s'
                  % (slug, g['status'], len(g['runs']), g['cost_usd'], v, g.get('branch', '')))
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
