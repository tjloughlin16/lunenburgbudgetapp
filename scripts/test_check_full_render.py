#!/usr/bin/env python3
"""The full-render gate refuses what would re-render every page, and nothing else.

Builds a throwaway repository shaped like this one, installs the real hooks, and plants commits.
Each case is a commit to main through the real pre-commit hook, armed and unarmed.

    python3 scripts/test_check_full_render.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, 'check_full_render.py')
SHELL = '<!doctype html>\n<!-- NEWEST REPORTS: %s -->\n<html><head><script src="/assets/index.js"></script></head></html>\n'


def run(cwd, *a, env=None, check=True):
    r = subprocess.run(list(a), cwd=cwd, capture_output=True, text=True, env=env)
    if check and r.returncode:
        raise AssertionError('%s: %s %s' % (' '.join(a), r.stdout, r.stderr))
    return r


def write(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8').write(text)


def world():
    d = tempfile.mkdtemp(prefix='full-render-gate-')
    run(d, 'git', 'init', '-q', '-b', 'main')
    run(d, 'git', 'config', 'user.email', 't@example.invalid')
    run(d, 'git', 'config', 'user.name', 'test')
    os.makedirs(os.path.join(d, 'scripts'))
    shutil.copy(GATE, os.path.join(d, 'scripts', 'check_full_render.py'))
    write(d, 'fy28/index.html', SHELL % 'monday')
    write(d, 'fy28/src/App.tsx', 'export const A = 1\n')
    write(d, 'fy28/src/data/sources.json', '{"n": 1}\n')
    write(d, 'fy28/public/data/sources.json', '{"n": 1}\n')
    write(d, 'sources/data/table.csv', 'a\n1\n')
    run(d, 'git', 'add', '-A')
    run(d, 'git', 'commit', '-q', '-m', 'base')
    run(d, sys.executable, 'scripts/check_full_render.py', '--install', '--root', d)
    return d


def commit(d, rel, text, env=None):
    write(d, rel, text)
    run(d, 'git', 'add', rel)
    e = dict(os.environ, **(env or {}))
    return run(d, 'git', 'commit', '-q', '-m', 'change %s' % rel, env=e, check=False)


def arm(d):
    write(d, 'ops/FULL-RENDER-GATE-ARMED', 'armed for the test\n')


CASES = []


def case(fn):
    CASES.append(fn)
    return fn


@case
def a_planted_code_commit_is_refused_when_armed():
    d = world()
    arm(d)
    r = commit(d, 'fy28/src/App.tsx', 'export const A = 2\n')
    assert r.returncode != 0, 'a code commit got through an armed gate'
    assert 'REFUSED' in r.stdout + r.stderr
    assert run(d, 'git', 'log', '--format=%s').stdout.splitlines()[0] == 'base'


@case
def bundled_data_is_refused_like_code():
    d = world()
    arm(d)
    r = commit(d, 'fy28/src/data/sources.json', '{"n": 2}\n')
    assert r.returncode != 0, 'fy28/src/data is compiled into the bundle and must be refused'


@case
def data_outside_the_bundle_passes():
    d = world()
    arm(d)
    assert commit(d, 'sources/data/table.csv', 'a\n2\n').returncode == 0
    assert commit(d, 'fy28/public/data/sources.json', '{"n": 2}\n').returncode == 0


@case
def the_preamble_is_not_keyed_but_the_shell_is():
    d = world()
    arm(d)
    assert commit(d, 'fy28/index.html', SHELL % 'tuesday').returncode == 0, 'preamble-only change refused'
    r = commit(d, 'fy28/index.html', (SHELL % 'tuesday').replace('index.js', 'index2.js'))
    assert r.returncode != 0, 'a change after <html got through'


@case
def the_prerender_script_and_build_config_are_refused():
    d = world()
    arm(d)
    assert commit(d, 'fy28/scripts/prerender.mjs', '// x\n').returncode != 0
    assert commit(d, 'fy28/package.json', '{}\n').returncode != 0


@case
def unarmed_reports_and_lets_it_through():
    d = world()
    r = commit(d, 'fy28/src/App.tsx', 'export const A = 3\n')
    assert r.returncode == 0, 'an unarmed gate blocked a commit'


@case
def the_owner_override_lets_one_through_and_is_logged():
    d = world()
    arm(d)
    r = commit(d, 'fy28/src/App.tsx', 'export const A = 4\n', env={'FULL_RENDER_APPROVED': 'TJ: test'})
    assert r.returncode == 0
    assert 'TJ: test' in open(os.path.join(d, 'build/full-render-gate/overrides.log')).read()


@case
def another_branch_is_not_gated():
    d = world()
    arm(d)
    run(d, 'git', 'checkout', '-q', '-b', 'side')
    assert commit(d, 'fy28/src/App.tsx', 'export const A = 5\n').returncode == 0


@case
def a_push_to_main_carrying_a_code_commit_is_refused():
    d = world()
    origin = tempfile.mkdtemp(prefix='full-render-origin-')
    run(origin, 'git', 'init', '-q', '--bare')
    run(d, 'git', 'remote', 'add', 'origin', origin)
    run(d, 'git', 'push', '-q', 'origin', 'main')
    assert commit(d, 'fy28/src/App.tsx', 'export const A = 6\n').returncode == 0  # unarmed: committed
    arm(d)
    r = run(d, 'git', 'push', 'origin', 'main', check=False)
    assert r.returncode != 0 and 'REFUSED' in r.stdout + r.stderr, 'pre-push let a full render through'
    shutil.rmtree(origin, ignore_errors=True)


def main():
    bad = 0
    for fn in CASES:
        try:
            fn()
            print('   ok   %s' % fn.__name__)
        except AssertionError as e:
            bad += 1
            print('  FAIL  %s: %s' % (fn.__name__, str(e)[:300]))
    print('%d of %d full-render gate cases hold' % (len(CASES) - bad, len(CASES)))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
