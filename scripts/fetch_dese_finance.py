#!/usr/bin/env python3
"""DESE's three district-finance datasets: catalogue them, and record how to get them again.

    python3 scripts/fetch_dese_finance.py              # verify what we hold, print the registry
    python3 scripts/fetch_dese_finance.py --adopt DIR  # ingest the portal downloads from DIR
    python3 scripts/fetch_dese_finance.py --api        # re-download from the API and compare
    python3 scripts/fetch_dese_finance.py --check      # registry reproduces; every sha256 holds

WHY THESE THREE

`cnfs-edqq`, District Expenditures by Function Code, is the one that matters. It prints
`GEN_FUND` and `GRNTS_REVOLV` as SEPARATE COLUMNS, per DESE function code, per district,
per year, 2009-2025. Rule 11 says the district's budget documents show the general fund
and nothing else, so a line that rises because a grant ended looks identical to a line
that rises because the district grew, and it names DESE's End of Year Financial Report as
the document that would settle it. This is that split, published, for every district.

It does NOT close the gap. What it gives is the split by DESE FUNCTION CODE; the question
rule 11 asks is which fund pays which BUDGET LINE, and a function code is not a budget
line. It bounds the answer -- see `sources/data/money-gaps.csv`.

`er3w-dyti` and `i5up-aez6` are the same measures at district and SCHOOL level:
enrollment, demographics, staffing FTE, MCAS and per-pupil expenditure by function.

**`er3w-dyti` supersedes `dese_measure` on coverage and agrees with it exactly.** The
RADAR workbook already in the archive is the same measures for seven districts;
`extract_dese_finance.py` asserts all 2,982 values agree, and this dataset carries 421
districts and 17 years. Nothing is deleted -- `dese_measure` is what the site already
quotes -- but a second answer is not what this is.

WHERE THE FILES CAME FROM, AND WHY NOT THE API

The API works and is recorded below, but `$limit` and `$where` on the v3 `views/.../query`
route are ignored, so a filtered request returns the whole dataset anyway. The copies here
came off the portal's own Export button on 8 September 2026. Both routes were compared
row for row and are identical -- run `--api` to repeat that.

So each dataset carries FOUR addresses, and they are different things:

  * `portal_page`   -- where a person goes, and where the field descriptions live
  * `api_endpoint`  -- how a program refreshes it
  * `dataset_id`    -- the Socrata identity, which survives a retitling
  * `publisher_name`-- the filename the Export button produced, which is what somebody
                       asks DESE for when the rest of it has moved

The browser appended ` (1)` to one download because a file of that name was already in
the folder. That suffix is the browser's, not DESE's, and the publisher name recorded
below is the one without it.
"""
import argparse
import csv
import hashlib
import os
import shutil
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESE = os.path.join(ROOT, 'sources', 'state-dese')
INDEX = os.path.join(DESE, 'index.csv')
REGISTRY = os.path.join(DESE, 'socrata-datasets.csv')

PORTAL = 'https://educationtocareer.data.mass.gov'
UA = {'User-Agent': ('Mozilla/5.0 (compatible; LunenburgBudgetProject/1.0; '
                     '+https://lunenburgbudgetproject.org)')}

# The registry. Everything needed to get any of these again without rediscovering it.
DATASETS = [
    dict(
        dataset_id='cnfs-edqq',
        title='District Expenditures by Function Code',
        local='district-expenditures-by-function.xlsx',
        publisher_name='District_Expenditures_by_Function_Code_20260908.xlsx',
        downloaded='2026-09-08',
        columns=('SY DIST_CODE DIST_NAME FUNC_CAT_CODE FUNC_CAT_DESC FUNC_CODE FUNC_DESC '
                 'IN_OUT_DIST GEN_FUND GRNTS_REVOLV TOT_EXP PER_PUPIL_EXP'),
        offers=('Spending by DESE function code, per district, per year 2009-2025, with '
                'the general fund and grants/revolving money in SEPARATE columns. The '
                'only published split of the two this project has found. Rollup rows sit '
                'beside detail rows in the same file and nothing in the column names says '
                'which is which -- see extract_dese_finance.py.'),
        label=('DESE district expenditures by function code, SY2009-SY2025 — general fund '
               'and grants/revolving as separate columns, every Massachusetts district'),
    ),
    dict(
        dataset_id='er3w-dyti',
        title='District Expenditures by Spending Category',
        local='district-expenditures-by-spending-category.xlsx',
        publisher_name='District_Expenditures_by_Spending_Category_20260908.xlsx',
        downloaded='2026-09-08',
        columns='SY DIST_CODE DIST_NAME IND_CAT IND_SUBCAT IND_VALUE IND_VALUE_TYPE',
        offers=('Enrollment, demographics, staffing FTE, MCAS and per-pupil expenditure '
                'by function, per district, per year. The same measures as the RADAR '
                'workbook behind `dese_measure`, for all 421 districts rather than seven; '
                'checked value for value and they agree exactly. Percentages are printed '
                'here as 57.0 where the workbook stores 0.57.'),
        label=('DESE district expenditures by spending category, SY2009-SY2025 — the '
               'RADAR measures for every district; supersedes the seven-district workbook'),
    ),
    dict(
        dataset_id='i5up-aez6',
        title='School Expenditures by Spending Category',
        local='school-expenditures-by-spending-category.xlsx',
        publisher_name='School_Expenditures_by_Spending_Category_20260908.xlsx',
        downloaded='2026-09-08',
        columns=('SY DIST_CODE DIST_NAME ORG_CODE ORG_NAME GRADES_SERVED IND_CAT '
                 'IND_SUBCAT IND_VALUE IND_VALUE_TYPE'),
        offers=('The same measures again, but PER SCHOOL -- org code, school name and '
                'grades served. A granularity this archive has never held: the town '
                'budget and every DESE table above it are district-wide. Catalogued and '
                'not yet extracted; nothing here reads it.'),
        label=('DESE school expenditures by spending category, SY2009-SY2025 — per-school '
               'rather than per-district'),
    ),
]

FIELDS = ['dataset_id', 'title', 'portal_page', 'api_endpoint', 'local', 'publisher_name',
          'downloaded', 'bytes', 'sha256', 'rows', 'columns', 'offers']


def portal_page(d):
    return f"{PORTAL}/d/{d['dataset_id']}"


def api_endpoint(d):
    # The `resource` route, which -- unlike the v3 `views/<id>/query.json` route -- does
    # honour $where and $limit. Checked: DIST_CODE=01620000 returned 1,089 rows, not
    # 363,514. Recorded without parameters because the whole dataset is what we mirror.
    return f"{PORTAL}/resource/{d['dataset_id']}.csv"


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def data_rows(path):
    """How many data rows the workbook holds. Read once, at adopt time.

    Not recomputed on --check, deliberately: re-opening three workbooks totalling 60MB
    costs four minutes, and the sha256 already proves the bytes have not moved. A row
    count that cannot change without the hash changing does not need re-deriving; saying
    so here rather than leaving it to look like an omission.
    """
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb['Data']
    n = sum(1 for _ in ws.iter_rows(values_only=True)) - 1
    wb.close()
    return n


def read_registry():
    if not os.path.exists(REGISTRY):
        return {}
    return {r['dataset_id']: r for r in csv.DictReader(open(REGISTRY, encoding='utf-8'))}


def build_registry(adopt_rows=None):
    """The registry as it should be, from DATASETS plus what is on disk."""
    prior = read_registry()
    out = []
    for d in DATASETS:
        path = os.path.join(DESE, d['local'])
        row = dict(dataset_id=d['dataset_id'], title=d['title'], portal_page=portal_page(d),
                   api_endpoint=api_endpoint(d),
                   local=os.path.relpath(path, ROOT), publisher_name=d['publisher_name'],
                   downloaded=d['downloaded'], columns=d['columns'], offers=d['offers'])
        if os.path.exists(path):
            row['bytes'] = str(os.path.getsize(path))
            row['sha256'] = sha256(path)
        else:
            row['bytes'] = row['sha256'] = ''
        if adopt_rows and d['dataset_id'] in adopt_rows:
            row['rows'] = str(adopt_rows[d['dataset_id']])
        else:
            row['rows'] = prior.get(d['dataset_id'], {}).get('rows', '')
        out.append(row)
    return out


def render(rows):
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, '') for k in FIELDS})
    return buf.getvalue()


def catalogue(rows):
    """index.csv is the archive's own catalogue. A file not in it is not a source."""
    have = list(csv.DictReader(open(INDEX, encoding='utf-8')))
    fields = list(have[0].keys())
    by_local = {r['local']: r for r in have}
    for d, r in zip(DATASETS, rows):
        if not r['sha256']:
            continue
        row = dict(label=d['label'], upstream=r['api_endpoint'], local=r['local'], text='',
                   bytes=r['bytes'], sha256=r['sha256'], read='xlsx')
        if r['local'] in by_local:
            by_local[r['local']].update(row)
        else:
            have.append(row)
            by_local[r['local']] = row
    with open(INDEX, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in have:
            w.writerow({k: r.get(k, '') for k in fields})
    return len(have)


def adopt(src_dir):
    """Copy the portal downloads in under stable names, and record what they were called.

    A download folder is not an address. The publisher's filename is (rule 12), and it is
    in DATASETS above; the local name is ours and is stable so that nothing downstream
    has to know what day the file was exported.
    """
    counts = {}
    for d in DATASETS:
        dest = os.path.join(DESE, d['local'])
        cands = [d['publisher_name'],
                 d['publisher_name'].replace('.xlsx', ' (1).xlsx'),
                 d['publisher_name'].replace('.xlsx', ' (2).xlsx')]
        src = next((os.path.join(src_dir, c) for c in cands
                    if os.path.exists(os.path.join(src_dir, c))), None)
        if not src:
            print(f"  {d['dataset_id']}  NOT FOUND in {src_dir}: {d['publisher_name']}")
            continue
        with open(src, 'rb') as fh:
            head = fh.read(2)
        if head != b'PK':
            raise SystemExit(f'{src}\n  expected a spreadsheet, got {head!r}. '
                             'Nothing written.')
        if os.path.basename(src) != d['publisher_name']:
            print(f"    note: taken from {os.path.basename(src)}; the ' (n)' is the "
                  f"browser's, the publisher's name is {d['publisher_name']}")
        shutil.copy2(src, dest)
        counts[d['dataset_id']] = data_rows(dest)
        print(f"  {d['dataset_id']}  {d['local']:52} "
              f"{os.path.getsize(dest):>11,} bytes  {counts[d['dataset_id']]:>7,} rows")
    return counts


def compare_api(dataset_id):
    """Rule 12: a link is not checked until something has been downloaded from it.

    Pulls the whole dataset from the API and compares it, row for row, against our
    workbook. The two routes have different column CASE (`sy` against `SY`) and the API
    renders every value as text, so the comparison is on the stringified cells.
    """
    import openpyxl
    d = next(x for x in DATASETS if x['dataset_id'] == dataset_id)
    url = api_endpoint(d) + '?$limit=1000000'
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=300) as res:
        body = res.read().decode('utf-8', 'replace')
    rd = csv.reader(body.splitlines())
    api_head = [c.upper() for c in next(rd)]
    api = sorted(tuple(c.strip() for c in r) for r in rd)

    wb = openpyxl.load_workbook(os.path.join(DESE, d['local']), read_only=True)
    it = wb['Data'].iter_rows(values_only=True)
    ours_head = [str(c) for c in next(it)]
    ours = sorted(tuple('' if c is None else str(c).strip() for c in r) for r in it)
    wb.close()
    # The workbook types the money columns as numbers; the API sends them as text.
    norm = lambda rs: sorted(tuple(c[:-2] if c.endswith('.0') and c[:-2].lstrip('-').isdigit()
                                   else c for c in r) for r in rs)
    same = api_head == ours_head and norm(api) == norm(ours)
    print(f"  {dataset_id}  api {len(api):,} rows  ours {len(ours):,} rows  "
          f"{'IDENTICAL' if same else 'DIFFERENT'}")
    return same


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--adopt', metavar='DIR', nargs='?',
                    const=os.path.expanduser('~/Downloads'),
                    help='ingest the portal downloads from DIR (default ~/Downloads)')
    ap.add_argument('--api', action='store_true',
                    help='re-download each dataset from the API and compare with our copy')
    ap.add_argument('--check', action='store_true',
                    help='fail if the registry is stale or a stored sha256 no longer holds')
    a = ap.parse_args()

    counts = None
    if a.adopt:
        print(f'Adopting DESE portal downloads from {a.adopt}\n')
        counts = adopt(a.adopt)
        print()

    rows = build_registry(counts)
    text = render(rows)

    if a.check:
        have = open(REGISTRY, encoding='utf-8').read() if os.path.exists(REGISTRY) else ''
        missing = [r['local'] for r in rows if not r['sha256']]
        if missing:
            print('catalogued but not on disk:')
            for m in missing:
                print('  ' + m)
            print('run scripts/sync_archive.py --pull')
            return 1
        if have != text:
            print(f'{os.path.relpath(REGISTRY, ROOT)} is stale — a file changed, or the '
                  'registry did.\nRe-run: python3 scripts/fetch_dese_finance.py')
            return 1
        print(f'ok: {len(rows)} DESE datasets catalogued, every sha256 still holds')
        return 0

    with open(REGISTRY, 'w', encoding='utf-8', newline='') as fh:
        fh.write(text)
    n = catalogue(rows)

    if a.api:
        print('Comparing each dataset against its API endpoint\n')
        if not all(compare_api(d['dataset_id']) for d in DATASETS):
            print('\nA dataset differs from what the API now serves. That is a FINDING, '
                  'not a fault:\nDESE has restated something. Do not overwrite our copy; '
                  'add the new one beside it.')
            return 1
        print()

    print(f'\n{os.path.relpath(REGISTRY, ROOT)} — the registry, refreshed')
    for r in rows:
        print(f"  {r['dataset_id']}  {r['title']:48} "
              f"{int(r['rows']):>8,} rows" if r['rows'] else
              f"  {r['dataset_id']}  {r['title']:48}  (not on disk)")
    print(f"catalogued {n} sources in {os.path.relpath(INDEX, ROOT)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
