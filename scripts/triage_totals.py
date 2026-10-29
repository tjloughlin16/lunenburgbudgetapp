#!/usr/bin/env python3
"""Why did a total not close? Classify each open check by its fingerprint. No model.

PLAN-ANNUAL-REPORT-PIPELINE.md section 7, layer 2 (TRIAGE). A total that does not close is one
of three things, and they must be told apart, because only one of them is about the town:

  misread        OCR got a cell wrong. Settled here when ONE correction of a kind OCR is
                 known to make closes the identity EXACTLY: a figure Textract could not parse
                 (`($21,00)`, two figures in one cell), `$` read as `8`, or a whole column
                 placed one row off its labels. A single-digit change is only a SUSPECT --
                 usually several cells could take it.
  grouping       OUR checker summed the wrong rows: the difference is exactly the rows just
                 before the block, or the first rows of it.
  printed_error  every cell reads cleanly and nothing above explains it: the page's own
                 arithmetic, possibly. Never settled here -- a second reader must agree
                 digit for digit (layer 3, RECONCILE).

`settled` means the arithmetic decided: the correction named makes the identity close and no
other correction of that kind does. Everything not settled goes to RECONCILE, with this
module's guess. Nothing here changes a figure: a correction is recorded BESIDE the value.

    python3 scripts/triage_totals.py "2000 Annual Town Report"
"""
from __future__ import annotations

import argparse
import copy
import re
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_totals as V  # noqa: E402

CLEAN = 95.0        # a cell read at this confidence or better counts as read cleanly
GROUPING_SHARE = Decimal('0.10')   # a miss past this share of the printed total is rows, not a digit


@dataclass
class Triage:
    triage: str                  # misread | grouping | printed_error | cannot_tell
    settled: bool
    how: str                     # what the fingerprint was
    corrections: list = field(default_factory=list)   # [ref, read as, would be]


def num(v):
    return V.money(v)


def rereadings(text):
    """Other readings of a cell, each a mistake OCR is known to make. [(why, value)]"""
    out = []
    t = text.strip()
    # a comma scanned for the decimal point: `($21,00)`
    m = re.fullmatch(r'(\(?)\$?\s*([\d,]+),(\d{2})(\)?)', t)
    if m:
        v, _, _ = V.parse(f'{m.group(1)}{m.group(2)}.{m.group(3)}{m.group(4)}')
        if v is not None:
            out.append(('a comma read for the decimal point', v))
    # a full stop scanned for a thousands comma: `$27,097.992`
    m = re.fullmatch(r'(\(?\$?\s*)(\d{1,3}(?:[.,]\d{3})+)(\)?)', t)
    if m and '.' in m.group(2):
        v, _, _ = V.parse(m.group(1) + m.group(2).replace('.', ',') + m.group(3))
        if v is not None:
            out.append(('a full stop read for a thousands comma', v))
    # `$` read as `8` or `S`: `8297,633`, `S1,250.00`
    m = re.fullmatch(r'(\(?)[8S]([\d,]+(?:\.\d+)?)(\)?)', t)
    if m:
        v, _, _ = V.parse(m.group(1) + m.group(2) + m.group(3))
        if v is not None:
            out.append(('`$` read as `' + t.lstrip('(')[0] + '`', v))
    # two figures in one cell: `108.67 $ 73.49`
    parts = [p for p in re.split(r'\s*\$\s*|\s+', t) if p]
    if len(parts) > 1:
        vals = [V.parse(p)[0] for p in parts]
        if all(v is not None for v in vals):
            out.append(('two figures read into one cell: ' + ' and '.join(map(num, vals)), sum(vals)))
    return out


def digit_swaps(text, value, need):
    """Single-digit changes to a cell's text that move its value by exactly `need`."""
    out = []
    for i, ch in enumerate(text):
        if not ch.isdigit():
            continue
        for d in '0123456789':
            if d == ch:
                continue
            v, _, _ = V.parse(text[:i] + d + text[i + 1:])
            if v is not None and v - value == need:
                out.append(text[:i] + d + text[i + 1:])
    return out


def cells_of(run, col):
    """[(ref, Cell)] down one column of a run of rows."""
    return [(r.ref, r.cells[col]) for r in run['rows'] if col in r.cells]


def shifted(run, col, by):
    """The run with one column's cells moved `by` rows against the labels."""
    new = copy.deepcopy(run)
    rows = new['rows']
    cells = [r.cells.pop(col, None) for r in rows]
    for i, c in enumerate(cells):
        j = i + by
        if c is not None and 0 <= j < len(rows):
            rows[j].cells[col] = c
    return new


def with_value(run, ref, col, value):
    """The run with one cell read as `value`."""
    new = copy.deepcopy(run)
    for r in new['rows']:
        if r.ref == ref:
            c = r.cells[col]
            c.value, c.unparsed = value, False
            c.places = max(0, -value.as_tuple().exponent)
    return new


def open_in(run, col):
    return sum(c.status == 'open' and c.col == col for c in V.check_stream(run))


def closes(run, check, before):
    """Does `check` close in this version of the run, leaving fewer open in its column than the
    `before` the change? A change that closes one total by opening another explains nothing."""
    after = [c for c in V.check_stream(run) if c.col == check.col]
    target = [c for c in after if c.ref == check.ref]
    return (bool(target) and target[0].status.startswith('closed')
            and sum(c.status == 'open' for c in after) < before)


def triage(check, run):
    diff = Decimal(check.difference.replace(',', ''))
    cells = dict(cells_of(run, check.col))
    items = set(check.items)
    before = open_in(run, check.col)

    # 1. one cell re-read the way OCR is known to misread it -- a figure that did not parse,
    # a comma for a point, `$` for `8` -- and the table re-checked with it: does this total
    # close, with fewer open in the column than before?
    fixes = []
    for ref, c in cells.items():
        for why, v in rereadings(c.text):
            if v != c.value and closes(with_value(run, ref, check.col, v), check, before):
                fixes.append([ref, c.text, num(v), why])
    if len(fixes) == 1:
        return Triage('misread', True, fixes[0][3], [fixes[0][:3]])

    # 2. the whole column one row off its labels
    # it must keep every total the column had, at least three of them, and close them all:
    # moving a column a row can make one or two totals close by coincidence
    had = [c for c in V.check_stream(run) if c.col == check.col]
    for by in (-1, 1):
        after = [c for c in V.check_stream(shifted(run, check.col, by)) if c.col == check.col]
        if (len(after) >= max(3, len(had)) and {c.ref for c in after} >= {c.ref for c in had}
                and all(c.status.startswith('closed') for c in after)):
            way = 'down' if by < 0 else 'up'
            return Triage('misread', True,
                          f'the column is one row {way} of its labels: shifted back, all '
                          f'{len(after)} totals in it close', [])

    # 4. our grouping: the rows just before the block, or the first rows of it
    order = [ref for ref, _ in cells_of(run, check.col)]
    if check.items and check.items[0] in order:
        start = order.index(check.items[0])
        s = Decimal(0)
        for ref in reversed(order[:start]):
            c = cells[ref]
            if c.value is None:
                break
            s += c.value
            if s == diff:
                return Triage('grouping', False, f'the difference is the rows {ref} to just before the block', [])
        s = Decimal(0)
        for ref in check.items[:-1]:
            s += cells[ref].value if ref in cells and cells[ref].value is not None else 0
            if -s == diff:
                return Triage('grouping', False, f'the difference is the block\'s first rows, to {ref}', [])

    # 5. one digit's worth: a suspect, and the count of cells that could explain it
    swaps = []
    for ref, c in cells.items():
        if (ref in items or ref == check.ref) and c.value is not None:
            need = -diff if ref == check.ref else diff
            swaps += [[ref, c.text, s] for s in digit_swaps(c.text, c.value, need)]
    if swaps:
        return Triage('misread', False, f'one digit changed would close it; {len(swaps)} ways to do that',
                      swaps[:6])

    if fixes:
        return Triage('misread', False, f'{len(fixes)} re-readings would close it', [f[:3] for f in fixes])
    # A MISS THAT IS A LARGE SHARE OF THE TOTAL ITSELF IS WHOLE ROWS, NOT A DIGIT. No single
    # digit change explains it (step 5 ran), so the block we summed is the wrong set of rows:
    # a grouping failure of OURS, never a claim that the town's arithmetic is wrong.
    # notes/HANDOFF-ANNUAL-REPORT-REVIEW.md: FY2011's debt schedules put 19 such misses in the
    # register as printed_error suspects, every one on a page a person had proved.
    printed = abs(Decimal(check.printed.replace(',', '')))
    if printed and abs(diff) > printed * GROUPING_SHARE:
        return Triage('grouping', False, f'the miss is {abs(diff) / printed:.0%} of the total itself: '
                      'whole rows, not a digit -- the block summed is the wrong one', [])
    low =[c for ref, c in cells.items() if (ref in items or ref == check.ref) and c.confidence < CLEAN]
    if check.unparsed or low:
        return Triage('cannot_tell', False, f'{len(low)} cells read below {CLEAN:.0f}% confidence'
                      + (f', {len(check.unparsed)} that did not parse' if check.unparsed else ''), [])
    return Triage('printed_error', False, f'every cell read at {CLEAN:.0f}% or better and no single '
                  'change or grouping explains it', [])


def run(stem, pages=None):
    checks, runs = V.validate(stem, pages)
    return [(c, triage(c, runs[c.stream])) for c in checks if c.status == 'open'], checks


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('stem')
    ap.add_argument('--pages', type=V.page_set)
    args = ap.parse_args(argv)
    found, checks = run(args.stem, args.pages)
    for c, t in found:
        print(f'{c.ref:<9} {c.label[:30]:<30} {c.column[:18]:<18} off {c.difference:>12}  '
              f'{t.triage}{" (settled)" if t.settled else ""}: {t.how}')
        for fix in t.corrections:
            print(f'{"":>12}{fix[0]}: {fix[1]!r} -> {fix[2]!r}')
    tally = {}
    for _, t in found:
        k = t.triage + (' settled' if t.settled else '')
        tally[k] = tally.get(k, 0) + 1
    print(f'{len(checks)} checks, {len(found)} open: ' + ', '.join(f'{n} {k}' for k, n in sorted(tally.items())))


if __name__ == '__main__':
    main()
