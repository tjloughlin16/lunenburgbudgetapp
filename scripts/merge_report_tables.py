#!/usr/bin/env python3
"""Fold every per-edition folder under `sources/data/report-tables/` into the shared datasets.

    python3 scripts/merge_report_tables.py            # write
    python3 scripts/merge_report_tables.py --check    # fail if a shared file does not reproduce

WHY A MERGE AND NOT A WRITER PER REPORT. The 1959-2010 reports are read one agent per report,
several at once. Two agents appending to `report-appropriations.csv` at the same moment is the
shared-resource collision CLAUDE.md's "Several agents in one working tree" records costing
real rows. So a worker writes ONLY inside its own folder, `report-tables/<edition>/`, and this
one deterministic script is the only thing that touches the shared files. See
`sources/data/report-tables/README.md` for the layout.

THE INVARIANT, and how it is kept. A shared file is THE GENERATOR'S OWN ROWS, UNTOUCHED, then
every edition folder's rows for it, in folder order. "Untouched" is literal: the prefix is kept
as the raw text it was, line for line, never parsed and re-written, so FY2011-FY2025 rows are
byte-identical by construction and `--check` proves it by comparing bytes. A row belongs to an
edition folder when its `edition` column is the folder's edition key, or -- for the files with
no `edition` column -- its `document` column names the folder's PDF. FY-era rows carry
`FY2011`-style editions and other documents, so the two can never be confused.

GENERATORS OF THESE FILES call `with_editions(path, text)` on their own output before writing
or comparing, so re-running one does not drop the edition rows and its own `--check` still
holds. The hooked generators are listed in HOOKED below; any OTHER generator of a file named
here drops the rows when re-run, and `--check` (run by check_generated.py) then fails until
this is re-run. That is the self-healing half: a dropped row is loud, not silent.

`money-gaps.csv` is different: many sessions write it by hand. Gap candidates are APPENDED
there only if no row already has the same `what`, and the file is never rewritten.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
FOLDERS = os.path.join(DATA, 'report-tables')
GAPS = os.path.join(DATA, 'money-gaps.csv')

# The generators that call with_editions() on what they write. Kept here so the list of
# writers of a shared file is in one place.
HOOKED = {
    'annual-report-pages.csv': 'map_annual_report_pages.py',
    'treasurers-cash.csv': 'extract_treasurers_cash.py',
    'special-revenue-funds.csv': 'extract_special_revenue.py',
    'annual-report-receipts.csv': 'extract_annual_receipts.py',
    'annual-report-catalogue.csv': 'build_report_catalogue.py',
    'report-*.csv (the generic family)': 'extract_tables.py',
}

csv.field_size_limit(10 ** 9)


# EDITION FOLDERS NOT YET INTEGRATED. A batch of workers fills its folders while an integration
# pass merges an earlier batch, so a folder existing is not a folder being ready: one line per
# edition held out of every shared file until its own integration pass removes the line
# (`sources/data/report-tables/HELD`, `<edition>  <why>`; `#` starts a comment)
HELD = os.path.join(FOLDERS, 'HELD')


def held():
    """{edition key} the HELD register keeps out of the merge."""
    if not os.path.exists(HELD):
        return set()
    with open(HELD, encoding='utf-8') as fh:
        return {ln.split()[0] for ln in fh if ln.strip() and not ln.lstrip().startswith('#')}


def editions():
    """[(folder, edition.json)] in folder order -- the order rows are appended in. A folder named
    in HELD is left out."""
    out = []
    if not os.path.isdir(FOLDERS):
        return out
    hold = held()
    for name in sorted(os.listdir(FOLDERS)):
        if name in hold:
            continue
        f = os.path.join(FOLDERS, name, 'edition.json')
        if os.path.exists(f):
            with open(f, encoding='utf-8') as fh:
                out.append((os.path.join(FOLDERS, name), json.load(fh)))
    return out


def targets():
    """{shared file basename: [(edition.json, path of that edition's rows for it)]}."""
    out = {}
    for folder, ed in editions():
        rows = os.path.join(folder, 'rows')
        for name in sorted(os.listdir(rows)) if os.path.isdir(rows) else ():
            if name.endswith('.csv'):
                out.setdefault(name, []).append((ed, os.path.join(rows, name)))
        for own, shared in (('pages.csv', 'annual-report-pages.csv'),
                            ('catalogue.csv', 'annual-report-catalogue.csv')):
            f = os.path.join(folder, own)
            if os.path.exists(f):
                out.setdefault(shared, []).append((ed, f))
    return out


def belongs(row, eds):
    """Is this row one an edition folder put there?"""
    for ed in eds:
        if row.get('edition', None) is not None and row.get('edition') == ed['edition']:
            return True
        doc = row.get('document') or ''
        if doc and ed['stem'] in doc:
            return True
    return False


def _newline(text):
    first = text.split('\n', 1)[0]
    return '\r\n' if first.endswith('\r') else '\n'


def split_own(text, eds):
    """(raw prefix holding the generator's own rows, header fields). Edition rows must all sit
    after the generator's rows; anything else is a file somebody edited by hand, and refused."""
    lines = text.splitlines(keepends=True)
    if not lines:
        return '', None
    reader = csv.reader(iter(lines))
    header = next(reader)
    keep_upto = reader.line_num
    seen_edition = False
    for rec in reader:
        row = dict(zip(header, rec))
        if belongs(row, eds):
            seen_edition = True
            continue
        if seen_edition:
            raise SystemExit('an FY-era row follows an edition row at line %d: the file was edited '
                             'out of order; refusing to merge' % reader.line_num)
        keep_upto = reader.line_num
    return ''.join(lines[:keep_upto]), header


def serialize(rows, header, nl):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=header, lineterminator=nl, extrasaction='raise')
    for r in rows:
        w.writerow({h: r.get(h, '') for h in header})
    return buf.getvalue()


def edition_rows(basename):
    """The rows every edition folder holds for one shared file, in folder order."""
    out = []
    for ed, path in targets().get(basename, []):
        with open(path, newline='', encoding='utf-8') as fh:
            out += list(csv.DictReader(fh))
    return out


def with_editions(path, text):
    """A generator's own output for `path`, with the edition rows appended. Pure: reads the
    edition folders, writes nothing. A new dataset (no generator) passes text=''."""
    base = os.path.basename(path)
    eds = [ed for ed, _ in editions_for(base)]
    if not eds:
        return text
    rows = edition_rows(base)
    if not text:
        # A NEW DATASET: nothing but edition rows, in the worker's own column order.
        if not rows:
            return text
        header = list(rows[0].keys())
        buf = io.StringIO()
        csv.writer(buf, lineterminator='\n').writerow(header)
        return buf.getvalue() + serialize(rows, header, '\n')
    prefix, header = split_own(text, eds)
    extra = set(k for r in rows for k in r) - set(header)
    if extra:
        raise SystemExit('%s: edition rows carry columns the file does not: %s'
                         % (base, ', '.join(sorted(extra))))
    if prefix and not prefix.endswith(('\n', '\r')):
        prefix += _newline(text)
    return prefix + serialize(rows, header, _newline(text))


def editions_for(base):
    return targets().get(base, [])


def gap_candidates():
    out = []
    for folder, _ in editions():
        f = os.path.join(folder, 'gaps.csv')
        if os.path.exists(f):
            with open(f, newline='', encoding='utf-8') as fh:
                out += [r for r in csv.DictReader(fh)]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args(argv)
    stale, wrote = [], []
    for base in sorted(targets()):
        path = os.path.join(DATA, base)
        cur = open(path, newline='', encoding='utf-8').read() if os.path.exists(path) else ''
        new = with_editions(path, cur)
        if new == cur:
            continue
        if a.check:
            stale.append(base)
            continue
        tmp = path + '.merge-tmp'
        with open(tmp, 'w', newline='', encoding='utf-8') as fh:
            fh.write(new)
        os.replace(tmp, path)
        wrote.append(base)

    # money-gaps: append-only, by `what`, re-read immediately before writing.
    gaps = gap_candidates()
    with open(GAPS, newline='', encoding='utf-8') as fh:
        text = fh.read()
    have = {r.get('what', '') for r in csv.DictReader(io.StringIO(text))}
    missing = [g for g in gaps if g['what'] not in have]
    if missing and a.check:
        stale.append('money-gaps.csv (%d gap(s) not registered)' % len(missing))
    elif missing:
        header = next(csv.reader(io.StringIO(text)))
        nl = _newline(text)
        add = serialize([{k: g.get(k, '') for k in header} for g in missing], header, nl)
        with open(GAPS, 'a', newline='', encoding='utf-8') as fh:
            if not text.endswith(('\n', '\r')):
                fh.write(nl)
            fh.write(add)
        wrote.append('money-gaps.csv (+%d)' % len(missing))

    n_ed = len(editions())
    if a.check:
        if stale:
            print('STALE (run: python3 scripts/merge_report_tables.py):\n  ' + '\n  '.join(stale),
                  file=sys.stderr)
            return 1
        print('ok -- %d shared file(s) reproduce from %d edition folder(s); %d gap(s) registered'
              % (len(targets()), n_ed, len(gaps)))
        return 0
    print('merged %d edition folder(s): %s' % (n_ed, ', '.join(wrote) or 'nothing changed'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
