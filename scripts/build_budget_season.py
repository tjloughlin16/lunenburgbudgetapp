#!/usr/bin/env python3
"""A BUDGET SEASON AS A STATUS BOARD -- the state view, backed by the event log.

    python3 scripts/build_budget_season.py fy27            # -> fy28/public/data/budget-season-fy27.json
    python3 scripts/build_budget_season.py fy27 --check    # ...and fail if it is stale or a citation is dead

notes/process/BUDGET-SEASON-MODEL.md is the model. TJ, 14 September 2026: "the event log
should back up the state view. So we have the state view, then it can be 'built' or
reviewed/audited from the event log."

The state view is sources/data/budget-seasons/<fy>.csv, written by hand (retro) or from
rows the refresh proposes (live): block, item, scope, status, figure, fte, date, who, why,
evidence, note. The event log is what the evidence column points at, and EVERY citation is
resolved here or the build fails:

    board/date@seconds   our record of that meeting -- the budget-state file for that
                         recording (write_budget_state.py), or our minutes of it where the
                         extraction has not run (2025); resolved to the minutes page and the
                         video at that second
    doc:<path>           a document in the archive, resolved to its /docs/ address
    ballot:<date>        rows in sources/data/ballot-questions.csv for that election

<fy>-lines.csv (extract_scenario_lines.py) rides along: every budget line the scenarios
differ on, footed to the documents, so the cut list can be checked against it.
"""
import argparse
import csv
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEASONS = os.path.join(ROOT, 'sources', 'data', 'budget-seasons')
STATE = os.path.join(ROOT, 'sources', 'data', 'budget-state')
MINUTES = os.path.join(ROOT, 'sources', 'data', 'recording-minutes')
BALLOT = os.path.join(ROOT, 'sources', 'data', 'ballot-questions.csv')
OUTDIR = os.path.join(ROOT, 'fy28', 'public', 'data')
BLOCKS = ['deficit', 'proposals', 'cuts', 'override', 'late', 'final']


def read_csv(p):
    return list(csv.DictReader(open(p, encoding='utf-8')))


def doc_label(rel):
    """The publisher's own title from the folder's index, so a reader sees 'FY27 Budget
    Projections as of 3-23-26' rather than a filename. Our analyses are labelled as ours."""
    if rel.startswith('sources/analyses/'):
        return 'our analysis: ' + os.path.basename(rel).replace('.md', '').replace('-', ' ')
    m = re.match(r'^sources/meetings/text/([a-z0-9-]+)/(\d{4}-\d{2}-\d{2})-(agenda|minutes)-\d+\.txt$', rel)
    if m:                                    # the town's own minutes or agenda, named as a reader would
        board = ' '.join(w.capitalize() for w in m.group(1).split('-'))
        d = m.group(2)
        return '%s %s, %s' % (board, m.group(3), __import__('datetime').date.fromisoformat(d).strftime('%-d %b %Y'))
    folder = rel.split('/')[1]
    idx = os.path.join(ROOT, 'sources', folder, 'index.csv')
    if os.path.exists(idx):
        for r in read_csv(idx):
            if r.get('local') == rel:
                return __import__('html').unescape(r.get('label') or os.path.basename(rel)).replace('&nbsp;', '').strip()
    return os.path.basename(rel)


def resolve(ev):
    """One citation -> where a reader goes. Fails loudly on a dead one."""
    ev = (ev or '').strip()
    if not ev:
        return None
    if ev.startswith('doc:'):
        rel = ev[4:]
        if not os.path.exists(os.path.join(ROOT, rel)):
            raise SystemExit('dead citation: %s' % ev)
        return dict(kind='document', href='/docs/' + rel.split('sources/', 1)[1], label=doc_label(rel))
    if ev.startswith('ballot:'):
        date = ev[7:]
        qs = [r for r in read_csv(BALLOT) if r['date'] == date]
        if not qs:
            raise SystemExit('dead citation: %s (no ballot rows)' % ev)
        return dict(kind='ballot', href='/data/ballot-questions.csv', label='%s, %s' % (qs[0]['election'], date))
    m = re.match(r'^([a-z0-9-]+)/(\d{4}-\d{2}-\d{2})@(\d+)$', ev)
    if not m:
        raise SystemExit('unreadable citation: %s' % ev)
    board, date, t = m.group(1), m.group(2), int(m.group(3))
    # our record of the meeting: the budget-state file (2026 on) or our minutes of the recording
    files = glob.glob(os.path.join(STATE, board, '%s-*.json' % date)) or glob.glob(os.path.join(MINUTES, board, '%s-*.json' % date))
    if not files:
        raise SystemExit('dead citation: %s (no budget-state file and no minutes of ours for that meeting)' % ev)
    d = json.load(open(files[0], encoding='utf-8'))
    return dict(kind='meeting', board=d['board'], board_slug=board, date=date, t=t,
                href='%s&t=%ds' % (d['video_url'], t) if t else d['video_url'],
                page='/meeting-minutes/%s/%s-%s' % (board, date, d['video_id']),
                label='%s, %s%s' % (d['board'], date, (' · %d:%02d' % (t // 60, t % 60)) if t else ''))


def build(fy):
    rows = read_csv(os.path.join(SEASONS, '%s.csv' % fy))
    blocks = {b: [] for b in BLOCKS}
    for i, r in enumerate(rows):
        if r['block'] not in blocks:
            raise SystemExit('row %d: unknown block %r' % (i + 2, r['block']))
        blocks[r['block']].append(dict(r, fte=float(r['fte']) if r['fte'] else None, cite=resolve(r['evidence'])))
    for b in blocks:
        if b != 'proposals':                 # proposals stay in the order the publisher printed them
            blocks[b].sort(key=lambda r: r['date'])
    lines_p = os.path.join(SEASONS, '%s-lines.csv' % fy)
    lines = read_csv(lines_p) if os.path.exists(lines_p) else []
    for r in lines:
        for k in ('level_service', 'balanced', 'tier1_core', 'tier2_restoration', 'cut', 'tier1_restores', 'tier2_restores'):
            r[k] = float(r[k]) if r[k] else None
    return dict(fy=int(fy[2:]) + 2000, source='sources/data/budget-seasons/%s.csv' % fy, rows=len(rows), blocks=blocks, lines=lines,
                model='notes/process/BUDGET-SEASON-MODEL.md')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('fy')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    out = os.path.join(OUTDIR, 'budget-season-%s.json' % a.fy)
    text = json.dumps(build(a.fy), indent=1, sort_keys=True, ensure_ascii=False) + '\n'
    if a.check:
        have = open(out, encoding='utf-8').read() if os.path.exists(out) else ''
        print('ok — %s reproduces; every citation resolves' % os.path.relpath(out, ROOT) if have == text else 'STALE ' + out)
        return 0 if have == text else 1
    open(out, 'w', encoding='utf-8').write(text)
    d = json.loads(text)
    print('%s: %d rows — %s' % (os.path.relpath(out, ROOT), d['rows'], ', '.join('%s %d' % (b, len(d['blocks'][b])) for b in BLOCKS)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
