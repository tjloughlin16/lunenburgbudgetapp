#!/usr/bin/env python3
"""The Assessors' valuation tables in the annual town reports, read and RECONCILED.

Why this exists beside `extract_tables.py valuation`, which already writes
`sources/data/report-valuation.csv`:

**The generic extractor cannot read these pages, and what it writes is not merely
unchecked -- it is wrong.** The Assessors print three or four independent tables on one
page (major class, the abstract of assessments, the valuation and tax history, the overlay
account), each with its own columns. One column ruler cannot serve four tables. On FY2018
page 41 it produced

    Residential     (no values at all)
    Commercial      v2 = 6603477819.70

-- which is `66,034,778` and the tax rate `19.70` run together into one figure, and a
class row with every figure lost. Every one of the 321 rows in `report-valuation.csv`
carries `status=no check`, so nothing said so.

So this reads the valuation family on its own terms: each table located by its own printed
heading, its columns named from a header that was READ and written down here (rule 13b,
never inferred), and every year reconciled to a control the document itself prints.

Four tables, and what proves each one:

| table | control |
|---|---|
| `major_class` | the printed TOTALS row: valuation, levy, and levy percent summing to 100 |
| `total_valuation` | the printed `Total Valuation` line (FY2024, FY2025 layout) |
| `new_growth` | no printed total; the row's own identity, added valuation x rate / 1000 |
| `avg_values` | no printed total; the row's own identity, the printed % change |

**A year that does not tie is written with `status=check failed` and its residual, and is
excluded from every series.** FY2021 is the one that matters: its four class rows are
internally consistent to the penny and its printed TOTALS row is FY2020's, left in. So the
levy-percent column ties to 100.0000 and the valuation and levy columns miss by
$194,412,308 and $1,902,070.30. Three facts, not one pass/fail, which is why the
reconciliation is reported per column.

**Repairs.** A misread glyph is repaired only where the document's own arithmetic fixes
it, in the narrow form rule 13b allows: exactly one row in a column is short, the column's
printed total names what that row must be, AND the repaired figure independently satisfies
the row's own identity (valuation x rate / 1000 = levy). Two statements agreeing on the
same digit is proof; one is a guess. Every repair is written into `repaired` with the raw
OCR text beside it, so nothing is silently corrected.

    python3 scripts/extract_valuation.py
    python3 scripts/extract_valuation.py --check
"""

import argparse
import collections
import csv
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
OUT = os.path.join(ROOT, 'sources', 'data', 'valuation-by-class.csv')
# A page refused is not a page read. `map_annual_report_pages.py` clears a queued page
# the moment any dataset holds a row citing its `report_fy` and `page`, so a refusal left
# in the dataset would report the page as read while holding none of its figures. Refusals
# go beside it, in a file carrying a `state` column -- the flag that join uses to skip a
# catalogue of what has been read rather than a reading.
REFUSED = os.path.join(ROOT, 'sources', 'data', 'valuation-refused.csv')
REFUSED_FIELDS = ['dataset', 'edition', 'report_fy', 'document', 'page', 'table',
                  'state', 'reconciliation']

# `report_fy` is the fiscal year of the REPORT this page was printed in, and `page` is
# the page in it. Those two names are the join `scripts/map_annual_report_pages.py` uses
# to decide a queued page has been read -- so a dataset that calls them anything else is
# reported as unread however well it reads. `table_fiscal_year` and `column_year` are the
# years the FIGURES are about, which is a different question and never the join key: the
# FY2016 report reprints fiscal 2009's new growth.
FIELDS = ['dataset', 'edition', 'report_fy', 'document', 'page', 'table',
          'table_fiscal_year', 'column_year',
          'label', 'kind', 'levy_percent', 'levy_from_percent', 'valuation', 'tax_rate',
          'tax_levy', 'value', 'share_percent', 'added_valuation', 'new_revenue',
          'change_percent', 'prior_value', 'columns_as_printed', 'repaired',
          'status', 'reconciliation']

# The class rows, as the Assessors print them. `Net of Exempt` is a second line of the
# Commercial and Industrial labels in FY2022 and carries no figures of its own.
CLASS_ROW = re.compile(r'^(residential|open\s*space|commercial|industrial|'
                       r'personal(\s+property)?)\b', re.I)
TOTAL_ROW = re.compile(r'^(totals?|subtotal)\b', re.I)

MONEY = re.compile(r'^\(?[S$]?-?[\d][\d,.]*\)?%?$')


def num(tok):
    """A printed figure, or None. `-0-` is how these pages print a zero."""
    t = (tok or '').strip()
    if t in ('-0-', '-0—', '—0—'):
        return 0.0
    neg = t.startswith('(') and t.endswith(')')
    t = t.strip('()').replace('$', '').replace('S', '').replace('%', '').strip()
    if not re.match(r'^-?[\d][\d,.]*$', t):
        return None
    # Thousands separators only: a lone trailing group of exactly two digits after the
    # last dot is a decimal; everything else that is three digits is a separator.
    parts = re.split(r'[,.]', t)
    # A final group of one or two digits is a decimal fraction whichever mark precedes
    # it. The OCR reads a good many decimal points as commas -- `48,000,00` and
    # `685,000,0` are both on one page of the FY2019 report -- and no thousands
    # separator is ever followed by fewer than three digits, so the shape decides it.
    if len(parts) > 1 and len(parts[-1]) in (1, 2):
        body, frac = ''.join(parts[:-1]), parts[-1]
    elif len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
        body, frac = ''.join(parts), ''
    elif '.' in t and t.count('.') == 1:
        body, frac = t.split('.')
        body = body.replace(',', '')
    else:
        body, frac = ''.join(parts), ''
    if not body.lstrip('-').isdigit():
        return None
    v = float(body + ('.' + frac if frac else ''))
    return -v if neg else v


def digits(s):
    return re.sub(r'\D', '', s or '')


def edit_distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def pages_of(tsv):
    """Every page as lines, top to bottom, each line a list of words with geometry.

    The OCR's `y` grows UPWARD (PDF origin), so reading order is descending y. Getting
    that backwards puts the TOTALS row above the rows it totals, which reads as a table
    with no total at all.
    """
    csv.field_size_limit(10 ** 9)
    out = collections.defaultdict(list)
    with open(tsv) as fh:
        # QUOTE_NONE is not a nicety. A double quote in an OCR word -- `6" main`, a stray
        # mark on a scan -- makes the default reader treat everything up to the NEXT quote
        # as one field, swallowing whole lines with it. On the FY2017 report that silently
        # dropped 2,150 of 15,293 words and every word on page 155, which then read as a
        # blank page. The instrument, not the town.
        for r in csv.DictReader(fh, delimiter='\t', quoting=csv.QUOTE_NONE):
            out[int(r['page'])].append({
                'x': float(r['x']), 'y': float(r['y']), 'w': float(r['w']),
                'text': r['text'], 'cx': float(r['x']) + float(r['w']) / 2,
            })
    pages = {}
    for p, words in out.items():
        words.sort(key=lambda w: -w['y'])
        lines, cur = [], []
        for w in words:
            if cur and abs(cur[-1]['y'] - w['y']) > 0.006:
                lines.append(sorted(cur, key=lambda z: z['x']))
                cur = []
            cur.append(w)
        if cur:
            lines.append(sorted(cur, key=lambda z: z['x']))
        pages[p] = lines
    return pages


def text_of(line):
    return ' '.join(w['text'] for w in line)


def split_label(line):
    """The leading words are the label; the trailing figures are the data."""
    label, vals = [], []
    for w in line:
        if num(w['text']) is not None and MONEY.match(w['text'].strip()):
            vals.append(w)
        elif not vals:
            label.append(w)
        else:
            # A word after the figures have started (a stray `fwd`, `T`) is not a figure.
            continue
    return ' '.join(w['text'] for w in label).strip(), vals


def ruler(rows, gap=0.05):
    """Column centres, clustered from the figures the rows actually printed.

    Built from the data and not from the heading, because a heading word sits over the
    middle of nothing in particular -- and because rule 13b's third rule is that a figure
    is placed by POSITION, never by order: the FY2022 TOTAL row prints three of five
    columns, and read in order every one of them lands under the wrong heading.
    """
    cs = sorted(w['cx'] for _, vals in rows for w in vals)
    if not cs:
        return []
    cols, cur = [], [cs[0]]
    for c in cs[1:]:
        if c - cur[-1] > gap:
            cols.append(cur)
            cur = []
        cur.append(c)
    cols.append(cur)
    return [sum(c) / len(c) for c in cols]


def place(vals, cols):
    """Each figure under the column whose centre it is nearest. Absent stays absent."""
    out = [None] * len(cols)
    raw = [''] * len(cols)
    for w in vals:
        i = min(range(len(cols)), key=lambda k: abs(cols[k] - w['cx']))
        if out[i] is None:
            out[i], raw[i] = num(w['text']), w['text']
    return out, raw


# ---------------------------------------------------------------------------
# The layouts. READ off the page and written down, per rule 13b's fourth rule:
# a column is never named from a word the OCR happened to put above it.

LAYOUT_A = ['levy_percent', 'valuation', 'tax_rate', 'tax_levy']
HEADING_A = 'Property Class | Levy Percent | Valuation by Class | Tax Rate | Tax Levy'

LAYOUT_B = ['levy_percent', 'levy_from_percent', 'valuation', 'tax_rate', 'tax_levy']
HEADING_B = ('CLASS | (b) Levy percentage from LA5 | (c) each percent in col (b) times '
             'Ic above | (d) Valuation by class from LA-5 | (e) Tax Rates (c)/(d) x 1000 '
             '| (f) Levy by class (d) x (e) / 1000')

LAYOUT_TOTVAL = ['value', 'share_percent']
HEADING_TOTVAL = 'Class | Valuation | % of Total Value'

LAYOUT_GROWTH = ['added_valuation', 'tax_rate', 'new_revenue', 'change_percent']
HEADING_GROWTH = 'Fiscal Year | Added Valuation | Tax Rate | New Revenues | Change (%)'

LAYOUT_AVG = ['value', 'prior_value', 'change_percent']
HEADING_AVG = 'Property Type | FY2025 | FY2024 | % Change'


def find_major_class(pages):
    for p, lines in sorted(pages.items()):
        for i, line in enumerate(lines):
            t = text_of(line)
            if re.search(r'Assessments and Revenues by Major', t, re.I):
                return p, lines, i
            if re.search(r'Levy [Pp]ercent(age)?\b', t):
                return p, lines, max(0, i - 1)
    return None, None, None


def read_major_class(edition, doc, pages):
    p, lines, start = find_major_class(pages)
    if p is None:
        return []
    layout, heading = LAYOUT_A, HEADING_A
    for line in lines[start:start + 4]:
        if re.search(r'\(b\)', text_of(line)):
            layout, heading = LAYOUT_B, HEADING_B
    rows = []
    for line in lines[start:]:
        label, vals = split_label(line)
        if not vals:
            continue
        if CLASS_ROW.match(label) or TOTAL_ROW.match(label):
            rows.append((label, vals))
        if TOTAL_ROW.match(label) and label.lower().startswith('total'):
            break
    if not rows:
        return []
    cols = ruler(rows)
    if len(cols) != len(layout):
        return [{'dataset': 'valuation', 'edition': edition, 'document': doc, 'page': p,
                 'table': 'major_class', 'label': '', 'kind': 'refused',
                 'columns_as_printed': heading, 'status': 'check failed',
                 'reconciliation': (f'the page ruled into {len(cols)} columns where the '
                                    f'layout read off it has {len(layout)}; refused '
                                    f'rather than aligned')}]
    out = []
    for label, vals in rows:
        placed, raw = place(vals, cols)
        r = {'dataset': 'valuation', 'edition': edition, 'document': doc, 'page': p,
             'table': 'major_class', 'label': label,
             'kind': 'total' if TOTAL_ROW.match(label) else 'row',
             'columns_as_printed': heading, 'repaired': ''}
        for name, v, rw in zip(layout, placed, raw):
            r[name] = v
            r.setdefault('_raw', {})[name] = rw
        out.append(r)
    return reconcile_major_class(out)


def reconcile_major_class(rows):
    detail = [r for r in rows if r['kind'] == 'row']
    totals = [r for r in rows if r['kind'] == 'total'
              and (r['label'] or '').lower().startswith('total')]
    if not detail or not totals:
        for r in rows:
            r['status'] = 'no check'
            r['reconciliation'] = 'no total printed'
        return rows
    total = totals[-1]
    notes, ok = [], True

    for col, tol in (('valuation', 1.0), ('tax_levy', 1.0)):
        got = sum(r[col] for r in detail if r.get(col) is not None)
        want = total.get(col)
        if want is None:
            notes.append(f'{col}: the TOTALS row prints none')
            ok = False
            continue
        if abs(got - want) > tol:
            fixed = repair(detail, col, want, tol) or repair_total(total, detail, col)
            if fixed:
                notes.append(fixed)
                got = sum(r[col] for r in detail if r.get(col) is not None)
                want = total.get(col)
            if abs(got - want) > tol:
                notes.append(f'{col}: {got:,.2f} against a printed {want:,.2f} '
                             f'({got - want:+,.2f})')
                ok = False
                continue
        notes.append(f'{col}: {got:,.2f} = the printed total')

    pct = sum(r['levy_percent'] for r in detail if r.get('levy_percent') is not None)
    if abs(pct - 100) < 0.02:
        notes.append('levy percent: the class shares sum to 100.0000')
    else:
        notes.append(f'levy percent: the class shares sum to {pct:.4f}, not 100')
        ok = False

    bad = []
    for r in detail:
        v, rate, levy = r.get('valuation'), r.get('tax_rate'), r.get('tax_levy')
        if None in (v, rate, levy):
            continue
        if abs(v * rate / 1000 - levy) > 2.0:
            bad.append(r['label'])
    notes.append('valuation x rate / 1000 = levy holds on every class row' if not bad
                 else 'valuation x rate / 1000 fails on: ' + ', '.join(bad))
    if bad:
        ok = False

    status = 'checked' if ok else 'check failed'
    for r in rows:
        r['status'] = status
        r['reconciliation'] = ' ; '.join(notes)
        r.pop('_raw', None)
    return rows


def repair(detail, col, want, tol):
    """Repair one short cell, and only where the document says the figure TWICE.

    Two statements can name a missing figure. The column's printed total names it by
    subtraction. The row's own identity -- valuation x rate / 1000 = levy -- names it
    independently. A repair is written when the residual is confirmed EITHER by that
    identity agreeing to the penny, or by being within two misread glyphs of what the OCR
    returned; one statement alone is a guess and is refused.

    Three real cases, and each needs a different one of the two:

    * FY2016 residential valuation prints `21,174,263.21`, which is not a valuation at
      all. The column residual gives 1,079,768,102 and the row identity gives
      1,079,768,102.00 from the printed levy. Nothing about the digits is close; the
      arithmetic is exact.
    * FY2020 residential valuation reads `1,04,806,468` -- a dropped digit -- and its
      levy reads `24,455,093.20` for `25,455,093.20`. Both cells are wrong, so the
      identity cannot confirm the first until the second is repaired. The dropped digit
      does it, and the identity then holds on the repaired pair.
    * FY2011's TOTALS cell reads `1,114,2828,889` for `1,114,282,889` -- the misread is
      the CONTROL, not a row. That is handled by `repair_total`.
    """
    best = None
    for r in detail:
        others = sum(o[col] for o in detail if o is not r and o.get(col) is not None)
        implied = want - others
        have = r.get(col)
        if have is None or abs(have - implied) < tol:
            continue
        rate = r.get('tax_rate')
        identity = None
        if rate:
            if col == 'valuation' and r.get('tax_levy') is not None:
                identity = r['tax_levy'] * 1000 / rate
            elif col == 'tax_levy' and r.get('valuation') is not None:
                identity = r['valuation'] * rate / 1000
        raw = (r.get('_raw') or {}).get(col, '')
        agrees = identity is not None and abs(identity - implied) <= 2.0
        dist = edit_distance(digits(raw), digits(f'{implied:.0f}'))
        score = 0 if agrees else dist
        if score > 2:
            continue
        why = ('the row identity gives the same figure to the penny' if agrees
               else f'the OCR text is {dist} misread glyph(s) from it')
        if best is None or score < best[0]:
            best = (score, r, implied, raw, why)
    if best is None:
        return None
    _, r, implied, raw, why = best
    r[col] = implied
    r['repaired'] = (f'{col}: OCR read {raw!r}; the printed column total requires '
                     f'{implied:,.2f} and {why}')
    return (f'{col}: {r["label"]} repaired from {raw!r} to {implied:,.2f} '
            f'-- named by the printed total, and {why}')


def repair_total(total, detail, col):
    """The misread is sometimes the CONTROL itself.

    FY2011 prints its total valuation as `1,114,2828,889`. The four class rows sum to
    1,114,282,889, which is one glyph away, and the FY2016 report's own Valuation and Tax
    History prints 1,114,282,889 against fiscal 2011 -- so the figure is in this archive
    twice and the total cell is what misread. Repaired only at an edit distance of two or
    less, because a control repaired to match the rows it is supposed to test would
    otherwise prove nothing.
    """
    got = sum(r[col] for r in detail if r.get(col) is not None)
    raw = (total.get('_raw') or {}).get(col, '')
    if total.get(col) is None or not raw:
        return None
    if edit_distance(digits(raw), digits(f'{got:.0f}')) > 2:
        return None
    total[col] = got
    total['repaired'] = (f'{col}: the TOTALS cell read {raw!r}; the class rows sum to '
                         f'{got:,.2f}, one or two glyphs away')
    return (f'{col}: the printed TOTALS cell {raw!r} is itself the misread -- the class '
            f'rows sum to {got:,.2f}')


HEADING_LA4 = ('Property Type | Parcel Count | Class1 Residential | Class2 Open Space '
               '| Class3 Commercial | Class4 Industrial | Class5 Pers Prop')
LA4_COLUMNS = ['Parcel Count', 'Class1 Residential', 'Class3 Commercial',
               'Class4 Industrial', 'Class5 Pers Prop']


def read_la4(edition, doc, pages):
    """The TOTALS line of the state LA4 the Assessors reprint, and nothing else.

    The full LA4 is not read here and should not be read this way: three of its rows
    carry a SECOND parcel-count box (the form says so in its own footnote -- mixed-use
    parcels on the left, 100% Chapter land on the right), so the page has a column that
    exists on three lines out of twenty-five. That is a table to read on its own terms,
    later.

    What is read is the one line this archive needs today: the column TOTALS, and the
    `Real and Personal Property Total Value` printed beneath them, which the four class
    columns foot to exactly. It is a second, independent statement of the same four
    figures the Assessors print on their own page -- and it is what settles which of two
    cells there misread. `Class2 Open Space` prints nothing in either year, so five
    figures appear where six headings do; they are named from the heading above, read and
    written down, never from their order.
    """
    for p, lines in sorted(pages.items()):
        tv = [line for line in lines
              if text_of(line).startswith('Real and Personal Property Total Value')]
        tot = [line for line in lines if text_of(line).startswith('TOTALS')]
        if not tv or not tot:
            continue
        _, tvals = split_label(tv[0])
        _, cvals = split_label(tot[0])
        if len(tvals) != 1 or len(cvals) != len(LA4_COLUMNS):
            continue
        total = num(tvals[0]['text'])
        figures = [num(w['text']) for w in cvals]
        classes = figures[1:]
        got = sum(classes)
        ok = abs(got - total) < 1
        note = (f'the four class columns sum to {got:,.0f} = the printed Real and '
                f'Personal Property Total Value' if ok else
                f'the four class columns sum to {got:,.0f} against a printed '
                f'{total:,.0f} ({got - total:+,.0f})')
        out = []
        for name, v in zip(LA4_COLUMNS, figures):
            out.append({'dataset': 'valuation', 'edition': edition, 'document': doc,
                        'page': p, 'table': 'la4_totals', 'label': name, 'kind': 'total',
                        'columns_as_printed': HEADING_LA4, 'repaired': '',
                        'value': v, 'status': 'checked' if ok else 'check failed',
                        'reconciliation': note})
        out.append({'dataset': 'valuation', 'edition': edition, 'document': doc,
                    'page': p, 'table': 'la4_totals',
                    'label': 'Real and Personal Property Total Value', 'kind': 'total',
                    'columns_as_printed': HEADING_LA4, 'repaired': '', 'value': total,
                    'status': 'checked' if ok else 'check failed', 'reconciliation': note})
        return out
    return []


def read_total_valuation(edition, doc, pages, la4=None):
    """The FY2024 / FY2025 layout: Class | Valuation | % of Total Value."""
    for p, lines in sorted(pages.items()):
        idx = [i for i, line in enumerate(lines)
               if re.match(r'^\s*(Total Valuation)\b', text_of(line))
               and '%' in text_of(line)]
        if not idx:
            continue
        end = idx[0]
        rows = []
        for line in lines[max(0, end - 5):end + 1]:
            label, vals = split_label(line)
            if len(vals) >= 2 and (CLASS_ROW.match(label)
                                   or label.lower().startswith('total valuation')):
                rows.append((label, vals))
        if len(rows) < 3:
            continue
        cols = ruler(rows)
        if len(cols) != 2:
            continue
        out = []
        for label, vals in rows:
            placed, raw = place(vals, cols)
            r = {'dataset': 'valuation', 'edition': edition, 'document': doc, 'page': p,
                 'table': 'total_valuation', 'label': label,
                 'kind': 'total' if label.lower().startswith('total') else 'row',
                 'columns_as_printed': HEADING_TOTVAL, 'repaired': '',
                 'value': placed[0], 'share_percent': placed[1]}
            r.setdefault('_raw', {})['value'] = raw[0]
            out.append(r)
        return reconcile_total_valuation(out, la4)
    return []


def reconcile_total_valuation(rows, la4=None):
    detail = [r for r in rows if r['kind'] == 'row']
    totals = [r for r in rows if r['kind'] == 'total']
    notes, ok = [], True
    if not totals:
        for r in rows:
            r['status'], r['reconciliation'] = 'no check', 'no total printed'
        return rows
    want = totals[-1]['value']
    got = sum(r['value'] for r in detail if r.get('value') is not None)
    if abs(got - want) > 1:
        fixed = repair_from_la4(detail, want, la4) or repair_simple(detail, 'value', want)
        if fixed:
            notes.append(fixed)
            got = sum(r['value'] for r in detail if r.get('value') is not None)
    if abs(got - want) <= 1:
        notes.append(f'valuation: {got:,.0f} = the printed Total Valuation')
    else:
        notes.append(f'valuation: {got:,.0f} against a printed {want:,.0f} '
                     f'({got - want:+,.0f})')
        ok = False
    for r in rows:
        r['status'] = 'checked' if ok else 'check failed'
        r['reconciliation'] = ' ; '.join(notes)
        r.pop('_raw', None)
    return rows


LA4_CLASS = {'residential': 'Class1 Residential', 'commercial': 'Class3 Commercial',
             'industrial': 'Class4 Industrial', 'personal property': 'Class5 Pers Prop'}


def repair_from_la4(detail, want, la4):
    """Two cells are each one glyph from explaining the residual. A document decides.

    FY2025's Assessors page misses its own printed Total Valuation by $2,000, and both
    `$97,763,006` (Commercial) and `$32,627,700` (Industrial) are a single digit away from
    closing it. Choosing between them by edit distance is a coin toss, and picking one
    would be this project doing exactly what rule 13 forbids -- publishing a derived
    choice as an observation.

    The LA4 reprinted on the next page decides it: its Class3 Commercial column prints
    97,763,006, matching the Assessors' page, and its Class4 Industrial column prints
    32,625,700, which is the figure the Total Valuation requires. So the industrial cell
    is what misread, and the repair is a figure the document states rather than one we
    inferred.
    """
    if not la4:
        return None
    by = {r['label']: r['value'] for r in la4 if r.get('value') is not None}
    for r in detail:
        key = LA4_CLASS.get((r['label'] or '').strip().lower())
        if not key or key not in by or r.get('value') is None:
            continue
        if abs(r['value'] - by[key]) < 1:
            continue
        others = sum(o['value'] for o in detail if o is not r and o.get('value') is not None)
        if abs(others + by[key] - want) > 1:
            continue
        raw = (r.get('_raw') or {}).get('value', '')
        r['repaired'] = (f'value: the Assessors page reads {raw!r}; the LA4 reprinted in '
                         f'the same report prints {by[key]:,.0f} under {key}, which is '
                         f'what the printed Total Valuation requires')
        r['value'] = by[key]
        return (f'value: {r["label"]} repaired from {raw!r} to {by[key]:,.0f} -- the LA4 '
                f'in the same report prints it under {key}, and it closes the total')
    return None


def repair_simple(detail, col, want):
    """One short cell named by the printed total, within two misread glyphs of it.

    FY2025 needs one: Industrial reads `$32,627,700` on the Assessors' page and the
    printed Total Valuation requires `32,625,700`. The LA4 form reprinted overleaf on
    page 34 prints `32,625,700` in its Class4 column and foots to the same
    `2,360,706,780`, so the repaired digit is what the document says twice.
    """
    best = None
    for r in detail:
        others = sum(o[col] for o in detail if o is not r and o.get(col) is not None)
        implied = want - others
        raw = (r.get('_raw') or {}).get(col, '')
        if r.get(col) is None or abs(r[col] - implied) < 1:
            continue
        dist = edit_distance(digits(raw), digits(f'{implied:.0f}'))
        if dist > 2:
            continue
        if best is None or dist < best[0]:
            best = (dist, r, implied, raw, 1)
        elif dist == best[0]:
            best = best[:4] + (best[4] + 1,)
    if best is not None and best[4] > 1:
        # Two cells are each the same distance from explaining the residual. Choosing
        # one would be a guess wearing the clothes of a measurement.
        return (f'{col}: refused to repair -- {best[4]} cells are each '
                f'{best[0]} misread glyph(s) from closing the residual, and nothing '
                f'here says which')
    if best is not None:
        _, r, implied, raw, _ = best
        r['repaired'] = (f'{col}: OCR read {raw!r}; the printed Total Valuation '
                         f'requires {implied:,.0f}')
        return (f'{col}: {r["label"]} repaired from {raw!r} to {implied:,.0f} '
                f'-- named by the printed Total Valuation')
    return None


def read_new_growth(edition, doc, pages):
    for p, lines in sorted(pages.items()):
        idx = [i for i, line in enumerate(lines)
               if re.match(r'^\s*New Growth Revenue\s*$', text_of(line))]
        if not idx:
            continue
        rows = []
        for line in lines[idx[0]:]:
            label, vals = split_label(line)
            if label or len(vals) < 4:
                if rows:
                    break
                continue
            year = num(vals[0]['text'])
            if year is None or not 1990 < year < 2100:
                if rows:
                    break
                continue
            rows.append((str(int(year)), vals[1:]))
        if len(rows) < 3:
            continue
        cols = ruler(rows)
        if len(cols) != 4:
            continue
        out = []
        for label, vals in rows:
            placed, _ = place(vals, cols)
            out.append({'dataset': 'valuation', 'edition': edition, 'document': doc,
                        'page': p, 'table': 'new_growth', 'label': label,
                        'table_fiscal_year': label, 'kind': 'row',
                        'columns_as_printed': HEADING_GROWTH, 'repaired': '',
                        'added_valuation': placed[0], 'tax_rate': placed[1],
                        'new_revenue': placed[2], 'change_percent': placed[3]})
        return reconcile_new_growth(out)
    return []


def reconcile_new_growth(rows):
    """No printed total. The control is the row's own arithmetic, stated by the columns.

    `Added Valuation x Tax Rate / 1000 = New Revenues` is an identity the table asserts
    about itself, so a misread digit in any of the three cannot survive it. Where the
    printed tax rate is the NEXT year's -- the convention changes between editions and
    the catalogue notes it -- the row is reported as failing rather than quietly rounded
    past.
    """
    notes, bad = [], []
    for r in rows:
        v, rate, rev = r['added_valuation'], r['tax_rate'], r['new_revenue']
        r['status'] = 'checked'
        if None in (v, rate, rev):
            bad.append(f'{r["label"]} (a cell did not read)')
            r['status'] = 'check failed'
            continue
        if abs(v * rate / 1000 - rev) > max(2.0, abs(rev) * 0.005):
            bad.append(f'{r["label"]} ({v * rate / 1000:,.0f} against a printed '
                       f'{rev:,.0f})')
            r['status'] = 'check failed'
    n = len(rows)
    if bad:
        notes.append(f'added valuation x rate / 1000 = new revenue holds on '
                     f'{n - len(bad)} of {n} rows; fails on ' + '; '.join(bad))
    else:
        notes.append(f'added valuation x rate / 1000 = new revenue holds on all '
                     f'{n} rows')
    for r in rows:
        r['reconciliation'] = ' ; '.join(notes)
    return rows


def read_avg_values(edition, doc, pages):
    """FY2024 / FY2025: average single-family and commercial value, two years side by
    side with the percentage change printed. The identity is the printed change."""
    out = []
    for p, lines in sorted(pages.items()):
        hdr = [i for i, line in enumerate(lines)
               if re.match(r'^\s*Property Type\s+FY\d{4}\s+FY\d{4}', text_of(line))]
        if not hdr:
            continue
        head = text_of(lines[hdr[0]])
        years = re.findall(r'FY(\d{4})', head)
        rows = []
        for line in lines[hdr[0] + 1:hdr[0] + 5]:
            label, vals = split_label(line)
            if not re.match(r'^Avg\.', label) or len(vals) < 3:
                continue
            rows.append((label, vals))
        if not rows:
            continue
        cols = ruler(rows)
        if len(cols) != 3:
            continue
        notes, bad = [], []
        for label, vals in rows:
            placed, _ = place(vals, cols)
            cur, prior, chg = placed
            r = {'dataset': 'valuation', 'edition': edition, 'document': doc, 'page': p,
                 'table': 'avg_values', 'label': label, 'kind': 'row',
                 'table_fiscal_year': years[0] if years else '',
                 'columns_as_printed': head, 'repaired': '',
                 'value': cur, 'prior_value': prior, 'change_percent': chg}
            if None not in (cur, prior, chg) and prior:
                if abs((cur - prior) / prior * 100 - chg) > 0.6:
                    bad.append(f'{label} ({(cur - prior) / prior * 100:.1f}% against a '
                               f'printed {chg}%)')
            out.append(r)
        notes.append('the printed %% change is what the two figures give, on all '
                     '%d rows' % len(rows) if not bad
                     else 'the printed %% change disagrees on: ' + '; '.join(bad))
        for r in out:
            r['status'] = 'checked' if not bad else 'check failed'
            r['reconciliation'] = ' ; '.join(notes)
        return out
    return []


def cross_edition_new_growth(rows):
    """Nine editions reprint the same new-growth history. They must agree, and do not.

    This is a control no single page can give: the FY2011 report prints fiscal 2011's
    added valuation, and so do the FY2012 through FY2016 reports. A figure restated in
    six documents is either the same figure six times or a finding. Reported here rather
    than folded into a row's status, because a disagreement BETWEEN documents is a fact
    about the documents and not a defect in either row.
    """
    seen = collections.defaultdict(dict)
    for r in rows:
        if r['table'] != 'new_growth' or r['added_valuation'] in (None, ''):
            continue
        seen[r['label']][r['edition']] = (r['added_valuation'], r['new_revenue'])
    out, bad = [], 0
    for year in sorted(seen):
        vals = seen[year]
        distinct = sorted({v[0] for v in vals.values()})
        if len(distinct) > 1:
            bad += 1
            where = '; '.join(f'{e} says {v[0]:,.0f}' for e, v in sorted(vals.items()))
            out.append(f'  !! fiscal {year}: {where}')
    head = (f'new growth restated across editions: {len(seen)} fiscal years, '
            f'{len(seen) - bad} agree in every report that prints them, {bad} do not')
    return [head] + out


LEVY_ROWS = re.compile(r'^(Prior Year Levy Limit|2.?.?%? Increase|22% Increase|'
                       r'Estimated New Growth|Debt Exclusion|Taxes:?\s*Total)', re.I)


def read_levy_buildup(edition, doc, pages):
    """How the levy limit is built, the one year the town prints the arithmetic.

    Proposition 2 1/2 says the levy limit is last year's limit, plus 2.5% of it, plus
    certified new growth; a debt exclusion sits outside the limit and is added after. The
    FY2024 Finance Committee report prints that sum for three years side by side, and it
    is the only place in sixteen annual reports that does -- searched for by its first
    row, `Prior Year Levy Limit`, which appears on one page of one edition.

    Each YEAR is a column and each column is checked on its own: the four components
    against the `Taxes: Total` printed beneath them. FY22 and FY23 foot exactly. FY24
    does not, by $55,184.33, and the printed total is the figure corroborated by the
    report's own percentage column -- so the shortfall is in the components, and which
    one is not established here.
    """
    for p, lines in sorted(pages.items()):
        rows = [line for line in lines if LEVY_ROWS.match(text_of(line).strip())]
        if len(rows) < 5:
            continue
        head = ''
        for line in lines:
            t = text_of(line).strip()
            if re.match(r'^FY\d\d\s+\w+\s+FY\d\d', t):
                head = t
        years = re.findall(r'FY(\d\d)', head)
        # The label is the row's NAME, not the whole printed line -- three year columns
        # and two percentages follow it on the same line. `2 1/2% Increase` is what the
        # page shows; the OCR renders the vulgar fraction as `22% Increase`, and the
        # printed text is kept as it read rather than silently corrected.
        pairs = [(LEVY_ROWS.match(text_of(line).strip()).group(1), money_words_v(line))
                 for line in rows]
        # Five columns are printed: three years and two percentage changes, and the
        # percentages are excluded above. Reading the remaining three IN ORDER is only
        # safe because every row prints all three -- so that is asserted rather than
        # assumed, and a page where any row is short is refused. The OCR boxes here are
        # not alignable: `$ 27,131,063.00` arrives as one box and `$` `2,831,932.29` as
        # two, on the same column.
        if any(len(v) != 3 for _, v in pairs):
            short = [t for t, v in pairs if len(v) != 3]
            return [{'dataset': 'valuation', 'edition': edition, 'document': doc,
                     'page': p, 'table': 'levy_buildup', 'label': '', 'kind': 'refused',
                     'status': 'check failed',
                     'reconciliation': ('the three year columns are read in order, which '
                                        'requires every row to print all three; these do '
                                        'not: ' + '; '.join(short))}]
        out, notes = [], []
        table = {label: [num(w['text'].replace(' ', '')) for w in vals]
                 for label, vals in pairs}
        totals = [v for k, v in table.items() if re.match(r'^Taxes', k, re.I)]
        if not totals:
            continue
        total = totals[0]
        ok_all = True
        for i, want in enumerate(total):
            parts = [v[i] for k, v in table.items()
                     if not re.match(r'^Taxes', k, re.I) and v[i] is not None]
            if want is None or len(parts) < 4:
                notes.append(f'column {i + 1}: not every component read')
                ok_all = False
                continue
            got = sum(parts)
            year = 'FY' + years[i] if i < len(years) else f'column {i + 1}'
            if abs(got - want) < 1:
                notes.append(f'{year}: the four components sum to {got:,.2f} = the '
                             f'printed Taxes: Total')
            else:
                notes.append(f'{year}: the four components sum to {got:,.2f} against a '
                             f'printed {want:,.2f} ({got - want:+,.2f})')
                ok_all = False
        for label, vals in pairs:
            placed = table[label]
            for i in range(3):
                if placed[i] is None:
                    continue
                out.append({'dataset': 'valuation', 'edition': edition, 'document': doc,
                            'page': p, 'table': 'levy_buildup', 'label': label,
                            'column_year': 'FY' + years[i] if i < len(years) else '',
                            'kind': 'total' if re.match(r'^Taxes', label, re.I) else 'row',
                            'columns_as_printed': head, 'repaired': '',
                            'value': placed[i],
                            'status': 'checked' if ok_all else 'check failed',
                            'reconciliation': ' ; '.join(notes)})
        return out
    return []


def money_words_v(line):
    """The figures on a levy line, with a lone `$` dropped and percentages excluded."""
    out = []
    for w in line:
        t = w['text'].strip()
        t = t.replace(' ', '')
        if t in ('$', 'S') or t.endswith('%') or not t:
            continue
        if num(t) is not None and MONEY.match(t):
            out.append(w)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='fail if the written file no longer reproduces')
    args = ap.parse_args()

    rows, refused = [], []
    for tsv in sorted(glob.glob(os.path.join(OCR, '*annual-town-report.tsv'))):
        name = os.path.basename(tsv)
        m = re.search(r'fy-?(\d{4})', name)
        if not m:
            continue
        edition = 'FY' + m.group(1)
        doc = name.replace('.tsv', '.pdf')
        pages = pages_of(tsv)
        la4 = read_la4(edition, doc, pages)
        found = list(la4)
        found += read_total_valuation(edition, doc, pages, la4)
        for reader in (read_major_class, read_new_growth, read_avg_values,
                       read_levy_buildup):
            found += reader(edition, doc, pages)
        for r in found:
            r['report_fy'] = m.group(1)
            r.setdefault('table_fiscal_year', m.group(1))
            if r.get('kind') == 'refused':
                r['state'] = 'refused'
                refused.append({k: r.get(k, '') for k in REFUSED_FIELDS})
            else:
                rows.append({k: r.get(k, '') for k in FIELDS})

    rows.sort(key=lambda r: (r['edition'], r['table'], int(r['page'])))
    refused.sort(key=lambda r: (r['edition'], int(r['page'])))
    cross = cross_edition_new_growth(rows)

    if args.check:
        for path, want in ((OUT, rows), (REFUSED, refused)):
            if not os.path.exists(path):
                sys.exit(f'{path} does not exist')
            have = [dict(h) for h in csv.DictReader(open(path))]
            if have != [{k: ('' if v is None else str(v)) for k, v in r.items()}
                        for r in want]:
                sys.exit(f'{path} is stale -- re-run scripts/extract_valuation.py')
        print(f'{OUT}: {len(rows)} rows, {len(refused)} refused, reproduces')
        return

    with open(OUT, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    with open(REFUSED, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=REFUSED_FIELDS)
        w.writeheader()
        w.writerows(refused)

    by = collections.defaultdict(list)
    for r in rows:
        by[(r['table'], r['edition'])].append(r)
    for line in cross:
        print(line)
    print()
    for table in ('major_class', 'total_valuation', 'la4_totals',
                  'new_growth', 'avg_values', 'levy_buildup'):
        eds = [(e, rs) for (t, e), rs in sorted(by.items()) if t == table]
        n_ok = sum(1 for _, rs in eds
                   if not any(r['status'] == 'check failed' for r in rs))
        print(f'{table}: {len(eds)} editions, {n_ok} checked, '
              f'{len(eds) - n_ok} not')
        for e, rs in eds:
            failed = sum(1 for r in rs if r['status'] == 'check failed')
            mark = '  ' if not failed else '!!'
            print(f'  {mark} {e} p{rs[0]["page"]:>3}  {len(rs):>2} rows  '
                  f'{failed} failed  {rs[0]["reconciliation"][:140]}')
    for r in refused:
        print(f'!! {r["edition"]} p{int(r["page"]):>3} {r["table"]} REFUSED, not filed '
              f'as a reading  {r["reconciliation"][:100]}')
    print(f'\nwrote {OUT}: {len(rows)} rows; {REFUSED}: {len(refused)} refused')


if __name__ == '__main__':
    main()
