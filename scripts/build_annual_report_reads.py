#!/usr/bin/env python3
"""The pages read by an isolated run, as a CSV the page map can see.

    python3 scripts/build_annual_report_reads.py

WHY THIS EXISTS. `benchmark_ingest.py` reads a page in isolation and writes what it found
to `sources/data/annual-report-reads/fy<YY>-p<N>.json`. The backlog counts a page as read
when some CSV in `sources/data/` carries a YEAR column and a PAGE column naming it -- so a
JSON file, however well proved, moves nothing. TJ, on being shown a page that had been
read: *"which ingestion dash metric is this reducing"*. None of them, and that was the
honest answer.

So this flattens those reads into one CSV with `fy` and `page`, which is the only shape
the map reads. A page with ZERO rows is deliberately NOT written: a refusal is a correct
answer and it is not a reading, and counting it would move the number without moving the
archive -- the exact defect `notes/generated/AGENTIC-BACKLOG.md` warns about when it says
a page counts as read when any dataset cites it.
"""
import csv
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources', 'data', 'annual-report-reads')
OUT = os.path.join(ROOT, 'sources', 'data', 'annual-report-reads.csv')
FIELDS = ['fy', 'page', 'table', 'row_label', 'column', 'value', 'proved', 'read_by']


def main():
    out = []
    refused = []
    for f in sorted(glob.glob(os.path.join(SRC, '*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        rows = d.get('rows') or []
        if not rows:
            refused.append((d.get('fy'), d.get('page'), (d.get('note') or '')[:70]))
            continue
        cols = d.get('columns') or []
        for r in rows:
            vals = r.get('values') or []
            for i, v in enumerate(vals):
                out.append(dict(fy=d['fy'], page=d['page'], table=d.get('table', ''),
                                row_label=r.get('label', ''),
                                column=cols[i] if i < len(cols) else 'column %d' % (i + 1),
                                value=v, proved=(d.get('proved') or '')[:160],
                                read_by=d.get('read_by', '')))
    with open(OUT, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator='\n')
        w.writeheader()
        w.writerows(out)
    pages = len({(r['fy'], r['page']) for r in out})
    print('%d value(s) from %d page(s) -> %s' % (len(out), pages, os.path.relpath(OUT, ROOT)))
    for fy, page, why in refused:
        print('   fy%s p%s refused, not counted as read: %s' % (fy, page, why))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
