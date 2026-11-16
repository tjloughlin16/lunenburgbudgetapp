#!/usr/bin/env python3
"""The prerender build gate: review why a build wanted to render too much, then approve it.

    python3 scripts/prerender_gate.py status            # is a build blocked, and on what
    python3 scripts/prerender_gate.py review            # an agent finds what caused it
    python3 scripts/prerender_gate.py approve --by TJ --reason "the menu hook fix; one full render"

WHY THIS EXISTS. From 14 to 16 November 2026 every daily refresh re-rendered all 3,865 routes
-- 48 minutes each -- because a menu hook on every page read the clock, and a fetch of a file
the refresh rewrites daily made that file an input of every page. Nothing said so: the log
printed `0 reused` and a run that took three hours read as normal. TJ: *"lets also build a
build gate that blocks a build when it tries to render more than 100 pages. it has to be
explicitly approved, but needs agentic review to see what caused it."*

fy28/scripts/prerender.mjs decides, before Chrome starts, why each route cannot be reused.
Past PRERENDER_GATE routes (100) it writes those causes to `fy28/.prerender-cache/
gate-blocked.json` and exits 4. This script is the other half:

- `review` gives the causes, the commits since the last deployed build and the diffs of the
  inputs that changed to one agent call (scripts/claude_lean.py, sonnet, read-only tools over
  fy28/), which names the cause with evidence and says whether a full render is the right
  answer or a defect to fix. Written to `build/prerender-gate/` and printed. The refresh runs it
  automatically when its build is gated (scripts/refresh.py).
- `approve` is the owner's decision, and only that. It approves the blocked CAUSE (a
  fingerprint of the causes covering 5%+ of the routes), so a retry after more commits still
  matches; it is good for one successful build within 48 hours, then spent.

An approval is not the review. `approve` refuses when no review has been written for the
blocked build, unless `--without-review` says why.
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import claude_lean  # noqa: E402

APP = os.environ.get('PRERENDER_GATE_APP') or os.path.join(ROOT, 'fy28')  # a scratch copy, for testing
CACHE = os.path.join(APP, '.prerender-cache')
BLOCKED = os.path.join(CACHE, 'gate-blocked.json')
APPROVED = os.path.join(CACHE, 'gate-approved.json')
OUT = os.path.join(ROOT, 'build', 'prerender-gate')
SHIP = os.path.join(APP, 'dist', 'data', 'ship.json')
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
MODEL = os.environ.get('PRERENDER_GATE_MODEL', 'sonnet')

SYSTEM = """You review why a static-site prerender wanted to re-render far more pages than a
daily data refresh should touch. Pages are reused when every input they were seen to read is
byte-identical. Each cause key means:

- "input changed: /path" -- a file the page fetched while rendering now hashes differently.
  If ONE such path covers most routes, some component on every page (menu, footer, layout,
  a root-level effect) fetches it; find which, under /src/.
- "reads the clock (rendered on an earlier day)" -- code ran during render that READ the date
  (Date.now, a used `new Date()`, Intl date formatting). On every page means a shared component.
- "shell, probe or prerender script changed" -- fy28/index.html (the built shell) or
  fy28/scripts/prerender.mjs changed. A real code or shell change: a full render is correct,
  unless the shell carries data that changes daily.
- "never rendered before" -- new routes. "reads another host" -- a cross-origin fetch.
- "input changed: /assets/index-*.js" -- the app bundle changed: any code change. Correct.

Decide: is this an INTENDED full render (code, shell or bundle change someone made on purpose)
or a DEFECT (a shared component depending on daily data or the clock)? Name the file and the
code responsible, with the evidence you read. You may read files under the fy28 directory
given; paths you open must be absolute. Be brief and concrete.

A cause you did not READ is a hypothesis. If you could not open the file that would show it,
or the evidence does not single out one change, the verdict is "unclear" and you say what you
could not check. Never present an inference as the cause. "shell, probe or prerender script
changed" on every route is usually a deliberate code change: look at the diffs given before
calling it a defect."""

SCHEMA = {
    'type': 'object',
    'properties': {
        'verdict': {'type': 'string', 'enum': ['intended', 'defect', 'unclear']},
        'cause': {'type': 'string', 'description': 'One or two sentences: what made these routes render.'},
        'evidence': {'type': 'string', 'description': 'Files, lines, commits you read that show it.'},
        'fix': {'type': 'string', 'description': 'For a defect, the change that removes it. Else empty.'},
        'approve': {'type': 'string', 'description': 'One line: whether approving this full render is reasonable, and why.'},
    },
    'required': ['verdict', 'cause', 'evidence', 'fix', 'approve'],
}


def load(path):
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True).stdout


def latest_review(token):
    if not os.path.isdir(OUT):
        return None
    for name in sorted(os.listdir(OUT), reverse=True):
        if name.endswith('.json'):
            r = load(os.path.join(OUT, name))
            if r and r.get('token') == token:
                return os.path.join(OUT, name)
    return None


def status(_a):
    b = load(BLOCKED)
    if not b:
        print('no build is blocked by the prerender gate.')
        ap = load(APPROVED)
        if ap:
            print('an approval is waiting to be spent: cause %s by %s at %s' % (ap['token'], ap['by'], ap['at']))
        return 0
    print('BLOCKED %s: %d of %d routes would render (gate %d), cause %s'
          % (b['at'], b['to_render'], b['of'], b['gate'], b['token']))
    for c in b['causes'][:12]:
        print('  %6d  %s' % (c['routes'], c['cause']))
    rv = latest_review(b['token'])
    print('review: %s' % (rv or 'none yet -- python3 scripts/prerender_gate.py review'))
    return 1


def review(a):
    b = load(BLOCKED)
    if not b:
        print('no build is blocked; nothing to review.')
        return 0
    ship = load(SHIP) or {}
    since = ship.get('commit')
    rng = ['%s..HEAD' % since] if since else ['--since=4.days']
    paths = ['fy28/src', 'fy28/index.html', 'fy28/scripts/prerender.mjs', 'fy28/vite.config.ts']
    changed = [c['cause'][len('input changed: '):] for c in b['causes']
               if c['cause'].startswith('input changed: ') and c['routes'] >= max(1, b['to_render'] * 0.05)]
    parts = ['BLOCKED BUILD:\n' + json.dumps({k: b[k] for k in ('to_render', 'of', 'gate', 'causes', 'sample')}, indent=1)[:12000],
             'LAST DEPLOYED BUILD: %s' % (json.dumps(ship) if ship else 'unknown'),
             'COMMITS SINCE, touching app code or the shell:\n' + (git('log', '--format=%h %ci %s', *rng, '--', *paths)[:6000] or '(none)'),
             'DIFF STAT of app code since:\n' + (git('diff', '--stat', since, 'HEAD', '--', *paths)[:4000] if since else '(no deployed commit known)'),
             'UNCOMMITTED changes to app code in the working tree (a hand build includes these; a '
             'refresh builds only the commit):\n' + (git('diff', 'HEAD', '--', *paths)[:8000] or '(none)')]
    for p in changed[:4]:
        src = 'fy28/public' + p
        parts.append('INPUT %s, recent commits:\n%s' % (p, git('log', '-6', '--format=%h %ci %s', '--', src)[:2000] or '(not tracked: generated at build time)'))
    parts.append('The app source is under %s/src; the prerenderer is %s/scripts/prerender.mjs.' % (os.path.join(ROOT, 'fy28'), os.path.join(ROOT, 'fy28')))
    prompt = '\n\n'.join(parts)
    if a.dry_run:
        print(prompt)
        return 0
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    r = claude_lean.run(['claude', '-p', '--tools', 'Read,Grep,Glob', '--allowedTools', 'Read,Grep,Glob',
                         '--model', MODEL,
                         '--system-prompt', SYSTEM, '--json-schema', json.dumps(SCHEMA),
                         '--output-format', 'json', '--max-budget-usd', '1.50'],
                        add_dirs=[os.path.realpath(os.path.join(ROOT, 'fy28')), APP], input=prompt, capture_output=True, text=True, env=env, timeout=900)
    if r.returncode != 0:
        print((r.stdout + r.stderr)[-1500:])
        print('the review call failed; the build stays blocked.')
        return 2
    try:
        outer = json.loads(r.stdout)
        found = outer.get('structured_output') or json.loads(outer.get('result') or '{}')
    except ValueError:
        print(r.stdout[-1500:])
        print('the review returned no readable verdict; the build stays blocked.')
        return 2
    os.makedirs(OUT, exist_ok=True)
    stamp = dt.datetime.now().strftime('%Y-%m-%dT%H%M%S')
    rec = dict(found, token=b['token'], blocked_at=b['at'], to_render=b['to_render'],
               causes=b['causes'][:8], model=MODEL, cost_usd=outer.get('total_cost_usd'))
    path = os.path.join(OUT, 'review-%s.json' % stamp)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(rec, fh, indent=1)
    print('PRERENDER GATE REVIEW (%s): %s\n  cause: %s\n  evidence: %s\n  fix: %s\n  approve? %s\n  written to %s'
          % (b['token'], found['verdict'].upper(), found['cause'], found['evidence'], found['fix'] or '-',
             found['approve'], path))
    return 0


def approve(a):
    b = load(BLOCKED)
    if not b:
        print('no build is blocked; there is nothing to approve.')
        return 1
    rv = latest_review(b['token'])
    if not rv and not a.without_review:
        print('no review of cause %s yet. Run `python3 scripts/prerender_gate.py review` first, or '
              'pass --without-review "WHY".' % b['token'])
        return 1
    rec = {'token': b['token'], 'by': a.by, 'reason': a.reason,
           'at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
           'to_render': b['to_render'], 'review': rv, 'without_review': a.without_review}
    tmp = APPROVED + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(rec, fh, indent=1)
    os.replace(tmp, APPROVED)
    print('approved cause %s (%d routes) for one build within 48h. Retry the build, e.g. '
          '`python3 scripts/refresh.py --ship-only`.' % (b['token'], b['to_render']))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('status')
    r = sub.add_parser('review')
    r.add_argument('--dry-run', action='store_true', help='print the prompt; call nothing')
    p = sub.add_parser('approve')
    p.add_argument('--by', required=True)
    p.add_argument('--reason', required=True)
    p.add_argument('--without-review', default='', metavar='WHY')
    a = ap.parse_args()
    return {'status': status, 'review': review, 'approve': approve}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
