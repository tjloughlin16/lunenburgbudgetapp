"""Every old /docs/ address still resolves to a file that exists.

    python3 scripts/check_moved_docs.py

The archive was reorganised on 4 September 2026 and `llms.txt` tells agents to CITE
`/docs/<path>` URLs, so an address published before that date is a promise. The map lives
in `fy28/functions/docs/_moved.js` and this asserts the only thing that matters about it:
that every target is a file the site actually serves.

**A 301 to a 404 is worse than a 404.** It tells a caller the document moved, sends them
somewhere, and leaves them with nothing -- and it looks like the redirect worked.

**"Served" now means two places, not one.** Since 5 September 2026 the publishers' own
files are not in the build: they are in R2 and `functions/docs/_bucket.js` streams them
under the same URL. So a target counts as served if it is a build asset OR an object the
archive manifest lists -- and a target in neither is the broken alias this looks for.
Checking only the build directory would have started reporting 1,682 false failures the
day the binaries left it, which is the kind of check that gets switched off.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive_storage  # noqa: E402

MOVED = os.path.join(ROOT, 'fy28', 'functions', 'docs', '_moved.js')
DOCS = os.path.join(ROOT, 'fy28', 'public', 'docs')


def parse():
    """Read the map out of the module without a JS runtime."""
    src = open(MOVED, encoding='utf-8').read()
    prefix = [(m.group(1), m.group(2)) for m in
              re.finditer(r'\["([^"]+)",\s*"([^"]+)"\]', src)]
    pairs = dict(re.findall(r'^\s*"([^"]+)":\s*"([^"]+)",\s*$', src, re.M))
    return prefix, pairs


def main():
    prefix, exact = parse()
    if not prefix or not exact:
        print('could not parse the map — has _moved.js changed shape?')
        return 1

    manifest = archive_storage.read_manifest()

    def served(rel):
        return os.path.exists(os.path.join(DOCS, rel)) or rel in manifest

    bad = []
    for old, new in sorted(exact.items()):
        if not served(new):
            bad.append((old, new))

    # A prefix rule is only as good as the tree it points into.
    for frm, to in prefix:
        folder = to.rstrip('/')
        if not (os.path.isdir(os.path.join(DOCS, folder))
                or any(k.startswith(folder + '/') for k in manifest)):
            bad.append((frm + '<anything>', to + ' — destination directory missing'))

    # There is no longer any such thing as a document too large to serve. The seven that
    # were over Cloudflare Pages' 25MiB per-file cap -- six annual town reports and a
    # bridge assessment -- are in the bucket, which has no cap, so the exemption this
    # check used to carry has been deleted rather than left to rot into a loophole.

    n_bucket = sum(1 for _, new in exact.items()
                   if not os.path.exists(os.path.join(DOCS, new)) and new in manifest)
    print('%d exact aliases, %d prefix rules' % (len(exact), len(prefix)))
    if bad:
        print('\n%d alias(es) point at something that is not served:' % len(bad))
        for old, new in bad[:20]:
            print('   /docs/%s  ->  /docs/%s' % (old, new))
        return 1
    print('every alias target is served: %d from the build, %d from the bucket'
          % (len(exact) - n_bucket, n_bucket))
    return 0


if __name__ == '__main__':
    sys.exit(main())
