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
    video       {status: 'posted'|'missing'|'n/a', url: str|None, reason: str|None}
    minutes     {status: 'posted'|'missing', url: str|None}
    transcript  {status: 'posted'|'missing'|'n/a', captions_disabled: bool, reason: str|None}
    our_minutes {path, url, written, headline} or None

`reason` is only ever set on an `'n/a'`, two to four words, for a tooltip -- never on
`'missing'`, which speaks for itself.

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


def status(row, first_video):
    """The rules alone, for ONE meeting row -- a dict with at least `board_slug`, `date`,
    `agenda`, `minutes`, `video`, `transcript`, `captions_disabled`, and either
    `video_url` (a single resolved URL) or `video_urls` (the register's own column).
    `first_video` is `first_video_dates()`'s result. Takes '0'/'1' strings (as the CSV
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
        v_status, v_reason = 'missing', None
    m_status = 'posted' if _truthy(row.get('minutes')) else 'missing'
    if not has_video:
        t_status, t_reason = 'n/a', 'no recording'
    elif _truthy(row.get('transcript')):
        t_status, t_reason = 'posted', None
    else:
        t_status, t_reason = 'missing', None
    video_url = row.get('video_url') or (row.get('video_urls') or '').split(',')[0].strip() or None
    return dict(
        agenda=dict(posted=_truthy(row.get('agenda')), url=row.get('agenda_url') or None),
        video=dict(status=v_status, url=video_url if has_video else None, reason=v_reason),
        minutes=dict(status=m_status, url=row.get('minutes_url') or None),
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
    rows = [r for r in all_rows if r['board_slug'] == board_slug] if board_slug is not None else all_rows
    out = []
    for r in rows:
        d = r.get('date', '')
        if len(d) < 7:
            continue
        b = r['board_slug']
        st = status(r, first_video)
        our_minutes = None
        if r.get('our_minutes_path'):
            our_minutes = dict(path=r.get('our_minutes_path') or None, url=r.get('our_minutes_url') or None,
                                written=r.get('our_minutes_written') or None,
                                headline=r.get('our_minutes_headline') or None)
        out.append(dict(board=r.get('board') or b, board_slug=b, date=d,
                         agenda=st['agenda'], video=st['video'], minutes=st['minutes'],
                         transcript=st['transcript'], our_minutes=our_minutes))
    out.sort(key=lambda m: m['date'], reverse=True)
    return out


def missing_only(rows):
    """`records()`, filtered to meetings missing at least one of video, minutes or
    transcript -- `'n/a'` never counts as missing."""
    return [m for m in rows if is_missing(m)]


def is_missing(m):
    """One meeting dict (the shape `records()` or `status()` returns, merged with
    `board_slug`/`date`) is missing something -- `'n/a'` never counts."""
    return m['video']['status'] == 'missing' or m['minutes']['status'] == 'missing' \
        or m['transcript']['status'] == 'missing'
