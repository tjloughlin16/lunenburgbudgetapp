"""Shared plumbing for the R2 archive: the manifest, the credential, and the API.

Two scripts use this — `sync_archive.py`, which moves bytes, and
`check_archive_storage.py`, which reconciles what is there against what should be. They
share this module so the two cannot disagree about a key, a hash or an endpoint. The same
reason the fetcher and the repair share one classifier.

**Keys mirror the archive path exactly**, minus the `sources/` prefix:

    sources/town-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.xlsx
          → town-ledgers/expenses/glytdbud-expense-fy2026-p12-gf-all.xlsx

so an object's address describes itself, and the folder names the reorg settled are the
published interface.

**The bucket is locked and the lock blocks overwriting as well as deletion.** Every write
here is therefore a one-way door: a wrong object cannot be corrected in place, only
superseded under a new key. That is why nothing writes without reading back first, and why
`--push` refuses a key whose bytes already differ rather than trying to fix it.

**The credential is wrangler's.** It lives in wrangler's own config outside this
repository, and it is never written here or printed. `wrangler login` is what grants it;
this module only reads it and asks wrangler to refresh it when it is close to expiring.
"""
import csv
import hashlib
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources')

ACCOUNT = '9221b607bd1ade7b08a96ab614b6edce'
BUCKET = 'lunenburg-budget-project'
PUBLIC_BASE = 'https://pub-5baef0f2604545c398a39a176e400e34.r2.dev'
API = (f'https://api.cloudflare.com/client/v4/accounts/{ACCOUNT}'
       f'/r2/buckets/{BUCKET}')

MANIFEST = os.path.join(SRC, 'data', 'archive-manifest.csv')
# What --push has already uploaded and read back. A cache, so a resumed run does not
# re-download 1.4 GB to learn what it did last time. It is a claim about the bucket, not
# the bucket -- check_archive_storage.py asks the bucket itself and never reads this.
STATE = os.path.join(SRC, 'data', 'archive-push-state.csv')

# Files that are ours rather than the archive's, and would be noise in a public download
# area. .DS_Store is the only one that has actually turned up.
SKIP_NAMES = {'.DS_Store'}

# The bucket's own bookkeeping, which lives under sources/data/ and would otherwise be in
# its own manifest. Both change every time the archive does, and an object cannot be
# updated once written, so a copy in the bucket would be permanently out of date about the
# bucket. The current manifest is published by the site instead, which git versions.
SKIP_KEYS = {'data/archive-manifest.csv', 'data/archive-push-state.csv',
             # The two search indexes: derived, gitignored, rebuilt by a script from files
             # the bucket already holds, and re-derived daily -- so every copy in the bucket
             # is an older rendering the moment it lands, and the larger one (340 MB) dies
             # in a single PUT anyway. Neither is a document anyone published.
             'data/search-fts.db', 'data/minutes-fts.db',
             # DUPLICATES UNDER A SECOND NAME, 17 September 2026. For an hour the district
             # crawler unescaped `&#39;` in labels, so eleven documents whose names carry
             # `-39-s-` were re-downloaded as `-s-` and pushed before it was caught. Same
             # bytes as the originals, which the manifest keeps; the bucket cannot delete
             # them, so they are recorded here as what they are.
             *['district-budget/docs/3-12-25-town-manager-s-budget.pdf', 'district-budget/docs/budget-hearing-fy22-superintendent-s-recommended-budget.pdf', 'district-budget/docs/final-fy26-town-manager-s-target-budget-approved-3-12-25.pdf', 'district-budget/docs/final-fy26-town-manager-s-target-budget.pdf', 'district-budget/docs/fy24-superintendent-s-recommended-budget-presentation.pdf', 'district-budget/docs/fy25-superintendent-s-budget-update.pdf', 'district-budget/docs/fy26-superintendent-s-proposed-budget-2-26-25-updated-3-12-25.pdf', 'district-budget/docs/fy26-superintendent-s-proposed-budget-presentation-1-22-25.pdf', 'district-budget/docs/fy26-town-manager-s-target-budget-2-5-25-presentation.pdf', 'district-budget/docs/superintendent-s-fy21-budget-identified-needs.pdf', 'district-budget/docs/updated-town-manager-s-budget-sheets-2-66-2-5-25.xlsx', 'district-budget/text/3-12-25-town-manager-s-budget.txt', 'district-budget/text/budget-hearing-fy22-superintendent-s-recommended-budget.txt', 'district-budget/text/final-fy26-town-manager-s-target-budget-approved-3-12-25.txt', 'district-budget/text/final-fy26-town-manager-s-target-budget.txt', 'district-budget/text/fy24-superintendent-s-recommended-budget-presentation.txt', 'district-budget/text/fy25-superintendent-s-budget-update.txt', 'district-budget/text/fy26-superintendent-s-proposed-budget-2-26-25-updated-3-12-25.txt', 'district-budget/text/fy26-superintendent-s-proposed-budget-presentation-1-22-25.txt', 'district-budget/text/fy26-town-manager-s-target-budget-2-5-25-presentation.txt', 'district-budget/text/superintendent-s-fy21-budget-identified-needs.txt', 'district-budget/text/updated-town-manager-s-budget-sheets-2-66-2-5-25.txt']}

CONTENT_TYPES = {
    '.pdf': 'application/pdf',
    '.csv': 'text/csv; charset=utf-8',
    '.txt': 'text/plain; charset=utf-8',
    '.md': 'text/markdown; charset=utf-8',
    '.json': 'application/json',
    '.html': 'text/html; charset=utf-8',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.xls': 'application/vnd.ms-excel',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.doc': 'application/msword',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.ppt': 'application/vnd.ms-powerpoint',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.zip': 'application/zip',
    '.db': 'application/vnd.sqlite3',
}


def content_type(key):
    return CONTENT_TYPES.get(os.path.splitext(key)[1].lower(),
                             'application/octet-stream')


# --- the credential -------------------------------------------------------------------

WRANGLER_CONFIG = os.path.expanduser(
    '~/Library/Preferences/.wrangler/config/default.toml')
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')


def _read_token():
    if not os.path.exists(WRANGLER_CONFIG):
        sys.exit('No wrangler credential. Run `wrangler login` first.\n'
                 f'  expected {WRANGLER_CONFIG}')
    blob = open(WRANGLER_CONFIG).read()
    tok = re.search(r'oauth_token\s*=\s*"([^"]+)"', blob)
    exp = re.search(r'expiration_time\s*=\s*"([^"]+)"', blob)
    if not tok:
        sys.exit('wrangler config has no oauth_token. Run `wrangler login`.')
    return tok.group(1), (exp.group(1) if exp else '')


def _refresh_token():
    """Ask wrangler to refresh its own OAuth token, by making it do something cheap.

    Wrangler needs Node 22; the system Node is 20 and fails, which is why the nvm path is
    prepended rather than trusted to be on PATH.
    """
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    subprocess.run(['npx', 'wrangler', 'r2', 'bucket', 'list'],
                   cwd=os.path.join(ROOT, 'fy28'), env=env,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)


_token_cache = {'value': None, 'expires': ''}


def token(force_refresh=False):
    import datetime
    if force_refresh:
        _refresh_token()
        _token_cache['value'] = None
    if _token_cache['value'] is None:
        _token_cache['value'], _token_cache['expires'] = _read_token()
    exp = _token_cache['expires']
    if exp:
        try:
            when = datetime.datetime.strptime(exp, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            when = None
        if when and when - datetime.datetime.utcnow() < datetime.timedelta(minutes=5):
            _refresh_token()
            _token_cache['value'], _token_cache['expires'] = _read_token()
    return _token_cache['value']


# --- the API --------------------------------------------------------------------------

class NotFound(Exception):
    pass


# Cloudflare's REST API for R2 objects allows roughly 1,200 requests per five minutes --
# four a second -- and answers 429 with "consider throttling your request speed" above it.
# A push makes two requests per file (the PUT and the read-back), so 3,876 files is nearly
# 8,000 requests and the limit is the thing that decides how long it takes, not bandwidth.
# The limiter is global rather than per-thread because the quota is.
RATE = float(os.environ.get('ARCHIVE_RATE', '3.0'))
_rate_lock = threading.Lock()
_next_slot = [0.0]


def _wait_turn():
    with _rate_lock:
        now = time.monotonic()
        slot = max(now, _next_slot[0])
        _next_slot[0] = slot + 1.0 / RATE
    delay = slot - time.monotonic()
    if delay > 0:
        time.sleep(delay)


def _back_off(seconds):
    """Push every thread's next slot out, not just this one's.

    A 429 means the account is over its quota, so having only the unlucky thread wait
    would let the other seven keep spending it.
    """
    with _rate_lock:
        _next_slot[0] = max(_next_slot[0], time.monotonic() + seconds)


def _request(method, url, data=None, headers=None, timeout=300):
    """One API call, with the token refreshed once on a 401 and retried on a 5xx.

    A 404 is raised as NotFound rather than an error: "this object is not there yet" is
    the normal case during a push, not a failure.
    """
    last, tries = None, 8
    for attempt in range(tries):
        _wait_turn()
        h = {'Authorization': 'Bearer ' + token(force_refresh=(attempt == 1))}
        h.update(headers or {})
        req = urllib.request.Request(url, data=data, method=method, headers=h)
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            body = b''
            try:
                body = e.read()[:600]
            except Exception:
                pass
            if e.code == 404:
                raise NotFound(url)
            last = f'HTTP {e.code} {method} {url.rsplit("/", 1)[-1]}: {body!r}'
            # 409 is the bucket lock refusing to overwrite. That is a decision, not a
            # hiccup, and retrying it eight times only wastes quota.
            if e.code == 409:
                raise RuntimeError(last)
            if e.code == 401 and attempt == 0:
                continue
            if e.code == 429 and attempt < tries - 1:
                _back_off(10 * (attempt + 1))
                continue
            if e.code in (500, 502, 503, 504) and attempt < tries - 1:
                time.sleep(2 ** min(attempt, 5))
                continue
            raise RuntimeError(last)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = f'{type(e).__name__} {method} {url}: {e}'
            if attempt < tries - 1:
                time.sleep(2 ** min(attempt, 5))
                continue
            raise RuntimeError(last)
    raise RuntimeError(last or 'request failed')


def _object_url(key):
    # The key goes in the path. Every character in this archive's keys is already
    # URL-safe -- no spaces, no quotes -- and quoting the slashes would break the path,
    # so the assertion is made rather than assumed.
    assert re.fullmatch(r'[A-Za-z0-9._/-]+', key), f'unsafe key: {key!r}'
    return f'{API}/objects/{key}'


def get_object(key, sink=None):
    """Stream an object out of the bucket, returning (sha256, md5, bytes read).

    Reads back rather than trusting the write. The point of the whole exercise is that
    the copy in the bucket is the document, and an upload that reported success is a
    claim about the upload, not about the object.
    """
    res = _request('GET', _object_url(key))
    sha, md5, n = hashlib.sha256(), hashlib.md5(), 0
    while True:
        chunk = res.read(1 << 20)
        if not chunk:
            break
        sha.update(chunk)
        md5.update(chunk)
        n += len(chunk)
        if sink is not None:
            sink.write(chunk)
    return sha.hexdigest(), md5.hexdigest(), n


def put_object(key, path):
    with open(path, 'rb') as fh:
        body = fh.read()
    _request('PUT', _object_url(key), data=body,
             headers={'Content-Type': content_type(key),
                      'Content-Length': str(len(body))})


def list_objects(prefix=''):
    """Every object in the bucket, as the bucket reports it: name, size, etag.

    The etag of a single-part upload is the MD5 of the bytes, which is the only thing a
    listing gives you that can be compared to a local file without downloading it.
    """
    import json
    out, cursor = [], None
    while True:
        url = f'{API}/objects?per_page=1000'
        if prefix:
            url += '&prefix=' + urllib.request.quote(prefix)
        if cursor:
            url += '&cursor=' + urllib.request.quote(cursor)
        payload = json.loads(_request('GET', url).read())
        if not payload.get('success'):
            raise RuntimeError(f'list failed: {payload.get("errors")}')
        out.extend(payload.get('result') or [])
        cursor = (payload.get('result_info') or {}).get('cursor')
        if not cursor:
            return out


# --- the manifest ---------------------------------------------------------------------

def hash_file(path):
    sha, md5, n = hashlib.sha256(), hashlib.md5(), 0
    with open(path, 'rb') as fh:
        while True:
            chunk = fh.read(1 << 20)
            if not chunk:
                break
            sha.update(chunk)
            md5.update(chunk)
            n += len(chunk)
    return sha.hexdigest(), md5.hexdigest(), n


def walk_sources():
    """Every file under sources/, as bucket keys, in a stable order."""
    keys = []
    for dirpath, dirnames, filenames in os.walk(SRC):
        dirnames.sort()
        for name in sorted(filenames):
            if name in SKIP_NAMES:
                continue
            full = os.path.join(dirpath, name)
            key = os.path.relpath(full, SRC)
            if key in SKIP_KEYS:
                continue
            keys.append(key)
    return sorted(keys)


def local_path(key):
    return os.path.join(SRC, key)


def read_manifest(path=MANIFEST):
    if not os.path.exists(path):
        return {}
    with open(path, newline='') as fh:
        return {r['key']: r for r in csv.DictReader(fh)}


def write_manifest(rows, path=MANIFEST):
    cols = ['key', 'bytes', 'sha256', 'etag_md5', 'upstream']
    tmp = path + '.tmp'
    with open(tmp, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, '') for c in cols})
    os.replace(tmp, path)


def upstream_urls():
    """The publisher's own URL for each document, from the per-folder index.csv files.

    Rule 12: a copy is only checkable if somebody can get back to the document it came
    from, so the manifest carries the address alongside the hash. Most objects have none
    -- extracted text, derived CSVs, and the 43 primary documents gathered before the
    mirror existed -- and an empty cell says so rather than inventing one.
    """
    out = {}
    for folder in sorted(os.listdir(SRC)):
        idx = os.path.join(SRC, folder, 'index.csv')
        if not os.path.exists(idx):
            continue
        matched = 0
        with open(idx, newline='') as fh:
            for row in csv.DictReader(fh):
                url = (row.get('upstream') or row.get('url') or '').strip()
                for col in ('local', 'text', 'path'):
                    rel = (row.get(col) or '').strip()
                    if not rel:
                        continue
                    rel = rel[len('sources/'):] if rel.startswith('sources/') else rel
                    # AN INDEX MAY BE WRITTEN RELATIVE TO ITS OWN FOLDER, and
                    # `sources/meetings/index.csv` is: it stores
                    # `select-board/2018-06-18-minutes-5130.pdf` where the manifest key
                    # is `meetings/select-board/...`. Unqualified, the join matched none
                    # of 24,033 rows and every upstream cell was written empty -- which
                    # reads as "the town published no address for these" when in fact
                    # all 12,065 addresses were sitting one column away. That is the
                    # third defect shape in CLAUDE.md: a join matching nothing is
                    # indistinguishable from data that is absent.
                    if not rel.startswith(folder + '/'):
                        rel = folder + '/' + rel
                    if url and rel not in out:
                        out[rel] = url
                        matched += 1
        # AND IT ASSERTS THAT IT MATCHED. An index that stops joining must fail loudly
        # rather than quietly contribute nothing.
        if matched == 0:
            raise SystemExit(
                'sources/%s/index.csv yielded no upstream addresses. Either it has no '
                'url column or its paths no longer line up with the manifest keys; '
                'either way the manifest would silently record 0 addresses for that '
                'folder.' % folder)
    return out


# --- what is frozen, and what only looks like it -------------------------------------

# The bucket lock blocks overwriting, so an object put there can never be corrected --
# only superseded under a new key. That makes the bucket right for one kind of file and
# wrong for another, and the line between them is the same line CLAUDE.md already draws
# for what stays in git:
#
#   * a document somebody else published does not change. If our copy ever differs from
#     what we uploaded that is a defect, not a revision, and freezing it is the point.
#   * everything we derive from those documents DOES change -- extracted text changes
#     when an extractor improves, and the analyses change when a rate does. Git versions
#     those properly: atomic across files, with a message, reviewable before it merges.
#
# So membership is decided by extension and location rather than by size. `analyses/` and
# `data/` are ours whatever the extension; `text/`, `ocr/` and `pages/` are our renderings
# of somebody else's document, sitting beside it.
ORIGINAL_EXTS = {'.pdf', '.xlsx', '.xls', '.docx', '.doc', '.pptx', '.ppt',
                 '.html', '.zip', '.bin', '.key'}
OURS_TOP = {'analyses', 'data'}
OURS_DIRS = {'text', 'ocr', 'pages'}


# A DATED SNAPSHOT FOLDER IS FROZEN WHATEVER IS IN IT. `2026-09-25/` is a statement that
# these are the bytes a publisher was serving on that day, and a day does not happen twice.
DATED_SNAPSHOT = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def incomplete(prefix=None, manifest_path=None):
    """Documents the index names that THIS TREE does not hold.

    `prefix` SCOPES IT TO WHAT THE CALLER ACTUALLY COUNTS, and passing it is the difference
    between a useful check and one that gets ignored. The first version took no prefix, so
    `build_minutes_searchable.py` -- which counts MEETING documents -- refused to run
    because three `state-dls` and `district-budget` files were absent. Those cannot affect a
    count of minutes, and two of them are registered in `document-defects.csv` as documents
    whose publisher replaced the bytes, so they can never be pulled and the check would have
    been permanently red. A check that is always failing is a check nobody reads.

    A COUNT COMPUTED IN A PARTIAL TREE IS AN UNDERSTATEMENT, and nothing said so. On 25
    September 2026 the sentence *"N meeting documents this archive holds are searchable"*
    had three defensible values at once -- 12,055 here, 12,072 in a payload committed two
    days earlier, 12,088 from a complete tree -- because `build_minutes_searchable.py`
    defines `held` as *index rows whose file exists on disk*. Every one was correct about
    its own tree, which is exactly what made it useless. Two hours went into "33 documents
    are missing" before that was understood; they were in the other worktree.

    So a generator that publishes a corpus count asks this first and REFUSES rather than
    understating. The remedy is one command -- `sync_archive.py --pull` -- which is why
    refusing costs nothing and publishing a low number costs a correction later.

    Frozen keys only: our derived files legitimately come and go.
    """
    rows = read_manifest(manifest_path or MANIFEST)
    return sorted(k for k in rows
                  if frozen(k)
                  and (prefix is None or k.startswith(prefix))
                  and not os.path.exists(local_path(k)))


def frozen(key):
    """Is this key one of the publisher's own files, rather than one of our renderings?

    THE EXTENSION IS A PROXY AND IT LEAKED. `ORIGINAL_EXTS` decides this, which means a
    document the publisher happened to serve as CSV was classified as OURS -- so nothing
    required it to be backed up, and `--push --frozen` skipped it. The district publishes
    its staff directories as Google Sheets, and the CSV export is the ROWS: the thing every
    figure in `school-staff-directory.csv` is computed from. Six files, held in one place,
    that the archive's own promise did not cover.

    That is rule 13a's lesson pointed at backup policy: *ask which produced it, never what
    it was saved as.* `.csv` cannot simply be added to `ORIGINAL_EXTS` -- every
    `sources/*/index.csv` is OUR catalogue and changes constantly, and freezing one would
    make the manifest refuse to write the moment it did.

    So the second test is the PATH, not the name: a file inside a dated snapshot folder is
    the publisher's, on that date, whatever its extension. Those folders exist precisely
    because the publisher overwrites in place and the snapshot is the only record -- which
    is the strongest possible reason to require a backup. A `checked.csv` at the root of
    such a tree is ours and is not caught, correctly, because it appends on every run.
    """
    parts = key.split('/')
    if parts[0] in OURS_TOP:
        return False
    if OURS_DIRS & set(parts[:-1]):
        return False
    if any(DATED_SNAPSHOT.match(p) for p in parts[:-1]):
        return True
    return os.path.splitext(parts[-1])[1].lower() in ORIGINAL_EXTS
