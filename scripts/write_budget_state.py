#!/usr/bin/env python3
"""What the budget boards have put on the record about THE BUDGET: the deficit as stated,
the cuts as named, the override as sized -- one file per meeting, written by a model from
the captions, so the budget feed can show the latest and what changed.

    python3 scripts/write_budget_state.py --since 2026-06-15   # every budget-board meeting with a transcript since
    python3 scripts/write_budget_state.py school-committee 2026-09-09
    python3 scripts/write_budget_state.py --check
    python3 scripts/write_budget_state.py --status

TJ, 14 September 2026: "if the school committee announces a deficit, or announces cuts, it
needs to show on this page the most recent information -- 'School committee announced 10
cuts for a $2m deficit'. So something like key metrics: school and town deficits and cuts
that have been discussed/announced, with totals. The cuts named so far (keeping up with
changes, for when the cut lists change weekly)."

WHAT IS EXTRACTED, and what is not. STATEMENTS: a figure somebody put on the record about
the budget being built -- a deficit or gap, a budget total, an override amount, a state-aid
figure -- with the fiscal year it is for, who said it BY ROLE (the superintendent, the town
manager, the chair; never a name -- rule 8), whether it was announced, proposed, voted or
withdrawn, and the second in the video. CUTS: each reduction named, with its amount and
FTE as heard and its status. Every figure is AS HEARD from machine captions, which mishear
numbers; the page says so, and the second in the video is what a reader checks.

NOT extracted: a department's spending, a transfer between lines, a grant, a fee. Money,
but not the budget. The same line the budget feed draws.

The same discipline as write_recording_minutes.py: output keyed to the transcript's sha256,
current files skipped, the cost recorded. Runs inside the refresh for the three budget
boards' new recordings, and by hand for a window.
"""
import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from write_recording_minutes import transcripts, lines_for, sha256_of, NODE22, MODEL   # noqa: E402

OUT = os.path.join(ROOT, 'sources', 'data', 'budget-state')
BOARDS = ('school-committee', 'select-board', 'finance-committee')

SYSTEM = """You read machine captions of a Massachusetts town board meeting and extract ONLY what was put on the record about THE BUDGET BEING BUILT for a coming fiscal year and what will go to Town Meeting: deficits or gaps stated, budget totals stated, override amounts, state aid (Chapter 70) figures, free cash to be used, and every CUT named (a position, a program, a line) with its amount and FTE where said.

Rules:
- Figures are AS HEARD. Copy the number the captions carry; do not correct or infer. If no figure was said, leave amount empty.
- Say WHO by role only: the superintendent, the business administrator, the town manager, the chair, a member, a resident. Never a name.
- Status: announced (stated as fact by staff or chair), proposed (put forward for discussion), voted (a motion carried), restored (a cut reversed), withdrawn.
- Scope: school (the school department budget), town (the omnibus/municipal budget), both.
- Include the fiscal year the statement is about (e.g. 2027, 2028) when it can be told from context; otherwise null.
- t is the caption line's seconds.
- Do NOT include: line-item transfers within the current year, grants, fees, a department's spending review, closeouts of past years, capital projects unless framed as a warrant article amount.
- If nothing qualifies, return empty lists. Do not invent."""

SCHEMA = {
    "type": "object",
    "properties": {
        "statements": {"type": "array", "items": {"type": "object", "properties": {
            "kind": {"type": "string", "enum": ["deficit", "budget_total", "override", "state_aid", "free_cash", "levy", "other"]},
            "scope": {"type": "string", "enum": ["school", "town", "both"]},
            "fiscal_year": {"type": ["integer", "null"]},
            "amount_as_heard": {"type": ["string", "null"]},
            "statement": {"type": "string", "description": "one line, what was said, in plain words"},
            "who": {"type": "string", "description": "by role, never a name"},
            "status": {"type": "string", "enum": ["announced", "proposed", "voted", "restored", "withdrawn"]},
            "t": {"type": "integer"}},
            "required": ["kind", "scope", "fiscal_year", "amount_as_heard", "statement", "who", "status", "t"]}},
        "cuts": {"type": "array", "items": {"type": "object", "properties": {
            "item": {"type": "string", "description": "the position, program or line, in the words used"},
            "scope": {"type": "string", "enum": ["school", "town"]},
            "fiscal_year": {"type": ["integer", "null"]},
            "amount_as_heard": {"type": ["string", "null"]},
            "fte_as_heard": {"type": ["string", "null"]},
            "status": {"type": "string", "enum": ["announced", "proposed", "voted", "restored", "withdrawn"]},
            "who": {"type": "string"},
            "t": {"type": "integer"}},
            "required": ["item", "scope", "fiscal_year", "amount_as_heard", "fte_as_heard", "status", "who", "t"]}},
        "nothing_on_the_budget": {"type": "boolean"}},
    "required": ["statements", "cuts", "nothing_on_the_budget"]}


def out_path(t):
    return os.path.join(OUT, t['board_slug'], '%s-%s.json' % (t['date'], t['video_id']))


def current(t):
    p = out_path(t)
    return os.path.exists(p) and json.load(open(p)).get('source', {}).get('sha256') == sha256_of(t['path'])


def write_one(t):
    if current(t):
        return 'current'
    doc = json.load(open(t['path'], encoding='utf-8'))
    lines = lines_for(doc)
    if len(lines) < 5:
        return 'too short'
    board = doc.get('title') or t['board_slug'].replace('-', ' ').title()
    prompt = ('Meeting: %s, %s. Recording: %s\n\nCaptions (%d lines, [seconds] text):\n\n%s'
              % (board, t['date'], doc.get('video_url'), len(lines), '\n'.join(lines)))
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    r = subprocess.run(['claude', '-p', '--tools', '', '--model', MODEL, '--system-prompt', SYSTEM,
                        '--json-schema', json.dumps(SCHEMA), '--output-format', 'json', '--max-budget-usd', '1'],
                       input=prompt, capture_output=True, text=True, env=env, timeout=900)
    if r.returncode != 0:
        raise SystemExit('claude failed on %s:\n%s' % (t['rel'], (r.stdout + r.stderr)[-2000:]))
    res = json.loads(r.stdout)
    body = res.get('structured_output') or res.get('result')
    if isinstance(body, str):
        body = json.loads(body)
    if not isinstance(body, dict) or 'statements' not in body:
        raise SystemExit('no structured output for %s' % t['rel'])
    os.makedirs(os.path.dirname(out_path(t)), exist_ok=True)
    with open(out_path(t), 'w', encoding='utf-8') as fh:
        json.dump(dict(
            warning=('EXTRACTED BY A LANGUAGE MODEL FROM MACHINE CAPTIONS. Every figure is as heard and may be '
                     'misheard; every line carries the second in the video, which is the record.'),
            board_slug=t['board_slug'], board=board, meeting_date=t['date'], video_id=t['video_id'],
            video_url=doc.get('video_url') or 'https://www.youtube.com/watch?v=' + t['video_id'],
            source=dict(transcript=t['rel'], sha256=sha256_of(t['path'])),
            written=dict(by='scripts/write_budget_state.py', model=MODEL,
                         at=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), cost_usd=res.get('total_cost_usd')),
            state=body), fh, indent=1, sort_keys=True)
        fh.write('\n')
    return 'written ($%.3f) — %d statements, %d cuts' % (res.get('total_cost_usd') or 0, len(body['statements']), len(body['cuts']))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('board_pos', nargs='?', metavar='board')
    ap.add_argument('date', nargs='?')
    ap.add_argument('--since')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--status', action='store_true')
    a = ap.parse_args()
    ts = [t for t in transcripts() if t['board_slug'] in BOARDS]
    if a.check:
        bad = 0
        for f in glob.glob(os.path.join(OUT, '*', '*.json')):
            d = json.load(open(f))
            p = os.path.join(ROOT, d['source']['transcript'])
            if not os.path.exists(p) or sha256_of(p) != d['source']['sha256']:
                print('STALE', os.path.relpath(f, ROOT)); bad += 1
        print('%d budget-state file(s), %d problem(s)' % (len(glob.glob(os.path.join(OUT, '*', '*.json'))), bad))
        return 1 if bad else 0
    if a.status:
        have = {os.path.relpath(f, OUT)[:-5] for f in glob.glob(os.path.join(OUT, '*', '*.json'))}
        for b in BOARDS:
            n = sum(1 for t in ts if t['board_slug'] == b)
            h = sum(1 for t in ts if t['board_slug'] == b and '%s/%s-%s' % (b, t['date'], t['video_id']) in have)
            print('  %-20s %3d transcripts, %3d with budget state' % (b, n, h))
        return 0
    if a.board_pos and a.date:
        ts = [t for t in ts if t['board_slug'] == a.board_pos and t['date'] == a.date]
    elif a.since:
        ts = [t for t in ts if t['date'] >= a.since]
    else:
        ap.error('name a board and date, or --since')
    ts.sort(key=lambda t: t['date'], reverse=True)
    ts = [t for t in ts if not current(t)]
    if a.limit:
        ts = ts[:a.limit]
    for t in ts:
        print('%s %s  %s' % (t['board_slug'], t['date'], write_one(t)), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
