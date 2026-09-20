#!/usr/bin/env python3
"""The agentic backlog: every stream of machine reading this project runs, how far each
has got, and the order it works in.

    python3 scripts/build_agentic_backlog.py       # write notes/generated/AGENTIC-BACKLOG.md

TJ, 17 September 2026: "Sounds like we just have some Agentic processing. Put them into a
list and work them in priority order, newest first. Last 2 years is most important across
everything than deeper for more." Four streams, one rule: the last two years across every
board before anything older, newest first inside each. Counts are derived; the refresh
rewrites this daily.
"""
import csv
import datetime as dt
import glob
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
OUT = os.path.join(ROOT, 'notes', 'generated', 'AGENTIC-BACKLOG.md')
RECENT = (dt.date.today() - dt.timedelta(days=730)).isoformat()


def read(p):
    return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []


def split(dates_done, dates_todo):
    r = lambda ds: (sum(1 for d in ds if d >= RECENT), sum(1 for d in ds if d < RECENT))
    return r(dates_done), r(dates_todo)


def transcripts():
    # ONE ROW PER RECORDING. youtube-video-boards.csv is one row per (video, board), so a
    # joint body's meeting appears under each board that was in it -- a Tri-Board meeting is
    # four rows. Counting rows counts that recording four times in a backlog of recordings.
    rows = read(os.path.join(ROOT, 'sources', 'data', 'youtube-video-boards.csv'))
    rows = list({r['video_id']: r for r in rows}.values())
    have = {os.path.basename(p)[-16:-5] for p in glob.glob(os.path.join(ROOT, 'sources', 'data', 'youtube-transcripts', '*', '*.json'))}
    nocap = {r['video_id'] for r in read(os.path.join(ROOT, 'sources', 'data', 'youtube-no-captions.csv'))}
    done = [r['meeting_date'] for r in rows if r['video_id'] in have]
    todo = [r['meeting_date'] for r in rows if r['video_id'] not in have and r['video_id'] not in nocap and r['meeting_date']]
    return done, todo


def recording_minutes():
    import refresh
    have = [os.path.basename(p)[:10] for p in glob.glob(os.path.join(ROOT, 'sources', 'data', 'recording-minutes', '*', '*.json'))]
    todo = [t['meeting_date'] for t in refresh.minutes_targets(refresh.policy())]
    return have, todo


def official_votes():
    import extract_official_votes as E
    files = E.minutes_files()
    have = {os.path.relpath(p, E.OUT)[:-5] for p in glob.glob(os.path.join(E.OUT, '*', '*.json'))}
    done = [e['date'] for e in files if '%s/%s-%s' % (e['board_slug'], e['date'], e['docid']) in have]
    todo = []
    for e in files:
        if '%s/%s-%s' % (e['board_slug'], e['date'], e['docid']) in have:
            continue
        body = open(e['path'], encoding='utf-8', errors='replace').read()
        if len(re.sub(r'\s+', ' ', body)) >= E.MIN_CHARS:
            todo.append(e['date'])
    return done, todo


def ocr():
    import ocr_scanned_minutes as O
    done = [r['date'] for r in O.registry().values()]
    todo = [c['date'] for c in O.candidates()]
    return done, todo


def extraction():
    """The annual reports: rows READ against rows RECONCILED.

    TJ, 20 September 2026, after finding the stabilization history unusable only because
    he asked for it: "we need to surface these gaps so I dont find them with questions
    like this" -- and then, on this backlog: "we need to add that to the list next.
    Anytime you have nothing to do, just work on that."

    It is not one of the claude -p streams and it is the largest backlog in the project:
    13,405 rows off sixteen annual reports, of which about 3% are tied to a total the
    document itself prints. The counts come from the database so they move the day an
    extractor improves.
    """
    import sqlite3
    db = sqlite3.connect(os.path.join(ROOT, 'sources', 'data', 'lunenburg.db'))
    done, todo = [], []
    for (t,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' "
                           "AND name LIKE 'report_%'"):
        try:
            rows = dict(db.execute('SELECT status, COUNT(*) FROM %s GROUP BY status' % t)
                        .fetchall())
        except sqlite3.OperationalError:
            continue
        # Dated by the report they came from, so the two-year rule sorts them the same way
        # every other stream is sorted.
        try:
            fys = [r[0] for r in db.execute('SELECT DISTINCT fy FROM %s' % t)]
        except sqlite3.OperationalError:
            fys = []
        for fy in fys:
            if not fy:
                continue
            d = '%d-06-30' % int(fy)
            n = db.execute('SELECT COUNT(*) FROM %s WHERE fy=?' % t, (fy,)).fetchone()[0]
            ok = db.execute("SELECT COUNT(*) FROM %s WHERE fy=? AND status='checked'" % t,
                            (fy,)).fetchone()[0]
            done += [d] * ok
            todo += [d] * (n - ok)
    return done, todo


def main():
    streams = [
        ('Captions for recordings', 'fetch_youtube_transcripts.py — free, throttled by YouTube; run_transcript_backfill.sh sweeps the last two years across every board, then the rest; the refresh takes 12 a day', transcripts()),
        ('Our minutes of recordings', 'write_recording_minutes.py — claude -p, ~0.09% of the weekly allowance each; the refresh writes 3 a day, last two years first, then the three budget boards deeper', recording_minutes()),
        ('Votes from the town’s minutes', 'extract_official_votes.py — claude -p on the small model, ~0.03% each, every quote checked verbatim; the refresh reads 40 a day, newest first across every board', official_votes()),
        ('Reconciling the annual-report tables', 'the largest backlog here and not an '
         'agentic one: rows are READ, and a row is only usable once it ties to a total '
         'the document itself prints. Mostly a per-page column ruler putting ACCOUNT '
         'NUMBER where the first figure belongs, and ten of seventeen trust-fund years '
         'needing real PDF geometry. Survey: sources/data/extraction-plan.csv',
         extraction()),
        ('OCR of scanned minutes', 'ocr_scanned_minutes.py — macOS Vision, local and free, ~30 s each; the refresh reads 40 a day, newest first; a scan read here enters search and the votes stream', ocr()),
    ]
    b = io.StringIO()
    b.write('# The agentic backlog\n\n')
    b.write('Generated by `scripts/build_agentic_backlog.py`, %s. **The rule:** the last two years (since %s) across every board before anything older; newest first inside each stream. Costs are the calibrated share of the plan’s weekly allowance (CLAUDE.md, ~/.claude).\n\n' % (dt.date.today().isoformat(), RECENT))
    b.write('| stream | done, last 2 yrs | to do, last 2 yrs | done, older | to do, older | how |\n|---|---:|---:|---:|---:|---|\n')
    for name, how, (done, todo) in streams:
        (dr, do), (tr, to) = split(done, todo)
        b.write('| %s | %d | **%d** | %d | %d | %s |\n' % (name, dr, tr, do, to, how))
    # `recording-minutes-policy.csv` READS LIKE A SCOPE FILE AND IS NOT. Its `*` row
    # covers any board since 2000-01-01, so refresh.covered() matches every transcript:
    # the file sets PRIORITY -- Town Meeting, then the three budget boards, then the rest
    # -- and MAX_MINUTES_PER_RUN limits the night. Nothing is excluded, so this footer no
    # longer says anything is.
    b.write('\n**Not in any stream, by choice:** conclusions on the finance pages are a '
            'per-owner writing job rather than a batch. Minutes-writing is NOT in this '
            'category: `sources/data/recording-minutes-policy.csv` sets the order every '
            'board is written in, not which boards qualify.\n')
    # PROPOSED, AND NOT COUNTED ABOVE because the extractor does not exist yet -- a row
    # with no data behind it would read as a stream that is running and at zero.
    b.write('\n**Proposed, not built:** *Town Meeting vote displays.* Town Meeting runs '
            'electronic voting and puts the VERBATIM motion text and the counted tally on '
            'screen, and the whole meeting is on video -- so every appropriation motion is '
            'recoverable exactly, with a tally arithmetic can check, rather than paraphrased '
            'from captions. Article 3 of the 3 September 2026 Special Town Meeting is the '
            'worked case: the display reads `$30,308.00` and `224 / 29 / 0 / 253`, and our '
            'recording minutes record it as the single word `passed`. `sources/data/'
            'official-votes/` holds 30-odd boards and no `town-meeting/` at all, so the body '
            'that actually appropriates is the one captured least precisely. Same machinery '
            'as `ocr_scanned_minutes.py` (macOS Vision, local, free), pointed at sampled '
            'frames instead of scanned PDFs.\n')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(b.getvalue())
    print(b.getvalue())


if __name__ == '__main__':
    main()
