#!/usr/bin/env python3
"""RUN A COMMAND HOLDING THE SITE-BUILD LOCK. `npm run build:site` goes through this.

    python3 scripts/with_build_lock.py <command ...>

fy28/dist is shared. A build empties it and refills it page by page, so anything that READS
it while a build runs reads a torn folder. On 14 October 2026 a hand build started at 07:30
while the 07:00 refresh was indexing dist/, and the refresh died on a page the build had
just deleted (build_search_index.py, FileNotFoundError on department-budgets.html).

The refresh already held build/site-build.lock around its OWN build, but nothing else took
it: not a build started by hand, and not the refresh's steps that read dist/. Now both do.
The lock is an flock, so the kernel releases it if the holder dies -- it cannot go stale.

A process that already holds the lock (the refresh, building after its dist-reading steps)
sets SITE_BUILD_LOCK_HELD=1 so this does not wait on itself.
"""
import fcntl, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK = os.path.join(ROOT, 'build', 'site-build.lock')

cmd = sys.argv[1:]
if not cmd:
    sys.exit('usage: with_build_lock.py <command ...>')
if os.environ.get('SITE_BUILD_LOCK_HELD'):
    sys.exit(subprocess.run(cmd).returncode)
os.makedirs(os.path.dirname(LOCK), exist_ok=True)
fh = open(LOCK, 'a+')
try:
    fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    print('with_build_lock: the site-build lock is held -- the daily refresh is reading or '
          'building fy28/dist. Waiting for it...', flush=True)
    t0 = time.monotonic()
    fcntl.flock(fh, fcntl.LOCK_EX)
    print('with_build_lock: got it after %d s' % (time.monotonic() - t0), flush=True)
sys.exit(subprocess.run(cmd, env=dict(os.environ, SITE_BUILD_LOCK_HELD='1')).returncode)
