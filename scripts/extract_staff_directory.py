#!/usr/bin/env python3
"""WHO WORKS FOR THE TOWN TODAY, from the town's own staff directory.

    python3 scripts/extract_staff_directory.py [--check]

Writes `sources/data/staff-directory.csv`.

TJ, 22 September 2026, after being told four departments were missing from the org chart:
`https://www.lunenburgma.gov/m/directory`.

WHY THIS MATTERS MORE THAN ANOTHER ROSTER. Everything else this project knows about who
works for the town is read out of ANNUAL REPORTS -- a body that files none is invisible,
and both of our other sources share that blind spot. The directory is the town listing
its own departments and its own staff, with each person's title, and it holds four
departments that appear in no annual report and no officials listing: Accounting, Human
Resources, Facilities/Grounds/Recreation, and Public Access Cable.

IT IS A CONTACT LIST, NOT AN ORG CHART, and the difference is load-bearing. It gives no
rank order, no reporting line and no date -- it is whoever the town is publishing TODAY,
which makes it a snapshot with no year attached rather than a series. Where it disagrees
with a department's own published chart, the chart wins: the directory lists Animal
Control as its own entry and the Police Department's FY27 chart puts `ACO Kathy Comeau`
under the Chief.

AND IT IS FETCHED PER DEPARTMENT. The directory's own page renders only the CATEGORIES
into HTML; the people arrive behind a tab that needs a click, so `--dump-dom` sees none of
them. Each department has its own address -- `/m/directory/department?did=N` -- and those
render fully.
"""
import argparse
import csv
import glob
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(ROOT, 'sources', 'town-supplementary', 'docs', 'staff-directory')
OUT = os.path.join(ROOT, 'sources', 'data', 'staff-directory.csv')
FIELDS = ['department', 'person', 'title', 'did', 'source']

# The directory renders each person as a two-letter avatar, then the name, then the title.
INITIALS = re.compile(r'^[A-Z][A-Z]$')
NAME = re.compile(r"^[A-Z][A-Za-z.'’-]+(?:\s+[A-Z(][A-Za-z.'’)-]*){1,3}$")
# Everything the template prints that is not a person.
CHROME = re.compile(r'^(back to directory|agendas|careers|online payments|calendar|'
                    r'explore|town meeting|quick links|site links|home|site map|'
                    r'contact us|accessibility|copyright|privacy|government websites|'
                    r'loading|do not show|close|arrow|slideshow|phone|email|e-mail|'
                    r'town of lunenburg|\W|\d)', re.I)


def lines(path):
    s = open(path, encoding='utf-8', errors='replace').read()
    s = re.sub(r'<script.*?</script>|<style.*?</style>', '', s, flags=re.S | re.I)
    return [x.strip() for x in html.unescape(re.sub(r'<[^>]+>', '\n', s)).split('\n')
            if x.strip()]


def department_of(rows):
    """The heading the page gives itself, which is the department's own name."""
    for i, t in enumerate(rows[:60]):
        if t.lower() == 'directory' and i + 1 < len(rows):
            nxt = rows[i + 1].strip()
            if nxt and not CHROME.match(nxt):
                return nxt
    return ''


def read(path):
    rows = lines(path)
    dept = department_of(rows)
    did = re.search(r'did-(\d+)', os.path.basename(path)).group(1)
    out, seen = [], set()
    for i, t in enumerate(rows):
        # A PERSON IS AN AVATAR FOLLOWED BY A NAME. The initials block is the only mark
        # the template puts on a person and nothing else, which makes it a far safer
        # anchor than trying to tell a name from a job title by shape.
        if not INITIALS.match(t) or i + 2 >= len(rows):
            continue
        name, title = rows[i + 1].strip(), rows[i + 2].strip()
        if not NAME.match(name) or CHROME.match(name) or CHROME.match(title):
            continue
        key = (dept, name.lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(department=dept, person=name, title=title, did=did,
                        source='town staff directory, /m/directory/department?did=%s' % did))
    return out


def build():
    out = []
    for p in sorted(glob.glob(os.path.join(PAGES, 'did-*.html')),
                    key=lambda p: int(re.search(r'did-(\d+)', p).group(1))):
        out += read(p)
    out.sort(key=lambda r: (r['department'].lower(), r['person'].lower()))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows = build()
    if a.check:
        old = list(csv.DictReader(open(OUT, encoding='utf-8'))) if os.path.exists(OUT) else []
        if len(old) != len(rows) or any(
                any(str(r[k]) != o[k] for k in FIELDS) for r, o in zip(rows, old)):
            print('STALE %s' % OUT)
            return 1
        return 0
    with open(OUT, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    import collections
    per = collections.Counter(r['department'] for r in rows)
    print('%d people across %d departments' % (len(rows), len(per)))
    for d, n in per.most_common():
        print('  %-44s %3d' % (d[:44], n))
    return 0


if __name__ == '__main__':
    sys.exit(main())
