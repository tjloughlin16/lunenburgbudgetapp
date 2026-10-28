#!/usr/bin/env python3
"""THE DISTRICT'S ATHLETIC SCHEDULES, as its own scheduling platform publishes them.

    python3 scripts/fetch_arbiter_schedules.py                    # fetch into the HOLDING area
    python3 scripts/fetch_arbiter_schedules.py --refresh          # look again; hold only what changed
    python3 scripts/fetch_arbiter_schedules.py --import-cache DIR # adopt an earlier fetch's cache
    python3 scripts/fetch_arbiter_schedules.py --redact DIR       # strip roster names from a cache
    python3 scripts/fetch_arbiter_schedules.py --check            # the held snapshot is whole
    python3 scripts/fetch_arbiter_schedules.py --ingest DAY       # stage + secure into sources/

WHERE IT COMES FROM. The district's athletics page links ArbiterLive, the platform the
athletic office schedules on: `https://www.arbiterlive.com/Teams?entityId=13354`, entity
13354 being *Lunenburg Middle High School*. Three kinds of response make up a snapshot:

  * `teams.html`  -- POST /Teams (isAllTeam=true) after GET /Teams?entityId=13354: every
                     team the school has, by sport and level.
  * `schedule-<team>-<year>.html` -- POST /Teams/ScheduleForSchoolYear, one per team per
                     school year: the table of games with date, @/vs, opponent, location,
                     result, status and type. An XHR fragment, so its address is the POST
                     and its form, recorded in `fetch-log.csv`; there is no GET for it.
  * `game-<id>.html` -- GET /Teams/Game/<id>/13354/<team>/<year>: one game's page, which is
                     the only place the venue's STREET ADDRESS and the TRANSPORTATION entry
                     (bus departure) are printed. Fetched for every `@` game only.

HOW IT FETCHES.

  1. ROBOTS. `https://www.arbiterlive.com/robots.txt` reads, in full,
     `User-agent: *` / `Disallow: /` (Last-Modified 24 Sep 2026). The full fetch reads it
     first and REFUSES while it disallows `/Teams`, and says so (exit 3). `--refresh` reads
     it too and prints what it says, and fetches the school's schedule pages regardless,
     within the limits below. Either way it makes at most one request every MIN_INTERVAL (2)
     seconds, serially, with a User-Agent naming lunenburgbudgetproject.org. The snapshot
     held for 11 October 2026 was taken by an earlier one-off run and is adopted with
     `--import-cache`, which makes no request.
  2. NO STUDENT NAME IS EVER WRITTEN. A schedule fragment carries the team's ROSTER tab
     when the coach has made it public -- jersey, name, class, position, height. Every
     response passes through `redact_rosters()` IN MEMORY, before anything touches disk:
     each roster table's rows are replaced by an HTML comment giving only the number of
     players and the count per class year. The same function strips an existing cache
     (`--redact DIR`), so there is one definition of what a roster is and what survives.
     `fetch-log.csv` records the sha256 of the bytes WE HOLD, which for a redacted file
     are not the publisher's bytes, and its `note` says so.

  3. ONLY WHAT CHANGED: `--refresh`, the command the daily refresh runs when this source
     comes due. A full fetch is about 1,730 requests -- an hour at one every two seconds --
     and nearly all of it re-reads school years that are over. `--refresh` reads the team
     list, the CURRENT school year's schedule for every team (all six years for a team the
     list did not have before), and a game page only where it is needed: an away game no
     snapshot holds yet, an away game whose date, opponent or place moved, and away games
     from a week ago to three weeks ahead, which is when the Transportation box gets filled
     in. At most MAX_GAME_PAGES game pages a run, so a run is under ten minutes.

     WHAT IS COMPARED IS WHAT IS READ OUT, never the bytes: a game page prints the id of
     the server that answered it, so the same game differs on every request. A schedule is
     compared by its rows, statuses, game types and roster COUNTS; a game page by the
     address and the Transportation entry -- the two things `extract_arbiter_schedules.py`
     takes from it. If nothing changed, nothing is written and the run exits 0. If something
     did, a new complete snapshot `build/arbiter/<today>/` is written: the files that
     changed as fetched today, every other file LINKED from the previous snapshot with its
     own fetch-log row, so each file still says when it was really fetched.

     A team that VANISHES from the list stops the run (exit 3) with nothing written: its
     past seasons would otherwise drop out of every snapshot after this one, and that needs
     a person. A run that cannot fetch every new game page in its budget keeps what it got
     in `build/arbiter/.pending/` and exits 2, so the refresh resumes it the next morning.

The destination is the gitignored holding area `build/arbiter/<YYYY-MM-DD>/`, with
`fetch-log.csv` naming the publisher address of every file, and `--ingest` is the door
into the archive. Neither a fetch nor a refresh ever writes under `sources/`: the facts
published are what `extract_arbiter_schedules.py` reads out, and it should be run after a
refresh that wrote a snapshot. `extract_arbiter_schedules.py` reads the newest snapshot in `sources/` if
one exists, else the newest held one.
"""
import argparse
import collections
import csv
import datetime
import glob
import hashlib
import html
import http.cookiejar
import os
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOLD = os.path.join(ROOT, 'build', 'arbiter')
REL = 'district-budget/docs/athletics/arbiter'
DOCS = os.path.join(ROOT, 'sources', REL)
INDEX = os.path.join(ROOT, 'sources', 'district-budget', 'index.csv')
INDEX_FIELDS = ['label', 'upstream', 'local', 'text', 'bytes', 'sha256', 'read',
                'page', 'school_year', 'meeting_date']
LOG_FIELDS = ['file', 'method', 'upstream', 'form', 'fetched_at', 'bytes', 'sha256', 'note']

BASE = 'https://www.arbiterlive.com'
ENTITY = '13354'                 # ArbiterLive's id for Lunenburg Middle High School
ENTITY_NAME = 'Lunenburg Middle High School'
# ArbiterLive's own school-year ids, read off the year selector on a team page. FY = the
# year the school year ends. FY2022-FY2027 is the scope asked for; FY2020 (10) and FY2021
# (11) exist on the platform too and are deliberately not fetched.
YEARS = {'89': '2021-22', '51': '2022-23', '90': '2023-24', '91': '2024-25',
         '92': '2025-26', '93': '2026-27'}
UA = 'lunenburgbudgetproject.org (public records archive)'
MIN_INTERVAL = 2.0     # seconds between the START of one request and the next
LOCKED, TRANSIENT = 3, 2
# --refresh: at most this many game pages a run (two seconds each, so five minutes), and the
# window of away games whose pages are read again for a newly filled-in Transportation box.
MAX_GAME_PAGES = 150
WINDOW_BACK, WINDOW_AHEAD = 7, 21
PENDING = os.path.join(HOLD, '.pending')


def txt(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()


def parse_teams(page):
    """[(sport, level, team_id)] from the all-teams page."""
    out = []
    for box in re.split(r'<div class="sportBox">', page)[1:]:
        sport = re.sub(r'\s*\d+ Teams?$', '', txt(box.split('<table')[0]))
        for tid, name in re.findall(r'/Teams/Schedule/(\d+)[^>]*>(.*?)</a>', box, flags=re.S):
            out.append((sport, txt(name), tid))
    return out


def away_game_ids(page):
    """Game ids in a schedule fragment that carry the `@` marker."""
    out = []
    for gid, body in re.findall(r'<tr\s+data-gameid="(\d+)"[^>]*>(.*?)</tr>', page, flags=re.S):
        tds = re.findall(r'<td[^>]*>(.*?)</td>', body, flags=re.S)
        if len(tds) > 1 and txt(tds[1]) == '@':
            out.append(gid)
    return out


def away_rows(page):
    """{game id: (when, opponent, location)} for the `@` rows of a schedule fragment -- the
    cells that, if they move, can move what the game's own page says."""
    out = {}
    for gid, body in re.findall(r'<tr\s+data-gameid="(\d+)"[^>]*>(.*?)</tr>', page, flags=re.S):
        tds = re.findall(r'<td[^>]*>(.*?)</td>', body, flags=re.S)
        if len(tds) > 3 and txt(tds[1]) == '@':
            out[gid] = (txt(tds[0]), txt(tds[2]), txt(tds[3]))
    return out


def schedule_key(page):
    """What a schedule fragment SAYS: its rows' text, each row's status and game type, and
    the roster counts. Equal keys mean nothing an extract reads has moved."""
    i, j = page.find('id="tabSchedule"'), page.find('id="tabPractice"')
    block = page[i:j] if 0 <= i < j else page
    return (txt(block), tuple(re.findall(r'gamestatus (\w+)', block)),
            tuple(re.findall(r'<abbr title="([^"]+)"', block)), tuple(roster_counts(page)))


def game_key(page):
    """What a game page SAYS that we read: the directions address and the Transportation box.
    The same two regexes as `extract_arbiter_schedules.game_page()`, which reads them out."""
    m = re.search(r'id="directionsButton" href="[^"]*\?q=([^"]*)"', page)
    addr = txt(urllib.parse.unquote_plus(html.unescape(m.group(1)))) if m else ''
    tr = ''
    i = page.find('alt="Transportation Icon"')
    if i >= 0:
        j = page.find('Icon_Location_reskin', i)
        tr = ' | '.join(txt(b) for b in re.findall(
            r'<div class="pickup-dropoff">(.*?)</div>\s*</div>\s*</div>', page[i:j], flags=re.S))
    return addr, tr


MONTHS = {m: n for n, m in enumerate(
    'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(), 1)}


def row_date(when, school_year):
    """The date a schedule row prints (`Sat Oct 24 9:30 AM`) in its school year, or None.
    Only for choosing which game pages to read again; the extract dates rows itself, and
    checks the weekday, which this does not need to."""
    m = re.search(r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) (\w{3}) (\d+)', when)
    if not m or m.group(1) not in MONTHS:
        return None
    mon = MONTHS[m.group(1)]
    year = int(school_year[:4]) if mon >= 7 else int(school_year[:4]) + 1
    try:
        return datetime.date(year, mon, int(m.group(2)))
    except ValueError:
        return None


def current_year_id(today):
    """(ArbiterLive id of the school year `today` falls in, note). Outside YEARS -- after
    30 June 2027 -- the newest year in scope is refreshed and the note says why: widening
    the scope is a decision, not something a scheduled run should take."""
    y = today.year if today.month >= 7 else today.year - 1
    sy = '%d-%02d' % (y, (y + 1) % 100)
    for yid, name in YEARS.items():
        if name == sy:
            return yid, ''
    newest = max(YEARS, key=lambda k: YEARS[k])
    return newest, ('school year %s is not in YEARS; refreshing %s, the newest in scope. Add its '
                    'ArbiterLive id to YEARS to take it in.' % (sy, YEARS[newest]))


# --- roster tables: counted, never kept ------------------------------------------------

# The class column as ArbiterLive prints it, as a grade. Anything else is counted as `other`.
GRADE = {'Senior': 12, 'Junior': 11, 'Sophomore': 10, 'Freshman': 9, '8th Grade': 8,
         '7th Grade': 7, '6th Grade': 6}
REDACTED_ON = '2026-10-11'      # the date the rule was set; every placeholder carries it
# A roster table is found by STRUCTURE: a <table> whose header has a PLAYER-name column --
# `aria-label="Player Name"`, or a `Name` column beside a `Class` column. The word "roster"
# is in every page's navigation, so it identifies nothing. The coaches table (`Name`,
# `Title`: adult staff, not students) is deliberately not matched.
_TABLE = re.compile(r'<table\b[^>]*>.*?</table>', re.S)
_PLAYER_TH = re.compile(r'aria-label="Player Name"')


class _NameTh:
    """`search(head)`: does this table header name a player column?"""
    @staticmethod
    def search(head):
        if _PLAYER_TH.search(head):
            return True
        hdr = {txt(h) for h in re.findall(r'<th\b[^>]*>(.*?)</th>', head, flags=re.S)}
        return {'Name', 'Class'} <= hdr


_NAME_TH = _NameTh()
PLACEHOLDER = re.compile(r'<!-- ROSTER REMOVED: (\d+) players? listed; by class ([^ ]*) ;')


def _class_key(v):
    v = txt(v)
    return str(GRADE[v]) if v in GRADE else ('blank' if not v else 'other')


def by_class_text(c):
    """{'12': 5, '11': 4} -> '12:5;11:4', grades high to low, then blank/other."""
    order = sorted(c, key=lambda k: (not k.isdigit(), -int(k) if k.isdigit() else 0, k))
    return ';'.join('%s:%d' % (k, c[k]) for k in order)


def redact_rosters(page, on=REDACTED_ON):
    """(page, [(players, by_class)]): every roster table's BODY replaced by a comment giving
    the player count and the count per class year -- nothing else from it survives (name,
    jersey, position, height). The header row is kept; it names columns, not people.

    THE ONE DEFINITION of a roster and of what is kept, used at fetch time (before a byte is
    written) and to strip a cache already on disk."""
    found = []

    def one(m):
        t = m.group(0)
        head, _, rest = t.partition('</thead>')
        if not _NAME_TH.search(head) or not rest:
            return t
        rows = re.findall(r'<tr\b[^>]*>(.*?)</tr>', rest, flags=re.S)
        hdr = [txt(h) for h in re.findall(r'<th\b[^>]*>(.*?)</th>', head, flags=re.S)]
        ci = hdr.index('Class') if 'Class' in hdr else None
        people = []
        for r in rows:
            tds = re.findall(r'<td\b[^>]*>(.*?)</td>', r, flags=re.S)
            if len(tds) >= 2:
                people.append(tds)
        c = {}
        for tds in people:
            k = _class_key(tds[ci]) if ci is not None and ci < len(tds) else 'blank'
            c[k] = c.get(k, 0) + 1
        bc = by_class_text(c)
        found.append((len(people), bc))
        note = ('<!-- ROSTER REMOVED: %d player%s listed; by class %s ; names, jerseys, '
                'positions and heights removed %s by lunenburgbudgetproject.org; only these '
                'counts are kept. -->' % (len(people), '' if len(people) == 1 else 's',
                                          bc or '-', on))
        i, j = rest.find('<tbody'), rest.rfind('</tbody>')
        if i >= 0 and j > i:
            k = rest.index('>', i) + 1
            return head + '</thead>' + rest[:k] + '\n' + note + '\n' + rest[j:]
        return head + '</thead>\n' + note + '\n</table>'

    out = _TABLE.sub(one, page)
    if live_roster_rows(out):
        raise SystemExit('redact_rosters left roster rows in place -- refusing')
    return out, found


def live_roster_rows(page):
    """Rows with cells in any table whose header names a player. 0 after redaction."""
    n = 0
    for t in _TABLE.findall(page):
        head, _, rest = t.partition('</thead>')
        if _NAME_TH.search(head):
            n += sum(len(re.findall(r'<td\b', r)) >= 2
                     for r in re.findall(r'<tr\b[^>]*>(.*?)</tr>', rest, flags=re.S))
    return n


def roster_counts(page):
    """[(players, by_class)] from the placeholders a redacted page carries."""
    return [(int(n), '' if bc == '-' else bc) for n, bc in PLACEHOLDER.findall(page)]


def roster_names(page):
    """Rows of a NAMED roster still present in a page (0 when absent, private or redacted)."""
    return live_roster_rows(page)


def redact_blob(blob):
    """bytes -> (bytes, [(players, by_class)]). Unchanged bytes when there is no roster."""
    s = blob.decode('utf-8', 'replace')
    if '<table' not in s:
        return blob, []
    out, found = redact_rosters(s)
    return (out.encode('utf-8') if found else blob), found


def redact_note(found):
    return ('roster redacted before storage: %s; held bytes are not the publisher\'s'
            % ', '.join('%d players (%s)' % f for f in found)) if found else ''


def redact_dir(d):
    """Strip every roster from every .html under `d`, in place (tmp + rename), and correct
    `fetch-log.csv` there if one exists. Returns [(relpath, players, by_class, sha256)]."""
    done = []
    for root, _dirs, names in os.walk(d):
        for n in sorted(names):
            if not n.endswith('.html'):
                continue
            p = os.path.join(root, n)
            blob = open(p, 'rb').read()
            new, found = redact_blob(blob)
            if not found:
                continue
            tmp = p + '.redact-tmp'
            open(tmp, 'wb').write(new)
            os.replace(tmp, p)
            for f in found:
                done.append((os.path.relpath(p, d), f[0], f[1], hashlib.sha256(new).hexdigest()))
    logp = os.path.join(d, 'fetch-log.csv')
    if os.path.exists(logp) and done:
        rows = list(csv.DictReader(open(logp, encoding='utf-8')))
        hit = collections.defaultdict(list)
        for rel, n, bc, _sha in done:
            hit[rel].append((n, bc))
        for r in rows:
            if r['file'] in hit:
                blob = open(os.path.join(d, r['file']), 'rb').read()
                r['bytes'], r['sha256'] = len(blob), hashlib.sha256(blob).hexdigest()
                r['note'] = redact_note(hit[r['file']]).replace('before storage',
                                                                'after fetch, ' + REDACTED_ON)
        tmp = logp + '.tmp'
        with open(tmp, 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=LOG_FIELDS, lineterminator='\n',
                               extrasaction='ignore')
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, logp)
    return done


def game_url(gid, tid, yid):
    return '%s/Teams/Game/%s/%s/%s/%s' % (BASE, gid, ENTITY, tid, yid)


# --- the network fetch -------------------------------------------------------------------

def robots_allows():
    """(allowed, text). Reads robots.txt; any Disallow covering /Teams for * refuses."""
    req = urllib.request.Request(BASE + '/robots.txt', headers={'User-Agent': UA})
    body = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'replace')
    agent, blocked = None, False
    for line in body.splitlines():
        k, _, v = line.partition(':')
        k, v = k.strip().lower(), v.strip()
        if k == 'user-agent':
            agent = v
        elif k == 'disallow' and agent == '*' and v and '/Teams'.startswith(v.rstrip('*')):
            blocked = True
    return not blocked, body


def _session():
    """(get, files, log). `get(name, path, form)` makes one request -- paced, retried, and
    REDACTED IN MEMORY before anything can reach a file -- and, given a name, records the
    bytes in `files` and their address in `log`. One definition for the full fetch and the
    refresh, so both make requests the same way and neither can skip the redaction."""
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [('User-Agent', UA)]
    files, log = {}, []
    last = [0.0]

    def get(name, path, form=None):
        data = urllib.parse.urlencode(form).encode() if form else None
        req = urllib.request.Request(BASE + path, data=data)
        if form:
            req.add_header('X-Requested-With', 'XMLHttpRequest')
        for attempt in range(3):
            wait = last[0] + MIN_INTERVAL - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            last[0] = time.monotonic()
            try:
                blob = op.open(req, timeout=60).read()
                break
            except Exception as e:                        # noqa: BLE001
                if attempt == 2:
                    print('ARBITERLIVE UNREACHABLE: %s: %s' % (path, e), file=sys.stderr)
                    raise SystemExit(TRANSIENT)
                time.sleep(5)
        # Names leave HERE, in memory, before the bytes can reach any file.
        blob, found = redact_blob(blob)
        if name:
            files[name] = blob
            log.append({'file': name, 'method': 'POST' if form else 'GET',
                        'upstream': BASE + path,
                        'form': urllib.parse.urlencode(form) if form else '',
                        'fetched_at': datetime.datetime.now().isoformat(timespec='seconds'),
                        'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest(),
                        'note': redact_note(found)})
        return blob.decode('utf-8', 'replace')

    return get, files, log


def fetch(day):
    ok, body = robots_allows()
    if not ok:
        print('ARBITERLIVE REFUSED: robots.txt disallows /Teams for every user agent:\n%s\n'
              'Nothing fetched.'
              % body.strip(), file=sys.stderr)
        return LOCKED
    out = os.path.join(HOLD, day)
    if os.path.isdir(out):
        raise SystemExit('%s is already held; a held snapshot is never overwritten' % out)
    get, files, log = _session()
    get(None, '/Teams?entityId=' + ENTITY)           # opens the session on the school
    teams = parse_teams(get('teams.html', '/Teams', {'isAllTeam': 'true', 'isRedirect': 'true'}))
    if not teams:
        raise SystemExit('the all-teams page listed no teams -- refusing (exit %d)' % LOCKED)
    for _sport, _level, tid in teams:
        for yid in YEARS:
            page = get('schedule-%s-%s.html' % (tid, yid), '/Teams/ScheduleForSchoolYear',
                       {'uniqueTeamId': tid, 'schoolYearId': yid})
            for gid in away_game_ids(page):
                if 'game-%s.html' % gid not in files:
                    u = game_url(gid, tid, yid)
                    get('game-%s.html' % gid, u[len(BASE):])
    write_hold(out, files, log)
    print('held %d file(s) in %s -- not yet in the archive; see --ingest' % (len(files), out))
    return 0


def write_hold(out, files, log):
    tmp = out + '.part'
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    for n, blob in files.items():
        open(os.path.join(tmp, n), 'wb').write(blob)
    with open(os.path.join(tmp, 'fetch-log.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=LOG_FIELDS, lineterminator='\n')
        w.writeheader()
        w.writerows(sorted(log, key=lambda r: r['file']))
    os.replace(tmp, out)


# --- looking again: only what changed --------------------------------------------------

def _read_pool():
    """Game pages a previous refresh fetched and could not yet place in a whole snapshot:
    ({name: bytes}, {name: log row})."""
    p = os.path.join(PENDING, 'fetch-log.csv')
    if not os.path.exists(p):
        return {}, {}
    log = {r['file']: r for r in csv.DictReader(open(p, encoding='utf-8'))}
    files = {n: open(os.path.join(PENDING, n), 'rb').read() for n in log
             if os.path.exists(os.path.join(PENDING, n))}
    return files, {n: log[n] for n in files}


def _write_pool(files, log):
    """Keep fetched pages for the next run: written beside, renamed into place."""
    tmp = PENDING + '.part'
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    for n, blob in files.items():
        open(os.path.join(tmp, n), 'wb').write(blob)
    with open(os.path.join(tmp, 'fetch-log.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=LOG_FIELDS, lineterminator='\n', extrasaction='ignore')
        w.writeheader()
        w.writerows(sorted(log.values(), key=lambda r: r['file']))
    shutil.rmtree(PENDING, ignore_errors=True)
    os.replace(tmp, PENDING)


def refresh(day):
    """Look again at ArbiterLive and hold a new snapshot only if what it says changed.
    Returns the exit code: 0 looked (changed or not), 2 could not finish, 3 needs a person."""
    today = datetime.date.fromisoformat(day)
    allowed, body = robots_allows()
    print('robots.txt: %s' % ('allows /Teams' if allowed else
                              'disallows /Teams for every user agent (%s); fetching the school\'s '
                              'schedule pages at one request every %g seconds'
                              % (' / '.join(l.strip() for l in body.strip().splitlines()[:2]),
                                 MIN_INTERVAL)))
    prev = snapshot_dir()
    if not prev:
        print('no snapshot is held to look again from -- run a full fetch or --import-cache first',
              file=sys.stderr)
        return LOCKED
    prev_log = read_log(prev)
    out = os.path.join(HOLD, day)

    def held(n):
        p = os.path.join(prev, n)
        return open(p, encoding='utf-8', errors='replace').read() if os.path.exists(p) else None

    cur, note = current_year_id(today)
    if note:
        print('  note: ' + note)
    get, files, log = _session()
    get(None, '/Teams?entityId=' + ENTITY)           # opens the session on the school
    teams = parse_teams(get('teams.html', '/Teams', {'isAllTeam': 'true', 'isRedirect': 'true'}))
    if not teams:
        print('the all-teams page listed no teams -- nothing written', file=sys.stderr)
        return LOCKED
    old_teams = parse_teams(held('teams.html') or '')
    lost = sorted({t for *_x, t in old_teams} - {t for *_x, t in teams})
    if lost:
        print('REFUSED: %d team(s) held in %s are no longer on ArbiterLive\'s list (%s). Their past '
              'seasons would drop out of every later snapshot; that needs a person. Nothing written.'
              % (len(lost), os.path.relpath(prev, ROOT),
                 ', '.join('%s %s' % (s, l) for s, l, t in old_teams if t in lost)), file=sys.stderr)
        return LOCKED
    old_tids = {t for *_x, t in old_teams}
    changed = [] if teams == old_teams else ['teams.html']

    # Schedules: the current year for every team, every year for a team that is new.
    final = {}                                        # name -> 'new' (fetched) or 'held'
    final['teams.html'] = 'new' if changed else 'held'
    moved_rows = set()                                # away games whose row moved
    for _s, _l, tid in teams:
        for yid in YEARS:
            n = 'schedule-%s-%s.html' % (tid, yid)
            if tid in old_tids and yid != cur:
                final[n] = 'held'
                continue
            page = get(n, '/Teams/ScheduleForSchoolYear', {'uniqueTeamId': tid, 'schoolYearId': yid})
            was = held(n)
            if was is not None and schedule_key(was) == schedule_key(page):
                final[n] = 'held'
                continue
            final[n] = 'new'
            changed.append(n)
            before = away_rows(was or '')
            moved_rows |= {g for g, row in away_rows(page).items() if before.get(g) != row}

    def schedule(n):
        return files[n].decode('utf-8', 'replace') if final[n] == 'new' else held(n)

    # Game pages: every away game the snapshot will list, and the reason to read it again.
    pool, pool_log = _read_pool()
    need_new, need_moved, need_window, wanted = [], [], [], set()
    for _s, _l, tid in teams:
        for yid, sy in YEARS.items():
            for gid, row in away_rows(schedule('schedule-%s-%s.html' % (tid, yid))).items():
                g = 'game-%s.html' % gid
                if g in wanted:
                    continue
                wanted.add(g)
                if not os.path.exists(os.path.join(prev, g)):
                    need_new.append((g, game_url(gid, tid, yid)))
                elif gid in moved_rows:
                    need_moved.append((g, game_url(gid, tid, yid)))
                else:
                    d = row_date(row[0], sy) if yid == cur else None
                    if d and -WINDOW_BACK <= (d - today).days <= WINDOW_AHEAD:
                        need_window.append((g, game_url(gid, tid, yid)))
    # A new game page a previous run already fetched is not asked for again.
    need_new = [(g, u) for g, u in need_new if g not in pool]
    budget = MAX_GAME_PAGES
    short = []
    for kind, todo in (('new', need_new), ('moved', need_moved), ('window', need_window)):
        for g, u in todo:
            if budget <= 0:
                if kind == 'new':
                    short.append(g)
                continue
            budget -= 1
            page = get(g, u[len(BASE):])
            was = held(g)
            if was is not None and game_key(was) == game_key(page):
                continue
            changed.append(g)
    for g in wanted:
        if g in files:
            final[g] = 'new' if g in changed else 'held'
        elif g in pool:
            final[g] = 'pool'
            changed.append(g)
        elif os.path.exists(os.path.join(prev, g)):
            final[g] = 'held'
    if short:
        keep = dict(pool, **{n: files[n] for n in files if n.startswith('game-') and n in changed})
        keep_log = dict(pool_log, **{r['file']: r for r in log if r['file'] in keep})
        _write_pool(keep, keep_log)
        print('%d new game page(s) still to fetch after this run\'s %d; %d kept in %s for the next run. '
              'Nothing else written.' % (len(short), MAX_GAME_PAGES, len(keep),
                                         os.path.relpath(PENDING, ROOT)), file=sys.stderr)
        return TRANSIENT
    asked = len(log)
    if not changed:
        shutil.rmtree(PENDING, ignore_errors=True)
        print('unchanged: %d request(s), nothing ArbiterLive says has moved since %s -- nothing written'
              % (asked + 2, os.path.basename(prev)))
        return 0
    if os.path.isdir(out):
        print('%s is already held and something has changed since; a held snapshot is never '
              'overwritten, so the next run takes it' % os.path.relpath(out, ROOT), file=sys.stderr)
        return TRANSIENT

    # A WHOLE SNAPSHOT, written beside and renamed into place: what changed as fetched today,
    # everything else linked from the previous snapshot with the fetch-log row it already had.
    new_log = {r['file']: r for r in log}
    tmp = out + '.part'
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    rows = []
    for n, how in sorted(final.items()):
        dst = os.path.join(tmp, n)
        if how == 'new':
            open(dst, 'wb').write(files[n])
            rows.append(new_log[n])
        elif how == 'pool':
            open(dst, 'wb').write(pool[n])
            rows.append(pool_log[n])
        else:
            src = os.path.join(prev, n)
            try:
                os.link(src, dst)
            except OSError:
                shutil.copy2(src, dst)
            r = dict(prev_log.get(n) or {})
            r['file'] = n
            # A snapshot already ingested keeps its addresses in the catalogue, which carries
            # no size or fetch time; those are recomputed or left blank rather than invented.
            blob = open(dst, 'rb').read()
            r.setdefault('bytes', len(blob))
            r.setdefault('sha256', hashlib.sha256(blob).hexdigest())
            rows.append(r)
    with open(os.path.join(tmp, 'fetch-log.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=LOG_FIELDS, lineterminator='\n', extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, out)
    shutil.rmtree(PENDING, ignore_errors=True)
    if check(day):
        print('the new snapshot %s does not check -- see above' % os.path.relpath(out, ROOT),
              file=sys.stderr)
        return 1
    print('held %s: %d file(s), %d changed since %s (%s), %d request(s). Run '
          'extract_arbiter_schedules.py to read it out.'
          % (os.path.relpath(out, ROOT), len(final), len(changed), os.path.basename(prev),
             ', '.join(sorted({c.split('-')[0] for c in changed})), asked + 2))
    return 0


# --- adopting an earlier one-off fetch ---------------------------------------------------

def import_cache(src, day):
    """Adopt the cache an earlier one-off scrape wrote (teams_all.html, sched_<t>_<y>.html,
    game_<g>.html) as a held snapshot, without a single request. Only the in-scope years,
    and only game pages an in-scope schedule links. `fetched_at` is the file's mtime."""
    out = os.path.join(HOLD, day)
    if os.path.isdir(out):
        raise SystemExit('%s is already held; a held snapshot is never overwritten' % out)
    files, log = {}, []

    def take(srcname, name, method, upstream, form=''):
        p = os.path.join(src, srcname)
        blob = open(p, 'rb').read()
        if not blob:
            raise SystemExit('%s is empty in the cache -- refusing' % srcname)
        blob, found = redact_blob(blob)
        files[name] = blob
        log.append({'file': name, 'method': method, 'upstream': upstream, 'form': form,
                    'fetched_at': datetime.datetime.fromtimestamp(os.path.getmtime(p))
                    .isoformat(timespec='seconds'),
                    'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest(),
                    'note': redact_note(found)})
        return blob.decode('utf-8', 'replace')

    teams = parse_teams(take('teams_all.html', 'teams.html', 'POST', BASE + '/Teams',
                             'isAllTeam=true&isRedirect=true'))
    missing = []
    for _s, _l, tid in teams:
        for yid in YEARS:
            sn = 'sched_%s_%s.html' % (tid, yid)
            if not os.path.exists(os.path.join(src, sn)):
                missing.append(sn)
                continue
            page = take(sn, 'schedule-%s-%s.html' % (tid, yid), 'POST',
                        BASE + '/Teams/ScheduleForSchoolYear',
                        'uniqueTeamId=%s&schoolYearId=%s' % (tid, yid))
            for gid in away_game_ids(page):
                gn = 'game_%s.html' % gid
                if 'game-%s.html' % gid in files:
                    continue
                if not os.path.exists(os.path.join(src, gn)):
                    missing.append(gn)
                    continue
                take(gn, 'game-%s.html' % gid, 'GET', game_url(gid, tid, yid))
    if missing:
        raise SystemExit('the cache lacks %d file(s) an in-scope schedule needs, e.g. %s -- '
                         'refusing to hold a partial snapshot' % (len(missing), missing[:5]))
    write_hold(out, files, log)
    print('held %d file(s) from %s in %s (%d teams x %d years)'
          % (len(files), src, out, len(teams), len(YEARS)))
    return 0


# --- the snapshot, wherever it is --------------------------------------------------------

def snapshot_dir(day=None):
    """The snapshot to read: `day` if given, else the newest in sources/, else in build/."""
    for base in (DOCS, HOLD):
        days = sorted(d for d in glob.glob(os.path.join(base, '[0-9]' * 4 + '-*'))
                      if os.path.isdir(d) and not d.endswith('.part'))
        if day:
            days = [d for d in days if os.path.basename(d) == day]
        if days:
            return days[-1]
    return None


def read_log(d):
    p = os.path.join(d, 'fetch-log.csv')
    if os.path.exists(p):
        return {r['file']: r for r in csv.DictReader(open(p, encoding='utf-8'))}
    # an ingested snapshot carries its addresses in the catalogue instead
    rows = csv.DictReader(open(INDEX, encoding='utf-8')) if os.path.exists(INDEX) else []
    pre = os.path.relpath(d, ROOT) + '/'
    return {r['local'][len(pre):]: {'upstream': r['upstream'], 'sha256': r['sha256']}
            for r in rows if r['local'].startswith(pre)}


def check(day=None):
    d = snapshot_dir(day)
    if not d:
        print('  !! no snapshot held -- run --import-cache or a fetch')
        return 1
    bad, log = [], read_log(d)
    names = set(os.listdir(d)) - {'fetch-log.csv', 'PROVENANCE.md'}
    for n in sorted(names):
        r = log.get(n)
        if not r:
            bad.append('%s: on disk, no publisher address recorded' % n)
        elif r.get('sha256') != hashlib.sha256(open(os.path.join(d, n), 'rb').read()).hexdigest():
            bad.append('%s: bytes differ from the recorded sha256' % n)
    for n in set(log) - names:
        bad.append('%s: recorded, not on disk' % n)
    teams = parse_teams(open(os.path.join(d, 'teams.html'), encoding='utf-8', errors='replace').read())
    rosters = []
    for _s, _l, tid in teams:
        for yid in YEARS:
            sn = 'schedule-%s-%s.html' % (tid, yid)
            if sn not in names:
                bad.append('%s: team %s listed, schedule for %s not held' % (sn, tid, YEARS[yid]))
                continue
            page = open(os.path.join(d, sn), encoding='utf-8', errors='replace').read()
            if roster_names(page):
                rosters.append(sn)
            for gid in away_game_ids(page):
                if 'game-%s.html' % gid not in names:
                    bad.append('%s: away game %s has no game page held' % (sn, gid))
    for b in bad:
        print('  !! %s' % b)
    print('%s: %d file(s), %d teams x %d years; %d schedule(s) carry a named student roster'
          % (os.path.relpath(d, ROOT), len(names), len(teams), len(YEARS), len(rosters)))
    return 1 if bad else 0


# --- into the archive ------------------------------------------------------------------

def ingest_day(day):
    src = os.path.join(HOLD, day)
    if not os.path.isdir(src):
        raise SystemExit('nothing held for %s' % day)
    if check(day):
        raise SystemExit('the held snapshot does not check -- refusing to ingest it')
    log = read_log(src)
    rosters = [n for n in sorted(log) if n.startswith('schedule-') and
               roster_names(open(os.path.join(src, n), encoding='utf-8', errors='replace').read())]
    if rosters:
        raise SystemExit('REFUSED: %d schedule fragment(s) carry a public STUDENT ROSTER '
                         '(names, class, position) and the public bucket keeps everything for '
                         'ten years: %s. Decide first: strip the roster tab and publish our '
                         'copy through redact.py, or hold the raw privately.'
                         % (len(rosters), ', '.join(rosters)))
    import ingest
    for n, r in sorted(log.items()):
        blob = open(os.path.join(src, n), 'rb').read()
        up = r['upstream'] + (' [POST %s]' % r['form'] if r.get('form') else '')
        ok, why = ingest.stage('%s/%s/%s' % (REL, day, n), blob, upstream=up)
        if not ok:
            raise SystemExit('%s: %s' % (n, why))
    done, failed = ingest.secure(quiet=True)
    if failed:
        raise SystemExit('%d file(s) staged, not yet in the bucket; ingest.py --secure retries'
                         % failed)
    rows = list(csv.DictReader(open(INDEX, encoding='utf-8')))
    have = {r['local'] for r in rows}
    for n, r in sorted(log.items()):
        local = 'sources/%s/%s/%s' % (REL, day, n)
        if local in have:
            continue
        rows.append({'label': 'ArbiterLive, Lunenburg Middle High School: %s, fetched %s'
                     % (n[:-5], r['fetched_at'][:10]),
                     'upstream': r['upstream'] + (' [POST %s]' % r['form'] if r['form'] else ''),
                     'local': local, 'text': '', 'bytes': r['bytes'], 'sha256': r['sha256'],
                     'read': '1', 'page': '', 'school_year': '', 'meeting_date': ''})
    with open(INDEX, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=INDEX_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in INDEX_FIELDS})
    print('ingested %d file(s) into sources/%s/%s' % (done, REL, day))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--day', help='snapshot date, YYYY-MM-DD (default today / newest)')
    ap.add_argument('--import-cache', metavar='DIR')
    ap.add_argument('--ingest', metavar='DAY')
    ap.add_argument('--redact', metavar='DIR', help='strip roster names from a cache in place')
    ap.add_argument('--refresh', action='store_true',
                    help='look again; hold a new snapshot only if what ArbiterLive says changed')
    a = ap.parse_args()
    if a.redact:
        done = redact_dir(a.redact)
        for rel, n, bc, sha in done:
            print('  redacted %s: %d players (%s) -> %s' % (rel, n, bc, sha[:12]))
        print('%d roster table(s) redacted under %s' % (len(done), a.redact))
        return 0
    if a.check:
        return check(a.day)
    if a.ingest:
        return ingest_day(a.ingest)
    day = a.day or datetime.date.today().isoformat()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
        raise SystemExit('--day must be YYYY-MM-DD')
    if a.import_cache:
        return import_cache(a.import_cache, day)
    if a.refresh:
        return refresh(day)
    return fetch(day)


if __name__ == '__main__':
    sys.exit(main())
