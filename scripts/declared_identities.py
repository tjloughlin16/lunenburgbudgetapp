#!/usr/bin/env python3
"""IDENTITIES A PAGE PRINTS THAT NO GENERIC CHECK CAN FIND, written down by eye and tested in code.

An `edition.json` opt-in for the calendar editions (`"declared_identities": [...]`, closing the
1971-1980 pages, 30 October 2026). The column validator reads one table at a time and one column
at a time; a balance sheet whose asset total sits at the foot of the RIGHT-hand group of a
side-by-side layout, a section subtotal printed in a second column, a schedule continued on the
next page, or a label that states its own rule (`50% Returned by State`) is out of its reach.

Each entry names, BY EYE, which printed figures an identity the page prints covers -- the same
kind of judgement `map.csv` records (rule 13b: a layout read and written down, never inferred).
What PROVES anything is still the arithmetic, done here on the figures as read:

    {"eq": "40/1/r26:p2 = 40/1/r7:p1 + 40/1/r14:p1 + 40/1/r25:p2",
     "why": "p40: the asset total $520,694.41 printed at the foot of the right group"}

A term is `[coef*]<page>/<table>/r<row>[-<row>][:p<panel>][.v<n>|.vL]`, with `+` or ` - `
between terms. A row RANGE sums every row of that table between the two (and of that panel,
where one is named) that prints a figure in the column; `.vL` (the default) is the row's last
figure; `.cN` is Textract's column N of each row as read, for a column with blank cells, where
the Nth figure of a row is not the Nth column. `#88,163.87` is a figure the page prints that no table cell holds, quoted from the
text read, as the map's `stated_total` is. Every row the identity names is then `checked` if it closes to the cent and `check
failed` if it does not -- an identity that fails is a statement about the page or our reading of
it, and it is published as one, never dropped: every row it names reads `check failed`, whatever
else closed on it. A closing identity changes only a `no check` row; a row that another check
already decided keeps its verdict and carries this note too -- unless the entry says
`replaces` (why that check read the wrong cells), and then a row it failed is re-decided by this
identity, with the failed note kept beside it.
"""
from __future__ import annotations

import re
from decimal import Decimal

TERM = re.compile(r'^(?:(?P<coef>-?[0-9.]+)\*)?(?P<page>\d+)/(?P<table>\d+)/r(?P<a>\d+)(?:-(?P<b>\d+))?'
                  r'(?::p(?P<panel>\d+))?(?:\.(?P<kind>[vc])(?P<col>\d+|L))?$')


def _terms(expr):
    out, sign = [], 1
    for tok in re.split(r'\s+([+-])\s+', ' + ' + expr.strip()):
        tok = tok.strip()
        if tok in ('+', '-'):
            sign = 1 if tok == '+' else -1
            continue
        if not tok:
            continue
        if tok.startswith('#'):
            # a figure the page prints where no table cell holds it, quoted from the text read
            # (the map's `stated_total` in this form)
            out.append((sign * Decimal(tok[1:].replace(',', '')), None))
            continue
        m = TERM.match(tok)
        if not m:
            raise SystemExit('declared_identities: cannot read the term %r' % tok)
        out.append((sign * Decimal(m['coef'] or '1'), m))
    return out


def _value(row, col):
    vals = [(i, row['v%d' % i]) for i in range(1, 9) if row.get('v%d' % i, '') != '']
    if col in (None, 'L'):
        return Decimal(vals[-1][1]) if vals else None
    v = row.get('v%s' % col, '')
    return Decimal(v) if v != '' else None


def apply(specs, dataset_rows, tables=None):
    """`specs` from edition.json; `dataset_rows` the emitted rows by target file, edited in place."""
    index = {}
    for rows in dataset_rows.values():
        for r in rows:
            if 'line_no' not in r or 'status' not in r:
                continue
            m = re.match(r'^t(\d+)r(\d+)$', str(r.get('line_no') or ''))
            if m:
                index.setdefault((int(r['page']), int(m[1]), int(m[2])), []).append(r)
    for spec in specs:
        lhs, rhs = spec['eq'].split('=')
        sides, used = [], []
        # A RATIO the page prints (`Debt Per Capita`, `Percentage Uncollected`): `a = b / c`, with
        # `scale` (100 for a percent) and `places`, the decimals the page rounds it to (`truncate`: cut off,
        # not rounded -- the 1979 Treasurer's measures)
        for expr in [lhs] + rhs.split(' / '):
            total = Decimal(0)
            for coef, m in _terms(expr):
                if m is None:
                    total += coef
                    continue
                p, t, a = int(m['page']), int(m['table']), int(m['a'])
                b = int(m['b'] or a)
                hit = 0
                if m['kind'] == 'c':
                    # `.cN`: Textract's column N of each row, as read after every repair -- for a
                    # column whose rows print blanks, where `vN` (the row's Nth figure) shifts
                    for rn in range(a, b + 1):
                        tr = next((x for x in (tables or {}).get((p, t), []) if x.row == rn), None)
                        cell = tr.cells.get(int(m['col'])) if tr is not None else None
                        if cell is None or cell.value is None:
                            continue
                        total += coef * cell.value
                        used.extend(index.get((p, t, rn), []))
                        hit += 1
                    if not hit:
                        raise SystemExit('declared_identities: %s names no cell with a figure (%s)'
                                         % (m.group(0), spec['eq']))
                    continue
                for rn in range(a, b + 1):
                    for r in index.get((p, t, rn), []):
                        if m['panel'] and str(r.get('panel') or '') != m['panel']:
                            continue
                        v = _value(r, m['col'])
                        if v is None:
                            continue
                        total += coef * v
                        used.append(r)
                        hit += 1
                if not hit:
                    raise SystemExit('declared_identities: %s names no row with a figure (%s)'
                                     % (m.group(0), spec['eq']))
            sides.append(total)
        if len(sides) == 3:
            q = Decimal(1).scaleb(-int(spec.get('places', 2)))
            sides = [sides[0], (sides[1] / sides[2] * Decimal(str(spec.get('scale', 1)))).quantize(q, rounding='ROUND_DOWN' if spec.get('truncate') else 'ROUND_HALF_UP')]
        ok = sides[0] == sides[1]
        # `tol`: the edition's dollar rounding tolerance (TJ, 29 Oct 2026), named per identity and
        # worded with the same countable phrase as the column checks (1995 p21: whole-dollar
        # highway accounts, a balance $1 off appropriated less expenditures)
        rounded = (not ok and spec.get('tol') is not None
                   and abs(sides[0] - sides[1]) <= Decimal(str(spec['tol'])))
        ok = ok or rounded
        note = ('DECLARED IDENTITY (%s): %s -- %s %s %s%s'
                % (spec['why'], spec['eq'], _money(sides[0]), '=' if ok else '!=', _money(sides[1]),
                   ' within $1 rounding tolerance (printed differs by $%s)' % _money(abs(sides[0] - sides[1]))
                   if rounded else '' if ok else ' (off %s)' % _money(sides[0] - sides[1])))
        for r in used:
            if spec.get('replaces') and r['status'] == 'check failed' and ok:
                # THE READER'S OWN CHECK WAS APPLIED TO THE WRONG CELLS (a header Textract set one
                # column off, a total cell holding two stacked figures), said in `replaces`; the
                # identity the page prints, on the right cells, decides instead. Its old note is kept
                r['status'] = 'checked'
                r['reconciliation'] = '%s ; REPLACES the check that failed (%s): %s' % (note, spec['replaces'], r['reconciliation'])
                continue
            if not ok and r['status'] != 'check failed':
                # an identity that fails fails every row it names, whatever else closed on it
                r['status'] = 'check failed'
                r['reconciliation'] = note + (' ; ' + r['reconciliation'] if r['reconciliation'] and
                                              r['reconciliation'] != 'no total printed' else '')
            elif r['status'] == 'no check':
                r['status'] = 'checked'
                r['reconciliation'] = note + (' ; ' + r['reconciliation'] if r['reconciliation'] and
                                              r['reconciliation'] != 'no total printed' else '')
            elif note not in r['reconciliation']:
                r['reconciliation'] = (r['reconciliation'] + ' ; ' if r['reconciliation'] else '') + note


def _money(d):
    return '{:,.2f}'.format(d)


def apply_cell_readings(readings, tables, parse):
    """A CELL TEXTRACT SEGMENTED WRONG, read as the page prints it (`edition.json`: `"cell_readings"`,
    an opt-in beside `witnessed-cells.csv`). Not a misread GLYPH -- the witness's job -- but a cell
    boundary: `Chapter | 76 8,183.45`, where the `76` ending the label line landed in the figure
    cell, or `17,416.75 5,022.00`, a section subtotal and the next line's item in one cell. Each entry
    names the cell, the exact Textract text (an error if the cache moved), the reading, and why --
    the evidence being the page's own layout, usually Textract's LINES read printing the figure on
    a line of its own. The cell keeps Textract's text and says so in `repaired_cells`."""
    for w in readings:
        p, t, r, c = (int(x) for x in w['cell'].split('/'))
        row = next((x for x in tables.get((p, t), []) if x.row == r), None)
        cell = row.cells.get(c) if row is not None else None
        if cell is None or cell.text != w['textract']:
            raise SystemExit('cell_readings: p%d t%d r%d c%d is not Textract `%s` any more' % (p, t, r, c, w['textract']))
        cell.value, cell.places, cell.unparsed = parse(w['read_as'])
        cell.repair = 'cell reading: Textract `%s`, read as `%s` -- %s' % (w['textract'], w['read_as'], w['why'])
