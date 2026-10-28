#!/usr/bin/env python3
"""Every board's own page on the town's site -- its charter text, its members, when it
meets, and whether it has a Facebook page -- mirrored and extracted.

    python3 scripts/fetch_board_pages.py            # look again; keep a version only if it changed
    python3 scripts/fetch_board_pages.py --check    # the extract still reproduces from the mirror
    python3 scripts/fetch_board_pages.py --reparse  # re-extract the mirrored pages, no network

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

RUN UNATTENDED, ON A CADENCE. The daily refresh runs this as a `job` from
sources/data/source-cadence.csv, so a plain run has to be safe to repeat with nobody
watching:

  * A VERSION IS KEPT ONLY WHEN WHAT THE PAGE SAYS CHANGED. The bytes are no test: the town's
    CivicPlus template is re-issued under every page from time to time (a board page of
    14 September and the same page on 28 October differ in 321 lines of markup and not one
    word of text), and the district's Google Sites page carries a fresh script nonce on
    every request, so two fetches a second apart never match. What is compared is what
    this script extracts -- meetings, members, overview, charter, Facebook -- between the
    page just fetched and the working copy held, both read by the SAME parser, so a parser
    change can never pass itself off as the town changing its page.
  * AN UNCHANGED PAGE WRITES NOTHING: not a version, not an index row, not a new
    `fetched_at`. A run in which no board changed leaves git quiet. `fetched_at` is when the
    version held was fetched; when we last LOOKED is the refresh's own record,
    sources/data/source-checks.csv.
  * EXIT 0 MEANS EVERY PAGE WAS READ, changed or not. Non-zero means some page could not be
    read or a changed version could not be secured -- that board keeps its previous row and
    the refresh tries again the next morning.
  * A LISTING THAT SHRINKS SHARPLY IS REFUSED, not believed. If the town's list of boards
    comes back with far fewer boards than we hold, the likeliest cause is a redesigned page
    the link pattern no longer reads, and writing that out would delete most of the boards
    from every page that reads board-pages.csv.
"""
import argparse
import csv
import hashlib
import html as H
import io
import json
import os
import re
import sys
import time
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
# One request a second at most, serially. About forty pages, so a full look is under two
# minutes, and a small town's web host never sees a burst from us.
MIN_INTERVAL = 1.0
# The fields a version is judged by: what the parser reads off the page.
CONTENT = ('meets', 'members', 'overview', 'charter_ref', 'facebook', 'facebook_scope')
# Refuse a listing that lost more than this share of the boards we hold (see the docstring).
MAX_LOST = 0.25
COLS = ['slug', 'name', 'source', 'url', 'local', 'sha256', 'meets', 'members', 'overview',
        'charter_ref', 'facebook', 'facebook_scope', 'fetched_at']


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        h.update(fh.read())
    return h.hexdigest()


def keep(local, blob, url):
    """Every version of a page its publisher rewrites in place, and the latest at `local`.

    These pages used to be written straight over their fixed names, so a page the district
    changed on 14 September replaced the version the bucket held, and the new one never
    reached the bucket at all (found 9 October 2026). ingest.land_version() lands each
    distinct version under a dated folder -- pushed, read back, catalogued -- and keeps the
    fixed name as the working copy this script and its readers use.

    Returns True when the version is secured. On False the working copy is left as it was,
    so the next run compares against the old version again and retries the landing.
    """
    sys.path.insert(0, os.path.join(ROOT, 'scripts'))
    import ingest
    key = os.path.relpath(local, os.path.join(ROOT, 'sources'))
    ok, why = ingest.land_version(key, blob, url)
    if not ok:
        print('  !! %s: %s -- working copy left as it was' % (key, why))
    return ok


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


_last = [0.0]


def fetch(url, tries=3):
    """The page's bytes, at most one request per MIN_INTERVAL, with two retries.

    Raises after the last try: a page we could not read is a failed look, never an empty
    board."""
    for i in range(tries):
        wait = _last[0] + MIN_INTERVAL - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.monotonic()
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()
        except Exception:                                        # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1))


def text_of(html):
    t = re.sub(r'<script.*?</script>|<style.*?</style>', '', html, flags=re.S)
    t = re.sub(r'<br\s*/?>|</p>|</li>|</div>|</h\d>', '\n', t, flags=re.I)
    t = re.sub(r'<[^>]+>', '', t)
    t = H.unescape(t)
    t = re.sub(r'[ \t\u00a0]+', ' ', t)
    # Every line stripped, so a heading CivicPlus indents (" Contact Us") still ends a section.
    t = '\n'.join(line.strip() for line in t.split('\n'))
    return re.sub(r'\n\s*\n+', '\n', t).strip()


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


# Headings and labels that end an overview: the next section, or the page furniture.
CHROME = ['Contact Us', 'Members', 'Meetings', 'Agendas & Minutes', 'Quick Links', 'Physical Address',
          'Mailing Address', 'Directory', 'Staff', 'Documents', 'Related Links', 'Helpful Links', 'Links',
          'Local Sports Organization Contacts', 'Site Links', 'Loading', 'View All',
          'Related Documents', 'Related Documents and Links', 'Code of Conduct', 'Forms', 'Applications']
LINK_LINE = re.compile(r'^(Facebook:|Email |Phone:|Fax:|/QuickLinks|-->|View All|\[\]|Arrow |Slideshow |Do Not Show|Close$|Government Websites)')


def parse_town(html):
    text = text_of(html)
    heads = ['Meetings', 'Agendas & Minutes', 'Members', 'Overview', 'Contact Us', 'Responsibilities', 'Mission', 'Purpose']
    meets = section(text, 'Meetings', heads[1:])
    member_ends = ['Overview', 'Contact Us', 'Responsibilities', 'Mission', 'Purpose', 'Staff', 'Documents',
                   'Agendas & Minutes']
    members = section(text, 'Members', member_ends)
    if not members:
        # A HEADING THAT NAMES THE BOARD IS STILL THE MEMBERS HEADING. The Board of Assessors
        # retitled its block `Board of Assessors Members:` between 14 September and
        # 28 October 2026, and the exact match above then read no members at all -- which
        # an unattended run would have published as a board with nobody on it.
        m = re.search(r'\n([^\n]{0,60}Members:?)\n', '\n' + text + '\n')
        if m:
            members = section(text, m.group(1), member_ends)
    overview = ''
    for h in ('Overview', 'Responsibilities', 'Mission', 'Purpose'):
        overview = section(text, h, CHROME)
        if overview:
            break
    # THE PAGE'S FURNITURE IS NOT THE BOARD'S DESCRIPTION. TJ, 17 September 2026, on the
    # Parks page: "the one for parks is insanely long ... filter it out to be a description
    # and not an app link." CivicPlus prints quick links, the contact card, the footer and
    # the slideshow controls after the overview with no heading of their own, so a line
    # that is a link label rather than a sentence ends the description too.
    kept = []
    for line in overview.split('\n'):
        if LINK_LINE.match(line):
            break
        kept.append(line)
    overview = '\n'.join(kept).strip()
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
    block = text[i:j] if i >= 0 and j > i else ''
    # The page breaks names, roles and terms across lines unevenly ("Vice\nChai\nr", "202\n8"),
    # so members are read as name-role-email-term groups rather than line by line.
    flat = re.sub(r'\s+', ' ', block)
    found = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][A-Za-z.\'-]+)+),\s*((?:Vice\s*Chai\s*r|Vice Chair|Chair|Secretary|Member))\s+[a-z.]+@lunenburgschools\.net\s+Term expires\s*(\d{3}\s?\d)', flat)
    members = '\n'.join('%s, %s — Term expires %s' % (n.strip(), re.sub(r'\s+', '', r).replace('ViceChair', 'Vice Chair'), t.replace(' ', '')) for n, r, t in found)
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
    """Set this page's row in a SHARED catalogue -- re-read immediately before writing,
    written only if the row actually changed, in the file's own newline convention, and
    renamed into place. Other crawlers write these files too, and a rewrite that flipped
    every line ending or dropped a row another writer had just added would be our damage."""
    raw = open(index_path, 'rb').read()
    nl = '\r\n' if b'\r\n' in raw[:4096] else '\n'
    rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8'))))
    cols = list(rows[0].keys())
    rel = os.path.relpath(local, ROOT)
    new = {c: '' for c in cols} | dict(label=label, upstream=url, local=rel, bytes=str(size), sha256=digest, read='html page')
    have = [r for r in rows if r['local'] == rel]
    if len(have) == 1 and {c: have[0].get(c) or '' for c in cols} == new:
        return
    rows = [r for r in rows if r['local'] != rel] + [new]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator=nl)
    w.writeheader()
    w.writerows(rows)
    tmp = index_path + '.tmp'
    open(tmp, 'w', newline='', encoding='utf-8').write(buf.getvalue())
    os.replace(tmp, index_path)


def held_content(row, parser):
    """What the working copy says, read by the parser in use now -- or None if not on disk."""
    p = os.path.join(ROOT, row['local']) if row else ''
    if not p or not os.path.exists(p):
        return None
    got = parser(open(p, 'rb').read().decode('utf-8', 'replace'))
    return {k: got.get(k, '') for k in CONTENT}


def look(name, slug, source, url, local, index_path, label, parser, prev, now):
    """Fetch one board's page and return (row, ok). Lands a version only if the extract changed.

    `prev` is the board's row in board-pages.csv as held. An unchanged page returns that
    row with its fetch-time fields untouched and its extracted fields re-read from the
    working copy -- exactly what --reparse would write -- so nothing in the file moves."""
    html = fetch(url)
    p = parser(html.decode('utf-8', 'replace'))
    if source == 'district':
        # The district row's overview is written by us (see parse_district), not read off the
        # page, so it is not part of what the page says.
        p['overview'] = prev['overview'] if prev and prev.get('overview') else p['overview']
    fresh = {k: p.get(k, '') for k in CONTENT}
    held = held_content(prev, parser)
    if held is not None and source == 'district':
        held['overview'] = fresh['overview']
    # The row must also still describe the bytes on disk: a run that secured a version and then
    # died before writing the row would otherwise leave the two disagreeing for good, because
    # every later run would find the content unchanged and never touch the row again.
    # A retitled page (a new address for the same page id) is a change too: its title is part
    # of what the page says, and the catalogue row must carry the address it now answers at.
    if (prev and held is not None and held == fresh and prev.get('local') == os.path.relpath(local, ROOT)
            and prev.get('url') == url and prev.get('sha256') == sha256(local)):
        return dict(prev, slug=slug, name=name, **fresh), True
    # A FIELD THAT EMPTIES IS NAMED, because it is more often the parser losing the page than
    # the town emptying a board (rule 13c). The version is still kept -- it is what the town
    # is serving -- and the line tells whoever reads the refresh notes where to look.
    for k in ('meets', 'members', 'overview'):
        if held and held.get(k) and not fresh.get(k):
            print('  ?? %s: %s was %d line(s), now reads empty -- check the page and the parser'
                  % (name, k, len(held[k].split('\n'))))
    if not keep(local, html, url):
        return prev, False
    digest = sha256(local)
    add_index_row(index_path, label, url, local, digest, len(html))
    print('  changed  %-45s %s' % (name, ', '.join(k for k in CONTENT if not held or held.get(k) != fresh[k])))
    return dict(slug=slug, name=name, source=source, url=url, local=os.path.relpath(local, ROOT),
                sha256=digest, fetched_at=now, **p), True


def reparse():
    """Re-run the extractor over the pages already mirrored -- the parser changed, the town
    did not -- keeping every fetch-time field as it was."""
    rows = list(csv.DictReader(open(OUT, encoding='utf-8')))
    for r in rows:
        html = open(os.path.join(ROOT, r['local']), 'rb').read().decode('utf-8', 'replace')
        p = parse_town(html) if r['source'] == 'town' else parse_district(html)
        if r['source'] == 'district':
            p = {k: v for k, v in p.items() if k in r and v}      # the district row's hand-written overview stays
            p.pop('overview', None)
        r.update(p)
        print('  %-45s overview %4d words' % (r['name'], len(r['overview'].split())))
    with open(OUT, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--reparse', action='store_true', help='re-extract from the mirrored pages without fetching')
    a = ap.parse_args()
    if a.check:
        have = list(csv.DictReader(open(OUT, encoding='utf-8'))) if os.path.exists(OUT) else []
        bad = [r['slug'] for r in have if not os.path.exists(os.path.join(ROOT, r['local'])) or sha256(os.path.join(ROOT, r['local'])) != r['sha256']]
        print('ok — %d board pages, every mirror still the bytes the extract was read from' % len(have) if not bad
              else 'STALE board-pages.csv: %s' % ', '.join(bad))
        return 1 if bad else 0
    import datetime as dt
    if a.reparse:
        return reparse()
    now = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    slugs = meeting_slugs()
    prev_rows = list(csv.DictReader(open(OUT, encoding='utf-8'))) if os.path.exists(OUT) else []
    prev = {r['url']: r for r in prev_rows}
    index = fetch(INDEX_URL).decode('utf-8', 'replace')
    links = []
    for u, t in re.findall(r'<a[^>]+href="(/\d+/[^"]+)"[^>]*>([^<]+)</a>', index):
        t = H.unescape(t).strip()
        if t in ('Boards & Commissions', 'Boards and Commissions', 'Departments', 'Business', 'Community', 'How Do I...',
                 'Charter and Town Bylaws', 'Explore Lunenburg Brochure', 'Police', 'Town Clerk'):
            continue
        if (u, t) not in links:
            links.append((u, t))
    # A BOARD IS ITS PAGE ID, NOT ITS TITLE. The town retitled /772/Board-of-Assessors as
    # /772/Assessors-Department in October 2026; keyed on the address, that read as one board
    # gone and a new one arrived under a slug no meeting joins to. Keyed on the id, it is the
    # same board under a new name, and it keeps the slug and the mirror filename it had.
    pid_of = lambda url: url.split('lunenburgma.gov/', 1)[-1].split('/', 1)[0]
    prev_town = {pid_of(r['url']): r for r in prev_rows if r['source'] == 'town'}
    held_town = set(prev_town)
    listed = {u.split('/')[1] for u, _ in links}
    lost = sorted(held_town - listed)
    if held_town and len(lost) > MAX_LOST * len(held_town):
        print('REFUSED: the boards listing at %s shows %d board(s) and %d of the %d held are not on it. '
              'That is a page the link pattern no longer reads, not %d boards dissolved. Nothing written.'
              % (INDEX_URL, len(links), len(lost), len(held_town), len(lost)), file=sys.stderr)
        return 1
    for pid in lost:
        print('  gone     %s is no longer on the boards listing; its row is dropped, its versions are kept'
              % prev_town[pid]['url'])
    rows, failed = [], []
    os.makedirs(TOWN_DOCS, exist_ok=True)
    for u, name in links:
        url = 'https://www.lunenburgma.gov' + u
        pid = u.split('/')[1]
        before = prev_town.get(pid)
        local = os.path.join(TOWN_DOCS, 'board-%s-%s.html' % (pid, slugify(name)))
        # Where the town's page name and its AgendaCenter name differ, the meetings slug wins.
        slug = {'by-law-review-committee': 'by-law-committee'}.get(slugify(name)) or slugs.get(slugify(name), slugify(name))
        if before and before['name'] != name:
            print('  renamed  %s -> %s (page %s); slug %s and its mirror are kept'
                  % (before['name'], name, pid, before['slug']))
        if before:
            slug, local = before['slug'], os.path.join(ROOT, before['local'])
        try:
            row, ok = look(name, slug, 'town', url, local, TOWN_INDEX, name + ' (board page)', parse_town,
                           before, now)
        except Exception as e:                                   # noqa: BLE001
            print('  !! %s: %s' % (url, e))
            row, ok = before, False
        if not ok:
            failed.append(name)
        if row:
            rows.append(row)
    try:
        row, ok = look('School Committee', 'school-committee', 'district', SC_URL,
                       os.path.join(DIST_DOCS, 'school-committee-page.html'), DIST_INDEX,
                       'School Committee (district page)', parse_district, prev.get(SC_URL), now)
    except Exception as e:                                       # noqa: BLE001
        print('  !! %s: %s' % (SC_URL, e))
        row, ok = prev.get(SC_URL), False
    if not ok:
        failed.append('School Committee')
    if row:
        rows.append(row)
    # Written only if a row moved, so an unchanged run leaves the file byte for byte as it was.
    norm = lambda rs: [{c: r.get(c) or '' for c in COLS} for r in rs]
    if norm(rows) != norm(prev_rows):
        tmp = OUT + '.tmp'
        with open(tmp, 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=COLS)
            w.writeheader()
            w.writerows(norm(rows))
        os.replace(tmp, OUT)
    own = [r for r in rows if r['facebook_scope'] == 'board']
    moved = sum(1 for r in rows if r['fetched_at'] == now)
    print('%s: %d boards, %d changed since last held; %d with a Facebook link of their own (%s); %d cite a charter section'
          % (os.path.relpath(OUT, ROOT), len(rows), moved, len(own), ', '.join(r['name'] for r in own),
             sum(1 for r in rows if r['charter_ref'])))
    if failed:
        print('could not read or secure %d page(s): %s -- their previous rows are kept' % (len(failed), ', '.join(failed)),
              file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
