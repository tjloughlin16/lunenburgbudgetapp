#!/usr/bin/env python3
"""ONE DEFINITION OF A MEETING'S RECORD -- read once, used by the backlog-depth chart
(`build_backlog_depth.py`), the per-board Recent-meetings table (`build_boards.py`) and
the per-board missing-records pages (`build_board_records.py`), so none of the three can
disagree about what counts as missing.

    from meeting_records import records, status, fiscal_year
    records()                      # every meeting, every board, newest first
    records('parks-commission')    # one board
    status(row, first_video)       # the rules alone, for a caller that already has a row

Reads `sources/data/meeting-register.csv` straight. Rows with `part_of` set are skipped
-- that meeting's record lives under another board's row (a sub-committee meeting folded
into its parent). Each returned dict:

    board, board_slug, date
    agenda      {posted: bool, url: str|None}
    due         'YYYY-MM-DD' or None -- when an absent record becomes MISSING (below)
    video       {status: 'posted'|'not-provided'|'not-available'|'missing'|'n/a', url, reason}
    minutes     {status: 'posted'|'not-provided'|'not-available'|'missing', url, reason}
    transcript  {status: 'posted'|'not-provided'|'not-available'|'missing'|'n/a', captions_disabled, reason}
    our_minutes {path, url, written, headline} or None

`reason` is set on an `'n/a'`, a `'not-available'` or a `'not-provided'` (where it is the
explanation, shown in full) -- never on `'missing'`, which speaks for itself.

A STATUS, NEVER A BARE BOOLEAN. `'n/a'` is not the same claim as "absent and should
exist" -- conflating them is the trap TJ named building the backlog-depth chart: a board
that has never once recorded a meeting must not look identical to a board that lost a
recording it would otherwise have posted. So:

- `video` is `'n/a'` when the board has no recording anywhere in the register (it does
  not record at all), OR when this meeting's date is before the board's own first dated
  recording. It is `'missing'` only for a date on or after that first recording, with no
  video found. Never `'missing'` in either `'n/a'` case.
- `transcript` is `'n/a'` whenever there is no video to have a transcript of; `'missing'`
  only when a video exists and no transcript does (which may be because captions are
  disabled on that upload -- carried separately as `captions_disabled`, never folded in).
- `minutes` has no `'n/a'` state: the town is always expected to publish minutes of a
  meeting it held, regardless of whether anybody filmed it.

OUR OWN MINUTES ARE A FOURTH, SEPARATE QUESTION -- `our_minutes_status()` below. They are
written FROM the recording, so they cannot exist before the video does; a meeting with no
video is not a gap in OUR work, it is waiting on the town's. States: `'posted'` (we have
them), `'pending'` (video is in, ours is still in the processing queue -- our backlog, not
the town's gap), `'needs-video'` (no video yet to write from), `'n/a'` (this board or date
is outside `recording-minutes-policy.csv`, so nothing will ever be written from it).

NOT AVAILABLE, VERSUS MISSING -- THE APPROVAL WINDOW. TJ, 7 October 2026: *"Only use the
word MISSING when anything goes beyond that timeline. Before that, call it 'not
available'."* The timeline is the Open Meeting Law's: a public body approves minutes "in a
timely manner", generally within the next three meetings or 30 days, whichever is later
(940 CMR 29.11(2)), unless it shows good cause. So an absent record is `'not-available'`
until its meeting's `due` date has passed, and `'missing'` only after:

    due = the later of (meeting + 30 days, the board's THIRD meeting after this one)

The three meetings are counted in the register, noticed meetings included, so a third
meeting already on the calendar gives a date in the future. A board that has not yet
noticed three more meetings has no `due` at all, and nothing of that meeting is missing
yet -- the window has not closed. The rule is about MINUTES; it is applied to the
recording and the transcript too, because TJ asked for one word, MISSING, to mean one
thing across the page. `'not-available'` never counts as missing, exactly like `'n/a'`.

The date is compared with `as_of` (today) here, for the surfaces that are built once --
the email report, the backlog chart. The web pages carry `due` and decide on the
READER'S clock, so a meeting turns MISSING the day its window closes without a deploy.

EXPLAINED, NOT MISSING. TJ, 7 October 2026, on the Parks Commission's 10 August 2026
meeting: *"there is no recording and will never be a recording as we met at the Town
Beach ... So we shouldn't say missing here. We should say something that it won't be
provided and that's ok."* `sources/data/meeting-record-explanations.csv` holds one row per
(board, date, record) somebody has explained, with who said so. An absent record with an
explanation is `'not-provided'`, its `reason` the explanation itself -- never missing,
never a gap, whatever the window says. A record that turns up anyway is `'posted'`; the
explanation does not hide it.

Verified against the file before trusting them (rule 13c): `agenda`, `minutes`, `video`,
`transcript` and `captions_disabled` are each only ever `'0'` or `'1'`, checked 7 October
2026 across all 7,057 rows.
"""
import csv
import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
REGISTER = os.path.join(ROOT, 'sources', 'data', 'meeting-register.csv')
EXPLANATIONS = os.path.join(ROOT, 'sources', 'data', 'meeting-record-explanations.csv')
RECORD_KINDS = ('video', 'minutes', 'transcript')
_explained = None


def explanations():
    """{(board_slug, date, record): explanation}, read once. A row naming a record kind
    that is not one of RECORD_KINDS is refused rather than ignored -- a typo would
    otherwise leave a meeting saying MISSING after somebody explained it."""
    global _explained
    if _explained is None:
        _explained = {}
        if os.path.exists(EXPLANATIONS):
            for r in csv.DictReader(open(EXPLANATIONS, encoding='utf-8')):
                if r['record'] not in RECORD_KINDS:
                    raise SystemExit('%s: record %r is not one of %s'
                                     % (os.path.relpath(EXPLANATIONS, ROOT), r['record'], RECORD_KINDS))
                if not r.get('explanation', '').strip():
                    raise SystemExit('%s: %s %s has no explanation'
                                     % (os.path.relpath(EXPLANATIONS, ROOT), r['board_slug'], r['date']))
                _explained[(r['board_slug'], r['date'], r['record'])] = r['explanation'].strip()
    return _explained


def fiscal_year(ym):
    """Massachusetts FY: July starts the next one. FY2023 is Jul 2022 - Jun 2023. `ym` is
    a date or a 'YYYY-MM' prefix; only the first 7 characters are read."""
    y, m = int(ym[:4]), int(ym[5:7])
    return y + 1 if m >= 7 else y


def is_held(date, as_of=None):
    """Has this meeting's date already passed? A meeting the town has noticed but not yet
    held is not missing anything -- nothing is due. `as_of` defaults to today."""
    return date <= (as_of or dt.date.today().isoformat())


def _truthy(v):
    return v in ('1', True, 1)


def _rows():
    if not os.path.exists(REGISTER):
        return []
    return [r for r in csv.DictReader(open(REGISTER, encoding='utf-8')) if not r.get('part_of')]


def first_video_dates(rows=None):
    """{board_slug: earliest date that board has ANY posted video}. A board absent from
    this dict has never recorded at all. Pass the rows already read from the register to
    avoid a second file read; omit to read it here."""
    first = {}
    for r in (rows if rows is not None else _rows()):
        d = r.get('date', '')
        if _truthy(r.get('video')) and len(d) >= 7:
            b = r.get('board_slug')
            if b and (b not in first or d < first[b]):
                first[b] = d
    return first


APPROVAL_DAYS = 30
APPROVAL_MEETINGS = 3


def due_dates(rows=None):
    """{(board_slug, date): due} -- the close of each meeting's approval window: the later
    of 30 days after it and the board's third meeting after it, or None when the board has
    not yet noticed three more. Counted over every dated register row, held or noticed."""
    by_board = {}
    for r in (rows if rows is not None else _rows()):
        d = r.get('date', '')
        if r.get('board_slug') and len(d) == 10:
            by_board.setdefault(r['board_slug'], set()).add(d)
    out = {}
    for b, ds in by_board.items():
        ds = sorted(ds)
        for i, d in enumerate(ds):
            third = ds[i + APPROVAL_MEETINGS] if i + APPROVAL_MEETINGS < len(ds) else None
            out[(b, d)] = third and max(third, (dt.date.fromisoformat(d) + dt.timedelta(days=APPROVAL_DAYS)).isoformat())
    return out


def window_open(due, as_of=None):
    """Is the approval window still open on `as_of` (today)? No `due` means it is: the
    board has not yet held the three meetings the window waits for."""
    return due is None or (as_of or dt.date.today().isoformat()) <= due


def _absent(due, as_of):
    """The status of a record that should exist and does not: MISSING only once the window
    has closed."""
    if window_open(due, as_of):
        return 'not-available', ('due by ' + due) if due else 'within the approval window'
    return 'missing', None


def status(row, first_video, due=None, as_of=None):
    """The rules alone, for ONE meeting row -- a dict with at least `board_slug`, `date`,
    `agenda`, `minutes`, `video`, `transcript`, `captions_disabled`, and either
    `video_url` (a single resolved URL) or `video_urls` (the register's own column).
    `first_video` is `first_video_dates()`'s result; `due` is this meeting's entry in
    `due_dates()` and `as_of` the day to judge it on (today). Takes '0'/'1' strings (as the CSV
    holds them) or plain booleans, so a caller with its own richer join of the same facts
    -- `build_boards.py` already assembles one from several sources -- can drive the same
    rules without a second read of the register."""
    b, d = row.get('board_slug'), row.get('date', '')
    has_video = _truthy(row.get('video'))
    board_records_at_all = b in first_video
    before_first = board_records_at_all and d < first_video[b]
    if has_video:
        v_status, v_reason = 'posted', None
    elif not board_records_at_all:
        v_status, v_reason = 'n/a', "board doesn't record"
    elif before_first:
        v_status, v_reason = 'n/a', 'before recordings began'
    else:
        v_status, v_reason = _absent(due, as_of)
    m_status, m_reason = ('posted', None) if _truthy(row.get('minutes')) else _absent(due, as_of)
    if not has_video:
        t_status, t_reason = 'n/a', 'no recording'
    elif _truthy(row.get('transcript')):
        t_status, t_reason = 'posted', None
    else:
        t_status, t_reason = _absent(due, as_of)
    # An explanation outranks every absent state -- 'n/a', the window and MISSING alike.
    ex = explanations()
    if v_status != 'posted' and (b, d, 'video') in ex:
        v_status, v_reason = 'not-provided', ex[(b, d, 'video')]
    if m_status != 'posted' and (b, d, 'minutes') in ex:
        m_status, m_reason = 'not-provided', ex[(b, d, 'minutes')]
    if t_status != 'posted' and (b, d, 'transcript') in ex:
        t_status, t_reason = 'not-provided', ex[(b, d, 'transcript')]
    video_url = row.get('video_url') or (row.get('video_urls') or '').split(',')[0].strip() or None
    return dict(
        due=due,
        agenda=dict(posted=_truthy(row.get('agenda')), url=row.get('agenda_url') or None),
        video=dict(status=v_status, url=video_url if has_video else None, reason=v_reason),
        minutes=dict(status=m_status, url=row.get('minutes_url') or None, reason=m_reason),
        transcript=dict(status=t_status, captions_disabled=_truthy(row.get('captions_disabled')), reason=t_reason),
    )


_POLICY = os.path.join(ROOT, 'sources', 'data', 'recording-minutes-policy.csv')


def policy_rows():
    """`recording-minutes-policy.csv`, read once and handed to `in_policy()` by a caller
    checking many meetings, rather than re-reading the file for each one."""
    if not os.path.exists(_POLICY):
        return []
    return [r for r in csv.DictReader(open(_POLICY, encoding='utf-8')) if r.get('board_slug') and r.get('since')]


def in_policy(board_slug, date, rows=None):
    """Is this (board, date) inside `recording-minutes-policy.csv` -- i.e. is OUR minutes
    ever meant to exist for it. `*` covers any board. The same test `refresh.covered()`
    applies when deciding what to write next; read directly here rather than importing
    `refresh`, which pulls in the whole daily-run module for one boolean."""
    rows = rows if rows is not None else policy_rows()
    return any(r['board_slug'] in (board_slug, '*') and date >= r['since'] for r in rows)


def our_minutes_status(has_our_minutes, video_status, policy_ok=True):
    """Our minutes are written FROM the recording, so a meeting with no video yet is not
    our gap -- it is waiting on the town's. Four states: `'posted'` (we have them),
    `'pending'` (video is in; ours is in the queue), `'needs-video'` (no video to write
    from yet), `'n/a'` (outside the policy -- nothing will be written from this one)."""
    if has_our_minutes:
        return dict(state='posted', reason=None)
    if not policy_ok:
        return dict(state='n/a', reason='not in our policy')
    if video_status == 'posted':
        return dict(state='pending', reason='in our queue')
    return dict(state='needs-video', reason='written from the recording')


def records(board_slug=None):
    """Every meeting (newest first) for `board_slug`, or for every board if omitted."""
    all_rows = _rows()
    first_video = first_video_dates(all_rows)
    due = due_dates(all_rows)
    rows = [r for r in all_rows if r['board_slug'] == board_slug] if board_slug is not None else all_rows
    out = []
    for r in rows:
        d = r.get('date', '')
        if len(d) < 7:
            continue
        b = r['board_slug']
        st = status(r, first_video, due.get((b, d)))
        our_minutes = None
        if r.get('our_minutes_path'):
            our_minutes = dict(path=r.get('our_minutes_path') or None, url=r.get('our_minutes_url') or None,
                                written=r.get('our_minutes_written') or None,
                                headline=r.get('our_minutes_headline') or None)
        out.append(dict(board=r.get('board') or b, board_slug=b, date=d, due=st['due'],
                         agenda=st['agenda'], video=st['video'], minutes=st['minutes'],
                         transcript=st['transcript'], our_minutes=our_minutes))
    out.sort(key=lambda m: m['date'], reverse=True)
    return out


def missing_only(rows):
    """`records()`, filtered to meetings missing at least one of video, minutes or
    transcript -- `'n/a'` and `'not-available'` never count as missing."""
    return [m for m in rows if is_missing(m)]


def is_missing(m):
    """One meeting dict (the shape `records()` or `status()` returns, merged with
    `board_slug`/`date`) is missing something -- `'n/a'` and `'not-available'` never count."""
    return m['video']['status'] == 'missing' or m['minutes']['status'] == 'missing' \
        or m['transcript']['status'] == 'missing'


def is_gap(m):
    """Something absent that should exist -- `'missing'` OR still `'not-available'` inside
    its approval window. What a gaps-only list shows; `is_missing()` is what it counts."""
    return any(m[k]['status'] in ('missing', 'not-available') for k in ('video', 'minutes', 'transcript'))
