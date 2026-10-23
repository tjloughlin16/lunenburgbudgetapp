#!/usr/bin/env python3
"""THE SHELVES: fy28/public/data/topics.json, assembled from the registry (scripts/topics.py)
and every topic payload under fy28/public/data/topics/. It is what a hub's cards, the
/reports shelves and the prerender list read, so a page appears everywhere the day its
payload exists and nowhere before.

Each topic carries its title (the registry's), its finding (its payload's), its one
address, every shelf it is listed on, and an estimated reading time: the words a reader
meets on the page at 200 a minute, rounded up -- an ESTIMATE, labelled "about" where shown.

    python3 scripts/build_topics_index.py            # write
    python3 scripts/build_topics_index.py --check    # fail if stale, or a registered page has no payload
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import topics as REG  # noqa: E402

ROOT = os.path.dirname(HERE)
DIR = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics')
OUT = os.path.join(ROOT, 'fy28', 'public', 'data', 'topics.json')
# The ROUTER's list: which first path segments are category hubs. Bundled into the app (it is
# read synchronously, before any fetch), and only categories whose hub payload exists -- so a
# category routes the day its hub is built and not before.
ROUTES_OUT = os.path.join(ROOT, 'fy28', 'src', 'data', 'topic-categories.json')


def words(p):
    """The prose a reader meets on the page, counted."""
    parts = [p.get('finding', {}).get('text', ''), p.get('answer', {}).get('text', '')]
    for f in p.get('facts', []):
        parts.append(f['label']['text'])
    for c in p.get('conclusions', []) + (p.get('ladder') or {}).get('conclusions', []):
        parts.append(c['text'])
        parts += [n['text'] for n in c.get('notes', [])]
    parts += [s['quote'] for s in p.get('said', [])]
    for t in (p.get('ladder') or {}).get('tiers', []):
        parts += [f['label']['text'] for f in t['facts']]
    for t in [p.get('table')] + p.get('tables', []):
        if t:
            parts += [' '.join(r['label'] for r in t['views'][0]['rows'])]
    return sum(len(x.split()) for x in parts)


def build(strict):
    bad = REG.check()
    pays = {}
    for tid in list(REG.TOPICS) + [c['id'] for c in REG.CATEGORIES]:
        f = os.path.join(DIR, '%s.json' % tid)
        if os.path.exists(f):
            pays[tid] = json.load(open(f, encoding='utf-8'))
        elif strict:
            bad.append('%s is registered and has no payload (%s)' % (tid, os.path.relpath(f, ROOT)))
    topics = {}
    for tid, (title, home, gen) in REG.TOPICS.items():
        p = pays.get(tid)
        topics[tid] = dict(
            id=tid, title=title, path=REG.path(tid), home=home, shelves=REG.shelves_of(tid),
            finding=p['finding']['text'] if p else None,
            minutes=max(1, math.ceil(words(p) / 200)) if p else None,
            ready=bool(p), generator='scripts/' + gen)
    cats = []
    for c in REG.CATEGORIES:
        h = pays.get(c['id'])
        cats.append(dict(
            id=c['id'], shelf=c['shelf'], title=c['title'], path=REG.path(c['id']),
            answer=h['answer']['text'] if h else None,
            minutes=max(1, math.ceil(words(h) / 200)) if h else None, ready=bool(h),
            groups=[dict(title=g, topics=list(ids)) for g, ids in c['groups']],
            elsewhere=[dict(href=a, title=b) for a, b in c.get('elsewhere', [])],
            start=list(c.get('start', [])),
            area=c.get('area'), order=c.get('order', 99)))
    out = dict(generated_by='scripts/build_topics_index.py', categories=cats, topics=topics,
               areas=[dict(id=a, title=t) for a, t in REG.AREAS])
    routes = json.dumps(sorted(c['id'] for c in cats if c['ready']), indent=1) + '\n'
    return json.dumps(out, indent=1, ensure_ascii=False, sort_keys=True) + '\n', routes, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text, routes, bad = build(strict=a.check)
    if a.check:
        for path, want in ((OUT, text), (ROUTES_OUT, routes)):
            cur = open(path, encoding='utf-8').read() if os.path.exists(path) else None
            if cur != want:
                bad.append('%s is stale' % os.path.relpath(path, ROOT))
        print('\n'.join(bad) or 'topics.json current')
        return 1 if bad else 0
    for path, body in ((OUT, text), (ROUTES_OUT, routes)):
        with open(path, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(body)
    print('wrote %s%s' % (os.path.relpath(OUT, ROOT), ('; ' + '; '.join(bad)) if bad else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
