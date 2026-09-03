#!/usr/bin/env python3
"""Mirror the Town of Lunenburg's agenda and minutes archive locally.

The town runs CivicEngage, whose AgendaCenter only renders one year of one board at a
time; the year tabs are an AJAX POST to /AgendaCenter/UpdateCategoryList. Its search
endpoint exists but silently under-returns older years (20 hits for 2025 where the board's
own tab has 80), so this walks board x year directly instead.

    python3 scripts/fetch_agendas.py --from 2025 [--to 2026] [--inventory]

Resumable: a file already on disk with a non-zero size is skipped. --inventory lists what
would be fetched without downloading anything.
"""
import argparse, csv, datetime as dt, pathlib, re, sys, time, urllib.parse, urllib.request

BASE = 'https://www.lunenburgma.gov'
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'sources' / 'minutes'
# Who this is, in a form somebody can look up.
#
# A crawler that will not say what it is gives an administrator seeing a burst of requests
# nothing to do but block it. Naming the site means the request is attributable, the
# +URL leads to a page explaining what the project is, and anybody who wants it to stop
# has an obvious way to ask.
#
# It is also the honest form. This is not a browser and should not claim to be one; the
# "Mozilla/5.0 (compatible; ...)" prefix is the convention every well-behaved crawler
# uses, and the rest of it is true.
UA = {'User-Agent': ('Mozilla/5.0 (compatible; LunenburgBudgetProject/1.0; +https://lunenburgbudgetproject.org)')}


# Magic bytes, because the extension is our guess and the Content-Type header is the
# server's claim. Neither is the file. OOXML (.docx/.xlsx) and legacy Office (.doc/.xls)
# share a container with other formats, so the container is resolved further before it is
# named -- a .docx and a .xlsx are both a zip, and calling one the other produces a file
# nothing can open and no error saying why.
def sniff(blob: bytes) -> str | None:
    """The extension this content actually is, or None if it is not a document at all."""
    if blob.startswith(b'%PDF'):
        return '.pdf'
    if blob.startswith(b'PK\x03\x04'):
        head = blob[:4000]
        if b'word/' in head:
            return '.docx'
        if b'xl/' in head:
            return '.xlsx'
        if b'ppt/' in head:
            return '.pptx'
        return '.zip'
    if blob.startswith(b'\xd0\xcf\x11\xe0'):     # OLE2: pre-2007 Word and Excel
        return '.doc'
    return None                                    # an HTML error page, or nothing useful


def get(url: str, data: dict | None = None, tries: int = 3) -> bytes:
    body = urllib.parse.urlencode(data).encode() if data else None
    headers = dict(UA)
    if data:
        headers['X-Requested-With'] = 'XMLHttpRequest'
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception as e:
            if i == tries - 1:
                print(f'  ! {url} {data or ""}: {e}', file=sys.stderr)
                return b''
            time.sleep(2 * (i + 1))
    return b''


def slug(s: str) -> str:
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s.lower())).strip('-')


def categories() -> dict[str, str]:
    """Board id -> name, read off the aria-labels on each board's year tabs."""
    h = get(f'{BASE}/AgendaCenter').decode('utf-8', 'replace')
    cats: dict[str, str] = {}
    for m in re.finditer(
            r'aria-label="([^"]+?) (?:19|20)\d{2}" href="javascript:changeYear\(\d+,\s*(\d+),', h):
        cats.setdefault(m.group(2), m.group(1).strip())
    return cats


def listing(cat_id: str, year: int) -> list[tuple[str, str, str]]:
    """(kind, date, file id) for one board-year."""
    h = get(f'{BASE}/AgendaCenter/UpdateCategoryList',
            {'year': year, 'catID': cat_id}).decode('utf-8', 'replace')
    out = set()
    for kind, date, fid in re.findall(
            r'ViewFile/(Agenda|Minutes)/_(\d{8})-(\d+)', h):
        if date[4:] == str(year):
            out.add((kind.lower(), date, fid))
    return sorted(out)


def backfill() -> int:
    """Fetch the rows an earlier run recorded as absent, and correct the index.

    Every one of the 39 rows blanked by the old `%PDF` test was a live document the whole
    time -- 35 .docx, 3 .doc, 1 .xlsx. This re-fetches those rows only, so the whole
    board x year walk is not repeated to recover them, and rewrites the index with the
    paths and extensions that actually arrived.
    """
    idx = OUT / 'index.csv'
    rows = list(csv.DictReader(idx.open()))
    todo = [r for r in rows if not r['path'].strip()]
    print(f'{len(todo)} of {len(rows)} index rows have no local file')
    got, still = 0, []
    for r in todo:
        blob = get(r['url'])
        ext = sniff(blob)
        if ext is None:
            still.append(r)
            print(f'  gone     {r["board"][:32]:<32} {r["date"]} {r["kind"]}')
            continue
        rel = f'{slug(r["board"])}/{r["date"]}-{r["kind"]}-{r["file_id"]}{ext}'
        p = OUT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(blob)
        r['path'] = rel
        got += 1
        print(f'  {ext:<8} {r["board"][:32]:<32} {r["date"]} {r["kind"]}  {len(blob):,}b')
        time.sleep(0.15)
    with idx.open('w', newline='') as f:
        w = csv.DictWriter(f, ['board', 'board_id', 'date', 'kind', 'file_id', 'path', 'url'])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r['board'], r['date'], r['kind'])))
    print(f'\nrecovered {got}; {len(still)} genuinely absent')
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='start', type=int, default=2025)
    ap.add_argument('--to', dest='end', type=int, default=dt.date.today().year)
    ap.add_argument('--inventory', action='store_true')
    ap.add_argument('--backfill', action='store_true',
                    help='fetch only the index rows that have no local file, and stop')
    a = ap.parse_args()

    if a.backfill:
        return backfill()

    cats = categories()
    print(f'{len(cats)} boards, {a.start}-{a.end}')
    rows, seen = [], set()
    for cid, name in sorted(cats.items(), key=lambda x: int(x[0])):
        for year in range(a.start, a.end + 1):
            for kind, date, fid in listing(cid, year):
                if (kind, fid) in seen:      # boards share files (joint meetings)
                    continue
                seen.add((kind, fid))
                iso = f'{date[4:]}-{date[:2]}-{date[2:4]}'
                rows.append({'board': name, 'board_id': cid, 'date': iso, 'kind': kind,
                             'file_id': fid,
                             'path': f'{slug(name)}/{iso}-{kind}-{fid}.pdf',
                             'url': f'{BASE}/AgendaCenter/ViewFile/'
                                    f'{kind.capitalize()}/_{date}-{fid}'})
            time.sleep(0.2)
        print(f'  {name[:44]:<44} {sum(1 for r in rows if r["board_id"] == cid):>4}')

    print(f'\n{len(rows)} documents')
    if a.inventory:
        return

    got = 0
    for r in rows:
        p = OUT / r['path']
        if p.exists() and p.stat().st_size > 0:
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        blob = get(r['url'])
        # What the town actually served. CivicEngage returns an HTML error page rather
        # than a 404 for a missing file, and this used to test `blob.startswith(b'%PDF')`
        # and blank the path for anything else -- which was one inference too many. A
        # response that is not a PDF means the file is missing OR that the town published
        # it as a Word document, and 39 documents were silently recorded as absent for
        # being .docx. Every one of them was live and fetchable the whole time.
        #
        # A missing file is now the ONLY thing that blanks a path, and it is identified
        # positively, by the error page's own magic, rather than by not being a PDF.
        kind_of = sniff(blob)
        if kind_of is None:
            r['path'] = ''
            continue
        if kind_of != '.pdf':
            # The row was written assuming .pdf. Correct it to what arrived.
            r['path'] = r['path'][:-4] + kind_of
            p = OUT / r['path']
            p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(blob)
        got += 1
        if got % 25 == 0:
            print(f'  {got} downloaded')
        time.sleep(0.15)

    idx = OUT / 'index.csv'
    with idx.open('w', newline='') as f:
        w = csv.DictWriter(f, ['board', 'board_id', 'date', 'kind', 'file_id', 'path', 'url'])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r['board'], r['date'], r['kind'])))
    print(f'downloaded {got}; index -> {idx}')


if __name__ == '__main__':
    main()
