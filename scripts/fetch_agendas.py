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
import argparse, csv, datetime as dt, html, os, pathlib, re, sys, time, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ingest          # noqa: E402 -- the one door every document arrives through

BASE = 'https://www.lunenburgma.gov'
# `title` is the town's own name for the meeting, as the listing prints it; `board` is the
# CATEGORY it was filed under. They differ, and only `title` says which body met.
COLS = ['board', 'board_id', 'date', 'kind', 'file_id', 'path', 'url', 'title']
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'sources' / 'meetings'
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


# A LISTING ROW IS ONE MEETING, AND IT HAS A TITLE. The category a document is filed under
# is not the body that met: on 13 October 2026 the School Committee category held
# "School Advisory Council LMS" and "School Advisory Council LHS" beside "School Committee
# Revised", and this parser kept only the category -- so the site announced two School
# Committee meetings that were principals' advisory councils. TJ: "On the agenda center
# it's listed as 'School Advisory Council LHS'. Do you not see it that way?" We did not;
# we threw the title away. The row's title is the link text of its agenda, and it covers
# the minutes posted in the same row.
ROW = re.compile(r'<tr id="row\d+\w*" class="catAgendaRow">(.*?)</tr>', re.S)
TITLE = re.compile(r'<p>\s*<a [^>]*href="/AgendaCenter/ViewFile/\w+/_\d{8}-\d+"[^>]*>(.*?)</a>', re.S)
FILE = re.compile(r'ViewFile/(Agenda|Minutes)/_(\d{8})-(\d+)')


def parse_listing(h: str, year: int) -> list[tuple[str, str, str, str]]:
    """(kind, MMDDYYYY, file id, title) for every document one board-year page lists.

    The one parser for the AgendaCenter's listing HTML -- watch_meetings.py calls it too,
    so the two cannot disagree about what a page says. A document found outside any row
    is still returned, with an empty title, so a markup change costs the title and never
    the document."""
    out: dict[tuple[str, str], tuple[str, str, str, str]] = {}
    for row in ROW.findall(h):
        t = TITLE.search(row)
        title = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', t.group(1)))).strip() if t else ''
        for kind, date, fid in FILE.findall(row):
            out.setdefault((kind.lower(), fid), (kind.lower(), date, fid, title))
    for kind, date, fid in FILE.findall(h):
        out.setdefault((kind.lower(), fid), (kind.lower(), date, fid, ''))
    return sorted(v for v in out.values() if v[1][4:] == str(year))


def listing(cat_id: str, year: int) -> list[tuple[str, str, str, str]]:
    """(kind, date, file id, title) for one board-year."""
    h = get(f'{BASE}/AgendaCenter/UpdateCategoryList',
            {'year': year, 'catID': cat_id}).decode('utf-8', 'replace')
    return parse_listing(h, year)


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
    staged: list[tuple[dict, str]] = []
    for r in todo:
        blob = get(r['url'])
        ext = sniff(blob)
        if ext is None:
            still.append(r)
            print(f'  gone     {r["board"][:32]:<32} {r["date"]} {r["kind"]}')
            continue
        rel = f'{slug(r["board"])}/{r["date"]}-{r["kind"]}-{r["file_id"]}{ext}'
        # THROUGH `ingest`, for the reason the main loop does -- and this is the path that
        # matters most, because `refresh.py` calls `--backfill` every morning. The index
        # row's `path` is set only once the document is in the bucket AND filed, so a
        # document still in flight keeps an empty path and stays a backfill candidate
        # tomorrow. A catalogue that names a file nobody holds is the state this project
        # spent 25 September chasing.
        ok, why = ingest.stage('meetings/' + rel, blob, upstream=r['url'])
        if not ok:
            still.append(r)
            print(f'  refused  {r["board"][:32]:<32} {r["date"]} {r["kind"]}  {why[:48]}')
            continue
        staged.append((r, rel))
        got += 1
        print(f'  {ext:<8} {r["board"][:32]:<32} {r["date"]} {r["kind"]}  {len(blob):,}b')
        time.sleep(0.15)

    if staged:
        ingest.secure()
        for r, rel in staged:
            if (OUT / rel).exists():
                r['path'] = rel
            else:
                print(f'  in flight, path left blank: {rel}')
    with idx.open('w', newline='') as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r['board'], r['date'], r['kind'])))
    print(f'\nrecovered {got}; {len(still)} genuinely absent')
    return 0


def titles(start: int, end: int) -> int:
    """Fill `title` on the rows the index already holds. Downloads no document.

    Every row catalogued before 13 October 2026 was written without its title. This
    walks the listings again and sets the title only; paths, files and the bucket are
    untouched. A row whose listing did not answer keeps an empty title and says so."""
    idx = OUT / 'index.csv'
    rows = list(csv.DictReader(idx.open()))
    by = {(r['board_id'], r['file_id'], r['kind']): r for r in rows}
    cats = categories()
    found, failed = 0, []
    for cid, name in sorted(cats.items(), key=lambda x: int(x[0])):
        for year in range(start, end + 1):
            body = get(f'{BASE}/AgendaCenter/UpdateCategoryList', {'year': year, 'catID': cid})
            if not body:
                failed.append(f'{name} {year}')
                continue
            for kind, date, fid, title in parse_listing(body.decode('utf-8', 'replace'), year):
                r = by.get((cid, fid, kind))
                if r is not None and title:
                    r['title'] = title
                    found += 1
            time.sleep(0.2)
        print(f'  {name[:44]:<44} {sum(1 for r in rows if r["board_id"] == cid and r.get("title")):>5} titled')
    with idx.open('w', newline='') as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r['board'], r['date'], r['kind'])))
    untitled = sum(1 for r in rows if not r.get('title'))
    print(f'\n{found} titles set; {untitled} of {len(rows)} rows still untitled; '
          f'{len(failed)} board-years did not answer' + (f': {", ".join(failed[:8])}' if failed else ''))
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='start', type=int, default=2025)
    ap.add_argument('--to', dest='end', type=int, default=dt.date.today().year)
    ap.add_argument('--inventory', action='store_true')
    ap.add_argument('--backfill', action='store_true',
                    help='fetch only the index rows that have no local file, and stop')
    ap.add_argument('--titles', action='store_true',
                    help="fill the town's meeting title on rows already held; downloads nothing")
    a = ap.parse_args()

    if a.titles:
        return titles(a.start, a.end)

    if a.backfill:
        return backfill()

    cats = categories()
    print(f'{len(cats)} boards, {a.start}-{a.end}')
    rows, seen = [], set()
    for cid, name in sorted(cats.items(), key=lambda x: int(x[0])):
        for year in range(a.start, a.end + 1):
            for kind, date, fid, title in listing(cid, year):
                if (kind, fid) in seen:      # boards share files (joint meetings)
                    continue
                seen.add((kind, fid))
                iso = f'{date[4:]}-{date[:2]}-{date[2:4]}'
                rows.append({'board': name, 'board_id': cid, 'date': iso, 'kind': kind,
                             'file_id': fid, 'title': title,
                             'path': f'{slug(name)}/{iso}-{kind}-{fid}.pdf',
                             'url': f'{BASE}/AgendaCenter/ViewFile/'
                                    f'{kind.capitalize()}/_{date}-{fid}'})
            time.sleep(0.2)
        print(f'  {name[:44]:<44} {sum(1 for r in rows if r["board_id"] == cid):>4}')

    print(f'\n{len(rows)} documents')
    if a.inventory:
        return

    got = 0
    staged: list[tuple[dict, str]] = []
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
        # THROUGH `ingest`, NOT STRAIGHT TO DISK. This used to be `p.write_bytes(blob)`:
        # a non-atomic write to the document's real archival path, an hour before anything
        # backed it up. A crash mid-write left a truncated file at the real name, and a run
        # that died before the refresh's last step left the morning's documents in one
        # place -- six agendas were sitting exactly that way on 25 September 2026.
        #
        # `stage` validates, writes atomically into build/ingest/ and registers the document
        # as IN FLIGHT; `secure` below pushes it, reads it back and only then files it into
        # sources/ and catalogues it. So a document is in the archive if and only if it is
        # in the bucket, and nothing destructive can run while one is in flight.
        key = 'meetings/' + r['path']
        ok, why = ingest.stage(key, blob, upstream=r['url'])
        if not ok:
            print(f'  ?? refused {r["path"]}: {why}')
            r['path'] = ''
            continue
        staged.append((r, key))
        got += 1
        if got % 25 == 0:
            print(f'  {got} downloaded')
        time.sleep(0.15)

    # SECURE THE BATCH, THEN LET THE INDEX NAME ONLY WHAT IS ACTUALLY HELD. A row whose
    # document is still in flight keeps an EMPTY path, which is exactly what `--backfill`
    # looks for -- so the next run picks it up and `stage` is idempotent about it. That is
    # what stops the catalogue from naming a document nobody holds, which is the state this
    # project spent hours chasing on 25 September.
    if staged:
        secured, failed = ingest.secure()
        for r, key in staged:
            if not (OUT / r['path']).exists():
                r['path'] = ''

    # MERGE INTO THE INDEX. NEVER REPLACE IT. A walk of one year used to rewrite the whole
    # file with that year's rows -- the daily refresh's first run (11 September 2026) took
    # it from 12,065 rows to 584, the search index rebuilt from the stub, and the push
    # then deleted every other year's minutes from the live database. The index is the
    # catalogue of everything held; a run that saw part of it may only add to it.
    idx = OUT / 'index.csv'
    cols = COLS
    held = {}
    if idx.exists():
        for r in csv.DictReader(idx.open()):
            held[(r['board_id'], r['file_id'], r['kind'])] = r
    before = len(held)
    for r in rows:
        old = held.get((r['board_id'], r['file_id'], r['kind']), {})
        new = {c: r.get(c, '') for c in cols}
        new['title'] = new['title'] or old.get('title', '')   # a row seen without its title keeps the one it had
        held[(r['board_id'], r['file_id'], r['kind'])] = new
    merged = sorted(held.values(), key=lambda r: (r['board'], r['date'], r['kind']))
    if before and len(merged) < before:
        raise SystemExit(f'refusing to write index.csv: would shrink from {before} to {len(merged)} rows')
    with idx.open('w', newline='') as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(merged)
    print(f'downloaded {got}; index -> {idx} ({before} held, {len(merged)} after merge)')


if __name__ == '__main__':
    main()
