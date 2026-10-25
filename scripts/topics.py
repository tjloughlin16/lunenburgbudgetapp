#!/usr/bin/env python3
"""THE REGISTRY OF TOPIC PAGES: which categories exist, which pages are in each, what each
is called, and where it lives. The one place a page's existence is decided.

WHY. TJ, 12 October 2026: *"nobody will ever read these full reports... we need to break
up all these long reports into smaller pages everywhere"* -- starting with athletics and
transportation, as "a model that makes sense and we can replicate". An inventory of the
site found the same questions answered in three to seven places each (athletic buses
moving from fees to the town: seven). So splitting is also DEDUPLICATING: every question
gets exactly one page, and every other place links to it.

THE MODEL.
    category      a shelf on /reports, and a hub page at /<category>
    hub           the matrix of facts, the conclusions, a card per topic   (~3 min)
    topic         one question, one chart, two to four conclusions         (< 5 min)
    shared topic  ONE address, listed on every shelf it belongs to -- never two copies
    reference     year-by-year tables, what was said, method, sources

TITLES ARE DESCRIPTIVE, NOT QUESTIONS AND NOT FINDINGS. TJ: *"i dont like the question
format... we need a more clear title. a more direct title."* A title is the subject in
two to four words; the line under it -- the payload's `finding` -- is what it shows.
Descriptive titles scan in a list and do not go stale when a number moves.

A topic's address is /<home>/<id>; `home` is the category it belongs to first. A topic
listed on another shelf keeps that one address.
"""

# ONE FILE PER CATEGORY, in scripts/topic_registry/. Each defines CATEGORY (id, shelf,
# title, area, order, full_report, groups, optional elsewhere, optional start), GENERATOR (the script that
# writes its pages), optional TOPIC_GENERATORS ({id: script} for a topic another script
# writes) and TOPICS ({id: title}) for the topics it is HOME to. A group may list
# a topic another category is home to: that is how one page sits on two shelves.
#
# Split from one list on 12 October 2026 so several authors -- people or agents -- can each
# add a category without rewriting a shared file (CLAUDE.md: "a generated file with several
# authors gets clobbered, not merged"). `area` groups the shelves on /reports:
AREAS = [('school', 'The schools'), ('town', 'The town'), ('options', 'Budget options'),
         # SPECIAL REPORTS: one-off reports for a decision or a moment, at the bottom of the menu
         # and of /reports, each with an `archive_after` date past which it leaves the menu and
         # moves to the archive on /reports (TJ, 24 October 2026: "reports that wont stay on the
         # menu forever at a high level and will eventually go into an archive").
         ('special', 'Special reports')]

import importlib as _il
import re
import pkgutil as _pk
import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import topic_registry as _reg  # noqa: E402

CATEGORIES, TOPICS = [], {}
for _m in sorted(_pk.iter_modules(_reg.__path__), key=lambda m: m.name):
    if _m.name == 'related':          # relations between pages, not a shelf (topic_registry/related.py)
        continue
    _mod = _il.import_module('topic_registry.' + _m.name)
    CATEGORIES.append(_mod.CATEGORY)
    for _tid, _title in _mod.TOPICS.items():
        if _tid in TOPICS:
            raise SystemExit('topic %r is registered by two categories' % _tid)
        # id -> (title, home category, generator that writes its payload). A category's
        # topics are written by its GENERATOR unless `TOPIC_GENERATORS` names another script
        # for one of them -- a shelf can gain pages built from a different source without its
        # first generator having to read that source.
        TOPICS[_tid] = (_title, _mod.CATEGORY['id'],
                        getattr(_mod, 'TOPIC_GENERATORS', {}).get(_tid, _mod.GENERATOR))
CATEGORIES.sort(key=lambda c: (c.get('order', 99), c['id']))
HUB_GENERATOR = {c['id']: _il.import_module('topic_registry.' + c['id'].replace('-', '_')).GENERATOR
                 for c in CATEGORIES}


def category(cid):
    return next(c for c in CATEGORIES if c['id'] == cid)


def path(tid):
    """The one address of a topic, or of a hub when given a category id."""
    if any(c['id'] == tid for c in CATEGORIES):
        return '/' + tid
    return '/%s/%s' % (TOPICS[tid][1], tid)


def shelves_of(tid):
    """Every category a topic is listed under, its home first."""
    home = TOPICS[tid][1]
    rest = [c['id'] for c in CATEGORIES
            if c['id'] != home and any(tid in ids for _, ids in c['groups'])]
    return [home] + rest


def check():
    """Every listed topic is registered, every registered topic is listed at home, and no
    topic appears twice on one shelf."""
    bad = []
    for c in CATEGORIES:
        seen = [t for _, ids in c['groups'] for t in ids]
        for t in seen:
            if t not in TOPICS:
                bad.append('%s lists %r, which is not registered' % (c['id'], t))
        if len(set(seen)) != len(seen):
            bad.append('%s lists a topic twice' % c['id'])
        # `start`: the pages a reader of this hub should open first -- the most insightful,
        # called out above everything else (TJ, 19 October 2026). Each must be on the shelf.
        for t in c.get('start', []):
            if t not in seen:
                bad.append('%s: start page %r is not listed on the shelf' % (c['id'], t))
        if len(c.get('start', [])) > 3:
            bad.append('%s: more than three start pages is a second index, not a callout'
                       % c['id'])
    titles = {}
    for c in CATEGORIES:
        if c.get('area') not in dict(AREAS):
            bad.append('%s: area %r is not one of %s' % (c['id'], c.get('area'), [a for a, _ in AREAS]))
        aa = c.get('archive_after')
        if (c.get('area') == 'special') != bool(aa):
            bad.append('%s: a special report, and only one, carries archive_after' % c['id'])
        if aa and not re.fullmatch(r'\d{4}-\d\d-\d\d', aa):
            bad.append('%s: archive_after %r is not an ISO date' % (c['id'], aa))
        for name in (c['title'], c['shelf']):
            if name.rstrip().endswith(('?', '.')) or len(name.split()) > 5:
                bad.append('%s: %r reads as a sentence -- a title is the subject in 2-4 words'
                           % (c['id'], name))
    for t, (title, _, _) in TOPICS.items():
        if title.rstrip().endswith(('?', '.')) or len(title.split()) > 5:
            bad.append('%s: %r reads as a sentence -- a title is the subject in 2-4 words'
                       % (t, title))
        titles.setdefault(title.lower(), []).append(t)
    bad += ['two topics share the title %r: %s' % (k, v) for k, v in titles.items() if len(v) > 1]
    for t, (_, home, _) in TOPICS.items():
        if not any(t in ids for _, ids in category(home)['groups']):
            bad.append('%r is not listed on its home shelf %r' % (t, home))
    return bad


if __name__ == '__main__':
    import sys
    b = check()
    print('\n'.join(b) or 'topics: %d categories, %d topics' % (len(CATEGORIES), len(TOPICS)))
    sys.exit(1 if b else 0)
