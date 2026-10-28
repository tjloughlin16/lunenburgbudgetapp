#!/usr/bin/env python3
"""Does every total a page prints close on the rows above it? Textract cells, Decimal, no model.

PLAN-ANNUAL-REPORT-PIPELINE.md section 7, layer 1 (VALIDATE). A page states identities about
itself -- TOTAL rows, subtotals, a grand total of totals, a balance sheet whose assets equal its
liabilities and fund equity -- and an identity is the one check an OCR misread cannot survive
(rule 13b). So each is recomputed, to the cent, and recorded as closed or off by an exact amount.

GROUPING is the hard part, and getting it wrong looks exactly like a misread. A block runs from
its first row to its TOTAL; it may hold sub-blocks with their own totals, including an unlabeled
subtotal row; and it may CONTINUE onto the next page, whose table then starts with no header.
So each column keeps a STACK of what has not yet been summed into a total:

  - a data row pushes its figure;
  - a total pops the run of entries directly above it that sums to it, exactly, and pushes
    itself in their place -- so a total of totals (`TOTAL LIABILITIES/FUND EQUITY`, a `GRAND
    TOTAL`) closes on the totals, and a total below a subtotal closes on the subtotal;
  - a total that closes on nothing pops its natural block (everything since the last total)
    and pushes the PRINTED figure, so one bad total does not break every total after it;
  - an unlabeled row that equals the sum of two or more entries above it, in every column it
    fills, is a subtotal.

A page continues the previous page's table when it has the same number of columns and no
header of its own. Nothing is tolerated: a total closes or it is off, unless the items are
printed finer than the total (shares to 4 places summing to `1`), when the page itself shows
rounding and the allowance is half a unit per item.

Each open total gets the clues TRIAGE (layer 2) reads: the cells' confidence, cells in the
block that would not parse as a number, and the difference itself.

    python3 scripts/validate_totals.py "2000 Annual Town Report" --pages 67,86-88
    python3 scripts/validate_totals.py STEM --json
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
OUT = ROOT / 'build' / 'textract' / 'out'

NUMBER = re.compile(r'^-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?$')
DASH = {'-', '$-', '—', '–', '$—', '$–'}
GRAND = re.compile(r'\bgrand\b', re.I)
TOTAL = re.compile(r'\b(?:sub-?)?totals?\b', re.I)
ASSETS = re.compile(r'\btotal\s+assets\b', re.I)
KIND_STOP = {'total', 'totals', 'grand', 'subtotal', 'subtotals', 'fund', 'funds', 'department',
             'dept', 'with', 'from'}
LIAB_EQUITY = re.compile(r'\btotal\s+liabilit\w*\s*(?:/|and|&)\s*fund\s+(?:equity|balance)', re.I)


@dataclass
class Cell:
    text: str
    confidence: float
    value: Decimal | None = None     # None: blank, or not a number
    places: int = 0
    unparsed: bool = False           # text that looks like figures but did not read as one


@dataclass
class Row:
    page: int
    row: int
    cells: dict                      # col -> Cell
    table: int = 1

    @property
    def ref(self):
        """`p86r15`; `p84t2r5` for the second table on a page, whose rows restart at 1."""
        return f'p{self.page}' + (f't{self.table}' if self.table > 1 else '') + f'r{self.row}'

    def label(self, cols):
        return ' '.join(c.text for k, c in sorted(self.cells.items())
                        if c.text and c.value is None and not c.unparsed and k not in cols).strip()


@dataclass
class Entry:
    ref: str
    value: Decimal
    places: int
    total: bool = False              # a total or subtotal sitting on the stack
    grand: bool = False              # ...a GRAND total, which ends a section


@dataclass
class Check:
    page: int
    ref: str                         # the total's row
    label: str
    column: str
    printed: str
    computed: str
    difference: str
    status: str                      # closed | closed_rounded | open | incomplete
    items: list = field(default_factory=list)       # refs summed
    grouping: str = ''               # natural | run | of_totals | balance
    low_confidence: list = field(default_factory=list)
    unparsed: list = field(default_factory=list)    # [ref, text] in the block
    col: int = 0                     # Textract's column index
    stream: int = 0                  # which run of rows (validate's second return value)


def parse(text):
    """'$ 1,234.56' -> (Decimal, places). '(86,070.12)' is negative. '$ -' is zero."""
    t = text.replace(' ', '').replace('$', '', 1) if text.strip() not in DASH else '-'
    if t in ('-', '—', '–'):
        return Decimal(0), 0, False
    if not t:
        return None, 0, False
    neg = t.startswith('(') and t.endswith(')')
    t = t.strip('()')
    if NUMBER.match(t):
        v = Decimal(t.replace(',', ''))
        places = len(t.split('.')[1]) if '.' in t else 0
        return (-v if neg else v), places, False
    return None, 0, bool(re.search(r'\d[\d,.]*\d', t)) and not re.search(r'[A-Za-z]{2}', t)


def word_confidence(stem, pages):
    """{(page, table, row, col): the lowest confidence of the WORDS in the cell}. The cells TSV
    carries Textract's confidence in the CELL -- its boundaries -- which runs 85-93% on a clean
    scan; whether the DIGITS were read well is on the words, in the cached response."""
    import json
    import page_integrity
    sha, _, _ = page_integrity.document(stem, pages)
    out = {}
    if sha is None:
        return out
    for f in sorted((page_integrity.CACHE / sha).glob('p*-tables.json')):
        page = int(f.name[1:4])
        if page not in pages:
            continue
        blocks = json.loads(f.read_text())['Blocks']
        by_id = {b['Id']: b for b in blocks}
        t = 0
        for b in blocks:
            if b['BlockType'] != 'TABLE':
                continue
            t += 1
            for rel in b.get('Relationships', []):
                for cid in rel['Ids'] if rel['Type'] == 'CHILD' else ():
                    c = by_id.get(cid)
                    if not c or c['BlockType'] != 'CELL':
                        continue
                    words = [by_id[w]['Confidence'] for r in c.get('Relationships', [])
                             if r['Type'] == 'CHILD' for w in r['Ids']
                             if w in by_id and by_id[w]['BlockType'] == 'WORD']
                    if words:
                        out[(page, t, c['RowIndex'], c['ColumnIndex'])] = min(words)
    return out


def load(stem, pages=None):
    """{(page, table): [Row]} from the Textract cells, each with its words' confidence."""
    tables = {}
    with open(OUT / f'{stem}.cells.tsv', newline='') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            p = int(r['page'])
            if pages and p not in pages:
                continue
            v, places, bad = parse(r['text'])
            rows = tables.setdefault((p, int(r['table'])), {})
            row = rows.setdefault(int(r['row']), Row(p, int(r['row']), {}, int(r['table'])))
            row.cells[int(r['col'])] = Cell(r['text'], float(r['confidence']), v, places, bad)
    words = word_confidence(stem, {p for p, _ in tables})
    for (p, t), rows in tables.items():
        for row in rows.values():
            for k, c in row.cells.items():
                c.confidence = words.get((p, t, row.row, k), c.confidence)
    return {k: [rows[i] for i in sorted(rows)] for k, rows in sorted(tables.items())}


def is_figure(c):
    return c.value is not None and ('.' in c.text or '$' in c.text or ',' in c.text or c.text.strip() in DASH)


def split_header(rows):
    """Rows before the first one holding a figure are the header -- less any rows just above
    it that carry only a row label (`MASS WATER POLLUTION`, `PRINCIPAL`): those are the first
    rows of the body, and a figure Textract placed a row off belongs to one of them."""
    for i, r in enumerate(rows):
        if any(is_figure(c) for c in r.cells.values()):
            first = min(min(r.cells) for r in rows)
            while i > 0 and not any(c.text for k, c in rows[i - 1].cells.items() if k != first):
                i -= 1
            return rows[:i], rows[i:]
    return rows, []


def streams(tables, read):
    """Tables joined into the runs they print: a table with the same column count as the one
    before it, on the same page or the next, CONTINUES it when it has no header of its own or
    repeats the same header. Textract splits one long list into several tables on a page.

    `may_begin_earlier`: the run's first table has no header, or the page before it was not
    read -- so its first block may hold rows we do not have."""
    out, last = [], None
    for (page, t), rows in tables.items():
        head, body = split_header(rows)
        ncols = max((max(r.cells) for r in rows), default=0)
        names = {}
        for r in head:
            for k, c in r.cells.items():
                if c.text:
                    names[k] = (names.get(k, '') + ' ' + c.text).strip()
        adjacent = last and (page == last['page'] and t == last['table'] + 1
                             or page == last['page'] + 1 and t == 1)
        if adjacent and last['ncols'] == ncols and (not names or names == last['names']):
            last['rows'] += body
            last['pages'].append(page)
            last['page'], last['table'] = page, t
        else:
            last = {'page': page, 'pages': [page], 'table': t, 'ncols': ncols, 'rows': body,
                    'names': names,
                    'may_begin_earlier': not names or (page > 1 and page - 1 not in read)}
            out.append(last)
    return out


def figure_cols(rows):
    """Columns holding figures: label columns are the rest."""
    counts = {}
    for r in rows:
        for k, c in r.cells.items():
            if c.value is not None:
                counts[k] = counts.get(k, 0) + 1
    return {k for k, n in counts.items() if n >= 2}


def money(v):
    return f'{v:,.2f}' if v == v.quantize(Decimal('0.01')) else f'{v}'


def close(stack, printed, places, n_min=1):
    """The longest run of entries directly above that sums to `printed` (index into `stack`). Exactly, or within
    half a unit per item when the items are printed finer than the total."""
    s, best = Decimal(0), None
    for i in range(len(stack) - 1, -1, -1):
        s += stack[i].value
        n = len(stack) - i
        if n < n_min:
            continue
        finer = max(e.places for e in stack[i:])
        if s == printed:
            best = (i, 'closed')
        elif finer > places and abs(s - printed) <= n * Decimal(5) / Decimal(10) ** (finer + 1) and not best:
            best = (i, 'closed_rounded')
    return best


def first_close(stack, c):
    """Where the block for a printed total starts in `stack`, (index, status), or None. The
    block since the last total when that closes; a longer run only adds zeros to it."""
    nat = natural(stack)
    hit = close(stack, c.value, c.places)
    if hit and hit[0] < nat and close(stack[nat:], c.value, c.places):
        hit = (nat, close(stack[nat:], c.value, c.places)[1])
    return hit


def natural(stack):
    """Everything since the last total on the stack."""
    i = len(stack)
    while i > 0 and not stack[i - 1].total:
        i -= 1
    return i


def kind_words(label):
    """What a total is a total OF: `GRAND TOTAL PRINCIPAL` -> {'principal'}."""
    return set(re.findall(r'[a-z]{4,}', label.lower())) - KIND_STOP


def read_pages(stem):
    """Every page Textract returned text for -- a page with no table is still a page read."""
    with open(OUT / f'{stem}.lines.tsv', newline='') as f:
        return {int(r['page']) for r in csv.DictReader(f, delimiter='\t')}


def validate(stem, pages=None):
    """Every check in the report, and the runs of rows they were made on (TRIAGE re-checks a
    run with one change applied)."""
    runs = streams(load(stem, pages), read_pages(stem))
    checks = []
    for i, st in enumerate(runs):
        prev = runs[i - 1] if i else None
        # what the table before left unsummed, column by HEADER (a page with an extra
        # annotation column shifts every position), if it is adjacent and shares two headers:
        # a grand total can sum a statement Textract returned as separate tables, across pages
        shared = prev and len(set(prev['names'].values()) & set(st['names'].values())) >= 2
        st['carry'] = prev['residue'] if shared and st['pages'][0] - prev['page'] <= 1 else {}
        st['carried_partial'] = bool(st['carry']) and (prev['may_begin_earlier'] or prev.get('carried_partial'))
        for c in check_stream(st):
            c.stream = i
            checks.append(c)
    return checks, runs


def check_stream(st):
    checks = []
    rows = st['rows']
    cols = figure_cols(rows)
    stacks = {k: [] for k in cols}
    carried = st.get('carry', {})
    carry = {k: list(carried.get(st['names'].get(k), [])) for k in cols}
    seen = {k: [] for k in cols}          # every data row, (label, Entry), summed or not
    unparsed = {k: [] for k in cols}
    totals_by_label = []
    for r in rows:
        label = r.label(cols)
        figs = {k: c for k, c in r.cells.items() if k in cols and c.value is not None}
        for k, c in r.cells.items():
            if k in cols and c.unparsed:
                unparsed[k].append([r.ref, c.text])
        if not figs:
            continue
        is_total = bool(TOTAL.search(label))
        if not is_total and not label:
            # an unlabeled row is a subtotal if every non-zero figure in it closes on 2+
            # entries; its zeros say nothing either way and are not checked
            live = {k: c for k, c in figs.items() if c.value != 0}
            if live and all(close(stacks[k], c.value, c.places, n_min=2) for k, c in live.items()):
                is_total, figs = True, live
        if not is_total:
            for k, c in figs.items():
                stacks[k].append(Entry(r.ref, c.value, c.places))
                seen[k].append((label, stacks[k][-1]))
            continue
        totals_by_label.append((label, r, figs))
        found = {k: first_close(stacks[k], c) for k, c in figs.items()}
        # a total row covers the same rows in every column: where two or more columns agree
        # where the block starts, that is the block for the rest of the row too
        starts = Counter(stacks[k][h[0]].ref for k, h in found.items() if h and h[0] < len(stacks[k]))
        span = next((ref for ref, n in starts.most_common(1) if n >= 2), None)
        for k, c in figs.items():
            stack = stacks[k]
            nat = natural(stack)
            hit = found[k]
            lo = hit[0] if hit else nat
            if not hit and span:
                lo = next((i for i, e in enumerate(stack) if _key(e.ref) >= _key(span)), len(stack))
                if lo == len(stack):
                    # nothing printed in this column over the block's rows: the page states
                    # no sum here to check (`BALANCE TO REVENUE` printed on the total only)
                    stack.append(Entry(r.ref, c.value, c.places, total=True))
                    continue
            block = stack[lo:]
            by_kind = across = None
            if not hit and GRAND.search(label):
                # a GRAND total's block is everything since the last grand total -- in this
                # table and, if there is none, the ones it continues
                lo = next((i + 1 for i in range(len(stack) - 1, -1, -1) if stack[i].grand), 0)
                block = (carry.get(k, []) if lo == 0 else []) + stack[lo:]
            if not hit and carry.get(k):
                # a total that runs back into the table before
                joined = carry[k] + stack
                h = close(joined, c.value, c.places)
                if h and h[0] < len(carry[k]):
                    across, hit = joined[h[0]:], h
                    carry[k] = carry[k][:h[0]]
                    lo, block = 0, list(stack)
            if not hit and (want := kind_words(label)):
                # a total of one KIND of row, wherever it sits: `GRAND TOTAL PRINCIPAL`
                # is every PRINCIPAL row, each already inside its own loan's total
                kind = [e for l, e in seen[k] if want & kind_words(l)]
                if len(kind) >= 2 and sum(e.value for e in kind) == c.value:
                    by_kind = kind
            computed = sum((e.value for e in by_kind or across or block), Decimal(0))
            if by_kind:
                status = 'closed'
            elif not block and c.value == 0:
                status = 'closed'
            elif hit:
                status = hit[1]
            elif ((st['may_begin_earlier'] or st.get('carried_partial'))
                  and (lo == 0 or not block or all(e.total for e in block))):
                # the block reaches back past the first row we hold
                status = 'incomplete'
            else:
                status = 'open'
            grouping = ('by_kind' if by_kind else 'across_tables' if across else
                        'empty' if not block else 'natural' if lo == nat else
                        'of_totals' if all(e.total for e in block) else 'run')
            block_refs = {e.ref for e in block}
            low = [[ref, cc.text, cc.confidence] for ref, cc in
                   ((rr.ref, rr.cells.get(k)) for rr in rows if rr.ref in block_refs | {r.ref})
                   if cc and cc.confidence < 90]
            checks.append(Check(
                page=r.page, ref=r.ref, label=label or '(unlabeled subtotal)',
                column=st['names'].get(k, f'col {k}'), printed=money(c.value),
                computed=money(computed), difference=money(c.value - computed), status=status,
                items=[e.ref for e in by_kind or across or block], grouping=grouping, low_confidence=low, col=k,
                unparsed=[u for u in unparsed[k] if u[0] in block_refs or not block_refs
                          or _between(u[0], block, r)]))
            if not by_kind:
                del stack[lo:]
            stack.append(Entry(r.ref, c.value, c.places, total=True, grand=bool(GRAND.search(label))))
    # a balance sheet: total assets equal total liabilities and fund equity, column by column
    assets = [(r, f) for l, r, f in totals_by_label if ASSETS.search(l)]
    equity = [(r, f) for l, r, f in totals_by_label if LIAB_EQUITY.search(l)]
    if assets and equity:
        (ra, fa), (re_, fe) = assets[-1], equity[-1]
        for k in sorted(set(fa) | set(fe)):
            a, e = fa.get(k), fe.get(k)
            if a is None or e is None:
                continue
            checks.append(Check(
                page=re_.page, ref=re_.ref, label='assets = liabilities + fund equity',
                column=st['names'].get(k, f'col {k}'), printed=money(e.value), computed=money(a.value),
                difference=money(e.value - a.value),
                status='closed' if a.value == e.value else 'open', items=[ra.ref], grouping='balance',
                col=k))
    st['residue'] = {st['names'].get(k, f'col {k}'): carry.get(k, []) + stacks.get(k, []) for k in cols}
    return checks


def _key(ref):
    """`p84t2r5` -> (84, 2, 5): page, table, row -- reading order."""
    m = re.fullmatch(r'p(\d+)(?:t(\d+))?r(\d+)', ref)
    return int(m.group(1)), int(m.group(2) or 1), int(m.group(3))


def _between(ref, block, total_row):
    """Is an unparsed cell inside the block's span of rows?"""
    if not block:
        return False
    return _key(block[0].ref) <= _key(ref) <= _key(total_row.ref)


STATUSES = ('closed', 'closed_rounded', 'incomplete', 'open')


def page_set(spec):
    out = set()
    for part in spec.split(','):
        a, _, b = part.partition('-')
        out.update(range(int(a), int(b or a) + 1))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('stem')
    ap.add_argument('--pages', type=page_set)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--open', action='store_true', help='print only what did not close')
    args = ap.parse_args(argv)
    if not (OUT / f'{args.stem}.cells.tsv').exists():
        sys.exit(f'no Textract cells for {args.stem!r} in {OUT}')
    checks, _ = validate(args.stem, args.pages)
    if args.json:
        print(json.dumps([asdict(c) for c in checks], indent=1))
        return
    for c in checks:
        if args.open and c.status != 'open':
            continue
        off = '' if c.status != 'open' else f'  OFF {c.difference}'
        print(f'{c.status:<14} {c.ref:<9} {c.label[:34]:<34} {c.column[:24]:<24} {c.printed:>15} '
              f'{c.grouping:<9}{off}')
        if c.status == 'open':
            for u in c.unparsed:
                print(f'{"":>25}unparsed {u[0]}: {u[1]!r}')
    n = {s: sum(c.status == s for c in checks) for s in STATUSES}
    print(f'{len(checks)} checks: {n["closed"]} closed, {n["closed_rounded"]} within printed rounding, '
          f'{n["incomplete"]} reaching rows we do not hold, {n["open"]} open')


if __name__ == '__main__':
    main()
