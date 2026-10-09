#!/usr/bin/env python3
"""The refresh's git rules, exercised against throwaway repositories. No network, no
model, nothing outside build/.

    python3 scripts/test_refresh_git.py      # exit 0 when every case holds

WHY A TEST AND NOT A READ-THROUGH. Every rule in refresh_git.py exists because the
opposite happened here: `add -A` swept work into a commit, a failed rebase plus `rebase
--abort` stranded 2,108 files on 4 October 2026, a moved main pushed the 8 October run to a
side branch. The code that prevents those can only be trusted the way the old code should
have been -- by making each situation happen and looking at what is left on disk. Each
case below builds an origin, a working tree and a second clone that plays "somebody else",
and asserts on file CONTENT, not on what the functions return.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import refresh_git as G  # noqa: E402

# Per process, so two agents running the checks at once cannot remove each other's repos.
SANDBOX = os.path.join(ROOT, 'build', 'test-refresh-git', str(os.getpid()))
ENV = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@example.invalid',
           GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@example.invalid',
           GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1')
os.environ.update({k: ENV[k] for k in ('GIT_AUTHOR_NAME', 'GIT_AUTHOR_EMAIL',
                                        'GIT_COMMITTER_NAME', 'GIT_COMMITTER_EMAIL',
                                        'GIT_CONFIG_GLOBAL', 'GIT_CONFIG_NOSYSTEM')})


def run(cwd, *args):
    r = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True, env=ENV)
    if r.returncode:
        raise AssertionError('git %s: %s' % (' '.join(args), r.stderr))
    return r.stdout.strip()


def write(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as fh:
        fh.write(text)


def read(root, rel):
    p = os.path.join(root, rel)
    return open(p).read() if os.path.exists(p) else None


def world():
    """origin (bare), tree (the refresh's working tree, on main), other (somebody else)."""
    d = tempfile.mkdtemp(dir=SANDBOX)
    origin, tree, other = (os.path.join(d, n) for n in ('origin.git', 'tree', 'other'))
    run(d, 'init', '-q', '--bare', '-b', 'main', origin)
    run(d, 'clone', '-q', origin, tree)
    run(tree, 'checkout', '-q', '-b', 'main')
    write(tree, '.gitattributes', 'log.csv merge=union\n')
    write(tree, 'log.csv', 'at,what\n1,first\n')
    write(tree, 'page.json', '{"v": 1}\n')
    write(tree, 'edited.md', 'committed text\n')
    write(tree, 'gone.txt', 'will be deleted by a person\n')
    write(tree, 'shared.txt', 'line one\n')
    run(tree, 'add', '.')
    run(tree, 'commit', '-q', '-m', 'seed')
    run(tree, 'push', '-q', 'origin', 'main')
    run(d, 'clone', '-q', origin, other)
    return tree, other


CASES = []


def case(fn):
    CASES.append(fn)
    return fn


@case
def uncommitted_work_is_put_back_and_never_staged():
    tree, _ = world()
    # Somebody else's session, before the run: an edit, a staged edit, an untracked file,
    # a deletion.
    write(tree, 'edited.md', 'A PERSON IS HALFWAY THROUGH THIS\n')
    write(tree, 'shared.txt', 'staged by a person\n')
    run(tree, 'add', 'shared.txt')
    write(tree, 'notes-untracked.md', 'a draft nobody committed\n')
    os.remove(os.path.join(tree, 'gone.txt'))
    base = G.Baseline.take(tree, stamp='t1')
    # The run: overwrites the edited file, recreates the deleted one, writes its own.
    write(tree, 'edited.md', 'what the generator writes\n')
    write(tree, 'gone.txt', 'regenerated\n')
    write(tree, 'page.json', '{"v": 2}\n')
    write(tree, 'new-minutes.json', '{}\n')
    ours, blocked, appended = G.settle(tree, base)
    assert ours == ['new-minutes.json', 'page.json'], ours
    assert appended == [], appended
    assert sorted(blocked) == ['edited.md', 'gone.txt'], blocked
    assert read(tree, 'edited.md') == 'A PERSON IS HALFWAY THROUGH THIS\n'
    assert read(tree, 'gone.txt') is None, 'a deletion was not put back'
    keep = os.path.join(base.store, 'conflicts')
    assert read(keep, 'edited.md') == 'what the generator writes\n', 'run version lost'
    assert read(keep, 'gone.txt') == 'regenerated\n', 'run version lost'
    sha = G.commit(tree, ours, 'Daily refresh, test')
    assert sha
    in_commit = run(tree, 'show', '--name-only', '--format=', sha).split()
    assert sorted(in_commit) == ['new-minutes.json', 'page.json'], in_commit
    # The person's staged entry is STILL staged, and their untracked draft untouched.
    assert 'shared.txt' in run(tree, 'diff', '--cached', '--name-only').split()
    assert read(tree, 'notes-untracked.md') == 'a draft nobody committed\n'
    assert read(tree, 'shared.txt') == 'staged by a person\n'


@case
def a_file_its_owner_committed_mid_run_is_left_alone():
    tree, _ = world()
    write(tree, 'edited.md', 'draft\n')
    base = G.Baseline.take(tree, stamp='t2')
    write(tree, 'edited.md', 'finished\n')            # the owner keeps working...
    run(tree, 'commit', '-q', '-am', 'owner commits')  # ...and commits during the run
    ours, blocked, _ = G.settle(tree, base)
    assert blocked == [] and ours == [], (ours, blocked)
    assert read(tree, 'edited.md') == 'finished\n', 'reverted a commit in the tree'


@case
def an_append_only_log_with_uncommitted_rows_keeps_everybodys_rows():
    tree, _ = world()
    write(tree, 'log.csv', read(tree, 'log.csv') + '2,the paced minutes run, uncommitted\n')
    write(tree, 'page.json', '{"v": 1, "a person": "editing"}\n')   # not append-only
    base = G.Baseline.take(tree, stamp='t3')
    write(tree, 'log.csv', read(tree, 'log.csv') + '3,the refresh\n')
    write(tree, 'page.json', '{"v": 1, "a person": "editing"}\n{"appended": 1}\n')
    ours, blocked, appended = G.settle(tree, base)
    assert appended == ['log.csv'] and blocked == ['page.json'] and ours == [], \
        (ours, blocked, appended)
    log = read(tree, 'log.csv')
    assert log.endswith('2,the paced minutes run, uncommitted\n3,the refresh\n'), log
    # A file NOT declared append-only is put back even when the change looks like an append.
    assert read(tree, 'page.json') == '{"v": 1, "a person": "editing"}\n'


@case
def pushes_straight_when_main_did_not_move():
    tree, _ = world()
    write(tree, 'page.json', '{"v": 3}\n')
    assert G.commit(tree, ['page.json'], 'refresh')
    status, detail = G.publish(tree)
    assert status == 'pushed', (status, detail)
    assert run(tree, 'rev-parse', 'HEAD') == run(tree, 'rev-parse', 'origin/main')


@case
def a_moved_main_is_replayed_onto_and_union_keeps_both_rows():
    tree, other = world()
    write(other, 'log.csv', read(other, 'log.csv') + '2,somebody else\n')
    write(other, 'unrelated.md', 'merged while the refresh ran\n')
    run(other, 'add', '.')
    run(other, 'commit', '-q', '-m', 'meanwhile')
    run(other, 'push', '-q', 'origin', 'main')
    write(tree, 'log.csv', read(tree, 'log.csv') + '2,the refresh\n')
    write(tree, 'page.json', '{"v": 4}\n')
    write(tree, 'edited.md', 'a person, uncommitted, untouched by either side\n')
    G.commit(tree, ['log.csv', 'page.json'], 'refresh')
    status, detail = G.publish(tree)
    assert status == 'pushed', (status, detail)
    assert run(tree, 'rev-parse', 'HEAD') == run(tree, 'rev-parse', 'origin/main')
    log = read(tree, 'log.csv')
    assert '2,somebody else' in log and '2,the refresh' in log, log
    assert read(tree, 'unrelated.md') == 'merged while the refresh ran\n'
    assert read(tree, 'edited.md') == 'a person, uncommitted, untouched by either side\n'
    # Linear: the refresh commit's parent is the commit somebody else pushed.
    assert run(tree, 'rev-parse', 'HEAD^') == run(other, 'rev-parse', 'HEAD')


@case
def without_the_union_line_the_same_appends_conflict():
    # The falsifier for the case above: if this ever passes cleanly, the union case is not
    # testing .gitattributes at all.
    tree, other = world()
    write(other, '.gitattributes', '')
    write(other, 'log.csv', read(other, 'log.csv') + '2,somebody else\n')
    run(other, 'commit', '-q', '-am', 'meanwhile, and no union')
    run(other, 'push', '-q', 'origin', 'main')
    write(tree, '.gitattributes', '')
    run(tree, 'commit', '-q', '-am', 'no union here either')
    write(tree, 'log.csv', read(tree, 'log.csv') + '2,the refresh\n')
    G.commit(tree, ['log.csv'], 'refresh')
    # The `no union` commit is a person's, so publish() would stop at local-only; ask the
    # replay directly, which is the part under test.
    run(tree, 'fetch', '-q')
    upstream = run(tree, 'rev-parse', 'origin/main')
    _, conflicted = G._replay(tree, [run(tree, 'rev-parse', 'HEAD')], upstream)
    assert conflicted == ['log.csv'], conflicted


@case
def a_moved_main_that_touches_uncommitted_work_moves_nothing():
    tree, other = world()
    write(other, 'edited.md', 'upstream changed this file\n')
    run(other, 'commit', '-q', '-am', 'meanwhile')
    run(other, 'push', '-q', 'origin', 'main')
    write(tree, 'edited.md', 'A PERSON IS EDITING THIS\n')      # dirty, not the refresh's
    write(tree, 'page.json', '{"v": 5}\n')
    sha = G.commit(tree, ['page.json'], 'refresh')
    status, detail = G.publish(tree)
    assert status == 'refused', (status, detail)
    assert read(tree, 'edited.md') == 'A PERSON IS EDITING THIS\n'
    assert run(tree, 'rev-parse', 'HEAD') == sha, 'the local commit moved'
    # ...and once the person is done, the NEXT run replays its own earlier commit.
    run(tree, 'commit', '-q', '-am', 'person commits')   # a foreign local commit now
    status, detail = G.publish(tree)
    assert status == 'local-only', (status, detail)


@case
def a_real_conflict_keeps_the_commit_local():
    tree, other = world()
    write(other, 'page.json', '{"v": "upstream"}\n')
    run(other, 'commit', '-q', '-am', 'meanwhile')
    run(other, 'push', '-q', 'origin', 'main')
    write(tree, 'page.json', '{"v": "refresh"}\n')
    sha = G.commit(tree, ['page.json'], 'refresh')
    status, detail = G.publish(tree)
    assert status == 'conflict' and 'page.json' in detail, (status, detail)
    assert run(tree, 'rev-parse', 'HEAD') == sha
    assert read(tree, 'page.json') == '{"v": "refresh"}\n'
    assert not G.operation_in_progress(tree), 'left a half-finished operation'


@case
def a_push_rejected_by_a_race_is_retried():
    tree, other = world()
    write(tree, 'page.json', '{"v": 6}\n')
    G.commit(tree, ['page.json'], 'refresh')
    real, raced = G.git, []

    def racing(root, *args, **kw):
        if args[:1] == ('push',) and not raced:
            raced.append(1)                  # main moves between our fetch and our push
            write(other, 'race.md', 'x\n')
            run(other, 'add', '.')
            run(other, 'commit', '-q', '-m', 'race')
            run(other, 'push', '-q', 'origin', 'main')
        return real(root, *args, **kw)
    G.git = racing
    try:
        status, detail = G.publish(tree)
    finally:
        G.git = real
    assert status == 'pushed' and 'attempt 2' in detail, (status, detail)
    assert read(tree, 'race.md') == 'x\n'


@case
def a_side_branch_commits_locally_and_never_pushes():
    tree, _ = world()
    run(tree, 'checkout', '-q', '-b', 'feature')
    write(tree, 'page.json', '{"v": 7}\n')
    assert G.commit(tree, ['page.json'], 'refresh')
    before = run(tree, 'ls-remote', 'origin', 'refs/heads/*')
    status, _ = G.publish(tree)
    assert status == 'not-main', status
    assert run(tree, 'ls-remote', 'origin', 'refs/heads/*') == before, 'pushed something'


@case
def nothing_is_committed_into_a_half_finished_operation():
    tree, _ = world()
    git_dir = run(tree, 'rev-parse', '--absolute-git-dir')
    write(git_dir, 'MERGE_HEAD', run(tree, 'rev-parse', 'HEAD') + '\n')
    write(tree, 'page.json', '{"v": 8}\n')
    assert G.commit(tree, ['page.json'], 'refresh') is None


def main():
    os.makedirs(SANDBOX, exist_ok=True)
    bad = 0
    for fn in CASES:
        try:
            fn()
            print('  ok    %s' % fn.__name__)
        except Exception as e:      # noqa: BLE001 -- report every case, not the first
            bad += 1
            print('  FAIL  %s: %s' % (fn.__name__, e))
    # Everything this made is under build/test-refresh-git; it is ours and disposable.
    shutil.rmtree(SANDBOX, ignore_errors=True)
    print('%d of %d refresh git cases hold' % (len(CASES) - bad, len(CASES)))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
