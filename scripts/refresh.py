#!/usr/bin/env python3
"""One run that brings the archive up to today, deterministically, and says what changed.

    python3 scripts/refresh.py                # watch, fetch, write, rebuild; commit and deploy nothing
    python3 scripts/refresh.py --commit       # ...and commit ONLY the files it wrote; push when on main
    python3 scripts/refresh.py --deploy       # ...and build the site and deploy it (implies --commit)
    python3 scripts/refresh.py --dry-run      # watch only; write nothing, fetch nothing
    python3 scripts/refresh.py --no-minutes   # skip the model step (costs money per meeting)
    python3 scripts/refresh.py --check        # every watcher's state holds together

QUEUE item 12. TJ: "deterministic". Every step here is a script that already answers
"what changed since last time" from a committed state file and is idempotent on its own;
this runs them in the order their outputs feed each other, and ends with a digest that is
DERIVED from their event logs rather than accumulated across runs.

THE ORDER, AND WHY IT CANNOT MOVE

  1. watch_meetings      what appeared on the town's AgendaCenter (agendas, minutes)
  2. fetch_agendas       the documents themselves, for this year -- resumable, skips held
  3. extract_minutes     text out of anything new (Word and Excel too)
  3b. agenda previews    the UPCOMING notice: what is on a policy-board agenda dated today
                         or later, quoted from the agenda, with a Facebook text to paste
  3c. watch_feeds        the town's news flash and alert feeds; linked, never republished
  3d. watch_documents    new documents on the district's budget page and the town's finance
                         pages, through the crawlers that built the mirrors
  4. watch_youtube       what appeared on the town's channel (the RSS feed, no key)
  5. classification      which board a new video belongs to, from its title
  6. transcripts         captions for recent meetings -- re-tried every run, because
                         YouTube's auto-captions arrive hours to days after the upload
  7. minutes             OUR minutes, for recordings inside the approved POLICY only
  7b. reconcile          ours against the town's minutes where both exist: caption
                         errors resolved beside the as-heard reading, real differences flagged
  8. rebuild             the feed, the minutes payload, the notices, the index, the metrics
  9. push                the search index and the analysis database to D1, incrementally
 10. commit              only the files this run wrote (refresh_git.py), replayed onto main
 11. deploy              only with --deploy, only from main's own commit, gated only on the
                         generators this run executed. Rule 10: nothing deploys unasked.

THE POLICY FILE IS THE APPROVAL. `sources/data/recording-minutes-policy.csv` names which
boards, from which date, TJ has approved minutes for. Step 7 writes minutes for a
recording only if a policy row covers it, and at most MAX_MINUTES_PER_RUN of them, because
that step draws on the Max plan's weekly allowance (~0.09% a meeting) and everything else
here is free. Rows carry a `priority`; `*` covers any board.

TWO THINGS IT REFUSES TO DO AT ONCE. If the transcript backfill is running it skips the
caption fetch rather than competing for the same rate limit (the pattern is written so it
cannot match its own argv -- see CLAUDE.md on pgrep).

IT PUSHES THE ANALYSIS DATABASE TOO (`sync_d1.py`, incremental), TJ, 24 October 2026:
*"the daily refresh can push the database."* It used to be a decision because D1 STOPPED
at 100,000 writes a day on the free plan. On Workers Paid (since 9 October 2026) writes are
a monthly allowance, and six tables -- the school journal among them -- had gone unpushed
for days because nobody ran it by hand, so `/api/query` answered "no such table".
"""
import argparse
import csv
import datetime as dt
import glob
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, 'scripts')
sys.path.insert(0, SCRIPTS)
import archive_storage  # noqa: E402  -- the one line between a publisher's document and our renderings
POLICY = os.path.join(ROOT, 'sources', 'data', 'recording-minutes-policy.csv')
RUNS = os.path.join(ROOT, 'sources', 'data', 'refresh-runs.csv')
WHATS_NEW = os.path.join(ROOT, 'fy28', 'public', 'data', 'whats-new.json')
MEETING_EVENTS = os.path.join(ROOT, 'sources', 'data', 'meeting-watch-events.csv')
YOUTUBE_EVENTS = os.path.join(ROOT, 'sources', 'data', 'youtube-watch-events.csv')
FEED_EVENTS = os.path.join(ROOT, 'sources', 'data', 'feed-watch-events.csv')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
FEED_SOURCES = os.path.join(ROOT, 'sources', 'data', 'feed-sources.csv')
DOC_EVENTS = os.path.join(ROOT, 'sources', 'data', 'document-watch-events.csv')
TRANSCRIPT_INDEX = os.path.join(ROOT, 'sources', 'data', 'youtube-transcript-index.csv')
RECORDED = os.path.join(ROOT, 'sources', 'data', 'recording-minutes')
FEED_EVENTS = os.path.join(ROOT, 'sources', 'data', 'feed-watch-events.csv')
MANIFEST = os.path.join(ROOT, 'sources', 'data', 'archive-manifest.csv')
BUDGET_DOCS = (os.path.join(ROOT, 'sources', 'district-budget', 'index.csv'),
               os.path.join(ROOT, 'sources', 'town-budget', 'index.csv'))
OTHER_DOCS = (os.path.join(ROOT, 'sources', 'town-supplementary', 'index.csv'),)
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
# THREE A DAY. Measured 13-14 September 2026: one minutes run is about 0.09% of the Max
# plan's weekly allowance, so three a day is ~2% a week -- the pace TJ set. The whole
# backlog of transcripts (~880) clears in about ten months at this pace; raise it here
# if he wants faster, never past ~20 (2% a DAY). See ~/.claude/CLAUDE.md.
MAX_MINUTES_PER_RUN = 3
# The town's own minutes, read for their votes: cheap (a short document, the small model,
# every quote checked) but 4,600 of them, so newest first and capped, every board.
MAX_OFFICIAL_VOTES_PER_RUN = 40
MAX_OCR_PER_RUN = 40             # ~20 minutes of local CPU; nothing charged to the plan
MAX_RECONCILE_PER_RUN = 10       # ~3 minutes, ~$3; excludes nothing, just bounds a run
SEARCH_PUSH_LIMIT = 20000       # rows; leaves the day's budget for a data push too
DB_PUSH_LIMIT = 40000           # rows a run; a table bigger than this goes in slices
TRANSCRIPT_WINDOW_DAYS = 21     # captions are retried for meetings this recent

# THE PAYLOADS THE SITE SERVES, rebuilt every run because the database is.
#
# The refresh never rebuilt `lunenburg.db` at all, so every payload derived from it drifted
# from the day's own data and the run deployed anyway: on 29 September 2026 merging one
# refresh commit took check_generated from 3 failures to 28. A reader was served athletics,
# Chapter 70, peer spending and twenty more built from a database nobody had rebuilt.
#
# EXTRACTORS ARE DELIBERATELY ABSENT. These are pure functions of the database and the
# tracked CSVs -- read, write a payload, touch nothing else -- and that is the whole test
# for being on this list. Three EXTRACTORS were found on 29 September 2026 to DESTROY data
# when run unattended: extract_trust_balance_detail deleted a year of trust balances,
# build_finance would have published receipts as closing balances, build_extraction_gaps
# deleted four registered gaps. Nothing that reads a PDF or rewrites a source CSV belongs
# here; a person runs those and reads the diff.
SITE_PAYLOADS = [
    # 1. CATALOGUE THE DOCUMENTS THIS RUN FETCHED, before anything counts them. On 30
    #    September 2026 the run fetched three agendas and three sets of minutes and left
    #    them uncatalogued, so the source index, the views, the search index over the
    #    minutes and every count derived from them were stale at the gate and the site
    #    did not deploy. The database was one layer of the same fault; this is the other.
    'build_source_index.py', 'build_views.py',
    # 2. The database, and the API published from it.
    'build_db.py', 'build_api.py',
    # 3. The payloads the site serves off the database.
    'build_athletics_charts.py', 'build_insurance_charts.py', 'build_monty_tech.py',
    'build_ch70_formula.py', 'build_minimum_aid.py', 'build_peer_spending.py',
    'build_special_education.py', 'build_sped_regulation.py', 'build_spending_vs_required.py',
    'build_stopped_funding.py', 'build_cut_register.py', 'build_grant_unwinding.py',
    'build_attrition.py', 'build_course_offerings.py', 'build_staffing_charts.py',
    'build_board_posting.py', 'build_youth_sports.py', 'build_lunenburg_by_the_numbers.py',
    'build_what_families_pay.py', 'build_no_captions_report.py',
    # 4. The indexes and the written pages that count what is now held.
    'build_minutes_fts.py',
    # One page per person: reads the org charts, the minutes' votes and the index just built.
    'build_people.py',
    'build_reading_time.py', 'build_short_versions.py',
    'build_schema_page.py', 'build_reference_pages.py', 'build_decisions_doc.py',
    'build_ingest_plan.py', 'build_reports_index.py', 'build_sitemap.py',
    # /ask and the footer on every page: the newest reports and every count, after the index.
    'build_agent_manifest.py',
    # 5. LAST, because they count everything above them.
    'build_readme.py', 'build_app_metrics.py',
]

# A FAILING CHECK THAT IS NOT STALENESS, and why. Any other generator THIS RUN executed
# blocks the deploy when it no longer reproduces (see scoped_gate).
# Each entry has to say what it is instead, so this cannot quietly become the place a
# real failure goes to be ignored.
NOT_BLOCKING = {
    'build_if_students_leave.py': 'a FINDING about the archive, not a stale file: FY2011 '
                                  'School Choice does not state its own arithmetic',
    'sync_d1.py': 'an external service; the run pushes it at step 9, and a table deferred '
                  'past the row ceiling makes --check error until the next run',
    'build_search_index.py': 'rebuilt below; it re-checks its own inputs and a document '
                             'fetched mid-run always looks newer than the index',
    # THE REST OF THIS SET ARE CONTENT CHECKS, not reproducibility checks. They read the
    # archive and report what they find there; a finding is worth a note and is not a reason
    # to withhold a site that matches its own data. Each still appears in the run's notes.
    'write_recording_minutes.py': 'checks 558 of OUR minutes files parse, link and match '
        'their transcript. A problem in one is a finding about that file, not a site that '
        'disagrees with its data -- and --relink fixes the common one, the town publishing '
        'its own minutes for a meeting we had only a recording of',
    'write_budget_state.py': 'reports how many meetings still have no budget state written; '
        'being behind is the backlog, not staleness',
    'fetch_board_pages.py': 'compares the town\u2019s live board pages against the bytes our '
        'extract was read from. A change there is the TOWN editing a page, which is a thing '
        'to look at rather than a thing to rebuild',
    'check_github_mirror.py': 'it asks whether files are COMMITTED, which is a question '
                              'about the repository rather than whether the site matches '
                              'its data; the refresh does not run it',
}

# A GENERATOR A PERSON RUNS, AND WHY IT MAY NOT RUN HERE. The run must NOT fix these
# itself: every one was found on 29 September 2026 to DESTROY or MISSTATE data when run
# unattended. Since 9 October 2026 a stale one is REPORTED with this reason and never holds
# the deploy -- the refresh never executes them, so the scoped gate cannot be about them.
BY_HAND = {
    'extract_trust_balance_detail.py': 'ran unattended it DELETED a year of trust balances: '
        'its text-layer reader returns [] for `the heading is not here`, which the caller '
        'reads as `refused` rather than `use OCR`',
    'extract_special_revenue.py': 'reads every transcription of a year and once pulled '
        'appropriations, trust and debt rows into the special revenue dataset',
    'build_extraction_gaps.py': 'owns side=extraction in money-gaps.csv and rewrites it, '
        'which deleted four gaps a person had registered by hand',
    'build_finance.py': 'reads the special revenue balance by ORDINAL column, and the '
        'ordinal means receipts in one edition and the balance in another',
}
# THE FIRST-CLASS OBJECTS OF A STATUS REPORT. TJ, 29 September 2026: *"consider those the
# first class objects for status reports... things like votes are not first class objects"*.
#
# Seven arrive from outside and one we make. A status report counts THESE and nothing else:
# a vote, a segment, a byte and a row are all things that happen INSIDE a document, and
# counting them tells a reader how talkative a meeting was rather than what moved. Defined
# once, here, and read by the run row, the printed summary and the dashboard, so the three
# cannot drift into three different answers.
# THE REFRESH COUNTS WHAT IT WRITES, AND NOTHING ELSE. TJ, 9 October 2026: *"state-law has
# nothing to do with refresh, so it shouldnt ever fail on something unrelated to it"* and
# *"if the refresh will impact something, then sure its important it doesnt overwrite. but
# things it has NOTHING to do with?"*
#
# This used to map EVERY top-level folder of the archive and raise on one it did not know,
# so that no class of document went uncounted (TJ, 29 September). Two things went wrong
# with that, and both came from diffing the WHOLE archive:
#
#   * it STOPPED the run over folders the refresh never touches. sources/state-law/ arrived
#     on 8 October from a hand-started download, and the 9 October refresh died at 07:00:03
#     having fetched nothing at all -- to protect the accuracy of one line of its report;
#   * it CREDITED the refresh with documents it never fetched. The 8 October row reports 3
#     ledgers, 9 contracts and 5 peer-district documents, and the refresh has no fetcher
#     for any of the three: whatever landed in the run's window was counted as its own.
#
# So the map is now the folders the refresh's own fetchers write into (watch_documents.py,
# fetch_board_pages.py, fetch_staff_directory.py, fetch_school_staff_directory.py,
# fetch_school_job_postings.py, fetch_town_job_postings.py), plus `analyses`, which its build steps write. Any other
# folder is outside its scope: never an error, and never reported as FOUND -- a new
# document there is listed separately, as found in our local files (LOCAL, below). Whether the WHOLE archive is
# catalogued and backed up is a different question, asked by build_source_index.py and
# check_archive_backed_up.py, which do not stand between the town and the morning fetch.
# `meetings` and `data` are counted from the event logs above, not from here.
#
# The other classes in ARRIVES (ledgers, contracts, correspondence, peer district
# documents) only ever arrive by hand, so a refresh reports 0 for them by construction.
# Annual reports used to be in that list; since 27 October 2026 the town crawl files them.
# The columns stay, because refresh-runs.csv is read by its header.
REFRESH_WRITES = {
    'district-budget': 'budget documents', 'town-budget': 'budget documents',
    'state-dls': 'state documents', 'state-dese': 'state documents',
    'town-supplementary': 'other town documents',
    'town-annual-reports': 'annual reports',     # fetch_town_docs.py, since 27 October 2026
    # The Attorney General's Open Meeting Law determinations, fetched WEEKLY by this run
    # since 9 October 2026 (see source-cadence.csv). The statute and the guide in the same folder
    # arrived by hand, and arrive no more often than the legislature acts.
    'state-law': 'state documents',
    'analyses': 'analyses',                      # ours
}
# A SNAPSHOT IS ONE LOOK, NOT A PILE OF DOCUMENTS. TJ, 9 October 2026: the run reported 10
# budget documents and 29 other town documents, and they were this week's staff-directory
# copies -- the district's six sheets and the town directory's pages, each saved whole into
# a dated folder because the publishers overwrite in place. Real fetches, not new
# publications. So a dated folder under one of these is counted ONCE, as a snapshot.
import re as _re
SNAPSHOT = _re.compile(r'^(.+/(staff-directory|job-postings))/(\d{4}-\d{2}-\d{2})/')
SNAPSHOT_WHAT = {'town-supplementary': {'staff-directory': 'town staff directory'},
                 'district-budget': {'staff-directory': 'district staff directory',
                                     'job-postings': 'district job postings (SchoolSpring)'}}

# Counted from the event logs (agendas, minutes, videos, transcripts), not the manifest; and
# `data` is ours throughout.
ARCHIVE_EVENTS = {'meetings', 'data'}
ARRIVES = ('agendas', 'official minutes', 'videos', 'transcripts', 'announcements',
           'budget documents', 'state documents', 'other town documents',
           'annual reports', 'ledgers', 'contracts', 'correspondence',
           'peer district documents',
           'snapshots')
MAKES = ('generated minutes', 'analyses')
# FOUND ON EXTERNAL SITES vs FOUND IN OUR LOCAL FILES. TJ, 9 October 2026: *"counting them
# as 'found' is OK too, but we should be sure to distinguish 'found on external sites' or
# 'found in our local files'"*. ARRIVES is the first: what this run's watchers and fetchers
# brought in. LOCAL is the second: a published document that is new to the archive but sits
# in a folder the refresh does not fetch into -- placed by hand, or by another job such as
# the AG determinations download -- which the run catalogues and does not claim to have found.
LOCAL = ('local documents',)
FIRST_CLASS = ARRIVES + LOCAL + MAKES
RUN_COLS = (['ran_at', 'as_of'] + ['new_' + k.replace(' ', '_') for k in FIRST_CLASS] +
            ['deployed', 'seconds', 'timings', 'notes',
            # `incomplete` until the run reaches its own end. A row that stays incomplete
            # is a run that died, and that is a fact worth keeping rather than an absence
            # to be guessed at. Old rows have no value here and read as finished, which
            # they are.
            'state'])


TIMINGS = []          # (step, seconds, exit code) -- printed at the end and written to the run row
# EVERY SCRIPT THIS RUN EXECUTED, by file name, whatever its arguments or exit code. This is
# what scopes the deploy gate: only the --check of a generator THIS RUN ran may hold the
# site back. Recorded where the subprocess is started, so it cannot drift from what ran --
# a hand-kept list of `generators the refresh rebuilds` is exactly the shape of defect
# CLAUDE.md names first. (TIMINGS cannot serve: its names carry positional arguments.)
RAN = set()



# WHEN EACH SOURCE IS LOOKED AT AGAIN is one register, sources/data/source-cadence.csv, and
# one due-check, source_cadence.due(). TJ, 28 October 2026: no separate weekly or monthly
# script -- the daily run knows each source's cadence and fetches whatever has come due, or is
# past due, since its last successful look. That replaced three hand-written copies of the
# same test here (a stamp file for the OML letters, two `checked.csv` reads for the
# directories and DESE). It is catch-up scheduling: a missed morning is made up the next
# one rather than waiting a whole cycle, and a look is recorded only when the fetch exits 0,
# so a failure is retried tomorrow rather than skipped. notes/reference/SOURCE-CADENCE.md is
# the table; `python3 scripts/source_cadence.py` is its live state.
import source_cadence as SC  # noqa: E402


def looked(source_id, a, r, notes=None, what=None):
    """Record one look at a source from its exit code; on failure, say so in the run's notes."""
    SC.record(source_id, a.as_of, r.returncode == 0,
              '' if r.returncode == 0 else 'exit %d' % r.returncode)
    if r.returncode and notes is not None and what:
        notes.append('%s: exit %d -- retried tomorrow; %s' % (source_id, r.returncode, what))


def slow_sources(a, notes):
    """Run every `job` and `slice` row that is due, record each look, name what changed."""
    for r in SC.runnable():
        if not SC.due(r['id'], a.as_of):
            continue
        looked(r['id'], a, py(*SC.argv(r), check=False), notes,
               'run python3 scripts/%s' % r['command'])
    found = SC.changes(on=a.as_of)
    for kind, said in (('changed', 'CHANGED AT THE PUBLISHER, found today'),
                       ('ours', 'defects in our archive the source checks exposed today')):
        new = [c['what'] for c in found if c['kind'] == kind]
        if new:
            notes.append('%s: %d -- %s%s. Run python3 scripts/source_cadence.py'
                         % (said, len(new), '; '.join(new[:4]), ' ...' if len(new) > 4 else ''))


def oml_years(as_of):
    """This year, and in January last year too: a letter issued on 30 December is numbered
    in the old year and may not be posted until the new one."""
    d = dt.date.fromisoformat(as_of)
    return [d.year - 1, d.year] if d.month == 1 else [d.year]


def fetch_oml(a, notes):
    """-> whether it ran. Its failure is a NOTE, never fatal: the determinations are
    reference material and have nothing to do with whether this morning's meetings reach
    the site."""
    if not SC.due('oml-determinations', a.as_of):
        return False
    bad = [y for y in oml_years(a.as_of)
           if py('fetch_oml_determinations.py', '--all', '--year', str(y),
                 check=False).returncode != 0]
    SC.record('oml-determinations', a.as_of, not bad,
              'failed for %s' % ', '.join(map(str, bad)) if bad else '')
    if bad:
        notes.append('OML determinations: the weekly fetch failed for %s -- retried tomorrow; '
                     'run fetch_oml_determinations.py --all --year %s'
                     % (', '.join(map(str, bad)), bad[-1]))
    return True


def record_run(a, delta, deployed, state, notes=()):
    """One row per day in refresh-runs.csv, written TWICE: once before the steps that can
    die, and again when the run finishes.

    The first write is the tombstone. Until 19 September 2026 this happened only at the
    end, so three consecutive failures left no trace at all and looked like quiet days.
    """
    runs = [r for r in read_csv(RUNS) if r['as_of'] != a.as_of]     # one row per day
    runs.append({'ran_at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                 'as_of': a.as_of, 'deployed': 'yes' if deployed else 'no',
                 **{'new_' + k.replace(' ', '_'): delta[k] for k in FIRST_CLASS},
                 'seconds': int(sum(t[1] for t in TIMINGS)),
                 'timings': ' '.join('%s=%d' % (n.replace(' ', '_'), int(sec)) for n, sec, _ in TIMINGS),
                 'notes': '; '.join(notes), 'state': state})
    with open(RUNS, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=RUN_COLS)
        w.writeheader()
        for r in sorted(runs, key=lambda r: r['as_of']):
            w.writerow({c: r.get(c, '') for c in RUN_COLS})


def sh(args, check=True, quiet=False, **kw):
    import time
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    env.update(kw.pop('extra_env', None) or {})
    name = os.path.basename(args[1] if args[0].endswith('python3') or 'python' in args[0] else args[0])
    if len(args) > 2 and not args[2].startswith('-'):
        name += ' ' + ' '.join(a for a in args[2:] if not a.startswith('-'))[:40]
    print('\n$ ' + ' '.join(args), flush=True)
    t0 = time.monotonic()
    kw.setdefault('cwd', ROOT)
    r = subprocess.run(args, env=env, capture_output=quiet, text=True, **kw)
    secs = time.monotonic() - t0
    TIMINGS.append((name, secs, r.returncode))
    RAN.add(os.path.basename(args[1] if 'python' in os.path.basename(args[0]) else args[0]))
    print('  [%s: %.1fs, exit %d]' % (name, secs, r.returncode), flush=True)
    if check and r.returncode != 0:
        if quiet:
            print((r.stdout or '') + (r.stderr or ''))
        raise SystemExit('step failed: %s' % ' '.join(args))
    return r


def py(script, *args, **kw):
    return sh([sys.executable, os.path.join(SCRIPTS, script), *args], **kw)


SCHOOLSPRING_ALERT = os.path.join(ROOT, 'build', 'schoolspring-ALERT.txt')


# THE METERED STEPS SHARE ONE STOP. Every step below that calls `claude -p` spends the
# same allowance, so a usage or session limit that refuses one refuses all of them. Before
# this, each ran with check=False and nothing read its output: a refused step printed a
# failure and the next metered step was called anyway -- and extract_official_votes.py,
# which counted only SUCCESSES against its --limit, would walk the whole corpus being
# refused. On 6 October 2026 the same blind spot in the sweep spun 5,145 refused calls
# over three and a half hours. A limit now ends every metered step for the rest of the run,
# and the run says so in its notes. The word list is the sweep's, imported, so the two
# cannot disagree about what a limit is.
METERED = {'stopped': None}


def metered(script, *args, notes=None):
    from sweep_backlog import HARD_LIMIT_WORDS, kill_switch
    if not METERED['stopped'] and kill_switch():
        METERED['stopped'] = kill_switch()
        if notes is not None:
            notes.append('metered steps skipped: ' + METERED['stopped'])
    if METERED['stopped']:
        print('\n$ %s -- SKIPPED: %s' % (script, METERED['stopped']), flush=True)
        return None
    import time
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    cmd = [sys.executable, os.path.join(SCRIPTS, script), *args]
    print('\n$ ' + ' '.join(cmd), flush=True)
    t0 = time.monotonic()
    p = subprocess.Popen(cmd, env=env, cwd=ROOT, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    seen = []
    for line in p.stdout:              # streamed, so the log still shows progress live
        print(line, end='', flush=True)
        seen.append(line)
    rc = p.wait()
    secs = time.monotonic() - t0
    TIMINGS.append((script, secs, rc))
    RAN.add(script)
    print('  [%s: %.1fs, exit %d]' % (script, secs, rc), flush=True)
    low = ''.join(seen[-200:]).lower()
    hit = next((w for w in HARD_LIMIT_WORDS if w in low), None)
    if hit:
        METERED['stopped'] = '%s hit a limit (%r); no further model calls this run' % (script, hit)
        print('  ' + METERED['stopped'], flush=True)
        if notes is not None:
            notes.append(METERED['stopped'])
    return rc


def schoolspring_alert(rc, notes):
    """A LOUD notice when SchoolSpring stops answering us, and silence when it answers.

    The job-postings feed reads an UNDOCUMENTED API (see fetch_school_job_postings.py), so
    the day it is locked down is expected rather than hypothetical. TJ, 5 October 2026:
    *"make a big failure notice in refresh if that happens."* So: a full-width banner in
    the run's output, a desktop notification with a sound, and a STICKY file that names
    the day it started -- because a notification is gone when dismissed and the machine
    may be asleep. A success deletes the file: an alert that outlives its cause trains
    you to ignore it.

    Exit 3 (LOCKED) is loud from the first run. Exit 2 (TRANSIENT -- a timeout, a 5xx)
    is a note until it has lasted three days, then loud too: a "transient" failure that
    never clears is a lockout by another name.
    """
    if rc == 0:
        if os.path.exists(SCHOOLSPRING_ALERT):
            os.remove(SCHOOLSPRING_ALERT)
        return
    today = dt.date.today().isoformat()
    since = today
    if os.path.exists(SCHOOLSPRING_ALERT):
        for line in open(SCHOOLSPRING_ALERT, encoding='utf-8'):
            if line.startswith('since: '):
                since = line.split(': ', 1)[1].strip()
    days = (dt.date.fromisoformat(today) - dt.date.fromisoformat(since)).days
    kind = {3: 'LOCKED OR CHANGED', 2: 'UNREACHABLE'}.get(rc, 'FAILED (exit %d)' % rc)
    os.makedirs(os.path.dirname(SCHOOLSPRING_ALERT), exist_ok=True)
    with open(SCHOOLSPRING_ALERT, 'w', encoding='utf-8') as fh:
        fh.write('SchoolSpring job postings: %s\nsince: %s\nlast: %s\n'
                 'No postings were read, and none were marked removed. '
                 'Run: python3 scripts/fetch_school_job_postings.py --dry-run\n'
                 % (kind, since, today))
    loud = rc != 2 or days >= 3
    msg = 'SCHOOLSPRING %s since %s -- job postings are NOT being tracked' % (kind, since)
    notes.append(('!!! ' if loud else '') + msg)
    if not loud:
        return
    bar = '!' * 78
    print('\n%s\n!!!  %-70s !!!\n!!!  %-70s !!!\n!!!  %-70s !!!\n%s\n'
          % (bar, 'SCHOOLSPRING JOB POSTINGS: %s' % kind,
             'failing since %s (%d day(s)); nothing read or marked removed' % (since, days),
             'see build/schoolspring-ALERT.txt', bar))
    subprocess.run(['osascript', '-e', 'display notification "job postings are not being '
                    'tracked since %s" with title "SchoolSpring %s" sound name "Basso"'
                    % (since, kind)], capture_output=True)


def backfill_running():
    r = subprocess.run(['pgrep', '-f', '[r]un_transcript_backfill|[f]etch_youtube_transcripts'],
                       capture_output=True, text=True)
    return r.returncode == 0


def read_csv(path):
    if not os.path.exists(path):
        return []
    return list(csv.DictReader(open(path, newline='', encoding='utf-8')))


def policy():
    return [r for r in read_csv(POLICY) if r.get('board_slug') and r.get('since')]


def covered(board_slug, date, rows):
    """The policy row that covers this recording, or None. `*` covers any board."""
    hits = [r for r in rows if r['board_slug'] in (board_slug, '*') and date >= r['since']]
    return min(hits, key=lambda r: int(r.get('priority') or 9)) if hits else None


def minutes_targets(rows):
    """Recordings inside the policy with a transcript on disk and no minutes yet -- EVERY
    recording, a re-upload included: both are valid, and merge_recording_minutes.py
    reconciles their minutes."""
    out = []
    for t in read_csv(TRANSCRIPT_INDEX):
        row = covered(t['board_slug'], t['meeting_date'], rows)
        if not row:
            continue
        if not os.path.exists(os.path.join(ROOT, t['path'])):
            continue
        target = os.path.join(RECORDED, t['board_slug'], '%s-%s.json' % (t['meeting_date'], t['video_id']))
        if not os.path.exists(target):
            # A transcript the writer refuses as `too short` is not work: imported, not restated.
            import write_recording_minutes as W
            if W.too_short(os.path.join(ROOT, t['path'])):
                continue
            out.append(dict(t, priority=int(row.get('priority') or 9)))
    # THE LAST TWO YEARS FIRST, ACROSS EVERY BOARD; then priority; newest first inside
    # each. TJ, 17 September 2026: "work them in priority order, newest first. Last 2
    # years is most important across everything than deeper for more." Three a day at
    # the calibrated 0.09% of the weekly allowance per meeting.
    out.sort(key=lambda t: (0 if t['meeting_date'] >= recent_since() else 1, t['priority'], -int(t['meeting_date'].replace('-', ''))))
    return out


RECENT_YEARS = 2

# NEW ONLY. THE REFRESH DOES NO BACKFILL. TJ, 6 October 2026: *"Let's cancel backfill from
# the refresh. I'll ask deliberately when to do the backfill."* Every metered step below
# reads only what ARRIVED in the last NEW_DAYS -- by the date the document was first seen
# or the transcript fetched, never by the meeting date, because a year-old meeting's
# minutes can be published today (TJ, 28 September 2026) and that is new. A week, so a
# missed morning or two is caught up rather than lost. Anything older is backlog, and
# backlog runs only when TJ asks for it.
NEW_DAYS = 7


def new_since(as_of):
    return (dt.date.fromisoformat(as_of) - dt.timedelta(days=NEW_DAYS)).isoformat()


def new_official_minutes(as_of):
    """(board_slug, meeting_date) for every set of the town's minutes first seen recently."""
    since = new_since(as_of)
    return sorted({(e['board_slug'], e['meeting_date']) for e in read_csv(MEETING_EVENTS)
                   if e['kind'] == 'minutes' and e['first_seen'] >= since},
                  key=lambda x: x[1], reverse=True)


def recent_since():
    return (dt.date.today() - dt.timedelta(days=365 * RECENT_YEARS)).isoformat()


MEETINGS_INDEX = os.path.join(ROOT, 'sources', 'meetings', 'index.csv')


def adopt_new_meeting_documents(as_of):
    """Rows the watcher first saw today, appended to sources/meetings/index.csv with an
    empty path, for `fetch_agendas.py --backfill` to fetch. Never removes a row."""
    import re
    events = [e for e in read_csv(MEETING_EVENTS) if e['first_seen'] == as_of]
    if not events:
        return 0
    rows = read_csv(MEETINGS_INDEX)
    held = {(r['file_id'], r['kind']) for r in rows}
    board_id = {r['board']: r['board_id'] for r in rows if r.get('board_id')}
    added = 0
    for e in events:
        if (e['file_id'], e['kind']) in held:
            continue
        rows.append({'board': e['board'], 'board_id': board_id.get(e['board'], ''),
                     'date': e['meeting_date'], 'kind': e['kind'], 'file_id': e['file_id'],
                     'path': '', 'url': e['url'], 'title': e.get('title', '')})
        held.add((e['file_id'], e['kind']))
        added += 1
    if added:
        # THROUGH THE ONE GUARDED WRITER. This function used to write the index itself, from
        # a column list typed before `title` existed, and on 14 October 2026 it erased all
        # 11,326 of the town's meeting titles. fetch_agendas.write_index keeps every column
        # the file has and refuses to empty a single cell.
        import fetch_agendas
        fetch_agendas.write_index(rows, MEETINGS_INDEX)
        print('adopted %d new meeting document(s) into the catalogue' % added)
    return added


# WHERE EACH DOCUMENT WAS FOUND. TJ, 9 October 2026: *"we should show the docs we found
# and from where we found them. if the finance committee put a DUMP of files somewhere and
# we found them, it should show that"*. Each mirrored folder's index.csv carries the
# publisher's title and the address; the district's also carries the LISTING PAGE it was
# found on and the meeting date. The town's and the state's do not record the page, so
# for those the address is the answer.
WHERE_PAGE = {'sc-meetings': 'School Committee meeting documents', 'budget': 'budget page'}
WHERE_FOLDER = {'district-budget': 'district site', 'town-budget': 'town site, budget and finance pages',
                'town-supplementary': 'town site, other pages', 'state-dls': 'state, Division of Local Services',
                'state-dese': 'state, DESE', 'town-annual-reports': 'town site, Annual Town Reports',
                'state-law': 'state, Attorney General (Open Meeting Law determinations)'}
DOC_INFO = {}


def where_found():
    """{archive key: {title, where, url, meeting}} for every row of the refresh's own indexes."""
    out = {}
    for top in REFRESH_WRITES:
        for r in read_csv(os.path.join(ROOT, 'sources', top, 'index.csv')):
            local = r.get('local') or ''
            key = local[len('sources/'):] if local.startswith('sources/') else local
            if not key:
                continue
            where = WHERE_FOLDER.get(top, top)
            if r.get('page'):
                where += ' \u00b7 ' + WHERE_PAGE.get(r['page'], r['page'])
            out[key] = {'title': r.get('label') or r.get('title') or '', 'where': where,
                        'url': r.get('upstream') or r.get('url') or '',
                        'meeting': r.get('meeting_date') or ''}
    return out


def inventory():
    """WHICH DOCUMENTS we hold, not how many.

    This used to return five counts, so a run could say `new agendas 3` and nothing in
    the log, the run row or the dashboard could say WHICH three. TJ, 29 September 2026,
    after a third attempt to get a legible answer out of a finished run: *"i want counts
    of full documents"*, and before that *"we're still not getting a clear update from
    daily refresh"*. A count is not an update. The identity of the document is.

    Each value is a dict of {key: label}, so the run diffs them and gets the new
    documents themselves.
    """
    inv = {}
    ev = read_csv(MEETING_EVENTS)
    inv['agendas'] = {e['file_id'] or (e['board_slug'] + e['meeting_date']):
                      '%s  %s' % (e['board'], e['meeting_date'])
                      for e in ev if e['kind'] == 'agenda'}
    inv['official minutes'] = {e['file_id'] or (e['board_slug'] + e['meeting_date']):
                               '%s  %s' % (e['board'], e['meeting_date'])
                               for e in ev if e['kind'] == 'minutes'}
    inv['videos'] = {e['video_id']: '%s  %s' % (e.get('uploaded') or '', e.get('title') or '')
                     for e in read_csv(YOUTUBE_EVENTS)}
    tr = read_csv(TRANSCRIPT_INDEX)
    inv['transcripts'] = {(t.get('video_id') or t.get('id') or str(i)):
                          '%s  %s' % (t.get('meeting_date') or t.get('uploaded') or '',
                                      (t.get('board_slug') or '').replace('-', ' ').title()
                                      or t.get('board') or t.get('title') or '')
                          for i, t in enumerate(tr)}
    ours = {}
    for f in glob.glob(os.path.join(RECORDED, '*', '*.json')):
        board = os.path.basename(os.path.dirname(f))
        ours[f] = '%s  %s' % (board.replace('-', ' '), os.path.basename(f)[:10])
    inv['generated minutes'] = ours

    inv['announcements'] = {(e.get('link') or e.get('title') or str(i)):
                            '%s  %s' % (e.get('source') or '', (e.get('title') or '')[:60])
                            for i, e in enumerate(read_csv(FEED_EVENTS))}

    # THE REST COME OFF THE ARCHIVE MANIFEST, which is the index of every document this
    # project holds. Keyed on SHA256, so a publisher who overwrites a file in place --
    # which the state does, and the district's web pages do -- shows up as a new document
    # rather than as nothing at all.
    for group in ARRIVES + LOCAL + MAKES:
        inv.setdefault(group, {})
    inv['renderings'] = {}
    found_at = where_found()
    for r in read_csv(MANIFEST):
        key = r.get('key') or ''
        if '/' not in key:
            continue
        top = key.split('/')[0]
        ident = r.get('sha256') or key
        group = REFRESH_WRITES.get(top)
        if group in MAKES:                       # our analyses: the document is the .md
            if key.endswith('.md'):
                inv[group][ident] = key.split('/')[-1][:70]
            continue
        # A DOCUMENT, NOT ITS RENDERINGS. The 8 October run reported 279 budget documents:
        # 6 were the district's, the rest extracted text and working files of ours. A
        # published document is what archive_storage.frozen() says it is; the rest are
        # counted once, as renderings, and never listed as documents.
        if not archive_storage.frozen(key):
            if top not in ARCHIVE_EVENTS:
                inv['renderings'][ident] = key
            continue
        if top in ARCHIVE_EVENTS:                # counted from the watchers' event logs above
            continue
        snap = SNAPSHOT.match(key)
        if snap and top in REFRESH_WRITES:
            what = SNAPSHOT_WHAT.get(top, {}).get(snap.group(2), snap.group(2).replace('-', ' '))
            folder = snap.group(0).rstrip('/')
            files = inv['snapshots'].get(folder, (0,))[0] + 1 if isinstance(inv['snapshots'].get(folder), tuple) else 1
            inv['snapshots'][folder] = (files, what, snap.group(3))
            continue
        if group:
            w = found_at.get(key, {})
            inv[group][ident] = ('%s  [%s%s]' % (w.get('title') or key.split('/')[-1], w.get('where') or top,
                                                 (', meeting ' + w['meeting']) if w.get('meeting') else ''))[:160]
            DOC_INFO[ident] = dict(kind=group, file=key, **{k: w.get(k, '') for k in ('title', 'where', 'url', 'meeting')})
        else:                                    # new to us, and not fetched by the refresh
            inv['local documents'][ident] = key[:110]
            DOC_INFO[ident] = dict(kind='local documents', file=key, dir=os.path.dirname(key))
    for folder, (n, what, day) in list(inv['snapshots'].items()):
        inv['snapshots'][folder] = '%s, %s  [%d file%s]' % (what, day, n, '' if n == 1 else 's')
    return inv


def whats_new(as_of, days=14):
    """The last two weeks of every event log, as one announcement payload."""
    since = (dt.date.fromisoformat(as_of) - dt.timedelta(days=days)).isoformat()
    me = [e for e in read_csv(MEETING_EVENTS) if e['first_seen'] >= since]
    ye = [e for e in read_csv(YOUTUBE_EVENTS) if e['first_seen'] >= since]
    ours = []
    for f in glob.glob(os.path.join(RECORDED, '*', '*.json')):
        m = json.load(open(f, encoding='utf-8'))
        when = (m.get('written') or {}).get('at', '')[:10]
        if when >= since:
            ours.append({'written': when, 'board': m['board'], 'board_slug': m['board_slug'],
                         'date': m['meeting_date'],
                         'url': '/meeting-minutes/%s/%s-%s' % (m['board_slug'], m['meeting_date'], m['video_id']),
                         'votes': sum(1 for v in m['minutes']['votes'] if not v.get('procedural'))})
    ours.sort(key=lambda x: (x['written'], x['date']), reverse=True)
    tr = [t for t in read_csv(TRANSCRIPT_INDEX) if (t.get('fetched_at') or '')[:10] >= since]
    fe = [e for e in read_csv(FEED_EVENTS) if e['first_seen'] >= since]
    de = [e for e in read_csv(DOC_EVENTS) if e['first_seen'] >= since]
    srcs = read_csv(FEED_SOURCES)
    return {
        'category': 'announcement',
        'not_a_measurement': 'What our watchers first saw, by the day they saw it. first_seen is our '
                             'crawl date, not the day the town posted anything.',
        'as_of': as_of,
        'window_days': days,
        'agendas': sorted([e for e in me if e['kind'] == 'agenda'], key=lambda e: (e['first_seen'], e['meeting_date']), reverse=True),
        'minutes': sorted([e for e in me if e['kind'] == 'minutes'], key=lambda e: (e['first_seen'], e['meeting_date']), reverse=True),
        'videos': sorted(ye, key=lambda e: (e['first_seen'], e['uploaded']), reverse=True),
        'transcripts': sorted([{'board_slug': t['board_slug'], 'date': t['meeting_date'], 'video_id': t['video_id'],
                                'fetched': (t.get('fetched_at') or '')[:10]} for t in tr],
                              key=lambda t: (t['fetched'], t['date']), reverse=True),
        'our_minutes': ours,
        'feeds': sorted(fe, key=lambda e: (e['published'], e['first_seen']), reverse=True),
        'documents': sorted([{**e, 'url': '/docs/' + e['local'][len('sources/'):] if e.get('local', '').startswith('sources/') else e.get('upstream', '')} for e in de],
                            key=lambda e: e['first_seen'], reverse=True),
        'feed_sources': {'watched': sum(1 for s in srcs if s.get('url')),
                         'without_a_feed': [s['source'] for s in srcs if not s.get('url')]},
        'counts': {'agendas': sum(1 for e in me if e['kind'] == 'agenda'),
                   'minutes': sum(1 for e in me if e['kind'] == 'minutes'),
                   'videos': len(ye), 'transcripts': len(tr), 'our_minutes': len(ours), 'feeds': len(fe), 'documents': len(de)},
    }


def write_to_post(as_of):
    """The Facebook texts, ready to paste, in build/ (gitignored) -- NOT on the site, which
    carries nothing addressed to us. One file, newest first, upcoming then retro."""
    p = json.load(open(os.path.join(ROOT, 'fy28', 'public', 'data', 'notices.json'), encoding='utf-8'))
    out = os.path.join(ROOT, 'build', 'notices-to-post.md')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    # NEW means written by this run: the preview or the minutes carry today's date. A
    # notice from an earlier day is still in the file -- the window is two weeks -- but
    # the heading says so, so the morning question "what do I post today" is the first
    # lines, not a diff.
    new_up = [u for u in p['upcoming'] if u.get('written') == as_of]
    new_re = [r for r in p['retro'] if r.get('written') == as_of]
    L = ['# Notices ready to post — as of %s' % as_of, '',
         '**New today: %d upcoming, %d what-happened.** Copy a block into Facebook. Nothing posts itself.'
         % (len(new_up), len(new_re)), '']
    for u in p['upcoming']:
        tag = 'NEW TODAY — ' if u.get('written') == as_of else ''
        L += ['## %sUPCOMING — %s, %s (%d day%s away)' % (tag, u['board'], u['date'], u['days_away'], '' if u['days_away'] == 1 else 's'), '', '```', u['facebook'], '```', '']
    for r in p['retro']:
        tag = 'NEW TODAY — ' if r.get('written') == as_of else ''
        L += ['## %sWHAT HAPPENED — %s, %s' % (tag, r['board'], r['date']), '', '```', r['facebook'], '```', '']
    open(out, 'w', encoding='utf-8').write('\n'.join(L))
    print('\nREADY TO POST (%s): %d upcoming (%d new today), %d what-happened (%d new today)'
          % (os.path.relpath(out, ROOT), len(p['upcoming']), len(new_up), len(p['retro']), len(new_re)))
    for u in new_up:
        print('  NEW  upcoming  %s %s — %s' % (u['board'], u['date'], u['one_line'][:90]))
    for r in new_re:
        # NOT a vote count: votes are not a first-class object -- see FIRST_CLASS.
        print('  NEW  happened  %s %s' % (r['board'], r['date']))


def back_up_documents(notes, why):
    """Put every document this tree holds into the bucket, NOW, and say so if it fails.

    TJ, 25 September 2026: *"i want to make sure any file we downoad is ALWAYS saved before
    we can even think of deleting it or cleaning a repo..."*

    THIS USED TO BE STEP 10 OF 10 AND ITS FAILURE WAS IGNORED. The comment beside it already
    knew the failure mode -- it names a Stormwater agenda that went that way on 17 September
    2026 -- and it was still the last thing the run did, with `check=False`, so a run that
    died anywhere earlier left the morning's documents on one disk and reported a clean day.
    Six agendas were in that state on 25 September.

    So it is called the moment documents land, not at the end. A run that dies after this
    has already saved what it fetched. (The refresh no longer destroys anything at the top of
    a run -- see refresh_git.py -- but a disk can still fail, and one copy is one copy.)

    AND A FAILED BACKUP IS NOW A NOTE, which reaches `refresh-runs.csv` and the
    notification. It does not abort the run: the documents are still on disk, nothing in the
    refresh deletes them, and the next run backs them up again, so the safe thing is to
    carry on ingesting and tell somebody. A backup that fails silently is the
    only version of this that loses a document.
    """
    rc = py('sync_archive.py', '--manifest', check=False).returncode
    rc += py('sync_archive.py', '--push', '--frozen', check=False).returncode
    if rc:
        notes.append('ARCHIVE BACKUP FAILED (%s) -- documents may be held in one place; '
                     'run check_archive_backed_up.py' % why)
    return rc == 0


# ------------------------------------------------------------- COMMITTING WHAT IT WROTE
# THE REFRESH RUNS IN THE WORKING TREE A PERSON IS USING, on whatever branch is checked out
# (TJ, 8 October 2026: *"refresh should work in whatever branch we're currently on"*). So it
# commits ONLY what it wrote, puts back anything of somebody else's it overwrote, and
# reaches main by replay rather than by a side branch. The mechanics, and why each rule
# exists, are in refresh_git.py; this is where the run calls them.
#
# CALLED TWICE: once before the deploy gate, so the gate and the deploy judge the commit
# that is actually on main, and once at the very end for the run row, which cannot know
# whether it deployed until after. A run that DIES is committed too (see main), because
# what it fetched is real and the old shell wrapper committed a failed run as well -- left
# uncommitted, tomorrow's run would find it dirty and treat it as somebody else's work.
def commit_run(a, notes, ctx, why):
    import refresh_git as G
    base = ctx.get('base')
    if base is None:
        return
    try:
        ours, blocked, appended = G.settle(ROOT, base)
        for p in appended:
            note = ('%s held uncommitted rows, so the rows this run appended stay '
                    'uncommitted with them (nothing set aside)' % p)
            if note not in notes:
                notes.append(note)
        new_blocked = [p for p in blocked if p not in ctx['blocked']]
        ctx['blocked'].extend(new_blocked)
        if new_blocked:
            # NOT YET REFRESHABLE, NOT FAILED. TJ, 8 October 2026: *"just mark that page as
            # a block and move on."* Every one is listed in the log; the note names a few.
            print('\n  NOT YET REFRESHABLE -- the refresh overwrote these, and they held '
                  'uncommitted changes it did not make; their owner’s version is back in '
                  'place, the refresh’s is kept in %s/conflicts/'
                  % os.path.relpath(base.store, ROOT))
            for p in new_blocked:
                print('    not yet refreshable: %s has uncommitted changes the refresh did '
                      'not make' % p)
            notes.append('not yet refreshable: %d file(s) have uncommitted changes the '
                         'refresh did not make, so its version was set aside: %s%s'
                         % (len(new_blocked), ', '.join(new_blocked[:6]),
                            ' ...' if len(new_blocked) > 6 else ''))
        reason = G.operation_in_progress(ROOT)
        if not G.branch(ROOT) or reason:
            if ours and not ctx.get('said_uncommitted'):
                ctx['said_uncommitted'] = True
                notes.append('NOT COMMITTED: %s, so the refresh left its %d file(s) in the '
                             'working tree' % ('a %s is in progress' % reason if reason
                                               else 'HEAD is detached', len(ours)))
            ctx['push'] = 'uncommitted'
            return
        last = read_csv(RUNS)
        found = ', '.join('%s=%s' % (k[4:], v) for k, v in (last[-1] if last else {}).items()
                          if k.startswith('new_') and v and v != '0') or 'nothing new'
        msg = ('Daily refresh, %s%s\n\n%s\n\nAutomated by scripts/refresh.py: only the %d '
               'file(s) this run wrote.' % (a.as_of, '' if why == 'data' else ' (%s)' % why,
                                           found, len(ours)))
        sha = G.commit(ROOT, ours, msg)
        if sha:
            print('  committed %d file(s) the refresh wrote, as %s' % (len(ours), sha[:8]))
        status, detail = G.publish(ROOT)
        ctx['push'] = status
        print('  %s: %s' % (status, detail))
        if status == 'not-main':
            note = 'not deployed: on branch %s' % (G.branch(ROOT) or 'detached')
            if note not in notes:
                notes.append(note)
        elif status not in ('pushed', 'nothing'):
            notes.append('NOT PUSHED (%s): %s' % (status, detail))
    except G.GitError as e:
        ctx['push'] = 'failed'
        notes.append('COMMIT FAILED: %s' % e)
        print('  COMMIT FAILED: %s' % e)


# ------------------------------------------------------------- THE SCOPED DEPLOY GATE
def scoped_gate(notes):
    """-> True when every generator THIS RUN executed still reproduces its output.

    IT USED TO BE ALL OF THEM. Any failing check in check_generated held the site back, so
    on 8 October 2026 fourteen unrelated stale outputs -- state aid, the money flow, the
    README -- kept that morning's new meetings off the site. A stale page this run never
    touched is no less stale for being withheld with everything else, and withholding the
    meetings fixes nothing about it.

    SO ONLY THE RUN'S OWN GENERATORS BLOCK (RAN, recorded where each was started); every
    other failure is REPORTED, with its reason, and never blocks. The whole check still
    runs, because the report is how somebody learns a page elsewhere has gone stale.
    """
    chk = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'check_generated.py')],
                         cwd=ROOT, capture_output=True, text=True)
    # The whole output is read, never its tail: fifteen of twenty-three failures went
    # unread on 29 September 2026 because a person read the report through `tail -25`.
    failing = []
    for line in (chk.stdout or '').splitlines():
        if not line.startswith('  FAIL'):
            continue
        parts = line.split(None, 2)
        failing.append((parts[1] if len(parts) > 1 else '?',
                        (parts[2] if len(parts) > 2 else '').strip()))
    blocking = [(n, w) for n, w in failing if n in RAN and n not in NOT_BLOCKING]
    reported = [(n, w) for n, w in failing if (n, w) not in blocking]
    if reported:
        notes.append('stale elsewhere, reported and NOT blocking: %d output(s): %s'
                     % (len(reported), ', '.join(sorted({n for n, _ in reported}))))
        print('  STALE ELSEWHERE -- reported, never blocking:')
        for name, why in sorted(reported):
            tag = ('[a person runs this: %s]' % BY_HAND[name][:70] if name in BY_HAND else
                   '[not blocking: %s]' % NOT_BLOCKING[name][:70] if name in NOT_BLOCKING else
                   '[this run did not execute it]')
            print('      %-34s %s  %s' % (name, why[:80], tag))
    if blocking:
        notes.append('DID NOT DEPLOY: %d output(s) THIS RUN rebuilt still do not reproduce '
                     'from their inputs -- a defect in the refresh, or an input holding '
                     'uncommitted changes: %s'
                     % (len(blocking), ', '.join(sorted(n for n, _ in blocking))))
        print('  NOT deploying -- executed by this run and still stale:')
        for name, why in sorted(blocking):
            print('      %-34s %s' % (name, why[:104]))
        return False
    print('  every generator this run executed (%d scripts) reproduces its output; safe to '
          'deploy' % len(RAN))
    return True


# ONE SITE BUILD AT A TIME. `npm run build:site` writes a shared dist/ and binds a fixed
# Chrome port (CLAUDE.md, "Several agents in one working tree"), and check-then-build
# races. So: an flock -- released by the kernel if this process dies, so it cannot go
# stale -- and, for a build somebody started by hand without the lock, a wait on the
# process itself. The patterns are BRACKETED so pgrep cannot match its own argv:
# unbracketed, this exact kind of wait reported a builder that was itself, forever.
BUILD_LOCK = os.path.join(ROOT, 'build', 'site-build.lock')
BUILD_WAIT_S = 30 * 60


def acquire_build_lock(notes):
    import fcntl
    import time
    os.makedirs(os.path.dirname(BUILD_LOCK), exist_ok=True)
    fh = open(BUILD_LOCK, 'a+')
    t0 = time.monotonic()
    while True:
        busy = subprocess.run(['pgrep', '-f', '[v]ite build|[s]cripts/prerender.mjs'],
                              capture_output=True).returncode == 0
        if not busy:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return fh
            except BlockingIOError:
                pass
        if time.monotonic() - t0 > BUILD_WAIT_S:
            fh.close()
            notes.append('DID NOT DEPLOY: another site build was running for %d minutes'
                         % (BUILD_WAIT_S // 60))
            return None
        time.sleep(15)


def deploy_allowed(notes, ctx):
    """Every condition a deploy needs, each refusal a NOTE rather than a printed line -- a
    note reaches refresh-runs.csv, the dashboard and the notification, and the old refusal
    was one line in a 1,600-line log while the run exited 0.

    1. THE BRANCH IS main. Anywhere else the run ingests, commits locally and reports
       `not deployed: on branch X` (15 September 2026: a refresh built a feature branch and
       Cloudflare put the deploy on a preview alias while the log said "deployed").
    2. THE COMMIT REACHED origin/main, AND HEAD IS EXACTLY origin/main. A NAME IS NOT THE
       FACT: from 23 September 2026 the refresh pushed to main and then silently refused to
       deploy for four days because it tested the branch NAME of a detached HEAD. What
       matters is whether this commit is the one main points at.
    3. NO SITE FILE HOLDS SOMEBODY ELSE'S UNCOMMITTED WORK. The build reads fy28/ from the
       working tree, and this tree is a person's: a dirty file there would be shipped to
       production without ever being committed. Refused and named, never cleaned.
    4. EVERY GENERATOR THIS RUN EXECUTED REPRODUCES -- see scoped_gate.
    """
    import refresh_git as G
    b = G.branch(ROOT)
    if b != 'main':
        note = 'not deployed: on branch %s' % (b or 'detached')
        if note not in notes:
            notes.append(note)
        return False
    if ctx.get('push') not in ('pushed', 'nothing'):
        notes.append('DID NOT DEPLOY: the refresh commit did not reach origin/main (%s)'
                     % ctx.get('push'))
        return False
    head = G.head(ROOT)
    origin_main = G.git(ROOT, 'rev-parse', 'refs/remotes/origin/main', check=False).stdout.strip()
    if not head or head != origin_main:
        notes.append('DID NOT DEPLOY: this tree is at %s and origin/main is at %s, so the '
                     'build would not be main’s own commit' % (head[:8] or '?',
                                                                origin_main[:8] or '?'))
        return False
    site_dirty = [p for p in G.dirty_paths(ROOT) if p.startswith('fy28/')]
    if site_dirty:
        notes.append('DID NOT DEPLOY: %d file(s) under fy28/ hold uncommitted changes the '
                     'refresh did not make, and the build would ship them: %s%s'
                     % (len(site_dirty), ', '.join(site_dirty[:5]),
                        ' ...' if len(site_dirty) > 5 else ''))
        return False
    return scoped_gate(notes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--deploy', action='store_true',
                    help='commit, push, and build and deploy the site (implies --commit)')
    ap.add_argument('--commit', action='store_true',
                    help='commit ONLY the files this run wrote, and push them when on main')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-minutes', action='store_true')
    ap.add_argument('--no-push', action='store_true', help='skip the D1 pushes (search index and database)')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--as-of', default=dt.date.today().isoformat())
    a = ap.parse_args()

    if a.check:
        bad = 0
        for s, args in (('watch_meetings.py', ['--check']), ('watch_youtube.py', ['--check']), ('watch_feeds.py', ['--check']), ('watch_documents.py', ['--check']), ('watch_grants.py', ['--check']),
                        ('write_recording_minutes.py', ['--check']), ('write_agenda_preview.py', ['--check']),
                        ('build_notices.py', ['--check']), ('build_meeting_feed.py', ['--check']),
                        ('build_boards.py', ['--check']), ('build_budget_feed.py', ['--check'])):
            bad += py(s, *args, check=False).returncode != 0
        return 1 if bad else 0

    # THE BASELINE FIRST, before the run writes a byte: what is dirty now is somebody
    # else's, and a copy of it goes into build/ so nothing the run overwrites is lost.
    a.commit = (a.commit or a.deploy) and not a.dry_run
    ctx = {'base': None, 'blocked': [], 'push': None}
    if a.commit:
        import refresh_git as G
        ctx['base'] = G.Baseline.take(ROOT)
        print('baseline: branch %s at %s; %d path(s) already hold uncommitted work and will '
              'not be committed by this run' % (ctx['base'].branch or '(detached)',
                                                ctx['base'].head[:8], len(ctx['base'].dirty)))
    notes = []
    finished = False
    try:
        rc = run(a, notes, ctx)
        finished = True
        return rc
    finally:
        if not finished and ctx['base'] is not None and not ctx.get('done'):
            # A RUN THAT DIES STILL COMMITS WHAT IT FETCHED -- see commit_run. No deploy.
            print('\nthe run stopped early; committing what it had written')
            commit_run(a, notes, ctx, 'stopped early')
            for n in notes:
                print('  note: ' + n)


def run(a, notes, ctx):
    before = inventory()

    # 0. THE TREE IS MADE WHOLE BEFORE ANYTHING COUNTS IT.
    #
    # `build_minutes_searchable.py` refuses to publish a corpus count from a tree that is
    # missing documents the index names, because that count is published in ten payloads and
    # a partial tree understates it -- the same figure had three defensible values on 25
    # September 2026. That refusal is right and it is only half a design: the first refresh
    # run after it was added STOPPED, 57 documents short, because the interactive tree had
    # ingested the district's staff directories and this tree had never pulled them.
    #
    # A REFUSAL NEEDS A REPAIR PATH IN THE SAME RUN. The documents are all in the bucket --
    # that is what the gate guarantees before anything gets this far -- so completeness is
    # one command away and there is no reason to make a person type it. What must never be
    # self-healed is DESTRUCTION (see the pristine check); fetching what we already own is
    # the opposite of that.
    if not a.dry_run:
        py('sync_archive.py', '--pull', check=False)

    # 1-3. The town's documents.
    py('watch_meetings.py', '--as-of', a.as_of, *(['--dry-run'] if a.dry_run else []))
    if not a.dry_run:
        # THE WATCHER'S LISTING IS THE FETCHER'S LIST. The fetcher used to re-list all 51
        # boards a minute after the watcher had -- the same requests twice. Now the
        # documents the watcher saw today are adopted into the catalogue with no path,
        # and `--backfill` fetches exactly those rows and fills the path in.
        n = adopt_new_meeting_documents(a.as_of)
        if n:
            py('fetch_agendas.py', '--backfill')
            # THE MOMENT THEY LAND. Not at the end of the run -- see back_up_documents.
            if not a.no_push:
                back_up_documents(notes, 'after fetching agendas and minutes')
        py('extract_minutes.py')
        py('build_minutes_searchable.py')
        if not a.no_minutes:
            metered('write_agenda_preview.py', '--upcoming', '--as-of', a.as_of, notes=notes)

    # 3d. New DOCUMENTS on the district's budget page and the town's finance pages --
    # the listing pages the archive was built from, re-walked; a shrunken index is
    # refused. TJ: "look for new documents posted from the school committee (budget
    # related), as well as on the town pages from the areas we've found."
    py('watch_documents.py', '--as-of', a.as_of, *(['--dry-run'] if a.dry_run else []), check=False)
    if not a.dry_run and not a.no_push:
        back_up_documents(notes, 'after the document watcher')
    # 4a. A NEW BUDGET DOCUMENT IS READ THE MORNING IT APPEARS. TJ, 16 September 2026:
    # "anytime a new doc is 'found', we need to identify if it impacts the budget feed and
    # process it right then and there." One read per document, page-cited, into the same
    # budget-state shape the feed and the season boards already draw from.
    if not a.dry_run:
        metered('write_document_budget_state.py', '--new', '--as-of', a.as_of, '--limit', '3', notes=notes)

    # 3e. THE TWO STAFF DIRECTORIES, WEEKLY. Who works for the town and who works for the
    # district, off the pages they publish themselves -- and the only sources here that
    # cease to exist if nobody re-fetches them: both publishers overwrite in place, so
    # there is no FY2026 copy of either anywhere and the archive's snapshots are the only
    # history that will ever exist.
    #
    # THIS IS THE GAP THAT PROMPTED IT. `fetch_staff_directory.py` was named in no
    # scheduled script -- not here, not the daily wrapper, not the weekly sweep -- so the
    # town's people were ONE photograph taken on 22 September 2026 with nothing arranged to
    # take the next. The failure mode is silent: the file goes on answering correctly about
    # a day that recedes.
    #
    # WEEKLY, NOT DAILY, AND A SNAPSHOT ONLY WHEN SOMETHING MOVED. A directory does not
    # change daily, an unchanged snapshot is frozen in the bucket for ten years, and
    # `--if-changed` writes nothing when the pages match the last one while still logging
    # that it looked. So `checked.csv` answers how current the snapshot is, which a missing
    # snapshot cannot.
    #
    # GATED ON THE LOG RATHER THAN ON THE WEEKDAY: a run missed on its day would otherwise
    # wait a full week, and this project has had a scheduled job hand back its own window
    # once already.
    if not a.dry_run:
        for script, source in (('fetch_staff_directory.py', 'staff-directory-town'),
                               ('fetch_school_staff_directory.py', 'staff-directory-district')):
            if SC.due(source, a.as_of):
                looked(source, a, py(script, '--if-changed', check=False))
        py('extract_staff_directory.py', check=False)
        py('extract_school_staff_directory.py', check=False)

    # 3f. THE DISTRICT'S JOB POSTINGS, DAILY. TJ, 5 October 2026: "put this on the refresh
    # list to see if new job postings are added or some removed... and keep the history as
    # a table." Off SchoolSpring's public JSON API for the district's own employer account
    # (Indeed only syndicates it, refuses scripts, and forbids scraping).
    #
    # DAILY, NOT WEEKLY LIKE THE DIRECTORIES, because the thing being measured is turnover:
    # the fifteen open on 5 October 2026 print close dates one to three months after their
    # post dates, but a posting can come down the day it is filled, so a weekly look would
    # widen every `removed_seen` to a seven-day window and could miss a short posting
    # altogether. A daily look costs four seconds and sixteen small GETs, and
    # it is still CHANGE-ONLY -- the API is byte-stable, so an unchanged day writes nothing
    # to the frozen bucket and only appends to `checked.csv`, and a posting's detail is
    # stored once, not once per day it stays open. The fetcher secures what it writes
    # through `ingest`, so no separate backup step is needed here.
    if not a.dry_run:
        r = py('fetch_school_job_postings.py', '--if-changed', check=False)
        schoolspring_alert(r.returncode, notes)
        py('extract_school_job_postings.py', check=False)
        # THE TOWN'S OWN JOB BOARD, daily for the same reason. A page whose parse no longer
        # ties to its own printed count exits 3 and records nothing, so a redesign can never
        # mark every open town job as taken down; it says so here instead.
        r = py('fetch_town_job_postings.py', '--if-changed', check=False)
        if r.returncode:
            notes.append('!!! TOWN JOB BOARD exit %d -- town postings NOT read today, none marked '
                         'taken down. Run: python3 scripts/fetch_town_job_postings.py --dry-run'
                         % r.returncode)
        # Both employers into one page, /jobs, and the links on every board and department
        # page -- after both sides have been read.
        py('build_job_postings.py', check=False)

    # 3c. The town's and the community's feeds -- news, alerts, registrations. Linked and
    # attributed, never republished (QUEUE 13, 14).
    py('watch_feeds.py', '--as-of', a.as_of, *(['--dry-run'] if a.dry_run else []), check=False)

    # 3g. The Attorney General's Open Meeting Law determinations, weekly -- gated by
    # source-cadence.csv; `--all --year` skips every letter already held, so a quiet week
    # costs the walk past the last held number and no more.
    if not a.dry_run:
        if fetch_oml(a, notes) and not a.no_push:
            back_up_documents(notes, 'after the OML determinations')

    # 3h. DESE'S CURRENT GRANT OPPORTUNITIES, WEEKLY, for /grants-open-to-lunenburg. DESE
    # publishes only the current list and overwrites it in place, so these copies are the only
    # history of it. Gated by source-cadence.csv like the directories (a missed day
    # does not wait a week); a page lands only when its bytes changed, through `ingest`, so no
    # separate backup step. Network only, about 75 requests at one a second -- no model call.
    if not a.dry_run:
        if SC.due('dese-grants', a.as_of):
            looked('dese-grants', a, py('fetch_dese_grants.py', '--if-changed', check=False),
                   notes, 'run python3 scripts/fetch_dese_grants.py --dry-run')
        py('extract_dese_grants.py', check=False)
        py('build_grants_open.py', check=False)
        # 3h'. DESE'S COMPETITIVE AWARD LISTS -- who WON each grant -- on the same weekly beat.
        # DESE keeps only the current and previous year's lists up: FY2025's link already
        # answers with its error page, so a list we have not saved before it goes is gone
        # (23 October 2026). land_version never lands the same bytes twice.
        if SC.due('dese-awards', a.as_of):
            looked('dese-awards', a, py('fetch_dese_awards.py', check=False),
                   notes, 'run python3 scripts/fetch_dese_awards.py --dry-run')
            py('extract_dese_awards.py', check=False)
        # 3h''. WHAT IS NEW FROM DESE, for the home page's notification line: a grant newly
        # open to districts, an award list naming Lunenburg or a comparison district. Read off
        # the snapshots just landed, never a fetch, so it runs every day; build_notices.py
        # (step 8) publishes the live ones. No model call.
        r = py('watch_grants.py', check=False)
        if r.returncode:
            notes.append('DESE grant watch exited %d -- run python3 scripts/watch_grants.py --check'
                         % r.returncode)

    # 3i. DESE'S ENTITLEMENT ALLOCATIONS, WEEKLY: every district, every fund code, FY2017 to
    # the coming year. DESE revises these pages in place (each carries `Last Updated`), so the
    # dated snapshots are the only record of an allocation before it was revised. Gated on
    # source-cadence.csv like 3h; a page lands only when its bytes differ from the
    # newest snapshot, through `ingest`, and a year whose by-district pages do not reconcile
    # with its fund-code pages lands nothing. Network only, ~265 requests at one a second.
    # extract runs after it so dese-fund-codes.csv picks up a list 3h just refreshed.
    if not a.dry_run:
        if SC.due('dese-entitlements', a.as_of):
            looked('dese-entitlements', a,
                   py('fetch_dese_entitlements.py', '--if-changed', check=False),
                   notes, 'run python3 scripts/fetch_dese_entitlements.py --dry-run')
        py('extract_dese_entitlements.py', check=False)

    # 3j. THE SLOW SOURCES: everything in source-cadence.csv the refresh runs generically --
    # the monthly and quarterly checks. A `job` runs when its cadence has elapsed since its
    # last successful look; a `slice` runs every morning and itself picks the few documents
    # whose own last check is oldest, so 4,000 documents on a 30-to-90-day cycle cost a
    # hundred-odd requests a morning, not all of them on one. CHECKS ONLY: plain HTTPS and a
    # hash, no model call, nothing landed in the archive -- what moved is reported below and
    # by `python3 scripts/source_cadence.py`, for a person to take in.
    if not a.dry_run:
        slow_sources(a, notes)

    # 4-6. The town's recordings.
    py('watch_youtube.py', '--as-of', a.as_of, *(['--dry-run'] if a.dry_run else []))
    if not a.dry_run:
        py('build_youtube_classification.py')
        if backfill_running():
            notes.append('transcript fetch skipped: the backfill is running')
            print('\nthe transcript backfill is running; not competing with it for captions')
        else:
            since = (dt.date.fromisoformat(a.as_of) - dt.timedelta(days=TRANSCRIPT_WINDOW_DAYS)).isoformat()
            py('fetch_youtube_transcripts.py', '--since', since, '--limit', '12', '--sleep', '45', check=False)
        # A MEETING POSTED TWICE. Which videos are the same recording, from their captions --
        # BEFORE minutes are written, so both recordings are written and then merged. A
        # newly re-posted meeting is news: the town usually re-posts to fix something.
        rv = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'reconcile_meeting_videos.py')],
                            capture_output=True, text=True)
        print(rv.stdout, end='')
        for line in rv.stdout.splitlines():
            if line.startswith('NEWLY RE-POSTED'):
                notes.append(line.lower().replace('newly re-posted: ', 're-posted: '))

    wrote_minutes = set()     # (board, date) whose minutes this run wrote -- reconciled below
    # 7. Our minutes, inside the policy, capped -- for recordings whose transcript is NEW.
    if not a.dry_run and not a.no_minutes:
        rows = policy()
        since_new = new_since(a.as_of)
        targets = [t for t in minutes_targets(rows) if (t.get('fetched_at') or '')[:10] >= since_new]
        if len(targets) > MAX_MINUTES_PER_RUN:
            notes.append('%d recordings await minutes; wrote %d' % (len(targets), MAX_MINUTES_PER_RUN))
        for t in targets[:MAX_MINUTES_PER_RUN]:
            metered('write_recording_minutes.py', t['board_slug'], t['meeting_date'], notes=notes)
            wrote_minutes.add((t['board_slug'], t['meeting_date']))

    # 7b. SCANNED MINUTES, OCR'D -- local, free, about half a minute each; newest first.
    if not a.dry_run and not a.no_minutes:
        py('ocr_scanned_minutes.py', '--limit', str(MAX_OCR_PER_RUN), check=False)

    # 7c. THE TOWN'S MINUTES, READ FOR THEIR VOTES -- every board, newest first, capped.
    # build_boards.py joins these with our recording minutes at build time, so the two
    # records can arrive in either order (TJ, 17 September 2026). Runs after the OCR so
    # a scan read today is read for its votes today.
    if not a.dry_run and not a.no_minutes:
        # NEW minutes only, each by board and date, through process_meeting.py -- the same
        # runner and the same read order as the backlog: our minutes first when the captions
        # exist, then the town's minutes read structured and reconciled in one call. A
        # meeting already done answers `nothing to do` and costs nothing. Capped as a backstop.
        for board, date in new_official_minutes(a.as_of)[:MAX_OFFICIAL_VOTES_PER_RUN]:
            metered('process_meeting.py', board, date, notes=notes)

    # 7a. The budget state of the three budget boards' recordings -- the deficit, the cuts,
    # the warnings as put on the record -- newest first, capped like the minutes. A file
    # behind the extraction's schema counts as work, so a schema change backfills itself
    # at MAX_MINUTES_PER_RUN a day rather than in one expensive batch.
    if not a.dry_run and not a.no_minutes:
        since = (dt.date.fromisoformat(a.as_of) - dt.timedelta(days=400)).isoformat()
        # ONLY THE CATCH-UP. A new meeting's budget state now comes out of the same read
        # as its minutes (step 6), so this reads only meetings that already have minutes
        # from before the merge, or files behind the schema -- never a meeting the minutes
        # step will read anyway. TJ: "it will save both TOKENS and time."
        # REMOVED 6 October 2026: this step was ONLY the catch-up -- backfill, which the refresh
        # no longer does. A new meeting's budget state comes out of the minutes step. Run
        # `write_budget_state.py --since ... --with-minutes-only` by hand when TJ asks.
        pass

    # 7a'. The live season's board, re-read from the record: warnings straight onto the
    # page, figures and cuts PROPOSED into budget-seasons/fy28.proposed.csv for a person to
    # confirm by copying a row into fy28.csv. Nothing with a figure appears unconfirmed.
    if not a.dry_run:
        py('build_budget_season.py', 'fy28', check=False)
        try:
            import csv as _csv
            pp = os.path.join(ROOT, 'sources', 'data', 'budget-seasons', 'fy28.proposed.csv')
            n = sum(1 for _ in _csv.DictReader(open(pp, encoding='utf-8'))) if os.path.exists(pp) else 0
            if n:
                notes.append('%d row(s) proposed for the FY28 board in sources/data/budget-seasons/fy28.proposed.csv -- confirm by copying into fy28.csv' % n)
        except Exception as e:
            notes.append('could not count proposed season rows: %s' % e)

    # 7b. Against the town's minutes, FOR RECENT MEETINGS ONLY.
    #
    # THIS COMMENT USED TO SAY `does work only when new` AND THE CALL BELOW HAD NO WINDOW,
    # so it reconciled every unreconciled pair in the archive, every day. On 28 September
    # 2026 it ran for two hours inside the daily refresh, made 89 model calls and spent
    # $22.73 API-equivalent with 157 pairs still to go -- another four and a half hours and
    # about a tenth of the week's allowance, in one step.
    #
    # TJ, that day: *"REFRESH is intended to fetch anything NEW that was added. Not churn
    # through a backlog... it should be fast, and small. its a DIFF based tool."*
    #
    # A WINDOW ON THE MEETING DATE WAS THE FIRST FIX AND IT WAS WRONG. TJ, the same day:
    # *"there may be a meeting from a year ago, that only recently had its transcript
    # filled in, or its minutes added. So the NEW is relevant to new files/info created...
    # not based on the meeting dates... otherwise we'll miss things."* A pair becomes
    # eligible when the TOWN publishes, which can be a year after the meeting, and nothing
    # in sources/meetings/index.csv records when a document was fetched -- so there is no
    # honest date to window on. A cap alone excludes nothing: the queue runs newest first,
    # and a pair that becomes eligible today is reached within a day or two whatever its
    # date. The historical backlog still belongs to sweep_backlog.py, which needs a
    # reconcile stream it does not yet have.
    if not a.dry_run and not a.no_minutes:
        # A pair is NEW when either side is: the town's minutes first seen recently, or our
        # minutes written this run. reconcile_minutes.py skips a pair that is already
        # reconciled or has no official minutes, without calling the model.
        pairs = sorted(set(new_official_minutes(a.as_of)) | wrote_minutes, key=lambda x: x[1], reverse=True)
        for board, date in pairs[:MAX_RECONCILE_PER_RUN]:
            metered('reconcile_minutes.py', board, date, notes=notes)

    # 8. Rebuild everything derived from the above.
    if not a.dry_run:
        # THE ONE MEETING RECORD, before anything that lists meetings reads it.
        py('extract_document_timestamps.py', '--quiet')
        py('build_meeting_register.py')
        py('build_meeting_pages.py')     # a page for every meeting in it
        py('build_meeting_feed.py')
        py('build_recording_minutes.py')
        # THE SUGGESTED-REPORTS REGISTER, merged from every minutes file just written. Free:
        # the suggestions rode on the minutes call; this only groups them.
        py('build_suggested_reports.py')
        py('build_notices.py')
        # OPEN SEATS BEFORE THE BOARDS, because build_boards.py reads the vacancy counts
        # to put `One open board seat available` on a board's own page. TJ, 22 September
        # 2026: *"make sure the 'open seats' is dynamic"* -- dynamic means regenerated by
        # this run, so a seat filled between annual reports stops being advertised the day
        # the listing changes rather than whenever somebody remembers.
        py('extract_personnel.py')
        py('build_open_seats.py')
        py('build_board_composition.py')
        py('build_town_personnel.py')
        py('build_boards.py', '--as-of', a.as_of)
        # EVERY BOARD'S TRANSFERS, by fiscal year -- from the same official-votes files step
        # 7c just wrote, so a transfer voted at a meeting reaches /boards/<slug>/transfers the
        # day its minutes are read (TJ, 10 Oct 2026).
        py('build_board_transfers.py', check=False)
        # THE THREADS, FROM THE SAME MINUTES. Not in this run until 10 October 2026, so the
        # threads page sat at 19 September for three weeks while the turf field came up at
        # four more meetings -- a generator nothing ran, and nothing checked.
        # ...after the agendas are matched to them, so a thread names its next meeting.
        py('build_agenda_threads.py', check=False)
        # THE TOWN MEETINGS: every meeting found from the record, every warrant article and
        # where it stands, written as generated threads that build_threads.py merges -- so a
        # new warrant, recommendation or vote reaches its board the day it is read (TJ, 21
        # October 2026). Deterministic, no model, ~25s.
        py('build_town_meetings.py', check=False)
        # A SENTENCE OR TWO PER ARTICLE, for meetings coming up or just held -- only where the
        # article's record moved, so most days this is no call at all. Metered like the
        # callouts; each summary is checked before it can show (write_article_summaries.py).
        if not a.no_minutes and not a.dry_run:
            if metered('write_article_summaries.py', notes=notes) is not None:
                py('build_town_meetings.py', check=False)
        py('build_threads.py', check=False)
        # THE CALLOUTS, for the threads whose record just changed -- what someone says next
        # (TJ, 19 October 2026). A model picks, threads batched to a call, only where the input moved, and a second call judges every new pick;
        # build_threads.py checks every pick against its source and drops what fails, so it
        # runs again after. Metered: the kill switch and the limit words stop it like any other.
        if not a.no_minutes and not a.dry_run:
            if metered('write_thread_callouts.py', notes=notes) is not None:
                py('build_threads.py', check=False)
        py('build_budget_feed.py', '--as-of', a.as_of)
        py('build_feeds.py')
        # THE FY BREAKDOWN UNLOCKS A YEAR BY ITSELF (TJ, 27 October 2026: "as soon as we ingest the
        # same data from munis.. the FY should auto-unlock"): it reads its years off the journal and
        # shows each one whose inputs are held, so rebuilding it daily is the whole hook. ~12 s.
        py('build_fy_breakdown.py', check=False)
        py('verify_fy_breakdown.py', check=False)
        # AND THE DATABASE, AND EVERYTHING THE SITE SERVES OFF IT. See SITE_PAYLOADS:
        # this run has just changed the minutes, the transcripts and the meeting record,
        # and every payload built from them was being left at yesterday's figures and
        # deployed anyway.
        for gen in SITE_PAYLOADS:
            py(gen, check=False)
        # THE MENU'S CHANGE INDICATORS, last: it reads jobs, threads, minutes, the budget
        # feed, the meeting feed and the reports index, all written above.
        py('build_site_changes.py', check=False)
        # A new budget episode the feed thinks it sees -- a Special Town Meeting date, an
        # override, the Governor's budget, the season opening -- is PROPOSED here, with its
        # evidence, for TJ or the agent to confirm by adding a row to budget-episodes.csv.
        try:
            feed = json.load(open(os.path.join(ROOT, 'fy28', 'public', 'data', 'budget-feed.json')))
            for p in feed.get('proposed_episodes', []):
                notes.append('possible new budget episode: %s (%s) -- add to sources/data/budget-episodes.csv if real' % (p['signal'], p['evidence']))
            # A story forming that no thread names -- 'athletics' in 23 lines across 9 meetings --
            # is proposed the same way; a row in sources/data/budget-threads.csv makes it one.
            for p in feed.get('proposed_threads', [])[:5]:
                notes.append('a budget story may be forming: %s -- %d lines across %d meetings, %s to %s; add to sources/data/budget-threads.csv to give it a thread'
                             % (p['name'], p['rows'], p['meetings'], p['first'], p['last']))
        except Exception as e:
            notes.append('could not read proposed episodes: %s' % e)
        # The finished seasons, rebuilt too: their calendars and minutes counts move as the
        # archive fills in. Each closes on its election day (sources/data/budget-cycles.csv).
        for fy, closes in (('fy26', '2025-05-17'), ('fy27', '2026-05-16')):
            py('build_budget_feed.py', '--as-of', closes, '--out', 'fy28/public/data/budget-feed-%s.json' % fy)
        metered('tag_document_affinity.py', notes=notes)     # only documents not yet tagged; cents
        # THESE THREE READ fy28/dist, so they hold the site-build lock while they do: a build
        # started by hand empties dist/ and refills it page by page, and on 14 October 2026
        # one did exactly that under build_search_index.py, which died on a deleted page.
        # Hand builds take the same lock (scripts/with_build_lock.py, via npm run build:site).
        dist_lock = acquire_build_lock(notes)
        try:
            py('build_search_index.py', '--quiet')
            py('build_app_metrics.py')
            py('build_sitemap.py')
        finally:
            if dist_lock is not None:
                dist_lock.close()
        # WHAT READERS HAVE ASKED, pulled off the questions database so an unanswered
        # question cannot sit with no sign of it anywhere a person looks. Counts only --
        # no bodies, no email addresses. check=False because a courtesy must not fail the
        # night's ingestion.
        py('pull_questions.py', check=False)
        # AND WHAT THEY SEARCHED FOR (pull_searches.py): every search, its words, its hits.
        # Gitignored, never committed -- a search can be a person's name.
        py('pull_searches.py', check=False)
        py('build_agentic_backlog.py', check=False)     # where every machine-reading stream stands, notes/generated/AGENTIC-BACKLOG.md
        # AND HOW DEEP IT IS, by the MEETING's own date rather than by when we found it.
        # Runs after the streams above have done their work, so the figure on the
        # dashboard falls as the queue drains rather than describing this morning.
        py('build_backlog_depth.py', check=False)       # notes/generated/BACKLOG-DEPTH.md + /data/backlog-depth.json
        # 9. The search index and the analysis database to D1. Both incremental: only
        # tables whose digest differs are sent, and anything past the row ceiling is named
        # and waits for the next run. check=False -- a refused push is a note, not a
        # reason to lose the night's ingestion.
        if not a.no_push:
            py('sync_search_d1.py', '--limit', str(SEARCH_PUSH_LIMIT), check=False)
            py('sync_d1.py', '--limit', str(DB_PUSH_LIMIT), check=False)
        # 10. THE DOCUMENTS THEMSELVES TO THE BUCKET. The refresh fetches the town's new
        # PDFs into its own worktree, but git carries only the manifest and the text --
        # so a document fetched here and never pushed exists on one disk and nowhere
        # else (a Stormwater agenda went that way on 17 September 2026). New keys only.
        if not a.no_push:
            # The final sweep, for anything a later step fetched. Backups now also happen
            # as documents land, so this is a backstop rather than the only chance.
            back_up_documents(notes, 'the end-of-run sweep')

    # HOW MANY DAYS NOBODY LOOKED. A gap in the crawl silently becomes a gap in what this
    # project can say: a document `first seen` after a four-day hole could have been posted
    # on any of those days, and the figure reads like a posting time. TJ, 25 September 2026:
    # *"Can you be sure we processed the agenda and would know if it was posted wed or
    # Thurs?"* -- the answer was no, and nothing said so. It is a note rather than a failure
    # because a missed day cannot be recovered; the point is that it is visible while the
    # documents are still fresh enough to reason about.
    if not a.dry_run:
        gaps = py('check_watch_gaps.py', '--as-of', a.as_of, check=False)
        if gaps.returncode:
            notes.append('the meeting watcher has missed days recently -- run '
                         'check_watch_gaps.py; `first seen` is no better than the gap')

    after = inventory()
    # THE DOCUMENTS THEMSELVES, not the difference between two counts.
    arrived = {k: [after[k][i] for i in after[k] if i not in before[k]] for k in after}
    # OUR MINUTES: ONLY THE ONES THIS RUN ASKED FOR. The folder is shared with
    # process_meeting.py, which can be writing beside the refresh -- the 9 October dry run
    # wrote nothing and still listed four 2023 meetings as its own. `wrote_minutes` is the
    # set step 7 actually requested; a new file outside it belongs to somebody else.
    arrived['generated minutes'] = [
        after['generated minutes'][f] for f in after['generated minutes']
        if f not in before['generated minutes']
        and (os.path.basename(os.path.dirname(f)), os.path.basename(f)[:10]) in wrote_minutes]
    delta = {k: len(v) for k, v in arrived.items()}
    # THE LIST ITSELF, KEPT FOR THE DASHBOARD. TJ, 9 October 2026: *"i want to see which
    # meetings and docs it picked up to make sure its working everyday"*. The run printed
    # this into its log and nowhere else, so checking a morning meant reading a log. Written
    # here, before the check and the deploy that follow, so a run that dies there still leaves what
    # it found; a dry run writes it too, marked, because that is how a change gets checked.
    found_dir = os.path.join(ROOT, 'build', 'refresh-found')
    os.makedirs(found_dir, exist_ok=True)
    found = {'as_of': a.as_of, 'written_at': dt.datetime.now().isoformat(timespec='seconds'),
             'dry_run': bool(a.dry_run), 'tree': ROOT,
             'found': {k: sorted(arrived[k]) for k in ARRIVES},
             # the same documents with their title, where they were found and the address
             'found_docs': [DOC_INFO[i] for k in ARRIVES for i in after[k]
                            if i not in before[k] and i in DOC_INFO],
             'local': sorted(arrived['local documents']),
             'local_docs': [DOC_INFO[i] for i in after['local documents']
                            if i not in before['local documents'] and i in DOC_INFO],
             'renderings': len(arrived['renderings']),
             'wrote': {k: sorted(arrived[k]) for k in MAKES}}
    tmp = os.path.join(found_dir, '.%s.json.tmp' % a.as_of)
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(found, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, os.path.join(found_dir, '%s%s.json' % (a.as_of, '-dry-run' if a.dry_run else '')))

    # THE ROW GOES IN BEFORE THE RISKY PART, NOT AFTER IT.
    #
    # It used to be appended at the very end, so a run that died anywhere earlier left
    # NOTHING -- and no row reads as a quiet day, not as a failure. The refresh failed on
    # 16, 17 and 18 September 2026 (build_search_index.py, `database or disk is full`) and
    # refresh-runs.csv simply stopped at the 15th. Nobody knew for four days.
    #
    # A registry written only by success cannot record a failure, which is the one thing
    # it most needs to record. So the row is written here, marked `incomplete`, and
    # updated to the finished state at the end. A run that dies now leaves its own
    # tombstone with what it had found before it went. The notices and what's-new go with
    # it, BEFORE the commit, because the site serves both and the deploy below builds what
    # was committed.
    if not a.dry_run:
        record_run(a, delta, deployed=False, state='incomplete', notes=notes)
        write_to_post(a.as_of)
        payload = whats_new(a.as_of)
        with open(WHATS_NEW, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, indent=1, ensure_ascii=False)
            fh.write('\n')

    # COMMIT WHAT THIS RUN WROTE, AND ONLY THAT, BEFORE ANYTHING JUDGES A DEPLOY. The old
    # order deployed the uncommitted working tree and committed afterwards in the shell
    # wrapper, which was safe only because that tree was reset to main each morning. This
    # tree is a person's, so the site must be built from what is on main.
    if a.commit:
        commit_run(a, notes, ctx, 'data')

    # 10. The site, only when asked -- and see deploy_allowed for every condition.
    deployed = False
    if a.deploy and not a.dry_run and deploy_allowed(notes, ctx):
        lock = acquire_build_lock(notes)
        if lock is not None:
            try:
                sh(['npm', 'run', 'build:site'], cwd=os.path.join(ROOT, 'fy28'),
                   extra_env={'SITE_BUILD_LOCK_HELD': '1'})
                # `--branch main`, NAMED. Wrangler takes production-or-preview from the git
                # branch; on 9 October 2026 a hand deploy from a tree on another branch went
                # to `refresh.lunenburg-fy28.pages.dev` while production kept the old site.
                # deploy_allowed already refuses anything but main's own commit, so naming
                # the branch only says what is already true.
                sh(['npx', 'wrangler', 'pages', 'deploy', '--branch', 'main'],
                   cwd=os.path.join(ROOT, 'fy28'))
                deployed = True
            finally:
                lock.close()

    if not a.dry_run:
        record_run(a, delta, deployed, 'ok', notes)
        if a.commit:
            commit_run(a, notes, ctx, 'run row')
        ctx['done'] = True

    # THE DOCUMENTS FIRST. WHAT CAME IN, WHAT WE MADE, THEN THE CLOCK.
    #
    # This block used to be fifty lines of seconds followed by one line of counts, and
    # TJ asked three times in one morning for something legible out of it: "we're still
    # not getting a clear update from daily refresh", then "i want a list of all the
    # documents it found and their type, and then what it generated", then "i want
    # counts of full documents". A step that took 2069 seconds is not the news. Five
    # agendas and three minutes we wrote is the news, and the run knew both all along.
    total = sum(t[1] for t in TIMINGS)
    # THE EIGHT OBJECTS TJ ASKED FOR, 29 September 2026, and no others. Never a count of
    # VOTES: "telling me the number of votes it found is absurd" -- a vote count measures
    # how often somebody moved a motion, not what the town published or what we made.
    n_in = sum(delta[k] for k in ARRIVES)
    print('\n=== refresh %s — %d document(s) in, %d written, %d min %d s ==='
          % (a.as_of, n_in, delta['generated minutes'], total // 60, total % 60))

    print('\n  FOUND ON EXTERNAL SITES -- %d document(s)' % n_in)
    for key in ARRIVES:
        print('    %-22s %d' % (key, delta[key]))
        for line in sorted(arrived[key]):
            print('        %s' % line)
    if not n_in:
        print('    nothing new was published today')

    print('\n  FOUND IN OUR LOCAL FILES -- %d document(s) new to the archive that this run did '
          'not fetch (placed by hand, or by another job)' % delta['local documents'])
    by_dir = {}
    for line in arrived['local documents']:
        by_dir.setdefault(os.path.dirname(line), []).append(line)
    for d in sorted(by_dir, key=lambda d: -len(by_dir[d])):
        print('    %-60s %d' % (d, len(by_dir[d])))
        for line in sorted(by_dir[d])[:10]:
            print('        %s' % os.path.basename(line))
        if len(by_dir[d]) > 10:
            print('        ... and %d more' % (len(by_dir[d]) - 10))
    if delta['renderings']:
        print('    plus %d rendering(s) of ours catalogued -- extracted text, working files; '
              'not documents' % delta['renderings'])

    print('\n  WROTE -- %d document(s) of our own' % delta['generated minutes'])
    for line in sorted(arrived['generated minutes']):
        print('        generated minutes   %s' % line)
    if not delta['generated minutes']:
        print('        none')

    for n in notes:
        print('\n  note: ' + n)
    print('\n  deployed' if deployed else '\n  NOT deployed%s' % ('' if a.deploy else ' (pass --deploy)'))

    # The clock last, because it is about US and not about the town.
    print('\n  --- where the time went ---')
    print('  %-46s %8s' % ('step', 'seconds'))
    for name, secs, rc in sorted(TIMINGS, key=lambda t: -t[1]):
        print('  %-46s %8.1f%s' % (name[:46], secs, '' if rc == 0 else '  exit %d' % rc))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
