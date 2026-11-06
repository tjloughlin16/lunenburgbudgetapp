#!/usr/bin/env python3
"""How a refresh gets its work onto the site: committed, pushed, built, deployed, verified.

    python3 scripts/refresh_ship.py --plan     # read-only: what a run starting now would do
    python3 scripts/refresh_ship.py --verify   # read-only: does production serve fy28/dist?

TJ, 5 November 2026: *"we need to make sure everything is committed and deployed after every
refresh."* From 30 September to 5 November 2026 every run recorded deployed=no. Three guards
took turns: an output that did not reproduce, a local commit that was not the refresh's, and a
dirty file under fy28/. Each protected something real, and each answered by withholding the
whole site and exiting 0. What replaces each one, so that no protection is simply dropped:

  guard                       what it protected             what protects it now
  --------------------------  ----------------------------  --------------------------------
  no dirty file under fy28/   uncommitted work reaching     the build runs on an EXPORT of the
                              production                    pushed commit, so nothing that is
                                                            uncommitted can be in it at all
  HEAD == origin/main         the build being main's own    the export IS origin/main's commit
                              commit
  a person's unpushed         a push nobody decided on      a live genlock prohibition naming
  commits stay local                                        push or deploy stops the run; only
                                                            main, by explicit refspec, ever moves
  every generator it ran      a site that disagrees with    the same check, after one repair
  reproduces                  its own data                  (rebuild, commit); what still fails
                                                            stops the deploy, by name
  on branch main              a preview alias               unchanged

THE PACED MEETING RUN WRITES INTO THIS TREE ALL DAY. What it wrote before a refresh started
looked like somebody else's work to refresh_git.Baseline, so it was never committed: about
1,250 files had piled up by 5 November 2026. So:

  * ITS OUTPUT IS A DECLARED SET (MEETING_OUTPUTS), committed at the top of a run.
  * ONLY UNDER ITS OWN LOCK. process_meeting.py already has a protocol for a batch to take the
    lock from the paced run: it finishes the meeting in flight and waits. The refresh takes
    the lock the same way, so no commit ever reads a meeting half written. A kernel flock and
    a pid in the request file mean a refresh that dies hands it straight back.
  * THE PAUSE COVERS THE REBUILD, THE BUILD AND THE LAST COMMIT, so the payloads, the commit
    and the check all describe one set of meetings. A step in flight is never killed.

WHAT IS NOT DECLARED IS NOT SWEPT. refresh_git.settle cannot tell a file the refresh wrote from
one a session started editing during the run, and in the last sixty runs it committed ten of
scripts/ that way. split_ours holds back anything hand-written and anything a genlock claim
covers; they stay dirty, and the run says so.

ARMED BY A FILE. ops/REFRESH-SHIP-ARMED exists -> a run ships. Absent -> it ingests and commits
as it always has and deploys nothing. launchd runs scripts/daily_refresh.sh from this working
tree, so an edit here is live at the next 07:00 whether or not it was ever pushed; the file is
what stops an unproved path from pushing and deploying by itself.

Python 3.9-safe, like refresh_git.py: refresh.py imports this.
"""
import fcntl
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ARMED_FILE = os.path.join('ops', 'REFRESH-SHIP-ARMED')
SITE = 'https://lunenburgbudgetproject.org'
# The custom domain answers 403 to anything without a browser's user agent.
BROWSER = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 Safari/605.1.15'
MARKER = os.path.join('data', 'ship.json')

# WHAT THE PACED MEETING RUN WRITES, and nothing else. Read off the scripts it runs
# (write_recording_minutes, extract_official_votes, reconcile_minutes) and checked against
# every file modified while it ran alone on 5 November 2026. A prefix ends in `/`.
MEETING_OUTPUTS = ('sources/data/official-votes/', 'sources/data/recording-minutes/',
                   'sources/data/budget-state/', 'sources/data/agentic-spend.csv',
                   'fy28/public/docs/data/agentic-spend.csv')

# HAND-WRITTEN, so never committed by a refresh: a file here that changed during a run is a
# session's half-finished work. Written as prefixes, with the generated files inside them
# named below; a generated file wrongly held back stays dirty and is named in the run's
# notes, which costs a day, and a hand edit wrongly swept reaches production by itself.
AUTHORED = ('scripts/', 'ops/', 'notes/', '.claude/', 'fy28/src/', 'fy28/scripts/',
            'fy28/functions/', 'fy28/sql/', 'fy28/schema/', 'CLAUDE.md', '.gitignore',
            '.gitattributes', 'fy28/package.json', 'fy28/package-lock.json',
            'fy28/vite.config.ts')
GENERATED_INSIDE = ('fy28/src/data/', 'fy28/functions/api/_tablesizes.js', 'notes/generated/',
                    'notes/reference/')

# A LIVE PROHIBITION IS A HOLD WHEN IT NAMES A PUSH OR A DEPLOY. `Never git push --mirror` is
# about a command the refresh does not use, so it does not stop the run. Erring the other way
# costs a loud morning; a hold missed puts something on GitHub that cannot be taken back.
HOLD_WORDS = re.compile(r'\b(push|pushed|pushing|deploy|deployed|deploying)\b', re.I)
NOT_A_HOLD = re.compile(r'push\s+--mirror', re.I)


def armed(root=ROOT):
    return os.path.exists(os.path.join(root, ARMED_FILE))


# ---------------------------------------------------------------------- the meeting run
class MeetingPause(object):
    """Hold the paced meeting run between meetings, with process_meeting.py's own protocol:
    build/process-meeting.YIELD names a live pid, the paced run finishes its meeting in flight
    and releases the flock, and takes it back when the request is gone. Release is in that
    order too, flock first, as process_meeting.py's own batch does it."""

    def __init__(self, root=ROOT, wait_s=25 * 60, poll_s=5):
        self.root = root
        self.lock = os.path.join(root, 'build', 'process-meeting.lock')
        self.request = os.path.join(root, 'build', 'process-meeting.YIELD')
        self.wait_s, self.poll_s = wait_s, poll_s
        self.fh, self.asked = None, False

    @property
    def held(self):
        return self.fh is not None

    def _ask(self):
        # Another batch already waiting is left alone: its pid stays in the file, and this
        # asks again once it has gone.
        if os.path.exists(self.request):
            return
        tmp = '%s.%d.tmp' % (self.request, os.getpid())
        with open(tmp, 'w') as fh:
            fh.write('%d\n' % os.getpid())
        os.replace(tmp, self.request)
        self.asked = True

    def acquire(self):
        """-> True once the meeting run is between meetings and cannot start another."""
        if self.fh is not None:
            return True
        os.makedirs(os.path.dirname(self.lock), exist_ok=True)
        fh = open(self.lock, 'a+')
        t0 = time.monotonic()
        while True:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() - t0 > self.wait_s:
                    self._withdraw()
                    fh.close()
                    return False
                self._ask()
                time.sleep(self.poll_s)
        fh.seek(0)
        fh.truncate()
        fh.write('%d refresh\n' % os.getpid())
        fh.flush()
        self.fh = fh
        return True

    def _withdraw(self):
        if not self.asked:
            return
        self.asked = False
        try:
            with open(self.request) as fh:
                mine = fh.read().split()[:1] == [str(os.getpid())]
            if mine:
                os.remove(os.path.join(self.root, 'build', 'process-meeting.YIELD'))
        except OSError:
            pass

    def release(self):
        if self.fh is not None:
            fcntl.flock(self.fh, fcntl.LOCK_UN)
            self.fh.close()
            self.fh = None
        self._withdraw()


def is_meeting_output(path):
    return any(path == m or (m.endswith('/') and path.startswith(m)) for m in MEETING_OUTPUTS)


def _under(path, prefix):
    prefix = prefix.rstrip('/')
    return path == prefix or path.startswith(prefix + '/')


def is_authored(path):
    if any(_under(path, g) for g in GENERATED_INSIDE):
        return False
    return any(_under(path, a) for a in AUTHORED)


def claimed_paths(root=ROOT):
    """Every path a genlock claim covers: `T-XXXXX  until 07:56Z  a/b, c/d`. A claim is a
    declaration that somebody is working there, so a refresh does not commit under it."""
    try:
        r = subprocess.run(['genlock', 'claims'], cwd=root, capture_output=True, text=True,
                           timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode:
        return None
    out = []
    for line in r.stdout.splitlines():
        m = re.match(r'\s*\*?\s*T-\S+\s+until\s+\S+\s+(.*)$', line)
        if m:
            out.extend(p.strip() for p in m.group(1).split(',') if p.strip())
    return out


def split_ours(paths, claims=(), exclude_meeting=False):
    """-> (commit these, hold these back)."""
    keep, held = [], []
    for p in paths:
        if is_authored(p) or any(_under(p, c) for c in (claims or ())) \
                or (exclude_meeting and is_meeting_output(p)):
            held.append(p)
        else:
            keep.append(p)
    return keep, held


def adopt_meeting_output(root, G):
    """Commit what the paced run wrote since the last refresh, under its lock, BEFORE the
    baseline -- or the baseline calls it somebody else's and it is never committed.
    -> (commit sha or None, files, why it did not happen or '')."""
    pause = MeetingPause(root)
    if G.operation_in_progress(root):
        return None, 0, 'a git operation is in progress'
    if not pause.acquire():
        return None, 0, 'the meeting run did not yield in %d minutes' % (pause.wait_s // 60)
    try:
        claims = claimed_paths(root) or ()
        mine = [p for p in G.dirty_paths(root) if is_meeting_output(p)]
        mine, _ = split_ours(mine, claims)
        if not mine:
            return None, 0, ''
        sha = G.commit(root, mine, 'Meeting run output up to this refresh\n\nWritten by '
                       'scripts/process_meeting.py; committed by scripts/refresh.py under the '
                       "meeting run's own lock: %d file(s)." % len(mine))
        return sha, len(mine), ''
    finally:
        pause.release()


def push_holds(root=ROOT):
    """-> the live prohibitions that stop a push. Raises OSError when they cannot be read: a
    push that cannot be undone does not go ahead on an unread list."""
    r = subprocess.run(['genlock', 'orient'], cwd=root, capture_output=True, text=True,
                       timeout=120)
    if r.returncode:
        raise OSError('genlock orient exited %d' % r.returncode)
    out = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith('DO NOT:') and HOLD_WORDS.search(line) and not NOT_A_HOLD.search(line):
            out.append(line[len('DO NOT:'):].strip())
    return out


# ---------------------------------------------------------------------- the clean-room build
def export_commit(root, sha):
    """fy28/ exactly as `sha` holds it, in build/ship/tree. Nothing uncommitted can be in it.

    `git archive`, not a worktree: no second HEAD, no index and nothing to prune. Beside it,
    only what git deliberately does not carry: node_modules and the prerender's reuse cache
    (keyed on content, so sharing it is safe), and the published files that .gitignore keeps
    out of the repository, hard-linked. Vite copies those out; it never writes to them."""
    tree = os.path.join(root, 'build', 'ship', 'tree')
    if os.path.lexists(tree):
        shutil.rmtree(tree)
    os.makedirs(tree)
    # A REPOSITORY OF ITS OWN, WITH ITS .gitignore, because the CSS depends on it. Tailwind finds
    # class names by scanning the project and skips what git ignores. Exported bare it also read
    # the data files, and the same commit built 89,655 bytes of CSS against 62,203 (6 November 2026).
    want = ['fy28', '.gitignore']
    # The prerender reads this one file from outside fy28/, and copes if it is not there.
    if subprocess.run(['git', 'cat-file', '-e', '%s:sources/analyses/UNLISTED' % sha], cwd=root,
                      capture_output=True).returncode == 0:
        want.append('sources/analyses/UNLISTED')
    a = subprocess.Popen(['git', 'archive', '--format=tar', sha] + want, cwd=root,
                         stdout=subprocess.PIPE)
    t = subprocess.run(['tar', '-xf', '-', '-C', tree], stdin=a.stdout, capture_output=True, text=True)
    a.stdout.close()
    if a.wait() or t.returncode:
        raise OSError('could not export %s: %s' % (sha[:8], (t.stderr or 'git archive failed')[:300]))
    subprocess.run(['git', 'init', '-q', tree], capture_output=True, check=True)
    app, here = os.path.join(tree, 'fy28'), os.path.join(root, 'fy28')
    for name in ('node_modules', '.prerender-cache', '.wrangler'):
        if os.path.exists(os.path.join(here, name)):
            os.symlink(os.path.join(here, name), os.path.join(app, name))
    ignored = subprocess.run(['git', 'ls-files', '-z', '--others', '--ignored', '--exclude-standard',
                              'fy28/public'], cwd=root, capture_output=True, text=True).stdout
    for rel in ignored.split('\0'):
        if not rel or os.path.basename(rel) == '.DS_Store':
            continue
        dst = os.path.join(tree, rel)
        if not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            os.link(os.path.join(root, rel), dst)
    return tree


def drop_export_repo(root):
    """The export's empty repository has done its job once the build is over. Wrangler looks up
    commit details in whatever repository holds its working directory, and this one holds none."""
    shutil.rmtree(os.path.join(root, 'build', 'ship', 'tree', '.git'))


def discard_export(root):
    """After a verified deploy. A failed run keeps it, to look at; the next export replaces it."""
    shutil.rmtree(os.path.join(root, 'build', 'ship', 'tree'), ignore_errors=True)


def install_dist(root, tree):
    """Put the finished build at fy28/dist by renaming, which is what the dist-reading
    generators, sync_derived and the dist checks look at. Whole or not at all: the old dist
    stays in place until the new one is complete. Hold the site-build lock."""
    new = os.path.join(tree, 'fy28', 'dist')
    if not os.path.isfile(os.path.join(new, 'index.html')):
        raise OSError('the build left no %s' % os.path.relpath(new, root))
    dist = os.path.join(root, 'fy28', 'dist')
    old = os.path.join(root, 'build', 'ship', 'old-dist')
    if os.path.lexists(old):
        shutil.rmtree(old)
    if os.path.lexists(dist):
        os.rename(dist, old)
    try:
        os.rename(new, dist)
    except OSError:
        if os.path.lexists(old):
            os.rename(old, dist)
        raise
    if os.path.lexists(old):
        shutil.rmtree(old)


def overlay_public(root, sha):
    """Copy the fy28/public files commit `sha` changed into fy28/dist, because vite would have
    copied them there byte for byte. The dist-reading generators write those files AFTER the
    build they read, so without this production is always a build behind what main says.
    Only that one commit: other sessions' commits go out with the next build. -> files."""
    out = subprocess.run(['git', 'diff-tree', '-r', '--no-commit-id', '--name-only', '-z',
                          '--diff-filter=AM', sha, '--', 'fy28/public'],
                         cwd=root, capture_output=True, text=True).stdout
    n = 0
    for rel in out.split('\0'):
        if not rel:
            continue
        blob = subprocess.run(['git', 'cat-file', 'blob', '%s:%s' % (sha, rel)], cwd=root,
                              capture_output=True)
        if blob.returncode:
            raise OSError('could not read %s at %s' % (rel, sha[:8]))
        dst = os.path.join(root, 'fy28', 'dist', rel[len('fy28/public/'):])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        tmp = dst + '.ship.tmp'
        with open(tmp, 'wb') as fh:
            fh.write(blob.stdout)
        os.replace(tmp, dst)
        n += 1
    return n


def write_marker(root, sha, stamp):
    """A file only this build holds, so that a match proves THIS deploy is what production
    serves. A data file can match simply because it did not change since yesterday's site.
    In dist only; nothing commits it."""
    path = os.path.join(root, 'fy28', 'dist', MARKER)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('{"commit": "%s", "built": "%s"}\n' % (sha, stamp))


# ---------------------------------------------------------------------- deploying
DEPLOY_SITE_UPLOAD_FAILED = 75     # scripts/deploy_site.sh: everything passed, wrangler did not


def split_stage(root, stage, chunks=3):
    """The stage in `chunks` hard-linked parts. 29 October 2026: three uploads died near 10,500
    of 12,328 files, a failed attempt keeps nothing and a blind retry does not converge. A
    preview branch keeps what it uploaded and never touches production."""
    dest = os.path.join(root, 'build', 'ship', 'chunks')
    if os.path.lexists(dest):
        shutil.rmtree(dest)
    n, dirs = 0, [os.path.join(dest, str(i)) for i in range(chunks)]
    for d, _, names in os.walk(stage):
        rel = os.path.relpath(d, stage)
        for name in sorted(names):
            part = os.path.join(dirs[n % chunks], rel)
            os.makedirs(part, exist_ok=True)
            os.link(os.path.join(d, name), os.path.join(part, name))
            n += 1
    return [d for d in dirs if os.path.isdir(d)]


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def fetch_sha256(url):
    """-> (sha256 of the bytes served, or None; http status)."""
    r = subprocess.run(['curl', '-sL', '--compressed', '--max-time', '120', '-A', BROWSER,
                        '-w', '%{http_code}', '-o', '-', url], capture_output=True)
    body, code = r.stdout[:-3], r.stdout[-3:].decode('ascii', 'replace')
    if r.returncode or code != '200':
        return None, code
    return hashlib.sha256(body).hexdigest(), code


def verify_production(dist, files, nonce, site=SITE, fetch=fetch_sha256, tries=10, wait_s=30):
    """Fetch `files` from production and compare each with what was built, by sha256. Retried
    because the edge takes a moment after a deploy.
    -> (True, 'matched: ...') or (False, 'a/b.json: served <sha>, built <sha>')."""
    last = 'nothing was checked'
    for attempt in range(tries):
        if attempt:
            time.sleep(wait_s)
        bad = []
        for rel in files:
            want = _sha256_file(os.path.join(dist, rel))
            got, code = fetch('%s/%s?ship=%s' % (site, rel.replace(os.sep, '/'), nonce))
            if got != want:
                bad.append('%s: served %s (http %s), built %s'
                           % (rel, (got or 'nothing')[:12], code, want[:12]))
        if not bad and files:
            return True, 'matched by sha256: ' + ', '.join(
                '%s %s' % (rel, _sha256_file(os.path.join(dist, rel))[:12]) for rel in files)
        last = '; '.join(bad)
    return False, last


def verify_list(dist):
    """The marker proves this deploy is live; the others prove it carries the day's data."""
    wanted = [MARKER, 'index.html', os.path.join('data', 'whats-new.json'),
              os.path.join('data', 'reports.json')]
    return [f for f in wanted if os.path.exists(os.path.join(dist, f))]


# ---------------------------------------------------------------------- read-only reports
def plan(root=ROOT):
    import refresh_git as G
    print('armed: %s (%s)' % ('YES, a run pushes and deploys' if armed(root) else
                              'no, a run ingests, commits, deploys nothing', ARMED_FILE))
    print('branch %s at %s' % (G.branch(root) or '(detached)', G.head(root)[:8]))
    ahead = G.git(root, 'rev-list', 'refs/remotes/origin/main..HEAD', check=False).stdout.split()
    print('%d commit(s) ahead of origin/main would go out' % len(ahead))
    for c in ahead[:20]:
        print('    ' + G.git(root, 'log', '-1', '--format=%h %s', c).stdout.strip()[:100])
    try:
        holds = push_holds(root)
        print('push holds: %d' % len(holds))
        for h in holds:
            print('    ' + h[:120])
    except OSError as e:
        print('push holds: COULD NOT READ (%s) -- a run would not push' % e)
    claims = claimed_paths(root)
    print('claims: %s' % ('COULD NOT READ' if claims is None else len(claims)))
    dirty = G.dirty_paths(root)
    meeting = [p for p in dirty if is_meeting_output(p)]
    rest, held = split_ours([p for p in dirty if p not in meeting], claims or ())
    print('dirty: %d. Meeting output, adopted at the top of a run: %d. Hand-written or claimed, '
          'never committed: %d. Other, left alone as somebody else\'s: %d'
          % (len(dirty), len(meeting), len(held), len(rest)))
    for p in (held + rest)[:20]:
        print('    ' + p)
    holder = ''
    try:
        holder = open(os.path.join(root, 'build', 'process-meeting.lock')).read().strip()
    except OSError:
        pass
    print('meeting-run lock: %s' % (holder or 'not held'))
    return 0


def verify_cli(root=ROOT):
    dist = os.path.join(root, 'fy28', 'dist')
    ok, detail = verify_production(dist, [f for f in verify_list(dist) if f != MARKER], 'check',
                                   tries=1)
    print(('production matches fy28/dist -- ' if ok else 'production does NOT match fy28/dist: ') + detail)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    if '--plan' in sys.argv:
        sys.exit(plan())
    if '--verify' in sys.argv:
        sys.exit(verify_cli())
    print(__doc__)
    sys.exit(2)
