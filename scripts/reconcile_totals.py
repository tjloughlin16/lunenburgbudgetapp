#!/usr/bin/env python3
"""A second reader for the totals TRIAGE could not settle: an image of the block, read by
`claude -p`, and the arithmetic deciding what that reading means.

PLAN-ANNUAL-REPORT-PIPELINE.md section 7, layer 3 (RECONCILE). The model is shown a crop of the
column and its total, IN READING ORIENTATION, and asked to transcribe the figures -- it is NOT
shown what Textract read, so the two readings are independent. Then, with no judgment at all:

  misread        the model's figures add up to the total it read, and differ from Textract's in
                 some cells: those cells were misread, and the corrections are recorded beside
                 the values (never over them)
  printed_error  the model's figures are Textract's, digit for digit, total included, and they
                 still do not add up: two independent readers agree and the page is wrong
  cannot_tell    anything else -- left for a person, with what the model read

THE AGENT PROPOSES, THE ARITHMETIC DECIDES. The model's own opinion of what went wrong is not
asked for. A printed error is copied to document-defects.csv only by a person (`--accept`),
because that register is published and speaks about the town.

The crop matters more than the model. A landscape table scanned onto a portrait page was
cropped twice by guessed coordinates and missed the column both times; so the crop is the
union of the cells' own boxes, and the page is turned until Textract's words run left to right.

COST: one `claude -p` call per total, with an image -- not the cheapest call. Nothing is sent
without `--limit N`; without it the crops are written and the calls listed. Quote it in the
week before a batch (CLAUDE.md, `claude -p` costs).

    python3 scripts/reconcile_totals.py "2000 Annual Town Report"            # crops + what it would send
    python3 scripts/reconcile_totals.py "2000 Annual Town Report" --only p86r15 --limit 1
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
import claude_lean
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import archive_storage  # noqa: E402
import page_integrity  # noqa: E402
import report_review  # noqa: E402
import triage_totals  # noqa: E402
import validate_totals as V  # noqa: E402

CROPS = ROOT / 'build' / 'annual-report-review' / 'crops'
MODEL = 'sonnet'
SCALE = 4            # 288 dpi: a cent's digits are several pixels high on these scans
PAD = 0.01           # page fraction around the cells
TIMEOUT = 300

SYSTEM = ('You transcribe figures from a scanned municipal report, exactly as printed. You never '
          'correct, round or compute anything: if a figure is printed wrong, transcribe it wrong. '
          'If a digit cannot be read, write ? in its place.')

SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['rows', 'total', 'legible'],
    'properties': {
        'rows': {'type': 'array', 'items': {
            'type': 'object', 'additionalProperties': False, 'required': ['label', 'printed'],
            'properties': {'label': {'type': 'string'}, 'printed': {'type': 'string'}}}},
        'total': {'type': 'string'},
        'legible': {'type': 'boolean'},
        'note': {'type': 'string'},
    },
}


def cache_blocks(sha, page):
    return json.loads((page_integrity.CACHE / sha / f'p{page:03d}-tables.json').read_text())['Blocks']


def cell_boxes(blocks):
    """{(table, row, col): BoundingBox} in Textract's table order, as the TSVs number them."""
    by_id = {b['Id']: b for b in blocks}
    out, t = {}, 0
    for b in blocks:
        if b['BlockType'] != 'TABLE':
            continue
        t += 1
        for rel in b.get('Relationships', []):
            for cid in rel['Ids'] if rel['Type'] == 'CHILD' else ():
                c = by_id.get(cid)
                if c and c['BlockType'] == 'CELL':
                    out[(t, c['RowIndex'], c['ColumnIndex'])] = c['Geometry']['BoundingBox']
    return out


def reading_turn(blocks):
    """Degrees to turn the page image (PIL, counter-clockwise) so its words run left to right:
    the median direction of every WORD's top edge, snapped to a quarter turn."""
    angles = []
    for b in blocks:
        if b['BlockType'] == 'WORD' and len(b['Geometry'].get('Polygon', [])) >= 2:
            p0, p1 = b['Geometry']['Polygon'][:2]
            angles.append(math.degrees(math.atan2(-(p1['Y'] - p0['Y']), p1['X'] - p0['X'])))
    if not angles:
        return 0
    return -round(statistics.median(angles) / 90) * 90 % 360


def crop(pdf, sha, check, run):
    """The block's cells -- labels, figures, total -- as one image the right way up."""
    import pypdfium2
    refs = set(check.items) | {check.ref}
    first = min(min(r.cells) for r in run['rows'])
    boxes = []
    for page in sorted({V._key(ref)[0] for ref in refs}):
        cells = cell_boxes(cache_blocks(sha, page))
        mine = [(V._key(ref)[1:], k) for ref in refs if V._key(ref)[0] == page for k in (check.col, first)]
        got = [cells[(t, r, k)] for (t, r), k in mine if (t, r, k) in cells]
        if got:
            boxes.append((page, got))
    images = []
    for page, got in boxes:
        left = max(0, min(b['Left'] for b in got) - PAD)
        top = max(0, min(b['Top'] for b in got) - PAD)
        right = min(1, max(b['Left'] + b['Width'] for b in got) + PAD)
        bottom = min(1, max(b['Top'] + b['Height'] for b in got) + PAD)
        img = pypdfium2.PdfDocument(str(pdf))[page - 1].render(scale=SCALE).to_pil()
        w, h = img.size
        img = img.crop((int(left * w), int(top * h), int(right * w), int(bottom * h)))
        images.append(img.rotate(reading_turn(cache_blocks(sha, page)), expand=True))
    if not images:
        return None
    from PIL import Image
    out = Image.new('RGB', (max(i.width for i in images), sum(i.height for i in images)), 'white')
    y = 0
    for i in images:                       # a block across a page break: one strip, in order
        out.paste(i, (0, y))
        y += i.height
    CROPS.mkdir(parents=True, exist_ok=True)
    path = CROPS / f'{sha[:12]}-{check.ref}-c{check.col}.png'
    out.save(path)
    return path


def ask(path, check, run, model):
    labels = {r.ref: r.label(V.figure_cols(run['rows'])) or '(no label)' for r in run['rows']}
    rows = '\n'.join(f'- {labels[ref]}' for ref in check.items)
    prompt = (f'Read the image {path}. It is part of a table from a scanned town report.\n\n'
              f'In the RIGHT-MOST full column of figures (headed "{check.column}" in the report; '
              'the heading is not in the image), transcribe the figure printed on each of '
              f'these {len(check.items)} rows, in this order:\n{rows}\n\n'
              f'Then transcribe the figure on the row "{labels[check.ref]}" as `total`. Write each '
              'figure exactly as printed, with its $ and commas and parentheses. A row with nothing '
              'printed in that column is an empty string. Set `legible` false if the image does not '
              'show those rows clearly.')
    r = claude_lean.run(['claude', '-p', '--model', model, '--tools', 'Read', '--allowedTools', 'Read',
                        '--system-prompt', SYSTEM, '--json-schema', json.dumps(SCHEMA),
                        '--output-format', 'json', '--max-budget-usd', '1'],
                       input=prompt, capture_output=True, text=True, timeout=TIMEOUT, add_dirs=[CROPS],
                       env={**os.environ, 'CLAUDE_CODE_ENTRYPOINT': 'reconcile_totals'})
    if r.returncode != 0:
        raise SystemExit(f'claude failed on {check.ref}:\n{(r.stdout + r.stderr)[-1500:]}')
    res = json.loads(r.stdout)
    body = res.get('structured_output') or res.get('result')
    return (json.loads(body) if isinstance(body, str) else body), res.get('total_cost_usd')


def decide(check, run, reading):
    """The arithmetic's verdict on a second reading: (verdict, note, corrections)."""
    cells = dict(triage_totals.cells_of(run, check.col))
    ours = [cells[ref].value if ref in cells else None for ref in check.items]
    theirs = [V.parse(r['printed'])[0] if r['printed'].strip() else Decimal(0) for r in reading['rows']]
    total = V.parse(reading['total'])[0]
    if not reading.get('legible') or len(theirs) != len(ours) or total is None or None in theirs:
        return 'cannot_tell', 'the second reader could not read every figure', []
    printed = cells[check.ref].value
    ours = [v if v is not None else Decimal(0) for v in ours]
    if sum(theirs) == total:
        fixes = [[ref, cells[ref].text, num] for ref, a, b, num in
                 zip(check.items, ours, theirs, (r['printed'] for r in reading['rows'])) if a != b]
        if total != printed:
            fixes.append([check.ref, cells[check.ref].text, reading['total']])
        if fixes:
            return 'misread', 'the second reading adds up; it differs from Textract in ' + \
                   ', '.join(f[0] for f in fixes), fixes
        return 'cannot_tell', 'the second reading adds up and matches Textract, which does not', []
    if theirs == ours and total == printed:
        return 'printed_error', (f'two readers agree digit for digit and the page does not add up: '
                                 f'the rows sum to {V.money(sum(ours))}, the page prints {V.money(printed)}'), []
    return 'cannot_tell', 'the second reading neither adds up nor matches Textract', []


DEFECTS = ROOT / 'sources' / 'data' / 'document-defects.csv'


def accept(stem, ref, who, body=''):
    """A person accepts a reconciled printed error: one row in document-defects.csv, which is
    published. Appended, re-read first, the file's own CRLF kept (CLAUDE.md: several authors)."""
    import csv
    from report_year import report_year
    rows = [r for r in report_review.read_register()
            if r['ref'] == ref and r['verdict'] == 'printed_error' and r['found'] == 'open total']
    if len(rows) != 1:
        sys.exit(f'{ref}: {len(rows)} reconciled printed errors in the register; accept needs exactly one')
    r = rows[0]
    if not r['decided_by'].startswith('reconcile'):
        sys.exit(f'{ref}: no second reading on record')
    year = report_year(Path(r['document']).name) or report_year(stem)
    with open(DEFECTS, newline='') as f:
        have = list(csv.DictReader(f))
    evidence = (f"PDF page {r['page']}, row {ref}, column {r['column']}: {r['note']}. "
                f"Read by Textract and again from an image (scripts/reconcile_totals.py); accepted by {who}")
    if any(d['document'] == r['document'] and ref in d['evidence'] for d in have):
        sys.exit(f'{ref}: already in {DEFECTS.relative_to(ROOT)}')
    with open(DEFECTS, 'a', newline='') as f:
        csv.writer(f).writerow([year.year if year else '', r['document'], body or r['check'].title(),
                                f"{r['check']} in the {r['column']} column prints {r['printed']}; the rows "
                                f"above it sum to {r['computed']}, a difference of {r['difference']}. "
                                'The figures are kept as printed.',
                                'measured: two independent readings of the page agree digit for digit',
                                evidence])
    print(f'{ref}: added to {DEFECTS.relative_to(ROOT)}')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('stem')
    ap.add_argument('--only', help='one total, by its row ref (p86r15)')
    ap.add_argument('--limit', type=int, default=0, help='send at most N to the model (default: none)')
    ap.add_argument('--model', default=MODEL)
    ap.add_argument('--accept', metavar='REF', help='a PERSON accepts a reconciled printed error: '
                    'copy it to document-defects.csv (published)')
    ap.add_argument('--by', default='', help='who accepted it, with --accept')
    ap.add_argument('--body', default='', help='the section of the report it is in, with --accept '
                    '(the page heading); default: the total\'s own label')
    args = ap.parse_args(argv)
    if args.accept:
        if not args.by:
            ap.error('--accept needs --by: a printed error reaches the public register only on a name')
        return accept(args.stem, args.accept, args.by, args.body)

    found, _ = triage_totals.run(args.stem)
    todo = [(c, t) for c, t in found if not t.settled and (not args.only or c.ref == args.only)]
    sha, _, _ = page_integrity.document(args.stem, set(page_integrity.read_lines(
        page_integrity.OUT / f'{args.stem}.lines.tsv')))
    key = report_review.document_name(sha, args.stem)
    pdf = Path(archive_storage.local_path(key))
    if not pdf.exists():
        sys.exit(f'the PDF is not on this disk: {pdf} (sync_archive.py --pull)')
    _, runs = V.validate(args.stem)
    register = report_review.read_register()
    index = {(r['sha256'], r['ref'], r['check'], r['column']): r for r in register}
    sent, spent = 0, 0.0
    for c, t in todo:
        run = runs[c.stream]
        path = crop(pdf, sha, c, run)
        row = index.get((sha, c.ref, c.label, c.column))
        line = f'{c.ref:<9} {c.label[:28]:<28} {c.column[:18]:<18} off {c.difference:>12}  {t.triage:<13}'
        if row is not None and path:
            row['crop'] = str(path.relative_to(ROOT))
        if row is not None and row.get('verdict'):
            print(f'{line} already decided: {row["verdict"]} ({row["decided_by"]})')
            continue
        if sent >= args.limit or path is None:
            print(f'{line} {"crop " + str(path.relative_to(ROOT)) if path else "NO CROP: no cell boxes"}')
            continue
        reading, cost = ask(path, c, run, args.model)
        sent += 1
        spent += cost or 0
        verdict, note, fixes = decide(c, run, reading)
        print(f'{line} -> {verdict}: {note} (${cost or 0:.3f})')
        if row is not None:
            row.update(verdict=verdict, decided_by=f'reconcile ({args.model}), arithmetic',
                       note=note + (('; read: ' + json.dumps(reading)) if verdict == 'cannot_tell' else ''),
                       correction=row['correction'] if not fixes else
                       '; '.join(f'{r} {a!r} -> {b!r}' for r, a, b in fixes))
    report_review.write_register(register)
    print(f'{len(todo)} unsettled; {sent} sent to {args.model}, ${spent:.3f} API-equivalent')


if __name__ == '__main__':
    main()
