#!/usr/bin/env python3
"""Check one annual report after Textract: page order, then every printed total, then why each
open one is open. Log what is found; never stop on it.

PLAN-ANNUAL-REPORT-PIPELINE.md sections 7 and 8. TJ, 27 October 2026: *"basically after
processing, log the discrepancies from the analysis, and then we can review after the fact."*
So a report with open discrepancies is processed, with a count of what is open -- not stuck.

  1. page_integrity.py   is the scan complete and in order
  2. validate_totals.py  does every printed total close (VALIDATE)
  3. triage_totals.py    why not, by fingerprint (TRIAGE)

What is found goes into ONE review register, notes/generated/annual-report-discrepancies.csv:
one row per page problem and per total that did not close. INTERNAL, deliberately not under
sources/data, which is published: a `printed_error` here is a SUSPECT (rule 7), and a public
list of where the town's arithmetic might be wrong is an audit (rule 8). What survives review
reaches the public through document-defects.csv, as a finding. Rows are rewritten on every run from
what the checks find now; the columns a PERSON or the reconcile step fills -- `verdict`,
`decided_by`, `crop`, `note` -- are carried over by key and never overwritten. A row whose check
closes on a later run is dropped unless somebody has written a verdict on it.

A total marked `incomplete` reaches rows on a page we do not hold; it is counted, not
registered -- it says what was READ, not what the town printed.

    python3 scripts/report_review.py "2000 Annual Town Report"
    python3 scripts/report_review.py --all
    python3 scripts/report_review.py STEM --dry-run     # print, write nothing
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import archive_storage  # noqa: E402
import page_integrity  # noqa: E402
import triage_totals  # noqa: E402
import validate_totals  # noqa: E402

REGISTER = ROOT / 'notes' / 'generated' / 'annual-report-discrepancies.csv'
FIELDS = ['document', 'sha256', 'page', 'ref', 'check', 'column', 'printed', 'computed', 'difference',
          'found', 'triage', 'settled', 'how', 'correction',
          'verdict', 'decided_by', 'crop', 'note']
KEY = ('sha256', 'ref', 'check', 'column')
KEPT = ('verdict', 'decided_by', 'crop', 'note')      # a person's, or reconcile's; never rewritten


def document_name(sha, stem):
    for row in archive_storage.read_manifest().values():
        if row['sha256'] == sha:
            return row['key']
    return stem


def review(stem):
    """(register rows, summary) for one report."""
    rep = page_integrity.check(page_integrity.OUT / f'{stem}.lines.tsv')
    sha = rep.sha256 or ''
    doc = document_name(sha, stem)
    rows = []
    for f in rep.findings:
        if f.kind == 'note':
            continue
        rows.append({'document': doc, 'sha256': sha, 'page': ' '.join(map(str, f.pages)),
                     'ref': 'p' + '-'.join(map(str, f.pages)) if f.pages else '', 'check': f.check,
                     'column': '', 'found': f.kind, 'how': f.detail})
    found, checks = triage_totals.run(stem)
    for c, t in found:
        rows.append({'document': doc, 'sha256': sha, 'page': str(c.page), 'ref': c.ref, 'check': c.label,
                     'column': c.column, 'printed': c.printed, 'computed': c.computed,
                     'difference': c.difference, 'found': 'open total', 'triage': t.triage,
                     'settled': 'yes' if t.settled else '', 'how': t.how,
                     'correction': '; '.join(f'{ref} {old!r} -> {new!r}' for ref, old, new in t.corrections)})
    summary = {
        'document': doc, 'pages': len(rep.pdf_pages), 'pages_ok': rep.pages_ok,
        'page_issues': sum(f.kind == 'issue' for f in rep.findings),
        'totals': len(checks),
        **{s: sum(c.status == s for c in checks) for s in validate_totals.STATUSES},
        **{f'triage_{k}': sum(t.triage == k for _, t in found) for k in
           ('misread', 'grouping', 'printed_error', 'cannot_tell')},
        'settled': sum(t.settled for _, t in found),
    }
    return rows, summary


def merge(old, new, shas):
    """New rows for the reports just checked, carrying the KEPT columns; other reports' rows,
    and rows somebody has decided on, stay."""
    prior = {tuple(r[k] for k in KEY): r for r in old}
    out, seen = [], set()
    for r in new:
        key = tuple(r.get(k, '') for k in KEY)
        seen.add(key)
        keep = prior.get(key, {})
        out.append({f: keep.get(f, '') if f in KEPT else r.get(f, '') for f in FIELDS})
    for key, r in prior.items():
        if key in seen:
            continue
        if r['sha256'] not in shas or any(r.get(f) for f in ('verdict', 'decided_by')):
            out.append({f: r.get(f, '') for f in FIELDS})
    return out


def read_register():
    if not REGISTER.exists():
        return []
    with open(REGISTER, newline='') as f:
        return list(csv.DictReader(f))


def write_register(rows):
    rows.sort(key=lambda r: (r['document'], int(r['page'].split()[0]) if r['page'] else 0, r['ref'], r['column']))
    tmp = REGISTER.with_suffix('.tmp')
    with open(tmp, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, REGISTER)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('stems', nargs='*')
    ap.add_argument('--all', action='store_true', help='every Textract output')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args(argv)
    stems = args.stems or ([p.name.removesuffix('.lines.tsv') for p in sorted(page_integrity.OUT.glob('*.lines.tsv'))]
                           if args.all else ap.error('name a report, or --all'))
    new, shas = [], set()
    for stem in stems:
        rows, s = review(stem)
        new += rows
        shas.add(rows[0]['sha256'] if rows else '')
        print(f"{s['document']}: {s['pages']} pages, " + ('in order' if s['pages_ok'] else
              f"{s['page_issues']} PAGE ISSUE(S)") + f"; {s['totals']} totals checked: {s['closed']} closed, "
              f"{s['closed_rounded']} within printed rounding, {s['incomplete']} reach unread pages, "
              f"{s['open']} open -- {s['triage_misread']} misread ({s['settled']} settled), "
              f"{s['triage_grouping']} grouping, {s['triage_printed_error']} printed-error suspect, "
              f"{s['triage_cannot_tell']} cannot tell")
    if args.dry_run:
        return
    rows = merge(read_register(), new, shas)
    write_register(rows)
    print(f'{REGISTER.relative_to(ROOT)}: {len(rows)} rows')


if __name__ == '__main__':
    main()
