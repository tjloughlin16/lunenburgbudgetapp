#!/usr/bin/env python3
"""HOW FAR EVERY AWAY VENUE IS, BY ROAD, from Lunenburg Middle High School.

    python3 scripts/build_athletics_venue_distances.py           # geocode + route what is new
    python3 scripts/build_athletics_venue_distances.py --check   # offline: rebuild from the cache

Reads every distinct street address an `@` game's page prints in
`sources/data/athletics-schedules.csv` and writes `sources/data/athletics-venue-distances.csv`.

THE ORIGIN IS READ, NOT ASSUMED. `1079 Massachusetts Avenue Lunenburg, MA 01462` is the
address Lunenburg High School prints in its own footer at https://lhs.lunenburgschools.net/
(read 11 October 2026); ArbiterLive prints the same street address for the school entity.

HOW, AND WHAT IS OURS.

  * Geocoding: Nominatim (OpenStreetMap), https://nominatim.openstreetmap.org/search, one
    request a second, User-Agent naming lunenburgbudgetproject.org, per its usage policy.
  * Routing: the public OSRM demo server, https://router.project-osrm.org, car profile, OSM
    road data. `round_trip_miles` is OSRM's school->venue distance PLUS its venue->school
    distance -- two routes, because one-way streets make them differ -- not 2 x one way.
  * EVERY RESPONSE IS KEPT, verbatim, in `sources/data/athletics-venue-geocache.csv`, keyed by
    the request URL. A run asks the network only for a URL that file does not hold, and
    `--check` asks it for nothing: it rebuilds the output from the cache and compares.

WHEN A DISTANCE IS LEFT BLANK. `geocode_match` says what Nominatim matched:
`house number` (the address point), `street` (the street, no house number -- the point is
somewhere on that road), `place` (a named building or ground), `town only` (a town, postcode
or county centre) or `failed`. A match is also refused as `mismatch` when its postcode and
its town both disagree with the address asked for. For `town only`, `mismatch` and `failed`
the distance is BLANK. A town centre is not the venue, and a distance to it would be a
figure we made up. So is a venue whose printed address is the school's own (below).
"""
import argparse
import collections
import csv
import datetime
import io
import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES = os.path.join(ROOT, 'sources', 'data', 'athletics-schedules.csv')
OUT = os.path.join(ROOT, 'sources', 'data', 'athletics-venue-distances.csv')
CACHE = os.path.join(ROOT, 'sources', 'data', 'athletics-venue-geocache.csv')
CACHE_FIELDS = ['url', 'fetched_on', 'response']

ORIGIN_NAME = 'Lunenburg Middle High School'
ORIGIN_ADDRESS = '1079 Massachusetts Avenue Lunenburg, MA 01462'
ORIGIN_SOURCE = 'https://lhs.lunenburgschools.net/ (footer), read 2026-10-11'

NOMINATIM = 'https://nominatim.openstreetmap.org/search'
OSRM = 'https://router.project-osrm.org/route/v1/driving/'
UA = 'lunenburgbudgetproject.org athletics travel distances (public budget archive)'
METRES_PER_MILE = 1609.344
FIELDS = ['venue', 'address', 'games', 'lat', 'lon', 'geocode_match', 'geocode_display',
          'straight_line_miles', 'one_way_miles', 'return_miles', 'round_trip_miles',
          'method', 'fetched_on']
STATES = r'(?:MA|Massachusetts|NH|New Hampshire|RI|Rhode Island|CT|Connecticut|VT|Vermont|ME|Maine|NY)'
SUFFIX = (r'(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Lane|Ln|Way|Boulevard|Blvd|Parkway|Pkwy|'
          r'Highway|Hwy|Row|Circle|Cir|Court|Ct|Place|Pl|Pike|Turnpike|Tpke|Terrace|Ter|Square|'
          r'Sq|Trail|Path|Hill|Common|Plaza|Extension|Ext)\.?')
TOWN_LEVEL = {'city', 'town', 'village', 'hamlet', 'municipality', 'postcode', 'county',
              'state', 'suburb', 'neighbourhood', 'quarter', 'borough', 'country', 'region'}


class Cache:
    def __init__(self, offline):
        self.offline = offline
        self.rows = {}
        if os.path.exists(CACHE):
            self.rows = {r['url']: r for r in csv.DictReader(open(CACHE, encoding='utf-8'))}
        self.last = 0.0
        self.new = 0

    def get(self, url):
        if url in self.rows:
            r = self.rows[url]
            return json.loads(r['response']), r['fetched_on']
        if self.offline:
            raise KeyError(url)
        wait = 1.05 - (time.time() - self.last)
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
        for attempt in range(3):
            try:
                body = urllib.request.urlopen(req, timeout=60).read().decode('utf-8')
                break
            except Exception as e:                      # noqa: BLE001
                if attempt == 2:
                    raise SystemExit('%s: %s' % (url, e))
                time.sleep(5)
        self.last = time.time()
        day = datetime.date.today().isoformat()
        self.rows[url] = {'url': url, 'fetched_on': day, 'response': body}
        self.new += 1
        if self.new % 20 == 0:
            self.save()
        return json.loads(body), day

    def save(self):
        tmp = CACHE + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=CACHE_FIELDS, lineterminator='\n')
            w.writeheader()
            for k in sorted(self.rows):
                w.writerow(self.rows[k])
        os.replace(tmp, CACHE)


def split(address):
    """(street, town, zip) where the address can be split at a street suffix; else
    (None, None, zip). ArbiterLive prints `141 Washington Street Ayer, MA 01432` with no
    comma between street and town, so the boundary is the last street-type word."""
    a = re.sub(r'\s+', ' ', address).strip()
    m = re.match(r'^(.*?),?\s+' + STATES + r',?\s+(\d{5})(?:-\d{4})?$', a)
    if not m:
        z = re.search(r'\b(\d{5})(?:-\d{4})?\s*$', a)
        return None, None, z.group(1) if z else None
    head, zp = m.group(1), m.group(2)
    if ',' in head:
        street, town = head.rsplit(',', 1)
        return street.strip(), town.strip(), zp
    sm = list(re.finditer(r'\b' + SUFFIX + r'(?=\s)', head, flags=re.I))
    if sm:
        cut = sm[-1].end()
        return head[:cut].strip(), head[cut:].strip(' ,'), zp
    return None, None, zp


def clean_street(s):
    s = re.sub(r'\b([NSEW])\.(?=\S)', r'\1 ', s)          # `W.Boylston` -> `W Boylston`
    s = re.sub(r'#\s*\S+', '', s)
    s = re.sub(r'\bRte\.?\s*', 'Route ', s, flags=re.I)
    return re.sub(r'\s+', ' ', s).strip()


def queries(address):
    street, town, zp = split(address)
    out = []
    if street and town:
        st = clean_street(street)
        out.append({'street': st, 'city': town, 'postalcode': zp or ''})
        out.append({'q': '%s, %s %s' % (st, town, zp or '')})
    out.append({'q': re.sub(r'\s+', ' ', address)})
    urls = []
    for q in out:
        q = {k: v for k, v in q.items() if v}
        q.update({'format': 'jsonv2', 'addressdetails': '1', 'limit': '1', 'countrycodes': 'us'})
        urls.append(NOMINATIM + '?' + urllib.parse.urlencode(sorted(q.items())))
    return urls, town, zp


def classify(hit, address, town, zp):
    ad = hit.get('address', {})
    at = hit.get('addresstype') or hit.get('type') or ''
    if at in TOWN_LEVEL:
        kind = 'town only'
    elif ad.get('house_number'):
        kind = 'house number'
    elif hit.get('category') == 'highway' or at == 'road':
        kind = 'street'
    else:
        kind = 'place'
    got_zip = (ad.get('postcode') or '')[:5]
    got_towns = {(ad.get(k) or '').lower() for k in ('city', 'town', 'village', 'hamlet',
                                                     'municipality', 'suburb')} - {''}
    zip_ok = bool(zp and got_zip == zp)
    town_ok = bool(town and town.lower() in got_towns)
    if kind != 'town only' and (zp or town) and not zip_ok and not town_ok:
        kind = 'mismatch'
    return kind


def geocode(cache, address):
    """(lat, lon, kind, display, fetched_on). Tries the split, structured query first."""
    urls, town, zp = queries(address)
    best = None
    rank = {'house number': 0, 'place': 1, 'street': 2, 'town only': 3, 'mismatch': 4}
    for u in urls:
        res, day = cache.get(u)
        if not res:
            continue
        kind = classify(res[0], address, town, zp)
        cand = (rank[kind], float(res[0]['lat']), float(res[0]['lon']), kind,
                res[0].get('display_name', ''), day)
        if best is None or cand[0] < best[0]:
            best = cand
        if kind == 'house number':
            break
    if best is None:
        return None, None, 'failed', '', cache.rows[urls[-1]]['fetched_on']
    return best[1], best[2], best[3], best[4], best[5]


def route(cache, a, b):
    url = '%s%.6f,%.6f;%.6f,%.6f?overview=false&alternatives=false' % (OSRM, a[1], a[0], b[1], b[0])
    res, day = cache.get(url)
    if res.get('code') != 'Ok' or not res.get('routes'):
        return None, day
    return res['routes'][0]['distance'] / METRES_PER_MILE, day


def haversine(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 3958.7613 * math.asin(math.sqrt(h))


def build(offline):
    cache = Cache(offline)
    olat, olon, okind, odisp, _ = geocode(cache, ORIGIN_ADDRESS)
    if okind != 'house number' or 'Lunenburg' not in odisp:
        raise SystemExit('the origin did not geocode to its house number (%s: %s) -- refusing'
                         % (okind, odisp))
    origin = (olat, olon)
    venues = collections.defaultdict(collections.Counter)
    for r in csv.DictReader(open(GAMES, encoding='utf-8')):
        if r['home_away'] == 'away' and r['address']:
            venues[re.sub(r'\s+', ' ', r['address']).strip()][r['venue']] += 1
    rows = []
    for addr in sorted(venues):
        lat, lon, kind, disp, day = geocode(cache, addr)
        row = {'venue': ' / '.join(v for v, _ in venues[addr].most_common()),
               'address': addr, 'games': sum(venues[addr].values()),
               'lat': '%.6f' % lat if lat is not None else '',
               'lon': '%.6f' % lon if lon is not None else '',
               'geocode_match': kind, 'geocode_display': disp,
               'straight_line_miles': '', 'one_way_miles': '', 'return_miles': '',
               'round_trip_miles': '', 'fetched_on': day,
               'method': ('Nominatim/OSM geocode; OSRM car route school->venue + venue->school; '
                          'origin %s' % ORIGIN_ADDRESS)}
        # ArbiterLive prints the SCHOOL'S OWN ADDRESS for a venue it has no address for --
        # Wallace Civic Center, a Fitchburg rink, appears at `1079 Massachusetts Ave, Lunenburg`.
        # A point on top of the school is therefore only a distance when every venue at it
        # IS the school; otherwise it is a placeholder, and the distance stays blank.
        if (kind in ('house number', 'street', 'place')
                and haversine(origin, (lat, lon)) < 0.2
                and any(not v.startswith(ORIGIN_NAME) for v in venues[addr])):
            kind = row['geocode_match'] = "the school's own address, printed for a venue elsewhere"
        if kind in ('house number', 'street', 'place'):
            v = (lat, lon)
            out_, d1 = route(cache, origin, v)
            back, d2 = route(cache, v, origin)
            row['straight_line_miles'] = '%.1f' % haversine(origin, v)
            if out_ is not None and back is not None:
                row['one_way_miles'] = '%.1f' % out_
                row['return_miles'] = '%.1f' % back
                row['round_trip_miles'] = '%.1f' % (out_ + back)
            else:
                row['geocode_match'] += '; route failed'
            row['fetched_on'] = max(day, d1, d2)
        rows.append(row)
    if not offline:
        cache.save()
    return rows


def render(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    try:
        rows = build(offline=a.check)
    except KeyError as e:
        print('  !! not in the cache: %s -- run without --check' % e)
        return 1
    text = render(rows)
    if a.check:
        ok = os.path.exists(OUT) and open(OUT, encoding='utf-8').read() == text
        print('%d venues; %s' % (len(rows), 'fresh' if ok else 'STALE -- run without --check'))
        return 0 if ok else 1
    tmp = OUT + '.tmp'
    open(tmp, 'w', encoding='utf-8', newline='').write(text)
    os.replace(tmp, OUT)
    c = collections.Counter(r['geocode_match'] for r in rows)
    print('%d venues: %s' % (len(rows), dict(c)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
