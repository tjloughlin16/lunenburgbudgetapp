#!/usr/bin/env python3
"""Atom feeds: one per board, one for the budget feed, one for everything -- so a
resident can be told when a board gets a meeting, or when the budget feed moves,
without this project holding anybody's address.

    python3 scripts/build_feeds.py            # write fy28/public/feeds/*.xml
    python3 scripts/build_feeds.py --check    # fail if any feed no longer reproduces

TJ, 17 September 2026: "is there a way for people to get updates when something on the
site changes? I specifically want them to be able to get updates when an individual
board gets updated with a meeting, or something like the budget feed updates."

THE SUBSTRATE, NOT A CHANNEL. A feed is a static file the refresh regenerates like every
other payload. A feed reader subscribes to it directly; an RSS-to-email service
(Feedrabbit, Blogtrottr) turns it into email; Zapier or IFTTT turn it into a Slack or a
text. So one file serves every channel, and this site keeps no subscriber list -- which
is the same choice the analytics made: nothing here identifies a reader.

WHAT AN ENTRY IS -- TJ's rule, 17 September 2026: "the feed will fire after the
video+transcript+minutes are posted, and when the agenda is first posted or changed."
So a board's feed carries exactly two kinds of entry, each dated the day it happened:
  - AN AGENDA, posted or changed. The watcher records every agenda file it meets
    (meeting-watch-events.csv), and a re-posted agenda arrives under a new file id, so
    a change is a second entry for the same meeting and says so.
  - THE MEETING, COMPLETE: the recording is up, its captions are in, and our minutes are
    written. That is one entry, the day the minutes were written -- not a ping for the
    video, another for the transcript and a third for the minutes. The town's own
    minutes arriving later is not an entry; the site shows them but nobody needs to be
    woken for them.
The budget feed carries one entry per line (budget-feed.json).

An entry's id is built from the thing it describes rather than from the day, so a
reader that has seen it once does not see it twice, and a feed rebuilt tomorrow carries
the same ids. Newest first; the last FEED_DAYS days or the last FEED_MAX entries,
whichever is more.

Atom rather than RSS 2.0 because it has one date field, one id field and a defined
escaping, and every reader made since 2005 accepts it. The MIME type is
application/atom+xml, and fy28/public/_headers should keep serving it as that.
"""
import argparse
import csv
import datetime as dt
import glob
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from build_sitemap import SITE   # noqa: E402  one origin, defined once

OUT = os.path.join(ROOT, 'fy28', 'public', 'feeds')
MEETING_EVENTS = os.path.join(ROOT, 'sources', 'data', 'meeting-watch-events.csv')
MINUTES = os.path.join(ROOT, 'sources', 'data', 'recording-minutes')
BOARDS = os.path.join(ROOT, 'fy28', 'public', 'data', 'boards.json')
BUDGET = os.path.join(ROOT, 'fy28', 'public', 'data', 'budget-feed.json')
FEED_DAYS = 90
RECENT_DAYS = 45   # a meeting completed this long after it happened is news; older is backfill
FEED_MAX = 50
AUTHOR = 'The Lunenburg Budget Project'


def read_csv(p):
    return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []


def esc(s):
    return html.escape(str(s or ''), quote=True)


def nice_date(iso):
    d = dt.date.fromisoformat(iso[:10])
    return '%d %s %d' % (d.day, d.strftime('%B'), d.year)


def entry_id(*parts):
    """A tag URI (RFC 4151): stable, unique, and not a URL anybody will try to open."""
    return 'tag:lunenburgbudgetproject.org,2026:' + '/'.join(re.sub(r'[^A-Za-z0-9._-]+', '-', str(p)) for p in parts)


def board_names():
    if not os.path.exists(BOARDS):
        raise SystemExit('build_feeds: %s is missing; run build_boards.py first' % os.path.relpath(BOARDS, ROOT))
    d = json.load(open(BOARDS, encoding='utf-8'))
    return {b['slug']: b['name'] for b in d['boards']}


def board_events(names):
    """Every dated change to a board, as entries: {slug, seen, id, title, link, summary}."""
    out = []
    agendas = [e for e in read_csv(MEETING_EVENTS) if e['kind'] == 'agenda' and e['board_slug'] in names]
    agendas.sort(key=lambda e: (e['board_slug'], e['meeting_date'], e['first_seen'], e['file_id']))
    seen_meeting = set()
    for e in agendas:
        slug, key = e['board_slug'], (e['board_slug'], e['meeting_date'])
        changed = key in seen_meeting
        seen_meeting.add(key)
        out.append(dict(
            slug=slug, seen=e['first_seen'],
            id=entry_id(slug, e['meeting_date'], 'agenda', e['file_id']),
            title='%s: agenda %s for the meeting of %s' % (names[slug], 'changed' if changed else 'posted', nice_date(e['meeting_date'])),
            link=SITE + '/boards/' + slug,
            summary='The town %s the agenda for the %s meeting of %s. The agenda itself: %s'
                    % ('re-posted' if changed else 'posted', names[slug], nice_date(e['meeting_date']), e['url'])))
    # One entry per MEETING: a meeting recorded in two parts has two minutes files and
    # rings once, on the first part written.
    done = set()
    for f in sorted(glob.glob(os.path.join(MINUTES, '*', '*.json'))):
        m = json.load(open(f, encoding='utf-8'))
        slug = m.get('board_slug')
        if slug not in names or not m.get('written', {}).get('at'):
            continue
        if (slug, m['meeting_date']) in done:
            continue
        done.add((slug, m['meeting_date']))
        written = m['written']['at'][:10]
        if (dt.date.fromisoformat(written) - dt.date.fromisoformat(m['meeting_date'])).days > RECENT_DAYS:
            continue
        headline = ((m.get('minutes') or {}).get('headline') or '').strip()
        if headline and headline[-1] not in '.!?':
            headline += '.'
        page = '/meeting-minutes/%s/%s-%s' % (slug, m['meeting_date'], m['video_id'])
        out.append(dict(
            slug=slug, seen=written,
            id=entry_id(slug, m['meeting_date'], 'complete'),
            title='%s: the meeting of %s — recording, transcript and our minutes' % (names[slug], nice_date(m['meeting_date'])),
            link=SITE + page,
            summary=(headline + ' ' if headline else '') + 'The recording is on the town’s channel (%s), its captions are searchable, and our minutes are written from them; the video at its timestamp is the record.' % m.get('video_url', '')))
    return out


def budget_entries():
    if not os.path.exists(BUDGET):
        raise SystemExit('build_feeds: %s is missing; run build_budget_feed.py first' % os.path.relpath(BUDGET, ROOT))
    d = json.load(open(BUDGET, encoding='utf-8'))
    out = []
    for e in d['entries']:
        page = e.get('page') or '/budget-feed'
        out.append(dict(
            slug='budget', seen=e['date'],
            id=entry_id('budget', e['board_slug'], e['date'], e['kind'], e.get('t') or e.get('file_id') or re.sub(r'\W+', '-', e['text'])[:60]),
            title='%s — %s: %s' % (e['board'], e['kind'], e['text']),
            link=(SITE + page) if page.startswith('/') else page,
            summary='%s, %s. %s' % (e['board'], nice_date(e['date']), e.get('detail') or '')))
    return out


def window(entries):
    entries.sort(key=lambda e: (e['seen'], e['id']), reverse=True)
    if not entries:
        return []
    cutoff = (dt.date.fromisoformat(entries[0]['seen']) - dt.timedelta(days=FEED_DAYS)).isoformat()
    kept = [e for e in entries if e['seen'] >= cutoff]
    return kept if len(kept) >= FEED_MAX else entries[:FEED_MAX]


def atom(feed_id, title, subtitle, self_path, alt_path, entries):
    updated = (entries[0]['seen'] if entries else '2026-01-01') + 'T00:00:00Z'
    lines = ['<?xml version="1.0" encoding="utf-8"?>',
             '<feed xmlns="http://www.w3.org/2005/Atom">',
             '  <title>%s</title>' % esc(title),
             '  <subtitle>%s</subtitle>' % esc(subtitle),
             '  <id>%s</id>' % esc(feed_id),
             '  <link rel="self" type="application/atom+xml" href="%s"/>' % esc(SITE + self_path),
             '  <link rel="alternate" type="text/html" href="%s"/>' % esc(SITE + alt_path),
             '  <updated>%s</updated>' % updated,
             '  <author><name>%s</name></author>' % esc(AUTHOR),
             '  <generator>scripts/build_feeds.py</generator>']
    for e in entries:
        lines += ['  <entry>',
                  '    <id>%s</id>' % esc(e['id']),
                  '    <title>%s</title>' % esc(e['title']),
                  '    <link rel="alternate" href="%s"/>' % esc(e['link']),
                  '    <updated>%sT00:00:00Z</updated>' % e['seen'][:10],
                  '    <summary>%s</summary>' % esc(e['summary'].strip()),
                  '  </entry>']
    lines.append('</feed>')
    return '\n'.join(lines) + '\n'


def build():
    names = board_names()
    events = board_events(names)
    feeds = {}
    for slug, name in sorted(names.items()):
        mine = [e for e in events if e['slug'] == slug]
        if not mine:
            continue
        feeds['%s.xml' % slug] = atom(entry_id('feed', slug), '%s — Lunenburg Budget Project' % name,
                                      'When an agenda is posted or changed, and when a meeting’s recording, transcript and our minutes are all in.',
                                      '/feeds/%s.xml' % slug, '/boards/' + slug, window(mine))
    feeds['budget.xml'] = atom(entry_id('feed', 'budget'), 'The budget feed — Lunenburg Budget Project',
                               'Everything budget-related across every board, as it goes on the record.',
                               '/feeds/budget.xml', '/budget-feed', window(budget_entries()))
    feeds['all.xml'] = atom(entry_id('feed', 'all'), 'Every board — Lunenburg Budget Project',
                            'Every change to every board, as the refresh sees it.',
                            '/feeds/all.xml', '/boards', window(list(events)))
    return feeds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    feeds = build()
    if a.check:
        stale = [n for n, body in feeds.items()
                 if not os.path.exists(os.path.join(OUT, n)) or open(os.path.join(OUT, n), encoding='utf-8').read() != body]
        extra = [os.path.basename(p) for p in glob.glob(os.path.join(OUT, '*.xml')) if os.path.basename(p) not in feeds]
        if stale or extra:
            print('STALE feeds: %s%s — run build_feeds.py' % (', '.join(stale), (' (and %s no longer produced)' % ', '.join(extra)) if extra else ''))
            return 1
        print('ok — %d feeds reproduce' % len(feeds))
        return 0
    os.makedirs(OUT, exist_ok=True)
    for p in glob.glob(os.path.join(OUT, '*.xml')):
        if os.path.basename(p) not in feeds:
            os.remove(p)
    for n, body in feeds.items():
        with open(os.path.join(OUT, n), 'w', encoding='utf-8') as fh:
            fh.write(body)
    n_entries = sum(body.count('<entry>') for body in feeds.values())
    print('%s: %d feeds, %d entries; budget.xml %d, all.xml %d'
          % (os.path.relpath(OUT, ROOT), len(feeds), n_entries, feeds['budget.xml'].count('<entry>'), feeds['all.xml'].count('<entry>')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
