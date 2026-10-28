#!/usr/bin/env python3
"""DESE's datasets on the state's open data portal: land a new version when, and only when,
the portal says the rows changed.

    python3 scripts/fetch_dese_socrata.py              # what the refresh runs: archive new versions
    python3 scripts/fetch_dese_socrata.py --dry-run    # ask the portal; download and land nothing
    python3 scripts/fetch_dese_socrata.py --promote    # ...and make each newest version the working copy
    python3 scripts/fetch_dese_socrata.py --promote ab34-d3ma   # promote that dataset only
    python3 scripts/fetch_dese_socrata.py --check      # every held version is catalogued; offline

WHY BYTES CANNOT DECIDE IT. The portal generates an export on every download: two exports of
the circuit breaker a second apart on 28 October 2026 were the same size, the same rows and
different sha256 (bd6d73db..., 24903fae...). A fetcher that compared bytes would land a new
"version" every run, and every one would be frozen in the bucket for ten years saying
nothing. So the portal is asked the question directly, the way check_socrata_sources.py asks
it: `rowsUpdatedAt` on /api/views/<id>.json. A dataset is downloaded only when that is LATER
than the newest copy we hold.

THE NEWEST COPY WE HOLD is the latest of two dates: the dated version folders this script
lands into (`state-dese/<YYYY-MM-DD>/<name>`, looked for in the MANIFEST as well as on disk,
so a tree that has not pulled every version does not re-download one the archive already
has), and, for a dataset never re-landed, the date the working copy's sha256 was first
committed to the registry -- check_socrata_sources.our_copy_date, the same answer that check
gives, so the two cannot disagree about which datasets moved. Both are DAYS: an update on the
same day as our download, after it, is not seen until the portal next moves. Stated, not fixed,
because nothing in the repository records the hour.

ARCHIVE, AND PROMOTE, ARE TWO STEPS ON PURPOSE. The unattended run ARCHIVES: the new export
is validated, landed through ingest under a dated folder, catalogued, and that is all. The
working copy at the fixed name -- the file some forty generators read, and so the figures on
the site -- is not touched. Changing it is `--promote`, which does what ingest.land_version
does for every other overwritten-in-place source (registers the fixed name as a working copy
and rewrites it), then rebuilds dese-source-registry.csv and, for the three finance datasets,
socrata-datasets.csv, so their --check modes and the next portal check compare against the
new copy. It is separate because a DESE restatement changes published figures -- the
circuit breaker's 7 October update withheld a count our pages still print -- and
check_socrata_sources.py and source_cadence.py both say a person decides that and re-runs what
reads it. If that decision is ever taken the other way, the cadence command gains `--promote`
and nothing else changes.

WHY A SCRIPT OF ITS OWN rather than more of fetch_dese_finance.py: that script owns three
datasets, a registry of its own with a hand-typed download date and export filename, and an
--adopt path for files saved from a browser. The eighteen datasets the portal check watches
are the socrata rows of dese-source-registry.csv, so this reads exactly those rows and its
list cannot drift from the check's.

THE EXPORT ROUTE is /api/v3/views/<id>/export.xlsx. It returns the same workbook the portal's
Export button produced for our copies -- one sheet, `Data`, inline strings, the same header
(checked against the circuit breaker, 28 October 2026). `rows.xlsx` on the older route answers
406, and `rows.csv` would change the file format our extractors read.

One small request per dataset, a second apart; a download only for a dataset that moved.
Exit 0 when every dataset was asked and every needed download landed; 1 when any could not
be, so the refresh records the look as failed and tries again the next morning.
"""
import argparse
import csv
import datetime
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import archive_storage as A  # noqa: E402
import check_socrata_sources as C  # noqa: E402

ROOT = os.path.dirname(HERE)
REGISTRY = C.REGISTRY
STATUS = C.OUT
INDEX = os.path.join(ROOT, 'sources', 'state-dese', 'index.csv')
INDEX_FIELDS = ['label', 'upstream', 'local', 'text', 'bytes', 'sha256', 'read']
UA = {'User-Agent': C.UA}
PAUSE = 1.0
# The three datasets fetch_dese_finance.py also registers, in socrata-datasets.csv. A promote
# of one of them must rebuild that registry too, or its --check fails on a sha256 that moved.
FINANCE = {'cnfs-edqq', 'er3w-dyti', 'i5up-aez6'}


def socrata_rows():
    with open(REGISTRY, newline='', encoding='utf-8') as fh:
        return [r for r in csv.DictReader(fh) if r['source_kind'] == 'socrata']


def host(row):
    return urllib.parse.urlsplit(row['api_endpoint'] or row['portal_page']).netloc


def export_url(row):
    return 'https://%s/api/v3/views/%s/export.xlsx' % (host(row), row['dataset_id'])


def _get(url, timeout):
    """One retry after a pause: a portal's bad minute should not cost a week's look."""
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception:                          # noqa: BLE001 -- retried once, then raised
            if attempt:
                raise
            time.sleep(15)


def rows_updated(row):
    """-> (epoch seconds, 'YYYY-MM-DD'). The day is computed exactly as
    check_socrata_sources.rows_updated computes it, so both scripts call the same datasets
    moved."""
    meta = json.loads(_get('https://%s/api/views/%s.json' % (host(row), row['dataset_id']), 30))
    ts = meta.get('rowsUpdatedAt') or meta.get('viewLastModified')
    if not ts:
        raise ValueError('the portal gave no rowsUpdatedAt for %s' % row['dataset_id'])
    return ts, datetime.datetime.fromtimestamp(ts).date().isoformat()


def _split(key):
    d, name = os.path.split(key)
    stem, ext = os.path.splitext(name)
    return d, stem, ext


DATED = re.compile(r'^(\d{4}-\d{2}-\d{2})$')


def versions(key):
    """[(day, dated key)] for every dated version of `key` the archive holds -- in the
    manifest or on disk -- oldest first. Same folder pattern ingest.land_version writes and
    globs, so a version landed by either is found by both."""
    d, stem, ext = _split(key)
    found = {}
    pat = re.compile(r'^%s/(\d{4}-\d{2}-\d{2})/%s(-[0-9a-f]{8})?%s$'
                     % (re.escape(d), re.escape(stem), re.escape(ext)))
    for k in A.read_manifest():
        m = pat.match(k)
        if m:
            found[k] = m.group(1)
    for p in glob.glob(os.path.join(A.SRC, d, '[0-9]' * 4 + '-*', stem + '*' + ext)):
        k = os.path.relpath(p, A.SRC).replace(os.sep, '/')
        m = pat.match(k)
        if m:
            found[k] = m.group(1)
    return sorted((day, k) for k, day in found.items())


def newest_held(row):
    """The day of the newest copy we hold, by either route, or ''."""
    days = [day for day, _k in versions(row['local'][len('sources/'):])]
    days.append(C.our_copy_date(row['sha256']))
    days = [d for d in days if d]
    return max(days) if days else ''


def header(blob_or_path):
    """The first row of the `Data` sheet, read off the XML rather than through openpyxl.

    openpyxl took over two minutes to open the 136 MB teachers workbook in read-only mode;
    the export writes inline strings, so the header is the `<t>` values of row 1, in the first
    few kilobytes of the sheet. And opening the zip at all proves the download is whole: the
    central directory is at the END of the file, so a truncated export does not open."""
    src = io.BytesIO(blob_or_path) if isinstance(blob_or_path, bytes) else blob_or_path
    with zipfile.ZipFile(src) as z:
        names = re.findall(rb'<sheet [^>]*name="([^"]+)"', z.read('xl/workbook.xml'))
        if names != [b'Data']:
            raise ValueError('sheets are %r, not one sheet named Data' % names)
        bad = z.testzip()
        if bad:
            raise ValueError('corrupt member %s' % bad)
        with z.open('xl/worksheets/sheet1.xml') as fh:
            head = fh.read(65536).decode('utf-8', 'replace')
    m = re.search(r'<row r="1"[^>]*>(.*?)</row>', head, re.S)
    if not m:
        raise ValueError('no header row in the first 64 KB of the sheet')
    return [t for t in re.findall(r'<t[^>]*>([^<]*)</t>', m.group(1))]


def validate(blob, row):
    """Refuse anything that is not a whole workbook of this dataset. Returns a note, '' if
    nothing worth saying. An R2 object cannot be corrected, so this is the last chance."""
    if not blob.startswith(b'PK'):
        raise ValueError('not a spreadsheet: first bytes %r' % blob[:16])
    new = header(blob)
    with zipfile.ZipFile(io.BytesIO(blob)) as z, z.open('xl/worksheets/sheet1.xml') as fh:
        if b'<row r="2"' not in fh.read(1 << 20):
            raise ValueError('a header and no data rows')
    working = os.path.join(ROOT, row['local'])
    if os.path.exists(working):
        old = header(working)
        if new != old:
            # A schema change is still DESE's file, and exactly the version most worth
            # keeping -- so it is archived, and said loudly, because every extractor reading
            # the old columns breaks the day it is promoted.
            return 'HEADER CHANGED: %s -> %s' % (old, new)
    return ''


def archive_version(key, blob, upstream, day=None):
    """Land `blob` as a dated version of `key` WITHOUT touching the working copy at `key`.

    The archive half of ingest.land_version, with the same folder and the same name, so a
    later land_version of the same bytes finds this one held and lands nothing twice.
    Returns (ok, reason, dated key)."""
    import ingest
    day = day or datetime.date.today().isoformat()
    sha = hashlib.sha256(blob).hexdigest()
    d, stem, ext = _split(key)
    for _day, k in versions(key):
        p = A.local_path(k)
        held = (A.hash_file(p)[0] if os.path.exists(p)
                else A.read_manifest().get(k, {}).get('sha256'))
        if held == sha:
            return True, 'already held as %s' % k, k
    dated = '%s/%s/%s%s' % (d, day, stem, ext)
    if os.path.exists(A.local_path(dated)) or dated in A.read_manifest():
        dated = '%s/%s/%s-%s%s' % (d, day, stem, sha[:8], ext)   # a second version that day
    ok, why = ingest.land(dated, blob, upstream)
    return ok, why, dated


def catalogue(entries):
    """Add or refresh rows of sources/state-dese/index.csv, keyed on `local`. SHARED with the
    other DESE fetchers: re-read immediately before writing, only our own rows touched,
    newline convention kept, replaced atomically -- and not rewritten at all when nothing in
    it would change."""
    raw = open(INDEX, 'rb').read()
    nl = '\r\n' if b'\r\n' in raw else '\n'
    have = list(csv.DictReader(io.StringIO(raw.decode('utf-8'))))
    fields = list(have[0].keys()) if have else INDEX_FIELDS
    by_local = {r['local']: r for r in have}
    changed = 0
    for e in entries:
        e = {k: str(e.get(k, '')) for k in fields}
        cur = by_local.get(e['local'])
        if cur is None:
            have.append(e)
            by_local[e['local']] = e
            changed += 1
        elif any(cur.get(k, '') != e[k] for k in fields if e[k]):
            cur.update({k: v for k, v in e.items() if v})
            changed += 1
    if not changed:
        return 0
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=fields, lineterminator=nl)
    w.writeheader()
    w.writerows(have)
    tmp = INDEX + '.tmp'
    open(tmp, 'wb').write(out.getvalue().encode('utf-8'))
    os.replace(tmp, INDEX)
    return changed


def fetch(rows, dry_run):
    """Ask the portal about every dataset; archive the ones that moved. -> failures."""
    failures, today = 0, datetime.date.today().isoformat()
    for n, r in enumerate(rows):
        if n:
            time.sleep(PAUSE)
        key = r['local'][len('sources/'):]
        try:
            ts, upd = rows_updated(r)
        except Exception as e:                     # noqa: BLE001 -- reported, retried tomorrow
            print('  unreachable  %s: %s' % (r['dataset_id'], str(e)[:120]))
            failures += 1
            continue
        ours = newest_held(r)
        if ours and upd <= ours:
            continue
        print('  moved  %s %s: rows updated %s, newest copy held %s'
              % (r['dataset_id'], r['name'][:48], upd, ours or 'unknown'))
        if dry_run:
            continue
        url = export_url(r)
        try:
            time.sleep(PAUSE)
            blob = _get(url, 600)
            note = validate(blob, r)
            # The rows must not have moved WHILE we downloaded, or the export is of no
            # stated moment. Asked again; a mismatch waits for the next run.
            time.sleep(PAUSE)
            if rows_updated(r)[0] != ts:
                print('    the rows changed during the download; nothing landed, next run retries')
                failures += 1
                continue
        except Exception as e:                     # noqa: BLE001
            print('    !! %s: %s' % (url, str(e)[:160]))
            failures += 1
            continue
        if note:
            print('    ' + note)
        ok, why, dated = archive_version(key, blob, url, today)
        if not ok:
            print('    !! %s: %s' % (dated, why))
            failures += 1
            continue
        stamp = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
        catalogue([dict(
            label='%s -- DESE export of %s, rows last updated %s per the portal (dataset %s)'
                  % (r['name'], today, stamp.strftime('%Y-%m-%d %H:%M UTC'), r['dataset_id']),
            upstream=url, local='sources/' + dated, text='', bytes=len(blob),
            sha256=hashlib.sha256(blob).hexdigest(), read='xlsx')])
        print('    landed %s  %d bytes%s' % (dated, len(blob), ('  (%s)' % why) if why else ''))
    return failures


def promote(rows, only):
    """Make the newest held version of each dataset its working copy. -> failures."""
    import ingest
    failures, moved = 0, []
    for r in rows:
        if only and r['dataset_id'] not in only:
            continue
        key = r['local'][len('sources/'):]
        vs = [(d, k) for d, k in versions(key) if os.path.exists(A.local_path(k))]
        if not vs:
            continue
        day, dated = vs[-1]
        blob = open(A.local_path(dated), 'rb').read()
        working = A.local_path(key)
        if os.path.exists(working) and A.hash_file(working)[0] == hashlib.sha256(blob).hexdigest():
            continue
        if day <= C.our_copy_date(r['sha256']):
            continue          # the working copy was taken after this version: not newer
        ok, why = ingest.land_version(key, blob, export_url(r), day)
        if not ok:
            print('  !! promote %s: %s' % (key, why))
            failures += 1
            continue
        print('  promoted %s -> working copy %s' % (dated, key))
        catalogue([dict(local=r['local'], bytes=len(blob),
                        sha256=hashlib.sha256(blob).hexdigest())])
        moved.append(r)
    if not moved:
        return failures
    # The registry is rebuilt from disk, which is how its sha256 comes to name the new copy --
    # the comparison the next portal check makes.
    for cmd in (['build_dese_registry.py'] +
                (['fetch_dese_finance.py'] if any(r['dataset_id'] in FINANCE for r in moved) else [])):
        p = subprocess.run([sys.executable, os.path.join(HERE, cmd)], cwd=ROOT)
        if p.returncode:
            print('  !! %s exited %d' % (cmd, p.returncode))
            failures += 1
    _mark_current(moved)
    print('promoted %d. Everything that reads them must be re-run before anything is '
          'published: grep scripts/ for each file name.' % len(moved))
    return failures


def _mark_current(moved):
    """socrata-status.csv says `updated since our copy` until its next monthly run; once the
    copy IS the update, that row is wrong, and source_cadence.changes() would keep reporting
    it. Re-read just before writing; only these rows touched."""
    if not os.path.exists(STATUS):
        return
    with open(STATUS, newline='', encoding='utf-8') as fh:
        have = list(csv.DictReader(fh))
    ids, today = {r['dataset_id'] for r in moved}, datetime.date.today().isoformat()
    for s in have:
        if s['dataset_id'] in ids:
            s.update(our_copy=today, state='current', checked=today)
    tmp = STATUS + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, C.FIELDS)
        w.writeheader()
        w.writerows(have)
    os.replace(tmp, STATUS)


def check(rows):
    """Offline: every dated version on disk is catalogued with its own sha256."""
    have = {r['local']: r for r in csv.DictReader(open(INDEX, encoding='utf-8'))}
    bad, n = [], 0
    for r in rows:
        for _day, k in versions(r['local'][len('sources/'):]):
            p = A.local_path(k)
            if not os.path.exists(p):
                continue
            n += 1
            row = have.get('sources/' + k)
            if not row:
                bad.append('sources/%s is on disk and not catalogued' % k)
            elif row['sha256'] != A.hash_file(p)[0]:
                bad.append('sources/%s has changed since it was catalogued' % k)
    for b in bad:
        print('  !!', b)
    print('%d dated version(s) of %d datasets: %s'
          % (n, len(rows), 'ok' if not bad else '%d problems' % len(bad)))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true', help='ask the portal; land nothing')
    ap.add_argument('--promote', nargs='*', metavar='DATASET_ID',
                    help='after fetching, make the newest held version the working copy '
                         '(all datasets, or only those named)')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows = socrata_rows()
    if a.check:
        return check(rows)
    failures = fetch(rows, a.dry_run)
    if a.promote is not None and not a.dry_run:
        failures += promote(rows, set(a.promote))
    print('%d datasets asked; %d failure(s)' % (len(rows), failures))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
