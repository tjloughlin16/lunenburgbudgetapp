#!/usr/bin/env python3
"""LOCATE: cells that two independent printed identities pin to ONE value. No model, no network.

    python3 scripts/locate_cell_misreads.py 1993 1995        # candidates -> build/cell-witness/candidates-<ed>.csv
    python3 scripts/locate_cell_misreads.py --all            # every edition 1986-2010

notes/process/ANNUAL-REPORT-CELL-WITNESS.md is the process. This is step 1 of four.

A cell is a CANDIDATE only when a failing ROW identity (begin + in - out = end, the debt
page's BALANCE = AMOUNT - PAYMENTS) and an OPEN COLUMN total both contain it and each,
solved for that cell alone, asks for the SAME value. A single failing identity is not enough:
a cell off in a long column is one of dozens; a cell off in its row AND its column, by amounts
that agree, is the cell. It is still only the arithmetic's proposal. Nothing is corrected
until an independent reader, shown the page and NOT the required value, reads the same digits
(witness_cell_crops.py), because Textract's own re-reading shares the error.

Setup mirrors read_report_tables.build() up to the checks, with the witnessed cells of
`witnessed-cells.csv` already applied, so a corrected cell stops being a candidate.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import page_integrity  # noqa: E402
import read_report_tables as R  # noqa: E402
import validate_totals as V  # noqa: E402

ROOT = R.ROOT
OUTDIR = os.path.join(ROOT, 'build', 'cell-witness')
FIELDS = ['edition', 'page', 'table', 'row', 'col', 'ref', 'family', 'column', 'row_label', 'textract_text',
          'textract_value', 'required_value', 'row_identity', 'column_identity', 'sha', 'bbox']


def setup(edition):
    d = R.folder(edition)
    ed = json.load(open(os.path.join(d, 'edition.json'), encoding='utf-8'))
    stem = ed['stem']
    tables = V.load(stem)
    m_rows = R.read_csv(os.path.join(d, 'map.csv'))
    R.apply_witness(d, tables)
    # the edition's opt-ins, exactly as read_report_tables.build() sets them
    R.OPTS.clear()
    R.OPTS.update(k for k, v in ed.items() if v is True)
    # the 1991-2010 close-out's opt-ins that change what the checks see (30 October 2026): the
    # row-identity tolerances, the debt pages exempt from the row total, figures re-placed by
    # position, figures split out of a label cell, and cells read as printed -- in build()'s order
    R.DEBT_ROW_TOL[0] = Decimal(str(ed.get('rounding_tolerance_usd', 0))) if 'debt_row_totals' in R.OPTS else Decimal(0)
    R.ROW_TOL[0] = Decimal(str(ed.get('rounding_tolerance_usd', 0))) if 'row_identity_tolerance' in R.OPTS else Decimal(0)
    R.DEBT_ROW_SKIP.clear()
    R.DEBT_ROW_SKIP.update(ed.get('debt_row_totals_skip') or ())
    R.apply_calendar_repairs(tables)
    if ed.get('rebuild_by_position'):
        R.rebuild_by_position(stem, tables, ed['rebuild_by_position'])
        R.apply_calendar_repairs(tables)
    if ed.get('label_figure_split'):
        R.split_label_figures(tables, ed['label_figure_split'])
    R.apply_witnessed_cells(d, tables)
    if ed.get('cell_readings'):
        import declared_identities
        declared_identities.apply_cell_readings(ed['cell_readings'], tables, V.parse)
    if 'stacked_pairs' in R.OPTS:
        tables = R.split_stacked_pairs(m_rows, tables)
    R.split_list_total_cells(m_rows, tables)
    vt = R.without_averages(m_rows, tables)
    if ed.get('unlabeled_subtotals') is True:
        vt = R.mark_unlabeled_subtotals(m_rows, vt, tuple(ed.get('unlabeled_subtotals_in') or ('report-appropriations',)))
    checks, _ = R.cell_checks(stem, vt, R.validator_names(m_rows, tables, ed.get('validator_drop_titles') is True),
                              tol=ed.get('rounding_tolerance_usd', 0),
                              tol_off_pages={int(m['page']) for m in m_rows if m['dataset'] == 'report-elections'})
    return d, ed, stem, tables, m_rows, checks


def row_solutions(family, names, cells, figcols=()):
    """[(col, required value, text)] for every cell of this row an UNFAILING-but-for-it identity
    would pin, one entry per failing identity."""
    out = []
    idents = list(R.IDENTITIES.get(family, []))
    if family == 'debt-repayment-schedule' and not names and len(figcols) >= 3:
        # THE YEAR HEADER IS IN THE PAGE LINES, NOT THE CELLS (1987 p40, 1988 p41): the columns
        # are unnamed, so they are named by POSITION for this identity only -- the last figure
        # column is the row's TOTAL, the ones before it its fiscal years. Locator only: nothing
        # read_report_tables grades moves
        names = {k: ('TOTAL' if k == max(figcols) else '%04d' % k) for k in figcols}
    if family == 'debt-repayment-schedule':
        # LOCATOR-ONLY identity, printed on the page: a row's TOTAL column is the sum of its
        # fiscal-year columns (named by the year). Not added to IDENTITIES: it would move rows
        # read_report_tables already grades, and this module only proposes.
        years = sorted(n for n in names.values() if re.fullmatch(r'\d{4}', n))
        if years and any(n == 'TOTAL' for n in names.values()):
            idents.append(('^TOTAL$', [(1, '^%s$' % y) for y in years]))
    for ident in idents:
        target, terms = ident[0], ident[1]
        opts = ident[2] if len(ident) > 2 else {}

        def col(rx):
            hits = [k for k, n in names.items() if re.search(rx, n, re.I)]
            return hits[0] if len(hits) == 1 else None
        if any(any(re.search(rx, n, re.I) for n in names.values()) for rx in opts.get('absent', ())):
            continue
        tk = col(target)
        ks = [(s, col(rx)) for s, rx in terms]
        if tk is None or any(k is None for _, k in ks) or tk in [k for _, k in ks]:
            continue
        need = [col(rx) for rx in opts.get('needs', ())]
        if any(k is None or cells.get(k) is None or cells[k].value is None for k in need):
            continue
        tc = cells.get(tk)
        if tc is None or tc.value is None:
            continue
        if any(cells.get(k) is not None and cells[k].unparsed for _, k in ks):
            continue
        got = sum((s * (cells[k].value if cells.get(k) is not None and cells[k].value is not None
                        else Decimal(0)) for s, k in ks), Decimal(0))
        if got == tc.value:
            continue
        what = '%s %s = %s (printed %s)' % (names[tk], '!=', ' '.join(('+' if s > 0 else '-') + names[k][:18]
                                                                    for s, k in ks), V.money(tc.value))
        out.append((tk, got, what))                              # the target column should read `got`
        for s, k in ks:
            c = cells.get(k)
            old = c.value if c is not None and c.value is not None else Decimal(0)
            out.append((k, old + (tc.value - got) / s, what))     # a term moves by delta / sign
    return out


def one_edit(a, b):
    """Do these digit strings differ by one substitution, insertion or deletion (or not at all)?
    The misreads OCR makes here -- `$`->`8`, `5`<->`6`, a dropped or extra digit -- are all one
    edit; a pin that needs two is two coincident identities, not a misread (1992 p36)."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    a, b = sorted((a, b), key=len)
    return any(b[:i] + b[i + 1:] == a for i in range(len(b)))


def locate(edition):
    d, ed, stem, tables, m_rows, checks = setup(edition)
    cell_of = {}
    for (p, t), rows in tables.items():
        for r in rows:
            for k, c in r.cells.items():
                cell_of[(r.ref, k)] = (r, c)
    prev_header = {}
    for m in m_rows:
        if (int(m['page']), int(m['table'])) in tables:
            _, _, n0, c0 = R.own_header(m, tables)
            prev_header['%s/%s' % (m['page'], m['table'])] = (n0, c0)
    found = {}
    for m in m_rows:
        if not m['dataset'] or (int(m['page']), int(m['table'])) not in tables:
            continue
        for rec in R.records(m, tables, checks, ed, prev_header):
            row_ref = rec['ref']
            cells = rec['cells']
            sols = row_solutions(m['family'], rec['names'], cells, rec['figcols'])
            for k, required, rtext in sols:
                if (row_ref, k) not in cell_of:
                    continue
                _, c = cell_of[(row_ref, k)]
                old = c.value if c.value is not None else Decimal(0)
                for status, ch, _tr in checks.get((row_ref, k), []):
                    if status != 'open':
                        continue
                    printed, computed = V.parse(ch.printed)[0], Decimal(ch.computed.replace(',', ''))
                    want = computed if ch.ref == row_ref else old + (printed - computed)
                    cents = re.search(r'\.\d{2}\)?$', c.text.strip())
                    shown = ('%.2f' % abs(want)) if cents else ('%d' % abs(want))
                    if want == required and want != old and one_edit(re.sub(r'\D', '', c.text), re.sub(r'\D', '', shown)):
                        found[(row_ref, k)] = dict(
                            edition=edition, page=rec['page'], table=rec['table'], row=rec['row'], col=k,
                            ref=row_ref, family=m['family'], column=rec['names'].get(k, ''),
                            row_label=rec['label'][:60], textract_text=c.text, textract_value=V.money(old),
                            required_value=V.money(want), row_identity=rtext,
                            column_identity='%s at %s `%s`: printed %s, rows sum %s' % (
                                ch.column, ch.ref, ch.label[:30], ch.printed, ch.computed))
    out = []
    docs = {}
    for key, row in sorted(found.items()):
        p = row['page']
        if p not in docs:
            docs[p] = page_integrity.document(stem, {p})[0]
        row['sha'] = docs[p] or ''
        row['bbox'] = ''
        if row['sha']:
            f = page_integrity.CACHE / row['sha'] / ('p%03d-tables.json' % p)
            if f.exists():
                from reconcile_totals import cell_boxes
                bb = cell_boxes(json.loads(f.read_text())['Blocks']).get((row['table'], row['row'], row['col']))
                row['bbox'] = json.dumps(bb) if bb else ''
        out.append(row)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('editions', nargs='*')
    ap.add_argument('--all', action='store_true')
    a = ap.parse_args(argv)
    eds = [str(y) for y in range(1986, 2011)] if a.all else a.editions
    os.makedirs(OUTDIR, exist_ok=True)
    total = 0
    for ed in eds:
        rows = locate(ed)
        total += len(rows)
        with open(os.path.join(OUTDIR, 'candidates-%s.csv' % ed), 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, FIELDS)
            w.writeheader()
            w.writerows(rows)
        print('%s: %d candidate(s)' % (ed, len(rows)))
        for r in rows:
            print('   p%s %s col%s `%s` Textract %r -> %s  [%s]' % (
                r['page'], r['ref'], r['col'], r['row_label'][:30], r['textract_text'], r['required_value'], r['column']))
    print('total %d' % total)
    return 0


if __name__ == '__main__':
    sys.exit(main())
