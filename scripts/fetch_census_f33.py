#!/usr/bin/env python3
"""The Census Bureau's own definitions of its school-finance items: the FY2024 form F-33 and
the FY2024 technical documentation, landed through `ingest` and read to text.

    python3 scripts/fetch_census_f33.py           # fetch, land what changed, extract text
                                                  #   (the refresh runs exactly this)
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
The documentation was already held; fetching it again lands nothing if the bytes match, and
lands a VERSION if they do not (below) -- so a run that changes something is also the news
that our copy is no longer census.gov's current one.

RUN UNATTENDED, ON A CADENCE. Both files are byte-stable between requests (28 October 2026:
the PDF and the .docx each fetched again, sha256 identical to our copies; census.gov's
Last-Modified is 26 September 2025 and 7 May 2026). So the bytes ARE the test here:
identical bytes land nothing and the text is not re-extracted. Different bytes at the same
address are census.gov replacing its own file in place -- an erratum, a re-issue -- and are
landed as a version with `ingest.land_version()`, rather than refused, so the refresh keeps
the new copy and the bucket keeps the old one under the plain name.

A NEW SURVEY YEAR IS REPORTED, NOT FETCHED. Census publishes the next year's form and
documentation under new addresses (`.../questionnaires/2025/f33_2025_508.pdf`). The run asks
whether they exist yet and says so, exiting 0 because it looked. It does not land them:
census_revenue.py reads the 2024 files by name, the data file `census-elsec24.xlsx` is
survey-year 2024 too, and build_source_index.py catalogues each file by name -- so a new
year is a change to the pages and belongs to a person.
"""
import argparse
import hashlib
import os
import re
import sys
import urllib.error
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


UA = {'User-Agent': 'Mozilla/5.0 (lunenburgbudgetproject.org)'}


def get(url):
    """The file at `url`, or fail() -- which exits non-zero, the refresh's could-not-look."""
    try:
        return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()
    except (urllib.error.URLError, TimeoutError) as e:
        fail('%s: %s' % (url, e))


def exists(url):
    """Does census.gov answer for this address yet? A 404 is an answer (no); anything
    else that is not a 200 means we could not tell, and fails the run."""
    try:
        urllib.request.urlopen(urllib.request.Request(url, headers=UA, method='HEAD'), timeout=60)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        fail('%s: HTTP %s' % (url, e.code))
    except (urllib.error.URLError, TimeoutError) as e:
        fail('%s: %s' % (url, e))


def newer_survey_years():
    """Survey years after 2024 whose form census.gov now publishes. The form for year Y
    appears during Y+1 at the earliest, so the candidates stop at last year."""
    import datetime
    return [y for y in range(2025, datetime.date.today().year)
            if exists(W2 + 'technical-documentation/questionnaires/%d/f33_%d_508.pdf' % (y, y))]


def run():
    import ingest
    for key, url, txt in DOCS:
        blob = get(url)
        local = os.path.join(SRC, key)
        sha = hashlib.sha256(blob).hexdigest()
        if os.path.exists(local) and open(local, 'rb').read() == blob:
            why = 'unchanged'
        else:
            # Not held: a first landing. Held with other bytes: census.gov replaced it in
            # place, and land_version keeps both rather than refusing the new one.
            land = ingest.land if not os.path.exists(local) else ingest.land_version
            ok, why = land(key, blob, url)
            if not ok:
                fail('%s: %s' % (key, why))
            why = why or 'landed'
        print('%-44s %s  %s' % (key, sha[:12], why))
        t = os.path.join(TEXT, txt)
        if why != 'unchanged' or not os.path.exists(t):
            print('  text: %s (%s)' % (os.path.join('sources/state-census/text', txt), extract(key, txt)))
    for y in newer_survey_years():
        print('NOTICE: census.gov now publishes the F-33 for survey year %d; this project '
              'reads 2024. Moving to it is a decision about the pages -- see the docstring.' % y)


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
        have = A.hash_file(p)[0]
        # After census.gov replaces a file, the plain name is a working copy holding the
        # newest version, and the manifest row that matches it is the dated one.
        versions = {s for k, s in man.items()
                    if re.fullmatch(r'state-census/\d{4}-\d{2}-\d{2}/' + re.escape(os.path.basename(key)), k)}
        if man.get(key) != have and not (key in A.working_copies() and have in versions):
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
