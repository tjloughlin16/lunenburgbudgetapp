"""Fetch DESE's RADAR district comparison and Lunenburg's finance profile, and catalogue them.

    python3 scripts/fetch_dese_radar.py

Writes into `sources/state-dese/`, appends to `sources/state-dese/index.csv`, and records the sha256
of each file at the moment it was taken.

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
"""
import csv
import hashlib
import os
import sys
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


def fetch(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as res:
        body = res.read()
        ctype = res.headers.get('content-type', '')
    # Rule 13: a URL whose title matches is a candidate. The check is what came back.
    # An HTML body where a spreadsheet was expected is a sign-in wall or an error page,
    # and it must not be written over a good copy.
    if dest.endswith('.xlsx') and not body.startswith(b'PK'):
        raise SystemExit(f'{url}\n  expected a spreadsheet, got {ctype} '
                         f'({len(body)} bytes). Nothing written.')
    if dest.endswith('.html') and b'<' not in body[:512]:
        raise SystemExit(f'{url}\n  expected HTML, got {ctype}. Nothing written.')
    with open(dest, 'wb') as fh:
        fh.write(body)
    return len(body), ctype


def main():
    os.makedirs(DESE, exist_ok=True)
    rows = list(csv.DictReader(open(INDEX, encoding='utf-8')))
    fields = list(rows[0].keys())
    by_local = {r['local']: r for r in rows}

    print('Fetching DESE all-funds sources\n')
    for w in WANTED:
        dest = os.path.join(DESE, w['local'])
        rel = os.path.relpath(dest, ROOT)
        prior = by_local.get(rel, {}).get('sha256')
        n, ctype = fetch(w['upstream'], dest)
        digest = sha256(dest)
        state = ('new' if not prior else
                 'unchanged' if prior == digest else 'CHANGED since last fetch')
        print(f"  {w['local']:36} {n:>9,} bytes  {ctype.split(';')[0]:52} {state}")
        print(f"    {digest}")
        row = dict(label=w['label'], upstream=w['upstream'], local=rel, text='',
                   bytes=str(n), sha256=digest, read=w['read'])
        if rel in by_local:
            by_local[rel].update(row)
        else:
            rows.append(row)
            by_local[rel] = row

    with open(INDEX, 'w', newline='', encoding='utf-8') as fh:
        wtr = csv.DictWriter(fh, fieldnames=fields)
        wtr.writeheader()
        for r in rows:
            wtr.writerow({k: r.get(k, '') for k in fields})
    print(f'\ncatalogued {len(rows)} DESE sources in {os.path.relpath(INDEX, ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
