#!/usr/bin/env python3
"""THE ATTORNEY GENERAL'S OPEN MEETING LAW DETERMINATIONS -- a CHOSEN few, not the database.

    python3 scripts/fetch_oml_determinations.py            # fetch the chosen ones not yet held
    python3 scripts/fetch_oml_determinations.py --check    # every held one: hash, text present
    python3 scripts/fetch_oml_determinations.py --search acronym   # ask the AG's own full-text
                                                           #   search, print every hit, save nothing

WHAT THIS IS. The AG's Division of Open Government publishes every determination letter it
has issued -- thousands -- through a Hyland "Public Access" portal,
massago.hylandcloud.com/231publicaccess2/OML.html, the page mass.gov's Open Meeting Law
landing page links as the determination lookup. This script does not mirror that database.
It fetches the letters named in CHOSEN below, each picked for a question this project was
asked, with the reason recorded beside it, so the selection is a decision a reader can see
rather than a sample nobody can explain. Bulk-fetching remains a separate decision.

HOW THE PORTAL ANSWERS, read off its own client (`!obpa/obpa_app.js`), 8 October 2026:

  * POST api/CustomQuery/KeywordSearch  {QueryID:104, Keywords:[{ID:135, Value:"OML 2024-218"}]}
    finds a letter by its DETERMINATION NUMBER (keyword 135) and returns a document ID;
  * POST api/DocumentType/FullTextSearch {SearchText, DocTypeID:120} is the portal's own
    full-text search over the letters (what `--search` calls);
  * GET  api/Document/<ID>/?ViewerMode=PDF&ForceDownload=true returns the PDF, with the AG's
    filename in Content-Disposition.

The portal answers plain HTTPS; no browser is needed (unlike mass.gov, see
browser_fetch.mjs). THE DOCUMENT ID IS A TOKEN THE PORTAL MINTS PER SEARCH -- two searches
for the same letter return two different IDs, both of which fetched the same bytes when
tested. So `upstream` records the token URL that was actually fetched, and `fetched_via`
records the durable route: the lookup page, searched by determination number. That route is
the address a resident can follow when the token stops working (rule 12).

WHERE IT LANDS. `sources/state-law/<retrieval date>/determinations/<slug of the AG's
filename>`, through `ingest.land()` (staged, pushed, read back, filed), catalogued in the
same `sources/state-law/index.csv` as the statute and the guide, with text in
`sources/state-law/text/` -- so `search_minutes.py --corpus law` and `oml_law.py` read
them with no change.
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fetch_open_meeting_law as F  # noqa: E402  -- one index, one extractor, one naming rule

ROOT = F.ROOT
PORTAL = 'https://massago.hylandcloud.com/231publicaccess2'
API = PORTAL + '/api'
LOOKUP = PORTAL + '/OML.html'
AG = 'Attorney General of Massachusetts'

# (determination number as the AG writes it, why it is here). Chosen 8 October 2026 for one
# question -- are acronyms on an agenda an Open Meeting Law problem -- from the portal's own
# full-text search for "acronym" (66 hits) and "abbreviation" (48 hits), plus the letters
# a secondary summary (Concord's) cited for the general specificity standard. Includes
# letters that found NO violation, so the selection is not one-sided.
CHOSEN = [
    ('OML 2024-218', 'Lunenburg Historical Commission: the same town; advises against acronyms on notices'),
    ('OML 2014-138', 'Cape & Vineyard Electric Cooperative: the footnote later letters cite on abbreviations'),
    ('OML 2015-197', 'Barnstable Town Council Roads Sub-committee: an abbreviation found to violate the law'),
    ('OML 2018-56', 'Group Insurance Commission: "may not use acronyms ... unless commonly understood"'),
    ('OML 2015-148', 'Barnstable School Committee: AFSCME found widely understood -- no violation on that'),
    ('OML 2022-176', 'Fall River Board of Health: acronym, but the topic still reasonably informed'),
    ('OML 2022-174', 'Medway School Committee: "SLA" on a notice likely does not comply'),
    ('OML 2020-152', 'Monomoy Regional School Committee: the acronym "COA"'),
    ('OML 2023-83', 'Medfield School Committee: policy codes BEDH / BEDH-E not widely understood'),
    ('OML 2025-153', 'Somerset Planning Board: "B.E.S.S." -- a recent statement of the standard'),
    ('OML 2026-99', 'Medfield Housing Authority: "PMR" -- the most recent letter on point found'),
    ('OML 2015-127', 'Sandwich Board of Selectmen: "old business" / "new business" headings'),
    ('OML 2015-128', 'Warren Board of Selectmen: "general housekeeping" -- insufficient'),
    ('OML 2011-11', 'Freetown Soil Conservation Board: the reasonable-member specificity standard'),
    ('OML 2014-125', 'Lanesborough Elementary School Committee: a budget topic found sufficient'),
]


# ONE COOKIE JAR FOR THE RUN. The portal sets a load-balancer cookie (FB_LB) and a document
# ID minted on one backend answered 500 when fetched cold from another; the portal's own
# client keeps the cookie and POSTs to the document before GETting it, so this does too.
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())


def post(path, body):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    with OPENER.open(req, timeout=120) as r:
        return json.load(r)


TOLERANT = False


def lookup(number):
    """The portal's record for one determination number: (doc ID, name, columns)."""
    d = post('/CustomQuery/KeywordSearch',
             {'QueryID': 104, 'Keywords': [{'ID': 135, 'Value': number}], 'QueryLimit': 0})
    heads = [c['Heading'] for c in d.get('DisplayColumns') or []]
    hits = [x for x in d.get('Data') or [] if x['Name'].startswith('DETERMINATION')]
    if not hits and TOLERANT:
        return None, None, None                 # --all walks numbers; a gap is not an error
    if len(hits) > 1 and TOLERANT:
        # ONE NUMBER, SEVERAL ENTRIES: OML 2012-5 is listed twice under the same name
        # (found 9 Oct 2026, when it ended the overnight walk). fetch_one fetches each and
        # keeps a second only if its bytes differ -- a duplicate is not a second letter.
        return [(x['ID'], x['Name'], dict(zip(heads, [v['Value'] for v in x.get('DisplayColumnValues') or []])))
                for x in hits], None, None
    if len(hits) != 1:
        raise SystemExit('%s: the portal returned %d determinations, expected 1: %s'
                         % (number, len(hits), [x['Name'] for x in d.get('Data') or []]))
    x = hits[0]
    cols = dict(zip(heads, [v['Value'] for v in x.get('DisplayColumnValues') or []]))
    return x['ID'], x['Name'], cols


def download(doc_id):
    """(url, status, disposition, bytes). The portal answers HTTP 500 INTERMITTENTLY -- on
    8 October 2026 one letter failed on one request form and succeeded on the next, with
    identical bytes from either form -- so each letter gets up to six attempts, alternating
    the two URL forms the portal's client uses, and the URL that answered is the one kept."""
    import time
    path = '/Document/%s/' % urllib.parse.quote(doc_id, safe='')
    last = (API + path, 0, '', b'')
    for attempt in range(6):
        url = API + path + ('?ViewerMode=PDF&ForceDownload=true' if attempt % 2 == 0 else '')
        try:
            post(path, {})
            with OPENER.open(url, timeout=120) as r:
                return url, r.status, r.headers.get('content-disposition') or '', r.read()
        except urllib.error.HTTPError as e:
            last = (url, e.code, '', b'')
            time.sleep(2)
    return last


def did_of(number):
    return 'oml-det-' + re.sub(r'[^0-9]+', '-', number).strip('-')


def fetch_one(number, rows, today):
    """Fetch, land and catalogue one determination. -> 'held' | 'ok' | 'gap' | 'failed'."""
    import ingest
    did = did_of(number)
    if did in rows:
        return 'held'
    doc_id, name, cols = lookup(number)
    if doc_id is None:
        return 'gap'
    if isinstance(doc_id, list):
        seen, result = set(), 'gap'
        for i, (one_id, one_name, one_cols) in enumerate(doc_id):
            url, status, disp, blob = download(one_id)
            h = hashlib.sha256(blob).hexdigest() if blob else ''
            if not blob.startswith(b'%PDF') or h in seen:
                continue
            seen.add(h)
            r = land_one(number if not seen - {h} else '%s (%s)' % (number, chr(97 + i)),
                         did if len(seen) == 1 else '%s-%s' % (did, chr(97 + i)),
                         url, disp, blob, one_cols, rows, today)
            result = 'ok' if r == 'ok' or result == 'ok' else r
        return result
    url, status, disp, blob = download(doc_id)
    if status != 200 or not blob.startswith(b'%PDF'):
        print('  !! %-14s HTTP %s, not a PDF' % (number, status), flush=True)
        return 'failed'
    return land_one(number, did, url, disp, blob, cols, rows, today)


def land_one(number, did, url, disp, blob, cols, rows, today):
    """Land, extract and catalogue one fetched letter under `did`."""
    import ingest
    pub = F.publisher_filename(url, disp, 'application/pdf')
    key = 'state-law/%s/determinations/%s' % (today, F.archival_name(pub))
    ok, reason = ingest.land(key, blob, url)
    if not ok:
        print('  !! %-14s %s' % (number, reason), flush=True)
        return 'failed'
    local = os.path.join(ROOT, 'sources', key)
    txt = os.path.join(F.TEXT, did + '.txt')
    verdict = cols.get('Violation') or 'not stated'
    # The portal's Violation field is for the LETTER, across every allegation in it --
    # not for any one topic. Labelled as the portal's field so it is not read as more.
    label = ('AG determination %s, %s, %s (portal Violation field: %s)'
             % (cols.get('Determination Number', number), cols.get('Determination Date', ''),
                html.unescape(cols.get('Public Body Name') or '').title(), verdict))
    rows[did] = {'id': did, 'label': label, 'publisher': AG, 'upstream': url,
                 'publisher_filename': pub, 'local': os.path.relpath(local, ROOT),
                 'text': os.path.relpath(txt, ROOT), 'bytes': str(len(blob)),
                 'sha256': hashlib.sha256(blob).hexdigest(), 'retrieved': today,
                 'fetched_via': ('plain HTTPS from the AG determination lookup (%s), '
                                 'found by Determination Number "%s"; the document '
                                 'ID in the URL is minted per search' % (LOOKUP, number)),
                 'read': F.extract(local, txt, url)}
    F.write_index(rows)
    print('  ok %-14s %7d bytes  %s  %s' % (number, len(blob), rows[did]['sha256'][:12], pub), flush=True)
    return 'ok'


def fetch():
    rows = F.read_index()
    today = dt.date.today().isoformat()
    failed = sum(fetch_one(number, rows, today) == 'failed' for number, _ in CHOSEN)
    return 1 if failed else 0


# EVERY DETERMINATION, NOT A CHOSEN FEW. TJ, 8 October 2026: "Is it ingesting ALL
# determinations? Beyond acronyms". The portal has no "list everything" call this client
# could find, but it answers a lookup by DETERMINATION NUMBER, and the numbers run
# OML <year>-1, -2, ... within each year from 2010 (when the AG took over the law). So
# --all walks the numbers, year by year, and moves to the next year after GAP_STOP numbers
# in a row return nothing. Resumable: anything already held is skipped. Plain downloads,
# no model calls; polite pacing, because this is the AG's own server.
GAP_STOP = 25
PAUSE_S = 0.5


def fetch_all(first_year=2010, last_year=None):
    import time
    global TOLERANT
    TOLERANT = True
    rows = F.read_index()
    today = dt.date.today().isoformat()
    last_year = last_year or dt.date.today().year
    totals = {'held': 0, 'ok': 0, 'gap': 0, 'failed': 0}
    for year in range(first_year, last_year + 1):
        n, gaps, found = 0, 0, 0
        while gaps < GAP_STOP:
            n += 1
            number = 'OML %d-%d' % (year, n)
            try:
                r = fetch_one(number, rows, today)
            except (Exception, SystemExit) as e:     # noqa: BLE001 -- one letter must not end the walk
                # SystemExit too: lookup() raises it on a portal answer it does not expect,
                # and on 8 October that ended the whole walk at OML 2012-5 overnight.
                print('  !! %-14s %s' % (number, str(e)[:120]), flush=True)
                r = 'failed'
            totals[r] += 1
            gaps = gaps + 1 if r == 'gap' else 0
            found += r in ('ok', 'held')
            if r != 'held':
                time.sleep(PAUSE_S)
        print('%d: %d determinations held, walked to %d' % (year, found, n - GAP_STOP), flush=True)
    print('all years: %(ok)d fetched, %(held)d already held, %(failed)d failed, %(gap)d numbers with no letter' % totals)
    return 1 if totals['failed'] else 0


def check():
    rows = F.read_index()
    bad = []
    for number, _ in CHOSEN:
        r = rows.get(did_of(number))
        if not r:
            bad.append('%s: not held' % number)
            continue
        p = os.path.join(ROOT, r['local'])
        if not os.path.exists(p):
            bad.append('%s: %s missing on disk (sync_archive.py --pull)' % (number, r['local']))
        elif hashlib.sha256(open(p, 'rb').read()).hexdigest() != r['sha256']:
            bad.append('%s: sha256 differs from index' % number)
        t = os.path.join(ROOT, r['text'])
        if not os.path.exists(t) or len(open(t, encoding='utf-8').read().strip()) < 200:
            bad.append('%s: extracted text missing or near-empty' % number)
    for b in bad:
        print('  !!', b)
    print('determinations: %d of %d held, hashed and extracted' % (len(CHOSEN) - len(bad), len(CHOSEN)))
    return 1 if bad else 0


def search(text):
    d = post('/DocumentType/FullTextSearch',
             {'SearchText': text, 'DocTypeID': 120, 'Keywords': [], 'QueryLimit': 0})
    hits = d.get('Data') or []
    print('AG full-text search %r: %d letters%s' % (text, len(hits), ' (TRUNCATED)' if d.get('Truncated') else ''))
    for x in hits:
        print('  %s\n      %s' % (x['Name'], ' '.join((x.get('Summary') or '').split())[:160]))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--search')
    ap.add_argument('--all', action='store_true', help='walk every determination number, 2010 to this year (resumable)')
    ap.add_argument('--year', type=int, help='with --all: one year only')
    a = ap.parse_args()
    if a.search:
        return search(a.search)
    if a.all:
        return fetch_all(a.year or 2010, a.year)
    return check() if a.check else fetch()


if __name__ == '__main__':
    sys.exit(main())
