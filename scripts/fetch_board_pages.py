#!/usr/bin/env python3
"""Every board's own page on the town's site -- its charter text, its members, when it
meets, and whether it has a Facebook page -- mirrored and extracted.

    python3 scripts/fetch_board_pages.py          # fetch, mirror, extract
    python3 scripts/fetch_board_pages.py --check  # the extract still reproduces from the mirror

TJ, 14 September 2026: "on the landing page for each board, can you put their charter and
a link to their town page? we also need to see if these boards have facebook pages."

WHERE IT COMES FROM. https://www.lunenburgma.gov/158/Boards-Commissions lists every town
board with a page of its own; each page carries a Meetings block (when, where), a Members
block (names, roles, terms) and an Overview (what the board is and does, usually citing the
Charter or a bylaw). The School Committee is NOT on that list -- it is a body of the school
district, elected under Chapter 71 of the General Laws, and its page is on the district's
site: https://www.lunenburgschools.net/school-committee-1.

Each page is saved as fetched under sources/town-supplementary/docs/board-<id>-<slug>.html
(the district one under sources/district-budget/docs/), indexed with its address, and
extracted into sources/data/board-pages.csv with the text AS PRINTED. The overview is the
town's own sentence about the board and is quoted, never paraphrased.

FACEBOOK. A board's page is searched for a facebook.com link. The town's site links only
the TOWN's page (facebook.com/townoflunenburgma) from its footer; that is recorded as
`town`, not as the board's. A board-specific link is recorded only where the board's own
page carries one -- the School Committee's group is the one found. Facebook itself cannot
be searched by script, so "none on the board's page" is what is established, not "none".
"""
import argparse
import csv
import hashlib
import html as H
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_URL = 'https://www.lunenburgma.gov/158/Boards-Commissions'
SC_URL = 'https://www.lunenburgschools.net/school-committee-1'
TOWN_FB = 'https://www.facebook.com/townoflunenburgma/'
OUT = os.path.join(ROOT, 'sources', 'data', 'board-pages.csv')
TOWN_DOCS = os.path.join(ROOT, 'sources', 'town-supplementary', 'docs')
TOWN_INDEX = os.path.join(ROOT, 'sources', 'town-supplementary', 'index.csv')
DIST_DOCS = os.path.join(ROOT, 'sources', 'district-budget', 'docs')
DIST_INDEX = os.path.join(ROOT, 'sources', 'district-budget', 'index.csv')
MEETINGS_INDEX = os.path.join(ROOT, 'sources', 'meetings', 'index.csv')
UA = {'User-Agent': 'Mozilla/5.0 (lunenburgbudgetproject.org research)'}
COLS = ['slug', 'name', 'source', 'url', 'local', 'sha256', 'meets', 'members', 'overview',
        'charter_ref', 'facebook', 'facebook_scope', 'fetched_at']


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        h.update(fh.read())
    return h.hexdigest()


def slugify(name):
    s = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return s


def meeting_slugs():
    """The board slugs the meetings index uses, so a town page joins the board it belongs to."""
    out = {}
    for r in csv.DictReader(open(MEETINGS_INDEX, encoding='utf-8')):
        if r['path']:
            out.setdefault(slugify(r['board']), r['path'].split('/')[0])
    return out


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()


def text_of(html):
    t = re.sub(r'<script.*?</script>|<style.*?</style>', '', html, flags=re.S)
    t = re.sub(r'<br\s*/?>|</p>|</li>|</div>|</h\d>', '\n', t, flags=re.I)
    t = re.sub(r'<[^>]+>', '', t)
    t = H.unescape(t)
    return re.sub(r'[ \t ]+', ' ', re.sub(r'\n\s*\n+', '\n', t)).strip()


def section(text, start, ends):
    """The lines between a heading and the next of `ends`, as printed."""
    i = text.find('\n' + start + '\n')
    if i < 0:
        return ''
    body = text[i + len(start) + 2:]
    cut = len(body)
    for e in ends:
        j = body.find('\n' + e + '\n')
        if 0 <= j < cut:
            cut = j
    return body[:cut].strip()


def parse_town(html):
    text = text_of(html)
    heads = ['Meetings', 'Agendas & Minutes', 'Members', 'Overview', 'Contact Us', 'Responsibilities', 'Mission', 'Purpose']
    meets = section(text, 'Meetings', heads[1:])
    members = section(text, 'Members', ['Overview', 'Contact Us', 'Responsibilities', 'Mission', 'Purpose', 'Staff', 'Documents'])
    overview = ''
    for h in ('Overview', 'Responsibilities', 'Mission', 'Purpose'):
        overview = section(text, h, ['Contact Us', 'Members', 'Meetings', 'Agendas & Minutes'])
        if overview:
            break
    # tidy: members print as "Name\n, Chair\nTerm Expires June 2029"
    members = re.sub(r'\n, ', ', ', members)
    members = re.sub(r'\n(Term Expires[^\n]*)', r' — \1', members)
    # A citation, not a sentence: "Charter, Section 2-1(c)", "Chapter 40, Section 8C", "M.G.L. c. 41".
    # A bylaw named in prose is recorded as the bylaw, not quoted at length.
    charter = re.search(r"((?:Town\s+)?Charter,?\s+(?:Section|§)\s*[\d\-()a-z.]+|(?:M\.?G\.?L\.?|Chapter|c\.)\s*\d+[A-Z]?(?:,?\s*(?:Section|§)\s*[\d\w()]+)?)", overview)
    charter_ref = charter.group(1).strip().rstrip('.') if charter else ('a Town Bylaw' if re.search(r'by-?law', overview, re.I) else '')
    fb = sorted(set(re.findall(r'https?://(?:www\.)?facebook\.com/[^"\'\s<>]+', html)))
    own = [u for u in fb if 'townoflunenburgma' not in u]
    return dict(meets=meets, members=members, overview=overview, charter_ref=charter_ref,
                facebook=own[0] if own else (TOWN_FB if fb else ''), facebook_scope='board' if own else ('town' if fb else 'none on the page'))


def parse_district(html):
    text = text_of(html)
    i = text.find('School Committee Members & INFORMATION')
    j = text.find('Broadcast of Meetings')
    members = text[i:j].split('\n', 1)[1] if i >= 0 and j > i else ''
    members = re.sub(r'\n(Term expires[^\n]*)', r' — \1', members)
    members = re.sub(r'\n[a-z.]+@lunenburgschools\.net', '', members)
    members = re.sub(r'\n', ' ', members).strip()
    members = re.sub(r'\s+—', ' —', re.sub(r'(\d{4})\s+', r'\1 · ', members))
    k = text.find('Broadcast of Meetings')
    meets = text[k:].split('LUNENBURG SCHOOL COMMITTEE', 1)[0].split('\n', 1)[1].strip() if k >= 0 else ''
    fb = sorted(set(re.findall(r'https?://(?:www\.)?facebook\.com/[^"\'\s<>]+', html)))
    return dict(meets=meets, members=members,
                overview=('The School Committee is a body of the school district, not of the town: five members elected '
                          'town-wide to three-year terms, with general charge of the public schools under Massachusetts '
                          'General Laws Chapter 71, Section 37. Its page is on the district’s site, which is why it is '
                          'not on the town’s list of boards.'),
                charter_ref='M.G.L. c. 71, § 37', facebook=fb[0] if fb else '', facebook_scope='board' if fb else 'none on the page')


def add_index_row(index_path, label, url, local, digest, size):
    rows = list(csv.DictReader(open(index_path, encoding='utf-8')))
    cols = list(rows[0].keys())
    rel = os.path.relpath(local, ROOT)
    rows = [r for r in rows if r['local'] != rel]
    rows.append({c: '' for c in cols} | dict(label=label, upstream=url, local=rel, bytes=str(size), sha256=digest, read='html page'))
    with open(index_path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.check:
        have = list(csv.DictReader(open(OUT, encoding='utf-8'))) if os.path.exists(OUT) else []
        bad = [r['slug'] for r in have if not os.path.exists(os.path.join(ROOT, r['local'])) or sha256(os.path.join(ROOT, r['local'])) != r['sha256']]
        print('ok — %d board pages, every mirror still the bytes the extract was read from' % len(have) if not bad
              else 'STALE board-pages.csv: %s' % ', '.join(bad))
        return 1 if bad else 0
    import datetime as dt
    now = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    slugs = meeting_slugs()
    index = fetch(INDEX_URL).decode('utf-8', 'replace')
    links = []
    for u, t in re.findall(r'<a[^>]+href="(/\d+/[^"]+)"[^>]*>([^<]+)</a>', index):
        t = H.unescape(t).strip()
        if t in ('Boards & Commissions', 'Boards and Commissions', 'Departments', 'Business', 'Community', 'How Do I...',
                 'Charter and Town Bylaws', 'Explore Lunenburg Brochure', 'Police', 'Town Clerk'):
            continue
        if (u, t) not in links:
            links.append((u, t))
    rows = []
    os.makedirs(TOWN_DOCS, exist_ok=True)
    for u, name in links:
        url = 'https://www.lunenburgma.gov' + u
        html = fetch(url)
        pid = u.split('/')[1]
        local = os.path.join(TOWN_DOCS, 'board-%s-%s.html' % (pid, slugify(name)))
        open(local, 'wb').write(html)
        digest = sha256(local)
        add_index_row(TOWN_INDEX, name + ' (board page)', url, local, digest, len(html))
        p = parse_town(html.decode('utf-8', 'replace'))
        # Where the town's page name and its AgendaCenter name differ, the meetings slug wins.
        slug = {'by-law-review-committee': 'by-law-committee'}.get(slugify(name)) or slugs.get(slugify(name), slugify(name))
        rows.append(dict(slug=slug, name=name, source='town', url=url, local=os.path.relpath(local, ROOT), sha256=digest,
                         fetched_at=now, **p))
        print('  %-45s %s' % (name, 'charter: ' + p['charter_ref'] if p['charter_ref'] else ('overview %d chars' % len(p['overview']))))
    html = fetch(SC_URL)
    local = os.path.join(DIST_DOCS, 'school-committee-page.html')
    open(local, 'wb').write(html)
    digest = sha256(local)
    add_index_row(DIST_INDEX, 'School Committee (district page)', SC_URL, local, digest, len(html))
    p = parse_district(html.decode('utf-8', 'replace'))
    rows.append(dict(slug='school-committee', name='School Committee', source='district', url=SC_URL,
                     local=os.path.relpath(local, ROOT), sha256=digest, fetched_at=now, **p))
    with open(OUT, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    own = [r for r in rows if r['facebook_scope'] == 'board']
    print('%s: %d boards; %d with a Facebook link of their own (%s); %d cite a charter section'
          % (os.path.relpath(OUT, ROOT), len(rows), len(own), ', '.join(r['name'] for r in own),
             sum(1 for r in rows if r['charter_ref'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
