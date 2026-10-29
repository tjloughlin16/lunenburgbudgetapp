#!/usr/bin/env python3
"""One Textract-read annual report, from its tables to rows in the project's own datasets.

    python3 scripts/read_report_tables.py 2010            # (re)write report-tables/2010/
    python3 scripts/read_report_tables.py 2010 --check    # fail if the folder does not reproduce
    python3 scripts/read_report_tables.py 2009 --inventory  # step 1 only: tables.csv, to map by eye

PLAN-ANNUAL-REPORT-PIPELINE.md section 4a, TJ's rule for the 1959-2010 reports: work from the
PAGE outward. (1) every table on every page is inventoried with its printed heading; (2) a table
lands in an EXISTING dataset only when it is the same quantity, stage and grain; (3) one that
does not gets a NEW dataset named for what the page prints; (4) what a modern dataset holds and
this report does not print is a GAP. Steps 2-4 are judgement, so they are written down BY EYE in
the folder (`map.csv`, `gaps.csv`, `edition.json`); this script does the rest, and it is the
same script for every edition.

WRITES ONLY INSIDE `sources/data/report-tables/<edition>/`. Never a shared file:
`merge_report_tables.py` folds the folders in. See `sources/data/report-tables/README.md`.

WHAT `status` MEANS HERE, the same three words every other extractor uses:
  checked       an identity the page itself prints closed on this row's figures -- a column
                total it sits under (validate_totals.py, P6 layer 1), or the row identity its
                own printed columns state (begin + in - out = end; precinct sum = TOTAL)
  check failed  one of those identities did not close; `reconciliation` says by how much and
                what TRIAGE (P6 layer 2) made of it. A one-digit re-reading that WOULD close it
                is recorded beside the value, never applied: the figure stays as Textract read it
  no check      nothing on the page states an identity this row takes part in
Rule 13: `column_meaning` is built from the PRINTED header cells Textract returned, cited by
page and table; where no header row was read it says `not established`.

READINGS APPLIED BEFORE ANYTHING IS BUILT, each named in the row's `reconciliation`
(`read through: ...`) and counted in `repaired_cells`:
  - validate_totals.REPAIRS: `S38,212.37`, `$ 2,500.00+`, `$6,920;527`, `$19,126.`
  - the GLYPH WITNESS (witness_dollar_glyphs.py -> glyph-witness.csv): a wage cell whose `$`
    Textract read as a leading `8` or `3` is decided by comparing its first glyph with the
    page's own `$` and digits; one it cannot decide is AMBIGUOUS -- no value, `check failed`
  - percents (`5.90%`) become figures, marked `[percent]` in `column_meaning`, AFTER the
    column checks: a share is never summed with a count

THE MAP'S OWN COLUMNS (map.csv, by eye), beyond those the README lists:
  `header`   `none` (no header row printed) | `row:N` (the header is row N) | `skip:N` (the
             first N rows are the running title). Default: the reader's rules in header_split()
  `layout`   `groups:N` or `spans:1-2,4-5,7-8` (side-by-side groups with spacer columns)
  `copy`     capital-plans: which printed copy (`town meeting article`; default `committee report`)
  `checks`   `none`: the validator's column checks do not apply (an identity the page does not state)
"""
from __future__ import annotations

import argparse
import collections
import csv
import io
import json
import os
import re
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_report_catalogue  # noqa: E402
import map_annual_report_pages as M  # noqa: E402
import page_integrity  # noqa: E402
import triage_totals  # noqa: E402
import validate_totals as V  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOLDERS = os.path.join(ROOT, 'sources', 'data', 'report-tables')
MAX_V = 8

GENERIC = ['dataset', 'fy', 'edition', 'page', 'panel', 'group', 'label', 'label_missing', 'kind',
           'row_check', 'derived_cell', 'table_family', 'line_no', 'columns_as_printed'] + \
          ['v%d' % i for i in range(1, MAX_V + 1)] + \
          ['n_values', 'ruler_spanned', 'repaired_cells', 'unparsed_cells', 'column_meaning',
           'status', 'reconciliation']

# ROW IDENTITIES, by table family: the printed column a row's figures must arrive at, from the
# other printed columns. Matched on the PRINTED header (regex, case-insensitive); an identity
# whose columns are not all found is not applied -- never guessed onto other columns.
# Blank cells count as zero; a blank target is not checked, unless the identity says
# `blank_target: zero`. An identity may name columns that must be ABSENT, which is how two
# editions' layouts that share most of their headings are told apart.
#
# Each edition's layout below was written from its printed header and TESTED on its rows
# before it went in -- the closure counts are in sources/data/report-tables/README.md.
IDENTITIES = {
    # BALANCE TO REVENUE = AVAILABLE - EXPENDED - ENCUMBERED, where the balance is printed. A
    # BLANK balance is NOT read as zero, though 2004 and 2009 asked for it: tried on 2010, the
    # blank-balance lines fail in offsetting pairs inside one department (Payroll +439.48,
    # Other Expenses -439.48), because the balance is struck per department, not per line. A
    # check that fails on correct figures is no better than one that cannot fail.
    'accountant-schedule': [('BALANCE', [(1, 'AVAILABLE'), (-1, 'EXPENDED'), (-1, 'ENCUMBERED')])],
    'special-revenue': [('BALANCE', [(1, 'FORWARD 7'), (1, 'RECEIPTS'), (-1, 'DISBURSEMENTS')])],
    'capital-projects': [('^BALANCE', [(1, 'APPROPRIATED'), (-1, 'EXPENDED')])],
    'trust-funds': [
        # 2010: BEGINNING BALANCE PRINC. | ... EARNINGS | CONTRIB | NET EARNINGS | DISBURSE | TRANSFERS
        ('ENDING CASH', [(1, 'BEGIN+ING BALANCE PRINC'), (1, 'BEGIN+ING BALANCE EARN'),
                         (1, 'CONTRIB'), (1, 'NET EARNINGS'), (-1, 'DISBURSE'),
                         (1, 'TRANSFERS')]),
        # 2007 and 2009: BEGIN BAL ... | NET EARN(ING)S | DISBURS(EMENTS) | TRANS(.) (OF) EARN(ING)S.
        # DISBURSEMENTS are printed NEGATIVE in these editions, so the term is added; and
        # 2007's REALIZED G/L is not a term (it is inside NET EARNINGS: 0 of 41 rows close
        # with it, 37 of 41 without).
        ('ENDING CASH', [(1, 'BEGIN BAL\\w* PRINC'), (1, 'BEGIN BAL\\w* EARN'), (1, 'CONTRIB'),
                         (1, 'NET EARN'), (1, 'DISBURS'), (1, 'TRANS\\W*(?:OF )?EARN')]),
        # 2006: the same, with NO transfers column and disbursements printed positive
        ('ENDING CASH', [(1, 'BEGIN BAL\\w* PRINC'), (1, 'BEGIN BAL\\w* EARN'), (1, 'CONTRIB'),
                         (1, 'NET EARN'), (-1, 'DISBURS')], {'absent': ['TRANS']}),
        ('ENDING MARKET', [(1, 'ENDING CASH'), (1, 'UNREALIZED')]),
        # 2009 heads its market column `6/30/2009 MARKET VALUE`
        ('MARKET VALUE', [(1, 'ENDING CASH'), (1, 'UNREALIZED')], {'absent': ['ENDING MARKET']}),
    ],
    'collection-of-taxes': [('BALANCES', [(1, 'FORWARD'), (1, 'COMMIT'), (1, 'ADJUSTMENTS'),
                                          (1, 'REFUNDS'), (1, 'PAYMENTS'), (1, 'ABATEMENTS'),
                                          (1, 'TAX TITLE')])],
    # precinct columns are headed `PREC A` in most years and `PRE A` in 2004's state primary
    'elections': [('^TOTAL', [(1, 'PRE\\w* A'), (1, 'PRE\\w* B'), (1, 'PRE\\w* C'), (1, 'PRE\\w* D')])],
    'debt-by-issue': [('^BALANCE', [(1, '^AMOUNT'), (-1, 'PAYMENTS PRINCIPAL')]),
                      # 2007 prints `TOTAL PAYMENTS THRU 2007` over two sub-columns, and the
                      # principal one is named `TOTAL PRINCIPAL` (10 of 10 issues close)
                      ('^BALANCE', [(1, '^AMOUNT'), (-1, '^TOTAL PRINCIPAL')])],
}
ID_TEXT = re.compile(r'^\d[\d\s\-/&]*$')          # `1518`, `2830-2838`, `2354/2355/23`
DATE_HEAD = re.compile(r'^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$')
PERCENT = re.compile(r'^\(?-?(\d*\.?\d+)\s*%\)?$')


def folder(edition):
    return os.path.join(FOLDERS, edition)


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def num(v):
    s = format(v, 'f')
    return s


def lines_by_page(stem):
    out = collections.defaultdict(list)
    with open(V.OUT / f'{stem}.lines.tsv', newline='') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            out[int(r['page'])].append(r)
    for p in out:
        out[p].sort(key=lambda r: float(r['top']))
    return out


TITLE_MARK = re.compile(r'\b(TOWN|LUNENBURG|FISCAL|SUMMARY|SPECIAL REVENUE|GENERAL FUND|CLASSIFICATION|'
                        r'APPROPRIATIONS|ACCOUNTS|ENDING|ENDED)\b', re.I)
TOP_LINES = {}           # {page: set of words in the page's first four lines}, set by build()


def drop_title(head, page):
    """THE PAGE'S RUNNING TITLE IS NOT A COLUMN NAME. Textract returns `TOWN OF LUNENBURG /
    SPECIAL REVENUE FUNDS / FISCAL YEAR ENDING 6/30/09` as header rows, and `header_names`
    concatenated them into every column's name (`v1=TOWN OF SPECIAL REVENUE FISCAL YEAR ENDING
    FORWARD 7/1/2008`), on the special revenue and accountant pages of nine editions. A header
    row is dropped when every word in it is in the page's first four printed lines AND it carries
    a title word -- and never when it is the only header row left."""
    top = TOP_LINES.get(page, set())
    keep = []
    for i, r in enumerate(head):
        words = re.findall(r'[A-Za-z0-9&/\']+', ' '.join(c.text for c in r.cells.values()).upper())
        later = any(any(c.text.strip() for c in x.cells.values()) for x in head[i + 1:])
        if words and later and set(words) <= top and TITLE_MARK.search(' '.join(words)):
            continue
        keep.append(r)
    return keep


def header_names(head):
    names = {}
    for r in head:
        for k, c in sorted(r.cells.items()):
            if c.text.strip():
                names[k] = (names.get(k, '') + ' ' + ' '.join(c.text.split())).strip()
    return names


# ---- 1. the inventory ------------------------------------------------------------------------

def inventory(stem, tables, lines):
    out = []
    for (p, t), rows in tables.items():
        head, body = V.split_header(rows)
        names = header_names(head)
        ncols = max((max(r.cells) for r in rows), default=0)
        top = [' '.join(l['text'].split()) for l in lines.get(p, [])[:4]]
        figs = sum(1 for r in rows for c in r.cells.values() if V.is_figure(c))
        out.append({'page': p, 'table': t, 'rows': len(rows), 'cols': ncols, 'header_rows': len(head),
                    'printed_header': ' | '.join(names[k] for k in sorted(names)),
                    'page_top_lines': ' || '.join(top)[:240], 'figures': figs})
    return out


# ---- 2. checks: what each cell's printed identities said ---------------------------------------

def cell_checks(stem, tables=None):
    """{(ref, col): [(status, Check, Triage|None)]} from P6 layers 1 and 2, on the cells as
    this edition reads them (the glyph witness applied)."""
    checks, runs = V.validate(stem, tables=tables)
    out = collections.defaultdict(list)
    for c in checks:
        t = triage_totals.triage(c, runs[c.stream]) if c.status == 'open' else None
        for ref in set(c.items) | {c.ref}:
            out[(ref, c.col)].append((c.status, c, t))
    return out, checks


def describe(c, t):
    if c.status.startswith('closed'):
        return '%s closes at %s `%s`' % (c.column, c.ref, c.label[:40])
    if c.status == 'incomplete':
        return '%s at %s reaches rows on a page not held' % (c.column, c.ref)
    s = '%s at %s `%s`: printed %s, rows sum %s (off %s)' % (
        c.column, c.ref, c.label[:40], c.printed, c.computed, c.difference)
    if t:
        s += ' [triage: %s%s -- %s%s]' % (t.triage, ' settled' if t.settled else '', t.how,
                                           ''.join('; %s %r -> %r' % tuple(x[:3]) for x in t.corrections[:2]))
    return s


def row_identity(family, names, cells):
    """[(ok, text)] for each identity of this family whose columns the header prints."""
    out = []
    for ident in IDENTITIES.get(family, []):
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
        tc = cells.get(tk)
        blank = tc is None or (tc.value is None and not tc.unparsed and not tc.text.strip())
        if blank and opts.get('blank_target') == 'zero':
            # A PRINTED BLANK READ AS ZERO -- only on a row that prints the columns the
            # identity rests on, so a heading row or a carried-forward line is not checked
            need = [col(rx) for rx in opts.get('needs', ())]
            if any(k is None or cells.get(k) is None or cells[k].value is None for k in need):
                continue
            target_value = Decimal(0)
        elif tc is None or tc.value is None:
            continue
        else:
            target_value = tc.value
        if any(cells.get(k) is not None and cells[k].unparsed for _, k in ks):
            out.append((False, '%s: a term did not parse' % names[tk]))
            continue
        got = sum((s * (cells[k].value if cells.get(k) is not None and cells[k].value is not None
                        else Decimal(0)) for s, k in ks), Decimal(0))
        ok = got == target_value
        out.append((ok, '%s%s %s %s' % (names[tk], ' (blank, read as 0)' if blank else '', '=' if ok else '!=',
                                        ' '.join(('+' if s > 0 else '-') + names[k][:18] for s, k in ks)
                                        + ('' if ok else ' (%s vs %s)' % (V.money(target_value), V.money(got))))))
    return out


# ---- 2b. readings applied to the cells before anything is built on them -----------------------

def apply_witness(d, tables):
    """THE GLYPH WITNESS (scripts/witness_dollar_glyphs.py): where a wage cell's first glyph
    was compared with the page's own `$` and digits, take that reading; where it could not be
    decided, the cell is AMBIGUOUS -- no value, and its row is kept out of `checked`. Returns
    {(page, text): (decision, reading)} for the coverage check to read the LINES the same way."""
    w = read_csv(os.path.join(d, 'glyph-witness.csv'))
    seen = collections.defaultdict(set)
    for r in w:
        seen[(int(r['page']), r['text'])].add((r['decision'], r['reading'], r['score_dollar'], r['score_digit']))
    out = {}
    for k, v in seen.items():
        decs = {x[0] for x in v}
        out[k] = (decs.pop(), next(iter(v))) if len(decs) == 1 else ('undecided', next(iter(v)))
    for (p, t), rows in tables.items():
        for r in rows:
            for c in r.cells.values():
                hit = out.get((p, c.text.replace(' ', '')))
                if not hit:
                    continue
                dec, (_, reading, sd, sx) = hit
                if dec == '$' or dec == 'digit':
                    c.value, c.places, _ = V.parse(reading)
                    if reading != c.text.replace(' ', ''):
                        c.repair = ('glyph witness: Textract `%s`; its first glyph matches this page\'s `$` '
                                    '(%s) not its `%s` (%s), so `%s`' % (c.text, sd, c.text[0], sx, reading))
                else:
                    c.value, c.unparsed = None, True
                    c.ambiguous = ('AMBIGUOUS: Textract `%s` prints no `$` on a page that prints one on most '
                                   'figures, and its first glyph could not be decided between `$` (%s) and '
                                   '`%s` (%s) -- `%s` or `$%s`' % (c.text, sd, c.text[0], sx, c.text, c.text[1:]))
    return out


def apply_percents(tables):
    """PERCENTS AS FIGURES, applied AFTER the column checks: a percent is a share, never summed
    with a count or a dollar, so it takes no part in `validate_totals`; it lands in a v-column
    with `[percent]` beside its name in `column_meaning`."""
    for rows in tables.values():
        for r in rows:
            for c in r.cells.values():
                m = PERCENT.match(c.text.strip())
                if m and c.value is None:
                    c.value, c.places, c.unparsed = Decimal(m.group(1)), len(m.group(1).split('.')[1]) if '.' in m.group(1) else 0, False
                    if c.text.strip().startswith('(') or c.text.strip().startswith('-'):
                        c.value = -c.value
                    c.percent = True


def repairs_of(c):
    """The named readings applied to one cell, for `repaired_cells`."""
    out = []
    if V.FWD.match(c.text.replace(' ', '').replace('$', '', 1)):
        out.append('fwd mark')
    out += V.repair(c.text)[1]
    if getattr(c, 'repair', None):
        out.append(c.repair)
    return out


# ---- 3. records: one per printed row (or per side-by-side group) -----------------------------

def _nonempty(r):
    return [(k, c) for k, c in sorted(r.cells.items()) if c.text.strip()]


def _data_row(r):
    """A row of a table with no money figure that is DATA, not a header: a text cell and at
    least one number, in either order (`2004 | Kathryn Herrick` is an office holder and her
    term), the numbers not being a run of DISTINCT years (`School/Grade | 2007 | 2008`)."""
    cells = _nonempty(r)
    nums = [c for _, c in cells if c.value is not None]
    if not nums or not any(re.search(r'[A-Za-z]{2}', c.text) for _, c in cells if c.value is None):
        return False
    years = [c.text.strip() for c in nums]
    return not (len(years) >= 2 and all(V.YEAR.match(y) for y in years) and len(set(years)) == len(years))


def header_split(m, rows, ncols):
    """(head, body, how). THE MAP DECIDES WHERE IT CAN: `header` = `none` (the table prints no
    header row: every row is data), `row:N` (the header is row N; rows above it are a title),
    `skip:N` (the first N rows are the page's running title, then the ordinary rule).

    THE ORDINARY RULE for a table with no money figure, which used to take row 1 as the header
    whatever it was -- and on officials lists, rosters and activity counts row 1 is DATA, so
    the first office holder, the first category, the whole of a one-row table was lost (2001,
    2003, 2006, 2007 and 2010 all lost rows this way): skip leading empty rows and one-cell
    title rows; then the first row is the header only if it does not read as data."""
    how = (m.get('header') or '').strip()
    if how == 'none':
        return [], [r for r in rows if _nonempty(r)], 'the map: no header row printed'
    if how.startswith('row:'):
        n = int(how[4:])
        return rows[n - 1:n], rows[n:], 'the map: header is row %d' % n
    if how.startswith('skip:'):
        rows = rows[int(how[5:]):]
    # A ROW OF DATES IS A HEADER (`School/Grade | 10-01-99 | 10-01-00 | 10-01-01`), wherever in
    # the first few rows Textract put it -- under a title and a blank row in 2001-2003, under
    # an empty row in 2008-2009. Rows above it are the title.
    for j, r in enumerate(rows[:5]):
        if sum(1 for _, c in _nonempty(r) if DATE_HEAD.match(c.text.strip())) >= 2:
            return rows[j:j + 1], rows[j + 1:], ('header is row %d, a row of dates' % (j + 1)) if j else ''
    head, body = V.split_header(rows)
    if body:
        return head, body, ''
    i = 0
    while i < len(rows) and not _nonempty(rows[i]):
        i += 1
    if i:
        # Textract's EMPTY first row is the header the table does not print: nothing is lost
        return rows[:i], rows[i:], ''
    while i < len(rows) and ncols >= 3 and len(_nonempty(rows[i])) == 1:
        i += 1                                     # one-cell title rows above a wide table
    if i < len(rows) and _data_row(rows[i]):
        return rows[:i], rows[i:], 'no header row: row %d is data' % (i + 1)
    return rows[:i + 1], rows[i + 1:], ''


def spans_of(m, ncols):
    """Side-by-side groups: `groups:N` cuts N equal widths; `spans:1-2,4-5,7-8` names each
    group's columns, for a page Textract returned with empty spacer columns between them."""
    layout = (m.get('layout') or 'groups:1').strip()
    if layout.startswith('spans:'):
        out = []
        for part in layout[6:].split(','):
            lo, _, hi = part.partition('-')
            out.append(range(int(lo), int(hi or lo) + 1))
        return out
    groups = int(layout.split(':')[1])
    width = max(1, ncols // groups)
    return [range(g * width + 1, (g + 1) * width + 1) for g in range(groups)]


def id_columns(body, figcols):
    """IDENTIFIER COLUMNS: a fund number (`1518`), a line number -- integers with no `$`, `.`
    or `,`, in a column to the LEFT of the row's first text column. They name the row; they
    are not amounts, and read as figures they pushed every amount one v-column along and broke
    the identities (2009 pp56-59)."""
    # only in a table of AMOUNTS (a `$` or cents) or of percents: in a table of counts --
    # an election, an officials list -- an integer column left of the names is data
    if not any(('$' in c.text or re.search(r'\.\d\d\b', c.text) or getattr(c, 'percent', False))
               and c.value is not None for r in body for c in r.cells.values()):
        return set()
    n = collections.Counter(k for r in body for k, c in r.cells.items()
                            if re.search(r'[A-Za-z]{2}', c.text) and c.value is None and not c.unparsed)
    filled = sum(1 for r in body if any(c.text.strip() for c in r.cells.values()))
    text_cols = [k for k, v in n.items() if v >= max(1 if filled < 4 else 2, filled * 3 // 10)]
    if not text_cols:
        return set()
    first_text = min(text_cols)
    out = set()
    for k in figcols:
        if k >= first_text:
            continue
        cells = [r.cells[k] for r in body if k in r.cells and r.cells[k].text.strip()]
        if cells and not any(V.is_figure(c) or getattr(c, 'percent', False) for c in cells) \
                and all(ID_TEXT.match(c.text.strip()) for c in cells):
            out.add(k)
    return out


def records(m, tables, checks, edition, prev_header):
    """Generic records for one mapped table: dicts with the cells kept for the emitters."""
    p, t = int(m['page']), int(m['table'])
    rows = tables[(p, t)]
    ncols = max((max(r.cells) for r in rows), default=0)
    head, body, how = header_split(m, rows, ncols)
    titled = drop_title(head, p)
    names = header_names(titled)
    cite = 'printed header, p%d table %d (Textract cells)' % (p, t)
    if len(titled) < len(head):
        cite += '; the running title above it is not part of any name'
    if how:
        cite += '; %s' % how
    if m.get('header_from'):
        # THE MAP NAMES THE TABLE THIS ONE CONTINUES, and that is a by-eye statement: it
        # wins over whatever Textract returned as a header here, which on a continuation page
        # is the running title (2009 pp56-59 named its columns `TOWN OF SPECIAL REVENUE`)
        ref = m['header_from']
        names, cite = prev_header.get(ref, ({}, ''))
        cite = cite + ', which this table continues'
    prev_header['%d/%d' % (p, t)] = (names, cite)
    spans = spans_of(m, ncols)
    groups = len(spans)
    figcols_of, idcols_of = [], []
    for span in spans:
        sub = [V.Row(rr.page, rr.row, {k: c for k, c in rr.cells.items() if k in span}, rr.table) for rr in body]
        fc = set(V.figure_cols(sub)) | {k for rr in sub for k, c in rr.cells.items() if getattr(c, 'ambiguous', None)}
        ids = id_columns(sub, fc)
        figcols_of.append(sorted(fc - ids))
        idcols_of.append(ids)
    no_checks = (m.get('checks') or '').strip() == 'none'
    out, group, pending = [], {}, {}
    for r in body:
        for g, span in enumerate(spans):
            cells = {k: c for k, c in r.cells.items() if k in span}
            gnames = {k: names.get(k, '') for k in span if names.get(k)}
            figcols = figcols_of[g]
            figs = [(k, cells[k]) for k in figcols if k in cells and cells[k].value is not None]
            text = [' '.join(cells[k].text.split()) for k in sorted(cells)
                    if k not in figcols and cells[k].text.strip()]
            unparsed = [cells[k].text for k in figcols if k in cells and cells[k].unparsed]
            ambiguous = [cells[k].ambiguous for k in figcols if k in cells and getattr(cells[k], 'ambiguous', None)]
            label = ' '.join(text)
            ids = [' '.join(cells[k].text.split()) for k in idcols_of[g] if k in cells and cells[k].text.strip()]
            if not figs and not unparsed and ids:
                # A NUMBERED LINE WITH NO AMOUNT (`64 Street Lights`, nothing voted) is an item,
                # not a heading: it lands with no values rather than becoming the next row's group
                figs = []
            elif not figs and not unparsed:
                # A MONTH PRINTED IN A FIGURE COLUMN (2001 p79's deaths: `JUNE` in the date
                # column) heads the rows below it, the way a label-only row does
                words = [' '.join(cells[k].text.split()) for k in figcols
                         if k in cells and re.search(r'[A-Za-z]{3}', cells[k].text)]
                if not label and words:
                    group[g] = ' '.join(words)[:80]
                    continue
                if label and figcols:
                    group[g] = label[:80]
                    pending[g] = (r, label)
                    continue
                if not label:
                    continue
            stats = []
            for k, c in figs:
                # THE INNERMOST CHECK ONLY: the smallest block this cell is summed in. A grand
                # total that stays open says a cell SOMEWHERE in the column is off; the block
                # that holds this cell directly says whether it is this one.
                here = [] if no_checks else checks.get((r.ref, k), [])
                if here:
                    least = min(len(ch.items) for _, ch, _ in here)
                    stats += [(s, ch, tr) for s, ch, tr in here if len(ch.items) == least]
            ident = row_identity(m['family'], gnames, cells)
            pending.pop(g, None)
            out.append({'page': p, 'table': t, 'row': r.row, 'ref': r.ref, 'panel': g + 1 if groups > 1 else '',
                        'group': group.get(g, ''), 'label': label, 'figs': figs, 'figcols': figcols,
                        'names': gnames, 'cite': cite, 'unparsed': unparsed, 'ambiguous': ambiguous,
                        'stats': stats, 'ident': ident, 'is_total': bool(V.TOTAL.search(label)), 'cells': cells})
    # A LABEL-ONLY ROW THAT HEADS NOTHING (the last line of a table: `Students w/Disabilities
    # (n=8) Not calculated if n<10`) is a row of its own, not a group for rows that never come
    for g, (r, label) in sorted(pending.items()):
        out.append({'page': p, 'table': t, 'row': r.row, 'ref': r.ref, 'panel': g + 1 if groups > 1 else '',
                    'group': '', 'label': label, 'figs': [], 'figcols': figcols_of[g], 'names': {}, 'cite': cite,
                    'unparsed': [], 'ambiguous': [], 'stats': [], 'ident': [], 'is_total': False,
                    'cells': {k: c for k, c in r.cells.items() if k in spans[g]}})
    return out


def verdict(rec, cols=None):
    if rec.get('ambiguous'):
        return 'check failed', '', ' ; '.join(rec['ambiguous'])
    return _verdict(rec, cols)


def _verdict(rec, cols=None):
    """The row's status. WHERE THE ROW STATES ITS OWN IDENTITY (begin + in - out = end, the
    precinct sum), THAT DECIDES: it is the identity that contains this row's figures and no
    other row's, so a misread here breaks it and a misread elsewhere does not. A column total
    that stays open is then recorded in `reconciliation` but does not fail every row it spans --
    one bad cell in a column of eighty would otherwise fail eighty rows that each close.
    Where the row states no identity, the column totals it sits under decide."""
    if rec['ident']:
        bad = [x for x in rec['ident'] if not x[0]]
        status = 'check failed' if bad else 'checked'
    else:
        mine = [x for x in rec['stats'] if cols is None or x[1].col in cols]
        bad = [x for x in mine if x[0] == 'open']
        good = [x for x in mine if x[0].startswith('closed')]
        status = 'check failed' if bad else 'checked' if good else 'no check'
    seen, parts = set(), []
    for s, c, tr in rec['stats']:
        if cols is not None and c.col not in cols:
            continue
        if (c.ref, c.col) not in seen:
            seen.add((c.ref, c.col))
            parts.append(describe(c, tr))
    rc = '; '.join(x[1] for x in rec['ident'])
    rec_text = ' ; '.join(parts[:4]) + (' (+%d more)' % (len(parts) - 4) if len(parts) > 4 else '')
    return status, rc, rec_text or ('no total printed' if status == 'no check' else '')


# ---- 4. emitters: a record into the target dataset's own columns -----------------------------

def emit_generic(m, recs, ed):
    out = []
    for rec in recs:
        figs = rec['figs']
        chunks = [figs[i:i + MAX_V] for i in range(0, max(len(figs), 1), MAX_V)] or [[]]
        for ci, chunk in enumerate(chunks):
            status, rc, recon = verdict(rec, {k for k, _ in chunk} if len(chunks) > 1 else None)
            meaning = ' | '.join('v%d=%s%s' % (i + 1, rec['names'].get(k, 'not established'),
                                               ' [percent]' if getattr(c, 'percent', False) else '')
                                 for i, (k, c) in enumerate(chunk))
            fixes = [x for _, c in chunk for x in repairs_of(c)]
            row = {f: '' for f in GENERIC}
            panel = rec['panel']
            if len(chunks) > 1:
                panel = '%s%s' % ('%s.' % panel if panel else '', ci + 1)
            row.update(dataset=m['dataset'].replace('report-', '').replace('-', '_'), fy=ed['fy'],
                       edition=ed['edition'], page=rec['page'], panel=panel, group=rec['group'],
                       label=rec['label'][:200], label_missing='yes' if not rec['label'] else '',
                       kind='total' if rec['is_total'] else 'row', row_check=rc,
                       table_family=m['family'], line_no='t%dr%d' % (rec['table'], rec['row']),
                       columns_as_printed=' | '.join(rec['names'].get(k, '') for k, _ in chunk)[:300],
                       n_values=len(chunk),
                       repaired_cells=len(fixes) or '',
                       unparsed_cells=' ; '.join(rec['unparsed']),
                       column_meaning=(meaning + ' (%s)' % rec['cite']) if chunk else '',
                       status=status, reconciliation=recon + (' ; read through: ' + ' ; '.join(fixes) if fixes else ''))
            for i, (k, c) in enumerate(chunk):
                row['v%d' % (i + 1)] = num(c.value)
            out.append(row)
    return out


def by_name(rec, rx):
    for k, n in rec['names'].items():
        if re.search(rx, n, re.I):
            c = rec['cells'].get(k)
            return c.value if c is not None and c.value is not None else None
    return None


def emit_receipts(m, recs, ed):
    """annual-report-receipts: one revenue account, its FY amount. The page prints a SUMMARY OF
    RECEIPTS by category and a GRAND TOTAL; the accounts are checked when they sum to it."""
    items, summary, grand = [], [], None
    for rec in recs:
        lab = rec['label']
        if not rec['figs']:
            continue
        v = rec['figs'][0][1].value
        if re.search(r'GRAND TOTAL', lab, re.I):
            grand = (rec, v)
        elif re.search(r'SUMMARY OF RECEIPTS', rec['group'], re.I):
            summary.append((rec, v))
        else:
            items.append((rec, v))
    s_items = sum((v for _, v in items), Decimal(0))
    s_summary = sum((v for _, v in summary), Decimal(0))
    ok_items = grand is not None and s_items == grand[1]
    out = []
    note = ('accounts sum %s vs the printed GRAND TOTAL %s; categories in the SUMMARY OF RECEIPTS sum %s'
            % (V.money(s_items), V.money(grand[1]) if grand else 'not read', V.money(s_summary)))
    for rec, v in items:
        out.append({'fy': ed['fy'], 'source': re.sub(r'^[A-Z &/]+:\s*', '', rec['label']) or rec['label'],
                    'amount': num(v), 'status': 'checked' if ok_items else 'check failed' if grand else 'no check',
                    'document': os.path.basename(ed['pdf']), 'page': rec['page']})
    return out, note


CASH_INVESTED = re.compile(r'CURRENT CASH INVESTED', re.I)
MONEY_TOKEN = re.compile(r'\(?\$?\s?\(?\d{1,3}(?:,\d{3})+(?:\.\d{2})?\)?|\(?\$?\s?\(?\d+\.\d{2}\)?')


def raw_figures(text):
    """Every money figure in a cell, in order -- a cell may print two (`$71,193,967.00
    ($48,093,859.00)`, 2006 p64). Parenthesised is negative."""
    whole = V.parse(text)[0]
    if whole is not None:
        return [whole] if V.is_figure(V.Cell(text, 0, whole)) else []
    out = []
    for tok in MONEY_TOKEN.findall(text):
        if '$' not in tok and not re.search(r'\.\d\d', tok):
            continue            # `30,2006` in `BALANCE JUNE 30,2006` is a date, not a figure
        v = V.parse(tok.replace('(', '').replace(')', ''))[0]
        if v is not None:
            out.append(-v if '(' in tok else v)
    return out


def emit_treasurers_cash(m, recs, ed, raw):
    """CONSTRUCTION: published only when the accounts sum to the total the page prints.

    THE TOTAL may be a labelled row (`TOTAL`, `GENERAL LEDGER BALANCE`), an unlabelled last
    row holding one figure (2001, 2002), or -- where Textract put the account list and its
    total in two tables -- the `stated_total` the map cites from the other table (2003-2006).
    And where the page prints the year's cash ROLL-FORWARD above the accounts (2007, 2008:
    balance, receipts, disbursed, general ledger balance, then `CURRENT CASH INVESTED:`), those
    lines are not accounts: they go to `report-treasurers-cash-reconciliation`, returned third."""
    start = next((rr.row for rr in raw if any(CASH_INVESTED.search(c.text) for c in rr.cells.values())), None)
    block = [rr for rr in raw if start is not None and rr.row < start]
    body = [r for r in recs if start is None or r['row'] > start]
    accts = [r for r in body if r['figs'] and not r['is_total']
             and not re.search(r'balance|^receipts|^disbursed', r['label'], re.I)]
    totals = [r for r in body if r['figs'] and (r['is_total'] or re.search(r'ledger balance', r['label'], re.I))]
    s = sum((r['figs'][0][1].value for r in accts), Decimal(0))
    if totals:
        printed, where = totals[-1]['figs'][0][1].value, 'the printed %s' % totals[-1]['label']
    else:
        last = [rr for rr in raw if rr.cells and any(c.text.strip() for c in rr.cells.values())][-1:]
        lone = [c for rr in last for c in rr.cells.values() if c.text.strip()]
        if len(lone) == 1 and lone[0].value is not None and not accts[-1:] == [] and \
                last[0].row > max(r['row'] for r in accts):
            printed, where = lone[0].value, 'the unlabelled figure printed under the list (row %d)' % last[0].row
        elif m.get('stated_total'):
            printed, where = Decimal(m['stated_total']), 'the total the page prints outside this table (map `stated_total`)'
        else:
            printed, where = None, ''
    recon = emit_cash_reconciliation(m, block, ed) if block else []
    if printed is None or printed != s:
        return [], 'accounts sum %s, printed %s: not published (refused)' % (
            V.money(s), V.money(printed) if printed is not None else 'none read'), recon
    return [{'fy': ed['fy'], 'report_fy': ed['fy'], 'held_as': r['label'], 'amount': num(r['figs'][0][1].value),
             'column': 'as printed', 'page': r['page'], 'document': ed['pdf']} for r in accts], \
        '%d accounts sum to %s, %s' % (len(accts), V.money(s), where), recon


RECON = [('opening', r'^BALANCE\b'), ('receipts', r'^RECEIPTS'), ('investments', r'LESS INVESTMENTS'),
         ('disbursed', r'^DISBURSED'), ('revenue_invested', r'LESS REVENUE CASH'),
         ('ledger', r'GENERAL LEDGER BALANCE')]


def emit_cash_reconciliation(m, raw, ed):
    """`report-treasurers-cash-reconciliation`: the Treasurer's year of cash, as the page prints
    it -- opening balance, receipts (less investments transferred), disbursed (less revenue
    cash invested), general ledger balance. ITS IDENTITY RUNS DOWN THE PAGE, not across a row,
    which is why `IDENTITIES` could not hold it:

        net receipts   = receipts - investments transferred
        after receipts = opening + net receipts
        net disbursed  = disbursed - revenue cash invested
        ledger balance = after receipts - net disbursed

    Each step is checked where the page prints both sides; the unlabelled figures are the
    running subtotals, taken in the order printed. Every row carries the chain's verdict,
    because one misread anywhere in it breaks the ledger balance and does not say where."""
    lines = []
    for rr in raw:
        label = ' '.join(' '.join(c.text.split()) for k, c in sorted(rr.cells.items())
                         if c.text.strip() and not raw_figures(c.text))
        figs = [v for k, c in sorted(rr.cells.items()) for v in raw_figures(c.text)]
        if label or figs:
            lines.append((rr, label, figs))
    got = {}
    phase = 'before'
    subtotals = {'receipts': ['net_receipts', 'after_receipts'], 'disbursed': ['net_disbursed']}
    for rr, label, figs in lines:
        kind = next((k for k, rx in RECON if re.search(rx, label, re.I)), None)
        if kind == 'receipts' and re.search(RECON[2][1], label, re.I):
            # one printed line holding receipts, the transfer, and the net (2006)
            got['receipts'], got['investments'] = figs[0], figs[1] if len(figs) > 1 else None
            if len(figs) > 2:
                got['net_receipts'] = figs[2]
            phase = 'receipts'
        elif kind == 'disbursed' and re.search(RECON[4][1], label, re.I):
            got['disbursed'], got['revenue_invested'] = figs[0], figs[1] if len(figs) > 1 else None
            if len(figs) > 2:
                got['net_disbursed'] = figs[2]
            phase = 'disbursed'
        elif kind and figs:
            got[kind] = figs[0]
            phase = {'receipts': 'receipts', 'investments': 'receipts', 'disbursed': 'disbursed',
                     'revenue_invested': 'disbursed'}.get(kind, phase)
        elif not label and figs:
            slot = next((x for x in subtotals.get(phase, []) if x not in got), None)
            if slot:
                got[slot] = figs[0]
    A = lambda k: abs(got[k]) if got.get(k) is not None else None  # noqa: E731
    steps = []

    def step(name, printed, parts):
        if printed is None or any(x is None for x in parts):
            return None
        calc = sum(parts, Decimal(0))
        steps.append((printed == calc, '%s %s %s' % (name, V.money(printed), '=' if printed == calc else
                                                      '!= %s (off %s)' % (V.money(calc), V.money(printed - calc)))))
        return printed
    nr = got.get('net_receipts')
    nr_calc = (A('receipts') - A('investments')) if A('receipts') is not None and A('investments') is not None else A('receipts')
    if nr is not None:
        step('net receipts', nr, [A('receipts'), -A('investments') if A('investments') is not None else None])
    nr = nr if nr is not None else nr_calc
    ar = got.get('after_receipts')
    if ar is not None:
        step('opening + net receipts', ar, [got.get('opening'), nr])
    ar = ar if ar is not None else (got['opening'] + nr if got.get('opening') is not None and nr is not None else None)
    nd = got.get('net_disbursed')
    nd_calc = (A('disbursed') - A('revenue_invested')) if A('disbursed') is not None and A('revenue_invested') is not None else A('disbursed')
    if nd is not None:
        step('net disbursed', nd, [A('disbursed'), -A('revenue_invested') if A('revenue_invested') is not None else None])
    nd = nd if nd is not None else nd_calc
    step('general ledger balance', got.get('ledger'), [ar, -nd if nd is not None else None])
    ok = bool(steps) and all(x[0] for x in steps)
    status = 'checked' if ok else 'check failed' if steps else 'no check'
    recon = '; '.join(x[1] for x in steps) or 'the chain could not be followed: %s' % ', '.join(sorted(got))
    out = []
    for rr, label, figs in lines:
        row = {f: '' for f in GENERIC}
        row.update(dataset='treasurers_cash_reconciliation', fy=ed['fy'], edition=ed['edition'], page=rr.page,
                   label=label[:200], label_missing='' if label else 'yes (a running subtotal)',
                   kind='total' if re.search(RECON[5][1], label, re.I) else 'row',
                   table_family='cash-reconciliation', line_no='t%dr%d' % (rr.table, rr.row),
                   n_values=len(figs), status=status, reconciliation=recon,
                   column_meaning=' | '.join('v%d=as printed, in the running column (no column heading is printed)'
                                             % (i + 1) for i in range(len(figs))) +
                   ' (p%d table %d, Textract cells; a cell printing two figures is split)' % (rr.page, rr.table))
        for i, v in enumerate(figs[:MAX_V]):
            row['v%d' % (i + 1)] = num(v)
        out.append(row)
    return out


FUNDS = [('GENERAL', 'general'), ('SPECIAL REVENUE', 'special_revenue'), ('ENTERPRISE', 'enterprise'),
         ('CAPITAL PROJECT', 'capital_project'), ('FI\\w+CIARY|TRUST', 'trust_agency'),
         ('LONG.TERM', 'long_term_debt')]


def emit_balance_sheet(m, recs, ed, folios, checks):
    """CONSTRUCTION, per fund column: a column is published only when its TOTAL ASSETS and
    assets = liabilities + fund equity both close on the page. The rest is refused, by name."""
    names = recs[0]['names'] if recs else {}
    fund_of = {}
    for k, n in names.items():
        for rx, f in FUNDS:
            if re.search(rx, n, re.I) and f not in fund_of.values():
                fund_of[k] = f
                break
    p = recs[0]['page'] if recs else 0
    ok = {}
    for k in fund_of:
        st = [c.status for ref_col, lst in checks.items() if ref_col[1] == k
              for s, c, _ in lst if c.page == p and (V.ASSETS.search(c.label) or c.grouping == 'balance')]
        ok[k] = bool(st) and all(s.startswith('closed') for s in st)
    rows, totals, section = [], [], 'assets'
    for rec in recs:
        lab = rec['label']
        for k, c in rec['figs']:
            if k not in fund_of:
                continue
            base = dict(fy=ed['fy'], edition=ed['edition'], page_printed=folios.get(p, ''), page_pdf=p)
            if rec['is_total']:
                totals.append(dict(base, total_row=lab, fund=fund_of[k], amount=num(c.value),
                                   quote='%s row, printed page %s' % (lab, folios.get(p, '?'))))
            elif ok[k]:
                rows.append(dict(base, section=section, line=lab, fund=fund_of[k], amount=num(c.value),
                                 document=ed['pdf'], read_by='textract', report_fy=ed['fy'], page=p))
        if re.search(r'TOTAL ASSETS', lab, re.I):
            section = 'liabilities'
        elif re.search(r'TOTAL LIABILITIES$|TOTAL LIABILITIES\b(?!.*EQUITY)', lab, re.I):
            section = 'fund_balances'
    refused = sorted(f for k, f in fund_of.items() if not ok[k])
    return rows, totals, ('published: %s; refused (an identity on the page did not close): %s'
                          % (', '.join(sorted(f for k, f in fund_of.items() if ok[k])) or 'none',
                             ', '.join(refused) or 'none'))


def emit_special_revenue(m, recs, ed):
    out, n = [], collections.Counter()
    for rec in recs:
        if not rec['figs']:
            continue
        status, rc, recon = verdict(rec)
        n[rec['page']] += 1
        row = {'fy': ed['fy'], 'edition': ed['edition'], 'group': rec['group'],
               'fund': 'p%d-%02d %s :: %s' % (rec['page'], n[rec['page']], rec['group'], rec['label']),
               'page': rec['page'], 'is_subtotal': 'yes' if rec['is_total'] else '',
               'columns_as_printed': ' | '.join(rec['names'].get(k, '') for k, _ in rec['figs']),
               'receipts': num(by_name(rec, 'RECEIPTS')) if by_name(rec, 'RECEIPTS') is not None else '',
               'read_by': 'textract (AWS), cells as returned', 'n_values': len(rec['figs']),
               'column_meaning': ' | '.join('v%d=%s' % (i + 1, rec['names'].get(k, 'not established'))
                                            for i, (k, _) in enumerate(rec['figs'])) + ' (%s)' % rec['cite'],
               'row_check': rc, 'status': status, 'reconciliation': recon}
        for i, (k, c) in enumerate(rec['figs'][:6]):
            row['v%d' % (i + 1)] = num(c.value)
        out.append(row)
    return out


def emit_tax_collection(m, recs, ed):
    cols = [('forward', 'FORWARD'), ('committed', 'COMMIT'), ('adjustments', 'ADJUSTMENTS'),
            ('refunds', 'REFUNDS'), ('payments', 'PAYMENTS'), ('abatements', 'ABATEMENTS'),
            ('transfer', 'TAX TITLE'), ('balance', 'BALANCES')]
    out = []
    for rec in recs:
        if not rec['figs']:
            continue
        row = {'fy': ed['fy'], 'section': rec['group'], 'item': rec['label'], 'page': rec['page'],
               'instrument': 'textract', 'document': ed['pdf']}
        for f, rx in cols:
            v = by_name(rec, rx)
            row[f] = num(v) if v is not None else ''
        status, _, _ = verdict(rec)
        row['proof'] = 'footed to its own printed balance' if rec['ident'] and all(x[0] for x in rec['ident']) \
            and status == 'checked' else ''
        out.append(row)
    return out


def emit_capital_plan(m, recs, ed, stated_total):
    items = [r for r in recs if r['figs'] and not r['is_total']]
    s = sum((r['figs'][0][1].value for r in items), Decimal(0))
    ok = stated_total is not None and s == stated_total
    return [{'dataset': 'capital_plan', 'edition': ed['edition'], 'report_fy': ed['fy'],
             'document': os.path.basename(ed['pdf']), 'page': r['page'], 'copy': m.get('copy') or 'committee report',
             'plan_fiscal_year': m.get('period_fy', ''), 'line_no': i + 1, 'project': ' :: '.join(' '.join(c.text.split()) for k, c in sorted(r['cells'].items()) if k not in r['figcols'] and c.text.strip()),
             'cost': num(r['figs'][0][1].value), 'cumulative': '',
             'printed_total': num(stated_total) if stated_total is not None else '',
             'columns_as_printed': ' | '.join(r['names'].values()),
             'status': 'checked' if ok else 'check failed' if stated_total is not None else 'no check',
             'reconciliation': '%d project rows sum to %s %s the total the page states'
             % (len(items), V.money(s), '=' if ok else '!=')} for i, r in enumerate(items)]


def emit_salary_schedule(m, recs, ed):
    out = []
    for rec in recs:
        grade = rec['label'] or (str(rec['figs'][0][1].value) if rec['figs'] else '')
        figs = rec['figs']
        if rec['figs'] and not rec['label']:      # the GRADE column parsed as a number
            grade, figs = str(int(figs[0][1].value)), figs[1:]
        for k, c in figs:
            step = re.search(r'(\d+)', rec['names'].get(k, ''))
            out.append({'report_fy': ed['fy'], 'document': os.path.basename(ed['pdf']), 'page': rec['page'],
                        'schedule_fy': m.get('period_fy', ''), 'grade': grade,
                        'step': step.group(1) if step else '', 'rate': num(c.value),
                        'basis': 'Textract cells (%s)' % rec['cite'], 'confirmed_by': ''})
    return out


def coverage(rows, lines, witness, m_rows):
    """A WAGE LIST PRINTS NO TOTAL, so it is graded the way FY2011-FY2025's wage pages are
    (map_annual_report_pages.PROOF, `gross-wages`): every money figure the page prints is
    captured, each on a row with a name. The witness is the page's LINE output -- a second
    pass of the same engine over the same page, NOT an independent reader, so it shares any
    misreading of a glyph. Two things make up for that:

      - where the GLYPH WITNESS decided a cell (witness_dollar_glyphs.py), the line is read
        the same way; where it could not, that row is `check failed` and the figure is
        counted out of both sides, so its neighbours are still graded
      - where the run PRINTS A GRAND TOTAL (2002, 2004: `GRAND TOTAL GROSS WAGES ...`, the
        map's `stated_total`), the employee rows are summed against it -- a check that can
        fail where coverage cannot, since a figure missed by both passes leaves the sum short"""
    by = collections.defaultdict(list)
    for r in rows:
        by[int(r['page'])].append(r)
    stated = [Decimal(m['stated_total']) for m in m_rows
              if m.get('dataset') == 'report-gross-wages' and m.get('stated_total')]
    for p, rs in by.items():
        printed, unread = collections.Counter(), 0
        for l in lines.get(p, []):
            t = V.repair(l['text'].strip())[0]       # the line read through the same marks as the cell
            if M.MONEY.match(t):
                w = witness.get((p, t.replace(' ', '')))
                if w and w[0] == 'undecided':
                    unread += 1
                    continue
                v = V.parse(w[1][1] if w else t)[0]
                if v is not None:
                    printed[v] += 1
        got = collections.Counter(Decimal(r['v1']) for r in rs if r['v1'])
        named = all(r['label'] for r in rs if r['v1'])
        ok = got == printed and named
        missing = sum((printed - got).values())
        extra = sum((got - printed).values())
        for r in rs:
            if r['status'] == 'check failed' and r['reconciliation'].startswith('AMBIGUOUS'):
                continue
            r['status'] = 'checked' if ok else 'check failed'
            r['reconciliation'] = ('coverage: all %d money figures printed on the page are captured, each with a name'
                                   % sum(printed.values()) if ok else
                                   'coverage: %d figure(s) in the page text not captured, %d captured not in the text'
                                   % (missing, extra)) + \
                (' (%d figure(s) whose first glyph is undecided are counted out of both sides)' % unread if unread else '') + \
                (r['reconciliation'][r['reconciliation'].index(' ; read through:'):]
                 if ' ; read through:' in r['reconciliation'] else '')
    if stated and rows:
        emp = [r for r in rows if r['kind'] != 'total' and r['v1']]
        s = sum((Decimal(r['v1']) for r in emp), Decimal(0))
        amb = sum(1 for r in rows if r['kind'] != 'total' and not r['v1'])
        tie = s == stated[-1]
        note = (' ; GRAND TOTAL: %d employee rows sum to %s, %s the printed %s%s'
                % (len(emp), V.money(s), '=' if tie else '!=', V.money(stated[-1]),
                   '' if tie else ' (short %s%s)' % (V.money(stated[-1] - s),
                                                     ', with %d row(s) holding no reading' % amb if amb else '')))
        for r in rows:
            r['reconciliation'] += note


# ---- 5. pages and the catalogue --------------------------------------------------------------

def page_states(dataset_rows, ed, m_rows, lines, money_counts):
    """annual-report-pages rows, by the mapper's own PROOF registry and state order."""
    by = collections.defaultdict(lambda: collections.defaultdict(set))
    cites = collections.defaultdict(set)
    for target, rows in dataset_rows.items():
        lab = M._label(target[:-4])
        col, style = M.PROOF.get(lab, (None, M.NOTHING))
        for r in rows:
            pg = r.get('page') or r.get('page_pdf')
            try:
                key = int(pg)
            except (TypeError, ValueError):
                continue
            cites[key].add(lab)
            v = M.proof_verdict(style, r.get(col) if col else None)
            if v:
                by[key][lab].add(v)
    financial = sorted({int(m['page']) for m in m_rows if m.get('financial') == 'yes'})
    # A PAGE READ AND DELIBERATELY NOT LANDED IS REFUSED, NOT UNREAD. `unread` means nobody has
    # looked; a map row saying `NOT LANDED` with its reason is somebody having looked
    mapped = {int(m['page']) for m in m_rows if m.get('dataset') or (m.get('note') or '').startswith('NOT LANDED')}
    out = []
    for p in financial:
        verd = by.get(p, {})
        proved = sorted(l for l, v in verd.items() if 'proven' in v and 'failed' not in v)
        failed = sorted(l for l, v in verd.items() if 'failed' in v)
        hits = cites.get(p, set())
        state = 'proven' if proved else 'unproven' if hits else 'refused' if p in mapped else 'unread'
        texts = [' '.join(l['text'].split()) for l in lines.get(p, [])]
        top = [t for t in texts[:10] if len(t) > 6 and not M.MONEY.match(t)]
        subj = M.subject_of(top, texts)
        pri, why = M.PRIORITY.get(subj, (99, ''))
        out.append({'fy': ed['fy'], 'page': p, 'subject': subj, 'priority': pri, 'state': state,
                    'read': 'yes' if hits else 'no', 'figures': money_counts.get(p, 0), 'figures_reversed': 0,
                    'read_by': ', '.join(sorted(hits)), 'proved_by': ', '.join(proved),
                    'failed_by': ', '.join(failed),
                    'refused_by': 'read_report_tables' if state == 'refused' else '',
                    'heading': (top[0] if top else '')[:60], 'answers': why, 'document': ed['pdf']})
    return out


def catalogue(m_rows, inv, ed, landed):
    invk = {(int(r['page']), int(r['table'])): r for r in inv}
    groups = collections.OrderedDict()
    for m in m_rows:
        groups.setdefault(m['name'], []).append(m)
    out = []
    for name, ms in groups.items():
        pages = sorted({int(m['page']) for m in ms})
        iv = [invk[(int(m['page']), int(m['table']))] for m in ms]
        where = sorted({m['dataset'] for m in ms if m['dataset']})
        n = sum(landed.get((int(m['page']), int(m['table'])), 0) for m in ms)
        out.append({'fy': ed['fy'], 'edition': ed['edition'], 'document': os.path.basename(ed['pdf']),
                    'name': name, 'printed_heading': ms[0].get('printed_heading') or iv[0]['printed_header'][:300],
                    'pages': '%d-%d' % (pages[0], pages[-1]) if len(pages) > 1 else str(pages[0]),
                    'what_it_is': ms[0].get('note', ''), 'grain': ms[0].get('grain', ''),
                    'columns': iv[0]['printed_header'][:300],
                    'layout': '; '.join('Textract p%s table %s, %s rows x %s cols'
                                        % (i['page'], i['table'], i['rows'], i['cols']) for i in iv)[:300],
                    'printed_total': '', 'approx_rows': sum(int(i['rows']) for i in iv),
                    'extractable': 'textract cells',
                    'notes': ('landed in %s: %d rows. %s' % (', '.join(where), n, ms[0].get('period', ''))
                              if where else 'NOT LANDED: %s' % ms[0].get('note', '')).strip(),
                    'cluster': build_report_catalogue.key_of(name)})
    return out


# ---- the run ---------------------------------------------------------------------------------

def write(path, rows, fields=None):
    buf = io.StringIO()
    fields = fields or (list(rows[0].keys()) if rows else [])
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    return path, buf.getvalue()


def build(edition, inventory_only=False):
    d = folder(edition)
    ed = json.load(open(os.path.join(d, 'edition.json'), encoding='utf-8'))
    stem = ed['stem']
    tables = V.load(stem)
    lines = lines_by_page(stem)
    out = [write(os.path.join(d, 'tables.csv'), inventory(stem, tables, lines))]
    if inventory_only:
        return out, {}
    m_rows = read_csv(os.path.join(d, 'map.csv'))
    unmapped = sorted(set(tables) - {(int(m['page']), int(m['table'])) for m in m_rows})
    if unmapped:
        raise SystemExit('map.csv does not account for %d table(s): %s -- every table gets a row, '
                         'with an empty dataset and a reason if it is not landed'
                         % (len(unmapped), ', '.join('p%dt%d' % k for k in unmapped)))
    TOP_LINES.clear()
    for p, ls in lines.items():
        TOP_LINES[p] = set(re.findall(r'[A-Za-z0-9&/\']+', ' '.join(l['text'] for l in ls[:4]).upper()))
    witness = apply_witness(d, tables)
    checks, _ = cell_checks(stem, tables)
    apply_percents(tables)
    rep = page_integrity.check(page_integrity.OUT / f'{stem}.lines.tsv')
    folios = rep.folios
    dataset_rows = collections.defaultdict(list)
    notes, landed, prev_header = {}, collections.Counter(), {}
    for m in m_rows:
        if not m['dataset']:
            continue
        recs = records(m, tables, checks, ed, prev_header)
        k = (int(m['page']), int(m['table']))
        target = m['dataset'] + '.csv'
        if m['dataset'] == 'report-treasurers-cash-reconciliation':
            rows = emit_cash_reconciliation(m, tables[k], ed)
        elif m['dataset'].startswith('report-'):
            rows = emit_generic(m, recs, ed)
        elif m['dataset'] == 'annual-report-receipts':
            rows, notes[k] = emit_receipts(m, recs, ed)
        elif m['dataset'] == 'treasurers-cash':
            rows, notes[k], recon = emit_treasurers_cash(m, recs, ed, tables[k])
            dataset_rows['report-treasurers-cash-reconciliation.csv'] += recon
        elif m['dataset'] == 'balance-sheet':
            rows, totals, notes[k] = emit_balance_sheet(m, recs, ed, folios, checks)
            dataset_rows['balance-sheet-printed-totals.csv'] += totals
        elif m['dataset'] == 'special-revenue-funds':
            rows = emit_special_revenue(m, recs, ed)
        elif m['dataset'] == 'tax-collection':
            rows = emit_tax_collection(m, recs, ed)
        elif m['dataset'] == 'capital-plans':
            rows = emit_capital_plan(m, recs, ed, Decimal(m['stated_total']) if m.get('stated_total') else None)
        elif m['dataset'] == 'salary-schedule':
            rows = emit_salary_schedule(m, recs, ed)
        else:
            raise SystemExit('no emitter for dataset %r (p%s t%s)' % (m['dataset'], m['page'], m['table']))
        dataset_rows[target] += rows
        landed[k] += len(rows)
    coverage(dataset_rows.get('report-gross-wages.csv', []), lines, witness, m_rows)
    # A DATASET A FOLDER NO LONGER PRODUCES (renamed, or its rows moved) must not linger in
    # rows/, where the merge would still fold it in
    produced = {t for t, r in dataset_rows.items() if r}
    rows_dir = os.path.join(d, 'rows')
    for name in sorted(os.listdir(rows_dir)) if os.path.isdir(rows_dir) else ():
        if name.endswith('.csv') and name not in produced:
            out.append((os.path.join(rows_dir, name), None))
    for target, rows in sorted(dataset_rows.items()):
        if not rows:
            continue
        # IN THE SHARED FILE'S OWN COLUMNS, read off its header -- a row the merge cannot place
        # column for column is refused there, so it is made to fit here, or this fails first.
        shared = os.path.join(ROOT, 'sources', 'data', target)
        if os.path.exists(shared):
            with open(shared, newline='', encoding='utf-8') as fh:
                fields = next(csv.reader(fh))
        else:
            fields = GENERIC if target.startswith('report-') else None
        extra = {k for r in rows for k in r} - set(fields or {k for r in rows for k in r})
        if extra:
            raise SystemExit('%s: columns the shared file does not have: %s' % (target, ', '.join(sorted(extra))))
        out.append(write(os.path.join(d, 'rows', target), [{f: r.get(f, '') for f in fields} for r in rows]
                         if fields else rows, fields))
    money_counts = collections.Counter(p for p, ls in lines.items() for l in ls if M.MONEY.match(l['text'].strip()))
    out.append(write(os.path.join(d, 'pages.csv'), page_states(dataset_rows, ed, m_rows, lines, money_counts),
                     M.FIELDS))
    out.append(write(os.path.join(d, 'catalogue.csv'), catalogue(m_rows, read_csv(os.path.join(d, 'tables.csv'))
                                                                 or inventory(stem, tables, lines), ed, landed)))
    out.append(write(os.path.join(d, 'notes.csv'),
                     [{'page': k[0], 'table': k[1], 'note': v} for k, v in sorted(notes.items())] or
                     [{'page': '', 'table': '', 'note': ''}]))
    return out, dataset_rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('edition')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--inventory', action='store_true', help='write tables.csv only, to map by eye')
    a = ap.parse_args(argv)
    files, dataset_rows = build(a.edition, a.inventory)
    stale = []
    for path, text in files:
        cur = open(path, encoding='utf-8').read() if os.path.exists(path) else None
        if cur == text:
            continue
        if a.check:
            stale.append(os.path.relpath(path, ROOT) + (' (should not exist)' if text is None else ''))
            continue
        if text is None:
            os.remove(path)
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path + '.tmp', 'w', encoding='utf-8', newline='') as fh:
            fh.write(text)
        os.replace(path + '.tmp', path)
    if a.check:
        if stale:
            print('STALE: ' + ', '.join(stale), file=sys.stderr)
            return 1
        print('ok -- report-tables/%s reproduces' % a.edition)
        return 0
    for target, rows in sorted(dataset_rows.items()):
        st = collections.Counter(r.get('status', '') for r in rows)
        print('  %-40s %5d rows  %s' % (target, len(rows), ', '.join('%s %d' % kv for kv in sorted(st.items()))))
    pages = read_csv(os.path.join(folder(a.edition), 'pages.csv'))
    print('  pages: %s' % dict(collections.Counter(r['state'] for r in pages)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
