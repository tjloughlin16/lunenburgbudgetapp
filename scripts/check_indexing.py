#!/usr/bin/env python3
"""Have the search engines actually indexed this site — asked, not inferred.

WHY THIS EXISTS

Three agents in two days could not read anything under the homepage, and two of them said
why: the domain is not in a search index, and their fetchers only follow links that came
back from a search result. That makes indexing the load-bearing question of the whole
agent-access workstream — and until now the only evidence in either direction was an agent
saying "I searched and found nothing", which is a report, not a measurement.

`CLAUDE.md` rules out the tempting shortcut: **nothing here scrapes a `site:` query and
calls the count a measurement.** A scraped result page is a rendering, and quoting a
rendering as an observation is rule 13. So this asks the two engines through their own
APIs, which answer about their own index.

WHAT IT DOES NOT DO

It does not decide whether a URL is "fine". Google returns a `coverageState` in its own
words — `Submitted and indexed`, `Crawled - currently not indexed`,
`Discovered - currently not indexed`, `URL is unknown to Google` — and those distinctions
carry the diagnosis. Collapsing them into a boolean would throw away the only part worth
reading, so this prints the string verbatim and counts by it.

It also never fails the build for a URL not being indexed. That is a fact about Google,
not a defect in this repository. It exits non-zero only when a credential is broken or an
API refuses, because those mean the ANSWER IS ABSENT — and an absent answer that reads
like "nothing is indexed" is the exact failure shape this project exists to stamp out.

CREDENTIALS — both are free, neither is in git

  Google:  a service account with the Search Console API enabled, its JSON key at
           secrets/gsc-service-account.json, and the service account's email added as a
           user on the Search Console property. Scope: webmasters.readonly.
  Bing:    an API key from Bing Webmaster Tools → Settings (top right) → API Access,
           in secrets/bing-api-key.txt or $BING_API_KEY.

Either half runs on its own. Missing credentials are reported as missing, never as zero.

    python3 scripts/check_indexing.py
    python3 scripts/check_indexing.py --engine google
    python3 scripts/check_indexing.py --csv sources/data/indexing-status.csv
"""

import argparse
import base64
import csv
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITEMAP = os.path.join(ROOT, 'fy28', 'public', 'sitemap.xml')
SECRETS = os.path.join(ROOT, 'secrets')
GSC_KEY = os.path.join(SECRETS, 'gsc-service-account.json')
BING_KEY = os.path.join(SECRETS, 'bing-api-key.txt')

# The property as Search Console names it. A Domain property is `sc-domain:<host>`; a
# URL-prefix property is the prefix itself. Ours was verified by DNS, so it is the former.
SITE_URL = 'sc-domain:lunenburgbudgetproject.org'
BING_SITE = 'https://lunenburgbudgetproject.org'

INSPECT = 'https://searchconsole.googleapis.com/v1/urlInspection/index:inspect'
TOKEN_URL = 'https://oauth2.googleapis.com/token'
SCOPE = 'https://www.googleapis.com/auth/webmasters.readonly'
BING_API = 'https://ssl.bing.com/webmaster/api.svc/json'

# Google documents 2,000 inspections a day and 600 a minute per property. 68 URLs is far
# inside both, but the pause keeps a future larger sitemap inside the per-minute one
# without anybody having to remember this paragraph.
PAUSE = 0.12


def b64u(raw: bytes) -> str:
    """base64url, unpadded — what JWS requires and what base64.b64encode does not give."""
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode()


def sign_rs256(private_key_pem: str, message: bytes) -> bytes:
    """RS256 over `message`, using openssl with the key on a private temp file."""
    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.pem', delete=False) as fh:
        os.chmod(fh.name, 0o600)
        fh.write(private_key_pem)
        path = fh.name
    try:
        proc = subprocess.run(
            ['openssl', 'dgst', '-sha256', '-sign', path, '-binary'],
            input=message, capture_output=True)
        if proc.returncode != 0:
            raise SystemExit('openssl could not sign the JWT: '
                             + proc.stderr.decode(errors='replace').strip())
        return proc.stdout
    finally:
        os.unlink(path)


def google_token(key_path):
    with open(key_path) as fh:
        key = json.load(fh)
    for field in ('client_email', 'private_key'):
        if field not in key:
            raise SystemExit(f'{key_path}: not a service-account key — no {field!r}')
    now = int(time.time())
    aud = key.get('token_uri', TOKEN_URL)
    header = b64u(json.dumps({'alg': 'RS256', 'typ': 'JWT'}).encode())
    claims = b64u(json.dumps({
        'iss': key['client_email'], 'scope': SCOPE, 'aud': aud,
        'iat': now, 'exp': now + 3600}).encode())
    signing_input = f'{header}.{claims}'.encode()
    jwt = f'{header}.{claims}.{b64u(sign_rs256(key["private_key"], signing_input))}'

    body = urllib.parse.urlencode({
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        'assertion': jwt}).encode()
    req = urllib.request.Request(aud, data=body, method='POST',
                                 headers={'content-type':
                                          'application/x-www-form-urlencoded'})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.load(res)['access_token']
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors='replace')[:400]
        raise SystemExit(
            f'Google refused the service-account assertion ({e.code}).\n  {detail}\n'
            '  Usually one of: the Search Console API is not enabled on the project, or\n'
            '  the service account email is not added as a user on the property.')


def sitemap_urls():
    """The URLs we publish, read from the sitemap rather than typed.

    If this is ever empty the run must stop. A check that inspects nothing prints nothing,
    and nothing reads as `not indexed` — which is the one conclusion this script exists to
    make impossible to reach by accident.
    """
    ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    root = ET.parse(SITEMAP).getroot()
    urls = [e.text.strip() for e in root.findall('.//s:loc', ns) if e.text]
    if not urls:
        raise SystemExit(f'{SITEMAP} lists no URLs. Refusing to report an empty index.')
    return urls


def inspect_google(token, url):
    body = json.dumps({'inspectionUrl': url, 'siteUrl': SITE_URL}).encode()
    req = urllib.request.Request(INSPECT, data=body, method='POST', headers={
        'authorization': f'Bearer {token}', 'content-type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=45) as res:
            r = json.load(res)
    except urllib.error.HTTPError as e:
        return {'error': f'HTTP {e.code}: {e.read().decode(errors="replace")[:160]}'}
    idx = r.get('inspectionResult', {}).get('indexStatusResult', {})
    return {
        # Google's own words, not ours. The distinction between "Crawled - currently not
        # indexed" and "URL is unknown to Google" is the entire diagnosis, and any mapping
        # we invented would throw it away.
        'coverageState': idx.get('coverageState', ''),
        'verdict': idx.get('verdict', ''),
        'robotsTxtState': idx.get('robotsTxtState', ''),
        'lastCrawlTime': idx.get('lastCrawlTime', ''),
    }


def inspect_bing(key, url):
    q = urllib.parse.urlencode({'apikey': key, 'siteUrl': BING_SITE, 'url': url})
    req = urllib.request.Request(f'{BING_API}/GetUrlInfo?{q}',
                                 headers={'user-agent': 'lunenburgbudgetproject.org/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=45) as res:
            r = json.load(res)
    except urllib.error.HTTPError as e:
        return {'error': f'HTTP {e.code}: {e.read().decode(errors="replace")[:160]}'}
    d = r.get('d') or {}
    return {'bing_discovered': d.get('DiscoveredDate', ''),
            'bing_indexed': d.get('LastCrawledDate', ''),
            'bing_docs': d.get('TotalDiscoveredPages', '')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--engine', choices=['google', 'bing', 'both'], default='both')
    ap.add_argument('--csv', help='also write the per-URL answers here')
    args = ap.parse_args()

    urls = sitemap_urls()
    rows, engines_run = [], []

    token = None
    if args.engine in ('google', 'both'):
        if os.path.exists(GSC_KEY):
            token = google_token(GSC_KEY)
            engines_run.append('google')
        else:
            print(f'  google: SKIPPED — no {os.path.relpath(GSC_KEY, ROOT)}.\n'
                  '          This is a MISSING ANSWER, not a finding of "not indexed".')

    bing_key = os.environ.get('BING_API_KEY')
    if not bing_key and os.path.exists(BING_KEY):
        bing_key = open(BING_KEY).read().strip()
    if args.engine in ('bing', 'both'):
        if bing_key:
            engines_run.append('bing')
        else:
            print(f'  bing:   SKIPPED — no $BING_API_KEY and no '
                  f'{os.path.relpath(BING_KEY, ROOT)}.\n'
                  '          This is a MISSING ANSWER, not a finding of "not indexed".')

    if not engines_run:
        raise SystemExit(
            '\nNo engine could be asked, so nothing is known either way.\n'
            'Read the docstring for the two credentials; both are free.')

    print(f'\nasking {", ".join(engines_run)} about {len(urls)} published URLs\n')
    for url in urls:
        row = {'url': url}
        if token:
            row.update(inspect_google(token, url))
            time.sleep(PAUSE)
        if bing_key and 'bing' in engines_run:
            row.update(inspect_bing(bing_key, url))
            time.sleep(PAUSE)
        rows.append(row)
        state = row.get('coverageState') or row.get('error') or ''
        print(f'  {state[:46]:<46} {url}')

    # Counted by Google's own string. Never bucketed into ok/not-ok: "Crawled - currently
    # not indexed" and "URL is unknown to Google" mean different things to do next.
    if token:
        tally = {}
        for r in rows:
            tally[r.get('coverageState') or r.get('error', '(no answer)')] = \
                tally.get(r.get('coverageState') or r.get('error', '(no answer)'), 0) + 1
        print('\ngoogle, by its own coverageState:')
        for state, n in sorted(tally.items(), key=lambda kv: -kv[1]):
            print(f'  {n:>4}  {state}')
        print(f'  ----  of {len(urls)} URLs published in the sitemap')

    errors = [r for r in rows if r.get('error')]
    if errors:
        print(f'\n{len(errors)} URL(s) got an error rather than an answer:')
        for r in errors[:5]:
            print(f'  {r["url"]}\n    {r["error"]}')

    if args.csv:
        path = args.csv if os.path.isabs(args.csv) else os.path.join(ROOT, args.csv)
        cols = sorted({k for r in rows for k in r})
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=['url'] + [c for c in cols if c != 'url'])
            w.writeheader()
            w.writerows(rows)
        print(f'\nwrote {os.path.relpath(path, ROOT)}')

    # An unindexed URL is a fact about Google. A URL we could not ask about is a hole in
    # this check, and only the second one is a failure here.
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
