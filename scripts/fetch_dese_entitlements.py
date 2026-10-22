"""DESE's federal entitlement allocations for one district, every fiscal year DESE serves.

    python3 scripts/fetch_dese_entitlements.py              # Lunenburg (0162)
    python3 scripts/fetch_dese_entitlements.py --code 0162

Writes build/dese-entitlements/<code>/fy<YYYY>.html and allocations.csv. NOT YET WIRED TO
ingest.land: the pages are not in the archive and nothing here is published. DESE overwrites
these pages in place, so the wired version must snapshot only when a page changes.

An ALLOCATION is what the district may draw on a federal grant year. It is not a receipt and
not a spend. Every page is checked against the `District Total` it prints, and a year that
does not foot is refused.
"""
import argparse
import csv
import hashlib
import html
import re
import sys
import time
import urllib.request
from pathlib import Path

URL = 'https://www.doe.mass.edu/grants/entitlement-allocation.aspx?view=district&fy={fy}&code={code}'
OUT = Path(__file__).resolve().parent.parent / 'build' / 'dese-entitlements'


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (lunenburgbudgetproject.org)'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def selected(page, name):
    m = re.search(name + r'.*?<option selected="selected" value="(\d+)"', page, re.S)
    return m.group(1) if m else None


def rows(page):
    table = re.findall(r'<table.*?</table>', page, re.S)[-1]
    out = []
    for tr in re.findall(r'<tr.*?</tr>', table, re.S):
        c = [html.unescape(re.sub(r'<[^>]+>', '', x)).strip()
             for x in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S)]
        if len(c) == 3 and c[2].startswith('$'):
            out.append((c[0], c[1], int(c[2].replace('$', '').replace(',', ''))))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--code', default='0162')
    a = ap.parse_args()
    out = OUT / a.code
    out.mkdir(parents=True, exist_ok=True)
    first = get(URL.format(fy=2027, code=a.code)).decode('utf-8', 'replace')
    years = re.findall(r'<option[^>]*value="(\d{4})"',
                       re.search(r'ddlFiscalYear.*?</select>', first, re.S).group(0))
    written, refused = [], []
    for fy in sorted(years):
        raw = get(URL.format(fy=fy, code=a.code))
        page = raw.decode('utf-8', 'replace')
        if selected(page, 'ddlFiscalYear') != fy or selected(page, 'ddlFundcode') != a.code:
            refused.append((fy, 'page answered for a different year or district'))
            continue
        r = rows(page)
        total = [x for x in r if x[1] == 'District Total']
        body = [x for x in r if x[1] != 'District Total']
        if len(total) != 1 or sum(x[2] for x in body) != total[0][2]:
            refused.append((fy, 'grants do not foot to the printed District Total'))
            continue
        (out / f'fy{fy}.html').write_bytes(raw)
        sha = hashlib.sha256(raw).hexdigest()
        for code, name, amt in body:
            written.append({'fy': fy, 'district_code': a.code, 'fund_code': code, 'grant': name,
                            'allocation': amt, 'source_url': URL.format(fy=fy, code=a.code),
                            'sha256': sha, 'fetched': time.strftime('%Y-%m-%d')})
        time.sleep(1)
    with open(out / 'allocations.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(written[0]))
        w.writeheader()
        w.writerows(written)
    print(f'{len(years) - len(refused)} of {len(years)} years footed, {len(written)} allocations -> {out}/allocations.csv')
    for fy, why in refused:
        print(f'  REFUSED FY{fy}: {why}')
    return 1 if refused else 0


if __name__ == '__main__':
    sys.exit(main())
