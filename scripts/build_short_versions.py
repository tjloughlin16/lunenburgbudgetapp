#!/usr/bin/env python3
"""Every page, and the points its short version asks a reader to leave with.

    python3 scripts/build_short_versions.py           # write notes/generated/SHORT-VERSIONS.md + short-versions.csv
    python3 scripts/build_short_versions.py --check   # fail if either no longer reproduces

TJ, 16 September 2026: "create a table (and maybe even a full spreadsheet) of every page
we have, and the short form 3 points or the major conclusions/points of each that readers
should take away from it."

READ OFF THE BUILD, NOT OFF THE SOURCE. The points are extracted from the `data-short`
region of each prerendered page in fy28/dist -- the same region the on-page indicator
measures and scripts/build_reading_time.py budgets -- so the table says what the page
actually shows a reader, not what a payload holds or a page component intends. A page
whose short version is a Conclusions block yields its claims and their headline figures;
the crisis page yields its five claims; /solutions yields its six takeaways; a markdown
analysis yields the paragraphs of its first section. Nothing here is typed (rule 2).

What counts as a POINT: a heading inside the short version, a claim line (a bold or
semibold paragraph of card size), or a list item that opens in bold. The label spans
("What it rests on", "What it does not show") are not points and are dropped. The
headline figure beside a claim is carried in its own column.

Two outputs from one pass, one for reading and one for a spreadsheet:

    notes/generated/SHORT-VERSIONS.md     one table, every page, points as a list
    notes/generated/short-versions.csv    one row per page: route, title, kind,
                                          short_minutes, points (joined with " | "),
                                          figures, and point_1..point_N as columns

Sorted the way a reader meets the site: the front page's doors first, then the areas.
"""
import argparse
import csv
import html
import io
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, 'fy28', 'dist')
OUT_MD = os.path.join(ROOT, 'notes', 'generated', 'SHORT-VERSIONS.md')
OUT_CSV = os.path.join(ROOT, 'notes', 'generated', 'short-versions.csv')
READING = os.path.join(ROOT, 'notes', 'generated', 'reading-time.csv')

# Label spans and boilerplate that sit inside a short version but are not points.
NOT_A_POINT = re.compile(
    r'^(what it rests on|what it does not show|what this does not show|finding \d+|'
    r'how this was worked out|hypothesis|short version|on this page|read the |'
    r'\d{2}\s*(projected|on the record|record and projection)?)$', re.I)
CLAIM_CLASS = re.compile(r'\b(font-bold|font-semibold)\b')
FIGURE_CLASS = re.compile(r'\btext-(xl|2xl|3xl)\b')
LABEL_CLASS = re.compile(r'\buppercase\b')


GENERIC_HEADING = re.compile(
    r'^(if you read nothing else|what (this|we) (page )?(establish|found|now hold)\w*|what the \w+ years say|'
    r'the story in \d+ figures|in plain terms|the short version|what is in it|where things stand.*)$', re.I)
NUMERIC = re.compile(r'^[\s$€£+\-−~≈]*[\d.,]+\s*(%|×|x|k|M|FTE|pts|yr|min|a year)?\s*$', re.I)
CARD_CLASS = re.compile(r'(^|\s)card(\s|$)')


class Points(HTMLParser):
    """Walk one page; inside any `data-short` element, collect points and figures.

    A point found inside a `.card` is prefixed with that card's headline figure -- the
    Insight and Conclusions cards set the number above a claim that reads as a fragment
    on its own ("Of the schools' health insurance is not in the school budget at all")."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.stack = []           # (tag, is_short, kind, is_card)
        self.buf = None
        self.points = []
        self.figures = []
        self.cards = []           # open cards: {'figure': str|None, 'points': []}
        self.in_body = 0          # inside a markdown .report-body
        self.paras = []           # every paragraph's first sentence, the fallback
        self.figrows = []         # "value label" lines from figure rows, the fallback for figure-only short versions
        self.lists = []           # open list tags, so a bold list item counts only in an <ol>
        self.row = None           # (texts) while inside a figure row

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get('class', '')
        if 'data-short' in a:
            self.depth += 1
        is_card = self.depth > 0 and bool(CARD_CLASS.search(cls))
        if is_card:
            self.cards.append({'figure': None, 'points': []})
        if self.depth > 0 and 'report-body' in cls:
            self.in_body += 1
        if tag in ('ol', 'ul'):
            self.lists.append(tag)
        is_row = self.depth > 0 and tag == 'div' and 'items-baseline' in cls and self.row is None
        if is_row:
            self.row = []
        elif self.row is not None:
            self.row.append(' ')
        kind = None
        if self.depth > 0 and self.buf is None:
            if tag in ('h2', 'h3', 'h4'):
                kind = 'point'
            elif tag == 'p' and CLAIM_CLASS.search(cls) and not LABEL_CLASS.search(cls):
                kind = 'point'
            elif tag == 'p' or (tag == 'li' and self.in_body):
                kind = 'para'
            elif tag == 'strong' and self.stack and self.stack[-1][0] == 'li' and self.lists and self.lists[-1] == 'ol':
                kind = 'point'
            elif tag in ('span', 'div') and FIGURE_CLASS.search(cls) and 'tnum' in cls:
                kind = 'figure'
        if kind:
            self.buf = (kind, [])
        self.stack.append((tag, 'data-short' in a, kind, is_card, self.depth > 0 and 'report-body' in cls, is_row))

    def handle_data(self, data):
        if self.buf is not None:
            self.buf[1].append(data)
        if self.row is not None:
            self.row.append(data)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs); self.handle_endtag(tag)

    def emit(self, kind, text):
        if kind == 'para':
            # First sentence -- but "1. Lunenburg paid ..." is a numbered claim, not a
            # one-character sentence, so a period straight after a lone digit does not end one.
            first = re.split(r'(?<!\b\d\.)(?<=[.!?])\s', text, 1)[0]
            if first and not NUMERIC.match(first) and len(first) > 20:
                self.paras.append(first)
            if not self.in_body:
                return
            text = first
        if not text or NOT_A_POINT.match(text) or GENERIC_HEADING.match(text):
            return
        if kind in ('point', 'para') and NUMERIC.match(text):
            kind = 'figure'
        if kind == 'figure':
            self.figures.append(text)
            if self.cards and self.cards[-1]['figure'] is None:
                self.cards[-1]['figure'] = text
            return
        if self.cards:
            self.cards[-1]['points'].append(text)
        else:
            self.points.append(text)

    def handle_endtag(self, tag):
        while self.stack:
            t, was_short, kind, is_card, is_body, is_row = self.stack.pop()
            if t in ('ol', 'ul') and self.lists:
                self.lists.pop()
            if is_row and self.row is not None:
                line = re.sub(r'\s+', ' ', ''.join(self.row)).strip()
                if line and not NUMERIC.match(line):
                    self.figrows.append(line)
                self.row = None
            if kind and self.buf is not None:
                self.emit(self.buf[0], re.sub(r'\s+', ' ', ''.join(self.buf[1])).strip())
                self.buf = None
            if is_card and self.cards:
                c = self.cards.pop()
                for p in c['points']:
                    fig = c['figure']
                    self.points.append(p if not fig or fig.lower() in p.lower() else '%s — %s' % (fig, p))
            if is_body:
                self.in_body -= 1
            if was_short:
                self.depth -= 1
            if t == tag:
                break


def dedupe(xs):
    seen, out = set(), []
    for x in xs:
        k = x.lower()
        if k not in seen:
            seen.add(k); out.append(x)
    return out


def rows():
    rt = {r['route']: r for r in csv.DictReader(open(READING, encoding='utf-8'))}
    out = []
    for route, r in rt.items():
        path = os.path.join(DIST, (route.strip('/') or 'index') + '.html')
        if not os.path.exists(path):
            continue
        p = Points()
        p.feed(open(path, encoding='utf-8', errors='replace').read())
        points = dedupe(p.points)
        # A short version made of figures alone (the story page) or of plain prose (four
        # sentences) has no claim lines; fall back to the figure rows, then the paragraphs.
        if len(points) < 3 and p.figrows:
            points = dedupe(points + p.figrows)
        if len(points) < 3 and p.paras:
            points = dedupe(points + p.paras)[:6]
        figures = dedupe(p.figures)
        out.append({
            'route': route,
            'title': r['title'],
            'kind': r['kind'],
            'short_minutes': r['short_minutes'],
            'full_minutes': r['minutes'],
            'points': points,
            'figures': figures,
        })
    return out


AREA_ORDER = ['Home', 'Start here', 'How the money moves', 'Reports and analyses']


def sort_key(r):
    crumb = r['route']
    order = {'/': 0, '/crisis': 1, '/solutions': 2, '/straight-answers': 3, '/bend-the-curve': 4,
             '/what-solved-requires': 5, '/overrides': 6, '/the-situation': 7, '/the-money': 8,
             '/one-big-report': 9}
    return (order.get(crumb, 50), 0 if r['kind'] == 'page' else 1, crumb)


def render_md(rs):
    lines = ['# Every page, and what a reader should leave with', '',
             'Generated by `scripts/build_short_versions.py` from the built site: the points inside each',
             "page's short version (the part the on-page indicator measures and the five-minute budget",
             'holds). A page marked *reference* or *tool* has no short version by design. A page with',
             'no points has no short version yet -- see `notes/HANDOFF-WAYFINDING.md`.', '',
             'The spreadsheet form is `short-versions.csv` beside this file.', '',
             '| page | kind | short / full | the points a reader should take away |',
             '|---|---|---:|---|']
    for r in rs:
        pts = r['points']
        cell = '<br>'.join('%d. %s' % (i + 1, html.escape(x).replace('|', '\\|')) for i, x in enumerate(pts)) if pts else '*(none declared)*'
        t = ('%s / %s min' % (r['short_minutes'], r['full_minutes'])) if r['short_minutes'] else ('— / %s min' % r['full_minutes'])
        lines.append('| [%s](%s) | %s | %s | %s |' % (html.escape(r['title']).replace('|', '\\|'), r['route'], r['kind'], t, cell))
    return '\n'.join(lines) + '\n'


def render_csv(rs):
    n = max((len(r['points']) for r in rs), default=0)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(['route', 'title', 'kind', 'short_minutes', 'full_minutes', 'point_count', 'points', 'figures']
               + ['point_%d' % (i + 1) for i in range(n)])
    for r in rs:
        w.writerow([r['route'], r['title'], r['kind'], r['short_minutes'], r['full_minutes'], len(r['points']),
                    ' | '.join(r['points']), ' | '.join(r['figures'])]
                   + r['points'] + [''] * (n - len(r['points'])))
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if not os.path.isdir(DIST) or not os.path.exists(READING):
        raise SystemExit('needs fy28/dist and notes/generated/reading-time.csv -- build first')
    rs = sorted(rows(), key=sort_key)
    md, cs = render_md(rs), render_csv(rs)
    if a.check:
        ok = True
        for path, text in ((OUT_MD, md), (OUT_CSV, cs)):
            have = open(path, encoding='utf-8').read() if os.path.exists(path) else ''
            if have != text:
                print('STALE %s -- run: python3 scripts/build_short_versions.py' % os.path.relpath(path, ROOT)); ok = False
        if ok:
            print('ok: short-versions reproduce (%d pages, %d with points)' % (len(rs), sum(1 for r in rs if r['points'])))
        return 0 if ok else 1
    open(OUT_MD, 'w', encoding='utf-8').write(md)
    open(OUT_CSV, 'w', encoding='utf-8').write(cs)
    print('wrote %s and %s -- %d pages, %d with points, %d points in all'
          % (os.path.relpath(OUT_MD, ROOT), os.path.relpath(OUT_CSV, ROOT), len(rs),
             sum(1 for r in rs if r['points']), sum(len(r['points']) for r in rs)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
