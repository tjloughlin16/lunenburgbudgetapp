#!/usr/bin/env python3
"""THE INGESTION DASHBOARD: what is running, what is queued, what is left.

    python3 scripts/build_ingest_status.py            # write it once
    python3 scripts/build_ingest_status.py --watch    # ...and keep it fresh every 20s
    python3 scripts/build_ingest_status.py --open     # ...and open it

WHY. TJ, 19 September 2026: "I have to keep asking you and I'd prefer to just open that
to see what is going on." Every fact on this page was already somewhere -- a registry, a
log, a process list -- and the only way to read it was to ask somebody to run four
commands and reconcile the answers. That reconciliation is exactly where I got it wrong
in conversation the same morning, quoting 478, then 963, then 840 for one quantity,
because three registries answer three slightly different questions and nothing put them
side by side.

So this page has one job: **one number per stream, derived the same way every time.**

WHERE IT LIVES, AND WHY NOT ON THE SITE. `build/status/`, local, gitignored, opened as a
file. It reads the state of THIS machine -- which processes are alive, what today's
refresh log says -- and none of that is true for anybody else or worth publishing. The
public site answers what the town spends; this answers whether the pipeline is awake.

NO SERVER. The page is a file with the data inlined, and it meta-refreshes. `--watch`
rewrites it every twenty seconds, so an open tab keeps up without anything listening on a
port. The document table is a separate `sources.js` loaded with a <script> tag, because
`fetch()` of a local file is blocked by the browser and a <script> tag is not.
"""
import argparse, collections, csv, datetime as dt, glob, html, json, os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
OUT  = os.path.join(ROOT, 'build', 'status')
TREE = os.path.join(os.path.dirname(ROOT), 'lunenburgbudgets-refresh')

def rows(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p): return []
    with open(p, encoding='utf-8', errors='replace') as fh:
        return list(csv.DictReader(fh))

def ago(ts):
    """A timestamp as '3m ago'. Takes anything ISO-ish."""
    if not ts: return ''
    try:
        s = ts.replace('Z', '+00:00')
        d = dt.datetime.fromisoformat(s)
        if d.tzinfo is None: d = d.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return ts
    n = (dt.datetime.now(dt.timezone.utc) - d).total_seconds()
    if n < 60: return '%ds ago' % int(n)
    if n < 3600: return '%dm ago' % int(n / 60)
    if n < 86400: return '%dh ago' % int(n / 3600)
    return '%dd ago' % int(n / 86400)

# ---------------------------------------------------------------- what is alive
# EVERY PATTERN IS BRACKETED. `pgrep -f "sweep_backlog"` matches the shell running the
# pgrep, so a naive check reports itself as a running job -- the self-matching pattern
# CLAUDE.md warns about, which has cost this project a session's coordination twice.
# `[s]weep_backlog` cannot match its own argv.
WATCHED = [
    ('YouTube captions',   r'[f]etch_youtube_transcripts\.py',  'fetching machine captions from the channel'),
    ('Caption backfill',   r'[r]un_transcript_backfill\.sh',    'the wrapper: newest first, backs off when YouTube refuses'),
    ('OCR of scans',       r'[o]cr_scanned_minutes\.py|[o]cr_pdf', 'macOS Vision reading image-only PDFs — local and free'),
    ('Daily refresh',      r'[r]efresh\.py|[d]aily_refresh\.sh', 'the 7am run: watch the town, fetch what is new, rebuild'),
    ('Our minutes',        r'[w]rite_recording_minutes\.py',    'claude -p writing minutes from a transcript — COSTS ALLOWANCE'),
    ('Votes',              r'[e]xtract_official_votes\.py',     'claude -p reading votes out of the town’s minutes — COSTS ALLOWANCE'),
    ('Backlog sweep',      r'[s]weep_backlog\.py',              'the pre-reset sweep — COSTS ALLOWANCE'),
    ('Text extraction',    r'[e]xtract_minutes\.py',            'pulling text out of newly fetched PDFs'),
    ('Site build',         r'[v]ite build|[p]rerender\.mjs',    'building the 332 routes'),
    ('Archive sync',       r'[s]ync_archive\.py',               'hashing or pushing documents to R2'),
]

def running():
    out = []
    for name, pat, what in WATCHED:
        try:
            r = subprocess.run(['pgrep', '-f', pat], capture_output=True, text=True)
            pids = [p for p in r.stdout.split() if p]
        except Exception:
            pids = []
        if not pids: continue
        el, cmd = '', ''
        try:
            p = subprocess.run(['ps', '-o', 'etime=,command=', '-p', pids[0]],
                               capture_output=True, text=True).stdout.strip()
            el = p.split()[0] if p else ''
            cmd = ' '.join(p.split()[1:])[:200]
        except Exception:
            pass
        out.append(dict(name=name, what=what, n=len(pids), elapsed=el, cmd=cmd,
                        costs='COSTS ALLOWANCE' in what))
    return out


def group(items):
    """A pending list as one row per board: how many, and the span they cover.

    TJ, 19 September 2026: "I want to know details in a collapsible way ... '940 videos'
    with a breakdown of the dates and boards." A total is a number to worry about; a
    total broken out by board and date is a plan. It also makes the shape of a backlog
    legible -- the caption gap is not spread evenly, it is the land-use boards before
    2022, which is a different fact from 'we are behind'.

    items: (board, date) pairs.
    """
    by = collections.defaultdict(list)
    for b, d in items:
        by[b].append(d)
    out = []
    for b, ds in by.items():
        ds = sorted(x for x in ds if x)
        out.append(dict(board=b, n=len(by[b]), first=ds[0] if ds else '',
                        last=ds[-1] if ds else '', dates=ds))
    return sorted(out, key=lambda r: -r['n'])


def caption_pending():
    """Videos classified to a board and date whose captions we do not hold."""
    have = {r['video_id'] for r in rows('youtube-transcript-index.csv')}
    dead = {r['video_id'] for r in rows('youtube-no-captions.csv')}
    todo = [r for r in rows('youtube-video-boards.csv')
            if r.get('meeting_date') and r['video_id'] not in have and r['video_id'] not in dead]
    return group((r['board_slug'], r['meeting_date']) for r in todo)


def register_pending(want, have_dir):
    """Meetings the register says CAN be read, for which no file exists yet."""
    have = {os.path.relpath(p, os.path.join(DATA, have_dir))[:-5].split('/')[0] + '|' +
            os.path.basename(p)[:10]
            for p in glob.glob(os.path.join(DATA, have_dir, '*', '*.json'))}
    out = []
    for r in rows('meeting-register.csv'):
        if r.get('part_of') or not want(r):
            continue
        if '%s|%s' % (r['board_slug'], r['date']) in have:
            continue
        out.append((r['board_slug'], r['date']))
    return group(out)


# ------------------------------------------------------------------- the streams
def streams():
    """One row per ingestion stream: how many done, how many left, measured ONE way.

    The count and the denominator come from the same place for each stream, because the
    morning this page was written three registries gave three different answers for the
    caption backlog and all three were defensible.
    """
    s = []

    # CAPTIONS. The fetcher is the authority: it knows which videos are in scope (matched
    # to a board) as opposed to merely on the channel.
    # ONE NUMBER, ONE SOURCE. The first version of this card counted the todo as every
    # video on the channel minus what we hold -- 2,661 -- while the breakdown beneath it
    # counted only videos classified to a board AND a date -- 831. Both were defensible
    # and they sat two inches apart, which is the precise failure this page was built to
    # stop: I had quoted 478, then 963, then 840 for this one quantity in conversation
    # the same morning, because three registries answer three slightly different
    # questions. So the headline is now the SAME list the breakdown expands, and what the
    # other number counted is said out loud beside it rather than silently replacing it.
    idx = rows('youtube-transcript-index.csv')
    nocap = rows('youtube-no-captions.csv')
    vids = rows('youtube-videos.csv')
    have = {r['video_id'] for r in idx}
    dead = {r['video_id'] for r in nocap}
    pend = caption_pending()
    todo = sum(p['n'] for p in pend)
    # Everything on the channel that is not a classified board meeting: ceremonies, a
    # Patriot Day remembrance, multi-part uploads with no date. Not a backlog.
    unclassified = max(0, len(vids) - len(have) - len(dead) - todo)
    by_board = collections.Counter(r['board_slug'] for r in idx)
    s.append(dict(key='captions', name='Captions for recordings',
                  done=len(have), todo=todo,
                  blocked=len(dead), blocked_why='captions disabled by the publisher',
                  cost='free — throttled by YouTube',
                  last=ago(max([r.get('fetched_at','') for r in idx] or [''])),
                  note='%d boards with captions held; %s more uploads carry no board and date, '
                       'so they are not a meeting backlog' % (len(by_board), '{:,}'.format(unclassified)),
                  pending=pend))

    # OCR.
    ocr = rows('ocr-minutes.csv')
    try:
        left = int(subprocess.run([sys.executable, os.path.join(ROOT,'scripts','ocr_scanned_minutes.py'),'--status'],
                  capture_output=True, text=True, cwd=ROOT, timeout=120).stdout.split()[0])
    except Exception:
        left = None
    s.append(dict(key='ocr', name='OCR of scanned minutes', done=len(ocr), todo=left,
                  blocked=0, blocked_why='', cost='free — macOS Vision, local',
                  last=ago(max([r.get('ocr_at','') for r in ocr] or [''])),
                  note='a scan is invisible to search and to the vote reader until this runs',
                  pending=[]))

    # VOTES and OUR MINUTES: count files, and take the denominator from the register.
    # THE HEADLINE IS THE SUM OF THE BREAKDOWN, always. Computing the two separately is
    # what put 1,201 in the pill and 1,206 in the table beneath it -- five meetings whose
    # file exists but whose register row no longer matches it. That difference is worth
    # finding, and it is not worth guessing at from a dashboard, so the page states the
    # one figure it can stand behind: how many meetings have no file.
    vp = register_pending(lambda r: r.get('minutes') == '1', 'official-votes')
    s.append(dict(key='votes', name='Votes from the town’s minutes',
                  done=len(glob.glob(os.path.join(DATA, 'official-votes', '*', '*.json'))),
                  todo=sum(p['n'] for p in vp), blocked=0, blocked_why='',
                  cost='~0.03% of the weekly allowance each',
                  last='', note='every vote carries a quote checked verbatim against the minutes',
                  pending=vp))
    mp = register_pending(lambda r: bool(r.get('transcript_paths')), 'recording-minutes')
    s.append(dict(key='ourminutes', name='Our minutes of recordings',
                  done=len(glob.glob(os.path.join(DATA, 'recording-minutes', '*', '*.json'))),
                  todo=sum(p['n'] for p in mp), blocked=0, blocked_why='',
                  cost='~0.09% of the weekly allowance each',
                  last='', note='written from our captions; two derived layers from the meeting',
                  pending=mp))
    return s

# -------------------------------------------------------------------- the refresh
WATCHERS = [
    ('watch_meetings.py',  'the town’s AgendaCenter — every board’s agendas and minutes'),
    ('fetch_agendas.py',   'downloads whatever the watcher found that we do not hold'),
    ('watch_documents.py', 'the district’s budget page and the town’s finance pages'),
    ('watch_feeds.py',     'the town’s news flash and alert feeds'),
    ('watch_youtube.py',   'the channel’s RSS feed — new recordings'),
]

def refresh():
    """Today's run: whether it is going, where it looked, what it found, what it will do."""
    logdir = os.path.join(ROOT, 'build', 'refresh-logs')
    logs = sorted(glob.glob(os.path.join(logdir, '*.log')), reverse=True)
    today = dt.date.today().isoformat()
    cur = logs[0] if logs else None
    text = ''
    if cur:
        with open(cur, encoding='utf-8', errors='replace') as fh:
            text = fh.read()
    live = any(r['name'] == 'Daily refresh' for r in running())

    # WHERE IT LOOKED, read off the log rather than assumed. A watcher that did not run
    # is a watcher that did not look, and the difference matters when something is missing.
    looked = []
    for script, what in WATCHERS:
        m = re.findall(re.escape(script) + r'[^\n]*?: ([\d.]+)s, exit (\d+)', text)
        if m:
            looked.append(dict(script=script, what=what, seconds=float(m[-1][0]), exit=int(m[-1][1]), ran=True))
        else:
            looked.append(dict(script=script, what=what, seconds=None, exit=None, ran=False))

    found = []
    for pat, label in ((r'(\d+) new agenda', 'agendas'), (r'(\d+) new minutes', 'minutes'),
                       (r'(\d+) new video', 'recordings'), (r'(\d+) new transcript', 'captions')):
        m = re.findall(pat, text)
        if m: found.append(dict(label=label, n=int(m[-1])))

    # WHAT IT IS ABOUT TO DO. The log prints each claude -p job as it starts, so the last
    # one with no result line after it is the one in flight.
    jobs = re.findall(r'(write_recording_minutes|extract_official_votes)\.py '
                      r'([a-z0-9-]+) (\d{4}-\d{2}-\d{2})', text)
    costs = [float(x) for x in re.findall(r'written \(\$([\d.]+)\)', text)]
    hist = rows('refresh-runs.csv')[-6:][::-1]
    return dict(live=live, log=os.path.basename(cur) if cur else None, today=today,
                looked=looked, found=found,
                jobs=[dict(script=a, board=b, date=c) for a, b, c in jobs[-6:]][::-1],
                spent=round(sum(costs), 2), spent_n=len(costs),
                tail=[l for l in text.splitlines() if l.strip()][-14:],
                history=hist)

# ------------------------------------------------------------- queued, not ingested
def queued():
    """Anything sitting in the inbox that has not been filed into sources/.

    MATCHED BY CONTENT, NOT BY NAME. The first version compared filenames against the
    manifest and reported all three of the Select Board deliveries as NOT INGESTED --
    hours after they had been ingested -- because filing them renames them to the
    archive's own convention. A dashboard that cries wolf is worse than no dashboard, and
    a sha256 cannot be fooled by a rename. A zip is opened and judged by what is inside
    it: the container is packaging, the documents are the delivery.
    """
    import hashlib, zipfile
    q = []
    inbox = os.path.join(ROOT, 'build', 'inbox')
    if not os.path.isdir(inbox):
        return q
    known = set()
    mp = os.path.join(DATA, 'archive-manifest.csv')
    if os.path.exists(mp):
        with open(mp, encoding='utf-8', errors='replace') as fh:
            known = {r['sha256'] for r in csv.DictReader(fh) if r.get('sha256')}

    def sha(b):
        return hashlib.sha256(b).hexdigest()

    for fn in sorted(os.listdir(inbox)):
        if fn.startswith('.'):
            continue
        p = os.path.join(inbox, fn)
        if os.path.isdir(p):
            continue                       # a working folder is not a delivery
        size = os.path.getsize(p)
        try:
            if fn.lower().endswith('.zip'):
                with zipfile.ZipFile(p) as z:
                    names = [n for n in z.namelist()
                             if not n.startswith('__MACOSX/') and not n.endswith('/')]
                    hits = sum(1 for n in names if sha(z.read(n)) in known)
                q.append(dict(name=fn, bytes=size, n=len(names), done=hits,
                              ingested=(hits == len(names) and bool(names)),
                              note='%d of %d documents inside are in the archive' % (hits, len(names))))
            else:
                with open(p, 'rb') as fh:
                    hit = sha(fh.read()) in known
                q.append(dict(name=fn, bytes=size, n=1, done=1 if hit else 0, ingested=hit,
                              note='' if hit else 'not filed into sources/ yet'))
        except Exception as e:
            q.append(dict(name=fn, bytes=size, n=0, done=0, ingested=None,
                          note='could not be read: %s' % e))
    return q


# ---------------------------------------------------------------------- the sources
def sources():
    """Every document held, with what is known about it.

    Derived text is excluded: it is a rendering of a document, not a document, and
    including it doubles the table while adding no address anybody can check.
    """
    out = []
    upstream = {}
    for idx in glob.glob(os.path.join(ROOT, 'sources', '*', 'index.csv')):
        folder = os.path.basename(os.path.dirname(idx))
        try:
            with open(idx, encoding='utf-8', errors='replace') as fh:
                for r in csv.DictReader(fh):
                    loc = (r.get('local') or r.get('path') or '').strip()
                    if not loc: continue
                    key = loc[len('sources/'):] if loc.startswith('sources/') else folder + '/' + loc
                    upstream[key] = r.get('url') or r.get('upstream') or ''
        except Exception:
            pass
    mp = os.path.join(DATA, 'archive-manifest.csv')
    if not os.path.exists(mp): return out
    with open(mp, encoding='utf-8', errors='replace') as fh:
        for r in csv.DictReader(fh):
            k = r['key']
            if '/text/' in k or k.endswith('.txt'): continue
            top = k.split('/')[0]
            out.append([k, int(r['bytes'] or 0), (r.get('upstream') or upstream.get(k, '') or ''),
                        (r.get('sha256') or '')[:12], top])
    return out

# --------------------------------------------------------------------------- render
CSS = """
*{box-sizing:border-box}body{margin:0;font:14px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
background:#0e1116;color:#e6edf3}a{color:#6cb6ff}
.wrap{max-width:1180px;margin:0 auto;padding:22px 18px 60px}
h1{font-size:19px;margin:0 0 2px}h2{font-size:12px;text-transform:uppercase;letter-spacing:.12em;
color:#8b949e;margin:26px 0 10px;font-weight:600}
.sub{color:#8b949e;font-size:12.5px;margin:0 0 4px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px 14px;margin-bottom:8px}
.on{border-left:3px solid #3fb950}.cost{border-left:3px solid #d29922}.idle{color:#8b949e}
.row{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.grow{flex:1;min-width:200px}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
.num{font-variant-numeric:tabular-nums}
.bar{height:6px;background:#21262d;border-radius:3px;overflow:hidden;margin-top:6px}
.bar i{display:block;height:100%;background:#3fb950}
.bar i.part{background:#d29922}
.pill{font-size:11px;padding:1px 7px;border-radius:9px;background:#21262d;color:#8b949e}
.pill.go{background:#1a3a24;color:#3fb950}.pill.warn{background:#3a2d12;color:#d29922}
.pill.no{background:#3a1d1d;color:#f85149}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{text-align:left;color:#8b949e;font-weight:600;padding:5px 8px;border-bottom:1px solid #30363d;
position:sticky;top:0;background:#0e1116}
td{padding:4px 8px;border-bottom:1px solid #1c2128;vertical-align:top}
tr:hover td{background:#161b22}
pre{background:#0b0e13;border:1px solid #21262d;border-radius:6px;padding:10px;overflow-x:auto;
font-size:11.5px;color:#a0adba;margin:0;max-height:260px}
input[type=search]{width:100%;padding:8px 10px;background:#0b0e13;border:1px solid #30363d;
border-radius:6px;color:#e6edf3;font-size:13px}
.tiny{font-size:11.5px;color:#8b949e}.r{text-align:right}
.tabs a{display:inline-block;padding:5px 11px;border:1px solid #30363d;border-radius:6px;
margin-right:6px;text-decoration:none;font-size:12.5px}
.tabs a.sel{background:#1f6feb;border-color:#1f6feb;color:#fff}
"""

def bar(done, todo):
    tot = (done or 0) + (todo or 0)
    if not tot: return ''
    return '<div class="bar"><i style="width:%.1f%%"></i></div>' % (100.0 * done / tot)

def page_live(st):
    R, S, F, Q = st['running'], st['streams'], st['refresh'], st['queued']
    h = []
    h.append('<div class="wrap"><div class="row"><div class="grow"><h1>Ingestion</h1>'
             '<p class="sub">%s &middot; refreshes itself every 20s</p></div>'
             '<div class="tabs"><a class="sel" href="index.html">Running</a>'
             '<a href="sources.html">Documents</a></div></div>' % st['generated'])

    h.append('<h2>Running now</h2>')
    if not R:
        h.append('<div class="card idle">Nothing is running. No process is fetching, reading or building.</div>')
    for r in R:
        h.append('<div class="card %s"><div class="row"><b class="grow">%s</b>'
                 '<span class="pill %s">%s</span><span class="tiny num">%s</span></div>'
                 '<div class="tiny">%s</div><div class="mono tiny" style="margin-top:4px;color:#586069">%s</div></div>'
                 % ('cost' if r['costs'] else 'on', html.escape(r['name']),
                    'warn' if r['costs'] else 'go',
                    ('%d procs' % r['n']) if r['n'] > 1 else 'running',
                    html.escape(r['elapsed']), html.escape(r['what']), html.escape(r['cmd'])))

    h.append('<h2>The daily refresh</h2>')
    h.append('<div class="card %s"><div class="row"><b class="grow">%s</b><span class="pill %s">%s</span></div>'
             % ('on' if F['live'] else '', 'Today&rsquo;s run &mdash; ' + F['today'],
                'go' if F['live'] else '', 'running' if F['live'] else 'not running'))
    if F['found']:
        h.append('<div class="row tiny" style="margin-top:6px">Found: ' +
                 ' &middot; '.join('<b>%d</b> %s' % (f['n'], f['label']) for f in F['found']) + '</div>')
    if F['spent_n']:
        h.append('<div class="tiny" style="margin-top:4px">Spent today: <b>$%.2f</b> API-equivalent '
                 'across %d job(s) &mdash; about %.1f%% of the week.</div>'
                 % (F['spent'], F['spent_n'], F['spent'] / 5))
    h.append('</div>')

    h.append('<div class="card"><div class="tiny" style="margin-bottom:6px"><b>Where it looked today.</b> '
             'A watcher that did not run is a watcher that did not look.</div><table>')
    for w in F['looked']:
        h.append('<tr><td class="mono">%s</td><td>%s</td><td class="r">%s</td></tr>'
                 % (w['script'], html.escape(w['what']),
                    ('<span class="pill go">%.0fs</span>' % w['seconds']) if w['ran']
                    else '<span class="pill">did not run</span>'))
    h.append('</table></div>')

    if F['jobs']:
        h.append('<div class="card"><div class="tiny" style="margin-bottom:6px">'
                 '<b>Reading jobs this run</b> (newest first)</div><table>')
        for j in F['jobs']:
            h.append('<tr><td class="mono">%s</td><td>%s</td><td class="r mono">%s</td></tr>'
                     % (j['script'], html.escape(j['board']), j['date']))
        h.append('</table></div>')

    h.append('<div class="card"><div class="tiny" style="margin-bottom:6px"><b>Log</b> &mdash; %s</div><pre>%s</pre></div>'
             % (F['log'] or 'none', html.escape('\n'.join(F['tail'])) or 'nothing yet today'))

    h.append('<h2>Streams</h2>')
    for s in S:
        todo = s['todo']
        h.append('<div class="card"><div class="row"><b class="grow">%s</b>'
                 '<span class="num">%s done</span>'
                 '<span class="pill %s">%s</span></div>%s'
                 '<div class="tiny" style="margin-top:6px">%s &middot; %s%s</div>'
                 % (html.escape(s['name']), '{:,}'.format(s['done']),
                    'go' if todo == 0 else 'warn',
                    'complete' if todo == 0 else ('{:,} left'.format(todo) if todo is not None else 'unknown'),
                    bar(s['done'], todo or 0), html.escape(s['cost']),
                    html.escape(s['note']),
                    (' &middot; %d blocked: %s' % (s['blocked'], html.escape(s['blocked_why']))) if s['blocked'] else ''))
        # THE BREAKDOWN, COLLAPSED. A backlog total says how worried to be; the boards and
        # the years say what it actually is. Collapsed because the number is the thing a
        # glance wants and the detail is the thing a decision wants.
        pend = s.get('pending') or []
        if pend:
            n = sum(p['n'] for p in pend)
            h.append('<details style="margin-top:8px"><summary class="tiny" '
                     'style="cursor:pointer;color:#6cb6ff">%s across %d board(s) — '
                     'by board and date</summary><table style="margin-top:8px">'
                     '<tr><th>board</th><th class="r">left</th><th>earliest</th>'
                     '<th>latest</th><th></th></tr>' % ('{:,}'.format(n), len(pend)))
            for r in pend:
                h.append('<tr><td>%s</td><td class="r num">%d</td>'
                         '<td class="mono tiny">%s</td><td class="mono tiny">%s</td>'
                         '<td><details><summary class="tiny" style="cursor:pointer;color:#8b949e">'
                         'dates</summary><div class="mono tiny" style="max-width:420px">%s</div>'
                         '</details></td></tr>'
                         % (html.escape(r['board'].replace('-', ' ')), r['n'],
                            r['first'], r['last'],
                            ' '.join(r['dates'][:400])))
            h.append('</table></details>')
        h.append('</div>')

    h.append('<h2>Queued, not yet ingested</h2>')
    if not Q:
        h.append('<div class="card idle">The inbox is empty.</div>')
    for q in Q:
        h.append('<div class="card"><div class="row"><b class="grow mono">%s</b>'
                 '<span class="pill %s">%s</span><span class="tiny num">%s</span></div>'
                 '<div class="tiny">%s</div></div>'
                 % (html.escape(q['name']),
                    'go' if q['ingested'] else ('' if q['ingested'] is None else 'no'),
                    'ingested' if q['ingested'] else ('unreadable' if q['ingested'] is None else 'NOT INGESTED'),
                    '{:,} B'.format(q['bytes']) if q['bytes'] else '', html.escape(q['note'])))

    h.append('<h2>Recent refresh runs</h2><div class="card"><table>'
             '<tr><th>ran</th><th>as of</th><th class="r">agendas</th><th class="r">minutes</th>'
             '<th class="r">videos</th><th class="r">captions</th><th>deployed</th><th>note</th></tr>')
    for r in F['history']:
        h.append('<tr><td class="mono">%s</td><td class="mono">%s</td>'
                 '<td class="r num">%s</td><td class="r num">%s</td><td class="r num">%s</td>'
                 '<td class="r num">%s</td><td>%s</td><td class="tiny">%s</td></tr>'
                 % (ago(r.get('ran_at')), r.get('as_of',''), r.get('new_agendas',''),
                    r.get('new_minutes',''), r.get('new_videos',''), r.get('new_transcripts',''),
                    r.get('deployed',''), html.escape((r.get('notes') or '')[:70])))
    h.append('</table></div></div>')
    return ''.join(h)

def page_sources(st, n):
    return ('<div class="wrap"><div class="row"><div class="grow"><h1>Documents</h1>'
            '<p class="sub">%s held &middot; %s</p></div>'
            '<div class="tabs"><a href="index.html">Running</a>'
            '<a class="sel" href="sources.html">Documents</a></div></div>'
            '<input type="search" id="q" placeholder="filter by path, folder or address — e.g. select-board 2025, or munis, or xlsx">'
            '<p class="tiny" id="c" style="margin:8px 0"></p>'
            '<table><tr><th>document</th><th class="r">size</th><th>publisher&rsquo;s address</th>'
            '<th>sha256</th></tr><tbody id="t"></tbody></table>'
            '<p class="tiny" id="more"></p></div>'
            % ('{:,}'.format(n), st['generated']))

JS = """
const fmt=b=>b>1e6?(b/1e6).toFixed(1)+' MB':b>1e3?Math.round(b/1e3)+' KB':b+' B';
const t=document.getElementById('t'),q=document.getElementById('q'),c=document.getElementById('c'),
      more=document.getElementById('more');
const CAP=400;
function draw(){
  const s=q.value.toLowerCase().split(/\\s+/).filter(Boolean);
  const hit=DOCS.filter(d=>s.every(w=>d[0].toLowerCase().includes(w)||(d[2]||'').toLowerCase().includes(w)));
  c.textContent=hit.length.toLocaleString()+' of '+DOCS.length.toLocaleString()+' documents'+
    (hit.length>CAP?' — showing the first '+CAP:'');
  t.innerHTML=hit.slice(0,CAP).map(d=>
    '<tr><td class="mono">'+d[0]+'</td><td class="r num">'+fmt(d[1])+'</td><td class="tiny">'+
    (d[2]?'<a href="'+d[2]+'">'+d[2].slice(0,64)+'</a>':'<span style="color:#f85149">no address</span>')+
    '</td><td class="mono tiny">'+d[3]+'</td></tr>').join('');
  more.textContent=hit.length>CAP?'Narrow the filter to see the rest.':'';
}
q.addEventListener('input',draw);draw();
"""

def write(open_it=False):
    os.makedirs(OUT, exist_ok=True)
    st = dict(generated=dt.datetime.now().strftime('%a %d %b, %H:%M:%S'),
              running=running(), streams=streams(), refresh=refresh(), queued=queued())
    docs = sources()
    shell = ('<!doctype html><meta charset=utf-8><meta name=viewport '
             'content="width=device-width,initial-scale=1"><title>%s</title>'
             '%s<style>%s</style>%s')
    with open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8') as fh:
        fh.write(shell % ('Ingestion', '<meta http-equiv="refresh" content="20">', CSS, page_live(st)))
    # The document list is written as a <script>, not JSON: a browser will not fetch() a
    # local file but will happily <script src> one.
    with open(os.path.join(OUT, 'docs.js'), 'w', encoding='utf-8') as fh:
        fh.write('const DOCS=' + json.dumps(docs, separators=(',', ':')) + ';')
    with open(os.path.join(OUT, 'sources.html'), 'w', encoding='utf-8') as fh:
        fh.write(shell % ('Documents', '', CSS, page_sources(st, len(docs)))
                 + '<script src="docs.js"></script><script>' + JS + '</script>')
    return st, len(docs)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--watch', action='store_true', help='rewrite every 20 seconds')
    ap.add_argument('--open', action='store_true')
    a = ap.parse_args()
    st, n = write()
    p = os.path.join(OUT, 'index.html')
    print('wrote %s — %d running, %d documents' % (os.path.relpath(p, ROOT), len(st['running']), n))
    if a.open:
        subprocess.run(['open', p])
    if a.watch:
        print('watching; ctrl-c to stop')
        while True:
            time.sleep(20)
            try:
                write()
            except Exception as e:
                print('  (skipped a cycle: %s)' % e)

if __name__ == '__main__':
    main()
