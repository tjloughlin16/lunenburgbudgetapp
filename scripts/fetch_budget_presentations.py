#!/usr/bin/env python3
"""THE DEPARTMENT BUDGET PRESENTATIONS, fetched and catalogued by DocumentCenter id.

    python3 scripts/fetch_budget_presentations.py 3584 [3585 ...]
    python3 scripts/fetch_budget_presentations.py --check

TJ, 22 September 2026: *"you should ingest that PD presentation. we have it. dont wait."*

WHY THESE ARE WORTH THEIR OWN INGEST. A department's budget presentation is the only
place it draws ITS OWN organisational chart, and the Police Department's FY27 deck --
presented 19 February 2026 -- does three things no annual report does:

  it lays the department out the way the department is ORGANISED: the Chief, then the
  Administrative Lieutenant and the office, then Day, Evening and Night Shift, the
  Investigative Bureau, Community Policing, Split Shift, Traffic Bureau, the Reserve
  Officers and a Civilian Traffic Unit side by side, each headed by its sergeant;

  it names people the FY2025 annual report does not -- a Front Desk Clerk, a five-person
  Civilian Traffic Unit;

  and IT MARKS EVERY POST `Funded` OR `Funded - Vacant`, which is the
  ESTABLISHMENT-versus-HEADCOUNT distinction this project has said all year the town
  publishes nowhere. A roster names who is there; an establishment names the posts. Only
  the DPW and the Assessing office publish the second, which is why a department that
  shrank and a department that could not hire look identical everywhere else.

ONE DEPARTMENT IS NOT THE SET, and the rest arrive in about two weeks (A0b in the queue).
This takes ids so the others slot in beside this one rather than being ingested a
different way later.
"""
import argparse
import csv
import hashlib
import io
import os
import re
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
FOLDER = os.path.join(ROOT, 'sources', 'town-supplementary')
DOCS, TEXT = os.path.join(FOLDER, 'docs'), os.path.join(FOLDER, 'text')
INDEX = os.path.join(FOLDER, 'index.csv')
VIEW = 'https://www.lunenburgma.gov/DocumentCenter/View/%s'
FIELDS = ['label', 'upstream', 'local', 'text', 'bytes', 'sha256', 'read']
UA = {'User-Agent': 'lunenburgbudgetproject.org (public records archive)'}


def fetch(did):
    """The bytes, and the publisher's own filename out of the redirect."""
    req = urllib.request.Request(VIEW % did, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        blob, final = r.read(), r.geturl()
        disp = r.headers.get('content-disposition', '')
    name = ''
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', disp)
    if m:
        name = m.group(1)
    if not name:
        name = re.sub(r'\?.*$', '', final.rsplit('/', 1)[-1])
    # The publisher's filename arrives percent-encoded in the URL.
    return blob, urllib.parse.unquote(name)


def slug(s):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s.lower())).strip('-')


def catalogue(rows):
    """Append to the shared index. Re-read first; never rewrite what is already there."""
    raw = open(INDEX, 'rb').read()
    nl = '\r\n' if b'\r\n' in raw else '\n'
    have = list(csv.DictReader(io.StringIO(raw.decode('utf-8'))))
    known = {r['local'] for r in have}
    added = [r for r in rows if r['local'] not in known]
    if not added:
        return 0
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=FIELDS, lineterminator=nl)
    w.writeheader()
    w.writerows(have + added)
    open(INDEX, 'wb').write(out.getvalue().encode('utf-8'))
    return len(added)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ids', nargs='*', help='DocumentCenter ids, e.g. 3584')
    ap.add_argument('--label', default='', help='override the label for a single id')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    if a.check:
        have = {r['local']: r for r in csv.DictReader(open(INDEX, encoding='utf-8'))}
        bad = []
        for f in sorted(os.listdir(DOCS)):
            if 'budget-presentation' not in f:
                continue
            rel = os.path.relpath(os.path.join(DOCS, f), ROOT)
            row = have.get(rel)
            if not row:
                bad.append('%s is on disk and in no catalogue' % rel)
            elif hashlib.sha256(open(os.path.join(DOCS, f), 'rb').read()).hexdigest() \
                    != row['sha256']:
                bad.append('%s has changed since it was catalogued' % rel)
        for b in bad:
            print(b)
        return 1 if bad else 0

    import fetch_town_docs as T
    os.makedirs(DOCS, exist_ok=True)
    os.makedirs(TEXT, exist_ok=True)
    rows = []
    for did in a.ids:
        blob, published = fetch(did)
        # THE PUBLISHER'S OWN FILENAME, kept in the name we save it under. Links die --
        # 57 of ours did in one day -- and when they do, asking the town for a document
        # BY THE NAME IT USES is the only route a resident has.
        base = '%s-%s' % (did, slug(os.path.splitext(published)[0] or 'document'))
        path = os.path.join(DOCS, base + '.pdf')
        open(path, 'wb').write(blob)
        txt = os.path.join(TEXT, base + '.txt')
        try:
            T.extract(path, txt)
        except Exception as e:                                   # noqa: BLE001
            print('  text extraction failed for %s: %s' % (base, e))
            txt = ''
        rows.append(dict(
            label=a.label or published.replace('-', ' ').replace('.pdf', '').strip(),
            upstream=VIEW % did, local=os.path.relpath(path, ROOT),
            text=os.path.relpath(txt, ROOT) if txt and os.path.exists(txt) else '',
            bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest(), read=''))
        print('%s  %s  %d bytes  sha256 %s'
              % (did, published, len(blob), rows[-1]['sha256'][:16]))
    n = catalogue(rows)
    print('%d fetched, %d newly catalogued' % (len(rows), n))
    return 0


if __name__ == '__main__':
    sys.exit(main())
