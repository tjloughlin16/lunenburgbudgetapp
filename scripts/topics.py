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
# title, area, order, full_report, groups, optional elsewhere), GENERATOR (the script that
# writes its pages) and TOPICS ({id: title}) for the topics it is HOME to. A group may list
# a topic another category is home to: that is how one page sits on two shelves.
#
# Split from one list on 12 October 2026 so several authors -- people or agents -- can each
# add a category without rewriting a shared file (CLAUDE.md: "a generated file with several
# authors gets clobbered, not merged"). `area` groups the shelves on /reports:
AREAS = [('school', 'The schools'), ('town', 'The town'), ('options', 'Budget options')]

import importlib as _il
import pkgutil as _pk
import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import topic_registry as _reg  # noqa: E402

# NEW: a category module may also define NEW, the ids of its topics that answer a question
# NO EARLIER REPORT ANSWERED. Those, and only those, are listed under "New reports" on
# /reports and in the menu (build_reports_index.py), dated by the commit that added the
# topic's payload. TJ, 14 October 2026: "I would assume all the new stuff would show up
# under 'new reports' but it doesnt." A topic MOVED out of an old report is not new: the
# 12-13 October conversion created some two hundred topic files, and listing them by file
# date would bury the few that are. So it is declared, not inferred.
CATEGORIES, TOPICS, NEW = [], {}, set()
for _m in sorted(_pk.iter_modules(_reg.__path__), key=lambda m: m.name):
    _mod = _il.import_module('topic_registry.' + _m.name)
    CATEGORIES.append(_mod.CATEGORY)
    for _tid in getattr(_mod, 'NEW', ()):
        if _tid not in _mod.TOPICS:
            raise SystemExit('%s lists %r as NEW but is not its home' % (_m.name, _tid))
        NEW.add(_tid)
    for _tid, _title in _mod.TOPICS.items():
        if _tid in TOPICS:
            raise SystemExit('topic %r is registered by two categories' % _tid)
        # id -> (title, home category, generator that writes its payload)
        TOPICS[_tid] = (_title, _mod.CATEGORY['id'], _mod.GENERATOR)
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
    titles = {}
    for c in CATEGORIES:
        if c.get('area') not in dict(AREAS):
            bad.append('%s: area %r is not one of %s' % (c['id'], c.get('area'), [a for a, _ in AREAS]))
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
