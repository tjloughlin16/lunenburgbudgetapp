#!/usr/bin/env python3
"""Topic tags for the archive's documents, so a search for a subject finds the document
about it even when the document's text never says the word.

    python3 scripts/tag_document_affinity.py            # tag every untagged document
    python3 scripts/tag_document_affinity.py --check    # every tagged doc_key still exists

The pages were tagged by hand (`sources/data/search-affinity.csv`, 77 rows). The 273
archive documents are too many for that, and their labels are not enough -- "Slide Deck
from the SC Meeting 3/23/26" is about the FY27 budget cuts and says neither. So each
document's label and first page go to a model, forty at a time, and the tags come back
into the SAME CSV the page tags live in, one row per document, keyed by the doc_key the index gives the document's FIRST page, which is the row the
affinity table pins (the page suffix is dropped from the title there).

Tags are free text but short, in the town's words and ours, and never a figure. A
document already tagged is skipped, so this runs cheaply after new documents arrive.
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import build_search_index as B  # noqa: E402

CSV = B.AFFINITY_CSV
NODE22 = os.path.expanduser('~/.nvm/versions/node/v22.22.2/bin')
BATCH = 40

SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['docs'],
          'properties': {'docs': {'type': 'array', 'items': {
              'type': 'object', 'additionalProperties': False, 'required': ['i', 'tags'],
              'properties': {'i': {'type': 'integer'},
                             'tags': {'type': 'array', 'items': {'type': 'string'}, 'minItems': 3, 'maxItems': 8}}}}}}

SYSTEM = """For each document (a label and the start of its text), give 3 to 8 short topic tags a Lunenburg resident might search for: the subject (e.g. "school budget", "health insurance", "special education", "athletics", "state aid", "chapter 70", "free cash", "capital plan", "police budget", "annual report"), the fiscal year as "FY2027" if evident, the body ("school committee", "town manager", "finance committee", "DESE"), and plain words for what it is ("budget presentation", "cut list", "financial statements"). No figures. No tag longer than four words. Return only the JSON."""


def documents():
    """One entry per source document the index holds a first page for."""
    db = B.connect(B.DB, create=False)
    rows = db.execute("SELECT doc_key, title, file_key FROM search WHERE corpus='source' AND doc_key LIKE '%#p1' "
                      "OR (corpus='source' AND doc_key LIKE '%#p0')").fetchall()
    out = {}
    for r in rows:
        base = r['doc_key'].split('#')[0]
        # The key is the index's own key for the document's first page, which is the row
        # the affinity table pins; the page suffix is stripped from the title there.
        out.setdefault(base, {'doc_key': r['doc_key'], 'title': re.sub(r', page \d+$', '', r['title']), 'file_key': r['file_key']})
    return list(out.values())


def first_page(file_key, n=900):
    raw = open(os.path.join(ROOT, file_key), encoding='utf-8', errors='replace').read()
    body = re.sub(r'^===PAGE \d+===$', '', raw, flags=re.M)
    return re.sub(r'\s+', ' ', body).strip()[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rows = list(csv.DictReader(open(CSV, encoding='utf-8')))
    have = {r['doc_key'] for r in rows}
    docs = documents()
    if a.check:
        keys = {d['doc_key'] for d in docs}
        bad = [r['doc_key'] for r in rows if '#p' in r['doc_key'] and r['doc_key'] not in keys]
        print('%d document tag rows; %d name a document the index no longer holds' % (sum(1 for r in rows if '#p' in r['doc_key']), len(bad)))
        return 1 if bad else 0
    todo = [d for d in docs if d['doc_key'] not in have]
    print('%d documents, %d untagged' % (len(docs), len(todo)))
    env = dict(os.environ, PATH=NODE22 + os.pathsep + os.environ.get('PATH', ''))
    total = 0.0
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        prompt = '\n\n'.join('%d. LABEL: %s\nTEXT: %s' % (j, d['title'], first_page(d['file_key'])) for j, d in enumerate(batch))
        r = subprocess.run(['claude', '-p', '--tools', '', '--model', 'sonnet', '--system-prompt', SYSTEM,
                            '--json-schema', json.dumps(SCHEMA), '--output-format', 'json', '--max-budget-usd', '1'],
                           input=prompt, capture_output=True, text=True, env=env, timeout=600)
        if r.returncode != 0:
            raise SystemExit('claude failed on batch %d' % (i // BATCH))
        res = json.loads(r.stdout)
        body = res.get('structured_output') or res.get('result')
        if isinstance(body, str):
            body = json.loads(body)
        got = {x['i']: x['tags'] for x in body['docs']}
        with open(CSV, 'a', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            for j, d in enumerate(batch):
                tags = [t.strip() for t in got.get(j, []) if t.strip()]
                if tags:
                    w.writerow([d['doc_key'], '; '.join(dict.fromkeys(tags))])
        total += res.get('total_cost_usd') or 0
        print('  batch %d: %d tagged ($%.3f)' % (i // BATCH + 1, len(got), res.get('total_cost_usd') or 0), flush=True)
    print('done: $%.2f' % total)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
