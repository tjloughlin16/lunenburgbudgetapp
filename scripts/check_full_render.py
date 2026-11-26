#!/usr/bin/env python3
"""The full-render merge gate: refuse a commit to main that would make the site re-render every page.

    python3 scripts/check_full_render.py --staged            # what is staged now (the pre-commit hook)
    python3 scripts/check_full_render.py --range A..B        # a run of commits (the pre-push hook)
    python3 scripts/check_full_render.py --merge             # MERGE_HEAD against HEAD (pre-merge-commit)
    python3 scripts/check_full_render.py --install           # write the three hooks; they do nothing until armed
    python3 scripts/check_full_render.py --status            # armed or not, and the hooks installed

WHY. TJ, 26 November 2026, after the sixth full render in thirteen days: *"I want to put in a hard
merge block. Any commit that attempts to get merged that causes a full re-render is now considered
blocked, and we need to figure out how to prevent that from now on."*

WHAT A FULL RENDER IS, mechanically. fy28/scripts/prerender.mjs reuses a cached page only while
one key matches every route at once (`global`, line ~564):

    sha256( index.html AS BUILT, from `<html` onward  +  PROBE  +  prerender.mjs's own text )

The built index.html names the hashed bundle (/assets/index-*.js) and stylesheet. The site is
ONE bundle with no code splitting, so anything that changes the bundle's bytes changes `global`
and every page is re-rendered. What changes the bundle:

  - fy28/src/**            all app code, AND the JSON it imports from fy28/src/data/ -- which the
                           refresh rewrites (sources.json, agent-manifest.json). Data is code here.
  - fy28/index.html        but only from `<html` on; the preamble before it is spliced, not keyed
  - prerender.mjs          its own text is in the key (and PROBE lives in it)
  - the build config       vite.config.ts, package.json, package-lock.json, tsconfig*.json

This is a PREDICTION from paths, and it errs one way: a comment-only edit under fy28/src is
refused although esbuild would strip it. It never passes a change that touches the key. Two
things it does not see: Tailwind v4 scans tracked files for class names, so a committed data
file under fy28/public could in principle add CSS; and a dependency resolved differently on
`npm install` without a lockfile change. Both are rare and both are named here rather than
guessed at.

ARMING. Nothing is refused until ops/FULL-RENDER-GATE-ARMED exists -- the hooks check for that
file in shell before starting Python, so an unarmed gate costs a stat. Arming it is TJ's call,
because with one bundle it refuses nearly every code commit and every refresh that rewrites
sources.json (see notes/process/AVOIDING-FULL-RENDERS.md).

OVERRIDE. FULL_RENDER_APPROVED="who and why" in the environment lets one commit or push through,
and is appended to build/full-render-gate/overrides.log. It is for the owner, not for an agent.
"""
import argparse
import datetime
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARMED_FILE = os.path.join('ops', 'FULL-RENDER-GATE-ARMED')
LOG = os.path.join('build', 'full-render-gate', 'overrides.log')

PREFIXES = ('fy28/src/',)
FILES = ('fy28/scripts/prerender.mjs', 'fy28/vite.config.ts', 'fy28/package.json',
         'fy28/package-lock.json', 'fy28/tsconfig.json', 'fy28/tsconfig.app.json',
         'fy28/tsconfig.node.json')
SHELL = 'fy28/index.html'
HOOKS = ('pre-commit', 'pre-merge-commit', 'pre-push')


def git(root, *args, check=True):
    r = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit('git %s: %s' % (' '.join(args), r.stderr.strip()[:300]))
    return r


def blob(root, rev, path):
    """A file's text at a revision; rev None = the index (staged). '' when absent."""
    spec = (':%s' % path) if rev is None else ('%s:%s' % (rev, path))
    r = git(root, 'show', spec, check=False)
    return r.stdout if r.returncode == 0 else ''


def keyed_shell(text):
    """index.html from `<html` on: the part prerender.mjs hashes."""
    at = text.find('<html')
    return text[at:] if at >= 0 else text


def triggers(root, paths, old, new):
    """-> [(path, why)] for each changed path that changes the prerender's global key.
    old/new are revisions; new None means the index."""
    out = []
    for p in sorted(set(paths)):
        if p.startswith(PREFIXES):
            out.append((p, 'compiled into the one bundle'))
        elif p in FILES:
            out.append((p, 'part of the build or of the cache key itself'))
        elif p == SHELL and keyed_shell(blob(root, old, p)) != keyed_shell(blob(root, new, p)):
            out.append((p, 'changed from <html on, which is hashed'))
    return out


def changed(root, old, new):
    if new is None:
        args = ['diff', '--cached', '--name-only', '-z'] + ([old] if old else [])
    else:
        args = ['diff', '--name-only', '-z', old, new]
    return [p for p in git(root, *args).stdout.split('\0') if p]


def armed(root):
    return os.path.exists(os.path.join(root, ARMED_FILE))


def decide(root, found, where):
    """Print, log an override, -> exit code."""
    if not found:
        return 0
    print('\nFULL-RENDER GATE: %s would re-render every page of the site (%d path(s)):' % (where, len(found)))
    for p, why in found[:25]:
        print('    %-60s %s' % (p, why))
    if len(found) > 25:
        print('    ... and %d more' % (len(found) - 25))
    if not armed(root):
        print('  (gate not armed: reported only. Arming is TJ\'s decision -- %s)' % ARMED_FILE)
        return 0
    ok = os.environ.get('FULL_RENDER_APPROVED', '').strip()
    if ok:
        path = os.path.join(root, LOG)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'a', encoding='utf-8') as fh:
            fh.write('%s\t%s\t%s\t%s\n' % (datetime.datetime.now().isoformat(timespec='seconds'), where,
                                            ok, ','.join(p for p, _ in found)))
        print('  ALLOWED by FULL_RENDER_APPROVED: %s (logged to %s)' % (ok, LOG))
        return 0
    print('  REFUSED. See notes/process/AVOIDING-FULL-RENDERS.md for how to land this without a full\n'
          '  render. Only the owner overrides: FULL_RENDER_APPROVED="who and why".')
    return 1


def branch(root):
    return git(root, 'symbolic-ref', '--quiet', '--short', 'HEAD', check=False).stdout.strip()


HOOK = '''#!/bin/sh
# full-render gate (scripts/check_full_render.py). Does nothing unless ops/FULL-RENDER-GATE-ARMED exists.
root="$(git rev-parse --show-toplevel)" || exit 0
[ -e "$root/ops/FULL-RENDER-GATE-ARMED" ] || exit 0
exec /usr/local/opt/python@3.11/bin/python3.11 "$root/scripts/check_full_render.py" --hook %s "$@"
'''


def install(root):
    hooks = git(root, 'rev-parse', '--git-path', 'hooks').stdout.strip()
    hooks = hooks if os.path.isabs(hooks) else os.path.join(root, hooks)
    for h in HOOKS:
        p = os.path.join(hooks, h)
        if os.path.exists(p) and 'full-render gate' not in open(p, encoding='utf-8', errors='replace').read():
            raise SystemExit('%s exists and is not ours; not overwriting it' % p)
        with open(p + '.tmp', 'w', encoding='utf-8') as fh:
            fh.write(HOOK % h)
        os.chmod(p + '.tmp', 0o755)
        os.replace(p + '.tmp', p)
        print('installed %s' % p)


def hook(root, name, argv):
    if name == 'pre-commit':
        if branch(root) != 'main':
            return 0
        head = git(root, 'rev-parse', '--verify', '--quiet', 'HEAD', check=False).stdout.strip() or None
        return decide(root, triggers(root, changed(root, head, None), head, None), 'this commit to main')
    if name == 'pre-merge-commit':
        if branch(root) != 'main':
            return 0
        mh = git(root, 'rev-parse', '--verify', '--quiet', 'MERGE_HEAD', check=False).stdout.strip()
        if not mh:
            return 0
        return decide(root, triggers(root, changed(root, 'HEAD', None), 'HEAD', None), 'this merge into main')
    if name == 'pre-push':
        code = 0
        for line in sys.stdin.read().splitlines():
            local_ref, local_sha, remote_ref, remote_sha = (line.split() + ['', '', '', ''])[:4]
            if remote_ref != 'refs/heads/main' or set(local_sha) == {'0'}:
                continue
            base = remote_sha if set(remote_sha) != {'0'} else None
            if not base:
                continue
            code |= decide(root, triggers(root, changed(root, base, local_sha), base, local_sha),
                           'this push to main (%s..%s)' % (base[:8], local_sha[:8]))
        return code
    return 0


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--staged', action='store_true')
    g.add_argument('--range')
    g.add_argument('--merge', action='store_true')
    g.add_argument('--install', action='store_true')
    g.add_argument('--status', action='store_true')
    g.add_argument('--hook')
    ap.add_argument('--root', default=ROOT)
    a, rest = ap.parse_known_args()
    root = a.root
    if a.install:
        install(root)
        return 0
    if a.status:
        hooks = git(root, 'rev-parse', '--git-path', 'hooks').stdout.strip()
        hooks = hooks if os.path.isabs(hooks) else os.path.join(root, hooks)
        print('armed: %s (%s)' % ('YES' if armed(root) else 'no', ARMED_FILE))
        for h in HOOKS:
            p = os.path.join(hooks, h)
            ours = os.path.exists(p) and 'full-render gate' in open(p, errors='replace').read()
            print('  %-17s %s' % (h, 'installed' if ours else 'not installed'))
        return 0
    if a.hook:
        return hook(root, a.hook, rest)
    if a.staged:
        head = git(root, 'rev-parse', '--verify', '--quiet', 'HEAD', check=False).stdout.strip() or None
        return decide(root, triggers(root, changed(root, head, None), head, None), 'what is staged')
    if a.merge:
        return decide(root, triggers(root, changed(root, 'HEAD', None), 'HEAD', None), 'this merge')
    old, new = a.range.split('..', 1)
    return decide(root, triggers(root, changed(root, old, new), old, new), a.range)


if __name__ == '__main__':
    sys.exit(main())
