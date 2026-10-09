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
import argparse, collections, csv, datetime as dt, glob, html, json, os, re, subprocess, sqlite3, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import stream_cost as COST  # noqa: E402
DATA = os.path.join(ROOT, 'sources', 'data')
OUT  = os.path.join(ROOT, 'build', 'status')
TREE = os.path.join(os.path.dirname(ROOT), 'lunenburgbudgets-refresh')

# ONCE PER BUILD. It was called twice a build at ~10 s each (9 October 2026; 1.3 s when the
# comment above was written), and the launchd job rebuilds every 60 s -- so the page spent
# more time computing than resting. write() clears this at the start of every build.
_ONCE = {}


def once(fn):
    def wrapped():
        if fn.__name__ not in _ONCE:
            _ONCE[fn.__name__] = fn()
        return _ONCE[fn.__name__]
    wrapped.__name__ = fn.__name__
    return wrapped


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


def clock(ts):
    """A timestamp as the wall clock says it, local: '08:12'.

    TJ, 20 September 2026: "Seeing refresh failed and all that done today is not
    believable." He is right, and `ago()` is why -- "3h ago" is a duration, and a page
    full of durations beside a failed run reads as a claim rather than a record. A clock
    time can be checked against the log, the shell history and his own memory of the
    morning; a relative one cannot.
    """
    if not ts: return ''
    try:
        d = dt.datetime.fromisoformat(ts.replace('Z', '+00:00'))
        if d.tzinfo is None: d = d.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return ''
    return d.astimezone().strftime('%H:%M')

# ---------------------------------------------------------------- what is alive
# EVERY PATTERN IS BRACKETED. `pgrep -f "sweep_backlog"` matches the shell running the
# pgrep, so a naive check reports itself as a running job -- the self-matching pattern
# CLAUDE.md warns about, which has cost this project a session's coordination twice.
# `[s]weep_backlog` cannot match its own argv.
# THE JOBS THAT SPEND THE PLAN. Named here rather than sniffed out of the description,
# because a label that depends on a phrase in prose breaks the first time the prose is
# reworded — which it was, the moment the word changed from a colour to a tag.
# WHICH JOBS SPEND THE ALLOWANCE. The daily refresh is deliberately NOT here, and the
# reasoning took a wrong turn first.
#
# TJ: "the Daily refresh isn't agentic?" -- and it does spend: step 7 writes our minutes
# of new recordings through `claude -p`, $0.67 on the morning this was written. So the
# first fix was to tag it. Then: "maybe you split out the recording minutes into a
# separate bar then?"
#
# That is the better answer, and it is already how the page works. The refresh is a
# WRAPPER around a dozen steps, all but one of them free, and the agentic one --
# write_recording_minutes.py -- is watched in its own right and appears as its own card
# whenever it runs, tagged and with its own elapsed time. Tagging the parent as well
# would count the same spending twice on one screen and blur the thing the tag is for:
# which PROCESS is costing money right now.
#
# So the parent stays green and names its spend as a figure; the child carries the tag.
AGENTIC = {'Writing up a recorded meeting', 'Reading the town’s official minutes', 'Backlog sweep', 'Reading what a budget meeting decided'}

# WHAT EACH JOB IS, IN ONE LINE A PERSON WOULD SAY. TJ, 19 September 2026: "I think these
# steps need descriptions too, short descriptions. the 'votes' one keeps getting me."
#
# It kept getting him because the label named the OUTPUT and the confusion was about the
# INPUT: "Votes" sounds like it should be everything we take from a meeting, when it is
# one narrow thing taken from the town's own minutes -- the other stream, our minutes,
# is the one that captures the whole meeting. So each line now says what goes in and what
# comes out, in that order, because that is the distinction the names could not carry.
#
# `sleeps` marks a wrapper that spends most of its life waiting: alive is not working, and
# a page that cannot tell them apart says "running" about a process asleep in a backoff.
WATCHED = [
    ('Fetching captions', r'[f]etch_youtube_transcripts\.py',
     'The machine captions of a recording, so a meeting nobody minuted can still be '
     'searched. One batch at a time.', False),
    ('Caption backfill', r'[r]un_transcript_backfill\.sh',
     'Works through the recordings with no captions yet, newest first. Backs off for '
     'longer and longer when YouTube refuses, so it is asleep more often than not.', True),
    ('Reading scanned minutes', r'[o]cr_scanned_minutes\.py|[o]cr_pdf',
     'Minutes the town posted as page images are invisible to search until a reader looks '
     'at the pixels. Local and free.', False),
    ('Daily refresh', r'[r]efresh\.py|[d]aily_refresh\.sh',
     'The 7am run: check the town and the channel, fetch what is new, rebuild, deploy.', False),
    ('Writing up a recorded meeting', r'[w]rite_recording_minutes\.py',
     'Our record of what happened, from our captions: decisions, votes, transfers, '
     'topics, public comment. Used where the town published no minutes at all.', False),
    ('Reading the town’s official minutes', r'[e]xtract_official_votes\.py',
     'The whole meeting as the town recorded it: attendees, votes, decisions, budget items, '
     'transfers, public comment, topics, each quoted verbatim. Structured reads since 6 '
     'October 2026; before that it took the votes only.', False),
    ('Reading what a budget meeting decided', r'[w]rite_budget_state\.py',
     'Reads a budget meeting and records what it put on the record: the deficit, the '
     'cuts, the proposals. Feeds the budget season page.', False),
    ('Backlog sweep', r'[s]weep_backlog\.py',
     'Works the votes and minutes backlog in bulk, newest first, until the plan says no.', False),
    ('Downloading the AG’s Open Meeting Law determinations', r'[f]etch_oml_determinations\.py',
     'Every determination letter the Attorney General has issued, 2010 to today, each one '
     'landed in the bucket with its text. Download only; nothing reads them yet.', False),
    ('Text extraction', r'[e]xtract_minutes\.py',
     'Pulls the text out of newly downloaded PDFs and Word files.', False),
    ('Site build', r'[v]ite build|[p]rerender\.mjs',
     'Rebuilds the 332 pages of the public site.', False),
    ('Archive sync', r'[s]ync_archive\.py',
     'Hashes the archive, or uploads new documents to the R2 bucket.', False),
]

# A wrapper is WORKING only while one of these is alive under it.
WHAT = {name: what for name, _, what, _ in WATCHED}

CHILD_OF = {'Caption backfill': r'[f]etch_youtube_transcripts\.py',
            'Daily refresh': r'[a-z_]+\.py'}



def etime_seconds(e):
    """ps etime — [[dd-]hh:]mm:ss — as seconds."""
    if not e:
        return 0
    days, _, rest = e.partition('-')
    if not rest:
        rest, days = days, '0'
    parts = [int(x) for x in rest.split(':')]
    while len(parts) < 3:
        parts.insert(0, 0)
    return int(days) * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]


# HOW MANY THIS RUN HAS DONE, from the same timestamps "Done today" uses.
#
# TJ, 19 September 2026: "running now and done today have metric discrepancies."
#
# They did, and it was the mtime bug again -- fixed in done_today() and left here. This
# counted files whose mtime fell after the process started, across both trees, so the
# refresh tree's `git reset --hard` inflated it: 33 "landed" against 20 actually read.
# Two panels on one screen, each confidently reporting a different number for one
# quantity, is the exact failure this page was built to end, so it may not be measured
# two ways.
#
# Every stream that records WHEN it did a thing is counted from that record. A stream with
# no such record reports nothing rather than a figure from an adjacent quantity.
SINCE = {
    'Fetching captions': ('youtube-transcript-index.csv', 'fetched_at'),
    'Caption backfill': ('youtube-transcript-index.csv', 'fetched_at'),
    'Reading scanned minutes':     ('ocr-minutes.csv', 'ocr_at'),
}


def scope(name, cmd, elapsed):
    """What this run means to do, and what it has done since it started.

    THE PLAN is the job's own `--limit`, read off the command line it is running under.
    A wrapper that loops has no total of its own -- its `--limit` belongs to the child --
    so it reports progress without a denominator rather than inventing one.
    """
    m = re.search(r'--limit\s+(\d+)', cmd or '')
    plan = int(m.group(1)) if m else None
    reg = SINCE.get(name)
    if not reg:
        return dict(plan=plan, done=None)
    start = dt.datetime.fromtimestamp(time.time() - etime_seconds(elapsed),
                                      dt.timezone.utc).isoformat()
    f, col = reg
    done = sum(1 for r in rows(f) if (r.get(col) or '') >= start)
    return dict(plan=plan, done=done)



# EVERY STEP, NOT A LIST SOMEBODY REMEMBERED TO UPDATE.
#
# The watched list was typed by hand, and write_budget_state.py ran for two minutes
# spending the allowance while the page said "Caption backfill" was the only thing going.
# A hand-kept list fails silently in the one direction that matters: it cannot report a
# job it was never told about, and its silence is indistinguishable from that job not
# running.
#
# So anything running out of scripts/ is discovered, whether or not it is described.
# A described job gets its sentence; an undescribed one still appears, named, which is a
# visible prompt to describe it rather than an invisible gap.
# EVERY STEP, IN THE WORDS OF WHAT IT DOES FOR THE TOWN.
#
# TJ, 19 September 2026: "Give descriptive titles and descriptions. build_boards.py is a
# script ;)"
#
# Quite. A filename is what WE call the thing; this page is read to find out what the
# machine is doing, and `tag_document_affinity.py` answers that for nobody. The fallback
# to a filename stays -- an undescribed step must still appear, because a silent gap is
# what let write_budget_state.py run unlisted -- but it is a prompt to write a line here,
# not a place to leave one.
#
# Each entry is a TITLE saying what changes in the world, and a sentence saying why a
# resident would care.
STEP_WORDS = {
    # --- looking
    'watch_meetings': ('Checking for new agendas and minutes',
        'Every board’s page on the town’s Agenda Center, for anything posted since the last look.'),
    'watch_documents': ('Checking the budget pages',
        'The district’s budget pages and the town’s finance pages, for documents that were not there yesterday.'),
    'watch_feeds': ('Checking the town’s announcements',
        'The news flash and alert feeds: closures, warrants, elections.'),
    'watch_youtube': ('Checking for new recordings',
        'The town’s YouTube channel, for meetings that have just been posted.'),
    # --- getting
    'fetch_agendas': ('Downloading agendas and minutes',
        'Saving a copy of everything the town posted that this archive does not already hold.'),
    'fetch_town_docs': ('Downloading town documents',
        'Saving new documents from the town’s own pages.'),
    'fetch_school_budget_docs': ('Downloading district documents',
        'Saving new documents from the district’s budget pages — many of them Google Drive links that die.'),
    'fetch_youtube_transcripts': ('Fetching captions',
        'The machine captions of a recording, so a meeting nobody minuted can still be searched.'),
    # --- reading
    'extract_minutes': ('Reading the new files',
        'Pulling the words out of the PDFs and Word files just downloaded, so they can be searched.'),
    'ocr_scanned_minutes': ('Reading scanned minutes',
        'Minutes the town posted as page images are invisible to search until a reader looks at the pixels.'),
    'extract_document_timestamps': ('Dating the documents',
        'When each agenda and set of minutes was MADE, from the file’s own metadata — a lower bound on when the town could have posted it.'),
    'build_youtube_classification': ('Matching recordings to meetings',
        'Working out which board and which date each new video belongs to.'),
    'tag_document_affinity': ('Tagging documents by subject',
        'So a search for a subject finds the document about it even when the document never uses that word.'),
    'reconcile_minutes': ('Comparing our minutes with the town’s',
        'Where both exist: caption mistakes resolved against the record, real differences flagged.'),
    # --- writing
    'write_recording_minutes': ('Writing up a recorded meeting',
        'Our record of what happened, from our captions: decisions, votes, transfers, topics, public comment.'),
    'extract_official_votes': ('Reading the town’s official minutes',
        'The whole meeting as the town recorded it, each item quoted verbatim.'),
    'write_budget_state': ('Reading what a budget meeting decided',
        'The deficit, the cuts and the proposals a meeting put on the record.'),
    'write_document_budget_state': ('Reading what a new budget document says',
        'What a document just published changes about the budget being built.'),
    'write_agenda_preview': ('Previewing an upcoming meeting',
        'A plain-language note on what a meeting is about to cover, before it happens.'),
    # --- publishing
    'build_minutes_searchable': ('Indexing the new minutes',
        'Making the text just read findable by search.'),
    'build_search_index': ('Rebuilding search',
        'One index across pages, documents, minutes and captions.'),
    'build_meeting_register': ('Rebuilding the meeting record',
        'One row per meeting with every artifact on it — the list every page reads to know what happened.'),
    'build_boards': ('Rebuilding the board pages',
        'One page per board: what is coming, what happened, every vote, where the time goes.'),
    'build_budget_feed': ('Rebuilding the budget feed',
        'Everything budget-related across every board, on one page.'),
    'build_budget_season': ('Rebuilding the budget season',
        'The season as a status board, from what the record now says.'),
    'build_meeting_feed': ('Rebuilding the meeting feed',
        'What is coming, and whose minutes have just appeared.'),
    'build_notices': ('Writing the notices',
        'What to tell people before a meeting, and what to tell them after.'),
    'build_recording_minutes': ('Publishing our minutes',
        'Putting the meetings we wrote up onto the site.'),
    'build_feeds': ('Rebuilding the subscriptions',
        'The Atom feeds a resident subscribes to: one per board, one for the budget, one for everything.'),
}


def discovered(known):
    """Any script of ours running that the watched list does not already name.

    `ps`, not `pgrep -af`: on macOS pgrep's -a prints PIDs only, so the first version
    parsed an empty command line and discovered nothing -- failing exactly the way the
    hand-kept list it was written to replace had failed, and just as quietly.
    """
    out = []
    try:
        r = subprocess.run(['ps', '-Ao', 'pid=,etime=,args='],
                           capture_output=True, text=True)
    except Exception:
        return out
    for line in r.stdout.splitlines():
        m = re.search(r'lunenburgbudgets[a-z-]*/scripts/([a-z_]+)\.(py|sh)', line)
        if not m:
            continue
        stem = m.group(1)
        if stem in known or stem == 'build_ingest_status':
            continue
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        name, what = STEP_WORDS.get(stem, (stem + '.py', 'A step of the daily run.'))
        out.append(dict(name=name, what=what, n=1, elapsed=parts[1], idle=False,
                        cmd=parts[2][:200], plan=None, done=None, stem=stem,
                        costs=stem.startswith('write_') or stem.startswith('extract_official')))
    return out


def running():
    out = []
    for name, pat, what, sleeps in WATCHED:
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
        # ALIVE IS NOT WORKING. The caption backfill runs for days and spends most of
        # them asleep between batches; reporting that as "running" is how a page ends up
        # implying two things are happening when one is.
        idle = False
        if sleeps:
            kid = CHILD_OF.get(name)
            idle = not (kid and subprocess.run(['pgrep', '-f', kid],
                                               capture_output=True, text=True).stdout.strip())
        out.append(dict(name=name, what=what, n=len(pids), elapsed=el, cmd=cmd, idle=idle,
                        costs=name in AGENTIC, **scope(name, cmd, el)))

    for x in out:
        if x['name'] == OML_JOB:
            o = oml_progress()
            if o:
                x.update(plan=o['listed'], done=o['held'], scope_word='held of the AG’s list',
                         extra=o['running_line'])

    # ...and anything else of ours that is running, described or not. The patterns above
    # are bracketed so they cannot match their own argv (`[d]aily_refresh`), so the
    # leading letter has to be put back before comparing against a real script name.
    known = {re.sub(r'[\[\]]', '', m) for m in
             re.findall(r'((?:\[[a-z]\])?[a-z_]+)\\?\.(?:py|sh)',
                        ' '.join(pat for _, pat, _, _ in WATCHED))}
    known |= {'refresh', 'daily_refresh'}
    seen = {x['name'] for x in out}
    for x in discovered(known):
        if x['name'] not in seen:
            out.append(x)
    return out



def newest(paths):
    """The mtime of the most recently written file in a stream, as a timestamp.

    ELAPSED IS NOT ACTIVITY, and the first version of this page only showed elapsed. The
    caption backfill reads '1d 8h' because that wrapper has been alive since Thursday --
    it says nothing about whether anything has landed, and the wrapper spends most of its
    life asleep in a backoff. What a reader actually wants is when this stream last
    PRODUCED something, which is the newest file it owns.
    """
    # BOTH TREES. The 7am refresh runs in ../lunenburgbudgets-refresh and commits from
    # there, so a stream it drives looks hours stale here until the next pull. The work
    # happened; this tree just has not seen it yet.
    best = 0
    pats = list(paths) + [q.replace(ROOT, TREE, 1) for q in paths if os.path.isdir(TREE)]
    for pat in pats:
        for f in glob.glob(pat):
            try:
                m = os.path.getmtime(f)
            except OSError:
                continue
            if m > best:
                best = m
    if not best:
        return ''
    return dt.datetime.fromtimestamp(best, dt.timezone.utc).isoformat()


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


def register_split(want, have_dir, keep=None):
    """(meetings with a file, meetings without) -- ONE GRAIN, from ONE join.

    BOTH SIDES COME OUT OF HERE BECAUSE THE CARD ADDS THEM. TJ, reading the votes card:
    *"i see `1,828 of 4,515 sets of the town's minutes processed`"* -- and 4,515 is not a
    quantity. It was `done + todo` where `done` counted FILES, one per minutes DOCUMENT,
    and `todo` counted MEETINGS out of the register. 198 dates hold more than one set of
    minutes (Planning Board 2022-10-24 holds five), so the two diverge, and their sum is
    documents plus meetings: neither of the three real denominators, which are 4,702
    documents, 4,428 distinct board-and-date among them, and 4,438 register meetings.

    The comment this replaces had already caught a symptom -- `1,201 in the pill and
    1,206 in the table` -- and fixed it by trusting the pending side and leaving `done` a
    file count. That kept the two figures from disagreeing with each other and let their
    TOTAL be wrong instead. Counting both from one join is what actually closes it: the
    sum is the register's own figure by construction.

    The document count is not lost -- the card states it as a note, because `how many
    files did we write` and `how many meetings are covered` are both worth knowing and
    must never be added together.
    """
    have = {os.path.relpath(p, os.path.join(DATA, have_dir))[:-5].split('/')[0] + '|' +
            os.path.basename(p)[:10]
            for p in glob.glob(os.path.join(DATA, have_dir, '*', '*.json'))
            if keep is None or keep(p)}
    covered, out = 0, []
    for r in rows('meeting-register.csv'):
        if r.get('part_of') or not want(r):
            continue
        if '%s|%s' % (r['board_slug'], r['date']) in have:
            covered += 1
            continue
        out.append((r['board_slug'], r['date']))
    return covered, group(out)


def register_pending(want, have_dir):
    """Just the pending half, for callers that do not state a total."""
    return register_split(want, have_dir)[1]



def annual_report_pages():
    """Financial pages of the annual reports, by SUBJECT, and whether anything read them.

    TJ: "I want ot know what is in them and what can be processed from them. So on the
    backlog, break down the annual report info into the particular data sets that can be
    extracted."

    The other extraction card counts ROWS in datasets that already exist, which means a
    table nobody has written an extractor for contributes nothing to it and is invisible.
    That is how a better stabilization table sat unread in the same reports for weeks. This
    card counts PAGES and groups them by what is printed on them, so the queue includes
    the work nobody has started.
    """
    f = os.path.join(DATA, 'annual-report-pages.csv')
    if not os.path.exists(f):
        return 0, 0, 0, 0, 0, 0, []
    # REMAINING WORK IS FOUR DIFFERENT JOBS AND THE COUNT MUST SAY WHICH. ONE OF THEM
    # COSTS MODEL TOKENS AND THE OTHERS DO NOT.
    #
    # TJ, 27 September 2026, after the number moved three times in one day: *"i think we
    # need a different metric then. read and refused as separate? (refused need to be...
    # rerun?!)"* A refused page must never be rerun -- it returns the same refusal and pays
    # for it -- and that this card made rerunning look like the remedy is the clearest
    # evidence `N left` was the wrong figure rather than merely a noisy one.
    #
    # `done` is now PROVEN: the page's rows tie to a total the page itself prints. It is
    # lower than the `read` it replaces, and deliberately: `read` meant any dataset cites
    # this page, which is a fact about our FILING and moved twice in a day in both
    # directions without the archive changing. See PROOF in map_annual_report_pages.py.
    done, refused, unread, unproven, reversed_, blocked, todo = 0, 0, 0, 0, 0, 0, []
    for r in rows('annual-report-pages.csv'):
        st = r.get('state')
        if st == 'proven':
            done += 1
            continue
        label = r.get('subject') or 'unknown'
        if st == 'reversed':
            reversed_ += 1
            label += ' \u2014 needs re-OCR'
        elif st == 'refused':
            refused += 1
            label += ' \u2014 read & REFUSED, fix the extractor (code)'
        elif st == 'unproven':
            unproven += 1
            label += ' \u2014 rows exist, UNPROVEN, write the check (code)'
        elif st == 'blocked':
            # NOT UNREAD. A blocked page is one somebody HAS looked at and cannot read --
            # FY2023 p25 is stored at 93 dpi with about 150 line items on it -- and it fell
            # into the `else` here, which labels a page `not yet read (TOKENS)`. That is the
            # exact opposite of true: it is the one state model spend cannot move.
            # AND IT IS NOT OUTSTANDING WORK EITHER, so it does not join `todo`. It was
            # counted in BOTH, which made this card contradict itself: the headline said
            # `0 of 511 pages unfinished` while the bar, fed todo=3, drew amber -- one
            # number saying finished and the colour beside it saying not. TJ saw the bar
            # and asked whether it was done. A page nobody can read is reported in its own
            # colour and its own count, never as a backlog somebody could clear.
            blocked += 1
            continue
        else:
            unread += 1
            label += ' \u2014 not yet read (TOKENS)'
        todo.append((label, '%s-06-30' % r['fy']))
    out = group(todo)
    for g in out:
        g['dates'] = ['%s (%s)' % (d, '{:,}'.format(n))
                      for d, n in sorted(collections.Counter(g['dates']).items())]
    # IN PRIORITY ORDER, NOT BY SIZE. `group()` sorts by how many are left, which puts
    # the 73 unclassifiable pages at the top of a queue whose whole point is what to do
    # next. The map ranks the subjects by what extracting them would ANSWER, and that is
    # the order a reader wants.
    rank = {}
    for r in rows('annual-report-pages.csv'):
        try:
            rank[r['subject']] = int(r['priority'])
        except (KeyError, TypeError, ValueError):
            continue
    for g in out:
        g['rank'] = rank.get(g['board'].split(' (')[0], 99)
    out.sort(key=lambda g: (g['rank'], -g['n']))
    return done, refused, unproven, unread, reversed_, blocked, out


def first_class_today(as_of=None):
    """[(label, n)] for the latest refresh run -- ONLY the objects with a count.

    THE COLUMNS ARE REFRESH.PY'S OWN. It writes one `new_<object>` column per first-class
    document class, so this reads whatever it wrote rather than keeping a second list that
    would drift apart from it.

    ONLY NON-ZEROES. TJ, 29 September 2026: *"you can only show non-0s"*. Fifteen rows of
    which thirteen read zero is not a status, it is a table of things that did not happen,
    and the two that did are lost in it. A day on which nothing arrived says so in one
    line instead.
    """
    runs = rows('refresh-runs.csv')
    if not runs:
        return None
    last = sorted(runs, key=lambda r: r.get('as_of') or '')[-1]
    # AND IT MUST BE THE DAY THE CARD IS ABOUT. This panel is headed `Today's run` and was
    # rendering the LAST row whatever its date, so on 29 September 2026 it showed the 28th's
    # three documents under today's heading -- today's row being in origin/main, one commit
    # ahead of this tree. A stale figure under a dated heading is worse than no figure:
    # nothing about it looks wrong. None means `this day has no row`, which the caller says
    # out loud.
    if as_of and (last.get('as_of') or '') != as_of:
        return None
    # Rows written before 29 September 2026 use the older, shorter column names. Mapped
    # rather than dropped, so yesterday's run still reads as a run.
    WAS = {'minutes': 'official minutes', 'our_minutes': 'generated minutes'}
    out = []
    for col, v in last.items():
        if not col.startswith('new_'):
            continue
        try:
            n = int(v or 0)
        except ValueError:
            continue
        if not n:
            continue
        key = col[4:]
        label = WAS.get(key, key.replace('_', ' '))
        if n == 1:                       # `1 videos` reads like a bug in the dashboard
            label = {'analyses': 'analysis'}.get(label, label[:-1] if label.endswith('s')
                                                 and not label.endswith('ss') else label)
        out.append((label, n))
    return sorted(out, key=lambda t: -t[1])


def annual_reports_whole():
    """The sixteen annual town reports, counted as REPORTS rather than as pages.

    TJ, 28 September 2026: *"can you add a row for `total annual reports`. I want to see how
    many annual reports we have fully ingested vs partially vs none."*

    The page card beside this one answers *how much work is left*; this one answers *how far
    through the archive are we*, and they are different questions with different shapes. 244
    pages proven out of 484 reads as half done. It is not half done in the sense that
    matters: three reports are FINISHED and twelve are part-read, and a report you can quote
    end to end is worth more than the same number of pages scattered across twelve.

    A report is FINISHED when nothing is left that anybody could do -- every page proven, or
    proven except pages that CANNOT be read. FY2023 is finished with one blocked page on it,
    and calling it unfinished for ever would be the same mistake `blocked` exists to fix.
    """
    f = os.path.join(DATA, 'annual-report-pages.csv')
    if not os.path.exists(f):
        return 0, 0, 0, []
    by = collections.defaultdict(collections.Counter)
    for r in rows('annual-report-pages.csv'):
        by[r.get('fy')][r.get('state')] += 1
    done = part = none = 0
    pending = []
    for fy, c in sorted(by.items()):
        left = c['unproven'] + c['refused'] + c['unread'] + c['reversed']
        if not left:
            done += 1
            continue
        if c['proven']:
            part += 1
            what = '%d of %d pages proven' % (c['proven'], sum(c.values()))
        else:
            none += 1
            what = 'nothing proven yet, %d pages' % sum(c.values())
        pending.append(('FY%s \u2014 %s' % (fy, what), '%s-06-30' % fy))
    out = group(pending)
    for g in out:
        g['dates'] = ['%s (%s)' % (d, '{:,}'.format(n))
                      for d, n in sorted(collections.Counter(g['dates']).items())]
    return done, part, none, out


def extraction_pending():
    """The annual-report tables: rows READ against rows the document's OWN total proves.

    THIS IS NOT A claude -p STREAM AND IT IS THE LARGEST BACKLOG HERE. TJ, 20 September
    2026, after the stabilization history turned out to be unusable only because he asked
    for it: "we need to surface these gaps so I dont find them with questions like this."
    A dashboard that lists only the streams that cost allowance money is a dashboard that
    hides the free work, and the free work is where the data is.

    The grain is (dataset, fiscal year), because that is the unit somebody sits down and
    fixes: one table family in one annual report. `status='checked'` means the extract
    reconciles to a figure the report itself prints -- rule 13's `column_meaning`
    discipline -- and everything else is read but unproven.

    Counted out of the database rather than off the CSVs so the numbers move the day an
    extractor improves, not the day somebody remembers to update a note.
    """
    db = os.path.join(DATA, 'lunenburg.db')
    if not os.path.exists(db):
        return 0, []
    con = sqlite3.connect('file:%s?mode=ro' % db, uri=True)
    done, pend = 0, []
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' "
                            "AND name LIKE 'report_%' ORDER BY name"):
        cols = {r[1] for r in con.execute('PRAGMA table_info("%s")' % t)}
        if 'status' not in cols or 'fy' not in cols:
            continue
        label = t[len('report_'):].replace('_', ' ')
        for fy, n, ok in con.execute(
                'SELECT fy, COUNT(*), SUM(CASE WHEN status=\'checked\' THEN 1 ELSE 0 END) '
                'FROM "%s" GROUP BY fy' % t):
            done += ok or 0
            if not fy:
                continue
            pend += [(label, '%d-06-30' % int(fy))] * ((n or 0) - (ok or 0))
    con.close()
    out = group(pend)
    # ONE ENTRY PER FISCAL YEAR, NOT ONE PER ROW. Every other stream's date list is one
    # meeting each, so printing them all is the breakdown. Here a dataset holds thousands
    # of rows sharing fifteen fiscal years, and the raw list prints 2011-06-30 four
    # hundred times -- which is noise wearing the costume of detail.
    for r in out:
        r['dates'] = ['%s (%s)' % (d, '{:,}'.format(n))
                      for d, n in sorted(collections.Counter(r['dates']).items())]
    return done, out


# ------------------------------------------------------------------- the streams
# WHAT THE COST COLUMN MEANS, because `free` was answering the wrong question.
#
# TJ, 27 September 2026: *"I don't know what batch free means"*, and then: *"update the
# dash for the real cost"*. He was right to push. The column said `free` for the streams
# that call no model, which is true about RUNNING the job and says nothing about the cost
# of GETTING IT DONE -- and the free streams are precisely the ones with no process behind
# them, so a person or an agent has to sit and do them. This week that was the larger
# number by far: the unattended streams read about 1,000 items for roughly 10% of the
# weekly allowance, while the attended work took roughly 40%.
#
# So the column now states two things: what one item costs to run, and WHO HAS TO BE
# THERE. `unattended` is the cheap word. `needs a session` is the expensive one.
def _counted(n, unit, total=None, remaining=False):
    """A figure with its UNIT, never bare.

    TJ, 27 September 2026, after the page queue had spent a day saying `459 done` and a
    reader could not tell what had been done to what: *"we need units on the numbers...
    numbers need to mean numbers"*. This is rule 7b applied to the dashboard: a bare number
    in a stat box is exactly the figure somebody quotes, and ten children, ten documents
    and ten budget lines must not look alike.

    `total` renders `459 of 474`, which is the form that cannot be misread as a rate.
    """
    if n is None:
        return 'unknown'
    unit = unit or ('item', 'items', 'items')
    # index 2 is the REMAINING phrase, and it is a different sentence about a different
    # set: `15 pages with proven rows left` said the opposite of the truth about those
    # fifteen pages, which have no proven rows at all and are why the queue is not empty.
    word = unit[2] if remaining else unit[0 if n == 1 else 1]
    if total:
        return '%s of %s %s' % ('{:,}'.format(n), '{:,}'.format(total), word)
    return '%s %s' % ('{:,}'.format(n), word)


# THE AG'S OPEN MEETING LAW DETERMINATIONS. TJ, 9 October 2026: put the download on the
# dashboard -- running, a burndown, and completion overall.
#
# THE DENOMINATOR IS THE PORTAL'S OWN LIST, not the walk. `fetch_oml_determinations.py
# --all` walks numbers and only learns a year has ended after 25 empty ones, so it cannot
# say how many are left. `--census` asks the portal `OML <year>*` and gets every number it
# lists -- one call a year, nothing downloaded -- into build/oml-census.json. Refreshed here
# when it is over six hours old, because the AG keeps issuing letters this year.
#
# THE BURNDOWN IS TIMED FROM THE BUCKET, not from file mtimes: archive-push-state.csv
# records when each letter was read back from R2 and compared, which is the moment it was
# actually secured.
OML_JOB = 'Downloading the AG’s Open Meeting Law determinations'
OML_CENSUS = os.path.join(ROOT, 'build', 'oml-census.json')
OML_LOG = os.path.join(ROOT, 'build', 'oml-determinations-all.log')
OML_INDEX = os.path.join(ROOT, 'sources', 'state-law', 'index.csv')


def _local(stamp):
    """A push-state timestamp as naive LOCAL time. Two writers, two conventions:
    sync_archive.py writes UTC with a trailing Z, ingest.py writes local time with none."""
    if stamp.endswith('Z'):
        return (dt.datetime.strptime(stamp, '%Y-%m-%dT%H:%M:%SZ')
                .replace(tzinfo=dt.timezone.utc).astimezone().replace(tzinfo=None))
    return dt.datetime.fromisoformat(stamp)


@once
def oml_progress():
    try:
        age = time.time() - os.path.getmtime(OML_CENSUS)
    except OSError:
        age = None
    if age is None or age > 6 * 3600:
        try:
            subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'fetch_oml_determinations.py'),
                            '--census'], cwd=ROOT, timeout=120, capture_output=True)
        except Exception:
            pass
    try:
        cen = json.load(open(OML_CENSUS))
    except Exception:
        return None
    listed = {(int(y), n) for y, v in cen['years'].items() for n in v['numbers']}
    held = set()
    try:
        for r in csv.DictReader(open(OML_INDEX, encoding='utf-8')):
            m = re.match(r'oml-det-(\d{4})-(\d+)', r['id'])
            if m:
                held.add((int(m.group(1)), int(m.group(2))))
    except OSError:
        pass
    got = held & listed
    # when each was secured
    when = {}
    for r in rows('archive-push-state.csv'):
        k = r.get('key') or ''
        m = re.search(r'/determinations/.*?oml-(\d{4})-(\d+)', k)
        if m and r.get('verified_at'):
            yn = (int(m.group(1)), int(m.group(2)))
            t = _local(r['verified_at'])
            if yn in listed and (yn not in when or t < when[yn]):
                when[yn] = t
    times = sorted(when.values())
    years = []
    for y in sorted(cen['years']):
        nums = cen['years'][y]['numbers']
        h = sum(1 for n in nums if (int(y), n) in held)
        years.append(dict(year=y, listed=len(nums), held=h,
                          missing=[n for n in nums if (int(y), n) not in held],
                          truncated=cen['years'][y].get('truncated')))
    # where the walk is, and how fast -- the last 30 minutes of bucket timestamps
    pos, failed = '', 0
    try:
        lines = open(OML_LOG, encoding='utf-8', errors='replace').read().splitlines()
        oks = [l for l in lines if l.startswith('  ok OML')]
        pos = oks[-1].split()[1] + ' ' + oks[-1].split()[2] if oks else ''
        failed = sum(1 for l in lines if l.startswith('  !!'))
    except OSError:
        pass
    cut = dt.datetime.now() - dt.timedelta(minutes=30)
    recent = sum(1 for t in times if t >= cut)
    rate = recent * 2.0                         # per hour
    left = len(listed) - len(got)
    eta = ('about %.1f hours to go at that pace (an estimate, not a schedule)' % (left / rate)
           if rate and left else '')
    line = ' &middot; '.join(x for x in (
        ('last landed <b>%s</b>' % pos) if pos else '',
        '%d in the last 30 minutes' % recent, eta,
        ('<span style="color:#f85149">%d failed lines in the log</span>' % failed) if failed else ''
    ) if x)
    return dict(listed=len(listed), held=len(got), left=left, years=years, times=times,
                asked=cen.get('asked', ''), running_line=line, rate=rate)


def oml_chart(o):
    """Two panels, one measure each (never two y-scales on one): what is left over time,
    and what is held of each year's list."""
    if not o:
        return ''
    out = ['<div style="display:flex;gap:18px;flex-wrap:wrap;margin-top:10px">']
    # --- burndown: letters left, over clock time
    W, H, L, R, T, B = 460, 170, 40, 10, 14, 24
    total = o['listed']
    pts = []
    for i, t in enumerate(o['times']):
        pts.append((t, total - (i + 1)))
    # THIS RUN, NOT THE WHOLE HISTORY. The fourteen chosen letters landed the evening
    # before the walk, and the walk itself stopped overnight on OML 2012-5, so an axis from
    # the first letter is mostly a flat line across hours nobody was fetching. The axis
    # starts after the last pause of over an hour; what was held before it is the level
    # the line starts from, and the caption says so.
    before = 0
    for i in range(len(pts) - 1, 0, -1):
        if (pts[i][0] - pts[i - 1][0]).total_seconds() > 3600:
            before, pts = i, pts[i:]
            break
    if pts:
        t0 = pts[0][0]
        t1 = max(dt.datetime.now(), pts[-1][0])
        span = max((t1 - t0).total_seconds(), 60)
        def X(t):
            return L + (W - L - R) * (t - t0).total_seconds() / span
        def Y(v):
            return T + (H - T - B) * (1 - v / float(total))
        step = max(1, len(pts) // 300)
        keep = pts[::step] + [pts[-1]]
        poly = ' '.join('%.1f,%.1f' % (X(t), Y(v)) for t, v in keep)
        svg = ['<svg viewBox="0 0 %d %d" width="%d" height="%d" style="max-width:100%%">' % (W, H, W, H)]
        for v in (0, total // 2, total):
            svg.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#21262d"/>'
                       '<text x="%d" y="%.1f" fill="#8b949e" font-size="10" text-anchor="end">%s</text>'
                       % (L, W - R, Y(v), Y(v), L - 4, Y(v) + 3, '{:,}'.format(v)))
        svg.append('<polyline points="%s" fill="none" stroke="#d29922" stroke-width="2"/>' % poly)
        for t, v in keep[::max(1, len(keep) // 40)] + [keep[-1]]:
            svg.append('<circle cx="%.1f" cy="%.1f" r="7" fill="transparent"><title>%s: %s left</title></circle>'
                       % (X(t), Y(v), t.strftime('%a %H:%M'), '{:,}'.format(v)))
        for when, anchor, x in ((t0, 'start', L), (t1, 'end', W - R)):
            svg.append('<text x="%d" y="%d" fill="#8b949e" font-size="10" text-anchor="%s">%s</text>'
                       % (x, H - 6, anchor, when.strftime('%a %H:%M')))
        svg.append('</svg>')
        out.append('<div style="width:%dpx;max-width:100%%"><div class="tiny" style="margin-bottom:2px">'
                   '<b>Letters still to fetch</b>, by when each was secured in the bucket &mdash; '
                   'this run, since %s%s</div>%s</div>'
                   % (W, pts[0][0].strftime('%a %H:%M'),
                      ('; %d were held before it' % before) if before else '', ''.join(svg)))
    # --- by year: held of the portal's list
    ys = o['years']
    W2, H2, B2, T2 = 460, 170, 24, 14
    mx = max(y['listed'] for y in ys) or 1
    bw = (W2 - 10) / float(len(ys)) - 3
    svg = ['<svg viewBox="0 0 %d %d" width="%d" height="%d" style="max-width:100%%">' % (W2, H2, W2, H2)]
    for i, y in enumerate(ys):
        x = 5 + i * (bw + 3)
        full = (H2 - T2 - B2) * y['listed'] / float(mx)
        hh = full * y['held'] / float(y['listed'] or 1)
        tip = '%s: %d of %d held, %d to fetch' % (y['year'], y['held'], y['listed'], y['listed'] - y['held'])
        done = y['held'] >= y['listed']
        svg.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2" fill="#21262d"><title>%s</title></rect>'
                   % (x, H2 - B2 - full, bw, full, tip))
        if hh:
            svg.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2" fill="%s"><title>%s</title></rect>'
                       % (x, H2 - B2 - hh, bw, hh, '#3fb950' if done else '#d29922', tip))
        svg.append('<text x="%.1f" y="%d" fill="#8b949e" font-size="9.5" text-anchor="middle">’%s</text>'
                   % (x + bw / 2, H2 - B2 + 12, y['year'][-2:]))
        svg.append('<text x="%.1f" y="%.1f" fill="#8b949e" font-size="9" text-anchor="middle">%d</text>'
                   % (x + bw / 2, H2 - B2 - full - 3, y['listed']))
    svg.append('</svg>')
    out.append('<div style="width:%dpx;max-width:100%%"><div class="tiny" style="margin-bottom:2px"><b>By year of the letter</b> &mdash; '
               '<span style="color:#3fb950">&#9632;</span> year complete '
               '<span style="color:#d29922">&#9632;</span> held '
               '<span style="color:#6e7681">&#9632;</span> still to fetch; the number on top is '
               'how many the portal lists</div>%s</div>' % (W2, ''.join(svg)))
    out.append('</div>')
    return ''.join(out)


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
    s.append(dict(key='captions', unit=('recording with captions held', 'recordings with captions held', 'recordings still to fetch'), name='Captions for recordings',
                  io='in: the town’s YouTube channel &rarr; out: a timed transcript — a finding aid, never a source',
                  done=len(have), todo=todo,
                  blocked=len(dead), blocked_why='captions disabled by the publisher',
                  cost='no model, runs by itself \u2014 throttled by YouTube',
                  last=ago(newest([os.path.join(DATA, 'youtube-transcripts', '*', '*')])),
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
    s.append(dict(key='ocr', unit=('scanned set of minutes read', 'scanned sets of minutes read', 'scans still to read'), name='OCR of scanned minutes',
                  io='in: minutes the town posted as page images &rarr; out: text a search and the vote reader can read',
                  done=len(ocr), todo=left,
                  blocked=0, blocked_why='', cost='no model, runs by itself \u2014 macOS Vision, local',
                  last=ago(newest([os.path.join(DATA, 'ocr-minutes.csv')])),
                  note='a scan is invisible to search and to the vote reader until this runs',
                  pending=[]))

    # VOTES and OUR MINUTES: count files, and take the denominator from the register.
    # THE HEADLINE IS THE SUM OF THE BREAKDOWN, always. Computing the two separately is
    # what put 1,201 in the pill and 1,206 in the table beneath it -- five meetings whose
    # file exists but whose register row no longer matches it. That difference is worth
    # finding, and it is not worth guessing at from a dashboard, so the page states the
    # one figure it can stand behind: how many meetings have no file.
    # DONE MEANS STRUCTURED (TJ, 6 October 2026). A meeting counts as processed only once its
    # official minutes have the schema-2 read; one read for votes only is still to do, and
    # the card says how many of the to-do are that, so the dual state is visible.
    def structured(p):
        return '"schema": 2' in open(p, encoding='utf-8').read()
    v_done, vp = register_split(lambda r: r.get('minutes') == '1', 'official-votes', keep=structured)
    v_any, _ = register_split(lambda r: r.get('minutes') == '1', 'official-votes')
    v_votes_only = v_any - v_done
    # NAMED FOR WHAT IT PRODUCES, WHICH IS ONLY VOTES. TJ, 19 September 2026: "why do you
    # call it 'Votes from the town's minutes'? I assume this means 'Our own minutes'
    # because its more than votes isnt it that we're processing for?" -- a fair reading,
    # and the answer is no: these are two different streams over two different inputs, and
    # the cards did not say so. This one reads the minutes THE TOWN PUBLISHED and takes
    # votes out of them, each with a verbatim quote. The other writes OUR minutes from OUR
    # captions of a recording, and that one is the full record -- decisions, transfers,
    # topics, public comment, budget items -- of which votes are one part. Every card now
    # prints its input and its output, because a label alone could not carry the
    # distinction and the distinction is the whole point (rule 13: ours and theirs).
    # NAMED FOR THE DOCUMENT, NOT FOR WHAT WE CURRENTLY TAKE OUT OF IT. TJ raised this on
    # 19 September and again on 28 September: *"why are you so focused on votes? We process
    # OFFICIAL minutes and we create our own minutes. votes is ONE PIECE of what the
    # minutes have in them."*
    #
    # The first answer was that the stream really does produce only votes, and every card
    # was given an input and an output line so the two streams could be told apart. That
    # was true and it missed the point. A set of the town's minutes holds decisions,
    # transfers, appointments, public comment; votes are all we EXTRACT today, which is a
    # limitation of our reader and not a description of the document. Calling the stream
    # `Votes` put that limitation in the name, where it reads as the definition -- and made
    # a backlog of 3,041 DOCUMENTS look like a vote tally.
    #
    # So the name is the document and the output line says what we take from it, with
    # `today` doing real work: it marks the gap rather than hiding it.
    s.append(dict(key='votes', unit=('set of the town’s minutes processed', 'sets of the town’s minutes processed', 'sets of the town’s minutes still to process'), name='The town’s OFFICIAL minutes',
                  io='in: the minutes the town published, whose TEXT is already '
                     'extracted and searchable &rarr; out: the whole meeting as the town '
                     'recorded it &mdash; attendees, votes, decisions, budget items, '
                     'transfers, public comment, topics &mdash; each item quoted verbatim. '
                     '<b>%s of the meetings still to process were read for VOTES ONLY</b> '
                     'before 6 October 2026 and wait to be re-read structured; the rest have '
                     'never been read' % '{:,}'.format(v_votes_only),
                  done=v_done,
                  todo=sum(p['n'] for p in vp), blocked=0, blocked_why='',
                  # DERIVED, NOT TYPED. This said `~0.03% of the week each` and the
                  # measured figure is <=0.0193% -- a 35-55% overstatement in the number
                  # anybody sizes a batch against. Every vote file carries its own
                  # `cost_usd`; see notes/findings/METERED-BATCH-COST.md.
                  cost=COST.phrase('official-votes', 'structured read not yet priced', schema=2)
                       + ' &middot; %s vote files '
                       'written, one per minutes DOCUMENT; 198 dates hold more than one '
                       'set, so files and meetings are different counts and are never '
                       'added' % '{:,}'.format(
                           len(glob.glob(os.path.join(DATA, 'official-votes', '*', '*.json')))),
                  last=ago(newest([os.path.join(DATA, 'official-votes', '*', '*.json')])), note='every vote carries a quote checked verbatim against the minutes',
                  pending=vp))
    m_done, mp = register_split(lambda r: bool(r.get('transcript_paths')), 'recording-minutes')
    s.append(dict(key='ourminutes', unit=('recording written up', 'recordings written up', 'recordings still to write up'), name='OUR minutes, written from the recordings',
                  io='in: our machine captions of a video &rarr; out: the whole meeting — decisions, '
                     'votes, transfers, budget items, topics, public comment',
                  done=m_done,
                  todo=sum(p['n'] for p in mp), blocked=0, blocked_why='',
                  cost=COST.phrase('recording-minutes', '~0.09% of the week each, runs by itself')
                       + ' &middot; %s files written, '
                       'one per RECORDING' % '{:,}'.format(
                           len(glob.glob(os.path.join(DATA, 'recording-minutes', '*', '*.json')))),
                  last=ago(newest([os.path.join(DATA, 'recording-minutes', '*', '*.json')])), note='written from our captions; two derived layers from the meeting',
                  pending=mp))
    o = oml_progress()
    if o:
        s.append(dict(key='oml', unit=('determination letter held', 'determination letters held',
                                       'determination letters still to fetch'),
                      name='The AG’s Open Meeting Law determinations',
                      io='in: the Attorney General’s determination lookup, walked number by number '
                         '&rarr; out: every letter, in the bucket, with its text. Download only '
                         '&mdash; nothing reads them yet (TJ, 8 October 2026)',
                      done=o['held'], todo=o['left'], blocked=0, blocked_why='',
                      cost='no model — plain downloads from the AG’s portal, paced half a second apart',
                      last=ago(newest([os.path.join(ROOT, 'sources', 'state-law', '*', 'determinations', '*.pdf')])),
                      note='the total is what the portal itself lists, %s determination numbers, counted %s'
                           % ('{:,}'.format(o['listed']), o['asked'].replace('T', ' ')[:16]),
                      chart=oml_chart(o),
                      pending=[dict(board='%s letters' % y['year'], n=len(y['missing']),
                                    first='OML %s-%d' % (y['year'], y['missing'][0]),
                                    last='OML %s-%d' % (y['year'], y['missing'][-1]),
                                    dates=['%d' % n for n in y['missing']])
                               for y in reversed(o['years']) if y['missing']]))

    # THE ANNUAL REPORTS. Free, ours, and the biggest pile in the project.
    ex_done, ex_pend = extraction_pending()
    s.append(dict(key='extraction', unit=('row that ties to a printed total', 'rows that tie to a printed total', 'rows still to reconcile'), name='Reconciling the annual-report tables',
                  io='in: sixteen annual town reports, read page by page &rarr; out: rows tied to a total the report itself prints',
                  done=ex_done, todo=sum(p['n'] for p in ex_pend),
                  blocked=0, blocked_why='', cost='~0.12% of the week a page if run on its own; far more if done in a conversation',
                  last=ago(newest([os.path.join(DATA, 'lunenburg.db')])),
                  note='a row that does not reconcile is read, not proven; nothing may be '
                       'aggregated across the two',
                  pending=ex_pend))

    # THE ANNUAL REPORTS, BY WHAT IS ON THE PAGE. Counted from the pages rather than from
    # the datasets, so a table with no extractor yet is in the queue instead of absent
    # from it.
    (ar_done, ar_refused, ar_unproven, ar_unread, ar_reversed, ar_blocked,
     ar_todo) = annual_report_pages()

    # THE WHOLE REPORTS, beside the pages. A report finished end to end is a different
    # thing from the same number of pages scattered across twelve of them, and the page
    # card cannot say which you have.
    rep_done, rep_part, rep_none, rep_todo = annual_reports_whole()
    if rep_done or rep_part or rep_none:
        s.append(dict(key='annualreports', name='Annual reports, finished end to end',
                      unit=('annual report read end to end',
                            'annual reports read end to end',
                            'reports with pages still to do'),
                      headline=_counted(rep_part + rep_none,
                                        ('report not finished',
                                         'reports not finished',
                                         'reports not finished'),
                                        total=rep_done + rep_part + rep_none),
                      pill=(_counted(rep_done, ('report FINISHED',
                                                'reports FINISHED',
                                                'reports FINISHED'))
                            if rep_done else 'no report finished yet'),
                      breakdown=[
                          ('FINISHED', rep_done,
                           'every page proven, or proven but for pages that cannot be read',
                           'done'),
                          ('PART-READ', rep_part,
                           'some pages proven, some still to do',
                           'finish the year, section by section'),
                          ('NOT STARTED', rep_none,
                           'no page in the report proves yet',
                           'start the year'),
                      ],
                      io='in: 15 annual town reports &rarr; out: reports a resident can '
                         'quote end to end',
                      done=rep_done, todo=rep_part + rep_none,
                      blocked=0, blocked_why='',
                      cost='a year at a time, section by section \u2014 see '
                           'notes/process/READING-A-REPORT-PAGE.md',
                      last=ago(newest([os.path.join(DATA, 'annual-report-pages.csv')])),
                      note='A REPORT IS FINISHED WHEN NOTHING IS LEFT THAT ANYBODY COULD '
                           'DO \u2014 a page nobody CAN read does not hold a year open for '
                           'ever. FY2023 is finished with one such page on it',
                      pending=rep_todo))
    if ar_done or ar_todo:
        # THE UPPER METRIC IS UNFINISHED, AND THE PANEL ITEMISES IT. TJ, 27 September
        # 2026: *"the upper metric for that annual report page needs to be 'unfinished'
        # with an itemized breakdown inside the panel with these specific terms"*.
        #
        # Right, and for a reason the other five streams do not have: the remainder here
        # is FOUR different jobs and only one of them costs model tokens. A headline
        # counting what is DONE has to pick one definition of done, and every choice was
        # wrong -- `read` drifted with our filing, `proven` is honest and reads as though
        # 312 pages were unstarted. `unfinished` is the one figure that is true whichever
        # job you mean, and the itemisation below is where the four terms say which.
        # BLOCKED IS NOT IN THE UNFINISHED COUNT. Unfinished means work somebody could
        # do; a page nobody CAN read is not waiting on anybody. It is shown in the
        # breakdown and in `blocked` so it never simply disappears.
        ar_unfinished = ar_refused + ar_unproven + ar_unread + ar_reversed
        s.append(dict(key='annualpages', unit=('page whose rows PROVE against its own printed total', 'pages whose rows PROVE against their own printed total', 'pages not yet proven'),
                      headline=_counted(ar_unfinished,
                                        ('page unfinished', 'pages unfinished',
                                         'pages unfinished'),
                                        total=ar_done + ar_unfinished),
                      # THE PILL CARRIES THE ONLY FIGURE SPEND CAN MOVE. Everything else
                      # left on this stream is code, and `312 left` beside a token cost is
                      # what invited rerunning a refused page.
                      pill=('nothing left to READ &mdash; every unfinished page is code'
                            if not ar_unread else
                            _counted(ar_unread, ('page still to read',
                                                 'pages still to read',
                                                 'pages still to read'))),
                      breakdown=[
                          ('PROVEN', ar_done, 'rows tie to a total the page prints',
                           'done'),
                          ('UNPROVEN', ar_unproven,
                           'rows exist, nothing recorded a check',
                           'write the check &mdash; code'),
                          ('REFUSED', ar_refused,
                           'an extractor reached it and wrote nothing, with a reason',
                           'fix the extractor &mdash; code'),
                          ('UNREAD', ar_unread, 'nobody has looked',
                           'read it &mdash; THE ONLY ONE THAT COSTS TOKENS'),
                          ('reversed', ar_reversed,
                           'the OCR of the page came out mirrored', 're-OCR it &mdash; '
                           'free, background'),
                          ('BLOCKED', ar_blocked,
                           'somebody looked and the page cannot be read at all',
                           'nothing here &mdash; and for 2 of the 3 a better scan is NOT the '
                           'remedy: the TOWN did not print the figures'),
                      ], name='Annual report pages, by what is on them',
                      io='in: 15 annual town reports, page by page &rarr; out: the tables '
                         'nobody has extracted yet, grouped by subject',
                      done=ar_done, todo=sum(p['n'] for p in ar_todo),
                      blocked=ar_blocked,
                      blocked_why=('CLOSED, not outstanding. Somebody read these and '
                                   'could not: one is a 93 dpi scan, two the town '
                                   'printed short. sources/data/page-blocked.csv'),
                      cost='~0.12% of the week a page if run on its own; far more if done in a conversation',
                      last=ago(newest([os.path.join(DATA, 'annual-report-pages.csv')])),
                      # WHAT THE ITEMISATION BELOW CANNOT SAY. The four counts and their
                      # actions are rendered as rows, so repeating them here would be the
                      # block of context rule 7a exists to remove. What is left is the
                      # thing a reader has to be told rather than shown.
                      note='A REFUSED PAGE IS NEVER RERUN \u2014 it returns the same '
                           'refusal and pays a model for it. The subject is read off the '
                           'page\u2019s own headings and is a guess',
                      pending=ar_todo))

    bd = backlog_depth()
    if bd and bd.get('total_jobs'):
        # THE THREE STREAMS ARE NEVER SUMMED INTO ONE BAR. A vote extraction, a
        # reconciliation and a set of written minutes are three different pieces of work at
        # three different prices, and `reconcile` can only exist where a RECORDING exists --
        # so its zero before 2025 is the channel's start date and not neglect.
        # THE UNIT IS WHAT A JOB IS, NOT WHAT IT IS ABOUT. `votes` reads ONE FILE PER SET
        # OF MINUTES, so 3,041 is sets of minutes still to read -- a set may hold eight
        # votes or none. Labelled `the votes in the town's minutes` beside that figure it
        # read as a count of votes, which is the units failure rule 7b exists to stop:
        # ten children, ten documents and ten budget lines must not look alike.
        # NAME THE DOCUMENT AND THE WORK, NOT TODAY'S EXTRACTOR. TJ: *"why are you so
        # focused on votes? We process OFFICIAL minutes and we create our own minutes.
        # votes is ONE PIECE of what the minutes have in them."* Right -- the stream is
        # THE TOWN'S OFFICIAL MINUTES, PROCESSED; votes are what we happen to take out of
        # them today, and calling the stream `votes` framed a document-processing backlog
        # as a vote-counting one. The internal key stays `votes` because that is the
        # script; what a reader is shown is the document.
        what = {'official': 'meetings whose OFFICIAL minutes have never been read',
                'official-v1': 'meetings whose OFFICIAL minutes were read for votes only '
                               '\u2014 waiting to be re-read structured (attendees, '
                               'decisions, budget items, transfers, public comment, topics)',
                'reconcile': 'meetings where we hold both records and have not compared '
                             'ours against the town\u2019s',
                'minutes': 'recordings we have not yet written OUR minutes from'}
        stream_rows = []
        for st in bd['streams']:
            stream_rows.append((st['name'], st['jobs'], what.get(st['name'], ''),
                         ('~$%.2f a job' % st['unit_cost']) if st.get('unit_cost')
                         else 'no measured cost yet'))
        pend = [dict(board=r['fy'], n=r['total'], first='', last='',
                     dates=['%s %s' % (r[k], k) for k in ('official', 'official-v1', 'reconcile', 'minutes')
                            if r.get(k)])
                for r in reversed(bd.get('by_fiscal_year', [])) if r['total']]
        s.append(dict(
            key='backlogdepth',
            unit=('job off the backlog', 'jobs off the backlog', 'jobs left'),
            headline=_counted(bd['total_jobs'],
                              ('job in the backlog', 'jobs in the backlog',
                               'jobs in the backlog')),
            pill='by the MEETING\u2019s own date, not by when we found it',
            breakdown=stream_rows,
            name='How deep the backlog is, by fiscal year of the meeting',
            io='in: every outstanding machine-reading job &rarr; out: where it piles up, '
               'by the town\u2019s own dates',
            done=0, todo=bd['total_jobs'], blocked=0, blocked_why='',
            cost=('about $%s to clear, roughly %s of a week\u2019s allowance'
                  % (format(int(bd['estimated_usd']), ','), bd['estimated_weeks'])),
            last=ago(dt.datetime.now(dt.timezone.utc).isoformat()),   # computed this redraw
            note='Streams are counted separately and must never be added \u2014 '
                 '`reconcile` cannot exist before the recordings do, so its zero before '
                 'FY2025 is the channel\u2019s start date, not a gap. Falls on its own as '
                 'work comes off the queue',
            pending=pend))

    # THE DEPTH GOES FIRST ON A PAGE CALLED BACKLOG. It is the only panel that describes
    # the whole page rather than one stream, and appended in build order it landed at the
    # bottom, below six streams -- so the overview was the last thing a reader reached.
    # Rule 7a: the thing first.
    return sorted(s, key=lambda p: 0 if p['key'] == 'backlogdepth' else 1)



# -------------------------------------------------------- how deep the backlog is
#
# TJ, 28 September 2026: *"i want a visualization in the backlog that shows all the
# documents in the backlog and their MEETING DATE (NOT discover date) as a count. so i can
# see how deep the backlog is based on month+year, or a rollup per year, and the type."*
#
# WHY THE MEETING DATE. `first_seen` is when our crawler found a document and is the right
# key for deciding what is NEW. It is the wrong key for depth: discovery dates cluster on
# the days we happened to crawl, so a chart of them shows our crawling schedule rather than
# the town's record. The meeting date is the town's own and does not move.
#
# IT READS THE QUEUE, LIVE. It used to read the payload `build_backlog_depth.py` writes,
# which only the daily refresh rewrote -- on the reasoning that `sweep_backlog.jobs()` was
# too dear to run per redraw. Measured 6 October 2026: 1.3 seconds. And the cost of the
# shortcut was real: the refresh broke on 4 October and the chart sat on that morning's
# numbers for two days while a sweep cleared hundreds of jobs under it. TJ: *"it should
# pull from the source jobs directly."* So it computes the same payload from the same
# `gather()`, in memory, writing nothing; the file is only the fallback if that fails.
BACKLOG_DEPTH = os.path.join(ROOT, 'fy28', 'public', 'data', 'backlog-depth.json')


@once
def backlog_depth():
    try:
        import build_backlog_depth as B
        jobs, by_year, by_month, by_board = B.gather()
        return B.payload(jobs, by_year, by_month, by_board, B.unit_costs())
    except Exception as e:                      # the saved payload is the fallback
        print('backlog depth: live read failed (%s); using the saved payload' % e, file=sys.stderr)
    if not os.path.exists(BACKLOG_DEPTH):
        return None
    try:
        with open(BACKLOG_DEPTH, encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


# ------------------------------------------------------- the backlog, as a picture
#
# TJ, 28 September 2026: *"i wanted a chart. like a bar chart"* and *"put at the top"*.
# The first version of this was a table of counts inside a card, which is a breakdown and
# not a visualization -- the shape of a backlog is the thing to see, and a column of
# numbers makes the eye do the work a bar does for free.
#
# STACKED BY STREAM, ONE BAR PER FISCAL YEAR. The streams are never added into a single
# total bar, because a vote extraction, a reconciliation and a set of written minutes are
# three different jobs at three different prices -- but stacking them in one column is how
# the COMPOSITION of a year becomes visible, which is the question: FY2019 is votes,
# FY2024 is minutes, FY2026 is reconcile, and those are three different problems.
#
# Inline SVG, no library: this page is a local file opened from disk, and a chart that
# needed a CDN would be a blank rectangle the first time the machine was offline.
# THE TOWN'S MINUTES IN TWO SHADES OF ONE COLOUR (TJ, 6 October 2026): never read, and
# read for votes only. One kind of document in two states of processing, so one hue -- the
# pale one is the dual state that drains as meetings are re-read structured.
STREAM_COLOUR = [('official', '#6cb6ff'), ('official-v1', '#2f5d8a'), ('reconcile', '#d29922'),
                 ('minutes', '#a371f7')]

# MISSING RECORDS ARE NOT WORK, so they are never a STREAM colour. TJ, 7 October 2026:
# *"if we clear all work, i want to still visualize on this chart the ones that are missing
# and not yet available."* Drawn as their own hatched, neutral-grey segments stacked ABOVE
# the job stack on the same bar -- three hatch densities on one grey, not three hues, so the
# eye reads "this is not a coloured job" rather than "this is a fourth kind of job". Each
# tuple is (stream key, background shade, hatch-line spacing, hatch-line width); the same
# shade is reused for the legend swatch so the two match.
MISSING_COLOUR = [('missing_minutes', '#3a2a2c', 5, 1.6), ('missing_video', '#25362e', 7, 1.8),
                  ('missing_transcript', '#38331f', 9, 2.0)]
# ONE HUE PER KIND OF GAP (TJ, 7 October 2026: three greys could only be told apart by
# hovering). Still hatched, so a gap never reads as a fifth kind of job; the hue says which
# gap. Chosen clear of the job colours (blues, orange, purple).
MISSING_LINE = {'missing_minutes': '#d07878', 'missing_video': '#6fbf95', 'missing_transcript': '#c8b46a'}
MISSING_LABEL = {'missing_minutes': 'no town minutes', 'missing_video': 'no recording',
                 'missing_transcript': 'no transcript'}

# NEEDS REVIEW IS NEITHER A JOB NOR AN ABSENCE -- a third thing on the same bar. TJ, 7
# October 2026: two schema-2 reads came back with their whole attendance list dropped by
# the quote check although both sets of minutes print one, and *"these should be FLAGGED
# somehow, show up on the chart, put back into the backlog and need a direct review
# (pulled out of the normal flow of processing so they can't back anything up)."* So it is
# drawn as its own SOLID segment -- not hatched like a missing record, because this is a
# real document we hold and the gap is in OUR reading of it, not in the town's record --
# in a hue clear of the four job colours and the three missing hues. `review_queue.py`
# decides what is held; this only draws the count `build_backlog_depth.py` already pulled
# out of the job totals and `% open`.
NEEDS_REVIEW_COLOUR = '#f778ba'
NEEDS_REVIEW_LABEL = 'held for review — a suspect read, pulled out for a person to check'


# THE CHART FILTERS TO A BOARD, AND SWITCHES MEASURE. TJ, 6 October 2026: *"the select
# board/school/finance was supposed to be a filter/toggle on the main bar chart so i could
# see per FY what % is still open for them, and for what years."* Every combination is drawn
# here, at build time, and two rows of buttons show one -- the page is a local file and must
# not need a library or a network to switch a view.
#
#   jobs    open JOBS by stream, stacked: what is left, and what kind of work it is
#   % open  of the MEETINGS with a record to process in that year, the share still open:
#           one unit over the same unit, so it can be a percentage (jobs cannot -- a meeting
#           waiting in two streams is two jobs). Read off build_backlog_depth's payload.
def _board_name(slug):
    return slug.replace('-', ' ').title().replace(' Of ', ' of ').replace(' On ', ' on ').replace('Pacc', '(PACC)')


def _jobs_svg(rows, key='x', show_missing=True, show_held=True):
    # MISSING RECORDS CAN BE HIDDEN (TJ, 7 October 2026). Hidden means drawn without them --
    # the bars rescale to the work alone -- not drawn with them and then made invisible,
    # which would leave the work squashed under empty space.
    if not show_missing:
        rows = [dict(r, **{s: 0 for s, _, _, _ in MISSING_COLOUR}) for r in rows]
        key = key + '-nm'
    # HELD MEETINGS CAN BE HIDDEN TOO (TJ, 7 October 2026), the same way: redrawn without them.
    if not show_held:
        rows = [dict(r, needs_review=0) for r in rows]
        key = key + '-nh'
    # NEITHER "no jobs" NOR "nothing open" MAY HIDE A YEAR WITH SOMETHING MISSING OR HELD
    # FOR REVIEW. A fiscal year can have every job cleared and still owe a bar, because a
    # missing record is not work and a held meeting is pulled out of the backlog, not
    # cleared from it.
    rows = [r for r in rows
           if r.get('total') or r.get('needs_review') or any(r.get(s) for s, _, _, _ in MISSING_COLOUR)]
    if not rows:
        return '<div class="tiny" style="margin:12px 0">Nothing open, and nothing missing.</div>'
    hi = max(r['total'] + r.get('needs_review', 0) + sum(r.get(s, 0) for s, _, _, _ in MISSING_COLOUR)
            for r in rows)
    W, H, PAD, GAP = 1000, 210, 26, 4
    bw = max(6.0, (W - PAD * 2) / max(len(rows), 1) - GAP)
    pid = re.sub(r'[^a-z0-9]+', '-', key.lower()).strip('-') or 'x'
    out = ['<svg viewBox="0 0 %d %d" width="100%%" height="%d" style="display:block;margin:8px 0 2px">'
           % (W, H, H)]
    out.append('<defs>%s</defs>' % ''.join(
        '<pattern id="bk-hatch-%s-%s" width="%d" height="%d" patternTransform="rotate(45)" '
        'patternUnits="userSpaceOnUse"><rect width="%d" height="%d" fill="%s"/>'
        '<line x1="0" y1="0" x2="0" y2="%d" stroke="%s" stroke-width="%.1f"/></pattern>'
        % (pid, name, spacing, spacing, spacing, spacing, bg, spacing, MISSING_LINE[name], sw)
        for name, bg, spacing, sw in MISSING_COLOUR))
    base = H - 26
    for i, r in enumerate(rows):
        x = PAD + i * (bw + GAP)
        y = base
        for name, col in STREAM_COLOUR:
            n = r.get(name, 0)
            if not n:
                continue
            bh = (base - 14) * n / hi
            y -= bh
            out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s">'
                       '<title>%s %s: %s</title></rect>' % (x, y, bw, bh, col, r['fy'], name, format(n, ',')))
        job_top = y
        nr = r.get('needs_review', 0)
        if nr:
            bh = (base - 14) * nr / hi
            y -= bh
            out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s">'
                       '<title>%s held for review: %s meeting(s) \u2014 %s</title></rect>'
                       % (x, y, bw, bh, NEEDS_REVIEW_COLOUR, r['fy'], format(nr, ','),
                          html.escape('; '.join('%s %d' % (_board_name(b), c)
                                                for b, c in (r.get('needs_review_boards') or {}).items())
                                      or NEEDS_REVIEW_LABEL)))
        review_top = y
        for name, _bg, _sp, _sw in MISSING_COLOUR:
            n = r.get(name, 0)
            if not n:
                continue
            bh = (base - 14) * n / hi
            y -= bh
            out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="url(#bk-hatch-%s-%s)">'
                       '<title>%s %s: %s meeting(s) \u2014 not work, the record is simply '
                       'incomplete</title></rect>'
                       % (x, y, bw, bh, pid, name, r['fy'], MISSING_LABEL[name], format(n, ',')))
        out.append('<text x="%.1f" y="%d" fill="#8b949e" font-size="10" text-anchor="middle">%s</text>'
                   % (x + bw / 2, base + 12, '\u2019' + r['fy'][-2:]))
        # THE BAR'S TOTAL LABEL IS THE JOB TOTAL, NEVER THE COMBINED HEIGHT -- a reader must
        # not read the two numbers as one. The missing total gets its own, smaller "+N"
        # label above the hatch (the word "missing" is in the legend and the hover title,
        # not repeated per bar -- it does not fit a narrow fiscal-year column without
        # colliding with its neighbour, which it did at first draft). A minimum 10px gap is
        # forced between the two labels even where a segment is a sliver a pixel tall, so a
        # tiny job total and a tiny missing total never print on top of each other.
        job_label_y = job_top - 3
        if r['total']:
            out.append('<text x="%.1f" y="%.1f" fill="#e6edf3" font-size="9.5" text-anchor="middle">%s</text>'
                       % (x + bw / 2, job_label_y, format(r['total'], ',')))
        # THREE LABELS CAN NOW STACK ON ONE BAR -- job total, needs-review, missing total --
        # so each is forced at least 10px above whichever label below it actually printed,
        # never above a slot nothing occupies, or a tiny segment prints its label floating
        # in empty space above a gap.
        review_label_y = None
        if nr:
            review_label_y = review_top - 3
            if r['total']:
                review_label_y = min(review_label_y, job_label_y - 10)
            out.append('<text x="%.1f" y="%.1f" fill="%s" font-size="8" text-anchor="middle">%s</text>'
                       % (x + bw / 2, review_label_y, NEEDS_REVIEW_COLOUR, format(nr, ',')))
        miss_tot = sum(r.get(s, 0) for s, _, _, _ in MISSING_COLOUR)
        if miss_tot:
            floor = y - 3
            if review_label_y is not None:
                floor = min(floor, review_label_y - 10)
            elif r['total']:
                floor = min(floor, job_label_y - 10)
            out.append('<text x="%.1f" y="%.1f" fill="#8b949e" font-size="8" text-anchor="middle">+%s</text>'
                       % (x + bw / 2, floor, format(miss_tot, ',')))
    out.append('</svg>')
    return ''.join(out)


def _pct_svg(rows):
    rows = [r for r in rows if r.get('meetings')]
    if not rows:
        return '<div class="tiny" style="margin:12px 0">No meetings with a record to process.</div>'
    W, H, PAD, GAP = 1000, 210, 26, 4
    bw = max(6.0, (W - PAD * 2) / max(len(rows), 1) - GAP)
    out = ['<svg viewBox="0 0 %d %d" width="100%%" height="%d" style="display:block;margin:8px 0 2px">'
           % (W, H, H)]
    base, top = H - 26, 16
    for i, r in enumerate(rows):
        x = PAD + i * (bw + GAP)
        full = base - top
        bh = full * r['pct_open'] / 100.0
        tip = ('%s: %d of %d meetings still open (%.0f%%) \u2014 %s'
               % (r['fy'], r['meetings_open'], r['meetings'], r['pct_open'],
                  ', '.join('%s %d' % (n, r.get(n, 0)) for n, _ in STREAM_COLOUR if r.get(n))
                  or 'nothing open'))
        out.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="#21262d"><title>%s</title></rect>'
                   % (x, top, bw, full, tip))
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#d29922"><title>%s</title></rect>'
                   % (x, base - bh, bw, bh, tip))
        out.append('<text x="%.1f" y="%d" fill="#8b949e" font-size="10" text-anchor="middle">%s</text>'
                   % (x + bw / 2, base + 12, '\u2019' + r['fy'][-2:]))
        out.append('<text x="%.1f" y="%.1f" fill="#e6edf3" font-size="9.5" text-anchor="middle">%.0f%%</text>'
                   % (x + bw / 2, top - 4, r['pct_open']))
    out.append('</svg>')
    return ''.join(out)


def backlog_chart(bd):
    """The fiscal-year chart, filterable to a budget board, in two measures."""
    byfy = bd.get('by_board_fiscal_year') or {}
    boards = [('all', 'All boards')] + [(b['slug'], b['name']) for b in bd.get('filter_boards', [])]
    if not byfy:                       # an older payload: the unfiltered chart only
        byfy = {'all': bd.get('by_fiscal_year', [])}
        boards = boards[:1]
    btn = ('<button type="button" data-%s="%s" onclick="bkPick(this)" style="font:inherit;font-size:12px;'
           'padding:3px 10px;margin:0 4px 4px 0;border-radius:12px;border:1px solid #30363d;'
           'background:%s;color:#e6edf3;cursor:pointer">%s</button>')
    out = ['<div class="card" id="bk"><div class="row"><b class="grow">Backlog by fiscal year of the meeting</b>'
           '<span class="tiny">%s jobs to process</span></div>' % format(bd['total_jobs'], ',')]
    out.append('<div style="margin-top:8px">%s</div>' % ''.join(
        btn % ('board', k, '#1f6feb' if k == 'all' else '#161b22', html.escape(n)) for k, n in boards))
    out.append('<div>%s</div>' % ''.join(
        btn % ('measure', k, '#1f6feb' if k == 'jobs' else '#161b22', n)
        for k, n in [('jobs', 'open jobs, by stream'), ('pct', '% of meetings still open')]))
    out.append('<div>%s</div>' % ''.join(
        btn % ('missing', k, '#1f6feb' if k == 'on' else '#161b22', n)
        for k, n in [('on', 'missing records: shown'), ('off', 'missing records: hidden')]))
    total_held = sum(r.get('needs_review', 0) for r in byfy.get('all', []))
    out.append('<div>%s</div>' % ''.join(
        btn % ('held', k, '#1f6feb' if k == 'on' else '#161b22', n)
        for k, n in [('on', 'held for review: shown (%s)' % format(total_held, ',')),
                     ('off', 'held for review: hidden')]))
    for k, name in boards:
        rows = byfy.get(k, [])
        open_m = sum(r.get('meetings_open', 0) for r in rows)
        held = sum(r.get('meetings', 0) for r in rows)
        summary = ('%s: %s of %s meetings with a record to process still have something open'
                   % (html.escape(name), format(open_m, ','), format(held, ','))) if held else ''
        variants = [('jobs', mi, he, (lambda rs, kk=k, a=(mi == 'on'), b=(he == 'on'):
                                      _jobs_svg(rs, key=kk, show_missing=a, show_held=b)))
                    for mi in ('on', 'off') for he in ('on', 'off')] + [('pct', 'any', 'any', _pct_svg)]
        for m, mi, he, draw in variants:
            out.append('<div class="bkp" data-board="%s" data-measure="%s" data-missing="%s" data-held="%s" '
                       'style="display:%s"><div class="tiny" style="margin-top:6px">%s</div>%s</div>'
                       % (k, m, mi, he, 'block' if (k, m, mi, he) == ('all', 'jobs', 'on', 'on') else 'none',
                          summary, draw(rows)))
    legend = {'official': 'the town\u2019s official minutes, never read',
              'official-v1': 'the town\u2019s official minutes, votes only \u2014 to re-read structured',
              'reconcile': 'the two records of a meeting, to compare',
              'minutes': 'recordings, to write OUR minutes from'}
    out.append('<div class="tiny bkl" data-for="jobs">%s</div>'
               % ' &nbsp; '.join('<span style="color:%s">\u25a0</span> %s' % (c, legend[n]) for n, c in STREAM_COLOUR))
    out.append('<div class="tiny bkl" data-for="jobs" data-held="1" style="margin-top:2px">'
               '<span style="color:%s">\u25a0</span> %s \u2014 hover a pink block for the boards</div>'
               % (NEEDS_REVIEW_COLOUR, NEEDS_REVIEW_LABEL))
    out.append('<div class="tiny bkl" data-for="jobs" data-miss="1" style="margin-top:2px">Not available \u2014 not work '
               'we can do: %s</div>'
               % ' \u00b7 '.join('<span style="color:%s">\u25a0</span> %s' % (MISSING_LINE[n], MISSING_LABEL[n])
                                  for n, bg, _sp, _sw in MISSING_COLOUR))
    out.append('<div class="tiny bkl" data-for="pct" style="display:none"><span style="color:#d29922">\u25a0</span> '
               'still open &nbsp; <span style="color:#21262d">\u25a0</span> done. Of the board\u2019s meetings '
               'in that fiscal year that have a record to process \u2014 the town\u2019s minutes with readable '
               'text, or a usable recording \u2014 the share with anything still to do. Hover a bar for what '
               'is left. A meeting with only an agenda has nothing to process and is not counted.</div>')
    out.append('<div class="tiny" style="margin-top:4px">By the MEETING\u2019s own date, not by when we found it. '
               'A job is one meeting in one stream, so a meeting waiting in two streams is two jobs; the '
               'streams are different work at different prices and are never added into one figure.</div></div>')
    out.append("""<script>
function bkPick(b){var c=document.getElementById('bk');
 var k=b.dataset.board?'board':(b.dataset.measure?'measure':(b.dataset.missing?'missing':'held'));
 c.querySelectorAll('button[data-'+k+']').forEach(function(x){x.style.background=(x===b)?'#1f6feb':'#161b22';});
 c.dataset[k]=b.dataset[k];
 var bd=c.dataset.board||'all', ms=c.dataset.measure||'jobs', mi=c.dataset.missing||'on', he=c.dataset.held||'on';
 c.querySelectorAll('.bkp').forEach(function(p){p.style.display=(p.dataset.board===bd&&p.dataset.measure===ms
   &&(p.dataset.missing==='any'||p.dataset.missing===mi)&&(p.dataset.held==='any'||p.dataset.held===he))?'block':'none';});
 c.querySelectorAll('.bkl').forEach(function(l){l.style.display=(l.dataset['for']===ms
   &&!(l.dataset.miss&&mi==='off')&&!(l.dataset.held&&he==='off'))?'block':'none';});
 try{localStorage.setItem('bk',bd+'|'+ms+'|'+mi+'|'+he);}catch(e){}
}
(function(){try{var v=(localStorage.getItem('bk')||'').split('|');var c=document.getElementById('bk');
 if(v[0]){var b=c.querySelector('button[data-board="'+v[0]+'"]');if(b)bkPick(b);}
 if(v[1]){var m=c.querySelector('button[data-measure="'+v[1]+'"]');if(m)bkPick(m);}
 if(v[2]){var x=c.querySelector('button[data-missing="'+v[2]+'"]');if(x)bkPick(x);}
 if(v[3]){var y=c.querySelector('button[data-held="'+v[3]+'"]');if(y)bkPick(y);}}catch(e){}})();
</script>""")
    return ''.join(out)


# -------------------------------------------------------------------- the refresh
# WHERE THE PIPELINE LOOKS, AS ADDRESSES A PERSON CAN OPEN.
#
# TJ, 19 September 2026: "I don't need the python script name. just a label of the type
# of material based on the location, and a link to it."
#
# Right: the script is our implementation, and what a reader wants to know is which page
# on the town's website was checked and whether checking it worked. The label names the
# MATERIAL, the link goes to the place, and the script is kept only as the key that finds
# the run in today's log.
#
# Every address here is read from the same place the watcher reads it -- feed-sources.csv
# for the feeds, the channel id for YouTube -- rather than typed, so a source that moves
# moves here too (rule 2).
def watcher_targets():
    feeds = [r for r in rows('feed-sources.csv') if r.get('url')]
    chan = ''
    try:
        sys.path.insert(0, os.path.join(ROOT, 'scripts'))
        import watch_youtube as WY
        chan = WY.FEED
    except Exception:
        pass
    town = 'https://www.lunenburgma.gov'
    return [
        dict(script='watch_meetings.py',
             label='Agendas and minutes, every board',
             where='the town’s Agenda Center',
             links=[(town + '/AgendaCenter', 'AgendaCenter')]),
        dict(script='fetch_agendas.py',
             label='Downloading what the watcher found',
             where='the same Agenda Center, file by file',
             links=[(town + '/AgendaCenter', 'AgendaCenter')]),
        dict(script='watch_documents.py',
             label='Budget documents — district and town',
             where='the district’s budget pages and the town’s finance pages',
             links=[('https://www.lunenburgschools.net/school-committee-1/meetings',
                     'school committee meetings'),
                    ('https://www.lunenburgschools.net/department-directory/',
                     'district directory'),
                    (town + '/199/Finance', 'town finance')]),
        dict(script='watch_feeds.py',
             label='Town announcements',
             where='news flash and alert feeds',
             links=[(f['url'], f['source'].split('—')[-1].strip() or f['source'])
                    for f in feeds]),
        dict(script='watch_youtube.py',
             label='New meeting recordings',
             where='the town’s YouTube channel feed',
             links=[(chan or 'https://www.youtube.com/@LunenburgTV', 'channel feed')]),
    ]




def found_by_day():
    """What the WATCHERS saw, per day, from their own event logs.

    TJ, 19 September 2026: "it looks like none of the refresh runs found much, but i dont
    think thats true." It is not true, and it was the same bug one level down.

    The counts were coming from refresh-runs.csv, which refresh.py writes at the END --
    after the step that died on the 16th, 17th and 18th. So three days that found seven
    agendas and four recordings between them printed a dash, as if the town had posted
    nothing.

    The watchers write their events the moment they see them, near the start of the run,
    and those files survived every failure. They are the honest source for "what did this
    day turn up": an observation log, written first, rather than a summary written last.
    """
    out = collections.defaultdict(collections.Counter)
    for f, label in (('meeting-watch-events.csv', None),          # kind column: agenda/minutes
                     ('youtube-watch-events.csv', 'videos'),
                     ('document-watch-events.csv', 'documents'),
                     ('feed-watch-events.csv', 'notices')):
        for r in rows(f):
            day = (r.get('first_seen') or r.get('seen_at') or '')[:10]
            if not day:
                continue
            # The watcher's own words: 'agenda' and 'minutes'. Blind pluralisation turned
            # the second into 'minutess' and the column read empty.
            k = label or {'agenda': 'agendas', 'minutes': 'minutes'}.get(r.get('kind'), 'other')
            out[day][k] += 1
    return out


def run_history(n=8):
    """Every day the refresh RAN, from its logs — not from the registry it writes.

    TJ, 19 September 2026: "Recent refresh runs... but i know one ran yesterday?"

    It did. The table was reading sources/data/refresh-runs.csv, and that file's last row
    is the 15th -- because the run appends its row at the END, and the runs of the 16th,
    17th and 18th all died before reaching it (`database or disk is full`, from Thursday's
    full disk). So a registry written only by a successful run reported three failures as
    SILENCE, which is the one thing a status page must never do.

    The log file is the ground truth that a run happened at all; the registry is the
    detail of what a run found. Read the first, join the second, and say plainly where a
    run left no row.
    """
    logs = sorted(glob.glob(os.path.join(ROOT, 'build', 'refresh-logs', '*.log')), reverse=True)
    by_day = {r['as_of']: r for r in rows('refresh-runs.csv')}
    seen = found_by_day()
    out = []
    for f in logs[:n]:
        base = os.path.basename(f)[:-4]
        day = base[:10]
        again = base[10:].strip('-') or ''      # '', 'rerun', …
        try:
            with open(f, encoding='utf-8', errors='replace') as fh:
                text = fh.read()
        except OSError:
            continue
        ex = re.findall(r'refresh exit (\d+)', text)
        # The log prints the whole interpreter command, so the script name is the LAST
        # .py on the line, not the first token after the colon.
        fails = re.findall(r'step failed:.*?([a-z_]+\.py)', text)
        done = '=== finished' in text
        out.append(dict(day=day, again=again, name=os.path.basename(f),
                        exit=int(ex[-1]) if ex else None, finished=done,
                        failed=sorted(set(fails)),
                        running=(not done and day == dt.date.today().isoformat()),
                        row=by_day.get(day), seen=seen.get(day, collections.Counter()),
                        mtime=ago(dt.datetime.fromtimestamp(os.path.getmtime(f),
                                                            dt.timezone.utc).isoformat())))
    return out



# THE REFRESH IS FOUR PHASES, AND KNOWING WHICH ONE IT IS IN IS THE USEFUL FACT.
#
# TJ, 19 September 2026: "Daily refresh 'fetch' vs processing steps?"
#
# A run takes hours and the card said only "up 01:32:43", which tells you it is alive and
# nothing about whether it is still finding things or long past that. The phases answer
# different questions and fail differently:
#
#   WATCH    what is new on the town's site and the channel — network, free, fast
#   FETCH    download what we do not hold — network, free, the slow part when the town
#            has posted a lot
#   READ     extract text, OCR, classify — local, free, CPU-bound
#   WRITE    our minutes, the votes, the budget state — `claude -p`, and the only phase
#            that spends the allowance
#   PUBLISH  rebuild the payloads, the search index, the site, deploy
#
# A step is mapped by name rather than by position, because the order changes and a
# position-based label would silently mislabel the day it does (the `v1` mistake, in a
# different costume).
PHASES = [
    ('watch',   'Watching',   ('watch_',)),
    ('fetch',   'Fetching',   ('fetch_',)),
    ('read',    'Reading',    ('extract_minutes', 'ocr_', 'build_minutes_searchable',
                               'build_youtube_classification', 'split_large_text')),
    ('write',   'Writing',    ('write_recording_minutes', 'write_budget_state',
                               'extract_official_votes', 'write_document_budget_state',
                               'write_agenda_preview')),
    ('publish', 'Publishing', ('build_', 'sync_', 'export_', 'npm', 'wrangler')),
]


def phase_of(script):
    for key, _, pats in PHASES:
        if any(script.startswith(x) or x in script for x in pats):
            return key
    return 'publish'


def refresh_phase(text):
    """Which phase the run is in now, and which it has been through.

    The log prints `$ <command>` when a step starts and `  [name: 1.2s, exit N]` when it
    finishes, so the step in flight is the last one started with no completion after it.
    """
    steps = re.findall(r'^\$ .*?([a-z_]+\.py)|^\$ .*?(npm|npx) ', text, re.M)
    names = [a or b for a, b in steps]
    seen, order = set(), []
    for n in names:
        k = phase_of(n)
        if k not in seen:
            seen.add(k)
            order.append(k)
    last = names[-1] if names else ''
    tail = text.rsplit('$ ', 1)[-1] if '$ ' in text else ''
    in_flight = last and ('exit ' not in tail)
    return dict(now=phase_of(last) if in_flight else None,
                step=last if in_flight else '', seen=seen)


# WHAT THE REFRESH PICKED UP, ITEMISED. TJ, 9 October 2026: *"i want the dashboard to show
# the actual files the refresh found or created, itemized ... i want to see which meetings
# and docs it picked up to make sure its working everyday"*.
#
# refresh.py writes build/refresh-found/<date>.json the moment it has diffed its inventory.
# Runs from before that file existed printed the same list into their log as a FOUND block,
# so a day with no JSON is read off its log -- the same list, from the run's own output.
# Dry runs are never shown here: this panel answers "did the morning run work".
FOUND_DIRS = (os.path.join(ROOT, 'build', 'refresh-found'), os.path.join(TREE, 'build', 'refresh-found'))
FOUND_KIND = re.compile(r'^    ([a-z][a-z ]+?)\s+(\d+)$')


def _found_from_log(path):
    try:
        text = open(path, encoding='utf-8', errors='replace').read()
    except OSError:
        return None
    if '  FOUND -- ' not in text:
        return None
    found, wrote, kind, part = {}, {}, None, None
    for line in text.split('  FOUND -- ', 1)[1].splitlines()[1:]:
        if line.startswith('  WROTE -- '):
            part = 'wrote'
            continue
        if line.startswith('  note:') or line.strip() in ('deployed', 'NOT deployed (pass --deploy)') \
                or line.startswith('  ---'):
            break
        if part == 'wrote':
            m = re.match(r'^        (generated minutes|analyses)\s+(.*)$', line)
            if m:
                wrote.setdefault(m.group(1), []).append(m.group(2).strip())
            continue
        m = FOUND_KIND.match(line)
        if m:
            kind = m.group(1).strip()
            found.setdefault(kind, [])
        elif line.startswith('        ') and kind and line.strip() != 'nothing new was published today':
            found[kind].append(line.strip())
    return dict(found=found, wrote=wrote, source='log')


def refresh_found(days=10):
    """The most recent real run's itemised list: (date, payload), or (None, None)."""
    for i in range(days):
        day = (dt.date.today() - dt.timedelta(days=i)).isoformat()
        for d in FOUND_DIRS:
            f = os.path.join(d, day + '.json')
            if os.path.exists(f):
                try:
                    j = json.load(open(f, encoding='utf-8'))
                    j['source'] = 'json'
                    return day, j
                except Exception:
                    pass
        j = _found_from_log(os.path.join(ROOT, 'build', 'refresh-logs', day + '.log'))
        if j:
            return day, j
    return None, None


# FOUND SO FAR, LIVE. TJ, 9 October 2026, waiting for the Finance Committee video to appear:
# *"oh it updates it at the END"*. The run writes its list only after the slow steps, but
# every watcher records a find the moment it makes it, in its own event log. So while
# today's list does not exist yet, this reads those logs -- the refresh tree's first,
# because that is where the scheduled run writes -- for what has been found today so far.
EVENT_LOGS = (
    ('meeting-watch-events.csv', lambda r: r.get('kind') == 'agenda' and 'agendas'
                                 or r.get('kind') == 'minutes' and 'official minutes',
     lambda r: '%s  %s' % (r.get('board', ''), r.get('meeting_date', '')),
     lambda r: 'town AgendaCenter', 'url'),
    ('youtube-watch-events.csv', lambda r: 'videos',
     lambda r: r.get('title', ''), lambda r: 'town YouTube channel', 'url'),
    ('document-watch-events.csv', lambda r: 'documents',
     lambda r: r.get('label', ''), lambda r: WHERE_DOC.get(r.get('folder', ''), r.get('folder', '')), 'upstream'),
    ('feed-watch-events.csv', lambda r: 'announcements',
     lambda r: r.get('title', ''), lambda r: r.get('source', ''), 'link'),
)
WHERE_DOC = {'district-budget': 'district site', 'town-budget': 'town site, budget and finance pages',
             'town-supplementary': 'town site, other pages'}


def found_today(today):
    """{kind: [(label, where, url)]} from the watchers' event logs, first seen today."""
    for tree in (TREE, ROOT):
        out = collections.OrderedDict()
        for f, kind_of, label, where, url in EVENT_LOGS:
            p = os.path.join(tree, 'sources', 'data', f)
            try:
                rs = list(csv.DictReader(open(p, encoding='utf-8')))
            except OSError:
                continue
            for r in rs:
                if r.get('first_seen') != today:
                    continue
                k = kind_of(r)
                if k:
                    out.setdefault(k, []).append((label(r), where(r), r.get(url, '')))
        if out:
            return out
    return {}


def _found_live(today, live):
    got = found_today(today)
    n = sum(len(v) for v in got.values())
    out = ['<div class="card on"><div class="tiny" style="margin-bottom:6px"><b>Found so far today</b>'
           ' &mdash; %d %s <span style="color:#8b949e">&middot; read live from the watchers&rsquo; '
           'logs; the full list (with transcripts, local files and what we wrote) appears when the '
           'run finishes</span></div>' % (n, 'so far' if live else 'today')]
    if not got:
        out.append('<div class="tiny" style="color:#8b949e">nothing yet%s</div>'
                   % ('' if live else ' -- no run has looked today'))
    for kind, items in got.items():
        body = ''.join('<div class="mono tiny" style="padding:1px 0 1px 14px">%s '
                       '<span style="color:#8b949e">&mdash; %s</span>%s</div>'
                       % (html.escape(lb), html.escape(wh),
                          (' <a href="%s" target="_blank">link</a>' % html.escape(u, quote=True)) if u else '')
                       for lb, wh, u in items)
        out.append('<details data-k="live-%s" open style="margin:3px 0 3px 10px"><summary class="tiny" '
                   'style="cursor:pointer"><b>%d</b> %s</summary>%s</details>'
                   % (re.sub(r'\W+', '-', kind), len(items), html.escape(kind), body))
    out.append('</div>')
    return ''.join(out)


def _found_card(today):
    day, j = refresh_found()
    if not j:
        return ('<div class="card"><div class="tiny"><b>What it picked up.</b> No run in the '
                'last ten days got far enough to list what it found.</div></div>')
    # NEUTRAL, NOT AMBER. TJ, 9 October 2026: *"shouldnt be orange. that looks like an error
    # or warning"*. The last run's list is not a fault; the date says which run it is, and
    # whether today's run failed is the alert banner's job, not this panel's.
    stale = day != today
    live = any(r['name'] == 'Daily refresh' for r in running())
    lead = _found_live(today, live) if stale else ''
    when = ('the %s run' % dt.date.fromisoformat(day).strftime('%-d %B') if stale else 'today')
    note = (' <span class="tiny" style="color:#8b949e">&middot; today&rsquo;s run is in progress; '
            'its list appears when it finishes</span>' if stale and live else '')
    out = [lead + '<div class="card"><div class="tiny" style="margin-bottom:6px">'
           '<b>What it picked up</b> &mdash; %s%s</div>' % (when, note)]
    def fold(key, n, label, body, open_at=15):
        return ('<details data-k="found-%s"%s style="margin:3px 0 3px 10px"><summary class="tiny" '
                'style="cursor:pointer"><b>%d</b> %s</summary>%s</details>'
                % (re.sub(r'\W+', '-', key), ' open' if n <= open_at else '', n, label, body))

    def line(x):
        return '<div class="mono tiny" style="padding:1px 0 1px 14px">%s</div>' % x

    # FOUND ON EXTERNAL SITES: each document with where it was found and its address.
    docs = collections.defaultdict(list)
    for d in j.get('found_docs') or []:
        docs[d['kind']].append(d)
    ext, empty = [], []
    for kind, items in (j.get('found') or {}).items():
        if not items:
            empty.append(kind)
            continue
        if docs.get(kind):
            body = ''.join(line('%s <span style="color:#8b949e">&mdash; %s%s</span>%s' % (
                html.escape(d['title'] or os.path.basename(d['file'])), html.escape(d['where']),
                (', meeting ' + html.escape(d['meeting'])) if d.get('meeting') else '',
                (' <a href="%s" target="_blank">link</a>' % html.escape(d['url'], quote=True)) if d.get('url') else ''))
                for d in sorted(docs[kind], key=lambda d: (d['where'], d['title'])))
        else:
            body = ''.join(line(html.escape(x)) for x in items)
        ext.append(fold(kind, len(items), html.escape(kind), body))
    n_ext = sum(len(v) for v in (j.get('found') or {}).values())
    out.append('<div class="tiny" style="margin-top:4px"><b>Found on external sites</b> &mdash; '
               '%d document(s)</div>' % n_ext)
    out.extend(ext or ['<div class="tiny" style="margin-left:10px;color:#8b949e">nothing new was published</div>'])
    if empty and ext:
        out.append('<div class="tiny" style="margin:2px 0 0 10px;color:#6e7681">nothing new: %s</div>'
                   % html.escape(', '.join(empty)))

    # FOUND IN OUR LOCAL FILES: grouped by the folder they landed in, so a batch shows as one.
    if 'local' in j:
        local = j.get('local_docs') or [{'file': f, 'dir': os.path.dirname(f)} for f in j.get('local', [])]
        out.append('<div class="tiny" style="margin-top:10px"><b>Found in our local files</b> &mdash; '
                   '%d document(s) new to the archive that the refresh did not fetch: placed by hand, '
                   'or by another job</div>' % len(local))
        by_dir = collections.defaultdict(list)
        for d in local:
            by_dir[d['dir']].append(os.path.basename(d['file']))
        for d in sorted(by_dir, key=lambda d: -len(by_dir[d])):
            out.append(fold('local-' + d, len(by_dir[d]), '<span class="mono">%s</span>' % html.escape(d),
                            ''.join(line(html.escape(f)) for f in sorted(by_dir[d])), open_at=5))
        if not local:
            out.append('<div class="tiny" style="margin-left:10px;color:#8b949e">none</div>')
        if j.get('renderings'):
            out.append('<div class="tiny" style="margin:4px 0 0 10px;color:#6e7681">plus %d rendering(s) '
                       'of ours catalogued &mdash; extracted text and working files, not documents</div>'
                       % j['renderings'])

    # WRITTEN BY US
    wrote = [(k, v) for k, v in (j.get('wrote') or {}).items() if v]
    out.append('<div class="tiny" style="margin-top:10px"><b>Written by us</b> &mdash; %d</div>'
               % sum(len(v) for _, v in wrote))
    for kind, items in wrote:
        out.append(fold('wrote-' + kind, len(items), html.escape(kind),
                        ''.join(line(html.escape(x)) for x in items)))
    if j.get('replayed'):
        out.append('<div class="tiny" style="margin-top:6px;color:#8b949e">replayed under the '
                   '9 October rules from the git state before and after that run; it reported 279 '
                   'budget documents at the time, counting extracted text and files it did not '
                   'fetch</div>')
    if j.get('source') == 'log':
        out.append('<div class="tiny" style="margin-top:6px;color:#8b949e">read off that '
                   'run&rsquo;s log, and COUNTED THE OLD WAY: until 9 October 2026 a run also '
                   'listed extracted text files, our own working files, and documents and '
                   'minutes other processes landed while it ran. Runs from 10 October list '
                   'only what the refresh itself fetched or wrote.</div>')
    out.append('</div>')
    return ''.join(out)


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
    # WHAT EACH STEP FOUND, not just whether it ran.
    #
    # TJ, 20 September 2026: "under 'The daily refresh', I want to see the total counts of
    # what was found in each step." The table said a watcher ran and took 4 seconds, which
    # answers "did it look" and not "was there anything there" -- and those are different
    # questions, especially on a morning when the run failed later.
    #
    # Counted from the step's OWN slice of the log: everything printed after this script's
    # invocation and before the next one. Counting the whole file per pattern attributes a
    # number to whichever step the pattern happened to match first.
    steps = [t['script'] for t in watcher_targets()]
    bounds = {}
    for sc in steps:
        m = re.search(re.escape(sc), text)
        bounds[sc] = m.start() if m else None
    ordered = sorted([(v, k) for k, v in bounds.items() if v is not None])
    slice_of = {}
    for i, (pos, sc) in enumerate(ordered):
        end = ordered[i + 1][0] if i + 1 < len(ordered) else len(text)
        slice_of[sc] = text[pos:end]

    # READ OFF THE LOG, NOT GUESSED. The first version of this invented the phrases --
    # "(\d+) new agenda", "(\d+) new document" -- and matched almost nothing, because the
    # watchers do not say that. watch_meetings.py prints
    #   "live: 51 boards, 1518 documents listed; 0 new (0 agendas, 0 minutes)"
    # and the feed watcher prints "N in feed, M new". Those are the sentences to parse,
    # and they are quoted here so the next person can see what is being matched against.
    # NOT VOTES. TJ, 29 September 2026: *"do NOT count votes on the dashboard or reports.
    # telling me the number of votes it found is absurd"* -- and he is right about why.
    # A vote count is not a measure of anything we did or the town published: it is how
    # many times somebody happened to move a motion in whatever minutes got read. Two
    # documents can yield nine votes or none, and the number moves for reasons that have
    # nothing to do with progress. DOCUMENTS are the unit here, in both directions --
    # what the town published, and what we wrote from it.
    FOUND_PATTERNS = ((r'(\d+) new \((\d+) agendas?, (\d+) minutes?\)', None),
                      (r'(\d+) in feed, (\d+) new', 'feed items'),
                      (r'(\d+) new transcript', 'captions'),
                      (r'(\d+) new recording', 'recordings'))

    def tally(blob):
        out = []
        # The meetings watcher reports agendas and minutes inside one sentence, so it is
        # parsed as a triple rather than three separate patterns that would each match it.
        for a, ag, mi in re.findall(FOUND_PATTERNS[0][0], blob):
            for n, label in ((int(ag), 'agendas'), (int(mi), 'sets of minutes')):
                if n:
                    out.append(dict(label=label, n=n))
        for n_in, n_new in re.findall(FOUND_PATTERNS[1][0], blob):
            if int(n_new):
                out.append(dict(label='feed items', n=int(n_new)))
        for pat, label in FOUND_PATTERNS[2:]:
            hits = [int(x) for x in re.findall(pat, blob)]
            if sum(hits):
                out.append(dict(label=label, n=sum(hits)))
        # Merge duplicates: a step whose sentence appears twice should read once.
        merged = {}
        for f in out:
            merged[f['label']] = merged.get(f['label'], 0) + f['n']
        return [dict(label=k, n=v) for k, v in merged.items()]

    looked = []
    for t in watcher_targets():
        m = re.findall(re.escape(t['script']) + r'[^\n]*?: ([\d.]+)s, exit (\d+)', text)
        looked.append(dict(t, seconds=float(m[-1][0]) if m else None,
                           exit=int(m[-1][1]) if m else None, ran=bool(m),
                           found=tally(slice_of.get(t['script'], ''))))

    # The run total. SUMMED rather than last-match: a watcher that reports per board
    # prints the phrase many times, and `m[-1]` quietly published the final board's count
    # as though it were the morning's.
    found = tally(text)

    # WHAT IT IS ABOUT TO DO. The log prints each claude -p job as it starts, so the last
    # one with no result line after it is the one in flight.
    jobs = re.findall(r'(write_recording_minutes|extract_official_votes)\.py '
                      r'([a-z0-9-]+) (\d{4}-\d{2}-\d{2})', text)
    costs = [float(x) for x in re.findall(r'written \(\$([\d.]+)\)', text)]
    hist = run_history()
    ph = refresh_phase(text)
    return dict(live=live, phase=ph, log=os.path.basename(cur) if cur else None, today=today,
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
# WHOSE DOCUMENT IS THIS? Rule 3, applied to the one column that was frightening people.
#
# TJ, 19 September 2026: "its alarming to see 'no publisher address' for many. but looking
# closer, its because this is a generated set of docs. I think we need something that
# indicates that in that column to not be alarming. it looks like info is 'missing' but
# its not."
#
# Exactly right, and the red was mine. A document with no publisher address is one of
# three completely different things, and printing them identically turns two harmless
# ones into an alarm:
#
#   OURS        we wrote it, so there is no publisher but us. Nothing is missing.
#   PUBLISHED   somebody else put it on a website, and we hold its address.
#   BY REQUEST  somebody else's document that never had a public address -- it came by
#               records request, by email, in a packet. THIS is the one worth a colour,
#               and it is the count rule 12 says should stay uncomfortable.
#
# The folder decides the first, because sources/ is organised by HOW A DOCUMENT REACHED
# US -- which is precisely this question -- and the presence of an address decides the
# other two.
OURS = {'analyses', 'data'}

def origin_of(top, upstream):
    if top in OURS:
        return 'ours'
    return 'published' if upstream else 'request'


# WHAT KIND OF THING IT IS, in the words somebody would search with. The file extension
# is not it: .pdf covers a set of minutes, a budget book and a union contract, and those
# are three different questions. The folder is the better signal, because sources/ is
# organised by how a document reached us, and within meetings/ the filename says which
# half of the meeting it is.
def kind_of(k, top):
    if top == 'meetings':
        if '-agenda-' in k:
            return 'agenda'
        if '-minutes-' in k:
            return 'minutes'
        return 'meeting'
    if top in ('town-budget', 'district-budget', 'budget-workbooks'):
        return 'budget'
    if top in ('town-ledgers', 'munis-ledgers'):
        return 'ledger'
    if top.startswith('state-'):
        return 'state'
    if top == 'contracts':
        return 'contract'
    if top == 'town-annual-reports':
        return 'annual report'
    if top == 'correspondence':
        return 'correspondence'
    if top == 'analyses':
        return 'analysis'
    if top == 'data':
        return 'dataset'
    # A file at the root of sources/ has no folder to speak for it, and falling through to
    # `top` printed the filename as its own kind ("MANIFEST.md").
    return top if '/' in k else 'archive note'


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
            up = (r.get('upstream') or upstream.get(k, '') or '')
            out.append([k, int(r['bytes'] or 0), up, (r.get('sha256') or '')[:12],
                        top, origin_of(top, up), kind_of(k, top)])
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
.on{border-left:3px solid #3fb950}
.alert{border:1px solid #f85149;border-left:4px solid #f85149;background:#2b1214}
.warnbox{border:1px solid #9e6a03;border-left:4px solid #d29922;background:#241c0c}
.runbox{border:1px solid #2ea043;border-left:4px solid #3fb950;background:#0f1f14}
.card.done{border-left:3px solid #30363d}
/* The three right-hand cells share a rail across every card, so the figures read down as
   a column rather than wandering with the length of the name beside them. */
.metric{width:5rem;text-align:right;font-size:16px;font-weight:600;
font-variant-numeric:tabular-nums;flex:0 0 auto}
.unit{width:10rem;font-size:12px;color:#8b949e;flex:0 0 auto;padding-left:8px}
.when{width:7rem;text-align:right;flex:0 0 auto}
@media (max-width:700px){
  .row{flex-wrap:wrap!important}
  .metric,.unit,.when{width:auto;text-align:left}
}.cost{border-left:3px solid #d29922}.idle{color:#8b949e}
.row{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.grow{flex:1;min-width:200px}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
.num{font-variant-numeric:tabular-nums}
.bar{height:6px;background:#21262d;border-radius:3px;overflow:hidden;margin-top:6px;display:flex}
.bar i{display:block;height:100%;background:#3fb950}
.bar i.part{background:#d29922}
.bar i.blocked{background:#f85149}
/* A PILL IS A LABEL, AND A LABEL THAT WRAPS IS NOT ONE. "stopped part-way" broke across
   two lines inside its own rounded box, which reads as two damaged pills rather than one
   phrase. white-space:nowrap keeps it whole; inline-block makes the padding and radius
   apply to the whole run rather than to each line fragment. */
.pill{display:inline-block;white-space:nowrap;font-size:11px;padding:1px 7px;
border-radius:9px;background:#21262d;color:#8b949e}
.pill.go{background:#1a3a24;color:#3fb950}.pill.warn{background:#3a2d12;color:#d29922}
.pill.no{background:#3a1d1d;color:#f85149}
.key{display:inline-block;width:9px;height:9px;border-radius:2px;margin:0 3px 0 10px}
.key.go{background:#3fb950}.key.warn{background:#d29922}
.ph{font-size:11px;padding:2px 8px;border-radius:9px;background:#21262d;color:#586069;
white-space:nowrap}
.ph.done{color:#3fb950}.ph.now{background:#1f6feb;color:#fff;font-weight:600}
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
.chips{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 10px}
.chip{display:inline-block;padding:5px 11px;border:1px solid #30363d;border-radius:14px;
text-decoration:none;font-size:12px;color:#8b949e}
.chip.sel{background:#1f6feb;border-color:#1f6feb;color:#fff}
.chip b{color:inherit;margin-left:3px}
.tag{display:inline-block;white-space:nowrap;font-size:10.5px;padding:1px 6px;
border-radius:8px;text-transform:uppercase;letter-spacing:.06em}
.chip{white-space:nowrap}
.tag.ours{background:#12243a;color:#6cb6ff}.tag.req{background:#3a2d12;color:#d29922}
.tag.agentic{background:#2a1e3d;color:#c09cf5}
.lnk{display:inline-block;white-space:nowrap;font-size:11px;padding:1px 7px;border-radius:9px;
border:1px solid #30363d;color:#6cb6ff;text-decoration:none}
.lnk:hover{border-color:#6cb6ff}
"""

def bar(done, todo, blocked=0):
    """Green means finished. Anything short of finished is amber.

    TJ, 19 September 2026: "none should be green until its done." He is right, and the
    first version had it backwards: a green bar 60% of the way across reads as healthy,
    when the only thing it says is that a backlog is 40% unread. Green is a claim about
    the END STATE, and spending it on progress leaves no colour to mean 'complete'.
    """
    tot = (done or 0) + (todo or 0) + (blocked or 0)
    if not tot:
        return ''
    # A BLOCKED PAGE IS NOT DONE AND IT IS NOT OUTSTANDING, so it gets its own colour.
    # Before this, 511 proven and 3 blocked drew a FULL GREEN bar: the three pages nobody
    # could read were counted as finished, and the bar claimed 100% of a thing that is
    # 99.4%. TJ, 3 October 2026: *make the progress bar red then to show they are blocked,
    # and in the count section show the blocked count.* Red is right because it is the one
    # state no amount of work moves -- amber says `not yet`, red says `not from here`.
    pd = 100.0 * (done or 0) / tot
    pb = 100.0 * (blocked or 0) / tot
    cls = '' if not todo else ' class="part"'
    out = '<div class="bar"><i%s style="width:%.1f%%"></i>' % (cls, pd)
    if blocked:
        out += '<i class="blocked" style="width:%.1f%%"></i>' % pb
    return out + '</div>'

def alert():
    """An alarm about the CURRENT state, not a memorial to past failures.

    TJ, 19 September 2026: "when one is running, that becomes less important ... 'Failed
    but rerunning' is a not-alarming thing. we dont want that red alarm on the dash
    forever now that a refresh is being run."

    Right, and the first version was a memorial. It listed every recent failure in red for
    as long as those logs existed, so the banner would still have been shouting about the
    16th in October. An alarm that cannot go away is an alarm nobody reads -- and the
    whole point of building this was that four days of real failure went unnoticed.

    So the colour tracks what is true NOW, and there are three states:

      RED       the latest finished run failed and nothing is running. Broken, unattended.
      AMBER     it failed, and a run is going right now. Being dealt with; worth knowing,
                not worth alarming about.
      NOTHING   the latest finished run succeeded. The failures are history and the run
                table is where history belongs.

    Overdue stays its own alarm: a job that never fires writes no failure either.
    """
    out = []
    hist = run_history(10)
    live = [r for r in hist if r['running']]
    done = [r for r in hist if not r['running']]

    def broke(r):
        return r['exit'] not in (0, None) or r['failed'] or not r['finished']

    # THE CONSECUTIVE STREAK ENDING NOW, not every failure in the last ten logs. Listing
    # "18, 17, 16, 16, 14, 12" folds a live outage together with history somebody already
    # dealt with, and the reader cannot tell which is which.
    bad = []
    for r in done:
        if not broke(r):
            break
        bad.append(r)
    latest = done[0] if done else None

    if bad and latest and broke(latest):
        # A day that ran twice and failed twice is ONE broken day, not two.
        days = ', '.join(sorted({r['day'] for r in bad}, reverse=True))
        names = sorted({f for r in bad for f in r['failed']})
        if live:
            out.append(dict(kind='recovering',
                            head='Failed on %s — a run is going now' % days,
                            text=('Last break was in ' + ', '.join(names) + '. ' if names else '')
                                 + 'Watch it below; this clears when the run finishes.'))
        else:
            out.append(dict(kind='failed',
                            head='%d day%s failed: %s' % (len(set(r['day'] for r in bad)),
                                 '' if len(set(r['day'] for r in bad)) == 1 else 's', days),
                            text=('Broke on ' + ', '.join(names) + '. ' if names else '')
                                 + 'Nothing new has been ingested since, and no run is going.'))

    today = dt.date.today().isoformat()
    log = os.path.join(ROOT, 'build', 'refresh-logs', today + '.log')
    if not os.path.exists(log) and dt.datetime.now().hour >= 10:
        out.append(dict(kind='overdue', head='No run at all today (%s)' % today,
                        text='It is past 10am and there is no log for today. Check '
                             '`launchctl list | grep lunenburg` and that '
                             '../lunenburgbudgets-refresh still exists.'))
    return out




QUESTIONS_STALE_S = 3600


def reader_questions():
    """What residents have asked through /ask-a-question: counts, the rows, and WHEN CHECKED.

    Counts and metadata only. The bodies and any email addresses stay in the questions
    database and never reach this machine -- see scripts/pull_questions.py.

    THE LAST CHECK IS SHOWN, AND KEPT WITHIN THE HOUR. TJ, 9 October 2026: *"the last date it
    was checked so i know its accurate"*. The daily refresh pulls the questions in its own
    tree, and the file is gitignored, so this tree's copy only moved when somebody ran the
    pull by hand -- a dashboard could say `0 open` off a copy days old. So the copy is read
    from whichever tree checked most recently, and when that is over an hour ago this pulls
    again: one small read of a separate database, at most once an hour.
    """
    def stamp(tree):
        try:
            return open(os.path.join(tree, 'build', 'reader-questions-checked.txt')).read().strip()
        except OSError:
            return ''
    best = max((ROOT, TREE), key=stamp)
    checked = stamp(best)
    try:
        when = dt.datetime.fromisoformat(checked) if checked else None
        if when is not None and when.tzinfo is None:     # an older stamp, written as local time
            when = when.astimezone()
        age = (dt.datetime.now(dt.timezone.utc) - when).total_seconds() if when else None
    except ValueError:
        age = None
    if age is None or age > QUESTIONS_STALE_S:
        try:
            subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'pull_questions.py')],
                           cwd=ROOT, capture_output=True, timeout=120)
        except Exception:
            pass
        if stamp(ROOT) > checked:
            best, checked = ROOT, stamp(ROOT)
    f = os.path.join(best, 'sources', 'data', 'reader-questions.csv')
    if not os.path.exists(f):
        return None
    rs = list(csv.DictReader(open(f, encoding='utf-8')))
    open_ = [r for r in rs if (r.get('status') or '') != 'answered']
    return dict(total=len(rs), open=len(open_), answered=len(rs) - len(open_), rows=rs,
                checked=checked,
                newest=max((r.get('asked_at') or '' for r in rs), default=''),
                oldest_open=min((r.get('asked_at') or '' for r in open_), default=''))


# WHAT GOT DONE TODAY, BY CATEGORY. TJ, 19 September 2026: "the 'finished recently' is the
# individual jobs, but that's too detailed for me to draw insights from it, and it doesnt
# give me overall COUNTS of what was done and the category (Youtube found X videos. Built
# 100 transcripts)."
#
# Right: a list of fourteen steps with durations is a TRACE, and a trace is what you read
# when something went wrong. What a person wants on opening the page is the day's result
# -- how many transcripts, how many scans read, how many votes -- in the same shape as the
# running cards, so a job reads the same whether it is working or done.
#
# Counted from the files themselves rather than from anything a script printed. A log line
# says what a script believed; a file on disk with today's mtime is what actually landed,
# and the two have already disagreed on this page once (the refresh's own summary, written
# at the end, describing runs that never reached it).
# COUNTED FROM WHAT TIMESTAMPED THE WORK, NEVER FROM mtime.
#
# The first version of this counted files whose mtime fell after midnight and reported
# "11,795 scans read today" against an archive holding 1,687 of them. Two things touch
# mtimes in bulk and neither is work: extract_minutes.py rewrites every text file it
# checks, and the refresh tree runs `git reset --hard origin/main` before every run, which
# restamps everything that changed. A file's mtime answers "when was this last written",
# and the question here is "when was this DONE" -- adjacent, and not the same (rule 7's
# proxy trap, in the instrument rather than the analysis).
#
# So every count comes from a registry that records when the work happened, or from the
# run log, which prints each job as it completes. Where neither exists, the category is
# left out rather than estimated.

def done_today():
    """One card per category: how many landed today, and when the last one did."""
    today = dt.date.today().isoformat()
    live = {r['name'] for r in running() if not r.get('idle')}
    out = []

    def card(name, unit, n, last='', what=None):
        if n:
            out.append(dict(name=name, unit=unit, n=n, still_running=name in live,
                            last=ago(last) if last else '', at=clock(last),
                            what=what if what is not None else WHAT.get(name, ''),
                            costs=name in AGENTIC))

    def from_registry(f, col):
        ts = [r.get(col, '') for r in rows(f) if (r.get(col) or '').startswith(today)]
        return len(ts), max(ts) if ts else ''

    n, last = from_registry('ocr-minutes.csv', 'ocr_at')
    card('Reading scanned minutes', 'scans read', n, last)
    n, last = from_registry('youtube-transcript-index.csv', 'fetched_at')
    card('Fetching captions', 'transcripts fetched', n, last)

    # The reading jobs print one line each as they finish, in today's run log, and the
    # sweep logs its own to agentic-spend.csv. Both carry a real time.
    log = os.path.join(ROOT, 'build', 'refresh-logs', today + '.log')
    text = ''
    if os.path.exists(log):
        with open(log, encoding='utf-8', errors='replace') as fh:
            text = fh.read()
    spend = [r for r in rows('agentic-spend.csv') if (r.get('at') or '').startswith(today)]
    # A TIME, NOT JUST A COUNT. These two were the cards reading "done" with nothing
    # beside them -- TJ, 20 September 2026: "Seeing refresh failed and all that done today
    # is not believable." The run log prints these jobs without a clock, but
    # agentic-spend.csv stamps every one of them, so the last row for the stream is when
    # the work actually stopped. Where the log counted jobs the registry did not, the time
    # is still the registry's latest: it is a floor rather than a guess, and a floor is
    # checkable.
    def spend_at(stream):
        ts = [r['at'] for r in spend if r.get('stream') == stream and r.get('at')]
        return max(ts) if ts else ''

    card('Writing up a recorded meeting', 'meetings written up',
         len(re.findall(r'written \(\$', text)) + sum(1 for r in spend if r['stream'] == 'minutes'),
         spend_at('minutes'))
    # The unit is a SET OF MINUTES READ, never a vote counted -- see FOUND_PATTERNS.
    card('Reading the town’s official minutes', 'sets of minutes read',
         len(re.findall(r'wrote \d+ vote', text)) + sum(1 for r in spend if r['stream'] == 'votes'),
         spend_at('votes'))

    # What the WATCHERS found today: seeing, not making, and a different kind of work.
    seen = found_by_day().get(today, collections.Counter())
    for k, label in (('agendas', 'agendas'), ('minutes', 'sets of minutes'),
                     ('notices', 'town notices')):
        card('Found on the town’s site', label + ' spotted', seen.get(k, 0), what=
             'New since the last look — the watcher reports it, then the fetcher '
             'downloads it.')
    card('Found on the channel', 'recordings spotted', seen.get('videos', 0), what=
         'New uploads on the town’s YouTube channel.')

    # AND EVERY OTHER STEP THAT FINISHED TODAY. The four above are the ones that keep a
    # registry and can say how MANY; the rest of the run is real work too, and leaving it
    # off made a busy morning look like four things happened. Each is counted in runs --
    # the honest unit when nothing counts the output -- with the time it took.
    # A step whose output is already counted above must not appear again as "1 run": the
    # same work twice on one panel is the discrepancy this page exists to prevent, and the
    # registry card is the better of the two because it counts what landed.
    named = {c['name'] for c in out}
    counted = {'write_recording_minutes': 'Writing up a recorded meeting',
               'extract_official_votes': 'Reading the town’s official minutes',
               'ocr_scanned_minutes': 'Reading scanned minutes',
               'fetch_youtube_transcripts': 'Fetching captions'}
    runs = collections.Counter()
    secs = collections.Counter()
    for x in finished(400):
        if x['day'] != today:
            continue
        stem = x['step'].split('.py')[0].split()[0]
        runs[stem] += 1
        secs[stem] += x['seconds']
    for stem, n in runs.most_common():
        if counted.get(stem) in named:
            continue
        name, what = STEP_WORDS.get(stem, (stem + '.py', 'A step of the daily run.'))
        if name in named:
            continue
        mins = secs[stem] / 60
        out.append(dict(name=name, unit=('run' if n == 1 else 'runs') +
                        (', %.0f min' % mins if mins >= 1 else ''),
                        n=n, still_running=False, last='', what=what,
                        costs=stem.startswith('write_') or stem.startswith('extract_official')))
    return sorted(out, key=lambda r: -r['n'])


def finished(n=14):
    """Steps that ran and COMPLETED recently, newest first.

    TJ, 19 September 2026: "i was surprised that there are no other processes running. i
    think that means everything else completed? I guess i need to see somehow when things
    ran but completed too ... otherwise its confusing."

    Exactly the gap. A list of what is running answers half a question: an empty list
    means either everything finished or nothing ever started, and those are opposite
    situations that look identical. The page has been showing the half that alarms and
    hiding the half that reassures.

    The refresh log already records every step it completes -- `[name: 12.3s, exit 0]` --
    so this is a read, not a new measurement. Steps that took under two seconds are left
    out: a check that returns instantly is noise beside a fetch that took four minutes.
    """
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'build', 'refresh-logs', '*.log')),
                    reverse=True)[:2]:
        day = os.path.basename(f)[:10]
        try:
            with open(f, encoding='utf-8', errors='replace') as fh:
                text = fh.read()
        except OSError:
            continue
        # Newest step first WITHIN the day, and the days are already newest first -- so
        # today's most recent step leads. Reversing the whole flat list instead put
        # yesterday's earliest step at the top, which is the least interesting row there is.
        steps = []
        for m in re.finditer(r'\[([a-z_]+\.py[^:]*): ([\d.]+)s, exit (\d+)\]', text):
            secs = float(m.group(2))
            if secs < 2:
                continue
            steps.append(dict(day=day, step=m.group(1), seconds=secs, exit=int(m.group(3))))
        out.extend(steps[::-1])
        if len(out) >= n:
            break
    return out[:n]



# ONE TAB BAR, SHARED. Three pages that each wrote their own would drift the first time a
# fourth was added -- the stale-copy failure this repo has hit with every hand-kept list.
# THE WEEKLY PACING LINE, beside what is running. TJ, 9 October 2026: the minutes run paces
# to a straight line across the week (process_meeting.py --week-line), so the page shows the
# same two numbers the governor decides on -- the server's weekly bar and where the line is
# -- read from the same files, so the card and the run cannot disagree.
def _week_pacing_card():
    try:
        sys.path.insert(0, os.path.join(ROOT, 'scripts'))
        import usage_governor as G
        hist = G.readings()
        wr = G.week_reset()
    except Exception:
        return ''
    if not hist or not wr:
        return ''
    last = hist[-1]
    now = time.time()
    goal = 90.0
    m = re.search(r'--week-line\s+([\d.]+)', ' '.join(r.get('cmd', '') for r in running()))
    live = bool(m)
    if m:
        goal = float(m.group(1))
    line = G.week_line(goal, wr, now)
    u7 = last['u7']
    gap = u7 - line
    catch = ''
    if gap > 0:
        # when the line reaches today's bar, if nothing else is spent
        lo, hi = now, wr
        for _ in range(40):
            mid = (lo + hi) / 2
            if G.week_line(goal, wr, mid) < u7:
                lo = mid
            else:
                hi = mid
        catch = ' &middot; the line reaches %g%% around <b>%s</b>' % (u7, dt.datetime.fromtimestamp(hi).strftime('%a %H:%M'))
    state = (('<span class="pill">waiting</span>' if gap >= 0 else '<span class="pill go">filling</span>')
             if live else '<span class="pill">no paced run</span>')
    pct = lambda v: max(0.0, min(100.0, v))
    bar = ('<div style="position:relative;height:10px;background:#21262d;border-radius:5px;margin:8px 0 2px">'
           '<div style="position:absolute;left:0;top:0;bottom:0;width:%.1f%%;background:#d29922;border-radius:5px"></div>'
           '<div title="the line" style="position:absolute;top:-3px;bottom:-3px;left:%.1f%%;width:2px;background:#e6edf3"></div>'
           '</div>' % (pct(u7), pct(line)))
    return ('<div class="card"><div class="row"><b class="grow">Weekly pacing</b>%s</div>%s'
            '<div class="tiny">Weekly bar <b>%g%%</b> against a line at <b>%.1f%%</b> (%s %.1f points) &middot; goal %g%%, '
            'climbing to 100%% over the last day &middot; resets %s%s</div>'
            '<div class="tiny" style="color:#8b949e;margin-top:2px">The bar counts every session on the account, so a heavy '
            'interactive day raises it and the minutes run starts less; reading %s.</div></div>'
            % (state, bar, u7, line, 'ahead by' if gap >= 0 else 'behind by', abs(gap), goal,
               dt.datetime.fromtimestamp(wr).strftime('%a %d %b %H:%M'), catch, ago(dt.datetime.fromtimestamp(last['t'], dt.timezone.utc).isoformat())))


def tabs(sel, q=None):
    """The tab bar. `Questions (N)` carries the count of OPEN questions, so somebody waiting
    on an answer is visible from every page, not only from the Questions tab."""
    n = (q or {}).get('open') or 0
    items = [('index.html', 'Running'), ('backlog.html', 'Backlog'), ('sources.html', 'Documents'),
             ('questions.html', 'Questions' + (' (%d)' % n if n else ''))]
    return '<div class="tabs">%s</div>' % ''.join(
        '<a%s href="%s">%s</a>' % (' class="sel"' if href == sel else '', href, label)
        for href, label in items)


def page_live(st):
    # The refresh prints each job's cost as it finishes, so its spend so far is readable
    # from today's log -- an actual figure beats a tag that only warns it could spend.

    R, S, F, Q = st['running'], st['streams'], st['refresh'], st['queued']
    h = []
    h.append('<div class="wrap"><div class="row"><div class="grow"><h1>Ingestion</h1>'
             '<p class="sub">%s &middot; refreshes itself every 20s</p></div>'
             '%s</div>' % (st['generated'], tabs('index.html', st.get('questions'))))

    for a in st['alerts']:
        tone = {'failed': ('alert', 'no', 'REFRESH FAILED'),
                'recovering': ('warnbox', 'warn', 'FAILED — RERUNNING'),
                'overdue': ('alert', 'no', 'NO RUN TODAY')}[a['kind']]
        h.append('<div class="card %s"><div class="row"><span class="pill %s">%s</span>'
                 '<b class="grow">%s</b></div>'
                 '<div class="tiny" style="margin-top:4px">%s</div></div>'
                 % (tone[0], tone[1], tone[2],
                    html.escape(a['head']), html.escape(a['text'])))

    live = [x for x in R if x['name'] == 'Daily refresh']
    if live:
        r = live[0]
        found = ' &middot; '.join('<b>%d</b> %s' % (f['n'], f['label']) for f in F['found'])
        h.append('<div class="card runbox"><div class="row">'
                 '<span class="pill go">DAILY REFRESH RUNNING</span>'
                 '<b class="grow">%s</b><span class="tiny num">up %s</span></div>'
                 '%s%s%s</div>'
                 % (('now running <code>%s</code>' % html.escape(F['phase']['step']))
                    if F['phase']['step'] else 'between steps',
                    html.escape(r['elapsed']),
                    ('<div class="tiny" style="margin-top:8px">Found so far: %s</div>' % found)
                    if found else '',
                    ('<div class="tiny" style="margin-top:4px">Spent <b style="color:#c09cf5">'
                     '$%.2f</b> today — about %.1f%% of the week, all of it in the writing '
                     'phase.</div>' % (F['spent'], F['spent'] / 5)) if F['spent'] else '',
                    '<div class="tiny" style="margin-top:4px">Its individual steps appear '
                    'below, under Running now as they go and Done today when they '
                    'finish.</div>'))

    h.append(_week_pacing_card())

    h.append('<h2>Running now</h2>'
             '<p class="sub" style="margin:-4px 0 10px">'
             '<span class="tag agentic">agentic</span> spends the weekly plan allowance '
             '(<code>claude -p</code>). Everything else is free — local work, or just '
             'network.</p>')
    if not [x for x in R if x['name'] != 'Daily refresh']:
        h.append('<div class="card idle">No individual job is running.</div>')
    for r in [x for x in R if x['name'] != 'Daily refresh']:
        if r['done'] is not None and r['plan']:
            sc = ('<span class="pill go">%s of %s %s</span>'
                  % ('{:,}'.format(min(r['done'], r['plan'])), '{:,}'.format(r['plan']),
                     r.get('scope_word', 'this batch'))
                  + bar(r['done'], max(0, r['plan'] - r['done'])))
        elif r['done'] is not None:
            sc = ('<span class="pill" title="a looping wrapper: no total of its own">'
                  '%d since it started</span>' % r['done'])
        else:
            sc = ''
        # The refresh prints each job's cost as it finishes, so its spend so far is
        # readable from today's log. An actual figure on the wrapper beats a tag: it says
        # what was spent rather than warning that something might be.
        spent = (' <span class="tiny" style="color:#c09cf5">$%.2f today, in its agentic '
                 'step</span>' % F['spent']) if (r['name'] == 'Daily refresh' and F['spent']) else ''
        h.append('<div class="card %s"><div class="row" style="flex-wrap:nowrap">'
                 '<b class="grow" style="min-width:0">%s%s%s</b>'
                 '<span class="unit" style="width:11rem;text-align:right">%s</span>'
                 '<span class="when"><span class="pill %s">%s</span></span>'
                 '<span class="tiny num" style="width:6.5rem;text-align:right">up %s</span></div>'
                 '<div class="tiny">%s</div>%s<div class="mono tiny" style="margin-top:4px;color:#586069">%s</div></div>'
                 % ('' if r['idle'] else 'on', html.escape(r['name']),
                    ' <span class="tag agentic">agentic</span>' if r['costs'] else '',
                    spent, sc, '' if r['idle'] else 'go',
                    'waiting' if r['idle'] else
                    (('%d procs' % r['n']) if r['n'] > 1 else 'working'),
                    html.escape(r['elapsed']), html.escape(r['what']),
                    ('<div class="tiny" style="margin-top:4px">%s</div>' % r['extra'] if r.get('extra') else ''),
                    html.escape(r['cmd'])))

    # WHAT JUST FINISHED, in the same shape as what is running. Without this, "nothing is
    # running" cannot be told apart from "nothing ever started", and the first is fine
    # while the second is an outage.
    if st['done']:
        h.append('<h2>Done today</h2>')
        for d in st['done']:
            h.append('<div class="card done"><div class="row" style="flex-wrap:nowrap">'
                     '<b class="grow" style="min-width:0">%s%s</b>'
                     '<span class="metric">%s</span>'
                     '<span class="unit">%s</span>'
                     '<span class="when"><span class="pill %s">%s</span></span></div>'
                     '<div class="tiny" style="margin-top:4px">%s</div></div>'
                     % (html.escape(d['name']),
                        ' <span class="tag agentic">agentic</span>' if d['costs'] else '',
                        '{:,}'.format(d['n']), html.escape(d['unit']),
                        'go' if d['still_running'] else '',
                        'still going' if d['still_running']
                        else ('%s &middot; %s' % (d['at'], d['last'])
                              if d.get('at') and d['last']
                              else ('last %s' % d['last'] if d['last'] else 'no time recorded')),
                        html.escape(d['what'])))

    # The step-by-step trace stays, folded: it is what you read when something went wrong,
    # not what you open the page for.
    if st['finished']:
        h.append('<details data-k="trace" class="card"><summary class="tiny" '
                 'style="cursor:pointer;color:#6cb6ff">every step that finished, with '
                 'its duration</summary><table style="margin-top:8px">')
        for x in st['finished']:
            h.append('<tr><td class="mono">%s</td><td class="tiny">%s</td>'
                     '<td class="r num tiny">%s</td><td class="r">%s</td></tr>'
                     % (html.escape(x['step']), x['day'],
                        ('%.0fs' % x['seconds']) if x['seconds'] < 90
                        else '%.0fm' % (x['seconds'] / 60),
                        '<span class="pill go">done</span>' if x['exit'] == 0
                        else '<span class="pill no">exit %d</span>' % x['exit']))
        h.append('</table></details>')

    h.append('<h2>The daily refresh</h2>')
    h.append('<div class="card %s"><div class="row"><b class="grow">%s</b><span class="pill %s">%s</span></div>'
             % ('on' if F['live'] else '', 'Today&rsquo;s run &mdash; ' + F['today'],
                'go' if F['live'] else '', 'running' if F['live'] else 'not running'))
    # THE FIRST-CLASS OBJECTS, read off the run row that refresh.py wrote, so this panel
    # and the run's own printed summary cannot give two different answers. `refresh.py`
    # defines them in FIRST_CLASS; nothing else is counted here, and never a vote.
    fc = first_class_today(F['today'])
    if fc:
        h.append('<div class="row tiny" style="margin-top:8px">' + ' &middot; '.join(
            '<b>%d</b> %s' % (n, label) for label, n in fc) + '</div>')
    elif fc == []:
        h.append('<div class="row tiny" style="margin-top:8px">no new documents today</div>')
    elif fc is None:
        h.append('<div class="row tiny" style="margin-top:8px">'
                 'this run has not recorded its row yet</div>')
    elif F['found']:
        h.append('<div class="row tiny" style="margin-top:6px">Found: ' +
                 ' &middot; '.join('<b>%d</b> %s' % (f['n'], f['label']) for f in F['found']) + '</div>')
    if F['spent_n']:
        h.append('<div class="tiny" style="margin-top:4px">Spent today: <b>$%.2f</b> API-equivalent '
                 'across %d job(s) &mdash; about %.1f%% of the week.</div>'
                 % (F['spent'], F['spent_n'], F['spent'] / 5))
    h.append('</div>')

    h.append(_found_card(F['today']))

    h.append('<div class="card"><div class="tiny" style="margin-bottom:6px"><b>Where it looked today.</b> '
             'A watcher that did not run is a watcher that did not look.</div><table>')
    for w in F['looked']:
        links = ' &middot; '.join('<a href="%s" target="_blank">%s</a>'
                                  % (html.escape(u, quote=True), html.escape(t))
                                  for u, t in w['links'] if u)
        got = (' &middot; '.join('<b>%d</b> %s' % (f['n'], html.escape(f['label']))
                                 for f in w.get('found', []))
               or ('<span style="opacity:.55">nothing new</span>' if w['ran'] else ''))
        h.append('<tr><td><b>%s</b><div class="tiny">%s</div></td>'
                 '<td class="tiny">%s</td><td class="tiny">%s</td><td class="r">%s</td></tr>'
                 % (html.escape(w['label']), html.escape(w['where']), links, got,
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

    h.append('<h2>Recent refresh runs</h2>'
             '<p class="sub" style="margin:-4px 0 10px">What each run SAW, counted from the '
             'watchers’ own event logs — which are written the moment something is spotted, '
             'so a run that died later still reports what it found.</p>'
             '<div class="card"><table>'
             '<tr><th>day</th><th style="width:7.5rem">outcome</th><th class="r">agendas</th><th class="r">minutes</th>'
             '<th class="r">recordings</th><th class="r">notices</th><th>note</th></tr>')
    for r in F['history']:
        row = r['row'] or {}
        if r['running']:
            state = '<span class="pill go">running</span>'
        elif r['exit'] == 0 or (r['finished'] and r['exit'] is None and not r['failed']):
            state = '<span class="pill go">ok</span>'
        elif r['exit'] is None and not r['finished']:
            state = '<span class="pill warn">stopped part-way</span>'
        else:
            state = '<span class="pill no">FAILED</span>'
        note = ('broke on ' + ', '.join(r['failed'])) if r['failed'] else (row.get('notes') or '')
        if not row and not r['running']:
            note = (note + ' — ' if note else '') + 'wrote no row: it died before recording the run'
        h.append('<tr><td class="mono" style="white-space:nowrap">%s%s'
                 '<div class="tiny">%s</div></td><td>%s</td>'
                 '<td class="r num">%s</td><td class="r num">%s</td><td class="r num">%s</td>'
                 '<td class="r num">%s</td><td class="tiny">%s</td></tr>'
                 % (r['day'],
                    ('<span class="tiny" style="color:#d29922"> %s</span>' % r['again'])
                    if r['again'] else '',
                    r['mtime'], state,
                    r['seen'].get('agendas') or '·', r['seen'].get('minutes') or '·',
                    r['seen'].get('videos') or '·', r['seen'].get('notices') or '·',
                    html.escape(note[:120])))
    h.append('</table></div></div>')
    return ''.join(h)

def page_questions(st):
    """What readers have asked, on its own tab. TJ, 9 October 2026: *"Questions from Readers
    should be a whole tab"*, with the last check beside the figures *"so i know its
    accurate"*."""
    q = st.get('questions')
    h = ['<div class="wrap"><div class="row"><div class="grow"><h1>Questions from readers</h1>'
         '<p class="sub">%s</p></div>%s</div>' % (st['generated'], tabs('questions.html', q))]
    if not q:
        h.append('<div class="card idle">No questions file yet &mdash; run '
                 '<code>python3 scripts/pull_questions.py</code>.</div></div>')
        return ''.join(h)
    checked = q.get('checked') or ''
    h.append('<div class="card %s"><div class="row"><b class="grow">%d open</b>'
             '<span class="pill %s">%d answered of %d</span></div>'
             '<div class="tiny" style="margin-top:6px">Last checked <b>%s</b>%s &middot; checked '
             'again whenever the last check is over an hour old, and by every daily refresh</div>'
             % ('on' if q['open'] else '', q['open'], 'warn' if q['open'] else '', q['answered'],
                q['total'], html.escape(checked.replace('T', ' ')[:16]) if checked else 'never',
                (' (%s)' % ago(checked)) if checked else ''))
    if q['open'] and q['oldest_open']:
        h.append('<div class="tiny" style="margin-top:4px">Oldest unanswered: <b>%s</b> &middot; '
                 'answer at <a href="https://lunenburgbudgetproject.org/ask-a-question" '
                 'target="_blank">/ask-a-question</a></div>' % ago(q['oldest_open']))
    h.append('</div>')
    h.append('<h2>Every question</h2><p class="sub" style="margin:-4px 0 10px">Metadata only. '
             'The words and any email address stay in the questions database and never reach '
             'this machine; read and answer them at /ask-a-question.</p>'
             '<div class="card"><table><tr><th>asked</th><th>status</th><th>topic</th>'
             '<th class="r">length</th><th>email</th><th>country</th></tr>')
    for r in sorted(q['rows'], key=lambda r: r.get('asked_at') or '', reverse=True):
        st_ = r.get('status') or ''
        h.append('<tr><td class="mono tiny">%s</td><td><span class="pill %s">%s</span></td>'
                 '<td>%s</td><td class="r num">%s chars</td><td>%s</td><td>%s</td></tr>'
                 % (html.escape((r.get('asked_at') or '').replace('T', ' ')[:16]),
                    '' if st_ == 'answered' else 'warn', html.escape(st_ or 'open'),
                    html.escape(r.get('topic') or '\u2014'), html.escape(r.get('body_chars') or ''),
                    'yes' if r.get('has_email') == '1' else 'no', html.escape(r.get('country') or '')))
    h.append('</table></div></div>')
    return ''.join(h)


def page_backlog(st):
    """What is still owed: every stream's remainder, and anything waiting in the inbox.

    THE BACKLOG IS A DIFFERENT QUESTION FROM THE PIPELINE. TJ, 19 September 2026: "lets
    put 'Streams' and 'inbox' in a new tab that is something related to 'open things'."

    Right, and they were on the wrong page. "Running" answers IS IT WORKING -- checked
    when you want reassurance, or a cause. This answers WHAT IS STILL OWED, which is a
    planning question asked at a different moment; burying it under a live process list
    meant scrolling past what is happening to reach what is outstanding.
    """
    S, Q = st['streams'], st['queued']
    # NO CROSS-UNIT TOTAL. This line said `18,001 still to process`, which added 13,222
    # ROWS to 2,880 SETS OF MINUTES to 1,884 RECORDINGS to 15 PAGES. Nothing in the world
    # is 18,001 of anything, and the figure sat in the largest type on the page -- exactly
    # where a reader takes a number to quote it. Rule 7b: ten children, ten documents and
    # ten budget lines must not look alike, and adding them is the same error committed
    # once rather than four times.
    open_streams = [x for x in S if (x['todo'] or 0) > 0]
    biggest = max(open_streams, key=lambda x: x['todo']) if open_streams else None
    unfiled = sum(1 for q in Q if q['ingested'] is False)
    h = []
    h.append('<div class="wrap"><div class="row"><div class="grow"><h1>Backlog</h1>'
             '<p class="sub">%s%s &middot; %s</p></div>%s</div>'
             % (('%d of %d streams have work outstanding; the largest is %s'
                 % (len(open_streams), len(S),
                    _counted(biggest['todo'], biggest.get('unit'), remaining=True)))
                if biggest else 'every stream is complete',
                (', %d delivery not filed' % unfiled) if unfiled == 1 else
                (', %d deliveries not filed' % unfiled) if unfiled else '',
                st['generated'], tabs('backlog.html', st.get('questions'))))
    bd = backlog_depth()
    if bd and bd.get('total_jobs'):
        h.append(backlog_chart(bd))
    h.append('<h2>Streams</h2>')
    for s in S:
        todo = s['todo']
        h.append('<div class="card"><div class="row"><b class="grow">%s</b>'
                 '<span class="tiny">%s</span>'
                 '<span class="num">%s</span>'
                 '<span class="pill %s">%s</span></div>%s'
                 '<div class="tiny" style="margin-top:6px">%s</div>'
                 '<div class="tiny" style="margin-top:4px">%s &middot; %s%s</div>'
                 % (html.escape(s['name']) +
                    (' <span class="tag agentic">agentic</span>'
                     if 'allowance' in s['cost'] else ''),
                    ('last landed %s' % html.escape(s['last'])) if s['last'] else '',
                    s.get('headline') or
                    _counted(s['done'], s.get('unit'), total=(s['done'] + (todo or 0))),
                    'go' if todo == 0 else 'warn',
                    # `complete` with blocked pages on it overstates the thing. Say both.
                    ('complete' if not s.get('blocked')
                     else 'complete &middot; %d blocked' % s['blocked']) if todo == 0 else
                    (s.get('pill') or _counted(todo, s.get('unit'), remaining=True)
                     if todo is not None else 'unknown'),
                    bar(s['done'], todo or 0, s.get('blocked') or 0), s.get('io', ''), html.escape(s['cost']),
                    html.escape(s['note']),
                    (' &middot; %d blocked: %s' % (s['blocked'], html.escape(s['blocked_why']))) if s['blocked'] else ''))
        # THE TERMS, ITEMISED AND NOT COLLAPSED. A headline of `unfinished` is only honest
        # if what it is made of is visible without a click -- four states, four different
        # jobs, and the one that costs model tokens marked as such. A zero row is KEPT:
        # `UNREAD 0` is the most useful line here, because it says no amount of spend moves
        # this stream, and a row that disappears when it reaches zero cannot say that.
        for term, n, means, action in (s.get('breakdown') or []):
            h.append('<div class="tiny" style="margin-top:4px;display:flex;gap:8px;'
                     'flex-wrap:wrap">'
                     '<b style="flex:0 0 5.5rem;color:%s">%s</b>'
                     '<span style="flex:0 0 3.5rem;text-align:right">%s</span>'
                     '<span class="grow">%s</span>'
                     '<span style="color:#8b949e">%s</span></div>'
                     # BLOCKED IS RED AND MATCHES ITS SEGMENT IN THE BAR. It was grey,
                     # the colour this card uses for `a count that is zero and tells you
                     # so`, so the one state nothing can move looked like the states that
                     # had nothing in them. A reader following a red segment in the bar
                     # down to the counts has to land on the same colour.
                     % ('#3fb950' if term == 'PROVEN' else
                        '#f85149' if term == 'BLOCKED' else
                        '#d29922' if term in ('UNPROVEN', 'REFUSED') else '#8b949e',
                        html.escape(term), '{:,}'.format(n), html.escape(means), action))
        if s.get('chart'):
            h.append(s['chart'])
        # THE BREAKDOWN, COLLAPSED. A backlog total says how worried to be; the boards and
        # the years say what it actually is. Collapsed because the number is the thing a
        # glance wants and the detail is the thing a decision wants.
        pend = s.get('pending') or []
        if pend:
            n = sum(p['n'] for p in pend)
            # THE RANK IS A COLUMN, because the order of the rows is a claim and a
            # reader should be able to see what it rests on rather than infer it.
            ranked = any('rank' in p for p in pend)
            h.append('<details data-k="%s" style="margin-top:8px"><summary class="tiny" '
                     'style="cursor:pointer;color:#6cb6ff">%s across %d group(s) &mdash; '
                     'what is left, and in what order</summary>'
                     '<table style="margin-top:8px">'
                     '<tr>%s<th>group</th><th class="r">left</th><th>earliest</th>'
                     '<th>latest</th><th>years</th></tr>'
                     % (s['key'], '{:,}'.format(n), len(pend),
                        '<th class="r">rank</th>' if ranked else ''))
            for r in pend:
                # CHIPS THAT WRAP, NOT A DETAILS INSIDE A DETAILS. TJ: "on the 'dates'
                # expandable in the backlog, that is poor UX. It expands horitonzally and
                # vertically and loooks awful."
                #
                # It did. A nested <details> in a table cell opens to a 420px block of
                # space-separated dates, which widens the column, pushes the table past
                # the page and leaves a ragged hole where the row used to be -- and it
                # hid the one thing the breakdown is for behind a second click. The dates
                # are now inline chips that wrap inside the cell they belong to: the
                # shape of a backlog is legible at a glance, the table keeps its width,
                # and nothing has to be opened.
                chips = ''.join(
                    '<span style="display:inline-block;padding:1px 6px;margin:1px 3px 1px 0;'
                    'border-radius:9px;background:#1d2530;color:#9fb4cc;font-size:10px;'
                    'white-space:nowrap">%s</span>' % html.escape(d)
                    for d in r['dates'][:60])
                more = ('<span class="tiny" style="color:#6e7681"> +%d more</span>'
                        % (len(r['dates']) - 60)) if len(r['dates']) > 60 else ''
                rk = ('<td class="r num" style="vertical-align:top;color:#6cb6ff">%s</td>'
                      % (r['rank'] if r.get('rank', 99) < 99 else '\u2014')) if ranked else ''
                h.append('<tr>%s<td style="vertical-align:top">%s</td>'
                         '<td class="r num" style="vertical-align:top">%d</td>'
                         '<td class="mono tiny" style="vertical-align:top">%s</td>'
                         '<td class="mono tiny" style="vertical-align:top">%s</td>'
                         '<td style="max-width:460px">%s%s</td></tr>'
                         % (rk, html.escape(r['board'].replace('-', ' ')), r['n'],
                            r['first'], r['last'], chips, more))
            h.append('</table></details>')
        h.append('</div>')

    # THE HEADING WAS LYING. TJ, 19 September 2026: "for 'Queued, not yet ingested', i see
    # things labeled 'ingested'.. not sure what that means." Of course -- the section was
    # named for one outcome and listed both, so the label contradicted the heading. It is
    # the INBOX: what is sitting in it, and whether each delivery has been filed.
    # THE PLAN SECTION WAS REMOVED 6 October 2026. TJ: *"remove 'The plan' part of the
    # backlog. we are not following that."* A plan nobody follows, on the page people read
    # to see what happens next, is a confident wrong answer. ingest-plan.csv and its
    # generator still exist; nothing here renders them.
    h.append('<h2>The inbox</h2><p class="sub" style="margin:-4px 0 10px">'
             'Deliveries dropped in <code>build/inbox/</code>. Matched to the archive by '
             'checksum, so a file renamed on filing is still recognised.</p>')
    if not Q:
        h.append('<div class="card idle">The inbox is empty.</div>')
    for q in Q:
        h.append('<div class="card"><div class="row"><b class="grow mono">%s</b>'
                 '<span class="pill %s">%s</span><span class="tiny num">%s</span></div>'
                 '<div class="tiny">%s</div></div>'
                 % (html.escape(q['name']),
                    'go' if q['ingested'] else ('' if q['ingested'] is None else 'no'),
                    'filed' if q['ingested'] else ('unreadable' if q['ingested'] is None else 'NOT FILED'),
                    '{:,} B'.format(q['bytes']) if q['bytes'] else '', html.escape(q['note'])))

    h.append('</div>')
    return ''.join(h)


# -------------------------------------------------- what we HOLD, by fiscal year
#
# TJ, 28 September 2026: *"can you generate a similar bar chart on the DOCUMENTS tab of the
# dash that shows the FY breakdown of what we have?"*
#
# The Backlog chart is what is LEFT; this is what is HELD, and the two are read together.
# Stacked by ORIGIN rather than by kind, because that is the distinction the tab's own
# chips already make and the one that matters to a reader: what the town, district or
# state PUBLISHED, what is OURS (extracted text, transcripts, our minutes), and what came
# by request with no public address.
#
# THE YEAR COMES OFF THE DOCUMENT'S OWN NAME. A meeting document carries its date, a
# budget document usually carries an FY; 31,081 of 32,110 keys yield one. What does not is
# counted as `no date` and shown, because dropping it would make the bars add to less than
# the total with nothing saying why.
DOC_FY_DATE = re.compile(r'(?:^|[/_-])(20[0-2][0-9])-(\d{2})-\d{2}')
DOC_FY_NAME = re.compile(r'\bfy[-_ ]?(20[0-2][0-9]|[0-2][0-9])\b', re.I)
ORIGIN_COLOUR = [('published', '#6cb6ff', 'published by the town, district or state'),
                 ('ours', '#a371f7', 'ours \u2014 extracted text, transcripts, our minutes'),
                 ('request', '#d29922', 'by request \u2014 no public address')]


def doc_fiscal_year(key):
    m = DOC_FY_DATE.search(key)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        return 'FY%d' % (y + 1 if mo >= 7 else y)
    m = DOC_FY_NAME.search(key)
    if m:
        v = m.group(1)
        return 'FY%d' % (int(v) if len(v) == 4 else 2000 + int(v))
    return ''


def docs_fy_chart(docs):
    """One stacked bar per fiscal year of what the archive HOLDS, by origin."""
    by = collections.defaultdict(lambda: collections.Counter())
    undated = collections.Counter()
    for d in docs:
        fy = doc_fiscal_year(d[0] or '')   # d[0] is the full key; d[4] is its top folder
        (by[fy] if fy else undated)[d[5]] += 1
    rows = [(fy, by[fy]) for fy in sorted(by)]
    if not rows:
        return ''
    hi = max(sum(c.values()) for _, c in rows)
    W, H, PAD, GAP = 1000, 200, 26, 4
    bw = max(6.0, (W - PAD * 2) / max(len(rows), 1) - GAP)
    out = ['<div class="card"><div class="row"><b class="grow">What we hold, by fiscal '
           'year of the document</b><span class="tiny">%s documents &middot; tallest bar '
           '%s</span></div>' % (format(len(docs), ','), format(hi, ','))]
    out.append('<svg viewBox="0 0 %d %d" width="100%%" height="%d" '
               'style="display:block;margin:8px 0 2px">' % (W, H, H))
    base = H - 26
    for i, (fy, c) in enumerate(rows):
        x = PAD + i * (bw + GAP)
        y = base
        for name, col, _ in ORIGIN_COLOUR:
            n = c.get(name, 0)
            if not n:
                continue
            bh = (base - 14) * n / hi
            y -= bh
            out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s">'
                       '<title>%s %s: %s</title></rect>'
                       % (x, y, bw, bh, col, fy, name, format(n, ',')))
        out.append('<text x="%.1f" y="%d" fill="#8b949e" font-size="10" '
                   'text-anchor="middle">\u2019%s</text>' % (x + bw / 2, base + 12, fy[-2:]))
        out.append('<text x="%.1f" y="%.1f" fill="#e6edf3" font-size="9.5" '
                   'text-anchor="middle">%s</text>'
                   % (x + bw / 2, y - 3, format(sum(c.values()), ',')))
    out.append('</svg>')
    out.append('<div class="tiny">%s</div>'
               % ' &nbsp; '.join('<span style="color:%s">\u25a0</span> %s' % (c, lbl)
                                 for _, c, lbl in ORIGIN_COLOUR))
    out.append('<div class="tiny" style="margin-top:4px">The year is read off the '
               'document\u2019s own name \u2014 a meeting document carries its date, a '
               'budget document an FY. %s carry neither and are not in a bar, which is why '
               'the bars come to less than the total. This is what we HOLD; the Backlog '
               'tab is what is left to do with it.</div></div>'
               % format(sum(undated.values()), ','))
    return ''.join(out)

def page_sources(st, n, counts, kinds, docs=()):
    def chips(group, items):
        return ''.join(
            '<a href="#" class="chip" data-g="%s" data-v="%s">%s <b>%s</b></a>'
            % (group, k, lbl, '{:,}'.format(cnt))
            for k, lbl, cnt in items)

    origin = chips('o', [('', 'Everything', counts.get('', 0)),
                         ('published', 'Published by the town, district or state', counts.get('published', 0)),
                         ('ours', 'Ours', counts.get('ours', 0)),
                         ('request', 'By request — no public address', counts.get('request', 0))])
    # Ordered by how many there are, so the big piles are reachable first and a long tail
    # does not push them off the row.
    kind = chips('k', [('', 'Any kind', n)] +
                 [(k, k, c) for k, c in kinds.most_common(10)])
    return ('<div class="wrap"><div class="row"><div class="grow"><h1>Documents</h1>'
            '<p class="sub">%s held &middot; %s</p></div>'
            '%s</div>'
            '%s'
            '<div class="chips" data-g="o">%s</div>'
            '<div class="chips" data-g="k">%s</div>'
            '<input type="search" id="q" placeholder="filter by path, folder or address — e.g. select-board 2025, or munis, or xlsx">'
            '<p class="tiny" id="c" style="margin:8px 0"></p>'
            '<table><tr><th>document</th><th>kind</th><th class="r">size</th>'
            '<th>where it came from</th><th>sha256</th></tr><tbody id="t"></tbody></table>'
            '<p class="tiny" id="more"></p></div>'
            % ('{:,}'.format(n), st['generated'], tabs('sources.html', st.get('questions')),
               docs_fy_chart(docs), origin, kind))


KEEP = """
/* THE PAGE RELOADS ITSELF EVERY 20s, AND THAT USED TO THROW AWAY WHAT YOU WERE READING.
   Any breakdown you expanded collapsed again and the scroll jumped to the top -- so the
   one thing the detail is for, reading it, was the one thing you could not do.

   fetch() of a local file is blocked by the browser, so there is no swapping content in
   place without a server. What there is: remember which <details> were open and where the
   page was, and put both back on the way in. The reload still happens; it stops being
   visible. */
(function(){
  const K='ingest-open', S='ingest-scroll';
  const all=()=>[...document.querySelectorAll('details[data-k]')];
  try{
    const open=new Set(JSON.parse(sessionStorage.getItem(K)||'[]'));
    all().forEach(d=>{if(open.has(d.dataset.k))d.open=true});
    const y=+sessionStorage.getItem(S)||0; if(y)window.scrollTo(0,y);
  }catch(e){}
  const save=()=>{try{
    sessionStorage.setItem(K,JSON.stringify(all().filter(d=>d.open).map(d=>d.dataset.k)));
    sessionStorage.setItem(S,String(window.scrollY));
  }catch(e){}};
  document.addEventListener('toggle',save,true);
  window.addEventListener('scroll',()=>{clearTimeout(window._t);window._t=setTimeout(save,150)});
  window.addEventListener('beforeunload',save);
})();
"""

JS = """
const fmt=b=>b>1e6?(b/1e6).toFixed(1)+' MB':b>1e3?Math.round(b/1e3)+' KB':b+' B';
const t=document.getElementById('t'),q=document.getElementById('q'),c=document.getElementById('c'),
      more=document.getElementById('more');
const CAP=400; const F={o:'',k:''};
/* THREE KINDS OF "no address" AND ONLY ONE IS A GAP: ours has no publisher but us, a
   records delivery never had a public address, a published document has one. The chips
   above carry the explanation, so the cell carries only the tag -- a sentence in a cell
   is unreadable at a glance and pushes the columns that matter off the screen. */
/* The publisher, from the address, so the column says WHOSE it is in one word. The full
   URL is the link's title, one hover away, and the link itself is the way to open it. */
const host=u=>{try{const h=new URL(u).hostname.replace(/^www\./,'');
  return {'lunenburgma.gov':'town','lunenburgschools.net':'district',
          'lunenburgonline.com':'district','drive.google.com':'drive',
          'docs.google.com':'drive','doe.mass.edu':'DESE','mass.gov':'state',
          'youtube.com':'youtube'}[h]||h.split('.').slice(-2)[0];}catch(e){return 'link'}};
const WHERE={ours:'<span class="tag ours">ours</span>',
             request:'<span class="tag req">by request</span>'};
function draw(){
  const s=q.value.toLowerCase().split(/\s+/).filter(Boolean);
  const hit=DOCS.filter(d=>(!F.o||d[5]===F.o)&&(!F.k||d[6]===F.k)&&
    s.every(w=>d[0].toLowerCase().includes(w)||(d[2]||'').toLowerCase().includes(w)));
  c.textContent=hit.length.toLocaleString()+' of '+DOCS.length.toLocaleString()+' documents'+
    (hit.length>CAP?' \u2014 showing the first '+CAP:'');
  t.innerHTML=hit.slice(0,CAP).map(d=>
    '<tr><td class="mono">'+d[0]+'</td><td class="tiny">'+d[6]+'</td>'+
    '<td class="r num">'+fmt(d[1])+'</td><td>'+
    (d[2]?'<a class="lnk" href="'+d[2]+'" target="_blank" title="'+d[2]+'">'+host(d[2])+' \u2197</a>'
         :(WHERE[d[5]]||''))+
    '</td><td class="mono tiny">'+d[3]+'</td></tr>').join('');
  more.textContent=hit.length>CAP?'Narrow the filter to see the rest.':'';
}
document.querySelectorAll('.chip').forEach(a=>a.addEventListener('click',e=>{
  e.preventDefault(); const g=a.dataset.g; F[g]=a.dataset.v;
  document.querySelectorAll('.chip[data-g="'+g+'"]').forEach(x=>x.classList.toggle('sel',x===a));
  draw();
}));
document.querySelectorAll('.chips').forEach(r=>r.querySelector('.chip').classList.add('sel'));
q.addEventListener('input',draw);draw();
"""

def write(open_it=False):
    _ONCE.clear()
    os.makedirs(OUT, exist_ok=True)
    st = dict(generated=dt.datetime.now().strftime('%a %d %b, %H:%M:%S'),
              running=running(), streams=streams(), refresh=refresh(), queued=queued(),
              alerts=alert(), finished=finished(), done=done_today(),
              questions=reader_questions())
    docs = sources()
    shell = ('<!doctype html><meta charset=utf-8><meta name=viewport '
             'content="width=device-width,initial-scale=1"><title>%s</title>'
             '%s<style>%s</style>%s')
    with open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8') as fh:
        fh.write(shell % ('Ingestion', '<meta http-equiv="refresh" content="20">', CSS,
                          page_live(st)) + '<script>' + KEEP + '</script>')
    # The document list is written as a <script>, not JSON: a browser will not fetch() a
    # local file but will happily <script src> one.
    with open(os.path.join(OUT, 'docs.js'), 'w', encoding='utf-8') as fh:
        fh.write('const DOCS=' + json.dumps(docs, separators=(',', ':')) + ';')
    # BUILD IT, THEN OPEN THE FILE. `open(path, 'w')` truncates immediately, so a crash
    # while the page is still being composed -- inside the write call -- leaves ZERO
    # BYTES where a working page was. That is what happened: a KeyError in the plan
    # section emptied backlog.html, and the browser then reported
    # "Unsafe attempt to load URL file://... 'file:' URLs are treated as unique security
    # origins", which is what Chrome says about an empty document and names nothing about
    # the real cause two frames away.
    #
    # Composed first, the previous good page survives a failure. A stale dashboard is a
    # far better failure than a blank one, because a blank one looks like a browser
    # problem and gets debugged in the wrong place.
    _backlog = (shell % ('Backlog', '<meta http-equiv="refresh" content="60">', CSS,
                         page_backlog(st)) + '<script>' + KEEP + '</script>')
    with open(os.path.join(OUT, 'backlog.html'), 'w', encoding='utf-8') as fh:
        fh.write(_backlog)
    _questions = (shell % ('Questions', '<meta http-equiv="refresh" content="60">', CSS,
                           page_questions(st)) + '<script>' + KEEP + '</script>')
    with open(os.path.join(OUT, 'questions.html'), 'w', encoding='utf-8') as fh:
        fh.write(_questions)
    with open(os.path.join(OUT, 'sources.html'), 'w', encoding='utf-8') as fh:
        counts = collections.Counter(d[5] for d in docs)
        counts[''] = len(docs)
        kinds = collections.Counter(d[6] for d in docs)
        fh.write(shell % ('Documents', '', CSS,
                                 page_sources(st, len(docs), counts, kinds, docs))
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
