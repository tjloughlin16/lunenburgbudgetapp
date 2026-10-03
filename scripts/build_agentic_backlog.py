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


def transcript_disk_lag():
    """Captions the INDEX records that this checkout does not hold on disk.

    Not a backlog -- nobody has to fetch them again. It is how far this tree is behind
    the archive, and it is only ever non-zero in a tree that is not the one the refresh
    runs in. Printed so a thin checkout is visible instead of silently shrinking a count.
    """
    idx = {r['video_id'] for r in read(os.path.join(ROOT, 'sources', 'data', 'youtube-transcript-index.csv'))}
    disk = {os.path.basename(p)[-16:-5] for p in glob.glob(os.path.join(ROOT, 'sources', 'data', 'youtube-transcripts', '*', '*.json'))}
    return len(idx - disk)


def transcripts():
    # ONE ROW PER RECORDING. youtube-video-boards.csv is one row per (video, board), so a
    # joint body's meeting appears under each board that was in it -- a Tri-Board meeting is
    # four rows. Counting rows counts that recording four times in a backlog of recordings.
    rows = read(os.path.join(ROOT, 'sources', 'data', 'youtube-video-boards.csv'))
    rows = list({r['video_id']: r for r in rows}.values())
    # THE TRACKED INDEX, NOT THE FILES ON DISK. `youtube-transcripts/` is GITIGNORED, so
    # this used to publish a figure about whichever CHECKOUT ran the generator and read as
    # a figure about the archive -- the defect CLAUDE.md names for
    # `build_minutes_searchable.py`, which now refuses rather than guess.
    #
    # It bit on 3 October 2026. The daily refresh runs in its own worktree and fetched 8
    # captions overnight into ITS ignored directory; this tree holds 2,666 files and that
    # one holds 2,674, so merging its generated copy and regenerating here moved the row
    # from `702 held, 0 to do` to `694 held, 8 to do`. Nothing about the town changed and
    # no caption was lost -- the 8 are in the index, which is TRACKED and identical in
    # both trees. Tomorrow's refresh would have flipped it back, which is worse than
    # being wrong once: a figure that oscillates with whoever last ran the build.
    #
    # So the count comes off the index, the archive's own record of what captions exist,
    # and the files are its payload. `disk_lag()` reports the difference rather than
    # hiding it, because a checkout missing payload is worth seeing -- just not worth
    # publishing as a backlog somebody should clear.
    have = {r['video_id'] for r in read(os.path.join(ROOT, 'sources', 'data', 'youtube-transcript-index.csv'))}
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


def annual_report_years():
    """How many annual-report YEARS are closed -- this project's definition of done.

    A year is done when every financial page it holds is `proven` or `blocked`. That is
    what commit 595148b1 means by *FY2025 is read: 23 of 23 pages, every one tied to
    arithmetic the page states*, and what `annual_report_progress.py` reports.

    IT IS NOT THE QUESTION THE ROW COUNTS IN THIS FILE ANSWER, and conflating the two
    cost an hour on 1 October 2026. Row `status` in the `report_*` tables measures
    whether a GENERIC extract was exhausted; a page read by eye SUPERSEDES the generic
    extract WITHOUT EMPTYING IT, so those counts stay high on years that are finished.
    """
    import csv as _csv
    import collections as _c
    f = os.path.join(ROOT, 'sources', 'data', 'annual-report-pages.csv')
    by = _c.defaultdict(_c.Counter)
    with open(f, newline='', encoding='utf-8-sig') as fh:
        for r in _csv.DictReader(fh):
            fy = (r.get('fy') or '').strip()
            if not fy:
                continue
            by[fy][(r.get('state') or '').strip()] += 1
            by[fy]['pages'] += 1
    closed = sum(1 for c in by.values() if c['proven'] + c['blocked'] == c['pages'])
    return (closed, len(by), sum(c['pages'] for c in by.values()),
            sum(c['blocked'] for c in by.values()))


def annual_report_banner():
    """The page-level truth, at the TOP, because the row counts below read as a backlog."""
    closed, total, pages, blocked = annual_report_years()
    if closed < total:
        return ('**The annual reports: %d of %d years CLOSED** of %d financial pages. '
                'A year is closed when every page is `proven` or `blocked` -- run '
                '`python3 scripts/annual_report_progress.py`.\n\n' % (closed, total, pages))
    return ('## THE ANNUAL REPORTS ARE DONE -- %d of %d years, all %d financial pages\n\n'
            'Every financial page of every annual town report, FY2011-FY2025, is `proven` '
            'or `blocked`. Run `python3 scripts/annual_report_progress.py`; it prints '
            '*Every year is done. Nothing to pick.*\n\n'
            '**%d page(s) are BLOCKED, and `done` does NOT mean every figure is in a '
            'dataset.** A blocked page is one a person read and could not -- registered '
            'in `sources/data/page-blocked.csv` with its reason and the one document that '
            'would settle it. Two were printed short by the town; one is a 93 dpi scan.\n\n'
            '**THE ROW COUNTS BELOW ARE ROWS, NOT PAGES, AND THEY ARE NOT WORK '
            'OUTSTANDING.** `status` on a `report_*` row says whether a GENERIC extract '
            'was exhausted. A page read by eye supersedes that extract without emptying '
            'it, so the figure stays high on a year that is finished. Reading it as a '
            'backlog is the grain mistake that cost an hour on 1 October 2026.\n\n'
            % (closed, total, pages, blocked))

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


def _superseded():
    """The rows inside the extraction backlog that are not really work.

    Derived, so it cannot go stale the way a typed sentence would: the counts come from
    the same database the stream above is measured from.
    """
    import sqlite3
    db = sqlite3.connect(os.path.join(ROOT, 'sources', 'data', 'lunenburg.db'))

    def count(t, where=''):
        try:
            return db.execute('SELECT COUNT(*) FROM %s %s' % (t, where)).fetchone()[0]
        except sqlite3.OperationalError:
            return 0

    off = count('report_officials')
    off_junk = count('report_officials', "WHERE (label IS NULL OR label='') AND v1=page")
    wages = count('report_gross_wages')
    ours = 0
    p = os.path.join(ROOT, 'sources', 'data', 'gross-wages.csv')
    if os.path.exists(p):
        ours = sum(1 for _ in open(p, encoding='utf-8')) - 1
    posts = 0
    p = os.path.join(ROOT, 'sources', 'data', 'town-personnel.csv')
    if os.path.exists(p):
        posts = sum(1 for _ in open(p, encoding='utf-8')) - 1
    trust = count('report_trust_funds')
    trust_ok = count('report_trust_funds', "WHERE status='checked'")
    stab_rows = stab_years = 0
    p = os.path.join(ROOT, 'sources', 'data', 'stabilization-balances.csv')
    if os.path.exists(p):
        import csv as _csv
        rs = list(_csv.DictReader(open(p, encoding='utf-8')))
        stab_rows, stab_years = len(rs), len({r['fy'] for r in rs})
    return (
        '\n**Counted above and NOT really work.** Three of the generic table extracts inside '
        '`Reconciling the annual-report tables` should not be read as a backlog anybody '
        'will clear:\n\n'
        '- **`report_officials`, %d rows, none checked.** It is not the officials listing. '
        'Its FY2011 rows are `Nancy L Woodruff 79` and `Robert E. Tucker WWII 82` — a '
        'memorial page — and %d of its rows carry NO LABEL and a value equal to their own '
        'page number. The listing itself is read properly by `extract_personnel.py` into '
        '`town-personnel.csv`, %d rows, every one tied to a post and a year, with a '
        '`size_check` against the membership each heading states.\n'
        '- **`report_gross_wages`, %d rows, none checked.** The same pages are read by '
        '`extract_gross_wages.py` into `gross-wages.csv`, %d rows of name and amount. '
        'NEITHER is published and both are honest about why: the town stopped printing the '
        'department beside each name after FY2016, so the list cannot be split by '
        'department, and no wage page prints a total to foot a row against. '
        'THIS LINE ALSO CARRIED A SECOND REASON UNTIL 28 SEPTEMBER 2026 -- that the '
        'two-column layout loses a third to a half of the given names -- and it was '
        'false: it measured our OCR CACHE, which held the surname column and nothing '
        'else on two of FY2019\u2019s seven pages. A re-read took that year from 44 '
        'names to 516. Registered in `money-gaps.csv` rather than shown.\n'
        '- **`report_trust_funds`, %d rows, %d checked** — and the part of it anybody asks '
        'about is already read. The STABILIZATION funds are in '
        '`stabilization-balances.csv`: %d fund-years across %d years, every one proven '
        'against an identity the table states about itself, published at '
        '`/analysis/stabilization-funds`. What is genuinely unreconciled is the REST of '
        'the trust table — the cemetery, library and scholarship funds — so this row is a '
        'real backlog, but it is not the stabilization backlog it reads as.\n\n'
        'Left in the count deliberately rather than quietly subtracted — a number that '
        'moves because somebody changed what it counts is worse than one that is too big '
        'and says so.\n'
        % (off, off_junk, posts, wages, ours, trust, trust_ok, stab_rows, stab_years))


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
    b.write(annual_report_banner())
    b.write('Generated by `scripts/build_agentic_backlog.py`, %s. **The rule:** the last two years (since %s) across every board before anything older; newest first inside each stream. Costs are the calibrated share of the plan’s weekly allowance (CLAUDE.md, ~/.claude).\n\n' % (dt.date.today().isoformat(), RECENT))
    b.write('| stream | done, last 2 yrs | to do, last 2 yrs | done, older | to do, older | how |\n|---|---:|---:|---:|---:|---|\n')
    for name, how, (done, todo) in streams:
        (dr, do), (tr, to) = split(done, todo)
        b.write('| %s | %d | **%d** | %d | %d | %s |\n' % (name, dr, tr, do, to, how))
    lag = transcript_disk_lag()
    if lag:
        # SAID OUT LOUD, BESIDE THE TABLE, so a thin checkout is visible without the
        # count moving. This is not work: the captions exist and the index records them.
        b.write('\n*This checkout holds no local copy of %d caption file(s) the index '
                'records -- `sources/data/youtube-transcripts/` is gitignored and the daily '
                'refresh fetches into its own worktree. Nothing to fetch again; the counts '
                'above come from the tracked index, not from this disk.*\n' % lag)
    # `recording-minutes-policy.csv` READS LIKE A SCOPE FILE AND IS NOT. Its `*` row
    # covers any board since 2000-01-01, so refresh.covered() matches every transcript:
    # the file sets PRIORITY -- Town Meeting, then the three budget boards, then the rest
    # -- and MAX_MINUTES_PER_RUN limits the night. Nothing is excluded, so this footer no
    # longer says anything is.
    # NOT EVERY ROW IN THE BACKLOG IS WORK. TJ, 22 September 2026: *"can you also update
    # the backlog status? I 'think' we have things listed there that we already
    # processed, but lets just check it."* Checked, and the answer is not staleness --
    # rebuilding the database moved none of these numbers. Two of the generic table
    # extracts are counted as outstanding when one has been REPLACED and the other is
    # largely noise, and a backlog that counts either as work to do is lying about its
    # own size.
    b.write(_superseded())
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
    b.write('\n**Proposed, not built:** *The town\u2019s OFFICIAL minutes, read for more '
            'than votes.* TJ, 28 September 2026: *"votes is ONE PIECE of what the minutes '
            'have in them."*\n\n'
            'WHAT WE HAVE. The TEXT of every set of the town\u2019s minutes is extracted '
            'and in the search index -- 12,095 files -- so a resident can find an '
            'appointment or a transfer in them today. What we build from that text is one '
            'object: a VOTE, with a verbatim quote. `write_recording_minutes.py` already '
            'builds ten -- attendees, public_comment, headline, summary, tags, votes, '
            'budget_items, transfers, decisions, topics -- and reads MACHINE CAPTIONS. The '
            'schema, the prompt and the validator exist; nothing points them at the '
            'town\u2019s own minutes.\n\n'
            'WHY IT MATTERS MOST FOR THE OLD YEARS. Recordings barely exist before 2024, so '
            'the rich objects do not either: 0 in 2019, 0 in 2020, 1 in 2021, 2 in 2022, 2 '
            'in 2023 against 30, 33, 119, 239 and 325 sets of official minutes in those same '
            'years. For everything before 2024 we can answer vote questions and nothing '
            'else, from documents whose text we hold. `How many appointments did the Select '
            'Board make in FY2024` is not answerable today; the words are findable, the ROW '
            'does not exist.\n\n'
            'WHAT IT IS NOT. Not a new extractor -- an existing one pointed at a cleaner '
            'input. The town\u2019s minutes beat captions on transcription: no mishearings, '
            'no `$1,500` read as `$50`. But they are a SUMMARY written by a clerk, where a '
            'caption is verbatim, so a `decision` taken from them is the clerk\u2019s '
            'rendering and not the meeting -- a different evidential thing that has to be '
            'labelled as such, which is the same ours-and-theirs line `reconcile_minutes.py` '
            'already draws. It does not replace reconciliation; it makes it like-for-like '
            'instead of ten objects against one.\n\n'
            'COST AND PLACEMENT. ~$0.09 a document today for votes alone; the full schema is '
            'nearer the $0.37 our minutes cost, so 2,841 outstanding is roughly $1,000 -- '
            'two weeks\u2019 allowance. That is sweeper work in unused allowance, never the '
            'daily refresh. And it would REPLACE the votes-only pass rather than run beside '
            'it, so the comparison is against $0.09 a document and not additional to it.\n\n'
            'BEFORE ANY OF IT: the annual reports. TJ, the same day: *"my first goal today '
            'is to get through all the annual reports."*\n')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(b.getvalue())
    print(b.getvalue())


if __name__ == '__main__':
    main()
