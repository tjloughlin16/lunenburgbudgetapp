#!/usr/bin/env python3
"""How long every page takes to read, measured from the build.

    python3 scripts/build_reading_time.py           # write notes/generated/reading-time.csv
    python3 scripts/build_reading_time.py --check   # fail if it no longer reproduces

One row per prerendered route in fy28/dist: the words a reader meets (body text, with
the header, breadcrumb, footer and scripts stripped), the minutes that is at 230 words a
minute, and the shape of the page -- how many sections, how many words before the first
one. TJ, 15 September 2026: "an expected reading time for every page and report ... I
think that will help us figure out how we need to create separate shorter pages."

WHAT THE NUMBER IS. Words in the DOM as prerendered, at every dial's default, with
`<details>` counted whether or not it is open -- so a page that hides half of itself
behind an expander is measured at its full length, which is the honest length. A route
that serves many pages (a post, a meeting, a board) is measured only at its index,
because those are the only ones in the build; the per-item pages are in the JSON
payloads and not here. The pace is a reading pace, not a skimming one: nobody reads a
45-minute page, which is the point of the table.

Sorted longest first, because the top of the list is the work.

THE SHORT VERSION, AND ITS BUDGET. TJ, 15 September: "'Short version' is perfect." Every
page can declare the part of itself sized to one sitting -- `data-short` in the DOM, set
by components/report.tsx -- and it is measured here as `short_words`. The budget is
SHORT_BUDGET words, about two minutes, and it is enforced as a RATCHET rather than a
wall: `--check` fails if any page's short version is over budget and larger than the
last time this file was written, and it fails if a page that was under budget goes over.
A page already over budget may only shrink. That is the honest shape for a rule adopted
with eight pages already breaking it -- a wall would have failed the build on the day
the rule arrived and taught everybody to skip the check; a ratchet lets nothing get
worse and reports what is left. Pages with no short version at all are listed, not
failed, for the same reason; `--strict` fails on them too, for the day coverage is done.
"""
import argparse
import csv
import html
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, 'fy28', 'dist')
OUT = os.path.join(ROOT, 'notes', 'generated', 'reading-time.csv')

WPM = 230
# Two minutes. A short version has to fit one sitting; past this it is a second page.
SHORT_BUDGET = 460
SHORT = re.compile(r'<[^>]+\bdata-short\b', re.I)
# Skipped: not pages a person reads, or not ours to measure.
SKIP_PREFIX = ('share/', 'docs/', 'data/', 'api/', 'reference/', 'minutes/', 'assets/')

TAG = re.compile(r'<[^>]+>')
COMMENT = re.compile(r'<!--.*?-->', re.S)
DROP = re.compile(r'<(script|style|noscript|svg)\b.*?</\1>', re.S | re.I)
# The furniture every page carries: the sticky header, the breadcrumb and the footer.
FURNITURE = re.compile(r'<header class="no-print[^"]*".*?</header>|<nav aria-label="Breadcrumb".*?</nav>|<footer\b.*?</footer>', re.S | re.I)
H1 = re.compile(r'<h1\b[^>]*>(.*?)</h1>', re.S | re.I)
H2 = re.compile(r'<h2\b[^>]*>(.*?)</h2>', re.S | re.I)
TITLE = re.compile(r'<title>(.*?)</title>', re.S | re.I)
CRUMB = re.compile(r'<nav aria-label="Breadcrumb".*?</nav>', re.S | re.I)
LI = re.compile(r'<li\b[^>]*>(.*?)</li>', re.S | re.I)


def text(fragment):
    return re.sub(r'\s+', ' ', html.unescape(TAG.sub(' ', fragment))).strip()


def words(fragment):
    return len(text(fragment).split())


def routes():
    out = []
    for dirpath, _, names in os.walk(DIST):
        for name in names:
            if not name.endswith('.html'):
                continue
            path = os.path.join(dirpath, name)
            route = os.path.relpath(path, DIST)[:-len('.html')]
            if route == 'index':
                route = ''
            if route.startswith(SKIP_PREFIX) or route.startswith('__'):
                continue
            out.append((route, path))
    return out


def short_words(body):
    """Words inside any data-short element, counted once however the marks nest.
    None when the page declares no short version."""
    marks = list(SHORT.finditer(body))
    if not marks:
        return None
    # Walk each marked element to its matching close tag by counting open/close tags of
    # the same name, then union the spans so a Conclusions block inside a conclusions
    # section is not counted twice.
    spans = []
    for m in marks:
        name = re.match(r'<([a-zA-Z0-9]+)', body[m.start():]).group(1)
        depth = 0
        for t in re.finditer(r'<(/?)%s\b[^>]*>' % name, body[m.start():], re.I):
            depth += -1 if t.group(1) else 1
            if depth == 0:
                spans.append((m.start(), m.start() + t.end()))
                break
    spans.sort()
    merged = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return sum(words(body[a:b]) for a, b in merged)


def measure(route, path):
    raw = open(path, encoding='utf-8', errors='replace').read()
    raw = COMMENT.sub(' ', raw)
    raw = DROP.sub(' ', raw)
    t = TITLE.search(raw)
    title = re.sub(r'\s+—\s+Lunenburg Budget Project\s*$', '', text(t.group(1))) if t else route
    crumb = CRUMB.search(raw)
    # The structural trail, as the page shows it -- PARENT in routes.ts, not the area.
    trail = ' > '.join(text(x).rstrip(' \u203a') for x in LI.findall(crumb.group(0))) if crumb else ''
    body = FURNITURE.sub(' ', raw)
    h1 = H1.search(body)
    h2s = [m.start() for m in H2.finditer(body)]
    total = words(body)
    # Words before the first section heading -- the standfirst and whatever else stands
    # in front of the thing (rule 7a's count).
    before = words(body[:h2s[0]]) if h2s else total
    short = short_words(body)
    return {
        'route': '/' + route,
        'title': title,
        'breadcrumb': trail,
        'h1': text(h1.group(1)) if h1 else '',
        'words': total,
        'minutes': round(total / WPM, 1),
        'short_words': '' if short is None else short,
        'short_minutes': '' if short is None else round(short / WPM, 1),
        'short_over_budget': '' if short is None else ('yes' if short > SHORT_BUDGET else ''),
        'sections': len(h2s),
        'words_before_first_section': before,
        # A table is read down a column, not word by word, so a page whose words are
        # mostly rows is shorter than its count says. The count is here to discount it.
        'table_rows': len(re.findall(r'<tr\b', body, re.I)),
        'details_blocks': len(re.findall(r'<details\b', body, re.I)),
    }


def render():
    if not os.path.isdir(DIST):
        raise SystemExit('no build at fy28/dist -- run npm run build:site first')
    rows = [measure(r, p) for r, p in routes()]
    rows.sort(key=lambda r: (-r['words'], r['route']))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue(), rows


def budget(rows, previous, strict):
    """The ratchet. Returns a list of failures; empty means the short versions held."""
    fails = []
    was = {r['route']: r for r in previous}
    for r in rows:
        if r['short_words'] == '':
            continue
        n = int(r['short_words'])
        if n <= SHORT_BUDGET:
            continue
        before = was.get(r['route'], {}).get('short_words', '')
        if not was:
            continue  # no baseline yet: this write IS the baseline
        if before == '' or int(before) <= SHORT_BUDGET:
            fails.append('%s: short version is %d words, over the %d budget (it was %s)'
                         % (r['route'], n, SHORT_BUDGET, before or 'not declared'))
        elif n > int(before):
            fails.append('%s: short version grew from %s to %d words while over the %d budget -- it may only shrink'
                         % (r['route'], before, n, SHORT_BUDGET))
    missing = [r['route'] for r in rows if r['short_words'] == '' and r['route'] not in ('/', '/not-found', '/search')]
    if strict and missing:
        fails.append('%d page(s) declare no short version: %s' % (len(missing), ', '.join(missing)))
    return fails, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--strict', action='store_true', help='also fail pages with no short version')
    ap.add_argument('--allow-growth', action='store_true', help='write even though a short version grew past its budget')
    a = ap.parse_args()
    out, rows = render()
    previous = list(csv.DictReader(open(OUT, encoding='utf-8'))) if os.path.exists(OUT) else []
    # The first write after the column arrives is the baseline the ratchet turns from.
    if previous and 'short_words' not in previous[0]:
        previous = []
    fails, missing = budget(rows, previous, a.strict)
    over = [r for r in rows if r['short_over_budget']]
    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        for f in fails:
            print('BUDGET ' + f)
        if have != out:
            print('STALE %s -- run: python3 scripts/build_reading_time.py' % os.path.relpath(OUT, ROOT))
            return 1
        if fails:
            return 1
        print('ok: %s reproduces; %d short version(s) still over the %d-word budget, none grew; %d page(s) declare none'
              % (os.path.relpath(OUT, ROOT), len(over), SHORT_BUDGET, len(missing)))
        return 0
    for f in fails:
        print('BUDGET ' + f)
    if fails and not a.allow_growth:
        # Refusing to write is what keeps the ratchet a ratchet: a write that moved the
        # baseline would let the next --check pass on a page that just got longer.
        print('not written: shrink the short version, or pass --allow-growth to move the baseline on purpose')
        return 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write(out)
    total = sum(r['words'] for r in rows)
    print('wrote %s -- %d pages, %s words, %d min at %d wpm; longest %s (%s min)'
          % (os.path.relpath(OUT, ROOT), len(rows), format(total, ','), total // WPM, WPM,
             rows[0]['route'], rows[0]['minutes']))
    print('short versions: %d declared, %d over the %d-word budget, %d page(s) with none'
          % (sum(1 for r in rows if r['short_words'] != ''), len(over), SHORT_BUDGET, len(missing)))
    for r in over:
        print('  over: %-45s %5s words' % (r['route'], r['short_words']))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
