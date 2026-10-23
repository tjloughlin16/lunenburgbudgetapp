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
    python3 scripts/build_topics_index.py --suggest-related   # candidate related pairs, ranked;
                                                              # printed for a person to accept

RELATED PAGES are declared in scripts/topic_registry/related.py, validated here, and written
into each topic's and each hub's `related` list -- the one place Topic.tsx reads them from.
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import topics as REG  # noqa: E402
from topic_registry import related as REL  # noqa: E402

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


def app_routes():
    """Every first path segment the app routes, read off fy28/src/routes.ts's string values."""
    import re
    src = open(os.path.join(ROOT, 'fy28', 'src', 'routes.ts'), encoding='utf-8').read()
    return {m.split('/')[0] for m in re.findall(r":\s*'([a-z0-9][a-z0-9/-]*)'", src)}


def related():
    """{page id: [{id, title, path, why}]} from the declared clusters, symmetric by
    construction, and the list of rule breaks (scripts/topic_registry/related.py)."""
    bad, out = [], {}
    cats = {c['id']: c for c in REG.CATEGORIES}
    routes = None
    for n, cluster in enumerate(REL.RELATED, 1):
        where = 'related.py cluster %d' % n
        if len(cluster) < 2:
            bad.append('%s: a cluster relates two or more pages' % where)
        members = []
        for m in cluster:
            if len(m) == 2:
                mid, why = m
                if mid in REG.TOPICS:
                    title = REG.TOPICS[mid][0]
                elif mid in cats:
                    title = cats[mid]['title']
                else:
                    bad.append('%s: %r is not a registered topic or category' % (where, mid))
                    continue
                path = REG.path(mid)
            elif len(m) == 3:
                path, title, why = m
                routes = routes if routes is not None else app_routes()
                if not (isinstance(path, str) and path.startswith('/')
                        and path.strip('/').split('/')[0] in routes):
                    bad.append('%s: %r is not a route the app declares (fy28/src/routes.ts)'
                               % (where, path))
                    continue
                mid = path
            else:
                bad.append('%s: a member is (id, why) or (path, title, why), not %r' % (where, m))
                continue
            if not (0 < len(why) <= REL.WHY_MAX) or any(ch.isdigit() for ch in why) \
                    or why.rstrip().endswith('.'):
                bad.append('%s: %s why %r: a phrase of at most %d characters, no figures, no '
                           'full stop' % (where, mid, why, REL.WHY_MAX))
            members.append(dict(id=mid, title=title, path=path, why=why))
        ids = [x['id'] for x in members]
        if len(set(ids)) != len(ids):
            bad.append('%s: a page is related to itself' % where)
        for me in members:
            if me['path'] != me['id']:          # a topic or hub: it draws the block
                for other in members:
                    if other['id'] != me['id']:
                        out.setdefault(me['id'], []).append(other)
    for pid, rs in out.items():
        seen = [r['id'] for r in rs]
        if len(set(seen)) != len(seen):
            bad.append('%s is offered the same related page twice' % pid)
        if len(rs) > REL.MAX_PER_PAGE:
            bad.append('%s has %d related pages; at most %d, or it is a second shelf'
                       % (pid, len(rs), REL.MAX_PER_PAGE))
    return out, bad


def build(strict):
    bad = REG.check()
    rel, rbad = related()
    bad += rbad
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
            ready=bool(p), generator='scripts/' + gen, related=rel.get(tid, []))
    cats = []
    for c in REG.CATEGORIES:
        h = pays.get(c['id'])
        cats.append(dict(
            id=c['id'], shelf=c['shelf'], title=c['title'], path=REG.path(c['id']),
            answer=h['answer']['text'] if h else None,
            minutes=max(1, math.ceil(words(h) / 200)) if h else None, ready=bool(h),
            groups=[dict(title=g, topics=list(ids)) for g, ids in c['groups']],
            elsewhere=[dict(href=a, title=b) for a, b in c.get('elsewhere', [])],
            start=list(c.get('start', [])), related=rel.get(c['id'], []),
            area=c.get('area'), order=c.get('order', 99)))
    out = dict(generated_by='scripts/build_topics_index.py', categories=cats, topics=topics,
               areas=[dict(id=a, title=t) for a, t in REG.AREAS])
    routes = json.dumps(sorted(c['id'] for c in cats if c['ready']), indent=1) + '\n'
    return json.dumps(out, indent=1, ensure_ascii=False, sort_keys=True) + '\n', routes, bad


def features(p):
    """What a page is BUILT FROM: its sources' addresses (fragment dropped) and its chart's
    data file. Two pages read from the same rare document are likely about related things."""
    f = {s['href'].split('#')[0] for s in p.get('sources', [])}
    ch = p.get('chart')
    if isinstance(ch, dict) and isinstance(ch.get('source'), str):
        f.add(ch['source'].split('#')[0])
    return f


def suggest_related(top=40, same_shelf=False):
    """CANDIDATES, NOT RELATIONS. Every pair of topic pages scored by the documents and
    datasets they share, each weighted by how rare it is (log of pages / pages citing it), so
    a workbook three pages read counts for far more than the model every page cites. Pairs
    already declared are left out, and so are pairs that share a shelf: the hub already lists
    them side by side, and a relation earns its place by crossing shelves. --same-shelf keeps
    them, for a shelf too long to scan.
    Nothing is accepted here: a person reads the list and adds a cluster to related.py."""
    import itertools
    pays = {}
    for tid in REG.TOPICS:
        f = os.path.join(DIR, '%s.json' % tid)
        if os.path.exists(f):
            pays[tid] = features(json.load(open(f, encoding='utf-8')))
    df = {}
    for fs in pays.values():
        for x in fs:
            df[x] = df.get(x, 0) + 1
    n = len(pays)
    rel, _ = related()
    declared = {(a, r['id']) for a, rs in rel.items() for r in rs}
    shelves = {t: set(REG.shelves_of(t)) for t in pays}
    rows = []
    for a, b in itertools.combinations(sorted(pays), 2):
        if (a, b) in declared or (not same_shelf and shelves[a] & shelves[b]):
            continue
        shared = pays[a] & pays[b]
        if not shared:
            continue
        w = {x: math.log(n / df[x]) for x in shared}
        score = sum(w.values())
        if score <= 0:
            continue
        rows.append((score, a, b, sorted(shared, key=lambda x: -w[x])))
    rows.sort(key=lambda r: -r[0])
    print('%d candidate pairs from %d pages; top %d by shared rare sources. NOT accepted --'
          ' add a cluster to scripts/topic_registry/related.py to accept one.\n' % (len(rows), n, top))
    for i, (score, a, b, shared) in enumerate(rows[:top], 1):
        ta, ha, _ = REG.TOPICS[a]
        tb, hb, _ = REG.TOPICS[b]
        print('%2d. %5.1f  %s (%s)  <->  %s (%s)' % (i, score, ta, ha, tb, hb))
        print('      %s / %s; %d shared, rarest: %s' % (a, b, len(shared), ', '.join(
            x.rsplit('/', 1)[-1] for x in shared[:3])))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--suggest-related', action='store_true')
    ap.add_argument('--same-shelf', action='store_true', help='with --suggest-related')
    a = ap.parse_args()
    if a.suggest_related:
        return suggest_related(same_shelf=a.same_shelf)
    _, rbad = related()
    if rbad:                     # a broken relation refuses to write, in either mode
        print('\n'.join(rbad))
        return 1
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
