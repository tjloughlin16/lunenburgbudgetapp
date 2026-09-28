#!/usr/bin/env python3
"""THE RECEIVABLES PAGES OF THE ANNUAL REPORTS, proved row by row.

    python3 scripts/extract_receivables.py            # write sources/data/receivables.csv
    python3 scripts/extract_receivables.py --check    # fail if it no longer reproduces
    python3 scripts/extract_receivables.py --show fy2016:47

TWO DIFFERENT TABLES ARE FILED UNDER ONE SUBJECT, and reading them as one would have been
the first mistake. `annual-report-pages.csv` groups nine pages as `receivables`:

  * COLLECTION OF TAXES / RECEIVABLES SUMMARY -- eight pages. An AGEING table: one row per
    `LEVY OF <year>`, inside sections (REAL ESTATE, PERSONAL PROPERTY, MOTOR VEHICLE and
    the rest), carrying what was outstanding, what was committed, what came in and what is
    still owed.
  * General Fund Accounts Receivable Detail -- one page, FY2024 p22. One row per ACCOUNT
    NUMBER, with a deferred-revenue column and receipts measured to a date three months
    AFTER the fiscal year ends. Not the same quantity and not comparable to the other.

Each is recognised by the title it prints, never by its page number.

AND THE COLUMNS MOVE EVERY YEAR -- rule 13c, which this survey found the hard way:

    FY2016   FISCAL YEAR FORWARD COMMITTMENTS/ADJUSTMENTS REFUNDS PAYMENTS ABATEMENTS TRANSFER BALANCES
    FY2019   FISCAL YEAR FORWARD COMMITTMENTS ABATEMENTS PAYMENTS REFUNDS TRANSFER ADJUSTMENTS BALANCES
    FY2024   as FY2019, at different positions, and one page whose header OCRs as a single
             merged box

Payments and abatements are SWAPPED between 2016 and 2019 and refunds moves across three
columns. A extractor keyed on position, or on a layout written down once, would have put
payments under abatements for three years and produced figures that looked right. So the
header is read off each page and the columns are named from the words actually printed;
a page whose header cannot be read is REFUSED rather than aligned to a guess.

WHAT MAKES IT SAFE. Both tables state an identity about themselves, and only rows that
satisfy it are written:

  * ageing:  forward + committed + refunds - payments - abatements + transfers = balance
  * detail:  the rows sum to the GRAND TOTAL the page prints

The second is what proves the detail page is completely read even though OCR recovers a
label for only seven of its twenty-five rows: those seven sum to $1,275,638.93 and the
page prints $1,275,638.93, so the rest are the zeroes they appear to be. A reconciliation
is the only thing that can tell a short read from a complete one.
"""
import argparse
import collections
import csv
import io
import glob
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdf_tables as T  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCR = os.path.join(ROOT, 'sources', 'town-budget', 'ocr')
OUT = os.path.join(ROOT, 'sources', 'data', 'receivables.csv')
PAGES = os.path.join(ROOT, 'sources', 'data', 'annual-report-pages.csv')

# The words each column can be printed under. Read from the page; the ONLY thing fixed
# here is which printed word means which quantity, and the sign it carries into the
# identity. `adjustments` is +1 because the table prints its own parentheses.
COLUMNS = [
    ('forward',     r'FORWARD',                      +1),
    ('committed',   r'COMMIT[TI]?MENTS?',            +1),
    ('abatements',  r'ABATEMENTS?',                  +1),
    ('payments',    r'PAYMENTS?',                    +1),
    ('refunds',     r'REFUNDS?',                     +1),
    ('transfers',   r'TRANSFERS?',                   +1),
    # `AD[JI]` because the scanner reads the J of ADJUSTMENTS as an I: FY2021 page 47
    # prints `ADIUSTMENTS` and the column went unnamed, so every figure under it was
    # dropped and fifteen rows on that page failed to sum to their own printed balance.
    # A conservative widening of ONE character that the scanner is known to confuse --
    # not a looser pattern.
    ('adjustments', r'AD[JI]USTM?E?N?T?S?',           +1),
    ('balance',     r'BALANCES?',                    +1),
]
LEVY = re.compile(r'LEVY\s+OF\s+(\d{4})', re.I)
SECTION = re.compile(r'^(REAL ESTATE|PERSONAL PROPERTY|MOTOR VEHICLE|BOAT|FARM|'
                     r'CPA|COMMUNITY PRESERVATION|SEWER|WATER|TRASH|AMBULANCE|BETTERMENT)',
                     re.I)
TOL = 0.02


def reports():
    for f in sorted(glob.glob(os.path.join(OCR, '*annual-town-report.tsv'))):
        m = re.search(r'fy-(\d{4})-', f)
        if m:
            yield int(m.group(1)), f


def by_page(path):
    out = collections.defaultdict(list)
    for b in T.read_boxes(path):
        out[b['page']].append(b)
    return out


def band(boxes):
    """HALF THE PAGE'S OWN ROW PITCH, measured, never a constant -- rule 13b.

    A guessed tolerance holds some rows together and splits others, and what it loses from
    the long rows is the balance column every check depends on.
    """
    ys = sorted({round(b['y'], 4) for b in boxes})
    # THE TWO POPULATIONS HAVE TO BE SEPARATED BEFORE THE PITCH IS MEASURED. On a scan a
    # printed row's boxes do not share a `y`, so the gaps between consecutive readings are
    # a mixture: the jitter WITHIN a row and the pitch BETWEEN rows. Taking the median of
    # the mixture returns the jitter, because there are more boxes in a row than rows on
    # the page -- 0.0036 on FY2017 page 43 and FY2020 page 49 against true pitches of
    # 0.0097 and 0.0226. The band came out smaller than the scatter it exists to absorb,
    # so a label and its balance landed in different rows and seven pages were refused for
    # `no row on the page carries both a label and a balance figure`.
    #
    # The page's own TYPE SIZE tells them apart: boxes of one printed row share a baseline
    # and rows are set more than a line apart. So gaps under six tenths of the median box
    # height are jitter and are dropped, and the pitch is the median of what is left.
    # Measured from the page, not chosen -- the same correction the debt schedules and the
    # FY2019 wage pages both needed, which is three extractors making one mistake.
    hs = [b['h'] for b in boxes if b['h'] > 0]
    floor = (statistics.median(hs) * 0.6) if hs else 0.004
    gaps = sorted(b - a for a, b in zip(ys, ys[1:]) if floor < (b - a) < 0.05)
    if not gaps:
        return max(floor, 0.003)
    return max(gaps[len(gaps) // 2] / 2.0, 0.003)


def pat_of(name):
    return next(p for n, p, _ in COLUMNS if n == name)


def header_of(boxes):
    """The column names AS PRINTED, and where each sits. None if they cannot be read."""
    hits, width_of = [], {}
    for b in boxes:
        t = (b['text'] or '').upper()
        for name, pat, sign in COLUMNS:
            if re.search(pat, t):
                hits.append((b['y'], b['x'], name, sign, b['text']))
                width_of[id(b['text'])] = b['w']
    if not hits:
        return None
    # The header is the y that carries the most of those words.
    rows = collections.Counter(round(y, 2) for y, *_ in hits)
    hy, n = rows.most_common(1)[0]
    if n < 3:
        return None
    cols = {}
    for y, x, name, sign, raw in hits:
        if abs(y - hy) >= 0.025 or name in cols:
            continue
        # A MERGED HEADING GIVES EVERY NAME IN IT THE SAME x, WHICH IS NOT A POSITION.
        # FY2017 page 43 returns `FORWARD COMMITTMENTS ADJUSTMENTS REFUNDS PAYMENTS` as
        # ONE observation, so five columns were all recorded at x=0.307 and every figure
        # on the page was placed against the same coordinate. The box spans the columns it
        # names, so each name's own x is recoverable by where it sits INSIDE the string --
        # the same character-position split `split_merged` does for figures in the debt
        # schedules. Interpolated, and exact enough: what matters is the ORDER and spacing
        # of the headings, which is what the placement compares against.
        m = re.search(pat_of(name), (raw or '').upper())
        w = width_of.get(id(raw), None)
        if m and w and len(raw) > 0:
            mid = (m.start() + m.end()) / 2.0
            x = x + w * (mid / len(raw))
        cols[name] = dict(x=x, sign=sign, printed=raw)
    return dict(y=hy, cols=cols) if len(cols) >= 3 else None


def place(figs, cols):
    """EACH FIGURE UNDER THE COLUMN ITS CENTRE IS NEAREST -- never in printed order.

    A levy with no activity prints nothing in those columns, so taking the figures in
    order puts every one after the first gap under the wrong heading.
    """
    # AND WHERE TWO FIGURES CLAIM ONE COLUMN, THE NEARER ONE TAKES IT. `setdefault` kept
    # whichever came first, which is printed order -- the very thing this function exists
    # to avoid, reintroduced one line below the docstring that forbids it. On FY2021 page
    # 47 a row printed figures at 0.269, 0.779 and 0.849 where the page has no TRANSFERS
    # heading, so both of the last two were nearest to BALANCE and the leftmost won:
    # balance read 4.85 against a printed 3,276.19, and 3,271.34 + 4.85 = 3,276.19 says
    # which of the two it is. Fifteen rows on that page failed for this, which took it
    # under the threshold that proves a page, which refused the page whole.
    best = {}
    for x, v in figs:
        name = min(cols, key=lambda k: abs(cols[k]['x'] - x))
        d = abs(cols[name]['x'] - x)
        if d > 0.09:
            continue
        if name not in best or d < best[name][0]:
            best[name] = (d, v)
    return {k: v for k, (_, v) in best.items()}


def ageing_page(fy, page, boxes):
    """One COLLECTION OF TAXES page: rows that prove, and the ones that do not."""
    head = header_of(boxes)
    if not head:
        return [], [_refuse(fy, page, 'the header could not be read; refused rather '
                                     'than aligned')]
    cols = head['cols']
    if 'balance' not in cols:
        return [], [_refuse(fy, page, 'no BALANCES column printed, so no row can be '
                                     'proved')]
    b = band(boxes)
    rows, notes, candidates = [], [], []
    section = ''
    # Sections and levy labels both sit in the left margin; walk the page top down so a
    # section heading is in force for the rows beneath it.
    for bx in sorted(boxes, key=lambda z: -z['y']):
        t = (bx['text'] or '').strip()
        if bx['x'] < 0.30 and SECTION.match(t):
            section = t.upper()
    for bx in sorted(boxes, key=lambda z: -z['y']):
        t = (bx['text'] or '').strip()
        if bx['x'] < 0.30 and SECTION.match(t):
            section = t.upper()
            continue
        m = LEVY.search(t)
        if not m or bx['x'] > 0.30:
            continue
        levy = int(m.group(1))
        figs = []
        for o in boxes:
            if abs(o['y'] - bx['y']) > b or o['x'] <= 0.25:
                continue
            v = T.amount((o['text'] or '').strip())
            if v is not None:
                figs.append((o['x'], v))
        got = place(figs, cols)
        if 'balance' not in got:
            notes.append('fy%d p%d %s levy %d: no balance figure on the row'
                         % (fy, page, section or '?', levy))
            continue
        parts = {k: got.get(k, 0.0) for k in
                 ('forward', 'committed', 'refunds', 'payments', 'abatements',
                  'transfers', 'adjustments')}
        candidates.append((levy, section or 'not stated', parts, got['balance']))

    # WHICH SIGN THE PAGE USES IS A FACT ABOUT THE PAGE, and it is not the same every year.
    #
    # FY2016 prints an ageing table whose parts add up to the balance. FY2019 prints the
    # same table with the signs inverted -- LEVY OF 2017 reads (17,280.57), (307.70),
    # 17,386.74 against a printed balance of 201.53, and the parts sum to MINUS 201.53.
    # Same arithmetic, opposite convention, and nothing on the page says so.
    #
    # The wrong fix is a per-year sign table: that is choosing a sign until the answer
    # closes, which is fitting the rule to the result. Instead the page DECLARES its
    # convention by which one proves its rows, and it has to prove essentially all of
    # them -- a convention that works for half a page is not a convention, it is a
    # coincidence, and the page is refused.
    # A ROW'S LABEL IS NOT ALWAYS A LEVY YEAR, and assuming it was refused seven legible
    # pages. FY2018 page 54 prints the same eight columns under the same header and names
    # its rows `SEPTIC COMMITTED INT`, `WATER COMMITTED DUE W.D. PRI` -- committed accounts
    # rather than tax levies -- and every one of them states the page's own identity:
    # 0.00 + 1,094.56 - 547.28 = 547.28. Rule 13c: the town does not print one table shape
    # every year, and a matcher that finds no levy year is saying something about our
    # pattern, not about the page.
    #
    # It runs ONLY where the levy path found nothing, so no page that already reads can
    # change, and a named row has to clear the same bar: place a balance, place at least
    # two other columns, and prove under the page's single sign convention.
    if not candidates:
        for bx in sorted(boxes, key=lambda z: -z['y']):
            t = re.sub(r'\s+', ' ', (bx['text'] or '')).strip()
            if bx['x'] >= 0.30 or len(t) < 4 or not re.search(r'[A-Za-z]{3}', t):
                continue
            if SECTION.match(t) or t.upper().startswith(('GRAND TOTAL', 'TOTAL')):
                continue
            if head['y'] - 0.02 <= bx['y'] <= head['y'] + 0.02:
                continue
            figs = []
            for o in boxes:
                if abs(o['y'] - bx['y']) > b or o['x'] <= 0.25:
                    continue
                v = T.amount((o['text'] or '').strip())
                if v is not None:
                    figs.append((o['x'], v))
            got = place(figs, cols)
            if 'balance' not in got or len(got) < 3:
                continue
            parts = {k: got.get(k, 0.0) for k in
                     ('forward', 'committed', 'refunds', 'payments', 'abatements',
                      'transfers', 'adjustments')}
            candidates.append((t.upper(), section or 'not stated', parts, got['balance']))

    if not candidates:
        # A page that yields no candidate row at all was still READ, and silently
        # returning nothing is what made it indistinguishable from an unopened page.
        return [], notes + [_refuse(fy, page, 'no row on the page carries both a label '
                                              'and a balance figure')]
    best, best_sign, best_n = None, None, -1
    for sign in (1, -1):
        proved = [c for c in candidates
                  if abs(sign * sum(c[2].values()) - c[3]) <= TOL]
        if len(proved) > best_n:
            best, best_sign, best_n = proved, sign, len(proved)
    if best_n < 3 or best_n < 0.8 * len(candidates):
        notes.append(_refuse(fy, page, 'no single sign convention proves the page '
                                       '(%d of %d rows at best); refused'
                                       % (best_n, len(candidates))))
        return [], notes
    for levy, section_, parts, balance in best:
        rows.append(dict(fy=fy, page=page, table='collection of taxes',
                         section=section_, levy_year=levy,
                         **{k: '%.2f' % v for k, v in parts.items()},
                         balance='%.2f' % balance,
                         checked='parts sum to the printed balance'
                                 if best_sign > 0 else
                                 'parts sum to the printed balance, signs inverted '
                                 'as this page prints them'))
    skipped = len(candidates) - best_n
    if skipped:
        notes.append('fy%d p%d: %d of %d rows did not prove under the page\u2019s own '
                     'convention and were not written' % (fy, page, skipped, len(candidates)))
    return rows, notes


# A REFUSAL IS A FINDING AND IT HAS TO BE WRITTEN DOWN.
#
# This extractor refused ten pages and said so on stdout, where it was read once and lost.
# Nothing downstream could tell those ten pages from pages nobody had ever opened, so the
# annual-report queue carried them as `unread` -- work nobody has started -- when the truth
# is that the page is legible, an extractor exists, and the extractor is what is wrong.
# That is a different job, for a different person, and the queue could not say which.
#
# Seven other extractors here already write `<dataset>-refused.csv`. This one now does too.
# The `state` column is what keeps it honest: map_annual_report_pages.py treats any file
# carrying `state` as a catalogue rather than a reading, so recording a refusal cannot
# accidentally credit the page as read.
_REFUSED = []
REFUSED = os.path.join(ROOT, 'sources', 'data', 'receivables-refused.csv')
REFUSED_FIELDS = ['dataset', 'edition', 'report_fy', 'page', 'state', 'reason']


def _refuse(fy, page, reason):
    """Record that this page was read and refused, and return the note to print."""
    _REFUSED.append(dict(dataset='receivables', edition='FY%d' % fy, report_fy=fy,
                         page=page, state='refused', reason=reason))
    return 'fy%d p%d: %s' % (fy, page, reason)


DETAIL_COLS = [('receivable', r'Accounts|Receivable'), ('deferred', r'Deferred|Revenue'),
               ('receipts', r'Receipts'), ('remaining', r'Remaining')]


def detail_page(fy, page, boxes):
    """The General Fund Accounts Receivable Detail page, tied to its own printed total."""
    b = band(boxes)
    total_box = [z for z in boxes
                 if re.search(r'otal General Fund Accounts Receivable', z['text'] or '')]
    if not total_box:
        return [], ['fy%d p%d: no printed grand total, so nothing can be reconciled'
                    % (fy, page)]
    ty = total_box[0]['y']
    printed = [T.amount((z['text'] or '').strip()) for z in boxes
               if abs(z['y'] - ty) <= b and z['x'] > 0.4]
    printed = [v for v in printed if v is not None]
    if not printed:
        return [], ['fy%d p%d: the total row carries no figure' % (fy, page)]
    grand = max(printed)
    rows, seen = [], []
    for bx in sorted(boxes, key=lambda z: -z['y']):
        t = (bx['text'] or '').strip()
        if not re.match(r'^\d{4}-\d{6}$', t) or bx['y'] <= ty:
            continue
        near = [z for z in boxes if abs(z['y'] - bx['y']) <= b]
        name = ''.join(z['text'] for z in sorted(near, key=lambda z: z['x'])
                       if 0.15 < z['x'] < 0.45)
        figs = sorted([(z['x'], T.amount((z['text'] or '').strip())) for z in near
                       if z['x'] > 0.45 and T.amount((z['text'] or '').strip()) is not None])
        val = figs[0][1] if figs else 0.0
        seen.append(val)
        rows.append(dict(fy=fy, page=page, table='general fund accounts receivable',
                         section='general fund', levy_year='', forward='', committed='',
                         refunds='', payments='', abatements='', transfers='',
                         adjustments='', balance='%.2f' % val,
                         checked='account %s %s' % (t, name.strip())))
    # THE RECONCILIATION IS THE WHOLE POINT, and it is what proves a short read is not a
    # short table: seven labelled rows summing to the printed total means the rest are the
    # zeroes they appear to be.
    if abs(sum(seen) - grand) > TOL:
        return [], ['fy%d p%d: rows sum to %.2f against a printed %.2f; not written'
                    % (fy, page, sum(seen), grand)]
    for r in rows:
        r['checked'] = r['checked'] + ' — ties to the printed total $%s' % ('{:,.2f}'.format(grand))
    return rows, []


FIELDS = ['fy', 'page', 'table', 'section', 'levy_year', 'forward', 'committed',
          'refunds', 'payments', 'abatements', 'transfers', 'adjustments', 'balance',
          'checked']


def wanted():
    """The pages `annual-report-pages.csv` files under `receivables`, and nothing else.

    Read from the map rather than listed here, so a page that is reclassified moves with
    it -- the location-hardcoding defect this repo has had four times.
    """
    out = collections.defaultdict(list)
    with open(PAGES, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            # TAX-COLLECTION IS THE SAME TABLE UNDER ANOTHER NAME. The page map assigns
            # a subject from the page's own headings, and `FY2011 COLLECTION OF TAXES`
            # lands under `tax-collection` while `FY2016 COLLECTION OF TAXES /
            # RECEIVABLES SUMMARY` lands under `receivables`. One table, two labels,
            # because the town added a second heading line in 2014. The reader keys on
            # what the page PRINTS, so it needs both subjects offered to it.
            if r.get('subject') in ('receivables', 'tax-collection'):
                out[int(r['fy'])].append(int(r['page']))
    return out


def run(show=None):
    want = wanted()
    rows, notes = [], []
    for fy, path in reports():
        if fy not in want:
            continue
        pages = by_page(path)
        for page in sorted(want[fy]):
            boxes = pages.get(page) or []
            if not boxes:
                notes.append(_refuse(fy, page, 'no OCR boxes for the page'))
                continue
            title = ' '.join(z['text'] for z in sorted(boxes, key=lambda z: -z['y'])[:6])
            if show and show == 'fy%d:%d' % (fy, page):
                for z in sorted(boxes, key=lambda z: (-z['y'], z['x'])):
                    print('  y=%.3f x=%.3f  %s' % (z['y'], z['x'], z['text']))
                return [], []
            # THE TABLE IS RECOGNISED BY WHAT IT PRINTS, never by its page number.
            if re.search(r'Accounts Receivable Detail', title, re.I):
                r, n = detail_page(fy, page, boxes)
            else:
                r, n = ageing_page(fy, page, boxes)
            rows.extend(r)
            notes.extend(n)
    return rows, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--show')
    a = ap.parse_args()
    rows, notes = run(show=a.show)
    if a.show:
        return 0
    rows.sort(key=lambda r: (r['fy'], r['page'], str(r['section']), str(r['levy_year'])))
    body = ['%s\n' % ','.join(FIELDS)]
    buf = []
    for r in rows:
        buf.append([str(r.get(k, '')) for k in FIELDS])
    s = io.StringIO()
    w = csv.writer(s, lineterminator='\n')
    w.writerow(FIELDS)
    w.writerows(buf)
    text = s.getvalue()

    # THE REFUSALS ARE AN OUTPUT, not a log line. Rendered here beside the rows so that
    # --check covers both: a refusal that quietly stops being recorded would put its page
    # back to looking like one nobody ever opened.
    _REFUSED.sort(key=lambda r: (r['report_fy'], r['page']))
    rs = io.StringIO()
    rw = csv.writer(rs, lineterminator='\n')
    rw.writerow(REFUSED_FIELDS)
    rw.writerows([[str(r.get(k, '')) for k in REFUSED_FIELDS] for r in _REFUSED])
    rtext = rs.getvalue()

    if a.check:
        have = open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        rhave = open(REFUSED, encoding='utf-8').read() if os.path.exists(REFUSED) else ''
        if have != text:
            print('receivables.csv is stale; re-run without --check')
            return 1
        if rhave != rtext:
            print('receivables-refused.csv is stale; re-run without --check')
            return 1
        print('%d row(s) and %d refusal(s), both reproduce' % (len(rows), len(_REFUSED)))
        return 0
    with open(OUT, 'w', encoding='utf-8', newline='') as fh:
        fh.write(text)
    with open(REFUSED, 'w', encoding='utf-8', newline='') as fh:
        fh.write(rtext)
    print('%d page(s) read and REFUSED, written to %s'
          % (len(_REFUSED), os.path.relpath(REFUSED, ROOT)))
    by_t = collections.Counter(r['table'] for r in rows)
    print('%d row(s) written to %s' % (len(rows), os.path.relpath(OUT, ROOT)))
    for k, v in by_t.items():
        print('   %-38s %d' % (k, v))
    if notes:
        print('\n%d page(s)/row(s) NOT written, and why:' % len(notes))
        for n in notes:
            print('   ' + n)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
