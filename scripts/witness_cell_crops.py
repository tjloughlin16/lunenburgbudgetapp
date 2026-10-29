#!/usr/bin/env python3
"""CROP, READ, DECIDE: an independent reader confirms a cell the arithmetic located.

    python3 scripts/locate_cell_misreads.py --all          # 1. candidates (no network)
    python3 scripts/witness_cell_crops.py crops            # 2. one PNG per candidate (no network)
    python3 scripts/witness_cell_crops.py read --limit 5   # 3. `claude -p` reads the crops (costs usage)
    python3 scripts/witness_cell_crops.py reading KEY TEXT --reader NAME   # 3'. a person's blind reading
    python3 scripts/witness_cell_crops.py decide           # 4. accept only an exact match; log the rest

notes/process/ANNUAL-REPORT-CELL-WITNESS.md is the process and says what it will not do.

BLIND. The reader is shown the cropped cell and nothing else: not Textract's text, not the
value the arithmetic requires. `decide` is where the two meet, and only there. An agreeing
reading proves the digits because the reader and the arithmetic reached the same figure by
independent routes; Textract re-reading the same pixels would share the error.

ACCEPT only when the reading, parsed, equals the required value EXACTLY. Then the cell goes to
`report-tables/<ed>/witnessed-cells.csv` (read_report_tables.apply_witnessed_cells applies it).
A reading that differs corrects nothing, and is logged in `cell-witness-log.csv` beside it and
stamped on the matching row of notes/generated/annual-report-discrepancies.csv.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import glob
import json
import os
import subprocess
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import page_integrity  # noqa: E402
import reconcile_totals as RT  # noqa: E402
import validate_totals as V  # noqa: E402
from locate_cell_misreads import FIELDS as CAND_FIELDS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, 'build', 'cell-witness')
CROPS = os.path.join(BASE, 'crops')
READINGS = os.path.join(BASE, 'readings.csv')
RFIELDS = ['key', 'reader', 'text', 'legible', 'crop', 'date', 'cost_usd']
FOLDERS = os.path.join(ROOT, 'sources', 'data', 'report-tables')
REGISTER = os.path.join(ROOT, 'notes', 'generated', 'annual-report-discrepancies.csv')
SCALE = 6                      # 432 dpi
MARGIN_X, MARGIN_Y = 0.006, 0.004
MODEL = 'sonnet'
SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['text', 'legible'],
          'properties': {'text': {'type': 'string'}, 'legible': {'type': 'boolean'}}}
SYSTEM = ('You transcribe one figure from a scanned municipal report, exactly as printed. You never '
          'correct, round or compute anything. If a digit cannot be read, write ? in its place.')


def key_of(r):
    return '%s:%s:%s:%s:%s' % (r['edition'], r['page'], r['table'], r['row'], r['col'])


def candidates():
    out = []
    for f in sorted(glob.glob(os.path.join(BASE, 'candidates-*.csv'))):
        out += list(csv.DictReader(open(f, newline='', encoding='utf-8')))
    return out


def crop_path(r):
    return os.path.join(CROPS, '%s-p%s-t%sr%sc%s.png' % (r['edition'], r['page'], r['table'], r['row'], r['col']))


def readings():
    if not os.path.exists(READINGS):
        return {}
    return {r['key']: r for r in csv.DictReader(open(READINGS, newline='', encoding='utf-8'))}


def save_reading(row):
    cur = readings()
    cur[row['key']] = row
    os.makedirs(BASE, exist_ok=True)
    with open(READINGS, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, RFIELDS, lineterminator='\n')
        w.writeheader()
        w.writerows(cur[k] for k in sorted(cur))


def make_crops():
    import pypdfium2
    os.makedirs(CROPS, exist_ok=True)
    n = 0
    pdfs = {}
    for r in candidates():
        if not r['bbox']:
            print('no box for', key_of(r))
            continue
        ed = json.load(open(os.path.join(FOLDERS, r['edition'], 'edition.json'), encoding='utf-8'))
        pdf = pdfs.setdefault(r['edition'], pypdfium2.PdfDocument(os.path.join(ROOT, ed['pdf'])))
        b = json.loads(r['bbox'])
        page = int(r['page'])
        img = pdf[page - 1].render(scale=SCALE).to_pil()
        w, h = img.size
        box = (max(0, b['Left'] - MARGIN_X), max(0, b['Top'] - MARGIN_Y),
               min(1, b['Left'] + b['Width'] + MARGIN_X), min(1, b['Top'] + b['Height'] + MARGIN_Y))
        img = img.crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)))
        turn = RT.reading_turn(RT.cache_blocks(r['sha'], page))
        img.rotate(turn, expand=True).save(crop_path(r))
        n += 1
    print('%d crop(s) in %s' % (n, os.path.relpath(CROPS, ROOT)))


def read_with_claude(limit):
    done = readings()
    sent = 0
    for r in candidates():
        k = key_of(r)
        if k in done and done[k]['reader'].startswith('claude'):
            continue
        if sent >= limit:
            break
        path = crop_path(r)
        prompt = ('Read the image %s. It is one cell cropped from a scanned page of a town report. '
                  'Transcribe the figure printed in it exactly as printed, with any $ sign, commas, '
                  'decimal point, minus sign or parentheses. Set legible false if you cannot read it.' % path)
        p = subprocess.run(['claude', '-p', '--model', MODEL, '--tools', 'Read', '--allowedTools', 'Read',
                            '--system-prompt', SYSTEM, '--json-schema', json.dumps(SCHEMA),
                            '--output-format', 'json', '--max-budget-usd', '0.5'],
                           input=prompt, capture_output=True, text=True, timeout=300, cwd=ROOT,
                           env={**os.environ, 'CLAUDE_CODE_ENTRYPOINT': 'witness_cell_crops'})
        if p.returncode != 0:
            raise SystemExit('claude failed on %s:\n%s' % (k, (p.stdout + p.stderr)[-1000:]))
        res = json.loads(p.stdout)
        body = res.get('structured_output') or res.get('result')
        body = json.loads(body) if isinstance(body, str) else body
        save_reading({'key': k, 'reader': 'claude-p:' + MODEL, 'text': body['text'],
                      'legible': str(bool(body['legible'])), 'crop': os.path.relpath(path, ROOT),
                      'date': datetime.date.today().isoformat(), 'cost_usd': res.get('total_cost_usd', '')})
        sent += 1
        print('%s -> %r (legible %s, $%s)' % (k, body['text'], body['legible'], res.get('total_cost_usd')))
    print('%d call(s)' % sent)


def stamp_register(r, reading, note):
    if not os.path.exists(REGISTER):
        return 0
    with open(REGISTER, newline='') as fh:
        rd = csv.DictReader(fh)
        fields, rows = rd.fieldnames, list(rd)
    stem = json.load(open(os.path.join(FOLDERS, r['edition'], 'edition.json'), encoding='utf-8'))['stem']
    n = 0
    for x in rows:
        if x['document'].endswith(stem + '.pdf') and x['page'] == r['page'] and \
                ("%s '" % r['ref']) in x['correction'] and not x['verdict']:
            x['verdict'], x['decided_by'], x['crop'], x['note'] = \
                'witness_disagrees', 'cell witness %s' % reading['reader'], reading['crop'], note
            n += 1
    if n:
        with open(REGISTER + '.tmp', 'w', newline='') as fh:
            w = csv.DictWriter(fh, fields, lineterminator='\n')
            w.writeheader()
            w.writerows(rows)
        os.replace(REGISTER + '.tmp', REGISTER)
    return n


def decide():
    got = readings()
    by_ed = {}
    for r in candidates():
        by_ed.setdefault(r['edition'], []).append(r)
    summary = {'accepted': 0, 'disagreed': 0, 'unread': 0}
    for ed, rows in sorted(by_ed.items()):
        d = os.path.join(FOLDERS, ed)
        wpath, lpath = os.path.join(d, 'witnessed-cells.csv'), os.path.join(d, 'cell-witness-log.csv')
        WF = ['page', 'table', 'row', 'col', 'ref', 'textract_text', 'corrected_text', 'witness', 'closes']
        LF = ['page', 'table', 'row', 'col', 'ref', 'textract_text', 'reading', 'required_value', 'outcome',
              'reader', 'crop', 'date']
        wit = {(x['page'], x['table'], x['row'], x['col']): x for x in
               (csv.DictReader(open(wpath, newline='', encoding='utf-8')) if os.path.exists(wpath) else [])}
        log = {(x['page'], x['table'], x['row'], x['col']): x for x in
               (csv.DictReader(open(lpath, newline='', encoding='utf-8')) if os.path.exists(lpath) else [])}
        for r in rows:
            k = key_of(r)
            ck = (r['page'], r['table'], r['row'], r['col'])
            rd = got.get(k)
            if rd is None or rd['legible'] != 'True':
                summary['unread'] += 1
                continue
            value = V.parse(rd['text'])[0]
            ok = value is not None and value == Decimal(r['required_value'].replace(',', ''))
            outcome = 'accepted' if ok else 'disagrees'
            summary['accepted' if ok else 'disagreed'] += 1
            log[ck] = {'page': r['page'], 'table': r['table'], 'row': r['row'], 'col': r['col'], 'ref': r['ref'],
                       'textract_text': r['textract_text'], 'reading': rd['text'],
                       'required_value': r['required_value'], 'outcome': outcome, 'reader': rd['reader'],
                       'crop': rd['crop'], 'date': rd['date']}
            if ok:
                wit[ck] = {'page': r['page'], 'table': r['table'], 'row': r['row'], 'col': r['col'],
                           'ref': r['ref'], 'textract_text': r['textract_text'], 'corrected_text': rd['text'],
                           'witness': 'read independently by %s from %s on %s, blind to Textract and to the '
                                      'required value; equals the value both identities require' % (
                                          rd['reader'], rd['crop'], rd['date']),
                           'closes': '%s ; %s' % (r['row_identity'], r['column_identity'])}
            else:
                n = stamp_register(r, rd, 'reader saw `%s`; arithmetic required %s; nothing corrected'
                                   % (rd['text'], r['required_value']))
                print('disagree %s: reader %r vs required %s (register rows stamped: %d)' % (
                    k, rd['text'], r['required_value'], n))
        for path, fields, data in ((wpath, WF, wit), (lpath, LF, log)):
            if data:
                with open(path, 'w', newline='', encoding='utf-8') as fh:
                    w = csv.DictWriter(fh, fields, lineterminator='\n')
                    w.writeheader()
                    w.writerows(data[k] for k in sorted(data, key=lambda t: tuple(int(i) for i in t)))
    print(summary)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sp = ap.add_subparsers(dest='cmd', required=True)
    sp.add_parser('crops')
    rp = sp.add_parser('read')
    rp.add_argument('--limit', type=int, default=0)
    pp = sp.add_parser('reading')
    pp.add_argument('key')
    pp.add_argument('text')
    pp.add_argument('--reader', required=True)
    pp.add_argument('--illegible', action='store_true')
    sp.add_parser('decide')
    a = ap.parse_args(argv)
    if a.cmd == 'crops':
        make_crops()
    elif a.cmd == 'read':
        if a.limit <= 0:
            raise SystemExit('nothing is sent without --limit N')
        read_with_claude(a.limit)
    elif a.cmd == 'reading':
        path = os.path.relpath(crop_path(dict(zip(('edition', 'page', 'table', 'row', 'col'), a.key.split(':')))), ROOT)
        save_reading({'key': a.key, 'reader': a.reader, 'text': a.text, 'legible': str(not a.illegible),
                      'crop': path, 'date': datetime.date.today().isoformat(), 'cost_usd': ''})
    else:
        decide()
    return 0


if __name__ == '__main__':
    sys.exit(main())
