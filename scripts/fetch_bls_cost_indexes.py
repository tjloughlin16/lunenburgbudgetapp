#!/usr/bin/env python3
"""THE COST INDEXES: one price index per kind of school spending, from the Bureau of Labor
Statistics, saved as the API returned it and landed through ingest.land().

    python3 scripts/fetch_bls_cost_indexes.py               # fetch and land what is missing
    python3 scripts/fetch_bls_cost_indexes.py --saved DIR   # land responses already fetched
                                                            #   today into DIR, by filename
    python3 scripts/fetch_bls_cost_indexes.py --check       # every file held, every one a
                                                            #   successful answer for its series

WHY. TJ, 20 October 2026, on /school-spending-history/inflation-and-school-costs: every kind
of school spending was measured against ONE household price index, and he agreed to measure
each kind against inflation for that kind of thing instead. Which series stands for which
kind, and why, is OUR choice and is written down in sources/data/inflation-cost-index-map.csv;
this script only fetches what that choice needs.

HOW, AND WHY THIS WAY. Exactly as the Boston CPI was fetched on 18 October 2026
(sources/federal-bls/PROVENANCE.md): BLS's public API, used without a registration key,
which answers at most ten years a request -- so each series is two requests, 2008-2017 and
2018-2026. BLS's flat files (download.bls.gov/pub/time.series/) answered this project 403 on
20 October 2026, as they did on the 18th. The request address IS the document's name: BLS
names no file.

Every file lands DIRECTLY under sources/federal-bls/, named by BLS's own series ID, because
archive_storage.frozen() treats a `.json` there as the publisher's answer (backed up, never
overwritten), and a file in a subfolder would be treated as ours. The names do not begin
`cpi-u-`, which build_spending_staff_students_topics.py reads as the household index.

A RESPONSE IS CHECKED BEFORE IT IS KEPT. The unregistered API answers a daily-limit refusal
with ordinary JSON (`REQUEST_NOT_PROCESSED`), which the ingest sniff cannot tell from data;
so a response is landed only if its status is REQUEST_SUCCEEDED and it holds the series
asked for, with at least one value.
"""
import argparse
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
import ingest  # noqa: E402

API = 'https://api.bls.gov/publicAPI/v2/timeseries/data/%s?startyear=%d&endyear=%d'
RANGES = [(2008, 2017), (2018, 2026)]
# The series sources/data/inflation-cost-index-map.csv names. Household CPI (CUURS11ASA0)
# is NOT here: it is already held, under its own names, from 18 October 2026.
SERIES = [
    'CIU3026110000000I',   # ECI, wages and salaries, state and local government, elementary
                           #   and secondary schools (index, Dec 2005 = 100), quarterly
    'CIU3030000000000I',   # ECI, benefits, state and local government, all workers (BLS
                           #   publishes no benefits series for schools alone), quarterly
    'CUURS11ASAF11',       # CPI-U, food at home, Boston-Cambridge-Newton, monthly
    'CUUR0100SAH21',       # CPI-U, household energy, Northeast region, monthly (the Boston
                           #   household energy series stops at December 2024)
]


def key(series, a, b):
    return 'federal-bls/%s-%d-%d.json' % (series, a, b)


def good(series, blob):
    try:
        d = json.loads(blob)
    except ValueError:
        return 'not JSON'
    if d.get('status') != 'REQUEST_SUCCEEDED':
        return 'status %r: %s' % (d.get('status'), d.get('message'))
    s = d.get('Results', {}).get('series') or []
    if len(s) != 1 or s[0].get('seriesID') != series:
        return 'does not hold %s' % series
    if not s[0].get('data'):
        return 'no values'
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--saved', help='land responses already fetched into this directory')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    bad = 0
    for s in SERIES:
        for y0, y1 in RANGES:
            k = key(s, y0, y1)
            here = os.path.join(ROOT, 'sources', k)
            if a.check:
                why = good(s, open(here, 'rb').read()) if os.path.exists(here) else 'not held'
                print(('ok    ' if not why else 'FAIL  ') + k + ('' if not why else ': ' + why))
                bad += bool(why)
                continue
            if os.path.exists(here):
                print('held  %s' % k)
                continue
            url = API % (s, y0, y1)
            if a.saved:
                blob = open(os.path.join(a.saved, '%s-%d-%d.json' % (s, y0, y1)), 'rb').read()
            else:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 '
                                                           '(lunenburgbudgetproject.org research)'})
                with urllib.request.urlopen(req, timeout=60) as r:
                    blob = r.read()
                time.sleep(2)
            why = good(s, blob)
            if why:
                print('REFUSED %s: %s' % (k, why))
                bad += 1
                continue
            ok, why = ingest.land(k, blob, upstream=url)
            print(('landed %s' % k) if ok else ('FAILED %s: %s' % (k, why)))
            bad += not ok
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
