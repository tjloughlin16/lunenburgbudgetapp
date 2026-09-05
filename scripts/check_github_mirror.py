#!/usr/bin/env python3
"""Is everything an agent might need also reachable when the site is not?

    python3 scripts/check_github_mirror.py

WHY THIS EXISTS

Some agents cannot reach lunenburgbudgetproject.org at all. Not because anything is wrong
with it -- it answers every request in under 300ms, to any user agent, with no bot
protection -- but because their sandbox has an egress allowlist and this domain is not on
it. `x-deny-reason: host_not_allowed`. Nothing published here can change that.

What CAN be true is that the same material is reachable somewhere their allowlist does
permit, and for most sandboxes that is GitHub. It already is: every static API file, the
whole extracted text, the manifests and the analysis database are committed, so
`raw.githubusercontent.com/<repo>/main/<path>` serves them.

That is a fallback nobody knew about, which is the same as not having one. It is now stated
at the top of llms.txt and in the README -- and this check makes sure the claim stays true,
because a mirror that has quietly gone incomplete is worse than one that was never
promised.

The one thing that cannot be mirrored is `/api/query`, which needs a database at request
time. An agent on GitHub can query the committed database instead; that is what one did.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# What the fallback promises. Every file under these must be committed, or an agent
# following the README lands on a 404.
MIRRORED = ['fy28/public/api', 'fy28/public/docs/data', 'fy28/public/minutes/find']
# The database an agent queries when it cannot reach /api/query.
MUST_EXIST = ['fy28/public/docs/data/lunenburg.db', 'fy28/public/llms.txt',
              'sources/data/archive-manifest.csv', 'README.md']


def tracked():
    out = subprocess.run(['git', '-C', ROOT, 'ls-files', '-z'],
                         capture_output=True, text=True).stdout
    return set(out.split('\0'))


def main():
    have = tracked()
    missing = []
    for folder in MIRRORED:
        base = os.path.join(ROOT, folder)
        if not os.path.isdir(base):
            continue
        for dirpath, _dirs, files in os.walk(base):
            for name in files:
                rel = os.path.relpath(os.path.join(dirpath, name), ROOT)
                rel = rel.replace(os.sep, '/')
                if rel not in have:
                    missing.append(rel)
    absent = [p for p in MUST_EXIST if p not in have]

    counts = {f: sum(1 for p in have if p.startswith(f + '/')) for f in MIRRORED}
    for folder, n in counts.items():
        print(f'  {n:>5} files mirrored from {folder}')

    if missing or absent:
        if absent:
            print(f'\n{len(absent)} file(s) the fallback names are not in the repository:')
            for p in absent:
                print('  ' + p)
        if missing:
            print(f'\n{len(missing)} published file(s) are NOT committed, so an agent that '
                  f'can only reach GitHub gets a 404:')
            for p in missing[:10]:
                print('  ' + p)
            if len(missing) > 10:
                print(f'  ... and {len(missing) - 10} more')
        print('\n  Commit them, or stop promising the mirror in llms.txt and README.md.')
        return 1

    print(f'\nok: the GitHub fallback is complete — '
          f'{sum(counts.values()):,} files, and the database itself')
    return 0


if __name__ == '__main__':
    sys.exit(main())
