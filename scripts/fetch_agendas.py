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
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) lunenburgbudgets/1.0'}


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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='start', type=int, default=2025)
    ap.add_argument('--to', dest='end', type=int, default=dt.date.today().year)
    ap.add_argument('--inventory', action='store_true')
    a = ap.parse_args()

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
        # CivicEngage serves an HTML error page rather than a 404 for missing files.
        if not blob.startswith(b'%PDF'):
            r['path'] = ''
            continue
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
