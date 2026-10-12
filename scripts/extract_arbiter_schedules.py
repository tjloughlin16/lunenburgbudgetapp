#!/usr/bin/env python3
"""EVERY GAME ON THE DISTRICT'S ATHLETIC SCHEDULES, FY2022-FY2027, one row each.

    python3 scripts/extract_arbiter_schedules.py           # write both CSVs
    python3 scripts/extract_arbiter_schedules.py --check   # fail if either is stale

Reads the snapshot `fetch_arbiter_schedules.py` holds (the newest in `sources/`, else the
newest in `build/arbiter/`) and writes:

  sources/data/athletics-schedules.csv           one row per schedule row ArbiterLive prints
  sources/data/athletics-schedules-coverage.csv  sport x level x school year: is it there?
  sources/data/athletics-roster-counts.csv       players per team per year, where a coach made
                                                 the roster public -- COUNTS ONLY

ROSTERS. A schedule fragment carries the team's roster when the coach made it public. No
name is kept anywhere: `fetch_arbiter_schedules.redact_rosters()` replaces each roster
table's rows with a comment holding the player count and the count per class year, and this
reads that comment (or, given an unredacted page, counts it in memory and writes no name).
`players` is rows listed on the roster as published on the fetch date -- not a count of
children who played, finished the season or paid a fee. `by_class` is grade:count, 12 =
Senior ... 9 = Freshman, 8 and 7 = middle-school grades; `other`/`blank` where the class
cell is something else or empty.

WHAT EACH COLUMN IS, AND WHICH ARE OURS.

  * `arbiter_marker` is the publisher's: `@`, `vs`, or blank (a tournament row).
  * `home_away` is that marker translated -- `vs` home, `@` away -- and NOTHING MORE.
    ArbiterLive has no neutral-site flag, so `neutral` is never asserted here; a tournament
    row, which prints no marker and no location, is `unknown`. A `vs` game at a rink in
    another town (hockey at Wallace Civic Center, Fitchburg) is HOME, as the district lists
    it, and `venue_in_lunenburg` says separately that the team still travelled.
  * `address` is the street address on the game's own page (the directions link), for `@`
    games. For any other row it is filled from another game page naming the SAME venue,
    and `address_source` says which.
  * `transport_request` is the game page's Transportation box, verbatim (usually a bus
    departure: `Lunenburg Middle High School - Departure 4:00PM`). Present only on `@`
    games' pages, because only those were fetched. Blank does not mean no bus was booked.
  * `season` is OURS: the MIAA season the sport is played in, by sport name.
  * `date` is ours too, in the sense that ArbiterLive prints `Tue Sep 7` with no year; the
    year is the school year's half the month falls in, and the printed WEEKDAY is checked
    against it -- the extract refuses to write if one disagrees.

COVERAGE. `missing` means ArbiterLive prints no row for that team in that year -- NOT that
the team played no games; the team may not have existed, or its coach may not have used
the platform. `partial` means rows exist but something says they are not the whole season,
and `basis` names which. `complete` means only that nothing so far says otherwise.
"""
import argparse
import collections
import csv
import datetime
import io
import os
import re
import statistics
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fetch_arbiter_schedules as F  # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'sources', 'data', 'athletics-schedules.csv')
COV = os.path.join(ROOT, 'sources', 'data', 'athletics-schedules-coverage.csv')
ROS = os.path.join(ROOT, 'sources', 'data', 'athletics-roster-counts.csv')

SEASON = {'Football': 'fall', 'Soccer': 'fall', 'Field Hockey': 'fall', 'Cross Country': 'fall',
          'Golf': 'fall', 'Volleyball': 'fall', 'Sideline Cheerleading': 'fall',
          'Basketball': 'winter', 'Hockey': 'winter', 'Track & Field - Indoor': 'winter',
          'Ski': 'winter', 'Baseball': 'spring', 'Softball': 'spring',
          'Lacrosse - Boys': 'spring', 'Lacrosse - Girls': 'spring',
          'Track & Field - Outdoor': 'spring'}
# The last month of each season; a season is "not over" at fetch time until it has passed.
SEASON_END = {'fall': 11, 'winter': 3, 'spring': 6}
MON = {m: i for i, m in enumerate('Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(), 1)}
DOW = 'Mon Tue Wed Thu Fri Sat Sun'.split()
NOT_PLAYED = {'Canceled', 'Cancelled', 'Postponed', 'Rainout', 'Suspended'}

FIELDS = ['fiscal_year', 'school_year', 'season', 'sport', 'level', 'date', 'end_date', 'time',
          'arbiter_marker', 'home_away', 'opponent', 'opponents_in_event', 'venue', 'facility',
          'address', 'address_source', 'venue_in_lunenburg', 'status', 'game_type', 'result',
          'transport_request', 'game_id', 'team_id', 'source_url']
COV_FIELDS = ['fiscal_year', 'school_year', 'season', 'sport', 'level', 'team_id', 'rows_listed',
              'away', 'not_played', 'with_result', 'assessment', 'basis']
ROS_FIELDS = ['fiscal_year', 'school_year', 'sport', 'level', 'team_id', 'players', 'by_class',
              'source_url', 'observed_on']


def to_date(dow, mon, day, school_year):
    y1, y2 = int(school_year[:4]), int(school_year[:2] + school_year[5:7])
    m = MON[mon]
    d = datetime.date(y1 if m >= 7 else y2, m, int(day))
    if DOW[d.weekday()] != dow:
        raise SystemExit('weekday check failed: %s %s %s in %s is a %s'
                         % (dow, mon, day, school_year, DOW[d.weekday()]))
    return d.isoformat()


def game_page(d, gid):
    """(address, transport, location_block) from a held game page, or None."""
    p = os.path.join(d, 'game-%s.html' % gid)
    if not os.path.exists(p):
        return None
    s = open(p, encoding='utf-8', errors='replace').read()
    m = re.search(r'id="directionsButton" href="[^"]*\?q=([^"]*)"', s)
    addr = F.txt(urllib.parse.unquote_plus(F.html.unescape(m.group(1)))) if m else ''
    if '(unknown)' in addr or 'Houston, TX' in addr:      # the platform's placeholder
        addr = ''
    tr = ''
    i = s.find('alt="Transportation Icon"')
    if i >= 0:
        j = s.find('Icon_Location_reskin', i)
        tr = ' | '.join(F.txt(b) for b in re.findall(
            r'<div class="pickup-dropoff">(.*?)</div>\s*</div>\s*</div>', s[i:j], flags=re.S))
    return addr, tr


def rows_from(d):
    teams = F.parse_teams(open(os.path.join(d, 'teams.html'), encoding='utf-8', errors='replace').read())
    out, per_team = [], {}
    for sport, level, tid in teams:
        for yid, sy in F.YEARS.items():
            page = open(os.path.join(d, 'schedule-%s-%s.html' % (tid, yid)),
                        encoding='utf-8', errors='replace').read()
            i, j = page.find('id="tabSchedule"'), page.find('id="tabPractice"')
            block = page[i:j]
            n = 0
            for kind, gid, body in re.findall(
                    r'<tr\s+data-(gameid|tournamentid)="(\d+)"[^>]*>(.*?)</tr>', block, flags=re.S):
                n += 1
                tds = re.findall(r'<td[^>]*>(.*?)</td>', body, flags=re.S)
                when = F.txt(tds[0])
                dm = re.findall(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun) (\w{3}) (\d+)', when)
                if not dm:
                    raise SystemExit('%s/%s row %s: no date in %r' % (tid, yid, gid, when))
                date = to_date(*dm[0], sy)
                end = to_date(*dm[-1], sy) if len(dm) > 1 else ''
                tm = re.search(r'\d{1,2}:\d{2} [AP]M', when)
                marker = F.txt(tds[1]) if kind == 'gameid' else ''
                loc = [F.txt(p) for p in re.split(r'<br\s*/?>', tds[3])]
                st = re.search(r'gamestatus (\w+)', body)
                ty = re.search(r'<abbr title="([^"]+)"', body)
                opp = F.txt(tds[2])
                multi = re.search(r' with (\d+) others?$', opp)
                res = F.txt(tds[4]) if len(tds) > 4 and kind == 'gameid' else ''
                gp = game_page(d, gid) if kind == 'gameid' else None
                url = (F.game_url(gid, tid, yid) if kind == 'gameid'
                       else '%s/Teams/Tournament/%s/%s' % (F.BASE, gid, F.ENTITY))
                out.append({
                    'fiscal_year': 'FY' + sy[:2] + sy[5:7], 'school_year': sy,
                    'season': SEASON.get(sport, ''), 'sport': sport, 'level': level,
                    'date': date, 'end_date': end, 'time': tm.group(0) if tm else '',
                    'arbiter_marker': marker,
                    'home_away': {'@': 'away', 'vs': 'home'}.get(marker, 'unknown'),
                    'opponent': opp,
                    'opponents_in_event': (int(multi.group(1)) + 1) if multi
                    else (1 if kind == 'gameid' and opp else ''),
                    'venue': loc[0] if loc else '', 'facility': ' '.join(loc[1:]).strip(),
                    'address': gp[0] if gp else '',
                    'address_source': 'game page' if gp and gp[0] else '',
                    'status': st.group(1) if st else '',
                    'game_type': ty.group(1).replace('NonLeague', 'Non-League') if ty else '',
                    'result': res,
                    'transport_request': gp[1] if gp else '',
                    'game_id': gid if kind == 'gameid' else '', 'team_id': tid,
                    'source_url': url, '_kind': kind, '_yid': yid})
            per_team[(sport, level, tid, yid)] = n
    # Fill an address from another game page naming the same venue -- and say so.
    by_venue = collections.defaultdict(collections.Counter)
    for r in out:
        if r['address_source'] == 'game page':
            by_venue[r['venue']][r['address']] += 1
    for r in out:
        if not r['address'] and r['venue'] in by_venue:
            r['address'] = by_venue[r['venue']].most_common(1)[0][0]
            r['address_source'] = 'same venue name, another game page'
        place = (r['address'] or r['venue']).lower()
        r['venue_in_lunenburg'] = ('yes' if 'lunenburg' in place
                                   else 'no' if r['address'] else 'unknown')
    out.sort(key=lambda r: (r['fiscal_year'], r['sport'], r['level'], r['date'], r['time'],
                            r['game_id'] or r['source_url']))
    return teams, out, per_team


def coverage(teams, rows, per_team, fetched):
    by = collections.defaultdict(list)
    for r in rows:
        by[(r['sport'], r['level'], r['team_id'], r['_yid'])].append(r)
    cov = []
    for sport, level, tid in teams:
        counts = [per_team[(sport, level, tid, y)] for y in F.YEARS
                  if per_team[(sport, level, tid, y)]]
        med = statistics.median(counts) if counts else 0
        for yid, sy in F.YEARS.items():
            rs = by.get((sport, level, tid, yid), [])
            n = len(rs)
            season = SEASON.get(sport, '')
            end_y = int(sy[:4]) if SEASON_END.get(season, 6) >= 7 else int(sy[:2] + sy[5:7])
            over = (end_y, SEASON_END.get(season, 6)) < (fetched.year, fetched.month)
            notp = sum(r['status'] in NOT_PLAYED for r in rs)
            basis = []
            if n == 0:
                a = 'missing'
                basis.append('no row in the source' + ('' if over else
                             '; the season had not ended at the fetch date'))
            else:
                if not over:
                    basis.append('season not over at the fetch date (%s)' % fetched.isoformat())
                if n < med / 2:
                    basis.append('%d rows, under half this team\'s median of %g' % (n, med))
                if notp * 2 > n:
                    basis.append('%d of %d rows canceled/postponed/rained out' % (notp, n))
                a = 'partial' if basis else 'complete'
                if not basis:
                    basis.append('%d rows; team median %g; nothing says otherwise' % (n, med))
            cov.append({'fiscal_year': 'FY' + sy[:2] + sy[5:7], 'school_year': sy,
                        'season': season, 'sport': sport, 'level': level, 'team_id': tid,
                        'rows_listed': n, 'away': sum(r['home_away'] == 'away' for r in rs),
                        'not_played': notp, 'with_result': sum(bool(r['result']) for r in rs),
                        'assessment': a, 'basis': '; '.join(basis)})
    cov.sort(key=lambda c: (c['sport'], c['level'], c['team_id'], c['fiscal_year']))
    return cov


def roster_rows(d, teams):
    """One row per public roster table: counts only. Never a name, by construction: the
    only things read are the redaction placeholder or, for an unredacted page, the counts
    redact_rosters() returns -- its redacted text is discarded, nothing is written."""
    log = F.read_log(d)
    out = []
    for sport, level, tid in teams:
        for yid, sy in F.YEARS.items():
            n = 'schedule-%s-%s.html' % (tid, yid)
            page = open(os.path.join(d, n), encoding='utf-8', errors='replace').read()
            found = F.roster_counts(page) + (F.redact_rosters(page)[1]
                                             if F.live_roster_rows(page) else [])
            r = log.get(n, {})
            for players, bc in found:
                out.append({'fiscal_year': 'FY' + sy[:2] + sy[5:7], 'school_year': sy,
                            'sport': sport, 'level': level, 'team_id': tid,
                            'players': players, 'by_class': bc,
                            'source_url': '%s/Teams/ScheduleForSchoolYear [POST uniqueTeamId=%s'
                                          '&schoolYearId=%s]' % (F.BASE, tid, yid),
                            'observed_on': (r.get('fetched_at') or os.path.basename(d))[:10]})
    out.sort(key=lambda r: (r['fiscal_year'], r['sport'], r['level'], r['team_id']))
    return out


def render(rows, fields):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator='\n', extrasaction='ignore')
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def build():
    d = F.snapshot_dir()
    if not d:
        raise SystemExit('no ArbiterLive snapshot held; run fetch_arbiter_schedules.py first')
    fetched = datetime.date.fromisoformat(os.path.basename(d))
    teams, rows, per_team = rows_from(d)
    # every `@` game must have yielded its page -- a join that matches nothing is not data
    nopage = [r['game_id'] for r in rows if r['arbiter_marker'] == '@'
              and not os.path.exists(os.path.join(d, 'game-%s.html' % r['game_id']))]
    if nopage:
        raise SystemExit('%d away game(s) without a held page, e.g. %s' % (len(nopage), nopage[:3]))
    cov = coverage(teams, rows, per_team, fetched)
    if sum(c['rows_listed'] for c in cov) != len(rows):
        raise SystemExit('coverage does not sum to the rows extracted')
    return d, rows, cov, roster_rows(d, teams)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    d, rows, cov, ros = build()
    want = {OUT: render(rows, FIELDS), COV: render(cov, COV_FIELDS), ROS: render(ros, ROS_FIELDS)}
    if a.check:
        stale = [p for p, t in want.items()
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != t]
        for p in stale:
            print('  !! %s is stale -- run without --check' % os.path.relpath(p, ROOT))
        print('%d rows, %d roster count(s) from %s' % (len(rows), len(ros), os.path.relpath(d, ROOT)))
        return 1 if stale else 0
    for p, t in want.items():
        tmp = p + '.tmp'
        open(tmp, 'w', encoding='utf-8', newline='').write(t)
        os.replace(tmp, p)
    c = collections.Counter(r['home_away'] for r in rows)
    a_ = collections.Counter(x['assessment'] for x in cov)
    print('%d rows (%s) from %s; coverage %s; %d public roster(s), %d players'
          % (len(rows), dict(c), os.path.relpath(d, ROOT), dict(a_), len(ros),
             sum(r['players'] for r in ros)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
