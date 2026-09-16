#!/usr/bin/env python3
"""How people move through the site, from the first-party events.

    CF_ANALYTICS_TOKEN=... python3 scripts/report_site_events.py            # last 7 days
    CF_ANALYTICS_TOKEN=... python3 scripts/report_site_events.py --days 30

Reads the `lburg_usage_data` Analytics Engine dataset that functions/api/event.js
writes (see src/lib/track.ts for what is and is not recorded -- no cookie, no identifier)
and prints the funnel as counts at each step:

    where people LAND, and from where          view events flagged landing; referrer host
    what gets READ                             view events by page
    which DOOR they take on the front page     door events
    whether the FOLD gets opened, per page     fold_open ÷ views of that page
    which EXIT under the crisis wedge          exit events
    what they SEARCHED for and did not find    search_zero terms
    questions asked                            question events

THE TOKEN. Analytics Engine is queried through the Cloudflare API with an API token
carrying "Account Analytics: Read" (My Profile > API Tokens > Create). It is not the
wrangler login, whose OAuth scopes do not include analytics. Put it in the environment;
never in this file or the repo.

THE COUNTS ARE SAMPLED. Analytics Engine samples under load and reports the sampling
interval per row; every SUM here is over `_sample_interval`, which is the documented way
to get the estimate back. Small numbers are exact; large ones are estimates and say so.
"""
import argparse
import json
import os
import sys
import urllib.request

ACCOUNT = '9221b607bd1ade7b08a96ab614b6edce'
DATASET = 'lburg_usage_data'
URL = 'https://api.cloudflare.com/client/v4/accounts/%s/analytics_engine/sql' % ACCOUNT
# blob1 name · blob2 page · blob3 detail · blob4 referrer host · blob5 country · blob6 landing


def query(sql, token):
    req = urllib.request.Request(URL, data=sql.encode('utf-8'), method='POST',
                                 headers={'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)['data']


def table(rows, cols, head, width=48):
    print('\n' + head)
    if not rows:
        print('  (nothing recorded)')
        return
    for r in rows:
        print('  ' + '  '.join(str(r[c])[:width].ljust(width) if i == 0 else str(r[c]).rjust(8)
                               for i, c in enumerate(cols)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=7)
    a = ap.parse_args()
    token = os.environ.get('CF_ANALYTICS_TOKEN')
    if not token:
        print('set CF_ANALYTICS_TOKEN to an API token with Account Analytics: Read', file=sys.stderr)
        return 2
    since = "timestamp > NOW() - INTERVAL '%d' DAY" % a.days
    q = lambda sql: query(sql % {'d': DATASET, 'since': since}, token)

    print('Site events, last %d days (counts are sample-corrected estimates)' % a.days)

    total = q("SELECT blob1 AS name, SUM(_sample_interval) AS n FROM %(d)s WHERE %(since)s GROUP BY name ORDER BY n DESC")
    table(total, ['name', 'n'], 'EVENTS')

    land = q("SELECT blob2 AS page, SUM(_sample_interval) AS n FROM %(d)s WHERE %(since)s AND blob1='view' AND blob6='landing' GROUP BY page ORDER BY n DESC LIMIT 25")
    table(land, ['page', 'n'], 'WHERE PEOPLE LAND (first page of a visit)')

    ref = q("SELECT blob4 AS host, SUM(_sample_interval) AS n FROM %(d)s WHERE %(since)s AND blob1='view' AND blob6='landing' AND blob4<>'' GROUP BY host ORDER BY n DESC LIMIT 25")
    table(ref, ['host', 'n'], 'FROM WHERE (referrer host on the landing page; blank means typed, bookmarked or an app)')

    views = q("SELECT blob2 AS page, SUM(_sample_interval) AS n FROM %(d)s WHERE %(since)s AND blob1='view' GROUP BY page ORDER BY n DESC LIMIT 40")
    table(views, ['page', 'n'], 'WHAT GETS READ (views by page, including in-app navigation)')

    doors = q("SELECT blob3 AS door, SUM(_sample_interval) AS n FROM %(d)s WHERE %(since)s AND blob1='door' GROUP BY door ORDER BY n DESC")
    table(doors, ['door', 'n'], 'WHICH DOOR on the front page')

    folds = q("SELECT blob2 AS page, SUM(_sample_interval) AS opened FROM %(d)s WHERE %(since)s AND blob1='fold_open' GROUP BY page ORDER BY opened DESC LIMIT 40")
    byview = {r['page']: r['n'] for r in views}
    for r in folds:
        v = byview.get(r['page'], 0)
        r['rate'] = ('%d%%' % round(100 * r['opened'] / v)) if v else '?'
    table(folds, ['page', 'opened', 'rate'], 'THE FOLD: opened, and as a share of that page\'s views')

    exits = q("SELECT blob3 AS exit, SUM(_sample_interval) AS n FROM %(d)s WHERE %(since)s AND blob1='exit' GROUP BY exit ORDER BY n DESC")
    table(exits, ['exit', 'n'], 'WHICH EXIT under the crisis wedge')

    zero = q("SELECT blob3 AS term, SUM(_sample_interval) AS n FROM %(d)s WHERE %(since)s AND blob1='search_zero' GROUP BY term ORDER BY n DESC LIMIT 40")
    table(zero, ['term', 'n'], 'SEARCHED AND FOUND NOTHING (the questions the archive did not answer)')

    countries = q("SELECT blob5 AS country, SUM(_sample_interval) AS n FROM %(d)s WHERE %(since)s AND blob1='view' AND blob6='landing' GROUP BY country ORDER BY n DESC LIMIT 10")
    table(countries, ['country', 'n'], 'COUNTRY of the landing page (bots show up here first)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
