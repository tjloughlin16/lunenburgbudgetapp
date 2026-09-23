#!/usr/bin/env python3
"""The RECEIVABLES SUMMARY out of the annual town reports, proved against its own total.

WHAT THE PAGES ACTUALLY ARE
---------------------------
`annual-report-pages.csv` calls 29 pages `receivables`, and that column is a guess off a
heading. Twenty-seven of them are one table, printed under three lines the town sets
itself:

    TOWN OF LUNENBURG
    FY2022 COLLECTION OF TAXES
    RECEIVABLES SUMMARY
    JUNE 30, 2022

It is the Collector's receivable control: one row per tax levy and per charge, running
BALANCE FORWARD -> COMMITTMENTS -> ABATEMENTS -> PAYMENTS -> REFUNDS -> TRANSFER ->
ADJUSTMENTS -> BALANCES, across two or three pages, ending in a printed GRAND TOTAL.

The other two are not that table and are not read here. FY2024 page 21 is a `Combining
Balance Sheet - Enterprise Funds` on which the word `Receivables:` is a stub heading, and
FY2024 page 22 is a `General Fund Accounts Receivable Detail` -- a different table with
different columns.

THE THREE THINGS THAT MAKE THESE PAGES HARD
-------------------------------------------
**1. The column ORDER changes between years.** FY2016 and FY2017 print
FORWARD COMMITTMENTS ADJUSTMENTS REFUNDS PAYMENTS ABATEMENTS TRANSFER BALANCES. FY2020
onward print FORWARD COMMITTMENTS ABATEMENTS PAYMENTS REFUNDS TRANSFER ADJUSTMENTS
BALANCES. Same eight names, two different orders, and nothing on the page says so. So the
header is READ, per page, and never assumed -- rule 13b's fourth rule, and the reason a
year whose header cannot be read is refused rather than aligned to a neighbour's.

**2. An absent column prints nothing.** Most rows carry three or four figures out of
eight. Taking the figures in order puts every one of them under the wrong heading from the
first gap onward, so each figure is placed by the COLUMN POSITION it is nearest.

**3. The header itself is sometimes one observation over several columns.** FY2024 page 38
returns `COMMITIMENTS ABATEMENTS` and `TRANSFER ADJUSTMENTS BALANCES` as single boxes, and
splitting those proportionally is exactly the invention rule 13b forbids. Instead the
page's readable anchors -- the header words that DID come back one to a box -- are fitted
to a page of the same year whose header is complete, and the columns are carried across by
that measured map. A page with fewer than two anchors is refused.

THE PROOF
---------
Two identities, both stated by the document, both checked:

    forward + committments + abatements + payments + refunds + transfer + adjustments
        =  BALANCES                                              (every row)

    the eight column sums of every detail row  =  the printed GRAND TOTAL   (every year)

The second is the one that matters. A figure dropped, a figure misread, or a column
misnamed all show up there, and a year that does not tie on all eight columns is NOT
written: it is recorded in `receivables-reconciliation.csv` with the column that failed
and by how much. Nothing published here was reconciled by hand.

WHAT IS SURPRISING ABOUT THE SOURCE is written down in `notes/findings/RECEIVABLES.md`,
including the two pages that are not this table, the year the column order changes, the
stale `FY2021` heading FY2023 and FY2024 both carry, the $13,300.00 step between FY2017's
closing balance and FY2018's opening one, and the five corrected boxes.

Outputs
-------
    sources/data/receivables.csv                 -- the detail rows, years that tie only
    sources/data/receivables-reconciliation.csv  -- every year, tied or not, and why

    python3 scripts/extract_receivables.py            # write
    python3 scripts/extract_receivables.py --check    # fail if either has gone stale
"""
import collections
import csv
import glob
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from read_trust_table import MONEY, money, skew, split_merged  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
OUT_ROWS = os.path.join(ROOT, 'sources', 'data', 'receivables.csv')
OUT_RECON = os.path.join(ROOT, 'sources', 'data', 'receivables-reconciliation.csv')

TOL = 0.02

# FIVE BOXES IN FIFTEEN THOUSAND, EACH ONE LOOKED AT ON THE RENDERED PAGE.
#
# Rule 13c: a matcher that fails is a statement about OUR INSTRUMENT, not about the town.
# Each of these is a figure the document prints perfectly clearly and the scanner returned
# wrong, and each was found the same way -- the year missed its own GRAND TOTAL by exactly
# one figure, which is the whole reason the control total is worth reconciling to. Every
# one was then settled by rendering the page and reading it:
#
#   swift scripts/render_pdf_page.swift <the report>.pdf <page> /tmp/p.png
#
# and none is written down here on inference. Four are dropped brackets -- these pages
# print negative figures in red parentheses and the scanner keeps the red and loses the
# brackets -- and the fifth is a `$` read as a `5`. A correction is addressed to a box, by
# the page and the coordinates the scanner gave it, so it cannot silently start applying
# to something else.
#
#   (report stem, page, x, y): (value, what the page prints, what the scanner returned)
CORRECTIONS = {
    ('4124-fy-2017-annual-town-report', 45, 0.72965, 0.38534):
        (-15951.34, '($15,951.34)', '$15,951.34'),
    ('4125-fy-2018-annual-town-report', 52, 0.66860, 0.56203):
        (-1106.89, '($1,106.89)', '(51,106.89)'),
    ('4129-fy-2022-annual-town-report', 49, 0.66566, 0.54295):
        (-14434655.16, '($14,434,655.16)', '$14,434,655.16'),
    ('4131-fy-2023-annual-town-report', 55, 0.67733, 0.19173):
        (-2092.75, '(2,092.75)', '2.092.75'),
    ('4131-fy-2023-annual-town-report', 55, 0.85029, 0.35902):
        (47179.26, '47,179.26', '7.179.2'),
}

# The eight money columns, by the name the town prints over each. A header box is accepted
# only when its letters reduce to exactly one of these -- `COMMITIMENTS`, `ADIUSTMENTS`
# and `ADJUSTM` are the scanner's spellings of three of them, and a box holding two names
# reduces to neither and anchors nothing.
COLUMNS = ('balance_forward', 'commitments', 'abatements', 'payments',
           'refunds', 'transfer', 'adjustments', 'balance')
LABEL_COL = 'fiscal_year'
EXACT = {
    'FORWARD': 'balance_forward',
    'ABATEMENTS': 'abatements',
    'PAYMENTS': 'payments',
    'REFUNDS': 'refunds',
    'TRANSFER': 'transfer',
    'BALANCES': 'balance',
}
# The scanner's spellings of three headings, each one letter or so adrift and none of
# them ambiguous: `COMMITIMENTS`, `ADIUSTMENTS`, `ADJUSTM` cut off at the page edge, and
# FY2015's `DJUSTMENT` with its A missing.
PREFIX = (('COMMIT', 'commitments'), ('ADJUST', 'adjustments'),
          ('ADIUST', 'adjustments'), ('DJUST', 'adjustments'))
TITLE = ('TOWN OF LUNENBURG', 'COLLECTION OF TAXES', 'RECEIVABLES SUMMARY', 'JUNE 30')
MONEY_LOOKING = re.compile(r'\d[\d.,]*[.,]\d\d')


def word_column(w):
    if w in EXACT:
        return EXACT[w]
    for pre, name in PREFIX:
        if w.startswith(pre):
            return name
    return None


def heading(text):
    """Every column this header box names, left to right.

    One box often holds two headings -- `COMMITTMENTS ADJUSTMENTS` in FY2016 and FY2017,
    `COMMITIMENTS ABATEMENTS` in FY2024 -- and in some years EVERY page merges the same
    pair, so no page of that year prints all eight one to a box. Such a box still tells
    us two true things: which names are there, and in what order. What it cannot tell us
    is where either column sits, and splitting its width between them is the proportional
    guess rule 13b forbids. So a merged box NAMES but does not ANCHOR.
    """
    words = re.findall(r'[A-Za-z]+', text.upper())
    if words == ['FISCAL', 'YEAR']:
        return [LABEL_COL]
    named = [word_column(w) for w in words]
    return named if named and all(named) else []


def figure(text):
    """The text of a box as a figure, or None.

    TWO CHARACTERS AT THE END OF A TOKEN COST A WHOLE YEAR EACH, silently. FY2021 page 47
    returns `$3,362.61.` for the balance brought forward on tax liens and page 48 returns
    `($170,480.35]` for a payment; neither matches a figure, so neither was placed in a
    column, and each year missed its own GRAND TOTAL by exactly that amount. Not a
    misread figure -- no figure at all, which is the loss that leaves no trace.

    Both normalisations are safe in the only sense that matters: they cannot change which
    digits are present, or whether the figure was bracketed.
    """
    t = text.strip()
    if t.startswith('(') and t[-1:] in ']}|1':
        t = t[:-1] + ')'
    t = t.rstrip('.,')
    if t.endswith(')'):
        t = t.rstrip('.,)') + ')'
    if not MONEY.match(t):
        return None
    try:
        return money(t)
    except ValueError:
        return None


def load(path):
    pages = collections.defaultdict(list)
    with open(path) as fh:
        for row in csv.DictReader(fh, delimiter='\t', quoting=csv.QUOTE_NONE):
            for k in ('x', 'y', 'w', 'h'):
                row[k] = float(row[k])
            row['page'] = int(row['page'])
            pages[row['page']].append(row)
    return pages


def table_pages(pages):
    """Pages of one report that carry the RECEIVABLES SUMMARY table.

    THE LAST PAGE OFTEN DOES NOT REPEAT THE HEADING. FY2015 page 45 and FY2025 page 41
    open straight into `OTHER EXCISE TAXES` and end in the GRAND TOTAL, and looking only
    for the heading loses the control total and with it the whole year. So the run is
    extended over any following page that prints a GRAND TOTAL and no title line of its
    own -- which is what a continuation of this table looks like and what the start of
    any other table does not.
    """
    titled = sorted(p for p, boxes in pages.items()
                    if any('RECEIVABLES SUMMARY' in b['text'] for b in boxes))
    if not titled:
        return []
    run = list(titled)
    p = run[-1] + 1
    while p in pages:
        boxes = pages[p]
        if any(t in b['text'] for b in boxes for t in TITLE):
            break
        if not any(b['text'].strip().upper().startswith('GRAND TOTAL') for b in boxes):
            break
        run.append(p)
        p += 1
    return run


def page_header(boxes, Y):
    """The header boxes of one page, and the y below which the data starts.

    The header sits under the four title lines and over the first figure. Every box in
    that band whose letters name exactly one column is an ANCHOR: a centre, in this page's
    own coordinates, for the column it names.
    """
    vals = [b for b in boxes if figure(b['text']) is not None]
    if not vals:
        return {}, None
    titles = [b for b in boxes if any(t in b['text'] for t in TITLE)]
    top = min(Y(b) for b in titles) if titles else 1.0
    first_val = max(Y(b) for b in vals)
    anchors, order = {}, []
    for b in sorted(boxes, key=lambda b: b['x']):
        if not (first_val < Y(b) < top):
            continue
        names = heading(b['text'])
        if not names:
            continue
        order.extend(n for n in names if n != LABEL_COL)
        if len(names) == 1 and names[0] not in anchors:
            anchors[names[0]] = b['x'] + b['w'] / 2.0
    return anchors, order, first_val


def ruler(anchors, order):
    """Column centres where the header named every column but anchored only some.

    The eight columns of this table are set on a near-uniform pitch, so the anchors that
    DID come back one to a box measure that pitch: a least-squares line through
    (printed position, centre) predicts the ones that did not, and its residual on the
    anchors says how well the page actually supports it. This is still reading the
    header -- the names and their order come off the page, only the missing centres are
    interpolated between measured ones -- and the GRAND TOTAL is what decides whether it
    was read right.

    Refused unless the header named all eight columns exactly once and anchored three.
    """
    if sorted(order) != sorted(COLUMNS) or len(anchors) < 3:
        return None, None
    idx = {c: i for i, c in enumerate(order)}
    xs = [idx[c] for c in anchors if c in idx]
    ys = [anchors[c] for c in anchors if c in idx]
    if len(xs) < 3:
        return None, None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return None, None
    a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    b = my - a * mx
    resid = max(abs(a * x + b - y) for x, y in zip(xs, ys))
    out = dict(anchors)
    for c in COLUMNS:
        out.setdefault(c, a * idx[c] + b)
    if LABEL_COL in anchors:
        out[LABEL_COL] = anchors[LABEL_COL]
    return out, resid


def fit(anchors, reference):
    """A page's column centres, carried from a page of the same year by a measured map.

    Shared anchors give `x_page = a * x_reference + b` by least squares. Two are enough
    for a line and two is the floor; a page with fewer is refused rather than guessed at.
    """
    shared = sorted(set(anchors) & set(reference))
    if len(shared) < 2:
        return None, None
    xs = [reference[k] for k in shared]
    ys = [anchors[k] for k in shared]
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return None, None
    a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    b = my - a * mx
    resid = max(abs(a * x + b - y) for x, y in zip(xs, ys))
    return {k: a * v + b for k, v in reference.items()}, resid


def read_page(boxes, centres, Y, first_val, stem, page):
    """Rows of one page: (label, {column: value}), placed by position and never by order."""
    order = [LABEL_COL] + list(COLUMNS)
    order = [c for c in order if c in centres]

    def column_of(b):
        c = b['x'] + b['w'] if figure(b['text']) is not None else b['x'] + b['w'] / 2.0
        return min(order, key=lambda k: abs(centres[k] - c))

    body = [b for b in boxes if Y(b) <= first_val + 1e-9]
    if not body:
        return [], 0
    # Refine each money column's centre to the median RIGHT EDGE of the figures the
    # header put there. The header word is centred over the column and the figures are
    # right-aligned in it, so the header alone is a systematically shifted ruler; one
    # pass over the page's own figures removes the shift without introducing a constant.
    placed = collections.defaultdict(list)
    for b in body:
        if figure(b['text']) is not None:
            placed[column_of(b)].append(b['x'] + b['w'])
    centres = dict(centres)
    for k, edges in placed.items():
        if k != LABEL_COL and len(edges) >= 3:
            centres[k] = statistics.median(edges)

    # THE ROWS ARE THE PRINTED LABELS, and every figure joins the label it is NEAREST.
    #
    # The first version grew a row forward from whichever box came first and started a
    # new one once the gap passed half the page's row pitch. That is the trust-table
    # recipe and it is wrong for a table this wide: a row here runs the full width of the
    # page, so the scanner's own rotation spreads one row's observations over more y than
    # half a pitch, and the last figure on the line -- always the BALANCES column, the
    # one every check depends on -- falls off the end into a row of its own. It cost
    # FY2017 and FY2022 a row each, and both losses looked like missing data.
    #
    # Every row of this table prints a label, so the labels ARE the rows. Nearest wins,
    # with no tolerance to pick: the pitch is what separates two rows and a figure sits
    # far nearer its own label than the next one down.
    labels = sorted((b for b in body if column_of(b) == LABEL_COL
                     and figure(b['text']) is None
                     and not any(t in b['text'] for t in TITLE)),
                    key=lambda b: -Y(b))
    if not labels:
        return [], 0
    rows = []
    for b in labels:
        if rows and abs(Y(rows[-1]['anchor']) - Y(b)) < 1e-6:
            rows[-1]['label'].append(b['text'].strip())
            continue
        rows.append({'anchor': b, 'label': [b['text'].strip()], 'vals': {},
                     'dup': False, 'fixed': []})
    out, unparsed = rows, 0
    for b in body:
        t = b['text'].strip()
        if any(x in t for x in TITLE):
            continue
        fix = CORRECTIONS.get((stem, page, round(b['x'], 5), round(b['y'], 5)))
        v = fix[0] if fix else figure(t)
        col = column_of(b)
        if v is None:
            if MONEY_LOOKING.search(t) and col != LABEL_COL:
                unparsed += 1
            continue
        row = min(rows, key=lambda r: abs(Y(r['anchor']) - Y(b)))
        if col in row['vals']:
            row['dup'] = True
        row['vals'][col] = row['vals'].get(col, 0.0) + v
        if fix:
            row['fixed'].append(col)
    return [(' '.join(r['label']).strip(), r['vals'], r['dup'],
             ';'.join(sorted(set(r['fixed'])))) for r in out], unparsed


def extract():
    years = {}
    for path in sorted(glob.glob(os.path.join(OCR, '*annual-town-report*.tsv'))):
        name = os.path.basename(path)
        m = re.search(r'fy-(\d{4})', name)
        if not m:
            continue
        fy = int(m.group(1))
        stem = name[:-4]
        pages = load(path)
        pnums = table_pages(pages)
        if not pnums:
            continue
        doc = os.path.relpath(path, ROOT)

        # EVERY PAGE'S COLUMNS ARE READ OFF ITS OWN HEADER, by one of three routes, and
        # a page that none of them fits contributes nothing rather than being aligned to
        # a neighbour's layout on trust. Which route was used is written into `notes`.
        #
        #   anchors   -- the header returned all eight names one to a box
        #   ruler     -- it named all eight but anchored only some; the pitch is fitted
        #   carried   -- it named fewer than eight; a page of the SAME YEAR that did is
        #                mapped onto this one by the anchors the two share
        prepared = {}
        for p in pnums:
            boxes = split_merged(pages[p])
            m_slope = skew(boxes)
            # A BOX IS PLACED BY ITS CENTRE, never by its bottom edge. A bracketed
            # figure's box is half again as tall as a plain one -- the brackets ascend
            # and descend past the digits -- so its bottom sits visibly lower than its
            # neighbours' and it lands in the row beneath. FY2017's `($18,493.51)`, box
            # height 0.0177 against a typical 0.0113, is the worked example: a motor
            # vehicle abatement that read perfectly and was filed against the wrong levy.
            Y = (lambda s: (lambda b: b['y'] + b['h'] / 2.0 - s * b['x']))(m_slope)
            anchors, order, first_val = page_header(boxes, Y)
            centres, resid, how = None, None, None
            if all(c in anchors for c in COLUMNS):
                centres, resid, how = dict(anchors), 0.0, 'anchors'
            else:
                centres, resid = ruler(anchors, order)
                how = 'ruler' if centres else None
            prepared[p] = dict(boxes=boxes, Y=Y, slope=m_slope, anchors=anchors,
                               order=order, first_val=first_val, centres=centres,
                               resid=resid, how=how)
        rec = {'fy': fy, 'document': doc, 'pages': ';'.join(str(p) for p in pnums)}
        named = [p for p in pnums if prepared[p]['centres']]
        if not named:
            best = max(pnums, key=lambda p: (len(set(prepared[p]['order'])),
                                             len(prepared[p]['anchors'])))
            miss = [c for c in COLUMNS if c not in set(prepared[best]['order'])]
            if miss:
                why = ('no page names all eight columns: the fullest header, on p%d, '
                       'names %d of them and never %s -- the scan of these pages ends '
                       'before the right-hand columns'
                       % (best, 8 - len(miss), ' or '.join(miss)))
            else:
                why = ('no page anchors enough columns: the fullest header, on p%d, '
                       'names all eight but the scanner returned them run together in '
                       'one box, so only %d column position is measurable and the '
                       'pitch cannot be fitted'
                       % (best,
                          len([c for c in prepared[best]['anchors'] if c != LABEL_COL])))
            rec.update(state='refused', reason=why)
            years.setdefault(fy, []).append((rec, [], None))
            continue
        ref_page = max(named, key=lambda p: (len(prepared[p]['anchors']),
                                             -(prepared[p]['resid'] or 0)))
        reference = prepared[ref_page]['centres']
        for p in pnums:
            pr = prepared[p]
            if pr['centres'] is None:
                pr['centres'], pr['resid'] = fit(pr['anchors'], reference)
                pr['how'] = 'carried from p%d' % ref_page if pr['centres'] else None
        rec['header_read_from_page'] = ref_page
        rec['column_order'] = ';'.join(
            sorted(COLUMNS, key=lambda c: reference[c]))

        rows, notes, unparsed_total = [], [], 0
        for p in pnums:
            pr = prepared[p]
            if pr['first_val'] is None:
                notes.append('p%d: no figures' % p)
                continue
            if pr['centres'] is None:
                notes.append('p%d: header unreadable and too few anchors to carry one' % p)
                continue
            notes.append('p%d %s residual %.4f skew %.5f'
                         % (p, pr['how'], pr['resid'], pr['slope']))
            page_rows, unparsed = read_page(pr['boxes'], pr['centres'], pr['Y'],
                                            pr['first_val'], stem, p)
            unparsed_total += unparsed
            section = ''
            for label, vals, dup, fixed in page_rows:
                lab = re.sub(r'\s+', ' ', label).strip()
                if not vals:
                    if lab and not any(t in lab for t in TITLE):
                        section = lab
                    continue
                rows.append(dict(fy=fy, document=doc, page=p, section=section,
                                 line=lab, vals=vals, dup=dup, corrected=fixed))
        rec['unparsed_figures'] = unparsed_total
        rec['notes'] = '; '.join(notes)
        years.setdefault(fy, []).append((rec, rows, None))
    return years


def reconcile(rec, rows):
    """Tie the detail to the GRAND TOTAL the page prints. Refuse the year otherwise."""
    totals = [r for r in rows if r['line'].upper().startswith('GRAND TOTAL')]
    detail = [r for r in rows if not r['line'].upper().startswith('GRAND TOTAL')]
    rec['rows'] = len(detail)
    if len(totals) != 1:
        rec.update(state='refused',
                   reason='%d GRAND TOTAL rows were read off pages %s, not one'
                          % (len(totals), rec['pages']))
        return []
    printed = totals[0]['vals']
    rec['grand_total_forward'] = '%.2f' % printed.get('balance_forward', 0.0)
    rec['grand_total_balance'] = '%.2f' % printed.get('balance', 0.0)
    failed = []
    for c in COLUMNS:
        ours = round(sum(r['vals'].get(c, 0.0) for r in detail), 2)
        theirs = round(printed.get(c, 0.0), 2)
        if abs(ours - theirs) > TOL:
            failed.append('%s ours %.2f printed %.2f diff %.2f' % (c, ours, theirs,
                                                                   ours - theirs))
    if failed:
        rec.update(state='refused',
                   reason='does not tie to its own GRAND TOTAL: ' + '; '.join(failed))
        return []
    bad = 0
    for r in detail:
        v = r['vals']
        moved = sum(v.get(c, 0.0) for c in COLUMNS if c != 'balance')
        ok = abs(moved - v.get('balance', 0.0)) <= TOL
        if r['dup']:
            # Two printed lines whose label the scanner returned once, so they were read
            # as one row: the figures are the SUM of two lines of the table. They are
            # published because they are part of a reading that ties, and labelled
            # because nobody should quote one as a single line of the document.
            r['row_check'] = 'two printed lines read as one' if ok else 'check failed'
        else:
            r['row_check'] = 'checked' if ok else 'check failed'
        bad += r['row_check'] == 'check failed'
    rec.update(state='reconciled',
               reason='ties to its printed GRAND TOTAL on all eight columns',
               rows_failing_row_identity=bad)
    return detail


def build():
    out_rows, out_rec = [], []
    for fy, candidates in sorted(extract().items()):
        kept = []
        for rec, rows, _ in candidates:
            if rec.get('state') == 'refused':
                out_rec.append(rec)
                continue
            detail = reconcile(rec, rows)
            out_rec.append(rec)
            if detail:
                kept.append(detail)
        for detail in kept:
            out_rows.extend(detail)
    header = (['fy', 'document', 'page', 'section', 'line'] + list(COLUMNS)
              + ['row_check', 'ocr_corrected'])
    rows_csv = [header]
    for r in sorted(out_rows, key=lambda r: (r['fy'], r['page'])):
        rows_csv.append([r['fy'], r['document'], r['page'], r['section'], r['line']]
                        + ['' if c not in r['vals'] else '%.2f' % r['vals'][c]
                           for c in COLUMNS]
                        + [r['row_check'], r['corrected']])
    # A SECOND IDENTITY, ACROSS DOCUMENTS: what a year carries forward is what the year
    # before it ended with, and each figure is printed on its own GRAND TOTAL line in a
    # different annual report. It is not what decides whether a year is published -- a
    # year is published because it ties to its OWN total -- but it is the only check here
    # that a whole reading can be tested against something outside it, and FY2018 fails
    # it: it opens $13,300.00 above where FY2017 closed. Both figures are the town's.
    by_fy = {rec['fy']: rec for rec in out_rec if 'grand_total_balance' in rec}
    for fy, rec in by_fy.items():
        prior = by_fy.get(fy - 1)
        if prior and rec.get('grand_total_forward'):
            rec['opens_where_prior_closed'] = (
                '%.2f' % (float(rec['grand_total_forward'])
                          - float(prior['grand_total_balance'])))
    rec_header = ['fy', 'document', 'pages', 'state', 'rows', 'column_order',
                  'header_read_from_page', 'grand_total_forward',
                  'grand_total_balance', 'opens_where_prior_closed',
                  'rows_failing_row_identity', 'unparsed_figures', 'reason', 'notes']
    rec_csv = [rec_header]
    for rec in sorted(out_rec, key=lambda r: (r['fy'], r['document'])):
        rec_csv.append([rec.get(k, '') for k in rec_header])
    return rows_csv, rec_csv


def render(table):
    import io
    buf = io.StringIO()
    csv.writer(buf, lineterminator='\n').writerows(table)
    return buf.getvalue()


def main():
    rows_csv, rec_csv = build()
    want = {OUT_ROWS: render(rows_csv), OUT_RECON: render(rec_csv)}
    if '--check' in sys.argv:
        bad = False
        for path, text in want.items():
            have = open(path).read() if os.path.exists(path) else None
            if have != text:
                print('STALE: %s' % os.path.relpath(path, ROOT))
                bad = True
        if bad:
            sys.exit(1)
        print('receivables: both outputs reproduce')
        return
    for path, text in want.items():
        with open(path, 'w', newline='') as fh:
            fh.write(text)
    rec_header = rec_csv[0]
    tied = [r for r in rec_csv[1:] if r[3] == 'reconciled']
    print('%d detail rows written; %d of %d readings tie to their printed GRAND TOTAL'
          % (len(rows_csv) - 1, len(tied), len(rec_csv) - 1))
    for r in rec_csv[1:]:
        print('  FY%s %-12s %-4s %s' % (r[0], r[3], (r[4] or '-'),
                                     str(r[rec_header.index('reason')])[:110]))


if __name__ == '__main__':
    main()
