#!/usr/bin/env python3
"""THE REVIEW QUEUE -- suspect structured reads of the town's minutes, pulled out for a
person to check.

    python3 scripts/review_queue.py --sweep                  # scan official-votes, add OPEN rows
    python3 scripts/review_queue.py --list                   # every OPEN item
    python3 scripts/review_queue.py --show council-on-aging/2026-07-14-7894
    python3 scripts/review_queue.py --resolve KEY --accept --note "..."
    python3 scripts/review_queue.py --resolve KEY --reread --note "..."   # ONE meeting, re-read
    python3 scripts/review_queue.py --check                  # the CSV is well-formed, every key exists

WHY. TJ, 7 October 2026: two schema-2 reads came back with their whole attendance list
dropped by the quote check -- council-on-aging 2026-07-14 (13 attendees) and
cemetery-commission 2026-07-30 (4) -- although both sets of minutes print attendance
("PRESENT", "In attendance:"). *"these should be FLAGGED somehow, show up on the chart,
put back into the backlog and need a direct review (pulled out of the normal flow of
processing so they can't back anything up)."*

WHAT A ROW IS. One flagged read, by key (as `extract_official_votes.out_path` names it:
`<board_slug>/<meeting_date>-<docid>`), with why it was flagged and what became of it.
Appended, never rewritten wholesale: read fully, re-read immediately before any write,
written back via temp + rename, the file's own newline convention preserved -- the same
discipline CLAUDE.md asks of every generated file several agents can touch.

THE SKIP RULE LIVES HERE, IN ONE PLACE. `open_keys()` is the single answer to "is this
meeting held for review", imported by process_meeting.py (steps/snapshot/queue) and by
build_backlog_depth.py (the needs-review count on the backlog chart) -- so the two can
never disagree about which meetings are pulled out of the normal flow.

THE SWEEP'S THREE RULES, A STARTING POINT -- report the counts; TJ tunes the thresholds:

  A. a quoted field had items and every one was dropped            an instrument failing,
     (dropped_unquoted_by_field[f] > 0 and the field kept 0)        not an absence -- 13c
  B. the file dropped MIN_TOTAL_DROPPED (5) or more items in total
  C. the file's own `note` says the TEXT is damaged -- OCR errors, pages missing,
     unreadable -- matched conservatively, per sentence, and never inside a clause that
     negates it ("No pages missing or unreadable sections identified" must not match)

A RESOLUTION IS TJ'S CALL. `--reread` runs extract_official_votes.py --force on exactly
ONE meeting -- never batched, and it is a real model call. Nothing in `--sweep`, `--list`
or `--show` ever calls a model.
"""
import argparse
import csv
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
CSV = os.path.join(ROOT, 'sources', 'data', 'review-queue.csv')
FIELDS = ['key', 'board_slug', 'meeting_date', 'reason', 'detail', 'flagged_on',
          'status', 'resolution', 'resolved_on', 'note']

MIN_TOTAL_DROPPED = 5    # rule B -- a starting point, see the module docstring

# Rule C: conservative phrases a note uses to say the TEXT ITSELF is damaged, never a
# judgement about what the minutes record. Checked one sentence at a time, and skipped
# where the same sentence negates it.
DAMAGE_PATTERNS = [
    r'unreadable', r'illegible', r'pages? missing', r'missing pages?',
    r'could not (?:be )?read', r'cannot (?:be )?read', r'could not be located',
    r'text breaks off', r'garbled', r'corrupt(?:ed)?', r'\bdamaged\b',
    r"(?:several|many|numerous|multiple|severe(?:ly)?)\s+[a-z' ]{0,20}"
    r'(?:ocr|transcription)\s+errors?',
]
NEGATORS = re.compile(r'\b(no|not|none|without|nor)\b', re.I)


def _rows():
    """The whole file, read fresh -- never cached, so a row written a moment ago by
    another process is never silently overwritten."""
    if not os.path.exists(CSV):
        return []
    with open(CSV, newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def _nl():
    """This file's own newline convention, so a write never changes it."""
    if not os.path.exists(CSV):
        return '\n'
    with open(CSV, 'rb') as fh:
        return '\r\n' if b'\r\n' in fh.read() else '\n'


def _write(rows):
    """The whole file, via temp + rename. Call sites re-read immediately before this."""
    nl = _nl()
    os.makedirs(os.path.dirname(CSV), exist_ok=True)
    tmp = CSV + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator=nl)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in FIELDS})
    os.replace(tmp, CSV)


def open_keys():
    """(board_slug, meeting_date) for every OPEN row -- the one skip rule, imported by
    process_meeting.py (steps/snapshot/queue) and build_backlog_depth.py (the
    needs-review count). A meeting held for review is pulled out of both."""
    return {(r['board_slug'], r['meeting_date']) for r in _rows() if r.get('status') == 'open'}


def held(board, date):
    return (board, date) in open_keys()


def open_rows():
    return [r for r in _rows() if r.get('status') == 'open']


def rows_for(key):
    return [r for r in _rows() if r['key'] == key]


def damage_match(note):
    """The first damage phrase in `note` that is not inside a negated clause, or None."""
    if not note:
        return None
    for sent in re.split(r'(?<=[.;])\s+', note):
        for pat in DAMAGE_PATTERNS:
            m = re.search(pat, sent, re.I)
            if m and not NEGATORS.search(sent[:m.start()]):
                return m.group(0)
    return None


def _flags(d):
    """Every (reason, detail) this schema-2 document earns, under the three rules."""
    import extract_official_votes as E
    out = []
    dropped_by = d.get('dropped_unquoted_by_field') or {}
    for f in E.QUOTED:
        n_dropped, n_kept = dropped_by.get(f, 0), len(d.get(f) or [])
        if n_dropped > 0 and n_kept == 0:
            out.append(('field_all_dropped:%s' % f, '%s: 0 kept, %d dropped' % (f, n_dropped)))
    total = d.get('dropped_unquoted', 0)
    if total >= MIN_TOTAL_DROPPED:
        out.append(('high_dropped_total', '%d dropped in total (>= %d)' % (total, MIN_TOTAL_DROPPED)))
    m = damage_match(d.get('note', ''))
    if m:
        out.append(('note_damage', 'note matched %r' % m))
    return out


def sweep():
    import extract_official_votes as E
    base = _rows()
    existing = {(r['key'], r['reason']) for r in base}
    by_rule = {'field_all_dropped': [0, 0], 'high_dropped_total': [0, 0], 'note_damage': [0, 0]}
    today = dt.date.today().isoformat()
    candidates = []
    for p in sorted(glob.glob(os.path.join(E.OUT, '*', '*.json'))):
        try:
            d = json.load(open(p, encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if E.schema_of(d) < 2:
            continue
        key = os.path.relpath(p, E.OUT)[:-5]
        board, date = d.get('board_slug', ''), d.get('meeting_date', '')
        for reason, detail in _flags(d):
            rule = reason.split(':')[0]
            by_rule.setdefault(rule, [0, 0])
            by_rule[rule][0] += 1
            if (key, reason) in existing:
                continue
            existing.add((key, reason))
            candidates.append(dict(key=key, board_slug=board, meeting_date=date, reason=reason,
                                   detail=detail, flagged_on=today, status='open', resolution='',
                                   resolved_on='', note=''))
    added = []
    if candidates:
        # RE-READ IMMEDIATELY BEFORE WRITING: another agent may have appended a row for
        # the same key+reason since `base` was read at the top of this function.
        fresh = _rows()
        fresh_keys = {(r['key'], r['reason']) for r in fresh}
        added = [c for c in candidates if (c['key'], c['reason']) not in fresh_keys]
        for c in added:
            by_rule[c['reason'].split(':')[0]][1] += 1
        if added:
            _write(fresh + added)
    label = {'field_all_dropped': 'a quoted field entirely dropped',
             'high_dropped_total': 'dropped %d or more in total' % MIN_TOTAL_DROPPED,
             'note_damage': 'note says the text is damaged'}
    for rule in sorted(by_rule):
        matched, new = by_rule[rule]
        print('  %-20s %-38s matched %3d file(s), %2d new row(s)' % (rule, label.get(rule, rule), matched, new))
    print('%d new row(s) added' % len(added))
    return added


def _list():
    rows = sorted(open_rows(), key=lambda r: (r['meeting_date'], r['board_slug'], r['reason']), reverse=True)
    if not rows:
        print('nothing open')
        return
    for r in rows:
        print('%-55s %-10s %-26s %s' % (r['key'], r['meeting_date'], r['reason'], r['detail']))
    print('%d open' % len(rows))


ATTEND_HEADING = re.compile(
    r'^(PRESENT|IN ATTENDANCE|ATTENDANCE|ALSO PRESENT|MEMBERS PRESENT|EXCUSED|ABSENT|GUESTS)\s*:?\s*$', re.I)


def _attendance_excerpt(text, lines=20):
    """The lines after an attendance heading -- `PRESENT`, `In attendance:` and their
    kin -- never the model's dropped output, which this file does not store."""
    ls = text.splitlines()
    out = []
    for i, ln in enumerate(ls):
        if ATTEND_HEADING.match(ln.strip()):
            out.append('  [%d] %s' % (i + 1, ln))
            for j in range(i + 1, min(i + 1 + lines, len(ls))):
                out.append('  [%d] %s' % (j + 1, ls[j]))
            out.append('  ...')
    return '\n'.join(out) if out else '  (no PRESENT / In attendance: heading found)'


def show(key):
    rows = rows_for(key)
    if not rows:
        sys.exit('no row for %s' % key)
    import extract_official_votes as E
    print(key)
    for r in rows:
        print('  [%s] %s -- %s' % (r['status'], r['reason'], r['detail']))
        if r['status'] != 'open':
            print('      resolved %s: %s -- %s' % (r['resolved_on'], r['resolution'], r['note']))
    p = os.path.join(E.OUT, key + '.json')
    if not os.path.exists(p):
        print('(no official-votes file at %s)' % os.path.relpath(p, ROOT))
        return
    d = json.load(open(p, encoding='utf-8'))
    print('kept, by field:    %s' % ', '.join('%s %d' % (f, len(d.get(f) or [])) for f in E.QUOTED))
    print('dropped, by field: %s (dropped_unquoted total %d)'
          % (d.get('dropped_unquoted_by_field') or {}, d.get('dropped_unquoted', 0)))
    src = os.path.join(ROOT, d['source']['text'])
    if os.path.exists(src):
        print('\nsource text (%s), attendance section:' % os.path.relpath(src, ROOT))
        print(_attendance_excerpt(open(src, encoding='utf-8', errors='replace').read()))
    else:
        print('(source text gone: %s)' % os.path.relpath(src, ROOT))


def resolve(key, how, note):
    mine = [r for r in rows_for(key) if r['status'] == 'open']
    if not mine:
        sys.exit('no OPEN row for %s' % key)
    board, date = mine[0]['board_slug'], mine[0]['meeting_date']
    outcome = ''
    if how == 'reread':
        cmd = ['python3', 'scripts/extract_official_votes.py', board, date, '--schema', '2', '--force']
        print('running ONE meeting, never batched: %s' % ' '.join(cmd))
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        print(r.stdout, end='')
        print(r.stderr, end='', file=sys.stderr)
        if r.returncode != 0:
            sys.exit('reread failed; row left open:\n%s' % (r.stdout + r.stderr)[-2000:])
        outcome = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ''
    # RE-READ IMMEDIATELY BEFORE WRITING, since --reread may have taken minutes.
    rows = _rows()
    today = dt.date.today().isoformat()
    n = 0
    for r in rows:
        if r['key'] == key and r['status'] == 'open':
            r['status'] = 'resolved'
            r['resolution'] = how
            r['resolved_on'] = today
            r['note'] = ((note or '') + (('; ' + outcome) if outcome else '')).strip('; ')
            n += 1
    if n == 0:
        sys.exit('no OPEN row for %s (resolved by someone else since this run started)' % key)
    _write(rows)
    print('resolved %d row(s) for %s as %s' % (n, key, how))


def check():
    import extract_official_votes as E
    rows = _rows()
    bad = []
    if os.path.exists(CSV):
        with open(CSV, 'rb') as fh:
            header = fh.readline().rstrip(b'\r\n').decode('utf-8')
        if header.split(',') != FIELDS:
            bad.append('header does not match FIELDS: %s' % header)
    seen_open = set()
    for i, r in enumerate(rows):
        for k in FIELDS:
            if k not in r:
                bad.append('row %d (%s): missing column %s' % (i, r.get('key'), k))
        if r.get('status') not in ('open', 'resolved'):
            bad.append('row %d (%s): bad status %r' % (i, r.get('key'), r.get('status')))
        if r.get('status') == 'resolved' and r.get('resolution') not in ('reread', 'accepted'):
            bad.append('row %d (%s): resolved with no valid resolution' % (i, r.get('key')))
        p = os.path.join(E.OUT, r['key'] + '.json')
        if not os.path.exists(p):
            bad.append('row %d: key does not exist on disk: %s' % (i, r['key']))
        dup = (r['key'], r['reason'])
        if r.get('status') == 'open':
            if dup in seen_open:
                bad.append('row %d: duplicate OPEN key+reason %s' % (i, dup))
            seen_open.add(dup)
    if bad:
        sys.exit('review queue: %d problem(s)\n  ' % len(bad) + '\n  '.join(bad))
    print('review queue: %d row(s), %d open, every key exists' % (len(rows), sum(r['status'] == 'open' for r in rows)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--sweep', action='store_true')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--show', metavar='KEY')
    ap.add_argument('--resolve', metavar='KEY')
    ap.add_argument('--reread', action='store_true')
    ap.add_argument('--accept', action='store_true')
    ap.add_argument('--note', default='')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.sweep:
        sweep()
    elif a.list:
        _list()
    elif a.show:
        show(a.show)
    elif a.resolve:
        if a.reread == a.accept:
            ap.error('--resolve needs exactly one of --reread or --accept')
        resolve(a.resolve, 'reread' if a.reread else 'accepted', a.note)
    elif a.check:
        return check()
    else:
        ap.error('nothing to do -- see --help')
    return 0


if __name__ == '__main__':
    sys.exit(main())
