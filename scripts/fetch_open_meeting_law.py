#!/usr/bin/env python3
"""THE OPEN MEETING LAW, AS THE STATE PUBLISHES IT: fetched, secured, extracted.

    python3 scripts/fetch_open_meeting_law.py            # fetch what is not yet held
    python3 scripts/fetch_open_meeting_law.py --refresh  # that, then look again at everything held
    python3 scripts/fetch_open_meeting_law.py --check    # every held file: hash, text present

What it holds, and from whom -- the publisher's own copies only:

  * the Attorney General's OPEN MEETING LAW GUIDE (PDF), the AG's landing page, FAQ page,
    educational-materials page and four of its checklists (notice, minutes, executive
    session, the chair's responsibilities) -- mass.gov;
  * the REGULATIONS, 940 CMR 29.00, as the AG publishes them (PDF) -- mass.gov;
  * the STATUTE twice: the AG's PDF of G.L. c.30A §§18-25, and each section's page on
    malegislature.gov, which is the Legislature's own text;
  * the AG's guidance on the remote-participation extension act -- mass.gov. (The act
    itself would not download; see DOCS.)

NOT the AG's determinations. They live in a search portal
(massago.hylandcloud.com/231publicaccess2/OML.html), thousands of letters; bulk-fetching
them is a separate decision, not taken. A CHOSEN few, each with the reason it was chosen,
are fetched by `fetch_oml_determinations.py` into the same index and text folder.

HOW IT FETCHES, AND WHY THAT IS PART OF THE PROVENANCE. mass.gov answers every
non-browser client -- curl, urllib, any header set tried -- with `403 Not allowed`, and
answers Chrome. So `browser_fetch.mjs` opens one mass.gov page in headless Chrome and
fetches each document from INSIDE it with `fetch()`, saving the HTTP response body as the
server sent it. Not the rendered DOM: that would be our rendering of their page (rule 13).
malegislature.gov answers a plain request and is fetched with one.

WHERE IT LANDS. `sources/state-law/<retrieval date>/<publisher filename>`, through
`ingest.land()` -- staged, pushed, read back, then filed. The date folder is not
decoration: a mass.gov or malegislature HTML page carries a per-request token, so its
bytes differ on every fetch, and a dated snapshot is the honest name for "what the state
was serving on this day" (archive_storage.frozen() treats it so). `index.csv` beside it
carries, per document: the label, the publisher URL, the publisher's filename, our copy,
its sha256, the retrieval date and the route it was fetched by. Extracted text goes to
`sources/state-law/text/` and is what `search_minutes.py --corpus law` and
`oml_review.py` read.

LOOKING AGAIN: `--refresh`, the command the daily refresh runs when this source comes due.
A plain run fetches only what is not yet held and never looks at a held document again, so
on its own it cannot notice the AG revising the Guide. `--refresh` re-fetches every
document in DOCS and lands a new dated snapshot ONLY WHERE WHAT THE DOCUMENT SAYS CHANGED:

  * a PDF is compared by its bytes first -- mass.gov serves the same file byte for byte
    (all seven PDFs, checked 28 October 2026) -- and only if those differ is its text extracted
    and compared, so a re-saved file with the same words is not a new version;
  * an HTML page is never compared by its bytes, because they differ on every request (all
    twenty-eight pages, the same day): its document region is extracted by `html_text()` from
    the page just fetched AND from the copy held, by the same code, and compared. A change to
    `html_text()` therefore cannot pass itself off as the state revising a statute.

Unchanged documents land nothing and write nothing. Exit 0 means every document was read;
non-zero means one could not be (mass.gov refusing, a page not answering, Chrome not
starting) and the refresh tries again the next morning. Thirty-five documents: one headless
Chrome session for mass.gov, one plain request a second for the rest -- under three minutes.
"""
import argparse
import csv
import datetime as dt
import hashlib
import html
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
FOLDER = os.path.join(ROOT, 'sources', 'state-law')
TEXT = os.path.join(FOLDER, 'text')
INDEX = os.path.join(FOLDER, 'index.csv')
FIELDS = ['id', 'label', 'publisher', 'upstream', 'publisher_filename', 'local', 'text',
          'bytes', 'sha256', 'retrieved', 'fetched_via', 'read']
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
MASS = 'https://www.mass.gov'
ORIGIN = MASS + '/the-open-meeting-law'
LEG = 'https://malegislature.gov/Laws/GeneralLaws/PartI/TitleIII/Chapter30A/Section%d'

# id, label, url. The id is OURS and stable; it names the text file and is what a review
# cites. The label is what the document is, in the publisher's words where it has some.
AG = 'Attorney General of Massachusetts'
DOCS = [
    ('oml-guide', 'Open Meeting Law Guide and Educational Materials (Attorney General)', AG,
     MASS + '/doc/open-meeting-law-guide-5/download'),
    ('940-cmr-29', '940 CMR 29.00, Open Meeting Law regulations (Attorney General, clean version)', AG,
     MASS + '/doc/new-open-meeting-law-regulations-clean-version/download'),
    ('c30a-18-25-ag-text', 'G.L. c.30A §§18-25, the Open Meeting Law (text as published by the Attorney General)', AG,
     MASS + '/doc/open-meeting-law-text/download'),
    ('oml-landing', 'The Open Meeting Law (Attorney General landing page)', AG, ORIGIN),
    ('oml-faq', 'Frequently asked questions about the Open Meeting Law (Attorney General)', AG,
     MASS + '/info-details/frequently-asked-questions-about-the-open-meeting-law'),
    ('oml-educational-materials', 'Open Meeting Law educational materials (Attorney General)', AG,
     MASS + '/info-details/open-meeting-law-educational-materials'),
    ('oml-notice-checklist', 'OML checklist: notice (Attorney General, 6 Nov 2024)', AG,
     MASS + '/doc/11062024-oml-notice-checklist/download'),
    ('oml-minutes-checklist', 'OML checklist: minutes (Attorney General, 6 Nov 2024)', AG,
     MASS + '/doc/110624-oml-minutes-checklist/download'),
    ('oml-executive-session-checklist', 'OML checklist: executive session (Attorney General, 6 Nov 2024)', AG,
     MASS + '/doc/11062024-oml-executive-session-checklist/download'),
    ('oml-chair-checklist', 'OML checklist: responsibilities of the chair (Attorney General, 6 Nov 2024)', AG,
     MASS + '/doc/11062024-oml-responsibilities-of-the-chair-checklist/download'),
    # NOT HELD: the act itself, /doc/an-act-relative-to-extending-certain-covid-19-measures/
    # download. Its fetch from inside the page did not answer in 90 seconds, twice, on
    # 8 October 2026. The AG's guidance on it, below, is held and quotes what a review needs.
    ('remote-participation-guidance', 'Updated guidance on holding meetings under the act extending certain COVID-19 measures (Attorney General)', AG,
     MASS + '/info-details/updated-guidance-on-holding-meetings-pursuant-to-the-act-extending-certain-covid-19-measures'),
] + [('c30a-%d' % n, 'G.L. c.30A §%d (malegislature.gov)' % n, 'General Court of Massachusetts', LEG % n)
     for n in range(18, 26)]

# REGIONAL SCHOOL DISTRICTS -- not the Open Meeting Law, but the same archive and the same
# route. TJ, 14 October 2026, on whether Lunenburg "chooses" to be in the Monty Tech district:
# the statute and the state's regulations say how a district is formed and how a member town
# leaves; the Montachusett regional agreement itself is not public and is not fetched here.
C71 = 'https://malegislature.gov/Laws/GeneralLaws/PartI/TitleXII/Chapter71/Section%s'
DOCS += [('c71-%s' % n.lower(), 'G.L. c.71 §%s, regional school districts (malegislature.gov)' % n,
          'General Court of Massachusetts', C71 % n)
         for n in ('14', '14A', '14B', '14C', '14D', '15', '16', '16A', '16B', '16C', '16D')]
DOCS += [('603-cmr-41', '603 CMR 41.00, Regional School Districts (DESE regulations)',
          'Massachusetts Department of Elementary and Secondary Education',
          'https://www.doe.mass.edu/lawsregs/603cmr41.html')]
# SCHOOL FINANCE -- the definition of NET SCHOOL SPENDING, which the "What per pupil counts"
# page sets beside DESE's per-pupil figure. TJ, 14 October 2026, after people in town said
# some districts count capital in per-pupil spending and some do not.
C70 = 'https://malegislature.gov/Laws/GeneralLaws/PartI/TitleXII/Chapter70/Section%s'
DOCS += [('c70-2', 'G.L. c.70 §2, definitions including net school spending (malegislature.gov)',
          'General Court of Massachusetts', C70 % '2')]
# The page above is only the regulation's table of contents; the text is behind ?section=all.
DOCS += [('603-cmr-41-all', '603 CMR 41.00, Regional School Districts, all sections (DESE regulations)',
          'Massachusetts Department of Elementary and Secondary Education',
          'https://www.doe.mass.edu/lawsregs/603cmr41.html?section=all')]

# SPECIAL EDUCATION -- the reserve fund and who pays when a placed child moves. TJ, 24 October
# 2026, asking whether the district's account of a 1 April deadline (School Committee minutes,
# 28 February 2024) is true. c.71B §5 is the statute that answers it; c.40 §13E is the Special
# Education Reserve Fund itself, whose cap the SERF report had only as the Town Manager described it.
DOCS += [('c71b-5', 'G.L. c.71B §5, special education costs, and who pays when a placed child moves '
          '(malegislature.gov)', 'General Court of Massachusetts',
          'https://malegislature.gov/Laws/GeneralLaws/PartI/TitleXII/Chapter71B/Section5'),
         ('c40-13e', 'G.L. c.40 §13E, the special education reserve fund (malegislature.gov)',
          'General Court of Massachusetts',
          'https://malegislature.gov/Laws/GeneralLaws/PartI/TitleVII/Chapter40/Section13E')]


def read_index():
    if not os.path.exists(INDEX):
        return {}
    with open(INDEX, encoding='utf-8') as fh:
        return {r['id']: r for r in csv.DictReader(fh)}


def write_index(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    order = [d[0] for d in DOCS]
    for k in sorted(rows, key=lambda k: order.index(k) if k in order else 999):
        w.writerow({f: rows[k].get(f, '') for f in FIELDS})
    tmp = INDEX + '.part'
    open(tmp, 'w', encoding='utf-8', newline='').write(buf.getvalue())
    os.replace(tmp, INDEX)


def via_browser(urls):
    """{url: (status, final_url, content_type, disposition, bytes)} through headless Chrome."""
    with tempfile.TemporaryDirectory() as d:
        env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
        r = subprocess.run(['node', os.path.join(HERE, 'browser_fetch.mjs'), d, ORIGIN] + urls,
                           capture_output=True, text=True, env=env, timeout=600)
        if r.returncode != 0:
            raise SystemExit('browser fetch failed:\n' + (r.stdout + r.stderr)[-2000:])
        out = {}
        for x in json.load(open(os.path.join(d, 'result.json'))):
            if 'file' not in x:
                out[x['requested']] = (0, '', '', '', b'')
                continue
            out[x['requested']] = (x['status'], x['final'], x.get('type') or '',
                                   x.get('disposition') or '', open(x['file'], 'rb').read())
        return out


def via_http(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (lunenburgbudgetproject.org archive)'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return (r.status, r.geturl(), r.headers.get('content-type') or '',
                r.headers.get('content-disposition') or '', r.read())


def publisher_filename(url, disposition, ctype):
    m = re.search(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)", disposition or '')
    if m:
        return urllib.request.unquote(m.group(1)).strip()
    tail = url.rstrip('/').split('/')
    name = tail[-2] if tail[-1] == 'download' else tail[-1]
    ext = '.pdf' if 'pdf' in ctype else '.html'
    return name + ext


# THE TEXT. For HTML, the region that holds the document and nothing else: mass.gov's
# <main>, and on malegislature.gov the section from its heading to the end of its column.
def html_text(raw, url):
    t = raw.decode('utf-8', errors='replace')
    t = re.sub(r'(?is)<(script|style|noscript|svg)\b.*?</\1>', ' ', t)
    # FORMS ARE DROPPED ONLY IF THE PAGE SURVIVES IT. A <form> is usually a search box, but
    # DESE (doe.mass.edu) wraps its WHOLE page in one, so dropping forms deleted 603 CMR 41.00
    # entirely and it extracted to 88 characters (14 October 2026).
    no_forms = re.sub(r'(?is)<form\b.*?</form>', ' ', t)
    if len(re.sub(r'<[^>]+>|\s+', '', no_forms)) > 1500:
        t = no_forms
    if 'malegislature.gov' in url:
        i = t.find('id="skipTo"')
        j = t.find('</main>', i) if i >= 0 else -1
        if i >= 0:
            t = t[t.rfind('<h2', 0, i):j if j > 0 else None]
            k = t.find('<div class="modal')
            t = t[:k] if k > 0 else t
    else:
        m = re.search(r'(?is)<main\b.*?</main>', t)
        # A <main> with almost no text in it is not where the page is: fall back to the
        # whole document rather than keep a header and lose the body.
        if m and len(re.sub(r'<[^>]+>|\s+', '', m.group(0))) > 1500:
            t = m.group(0)
        else:
            t = re.sub(r'(?is)<head\b.*?</head>', ' ', t)   # the whole document less its head
    t = re.sub(r'(?i)<br\s*/?>', '\n', t)
    t = re.sub(r'(?i)</?(p|div|h[1-6]|li|tr|section|article|header|ul|ol|table)\b[^>]*>', '\n', t)
    t = html.unescape(re.sub(r'<[^>]+>', ' ', t)).replace(' ', ' ')
    lines = [re.sub(r'[ \t]+', ' ', ln).strip() for ln in t.splitlines()]
    out, blank = [], False
    for ln in lines:
        if not ln:
            if not blank and out:
                out.append('')
            blank = True
            continue
        out.append(ln)
        blank = False
    return '\n'.join(out).strip() + '\n'


def archival_name(publisher_name):
    """The key's filename. The bucket takes [A-Za-z0-9._-] only, and the AG names its files
    `2025 Guide with ed materials 6-25-25 (Updated Cover).pdf`. So the key is a slug of the
    publisher's name and the name ITSELF is kept, verbatim, in `publisher_filename` -- the
    name a resident asks for when the link dies (rule 12)."""
    stem, ext = os.path.splitext(publisher_name)
    slug = re.sub(r'[^a-z0-9.]+', '-', stem.lower()).strip('-.')
    return slug + ext.lower()


def held_copy(url):
    """An HTML page already secured under a dated folder, by its deterministic name.

    A first run secured eleven pages and then refused the PDFs (their names held spaces), so
    the index was never written for the pages that DID land. Their bytes cannot be fetched
    again identically -- each carries a per-request token -- so they are adopted from the
    archive rather than refetched into a refusal."""
    name = url.rstrip('/').split('/')[-1] + '.html'
    pushed = ingest_pushed()
    for d in sorted(os.listdir(FOLDER), reverse=True) if os.path.isdir(FOLDER) else []:
        key = 'state-law/%s/%s' % (d, name)
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', d) and key in pushed and os.path.exists(os.path.join(ROOT, 'sources', key)):
            return d, key, name
    return None


def ingest_pushed():
    import ingest
    return ingest._pushed()


def extract(local, txt_path, url):
    os.makedirs(os.path.dirname(txt_path), exist_ok=True)
    if local.lower().endswith('.pdf'):
        import pdf_kind
        return pdf_kind.extract_text(local, txt_path)
    open(txt_path, 'w', encoding='utf-8').write(html_text(open(local, 'rb').read(), url))
    return 'html, document region'


def fetch(only=None):
    import ingest
    rows = read_index()
    todo = [d for d in DOCS if d[0] not in rows and (not only or d[0] in only)]
    if not todo:
        print('every document already held; nothing to fetch')
        return 0
    today = dt.date.today().isoformat()
    for d in list(todo):
        got = held_copy(d[3])
        if not got:
            continue
        day, key, name = got
        did, label, publisher, url = d
        local = os.path.join(ROOT, 'sources', key)
        blob = open(local, 'rb').read()
        txt = os.path.join(TEXT, did + '.txt')
        rows[did] = {'id': did, 'label': label, 'publisher': publisher, 'upstream': url,
                     'publisher_filename': name, 'local': os.path.relpath(local, ROOT),
                     'text': os.path.relpath(txt, ROOT), 'bytes': str(len(blob)),
                     'sha256': hashlib.sha256(blob).hexdigest(), 'retrieved': day,
                     'fetched_via': ('plain HTTPS GET' if 'malegislature' in url else
                                     'headless Chrome, fetch() from inside a mass.gov page '
                                     '(mass.gov answers non-browser clients 403)'),
                     'read': extract(local, txt, url)}
        print('  held %-30s %8d bytes  %s  %s' % (did, len(blob), rows[did]['sha256'][:12], key))
        todo.remove(d)
    write_index(rows)
    if not todo:
        return 0
    mass_urls = [u for _, _, _, u in todo if u.startswith(MASS)]
    browser = via_browser(mass_urls) if mass_urls else {}   # nothing on mass.gov: no browser to start
    failed = 0
    for did, label, publisher, url in todo:
        if url.startswith(MASS):
            status, final, ctype, disp, blob = browser[url]
            how = 'headless Chrome, fetch() from inside a mass.gov page (mass.gov answers non-browser clients 403)'
        else:
            status, final, ctype, disp, blob = via_http(url)
            how = 'plain HTTPS GET'
        if status != 200:
            print('  !! %-32s HTTP %s %s' % (did, status, url))
            failed += 1
            continue
        if url.startswith(MASS) and b'<title>Not allowed' in blob[:4000]:
            print('  !! %-32s mass.gov refused (Not allowed page)' % did)
            failed += 1
            continue
        name = publisher_filename(final or url, disp, ctype)
        key = 'state-law/%s/%s' % (today, archival_name(name))
        ok, why = ingest.land(key, blob, url)
        if not ok:
            print('  !! %-32s %s' % (did, why))
            failed += 1
            continue
        local = os.path.join(ROOT, 'sources', key)
        txt = os.path.join(TEXT, did + '.txt')
        read = extract(local, txt, url)
        rows[did] = {'id': did, 'label': label, 'publisher': publisher, 'upstream': url,
                     'publisher_filename': name, 'local': os.path.relpath(local, ROOT),
                     'text': os.path.relpath(txt, ROOT), 'bytes': str(len(blob)),
                     'sha256': hashlib.sha256(blob).hexdigest(), 'retrieved': today,
                     'fetched_via': how, 'read': read}
        print('  ok %-32s %8d bytes  %s  %s' % (did, len(blob), rows[did]['sha256'][:12], name))
        write_index(rows)
    return 1 if failed else 0


def merge_index(changed):
    """Write `changed` rows into the index, re-reading it first. The index is shared with
    fetch_oml_determinations.py, which writes thousands of rows into it; a refresh that wrote
    back the copy it read at the start would drop anything that script added meanwhile."""
    rows = read_index()
    rows.update(changed)
    write_index(rows)


def same_text(did, url, local, blob):
    """Does `blob` say what the held copy at `local` says? Both read by the same extractor."""
    held = open(local, 'rb').read()
    if hashlib.sha256(held).hexdigest() == hashlib.sha256(blob).hexdigest():
        return True
    if not local.lower().endswith('.pdf'):
        return html_text(held, url) == html_text(blob, url)
    if not blob.startswith(b'%PDF'):
        return False
    import pdf_kind
    with tempfile.TemporaryDirectory() as d:
        texts = []
        for n, b in (('held', held), ('new', blob)):
            pdf, txt = os.path.join(d, n + '.pdf'), os.path.join(d, n + '.txt')
            open(pdf, 'wb').write(b)
            pdf_kind.extract_text(pdf, txt)
            texts.append(open(txt, encoding='utf-8', errors='replace').read())
    return texts[0] == texts[1]


def refresh():
    """Fetch anything not yet held, then look again at everything that is (see the docstring)."""
    import time
    import ingest
    failed = fetch()
    rows = read_index()
    today = dt.date.today().isoformat()
    # Anything fetched today has just been read; asking for it again tells us nothing.
    held = [d for d in DOCS if d[0] in rows and rows[d[0]].get('retrieved') != today]
    mass_urls = [u for _, _, _, u in held if u.startswith(MASS)]
    browser = via_browser(mass_urls) if mass_urls else {}
    changed, same = {}, 0
    for did, label, publisher, url in held:
        r = rows[did]
        local = os.path.join(ROOT, r['local'])
        try:
            if url.startswith(MASS):
                status, final, ctype, disp, blob = browser[url]
                how = r['fetched_via']
            else:
                time.sleep(1.0)                      # one plain request a second, at most
                status, final, ctype, disp, blob = via_http(url)
                how = 'plain HTTPS GET'
        except Exception as e:                       # noqa: BLE001 -- counted, not raised
            print('  !! %-32s %s' % (did, e))
            failed = 1
            continue
        if status != 200 or (url.startswith(MASS) and b'<title>Not allowed' in blob[:4000]):
            print('  !! %-32s HTTP %s%s' % (did, status, ' (mass.gov refused)' if status == 200 else ''))
            failed = 1
            continue
        if not os.path.exists(local):
            print('  !! %-32s held copy %s is not on disk (sync_archive.py --pull)' % (did, r['local']))
            failed = 1
            continue
        if same_text(did, url, local, blob):
            same += 1
            continue
        name = publisher_filename(final or url, disp, ctype)
        key = 'state-law/%s/%s' % (today, archival_name(name))
        ok, why = ingest.land(key, blob, url)
        if not ok:
            print('  !! %-32s changed, but could not be secured: %s' % (did, why))
            failed = 1
            continue
        new = os.path.join(ROOT, 'sources', key)
        txt = os.path.join(ROOT, r['text'])
        changed[did] = dict(r, publisher_filename=name, local=os.path.relpath(new, ROOT),
                            bytes=str(len(blob)), sha256=hashlib.sha256(blob).hexdigest(),
                            retrieved=today, fetched_via=how, read=extract(new, txt, url))
        print('  CHANGED %-28s was %s, now %s' % (did, r['retrieved'], key))
    if changed:
        merge_index(changed)
    print('open meeting law: %d looked at again, %d unchanged, %d changed%s'
          % (len(held), same, len(changed), '' if not failed else '; some could not be read'))
    return 1 if failed else 0


def check():
    rows = read_index()
    bad = []
    for d in DOCS:
        r = rows.get(d[0])
        if not r:
            bad.append('%s: not held' % d[0])
            continue
        p = os.path.join(ROOT, r['local'])
        if not os.path.exists(p):
            bad.append('%s: %s missing on disk (sync_archive.py --pull)' % (d[0], r['local']))
        elif hashlib.sha256(open(p, 'rb').read()).hexdigest() != r['sha256']:
            bad.append('%s: sha256 differs from index' % d[0])
        t = os.path.join(ROOT, r['text'])
        if not os.path.exists(t) or len(open(t, encoding='utf-8').read().strip()) < 200:
            bad.append('%s: extracted text missing or near-empty' % d[0])
    for b in bad:
        print('  !!', b)
    print('open meeting law: %d of %d documents held, hashed and extracted' % (len(DOCS) - len(bad), len(DOCS))
          if not bad else '%d problem(s)' % len(bad))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--only', nargs='*')
    ap.add_argument('--reextract', action='store_true', help='rewrite the text from the held copies')
    ap.add_argument('--refresh', action='store_true',
                    help='also re-fetch every held document; land a new snapshot only where its text changed')
    a = ap.parse_args()
    if a.check:
        return check()
    if a.refresh:
        return refresh()
    if a.reextract:
        rows = read_index()
        for r in rows.values():
            r['read'] = extract(os.path.join(ROOT, r['local']), os.path.join(ROOT, r['text']), r['upstream'])
        write_index(rows)
        return check()
    return fetch(a.only)


if __name__ == '__main__':
    sys.exit(main())
