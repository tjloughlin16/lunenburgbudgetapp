#!/usr/bin/env python3
"""DESE's state and federal entitlement allocations: every district, every fund code, every
fiscal year DESE serves -- fetched, reconciled, and landed in the archive.

    python3 scripts/fetch_dese_entitlements.py --if-changed   # what the weekly run uses
    python3 scripts/fetch_dese_entitlements.py --dry-run      # fetch and reconcile, land nothing
    python3 scripts/fetch_dese_entitlements.py --check        # every held page is catalogued

THE PAGES. Two views of one ASP.NET form, both GET-addressable:

  view=code&fy=<YYYY>&code=<4-digit fund code>   District Name | Amount, every district
  view=district&fy=<YYYY>&code=<district code>   Fund Code | Grant Name | Amount, one district,
                                                 with a printed District Total

The years and fund codes are READ OFF the form's own selects (`ddlFiscalYear`,
`ddlFundcode`) rather than typed here. The code MUST be four characters: `code=240` silently
returns 0113, which is why every page is checked to have answered for the year and code it
was asked about (extract_dese_entitlements.parse_code_page).

THE CHECK, AND WHY IT IS THE CROSS-VIEW ONE. The by-code view prints no total, so it cannot
be footed alone. For each district in `extract_dese_entitlements.RECONCILE` the by-district
page must foot to its own District Total and its line items must equal that district's rows
across all the year's fund-code pages. A YEAR THAT DOES NOT RECONCILE IS NOT LANDED.

DESE REVISES THESE IN PLACE (the pages carry `Last Updated`), so each page is kept as a
dated snapshot under `sources/state-dese/entitlements/<YYYY-MM-DD>/` -- a folder
archive_storage freezes -- and a page is landed ONLY WHEN ITS BYTES DIFFER from the newest
snapshot of it already held. The pages are byte-stable between requests (checked on
22 October 2026: two fetches a second apart, identical sha256), so the strict comparison
is the right one. Every run is logged in `entitlements/checked.csv` whether or not anything
changed, so "nothing changed since July" is distinguishable from "nobody looked".

Everything goes in through `ingest.stage()` + `ingest.secure()`: pushed to the bucket and
read back before it is filed in `sources/`, then catalogued in `sources/state-dese/index.csv`
with the publisher's exact URL.

About 270 requests at one a second: roughly five minutes.
"""
import argparse
import csv
import datetime
import hashlib
import io
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract_dese_entitlements as X  # noqa: E402
import snapshot_log  # noqa: E402

ROOT = os.path.dirname(HERE)
KEYDIR = 'state-dese/entitlements'
DOCS = X.DOCS
INDEX = os.path.join(ROOT, 'sources', 'state-dese', 'index.csv')
INDEX_FIELDS = ['label', 'upstream', 'local', 'text', 'bytes', 'sha256', 'read']
UA = {'User-Agent': 'lunenburgbudgetproject.org (public records archive of Lunenburg, MA '
                    'budget documents; one request a second)'}
PAUSE = 1.0


class NotServed(IOError):
    """DESE answered with its Server Error Page after every retry."""


CACHE = None   # --raw DIR: keep every response there, and answer from it when present


def get(url):
    if CACHE:
        p = os.path.join(CACHE, hashlib.sha256(url.encode()).hexdigest()[:24])
        if os.path.exists(p):
            return open(p, 'rb').read()
        blob = _get(url)
        os.makedirs(CACHE, exist_ok=True)
        open(p, 'wb').write(blob)
        return blob
    return _get(url)


def _get(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r:
                blob = r.read()
            time.sleep(PAUSE)
            # DESE ANSWERS A FAILED QUERY WITH HTTP 200 AND A 'Server Error Page' -- seen once
            # in 266 requests on 22 October 2026, for 0240 FY2018. Retried, never kept.
            if b'Server Error Page' in blob:
                raise NotServed('DESE returned its Server Error Page')
            return blob
        except Exception:                      # noqa: BLE001 -- retried, then raised
            if attempt == 2:
                raise
            time.sleep(10 * (attempt + 1))


def fetch_all(log=print):
    """{fy: {'code': {code: bytes}, 'district': {dcode: bytes}}}. The open-grants list
    (grants.aspx) is NOT fetched here: fetch_dese_grants.py owns it, under state-dese/grants/."""
    first = get(X.CODE_URL.format(fy=datetime.date.today().year, code='0113')).decode('utf-8', 'replace')
    years = sorted(v for v, _l in X.options(first, 'ddlFiscalYear'))
    codes = [v for v, _l in X.options(first, 'ddlFundcode')]
    if not years or not codes:
        raise SystemExit('the form offered no years or no fund codes -- the page has changed shape')
    log('DESE offers FY%s-FY%s (%d years) and %d fund codes: %s'
        % (years[0], years[-1], len(years), len(codes), ' '.join(codes)))
    out = {}
    names = None
    for fy in years:
        out[fy] = {'code': {}, 'district': {}}
        for code in codes:
            try:
                out[fy]['code'][code] = get(X.CODE_URL.format(fy=fy, code=code))
            except NotServed as e:
                # Named downstream by reconcile(), which excludes it from the check and says so.
                log('  FY%s %s NOT SERVED: %s' % (fy, code, e))
        if names is None:
            # The district codes, off DESE's own select. Any by-district page carries the
            # whole list; 0001 is only the address of one such page, and nothing is read
            # from its grid.
            boot = get(X.DISTRICT_URL.format(fy=fy, code='0001')).decode('utf-8', 'replace')
            names = X.district_codes(boot)
        for dname in X.RECONCILE:
            got = names.get(dname, set())
            if len(got) != 1:
                raise SystemExit('%s resolves to %d codes in DESE\'s district select: %s'
                                 % (dname, len(got), sorted(got)))
            dcode = next(iter(got))
            out[fy]['district'][dcode] = get(X.DISTRICT_URL.format(fy=fy, code=dcode))
        log('  FY%s fetched' % fy)
    return out


def newest(name):
    """sha256 of the newest held snapshot of `name`, or None."""
    p = X.held().get(name)
    return hashlib.sha256(open(p, 'rb').read()).hexdigest() if p else None


def catalogue(rows):
    """Append to the shared index -- re-read immediately before writing, keep its newlines."""
    raw = open(INDEX, 'rb').read()
    nl = '\r\n' if b'\r\n' in raw else '\n'
    have = list(csv.DictReader(io.StringIO(raw.decode('utf-8'))))
    known = {r['local'] for r in have}
    added = [r for r in rows if r['local'] not in known]
    if not added:
        return 0
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=INDEX_FIELDS, lineterminator=nl)
    w.writeheader()
    w.writerows(have + added)
    tmp = INDEX + '.tmp'
    open(tmp, 'wb').write(out.getvalue().encode('utf-8'))
    os.replace(tmp, INDEX)
    return len(added)


def label(name, blob, today):
    m = X.NAME.match(name)
    page = blob.decode('utf-8', 'replace')
    kind, code, fy = m.groups()
    if kind == 'code':
        h = X.heading(page)
        return ('DESE entitlement allocations by fund code, every district: %s, FY%s (fetched %s)'
                % (h.rsplit(' ', 1)[0], fy, today))
    dname = dict(X.options(page, 'ddlFundcode')).get(code, code)
    return ('DESE entitlement allocations by district: %s (%s), every grant, FY%s (fetched %s)'
            % (dname, code, fy, today))


def check():
    have = {r['local']: r for r in csv.DictReader(open(INDEX, encoding='utf-8'))}
    bad = []
    for dp, _d, fs in os.walk(DOCS):
        for f in fs:
            if not f.endswith('.html'):
                continue
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, ROOT)
            row = have.get(rel)
            if not row:
                bad.append('%s is on disk and in no catalogue' % rel)
            elif hashlib.sha256(open(full, 'rb').read()).hexdigest() != row['sha256']:
                bad.append('%s has changed since it was catalogued' % rel)
    for b in bad:
        print(b)
    print('%d problem(s)' % len(bad))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--if-changed', action='store_true',
                    help='land a page only when its bytes differ from the newest snapshot '
                         '(always true: an identical snapshot would be frozen for ten years '
                         'saying nothing; the flag is accepted so the schedule reads plainly)')
    ap.add_argument('--dry-run', action='store_true', help='fetch and reconcile; land nothing')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--raw', metavar='DIR',
                    help='debugging: keep raw responses in DIR (outside sources/) and reuse them')
    a = ap.parse_args()
    if a.check:
        return check()
    global CACHE
    CACHE = a.raw
    import ingest
    today = datetime.date.today().isoformat()
    fetched = fetch_all()

    land, refused, url = {}, [], {}
    for fy, v in sorted(fetched.items()):
        try:
            notes = X.reconcile(fy, {c: b.decode('utf-8', 'replace') for c, b in v['code'].items()},
                                {c: b.decode('utf-8', 'replace') for c, b in v['district'].items()})
        except X.Refused as e:
            refused.append((fy, str(e)))
            continue
        for n in notes:
            print('  note: ' + n)
        for c, b in v['code'].items():
            land['code-%s-fy%s.html' % (c, fy)] = b
            url['code-%s-fy%s.html' % (c, fy)] = X.CODE_URL.format(fy=fy, code=c)
        for c, b in v['district'].items():
            land['district-%s-fy%s.html' % (c, fy)] = b
            url['district-%s-fy%s.html' % (c, fy)] = X.DISTRICT_URL.format(fy=fy, code=c)
    print('%d of %d years reconciled' % (len(fetched) - len(refused), len(fetched)))
    for fy, why in refused:
        print('  REFUSED FY%s (nothing from it landed): %s' % (fy, why))

    changed = {n: b for n, b in land.items() if newest(n) != hashlib.sha256(b).hexdigest()}
    print('%d pages reconciled; %d differ from the newest snapshot held' % (len(land), len(changed)))
    if a.dry_run:
        return 1 if refused else 0
    if not changed:
        snapshot_log.record(DOCS, today, False, snapshot=snapshot_log.latest(DOCS) or '',
                            files=len(land), note='every page identical to its newest snapshot')
        return 1 if refused else 0

    staged, rows = 0, []
    for n, b in sorted(changed.items()):
        key = '%s/%s/%s' % (KEYDIR, today, n)
        ok, why = ingest.stage(key, b, url[n])
        if not ok:
            print('  !! %s not staged: %s' % (key, why))
            continue
        staged += 1
        rows.append(dict(label=label(n, b, today), upstream=url[n],
                         local=os.path.join('sources', key), text='', bytes=len(b),
                         sha256=hashlib.sha256(b).hexdigest(), read='html'))
    done, failed = ingest.secure(quiet=True)
    print('staged %d; secured %d; failed %d' % (staged, done, failed))
    held_now = [r for r in rows if os.path.exists(os.path.join(ROOT, r['local']))]
    n = catalogue(held_now)
    print('%d newly catalogued in %s' % (n, os.path.relpath(INDEX, ROOT)))
    snapshot_log.record(DOCS, today, True, snapshot=today, files=len(held_now),
                        note='%d of %d pages changed; %d refused years' % (len(changed), len(land), len(refused)))
    return 1 if (refused or failed) else 0


if __name__ == '__main__':
    sys.exit(main())
