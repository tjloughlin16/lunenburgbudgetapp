#!/usr/bin/env python3
"""The Census Bureau's own definitions of its school-finance items: the FY2024 form F-33 and
the FY2024 technical documentation, landed through `ingest` and read to text.

    python3 scripts/fetch_census_f33.py           # fetch, land, extract text
    python3 scripts/fetch_census_f33.py --check   # every held file: sha256, text present

WHY. `/monty-tech/monty-tech-revenue` carried one row, "Other local: tuition, fees, interest,
other", that was a remainder of six Census items with codes like A07 and U97. TJ, 23 October
2026: *"that's a huge number and not to know what it represents is hard... like what is A07
Tuition?! U97?!"* The answer is in two Census documents, and `census_revenue.py` now reads
both rather than a label typed from memory:

  * THE CODE -> NAME MAPPING comes from the technical documentation (`school24doc.docx`), whose
    TLOCREV entry lists each local item's code beside its name. That is the authoritative
    pairing. The F-33 FORM prints the codes in a column separate from the line labels, so
    pairing a code with a label by position on the form would be reading a position as a
    name (CLAUDE.md 13b) -- it is used here only for what each line MEANS.
  * WHAT EACH ITEM MEANS comes from the form's own instructions, "Part I - REVENUE, Section A
    - FROM LOCAL SOURCES", page 8 of the FY2024 F-33.

Both are census.gov's own files for survey year 2024, the year `census-elsec24.xlsx` reports.
The documentation was already held; landing it again is a no-op if the bytes match, and is
REFUSED if they do not, which is the check that our copy is still census.gov's.
"""
import argparse
import hashlib
import os
import re
import sys
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'sources')
TEXT = os.path.join(SRC, 'state-census', 'text')

W2 = 'https://www2.census.gov/programs-surveys/school-finances/'
# key, upstream, text file. The key keeps the publisher's filename after our `census-` prefix,
# as census-elsec24.xlsx and census-school24doc.docx already do.
DOCS = [
    ('state-census/census-f33_2024_508.pdf',
     W2 + 'technical-documentation/questionnaires/2024/f33_2024_508.pdf',
     'census-f33_2024_508.txt'),
    ('state-census/census-school24doc.docx',
     W2 + 'tables/2024/secondary-education-finance/school24doc.docx',
     'census-school24doc.txt'),
]
# Where census.gov lists the form, for a reader whose link has died.
INDEX_PAGE = ('https://www.census.gov/programs-surveys/school-finances/technical-documentation/'
              'questionnaires.2024.html')


def fail(msg):
    raise SystemExit('fetch_census_f33: ' + msg)


def docx_text(path):
    """One line per paragraph, in body order -- table cells included, since the item lists are
    tables. Plain zip + XML so the reading has no dependency to drift."""
    xml = zipfile.ZipFile(path).read('word/document.xml').decode('utf-8')
    xml = re.sub(r'<w:tab/>', '\t', xml)
    xml = re.sub(r'</w:p>', '\n', xml)
    t = re.sub(r'<[^>]+>', '', xml)
    for a, b in (('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'), ('&quot;', '"'), ('&apos;', "'")):
        t = t.replace(a, b)
    return t


def extract(key, txt):
    local = os.path.join(SRC, key)
    os.makedirs(TEXT, exist_ok=True)
    out = os.path.join(TEXT, txt)
    if key.endswith('.pdf'):
        import pdf_kind
        how = pdf_kind.extract_text(local, out + '.tmp')
        os.replace(out + '.tmp', out)
        return how
    with open(out + '.tmp', 'w', encoding='utf-8') as fh:
        fh.write(docx_text(local))
    os.replace(out + '.tmp', out)
    return 'docx paragraphs'


def run():
    import ingest
    for key, url, txt in DOCS:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (lunenburgbudgetproject.org)'})
        blob = urllib.request.urlopen(req, timeout=120).read()
        ok, why = ingest.land(key, blob, url)
        if not ok:
            fail('%s: %s' % (key, why))
        print('%-44s %s  %s' % (key, hashlib.sha256(blob).hexdigest()[:12], why or 'landed'))
        print('  text: %s (%s)' % (os.path.join('sources/state-census/text', txt), extract(key, txt)))


def check():
    import archive_storage as A
    bad = []
    man = {}
    import csv
    for r in csv.DictReader(open(os.path.join(SRC, 'data', 'archive-manifest.csv'), encoding='utf-8')):
        man[r['key']] = r['sha256']
    for key, url, txt in DOCS:
        p = os.path.join(SRC, key)
        if not os.path.exists(p):
            bad.append('%s not on disk; sync_archive.py --pull' % key)
            continue
        if man.get(key) != A.hash_file(p)[0]:
            bad.append('%s does not match its manifest row' % key)
        t = os.path.join(TEXT, txt)
        if not os.path.exists(t) or os.path.getsize(t) < 1000:
            bad.append('%s has no text at %s' % (key, t))
    if bad:
        fail('\n  '.join([''] + bad))
    print('fetch_census_f33: %d documents held, hashed and read to text' % len(DOCS))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    check() if a.check else run()
