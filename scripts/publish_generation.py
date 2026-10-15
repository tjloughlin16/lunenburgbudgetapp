#!/usr/bin/env python3
"""PUBLISH A GENERATED REPORT: its branch onto main, then pushed, built and deployed.

    python3 scripts/publish_generation.py <slug>             # the whole thing
    python3 scripts/publish_generation.py <slug> --no-deploy # onto main and pushed; no build, no deploy
    python3 scripts/publish_generation.py <slug> --check     # would it land cleanly? replay in memory only:
                                                             #   nothing moved, committed or pushed

Started by the Publish button on the dashboard (dashboard_server.py). TJ, 15 October 2026:
*"there needs to be a 'publish' button that commits ... and deploys"* -- and, of the worktrees:
*"make sure we dont hit the same issues as refresh, which means losing work, stepping on
commits, etc"*. Pressing the button IS the person asking for the deploy (CLAUDE.md rule 10).

EVERY GIT STEP IS refresh_git's, so there is one implementation of "never lose or step on
work", not two:

  1. REPLAY, NOT MERGE. The generation's commits are re-applied onto the current main with
     `git merge-tree` (refresh_git._replay), which touches neither the working tree nor the
     index. A conflict stops everything with NOTHING changed, and names the files.
  2. MOVE, OR REFUSE. The person's tree moves onto the new main with a two-tree
     `read-tree -m -u` (refresh_git._move_to), which REFUSES rather than overwrites a file
     holding somebody's uncommitted work. Guarded by the old head: if main moved meanwhile, it
     fails rather than discarding what it moved to.
  3. THE SHARED INDEX FILES ARE REBUILT ON MAIN, from everything on main -- never carried from
     the branch (generate_report.DERIVED) -- under refresh_git's Baseline/settle, so another
     session's uncommitted copy of one is put back and named, never committed for them. Only
     the paths this step wrote are committed (`commit --only`, from a pathspec file).
  4. CHECKED ON MAIN BEFORE ANYTHING LEAVES THIS MACHINE: the generation's own declared checks
     and the registry. A failure stops before the push; the commits stay local, reported.
  5. PUSH WITHOUT FORCE, with bounded retries: if origin/main moved, the local commits are
     replayed onto it and the tree moved -- refusing, again, rather than overwriting.
  6. DEPLOY ONLY A TREE THAT IS WHAT WAS COMMITTED. Refused while any file under fy28/ holds
     somebody else's uncommitted change (the refresh's rule, TJ 9 October 2026): the build
     reads the working tree and would ship it. Then `npm run build:site` (its own lock) and
     `deploy_site.sh` (which refuses a half-built dist), then each page fetched from production.

Nothing here resets, cleans, stashes, checks out, rebases, forces, or deletes a branch or a
worktree; check_refresh_safe.py fails the build if that ever changes. The worktree and the
gen/<slug> branch are KEPT after publishing: a branch is cheap, and it is the record.
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import refresh_git as G  # noqa: E402
import generate_report as GR  # noqa: E402

SITE = 'https://lunenburgbudgetproject.org'
NODE22 = GR.NODE22
LOCK = os.path.join(ROOT, 'build', 'report-generations', 'PUBLISHING')
INDEX_GENERATORS = ['build_topics_index.py', 'build_reports_index.py', 'build_source_index.py',
                    'build_sitemap.py', 'build_site_changes.py']


def now():
    return dt.datetime.now().astimezone().isoformat(timespec='seconds')


def step(g, name, detail='', state='running'):
    g.setdefault('publish', {}).setdefault('steps', []).append(dict(at=now(), step=name, detail=detail[:1500]))
    g['publish']['state'] = state
    GR.save(g)
    print('  %s: %s' % (name, detail[:300]), flush=True)


def stop(g, why, status):
    step(g, 'stopped', why, state='stopped')
    g['status'] = status
    GR.save(g)
    return 1


def env22():
    return dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))


def sh(cmd, cwd=ROOT, timeout=3600):
    r = subprocess.run(['/bin/bash', '-c', cmd], cwd=cwd, capture_output=True, text=True,
                       env=env22(), timeout=timeout)
    return r.returncode, (r.stdout + r.stderr)[-2000:]


def push(g):
    """Local main onto origin/main: fetch, replay if origin moved, push. No force, three tries."""
    for attempt in range(1, G.PUSH_TRIES + 1):
        f = G.git(ROOT, 'fetch', '-q', 'origin', 'main', check=False)
        if f.returncode:
            return False, 'fetch failed: %s' % f.stderr.strip()[:300]
        up = G.git(ROOT, 'rev-parse', 'refs/remotes/origin/main').stdout.strip()
        local = G.head(ROOT)
        if G.git(ROOT, 'merge-base', '--is-ancestor', up, local, check=False).returncode:
            ahead = G.git(ROOT, 'rev-list', '--reverse', '%s..%s' % (up, local)).stdout.split()
            new, conflicted = G._replay(ROOT, ahead, up)
            if conflicted:
                return False, 'origin/main moved and the replay conflicts on: %s' % ', '.join(conflicted[:10])
            ok, why = G._move_to(ROOT, local, new, 'refs/heads/main')
            if not ok:
                return False, 'origin/main moved; moving this tree onto it would touch uncommitted work: %s' % why
            local = new
        p = G.git(ROOT, 'push', '-q', 'origin', '%s:refs/heads/main' % local, check=False)
        if p.returncode == 0:
            return True, 'pushed %s (attempt %d)' % (local[:9], attempt)
    return False, 'push rejected %d times; main keeps moving' % G.PUSH_TRIES


def verify_live(pages):
    out = []
    for p in pages:
        path = p['path'] if p['path'].startswith('/') else '/' + p['path']
        try:
            with urllib.request.urlopen(urllib.request.Request(SITE + path, headers={'User-Agent': 'publish-check'}), timeout=30) as r:
                body = r.read().decode('utf-8', 'replace')
                out.append(dict(path=path, status=r.status, title_found=p['title'] in body))
        except Exception as e:  # noqa: BLE001 -- recorded, not raised: the deploy happened
            out.append(dict(path=path, status=None, error=str(e)[:200]))
    return out


def publish(slug, deploy=True):
    g = GR.load(slug)
    if not g:
        raise SystemExit('publish_generation: no generation %r' % slug)
    if g['status'] != 'draft-ready':
        raise SystemExit('publish_generation: %s is %s; only a draft-ready generation whose checks '
                         'pass is published' % (slug, g['status']))
    if not all(c['exit'] == 0 for c in g.get('checks') or []):
        raise SystemExit('publish_generation: %s has failing checks' % slug)
    os.makedirs(GR.LOGS, exist_ok=True)
    if os.path.exists(LOCK):
        raise SystemExit('publish_generation: a publish is running (%s)' % open(LOCK).read().strip())
    open(LOCK, 'w').write('%s %s' % (slug, now()))
    try:
        g['status'] = 'publishing'
        g['publish'] = dict(started=now(), steps=[], state='running')
        GR.save(g)
        if G.branch(ROOT) != 'main':
            return stop(g, 'the tree at %s is on %r, not main; nothing changed' % (ROOT, G.branch(ROOT)), 'draft-ready')
        if G.operation_in_progress(ROOT):
            return stop(g, 'a %s is half-finished in the tree; nothing changed' % G.operation_in_progress(ROOT), 'draft-ready')
        br = GR.branch(slug)
        main0 = G.head(ROOT)
        base = G.git(ROOT, 'merge-base', main0, br).stdout.strip()
        commits = G.git(ROOT, 'rev-list', '--reverse', '%s..%s' % (base, br)).stdout.split()
        if not commits:
            return stop(g, 'the branch has no commits to publish', 'draft-ready')
        # 1. replay
        new, conflicted = G._replay(ROOT, commits, main0)
        if conflicted:
            return stop(g, 'main has moved and the generation conflicts with it on: %s. Nothing changed; '
                           'Continue the generation to bring it up to date.' % ', '.join(conflicted[:12]), 'draft-ready')
        step(g, 'replayed', '%d commit(s) onto main at %s' % (len(commits), main0[:9]))
        # 2. move, or refuse
        ok, why = G._move_to(ROOT, main0, new, 'refs/heads/main')
        if not ok:
            return stop(g, 'moving the tree onto the new main would overwrite uncommitted work, so nothing '
                           'moved: %s' % why, 'draft-ready')
        step(g, 'on main', 'main is now %s' % new[:9])
        # 3. the shared index files, rebuilt from main
        base_line = G.Baseline.take(ROOT)
        for gen in INDEX_GENERATORS:
            code, out = sh('python3 scripts/%s' % gen)
            if code:
                step(g, 'index generator failed', '%s: %s' % (gen, out[-600:]))
        ours, blocked, _ = G.settle(ROOT, base_line)
        sha = G.commit(ROOT, ours, 'Published generation %s: the shared index files, rebuilt on main' % slug)
        step(g, 'index files', 'committed %s (%d paths)%s' % (sha[:9] if sha else 'nothing', len(ours),
             ('; NOT refreshed, held by somebody else: %s' % ', '.join(blocked[:8])) if blocked else ''))
        # 4. checks on main
        fails = []
        for cmd in ['python3 scripts/topics.py', 'python3 scripts/build_topics_index.py --check'] + \
                [c for c in (g.get('result') or {}).get('checks') or []][:12]:
            code, out = sh(cmd, timeout=1200)
            if code:
                fails.append('%s -> %s' % (cmd, out[-300:]))
        if fails:
            return stop(g, 'checks failed on main, so nothing was pushed or deployed (the commits are on '
                           'local main): %s' % ' | '.join(fails), 'publish-failed')
        step(g, 'checks', 'all pass on main')
        # 5. push
        ok, why = push(g)
        if not ok:
            return stop(g, 'not pushed: %s. The commits are on local main.' % why, 'publish-failed')
        step(g, 'pushed', why)
        g['published_commit'] = G.head(ROOT)
        if not deploy:
            g['status'] = 'published'
            step(g, 'done', 'pushed; not deployed (--no-deploy)', state='done')
            return 0
        # 6. deploy
        site_dirty = [p for p in G.dirty_paths(ROOT) if p.startswith('fy28/')]
        if site_dirty:
            return stop(g, 'pushed, but NOT deployed: fy28/ holds uncommitted changes that are not this '
                           'report\'s and the build would ship them: %s' % ', '.join(site_dirty[:10]), 'published-not-deployed')
        step(g, 'building', 'npm run build:site -- about 25 minutes for a code change')
        code, out = sh('cd fy28 && npm run build:site', timeout=5400)
        if code:
            return stop(g, 'pushed, but the site build failed, so nothing was deployed: %s' % out[-800:], 'published-not-deployed')
        code, out = sh('bash scripts/deploy_site.sh', timeout=1800)
        if code:
            return stop(g, 'pushed and built, but the deploy refused or failed: %s' % out[-800:], 'published-not-deployed')
        step(g, 'deployed', out[-300:])
        g['live'] = verify_live((g.get('result') or {}).get('pages') or [])
        g['status'] = 'published'
        step(g, 'done', 'live: %s' % ', '.join('%s %s' % (x['path'], x.get('status')) for x in g['live']), state='done')
        return 0
    finally:
        if os.path.exists(LOCK):
            os.remove(LOCK)


def preflight(slug):
    """The replay, done in memory (merge-tree writes objects, never the tree or the index), and
    what the deploy step would refuse on. -> dict; also recorded on the generation."""
    br = GR.branch(slug)
    main0 = G.head(ROOT)
    base = G.git(ROOT, 'merge-base', main0, br).stdout.strip()
    commits = G.git(ROOT, 'rev-list', '--reverse', '%s..%s' % (base, br)).stdout.split()
    _new, conflicted = G._replay(ROOT, commits, main0) if commits else (None, [])
    files = set(G.git(ROOT, 'diff', '--name-only', '%s..%s' % (base, br)).stdout.split())
    dirty = set(G.dirty_paths(ROOT))
    out = dict(at=now(), main=main0[:9], commits=len(commits), conflicts=conflicted,
               dirty_overlap=sorted(files & dirty), main_branch=G.branch(ROOT) == 'main',
               site_dirty=[p for p in dirty if p.startswith('fy28/')][:20])
    out['clean'] = bool(commits) and not conflicted and not out['dirty_overlap'] and out['main_branch']
    g = GR.load(slug)
    if g:
        g['preflight'] = out
        GR.save(g)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('slug')
    ap.add_argument('--no-deploy', action='store_true')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.check:
        r = preflight(a.slug)
        print(json.dumps(r, indent=1))
        return 0 if r['clean'] else 1
    return publish(a.slug, deploy=not a.no_deploy)


if __name__ == '__main__':
    sys.exit(main())
