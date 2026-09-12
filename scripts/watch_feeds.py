#!/usr/bin/env python3
"""What has APPEARED in the town's and the community's feeds since we last looked.

    python3 scripts/watch_feeds.py            # read every registered feed; record what is NEW
    python3 scripts/watch_feeds.py --check    # no network; the state holds together
    python3 scripts/watch_feeds.py --dry-run

QUEUE items 13 (community news) and 14 (sports registrations) are one mechanism with
different sources: a feed somebody else publishes, watched deterministically, and shown
as a LINK with its title, its date and who published it. Nothing is republished. TJ's
rule for both: *"Aggregate and LINK. Do not republish ... the value is the pointer plus
a sentence of context, not a copy. Attribute the source on every item."*

THE SOURCE REGISTRY is `sources/data/feed-sources.csv`: one row per feed, with a `kind`
(`town`, `district`, `sports`, `community`) the page groups by, and a `note` for a source
recorded before its feed is known -- the youth leagues, for instance, which publish on
Facebook and have no feed anybody can read. A registry row with no URL is a to-do that
the page can count, not a crawl.

DETERMINISM, as in every watcher here: the event log is the memory, an item's identity
is (source, link), and a second run on the same day writes nothing.
"""
import argparse
import csv
import datetime as dt
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(ROOT, 'sources', 'data', 'feed-sources.csv')
EVENTS = os.path.join(ROOT, 'sources', 'data', 'feed-watch-events.csv')
EVENT_COLS = ['first_seen', 'source', 'kind', 'published', 'title', 'link']
MAX_PER_SOURCE_FIRST_RUN = 10   # a brand-new source announces its latest ten, not its archive


def read_csv(path):
    if not os.path.exists(path):
        return []
    return list(csv.DictReader(open(path, newline='', encoding='utf-8')))


def write_csv(path, rows, cols):
    tmp = path + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, '') for c in cols})
    os.replace(tmp, path)


def items_of(xml_bytes):
    root = ET.fromstring(xml_bytes)
    out = []
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    for it in root.findall('.//item'):          # RSS 2.0
        pub = it.findtext('pubDate') or ''
        try:
            pub = parsedate_to_datetime(pub).date().isoformat()
        except Exception:
            pub = pub[:10]
        out.append({'title': (it.findtext('title') or '').strip(), 'link': (it.findtext('link') or '').strip(), 'published': pub})
    for e in root.findall('a:entry', ns):        # Atom
        link = e.find('a:link', ns)
        out.append({'title': (e.findtext('a:title', default='', namespaces=ns) or '').strip(),
                    'link': (link.get('href') if link is not None else '').strip(),
                    'published': (e.findtext('a:published', default='', namespaces=ns) or e.findtext('a:updated', default='', namespaces=ns) or '')[:10]})
    return [x for x in out if x['link']]


def check():
    srcs = {r['source'] for r in read_csv(SOURCES)}
    ev = read_csv(EVENTS)
    bad = [e for e in ev if e['source'] not in srcs]
    dup = len(ev) - len({(e['source'], e['link']) for e in ev})
    if bad or dup:
        print('FAIL: %d event(s) from an unregistered source; %d duplicated' % (len(bad), dup))
        return 1
    print('ok: %d feed event(s) from %d registered source(s)' % (len(ev), len(srcs)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--as-of', default=dt.date.today().isoformat())
    a = ap.parse_args()
    if a.check:
        return check()
    sources = [r for r in read_csv(SOURCES) if r.get('url')]
    if not sources:
        raise SystemExit('no feed sources with a URL in %s' % os.path.relpath(SOURCES, ROOT))
    events = read_csv(EVENTS)
    known = {(e['source'], e['link']) for e in events}
    seen_sources = {e['source'] for e in events}
    fresh = []
    for s in sources:
        try:
            req = urllib.request.Request(s['url'], headers={'User-Agent': 'Mozilla/5.0 lunenburgbudgetproject.org watcher'})
            with urllib.request.urlopen(req, timeout=45) as r:
                items = items_of(r.read())
        except Exception as e:
            print('  %-24s unreachable: %s' % (s['source'], str(e)[:80]))
            continue
        new = [i for i in items if (s['source'], i['link']) not in known]
        if s['source'] not in seen_sources:
            new = new[:MAX_PER_SOURCE_FIRST_RUN]
        print('  %-24s %d in feed, %d new' % (s['source'], len(items), len(new)))
        for i in new:
            print('    NEW  %s  %s' % (i['published'], i['title'][:80]))
            fresh.append({'first_seen': a.as_of, 'source': s['source'], 'kind': s['kind'],
                          'published': i['published'], 'title': i['title'], 'link': i['link']})
            known.add((s['source'], i['link']))
    if not fresh:
        print('nothing new in any feed')
        return 0
    if a.dry_run:
        return 0
    write_csv(EVENTS, events + fresh, EVENT_COLS)
    print('%d new item(s) recorded' % len(fresh))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
