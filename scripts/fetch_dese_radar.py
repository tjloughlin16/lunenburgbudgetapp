"""Fetch DESE's RADAR district comparison and Lunenburg's finance profile, and catalogue them.

    python3 scripts/fetch_dese_radar.py

Lands through `ingest.land_version()` into `sources/state-dese/`, catalogues in
`sources/state-dese/index.csv`, and records the sha256 of each version at the moment it was taken.

WHY THESE TWO DOCUMENTS

Every figure this project holds about school spending comes from the town's GENERAL FUND:
the appropriation, and the district's own budget documents about it. Grants, revolving
funds, school choice and gifts pay for real staff and appear nowhere in any of it. That is
rule 11, and it is the largest hole in the archive.

These are the first independent, ALL-FUNDS view of Lunenburg's school spending. They do
not close the hole -- neither one maps a fund onto a budget line -- but they bound it from
outside, from a publisher who is not the district.

WHY NOT THE END OF YEAR FINANCIAL REPORT ITSELF

Because DESE does not publish it. `doe.mass.edu/finance/accounting/eoy/` looks like the
right page and is a SUBMISSION portal: blank forms, instructions, a certification page.
The schedules districts file -- including Schedule 1, which separates revenues and
expenditures by source of funds and is the document that would actually answer this --
are not published per district. Lunenburg files it, so Lunenburg holds it, and a records
request to the district is a shorter path than DESE. Recorded here so that nobody spends
another afternoon looking for a public download that does not exist.

WHAT THESE FIGURES ARE NOT

DESE's "in-district expenditures" is NOT the town's school appropriation and the two must
never be subtracted from one another to produce "hidden money". DESE counts costs the
school budget does not carry -- town-paid insurance and retirement attributed to the
schools is $3,459 per pupil on its own. Reconciling DESE's definition to the town's
appropriation is a separate piece of work that has not been done. Until it is, these are a
second opinion, not a comparison.

BOTH ARE OVERWRITTEN IN PLACE, so both go through `ingest.land_version()`: a changed file is
landed as a dated version (`state-dese/<YYYY-MM-DD>/<name>`) and the fixed name becomes the
working copy the extractors read. An UNCHANGED one lands nothing, which is what lets this run
unattended -- and "unchanged" has to mean something different for each:

  * the workbook is a static file, byte-stable between requests (28 October 2026: two
    fetches, sha256 0391c2d3..., identical to ours; Last-Modified 29 July 2026), so bytes
    decide it;
  * the profile page is not. Between our 5 September copy and 28 October it changed only in
    DESE's site chrome -- `Release 9.28.0.0` became `Release 9.35.0.0`, and a banner comment
    appeared -- with every figure the same. Comparing bytes would land a new "version" each
    time DESE ships a release of its website. So the page is compared on its TEXT, with the
    release number, scripts, styles and comments taken out; only a change in what it says
    lands a version.

Exit 0 when both were looked at, changed or not; non-zero when either could not be fetched or
did not validate.
"""
import csv
import glob
import hashlib
import io
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESE = os.path.join(ROOT, 'sources', 'state-dese')
INDEX = os.path.join(DESE, 'index.csv')

UA = {'User-Agent': ('Mozilla/5.0 (compatible; LunenburgBudgetProject/1.0; '
                     '+https://lunenburgbudgetproject.org)')}

# Lunenburg's DESE organisation code. Checked against the educator-contract endpoints
# already in the archive, which take it in the URL and were verified by download.
ORG = '01620000'

WANTED = [
    dict(local='radar-district-comparison.xlsx',
         upstream='https://www.doe.mass.edu/research/radar/district-comparison.xlsx',
         publisher_name='district-comparison.xlsx',
         read='budget-workbooks',
         label='DESE RADAR district comparison — spending by function, all funds, '
               'every district, FY2021-FY2025'),
    dict(local='lunenburg-finance-profile.html',
         upstream=('https://profiles.doe.mass.edu/profiles/finance.aspx'
                   f'?orgcode={ORG}&orgtypecode=5&dropDownOrgCode=2'),
         publisher_name='finance.aspx',
         read='html',
         label='DESE school and district profiles — Lunenburg per pupil expenditures, '
               'all funds'),
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def fetch(url, local):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as res:
        body = res.read()
        ctype = res.headers.get('content-type', '')
    # Rule 13: a URL whose title matches is a candidate. The check is what came back.
    # An HTML body where a spreadsheet was expected is a sign-in wall or an error page,
    # and it must not be landed over a good copy.
    if local.endswith('.xlsx') and not body.startswith(b'PK'):
        raise SystemExit(f'{url}\n  expected a spreadsheet, got {ctype} '
                         f'({len(body)} bytes). Nothing landed.')
    if local.endswith('.html') and (b'<' not in body[:512] or ORG.encode() not in body):
        raise SystemExit(f'{url}\n  expected Lunenburg\'s profile page, got {ctype}. '
                         'Nothing landed.')
    return body, ctype


def text_of(blob):
    """What a page SAYS, for deciding whether it changed. Never stored; never quoted."""
    t = blob.decode('utf-8', 'replace')
    t = re.sub(r'(?is)<(script|style)\b.*?</\1>', ' ', t)
    t = re.sub(r'(?s)<!--.*?-->', ' ', t)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'Release \d+(\.\d+)+', ' ', t)
    return ' '.join(t.split())


def same(local, old, new):
    if old is None:
        return False
    return (text_of(old) == text_of(new)) if local.endswith('.html') else old == new


def catalogue(entries):
    """Add or refresh our rows of the SHARED index: re-read just before writing, newline
    convention kept, replaced atomically, and not written at all when nothing changed."""
    raw = open(INDEX, 'rb').read()
    nl = '\r\n' if b'\r\n' in raw else '\n'
    rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8'))))
    fields = list(rows[0].keys())
    by_local = {r['local']: r for r in rows}
    for e in entries:
        if e['local'] in by_local:
            by_local[e['local']].update(e)
        else:
            rows.append(e)
            by_local[e['local']] = e
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=fields, lineterminator=nl)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, '') for k in fields})
    tmp = INDEX + '.tmp'
    open(tmp, 'wb').write(out.getvalue().encode('utf-8'))
    os.replace(tmp, INDEX)


def main():
    import ingest
    print('Fetching DESE all-funds sources\n')
    entries, failed = [], 0
    for n, w in enumerate(WANTED):
        if n:
            time.sleep(1)
        key = 'state-dese/' + w['local']
        path = os.path.join(DESE, w['local'])
        body, ctype = fetch(w['upstream'], w['local'])
        old = open(path, 'rb').read() if os.path.exists(path) else None
        if same(w['local'], old, body):
            print(f"  {w['local']:36} {len(body):>9,} bytes  unchanged")
            continue
        ok, why = ingest.land_version(key, body, w['upstream'])
        if not ok:
            print(f"  !! {key}: {why}")
            failed += 1
            continue
        digest = hashlib.sha256(body).hexdigest()
        print(f"  {w['local']:36} {len(body):>9,} bytes  {ctype.split(';')[0]:40} "
              f"{'new' if old is None else 'CHANGED -- a new version landed'}")
        print(f"    {digest}")
        row = dict(label=w['label'], upstream=w['upstream'], local=os.path.relpath(path, ROOT),
                   text='', bytes=str(len(body)), sha256=digest, read=w['read'])
        entries.append(row)
        # The dated version is a source in its own right and is catalogued as one.
        for k in glob.glob(os.path.join(DESE, '[0-9]' * 4 + '-*', '*' + os.path.splitext(w['local'])[1])):
            if os.path.basename(k).startswith(os.path.splitext(w['local'])[0]) and \
                    hashlib.sha256(open(k, 'rb').read()).hexdigest() == digest:
                entries.append(dict(row, local=os.path.relpath(k, ROOT),
                                    label=w['label'] + ' (version fetched %s)'
                                    % os.path.basename(os.path.dirname(k))))
    if entries:
        catalogue(entries)
        print(f'\ncatalogued {len(entries)} rows in {os.path.relpath(INDEX, ROOT)}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
