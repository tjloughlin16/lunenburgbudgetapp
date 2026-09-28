#!/usr/bin/env python3
"""WHAT ONE PAGE OF INGEST COSTS IN AN ISOLATED SESSION. Measured, not estimated.

    python3 scripts/benchmark_ingest.py --fy 2017 --page 148

TJ, 27 September 2026: *"Never ingest with context heavy session"*, and then: *"take one
of the ingest categories and get through one unit and benchmark session usage. Don't use
YOUR session."*

WHY IT HAD TO BE MEASURED THIS WAY. The two unattended streams have a price -- $0.15 a
votes run, $0.45 a minutes run -- because they print what `claude -p --output-format json`
reports. The third category, the one the dashboard now marks NEEDS A SESSION, had no
price at all, and the only figure anybody had for it was a whole day's interactive session
divided by a guess. That is not a measurement of the work; it is a measurement of the
conversation the work happened inside.

So: one page, one `claude -p` call, nothing in front of it but the page. No conversation
history, no repo, no tools -- the boxes go in the prompt and structured rows come back.
That is the same work done in the cheapest place it can be done, and the difference
between this number and a session's is the whole argument for isolation.

The result appends to sources/data/ingest-benchmark.csv so a second run is comparable to
the first rather than a fresh opinion.
"""
import argparse
import collections
import csv
import datetime as dt
import glob
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import pdf_tables as T  # noqa: E402
import worklease  # noqa: E402

OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
OUT = os.path.join(ROOT, 'sources', 'data', 'ingest-benchmark.csv')
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
MODEL = 'claude-sonnet-5'

SCHEMA = {
    'type': 'object',
    'required': ['table', 'columns', 'rows', 'proved', 'note'],
    'properties': {
        'table': {'type': 'string', 'description': 'the title the page prints'},
        'columns': {'type': 'array', 'items': {'type': 'string'},
                    'description': 'column names AS PRINTED in the header, left to right'},
        'rows': {'type': 'array', 'items': {
            'type': 'object', 'required': ['label', 'values'],
            'properties': {'label': {'type': 'string'},
                           'values': {'type': 'array', 'items': {'type': 'string'}}}}},
        'proved': {'type': 'string',
                   'description': 'the identity or printed total the rows were checked '
                                  'against, and whether it held; "none" if the page '
                                  'states none'},
        'note': {'type': 'string',
                 'description': 'what could NOT be read, if anything'},
    },
}

SYSTEM = (
    'You read one page of a town annual report from OCR boxes and return its table. '
    'Rules, in order of importance. (1) Name columns ONLY from header words actually '
    'present on the page; never infer a column name from a position. (2) Place each '
    'figure under the column whose centre it is nearest, never by the order figures '
    'appear, because a row with no activity prints nothing in those columns. (3) If the '
    'page prints a total or states an identity, check the rows against it and say in '
    '`proved` whether it held. (4) If the header cannot be read, return no rows and say '
    'so in `note`. A refusal is a correct answer; a plausible guess is not.'
)


def page_boxes(fy, page):
    f = glob.glob(os.path.join(OCR, '*fy-%d-annual-town-report.tsv' % fy))
    if not f:
        raise SystemExit('no OCR for FY%d' % fy)
    by = collections.defaultdict(list)
    for b in T.read_boxes(f[0]):
        by[b['page']].append(b)
    bx = by.get(page) or []
    if not bx:
        raise SystemExit('no boxes on FY%d page %d' % (fy, page))
    return sorted(bx, key=lambda z: (-z['y'], z['x']))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fy', type=int, required=True)
    ap.add_argument('--page', type=int, required=True)
    ap.add_argument('--model', default=MODEL)
    a = ap.parse_args()

    # ONE PAGE, ONE READER. Two processes read this same page seventeen minutes apart on
    # 27 September 2026 -- about $4 of model spend for a second copy of an answer we had --
    # because both derived the same work list the same correct way and a page being read
    # looked exactly like a page nobody had opened. The claim is on the PAGE and not on the
    # batch, so any number of drivers, sweeps or sessions converge instead of colliding; a
    # lock around a batch would have been held by each of them separately.
    with worklease.claim('annual-page-fy%d-p%d' % (a.fy, a.page),
                         note='benchmark_ingest.py') as got:
        if not got:
            print('FY%d page %d is already being read by another process; skipped'
                  % (a.fy, a.page))
            return 0
        return read_page(a)


def read_page(a):
    bx = page_boxes(a.fy, a.page)
    prompt = ('Annual town report FY%d, page %d. OCR boxes, top to bottom, as '
              'y x text:\n\n' % (a.fy, a.page)
              + '\n'.join('%.3f %.3f %s' % (b['y'], b['x'], b['text']) for b in bx))

    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    began = dt.datetime.now()
    r = subprocess.run(
        ['claude', '-p', '--tools', '', '--model', a.model, '--system-prompt', SYSTEM,
         '--json-schema', json.dumps(SCHEMA), '--output-format', 'json',
         '--max-budget-usd', '2'],
        input=prompt, capture_output=True, text=True, env=env, timeout=900)
    secs = (dt.datetime.now() - began).total_seconds()
    if r.returncode != 0:
        raise SystemExit('claude failed:\n' + (r.stdout + r.stderr)[-1500:])
    res = json.loads(r.stdout)
    body = res.get('structured_output') or res.get('result')
    if isinstance(body, str):
        body = json.loads(body)
    cost = res.get('total_cost_usd')
    rows = len(body.get('rows') or [])

    # THE RUN KEEPS ITS WORK. The first version measured a page and threw the table away,
    # which is paying for an extraction to learn what an extraction costs. Each run now
    # writes what it read beside the benchmark row, so the benchmark IS the ingest.
    got = os.path.join(ROOT, 'sources', 'data', 'annual-report-reads')
    os.makedirs(got, exist_ok=True)
    doc = os.path.join(got, 'fy%d-p%d.json' % (a.fy, a.page))
    with open(doc, 'w', encoding='utf-8') as fh:
        json.dump(dict(fy=a.fy, page=a.page, model=a.model, boxes=len(bx),
                       read_by='scripts/benchmark_ingest.py',
                       at=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                       cost_usd=cost, **body), fh, indent=1, ensure_ascii=False)
        fh.write('\n')

    new = not os.path.exists(OUT)
    with open(OUT, 'a', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh, lineterminator='\n')
        if new:
            w.writerow(['at', 'fy', 'page', 'model', 'boxes', 'rows_returned',
                        'cost_usd', 'seconds', 'pct_of_week', 'proved', 'note'])
        w.writerow([dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    a.fy, a.page, a.model, len(bx), rows,
                    '' if cost is None else '%.4f' % cost, '%.1f' % secs,
                    '' if cost is None else '%.3f' % (cost / 5.0),
                    (body.get('proved') or '')[:200], (body.get('note') or '')[:200]])

    print('  saved    : %s' % os.path.relpath(doc, ROOT))
    print('FY%d page %d — %d OCR boxes' % (a.fy, a.page, len(bx)))
    print('  table    : %s' % (body.get('table') or '(not stated)'))
    print('  columns  : %s' % ', '.join(body.get('columns') or []) or '(none read)')
    print('  rows     : %d' % rows)
    print('  proved   : %s' % (body.get('proved') or '(nothing stated)'))
    if body.get('note'):
        print('  note     : %s' % body['note'])
    print('  COST     : $%.4f  (~%.3f%% of the weekly allowance)  in %.0fs'
          % (cost or 0, (cost or 0) / 5.0, secs))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
