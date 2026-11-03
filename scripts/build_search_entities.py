#!/usr/bin/env python3
"""The curated things a search should find FIRST: every page we built, by its name.

    python3 scripts/build_search_entities.py           # write fy28/public/data/search-entities.json
    python3 scripts/build_search_entities.py --check   # fail if the file no longer reproduces

TJ, 3 November 2026: *"a search for a name (it shows up in staff lists, etc) should
automatically bring up the staffing profile. type in a keyword that is close to a report
title, shows the report ... we have pre-packaged highly valuable pages crafted and built for
important concepts. we should try to funnel people into the curated pages vs the raw pages
(minutes) when we detect its likely ... anything that seems to hit a contract page should be
suggested first."*

WHY A SEPARATE LIST, AND NOT BETTER RANKING INSIDE THE FULL-TEXT INDEX. The full-text index
ranks by how often the words appear in a page's BODY. A person's profile says their name
once; a year of Select Board minutes says it forty times. A hub called "Free cash" is a
short page; a budget workbook prints "free cash" on every tab. So bm25 is right about the
text and wrong about what the reader came for, and no weighting of it fixes that: the
question "is there a page NAMED for this?" is a question about names, not bodies.

So this is a list of NAMES -- every page this project built for a concept, every person
with a profile, every board, department, budget line, fund and contract -- each with the
words it answers to. /api/search matches the query against it in memory (functions/api/
_entities.js) and returns the matches as `best`, above every corpus. It reads ZERO rows of
D1: the list is a static file the function fetches once per isolate.

WHAT EACH ENTRY ANSWERS TO, AND WHO DECIDED IT
  * its TITLE, as the page itself is called (routes.ts LABEL, topics.json, reports.json ...)
  * its ALIASES -- the addresses routes.ts already accepts for it (ALIASES, TOPIC_ALIASES),
    spelled as words. Somebody decided those are what people type; we reuse the decision.
  * its KEYWORDS -- the hand-written tags in sources/data/search-affinity.csv for that page,
    and sources/data/search-entity-aliases.csv, a short list kept for searches that failed.
    Keywords match at a discount and are labelled as ours on the result.

WHAT IS LEFT OUT
  * UNLISTED pages (routes.ts UNLISTED, sources/analyses/UNLISTED): reachable only by
    somebody given the address. A search result is a door, and they have none on purpose.
  * Meeting pages, raw documents (except contracts and the annual town reports, which ARE
    the thing asked for), and anything not already published at its own address.

PRIVACY. People come from people.json, the same list /people/<slug> renders and the `person`
corpus already indexes -- names as the org charts print them, a role, a unit, a year. No
contact detail, nothing about children or families (notes/process/DATA-PRIVACY.md). The
same name is not proven to be one person, and the result says so.
"""
import argparse
import csv
import glob
import html
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, 'fy28', 'public')
DATA = os.path.join(PUB, 'data')
ROUTES_TS = os.path.join(ROOT, 'fy28', 'src', 'routes.ts')
OUT = os.path.join(DATA, 'search-entities.json')
AFFINITY = os.path.join(ROOT, 'sources', 'data', 'search-affinity.csv')
HAND = os.path.join(ROOT, 'sources', 'data', 'search-entity-aliases.csv')
CONTRACTS = os.path.join(ROOT, 'sources', 'contracts', 'index.csv')
UNLISTED_ANALYSES = os.path.join(ROOT, 'sources', 'analyses', 'UNLISTED')

# The order a kind is preferred in when two score alike: a page built to answer a question
# before a profile, a profile before a row of the budget. functions/api/_entities.js reads
# the weight off each entry, so this table is the only place it is set.
KIND_WEIGHT = {
    'hub': 1.0, 'report': 0.97, 'topic': 0.96, 'page': 0.94, 'contract': 0.95,
    'person': 0.95, 'board': 0.94, 'department': 0.92, 'annual': 0.9,
    'line': 0.86, 'fund': 0.88, 'function': 0.8, 'post': 0.85,
}


OFFICE_WORD = re.compile(r'\b(assistant|manager|insurance|clerk|treasurer|director|administrative|'
                         r'coordinator|department|office|secretary|town|school|staff|position|vacant)\b', re.I)


def load(path):
    return json.load(io.open(path, encoding='utf-8'))


def words(slug):
    """An address as the words it spells: `teaching-assistants` -> `teaching assistants`."""
    return ' '.join(slug.replace('_', '-').split('-')).strip()


def routes():
    """SLUG, LABEL, ALIASES, TOPIC_ALIASES and UNLISTED, read out of routes.ts the way
    build_sitemap.py and prerender.mjs read it."""
    src = io.open(ROUTES_TS, encoding='utf-8').read()

    def table(name):
        m = re.search(r'(?:export )?const %s: Record<[^>]+> = \{(.*?)\n\}' % name, src, re.S)
        if not m:
            raise SystemExit('routes.ts: could not find %s' % name)
        body = re.sub(r'//[^\n]*', '', m.group(1))
        pairs = re.findall(r"(?:'([^']+)'|([A-Za-z]+))\s*:\s*'([^']*)'", body)
        return {(a or b): v for a, b, v in pairs}

    u = re.search(r"export const UNLISTED[^\n]*new Set<Tab>\(\[([^\]]*)\]", src)
    unlisted = set(re.findall(r"'([a-z]+)'", u.group(1))) if u else set()
    return table('SLUG'), table('LABEL'), table('ALIASES'), table('TOPIC_ALIASES'), unlisted


class Registry:
    def __init__(self):
        self.by_url = {}

    def add(self, kind, title, url, sub='', aliases=(), keywords=()):
        title = ' '.join((title or '').split())
        if not title or not url:
            return
        e = self.by_url.get(url)
        if e is None:
            e = self.by_url[url] = {'k': kind, 't': title, 'u': url, 's': sub, 'a': [], 'w': []}
        elif KIND_WEIGHT[kind] > KIND_WEIGHT[e['k']]:
            # A hub that took a page's address is the hub: keep the stronger kind and name,
            # and keep the weaker name as an alias so either finds it.
            e['a'].append(e['t'])
            e.update(k=kind, t=title, s=sub or e['s'])
        elif title.lower() != e['t'].lower():
            e['a'].append(title)
        for a in aliases:
            a = ' '.join(a.split())
            if a and a.lower() != e['t'].lower():
                e['a'].append(a)
        for w in keywords:
            w = ' '.join(w.split())
            if w:
                e['w'].append(w)

    def entities(self):
        out = []
        for e in self.by_url.values():
            seen, a = {e['t'].lower()}, []
            for x in e['a']:
                if x.lower() not in seen:
                    seen.add(x.lower()); a.append(x)
            w = []
            for x in e['w']:
                if x.lower() not in seen:
                    seen.add(x.lower()); w.append(x)
            row = {'k': e['k'], 't': e['t'], 'u': e['u']}
            if e['s']:
                row['s'] = e['s']
            if a:
                row['a'] = a
            if w:
                row['w'] = w
            out.append(row)
        return sorted(out, key=lambda r: (r['k'], r['u']))


def build():
    reg = Registry()
    slug, label, aliases, topic_aliases, unlisted = routes()

    # 1. HUBS AND TOPIC PAGES, as the shelves name them.
    topics = load(os.path.join(DATA, 'topics.json'))
    for c in topics.get('categories', []):
        if c.get('ready') is False or c.get('merged_into'):
            continue
        reg.add('hub', c.get('title') or words(c['id']), c['path'], 'Hub', aliases=[words(c['id'])])
    for t in topics.get('topics', {}).values():
        if not t.get('ready'):
            continue
        reg.add('topic', t['title'], t['path'], 'Topic page', aliases=[words(t['id'])])
    for a, target in topic_aliases.items():
        path = '/' + target
        hit = [p for p in reg.by_url if p == path or p.endswith('/' + target)]
        if hit:
            reg.add(reg.by_url[hit[0]]['k'], reg.by_url[hit[0]]['t'], hit[0], aliases=[words(a)])

    # 2. TOP-LEVEL PAGES, by the label routes.ts gives them, and every address they answer to.
    tab_url = {}
    for tab, s in slug.items():
        # `topic` is the topic page TYPE; its slug is a placeholder, not a page.
        if not s or tab in unlisted or tab not in label or tab == 'topic':
            continue
        tab_url[tab] = '/' + s
        name = label[tab].split(' — ')[0]
        reg.add('page', name, '/' + s, 'Page', aliases=[label[tab], words(s)])
    for a, tab in aliases.items():
        if tab not in tab_url:
            continue
        # A ONE-WORD ADDRESS IS A KEYWORD, NOT A NAME. `/budget` opens Build your own budget and
        # `/rates` the curve, because a link once said so -- but a reader searching `budget`
        # or `rates` is not asking for either page. Several words (`teaching-assistants`), or
        # a word the title already holds, are names; a lone word matches at a discount.
        w = words(a)
        named = ' ' in w or w.lower() in label[tab].lower()
        reg.add('page', label[tab].split(' — ')[0], tab_url[tab],
                aliases=[w] if named else [], keywords=[] if named else [w])

    # 3. REPORTS, as /reports lists them -- minus the unlisted analyses.
    hidden = set()
    if os.path.exists(UNLISTED_ANALYSES):
        hidden = {l.strip() for l in io.open(UNLISTED_ANALYSES, encoding='utf-8')
                  if l.strip() and not l.startswith('#')}
    rep = load(os.path.join(DATA, 'reports.json'))
    for g in ('reports', 'pages', 'finance'):
        for r in rep.get(g) or []:
            if not isinstance(r, dict) or not r.get('url'):
                continue
            if r.get('id') in hidden and r['url'].startswith('/analysis/'):
                continue
            reg.add('report' if g == 'reports' else 'page', r['title'].split(' — ')[0], r['url'],
                    'Report' if g == 'reports' else 'Page', aliases=[r['title']])

    # 3b. THE REFERENCE PAGES (build_reference_pages.py), by their own <title>. Served as
    #     /reference/<name>.html; the page corpus cites them without the extension.
    for f in sorted(glob.glob(os.path.join(PUB, 'reference', '*.html'))):
        m = re.search(r'<title>(.*?)</title>', io.open(f, encoding='utf-8').read(), re.S)
        if m:
            t = html.unescape(re.sub(r'\s+', ' ', m.group(1))).split(' — Lunenburg')[0].strip()
            reg.add('page', t, '/reference/' + os.path.basename(f)[:-len('.html')], 'Reference')

    # 4. BOARDS AND DEPARTMENTS.
    for b in load(os.path.join(DATA, 'boards.json')).get('boards', []):
        reg.add('board', b['name'], '/boards/' + b['slug'], 'Board', aliases=[words(b['slug'])])
    fin = load(os.path.join(DATA, 'finance.json'))
    owners = fin.get('owners', {})
    for d in fin.get('departments', []):
        if d['slug'] in owners:
            reg.add('department', d['name'], '/departments/' + d['slug'], 'Town department')

    # 5. THE SCHOOL BUDGET, line by line, fund by fund (fy-breakdown/index.json).
    fy = load(os.path.join(DATA, 'fy-breakdown', 'index.json'))
    for x in fy.get('lines', []):
        # `Instr Serv Director Salary · Instr Serv Director Salaries` -- the line, then its group.
        head = x['name'].split(' · ')
        reg.add('line', head[0], '/school-lines/' + x['slug'],
                'School budget line' + (' · ' + head[1] if len(head) > 1 else ''), aliases=head[1:2])
    for x in fy.get('funds', []):
        reg.add('fund', x['name'], '/school-funds/' + x['slug'], 'School fund · ' + x.get('cat', ''))
    for x in fy.get('groups', []):
        reg.add('fund', x['name'], '/school-groups/' + x['slug'], 'School budget group')
    fp = os.path.join(DATA, 'fy-breakdown', 'functions.json')
    if os.path.exists(fp):
        for x in load(fp).get('functions', []):
            if x['code'] != '0000':
                reg.add('function', x['name'], '/school-functions/' + x['code'],
                        'School function code ' + x['code'])

    # 6. CONTRACTS: the agreements themselves. A contract document IS what a reader asking for
    #    the contract wants, so it is a named thing here, not a raw document. TJ: "anything
    #    that seems to hit a contract page should be suggested first."
    for r in csv.DictReader(io.open(CONTRACTS, encoding='utf-8')):
        path = r.get('local') or r.get('text') or ''
        if not path.startswith('sources/'):
            continue
        lab = r['label']
        # The part before the dash is the name; the rest is the description.
        name, _, rest = lab.partition(' — ')
        name = re.sub(r',\s*(as filed with DESE|the union.s .*|from the .*)$', '', name)
        # Answers to `<name> contract` as well: the town's papers call most of these an
        # AGREEMENT or an MOA, and a reader types `custodian contract`.
        reg.add('contract', name, '/docs/' + path[len('sources/'):], 'Contract' + (' · ' + rest if rest else ''),
                aliases=[name + ' contract'])

    # 7. THE ANNUAL TOWN REPORTS, a year each.
    for d in load(os.path.join(DATA, 'annual-reports.json')).get('documents', []):
        if d.get('addendum'):
            continue
        reg.add('annual', 'Annual town report %s' % d['fy'], d['url'], 'The town’s annual report, %s' % d['fy'],
                aliases=['town report %s' % d['fy']])

    # 8. PEOPLE WITH A PROFILE.
    for p in load(os.path.join(DATA, 'people.json')).get('people', []):
        # A ROSTER LINE THAT NAMES A POST, NOT A PERSON -- `Health Insurance`, `Administrative
        # Assistant`, `Assistant Town Manager` -- has a profile page today (a defect upstream,
        # in build_people.py) and no role. As a search result it would answer `health
        # insurance` with a person, so it is left out here.
        if not p.get('role') and OFFICE_WORD.search(p['name']):
            continue
        sub = ', '.join(x for x in (p.get('role'), p.get('unit')) if x and x != 'officer')
        reg.add('person', p['name'], '/people/' + p['slug'],
                (sub + (', FY%s' % p['fy'] if p.get('fy') else '')) or 'Person')

    # 9. POSTS.
    for p in load(os.path.join(DATA, 'blog.json')).get('posts', []):
        if p.get('slug') and p.get('title'):
            reg.add('post', p['title'], '/blog/' + p['slug'], 'Blog post')

    # 10. KEYWORDS: the hand-written affinity tags for pages, then our own short list.
    for r in csv.DictReader(io.open(AFFINITY, encoding='utf-8')):
        if not r['doc_key'].startswith('page:'):
            continue
        key = r['doc_key'][len('page:'):]
        route = '/' if key == 'home' else '/' + key
        # A page that has since moved is tagged under its old address: follow routes.ts.
        if route not in reg.by_url and key in aliases and aliases[key] in tab_url:
            route = tab_url[aliases[key]]
        elif route not in reg.by_url and key in topic_aliases:
            route = '/' + topic_aliases[key]
        elif route not in reg.by_url:
            # The page was unlisted when a hub absorbed it, and the hub took the tab's id:
            # /parks-and-recreation (tab `parks`) became the Parks hub at /parks. Its tags
            # describe the hub's subject, so they follow it there.
            tab = next((t for t, sl in slug.items() if sl == key), None)
            if tab and '/' + tab in reg.by_url:
                route = '/' + tab
        if route in reg.by_url:
            e = reg.by_url[route]
            reg.add(e['k'], e['t'], route, keywords=[t for t in r['tags'].split(';') if not re.search(r'\d', t)])
    if os.path.exists(HAND):
        for r in csv.DictReader(io.open(HAND, encoding='utf-8')):
            u = r['url'].strip()
            if u not in reg.by_url:
                raise SystemExit('search-entity-aliases.csv names %s, which no curated page has' % u)
            e = reg.by_url[u]
            reg.add(e['k'], e['t'], u, keywords=[t for t in r['words'].split(';')])

    ents = reg.entities()
    counts = {}
    for e in ents:
        counts[e['k']] = counts.get(e['k'], 0) + 1
    return {
        'generated_by': 'scripts/build_search_entities.py',
        'about': 'Every curated page by its name: hubs, topic pages, reports, pages, boards, '
                 'departments, school budget lines and funds, contracts, the annual town reports, '
                 'people with a profile and posts. /api/search matches a query against these names '
                 'and returns the matches as `best`, ahead of the full-text results. `a` are the '
                 'addresses routes.ts accepts, as words; `w` are hand-written keywords (ours).',
        'weights': KIND_WEIGHT,
        'counts': dict(sorted(counts.items())),
        'entities': ents,
    }


def render(payload):
    return json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    text = render(build())
    if a.check:
        cur = io.open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        if cur != text:
            print('search-entities.json is stale -- run scripts/build_search_entities.py', file=sys.stderr)
            return 1
        print('search-entities.json reproduces (%d entities)' % len(json.loads(text)['entities']))
        return 0
    tmp = OUT + '.tmp'
    io.open(tmp, 'w', encoding='utf-8').write(text)
    os.replace(tmp, OUT)
    d = json.loads(text)
    print('wrote %s -- %d entities: %s' % (os.path.relpath(OUT, ROOT), len(d['entities']),
          ', '.join('%s %d' % kv for kv in d['counts'].items())))
    return 0


if __name__ == '__main__':
    sys.exit(main())
