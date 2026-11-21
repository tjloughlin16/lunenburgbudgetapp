#!/usr/bin/env python3
"""CAPITAL REQUESTS MADE AND NEVER RANKED: every request a department made for a fiscal year that
the Capital Planning Committee's list for that year does not hold, FY2023-FY2027 (FY2028 where held).

    python3.11 scripts/build_capital_unranked.py           # validate, fill ranked_in, rewrite the CSV
    python3.11 scripts/build_capital_unranked.py --check   # fail if anything would change or fails

TJ, 20 November 2026: *"we need to show requests made that werent ranked FOR SURE. and if we can,
figure out why (minutes?! transcripts?!)"*.

sources/data/capital-requests-unranked.csv is READ BY HAND, one row per request, each with the
coordinate and raw text of the document that shows the request was made, and of the document
(or recording) that says why it went no further. The rows were read on 20-21 November 2026 from
the CPC minutes, the department and Town Manager decks, the CPC's own workbooks and the School
Committee's capital plans; reasons were looked for in the minutes and the caption finding aid.

What this script owns, and checks:
- `ranked_in`, DERIVED: every appearance of the same project on any year's ranked list
  (sources/data/capital-rankings.csv), joined by the town's project number, or by `same_as` where
  the row names the ranked request it was folded into or became. Never by a guess at a name.
- that a row's project number is NOT on its own cycle's ranked list (else it is not unranked);
- that every cited source file exists in the archive or the repository;
- that a reason is either quoted with a source, or is exactly `none recorded`;
- that a reason heard only in a recording says `captions (finding aid)`.

`kind` says what happened, in the documents' terms:
  dropped     on a department's or the committee's request list, absent from the ranked list
  withdrawn   the department or the committee is recorded taking it off before the ranking
  not-ranked  on the committee's working list and left unrated
  moved       requested for this year, recorded as pushed to a later year
  merged      split or folded into requests that WERE ranked (shown, never counted as unranked)
  out-year    presented in this cycle only as a later year's money: context, not an unranked request
  not-yet-ranked  FY2028: requested; the committee's list is not held or not yet voted
`ours` = yes where the row's identification is our match rather than printed (say why in notes).
"""
import argparse
import csv
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data', 'capital-requests-unranked.csv')
RANKED = os.path.join(ROOT, 'sources', 'data', 'capital-rankings.csv')
COLS = ['cycle_fy', 'money_fy', 'project_number', 'project', 'department', 'amount', 'kind', 'same_as',
        'request_source', 'request_where', 'request_quote', 'request_basis',
        'reason', 'reason_source', 'reason_where', 'reason_quote', 'reason_basis', 'ours', 'notes', 'ranked_in']
KINDS = {'dropped', 'withdrawn', 'not-ranked', 'moved', 'merged', 'out-year', 'not-yet-ranked'}
# Kinds that are a request made for that year and never ranked: what the pages draw as unranked.
UNRANKED = ('dropped', 'withdrawn', 'not-ranked', 'moved', 'not-yet-ranked')
REASON_BASIS = {'document', 'captions (finding aid)', 'none recorded', 'document (match ours)'}


def fail(msg):
    raise SystemExit('build_capital_unranked: ' + msg)


def exists(path):
    """A cited source: an archive path under sources/, a repository path, or a video address."""
    if not path:
        return True
    for p in path.split(';'):
        p = p.strip().split(' ')[0]
        if p.startswith('http') or not p:
            continue
        if not any(os.path.exists(os.path.join(ROOT, b, p)) for b in ('sources', '')):
            return False
    return True


def ranked_rows():
    return list(csv.DictReader(open(RANKED, encoding='utf-8')))


def key_of(r):
    return r['project_number'] or r['project']


def appearances(row, R):
    """Every ranked row that is this project: same town number, or named in same_as."""
    want = set()
    if row['project_number']:
        want.add(('*', row['project_number']))
    for ref in filter(None, (x.strip() for x in row['same_as'].split(';'))):
        fy, _, k = ref.partition(':')
        want.add((fy, k))
    out = []
    for r in R:
        k = key_of(r)
        if ('*', r['project_number']) in want or (r['fiscal_year'], k) in want:
            out.append(r)
    return sorted(out, key=lambda r: r['fiscal_year'])


def fmt(r):
    rank = ('rank %s of %s' % (r['cpc_rank'], r['cpc_ranked_of'])) if r['cpc_rank'] else 'unranked'
    return 'FY%s %s (%s)' % (r['fiscal_year'], rank, 'funded' if r['funded'] == 'yes' else 'not funded')


def build():
    R = ranked_rows()
    rows = list(csv.DictReader(open(DATA, encoding='utf-8')))
    if not rows or list(rows[0].keys()) != COLS:
        fail('columns must be exactly %s' % COLS)
    for i, row in enumerate(rows, 2):
        at = 'row %d (%s %s)' % (i, row['cycle_fy'], row['project'][:40])
        if row['kind'] not in KINDS:
            fail('%s: kind %r' % (at, row['kind']))
        if row['reason_basis'] not in REASON_BASIS:
            fail('%s: reason_basis %r' % (at, row['reason_basis']))
        if (row['reason_basis'] == 'none recorded') != (row['reason'] == 'none recorded'):
            fail('%s: a reason is quoted with a source or is exactly "none recorded"' % at)
        if row['reason_basis'] != 'none recorded' and not (row['reason_source'] and row['reason_quote']):
            fail('%s: a recorded reason needs its source and its quote' % at)
        if row['reason_basis'] == 'captions (finding aid)' and 'youtube' not in row['reason_source'] + row['reason_where']:
            fail('%s: a reason from captions is cited as the video at its timestamp' % at)
        if not row['request_source'] or not row['request_where']:
            fail('%s: no request coordinate' % at)
        for col in ('request_source', 'reason_source'):
            if not exists(row[col]):
                fail('%s: %s %r is not in the archive' % (at, col, row[col]))
        if row['ours'] not in ('yes', ''):
            fail('%s: ours is yes or empty' % at)
        same = [r for r in R if r['fiscal_year'] == row['cycle_fy'] and row['project_number']
                and r['project_number'] == row['project_number']]
        if same and row['kind'] != 'merged':
            fail('%s: %s IS on the FY%s ranked list' % (at, row['project_number'], row['cycle_fy']))
        for ref in filter(None, (x.strip() for x in row['same_as'].split(';'))):
            fy, _, k = ref.partition(':')
            if not any(r['fiscal_year'] == fy and key_of(r) == k for r in R):
                fail('%s: same_as %r matches no ranked row' % (at, ref))
        if row['kind'] == 'merged' and not row['same_as']:
            fail('%s: a merged request names the ranked requests it became' % at)
        row['ranked_in'] = '; '.join(fmt(r) for r in appearances(row, R)) or 'never ranked FY2023-FY2027'
    return rows


def render(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    out = render(build())
    cur = open(DATA, encoding='utf-8').read()
    if a.check:
        if cur != out:
            fail('%s is stale: run without --check' % os.path.relpath(DATA, ROOT))
        print('capital unranked: current, %d rows' % (out.count('\n') - 1))
        return
    if cur != out:
        open(DATA + '.tmp', 'w', encoding='utf-8').write(out)
        os.replace(DATA + '.tmp', DATA)
    print('wrote %s' % os.path.relpath(DATA, ROOT))


if __name__ == '__main__':
    main()
