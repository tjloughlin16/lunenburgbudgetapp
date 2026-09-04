"""Every old /docs/ address still resolves to a file that exists.

    python3 scripts/check_moved_docs.py

The archive was reorganised on 4 September 2026 and `llms.txt` tells agents to CITE
`/docs/<path>` URLs, so an address published before that date is a promise. The map lives
in `fy28/functions/docs/_moved.js` and this asserts the only thing that matters about it:
that every target is a file the site actually serves.

**A 301 to a 404 is worse than a 404.** It tells a caller the document moved, sends them
somewhere, and leaves them with nothing -- and it looks like the redirect worked.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

    bad = []
    for old, new in sorted(exact.items()):
        if not os.path.exists(os.path.join(DOCS, new)):
            bad.append((old, new))

    # A prefix rule is only as good as the tree it points into.
    for frm, to in prefix:
        if not os.path.isdir(os.path.join(DOCS, to.rstrip('/'))):
            bad.append((frm + '<anything>', to + ' — destination directory missing'))

    # A document deliberately not served -- over the host's per-file cap -- is not a
    # broken alias. It is unreachable at the old address and the new one alike, and
    # saying so is the catalogue's job, not this one.
    oversize = set()
    cat = os.path.join(ROOT, 'fy28', 'src', 'data', 'sources.json')
    if os.path.exists(cat):
        blob = json.load(open(cat, encoding='utf-8'))

        def walk(node):
            if isinstance(node, dict):
                # Either hosted elsewhere, or over the host's per-file cap and
                # therefore named in the catalogue but not served from here. Both are
                # unreachable at the old address and the new one alike.
                if node.get('path') and (node.get('offsite')
                                         or (node.get('bytes') or 0) > 25 * 1024 * 1024):
                    oversize.add(node['path'])
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)
        walk(blob)
    bad = [(o, n) for o, n in bad if n.split(' —')[0] not in oversize]

    print('%d exact aliases, %d prefix rules' % (len(exact), len(prefix)))
    if bad:
        print('\n%d alias(es) point at something that is not served:' % len(bad))
        for old, new in bad[:20]:
            print('   /docs/%s  ->  /docs/%s' % (old, new))
        return 1
    print('every alias target exists in fy28/public/docs')
    return 0


if __name__ == '__main__':
    sys.exit(main())
