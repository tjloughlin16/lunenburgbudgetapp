#!/usr/bin/env python3
"""The refresh's whole relationship with git: what it may stage, how it commits, how it
reaches main. ADDITIVE ONLY, in the working tree a person is using, on whatever branch.

    import refresh_git as G
    base = G.Baseline.take(ROOT)          # FIRST, before the run writes anything
    ...the run...
    ours, blocked, appended = G.settle(ROOT, base)   # the run's; others' put back
    sha = G.commit(ROOT, ours, message)   # only those paths, nothing anybody else staged
    status, detail = G.publish(ROOT)      # onto origin/main, by replay, bounded retries

    python3 scripts/refresh_git.py --status   # what a run starting now would treat as
                                              #   somebody else's uncommitted work

WHY THIS EXISTS. TJ, 8 October 2026: *"refresh should be always additive"*, *"refresh
should work in whatever branch we're currently on"*, *"this shouldnt have ANY chance of a
destructive path"*, and *"if we have a page with edits, and the refresh would impact THAT
page, just count that page as not yet refreshable, but dont fail everything."* The old
refresh ran in a second checkout that it RESET each morning, refused to start unless that
checkout was pristine, committed with `git add -A`, and on a moved main pushed to a side
branch. It was blocked 5, 6 and 7 October by the first rule and split across a side branch
on the 8th by the last. See notes/HANDOFF-REFRESH-ADDITIVE.md.

THREE RULES, AND THE CODE BELOW IS ONLY THEIR MECHANICS.

  1. SOMEBODY ELSE'S UNCOMMITTED WORK IS NEVER STAGED AND NEVER LOST. Whatever is dirty
     when the run starts belongs to another session. It is copied into build/ before the
     run writes a byte, and a file the run then overwrote is PUT BACK from that copy and
     reported as not yet refreshable. The run's version is kept beside it in build/, so
     the operation loses nothing in either direction.
  2. ONLY THE RUN'S OWN FILES ARE COMMITTED. Never `add -A`: a pathspec file of exactly
     the paths the run changed, committed with `--only`, so even an entry another session
     has STAGED stays staged and out of the commit.
  3. MAIN IS REACHED BY REPLAY, NEVER BY A SIDE BRANCH OR A FORCE. If origin/main moved
     during the run, the refresh's commits are replayed onto it with `git merge-tree` --
     which needs no clean working tree, unlike `git rebase`, which refuses outright while
     another session has anything dirty -- and the working tree is moved with a two-tree
     `read-tree -m -u`, which REFUSES rather than overwrites if any file it would touch
     holds uncommitted work. A refusal is reported and the commit stays local, to be
     replayed by the next run.

WHAT THIS DELIBERATELY DOES NOT CALL: reset, clean, checkout, restore, stash, rebase, rm,
branch -f/-D, push --force. scripts/check_refresh_safe.py fails the build if any of them
appears here, in refresh.py or in daily_refresh.sh.

Python 3.9-safe on purpose: refresh.py imports this, and the dashboard and the backlog
scripts import refresh.py under /usr/bin/python3.
"""
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Every commit the refresh makes carries this trailer, so a later run can tell ITS OWN
# unpushed commits (safe to replay onto main) from a person's (never pushed for them).
TRAILER = 'Refresh-Run:'
PUSH_TRIES = 3


def git(root, *args, check=True, env=None, input=None):
    r = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True,
                       env=env, input=input)
    if check and r.returncode != 0:
        raise GitError('git %s failed (%d): %s' % (' '.join(args[:3]), r.returncode,
                                                    (r.stderr or r.stdout).strip()[:400]))
    return r


class GitError(Exception):
    pass


def _sha(path):
    """sha256 of a working-tree file, or None if it does not exist."""
    if not os.path.lexists(path):
        return None
    if os.path.islink(path):
        return 'link:' + os.readlink(path)
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def dirty_paths(root):
    """Every path git reports as not matching HEAD: modified, staged, deleted, untracked
    (each untracked FILE, not its directory), both sides of a rename. Ignored files are not
    dirty -- they are not anybody's commit to make."""
    out = git(root, 'status', '--porcelain=v1', '-z', '--untracked-files=all').stdout
    paths, parts, i = [], out.split('\0'), 0
    while i < len(parts):
        entry = parts[i]
        i += 1
        if len(entry) < 4:
            continue
        xy, path = entry[:2], entry[3:]
        if path.startswith('build/'):
            # build/ is gitignored here, and it is where this module keeps its own copies;
            # said again in code so a tree without that ignore line cannot commit them.
            if xy[0] in 'RC':
                i += 1
            continue
        paths.append(path)
        if xy[0] in 'RC':                 # -z puts a rename's ORIGINAL path next
            if i < len(parts) and parts[i]:
                paths.append(parts[i])
            i += 1
    return sorted(set(paths))


def head(root):
    r = git(root, 'rev-parse', '--verify', '-q', 'HEAD', check=False)
    return r.stdout.strip()


def branch(root):
    """The checked-out branch, or '' on a detached HEAD."""
    r = git(root, 'symbolic-ref', '-q', '--short', 'HEAD', check=False)
    return r.stdout.strip()


def operation_in_progress(root):
    """A merge, rebase, cherry-pick or revert somebody has half-finished in this tree, or
    ''. The refresh commits nothing on top of one: it would be committing into the middle
    of another person's operation."""
    for name in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'rebase-merge',
                 'rebase-apply'):
        p = git(root, 'rev-parse', '--git-path', name).stdout.strip()
        if os.path.exists(os.path.join(root, p)):
            return name
    return ''


class Baseline(object):
    """What was dirty when the run started, and a copy of every byte of it.

    The copy is what makes `put it back` possible without trusting git for content git
    never held: an untracked file, or an edit nobody staged, exists nowhere but the
    working tree.
    """

    def __init__(self, root, head, branch, dirty, store):
        self.root, self.head, self.branch, self.dirty, self.store = root, head, branch, dirty, store

    @classmethod
    def take(cls, root, stamp=None):
        stamp = stamp or dt.datetime.now().strftime('%Y-%m-%dT%H%M%S')
        store = os.path.join(root, 'build', 'refresh-baseline', stamp)
        dirty = {}
        for p in dirty_paths(root):
            src = os.path.join(root, p)
            h = _sha(src)
            dirty[p] = h
            if h is not None and not os.path.isdir(src):
                dst = os.path.join(store, 'files', p)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst, follow_symlinks=False)
        os.makedirs(store, exist_ok=True)
        b = cls(root, head(root), branch(root), dirty, store)
        with open(os.path.join(store, 'baseline.json'), 'w', encoding='utf-8') as fh:
            json.dump({'head': b.head, 'branch': b.branch, 'dirty': dirty}, fh, indent=1)
        return b


def _atomic_copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + '.refresh-restore.tmp'
    shutil.copy2(src, tmp, follow_symlinks=False)
    os.replace(tmp, dst)


def settle(root, base):
    """-> (ours, blocked, appended). `ours` is every path the run left dirty that was clean when it
    started -- the only paths it may stage. `blocked` is every path that held somebody
    else's uncommitted work AND changed during the run: its pre-run content is put back,
    the run's version is kept in build/refresh-conflicts/, and it is reported as not yet
    refreshable rather than failing anything. `appended` is an append-only log (union in
    .gitattributes) that held uncommitted rows and to which the run only added: left as it
    is, unstaged, everybody's rows intact.

    WHAT THIS CANNOT TELL APART, said rather than hidden: a file that was clean at the
    start and written during the run by ANOTHER process (the paced minutes run, say) looks
    exactly like one the refresh wrote, and is committed with it. Those writers produce
    the same kind of additive output the refresh does, and it would be committed anyway;
    the case that matters -- an edit somebody had in progress -- is the pre-dirty one,
    and that one is protected.
    """
    now = set(dirty_paths(root))
    ours = sorted(p for p in now if p not in base.dirty)
    blocked, appended = [], []
    keep = os.path.join(base.store, 'conflicts')
    moved_on = head(root) != base.head
    for p, was in sorted(base.dirty.items()):
        full = os.path.join(root, p)
        cur = _sha(full)
        if cur == was:
            continue
        if p not in now and moved_on:
            # It is clean against a HEAD that moved: its owner COMMITTED it during the run.
            # Putting the pre-commit copy back would undo their commit in the tree.
            continue
        if was is not None and cur is not None and _appended(root, p, base):
            # AN APPEND-ONLY LOG THAT ALREADY HELD SOMEBODY'S UNCOMMITTED ROWS, and the run
            # only ADDED rows after them. agentic-spend.csv is that file most mornings: the
            # paced minutes run appends to it all day. Their rows are still there, byte for
            # byte, so putting the old copy back would only throw away the run's rows. It
            # is left as it is and NOT staged -- committing it would commit their rows --
            # and goes in with whoever commits that file next.
            appended.append(p)
            continue
        # The run (or its owner) changed it. Keep the version on disk now, then put the
        # pre-run version back. Neither is lost: both are in build/.
        if cur is not None and not os.path.isdir(full):
            dst = os.path.join(keep, p)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if was is None:
                # It did not exist before the run (its owner had deleted it). MOVE the
                # recreated file into build/ -- the tree goes back to their deletion and
                # the bytes are kept, which a delete would not do.
                os.replace(full, dst)
            else:
                shutil.copy2(full, dst, follow_symlinks=False)
        if was is not None:
            _atomic_copy(os.path.join(base.store, 'files', p), full)
        blocked.append(p)
    return ours, blocked, appended


def _appended(root, rel, base):
    """Is `rel` declared append-only (merge=union in .gitattributes) and is its pre-run
    content an exact prefix of what is on disk now? Only then is leaving it alone safe."""
    attr = git(root, 'check-attr', 'merge', '--', rel, check=False).stdout.strip()
    if not attr.endswith(': union'):
        return False
    with open(os.path.join(base.store, 'files', rel), 'rb') as fh:
        before = fh.read()
    with open(os.path.join(root, rel), 'rb') as fh:
        after = fh.read()
    return len(after) > len(before) and after.startswith(before)


def _pathspec_file(root, paths):
    d = os.path.join(root, 'build', 'refresh-baseline')
    os.makedirs(d, exist_ok=True)
    f = os.path.join(d, 'pathspec-%d' % os.getpid())
    with open(f, 'w', encoding='utf-8') as fh:
        fh.write('\0'.join(paths))
    return f


def commit(root, paths, message):
    """Commit exactly `paths`, and nothing anybody else staged. -> the new sha, or None.

    `add` then `commit --only`, both from a pathspec FILE: `--only` is what keeps another
    session's staged entries out of this commit, and a file rather than argv because a
    full run can change thousands of paths."""
    if not paths:
        return None
    if not branch(root) or operation_in_progress(root):
        return None
    spec = _pathspec_file(root, paths)
    # LITERAL, because a path is a name and not a pattern: a file called `a*b.csv` must
    # not stage everything that globs to it.
    L = '--literal-pathspecs'
    git(root, L, 'add', '--pathspec-from-file=' + spec, '--pathspec-file-nul')
    if git(root, L, 'diff', '--cached', '--quiet', '--pathspec-from-file=' + spec,
           '--pathspec-file-nul', check=False).returncode == 0:
        return None
    msg = message.rstrip() + '\n\n%s %s\n' % (TRAILER, dt.date.today().isoformat())
    git(root, L, 'commit', '-q', '--only', '--pathspec-from-file=' + spec,
        '--pathspec-file-nul', '-F', '-', input=msg)
    return head(root)


def _is_refresh_commit(root, sha):
    body = git(root, 'log', '-1', '--format=%B', sha).stdout
    return TRAILER in body


def _replay(root, commits, onto):
    """Each commit in `commits`, oldest first, re-applied onto `onto` with merge-tree.
    -> (new tip, conflicted paths). Nothing in the working tree or the index is touched.
    `.gitattributes` is honoured, so a union-merged log cannot conflict."""
    tip = onto
    for c in commits:
        parent = git(root, 'rev-parse', c + '^').stdout.strip()
        r = git(root, 'merge-tree', '--write-tree', '--name-only', '--messages',
                '--merge-base=' + parent, tip, c, check=False)
        lines = r.stdout.splitlines()
        if r.returncode == 1:
            conflicted = []
            for ln in lines[1:]:
                if not ln.strip():
                    break
                conflicted.append(ln.strip())
            return None, conflicted or ['(merge-tree reported a conflict)']
        if r.returncode != 0:
            raise GitError('merge-tree failed: %s' % (r.stderr or r.stdout)[:400])
        tree = lines[0].strip()
        if tree == git(root, 'rev-parse', tip + '^{tree}').stdout.strip():
            continue                       # already upstream: nothing left to replay
        msg = git(root, 'log', '-1', '--format=%B', c).stdout
        env = dict(os.environ)
        for k, f in (('GIT_AUTHOR_NAME', '%an'), ('GIT_AUTHOR_EMAIL', '%ae'),
                     ('GIT_AUTHOR_DATE', '%aD')):
            env[k] = git(root, 'log', '-1', '--format=' + f, c).stdout.strip()
        tip = git(root, 'commit-tree', tree, '-p', tip, '-F', '-', env=env,
                  input=msg).stdout.strip()
    return tip, []


def _move_to(root, old, new, ref):
    """Move the checked-out branch from `old` to `new`, updating the index and the working
    tree for the paths that differ -- and REFUSING, with nothing changed, if any of those
    paths holds uncommitted work or an untracked file would be overwritten. That refusal
    is what `read-tree -m -u` does with two trees; it is the same safety `git merge` gives
    a dirty tree, without needing a merge commit."""
    if old == new:
        return True, ''
    r = git(root, 'read-tree', '-m', '-u', old, new, check=False)
    if r.returncode != 0:
        return False, (r.stderr or r.stdout).strip()[:600]
    # Guarded by the old value: if anything moved the branch meanwhile, this fails rather
    # than discarding what it moved to.
    git(root, 'update-ref', '-m', 'refresh: replay onto origin/main', ref, new, old)
    return True, ''


def publish(root, remote='origin', target='main', tries=PUSH_TRIES):
    """Put this branch's refresh commits on origin/main. -> (status, detail).

    status is one of 'pushed', 'nothing', 'local-only', 'not-main', 'conflict', 'refused',
    'failed'. Never a side branch, never a force: a commit that cannot reach main stays a
    local commit, and the next run tries again.
    """
    b = branch(root)
    if b != target:
        return 'not-main', 'on branch %r: committed locally, not pushed' % (b or 'detached HEAD')
    ref = 'refs/heads/' + b
    for attempt in range(1, tries + 1):
        f = git(root, 'fetch', '-q', remote, target, check=False)
        if f.returncode != 0:
            return 'failed', 'fetch failed: %s' % (f.stderr or '').strip()[:300]
        upstream = git(root, 'rev-parse', 'refs/remotes/%s/%s' % (remote, target)).stdout.strip()
        local = head(root)
        ahead = git(root, 'rev-list', '--reverse', '%s..%s' % (upstream, local)).stdout.split()
        if not ahead:
            return 'nothing', 'already at %s/%s' % (remote, target)
        foreign = [c for c in ahead if not _is_refresh_commit(root, c)]
        if foreign:
            # A PERSON'S UNPUSHED COMMITS ARE NOT OURS TO PUBLISH. Pushing HEAD would carry
            # them to main with ours; replaying ours alone would leave them behind locally.
            return 'local-only', ('%d local commit(s) on %s are not the refresh’s and not '
                                  'on %s/%s; the refresh commit stays local until they are '
                                  'pushed' % (len(foreign), b, remote, target))
        base = git(root, 'merge-base', upstream, local).stdout.strip()
        if base != upstream:
            new, conflicted = _replay(root, ahead, upstream)
            if conflicted:
                return 'conflict', ('main moved and the replay conflicts on: %s. The refresh '
                                    'commit stays local' % ', '.join(conflicted[:10]))
            ok, why = _move_to(root, local, new, ref)
            if not ok:
                return 'refused', ('main moved and moving this tree onto it would touch '
                                   'uncommitted work, so nothing was moved: %s' % why)
            local = new
            if local == upstream:
                return 'nothing', 'everything the refresh committed was already on main'
        p = git(root, 'push', '-q', remote, '%s:refs/heads/%s' % (local, target), check=False)
        if p.returncode == 0:
            return 'pushed', 'pushed %s to %s/%s (attempt %d)' % (local[:8], remote, target, attempt)
        # Rejected: main moved between the fetch and the push. Go round again.
    return 'failed', 'push rejected %d times; main keeps moving. The commit is local' % tries


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--status', action='store_true')
    a = ap.parse_args(argv)
    d = dirty_paths(ROOT)
    print('branch %s at %s; %d path(s) are somebody else’s uncommitted work to a run '
          'starting now%s' % (branch(ROOT) or '(detached)', head(ROOT)[:8], len(d),
                              ('; ' + operation_in_progress(ROOT) + ' in progress')
                              if operation_in_progress(ROOT) else ''))
    for p in d[:40]:
        print('  ' + p)
    if len(d) > 40:
        print('  ... and %d more' % (len(d) - 40))
    return 0


if __name__ == '__main__':
    sys.exit(main())
