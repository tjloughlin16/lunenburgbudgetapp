#!/usr/bin/env python3
"""Is the sitemap live, correct, and has anything been told about it?

    python3 scripts/check_sitemap.py            # fetch it and check every URL answers
    python3 scripts/check_sitemap.py --submit   # and tell the search engines it changed

TWO DIFFERENT QUESTIONS, AND ONLY ONE OF THEM IS OURS TO ANSWER

**Is the sitemap right?** Entirely checkable, and this does it: fetch the deployed file,
parse it, and fetch every URL in it. A sitemap listing an address that 404s is worse than
one that omits it, because a crawler that finds a dead link there trusts the rest less.

**Has anything indexed it?** Not checkable from here, and no script should pretend
otherwise. Whether Google has crawled a URL is knowable only in Google Search Console,
which needs the domain verified. Bing Webmaster Tools is the equivalent. Anything else --
scraping a `site:` query, counting results -- is a guess dressed as a measurement, and this
project has a rule about that.

What CAN be done without waiting is telling them. `--submit` uses IndexNow: a key file at
the site root proves ownership, and a POST lists the URLs that changed. Bing, Yandex,
Seznam and Naver participate; Google does not. Bing matters here because several agent
search tools are built on it, and being in a search result is what makes a URL fetchable
for a tool whose allowlist is built from search results -- which is the failure that
prompted all of this.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://lunenburgbudgetproject.org'
HOST = 'lunenburgbudgetproject.org'
KEY_FILE = os.path.join(ROOT, 'sources', 'data', 'indexnow-key.txt')
UA = {'User-Agent': 'lunenburgbudgetproject.org sitemap check'}


def get(url, timeout=60):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=UA), timeout=timeout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--submit', action='store_true',
                    help='tell the IndexNow search engines these URLs changed')
    ap.add_argument('--base', default=SITE)
    args = ap.parse_args()

    try:
        xml = get(args.base + '/sitemap.xml').read().decode()
    except Exception as e:                                       # noqa: BLE001
        print(f'could not fetch {args.base}/sitemap.xml: {e}')
        return 1
    urls = re.findall(r'<loc>([^<]+)</loc>', xml)
    lastmod = sorted(set(re.findall(r'<lastmod>([^<]+)</lastmod>', xml)))
    if not urls:
        print('sitemap.xml has no <loc> entries')
        return 1
    print(f'{len(urls)} URLs, lastmod {", ".join(lastmod) or "absent"}')

    bad = []
    for u in urls:
        try:
            res = get(u, timeout=45)
            if res.status != 200:
                bad.append((u, str(res.status)))
        except urllib.error.HTTPError as e:
            bad.append((u, f'HTTP {e.code}'))
        except Exception as e:                                   # noqa: BLE001
            bad.append((u, type(e).__name__))
    ok = len(urls) - len(bad)
    print(f'  {ok} answer, {len(bad)} do not')
    for u, why in bad[:10]:
        print(f'    {why:9s} {u.replace(SITE, "")}')
    if bad:
        print('\n  A sitemap naming an address that does not answer is worse than one that\n'
              '  omits it: a crawler that finds a dead link there trusts the rest less.')
        return 1

    if args.submit:
        if not os.path.exists(KEY_FILE):
            print('\nno IndexNow key at ' + os.path.relpath(KEY_FILE, ROOT))
            return 1
        key = open(KEY_FILE).read().strip()
        # The key file must be reachable, or the submission is refused silently.
        try:
            served = get(f'{SITE}/{key}.txt').read().decode().strip()
        except Exception as e:                                   # noqa: BLE001
            print(f'\nthe key file is not served at {SITE}/{key}.txt: {e}')
            return 1
        if served != key:
            print(f'\n{SITE}/{key}.txt does not contain the key')
            return 1
        body = json.dumps(dict(host=HOST, key=key,
                               keyLocation=f'{SITE}/{key}.txt',
                               urlList=urls)).encode()
        req = urllib.request.Request('https://api.indexnow.org/indexnow', data=body,
                                     headers={**UA, 'Content-Type': 'application/json'},
                                     method='POST')
        try:
            res = urllib.request.urlopen(req, timeout=60)
            print(f'\nsubmitted {len(urls)} URLs to IndexNow — HTTP {res.status}')
        except urllib.error.HTTPError as e:
            detail = ''
            try:
                detail = e.read().decode()[:200]
            except Exception:
                pass
            print(f'\nIndexNow refused: HTTP {e.code} {detail}')
            return 1
        print('  Bing, Yandex, Seznam and Naver participate. Google does not — for Google,\n'
              '  Search Console is the only way to see or influence what is indexed.')
    else:
        print('\nok: every URL in the sitemap answers')
        print('  Whether anything has INDEXED them is not knowable from here. Google\n'
              '  Search Console and Bing Webmaster Tools are the only honest answers to\n'
              '  that, and both need the domain verified. `--submit` tells the IndexNow\n'
              '  engines it changed, which is the part that does not require waiting.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
