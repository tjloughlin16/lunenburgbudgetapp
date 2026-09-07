#!/usr/bin/env python3
"""Append one edition of the combined balance sheet -- and REFUSE it if it does not tie.

    python3 scripts/append_balance_sheet_year.py --rows staged-rows.csv \
                                                 --totals staged-totals.csv
    python3 scripts/append_balance_sheet_year.py --rows ... --totals ... --dry-run

WHY THIS EXISTS RATHER THAN "APPEND, THEN RUN THE VERIFIER"

Because that ordering has already failed here. A year that does not reconcile, once it is
in the file, is a row somebody can query; the verifier merely complains about it afterwards
and the complaint scrolls past. `PROVENANCE-special-revenue-read.md` states the rule as
**a year that does not tie is not written down** -- so the writing has to be what is
gated, not the reporting.

So this script merges the staged edition into a COPY, runs `verify_balance_sheet.py`
against the copy, and only replaces the real files if every check passes. On failure it
prints the verifier's output and writes nothing at all.

WHAT IT WILL NOT DO

It will not adjust a printed total, and it will not add an entry to `PRINTED_DEFECTS` for
you. A page that disagrees with itself is a finding about the town's report: it gets read
again first, and then recorded by hand in the verifier with the amount pinned exactly and
what is NOT established written next to it.

THE STAGED FILES ARE THE SAME SHAPE AS THE REAL ONES, header included:

    balance-sheet.csv          fy,edition,page_printed,page_pdf,section,line,fund,amount,
                               document,read_by
    printed-totals.csv         fy,edition,page_printed,page_pdf,total_row,fund,amount,quote

`page_printed` is the number printed at the FOOT of the page and `page_pdf` is the page's
index in the PDF. Both are recorded because they are not the same number and the catalogue
has been wrong about which it holds -- `annual_report_catalogue` gives FY2019's balance
sheet as page 28, which is the PDF index; the page itself prints 26. Reading the catalogue
figure as printed lands you on the general fund expenditure pie chart.
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
READ = os.path.join(DATA, 'balance-sheet.csv')
TOTALS = os.path.join(DATA, 'balance-sheet-printed-totals.csv')
VERIFIER = os.path.join(ROOT, 'scripts', 'verify_balance_sheet.py')


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as fh:
        r = csv.DictReader(fh)
        return r.fieldnames, list(r)


def write_csv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


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
    out = kept + staged
    out.sort(key=lambda r: (int(r['fy']),))
    return fields, out, ed, len(base) - len(kept)


def run_verifier(read_path, totals_path):
    """Run verify_balance_sheet against a specific pair of files. Returns (ok, output)."""
    spec = importlib.util.spec_from_file_location('verify_balance_sheet', VERIFIER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.READ, mod.TOTALS = read_path, totals_path
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
    ap.add_argument('--rows', required=True, help='staged figure rows for ONE edition')
    ap.add_argument('--totals', required=True, help='staged printed totals for that edition')
    ap.add_argument('--dry-run', action='store_true',
                    help='check and report, write nothing even on success')
    a = ap.parse_args()
    for p in (a.rows, a.totals, READ, TOTALS):
        if not os.path.exists(p):
            sys.exit(f'missing: {p}')

    rfields, rrows, ed, replaced = merged(READ, a.rows)
    tfields, trows, ted, treplaced = merged(TOTALS, a.totals)
    if ted != ed:
        sys.exit(f'the staged rows are {ed} and the staged totals are {ted}')

    tmp = tempfile.mkdtemp(prefix='balance-sheet-')
    tr = os.path.join(tmp, 'balance-sheet.csv')
    tt = os.path.join(tmp, 'balance-sheet-printed-totals.csv')
    write_csv(tr, rfields, rrows)
    write_csv(tt, tfields, trows)

    ok, out = run_verifier(tr, tt)
    print(out, end='')

    if not ok:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f'\nREFUSED. {ed} does not reconcile, so nothing was written.')
        print('Read the page again. Do not adjust a printed total to make it tie; if the')
        print("town's own page disagrees with itself, that is a finding and it belongs in")
        print('PRINTED_DEFECTS in verify_balance_sheet.py, pinned to the exact amount,')
        print('with what it does NOT establish written beside it.')
        sys.exit(1)

    if a.dry_run:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f'\n{ed} reconciles. --dry-run, so nothing was written.')
        return

    shutil.move(tr, READ)
    shutil.move(tt, TOTALS)
    shutil.rmtree(tmp, ignore_errors=True)
    note = f' (replacing {replaced} row(s) already held for it)' if replaced else ''
    print(f'\n{ed} reconciles on every check and was written{note}: '
          f'{len([r for r in rrows if r["edition"] == ed])} figures, '
          f'{len([r for r in trows if r["edition"] == ed])} printed totals.')


if __name__ == '__main__':
    main()
