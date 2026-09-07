#!/usr/bin/env python3
"""Append one edition of the PEG Access statements -- and REFUSE it if it does not tie.

    python3 scripts/append_peg_access_year.py --rows staged-rows.csv \
                                              --totals staged-totals.csv \
                                              --identities staged-identities.csv
    python3 scripts/append_peg_access_year.py --rows ... --totals ... --identities ... \
                                              --dry-run

WHY THIS EXISTS RATHER THAN "APPEND, THEN RUN THE VERIFIER"

Because that ordering has already failed in this repository. A year that does not reconcile,
once it is in the file, is a row somebody can query; the verifier merely complains about it
afterwards and the complaint scrolls past. The rule is **a year that does not tie is not
written down** -- so the writing has to be what is gated, not the reporting.

So this script merges the staged edition into COPIES of all three files, runs
`verify_peg_access.py` against the copies, and only replaces the real files if every check
passes. On failure it prints the verifier's output and writes nothing at all.

WHAT IT WILL NOT DO

It will not adjust a printed total and it will not add an entry to `PRINTED_DEFECTS` for
you. A report that disagrees with itself is a finding about the town's document: it gets
read again first, and then recorded by hand in the verifier with the amount pinned exactly
and what is NOT established written next to it. FY2017's expense lines add to 450.01 more
than its own printed TOTAL and FY2020's two tables differ by 32 cents on one page; both are
recorded that way, not smoothed.

It will also not invent an identity. `peg-access-identities.csv` records the arithmetic the
STATEMENT states about itself, over the printed row ordinals, and it is transcribed from the
page like everything else -- because the arithmetic changes every few years and two rows of
FY2019's statement carry the identical printed label `Subtotal`. A statement with no
identity recorded is refused, and so is a printed row no identity reaches.

THE STAGED FILES ARE THE SAME SHAPE AS THE REAL ONES, header included:

    peg-access.csv                 fy,edition,page_printed,page_pdf,ordinal,line,amount,
                                   pct,quote,document,read_by
    peg-access-printed-totals.csv  fy,edition,page_printed,page_pdf,statement,ordinal,
                                   total_row,amount,pct,precision,quote,document
    peg-access-identities.csv      fy,edition,statement,identity,note

`page_printed` is the number printed at the FOOT of the page and `page_pdf` is the page's
index in the PDF. Both are recorded because they are not the same number and
`annual_report_catalogue` holds the PDF index: it gives FY2025's statement as page 64, and
the page itself prints 60. Read the foot; never trust an inferred offset.

`precision` is `cents` or `dollars`, transcribed from what the cell prints. FY2024 and
FY2025 print their statements in whole dollars while the line-item tables beside them are in
cents, and the cross-page check needs to know which it is looking at.
"""

import argparse
import csv
import importlib.util
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'sources', 'data')
READ = os.path.join(DATA, 'peg-access.csv')
TOTALS = os.path.join(DATA, 'peg-access-printed-totals.csv')
IDENTITIES = os.path.join(DATA, 'peg-access-identities.csv')
VERIFIER = os.path.join(ROOT, 'scripts', 'verify_peg_access.py')


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as fh:
        r = csv.DictReader(fh)
        return r.fieldnames, list(r)


def write_csv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def sort_key(r):
    return (int(r['fy']), r.get('statement', ''), int(r.get('ordinal', 0) or 0))


def merged(base_path, staged_path):
    """base + staged, with the staged edition replacing any copy already present."""
    fields, base = read_csv(base_path)
    sfields, staged = read_csv(staged_path)
    if sfields != fields:
        sys.exit(f'{os.path.basename(staged_path)} has columns {sfields}\n'
                 f'{os.path.basename(base_path)} has columns {fields}\n'
                 'They must match exactly.')
    eds = {r['edition'] for r in staged}
    if len(eds) != 1:
        sys.exit(f'stage ONE edition at a time; {staged_path} holds {sorted(eds) or "none"}')
    ed = eds.pop()
    kept = [r for r in base if r['edition'] != ed]
    out = sorted(kept + staged, key=sort_key)
    return fields, out, ed, len(base) - len(kept)


def run_verifier(read_path, totals_path, identities_path):
    """Run the verifier against a specific trio of files. Returns (ok, output)."""
    spec = importlib.util.spec_from_file_location('verify_peg_access', VERIFIER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.READ, mod.TOTALS, mod.IDENTITIES = read_path, totals_path, identities_path
    import io
    import contextlib
    buf = io.StringIO()
    ok = True
    with contextlib.redirect_stdout(buf):
        try:
            mod.main()
        except SystemExit as e:
            ok = not e.code
    return ok, buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rows', required=True, help='staged expense lines for ONE edition')
    ap.add_argument('--totals', required=True,
                    help='staged printed totals and statement rows for that edition')
    ap.add_argument('--identities', required=True,
                    help='the arithmetic that edition\'s statement states about itself')
    ap.add_argument('--dry-run', action='store_true',
                    help='check and report, write nothing even on success')
    a = ap.parse_args()
    for p in (a.rows, a.totals, a.identities, READ, TOTALS, IDENTITIES):
        if not os.path.exists(p):
            sys.exit(f'missing: {p}')

    rfields, rrows, ed, replaced = merged(READ, a.rows)
    tfields, trows, ted, _ = merged(TOTALS, a.totals)
    ifields, irows, ied, _ = merged(IDENTITIES, a.identities)
    if not (ted == ed and ied == ed):
        sys.exit(f'the staged files are for {ed}, {ted} and {ied}; stage one edition')

    tmp = tempfile.mkdtemp(prefix='peg-access-')
    tr = os.path.join(tmp, 'peg-access.csv')
    tt = os.path.join(tmp, 'peg-access-printed-totals.csv')
    ti = os.path.join(tmp, 'peg-access-identities.csv')
    write_csv(tr, rfields, rrows)
    write_csv(tt, tfields, trows)
    write_csv(ti, ifields, irows)

    ok, out = run_verifier(tr, tt, ti)
    print(out, end='')

    if not ok:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f'\nREFUSED. {ed} does not reconcile, so nothing was written.')
        print('Read the pages again. Do not adjust a printed figure to make it tie; if the')
        print("town's own report disagrees with itself, that is a finding and it belongs in")
        print('PRINTED_DEFECTS in verify_peg_access.py, pinned to the exact amount, with')
        print('what it does NOT establish written beside it.')
        sys.exit(1)

    if a.dry_run:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f'\n{ed} reconciles. --dry-run, so nothing was written.')
        return

    shutil.move(tr, READ)
    shutil.move(tt, TOTALS)
    shutil.move(ti, IDENTITIES)
    shutil.rmtree(tmp, ignore_errors=True)
    note = f' (replacing {replaced} row(s) already held for it)' if replaced else ''
    print(f'\n{ed} reconciles on every check and was written{note}: '
          f'{len([r for r in rrows if r["edition"] == ed])} expense lines, '
          f'{len([r for r in trows if r["edition"] == ed])} printed figures, '
          f'{len([r for r in irows if r["edition"] == ed])} identities.')


if __name__ == '__main__':
    main()
