#!/usr/bin/env python3
"""How a refresh ships, exercised against throwaway repositories. No network, no model, no
build and no deploy; nothing outside build/.

    python3 scripts/test_refresh_ship.py      # exit 0 when every case holds

The companion to test_refresh_git.py, and the same idea: make each situation happen and look at
what is left. refresh.py's own flow runs here with the expensive steps stubbed: `npm` writes a
dist from what the export holds, `deploy_site.sh` is a stub that records what it was given, and
production is a dictionary. WHAT THIS CANNOT PROVE: a real 25-minute build in the export, a real
upload, Cloudflare serving the result. The paced run's side is the real code: a child process
imports process_meeting.py and runs its own yield functions against a throwaway lock.
"""
import argparse
import csv
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import process_meeting as PM  # noqa: E402
import refresh as R  # noqa: E402
import refresh_git as G  # noqa: E402
import refresh_ship as S  # noqa: E402

SANDBOX = os.path.join(ROOT, 'build', 'test-refresh-ship', str(os.getpid()))
ENV = dict(GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@example.invalid', GIT_COMMITTER_NAME='t',
           GIT_COMMITTER_EMAIL='t@example.invalid', GIT_CONFIG_GLOBAL='/dev/null',
           GIT_CONFIG_NOSYSTEM='1')
os.environ.update(ENV)


def git(cwd, *args):
    r = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise AssertionError('git %s: %s' % (' '.join(args), r.stderr))
    return r.stdout.strip()


def write(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as fh:
        fh.write(text)


def read(root, rel):
    return open(os.path.join(root, rel)).read()


def world():
    d = tempfile.mkdtemp(dir=SANDBOX)
    origin, tree = os.path.join(d, 'origin.git'), os.path.join(d, 'tree')
    git(d, 'init', '-q', '--bare', '-b', 'main', origin)
    git(d, 'clone', '-q', origin, tree)
    git(tree, 'checkout', '-q', '-b', 'main')
    write(tree, '.gitignore', 'build/\nfy28/node_modules\nfy28/dist\nfy28/public/docs/big.xlsx\n')
    write(tree, 'fy28/public/data/page.json', '{"v": 1}\n')
    write(tree, 'fy28/public/data/reports.json', '{"r": 1}\n')
    write(tree, 'fy28/public/data/whats-new.json', '{"w": 1}\n')
    write(tree, 'fy28/src/App.tsx', 'committed\n')
    write(tree, 'sources/data/official-votes/b/2026-01-01.json', '{"old": 1}\n')
    write(tree, 'sources/data/agentic-spend.csv', 'at,what\n')
    write(tree, 'sources/data/money-gaps.csv', 'side,what\n')
    write(tree, 'sources/data/refresh-runs.csv', ','.join(R.RUN_COLS) + '\n')
    write(tree, 'sources/analyses/UNLISTED', 'hidden\n')
    write(tree, 'scripts/x.py', 'committed\n')
    write(tree, 'fy28/public/docs/big.xlsx', 'ignored but published\n')
    os.makedirs(os.path.join(tree, 'fy28', 'node_modules'))
    git(tree, 'add', '.')
    git(tree, 'commit', '-q', '-m', 'seed')
    git(tree, 'push', '-q', 'origin', 'main')
    return tree, origin


def shown(tree, sha='HEAD'):
    return git(tree, 'show', '--name-only', '--format=', sha).split()


CASES = []


def case(fn):
    CASES.append(fn)
    return fn


# -------------------------------------------------------------------- what may be committed
@case
def hand_written_files_and_claims_are_never_committed():
    keep, held = S.split_ours(
        ['scripts/x.py', 'fy28/src/App.tsx', 'fy28/src/data/sources.json', 'notes/QUEUE.md',
         'notes/generated/AGENTIC-BACKLOG.md', 'notes/reference/x.md',
         'fy28/functions/api/_tablesizes.js', 'fy28/functions/docs/_bucket.js', 'CLAUDE.md',
         'README.md', 'fy28/public/data/page.json', 'sources/data/money-gaps.csv',
         'sources/analyses/mine.md', 'scriptsy/z'],
        claims=['sources/analyses'])
    assert sorted(keep) == ['README.md', 'fy28/functions/api/_tablesizes.js',
                            'fy28/public/data/page.json', 'fy28/src/data/sources.json',
                            'notes/generated/AGENTIC-BACKLOG.md', 'notes/reference/x.md',
                            'scriptsy/z', 'sources/data/money-gaps.csv'], keep
    assert 'scripts/x.py' in held and 'sources/analyses/mine.md' in held


@case
def meeting_output_without_its_lock_is_held_back():
    keep, held = S.split_ours(['sources/data/recording-minutes/b/a.json', 'fy28/public/data/p.json'],
                              exclude_meeting=True)
    assert keep == ['fy28/public/data/p.json'] and held == ['sources/data/recording-minutes/b/a.json']


@case
def a_hold_stops_the_push_and_the_mirror_prohibition_does_not():
    real, fake = subprocess.run, []

    class Out(object):
        returncode = 0
        stdout = ('Goals:\n    DO NOT: Never git push --mirror: local branches stay local\n'
                  '    DO NOT: Never publish the raw Report 1 PDF\n')

    def run(*a, **k):
        fake.append(a)
        return Out
    subprocess.run = run
    try:
        assert S.push_holds() == [], S.push_holds()
        Out.stdout += '    DO NOT: Do not push main until the names are masked\n'
        assert len(S.push_holds()) == 1
        Out.returncode = 1
        try:
            S.push_holds()
            raise AssertionError('an unreadable list of holds did not raise')
        except OSError:
            pass
    finally:
        subprocess.run = real


@case
def claims_are_read_from_what_genlock_really_prints():
    real = subprocess.run

    class Out(object):
        returncode = 0
        stdout = ('* T-7PMGT  until 07:56Z  scripts/refresh.py, scripts/refresh_git.py\n'
                  '  T-ABCDE  until 08:00Z  sources/analyses\n')
    subprocess.run = lambda *a, **k: Out
    try:
        assert S.claimed_paths() == ['scripts/refresh.py', 'scripts/refresh_git.py',
                                     'sources/analyses'], S.claimed_paths()
    finally:
        subprocess.run = real


# ------------------------------------------------------------------------- the meeting run
PACED = r'''
import fcntl, os, sys, time
sys.path.insert(0, %(scripts)r)
import process_meeting as PM
root = %(root)r
PM.LOCK, PM.YIELD = os.path.join(root, 'build', 'process-meeting.lock'), os.path.join(root, 'build', 'process-meeting.YIELD')
PM.LOCK_FH = open(PM.LOCK, 'a+')
fcntl.flock(PM.LOCK_FH, fcntl.LOCK_EX)
PM.LOCK_FH.seek(0); PM.LOCK_FH.truncate(); PM.LOCK_FH.write('%%d paced\n' %% os.getpid()); PM.LOCK_FH.flush()
print('held', flush=True)
n = 0
while n < 400:
    asker = PM.yield_requested()
    if asker:
        PM.yield_to_batch(asker)
        print('back', flush=True)
        break
    # a meeting: the two halves of one file, with the lock held throughout
    with open(os.path.join(root, 'sources/data/official-votes/b/inflight.json'), 'w') as fh:
        fh.write('{"half":')
        fh.flush()
        time.sleep(0.05)
        fh.write(' %%d}\n' %% n)
    n += 1
    time.sleep(0.02)
open(os.path.join(root, 'sources/data/official-votes/b/after-the-pause.json'), 'w').write('{}\n')
print('done', flush=True)
'''


def saw(p, word):
    """The child prints process_meeting.py's own [gov] lines too; read past them to `word`."""
    for line in p.stdout:
        if line.strip() == word:
            return True
    return False


def paced_run(tree):
    os.makedirs(os.path.join(tree, 'build'), exist_ok=True)
    p = subprocess.Popen([sys.executable, '-u', '-c', PACED % {'scripts': HERE, 'root': tree}],
                         stdout=subprocess.PIPE, text=True)
    assert p.stdout.readline().strip() == 'held'
    return p


@case
def the_real_paced_run_yields_finishes_its_write_and_takes_the_lock_back():
    tree, _ = world()
    p = paced_run(tree)
    time.sleep(0.3)
    pause = S.MeetingPause(tree, wait_s=30, poll_s=0.05)
    assert pause.acquire(), 'the paced run did not yield'
    # WHILE WE HOLD IT THE FILE IS WHOLE AND DOES NOT CHANGE: this is the torn read not happening.
    a = read(tree, 'sources/data/official-votes/b/inflight.json')
    assert a.endswith('}\n'), 'torn: %r' % a
    time.sleep(0.3)
    assert read(tree, 'sources/data/official-votes/b/inflight.json') == a, 'written during the pause'
    assert not os.path.exists(os.path.join(tree, 'sources/data/official-votes/b/after-the-pause.json'))
    assert read(tree, 'build/process-meeting.lock').split() == [str(os.getpid()), 'refresh']
    pause.release()
    assert not os.path.exists(os.path.join(tree, 'build/process-meeting.YIELD'))
    assert saw(p, 'back') and saw(p, 'done'), 'the paced run did not come back'
    assert p.wait(timeout=30) == 0
    assert os.path.exists(os.path.join(tree, 'sources/data/official-votes/b/after-the-pause.json'))


@case
def a_refresh_that_dies_hands_the_lock_straight_back():
    tree, _ = world()
    p = paced_run(tree)
    child = subprocess.Popen([sys.executable, '-c', (
        'import sys; sys.path.insert(0, %r)\nimport refresh_ship as S, os, time\n'
        'x = S.MeetingPause(%r, wait_s=30, poll_s=0.05)\nassert x.acquire()\nprint("got", flush=True)\n'
        'os.kill(os.getpid(), 9)\n' % (HERE, tree))], stdout=subprocess.PIPE, text=True)
    assert child.stdout.readline().strip() == 'got'
    child.wait()
    assert saw(p, 'back') and saw(p, 'done'), 'the paced run stayed paused after -9'
    assert p.wait(timeout=30) == 0


@case
def a_paced_run_that_never_yields_times_out_and_withdraws():
    tree, _ = world()
    os.makedirs(os.path.join(tree, 'build'))
    import fcntl
    # A second open file description conflicts with flock, as another process would.
    holder = open(os.path.join(tree, 'build/process-meeting.lock'), 'a+')
    fcntl.flock(holder, fcntl.LOCK_EX)
    pause = S.MeetingPause(tree, wait_s=0.3, poll_s=0.05)
    assert pause.acquire() is False
    assert not pause.held
    assert not os.path.exists(os.path.join(tree, 'build/process-meeting.YIELD')), 'request left behind'
    holder.close()


@case
def adoption_commits_meeting_output_and_nothing_else():
    tree, _ = world()
    write(tree, 'sources/data/official-votes/b/new.json', '{"n": 1}\n')
    write(tree, 'sources/data/recording-minutes/b/new.json', '{"m": 1}\n')
    write(tree, 'sources/data/agentic-spend.csv', 'at,what\n1,x\n')
    write(tree, 'sources/data/money-gaps.csv', 'side,what\nhalf,finished\n')   # a session's
    write(tree, 'fy28/src/App.tsx', 'half finished\n')                           # a session's
    git(tree, 'add', 'fy28/src/App.tsx')                                         # ...and staged
    real = S.claimed_paths
    S.claimed_paths = lambda root=None: []
    try:
        sha, n, why = S.adopt_meeting_output(tree, G)
    finally:
        S.claimed_paths = real
    assert why == '' and n == 3, (why, n)
    assert sorted(shown(tree, sha)) == ['sources/data/agentic-spend.csv',
                                        'sources/data/official-votes/b/new.json',
                                        'sources/data/recording-minutes/b/new.json']
    assert 'Refresh-Run:' in git(tree, 'log', '-1', '--format=%B')
    left = G.dirty_paths(tree)
    assert left == ['fy28/src/App.tsx', 'sources/data/money-gaps.csv'], left
    assert git(tree, 'diff', '--cached', '--name-only') == 'fy28/src/App.tsx', 'their stage was disturbed'


# ------------------------------------------------------------------------------ publishing
@case
def foreign_commits_go_out_with_main_only_when_armed():
    tree, origin = world()
    write(tree, 'scripts/x.py', 'a person\n')
    git(tree, 'add', 'scripts/x.py')
    git(tree, 'commit', '-q', '-m', 'a person')
    git(tree, 'branch', 'wip-snapshot-2026-10-19')
    status, _ = G.publish(tree)
    assert status == 'local-only', status
    status, _ = G.publish(tree, foreign_ok=True)
    assert status == 'pushed', status
    assert git(origin, 'rev-parse', 'main') == git(tree, 'rev-parse', 'HEAD')
    refs = git(origin, 'for-each-ref', '--format=%(refname)')
    assert refs == 'refs/heads/main', 'something other than main was pushed: %s' % refs


@case
def a_persons_commit_is_never_replayed_when_origin_moved():
    tree, origin = world()
    other = os.path.join(os.path.dirname(tree), 'other')
    git(os.path.dirname(tree), 'clone', '-q', origin, other)
    write(other, 'elsewhere.txt', 'x\n')
    git(other, 'add', '.')
    git(other, 'commit', '-q', '-m', 'from elsewhere')
    git(other, 'push', '-q', 'origin', 'main')
    write(tree, 'scripts/x.py', 'a person\n')
    git(tree, 'add', 'scripts/x.py')
    git(tree, 'commit', '-q', '-m', 'a person')
    mine = git(tree, 'rev-parse', 'HEAD')
    status, detail = G.publish(tree, foreign_ok=True)
    assert status == 'diverged', (status, detail)
    assert git(tree, 'rev-parse', 'HEAD') == mine


# ------------------------------------------------------------------------- the clean room
@case
def the_export_holds_the_commit_and_no_uncommitted_work():
    tree, _ = world()
    sha = git(tree, 'rev-parse', 'HEAD')
    write(tree, 'fy28/src/App.tsx', 'HALF FINISHED, UNCOMMITTED\n')
    write(tree, 'fy28/public/data/page.json', '{"v": "dirty"}\n')
    write(tree, 'fy28/public/data/untracked-draft.json', '{}\n')
    t = S.export_commit(tree, sha)
    assert read(t, 'fy28/src/App.tsx') == 'committed\n'
    assert read(t, 'fy28/public/data/page.json') == '{"v": 1}\n'
    assert not os.path.exists(os.path.join(t, 'fy28/public/data/untracked-draft.json'))
    assert read(t, 'fy28/public/docs/big.xlsx') == 'ignored but published\n', 'an ignored published file was lost'
    assert read(t, 'sources/analyses/UNLISTED') == 'hidden\n'
    assert os.path.islink(os.path.join(t, 'fy28/node_modules'))
    # Tailwind skips what git ignores, so the CSS depends on these two being there at build time.
    assert os.path.isdir(os.path.join(t, '.git')) and os.path.isfile(os.path.join(t, '.gitignore'))
    S.drop_export_repo(tree)
    assert not os.path.exists(os.path.join(t, '.git'))
    # Run twice: the second export replaces the first.
    t = S.export_commit(tree, sha)
    assert read(t, 'fy28/src/App.tsx') == 'committed\n'


@case
def a_dist_is_replaced_whole_and_a_failed_build_leaves_it():
    tree, _ = world()
    t = S.export_commit(tree, git(tree, 'rev-parse', 'HEAD'))
    write(tree, 'fy28/dist/index.html', 'yesterday\n')
    try:
        S.install_dist(tree, t)
        raise AssertionError('installed a build with no index.html')
    except OSError:
        pass
    assert read(tree, 'fy28/dist/index.html') == 'yesterday\n'
    write(t, 'fy28/dist/index.html', 'today\n')
    S.install_dist(tree, t)
    assert read(tree, 'fy28/dist/index.html') == 'today\n'
    assert not os.path.exists(os.path.join(tree, 'build/ship/old-dist'))


@case
def overlay_copies_only_that_commits_public_files():
    tree, _ = world()
    write(tree, 'fy28/dist/data/reports.json', 'built\n')
    write(tree, 'fy28/public/data/reports.json', '{"r": 2}\n')
    write(tree, 'sources/data/money-gaps.csv', 'not public\n')
    git(tree, 'add', 'fy28/public/data/reports.json', 'sources/data/money-gaps.csv')
    git(tree, 'commit', '-q', '-m', 'after build')
    write(tree, 'fy28/public/data/reports.json', '{"r": "dirty, not the commit"}\n')
    assert S.overlay_public(tree, git(tree, 'rev-parse', 'HEAD')) == 1
    assert read(tree, 'fy28/dist/data/reports.json') == '{"r": 2}\n'


@case
def the_stage_splits_into_parts_that_together_hold_every_file():
    d = tempfile.mkdtemp(dir=SANDBOX)
    for i in range(10):
        write(d, 'stage/sub%d/f%d.txt' % (i % 2, i), str(i))
    parts = S.split_stage(d, os.path.join(d, 'stage'))
    seen = sorted(f for p in parts for _, _, names in os.walk(p) for f in names)
    assert seen == sorted('f%d.txt' % i for i in range(10)) and len(parts) == 3, seen


@case
def production_is_compared_by_hash_and_retried():
    d = tempfile.mkdtemp(dir=SANDBOX)
    write(d, 'a.json', 'built\n')
    want = hashlib.sha256(b'built\n').hexdigest()
    served = [(hashlib.sha256(b'yesterday\n').hexdigest(), '200'), (None, '403'), (want, '200')]
    ok, detail = S.verify_production(d, ['a.json'], 'n', fetch=lambda u: served.pop(0), tries=3, wait_s=0)
    assert ok and want[:12] in detail, detail
    ok, detail = S.verify_production(d, ['a.json'], 'n', fetch=lambda u: (None, '500'), tries=2, wait_s=0)
    assert not ok and 'http 500' in detail, detail
    ok, _ = S.verify_production(d, [], 'n', tries=1, wait_s=0)
    assert not ok, 'nothing checked cannot mean verified'


# --------------------------------------------------------- the whole shipping flow, stubbed
class Flow(object):
    """refresh.py pointed at a throwaway repository, with the build, the deploy, the check and
    production replaced by stubs that behave the way the real ones are documented to."""

    def __init__(self, tree):
        self.tree, self.commands, self.check_results = tree, [], []
        self.deploy_rc, self.served_ok, self.deploy_env = [0], True, None
        self.saved = {k: getattr(R, k) for k in ('ROOT', 'RUNS', 'SCRIPTS', 'sh', 'failing_checks',
                                                 'acquire_build_lock')}
        self.ship_saved = {k: getattr(S, k) for k in ('claimed_paths', 'push_holds', 'verify_production')}
        self.holds = []
        R.ROOT, R.RUNS = tree, os.path.join(tree, 'sources', 'data', 'refresh-runs.csv')
        R.SCRIPTS = os.path.join(tree, 'scripts')
        R.sh = self.sh
        R.failing_checks = self.failing
        # Never the real one: it is this machine's lock, and it waits on this machine's builds.
        R.acquire_build_lock = lambda notes: open(os.devnull)
        R.RAN.clear()
        S.claimed_paths = lambda root=None: []
        S.push_holds = lambda root=None: list(self.holds)
        S.verify_production = self.verify

    def restore(self):
        for k, v in self.saved.items():
            setattr(R, k, v)
        for k, v in self.ship_saved.items():
            setattr(S, k, v)

    def failing(self):
        return self.check_results.pop(0) if self.check_results else []

    def verify(self, dist, files, nonce):
        self.verified_files = files
        return (True, 'matched by sha256: stub') if self.served_ok else (False, 'a: served x, built y')

    def sh(self, args, check=True, quiet=False, **kw):
        kw.pop('extra_env', None) if 'deploy_site.sh' not in ' '.join(args) else None
        cmd = ' '.join(args)
        self.commands.append(cmd)
        rc = 0

        class Result(object):
            pass
        if 'build:site:unlocked' in cmd:
            cwd = kw['cwd']
            # The stub build: dist is what the EXPORT holds. A leak of the tree would show here.
            self.built_from = read(cwd, 'src/App.tsx')
            write(cwd, 'dist/index.html', 'built from ' + self.built_from)
            shutil.copytree(os.path.join(cwd, 'public', 'data'), os.path.join(cwd, 'dist', 'data'))
            rc = self.build_rc if hasattr(self, 'build_rc') else 0
        elif 'deploy_site.sh' in cmd:
            self.deploy_env = kw.get('extra_env')
            rc = self.deploy_rc.pop(0)
        elif 'build_reports_index.py' in cmd:
            # What really happens: it reads the date of the commit just made.
            write(self.tree, 'fy28/public/data/reports.json', '{"updated": "after the commit"}\n')
        R.RAN.add(os.path.basename(args[1] if 'python' in os.path.basename(args[0]) else args[0]))
        r = Result()
        r.returncode, r.stdout, r.stderr = rc, '', ''
        return r


def args(as_of='2026-11-06'):
    return argparse.Namespace(as_of=as_of, deploy=True, dry_run=False, commit=True)


def row(tree):
    return list(csv.DictReader(open(os.path.join(tree, 'sources/data/refresh-runs.csv'))))[-1]


def flow_setup(tree, f):
    write(tree, 'ops/REFRESH-SHIP-ARMED', 'armed\n')
    git(tree, 'add', 'ops/REFRESH-SHIP-ARMED')
    git(tree, 'commit', '-q', '-m', 'arm')
    git(tree, 'push', '-q', 'origin', 'main')
    ctx = {'base': None, 'blocked': [], 'held': [], 'push': None, 'armed': True,
           'pause': S.MeetingPause(tree, wait_s=5, poll_s=0.05)}
    ctx['base'] = G.Baseline.take(tree)
    assert ctx['pause'].acquire()
    return ctx


def run_ship(tree, f, ctx, a, notes):
    R.commit_run(a, notes, ctx, 'data')
    deployed = R.ship(a, notes, ctx)
    R.finish_shipping(a, lambda d, s: R.record_run(a, {k: 0 for k in R.FIRST_CLASS}, d, s, notes),
                      deployed, notes, ctx)
    ctx['pause'].release()
    return deployed


@case
def an_armed_run_ships_the_commit_and_leaves_a_sessions_work_behind():
    tree, origin = world()
    write(tree, 'fy28/src/App.tsx', 'A SESSION IS HALFWAY THROUGH THIS\n')   # dirty under fy28/: the old block
    write(tree, 'scripts/x.py', 'a session again\n')
    f = Flow(tree)
    try:
        write(tree, 'fy28/public/data/foreign.json', '{}\n')
        git(tree, 'add', 'fy28/public/data/foreign.json')
        git(tree, 'commit', '-q', '-m', 'a person’s unpushed commit: the other old block')
        ctx = flow_setup(tree, f)
        write(tree, 'fy28/public/data/page.json', '{"v": 2}\n')     # what the run wrote
        write(tree, 'scripts/started-during-the-run.py', 'half\n')  # the sweep of old
        notes = []
        a = args()
        assert run_ship(tree, f, ctx, a, notes) is True, notes
        assert 'ship_failure' not in ctx, ctx
        assert f.built_from == 'committed\n', 'uncommitted work reached the build: %r' % f.built_from
        assert read(tree, 'fy28/dist/index.html') == 'built from committed\n'
        assert read(tree, 'fy28/src/App.tsx') == 'A SESSION IS HALFWAY THROUGH THIS\n', 'their file moved'
        left = G.dirty_paths(tree)
        assert 'fy28/src/App.tsx' in left and 'scripts/started-during-the-run.py' in left, left
        assert git(origin, 'rev-parse', 'main') == git(tree, 'rev-parse', 'HEAD')
        out = git(origin, 'log', '--format=', '--name-only', 'main')
        assert 'started-during-the-run' not in out and 'App.tsx' in out  # App.tsx from the seed only
        assert git(origin, 'show', 'main:fy28/src/App.tsx') == 'committed'
        # The deploy got the export's cwd, the branch by name, and the after-build output.
        dep = [c for c in f.commands if 'deploy_site.sh' in c]
        assert len(dep) == 1 and '--branch main' in dep[0], dep
        assert f.deploy_env['DEPLOY_SITE_TREE'].endswith('build/ship/tree/fy28')
        assert not os.path.exists(os.path.join(tree, 'build/ship/tree')), 'the export was left behind'
        assert read(tree, 'fy28/dist/data/reports.json') == '{"updated": "after the commit"}\n'
        assert os.path.exists(os.path.join(tree, 'fy28/dist/data/ship.json'))
        assert f.verified_files[0] == S.MARKER and 'index.html' in f.verified_files
        r = row(tree)
        assert r['deployed'] == 'yes' and r['state'] == 'ok' and 'verified from production' in r['notes'], r
        assert 'refresh-runs.csv' in git(origin, 'show', '--name-only', '--format=', 'main')
    finally:
        f.restore()


@case
def a_failed_deploy_is_loud_and_names_its_cause():
    tree, origin = world()
    f = Flow(tree)
    try:
        ctx = flow_setup(tree, f)
        f.deploy_rc = [1]
        notes = []
        assert run_ship(tree, f, ctx, args(), notes) is False
        r = row(tree)
        assert r['deployed'] == 'no' and r['state'] == 'not shipped', r
        assert 'DID NOT DEPLOY: deploy_site.sh exited 1' in r['notes'], r['notes']
        assert 'deploy_site.sh exited 1' in read(tree, 'build/refresh-ship-failure.txt')
    finally:
        f.restore()


@case
def a_dead_upload_goes_up_in_parts_then_deploys():
    tree, _ = world()
    f = Flow(tree)
    try:
        ctx = flow_setup(tree, f)
        write(tree, 'build/deploy-stage/a.txt', 'a\n')
        f.deploy_rc = [S.DEPLOY_SITE_UPLOAD_FAILED, 0]
        assert run_ship(tree, f, ctx, args(), []) is True
        assert sum('upload-staging' in c for c in f.commands) == 1, f.commands
        assert sum('deploy_site.sh' in c for c in f.commands) == 2
        assert not any('upload-staging' in c and '--branch main' in c for c in f.commands)
    finally:
        f.restore()


@case
def production_serving_something_else_is_a_failure():
    tree, _ = world()
    f = Flow(tree)
    try:
        ctx = flow_setup(tree, f)
        f.served_ok = False
        assert run_ship(tree, f, ctx, args(), []) is False
        assert 'does not serve this build' in row(tree)['notes']
    finally:
        f.restore()


@case
def a_failed_build_touches_neither_dist_nor_production():
    tree, _ = world()
    f = Flow(tree)
    try:
        write(tree, 'fy28/dist/index.html', 'yesterday\n')
        ctx = flow_setup(tree, f)
        f.build_rc = 2
        assert run_ship(tree, f, ctx, args(), []) is False
        assert read(tree, 'fy28/dist/index.html') == 'yesterday\n'
        assert not any('deploy_site.sh' in c for c in f.commands)
        assert 'the site build failed (exit 2)' in row(tree)['notes']
    finally:
        f.restore()


@case
def a_hold_stops_everything_before_the_build():
    tree, origin = world()
    f = Flow(tree)
    try:
        ctx = flow_setup(tree, f)
        f.holds = ['Do not push main until the names are masked']
        write(tree, 'fy28/public/data/page.json', '{"v": 2}\n')
        was = git(origin, 'rev-parse', 'main')
        assert run_ship(tree, f, ctx, args(), []) is False
        assert git(origin, 'rev-parse', 'main') == was, 'it pushed through a hold'
        assert not any('build:site' in c for c in f.commands)
        assert 'names are masked' in row(tree)['notes']
    finally:
        f.restore()


@case
def a_stale_generator_is_repaired_and_one_that_stays_stale_stops_the_deploy():
    tree, _ = world()
    # Repaired: stale on the first look, gone on the second.
    f = Flow(tree)
    try:
        ctx = flow_setup(tree, f)
        R.RAN.add('build_notices.py')
        f.check_results = [[('build_notices.py', '--check')], [], []]
        assert run_ship(tree, f, ctx, args(), []) is True
        assert any('build_notices.py' in c for c in f.commands)
    finally:
        f.restore()
    tree, _ = world()
    f = Flow(tree)
    try:
        ctx = flow_setup(tree, f)
        R.RAN.add('build_notices.py')
        f.check_results = [[('build_notices.py', '--check')], [('build_notices.py', '--check')], []]
        assert run_ship(tree, f, ctx, args(), []) is False
        assert 'after a repair: build_notices.py' in row(tree)['notes']
        assert not any('build:site' in c for c in f.commands)
    finally:
        f.restore()


@case
def a_failure_in_a_generator_the_run_did_not_execute_never_blocks():
    # verify_balance_sheet.py: seven open failures, a decision for TJ. The refresh does not run it.
    tree, _ = world()
    f = Flow(tree)
    try:
        ctx = flow_setup(tree, f)
        f.check_results = [[('verify_balance_sheet.py', 'FAIL 7')]]
        notes = []
        assert run_ship(tree, f, ctx, args(), notes) is True
        assert any('stale elsewhere' in n and 'verify_balance_sheet.py' in n for n in notes), notes
    finally:
        f.restore()
    src = open(os.path.join(HERE, 'refresh.py'), encoding='utf-8').read()
    assert "py('verify_balance_sheet" not in src and "'verify_balance_sheet.py'," not in src


@case
def a_branch_that_is_not_main_does_not_ship():
    tree, _ = world()
    git(tree, 'checkout', '-q', '-b', 'side')
    f = Flow(tree)
    try:
        write(tree, 'ops/REFRESH-SHIP-ARMED', 'x\n')
        ctx = {'base': G.Baseline.take(tree), 'blocked': [], 'held': [], 'push': None, 'armed': True,
               'pause': S.MeetingPause(tree, wait_s=5, poll_s=0.05)}
        assert ctx['pause'].acquire()
        assert run_ship(tree, f, ctx, args(), []) is False
        assert 'only main reaches production' in row(tree)['notes']
    finally:
        f.restore()


@case
def ship_only_retries_without_ingesting_and_corrects_the_row():
    tree, origin = world()
    f = Flow(tree)
    try:
        ctx = flow_setup(tree, f)
        f.deploy_rc = [1]
        a = args()
        notes = ['a note from the morning']
        assert run_ship(tree, f, ctx, a, notes) is False
        assert row(tree)['deployed'] == 'no'
        f.deploy_rc = [0]
        f.commands.clear()
        assert R.ship_only(a) == 0
        r = row(tree)
        assert r['deployed'] == 'yes' and r['state'] == 'ok', r
        assert 'a note from the morning' in r['notes'] and 'DID NOT DEPLOY' not in r['notes'], r['notes']
        assert not any(w in c for c in f.commands for w in ('watch_', 'fetch_', 'process_meeting'))
        assert git(origin, 'rev-parse', 'main') == git(tree, 'rev-parse', 'HEAD')
    finally:
        f.restore()


@case
def unarmed_a_run_commits_as_it_always_did_and_pushes_no_persons_commit():
    tree, origin = world()
    f = Flow(tree)
    try:
        write(tree, 'scripts/x.py', 'a person\n')
        git(tree, 'add', 'scripts/x.py')
        git(tree, 'commit', '-q', '-m', 'a person')
        was = git(origin, 'rev-parse', 'main')
        ctx = {'base': G.Baseline.take(tree), 'blocked': [], 'held': [], 'push': None, 'armed': False}
        write(tree, 'fy28/public/data/page.json', '{"v": 2}\n')
        notes = []
        R.commit_run(args(), notes, ctx, 'data')
        assert ctx['push'] == 'local-only', ctx
        assert git(origin, 'rev-parse', 'main') == was
        assert 'fy28/public/data/page.json' in shown(tree)
        assert any('NOT PUSHED (local-only)' in n for n in notes)
    finally:
        f.restore()


@case
def daily_refresh_treats_exit_3_as_ran_raises_the_banner_and_does_not_ingest_twice():
    d = tempfile.mkdtemp(dir=SANDBOX)
    text = open(os.path.join(HERE, 'daily_refresh.sh'), encoding='utf-8').read()
    write(d, 'scripts/daily_refresh.sh', text.replace('osascript', 'true'))
    write(d, 'scripts/check_archive_backed_up.py', '')
    write(d, 'scripts/triage_refresh.py', '')
    write(d, 'scripts/refresh.py', 'import os\nopen("build/ran", "a").write("x")\n'
          'open("build/refresh-ship-failure.txt", "w").write("the upload died\\n")\nraise SystemExit(3)\n')
    git(d, 'init', '-q')
    log = os.path.join(d, 'build', 'refresh-logs', 'today.log')
    env = dict(os.environ, REFRESH_LOG=log)
    for _ in range(2):
        subprocess.run(['bash', os.path.join(d, 'scripts/daily_refresh.sh')], env=env, check=True)
    assert read(d, 'build/ran') == 'x', 'the second firing ingested again'
    alert = read(d, 'build/refresh-ALERT.txt')
    assert 'DID NOT DEPLOY' in alert and 'the upload died' in alert and '--ship-only' in alert, alert
    assert 'already ran today' in read(d, 'build/refresh-logs/today.log')


@case
def the_real_scripts_are_as_this_test_assumes():
    # The paths the pause uses are process_meeting.py's own.
    assert S.MeetingPause(ROOT).lock == PM.LOCK and S.MeetingPause(ROOT).request == PM.YIELD
    # The tree is not armed by accident in a commit this test did not see: it is a file, and
    # absent means the old behaviour with no deploy at all.
    assert S.ARMED_FILE == os.path.join('ops', 'REFRESH-SHIP-ARMED')
    d = tempfile.mkdtemp(dir=SANDBOX)
    assert S.armed(d) is False
    # A daily run reads exit 3 as `ran`, so the next login does not ingest it all again.
    text = open(os.path.join(HERE, 'daily_refresh.sh'), encoding='utf-8').read()
    assert '"refresh exit 3"' in text and 'refresh-ship-failure.txt' in text
    text = open(os.path.join(HERE, 'deploy_site.sh'), encoding='utf-8').read()
    assert 'DEPLOY_SITE_TREE' in text and '|| exit %d' % S.DEPLOY_SITE_UPLOAD_FAILED in text


def main():
    os.makedirs(SANDBOX, exist_ok=True)
    bad = 0
    real_out = sys.stdout
    for fn in CASES:
        try:
            sys.stdout = open(os.devnull, 'w')
            fn()
            sys.stdout = real_out
            print('  ok    %s' % fn.__name__)
        except BaseException as e:   # noqa: BLE001 -- report every case, not the first
            sys.stdout = real_out
            bad += 1
            print('  FAIL  %s: %s: %s' % (fn.__name__, type(e).__name__, str(e)[:600]))
    shutil.rmtree(SANDBOX, ignore_errors=True)
    print('%d of %d refresh shipping cases hold' % (len(CASES) - bad, len(CASES)))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
