#!/usr/bin/env python3
"""ONE PIECE OF WORK, ONE WORKER. A lease taken on the UNIT, not on the batch.

WHAT THIS EXISTS BECAUSE OF. On 27 September 2026 two processes read the same sixteen
annual-report pages at the same time, about $4 of model spend to learn nothing. Neither did
anything wrong. Both derived their work list the same correct way -- every page that
`annual-report-pages.csv` still marks unread -- seventeen minutes apart, and the list does
not change while a page is being read. A page IN FLIGHT was byte-identical to a page nobody
had ever opened.

THE LESSON IS WHERE THE LOCK GOES. The obvious fix is a lock around the batch, and it would
not have helped: the second run was a second batch, holding its own lock, working the same
pages. The claim has to be on the PAGE, inside the thing that reads one page, so that any
number of callers -- a driver, a sweep, another session, a person -- converge instead of
colliding. Protect the unit and the batch takes care of itself.

    import worklease
    with worklease.claim('annual-page-fy2013-p83') as got:
        if not got:
            return 0            # somebody else is on it; not an error
        ...do the work...

WHY IT EXPIRES, AND WHY IT CHECKS THE PID. A lease that outlives its holder is worse than no
lease, because the work then never happens and nothing says why. This project already has
that exact bug in another form: a supervisor logged `restarted` on the half hour for hours
while launchd reaped its children instantly, and a restart that cannot outlive its supervisor
reports success while doing nothing. So a lease is ignored when the process that took it is
gone, and ignored again once it is older than `ttl` even if that pid is somehow alive -- a
recycled pid must not be able to block a queue forever.

WHY IT IS NOT IN GIT. `sources/data/ingest-pending.csv` is tracked, deliberately: a document
staged but not yet in the bucket is a fact about the ARCHIVE, the gate refuses destructive
work while one exists, and it must survive a fresh clone. A lease is the opposite -- a fact
about a process on one machine for the next few minutes. Committing it would put transient
state into the archive's history and, worse, hand a stale lease to every clone.
"""
import contextlib
import json
import os
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEASES = os.path.join(ROOT, 'build', 'leases')
TTL = 3600.0


def _alive(pid):
    """Is that process still there? Signal 0 checks without delivering anything."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True          # exists, owned by somebody else
    except (OverflowError, ValueError, TypeError):
        return False
    return True


def _stale(path, ttl):
    """True when a lease file may be taken over: holder gone, unreadable, or expired."""
    try:
        with open(path, encoding='utf-8') as fh:
            d = json.load(fh)
    except (OSError, ValueError):
        return True          # unreadable or half-written: not a claim anybody can honour
    if time.time() - float(d.get('at') or 0) > ttl:
        return True
    return not _alive(int(d.get('pid') or -1))


def _path(name):
    safe = ''.join(c if (c.isalnum() or c in '-_.') else '-' for c in str(name))
    return os.path.join(LEASES, safe + '.lease')


@contextlib.contextmanager
def claim(name, ttl=TTL, note=''):
    """Take the lease on `name`, yielding True if it is ours and False if somebody has it.

    False is a normal outcome and not an error: it means another worker is already on this
    unit, and the caller should move to the next one rather than fail. The lease is released
    on the way out however the block ends, including on an exception -- a crash mid-page must
    not park the page for an hour.
    """
    os.makedirs(LEASES, exist_ok=True)
    p = _path(name)
    body = json.dumps(dict(pid=os.getpid(), at=time.time(), name=str(name),
                           note=str(note))).encode()
    mine = False
    for _ in range(2):
        try:
            # O_EXCL is the whole mechanism: the check and the claim are one operation, so
            # two processes arriving together cannot both believe they won. A read followed
            # by a write is the check-then-act race that caused this file to exist.
            fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            with os.fdopen(fd, 'wb') as fh:
                fh.write(body)
            mine = True
            break
        except FileExistsError:
            if not _stale(p, ttl):
                break
            # Taking over an abandoned lease. Unlink and go round once; if a third process
            # wins the gap, the next attempt fails cleanly and we simply do not get it.
            try:
                os.unlink(p)
            except OSError:
                break
    try:
        yield mine
    finally:
        if mine:
            try:
                os.unlink(p)
            except OSError:
                pass


def held(ttl=TTL):
    """Every lease currently honoured, for a dashboard or a person asking what is running."""
    out = []
    try:
        names = sorted(os.listdir(LEASES))
    except OSError:
        return out
    for n in names:
        if not n.endswith('.lease'):
            continue
        p = os.path.join(LEASES, n)
        if _stale(p, ttl):
            continue
        try:
            with open(p, encoding='utf-8') as fh:
                out.append(json.load(fh))
        except (OSError, ValueError):
            continue
    return out


def main():
    cur = held()
    if not cur:
        print('no work leased right now')
        return 0
    print('%d unit(s) of work leased:' % len(cur))
    for d in cur:
        print('  %-44s pid %-7s %.0fs ago%s'
              % (d.get('name'), d.get('pid'), time.time() - float(d.get('at') or 0),
                 (' -- %s' % d['note']) if d.get('note') else ''))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
