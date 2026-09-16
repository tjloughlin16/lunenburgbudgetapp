#!/usr/bin/env python3
"""What a budget DOCUMENT puts on the record about the budget being built -- the deficit
as stated, the cuts as named, the override as sized -- one file per document, so the
budget feed can show it the day the document appears.

    python3 scripts/write_document_budget_state.py --new --as-of 2026-09-16 --limit 3   # the refresh: documents watch_documents.py found today
    python3 scripts/write_document_budget_state.py sources/district-budget/docs/fy27-balanced-budget.pdf
    python3 scripts/write_document_budget_state.py --check
    python3 scripts/write_document_budget_state.py --status

TJ, 16 September 2026: "that's also true of new budget docs being produced by the town or
schools. anytime a new doc is 'found', we need to identify if it impacts the budget feed
and process it right then and there."

THE SAME SHAPE AS A MEETING'S BUDGET STATE, so the feed and the season builders read
it with the same code: statements, cuts, warnings, each with who (BY ROLE: "the
superintendent's budget book", "the town manager's message"), the fiscal year, and --
instead of a second of video -- the PAGE of the document. A document is a source in
its own right (rule 12), so the file also carries the document's address, filename and
sha256, and the extract is invalidated if the document's bytes change.

WHICH DOCUMENTS. Anything in the district's or the town's budget folders with a text
extract -- `sources/district-budget`, `sources/town-budget`, `sources/town-supplementary`.
The refresh (--new) reads only what watch_documents.py recorded as first seen on the
day, at most --limit of them, so a document is read once, the morning it appears.

WHAT IS EXTRACTED, and what is not, is the same line write_budget_state.py draws for a
meeting: the budget being BUILT and what goes to Town Meeting -- not a closeout, not a
transfer, not a grant. A figure is copied as PRINTED, never computed. A budget book that
prints a $1.2M gap yields one statement; one that prints a hundred line items yields
no statement, because a line item is not a gap.

`fiscal_year` is what puts a document into the right season. A document about FY27
found in 2026 lands in the FY27 replay; one about FY28 lands on the live board. The
season builders already key on the year, so nothing here routes by hand.
"""
import argparse
import csv
import datetime as dt
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from write_recording_minutes import NODE22, MODEL   # noqa: E402
import write_budget_state as BS                     # noqa: E402

OUT = os.path.join(ROOT, 'sources', 'data', 'budget-state', 'documents')
EVENTS = os.path.join(ROOT, 'sources', 'data', 'document-watch-events.csv')
FOLDERS = ('district-budget', 'town-budget', 'town-supplementary')
SCHEMA_VERSION = BS.SCHEMA_VERSION
MAX_CHARS = 180_000   # a budget book is long; the front of it is where the totals are

SYSTEM = BS.SYSTEM.replace(
    'You read machine captions of a Massachusetts town board meeting',
    'You read the extracted text of a budget DOCUMENT published by a Massachusetts town or its school district'
).replace(
    '- t is the caption line\'s seconds.',
    '- t is the PAGE NUMBER the figure is printed on, counted from the first page of the text (each page begins with a line "=== page N ===" where the extract marks pages; otherwise estimate from position and say so in the statement).'
).replace(
    'Figures are AS HEARD. Copy the number the captions carry; do not correct or infer.',
    'Figures are AS PRINTED. Copy the number the document prints; do not compute, sum or infer. A total the document prints is a statement; a line item is not.'
) + """
- WHO is the document's author by role: "the superintendent's budget book", "the town manager's budget message", "the finance committee's report", "a School Committee presentation". Never a person's name.
- A document is not a meeting: nothing here was 'voted' unless the document itself records a vote. Use 'announced' for a figure a document states, 'proposed' for a scenario it puts forward."""

# The document schema is the meeting schema with `t` meaning a page.
SCHEMA = json.loads(json.dumps(BS.SCHEMA))
for block in ('statements', 'cuts', 'warnings'):
    SCHEMA['properties'][block]['items']['properties']['t'] = {'type': 'integer', 'description': 'the page the figure is printed on'}


def sha256_of(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def read_csv(p):
    return list(csv.DictReader(open(p, encoding='utf-8'))) if os.path.exists(p) else []


DATE_IN_NAME = [
    (re.compile(r'(\d{4})-(\d{2})-(\d{2})'), lambda m: (int(m[1]), int(m[2]), int(m[3]))),
    (re.compile(r'\b(\d{1,2})-(\d{1,2})-(\d{2})\b'), lambda m: (2000 + int(m[3]), int(m[1]), int(m[2]))),
    (re.compile(r'\b(\d{1,2})-(\d{1,2})-(20\d{2})\b'), lambda m: (int(m[3]), int(m[1]), int(m[2]))),
]


def doc_date(doc, seen):
    """WHEN the document is FROM, which is what puts it in the right season -- not when we
    found it. "Balanced Budget Slides 3-23-26" is a March 2026 document about FY27 and
    belongs on the FY27 board, even if the crawler met it in September. Read off the
    label or filename where a date is written there; otherwise the day it was first
    seen, and the statements' own fiscal years do the rest."""
    for text in (doc.get('label') or '', os.path.basename(doc.get('local') or '')):
        for rx, f in DATE_IN_NAME:
            m = rx.search(text)
            if m:
                try:
                    y, mo, d = f(m)
                    return dt.date(y, mo, d).isoformat()
                except ValueError:
                    pass
    return seen


def documents():
    """Every budget document with a text extract, from the folders' own indexes."""
    out = []
    for f in FOLDERS:
        for r in read_csv(os.path.join(ROOT, 'sources', f, 'index.csv')):
            if r.get('text') and os.path.exists(os.path.join(ROOT, r['text'])) and r.get('local'):
                out.append(dict(r, folder=f))
    return out


def out_path(doc):
    base = os.path.splitext(os.path.basename(doc['local']))[0]
    return os.path.join(OUT, '%s--%s.json' % (doc['folder'], base))


def current(doc):
    p = out_path(doc)
    if not os.path.exists(p):
        return False
    d = json.load(open(p, encoding='utf-8'))
    loc = os.path.join(ROOT, doc['local'])
    return (os.path.exists(loc) and d.get('source', {}).get('sha256') == sha256_of(loc)
            and d.get('written', {}).get('schema') == SCHEMA_VERSION)


def write_one(doc, seen):
    if current(doc):
        return 'current'
    text = open(os.path.join(ROOT, doc['text']), encoding='utf-8', errors='replace').read()
    if len(text.strip()) < 200:
        return 'no usable text'
    body_text = text[:MAX_CHARS]
    prompt = ('Document: %s\nPublished by: %s\nFile: %s\n\nText (%d characters%s):\n\n%s'
              % (doc.get('label') or os.path.basename(doc['local']),
                 'the school district' if doc['folder'] == 'district-budget' else 'the town',
                 os.path.basename(doc['local']), len(text),
                 ', truncated to the first %d' % MAX_CHARS if len(text) > MAX_CHARS else '', body_text))
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    r = subprocess.run(['claude', '-p', '--tools', '', '--model', MODEL, '--system-prompt', SYSTEM,
                        '--json-schema', json.dumps(SCHEMA), '--output-format', 'json', '--max-budget-usd', '1'],
                       input=prompt, capture_output=True, text=True, env=env, timeout=900)
    if r.returncode != 0:
        raise SystemExit('claude failed on %s:\n%s' % (doc['local'], (r.stdout + r.stderr)[-2000:]))
    res = json.loads(r.stdout)
    body = res.get('structured_output') or res.get('result')
    if isinstance(body, str):
        body = json.loads(body)
    if not isinstance(body, dict) or 'statements' not in body:
        raise SystemExit('no structured output for %s' % doc['local'])
    loc = os.path.join(ROOT, doc['local'])
    os.makedirs(OUT, exist_ok=True)
    with open(out_path(doc), 'w', encoding='utf-8') as fh:
        json.dump(dict(
            warning=('EXTRACTED BY A LANGUAGE MODEL FROM A DOCUMENT\'S TEXT. Every figure is as printed '
                     'and every line carries the page it was read from, which is the record.'),
            # The fields the feed builder reads for a meeting, filled for a document: the
            # publisher stands as the board, the date it was first seen as the date, and
            # the document itself as the thing a citation opens.
            document=True,
            board_slug='documents', board=('Lunenburg Public Schools' if doc['folder'] == 'district-budget' else 'Town of Lunenburg') + ' — a budget document',
            meeting_date=doc_date(doc, seen), first_seen=seen, video_id=os.path.splitext(os.path.basename(doc['local']))[0],
            video_url='/docs/' + doc['local'].split('sources/', 1)[1],
            label=doc.get('label') or os.path.basename(doc['local']), upstream=doc.get('upstream', ''),
            source=dict(document=doc['local'], text=doc['text'], sha256=sha256_of(loc)),
            written=dict(by='scripts/write_document_budget_state.py', model=MODEL, schema=SCHEMA_VERSION,
                         at=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), cost_usd=res.get('total_cost_usd')),
            state=body), fh, indent=1, sort_keys=True)
        fh.write('\n')
    return 'written ($%.3f) — %d statements, %d cuts, %d warnings' % (
        res.get('total_cost_usd') or 0, len(body['statements']), len(body['cuts']), len(body.get('warnings') or []))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path', nargs='?', help='one document, by its sources/ path')
    ap.add_argument('--new', action='store_true', help='documents watch_documents.py first saw on --as-of')
    ap.add_argument('--as-of', default=dt.date.today().isoformat())
    ap.add_argument('--limit', type=int)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--status', action='store_true')
    a = ap.parse_args()
    docs = documents()
    if a.check:
        bad = 0
        for f in glob.glob(os.path.join(OUT, '*.json')):
            d = json.load(open(f, encoding='utf-8'))
            p = os.path.join(ROOT, d['source']['document'])
            if not os.path.exists(p) or sha256_of(p) != d['source']['sha256']:
                print('STALE', os.path.relpath(f, ROOT)); bad += 1
        print('%d document budget-state file(s), %d problem(s)' % (len(glob.glob(os.path.join(OUT, '*.json'))), bad))
        return 1 if bad else 0
    if a.status:
        have = sum(1 for d in docs if os.path.exists(out_path(d)))
        print('%d budget documents with text, %d with a budget state' % (len(docs), have))
        return 0
    seen_by_local = {e['local']: e['first_seen'] for e in read_csv(EVENTS)}
    if a.path:
        rel = os.path.relpath(os.path.abspath(a.path), ROOT)
        todo = [d for d in docs if d['local'] == rel]
        if not todo:
            raise SystemExit('not a budget document with a text extract: %s' % rel)
    elif a.new:
        fresh = {e['local'] for e in read_csv(EVENTS) if e['first_seen'] == a.as_of and e['folder'] in FOLDERS}
        todo = [d for d in docs if d['local'] in fresh]
    else:
        ap.error('name a document, or --new')
    todo = [d for d in todo if not current(d)]
    if a.limit:
        todo = todo[:a.limit]
    if not todo:
        print('nothing to read'); return 0
    for d in todo:
        print('%s  %s' % (d['local'], write_one(d, seen_by_local.get(d['local'], a.as_of))), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
