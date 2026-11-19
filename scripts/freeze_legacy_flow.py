#!/usr/bin/env python3
"""The pages still on the old order, frozen with their shape (see LEGACY_FLOW_FILE in topic.py).

    python3 scripts/freeze_legacy_flow.py --prune   # drop every listed page that is composed now
    python3 scripts/freeze_legacy_flow.py --check   # fail if a listed page is composed or missing

THE LIST ONLY SHRINKS. It was written once, on 18 November 2026, from the topic payloads in
fy28/public/data/topics/ that had no flow of their own. There is deliberately no command that
adds a page or re-records a shape: re-freezing would let a page change shape on the old order,
which is the thing the list exists to stop. A page leaves by being composed.
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import topic as TP  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOPICS = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics')


def payloads():
    out = {}
    for f in sorted(glob.glob(os.path.join(TOPICS, '*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        if d.get('kind') == 'topic':
            out[d['id']] = d
    return out


def write(pages):
    data = dict(about='Topic pages still on the old order, each with its shape. Only shrinks: '
                      'a page leaves by being composed (scripts/topic.py, LEGACY_FLOW_FILE).',
                frozen='2026-11-18', pages=dict(sorted(pages.items())))
    tmp = TP.LEGACY_FLOW_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(json.dumps(data, indent=1, ensure_ascii=False) + '\n')
    os.replace(tmp, TP.LEGACY_FLOW_FILE)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--prune', action='store_true')
    g.add_argument('--check', action='store_true')
    g.add_argument('--first-freeze', action='store_true', help=argparse.SUPPRESS)
    a = ap.parse_args()
    P = payloads()
    if a.first_freeze:
        if os.path.exists(TP.LEGACY_FLOW_FILE):
            raise SystemExit('the list exists; it is never re-frozen (see the docstring)')
        write({i: TP.page_shape(d) for i, d in P.items() if not d.get('composed')})
        print('froze %d pages' % len(json.load(open(TP.LEGACY_FLOW_FILE))['pages']))
        return 0
    leg = json.load(open(TP.LEGACY_FLOW_FILE, encoding='utf-8'))['pages']
    done = sorted(i for i in leg if i in P and P[i].get('composed'))
    gone = sorted(i for i in leg if i not in P)
    if a.prune:
        write({i: s for i, s in leg.items() if i not in done and i not in gone})
        print('pruned %d composed, %d no longer built; %d left on the old order'
              % (len(done), len(gone), len(leg) - len(done) - len(gone)))
        return 0
    if done or gone:
        print('STALE: composed %s; no longer built %s. Run --prune.' % (done, gone),
              file=sys.stderr)
        return 1
    print('legacy flow: %d pages still on the old order' % len(leg))
    return 0


if __name__ == '__main__':
    sys.exit(main())
